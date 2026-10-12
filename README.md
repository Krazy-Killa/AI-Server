# **AI Command Interface**
A unified control dashboard, backend API, and Discord bot designed for managing local AI models, system telemetry, GPU inference, and multi‑agent workflows. Built for AMD hardware (RX 6800 XT) and intended to run on a dedicated homelab server.

This project is currently in active development and fully functional in a local test environment.

---

## **Project Overview**
The AI Command Interface consists of three major components:

### **1. Frontend Dashboard (HTML/CSS/JS)**
A real‑time control interface featuring:

- Chat panel with user/AI message flow  
- Model selection and status  
- System monitor (GPU, VRAM, CPU, RAM)  
- Discord bot logs and controls  
- Settings panel (theme, accent colors)  
- Backend online/offline indicator  
- Fully responsive layout with internal scrolling  

### **2. FastAPI Backend (Python)**
Provides API endpoints for:

- System telemetry  
- Chat responses  
- Model management  
- Discord bot integration  
- Logging and diagnostics  

Currently uses **stub modules** for GPU, LLM, and bot logic, allowing full frontend testing before real GPU inference is added.

### **3. Discord Bot (Python)**
Connects to the backend and supports:

- Slash commands  
- Model listing  
- Model switching  
- Chat responses  
- Bot status reporting  

---

## **Current Features**
### ✔ Fully working dashboard UI  
### ✔ FastAPI backend with stub endpoints  
### ✔ Discord bot connected to backend  
### ✔ Live polling for system stats  
### ✔ Chat interface with message styling  
### ✔ Model cards with VRAM usage bars  
### ✔ System monitor with animated bars  
### ✔ Backend online/offline indicator  
### ✔ Sidebar navigation  
### ✔ Settings panel with color swatches  

All components run locally and communicate through `http://localhost:5000`.

---

## **Architecture**
```
ai-backend/
    main.py
    system_stats.py
    model_manager.py
    bot_manager.py
    gpu_stub.py
    gpu_llm.py
    gpu_rocm.py
    config.py

ai-dashboard/
    index.html
    css/style.css
    js/app.js

discord-bot/
    bot.py

docs/
    overview.md
    architecture.md
    api.md
```

---

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
