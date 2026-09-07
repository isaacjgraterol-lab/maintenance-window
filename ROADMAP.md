# Roadmap

This file describes planned work only. It does not promise delivery dates or implemented behavior.

## Current release - v1.0.0

Validated environment:

```text
Host OS: Windows 11
Python:  3.12
Network platform: Juniper Junos
```

Current functional scope:

```text
BGP Basic v1
├── BGP State
├── BGP Session Health
├── BEFORE / AFTER snapshots
├── multi-device comparison
├── Summary TXT / Detail TXT / JSON / Executive PDF
├── CLI
└── local GUI
```

Current source scope:

```text
PyEZ / NETCONF     -> Juniper Junos only
SSH CLI JSON       -> Juniper Junos only
gNMI / OpenConfig  -> Juniper Junos validated in v1.0.0
Manual JSON/XML    -> offline input
```

## Phase 1 - stabilize BGP Basic

Keep the current BGP Basic contract stable while addressing operator feedback, source coverage, error handling, test coverage, and documentation quality.

## Phase 2 - protocol State expansion

Planned, not implemented:

- LDP State.
- IS-IS State.
- OSPF State.
- RSVP State.

Each protocol should reuse the same operational pipeline:

```text
collect -> preserve RAW -> normalize -> snapshot -> compare -> report
```

The objective is one maintenance-window application, one multi-device workflow, and one GUI/report model rather than a separate tool per protocol.

## Phase 3 - advanced modules, beginning again with BGP

After the State layer is complete across the planned protocols, advanced validation starts again with BGP.

### BGP Routes / Prefixes

Planned, not implemented:

- received-route snapshots;
- advertised-route snapshots;
- added, removed, and changed prefixes;
- neighbor, family, VRF, and prefix filters;
- safety limits for large route tables.

### BGP VPN / Services

Planned, not implemented:

- VPNv4 and VPNv6;
- EVPN and L2VPN signaling;
- route-target and service-table validation;
- RD, RT, VRF, family, and route-type filters.

Advanced modules for LDP, IS-IS, OSPF, and RSVP can follow when operational requirements justify them.

## Cross-vendor gNMI / OpenConfig research

**Future research only - not implemented in v1.0.0.**

Candidate platforms:

- Cisco IOS XR.
- Nokia SR OS.

The multivendor path is gNMI/OpenConfig only. PyEZ and the Junos SSH CLI JSON collector remain Juniper Junos specific.

Before a new platform can be declared supported, the implementation should validate at least:

1. gNMI `Capabilities` discovery.
2. gNMI service version.
3. supported encodings.
4. advertised OpenConfig models and revisions.
5. OpenConfig BGP path availability.
6. vendor/platform deviations and missing leaves.
7. mapping into the common normalized BGP schema.
8. `FULL` / `PARTIAL` / `NOT_EVALUATED` coverage behavior.
9. real-device lab evidence and regression fixtures.

The intended future flow is:

```text
gNMI connection
      |
Capabilities
      |
model + encoding discovery
      |
platform capability/path profile
      |
OpenConfig collection
      |
common normalized BGP model
```

The project should not assume one universal BGP path or identical leaf coverage across vendors.

## Cross-cutting improvements

Potential work alongside the functional roadmap:

- configurable prefix-loss thresholds;
- clearer GUI coverage/source visualization;
- gNMI capability and deviation profiles;
- additional installation/troubleshooting examples;
- continued security and publication-gate hardening.

## Demand-driven platform work

### Linux

Linux is not part of the v1.0.0 validation statement. Validation may be prioritized if community feedback shows real operator demand.

### Hosted / no-install reporting

A hosted experience for viewing or generating reports from explicitly uploaded and sanitized artifacts may be explored later. It is exploratory, not committed roadmap work.

## Explicitly outside the current scope

- device configuration changes;
- automatic remediation;
- historical dashboard;
- public API;
- MCP server;
- external orchestration platform.

The project remains focused on read-only maintenance-window evidence, comparison, and reporting.
