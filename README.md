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
- Streaming local chat over WebSocket, validated configuration, and rotating
  backend logs. Backend tests: `python -m unittest discover` in `ai-backend`
  (the WebSocket tests need `httpx`).
- Dashboard polish: persistent dark/light theme, accent colour, collapsible
  sidebar, and panel transitions (Settings page and header toggle).

### Not yet operational

- Web research needs SearXNG running. On Windows it runs in WSL: install once
  with `wsl bash scripts/searxng/install-searxng.sh`, then start it with
  `run-searxng.bat` (see `docs/testing-environment.md`).
- Linux/Proxmox GPU telemetry and the production inference stack still need
  implementation and testing.
- Vision and image generation are not yet integrated with production models.
- VM, game-server, and network-service panels are planning views. The Discord
  page reports live bot heartbeats and operational logs and supports restart,
  command listing, and changing the active model shared with dashboard chat.
- Website-building assistance is planned, including workspace limits and
  approval before file changes or command execution.
- Authentication and user session management (designed, planned for Phase 2).
  CORS is restricted to the dashboard origins, but there is no login yet, so
  do not expose the backend beyond this machine.
- AI-powered diagnostics and self-healing (design specification only, planned
  for Phase 3).

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
sudo bash scripts/proxmox/prepare-ai-host.sh --install-searxng
```

`--check` inventories the host and checks AMD's live compatibility matrix
without changing the system. `--install-base` is limited to a detected
Proxmox VE 9.x Debian host, previews its apt plan, and refuses transactions
that change kernel packages. `--install-searxng` is also limited to that host.
It installs SearXNG for dashboard web research as an unprivileged `searxng`
user with a systemd service on `127.0.0.1:8888`, then verifies a JSON search.
It does not depend on the GPU, so the ROCm gate does not block it. Review the
plans before confirming them, and use the script only on the eventual server.
It does not install ROCm/HIP or configure the inference services. Linux GPU
runtimes and telemetry still need
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

## Development Roadmap

### Phase 1 — Local Test Environment (Complete)
- ✅ Dashboard UI with panel navigation
- ✅ Backend API stubs and integration
- ✅ Discord bot foundation
- ✅ System monitor with live telemetry
- ✅ Chat interface with message history
- ✅ Model discovery and selection
- ✅ Operational logging

### Phase 2 — Real Backend Features
- Linux/Proxmox deployment preparation (preflight and base-tools script done)
- SearXNG setup (Windows test setup done; Proxmox mode written, untested)
- Linux GPU telemetry integration
- ✅ Logging system (no backend log viewer in the dashboard yet)
- ✅ Configuration management and restricted CORS/WebSocket origins
- ✅ WebSocket streaming for local chat
- **JWT-based Authentication & Session Management** (not yet implemented)
  - Secure user login/logout
  - Token refresh mechanism
  - Protected API endpoints
  - Frontend login page
  - Rate limiting and security hardening
  - See [Authentication Documentation](./docs/authentication.md)

### Phase 3 — GPU Integration
- llama.cpp Vulkan support (Windows testing complete)
- ROCm/HIP stack for Proxmox
- ONNX Runtime GPU acceleration
- ComfyUI integration
- Container orchestration (Podman/Quadlet)
- NGINX reverse proxy setup
- Vector storage (Qdrant)
- **AI Diagnostics & Self-Healing System** (design specification only)
  - Real-time health monitoring and anomaly detection
  - Diagnostic engine for root cause analysis
  - Auto-remediation for safe operations
  - Error reporting and escalation workflows
  - Knowledge base of troubleshooting procedures
  - Audit logging and approval gates
  - See [AI Diagnostics Documentation](./docs/ai-diagnostics-self-healing.md)

### Phase 4 — Advanced Features
- Cited web research through self-hosted SearXNG
- Website-building agent with approval workflows
- Multi-model routing and load balancing
- Multi-GPU inference strategies
- Advanced agent workflows
- VM management integration
- Remote server control
- Discord bot automation
- **Advanced AI Diagnostics**
  - Machine learning-based anomaly detection
  - Self-learning knowledge base updates
  - Predictive issue detection
  - Cross-service dependency analysis

### Phase 5 — Polish
- ✅ UI animations and transitions
- ✅ Theme switching (dark/light modes)
- ✅ Mobile-responsive layout (real-device testing pending)
- ✅ Collapsible sidebar navigation

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
- [Authentication & Session Management](./docs/authentication.md)
- [AI Diagnostics & Self-Healing System](./docs/ai-diagnostics-self-healing.md)
- [Roadmap](./docs/roadmap.md)
