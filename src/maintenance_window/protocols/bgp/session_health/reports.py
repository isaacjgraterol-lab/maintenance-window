from __future__ import annotations

from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthResult,
    BgpSessionHealthComparison,
    BgpSessionHealthRecord,
    BgpSessionHealthResult,
)


def session_health_to_dict(
    comparison: BgpSessionHealthComparison,
) -> dict[str, object]:
    """Convert a session-health comparison into JSON-ready data."""
    return {
        "module": "session-health",
        "device": comparison.device,
        "result": comparison.result,
        "mw_id": comparison.mw_id,
        "before_stage": comparison.before_stage,
        "after_stage": comparison.after_stage,
        "before_source_requested": comparison.before_source_requested,
        "after_source_requested": comparison.after_source_requested,
        "before_source_actual": comparison.before_source_actual,
        "after_source_actual": comparison.after_source_actual,
        "source_fallback_before": (
            comparison.before_source_requested != comparison.before_source_actual
        ),
        "source_fallback_after": (
            comparison.after_source_requested != comparison.after_source_actual
        ),
        "coverage": comparison.coverage,
        "before_raw_file": (
            str(comparison.before_raw_file)
            if comparison.before_raw_file is not None
            else None
        ),
        "after_raw_file": (
            str(comparison.after_raw_file)
            if comparison.after_raw_file is not None
            else None
        ),
        "peers_total": comparison.peers_total,
        "peers_passed": comparison.peers_passed,
        "peers_failed": comparison.peers_failed,
        "peers_warning": comparison.peers_warning,
        "peers_unhealthy": comparison.peers_unhealthy,
        "peers_not_evaluated": comparison.peers_not_evaluated,
        "peers_partial": comparison.peers_partial,
        "families_total": comparison.families_total,
        "families_warning": comparison.families_warning,
        "families_failed": comparison.families_failed,
        "families_not_evaluated": comparison.families_not_evaluated,
        "fail_reasons": comparison.fail_reasons,
        "peers": [item.to_dict() for item in comparison.peer_results],
    }


def _important_results(
    peer_results: list[BgpSessionHealthResult],
) -> list[BgpSessionHealthResult]:
    return [
        item
        for item in peer_results
        if item.result in {"FAIL", "WARNING", "UNHEALTHY", "NOT_EVALUATED"}
        or item.coverage != "FULL"
        or any(
            family.result in {"FAIL", "WARNING", "NOT_EVALUATED"}
            for family in item.family_results
        )
    ]


def _important_family_results(
    family_results: list[BgpFamilyHealthResult],
) -> list[BgpFamilyHealthResult]:
    return [
        item
        for item in family_results
        if item.result in {"FAIL", "WARNING", "NOT_EVALUATED"}
    ]


def format_session_health_summary(
    comparison: BgpSessionHealthComparison,
) -> str:
    """Build a concise per-device session-health summary."""
    lines = [
        f"Device: {comparison.device}",
        f"Result: {comparison.result}",
        f"Coverage: {comparison.coverage}",
        (
            "Sources: "
            f"{comparison.before_source_requested}->{comparison.before_source_actual} "
            f"/ {comparison.after_source_requested}->{comparison.after_source_actual}"
        ),
        f"Peers total: {comparison.peers_total}",
        f"Peers passed: {comparison.peers_passed}",
        f"Peers failed: {comparison.peers_failed}",
        f"Peers warning: {comparison.peers_warning}",
        f"Peers unhealthy: {comparison.peers_unhealthy}",
        f"Peers not evaluated: {comparison.peers_not_evaluated}",
        f"Peers partial: {comparison.peers_partial}",
        f"Families total: {comparison.families_total}",
        f"Families warning: {comparison.families_warning}",
        f"Families failed: {comparison.families_failed}",
        f"Families not evaluated: {comparison.families_not_evaluated}",
    ]

    important = _important_results(comparison.peer_results)
    if important:
        lines.append("Important peers:")
        for item in important[:10]:
            lines.append(f"  {item.neighbor}   {item.result}")
            for finding in item.findings[:3]:
                lines.append(f"    - {finding.rule}: {finding.message}")
            for family in _important_family_results(item.family_results)[:5]:
                lines.append(
                    f"    - family {family.table} ({family.family}) {family.result}"
                )
                for finding in family.findings[:2]:
                    lines.append(f"      - {finding.rule}: {finding.message}")

    return "\n".join(lines)


def _record_summary(prefix: str, record: BgpSessionHealthRecord) -> str:
    return (
        f"{prefix}: "
        f"state={record.peer_state} "
        f"health={record.health} "
        f"uptime={record.elapsed_time_seconds} "
        f"flaps={record.flap_count} "
        f"received={record.received_prefix_count} "
        f"accepted={record.accepted_prefix_count} "
        f"active={record.active_prefix_count} "
        f"suppressed={record.suppressed_prefix_count} "
        f"advertised={record.advertised_prefix_count}"
    )


def _family_summary(prefix: str, family) -> str:
    return (
        f"{prefix}: "
        f"table={family.table} "
        f"family={family.family} "
        f"rib_state={family.rib_state} "
        f"send_state={family.send_state} "
        f"received={family.received_prefix_count} "
        f"accepted={family.accepted_prefix_count} "
        f"active={family.active_prefix_count} "
        f"suppressed={family.suppressed_prefix_count} "
        f"advertised={family.advertised_prefix_count}"
    )


def format_session_health_detail(
    comparison: BgpSessionHealthComparison,
) -> str:
    """Build a detailed per-device session-health report."""
    lines = [
        "BGP Session Health Detail",
        "",
        f"MW ID: {comparison.mw_id}",
        f"Device: {comparison.device}",
        f"Stages: {comparison.before_stage} -> {comparison.after_stage}",
        f"Result: {comparison.result}",
        f"Before raw: {comparison.before_raw_file}",
        f"After raw: {comparison.after_raw_file}",
        "",
        "Device Summary",
        "==============",
        format_session_health_summary(comparison),
        "",
        "Peer Summary",
        "============",
    ]

    for item in comparison.peer_results:
        before = item.before
        after = item.after
        lines.append(
            f"  Peer: {item.neighbor}   Result: {item.result} "
            f"Coverage: {item.coverage}"
        )
        if item.not_evaluated_checks:
            lines.append(
                "    Not evaluated checks: "
                + ", ".join(item.not_evaluated_checks)
            )
        if before is not None:
            lines.append("    " + _record_summary("before", before))
        if after is not None:
            lines.append("    " + _record_summary("after", after))
        for finding in item.findings:
            lines.append(f"    - {finding.severity} {finding.rule}: {finding.message}")

        if item.family_results:
            lines.append("    Family/Table Details:")
            for family_result in item.family_results:
                lines.append(
                    "      "
                    f"Table: {family_result.table} "
                    f"Family: {family_result.family} "
                    f"Result: {family_result.result}"
                )
                if family_result.before is not None:
                    lines.append(
                        "        " + _family_summary("before", family_result.before)
                    )
                if family_result.after is not None:
                    lines.append(
                        "        " + _family_summary("after", family_result.after)
                    )
                for finding in family_result.findings:
                    lines.append(
                        "        "
                        f"- {finding.severity} {finding.rule}: {finding.message}"
                    )

    return "\n".join(lines)
