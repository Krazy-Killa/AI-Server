# Backend Documentation

## Structure

ai-backend/
    main.py
    system_stats.py
    model_manager.py
    bot_manager.py
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
- CPU, RAM, GPU telemetry  
- Stubbed GPU stats for now  

model_manager.py  
- Model registry  
- Model selection  
- Metadata (VRAM usage, type)  

bot_manager.py  
- Discord bot status  
- Logs  
- Commands  

gpu_stub.py  
- Fake GPU load + VRAM usage  
- Used for frontend testing  

gpu_llm.py  
- llama.cpp integration (Windows)  

gpu_rocm.py  
- ROCm + vLLM integration (Linux)  

## Future Additions

- WebSocket streaming  
- Real inference pipeline  
- Persistent logs  
- Config loader
