# AI Command Interface

A local AI and homelab dashboard with a browser-based interface, FastAPI
backend, and optional Discord bot. Windows is the active build and prototype
environment for the server project. Shared application behavior is developed
and exercised here before deployment to the planned Linux/Proxmox host; only
OS-, hardware-, and deployment-specific parts are expected to need target
adjustments, with portability checked as the application is built.

## Project status

### Implemented and running in the Windows build environment

- Local chat through llama.cpp, with GPU inference on the RX 6800 XT.
- Installed GGUF model discovery and model switching from the dashboard.
  Switching restarts llama.cpp and confirms the new model is loaded.
- Live CPU and system RAM usage, plus Windows GPU load and dedicated VRAM
  telemetry.
- ONNX Runtime DirectML setup and a synthetic inference smoke test.
- Explicit web-research UI and backend integration for SearXNG.
- Streaming local chat over WebSocket, validated configuration, and rotating
  backend logs. Backend tests: `python -m unittest discover` in `ai-backend`
  (the test client is installed from `ai-backend/requirements-dev.txt`).
- Separate AI Interface and AI Chat panels. AI Interface is a single,
  persistent admin-shared server console transcript with attributed turns;
  private AI Chat history is never loaded into its context. AI Chat retains
  per-account private SQLite history with automatic resume of the latest
  conversation and bounded recent-turn context. Admins can separately publish
  operational notes to a curated shared store; only those approved notes are
  available across admin chat contexts. This is not transcript extraction,
  model training, or semantic retrieval.
- Dashboard polish: persistent dark/light theme, accent colour, collapsible
  sidebar, and panel transitions (Settings page and header toggle).

### Remaining work and target-specific validation

- Web research needs SearXNG running. On Windows it runs in WSL: install once
  with `wsl bash scripts/searxng/install-searxng.sh`, then start it with
  `run-searxng.bat`. A live SearXNG-to-llama.cpp smoke test of the new
  full-page/streaming path remains outstanding (see `docs/testing-environment.md`).
- Linux/Proxmox GPU telemetry and the production inference stack still need
  implementation and testing.
- Vision and image generation are not yet integrated with production models.
- VM and network-service panels have planning-only UI groundwork (empty VM
  inventory/recovery-console state and DHCPv4/DHCPv6/DNS/web/routing/firewall
  views); they are not connected to live services. Game-server management
  remains a planning view. The Discord page reports live bot heartbeats and
  operational logs and supports restart,
  command listing, and changing the active model shared with dashboard chat.
- Website-building assistance is planned, including workspace limits and
  approval before file changes or command execution.
- Dashboard login supports local accounts and explicitly mapped Proxmox
  identities, with revocable sessions and role-protected routes. Provision the
  first admin using the local CLI; Proxmox host/proxy security validation is
  still required before production deployment or broader LAN exposure. The
  opt-in HTTPS launchers allow trusted private-LAN testing; do not expose the
  backend to untrusted networks or the public internet. CORS is restricted to
  dashboard origins. Backend logs
  may contain operational details and are available only to authenticated
  administrators.
- AI diagnostics currently provide manually triggered, observe-only health
  checks with bounded SQLite-persisted observations, incidents, and audit
  events. The sidebar shows DIAG while an observation is running. The MAINT
  indicator awaits an implemented maintenance lifecycle; scheduling, semantic
  retrieval, and remediation are not implemented.

## Windows quick start

The Windows build environment uses Python 3.12. Its virtual environment and
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

