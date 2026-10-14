# AI-Powered Diagnostics & Self-Healing

> Status: **design specification with an initial observe-only prototype**.
> `ai-backend/diagnostics.py` provides on-demand local health/resource
> observations and persistent, bounded SQLite observation/incident/audit
> history. Explicit bounded API routes and a manual-run dashboard view are
> implemented. Scheduling, automated log analysis, semantic retrieval,
> remediation, and the rest of the design below are not implemented.

This document specifies the AI Maintenance Agent: a reactive self-healing
subsystem that monitors system telemetry and service health, retrieves relevant
local diagnostic knowledge through retrieval-augmented generation (RAG), and
produces structured repair proposals for a separate backend executor. The
model analyzes logs, error codes, and hardware health data; it never runs
commands or grants itself authority. The intended long-term goal is bounded
autonomy: a separate deterministic policy may authorize eligible registered
repairs without per-action approval, based on explicit user settings, action
risk, verified outcomes, and reviewed feedback. All diagnostic data,
maintenance procedures, and known-issue references are stored locally to
support private, domain-specific troubleshooting and recovery.

Existing building blocks it relies on: the FastAPI backend (`ai-backend/main.py`),
`system_stats.py` (CPU/RAM/GPU telemetry), `model_manager.py` (model discovery
and llama.cpp lifecycle), `bot_manager.py` (Discord bot process control), the
llama.cpp server, the optional SearXNG instance, the Discord bot
(`ai-discord-bot/bot.py`) and the browser dashboard (`index.html`, `js/`, `css/`).

---

## 1. System Architecture

### 1.1 Overview

The **AI Maintenance Agent** is a reactive service inside (or alongside) the
backend. It responds to telemetry thresholds, health-check failures, service
events, scheduled diagnostic requests, or a user request:

```
Signal -> Correlate -> Retrieve local knowledge -> Diagnose -> Propose structured repair
       -> Validate and authorize -> Backend executor -> Verify -> Record or escalate
```

It is deliberately a **hybrid** system. Deterministic monitors detect
conditions, the local RAG index retrieves relevant reviewed procedures and
known issues, and the local LLM interprets evidence and proposes a repair as
structured data. A deterministic backend executor independently validates
each proposed step against the action registry, preconditions, risk tier,
permissions, and approval policy before performing it. The model has no
command execution tools and cannot bypass the executor.

### 1.2 Components

| Component | Responsibility |
|---|---|
| **Monitor** | Reacts to telemetry thresholds, health-check failures, service events, and scheduled/user-triggered checks; emits `Signal` objects. |
| **Analyzer** | Correlates signals into `Incident`s and collects evidence. |
| **Local Retriever** | Searches reviewed runbooks and platform facts plus similar historical incidents, clearly separating approved procedures from empirical case evidence. |
| **Diagnostic Model** | Analyzes retrieved evidence and produces ranked hypotheses and a schema-constrained repair proposal; has no direct execution capability. |
| **Backend Executor** | Validates proposals against the fixed action registry, preconditions, risk policy, approvals, and rollback requirements; executes, verifies, or rejects them. |
| **Maintenance Coordinator** | Owns scheduled maintenance windows, gates normal AI traffic, selects the diagnostic model, and restores service afterward. |
| **Reporter** | Builds failure reports, assigns severity, notifies dashboard and Discord, handles escalation. |
| **Knowledge Base (KB)** | Runbooks, failure patterns, dependency map, configuration facts (see section 2). |
| **Audit Log** | Append-only record of every observation, decision and action. |

### 1.3 Data Flow

1. A telemetry threshold, failed health check, service event, user request, or
   scheduled diagnostic triggers an evaluation; the monitor emits one or more
   `Signal`s (e.g. `llama_server.unreachable`, `ram.high`).
2. Analyzer deduplicates and groups signals into an `Incident` (a single
   incident per root cause, not per symptom).
3. Analyzer collects evidence (log excerpts, metrics, process state) and
   walks the dependency graph to find the *deepest* failing dependency.
