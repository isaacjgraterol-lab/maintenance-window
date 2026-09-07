"""
Requested Maintenance Window snapshot comparison runner.

This executable reads and compares snapshots that already exist. It does
not connect to devices, collect raw data, or invoke any collector.

Example:
    python runners/snapshot_comparison/__init__.py \
        --protocol bgp \
        --mw-id MW_CORE_001 \
        --device all
"""

from __future__ import annotations

import sys
from typing import Sequence

from maintenance_window.runners.snapshot_comparison.arguments import (
    parse_args,
)
from maintenance_window.runners.snapshot_comparison.commands import (
    MAIN_FILE,
    PYTHON,
    build_compare_command,
)
from maintenance_window.runners.snapshot_comparison.config import (
    IMPLEMENTED_PROTOCOLS,
    PROJECT_ROOT,
    build_config,
    resolve_project_path,
    validate_configuration,
)
from maintenance_window.runners.snapshot_comparison.execution import (
    print_configuration,
    run_command,
    run_flow,
    subprocess,
)
from maintenance_window.runners.snapshot_comparison.models import (
    SnapshotComparisonConfig,
)


__all__ = [
    "IMPLEMENTED_PROTOCOLS",
    "MAIN_FILE",
    "PROJECT_ROOT",
    "PYTHON",
    "SnapshotComparisonConfig",
    "build_compare_command",
    "build_config",
    "main",
    "parse_args",
    "print_configuration",
    "resolve_project_path",
    "run_command",
    "run_flow",
    "subprocess",
    "validate_configuration",
]


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Parse, validate, and run one requested comparison."""
    try:
        args = parse_args(argv)
        config = build_config(args)
        validate_configuration(config)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_flow(config)


if __name__ == "__main__":
    raise SystemExit(main())
