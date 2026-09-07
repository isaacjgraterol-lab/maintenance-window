from __future__ import annotations

import json

from maintenance_window.cli_handlers.snapshot_comparison.defaults import (
    DEFAULT_BGP_SNAPSHOT_ROOT,
)
from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotComparisonRequest,
)
from maintenance_window.core.output import export_json_report
from maintenance_window.protocols.bgp.session_health.comparison import (
    compare_session_health_snapshots,
)
from maintenance_window.protocols.bgp.session_health.reports import (
    format_session_health_detail,
    format_session_health_summary,
    session_health_to_dict,
)


_SESSION_HEALTH_ERRORS = (
    FileNotFoundError,
    ValueError,
    RuntimeError,
    json.JSONDecodeError,
)


def _error_report(device_name: str, exc: BaseException) -> dict[str, object]:
    return {
        "module": "session-health",
        "device": device_name,
        "result": "ERROR",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "fail_reasons": ["comparison_error"],
    }


def _global_summary(reports: list[dict[str, object]]) -> dict[str, object]:
    total_devices = len(reports)
    error_devices = [report for report in reports if report.get("result") == "ERROR"]
    failed_devices = [report for report in reports if report.get("result") == "FAIL"]
    warning_devices = [report for report in reports if report.get("result") == "WARNING"]
    unhealthy_devices = [
        report
        for report in reports
        if report.get("result") == "PASS_WITH_UNHEALTHY_SESSIONS"
    ]
    passed_devices = [
        report
        for report in reports
        if report.get("result") in {"PASS", "PASS_WITH_UNHEALTHY_SESSIONS"}
    ]

    total_peers = sum(int(report.get("peers_total", 0)) for report in reports)
    total_failed_peers = sum(int(report.get("peers_failed", 0)) for report in reports)
    total_warning_peers = sum(int(report.get("peers_warning", 0)) for report in reports)
    total_unhealthy_peers = sum(int(report.get("peers_unhealthy", 0)) for report in reports)
    total_not_evaluated_peers = sum(
        int(report.get("peers_not_evaluated", 0)) for report in reports
    )
    total_partial_peers = sum(
        int(report.get("peers_partial", 0)) for report in reports
    )
    total_families = sum(int(report.get("families_total", 0)) for report in reports)
    total_family_warnings = sum(
        int(report.get("families_warning", 0)) for report in reports
    )
    total_family_failures = sum(
        int(report.get("families_failed", 0)) for report in reports
    )
    total_family_not_evaluated = sum(
        int(report.get("families_not_evaluated", 0)) for report in reports
    )
    partial_coverage_devices = [
        report for report in reports if report.get("coverage") != "FULL"
    ]

    if error_devices:
        overall_result = "ERROR"
    elif failed_devices or total_family_failures:
        overall_result = "FAIL"
    elif warning_devices or total_family_warnings:
        overall_result = "WARNING"
    elif unhealthy_devices:
        overall_result = "PASS_WITH_UNHEALTHY_SESSIONS"
    else:
        overall_result = "PASS"

    return {
        "overall_result": overall_result,
        "total_devices": total_devices,
        "passed_devices": len(passed_devices),
        "failed_devices": len(failed_devices),
        "warning_devices": len(warning_devices),
        "unhealthy_devices": len(unhealthy_devices),
        "error_devices": len(error_devices),
        "total_peers": total_peers,
        "total_failed_peers": total_failed_peers,
        "total_warning_peers": total_warning_peers,
        "total_unhealthy_peers": total_unhealthy_peers,
        "total_not_evaluated_peers": total_not_evaluated_peers,
        "total_partial_peers": total_partial_peers,
        "total_families": total_families,
        "total_family_warnings": total_family_warnings,
        "total_family_failures": total_family_failures,
        "total_family_not_evaluated": total_family_not_evaluated,
        "coverage": "PARTIAL" if partial_coverage_devices else "FULL",
        "devices_with_partial_coverage": [
            str(report.get("device")) for report in partial_coverage_devices
        ],
        "devices_with_errors": [str(report.get("device")) for report in error_devices],
        "devices_with_failures": [str(report.get("device")) for report in failed_devices],
        "devices_with_warnings": [str(report.get("device")) for report in warning_devices],
        "devices_with_unhealthy": [str(report.get("device")) for report in unhealthy_devices],
    }


