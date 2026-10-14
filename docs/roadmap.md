# Project Roadmap

## Status key

- **Done** — implemented and verified in the current Windows test environment.
- **In progress** — implementation is actively underway.
- **Not started** — planned, but implementation has not begun.
- **Waiting for server** — depends on the Proxmox host, its kernel, or the
  production hardware.

There are currently no roadmap items in active implementation. Partially
complete work is split between **Done** and its remaining **Not started** or
**Waiting for server** tasks.

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
  `--install-base`, and `--install-searxng` modes

### Not started

- Web research: basic cited search works in the Windows setup; full-page
  fetching and streaming remain.
- Backend log viewer: backend logs are written to files, but are not yet
  viewable in the dashboard.
- Proxmox-auth integration groundwork: define interfaces, mock Proxmox's
  ticket endpoint, and prepare the login UI. Mocked auth is not production
  authentication.

### Waiting for server

- Implement and validate Proxmox-backed login and proper application session
  management against the target Proxmox VE host. The Windows test setup has no
  Proxmox identity provider; confirm ticket/session lifetime, renewal,
  revocation, and disabled-user behavior on the actual server. Required before
  LAN or remote access. See [authentication.md](./authentication.md).
- Validate scheduled maintenance against the target service manager and
  hardware: enter/exit maintenance mode, pause/drain and restart normal
  workloads safely, keep the control plane operational, select the diagnostic
  model, retrieve local RAG data, validate structured proposals, restore the
  previous model, and verify updates/rollback.
- Validate the host-preparation script modes on the eventual Proxmox host;
  `--install-searxng` has not been tested in a Proxmox environment.
- Linux/Proxmox GPU telemetry, after the RX 6800 XT is installed in the host

## Phase 3 — GPU Integration and Diagnostics

### Design complete

- llama.cpp Vulkan build for Windows testing
- AI diagnostics and self-healing design specification (the system itself is
  not implemented)
  ([ai-diagnostics-self-healing.md](./ai-diagnostics-self-healing.md))

### Not started — buildable in the Windows test environment

- Diagnostics Phase 1: observe-only health checks, resource sampling,
  reactive incident records, evidence collection, reporting, and audit log
- Diagnostics status board and incident list
- Platform-specific knowledge-base runbooks and fault-injection tests
- Build local RAG groundwork: reviewed diagnostics procedures and known-issue
  references, local development vector store and embeddings, metadata filtering,
  and retrieval tests. Keep diagnostic data and source knowledge local;
  incident-derived content remains an untrusted draft pending review.
- Define a structured repair-proposal schema and prototype independent
  backend-executor validation with mocked actions. The model must never run
  commands or authorize its own proposals.
- Prototype the scheduled 03:00–04:00 maintenance lifecycle with a mocked
  clock/model manager: enter maintenance mode, pause user-facing services and
  inference while keeping the maintenance control plane alive, load a
  diagnostic model with locally retrieved knowledge, execute validated
  proposals, and restore normal operation. Simulation does not validate
  production recovery.

### Waiting for server and compatibility verification

- ROCm/HIP on the Proxmox host and ROCm-built llama.cpp / `llama-server`
- ONNX Runtime ROCm execution provider and ComfyUI ROCm
- Linux GPU telemetry and production inference validation
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
- Diagnostics Phase 2: safe auto-remediation and approval workflow. Real
  service restart actions require the production service setup.
- Daily 03:00–04:00 scheduled maintenance mode: safely pause normal
  user-facing services and inference; keep the coordinator, executor,
  monitoring, local RAG and recovery/notification path running; load the best
  eligible dedicated diagnostic model; reactively diagnose and submit
  structured repairs to the validated executor; run integrity checks and
  allowlisted safe updates; then restore the normal model/services after
  verification. Validate model/resource fit, local vector-store deployment
  (Qdrant is a candidate), retrieval, stop/start order, update rollback, and
  recovery on the server. The window must not force unsafe interruption at
  04:00; if health checks fail, remain paused and alert. Proxmox, kernel, GPU
  driver/ROCm, and firmware updates remain approval-only.
- Diagnostics Phase 3/4: ML-based detection, predictive alerts, and
  self-learning knowledge-base updates; effectiveness depends on collected
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

1. Prepare the Proxmox-auth interfaces, mocked API tests, and login UI; defer
   real session management until the Proxmox server is available.
2. Add a dashboard backend log viewer.
3. Build diagnostics observe mode and its dashboard view.
4. Complete web-research page fetching and streaming.
5. Build the website-building agent with approval controls.

## Documentation References

- [Authentication & Session Management](./authentication.md) — design and implementation guide
- [AI Diagnostics & Self-Healing System](./ai-diagnostics-self-healing.md) — design specification
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) — system components and data flow
- [Configuration Guide](./configuration.md) — environment variables and settings
- [Backend Documentation](./backend.md) — FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) — dashboard UI and JavaScript structure
