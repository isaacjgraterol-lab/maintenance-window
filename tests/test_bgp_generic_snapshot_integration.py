from __future__ import annotations

import json
from pathlib import Path

from maintenance_window.engine.snapshots import paths as generic_paths
from maintenance_window.protocols.bgp.snapshot_comparison import snapshots
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
)
from maintenance_window.protocols.bgp.snapshot_store import paths
from maintenance_window.protocols.bgp.snapshot_store import reader
from maintenance_window.protocols.bgp.snapshot_store import writer


def _session(
    neighbor: str,
    state: str = "Established",
) -> BgpSession:
    return BgpSession(
        device="router-a",
        neighbor=neighbor,
        state=state,
    )


def test_bgp_snapshot_paths_use_generic_path_engine() -> None:
    assert paths.build_snapshot_path is (
        generic_paths.build_snapshot_path
    )
    assert paths.safe_path_part is generic_paths.safe_path_part


def test_bgp_snapshot_public_contract_is_preserved() -> None:
    assert snapshots.write_bgp_snapshot is writer.write_bgp_snapshot
    assert snapshots.load_bgp_snapshot is reader.load_bgp_snapshot


def test_bgp_snapshot_round_trip_preserves_summary_and_model(
    tmp_path: Path,
) -> None:
    values = [
        _session("192.0.2.1"),
        _session("192.0.2.1", "Idle"),
        _session("192.0.2.2", "Active"),
    ]

    snapshot_path = snapshots.write_bgp_snapshot(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
        source_requested="pyez",
        source_actual="ssh",
        raw_file=Path("raw/router-a.json"),
        sessions=values,
    )
    loaded = snapshots.load_bgp_snapshot(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="before",
        device="router-a",
    )
    payload = json.loads(
        snapshot_path.read_text(
            encoding="utf-8"
        )
    )

    assert isinstance(loaded, BgpSnapshot)
    assert loaded.sessions == values
    assert payload["protocol"] == "bgp"
    assert payload["summary"] == {
        "total_sessions": 3,
        "unique_sessions": 2,
        "duplicate_entries": 1,
        "unhealthy_sessions": 2,
    }
    assert payload["duplicates"] == [
        {
            "device": "router-a",
            "neighbor": "192.0.2.1",
            "count": 2,
            "states": [
                "Established",
                "Idle",
            ],
        }
    ]
