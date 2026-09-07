"""Read exported JSON reports and extract GUI summary cards."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_TIMESTAMP_RE = re.compile(r"(20\d{6}_\d{6})")


def _get(data: dict[str, Any], *keys: str, default: object = None) -> object:
    node: object = data
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key, default)
    return node


def _first_report(data: dict[str, Any], section: str) -> dict[str, Any]:
    reports = data.get("reports", {})
    if not isinstance(reports, dict):
        return {}
    entries = reports.get(section, [])
    if isinstance(entries, list) and entries and isinstance(entries[0], dict):
        return entries[0]
    return {}


def _report_entries(data: dict[str, Any], section: str) -> list[dict[str, Any]]:
    reports = data.get("reports", {})
    if not isinstance(reports, dict):
        return []
    entries = reports.get(section, [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _raw_timestamp(value: object) -> str:
    if not value:
        return ""
    match = _TIMESTAMP_RE.search(str(value))
    if not match:
        return ""
    return match.group(1)


def _source_coverage_text(value: object) -> str:
    if isinstance(value, dict):
        parts = [f"{key}: {value[key]}" for key in sorted(value)]
        return ", ".join(parts) if parts else "N/A"
    if value is None:
        return "N/A"
    text = str(value).strip()
    return text or "N/A"


def _count_findings(data: dict[str, Any]) -> dict[str, int]:
    """Return global finding counts, preferring the report's canonical inventory."""
    existing = data.get("finding_counts")
    if not isinstance(existing, dict):
        existing = _get(data, "global_summary", "finding_counts", default={})
    if isinstance(existing, dict) and existing:
        return {str(key): int(value or 0) for key, value in existing.items()}

    counts: dict[str, int] = {}
    seen_peer_rules: set[tuple[str, str, str]] = set()
    for device_report in _report_entries(data, "session_health"):
        device = str(device_report.get("device") or "")
        peers = device_report.get("peers", [])
        if not isinstance(peers, list):
            continue
        for peer in peers:
            if not isinstance(peer, dict):
                continue
            neighbor = str(peer.get("neighbor") or "")
            findings = peer.get("findings", [])
            if isinstance(findings, list):
                for finding in findings:
                    if not isinstance(finding, dict):
                        continue
                    rule = str(finding.get("rule") or "unknown")
                    key = (device, neighbor, rule)
                    if key in seen_peer_rules:
                        continue
                    seen_peer_rules.add(key)
                    counts[rule] = counts.get(rule, 0) + 1

            families = peer.get("families", [])
            if not isinstance(families, list):
                continue
            for family in families:
                if not isinstance(family, dict):
                    continue
                family_findings = family.get("findings", [])
                if not isinstance(family_findings, list):
                    continue
                for finding in family_findings:
                    if not isinstance(finding, dict):
                        continue
                    rule = str(finding.get("rule") or "unknown")
                    counts[rule] = counts.get(rule, 0) + 1
    return counts


def _snapshot_evidence_rows(data: dict[str, Any], *, limit: int = 12) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    session_by_device: dict[str, dict[str, Any]] = {}
    for report in _report_entries(data, "session_health"):
        device = str(report.get("device") or "")
        if device and device not in session_by_device:
            session_by_device[device] = report

    for report in _report_entries(data, "state"):
        device = str(report.get("device") or "")
        before = report.get("before", {})
        after = report.get("after", {})
        if not isinstance(before, dict):
            before = {}
        if not isinstance(after, dict):
            after = {}

        session_report = session_by_device.get(device, {})
        before_raw = before.get("raw_file") or session_report.get("before_raw_file")
        after_raw = after.get("raw_file") or session_report.get("after_raw_file")

        rows.append(
            {
                "device": device,
                "before_source": str(before.get("source_actual") or ""),
                "before_raw_timestamp": _raw_timestamp(before_raw),
                "after_source": str(after.get("source_actual") or ""),
                "after_raw_timestamp": _raw_timestamp(after_raw),
                "before_raw_file": str(before_raw or ""),
                "after_raw_file": str(after_raw or ""),
            }
        )

    return rows[:limit]


