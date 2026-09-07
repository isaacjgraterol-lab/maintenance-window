from __future__ import annotations

from pathlib import Path

from maintenance_window.engine.snapshots.writer import write_snapshot
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_adapter import (
    BGP_SNAPSHOT_ADAPTER,
)


def write_bgp_snapshot(
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
    source_requested: str,
    source_actual: str,
    raw_file: Path | None,
    sessions: list[BgpSession],
) -> Path:
    """Write one normalized BGP snapshot to disk."""
    return write_snapshot(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
        source_requested=source_requested,
        source_actual=source_actual,
        raw_file=raw_file,
        items=sessions,
        adapter=BGP_SNAPSHOT_ADAPTER,
    )
