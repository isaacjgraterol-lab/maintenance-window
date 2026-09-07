from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from maintenance_window.engine.snapshots.contracts import (
    SnapshotAdapter,
)
from maintenance_window.engine.snapshots.paths import build_snapshot_path
from maintenance_window.engine.snapshots.payload import (
    build_snapshot_payload,
)


ItemT = TypeVar("ItemT")


def write_snapshot(
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
    source_requested: str,
    source_actual: str,
    raw_file: Path | None,
    items: list[ItemT],
    adapter: SnapshotAdapter[ItemT],
) -> Path:
    """Write one normalized protocol snapshot to disk."""
    snapshot_path = build_snapshot_path(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
    )
    snapshot_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = build_snapshot_payload(
        mw_id=mw_id,
        stage=stage,
        device=device,
        source_requested=source_requested,
        source_actual=source_actual,
        raw_file=raw_file,
        items=items,
        created_at_utc=datetime.now(
            timezone.utc
        ).isoformat(),
        adapter=adapter,
    )

    snapshot_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return snapshot_path
