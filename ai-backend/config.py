"""Validated backend settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_CORS_ORIGINS = ("http://127.0.0.1:8001", "http://localhost:8001")
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class ConfigError(ValueError):
    """Raised when an environment setting is invalid."""


def _text(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}.") from error
    if value < 1:
        raise ConfigError(f"{name} must be at least 1, got {value}.")
    return value


def _default_log_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AI-Server" / "logs"
    return Path.home() / "AI-Server" / "logs"


def _default_auth_database() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AI-Server" / "data" / "auth.sqlite3"
    return Path.home() / "AI-Server" / "data" / "auth.sqlite3"


def _boolean(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in ("true", "1", "yes", "on"):
        return True
    if raw in ("false", "0", "no", "off"):
        return False
    raise ConfigError(f"{name} must be true or false, got {raw!r}.")


def _cors_origins() -> tuple[str, ...]:
    raw = os.environ.get("AI_SERVER_CORS_ORIGINS", "").strip()
    if not raw:
        return DEFAULT_CORS_ORIGINS
    origins = tuple(origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip())
    if "*" in origins:
        raise ConfigError("AI_SERVER_CORS_ORIGINS must list explicit origins, not '*'.")
    return origins


@dataclass(frozen=True)
class Settings:
    llama_cpp_base_url: str
    llama_cpp_timeout_seconds: int
    llama_cpp_device: str
    llama_cpp_gpu_layers: int
    llama_cpp_ctx_size: int
    llm_max_tokens: int
    searxng_base_url: str
    cors_origins: tuple[str, ...]
    log_level: str
    log_directory: Path
    log_max_bytes: int
    log_backup_count: int
    max_chat_chars: int
    auth_database_path: Path
    memory_database_path: Path
    auth_cookie_secure: bool
    proxmox_api_url: str
    proxmox_inventory_token_id: str
    proxmox_inventory_token_secret: str
    proxmox_api_ca_bundle: Path | None
    proxmox_api_allow_missing_ca_key_usage: bool
    bot_api_token: str


def load_settings() -> Settings:
    log_level = _text("AI_SERVER_LOG_LEVEL", "INFO").upper()
    if log_level not in VALID_LOG_LEVELS:
        raise ConfigError(
            f"AI_SERVER_LOG_LEVEL must be one of {', '.join(VALID_LOG_LEVELS)}, got {log_level!r}."
        )

    configured_log_directory = os.environ.get("AI_SERVER_LOG_DIR", "").strip()
    log_directory = (
        Path(configured_log_directory).expanduser()
        if configured_log_directory
        else _default_log_directory()
    )

    configured_auth_database = os.environ.get("AI_SERVER_AUTH_DB_PATH", "").strip()
    auth_database_path = (
        Path(configured_auth_database).expanduser()
        if configured_auth_database
        else _default_auth_database()
    )
    configured_memory_database = os.environ.get("AI_SERVER_MEMORY_DB_PATH", "").strip()
    memory_database_path = (
        Path(configured_memory_database).expanduser()
        if configured_memory_database
        else auth_database_path.parent / "memory.sqlite3"
    )
    proxmox_api_url = os.environ.get("PROXMOX_API_URL", "").strip().rstrip("/")
    if proxmox_api_url:
        parsed_proxmox_url = urlsplit(proxmox_api_url)
        if (
            parsed_proxmox_url.scheme.lower() != "https"
            or not parsed_proxmox_url.netloc
            or parsed_proxmox_url.username is not None
            or parsed_proxmox_url.password is not None
            or parsed_proxmox_url.path not in ("", "/")
            or parsed_proxmox_url.query
            or parsed_proxmox_url.fragment
        ):
            raise ConfigError("PROXMOX_API_URL must be an HTTPS origin.")

    proxmox_inventory_token_id = os.environ.get(
        "PROXMOX_INVENTORY_TOKEN_ID", ""
    ).strip()
    proxmox_inventory_token_secret = os.environ.get(
        "PROXMOX_INVENTORY_TOKEN_SECRET", ""
    ).strip()
    if bool(proxmox_inventory_token_id) != bool(proxmox_inventory_token_secret):
        raise ConfigError(
            "PROXMOX_INVENTORY_TOKEN_ID and PROXMOX_INVENTORY_TOKEN_SECRET "
            "must be configured together."
        )
    if proxmox_inventory_token_id and not proxmox_api_url:
        raise ConfigError(
            "PROXMOX_API_URL is required when the inventory token is configured."
        )
    if (
        any(char in proxmox_inventory_token_id for char in "\r\n=")
        or any(char in proxmox_inventory_token_secret for char in "\r\n")
    ):
        raise ConfigError("Proxmox inventory token settings contain invalid characters.")

    configured_proxmox_ca_bundle = os.environ.get(
        "PROXMOX_API_CA_BUNDLE", ""
    ).strip()
    proxmox_api_ca_bundle = (
        Path(configured_proxmox_ca_bundle).expanduser()
        if configured_proxmox_ca_bundle
        else None
    )
    if proxmox_api_ca_bundle is not None and not proxmox_api_ca_bundle.is_file():
        raise ConfigError("PROXMOX_API_CA_BUNDLE must point to a readable CA file.")
    proxmox_api_allow_missing_ca_key_usage = _boolean(
        "PROXMOX_API_ALLOW_MISSING_CA_KEY_USAGE", False
    )
    if proxmox_api_allow_missing_ca_key_usage and proxmox_api_ca_bundle is None:
        raise ConfigError(
            "PROXMOX_API_CA_BUNDLE is required when "
            "PROXMOX_API_ALLOW_MISSING_CA_KEY_USAGE is true."
        )

    bot_api_token = os.environ.get("AI_SERVER_BOT_API_TOKEN", "").strip()
    if bot_api_token and len(bot_api_token) < 32:
        raise ConfigError("AI_SERVER_BOT_API_TOKEN must contain at least 32 characters.")

    return Settings(
        llama_cpp_base_url=_text("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
        llama_cpp_timeout_seconds=_positive_int("LLAMA_CPP_TIMEOUT_SECONDS", 120),
        llama_cpp_device=_text("LLAMA_CPP_DEVICE", "Vulkan0" if os.name == "nt" else "ROCm0"),
        llama_cpp_gpu_layers=_positive_int("LLAMA_CPP_GPU_LAYERS", 99),
        llama_cpp_ctx_size=_positive_int("LLAMA_CPP_CTX_SIZE", 4096),
        llm_max_tokens=_positive_int("AI_SERVER_MAX_TOKENS", 256),
        searxng_base_url=_text("SEARXNG_BASE_URL", "http://127.0.0.1:8888").rstrip("/"),
        cors_origins=_cors_origins(),
        log_level=log_level,
        log_directory=log_directory,
        log_max_bytes=_positive_int("AI_SERVER_LOG_MAX_BYTES", 5_000_000),
        log_backup_count=_positive_int("AI_SERVER_LOG_BACKUP_COUNT", 5),
        max_chat_chars=_positive_int("AI_SERVER_MAX_CHAT_CHARS", 4000),
        auth_database_path=auth_database_path,
        memory_database_path=memory_database_path,
        auth_cookie_secure=_boolean("AI_SERVER_AUTH_COOKIE_SECURE", True),
        proxmox_api_url=proxmox_api_url,
        proxmox_inventory_token_id=proxmox_inventory_token_id,
        proxmox_inventory_token_secret=proxmox_inventory_token_secret,
        proxmox_api_ca_bundle=proxmox_api_ca_bundle,
        proxmox_api_allow_missing_ca_key_usage=proxmox_api_allow_missing_ca_key_usage,
        bot_api_token=bot_api_token,
    )


settings = load_settings()
