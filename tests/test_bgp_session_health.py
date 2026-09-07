from __future__ import annotations

import json
from pathlib import Path

from maintenance_window.cli import build_parser
from maintenance_window.protocols.bgp.session_health.extractors import (
    extract_pyez_xml_records,
    extract_ssh_json_records,
    family_from_table,
)
from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpSessionHealthRecord,
)
from maintenance_window.protocols.bgp.session_health.reports import (
    format_session_health_detail,
)
from maintenance_window.protocols.bgp.session_health.rules import (
    evaluate_family_health_for_peer,
    evaluate_session_health,
    result_from_findings,
)


def test_parser_accepts_session_health_module() -> None:
    args = build_parser().parse_args([
        "--protocol",
        "bgp",
        "--module",
        "session-health",
        "--compare-snapshots",
        "before,after",
        "--mw-id",
        "MW_001",
        "--device",
        "all",
    ])

    assert args.module == "session-health"


def test_family_from_table_maps_known_tables_and_unknown() -> None:
    assert family_from_table("inet.0") == "ipv4-unicast"
    assert family_from_table("inet6.0") == "ipv6-unicast"
    assert family_from_table("inet.3") == "ipv4-labeled-unicast"
    assert family_from_table("inet6.3") == "ipv6-labeled-unicast"
    assert family_from_table("bgp.l3vpn.0") == "vpnv4-unicast"
    assert family_from_table("bgp.l3vpn-inet6.0") == "vpnv6-unicast"
    assert family_from_table("bgp.evpn.0") == "evpn"
    assert family_from_table("bgp.l2vpn.0") == "l2vpn-signaling"
    assert family_from_table("bgp.mvpn.0") == "mvpn"
    assert family_from_table("bgp.rtarget.0") == "route-target"
    assert family_from_table("bgp.inetsrte.0") == "ipv4-segment-routing-te"
    assert family_from_table("bgp.transport.3") == "bgp-ct / transport"
    assert family_from_table("lsdist.0") == "traffic-engineering / bgp-ls"
    assert family_from_table("inetflow.0") == "ipv4-flow"
    assert family_from_table("inet6flow.0") == "ipv6-flow"
    assert family_from_table("unknown.table.0") == "unknown"


def test_family_from_table_maps_instance_tables_by_suffix() -> None:
    assert family_from_table("VRF_TEST_135.inet.0") == "vrf-ipv4-unicast"
    assert family_from_table("vrf-Customer.inet6.0") == "vrf-ipv6-unicast"
    assert family_from_table("CUSTOMER_A.inet.3") == "vrf-ipv4-labeled-unicast"
    assert family_from_table("CUSTOMER_A.inet6.3") == "vrf-ipv6-labeled-unicast"
    assert family_from_table("evpn-NGH_TST_LT_MTY-510.evpn.0") == "evpn"
    assert family_from_table("__default_evpn__.evpn.0") == "evpn"


def test_pyez_xml_extractor_keeps_one_peer_with_multiple_families(tmp_path: Path) -> None:
    raw = tmp_path / "bgp.xml"
    raw.write_text(
        """
<bgp-information xmlns:junos="http://xml.juniper.net/junos">
  <bgp-peer>
    <peer-address>198.51.100.10+179</peer-address>
    <peer-as>64513</peer-as>
    <peer-state>Established</peer-state>
    <elapsed-time junos:seconds="1318">21:58</elapsed-time>
    <flap-count>253</flap-count>
    <bgp-rib>
      <name>inet.3</name>
      <bgp-rib-state>BGP restart is complete</bgp-rib-state>
      <send-state>in sync</send-state>
      <received-prefix-count>7</received-prefix-count>
      <accepted-prefix-count>5</accepted-prefix-count>
      <active-prefix-count>2</active-prefix-count>
      <suppressed-prefix-count>0</suppressed-prefix-count>
      <advertised-prefix-count>11</advertised-prefix-count>
    </bgp-rib>
    <bgp-rib>
      <name>inet.0</name>
      <bgp-rib-state>BGP restart is complete</bgp-rib-state>
      <send-state>in sync</send-state>
      <received-prefix-count>7</received-prefix-count>
      <accepted-prefix-count>5</accepted-prefix-count>
      <active-prefix-count>2</active-prefix-count>
      <suppressed-prefix-count>0</suppressed-prefix-count>
      <advertised-prefix-count>13</advertised-prefix-count>
    </bgp-rib>
    <bgp-rib>
      <name>bgp.transport.3</name>
      <bgp-rib-state>BGP restart is complete</bgp-rib-state>
      <send-state>in sync</send-state>
      <received-prefix-count>4</received-prefix-count>
      <accepted-prefix-count>4</accepted-prefix-count>
      <active-prefix-count>4</active-prefix-count>
      <suppressed-prefix-count>0</suppressed-prefix-count>
      <advertised-prefix-count>5</advertised-prefix-count>
    </bgp-rib>
  </bgp-peer>
</bgp-information>
""".strip(),
        encoding="utf-8",
    )

    records = extract_pyez_xml_records(raw, device_name="router-1", source="pyez")

    assert len(records) == 1
    record = records[0]
    assert record.neighbor == "198.51.100.10"
    assert record.peer_state == "Established"
    assert record.state == "Established"
    assert record.health == "OK"
    assert record.reason == "peer_established"
    assert record.peer_as == 64513
    assert record.remote_as == 64513
    assert record.elapsed_time_seconds == 1318
    assert record.flap_count == 253

    assert record.received_prefix_count == 18
    assert record.accepted_prefix_count == 14
    assert record.active_prefix_count == 8
    assert record.suppressed_prefix_count == 0
    assert record.advertised_prefix_count == 29

    assert len(record.families) == 3
    by_table = {family.table: family for family in record.families}
    assert by_table["inet.3"].family == "ipv4-labeled-unicast"
    assert by_table["inet.3"].received_prefix_count == 7
    assert by_table["inet.3"].advertised_prefix_count == 11
    assert by_table["inet.0"].family == "ipv4-unicast"
    assert by_table["inet.0"].advertised_prefix_count == 13
    assert by_table["bgp.transport.3"].family == "bgp-ct / transport"
    assert by_table["bgp.transport.3"].advertised_prefix_count == 5


