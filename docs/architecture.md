# System Architecture

## High-Level Diagram

Frontend (Dashboard)
    ↓ REST API
Backend (FastAPI)
    ↓ Internal Modules
GPU / LLM / Bot / System Stats

## Frontend

- Pure HTML/CSS/JS
- Panels for Chat, Models, System Monitor, Discord Bot, Settings
- Polls backend for telemetry and logs
- Sends chat messages and confirms the currently loaded model
- Sends explicitly selected web-research requests and displays source links
- Displays backend online/offline status

## Backend

- FastAPI application
- Modular design:
  - system_stats.py
  - model_manager.py
  - bot_manager.py
  - gpu/windows_gpu.py
  - gpu/gpu_stub.py
  - gpu/gpu_llm.py
  - gpu/gpu_rocm.py
- Provides REST endpoints for all dashboard features
- Streams local chat replies over WebSocket (`/ws/chat`)

## Web Research

- The user explicitly enables Research Web for a message; ordinary chat stays
  local and does not search the web.
- FastAPI queries a self-hosted SearXNG instance, passes a small set of
  untrusted search excerpts to the local llama.cpp model, and returns a
  summary with source links.
- SearXNG must enable JSON output and be configured through
  `SEARXNG_BASE_URL`; the Linux/Proxmox service deployment remains pending.
- Website-building assistance is planned as workspace-scoped work, requiring
  user approval before file changes or command execution.

## Discord Bot

- Python bot connected to backend
- Slash commands for chat, model selection, diagnostics
- Logs streamed to dashboard

## GPU Pipeline

- Windows testing uses llama.cpp Vulkan for local Qwen2.5 1.5B chat and reads
  RX 6800 XT load and dedicated-memory usage from live Windows counters.
- The Proxmox host will run its AI runtime directly and read GPU telemetry
  from its host GPU; Linux provider implementation remains future work.

## Proxmox Deployment

- The dashboard web server, FastAPI backend, and AI runtime are planned to run
  directly on the Proxmox host.
- Host GPU telemetry will read the RX 6800 XT used by the host AI runtime.
- The RX 6800 XT is intended for direct Proxmox host use; GPU passthrough to a
  VM is not part of the deployment plan. Host workloads may share GPU
  resources.
- Linux runtime, GPU telemetry, service management, and safe remote UI/API
  access remain to be validated. See the
  [Linux/Proxmox transition runbook](./linux-proxmox-transition.md).
