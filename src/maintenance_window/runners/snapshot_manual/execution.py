"""Execution orchestration for manual snapshot capture."""

from __future__ import annotations

import subprocess

from maintenance_window.runners.snapshot_manual.commands import (
    build_manual_snapshot_command,
)
from maintenance_window.runners.snapshot_manual.config import (
    PROJECT_ROOT,
)
from maintenance_window.runners.snapshot_manual.models import (
    SnapshotManualRunnerConfig,
)


def print_configuration(
    config: SnapshotManualRunnerConfig,
) -> None:
    """Print the resolved manual snapshot configuration."""
    print("\nMaintenance Window manual snapshot runner")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Stage: {config.stage}")
    print(f"Protocol: {config.protocol}")
    print(f"Input type: {config.input_type}")
    print(f"Input format: {config.input_format}")
    print(f"Device: {config.device}")
    print(f"MW ID: {config.mw_id}")
    print(f"Input file: {config.input_file}")
    print(f"Local DB: {config.local_db}")
    print(f"Filter: {config.session_filter}")
    print(f"Dry run: {config.dry_run}")
    print("Comparison: disabled in this runner")
    print("DB listing: disabled in this runner")


def run_command(
    command: list[str],
    dry_run: bool,
) -> int:
    """Execute one manual snapshot command."""
    print("\nCommand:")
    print(" ".join(command))
    print()

    if dry_run:
        print("Dry run: command not executed.")
        print("\nChild process exit code: 0")
        return 0

    completed_process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
    )

    print(
        f"\nChild process exit code: "
        f"{completed_process.returncode}"
    )

    return completed_process.returncode


def run_flow(
    config: SnapshotManualRunnerConfig,
) -> int:
    """Run one requested manual snapshot capture."""
    config.local_db.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_configuration(config)

    exit_code = run_command(
        build_manual_snapshot_command(config),
        config.dry_run,
    )

    print(
        f"\nManual snapshot final exit code: "
        f"{exit_code}"
    )

    return exit_code
