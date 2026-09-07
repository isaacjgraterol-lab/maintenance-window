from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from maintenance_window.engine.snapshots.contracts import (
    SnapshotAdapter,
)


ItemT = TypeVar("ItemT")


_RESERVED_PAYLOAD_KEYS = {
    "protocol",
    "mw_id",
    "stage",
    "device",
    "source_requested",
    "source_actual",
    "raw_file",
    "created_at_utc",
    "summary",
}


def build_snapshot_payload(
    *,
    mw_id: str,
    stage: str,
    device: str,
    source_requested: str,
    source_actual: str,
    raw_file: Path | None,
    items: list[ItemT],
    created_at_utc: str,
    adapter: SnapshotAdapter[ItemT],
) -> dict[str, Any]:
    """Build one normalized protocol snapshot payload."""
    details = adapter.build_details(items)
    protected_keys = _RESERVED_PAYLOAD_KEYS | {
        adapter.items_field,
    }
    collisions = protected_keys & set(details)

    if collisions:
        names = ", ".join(sorted(collisions))
        raise ValueError(
            "Snapshot adapter details use reserved keys: "
            f"{names}."
        )

    payload: dict[str, Any] = {
        "protocol": adapter.protocol,
        "mw_id": mw_id,
        "stage": stage,
        "device": device,
        "source_requested": source_requested,
        "source_actual": source_actual,
        "raw_file": (
            str(raw_file)
            if raw_file is not None
            else None
        ),
        "created_at_utc": created_at_utc,
        "summary": adapter.build_summary(items),
    }
    payload.update(details)
    payload[adapter.items_field] = [
        adapter.serialize_item(item)
        for item in items
    ]

    return payload
