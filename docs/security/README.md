# Security Documentation

This folder documents application identity, sessions, authorization, and the
security boundaries around dashboard and service access.

## Guide

- [Authentication & Session Management](./authentication.md) — local and
  Proxmox sign-in, application sessions, role mapping, protected routes, and
  deployment security checks.

## Key boundaries

- The backend, not UI visibility, enforces identity and role authorization.
- Proxmox identities require an explicit local role mapping; Proxmox
  authentication alone does not grant dashboard access.
- The Discord bot uses a separate, scoped service credential rather than a
  dashboard session.
- Production HTTPS, reverse-proxy, and physical-host security behavior remain
  to be validated on the target deployment.