def test_ssh_json_extractor_keeps_one_peer_with_multiple_families(tmp_path: Path) -> None:
    raw = tmp_path / "bgp.json"
    payload = {
        "bgp-information": [
            {
                "bgp-peer": [
                    {
                        "peer-address": [{"data": "198.51.100.10+179"}],
                        "peer-as": [{"data": "64513"}],
                        "peer-state": [{"data": "Establ"}],
                        "elapsed-time": [
                            {
                                "data": "00:22:05",
                                "attributes": {"junos:seconds": "1325"},
                            }
                        ],
                        "flap-count": [{"data": "253"}],
                        "bgp-rib": [
                            {
                                "name": [{"data": "inet.3"}],
                                "received-prefix-count": [{"data": "7"}],
                                "accepted-prefix-count": [{"data": "5"}],
                                "active-prefix-count": [{"data": "2"}],
                                "suppressed-prefix-count": [{"data": "0"}],
                                "advertised-prefix-count": [{"data": "11"}],
                            },
                            {
                                "name": [{"data": "inet.0"}],
                                "received-prefix-count": [{"data": "7"}],
                                "accepted-prefix-count": [{"data": "5"}],
                                "active-prefix-count": [{"data": "2"}],
                                "suppressed-prefix-count": [{"data": "0"}],
                                "advertised-prefix-count": [{"data": "13"}],
                            },
                            {
                                "name": [{"data": "bgp.transport.3"}],
                                "received-prefix-count": [{"data": "4"}],
                                "accepted-prefix-count": [{"data": "4"}],
                                "active-prefix-count": [{"data": "4"}],
                                "suppressed-prefix-count": [{"data": "0"}],
                                "advertised-prefix-count": [{"data": "5"}],
                            },
                        ],
                    }
                ]
            }
        ]
    }
    raw.write_text(json.dumps(payload), encoding="utf-8")

    records = extract_ssh_json_records(raw, device_name="router-2", source="ssh")

    assert len(records) == 1
    record = records[0]
    assert record.neighbor == "198.51.100.10"
    assert record.peer_state == "Established"
    assert record.elapsed_time_seconds == 1325
    assert record.received_prefix_count == 18
    assert record.accepted_prefix_count == 14
    assert record.active_prefix_count == 8
    assert record.advertised_prefix_count == 29
    assert len(record.families) == 3


def test_session_health_rules_detect_state_and_uptime_without_failing_prefix_deltas() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Established",
        elapsed_time_seconds=1000,
        flap_count=1,
        received_prefix_count=100,
        accepted_prefix_count=100,
        active_prefix_count=80,
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Established",
        elapsed_time_seconds=100,
        flap_count=2,
        received_prefix_count=60,
        accepted_prefix_count=60,
        active_prefix_count=60,
    )

    findings = evaluate_session_health(before, after)

    rules = {finding.rule for finding in findings}
    assert "flap_count_increased" in rules
    assert "uptime_reset" in rules
    assert result_from_findings(findings) == "WARNING"


