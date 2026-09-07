from __future__ import annotations

from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpFamilyHealthResult,
    BgpSessionHealthFinding,
    BgpSessionHealthRecord,
)


LOW_UPTIME_WARNING_SECONDS = 300
UPTIME_CONTINUITY_TOLERANCE_SECONDS = 30

# Prefix counters are dynamic on large BGP tables. Public v1 reports only
# meaningful losses instead of warning on every normal route churn event.
PREFIX_DROP_WARNING_ABSOLUTE = 10
PREFIX_DROP_WARNING_PERCENT = 1.0
PREFIX_DROP_FAIL_PERCENT = 20.0

_PREFIX_COUNTER_FIELDS = (
    "active_prefix_count",
    "received_prefix_count",
    "accepted_prefix_count",
    "suppressed_prefix_count",
    "advertised_prefix_count",
)


def _state_change_finding(
    before: BgpSessionHealthRecord,
    after: BgpSessionHealthRecord,
) -> BgpSessionHealthFinding | None:
    """Evaluate peer-state changes caused during the MW."""
    before_established = before.is_established
    after_established = after.is_established

    if before_established and not after_established:
        return BgpSessionHealthFinding(
            severity="FAIL",
            rule="session_down",
            message=(
                "Peer was Established before the maintenance window and "
                f"is {after.peer_state} after."
            ),
            before_value=before.peer_state,
            after_value=after.peer_state,
        )

    if not before_established and not after_established:
        return BgpSessionHealthFinding(
            severity="UNHEALTHY",
            rule="persistent_unhealthy_peer",
            message=(
                "Peer was not Established before the maintenance window "
                f"({before.peer_state}) and remains not Established after "
                f"({after.peer_state})."
            ),
            before_value=before.peer_state,
            after_value=after.peer_state,
        )

    if not before_established and after_established:
        return BgpSessionHealthFinding(
            severity="RECOVERED",
            rule="session_recovered",
            message=(
                "Peer was not Established before the maintenance window "
                f"({before.peer_state}) and is Established after."
            ),
            before_value=before.peer_state,
            after_value=after.peer_state,
        )

    return None


def _health_changed_finding(
    before: BgpSessionHealthRecord,
    after: BgpSessionHealthRecord,
) -> BgpSessionHealthFinding | None:
    if before.health == after.health:
        return None

    return BgpSessionHealthFinding(
        severity="WARNING",
        rule="health_changed",
        message=f"Peer health changed ({before.health} -> {after.health}).",
        before_value=before.health,
        after_value=after.health,
    )


def _uptime_reset_finding(
    before: BgpSessionHealthRecord,
    after: BgpSessionHealthRecord,
) -> BgpSessionHealthFinding | None:
    if (
        before.elapsed_time_seconds is None
        or after.elapsed_time_seconds is None
        or after.elapsed_time_seconds >= before.elapsed_time_seconds
    ):
        return None

    return BgpSessionHealthFinding(
        severity="WARNING",
        rule="uptime_reset",
        message=(
            "BGP uptime decreased/reset "
            f"({before.elapsed_time_seconds}s -> {after.elapsed_time_seconds}s)."
        ),
        before_value=before.elapsed_time_seconds,
        after_value=after.elapsed_time_seconds,
    )


def _uptime_continuity_finding(
    before: BgpSessionHealthRecord,
    after: BgpSessionHealthRecord,
    *,
    snapshot_elapsed_seconds: float | int | None,
) -> BgpSessionHealthFinding | None:
    """Detect a restart that a simple before/after uptime comparison can miss."""
    if (
        not before.is_established
        or not after.is_established
        or before.elapsed_time_seconds is None
        or after.elapsed_time_seconds is None
        or snapshot_elapsed_seconds is None
    ):
        return None

    interval = max(0, int(snapshot_elapsed_seconds))
    if interval <= UPTIME_CONTINUITY_TOLERANCE_SECONDS:
        return None

    # A direct decrease is already covered by uptime_reset.
    if after.elapsed_time_seconds < before.elapsed_time_seconds:
        return None

    expected_after = before.elapsed_time_seconds + interval
    continuity_gap = expected_after - after.elapsed_time_seconds
    if continuity_gap <= UPTIME_CONTINUITY_TOLERANCE_SECONDS:
        return None

    return BgpSessionHealthFinding(
        severity="WARNING",
        rule="session_restart_detected",
        message=(
            "BGP uptime did not preserve continuity across the snapshot interval "
            f"(before={before.elapsed_time_seconds}s, "
            f"snapshot_interval={interval}s, "
            f"expected_after~={expected_after}s, "
            f"actual_after={after.elapsed_time_seconds}s)."
        ),
        before_value=expected_after,
        after_value=after.elapsed_time_seconds,
    )


