# Backend Documentation

## Structure

ai-backend/
    main.py
    system_stats.py
    model_manager.py
    bot_manager.py
    gpu/
        windows_gpu.py
        gpu_stub.py
        gpu_llm.py
        gpu_rocm.py
    config.py

## Modules

main.py  
- FastAPI app  
- Route definitions  
- CORS config  

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
- OpenAI-compatible chat requests to the local llama.cpp server  

gpu_rocm.py  
- Placeholder only; Linux GPU telemetry/inference integration is not implemented  

## Linux/Proxmox portability

The backend's common Python dependencies are listed in
`requirements.txt`; Windows DirectML packages are isolated in
`requirements-windows.txt`. Linux GPU telemetry is not implemented: the
current provider returns unavailable off Windows, and `gpu_rocm.py` is a
stub. See the [Linux/Proxmox transition runbook](./linux-proxmox-transition.md)
before deploying the backend or exposing it to other devices.

## Future Additions

- WebSocket streaming  
- Linux/Proxmox GPU telemetry and inference integration
- Persistent logs  
- Config loader
