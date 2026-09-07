from __future__ import annotations

from datetime import datetime, timedelta, timezone

from maintenance_window.ui.executive_pdf import (
    _fit_text_size,
    _format_generated_timestamp,
    build_executive_pdf,
)


def test_long_windows_timezone_is_abbreviated() -> None:
    value = datetime(
        2026,
        9,
        5,
        17,
        16,
        tzinfo=timezone(timedelta(hours=-6), "Mountain Daylight Time"),
    )

    assert _format_generated_timestamp(value) == "2026-09-05 17:16 MDT"


def test_fit_text_size_shrinks_only_when_value_actually_exceeds_width() -> None:
    short_size = _fit_text_size("BGP", 100.0, 13.0, bold=True)
    fitting_size = _fit_text_size(
        "MW_BACKBONE_MIGRATION_DEMO_2026",
        176.0,
        8.5,
        bold=True,
        minimum=6.8,
    )
    oversized_size = _fit_text_size(
        "MW_BACKBONE_MIGRATION_DEMO_REGION_NORTH_2026",
        176.0,
        8.5,
        bold=True,
        minimum=6.8,
    )

    assert short_size == 13.0
    assert fitting_size == 8.5
    assert 6.8 <= oversized_size < 8.5


def test_executive_pdf_accepts_long_context_values_without_changing_page_count() -> None:
    payload = {
        "protocol": "bgp",
        "module": "full",
        "mw_id": "MW_BACKBONE_MIGRATION_DEMO_REGION_NORTH_2026",
        "before_stage": "before",
        "after_stage": "after",
        "devices": ["192.0.2.11", "192.0.2.12"],
        "result": "WARNING",
        "state_result": "PASS",
        "session_health_result": "WARNING",
        "global_summary": {
            "overall_result": "WARNING",
            "modules": {"state": "PASS", "session-health": "WARNING"},
            "state": {"total_devices": 2},
            "session_health": {
                "total_peers": 17,
                "total_warning_peers": 8,
                "total_unhealthy_peers": 1,
                "total_warning_families": 23,
                "total_failed_peers": 0,
                "total_not_evaluated_peers": 0,
            },
        },
        "device_summary": [],
        "reports": {"state": [], "session_health": []},
    }

    pdf = build_executive_pdf(payload)

    assert pdf.startswith(b"%PDF-1.4")
    assert b"MW_BACKBONE_MIGRATION_DEMO_REGION_NORTH_2026" in pdf
    assert b"/Count 3" in pdf