def test_family_health_detects_prefix_delta_by_device_neighbor_table() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="198.51.100.10",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.3",
                family="ipv4-labeled-unicast",
                received_prefix_count=7,
                accepted_prefix_count=5,
                active_prefix_count=2,
                advertised_prefix_count=11,
            ),
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=7,
                accepted_prefix_count=5,
                active_prefix_count=2,
                advertised_prefix_count=13,
            ),
        ],
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="198.51.100.10",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.3",
                family="ipv4-labeled-unicast",
                received_prefix_count=7,
                accepted_prefix_count=5,
                active_prefix_count=2,
                advertised_prefix_count=11,
            ),
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=6,
                accepted_prefix_count=4,
                active_prefix_count=1,
                advertised_prefix_count=12,
            ),
            BgpFamilyHealthCounters(
                table="bgp.transport.3",
                family="bgp-ct / transport",
                received_prefix_count=4,
                accepted_prefix_count=4,
                active_prefix_count=4,
                advertised_prefix_count=5,
            ),
        ],
    )

    family_results = evaluate_family_health_for_peer(
        before,
        after,
        device="router-1",
        neighbor="198.51.100.10",
    )

    by_table = {item.table: item for item in family_results}
    assert by_table["inet.3"].result == "PASS"
    assert by_table["inet.0"].result == "WARNING"
    assert any(
        finding.rule == "prefix_delta"
        and finding.table == "inet.0"
        for finding in by_table["inet.0"].findings
    )
    assert by_table["bgp.transport.3"].result == "WARNING"
    assert any(
        finding.rule == "new_family_after"
        for finding in by_table["bgp.transport.3"].findings
    )


def test_session_health_rules_keep_persistent_unhealthy_as_unhealthy() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.10",
        peer_state="Idle",
        elapsed_time_seconds=1000,
        flap_count=1,
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.10",
        peer_state="Idle",
        elapsed_time_seconds=1100,
        flap_count=1,
    )

    findings = evaluate_session_health(before, after)

    assert result_from_findings(findings) == "UNHEALTHY"
    assert any(
        finding.rule == "persistent_unhealthy_peer"
        for finding in findings
    )


def test_session_health_rules_fail_when_established_peer_goes_down() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.11",
        peer_state="Established",
        elapsed_time_seconds=1000,
        flap_count=1,
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.11",
        peer_state="Idle",
        elapsed_time_seconds=100,
        flap_count=1,
    )

    findings = evaluate_session_health(before, after)

    assert result_from_findings(findings) == "FAIL"
    assert any(finding.rule == "session_down" for finding in findings)
    assert any(finding.rule == "health_changed" for finding in findings)


def test_session_health_detail_reports_family_table_details() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="198.51.100.10",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.3",
                family="ipv4-labeled-unicast",
                received_prefix_count=7,
                accepted_prefix_count=5,
                active_prefix_count=2,
            )
        ],
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="198.51.100.10",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.3",
                family="ipv4-labeled-unicast",
                received_prefix_count=7,
                accepted_prefix_count=5,
                active_prefix_count=2,
            )
        ],
    )
    from maintenance_window.protocols.bgp.session_health.models import (
        BgpSessionHealthComparison,
        BgpSessionHealthResult,
    )

    comparison = BgpSessionHealthComparison(
        mw_id="MW_001",
        device="router-1",
        before_stage="before",
        after_stage="after",
        result="PASS",
        before_raw_file=None,
        after_raw_file=None,
        peer_results=[
            BgpSessionHealthResult(
                device="router-1",
                neighbor="198.51.100.10",
                result="PASS",
                before=before,
                after=after,
                family_results=evaluate_family_health_for_peer(
                    before,
                    after,
                    device="router-1",
                    neighbor="198.51.100.10",
                ),
            )
        ],
    )

    detail = format_session_health_detail(comparison)

    assert "Family/Table Details" in detail
    assert "Table: inet.3" in detail
    assert "Family: ipv4-labeled-unicast" in detail


