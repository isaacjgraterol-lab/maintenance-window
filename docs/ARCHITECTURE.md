# Architecture

## Design goals

- Read-only operational collection.
- Source-native RAW evidence preserved for traceability.
- One normalized BGP contract regardless of collection source.
- Separate BEFORE and AFTER snapshots per device.
- One compiled multi-device comparison report per MW ID.
- Explicit source/coverage visibility instead of invented data.
- Small replaceable collectors, parsers, engines, reports, and UI adapters.
- No report module performs a second live collection.

## v1.0.0 platform boundary

Validated host/runtime:

```text
Windows 11
Python 3.12
```

Validated network platform:

```text
Juniper Junos
```

Collection scope:

```text
PyEZ / NETCONF     -> Juniper Junos only
SSH CLI JSON       -> Juniper Junos only
gNMI / OpenConfig  -> Juniper Junos validated
Manual JSON/XML    -> offline evidence
```

Cisco IOS XR and Nokia SR OS are future gNMI/OpenConfig research targets only. They are not supported in v1.0.0.

## Main flow

```text
Operator
   |
CLI or local GUI
   |
Inventory + credentials
   |
Collector adapter
   |-- PyEZ / NETCONF / Junos RPC XML
   |-- SSH / Junos CLI JSON
   `-- gNMIc / OpenConfig notification data
   |
source-native RAW evidence
   |
source-specific parser
   |
normalized BGP model
   |
per-device BEFORE / AFTER snapshots
   |
State + Session Health comparison
   |
one Full multi-device report
   |-- Summary TXT
   |-- Detail TXT
   |-- JSON
   `-- Executive PDF
```

## Source-native evidence

### PyEZ / NETCONF

```text
Junos operational RPC -> NETCONF -> XML -> RAW XML
```

### SSH CLI JSON

```text
show bgp summary | display json -> SSH -> RAW JSON
```

### gNMI / OpenConfig

```text
implemented YANG/OpenConfig model
        |
     gNMI server
        |
protobuf notifications
        |
   gNMIc protojson
        |
      RAW JSON
```

YANG defines the modeled data tree. OpenConfig provides vendor-neutral YANG models. gNMI transports modeled values. gNMIc is the client used by this Windows release through WSL.

## Normalization

BGP State requires a minimum stable identity:

```text
device
neighbor
state
```

Session Health may additionally include:

```text
peer AS
uptime
flap count
AFI-SAFI/table identity
prefix counters
source-specific coverage
```

Missing optional data remains unavailable. The application does not manufacture zero values or fake state changes.

## Reusable Basic evidence

`config/audits/bgp/evidence_basic.json` defines the reusable Basic capture. BGP State and Session Health analyze the same collected evidence so their results refer to the same collection point.

## Fallback and same-source policy

When a configured collector falls back, snapshots retain both:

```text
source_requested
source_actual
```

The official BEFORE/AFTER result requires the same `source_actual` for a device on both sides. Cross-source comparison remains diagnostic because different source models can expose different fields.

## Result and coverage separation

Operational result and data coverage are separate:

```text
Operational result: PASS / PASS_WITH_UNHEALTHY_SESSIONS / WARNING / FAIL / ERROR
Coverage:           FULL / PARTIAL / NOT_EVALUATED
```

This matters especially for gNMI/OpenConfig, where implemented leaves differ by platform and software release.

## Family/table behavior

Session Health compares the set of families/tables exposed for each peer.

```text
new_family_after      -> WARNING
missing_family_after  -> WARNING
```

A missing family can represent loss of an AFI-SAFI/table and therefore loss of all routes/prefixes carried by that table. These findings are visible globally, per device, per peer, and in the example reports.

## Future multivendor direction

The multivendor path is **gNMI/OpenConfig only**. PyEZ and the current CLI JSON parser remain Junos-specific.

A future platform must not be enabled only because it has a gNMI endpoint. The intended discovery flow is:

```text
gNMI connection
      |
Capabilities
      |
version + encodings + advertised models
      |
platform capability/path profile
      |
OpenConfig BGP collection
      |
common normalized model
```

Capability profiles will account for path availability, model revision, encoding support, and vendor deviations before a platform can be declared supported.

## Security profiles

Transport security is configurable independently of the read-only application boundary.

- **Compatibility Mode (default):** favors reachability on trusted management networks.
- **Advanced Secure Mode:** optional SSH/NETCONF host-key verification and gNMI TLS/mTLS.

See [Advanced Security](ADVANCED_SECURITY.md).

## Generic engines

Protocol-neutral modules provide reusable live collection, snapshot serialization/loading, indexing, duplicate detection, comparison infrastructure, and manual input persistence. Protocol-specific packages supply collectors, parsers, models, rules, and presentation logic.

This is the pattern planned for later LDP, IS-IS, OSPF, and RSVP State modules.

## Safety boundary

The project does not intentionally perform device configuration or remediation actions such as:

```text
commit
load
lock
unlock
rollback
edit-config
```

The GUI binds to loopback and delegates operational logic to the same CLI/application layers rather than implementing a second protocol engine.
