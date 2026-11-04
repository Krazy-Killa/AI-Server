# Deployment Documentation

This folder documents the staged transition from Windows development to the
intended Linux/Proxmox deployment.

## Guide

- [Linux/Proxmox Transition Runbook](./linux-proxmox-transition.md) — current
  nested-lab deployment state, read-only Proxmox inventory setup, deployment
  decisions, and target-host acceptance checks.

## Status and boundaries

The Windows machine is the active shared-application development environment.
The nested Proxmox guest supports limited deployment and integration testing;
its results do not establish physical-host acceptance. Production service
exposure, HTTPS proxy behavior, boot/reboot recovery, and GPU runtime
compatibility require their separately documented validation gates.

Consult the [roadmap](../roadmap/README.md) for phase status and sequencing.