4. Local retrieval finds bounded, relevant reviewed knowledge and similar
   historical incidents using the incident signals, platform/version, and
   evidence. Prior cases include what was attempted and the independently
   verified outcome; they are evidence, not approved procedures. Sources,
   case IDs, and package versions are retained with the incident.
5. Deterministic rules and the diagnostic model rank hypotheses. When used,
   the model returns a structured proposal that references retrieved evidence
   and registered action IDs; unknown causes or low confidence go to escalation.
6. Backend Executor validates every proposed action. Tier 0/1 actions may run
   automatically only if all guardrails pass. Higher-risk actions require
   approval unless a separately configured autonomy policy explicitly
   authorizes that registered action after its evidence-based eligibility
   requirements are met. Model output and feedback history alone never
   authorize an action.
7. After each action the executor verifies recovery. On failure it rolls back,
   tries the next runbook step (bounded), then escalates.
8. Reporter publishes the outcome. Resolved incidents feed the learning loop.

### 1.4 Decision Making

An action is automatically authorized only if **all** applicable conditions
are true:

- Diagnosis confidence >= `AUTO_FIX_MIN_CONFIDENCE` (default 0.8).
- The action is registered and permitted for automatic execution by the
  current operating mode and explicit autonomy policy. Initially, this is
  limited to Tier 0/1; expanding eligibility requires the staged gates in
  section 8 and never includes Tier 3.
- Rate limits and circuit breakers permit it (section 9.5).
- The diagnostic agent is not in `observe-only` mode.
- No unexpected maintenance window or manual lock is active. During a
  scheduled window, only actions explicitly permitted for that window may run;
  the window does not bypass operating mode, risk-tier, approval, or rollback
  requirements.

Otherwise: request approval (understood but not authorized) or escalate
(not understood or unsafe). Confidence is a diagnostic signal, not permission.

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

### 1.7 Scheduled Maintenance Windows

The target schedule is a recurring daily maintenance window from **03:00 to
04:00 server-local time**, using an explicitly configured IANA timezone rather
than the browser's timezone. Daylight-saving transitions must be handled
deterministically. The feature remains disabled until it has been configured
and validated on the target server.

The Maintenance Coordinator owns a persisted state machine:
`scheduled -> entering -> maintenance -> restoring -> complete` (or
`failed/needs_attention`). At the window start it:

1. Records the currently selected normal model and service state.
2. Enters maintenance mode and blocks new user-facing work. It safely drains
   in-flight chat, research, model-switch, bot, and other inference or
   maintenance-conflicting activity; clients receive a clear maintenance
   response and retry guidance. The dashboard may retain a read-only
   maintenance-status view.
3. After draining, pauses or cleanly stops normal inference workloads and
   user-facing processes that could contend for resources or conflict with
   maintenance. It must not indiscriminately stop the maintenance control
   plane: the coordinator, backend executor, telemetry/health monitor, local
   RAG service, audit log, and required recovery/notification paths remain
   available. The exact service dependency and stop/start order is defined per
   deployment and tested before unattended operation.
4. If work does not drain before the configured deadline, disruptive
   maintenance is skipped and the missed window is reported rather than
   forcibly killing requests or overlapping model changes.
5. Selects and loads the best eligible installed model dedicated to diagnostics
   using
   an explicit policy (task capability, context size, compatibility, VRAM
   requirement, and benchmarked diagnostic quality/latency). It loads that
   model with the versioned diagnostics knowledge package described in
   section 2; the package is required task context, not an assumption that the
   model has been fine-tuned. It must not download or execute an arbitrary
   model selected by the LLM. If no eligible diagnostic model or compatible
   knowledge package can be loaded, deterministic checks continue where safe
   and model-dependent work is skipped and reported.
6. Runs reactive diagnostics and maintenance procedures against
   telemetry, logs, error states, and available hardware/VM health data. Local
   RAG supplies relevant reviewed procedures and known issues; the model
   generates structured remediation proposals for the backend executor.
   The executor validates and performs only registered, authorized actions.
