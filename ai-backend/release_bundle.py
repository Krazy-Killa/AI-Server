"""Signed release-bundle verification and staging (verify-only, never applies).

A bundle is an uncompressed outer tar with exactly three regular files:
``manifest.json`` (canonical JSON), ``manifest.sig`` (base64 Ed25519 signature
over the raw manifest bytes) and ``payload.tar.gz``. The manifest is signed and
carries the payload digest, so the payload is only trusted after both the
signature and the digest check pass. Staged bundles are stored for the operator
to apply at the console; nothing in this module executes or installs them.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import json
import os
import posixpath
import re
import shutil
import tarfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

FORMAT_VERSION = 1
PAYLOAD_TYPE = "source-tree"
MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "manifest.sig"
PAYLOAD_NAME = "payload.tar.gz"
OUTER_MEMBERS = frozenset({MANIFEST_NAME, SIGNATURE_NAME, PAYLOAD_NAME})
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SIGNATURE_BYTES = 512
MAX_PAYLOAD_MEMBERS = 2000
MAX_UNPACKED_BYTES = 256 * 1024 * 1024
MAX_STAGED_RELEASES = 3
REQUIRED_PAYLOAD_FILES = ("Containerfile", "ai-backend/main.py")
FORBIDDEN_SUFFIXES = (
    ".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx", ".gguf",
    ".safetensors", ".onnx",
)
RELEASE_ID_PATTERN = re.compile(r"^[0-9]{8}-[a-z0-9][a-z0-9-]{0,40}$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]{1,32})?$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_KEYS = frozenset(
    {"format_version", "release_id", "version", "created_at",
     "requires_data_migration", "payload"}
)
PAYLOAD_KEYS = frozenset({"type", "filename", "sha256", "size"})
RECORD_NAME = "record.json"


class BundleError(ValueError):
    """A bundle failed verification. Messages are safe to show to the operator."""


class BundleConflict(BundleError):
    """The release is already staged."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def decode_public_key(encoded: str) -> bytes:
    try:
        raw = base64.b64decode(encoded.strip(), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Public key is not valid base64.") from error
    if len(raw) != 32:
        raise ValueError("Public key must be a raw 32-byte Ed25519 key.")
    return raw


def key_fingerprint(raw_key: bytes) -> str:
    return hashlib.sha256(raw_key).hexdigest()[:16]


def _read_limited(handle: BinaryIO, limit: int, label: str) -> bytes:
    data = handle.read(limit + 1)
    if len(data) > limit:
        raise BundleError(f"{label} is too large.")
    return data


def _verify_signature(manifest: bytes, signature_b64: bytes, trusted: tuple[bytes, ...]) -> str:
    try:
        signature = base64.b64decode(signature_b64.strip(), validate=True)
    except (binascii.Error, ValueError) as error:
        raise BundleError("Signature is not valid base64.") from error
    if len(signature) != 64:
        raise BundleError("Signature has the wrong length.")
    for raw_key in trusted:
        try:
            Ed25519PublicKey.from_public_bytes(raw_key).verify(signature, manifest)
        except InvalidSignature:
            continue
        return key_fingerprint(raw_key)
    raise BundleError("Signature is not valid for any trusted signing key.")


def _validate_manifest(manifest: object) -> dict:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise BundleError("Manifest fields do not match the supported format.")
    if manifest["format_version"] != FORMAT_VERSION or isinstance(manifest["format_version"], bool):
        raise BundleError("Unsupported manifest format version.")
    release_id = manifest["release_id"]
    if not isinstance(release_id, str) or not RELEASE_ID_PATTERN.fullmatch(release_id):
        raise BundleError("Manifest release_id is invalid.")
    version = manifest["version"]
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise BundleError("Manifest version is invalid.")
    created_at = manifest["created_at"]
    try:
        if not isinstance(created_at, str):
            raise ValueError
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise BundleError("Manifest created_at is invalid.") from error
    if manifest["requires_data_migration"] is not False:
        raise BundleError(
            "Releases that require a data migration cannot be staged by this updater."
        )
    payload = manifest["payload"]
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS:
        raise BundleError("Manifest payload fields do not match the supported format.")
    if payload["type"] != PAYLOAD_TYPE:
        raise BundleError("Unsupported payload type.")
    if payload["filename"] != PAYLOAD_NAME:
        raise BundleError("Manifest payload filename is invalid.")
    if not isinstance(payload["sha256"], str) or not SHA256_PATTERN.fullmatch(payload["sha256"]):
        raise BundleError("Manifest payload digest is invalid.")
    size = payload["size"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise BundleError("Manifest payload size is invalid.")
    return manifest


class _LimitedReader:
    """Read-only wrapper that aborts once too many bytes have been produced."""

    def __init__(self, source: BinaryIO, limit: int) -> None:
        self._source = source
        self._remaining = limit

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = 1024 * 1024
        data = self._source.read(size)
        self._remaining -= len(data)
        if self._remaining < 0:
            raise BundleError("Payload expands beyond the allowed size.")
        return data


def _safe_member_name(name: str) -> str:
    if (
        not name
        or len(name) > 255
        or "\\" in name
        or "\x00" in name
        or name.startswith("/")
        or re.match(r"^[A-Za-z]:", name)
    ):
        raise BundleError("Payload contains an unsafe path.")
    normalized = posixpath.normpath(name)
    if normalized != name.rstrip("/") or any(
        part in ("", ".", "..") for part in normalized.split("/")
    ):
        raise BundleError("Payload contains an unsafe path.")
    return normalized


def _reject_forbidden(path: str) -> None:
    base = path.rsplit("/", 1)[-1].lower()
    if base.startswith(".env") and base != ".env.example":
        raise BundleError("Payload contains a secrets file.")
    if base.endswith(FORBIDDEN_SUFFIXES) or base in ("id_rsa", "id_ed25519"):
        raise BundleError("Payload contains a file type that must not be shipped.")


def inspect_payload(path: Path) -> dict:
    """Validate the payload tar without extracting it."""
    names: set[str] = set()
    files: set[str] = set()
    unpacked = 0
    try:
        with gzip.open(path, "rb") as compressed:
            limited = _LimitedReader(compressed, MAX_UNPACKED_BYTES + 16 * 1024 * 1024)
            with tarfile.open(fileobj=limited, mode="r|") as archive:  # type: ignore[arg-type]
                for member in archive:
                    if len(names) >= MAX_PAYLOAD_MEMBERS:
                        raise BundleError("Payload contains too many entries.")
                    name = _safe_member_name(member.name)
                    if name in names:
                        raise BundleError("Payload contains duplicate entries.")
                    names.add(name)
                    if member.isdir():
                        continue
                    if not member.isreg():
                        raise BundleError("Payload contains links or special files.")
                    _reject_forbidden(name)
                    unpacked += member.size
                    if unpacked > MAX_UNPACKED_BYTES:
                        raise BundleError("Payload expands beyond the allowed size.")
                    files.add(name)
    except BundleError:
        raise
    except (tarfile.TarError, OSError, EOFError) as error:
        raise BundleError("Payload is not a readable gzip tar archive.") from error
    for required in REQUIRED_PAYLOAD_FILES:
        if required not in files:
            raise BundleError(f"Payload is missing {required}.")
    return {"file_count": len(files), "unpacked_bytes": unpacked}


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(path, 0o700)


def purge_expired(staging_dir: Path, now: float | None = None) -> int:
    now = time.time() if now is None else now
    removed = 0
    if not staging_dir.is_dir():
        return removed
    for entry in staging_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith(".incoming"):
            if now - entry.stat().st_mtime > 3600:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
            continue
        record = _load_record(entry)
        if record is None or record["expires_at"] <= now:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


def _load_record(directory: Path) -> dict | None:
    try:
        record = json.loads((directory / RECORD_NAME).read_text(encoding="utf-8"))
        if isinstance(record, dict) and isinstance(record.get("expires_at"), (int, float)):
            return record
    except (OSError, ValueError):
        pass
    return None


def list_staged(staging_dir: Path) -> list[dict]:
    purge_expired(staging_dir)
    records = []
    if staging_dir.is_dir():
        for entry in sorted(staging_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                record = _load_record(entry)
                if record is not None:
                    records.append(record)
    return records


def get_staged(staging_dir: Path, release_id: str) -> dict | None:
    if not RELEASE_ID_PATTERN.fullmatch(release_id):
        return None
    purge_expired(staging_dir)
    return _load_record(staging_dir / release_id)


def discard_staged(staging_dir: Path, release_id: str) -> bool:
    if not RELEASE_ID_PATTERN.fullmatch(release_id):
        return False
    target = staging_dir / release_id
    if not target.is_dir():
        return False
    shutil.rmtree(target)
    return True


def new_incoming_path(staging_dir: Path) -> Path:
    incoming = staging_dir / ".incoming"
    _ensure_private_dir(incoming)
    return incoming / f"{uuid.uuid4().hex}.upload"


def verify_and_stage(
    upload_path: Path,
    *,
    staging_dir: Path,
    trusted_keys: tuple[bytes, ...],
    expiry_seconds: int,
    now: float | None = None,
) -> dict:
    """Verify an uploaded bundle and stage it. Raises BundleError on any failure."""
    if not trusted_keys:
        raise BundleError("No trusted signing key is configured.")
    now = time.time() if now is None else now
    _ensure_private_dir(staging_dir)
    purge_expired(staging_dir, now)

    try:
        with tarfile.open(upload_path, mode="r:") as outer:
            members = []
            for member in outer:
                members.append(member)
                if len(members) > len(OUTER_MEMBERS):
                    raise BundleError("Bundle contains unexpected entries.")
            by_name = {member.name: member for member in members}
            if len(by_name) != len(members) or set(by_name) != OUTER_MEMBERS:
                raise BundleError("Bundle must contain exactly the manifest, signature and payload.")
            if not all(member.isreg() for member in members):
                raise BundleError("Bundle contains links or special files.")

            manifest_bytes = _read_limited(
                outer.extractfile(by_name[MANIFEST_NAME]), MAX_MANIFEST_BYTES, "Manifest"
            )
            signature_bytes = _read_limited(
                outer.extractfile(by_name[SIGNATURE_NAME]), MAX_SIGNATURE_BYTES, "Signature"
            )
            signer = _verify_signature(manifest_bytes, signature_bytes, trusted_keys)
            try:
                manifest = _validate_manifest(json.loads(manifest_bytes))
            except ValueError as error:
                if isinstance(error, BundleError):
                    raise
                raise BundleError("Manifest is not valid JSON.") from error
            if canonical_json(manifest) != manifest_bytes:
                raise BundleError("Manifest is not in canonical form.")

            release_id = manifest["release_id"]
            if (staging_dir / release_id).exists():
                raise BundleConflict("This release is already staged. Discard it first.")
            if len([e for e in staging_dir.iterdir() if e.is_dir() and not e.name.startswith(".")]) >= MAX_STAGED_RELEASES:
                raise BundleError("Too many releases are staged. Discard one first.")

            expected = manifest["payload"]
            if by_name[PAYLOAD_NAME].size != expected["size"]:
                raise BundleError("Payload size does not match the signed manifest.")
            work = staging_dir / f".incoming-{uuid.uuid4().hex}"
            _ensure_private_dir(work)
            try:
                payload_path = work / PAYLOAD_NAME
                digest = hashlib.sha256()
                with outer.extractfile(by_name[PAYLOAD_NAME]) as source, open(
                    payload_path, "wb"
                ) as target:
                    while chunk := source.read(1024 * 1024):
                        digest.update(chunk)
                        target.write(chunk)
                if digest.hexdigest() != expected["sha256"]:
                    raise BundleError("Payload digest does not match the signed manifest.")
                summary = inspect_payload(payload_path)
                (work / MANIFEST_NAME).write_bytes(manifest_bytes)
                (work / SIGNATURE_NAME).write_bytes(signature_bytes)
                record = {
                    "release_id": release_id,
                    "version": manifest["version"],
                    "created_at": manifest["created_at"],
                    "signer": signer,
                    "payload_type": expected["type"],
                    "payload_sha256": expected["sha256"],
                    "payload_size": expected["size"],
                    "file_count": summary["file_count"],
                    "unpacked_bytes": summary["unpacked_bytes"],
                    "staged_at": now,
                    "expires_at": now + expiry_seconds,
                    "status": "verified",
                }
                (work / RECORD_NAME).write_text(json.dumps(record), encoding="utf-8")
                if os.name != "nt":
                    for item in work.iterdir():
                        os.chmod(item, 0o600)
                os.replace(work, staging_dir / release_id)
            except BaseException:
                shutil.rmtree(work, ignore_errors=True)
                raise
            return record
    except BundleError:
        raise
    except (tarfile.TarError, OSError, EOFError) as error:
        raise BundleError("Upload is not a readable release bundle.") from error
