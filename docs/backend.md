# Backend Documentation

## Structure

ai-backend/
    main.py
    config.py
    memory_store.py
    logging_config.py
    system_stats.py
    model_manager.py
    bot_manager.py
    gpu/
        windows_gpu.py
        gpu_stub.py
        gpu_llm.py
        gpu_rocm.py

## Modules

main.py  
- FastAPI app  
- Route definitions, including the `/ws/chat` streaming endpoint  
- Protected conversation create/list/read/delete routes and turn persistence
- Admin-only shared-insight routes and signed-in identity/shared-context
  injection for dashboard chat and research
- CORS limited to configured origins, plus WebSocket origin checks  
- Request logging middleware (polled status endpoints log at DEBUG only)  

config.py  
- Reads and validates environment settings once at import into a frozen
  `settings` object; invalid values stop startup with a clear message  
- Covers llama.cpp, model-switch options, SearXNG, CORS, chat limits, and logging  

memory_store.py
- Separate SQLite database for private account-scoped conversations and
  admin-published shared operational notes
- Enforces ownership on conversation reads, writes, and deletion
- Provides bounded recent-turn context for local chat; source messages remain
  available in full for the account's history view
- Bounds admin shared context and does not expose it to non-admin or Discord
  service requests

logging_config.py  
- Console plus rotating `backend.log` in `AI_SERVER_LOG_DIR` (default
  `%LOCALAPPDATA%\AI-Server\logs`, or `~/AI-Server/logs`)  
- Chat message text is not logged  

system_stats.py  
- CPU and RAM telemetry on supported systems  
- Currently obtains live GPU telemetry through the Windows-only provider  
- Live dedicated VRAM usage and device-local capacity on Windows  

gpu/windows_gpu.py  
- Reads Windows GPU Engine and dedicated-memory counters for the AMD adapter  
- Uses a background worker to keep API telemetry requests responsive  

model_manager.py  
- Discovers installed GGUF files and reports their disk size and load status  
- Restarts only the verified loopback llama.cpp process when switching installed models  
- Waits for `/props` confirmation and attempts to restore the previous model after a failed load  

bot_manager.py  
- Discord bot status  
- Logs  
- Commands  

gpu_stub.py  
- Legacy placeholder GPU statistics and inference stubs  
- GPU placeholder statistics are no longer used by `/api/system` or `/api/gpu`  

gpu_llm.py  
- OpenAI-compatible chat requests to the local llama.cpp server, including streaming  

gpu_rocm.py  
- Placeholder only; Linux GPU telemetry/inference integration is not implemented  

## Linux/Proxmox portability

The backend's common Python dependencies are listed in
`requirements.txt`; Windows DirectML packages are isolated in
`requirements-windows.txt`. Linux GPU telemetry is not implemented: the
current provider returns unavailable off Windows, and `gpu_rocm.py` is a
stub. See the [Linux/Proxmox transition runbook](./linux-proxmox-transition.md)
before deploying the backend or exposing it to other devices.

## Testing

From `ai-backend/`, install the development test client with
`python -m pip install -r requirements-dev.txt`, then run
`python -m unittest discover -s tests`. The test client is development-only;
production runtime dependencies remain in `requirements.txt`.

## Future Additions

- Streaming for web research responses
- Linux/Proxmox GPU telemetry and inference integration
- Log shipping or dashboard log viewing for backend logs
