# gpu/gpu_rocm.py

# This file will be filled in once the RX 6800 XT arrives and ROCm is installed.

def get_gpu_stats():
    """
    Real GPU stats using ROCm.
    Expected return:
    {
        "gpu_load": int,
        "gpu_temp": int,
        "vram_used": float,
        "vram_total": float,
        "power_draw": int,
        "fan_speed": int,
        "status": "ok"
    }
    """
    raise NotImplementedError("ROCm not yet available.")

def get_vram_usage():
    """Return VRAM usage."""
    raise NotImplementedError("ROCm not yet available.")

def get_gpu_temp():
    """Return GPU temperature."""
    raise NotImplementedError("ROCm not yet available.")
