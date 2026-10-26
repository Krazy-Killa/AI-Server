"""Read AMD GPU telemetry exposed by the Linux amdgpu sysfs interface."""

from __future__ import annotations

import re
from pathlib import Path

from gpu.telemetry import GpuTelemetry

_DRM_CLASS_PATH = Path("/sys/class/drm")
_PCI_VENDOR_AMD = "0x1002"
_GIB = 1024**3
_CARD_NAME = re.compile(r"card\d+\Z")
_PCI_ID = re.compile(r"(?m)^PCI_ID=([0-9a-fA-F]{4}:[0-9a-fA-F]{4})$")


class GpuStats(GpuTelemetry):
    gpu_temp: float | None
    power_draw: float | None
    fan_speed: int | None


class GpuTelemetryError(RuntimeError):
    """Raised when reliable AMD GPU telemetry cannot be read."""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="ascii").strip()


def _read_counter(path: Path) -> int:
    value = int(_read_text(path))
    if value < 0:
        raise ValueError(f"GPU telemetry counter contains a negative value: {path.name}")
    return value


def _amd_devices(drm_class_path: Path) -> list[Path]:
    try:
        cards = sorted(
            card for card in drm_class_path.iterdir() if _CARD_NAME.fullmatch(card.name)
        )
    except OSError as error:
        raise GpuTelemetryError(f"Unable to inspect DRM devices: {error}") from error

    devices: list[Path] = []
    for card in cards:
        device = card / "device"
        try:
            vendor = _read_text(device / "vendor").lower()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise GpuTelemetryError(f"Unable to read {card.name} vendor ID: {error}") from error
        if vendor == _PCI_VENDOR_AMD:
            devices.append(device)

    if not devices:
        raise GpuTelemetryError("No AMD GPU was found in the Linux DRM devices.")

    usable_devices = [
        device
        for device in devices
        if all(
            (device / counter).is_file()
            for counter in (
                "gpu_busy_percent",
                "mem_info_vram_used",
                "mem_info_vram_total",
            )
        )
    ]
    if not usable_devices:
        raise GpuTelemetryError(
            "AMD GPU amdgpu utilization and VRAM counters are unavailable."
        )
    if len(usable_devices) > 1:
        raise GpuTelemetryError(
            "Multiple AMD GPUs expose telemetry; selecting an adapter is ambiguous."
        )
    return usable_devices


def _adapter_name(device: Path) -> str:
    try:
        product_name = _read_text(device / "product_name")
    except FileNotFoundError:
        product_name = ""
    except OSError as error:
        raise GpuTelemetryError(f"Unable to read AMD GPU product name: {error}") from error
    if product_name:
        return product_name

    try:
        uevent = _read_text(device / "uevent")
    except FileNotFoundError:
        uevent = ""
    except OSError as error:
        raise GpuTelemetryError(f"Unable to read AMD GPU PCI identity: {error}") from error
    pci_id = _PCI_ID.search(uevent)
    if pci_id:
        return f"AMD GPU (PCI {pci_id.group(1).lower()})"
    return "AMD GPU"


def _snapshot(device: Path) -> GpuTelemetry:
    load = _read_counter(device / "gpu_busy_percent")
    if load > 100:
        raise ValueError("GPU utilization counter is outside the 0-100 percent range.")

    vram_used_bytes = _read_counter(device / "mem_info_vram_used")
    vram_total_bytes = _read_counter(device / "mem_info_vram_total")
    if vram_total_bytes == 0 or vram_used_bytes > vram_total_bytes:
        raise ValueError("GPU VRAM counters contain an invalid used/total value.")

    return {
        "gpu_load": load,
        "gpu_adapter": _adapter_name(device),
        "gpu_engine": "overall",
        "gpu_status": "ok",
        "gpu_error": None,
        "vram_used": round(vram_used_bytes / _GIB, 1),
        "vram_total": round(vram_total_bytes / _GIB, 1),
    }


def _unavailable(error: Exception) -> GpuTelemetry:
    return {
        "gpu_load": None,
        "gpu_adapter": None,
        "gpu_engine": None,
        "gpu_status": "unavailable",
        "gpu_error": str(error),
        "vram_used": None,
        "vram_total": None,
    }


def _get_snapshot() -> tuple[Path | None, GpuTelemetry]:
    try:
        (device,) = _amd_devices(_DRM_CLASS_PATH)
        return device, _snapshot(device)
    except (GpuTelemetryError, OSError, ValueError) as error:
        return None, _unavailable(error)


def _read_optional_sensor(device: Path, pattern: str) -> int | None:
    try:
        candidates = sorted(device.glob(f"hwmon/hwmon*/{pattern}"))
    except OSError:
        return None
    values: list[int] = []
    for path in candidates:
        try:
            values.append(_read_counter(path))
        except (OSError, ValueError):
            continue
    return values[0] if len(values) == 1 else None


def _gpu_temperature(device: Path) -> float | None:
    try:
        candidates = sorted(device.glob("hwmon/hwmon*/temp*_input"))
    except OSError:
        return None

    labelled: list[Path] = []
    for path in candidates:
        label_path = path.with_name(path.name.removesuffix("_input") + "_label")
        try:
            label = _read_text(label_path).lower()
        except FileNotFoundError:
            continue
        except OSError:
            continue
        if label in {"edge", "gpu"}:
            labelled.append(path)

    selected = labelled if labelled else candidates if len(candidates) == 1 else []
    if len(selected) != 1:
        return None
    try:
        return round(_read_counter(selected[0]) / 1000, 1)
    except (OSError, ValueError):
        return None


def get_gpu_load() -> GpuTelemetry:
    """Return the dashboard GPU telemetry contract using Linux amdgpu counters."""
    return _get_snapshot()[1]


def get_vram_usage() -> tuple[float | None, float | None]:
    """Return used and total VRAM in GiB, or two ``None`` values if unavailable."""
    snapshot = get_gpu_load()
    if snapshot["gpu_status"] != "ok":
        return None, None
    return snapshot["vram_used"], snapshot["vram_total"]


def get_gpu_temp() -> float | None:
    """Return the GPU edge temperature in Celsius when exposed by hwmon."""
    device, snapshot = _get_snapshot()
    if device is None or snapshot["gpu_status"] != "ok":
        return None
    return _gpu_temperature(device)


def get_gpu_stats() -> GpuStats:
    """Return core GPU telemetry and optional hwmon sensors."""
    device, snapshot = _get_snapshot()
    stats: GpuStats = {
        **snapshot,
        "gpu_temp": None,
        "power_draw": None,
        "fan_speed": None,
    }
    if device is None or snapshot["gpu_status"] != "ok":
        return stats

    temperature = _gpu_temperature(device)
    power_microwatts = _read_optional_sensor(device, "power*_average")
    if power_microwatts is None:
        power_microwatts = _read_optional_sensor(device, "power*_input")
    fan_rpm = _read_optional_sensor(device, "fan*_input")
    stats["gpu_temp"] = temperature
    stats["power_draw"] = (
        round(power_microwatts / 1_000_000, 1)
        if power_microwatts is not None
        else None
    )
    stats["fan_speed"] = fan_rpm
    return stats
