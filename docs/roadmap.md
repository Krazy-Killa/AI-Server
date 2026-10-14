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

All remaining work is directed toward the planned Proxmox server. Proxmox VE
9.1-1 is running as a nested Hyper-V guest on the Windows PC and is available
as an additional Linux/Proxmox deployment and integration environment. The
dashboard and backend have been deployed there for loopback-only testing over
an SSH tunnel; this is a manually started lab deployment, not a persistent or
production service setup. Use the guest to prepare and test suitable
OS/API/deployment work before the physical server is available. It does not
validate the physical host's hardware, GPU/ROCm, storage/network topology,
sustained performance, or recovery behavior. Windows remains the active
shared-application build environment, not the deployment target.

- **Pre-physical-server work:** use portable contracts, deterministic tests,
  and the nested Proxmox lab for Proxmox API, permissions,
  VM workflows, and Linux service/deployment integration. Identify all lab
  results as nested-lab evidence, not physical-server acceptance.
- **Server-gated:** requires the actual Proxmox release, kernel, GPU, network,
  service manager, installed services, or production proxy. Schedule it in
  Phase 5 or later; do not mark it done based on Windows, mocks, or nested-lab
  success where the physical server is required.
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
  incidents and pending threshold evidence restore on backend restart.
  Collection remains explicitly triggered and read-only. The expanded checks
  include backend process state and a read-only SQLite integrity probe;
  resource thresholds use duration confirmation, bounded observation gaps,
  and recovery hysteresis. Viewer-readable evidence reports summarize the
  selected saved observation, including incident state/evidence at that time,
  without running probes.
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

### Done — interface groundwork and read-only inventory implementation

- Virtual Machines panel has a read-only Proxmox VM/container inventory
  provider, authenticated viewer-level API route, and refreshable UI. The
  integration is implemented, covered by mocked tests, and connected to the
  nested Proxmox lab with its dedicated read-only token. A live query returned
  a populated guest list, verifying rendering; physical-host acceptance remains
  outstanding. No VM management or console controls are exposed.
- Network Services panel has planning-only views for DHCPv4, DHCPv6, DNS, web
  hosting, and routing/firewall. Service ownership, scopes, and configuration
  remain undecided; no backend or network changes are connected.

### Pre-physical-server work — portable and nested-lab eligible

- Prepare reviewed diagnostic runbooks and local retrieval tests. Keep
  incident-derived runbooks and curated knowledge as untrusted drafts until
  reviewed; retain incident records separately as evidence.
- Use the nested Proxmox lab to exercise Proxmox API
  authentication/permissions, VM lifecycle contracts, deployment scripts, and
  Linux service integration where the guest environment supports the feature.
  Record nested virtualization and lab-specific limitations.
- Define structured remediation proposals and validate them with a separate
  deterministic mocked executor. Do not connect the mock to live actions or
  grant model output authority.
- Simulate maintenance lifecycles with mocked clocks and service providers.
  Use simulations to test policy and failure paths only; do not enable
  scheduling or claim host recovery.
- Build the workspace-restricted website agent with explicit approval
  boundaries. Keep its file/command integrations disabled until permissions
  and recovery are validated for the target deployment.
- Define model-agnostic image job contracts and validate prompt intent,
  revisions, approval state, and reproducibility metadata. Do not prioritize a
  Windows-only runtime as a deployment deliverable.
- Define portable GPU telemetry interfaces and unavailable/error behavior;
  generic fixtures can test contracts but cannot validate the target GPU.
- Define Proxmox-oriented VM, network-service, and game-server contracts,
  authorization boundaries, and failure-state UI. Defer live VM controls
  until Phase 6 and until ownership, isolation, and recovery are validated.

## Phase 4 — Proxmox Readiness and Compatibility Gate

This phase closes decisions and preflight work, but does not claim the target
host has been integrated. Hardware-dependent conclusions remain unverified
until checked against the actual machine.

### In progress / waiting on target details

- Finalize the planned host specification and deployment inputs: intended
  Proxmox point release, CPU/GPU, boot mode, network topology, storage layout,
  recovery method, and service placement. Confirm these against the delivered
  server and installed OS in Phase 5; do not treat plans as verified inventory.
