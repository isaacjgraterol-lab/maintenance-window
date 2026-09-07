from __future__ import annotations

import argparse
import json
from pathlib import Path

from maintenance_window.cli import build_parser
from maintenance_window.protocols.bgp.full_report import reports
from maintenance_window.protocols.bgp.full_report import cli as full_cli


def test_parser_accepts_full_module() -> None:
    parser = build_parser()

    args = parser.parse_args([
        "--protocol",
        "bgp",
        "--module",
        "full",
        "--compare-snapshots",
        "before,after",
        "--mw-id",
        "MW_001",
        "--device",
        "all",
    ])

    assert args.module == "full"


def test_full_report_payload_combines_state_and_session_health() -> None:
    request = argparse.Namespace(
        mw_id="MW_001",
        before_stage="before",
        after_stage="after",
        device_names=["198.51.100.9"],
    )

    payload = reports.build_full_report_payload(
        request=request,
        state_reports=[
            {
                "module": "state",
                "device": "198.51.100.9",
                "result": "PASS",
                "lost_sessions_count": 0,
                "new_sessions_count": 0,
                "state_changes_count": 0,
                "new_unhealthy_count": 0,
                "persistent_unhealthy_count": 0,
            }
        ],
        session_health_reports=[
            {
                "module": "session-health",
                "device": "198.51.100.9",
                "result": "FAIL",
                "peers_total": 4,
                "peers_failed": 1,
                "peers_warning": 0,
                "peers_not_evaluated": 0,
                "peers": [],
            }
        ],
    )

    assert payload["result"] == "FAIL"
    assert payload["module_summary"]["state"]["result"] == "PASS"
    assert payload["module_summary"]["session-health"]["result"] == "FAIL"


def test_full_report_writes_summary_detail_and_json(tmp_path: Path) -> None:
    request = argparse.Namespace(
        mw_id="MW_001",
        before_stage="before",
        after_stage="after",
        device_names=["198.51.100.9"],
    )
    payload = reports.build_full_report_payload(
        request=request,
        state_reports=[{"device": "198.51.100.9", "result": "PASS"}],
        session_health_reports=[
            {
                "device": "198.51.100.9",
                "result": "PASS",
                "peers_total": 1,
                "peers_failed": 0,
                "peers_warning": 0,
                "peers_not_evaluated": 0,
            }
        ],
    )

    saved = reports.write_full_reports(
        snapshot_root=tmp_path,
        payload=payload,
        timestamp="20260701_120000",
    )

    assert Path(saved["summary"]).exists()
    assert Path(saved["detail"]).exists()
    assert Path(saved["json"]).exists()
    assert json.loads(Path(saved["json"]).read_text(encoding="utf-8"))["module"] == "full"


def test_run_bgp_full_report_uses_both_modules(monkeypatch, tmp_path, capsys) -> None:
    request = argparse.Namespace(
        mw_id="MW_001",
        before_stage="before",
        after_stage="after",
        device_names=["198.51.100.9"],
        output="summary",
        export_path=None,
    )

    monkeypatch.setattr(full_cli, "DEFAULT_BGP_SNAPSHOT_ROOT", tmp_path)
    monkeypatch.setattr(
        full_cli,
        "build_state_report",
        lambda request, device_name: {
            "module": "state",
            "device": device_name,
            "result": "PASS",
        },
    )
    monkeypatch.setattr(
        full_cli,
        "build_session_health_report",
        lambda request, device_name: {
            "module": "session-health",
            "device": device_name,
            "result": "FAIL",
            "peers_total": 1,
            "peers_failed": 1,
            "peers_warning": 0,
            "peers_not_evaluated": 0,
            "peers": [],
        },
    )

    exit_code = full_cli.run_bgp_full_report(request)
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "BGP Full Maintenance Report" in output
    assert "BGP-STATE: PASS" in output
    assert "BGP-SESSION-HEALTH: FAIL" in output
    assert (tmp_path / "MW_001" / "comparison_reports").exists()


def test_full_summary_explains_warning_peers_and_families() -> None:
    request = argparse.Namespace(
        mw_id="MW_001",
        before_stage="before",
        after_stage="after",
        device_names=["198.51.100.9"],
    )

    payload = reports.build_full_report_payload(
        request=request,
        state_reports=[{"device": "198.51.100.9", "result": "PASS"}],
        session_health_reports=[
            {
                "device": "198.51.100.9",
                "result": "WARNING",
                "peers_total": 1,
                "peers_passed": 0,
                "peers_failed": 0,
                "peers_warning": 1,
                "peers_not_evaluated": 0,
                "families_total": 2,
                "families_warning": 1,
                "families_failed": 0,
                "peers": [
                    {
                        "neighbor": "198.51.100.3",
                        "result": "WARNING",
                        "before": {
                            "state": "Established",
                            "health": "OK",
                            "uptime": "2d 6:30:26",
                            "elapsed_time_seconds": 196226,
                            "flap_count": 1,
                            "active_prefix_count": 4,
                            "received_prefix_count": 14,
                            "accepted_prefix_count": 10,
                            "suppressed_prefix_count": 0,
                            "advertised_prefix_count": None,
                        },
                        "after": {
                            "state": "Established",
                            "health": "OK",
                            "uptime": "14",
                            "elapsed_time_seconds": 14,
                            "flap_count": 2,
                            "active_prefix_count": 0,
                            "received_prefix_count": 20,
                            "accepted_prefix_count": 10,
                            "suppressed_prefix_count": 0,
                            "advertised_prefix_count": None,
                        },
                        "findings": [
                            {
                                "severity": "WARNING",
                                "rule": "uptime_reset",
                                "message": "BGP uptime decreased/reset (196226s -> 14s).",
                            }
                        ],
                        "families": [
                            {
                                "table": "inet.3",
                                "family": "ipv4-labeled-unicast",
                                "result": "WARNING",
                                "before": {
                                    "table": "inet.3",
                                    "family": "ipv4-labeled-unicast",
                                    "active_prefix_count": 2,
                                    "received_prefix_count": 7,
                                    "accepted_prefix_count": 5,
                                    "suppressed_prefix_count": 0,
                                    "advertised_prefix_count": None,
                                },
                                "after": {
                                    "table": "inet.3",
                                    "family": "ipv4-labeled-unicast",
                                    "active_prefix_count": 0,
                                    "received_prefix_count": 10,
                                    "accepted_prefix_count": 5,
                                    "suppressed_prefix_count": 0,
                                    "advertised_prefix_count": None,
                                },
                                "findings": [
                                    {
                                        "severity": "WARNING",
                                        "rule": "prefix_delta",
                                        "message": "active_prefix_count changed for table inet.3 (2 -> 0).",
                                        "table": "inet.3",
                                        "family": "ipv4-labeled-unicast",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    )

    summary = reports.format_full_summary(payload)
    detail = reports.format_full_detail(payload)

    assert "Families total: 2" in summary
    assert "Warning families: 1" in summary
    assert "Result explanation:" in summary
    assert "uptime_reset" in summary
    assert "prefix_delta" in summary
    assert "Peer: 198.51.100.3" in detail
    assert "Family/Table Details:" in detail
    assert "Table: inet.3" in detail
    assert "Family: ipv4-labeled-unicast" in detail
    assert "active: 2 -> 0" in detail
    assert "received: 7 -> 10" in detail
