import base64
import gzip
import hashlib
import io
import os
import tarfile
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "AI_SERVER_LOG_DIR", tempfile.mkdtemp(prefix="ai-server-test-logs-")
)

import release_bundle
from auth_test_helpers import authenticated_client
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

RELEASE_ID = "20261201-test"
GOOD_FILES = {
    "Containerfile": b"FROM scratch\n",
    "ai-backend/main.py": b"print('hi')\n",
}


def public_raw(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def make_payload(files=None, extra=None):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in (files if files is not None else GOOD_FILES).items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        if extra:
            extra(archive)
    return buffer.getvalue()


def make_manifest(payload, **overrides):
    manifest = {
        "format_version": 1,
        "release_id": RELEASE_ID,
        "version": "9.9.9",
        "created_at": "2026-12-01T00:00:00Z",
        "requires_data_migration": False,
        "payload": {
            "type": "source-tree",
            "filename": "payload.tar.gz",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        },
    }
    manifest.update(overrides)
    return manifest


def make_bundle(key, payload=None, manifest=None, manifest_bytes=None,
                signature=None, extra_members=()):
    payload = make_payload() if payload is None else payload
    manifest_bytes = manifest_bytes or release_bundle.canonical_json(
        manifest or make_manifest(payload)
    )
    signature = signature or base64.b64encode(key.sign(manifest_bytes))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as outer:
        for name, data in (
            ("manifest.json", manifest_bytes),
            ("manifest.sig", signature),
            ("payload.tar.gz", payload),
            *extra_members,
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            outer.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class ReleaseBundleTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="ai-server-bundle-test-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.directory, ignore_errors=True))
        self.key = Ed25519PrivateKey.generate()
        self.trusted = (public_raw(self.key),)
        self.staging = self.directory / "staging"

    def stage(self, data, trusted=None, **kwargs):
        upload = self.directory / "upload.bin"
        upload.write_bytes(data)
        return release_bundle.verify_and_stage(
            upload,
            staging_dir=self.staging,
            trusted_keys=trusted if trusted is not None else self.trusted,
            expiry_seconds=kwargs.pop("expiry_seconds", 3600),
            **kwargs,
        )

    def assertRejected(self, data, fragment, **kwargs):
        with self.assertRaises(release_bundle.BundleError) as context:
            self.stage(data, **kwargs)
        self.assertIn(fragment, str(context.exception))
        self.assertEqual(release_bundle.list_staged(self.staging), [])

    def test_valid_bundle_is_staged(self):
        record = self.stage(make_bundle(self.key))
        self.assertEqual(record["release_id"], RELEASE_ID)
        self.assertEqual(record["status"], "verified")
        self.assertEqual(record["file_count"], 2)
        self.assertEqual(record["signer"], release_bundle.key_fingerprint(self.trusted[0]))
        self.assertEqual(
            release_bundle.get_staged(self.staging, RELEASE_ID)["version"], "9.9.9"
        )
        self.assertTrue((self.staging / RELEASE_ID / "payload.tar.gz").is_file())

    def test_wrong_key_is_rejected(self):
        other = (public_raw(Ed25519PrivateKey.generate()),)
        self.assertRejected(make_bundle(self.key), "trusted signing key", trusted=other)

    def test_no_trusted_key_is_rejected(self):
        self.assertRejected(make_bundle(self.key), "No trusted signing key", trusted=())

    def test_tampered_manifest_is_rejected(self):
        payload = make_payload()
        signed = release_bundle.canonical_json(make_manifest(payload))
        signature = base64.b64encode(self.key.sign(signed))
        tampered = release_bundle.canonical_json(make_manifest(payload, version="1.0.0"))
        self.assertRejected(
            make_bundle(self.key, payload=payload, manifest_bytes=tampered, signature=signature),
            "trusted signing key",
        )

    def test_tampered_payload_is_rejected(self):
        payload = make_payload()
        other = make_payload({**GOOD_FILES, "ai-backend/evil.py": b"x"})
        data = make_bundle(self.key, payload=other, manifest=make_manifest(payload))
        self.assertRejected(data, "Payload size does not match")

    def test_same_size_payload_swap_is_rejected_by_digest(self):
        payload = make_payload()
        swapped = bytearray(payload)
        swapped[-5] ^= 0xFF
        data = make_bundle(self.key, payload=bytes(swapped), manifest=make_manifest(payload))
        self.assertRejected(data, "digest does not match")

    def test_non_canonical_manifest_is_rejected(self):
        payload = make_payload()
        pretty = release_bundle.canonical_json(make_manifest(payload)).replace(b",", b", ")
        self.assertRejected(
            make_bundle(self.key, payload=payload, manifest_bytes=pretty), "canonical"
        )

    def test_data_migration_release_is_rejected(self):
        payload = make_payload()
        data = make_bundle(
            self.key, payload=payload,
            manifest=make_manifest(payload, requires_data_migration=True),
        )
        self.assertRejected(data, "data migration")

    def test_unknown_manifest_field_and_bad_ids_are_rejected(self):
        payload = make_payload()
        for overrides in (
            {"extra": 1}, {"release_id": "../x"}, {"release_id": "20261201-A"},
            {"version": "latest"}, {"format_version": 2}, {"created_at": "soon"},
        ):
            manifest = make_manifest(payload)
            manifest.update(overrides)
            with self.subTest(overrides=overrides):
                self.assertRejected(
                    make_bundle(self.key, payload=payload, manifest=manifest), "anifest"
                )

    def test_extra_or_missing_outer_members_are_rejected(self):
        self.assertRejected(
            make_bundle(self.key, extra_members=(("extra.txt", b"x"),)), "unexpected entries"
        )
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:") as outer:
            info = tarfile.TarInfo("manifest.json")
            outer.addfile(info, io.BytesIO(b""))
        self.assertRejected(buffer.getvalue(), "exactly")

    def test_outer_link_member_is_rejected(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:") as outer:
            for name in ("manifest.json", "manifest.sig"):
                outer.addfile(tarfile.TarInfo(name), io.BytesIO(b""))
            link = tarfile.TarInfo("payload.tar.gz")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            outer.addfile(link)
        self.assertRejected(buffer.getvalue(), "links")

    def test_garbage_upload_is_rejected(self):
        self.assertRejected(b"not a tar archive" * 100, "readable")

    def test_unsafe_payload_members_are_rejected(self):
        def link(archive):
            info = tarfile.TarInfo("ai-backend/link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            archive.addfile(info)

        cases = {
            "traversal": ({**GOOD_FILES, "../escape.py": b"x"}, None, "unsafe path"),
            "absolute": ({**GOOD_FILES, "/etc/cron.d/x": b"x"}, None, "unsafe path"),
            "backslash": ({**GOOD_FILES, "a\\b.py": b"x"}, None, "unsafe path"),
            "dotslash": ({**GOOD_FILES, "./x.py": b"x"}, None, "unsafe path"),
            "env file": ({**GOOD_FILES, "ai-backend/.env": b"x"}, None, "secrets"),
            "database": ({**GOOD_FILES, "data/auth.sqlite3": b"x"}, None, "must not be shipped"),
            "private key": ({**GOOD_FILES, "deploy/server.key": b"x"}, None, "must not be shipped"),
            "symlink": (None, link, "links"),
            "missing required": ({"Containerfile": b"x"}, None, "missing ai-backend/main.py"),
        }
        for label, (files, extra, fragment) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as _:
                payload = make_payload(files, extra)
                self.assertRejected(make_bundle(self.key, payload=payload), fragment)

    def test_duplicate_payload_members_are_rejected(self):
        def duplicate(archive):
            info = tarfile.TarInfo("Containerfile")
            info.size = 1
            archive.addfile(info, io.BytesIO(b"x"))

        payload = make_payload(extra=duplicate)
        self.assertRejected(make_bundle(self.key, payload=payload), "duplicate")

    def test_decompression_bomb_is_rejected(self):
        with patch.object(release_bundle, "MAX_UNPACKED_BYTES", 1024 * 1024), \
                patch.object(release_bundle, "_LimitedReader", wraps=release_bundle._LimitedReader):
            payload = make_payload({**GOOD_FILES, "ai-backend/big.py": b"0" * (4 * 1024 * 1024)})
            self.assertRejected(make_bundle(self.key, payload=payload), "expands beyond")

    def test_non_gzip_payload_is_rejected(self):
        payload = b"plain bytes, not gzip"
        self.assertRejected(make_bundle(self.key, payload=payload), "gzip tar")

    def test_duplicate_release_conflicts_and_discard_works(self):
        self.stage(make_bundle(self.key))
        with self.assertRaises(release_bundle.BundleConflict):
            self.stage(make_bundle(self.key))
        self.assertTrue(release_bundle.discard_staged(self.staging, RELEASE_ID))
        self.assertFalse(release_bundle.discard_staged(self.staging, RELEASE_ID))
        self.assertFalse(release_bundle.discard_staged(self.staging, "../etc"))

    def test_staged_release_expires(self):
        self.stage(make_bundle(self.key), expiry_seconds=60)
        self.assertEqual(len(release_bundle.list_staged(self.staging)), 1)
        self.assertEqual(release_bundle.purge_expired(self.staging, now=10**11), 1)
        self.assertIsNone(release_bundle.get_staged(self.staging, RELEASE_ID))

    def test_failed_verification_leaves_no_work_directories(self):
        with self.assertRaises(release_bundle.BundleError):
            self.stage(make_bundle(self.key, payload=make_payload({"Containerfile": b"x"})))
        leftovers = [p.name for p in self.staging.iterdir() if p.name != ".incoming"]
        self.assertEqual(leftovers, [])


class ReleaseUpdateApiTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.directory = Path(tempfile.mkdtemp(prefix="ai-server-update-api-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.directory, ignore_errors=True))
        self.key = Ed25519PrivateKey.generate()
        self.configure(
            cors_origins=("http://127.0.0.1:8001",),
            update_public_keys=(public_raw(self.key),),
        )
        self.client, self.store = authenticated_client(self, main)

    def configure(self, **overrides):
        patcher = patch.object(
            self.main.runtime, "settings",
            replace(
                self.main.runtime.settings,
                update_staging_dir=self.directory / "updates",
                update_max_bytes=5 * 1024 * 1024,
                **overrides,
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def upload(self, data, client=None):
        return (client or self.client).post(
            "/api/admin/updates", content=data,
            headers={"content-type": "application/octet-stream"},
        )

    def test_upload_stage_list_get_and_discard(self):
        response = self.upload(make_bundle(self.key))
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["release_id"], RELEASE_ID)
        listing = self.client.get("/api/admin/updates").json()
        self.assertTrue(listing["enabled"])
        self.assertFalse(listing["apply_supported"])
        self.assertEqual([r["release_id"] for r in listing["staged"]], [RELEASE_ID])
        self.assertEqual(self.client.get(f"/api/admin/updates/{RELEASE_ID}").status_code, 200)
        self.assertEqual(self.client.post(f"/api/admin/updates/{RELEASE_ID}/apply").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/admin/updates/{RELEASE_ID}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/admin/updates/{RELEASE_ID}").status_code, 404)

    def test_unconfigured_key_disables_upload(self):
        self.configure(update_public_keys=())
        self.assertEqual(self.upload(make_bundle(self.key)).status_code, 503)
        self.assertFalse(self.client.get("/api/admin/updates").json()["enabled"])

    def test_bad_signature_is_422_and_nothing_is_staged(self):
        other = Ed25519PrivateKey.generate()
        response = self.upload(make_bundle(other))
        self.assertEqual(response.status_code, 422)
        self.assertIn("trusted signing key", response.json()["detail"])
        self.assertEqual(self.client.get("/api/admin/updates").json()["staged"], [])

    def test_oversized_and_empty_uploads_are_rejected(self):
        self.assertEqual(self.upload(b"x" * (5 * 1024 * 1024 + 1)).status_code, 413)
        self.assertEqual(self.upload(b"").status_code, 400)

    def test_duplicate_upload_is_409(self):
        self.assertEqual(self.upload(make_bundle(self.key)).status_code, 201)
        self.assertEqual(self.upload(make_bundle(self.key)).status_code, 409)

    def test_upload_requires_admin_csrf_and_origin(self):
        data = make_bundle(self.key)
        no_csrf = self.client.post(
            "/api/admin/updates", content=data, headers={"x-csrf-token": "wrong"}
        )
        self.assertEqual(no_csrf.status_code, 403)
        bad_origin = self.client.post(
            "/api/admin/updates", content=data, headers={"origin": "http://evil.example"}
        )
        self.assertEqual(bad_origin.status_code, 403)
        from fastapi.testclient import TestClient

        anonymous = TestClient(self.main.app)
        self.assertEqual(self.upload(data, anonymous).status_code, 401)
        self.store.create_local_user("plain-operator", "CorrectHorseBatteryStaple42!", "operator")
        operator = TestClient(self.main.app)
        login = operator.post(
            "/api/auth/login",
            json={"provider": "local", "username": "plain-operator",
                  "password": "CorrectHorseBatteryStaple42!"},
            headers={"origin": "http://127.0.0.1:8001"},
        )
        operator.headers.update(
            {"origin": "http://127.0.0.1:8001", "x-csrf-token": login.json()["csrf_token"]}
        )
        self.assertEqual(self.upload(data, operator).status_code, 403)
        self.assertEqual(operator.get("/api/admin/updates").status_code, 403)
        self.assertEqual(operator.delete(f"/api/admin/updates/{RELEASE_ID}").status_code, 403)


if __name__ == "__main__":
    unittest.main()
