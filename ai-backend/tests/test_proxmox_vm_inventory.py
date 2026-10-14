import json
import ssl
import unittest
from email.message import Message
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from proxmox_vm_inventory import (
    ProxmoxInventoryError,
    ProxmoxVMInventoryClient,
)


def response(payload):
    result = MagicMock()
    result.read.return_value = json.dumps(payload).encode("utf-8")
    result.__enter__.return_value = result
    return result


class ProxmoxVMInventoryClientTests(unittest.TestCase):
    def setUp(self):
        self.client = ProxmoxVMInventoryClient(
            "https://pve.example:8006/",
            "ai-inventory@pve!dashboard",
            "secret-value",
        )

    def test_fetches_only_filtered_inventory_with_api_token(self):
        opener = MagicMock()
        opener.open.return_value = response(
            {
                "data": [
                    {
                        "vmid": 101,
                        "name": "ai-server",
                        "node": "pve",
                        "type": "qemu",
                        "status": "running",
                        "maxcpu": 4,
                    },
                    {
                        "vmid": 102,
                        "node": "pve",
                        "type": "lxc",
                        "status": "stopped",
                        "template": True,
                    },
                ]
            }
        )
        with patch("proxmox_vm_inventory.build_opener", return_value=opener):
            guests = self.client.list_guests()

        request = opener.open.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://pve.example:8006/api2/json/cluster/resources?type=vm",
        )
        self.assertEqual(request.method, "GET")
        self.assertEqual(
            request.get_header("Authorization"),
            "PVEAPIToken=ai-inventory@pve!dashboard=secret-value",
        )
        self.assertEqual(
            guests,
            [
                {
                    "name": "ai-server",
                    "vmid": 101,
                    "node": "pve",
                    "type": "QEMU VM",
                    "status": "running",
                },
                {
                    "name": "Guest 102",
                    "vmid": 102,
                    "node": "pve",
                    "type": "LXC template",
                    "status": "stopped",
                },
            ],
        )

    def test_rejects_http_urls_and_malformed_tokens(self):
        for args in (
            ("http://pve.example:8006", "user@pve!token", "secret"),
            ("https://pve.example:8006", "user@pve!token=extra", "secret"),
            ("https://pve.example:8006", "user@pve!token", "secret\nvalue"),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                ProxmoxVMInventoryClient(*args)

    def test_lab_compatibility_relaxes_only_x509_strict_verification_flag(self):
        strict_flag = ssl.VERIFY_X509_STRICT
        other_flags = ssl.VERIFY_X509_TRUSTED_FIRST
        context = ssl.create_default_context()
        context.verify_flags = strict_flag | other_flags
        with patch(
            "proxmox_auth.ssl.create_default_context",
            return_value=context,
        ):
            ProxmoxVMInventoryClient(
                "https://pve.example:8006",
                "user@pve!inventory",
                "secret-value",
                ca_bundle="root-ca.pem",
                allow_missing_ca_key_usage=True,
            )
        self.assertEqual(context.verify_flags, other_flags)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_reports_transport_and_http_errors_without_response_body(self):
        cases = (
            URLError("sensitive transport detail"),
            HTTPError(
                "https://pve.example:8006/api2/json/cluster/resources?type=vm",
                403,
                "Forbidden",
                Message(),
                BytesIO(b"response body must not leak"),
            ),
        )
        for error in cases:
            opener = MagicMock()
            opener.open.side_effect = error
            with (
                self.subTest(error=error),
                patch("proxmox_vm_inventory.build_opener", return_value=opener),
                self.assertRaises(ProxmoxInventoryError) as raised,
            ):
                self.client.list_guests()
            self.assertNotIn("sensitive", str(raised.exception))
            self.assertNotIn("must not leak", str(raised.exception))

    def test_rejects_malformed_or_oversized_inventory(self):
        for payload in (
            {"data": "not a list"},
            {"data": [{"vmid": True, "name": "bad", "node": "pve",
                       "type": "qemu", "status": "running"}]},
            {"data": [{"vmid": 1, "name": "bad", "node": "pve",
                       "type": "unknown", "status": "running"}]},
        ):
            opener = MagicMock()
            opener.open.return_value = response(payload)
            with (
                self.subTest(payload=payload),
                patch("proxmox_vm_inventory.build_opener", return_value=opener),
                self.assertRaises(ProxmoxInventoryError),
            ):
                self.client.list_guests()

        opener = MagicMock()
        oversized = MagicMock()
        oversized.read.return_value = b"x" * (2 * 1024 * 1024 + 1)
        oversized.__enter__.return_value = oversized
        opener.open.return_value = oversized
        with (
            patch("proxmox_vm_inventory.build_opener", return_value=opener),
            self.assertRaisesRegex(ProxmoxInventoryError, "size limit"),
        ):
            self.client.list_guests()


if __name__ == "__main__":
    unittest.main()
