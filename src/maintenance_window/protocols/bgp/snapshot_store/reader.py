from __future__ import annotations

from pathlib import Path

from maintenance_window.engine.snapshots.reader import load_snapshot
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_adapter import (
    BGP_SNAPSHOT_ADAPTER,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
)


def load_bgp_snapshot(
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
) -> BgpSnapshot:
    """Load one normalized BGP snapshot from disk."""
    stored_snapshot = load_snapshot(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
        adapter=BGP_SNAPSHOT_ADAPTER,
    )

    return BgpSnapshot(
        mw_id=stored_snapshot.mw_id,
        stage=stored_snapshot.stage,
        device=stored_snapshot.device,
        source_requested=stored_snapshot.source_requested,
        source_actual=stored_snapshot.source_actual,
        raw_file=stored_snapshot.raw_file,
        created_at_utc=stored_snapshot.created_at_utc,
        sessions=stored_snapshot.items,
        path=stored_snapshot.path,
    )
