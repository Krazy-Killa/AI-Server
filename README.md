# AI Command Interface

A local AI and homelab dashboard with a browser-based interface, FastAPI
backend, and optional Discord bot. This project is being developed and tested
on Windows before deployment to a dedicated Linux/Proxmox server.

## Project status

### Working in the Windows test environment

- Local chat through llama.cpp, with GPU inference on the RX 6800 XT.
- Installed GGUF model discovery and model switching from the dashboard.
  Switching restarts llama.cpp and confirms the new model is loaded.
- Live CPU and system RAM usage, plus Windows GPU load and dedicated VRAM
  telemetry.
- ONNX Runtime DirectML setup and a synthetic inference smoke test.
- Explicit web-research UI and backend integration for SearXNG.
- User authentication with local accounts and optional Proxmox identity integration.
- Private conversation history per user with shared admin notes.
- Observe-only diagnostics and incident tracking with SQLite persistence,
  reviewed local runbook search, and disconnected maintenance/remediation test
  simulations.
- Read-only Proxmox VM/container inventory, verified against the nested lab's
  API token, plus proposal-only infrastructure contracts with no live mutation
  support. Rootless Podman/Quadlet backend and dashboard containers are active
  in the nested lab with loopback-only ports and passing health checks; their
  host-gateway mapping was verified with a live in-container Proxmox inventory
  read. Stop/start, controlled restart/limit behavior, and recovery from an
  unavailable deployment candidate were verified against a retained snapshot;
  rollback between distinct releases, boot/reboot recovery, and physical-host
  acceptance remain outstanding.

### Not yet operational

- SearXNG must be installed and configured before web research can search.
- Linux/Proxmox GPU telemetry and the production inference stack still need
  implementation and testing.
- Vision and image generation are not yet integrated with production models.
- Game-server and network-service panels remain planning views. The Discord
  page reports live bot heartbeats and operational logs and supports restart,
  command listing, and changing the active model shared with dashboard chat.
- Website-building assistance is planned, including workspace limits and
  approval before file changes or command execution.
- Live remediation and scheduled maintenance (Phase 2); only disconnected
  deterministic simulation flows are implemented.
- Advanced diagnostics with ML-based anomaly detection (Phase 3+).

## Windows quick start

The Windows test environment uses Python 3.12. Its virtual environment and
llama.cpp build/model files are kept outside the OneDrive project folder,
under `%LOCALAPPDATA%\AI-Server`.

1. Copy `.env.example` to `.env` and adjust settings for this machine. The
   backend and optional Discord bot load the project-root `.env`; the local
   file is ignored by Git. Never add credentials to `.env.example`.
2. Run `setup-windows.bat` from the project root.
3. Download the Qwen2.5 1.5B Instruct GGUF as described in
   [the testing guide](./docs/testing-environment.md).
4. Start `run-llama-server.bat` and leave it running.
5. In separate terminals, run `run-backend.bat` and `run-dashboard.bat`.
6. To start the optional Discord bot, run `run-discord-bot.bat` after
   configuring `DISCORD_TOKEN` in `.env`.
7. Open `http://127.0.0.1:8001`.

The backend listens on `http://127.0.0.1:8000`; llama.cpp listens on
`http://127.0.0.1:8080`. Use the dashboard's model dropdown or a model card to
switch among installed GGUFs. Switching interrupts active inference while
llama.cpp restarts.

## Planned deployment

The initial target is a Proxmox VE 9.x host with one AMD RX 6800 XT. The GPU
is currently in the Windows development machine and is intended to move to
the AI Server after a replacement GPU is acquired. The planned host stack is
ROCm/HIP, ROCm-built llama.cpp with `llama-server`, ONNX Runtime ROCm EP,
ComfyUI ROCm, Podman/Quadlet, NGINX, and Qdrant; ROCm/HIP is intended to be
installed on the Proxmox host. These are deployment targets, not installed or
validated server components. AMD's published support matrix currently does
not list this GPU and Proxmox combination as officially supported, so GPU
installation remains gated on compatibility verification for the actual
Proxmox release, kernel, and component versions.

The initial host-preparation script is a preflight and optional base-tools
installer, not an inference-stack installer:

```bash
bash scripts/proxmox/prepare-ai-host.sh --check
sudo bash scripts/proxmox/prepare-ai-host.sh --install-base
```

`--check` inventories the host and checks AMD's live compatibility matrix
without changing the system. `--install-base` is limited to a detected
Proxmox VE 9.x Debian host, previews its apt plan, and refuses transactions
that change kernel packages. Review the plan before confirming it, and use
the script only on the eventual server. It does not install ROCm/HIP or
configure the inference services. Linux GPU runtimes and telemetry still need
to be selected and validated; Windows DirectML is for development tests, not
the Linux deployment backend.

## Project layout

```text
ai-backend/       FastAPI API, local chat, telemetry, and research integration
ai-discord-bot/   Optional Discord bot client
css/              Dashboard styles
docs/             Setup, API, architecture, and project plans
js/               Dashboard behavior
index.html        Dashboard interface
```

## Documentation

- [Windows testing environment](./docs/testing-environment.md)
- [Configuration and secrets](./docs/configuration.md)
- [Project overview](./docs/overview.md)
- [Architecture](./docs/architecture.md)
- [Backend API](./docs/api.md)
- [Backend](./docs/backend.md)
- [Frontend](./docs/frontend.md)
- [GPU integration plan](./docs/gpu-plan.md)
- [Linux/Proxmox transition runbook](./docs/linux-proxmox-transition.md)
- [**Comprehensive Development Roadmap**](./docs/roadmap.md) — Detailed implementation phases, current status, and future plans
- [Authentication & Session Management](./docs/authentication.md) — JWT-based auth system with local accounts and Proxmox integration
- [AI Diagnostics & Self-Healing System](./docs/ai-diagnostics-self-healing.md) — Monitoring, diagnostics, and auto-remediation framework
