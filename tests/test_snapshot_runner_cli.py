from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.runners import snapshot_capture as runner


def create_required_files(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    inventory = tmp_path / "devices.txt"
    credentials = tmp_path / "credentials.json"
    connection_settings = tmp_path / "connection_settings.json"
    audit_settings = tmp_path / "bgp_state.json"

    inventory.write_text("198.51.100.8\n", encoding="utf-8")
    credentials.write_text("{}", encoding="utf-8")
    connection_settings.write_text("{}", encoding="utf-8")
    audit_settings.write_text("{}", encoding="utf-8")

    return (
        inventory,
        credentials,
        connection_settings,
        audit_settings,
    )


@pytest.mark.parametrize(
    ("stage", "source"),
    [
        ("before", "auto"),
        ("before", "pyez"),
        ("before", "ssh"),
        ("before", "gnmic"),
        ("after", "ssh"),
    ],
)
def test_capture_command_uses_requested_stage_and_source(
    tmp_path: Path,
    stage: str,
    source: str,
) -> None:
    (
        inventory,
        credentials,
        connection_settings,
        audit_settings,
    ) = create_required_files(tmp_path)

    args = runner.parse_args(
        [
            "--stage",
            stage,
            "--source",
            source,
            "--device",
            "198.51.100.8",
            "--mw-id",
            "MW_TEST_001",
            "--inventory",
            str(inventory),
            "--credentials",
            str(credentials),
            "--connection-settings",
            str(connection_settings),
            "--audit-settings",
            str(audit_settings),
        ]
    )

    config = runner.build_config(args)
    runner.validate_configuration(config)
    command = runner.build_capture_command(config)

    assert command[command.index("--source") + 1] == source
    assert command[command.index("--snapshot") + 1] == stage
    assert (
        command[command.index("--connection-settings") + 1]
        == str(connection_settings)
    )
    assert (
        command[command.index("--audit-settings") + 1]
        == str(audit_settings)
    )
    assert "--compare-snapshots" not in command


def test_snapshot_runner_rejects_compare_stage() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args(
            [
                "--stage",
                "compare",
                "--mw-id",
                "MW_BAD_001",
            ]
        )


def test_snapshot_dry_run_does_not_execute_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(runner.subprocess, "run", fail_if_called)

    assert runner.run_command(
        ["python", "main.py"],
        dry_run=True,
    ) == 0


def test_missing_inventory_returns_clean_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = runner.main(
        [
            "--stage",
            "before",
            "--source",
            "ssh",
            "--device",
            "198.51.100.8",
            "--mw-id",
            "MW_MISSING_001",
            "--inventory",
            str(tmp_path / "missing_devices.txt"),
            "--credentials",
            str(tmp_path / "missing_credentials.json"),
            "--connection-settings",
            str(tmp_path / "missing_connection_settings.json"),
            "--audit-settings",
            str(tmp_path / "missing_audit_settings.json"),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Error: Inventory does not exist:" in captured.err
    assert "Traceback" not in captured.err
