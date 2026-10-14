# Project Roadmap

## Status key

- **Done (Windows prototype)** — implemented and verified in the active
  Windows build environment, or with focused mocks where noted. This counts as
  project implementation for shared behavior; it does not imply target-host
  validation for OS-, hardware-, network-, or service-specific behavior.
- **In progress** — implementation is actively underway.
- **Not started** — planned, but implementation has not begun.
- **Experimental / waiting for server** — unsupported-by-vendor work that
  depends on the Proxmox host, its kernel, or the production hardware; staged
  investigation is possible, but runtime validation is still required.

Dashboard-owned login/session management and per-account SQLite conversation
history are implemented and verified in the Windows build/prototype
environment. Windows is the active server-development environment, not merely
a disposable mock: shared application and API behavior is built here, then
carried forward to Proxmox, with the expectation that most changes will be
limited to platform-specific integration. Verify portability through tests;
do not assume it solely from the language or framework.
Explicitly curated, admin-only shared operational notes are also implemented.
AI Chat transcripts remain private to each account. The AI Interface is a
separate, single admin-shared operational transcript with attributed turns;
its context does not load private AI Chat history.
Proxmox-host and HTTPS-proxy validation remain outstanding. The dashboard,
Windows backend foundation, operational logging, and interface polish are
implemented. Transcript history is separate from diagnostic incident history
and retrieval; automatic fact extraction and model training from conversations
are not implemented. Observe-only diagnostics and persistent incident history
are implemented locally; reviewed retrieval and production-host integration
remain outstanding. The production Linux/Proxmox stack is unvalidated.

## Sequencing and portability rule

Work is ordered by what can be implemented and verified in the Windows
prototype, then by what requires the actual Proxmox host. Windows is the build
environment for the shared server application, not a disposable mock.
Implement shared application behavior there and carry it forward; use explicit
provider boundaries, configuration, and platform-specific adapters to isolate
Linux/GPU/service differences. A mocked Proxmox response proves the client
contract, not real authentication, service behavior, GPU compatibility,
networking, or recovery.
Prefer environment-driven paths and settings, keep platform-specific imports
behind narrow providers, and preserve shared API behavior with cross-platform
tests. Windows tests and generic Linux/WSL CI can catch portability defects,
but cannot certify Proxmox, GPU, proxy, or service-manager behavior.

- **Windows prototype:** implement and test shared APIs, schemas,
  authorization, UI states, SQLite behavior, and policies against the working
  local services. Treat this as real project development, while identifying
  the operating-system and deployment assumptions.
- **Cross-platform/mocked:** test common behavior on generic Linux/WSL/CI and
  use fake providers or simulated clocks/services for unavailable dependencies.
  Label these checks as simulations; they increase portability confidence but
  do not certify Proxmox operation.
- **Server-gated:** requires the actual Proxmox release, kernel, GPU, network,
  service manager, or production proxy. Do not mark it done based on Windows
  success or mocks.
- **Post-integration:** enable live operations only after their target-host
  integration, permissions, and recovery path are tested.

## Phase 1 — Local Test Environment

**Status: Done**

- Dashboard UI and panel navigation
- FastAPI backend foundation
- Discord bot foundation
- System monitoring in the Windows test environment
- Local chat interface and model discovery/switching
- Operational logging

## Phase 2 — Portable Backend and Reliability

### Done

- Validated configuration loader
- Console and rotating-file backend logging
- WebSocket streaming for local chat
- CORS and WebSocket origin restrictions for configured dashboard origins
- Windows SearXNG test setup and dashboard web-research integration
- Cited web research with bounded public-page retrieval, explicit excerpt
  fallback status, and authenticated SSE streaming. Focused unit/API tests
  pass; a live SearXNG/llama.cpp end-to-end smoke test remains unverified.
- Dashboard-owned authentication: local and mapped Proxmox login, persistent
  revocable sessions, role authorization, protected REST/WebSocket routes,
  CSRF and origin checks, login throttling, CLI account/mapping management,
  and browser login/logout flow. Windows and mocked-provider tests pass;
  actual Proxmox/proxy validation is server-gated.
- Proxmox authentication interface and HTTPS ticket client with mocked
  responses. These tests establish client behavior, not real-provider
  integration.
- Per-account conversational history: isolated SQLite storage, saved-chat
  listing/resume/delete, and bounded recent-turn context for the local chat
  model. Bot API requests remain stateless. This does not implement automatic
  fact extraction, semantic/vector retrieval, or the separate diagnostics
  RAG system. History is retained locally until its owner deletes it.