def _flap_count_finding(
    before: BgpSessionHealthRecord,
    after: BgpSessionHealthRecord,
) -> BgpSessionHealthFinding | None:
    if before.flap_count is None or after.flap_count is None:
        return None

    if after.flap_count > before.flap_count:
        return BgpSessionHealthFinding(
            severity="WARNING",
            rule="flap_count_increased",
            message=(
                "BGP flap count increased "
                f"({before.flap_count} -> {after.flap_count})."
            ),
            before_value=before.flap_count,
            after_value=after.flap_count,
        )

    if after.flap_count < before.flap_count:
        return BgpSessionHealthFinding(
            severity="WARNING",
            rule="flap_count_reset",
            message=(
                "BGP flap count decreased/reset "
                f"({before.flap_count} -> {after.flap_count})."
            ),
            before_value=before.flap_count,
            after_value=after.flap_count,
        )

    return None


def _low_uptime_finding(
    after: BgpSessionHealthRecord,
) -> BgpSessionHealthFinding | None:
    if (
        not after.is_established
        or after.elapsed_time_seconds is None
        or after.elapsed_time_seconds >= LOW_UPTIME_WARNING_SECONDS
    ):
        return None

    return BgpSessionHealthFinding(
        severity="WARNING",
        rule="low_after_uptime",
        message=(
            "BGP uptime is low after the maintenance window "
            f"({after.elapsed_time_seconds}s)."
        ),
        after_value=after.elapsed_time_seconds,
    )


def evaluate_session_health(
    before: BgpSessionHealthRecord | None,
    after: BgpSessionHealthRecord | None,
    *,
    snapshot_elapsed_seconds: float | int | None = None,
) -> list[BgpSessionHealthFinding]:
    """Evaluate one peer using BGP session-health MW rules."""
    findings: list[BgpSessionHealthFinding] = []

    if before is None and after is None:
        return [
            BgpSessionHealthFinding(
                severity="NOT_EVALUATED",
                rule="missing_before_and_after",
                message="Peer is missing from both snapshots.",
            )
        ]

    if before is None:
        if after is not None and not after.is_established:
            return [
                BgpSessionHealthFinding(
                    severity="FAIL",
                    rule="new_peer_not_established",
                    message=(
                        "Peer is present only in the after snapshot and "
                        f"is {after.peer_state}."
                    ),
                    after_value=after.peer_state,
                )
            ]

        return [
            BgpSessionHealthFinding(
                severity="WARNING",
                rule="new_peer",
                message="Peer is present only in the after snapshot.",
                after_value=after.neighbor if after else None,
            )
        ]

    if after is None:
        severity = "FAIL" if before.is_established else "UNHEALTHY"
        rule = (
            "missing_after_established_peer"
            if before.is_established
            else "missing_after_previously_unhealthy_peer"
        )
        return [
            BgpSessionHealthFinding(
                severity=severity,
                rule=rule,
                message=(
                    "Peer was present before but is missing after. "
                    f"Before state was {before.peer_state}."
                ),
                before_value=before.peer_state,
            )
        ]

    state_finding = _state_change_finding(before, after)
    if state_finding is not None:
        findings.append(state_finding)

    health_finding = _health_changed_finding(before, after)
    if health_finding is not None:
        findings.append(health_finding)

    uptime_finding = _uptime_reset_finding(before, after)
    if uptime_finding is not None:
        findings.append(uptime_finding)
    else:
        continuity_finding = _uptime_continuity_finding(
            before,
            after,
            snapshot_elapsed_seconds=snapshot_elapsed_seconds,
        )
        if continuity_finding is not None:
            findings.append(continuity_finding)

    flap_finding = _flap_count_finding(before, after)
    if flap_finding is not None:
        findings.append(flap_finding)

    low_uptime_finding = _low_uptime_finding(after)
    if low_uptime_finding is not None:
        findings.append(low_uptime_finding)

    return findings


def _family_map(
    record: BgpSessionHealthRecord | None,
) -> dict[str, BgpFamilyHealthCounters]:
    if record is None:
        return {}
    return {family.table: family for family in record.families}


def _family_for_result(
    before: BgpFamilyHealthCounters | None,
    after: BgpFamilyHealthCounters | None,
) -> tuple[str, str]:
    family = after or before
    if family is None:
        return "unknown", "unknown"
    return family.table, family.family


def _prefix_drop_severity(
    before_value: int,
    after_value: int,
) -> str | None:
    """Classify meaningful prefix loss while ignoring increases and small churn."""
    if after_value >= before_value:
        return None

    drop = before_value - after_value
    if before_value > 0 and after_value == 0:
        return "FAIL"

    percent = (drop / before_value * 100.0) if before_value > 0 else 0.0
    if (
        drop >= PREFIX_DROP_WARNING_ABSOLUTE
        and percent >= PREFIX_DROP_FAIL_PERCENT
    ):
        return "FAIL"
    if percent >= PREFIX_DROP_FAIL_PERCENT:
        return "WARNING"
    if (
        drop >= PREFIX_DROP_WARNING_ABSOLUTE
        and percent >= PREFIX_DROP_WARNING_PERCENT
    ):
        return "WARNING"
    return None


