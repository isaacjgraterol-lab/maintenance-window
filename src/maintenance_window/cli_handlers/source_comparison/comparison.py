"""Compare two live BGP collectors for one device."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from maintenance_window.core.models import Device
from maintenance_window.protocols.bgp.service import compare_live_sources
from maintenance_window.protocols.bgp.source_comparison.reports import comparison_to_dict
from maintenance_window.cli_handlers.source_comparison.models import (
    DeviceSourceComparison,
    SourceComparisonRequest,
    SourceComparisonRuntime,
)


CompareLiveSources = Callable[..., tuple[Any, dict[str, Path], dict[str, str]]]
ComparisonToDict = Callable[[Any], dict[str, object]]


def compare_device_sources(
    request: SourceComparisonRequest,
    runtime: SourceComparisonRuntime,
    device: Device,
    *,
    compare_live_sources_fn: CompareLiveSources = compare_live_sources,
    comparison_to_dict_fn: ComparisonToDict = comparison_to_dict,
) -> DeviceSourceComparison:
    """Run both collectors and normalize their report metadata."""
    comparison, raw_files, actual_sources = compare_live_sources_fn(
        left_source=request.left_source,
        right_source=request.right_source,
        device=device,
        defaults=runtime.defaults,
        profiles=runtime.profiles,
        settings=runtime.settings,
        project_root=runtime.project_root,
    )

    report = comparison_to_dict_fn(comparison)
    report["raw_files"] = {
        source: str(path)
        for source, path in raw_files.items()
    }
    report["actual_sources"] = actual_sources

    return DeviceSourceComparison(
        comparison=comparison,
        report=report,
        raw_files=raw_files,
        actual_sources=actual_sources,
    )
