# Changelog

Notable changes to the AI Command Interface are documented here.
This file follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
principles and [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-10-14

### Added

- Documented RX 6800 XT ROCm/HIP on Proxmox as experimental and added
  community references for related `gfx1030` Linux compute reports and an
  RX 6800 XT llama.cpp guide, with explicit scope and verification caveats.
  Clarified direct host GPU use (no VM passthrough) in deployment docs and
  removed passthrough-specific fields from the host reference report.
- `prepare-ai-host.sh --report [FILE]` creates an owner-readable,
  privacy-conscious Markdown snapshot of selected Proxmox host, hardware,
  driver, package, service, and compatibility-check facts. It is local-only,
  refuses to overwrite an existing file, and excludes hostnames, network
  addresses, serial numbers, credentials, configuration contents, and logs.
- Initial observe-only diagnostics core in `ai-backend/diagnostics.py`:
  bounded local service health probes, CPU/RAM/disk/backend RSS sampling,
  observation evidence, process-local incident open/update/recovery tracking,
  and bounded audit events. Added bounded `/api/diagnostics/*` read endpoints,
  explicit `POST /api/diagnostics/observe`, and a manual-run dashboard status
  and incident view. No scheduler or remediation is enabled.
- Read-only backend log viewer at `/api/backend/logs` and in the dashboard.
  The API returns at most 500 recent lines; the panel shows the latest 200,
  supports manual refresh, and auto-refreshes only while open.
- Proxmox authentication groundwork: HTTPS ticket client with redirect
  rejection, typed auth/authorization interfaces, mocked API-response tests,
  and a disabled dashboard sign-in preview. No login endpoint or application
  session management is enabled.
- Phase 5 polish: persistent dark/light theme toggle, collapsible icon-only
  sidebar, panel fade-in animation, and persisted accent colour (also fixes
  accent glows not following the chosen colour). Preferences are stored in
  `localStorage` under `ai-server-ui-prefs`.
- Validated backend configuration loader (`ai-backend/config.py`); invalid
  settings now stop startup with a message naming the variable. New settings
  cover timeouts, token and message limits, CORS origins, and logging.
- Backend logging to the console and a rotating `backend.log`, with request
  logging (polled status endpoints at DEBUG only; chat text is not logged).
- WebSocket chat streaming at `/ws/chat`. The dashboard shows replies as they
  are generated and falls back to `/api/chat` if streaming cannot start.
  Closing the connection stops generation. Web research is not streamed.
- Tests for the configuration loader, streaming client, and WebSocket endpoint.
- SearXNG setup for the Windows test environment: `scripts/searxng/` installer,
  run script and settings template (loopback-only, JSON enabled), plus
  `run-searxng.bat`. It runs in WSL on a private Python 3.12 via `uv`, since
  SearXNG needs Python 3.11+ and does not support native Windows.
- `.gitattributes` keeping shell scripts and YAML on LF line endings.
- `prepare-ai-host.sh --install-searxng`: installs SearXNG on the Proxmox VE 9.x
  host as an unprivileged `searxng` user with a hardened systemd service on
  `127.0.0.1:8888`, then verifies the JSON search API. Not subject to the ROCm
  gate. Untested on a real Proxmox host; refusal outside Proxmox was verified.

- Recorded multi-GPU inference as a future evaluation item for the Linux/
  Proxmox server, including model splitting versus per-GPU instances and
  benchmarking requirements.
- Recorded the intended Proxmox host stack—ROCm/HIP, ROCm-built llama.cpp
  `llama-server`, ONNX Runtime ROCm EP, ComfyUI ROCm, Podman/Quadlet, NGINX,
  and Qdrant—in the transition and GPU plans.
- Recorded Proxmox VE 9.x and one RX 6800 XT as the planned initial server
  target; point release, kernel, and component versions remain to be verified.
- Recorded the decision to install ROCm/HIP on the Proxmox host, pending
  compatibility verification for its exact kernel and GPU.
- Added a Proxmox host-preparation script with live ROCm compatibility checks,
  kernel-aware prerequisite planning, and safeguards against kernel changes.
  Its read-only preflight and optional base-tools setup are not a full inference
  stack installer; ROCm and GPU-dependent components remain gated pending
  compatibility verification on the actual Proxmox release, kernel, and GPU.

### Changed

- CORS now allows only the configured dashboard origins (default
  `http://127.0.0.1:8001` and `http://localhost:8001`) instead of all origins.
  Set `AI_SERVER_CORS_ORIGINS` if the dashboard is served from another origin.
- Model-switch options, SearXNG URL, and llama.cpp settings now come from the
  central configuration loader; the chat token limit is configurable.
- Added `websockets` to the backend requirements; run
  `pip install -r ai-backend/requirements.txt` to update an existing environment.
- Documented that the preparation script requires a positively detected
  Proxmox VE 9.x Debian host for package setup, previews the apt plan, and
  refuses plans that change kernel packages. Corrected its Proxmox version
  parsing and initialized the planned GPU detection before the compatibility
  check.

## [0.3.0] - 2026-10-12

### Added

- Linux/Proxmox transition runbook covering platform decisions, portability
  gaps, deployment configuration, service/security requirements, and
  acceptance checks.
- Root `.gitignore`, local `.env`, and shareable `.env.example` configuration
  template; backend and Discord bot load project-root `.env` settings.
- Configuration documentation describing supported environment variables
  and the current launcher/API-origin limitations.
- Windows Discord bot launcher and corrected `/models` and `/selectmodel`
  slash commands for the current model inventory and selection API.
- Natural-language replies to direct Discord mentions, routed through the
  local AI chat backend.
- Discord Bot page controls for live status and latency, activity logs,
  registered slash commands, bot restart, and switching the active model
  shared with dashboard chat.

### Changed

- Linked the transition runbook from the README, GPU plan, backend docs, and
  architecture overview; clarified Linux GPU support is not implemented.
- Replaced simulated Discord bot status and logs with heartbeat-reported
  runtime data and bounded operational logs.
- Made dashboard restart requests restart the running bot process and report
  success after it reconnects.
- Enabled Discord Message Content Intent for direct-mention handling; it must
  also be enabled in the Discord Developer Portal.

### Fixed

- Connected the Discord Bot page's previously inactive controls to the backend
  APIs, including command listing and shared active-model selection.

## [0.2.0] - 2026-10-12

### Added

- Connected dashboard chat to a local llama.cpp server using Vulkan on Windows.
- Added discovery of installed GGUF models and live loaded-model status.
- Added model switching from the chat dropdown and model cards. The backend
  validates the server process, restarts it for the selected model, confirms
  the new model is loaded, and attempts to restore the prior model on failure.
- Added Windows GPU load and dedicated VRAM telemetry, plus live CPU and
  system RAM readings in the Host Monitor.
- Added explicit web-research mode using SearXNG, with source links in
  responses. SearXNG must be installed and configured before searches work.
- Added Windows setup and launch scripts, including an ONNX Runtime DirectML
  smoke test.
- Documented the Windows test environment, model setup, API, architecture,
  GPU plans, and Linux/Proxmox deployment considerations.
- Added focused backend tests for model switching and web research.

### Changed

- Updated the Models page and AI Interface dropdown to reflect the GGUF files
  installed on the test machine.
- Updated project documentation and the README to describe the current
  Windows test setup and distinguish working features from planned deployment
  work.

### Fixed

- Replaced simulated GPU load, VRAM, and Host Monitor RAM values with live
  readings; unavailable GPU telemetry is reported as unavailable rather than
  presented as a simulated measurement.
- Removed stale setup instructions and unresolved merge-conflict markers from
  the README.

### Model test assets

- Qwen2.5 1.5B Instruct Q4_K_M — used for dashboard chat testing.
- Stories15M Q4_0 — installed smoke-test model.
- Qwen3-8B Q4_K_M and Qwen2.5-Coder-7B-Instruct Q4_K_M — each passed a short
  Vulkan inference test with GPU layer offload on the RX 6800 XT.

### Known limitations

- SearXNG is not yet installed or configured.
- Linux/Proxmox GPU telemetry and production GPU runtime support remain future
  work; Windows DirectML testing does not establish Linux deployment support.
- Vision and image-generation integrations are not yet connected to production
  models. VM, game-server, and network-service panels are planning views, and
  Discord bot status/logs remain placeholders.

## [0.1.0] — Initial Commit

### Added

- Initial project structure, FastAPI backend, dashboard UI, and Discord bot
  connection logic.
- Placeholder endpoints and GPU/LLM stubs for development.
- Initial documentation, dashboard navigation and panels, model cards,
  system-monitor bars, chat layout, backend status indicator, and theme
  swatches.
