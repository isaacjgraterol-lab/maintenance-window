"""Build and persist JSON source-comparison reports."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from maintenance_window.core.output import export_json_report
from maintenance_window.cli_handlers.source_comparison.models import (
    DeviceSourceComparison,
    SourceComparisonRequest,
)


ExportJsonReport = Callable[[object, Path], None]


def build_source_comparison_export_payload(
    request: SourceComparisonRequest,
    results: list[DeviceSourceComparison],
) -> dict[str, object]:
    """Create the stable JSON payload for a source-comparison run."""
    return {
        "protocol": "bgp",
        "mode": "compare-source",
        "left_source": request.left_source,
        "right_source": request.right_source,
        "devices": [device.host for device in request.devices],
        "reports": [result.report for result in results],
    }


def export_source_comparison_report(
    request: SourceComparisonRequest,
    results: list[DeviceSourceComparison],
    *,
    export_json_report_fn: ExportJsonReport = export_json_report,
) -> Path | None:
    """Persist the report when the operator supplied ``--export``."""
    if request.export_path is None:
        return None

    export_json_report_fn(
        build_source_comparison_export_payload(request, results),
        request.export_path,
    )
    return request.export_path
