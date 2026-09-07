from __future__ import annotations

import argparse
import json
from pathlib import Path

from maintenance_window.cli import build_parser  # noqa: F401
from maintenance_window.protocols.bgp.full_report import reports
from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpSessionHealthRecord,
)
from maintenance_window.protocols.bgp.session_health.rules import (
    evaluate_family_health_for_peer,
    evaluate_session_health,
    result_from_findings,
    result_from_peer_and_family_results,
)
from maintenance_window.ui.report_reader import read_report_summary
from maintenance_window.ui.server import UiState, _render_result


def test_session_health_detects_restart_from_snapshot_uptime_continuity() -> None:
    before = BgpSessionHealthRecord(
        device="192.0.2.12",
        neighbor="192.0.2.11",
        peer_state="Established",
        elapsed_time_seconds=1389,
        flap_count=1,
    )
    after = BgpSessionHealthRecord(
        device="192.0.2.12",
        neighbor="192.0.2.11",
        peer_state="Established",
        elapsed_time_seconds=1581,
        flap_count=0,
    )

    findings = evaluate_session_health(
        before,
        after,
        snapshot_elapsed_seconds=1840,
    )
    rules = {finding.rule for finding in findings}

    assert "session_restart_detected" in rules
    assert "uptime_reset" not in rules
    assert "flap_count_reset" in rules
    assert result_from_findings(findings) == "WARNING"


def test_session_health_does_not_flag_normal_uptime_continuity() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Established",
        elapsed_time_seconds=1389,
        flap_count=0,
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Established",
        elapsed_time_seconds=3229,
        flap_count=0,
    )

    findings = evaluate_session_health(
        before,
        after,
        snapshot_elapsed_seconds=1840,
    )

    assert "session_restart_detected" not in {
        finding.rule for finding in findings
    }


def test_family_warning_is_propagated_to_visible_peer_result() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=1000,
            )
        ],
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Established",
        families=[
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=980,
            )
        ],
    )

    peer_findings = evaluate_session_health(before, after)
    family_results = evaluate_family_health_for_peer(
        before,
        after,
        device="router-1",
        neighbor="192.0.2.1",
    )

    assert result_from_findings(peer_findings) == "PASS"
    assert family_results[0].result == "WARNING"
    assert (
        result_from_peer_and_family_results(peer_findings, family_results)
        == "WARNING"
    )


def test_persistent_unhealthy_peer_is_not_hidden_by_family_warning() -> None:
    before = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Active",
        families=[
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=10,
            )
        ],
    )
    after = BgpSessionHealthRecord(
        device="router-1",
        neighbor="192.0.2.1",
        peer_state="Active",
        families=[
            BgpFamilyHealthCounters(
                table="inet.0",
                family="ipv4-unicast",
                received_prefix_count=11,
            )
        ],
    )

    peer_findings = evaluate_session_health(before, after)
    family_results = evaluate_family_health_for_peer(
        before,
        after,
        device="router-1",
        neighbor="192.0.2.1",
    )

    assert (
        result_from_peer_and_family_results(peer_findings, family_results)
        == "UNHEALTHY"
    )


def _sanitized_hardening_payload() -> dict[str, object]:
    request = argparse.Namespace(
        mw_id="MW_DEMO_HARDENING",
        before_stage="before",
        after_stage="after",
        device_names=["192.0.2.11", "192.0.2.12"],
    )
    return reports.build_full_report_payload(
        request=request,
        state_reports=[
            {
                "device": "192.0.2.11",
                "result": "PASS",
                "before": {"total_sessions": 12},
                "after": {"total_sessions": 12},
                "persistent_unhealthy_count": 1,
            },
            {
                "device": "192.0.2.12",
                "result": "PASS",
                "before": {"total_sessions": 5},
                "after": {"total_sessions": 5},
                "persistent_unhealthy_count": 0,
            },
        ],
        session_health_reports=[
            {
                "device": "192.0.2.11",
                "result": "WARNING",
                "peers_total": 12,
                "peers_passed": 9,
                "peers_failed": 0,
                "peers_warning": 2,
                "peers_unhealthy": 1,
                "peers_not_evaluated": 0,
                "families_total": 54,
                "families_warning": 11,
                "families_failed": 0,
                "peers": [],
            },
            {
                "device": "192.0.2.12",
                "result": "WARNING",
                "peers_total": 5,
                "peers_passed": 4,
                "peers_failed": 0,
                "peers_warning": 1,
                "peers_unhealthy": 0,
                "peers_not_evaluated": 0,
                "families_total": 23,
                "families_warning": 12,
                "families_failed": 0,
                "peers": [],
            },
        ],
    )


