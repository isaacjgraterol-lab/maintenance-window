from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintenance_window.protocols.bgp.parsers.gnmic_json import parse_gnmic_json
from maintenance_window.protocols.bgp.session_health.extractors import (
    extract_gnmic_json_records,
)
from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpSessionHealthRecord,
)
from maintenance_window.protocols.bgp.session_health.rules import (
    evaluate_family_health_for_peer,
)
from maintenance_window.protocols.bgp.snapshot_comparison.comparison import (
    compare_bgp_snapshots,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
)
from maintenance_window.protocols.bgp.source_guard import (
    normalize_source_name,
    validate_same_actual_source,
)
from maintenance_window.protocols.bgp.state.models import BgpSession


def _notification(
    neighbor: str,
    updates: list[tuple[str, object]],
    *,
    timestamp: int = 1_800_000_210_000_000_000,
    target: str = "PE01",
    afi_safi: str | None = None,
) -> dict[str, object]:
    prefix_elements: list[dict[str, object]] = [
        {"name": "network-instances"},
        {"name": "network-instance", "key": {"name": "DEFAULT"}},
        {"name": "protocols"},
        {"name": "protocol", "key": {"identifier": "BGP", "name": "DEFAULT"}},
        {"name": "bgp"},
        {"name": "neighbors"},
        {"name": "neighbor", "key": {"neighbor-address": neighbor}},
    ]
    if afi_safi is not None:
        prefix_elements.extend(
            [
                {"name": "afi-safis"},
                {"name": "afi-safi", "key": {"afi-safi-name": afi_safi}},
            ]
        )

    encoded_updates: list[dict[str, object]] = []
    for leaf, value in updates:
        if isinstance(value, bool):
            typed_value = {"boolVal": value}
        elif isinstance(value, int):
            typed_value = {"uintVal": value}
        else:
            typed_value = {"stringVal": str(value)}
        encoded_updates.append(
            {
                "path": {
                    "elem": [
                        {"name": "state"},
                        {"name": leaf},
                    ]
                },
                "val": typed_value,
            }
        )

    return {
        "update": {
            "timestamp": str(timestamp),
            "prefix": {
                "target": target,
                "elem": prefix_elements,
            },
            "update": encoded_updates,
        }
    }


def test_state_parser_uses_only_explicit_session_state_leaf(tmp_path: Path) -> None:
    raw_file = tmp_path / "gnmic.json"
    raw_file.write_text(
        json.dumps(
            [
                _notification(
                    "192.0.2.1",
                    [
                        ("session-state", "ESTABLISHED"),
                        ("peer-as", 64513),
                        ("last-established", 1_800_000_000_000_000_000),
                        ("established-transitions", 7),
                        ("enabled", True),
                        ("peer-type", "EXTERNAL"),
                        ("supported-capability", "RUNNING"),
                        ("group", "START"),
                    ],
                ),
                _notification(
                    "192.0.2.2",
                    [
                        ("session-state", "CONNECT"),
                        ("peer-as", 64512),
                    ],
                ),
            ]
        ),
        encoding="utf-8",
    )

    sessions = parse_gnmic_json(raw_file)

    assert [(item.neighbor, item.state) for item in sessions] == [
        ("192.0.2.1", "Established"),
        ("192.0.2.2", "Connect"),
    ]
    assert all(item.state not in {"RUNNING", "START", "64513", "64512"} for item in sessions)


def test_normalized_json_preserves_device_and_supports_fallback(tmp_path: Path) -> None:
    raw_file = tmp_path / "normalized.json"
    raw_file.write_text(
        json.dumps(
            [
                {
                    "device": "PE01",
                    "neighbor": "192.0.2.1",
                    "state": "Established",
                },
                {
                    "neighbor": "192.0.2.2",
                    "peer_state": "Active",
                },
            ]
        ),
        encoding="utf-8",
    )

    sessions = parse_gnmic_json(raw_file, fallback_device="file-input")

    assert sessions[0].device == "PE01"
    assert sessions[1].device == "file-input"
    assert sessions[1].state == "Active"


