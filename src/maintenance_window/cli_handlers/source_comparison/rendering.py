"""Render live source-comparison results to the CLI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from maintenance_window.core.models import Device
from maintenance_window.protocols.bgp.source_comparison.reports import (
    print_comparison_report,
)
from maintenance_window.cli_handlers.source_comparison.models import (
    DeviceSourceComparison,
    SourceComparisonRequest,
)


PrintComparisonReport = Callable[[Any], None]


def print_device_comparison_heading(
    request: SourceComparisonRequest,
    device: Device,
) -> None:
    """Print the device and requested source pair."""
    print(
        f"\nComparing BGP sources for device {device.host}: "
        f"{request.left_source} vs {request.right_source}"
    )


def print_device_comparison(
    result: DeviceSourceComparison,
    *,
    print_comparison_report_fn: PrintComparisonReport = print_comparison_report,
) -> None:
    """Print protocol report, raw files, and actual collector sources."""
    print_comparison_report_fn(result.comparison)

    print("\nRaw source files:")
    for source, path in result.raw_files.items():
        print(f"  {source}: {path}")

    print("Actual sources:")
    for requested_source, actual_source in result.actual_sources.items():
        print(f"  {requested_source}: {actual_source}")


def print_source_comparison_export(path: object) -> None:
    """Print the saved report path."""
    print(f"\nSource comparison report saved: {path}")
