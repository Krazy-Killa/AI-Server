# Linux/Proxmox Transition Runbook

## Purpose and status

Windows remains the active build and prototype environment for shared
application and API behavior. An additional deployment/integration lab is
running Proxmox VE 9.1-1 as a nested Hyper-V guest on the Windows PC. The
dashboard and backend are deployed in that guest for manual, loopback-only
testing through an SSH tunnel. This runbook identifies the platform-specific
changes, decisions, and target-host checks needed to carry the implementation
to Linux/Proxmox. Nested-lab results do not constitute physical-host acceptance.

The current guest deployment is a lab setup: rootless Podman/Quadlet backend
and dashboard unit definitions are installed and active, but neither is
configured for boot auto-start. The backend and dashboard are bound to
loopback-only host ports. NGINX/TLS, LAN application exposure, and inference
runtime are not configured. A dedicated non-root `ai-deploy` SSH account is
available for deployment work; it has no sudo access. Keep guest application
services bound to loopback unless a separately reviewed secure deployment is
requested.

## Read-only VM inventory lab integration

The dashboard can query Proxmox VM and container inventory through
`GET /api/proxmox/vms`. Configure this integration only on the backend:

- Set `PROXMOX_API_URL` to the Proxmox HTTPS origin using a hostname covered
  by the API certificate, for example `https://<pve-hostname>:8006`.
- Create a dedicated Proxmox user and API token for inventory. Use a
  privilege-separated token and grant only the audit/read privileges required
  for cluster resource inventory (normally `Sys.Audit` and `VM.Audit`) at the
  narrowest path that returns the intended guests. Do not grant VM modify,
  power, allocation, console, or storage privileges for this feature.
- Set `PROXMOX_INVENTORY_TOKEN_ID` to `user@realm!token-name` and
  `PROXMOX_INVENTORY_TOKEN_SECRET` to the token secret. Store the secret only
  in `/opt/ai-server/.env`, owned by `ai-server` and mode `0640`.
- If the Proxmox certificate is not trusted by the system, set
  `PROXMOX_API_CA_BUNDLE` to a readable PEM CA certificate. Keep hostname and
  certificate verification enabled; do not use an insecure TLS bypass.
- The nested guest's Proxmox CA lacks the X.509 `keyUsage` extension and
  Python OpenSSL strict verification rejects it. For this isolated lab only,
  `PROXMOX_API_ALLOW_MISSING_CA_KEY_USAGE=true` may be set alongside the
  explicit CA bundle. It disables OpenSSL's strict X.509 extension-policy
  checks for Proxmox connections while retaining trust-chain, validity, and
  hostname verification. Do not carry this compatibility setting into
  physical/production deployment; use a properly issued CA/certificate there.

Restart the backend after configuring settings, then open Virtual Machines and
refresh. A successful response verifies this token can read the intended
inventory; an HTTP 403 indicates that the token's ACL scope or audit privileges
need review. The route makes only a read-only cluster resource request and
returns only guest name, ID, node, type, and status. It does not expose token
credentials, cached/sample inventory, or VM controls.

### Nested-lab verification — 2026-10-16

On the nested Proxmox VE 9.1.1 guest (kernel `6.17.2-1-pve`, Python
`3.13.5`), the installed inventory client ran as `ai-server`, loaded its
protected environment file without displaying credentials, and successfully
retrieved one guest. The returned record had only `name`, `node`, `status`,
`type`, and `vmid`, confirming the configured token can read the requested
cluster inventory. The lab-only missing-CA-keyUsage compatibility option was
enabled with the explicit CA bundle; TLS chain and hostname verification were
retained.

The backend and static dashboard were also started in temporary, non-persistent
`systemd-run` units as `ai-server`; the static page used Python's standard
library HTTP server. Both reached active state with successful exit status,
bound only to `127.0.0.1`, and returned HTTP 200 for the dashboard root and
backend OpenAPI document. The unauthenticated inventory route returned HTTP
401, and Windows-side probes could not connect to ports 8000/8001. Both
temporary units were stopped and the ports were confirmed closed.

Podman 5.4.2 was subsequently installed for rootless `ai-server` operation.
Digest-pinned backend and static-dashboard images and Quadlet definitions were
built and started. Both containers passed health checks; the dashboard and
OpenAPI returned HTTP 200, the anonymous inventory request returned HTTP 401,
and host ports remained loopback-only. The units have bounded restart
behavior, but no boot target is configured. A direct host-side inventory read
previously succeeded. Container DNS and CA-file readability were confirmed,
but the container's initial connection to the guest LAN address on port 8006
was refused. A throwaway container test verified that
`--add-host=pve.mshome.net:host-gateway` reaches the API through Podman's
`host.containers.internal` gateway (`169.254.1.2`). This mapping has been added
to the backend Quadlet and deployed. After restarting the backend, the live
inventory client inside the container returned one guest with only the
expected `name`, `node`, `status`, `type`, and `vmid` fields. The backend and
dashboard remained active and healthy with loopback-only host ports. The
configured API hostname and TLS hostname verification were retained.

