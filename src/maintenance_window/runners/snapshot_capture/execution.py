"""Execution orchestration for automatic snapshot capture."""

from __future__ import annotations

import subprocess

from maintenance_window.runners.snapshot_capture.commands import (
    build_capture_command,
)
from maintenance_window.runners.snapshot_capture.config import PROJECT_ROOT
from maintenance_window.runners.snapshot_capture.models import SnapshotRunnerConfig


def print_configuration(
    config: SnapshotRunnerConfig,
) -> None:
    """Print the resolved capture configuration."""
    print("\nMaintenance Window automatic snapshot runner")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Stage: {config.stage}")
    print(f"Protocol: {config.protocol}")
    print(f"Source: {config.source}")
    print(f"Device selector: {config.device}")
    print(f"MW ID: {config.mw_id}")
    print(f"Filter: {config.session_filter}")
    print(f"Inventory: {config.inventory}")
    print(f"Credentials: {config.credentials}")
    print(f"Connection settings: {config.connection_settings}")
    print(f"Audit settings: {config.audit_settings}")
    print(f"Dry run: {config.dry_run}")
    print("Comparison: disabled in this runner")


def run_command(
    command: list[str],
    dry_run: bool,
) -> int:
    """Execute the capture command and return its exit code."""
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
    config: SnapshotRunnerConfig,
) -> int:
    """Run one BEFORE or AFTER automatic capture."""
    print_configuration(config)

    exit_code = run_command(
        build_capture_command(config),
        config.dry_run,
    )

    print(f"\nSnapshot capture final exit code: {exit_code}")

    return exit_code
