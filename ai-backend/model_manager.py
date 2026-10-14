"""Discover installed GGUF models and report the model loaded by llama.cpp."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

import psutil
from config import settings
from gpu.gpu_llm import LLAMA_CPP_BASE_URL

_switch_lock = threading.Lock()
_STARTUP_TIMEOUT_SECONDS = 180


class ModelInfo(TypedDict):
    id: str
    name: str
    filename: str
    format: str
    size_bytes: int
    size_gib: float
    status: str
    loaded: bool


class ModelInventory(TypedDict):
    models: list[ModelInfo]
    active_model: str | None
    runtime_status: str
    runtime_error: str | None
    model_directory: str


class ModelSwitchError(RuntimeError):
    """Raised when llama.cpp cannot be safely switched to a model."""


def _get_model_directory() -> Path:
    configured_directory = os.environ.get("AI_SERVER_MODEL_DIR")
    if configured_directory:
        return Path(configured_directory).expanduser()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AI-Server" / "models"

    return Path.home() / "AI-Server" / "models"


def _get_runtime_model() -> tuple[str | None, str, str | None]:
    try:
        with urlopen(f"{LLAMA_CPP_BASE_URL}/props", timeout=3) as response:
            runtime_info = json.load(response)
    except HTTPError as error:
        return None, "offline", f"llama.cpp returned HTTP {error.code}."
    except (URLError, TimeoutError, OSError) as error:
        return None, "offline", f"Cannot reach llama.cpp at {LLAMA_CPP_BASE_URL}: {error}"
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return None, "unknown", f"llama.cpp returned invalid model metadata: {error}"

    model_path = runtime_info.get("model_path") if isinstance(runtime_info, dict) else None
    if not isinstance(model_path, str) or not model_path:
        return None, "unknown", "llama.cpp did not report the loaded model path."

    return Path(model_path).name, "online", None


def list_models() -> ModelInventory:
    """Return installed GGUF files and identify the model currently loaded."""
    model_directory = _get_model_directory()
    loaded_filename, runtime_status, runtime_error = _get_runtime_model()
    loaded_filename_key = loaded_filename.casefold() if loaded_filename else None
    models: list[ModelInfo] = []

    if model_directory.is_dir():
        for model_path in sorted(model_directory.glob("*.gguf"), key=lambda path: path.name.casefold()):
            size_bytes = model_path.stat().st_size
            stem = model_path.stem
            display_stem = stem
            for separator in ("-q", "-iq", "-f", "-bf"):
                quantization_index = display_stem.casefold().find(separator)
                if quantization_index > 0:
                    display_stem = display_stem[:quantization_index]
                    break

            is_loaded = model_path.name.casefold() == loaded_filename_key
            models.append(
                ModelInfo(
                    id=model_path.name,
                    name=display_stem.replace("-", " ").replace("_", " ").title(),
                    filename=model_path.name,
                    format="GGUF",
                    size_bytes=size_bytes,
                    size_gib=round(size_bytes / (1024**3), 2),
                    status="loaded" if is_loaded else "installed",
                    loaded=is_loaded,
                )
            )

    active_model = next((model for model in models if model["loaded"]), None)
    return {
        "models": models,
        "active_model": active_model["id"] if active_model else None,
        "runtime_status": runtime_status,
        "runtime_error": runtime_error,
        "model_directory": str(model_directory),
    }


def get_active_model() -> ModelInfo | None:
    """Return the installed model currently loaded by llama.cpp, if any."""
    inventory = list_models()
    active_id = inventory["active_model"]
    if not isinstance(active_id, str):
        return None
    return next((model for model in inventory["models"] if model["id"] == active_id), None)


def _server_address() -> tuple[str, int]:
    parsed_url = urlsplit(LLAMA_CPP_BASE_URL)
    if parsed_url.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ModelSwitchError("Model switching is only supported for a loopback llama.cpp server.")
    if parsed_url.port is None:
        raise ModelSwitchError("LLAMA_CPP_BASE_URL must include the llama.cpp server port.")
    return parsed_url.hostname, parsed_url.port


def _get_server_executable() -> Path:
    configured_executable = os.environ.get("LLAMA_SERVER_EXECUTABLE")
    if configured_executable:
        executable = Path(configured_executable).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            executable = (
                Path(local_app_data)
                / "AI-Server"
                / "build"
                / "llama.cpp-vulkan"
                / "bin"
                / "Release"
                / "llama-server.exe"
            )
        else:
            discovered_executable = shutil.which("llama-server")
            if not discovered_executable:
                raise ModelSwitchError(
                    "llama-server was not found. Set LLAMA_SERVER_EXECUTABLE to its executable path."
                )
            executable = Path(discovered_executable)

    if not executable.is_file():
        raise ModelSwitchError(f"llama-server executable does not exist: {executable}")
    return executable.resolve()


def _find_server_process(port: int) -> psutil.Process | None:
    try:
        connections = psutil.net_connections(kind="tcp")
    except psutil.Error as error:
        raise ModelSwitchError(f"Cannot safely inspect the llama.cpp listener: {error}") from error

    listener: psutil.Process | None = None
    for connection in connections:
        if connection.status != psutil.CONN_LISTEN or not connection.laddr:
            continue
        if connection.laddr.port != port:
            continue
        if connection.laddr.ip not in {"127.0.0.1", "::1"}:
            raise ModelSwitchError(f"Port {port} is listening on a non-loopback address; refusing to stop it.")
        if connection.pid is None:
            raise ModelSwitchError(f"Cannot identify the process listening on llama.cpp port {port}.")
        if listener is not None and listener.pid != connection.pid:
            raise ModelSwitchError(f"Multiple processes are listening on llama.cpp port {port}.")
        try:
            listener = psutil.Process(connection.pid)
        except psutil.Error as error:
            raise ModelSwitchError(f"Cannot inspect the process listening on llama.cpp port {port}: {error}") from error
    return listener


def _validate_server_process(
    process: psutil.Process,
    executable: Path,
    model_path: Path,
    host: str,
    port: int,
) -> None:
    try:
        running_executable = Path(process.exe()).resolve()
        command_line = process.cmdline()
    except psutil.Error as error:
        raise ModelSwitchError(f"Cannot verify the llama.cpp process before stopping it: {error}") from error

    if os.path.normcase(str(running_executable)) != os.path.normcase(str(executable)):
        raise ModelSwitchError(
            f"Port {port} is owned by {running_executable}, not the configured llama-server executable."
        )

    for argument, expected_value in (("--host", host), ("--port", str(port))):
        if argument not in command_line:
            raise ModelSwitchError(
                "The process on the llama.cpp port does not have the expected host and port arguments."
            )
        argument_index = command_line.index(argument)
        if argument_index + 1 >= len(command_line) or command_line[argument_index + 1] != expected_value:
            raise ModelSwitchError(
                "The process on the llama.cpp port does not have the expected host and port arguments."
            )

    model_arguments = ("--model", "-m")
    argument_index = next(
        (index for index, argument in enumerate(command_line) if argument in model_arguments),
        None,
    )
    if argument_index is None or argument_index + 1 >= len(command_line):
        raise ModelSwitchError("The llama.cpp process has no verifiable model argument; refusing to stop it.")
    running_model = Path(command_line[argument_index + 1]).resolve()
    if os.path.normcase(str(running_model)) != os.path.normcase(str(model_path.resolve())):
        raise ModelSwitchError("The running llama.cpp model does not match the model reported by /props.")


def _stop_server_process(
    process: psutil.Process,
    executable: Path,
    model_path: Path,
    host: str,
    port: int,
) -> None:
    _validate_server_process(process, executable, model_path, host, port)
    try:
        process.terminate()
        process.wait(timeout=20)
    except psutil.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=10)
        except psutil.Error as error:
            raise ModelSwitchError(f"Could not terminate the verified llama.cpp process: {error}") from error
    except psutil.Error as error:
        raise ModelSwitchError(f"Could not stop the verified llama.cpp process: {error}") from error


def _server_command(executable: Path, model_path: Path, host: str, port: int) -> list[str]:
    command = [
        str(executable),
        "--model",
        str(model_path),
        "--host",
        host,
        "--port",
        str(port),
        "--device",
        settings.llama_cpp_device,
        "--gpu-layers",
        str(settings.llama_cpp_gpu_layers),
        "--ctx-size",
        str(settings.llama_cpp_ctx_size),
        "--alias",
        model_path.stem,
    ]
    if model_path.name.casefold().startswith("qwen3"):
        command.extend(["--no-jinja", "--chat-template", "chatml"])
    return command


def _start_server(executable: Path, model_path: Path, host: str, port: int) -> None:
    log_directory = _get_model_directory().parent / "logs"
    log_path = log_directory / "llama-server.log"
    environment = os.environ.copy()
    if os.name == "nt":
        vulkan_bin = Path(os.environ.get("VULKAN_SDK", r"C:\VulkanSDK\1.4.363.0")) / "Bin"
        if vulkan_bin.is_dir():
            environment["PATH"] = f"{vulkan_bin}{os.pathsep}{environment.get('PATH', '')}"

    try:
        log_directory.mkdir(parents=True, exist_ok=True)
        with log_path.open("ab") as log_file:
            process = subprocess.Popen(
                _server_command(executable, model_path, host, port),
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except OSError as error:
        raise ModelSwitchError(f"Could not start llama-server: {error}") from error

    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ModelSwitchError(
                f"llama-server exited during startup with code {process.returncode}. "
                f"See {log_path} for details."
            )
        loaded_filename, _, _ = _get_runtime_model()
        if loaded_filename and loaded_filename.casefold() == model_path.name.casefold():
            return
        time.sleep(1)

    try:
        process.terminate()
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    raise ModelSwitchError(
        f"llama-server did not report {model_path.name} as loaded within "
        f"{_STARTUP_TIMEOUT_SECONDS} seconds. See {log_path} for details."
    )


def switch_model(model_id: str) -> dict[str, str | bool]:
    """Safely restart the loopback llama.cpp server with an installed GGUF model."""
    with _switch_lock:
        inventory = list_models()
        selected_model = next((model for model in inventory["models"] if model["id"] == model_id), None)
        if selected_model is None:
            raise FileNotFoundError(f"Model is not installed: {model_id}")

        model_directory = _get_model_directory().resolve()
        target_path = (model_directory / selected_model["filename"]).resolve()
        if target_path.parent != model_directory or not target_path.is_file():
            raise FileNotFoundError(f"Model file is missing or outside the configured model directory: {model_id}")

        if inventory["active_model"] == model_id:
            return {"success": True, "active_model": model_id, "restarted": False}

        host, port = _server_address()
        executable = _get_server_executable()
        previous_id = inventory["active_model"]
        process = _find_server_process(port)
        if process is not None:
            if previous_id is None:
                raise ModelSwitchError(
                    "A process is listening on the llama.cpp port, but its loaded model is not a known installed "
                    "model; refusing to stop it."
                )
            previous_path = (model_directory / previous_id).resolve()
            if not previous_path.is_file():
                raise ModelSwitchError(
                    f"The active model file is missing from the configured model directory: {previous_id}"
                )
            _validate_server_process(process, executable, previous_path, host, port)
            _stop_server_process(process, executable, previous_path, host, port)
        elif inventory["runtime_status"] == "online":
            raise ModelSwitchError(
                "llama.cpp reports an active model, but the backend cannot identify its listening process."
            )
        else:
            previous_path = (model_directory / previous_id).resolve() if previous_id else None

        try:
            _start_server(executable, target_path, host, port)
        except ModelSwitchError as switch_error:
            if previous_path is None or not previous_path.is_file():
                raise
            try:
                _start_server(executable, previous_path, host, port)
            except ModelSwitchError as recovery_error:
                raise ModelSwitchError(
                    f"Could not load {model_id}: {switch_error} Recovery of {previous_id} also failed: {recovery_error}"
                ) from switch_error
            raise ModelSwitchError(
                f"Could not load {model_id}; restored the previously loaded model {previous_id}: {switch_error}"
            ) from switch_error

        return {"success": True, "active_model": model_id, "restarted": True}
