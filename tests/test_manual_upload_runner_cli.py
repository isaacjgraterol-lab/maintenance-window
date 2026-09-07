from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

import pytest

from maintenance_window.runners import snapshot_manual as runner


def test_legacy_manual_upload_entrypoint_is_removed() -> None:
    assert find_spec("maintenance_window.runners_manual_upload") is None


def test_official_manual_runner_uses_one_uploaded_file(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "MX204_06.json"
    input_file.write_text("{}", encoding="utf-8")

    args = runner.parse_args(
        [
            "--stage",
            "before",
            "--input",
            str(input_file),
            "--mw-id",
            "MW_JSON_001",
        ]
    )

    config = runner.build_config(args)
    runner.validate_configuration(config)
    command = runner.build_manual_snapshot_command(config)

    assert config.device == "MX204_06"
    assert config.input_type == "json"
    assert config.input_format == "json-file"
    assert command[command.index("--snapshot") + 1] == "before"
    assert command[command.index("--source") + 1] == "manual"
    assert "--compare-snapshots" not in command
    assert "--list-manual-db" not in command


def test_legacy_manual_arguments_are_rejected(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "MX204_06.json"
    input_file.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit):
        runner.parse_args(
            [
                "--stage",
                "before",
                "--input",
                str(input_file),
                "--mw-id",
                "MW_JSON_001",
                "--device",
                "legacy-device",
            ]
        )