def test_bgp_uptime_parser_fallback_when_seconds_attribute_is_missing(tmp_path: Path) -> None:
    from maintenance_window.protocols.bgp.session_health.uptime import (
        parse_bgp_uptime_to_seconds,
    )

    assert parse_bgp_uptime_to_seconds("3d 04:10:22") == 3 * 86400 + 4 * 3600 + 10 * 60 + 22
    assert parse_bgp_uptime_to_seconds("2w3d") == 17 * 86400
    assert parse_bgp_uptime_to_seconds("00:02:14") == 134
    assert parse_bgp_uptime_to_seconds("21:58") == 1318

    raw = tmp_path / "bgp.xml"
    raw.write_text(
        """
<bgp-information>
  <bgp-peer>
    <peer-address>198.51.100.10+179</peer-address>
    <peer-as>64513</peer-as>
    <peer-state>Established</peer-state>
    <elapsed-time>3d 04:10:22</elapsed-time>
  </bgp-peer>
</bgp-information>
""".strip(),
        encoding="utf-8",
    )

    records = extract_pyez_xml_records(raw, device_name="router-1", source="pyez")

    assert records[0].elapsed_time_raw == "3d 04:10:22"
    assert records[0].elapsed_time_seconds == 3 * 86400 + 4 * 3600 + 10 * 60 + 22


def test_pyez_xml_extractor_preserves_multiple_rib_states_per_family(tmp_path: Path) -> None:
    raw = tmp_path / "bgp.xml"
    raw.write_text(
        """
<bgp-information>
  <bgp-peer>
    <peer-address>198.51.100.10+179</peer-address>
    <peer-as>64513</peer-as>
    <peer-state>Established</peer-state>
    <bgp-rib>
      <name>bgp.transport.3</name>
      <bgp-rib-state>BGP restart is complete</bgp-rib-state>
      <bgp-rib-state>VPN restart is complete</bgp-rib-state>
      <send-state>in sync</send-state>
      <received-prefix-count>4</received-prefix-count>
      <accepted-prefix-count>4</accepted-prefix-count>
      <active-prefix-count>4</active-prefix-count>
      <suppressed-prefix-count>0</suppressed-prefix-count>
      <advertised-prefix-count>5</advertised-prefix-count>
    </bgp-rib>
  </bgp-peer>
</bgp-information>
""".strip(),
        encoding="utf-8",
    )

    records = extract_pyez_xml_records(raw, device_name="router-1", source="pyez")

    family = records[0].families[0]
    assert family.table == "bgp.transport.3"
    assert family.family == "bgp-ct / transport"
    assert family.rib_state == [
        "BGP restart is complete",
        "VPN restart is complete",
    ]
    assert family.advertised_prefix_count == 5


def test_ssh_json_extractor_preserves_multiple_rib_states_per_family(tmp_path: Path) -> None:
    raw = tmp_path / "bgp.json"
    payload = {
        "bgp-information": [
            {
                "bgp-peer": [
                    {
                        "peer-address": [{"data": "198.51.100.10+179"}],
                        "peer-as": [{"data": "64513"}],
                        "peer-state": [{"data": "Established"}],
                        "elapsed-time": [{"data": "00:02:14"}],
                        "bgp-rib": [
                            {
                                "name": [{"data": "bgp.transport.3"}],
                                "bgp-rib-state": [
                                    {"data": "BGP restart is complete"},
                                    {"data": "VPN restart is complete"},
                                ],
                                "send-state": [{"data": "in sync"}],
                                "received-prefix-count": [{"data": "4"}],
                                "accepted-prefix-count": [{"data": "4"}],
                                "active-prefix-count": [{"data": "4"}],
                                "suppressed-prefix-count": [{"data": "0"}],
                                "advertised-prefix-count": [{"data": "5"}],
                            }
                        ],
                    }
                ]
            }
        ]
    }
    raw.write_text(json.dumps(payload), encoding="utf-8")

    records = extract_ssh_json_records(raw, device_name="router-2", source="ssh")

    assert records[0].elapsed_time_seconds == 134
    family = records[0].families[0]
    assert family.rib_state == [
        "BGP restart is complete",
        "VPN restart is complete",
    ]
    assert family.send_state == "in sync"


def test_family_health_warns_when_existing_family_is_missing_after() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="198.51.100.20",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=100,
                accepted_prefix_count=100,
                active_prefix_count=100,
                advertised_prefix_count=100,
            ),
            BgpFamilyHealthCounters(
                table="inet6.0",
                family="ipv6-unicast",
                received_prefix_count=50,
                accepted_prefix_count=50,
                active_prefix_count=50,
                advertised_prefix_count=50,
            ),
        ],
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="198.51.100.20",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=100,
                accepted_prefix_count=100,
                active_prefix_count=100,
                advertised_prefix_count=100,
            )
        ],
    )

    results = evaluate_family_health_for_peer(
        before,
        after,
        device="router-1",
        neighbor="198.51.100.20",
    )
    by_table = {item.table: item for item in results}

    assert by_table["inet6.0"].result == "WARNING"
    assert [finding.rule for finding in by_table["inet6.0"].findings] == [
        "missing_family_after"
    ]
