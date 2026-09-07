# Development Guide

## Validated development environment

v1.0.0 CI validates:

```text
Windows 11 runner
Python 3.12
```

The project may work elsewhere, but unsupported environments should not be presented as validated without regression evidence.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Quality gate

Run the same logical gate as CI:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests tools
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\tools\public_release_check.py --root .
```

## Architecture rule

Keep responsibilities replaceable:

```text
collector
parser
normalizer
snapshot adapter
comparison rules
report formatter
UI adapter
```

Do not place protocol-comparison logic in the GUI.

## Adding or changing a parser

1. Preserve the source-native RAW evidence.
2. Parse only explicit source fields/leaves.
3. Group records by stable identity.
4. Normalize only documented values.
5. Keep absent optional data absent.
6. Add safe synthetic fixture tests.
7. Add malformed/partial-input tests.
8. Validate report coverage semantics.

## Adding a protocol

Reuse the common operational pattern:

```text
collect -> preserve RAW -> normalize -> snapshot -> compare -> report
```

The public roadmap currently plans State modules for LDP, IS-IS, OSPF, and RSVP before advanced protocol modules are expanded.

## gNMI/OpenConfig platform research

The future multivendor route is gNMI/OpenConfig only.

Before adding Cisco IOS XR, Nokia SR OS, or another platform, gather and preserve sanitized evidence for:

- gNMI `Capabilities`;
- supported encodings;
- advertised OpenConfig models/revisions;
- BGP path availability;
- missing/deviating leaves;
- normalized-schema equivalence;
- `FULL` / `PARTIAL` / `NOT_EVALUATED` behavior.

Do not add a selectable GUI vendor until at least two platforms have real-device validated support.

## Test expectations

Behavior changes should cover the relevant happy path and failure boundary. Important areas include:

- missing fields and partial coverage;
- duplicate records;
- BEFORE/AFTER mismatch;
- source fallback and same-source enforcement;
- multi-device behavior;
- family appearance/disappearance;
- meaningful prefix-loss thresholds;
- path/MW-ID safety;
- report-download boundaries;
- Compatibility/Advanced Secure settings;
- report serialization and GUI presentation.

## Public-data policy

Never commit real credentials, real inventory, customer/site identifiers, unreviewed RAW evidence, internal filesystem paths, or operational addresses.

Use documentation address space in public fixtures:

```text
192.0.2.0/24
198.51.100.0/24
203.0.113.0/24
2001:db8::/32
```

Run the publication scanner before every public release or pull request.
