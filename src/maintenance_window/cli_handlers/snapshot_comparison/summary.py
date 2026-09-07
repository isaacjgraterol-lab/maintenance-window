from __future__ import annotations


def _build_snapshot_global_summary(
    reports: list[dict[str, object]],
) -> dict[str, object]:
    """Build the global Maintenance Window result from device reports."""
    total_devices = len(reports)

    passed_reports = [
        report
        for report in reports
        if report.get("result") == "PASS"
    ]
    failed_reports = [
        report
        for report in reports
        if report.get("result") == "FAIL"
    ]
    error_reports = [
        report
        for report in reports
        if report.get("result") == "ERROR"
    ]

    passed_devices = len(passed_reports)
    failed_devices = len(failed_reports)
    error_devices = len(error_reports)

    devices_with_lost_sessions: list[str] = []
    devices_with_new_sessions: list[str] = []
    devices_with_state_changes: list[str] = []
    devices_with_new_unhealthy: list[str] = []
    devices_with_errors: list[str] = []

    total_lost_sessions = 0
    total_new_sessions = 0
    total_state_changes = 0
    total_new_unhealthy = 0
    total_resolved_unhealthy = 0
    total_persistent_unhealthy = 0

    for report in reports:
        device = str(report.get("device", "unknown"))

        if report.get("result") == "ERROR":
            devices_with_errors.append(device)

        lost_sessions_count = int(
            report.get("lost_sessions_count", 0)
        )
        new_sessions_count = int(
            report.get("new_sessions_count", 0)
        )
        state_changes_count = int(
            report.get("state_changes_count", 0)
        )
        new_unhealthy_count = int(
            report.get("new_unhealthy_count", 0)
        )
        resolved_unhealthy_count = int(
            report.get("resolved_unhealthy_count", 0)
        )
        persistent_unhealthy_count = int(
            report.get("persistent_unhealthy_count", 0)
        )

        total_lost_sessions += lost_sessions_count
        total_new_sessions += new_sessions_count
        total_state_changes += state_changes_count
        total_new_unhealthy += new_unhealthy_count
        total_resolved_unhealthy += resolved_unhealthy_count
        total_persistent_unhealthy += persistent_unhealthy_count

        if lost_sessions_count > 0:
            devices_with_lost_sessions.append(device)

        if new_sessions_count > 0:
            devices_with_new_sessions.append(device)

        if state_changes_count > 0:
            devices_with_state_changes.append(device)

        if new_unhealthy_count > 0:
            devices_with_new_unhealthy.append(device)

    if error_devices > 0:
        overall_result = "ERROR"
    elif failed_devices > 0:
        overall_result = "FAIL"
    else:
        overall_result = "PASS"

    return {
        "overall_result": overall_result,
        "total_devices": total_devices,
        "passed_devices": passed_devices,
        "failed_devices": failed_devices,
        "error_devices": error_devices,
        "total_lost_sessions": total_lost_sessions,
        "total_new_sessions": total_new_sessions,
        "total_state_changes": total_state_changes,
        "total_new_unhealthy": total_new_unhealthy,
        "total_resolved_unhealthy": total_resolved_unhealthy,
        "total_persistent_unhealthy": total_persistent_unhealthy,
        "devices_with_lost_sessions": devices_with_lost_sessions,
        "devices_with_new_sessions": devices_with_new_sessions,
        "devices_with_state_changes": devices_with_state_changes,
        "devices_with_new_unhealthy": devices_with_new_unhealthy,
        "devices_with_errors": devices_with_errors,
    }
