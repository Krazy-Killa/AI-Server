"""Validated backend settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
    )


settings = load_settings()
