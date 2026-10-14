import asyncio
import logging
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from time import monotonic
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi import HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load project configuration before importing modules that read environment variables.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from config import settings
from logging_config import MAX_LOG_LINES, read_recent_log_lines, setup_logging
from diagnostics import (
    DiagnosticsMonitor,
    observation_to_dict,
)

setup_logging(settings)

from system_stats import get_system_stats
from gpu.windows_gpu import get_gpu_load
from gpu.gpu_llm import LLMRuntimeError, run_llm, stream_llm
from web_research import ResearchRuntimeError, run_research
from bot_manager import (
    add_bot_log,
    get_bot_status,
    get_bot_logs,
    restart_bot,
    update_bot_heartbeat,
)
from model_manager import ModelSwitchError, list_models, switch_model
from vision_stub import analyze_image_stub
from embed_stub import embed_text_stub

app = FastAPI()
logger = logging.getLogger(__name__)
diagnostics_monitor = DiagnosticsMonitor()
logger.info("Backend starting (log level %s, logs in %s).", settings.log_level, settings.log_directory)

# Browsers send these polled paths constantly; log them at DEBUG only.
QUIET_PATHS = {
    "/api/system",
    "/api/bot/status",
    "/api/bot/logs",
    "/api/bot/heartbeat",
    "/api/backend/logs",
    "/api/diagnostics/status",
    "/api/diagnostics/observations",
    "/api/diagnostics/incidents",
}

# Allow dashboard access from configured origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = monotonic()
    level = logging.DEBUG if request.url.path in QUIET_PATHS else logging.INFO
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("%s %s failed", request.method, request.url.path)
        raise
    logger.log(
        level,
        "%s %s -> %d (%d ms)",
        request.method,
        request.url.path,
        response.status_code,
        round((monotonic() - started_at) * 1000),
    )
    return response

# Chat request model
class ChatRequest(BaseModel):
    message: str

class ResearchRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class ModelSelectRequest(BaseModel):
    model_id: str

class EmbedRequest(BaseModel):
    text: str

class BotHeartbeatRequest(BaseModel):
    latency_ms: int | None = Field(default=None, ge=0)
    commands: list[str] = Field(default_factory=list, max_length=50)

class BotLogRequest(BaseModel):
    message: str = Field(min_length=1, max_length=200)

