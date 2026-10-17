"""Read-only Proxmox VE guest inventory client."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

from proxmox_auth import create_proxmox_ssl_context
from proxmox_contracts import PROXMOX_INVENTORY_CONTRACT


MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ProxmoxInventoryError(Exception):
    """The Proxmox inventory could not be retrieved or validated safely."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None


class ProxmoxVMInventoryClient:
    """Fetch a filtered VM/container inventory with a dedicated API token."""

    def __init__(
        self,
        api_base_url: str,
        token_id: str,
        token_secret: str,
        ca_bundle: str | None = None,
        timeout_seconds: float = 5.0,
        allow_missing_ca_key_usage: bool = False,
    ) -> None:
        parsed = urlsplit(api_base_url.strip())
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Proxmox API base URL must be an HTTPS origin.")
        if not token_id or any(char in token_id for char in "\r\n="):
            raise ValueError("Proxmox API token ID is invalid.")
        if not token_secret or any(char in token_secret for char in "\r\n"):
            raise ValueError("Proxmox API token secret is invalid.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")

        self._api_base_url = f"https://{parsed.netloc}"
        self._authorization = f"PVEAPIToken={token_id}={token_secret}"
        self._timeout_seconds = timeout_seconds
        self._ssl_context = create_proxmox_ssl_context(
            ca_bundle,
            allow_missing_ca_key_usage=allow_missing_ca_key_usage,
        )

    def list_guests(self) -> list[dict[str, Any]]:
        """Return only inventory fields needed by the read-only dashboard."""
        request = Request(
            f"{self._api_base_url}{PROXMOX_INVENTORY_CONTRACT.path}",
            headers={
                "Accept": "application/json",
                "Authorization": self._authorization,
            },
            method="GET",
        )
        opener = build_opener(
            _RejectRedirects(),
            HTTPSHandler(context=self._ssl_context),
        )
        try:
            with opener.open(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            raise ProxmoxInventoryError(
                f"Proxmox API inventory request returned HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ProxmoxInventoryError(
                "Could not reach the Proxmox API inventory endpoint."
            ) from None

        if len(raw_body) > MAX_RESPONSE_BYTES:
            raise ProxmoxInventoryError(
                "Proxmox API inventory response exceeded the size limit."
            )
        try:
            payload = json.loads(raw_body)
            rows = payload["data"]
        except (json.JSONDecodeError, KeyError, TypeError):
            raise ProxmoxInventoryError(
                "Proxmox API inventory response was invalid."
            ) from None
        if not isinstance(rows, list):
            raise ProxmoxInventoryError(
                "Proxmox API inventory response was invalid."
            )
        return [self._guest_from_row(row) for row in rows]

    @staticmethod
    def _guest_from_row(row: Any) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise ProxmoxInventoryError(
                "Proxmox API inventory contained an invalid guest record."
            )

        vmid = row.get("vmid")
        node = row.get("node")
        guest_type = row.get("type")
        status = row.get("status")
        name = row.get("name")
        if (
            isinstance(vmid, bool)
            or not isinstance(vmid, int)
            or vmid < 1
            or not isinstance(node, str)
            or not node
            or len(node) > 128
            or guest_type not in ("qemu", "lxc")
            or not isinstance(status, str)
            or not status
            or len(status) > 32
            or (name is not None and (not isinstance(name, str) or len(name) > 256))
        ):
            raise ProxmoxInventoryError(
                "Proxmox API inventory contained an invalid guest record."
            )

        if name is None or not name.strip():
            name = f"Guest {vmid}"
        if row.get("template") is True:
            display_type = "QEMU template" if guest_type == "qemu" else "LXC template"
        else:
            display_type = "QEMU VM" if guest_type == "qemu" else "LXC container"

        return {
            "name": name,
            "vmid": vmid,
            "node": node,
            "type": display_type,
            "status": status,
        }
