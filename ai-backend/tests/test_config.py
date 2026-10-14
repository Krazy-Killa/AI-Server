import os
import unittest
from pathlib import Path
from unittest.mock import patch

from config import ConfigError, load_settings


CONFIG_VARIABLES = (
    "LLAMA_CPP_BASE_URL",
    "LLAMA_CPP_TIMEOUT_SECONDS",
    "LLAMA_CPP_DEVICE",
    "LLAMA_CPP_GPU_LAYERS",
    "LLAMA_CPP_CTX_SIZE",
    "AI_SERVER_MAX_TOKENS",
    "SEARXNG_BASE_URL",
    "AI_SERVER_CORS_ORIGINS",
    "AI_SERVER_LOG_LEVEL",
    "AI_SERVER_LOG_DIR",
    "AI_SERVER_LOG_MAX_BYTES",
    "AI_SERVER_LOG_BACKUP_COUNT",
    "AI_SERVER_MAX_CHAT_CHARS",
    "AI_SERVER_AUTH_DB_PATH",
    "AI_SERVER_MEMORY_DB_PATH",
    "AI_SERVER_AUTH_COOKIE_SECURE",
    "PROXMOX_API_URL",
    "AI_SERVER_BOT_API_TOKEN",
)


class LoadSettingsTests(unittest.TestCase):
    def load(self, **env):
        clean_environment = {k: v for k, v in os.environ.items() if k not in CONFIG_VARIABLES}
        with patch.dict(os.environ, {**clean_environment, **env}, clear=True):
            return load_settings()

    def test_defaults(self):
        settings = self.load()
        self.assertEqual(settings.llama_cpp_base_url, "http://127.0.0.1:8080")
        self.assertEqual(settings.llm_max_tokens, 256)
        self.assertEqual(settings.log_level, "INFO")
        self.assertIn("http://127.0.0.1:8001", settings.cors_origins)
        self.assertTrue(settings.auth_cookie_secure)
        self.assertEqual(settings.proxmox_api_url, "")
        self.assertEqual(settings.bot_api_token, "")
        self.assertEqual(
            settings.memory_database_path,
            settings.auth_database_path.parent / "memory.sqlite3",
        )

    def test_blank_values_use_defaults(self):
        settings = self.load(LLAMA_CPP_CTX_SIZE="  ", AI_SERVER_LOG_DIR="")
        self.assertEqual(settings.llama_cpp_ctx_size, 4096)

    def test_overrides_and_normalization(self):
        settings = self.load(
            LLAMA_CPP_BASE_URL="http://127.0.0.1:9000/",
            AI_SERVER_LOG_LEVEL="debug",
            AI_SERVER_LOG_DIR="logs-here",
            AI_SERVER_CORS_ORIGINS="http://a.test:1/, http://b.test",
        )
        self.assertEqual(settings.llama_cpp_base_url, "http://127.0.0.1:9000")
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.log_directory, Path("logs-here"))
        self.assertEqual(settings.cors_origins, ("http://a.test:1", "http://b.test"))

    def test_rejects_non_numeric_and_non_positive_numbers(self):
        with self.assertRaisesRegex(ConfigError, "LLAMA_CPP_GPU_LAYERS"):
            self.load(LLAMA_CPP_GPU_LAYERS="many")
        with self.assertRaisesRegex(ConfigError, "AI_SERVER_MAX_TOKENS"):
            self.load(AI_SERVER_MAX_TOKENS="0")

    def test_rejects_invalid_log_level(self):
        with self.assertRaisesRegex(ConfigError, "AI_SERVER_LOG_LEVEL"):
            self.load(AI_SERVER_LOG_LEVEL="LOUD")

    def test_rejects_wildcard_cors_origin(self):
        with self.assertRaisesRegex(ConfigError, "AI_SERVER_CORS_ORIGINS"):
            self.load(AI_SERVER_CORS_ORIGINS="*")

    def test_loads_authentication_settings(self):
        settings = self.load(
            AI_SERVER_AUTH_DB_PATH="auth-test.sqlite3",
            AI_SERVER_MEMORY_DB_PATH="memory-test.sqlite3",
            AI_SERVER_AUTH_COOKIE_SECURE="false",
            PROXMOX_API_URL="https://pve.example:8006/",
            AI_SERVER_BOT_API_TOKEN="x" * 40,
        )
        self.assertEqual(settings.auth_database_path, Path("auth-test.sqlite3"))
        self.assertEqual(settings.memory_database_path, Path("memory-test.sqlite3"))
        self.assertFalse(settings.auth_cookie_secure)
        self.assertEqual(settings.proxmox_api_url, "https://pve.example:8006")
        self.assertEqual(settings.bot_api_token, "x" * 40)

    def test_rejects_unsafe_proxmox_urls_and_short_bot_tokens(self):
        with self.assertRaisesRegex(ConfigError, "PROXMOX_API_URL"):
            self.load(PROXMOX_API_URL="http://pve.example:8006")
        with self.assertRaisesRegex(ConfigError, "AI_SERVER_BOT_API_TOKEN"):
            self.load(AI_SERVER_BOT_API_TOKEN="too-short")
        with self.assertRaisesRegex(ConfigError, "AI_SERVER_AUTH_COOKIE_SECURE"):
            self.load(AI_SERVER_AUTH_COOKIE_SECURE="sometimes")


if __name__ == "__main__":
    unittest.main()
