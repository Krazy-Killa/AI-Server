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

See [the Windows test setup](../operations/testing-environment.md) for exact environment
details. See the [Linux/Proxmox transition runbook](../deployment/linux-proxmox-transition.md)
for deployment blockers, decisions, and acceptance checks.

## Linux/Proxmox deployment

DirectML is Windows-specific and will not be the deployment backend. For the
planned Proxmox VE 9.x host with one RX 6800 XT, select Linux-compatible
runtime versions and builds and verify support before deployment. The intended
stack is ROCm/HIP, llama.cpp's ROCm build with `llama-server`, ONNX Runtime's
ROCm Execution Provider, and ComfyUI with a compatible ROCm environment.
ROCm/HIP is intended to be installed on the Proxmox host; Podman/Quadlet are
intended for service/container management, NGINX for the web entry point, and
Qdrant for vector storage. This is a planned stack only; exact versions and
GPU compatibility remain unverified. Treat ROCm/HIP use with the RX 6800 XT on
Proxmox VE as **experimental and community-supported only**: AMD's current
[ROCm compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
does not list this GPU/Proxmox combination. Linux reports on other
distributions are useful leads, not evidence that ROCm works natively on this
host.

### Experimental RX 6800 XT community evidence

The following community material was reviewed on 2026-10-14. These are
reported setups, not configurations validated by this project. Check each
source for updates before use; do not treat old commands or workarounds as
current installation instructions. These sources are relevant to native Linux
GPU compute, but none establishes a working ROCm setup on Proxmox VE 9.

- [llama.cpp issue #27275: ROCm 7.x comgr segfault on gfx1030](https://github.com/ggml-org/llama.cpp/issues/27275)
  reports an RX 6900 XT (`gfx1030`) running llama.cpp on Fedora 44 with ROCm
  7.1.1, which the reporter says segfaulted in `libamd_comgr` during HIP kernel
  compilation. The reporter says a side-by-side ROCm 6.3.1 setup worked on
  that same Fedora system. This is a single-user report on an RX 6900 XT, not
  the project's RX 6800 XT or Proxmox/Debian, and it does not independently
  establish which release is broadly reliable. Treat it as a warning to pin
  and test the exact ROCm/compiler combination, not as a recommendation to
  install ROCm 6.3.1 on Proxmox.
- [Arch Linux ROCm installation gist](https://gist.github.com/augustin-laurent/d29f026cdb53a4dff50a400c129d3ea7)
  describes installing ROCm packages and reports a TensorFlow test on an
  RX 6900 XT (`gfx1030`), with `HSA_OVERRIDE_GFX_VERSION=10.3.0` as an optional
  workaround. The 6900 XT is not the project's exact card, Arch is not Debian
  or Proxmox, and the gist's package versions and steps are time-sensitive.
  Do not copy the override without a concrete detection failure and a
  version-specific reason.
- [Quantized.uk: AMD ROCm with llama.cpp](https://quantized.uk/cookbook/amd-rocm-llamacpp/)
  lists RX 6800 XT/6900 XT (`gfx1030`) as working for GGUF inference and gives
  HIP build and server-start guidance. The guide also says its Radeon
  performance figures are not measured; it is a practical secondary guide,
  not a reproducible test log, upstream support statement, or Proxmox recipe.
  Its sample CMake target in the fetched page is `gfx1100` for a newer card,
  so it must be changed to the actual `gfx1030` target for an RX 6800 XT. Check
  its ROCm and llama.cpp instructions against the versions selected at test
  time.
- [ROCmate's gfx1030 notes](https://t0nd3.github.io/rocmate/gfx1030/) list
  community application hints for RX 6800/6900-class GPUs, including llama.cpp
  HIP use. This is a secondary compatibility tracker, not an upstream support
  statement or a reproducible test record for the planned host.

Taken together, these sources make an experimental investigation reasonable,
but they do **not** establish a known-good native Proxmox ROCm stack. Keep the
host kernel and boot configuration recoverable, capture the host report, pin
the exact software versions, and verify device visibility, HIP compute, and
the actual inference workload separately. No exact RX 6800 XT + Proxmox VE
native-host setup was found in the reviewed sources. The deployment design
uses the GPU directly on the Proxmox host; GPU passthrough to a VM is not
planned. Do not infer ROCm success from `rocminfo` device detection alone or
from the existing Windows Vulkan test.

The dashboard web server, backend API, and AI runtime are planned to run
on the Proxmox host, with Podman/Quadlet managing appropriate services. This
gives host processes or explicitly configured containers direct access to the
device without assigning it to a guest VM. It does not guarantee exclusive
use: host graphics, monitoring, or other GPU workloads can still consume
resources. A future decision to use a guest would require a separate
architecture and validation plan; it is outside the current deployment scope.

### Linux AMD GPU telemetry — implemented, host validation pending

The Linux provider reads the AMD `amdgpu` kernel driver's DRM sysfs counters:
overall utilization (`gpu_busy_percent`) and dedicated VRAM used/total
(`mem_info_vram_used` / `mem_info_vram_total`). It is wired into the existing
GPU API and reports `gpu_engine: "overall"` because this source does not
provide the per-engine breakdown used by the Windows provider. It uses the
kernel driver's reported product name where available and otherwise reports
the PCI identity; it does not guess a marketing model from the PCI ID.

The telemetry reader does not depend on `rocm-smi` and does not install or
require ROCm/HIP. Optional temperature, power, and fan readings are read from
unambiguous Linux hwmon sensors when present; absent or ambiguous optional
sensors remain `null`. Missing core counters, unreadable or invalid values,
and multiple supported AMD adapters return explicit `unavailable` status and
no fabricated readings. Multiple adapters are not silently selected.

Deterministic fixture tests verify counter parsing, units, adapter identity,
missing/invalid counters, optional hwmon data, and ambiguous devices. This
establishes provider behavior only; no Linux kernel, physical GPU, or ROCm
runtime was available in this environment. On the target host, verify the
actual `amdgpu` sysfs files and service-account permissions, adapter identity,
idle and inference load/VRAM readings, optional sensor behavior, and reads
from the chosen container/service arrangement. This telemetry path does not
establish that ROCm/HIP inference works on the RX 6800 XT or Proxmox.

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

The intended workload-role design is to dedicate the RX 6800 XT strictly to
maintenance AI (diagnostics, incident analysis, runbooks, and scheduled
maintenance), and use a possible second GPU for household-facing AI. Candidate
second-GPU choices are the Radeon RX 7900 XT/XTX, if greater VRAM capacity is
the priority, or the RX 9070 XT, for its RDNA 4 architecture and potential
speed/efficiency advantages. The exact 7900 variant is undecided, and these
tradeoffs have not been benchmarked with the intended workloads. The second
GPU is not selected or acquired. Until it is validated, the interim design is
single-GPU/single-runtime model handoff, not concurrent operation of both
roles. Power/cooling, compatibility, and performance are unvalidated. See the
[household infrastructure reference](../operations/home-network-topology.md#possible-multi-gpu-role-separation).

## Strategy

1. Validate the dashboard and API with live llama.cpp chat and Windows GPU
   telemetry; identify which remaining panels still use stubs.
2. Test Windows ONNX workloads using DirectML.
3. Build and smoke-test llama.cpp with Vulkan on Windows.
4. Choose an image-generation framework and validate it on Windows.
5. Record the Proxmox/OS layout and verify the exact kernel, GPU, and runtime
   combination against current upstream support information.
6. Install and smoke-test ROCm/HIP, llama.cpp `llama-server`, ONNX Runtime
   ROCm EP, and ComfyUI against the selected Linux host.
7. Validate the implemented Linux `amdgpu` telemetry provider against the
   target GPU and kernel through the existing dashboard API contract.
8. Deploy NGINX, Qdrant, and supported application services with Podman/
   Quadlet where appropriate; validate host inference and telemetry,
   model-switch recovery, and remote dashboard access.
9. If multiple GPUs are installed, benchmark supported model-splitting and
   per-GPU model-instance routing approaches against the single-GPU baseline.
