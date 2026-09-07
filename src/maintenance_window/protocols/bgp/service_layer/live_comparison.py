from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.service_layer.explicit_collection import (
    collect_with_source,
)
from maintenance_window.protocols.bgp.source_comparison.comparison import (
    compare_bgp_sources,
)
from maintenance_window.protocols.bgp.source_comparison.models import BgpSourceComparison


CollectionResult = tuple[list[BgpSession], Path, str]
ExplicitCollector = Callable[..., CollectionResult]
ComparisonFunction = Callable[..., BgpSourceComparison]
SUPPORTED_COMPARISON_SOURCES = frozenset({"ssh", "pyez", "gnmic"})


def validate_comparison_sources(
    left_source: str,
    right_source: str,
) -> None:
    """Validate a pair of explicit live collection sources."""
    if left_source == right_source:
        raise ValueError("Comparison requires two different sources.")

    if left_source not in SUPPORTED_COMPARISON_SOURCES:
        raise ValueError(
            f"Unsupported left comparison source: {left_source}"
        )

    if right_source not in SUPPORTED_COMPARISON_SOURCES:
        raise ValueError(
            f"Unsupported right comparison source: {right_source}"
        )


def compare_live_sources(
    left_source: str,
    right_source: str,
    device: Device,
    defaults: dict[str, str],
    profiles: dict[str, CredentialProfile],
    settings: dict[str, Any],
    project_root: Path,
    *,
    collect_with_source_fn: ExplicitCollector = collect_with_source,
    compare_bgp_sources_fn: ComparisonFunction = compare_bgp_sources,
) -> tuple[BgpSourceComparison, dict[str, Path], dict[str, str]]:
    """Collect through two explicit sources and compare normalized sessions."""
    validate_comparison_sources(left_source, right_source)

    common = {
        "device": device,
        "defaults": defaults,
        "profiles": profiles,
        "settings": settings,
        "project_root": project_root,
    }

    left_sessions, left_raw_file, left_actual_source = (
        collect_with_source_fn(source=left_source, **common)
    )
    right_sessions, right_raw_file, right_actual_source = (
        collect_with_source_fn(source=right_source, **common)
    )

    comparison = compare_bgp_sources_fn(
        left_source=left_actual_source,
        left_sessions=left_sessions,
        right_source=right_actual_source,
        right_sessions=right_sessions,
    )

    raw_files = {
        left_actual_source: left_raw_file,
        right_actual_source: right_raw_file,
    }
    actual_sources = {
        left_source: left_actual_source,
        right_source: right_actual_source,
    }

    return comparison, raw_files, actual_sources
