# Linux/Proxmox Transition Runbook

## Purpose and status

This runbook records what can move from the Windows test environment, what
must be implemented or decided for Linux, and the checks required before the
AI Server is considered operational. It is a preparation guide, not evidence
that Linux/Proxmox deployment has already been tested.

The current target is a Proxmox VE 9.x host with one AMD RX 6800 XT, with
services managed using Podman and Quadlet. The RX 6800 XT is currently in the
Windows development machine and is planned to move to the server after a
replacement GPU is acquired. This is a target design, not an installed or
compatibility-tested stack.

## Intended Linux/Proxmox stack

The planned components are:

- **GPU compute:** AMD ROCm and HIP.
- **ROCm placement:** install the ROCm/HIP stack on the Proxmox host; GPU
  driver, kernel, and device setup therefore require host-specific validation.
- **LLM inference:** llama.cpp built with ROCm support, exposing `llama-server`
  to the local backend.
- **Vision inference:** ONNX Runtime with its ROCm Execution Provider.
- **Image generation:** ComfyUI with a ROCm-compatible PyTorch/runtime setup.
- **Service packaging and lifecycle:** Podman containers managed by Quadlet
  systemd units where containerization is appropriate.
- **Web entry point:** NGINX serving the dashboard and reverse-proxying the
  protected backend endpoints.
- **Vector storage:** Qdrant, managed as a service/container.

The exact point release, kernel, ROCm/HIP and application versions, container
boundaries, persistent storage paths, network bindings, and installation
sources remain to be recorded and verified before generating version-pinned
installation steps. In particular, verify AMD's current support for installing
ROCm/HIP on the exact Proxmox host/kernel/RX 6800 XT combination; do not assume
the Windows Vulkan results establish ROCm, HIP, or ROCm telemetry
compatibility.

## What is portable now

- The dashboard is static HTML, CSS, and JavaScript.
- The API, chat client, model inventory/switching logic, and web-research
  integration are Python and use the standard library plus the packages in
  `ai-backend/requirements.txt`.
- CPU and system RAM percentages are read through `psutil`.
- Chat and research call local HTTP services. Their URLs are configurable
  using `LLAMA_CPP_BASE_URL` and `SEARXNG_BASE_URL`.
- The model manager already has POSIX process handling and defaults to a
  Linux llama.cpp device name of `ROCm0`. This is not proof that the eventual
  llama.cpp build exposes that device name or that ROCm supports the chosen
  OS/kernel/GPU combination.

## Linux blockers to close

1. **Record the operating-system target.** Services are intended to run on
   the Proxmox VE 9.x host, managed through Podman/Quadlet. Record the exact
   Proxmox point release, kernel, boot mode, GPU ownership, storage locations,
   and recovery access before driver work. Moving services into a guest
   changes GPU access and telemetry requirements and needs an explicit design
   change.
2. **Verify the GPU software stack for the exact target.** Check the current
   official AMD ROCm support matrix for the selected Proxmox release/kernel,
   RX 6800 XT (and any additional GPUs), and ROCm/HIP version. Then build
   llama.cpp with the ROCm backend and record its pinned revision, build
   flags, device name, and smoke-test results. Windows Vulkan test results do
   not certify this build.
3. **Implement a Linux telemetry provider.** `system_stats.py` currently
   imports `gpu.windows_gpu`; that provider intentionally returns unavailable
   on non-Windows systems. `gpu/gpu_rocm.py` is only a stub. Implement a Linux
   provider for the same API fields, with truthful adapter identity, GPU
   utilization, VRAM used/total, status, and diagnostic error. Report `null`
   and `unavailable` if the selected telemetry source cannot provide a live
   measurement; do not substitute simulated values. Verify idle and
   inference readings against an independent host tool.
4. **Decide how browsers reach the API.** `js/app.js` currently hardcodes
   `http://127.0.0.1:8000`. In a browser on another device, this points to that
   device, not the AI Server. Configure a server-reachable API origin or put
   the dashboard and API behind a same-origin reverse proxy, and test from a
   separate LAN client. Do not expose the llama.cpp port to the LAN.
5. **Harden access before LAN use.** FastAPI currently allows all CORS origins
   and has no authentication. Do not expose the API, model-switch endpoint, or
   llama.cpp to an untrusted network. Before remote/LAN access, decide and
   implement authentication, restrictive CORS, firewall rules, TLS or a
   trusted reverse proxy, and a safe model-switch policy.