7. Runs only allowlisted update routines whose preconditions, scope,
   verification, and rollback are registered. Model output can recommend
   registered actions but cannot create commands or bypass the executor.
8. Verifies update results and system integrity, stops starting work before
   the window ends, restores the previous normal model, and restarts/resumes
   paused services in dependency order. Normal operations are reopened only
   after required health checks and stability checks pass.

The 04:00 boundary is a target completion time, not permission to interrupt an
operation unsafely or restore service prematurely. If work cannot finish
safely within the window, the coordinator must stop at a safe boundary, roll
back when defined, or remain in maintenance with user-facing workloads paused
and raise an alert. It must not falsely report success or restore traffic to an
unhealthy service. A manual kill switch and audit record apply throughout.

Initial unattended update scope must be allowlisted and limited to
application/model updates with verified sources, pre-update health checks,
backups or snapshots where appropriate, post-update integrity and health
verification, and a tested rollback path. Proxmox, kernel, GPU driver/ROCm,
firmware, and other host-level or irreversible updates are excluded from
unattended updates and require explicit human approval. Update checks can
report available host updates without applying them.

### 1.8 Scheduled Maintenance Runbook

This is the required execution order for a maintenance window. Each phase has
a deterministic gate; the coordinator records the phase, inputs, result, and
timestamp in the audit history. A failed gate skips dependent work and follows
the recovery column rather than allowing the model to improvise a recovery.
The deployment-specific service order, checks, and rollback actions must be
filled in and tested before enabling a real schedule.

| Phase | Procedure and expected result | If the gate fails |
|---|---|---|
| 0. Preflight | Confirm the schedule/timezone, maintenance policy, action allowlist, disk space, service dependency map, installed diagnostic model and matching knowledge package, update sources, and required backups/rollback artifacts. Record current component versions, service states, selected model, and non-secret configuration fingerprints. Verify control plane, audit storage, health probes, and notification path are available. | Do not enter maintenance. Record a skipped window with the failed checks and notify the user. Never fetch an unapproved model or update artifact to make preflight pass. |
| 1. Enter and drain | Persist `entering`; announce maintenance; reject new conflicting work with retry guidance; drain active requests until the configured deadline. Expected: no in-flight work that conflicts with maintenance. | If the deadline expires, cancel the window, reopen the unchanged services, verify normal health, and report the skipped work. Do not kill requests to meet the clock. |
| 2. Quiesce workloads | Persist the exact service/model state. Stop or pause only configured user-facing workloads in dependency order. Keep coordinator, executor, monitor, local retrieval, audit, and recovery/notification paths running. Expected: workloads are quiescent and the maintenance control plane is healthy. | Restart/resume only what this runbook stopped, in reverse dependency order; verify baseline health. If restoration cannot be verified, remain gated and alert for intervention. |
| 3. Load diagnostic context | Load an already installed, eligible diagnostic model and the versioned task package. Run a bounded self-check and verify memory/resource headroom. Expected: model responds to a non-mutating diagnostic check and the correct package/version is recorded. | Unload the diagnostic model if safe; skip model-dependent work. Continue only explicitly permitted deterministic read-only checks, then restore the normal model and services. |
| 4. Diagnose and plan | Collect bounded/redacted evidence; retrieve applicable reviewed procedures and similar historical cases; label case history as evidence, not instructions. Produce a structured plan listing action IDs, risk tiers, preconditions, verification, rollback, and expected impact. The executor independently validates authorization. | If evidence conflicts, applicability is unknown, confidence is insufficient, or a step lacks a tested rollback where required, do not execute that step. Escalate with evidence and request approval where appropriate. |
| 5. Apply one change at a time | Run only registered, allowlisted actions with satisfied preconditions. For updates, verify source/integrity and required backup first. Record a before-state snapshot; apply one bounded change; capture its result before considering the next change. | Stop the sequence on any unexpected result. Do not continue to dependent updates. Use the action's registered rollback, then verify the prior state. |
| 6. Verify and decide | Independently rerun the affected health checks, dependency checks, integrity/version checks, and configured stability window. Expected: target checks pass and no related regression appears. Record success only after verification, not from command exit status or model assertion. | Roll back the failed change if defined and safe, then verify the restored state. If rollback is absent, fails, or leaves state uncertain, keep conflicting workloads paused and escalate; do not claim recovery. |
| 7. Restore normal operation | Stop starting maintenance work before the deadline. Restore the prior normal model and resume stopped services in dependency order. Verify backend, inference, required integrations, telemetry, and dashboard/control-plane health; then reopen user traffic. | If any required check fails, re-gate traffic, retry only the registered restoration action within its retry limit, and roll back the maintenance change when applicable. If still unhealthy, remain in `needs_attention`, preserve the control plane, notify the user, and provide manual recovery guidance. |
| 8. Close and learn | Persist final versions/states, actions, approvals, evidence references, verification, rollback, and incident links. Mark `complete` only after successful restoration; otherwise retain `failed/needs_attention`. Update case history with independently verified outcomes and user feedback. | If audit persistence or notification fails, do not mark complete; retain local recovery state and retry through the independent recovery path. Never treat an unverified attempt as a successful repair example. |