- Current provisional sizing: AMD CPU not yet selected, 32 GB system RAM with
  a possible 64 GB upgrade, 2 TB initial NVMe, and HDD-backed bulk/lower-I/O
  workloads. Confirm CPU/core count and actual memory needs against Proxmox,
  planned VMs, inference, and concurrent services before purchase.
- Select the storage topology: HDD count, RAID/ZFS layout, controller mode,
  usable capacity, and expansion plan are undecided. Redundancy is not a
  backup; plan a separate backup and test restoration. Consider NVMe for
  databases, active VM disks, and frequently used model files; model tiering
  improves load/switch time, not inference speed after model load.
- Research compatibility for the intended Proxmox release, RX 6800 XT,
  ROCm/HIP, and application versions. Confirm the installed Proxmox release
  and running kernel, and re-check compatibility on-host in Phase 5. AMD does
  not list the planned GPU/Proxmox combination as officially supported;
  community reports are leads, not proof. GPU passthrough is not planned.
  Follow the staged recovery and acceptance requirements in the
  [GPU plan](./gpu-plan.md).
- Select pinned versions, host-vs-container boundaries, persistent paths,
  service accounts, least-privilege GPU access, firewall policy, TLS/proxy
  design, secrets handling, and rollback procedures before installation.

### Gate to begin deployment

- Planned hardware, intended Proxmox release, and recovery method are
  documented; actual host inventory and recovery access must be confirmed
  before deployment on the delivered server.
- Storage, backup/restore, service, and network plans are reviewed.
- Experimental GPU risk is explicitly accepted or GPU-dependent features are
  deferred.
- Deployment steps are pinned, reviewed, and have a recovery path. Source-level
  review of the host-preparation script can happen pre-host; do not treat its
  `--check`, installer, or report modes as validated until run on the target.
  The script does not install ROCm or the inference stack.

## Phase 5 — Physical Target-Host Deployment and Core Integration

**Waiting for the physical Proxmox server.** The nested Hyper-V Proxmox
installation is a development lab only. Do not mark physical-host acceptance
complete from Windows runs, mocks, or nested-lab results.

- Record the actual host inventory, installed Proxmox release/running kernel,
  and recovery access. Validate the host-preparation script's `--check`,
  `--report`, and reviewed installer modes on that host, then install only
  reviewed prerequisites.
- Build and validate ROCm/HIP and ROCm llama.cpp/`llama-server` for the exact
  host; record device identity, build flags, versions, and smoke-test results.
  This remains experimental for the planned RX 6800 XT/Proxmox combination.
- Integrate the Linux telemetry provider with the actual GPU and validate
  adapter identity, utilization, and VRAM against a host tool during idle and
  inference. Return unavailable/null if the deployed source cannot provide
  trustworthy readings.
- Validate the observe-only resource threshold defaults under representative
  Proxmox server workloads, including inference and integrated-service
  activity. Measure false-alert rates, persistence across explicit sampling
  gaps, and recovery hysteresis before adopting production values. Collection
  must remain explicitly triggered; do not enable automatic execution as part
  of validation. Windows and generic Linux/CI results are not Proxmox
  acceptance evidence.
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

## Forward-work summary

The next tasks are Phase 3 portable contracts, reviewed retrieval/runbooks,
deterministic simulations, and Proxmox-oriented UI/provider work. Exercise
suitable API, permissions, VM workflow, deployment-script, and Linux service
work in the available nested Proxmox VE 9.1-1 lab. Record results as nested-lab
validation and document limitations; do not substitute Windows-only runtimes
for the planned Proxmox stack.

Once the physical server is available, confirm the installed host inventory
and complete the Phase 4 readiness gate, then execute Phase 5 physical-host
validation in controlled steps. This includes threshold validation under
representative server workloads, GPU/ROCm telemetry, service and reboot
recovery, and production authentication/proxy/network checks. Phase 6 live
product integrations remain gated on physical Phase 5 stability, access
control, and recovery. Keep the production backend local-only until
HTTPS/proxy behavior, firewall/network controls, and deployment have been
validated on the physical target.

## Documentation References

- [Authentication & Session Management](./authentication.md) — design and implementation guide
- [AI Diagnostics & Self-Healing System](./ai-diagnostics-self-healing.md) — design specification
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) — system components and data flow
- [Configuration Guide](./configuration.md) — environment variables and settings
- [Backend Documentation](./backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) — dashboard UI and JavaScript structure
