# Project Roadmap

## Status key

- **Done** — implemented and verified in the Windows development environment
  or with focused mocks, as applicable; this does not imply production-host
  validation.
- **In progress** — implementation is actively underway.
- **Not started** — planned, but implementation has not begun.
- **Experimental / waiting for server** — unsupported-by-vendor work that
  depends on the Proxmox host, its kernel, or the production hardware; staged
  investigation is possible, but runtime validation is still required.

Dashboard-owned login/session management and per-account SQLite conversation
history are implemented and verified in the Windows development environment.
Explicitly curated, admin-only shared operational notes are also implemented;
raw transcripts remain private to each account.
Proxmox-host and HTTPS-proxy validation remain outstanding. The dashboard,
Windows backend foundation, operational logging, and Phase 5 interface polish
are implemented. Transcript history is separate from planned Phase 3
diagnostic RAG; automatic fact memory and model training from conversations
are not implemented. The observe-only diagnostics core, API, and dashboard
view are implemented; persistent incident history, diagnostic RAG, and
production-host integration remain outstanding. The production Linux/Proxmox
stack also remains unvalidated.

## Phase 1 — Local Test Environment

**Status: Done**

- Dashboard UI and panel navigation
- FastAPI backend foundation
- Discord bot foundation
- System monitoring in the Windows test environment
- Local chat interface and model discovery/switching
- Operational logging

## Phase 2 — Real Backend Features

### Done

- Validated configuration loader
- Console and rotating-file backend logging
- WebSocket streaming for local chat
- CORS and WebSocket origin restrictions for configured dashboard origins
- Windows SearXNG test setup and dashboard web-research integration
- Initial Proxmox host preparation script, including `--check`,
  `--install-base`, and `--install-searxng` modes. These modes have not been
  validated on the target Proxmox host.
- Explicit read-only `--report` mode in the Proxmox host preparation script
  writes a private, redacted Markdown snapshot of host facts to support
  implementation planning. It does not upload data or validate runtime
  behavior; review the report before sharing, and capture fresh data on the
  actual server.
- Dashboard-owned authentication: local and mapped Proxmox login, persistent
  revocable sessions, role authorization, protected REST/WebSocket routes,
  CSRF and origin checks, login throttling, CLI account/mapping management,
  and browser login/logout flow. The Windows backend suite passes;
  production Proxmox and proxy validation remains outstanding.
- Proxmox authentication foundation: HTTPS ticket client, typed interface,
  and mocked API-response tests; the dashboard login uses this client.
- Per-account conversational history: isolated SQLite storage, saved-chat
  listing/resume/delete, and bounded recent-turn context for the local chat
  model. Bot API requests remain stateless. This does not implement automatic
  fact extraction, semantic/vector retrieval, or the separate diagnostics
  RAG system. History is retained locally until its owner deletes it.
- Admin shared insight memory: each note must be explicitly published by an
  admin; any admin can read or remove it. Admin identity and a bounded set of
  approved notes are supplied to dashboard chat and research. Private account
  transcripts are not shared, scraped, or used for model training. The newest
  private conversation resumes at sign-in.
- Read-only `GET /api/backend/logs` endpoint and dashboard panel: configurable
  tail bounded to 500 lines, defaults to the latest 200; manual refresh and
  five-second auto-refresh only while open. Access is admin-only.

### In progress

- Web research: basic cited search works in the Windows setup; full-page
  fetching and streaming remain.
### Not started

- Image-generation backend groundwork: translate text requests into a
  structured, editable image brief (subject/details, setting,
  composition/viewpoint, style, mood, lighting, palette, aspect ratio/use, and
  exclusions); preserve original prompt and user edits; define an API/job
  contract for submitting approved briefs to an image runtime; and retain
  reproducibility metadata (model/checkpoint, optional LoRAs/reference inputs,
  seed, and generation settings). Add tests for intent preservation,
  validation, revision state, and metadata capture. This phase need not run an
  image model or require GPU acceleration.

### Waiting for server

- Validate Proxmox-provider login, identity mapping, HTTPS certificate trust,
  session behavior for disabled Proxmox users, and secure-cookie behavior
  through the production proxy on the target host. Required before LAN or
  remote access. See [authentication.md](./authentication.md).
- Validate the host-preparation script modes on the eventual Proxmox host;
  `--install-searxng` has not been tested in a Proxmox environment.
