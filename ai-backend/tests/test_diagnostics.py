import unittest

from diagnostics import DiagnosticsMonitor, ResourceSnapshot


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

    def test_no_checks_produces_an_unknown_observation(self):
        monitor = DiagnosticsMonitor(checks=(), resource_sampler=resource_sample)

        observation = monitor.run_observation()

        self.assertEqual(observation.checks, ())
        self.assertEqual(observation.status, "unknown")


if __name__ == "__main__":
    unittest.main()
