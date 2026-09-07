from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from maintenance_window.engine.snapshots.contracts import (
    SnapshotAdapter,
)
from maintenance_window.engine.snapshots.models import StoredSnapshot
from maintenance_window.engine.snapshots.paths import build_snapshot_path


ItemT = TypeVar("ItemT")


def load_snapshot(
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
    adapter: SnapshotAdapter[ItemT],
) -> StoredSnapshot[ItemT]:
    """Load one normalized protocol snapshot from disk."""
    snapshot_path = build_snapshot_path(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
    )

    if not snapshot_path.exists():
        raise FileNotFoundError(
            f"{adapter.protocol.upper()} snapshot not found: "
            f"{snapshot_path}"
        )

    payload: Any = json.loads(
        snapshot_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "Snapshot JSON root must be an object: "
            f"{snapshot_path}"
        )

    payload_protocol = payload.get("protocol")

    if (
        payload_protocol is not None
        and str(payload_protocol).strip().lower()
        != adapter.protocol.strip().lower()
    ):
        raise ValueError(
            "Snapshot protocol mismatch: "
            f"{payload_protocol!r} != {adapter.protocol!r}."
        )

    snapshot_device = str(
        payload.get("device", device)
    )
    raw_items = payload.get(adapter.items_field, [])

    if not isinstance(raw_items, list):
        raise ValueError(
            "Snapshot items field must be a list: "
            f"{adapter.items_field!r}."
        )

    items: list[ItemT] = []

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError(
                "Each snapshot item must be a JSON object."
            )

        items.append(
            adapter.deserialize_item(
                raw_item,
                snapshot_device,
            )
        )

    return StoredSnapshot(
        protocol=adapter.protocol,
        mw_id=str(payload.get("mw_id", mw_id)),
        stage=str(payload.get("stage", stage)),
        device=snapshot_device,
        source_requested=str(
            payload.get(
                "source_requested",
                "unknown",
            )
        ),
        source_actual=str(
            payload.get(
                "source_actual",
                "unknown",
            )
        ),
        raw_file=payload.get("raw_file"),
        created_at_utc=str(
            payload.get("created_at_utc", "")
        ),
        items=items,
        path=snapshot_path,
    )
