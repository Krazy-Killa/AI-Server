# AI Command Interface — Project Overview

The AI Command Interface is a unified dashboard, backend API, and Discord bot designed to manage local AI models, system telemetry, GPU inference, and multi-agent workflows. It is optimized for AMD hardware (RX 6800 XT) and intended to run on a dedicated homelab server.

## Components
- **Frontend Dashboard** (HTML/CSS/JS)
- **FastAPI Backend** (Python)
- **Discord Bot** (Python)
- **Model Registry**
- **System Monitor**
- **AI Interface** (single admin-shared server console)
- **AI Chat** (private conversations and web research)
- **Local LLM Chat** (llama.cpp test integration)

## Current Status
The Windows build/prototype connects dashboard AI Chat to a local llama.cpp
Qwen2.5 1.5B Instruct model and reports live RX 6800 XT load and VRAM telemetry.
Dashboard authentication supports local accounts and explicitly mapped
Proxmox identities, with protected sessions and role-gated APIs; Proxmox and
production proxy deployment are not yet validated. Installed GGUF files are
discovered and can be selected for model switching; the backend confirms
which model is active and attempts recovery if a switch fails.
Discord heartbeat/status, operational logs, restart, command listing, and
model selection are connected to the optional bot service. Vision and image
generation still use placeholders. The VM panel has a backend-provided,
read-only Proxmox VM/container inventory when configured; VM management,
game-server, and network-service integrations remain unimplemented. Linux
GPU telemetry and runtime support remain to be implemented.
Windows remains the active build environment for shared application behavior.
An additional Proxmox VE 9.1-1 deployment/integration lab is running inside a
nested Hyper-V virtual machine on the Windows PC; the dashboard and backend
have been deployed there for manual loopback-only testing through an SSH
tunnel. This lab can support Linux/Proxmox implementation work, but GPU/ROCm,
physical hardware, production networking, and recovery behavior still require
validation on the eventual physical host.
The AI Interface has a single admin-shared, attributed transcript; private
AI Chat conversations remain scoped to each account.

## Goals
- Provide a unified control interface for local AI systems
- Support multiple models and inference backends
- Extend real GPU telemetry and inference to the Linux/Proxmox host
- Provide Discord bot control and monitoring
- Run on a dedicated AMD-powered server
