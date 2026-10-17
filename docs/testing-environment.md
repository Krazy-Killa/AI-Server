# Local Testing Environment

This project uses two pre-physical-server environments. Windows remains the
shared-application and GPU prototype environment; the RX 6800 XT is available
there for Windows-side tests before it is moved to the server. An additional
deployment/integration lab runs Proxmox VE 9.1-1 as a nested Hyper-V guest on
the same PC. The nested guest is for Linux/Proxmox deployment preparation and
integration testing, not physical-server acceptance.

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

## Nested Proxmox deployment lab

On 2026-10-16, the guest adapter was moved from Hyper-V NAT to an external
bridge. A reserved static LAN address and the guest's `/etc/hosts` node mapping
were updated so the configured Proxmox API hostname resolves to the guest.
Keep those values aligned if the lab network changes again.

The guest runs the dashboard and FastAPI backend from `/opt/ai-server`, with
runtime state under `/var/lib/ai-server`. The base deployment has no persistent
systemd/Quadlet units and does not auto-start after a guest boot. On
2026-10-16, transient `systemd-run` units were used to start Uvicorn and a
Python standard-library static server for the dashboard as the unprivileged
`ai-server` account, both bound only to `127.0.0.1`; both units were stopped
and the ports verified closed afterward. The dashboard root and backend
OpenAPI document returned HTTP 200, while an unauthenticated inventory request
returned HTTP 401. Windows could not reach the loopback-only ports. This was a
startup/stop smoke test, not a persistent service, reboot-recovery, or full
browser-login acceptance test.

The same-day read-only inventory check ran as `ai-server`, loaded the protected
guest `.env` without displaying its contents, and successfully retrieved one
guest using the configured Proxmox token. The response contained only
`name`, `node`, `status`, `type`, and `vmid`. The lab-only missing-CA-keyUsage
compatibility setting was enabled with the explicit CA bundle; certificate
chain and hostname verification remained enabled.

Dashboard login was verified previously. The optional Discord bot and
chat/inference remain degraded because their required services/runtime have
not been configured. NGINX/TLS, LAN application exposure, persistent service
supervision, and inference runtime are not configured. Do not reuse the
HTTP-only cookie setting outside the loopback SSH-tunnel test. All results are
nested-lab-only and do not validate physical hardware, GPU/ROCm,
network/storage topology, sustained performance, or recovery behavior. The
non-root `ai-deploy` SSH account is intended for deployment work and has no
sudo access.

## Setup

Run `setup-windows.bat` from the project root. It creates the isolated Python
environment, installs the API dependencies and ONNX Runtime DirectML, then
checks that ONNX Runtime exposes `DmlExecutionProvider`, then runs a small ONNX
graph through DirectML.

## Portable diagnostics and infrastructure tests

The runbook retrieval and maintenance/remediation simulations are local-only
portable behavior. They do not require the nested Proxmox guest, SearXNG,
llama.cpp, or the physical server. From PowerShell, run the focused backend
tests with the configured project interpreter:

```powershell
Push-Location .\ai-backend
& "$env:LOCALAPPDATA\AI-Server\venv\Scripts\python.exe" -m unittest discover -s tests -p "test_diagnostic_*.py"
& "$env:LOCALAPPDATA\AI-Server\venv\Scripts\python.exe" -m unittest discover -s tests -p "test_maintenance_simulation.py"
& "$env:LOCALAPPDATA\AI-Server\venv\Scripts\python.exe" -m unittest discover -s tests -p "test_proxmox_contracts.py"
Pop-Location
```

The tests verify reviewed-runbook filtering and access, deterministic
maintenance/remediation outcomes, proposal authorization/confirmation rules,
and the read-only Proxmox inventory contract. Passing them does not validate
live maintenance, Proxmox mutation, host recovery, or physical-server behavior.

Start the backend with `run-backend.bat`. It listens on
`http://127.0.0.1:8000`.

Start the dashboard in a second terminal with `run-dashboard.bat`, then open
`http://127.0.0.1:8001`. Serving the dashboard over HTTP allows it to call the
local API from the browser.

### Test the dashboard from a mobile device on the LAN

The normal launchers remain loopback-only. For a full mobile test (including
login and API requests), use the opt-in HTTPS LAN launchers below. Do not
disable secure cookies or expose the development servers to the public
internet. Keep the PC and phone on a trusted private Wi-Fi network and do not
configure router port forwarding.

1. Find the PC's private Wi-Fi IPv4 address with `ipconfig` (for example,
   `192.168.1.50`). Reserve that address in the router if possible so it does
   not change during testing.
