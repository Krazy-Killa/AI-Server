# AI-Powered Diagnostics & Self-Healing

> Status: **design specification** (not yet implemented). Endpoints, modules and
> tables described here are proposals for review and phased implementation.

This document specifies an AI diagnostic agent that monitors the AI-Server,
detects problems, attempts safe automatic corrections, and produces detailed
failure reports when user intervention is required.

Existing building blocks it relies on: the FastAPI backend (`ai-backend/main.py`),
`system_stats.py` (CPU/RAM/GPU telemetry), `model_manager.py` (model discovery
and llama.cpp lifecycle), `bot_manager.py` (Discord bot process control), the
llama.cpp server, the optional SearXNG instance, the Discord bot
(`ai-discord-bot/bot.py`) and the browser dashboard (`index.html`, `js/`, `css/`).

---

## 1. System Architecture

### 1.1 Overview

The **Diagnostic Agent** is a background service inside (or beside) the backend
that runs a continuous loop:

```
Observe -> Detect -> Diagnose -> Decide -> Act (or Escalate) -> Verify -> Record
```

It is deliberately a **hybrid** system. Deterministic rules, runbooks and
thresholds do the detection and execute all actions. The local LLM is used only
for *interpretation*: summarizing logs, ranking candidate root causes, matching
unfamiliar symptoms to runbooks, and writing human-readable reports. The LLM
never executes commands; it can only *select* from a registry of pre-approved
actions. This keeps behavior predictable and auditable.

### 1.2 Components

| Component | Responsibility |
|---|---|
| **Monitor** | Runs scheduled health checks, tails logs, samples metrics, emits `Signal` objects. |
| **Analyzer** | Correlates signals into `Incident`s, collects evidence, performs root cause analysis (rules first, LLM second). |
| **Remediation Engine** | Maps a diagnosis to a runbook, enforces guardrails, executes actions, verifies and rolls back. |
| **Reporter** | Builds failure reports, assigns severity, notifies dashboard and Discord, handles escalation. |
| **Knowledge Base (KB)** | Runbooks, failure patterns, dependency map, configuration facts (see section 2). |
| **Audit Log** | Append-only record of every observation, decision and action. |

### 1.3 Data Flow

1. Monitor emits a `Signal` (e.g. `llama_server.unreachable`, `ram.high`).
2. Analyzer deduplicates and groups signals into an `Incident` (a single
   incident per root cause, not per symptom).
3. Analyzer collects evidence (log excerpts, metrics, process state) and
   walks the dependency graph to find the *deepest* failing dependency.
4. Analyzer proposes ranked hypotheses with confidence scores.
5. Remediation Engine looks up a runbook for the top hypothesis and classifies
   its actions by risk tier.
6. Tier 0/1 actions run automatically if guardrails pass; Tier 2/3 create an
   approval request; unknown causes or low confidence go straight to escalation.
7. After each action the engine verifies recovery. On failure it rolls back,
   tries the next runbook step (bounded), then escalates.
8. Reporter publishes the outcome. Resolved incidents feed the learning loop.

### 1.4 Decision Making

An action is auto-executed only if **all** are true:

- Diagnosis confidence >= `AUTO_FIX_MIN_CONFIDENCE` (default 0.8).
- The runbook action is Tier 0 or Tier 1 (see 5.1).
- Rate limits and circuit breakers permit it (section 9.5).
- The diagnostic agent is not in `observe-only` mode.
- No maintenance window or manual lock is active.

Otherwise: request approval (risky but understood) or escalate (not understood).

### 1.5 Safety Guardrails and Approval Workflow (summary)

- Actions come from a fixed registry; no free-form shell generation.
- Every action declares risk tier, preconditions, verification, and rollback.
- Destructive actions always require explicit human approval.
- Rate limits, cooldowns and circuit breakers prevent restart loops.
- Everything is audit-logged. Details in sections 5 and 9.

### 1.6 Operating Modes

| Mode | Behavior |
|---|---|
| `off` | Agent disabled. |
| `observe` | Monitor, diagnose and report only. Default for Phase 1. |
| `assisted` | Proposes fixes; every action needs approval. |
| `auto-safe` | Executes Tier 0/1 automatically; others need approval. |

