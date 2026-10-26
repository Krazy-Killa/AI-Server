from fastapi import APIRouter

from api import runtime
from api.routes.chat import chat_endpoint

router = APIRouter()


@router.get("/api/system")
async def system_endpoint():
    stats = runtime.get_system_stats()
    stats["activity_mode"] = (
        "diagnostics" if runtime.diagnostics_monitor.is_running else None
    )
    return stats

@router.get("/api/proxmox/vms")
async def proxmox_vm_inventory():
    if runtime.proxmox_inventory_client is None:
        return {
            "configured": False,
            "status": "not_configured",
            "guests": [],
            "count": 0,
            "observed_at": None,
        }

    try:
        guests = await runtime.asyncio.to_thread(runtime.proxmox_inventory_client.list_guests)
    except runtime.ProxmoxInventoryError as error:
        runtime.logger.warning("Proxmox VM inventory request failed: %s", error)
        raise runtime.HTTPException(
            status_code=503,
            detail="Proxmox VM inventory is unavailable.",
        ) from error

    return {
        "configured": True,
        "status": "connected",
        "guests": guests,
        "count": len(guests),
        "observed_at": runtime.time.strftime("%Y-%m-%dT%H:%M:%SZ", runtime.time.gmtime()),
    }

@router.get("/api/backend/logs")
async def backend_logs(limit: int = runtime.Query(default=200, ge=1, le=runtime.MAX_LOG_LINES)):
    log_file = runtime.settings.log_directory / "backend.log"
    try:
        logs = await runtime.asyncio.to_thread(runtime.read_recent_log_lines, log_file, limit)
    except FileNotFoundError as error:
        raise runtime.HTTPException(
            status_code=404, detail="Backend log file is not available."
        ) from error
    except OSError as error:
        runtime.logger.exception("Could not read the backend log file.")
        raise runtime.HTTPException(
            status_code=500, detail="Backend log file could not be read."
        ) from error
    return {"logs": logs, "count": len(logs)}

@router.get("/api/diagnostics/status")
async def diagnostics_status():
    observations = runtime.diagnostics_monitor.get_observations()
    incidents = runtime.diagnostics_monitor.get_incidents()
    latest = observations[-1] if observations else None
    return {
        "mode": "observe_only",
        "storage": "sqlite",
        "status": latest.status if latest else "not_run",
        "latest_observation": runtime.observation_to_dict(latest) if latest else None,
        "open_incidents": sum(incident.status == "open" for incident in incidents),
        "total_incidents": len(incidents),
    }

@router.get("/api/diagnostics/observations")
async def diagnostics_observations(limit: int = runtime.Query(default=20, ge=1, le=100)):
    observations = runtime.diagnostics_monitor.get_observations()[-limit:]
    return {
        "observations": [runtime.observation_to_dict(item) for item in observations],
        "count": len(observations),
    }

@router.get("/api/diagnostics/incidents")
async def diagnostics_incidents(
    status: runtime.Literal["all", "open", "resolved"] = runtime.Query(default="all"),
    limit: int = runtime.Query(default=100, ge=1, le=500),
):
    incidents = runtime.diagnostics_monitor.get_incidents()
    if status != "all":
        incidents = [incident for incident in incidents if incident.status == status]
    incidents = incidents[-limit:]
    return {
        "incidents": [runtime.asdict(incident) for incident in incidents],
        "count": len(incidents),
    }

@router.get("/api/diagnostics/report")
async def diagnostics_report(observation_id: str = runtime.Query(min_length=1, max_length=80)):
    report = runtime.diagnostics_monitor.build_report(observation_id)
    if report is None:
        raise runtime.HTTPException(
            status_code=404, detail="Diagnostic observation was not found."
        )
    return report

@router.get("/api/diagnostics/runbooks")
async def diagnostics_runbooks(
    platform: runtime.Literal["proxmox-ve", "ai-server"] | None = None,
    signal: str | None = runtime.Query(default=None, min_length=1, max_length=120),
    limit: int = runtime.Query(default=50, ge=1, le=100),
):
    runbooks = runtime.list_runbooks(platform=platform, signal=signal)[:limit]
    return {
        "runbooks": [runbook.to_dict() for runbook in runbooks],
        "count": len(runbooks),
    }

@router.get("/api/diagnostics/runbooks/{runbook_id}")
async def diagnostics_runbook(runbook_id: str):
    runbook = runtime.get_runbook(runbook_id)
    if runbook is None:
        raise runtime.HTTPException(status_code=404, detail="Diagnostic runbook was not found.")
    return runbook.to_dict()

@router.get("/api/diagnostics/knowledge/search")
async def diagnostics_knowledge_search(
    query: str = runtime.Query(min_length=1, max_length=160),
    platform: runtime.Literal["proxmox-ve", "ai-server"] | None = None,
    limit: int = runtime.Query(default=10, ge=1, le=25),
):
    runbooks = runtime.search_runbooks(query, platform=platform, limit=limit)
    return {
        "query": query,
        "results": [runbook.to_dict() for runbook in runbooks],
        "count": len(runbooks),
    }

@router.post("/api/diagnostics/observe")
async def diagnostics_observe():
    try:
        observation = await runtime.asyncio.to_thread(runtime.diagnostics_monitor.run_observation)
    except runtime.DiagnosticsStoreError as error:
        runtime.logger.exception("Could not persist the diagnostics observation.")
        raise runtime.HTTPException(
            status_code=503,
            detail="Persistent diagnostics history is unavailable.",
        ) from error
    return runtime.observation_to_dict(observation)

@router.get("/api/bot/status")
async def bot_status():
    return runtime.get_bot_status()

@router.get("/api/bot/logs")
async def bot_logs():
    return runtime.get_bot_logs()

@router.post("/api/bot/heartbeat")
async def bot_heartbeat(req: runtime.BotHeartbeatRequest):
    restart_requested = runtime.update_bot_heartbeat(req.latency_ms, req.commands)
    return {"restart_requested": restart_requested}

@router.post("/api/bot/logs")
async def bot_log(req: runtime.BotLogRequest):
    runtime.add_bot_log(req.message)
    return {"success": True}

@router.post("/api/bot/restart")
async def bot_restart():
    if not runtime.restart_bot():
        raise runtime.HTTPException(status_code=409, detail="Discord bot is offline.")
    return {"status": "restart_requested"}

@router.get("/api/models")
async def models_list():
    return runtime.list_models()

@router.post("/api/model/select")
async def model_select(req: runtime.ModelSelectRequest):
    try:
        return await runtime.asyncio.to_thread(runtime.switch_model, req.model_id)
    except FileNotFoundError as error:
        raise runtime.HTTPException(status_code=404, detail=str(error)) from error
    except runtime.ModelSwitchError as error:
        runtime.logger.error("Could not switch llama.cpp model: %s", error)
        raise runtime.HTTPException(status_code=503, detail=str(error)) from error

@router.get("/api/vision")
async def vision_stub():
    return runtime.analyze_image_stub()

@router.post("/api/embed")
async def embed_stub(req: runtime.EmbedRequest):
    return runtime.embed_text_stub(req.text)

@router.get("/")
async def root():
    return {"status": "AI backend online"}

@router.get("/api/gpu")
async def gpu_stats():
    return runtime.get_gpu_load()

@router.post("/api/llm")
async def llm_endpoint(req: runtime.ChatRequest, request: runtime.Request):
    return await chat_endpoint(req, request)

@router.post("/api/vision/run")
async def vision_run(image: bytes):
    return runtime.run_image_model_stub(image)
