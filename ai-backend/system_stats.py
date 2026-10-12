import psutil

from gpu.windows_gpu import get_gpu_load


def get_system_stats():
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.5)

    # RAM usage
    ram = psutil.virtual_memory()
    ram_percent = ram.percent

    gpu = get_gpu_load()

    return {
        "gpu": gpu["gpu_load"],
        "gpu_adapter": gpu["gpu_adapter"],
        "gpu_engine": gpu["gpu_engine"],
        "gpu_status": gpu["gpu_status"],
        "gpu_error": gpu["gpu_error"],
        "vram_used": gpu["vram_used"],
        "vram_total": gpu["vram_total"],
        "cpu": cpu_percent,
        "ram": ram_percent
    }