2. Install and initialize [mkcert](https://github.com/FiloSottile/mkcert) on
   the PC. In PowerShell, generate a certificate whose subject includes that
   exact IP address:

   ```powershell
   $lanIp = "192.168.1.50"
   $certDir = "$env:LOCALAPPDATA\AI-Server\certs"
   New-Item -ItemType Directory -Force $certDir
   mkcert -install
   mkcert -cert-file "$certDir\lan.pem" -key-file "$certDir\lan-key.pem" $lanIp
   ```

   Find mkcert's CA directory with `mkcert -CAROOT`. Keep `lan-key.pem` and
   `rootCA-key.pem` on the PC. Install only the public `rootCA.pem` on the
   phone and explicitly enable trust for it as required by that phone's
   OS/browser. Never copy either private key to the phone. If the certificate
   is not trusted, stop and fix trust rather than bypassing the browser
   warning.
3. In the ignored project-root `.env`, configure these values using your
   address and certificate paths:

   ```dotenv
   AI_SERVER_LAN_HOST=192.168.1.50
   AI_SERVER_LAN_TLS_CERT=%LOCALAPPDATA%\AI-Server\certs\lan.pem
   AI_SERVER_LAN_TLS_KEY=%LOCALAPPDATA%\AI-Server\certs\lan-key.pem
   AI_SERVER_CORS_ORIGINS=https://192.168.1.50:8001
   AI_SERVER_AUTH_COOKIE_SECURE=true
   ```

4. Start `run-lan-backend.bat` and `run-lan-dashboard.bat` in separate
   terminals. They bind only to the configured private address and serve HTTPS
   on ports 8000 (API) and 8001 (dashboard). The dashboard server serves only
   `index.html`, `css/style.css`, and `js/app.js`; it does not expose the
   repository or `.env`. Open `https://192.168.1.50:8001` on the phone.
   To use the optional Discord bot while the LAN backend is running, set
   `AI_SERVER_API_BASE=https://192.168.1.50:8000` in `.env` and restart the
   bot. Its default `http://127.0.0.1:8000` points to loopback, where the
   LAN-only backend is not listening. Restore the loopback URL when returning
   to the normal backend launcher.
5. If Windows Firewall blocks the connection, open PowerShell as
   Administrator and allow TCP ports 8000 and 8001 only on the **Private**
   profile and only from `LocalSubnet`; do not allow these ports on Public
   networks:

   ```powershell
   New-NetFirewallRule -DisplayName "AI Server LAN Test" -Direction Inbound `
     -Action Allow -Protocol TCP -LocalPort 8000,8001 -Profile Private `
     -RemoteAddress LocalSubnet
   ```

   Stop both servers with Ctrl+C after testing. Remove the rule when finished:

   ```powershell
   Remove-NetFirewallRule -DisplayName "AI Server LAN Test"
   ```

The IP address in the certificate, `.env`, and browser URL must match. If the
address changes, regenerate the certificate and update the CORS origin. The
backend, llama.cpp, and SearXNG normal launchers remain loopback-bound; the
LAN backend can still reach those local services on the PC.

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

The AI Chat panel includes a **Research Web** checkbox. When enabled, the
next message uses `POST /api/research/stream`; otherwise chat stays local and
does not search. The complete-response `POST /api/research` endpoint remains
available. Both expect SearXNG at `http://127.0.0.1:8888` by default. Set
`SEARXNG_BASE_URL` before launching the backend to use another instance.
Research searches up to five sources and attempts to fetch full text from at
most three public HTTP(S) HTML pages. Each fetch is limited to one megabyte
and five seconds, revalidates up to three redirects, and rejects non-public
addresses and nonstandard ports. Unsafe, unavailable, and non-HTML pages fall
back to their SearXNG excerpts; source metadata reports `page_status`. The
stream returns source metadata before answer tokens, and completed turns are
saved with their citations. Automated unit and API tests cover these
boundaries; a live browser-to-WSL SearXNG-to-llama.cpp end-to-end smoke test
after this implementation is still unverified. Search queries may be
forwarded by SearXNG to its configured upstream search engines, so avoid
sending secrets or private data in Research mode.

SearXNG does not support native Windows, so the test environment runs it inside
WSL (Ubuntu) with no root access needed. One-time install from the project
root:

```powershell
wsl bash scripts/searxng/install-searxng.sh
```

The installer downloads `uv`, a private Python 3.12 (SearXNG needs 3.11 or
newer), and SearXNG into `~/searxng` in WSL, then creates `~/searxng/settings.yml`
from `scripts/searxng/settings.yml` with a random secret key. The settings bind
to `127.0.0.1:8888`, enable the `json` format the backend needs, and disable
the bot limiter, which is meant for public instances. Re-running the installer
updates SearXNG and keeps your settings. Start it with `run-searxng.bat` and
leave that window open; close it or press Ctrl+C to stop. Check it with:

```powershell
Invoke-RestMethod "http://127.0.0.1:8888/search?q=test&format=json"
```

The Models page discovers `.gguf` files in
`%LOCALAPPDATA%\AI-Server\models` and marks the file reported by llama.cpp's
`/props` endpoint as loaded. Choose an installed model from AI Chat
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