def _family_counter_delta_findings(
    before: BgpFamilyHealthCounters,
    after: BgpFamilyHealthCounters,
) -> list[BgpSessionHealthFinding]:
    findings: list[BgpSessionHealthFinding] = []

    for field_name in _PREFIX_COUNTER_FIELDS:
        before_value = getattr(before, field_name)
        after_value = getattr(after, field_name)

        if before_value is None or after_value is None:
            continue

        severity = _prefix_drop_severity(before_value, after_value)
        if severity is None:
            continue

        drop = before_value - after_value
        percent = (drop / before_value * 100.0) if before_value > 0 else 0.0
        findings.append(
            BgpSessionHealthFinding(
                severity=severity,
                rule="prefix_delta",
                message=(
                    f"{field_name} decreased for table {after.table} "
                    f"({before_value} -> {after_value}; "
                    f"drop={drop}, {percent:.2f}%)."
                ),
                before_value=before_value,
                after_value=after_value,
                table=after.table,
                family=after.family,
            )
        )

    return findings


def evaluate_family_health(
    *,
    device: str,
    neighbor: str,
    before: BgpFamilyHealthCounters | None,
    after: BgpFamilyHealthCounters | None,
) -> BgpFamilyHealthResult:
    """Evaluate one peer family/table using existing raw counters only."""
    table, family = _family_for_result(before, after)
    findings: list[BgpSessionHealthFinding] = []

    if before is None and after is None:
        findings.append(
            BgpSessionHealthFinding(
                severity="NOT_EVALUATED",
                rule="missing_family_before_and_after",
                message="Family/table is missing from both snapshots.",
                table=table,
                family=family,
            )
        )
    elif before is None:
        findings.append(
            BgpSessionHealthFinding(
                severity="WARNING",
                rule="new_family_after",
                message=f"Family/table is present only after: {table}.",
                table=table,
                family=family,
            )
        )
    elif after is None:
        findings.append(
            BgpSessionHealthFinding(
                severity="WARNING",
                rule="missing_family_after",
                message=f"Family/table is missing after: {table}.",
                table=table,
                family=family,
            )
        )
    else:
        findings.extend(_family_counter_delta_findings(before, after))

    return BgpFamilyHealthResult(
        device=device,
        neighbor=neighbor,
        table=table,
        family=family,
        result=result_from_findings(findings),
        before=before,
        after=after,
        findings=findings,
    )


def evaluate_family_health_for_peer(
    before: BgpSessionHealthRecord | None,
    after: BgpSessionHealthRecord | None,
    *,
    device: str,
    neighbor: str,
) -> list[BgpFamilyHealthResult]:
    before_map = _family_map(before)
    after_map = _family_map(after)
    tables = sorted(set(before_map) | set(after_map))

    source = str(
        (after.source if after is not None else None)
        or (before.source if before is not None else None)
        or ""
    ).strip().lower()
    partial_gnmi_coverage = (
        source in {"gnmi", "gnmic", "openconfig"}
        and bool(tables)
        and (not before_map or not after_map)
    )

    if partial_gnmi_coverage:
        results: list[BgpFamilyHealthResult] = []
        for table in tables:
            before_family = before_map.get(table)
            after_family = after_map.get(table)
            selected = after_family or before_family
            if selected is None:
                continue
            finding = BgpSessionHealthFinding(
                severity="NOT_EVALUATED",
                rule="partial_health_family_counters_unavailable",
                message=(
                    "AFI-SAFI counters were not available in both gNMI "
                    f"snapshots for table {table}; no counter delta was asserted."
                ),
                table=selected.table,
                family=selected.family,
            )
            results.append(
                BgpFamilyHealthResult(
                    device=device,
                    neighbor=neighbor,
                    table=selected.table,
                    family=selected.family,
                    result="NOT_EVALUATED",
                    before=before_family,
                    after=after_family,
                    findings=[finding],
                )
            )
        return results

    return [
        evaluate_family_health(
            device=device,
            neighbor=neighbor,
            before=before_map.get(table),
            after=after_map.get(table),
        )
        for table in tables
    ]


def result_from_findings(findings: list[BgpSessionHealthFinding]) -> str:
    """Return the peer or family result from its findings."""
    severities = {finding.severity for finding in findings}

    if "FAIL" in severities:
        return "FAIL"

    if "WARNING" in severities:
        return "WARNING"

    if "UNHEALTHY" in severities:
        return "UNHEALTHY"

    if "NOT_EVALUATED" in severities:
        return "NOT_EVALUATED"

    return "PASS"

def result_from_peer_and_family_results(
    findings: list[BgpSessionHealthFinding],
    family_results: list[BgpFamilyHealthResult],
) -> str:
    """Aggregate peer findings and family findings into the visible peer result."""
    peer_result = result_from_findings(findings)
    family_results_set = {item.result for item in family_results}

    if peer_result == "FAIL" or "FAIL" in family_results_set:
        return "FAIL"

    # Preserve the operational distinction for a peer that was already unhealthy
    # before the MW; family warnings must not hide that state.
    if peer_result == "UNHEALTHY":
        return "UNHEALTHY"

    if peer_result == "WARNING" or "WARNING" in family_results_set:
        return "WARNING"

    if peer_result == "NOT_EVALUATED" or "NOT_EVALUATED" in family_results_set:
        return "NOT_EVALUATED"

    return peer_result
