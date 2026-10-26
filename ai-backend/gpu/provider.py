"""Select the GPU telemetry reader supported by the current operating system."""

from __future__ import annotations

import platform

from gpu.telemetry import GpuTelemetry


def _unavailable(message: str) -> GpuTelemetry:
    return {
        "gpu_load": None,
        "gpu_adapter": None,
        "gpu_engine": None,
        "gpu_status": "unavailable",
        "gpu_error": message,
        "vram_used": None,
        "vram_total": None,
    }


def get_gpu_load() -> GpuTelemetry:
    operating_system = platform.system().lower()
    if operating_system == "windows":
        from gpu.windows_gpu import get_gpu_load as get_windows_gpu_load

        return get_windows_gpu_load()
    if operating_system == "linux":
        from gpu.gpu_rocm import get_gpu_load as get_linux_gpu_load

        return get_linux_gpu_load()
    return _unavailable(
        f"GPU telemetry is not implemented for {platform.system()}."
    )
