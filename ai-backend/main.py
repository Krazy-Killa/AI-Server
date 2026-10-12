import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load project configuration before importing modules that read environment variables.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from system_stats import get_system_stats
from gpu.windows_gpu import get_gpu_load
from gpu.gpu_llm import LLMRuntimeError, run_llm
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

# Allow dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
