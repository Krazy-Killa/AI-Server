# AI Server Project Context

**Purpose:** Primary onboarding briefing for new contributors and AI sessions.
This is a high-level snapshot, not an operational runbook. The
[development roadmap](./roadmap/README.md), focused subsystem guides, source,
and tests remain authoritative for detailed status and behavior.

**Status snapshot:** 2026-11-05. Distinguish implemented Windows behavior,
portable/mock test evidence, nested-lab validation, plans, and physical-host
acceptance. Success in one environment does not prove behavior in another.

## Project Overview

### Mission and goals

The AI Server (also called the **AI Command Interface**) is a local-first
household AI and operations platform under development. It combines a browser
dashboard, a Python/FastAPI backend, local model inference, system telemetry,
and an optional Discord bot. The intended deployment target is a dedicated
Linux server running Proxmox VE.

Goals include:

- Provide one interface for local AI chat, web research, model inventory and
  switching, host monitoring, and operations.
- Support private per-account conversations separately from the shared,
  admin-only AI Interface.
- Add bounded, evidence-based diagnostics and household infrastructure
  awareness over time.
- Prepare Linux/Proxmox deployment while developing shared application
  behavior and portability tests on Windows.

### Intended household operations use cases

Current implemented use cases include local AI chat and optional research,
system/GPU telemetry, private conversation history, explicitly published
admin-shared notes, observe-only diagnostics, backend logs, Discord bot
status/control, and read-only Proxmox VM/container inventory.

