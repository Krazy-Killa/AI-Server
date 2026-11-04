# GPU Documentation

This folder records GPU roles, Windows development evidence, and the
experimental Linux/Proxmox compute and telemetry work.

## Guide

- [GPU Integration Plan](./gpu-plan.md) — planned hardware roles, Windows
  Vulkan and DirectML testing, Linux telemetry, and ROCm/Proxmox compatibility
  gates.

## Status and boundaries

Windows Vulkan inference and Windows GPU telemetry have been exercised. The
Linux `amdgpu` telemetry provider is implemented and fixture-tested, but live
Linux readings and ROCm/HIP inference on the intended Proxmox host remain
unverified. Windows GPU results do not establish Linux or Proxmox support.
