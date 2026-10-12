"""Track live Discord bot heartbeats and dashboard restart requests."""

from collections import deque
from threading import Lock
import time

HEARTBEAT_TIMEOUT_SECONDS = 20
MAX_LOG_LINES = 200

_lock = Lock()
_last_seen: float | None = None
_last_restart: float | None = None
_latency_ms: int | None = None
_commands: list[str] = []
_restart_requested = False
_restart_in_progress = False
_logs: deque[str] = deque(maxlen=MAX_LOG_LINES)


def add_bot_log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    with _lock:
        _logs.append(f"[{timestamp}] {message}")


def update_bot_heartbeat(
    latency_ms: int | None,
    commands: list[str],
) -> bool:
    """Record a live bot heartbeat and return whether it should restart."""
    global _last_seen, _last_restart, _latency_ms
    global _commands, _restart_requested, _restart_in_progress

    now = time.time()
    restart_completed = False
    with _lock:
        was_offline = (
            _last_seen is None
            or now - _last_seen > HEARTBEAT_TIMEOUT_SECONDS
        )
        _last_seen = now
        _latency_ms = latency_ms
        _commands = commands
        restart_requested = _restart_requested
        if restart_requested:
            _restart_requested = False
            _restart_in_progress = True
        elif _restart_in_progress:
            _restart_in_progress = False
            _last_restart = now
            restart_completed = True

    if was_offline:
        add_bot_log("Discord bot heartbeat is active.")
    if restart_completed:
        add_bot_log("Discord bot restart completed.")
    return restart_requested


def get_bot_status() -> dict[str, object]:
    now = time.time()
    with _lock:
        online = (
            _last_seen is not None
            and now - _last_seen <= HEARTBEAT_TIMEOUT_SECONDS
        )
        return {
            "online": online,
            "latency_ms": _latency_ms if online else None,
            "last_seen": _last_seen,
            "last_restart": _last_restart,
            "commands": list(_commands),
            "restart_pending": _restart_requested or _restart_in_progress,
        }


def get_bot_logs() -> list[str]:
    with _lock:
        return list(_logs)


def restart_bot() -> bool:
    """Queue a restart for a live bot to perform from its own process."""
    global _last_restart, _restart_requested

    with _lock:
        if (
            _last_seen is None
            or time.time() - _last_seen > HEARTBEAT_TIMEOUT_SECONDS
        ):
            return False
        _restart_requested = True
        _last_restart = time.time()

    add_bot_log("Restart requested from dashboard.")
    return True
