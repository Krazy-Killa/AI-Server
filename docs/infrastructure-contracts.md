# Portable Infrastructure Contracts

These contracts define data and authorization expectations for portable
development. They are not API routes, providers, or permission grants. No
proposal type in this document can perform an operation.

## Proxmox inventory

`ai-backend/proxmox_contracts.py` defines the current inventory contract:

- `GET /api2/json/cluster/resources?type=vm`
- Dashboard minimum role: `viewer`
- Expected Proxmox privileges: `Sys.Audit` and `VM.Audit`, scoped as narrowly
  as practical
- Returned guest fields: `name`, `vmid`, `node`, `type`, and `status`
- Forbidden capabilities for this integration: create, configure, power,
  snapshot, console, and storage changes

The actual client is read-only. The token remains server-side; a Proxmox
response or dashboard inventory record is never treated as authorization to
mutate a guest.

## Proposal-only future contracts

The following Python data contracts capture requirements for later planning.
They have no routes or execution adapters.

| Contract | Inspection | Proposed changes |
|---|---|---|
| `ProxmoxVMActionProposal` | VM reference is node plus positive VMID. | Start, shutdown, stop, and reboot intents require `admin`, an exact operation-specific confirmation phrase, and `execution_mode="proposal_only"`. |
| `NetworkServiceProposal` | Supported scope: DHCPv4, DHCPv6, DNS, web, and routing/firewall. Authenticated viewer/operator/admin roles may propose inspection. | Configure/enable/disable intents require `admin`, a non-empty scope, exact confirmation, and proposal-only mode. |
| `GameServerProposal` | Instance ID is required; authenticated viewer/operator/admin roles may propose inspection. | Start/stop/restart/backup/restore intents require `admin`, exact instance-and-operation confirmation, and proposal-only mode. |

These types do not establish that an operation is safe, available, or
authorized on a real host. Future API routes must independently enforce roles,
CSRF/origin protections, least-privilege provider permissions, scoped
confirmation, auditability, preconditions, verification, failure handling, and
recovery. Live VM operations remain deferred until the roadmap's integration
gate is met.

## Failure and simulation boundaries

Proxmox inventory failures remain explicit: unconfigured is distinct from a
valid empty inventory, and upstream failures return unavailable rather than
cached or sample records. No contract turns a failed check into a successful
default.

Maintenance/remediation simulations use only fixed in-memory fixtures and a
deterministic mock clock. They do not import these proposal contracts as an
executor and have no path to Proxmox, host services, process control, shell,
databases, or persistent application state.
