import psutil

def get_system_stats():
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.5)

    # RAM usage
    ram = psutil.virtual_memory()
    ram_percent = ram.percent

    # Placeholder GPU stats (until ROCm is installed)
    # Later we will use rocm-smi or python bindings
    gpu_percent = 32
    vram_used = 6.1
    vram_total = 16

    return {
        "gpu": gpu_percent,
        "vram_used": vram_used,
        "vram_total": vram_total,
        "cpu": cpu_percent,
        "ram": ram_percent
    }