- Once the local maintenance prototype exists, validate its production
  integration against the target service manager and hardware: safely pause
  and restore workloads, keep the control plane available, retrieve local RAG
  data, validate proposals, restore the normal model, and verify updates and
  rollback. Exercise every phase and failed-gate recovery in the maintenance
  runbook before enabling the schedule.
- Integrate the currently implemented dashboard, FastAPI backend, llama.cpp
  model serving/switching, logging, optional SearXNG research, optional Discord
  bot, and observe-only diagnostics on the Proxmox host. Validate Linux
  dependencies, persistent paths and permissions, service startup/recovery,
  API and WebSocket routing through the chosen proxy, and end-to-end behavior
  using the acceptance checklist in the
  [Linux/Proxmox transition runbook](./linux-proxmox-transition.md). Windows
  success and mocked tests do not count as Proxmox integration verification.

## Phase 3 — GPU Integration and Diagnostics

### Design complete

- llama.cpp Vulkan build for Windows testing
- AI diagnostics and self-healing design specification (the system itself is
  not implemented)
  ([ai-diagnostics-self-healing.md](./ai-diagnostics-self-healing.md))

### Done — observe-only core, API, and dashboard groundwork

- `ai-backend/diagnostics.py` provides on-demand read-only checks for the
  backend process, llama.cpp health endpoint, SearXNG JSON search endpoint,
  and Discord heartbeat.
- Each observation captures CPU/RAM use, free space on the log volume, backend
  process RSS, and per-check results as evidence.
- Failed checks open/update warning incidents; a later healthy check resolves
  the incident. Observation, incident-open, and incident-resolved events are
  tracked in bounded process-local history.
- Explicit diagnostics API (`/api/diagnostics/status`, `/observations`,
  `/incidents`, and `POST /observe`) exposes bounded observation and incident
  data; collecting checks requires an explicit POST.
- Dashboard diagnostics panel shows latest check results, resource snapshot,
  and recent incidents, with manual refresh and an explicit run button.
- Explicit "run/check diagnostics" requests in signed-in operator chat execute
  one read-only observation and provide the captured evidence to the local
  model for explanation; informational questions do not trigger a run, and the
  Discord bot service credential does not receive this capability.
- Focused tests cover observations, incident recovery, audit events, and
  explicit propagation of unexpected probe failures.
- This is groundwork only: no scheduler, persistent storage, automated log
  analysis, thresholds, or remediation is enabled.

### Not started — buildable in the Windows test environment

- Image-generation GPU/runtime development: choose and test a Windows
  DirectML-compatible framework and model; integrate it with the Phase 2
  image-brief/API workflow. Measure GPU offload, VRAM/RAM headroom, generation
  latency, and output quality. Display generated results and support targeted
  revisions while retaining relevant settings/seed. Exact lettering should
  use a separate text/layout step rather than relying on image-model spelling.
- Complete Diagnostics Phase 1: persist incident/evidence/audit history,
  including user feedback, attempted actions, and independently verified
  outcomes; implement broader health checks, threshold durations and
  hysteresis, automated log analysis and reports, then add recurring
  scheduling only after cadence, retention, and failure behavior are tested.
  Current observations remain manual and process-local.
- Curated platform-specific knowledge-base runbooks and fault-injection tests.
- Build local retrieval groundwork: reviewed diagnostics procedures and
  known-issue references plus a searchable history of similar incidents and
  their verified outcomes; local development vector store and embeddings,
  metadata filtering, and retrieval tests. Keep incident records distinct
  from curated knowledge: past cases inform decisions but are not trusted
  procedures, and incident-derived runbooks remain drafts pending review.
- Define a structured repair-proposal schema and prototype independent
  backend-executor validation with mocked actions. The model must never run
  commands or grant itself authority; the long-term goal is for a separate
  deterministic policy to autonomously authorize individually eligible,
  registered repairs under explicit user settings.
- After the observe-mode, RAG, and proposal foundations exist, prototype the
  scheduled 03:00–04:00 lifecycle with a mocked clock/model manager. Simulate
  pausing normal workloads while retaining the maintenance control plane,
  loading the dedicated diagnostic model and local knowledge, executing only
  validated proposals, and restoring normal operation. Simulation does not
  validate production recovery.

### Waiting for server and compatibility verification

