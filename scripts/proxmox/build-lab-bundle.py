#!/usr/bin/env python3
"""Build an allow-listed, LF-normalized release bundle for the nested lab.

The bundle contains only what the Containerfile and Quadlet units need. It never
includes .env files, tests, databases, logs, or the Git directory. Text files are
normalized to LF so the Containerfile and Quadlet units parse on Linux even when
the Windows working tree uses CRLF.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SINGLE_FILES = (
    "Containerfile",
    ".containerignore",
    "index.html",
    "deploy/quadlet/ai-server-backend.container",
    "deploy/quadlet/ai-server-dashboard.container",
    "deploy/boot-autostart/ai-server-backend.container.d/10-boot-autostart.conf",
    "deploy/boot-autostart/ai-server-dashboard.container.d/10-boot-autostart.conf",
    "deploy/systemd/ai-server-housekeeping.service",
    "deploy/systemd/ai-server-housekeeping.timer",
    "scripts/proxmox/ai-server-housekeeping.sh",
    "ai-backend/requirements-linux.lock",
)
TREES = (("ai-backend", "*.py"), ("ai-backend/api", "*.py"),
         ("ai-backend/api/routes", "*.py"), ("ai-backend/gpu", "*.py"),
         ("css", "*"), ("js", "*"))
TEXT_SUFFIXES = {".py", ".html", ".css", ".js", ".lock", ".container", ".conf",
                 ".service", ".timer", ".sh", ""}


def collect() -> list[Path]:
    files = [ROOT / name for name in SINGLE_FILES]
    for directory, pattern in TREES:
        files.extend(sorted(p for p in (ROOT / directory).glob(pattern) if p.is_file()))
    missing = [str(p.relative_to(ROOT)) for p in files if not p.is_file()]
    if missing:
        raise SystemExit(f"Missing required files: {', '.join(missing)}")
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path of the .tar.gz to create.")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite {args.output}")

    entries = collect()
    with tarfile.open(args.output, "w:gz") as bundle:
        for path in entries:
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            if path.suffix in TEXT_SUFFIXES:
                data = data.replace(b"\r\n", b"\n")
            info = tarfile.TarInfo(relative)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            bundle.addfile(info, io.BytesIO(data))

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"{len(entries)} files -> {args.output}")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
