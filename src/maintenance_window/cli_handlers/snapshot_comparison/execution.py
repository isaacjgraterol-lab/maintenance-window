from __future__ import annotations

import argparse
import json
from types import SimpleNamespace
from typing import Any

from maintenance_window.cli_handlers.snapshot_comparison.comparison import (
    compare_snapshot_device,
)
from maintenance_window.cli_handlers.snapshot_comparison.exporting import (
    export_snapshot_comparison_report,
)
from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotDeviceComparison,
)
from maintenance_window.cli_handlers.snapshot_comparison.rendering import (
    _print_snapshot_global_summary,
    print_device_comparison,
    print_device_comparison_error,
    print_device_comparison_heading,
    print_exit_code,
    print_export_saved,
)
from maintenance_window.cli_handlers.snapshot_comparison.request import (
    build_snapshot_comparison_request,
)
from maintenance_window.cli_handlers.snapshot_comparison.summary import (
    _build_snapshot_global_summary,
)
from maintenance_window.protocols.bgp.full_report.cli import (
    run_bgp_full_report,
)
from maintenance_window.protocols.bgp.session_health.cli import (
    run_bgp_session_health_comparison,
)


_DEVICE_COMPARISON_ERRORS = (
    FileNotFoundError,
    ValueError,
    RuntimeError,
    json.JSONDecodeError,
)


def _build_error_result(
    *,
    device_name: str,
    exc: BaseException,
) -> SimpleNamespace:
    """Build an exportable device result for a comparison error."""
    return SimpleNamespace(
        report={
            "device": device_name,
            "result": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "fail_reasons": ["comparison_error"],
        }
    )


def _snapshot_exit_code(
    global_summary: dict[str, object],
) -> int:
    """Return 0 for PASS, 1 for FAIL, and 2 for ERROR."""
    overall_result = global_summary["overall_result"]

    if overall_result == "ERROR":
        return 2

    if overall_result == "FAIL":
        return 1

    return 0


def run_bgp_snapshot_comparison(args: argparse.Namespace) -> int:
    """Compare BGP snapshots and return a Maintenance Window exit code."""
    request = build_snapshot_comparison_request(args)

    if request.module == "session-health":
        return run_bgp_session_health_comparison(request)

    if request.module == "full":
        return run_bgp_full_report(request)

    if request.module != "state":
        raise ValueError(f"Unsupported BGP snapshot module: {request.module}")

    results: list[Any] = []

    for device_name in request.device_names:
        print_device_comparison_heading(device_name)

        try:
            result = compare_snapshot_device(request, device_name)
        except _DEVICE_COMPARISON_ERRORS as exc:
            print_device_comparison_error(device_name, exc)
            results.append(
                _build_error_result(
                    device_name=device_name,
                    exc=exc,
                )
            )
            continue

        print_device_comparison(result)
        results.append(result)

    global_summary = _build_snapshot_global_summary(
        [result.report for result in results]
    )
    _print_snapshot_global_summary(global_summary)

    if request.export_path is not None:
        export_snapshot_comparison_report(
            request,
            results,
            global_summary,
        )
        print_export_saved(request.export_path)

    exit_code = _snapshot_exit_code(global_summary)
    print_exit_code(exit_code)

    return exit_code
