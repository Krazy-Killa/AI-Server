# gpu/gpu_stub.py

def get_gpu_stats_stub():
    """Return placeholder GPU stats until ROCm is available."""
    return {
        "gpu_load": 32,
        "gpu_temp": 54,
        "vram_used": 6.1,
        "vram_total": 16,
        "power_draw": 120,
        "fan_speed": 40,
        "status": "stub"
    }

def run_llm_stub(prompt: str):
    """Simulated LLM response."""
    return {
        "response": f"[STUB] LLM received: '{prompt}'. Real inference will activate once GPU is online.",
        "tokens": 12,
        "latency_ms": 50
    }

def run_image_model_stub(image_bytes: bytes):
    """Simulated image model output."""
    return {
        "status": "stub",
        "description": "Image model not yet connected.",
        "size": len(image_bytes)
    }
