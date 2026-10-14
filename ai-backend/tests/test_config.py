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


if __name__ == "__main__":
    unittest.main()
