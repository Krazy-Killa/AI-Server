# AI Command Interface — Project Overview

The AI Command Interface is a unified dashboard, backend API, and Discord bot designed to manage local AI models, system telemetry, GPU inference, and multi-agent workflows. It is optimized for AMD hardware (RX 6800 XT) and intended to run on a dedicated homelab server.

## Components
- **Frontend Dashboard** (HTML/CSS/JS)
- **FastAPI Backend** (Python)
- **Discord Bot** (Python)
- **Model Registry**
- **System Monitor**
- **Chat Interface**
- **Local LLM Chat** (llama.cpp test integration)

## Current Status
The Windows test setup connects dashboard chat to a local llama.cpp Qwen2.5
1.5B Instruct model and reports live RX 6800 XT load and VRAM telemetry.
Model-registry actions, bot status/logs, vision, and image generation still
have limitations: installed GGUF files are discovered, but only the model
already loaded by llama.cpp is selectable; bot status/logs, vision, and image
generation still use placeholders. VM, game-server, and network-service panels
are planning views rather than live controls. Linux/Proxmox telemetry and
runtime support remain to be implemented.

## Goals
- Provide a unified control interface for local AI systems
- Support multiple models and inference backends
- Extend real GPU telemetry and inference to the Linux/Proxmox host
- Provide Discord bot control and monitoring
- Run on a dedicated AMD-powered server
