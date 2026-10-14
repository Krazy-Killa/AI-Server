import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from auth import AuthStore, hash_password, verify_password
from fastapi.testclient import TestClient

TEST_ORIGIN = "http://127.0.0.1:8001"
ADMIN_PASSWORD = "CorrectHorseBatteryStaple42!"


class PasswordHashTests(unittest.TestCase):
    def test_hash_is_salted_and_verifies_only_the_original_password(self):
        first = hash_password(ADMIN_PASSWORD)
        second = hash_password(ADMIN_PASSWORD)

        self.assertNotEqual(first, second)
        self.assertTrue(verify_password(ADMIN_PASSWORD, first))
        self.assertFalse(verify_password("incorrect password", first))

    def test_enforces_password_length_boundaries(self):
        with self.assertRaises(ValueError):
            hash_password("x" * 7)
        self.assertTrue(verify_password("x" * 8, hash_password("x" * 8)))
        with self.assertRaises(ValueError):
            hash_password("x" * 1025)


class AuthStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="auth-store-test-")
        self.addCleanup(self.temporary_directory.cleanup)
        self.store = AuthStore(
            Path(self.temporary_directory.name) / "auth.sqlite3",
            idle_timeout=120,
            absolute_timeout=300,
        )

    def test_requires_an_admin_before_creating_other_roles(self):
        with self.assertRaisesRegex(ValueError, "first enabled local account"):
            self.store.create_local_user("viewer", ADMIN_PASSWORD, "viewer")

        self.store.create_local_user("Admin", ADMIN_PASSWORD, "admin")
        self.store.create_local_user("viewer", ADMIN_PASSWORD, "viewer")
        self.assertEqual(
            [user["username"] for user in self.store.list_local_users()],
            ["admin", "viewer"],
        )

    def test_expired_or_revoked_sessions_cannot_be_reused(self):
        session = self.store.create_session("local", "admin", "admin", now=1000)
        self.assertIsNotNone(self.store.get_session(session.token, now=1010))
        self.assertIsNone(self.store.get_session(session.token, now=1131))

        another = self.store.create_session("local", "admin", "admin", now=2000)
        self.store.revoke_session(another.token)
        self.assertIsNone(self.store.get_session(another.token, now=2001))

    def test_new_session_prunes_expired_session_rows(self):
        self.store.create_session("local", "admin", "admin", now=1000)
        self.store.create_session("local", "admin", "admin", now=2000)

        with closing(sqlite3.connect(self.store.path)) as connection:
            session_count = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

        self.assertEqual(session_count, 1)

    def test_role_changes_and_account_disabling_revoke_sessions(self):
        self.store.create_local_user("admin", ADMIN_PASSWORD, "admin")
        session = self.store.create_session("local", "admin", "admin")

        with self.assertRaisesRegex(ValueError, "administrator must remain"):
            self.store.set_local_role("admin", "viewer")
        with self.assertRaisesRegex(ValueError, "administrator must remain"):
            self.store.set_local_disabled("admin", True)

        self.store.create_local_user("second-admin", ADMIN_PASSWORD, "admin")
        self.store.set_local_role("admin", "operator")
        self.assertIsNone(self.store.get_session(session.token))

    def test_login_throttle_tracks_username_and_source(self):
        for _ in range(5):
            self.store.record_failed_login("some-user", "127.0.0.1", now=1000)
        self.assertTrue(self.store.is_rate_limited("some-user", "127.0.0.2", now=1001))
        self.assertTrue(self.store.is_rate_limited("another-user", "127.0.0.1", now=1001))
        self.assertFalse(self.store.is_rate_limited("another-user", "127.0.0.2", now=1001))

    def test_proxmox_mapping_is_explicit_and_revocable(self):
        self.assertIsNone(self.store.authenticate_proxmox("operator@pve"))
        self.store.map_proxmox_user("operator@pve", "operator")
        self.assertEqual(
            self.store.authenticate_proxmox("operator@pve"),
            ("operator@pve", "operator"),
        )
        session = self.store.create_session("proxmox", "operator@pve", "operator")
        self.store.map_proxmox_user("operator@pve", "viewer")
        self.assertIsNone(self.store.get_session(session.token))
        self.assertEqual(
            self.store.authenticate_proxmox("operator@pve"),
            ("operator@pve", "viewer"),
        )

        session = self.store.create_session("proxmox", "operator@pve", "viewer")
        self.store.unmap_proxmox_user("operator@pve")
        self.assertIsNone(self.store.authenticate_proxmox("operator@pve"))
        self.assertIsNone(self.store.get_session(session.token))


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="auth-api-test-")
        self.addCleanup(self.temporary_directory.cleanup)
        database_path = Path(self.temporary_directory.name) / "auth.sqlite3"
        self.store = AuthStore(database_path)
        self.store.create_local_user("admin", ADMIN_PASSWORD, "admin")
        self.store.create_local_user("operator", ADMIN_PASSWORD, "operator")
        self.store.create_local_user("viewer", ADMIN_PASSWORD, "viewer")
        settings_patch = patch.object(
            main,
            "settings",
            replace(
                main.settings,
                auth_database_path=database_path,
                auth_cookie_secure=False,
                bot_api_token="",
            ),
        )
        auth_patch = patch.object(main, "auth_store", self.store)
        settings_patch.start()
        auth_patch.start()
        self.addCleanup(auth_patch.stop)
        self.addCleanup(settings_patch.stop)
        self.client = TestClient(main.app)

    def login(self, username="admin", provider="local"):
        response = self.client.post(
            "/api/auth/login",
            json={
                "provider": provider,
                "username": username,
                "password": ADMIN_PASSWORD,
            },
            headers={"origin": TEST_ORIGIN},
        )
        return response

    def set_csrf(self, response):
        self.client.headers.update(
            {"origin": TEST_ORIGIN, "x-csrf-token": response.json()["csrf_token"]}
        )

    def test_protected_endpoints_require_login_and_status_is_public(self):
        self.assertEqual(self.client.get("/api/system").status_code, 401)
        self.assertEqual(
            self.client.get("/api/auth/status").json(),
            {"authenticated": False},
        )

    def test_unknown_api_routes_are_denied_even_to_authenticated_users(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get("/api/not-enabled").status_code, 403)

    def test_local_login_sets_httponly_strict_cookie_and_status(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertNotIn("secure", cookie)
        status = self.client.get("/api/auth/status").json()
        self.assertEqual(status["role"], "admin")
        self.assertEqual(status["username"], "admin")

    def test_mutations_require_csrf_and_role_restrictions_are_enforced(self):
        admin_login = self.login()
        self.assertEqual(admin_login.status_code, 200)

        missing_csrf = self.client.post(
            "/api/diagnostics/observe", headers={"origin": TEST_ORIGIN}
        )
        self.assertEqual(missing_csrf.status_code, 403)
        self.assertEqual(missing_csrf.json()["detail"], "CSRF validation failed.")

        self.set_csrf(admin_login)
        allowed = self.client.post("/api/diagnostics/observe")
        self.assertEqual(allowed.status_code, 200)

        viewer_client = TestClient(self.main.app)
        viewer_login = viewer_client.post(
            "/api/auth/login",
            json={
                "provider": "local",
                "username": "viewer",
                "password": ADMIN_PASSWORD,
            },
            headers={"origin": TEST_ORIGIN},
        )
        self.assertEqual(viewer_login.status_code, 200)
        viewer_client.headers.update(
            {"origin": TEST_ORIGIN, "x-csrf-token": viewer_login.json()["csrf_token"]}
        )
        denied = viewer_client.post("/api/diagnostics/observe")
        self.assertEqual(denied.status_code, 403)

    def test_logout_revokes_the_session(self):
        login = self.login()
        self.set_csrf(login)

        response = self.client.post("/api/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.get("/api/auth/status").json()["authenticated"])
        self.assertEqual(self.client.get("/api/system").status_code, 401)

    def test_login_requires_an_allowed_origin_and_generic_credentials_failure(self):
        bad_origin = self.client.post(
            "/api/auth/login",
            json={"provider": "local", "username": "admin", "password": ADMIN_PASSWORD},
            headers={"origin": "https://attacker.example"},
        )
        self.assertEqual(bad_origin.status_code, 403)

        failure = self.client.post(
            "/api/auth/login",
            json={"provider": "local", "username": "missing", "password": ADMIN_PASSWORD},
            headers={"origin": TEST_ORIGIN},
        )
        self.assertEqual(failure.status_code, 401)
        self.assertEqual(failure.json()["detail"], "Invalid credentials or account access.")

    def test_proxmox_login_requires_an_explicit_role_mapping(self):
        self.store.map_proxmox_user("mapped@pve", "operator")
        with patch.object(
            self.main,
            "proxmox_authenticator",
            SimpleNamespace(
                authenticate=lambda username, password: SimpleNamespace(
                    username=username, ticket="secret", csrf_prevention_token="secret"
                )
            ),
        ):
            mapped = self.client.post(
                "/api/auth/login",
                json={
                    "provider": "proxmox",
                    "username": "mapped@pve",
                    "password": ADMIN_PASSWORD,
                },
                headers={"origin": TEST_ORIGIN},
            )
            self.assertEqual(mapped.status_code, 200)
            self.assertEqual(mapped.json()["role"], "operator")

            unmapped = TestClient(self.main.app).post(
                "/api/auth/login",
                json={
                    "provider": "proxmox",
                    "username": "unmapped@pve",
                    "password": ADMIN_PASSWORD,
                },
                headers={"origin": TEST_ORIGIN},
            )
        self.assertEqual(unmapped.status_code, 401)
        self.assertEqual(
            unmapped.json()["detail"], "Invalid credentials or account access."
        )

    def test_discord_bot_routes_require_scoped_service_credential(self):
        settings_patch = patch.object(
            self.main,
            "settings",
            replace(self.main.settings, bot_api_token="b" * 40),
        )
        settings_patch.start()
        self.addCleanup(settings_patch.stop)

        denied = self.client.post(
            "/api/bot/heartbeat", json={"latency_ms": 5, "commands": []}
        )
        accepted = self.client.post(
            "/api/bot/heartbeat",
            json={"latency_ms": 5, "commands": []},
            headers={"Authorization": f"Bearer {'b' * 40}"},
        )
        forbidden = self.client.get(
            "/api/backend/logs",
            headers={"Authorization": f"Bearer {'b' * 40}"},
        )

        self.assertEqual(denied.status_code, 401)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(forbidden.status_code, 403)


if __name__ == "__main__":
    unittest.main()