- Admin shared insight memory: each note must be explicitly published by an
  admin; any admin can read or remove it. Admin identity and a bounded set of
  approved notes are supplied to AI Chat and research. Private account
  transcripts are not shared, scraped, or used for model training. The newest
  private AI Chat conversation resumes at sign-in.
- AI Interface: a single persistent admin-shared operational transcript with
  authenticated admin attribution, separate from AI Chat history. Server-side
  authorization limits it to admins. Only explicitly requested read-only
  diagnostics can run; general server command execution and maintenance are
  not implemented.
- Read-only `GET /api/backend/logs` endpoint and dashboard panel: configurable
  tail bounded to 500 lines, defaults to the latest 200; manual refresh and
  five-second auto-refresh only while open. Access is admin-only.
- Persistent, bounded observe-only diagnostics: observations, incident
  state/transitions, and audit events in the local SQLite database; open
  incidents restore on backend restart. Collection is explicit and read-only.
- Optional HTTPS launchers for whole-dashboard testing from a mobile device
  on a trusted private LAN. They bind to one configured private IPv4 address
  and serve only public UI assets. Phone certificate trust and dashboard access
  have been verified on the local device; firewall rules were not changed.
  Mobile chat panels keep the header and composer visible while conversation
  content scrolls; the AI Interface console badge stays beside its title, and
  its safety notice can be dismissed until reload. Short landscape layouts
  (600px high or less) retain compact horizontal navigation without a sidebar
  toggle.
  Portrait chat controls are condensed; short landscape layouts keep the
  controls horizontal, place Research Web beside the input, and trim vertical
  spacing to reserve conversation space, with Transmit beside the message field.
- System Monitor telemetry is arranged in a responsive two-column metric grid,
  collapsing to one column on very narrow screens; values still use the
  existing telemetry update flow.
- Collapsed desktop sidebar navigation icons are centered within the narrow
  rail.
- Tablet navigation uses a full-width grid, with six columns in landscape and
  four in portrait; the header toggle hides or restores the navigation row to
  preserve active-panel space when requested.

## Phase 3 — Mocked Integrations and Portable Feature Work

### Done — interface groundwork

- Virtual Machines panel has a planning-only empty inventory, guest-details
  layout, and unavailable recovery-console state; it has no provider or live
  management controls.
- Network Services panel has planning-only views for DHCPv4, DHCPv6, DNS, web
  hosting, and routing/firewall. Service ownership, scopes, and configuration
  remain undecided; no backend or network changes are connected.

### Next — continue implementation in the Windows prototype

- Continue observe-only diagnostics with broader health checks, explicit
  threshold durations/hysteresis, evidence reports, and fault-injection tests.
  Keep collection and interpretation observe-only; no automatic execution.
- Build local retrieval over reviewed diagnostic procedures and similar
  incidents, with source and outcome metadata. Prior cases are evidence, not
  trusted procedures; incident-derived runbooks remain drafts until reviewed.
- Define structured repair proposals and validate them using a separate
  deterministic mocked executor. The model must not execute commands, grant
  itself authority, or change policy.
- Simulate scheduled maintenance using mocked clocks, model/service providers,
  and fault injection. The sidebar MAINT state must be driven by a real active
  lifecycle, which is not implemented yet. Treat simulations as lifecycle
  testing only; they do not prove host recovery or authorize deployment.
- Build the workspace-restricted website agent with explicit approval before
  file changes or command execution.
- Implement the model-agnostic image brief/job contract and metadata before
  integrating an image runtime.
- Add contract and validation tests for prompt intent preservation, editable
  revisions, approval state, and reproducibility metadata.
- Prototype Windows image-runtime integration behind the image provider
  interface where useful. Treat DirectML results as Windows-only; keep the
  API/job contract and application behavior runtime-independent.
- Define a shared GPU telemetry provider contract and Linux-provider
  unavailable/error behavior with fixtures or generic Linux CI. Do not report
  simulated measurements or claim the actual GPU is validated.
- Define typed contracts, authorization boundaries, mock providers, and
  failure-state UI for VM/network/game-server workflows. Define DHCP/DNS/
  routing ownership, isolation, and recovery before any live control.

## Phase 4 — Proxmox Readiness and Compatibility Gate

This phase closes decisions and preflight work, but does not claim the target
host has been integrated. Hardware-dependent conclusions remain unverified
until checked against the actual machine.

### In progress / waiting on target details

