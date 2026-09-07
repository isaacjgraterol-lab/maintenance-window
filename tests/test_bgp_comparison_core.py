from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.protocols.bgp.snapshot_comparison import comparison
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
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


def _snapshot(
    *,
    stage: str,
    sessions: list[BgpSession],
    mw_id: str = "MW-001",
    device: str = "router-a",
) -> BgpSnapshot:
    return BgpSnapshot(
        mw_id=mw_id,
        stage=stage,
        device=device,
        source_requested="auto",
        source_actual="ssh",
        raw_file=None,
        created_at_utc="2026-06-26T12:00:00+00:00",
        sessions=sessions,
        path=Path(f"{stage}.json"),
    )


def test_identical_bgp_snapshots_pass() -> None:
    sessions = [_session("192.0.2.1")]

    result = comparison.compare_bgp_snapshots(
        _snapshot(stage="before", sessions=sessions),
        _snapshot(stage="after", sessions=sessions),
    )

    assert result.result == "PASS"
    assert result.fail_reasons == []
    assert result.state_changes == []


def test_lost_bgp_session_fails() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(
            stage="before",
            sessions=[_session("192.0.2.1")],
        ),
        _snapshot(stage="after", sessions=[]),
    )

    assert result.result == "FAIL"
    assert result.fail_reasons == ["lost_sessions"]
    assert [
        item.neighbor
        for item in result.lost_sessions
    ] == ["192.0.2.1"]


def test_new_established_session_is_informational() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(stage="before", sessions=[]),
        _snapshot(
            stage="after",
            sessions=[_session("192.0.2.1")],
        ),
    )

    assert result.result == "PASS"
    assert result.new_unhealthy == []
    assert len(result.new_sessions) == 1


def test_new_unhealthy_session_fails() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(stage="before", sessions=[]),
        _snapshot(
            stage="after",
            sessions=[_session("192.0.2.1", "Idle")],
        ),
    )

    assert result.result == "FAIL"
    assert result.fail_reasons == [
        "new_unhealthy_sessions",
    ]


def test_established_to_idle_fails() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(
            stage="before",
            sessions=[_session("192.0.2.1")],
        ),
        _snapshot(
            stage="after",
            sessions=[_session("192.0.2.1", "Idle")],
        ),
    )

    assert result.result == "FAIL"
    assert result.fail_reasons == [
        "new_unhealthy_sessions",
    ]
    assert result.state_changes[0].before_state == "Established"
    assert result.state_changes[0].after_state == "Idle"


def test_idle_to_established_is_recovery() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(
            stage="before",
            sessions=[_session("192.0.2.1", "Idle")],
        ),
        _snapshot(
            stage="after",
            sessions=[_session("192.0.2.1")],
        ),
    )

    assert result.result == "PASS"
    assert len(result.resolved_unhealthy) == 1
    assert result.new_unhealthy == []


def test_persistent_unhealthy_session_does_not_create_new_failure() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(
            stage="before",
            sessions=[_session("192.0.2.1", "Idle")],
        ),
        _snapshot(
            stage="after",
            sessions=[_session("192.0.2.1", "Active")],
        ),
    )

    assert result.result == "PASS"
    assert len(result.persistent_unhealthy) == 1
    assert result.new_unhealthy == []


def test_bgp_duplicate_counts_are_preserved() -> None:
    result = comparison.compare_bgp_snapshots(
        _snapshot(
            stage="before",
            sessions=[
                _session("192.0.2.1"),
                _session("192.0.2.1", "Idle"),
            ],
        ),
        _snapshot(
            stage="after",
            sessions=[
                _session("192.0.2.1"),
                _session("192.0.2.1"),
            ],
        ),
    )

    assert result.before_duplicate_count == 1
    assert result.after_duplicate_count == 1
    assert result.before_duplicates[0].states == [
        "Established",
        "Idle",
    ]


def test_bgp_comparison_rejects_mw_id_mismatch() -> None:
    with pytest.raises(ValueError, match="MW ID mismatch"):
        comparison.compare_bgp_snapshots(
            _snapshot(
                stage="before",
                sessions=[],
                mw_id="MW-001",
            ),
            _snapshot(
                stage="after",
                sessions=[],
                mw_id="MW-002",
            ),
        )


def test_bgp_comparison_rejects_device_mismatch() -> None:
    with pytest.raises(ValueError, match="device mismatch"):
        comparison.compare_bgp_snapshots(
            _snapshot(
                stage="before",
                sessions=[],
                device="router-a",
            ),
            _snapshot(
                stage="after",
                sessions=[],
                device="router-b",
            ),
        )


def test_bgp_file_comparison_only_loads_existing_snapshots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    before = _snapshot(
        stage="before",
        sessions=[_session("192.0.2.1")],
    )
    after = _snapshot(
        stage="after",
        sessions=[_session("192.0.2.1")],
    )
    calls: list[tuple[str, str]] = []

    def fake_load_bgp_snapshot(
        snapshot_root: Path,
        mw_id: str,
        stage: str,
        device: str,
    ) -> BgpSnapshot:
        del snapshot_root, mw_id
        calls.append((stage, device))
        return before if stage == "before" else after

    monkeypatch.setattr(
        comparison,
        "load_bgp_snapshot",
        fake_load_bgp_snapshot,
    )

    result, loaded_before, loaded_after = (
        comparison.compare_bgp_snapshot_files(
            snapshot_root=tmp_path,
            mw_id="MW-001",
            before_stage="before",
            after_stage="after",
            device="router-a",
        )
    )

    assert calls == [
        ("before", "router-a"),
        ("after", "router-a"),
    ]
    assert result.result == "PASS"
    assert loaded_before is before
    assert loaded_after is after