def test_full_summary_contains_per_device_state_and_health_views() -> None:
    payload = _sanitized_hardening_payload()
    summary = reports.format_full_summary(payload)

    assert "DEVICE SUMMARY:" in summary
    assert "Device: 192.0.2.11" in summary
    assert "Device: 192.0.2.12" in summary
    assert "Total sessions: 12 -> 12" in summary
    assert "Total sessions: 5 -> 5" in summary
    assert "Total peers: 12" in summary
    assert "Total peers: 5" in summary
    assert payload["device_summary"][0]["state"]["persistent_unhealthy"] == 1


def test_result_explanation_is_not_truncated_in_summary_or_detail() -> None:
    request = argparse.Namespace(
        mw_id="MW_TEST",
        before_stage="before",
        after_stage="after",
        device_names=["router-1"],
    )
    findings = [
        {
            "severity": "WARNING",
            "rule": f"warning_rule_{index}",
            "message": f"warning message {index}",
        }
        for index in range(40)
    ]
    payload = reports.build_full_report_payload(
        request=request,
        state_reports=[{"device": "router-1", "result": "PASS"}],
        session_health_reports=[
            {
                "device": "router-1",
                "result": "WARNING",
                "peers_total": 1,
                "peers_passed": 0,
                "peers_failed": 0,
                "peers_warning": 1,
                "peers_unhealthy": 0,
                "peers_not_evaluated": 0,
                "families_total": 0,
                "families_warning": 0,
                "families_failed": 0,
                "peers": [
                    {
                        "neighbor": "192.0.2.1",
                        "result": "WARNING",
                        "findings": findings,
                        "families": [],
                    }
                ],
            }
        ],
    )

    summary = reports.format_full_summary(payload)
    detail = reports.format_full_detail(payload)

    assert "warning_rule_0" in summary
    assert "warning_rule_39" in summary
    assert "warning_rule_39" in detail
    assert detail.index("Result explanation:") < detail.index(
        "BGP-STATE device reports:"
    )


def test_read_report_summary_aggregates_multi_device_state_totals(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report.json"
    payload = _sanitized_hardening_payload()
    report.write_text(json.dumps(payload), encoding="utf-8")

    summary = read_report_summary(report)

    assert summary["total_sessions_before"] == 17
    assert summary["total_sessions_after"] == 17
    assert len(summary["device_summaries"]) == 2


def test_read_report_summary_counts_restart_and_flap_reset_rules(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "reports": {
                    "state": [],
                    "session_health": [
                        {
                            "device": "r1",
                            "peers": [
                                {
                                    "neighbor": "n1",
                                    "findings": [
                                        {"rule": "session_restart_detected"},
                                        {"rule": "flap_count_reset"},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    summary = read_report_summary(report)

    assert summary["session_restarts"] == 1
    assert summary["flap_count_resets"] == 1


def test_render_result_includes_per_device_operational_summary() -> None:
    state = UiState(
        action="compare-full",
        exit_code=0,
        result_title="Maintenance Window Result - Full",
        report_summary={
            "overall_result": "WARNING",
            "device_summaries": _sanitized_hardening_payload()["device_summary"],
        },
    )

    rendered = _render_result(state)

    assert "Per-device summary" in rendered
    assert "192.0.2.11" in rendered
    assert "12 -&gt; 12" in rendered
    assert "P:9 W:2 F:0 U:1 NE:0" in rendered
    assert "T:54 W:11 F:0" in rendered
