# Backend Documentation

## Structure

ai-backend/
    main.py
    api/
        runtime.py
        middleware.py
        routes/
            auth.py
            chat.py
            memory.py
            research.py
            operations.py
    config.py
    diagnostics.py
    memory_store.py
    logging_config.py
    system_stats.py
    model_manager.py
    bot_manager.py
    web_research.py
    gpu/
        windows_gpu.py
        gpu_stub.py
        gpu_llm.py
        gpu_rocm.py

## Modules

main.py
- Creates the FastAPI app and includes the routers.
- Preserves the `main:app` import path used by Uvicorn and the container.

api/runtime.py
- Loads `.env` and validated configuration before modules consume settings.
- Initializes shared service clients and stores; provides common chat-context,
  identity, and error helpers.

api/middleware.py
- Registers request authentication, authorization, CSRF/origin validation,
  request logging, and configured CORS handling.

api/routes/auth.py
- Login, session status, and logout endpoints.

api/routes/chat.py
- Local chat endpoints, including `/ws/chat`.

api/routes/memory.py
- Private conversation history, shared insights, and the admin-shared
  AI Interface conversation.

api/routes/research.py
- Complete and streamed `/api/research` endpoints.

api/routes/operations.py
- System/GPU telemetry, Proxmox inventory, backend logs, diagnostics,
  Discord-bot status, model selection, and placeholder endpoints.

The API routers share the runtime module's initialized services and settings;
the module split preserves the existing paths and authorization policy.
Protected conversation operations, shared-insight access, and signed-in
identity/shared-context handling are grouped with their corresponding chat or
memory router. WebSocket origin checks remain in the chat router; request
logging retains DEBUG-level handling for frequently polled paths.

config.py  
- Reads and validates environment settings once at import into a frozen
  `settings` object; invalid values stop startup with a clear message  
- Covers llama.cpp, model-switch options, SearXNG, CORS, chat limits, and logging  

web_research.py
- Searches SearXNG, retrieves a bounded set of public HTML pages, extracts
bounded text, and passes all external content to the model as untrusted
evidence. Redirect destinations and DNS-resolved IPs are revalidated.
- Supports complete JSON research responses and streamed answer chunks; failed
page fetches visibly fall back to the search excerpt.

diagnostics.py
- Performs only explicitly requested, read-only health checks and resource
  sampling
- Persists bounded observations, incident state, and audit events in the
  configured local SQLite memory database; reloads open incidents on startup
- Does not schedule checks, analyze logs, execute commands, or remediate

memory_store.py
- SQLite database for private account-scoped conversations, admin-published
  shared operational notes, and observe-only diagnostic history
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
- Obtains GPU readings through the platform provider
- Linux AMD telemetry reads `amdgpu` sysfs utilization and VRAM counters;
  Windows uses GPU Engine and dedicated-memory counters

gpu/windows_gpu.py
- Reads Windows GPU Engine and dedicated-memory counters for the AMD adapter  
- Uses a background worker to keep API telemetry requests responsive  

gpu/gpu_rocm.py
- Reads Linux `amdgpu` sysfs utilization and VRAM counters, with optional
  unambiguous hwmon temperature, power, and fan readings
- Does not require or validate ROCm/HIP; physical-host and service-permission
  checks remain outstanding

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

## Linux/Proxmox portability

The backend's common Python dependencies are listed in
`requirements.txt`; Windows DirectML packages are isolated in
`requirements-windows.txt`. Linux AMD GPU telemetry is implemented through
the kernel `amdgpu` sysfs interface and returns unavailable when required
counters cannot be read. It has deterministic fixture coverage, but has not
been validated on a Linux host or physical GPU. This telemetry does not
establish ROCm/HIP compute support. See the
[Linux/Proxmox transition runbook](../deployment/linux-proxmox-transition.md) before
deploying the backend or exposing it to other devices.

## Testing

From `ai-backend/`, install the development test client with
`python -m pip install -r requirements-dev.txt`, then run
`python -m unittest discover -s tests`. The test client is development-only;
production runtime dependencies remain in `requirements.txt`.

## Future Additions

- Live Linux/Proxmox GPU telemetry validation and inference integration
- Log shipping to a centralized destination