These results are nested-lab evidence only; physical-host acceptance remains
separate. Boot auto-start, reboot/failure recovery, NGINX/TLS, and LAN
application exposure have not been validated.

The current target is a Proxmox VE 9.x host with one AMD RX 6800 XT, with
services managed using Podman and Quadlet. The RX 6800 XT is currently in the
Windows development machine and is planned to move to the server after a
replacement GPU is acquired. This is a target design, not an installed or
compatibility-tested stack.

## Intended Linux/Proxmox stack

The planned components are:

- **GPU compute:** AMD ROCm and HIP.
- **ROCm placement:** install the ROCm/HIP stack on the Proxmox host; GPU
  driver, kernel, and device setup therefore require host-specific validation.
- **LLM inference:** llama.cpp built with ROCm support, exposing `llama-server`
  to the local backend.
- **Vision inference:** ONNX Runtime with its ROCm Execution Provider.
- **Image generation:** ComfyUI with a ROCm-compatible PyTorch/runtime setup.
- **Service packaging and lifecycle:** Podman containers managed by Quadlet
  systemd units where containerization is appropriate.
- **Web entry point:** NGINX serving the dashboard and reverse-proxying the
  protected backend endpoints.
- **Vector storage:** Qdrant, managed as a service/container.

The exact point release, kernel, ROCm/HIP and application versions, container
boundaries, persistent storage paths, network bindings, and installation
sources remain to be recorded and verified before generating version-pinned
installation steps. Treat ROCm/HIP on the planned RX 6800 XT + Proxmox host as
**experimental and community-supported only**: AMD's current support matrix
does not list this GPU/OS combination. Community reports cover related
`gfx1030` cards on other Linux distributions, but do not prove native ROCm
operation on this host. The GPU is intended for direct host use; assigning it
to a VM via passthrough is not part of this design. See the
[experimental community evidence and limitations](./gpu-plan.md#experimental-rx-6800-xt-community-evidence).
Do not assume the Windows Vulkan results establish ROCm, HIP, or ROCm telemetry
compatibility.

## Provisional host hardware and storage plan

This planning outline is not a finalized bill of materials. The exact AMD CPU
and core count remain open; choose them against the intended VM count and
concurrent workloads, including Proxmox overhead and host services. Start with
32 GB system RAM, with a possible upgrade to 64 GB after measuring actual
headroom. System RAM does not replace or add to the RX 6800 XT's 16 GB VRAM.

The initial storage target is a 2 TB NVMe drive for Proxmox/application
storage, active or write-intensive VM disks, databases, and frequently used
models. Additional NVMe devices may be added later. Larger HDDs are intended
for bulk file data and lower-I/O VMs such as DHCP and DNS. A file-hosting VM
can keep its OS and applications on NVMe while storing bulk files on an HDD
pool. Expect HDD-backed VMs to have slower boots and disk-intensive operations.

The model library may be tiered between HDD capacity and NVMe: keep frequently
used or pinned models on NVMe and less-used models on HDD. The eventual model
manager must verify copies and avoid moving models while loaded or in use.
This tiering chiefly reduces model access and load time; it does not make
inference faster once the model is loaded.

An HDD RAID/redundant pool is being considered, but the drive count, exact
layout, controller mode, usable capacity, filesystem, and expansion method
have not been selected. Storage redundancy does not replace separate backups;
document and test backup restoration. Finalize storage ownership and pool
design before creating production VM disks or file shares.

## What is portable now

- The dashboard is static HTML, CSS, and JavaScript.
- The API, chat client, model inventory/switching logic, and web-research
  integration are Python and use the standard library plus the packages in
  `ai-backend/requirements.txt`.
- CPU and system RAM percentages are read through `psutil`.
- Chat and research call local HTTP services. Their URLs are configurable
  using `LLAMA_CPP_BASE_URL` and `SEARXNG_BASE_URL`.
- The model manager already has POSIX process handling and defaults to a
  Linux llama.cpp device name of `ROCm0`. This is not proof that the eventual
  llama.cpp build exposes that device name or that ROCm supports the chosen
  OS/kernel/GPU combination.

The Windows build is the working prototype for shared application behavior;
these portability points are not merely mocks. However, Windows verification
does not establish Proxmox runtime behavior. Validate OS-, hardware-, network-,
and service-specific components using the staged host checks and end-to-end
acceptance below.

## Linux blockers to close

1. **Record the operating-system target.** Services are intended to run on
   the Proxmox VE 9.x host, managed through Podman/Quadlet. Record the exact
   Proxmox point release, kernel, boot mode, GPU ownership, storage locations,
   and recovery access before driver work. The GPU is for direct host use;
   moving services into a guest or assigning the GPU via passthrough would
   change the architecture and is not planned.
2. **Investigate the experimental GPU software stack for the exact target.**
   Check the current official AMD ROCm support matrix for the selected
   Proxmox release/kernel, RX 6800 XT (and any additional GPUs), and ROCm/HIP
   version. The current combination is not listed as officially supported;
   community reports are leads, not a support guarantee. Only proceed with a
   reviewed recovery plan and explicit acceptance of the experimental risk.
   Then build llama.cpp with the ROCm backend and record its pinned revision,
   build flags, device name, and smoke-test results. Windows Vulkan test
   results do not certify this build.
3. **Implement a Linux telemetry provider.** `system_stats.py` currently
   imports `gpu.windows_gpu`; that provider intentionally returns unavailable
   on non-Windows systems. `gpu/gpu_rocm.py` is only a stub. Implement a Linux
   provider for the same API fields, with truthful adapter identity, GPU
   utilization, VRAM used/total, status, and diagnostic error. Report `null`
   and `unavailable` if the selected telemetry source cannot provide a live
   measurement; do not substitute simulated values. Verify idle and
   inference readings against an independent host tool.
4. **Decide and verify how browsers reach the API.** `js/app.js` uses
   `http://127.0.0.1:8000` when opened as a local file, uses the dashboard
   host's port 8000 when the local dashboard is served on port 8001, and uses
   the dashboard's own origin otherwise. A deployment may set
   `window.AI_SERVER_API_BASE` before the app loads. Choose a server-reachable
   API origin or same-origin reverse proxy and test from a separate LAN
   client. Do not expose the llama.cpp port to the LAN.
5. **Validate deployment security before LAN use.** Dashboard-owned local
   accounts, explicitly mapped Proxmox identities, role-protected REST and
   WebSocket access, session cookies, CSRF checks, and origin restrictions are
   implemented and tested in the Windows environment. This does not validate
   real Proxmox ticket behavior or the production proxy. Do not expose the
   API, model-switch endpoint, or llama.cpp to an untrusted network. Before
   remote/LAN access, validate Proxmox login and role mappings as applicable,
   HTTPS and secure-cookie behavior through the chosen proxy, firewall rules,
   browser access from a separate client, and the model-switch policy.
6. **Create Linux service management.** The `.bat` scripts only support
   Windows. Prepare Podman/Quadlet units for containerized services and
   systemd units or documented host environments for components that need
   direct host/GPU access. Cover llama-server, backend, NGINX, Qdrant,
   ComfyUI, and any ONNX Runtime service actually integrated. Use a dedicated
   service account, explicit environment files, controlled startup ordering,
   persistent volumes/logs, health checks, and a least-privilege GPU device
   access policy. Ensure model switching can inspect and stop only its own
   llama-server process.
7. **Set Linux paths and permissions.** Configure `AI_SERVER_MODEL_DIR` and
   `LLAMA_SERVER_EXECUTABLE`; ensure the service account can read model files,
   write its logs, and access the selected GPU device. Keep models and
   llama.cpp build artifacts outside the source checkout and back them up or
   document how to reacquire them.
8. **Install Linux-specific AI packages separately.** Windows DirectML
   packages in `ai-backend/requirements-windows.txt` and
   `ai-discord-bot/requirements-windows.txt` are not the Linux install path.
   Install only the common `requirements.txt` dependencies first. Pin and
   validate the selected ONNX Runtime ROCm Execution Provider and ComfyUI
   ROCm-compatible dependency/model versions; neither is currently a
   production integration.
9. **Configure optional services and secrets.** Deploy SearXNG and enable its
   JSON response format before enabling web research. Set its URL through
   `SEARXNG_BASE_URL`. If the Discord bot is enabled, set a real token outside
   source control and set `AI_SERVER_API_BASE` to a reachable API address.
10. **Integrate and verify the existing application as a whole.** Run the
    backend unit tests on Linux; start each service under its intended
    supervisor with persistent paths; verify backend-to-llama.cpp model
    discovery, switching, chat and streaming; verify dashboard access and
    WebSocket traffic through the selected reverse proxy; verify logs and the
    observe-only diagnostics API/dashboard; then test optional SearXNG
    research and Discord commands/heartbeat when configured. Exercise service
    restart and host reboot recovery. Record failures and exact tested
    versions; do not mark Windows-only, mocked, or planned features as
    integrated.

## Deployment configuration inventory

| Setting | Current default/behavior | Linux deployment action |
| --- | --- | --- |
| `AI_SERVER_MODEL_DIR` | Windows `%LOCALAPPDATA%\AI-Server\models`; otherwise `~/AI-Server/models` | Set an explicit persistent model directory. |
| `LLAMA_SERVER_EXECUTABLE` | Windows build path, or `llama-server` on PATH when `LOCALAPPDATA` is absent | Set the absolute Linux executable path. |
| `LLAMA_CPP_BASE_URL` | `http://127.0.0.1:8080` | Keep loopback when API and runtime share the host. |
| `LLAMA_CPP_DEVICE` | `Vulkan0` on Windows; `ROCm0` otherwise | Set to the exact device identifier reported by the deployed build. |
| `LLAMA_CPP_GPU_LAYERS` | `99` | Confirm available VRAM and inference behavior; tune if needed. |
| `LLAMA_CPP_CTX_SIZE` | `4096` | Confirm memory use and desired context length. |
| `SEARXNG_BASE_URL` | `http://127.0.0.1:8888` | Set the reachable SearXNG endpoint and enable JSON output. |
| `AI_SERVER_API_BASE` | Discord bot defaults to `http://127.0.0.1:8000` | Set it if the bot runs on another host or guest. |
| `DISCORD_TOKEN` | Placeholder default | Supply through a protected environment file only if using the bot. |

Container image tags, Quadlet unit names, Qdrant data volume, ComfyUI model
directories, and NGINX hostnames/certificates must be selected in the
deployment-specific configuration; do not put secret values in unit files
tracked in the repository.

## Host preparation script

[`scripts/proxmox/prepare-ai-host.sh`](../scripts/proxmox/prepare-ai-host.sh)
is an initial, deliberately conservative bootstrap:

- Run `bash scripts/proxmox/prepare-ai-host.sh --check` for a read-only
  inventory of the installed distribution, Proxmox release, running kernel,
  architecture, and detected AMD display device. The script checks AMD's live
  [ROCm compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
  and fails closed unless the RX 6800 XT, Proxmox VE 9, and installed kernel
  family are explicitly listed.
- Run `bash scripts/proxmox/prepare-ai-host.sh --report` to create
  `ai-server-host-report.md` in the current directory, or pass a new output
  path with `--report /path/to/report.md`. This read-only snapshot records
  platform/kernel, CPU and memory, storage capacity/models, display device and
  driver details, GPU kernel-module and Secure Boot status, relevant installed
  package versions, selected service states, and the AMD compatibility-check
  result.
  The report is created with owner-only permissions and the script refuses to
  overwrite an existing destination. It excludes hostnames, usernames,
  network addresses, serial numbers, credentials, environment variables,
  configuration contents, and logs. It is not uploaded; the report mode does
  make the same read-only request to AMD's public compatibility matrix as
  `--check`. Review it before sharing. It supports implementation planning but
  does not replace live integration tests or prove that host features work.
- Run `sudo bash scripts/proxmox/prepare-ai-host.sh --install-base` only on
  the server, after reviewing its simulated apt plan. It installs common
  build/runtime and host tools and adds headers for the exact running kernel
  only when an apt candidate exists. It refuses a transaction that proposes
  replacing or removing a kernel package.
- Run `sudo bash scripts/proxmox/prepare-ai-host.sh --install-searxng` on the
  server to install SearXNG (the web-research backend). It runs as the
  unprivileged `searxng` user under systemd, bound to `127.0.0.1:8888`, and is
  independent of the GPU gate. The planned Podman/Quadlet layout may replace
  this systemd service later; the loopback address and JSON format stay the
  same, so `SEARXNG_BASE_URL` does not change.
As of 2026-10-12, AMD's current compatibility matrix does not list the
RX 6800 XT or Proxmox VE 9 as officially supported for ROCm. Therefore the
script must not be treated as permission to install ROCm on this target, and
the GPU compute stack remains gated. This is an explicit limitation, not a
claim that community-enabled ROCm configurations cannot work.

The script does not yet install ROCm/HIP, llama.cpp, ONNX Runtime ROCm EP,
ComfyUI, Qdrant, or production Quadlet/NGINX configuration. Those steps need
version pins and an install method verified for the actual host; do not
silently install floating latest releases on a Proxmox hypervisor.

The backend and Discord bot load project-root `.env` values with
`python-dotenv` when they start; shell-provided environment values take
precedence. The Windows `.bat` launchers do not source `.env` for their
llama.cpp command-line flags. See [configuration documentation](./configuration.md)
for the template and limitations.

## Recommended transition sequence

1. **Inventory and decision record:** document the Proxmox VE 9.x point
   release/kernel, host deployment choice, RX 6800 XT device, network
   exposure, storage, recovery method, and desired component versions. Do not
   begin ROCm installation until the exact target combination is checked
   against current upstream support information.
2. **Prepare the host safely:** establish console/SSH recovery, backups, and
   rollback; update the host using the chosen Proxmox procedure. Review an
   idempotent preflight/install plan before enabling package repositories,
   changing kernel/driver packages, or granting GPU device access.
3. **Validate the compute stack:** install a verified ROCm/HIP stack on the
   host and confirm the GPU is enumerated. Build llama.cpp with its ROCm
   backend; run a small-model inference through `llama-server`, then test
   Qwen2.5-Coder-7B and Qwen3-8B individually with VRAM headroom and
   repeatable prompts.
4. **Port and validate telemetry:** implement provider selection by platform,
   verify the API response schema is unchanged, and test idle/inference load
   and memory against an independent tool. Test missing permissions and
   missing telemetry utilities; the dashboard must show unavailable readings
   explicitly.
5. **Deploy supervised services:** configure model directory, runtime URL,
   exact device, backend environment, startup dependencies, logs, service
   account, and health checks. Validate model switching, startup failure,
   rollback to the previous model, and reboot recovery.
6. **Deploy the web interface safely:** choose same-origin proxy or a
   configured reachable API URL; test chat, model inventory, switching, and
   telemetry from both the host and a separate client. Keep llama.cpp
   loopback-only; restrict API reachability until authentication and network
   policy are in place.
7. **Deploy supporting services in stages:** install Podman/Quadlet and
   validate one unit at a time. Bring up NGINX and Qdrant with persistent
   storage and restricted network bindings. Add ONNX Runtime ROCm EP and
   ComfyUI in isolated, version-pinned environments/containers after
   compatibility checks; verify each against a representative workload.
   Deploy SearXNG and Discord only after their endpoint and secret handling
   are configured.
8. **Record operational handoff:** save exact versions, commands/build flags,
   service names, paths, environment variable names (not secret values),
   firewall/proxy design, GPU evidence, test results, backup/restore steps,
   and known limitations in this repository's deployment docs.

## Linux acceptance checklist

- [ ] Exact Proxmox VE 9.x point release/kernel and host deployment decision
      documented.
- [ ] RX 6800 XT driver/runtime combination verified against current upstream
      support and device enumerated by the chosen llama.cpp build.
- [ ] ROCm/HIP llama.cpp `llama-server`, ONNX Runtime ROCm EP, and ComfyUI
      versions/builds recorded; each installed component passes its own
      GPU-backed smoke test.
- [ ] Podman/Quadlet units survive restart/reboot with persistent data and
      least-privilege GPU access; NGINX and Qdrant expose only intended
      interfaces.
- [ ] Small-model inference and both 7B/8B models tested individually; logs
      confirm GPU offload and adequate VRAM headroom.
- [ ] `/api/system` returns valid CPU/RAM and live GPU fields; unavailable
      GPU measurements are `null`, with an explicit status/error.
- [ ] `/api/chat`, `/api/models`, model switching, and recovery tested after
      service restart and host reboot.
- [ ] Linux backend unit tests pass; backend, llama-server, and dashboard
      integrate under their documented service lifecycle with persistent
      model/log paths and correct ownership.
- [ ] Dashboard works from a separate client; API origin, proxy, CORS,
      WebSocket routing, authentication, firewall, and TLS decisions
      documented and tested.
- [ ] Observe-only diagnostics API and dashboard operate against live host
      checks and never perform remediation; verify backend logs and all other
      protected routes remain accessible only to their authorized dashboard
      roles through the deployed proxy.
- [ ] llama.cpp remains loopback-only and only the intended services are
      reachable from approved networks.
- [ ] SearXNG, if deployed, returns JSON results; secrets are stored outside
      the repository.
- [ ] Discord bot, if deployed, reaches the configured API, reports heartbeat,
      and handles intended commands without exposing its token.
- [ ] Backup/restore and recovery access verified; versions and known gaps
      recorded for handoff.

## Related documentation

- [GPU integration plan](./gpu-plan.md)
- [Windows testing environment](./testing-environment.md)
- [Architecture](./architecture.md)
- [Backend API](./api.md)
