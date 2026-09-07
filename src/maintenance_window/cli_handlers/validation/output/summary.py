"""Human-readable summary validation report."""

from __future__ import annotations

from typing import Any


def _line(label: str, value: object) -> str:
    return f"  {label}: {value}"


def render_summary_report(payload: dict[str, Any]) -> str:
    """Render the compact operator summary."""
    lines: list[str] = []
    lines.append("Maintenance Window BGP Validation")
    lines.append("")
    lines.append(f"Protocol: {str(payload.get('protocol', '')).upper()}")
    lines.append(f"Source requested: {payload.get('source_requested')}")
    if payload.get("workers") is not None:
        lines.append(f"Workers: {payload.get('workers')}")
    if payload.get("auth_backend") is not None:
        lines.append(f"Auth backend: {payload.get('auth_backend')}")
    if payload.get("device_selector") is not None:
        lines.append(f"Device selector: {payload.get('device_selector')}")
    if payload.get("snapshot_stage") is not None:
        lines.append(f"Snapshot stage: {payload.get('snapshot_stage')}")
    if payload.get("mw_id") is not None:
        lines.append(f"MW ID: {payload.get('mw_id')}")

    summary = payload["collection_summary"]
    lines.append("")
    lines.append("Collection summary:")
    lines.append(_line("Devices selected", summary["devices_selected"]))
    lines.append(_line("Devices collected", summary["devices_collected"]))
    lines.append(_line("Devices failed", summary["devices_failed"]))
    lines.append(_line("Sessions collected", summary["sessions_collected"]))
    lines.append(_line("Sessions selected", summary["sessions_selected"]))
    lines.append(_line("Filter", payload.get("filter")))

    lines.append("")
    lines.append("Session state summary:")
    state_summary = payload.get("session_state_summary") or {}
    if state_summary:
        for state, count in state_summary.items():
            lines.append(_line(state, count))
    else:
        lines.append("  None")

    per_device = payload.get("per_device_summary") or []
    lines.append("")
    lines.append("Per-device summary:")
    if per_device:
        for item in per_device:
            status = item.get("status")
            if status == "FAILED":
                lines.append(
                    "  "
                    f"{item['device']}   "
                    f"source={item['source']}   FAILED"
                )
            else:
                lines.append(
                    "  "
                    f"{item['device']}   "
                    f"source={item['source']}   "
                    f"sessions={item['sessions']}   "
                    f"unhealthy={item['unhealthy']}"
                )
    else:
        lines.append("  None")

    artifacts = payload.get("artifacts") or {}
    lines.append("")
    lines.append("Artifacts:")
    lines.append(_line("Raw files saved", artifacts.get("raw_files_saved", 0)))
    lines.append(_line("Snapshots saved", artifacts.get("snapshots_saved", 0)))
    report_files = artifacts.get("validation_report_files")
    if report_files:
        lines.append(_line("Summary report", report_files.get("summary")))
        lines.append(_line("Detail report", report_files.get("detail")))
        lines.append(_line("JSON report", report_files.get("json")))
    else:
        lines.append(_line("Snapshot reports", "not saved"))

    errors = payload.get("collection_errors") or []
    lines.append("")
    lines.append("Collection errors:")
    if errors:
        for error in errors:
            lines.append(
                "  "
                f"{error['device']}   "
                f"{error['source']}   "
                f"{error['error_type']}   "
                f"{error['error']}"
            )
    else:
        lines.append("  None")

    lines.append("")
    lines.append("Result:")
    lines.append(f"  {payload.get('result')}")
    lines.append("")
    lines.append(f"Exit code: {payload.get('exit_code')}")
    return "\n".join(lines) + "\n"
