# GPU Integration Plan

## Hardware and platforms

- The Windows development machine currently has the AMD RX 6800 XT installed.
- After a replacement GPU is acquired, the RX 6800 XT is intended to move to
  the dedicated AI Server.
- The dedicated server is planned to run Linux under Proxmox.

## Windows development/testing

- **LLMs:** llama.cpp with Vulkan is built and tested on Windows. The RX 6800
  XT is detected as `Vulkan0`; a small GGUF inference completed with all 7
  model layers offloaded to the GPU. The FastAPI chat endpoint is connected to
  the llama.cpp server and uses a Qwen2.5 1.5B Instruct GGUF for local
  responsiveness testing. The source checkout, build, and test model are
  stored under `%LOCALAPPDATA%\AI-Server`, outside the OneDrive project
  folder. This confirms the test path, not performance with production models.
- **Telemetry:** Windows GPU load and dedicated VRAM usage are reported live
  by the system monitor. Linux/Proxmox telemetry remains future work.
- **Vision:** ONNX Runtime + DirectML. The local environment and provider have
  been installed and a small synthetic ONNX inference has passed. A real
  vision model and app integration are not yet configured.
- **Image generation:** DirectML is the intended Windows testing direction;
  the compatible framework and isolated dependencies still need to be chosen.

See [the Windows test setup](./testing-environment.md) for exact environment
details. See the [Linux/Proxmox transition runbook](./linux-proxmox-transition.md)
for deployment blockers, decisions, and acceptance checks.

## Linux/Proxmox deployment

DirectML is Windows-specific and will not be the deployment backend. Select
Linux-compatible GPU runtimes for LLM, vision, and image generation separately,
and verify support for the RX 6800 XT and Proxmox host before deployment.
The dashboard web server, backend API, and AI runtime are planned to run
directly on the Proxmox host, so AI workloads and GPU telemetry will use the
host's GPU rather than a GPU-passthrough guest. This avoids VM GPU-passthrough
overhead and gives the host AI runtime direct access to the device. It does not
guarantee exclusive use: host graphics, monitoring, or other GPU workloads can
still consume resources. ROCm and other options remain candidates, not a
confirmed production stack. GPU passthrough is only relevant if a future VM is
intentionally assigned the GPU.

### Linux GPU telemetry — required after the GPU is moved

The current telemetry reader is Windows-only. Once the RX 6800 XT is installed
in the Linux/Proxmox server, implement and validate a Linux telemetry provider
that reads the host GPU used by the host AI runtime.

The Linux provider must return the same GPU load and status fields used by the
dashboard, report the correct adapter, and show `N/A` when a live reading is
unavailable rather than falling back to simulated utilization. Verify its
load readings under idle and real inference workloads, along with device
identity and VRAM reporting, before treating telemetry as operational. Proxmox
host and guest workload attribution should be considered separately if GPU
sharing with VMs is added later. Until Linux telemetry is implemented,
non-Windows systems report live GPU load as unavailable.

### Potential future: multi-GPU inference

After the final server GPU configuration and Linux runtime are known, evaluate
using multiple GPUs for LLM inference. The options are to split one model
across supported GPUs, or run a separate instance of the same model on each
GPU and route dashboard and Discord requests independently. The latter can
improve concurrent throughput but duplicates model memory; splitting may
increase the model size that fits but does not combine VRAM without runtime
support and may add inter-GPU communication overhead. Neither option is
implemented or assumed to improve performance. Compare supported hardware and
runtime combinations, VRAM use, throughput, latency, power, and stability
against the single-GPU setup before deciding.

## Strategy

1. Validate the dashboard and API with live llama.cpp chat and Windows GPU
   telemetry; identify which remaining panels still use stubs.
2. Test Windows ONNX workloads using DirectML.
3. Build and smoke-test llama.cpp with Vulkan on Windows.
4. Choose an image-generation framework and validate it on Windows.
5. Record the Proxmox/OS layout and verify the exact kernel, GPU, and runtime
   combination against current upstream support information.
6. Build and smoke-test the selected llama.cpp GPU backend on Linux.
7. Implement Linux GPU telemetry behind the existing dashboard API contract.
8. Integrate and validate host inference and telemetry under system services,
   including model switching, restart recovery, and remote dashboard access.
9. If multiple GPUs are installed, benchmark supported model-splitting and
   per-GPU model-instance routing approaches against the single-GPU baseline.
