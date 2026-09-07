from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.ui.command_builder import UiCommandRequest, build_mw_command
from maintenance_window.ui.options import (
    CAPTURE_LEVEL_OPTIONS,
    GNMIC_LIMITATION_MESSAGE,
    PROTOCOL_OPTIONS,
)
from maintenance_window.ui.report_reader import health_depth_for_source, resolve_health_depth
from maintenance_window.ui.server import _operator_output_for_action


def test_public_protocol_options_expose_only_operational_bgp() -> None:
    options = {option.value: option.available for option in PROTOCOL_OPTIONS}

    assert options == {"bgp": True}


def test_capture_before_command_uses_radius_by_default() -> None:
    command = build_mw_command(
        UiCommandRequest(
            action="capture-before",
            protocol="bgp",
            source="pyez",
            device_mode="individual",
            device="198.51.100.5",
            mw_id="MW_GUI_TEST_001",
        ),
        project_root=Path("/repo"),
        python_executable="python",
    )

    assert command.export_path is None
    assert command.command == [
        "python",
        str(Path("/repo") / "main.py"),
        "--protocol",
        "bgp",
        "--source",
        "pyez",
        "--snapshot",
        "before",
        "--mw-id",
        "MW_GUI_TEST_001",
        "--device",
        "198.51.100.5",
        "--filter",
        "all",
        "--output",
        "summary",
        "--auth-backend",
        "radius",
        "--workers",
        "1",
    ]


def test_capture_before_accepts_runtime_credentials_path() -> None:
    command = build_mw_command(
        UiCommandRequest(
            action="capture-before",
            protocol="bgp",
            source="ssh",
            device_mode="individual",
            device="198.51.100.5",
            mw_id="MW_GUI_TEST_001",
            credentials_path=Path("/tmp/radius.json"),
        ),
        project_root=Path("/repo"),
        python_executable="python",
    )

    assert "--credentials" in command.command
    assert str(Path("/tmp/radius.json")) in command.command


def test_capture_before_supports_limited_gui_workers() -> None:
    command = build_mw_command(
        UiCommandRequest(
            action="capture-before",
            protocol="bgp",
            source="pyez",
            device_mode="individual",
            device="198.51.100.5",
            mw_id="MW_GUI_TEST_001",
            workers=20,
        ),
        project_root=Path("/repo"),
        python_executable="python",
    )

    assert "--workers" in command.command
    assert "20" in command.command


def test_capture_before_rejects_workers_above_gui_limit() -> None:
    with pytest.raises(ValueError, match="Workers"):
        build_mw_command(
            UiCommandRequest(
                action="capture-before",
                protocol="bgp",
                source="pyez",
                device_mode="individual",
                device="198.51.100.5",
                mw_id="MW_GUI_TEST_001",
                workers=50,
            ),
            project_root=Path("/repo"),
            python_executable="python",
        )


def test_compare_full_command_exports_json_and_uses_resolved_devices(tmp_path: Path) -> None:
    mw_id = "MW_GUI_TEST_001"
    snapshot_root = tmp_path / "outputs" / "snapshots" / "bgp" / mw_id
    before_dir = snapshot_root / "before"
    after_dir = snapshot_root / "after"

    before_dir.mkdir(parents=True)
    after_dir.mkdir(parents=True)

    for device in ("198.51.100.5", "198.51.100.6"):
        (before_dir / f"{device}.json").write_text("{}", encoding="utf-8")
        (after_dir / f"{device}.json").write_text("{}", encoding="utf-8")

    # This device exists only in before, so it must not be selected.
    (before_dir / "198.51.100.7.json").write_text("{}", encoding="utf-8")

    command = build_mw_command(
        UiCommandRequest(
            action="compare-full",
            protocol="bgp",
            source="pyez",
            device_mode="individual",
            device="",
            mw_id=mw_id,
        ),
        project_root=tmp_path,
        python_executable="python",
    )

    assert command.export_path == (
        tmp_path / "outputs" / "reports" / "gui_MW_GUI_TEST_001_full.json"
    )
    assert "--module" in command.command
    assert "full" in command.command
    assert "--compare-snapshots" in command.command
    assert "before,after" in command.command
    assert "--export" in command.command

    device_index = command.command.index("--device") + 1
    assert command.command[device_index] == "198.51.100.5,198.51.100.6"
    assert "all" not in command.command

def test_list_manual_db_uses_operator_selected_limit() -> None:
    command = build_mw_command(
        UiCommandRequest(
            action="list-manual-db",
            protocol="bgp",
            source="pyez",
            device_mode="individual",
            device="",
            mw_id="",
            manual_db_limit=200,
        ),
        project_root=Path("/repo"),
        python_executable="python",
    )

    assert command.command == [
        "python",
        str(Path("/repo") / "main.py"),
        "--protocol",
        "bgp",
        "--list-manual-db",
        "--manual-db-limit",
        "200",
    ]


def test_manual_source_uses_input_file() -> None:
    command = build_mw_command(
        UiCommandRequest(
            action="capture-before",
            protocol="bgp",
            source="manual",
            device_mode="individual",
            device="Manual Input",
            mw_id="MW_MANUAL_GUI_001",
            manual_input_path=Path("sample.json"),
            manual_input_format="json-file",
        ),
        project_root=Path("/repo"),
        python_executable="python",
    )

    assert "--source" in command.command
    assert "manual" in command.command
    assert "--input" in command.command
    assert "sample.json" in command.command
    assert "--input-format" in command.command
    assert "json-file" in command.command


def test_gnmic_reports_partial_health() -> None:
    assert health_depth_for_source("gnmic") == "partial-health"
    assert "NOT_EVALUATED" in GNMIC_LIMITATION_MESSAGE


def test_pyez_and_ssh_report_full_health() -> None:
    assert health_depth_for_source("pyez") == "full-health"
    assert health_depth_for_source("ssh") == "full-health"


def test_resolve_health_depth_state_only_action() -> None:
    assert (
        resolve_health_depth(
            source="pyez",
            selected="auto",
            action="compare-state",
            not_evaluated_peers=None,
        )
        == "state-only"
    )


def test_resolve_health_depth_respects_gnmic_limit() -> None:
    assert (
        resolve_health_depth(
            source="gnmic",
            selected="auto",
            action="compare-full",
            not_evaluated_peers=93,
        )
        == "partial-health"
    )


def test_snapshot_operator_output_hides_mw_result() -> None:
    stdout = """Protocol: bgp
Source requested: pyez
Result:
  PASS_WITH_UNHEALTHY_SESSIONS
Total sessions: 111
Unique sessions: 97
"""

    output = _operator_output_for_action("capture-before", stdout)

    assert "Snapshot captured successfully." in output
    assert "No maintenance-window comparison was executed." in output
    assert "PASS_WITH_UNHEALTHY_SESSIONS" not in output
    assert "Total sessions: 111" in output
    assert "Unique sessions: 97" in output


def test_snapshot_operator_output_does_not_fake_success_without_stdout() -> None:
    assert _operator_output_for_action("capture-before", "") == ""


def test_capture_level_basic_is_the_only_enabled_gui_capture_profile() -> None:
    assert CAPTURE_LEVEL_OPTIONS == ("basic",)


def test_capture_before_rejects_unknown_capture_level() -> None:
    with pytest.raises(ValueError, match="capture level"):
        build_mw_command(
            UiCommandRequest(
                action="capture-before",
                protocol="bgp",
                source="pyez",
                device_mode="individual",
                device="198.51.100.5",
                mw_id="MW_GUI_TEST_001",
                capture_level="advanced",
            ),
            project_root=Path("/repo"),
            python_executable="python",
        )
