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

There are currently no roadmap items in active implementation. The dashboard,
Windows backend foundation, operational logging and Phase 5 interface polish
are implemented. Proxmox authentication is groundwork only; diagnostics and
the production Linux/Proxmox stack remain largely unimplemented. A first
read-only diagnostics core now exists; the next recommended work is to expose
it through a diagnostics API and dashboard view.

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
- Proxmox authentication groundwork: HTTPS ticket-client and typed interface,
  mocked response tests, and a disabled dashboard sign-in preview. This is not
  production authentication.
- Read-only `GET /api/backend/logs` endpoint and dashboard panel: configurable
  tail bounded to 500 lines, defaults to the latest 200; manual refresh and
  five-second auto-refresh only while open. The endpoint is currently
  unauthenticated, so keep the backend local-only until session authentication
  and protected routes are implemented.

### Not started

- Web research: basic cited search works in the Windows setup; full-page
  fetching and streaming remain.
- Complete login and session UI after the backend authentication/session
  design is implemented. The current sign-in UI is an inert preview.

### Waiting for server

- Implement and validate Proxmox-backed login and proper application session
  management against the target Proxmox VE host. The Windows test setup has no
  Proxmox identity provider; confirm ticket/session lifetime, renewal,
  revocation, and disabled-user behavior on the actual server; protect the
  backend log endpoint and other non-public routes. Required before LAN or
  remote access. See [authentication.md](./authentication.md).
- Validate the host-preparation script modes on the eventual Proxmox host;
  `--install-searxng` has not been tested in a Proxmox environment.
- Once the local maintenance prototype exists, validate its production
  integration against the target service manager and hardware: safely pause
  and restore workloads, keep the control plane available, retrieve local RAG
  data, validate proposals, restore the normal model, and verify updates and
  rollback.

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
- Focused tests cover observations, incident recovery, audit events, and
  explicit propagation of unexpected probe failures.
- This is groundwork only: no scheduler, persistent storage, automated log
  analysis, thresholds, or remediation is enabled.

### Not started — buildable in the Windows test environment

- Complete Diagnostics Phase 1: persist incident/evidence/audit history,
  implement broader health checks, threshold durations and hysteresis,
  automated log analysis and reports, then add recurring scheduling only
  after cadence, retention, and failure behavior are tested. Current
  observations remain manual and process-local.
- Curated platform-specific knowledge-base runbooks and fault-injection tests.
- Build local RAG groundwork: reviewed diagnostics procedures and known-issue
  references, local development vector store and embeddings, metadata filtering,
  and retrieval tests. Keep diagnostic data and source knowledge local;
  incident-derived content remains an untrusted draft pending review.
- Define a structured repair-proposal schema and prototype independent
  backend-executor validation with mocked actions. The model must never run
  commands or authorize its own proposals.
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

The planned Proxmox/RX 6800 XT combination is not listed as officially
supported in AMD's published compatibility matrix. Do not proceed with
GPU-dependent installation until the exact host and component compatibility
has been checked. The host-preparation script does not install this GPU stack.

## Phase 4 — Advanced Features

### Not started — can begin before the server is built

- Website-building agent, restricted to a configured workspace and requiring
  approval before file changes or command execution
- Discord automation and diagnostics notifications
- Additional agent workflows
- Diagnostics Phase 2: safe auto-remediation and approval workflow, after
  observe mode and independent executor validation are established. Real
  service-restart actions require the production service setup.
- Complete the scheduled maintenance implementation after the mocked
  lifecycle is proven. It must suspend normal workloads but keep the
  coordinator, executor, monitoring, local RAG, and recovery/notification path
  available; select an eligible dedicated diagnostic model; perform integrity
  checks and allowlisted safe updates; and restore normal operation only after
  verification. Do not force unsafe interruption at 04:00; remain paused and
  alert on failed health checks. Proxmox, kernel, GPU driver/ROCm, and firmware
  updates remain approval-only.
- Diagnostics Phase 3/4: ML-based detection, predictive alerts, and
  self-learning knowledge-base updates; these depend on collected and reviewed
  incident history.

### Waiting for server or deployment architecture

- Podman/Quadlet services, NGINX reverse proxy, TLS, and Qdrant deployment
- Multi-model routing
- Evaluate multi-GPU inference on the eventual hardware: model splitting or
  per-GPU instances with concurrent-client routing; compare compatibility,
  VRAM, throughput, latency, power, and stability against the single-GPU
  baseline
- VM management through Proxmox and remote server control

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
   incident-derived knowledge as untrusted drafts until reviewed.
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

Production authentication/session management, LAN exposure, Linux GPU
telemetry, and maintenance/service recovery validation remain gated on the
target Proxmox server. Keep the backend local-only until authentication,
protected routes, TLS, and network controls are in place.

## Documentation References

- [Authentication & Session Management](./authentication.md) — design and implementation guide
- [AI Diagnostics & Self-Healing System](./ai-diagnostics-self-healing.md) — design specification
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) — system components and data flow
- [Configuration Guide](./configuration.md) — environment variables and settings
- [Backend Documentation](./backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) — dashboard UI and JavaScript structure
