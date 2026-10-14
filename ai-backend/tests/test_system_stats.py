import unittest
from types import SimpleNamespace
from unittest.mock import patch

from system_stats import get_system_stats


class SystemStatsTests(unittest.TestCase):
    @patch("system_stats.platform.node", return_value="AI-NODE-01")
    @patch("system_stats.psutil.virtual_memory", return_value=SimpleNamespace(percent=42.5))
    @patch("system_stats.psutil.cpu_percent", return_value=17.0)
    @patch(
        "system_stats.get_gpu_load",
        return_value={
            "gpu_load": 31,
            "gpu_adapter": "AMD Radeon RX 6800 XT",
            "gpu_engine": "3D",
            "gpu_status": "ok",
            "gpu_error": None,
            "vram_used": 2.0,
            "vram_total": 16.0,
        },
    )
    def test_includes_runtime_node_and_gpu_adapter(
        self, _gpu_load, _cpu_percent, _virtual_memory, _node
    ):
        stats = get_system_stats()

        self.assertEqual(stats["node_name"], "AI-NODE-01")
        self.assertEqual(stats["gpu_adapter"], "AMD Radeon RX 6800 XT")
