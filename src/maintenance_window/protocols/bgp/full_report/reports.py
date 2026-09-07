from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from maintenance_window.core.path_safety import safe_path_part


class SavedFullReportPaths(dict):
    """Report path container compatible with dict and attribute access."""

    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _overall_result(results: list[object]) -> str:
    texts = {str(item) for item in results}
    if "ERROR" in texts:
        return "ERROR"
    if "FAIL" in texts:
        return "FAIL"
    if "WARNING" in texts:
        return "WARNING"
    if "PASS_WITH_UNHEALTHY_SESSIONS" in texts:
        return "PASS_WITH_UNHEALTHY_SESSIONS"
    return "PASS"


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: object, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value)
    return text if text else default


def _value(value: object) -> str:
    return "N/A" if value is None else str(value)


def _pair(before: object, after: object) -> str:
    return f"{_value(before)} -> {_value(after)}"


def _findings_from(item: dict[str, object]) -> list[dict[str, object]]:
    findings = item.get("findings", [])
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, dict)]


def _families_from(peer: dict[str, object]) -> list[dict[str, object]]:
    families = peer.get("families", [])
    if not isinstance(families, list):
        return []
    return [family for family in families if isinstance(family, dict)]


def _record_from(peer: dict[str, object], key: str) -> dict[str, object]:
    record = peer.get(key, {})
    return record if isinstance(record, dict) else {}


def _counter(record: dict[str, object], name: str) -> object:
    return record.get(name)


def _changed(before: object, after: object) -> bool:
    return before != after


def _session_health_metric(
    payload: dict[str, object],
    health: dict[str, object],
    summary_key: str,
    report_key: str,
) -> int:
    value = _to_int(health.get(summary_key), default=-1)
    if value >= 0:
        return value

    reports = payload.get("reports", {})
    if not isinstance(reports, dict):
        return 0
    health_reports = reports.get("session_health", [])
    if not isinstance(health_reports, list):
        return 0
    return sum(
        _to_int(report.get(report_key))
        for report in health_reports
        if isinstance(report, dict)
    )



def _stage_source(
    report: dict[str, object],
    stage: str,
    field: str,
) -> str:
    stage_payload = report.get(stage, {})
    if not isinstance(stage_payload, dict):
        return "unknown"
    return str(stage_payload.get(field) or "unknown")


def build_source_coverage(
    state_reports: list[dict[str, object]],
) -> dict[str, object]:
    """Summarize requested and actual collection sources per device/stage."""
    before_actual: Counter[str] = Counter()
    after_actual: Counter[str] = Counter()
    fallback_devices: list[dict[str, str]] = []
    devices: list[dict[str, object]] = []

    for report in state_reports:
        if report.get("result") == "ERROR":
            continue
        device = str(report.get("device") or "unknown")
        before_requested = _stage_source(report, "before", "source_requested")
        before_source = _stage_source(report, "before", "source_actual")
        after_requested = _stage_source(report, "after", "source_requested")
        after_source = _stage_source(report, "after", "source_actual")
        before_actual[before_source] += 1
        after_actual[after_source] += 1

        row = {
            "device": device,
            "before_requested": before_requested,
            "before_actual": before_source,
            "after_requested": after_requested,
            "after_actual": after_source,
            "before_fallback": before_requested != before_source,
            "after_fallback": after_requested != after_source,
        }
        devices.append(row)

        if row["before_fallback"] or row["after_fallback"]:
            fallback_devices.append(
                {
                    "device": device,
                    "before": f"{before_requested}->{before_source}",
                    "after": f"{after_requested}->{after_source}",
                }
            )

    return {
        "before_actual": dict(sorted(before_actual.items())),
        "after_actual": dict(sorted(after_actual.items())),
        "fallback_device_count": len(fallback_devices),
        "fallback_devices": fallback_devices,
        "devices": devices,
    }