# ===============================
# /api/chat — AI Chat Endpoint
# ===============================
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        return await asyncio.to_thread(run_llm, req.message)
    except LLMRuntimeError as error:
        logger.warning("Local LLM request failed: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error

# ===============================
# /ws/chat — Streaming AI Chat
# ===============================
async def _send_error(websocket: WebSocket, detail: str) -> None:
    await websocket.send_json({"type": "error", "detail": detail})


@app.websocket("/ws/chat")
async def chat_stream_endpoint(websocket: WebSocket):
    # Browsers do not apply CORS to WebSockets, so check the origin explicitly.
    origin = websocket.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in settings.cors_origins:
        logger.warning("Rejected chat WebSocket from origin %s", origin)
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("Chat WebSocket connected")
    try:
        while True:
            try:
                payload = await websocket.receive_json()
            except ValueError:
                await _send_error(websocket, "Messages must be valid JSON.")
                continue

            message = payload.get("message") if isinstance(payload, dict) else None
            if not isinstance(message, str) or not message.strip():
                await _send_error(websocket, "A non-empty 'message' string is required.")
                continue
            if len(message) > settings.max_chat_chars:
                await _send_error(
                    websocket, f"Message exceeds {settings.max_chat_chars} characters."
                )
                continue

            started_at = monotonic()
            stream = stream_llm(message)
            sentinel = object()
            try:
                while True:
                    chunk = await asyncio.to_thread(next, stream, sentinel)
                    if chunk is sentinel:
                        break
                    await websocket.send_json({"type": "token", "content": chunk})
                await websocket.send_json(
                    {"type": "done", "latency_ms": round((monotonic() - started_at) * 1000)}
                )
            except LLMRuntimeError as error:
                logger.warning("Streaming LLM request failed: %s", error)
                await _send_error(websocket, str(error))
            finally:
                # Closing the generator stops llama.cpp generation if the client left early.
                with suppress(ValueError):
                    stream.close()
    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected")


# ===============================
# /api/research — SearXNG + local LLM
# ===============================
@app.post("/api/research")
async def research_endpoint(req: ResearchRequest):
    try:
        return await asyncio.to_thread(run_research, req.message)
    except (ResearchRuntimeError, LLMRuntimeError) as error:
        logger.warning("Web research request failed: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error

# ===============================
# /api/system — Live System Stats
# ===============================
@app.get("/api/system")
async def system_endpoint():
    return get_system_stats()

# ===============================
# /api/backend/logs
# ===============================
@app.get("/api/backend/logs")
async def backend_logs(limit: int = Query(default=200, ge=1, le=MAX_LOG_LINES)):
    log_file = settings.log_directory / "backend.log"
    try:
        logs = await asyncio.to_thread(read_recent_log_lines, log_file, limit)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Backend log file is not available."
        ) from error
    except OSError as error:
        logger.exception("Could not read the backend log file.")
        raise HTTPException(
            status_code=500, detail="Backend log file could not be read."
        ) from error
    return {"logs": logs, "count": len(logs)}

# ===============================
# /api/diagnostics/*
# ===============================
@app.get("/api/diagnostics/status")
async def diagnostics_status():
    observations = diagnostics_monitor.get_observations()
    incidents = diagnostics_monitor.get_incidents()
    latest = observations[-1] if observations else None
    return {
        "mode": "observe_only",
        "storage": "process_local",
        "status": latest.status if latest else "not_run",
        "latest_observation": observation_to_dict(latest) if latest else None,
        "open_incidents": sum(incident.status == "open" for incident in incidents),
        "total_incidents": len(incidents),
    }


@app.get("/api/diagnostics/observations")
async def diagnostics_observations(limit: int = Query(default=20, ge=1, le=100)):
    observations = diagnostics_monitor.get_observations()[-limit:]
    return {
        "observations": [observation_to_dict(item) for item in observations],
        "count": len(observations),
    }


@app.get("/api/diagnostics/incidents")
async def diagnostics_incidents(
    status: Literal["all", "open", "resolved"] = Query(default="all"),
    limit: int = Query(default=100, ge=1, le=500),
):
    incidents = diagnostics_monitor.get_incidents()
    if status != "all":
        incidents = [incident for incident in incidents if incident.status == status]
    incidents = incidents[-limit:]
    return {
        "incidents": [asdict(incident) for incident in incidents],
        "count": len(incidents),
    }


@app.post("/api/diagnostics/observe")
async def diagnostics_observe():
    observation = await asyncio.to_thread(diagnostics_monitor.run_observation)
    return observation_to_dict(observation)

# ===============================
# /api/bot/status
# ===============================
@app.get("/api/bot/status")
async def bot_status():
    return get_bot_status()

# ===============================
# /api/bot/logs
# ===============================
@app.get("/api/bot/logs")
async def bot_logs():
    return get_bot_logs()

# ===============================
# /api/bot/heartbeat
# ===============================
@app.post("/api/bot/heartbeat")
async def bot_heartbeat(req: BotHeartbeatRequest):
    restart_requested = update_bot_heartbeat(req.latency_ms, req.commands)
    return {"restart_requested": restart_requested}

# ===============================
# /api/bot/logs
# ===============================
@app.post("/api/bot/logs")
async def bot_log(req: BotLogRequest):
    add_bot_log(req.message)
    return {"success": True}

# ===============================
# /api/bot/restart
# ===============================
@app.post("/api/bot/restart")
async def bot_restart():
    if not restart_bot():
        raise HTTPException(status_code=409, detail="Discord bot is offline.")
    return {"status": "restart_requested"}

# ===============================
# /api/models — List Models
# ===============================
@app.get("/api/models")
async def models_list():
    return list_models()

# ===============================
# /api/model/select — Switch Model
# ===============================
@app.post("/api/model/select")
async def model_select(req: ModelSelectRequest):
    try:
        return await asyncio.to_thread(switch_model, req.model_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ModelSwitchError as error:
        logger.error("Could not switch llama.cpp model: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error

# ===============================
# /api/vision — Stub
# ===============================
@app.get("/api/vision")
async def vision_stub():
    return analyze_image_stub()

# ===============================
# /api/embed — Stub
# ===============================
@app.post("/api/embed")
async def embed_stub(req: EmbedRequest):
    return embed_text_stub(req.text)

# ===============================
# Root endpoint
# ===============================
@app.get("/")
async def root():
    return {"status": "AI backend online"}
from gpu.gpu_stub import (
    run_image_model_stub
)

@app.get("/api/gpu")
async def gpu_stats():
    return get_gpu_load()

@app.post("/api/llm")
async def llm_endpoint(req: ChatRequest):
    return await chat_endpoint(req)

@app.post("/api/vision/run")
async def vision_run(image: bytes):
    return run_image_model_stub(image)
