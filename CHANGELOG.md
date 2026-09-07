# Changelog

## 1.0.0 - Public release

### Added

- BGP State and BGP Session Health before/after validation.
- Single-device and multi-device maintenance-window workflows.
- Source-native RAW evidence plus normalized per-device snapshots.
- PyEZ / NETCONF and SSH CLI JSON collectors for Juniper Junos.
- gNMI / OpenConfig collection validated on Juniper Junos through gNMIc/WSL.
- Local GUI and CLI.
- Summary TXT, Detail TXT, JSON, and Executive PDF reports.
- Session-restart, flap-increase, flap-reset, family-change, and meaningful prefix-loss findings.
- Explicit Session Health coverage semantics.
- Same-source official comparison guard and source-fallback visibility.
- Windows 11 / Python 3.12 Git-clone installation workflow.
- Compatibility Mode plus optional Advanced Secure Mode settings/documentation.
- Sanitized report/GUI demo generated through the real comparison engine.
- Public-repository sanitization scanner integrated into CI.

### Changed

- Prefix evaluation ignores increases and small normal churn; only meaningful losses affect Session Health.
- MW IDs use a shared Windows-safe validation policy across CLI/GUI entry points.
- GUI report downloads are restricted to generated report locations.
- GUI temporary credentials use the operating-system temporary directory rather than the repository tree.
- Credential dataclass representations redact passwords.
- GUI source labels make current Junos scope and future gNMI/OpenConfig multivendor direction explicit.
- Public documentation was consolidated around operator/developer use rather than internal release-process checklists.