def build_state_summary(
    reports: list[dict[str, object]],
) -> dict[str, object]:
    """Build the global BGP state summary from device reports."""
    error_reports = [
        report for report in reports if report.get("result") == "ERROR"
    ]
    failed_reports = [
        report for report in reports if report.get("result") == "FAIL"
    ]
    passed_reports = [
        report for report in reports if report.get("result") == "PASS"
    ]

    return {
        "overall_result": _overall_result(
            [report.get("result", "PASS") for report in reports]
        ),
        "total_devices": len(reports),
        "passed_devices": len(passed_reports),
        "failed_devices": len(failed_reports),
        "error_devices": len(error_reports),
        "total_lost_sessions": sum(
            _to_int(report.get("lost_sessions_count")) for report in reports
        ),
        "total_new_sessions": sum(
            _to_int(report.get("new_sessions_count")) for report in reports
        ),
        "total_state_changes": sum(
            _to_int(report.get("state_changes_count")) for report in reports
        ),
        "total_unhealthy_fsm_transitions": sum(
            _to_int(report.get("unhealthy_fsm_transitions_count"))
            for report in reports
        ),
        "total_new_unhealthy": sum(
            _to_int(report.get("new_unhealthy_count")) for report in reports
        ),
        "total_resolved_unhealthy": sum(
            _to_int(report.get("resolved_unhealthy_count"))
            for report in reports
        ),
        "total_persistent_unhealthy": sum(
            _to_int(report.get("persistent_unhealthy_count"))
            for report in reports
        ),
        "devices_with_errors": [
            str(report.get("device")) for report in error_reports
        ],
    }


def build_session_health_summary(
    reports: list[dict[str, object]],
) -> dict[str, object]:
    """Build the global BGP session-health summary from device reports."""
    error_reports = [
        report for report in reports if report.get("result") == "ERROR"
    ]
    failed_reports = [
        report for report in reports if report.get("result") == "FAIL"
    ]
    warning_reports = [
        report for report in reports if report.get("result") == "WARNING"
    ]
    unhealthy_reports = [
        report
        for report in reports
        if report.get("result") == "PASS_WITH_UNHEALTHY_SESSIONS"
    ]
    passed_reports = [
        report
        for report in reports
        if report.get("result") in {"PASS", "PASS_WITH_UNHEALTHY_SESSIONS"}
    ]

    return {
        "overall_result": _overall_result(
            [report.get("result", "PASS") for report in reports]
        ),
        "total_devices": len(reports),
        "passed_devices": len(passed_reports),
        "failed_devices": len(failed_reports),
        "warning_devices": len(warning_reports),
        "unhealthy_devices": len(unhealthy_reports),
        "error_devices": len(error_reports),
        "total_peers": sum(
            _to_int(report.get("peers_total")) for report in reports
        ),
        "total_failed_peers": sum(
            _to_int(report.get("peers_failed")) for report in reports
        ),
        "total_warning_peers": sum(
            _to_int(report.get("peers_warning")) for report in reports
        ),
        "total_unhealthy_peers": sum(
            _to_int(report.get("peers_unhealthy")) for report in reports
        ),
        "total_not_evaluated_peers": sum(
            _to_int(report.get("peers_not_evaluated"))
            for report in reports
        ),
        "total_partial_peers": sum(
            _to_int(report.get("peers_partial"))
            for report in reports
        ),
        "total_families": sum(
            _to_int(report.get("families_total")) for report in reports
        ),
        "total_warning_families": sum(
            _to_int(report.get("families_warning")) for report in reports
        ),
        "total_failed_families": sum(
            _to_int(report.get("families_failed")) for report in reports
        ),
        "total_not_evaluated_families": sum(
            _to_int(report.get("families_not_evaluated"))
            for report in reports
        ),
        "coverage": (
            "PARTIAL"
            if any(str(report.get("coverage")) != "FULL" for report in reports)
            else "FULL"
        ),
        "devices_with_partial_coverage": [
            str(report.get("device"))
            for report in reports
            if str(report.get("coverage")) != "FULL"
        ],
        "devices_with_errors": [
            str(report.get("device")) for report in error_reports
        ],
        "devices_with_failures": [
            str(report.get("device")) for report in failed_reports
        ],
        "devices_with_warnings": [
            str(report.get("device")) for report in warning_reports
        ],
        "devices_with_unhealthy": [
            str(report.get("device")) for report in unhealthy_reports
        ],
    }


