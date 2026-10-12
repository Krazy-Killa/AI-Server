<<<<<<< HEAD
# AI Command Interface

A local AI and homelab control interface with a browser dashboard, FastAPI
backend, and optional Discord bot.

## Project status

This project is being developed on Windows before the dedicated AI Server is
deployed. The RX 6800 XT is installed in the current development machine and
will be moved to the server after a replacement GPU is acquired. The planned
server will run Linux under Proxmox.

The dashboard and backend are prototypes. Chat is connected to the local
llama.cpp Qwen2.5 1.5B Instruct test model, and Windows GPU load/VRAM telemetry
is live. Three additional GGUF model files are installed; the Qwen3-8B and
Qwen2.5-Coder-7B-Instruct Q4_K_M models have both passed short Vulkan inference
tests with all model layers offloaded to the RX 6800 XT. The model page
discovers installed files and identifies which one llama.cpp has loaded;
the dropdown and model cards can switch the loaded model by safely restarting
the llama.cpp process.
Bot status/logs are still placeholders. UI panels for VMs, game servers, and
network services are planning views, not live controls.

## Current local test setup

The Windows test setup uses Python 3.12 and an isolated environment stored
outside the OneDrive project folder at `%LOCALAPPDATA%\AI-Server\venv`.
=======
# **AI Command Interface**
A unified control dashboard, backend API, and Discord bot designed for managing local AI models, system telemetry, GPU inference, and multi‑agent workflows. Built for AMD hardware (RX 6800 XT) and intended to run on a dedicated homelab server.
>>>>>>> d6edea5af0bcad77c51b93af819c7b6e01e4e20e

1. Run `setup-windows.bat` from the project root. This installs the backend,
   Discord bot, and ONNX Runtime DirectML dependencies, then runs a small ONNX
   inference smoke test through DirectML.
2. Download the Qwen2.5 1.5B Instruct GGUF as described in
   [docs/testing-environment.md](./docs/testing-environment.md).
3. Run `run-llama-server.bat` and leave its terminal open. This serves local
   inference through llama.cpp Vulkan on `127.0.0.1:8080`.
4. Run `run-backend.bat` to start the FastAPI API at
   `http://127.0.0.1:8000`.
5. In another terminal, run `run-dashboard.bat`. Open
   `http://127.0.0.1:8001`.

See [docs/testing-environment.md](./docs/testing-environment.md) for details
and limitations.

## Intended AI stack

- **LLMs:** llama.cpp with Vulkan for Windows testing; the RX 6800 XT was
  detected and completed a GGUF inference test with GPU layer offload. The
  local chat endpoint connects to the llama.cpp server using a Qwen2.5 1.5B
  Instruct test model. A separate backend still needs to be selected for
  Linux/Proxmox deployment.
- **Vision:** ONNX Runtime with DirectML for Windows testing.
- **Image generation:** DirectML for Windows testing; the specific framework
  and dependency environment are not selected yet.
- **Web research:** Explicit user-triggered SearXNG search with local-model
  summaries and source links; the SearXNG service still needs to be configured.
- **Website building:** Planned workspace-scoped coding assistance with user
  approval before file changes or commands.

DirectML is Windows-specific, so it is not the server deployment backend.
See [docs/gpu-plan.md](./docs/gpu-plan.md) for the platform distinction.

## Project layout

```text
ai-backend/       FastAPI API, system telemetry, local chat, GPU integration
ai-discord-bot/   Discord bot client for the backend
css/              Dashboard styles
docs/             Architecture, API, plans, and setup documentation
js/               Dashboard behavior
index.html        Dashboard interface
```

## Documentation

<<<<<<< HEAD
- [Project overview](./docs/overview.md)
- [Architecture](./docs/architecture.md)
- [Backend API](./docs/api.md)
- [Frontend](./docs/frontend.md)
- [Backend](./docs/backend.md)
- [GPU plan](./docs/gpu-plan.md)
- [Roadmap](./docs/roadmap.md)
- [Local testing environment](./docs/testing-environment.md)
=======
## **Development Environment**
- Visual Studio Code  
- GitHub Copilot enabled  
- FastAPI backend running locally  
- Dashboard served via Live Server or `python -m http.server`  
- RX 6800 XT available for testing GPU inference  
- Windows development environment (ROCm not installed)  

---

## **GPU Integration Plan**
The RX 6800 XT is currently installed in the main PC.

### **Supported on Windows**
- llama.cpp (HIP/DirectML)
- ONNX Runtime + DirectML
- Stable Diffusion (DirectML)

### **Requires Linux**
- ROCm  
- vLLM GPU mode  

The backend will eventually migrate to a dedicated server with ROCm installed.

---

## **Planned Features**
### Backend
- Replace stubs with real telemetry  
- Add model registry  
- Add logging system  
- Add WebSocket streaming  
- Integrate llama.cpp or vLLM  

### Frontend
- Scroll‑to‑bottom button  
- Message fade‑in animation  
- Collapsible sidebar  
- Theme switching  
- Model dropdown selector  

### Discord Bot
- Full slash command suite  
- Bot‑side logging  
- Model registry integration  

---

## **How to Run (Local Development)**

### **Backend**
```
cd ai-backend
python -m uvicorn main:app --host 0.0.0.0 --port 5000
```

### **Frontend**
```
cd ai-dashboard
python -m http.server 8000
```
Open:  
`http://localhost:8000`

### **Discord Bot**
```
cd discord-bot
python bot.py
```

---

## **Contributing**
This project is actively evolving. Contributions, refactors, and improvements are welcome — especially around:

- GPU inference  
- Model management  
- Frontend UI/UX  
- Logging and diagnostics  
- Documentation  

---

## **License**
MIT License (or whichever you choose later).

---

If you want, I can also generate:

- `docs/architecture.md`  
- `docs/api.md`  
- `docs/frontend-structure.md`  
- `docs/backend-structure.md`  
- `docs/gpu-plan.md`  

Just tell me which ones you want next.
>>>>>>> d6edea5af0bcad77c51b93af819c7b6e01e4e20e
