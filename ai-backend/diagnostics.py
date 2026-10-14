"""Read-only diagnostics observations for local service health and resources."""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from threading import Lock, RLock
from time import monotonic
from typing import Callable, Generator, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import psutil

from bot_manager import get_bot_status
from config import settings

logger = logging.getLogger(__name__)

MAX_OBSERVATIONS = 200
MAX_INCIDENTS = 500
MAX_AUDIT_EVENTS = 1000
MAX_PROBE_RESPONSE_BYTES = 64_000
PROBE_TIMEOUT_SECONDS = 2.0

HealthStatus = Literal["healthy", "degraded", "unknown"]
IncidentStatus = Literal["open", "resolved"]


class DiagnosticsStoreError(RuntimeError):
    """Persistent diagnostics history could not be read or written safely."""


@dataclass(frozen=True)
class HealthCheckResult:
    name: str
    status: HealthStatus
    detail: str
    duration_ms: int


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_percent: float
    ram_percent: float
    ram_used_bytes: int
    ram_total_bytes: int
    log_disk_free_percent: float
    log_disk_free_bytes: int
    backend_rss_bytes: int


@dataclass(frozen=True)
class DiagnosticIncident:
    id: str
    check_name: str
    severity: Literal["warning"]
    status: IncidentStatus
    detail: str
    first_seen: str
    last_seen: str
    occurrence_count: int
    last_observation_id: str


@dataclass(frozen=True)
class AuditEvent:
    id: str
    timestamp: str
    event: str
    observation_id: str
    detail: str


@dataclass(frozen=True)
class DiagnosticObservation:
    id: str
    observed_at: str
    status: HealthStatus
    checks: tuple[HealthCheckResult, ...]
    resources: ResourceSnapshot


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_resources() -> ResourceSnapshot:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(settings.log_directory))
    process = psutil.Process()
    return ResourceSnapshot(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        ram_percent=memory.percent,
        ram_used_bytes=memory.used,
        ram_total_bytes=memory.total,
        log_disk_free_percent=100.0 - disk.percent,
        log_disk_free_bytes=disk.free,
        backend_rss_bytes=process.memory_info().rss,
    )


def _http_get(url: str, *, accept: str = "application/json") -> tuple[int, bytes]:
    request = Request(url, headers={"Accept": accept}, method="GET")
    try:
        with urlopen(request, timeout=PROBE_TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_PROBE_RESPONSE_BYTES + 1)
            status = response.status
    except HTTPError as error:
        return error.code, b""
    except (URLError, TimeoutError, OSError, ValueError):
        return 0, b""

    if len(payload) > MAX_PROBE_RESPONSE_BYTES:
        return 0, b""
    return status, payload


def _check_llama_server() -> tuple[bool, str]:
    status, _ = _http_get(f"{settings.llama_cpp_base_url}/health")
    if status == 200:
        return True, "llama.cpp health endpoint returned HTTP 200."
    return False, "llama.cpp health endpoint did not report ready."


def _check_searxng() -> tuple[bool, str]:
    query = urlencode({"q": "ai-server-health-check", "format": "json"})
    status, payload = _http_get(
        f"{settings.searxng_base_url}/search?{query}",
        accept="application/json",
    )
    if status != 200:
        return False, "SearXNG search endpoint did not return HTTP 200."
    try:
        response = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, "SearXNG search endpoint returned invalid JSON."
    if not isinstance(response, dict) or not isinstance(response.get("results"), list):
        return False, "SearXNG response did not include a results list."
    return True, "SearXNG returned a valid JSON search response."


def _check_discord_bot() -> tuple[bool, str]:
    if get_bot_status()["online"]:
        return True, "Discord bot heartbeat is active."
    return False, "Discord bot is offline or its heartbeat is stale."


