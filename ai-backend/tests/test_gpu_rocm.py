import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gpu.gpu_rocm import get_gpu_load, get_gpu_stats, get_gpu_temp, get_vram_usage


class RocmTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="amdgpu-sysfs-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.drm_path = Path(self.temp_dir.name)
        self.device = self._add_device("card0", "0x1002", "AMD Radeon Test GPU")
        self.provider_path = patch("gpu.gpu_rocm._DRM_CLASS_PATH", self.drm_path)
        self.provider_path.start()
        self.addCleanup(self.provider_path.stop)

    def _add_device(
        self,
        card_name: str,
        vendor: str,
        product_name: str | None = None,
    ) -> Path:
        device = self.drm_path / card_name / "device"
        device.mkdir(parents=True)
        (device / "vendor").write_text(vendor, encoding="ascii")
        if product_name is not None:
            (device / "product_name").write_text(product_name, encoding="ascii")
        (device / "gpu_busy_percent").write_text("37\n", encoding="ascii")
        (device / "mem_info_vram_used").write_text(
            str(2 * 1024**3), encoding="ascii"
        )
        (device / "mem_info_vram_total").write_text(
            str(16 * 1024**3), encoding="ascii"
        )
        return device

    def test_reads_core_amdgpu_counters_in_dashboard_shape(self):
        self.assertEqual(
            get_gpu_load(),
            {
                "gpu_load": 37,
                "gpu_adapter": "AMD Radeon Test GPU",
                "gpu_engine": "overall",
                "gpu_status": "ok",
                "gpu_error": None,
                "vram_used": 2.0,
                "vram_total": 16.0,
            },
        )

    def test_reports_pci_identity_when_product_name_is_not_exposed(self):
        (self.device / "product_name").unlink()
        (self.device / "uevent").write_text(
            "PCI_ID=1002:73bf\n", encoding="ascii"
        )

        self.assertEqual(get_gpu_load()["gpu_adapter"], "AMD GPU (PCI 1002:73bf)")

    def test_missing_amd_gpu_is_unavailable_not_simulated(self):
        (self.device / "vendor").write_text("0x10de", encoding="ascii")

        stats = get_gpu_load()

        self.assertEqual(stats["gpu_status"], "unavailable")
        self.assertIsNone(stats["gpu_load"])
        self.assertIsNone(stats["vram_used"])
        if stats["gpu_error"] is None:
            self.fail("Unavailable telemetry should include an error.")
        self.assertIn("No AMD GPU", stats["gpu_error"])

    def test_missing_required_counter_is_reported_as_unavailable(self):
        (self.device / "gpu_busy_percent").unlink()

        stats = get_gpu_load()

        self.assertEqual(stats["gpu_status"], "unavailable")
        if stats["gpu_error"] is None:
            self.fail("Unavailable telemetry should include an error.")
        self.assertIn("counters are unavailable", stats["gpu_error"])

    def test_multiple_supported_amd_gpus_are_not_guessed(self):
        self._add_device("card1", "0x1002", "AMD Radeon Second GPU")

        stats = get_gpu_load()

        self.assertEqual(stats["gpu_status"], "unavailable")
        if stats["gpu_error"] is None:
            self.fail("Unavailable telemetry should include an error.")
        self.assertIn("ambiguous", stats["gpu_error"])

    def test_invalid_core_counter_is_unavailable(self):
        (self.device / "gpu_busy_percent").write_text("101", encoding="ascii")

        stats = get_gpu_load()

        self.assertEqual(stats["gpu_status"], "unavailable")
        if stats["gpu_error"] is None:
            self.fail("Unavailable telemetry should include an error.")
        self.assertIn("0-100", stats["gpu_error"])

    def test_reads_optional_hwmon_values_with_units(self):
        hwmon = self.device / "hwmon" / "hwmon0"
        hwmon.mkdir(parents=True)
        (hwmon / "temp1_input").write_text("54000", encoding="ascii")
        (hwmon / "temp1_label").write_text("edge", encoding="ascii")
        (hwmon / "power1_average").write_text(
            "120000000", encoding="ascii"
        )
        (hwmon / "fan1_input").write_text("1800", encoding="ascii")

        stats = get_gpu_stats()

        self.assertEqual(stats["gpu_temp"], 54.0)
        self.assertEqual(stats["power_draw"], 120.0)
        self.assertEqual(stats["fan_speed"], 1800)
        self.assertEqual(get_gpu_temp(), 54.0)

    def test_optional_hwmon_values_are_none_when_not_exposed(self):
        stats = get_gpu_stats()

        self.assertIsNone(stats["gpu_temp"])
        self.assertIsNone(stats["power_draw"])
        self.assertIsNone(stats["fan_speed"])

    def test_convenience_readers_return_values_and_unavailable_state(self):
        self.assertEqual(get_vram_usage(), (2.0, 16.0))
        self.assertEqual(get_gpu_temp(), None)

        (self.device / "mem_info_vram_used").unlink()

        self.assertEqual(get_vram_usage(), (None, None))
        self.assertIsNone(get_gpu_temp())


if __name__ == "__main__":
    unittest.main()
