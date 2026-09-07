from __future__ import annotations

import pytest

from maintenance_window.runners import snapshot_comparison as runner


def test_compare_command_uses_existing_snapshots_only() -> None:
    args = runner.parse_args(
        [
            "--protocol",
            "bgp",
            "--mw-id",
            "MW_COMPARE_001",
            "--device",
            "all",
        ]
    )

    config = runner.build_config(args)
    runner.validate_configuration(config)
    command = runner.build_compare_command(config)

    assert "--compare-snapshots" in command
    assert command[
        command.index("--compare-snapshots") + 1
    ] == "before,after"
    assert "--source" not in command
    assert "--snapshot" not in command
    assert "--inventory" not in command
    assert "--credentials" not in command
    assert "--settings" not in command


def test_comparison_rejects_same_stage() -> None:
    args = runner.parse_args(
        [
            "--mw-id",
            "MW_BAD_COMPARE",
            "--before-stage",
            "before",
            "--after-stage",
            "before",
        ]
    )

    config = runner.build_config(args)

    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        runner.validate_configuration(config)


def test_comparison_dry_run_does_not_execute_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(runner.subprocess, "run", fail_if_called)

    assert runner.run_command(
        ["python", "main.py"],
        dry_run=True,
    ) == 0