def _exit_code(summary: dict[str, object]) -> int:
    if summary["overall_result"] == "ERROR":
        return 2
    if summary["overall_result"] == "FAIL":
        return 1
    return 0


def _print_global_summary(summary: dict[str, object]) -> None:
    print("\nBGP Session Health global summary")
    print(f"Overall result: {summary['overall_result']}")
    print(f"Total devices: {summary['total_devices']}")
    print(f"Passed devices: {summary['passed_devices']}")
    print(f"Failed devices: {summary['failed_devices']}")
    print(f"Warning devices: {summary['warning_devices']}")
    print(f"Unhealthy devices: {summary['unhealthy_devices']}")
    print(f"Error devices: {summary['error_devices']}")
    print(f"Total peers: {summary['total_peers']}")
    print(f"Failed peers: {summary['total_failed_peers']}")
    print(f"Warning peers: {summary['total_warning_peers']}")
    print(f"Unhealthy peers: {summary['total_unhealthy_peers']}")
    print(f"Not evaluated peers: {summary['total_not_evaluated_peers']}")
    print(f"Partial peers: {summary['total_partial_peers']}")
    print(f"Coverage: {summary['coverage']}")
    print(f"Total families: {summary['total_families']}")
    print(f"Family warnings: {summary['total_family_warnings']}")
    print(f"Family failures: {summary['total_family_failures']}")
    print(
        "Families not evaluated: "
        f"{summary['total_family_not_evaluated']}"
    )


def _export_payload(
    request: SnapshotComparisonRequest,
    reports: list[dict[str, object]],
    summary: dict[str, object],
) -> dict[str, object]:
    return {
        "protocol": "bgp",
        "module": "session-health",
        "mode": "compare-snapshots",
        "mw_id": request.mw_id,
        "before_stage": request.before_stage,
        "after_stage": request.after_stage,
        "global_summary": summary,
        "devices": request.device_names,
        "reports": reports,
    }


def run_bgp_session_health_comparison(
    request: SnapshotComparisonRequest,
) -> int:
    """Run BGP session-health comparison for before/after snapshots."""
    reports: list[dict[str, object]] = []

    print("BGP Session Health Comparison")
    print(f"MW ID: {request.mw_id}")
    print(f"Stages: {request.before_stage} -> {request.after_stage}")
    print(f"Output: {request.output}")

    for device_name in request.device_names:
        try:
            comparison = compare_session_health_snapshots(
                snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
                mw_id=request.mw_id,
                before_stage=request.before_stage,
                after_stage=request.after_stage,
                device=device_name,
            )
        except _SESSION_HEALTH_ERRORS as exc:
            reports.append(_error_report(device_name, exc))
            if request.output in {"summary", "detail"}:
                print(f"\nDevice: {device_name}")
                print("Result: ERROR")
                print(f"Error: {type(exc).__name__}: {exc}")
            continue

        report = session_health_to_dict(comparison)
        reports.append(report)

        if request.output == "summary":
            print("\n" + format_session_health_summary(comparison))
        elif request.output == "detail":
            print("\n" + format_session_health_detail(comparison))

    summary = _global_summary(reports)
    payload = _export_payload(request, reports, summary)

    if request.output == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_global_summary(summary)

    if request.export_path is not None:
        export_json_report(payload, request.export_path)
        print(f"\nBGP session-health report saved: {request.export_path}")

    exit_code = _exit_code(summary)
    print(f"\nMaintenance Window exit code: {exit_code}")
    return exit_code
