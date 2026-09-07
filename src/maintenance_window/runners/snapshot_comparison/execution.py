"""Execution for requested snapshot comparison."""

from __future__ import annotations

import subprocess

from maintenance_window.runners.snapshot_comparison.commands import (
    build_compare_command,
)
from maintenance_window.runners.snapshot_comparison.config import (
    PROJECT_ROOT,
)
from maintenance_window.runners.snapshot_comparison.models import (
    SnapshotComparisonConfig,
)


def print_configuration(
    config: SnapshotComparisonConfig,
) -> None:
    """Print the resolved comparison configuration."""
    print("\nMaintenance Window snapshot comparison runner")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Protocol: {config.protocol}")
    print(f"MW ID: {config.mw_id}")
    print(f"Device selector: {config.device}")
    print(f"Before stage: {config.before_stage}")
    print(f"After stage: {config.after_stage}")
    print(f"Export report: {config.export_report}")
    print(f"Dry run: {config.dry_run}")
    print("Network collection: disabled in this runner")


def run_command(
    command: list[str],
    dry_run: bool,
) -> int:
    """Execute one comparison command."""
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
    config: SnapshotComparisonConfig,
) -> int:
    """Run one explicitly requested snapshot comparison."""
    config.export_report.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_configuration(config)

    exit_code = run_command(
        build_compare_command(config),
        config.dry_run,
    )

    print(f"\nSnapshot comparison final exit code: {exit_code}")

    return exit_code
