# Maintenance Window Automation - BGP v1.0.0

## First public release

v1.0.0 is the first public BGP maintenance-window release.

Validated runtime:

```text
Windows 11
Python 3.12
```

Official installation is **Git clone + editable install**.

The application performs read-only operational collection and does not configure network devices.

## Network-platform scope

| Source | v1.0.0 platform |
| --- | --- |
| PyEZ / NETCONF | Juniper Junos only |
| SSH CLI JSON | Juniper Junos only |
| gNMI / OpenConfig | Juniper Junos validated |
| Manual JSON/XML | Offline input |

Cisco IOS XR and Nokia SR OS are future research targets for the gNMI/OpenConfig path only. They are not supported in this release.

## Included capabilities

- BGP State BEFORE/AFTER comparison.
- BGP Session Health BEFORE/AFTER comparison.
- Single-device and multi-device workflows.
- Source-native RAW evidence plus normalized per-device snapshots.
- Same-source enforcement for official comparisons.
- Requested-source versus actual-source/fallback visibility.
- Session-restart detection using snapshot interval and BGP uptime continuity.
- Flap-count increase and flap-counter reset detection.
- New family/table detection.
- **Missing family/table detection** when a family present BEFORE is absent AFTER.
- Meaningful prefix-loss policy that ignores increases and small normal churn.
- Persistent pre-existing unhealthy-peer visibility.
- `FULL`, `PARTIAL`, and `NOT_EVALUATED` Session Health coverage.
- One compiled JSON / Summary TXT / Detail TXT / Executive PDF report.
- Local web GUI and CLI.
- Public-repository sanitization/security audit in CI.
- **348 automated offline tests** in the final release gate.

## Why missing families matter

A BGP peer can remain `Established` while an AFI-SAFI/table disappears. `missing_family_after` is therefore a visible `WARNING`: losing a family can mean losing the table and every route/prefix carried by it.

## Security modes

### Compatibility Mode - default

The release favors immediate compatibility on trusted management networks:

- SSH unknown host keys can be accepted.
- PyEZ/NETCONF host-key verification is disabled.
- gNMIc can run with non-TLS `--insecure` transport.

### Advanced Secure Mode - optional

Operators with known-host management and/or a TLS PKI can enable host-key verification and gNMI TLS/mTLS in `config/connections/settings.json`.

See `docs/ADVANCED_SECURITY.md`.

## Sanitized real-engine demo

The repository includes documentation-only synthetic evidence generated through the real parser/comparison/reporting path:

- `docs/examples/MW_DEMO_BGP_001_summary.txt`
- `docs/examples/MW_DEMO_BGP_001_detail.txt`
- `docs/examples/MW_DEMO_BGP_001_executive_report.pdf`
- `docs/images/MW_DEMO_BGP_001_gui_result.png`
- `docs/images/MW_DEMO_BGP_001_gui_main.png`

The final demonstration contains one occurrence of each of these key findings:

```text
session_restart_detected
flap_count_increased
flap_count_reset
new_family_after
missing_family_after
prefix_delta
persistent_unhealthy_peer
```

No production/customer evidence is included.

## Installation

Follow `docs/WINDOWS_INSTALLATION.md`.

## Planned direction

The roadmap first extends the common State workflow to LDP, IS-IS, OSPF, and RSVP. Advanced modules begin again with BGP after that State layer is complete.

Cross-vendor work is planned only for gNMI/OpenConfig and starts with capability/model/encoding/path discovery before Cisco IOS XR or Nokia SR OS can be declared supported.

Linux validation remains demand-driven.

## Feedback

Issues and sanitized operator feedback are welcome for Junos coverage, OpenConfig leaf availability, report usefulness, future protocol priorities, and demand for Linux/cross-vendor validation.

## Author

Isaac J. Graterol

- isaacjgraterol@gmail.com
- https://www.linkedin.com/in/inggraterol
