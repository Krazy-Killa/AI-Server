import json
import unittest
from email.message import Message
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

from proxmox_auth import (
    ProxmoxAuthenticationError,
    ProxmoxServiceError,
    ProxmoxTicketClient,
)


def response(payload):
    result = MagicMock()
    result.read.return_value = json.dumps(payload).encode("utf-8")
    result.__enter__.return_value = result
    return result


class ProxmoxTicketClientTests(unittest.TestCase):
    def test_posts_credentials_to_ticket_endpoint_and_returns_server_identity(self):
        opener = MagicMock()
        opener.open.return_value = response(
            {
                "data": {
                    "username": "dashboard@pve",
                    "ticket": "secret-ticket",
                    "CSRFPreventionToken": "secret-csrf",
                }
            }
        )
        with patch("proxmox_auth.build_opener", return_value=opener):
            ticket = ProxmoxTicketClient("https://pve.example:8006/").authenticate(
                " dashboard@pve ", "test-password"
            )

        request = opener.open.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://pve.example:8006/api2/json/access/ticket",
        )
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            parse_qs(request.data.decode("utf-8")),
            {"username": ["dashboard@pve"], "password": ["test-password"]},
        )
        self.assertEqual(ticket.username, "dashboard@pve")
        self.assertEqual(ticket.ticket, "secret-ticket")
        self.assertEqual(ticket.csrf_prevention_token, "secret-csrf")
        self.assertNotIn("secret-ticket", repr(ticket))
        self.assertNotIn("secret-csrf", repr(ticket))

    def test_rejects_non_https_or_non_origin_api_urls(self):
        for url in (
            "http://pve.example:8006",
            "https://user:pass@pve.example:8006",
            "https://pve.example:8006/api2",
            "https://pve.example:8006?debug=1",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                ProxmoxTicketClient(url)

    def test_rejects_empty_credentials_without_network_request(self):
        with patch("proxmox_auth.build_opener") as build_opener:
            with self.assertRaises(ProxmoxAuthenticationError):
                ProxmoxTicketClient("https://pve.example:8006").authenticate(
                    "  ", "password"
                )
            with self.assertRaises(ProxmoxAuthenticationError):
                ProxmoxTicketClient("https://pve.example:8006").authenticate(
                    "user@pve", ""
                )
        build_opener.assert_not_called()

    def test_rejects_invalid_credentials_with_generic_error(self):
        opener = MagicMock()
        opener.open.side_effect = HTTPError(
            "https://pve.example:8006/api2/json/access/ticket",
            401,
            "Unauthorized",
            Message(),
            BytesIO(b"password must not leak"),
        )
        with patch("proxmox_auth.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                ProxmoxAuthenticationError, "^Invalid Proxmox credentials\\.$"
            ):
                ProxmoxTicketClient("https://pve.example:8006").authenticate(
                    "user@pve", "password"
                )

    def test_reports_service_errors_without_exposing_transport_details(self):
        opener = MagicMock()
        opener.open.side_effect = URLError("private host details")
        with patch("proxmox_auth.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                ProxmoxServiceError,
                "^Could not reach the Proxmox authentication service\\.$",
            ):
                ProxmoxTicketClient("https://pve.example:8006").authenticate(
                    "user@pve", "password"
                )

    def test_does_not_follow_redirects(self):
        opener = MagicMock()
        headers = Message()
        headers["Location"] = "https://other.example/"
        opener.open.side_effect = HTTPError(
            "https://pve.example:8006/api2/json/access/ticket",
            302,
            "Found",
            headers,
            BytesIO(),
        )
        with patch("proxmox_auth.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                ProxmoxServiceError,
                "returned HTTP 302",
            ):
                ProxmoxTicketClient("https://pve.example:8006").authenticate(
                    "user@pve", "password"
                )

    def test_rejects_malformed_or_incomplete_proxmox_responses(self):
        for payload in (
            {"data": {"username": "user@pve"}},
            {"data": {"username": 42, "ticket": "ticket", "CSRFPreventionToken": "csrf"}},
        ):
            opener = MagicMock()
            opener.open.return_value = response(payload)
            with patch("proxmox_auth.build_opener", return_value=opener):
                with self.subTest(payload=payload), self.assertRaises(ProxmoxServiceError):
                    ProxmoxTicketClient("https://pve.example:8006").authenticate(
                        "user@pve", "password"
                    )


if __name__ == "__main__":
    unittest.main()
