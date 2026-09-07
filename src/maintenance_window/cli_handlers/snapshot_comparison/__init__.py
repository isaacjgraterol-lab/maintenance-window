"""Public facade for BGP snapshot comparison CLI handling.

The execution entry point is loaded lazily so full-report helpers can import the
comparison primitives without creating a circular import through this facade.
"""

from __future__ import annotations

from typing import Any

from maintenance_window.cli_handlers.snapshot_comparison.comparison import _extract_snapshot_comparison_parts
from maintenance_window.cli_handlers.snapshot_comparison.rendering import _print_snapshot_global_summary
from maintenance_window.cli_handlers.snapshot_comparison.request import parse_snapshot_compare_argument, resolve_snapshot_device_names
from maintenance_window.cli_handlers.snapshot_comparison.summary import _build_snapshot_global_summary

__all__ = ["_build_snapshot_global_summary", "_extract_snapshot_comparison_parts", "_print_snapshot_global_summary", "parse_snapshot_compare_argument", "resolve_snapshot_device_names", "run_bgp_snapshot_comparison"]


def __getattr__(name: str) -> Any:
    if name != "run_bgp_snapshot_comparison":
        raise AttributeError(name)
    from maintenance_window.cli_handlers.snapshot_comparison.execution import run_bgp_snapshot_comparison
    return run_bgp_snapshot_comparison
