from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from maintenance_window.cli_handlers.snapshot_comparison.comparison import (
    compare_snapshot_device,
)
from maintenance_window.cli_handlers.snapshot_comparison.defaults import (
    DEFAULT_BGP_SNAPSHOT_ROOT,
)
from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotComparisonRequest,
)
from maintenance_window.cli_handlers.snapshot_comparison.summary import (
    _build_snapshot_global_summary,
)
from maintenance_window.core.output import export_json_report
from maintenance_window.protocols.bgp.full_report.reports import (
    build_full_payload,
    build_full_summary,
    build_session_health_summary,
    format_full_detail,
    format_full_summary,
    write_full_report_files,
)
from maintenance_window.protocols.bgp.session_health.comparison import (
    compare_session_health_snapshots,
)
from maintenance_window.protocols.bgp.session_health.reports import (
    session_health_to_dict,
)


_FULL_REPORT_ERRORS = (
    FileNotFoundError,
    ValueError,
    RuntimeError,
    json.JSONDecodeError,
)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _report_directory(request: SnapshotComparisonRequest) -> Path:
    return (
        DEFAULT_BGP_SNAPSHOT_ROOT
        / request.mw_id
        / "comparison_reports"
        / _timestamp()
    )


def _error_report(
    *,
    module: str,
    device_name: str,
    exc: BaseException,
) -> dict[str, object]:
    return {
        "module": module,
        "device": device_name,
        "result": "ERROR",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "fail_reasons": ["comparison_error"],
    }


def _exit_code(summary: dict[str, object]) -> int:
    if summary["overall_result"] == "ERROR":
        return 2
    if summary["overall_result"] == "FAIL":
        return 1
    return 0


def build_state_report(
    request: SnapshotComparisonRequest,
    device_name: str,
) -> dict[str, object]:
    """Build one BGP-STATE device report."""
    result = compare_snapshot_device(request, device_name)
    return result.report


def build_session_health_report(
    request: SnapshotComparisonRequest,
    device_name: str,
) -> dict[str, object]:
    """Build one BGP-SESSION-HEALTH device report."""
    comparison = compare_session_health_snapshots(
        snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
        mw_id=request.mw_id,
        before_stage=request.before_stage,
        after_stage=request.after_stage,
        device=device_name,
    )
    return session_health_to_dict(comparison)


def _collect_state_reports(
    request: SnapshotComparisonRequest,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    reports: list[dict[str, object]] = []

    for device_name in request.device_names:
        try:
            report = build_state_report(request, device_name)
        except _FULL_REPORT_ERRORS as exc:
            reports.append(
                _error_report(
                    module="state",
                    device_name=device_name,
                    exc=exc,
                )
            )
            continue

        reports.append(report)

    return reports, _build_snapshot_global_summary(reports)


def _collect_session_health_reports(
    request: SnapshotComparisonRequest,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    reports: list[dict[str, object]] = []

    for device_name in request.device_names:
        try:
            report = build_session_health_report(request, device_name)
        except _FULL_REPORT_ERRORS as exc:
            reports.append(
                _error_report(
                    module="session-health",
                    device_name=device_name,
                    exc=exc,
                )
            )
            continue

        reports.append(report)

    return reports, build_session_health_summary(reports)


def _build_payload(
    *,
    request: SnapshotComparisonRequest,
    report_directory: Path,
    state_reports: list[dict[str, object]],
    state_summary: dict[str, object],
    health_reports: list[dict[str, object]],
    health_summary: dict[str, object],
) -> dict[str, object]:
    full_summary = build_full_summary(
        state_summary=state_summary,
        session_health_summary=health_summary,
    )

    return build_full_payload(
        mw_id=request.mw_id,
        before_stage=request.before_stage,
        after_stage=request.after_stage,
        devices=request.device_names,
        full_summary=full_summary,
        state_reports=state_reports,
        session_health_reports=health_reports,
        report_directory=report_directory,
    )


def run_bgp_full_report_comparison(
    request: SnapshotComparisonRequest,
) -> int:
    """Run a combined BGP-STATE and BGP-SESSION-HEALTH report."""
    print("BGP Full Maintenance Report")
    print(f"MW ID: {request.mw_id}")
    print(f"Stages: {request.before_stage} -> {request.after_stage}")
    print(f"Output: {request.output}")

    report_directory = _report_directory(request)

    state_reports, state_summary = _collect_state_reports(request)
    health_reports, health_summary = _collect_session_health_reports(request)

    payload = _build_payload(
        request=request,
        report_directory=report_directory,
        state_reports=state_reports,
        state_summary=state_summary,
        health_reports=health_reports,
        health_summary=health_summary,
    )

    write_full_report_files(
        payload=payload,
        report_directory=report_directory,
    )

    if request.output == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif request.output == "detail":
        print()
        print(format_full_detail(payload))
    else:
        print()
        print(format_full_summary(payload))

    print()
    print(f"BGP full report saved: {report_directory}")

    if request.export_path is not None:
        export_json_report(payload, request.export_path)
        print(f"BGP full report JSON export saved: {request.export_path}")

    summary = payload["global_summary"]
    assert isinstance(summary, dict)

    exit_code = _exit_code(summary)
    print()
    print(f"Maintenance Window exit code: {exit_code}")
    return exit_code


def run_bgp_full_report(
    request: SnapshotComparisonRequest,
) -> int:
    """Compatibility wrapper for the BGP full report entry point."""
    return run_bgp_full_report_comparison(request)
