from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.protocols.bgp.full_report.reports import (
    build_source_coverage,
)
from maintenance_window.protocols.bgp.session_health import comparison
from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpSessionHealthRecord,
)
from maintenance_window.protocols.bgp.session_health.reports import (
    session_health_to_dict,
)
from maintenance_window.protocols.bgp.session_health.rules import (
    evaluate_family_health,
)
from maintenance_window.protocols.bgp.snapshot_comparison.comparison import (
    compare_bgp_snapshots,
)
from maintenance_window.protocols.bgp.snapshot_comparison.reports import (
    snapshot_comparison_to_dict,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
)
from maintenance_window.protocols.bgp.state.models import BgpSession


def _snapshot(
    stage: str,
    *,
    source_requested: str = "gnmic",
    source_actual: str = "gnmic",
    state: str = "Established",
) -> BgpSnapshot:
    return BgpSnapshot(
        mw_id="MW-PUBLIC-001",
        stage=stage,
        device="router-a",
        source_requested=source_requested,
        source_actual=source_actual,
        raw_file=f"{stage}.json",
        created_at_utc="2026-07-29T00:00:00+00:00",
        sessions=[
            BgpSession(
                device="router-a",
                neighbor="192.0.2.1",
                state=state,
            )
        ],
        path=Path(f"{stage}.json"),
    )


def _state_only_record() -> BgpSessionHealthRecord:
    return BgpSessionHealthRecord(
        device="router-a",
        neighbor="192.0.2.1",
        peer_state="Established",
        source="gnmic",
    )


def test_state_only_gnmi_is_operational_pass_with_partial_coverage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    before_snapshot = _snapshot("before")
    after_snapshot = _snapshot("after")
    record = _state_only_record()

    def fake_load_bgp_snapshot(
        *,
        snapshot_root: Path,
        mw_id: str,
        stage: str,
        device: str,
    ) -> BgpSnapshot:
        del snapshot_root, mw_id, device
        return before_snapshot if stage == "before" else after_snapshot

    monkeypatch.setattr(comparison, "load_bgp_snapshot", fake_load_bgp_snapshot)
    monkeypatch.setattr(
        comparison,
        "_extract_snapshot_records",
        lambda snapshot: (Path(str(snapshot.raw_file)), [record]),
    )

    result = comparison.compare_session_health_snapshots(
        snapshot_root=tmp_path,
        mw_id="MW-PUBLIC-001",
        before_stage="before",
        after_stage="after",
        device="router-a",
    )

    assert result.result == "PASS"
    assert result.coverage == "PARTIAL"
    assert result.peers_partial == 1
    assert result.peers_not_evaluated == 0
    assert result.before_source_requested == "gnmic"
    assert result.before_source_actual == "gnmic"

    peer = result.peer_results[0]
    assert peer.result == "PASS"
    assert peer.coverage == "PARTIAL"
    assert set(peer.not_evaluated_checks) == {
        "peer_as",
        "uptime",
        "flap_count",
        "prefix_counters",
        "afi_safi_families",
    }

    payload = session_health_to_dict(result)
    assert payload["coverage"] == "PARTIAL"
    assert payload["peers_partial"] == 1
    assert payload["peers"][0]["coverage"] == "PARTIAL"
    assert "prefix_counters" in payload["peers"][0]["not_evaluated_checks"]


def test_source_coverage_reports_requested_source_and_fallback() -> None:
    reports = [
        {
            "device": "router-a",
            "result": "PASS",
            "before": {
                "source_requested": "gnmic",
                "source_actual": "gnmic",
            },
            "after": {
                "source_requested": "gnmic",
                "source_actual": "gnmic",
            },
        },
        {
            "device": "router-b",
            "result": "PASS",
            "before": {
                "source_requested": "gnmic",
                "source_actual": "ssh",
            },
            "after": {
                "source_requested": "gnmic",
                "source_actual": "ssh",
            },
        },
    ]

    coverage = build_source_coverage(reports)

    assert coverage["before_actual"] == {"gnmic": 1, "ssh": 1}
    assert coverage["after_actual"] == {"gnmic": 1, "ssh": 1}
    assert coverage["fallback_device_count"] == 1
    assert coverage["fallback_devices"] == [
        {
            "device": "router-b",
            "before": "gnmic->ssh",
            "after": "gnmic->ssh",
        }
    ]


def _family(value: int) -> BgpFamilyHealthCounters:
    return BgpFamilyHealthCounters(
        table="inet.0",
        family="ipv4-unicast",
        received_prefix_count=value,
    )


@pytest.mark.parametrize(
    ("before_value", "after_value", "expected"),
    [
        (1_000, 1_010, "PASS"),
        (1_000, 995, "PASS"),
        (1_000, 980, "WARNING"),
        (100, 75, "FAIL"),
        (100, 0, "FAIL"),
    ],
)
def test_prefix_policy_ignores_normal_churn_and_flags_meaningful_loss(
    before_value: int,
    after_value: int,
    expected: str,
) -> None:
    result = evaluate_family_health(
        device="router-a",
        neighbor="192.0.2.1",
        before=_family(before_value),
        after=_family(after_value),
    )

    assert result.result == expected
    if expected == "PASS":
        assert result.findings == []
    else:
        assert result.findings[0].rule == "prefix_delta"
        assert "decreased" in result.findings[0].message


def test_unhealthy_fsm_transition_is_counted_separately() -> None:
    before = _snapshot("before", source_requested="ssh", source_actual="ssh", state="Active")
    after = _snapshot("after", source_requested="ssh", source_actual="ssh", state="Connect")

    result = compare_bgp_snapshots(before, after)
    payload = snapshot_comparison_to_dict(result, before, after)

    assert result.result == "PASS"
    assert payload["state_changes_count"] == 1
    assert payload["unhealthy_fsm_transitions_count"] == 1
    assert payload["new_unhealthy_count"] == 0
    assert payload["unhealthy_fsm_transitions"][0] == {
        "device": "router-a",
        "neighbor": "192.0.2.1",
        "before_state": "Active",
        "after_state": "Connect",
    }
