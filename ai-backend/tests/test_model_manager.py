import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import model_manager
from model_manager import ModelSwitchError, switch_model


def make_model(model_id, loaded):
    return {
        "id": model_id,
        "name": model_id,
        "filename": model_id,
        "format": "GGUF",
        "size_bytes": 1,
        "size_gib": 0,
        "status": "loaded" if loaded else "installed",
        "loaded": loaded,
    }


class ModelSwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.model_directory = Path(self.temp_directory.name) / "models"
        self.model_directory.mkdir()
        self.previous_id = "previous.gguf"
        self.target_id = "target.gguf"
        (self.model_directory / self.previous_id).touch()
        (self.model_directory / self.target_id).touch()
        self.executable = Path(self.temp_directory.name) / "llama-server"
        self.executable.touch()
        self.inventory = {
            "models": [make_model(self.previous_id, True), make_model(self.target_id, False)],
            "active_model": self.previous_id,
            "runtime_status": "online",
            "runtime_error": None,
            "model_directory": str(self.model_directory),
        }

    def tearDown(self):
        self.temp_directory.cleanup()

    def _switch_patches(self, start_server, server_process=None):
        return (
            patch.object(model_manager, "list_models", return_value=self.inventory),
            patch.object(model_manager, "_get_model_directory", return_value=self.model_directory),
            patch.object(model_manager, "_server_address", return_value=("127.0.0.1", 8080)),
            patch.object(model_manager, "_get_server_executable", return_value=self.executable),
            patch.object(model_manager, "_find_server_process", return_value=server_process),
            patch.object(model_manager, "_start_server", side_effect=start_server),
        )

    def test_switch_starts_requested_installed_model(self):
        self.inventory["active_model"] = None
        self.inventory["runtime_status"] = "offline"
        patches = self._switch_patches(None)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5] as start_server:
            result = switch_model(self.target_id)

        self.assertEqual(
            result,
            {"success": True, "active_model": self.target_id, "restarted": True},
        )
        start_server.assert_called_once_with(
            self.executable,
            (self.model_directory / self.target_id).resolve(),
            "127.0.0.1",
            8080,
        )

    def test_unknown_model_is_rejected_without_starting_server(self):
        patches = self._switch_patches(None)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5] as start_server:
            with self.assertRaises(FileNotFoundError):
                switch_model("not-installed.gguf")

        start_server.assert_not_called()

    def test_failed_switch_attempts_to_restore_previous_model(self):
        process = MagicMock()
        patches = self._switch_patches([ModelSwitchError("target failed"), None], process)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5] as start_server,
            patch.object(model_manager, "_validate_server_process"),
            patch.object(model_manager, "_stop_server_process"),
        ):
            with self.assertRaisesRegex(ModelSwitchError, "restored the previously loaded model"):
                switch_model(self.target_id)

        self.assertEqual(start_server.call_count, 2)
        self.assertEqual(
            start_server.call_args_list[1].args[1],
            (self.model_directory / self.previous_id).resolve(),
        )

    def test_already_active_model_does_not_restart_server(self):
        self.inventory["active_model"] = self.target_id
        patches = self._switch_patches(None)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5] as start_server:
            result = switch_model(self.target_id)

        self.assertEqual(
            result,
            {"success": True, "active_model": self.target_id, "restarted": False},
        )
        start_server.assert_not_called()

    def test_qwen3_uses_compatible_chat_template(self):
        command = model_manager._server_command(
            self.executable,
            self.model_directory / "Qwen3-8B-Q4_K_M.gguf",
            "127.0.0.1",
            8080,
        )

        self.assertEqual(command[-3:], ["--no-jinja", "--chat-template", "chatml"])

    def test_refuses_to_stop_unrecognized_process(self):
        process = MagicMock()
        process.exe.return_value = str(Path(self.temp_directory.name) / "other-server")
        process.cmdline.return_value = []

        with self.assertRaisesRegex(ModelSwitchError, "not the configured llama-server"):
            model_manager._validate_server_process(
                process,
                self.executable,
                self.model_directory / self.previous_id,
                "127.0.0.1",
                8080,
            )


if __name__ == "__main__":
    unittest.main()
