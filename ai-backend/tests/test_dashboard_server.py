import threading
import unittest
from http.server import ThreadingHTTPServer
from functools import partial
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from dashboard_server import (
    CONTENT_SECURITY_POLICY,
    SECURITY_HEADERS,
    DashboardRequestHandler,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DashboardServerTests(unittest.TestCase):
    def setUp(self):
        handler = partial(DashboardRequestHandler, directory=str(REPOSITORY_ROOT))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()

    def test_policy_has_no_inline_or_unsafe_script_sources(self):
        script_src = next(
            part for part in CONTENT_SECURITY_POLICY.split("; ")
            if part.startswith("script-src")
        )
        self.assertEqual(script_src, "script-src 'self'")
        self.assertIn("frame-ancestors 'none'", CONTENT_SECURITY_POLICY)
        self.assertIn("default-src 'none'", CONTENT_SECURITY_POLICY)
        self.assertNotIn("unsafe", CONTENT_SECURITY_POLICY)

    def test_served_assets_carry_security_headers(self):
        for path in ("/", "/index.html", "/css/style.css", "/js/app.js", "/js/theme-init.js"):
            with self.subTest(path=path), urlopen(f"{self.base_url}{path}") as response:
                self.assertEqual(response.status, 200)
                for name, value in SECURITY_HEADERS.items():
                    self.assertEqual(response.headers[name], value)

    def test_error_responses_also_carry_security_headers(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(f"{self.base_url}/.env")
        error.exception.close()
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(
            error.exception.headers["Content-Security-Policy"],
            CONTENT_SECURITY_POLICY,
        )

    def test_only_dashboard_assets_are_served(self):
        for path in (
            "/.env",
            "/ai-backend/main.py",
            "/docs/backend/api.md",
            "/js/",
            "/css",
            "/js/../.env",
            "/js/%2e%2e/.env",
            "/js/..%2f.env",
            "/%2e%2e/.env",
        ):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                urlopen(f"{self.base_url}{path}")
            error.exception.close()
            self.assertEqual(error.exception.code, 404)

    def test_index_page_has_no_inline_scripts_or_handlers(self):
        html = (REPOSITORY_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)")
        self.assertNotRegex(html, r"(?i)\son[a-z]+\s*=")
        self.assertNotRegex(html, r"(?i)\sstyle\s*=")


if __name__ == "__main__":
    unittest.main()
