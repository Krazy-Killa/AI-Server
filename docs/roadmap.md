# Project Roadmap

## Phase 1 — Local Test Environment (Complete)

- Dashboard UI
- Backend stubs
- Discord bot stubs
- System monitor
- Chat interface
- Model cards
- Logs

## Phase 2 — Real Backend Features

- Linux/Proxmox deployment preparation and acceptance checks
- Kernel-aware Proxmox host preflight and optional base-tools setup script
  (initial version; host validation and full inference-stack installation
  remain outstanding)
- SearXNG setup for web research: Windows test setup done (WSL, `scripts/searxng/`);
  Proxmox `--install-searxng` mode written but not yet tested on the server
- Linux/Proxmox host GPU telemetry after the RX 6800 XT is moved to the server
- Logging system (done: console and rotating file logs; no dashboard log viewer
  for backend logs yet)
- Config loader (done: validated environment settings)
- WebSocket streaming (done for local chat; web research still non-streaming)
- Restrict CORS and WebSocket origins to the dashboard (done)
- **Authentication & Session Management** (JWT-based, designed in
  `docs/authentication.md`, not yet implemented; required before any
  LAN/remote access)
  - User login/logout endpoints
  - Token refresh mechanism
  - Protected endpoint middleware
  - Frontend login page and token management
  - Rate limiting and security hardening

## Phase 3 — GPU Integration

- llama.cpp Vulkan (Windows test build complete)
- Proxmox VE 9.x host stack (one RX 6800 XT): ROCm/HIP on the host,
  llama.cpp ROCm build/`llama-server`, ONNX Runtime ROCm EP, and ComfyUI ROCm
  (versions/support to verify; not yet installed or validated on the server)
- Podman/Quadlet service setup, NGINX reverse proxy, and Qdrant deployment
- Linux GPU telemetry for the Proxmox host
- Real inference pipeline
- **AI Diagnostics & Self-Healing System** (design specification in
  `docs/ai-diagnostics-self-healing.md`, not yet implemented). Its observe-mode
  phase can be built now on Windows; auto-remediation of real services waits
  for the server.
  - Real-time health monitoring and anomaly detection
  - Diagnostic engine for root cause analysis
  - Auto-remediation for safe operations (service restart, cache clear, config reload)
  - Error reporting and escalation for critical issues
  - Knowledge base of troubleshooting procedures and runbooks
  - User intervention workflows and approval gates
  - Audit logging of all diagnostic and remediation actions

The host preparation script inventories the host, optionally installs base
tools after previewing an apt plan, and can install SearXNG (`--install-searxng`,
which is not GPU-dependent). It does not install the GPU stack above.
Keep ROCm and GPU-dependent installation blocked until compatibility is
checked for the actual Proxmox release, running kernel, RX 6800 XT, and pinned
component versions. AMD's published matrix currently does not list the
planned GPU/Proxmox combination as officially supported.

## Phase 4 — Advanced Features

- Explicit, cited web research through self-hosted SearXNG (working on the
  Windows test setup; full-page fetching and streaming not yet implemented)
- Website-building agent limited to a configured workspace, with approval
  before file changes or command execution
- Multi-model routing
- Evaluate multi-GPU inference on the eventual Linux/Proxmox hardware:
  - Split one model across GPUs where the selected runtime supports it.
  - Alternatively, run a model instance per GPU and route concurrent clients.
  - Compare compatibility, VRAM use, throughput, latency, power, and stability
    against the single-GPU baseline before selecting an approach.
- Agent workflows
- VM management (separate from host AI/GPU telemetry)
- Remote server control
- Discord bot automation
- **Advanced AI Diagnostics** (self-learning and ML-based detection)
  - Machine learning-based anomaly detection
  - Self-learning knowledge base updates from successful fixes
  - Predictive issue detection
  - Advanced remediation strategies
  - Cross-service dependency analysis and recovery

## Phase 5 — Polish

- Animations (done: panel fade-in and sidebar transition; reduced motion respected)
- Theme switching (done: dark/light toggle, persisted)
- Mobile layout (done: compact header and scrolling nav under 760px)
- Collapsible sidebar (done: icon-only rail on desktop, persisted)
- Accent colour selection now persists
- Remaining: test on real mobile devices once the server is live

## Buildable now vs. waits for the server

**Buildable and testable now (Windows):** authentication; diagnostics observe
mode with its dashboard board and Discord notifications; a backend log viewer;
web-research streaming and page fetch; the website-building agent and its
approval workflow; Discord automation; diagnostics KB runbooks and fault-injection
tests; shell-script linting and a Debian VM dry run of `prepare-ai-host.sh`.

**Waits for the server:** ROCm/HIP and everything built on it (llama.cpp ROCm,
ONNX Runtime ROCm EP, ComfyUI); Linux GPU telemetry; Podman/Quadlet, NGINX,
TLS and Qdrant on the real host; validating `--install-searxng` on Proxmox;
diagnostics auto-remediation and ML detection (needs real incident history);
multi-GPU/multi-model routing; VM management and remote control.

Suggested order: authentication, backend log viewer, diagnostics observe mode,
web-research streaming, website-building agent.

---

## Documentation References

- [Authentication & Session Management](./authentication.md) - JWT-based auth system design and implementation guide
- [AI Diagnostics & Self-Healing System](./ai-diagnostics-self-healing.md) - AI-powered monitoring, diagnostics, and auto-remediation framework
- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) - Deployment decisions, blockers, and acceptance criteria
- [Architecture Overview](./architecture.md) - System components and data flow
- [Configuration Guide](./configuration.md) - Environment variables and settings
- [Backend Documentation](./backend.md) - FastAPI endpoints and modules
- [Frontend Documentation](./frontend.md) - Dashboard UI and JavaScript structure