- **Experimental:** investigate ROCm/HIP for direct host use and ROCm-built
  llama.cpp / `llama-server`. AMD does not list the RX 6800 XT + Proxmox
  combination as officially supported; community reports on related
  `gfx1030` cards are useful leads, not proof of a working configuration.
  GPU passthrough to a VM is not planned. Follow the staged verification and
  recovery requirements in the [GPU plan](./gpu-plan.md).
- ONNX Runtime ROCm execution provider and ComfyUI ROCm
- Implement and validate Linux/Proxmox GPU telemetry after the RX 6800 XT is
  installed in the host; the current live provider is Windows-specific.
- Production inference validation
- Verify versions and compatibility against the actual Proxmox release,
  running kernel, RX 6800 XT, and pinned component versions
- Image-generation deployment: evaluate the planned ComfyUI/ROCm deployment
  on the Proxmox host. Validate model load, GPU offload, VRAM/RAM headroom,
  generation latency, output quality, and recovery under representative
  workloads. Proxmox ROCm remains experimental pending verification of the
  exact host/kernel/GPU/software combination.

The planned Proxmox/RX 6800 XT combination is not listed as officially
supported in AMD's published compatibility matrix. Do not proceed with
GPU-dependent installation until the exact host and component compatibility
has been checked. The host-preparation script does not install this GPU stack.

### Provisional server hardware and storage plan

These are planning targets, not purchased or validated specifications. Confirm
the exact CPU, memory, storage devices, topology, and workload allocations
before building the host.

- **CPU:** AMD processor with enough cores and threads for Proxmox, planned
  VMs, and host services. Select the exact model based on VM count, workload
  concurrency, platform support, power/thermal limits, and budget; no CPU
  model or core count has been selected.
- **System RAM:** start with 32 GB, with a possible upgrade to 64 GB. Final
  sizing depends on the Proxmox host, VM allocations, inference context/cache,
  and services running concurrently. System RAM is separate from the RX 6800
  XT's 16 GB VRAM.
- **NVMe:** start with a 2 TB NVMe drive for Proxmox/application storage,
  active or write-intensive VM disks, databases, and a fast cache for
  frequently used models. Additional NVMe drives may be added as capacity or
  performance needs grow.
- **Model tiering:** keep the full model library on capacity storage as
  appropriate, promote frequently used or pinned models to NVMe, and retain
  less-used models on HDD. Promotion/eviction must preserve stable model IDs,
  verify copies before use/removal, and never move a model while it is loaded
  or in use. NVMe mainly improves model-file access and load/switch time, not
  inference speed after the model is loaded.
- **HDDs:** use larger-capacity HDDs for bulk file data, archives, backups as
  one copy, and lower-I/O VMs such as DHCP, DNS, and other network services.
  A file-hosting VM may keep its OS and applications on NVMe while its bulk
  data resides on the HDD pool. Expect slower boots and disk-heavy operations
  for HDD-backed VMs.
- **Redundancy and recovery:** an HDD RAID or other redundant pool is under
  consideration; drive count, RAID/ZFS layout, controller mode, usable
  capacity, and expansion strategy are undecided. Redundancy is not a backup:
  maintain a separate backup and test restores. Choose a layout that allows
  the intended future NVMe/HDD expansion without relying on unverified
  in-place conversion.

## Phase 4 — Advanced Features

### Done — pre-server dashboard groundwork

- Virtual Machines panel has a planning-only empty inventory, guest-details
  layout, and unavailable recovery-console state; it has no provider or live
  management controls.
- Network Services panel has planning-only views for DHCPv4, DHCPv6, DNS, web
  hosting, and routing/firewall. Service ownership, scopes, and configuration
  remain undecided; no backend or network changes are connected.

### Not started — can begin before the server is built

- Website-building agent, restricted to a configured workspace and requiring
  approval before file changes or command execution
- Discord automation and diagnostics notifications
- Additional agent workflows
- Diagnostics Phase 2: safe auto-remediation and approval workflow, after
  observe mode and independent executor validation are established. Real
  service-restart actions require the production service setup. Longer-term
  bounded autonomy may learn from user approval/denial reasons and verified
  outcomes, but feedback cannot silently alter permissions; Tier 3 actions
  remain approval-only. See the staged-autonomy design in
  [AI diagnostics & self-healing](./ai-diagnostics-self-healing.md).