---

## 2. Knowledge Base Structure

The KB is versioned, human-reviewable text (YAML/Markdown) stored in the
repository under `ai-backend/diagnostics/kb/`, with runtime additions kept in a
local store (`data/diagnostics/kb_overrides/`) until reviewed.

```
kb/
  runbooks/            # step-by-step procedures, one file per failure type
  patterns/            # symptom signatures -> candidate causes
  dependencies.yaml    # service dependency graph
  config_facts.yaml    # expected configuration, ports, paths, env vars
  recovery/            # full recovery procedures (cold start, restore)
  thresholds.yaml      # metric thresholds and durations
```

### 2.1 Runbooks

Each runbook is structured data so the engine can execute it and the LLM can
read it:

```yaml
id: RB-LLAMA-001
title: llama.cpp server unreachable
applies_to: [llama_server.unreachable]
preconditions:
  - model_file_exists
  - no_other_process_on_port: 8080
steps:
  - id: restart
    action: service.restart
    params: {service: llama_server}
    tier: 1
    verify: {check: llama_server.health, timeout_s: 90}
    rollback: null
  - id: reload_default_model
    action: model.load_default
    tier: 1
    verify: {check: llama_server.health, timeout_s: 120}
escalate_if: [steps_exhausted, verify_failed]
manual_guidance: |
  Check model path in the configuration, free VRAM, and llama-server logs.
```

### 2.2 Common Failure Patterns and Solutions

| Pattern (symptom) | Likely cause | Standard fix | Tier |
|---|---|---|---|
| `/api/chat` returns 503, llama port closed | llama.cpp crashed or not started | Restart llama server | 1 |
| llama log: `out of memory` / VRAM allocation failed | Model too large, VRAM leak | Reload with smaller context or model; escalate if repeated | 2 |
| Backend RAM > 90% sustained | Memory leak, large context | Clear caches, restart backend worker | 1 |
| `/api/research` 503, SearXNG unreachable | SearXNG down or JSON output disabled | Restart SearXNG; if JSON disabled, escalate | 1 / 3 |
| Discord bot offline | Bot process exited, invalid token | Restart bot; invalid token -> escalate | 1 / 3 |
| Disk free < 10% | Logs/models/cache growth | Rotate logs, clear temp cache; deleting models needs approval | 1 / 3 |
| GPU telemetry `null` | Driver/counter issue | Re-probe; escalate if persistent | 0 |
| High latency, normal CPU/GPU | Prompt too long, model swap thrash | Reduce context; report | 2 |
| Dashboard cannot reach backend | Backend down, CORS or port conflict | Restart backend (via supervisor); escalate on port conflict | 1 / 3 |

### 2.3 System Configuration Knowledge

`config_facts.yaml` records the *expected* state so drift is detectable:
backend host/port (`127.0.0.1:8000`), llama.cpp URL, model directory
(`AI_SERVER_MODEL_DIR`), `SEARXNG_BASE_URL`, Discord bot settings, GPU backend
(Windows AMD telemetry vs. Linux), Python versions and required packages, and
filesystem paths for logs and data. Secrets are **never** stored in the KB;
only names of required variables.

### 2.4 Service Dependency Mapping

```yaml
services:
  backend:        {depends_on: [], health: GET /api/system}
  llama_server:   {depends_on: [model_files, gpu], health: llama /health}
  chat_api:       {depends_on: [backend, llama_server]}
  research_api:   {depends_on: [backend, llama_server, searxng]}
  searxng:        {depends_on: [], optional: true}
  discord_bot:    {depends_on: [backend, discord_gateway]}
  dashboard:      {depends_on: [backend]}
```

Root cause analysis walks this graph bottom-up: if `chat_api` and
`discord_bot` both fail but `backend` is healthy and `llama_server` is down,
the incident is attributed to `llama_server` only.

### 2.5 Recovery Procedures

Documented for larger events: cold start order (model files -> llama server ->
backend -> bot -> dashboard), restoring configuration from a known-good
snapshot, recovering from a corrupted model download (re-verify checksum),
and recovery after host reboot or GPU driver reset.

### 2.6 KB Governance

