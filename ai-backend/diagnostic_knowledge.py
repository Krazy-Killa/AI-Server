"""Reviewed, local-only diagnostic runbooks and deterministic retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Literal


Platform = Literal["proxmox-ve", "ai-server"]


@dataclass(frozen=True)
class RunbookStep:
    id: str
    instruction: str
    expected_evidence: str


@dataclass(frozen=True)
class DiagnosticRunbook:
    id: str
    title: str
    summary: str
    version: str
    review_state: Literal["reviewed"]
    platforms: tuple[Platform, ...]
    signals: tuple[str, ...]
    steps: tuple[RunbookStep, ...]
    escalation: str
    owner: str = "AI Server project"
    last_reviewed: str = "2026-10-16"
    source: Literal["built-in"] = "built-in"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


RUNBOOKS: tuple[DiagnosticRunbook, ...] = (
    DiagnosticRunbook(
        id="RB-PVE-API-001",
        title="Proxmox API unavailable or TLS validation fails",
        summary=(
            "Narrow down DNS, API reachability, hostname, trust-chain, and "
            "certificate-policy issues without changing the Proxmox host."
        ),
        version="1.0",
        review_state="reviewed",
        platforms=("proxmox-ve",),
        signals=("proxmox.api.unreachable", "proxmox.api.tls_error"),
        steps=(
            RunbookStep(
                id="confirm-origin",
                instruction=(
                    "Confirm the configured API URL is an HTTPS origin and "
                    "uses the hostname present in the Proxmox API certificate."
                ),
                expected_evidence=(
                    "Configured origin and certificate hostname match; do not "
                    "substitute an IP address unless it is in the certificate."
                ),
            ),
            RunbookStep(
                id="check-trust",
                instruction=(
                    "Check that the configured CA bundle is the intended "
                    "Proxmox CA and is readable by the backend service account."
                ),
                expected_evidence=(
                    "The CA bundle is present, readable, and chains to the "
                    "certificate served by the configured host."
                ),
            ),
            RunbookStep(
                id="inspect-compatibility",
                instruction=(
                    "If Python reports a missing CA keyUsage extension, verify "
                    "whether the explicitly documented nested-lab compatibility "
                    "setting is enabled. Do not disable hostname or chain checks."
                ),
                expected_evidence=(
                    "The issue is isolated to the known extension-policy "
                    "compatibility case, or the sanitized TLS error is retained "
                    "for escalation."
                ),
            ),
        ),
        escalation=(
            "Escalate certificate, hostname, or trust-chain mismatches. Do not "
            "replace certificates, weaken verification, or restart Proxmox as "
            "part of this read-only procedure."
        ),
    ),
    DiagnosticRunbook(
        id="RB-PVE-INVENTORY-001",
        title="Proxmox inventory returns no visible guests",
        summary=(
            "Distinguish a legitimate empty inventory from a token scope or "
            "permission mismatch."
        ),
        version="1.0",
        review_state="reviewed",
        platforms=("proxmox-ve",),
        signals=("proxmox.inventory.empty",),
        steps=(
            RunbookStep(
                id="confirm-expected-guests",
                instruction=(
                    "Confirm that at least one VM or container should currently "
                    "be visible at the configured inventory scope."
                ),
                expected_evidence=(
                    "The expected guest and its Proxmox node are identified, or "
                    "an empty inventory is confirmed as expected."
                ),
            ),
            RunbookStep(
                id="check-token-identity",
                instruction=(
                    "Check the configured token ID and privilege-separated "
                    "identity without displaying or copying the token secret."
                ),
                expected_evidence=(
                    "The intended dedicated inventory token ID is configured; "
                    "the secret remains private in the backend environment."
                ),
            ),
            RunbookStep(
                id="check-acl-scope",
                instruction=(
                    "Review the token's effective ACL scope and read-only "
                    "Sys.Audit and VM.Audit privileges against the intended "
                    "guest inventory."
                ),
                expected_evidence=(
                    "The ACL scope includes the expected guests and grants no "
                    "modify, power, console, or storage privileges."
                ),
            ),
        ),
        escalation=(
            "Escalate if the configured scope and audit privileges appear "
            "correct but expected guests remain absent. Do not add privileges "
            "or change ACLs automatically."
        ),
    ),
    DiagnosticRunbook(
        id="RB-PVE-INVENTORY-002",
        title="Proxmox inventory request returns HTTP 403",
        summary=(
            "Investigate HTTP 401/403 from the read-only inventory API without "
            "exposing credentials or expanding permissions automatically."
        ),
        version="1.0",
        review_state="reviewed",
        platforms=("proxmox-ve",),
        signals=("proxmox.inventory.unauthorized", "proxmox.inventory.forbidden"),
        steps=(
            RunbookStep(
                id="check-token-pair",
                instruction=(
                    "Confirm the token ID and secret are both configured in the "
                    "backend environment; never print either value."
                ),
                expected_evidence=(
                    "The backend has a complete token pair and logs contain no "
                    "token values."
                ),
            ),
            RunbookStep(
                id="check-token-acl",
                instruction=(
                    "In the Proxmox administration interface, review the "
                    "dedicated token's privilege-separation setting and its "
                    "effective read-only ACL at the intended path."
                ),
                expected_evidence=(
                    "The token identity, privilege separation, ACL path, and "
                    "Sys.Audit/VM.Audit privileges match the approved scope."
                ),
            ),
            RunbookStep(
                id="retry-explicitly",
                instruction=(
                    "After an authorized administrator has corrected any "
                    "configuration, use the dashboard's explicit inventory "
                    "refresh and record the resulting HTTP status."
                ),
                expected_evidence=(
                    "A successful read-only response lists only the supported "
                    "guest summary fields, or the sanitized failure remains."
                ),
            ),
        ),
        escalation=(
            "ACL and token changes require an authorized human. Do not broaden "
            "permissions, rotate credentials, or retry repeatedly as an "
            "automated repair."
        ),
    ),
    DiagnosticRunbook(
        id="RB-AI-DIAGNOSTICS-001",
        title="Diagnostic history cannot be persisted",
        summary=(
            "Check the local diagnostics database path, disk capacity, and "
            "service-account access without modifying or deleting database data."
        ),
        version="1.0",
        review_state="reviewed",
        platforms=("ai-server",),
        signals=("diagnostics.store.unavailable",),
        steps=(
            RunbookStep(
                id="check-storage",
                instruction=(
                    "Review the configured memory database path, containing "
                    "filesystem, and available space using approved host "
                    "monitoring."
                ),
                expected_evidence=(
                    "Database location and available space are recorded without "
                    "reading private conversation contents."
                ),
            ),
            RunbookStep(
                id="check-service-access",
                instruction=(
                    "Have an administrator verify that the backend service "
                    "account can access its configured database and directory."
                ),
                expected_evidence=(
                    "Ownership and access match the deployment policy; no "
                    "permission changes are made by this diagnostic."
                ),
            ),
        ),
        escalation=(
            "Escalate database corruption, permission changes, restore, or "
            "migration. Do not delete, recreate, or rewrite diagnostic history."
        ),
    ),
)

_RUNBOOKS_BY_ID = {runbook.id: runbook for runbook in RUNBOOKS}


def get_runbook(runbook_id: str) -> DiagnosticRunbook | None:
    """Return one bundled reviewed procedure, if present."""
    return _RUNBOOKS_BY_ID.get(runbook_id)


def list_runbooks(
    *,
    platform: Platform | None = None,
    signal: str | None = None,
) -> tuple[DiagnosticRunbook, ...]:
    """List only bundled procedures applicable to the requested filters."""
    return tuple(
        runbook
        for runbook in RUNBOOKS
        if (platform is None or platform in runbook.platforms)
        and (signal is None or signal in runbook.signals)
    )


def search_runbooks(
    query: str,
    *,
    platform: Platform | None = None,
    limit: int = 10,
) -> tuple[DiagnosticRunbook, ...]:
    """Search reviewed runbooks deterministically using local lexical matching."""
    terms = tuple(dict.fromkeys(re.findall(r"[a-z0-9._-]+", query.casefold())))
    if not terms:
        return ()

    ranked: list[tuple[int, str, DiagnosticRunbook]] = []
    for runbook in list_runbooks(platform=platform):
        title = runbook.title.casefold()
        identifiers = " ".join((runbook.id, *runbook.signals)).casefold()
        summary = runbook.summary.casefold()
        details = " ".join(
            (
                *(step.instruction for step in runbook.steps),
                *(step.expected_evidence for step in runbook.steps),
                runbook.escalation,
            )
        ).casefold()
        score = sum(
            title.count(term) * 5
            + identifiers.count(term) * 4
            + summary.count(term) * 2
            + details.count(term)
            for term in terms
        )
        if score:
            ranked.append((score, runbook.id, runbook))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in ranked[:limit])
