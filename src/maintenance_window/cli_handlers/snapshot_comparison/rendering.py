from __future__ import annotations

from typing import cast

from maintenance_window.protocols.bgp.snapshot_comparison.reports import (
    print_snapshot_comparison_report,
)

from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotDeviceComparison,
)


def print_device_comparison_heading(device_name: str) -> None:
    """Print the device heading before loading its snapshots."""
    print(f"\nComparing BGP snapshots for device: {device_name}")


def print_device_comparison(
    result: SnapshotDeviceComparison,
) -> None:
    """Print one device-level comparison report."""
    print_snapshot_comparison_report(result.comparison)


def print_device_comparison_error(
    device_name: str,
    exc: BaseException,
) -> None:
    """Print one device-level comparison error."""
    print(
        "\nError comparing BGP snapshots for device "
        f"{device_name}: {exc}"
    )


def _print_snapshot_global_summary(
    global_summary: dict[str, object],
) -> None:
    """Print the global Maintenance Window comparison summary."""
    print("\nMaintenance Window global summary")
    print(f"Overall result: {global_summary['overall_result']}")
    print(f"Total devices: {global_summary['total_devices']}")
    print(f"Passed devices: {global_summary['passed_devices']}")
    print(f"Failed devices: {global_summary['failed_devices']}")
    print(f"Error devices: {global_summary['error_devices']}")
    print(
        "Total lost sessions: "
        f"{global_summary['total_lost_sessions']}"
    )
    print(
        "Total new sessions: "
        f"{global_summary['total_new_sessions']}"
    )
    print(
        "Total state changes: "
        f"{global_summary['total_state_changes']}"
    )
    print(
        "Total new unhealthy: "
        f"{global_summary['total_new_unhealthy']}"
    )
    print(
        "Total resolved unhealthy: "
        f"{global_summary['total_resolved_unhealthy']}"
    )
    print(
        "Total persistent unhealthy: "
        f"{global_summary['total_persistent_unhealthy']}"
    )

    devices_with_lost_sessions = cast(
        list[str],
        global_summary["devices_with_lost_sessions"],
    )
    devices_with_new_sessions = cast(
        list[str],
        global_summary["devices_with_new_sessions"],
    )
    devices_with_state_changes = cast(
        list[str],
        global_summary["devices_with_state_changes"],
    )
    devices_with_new_unhealthy = cast(
        list[str],
        global_summary["devices_with_new_unhealthy"],
    )
    devices_with_errors = cast(
        list[str],
        global_summary["devices_with_errors"],
    )

    if devices_with_lost_sessions:
        print(
            "Devices with lost sessions: "
            + ", ".join(devices_with_lost_sessions)
        )

    if devices_with_new_sessions:
        print(
            "Devices with new sessions: "
            + ", ".join(devices_with_new_sessions)
        )

    if devices_with_state_changes:
        print(
            "Devices with state changes: "
            + ", ".join(devices_with_state_changes)
        )

    if devices_with_new_unhealthy:
        print(
            "Devices with new unhealthy sessions: "
            + ", ".join(devices_with_new_unhealthy)
        )

    if devices_with_errors:
        print(
            "Devices with comparison errors: "
            + ", ".join(devices_with_errors)
        )


def print_export_saved(path: object) -> None:
    """Print the exported report location."""
    print(f"\nSnapshot comparison report saved: {path}")


def print_exit_code(exit_code: int) -> None:
    """Print the Maintenance Window comparison exit code."""
    print(f"\nMaintenance Window exit code: {exit_code}")
