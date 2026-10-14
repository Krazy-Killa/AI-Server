import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "AI_SERVER_LOG_DIR", tempfile.mkdtemp(prefix="ai-server-test-logs-")
)

from fastapi.testclient import TestClient


class BackendLogsEndpointTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        log_directory = Path(self.temporary_directory.name)
        self.settings_patch = patch.object(
            main,
            "settings",
            replace(main.settings, log_directory=log_directory),
        )
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.client = TestClient(main.app)

    def test_returns_only_the_requested_most_recent_lines(self):
        log_file = self.main.settings.log_directory / "backend.log"
        log_file.write_text("first\nsecond\nthird\nfourth\n", encoding="utf-8")

        response = self.client.get("/api/backend/logs?limit=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"logs": ["third", "fourth"], "count": 2})

    def test_reports_missing_backend_log_file(self):
        response = self.client.get("/api/backend/logs")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Backend log file is not available.")

    def test_rejects_limits_outside_the_supported_range(self):
        for limit in ("0", "501"):
            with self.subTest(limit=limit):
                response = self.client.get(f"/api/backend/logs?limit={limit}")
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