The deadline is not an instruction to force a transition. At 04:00, stop
starting new work and proceed only to a safe boundary. If restoration or health
verification is incomplete, remain in maintenance/`needs_attention`, keep
conflicting user traffic gated, and alert; do not report success simply to end
the window. The global kill switch disables new repair actions but must not
interrupt an unsafe-to-stop operation; recovery follows the action-specific
rollback contract and preserves the audit trail.

The real model-selection policy, maintenance scheduler, service gating,
model restoration, and update rollback behavior require validation on the
target Proxmox host and hardware. Development can test the coordinator with
mocked clocks, model manager, and update adapters, but those tests do not prove
production recovery.

---

## 2. Knowledge Base Structure

Diagnostic data, source documents, embeddings, and indexes are stored on local
server storage. Retrieval and inference must not send diagnostic content to an
external service. Keep two distinct sources of operational context:

- A durable incident and action history records observations, evidence,
  hypotheses, user approvals/denials and reasons, actions attempted, and
  independently verified results, including failures, rollbacks, and
  recurrence. The system starts with no assumed repair history; this local
  history grows as real incidents are investigated and resolved.
- The curated knowledge base contains reviewed, versioned runbooks, platform
  facts, and known issues. Source files remain authoritative and
  human-reviewable. New procedures drafted from case history stay isolated as
  drafts until reviewed and tested.

Similar historical cases can be retrieved to inform later diagnoses even
before a formal runbook exists. They must be labeled as past observations,
filtered for platform/version applicability, and presented with their actual
outcomes; a prior action is not automatically a safe or correct fix. Backups,
access controls, retention, and recovery of both the case history and
knowledge sources are part of deployment.

The target vector-store implementation is to be selected and validated for the
deployment. Qdrant is already planned as a local service in the host stack and
is a candidate backend; the design must also permit offline Windows development
and tests without claiming a production Qdrant deployment before it exists.

```
kb/
  model/                # diagnostic model profile and reviewed task instructions
  platform/             # platform- and version-specific reference files
  runbooks/            # step-by-step procedures, one file per failure type
  patterns/            # symptom signatures -> candidate causes
  dependencies.yaml    # service dependency graph
  config_facts.yaml    # expected configuration, ports, paths, env vars
  recovery/            # full recovery procedures (cold start, restore)
  thresholds.yaml      # metric thresholds and durations
```

