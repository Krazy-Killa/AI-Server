import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DotenvLocationTests(unittest.TestCase):
    def test_runtime_loads_dotenv_from_the_project_root(self):
        from api import runtime

        self.assertEqual(runtime.PROJECT_ROOT, REPOSITORY_ROOT)
        self.assertTrue((runtime.PROJECT_ROOT / ".env.example").is_file())

    def test_loader_in_the_api_package_uses_the_project_root_env_file(self):
        source = (
            REPOSITORY_ROOT / "ai-backend" / "api" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn('load_dotenv(PROJECT_ROOT / ".env")', source)

    def test_project_root_env_values_reach_the_environment(self):
        from dotenv import load_dotenv

        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("AI_SERVER_DOTENV_PROBE=loaded\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("AI_SERVER_DOTENV_PROBE", None)
                load_dotenv(env_file)
                self.assertEqual(os.environ["AI_SERVER_DOTENV_PROBE"], "loaded")
                os.environ.pop("AI_SERVER_DOTENV_PROBE", None)


if __name__ == "__main__":
    unittest.main()
