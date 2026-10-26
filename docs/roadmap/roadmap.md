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
- Dashboard behavior is organized into native browser modules without a build
  step; browser loading and focused module ownership are documented in the
  frontend guide. Playwright browser regressions now cover module loading,
  sign-in gating, viewer/operator/admin UI behavior, panel navigation, and
  persisted preferences. They found and fixed CSS that had overridden the
  standard `hidden` attribute on styled controls.
- FastAPI backend foundation
- Discord bot foundation
- System monitoring in the Windows test environment
- Local chat interface and model discovery/switching
- Operational logging

## Phase 2 — Portable Backend and Reliability

### Done

- Validated configuration loader
- FastAPI routes organized into auth, chat, memory, research, and operations
  modules while retaining the `main:app` deployment entry point. Full backend
  regression suite passes against the modular app.
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
  See the [AI Diagnostics & Self-Healing design](../diagnostics/ai-diagnostics-self-healing.md).
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
  [testing-environment guide](../operations/testing-environment.md). On 2026-10-17,
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
   release. Portable tests now guard the checked-in Containerfile and Quadlet
   lifecycle/security contract and exercise the HTTP health probe. These tests
   do not invoke Podman/systemd. Next validate deployment-script behavior and
   recovery after a guest reboot. Do not enable boot auto-start until
   separately reviewed; reboot recovery and physical-host acceptance remain
   unverified.
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
4. **Deployment-script lab checks — not yet run.** Exercise
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
   See the [Linux/Proxmox transition runbook](../deployment/linux-proxmox-transition.md).
   The planned deployment workflow now includes an admin-uploaded signed
   `.tar.gz` release containing a prebuilt architecture-specific OCI image and
   manifest, verified before apply. A separate rootless updater is required to
   survive backend restarts, coordinate only backend/dashboard services, run
   health checks, and restore the prior image on failure. This is a design
   only; signing, trust-key rotation, archive hardening, database backup/schema
   compatibility, and updater permissions/status remain unimplemented.
5. **Linux AMD GPU telemetry — provider implemented; target validation
   pending.** A platform dispatcher now selects the Windows provider or Linux
   `amdgpu` sysfs provider. Deterministic fixtures cover utilization, VRAM,
   optional hwmon sensors, invalid/missing counters, and ambiguous adapters.
   No ROCm/HIP runtime is installed or implied. Verify driver-exposed counters,
   service permissions, adapter identity, and idle/inference readings on the
   target Linux host before treating telemetry as operational.
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
- Current planned platform: Z590 motherboard with Intel Core i9-11900KF and
  RX 6800 XT. Start with 32 GB system RAM, with a possible 64 GB upgrade,
  2 TB initial NVMe, and HDD-backed bulk/lower-I/O workloads. Confirm the
  exact board model, delivered hardware, firmware/boot configuration, and
  actual memory needs against Proxmox, planned VMs, inference, and concurrent
  services before deployment.
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
  [GPU plan](../gpu/gpu-plan.md).
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
  this gate passes. See [authentication.md](../security/authentication.md).
- Integrate the existing dashboard, backend, model discovery/switching, chat
  and streaming, SQLite history, logging, optional research/bot, and
  observe-only diagnostics. Verify Linux dependencies, permissions, service
  recovery, proxy/WebSocket routing, and host reboot using the
  [Linux/Proxmox transition runbook](../deployment/linux-proxmox-transition.md).
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

The highest-priority eligible work remains the Linux deployment/service
lifecycle and portable integration checks. A Linux AMD GPU telemetry provider
is now implemented and fixture-tested, but live kernel/GPU readings remain
target-host validation. The VM panel already has its principal failure
states. Image contracts and website-agent groundwork remain lower integration
priority. Record lab results as nested-lab validation and document
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

## Candidate backlog — not scheduled

