"""Shared shape for GPU telemetry returned to the dashboard."""

from typing import TypedDict


class GpuTelemetry(TypedDict):
    gpu_load: int | None
    gpu_adapter: str | None
    gpu_engine: str | None
    gpu_status: str
    gpu_error: str | None
    vram_used: float | None
    vram_total: float | None