def _sum_state_snapshot_metric(
    data: dict[str, Any],
    *,
    stage: str,
    key: str,
) -> int:
    total = 0
    for report in _report_entries(data, "state"):
        snapshot = report.get(stage, {})
        if not isinstance(snapshot, dict):
            continue
        value = snapshot.get(key)
        try:
            if value is not None:
                total += int(value)
        except (TypeError, ValueError):
            continue
    return total


def _device_summary_rows(data: dict[str, Any]) -> list[dict[str, object]]:
    existing = data.get("device_summary")
    if isinstance(existing, list):
        return [item for item in existing if isinstance(item, dict)]

    state_by_device = {
        str(report.get("device") or ""): report
        for report in _report_entries(data, "state")
        if report.get("device")
    }
    health_by_device = {
        str(report.get("device") or ""): report
        for report in _report_entries(data, "session_health")
        if report.get("device")
    }
    devices = list(dict.fromkeys([*state_by_device, *health_by_device]))

    rows: list[dict[str, object]] = []
    for device in devices:
        state = state_by_device.get(device, {})
        health = health_by_device.get(device, {})
        before = state.get("before", {})
        after = state.get("after", {})
        if not isinstance(before, dict):
            before = {}
        if not isinstance(after, dict):
            after = {}

        rows.append(
            {
                "device": device,
                "overall_result": (
                    health.get("result")
                    if health.get("result") not in {None, "PASS"}
                    else state.get("result", health.get("result", "UNKNOWN"))
                ),
                "state": {
                    "result": state.get("result", "UNKNOWN"),
                    "total_sessions_before": before.get("total_sessions", 0),
                    "total_sessions_after": after.get("total_sessions", 0),
                    "lost_sessions": state.get("lost_sessions_count", 0),
                    "new_sessions": state.get("new_sessions_count", 0),
                    "state_changes": state.get("state_changes_count", 0),
                    "new_unhealthy": state.get("new_unhealthy_count", 0),
                    "persistent_unhealthy": state.get(
                        "persistent_unhealthy_count", 0
                    ),
                },
                "session_health": {
                    "result": health.get("result", "UNKNOWN"),
                    "total_peers": health.get("peers_total", 0),
                    "passed_peers": health.get("peers_passed", 0),
                    "failed_peers": health.get("peers_failed", 0),
                    "warning_peers": health.get("peers_warning", 0),
                    "unhealthy_peers": health.get("peers_unhealthy", 0),
                    "not_evaluated_peers": health.get(
                        "peers_not_evaluated", 0
                    ),
                    "families_total": health.get("families_total", 0),
                    "warning_families": health.get("families_warning", 0),
                    "failed_families": health.get("families_failed", 0),
                },
                "finding_counts": {},
            }
        )
    return rows


