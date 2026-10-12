#!/usr/bin/env bash
set -Eeuo pipefail

AMD_ROCM_MATRIX_URL="https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html"
MODE="check"

usage() {
    cat <<'EOF'
Usage: prepare-ai-host.sh [--check | --install-base]

  --check          Read-only host inventory and current AMD support check (default)
  --install-base   Install common host tools after showing the apt plan
  --help           Show this help

This does not install ROCm, llama.cpp, ONNX Runtime, ComfyUI, NGINX, or
Qdrant's application configuration. GPU stack installation remains blocked
until AMD publishes support for the detected Proxmox/kernel/GPU combination
and the application versions and service layout are reviewed.
EOF
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        --check)
            MODE="check"
            ;;
        --install-base)
            MODE="install-base"
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            usage >&2
            fail "Unknown option: $1"
            ;;
    esac
    shift
done

[[ "$(uname -s)" == "Linux" ]] || fail "This script must run on Linux."
[[ -r /etc/os-release ]] || fail "Cannot identify the Linux distribution."
# shellcheck disable=SC1091
source /etc/os-release

KERNEL_RELEASE="$(uname -r)"
ARCH="$(uname -m)"
PVE_VERSION="not detected"
if command -v pveversion >/dev/null 2>&1; then
    PVE_OUTPUT="$(pveversion 2>/dev/null || true)"
    PVE_VERSION="$(sed -nE 's/^pve-manager\/([0-9]+(\.[0-9]+)*).*/\1/p' <<<"$PVE_OUTPUT" | head -n 1)"
    PVE_VERSION="${PVE_VERSION:-not detected}"
fi
TARGET_VALID="yes"

printf '%s\n' "AI Server host preflight"
printf 'Distribution: %s %s (%s)\n' "${PRETTY_NAME:-unknown}" "${VERSION_ID:-}" "${ID:-unknown}"
printf 'Proxmox VE: %s\n' "$PVE_VERSION"
printf 'Kernel: %s\n' "$KERNEL_RELEASE"
printf 'Architecture: %s\n' "$ARCH"

GPU_LIST=""
if command -v lspci >/dev/null 2>&1; then
    GPU_LIST="$(lspci -nn | awk 'tolower($0) ~ /vga compatible controller|3d controller|display controller/ && tolower($0) ~ /amd|ati/ { print }')"
fi
if [[ -z "$GPU_LIST" ]] && [[ -d /sys/bus/pci/devices ]]; then
    for device in /sys/bus/pci/devices/*; do
        [[ -r "$device/vendor" && -r "$device/class" ]] || continue
        [[ "$(cat "$device/vendor")" == "0x1002" ]] || continue
        class="$(cat "$device/class")"
        [[ "$class" == 0x03* ]] || continue
        GPU_LIST+="${device##*/} AMD PCI device $(cat "$device/device")"$'\n'
    done
fi
if [[ -n "$GPU_LIST" ]]; then
    printf 'AMD display devices:\n%s\n' "$GPU_LIST"
else
    printf '%s\n' "AMD display devices: not detected (the GPU may not be installed or visible)"
fi
GPU_MODEL_PRESENT="no"
if grep -Eiq 'RX[[:space:]]*6800.*XT|6800[[:space:]]*XT' <<<"$GPU_LIST"; then
    GPU_MODEL_PRESENT="yes"
fi

if [[ "$ID" != "debian" ]] || [[ ! "$PVE_VERSION" =~ ^9(\.|$) ]]; then
    TARGET_VALID="no"
    printf '%s\n' "Target check: this installer requires a positively detected Proxmox VE 9.x Debian host."
    if [[ "$MODE" == "install-base" ]]; then
        fail "Refusing package installation outside a detected Proxmox VE host."
    fi
fi

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "AMD support check: unavailable (python3 is not installed)"
    AMD_CHECK="unverified"
elif python3 - "$AMD_ROCM_MATRIX_URL" "$KERNEL_RELEASE" "$GPU_MODEL_PRESENT" <<'PY'
import re
import sys
from html.parser import HTMLParser
from urllib.request import Request, urlopen

url, kernel, gpu_detected = sys.argv[1:]

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"th", "td"} and self.row is not None:
            self.cell = []
            self.in_cell = True

    def handle_data(self, data):
        if self.in_cell and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self.in_cell:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
            self.in_cell = False
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

try:
    request = Request(url, headers={"User-Agent": "AI-Server-Preflight/1.0"})
    with urlopen(request, timeout=15) as response:
        parser = Tables()
        parser.feed(response.read().decode("utf-8", errors="replace"))
except Exception as error:
    print(f"AMD support check: UNVERIFIED ({error})")
    sys.exit(2)