- Complete the scheduled maintenance implementation after the mocked
  lifecycle is proven. It must suspend normal workloads but keep the
  coordinator, executor, monitoring, local RAG, and recovery/notification path
  available; follow the phase-gated maintenance runbook; select an eligible
  dedicated diagnostic model; perform integrity checks and allowlisted safe
  updates; and restore normal operation only after verification. Fault-inject
  preflight, drain, model-load, action, verification, rollback, restore, audit,
  and notification failures. Do not force unsafe interruption at 04:00; remain
  paused and alert on failed health checks. Proxmox, kernel, GPU driver/ROCm,
  and firmware updates remain approval-only.
- Diagnostics Phase 3/4: ML-based detection, predictive alerts, and
  self-learning knowledge-base updates; these depend on collected and reviewed
  incident history. Evaluate any autonomous repair authorization per action
  against independently verified outcomes, explicit opt-in, and recovery
  safeguards before enabling it.

### Waiting for server or deployment architecture

- Podman/Quadlet services, NGINX reverse proxy, TLS, and Qdrant deployment
- Multi-model routing
- Evaluate multi-GPU inference on the eventual hardware: model splitting or
  per-GPU instances with concurrent-client routing; compare compatibility,
  VRAM, throughput, latency, power, and stability against the single-GPU
  baseline
- Full Proxmox VM lifecycle management from the dashboard: live inventory and
  status; create/configure from approved templates or ISOs; storage, CPU,
  memory and network assignment; start/stop/reboot; snapshots/backups where
  supported; task progress and audit history; and an authenticated browser
  console for guest recovery. Use least-privilege Proxmox API permissions,
  server-side authorization, explicit confirmation for destructive actions,
  and bounded actions rather than exposing Proxmox credentials to the browser.
  Prioritize the guest console as a recovery and administration path for
  virtual machines.
- Network Services backend integration and service plan for DHCPv4, DHCPv6,
  DNS, web hosting, and routing/firewall. Define service ownership, address
  scopes, IPv4/IPv6 behavior, DNS zones/forwarding, hosting boundaries, network
  segmentation, and recovery before enabling live controls. DHCP and
  routing/firewall changes can disconnect clients or the dashboard; require
  safeguards, explicit confirmation, and a tested recovery path, and avoid
  making the AI host the sole network edge without a deliberate availability
  design.
- Game Servers dashboard: first evaluate a family Minecraft server as the
  initial use case, then select an edition/version and a management approach.
  Plan guest isolation, resource limits, start/stop/status, player/health
  visibility, allowlist and access controls, backups/world restore, and
  optional mod/plugin handling. Do not enable public reachability until
  firewall, authentication, and family-safety requirements are reviewed.

## Phase 5 — Polish

### Done

- Panel fade-in and sidebar transition; reduced-motion preference respected
- Persistent dark/light theme
- Responsive compact header and scrolling navigation below 760px
- Persistent collapsible icon-only desktop sidebar
- Persistent accent-colour selection

### Not started

- Real-device mobile layout and interaction testing

## Suggested next work (no server required)

The auth groundwork, backend log viewer, and initial diagnostics API/dashboard
are complete. Recommended implementation order:

Model recommendations below are advisory and describe roles, not requirements
for a particular editor or agent platform. Use GPT Luna for implementation and
focused tests; use Claude Sonnet as an additional design/safety reviewer for
changes involving diagnostics, remediation, scheduling, or security. Re-check
the current model options when starting each task.

1. Complete observe mode with persistence, threshold durations/hysteresis,
   broader health/log evidence, reports, and fault-injection tests. Keep it
   strictly non-remediating and triggering explicit until scheduling,
   retention, and safety behavior are designed and tested.
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
5. Complete web-research full-page fetching and streaming, then build the
   workspace-restricted website agent with explicit approval for changes and
   command execution.
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

Production authentication/session validation, LAN exposure, Linux GPU
telemetry, and maintenance/service recovery remain gated on the target Proxmox
server. Dashboard authentication and protected routes are implemented locally;
keep the backend local-only until HTTPS/proxy behavior, firewall/network
controls, and the complete deployment have been validated.

## Documentation References

- [Authentication & Session Management](./authentication.md) — design and implementation guide
- [AI Diagnostics & Self-Healing System](./ai-diagnostics-self-healing.md) — design specification
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) — system components and data flow
- [Configuration Guide](./configuration.md) — environment variables and settings
- [Backend Documentation](./backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) — dashboard UI and JavaScript structure
