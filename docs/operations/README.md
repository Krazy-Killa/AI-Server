# Operations Documentation

This folder collects operator-facing configuration, testing, and
infrastructure-contract guidance for development and deployment preparation.

## Guides

- [Configuration](./configuration.md) — environment variables, local
  configuration, account administration, and secret-handling requirements.
- [Testing Environment](./testing-environment.md) — Windows prototype checks,
  the nested Proxmox lab, and the limits of each environment's evidence.
- [Portable Infrastructure Contracts](./infrastructure-contracts.md) —
  read-only inventory expectations and proposal-only future action contracts.

## Scope

Windows and WSL checks validate only the paths they exercise. Nested-lab
results are Proxmox-lab evidence, not physical-host acceptance. The
infrastructure contracts describe boundaries and data expectations; proposal
types do not provide operational routes or execute actions.