6. **Create Linux service management.** The `.bat` scripts only support
   Windows. Prepare Podman/Quadlet units for containerized services and
   systemd units or documented host environments for components that need
   direct host/GPU access. Cover llama-server, backend, NGINX, Qdrant,
   ComfyUI, and any ONNX Runtime service actually integrated. Use a dedicated
   service account, explicit environment files, controlled startup ordering,
   persistent volumes/logs, health checks, and a least-privilege GPU device
   access policy. Ensure model switching can inspect and stop only its own
   llama-server process.
7. **Set Linux paths and permissions.** Configure `AI_SERVER_MODEL_DIR` and
   `LLAMA_SERVER_EXECUTABLE`; ensure the service account can read model files,
   write its logs, and access the selected GPU device. Keep models and
   llama.cpp build artifacts outside the source checkout and back them up or
   document how to reacquire them.
8. **Install Linux-specific AI packages separately.** Windows DirectML
   packages in `ai-backend/requirements-windows.txt` and
   `ai-discord-bot/requirements-windows.txt` are not the Linux install path.
   Install only the common `requirements.txt` dependencies first. Pin and
   validate the selected ONNX Runtime ROCm Execution Provider and ComfyUI
   ROCm-compatible dependency/model versions; neither is currently a
   production integration.
9. **Configure optional services and secrets.** Deploy SearXNG and enable its
   JSON response format before enabling web research. Set its URL through
   `SEARXNG_BASE_URL`. If the Discord bot is enabled, set a real token outside
   source control and set `AI_SERVER_API_BASE` to a reachable API address.

## Deployment configuration inventory

| Setting | Current default/behavior | Linux deployment action |
| --- | --- | --- |
| `AI_SERVER_MODEL_DIR` | Windows `%LOCALAPPDATA%\AI-Server\models`; otherwise `~/AI-Server/models` | Set an explicit persistent model directory. |
| `LLAMA_SERVER_EXECUTABLE` | Windows build path, or `llama-server` on PATH when `LOCALAPPDATA` is absent | Set the absolute Linux executable path. |
| `LLAMA_CPP_BASE_URL` | `http://127.0.0.1:8080` | Keep loopback when API and runtime share the host. |
| `LLAMA_CPP_DEVICE` | `Vulkan0` on Windows; `ROCm0` otherwise | Set to the exact device identifier reported by the deployed build. |
| `LLAMA_CPP_GPU_LAYERS` | `99` | Confirm available VRAM and inference behavior; tune if needed. |
| `LLAMA_CPP_CTX_SIZE` | `4096` | Confirm memory use and desired context length. |
| `SEARXNG_BASE_URL` | `http://127.0.0.1:8888` | Set the reachable SearXNG endpoint and enable JSON output. |
| `AI_SERVER_API_BASE` | Discord bot defaults to `http://127.0.0.1:8000` | Set it if the bot runs on another host or guest. |
| `DISCORD_TOKEN` | Placeholder default | Supply through a protected environment file only if using the bot. |

Container image tags, Quadlet unit names, Qdrant data volume, ComfyUI model
directories, and NGINX hostnames/certificates must be selected in the
deployment-specific configuration; do not put secret values in unit files
tracked in the repository.

## Host preparation script

[`scripts/proxmox/prepare-ai-host.sh`](../scripts/proxmox/prepare-ai-host.sh)
is an initial, deliberately conservative bootstrap:

