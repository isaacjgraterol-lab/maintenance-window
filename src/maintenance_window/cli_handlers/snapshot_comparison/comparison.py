from __future__ import annotations

from typing import Any, cast

from maintenance_window.protocols.bgp.snapshot_comparison.comparison import (
    compare_bgp_snapshot_files,
)
from maintenance_window.protocols.bgp.snapshot_comparison.reports import (
    snapshot_comparison_to_dict,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshots import (
    BgpSnapshot,
    BgpSnapshotComparison,
)

from maintenance_window.cli_handlers.snapshot_comparison.defaults import (
    DEFAULT_BGP_SNAPSHOT_ROOT,
)
from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotComparisonRequest,
    SnapshotDeviceComparison,
)


def _extract_snapshot_comparison_parts(
    comparison_result: Any,
) -> tuple[BgpSnapshotComparison, BgpSnapshot, BgpSnapshot]:
    """Validate and unpack the comparison service tuple contract."""
    if not isinstance(comparison_result, tuple):
        raise RuntimeError(
            "compare_bgp_snapshot_files() must return "
            "(comparison, before_snapshot, after_snapshot)."
        )

    if len(comparison_result) != 3:
        raise RuntimeError(
            "compare_bgp_snapshot_files() returned an unexpected tuple. "
            "Expected exactly 3 values: "
            "(comparison, before_snapshot, after_snapshot)."
        )

    comparison, before_snapshot, after_snapshot = comparison_result

    if not hasattr(comparison, "before_stage") or not hasattr(
        comparison,
        "after_stage",
    ):
        raise RuntimeError(
            "compare_bgp_snapshot_files() did not return a valid "
            "BGP snapshot comparison object as the first tuple item."
        )

    return (
        cast(BgpSnapshotComparison, comparison),
        cast(BgpSnapshot, before_snapshot),
        cast(BgpSnapshot, after_snapshot),
    )


def compare_snapshot_device(
    request: SnapshotComparisonRequest,
    device_name: str,
) -> SnapshotDeviceComparison:
    """Load and compare before/after snapshots for one device."""
    comparison_result = compare_bgp_snapshot_files(
        snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
        mw_id=request.mw_id,
        before_stage=request.before_stage,
        after_stage=request.after_stage,
        device=device_name,
    )

    comparison, before_snapshot, after_snapshot = (
        _extract_snapshot_comparison_parts(comparison_result)
    )

    report = snapshot_comparison_to_dict(
        comparison,
        before_snapshot,
        after_snapshot,
    )

    return SnapshotDeviceComparison(
        device_name=device_name,
        comparison=comparison,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        report=report,
    )
