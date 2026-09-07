# Configuration

- `connections/settings.json` - collector connection/security settings.
- `audits/bgp/evidence_basic.json` - reusable BGP Basic capture.
- `audits/bgp/state.json` - BGP State analysis contract.
- `audits/bgp/session_health.json` - BGP Session Health analysis contract.

`connections/settings.json` ships in **Compatibility Mode** so operators can connect on trusted management networks without first deploying host-key verification or gNMI TLS. Optional Advanced Secure Mode is documented in [`docs/ADVANCED_SECURITY.md`](../docs/ADVANCED_SECURITY.md).

Future features remain in `ROADMAP.md` until implemented, tested, and documented. Cisco IOS XR/Nokia SR OS are not current selectable platforms; future multivendor work is limited to the gNMI/OpenConfig path.