- Finalize the host inventory: exact Proxmox point release/kernel, boot mode,
  GPU ownership, network topology, storage devices/layout, recovery access,
  and service placement. The initial host-preparation script's `--check`,
  `--install-base`, `--install-searxng`, and private `--report` modes exist;
  validate their behavior on the actual Proxmox host before relying on them.
- Current provisional sizing: AMD CPU not yet selected, 32 GB system RAM with
  a possible 64 GB upgrade, 2 TB initial NVMe, and HDD-backed bulk/lower-I/O
  workloads. Confirm CPU/core count and actual memory needs against Proxmox,
  planned VMs, inference, and concurrent services before purchase.
- Select the storage topology: HDD count, RAID/ZFS layout, controller mode,
  usable capacity, and expansion plan are undecided. Redundancy is not a
  backup; plan a separate backup and test restoration. Consider NVMe for
  databases, active VM disks, and frequently used model files; model tiering
  improves load/switch time, not inference speed after model load.
- Check current compatibility for the exact Proxmox release, running kernel,
  RX 6800 XT, ROCm/HIP, and application versions. AMD does not list the
  planned GPU/Proxmox combination as officially supported; community reports
  are leads, not proof. GPU passthrough is not planned. Follow the staged
  recovery and acceptance requirements in the [GPU plan](./gpu-plan.md).
- Select pinned versions, host-vs-container boundaries, persistent paths,
  service accounts, least-privilege GPU access, firewall policy, TLS/proxy
  design, secrets handling, and rollback procedures before installation.

### Gate to begin deployment

- Actual host inventory and recovery method are recorded.
- Storage, backup/restore, service, and network plans are reviewed.
- Experimental GPU risk is explicitly accepted or GPU-dependent features are
  deferred.
- Deployment steps are pinned, reviewed, and have a recovery path. The host
  preparation script does not install ROCm or the inference stack.

## Phase 5 — Target-Host Deployment and Core Integration

**Waiting for the Proxmox server.** Do not mark complete from Windows runs,
mocked authentication, or generic Linux tests alone.

- Validate the host-preparation script and install only reviewed prerequisites.
- Build and validate ROCm/HIP and ROCm llama.cpp/`llama-server` for the exact
  host; record device identity, build flags, versions, and smoke-test results.
  This remains experimental for the planned RX 6800 XT/Proxmox combination.
- Integrate the Linux telemetry provider with the actual GPU and validate
  adapter identity, utilization, and VRAM against a host tool during idle and
  inference. Return unavailable/null if the deployed source cannot provide
  trustworthy readings.
- Create Linux service management using Podman/Quadlet or systemd as
  appropriate. Cover the backend, llama-server, NGINX, SearXNG, and only
  runtimes that are actually integrated; use persistent paths, health checks,
  least privilege, startup ordering, and controlled restart/recovery.
- Validate dashboard-owned and real Proxmox login, role mapping, cookies,
  CSRF/origin checks, HTTPS reverse proxy, firewall rules, and browser access
  from a separate LAN client. Keep the API and inference service private until
  this gate passes. See [authentication.md](./authentication.md).
- Integrate the existing dashboard, backend, model discovery/switching, chat
  and streaming, SQLite history, logging, optional research/bot, and
  observe-only diagnostics. Verify Linux dependencies, permissions, service
  recovery, proxy/WebSocket routing, and host reboot using the
  [Linux/Proxmox transition runbook](./linux-proxmox-transition.md).
- Validate real maintenance pause/restore/recovery against deployed services
  only after the mocked lifecycle is complete. Keep the control plane and
  recovery path available; fault-inject every gate. Host, kernel, firmware,
  and GPU driver/ROCm updates remain approval-only.

## Phase 6 — Live Server-Dependent Product Integrations

Begin only after Phase 5 core stability, access control, and recovery have
been demonstrated on the target host.

- Integrate ONNX Runtime ROCm and ComfyUI ROCm. Validate model load, GPU
  offload, VRAM/RAM headroom, latency, output quality, and failure recovery.
- Connect VM lifecycle and guest console using least-privilege Proxmox API
  permissions, server-side authorization, bounded operations, explicit
  confirmation for destructive actions, task/audit history, and tested guest
  recovery.
- Connect DHCPv4/DHCPv6, DNS, web hosting, and routing/firewall only after
  service ownership, scopes, segmentation, and out-of-band recovery are
  defined. Network changes must not make the AI host the sole unprotected
  network edge or strand the dashboard.
