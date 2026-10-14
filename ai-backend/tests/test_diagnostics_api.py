import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import PropertyMock, patch

os.environ.setdefault(
    "AI_SERVER_LOG_DIR", tempfile.mkdtemp(prefix="ai-server-test-logs-")
)

from diagnostics import DiagnosticsMonitor, DiagnosticsStoreError, ResourceSnapshot
from auth_test_helpers import authenticated_client


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
        self.client, self.auth_store = authenticated_client(self, main)

    def test_system_status_reports_active_diagnostics_mode(self):
        with (
            patch.object(self.main, "get_system_stats", return_value={"cpu": 12.5}),
            patch.object(
                type(self.main.diagnostics_monitor),
                "is_running",
                new_callable=PropertyMock,
                return_value=True,
            ),
        ):
            response = self.client.get("/api/system")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["activity_mode"], "diagnostics")

    def test_system_status_reports_no_activity_mode_when_idle(self):
        with (
            patch.object(self.main, "get_system_stats", return_value={"cpu": 12.5}),
            patch.object(
                type(self.main.diagnostics_monitor),
                "is_running",
                new_callable=PropertyMock,
                return_value=False,
            ),
        ):
            response = self.client.get("/api/system")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["activity_mode"])

    def test_status_and_incidents_are_available_only_from_explicit_observations(self):
        status = self.client.get("/api/diagnostics/status")
        observations = self.client.get("/api/diagnostics/observations")

        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "not_run")
        self.assertEqual(status.json()["mode"], "observe_only")
        self.assertEqual(status.json()["storage"], "sqlite")
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

    def test_observation_reports_persistence_failure(self):
        with patch.object(
            self.main.diagnostics_monitor,
            "run_observation",
            side_effect=DiagnosticsStoreError("database unavailable"),
        ):
            response = self.client.post("/api/diagnostics/observe")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Persistent diagnostics history is unavailable.",
        )

    def test_explicit_chat_request_runs_read_only_diagnostics_and_shares_evidence(self):
        llm_result = {
            "reply": "The backend is healthy, but llama.cpp is degraded.",
            "latency_ms": 12,
            "tokens": 9,
        }
        with (
            patch.object(self.main, "run_llm", return_value=llm_result) as run_llm,
            patch.object(
                self.main.diagnostics_monitor,
                "run_observation",
                wraps=self.main.diagnostics_monitor.run_observation,
            ) as run_observation,
        ):
            response = self.client.post(
                "/api/chat", json={"message": "Could you run a diagnostic test?"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), llm_result)
        run_observation.assert_called_once_with()
        system_prompt = run_llm.call_args.args[1]
        self.assertIn("read-only diagnostics observation", system_prompt)
        self.assertIn("llama_server.health", system_prompt)
        self.assertIn("llama.cpp is not ready.", system_prompt)

    def test_interface_console_can_run_explicit_read_only_diagnostics(self):
        llm_result = {
            "reply": "The backend is healthy; llama.cpp is degraded.",
            "latency_ms": 12,
            "tokens": 9,
        }
        with (
            patch.object(self.main, "run_llm", return_value=llm_result) as run_llm,
            patch.object(
                self.main.diagnostics_monitor,
                "run_observation",
                wraps=self.main.diagnostics_monitor.run_observation,
            ) as run_observation,
        ):
            response = self.client.post(
                "/api/interface/chat", json={"message": "Run diagnostics."}
            )

        self.assertEqual(response.status_code, 200, response.text)
        run_observation.assert_called_once_with()
        system_prompt = run_llm.call_args.args[1]
        self.assertIn("read-only diagnostics observation", system_prompt)
        self.assertIn("llama_server.health", system_prompt)

    def test_diagnostics_questions_do_not_trigger_an_observation(self):
        llm_result = {"reply": "Use the Diagnostics panel.", "latency_ms": 5, "tokens": 6}
        with (
            patch.object(self.main, "run_llm", return_value=llm_result),
            patch.object(
                self.main.diagnostics_monitor,
                "run_observation",
                wraps=self.main.diagnostics_monitor.run_observation,
            ) as run_observation,
        ):
            response = self.client.post(
                "/api/chat", json={"message": "How do I run diagnostics?"}
            )

        self.assertEqual(response.status_code, 200)
        run_observation.assert_not_called()

    def test_discord_service_chat_cannot_trigger_diagnostics(self):
        from fastapi.testclient import TestClient

        service_token = "test-discord-service-token-" + "x" * 32
        settings_patch = patch.object(
            self.main,
            "settings",
            replace(self.main.settings, bot_api_token=service_token),
        )
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        service_client = TestClient(self.main.app)
        with (
            patch.object(
                self.main,
                "run_llm",
                return_value={"reply": "No observation run.", "latency_ms": 1, "tokens": 2},
            ),
            patch.object(
                self.main.diagnostics_monitor,
                "run_observation",
                wraps=self.main.diagnostics_monitor.run_observation,
            ) as run_observation,
        ):
            response = service_client.post(
                "/api/chat",
                json={"message": "Run a diagnostic test."},
                headers={"Authorization": f"Bearer {service_token}"},
            )

        self.assertEqual(response.status_code, 200)
        run_observation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
