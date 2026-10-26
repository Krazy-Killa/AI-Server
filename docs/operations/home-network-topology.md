# Household Network Topology and Future Infrastructure Notes

## Status and provenance

This is a planning reference based on the household topology and possible
server roles provided for the project. The current-state descriptions have not
been independently inspected or validated from the AI Server. Confirm the
topology, device models, firmware, management paths, and addressing on site
before using this document to configure services or integrations.

This document intentionally contains no management IP addresses, passwords,
API tokens, SSH keys, or other access secrets. Store any required credentials
in the appropriate private configuration or secret store, never in this
document or browser code.

## Current topology (as reported)

```text
Internet
   |
Xfinity Gateway (bridge mode; ISP connectivity)
   |
Google WiFi Mesh (primary router and mesh platform)
   |
   +-- AI Server
   +-- Household devices
   `-- TP-Link Access Point (AP mode, custom firmware)
          +-- Quest headset
          +-- Gaming consoles
          `-- High-bandwidth / low-latency devices
```

This is a logical overview, not a verified network diagram. Cabling, mesh
backhaul, VLANs, subnets, DHCP/DNS ownership, firewall policy, and the exact
attachment point of each device are not specified.

## Components and possible access

### Xfinity gateway

- Reported to operate in bridge mode and provide ISP connectivity.
- Not intended for direct management by the AI Server platform.
- No telemetry or management integration is selected.

### Google WiFi mesh

- Reported as the primary router and household mesh platform, managed through
  the Google Home ecosystem.
- May be observable indirectly through permitted network-health checks.
- Treat as a limited-visibility component unless a supported, least-privilege
  telemetry mechanism is identified and reviewed. No direct integration is
  implemented or selected.

### TP-Link access point

- Reported to operate in access-point rather than router mode, run custom
  firmware, use a static management address, and be reachable over SSH.
- This is a candidate for future observe-only diagnostics, subject to
  on-site verification of the model, firmware, SSH configuration, and access
  controls.
- Possible read-only telemetry includes reachability, system load, memory
  utilization, wireless client count, interface statistics, wireless
  performance metrics, and system logs.
- No SSH provider, telemetry schema, credentials, or integration is
  implemented. Do not infer that an SSH connection is authorized for the
  application or use general-purpose shell access as an integration design.

### AI Server

The intended centralized household operations platform may provide:

- AI chat and research
- Diagnostics and maintenance
- Network-health monitoring and incident tracking
- Infrastructure inventory and operational runbooks
- Future conversational voice interaction

The server's production deployment, network placement, interfaces, and
management exposure remain subject to the deployment and security acceptance
gates in the [Linux/Proxmox transition runbook](../deployment/linux-proxmox-transition.md).

## Future network-aware diagnostics

Potential future work may correlate WAN, LAN, Wi-Fi, and service-level
observations to distinguish likely ISP outages, router failures, wireless
congestion, access-point problems, and client/device-specific issues. Example
requests include “The internet is down,” “The Wi-Fi is slow,” and “The Quest
headset is lagging.” Reports should identify evidence and uncertainty, and
historical observations may support trend and recurring-issue analysis.

This remains a concept, not an implemented integration. Initial telemetry must
be explicitly configured, least-privilege, and observe-only. An unavailable
source must remain unavailable rather than being interpreted as healthy.
Recommendations must not silently become actions. Any later remediation needs
separate authorization, confirmation, audit, verification, and a tested
recovery path. See the [network-aware diagnostics roadmap concept](../roadmap/roadmap.md#candidate-backlog--not-scheduled).

## Future conversational household interface

The long-term concept is to let household members interact with diagnostics,
maintenance, and household services through natural conversation without
requiring direct dashboard access. Potential components include local
speech-to-text, maintenance AI, user-facing AI, and text-to-speech. Example
requests include:

- “Why is the internet slow?”
- “Did anything happen during maintenance last night?”
- “Is the AI server healthy?”
- “Can you diagnose the network?”

Identity, enrollment, authorization, audio privacy/retention, supported
devices, and optional proactive notifications remain undecided. Voice must not
itself establish identity or grant privileges. See the
[conversational household interface roadmap concept](../roadmap/roadmap.md#candidate-backlog--not-scheduled).

## Possible managed Wi-Fi evaluation

UniFi and TP-Link Omada are potential future managed-Wi-Fi platforms to
evaluate, not selected purchases or integrations. Desired capabilities may
include supported telemetry access, controller integration, device inventory,
client statistics, event logging, and data suitable for infrastructure-aware
diagnostics. Evaluate actual hardware, licensing, local API support, privacy,
and least-privilege access before choosing a platform.

## Possible multi-GPU role separation

The planned role split is to keep the RX 6800 XT dedicated to Maintenance AI
and add a second GPU for household-facing User AI:

| Candidate GPU role | Possible workloads |
| --- | --- |
| RX 6800 XT — maintenance AI | Diagnostics, incident analysis, runbook workflows, system-health monitoring, network diagnostics, and scheduled maintenance |
| Possible second GPU — user AI | Chat, research, Discord integrations, vision, and household interactions |

Possible second-GPU candidates are the Radeon RX 7900 XT/XTX or RX 9070 XT.
The current tradeoff is greater VRAM capacity as a reason to consider the
7900 XT/XTX, versus the 9070 XT's newer RDNA 4 architecture and potential
speed/efficiency advantages. This is a candidate comparison, not a measured
workload benchmark; the exact 7900 variant is undecided. The second GPU is not
selected or acquired. Until it is validated, single-GPU/single-runtime model
handoff remains the interim design, not concurrent operation of both roles.
Power/cooling, host compatibility, workload isolation, runtime support, and
performance have not been established. This does not change the current
one-GPU deployment plan or represent validated hardware sizing.