For full dashboard testing on a phone over a trusted private Wi-Fi network,
use the opt-in HTTPS LAN launchers and certificate/firewall instructions in
the [testing guide](./docs/testing-environment.md#test-the-dashboard-from-a-mobile-device-on-the-lan).
The default launchers remain loopback-only.

## Planned deployment

The initial target is a Proxmox VE 9.x host with one AMD RX 6800 XT. The GPU
is currently in the Windows build machine and is intended to move to
the AI Server after a replacement GPU is acquired. The planned host stack is
ROCm/HIP, ROCm-built llama.cpp with `llama-server`, ONNX Runtime ROCm EP,
ComfyUI ROCm, Podman/Quadlet, NGINX, and Qdrant; ROCm/HIP is intended to be
installed on the Proxmox host. These are deployment targets, not installed or
validated target-host components. Most application and API behavior is
developed in the Windows prototype; GPU drivers/telemetry, Linux services,
permissions, networking, and production proxy behavior require
platform-specific integration and verification. AMD's published support
matrix currently does not list this GPU and Proxmox combination as officially
supported, so GPU
installation is experimental and requires compatibility checks and staged
verification on the actual Proxmox release, kernel, and component versions.
The GPU will be used directly by the Proxmox host; VM passthrough is not
planned. Community reports are leads only; see the
[GPU plan](./docs/gpu-plan.md#experimental-rx-6800-xt-community-evidence).

The initial host-preparation script is a preflight and optional base-tools
installer, not an inference-stack installer:

```bash
bash scripts/proxmox/prepare-ai-host.sh --check
sudo bash scripts/proxmox/prepare-ai-host.sh --install-base
sudo bash scripts/proxmox/prepare-ai-host.sh --install-searxng
```

`--check` inventories the host and checks AMD's live compatibility matrix
without changing the system. Use
`bash scripts/proxmox/prepare-ai-host.sh --report` on the server to generate a
private, redacted Markdown reference snapshot for implementation planning;
review it before sharing. The report stays local, though report generation
makes the same read-only request to AMD's public compatibility matrix as
`--check`. `--install-base` is limited to a detected Proxmox VE 9.x Debian
host, previews its apt plan, and refuses transactions that change kernel
packages. `--install-searxng` is also limited to that host.
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

When implementing changes, update the relevant API, subsystem, roadmap, and
project-status documentation in the same change. See [AGENTS.md](./AGENTS.md)
for the documentation reference checklist.

## Development Roadmap

### Phase 1 — Local Test Environment (Complete)
- ✅ Dashboard UI with panel navigation
- ✅ Backend API stubs and integration
- ✅ Discord bot foundation
- ✅ System monitor with live telemetry
- ✅ Chat interface with message history
- ✅ Model discovery and selection
- ✅ Operational logging

### Phase 2 — Portable Backend and Reliability
- ✅ Configuration, logging, WebSocket chat, and account authentication
- ✅ Private SQLite conversations and explicitly shared admin notes
- ✅ Observe-only diagnostics with persistent bounded SQLite incident history
- ✅ Cited web research with bounded, SSRF-resistant page retrieval and
  Server-Sent Event answer streaming; unit and API tests cover fetch controls

### Phase 3 — Mocked Integrations and Portable Features
- Define typed contracts and mock providers for VM, network, and game-server
  workflows; no live infrastructure controls
- Build workspace-restricted agents and approval workflows
- Implement model-agnostic image-brief/job groundwork; add reviewed diagnostic
  retrieval, deterministic mocked repair validation, and maintenance
  lifecycle simulations
- See [AI Diagnostics Documentation](./docs/ai-diagnostics-self-healing.md)

### Phase 4 — Proxmox Readiness and Compatibility Gate
- Finalize host, network, storage, backup, recovery, and service decisions
- Check exact Proxmox/kernel/GPU/runtime compatibility; RX 6800 XT ROCm remains
  experimental and is not established by Windows Vulkan results
- Pin deployment versions and review installation, security, and rollback
  plans before touching the host

### Phase 5 — Target-Host Deployment and Core Integration (Server required)
- Validate Linux dependencies, services, GPU telemetry, inference, storage,
  permissions, restart/reboot recovery, and the production proxy
- Validate real Proxmox identity mapping, HTTPS cookies, firewall, and separate
  LAN-client access; keep the backend private until these checks pass
- Follow the [Linux/Proxmox transition runbook](./docs/linux-proxmox-transition.md)

### Phase 6 — Live Server-Dependent Product Integrations
- Integrate ONNX Runtime ROCm and ComfyUI after target-host stability
- Add live Proxmox VM/console, network services, and game-server management
  only after permissions, isolation, and recovery are validated
- Evaluate multi-model/multi-GPU use against a measured stable baseline
- Enable real maintenance actions only with tested authorization and rollback

### Phase 7 — Polish
- ✅ UI animations and transitions
- ✅ Theme switching (dark/light modes)
- ✅ Responsive layout; mobile LAN access and certificate trust verified on a
  phone, with full real-device layout and interaction testing still pending
- ✅ Collapsible sidebar navigation
- Keep broader real-device and deployed-environment interaction testing
  outstanding

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
