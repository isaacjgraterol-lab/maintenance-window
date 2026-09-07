from __future__ import annotations

from pathlib import Path

from maintenance_window.ui.report_downloads import (
    build_export_actions,
    resolve_report_download,
)


def test_build_export_actions_from_export_path_uses_export_file() -> None:
    html = build_export_actions(
        {
            "overall_result": "PASS",
            "export_path": "C:/repo/outputs/reports/gui_MW_TEST_state.json",
        }
    )

    assert "Download Summary TXT" in html
    assert "Download Detail TXT" in html
    assert "Download JSON" in html
    assert "Download PDF" in html
    assert "export_file=gui_MW_TEST_state.json" in html
    assert "export_path=" not in html


def test_resolve_downloads_from_export_file_name(tmp_path: Path) -> None:
    export_path = tmp_path / "outputs" / "reports" / "gui_MW_TEST_state.json"
    export_path.parent.mkdir(parents=True)
    export_path.write_text('{"result": "PASS"}', encoding="utf-8")

    summary = resolve_report_download(
        tmp_path,
        export_file_text="gui_MW_TEST_state.json",
        kind="summary-txt",
    )
    detail = resolve_report_download(
        tmp_path,
        export_file_text="gui_MW_TEST_state.json",
        kind="detail-txt",
    )
    json_report = resolve_report_download(
        tmp_path,
        export_file_text="gui_MW_TEST_state.json",
        kind="json",
    )
    pdf = resolve_report_download(
        tmp_path,
        export_file_text="gui_MW_TEST_state.json",
        kind="pdf",
    )

    assert summary.path.exists()
    assert detail.path.exists()
    assert json_report.path == export_path
    assert pdf.path.exists()
    assert pdf.path.read_bytes().startswith(b"%PDF")
