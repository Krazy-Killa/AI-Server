# Linux/Proxmox Transition Runbook

## Purpose and status

This runbook records what can move from the Windows test environment, what
must be implemented or decided for Linux, and the checks required before the
AI Server is considered operational. It is a preparation guide, not evidence
that Linux/Proxmox deployment has already been tested.

The current target is a Proxmox host running the dashboard web server, FastAPI
backend, and AI runtime directly on the host. The RX 6800 XT is currently in
the Windows development machine and is planned to move to the server after a
replacement GPU is acquired. Whether Proxmox VE itself or a host-managed
Linux installation will run these services is not yet settled; record that
choice before installing GPU drivers.

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

1. **Choose and record the operating-system layout.** Decide whether services
   run directly on the Proxmox VE host or on a Linux guest. The current design
   calls for host execution; putting AI in a guest changes GPU access and
   telemetry requirements. Record Proxmox/Linux versions, kernel, boot mode,
   GPU ownership, storage locations, and recovery access before driver work.
2. **Verify the GPU software stack for the exact target.** Check the current
   official AMD ROCm support matrix for the selected distribution, kernel,
   RX 6800 XT, and required runtime. Then choose/build llama.cpp accordingly
   (for example, ROCm/HIP or Vulkan if verified) and record the pinned
   llama.cpp revision, build flags, device name, and smoke-test results.
   Windows Vulkan test results do not certify the Linux build.
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
   Windows. Add Linux setup/start/stop procedures or service units for the
   model server, backend, and dashboard/reverse proxy. Use a dedicated
   service account, explicit environment files, controlled restart ordering,
   persistent logs, and clear health checks. Ensure the backend can inspect
   and stop only its own llama.cpp process when model switching.
7. **Set Linux paths and permissions.** Configure `AI_SERVER_MODEL_DIR` and
   `LLAMA_SERVER_EXECUTABLE`; ensure the service account can read model files,
   write its logs, and access the selected GPU device. Keep models and
   llama.cpp build artifacts outside the source checkout and back them up or
   document how to reacquire them.
8. **Select Linux-specific AI packages separately.** Windows DirectML packages
   in `ai-backend/requirements-windows.txt` and
   `ai-discord-bot/requirements-windows.txt` are not the Linux install path.
   Install only the common `requirements.txt` dependencies first. Select and
   validate Linux vision and image-generation runtimes/models separately;
   neither is currently a production integration.
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

The backend and Discord bot load project-root `.env` values with
`python-dotenv` when they start; shell-provided environment values take
precedence. The Windows `.bat` launchers do not source `.env` for their
llama.cpp command-line flags. See [configuration documentation](./configuration.md)
for the template and limitations.

## Recommended transition sequence

1. **Inventory and decision record:** document host/guest choice, exact OS and
   kernel, GPU device ownership, network exposure, storage, and rollback
   method. Do not begin ROCm installation until the exact target combination
   is checked against current upstream support information.
2. **Build a clean Linux test environment:** deploy the chosen OS, apply
   updates, establish SSH/console recovery, install Python and the common
   backend requirements in an isolated virtual environment, and verify the
   API can start without Windows-only dependencies.
3. **Validate GPU access before application setup:** confirm the host sees the
   RX 6800 XT, install only a verified driver/runtime, build llama.cpp, record
   available devices, and run a short inference test on a small model. Then
   test Qwen2.5-Coder-7B and Qwen3-8B individually with VRAM headroom and
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
7. **Add optional services one at a time:** deploy SearXNG and verify cited
   search results; add Discord only after token handling and remote API access
   are configured. Vision and image-generation work gets its own runtime and
   acceptance tests.
8. **Record operational handoff:** save exact versions, commands/build flags,
   service names, paths, environment variable names (not secret values),
   firewall/proxy design, GPU evidence, test results, backup/restore steps,
   and known limitations in this repository's deployment docs.

## Linux acceptance checklist

- [ ] Exact Proxmox/OS/kernel and host-versus-guest decision documented.
- [ ] RX 6800 XT driver/runtime combination verified against current upstream
      support and device enumerated by the chosen llama.cpp build.
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
