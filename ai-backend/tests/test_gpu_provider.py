import unittest
from unittest.mock import patch

from gpu.provider import get_gpu_load


class GpuProviderTests(unittest.TestCase):
    def test_selects_windows_provider(self):
        with (
            patch("gpu.provider.platform.system", return_value="Windows"),
            patch(
                "gpu.windows_gpu.get_gpu_load",
                return_value={"gpu_status": "windows"},
            ) as windows_provider,
        ):
            self.assertEqual(get_gpu_load(), {"gpu_status": "windows"})
        windows_provider.assert_called_once_with()

    def test_selects_linux_amdgpu_provider(self):
        with (
            patch("gpu.provider.platform.system", return_value="Linux"),
            patch(
                "gpu.gpu_rocm.get_gpu_load",
                return_value={"gpu_status": "linux"},
            ) as linux_provider,
        ):
            self.assertEqual(get_gpu_load(), {"gpu_status": "linux"})
        linux_provider.assert_called_once_with()

    def test_unsupported_platform_is_explicitly_unavailable(self):
        with patch("gpu.provider.platform.system", return_value="FreeBSD"):
            stats = get_gpu_load()

        self.assertEqual(stats["gpu_status"], "unavailable")
        if stats["gpu_error"] is None:
            self.fail("Unavailable telemetry should include an error.")
        self.assertIn("FreeBSD", stats["gpu_error"])
        self.assertIsNone(stats["gpu_load"])


if __name__ == "__main__":
    unittest.main()
