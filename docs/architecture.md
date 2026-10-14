# System Architecture

## High-Level Diagram

Frontend (Dashboard)
    ↓ REST API
Backend (FastAPI)
    ↓ Internal Modules
GPU / LLM / Bot / System Stats

## Frontend

- Pure HTML/CSS/JS
- Panels for Chat, Models, System Monitor, Virtual Machines, Network Services,
  Game Servers, Discord Bot, Diagnostics, Backend Logs, and Settings
- Polls backend for telemetry and logs
- Sends chat messages and confirms the currently loaded model
- An explicit diagnostic request in dashboard chat runs the same operator-only
  observe-once action as the Diagnostics panel; the local model receives that
  read-only evidence to explain the result
- Sends explicitly selected web-research requests and displays source links
- Displays backend online/offline status

## Backend

- FastAPI application
- Modular design:
  - system_stats.py
  - model_manager.py
  - bot_manager.py
  - gpu/windows_gpu.py
  - gpu/gpu_stub.py
  - gpu/gpu_llm.py
  - gpu/gpu_rocm.py
- Provides REST endpoints for all dashboard features
- Streams local chat replies over WebSocket (`/ws/chat`)
- Enforces dashboard account roles for REST/WebSocket routes and uses a
  separate scoped bearer credential for designated Discord-bot routes
- Persists private per-account conversation history and explicitly
  admin-published shared insights in a separate SQLite database. Admin chat
  and research receive current-admin identity and bounded shared notes; other
  roles and Discord service requests do not.
- Persists bounded observe-only diagnostic observations, incident state, and
  audit events in that local database, restoring open incidents after restart;
  diagnostics remain manually triggered and cannot execute repairs or commands.

## Web Research

- The user explicitly enables Research Web for a message; ordinary chat stays
  local and does not search the web.
- FastAPI queries a self-hosted SearXNG instance, passes a small set of
  untrusted search excerpts to the local llama.cpp model, and returns a
  summary with source links.
- SearXNG must enable JSON output and be configured through
  `SEARXNG_BASE_URL`; the Linux/Proxmox service deployment remains pending.
- Website-building assistance is planned as workspace-scoped work, requiring
  user approval before file changes or command execution.

## Discord Bot

- Python bot connected to backend
- Slash commands for chat, model selection, diagnostics
- Logs streamed to dashboard

## Conversational History

- `ai-backend/memory_store.py` stores dashboard conversations and messages in
  SQLite, separately from authentication records.
- Conversation ownership is scoped to the signed-in identity provider and
  username; other accounts cannot enumerate, read, or delete those records.
- The dashboard can start, resume, and delete conversations, and resumes the
  account's most recently updated conversation after sign-in. Discord bot
  requests remain stateless and are not written to dashboard history.
- Recent context is limited to 20 messages and 12,000 characters. The
  database retains conversation messages until the owner deletes them.
- Admins can explicitly publish and remove operational notes in a separate
  shared-insights table. Only admins can read or manage them; admins receive
  at most 20 newest notes and 8,000 characters of approved notes in chat and
  research context. The Discord service credential and non-admins receive no
  shared admin context.
- Account transcripts remain private and are never automatically extracted
  into shared notes. Shared notes are curated prompt context, not model
  training. There is no automatic fact extraction or semantic/vector
  retrieval. Diagnostic RAG remains a separate planned Phase 3 capability.

## GPU Pipeline

- Windows testing uses llama.cpp Vulkan for local Qwen2.5 1.5B chat and reads
  RX 6800 XT load and dedicated-memory usage from live Windows counters.
- The Proxmox host will run its AI runtime directly and read GPU telemetry
  from its host GPU; Linux provider implementation remains future work.

## Proxmox Deployment

- The dashboard web server, FastAPI backend, and AI runtime are planned to run
  directly on the Proxmox host.
- Host GPU telemetry will read the RX 6800 XT used by the host AI runtime.
- The RX 6800 XT is intended for direct Proxmox host use; GPU passthrough to a
  VM is not part of the deployment plan. Host workloads may share GPU
  resources.
- Linux runtime, GPU telemetry, service management, and safe remote UI/API
  access remain to be validated. See the
  [Linux/Proxmox transition runbook](./linux-proxmox-transition.md).

## Planned Infrastructure Management

The Virtual Machines and Network Services panels have UI planning groundwork,
but are not connected to backend APIs or live infrastructure. The VM panel
shows an empty inventory, guest-detail layout, and unavailable recovery-console
state; it must not imply sample data or controls are live. The intended VM
panel is a full dashboard-driven Proxmox guest lifecycle interface, including
provisioning, configuration, power controls, task status, and a browser console
for guest recovery. Integrate through a backend provider using narrowly scoped
Proxmox API permissions; never expose Proxmox credentials or unrestricted API
access to browser code. Destructive or connectivity-affecting operations need
authorization, explicit confirmation, audit records, and tested recovery.

The primary console requirement is recovering and administering guests when
their normal remote access is unavailable. Design the guest console flow
around Proxmox console access, authenticated sessions, correct terminal
rendering/input, and reliable reconnect/error handling.

The Network Services panel has UI planning views for DHCPv4, DHCPv6, DNS, web
hosting, and routing/firewall; nothing is configured or connected. Final
service placement, address scopes, segmentation, and edge-router ownership
remain undecided. DHCP and routing/firewall operations can sever management
access; keep safeguards and an independent recovery path.

The Game Servers panel is planned to manage isolated game-server workloads.
A family Minecraft server is a candidate first use case, not a selected
deployment. Choose edition/version and management tooling before integrating
live controls; plan player access/allowlisting, resource isolation, world
backups, and restore validation.