- Run `bash scripts/proxmox/prepare-ai-host.sh --check` for a read-only
  inventory of the installed distribution, Proxmox release, running kernel,
  architecture, and detected AMD display device. The script checks AMD's live
  [ROCm compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
  and fails closed unless the RX 6800 XT, Proxmox VE 9, and installed kernel
  family are explicitly listed.
- Run `sudo bash scripts/proxmox/prepare-ai-host.sh --install-base` only on
  the server, after reviewing its simulated apt plan. It installs common
  build/runtime and host tools and adds headers for the exact running kernel
  only when an apt candidate exists. It refuses a transaction that proposes
  replacing or removing a kernel package.

As of 2026-10-12, AMD's current compatibility matrix does not list the
RX 6800 XT or Proxmox VE 9 as officially supported for ROCm. Therefore the
script must not be treated as permission to install ROCm on this target, and
the GPU compute stack remains gated. This is an explicit limitation, not a
claim that community-enabled ROCm configurations cannot work.

The script does not yet install ROCm/HIP, llama.cpp, ONNX Runtime ROCm EP,
ComfyUI, Qdrant, or production Quadlet/NGINX configuration. Those steps need
version pins and an install method verified for the actual host; do not
silently install floating latest releases on a Proxmox hypervisor.

The backend and Discord bot load project-root `.env` values with
`python-dotenv` when they start; shell-provided environment values take
precedence. The Windows `.bat` launchers do not source `.env` for their
llama.cpp command-line flags. See [configuration documentation](./configuration.md)
for the template and limitations.

## Recommended transition sequence

1. **Inventory and decision record:** document the Proxmox VE 9.x point
   release/kernel, host deployment choice, RX 6800 XT device, network
   exposure, storage, recovery method, and desired component versions. Do not
   begin ROCm installation until the exact target combination is checked
   against current upstream support information.
2. **Prepare the host safely:** establish console/SSH recovery, backups, and
   rollback; update the host using the chosen Proxmox procedure. Review an
   idempotent preflight/install plan before enabling package repositories,
   changing kernel/driver packages, or granting GPU device access.
3. **Validate the compute stack:** install a verified ROCm/HIP stack on the
   host and confirm the GPU is enumerated. Build llama.cpp with its ROCm
   backend; run a small-model inference through `llama-server`, then test
   Qwen2.5-Coder-7B and Qwen3-8B individually with VRAM headroom and
   repeatable prompts.
4. **Port and validate telemetry:** implement provider selection by platform,
   verify the API response schema is unchanged, and test idle/inference load
   and memory against an independent tool. Test missing permissions and
   missing telemetry utilities; the dashboard must show unavailable readings
   explicitly.
5. **Deploy supervised services:** configure model directory, runtime URL,
   exact device, backend environment, startup dependencies, logs, service
   account, and health checks. Validate model switching, startup failure,
   rollback to the previous model, and reboot recovery.
6. **Deploy the web interface safely:** choose same-origin proxy or a
   configured reachable API URL; test chat, model inventory, switching, and
   telemetry from both the host and a separate client. Keep llama.cpp
   loopback-only; restrict API reachability until authentication and network
   policy are in place.
7. **Deploy supporting services in stages:** install Podman/Quadlet and
   validate one unit at a time. Bring up NGINX and Qdrant with persistent
   storage and restricted network bindings. Add ONNX Runtime ROCm EP and
   ComfyUI in isolated, version-pinned environments/containers after
   compatibility checks; verify each against a representative workload.
   Deploy SearXNG and Discord only after their endpoint and secret handling
   are configured.
8. **Record operational handoff:** save exact versions, commands/build flags,
   service names, paths, environment variable names (not secret values),
   firewall/proxy design, GPU evidence, test results, backup/restore steps,
   and known limitations in this repository's deployment docs.

## Linux acceptance checklist

- [ ] Exact Proxmox VE 9.x point release/kernel and host deployment decision
      documented.
- [ ] RX 6800 XT driver/runtime combination verified against current upstream
      support and device enumerated by the chosen llama.cpp build.
- [ ] ROCm/HIP llama.cpp `llama-server`, ONNX Runtime ROCm EP, and ComfyUI
      versions/builds recorded; each installed component passes its own
      GPU-backed smoke test.
- [ ] Podman/Quadlet units survive restart/reboot with persistent data and
      least-privilege GPU access; NGINX and Qdrant expose only intended
      interfaces.
- [ ] Small-model inference and both 7B/8B models tested individually; logs
      confirm GPU offload and adequate VRAM headroom.
- [ ] `/api/system` returns valid CPU/RAM and live GPU fields; unavailable
      GPU measurements are `null`, with an explicit status/error.
- [ ] `/api/chat`, `/api/models`, model switching, and recovery tested after
      service restart and host reboot.
- [ ] Dashboard works from a separate client; API origin, proxy, CORS,
      authentication, firewall, and TLS decisions documented.
- [ ] llama.cpp remains loopback-only and only the intended services are
      reachable from approved networks.
- [ ] SearXNG, if deployed, returns JSON results; secrets are stored outside
      the repository.
- [ ] Backup/restore and recovery access verified; versions and known gaps
      recorded for handoff.

## Related documentation

- [GPU integration plan](./gpu-plan.md)
- [Windows testing environment](./testing-environment.md)
- [Architecture](./architecture.md)
- [Backend API](./api.md)