rows = [" | ".join(row) for row in parser.rows]
gpu_supported = gpu_detected == "yes" and any(
    re.search(r"\bRX\s*6800\s*XT\b", row, re.IGNORECASE)
    and re.search(r"\bAMD\b|\bRadeon\b", row, re.IGNORECASE)
    for row in rows
)
pve_supported = any(
    re.search(r"\bProxmox\s+VE\s+9(?:\.x|\.\d+)?\b", row, re.IGNORECASE)
    for row in rows
)
kernel_major_minor = ".".join(kernel.split("-", 1)[0].split(".")[:2])
kernel_supported = any(
    pve_supported
    and re.search(r"\bProxmox\s+VE\s+9(?:\.x|\.\d+)?\b", row, re.IGNORECASE)
    and kernel_major_minor in row
    for row in rows
)

if gpu_supported and pve_supported and kernel_supported:
    print("AMD support check: listed for RX 6800 XT, Proxmox VE 9, and this kernel family.")
    sys.exit(0)

missing = []
if not gpu_supported:
    if gpu_detected != "yes":
        missing.append("the planned RX 6800 XT was not detected")
    if not any(
        re.search(r"\bRX\s*6800\s*XT\b", row, re.IGNORECASE)
        and re.search(r"\bAMD\b|\bRadeon\b", row, re.IGNORECASE)
        for row in rows
    ):
        missing.append("RX 6800 XT is not listed in AMD's supported GPU table")
if not pve_supported:
    missing.append("Proxmox VE 9 is not listed as a supported operating system")
if pve_supported and not kernel_supported:
    missing.append(f"kernel family {kernel_major_minor} is not listed for Proxmox VE 9")
print("AMD support check: NOT VERIFIED — " + "; ".join(missing))
sys.exit(1)
PY
then
    AMD_CHECK="supported"
else
    CHECK_STATUS=$?
    if [[ "$CHECK_STATUS" -eq 2 ]]; then
        AMD_CHECK="unverified"
    else
        AMD_CHECK="blocked"
    fi
fi

if [[ "$TARGET_VALID" != "yes" ]]; then
    AMD_CHECK="blocked"
fi

if [[ "$MODE" == "check" ]]; then
    printf 'ROCm install gate: %s\n' "$AMD_CHECK"
    printf 'AMD compatibility source: %s\n' "$AMD_ROCM_MATRIX_URL"
    printf '%s\n' "No system changes were made."
    if [[ "$AMD_CHECK" != "supported" ]]; then
        exit 2
    fi
    exit 0
fi

[[ "$EUID" -eq 0 ]] || fail "--install-base must be run as root."
command -v apt-get >/dev/null 2>&1 || fail "apt-get is required."
if [[ "$ARCH" != "x86_64" ]]; then
    fail "This initial stack plan only targets x86_64."
fi
[[ "$PVE_VERSION" == 9.* ]] || fail "Base package setup is currently limited to Proxmox VE 9.x."

BASE_PACKAGES=(
    ca-certificates
    curl
    git
    build-essential
    cmake
    ninja-build
    pkg-config
    python3
    python3-venv
    python3-pip
    pciutils
    podman
    nginx
)

apt-get update
HEADER_PACKAGE="proxmox-headers-${KERNEL_RELEASE}"
if apt-cache show "$HEADER_PACKAGE" >/dev/null 2>&1; then
    BASE_PACKAGES+=("$HEADER_PACKAGE")
    printf 'Matching installed-kernel headers: %s\n' "$HEADER_PACKAGE"
else
    printf 'WARNING: no apt candidate found for %s; kernel headers will not be installed.\n' "$HEADER_PACKAGE" >&2
fi

printf '\n%s\n' "Simulated package plan:"
APT_PLAN="$(apt-get --simulate install --no-install-recommends "${BASE_PACKAGES[@]}")"
printf '%s\n' "$APT_PLAN"
if grep -Eq '^(Inst|Remv) (pve-kernel|proxmox-kernel|linux-image|proxmox-default-kernel)(:|[[:space:]])' <<<"$APT_PLAN"; then
    fail "The proposed apt transaction changes a kernel package; refusing to continue."
fi
printf '\n%s\n' "This installs host prerequisites only; it does not install the inference stack."
read -r -p "Install these packages on this Proxmox host? [y/N] " answer
[[ "$answer" == "y" || "$answer" == "Y" ]] || fail "Cancelled; no packages installed."

apt-get install --no-install-recommends "${BASE_PACKAGES[@]}"
printf '\n%s\n' "Host prerequisites installed."
printf 'ROCm install gate: %s\n' "$AMD_CHECK"
printf '%s\n' "ROCm and GPU-dependent components remain uninstalled until their compatibility and version pins are verified."