class DiagnosticsStore:
    """SQLite persistence for bounded, observe-only diagnostics history."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if os.name != "nt":
                self.path.parent.chmod(0o700)
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS diagnostic_observations (
                        id TEXT PRIMARY KEY,
                        observed_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS diagnostic_observations_time
                        ON diagnostic_observations(observed_at DESC);
                    CREATE TABLE IF NOT EXISTS diagnostic_incidents (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
                        last_seen TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS diagnostic_incidents_status_time
                        ON diagnostic_incidents(status, last_seen DESC);
                    CREATE TABLE IF NOT EXISTS diagnostic_audit_events (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS diagnostic_audit_events_time
                        ON diagnostic_audit_events(timestamp DESC);
                    """
                )
            if os.name != "nt":
                self.path.chmod(0o600)
        except (OSError, sqlite3.Error) as error:
            raise DiagnosticsStoreError(
                "Could not initialize persistent diagnostics history."
            ) from error

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load_state(
        self,
    ) -> tuple[
        list[DiagnosticObservation],
        list[DiagnosticIncident],
        list[AuditEvent],
    ]:
        try:
            with self._connect() as connection:
                observations = connection.execute(
                    """SELECT payload_json FROM diagnostic_observations
                       ORDER BY rowid"""
                ).fetchall()
                incidents = connection.execute(
                    """SELECT payload_json FROM diagnostic_incidents
                       ORDER BY last_seen, id"""
                ).fetchall()
                audit_events = connection.execute(
                    """SELECT payload_json FROM diagnostic_audit_events
                       ORDER BY rowid"""
                ).fetchall()
            return (
                [self._observation_from_json(row["payload_json"]) for row in observations],
                [DiagnosticIncident(**json.loads(row["payload_json"])) for row in incidents],
                [AuditEvent(**json.loads(row["payload_json"])) for row in audit_events],
            )
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as error:
            raise DiagnosticsStoreError(
                "Could not load persistent diagnostics history."
            ) from error

    @staticmethod
    def _observation_from_json(payload: str) -> DiagnosticObservation:
        data = json.loads(payload)
        return DiagnosticObservation(
            id=data["id"],
            observed_at=data["observed_at"],
            status=data["status"],
            checks=tuple(HealthCheckResult(**check) for check in data["checks"]),
            resources=ResourceSnapshot(**data["resources"]),
        )

    def save_state(
        self,
        observation: DiagnosticObservation | None,
        incidents: list[DiagnosticIncident],
        audit_events: list[AuditEvent],
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if observation is not None:
                    connection.execute(
                        """INSERT OR IGNORE INTO diagnostic_observations
                           (id, observed_at, payload_json) VALUES (?, ?, ?)""",
                        (
                            observation.id,
                            observation.observed_at,
                            json.dumps(asdict(observation), separators=(",", ":")),
                        ),
                    )
                for incident in incidents:
                    connection.execute(
                        """INSERT INTO diagnostic_incidents
                           (id, status, last_seen, payload_json) VALUES (?, ?, ?, ?)
                           ON CONFLICT(id) DO UPDATE SET
                             status=excluded.status,
                             last_seen=excluded.last_seen,
                             payload_json=excluded.payload_json""",
                        (
                            incident.id,
                            incident.status,
                            incident.last_seen,
                            json.dumps(asdict(incident), separators=(",", ":")),
                        ),
                    )
                connection.executemany(
                    """INSERT OR IGNORE INTO diagnostic_audit_events
                       (id, timestamp, payload_json) VALUES (?, ?, ?)""",
                    [
                        (
                            event.id,
                            event.timestamp,
                            json.dumps(asdict(event), separators=(",", ":")),
                        )
                        for event in audit_events
                    ],
                )
                connection.execute(
                    """DELETE FROM diagnostic_observations
                       WHERE id NOT IN (
                           SELECT id FROM diagnostic_observations
                           ORDER BY rowid DESC LIMIT ?
                       )""",
                    (MAX_OBSERVATIONS,),
                )
                connection.execute(
                    """DELETE FROM diagnostic_incidents
                       WHERE status = 'resolved' AND id NOT IN (
                           SELECT id FROM diagnostic_incidents
                           WHERE status = 'resolved'
                           ORDER BY last_seen DESC, id DESC LIMIT ?
                       )""",
                    (MAX_INCIDENTS,),
                )
                connection.execute(
                    """DELETE FROM diagnostic_audit_events
                       WHERE id NOT IN (
                           SELECT id FROM diagnostic_audit_events
                           ORDER BY rowid DESC LIMIT ?
                       )""",
                    (MAX_AUDIT_EVENTS,),
                )
                connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise DiagnosticsStoreError(
                "Could not persist diagnostics history."
            ) from error


class DiagnosticsMonitor:
    """Collect observations and keep bounded, persistent incident history."""

    def __init__(
        self,
        checks: tuple[tuple[str, Callable[[], tuple[bool, str]]], ...] | None = None,
        resource_sampler: Callable[[], ResourceSnapshot] = _sample_resources,
        store: DiagnosticsStore | None = None,
    ) -> None:
        self._checks = checks if checks is not None else (
            ("backend.process", lambda: (True, "Backend process is serving this observation.")),
            ("llama_server.health", _check_llama_server),
            ("searxng.search", _check_searxng),
            ("discord_bot.heartbeat", _check_discord_bot),
        )
        self._resource_sampler = resource_sampler
        self._store = store
        self._collection_lock = Lock()
        self._lock = RLock()
        self._observations: deque[DiagnosticObservation] = deque(maxlen=MAX_OBSERVATIONS)
        self._incidents: deque[DiagnosticIncident] = deque(maxlen=MAX_INCIDENTS)
        self._audit_events: deque[AuditEvent] = deque(maxlen=MAX_AUDIT_EVENTS)
        self._active_incidents: dict[str, DiagnosticIncident] = {}
        if self._store is not None:
            observations, incidents, audit_events = self._store.load_state()
            self._observations.extend(observations)
            self._incidents.extend(incidents)
            self._audit_events.extend(audit_events)
            self._active_incidents = {
                incident.check_name: incident
                for incident in incidents
                if incident.status == "open"
            }

    def run_observation(self) -> DiagnosticObservation:
        with self._collection_lock:
            return self._collect_observation()

    def _collect_observation(self) -> DiagnosticObservation:
        observation_id = f"obs_{uuid4().hex}"
        started_at = _timestamp()
        with self._lock:
            self._record_audit(
                "observation.started",
                observation_id,
                "Read-only checks and sampling started.",
            )

        results: list[HealthCheckResult] = []
        try:
            for name, check in self._checks:
                started = monotonic()
                healthy, detail = check()
                elapsed_ms = max(0, round((monotonic() - started) * 1000))
                results.append(
                    HealthCheckResult(
                        name=name,
                        status="healthy" if healthy else "degraded",
                        detail=detail,
                        duration_ms=elapsed_ms,
                    )
                )
            resources = self._resource_sampler()
        except Exception as error:
            with self._lock:
                self._record_audit(
                    "observation.failed",
                    observation_id,
                    f"Observation failed with {type(error).__name__}.",
                )
                self._persist_state(None)
            raise
        observation = DiagnosticObservation(
            id=observation_id,
            observed_at=started_at,
            status=(
                "unknown"
                if not results
                else "healthy"
                if all(result.status == "healthy" for result in results)
                else "degraded"
            ),
            checks=tuple(results),
            resources=resources,
        )
        with self._lock:
            previous_observations = list(self._observations)
            previous_incidents = list(self._incidents)
            previous_audit_events = list(self._audit_events)
            previous_active_incidents = self._active_incidents.copy()
            self._observations.append(observation)
            self._update_incidents(observation)
            self._record_audit(
                "observation.completed",
                observation_id,
                f"Observation completed with status {observation.status}.",
            )
            try:
                self._persist_state(observation)
            except DiagnosticsStoreError:
                self._observations.clear()
                self._observations.extend(previous_observations)
                self._incidents.clear()
                self._incidents.extend(previous_incidents)
                self._audit_events.clear()
                self._audit_events.extend(previous_audit_events)
                self._active_incidents = previous_active_incidents
                self._record_audit(
                    "observation.failed",
                    observation_id,
                    "Completed observation could not be persisted.",
                )
                logger.exception("Could not save completed diagnostics history.")
                raise
        logger.info(
            "Read-only diagnostics observation completed: %s (%s).",
            observation.id,
            observation.status,
        )
        return observation

    def get_observations(self) -> list[DiagnosticObservation]:
        with self._lock:
            return list(self._observations)

    def get_incidents(self) -> list[DiagnosticIncident]:
        with self._lock:
            return list(self._incidents)

    def get_audit_events(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._audit_events)

    def _update_incidents(self, observation: DiagnosticObservation) -> None:
        checked_at = observation.observed_at
        results_by_name = {result.name: result for result in observation.checks}
        for name, result in results_by_name.items():
            active = self._active_incidents.get(name)
            if result.status == "degraded":
                if active is None:
                    incident = DiagnosticIncident(
                        id=f"inc_{uuid4().hex}",
                        check_name=name,
                        severity="warning",
                        status="open",
                        detail=result.detail,
                        first_seen=checked_at,
                        last_seen=checked_at,
                        occurrence_count=1,
                        last_observation_id=observation.id,
                    )
                    self._record_audit(
                        "incident.opened", observation.id, f"Opened warning for {name}."
                    )
                else:
                    incident = DiagnosticIncident(
                        id=active.id,
                        check_name=name,
                        severity=active.severity,
                        status="open",
                        detail=result.detail,
                        first_seen=active.first_seen,
                        last_seen=checked_at,
                        occurrence_count=active.occurrence_count + 1,
                        last_observation_id=observation.id,
                    )
                    if active in self._incidents:
                        self._incidents.remove(active)
                    self._record_audit(
                        "incident.updated",
                        observation.id,
                        f"Updated warning for {name}; observed {incident.occurrence_count} times.",
                    )
                self._active_incidents[name] = incident
                self._incidents.append(incident)
            elif active is not None:
                resolved = DiagnosticIncident(
                    id=active.id,
                    check_name=name,
                    severity=active.severity,
                    status="resolved",
                    detail=active.detail,
                    first_seen=active.first_seen,
                    last_seen=checked_at,
                    occurrence_count=active.occurrence_count,
                    last_observation_id=observation.id,
                )
                if active in self._incidents:
                    self._incidents.remove(active)
                self._incidents.append(resolved)
                del self._active_incidents[name]
                self._record_audit(
                    "incident.resolved", observation.id, f"Resolved warning for {name}."
                )

    def _record_audit(self, event: str, observation_id: str, detail: str) -> None:
        self._audit_events.append(
            AuditEvent(
                id=f"audit_{uuid4().hex}",
                timestamp=_timestamp(),
                event=event,
                observation_id=observation_id,
                detail=detail,
            )
        )

    def _persist_state(self, observation: DiagnosticObservation | None) -> None:
        if self._store is not None:
            self._store.save_state(
                observation,
                list(self._incidents),
                list(self._audit_events),
            )


def observation_to_dict(observation: DiagnosticObservation) -> dict[str, object]:
    """Serialize a diagnostic observation for the diagnostics API."""
    return asdict(observation)