Every entry has an `id`, `version`, `owner`, `last_reviewed` date and
`source` (`built-in`, `learned`, `user`). Learned entries are `draft` until a
user approves them (section 7.4).

---

## 3. Monitoring & Detection

### 3.1 Health Checks

| Check | Method | Interval | Failure condition |
|---|---|---|---|
| Backend API | `GET /api/system` | 15 s | non-200 or > 2 s, 3 consecutive |
| llama.cpp | `GET <llama>/health` | 15 s | unreachable or not `ok` |
| Chat probe (synthetic) | tiny `POST /api/chat` | 5 min | 503, or latency > threshold |
| SearXNG | JSON search for a fixed query | 1 min | unreachable / non-JSON |
| Discord bot | `bot_manager` status + heartbeat | 30 s | stopped or stale heartbeat |
| Dashboard | static file fetch | 1 min | non-200 |
| Model files | directory scan | 5 min | configured model missing |

### 3.2 System Resources

Reuse `system_stats.py`: CPU %, RAM %, GPU %, VRAM used/total, plus disk free
space and process-level RSS for the backend and llama server.

### 3.3 Performance Metrics and Thresholds

Defaults (configurable in `thresholds.yaml`):

| Metric | Warning | Critical | Duration |
|---|---|---|---|
| CPU | 85% | 95% | 5 min |
| RAM | 85% | 95% | 3 min |
| VRAM | 90% | 98% | 2 min |
| Disk free | < 15% | < 5% | immediate |
| Chat latency p95 | 2x baseline | 5x baseline | 10 min |
| Error rate (5xx) | 2% | 10% | 5 min |
| Tokens/sec | -30% vs baseline | -60% | 10 min |

Thresholds require a **duration** to avoid flapping, and use hysteresis (clear
at a lower level than the trigger).

### 3.4 Log Analysis and Anomaly Detection

- Sources: backend log, llama.cpp stdout/stderr, Discord bot log, OS events.
- Logs are tailed, normalized (timestamps, IDs and numbers masked) and
  clustered into templates; new or sharply increasing templates are anomalies.
- Statistical baselines (rolling median/MAD) over latency, error rate and
  resource use flag deviations.
- Log content is **untrusted data**: it is passed to the LLM only inside
  delimited data blocks, never as instructions (prompt-injection defense).

### 3.5 Error Pattern Recognition

Regex/keyword signatures from `patterns/` run first (`CUDA out of memory`,
`address already in use`, `Connection refused`, `No space left`, `401
Unauthorized` from Discord). Unmatched error clusters are queued for LLM
classification and, if still unknown, escalated as "unrecognized failure".

### 3.5.1 Signal Schema

```json
{
  "id": "sig_...", "ts": "2026-01-01T00:00:00Z",
  "source": "health_check|log|metric",
  "name": "llama_server.unreachable",
  "severity_hint": "warning", "value": null,
  "details": {"url": "http://127.0.0.1:8080/health", "error": "refused"}
}
```

---

## 4. Diagnostics Engine

### 4.1 Root Cause Analysis Procedure

1. **Group** related signals within a time window into one incident.
2. **Assess state**: snapshot of processes, ports, resources, config, recent
   changes (model switch, deploy, config edit).
3. **Check dependencies**: find the lowest failing node in the dependency graph.
4. **Map symptoms to causes** using the pattern table (deterministic scoring).
5. **Collect evidence** supporting and contradicting each hypothesis.
6. **Rank hypotheses**; if no rule exceeds the confidence threshold, ask the
   LLM to propose causes *from the KB's candidate list plus evidence*.
7. **Validate** with a non-invasive probe (e.g. check the port, run a small
   request) before any action.

### 4.2 System State Assessment

Captured as a `StateSnapshot`: service status, listening ports, process
list with CPU/RAM, GPU/VRAM, disk, loaded model, configuration hash, uptime,
last restart times, and recent incidents. Snapshots are stored with the
incident for later comparison.

### 4.3 Symptom-to-Cause Mapping

Rules are expressed declaratively:

