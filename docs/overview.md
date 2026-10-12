# AI Command Interface — Project Overview

The AI Command Interface is a unified dashboard, backend API, and Discord bot designed to manage local AI models, system telemetry, GPU inference, and multi-agent workflows. It is optimized for AMD hardware (RX 6800 XT) and intended to run on a dedicated homelab server.

## Components
- **Frontend Dashboard** (HTML/CSS/JS)
- **FastAPI Backend** (Python)
- **Discord Bot** (Python)
- **Model Registry**
- **System Monitor**
- **Chat Interface**
- **GPU Inference Pipeline** (future)

## Current Status
The system runs fully in a local test environment using stub modules for GPU, LLM, and bot logic. The dashboard communicates with the backend and displays live telemetry, chat messages, model cards, and bot logs.

## Goals
- Provide a unified control interface for local AI systems
- Support multiple models and inference backends
- Integrate real GPU telemetry and inference
- Provide Discord bot control and monitoring
- Run on a dedicated AMD-powered server
