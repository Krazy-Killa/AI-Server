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
  by the system monitor. Linux AMD telemetry is implemented through the
  `amdgpu` sysfs provider and fixture-tested; live Linux/Proxmox readings still
  require target-host validation.
- **Vision:** ONNX Runtime + DirectML. The local environment and provider have
  been installed and a small synthetic ONNX inference has passed. A real
  vision model and app integration are not yet configured.
- **Image generation:** DirectML is the intended Windows testing direction;
  the compatible framework and isolated dependencies still need to be chosen.

See [the Windows test setup](../operations/testing-environment.md) for exact environment
details. See the [Linux/Proxmox transition runbook](../deployment/linux-proxmox-transition.md)
for deployment blockers, decisions, and acceptance checks.

## Proposed single-GPU inference profiles — planned, not implemented

The proposed initial RX 6800 XT runtime keeps a small Utility AI resident while
one larger role model is loaded for the active operating profile:

| Role | Model | Intended responsibilities |
|---|---|---|
| Utility AI (resident) | Qwen2.5 1.5B Instruct | Discord interactions, status/notification requests, incident/diagnostic/update summaries, lightweight chat, and fallback responses |
| Household AI (Household mode) | Qwen3 8B | General household chat, research, planning, and future family-facing interactions |
| Maintenance AI (Maintenance mode) | Qwen2.5 Coder 7B Instruct | Diagnostics, log/runbook assistance, configuration review, infrastructure analysis, and operational reporting |

Household mode is intended to keep Utility AI available alongside Qwen3 8B.
Maintenance mode is intended to keep Utility AI available alongside Qwen2.5
Coder 7B. Discord status and notification requests route to Utility AI,
infrastructure analysis to Maintenance AI, and general conversation/research
to Household AI. During a profile transition, Utility AI is intended to
continue handling first-response requests while the larger model is loaded
and health-checked.

This is a target architecture, not current runtime behavior. The implemented
model manager currently controls one llama.cpp server and one loaded model;
switching models restarts that server. There is no resident Utility process,
profile selector/router, or concurrent model serving. The process/port
arrangement and request queue/failure policy still need design. The estimated
~1 GB Utility VRAM use is a planning estimate, not a measured residency
figure. The Qwen3 and Qwen2.5 Coder models have been smoke-tested individually
on Windows/Vulkan, but not while the Utility model is also resident. Measure
VRAM, system RAM, context/KV-cache, runtime overhead, latency, swap recovery,
and sustained behavior before treating either two-model profile as feasible
on the 16 GB card. The RX 6800 XT/Proxmox ROCm path remains unvalidated.

All roles must follow the platform's server-side reasoning policy: Utility and
Household replies never expose raw reasoning, and a future Maintenance
reasoning summary must not reveal raw chain-of-thought. Full reasoning
visibility is reserved for a future, explicitly gated developer/debug mode;
none is implemented. See the [backend API contract](../backend/api.md) for the
current output filter.

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

The shared Linux kernel ecosystem and Debian-related foundations of Ubuntu
and Proxmox make compatibility investigation technically plausible, but they
do not establish that the overall compatibility risk is low. Ubuntu and
Proxmox remain distinct operating-system distributions with different
packaging and kernel integration; an upstream kernel version match does not
make them interchangeable for ROCm support. AMD's published support applies
to the listed operating-system, kernel/driver, ROCm, and GPU combinations,
not automatically to Debian derivatives. Verify the exact Proxmox release
and running kernel, AMD driver, ROCm version, container device access, and
target inference workload on the physical host before drawing a compatibility
conclusion.

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

### Potential future: dual-GPU service separation

This future concept separates operational and household AI services so that
Household AI and Maintenance AI can remain available simultaneously without
swapping their models. Users would interact with services and roles rather
than choosing model files.

| GPU | Planned role | Intended models and workloads |
| --- | --- | --- |
| GPU 0 — RX 6800 XT | Operations | Qwen2.5 1.5B Utility AI remains resident; Qwen2.5 Coder 7B Maintenance AI handles diagnostics, runbooks, infrastructure analysis, and Discord operations |
| GPU 1 — future upgrade | Household | Qwen3 8B and future household-specific models handle general chat, research, voice, and family-facing services |

For example, Utility AI could acknowledge a Discord incident request and route
the analysis to Maintenance AI while Household AI remains available for
dashboard conversations and research. No model unloading would be required
between Household and Maintenance services.

The RX 9070 XT is a candidate second GPU, not a selection or claim of
confirmed suitability. Final selection depends on ROCm support, VRAM capacity,
power/cooling, and measured local AI performance.

This is a concept, not current runtime behavior. The physical server has not
been built, no second GPU has been selected or acquired, and the current model
manager still runs one active model and restarts it when switching. Simultaneous
Utility and Maintenance residency on the RX 6800 XT, a separate Household
runtime, service routing, ROCm compatibility, and failure recovery all require
design and validation before this architecture can be adopted.

## Strategy

1. Validate the dashboard and API with live llama.cpp chat and Windows GPU
   telemetry; identify which remaining panels still use stubs.
2. Test Windows ONNX workloads using DirectML.
3. Build and smoke-test llama.cpp with Vulkan on Windows.
4. Choose an image-generation framework and validate it on Windows.
5. Record the Proxmox/OS layout and verify the exact kernel, GPU, and runtime
   combination against current upstream support information.
6. Install and smoke-test ROCm/HIP, llama.cpp `llama-server`, ONNX Runtime
   ROCm EP, and ComfyUI against the selected Linux host; measure whether
   Utility AI can remain resident alongside each profile model.
7. Validate the implemented Linux `amdgpu` telemetry provider against the
   target GPU and kernel through the existing dashboard API contract.
8. Deploy NGINX, Qdrant, and supported application services with Podman/
   Quadlet where appropriate; validate host inference and telemetry,
   model-switch recovery, and remote dashboard access.
9. After measuring the single-GPU baseline, evaluate the proposed
   dual-GPU service split. Validate supported runtimes, simultaneous Utility
   and Maintenance residency on the Operations GPU, Household inference on the
   second GPU, routing, VRAM/RAM, throughput, latency, power/cooling, and
   recovery before enabling concurrent services.
