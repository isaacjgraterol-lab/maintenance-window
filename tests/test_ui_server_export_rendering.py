from __future__ import annotations

from maintenance_window.ui.server import UiState, _render_result


def test_render_result_with_report_directory_includes_export_buttons() -> None:
    state = UiState(
        action="compare-full",
        exit_code=0,
        result_title="Maintenance Window Result - Full",
        result_message="Comparison completed.",
        report_summary={
            "overall_result": "PASS_WITH_UNHEALTHY_SESSIONS",
            "report_directory": "C:/repo/outputs/snapshots/bgp/MW_TEST/comparison_reports/20260703_120000",
        },
    )

    rendered = _render_result(state)

    assert "Download Summary TXT" in rendered
    assert "Download Detail TXT" in rendered
    assert "Download JSON" in rendered
    assert "Download PDF" in rendered
    assert "report_dir=" in rendered


def test_render_result_with_export_path_includes_export_file_buttons() -> None:
    state = UiState(
        action="compare-state",
        exit_code=0,
        result_title="Maintenance Window Result - State",
        result_message="Comparison completed.",
        report_summary={
            "overall_result": "PASS",
            "export_path": "C:/repo/outputs/reports/gui_MW_TEST_state.json",
        },
    )

    rendered = _render_result(state)

    assert "Download Summary TXT" in rendered
    assert "Download Detail TXT" in rendered
    assert "Download JSON" in rendered
    assert "Download PDF" in rendered
    assert "export_file=gui_MW_TEST_state.json" in rendered


def test_render_result_shows_polished_summary_cards_and_collapsed_output() -> None:
    state = UiState(
        action="compare-full",
        exit_code=0,
        result_title="Maintenance Window Result - Full",
        result_message=(
            "Maintenance-window comparison executed using devices found in the "
            "selected MW snapshot folders. Summary is shown below and report "
            "artifacts are available for download."
        ),
        command="python main.py --protocol bgp",
        stdout="Overall result: WARNING",
        report_summary={
            "overall_result": "WARNING",
            "state_result": "PASS",
            "session_health_result": "WARNING",
            "lost_sessions": 0,
            "new_sessions": 0,
            "state_changes": 1,
            "new_unhealthy": 0,
            "warning_peers": 10,
            "uptime_resets": 1,
            "flap_count_increases": 1,
            "low_after_uptime_peers": 1,
            "warning_families": 47,
            "failed_families": 0,
            "snapshot_evidence": [
                {
                    "device": "198.51.100.11",
                    "before_source": "pyez",
                    "before_raw_timestamp": "20260708_090608",
                    "after_source": "pyez",
                    "after_raw_timestamp": "20260708_090709",
                }
            ],
            "snapshot_evidence_total": 1,
        },
    )

    rendered = _render_result(state)

    assert "Summary is shown below and report artifacts are available for download." in rendered
    assert "This comparison uses the current before/after snapshot files" in rendered
    assert "General summary" in rendered
    assert "BGP State" in rendered
    assert "BGP Session Health" in rendered
    assert "Future BGP modules" not in rendered
    assert rendered.index("BGP State") < rendered.index("State changes")
    assert rendered.index("BGP Session Health") < rendered.index("Warning peers")
    assert "Warning families" in rendered
    assert "Uptime resets" in rendered
    assert "Flap increases" in rendered
    assert "Low uptime peers" in rendered
    assert "Snapshot evidence used" in rendered
    assert "20260708_090608" in rendered
    assert "20260708_090709" in rendered
    assert "current before/after snapshot files" in rendered
    assert "Command and operator output" in rendered
    assert "<details" in rendered
    assert "JSON remains exported" not in rendered
