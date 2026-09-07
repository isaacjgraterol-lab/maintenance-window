"""Human-readable detailed validation report."""

from __future__ import annotations

from typing import Any

from maintenance_window.cli_handlers.validation.output.summary import (
    render_summary_report,
)


def render_detail_report(payload: dict[str, Any]) -> str:
    """Render the detailed operator report."""
    lines: list[str] = []
    lines.append("Maintenance Window BGP Validation - Detail")
    lines.append("")

    detail_lines = payload.get("detail_lines") or []
    if detail_lines:
        lines.append("Collection details:")
        for item in detail_lines:
            lines.append(f"  {item}")
        lines.append("")

    lines.append(render_summary_report(payload).rstrip())

    sessions = payload.get("sessions") or {}
    lines.append("")
    lines.append("Sessions:")
    if sessions:
        for device, device_sessions in sessions.items():
            lines.append(f"")
            lines.append(f"Device: {device}")
            for session in device_sessions:
                lines.append(
                    "  "
                    f"{session['neighbor']:<40} "
                    f"{session['state']}"
                )
    else:
        lines.append("  None")

    artifacts = payload.get("artifacts") or {}
    raw_files = artifacts.get("raw_files") or []
    snapshot_files = artifacts.get("snapshot_files") or []

    lines.append("")
    lines.append("Raw files:")
    if raw_files:
        for item in raw_files:
            lines.append(f"  {item}")
    else:
        lines.append("  None")

    lines.append("")
    lines.append("Snapshots:")
    if snapshot_files:
        for item in snapshot_files:
            lines.append(f"  {item}")
    else:
        lines.append("  None")

    return "\n".join(lines) + "\n"
