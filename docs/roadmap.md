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
- Linux/Proxmox host GPU telemetry after the RX 6800 XT is moved to the server
- Logging system
- Config loader
- WebSocket streaming

## Phase 3 — GPU Integration

- llama.cpp Vulkan (Windows test build complete)
- Proxmox VE 9.x host stack (one RX 6800 XT): ROCm/HIP on the host,
  llama.cpp ROCm build/`llama-server`, ONNX Runtime ROCm EP, and ComfyUI ROCm
  (versions/support to verify; not yet installed or validated on the server)
- Podman/Quadlet service setup, NGINX reverse proxy, and Qdrant deployment
- Linux GPU telemetry for the Proxmox host
- Real inference pipeline

The host preparation script only inventories the host and optionally installs
base tools after previewing an apt plan. It does not install the stack above.
Keep ROCm and GPU-dependent installation blocked until compatibility is
checked for the actual Proxmox release, running kernel, RX 6800 XT, and pinned
component versions. AMD's published matrix currently does not list the
planned GPU/Proxmox combination as officially supported.

## Phase 4 — Advanced Features

- Explicit, cited web research through self-hosted SearXNG
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

## Phase 5 — Polish

- Animations
- Theme switching
- Mobile layout
- Collapsible sidebar

See the [Linux/Proxmox transition runbook](./linux-proxmox-transition.md) for
deployment decisions, blockers, and acceptance criteria.