Future concepts include network-aware household diagnostics, infrastructure
inventory, a conversational voice interface, request-scoped operational
context for Maintenance AI, and possible separation of user-facing and
maintenance AI workloads, plus a household file-storage service. These
concepts are not implemented integrations; see
[Future Capabilities](#future-capabilities).

### Core architectural principles

- Keep model inference and application data local where the selected
  deployment supports it.
- Keep identity and authorization in the backend; dashboard role-based
  visibility is not the security boundary.
- Separate private account conversations, the admin-shared operational
  transcript, explicitly published shared notes, and diagnostic history.
- Keep providers and operating-system-specific telemetry behind explicit
  contracts; report unavailable data rather than fabricating readings.
- Treat external research content as untrusted evidence.
- Never expose raw model reasoning to users. Standard and streaming replies
  are filtered server-side, and saved assistant history is filtered before
  storage, display, and model reuse. Future Maintenance summaries may be
  optional, but raw chain-of-thought remains unavailable. Full reasoning
  visibility is reserved for a future, explicitly gated developer/debug mode;
  no such mode is implemented.
- Use narrow, read-only infrastructure integrations first. Never infer
  permission to make changes from inventory or monitoring access.
- Validate shared behavior on Windows, then separately validate Linux,
  Proxmox, network exposure, hardware, and recovery on their target
  environments.

## Development Philosophy

- **Observe First:** Diagnostics and initial infrastructure monitoring are
  explicitly requested and read-only. No live repair, scheduled maintenance,
  network changes, or general-purpose command execution is implemented.
- **Verify Before Action:** Model output is not authority. Any future action
  must be checked by deterministic backend policy, authorization, preconditions,
  and independent verification.
- **Fail Closed:** Reject unknown identities, unauthorized requests, invalid
  configuration, ambiguous hardware selection, and invalid/missing telemetry.
  Distinguish unavailable or unconfigured from healthy or empty.
- **Rollback When Uncertain:** Deployment and future operational changes need a
  known recovery path. Existing nested-lab rollback evidence restores a saved
  snapshot of the current build, not a previous distinct application release.
- **Documentation-Driven Development:** Read the roadmap and affected
  subsystem guide before implementation; update affected documentation with
  the code. Keep implemented, partial, planned, and unverified states explicit.
- **Evidence-Based Validation:** Use focused tests and observed target behavior.
  Mocks and source-contract tests prove only their defined scope. Record
  Windows, nested-lab, and physical-host evidence separately.

## Current Architecture

### Frontend

The frontend is static HTML, CSS, and native browser JavaScript ES modules;
there is no bundler. [index.html](https://github.com/Krazy-Killa/AI-Server/blob/main/index.html)
loads [js/app.js](https://github.com/Krazy-Killa/AI-Server/blob/main/js/app.js),
which owns authentication, navigation, chat/research, model selection, and bot
controls. Focused modules handle backend logs, diagnostics/VM inventory,
system telemetry, and UI preferences. It is served over HTTP/HTTPS to allow
module imports.

Playwright browser tests mock API responses. They cover module loading,
authentication gating and failures, role controls, navigation, and persisted
preferences. They are not backend authorization or deployment tests.

### Backend

`ai-backend/main.py` assembles the FastAPI app and preserves the `main:app`
server entry point. `ai-backend/api/` contains shared runtime setup,
authentication/logging/CORS middleware, and routers grouped into auth, chat,
memory, research, and operations. Related modules handle configuration,
SQLite memory, diagnostics, model lifecycle, system statistics, Proxmox
authentication/inventory, and SearXNG research. llama.cpp is a separate local
HTTP service. Backend settings are validated at startup; logs use console and
rotating-file handlers, and chat message text is not logged.

### Authentication

The dashboard supports local accounts and Proxmox identities explicitly
mapped to dashboard roles. The application owns sessions and permissions.
Sessions use protected cookies; state-changing browser requests require CSRF
and origin checks. Roles are `viewer`, `operator`, and `admin`. Account and
Proxmox role administration is performed through a trusted local CLI.
The optional Discord bot uses a separate machine credential and does not use
dashboard sessions.

### Diagnostics

`ai-backend/diagnostics.py` performs explicitly requested, bounded health and
resource observations. The implemented checks include backend/service status,
resource thresholds, and read-only SQLite integrity. There is no scheduled
collection, model-driven diagnosis, or live remediation.

### Incident tracking

Observations, incident state/transitions, and audit evidence are persisted in
the configured local SQLite database with bounded retention. Open incidents
and pending threshold evidence restore on backend startup. JSON evidence
reports refer to saved observations; generating a report does not run probes.

### Memory systems

The SQLite memory store contains separate data domains:

- Private per-account AI Chat conversations, with ownership checks and bounded
  recent-turn context.
- Admin-published shared operational notes, managed in the AI Interface and
  included only in authorized admin AI Chat, AI Interface, and Research
  context.
- The admin-shared AI Interface operational transcript, separate from private
  AI Chat history.
- Bounded diagnostics observations, incidents, and audit history.

Reviewed diagnostic runbooks are bundled and searched with deterministic local
lexical search. This is not semantic/vector retrieval. Conversation contents
are not automatically extracted into facts or used for model training.

### Maintenance Subsystem

The design describes a future AI Maintenance Agent, but the live implementation
is observe-only. Maintenance/remediation paths currently exist as deterministic
in-memory simulations with fixed fixtures; they do not connect to host
services, shell, Proxmox, or persistent application state. Scheduling, model
driven diagnosis, approvals/execution, and live remediation are not
implemented.

### Infrastructure Integrations

- **System telemetry:** CPU/RAM telemetry is available through `psutil`.
  Windows reports live GPU engine load and dedicated VRAM from Windows
  counters. Linux AMD telemetry reads kernel `amdgpu` sysfs counters through a
  platform provider and has fixture tests; live Linux/physical-GPU readings
  are unverified and do not establish ROCm/HIP inference support.
- **Proxmox:** a backend-only read-only API token can retrieve VM/container
  inventory. A nested-lab live inventory request returned the expected fields.
  No VM mutation or guest-console controls are implemented.
- **Network services:** DHCP/DNS/web/routing views are planning UI. There is no
  network telemetry provider or network-changing integration.
- **External services:** llama.cpp is used for local inference. The current
  model manager runs one active model; the Utility/Household/Maintenance
  single-GPU profile design is planned but not implemented. SearXNG is an
  optional research service and must be installed/configured to search. The
  Discord bot is optional.
- **Deployment:** rootless Podman/Quadlet definitions exist for backend and
  dashboard containers. A verify-only signed-bundle upload (Stage 1) is
  deployed to the nested lab and verified for one signed test bundle; the
  apply flow and separate updater are design-only. Model weights stay in the
  persistent model directory, not application bundles; a separate signed
  model-package workflow is planned but not implemented.

## Environment Strategy

### Windows Test Environment

Windows 11 with Python 3.12 is the active shared-application development and
prototype environment. The RX 6800 XT is currently available in this machine.
Windows tests cover application behavior, local llama.cpp/Vulkan inference,
GPU counters, DirectML smoke tests, and browser regressions. A live browser
smoke test on 2026-11-04 verified local chat and Research Web through WSL
SearXNG to llama.cpp; this is Windows/WSL evidence, not Linux/Proxmox
acceptance. Keep the Python environment and model/build files outside the
OneDrive repository under `%LOCALAPPDATA%\AI-Server`.

**Purpose:** Build shared application features and run deterministic tests
before moving them to Linux. Windows results do not validate Linux services,
ROCm, Proxmox networking, or physical-host recovery.

### Nested Lab Environment

Proxmox VE 9.1-1 runs as a nested Hyper-V guest on the Windows PC. The
dashboard and backend are deployed in rootless Podman/Quadlet containers with
ports bound to guest loopback. The latest deployment is
`20261106-updater-verify`; both containers were healthy about 45 seconds after
the switch, and the dashboard root returned 200 while `/docs` returned 404.
Boot auto-start and clean/forced guest recovery were verified earlier in the
nested lab; re-check reboot recovery after this latest release. NGINX/TLS
access was verified from Windows and iPhone before this release. A signed
Stage 1 test bundle was verified through the dashboard and the operator
reported that Discard appeared to work. A separate two-release rollback,
large upload through the dedicated NGINX location, and physical-host
acceptance remain unverified.

**Purpose:** Prepare Linux/Proxmox deployment and integration work. Results
are nested-lab evidence only, not physical server acceptance.

### Planned Physical AI Server

The target is a dedicated Proxmox VE 9.x server using direct host GPU access
(GPU passthrough is not planned). The current intended initial GPU is one
RX 6800 XT, moved from the Windows PC after a replacement GPU is obtained.
Potential Linux components include ROCm/HIP, ROCm-built llama.cpp,
Podman/Quadlet, NGINX, and other runtimes/services described in the
[deployment runbook](./deployment/linux-proxmox-transition.md). The RX 6800 XT
and Proxmox combination is not listed as officially supported by AMD in the
documented compatibility review. Ubuntu and Proxmox share Linux-kernel and
Debian-related foundations, which make testing plausible but do not establish
low compatibility risk or AMD support for Proxmox; they remain distinct
distributions with different packaging and kernel integration. Treat GPU
compute as experimental until the exact host, kernel, driver, ROCm stack,
container access, and inference workload are validated.

**Purpose:** Final target-host validation of hardware, kernel/runtime
compatibility, permissions, network exposure, service lifecycle, performance,
and recovery. Phase 5 is waiting for this physical server.

## Host Telemetry Status

The host monitor reports CPU and RAM telemetry. On the Windows development
machine, it also reports RX 6800 XT load and dedicated VRAM using Windows
performance counters. A Linux `amdgpu` sysfs provider exists and is covered by
fixture tests, but live Linux readings have not been validated. The dashboard's
System Monitor displays one-hour in-memory GPU, VRAM, CPU, and
RAM trends, sampled every ten seconds and reset when the page reloads. These
trend samples are not persisted by the backend. The project does not currently
integrate external network telemetry or correlate WAN, LAN, wireless, service,
and client evidence. Network-aware diagnostics remain a future observe-only
concept and are not implemented.

## Server Hardware Plans

### Current development hardware

The documented Windows development machine is Windows 11 and currently has
the AMD RX 6800 XT available for local Vulkan/llama.cpp tests and Windows GPU
telemetry. The repository does not establish its motherboard or CPU model.

### Planned server platform and GPU

The planned platform is a **Z590 motherboard + Intel Core i9-11900KF**, with
an RX 6800 XT as the initial GPU. The card is intended to serve a proposed
single-GPU Utility/Household/Maintenance inference architecture, not a
Maintenance-only workload. The exact motherboard model and delivered
physical hardware still need confirmation; this is a plan, not verified
inventory.

The RX 6800 XT has 16 GB VRAM according to the deployment planning guide. The
host is planned for 32 GB system RAM initially, with a possible 64 GB upgrade;
storage plans include a 2 TB initial NVMe and HDD-backed bulk/lower-I/O
workloads. These are provisional plans, not a finalized bill of materials.
The storage layout, redundancy, backup strategy, exact motherboard model, and
physical inventory must be confirmed.

### Proposed single-GPU AI roles and profiles — not implemented

The planned initial RX 6800 XT design uses three model roles on one GPU:

- **Utility AI — Qwen2.5 1.5B Instruct:** intended to stay resident as the
  first-response service for Discord interactions, status and notification
  requests, summaries, lightweight chat, and fallback responses. The roughly
  1 GB VRAM figure is an estimate, not a measured resident allocation.
- **Household AI — Qwen3 8B:** intended for general household chat, research,
  and planning in Household mode.
- **Maintenance AI — Qwen2.5 Coder 7B Instruct:** intended for diagnostics,
  log/runbook assistance, configuration review, infrastructure analysis, and
  operational reporting in Maintenance mode.

Each operating profile is intended to keep Utility AI available while loading
one larger profile model: Household mode pairs Utility with Qwen3 8B, while
Maintenance mode pairs Utility with Qwen2.5 Coder 7B. Discord status and
notification requests route to Utility; infrastructure analysis routes to
Maintenance; general conversation and research route to Household. Role
routing, persistent Utility residency, profile switching, and graceful
recovery are design goals, not current behavior.

The current model manager runs one active llama.cpp model and restarts that
server when switching. The Windows smoke tests loaded Qwen3 8B and Qwen2.5
Coder 7B individually; neither was tested while Utility remained resident.
The profile process/endpoint arrangement, VRAM and system-RAM headroom
(including context/KV cache and runtime overhead), latency, and failure
recovery must be designed and measured before this architecture is treated as
operational. ROCm/HIP on the planned Proxmox host remains separately
unvalidated.

### Possible future dual-GPU service separation

The proposed future split assigns the planned RX 6800 XT to Operations:
Qwen2.5 1.5B Utility AI would remain resident alongside Qwen2.5 Coder 7B
Maintenance AI. A future, unselected second GPU would serve Household AI with
Qwen3 8B and possible household-specific models. The goal is simultaneous,
service-oriented operation rather than model selection and swapping between
Household and Maintenance.

The RX 9070 XT is an unselected candidate. Selection depends on ROCm support,
VRAM, power/cooling, and measured local AI performance. The physical server is
not built, and the current model manager still supports one active model;
concurrent residency, per-GPU routing, compatibility, and recovery are
unimplemented and unverified.
See the [GPU plan](./gpu/gpu-plan.md#potential-future-dual-gpu-service-separation).

## Completed Milestones

Summary of milestones documented in the roadmap (not a substitute for its
scope notes and evidence boundaries):

- **Phase 1 — Local Test Environment: Done.** Dashboard and backend
  foundations, chat/model discovery, system monitoring, optional Discord bot,
  and operational logging.
- **Phase 2 — Portable Backend and Reliability: substantially implemented
  locally.** Configuration/logging, local chat streaming, web research,
  dashboard authentication, account-scoped conversation history,
  admin-shared notes and transcript, bounded observe-only diagnostics,
  incident history, and backend logs. Linux/proxy/physical behavior remains
  separately gated.
- **Phase 3 — Mocked Integrations and Portable Feature Work: partial.**
  Read-only Proxmox inventory and contracts, reviewed local lexical runbooks,
  deterministic maintenance/remediation simulations, browser modules, and
  other portable feature groundwork. Live remediation and infrastructure
  mutation are not included.
- **Frontend browser regressions:** Playwright tests cover native module
  loading, authentication and role controls, panel navigation, UI
  preferences, VM inventory rendering, signed-bundle staging controls, and
  Diagnostics report download/share behavior. These are browser tests with
  mocked API responses, not live-device acceptance.
- **Linux telemetry provider:** Linux AMD `amdgpu` sysfs provider and
  deterministic fixtures are implemented; live Linux/physical readings and
  ROCm/HIP inference are not validated.
- **Nested-lab deployment evidence:** rootless backend/dashboard containers
  are loopback-bound; service restart/limit checks, boot auto-start, clean and
  forced guest recovery, and a current-build snapshot rollback passed. The
  latest release was healthy immediately after its switch. Rollback between
  distinct application releases and physical-host acceptance remain
  outstanding.

## Current Priorities

According to the roadmap's integration-priority order:

1. **Linux deployment and service lifecycle:** highest-priority work; partial.
   Portable Containerfile/Quadlet contracts pass and some nested-lab checks
   passed. Deployment-script `--check` and `--report` were run on the nested
   guest on 2026-11-05 (read-only; ROCm gate correctly `blocked`; nested-lab
   evidence only). A Containerfile bug that would break any image built from it
   (missing backend `api/` packages) was fixed and a manual release procedure
   written; the redeploy was executed on the nested guest on 2026-11-05 (build,
   import gate, switch all succeeded; docs routes 404; dashboard CSP present;
   loopback-only binds). Whether the missing-`api/` bug caused the 2026-10-19
   failure remains unconfirmed. Boot auto-start and a post-boot housekeeping
   timer were installed and a clean guest reboot recovered both containers to
   healthy without manual start (nested lab only; a forced guest power-off also
   recovered with intact SQLite files; physical power loss and the physical
   host remain untested).
2. **Proxmox identity and authorization:** partial. A real mapped viewer login
   and role denial were tested in the nested lab; HTTPS login and
   proxy-aware lockout behavior were later verified from Windows/iPhone.
   Repeat the full authorized-route, CSRF/origin, and role-boundary checks
   after deployment changes; physical-host acceptance remains gated.
3. **Linux application smoke coverage:** partial. Unauthenticated protected
   route and Origin checks passed, the latest release passed its import gate,
   and containers were healthy with expected root/docs responses. Review
   authenticated application reads and persistent data/log behavior as the
   service account; add optional services only when installed.
4. **Deployment workflow:** the manual release procedure is in use. Signed
   updater Stage 1 (verify-only) is deployed and partly lab-verified with one
   signed bundle; the operator reported Discard appeared to work. Tamper and
   wrong-key rejection, expiry, and large upload through NGINX remain to test.
   Automatic Apply / Stage 2 remains unimplemented; a separate signed
   model-package flow is planned.
5. **Physical-host integration:** blocked until the planned physical Proxmox
   server is available. ROCm/HIP, production networking/proxy, GPU readings,
   reboot/recovery, and target acceptance cannot be established on Windows.
6. **Lower-priority product contracts:** define model-agnostic image-job
   contracts and a workspace-restricted website agent only after permissions,
   workspace boundaries, and recovery are decided. Keep file/command
   integrations disabled until then; a Windows-only image runtime is not a
   priority.

Concepts in the candidate backlog—including network-aware diagnostics, the
conversational household interface, managed Wi-Fi integration, and multi-GPU
workload separation—are not the current implementation priority.

## Future Capabilities

These are plans or concepts, not implemented behavior:

- **Household AI ↔ Maintenance AI Delegation Model:** Household AI is planned
  as the user-facing layer for chat, research, voice, and explanations;
  Maintenance AI is planned as the authoritative engine for diagnostics,
  incident analysis, infrastructure awareness, maintenance workflows, and
  runbook execution. Maintenance AI would primarily communicate through the
  AI Interface/Dashboard, while Household AI could request diagnostics for a
  user and translate persisted findings into audience-appropriate responses.
  The single-GPU Utility/Household/Maintenance model-profile architecture is
  planned separately; this delegated workflow and runbook execution remain
  unimplemented.
- **Maintenance AI Context Inference Layer (Planned):** provide a future
  Maintenance AI with bounded, request-scoped platform state and historical
  operational knowledge so responses can use current evidence without
  permanently expanding model context or VRAM. Future read-only collectors
  should automatically refresh structured SQLite snapshots from authoritative
  sources; Maintenance AI must not write authoritative facts. Reviewed
  runbooks are currently code-defined, not provisioned into SQLite; a versioned,
  safe data import and update path is unresolved. The context layer,
  collectors, historical-case retrieval, and model-assisted diagnosis are not
  implemented; see the
  [roadmap concept](./roadmap/README.md#candidate-backlog-not-scheduled).
- **Network-Aware Diagnostics (Concept):** extend Maintenance AI from server
  health to configured, read-only network and infrastructure evidence.
  Maintenance AI would correlate WAN, LAN, wireless, service, and client
  observations and produce findings; Household AI could request checks on a
  user's behalf and explain results. Least-privilege access, unavailable-data
  handling, evidence history, and separately gated remediation are design
  constraints. No network telemetry provider or end-to-end workflow is
  implemented.
- **Conversational Household Interface (Concept):** Household AI would handle
  chat, research, future voice requests, and user-facing explanations, while
  routing authorized operational questions to Maintenance AI. The future
  design includes an admin-managed Dashboard setting for a shared display
  name shown in Dashboard and conversational interfaces, plus a separate
  phonetic pronunciation for future speech recognition and voice interactions.
  An automatically suggested pronunciation may be reviewed and overridden by
  an administrator. Spoken invocation should use the configured pronunciation
  rather than assume the display name is consistently spoken or recognized;
  a future test may report recognition confidence. The name, pronunciation,
  invocation, and voice recognition do not establish identity,
  authentication, authorization, or privileges. No STT/TTS engine, phonetic
  standard, external pronunciation service, or implementation method is
  selected. Enrollment, consent, audio retention, notification safeguards,
  and listening-state feedback remain to be designed. This remains a concept:
  no name/pronunciation setting, voice-recognition test, voice interface, or
  STT/TTS integration is implemented.
- **Shared Incident Reporting and Administrative Visibility:** extend the
  current bounded diagnostics incident history to attribute household-
  initiated reports, provide authorized administrators a shared operational
  timeline with findings and resolution updates, and let Household AI explain
  findings without duplicating the operational record. This is a concept;
  household attribution and the shared Maintenance AI event workflow are not
  implemented.
- **Voice STT/TTS:** local speech-to-text input and text-to-speech responses
  are candidate components; models, devices, consent, and audio retention are
  undecided.
- **Managed WiFi Integration:** UniFi and TP-Link Omada are evaluation
  candidates, not selected products. Desired capabilities include device
  inventory, client statistics, events, and supported least-privilege
  telemetry.
- **Dual-GPU Service Separation (Concept):** keep Utility and Maintenance AI
  on the planned RX 6800 XT Operations GPU, with Household AI on a future
  second GPU. The RX 9070 XT is an unselected candidate. Concurrent residency,
  routing, and hardware compatibility are not implemented or validated. See the
  [GPU plan](./gpu/gpu-plan.md#potential-future-dual-gpu-service-separation)
  and the
  [roadmap candidate backlog](./roadmap/README.md#candidate-backlog-not-scheduled).
- **Infrastructure Awareness:** add verified read-only inventory and health
  sources for network and household services, starting with explicit scope
  and no configuration changes.
- **Household File Server / NAS (Concept):** provide a simple household
  storage service using up to four SATA HDDs in RAID 5 to increase usable
  capacity while retaining single-drive failure tolerance, with future
  expansion through a NAS box on a dedicated USB 3.1 connection or a separate
  Ethernet-connected NAS, preferably using two 2.5 Gbps links. RAID 5 is not
  a backup; the RAID/filesystem implementation, array-expansion procedure,
  access controls, backup/recovery design, and NAS connection behavior remain
  undecided. No NAS service is implemented.

See the
[roadmap candidate backlog](./roadmap/README.md#candidate-backlog-not-scheduled).

## Repository Guide

### Major directories and files

- `ai-backend/` — FastAPI app assembly, auth, configuration, memory,
  diagnostics, telemetry, model management, Proxmox clients/contracts,
  research, maintenance simulations, and backend unit tests.
- `ai-backend/api/` — Shared runtime/middleware and responsibility-focused
  FastAPI route modules.
- `ai-backend/gpu/` — platform telemetry providers, llama.cpp client, GPU
  placeholders, and DirectML smoke test.
- `ai-backend/tests/` — Python `unittest` suites for auth, API behavior,
  diagnostics, memory, telemetry, Proxmox, configuration, and deployment
  contracts.
- `ai-discord-bot/` — optional Discord client, backend API wrapper, and
  configuration.
- `css/`, `js/`, `index.html` — static dashboard source and native browser
  modules.
- `tests/frontend/` — Playwright browser regression config, static
  allowlisted test server, and UI tests.
- `deploy/quadlet/`, `Containerfile` — rootless backend/dashboard deployment
  definitions and shared image build.
- `scripts/proxmox/` — conservative Proxmox host-preparation preflight and
  optional base-tools installer.
- `scripts/searxng/` — optional SearXNG installation/run support.
- `docs/` — topic-organized architecture, backend, security, operations,
  deployment, diagnostics, GPU, frontend, and roadmap guides.
- Root `.bat` launch/setup files — Windows test environment launchers;
  separate LAN launchers are opt-in HTTPS tests.

### Testing structure

- Python tests use `unittest` under `ai-backend/tests/`.
- Frontend browser tests use Playwright/Chromium under `tests/frontend/` and
  run with `npm run test:frontend`.
- Linux provider fixtures and Containerfile/Quadlet contract tests run on
  Windows but do not execute Linux hardware, Podman, systemd, or reboot
  recovery.
- Follow [testing-environment.md](./operations/testing-environment.md) for
  exact commands and claims supported by each suite.

### Documentation areas

Start at [docs/README.md](./README.md) for the documentation index.
Important guides include the [roadmap](./roadmap/README.md),
[architecture](./architecture/README.md),
[API](./backend/api.md), [authentication](./security/authentication.md),
[diagnostics design](./diagnostics/ai-diagnostics-self-healing.md),
[deployment runbook](./deployment/linux-proxmox-transition.md), and
[GPU plan](./gpu/gpu-plan.md).

## AI Session Handoff

- **Project:** local-first AI Command Interface for household AI and
  operations, developed on Windows and intended for a Linux/Proxmox server.
- **Validated:** Windows application/backend behavior and tests; local
  llama.cpp/Vulkan smoke path and Windows GPU telemetry; DirectML synthetic
  test; browser regressions; portable Python tests; 2026-11-04 live Windows
  browser chat and WSL SearXNG research smoke test; selected loopback
  container lifecycle, reboot recovery, HTTPS proxy access, and read-only
  inventory checks in the nested Proxmox lab; one signed Stage 1 bundle
  verification in the lab.
- **Not validated:** physical-server deployment; Linux live GPU telemetry;
  RX 6800 XT ROCm/HIP inference on Proxmox; physical-target HTTPS/proxy/LAN
  acceptance; reboot recovery after the latest release; rollback between
  distinct application releases; all Stage 1 negative/large-upload tests;
  network telemetry; live maintenance/remediation; voice; or multi-GPU
  operation.
- **Direction:** preserve native browser modules and portable backend
  behavior; continue the roadmap's Linux deployment/service lifecycle and
  nested-lab checks before broad product integrations. Physical-host work
  remains gated on the server.
- **Constraints:** diagnostics and first network integrations remain
  observe-only; backend authorization is authoritative; use least privilege;
  do not turn model output into action authority; do not claim a mock or
  nested-lab result as physical-host acceptance; preserve recovery access and
  persistent data.
- **Hardware plan:** the current plan is a Z590 motherboard with an Intel
  Core i9-11900KF and RX 6800 XT. Confirm the exact motherboard model and
  delivered hardware before host-specific deployment.

For current status, read the [roadmap](./roadmap/README.md) and the focused
guide for the requested subsystem before editing code.
