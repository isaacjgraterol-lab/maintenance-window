# Contributing

Contributions are welcome when they preserve the read-only operational boundary and include safe regression coverage.

## Useful contributions

- parser fixes backed by synthetic fixtures;
- Juniper/OpenConfig platform validation;
- future gNMI capability/deviation research;
- better error handling;
- report and GUI usability improvements;
- documentation corrections;
- security improvements;
- small modular refactors.

## Before opening a pull request

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests tools
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\tools\public_release_check.py --root .
```

## Pull request rules

- Keep device operations read-only.
- Do not add configuration/remediation RPCs to this project scope.
- Do not commit real network data, credentials, inventory, customer/site names, or private filesystem paths.
- Use RFC documentation address space in tests/examples.
- Explain operational impact.
- Include tests for behavior changes.
- Update documentation when a public contract changes.
- Do not claim Cisco IOS XR, Nokia SR OS, Linux, or another platform as supported without real validation and regression evidence.

## Issue reports

Include only sanitized information:

- Python version;
- Windows version;
- collection source;
- sanitized error output;
- safe fixture when possible;
- expected versus observed behavior.

Never post credentials or unsanitized RAW evidence.
