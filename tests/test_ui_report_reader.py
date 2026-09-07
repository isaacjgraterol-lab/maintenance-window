from __future__ import annotations

import json
from pathlib import Path

from maintenance_window.ui.report_reader import read_report_summary, resolve_health_depth


def test_read_full_report_summary(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            {
                "result": "PASS_WITH_UNHEALTHY_SESSIONS",
                "state_result": "PASS",
                "session_health_result": "PASS_WITH_UNHEALTHY_SESSIONS",
                "report_directory": "outputs/snapshots/bgp/MW/report",
                "global_summary": {
                    "state": {
                        "total_lost_sessions": 0,
                        "total_new_sessions": 0,
                        "total_state_changes": 1,
                        "total_new_unhealthy": 0,
                        "total_resolved_unhealthy": 0,
                        "total_persistent_unhealthy": 4,
                    },
                    "session_health": {
                        "total_warning_peers": 2,
                        "total_failed_peers": 0,
                        "total_unhealthy_peers": 4,
                        "total_warning_families": 7,
                        "total_failed_families": 0,
                        "total_families": 30,
                        "total_not_evaluated_peers": 93,
                    },
                },
                "reports": {
                    "state": [
                        {
                            "device": "198.51.100.11",
                            "before": {
                                "total_sessions": 97,
                                "unique_sessions": 97,
                                "duplicate_entries": 0,
                                "source_actual": "pyez",
                                "raw_file": "outputs/raw/pyez/192.0.2.44_20260708_090608.xml",
                            },
                            "after": {
                                "total_sessions": 97,
                                "unique_sessions": 97,
                                "duplicate_entries": 0,
                                "source_actual": "pyez",
                                "raw_file": "outputs/raw/pyez/192.0.2.44_20260708_090709.xml",
                            },
                        }
                    ],
                    "session_health": [
                        {
                            "device": "198.51.100.11",
                            "peers": [
                                {
                                    "neighbor": "198.51.100.2",
                                    "findings": [
                                        {"rule": "uptime_reset"},
                                        {"rule": "flap_count_increased"},
                                        {"rule": "low_after_uptime"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    summary = read_report_summary(path)

    assert summary["overall_result"] == "PASS_WITH_UNHEALTHY_SESSIONS"
    assert summary["state_result"] == "PASS"
    assert summary["session_health_result"] == "PASS_WITH_UNHEALTHY_SESSIONS"
    assert summary["total_sessions_before"] == 97
    assert summary["total_sessions_after"] == 97
    assert summary["lost_sessions"] == 0
    assert summary["new_sessions"] == 0
    assert summary["state_changes"] == 1
    assert summary["new_unhealthy"] == 0
    assert summary["resolved_unhealthy"] == 0
    assert summary["persistent_unhealthy"] == 4
    assert summary["warning_peers"] == 2
    assert summary["failed_peers"] == 0
    assert summary["unhealthy_peers"] == 4
    assert summary["warning_families"] == 7
    assert summary["failed_families"] == 0
    assert summary["total_families"] == 30
    assert summary["not_evaluated_peers"] == 93
    assert summary["uptime_resets"] == 1
    assert summary["flap_count_increases"] == 1
    assert summary["low_after_uptime_peers"] == 1
    assert summary["report_directory"] == "outputs/snapshots/bgp/MW/report"
    evidence = summary["snapshot_evidence"]
    assert isinstance(evidence, list)
    assert evidence[0]["device"] == "198.51.100.11"
    assert evidence[0]["before_source"] == "pyez"
    assert evidence[0]["after_source"] == "pyez"
    assert evidence[0]["before_raw_timestamp"] == "20260708_090608"
    assert evidence[0]["after_raw_timestamp"] == "20260708_090709"


def test_read_report_summary_counts_each_peer_rule_once(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            {
                "reports": {
                    "session_health": [
                        {
                            "device": "r1",
                            "peers": [
                                {
                                    "neighbor": "n1",
                                    "findings": [
                                        {"rule": "uptime_reset"},
                                        {"rule": "uptime_reset"},
                                    ],
                                },
                                {
                                    "neighbor": "n2",
                                    "findings": [{"rule": "uptime_reset"}],
                                },
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    summary = read_report_summary(path)

    assert summary["uptime_resets"] == 2


def test_resolve_health_depth_uses_not_evaluated_peers() -> None:
    assert (
        resolve_health_depth(
            source="pyez",
            selected="auto",
            not_evaluated_peers=2,
        )
        == "partial-health"
    )


def test_resolve_health_depth_state_action() -> None:
    assert (
        resolve_health_depth(
            source="ssh",
            selected="auto",
            action="compare-state",
        )
        == "state-only"
    )
