# Welcome to AI Server

AI Server, also called the **AI Command Interface**, is a local-first AI and
homelab dashboard. It brings local AI chat, model management, system
monitoring, and an optional Discord bot together in one interface.

The project is being developed on Windows, with a Linux/Proxmox deployment
being prepared and tested in a nested lab.

## What can it do today?

> **✅ Working — Windows development environment**
>
> Local AI chat, model switching, system telemetry, user authentication,
> private conversation history, and on-demand, read-only diagnostics are
> implemented. The optional Discord bot can report status and control the
> active model.

> **🧪 Partially validated — nested Proxmox lab**
>
> The dashboard and backend have been deployed in a nested lab, with HTTPS
> access and read-only Proxmox inventory exercised there. Lab results do not
> establish acceptance on the physical server.

> **📋 Planned — not yet implemented**
>
> Concurrent AI profiles, live remediation, and production vision and image
> generation integrations remain future work.

> **⚠️ Not yet validated — target host**
>
> Linux GPU/ROCm inference and the physical Proxmox deployment still need
> target-host validation.

See the [roadmap](./roadmap/README.md) for detailed status and sequencing.
The [project overview](./architecture/overview.md) explains the components
and their current capabilities.

## Get started

- **Try the Windows development setup:** Follow the
  [Windows quick start](https://github.com/Krazy-Killa/AI-Server#windows-quick-start)
  and the detailed [testing guide](./operations/testing-environment.md).
- **Understand the project:** Read the
  [project overview](./architecture/overview.md) and
  [system architecture](./architecture/README.md).
- **Explore deployment:** Start with the
  [deployment guide](./deployment/README.md) and its Linux/Proxmox runbook.
- **See what's next:** Browse the [project roadmap](./roadmap/README.md).

## Explore the documentation

- [Backend](./backend/README.md) and [API reference](./backend/api.md) —
  backend modules and API contracts.
- [Frontend](./frontend/README.md) — dashboard panels and browser modules.
- [Security](./security/README.md) — authentication, sessions, and access,
  including the [authentication guide](./security/authentication.md).
- [Operations](./operations/README.md) — configuration, testing, and
  infrastructure contracts.
- [Diagnostics](./diagnostics/README.md) — current observations and the
  proposed self-healing design.
- [GPU](./gpu/README.md) — hardware integration and validation.
- [Project context](./project-context.md) — detailed contributor and AI
  session onboarding.

## How to read status callouts

Throughout these guides, **Working** identifies implemented behavior in the
specified environment; **Partially validated** identifies scoped evidence,
not full acceptance; **Planned** identifies future work; and **Not yet
validated** identifies behavior that still needs testing. Always check the
environment and scope stated in each callout.