The knowledge index contains chunked source text plus metadata such as document
ID/version, platform, component/version applicability, review state, source
path, and content hash. The incident history is structured durable storage;
it may also have a local search index for finding similar cases. Search
results must exclude drafts and incompatible platform/version knowledge by
default. Retrieval should favor exact signal/error matches and applicable
approved runbooks, with semantic search as a supplement. Similar incident
records must remain distinguishable from approved knowledge and include
whether the attempted action succeeded under independent verification.
Every model response records the retrieved document IDs, case IDs, and
versions used.

```text
Reviewed sources -> validate/version -> chunk + embed locally -> knowledge index
Incident -> filter by platform/version -> retrieve approved sources + similar cases
         -> local diagnostic model -> structured repair proposal
         -> executor validation -> registered backend action -> verify and record
```

### Diagnostic Model Knowledge Package

The diagnostic model must receive a task-specific, maintained set of learning
files whenever it is selected. These files provide operational context without
requiring model fine-tuning and without mixing diagnostics instructions into
ordinary chat. Retrieval combines applicable, approved files with relevant
historical cases clearly labeled as empirical evidence. The model profile
identifies compatible model capabilities,
minimum context size, resource requirements, and the evaluation results used
to select it. At inference time the system assembles a bounded context from:

- A reviewed diagnostics system guide: role, scope, evidence-handling rules,
  confidence requirements, escalation conditions, and the prohibition on
  issuing commands or bypassing registered actions.
- Relevant, versioned runbooks, symptom patterns, dependency/config facts,
  recovery procedures, and safety/update policies.
- Similar past incidents, including the evidence available at the time,
  actions attempted, user feedback, and verified outcome. Clearly mark these
  as empirical case history rather than approved instructions; an unsuccessful
  or unverified attempt must not be presented as a successful fix.
- Platform-specific files selected for the actual host (for example Windows
  test setup versus Proxmox/Linux), including tested service names, paths,
  ports, commands/probes, and supported component versions.
- Approved diagnostic examples and evaluation cases that teach expected
  evidence-based reasoning and report format.

Only relevant files should be retrieved for an incident; do not indiscriminately
place the entire KB or raw logs into the prompt. Retrieved evidence and logs
remain untrusted input and must be clearly delimited, size-limited, and
redacted as specified in section 3.4. The model may use these files to explain,
rank hypotheses, and propose registered actions; deterministic checks and the
backend executor remain authoritative.

Knowledge files are not executable instructions. Built-in files are
version-controlled and reviewed. New learning from incidents, user notes, or
model output is stored as an isolated draft with its evidence and provenance;
it never overwrites trusted files or becomes active until a human reviews,
tests, and approves it. Each package release records its version and content
hashes so an incident can be reproduced against the exact instructions the
model received. No passwords, tokens, private keys, or other secrets belong
in the package.

### 2.1 Runbooks

Each runbook is structured data so the engine can execute it and the LLM can
use it as retrieved reference material. The backend executor runs only its
registered actions; it does not execute free-form model-generated steps:

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
6. **Retrieve local knowledge** for this incident from the approved local RAG
   index, filtered by platform, component version, and review status.
7. **Rank hypotheses**; if rules do not resolve the incident, ask the local
   model to propose causes and structured repair steps grounded in the
   retrieved sources and evidence.
8. **Validate** hypotheses with non-invasive probes (e.g. check the port, run
   a small request). Pass proposed repairs to the backend executor, which
   validates them independently before any action.

The model response is data, not an executable plan. A proposal contains only
registered action identifiers and typed parameters, with evidence/source
references and a rationale, for example:

```json
{
  "incident_id": "inc_...",
  "hypotheses": [
    {"cause": "llama_server.process_dead", "confidence": 0.86,
     "evidence_ids": ["ev_process_state_1"]}
  ],
  "proposed_steps": [
    {"action_id": "service.restart", "parameters": {"service": "llama_server"},
     "runbook_id": "RB-LLAMA-001", "evidence_ids": ["ev_process_state_1"]}
  ],
  "escalate": false
}
```

The executor rejects unknown fields/actions, invalid parameter values,
unavailable evidence references, stale or incompatible knowledge versions,
and actions that fail preconditions, permission, risk, approval, or rollback
checks. It obtains executable parameters from the trusted registry/runbook;
model text is never interpolated into a shell command.

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

