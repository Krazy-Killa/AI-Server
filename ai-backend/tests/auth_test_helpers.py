import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from auth import AuthStore
from fastapi.testclient import TestClient

TEST_ORIGIN = "http://127.0.0.1:8001"
TEST_USERNAME = "test-admin"
TEST_PASSWORD = "CorrectHorseBatteryStaple42!"


def authenticated_client(test_case, main):
    directory = tempfile.TemporaryDirectory(prefix="ai-server-auth-test-")
    test_case.addCleanup(directory.cleanup)
    store = AuthStore(Path(directory.name) / "auth.sqlite3")
    store.create_local_user(TEST_USERNAME, TEST_PASSWORD, "admin")
    settings_patch = patch.object(main.runtime,
        "settings",
        replace(
            main.runtime.settings,
            auth_database_path=Path(directory.name) / "auth.sqlite3",
            auth_cookie_secure=False,
        ),
    )
    store_patch = patch.object(main.runtime, "auth_store", store)
    settings_patch.start()
    store_patch.start()
    test_case.addCleanup(store_patch.stop)
    test_case.addCleanup(settings_patch.stop)
    client = TestClient(main.app)
    login = client.post(
        "/api/auth/login",
        json={
            "provider": "local",
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        },
        headers={"origin": TEST_ORIGIN},
    )
    if login.status_code != 200:
        raise AssertionError(f"Test admin login failed: {login.status_code} {login.text}")
    client.headers.update(
        {"origin": TEST_ORIGIN, "x-csrf-token": login.json()["csrf_token"]}
    )
    return client, store
