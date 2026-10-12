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
- Sends chat messages and model selection commands
- Displays backend online/offline status

## Backend

- FastAPI application
- Modular design:
  - system_stats.py
  - model_manager.py
  - bot_manager.py
  - gpu_stub.py
  - gpu_llm.py
  - gpu_rocm.py
- Provides REST endpoints for all dashboard features
- Will later support WebSocket streaming

## Discord Bot

- Python bot connected to backend
- Slash commands for chat, model selection, diagnostics
- Logs streamed to dashboard

## GPU Pipeline

- Currently stubbed
- Will support:
  - llama.cpp (Windows)
  - ROCm + vLLM (Linux server)
