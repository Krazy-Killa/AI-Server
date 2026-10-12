# Local Testing Environment

The Windows development environment is separate from the planned Linux/Proxmox
server. The RX 6800 XT is available in the Windows development machine for
testing GPU workloads before it is moved to the server.

## Windows baseline

- Windows 11
- Python 3.12
- AMD Radeon RX 6800 XT
- ONNX Runtime DirectML for Windows-side ONNX tests
- Visual Studio 2022 Build Tools 17.14.41 with the C++ workload
- Vulkan SDK 1.4.363.0

The project Python environment is created outside the OneDrive workspace at
`%LOCALAPPDATA%\AI-Server\venv` to avoid synchronizing virtual-environment
files.

## Setup

Run `setup-windows.bat` from the project root. It creates the isolated Python
environment, installs the API dependencies and ONNX Runtime DirectML, then
checks that ONNX Runtime exposes `DmlExecutionProvider`, then runs a small ONNX
graph through DirectML.

Start the backend with `run-backend.bat`. It listens on
`http://127.0.0.1:8000`.

Start the dashboard in a second terminal with `run-dashboard.bat`, then open
`http://127.0.0.1:8001`. Serving the dashboard over HTTP allows it to call the
local API from the browser.

## GPU load telemetry

On Windows, the system monitor reads the RX 6800 XT's `GPU Engine` performance
counters and displays the busiest engine's utilization. The adapter is matched
to its engine counters using its Vulkan device LUID. The dashboard shows
dedicated-memory usage from Windows GPU Adapter Memory counters and the
device-local capacity reported by Vulkan. Counters are sampled in a background
worker because Windows exposes many per-process engine counters; readings
refresh about every six seconds on this machine. If the adapter or counters
are unavailable, the UI shows `N/A` instead of simulated load or VRAM usage.

## llama.cpp Vulkan chat test

The Windows llama.cpp build uses the upstream source at commit `8bb3cf0`,
checked out under `%LOCALAPPDATA%\AI-Server\src\llama.cpp`. It was configured
and built with Visual Studio 2022 Build Tools 17.14.41, MSVC 19.44, CMake
3.31.6, and Vulkan SDK 1.4.363.0. The `llama-cli` and `llama-server`
executables are under
`%LOCALAPPDATA%\AI-Server\build\llama.cpp-vulkan\bin\Release`.

The dashboard chat now sends requests from FastAPI to the local
llama.cpp-compatible endpoint at `http://127.0.0.1:8080`. Download the Qwen2.5
1.5B Instruct Q4_K_M model to the model directory and verify its SHA-256:

```bat
mkdir "%LOCALAPPDATA%\AI-Server\models" 2>nul
curl.exe -L --fail --output "%LOCALAPPDATA%\AI-Server\models\qwen2.5-1.5b-instruct-q4_k_m.gguf" "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf?download=true"
certutil -hashfile "%LOCALAPPDATA%\AI-Server\models\qwen2.5-1.5b-instruct-q4_k_m.gguf" SHA256
```

Expected SHA-256:
`6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.

Start the local LLM server and leave its terminal open:

```bat
run-llama-server.bat
```

The launcher loads the model onto `Vulkan0` with up to 99 layers offloaded,
listening only on `127.0.0.1:8080`. In a separate terminal, start
`run-backend.bat` and `run-dashboard.bat`, then submit a prompt in the
dashboard. Each assistant response displays its request latency. If the model
server is stopped, chat returns a visible error rather than a stub reply.
The local Qwen2.5 1.5B model has been verified through the dashboard chat path;
Windows telemetry reports live GPU load and VRAM while it runs.

### Explicit web research

The Chat Interface includes a **Research Web** checkbox. When enabled, the
next message uses `POST /api/research`; otherwise chat stays local and does not
search. The research endpoint expects SearXNG at
`http://127.0.0.1:8888` by default. Set `SEARXNG_BASE_URL` before launching
the backend to use another instance. Enable SearXNG's `json` response format
in its settings; the endpoint uses up to five result excerpts and returns
their source links with the local model's answer. It does not yet fetch full
pages. Search queries may be forwarded by SearXNG to its configured upstream
search engines, so avoid sending secrets or private data in Research mode. The
SearXNG service itself still needs to be installed and configured.

