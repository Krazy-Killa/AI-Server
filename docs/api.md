# Backend API Documentation

Base URL:
http://127.0.0.1:8000

---

## Authentication

The browser uses an application session cookie. Except for `GET /`,
`POST /api/auth/login`, and `GET /api/auth/status`, API routes require a
valid session and a role allowed for that route. Cookie-authenticated
state-changing requests require `X-CSRF-Token` from `/api/auth/status` and an
allowed `Origin`. Browser clients must use `credentials: "include"`.

`POST /api/auth/login`

```json
{
  "provider": "local",
  "username": "alice",
  "password": "..."
}
```

Use `"provider": "proxmox"` for Proxmox VE credentials. A successful login
sets an HttpOnly application-session cookie and returns identity, role, and a
CSRF token. Proxmox users without an explicit local role mapping are denied.
Credential failures return a generic error.

`GET /api/auth/status` returns the authenticated identity, role, and CSRF
token; unauthenticated clients receive `{"authenticated": false}`.
`POST /api/auth/logout` revokes the current session and clears its cookie.

The Discord bot uses a separate bearer credential and is limited to its
machine API routes. It does not use or receive a dashboard user's session.
The normal development backend is loopback-only. Optional Windows mobile
testing uses the dedicated LAN launcher with HTTPS on a single configured
private IPv4 address, an exact configured CORS origin, and Secure cookies;
this does not replace production HTTPS proxy and firewall validation. See
[Authentication & Session Management](./authentication.md) and the
[mobile LAN testing guide](./testing-environment.md#test-the-dashboard-from-a-mobile-device-on-the-lan).

## Authorization roles

- `viewer`: read-only status, models, and observe-only diagnostic history.
- `operator`: viewer access plus chat/research, model selection, and manual
  diagnostics observations, including explicit diagnostic requests in chat.
- `admin`: operator access plus backend logs, bot restart, and management of
  explicitly published shared admin insights and the shared AI Interface.

The local CLI manages accounts and explicit Proxmox identity-to-role mappings.
The API does not expose account administration.

## System Endpoints

GET /api/system  
Requires the viewer role.
Returns the backend host's `node_name`, CPU and RAM telemetry, plus GPU load.
On Windows, `gpu` is the live
utilization of the busiest engine on the detected AMD discrete GPU. The
response includes `gpu_adapter`, `gpu_engine`, `gpu_status`, and `gpu_error`;
`gpu` is `null` when the live reading is unavailable. `vram_used` and
`vram_total` report live dedicated-memory usage and device-local capacity in
GiB; they are `null` if GPU telemetry is unavailable. `activity_mode` is
`diagnostics` while a read-only observation is running, or `null` while idle.
The dashboard gives this active work precedence over its local/research chat
selection. `maintenance` is recognized by the dashboard but is not currently
reported because a maintenance lifecycle has not been implemented.

GET /api/gpu  
Requires the viewer role.
Returns the GPU load and telemetry status fields from `/api/system`.

---

## Diagnostics (Observe-only)

Diagnostics are explicitly triggered and read-only. No scheduler, repair
action, or command execution is exposed. Observations, incident state, and
audit events are stored in the local SQLite database configured by
`AI_SERVER_MEMORY_DB_PATH` and survive backend restarts. The database retains
the latest 200 observations, the latest 1,000 audit events, and all open
incidents plus up to 500 resolved incidents. These endpoints are available to
the viewer role. Running an observation requires the operator role.
Resource threshold state is evaluated only when an observation is explicitly
run. CPU >=90% and RAM >=90% must persist across observations for 120 seconds;
log-volume free space <=10% must persist for 60 seconds. Recovery requires
CPU <=80%, RAM <=85%, or free space >=15%, respectively, for 60 seconds.
Observations more than 300 seconds apart reset pending/recovery duration
confirmation. These sampled intervals are evidence only and do not establish
continuous conditions between observations.

GET /api/diagnostics/status
Returns `mode` (`observe_only`), `storage` (`sqlite`), the latest
observation and status (`not_run`, `healthy`, `degraded`, or `unknown`), and
incident counts.

GET /api/diagnostics/observations?limit=20
Returns recent observations, limited to 1–100 items.

GET /api/diagnostics/incidents?status=all&limit=100
Returns recent incidents filtered by `all`, `open`, or `resolved`, limited to
1–500 items.

GET /api/diagnostics/report?observation_id=obs_...
Requires the viewer role. Returns a JSON evidence report for a retained
observation, including its health checks, resource snapshot, threshold
evidence, and related incidents as they existed at that observation. Historical
incident fields are reconstructed from the selected observation's degraded
checks and active threshold evidence, with incident metadata used only when its
recorded interval contains the observation. Unknown or expired observation IDs
return 404. Report generation reads recorded in-memory history only: it does
not run probes, trigger a new observation, or write persistent state. The
dashboard's **Download report** action downloads the latest recorded
observation.

POST /api/diagnostics/observe
Runs the configured health checks and resource sampling once, records the
observation and incident transitions, and returns the observation. It does
not perform remediation. The dashboard exposes this action through its
Diagnostics panel's **Run observation** button. It requires the operator role.
An operator can also explicitly ask the dashboard chat to run/check
diagnostics. Such a request runs one read-only observation and provides its
results to the local model for explanation. Informational questions (for
example, "How do I run diagnostics?") do not start an observation. The Discord
bot service credential does not gain this capability through chat.

GET /api/diagnostics/runbooks?platform=proxmox-ve&signal=proxmox.inventory.empty
Requires the viewer role. Returns bundled reviewed runbooks, optionally
filtered by platform and signal. `limit` is 1–100 (default 50).

GET /api/diagnostics/runbooks/{runbook_id}
Requires the viewer role. Returns one bundled reviewed runbook or HTTP 404.
Runbook steps are manual diagnostic guidance; the endpoint does not execute
them.

GET /api/diagnostics/knowledge/search?query=inventory+403&platform=proxmox-ve
Requires the viewer role. Searches only bundled reviewed runbooks with
deterministic local lexical matching. `query` is required (1–160 characters);
`limit` is 1–25 (default 10). Historical incidents and drafts are not
searched. These read-only routes do not run observations or model inference.

---

## AI Interface

The AI Interface is an admin-only server console with one persistent transcript
shared among administrators. Turns are attributed to the signed-in admin.
Private AI Chat conversations are stored separately and are never loaded into
the shared console context. Do not enter private chat content, personal
details, passwords, or secrets in the shared console.

GET /api/interface/conversation
Returns the single shared transcript, with author attribution for user turns.

POST /api/interface/chat
Requires the admin role and a valid CSRF token/origin. Body:
`{"message": "Check backend health"}`

The local model may run a read-only diagnostic observation when explicitly
requested. Other server commands, configuration changes, repairs, and
maintenance actions are not implemented. The shared conversation is not a
general Chat/Research workspace.

---

## Chat Endpoints

POST /api/chat  
Requires the operator role.
Body:
{
  "message": "Hello",
  "conversation_id": "optional conversation UUID"
}

Returns:
- AI response from the local llama.cpp server, generated by the loaded model.
- `latency_ms`: end-to-end generation request time.
- `tokens`: generated token count when reported by llama.cpp.
- When `conversation_id` is provided, stores this account's user/assistant
  messages and includes bounded recent conversation turns in model context.

Returns HTTP 503 with a diagnostic message when the local llama.cpp server is
not reachable or does not return a valid chat response.

Conversation history belongs to the authenticated account (provider plus
username). Requests made using the Discord bot service credential are not
persisted. An invalid, deleted, or another account's conversation ID returns
HTTP 404.

For admin sessions only, dashboard chat also receives the signed-in admin's
identity and the newest explicitly published shared insights as system
context. Private transcripts remain account-scoped and are never used as
another admin's context. Shared context is limited to 20 notes and 8,000
characters. This is retrieved prompt context, not model training. The Discord
bot service credential and non-admin sessions receive no shared admin context.

GET /api/memory/conversations?limit=50
Requires the operator role. Lists up to 100 conversations belonging only to
the current account, newest first, with title, timestamps, and message count.

POST /api/memory/conversations
Requires the operator role. Creates an empty conversation and returns its UUID.

GET /api/memory/conversations/{conversation_id}
Requires the operator role. Returns that account's full saved message history.
Messages include role, content, creation time, and optional research source
links.

DELETE /api/memory/conversations/{conversation_id}
Requires the operator role. Permanently deletes that account's conversation
and all its messages.

GET /api/memory/shared-insights
Requires the admin role. Lists published operational notes shared across
admins, with publisher identity and creation time.

POST /api/memory/shared-insights
Requires the admin role and a valid CSRF token/origin. Body:
`{"content": "Operational note to share with admins"}`

Publishes one explicitly approved note (1–2,000 characters). The store is
limited to 100 notes; at capacity, the API returns HTTP 409 until an admin
removes an outdated note. No transcript or chat message is implicitly
published.

DELETE /api/memory/shared-insights/{insight_id}
Requires the admin role and a valid CSRF token/origin. Removes a shared note;
any admin may remove a published note. Returns HTTP 404 if it does not exist.

POST /api/research  
Requires the operator role.
Body:
{
  "message": "What changed in the latest Python release?"
}

Searches through the configured SearXNG instance, asks the local model to
summarize up to five results, and returns `reply`, `sources`,
`search_latency_ms`, `latency_ms`, and `tokens`. Each source includes `title`,
`url`, `snippet`, and `page_status` (`fetched`, `excerpt_only`, or
`not_fetched`). The backend attempts full-page retrieval for at most the first
three sources; the rest use their SearXNG excerpt. Fetches accept only public
HTTP(S) destinations on ports 80/443, resolve and pin public IP addresses,
revalidate every redirect (maximum three), require an HTML content type, and
bound each response to 1 MB and five seconds. Failed, unsafe, oversized, or
non-HTML fetches fall back to the search excerpt. Fetched page text and search
excerpts are explicitly untrusted evidence; instructions in them are never
followed. For admin sessions, explicitly published shared admin insights and
the current admin identity are included alongside the research safety prompt.
Returns HTTP 503 if SearXNG is unavailable or its search response is unusable;
model-stream errors are reported in-band by the streaming endpoint below.
Configure the SearXNG base URL with `SEARXNG_BASE_URL` (default
`http://127.0.0.1:8888`); its JSON output must be enabled in the SearXNG
configuration. Queries may be forwarded by SearXNG to its upstream search
engines; do not include secrets or private data.

POST /api/research/stream
Requires the operator role and a valid CSRF token/origin. Uses the same request
body and bounded page-retrieval policy as `POST /api/research`; the browser
uses this endpoint for AI Chat's Research Web mode. Returns Server-Sent Events
(`text/event-stream`):

- `event: sources` with `{"sources": [...], "search_latency_ms": 123}` before
  answer generation. Each source includes `page_status`.
- `event: token` with `{"content": "..."}` for each generated text chunk.
- `event: done` with `{"latency_ms": 1234}` after the completed assistant turn
  and its citations have been persisted when a conversation ID was supplied.
- `event: error` with `{"detail": "..."}` if generation or persistence fails
  after streaming has begun. Partial replies are not saved as completed turns.

Search/preparation failures return HTTP 503 before the stream begins.
Authenticated conversation IDs use the same account-scoped history and admin
shared-context behavior as `POST /api/research`.

WS /ws/chat  
Requires an authenticated operator session and an allowed dashboard origin.
Streams a local chat reply as llama.cpp generates it. The connection stays open
for multiple requests, one at a time. Browsers must connect from an origin in
`AI_SERVER_CORS_ORIGINS`; connections from other origins are rejected.

Client sends `{"message": "Hello", "conversation_id": "optional UUID"}` (1
to `AI_SERVER_MAX_CHAT_CHARS` characters, default 4000). When a conversation
ID is supplied, the backend persists the turn and uses up to the 20 most
recent saved messages, bounded to 12,000 characters, as prior model context.
Admin sessions also receive the signed-in admin identity and bounded,
explicitly published shared insights; private transcripts from other accounts
are not retrieved.

Server sends JSON messages:
- `{"type": "token", "content": "..."}` for each text chunk.
- `{"type": "done", "latency_ms": 1234}` when the reply is complete.
- `{"type": "error", "detail": "..."}` for invalid input (the connection stays
  open) or when llama.cpp is unreachable or returns an invalid stream.

Closing the connection mid-reply stops generation. The dashboard uses this
endpoint for ordinary chat and falls back to `POST /api/chat` if the stream
cannot start. AI Chat's Research Web mode uses `POST /api/research/stream`.

---

## Model Endpoints

GET /api/models  
Requires the viewer role.
Discovers `.gguf` files in `AI_SERVER_MODEL_DIR` (or the platform default)
and returns each file's name, filename, format, size, and load status. The
response also includes `active_model`, `runtime_status`, `runtime_error`, and
`model_directory`. A model is marked loaded only when llama.cpp's `/props`
reports that exact file path.

POST /api/model/select  
Requires the operator role.
Body:
{
  "model_id": "qwen2.5-1.5b-instruct-q4_k_m.gguf"
}

Selection restarts the loopback
llama.cpp server with the requested installed model, waits for `/props` to
confirm that model is loaded, then returns:

```json
{
  "success": true,
  "active_model": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
  "restarted": true
}
```

Selecting a model that is not installed returns HTTP 404. Unsafe or failed
server restarts return HTTP 503; if loading the requested model fails, the
backend attempts to restore the previously active model and reports that
recovery outcome in the error detail.

## Virtual Machines and Network Services

`GET /api/proxmox/vms`
Requires an authenticated dashboard session with the viewer role or higher.
Reads a filtered VM/container inventory from the configured Proxmox API with
the backend-only `PROXMOX_INVENTORY_TOKEN_ID` and
`PROXMOX_INVENTORY_TOKEN_SECRET`. Proxmox credentials are never sent to the
browser.

When the provider is not configured, returns HTTP 200 with explicit state:

```json
{
  "configured": false,
  "status": "not_configured",
  "guests": [],
  "count": 0,
  "observed_at": null
}
```

When connected, returns `configured: true`, `status: "connected"`, a `guests`
array containing only `name`, `vmid`, `node`, `type`, and `status`, the guest
`count`, and a UTC `observed_at` timestamp. Upstream failures return HTTP 503;
the endpoint does not substitute cached or sample inventory. The provider rejects redirects, verifies TLS certificates, and makes only a
read-only cluster-resource request. For the nested Proxmox lab only, Python
may reject the Proxmox-generated CA because it lacks the X.509 `keyUsage`
extension. The explicit `PROXMOX_API_ALLOW_MISSING_CA_KEY_USAGE` compatibility
setting relaxes OpenSSL's strict X.509 extension-policy checks but does not
disable configured CA-chain, certificate-validity, or hostname verification.
Do not use it for physical/production deployment.

The portable read-only and proposal-only contracts for VM, network-service,
and game-server integrations are documented in
[infrastructure-contracts.md](./infrastructure-contracts.md). Proposal
contracts are not HTTP routes and have no execution provider.

The VM dashboard refreshes the inventory when opened and on explicit refresh.
It has no create, power, snapshot, configuration, or console operations.
DHCPv4, DHCPv6, DNS, web-hosting, and routing/firewall remain planning-only;
no network-service monitoring or management API is implemented. When
implemented, the initial network-service integration is intended to be
observe-only and may report services hosted inside VMs; VM inventory by itself
does not verify service health. It must not expose mutation endpoints or
automatic remediation in that initial scope. Any later action-capable API
requires a separately reviewed and explicitly authorized autonomy phase.

---

## Discord Bot Endpoints

GET /api/bot/status  
Requires the viewer role for dashboard sessions. The Discord bot's machine
credential may also call this route.
Returns:
- Online/offline
- Latency
- Active model

GET /api/bot/logs  
Requires the admin role for dashboard sessions.
Returns:
- Recent bot log lines

POST /api/bot/heartbeat
POST /api/bot/logs
Discord-bot-only machine routes; both require the configured `AI_SERVER_BOT_API_TOKEN` service credential. The heartbeat reports bot latency/commands and returns any pending restart request. The log endpoint records a short, content-free operational event. These routes reject dashboard session credentials.

POST /api/bot/restart
Requires the admin role and CSRF protection. Requests a bot restart and
returns HTTP 409 when the bot is offline.

---

## Vision / Embedding (Stub)

GET /api/vision
Returns the current vision-analysis stub response; viewer role required.

POST /api/vision/run
Accepts image bytes and returns the current image-model stub response;
operator role required.

POST /api/embed
Requires the operator role or scoped Discord-bot credential. Returns the
current embedding stub response.

POST /api/llm
Operator-only alias for the local chat endpoint.
