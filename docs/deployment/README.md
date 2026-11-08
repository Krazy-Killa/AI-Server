# Deployment Documentation

This folder documents the staged transition from Windows development to the
intended Linux/Proxmox deployment.

> **🧪 Partially validated — nested Proxmox lab**
>
> Rootless services and HTTPS access have been tested in the nested lab.
> Physical-host deployment and production acceptance are still outstanding.

## Guide

- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — current
  nested-lab deployment state, read-only Proxmox inventory setup, deployment
  decisions, and target-host acceptance checks.

## Status and boundaries

The Windows machine is the active shared-application development environment.
The nested Proxmox guest supports deployment and integration testing; its
results do not establish physical-host acceptance. Rootless service lifecycle
and boot recovery have been tested in the nested guest. NGINX/TLS access was
verified from Windows and iPhone, and signed updater Stage 1 was partially
verified there. Repeat release-sensitive health/reboot checks as needed.
Physical-target service exposure, GPU runtime compatibility, and production
acceptance remain gated.

Consult the [roadmap](../roadmap/README.md) for phase status and sequencing.