def test_health_extractor_groups_neighbor_and_derives_uptime(tmp_path: Path) -> None:
    notification_timestamp = 1_800_000_210_000_000_000
    last_established = 1_800_000_000_000_000_000
    raw_file = tmp_path / "gnmic.json"
    raw_file.write_text(
        json.dumps(
            [
                _notification(
                    "192.0.2.1",
                    [
                        ("session-state", "ESTABLISHED"),
                        ("peer-as", 64513),
                        ("last-established", last_established),
                        ("established-transitions", 7),
                        ("enabled", True),
                        ("peer-type", "EXTERNAL"),
                    ],
                    timestamp=notification_timestamp,
                ),
                _notification(
                    "192.0.2.1",
                    [
                        ("received-prefixes", 20),
                        ("accepted-prefixes", 19),
                        ("active-prefixes", 18),
                        ("sent-prefixes", 17),
                    ],
                    timestamp=notification_timestamp,
                    afi_safi="IPV4_UNICAST",
                ),
            ]
        ),
        encoding="utf-8",
    )

    records = extract_gnmic_json_records(
        raw_file,
        device_name="PE01",
        source="gnmic",
    )

    assert len(records) == 1
    record = records[0]
    assert record.device == "PE01"
    assert record.neighbor == "192.0.2.1"
    assert record.peer_state == "Established"
    assert record.peer_as == 64513
    assert record.flap_count == 7
    assert record.enabled is True
    assert record.peer_type == "EXTERNAL"
    assert record.last_established_ns == last_established
    assert record.elapsed_time_seconds == 210
    assert record.elapsed_time_raw == "210s"
    assert record.received_prefix_count == 20
    assert record.accepted_prefix_count == 19
    assert record.active_prefix_count == 18
    assert record.advertised_prefix_count == 17
    assert len(record.families) == 1


def test_partial_gnmi_family_coverage_is_not_evaluated() -> None:
    family = BgpFamilyHealthCounters(
        table="IPV4_UNICAST",
        family="ipv4-unicast",
        received_prefix_count=20,
    )
    before = BgpSessionHealthRecord(
        device="PE01",
        neighbor="192.0.2.1",
        peer_state="Established",
        source="gnmic",
        families=[family],
    )
    after = BgpSessionHealthRecord(
        device="PE01",
        neighbor="192.0.2.1",
        peer_state="Established",
        source="gnmic",
        families=[],
    )

    results = evaluate_family_health_for_peer(
        before,
        after,
        device="PE01",
        neighbor="192.0.2.1",
    )

    assert len(results) == 1
    assert results[0].result == "NOT_EVALUATED"
    assert results[0].findings[0].rule == (
        "partial_health_family_counters_unavailable"
    )


def _snapshot(stage: str, source: str) -> BgpSnapshot:
    return BgpSnapshot(
        mw_id="MW-001",
        stage=stage,
        device="PE01",
        source_requested=source,
        source_actual=source,
        raw_file=None,
        created_at_utc="2026-07-27T10:00:00+00:00",
        sessions=[
            BgpSession(
                device="PE01",
                neighbor="192.0.2.1",
                state="Established",
            )
        ],
        path=Path(f"{stage}.json"),
    )


def test_source_guard_normalizes_gnmi_alias() -> None:
    assert normalize_source_name("gNMI") == "gnmic"
    validate_same_actual_source("gnmi", "gnmic")


def test_official_state_comparison_rejects_cross_source() -> None:
    with pytest.raises(ValueError, match="same source_actual"):
        compare_bgp_snapshots(
            _snapshot("before", "pyez"),
            _snapshot("after", "gnmic"),
        )



def test_official_session_health_comparison_rejects_cross_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from maintenance_window.protocols.bgp.session_health import comparison

    before = _snapshot("before", "pyez")
    after = _snapshot("after", "gnmic")

    def fake_load_bgp_snapshot(
        *,
        snapshot_root: Path,
        mw_id: str,
        stage: str,
        device: str,
    ) -> BgpSnapshot:
        del snapshot_root, mw_id, device
        return before if stage == "before" else after

    monkeypatch.setattr(
        comparison,
        "load_bgp_snapshot",
        fake_load_bgp_snapshot,
    )

    with pytest.raises(ValueError, match="same source_actual"):
        comparison.compare_session_health_snapshots(
            snapshot_root=tmp_path,
            mw_id="MW-001",
            before_stage="before",
            after_stage="after",
            device="PE01",
        )
