from __future__ import annotations

import os
from pathlib import Path

from maintenance_window.ui.snapshot_store import discover_snapshot_mw_records


def _write_snapshot(path: Path, *, timestamp: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    os.utime(path, (timestamp, timestamp))


def test_discover_snapshot_store_returns_recent_ready_mws_first(tmp_path: Path) -> None:
    old_mw = "MW_OLD"
    new_mw = "MW_NEW"

    _write_snapshot(
        tmp_path / "outputs" / "snapshots" / "bgp" / old_mw / "before" / "198.51.100.5.json",
        timestamp=100,
    )
    _write_snapshot(
        tmp_path / "outputs" / "snapshots" / "bgp" / old_mw / "after" / "198.51.100.5.json",
        timestamp=100,
    )

    _write_snapshot(
        tmp_path / "outputs" / "snapshots" / "bgp" / new_mw / "before" / "198.51.100.6.json",
        timestamp=200,
    )
    _write_snapshot(
        tmp_path / "outputs" / "snapshots" / "bgp" / new_mw / "after" / "198.51.100.6.json",
        timestamp=200,
    )

    records = discover_snapshot_mw_records(tmp_path, protocol="bgp")

    assert [record.mw_id for record in records] == ["MW_NEW", "MW_OLD"]
    assert records[0].ready is True
    assert records[0].before_count == 1
    assert records[0].after_count == 1
    assert records[0].common_count == 1
    assert records[0].common_devices == ("198.51.100.6",)
    assert records[0].before_last_modified != "N/A"
    assert records[0].after_last_modified != "N/A"


def test_discover_snapshot_store_marks_missing_after_not_ready(tmp_path: Path) -> None:
    mw_id = "MW_MISSING_AFTER"

    _write_snapshot(
        tmp_path / "outputs" / "snapshots" / "bgp" / mw_id / "before" / "198.51.100.5.json",
        timestamp=100,
    )

    records = discover_snapshot_mw_records(tmp_path, protocol="bgp")

    assert len(records) == 1
    assert records[0].mw_id == mw_id
    assert records[0].ready is False
    assert records[0].reason == "Missing after snapshot"
    assert records[0].common_count == 0