```yaml
- symptoms: [chat_api.503, llama_server.port_closed]
  cause: llama_server.process_dead
  weight: 0.85
- symptoms: [llama_server.log.oom]
  cause: gpu.vram_exhausted
  weight: 0.9
- symptoms: [discord_bot.stopped, discord.log.401]
  cause: discord.invalid_token
  weight: 0.95
```

Confidence combines rule weight, number of corroborating signals, absence of
contradicting evidence and past success rate of the matching runbook.

### 4.4 Evidence Collection

Per incident: last N log lines per involved service (redacted of tokens,
keys and IPs where configured), metric time series for the preceding 30
minutes, health check history, state snapshot, config diff against
`config_facts.yaml`, and the exact commands/probes run. Evidence is
size-capped and stored as an immutable bundle referenced by the incident ID.

### 4.5 Incident Model

```json
{
  "id": "inc_2026...", "status": "open|remediating|awaiting_approval|resolved|escalated",
  "severity": "warning", "root_cause": "llama_server.process_dead",
  "confidence": 0.86, "signals": ["sig_1"], "evidence_bundle": "ev_...",
  "attempts": [], "created_at": "...", "resolved_at": null
}
```

---

## 5. Auto-Remediation Capabilities

### 5.1 Risk Tiers

| Tier | Description | Handling | Examples |
|---|---|---|---|
| 0 | Read-only | Always allowed | Re-probe, collect extra logs |
| 1 | Safe, reversible, low impact | Automatic | Restart llama server/bot/SearXNG, clear caches, reload config, rotate logs |
| 2 | Impactful but recoverable | Approval (or auto after trust period, opt-in) | Switch model, reduce context size, restart backend, kill a stuck process |
| 3 | Dangerous / irreversible | Always approval, with confirmation | Delete files/models/data, migrations, change credentials, modify firewall, driver actions |

Anything not in the registry is Tier 3 by default and cannot be automated.

### 5.2 Safe Automatic Fixes

- **Service restart**: graceful stop, wait, start; max 1 restart per service per
  10 minutes by default.
- **Cache clear**: only application-owned cache directories, never user data.
- **Config reload**: re-read configuration; validate before applying.
- **Log rotation** of agent-known log files.
- **Reload default model** via `model_manager`.

### 5.3 Operations Requiring Approval

Data deletion, schema/data migrations, model removal, token/credential changes,
upgrading dependencies, host reboot, killing processes not started by the
server, any change outside the application directory.

### 5.4 Action Contract

```python
class Action:
    id: str; tier: int
    def preconditions(ctx) -> list[Check]: ...
    def snapshot(ctx) -> Snapshot          # state needed for rollback
    def execute(ctx) -> Result
    def verify(ctx) -> VerificationResult
    def rollback(ctx, snapshot) -> Result
```

### 5.5 Rollback Procedures

Before executing, the engine snapshots what the action changes (config file
copy, current model name, service state). If verification fails or health
regresses within the verification window, `rollback` restores the snapshot and
the failure is recorded. Actions that cannot be rolled back are Tier 3.

### 5.6 Success Verification

Verification is independent of the action's own return code: re-run the
originating health check(s), confirm related dependents recover, and observe
a **stability window** (default 2 minutes) with no recurrence. Only then is the
incident marked `resolved`. Failure after retries triggers escalation with the
full attempt history.

---

## 6. Error Reporting & Escalation

### 6.1 Severity Levels

| Level | Meaning | Delivery |
|---|---|---|
| `info` | Self-healed or minor; no action needed | Dashboard log |
| `warning` | Degraded or at risk; may need attention | Dashboard + Discord (batched) |
| `critical` | Service down or auto-fix failed; user action needed | Dashboard banner + Discord immediate, repeated until acknowledged |

Severity is raised automatically when auto-remediation fails, when an issue
recurs more than N times per day, or when a core dependency (backend,
llama.cpp) is down.

### 6.2 Failure Report Contents

1. **Summary**: one-line title, severity, affected services, start time, duration.
2. **What went wrong**: observed symptoms and impact.
3. **Why**: root cause and confidence, alternatives considered.
4. **What was tried**: each action, result, verification outcome, rollbacks.
5. **Why it failed / why not attempted**: e.g. "requires approval", "no runbook".
6. **Evidence**: log excerpts, metrics, state snapshot (links to bundle).
7. **Recommended user actions**: ordered steps, with commands where useful.
8. **References**: runbook IDs and docs.

