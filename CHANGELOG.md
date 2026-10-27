# Changelog

Notable changes to the AI Command Interface are documented here.
This file follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
principles and [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Clarified that RX 6800 XT telemetry is collected on the Windows development
  machine using Windows performance counters, rather than implying the card
  is specific to Windows.
- Restructured the Network-Aware Diagnostics and Conversational Household
  Interface roadmap concepts to match the delegation-model format, clarifying
  objectives, AI responsibilities, design constraints, and unimplemented
  status. Expanded the conversational interface concept with an
  admin-managed shared display name for dashboard/conversational interfaces
  and a separate reviewable phonetic pronunciation for future voice
  invocation. Invocation will rely on the configured pronunciation; an
  optional generated suggestion may be reviewed or overridden, and a future
  test may report recognition confidence. The name and voice recognition do
  not establish identity, authentication, authorization, or privileges. No
  STT/TTS engine, phonetic standard, external pronunciation service, or
  implementation method is selected; the capability is not implemented.
- Restructured the Multi-GPU Workload Separation roadmap concept to match the
  same format, documenting the intended RX 6800 XT Maintenance AI role, the
  possible second User AI GPU, candidate tradeoffs, and validation status.
- Clarified workload roles: the RX 6800 XT is intended strictly for
  maintenance AI, while a possible second GPU would serve household-facing AI.
  Until a second card is selected and validated, the interim design remains
  single-GPU/single-runtime model handoff.
- Recorded the Radeon RX 7900 XT/XTX and RX 9070 XT as unselected second-GPU
  candidates, noting the VRAM-capacity versus RDNA 4 speed/efficiency tradeoff.
  The current one-GPU deployment plan is unchanged; no workload benchmark has
  selected or validated either candidate.
- Clarified the planned exclusive on-demand diagnostic handoff for household
  symptom reports: gate household inference, use an approved installed
  maintenance model on the single llama.cpp runtime, then restore the prior
  model after health checks. This is a design requirement only; no such
  household workflow is implemented.

### Added

- Added a **Household File Server / NAS** concept to the roadmap: an initial
  service using up to four SATA HDDs in RAID 5, with possible USB 3.1 or
  Ethernet-connected NAS expansion. RAID 5 is intended to increase usable
  capacity and tolerate a single drive failure, not replace backups; array
  expansion, backup/recovery, and connection behavior remain unselected and
  unvalidated.
- Added the **Household AI ↔ Maintenance AI Delegation Model** as a roadmap
  concept, defining the planned user-facing and operational-analysis roles,
  diagnostics requests, persisted findings, and audience-appropriate
  explanations. Delegated operation and runbook execution are not implemented.
- Added the **Shared Incident Reporting and Administrative Visibility**
  concept to the roadmap: attribute household-initiated diagnostics, expose
  findings and resolution history to authorized administrators, and keep
  Household AI explanations linked to shared operational records. This
  extends existing bounded incident history; the proposed household workflow
  and attribution are not implemented.

### In Development

- Retrieval of similar historical incidents, semantic/vector search, and
  model-assisted diagnostics.
- Image-generation backend groundwork and later runtime integration.
- Linux/Proxmox deployment, real-provider authentication, and HTTPS proxy
  validation on the target server.

## [0.7.0] - 2026-10-26

### Added

- Added `docs/project-context.md` as the primary project onboarding and AI
  session briefing, with current architecture, environment evidence,
  infrastructure, priorities, and validation boundaries.
- Updated the roadmap, deployment runbook, and project context to record the
  planned Z590 + Intel Core i9-11900KF server platform. The exact motherboard
  model and delivered physical hardware still require confirmation.
- Split the FastAPI routes into auth, chat, memory, research, and operations
  modules under `ai-backend/api/`, while preserving the `main:app` Uvicorn
  entry point. Updated backend and architecture documentation.
- Added Playwright browser regressions for dashboard module loading,
  authentication gating and failed sign-in, viewer/operator/admin controls,
  panel navigation, and persisted UI preferences. The tests exposed and fixed
  a CSS rule that allowed styled controls with the HTML `hidden` attribute to
  remain visible. The suite mocks API responses and does not validate backend
  authorization.
- Added a household network and future infrastructure reference covering the
  reported network topology, possible read-only telemetry, household voice
  concepts, managed-Wi-Fi evaluation, and a potential multi-GPU workload split.
  Current-state details are unverified; no related integrations or hardware
  changes are implied.
- Documented network-aware household diagnostics as an unscheduled concept,
  including infrastructure telemetry, WAN/LAN/Wi-Fi correlation, example
  connectivity reports, history, and observe-only/authorization boundaries.
  No network diagnostic workflow or telemetry provider is implemented.
- Documented a conversational household interface as an unscheduled concept,
  covering local speech-to-text/text-to-speech, maintenance and diagnostic
  updates, optional proactive notifications, and identity, privacy, and
  authorization boundaries. No voice interface is implemented.
- Documented a planned admin-driven, signed `.tar.gz` update flow for the
  backend/dashboard application, using prebuilt OCI images, a separate
  rootless updater, validation before explicit apply, health checks, and
  rollback. No updater or update UI/API has been implemented.
- Added a Linux AMD GPU telemetry provider using `amdgpu` sysfs utilization
  and VRAM counters, optional unambiguous hwmon sensors, and a platform
  dispatcher behind the existing API. Deterministic fixture tests cover
  missing/invalid counters and ambiguous adapters. This does not install or
  validate ROCm/HIP, and live Linux/physical-GPU readings remain unverified.
- Added portable tests for backend/dashboard Containerfile and Quadlet
  lifecycle/security contracts, plus coverage for container health-check
  outcomes. These tests do not execute Podman, systemd, or reboot recovery.
- Added a read-only Proxmox VM/container inventory endpoint and dashboard view,
  with backend-only API-token credentials, authenticated viewer access, explicit
  unavailable states, and no infrastructure-changing operations. The nested
  lab token returned one guest with the expected filtered fields, and temporary
  backend/dashboard startup, unauthenticated-route rejection, loopback binding,
  and stop checks passed on 2026-10-16. No persistent service or physical-host
  acceptance is implied.
- Added an opt-in, lab-only Proxmox CA compatibility setting that retains
  certificate-chain and hostname verification.
- Added bundled, versioned reviewed diagnostic runbooks with local lexical
  search, platform/signal filters, viewer-authorized list/detail/search routes,
  and no incident-history retrieval or procedure execution.
- Added deterministic in-memory maintenance/remediation simulations for safe
  stop, verification, rollback, and escalation paths; the simulations have no
  live system, service, shell, network, or Proxmox adapters.
- Added read-only Proxmox inventory and proposal-only VM, network-service, and
  game-server contracts with admin/confirmation boundaries and no mutation
  routes.
- Expanded manually triggered, observe-only diagnostics with backend-process
  and read-only SQLite integrity probes, persisted CPU/RAM/disk threshold
  evidence with duration confirmation and recovery hysteresis, and a
  viewer-readable JSON evidence-report endpoint with dashboard download.
- Added fault-injection coverage for threshold confirmation, oscillation,
  observation gaps, restart persistence, probe failures, read-only integrity
  checks, saved-report behavior, and report-route authorization.
- Historical evidence reports now reconstruct incident state from the selected
  observation instead of exposing later incident updates.
- Documented the nested Proxmox VE 9.1-1 guest as an active, additional
  deployment/integration lab, including its loopback/SSH-tunnel deployment
  boundaries and distinction from physical-server acceptance.
- Added a digest-pinned Python container image, Linux dependency lock, health
  probe, and rootless Podman/Quadlet definitions for the backend and dashboard.
  Nested-lab containers passed health, HTTP, loopback-binding, and anonymous
  route checks. A host-gateway alias was tested in a throwaway container and
  deployed for Proxmox API access without changing the TLS hostname; the live
  inventory request returned one guest from inside the backend container.
  Stop/start checks passed, and a controlled backend-container failure
  triggered a successful single systemd restart while the dashboard remained
  healthy and both services stayed loopback-only. The configured limit allowed
  three automatic restarts, blocked a fourth rapid failure, and manual reset
  restored the backend. A failed unavailable-image candidate was rolled back
  to a retained Quadlet/image snapshot; recovery passed, while rollback between
  distinct releases and boot/reboot recovery remain unverified.
- Documented a future, separate application deployment-installer scope for the
  existing rootless backend/dashboard stack, including read-only preflight,
  explicit confirmation, pinned artifacts, secret/config boundaries, health
  checks, and rollback. This is a plan only; no installer or automatic
  deployment behavior has been implemented.
- Clarified the diagnostics design to require a future admin-editable
  scheduled-maintenance setting for enablement, recurrence, start/end, and
  IANA timezone. Proposed environment values are defaults only; neither the
  setting nor live scheduled execution is implemented.
- Clarified the Network Services direction: future monitoring may include
  DHCP/DNS/routing services inside VMs, with an observe-only initial scope and
  no mutation or autonomous remediation until separate, explicit maturity and
  safety gates are met. No monitoring integration has been implemented.

### Fixed

- Ensured allowed dashboard origins receive CORS headers on early
  authentication and authorization errors, allowing the browser to read the
  server's 401/403 response. Added regression coverage; deployment to the
  nested Proxmox lab remains pending.

## [0.6.0] - 2026-10-14

### Added

- Split the admin-shared, single-transcript server console (AI Interface) from
  per-account private conversations and web research (AI Chat). The console
  stores attributed admin turns separately and does not load private chat
  history.
- Display the backend host name, detected GPU adapter, and selected local or
  web-research mode in the sidebar using live system telemetry and UI state;
  show DIAG during active observations and recognize MAINT only when an
  implemented maintenance lifecycle reports it.
- Persisted bounded observe-only diagnostics observations, incident state, and
  audit events to the local SQLite memory database. Open incidents are restored
  after restart; collection remains manually triggered, with no scheduler,
  commands, or remediation.
- Completed cited web research with limited public-page retrieval, DNS-pinned
  and redirect-validated fetches, HTML-only extraction, excerpt fallbacks,
  untrusted-page prompt boundaries, and SSE token streaming in AI Chat.
  Research source fetch status and citations persist with completed turns.
- Added opt-in HTTPS launchers for mobile LAN testing. They bind only to a
  configured private IPv4 address, require exact CORS and Secure-cookie
  settings, and serve only the dashboard's public assets; normal development
  launchers remain loopback-only.
- Kept the mobile dashboard header and chat composers within the viewport so
  conversation content scrolls independently on AI Interface and AI Chat.
- Kept the AI Interface shared-console badge beside its title on mobile and
  made the shared-console safety notice dismissible until page reload.
- Prevented the desktop sidebar-collapse control from shrinking the
  full-width navigation layout on phones in landscape orientation.
- Condensed mobile chat controls to leave more room for conversation history
  while keeping landscape controls horizontal, moving Research Web beside the
  input, and keeping Transmit inline in AI Chat and AI Interface.
- Reorganized System Monitor resource readings into a responsive grid of
  individual metric cards.
- Centered navigation icons in the collapsed desktop sidebar rail.
- Changed tablet navigation to a full-width grid in portrait and landscape;
  the header toggle now hides or restores the tablet navigation row.

### Changed

- Reorganized the roadmap to separate portable Windows-testable work,
  mocked integrations, Proxmox readiness, target-host deployment, and live
  server-dependent features. Clarified that Windows is the active build and
  prototype environment for shared application behavior, not just a mock;
  Proxmox-specific runtime behavior still requires target-host validation.

## [0.5.0] - 2026-10-14

### Added

- Added a separate admin-shared operational insight store. Admins explicitly
  publish and remove notes; private conversation transcripts remain isolated
  by account. Admin chat and research receive the signed-in admin identity and
  bounded published context, while operators and Discord service calls do
  not. The newest private chat resumes after sign-in; this is prompt-context
  retrieval, not model training.
- Added planning-only Virtual Machines and Network Services dashboard
  interfaces: an empty VM inventory with guest-detail and recovery-console
  states, plus DHCPv4/DHCPv6, DNS, web hosting, and routing/firewall service
  views. No live APIs or infrastructure controls are connected.
- Added explicit observe-only diagnostics from operator dashboard chat: direct
  run/check requests execute one observation and provide its evidence to the
  local model; informational questions and Discord bot requests do not trigger
  the action.
- Implemented dashboard-owned local accounts and Proxmox ticket login with
  explicit role mappings, persistent revocable server-side sessions,
  scrypt-hashed local passwords, role-gated REST/WebSocket routes, CSRF and
  origin checks, and login throttling. Added a host-local account/mapping CLI,
  authenticated login/logout UI, and a scoped Discord-bot bearer credential.
  Windows unit/mocked-provider validation does not replace target Proxmox,
  HTTPS proxy, or LAN exposure checks.
- Added account-scoped SQLite conversation history with saved-chat listing,
  resume and confirmed deletion, bounded recent-turn context for local chat,
  and persisted research citations. Bot API chat remains stateless; automatic
  fact extraction and semantic memory are not included.

### Changed

- Reduced the minimum password length for local dashboard accounts from 12
  to 8 characters; account creation and password resets use the same rule.
- Clarified that the Discord gateway `DISCORD_TOKEN` and the backend bearer
  `AI_SERVER_BOT_API_TOKEN` are distinct credentials, documented safe generation
  and environment precedence, and improved the bot startup error accordingly.
- Expanded the diagnostics design to define a staged path toward bounded
  autonomous repairs, using an incident history of evidence, user
  approval/denial feedback, attempted actions, and verified outcomes to inform
  similar future cases. Historical cases remain distinct from reviewed
  runbooks; neither feedback nor model confidence alone grants permissions.
- Added a phase-gated scheduled maintenance runbook with preflight, workload
  draining, diagnostic-model loading, authorized actions, verification,
  rollback, service restoration, and explicit failure escalation. It remains
  a design requirement, not a validated Proxmox procedure.
- Recorded provisional Proxmox host hardware and storage targets: AMD CPU,
  32 GB initial RAM with possible 64 GB, 2 TB initial NVMe with future
  expansion, HDD-backed bulk/lower-I/O workloads, model tiering, and an
  undecided redundant HDD layout. Exact parts and storage topology remain open.
- Split planned image-generation work across Phases 2 and 3: Phase 2 covers
  backend prompt-to-brief/API/job groundwork and metadata; Phase 3 covers
  image-runtime integration, Windows DirectML development, and experimental
  Proxmox ROCm/GPU validation.
- Added a Proxmox integration gate for the currently built dashboard, backend,
  model serving/switching, logging, optional research and Discord services,
  and observe-only diagnostics, with Linux, proxy, persistence, and recovery
  acceptance checks.
- Expanded planned infrastructure dashboards: full Proxmox VM lifecycle and
  guest-console access focused on guest recovery; DHCPv4/DHCPv6, DNS, web
  hosting, and routing/firewall; and a family Minecraft server as a candidate
  first game-server use case. Live management remains unimplemented.
- Reconciled project documentation to distinguish implemented Windows
  behavior from unverified Proxmox deployment and to clarify current API
  routing, model switching, authentication, diagnostics, and shared-memory
  status.

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
