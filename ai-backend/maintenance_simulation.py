"""Deterministic in-memory maintenance and remediation simulations.

This module intentionally has no operating-system, Proxmox, service-manager,
or application-runtime integrations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal


MaintenanceState = Literal[
    "scheduled",
    "preflight",
    "entering",
    "draining",
    "maintenance",
    "restoring",
    "complete",
    "skipped",
    "needs_attention",
]
SimulationStatus = Literal[
    "blocked",
    "verified",
    "rolled_back",
    "needs_attention",
]


class DeterministicClock:
    """A fixed-start clock that advances only when a simulation records an event."""

    def __init__(self, start: datetime | None = None) -> None:
        self._current = start or datetime(2000, 1, 1, tzinfo=timezone.utc)
        if self._current.tzinfo is None:
            raise ValueError("Simulation clock start must be timezone-aware.")

    def tick(self) -> str:
        self._current += timedelta(seconds=1)
        return self._current.isoformat()


@dataclass(frozen=True)
class SimulationEvent:
    sequence: int
    timestamp: str
    phase: str
    status: str
    detail: str


@dataclass(frozen=True)
class MaintenanceScenario:
    preflight_passes: bool = True
    drain_completes: bool = True
    diagnostic_context_available: bool = True
    restoration_healthy: bool = True


@dataclass(frozen=True)
class MaintenanceSimulation:
    state: MaintenanceState
    events: tuple[SimulationEvent, ...]
    live_actions_performed: Literal[False] = False

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "events": [asdict(event) for event in self.events],
            "live_actions_performed": False,
        }


def simulate_maintenance(
    scenario: MaintenanceScenario,
    *,
    clock: DeterministicClock | None = None,
) -> MaintenanceSimulation:
    """Simulate maintenance gates without touching live workloads or services."""
    simulation_clock = clock or DeterministicClock()
    events: list[SimulationEvent] = []

    def record(phase: str, status: str, detail: str) -> None:
        events.append(
            SimulationEvent(
                sequence=len(events) + 1,
                timestamp=simulation_clock.tick(),
                phase=phase,
                status=status,
                detail=detail,
            )
        )

    record("scheduled", "simulated", "A maintenance window was selected.")
    record("preflight", "passed" if scenario.preflight_passes else "failed",
           "Preflight checks were evaluated in memory.")
    if not scenario.preflight_passes:
        record("skipped", "safe_stop", "Maintenance did not enter the traffic gate.")
        return MaintenanceSimulation("skipped", tuple(events))

    record("entering", "simulated", "The simulated traffic gate was enabled.")
    record("draining", "passed" if scenario.drain_completes else "timed_out",
           "In-flight work was evaluated by the scenario fixture.")
    if not scenario.drain_completes:
        record(
            "skipped",
            "safe_stop",
            "The simulated window was skipped; no workloads were stopped.",
        )
        return MaintenanceSimulation("skipped", tuple(events))

    record("maintenance", "started", "The in-memory maintenance phase began.")
    if scenario.diagnostic_context_available:
        record(
            "maintenance",
            "completed",
            "The preinstalled diagnostic context passed its simulated check.",
        )
    else:
        record(
            "maintenance",
            "degraded",
            "Diagnostic context was unavailable; model-dependent work was skipped.",
        )

    record("restoring", "started", "Baseline workloads were restored in simulation.")
    if not scenario.restoration_healthy:
        record(
            "needs_attention",
            "failed",
            "Simulated restoration health checks failed; traffic remains gated.",
        )
        return MaintenanceSimulation("needs_attention", tuple(events))

    record("complete", "verified", "Simulated restoration checks passed.")
    return MaintenanceSimulation("complete", tuple(events))


@dataclass(frozen=True)
class RemediationProposal:
    action_id: str
    target: str
    risk_tier: int


@dataclass(frozen=True)
class RemediationScenario:
    verification_passes: bool = True
    rollback_passes: bool = True
    initial_state: str = "degraded"


@dataclass(frozen=True)
class RemediationSimulation:
    status: SimulationStatus
    action_id: str
    target: str
    before_state: str
    after_state: str
    events: tuple[SimulationEvent, ...]
    live_actions_performed: Literal[False] = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "action_id": self.action_id,
            "target": self.target,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "events": [asdict(event) for event in self.events],
            "live_actions_performed": False,
        }


_SIMULATED_ACTIONS = {
    "service.restart": (1, frozenset({"llama_server", "searxng", "discord_bot"})),
}


def simulate_remediation(
    proposal: RemediationProposal,
    scenario: RemediationScenario = RemediationScenario(),
    *,
    clock: DeterministicClock | None = None,
) -> RemediationSimulation:
    """Validate and simulate one registered low-risk action in memory only."""
    simulation_clock = clock or DeterministicClock()
    events: list[SimulationEvent] = []

    def record(status: str, detail: str) -> None:
        events.append(
            SimulationEvent(
                sequence=len(events) + 1,
                timestamp=simulation_clock.tick(),
                phase="remediation",
                status=status,
                detail=detail,
            )
        )

    registered = _SIMULATED_ACTIONS.get(proposal.action_id)
    if (
        registered is None
        or proposal.risk_tier != registered[0]
        or proposal.target not in registered[1]
    ):
        record(
            "blocked",
            "The action, risk tier, or target is outside the simulation registry.",
        )
        return RemediationSimulation(
            "blocked",
            proposal.action_id,
            proposal.target,
            scenario.initial_state,
            scenario.initial_state,
            tuple(events),
        )

    record("accepted", "The registered action passed in-memory policy checks.")
    record("simulated", "The target state changed only in the simulation fixture.")
    if scenario.verification_passes:
        record("verified", "The simulated post-action health check passed.")
        return RemediationSimulation(
            "verified",
            proposal.action_id,
            proposal.target,
            scenario.initial_state,
            "healthy",
            tuple(events),
        )

    record("verification_failed", "The simulated health check did not recover.")
    if scenario.rollback_passes:
        record("rolled_back", "The simulation restored the recorded before-state.")
        return RemediationSimulation(
            "rolled_back",
            proposal.action_id,
            proposal.target,
            scenario.initial_state,
            scenario.initial_state,
            tuple(events),
        )

    record("needs_attention", "Simulated rollback failed; manual review is required.")
    return RemediationSimulation(
        "needs_attention",
        proposal.action_id,
        proposal.target,
        scenario.initial_state,
        "unknown",
        tuple(events),
    )
