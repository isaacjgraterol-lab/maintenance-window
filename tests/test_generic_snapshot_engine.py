from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from maintenance_window.engine.snapshots.contracts import (
    SnapshotAdapter,
)
from maintenance_window.engine.snapshots.paths import (
    build_snapshot_path,
)
from maintenance_window.engine.snapshots.payload import (
    build_snapshot_payload,
)
from maintenance_window.engine.snapshots.reader import load_snapshot
from maintenance_window.engine.snapshots.writer import write_snapshot


@dataclass(frozen=True)
class ExampleItem:
    device: str
    name: str
    state: str


def _serialize(item: ExampleItem) -> dict[str, str]:
    return {
        "device": item.device,
        "name": item.name,
        "state": item.state,
    }


def _deserialize(
    data: dict[str, object],
    fallback_device: str,
) -> ExampleItem:
    return ExampleItem(
        device=str(data.get("device", fallback_device)),
        name=str(data["name"]),
        state=str(data["state"]),
    )


EXAMPLE_ADAPTER = SnapshotAdapter[ExampleItem](
    protocol="example",
    items_field="items",
    serialize_item=_serialize,
    deserialize_item=_deserialize,
    build_summary=lambda items: {
        "total_items": len(items),
    },
    build_details=lambda items: {
        "unhealthy_items": sum(
            item.state != "up"
            for item in items
        ),
    },
)


def test_generic_snapshot_path_is_windows_safe(
    tmp_path: Path,
) -> None:
    assert build_snapshot_path(
        snapshot_root=tmp_path,
        mw_id="MW:01",
        stage=" BEFORE ",
        device="router/one",
    ) == (
        tmp_path
        / "MW_01"
        / "before"
        / "router_one.json"
    )


def test_generic_payload_preserves_common_and_protocol_fields() -> None:
    items = [
        ExampleItem("router-a", "peer-a", "up"),
        ExampleItem("router-a", "peer-b", "down"),
    ]

    result = build_snapshot_payload(
        mw_id="MW-001",
        stage="before",
        device="router-a",
        source_requested="auto",
        source_actual="ssh",
        raw_file=Path("raw/router-a.json"),
        items=items,
        created_at_utc="2026-06-26T12:00:00+00:00",
        adapter=EXAMPLE_ADAPTER,
    )

    assert result["protocol"] == "example"
    assert result["summary"] == {
        "total_items": 2,
    }
    assert result["unhealthy_items"] == 1
    assert result["items"][1]["state"] == "down"


def test_generic_payload_rejects_reserved_detail_keys() -> None:
    bad_adapter = SnapshotAdapter[ExampleItem](
        protocol="example",
        items_field="items",
        serialize_item=_serialize,
        deserialize_item=_deserialize,
        build_summary=lambda items: {},
        build_details=lambda items: {
            "protocol": "collision",
        },
    )

    with pytest.raises(ValueError, match="reserved keys"):
        build_snapshot_payload(
            mw_id="MW-001",
            stage="before",
            device="router-a",
            source_requested="auto",
            source_actual="ssh",
            raw_file=None,
            items=[],
            created_at_utc="2026-06-26T12:00:00+00:00",
            adapter=bad_adapter,
        )


def test_generic_snapshot_round_trip(
    tmp_path: Path,
) -> None:
    items = [
        ExampleItem("router-a", "peer-a", "up"),
        ExampleItem("router-a", "peer-b", "down"),
    ]

    path = write_snapshot(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
        source_requested="auto",
        source_actual="ssh",
        raw_file=Path("raw/router-a.json"),
        items=items,
        adapter=EXAMPLE_ADAPTER,
    )
    loaded = load_snapshot(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
        adapter=EXAMPLE_ADAPTER,
    )

    assert path.exists()
    assert loaded.protocol == "example"
    assert loaded.items == items
    assert loaded.source_requested == "auto"
    assert loaded.source_actual == "ssh"
    assert loaded.path == path


def test_generic_snapshot_reader_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="EXAMPLE snapshot not found",
    ):
        load_snapshot(
            snapshot_root=tmp_path,
            mw_id="MW-404",
            stage="before",
            device="router-a",
            adapter=EXAMPLE_ADAPTER,
        )


def test_generic_snapshot_reader_rejects_protocol_mismatch(
    tmp_path: Path,
) -> None:
    path = build_snapshot_path(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "protocol": "other",
                "items": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="protocol mismatch",
    ):
        load_snapshot(
            snapshot_root=tmp_path,
            mw_id="MW-001",
            stage="before",
            device="router-a",
            adapter=EXAMPLE_ADAPTER,
        )


def test_generic_snapshot_reader_accepts_legacy_missing_protocol(
    tmp_path: Path,
) -> None:
    path = build_snapshot_path(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "device": "payload-router",
                "items": [
                    {
                        "name": "peer-a",
                        "state": "up",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_snapshot(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
        adapter=EXAMPLE_ADAPTER,
    )

    assert loaded.protocol == "example"
    assert loaded.device == "payload-router"
    assert loaded.items[0].device == "payload-router"
