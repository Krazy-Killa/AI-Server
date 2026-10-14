import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from auth_test_helpers import TEST_ORIGIN, authenticated_client


class ProxmoxVMInventoryApiTests(unittest.TestCase):
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

    def test_reports_unconfigured_provider_explicitly(self):
        with patch.object(self.main, "proxmox_inventory_client", None):
            response = self.client.get("/api/proxmox/vms")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "configured": False,
                "status": "not_configured",
                "guests": [],
                "count": 0,
                "observed_at": None,
            },
        )

    def test_returns_live_inventory_shape_for_authenticated_viewers(self):
        guests = [
            {
                "name": "lab-vm",
                "vmid": 100,
                "node": "pve",
                "type": "QEMU VM",
                "status": "running",
            }
        ]
        with patch.object(
            self.main,
            "proxmox_inventory_client",
            SimpleNamespace(list_guests=lambda: guests),
        ):
            response = self.client.get("/api/proxmox/vms")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "connected")
        self.assertTrue(response.json()["configured"])
        self.assertEqual(response.json()["guests"], guests)
        self.assertEqual(response.json()["count"], 1)
        self.assertIsNotNone(response.json()["observed_at"])

        self.auth_store.create_local_user("test-viewer", "ViewerPassword42!", "viewer")
        viewer = self.client.__class__(self.main.app)
        login = viewer.post(
            "/api/auth/login",
            json={
                "provider": "local",
                "username": "test-viewer",
                "password": "ViewerPassword42!",
            },
            headers={"origin": TEST_ORIGIN},
        )
        viewer.cookies.update(login.cookies)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(viewer.get("/api/proxmox/vms").status_code, 200)

    def test_reports_upstream_failure_as_unavailable(self):
        from proxmox_vm_inventory import ProxmoxInventoryError

        def fail():
            raise ProxmoxInventoryError("Proxmox API inventory request returned HTTP 403.")

        with patch.object(
            self.main,
            "proxmox_inventory_client",
            SimpleNamespace(list_guests=fail),
        ):
            response = self.client.get("/api/proxmox/vms")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"], "Proxmox VM inventory is unavailable."
        )

    def test_requires_authenticated_viewer_role(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/proxmox/vms").status_code, 401)


if __name__ == "__main__":
    unittest.main()
