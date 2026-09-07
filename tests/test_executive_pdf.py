from __future__ import annotations

import json
from pathlib import Path

from maintenance_window.ui.executive_pdf import build_executive_pdf
from maintenance_window.ui.report_downloads import resolve_report_download


def _sample_payload() -> dict[str, object]:
    return {
        "protocol": "bgp",
        "module": "full",
        "mw_id": "MW_DEMO_HARDENING",
        "before_stage": "before",
        "after_stage": "after",
        "devices": ["192.0.2.11", "192.0.2.12"],
        "result": "WARNING",
        "state_result": "PASS",
        "session_health_result": "WARNING",
        "global_summary": {
            "overall_result": "WARNING",
            "modules": {"state": "PASS", "session-health": "WARNING"},
            "state": {
                "total_devices": 2,
                "total_lost_sessions": 0,
                "total_new_sessions": 0,
                "total_state_changes": 0,
                "total_new_unhealthy": 0,
                "total_persistent_unhealthy": 1,
            },
            "session_health": {
                "total_peers": 17,
                "total_failed_peers": 0,
                "total_warning_peers": 8,
                "total_unhealthy_peers": 1,
                "total_not_evaluated_peers": 0,
                "total_families": 77,
                "total_warning_families": 23,
                "total_failed_families": 0,
            },
        },
        "device_summary": [
            {
                "device": "192.0.2.11",
                "overall_result": "WARNING",
                "state": {
                    "result": "PASS",
                    "total_sessions_before": 12,
                    "total_sessions_after": 12,
                    "persistent_unhealthy": 1,
                },
                "session_health": {
                    "result": "WARNING",
                    "total_peers": 12,
                    "passed_peers": 7,
                    "failed_peers": 0,
                    "warning_peers": 4,
                    "unhealthy_peers": 1,
                    "not_evaluated_peers": 0,
                    "families_total": 54,
                    "warning_families": 11,
                    "failed_families": 0,
                },
                "finding_counts": {
                    "session_restart_detected": 2,
                    "flap_count_increased": 2,
                    "new_family_after": 1,
                    "missing_family_after": 1,
                    "prefix_delta": 27,
                    "persistent_unhealthy_peer": 1,
                },
            },
            {
                "device": "192.0.2.12",
                "overall_result": "WARNING",
                "state": {
                    "result": "PASS",
                    "total_sessions_before": 5,
                    "total_sessions_after": 5,
                    "persistent_unhealthy": 0,
                },
                "session_health": {
                    "result": "WARNING",
                    "total_peers": 5,
                    "passed_peers": 1,
                    "failed_peers": 0,
                    "warning_peers": 4,
                    "unhealthy_peers": 0,
                    "not_evaluated_peers": 0,
                    "families_total": 23,
                    "warning_families": 12,
                    "failed_families": 0,
                },
                "finding_counts": {
                    "session_restart_detected": 1,
                    "uptime_reset": 1,
                    "flap_count_increased": 1,
                    "flap_count_reset": 1,
                    "new_family_after": 1,
                    "prefix_delta": 30,
                },
            },
        ],
        "reports": {
            "state": [
                {
                    "device": "192.0.2.11",
                    "before": {"source_actual": "pyez"},
                    "after": {"source_actual": "pyez"},
                },
                {
                    "device": "192.0.2.12",
                    "before": {"source_actual": "pyez"},
                    "after": {"source_actual": "pyez"},
                },
            ],
            "session_health": [
                {
                    "device": "192.0.2.11",
                    "peers": [
                        {
                            "peer": "192.0.2.12",
                            "result": "WARNING",
                            "before": {"state": "Established"},
                            "after": {"state": "Established"},
                            "findings": [
                                {"rule": "session_restart_detected"},
                                {"rule": "flap_count_increased"},
                            ],
                            "families": [
                                {"result": "WARNING", "findings": [{"rule": "prefix_delta"}]}
                            ],
                        },
                        {
                            "peer": "2001:db8::44",
                            "result": "UNHEALTHY",
                            "before": {"state": "Active"},
                            "after": {"state": "Active"},
                            "findings": [{"rule": "persistent_unhealthy_peer"}],
                            "families": [],
                        },
                    ],
                },
                {
                    "device": "192.0.2.12",
                    "peers": [
                        {
                            "peer": "192.0.2.11",
                            "result": "WARNING",
                            "before": {"state": "Established"},
                            "after": {"state": "Established"},
                            "findings": [
                                {"rule": "session_restart_detected"},
                                {"rule": "flap_count_reset"},
                            ],
                            "families": [
                                {"result": "WARNING", "findings": [{"rule": "new_family_after"}]}
                            ],
                        }
                    ],
                },
            ],
        },
    }


def test_executive_pdf_is_three_page_vector_report() -> None:
    pdf = build_executive_pdf(_sample_payload())
    assert pdf.startswith(b"%PDF-1.4")
    assert b"Executive Report" in pdf
    assert b"DEVICE EXECUTIVE SUMMARY" in pdf
    assert b"OPERATIONAL ATTENTION" in pdf
    assert b"Missing families" in pdf
    assert b"isaacjgraterol@gmail.com" in pdf
    assert b"linkedin.com/in/inggraterol" in pdf
    assert b"/Count 3" in pdf
    assert len(pdf) > 10000


def test_full_report_download_uses_executive_json_renderer(tmp_path: Path) -> None:
    project = tmp_path
    report_dir = project / "outputs" / "snapshots" / "bgp" / "MW_DEMO_HARDENING" / "comparison_reports" / "20260905_165228"
    report_dir.mkdir(parents=True)
    (report_dir / "full_report.json").write_text(
        json.dumps(_sample_payload()), encoding="utf-8"
    )
    (report_dir / "full_summary.txt").write_text("legacy summary", encoding="utf-8")
    (report_dir / "full_detail.txt").write_text("legacy detail", encoding="utf-8")

    download = resolve_report_download(
        project,
        report_dir_text=str(report_dir),
        kind="pdf",
    )

    assert download.filename == "MW_DEMO_HARDENING_executive_report.pdf"
    assert download.content_type == "application/pdf"
    content = download.path.read_bytes()
    assert b"Executive Report" in content
    assert b"legacy detail" not in content