def _finding_counts_for_health_report(
    report: dict[str, object],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    peers = report.get("peers", [])
    if not isinstance(peers, list):
        return counts

    for peer in peers:
        if not isinstance(peer, dict):
            continue
        for finding in _findings_from(peer):
            rule = str(finding.get("rule") or "unknown")
            counts[rule] = counts.get(rule, 0) + 1
        for family in _families_from(peer):
            for finding in _findings_from(family):
                rule = str(finding.get("rule") or "unknown")
                counts[rule] = counts.get(rule, 0) + 1

    return dict(sorted(counts.items()))


def build_finding_counts(
    reports: list[dict[str, object]],
) -> dict[str, int]:
    """Aggregate peer/family Session Health findings across all devices."""
    totals: Counter[str] = Counter()
    for report in reports:
        totals.update(_finding_counts_for_health_report(report))
    return dict(sorted(totals.items()))


def build_device_summaries(
    *,
    state_reports: list[dict[str, object]],
    session_health_reports: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build a compact, complete per-device view for text/JSON/GUI reports."""
    state_by_device = {
        str(report.get("device")): report
        for report in state_reports
        if report.get("device") is not None
    }
    health_by_device = {
        str(report.get("device")): report
        for report in session_health_reports
        if report.get("device") is not None
    }

    devices: list[str] = []
    for report in [*state_reports, *session_health_reports]:
        device = str(report.get("device") or "")
        if device and device not in devices:
            devices.append(device)

    summaries: list[dict[str, object]] = []
    for device in devices:
        state = state_by_device.get(device, {})
        health = health_by_device.get(device, {})
        before = state.get("before", {})
        after = state.get("after", {})
        if not isinstance(before, dict):
            before = {}
        if not isinstance(after, dict):
            after = {}

        module_results = [
            str(report.get("result"))
            for report in (state, health)
            if report and report.get("result") is not None
        ]

        summaries.append(
            {
                "device": device,
                "overall_result": (
                    _overall_result(module_results)
                    if module_results
                    else "UNKNOWN"
                ),
                "state": {
                    "result": state.get("result", "UNKNOWN"),
                    "total_sessions_before": _to_int(
                        before.get("total_sessions")
                    ),
                    "total_sessions_after": _to_int(
                        after.get("total_sessions")
                    ),
                    "lost_sessions": _to_int(
                        state.get("lost_sessions_count")
                    ),
                    "new_sessions": _to_int(
                        state.get("new_sessions_count")
                    ),
                    "state_changes": _to_int(
                        state.get("state_changes_count")
                    ),
                    "new_unhealthy": _to_int(
                        state.get("new_unhealthy_count")
                    ),
                    "resolved_unhealthy": _to_int(
                        state.get("resolved_unhealthy_count")
                    ),
                    "persistent_unhealthy": _to_int(
                        state.get("persistent_unhealthy_count")
                    ),
                },
                "session_health": {
                    "result": health.get("result", "UNKNOWN"),
                    "total_peers": _to_int(health.get("peers_total")),
                    "passed_peers": _to_int(health.get("peers_passed")),
                    "failed_peers": _to_int(health.get("peers_failed")),
                    "warning_peers": _to_int(health.get("peers_warning")),
                    "unhealthy_peers": _to_int(
                        health.get("peers_unhealthy")
                    ),
                    "not_evaluated_peers": _to_int(
                        health.get("peers_not_evaluated")
                    ),
                    "families_total": _to_int(
                        health.get("families_total")
                    ),
                    "warning_families": _to_int(
                        health.get("families_warning")
                    ),
                    "failed_families": _to_int(
                        health.get("families_failed")
                    ),
                },
                "finding_counts": _finding_counts_for_health_report(health),
            }
        )

    return summaries


def build_full_summary(
    *,
    state_summary: dict[str, object],
    session_health_summary: dict[str, object],
) -> dict[str, object]:
    """Build the global result for the combined BGP report."""
    overall_result = _overall_result(
        [
            state_summary.get("overall_result", "PASS"),
            session_health_summary.get("overall_result", "PASS"),
        ]
    )

    return {
        "overall_result": overall_result,
        "modules": {
            "state": state_summary.get("overall_result", "UNKNOWN"),
            "session-health": session_health_summary.get(
                "overall_result",
                "UNKNOWN",
            ),
        },
        "state": state_summary,
        "session_health": session_health_summary,
    }


def build_full_payload(
    *,
    mw_id: str,
    before_stage: str,
    after_stage: str,
    devices: list[str],
    full_summary: dict[str, object],
    state_reports: list[dict[str, object]],
    session_health_reports: list[dict[str, object]],
    report_directory: object,
) -> dict[str, object]:
    """Build the JSON-serializable full BGP report payload."""
    modules = full_summary.get("modules", {})
    if not isinstance(modules, dict):
        modules = {}

    state_result = modules.get("state", "UNKNOWN")
    health_result = modules.get("session-health", "UNKNOWN")
    source_coverage = build_source_coverage(state_reports)
    finding_counts = build_finding_counts(session_health_reports)

    return {
        "protocol": "bgp",
        "module": "full",
        "mode": "compare-snapshots",
        "mw_id": mw_id,
        "before_stage": before_stage,
        "after_stage": after_stage,
        "devices": devices,
        "report_directory": str(report_directory),
        "result": full_summary.get("overall_result", "UNKNOWN"),
        "state_result": state_result,
        "session_health_result": health_result,
        "finding_counts": finding_counts,
        "module_summary": {
            "state": {
                "result": state_result,
                "summary": full_summary.get("state", {}),
            },
            "session-health": {
                "result": health_result,
                "summary": full_summary.get("session_health", {}),
            },
            "session_health": {
                "result": health_result,
                "summary": full_summary.get("session_health", {}),
            },
        },
        "global_summary": {
            **full_summary,
            "source_coverage": source_coverage,
            "finding_counts": finding_counts,
        },
        "source_coverage": source_coverage,
        "device_summary": build_device_summaries(
            state_reports=state_reports,
            session_health_reports=session_health_reports,
        ),
        "reports": {
            "state": state_reports,
            "session_health": session_health_reports,
        },
    }


def build_full_report_payload(
    *,
    request: object,
    state_reports: list[dict[str, object]],
    session_health_reports: list[dict[str, object]],
    report_directory: object = "",
) -> dict[str, object]:
    """Build a full report payload from a normalized request."""
    state_summary = build_state_summary(state_reports)
    session_health_summary = build_session_health_summary(
        session_health_reports
    )
    full_summary = build_full_summary(
        state_summary=state_summary,
        session_health_summary=session_health_summary,
    )

    return build_full_payload(
        mw_id=str(request.mw_id),
        before_stage=str(request.before_stage),
        after_stage=str(request.after_stage),
        devices=list(request.device_names),
        full_summary=full_summary,
        state_reports=state_reports,
        session_health_reports=session_health_reports,
        report_directory=report_directory,
    )


def _important_health_peers(
    report: dict[str, object],
) -> list[dict[str, object]]:
    peers = report.get("peers", [])
    if not isinstance(peers, list):
        return []

    important: list[dict[str, object]] = []
    for peer in peers:
        if not isinstance(peer, dict):
            continue
        if peer.get("result") in {"FAIL", "WARNING", "UNHEALTHY", "NOT_EVALUATED"}:
            important.append(peer)
            continue
        if str(peer.get("coverage") or "FULL") != "FULL":
            important.append(peer)
            continue
        if _findings_from(peer):
            important.append(peer)
            continue
        families = _families_from(peer)
        if any(family.get("result") in {"FAIL", "WARNING", "NOT_EVALUATED"} for family in families):
            important.append(peer)
            continue
    return important


_MAJOR_SEPARATOR = "=" * 72
_MINOR_SEPARATOR = "-" * 72


def _append_report_section(
    lines: list[str],
    title: str,
    *,
    major: bool = False,
) -> None:
    separator = _MAJOR_SEPARATOR if major else _MINOR_SEPARATOR
    if lines and lines[-1] != "":
        lines.append("")
    lines.extend([separator, title, separator])


def _append_result_explanation(
    lines: list[str],
    payload: dict[str, object],
) -> None:
    reports = payload.get("reports", {})
    if not isinstance(reports, dict):
        return

    state_reports = reports.get("state", [])
    health_reports = reports.get("session_health", [])

    blocking: list[str] = []
    warnings: list[str] = []

    if isinstance(state_reports, list):
        for report in state_reports:
            if not isinstance(report, dict):
                continue
            device = _text(report.get("device"))
            result = _text(report.get("result"))
            if result in {"ERROR", "FAIL"}:
                reason = ", ".join(str(item) for item in report.get("fail_reasons", []) if item) or "state comparison failed"
                blocking.append(f"BGP-STATE {device}: {result} ({reason})")

    if isinstance(health_reports, list):
        for report in health_reports:
            if not isinstance(report, dict):
                continue
            device = _text(report.get("device"))
            result = _text(report.get("result"))
            if result in {"ERROR", "FAIL"}:
                reason = ", ".join(str(item) for item in report.get("fail_reasons", []) if item) or "session-health comparison failed"
                blocking.append(f"BGP-SESSION-HEALTH {device}: {result} ({reason})")
            for peer in _important_health_peers(report):
                neighbor = _text(peer.get("neighbor"))
                peer_result = _text(peer.get("result"))
                peer_findings = _findings_from(peer)
                family_findings = []
                for family in _families_from(peer):
                    family_findings.extend(_findings_from(family))
                all_findings = peer_findings + family_findings
                if not all_findings and peer_result not in {"PASS", "OK"}:
                    warnings.append(f"{device} peer {neighbor}: {peer_result}")
                    continue
                for finding in all_findings:
                    table = finding.get("table")
                    table_text = f" / {table}" if table else ""
                    warnings.append(
                        f"{device} peer {neighbor}{table_text}: "
                        f"{finding.get('rule')} - {finding.get('message')}"
                    )

    _append_report_section(lines, "RESULT EXPLANATION")
    lines.append("Result explanation:")
    if blocking:
        lines.append("  Blocking reasons:")
        for item in blocking:
            lines.append(f"    - {item}")
    else:
        lines.append("  Blocking reasons: none")

    if warnings:
        lines.append("  Non-blocking warnings:")
        for item in warnings:
            lines.append(f"    - {item}")
    else:
        lines.append("  Non-blocking warnings: none")


def _format_source_counts(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "none"
    parts = [
        f"{key}: {_to_int(value[key])}"
        for key in sorted(value, key=str)
    ]
    return ", ".join(parts)


_FINDING_SUMMARY_LABELS = (
    ("session_restart_detected", "Session restarts"),
    ("uptime_reset", "Uptime resets"),
    ("flap_count_increased", "Flap count increases"),
    ("flap_count_reset", "Flap count resets"),
    ("new_family_after", "New families"),
    ("missing_family_after", "Missing families"),
    ("prefix_delta", "Prefix deltas"),
    ("persistent_unhealthy_peer", "Persistent unhealthy peers"),
    ("low_after_uptime", "Low-uptime peers"),
)


def _append_device_summaries(
    lines: list[str],
    payload: dict[str, object],
) -> None:
    summaries = payload.get("device_summary", [])
    if not isinstance(summaries, list):
        return

    _append_report_section(lines, "DEVICE SUMMARY:")
    for item in summaries:
        if not isinstance(item, dict):
            continue
        state = item.get("state", {})
        health = item.get("session_health", {})
        findings = item.get("finding_counts", {})
        if not isinstance(state, dict):
            state = {}
        if not isinstance(health, dict):
            health = {}
        if not isinstance(findings, dict):
            findings = {}

        lines.extend(
            [
                "",
                f"Device: {item.get('device')}",
                f"  Overall result: {item.get('overall_result')}",
                "",
                "  BGP-STATE:",
                f"    Result: {state.get('result')}",
                (
                    "    Total sessions: "
                    f"{state.get('total_sessions_before', 0)} -> "
                    f"{state.get('total_sessions_after', 0)}"
                ),
                f"    Lost sessions: {state.get('lost_sessions', 0)}",
                f"    New sessions: {state.get('new_sessions', 0)}",
                f"    State changes: {state.get('state_changes', 0)}",
                f"    New unhealthy: {state.get('new_unhealthy', 0)}",
                (
                    "    Persistent unhealthy: "
                    f"{state.get('persistent_unhealthy', 0)}"
                ),
                "",
                "  BGP-SESSION-HEALTH:",
                f"    Result: {health.get('result')}",
                f"    Total peers: {health.get('total_peers', 0)}",
                f"    Passed peers: {health.get('passed_peers', 0)}",
                f"    Failed peers: {health.get('failed_peers', 0)}",
                f"    Warning peers: {health.get('warning_peers', 0)}",
                f"    Unhealthy peers: {health.get('unhealthy_peers', 0)}",
                (
                    "    Not evaluated peers: "
                    f"{health.get('not_evaluated_peers', 0)}"
                ),
                f"    Families total: {health.get('families_total', 0)}",
                (
                    "    Warning families: "
                    f"{health.get('warning_families', 0)}"
                ),
                (
                    "    Failed families: "
                    f"{health.get('failed_families', 0)}"
                ),
                "",
                "  Findings:",
            ]
        )
        for rule, label in _FINDING_SUMMARY_LABELS:
            lines.append(f"    {label}: {_to_int(findings.get(rule))}")


def format_full_summary(payload: dict[str, object]) -> str:
    """Build a concise text summary for the full report."""
    summary = payload["global_summary"]
    assert isinstance(summary, dict)

    modules = summary.get("modules", {})
    assert isinstance(modules, dict)

    state = summary.get("state", {})
    assert isinstance(state, dict)

    health = summary.get("session_health", {})
    assert isinstance(health, dict)

    lines = [
        _MAJOR_SEPARATOR,
        "BGP FULL MAINTENANCE REPORT",
        _MAJOR_SEPARATOR,
        "",
        f"MW ID: {payload['mw_id']}",
        f"Stages: {payload['before_stage']} -> {payload['after_stage']}",
        f"Overall result: {summary.get('overall_result')}",
    ]

    _append_report_section(lines, "MODULE RESULTS")
    lines.extend(
        [
            f"  BGP-STATE: {modules.get('state')}",
            f"  BGP-SESSION-HEALTH: {modules.get('session-health')}",
        ]
    )

    _append_report_section(lines, "GLOBAL SUMMARY")
    lines.extend(
        [
            "BGP-STATE summary:",
            f"  Total devices: {state.get('total_devices', 0)}",
            f"  Lost sessions: {state.get('total_lost_sessions', 0)}",
            f"  New sessions: {state.get('total_new_sessions', 0)}",
            f"  State changes: {state.get('total_state_changes', 0)}",
            (
                "  Unhealthy FSM transitions: "
                f"{state.get('total_unhealthy_fsm_transitions', 0)}"
            ),
            f"  New unhealthy: {state.get('total_new_unhealthy', 0)}",
            f"  Persistent unhealthy: {state.get('total_persistent_unhealthy', 0)}",
            "",
            "BGP-SESSION-HEALTH summary:",
            f"  Total peers: {health.get('total_peers', 0)}",
            f"  Failed peers: {health.get('total_failed_peers', 0)}",
            f"  Warning peers: {health.get('total_warning_peers', 0)}",
            f"  Unhealthy peers: {health.get('total_unhealthy_peers', 0)}",
            f"  Not evaluated peers: {health.get('total_not_evaluated_peers', 0)}",
            f"  Partial peers: {health.get('total_partial_peers', 0)}",
            f"  Data coverage: {health.get('coverage', 'UNKNOWN')}",
            f"  Families total: {_session_health_metric(payload, health, 'total_families', 'families_total')}",
            f"  Warning families: {_session_health_metric(payload, health, 'total_warning_families', 'families_warning')}",
            f"  Failed families: {_session_health_metric(payload, health, 'total_failed_families', 'families_failed')}",
            (
                "  Not evaluated families: "
                f"{health.get('total_not_evaluated_families', 0)}"
            ),
            "",
            "Source coverage:",
            (
                "  Before actual: "
                f"{_format_source_counts(summary.get('source_coverage', {}).get('before_actual', {}))}"
            ),
            (
                "  After actual: "
                f"{_format_source_counts(summary.get('source_coverage', {}).get('after_actual', {}))}"
            ),
            (
                "  Fallback devices: "
                f"{summary.get('source_coverage', {}).get('fallback_device_count', 0)}"
            ),
        ]
    )

    finding_counts = payload.get("finding_counts", {})
    if not isinstance(finding_counts, dict):
        finding_counts = {}
    _append_report_section(lines, "KEY FINDING INVENTORY")
    for rule, label in _FINDING_SUMMARY_LABELS:
        lines.append(f"  {label}: {_to_int(finding_counts.get(rule))}")

    _append_device_summaries(lines, payload)
    _append_report_section(lines, "REPORT LOCATION")
    lines.append(f"Report directory: {payload['report_directory']}")

    _append_result_explanation(lines, payload)

    return "\n".join(lines)


def _append_state_detail(lines: list[str], report: dict[str, object]) -> None:
    lines.extend(
        [
            f"  Device: {report.get('device')}",
            f"    Result: {report.get('result')}",
            f"    Lost sessions: {report.get('lost_sessions_count', 0)}",
            f"    New sessions: {report.get('new_sessions_count', 0)}",
            f"    State changes: {report.get('state_changes_count', 0)}",
            (
                "    Unhealthy FSM transitions: "
                f"{report.get('unhealthy_fsm_transitions_count', 0)}"
            ),
            f"    New unhealthy: {report.get('new_unhealthy_count', 0)}",
            f"    Persistent unhealthy: {report.get('persistent_unhealthy_count', 0)}",
        ]
    )


def _counter_line(
    label: str,
    before: dict[str, object],
    after: dict[str, object],
    key: str,
) -> str:
    marker = " *" if _changed(before.get(key), after.get(key)) else ""
    return f"{label}: {_pair(before.get(key), after.get(key))}{marker}"


def _append_peer_detail(lines: list[str], peer: dict[str, object]) -> None:
    before = _record_from(peer, "before")
    after = _record_from(peer, "after")
    neighbor = _text(peer.get("neighbor"))

    lines.append(f"    Peer: {neighbor}")
    lines.append(f"      Result: {peer.get('result')}")
    lines.append(f"      Coverage: {peer.get('coverage', 'UNKNOWN')}")
    not_evaluated_checks = peer.get("not_evaluated_checks", [])
    if isinstance(not_evaluated_checks, list) and not_evaluated_checks:
        lines.append(
            "      Not evaluated checks: "
            + ", ".join(str(item) for item in not_evaluated_checks)
        )
    lines.append(f"      State: {_pair(before.get('peer_state') or before.get('state'), after.get('peer_state') or after.get('state'))}")
    lines.append(f"      Health: {_pair(before.get('health'), after.get('health'))}")
    lines.append(f"      Uptime: {_pair(before.get('uptime') or before.get('elapsed_time_raw'), after.get('uptime') or after.get('elapsed_time_raw'))}")
    lines.append(f"      Uptime seconds: {_pair(before.get('elapsed_time_seconds'), after.get('elapsed_time_seconds'))}")
    lines.append(f"      Flap count: {_pair(before.get('flap_count'), after.get('flap_count'))}")
    lines.append("      Peer counters:")
    lines.append("        " + _counter_line("active", before, after, "active_prefix_count"))
    lines.append("        " + _counter_line("received", before, after, "received_prefix_count"))
    lines.append("        " + _counter_line("accepted", before, after, "accepted_prefix_count"))
    lines.append("        " + _counter_line("suppressed", before, after, "suppressed_prefix_count"))
    lines.append("        " + _counter_line("advertised", before, after, "advertised_prefix_count"))

    findings = _findings_from(peer)
    if findings:
        lines.append("      Peer findings:")
        for finding in findings:
            lines.append(
                "        - "
                f"{finding.get('severity')} {finding.get('rule')}: "
                f"{finding.get('message')}"
            )

    families = _families_from(peer)
    if families:
        lines.append("      Family/Table Details:")
        for family in families:
            _append_family_detail(lines, family)


def _append_family_detail(lines: list[str], family: dict[str, object]) -> None:
    before = _record_from(family, "before")
    after = _record_from(family, "after")
    table = _text(family.get("table") or before.get("table") or after.get("table"))
    family_name = _text(family.get("family") or before.get("family") or after.get("family"))

    lines.append(f"        Table: {table}")
    lines.append(f"          Family: {family_name}")
    lines.append(f"          Result: {family.get('result')}")
    if before.get("rib_state") or after.get("rib_state"):
        lines.append(f"          RIB state: {_pair(before.get('rib_state'), after.get('rib_state'))}")
    if before.get("send_state") or after.get("send_state"):
        lines.append(f"          Send state: {_pair(before.get('send_state'), after.get('send_state'))}")
    lines.append(f"          active: {_pair(before.get('active_prefix_count'), after.get('active_prefix_count'))}")
    lines.append(f"          received: {_pair(before.get('received_prefix_count'), after.get('received_prefix_count'))}")
    lines.append(f"          accepted: {_pair(before.get('accepted_prefix_count'), after.get('accepted_prefix_count'))}")
    lines.append(f"          suppressed: {_pair(before.get('suppressed_prefix_count'), after.get('suppressed_prefix_count'))}")
    lines.append(f"          advertised: {_pair(before.get('advertised_prefix_count'), after.get('advertised_prefix_count'))}")

    findings = _findings_from(family)
    if findings:
        lines.append("          Findings:")
        for finding in findings:
            lines.append(
                "            - "
                f"{finding.get('severity')} {finding.get('rule')}: "
                f"{finding.get('message')}"
            )


def format_full_detail(payload: dict[str, object]) -> str:
    """Build a detailed text report for the full BGP report."""
    reports = payload["reports"]
    assert isinstance(reports, dict)

    state_reports = reports.get("state", [])
    health_reports = reports.get("session_health", [])

    lines = [
        format_full_summary(payload),
    ]
    _append_report_section(lines, "DETAILED REPORT", major=True)
    _append_report_section(lines, "BGP-STATE device reports:")

    if isinstance(state_reports, list):
        for report in state_reports:
            if isinstance(report, dict):
                _append_state_detail(lines, report)

    _append_report_section(lines, "BGP-SESSION-HEALTH device reports:")

    if isinstance(health_reports, list):
        for report in health_reports:
            if not isinstance(report, dict):
                continue

            lines.append(f"  Device: {report.get('device')}")
            lines.append(f"    Result: {report.get('result')}")
            lines.append(f"    Coverage: {report.get('coverage', 'UNKNOWN')}")
            lines.append(
                "    Sources: "
                f"{report.get('before_source_requested', 'unknown')}->"
                f"{report.get('before_source_actual', 'unknown')} / "
                f"{report.get('after_source_requested', 'unknown')}->"
                f"{report.get('after_source_actual', 'unknown')}"
            )
            lines.append(
                "    Peers: "
                f"total={report.get('peers_total', 0)} "
                f"passed={report.get('peers_passed', 0)} "
                f"failed={report.get('peers_failed', 0)} "
                f"warning={report.get('peers_warning', 0)} "
                f"unhealthy={report.get('peers_unhealthy', 0)} "
                f"not_evaluated={report.get('peers_not_evaluated', 0)} "
                f"partial={report.get('peers_partial', 0)}"
            )
            lines.append(
                "    Families: "
                f"total={report.get('families_total', 0)} "
                f"warning={report.get('families_warning', 0)} "
                f"failed={report.get('families_failed', 0)} "
                f"not_evaluated={report.get('families_not_evaluated', 0)}"
            )

            peers = report.get("peers", [])
            if not isinstance(peers, list):
                continue
            lines.append("    Peer Summary:")
            for peer in peers:
                if isinstance(peer, dict):
                    _append_peer_detail(lines, peer)

    return "\n".join(lines)


def write_full_report_files(
    *,
    payload: dict[str, object],
    report_directory: object,
) -> SavedFullReportPaths:
    """Write full report summary, detail and JSON files."""
    path = Path(report_directory)
    path.mkdir(parents=True, exist_ok=True)

    summary_path = path / "full_summary.txt"
    detail_path = path / "full_detail.txt"
    json_path = path / "full_report.json"

    summary_path.write_text(
        format_full_summary(payload) + "\n",
        encoding="utf-8",
    )
    detail_path.write_text(
        format_full_detail(payload) + "\n",
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return SavedFullReportPaths(
        directory=path,
        summary=summary_path,
        detail=detail_path,
        json=json_path,
        summary_path=summary_path,
        detail_path=detail_path,
        json_path=json_path,
    )


def write_full_reports(
    *,
    snapshot_root: object,
    payload: dict[str, object],
    timestamp: str,
) -> SavedFullReportPaths:
    """Write reports under the standard snapshot comparison report path."""
    report_directory = (
        Path(snapshot_root)
        / safe_path_part(str(payload["mw_id"]))
        / "comparison_reports"
        / timestamp
    )

    return write_full_report_files(
        payload=payload,
        report_directory=report_directory,
    )