def read_report_summary(path: Path | None) -> dict[str, object]:
    """Return a compact summary for the GUI result panel."""
    if path is None or not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return {}

    state_summary = _get(data, "global_summary", "state", default={})
    session_health_summary = _get(
        data,
        "global_summary",
        "session_health",
        default={},
    )
    finding_counts = _count_findings(data)

    return {
        "overall_result": data.get("result") or _get(
            data, "global_summary", "overall_result"
        ),
        "state_result": data.get("state_result") or _get(
            data, "global_summary", "modules", "state"
        ),
        "session_health_result": data.get("session_health_result") or _get(
            data, "global_summary", "modules", "session-health"
        ),
        "total_sessions_before": _sum_state_snapshot_metric(
            data, stage="before", key="total_sessions"
        ),
        "total_sessions_after": _sum_state_snapshot_metric(
            data, stage="after", key="total_sessions"
        ),
        "unique_sessions_before": _sum_state_snapshot_metric(
            data, stage="before", key="unique_sessions"
        ),
        "unique_sessions_after": _sum_state_snapshot_metric(
            data, stage="after", key="unique_sessions"
        ),
        "duplicate_entries_before": _sum_state_snapshot_metric(
            data, stage="before", key="duplicate_entries"
        ),
        "duplicate_entries_after": _sum_state_snapshot_metric(
            data, stage="after", key="duplicate_entries"
        ),
        "lost_sessions": _get(state_summary, "total_lost_sessions"),
        "new_sessions": _get(state_summary, "total_new_sessions"),
        "state_changes": _get(state_summary, "total_state_changes"),
        "unhealthy_fsm_transitions": _get(
            state_summary,
            "total_unhealthy_fsm_transitions",
        ),
        "new_unhealthy": _get(state_summary, "total_new_unhealthy"),
        "resolved_unhealthy": _get(state_summary, "total_resolved_unhealthy"),
        "persistent_unhealthy": _get(
            state_summary,
            "total_persistent_unhealthy",
        ),
        "warning_peers": _get(session_health_summary, "total_warning_peers"),
        "failed_peers": _get(session_health_summary, "total_failed_peers"),
        "unhealthy_peers": _get(session_health_summary, "total_unhealthy_peers"),
        "warning_families": _get(
            session_health_summary,
            "total_warning_families",
        ),
        "failed_families": _get(
            session_health_summary,
            "total_failed_families",
        ),
        "total_families": _get(session_health_summary, "total_families"),
        "not_evaluated_peers": _get(
            session_health_summary,
            "total_not_evaluated_peers",
        ),
        "partial_peers": _get(
            session_health_summary,
            "total_partial_peers",
        ),
        "health_coverage": _get(
            session_health_summary,
            "coverage",
        ),
        "fallback_device_count": _get(
            data,
            "source_coverage",
            "fallback_device_count",
        ),
        "before_source_coverage": _source_coverage_text(
            _get(data, "source_coverage", "before_actual")
        ),
        "after_source_coverage": _source_coverage_text(
            _get(data, "source_coverage", "after_actual")
        ),
        "session_restarts": finding_counts.get("session_restart_detected", 0),
        "uptime_resets": finding_counts.get("uptime_reset", 0),
        "flap_count_increases": finding_counts.get("flap_count_increased", 0),
        "flap_count_resets": finding_counts.get("flap_count_reset", 0),
        "low_after_uptime_peers": finding_counts.get("low_after_uptime", 0),
        "new_families": finding_counts.get("new_family_after", 0),
        "missing_families": finding_counts.get("missing_family_after", 0),
        "prefix_deltas": finding_counts.get("prefix_delta", 0),
        "persistent_unhealthy_findings": finding_counts.get(
            "persistent_unhealthy_peer", 0
        ),
        "device_summaries": _device_summary_rows(data),
        "snapshot_evidence": _snapshot_evidence_rows(data),
        "snapshot_evidence_total": len(_report_entries(data, "state")),
        "report_directory": data.get("report_directory"),
    }


def resolve_health_depth(
    *,
    source: str,
    selected: str = "auto",
    action: str = "",
    not_evaluated_peers: object = None,
) -> str:
    """Resolve operator-selected health depth into the applied depth."""
    if action == "compare-state" or selected == "state-only":
        return "state-only"

    if selected in {"partial-health", "full-health"}:
        return selected

    if source == "gnmic":
        return "partial-health"

    if isinstance(not_evaluated_peers, int) and not_evaluated_peers > 0:
        return "partial-health"

    if source in {"pyez", "ssh"}:
        return "full-health"

    if source == "manual":
        return "auto"

    return "unknown"


def health_depth_for_source(source: str) -> str:
    """Backward-compatible helper for old tests and callers."""
    return resolve_health_depth(source=source, selected="auto")