| Tier | Description | Initial handling | Possible future handling | Examples |
|---|---|---|---|---|
| 0 | Read-only | Always allowed | Always allowed | Re-probe, collect extra logs |
| 1 | Safe, reversible, low impact | Automatic when guardrails pass | Automatic when guardrails pass | Restart llama server/bot/SearXNG, clear caches, reload config, rotate logs |
| 2 | Impactful but recoverable | Approval required | May become automatic only for specifically allowlisted actions after explicit opt-in and staged evidence/review gates | Switch model, reduce context size, restart backend, kill a stuck process |
| 3 | Dangerous / irreversible | Always approval, with confirmation | Always approval; never eligible for autonomous execution | Delete files/models/data, migrations, change credentials, modify firewall, driver actions |

Anything not in the registry is Tier 3 by default and cannot be automated.
Approval history or model confidence cannot lower an action's tier or override
an approval requirement.

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
- **Maintenance status**: configured timezone and next window, normal/diagnostic
  model, traffic gate, progress, update results, and restore/health-check status.
- **Maintenance controls**: enable/disable future windows and request a safe
  abort. A user control must not forcibly interrupt an unsafe update step.

### 7.2 Approval Workflow

```
Incident -> action proposed (Tier 2/3) -> approval request created
 -> dashboard + Discord notification -> user Approve/Deny (+ comment)
 -> approved: execute, verify, rollback if needed  | denied: record, keep escalated
```

Approvals expire (default 1 h), are single-use, bound to the exact action and
parameters, and Tier 3 requires typing a confirmation phrase. The long-term
autonomy goal does not remove user control: automatic authorization is limited
to individually eligible registered actions under an explicitly enabled
policy, with per-action pause/disable controls and a global kill switch.
Feedback can inform later policy review, but repeated approvals or denials do
not silently change permissions.

### 7.3 Manual Remediation Guidance

In a future, explicitly approved remediation phase, incident reports may
include step-by-step instructions from a runbook's `manual_guidance`, with the
expected output of each step. A "Re-run checks" action would only collect new
evidence; it must not automatically mark an incident resolved or execute
remediation.

### 7.4 Learning from Repair Feedback and Outcomes

For each repair proposal, record the incident evidence, retrieved knowledge
versions, proposed action and risk tier, whether the user approved or denied
it, any user-provided reason, the executor's result, independent verification,
and any rollback or recurrence. Distinguish approval from success: an approved
repair may fail, and a denied repair is not evidence that the diagnosis was
wrong. Keep this feedback local, access-controlled, redacted, and attributable
to the relevant policy, action, runbook, and model versions.

Use incident history and verified outcomes to find comparable cases and
inform later diagnoses from the beginning; the system need not already know a
repair to start accumulating useful experience. Case retrieval does not
require promoting each incident into a runbook. Use reviewed feedback for
reporting and offline evaluation. The agent may draft a runbook/pattern or
diagnostic example from incidents and user notes, but it is stored as `draft`
and promoted only after review, platform-specific testing, and approval.
Feedback history must not directly modify model weights, action permissions,
risk tiers, or trusted knowledge. Any future policy or knowledge change is
versioned, evaluated against held-out and failure cases, explicitly approved,
and reversible; monitor for biased, sparse, stale, or poisoned feedback.
Approved knowledge files are tracked for effectiveness, and model-generated
changes never update the active package directly.

### 7.5 Staged Autonomy

Progress from observe-only to autonomous repair in explicit, reversible stages:

1. Persist observations and repair decisions; collect approval/denial reasons
   and independently verified outcomes without taking repair actions.
2. Enable assisted proposals and human approval, then measure success,
   recurrence, false positives, rollback, and escalation by action and
   platform/version.
3. Enable automatic Tier 0/1 actions only after deterministic preconditions,
   verification, rollback, rate limits, audit, and fault-injection tests pass.
