# AI Server Documentation

AI Server is a local-first AI and homelab dashboard with a browser interface,
a Python backend, and an optional Discord bot. It is under development on
Windows, with a Linux/Proxmox deployment planned and partially validated in a
nested lab. See the [roadmap](./roadmap/README.md) for what is implemented,
planned, and still awaiting validation.

Project guides are grouped by subject. Start with the roadmap for current
implementation status and sequencing; each subsystem guide distinguishes
implemented behavior from planned or unverified work.

| Folder | Contents |
| --- | --- |
| [architecture/](./architecture/README.md) | Project overview, components, and data flow |
| [backend/](./backend/README.md) | Backend modules and API contracts |
| [security/](./security/README.md) | Authentication, sessions, and authorization |
| [operations/](./operations/README.md) | Configuration, testing, and infrastructure contracts |
| [deployment/](./deployment/README.md) | Linux and Proxmox transition runbook |
| [diagnostics/](./diagnostics/README.md) | Observe-only diagnostics and proposed self-healing design |
| [gpu/](./gpu/README.md) | GPU integration status and deployment considerations |
| [frontend/](./frontend/README.md) | Dashboard panels and browser-module structure |
| [roadmap/](./roadmap/README.md) | Project status, phases, and next steps |

## Main references

- [Project context and AI session handoff](./project-context.md)
- [Project roadmap](./roadmap/README.md)
- [Architecture overview](./architecture/README.md)
- [Backend API](./backend/api.md)
- [Authentication and session management](./security/authentication.md)
- [Linux/Proxmox transition runbook](./deployment/linux-proxmox-transition.md)
