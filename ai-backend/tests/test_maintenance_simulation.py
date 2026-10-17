import unittest

from maintenance_simulation import (
    MaintenanceScenario,
    RemediationProposal,
    RemediationScenario,
    simulate_maintenance,
    simulate_remediation,
)


class MaintenanceSimulationTests(unittest.TestCase):
    def test_successful_flow_is_deterministic_and_completes(self):
        first = simulate_maintenance(MaintenanceScenario())
        second = simulate_maintenance(MaintenanceScenario())

        self.assertEqual(first, second)
        self.assertEqual(first.state, "complete")
        self.assertFalse(first.live_actions_performed)
        self.assertEqual(
            [event.phase for event in first.events],
            [
                "scheduled",
                "preflight",
                "entering",
                "draining",
                "maintenance",
                "maintenance",
                "restoring",
                "complete",
            ],
        )

    def test_failed_preflight_skips_without_entering_maintenance(self):
        result = simulate_maintenance(
            MaintenanceScenario(preflight_passes=False)
        )

        self.assertEqual(result.state, "skipped")
        self.assertNotIn("entering", [event.phase for event in result.events])

    def test_drain_timeout_skips_without_stopping_workloads(self):
        result = simulate_maintenance(
            MaintenanceScenario(drain_completes=False)
        )

        self.assertEqual(result.state, "skipped")
        self.assertEqual(result.events[-1].status, "safe_stop")

    def test_missing_diagnostic_context_is_reported_but_restores_services(self):
        result = simulate_maintenance(
            MaintenanceScenario(diagnostic_context_available=False)
        )

        self.assertEqual(result.state, "complete")
        self.assertTrue(
            any(event.status == "degraded" for event in result.events)
        )

    def test_failed_restoration_requires_attention_and_does_not_claim_success(self):
        result = simulate_maintenance(
            MaintenanceScenario(restoration_healthy=False)
        )

        self.assertEqual(result.state, "needs_attention")
        self.assertNotEqual(result.events[-1].status, "verified")


class RemediationSimulationTests(unittest.TestCase):
    def test_registered_action_verifies_in_simulation_only(self):
        proposal = RemediationProposal("service.restart", "llama_server", 1)
        result = simulate_remediation(proposal)

        self.assertEqual(result.status, "verified")
        self.assertEqual(result.before_state, "degraded")
        self.assertEqual(result.after_state, "healthy")
        self.assertFalse(result.live_actions_performed)

    def test_unregistered_action_wrong_tier_and_unknown_target_are_blocked(self):
        proposals = (
            RemediationProposal("shell.execute", "llama_server", 1),
            RemediationProposal("service.restart", "llama_server", 2),
            RemediationProposal("service.restart", "proxmox_host", 1),
        )
        for proposal in proposals:
            with self.subTest(proposal=proposal):
                result = simulate_remediation(proposal)
                self.assertEqual(result.status, "blocked")
                self.assertEqual(result.before_state, result.after_state)

    def test_failed_verification_rolls_back_before_state(self):
        result = simulate_remediation(
            RemediationProposal("service.restart", "searxng", 1),
            RemediationScenario(verification_passes=False),
        )

        self.assertEqual(result.status, "rolled_back")
        self.assertEqual(result.after_state, result.before_state)

    def test_failed_verification_and_rollback_escalate(self):
        result = simulate_remediation(
            RemediationProposal("service.restart", "discord_bot", 1),
            RemediationScenario(
                verification_passes=False,
                rollback_passes=False,
            ),
        )

        self.assertEqual(result.status, "needs_attention")
        self.assertEqual(result.after_state, "unknown")


if __name__ == "__main__":
    unittest.main()
