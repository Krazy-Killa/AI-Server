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
are implemented locally. A reviewed, local lexical runbook-retrieval prototype
and disconnected maintenance/remediation simulations are also implemented;
semantic/vector retrieval and live remediation remain outstanding. The
production Linux/Proxmox stack is unvalidated.

## Sequencing and portability rule

All remaining work is directed toward the planned Proxmox server. Proxmox VE
9.1-1 is running as a nested Hyper-V guest on the Windows PC and is available
as an additional Linux/Proxmox deployment and integration environment. The
dashboard and backend are installed there for loopback-only lab testing.
Transient service startup and stop were verified on 2026-10-16. Rootless
Podman/Quadlet backend and dashboard containers have since been built and are
currently active and healthy on loopback, but are not configured for boot
auto-start. The backend's host-gateway hostname mapping is deployed; a live
inventory call from the backend container returned one guest with the expected
fields. Use the guest to prepare and test suitable OS/API/deployment work
before the physical server is available. It does not validate the physical
host's hardware, GPU/ROCm, storage/network topology, sustained performance, or
recovery behavior. Windows remains the active shared-application build
environment, not the deployment target.

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
  and browser login/logout flow. Windows and mocked-provider tests pass. A
  real Proxmox identity was mapped to the viewer role and authenticated in the
  nested lab; viewer reads succeeded and higher-role access was denied.
  Middleware ordering was corrected so allowed dashboard origins can read
  authorization errors, and the backend suite passes. A lab image update
  attempt was rolled back after the backend did not remain reachable; API
  health recovered, but the cause was not isolated and the fix is not
  currently deployed. Physical-server and HTTPS-proxy validation remain
  outstanding.
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
- **Planned — admin-configurable scheduled maintenance window:** add an
  admin-only Diagnostics/Maintenance setting for enablement, recurrence days,
  start/end time, and explicit IANA timezone. Show the configured timezone and
  next scheduled window, validate and audit changes, and define persistence
  and activation semantics. The proposed environment values are defaults,
  not the admin UI. Keep scheduling disabled and do not execute maintenance
  until the setting, scheduler, and target lifecycle are separately validated.
  See the [AI Diagnostics & Self-Healing design](./ai-diagnostics-self-healing.md).
- **Network services autonomy policy:** keep future DHCP/DNS/web/routing and
  firewall integrations observe-only by default, whether services run on the
  Proxmox host or inside VMs. Do not expose mutation endpoints or automated
  remediation in the initial monitoring integration. Any later move to
  limited AI-assisted action must be a separate admin-authorized phase with
  explicit per-action boundaries, audit evidence, verification, and tested
  rollback/out-of-band recovery. Full autonomy is a distinct later gate; the
  AI must never promote its own authority or infer permission from successful
  monitoring.
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
  nested Proxmox lab with its dedicated inventory token. On 2026-10-16, the
  host-installed client successfully retrieved one guest with only the five
  dashboard fields; transient Linux backend/dashboard startup and stop checks
  passed with loopback-only listeners and rejection of an unauthenticated
  inventory request. A later rootless Podman deployment also passed dashboard,
  OpenAPI, health, and anonymous-route checks. After adding a host-gateway
  hostname mapping, the live inventory client inside the backend container
  returned one guest with the expected five dashboard fields. Services are
  active and healthy but not configured for boot auto-start. All results are
  nested-lab evidence, not physical-host acceptance. No VM management or
  console controls are exposed.
- Network Services panel has planning-only views for DHCPv4, DHCPv6, DNS, web
  hosting, and routing/firewall. The intended initial integration is
  **observe-only**, including services hosted inside VMs: discover their
  owning guest and report approved service health/metrics without changing
  guest services or network configuration. Service ownership, scopes,
  monitoring interfaces, and configuration remain undecided; no backend or
  network-service monitoring API is connected.

### Done — portable diagnostics knowledge, simulation, and contracts

- Added versioned, bundled diagnostic runbooks with a deterministic local
  lexical search and viewer-authorized list, detail, and search endpoints.
  Current procedures cover Proxmox API/TLS, empty/forbidden VM inventory, and
  local diagnostics storage. Retrieval returns reviewed procedures only;
  incident-derived drafts, embeddings, vector databases, and model-driven
  diagnosis are not connected.
- Added deterministic in-memory maintenance and remediation simulations with
  a fixed-start mock clock. Tests cover preflight and drain skips, missing
  diagnostic context, restoration failure, registered-action validation,
  verification, rollback, and escalation. Simulations have no service,
  process, shell, Proxmox, database, or network action adapter and cannot
  execute live work.
- Added read-only Proxmox inventory and proposal-only VM, network-service, and
  game-server contracts. Change intents require the declared admin role and
  exact confirmation phrase; no mutation routes or provider are implemented.

### Pre-physical-server work — portable and nested-lab eligible