### 6.3 Example Report

```
[CRITICAL] llama.cpp server down - chat and Discord replies failing
Since: 14:02 (23 min)   Confidence: 0.86

What happened: /api/chat returns 503; port 8080 not listening.
Why: llama-server exited with "failed to allocate VRAM (needs 9.1 GiB, 8.0 free)".
Tried: restart (failed, same error); reload smaller model (not permitted: Tier 2,
awaiting approval).
Recommended: 1) Close other GPU applications. 2) Approve switching to a smaller
model in the dashboard, or choose one manually. 3) Check driver status.
Evidence: ev_20260101_001
```

### 6.4 Escalation Policy

Escalate immediately for unknown causes, Tier 3 needs, or repeated failure.
Reminders at 15 min, 1 h, then every 6 h for critical issues. Duplicate
notifications are suppressed per incident.

---

## 7. User Intervention Workflows

### 7.1 Dashboard UI

New "Diagnostics" panel in the existing dashboard:

- **Status board**: green/yellow/red per service with last check time.
- **Active incidents**: severity, root cause, status, age.
- **Incident detail**: timeline, evidence viewer, attempts, report.
- **Pending approvals**: action, risk, rationale, rollback plan; Approve / Deny.
- **History**: resolved incidents and auto-fix success rates.
- **Controls**: mode switch, maintenance window, pause auto-remediation.

### 7.2 Approval Workflow

```
Incident -> action proposed (Tier 2/3) -> approval request created
 -> dashboard + Discord notification -> user Approve/Deny (+ comment)
 -> approved: execute, verify, rollback if needed  | denied: record, keep escalated
```

Approvals expire (default 1 h), are single-use, bound to the exact action and
parameters, and Tier 3 requires typing a confirmation phrase.

### 7.3 Manual Remediation Guidance

Reports include step-by-step instructions from the runbook's
`manual_guidance`, with the expected output of each step and a "Re-run checks"
button that triggers diagnostics and marks the incident resolved when healthy.

### 7.4 Knowledge Base Updates from Fixes

When a user resolves an incident manually, the dashboard asks "What fixed it?".
The agent drafts a runbook/pattern from the incident timeline and the user's
note, which is stored as `draft` and promoted after review (edit, approve,
reject). Approved entries are versioned and tracked for effectiveness.

---

## 8. Implementation Phases

### Phase 1: Basic Monitoring and Reporting (observe mode)
- Can be built and tested now on the Windows test setup; no GPU or server needed.
- Health checks, resource sampling, thresholds, log tailing.
- Incident model, evidence bundles, failure reports, severity levels.
- Dashboard status board and incident list; Discord notifications.
- Read-only API endpoints; audit log.
- **Exit criteria**: all checks run reliably, < 1 false alert/day, reports verified accurate.

### Phase 2: Auto-Remediation for Safe Operations
- Action registry, Tier 0/1 actions, verification, rollback, rate limiting.
- Runbook executor; approval workflow for Tier 2/3.
- **Exit criteria**: > 90% of Tier 1 fixes verified successful in testing; no restart loops under fault injection.

### Phase 3: Advanced Diagnostics and ML-Based Detection
- Log template clustering, statistical/ML anomaly detection, latency baselines.
- LLM-assisted hypothesis ranking and report writing.
- Trend and predictive alerts (disk filling, memory growth).
- **Exit criteria**: anomaly detection precision/recall targets met on recorded incidents.

### Phase 4: Self-Learning and Knowledge Base Updates
- Draft runbook generation from resolved incidents; review UI.
- Runbook success-rate tracking and confidence calibration.
- Optional trust-based promotion of Tier 2 actions to automatic.
- **Exit criteria**: reviewed KB additions measurably reduce escalations.

---

## 9. Safety & Security

### 9.1 Sandboxing and Isolation
- The agent runs as a dedicated low-privilege account with only the
  permissions its actions need; no administrator/root by default.
- Actions execute via a fixed registry using argument arrays (never shell
  string interpolation); paths are validated against an allowlist of
  application directories.