- **Household AI ↔ Maintenance AI Delegation Model (Future)**

  **Status:** Concept

  **Objective:** Separate conversational interactions from operational
  analysis by establishing Maintenance AI as the authoritative diagnostics
  engine and Household AI as the user-facing communication layer.

  **Responsibilities:**

  - **Household AI:** chat, research, voice interactions, and user-facing
    explanations.
  - **Maintenance AI:** diagnostics, incident analysis, infrastructure
    awareness, maintenance workflows, and runbook execution.

  **Design notes:**

  - Maintenance AI primarily communicates through the AI Interface/Dashboard.
  - Household AI may request diagnostics on behalf of a user.
  - Maintenance AI findings are persisted as operational records.
  - Household AI translates operational findings into audience-appropriate
    responses.

  This is a concept, not implemented behavior. The backend does not yet
  provide this delegated two-role workflow, and runbook execution remains
  unimplemented. Any future diagnostic request, operational record, and
  execution path must preserve the project's authorization, audit, and
  observe-first constraints.

- **Shared Incident Reporting and Administrative Visibility (Future)**

  **Status:** Concept

  **Objective:** Ensure diagnostics, incidents, and maintenance findings
  generated by the Maintenance AI are recorded as operational events in the AI
  Interface/Dashboard rather than existing only in individual user
  conversations. This extends the existing bounded diagnostics incident
  history: household-request attribution, a shared operational timeline, and
  updates linked to the same incident are not implemented.

  **Planned scope:**

  - Record diagnostics initiated by household members.
  - Associate incidents with the reporting user while preserving operational
    visibility.
  - Expose findings, status changes, and resolution history to authorized
    administrators.
  - Maintain a timeline of infrastructure-related incidents and
    investigations.
  - Allow Household AI to translate Maintenance AI findings into
    user-friendly explanations without duplicating operational records.

  **Example workflow:**

  1. A household member reports a problem.
  2. Household AI requests diagnostics from Maintenance AI.
  3. Maintenance AI generates findings and records an incident.
  4. The incident appears in the AI Dashboard for authorized administrators.
  5. Household AI translates the findings into a user-friendly response.
  6. Future updates and resolution activity attach to the existing incident
     record.

  **Long-term vision:** Treat diagnostics and maintenance activities as shared
  operational records instead of private chat messages, enabling historical
  analysis, administrative oversight, and future automated maintenance
  workflows. This is a concept only; no household incident attribution,
  shared Maintenance AI event workflow, or linked household-facing incident
  updates are implemented.

- **Network-Aware Diagnostics (Future)**

  **Status:** Concept

  **Objective:** Extend the Maintenance AI's diagnostics from AI Server
  health to household network and infrastructure awareness, so reported
  connectivity problems can be investigated using correlated, evidence-based
  observations.

  **Responsibilities:**

  - **Maintenance AI:** gather configured read-only telemetry from supported
    access points, routers, switches, and relevant services; correlate WAN,
    LAN, wireless, and client evidence; distinguish possible ISP outages,
    routing faults, wireless congestion, access-point failures, and
    client-specific issues; and produce findings and recommendations.
  - **Household AI:** accept household questions such as “The internet is
    down,” “The Wi-Fi is slow,” or “The Quest headset is lagging”; request
    diagnostics on the user's behalf; and explain findings in a
    user-appropriate way.

  **Design notes:**

  - Initial integrations must be observe-only and use explicitly configured,
    least-privilege read access. Unavailable telemetry must not be presented
    as healthy.
  - Findings, evidence, and incident history should support trend and
    recurring-issue analysis; recommendations must remain separate from
    operational actions.
  - Until a separate runtime is selected and validated, an on-demand
    household diagnostic request is planned to gate household inference,
    switch the single llama.cpp runtime to an approved installed Maintenance
    AI model, then restore the prior household model and reopen service only
    after health checks. This is separate from scheduled maintenance and
    does not itself authorize remediation.
  - Any guided or automated recovery requires separately reviewed
    authorization, confirmation, audit, verification, and recovery controls.
    The AI must not change network configuration or promote its own
    authority.

  This is a concept, not implemented behavior; it is not assigned to a phase
  or selected as the next priority. No network telemetry provider or
  end-to-end network diagnostic workflow is implemented. See the
  [diagnostics design](../diagnostics/ai-diagnostics-self-healing.md),
  [infrastructure contracts](../operations/infrastructure-contracts.md),
  and [household network reference](../operations/home-network-topology.md)
  for current constraints and possible integration points.

