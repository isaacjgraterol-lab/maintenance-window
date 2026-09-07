from __future__ import annotations

from pathlib import Path
from typing import Any

from maintenance_window.engine.snapshots.payload import (
    build_snapshot_payload as build_generic_snapshot_payload,
)
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_adapter import (
    BGP_SNAPSHOT_ADAPTER,
)


def build_snapshot_payload(
    *,
    mw_id: str,
    stage: str,
    device: str,
    source_requested: str,
    source_actual: str,
    raw_file: Path | None,
    sessions: list[BgpSession],
    created_at_utc: str,
) -> dict[str, Any]:
    """Build the normalized JSON payload for one BGP snapshot."""
    return build_generic_snapshot_payload(
        mw_id=mw_id,
        stage=stage,
        device=device,
        source_requested=source_requested,
        source_actual=source_actual,
        raw_file=raw_file,
        items=sessions,
        created_at_utc=created_at_utc,
        adapter=BGP_SNAPSHOT_ADAPTER,
    )