4. Consider Tier 2 actions individually only after an explicit opt-in, a
   documented evaluation threshold over sufficient representative outcomes,
   staged/canary operation, and a tested disable/rollback path. A policy
   engine—not the diagnostic model—grants authorization, and the user can
   revoke it at any time.

If evidence is insufficient, outcomes regress, the environment differs from
the tested platform/version, or a guardrail fails, fall back to approval or
observe mode. Tier 3 actions remain approval-only. No stage is enabled merely
because the model reports high confidence or the user approved similar
actions before.

---

## 8. Implementation Phases

### Phase 1: Basic Monitoring and Reporting (observe mode)
- Can be built and tested now on the Windows test setup; no GPU or server needed.
- **Implemented prototype**: explicitly triggered, read-only health checks for
  backend process state, llama.cpp, the local SQLite memory database, SearXNG,
  and Discord; CPU/RAM, log-volume free space, and backend RSS snapshots;
  bounded SQLite-persisted observations, incidents, and audit events. The
  SQLite integrity probe opens the database read-only. Failed service checks
  open/update incidents immediately; resource thresholds require duration
  confirmation and bounded gaps, then use a separate recovery hysteresis.
- **Implemented resource policies**: CPU at or above 90% for 120 seconds,
  recovering at or below 80% for 60 seconds; RAM at or above 90% for 120
  seconds, recovering at or below 85% for 60 seconds; log-volume free space at
  or below 10% for 60 seconds, recovering at or above 15% for 60 seconds.
  Consecutive explicit observations must be no more than 300 seconds apart;
  an excessive gap restarts duration confirmation. These are evidence-based
  samples, not continuous monitoring or guarantees that a condition persisted
  between samples.
- **Implemented interface**: viewer-readable read-only status, observation,
  incident, and saved-report endpoints; an operator-only explicit observation
  trigger; and dashboard controls to view current evidence and download the
  latest saved observation as JSON. Reports reconstruct incident state and
  evidence at the selected observation rather than serializing later incident
  updates. Report generation reads in-memory recorded history only; it does not
  run health probes, write state, diagnose root cause, execute commands, or
  remediate. Fault-injection tests cover threshold timing, oscillation,
  observation gaps, restart persistence, probe failures, read-only database
  checks, historical report fidelity, report generation, and API authorization.
- **Remaining Phase 1 work**: validate threshold defaults on the target
  Proxmox host under representative server workloads, including inference and
  integrated-service activity; measure false-alert rates and sampling-gap
  behavior before treating the defaults as production values. Windows
  prototype results alone do not establish Proxmox suitability. Also remaining:
  automated log analysis, root-cause analysis, severity levels beyond warning,
  incident correlation, curated local knowledge ingestion and read-only RAG,
  Discord notifications, and any recurring collection (which must be
  separately designed and explicitly approved). None are enabled by this
  prototype.
- The prototype does not perform scheduled or automatic observations, access
  a RAG database, analyze logs, send notifications, execute commands, or
  remediate failures. Histories and threshold evidence persist across backend
  restarts within the configured bounded SQLite retention.
- **Exit criteria**: not yet met. After the target Proxmox host and integrated
  services are available, validate probes and threshold defaults under
  representative server workloads, measure false-alert rates over an adequate
  observation period, assess sampling gaps, and review report accuracy before
  expanding the system. Windows test results are prototype evidence only.

### Phase 2: Auto-Remediation for Safe Operations
- Action registry, Tier 0/1 actions, verification, rollback, rate limiting.
- Schema-constrained repair proposals from the local model; backend executor
  validation; runbook execution; approval workflow for Tier 2/3. The model
  cannot authorize its own output.
- Scheduled maintenance coordinator: drain and gate normal AI traffic, load
  an eligible installed diagnostic model with its versioned knowledge
  package, run permitted tasks, then restore the previous model and reopen
  traffic only after health checks.
