"""Configuration shared by the opt-in Windows LAN test servers."""

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
PRIVATE_LAN_NETWORKS = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)


class LanTestConfigError(ValueError):
    """LAN test server configuration is missing or unsafe."""


@dataclass(frozen=True)
class LanTestConfig:
    host: str
    certificate: Path
    private_key: Path

    @property
    def dashboard_origin(self) -> str:
        return f"https://{self.host}:8001"


def load_lan_test_config() -> LanTestConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    host = os.environ.get("AI_SERVER_LAN_HOST", "").strip()
    certificate_value = os.environ.get("AI_SERVER_LAN_TLS_CERT", "").strip()
    private_key_value = os.environ.get("AI_SERVER_LAN_TLS_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("AI_SERVER_LAN_HOST", host),
            ("AI_SERVER_LAN_TLS_CERT", certificate_value),
            ("AI_SERVER_LAN_TLS_KEY", private_key_value),
        )
        if not value
    ]
    if missing:
        raise LanTestConfigError(
            "Set these .env values before starting LAN test mode: "
            + ", ".join(missing)
        )

    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise LanTestConfigError(
            "AI_SERVER_LAN_HOST must be a private IPv4 address for this LAN test."
        ) from error
    if address.version != 4 or not any(
        address in network for network in PRIVATE_LAN_NETWORKS
    ):
        raise LanTestConfigError(
            "AI_SERVER_LAN_HOST must be a private, non-loopback IPv4 address."
        )

    origin = f"https://{address}:8001"
    configured_origins = {
        value.strip().rstrip("/")
        for value in os.environ.get("AI_SERVER_CORS_ORIGINS", "").split(",")
        if value.strip()
    }
    if origin not in configured_origins:
        raise LanTestConfigError(
            f"Add {origin} to AI_SERVER_CORS_ORIGINS before starting LAN test mode."
        )
    if os.environ.get("AI_SERVER_AUTH_COOKIE_SECURE", "true").strip().lower() not in {
        "true",
        "1",
        "yes",
        "on",
    }:
        raise LanTestConfigError(
            "AI_SERVER_AUTH_COOKIE_SECURE must be true for LAN test mode."
        )

    certificate = Path(os.path.expandvars(certificate_value)).expanduser()
    private_key = Path(os.path.expandvars(private_key_value)).expanduser()
    if not certificate.is_absolute():
        certificate = PROJECT_ROOT / certificate
    if not private_key.is_absolute():
        private_key = PROJECT_ROOT / private_key
    if not certificate.is_file():
        raise LanTestConfigError(
            f"TLS certificate file does not exist: {certificate}"
        )
    if not private_key.is_file():
        raise LanTestConfigError(f"TLS private key file does not exist: {private_key}")

    return LanTestConfig(
        host=str(address),
        certificate=certificate.resolve(),
        private_key=private_key.resolve(),
    )
