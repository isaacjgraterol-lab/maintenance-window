from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from maintenance_window.protocols.bgp.snapshot_comparison import snapshots
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_store import (
    paths,
    payload,
    reader,
    serialization,
    sessions,
    writer,
)


def _session(
    neighbor: str,
    state: str = "Established",
    device: str = "router-a",
) -> BgpSession:
    return BgpSession(
        device=device,
        neighbor=neighbor,
        state=state,
    )


def test_public_snapshots_module_is_small_facade() -> None:
    facade_path = Path(snapshots.__file__).resolve()

    assert len(
        facade_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ) < 40
    assert snapshots.write_bgp_snapshot is writer.write_bgp_snapshot
    assert snapshots.load_bgp_snapshot is reader.load_bgp_snapshot


def test_public_snapshot_function_signatures_are_preserved() -> None:
    write_parameters = list(
        inspect.signature(
            snapshots.write_bgp_snapshot
        ).parameters
    )
    load_parameters = list(
        inspect.signature(
            snapshots.load_bgp_snapshot
        ).parameters
    )

    assert write_parameters == [
        "snapshot_root",
        "mw_id",
        "stage",
        "device",
        "source_requested",
        "source_actual",
        "raw_file",
        "sessions",
    ]
    assert load_parameters == [
        "snapshot_root",
        "mw_id",
        "stage",
        "device",
    ]


def test_build_snapshot_path_sanitizes_windows_invalid_characters(
    tmp_path: Path,
) -> None:
    result = paths.build_snapshot_path(
        snapshot_root=tmp_path,
        mw_id='MW:01',
        stage='BEFORE',
        device='router/one',
    )

    assert result == (
        tmp_path
        / "MW_01"
        / "before"
        / "router_one.json"
    )


def test_health_helpers_are_case_insensitive() -> None:
    assert sessions.is_healthy_state(
        " established "
    )
    assert not sessions.is_unhealthy_session(
        _session("192.0.2.1", "ESTABLISHED")
    )
    assert sessions.is_unhealthy_session(
        _session("192.0.2.2", "Idle")
    )


def test_session_map_uses_last_duplicate_record() -> None:
    values = [
        _session("192.0.2.1", "Idle"),
        _session("192.0.2.1", "Established"),
    ]

    session_map = sessions.build_session_map(values)
    stored = next(iter(session_map.values()))

    assert len(session_map) == 1
    assert stored.state == "Established"


def test_duplicate_detection_is_sorted_and_counted() -> None:
    values = [
        _session("192.0.2.2", "Idle"),
        _session("192.0.2.1", "Established"),
        _session("192.0.2.2", "Connect"),
        _session("192.0.2.1", "Established"),
        _session("192.0.2.2", "Idle"),
    ]

    duplicates = sessions.find_duplicates(values)

    assert [
        item.neighbor
        for item in duplicates
    ] == [
        "192.0.2.1",
        "192.0.2.2",
    ]
    assert duplicates[1].count == 3
    assert duplicates[1].states == [
        "Connect",
        "Idle",
    ]
    assert sessions.duplicate_count(
        duplicates
    ) == 3


def test_snapshot_payload_preserves_summary_and_evidence() -> None:
    values = [
        _session("192.0.2.1"),
        _session("192.0.2.1", "Idle"),
        _session("192.0.2.2", "Active"),
    ]

    payload_data = payload.build_snapshot_payload(
        mw_id="MW-001",
        stage="before",
        device="router-a",
        source_requested="auto",
        source_actual="ssh",
        raw_file=Path("raw/router-a.json"),
        sessions=values,
        created_at_utc="2026-06-25T12:00:00+00:00",
    )

    assert payload_data["protocol"] == "bgp"
    assert payload_data["raw_file"] == str(Path("raw/router-a.json"))
    assert payload_data["summary"] == {
        "total_sessions": 3,
        "unique_sessions": 2,
        "duplicate_entries": 1,
        "unhealthy_sessions": 2,
    }
    assert payload_data["duplicates"] == [
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


def test_write_and_load_snapshot_round_trip(
    tmp_path: Path,
) -> None:
    values = [
        _session("192.0.2.1"),
        _session("192.0.2.2", "Idle"),
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

    assert snapshot_path.exists()
    assert payload["summary"]["total_sessions"] == 2
    assert loaded.mw_id == "MW-001"
    assert loaded.source_requested == "pyez"
    assert loaded.source_actual == "ssh"
    assert loaded.raw_file == str(Path("raw/router-a.json"))
    assert loaded.sessions == values
    assert loaded.path == snapshot_path


def test_load_snapshot_uses_snapshot_device_as_session_fallback(
    tmp_path: Path,
) -> None:
    snapshot_path = paths.build_snapshot_path(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="after",
        device="requested-name",
    )
    snapshot_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    snapshot_path.write_text(
        json.dumps(
            {
                "mw_id": "MW-001",
                "stage": "after",
                "device": "payload-device",
                "sessions": [
                    {
                        "neighbor": "192.0.2.1",
                        "state": "Established",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = reader.load_bgp_snapshot(
        snapshot_root=tmp_path,
        mw_id="MW-001",
        stage="after",
        device="requested-name",
    )

    assert loaded.device == "payload-device"
    assert loaded.sessions[0].device == "payload-device"
    assert loaded.source_requested == "unknown"
    assert loaded.source_actual == "unknown"


def test_load_snapshot_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="BGP snapshot not found",
    ):
        snapshots.load_bgp_snapshot(
            snapshot_root=tmp_path,
            mw_id="MW-404",
            stage="before",
            device="router-a",
        )
