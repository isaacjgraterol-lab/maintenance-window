from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.runners import snapshot_manual as runner


def create_input(
    tmp_path: Path,
    filename: str,
) -> Path:
    input_file = tmp_path / filename
    input_file.write_text("{}", encoding="utf-8")
    return input_file


@pytest.mark.parametrize(
    ("stage", "filename", "input_format"),
    [
        ("before", "MX204_06.json", "json-file"),
        ("after", "MX204_06.json", "json-file"),
        ("before", "MX204_06.xml", "xml-file"),
        ("after", "MX204_06.xml", "xml-file"),
    ],
)
def test_manual_command_uses_requested_stage_and_format(
    tmp_path: Path,
    stage: str,
    filename: str,
    input_format: str,
) -> None:
    input_file = create_input(tmp_path, filename)

    args = runner.parse_args(
        [
            "--stage",
            stage,
            "--mw-id",
            "MW_MANUAL_001",
            "--input",
            str(input_file),
        ]
    )

    config = runner.build_config(args)
    runner.validate_configuration(config)
    command = runner.build_manual_snapshot_command(config)

    assert command[command.index("--snapshot") + 1] == stage
    assert command[command.index("--input-format") + 1] == input_format
    assert command[command.index("--device") + 1] == "MX204_06"
    assert command[command.index("--source") + 1] == "manual"
    assert "--compare-snapshots" not in command
    assert "--list-manual-db" not in command


def test_dry_run_does_not_execute_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(runner.subprocess, "run", fail_if_called)

    assert runner.run_command(
        ["python", "main.py"],
        dry_run=True,
    ) == 0


def test_missing_input_returns_clean_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = runner.main(
        [
            "--stage",
            "before",
            "--mw-id",
            "MW_MISSING_MANUAL",
            "--input",
            str(tmp_path / "missing.json"),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Error: Manual input does not exist:" in captured.err
    assert "Traceback" not in captured.err