- Create reviewed diagnostic-model knowledge files: system guide, diagnostic
  model profile/evaluation criteria, platform-specific references, and
  incident examples. Test retrieval and ensure learned content stays draft
  until reviewed.
- Add application/model updates only after allowlisting, verification,
  rollback, and safe-window behavior are tested. Host, kernel, GPU driver,
  ROCm, and firmware updates remain approval-only.
- **Exit criteria**: > 90% of Tier 1 fixes verified successful in testing; no restart loops under fault injection.

### Phase 3: Advanced Diagnostics and ML-Based Detection
- Log template clustering, statistical/ML anomaly detection, latency baselines.
- LLM-assisted hypothesis ranking and report writing.
- Trend and predictive alerts (disk filling, memory growth).
- **Exit criteria**: anomaly detection precision/recall targets met on recorded incidents.

### Phase 4: Self-Learning and Knowledge Base Updates
- Record user approval/denial reasons and independently verified repair
  outcomes; distinguish user approval from repair success.
- Draft runbook generation from resolved incidents; review UI; versioned
  retrieval/evaluation sets and runbook success-rate tracking.
- Evaluate bounded autonomous authorization for individually allowlisted
  Tier 2 actions only after explicit opt-in and staged evidence, safety tests,
  canary operation, and tested revocation/rollback. The deterministic policy
  engine authorizes; model confidence and feedback alone do not.
- Keep Tier 3 actions approval-only; feedback never silently changes action
  permissions, risk tiers, model weights, or trusted KB content.
- **Exit criteria**: reviewed KB additions measurably reduce escalations, and
  any enabled autonomous action meets documented reliability and recovery
  targets on the applicable platform/version.

---

## 9. Safety & Security

### 9.1 Sandboxing and Isolation
- The agent runs as a dedicated low-privilege account with only the
  permissions its actions need; no administrator/root by default.
- Actions execute via a fixed registry using argument arrays (never shell
  string interpolation); paths are validated against an allowlist of
  application directories.
- The LLM has no tool access beyond choosing from registry IDs; its output is
  schema-validated and passed to the backend executor, which independently
  checks every action and parameter before execution.

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
- **Local RAG storage**: diagnostic records, procedures, known issues,
  embeddings, and vector index stay on local storage. Embedding and retrieval
  operate locally; no diagnostic payload is sent to cloud AI or external
  vector services. Qdrant is the planned production candidate and must be
  validated locally on the target deployment.
- **Proxmox health data**: when deployed, collect only the required hardware
  and VM health fields through the Proxmox API using a dedicated, least-
  privilege read-only identity or token. Keep credentials in server-side
  secrets storage, redact them from evidence, and retain collected health data
  locally under the diagnostics retention/access policy.
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
- Maintenance-window tests cover timezone/DST boundaries, draining and
  rejecting new work, diagnostic-model selection/failure, restoration of the
  previous model, pausing and dependency-ordered resumption of normal
  workloads, keeping the control plane available, integrity-check failures,
  missed deadlines, process restart during maintenance, and refusing
  unapproved host-level updates.

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
| `DIAG_MAINTENANCE_ENABLED` | `false` | Enable only after configuring and validating the maintenance lifecycle |
| `DIAG_MAINTENANCE_DAYS` | `daily` | Recurrence for the target 03:00–04:00 window |
| `DIAG_MAINTENANCE_START` | `03:00` | Local server time, `HH:MM` |
| `DIAG_MAINTENANCE_END` | `04:00` | Local server time, `HH:MM` |
| `DIAG_MAINTENANCE_TIMEZONE` | unset | Required IANA timezone for the schedule |
| `DIAG_MAINTENANCE_DRAIN_TIMEOUT_S` | `300` | Maximum wait for in-flight work before skipping disruptive work |
| `DIAG_DIAGNOSTIC_MODEL` | unset | Preferred eligible installed model; selection policy may choose another |
| `DIAG_UPDATE_ALLOWLIST` | empty | Explicit update targets eligible for automation |
