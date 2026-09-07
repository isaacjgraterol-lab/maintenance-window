from __future__ import annotations

import argparse

from maintenance_window.cli import build_parser  # noqa: F401
from maintenance_window.protocols.bgp.full_report import reports
from maintenance_window.ui.server import UiState, _render_result


def _payload() -> dict[str, object]:
    request = argparse.Namespace(
        mw_id="MW_PRESENTATION",
        before_stage="before",
        after_stage="after",
        device_names=["192.0.2.11"],
    )
    return reports.build_full_report_payload(
        request=request,
        state_reports=[
            {
                "device": "192.0.2.11",
                "result": "PASS",
                "before": {"total_sessions": 2},
                "after": {"total_sessions": 2},
                "lost_sessions_count": 0,
                "new_sessions_count": 0,
                "state_changes_count": 0,
                "new_unhealthy_count": 0,
                "persistent_unhealthy_count": 0,
            }
        ],
        session_health_reports=[
            {
                "device": "192.0.2.11",
                "result": "WARNING",
                "peers_total": 2,
                "peers_passed": 1,
                "peers_failed": 0,
                "peers_warning": 1,
                "peers_unhealthy": 0,
                "peers_not_evaluated": 0,
                "families_total": 3,
                "families_warning": 1,
                "families_failed": 0,
                "peers": [
                    {
                        "neighbor": "192.0.2.1",
                        "result": "WARNING",
                        "findings": [
                            {
                                "severity": "WARNING",
                                "rule": "session_restart_detected",
                                "message": "restart detected",
                            },
                            {
                                "severity": "WARNING",
                                "rule": "flap_count_increased",
                                "message": "flap increased",
                            },
                        ],
                        "families": [
                            {
                                "table": "bgp.l3vpn.0",
                                "result": "WARNING",
                                "findings": [
                                    {
                                        "severity": "WARNING",
                                        "rule": "prefix_delta",
                                        "message": "prefix delta",
                                        "table": "bgp.l3vpn.0",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    )


def test_text_reports_have_clear_section_separators() -> None:
    payload = _payload()
    summary = reports.format_full_summary(payload)
    detail = reports.format_full_detail(payload)

    assert "=" * 72 in summary
    assert "-" * 72 in summary
    assert "MODULE RESULTS" in summary
    assert "GLOBAL SUMMARY" in summary
    assert "DEVICE SUMMARY:" in summary
    assert "RESULT EXPLANATION" in summary
    assert "BGP-STATE device reports:" in detail
    assert "BGP-SESSION-HEALTH device reports:" in detail
    assert detail.index("Result explanation:") < detail.index("DETAILED REPORT")


def test_result_page_exposes_clickable_contact_information_and_badges() -> None:
    payload = _payload()
    state = UiState(
        action="compare-full",
        exit_code=0,
        result_title="Maintenance Window Result - Full",
        report_summary={
            "overall_result": "WARNING",
            "state_result": "PASS",
            "session_health_result": "WARNING",
            "device_summaries": payload["device_summary"],
        },
    )

    rendered = _render_result(state)

    assert 'href="mailto:isaacjgraterol@gmail.com"' in rendered
    assert 'href="https://www.linkedin.com/in/inggraterol"' in rendered
    assert "linkedin.com/in/inggraterol" in rendered
    assert "result-badge result-warning" in rendered
    assert "result-badge result-pass" in rendered
    assert "Restart:1" in rendered
    assert "Flap+:1" in rendered
    assert "Prefix delta:1" in rendered
