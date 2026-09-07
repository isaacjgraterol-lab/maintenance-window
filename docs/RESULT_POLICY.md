# Result Policy

## Two independent dimensions

### Operational result

```text
PASS
PASS_WITH_UNHEALTHY_SESSIONS
WARNING
FAIL
ERROR
```

### Data coverage

```text
FULL
PARTIAL
NOT_EVALUATED
```

A `PASS` does not automatically imply `FULL` coverage.

## BGP State

### FAIL

A new negative endpoint-state condition was introduced, such as:

- an Established session is lost;
- an Established session becomes non-Established;
- a newly observed session is unhealthy.

### PASS

No new negative BGP State endpoint condition was introduced.

A peer that was already unhealthy before and remains unhealthy after is retained as context and does not automatically fail the maintenance window.

## Session Health

### FAIL

Examples include:

- an Established peer is down after maintenance;
- meaningful prefix loss crosses the failure policy;
- required comparison data is structurally invalid.

### WARNING

Examples include:

- BGP uptime reset;
- session restart inferred because uptime does not preserve continuity across the actual snapshot interval;
- flap count increased;
- flap counter decreased/reset;
- low post-maintenance uptime;
- meaningful but non-blocking prefix loss;
- a family/table appears after maintenance (`new_family_after`);
- a family/table disappears after maintenance (`missing_family_after`).

`missing_family_after` is intentionally visible because removal of an AFI-SAFI/table can represent loss of every route/prefix carried by that family, even when the peer remains `Established`.

Family/table `WARNING` or `FAIL` findings propagate into the visible peer/session-health result so a peer cannot be presented as `PASS` while one of its evaluated families is degraded.

### PASS_WITH_UNHEALTHY_SESSIONS

One or more peers were already unhealthy before and remain unhealthy after, with no new degradation introduced by the maintenance window.

## Prefix-loss policy

BGP table counters naturally change. v1.0.0 intentionally does not warn on every difference.

For a counter decrease:

- positive value to zero: `FAIL`;
- drop of at least 10 prefixes and at least 20%: `FAIL`;
- drop of at least 20% on a smaller table: `WARNING`;
- drop of at least 10 prefixes and at least 1%: `WARNING`;
- smaller decreases: ignored as normal churn;
- counter increases: ignored by the Session Health result.

The policy is deterministic. Configurable thresholds are roadmap work.

## Session-restart continuity

When both endpoint snapshots show `Established`, a simple state comparison can miss an in-window restart.

The engine compares:

```text
BEFORE BGP uptime
+ actual snapshot interval
~ expected AFTER uptime
```

A continuity gap greater than the configured tolerance produces `session_restart_detected`, unless a direct uptime decrease already produced `uptime_reset`.

## Flap counters

```text
AFTER > BEFORE  -> flap_count_increased
AFTER < BEFORE  -> flap_count_reset
```

A reset/decrease is reported because it can hide earlier flaps or indicate that the underlying counter/session state was reset.

## Coverage policy

A peer is `FULL` when the available source provides the Session Health signals required for the evaluated peer/families on both sides.

A peer can be `PARTIAL` when values such as these are unavailable:

```text
peer_as
uptime
flap_count
prefix_counters
afi_safi_families
afi_safi_comparison
```

Missing source leaves remain unavailable. They do not become fake zeros.

For partial gNMI/OpenConfig family coverage, the engine reports `NOT_EVALUATED` rather than asserting a family counter change that the source did not actually expose.

## Same-source rule

The official BEFORE/AFTER result requires matching `source_actual` for a device.

```text
PyEZ -> PyEZ
SSH  -> SSH
gNMI -> gNMI
```

Cross-source analysis can still be useful diagnostically, but it is not treated as the official MW result because source models can differ in coverage and semantics.