- The LLM has no tool access beyond choosing from registry IDs; its output is
  schema-validated.

### 9.2 Action Approval
Tiered approvals (section 7.2). Approvals are authenticated (see
`docs/authentication.md`), attributed to a user, and tamper-evident.

### 9.3 Audit Logging
Every signal, hypothesis, decision, approval, action, verification and rollback
is written to an append-only log (JSON lines, with hash chaining for tamper
detection) including timestamp, actor (`agent` or user), inputs, outputs and
incident ID. Secrets are redacted. Retention default 90 days.

### 9.4 Preventing Destructive Operations
- Default-deny: unregistered actions cannot run.
- Tier 3 never automatic; deletion limited to allowlisted temp/cache paths
  unless approved.
- Dry-run support and preconditions (e.g. verify backup/snapshot exists).
- Prompt-injection defense: logs and web content are data, never instructions.
- A global kill switch immediately sets mode to `off`.

### 9.5 Rate Limiting and Circuit Breakers
- Per-service cooldown (default 10 min) and max 3 auto-fix attempts per
  incident and 6 per service per 24 h.
- Global cap on actions per hour.
- Circuit breaker: after repeated failed fixes the agent stops acting on that
  service and escalates as critical.
- Exponential backoff between attempts.

### 9.6 Other Controls
Diagnostics API endpoints require authentication; evidence bundles are
access-controlled and redact secrets; KB files are integrity-checked.

---

## 10. API Endpoints

All under `/api/diagnostics`, JSON, authenticated. Proposed.

### Diagnostics
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Aggregated service health and agent mode. |
| GET | `/health/{service}` | Single service health with latest check details. |
| POST | `/run` | Run diagnostics now. Body: `{"scope": "all"\|"<service>"}`. Returns incident IDs. |
| GET | `/metrics` | Recent metrics and thresholds status. |

### Remediation
| Method | Path | Description |
|---|---|---|
| POST | `/incidents/{id}/remediate` | Attempt the recommended fix (guardrails apply). |
| GET | `/approvals` | Pending approval requests. |
| POST | `/approvals/{id}/approve` | Approve; body: `{"comment": "...", "confirmation": "..."}`. |
| POST | `/approvals/{id}/deny` | Deny with comment. |
| POST | `/incidents/{id}/rollback` | Roll back the last action. |
| PUT | `/mode` | Set mode (`off`, `observe`, `assisted`, `auto-safe`). |

### Reporting
| Method | Path | Description |
|---|---|---|
| GET | `/incidents` | List; filters `status`, `severity`, `service`, `since`. |
| GET | `/incidents/{id}` | Incident detail with attempts. |
| GET | `/incidents/{id}/report` | Full failure report (JSON or `?format=markdown`). |
| POST | `/incidents/{id}/acknowledge` | Acknowledge, stop reminders. |
| POST | `/incidents/{id}/resolve` | Mark manually resolved (+ optional fix note). |
| GET | `/audit` | Audit log query. |

### Knowledge Base
| Method | Path | Description |
|---|---|---|
| GET | `/kb/runbooks` | List runbooks. |
| GET | `/kb/runbooks/{id}` | Retrieve one. |
| POST | `/kb/runbooks` | Submit a new runbook (stored as draft). |
| PUT | `/kb/runbooks/{id}` | Edit (new version). |
| POST | `/kb/drafts/{id}/promote` | Approve a learned draft. |
| GET | `/kb/patterns`, `/kb/dependencies` | Read patterns and dependency map. |

Example response, `GET /api/diagnostics/health`:

```json
{
  "mode": "observe",
  "overall": "degraded",
  "services": {
    "backend": {"status": "healthy", "latency_ms": 12},
    "llama_server": {"status": "down", "since": "2026-01-01T14:02:00Z"}
  },
  "open_incidents": 1
}
```

Errors: 401/403 unauthenticated or unauthorized, 404 unknown ID, 409 action
blocked by guardrail (response includes the reason), 429 rate limited.

---

## 11. Integration Points

- **Monitoring data sources**: `system_stats.py` (CPU, RAM, GPU/VRAM),
  llama.cpp `/health` and metrics, process table, disk stats.