- **Partial — nested-lab integration:** the inventory token's live read
  permission and transient loopback backend/dashboard startup and stop were
  verified on 2026-10-16. Rootless Podman/Quadlet units and container health
  checks are now implemented; both containers are active, loopback-only, and
  not configured for boot auto-start. The container's original route to the
  guest API was refused; the backend Quadlet now maps the API hostname to
  Podman's host gateway. The deployed mapping and live inventory request were
  verified: the container returned one guest with the expected five fields.
  On 2026-10-17, explicit stop/start was verified: units stopped cleanly,
  containers exited, listeners closed, then both services restarted healthy.
  A controlled backend-container kill triggered one systemd restart; the
  backend returned healthy, OpenAPI returned HTTP 200, anonymous inventory
  remained HTTP 401, and the live inventory client returned the expected
  record. The dashboard remained healthy and both ports stayed loopback-only.
  A separate start-limit boundary check allowed three automatic restarts and
  blocked the fourth failure within 60 seconds; resetting the failed unit and
  starting it manually restored a healthy backend. See the
  [testing-environment guide](./testing-environment.md). On 2026-10-17,
  deployment rollback from an intentionally unavailable image candidate to a
  saved pre-test Quadlet/image snapshot also passed. The candidate was prevented
  from pulling from a registry; after the unit hit its start limit, restoring
  the snapshot, resetting the failed unit, and starting it manually restored
  healthy API and live inventory. The snapshot is of the current build, not a
  previous application release. Boot auto-start, reboot recovery,
  deployment-script validation, and physical-host acceptance remain
  outstanding.

#### Integration-priority order

1. **Linux deployment and service lifecycle — partial, nested-lab checks
   passed.** Podman/Quadlet
   was selected for the lab. Rootless backend and dashboard definitions now
   use loopback-only ports, explicit environment/CA mounts, persistent runtime
   state, health checks, and bounded restart behavior. The containers are
   active but not configured for boot auto-start. The updated host-gateway
   hostname mapping and live inventory request now pass in the nested lab.
   Stop/start, controlled backend failure/restart, start-limit behavior, and
   rollback from an unavailable candidate to a saved pre-test snapshot passed.
   The rollback baseline is the current build, not a previous application
   release. Next validate deployment-script behavior and recovery after a
   guest reboot. Do not enable boot auto-start until separately reviewed;
   reboot recovery and physical-host acceptance remain unverified.
2. **Proxmox identity and dashboard authorization — next.** Exercise the live
   Proxmox ticket login and identity-to-role mapping in the nested lab, then
   verify cookie, CSRF/origin, viewer/operator/admin boundaries. Use a
   least-privilege test identity; do not grant mutation permissions or treat
   lab success as physical-host acceptance.
3. **Linux application smoke coverage — after the service design.** Verify
   backend startup, SQLite paths/permissions, logs, authentication,
   read-only diagnostics, and API health as the service account. Add llama.cpp,
   SearXNG, bot, and proxy checks only when those services are installed and
   configured.
4. **Deployment-script lab checks — safe, read-only modes first.** Exercise
   `--check` and `--report` on the nested Proxmox guest, inspect their output
   and side effects, and record version/platform limits. Do not run installer
   modes or claim physical-target validation from the nested guest. A separate
   application deployment installer is **planned, not started**: explore it
   after the lab checks, keeping it distinct from `prepare-ai-host.sh`. Initial
   scope is only the existing rootless backend/dashboard image and Quadlet
   deployment, with read-only preflight, explicit confirmation, protected
   secret/config handling, pinned versions, health checks, and rollback that
   preserves persistent data. Keep SearXNG optional; exclude ROCm and the
   inference stack until their separate compatibility/version gates are met.
   See the [Linux/Proxmox transition runbook](./linux-proxmox-transition.md).
5. **Portable GPU telemetry interface — useful preparation, not integration
   acceptance.** Define typed provider outcomes and unavailable/error
   behavior, then test with deterministic fixtures. The actual provider,
   adapter identity, GPU readings, and thresholds remain Phase 5 server-gated.
6. **Lower integration priority product contracts.** Define model-agnostic
   image job contracts and build the workspace-restricted website agent only
   after deployment permissions, workspace boundaries, and recovery behavior
   are decided. Keep file/command integrations disabled until then; do not
   prioritize a Windows-only image runtime.

**Existing Proxmox UI status:** the VM panel already distinguishes loading,
not-configured, connected-empty, live inventory, and unavailable states. The
read-only API rejects unauthenticated requests and does not return cached or
sample inventory. No VM mutation or console controls are exposed. Further UI
guidance, such as linking a failure state to a reviewed runbook, is a
non-blocking improvement rather than a prerequisite for the next integration
step.

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
- A separate app-deployment installer contract has been documented for later
  exploration; no such installer is implemented. The existing host-preparation
  script remains separate, and the initial planned installer scope excludes
  GPU/inference components and defaults to non-persistent, loopback-only
  deployment.
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
- Connect DHCPv4/DHCPv6, DNS, web hosting, and routing/firewall in observe-only
  mode first, including discovery and health reporting for services hosted in
  VMs. Decide ownership, scopes, segmentation, supported read-only telemetry,
  and out-of-band recovery before integration. Keep mutation and automated
  remediation unavailable until a separately reviewed limited-autonomy phase;
  full autonomy requires a later explicit readiness and authorization gate.
  Network changes must not make the AI host the sole unprotected network edge
  or strand the dashboard.
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

The highest-priority eligible work is the nested-lab Linux deployment/service
lifecycle, followed by live Proxmox identity/role checks, Linux application
smoke coverage, and read-only deployment-script checks. The VM panel already
has its principal failure states. Portable GPU telemetry interfaces, image
contracts, and website-agent groundwork remain implementable but are lower
integration priority. Record lab results as nested-lab validation and document
limitations; do not substitute Windows-only runtimes for the planned Proxmox
stack.

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
- [Portable Infrastructure Contracts](./infrastructure-contracts.md) — read-only inventory and proposal-only infrastructure contracts
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) — system components and data flow
- [Configuration Guide](./configuration.md) — environment variables and settings
- [Backend Documentation](./backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) — dashboard UI and JavaScript structure