The Models page discovers `.gguf` files in
`%LOCALAPPDATA%\AI-Server\models` and marks the file reported by llama.cpp's
`/props` endpoint as loaded. Choose an installed model from the AI Interface
dropdown or click its card on the Models page to switch the running server.
The backend verifies that the loopback port belongs to the expected
`llama-server`, restarts it with the selected file, and only reports success
after `/props` confirms the new model. A failed load triggers an attempt to
restore the previous model. This interrupts in-flight requests while the
server restarts. Set `AI_SERVER_MODEL_DIR` before starting the backend to use
a different model directory, and set `LLAMA_SERVER_EXECUTABLE` if the server
binary is not at its default build path. On Linux, model switching defaults to
the `ROCm0` device; set `LLAMA_CPP_DEVICE` to a device name reported by that
llama.cpp build if it differs.

Additional 4-bit models for the RX 6800 XT are available in the same directory:

| Model | GGUF quantization | File size | SHA-256 |
| --- | --- | ---: | --- |
| [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B-GGUF) | Q4_K_M | 5,027,783,488 bytes (4.68 GiB) | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF) | Q4_K_M | 4,683,074,336 bytes (4.36 GiB) | `1664fccab734674a50763490a8c6931b70e3f2f8ec10031b54806d30e5f956b6` |

Both source model cards specify Apache-2.0 licensing. These are model-weight
files, not tools or executable code. Each model is intended to load by itself
on the 16 GiB GPU; VRAM is not shared by loading both into the current
single-model llama.cpp server at once.
Both files have been downloaded and verified against the SHA-256 hashes
listed above. Short Vulkan inference tests at a 4096-token context loaded
each model and offloaded all 37 Qwen3 or all 29 Qwen2.5-Coder layers to the
RX 6800 XT. These smoke tests confirm the GPU execution path, not sustained
performance or quality benchmarks.

To start one of the installed models instead of the default Qwen2.5 1.5B model
without using the dashboard, pass the exact filename to the launcher:

```bat
run-llama-server.bat Qwen3-8B-Q4_K_M.gguf
run-llama-server.bat Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf
```

After it starts, refresh the dashboard; the model inventory identifies the
newly loaded file. The launcher uses Vulkan, up to 99 GPU layers, and a 4096
token context. For Qwen3, it selects llama.cpp's built-in ChatML template
because the current pinned Jinja engine does not support an operation in
Qwen3's embedded template. Verify actual GPU offload and available VRAM in
the llama.cpp startup log and system monitor when testing each larger model.

To rebuild, open an x64 Visual Studio 2022 Developer Command Prompt and run:

```bat
set "VULKAN_SDK=C:\VulkanSDK\1.4.363.0"
set "PATH=%VULKAN_SDK%\Bin;%PATH%"
cmake -S "%LOCALAPPDATA%\AI-Server\src\llama.cpp" -B "%LOCALAPPDATA%\AI-Server\build\llama.cpp-vulkan" -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DGGML_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=ON
cmake --build "%LOCALAPPDATA%\AI-Server\build\llama.cpp-vulkan" --config Release --target llama-cli llama-server -j 8
```

The earlier tiny smoke-test model is
[`tinyllamas/stories15M-q4_0.gguf`](https://huggingface.co/ggml-org/models/resolve/main/tinyllamas/stories15M-q4_0.gguf)
from the `ggml-org/models` Hugging Face repository. Its SHA-256 is
`66967fbece6dbe97886593fdbb73589584927e29119ec31f08090732d1861739`.
With that model, the following command generated text and the verbose runtime
log confirmed `offloaded 7/7 layers to GPU` on the RX 6800 XT:

```bat
"%LOCALAPPDATA%\AI-Server\build\llama.cpp-vulkan\bin\Release\llama-cli.exe" -m "%LOCALAPPDATA%\AI-Server\models\stories15M-q4_0.gguf" -ngl 99 --device Vulkan0 -n 12 -p "Once upon a time" --single-turn --no-display-prompt --verbose
```

The tiny model verifies the Vulkan build and GPU-offload path; it is not a
quality or production-model benchmark. The Qwen2.5 1.5B model is used for
coherent chat and latency checks, not as a production model benchmark.

## Scope and limitations

- The small DirectML smoke test validates a basic GPU inference path; it does
  not validate a particular vision or image-generation model.
- No ONNX model is bundled. Add a model and an inference path before measuring
  vision workloads.
- Image generation still needs a selected DirectML-compatible framework and
  its own compatible dependency environment.
- GPU backend choices for Linux/Proxmox are separate from this Windows setup.
- Linux/Proxmox GPU telemetry and VRAM reporting are not implemented yet.
- Vision, image generation, and other unconnected workloads still use stubs.
