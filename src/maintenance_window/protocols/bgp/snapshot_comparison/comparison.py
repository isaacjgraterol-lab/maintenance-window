from __future__ import annotations

from pathlib import Path

from maintenance_window.engine.comparison.engine import compare_items
from maintenance_window.engine.comparison.indexing import duplicate_count
from maintenance_window.engine.comparison.validation import (
    validate_snapshot_pair,
)
from maintenance_window.protocols.bgp.snapshot_comparison.adapter import (
    BGP_COMPARISON_ADAPTER,
)
from maintenance_window.protocols.bgp.source_guard import (
    validate_same_actual_source,
)
from maintenance_window.protocols.bgp.state.rules import (
    build_bgp_fail_reasons,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
    BgpSnapshotComparison,
    BgpSnapshotDuplicateSession,
    BgpSnapshotStateChange,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshots import (
    load_bgp_snapshot,
)


def compare_bgp_snapshots(
    before: BgpSnapshot,
    after: BgpSnapshot,
) -> BgpSnapshotComparison:
    """Compare BGP snapshots before and after a maintenance window."""
    validate_snapshot_pair(before, after)
    validate_same_actual_source(before.source_actual, after.source_actual)

    diff = compare_items(
        before.sessions,
        after.sessions,
        BGP_COMPARISON_ADAPTER,
    )
    fail_reasons = build_bgp_fail_reasons(diff)

    before_duplicates = [
        BgpSnapshotDuplicateSession(
            device=item.key.device,
            neighbor=item.key.neighbor,
            count=item.count,
            states=item.states,
        )
        for item in diff.before_duplicates
    ]
    after_duplicates = [
        BgpSnapshotDuplicateSession(
            device=item.key.device,
            neighbor=item.key.neighbor,
            count=item.count,
            states=item.states,
        )
        for item in diff.after_duplicates
    ]

    return BgpSnapshotComparison(
        mw_id=before.mw_id,
        device=before.device,
        before_stage=before.stage,
        after_stage=after.stage,
        result="FAIL" if fail_reasons else "PASS",
        before_count=diff.before_count,
        after_count=diff.after_count,
        before_unique_count=diff.before_unique_count,
        after_unique_count=diff.after_unique_count,
        common_count=diff.common_count,
        before_duplicate_count=duplicate_count(
            diff.before_duplicates
        ),
        after_duplicate_count=duplicate_count(
            diff.after_duplicates
        ),
        before_duplicates=before_duplicates,
        after_duplicates=after_duplicates,
        lost_sessions=diff.lost_items,
        new_sessions=diff.new_items,
        state_changes=[
            BgpSnapshotStateChange(
                device=item.key.device,
                neighbor=item.key.neighbor,
                before_state=item.before_state,
                after_state=item.after_state,
            )
            for item in diff.state_changes
        ],
        before_unhealthy=diff.before_unhealthy,
        after_unhealthy=diff.after_unhealthy,
        new_unhealthy=diff.new_unhealthy,
        resolved_unhealthy=diff.resolved_unhealthy,
        persistent_unhealthy=diff.persistent_unhealthy,
        fail_reasons=fail_reasons,
    )


def compare_bgp_snapshot_files(
    snapshot_root: Path,
    mw_id: str,
    before_stage: str,
    after_stage: str,
    device: str,
) -> tuple[BgpSnapshotComparison, BgpSnapshot, BgpSnapshot]:
    """Load and compare existing BGP snapshot files without connecting."""
    before = load_bgp_snapshot(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=before_stage,
        device=device,
    )
    after = load_bgp_snapshot(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=after_stage,
        device=device,
    )

    validate_snapshot_pair(
        before,
        after,
        expected_mw_id=mw_id,
        expected_device=device,
        expected_before_stage=before_stage,
        expected_after_stage=after_stage,
    )
    comparison = compare_bgp_snapshots(before, after)

    return comparison, before, after
