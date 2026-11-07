# Changelog

Notable changes to the AI Command Interface are documented here.
This file follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
principles and [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Added a searchable documentation website and GitHub Pages deployment workflow.
- Expanded Settings → About with the current dashboard release, a concise
  capability overview, privacy and operational-boundary notes, and links to
  the source repository, documentation, and release notes.
- Moved the AI Chat model selector into the panel header and added a live
  Household AI readiness tile based on local runtime availability and loaded
  model state.
- Added four System Health Trends line charts for GPU load, VRAM, CPU, and RAM.
  They sample every 10 seconds and retain up to one hour in the current page
  session only; history resets on reload and is not persisted. Renamed the
  navigation item to System Monitor to match the panel title.
- Added server-side filtering of `<think>` blocks in standard and streaming
  model replies, with legacy assistant history sanitized before display and
  model reuse.

### Changed

- Moved the collapsed Shared Admin Knowledge manager from private AI Chat to
  the admin-shared AI Interface, reducing chat-panel clutter while preserving
  the existing note and context behavior. Not yet deployed.
- Removed the inert TEMP slider from AI Chat. Sampling remains at the backend's
  fixed `0.7` until a real temperature preference is implemented. Not yet
  deployed.

### Fixed

- Windows model switching now handles `psutil` reporting PID 0 for the
  listening socket by resolving the matching owner row, while preserving
  executable/port/model verification before stopping llama.cpp. Covered by
  model-manager tests.
- Diagnostics report download in the iOS Home Screen app now uses the native
  file-sharing sheet when supported, avoiding the unreliable Blob URL
  `download` behavior there. Browsers without file-sharing support keep the
  regular download flow. Covered by frontend tests; not yet deployed to the
  lab.

### In Development

- Maintenance AI Context Inference Layer: request-scoped platform state and
  historical operational retrieval for grounded responses. Planned for future
  development at medium-high priority; historical-case retrieval,
  semantic/vector search, and model-assisted diagnosis remain unimplemented.
- Image-generation backend groundwork and later runtime integration.
- Linux/Proxmox deployment, real-provider authentication, and HTTPS proxy
  validation on the target server.
- Single-GPU inference architecture plan: keep Qwen2.5 1.5B Utility AI
  resident while Household mode uses Qwen3 8B or Maintenance mode uses
  Qwen2.5 Coder 7B. Profile routing, co-resident serving, and VRAM/RAM
  feasibility are design work only; implementation and hardware validation
  remain outstanding.
- Future dual-GPU service-separation concept: the planned RX 6800 XT Operations
  GPU serves Utility and Maintenance AI, while an unselected second GPU serves
  Household AI. The RX 9070 XT and RX 9090 XT (or equivalent future flagship)
  remain candidates; concurrent operation and hardware compatibility are not
  implemented or validated.
- Separate signed model-package workflow for installing large model weights
  into persistent storage without coupling them to application updates or
  rollback; planned, not implemented.
- Signed updater follow-up: lab verification of tampered/wrong-key rejection,
  expiry purge, and a large upload through NGINX; Stage 2 apply and the
  privileged updater are not started.

## [0.9.2] - 2026-11-05

Deployed to the nested Proxmox lab as release `20261106-updater-verify`.
Stage 1 verification was tested with one signed bundle; see the runbook for
the exact scope and remaining lab checks.

### Added

- Signed release-bundle **Stage 1 (verify-only)**: admin-only `.aibundle`
  upload, Ed25519 signature and payload verification, hostile-archive checks,
  staging, listing, and discard; includes the signing tool
  `scripts/release/sign-release.py`, a dedicated NGINX upload location, and
  `cryptography` as a pinned dependency. The dashboard displayed the verified
  signer, payload digest, size, and expiry for a signed test bundle; Apply
  remains disabled. The operator reported that Discard appeared to work.
  Tampered/wrong-key rejection, expiry purge, and a large upload through NGINX
  have not yet been verified on the lab. Stage 2 apply is not implemented.

### Changed

- Restyled the Virtual Machines inventory table: consistent type scale, more
  padding and row separators, hover state, monospace VMID/node, and
  colour-coded power-state, connection, and inventory status pills. On phones,
  stat tiles display two per row, guest details use two-column cards, and the
  header places the status pill beside Refresh. Covered by a Playwright test;
  the on-device appearance was not separately recorded.

## [0.9.1] - 2026-11-05

Deployed to the nested Proxmox lab as release `20261106-nonblocking`.

### Fixed

- `/api/system` sampled CPU usage on the event loop, freezing the whole backend
  for 0.5 s per request. With two dashboards open (each polls it twice), sign-in
  and other requests stalled, so the login form could hang on "Signing in…".
  The sample now runs in a worker thread, with a regression test. On the lab,
  30 consecutive requests to the backend returned in 1-3 ms afterwards.
- Lab container health confirmed: both containers `healthy`, units `active`
  with no restarts, probe endpoints returning 200. Documented that
  `podman healthcheck run` / `podman exec` through `runuser` fail with a cgroup
  permission error and must not be used to judge health.

## [0.9.0] - 2026-11-05

Deployed to the nested Proxmox lab as release `20261106-frontend`. Asset
serving, the new Content-Security-Policy, and the 404/401 behavior were checked
over HTTPS. The shared-address lockout fix was confirmed on the lab: failed
sign-ins from an iPhone hit the readable "Too many login attempts" message
without locking the administrator out on a desktop. iPhone home-screen
install was confirmed afterwards: the app icon appears once full trust is
enabled for the lab certificate authority in iOS Certificate Trust Settings
(until then iOS silently falls back to a letter icon).

### Added

- Self-hosted web fonts (no Google Fonts dependency; CSP no longer allows
  third-party origins), a web-app manifest and home-screen icons, a banner
  shown when the backend is unreachable, and a stacked Diagnostics header on
  phones.
- Polling timers pause while the browser tab is hidden.
- Settings is now a tabbed page (Appearance, Account, Network & Access, Models,
  Diagnostics, About) with an admin-only Setup / Deployment tab containing a
  disabled Firmware File placeholder for the planned release-bundle updater.
  Browser regression tests cover tab switching, keyboard navigation, and
  role gating.
- Settings → Account shows the signed-in identity and a Sign out button, so
  phones (where the sidebar footer is hidden) can sign out. Chat's
  "cannot reach llama.cpp" error no longer refers to a Windows batch file.
- Login rate limiting is now correct behind the NGINX proxy. A new opt-in
  `AI_SERVER_TRUST_PROXY_HEADERS` setting makes the backend use the proxy's
  `X-Forwarded-For` client address. Before this, every LAN device appeared as
  one address, so five failed sign-ins from one device locked out everyone.
  The login throttle in NGINX also returns JSON now, and the dashboard shows
  a readable message instead of Safari's "string did not match the expected
  pattern".
- LAN access: an NGINX TLS reverse-proxy configuration
  (`deploy/nginx/ai-server.conf`) and a local-CA certificate generator
  (`scripts/proxmox/make-lan-cert.sh`) with name constraints, both in the lab
  bundle and covered by contract tests. Installed on the nested lab and
  verified from a Windows PC and an iPhone; the `/ws/chat` connection works
  through the proxy (streaming untested without llama.cpp), and the client
  address seen behind the proxy is correct once
  `AI_SERVER_TRUST_PROXY_HEADERS=true` is set (lab-tested).

### Fixed

- The header and System card CPU values were hardcoded at 18%; they now show
  live data or N/A. A stale VRAM overwrite that could print "null / nullGB"
  was removed.
- Small mobile labels are larger and text fields no longer trigger iOS zoom.

## [0.8.0] - 2026-11-05

### Security

- Dashboard static servers now send a restrictive Content-Security-Policy,
  `X-Frame-Options: DENY`, and related headers. A new
  `ai-backend/dashboard_server.py` replaces `python -m http.server` in the
  Quadlet dashboard unit and `run-dashboard.bat`, serves only the dashboard
  assets, and disables directory listings; the inline theme script moved to
  `js/theme-init.js`. Verified by unit tests and the Playwright suite; the lab
  container has not been rebuilt, and HSTS/TLS headers remain a proxy task.
- Proxmox dashboard login now rejects accounts whose ticket response signals a
  pending second factor (`NeedTFA` or a `PVE:!tfa!` ticket) instead of
  creating a session from the password alone. Covered by mocked tests only.
- The interactive API docs and schema are now off by default; see Added.

### Fixed

- Fixed `.env` not being loaded by the backend since the routes moved into the
  `api/` package: `api/runtime.py` looked in `ai-backend/` instead of the
  project root, so database paths, Proxmox settings, and other `.env` values
  silently fell back to defaults. In the nested lab this made the redeployed
  backend use empty databases. Covered by new tests; redeployed to the nested
  lab as `20261105-dotenv`, where the backend now resolves its `.env` paths and
  both containers are healthy.
- The Containerfile did not copy the backend `api/` and `api/routes/` packages,
  so an image built from it failed at startup with `ModuleNotFoundError: No
  module named 'api'` (reproduced by simulating the image contents; the likely
  cause of the failed 2026-10-19 lab deployment, not confirmed against that
  image). It now copies both, and a contract test fails if any backend package
  directory is not copied. LF line endings are now pinned for the Containerfile,
  `.containerignore`, Quadlet units, and lock files.

### Changed

- Removed 19 committed `.pyc` bytecode files from Git tracking; the existing
  `.gitignore` rules already cover them, and the files remain on disk.
- Added high-level `README.md` guides to the documentation subfolders that
  lacked them and linked those summaries from the documentation index.
- Renamed folder-matching documentation files in `docs/` to `README.md` and
  updated references to the new paths.
- Clarified the ROCm/Proxmox compatibility assessment: Linux-kernel and
  Debian-related common ground make testing plausible, but do not establish
  low risk or AMD support for Proxmox; the exact host, driver, ROCm, container,
  and inference combination remains to be validated.
- Audited the full roadmap for structural consistency: documented the `Partial`
  and `Concept` status meanings, separated Phase 2 planned behavior from
  completed work, aligned candidate-backlog concept labels and implementation
  status sections, clarified the NAS concept against the undecided host
  storage plan, and removed conflicting Phase 3 priority wording.
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

- Added an opt-in boot auto-start path (Quadlet drop-ins under
  `deploy/boot-autostart/`; base units remain manual-start) and an optional
  post-boot housekeeping timer (`deploy/systemd/`,
  `scripts/proxmox/ai-server-housekeeping.sh`) that prunes build directories
  and build logs older than 7 days only when both containers are healthy.
  The lab release procedure now writes build logs to an `ai-server`-owned
  path. Unit-tested and the script exercised in WSL with a stub `podman`.
  Installed on the nested guest; a clean reboot recovered both containers to
  healthy without a manual start, as did a forced guest power-off (SQLite
  integrity checks passed). The first timer-driven cleanup run is not
  yet observed.
- Disabled the interactive API docs and schema (`/docs`, `/redoc`,
  `/openapi.json`) by default; they now return 404 unless
  `AI_SERVER_ENABLE_API_DOCS=true` is set for local development. The Quadlet
  backend health probe now uses `GET /`. Covered by new unit tests; not yet
  deployed to the nested lab.
- Added `scripts/proxmox/build-lab-bundle.py` (allow-listed, LF-normalized lab
  release bundle) and a written manual lab release procedure with an import
  gate before switching services and an explicit rollback block, in the
  Linux/Proxmox runbook. Executed on the nested lab on 2026-11-05: build,
  import gate, and switch succeeded (nested-lab evidence only); `/docs`,
  `/redoc`, and `/openapi.json` return 404, the dashboard sends CSP and
  `X-Frame-Options: DENY`, and ports 8000/8001 stay bound to `127.0.0.1`.
- Ran an unauthenticated read-only loopback smoke check on the nested guest:
  32 protected routes returned 401 anonymously, login enforced the `Origin`
  check, and both ports were bound to `127.0.0.1`. Found that the lab dashboard
  still lacks the CSP headers (image not rebuilt) and that `/docs`, `/redoc`,
  and `/openapi.json` are publicly readable. Nested-lab evidence only.
- Ran `prepare-ai-host.sh --check` and `--report` on the nested Proxmox VE 9.1.1
  guest as the non-root `ai-deploy` account. Both were read-only; `--check`
  exited 2 with the ROCm gate `blocked` as designed, and `--report` wrote an
  owner-only report. Nested-lab evidence only; installer modes and physical-host
  runs are still pending. Fixed a cosmetic `MemTotal::` double-colon label in
  the `--report` memory section and re-verified it on the guest.
- Recorded the 2026-11-04 live Windows browser smoke test: local
  Qwen2.5 1.5B chat and Research Web through WSL SearXNG to llama.cpp both
  returned successfully, with source links in the research response. Kept the
  result scoped to Windows/WSL rather than Proxmox or physical-host acceptance.
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
