"""Persistent dashboard identities, login throttling, and server-side sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

ROLES = ("admin", "operator", "viewer")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 1024
SESSION_IDLE_SECONDS = 30 * 60
SESSION_ABSOLUTE_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 5
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
PROXMOX_USERNAME_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,64}$")
_SCRYPT_N = 1 << 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_LENGTH = 32


class AuthStoreError(RuntimeError):
    """Authentication data could not be read or updated safely."""


@dataclass(frozen=True)
class Session:
    token: str
    provider: str
    username: str
    role: str
    csrf_token: str
    expires_at: int
    absolute_expires_at: int


def normalize_local_username(username: str) -> str:
    normalized = username.strip().casefold()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username must be 1-64 letters, numbers, dots, dashes, or underscores.")
    return normalized


def normalize_proxmox_username(username: str) -> str:
    normalized = username.strip()
    if not PROXMOX_USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Proxmox username must include a valid user and realm.")
    return normalized


def hash_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be between {PASSWORD_MIN_LENGTH} and {PASSWORD_MAX_LENGTH} characters."
        )
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_LENGTH,
        maxmem=64 * 1024 * 1024,
    )
    return "scrypt${}${}${}${}".format(
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        base64.urlsafe_b64encode(salt + derived).decode("ascii").rstrip("="),
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, n_raw, r_raw, p_raw, encoded = encoded_hash.split("$", 4)
        if algorithm != "scrypt":
            return False
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
        if (n, r, p) != (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P):
            return False
        value = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        salt, expected = value[:16], value[16:]
        if len(salt) != 16 or len(expected) != _SCRYPT_LENGTH:
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=_SCRYPT_LENGTH,
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


class AuthStore:
    """SQLite-backed user, role mapping, rate-limit, and session store."""

    def __init__(
        self,
        path: Path,
        *,
        idle_timeout: int = SESSION_IDLE_SECONDS,
        absolute_timeout: int = SESSION_ABSOLUTE_SECONDS,
    ) -> None:
        if idle_timeout < 1 or absolute_timeout < idle_timeout:
            raise ValueError("Session timeouts must be positive and absolute >= idle.")
        self.path = Path(path).expanduser()
        self.idle_timeout = idle_timeout
        self.absolute_timeout = absolute_timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.path.parent.chmod(0o700)
        self._initialize()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS local_users (
                        username TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
                        disabled INTEGER NOT NULL DEFAULT 0 CHECK (disabled IN (0, 1)),
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS proxmox_mappings (
                        proxmox_username TEXT PRIMARY KEY,
                        role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
                        updated_at INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS sessions (
                        token_hash TEXT PRIMARY KEY,
                        provider TEXT NOT NULL CHECK (provider IN ('local', 'proxmox')),
                        username TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
                        csrf_token TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        last_seen INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL,
                        absolute_expires_at INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
                    CREATE TABLE IF NOT EXISTS login_attempts (
                        subject_hash TEXT NOT NULL,
                        attempted_at INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS login_attempt_window
                        ON login_attempts(subject_hash, attempted_at);
                    """
                )
        except sqlite3.Error as error:
            raise AuthStoreError("Could not initialize the authentication database.") from error
        if os.name != "nt":
            self.path.chmod(0o600)

    @staticmethod
    def _subject_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def is_rate_limited(self, username: str, client_host: str, now: int | None = None) -> bool:
        cutoff = (int(time.time()) if now is None else now) - LOGIN_WINDOW_SECONDS
        subjects = (self._subject_hash(f"user:{username.casefold()}"),
                    self._subject_hash(f"ip:{client_host}"))
        try:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM login_attempts WHERE attempted_at <= ?",
                    (cutoff,),
                )
                placeholders = ",".join("?" for _ in subjects)
                rows = connection.execute(
                    f"SELECT subject_hash, COUNT(*) AS attempts FROM login_attempts "
                    f"WHERE attempted_at > ? AND subject_hash IN ({placeholders}) "
                    "GROUP BY subject_hash",
                    (cutoff, *subjects),
                ).fetchall()
                return any(row["attempts"] >= LOGIN_MAX_ATTEMPTS for row in rows)
        except sqlite3.Error as error:
            raise AuthStoreError("Could not check authentication rate limits.") from error

    def record_failed_login(
        self, username: str, client_host: str, now: int | None = None
    ) -> None:
        timestamp = int(time.time()) if now is None else now
        subjects = (self._subject_hash(f"user:{username.casefold()}"),
                    self._subject_hash(f"ip:{client_host}"))
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM login_attempts WHERE attempted_at <= ?",
                    (timestamp - LOGIN_WINDOW_SECONDS,),
                )
                connection.executemany(
                    "INSERT INTO login_attempts(subject_hash, attempted_at) VALUES (?, ?)",
                    ((subject, timestamp) for subject in subjects),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise AuthStoreError("Could not record authentication failure.") from error

    def clear_login_failures(self, username: str, client_host: str) -> None:
        subjects = (self._subject_hash(f"user:{username.casefold()}"),
                    self._subject_hash(f"ip:{client_host}"))
        try:
            with self._connect() as connection:
                connection.executemany(
                    "DELETE FROM login_attempts WHERE subject_hash = ?",
                    ((subject,) for subject in subjects),
                )
        except sqlite3.Error as error:
            raise AuthStoreError("Could not clear authentication rate limits.") from error

    def authenticate_local(self, username: str, password: str) -> tuple[str, str] | None:
        try:
            normalized = normalize_local_username(username)
        except ValueError:
            normalized = username.strip().casefold()[:64]
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT password_hash, role, disabled FROM local_users WHERE username = ?",
                    (normalized,),
                ).fetchone()
            encoded = row["password_hash"] if row else _DUMMY_PASSWORD_HASH
            valid = verify_password(password, encoded)
            if not row or row["disabled"] or not valid:
                return None
            return normalized, row["role"]
        except sqlite3.Error as error:
            raise AuthStoreError("Could not authenticate the local account.") from error

    def authenticate_proxmox(self, proxmox_username: str) -> tuple[str, str] | None:
        try:
            normalized = normalize_proxmox_username(proxmox_username)
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT role FROM proxmox_mappings WHERE proxmox_username = ?",
                    (normalized.casefold(),),
                ).fetchone()
            return (normalized.casefold(), row["role"]) if row else None
        except ValueError:
            return None
        except sqlite3.Error as error:
            raise AuthStoreError("Could not read Proxmox role mapping.") from error

    def create_session(
        self, provider: str, username: str, role: str, now: int | None = None
    ) -> Session:
        timestamp = int(time.time()) if now is None else now
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = timestamp + self.idle_timeout
        absolute_expires_at = timestamp + self.absolute_timeout
        token_digest = self._subject_hash(token)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM sessions WHERE expires_at <= ? OR absolute_expires_at <= ?",
                    (timestamp, timestamp),
                )
                connection.execute(
                    """INSERT INTO sessions
                    (token_hash, provider, username, role, csrf_token, created_at,
                     last_seen, expires_at, absolute_expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (token_digest, provider, username, role, csrf_token, timestamp,
                     timestamp, expires_at, absolute_expires_at),
                )
                connection.commit()
            return Session(
                token, provider, username, role, csrf_token, expires_at, absolute_expires_at
            )
        except sqlite3.Error as error:
            raise AuthStoreError("Could not create an application session.") from error

    def get_session(
        self,
        token: str | None,
        now: int | None = None,
        *,
        touch: bool = True,
    ) -> Session | None:
        if not token or len(token) > 256:
            return None
        timestamp = int(time.time()) if now is None else now
        token_digest = self._subject_hash(token)
        try:
            with self._connect() as connection:
                if touch:
                    connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM sessions WHERE token_hash = ?", (token_digest,)
                ).fetchone()
                if (
                    row is None
                    or timestamp >= row["expires_at"]
                    or timestamp >= row["absolute_expires_at"]
                    or timestamp - row["last_seen"] >= self.idle_timeout
                ):
                    connection.execute(
                        "DELETE FROM sessions WHERE token_hash = ?", (token_digest,)
                    )
                    if touch:
                        connection.commit()
                    return None
                next_expiry = row["expires_at"]
                if touch:
                    next_expiry = min(
                        timestamp + self.idle_timeout, row["absolute_expires_at"]
                    )
                    connection.execute(
                        "UPDATE sessions SET last_seen = ?, expires_at = ? WHERE token_hash = ?",
                        (timestamp, next_expiry, token_digest),
                    )
                    connection.commit()
                return Session(
                    token,
                    row["provider"],
                    row["username"],
                    row["role"],
                    row["csrf_token"],
                    next_expiry,
                    row["absolute_expires_at"],
                )
        except sqlite3.Error as error:
            raise AuthStoreError("Could not read the application session.") from error

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        try:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM sessions WHERE token_hash = ?",
                    (self._subject_hash(token),),
                )
        except sqlite3.Error as error:
            raise AuthStoreError("Could not revoke the application session.") from error

    def create_local_user(self, username: str, password: str, role: str) -> None:
        normalized = normalize_local_username(username)
        if role not in ROLES:
            raise ValueError("Role must be admin, operator, or viewer.")
        encoded = hash_password(password)
        timestamp = int(time.time())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                has_admin = connection.execute(
                    "SELECT 1 FROM local_users WHERE role = 'admin' AND disabled = 0 LIMIT 1"
                ).fetchone()
                if not has_admin and role != "admin":
                    raise ValueError("The first enabled local account must have the admin role.")
                connection.execute(
                    """INSERT INTO local_users
                    (username, password_hash, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (normalized, encoded, role, timestamp, timestamp),
                )
                connection.commit()
        except sqlite3.IntegrityError as error:
            raise ValueError("That local username already exists.") from error
        except sqlite3.Error as error:
            raise AuthStoreError("Could not create the local account.") from error

    def set_local_password(self, username: str, password: str) -> None:
        normalized = normalize_local_username(username)
        encoded = hash_password(password)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                result = connection.execute(
                    "UPDATE local_users SET password_hash = ?, updated_at = ? WHERE username = ?",
                    (encoded, int(time.time()), normalized),
                )
                if result.rowcount != 1:
                    raise ValueError("Local account does not exist.")
                connection.execute(
                    "DELETE FROM sessions WHERE provider = 'local' AND username = ?",
                    (normalized,),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise AuthStoreError("Could not reset the local password.") from error

    def set_local_role(self, username: str, role: str) -> None:
        normalized = normalize_local_username(username)
        if role not in ROLES:
            raise ValueError("Role must be admin, operator, or viewer.")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                current = connection.execute(
                    "SELECT role, disabled FROM local_users WHERE username = ?",
                    (normalized,),
                ).fetchone()
                if (
                    current
                    and not current["disabled"]
                    and current["role"] == "admin"
                    and role != "admin"
                ):
                    admin_count = connection.execute(
                        "SELECT COUNT(*) FROM local_users WHERE role = 'admin' AND disabled = 0"
                    ).fetchone()[0]
                    if admin_count <= 1:
                        raise ValueError("At least one enabled local administrator must remain.")
                result = connection.execute(
                    "UPDATE local_users SET role = ?, updated_at = ? WHERE username = ?",
                    (role, int(time.time()), normalized),
                )
                if result.rowcount != 1:
                    raise ValueError("Local account does not exist.")
                connection.execute(
                    "DELETE FROM sessions WHERE provider = 'local' AND username = ?",
                    (normalized,),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise AuthStoreError("Could not update the local role.") from error

    def set_local_disabled(self, username: str, disabled: bool) -> None:
        normalized = normalize_local_username(username)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                current = connection.execute(
                    "SELECT role, disabled FROM local_users WHERE username = ?",
                    (normalized,),
                ).fetchone()
                if (
                    disabled
                    and current
                    and not current["disabled"]
                    and current["role"] == "admin"
                ):
                    admin_count = connection.execute(
                        "SELECT COUNT(*) FROM local_users WHERE role = 'admin' AND disabled = 0"
                    ).fetchone()[0]
                    if admin_count <= 1:
                        raise ValueError("At least one enabled local administrator must remain.")
                result = connection.execute(
                    "UPDATE local_users SET disabled = ?, updated_at = ? WHERE username = ?",
                    (int(disabled), int(time.time()), normalized),
                )
                if result.rowcount != 1:
                    raise ValueError("Local account does not exist.")
                if disabled:
                    connection.execute(
                        "DELETE FROM sessions WHERE provider = 'local' AND username = ?",
                        (normalized,),
                    )
                connection.commit()
        except sqlite3.Error as error:
            raise AuthStoreError("Could not update the local account state.") from error

    def map_proxmox_user(self, username: str, role: str) -> None:
        normalized = normalize_proxmox_username(username).casefold()
        if role not in ROLES:
            raise ValueError("Role must be admin, operator, or viewer.")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """INSERT INTO proxmox_mappings(proxmox_username, role, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(proxmox_username) DO UPDATE SET
                      role = excluded.role, updated_at = excluded.updated_at""",
                    (normalized, role, int(time.time())),
                )
                connection.execute(
                    "DELETE FROM sessions WHERE provider = 'proxmox' AND username = ?",
                    (normalized,),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise AuthStoreError("Could not map the Proxmox identity.") from error

    def unmap_proxmox_user(self, username: str) -> None:
        normalized = normalize_proxmox_username(username).casefold()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM proxmox_mappings WHERE proxmox_username = ?", (normalized,)
                )
                connection.execute(
                    "DELETE FROM sessions WHERE provider = 'proxmox' AND username = ?",
                    (normalized,),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise AuthStoreError("Could not remove the Proxmox identity mapping.") from error

    def list_local_users(self) -> list[dict[str, object]]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT username, role, disabled, created_at, updated_at "
                    "FROM local_users ORDER BY username"
                ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise AuthStoreError("Could not list local accounts.") from error

    def list_proxmox_mappings(self) -> list[dict[str, object]]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT proxmox_username, role, updated_at "
                    "FROM proxmox_mappings ORDER BY proxmox_username"
                ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise AuthStoreError("Could not list Proxmox mappings.") from error


_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-only")
