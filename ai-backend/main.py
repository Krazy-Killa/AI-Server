from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from system_stats import get_system_stats
from bot_manager import get_bot_status, get_bot_logs, restart_bot
from model_manager import list_models, select_model, get_active_model
from vision_stub import analyze_image_stub
from embed_stub import embed_text_stub

app = FastAPI()

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

class ModelSelectRequest(BaseModel):
    model_id: str

class EmbedRequest(BaseModel):
    text: str

# ===============================
# /api/chat — AI Chat Endpoint
# ===============================
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    user_msg = req.message
    reply = f"AI backend received: '{user_msg}'. Real inference will be enabled once GPU is online."
    return {"reply": reply}

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
# /api/bot/restart
# ===============================
@app.post("/api/bot/restart")
async def bot_restart():
    restart_bot()
    return {"status": "bot restarted"}

# ===============================
# /api/models — List Models
# ===============================
@app.get("/api/models")
async def models_list():
    return {
        "active": get_active_model(),
        "models": list_models()
    }

# ===============================
# /api/model/select — Switch Model
# ===============================
@app.post("/api/model/select")
async def model_select(req: ModelSelectRequest):
    success = select_model(req.model_id)
    return {"success": success}

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
    get_gpu_stats_stub,
    run_llm_stub,
    run_image_model_stub
)

@app.get("/api/gpu")
async def gpu_stats():
    return get_gpu_stats_stub()

@app.post("/api/llm")
async def llm_endpoint(req: ChatRequest):
    return run_llm_stub(req.message)

@app.post("/api/vision/run")
async def vision_run(image: bytes):
    return run_image_model_stub(image)
