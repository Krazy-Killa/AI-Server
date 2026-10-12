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
- Linux/Proxmox host GPU telemetry after the RX 6800 XT is moved to the server
- Logging system
- Config loader
- WebSocket streaming

## Phase 3 — GPU Integration

- llama.cpp Vulkan (Windows test build complete)
- Linux GPU runtime setup on the Proxmox host
- vLLM GPU mode
- Real inference pipeline

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