- **Conversational Household Interface (Future)**

  **Status:** Concept

  **Objective:** Let household members interact naturally with household
  services, diagnostics, and maintenance through a user-facing conversational
  interface, without requiring direct dashboard access for every request.

  **Responsibilities:**

  - **Household AI:** handle chat and research, accept future voice requests,
    provide spoken or written status and explanations, and route authorized
    diagnostic requests to Maintenance AI.
  - **Maintenance AI:** perform the delegated operational analysis and
    provide diagnostic findings for user-facing explanations and maintenance
    summaries.

  **Design notes:**

  - Local speech-to-text (STT) and text-to-speech (TTS) are candidate
    capabilities; technologies, models, microphones, speakers, and
    deployment topology have not been selected.
  - Household enrollment, identity, authorization, consent, audio retention,
    and safeguards against unintended or overheard requests must be defined
    before implementation. Voice recognition must not itself establish
    identity or grant privileges.
  - Requests must remain within the caller's authorized role. A symptom
    request may use the bounded Maintenance AI handoff described in the
    Network-Aware Diagnostics concept above, but operational changes require
    separate approval and recovery controls.
  - Any proactive notifications for critical incidents or maintenance events
    must be opt-in and avoid exposing sensitive household or infrastructure
    details to unauthorized listeners.

  This is a concept, not implemented behavior. No household voice interface,
  local STT/TTS integration, household enrollment/authorization workflow, or
  notification channel has been selected or implemented. The reported home
  topology and potential components are summarized in the
  [household network reference](../operations/home-network-topology.md).

- **Multi-GPU Workload Separation (Future)**

  **Status:** Concept

  **Objective:** Evaluate separate GPU capacity for the Maintenance AI and
  household-facing User AI so each role could operate independently without
  switching models on one shared runtime.

  **Responsibilities:**

  - **Maintenance AI:** use the planned RX 6800 XT exclusively, prioritizing
    its 16 GB VRAM capacity over inference speed for lower-frequency
    diagnostics and maintenance workloads.
  - **User AI:** use a possible second GPU for household chat, research,
    Discord integrations, vision, and conversational interaction.

  **Design notes:**

  - Candidate second GPUs are Radeon RX 7900 XT/XTX, if additional VRAM
    capacity is the priority, or RX 9070 XT, for its newer RDNA 4 architecture
    and potential speed/efficiency advantages.
  - The exact RX 7900 variant and comparative workload performance remain
    unresolved; these are not benchmark results or a hardware selection.
    The second GPU is not selected or acquired.
  - Until a second GPU and runtime arrangement are selected and validated,
    the interim design remains single-GPU/single-runtime model handoff, not
    concurrent operation of both roles. The current deployment plan remains
    one RX 6800 XT.
  - Power and cooling, host compatibility, runtime support, and workload
    isolation require validation before adopting separate concurrent
    workloads.

  This is a concept, not implemented behavior. No second GPU has been
  selected or acquired, and independent concurrent operation of the two AI
  roles has not been validated. See the [GPU plan](../gpu/gpu-plan.md#potential-future-multi-gpu-inference)
  and [household network and infrastructure reference](../operations/home-network-topology.md#possible-multi-gpu-role-separation).

## Documentation References

- [Authentication & Session Management](../security/authentication.md) — design and implementation guide
- [AI Diagnostics & Self-Healing System](../diagnostics/ai-diagnostics-self-healing.md) — design specification
- [Portable Infrastructure Contracts](../operations/infrastructure-contracts.md) — read-only inventory and proposal-only infrastructure contracts
- [Linux/Proxmox Transition Runbook](../deployment/linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](../architecture/architecture.md) — system components and data flow
- [Configuration Guide](../operations/configuration.md) — environment variables and settings
- [Backend Documentation](../backend/backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](../frontend/frontend.md) — dashboard UI and JavaScript structure
