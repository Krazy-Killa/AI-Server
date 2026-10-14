import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from psutil import AccessDenied

from diagnostics import (
    DiagnosticsMonitor,
    DiagnosticsStore,
    ResourceSnapshot,
    ThresholdPolicy,
    _check_backend_process,
    _check_memory_database,
    _check_searxng,
)


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


class DiagnosticsMonitorTests(unittest.TestCase):
    def test_default_threshold_policies_have_explicit_trigger_and_recovery_windows(self):
        self.assertEqual(
            [
                (
                    policy.name,
                    policy.trigger_value,
                    policy.clear_value,
                    policy.trigger_duration_seconds,
                    policy.recovery_duration_seconds,
                    policy.max_observation_gap_seconds,
                )
                for policy in DiagnosticsMonitor.DEFAULT_THRESHOLDS
            ],
            [
                ("resource.cpu.high", 90, 80, 120, 60, 300),
                ("resource.ram.high", 90, 85, 120, 60, 300),
                ("resource.log_disk_low", 10, 15, 60, 60, 300),
            ],
        )

    def test_observation_records_checks_resource_evidence_and_audit_events(self):
        checks = (
            ("backend.api", lambda: (True, "Backend is responding.")),
            ("llama_server.health", lambda: (False, "llama.cpp is not ready.")),
        )
        monitor = DiagnosticsMonitor(checks=checks, resource_sampler=resource_sample)

        observation = monitor.run_observation()

        self.assertEqual(observation.status, "degraded")
        self.assertEqual(
            [(check.name, check.status) for check in observation.checks],
            [("backend.api", "healthy"), ("llama_server.health", "degraded")],
        )
        self.assertGreaterEqual(observation.checks[0].duration_ms, 0)
        self.assertEqual(observation.resources, resource_sample())
        self.assertEqual(monitor.get_observations(), [observation])
        self.assertEqual(
            [event.event for event in monitor.get_audit_events()],
            ["observation.started", "incident.opened", "observation.completed"],
        )

    def test_repeated_failure_updates_one_incident_and_recovery_resolves_it(self):
        states = iter((False, False, True))
        monitor = DiagnosticsMonitor(
            checks=(("llama_server.health", lambda: (next(states), "Health probe result.")),),
            resource_sampler=resource_sample,
        )

        first = monitor.run_observation()
        first_incident = monitor.get_incidents()[-1]
        second = monitor.run_observation()
        updated_incident = monitor.get_incidents()[-1]
        recovered = monitor.run_observation()
        resolved_incident = monitor.get_incidents()[-1]

        self.assertEqual(first.status, "degraded")
        self.assertEqual(second.status, "degraded")
        self.assertEqual(recovered.status, "healthy")
        self.assertEqual(updated_incident.id, first_incident.id)
        self.assertEqual(updated_incident.occurrence_count, 2)
        self.assertEqual(resolved_incident.status, "resolved")
        self.assertEqual(resolved_incident.occurrence_count, 2)
        self.assertEqual(
            [event.event for event in monitor.get_audit_events()].count("incident.opened"),
            1,
        )
        self.assertEqual(
            [event.event for event in monitor.get_audit_events()].count("incident.updated"),
            1,
        )
        self.assertEqual(
            [event.event for event in monitor.get_audit_events()].count("incident.resolved"),
            1,
        )

    def test_probe_failure_is_not_converted_to_a_healthy_observation(self):
        def failed_probe():
            raise OSError("probe implementation failed")

        monitor = DiagnosticsMonitor(
            checks=(("llama_server.health", failed_probe),),
            resource_sampler=resource_sample,
        )

        with self.assertRaisesRegex(OSError, "probe implementation failed"):
            monitor.run_observation()

        self.assertEqual(monitor.get_observations(), [])
        self.assertEqual(
            [event.event for event in monitor.get_audit_events()],
            ["observation.started", "observation.failed"],
        )

    def test_resource_sampling_failure_is_audited_and_not_saved_as_healthy(self):
        def failed_sample():
            raise OSError("resource sampler failed")

        monitor = DiagnosticsMonitor(checks=(), resource_sampler=failed_sample)

        with self.assertRaisesRegex(OSError, "resource sampler failed"):
            monitor.run_observation()

        self.assertEqual(monitor.get_observations(), [])
        self.assertEqual(
            [event.event for event in monitor.get_audit_events()],
            ["observation.started", "observation.failed"],
        )

    def test_no_checks_produces_an_unknown_observation(self):
        monitor = DiagnosticsMonitor(checks=(), resource_sampler=resource_sample)

        observation = monitor.run_observation()

        self.assertEqual(observation.checks, ())
        self.assertEqual(observation.status, "unknown")

    def test_observations_and_incident_state_survive_monitor_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "diagnostics.sqlite3"
            checks = (("llama_server.health", lambda: (False, "Not ready.")),)
            first_monitor = DiagnosticsMonitor(
                checks=checks,
                resource_sampler=resource_sample,
                store=DiagnosticsStore(database_path),
            )

            first_monitor.run_observation()
            first_incident = first_monitor.get_incidents()[0]
            restarted_monitor = DiagnosticsMonitor(
                checks=(("llama_server.health", lambda: (True, "Ready.")),),
                resource_sampler=resource_sample,
                store=DiagnosticsStore(database_path),
            )

            self.assertEqual(len(restarted_monitor.get_observations()), 1)
            self.assertEqual(restarted_monitor.get_incidents()[0], first_incident)
            self.assertEqual(
                [event.event for event in restarted_monitor.get_audit_events()],
                [
                    "observation.started",
                    "incident.opened",
                    "observation.completed",
                ],
            )

            recovered = restarted_monitor.run_observation()

            self.assertEqual(recovered.status, "healthy")
            resolved = DiagnosticsMonitor(
                checks=checks,
                resource_sampler=resource_sample,
                store=DiagnosticsStore(database_path),
            )
            self.assertEqual(resolved.get_incidents()[0].status, "resolved")
            self.assertEqual(len(resolved.get_observations()), 2)
            self.assertIn(
                "incident.resolved",
                [event.event for event in resolved.get_audit_events()],
            )

    def test_threshold_requires_duration_and_recovery_hysteresis(self):
        now = [datetime(2026, 10, 14, tzinfo=timezone.utc)]
        resources = [replace(resource_sample(), cpu_percent=95.0)]
        policy = ThresholdPolicy(
            name="resource.cpu.high",
            resource="cpu_percent",
            unit="%",
            comparison="gte",
            trigger_value=90,
            clear_value=80,
            trigger_duration_seconds=120,
            recovery_duration_seconds=60,
        )
        monitor = DiagnosticsMonitor(
            checks=(),
            resource_sampler=lambda: resources[0],
            thresholds=(policy,),
            clock=lambda: now[0],
        )

        first = monitor.run_observation()
        self.assertEqual(first.status, "unknown")
        self.assertEqual(first.thresholds[0].status, "pending")

        now[0] += timedelta(seconds=120)
        triggered = monitor.run_observation()
        self.assertEqual(triggered.status, "degraded")
        self.assertEqual(triggered.thresholds[0].status, "triggered")
        self.assertEqual(monitor.get_incidents()[0].check_name, policy.name)

        resources[0] = replace(resources[0], cpu_percent=70.0)
        now[0] += timedelta(seconds=60)
        recovering = monitor.run_observation()
        self.assertEqual(recovering.thresholds[0].status, "recovering")
        self.assertEqual(monitor.get_incidents()[0].status, "open")

        now[0] += timedelta(seconds=301)
        after_recovery_gap = monitor.run_observation()
        self.assertEqual(after_recovery_gap.thresholds[0].status, "recovering")
        self.assertEqual(after_recovery_gap.thresholds[0].elapsed_seconds, 0)

        now[0] += timedelta(seconds=60)
        recovered = monitor.run_observation()
        self.assertEqual(recovered.thresholds[0].status, "normal")
        self.assertEqual(recovered.status, "unknown")
        self.assertEqual(monitor.get_incidents()[0].status, "resolved")

    def test_threshold_oscillation_and_observation_gap_reset_pending_duration(self):
        now = [datetime(2026, 10, 14, tzinfo=timezone.utc)]
        resources = [replace(resource_sample(), cpu_percent=95.0)]
        policy = ThresholdPolicy(
            name="resource.cpu.high",
            resource="cpu_percent",
            unit="%",
            comparison="gte",
            trigger_value=90,
            clear_value=80,
            trigger_duration_seconds=120,
            recovery_duration_seconds=60,
            max_observation_gap_seconds=300,
        )
        monitor = DiagnosticsMonitor(
            checks=(),
            resource_sampler=lambda: resources[0],
            thresholds=(policy,),
            clock=lambda: now[0],
        )

        self.assertEqual(monitor.run_observation().thresholds[0].status, "pending")
        now[0] += timedelta(seconds=60)
        resources[0] = replace(resources[0], cpu_percent=85.0)
        self.assertEqual(monitor.run_observation().thresholds[0].status, "normal")
        now[0] += timedelta(seconds=60)
        resources[0] = replace(resources[0], cpu_percent=95.0)
        restarted_pending = monitor.run_observation().thresholds[0]
        self.assertEqual(restarted_pending.status, "pending")
        self.assertEqual(restarted_pending.elapsed_seconds, 0)

        now[0] += timedelta(seconds=301)
        after_gap = monitor.run_observation().thresholds[0]
        self.assertEqual(after_gap.status, "pending")
        self.assertEqual(after_gap.elapsed_seconds, 0)
        self.assertIsNone(after_gap.active_since)

    def test_threshold_confirmation_state_survives_monitor_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "diagnostics.sqlite3"
            now = [datetime(2026, 10, 14, tzinfo=timezone.utc)]
            policy = ThresholdPolicy(
                name="resource.cpu.high",
                resource="cpu_percent",
                unit="%",
                comparison="gte",
                trigger_value=90,
                clear_value=80,
                trigger_duration_seconds=120,
                recovery_duration_seconds=60,
            )
            first_monitor = DiagnosticsMonitor(
                checks=(),
                resource_sampler=lambda: replace(resource_sample(), cpu_percent=95.0),
                store=DiagnosticsStore(database_path),
                thresholds=(policy,),
                clock=lambda: now[0],
            )
            first_monitor.run_observation()

            now[0] += timedelta(seconds=120)
            restarted_monitor = DiagnosticsMonitor(
                checks=(),
                resource_sampler=lambda: replace(resource_sample(), cpu_percent=95.0),
                store=DiagnosticsStore(database_path),
                thresholds=(policy,),
                clock=lambda: now[0],
            )
            observation = restarted_monitor.run_observation()

            self.assertEqual(observation.thresholds[0].status, "triggered")
            self.assertEqual(len(restarted_monitor.get_incidents()), 1)

    def test_report_generation_does_not_run_probes_or_sampling(self):
        calls = {"probe": 0, "sample": 0}

        def probe():
            calls["probe"] += 1
            return True, "Probe is healthy."

        def sample():
            calls["sample"] += 1
            return resource_sample()

        monitor = DiagnosticsMonitor(
            checks=(("backend.api", probe),),
            resource_sampler=sample,
        )
        observation = monitor.run_observation()
        counts_before_report = calls.copy()

        observations_before_report = monitor.get_observations()
        incidents_before_report = monitor.get_incidents()
        audit_before_report = monitor.get_audit_events()
        with patch.object(
            monitor,
            "_persist_state",
            wraps=monitor._persist_state,
        ) as persist_state:
            report = monitor.build_report(observation.id)
            persist_state.assert_not_called()

        self.assertEqual(calls, counts_before_report)
        self.assertEqual(monitor.get_observations(), observations_before_report)
        self.assertEqual(monitor.get_incidents(), incidents_before_report)
        self.assertEqual(monitor.get_audit_events(), audit_before_report)
        assert report is not None
        self.assertEqual(report["mode"], "observe_only")
        self.assertEqual(report["observation_id"], observation.id)
        self.assertIsNone(monitor.build_report("obs_missing"))

    def test_report_preserves_incident_state_at_historical_observation(self):
        states = iter(
            (
                (False, "Health probe failed."),
                (True, "Health probe recovered."),
            )
        )
        monitor = DiagnosticsMonitor(
            checks=(("llama_server.health", lambda: next(states)),),
            resource_sampler=resource_sample,
        )

        open_observation = monitor.run_observation()
        historical_report = monitor.build_report(open_observation.id)
        resolved_observation = monitor.run_observation()
        current_report = monitor.build_report(resolved_observation.id)

        assert historical_report is not None
        assert current_report is not None
        self.assertEqual(historical_report["status"], "degraded")
        self.assertEqual(current_report["status"], "healthy")
        historical_incidents = historical_report["incidents"]
        if not isinstance(historical_incidents, list):
            self.fail("Historical report incidents should be a list.")
        self.assertEqual(len(historical_incidents), 1)
        historical_incident = historical_incidents[0]
        if not isinstance(historical_incident, dict):
            self.fail("Historical report incidents should contain objects.")
        self.assertEqual(historical_incident["status"], "open")
        self.assertEqual(historical_incident["detail"], "Health probe failed.")
        self.assertEqual(historical_incident["occurrence_count"], 1)
        self.assertEqual(
            historical_incident["last_observation_id"], open_observation.id
        )
        self.assertEqual(current_report["incidents"], [])

    def test_read_only_sqlite_integrity_probe_does_not_modify_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "memory.sqlite3"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute("CREATE TABLE evidence (value TEXT)")
                connection.execute("INSERT INTO evidence VALUES ('preserve me')")
                connection.commit()
            finally:
                connection.close()
            before = hashlib.sha256(database_path.read_bytes()).digest()

            healthy, detail = _check_memory_database(database_path)

            self.assertTrue(healthy, detail)
            self.assertEqual(hashlib.sha256(database_path.read_bytes()).digest(), before)

    def test_integrity_probe_reports_corrupt_database_without_repairing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "corrupt.sqlite3"
            database_path.write_bytes(b"not a SQLite database")
            before = database_path.read_bytes()

            healthy, detail = _check_memory_database(database_path)

            self.assertFalse(healthy)
            self.assertIn("integrity check", detail)
            self.assertEqual(database_path.read_bytes(), before)

    def test_backend_process_and_search_response_failures_are_observations(self):
        with patch(
            "diagnostics.psutil.Process",
            side_effect=AccessDenied(pid=1),
        ):
            backend_healthy, backend_detail = _check_backend_process()
        self.assertFalse(backend_healthy)
        self.assertIn("could not be verified", backend_detail)

        with patch("diagnostics._http_get", return_value=(200, b"not-json")):
            search_healthy, search_detail = _check_searxng()
        self.assertFalse(search_healthy)
        self.assertIn("invalid JSON", search_detail)


if __name__ == "__main__":
    unittest.main()