- **Logging and metrics collection**: structured logging in backend and bot;
  metrics in a local ring buffer/SQLite store with retention; optional
  Prometheus-style export on Linux/Proxmox.
- **Existing backend services**: `model_manager` (model load/switch),
  `bot_manager` (bot start/stop/status), chat and research endpoints as
  synthetic probes. Actions call these modules rather than shelling out where
  possible.
- **Discord bot notifications**: a dedicated alerts channel; messages show
  severity, summary and a link to the dashboard; critical alerts can mention a
  role. Approvals are *only* linked from Discord, never granted by chat reply.
- **Dashboard UI components**: a new Diagnostics tab in `index.html`/`js`
  polling or streaming (SSE/WebSocket) from the API; reuse existing styles in `css/`.
- **Platform differences**: Windows (service control via supervisor scripts,
  AMD GPU counters) vs. Linux/Proxmox (systemd units); platform adapters hide
  the difference behind the action registry.

| Check | Windows test setup | Linux/Proxmox server |
|---|---|---|
| llama-server health | `http://127.0.0.1:8080/health` | same, behind the Quadlet/systemd unit |
| Backend / dashboard | ports 8000 / 8001 (`run-*.bat`) | systemd or Podman units behind NGINX |
| SearXNG | WSL process on 8888 (`run-searxng.bat`) | `searxng.service` on 127.0.0.1:8888 |
| GPU telemetry | Windows performance counters | `rocm-smi` / amdgpu sysfs (not yet built) |
| Service restart | process supervisor scripts | `systemctl restart` / Podman |
| Logs | `ai-backend` rotating log files | same files plus `journalctl` |

KB entries and runbooks must declare which platform they apply to. Phase 1
(observe mode) uses only the Windows column and needs no GPU or server.

---

## 12. Testing & Validation

### 12.1 Health Check Validation
Unit tests with mocked endpoints for success, timeout, malformed response and
flapping. Verify thresholds, durations and hysteresis.

### 12.2 Diagnostic Accuracy
Build a corpus of recorded or synthetic incidents with known root causes.
Metrics: root-cause top-1/top-3 accuracy, precision/recall of anomaly
detection, false-alert rate. Include multi-fault and cascading cases to
verify dependency attribution.

### 12.3 Remediation Effectiveness
Fault-injection tests (kill llama server, fill disk in a sandbox, block a
port, corrupt config, exhaust VRAM) measuring fix success rate, time to
recover, rollback correctness, and absence of restart loops.

### 12.4 Failure Reporting Accuracy
Review generated reports against ground truth: correct cause, complete
attempt history, evidence present and redacted, actionable recommendations,
correct severity. Snapshot tests for report templates.

### 12.5 Safety Guardrail Effectiveness
- Attempt Tier 2/3 actions without approval: must be blocked.
- Expired, reused, or parameter-mismatched approvals: rejected.
- Path-traversal and command-injection attempts in parameters: rejected.
- Prompt-injection strings in logs: must not alter decisions.
- Rate limit and circuit breaker triggers under repeated failure.
- Kill switch halts actions within seconds.
- Audit log completeness and hash-chain integrity checks.

### 12.6 Rollout
Run in `observe` mode first and compare with manual observations; enable
`auto-safe` per service; track KPIs (MTTR, auto-resolve rate, escalation
precision, false positives) and review weekly.

---

## Appendix: Configuration (proposed)

| Variable | Default | Purpose |
|---|---|---|
| `DIAG_MODE` | `observe` | Agent mode |
| `DIAG_CHECK_INTERVAL_S` | `15` | Base health check interval |
| `DIAG_AUTO_FIX_MIN_CONFIDENCE` | `0.8` | Confidence required for auto fixes |
| `DIAG_COOLDOWN_S` | `600` | Per-service action cooldown |
| `DIAG_MAX_ATTEMPTS` | `3` | Auto-fix attempts per incident |
| `DIAG_APPROVAL_TTL_S` | `3600` | Approval expiry |
| `DIAG_AUDIT_RETENTION_DAYS` | `90` | Audit log retention |
| `DIAG_DISCORD_CHANNEL_ID` | unset | Alerts channel |
