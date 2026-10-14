import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "AI_SERVER_LOG_DIR", tempfile.mkdtemp(prefix="ai-server-test-logs-")
)

from diagnostics import DiagnosticsMonitor, ResourceSnapshot
from fastapi.testclient import TestClient


def resource_sample():
    return ResourceSnapshot(
        cpu_percent=12.5,
        ram_percent=40.0,
        ram_used_bytes=400,
        ram_total_bytes=1000,
        log_disk_free_percent=75.0,
        log_disk_free_bytes=750,
        backend_rss_bytes=100,
    )


class DiagnosticsApiTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.settings_patch = patch.object(
            main,
            "settings",
            replace(main.settings, log_directory=Path(self.temporary_directory.name)),
        )
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.monitor_patch = patch.object(
            main,
            "diagnostics_monitor",
            DiagnosticsMonitor(
                checks=(
                    ("backend.process", lambda: (True, "Backend process is running.")),
                    ("llama_server.health", lambda: (False, "llama.cpp is not ready.")),
                ),
                resource_sampler=resource_sample,
            ),
        )
        self.monitor_patch.start()
        self.addCleanup(self.monitor_patch.stop)
        self.client = TestClient(main.app)

    def test_status_and_incidents_are_available_only_from_explicit_observations(self):
        status = self.client.get("/api/diagnostics/status")
        observations = self.client.get("/api/diagnostics/observations")

        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "not_run")
        self.assertEqual(status.json()["mode"], "observe_only")
        self.assertIsNone(status.json()["latest_observation"])
        self.assertEqual(observations.json(), {"observations": [], "count": 0})

        run = self.client.post("/api/diagnostics/observe")

        self.assertEqual(run.status_code, 200)
        self.assertEqual(run.json()["status"], "degraded")
        self.assertEqual(len(run.json()["checks"]), 2)
        self.assertEqual(run.json()["resources"]["cpu_percent"], 12.5)

        status = self.client.get("/api/diagnostics/status").json()
        incidents = self.client.get("/api/diagnostics/incidents?status=open").json()
        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["open_incidents"], 1)
        self.assertEqual(incidents["count"], 1)
        self.assertEqual(incidents["incidents"][0]["check_name"], "llama_server.health")

    def test_history_filters_and_limits_are_validated(self):
        self.client.post("/api/diagnostics/observe")

        observations = self.client.get("/api/diagnostics/observations?limit=1")
        resolved = self.client.get("/api/diagnostics/incidents?status=resolved")
        invalid_limit = self.client.get("/api/diagnostics/observations?limit=101")
        invalid_status = self.client.get("/api/diagnostics/incidents?status=other")

        self.assertEqual(observations.status_code, 200)
        self.assertEqual(observations.json()["count"], 1)
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["count"], 0)
        self.assertEqual(invalid_limit.status_code, 422)
        self.assertEqual(invalid_status.status_code, 422)


if __name__ == "__main__":
    unittest.main()
