"""Portable, non-executing contracts for Proxmox-facing dashboard features."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ProxmoxInventoryContract:
    method: Literal["GET"]
    path: str
    minimum_role: Literal["viewer"]
    required_privileges: tuple[str, ...]
    returned_fields: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]


PROXMOX_INVENTORY_CONTRACT = ProxmoxInventoryContract(
    method="GET",
    path="/api2/json/cluster/resources?type=vm",
    minimum_role="viewer",
    required_privileges=("Sys.Audit", "VM.Audit"),
    returned_fields=("name", "vmid", "node", "type", "status"),
    forbidden_capabilities=(
        "create",
        "configure",
        "power",
        "snapshot",
        "console",
        "storage",
    ),
)
_VM_OPERATIONS = frozenset({"start", "shutdown", "stop", "reboot"})
_NETWORK_OPERATIONS = frozenset({"inspect", "configure", "enable", "disable"})
_NETWORK_SERVICES = frozenset(
    {"dhcpv4", "dhcpv6", "dns", "web", "routing_firewall"}
)
_GAME_SERVER_OPERATIONS = frozenset(
    {"inspect", "start", "stop", "restart", "backup", "restore"}
)
_AUTHORIZED_ROLES = frozenset({"viewer", "operator", "admin"})


@dataclass(frozen=True)
class ProxmoxGuestReference:
    node: str
    vmid: int

    def __post_init__(self) -> None:
        if not isinstance(self.node, str) or not self.node.strip() or len(self.node) > 128:
            raise ValueError("Proxmox guest node is invalid.")
        if (
            isinstance(self.vmid, bool)
            or not isinstance(self.vmid, int)
            or self.vmid < 1
        ):
            raise ValueError("Proxmox guest VMID must be a positive integer.")


def _validate_proposal(
    *,
    requested_by_role: str,
    confirmation: str | None,
    expected_confirmation: str,
) -> None:
    if requested_by_role != "admin":
        raise ValueError("Infrastructure change proposals require the admin role.")
    if confirmation != expected_confirmation:
        raise ValueError("Infrastructure change proposal requires explicit confirmation.")


@dataclass(frozen=True)
class ProxmoxVMActionProposal:
    operation: Literal["start", "shutdown", "stop", "reboot"]
    guest: ProxmoxGuestReference
    requested_by_role: str
    confirmation: str | None
    execution_mode: Literal["proposal_only"] = "proposal_only"

    def __post_init__(self) -> None:
        if self.operation not in _VM_OPERATIONS:
            raise ValueError("Proxmox VM operation is not supported.")
        expected = f"PROPOSE VM {self.guest.vmid} {self.operation.upper()}"
        _validate_proposal(
            requested_by_role=self.requested_by_role,
            confirmation=self.confirmation,
            expected_confirmation=expected,
        )
        if self.execution_mode != "proposal_only":
            raise ValueError("Proxmox operations are proposal-only in this phase.")

    @staticmethod
    def confirmation_phrase(vmid: int, operation: str) -> str:
        return f"PROPOSE VM {vmid} {operation.upper()}"


@dataclass(frozen=True)
class NetworkServiceProposal:
    service: Literal["dhcpv4", "dhcpv6", "dns", "web", "routing_firewall"]
    operation: Literal["inspect", "configure", "enable", "disable"]
    scope: str
    requested_by_role: str
    confirmation: str | None = None
    execution_mode: Literal["proposal_only"] = "proposal_only"

    def __post_init__(self) -> None:
        if self.service not in _NETWORK_SERVICES or self.operation not in _NETWORK_OPERATIONS:
            raise ValueError("Network-service proposal is not supported.")
        if not isinstance(self.scope, str) or not self.scope.strip() or len(self.scope) > 256:
            raise ValueError("Network-service proposal scope is invalid.")
        if self.operation != "inspect":
            expected = f"PROPOSE {self.operation.upper()} {self.service.upper()}"
            _validate_proposal(
                requested_by_role=self.requested_by_role,
                confirmation=self.confirmation,
                expected_confirmation=expected,
            )
        elif self.requested_by_role not in _AUTHORIZED_ROLES:
            raise ValueError("Network-service inspection requires an authenticated role.")
        if self.execution_mode != "proposal_only":
            raise ValueError("Network-service operations are proposal-only in this phase.")

    @staticmethod
    def confirmation_phrase(operation: str, service: str) -> str:
        return f"PROPOSE {operation.upper()} {service.upper()}"


@dataclass(frozen=True)
class GameServerProposal:
    instance_id: str
    operation: Literal["inspect", "start", "stop", "restart", "backup", "restore"]
    requested_by_role: str
    confirmation: str | None = None
    execution_mode: Literal["proposal_only"] = "proposal_only"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.instance_id, str)
            or not self.instance_id.strip()
            or len(self.instance_id) > 128
        ):
            raise ValueError("Game-server instance ID is invalid.")
        if self.operation not in _GAME_SERVER_OPERATIONS:
            raise ValueError("Game-server operation is not supported.")
        if self.operation != "inspect":
            expected = (
                f"PROPOSE {self.operation.upper()} GAME SERVER {self.instance_id}"
            )
            _validate_proposal(
                requested_by_role=self.requested_by_role,
                confirmation=self.confirmation,
                expected_confirmation=expected,
            )
        elif self.requested_by_role not in _AUTHORIZED_ROLES:
            raise ValueError("Game-server inspection requires an authenticated role.")
        if self.execution_mode != "proposal_only":
            raise ValueError("Game-server operations are proposal-only in this phase.")

    @staticmethod
    def confirmation_phrase(operation: str, instance_id: str) -> str:
        return f"PROPOSE {operation.upper()} GAME SERVER {instance_id}"
