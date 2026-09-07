from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import json

from maintenance_window.cli import build_parser
from maintenance_window.cli_handlers.validation import rendering
from maintenance_window.cli_handlers.validation.models import (
    DeviceCollectionError,
    ValidationArtifacts,
)
from maintenance_window.protocols.bgp.state.models import BgpSession


def _args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "protocol": "bgp",
        "source": "ssh",
        "workers": 1,
        "auth_backend": "auto",
        "device": "router-a",
        "snapshot": None,
        "mw_id": None,
        "output": "summary",
        "export": None,
    }
    values.update(overrides)
    return Namespace(**values)


def _session(
    device: str = "router-a",
    neighbor: str = "192.0.2.1",
    state: str = "Established",
) -> BgpSession:
    return BgpSession(device=device, neighbor=neighbor, state=state)


def test_parser_accepts_output_modes() -> None:
    parser = build_parser()

    assert parser.parse_args(["--source", "ssh"]).output == "summary"
    assert parser.parse_args(["--source", "ssh", "--output", "detail"]).output == "detail"
    assert parser.parse_args(["--source", "ssh", "--output", "json"]).output == "json"


def test_snapshot_validation_reports_are_saved(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(rendering, "DEFAULT_BGP_SNAPSHOT_ROOT", tmp_path)
    artifacts = ValidationArtifacts(
        sessions=[_session(), _session(neighbor="192.0.2.2", state="Idle")],
        actual_sources=["router-a: ssh"],
        raw_files=[tmp_path / "raw.json"],
        snapshot_files=[tmp_path / "MW-001" / "before" / "router-a.json"],
    )

    exit_code = rendering.render_validation_result(
        args=_args(snapshot="before", mw_id="MW-001"),
        status_filter="all",
        artifacts=artifacts,
        filtered_sessions=list(artifacts.sessions),
    )

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Maintenance Window BGP Validation" in captured
    assert "Summary report" in captured

    report_roots = list((tmp_path / "MW-001" / "before" / "reports").iterdir())
    assert len(report_roots) == 1
    report_root = report_roots[0]
    assert (report_root / "summary.txt").is_file()
    assert (report_root / "detail.txt").is_file()
    report_json = report_root / "report.json"
    assert report_json.is_file()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["collection_summary"]["sessions_collected"] == 2
    assert payload["collection_summary"]["sessions_selected"] == 2
    assert payload["session_state_summary"] == {
        "Established": 1,
        "Idle": 1,
    }
    assert payload["artifacts"]["validation_report_files"] is not None


def test_non_snapshot_validation_does_not_save_reports(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(rendering, "DEFAULT_BGP_SNAPSHOT_ROOT", tmp_path)
    artifacts = ValidationArtifacts(
        sessions=[_session()],
        actual_sources=["router-a: ssh"],
    )

    exit_code = rendering.render_validation_result(
        args=_args(output="summary"),
        status_filter="all",
        artifacts=artifacts,
        filtered_sessions=list(artifacts.sessions),
    )

    assert exit_code == 0
    assert not list(tmp_path.rglob("summary.txt"))
    assert "Snapshot reports: not saved" in capsys.readouterr().out


def test_json_terminal_output_and_collection_error_exit_code(capsys) -> None:
    artifacts = ValidationArtifacts(
        sessions=[_session()],
        actual_sources=["router-a: ssh"],
        device_errors=[
            DeviceCollectionError(
                device="router-b",
                source="ssh",
                error_type="RuntimeError",
                error="authentication failed",
            )
        ],
    )

    exit_code = rendering.render_validation_result(
        args=_args(output="json"),
        status_filter="all",
        artifacts=artifacts,
        filtered_sessions=list(artifacts.sessions),
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"] == "PARTIAL_COLLECTION"
    assert payload["collection_summary"]["devices_failed"] == 1


def test_detail_terminal_output_contains_sessions(capsys) -> None:
    artifacts = ValidationArtifacts(
        sessions=[_session()],
        actual_sources=["router-a: ssh"],
    )

    rendering.render_validation_result(
        args=_args(output="detail"),
        status_filter="all",
        artifacts=artifacts,
        filtered_sessions=list(artifacts.sessions),
    )

    captured = capsys.readouterr().out
    assert "Maintenance Window BGP Validation - Detail" in captured
    assert "Sessions:" in captured
    assert "192.0.2.1" in captured
