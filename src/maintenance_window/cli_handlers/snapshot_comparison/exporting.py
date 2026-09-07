from __future__ import annotations

from maintenance_window.core.output import export_json_report

from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotComparisonRequest,
    SnapshotDeviceComparison,
)


def build_snapshot_comparison_export_payload(
    request: SnapshotComparisonRequest,
    results: list[SnapshotDeviceComparison],
    global_summary: dict[str, object],
) -> dict[str, object]:
    """Build the JSON-serializable multi-device export payload."""
    return {
        "protocol": "bgp",
        "mode": "compare-snapshots",
        "mw_id": request.mw_id,
        "before_stage": request.before_stage,
        "after_stage": request.after_stage,
        "global_summary": global_summary,
        "devices": request.device_names,
        "reports": [
            result.report
            for result in results
        ],
    }


def export_snapshot_comparison_report(
    request: SnapshotComparisonRequest,
    results: list[SnapshotDeviceComparison],
    global_summary: dict[str, object],
) -> None:
    """Export the comparison report when an output path was requested."""
    if request.export_path is None:
        return

    payload = build_snapshot_comparison_export_payload(
        request,
        results,
        global_summary,
    )

    export_json_report(
        payload,
        request.export_path,
    )
