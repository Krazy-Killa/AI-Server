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

### Not yet operational

- SearXNG must be installed and configured before web research can search.
- Linux/Proxmox GPU telemetry and the production inference stack still need
  implementation and testing.
- Vision and image generation are not yet integrated with production models.
- VM, game-server, and network-service panels are planning views. The Discord
  page reports live bot heartbeats and operational logs and supports restart,
  command listing, and changing the active model shared with dashboard chat.
- Website-building assistance is planned, including workspace limits and
  approval before file changes or command execution.

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

The RX 6800 XT is currently in the Windows development machine and is intended
to move to the AI Server after a replacement GPU is acquired. The server is
planned to run Linux under Proxmox, with the dashboard, backend, and AI
runtime running on the host. Windows DirectML is for development tests, not
the Linux deployment backend; Linux GPU runtimes and telemetry still need to
be selected and validated.

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
- [Roadmap](./docs/roadmap.md)
