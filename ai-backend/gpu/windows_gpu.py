"""Windows GPU utilization from Windows GPU Engine performance counters."""

from __future__ import annotations

from functools import lru_cache
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Lock, Thread
from time import sleep
from typing import Any

logger = logging.getLogger(__name__)
_GPU_LOAD_REFRESH_SECONDS = 1
_GPU_LOAD_LOCK = Lock()
_GPU_LOAD_CACHE: dict[str, int | float | str | None] = {
    "gpu_load": None,
    "gpu_adapter": None,
    "gpu_engine": None,
    "vram_used": None,
    "vram_total": None,
    "gpu_status": "checking",
    "gpu_error": None,
}
_GPU_LOAD_WORKER: Thread | None = None


def _device_properties(document: dict[str, Any]) -> dict[str, Any]:
    return document["capabilities"]["device"]["properties"]


def _get_device_local_vram_total(vulkaninfo: str, device_name: str) -> int:
    result = subprocess.run(
        [vulkaninfo, "--text"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    device_sections = list(re.finditer(r"(?m)^GPU\d+:\s*$", result.stdout))
    for index, match in enumerate(device_sections):
        end = device_sections[index + 1].start() if index + 1 < len(device_sections) else len(result.stdout)
        section = result.stdout[match.end() : end]
        reported_name = re.search(r"(?m)^\s*deviceName\s*=\s*(.+?)\s*$", section)
        if reported_name is None or reported_name.group(1) != device_name:
            continue

        memory_properties = re.search(
            r"VkPhysicalDeviceMemoryProperties:.*?(?=\n\s*memoryTypes: count)",
            section,
            re.DOTALL,
        )
        if memory_properties is None:
            break

        local_heaps = []
        for heap in re.finditer(
            r"memoryHeaps\[\d+\]:\s+size\s*=\s*(\d+)(.*?)(?=\n\s*memoryHeaps\[|\Z)",
            memory_properties.group(),
            re.DOTALL,
        ):
            if "MEMORY_HEAP_DEVICE_LOCAL_BIT" in heap.group(2):
                local_heaps.append(int(heap.group(1)))
        if local_heaps:
            return max(local_heaps)
        break

    raise RuntimeError(f"Vulkan did not report a device-local memory heap for {device_name}.")


@lru_cache(maxsize=1)
def _get_amd_gpu() -> tuple[str, str, int]:
    vulkaninfo = shutil.which("vulkaninfo.exe") or shutil.which("vulkaninfo")
    if vulkaninfo is None:
        raise FileNotFoundError("vulkaninfo is required to identify the AMD GPU adapter.")

    with tempfile.TemporaryDirectory(prefix="ai-server-vulkan-") as temp_dir:
        subprocess.run(
            [vulkaninfo, "--json"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        devices: list[tuple[str, str]] = []
        for json_path in Path(temp_dir).glob("VP_VULKANINFO_*.json"):
            document = json.loads(json_path.read_text(encoding="utf-8"))
            properties = _device_properties(document)
            device = properties["VkPhysicalDeviceProperties"]
            if (
                device.get("vendorID") != 0x1002
                or device.get("deviceType") != "VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU"
            ):
                continue

            vulkan11 = properties["VkPhysicalDeviceVulkan11Properties"]
            luid = vulkan11["deviceLUID"]
            if not vulkan11["deviceLUIDValid"] or len(luid) != 8:
                continue

            low = int.from_bytes(bytes(luid[:4]), byteorder="little")
            high = int.from_bytes(bytes(luid[4:]), byteorder="little")
            devices.append(
                (
                    device["deviceName"],
                    f"0x{high:08x}_0x{low:08x}",
                )
            )

    rx_6800_xt = [device for device in devices if "RX 6800 XT" in device[0]]
    if len(rx_6800_xt) == 1:
        adapter, luid = rx_6800_xt[0]
    elif len(devices) == 1:
        adapter, luid = devices[0]
    elif not devices:
        raise RuntimeError("Vulkan did not report an AMD discrete GPU with a valid adapter LUID.")
    else:
        raise RuntimeError("Multiple AMD discrete GPUs were found; the telemetry adapter is ambiguous.")

    return adapter, luid, _get_device_local_vram_total(vulkaninfo, adapter)


def _query_gpu_engine_load(luid: str) -> tuple[int, str, int]:
    counter_path = (
        f"\\GPU Engine(pid_*_luid_{luid}_phys_0_eng_*_engtype_*)"
        "\\Utilization Percentage"
    )
    memory_counter_path = f"\\GPU Adapter Memory(luid_{luid}_phys_0)\\Dedicated Usage"
    script = f"""
$ErrorActionPreference = 'Stop'
$samples = (Get-Counter -Counter '{counter_path}', '{memory_counter_path}' -SampleInterval 1 -MaxSamples 1).CounterSamples
$engineSamples = $samples | Where-Object {{ $_.Path -match 'GPU Engine\\(' }}
$memorySample = $samples | Where-Object {{ $_.Path -match 'GPU Adapter Memory\\(.*\\)\\\\Dedicated Usage$' }} | Select-Object -First 1
$engines = $engineSamples | Group-Object {{ $_.InstanceName -replace '^pid_\\d+_', '' }} | ForEach-Object {{
    [PSCustomObject]@{{ name = $_.Name; load = ($_.Group | Measure-Object CookedValue -Sum).Sum }}
}}
$peak = $engines | Sort-Object load -Descending | Select-Object -First 1
if ($null -eq $peak) {{ throw 'Windows returned no GPU Engine utilization counters for the AMD adapter.' }}
if ($null -eq $memorySample) {{ throw 'Windows returned no dedicated-memory counter for the AMD adapter.' }}
[PSCustomObject]@{{ load = [math]::Min(100, [math]::Max(0, [math]::Round($peak.load))); engine = ($peak.name -replace '^.*_engtype_', ''); vram_used = [math]::Round($memorySample.CookedValue) }} |
    ConvertTo-Json -Compress
"""
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        raise FileNotFoundError("Windows PowerShell is required to read GPU Engine performance counters.")

    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    data = json.loads(result.stdout)
    return int(data["load"]), str(data["engine"]), int(data["vram_used"])


def _refresh_gpu_load() -> None:
    global _GPU_LOAD_CACHE

    while True:
        try:
            adapter, luid, vram_total_bytes = _get_amd_gpu()
            load, engine, vram_used_bytes = _query_gpu_engine_load(luid)
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            KeyError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            TypeError,
            ValueError,
        ) as error:
            logger.exception("Unable to read AMD GPU telemetry.")
            snapshot: dict[str, int | float | str | None] = {
                "gpu_load": None,
                "gpu_adapter": None,
                "gpu_engine": None,
                "vram_used": None,
                "vram_total": None,
                "gpu_status": "unavailable",
                "gpu_error": str(error),
            }
        else:
            snapshot = {
                "gpu_load": load,
                "gpu_adapter": adapter,
                "gpu_engine": engine,
                "vram_used": round(vram_used_bytes / 1024**3, 1),
                "vram_total": round(vram_total_bytes / 1024**3, 1),
                "gpu_status": "ok",
                "gpu_error": None,
            }

        with _GPU_LOAD_LOCK:
            _GPU_LOAD_CACHE = snapshot

        sleep(_GPU_LOAD_REFRESH_SECONDS)


def get_gpu_load() -> dict[str, int | float | str | None]:
    global _GPU_LOAD_WORKER

    if os.name != "nt":
        return {
                "gpu_load": None,
            "gpu_adapter": None,
            "gpu_engine": None,
            "vram_used": None,
            "vram_total": None,
            "gpu_status": "unavailable",
            "gpu_error": "Windows GPU Engine counters are only available on Windows.",
        }

    with _GPU_LOAD_LOCK:
        if _GPU_LOAD_WORKER is None or not _GPU_LOAD_WORKER.is_alive():
            _GPU_LOAD_WORKER = Thread(
                target=_refresh_gpu_load,
                name="windows-gpu-telemetry",
                daemon=True,
            )
            _GPU_LOAD_WORKER.start()
        return _GPU_LOAD_CACHE.copy()