- Integrate the selected game-server manager; start with the family Minecraft
  use case only after edition/version, isolation, resource limits, allowlists,
  backups, world restore, and family-safety requirements are settled.
- Evaluate multi-model and multi-GPU routing against a measured single-GPU
  baseline; compare compatibility, VRAM, throughput, latency, power, and
  stability before enabling concurrent workloads.
- Enable any real repair or scheduled maintenance actions only after
  independent executor validation, per-action policy/approval, audit evidence,
  and tested rollback. Model output or prior user feedback never grants
  authority.

## Phase 7 — Polish

### Done

- Panel fade-in and sidebar transition; reduced-motion preference respected
- Persistent dark/light theme
- Responsive compact header and scrolling navigation on layouts 760px wide or
  less, or 600px high or less
- Persistent collapsible icon-only desktop sidebar
- Persistent accent-colour selection

### Not started

- Full real-device mobile layout and interaction testing; HTTPS LAN access and
  certificate trust have been verified on the phone, but broader device and
  interaction coverage remains outstanding

## Suggested next work (in the Windows prototype)

Continue shared application implementation and test it in the Windows
prototype. Isolate target-specific components behind providers and use mocks
only where the actual service/hardware is not available. Keep a separate
acceptance gate for real Proxmox deployment.

Model recommendations below are advisory and describe roles, not requirements
for a particular editor or agent platform. Use GPT Luna for implementation and
focused tests; use Claude Sonnet as an additional design/safety reviewer for
changes involving diagnostics, remediation, scheduling, or security. Re-check
the current model options when starting each task.

1. Expand the persistent observe-only diagnostics evidence: broaden checks,
   define threshold duration/hysteresis behavior, produce evidence reports,
   and add fault-injection tests. Keep observation explicitly triggered and
   non-remediating.
   **Models:** GPT Luna for implementation and tests; Claude Sonnet for
   reviewing thresholds, failure handling, and observe-only boundaries.
2. Create reviewed diagnostic runbooks and local RAG/retrieval tests. Keep
   incident-derived runbooks and curated knowledge as untrusted drafts until
   reviewed; retain incident records separately for evidence-based retrieval.
   **Models:** Claude Sonnet for runbook structure and retrieval/evaluation
   design; GPT Luna for ingestion code, tests, and integration.
3. Define structured remediation proposals and independently validate them in
   a mocked executor; enforce risk tiers, approval gates, and audit logging.
   **Models:** Claude Sonnet for proposal-schema and safety-boundary review;
   GPT Luna for the mocked executor, validation, and tests.
4. Prototype and test scheduled maintenance with a mocked clock, model
   manager, workload controller, update source, and recovery path. Treat this
   as simulation only until the Proxmox host is available.
   **Models:** Claude Sonnet for lifecycle and failure-mode review; GPT Luna
   for the simulation and deterministic tests.
5. Build the workspace-restricted website agent with explicit approval for
   changes and command execution.
   **Models:** GPT Luna for implementation and tests; Claude Sonnet for
   reviewing workspace isolation, approvals, and command-execution boundaries.
6. Define backend contracts and read-only/mock providers for the VM and
   Network Services UI groundwork, then add the Game Servers dashboard.
   Define the Proxmox VM lifecycle and guest-console boundary,
   DHCPv4/DHCPv6/DNS/web/routing-firewall service inventory and safety states,
   and a family Minecraft server as a candidate first game-server workflow.
   Defer live management actions until a Proxmox host, network architecture,
   game-server manager, authentication, and recovery path are selected and
   validated.
   **Models:** GPT Luna for schemas, UI, and mock-provider tests; Claude Sonnet
   for reviewing Proxmox permissions, network lockout risks, guest isolation,
   and recovery assumptions.

Next server-gated milestone: execute Phase 4's compatibility/readiness gate
against the actual hardware, then proceed through Phase 5 in controlled steps.
Production authentication/session validation, LAN exposure, Linux GPU
telemetry, and service/maintenance recovery remain gated on that host.
Dashboard authentication and protected routes are implemented locally; the
optional Windows LAN test mode is not production deployment. Keep the
production backend local-only until HTTPS/proxy behavior, firewall/network
controls, and the complete deployment have been validated.

## Documentation References

- [Authentication & Session Management](./authentication.md) — design and implementation guide
- [AI Diagnostics & Self-Healing System](./ai-diagnostics-self-healing.md) — design specification
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) — system components and data flow
- [Configuration Guide](./configuration.md) — environment variables and settings
- [Backend Documentation](./backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) — dashboard UI and JavaScript structure
