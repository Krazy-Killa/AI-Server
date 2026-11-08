# Diagnostics Documentation

This folder describes the current observe-only diagnostics capability and the
longer-term design for evidence-based maintenance workflows.

> **✅ Working — observe-only diagnostics**
>
> Explicit, bounded observations, incident history, reviewed local runbook
> retrieval, and disconnected simulations are implemented.

> **📋 Planned — not yet implemented**
>
> Scheduling, model-driven diagnosis, and live remediation are future work;
> simulations do not execute host or service operations.

## Guide

- [AI-Powered Diagnostics & Self-Healing](./ai-diagnostics-self-healing.md) —
  architecture, safety constraints, staged implementation plan, and status of
  diagnostic observations, runbooks, simulations, scheduling, and remediation.

## Current boundary

Explicitly requested, bounded, read-only observations and persistent incident
history are implemented. Reviewed local runbook retrieval and deterministic
maintenance/remediation simulations are also available. Scheduling,
model-driven diagnosis, and live remediation are not implemented; simulations
do not execute host or service operations.
