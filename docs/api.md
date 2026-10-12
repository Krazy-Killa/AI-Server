# Backend API Documentation

Base URL:
http://localhost:5000

---

## System Endpoints

GET /api/system  
Returns system telemetry:
- GPU load
- VRAM usage
- CPU usage
- RAM usage

---

## Chat Endpoints

POST /api/chat  
Body:
{
  "message": "Hello"
}

Returns:
- AI response (stub or real inference)

---

## Model Endpoints

GET /api/models  
Returns list of available models.

POST /api/model/select  
Body:
{
  "model": "llama3-8b"
}

---

## Discord Bot Endpoints

GET /api/bot/status  
Returns:
- Online/offline
- Latency
- Active model

GET /api/bot/logs  
Returns:
- Recent bot log lines

---

## Vision / Embedding (Stub)

POST /api/vision  
POST /api/embed
