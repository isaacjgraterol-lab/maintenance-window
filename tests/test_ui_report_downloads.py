from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.ui.report_downloads import (
    build_export_actions,
    resolve_report_download,
)


def _report_dir(project_root: Path) -> Path:
    path = (
        project_root
        / "outputs"
        / "snapshots"
        / "bgp"
        / "MW_TEST"
        / "comparison_reports"
        / "20260703_120000"
    )
    path.mkdir(parents=True)
    return path


def _export_file(project_root: Path, name: str = "gui_MW_TEST_state.json") -> Path:
    path = project_root / "outputs" / "reports" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"result": "PASS"}', encoding="utf-8")
    return path


def test_build_export_actions_returns_empty_without_report_reference() -> None:
    assert build_export_actions({}) == ""
    assert build_export_actions({"overall_result": "PASS"}) == ""


def test_build_export_actions_contains_download_links_for_report_directory() -> None:
    html = build_export_actions({"report_directory": "C:/repo/reports"})

    assert "Download Summary TXT" in html
    assert "Download Detail TXT" in html
    assert "Download JSON" in html
    assert "Download PDF" in html
    assert "/download-report?" in html
    assert "report_dir=" in html


def test_build_export_actions_contains_export_file_for_json_export() -> None:
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


def test_resolve_summary_detail_and_json_downloads_from_report_dir(tmp_path: Path) -> None:
    report_dir = _report_dir(tmp_path)
    (report_dir / "full_summary.txt").write_text("summary", encoding="utf-8")
    (report_dir / "full_detail.txt").write_text("detail", encoding="utf-8")
    (report_dir / "full_report.json").write_text('{"result": "PASS"}', encoding="utf-8")

    summary = resolve_report_download(tmp_path, str(report_dir), "summary-txt")
    detail = resolve_report_download(tmp_path, str(report_dir), "detail-txt")
    json_report = resolve_report_download(tmp_path, str(report_dir), "json")

    assert summary.path.name == "full_summary.txt"
    assert detail.path.name == "full_detail.txt"
    assert json_report.path.name == "full_report.json"
    assert summary.content_type.startswith("text/plain")
    assert json_report.content_type.startswith("application/json")


def test_resolve_pdf_download_from_report_dir_generates_pdf(tmp_path: Path) -> None:
    report_dir = _report_dir(tmp_path)
    (report_dir / "full_summary.txt").write_text("summary", encoding="utf-8")
    (report_dir / "full_detail.txt").write_text("detail", encoding="utf-8")

    pdf_report = resolve_report_download(tmp_path, str(report_dir), "pdf")

    assert pdf_report.path.exists()
    assert pdf_report.path.read_bytes().startswith(b"%PDF")
    assert pdf_report.content_type == "application/pdf"
    assert pdf_report.filename.endswith("_report.pdf")
    assert pdf_report.delete_after_send is True


def test_resolve_downloads_from_export_file_name(tmp_path: Path) -> None:
    export_path = _export_file(tmp_path)

    summary = resolve_report_download(
        tmp_path,
        export_file_text=export_path.name,
        kind="summary-txt",
    )
    detail = resolve_report_download(
        tmp_path,
        export_file_text=export_path.name,
        kind="detail-txt",
    )
    json_report = resolve_report_download(
        tmp_path,
        export_file_text=export_path.name,
        kind="json",
    )
    pdf = resolve_report_download(
        tmp_path,
        export_file_text=export_path.name,
        kind="pdf",
    )

    assert summary.path.exists()
    assert detail.path.exists()
    assert json_report.path == export_path
    assert pdf.path.exists()
    assert pdf.path.read_bytes().startswith(b"%PDF")
    assert summary.delete_after_send is True
    assert detail.delete_after_send is True
    assert json_report.delete_after_send is False
    assert pdf.delete_after_send is True


def test_resolve_downloads_from_export_path_for_backwards_compatibility(tmp_path: Path) -> None:
    export_path = _export_file(tmp_path, "gui_MW_TEST_session_health.json")

    json_report = resolve_report_download(
        tmp_path,
        export_path_text=str(export_path),
        kind="json",
    )

    assert json_report.path == export_path
    assert json_report.filename == "MW_TEST_report.json"


def test_resolve_download_rejects_path_outside_project(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside_report_dir"
    outside.mkdir(exist_ok=True)

    with pytest.raises(ValueError):
        resolve_report_download(tmp_path, str(outside), "json")


def test_resolve_download_rejects_unknown_kind(tmp_path: Path) -> None:
    report_dir = _report_dir(tmp_path)

    with pytest.raises(ValueError):
        resolve_report_download(tmp_path, str(report_dir), "xlsx")


def test_resolve_download_rejects_missing_reference(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_report_download(tmp_path, kind="json")
