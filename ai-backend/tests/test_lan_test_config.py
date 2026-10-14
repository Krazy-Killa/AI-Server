import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lan_test_config import LanTestConfigError, load_lan_test_config
from lan_dashboard_server import DashboardHandler


class LanTestConfigTests(unittest.TestCase):
    def test_dashboard_server_exposes_only_public_ui_assets(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        try:
            with urlopen(f"{base_url}/") as response:
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.headers["Content-Type"])
                self.assertIn(b"AI Server", response.read())

            for path in ("/.env", "/ai-backend/main.py", "/docs/api.md", "/%2e%2e/.env"):
                with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                    urlopen(f"{base_url}{path}")
                error.exception.close()
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            worker.join()
            server.server_close()

    def test_loads_private_host_and_https_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            certificate = Path(directory) / "lan.pem"
            private_key = Path(directory) / "lan-key.pem"
            certificate.touch()
            private_key.touch()
            environment = {
                "AI_SERVER_LAN_HOST": "192.168.1.50",
                "AI_SERVER_LAN_TLS_CERT": str(certificate),
                "AI_SERVER_LAN_TLS_KEY": str(private_key),
                "AI_SERVER_CORS_ORIGINS": "https://192.168.1.50:8001",
                "AI_SERVER_AUTH_COOKIE_SECURE": "true",
            }
            with patch.dict(os.environ, environment, clear=False):
                config = load_lan_test_config()

        self.assertEqual(config.host, "192.168.1.50")
        self.assertEqual(config.dashboard_origin, "https://192.168.1.50:8001")
        self.assertEqual(config.certificate, certificate.resolve())
        self.assertEqual(config.private_key, private_key.resolve())

    def test_rejects_non_private_and_wildcard_bind_addresses(self):
        for host in ("127.0.0.1", "8.8.8.8", "0.0.0.0", "host.local"):
            with self.subTest(host=host), patch.dict(
                os.environ,
                {
                    "AI_SERVER_LAN_HOST": host,
                    "AI_SERVER_LAN_TLS_CERT": "certificate.pem",
                    "AI_SERVER_LAN_TLS_KEY": "key.pem",
                    "AI_SERVER_CORS_ORIGINS": f"https://{host}:8001",
                },
                clear=False,
            ):
                with self.assertRaisesRegex(LanTestConfigError, "private"):
                    load_lan_test_config()

    def test_requires_explicit_cors_origin_and_secure_cookie(self):
        with tempfile.TemporaryDirectory() as directory:
            certificate = Path(directory) / "lan.pem"
            private_key = Path(directory) / "lan-key.pem"
            certificate.touch()
            private_key.touch()
            base_environment = {
                "AI_SERVER_LAN_HOST": "192.168.1.50",
                "AI_SERVER_LAN_TLS_CERT": str(certificate),
                "AI_SERVER_LAN_TLS_KEY": str(private_key),
                "AI_SERVER_CORS_ORIGINS": "https://192.168.1.50:8001",
                "AI_SERVER_AUTH_COOKIE_SECURE": "true",
            }
            with patch.dict(os.environ, {**base_environment, "AI_SERVER_CORS_ORIGINS": ""}):
                with self.assertRaisesRegex(LanTestConfigError, "AI_SERVER_CORS_ORIGINS"):
                    load_lan_test_config()
            with patch.dict(
                os.environ,
                {**base_environment, "AI_SERVER_AUTH_COOKIE_SECURE": "false"},
            ):
                with self.assertRaisesRegex(LanTestConfigError, "must be true"):
                    load_lan_test_config()


if __name__ == "__main__":
    unittest.main()
