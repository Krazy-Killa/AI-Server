import unittest
from dataclasses import replace
from unittest.mock import patch

from auth_test_helpers import TEST_ORIGIN, authenticated_client


class DiagnosticKnowledgeApiTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        cors_patch = patch.object(
            main,
            "settings",
            replace(main.settings, cors_origins=(TEST_ORIGIN,)),
        )
        cors_patch.start()
        self.addCleanup(cors_patch.stop)
        self.client, self.auth_store = authenticated_client(self, main)

    def test_viewers_can_list_search_and_retrieve_reviewed_runbooks(self):
        listing = self.client.get(
            "/api/diagnostics/runbooks",
            params={"platform": "proxmox-ve"},
        )
        search = self.client.get(
            "/api/diagnostics/knowledge/search",
            params={"query": "inventory 403", "platform": "proxmox-ve"},
        )
        runbook = self.client.get(
            "/api/diagnostics/runbooks/RB-PVE-INVENTORY-002"
        )

        self.assertEqual(listing.status_code, 200)
        self.assertTrue(listing.json()["runbooks"])
        self.assertTrue(
            all(
                item["review_state"] == "reviewed"
                for item in listing.json()["runbooks"]
            )
        )
        self.assertEqual(search.status_code, 200)
        self.assertEqual(
            search.json()["results"][0]["id"],
            "RB-PVE-INVENTORY-002",
        )
        self.assertEqual(runbook.status_code, 200)
        self.assertEqual(runbook.json()["review_state"], "reviewed")

        self.auth_store.create_local_user("knowledge-viewer", "ViewerPassword42!", "viewer")
        from fastapi.testclient import TestClient

        viewer = TestClient(self.main.app)
        login = viewer.post(
            "/api/auth/login",
            json={
                "provider": "local",
                "username": "knowledge-viewer",
                "password": "ViewerPassword42!",
            },
            headers={"origin": TEST_ORIGIN},
        )
        self.assertEqual(login.status_code, 200)
        viewer.cookies.update(login.cookies)
        self.assertEqual(
            viewer.get("/api/diagnostics/runbooks").status_code,
            200,
        )

    def test_search_and_runbook_reads_do_not_run_diagnostics(self):
        with patch.object(
            self.main.diagnostics_monitor,
            "run_observation",
        ) as run_observation:
            response = self.client.get(
                "/api/diagnostics/knowledge/search",
                params={"query": "Proxmox API"},
            )

        self.assertEqual(response.status_code, 200)
        run_observation.assert_not_called()

    def test_invalid_search_filters_and_unknown_runbooks_are_rejected(self):
        unknown = self.client.get(
            "/api/diagnostics/runbooks/RB-UNKNOWN-999"
        )
        invalid_platform = self.client.get(
            "/api/diagnostics/runbooks",
            params={"platform": "windows"},
        )
        empty_query = self.client.get(
            "/api/diagnostics/knowledge/search",
            params={"query": ""},
        )

        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(invalid_platform.status_code, 422)
        self.assertEqual(empty_query.status_code, 422)

    def test_runbook_routes_require_authenticated_viewer(self):
        self.client.cookies.clear()
        self.assertEqual(
            self.client.get("/api/diagnostics/runbooks").status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                "/api/diagnostics/runbooks/RB-PVE-INVENTORY-001"
            ).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
