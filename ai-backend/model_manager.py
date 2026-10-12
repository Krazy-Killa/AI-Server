# model_manager.py

# Placeholder model registry (will be replaced with real model loading later)
MODELS = {
    "llama3-8b": {
        "name": "Llama 3 8B",
        "type": "chat",
        "vram": 6.1,
        "status": "ready"
    },
    "mistral-7b": {
        "name": "Mistral 7B",
        "type": "reasoning",
        "vram": 4.8,
        "status": "ready"
    },
    "phi3-medium": {
        "name": "Phi-3 Medium",
        "type": "utility",
        "vram": 3.2,
        "status": "ready"
    },
    "sdxl": {
        "name": "SDXL",
        "type": "image",
        "vram": 7.4,
        "status": "ready"
    }
}

ACTIVE_MODEL = "llama3-8b"

def list_models():
    """Return all available models."""
    return MODELS

def get_active_model():
    """Return the currently active model."""
    return MODELS.get(ACTIVE_MODEL)

def select_model(model_id: str):
    """Switch active model."""
    global ACTIVE_MODEL
    if model_id in MODELS:
        ACTIVE_MODEL = model_id
        return True
    return False
