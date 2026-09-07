# Sanitized example reports

This folder demonstrates the actual v1.0.0 reporting model without publishing production evidence.

The example is synthetic and uses only documentation address space:

- `192.0.2.0/24`
- `198.51.100.0/24`
- `203.0.113.0/24`
- `2001:db8::/32`

## How the demo is produced

The demo is not a hand-edited report mockup. Synthetic Junos/PyEZ XML evidence is passed through the real parsing, normalized snapshot, BGP State comparison, Session Health, Full Report, Executive PDF, and GUI-rendering code paths.

This keeps the public example aligned with actual rule behavior.

## Expected demo result

```text
Overall                     WARNING
BGP State                   PASS
BGP Session Health          WARNING

session_restart_detected     1
flap_count_increased         1
flap_count_reset             1
new_family_after             1
missing_family_after         1
prefix_delta                 1
persistent_unhealthy_peer    1
```

The example intentionally demonstrates that endpoint BGP State can remain `PASS` while Session Health identifies an in-window degradation/event.

`missing_family_after` is important because the peer itself may remain `Established` while an AFI-SAFI/table disappears, potentially removing all routes/prefixes carried by that table.

The single `prefix_delta` is a meaningful prefix loss under the actual v1 rule. Normal counter increases are not presented as health degradation.

## Files

- [`MW_DEMO_BGP_001_summary.txt`](MW_DEMO_BGP_001_summary.txt) - structured global/per-device overview.
- [`MW_DEMO_BGP_001_detail.txt`](MW_DEMO_BGP_001_detail.txt) - peer/family before/after evidence and rule messages.
- [`MW_DEMO_BGP_001_executive_report.pdf`](MW_DEMO_BGP_001_executive_report.pdf) - three-page executive/operator report.
- [`../images/MW_DEMO_BGP_001_gui_result.png`](../images/MW_DEMO_BGP_001_gui_result.png) - real result-page renderer.
- [`../images/MW_DEMO_BGP_001_gui_main.png`](../images/MW_DEMO_BGP_001_gui_main.png) - real main-page renderer.

Do not use the documentation addresses as production inventory values.
