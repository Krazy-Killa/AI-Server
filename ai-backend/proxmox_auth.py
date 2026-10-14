"""Proxmox VE ticket-authentication groundwork.

This client validates credentials against the Proxmox API but does not create
or persist AI Server application sessions.
"""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass, field
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener


class ProxmoxAuthenticationError(Exception):
    """Credentials were rejected by Proxmox."""


class ProxmoxServiceError(Exception):
    """The Proxmox authentication service could not be used safely."""


@dataclass(frozen=True)
class ProxmoxTicket:
    """Proxmox-issued credentials; keep server-side and out of logs."""

    username: str
    ticket: str = field(repr=False)
    csrf_prevention_token: str = field(repr=False)


class ProxmoxAuthenticator(Protocol):
    """Credential-verification boundary for a future login endpoint."""

    def authenticate(self, username: str, password: str) -> ProxmoxTicket: ...


class ApplicationAuthorizationPolicy(Protocol):
    """Map a verified Proxmox identity to AI Server capabilities."""

    def capabilities_for(self, proxmox_username: str) -> frozenset[str]: ...


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None


def create_proxmox_ssl_context(
    ca_bundle: str | None = None,
    *,
    allow_missing_ca_key_usage: bool = False,
) -> ssl.SSLContext:
    """Create a verifying context with optional lab compatibility for PVE CA profiles."""
    try:
        context = ssl.create_default_context(cafile=ca_bundle)
    except (OSError, ssl.SSLError) as error:
        raise ValueError("Proxmox API CA bundle could not be loaded.") from error
    if allow_missing_ca_key_usage:
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


class ProxmoxTicketClient:
    """Validate a Proxmox user through its HTTPS ticket endpoint."""

    def __init__(
        self,
        api_base_url: str,
        timeout_seconds: float = 5.0,
        ca_bundle: str | None = None,
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
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")

        self._api_base_url = f"https://{parsed.netloc}"
        self._timeout_seconds = timeout_seconds
        self._ssl_context = create_proxmox_ssl_context(
            ca_bundle,
            allow_missing_ca_key_usage=allow_missing_ca_key_usage,
        )

    def authenticate(self, username: str, password: str) -> ProxmoxTicket:
        """Validate credentials and return a server-side-only Proxmox ticket."""
        normalized_username = username.strip()
        if not normalized_username or not password:
            raise ProxmoxAuthenticationError("Invalid Proxmox credentials.")

        request = Request(
            f"{self._api_base_url}/api2/json/access/ticket",
            data=urlencode(
                {"username": normalized_username, "password": password}
            ).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        opener = build_opener(
            _RejectRedirects(),
            HTTPSHandler(context=self._ssl_context),
        )
        try:
            with opener.open(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read(1_048_577)
        except HTTPError as error:
            if error.code in (401, 403):
                raise ProxmoxAuthenticationError(
                    "Invalid Proxmox credentials."
                ) from None
            raise ProxmoxServiceError(
                f"Proxmox authentication service returned HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ProxmoxServiceError(
                "Could not reach the Proxmox authentication service."
            ) from None

        if len(raw_body) > 1_048_576:
            raise ProxmoxServiceError(
                "Proxmox authentication response exceeded the size limit."
            )
        try:
            payload = json.loads(raw_body)
            data = payload["data"]
            canonical_username = data["username"]
            ticket = data["ticket"]
            csrf_token = data["CSRFPreventionToken"]
        except (json.JSONDecodeError, KeyError, TypeError):
            raise ProxmoxServiceError(
                "Proxmox authentication response was invalid."
            ) from None

        if not all(
            isinstance(value, str) and value
            for value in (canonical_username, ticket, csrf_token)
        ):
            raise ProxmoxServiceError(
                "Proxmox authentication response was incomplete."
            )

        return ProxmoxTicket(
            username=canonical_username,
            ticket=ticket,
            csrf_prevention_token=csrf_token,
        )
