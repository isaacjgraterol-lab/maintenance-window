from __future__ import annotations

import json

from maintenance_window.protocols.bgp.session_health.extractors import (
    extract_gnmic_json_records,
    extract_records_from_raw,
)
from maintenance_window.protocols.bgp.session_health.rules import (
    evaluate_session_health,
    result_from_findings,
)


def _gnmic_notification(neighbor: str, state: str) -> dict[str, object]:
    return {
        "update": {
            "timestamp": "1782950230667523582",
            "prefix": {
                "target": "198.51.100.5",
                "elem": [
                    {"name": "network-instances"},
                    {
                        "name": "network-instance",
                        "key": {"name": "DEFAULT"},
                    },
                    {"name": "protocols"},
                    {
                        "name": "protocol",
                        "key": {"identifier": "BGP", "name": "DEFAULT"},
                    },
                    {"name": "bgp"},
                    {"name": "neighbors"},
                    {
                        "name": "neighbor",
                        "key": {"neighbor-address": neighbor},
                    },
                ],
            },
            "update": [
                {
                    "path": {
                        "elem": [
                            {"name": "state"},
                            {"name": "session-state"},
                        ],
                    },
                    "val": {"stringVal": state},
                },
            ],
        },
    }


def test_extract_gnmic_json_records_maps_session_state_without_counters(tmp_path):
    raw_file = tmp_path / "gnmic.json"
    raw_file.write_text(
        json.dumps(
            [
                _gnmic_notification("198.51.100.1", "ACTIVE"),
                _gnmic_notification("198.51.100.4", "ESTABLISHED"),
            ],
        ),
        encoding="utf-8",
    )

    records = extract_gnmic_json_records(
        raw_file,
        device_name="198.51.100.5",
        source="gnmic",
    )

    by_neighbor = {record.neighbor: record for record in records}
    assert len(records) == 2
    assert by_neighbor["198.51.100.1"].peer_state == "Active"
    assert by_neighbor["198.51.100.1"].health == "CRITICAL"
    assert by_neighbor["198.51.100.4"].peer_state == "Established"
    assert by_neighbor["198.51.100.4"].health == "OK"
    assert by_neighbor["198.51.100.4"].source == "gnmic"
    assert by_neighbor["198.51.100.4"].flap_count is None
    assert by_neighbor["198.51.100.4"].received_prefix_count is None
    assert by_neighbor["198.51.100.4"].families == []


def test_extract_records_from_raw_uses_gnmic_adapter_when_source_is_gnmic(tmp_path):
    raw_file = tmp_path / "gnmic.json"
    raw_file.write_text(
        json.dumps([_gnmic_notification("203.0.113.44", "IDLE")]),
        encoding="utf-8",
    )

    records = extract_records_from_raw(
        raw_file,
        device_name="198.51.100.5",
        source="gnmic",
    )

    assert len(records) == 1
    assert records[0].neighbor == "203.0.113.44"
    assert records[0].peer_state == "Idle"
    assert records[0].source == "gnmic"


def test_gnmic_records_with_only_state_still_evaluate_as_pass_when_stable() -> None:
    raw_before = {
        "device": "198.51.100.5",
        "neighbor": "198.51.100.4",
        "state": "Established",
    }
    raw_after = {
        "device": "198.51.100.5",
        "neighbor": "198.51.100.4",
        "state": "Established",
    }
    before_file_payload = [raw_before]
    after_file_payload = [raw_after]

    # Use the extractor path to keep the test aligned with file-mode/gNMIc behavior.
    # gNMIc may not include counters, and that must not become NOT_EVALUATED.
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        before_file = Path(tmp) / "before.json"
        after_file = Path(tmp) / "after.json"
        before_file.write_text(json.dumps(before_file_payload), encoding="utf-8")
        after_file.write_text(json.dumps(after_file_payload), encoding="utf-8")
        before = extract_records_from_raw(
            before_file,
            device_name="198.51.100.5",
            source="gnmic",
        )[0]
        after = extract_records_from_raw(
            after_file,
            device_name="198.51.100.5",
            source="gnmic",
        )[0]

    findings = evaluate_session_health(before, after)

    assert findings == []
    assert result_from_findings(findings) == "PASS"


def _gnmic_leaf_notification(
    neighbor: str,
    leafs: dict[str, object],
    *,
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

    updates = []
    for leaf, value in leafs.items():
        updates.append(
            {
                "path": {"elem": [{"name": "state"}, {"name": leaf}]},
                "val": {"stringVal": str(value)} if isinstance(value, str) else {"uintVal": value},
            }
        )

    return {
        "update": {
            "timestamp": "1782950230667523582",
            "prefix": {
                "target": "198.51.100.5",
                "elem": prefix_elements,
            },
            "update": updates,
        },
    }


def test_extract_gnmic_json_records_maps_neighbor_and_afi_safi_health_fields(tmp_path):
    raw_file = tmp_path / "gnmic.json"
    raw_file.write_text(
        json.dumps(
            [
                _gnmic_leaf_notification(
                    "198.51.100.4",
                    {
                        "session-state": "ESTABLISHED",
                        "peer-as": 64513,
                        "established-transitions": 7,
                    },
                ),
                _gnmic_leaf_notification(
                    "198.51.100.4",
                    {
                        "received-prefixes": 20,
                        "accepted-prefixes": 19,
                        "active-prefixes": 18,
                        "sent-prefixes": 17,
                    },
                    afi_safi="IPV4_UNICAST",
                ),
            ]
        ),
        encoding="utf-8",
    )

    records = extract_gnmic_json_records(
        raw_file,
        device_name="198.51.100.5",
        source="gnmic",
    )

    assert len(records) == 1
    record = records[0]
    assert record.neighbor == "198.51.100.4"
    assert record.peer_state == "Established"
    assert record.peer_as == 64513
    assert record.flap_count == 7
    assert record.received_prefix_count == 20
    assert record.accepted_prefix_count == 19
    assert record.active_prefix_count == 18
    assert record.advertised_prefix_count == 17
    assert len(record.families) == 1
    assert record.families[0].table == "IPV4_UNICAST"
    assert record.families[0].family == "ipv4-unicast"
