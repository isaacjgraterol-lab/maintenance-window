"""
Automatic Maintenance Window snapshot capture runner.

This executable captures only one BEFORE or AFTER snapshot. It never
performs snapshot comparison.

The child application is responsible for:
    1. Collecting from gNMIc, PyEZ, SSH, or auto selection
    2. Saving the raw response
    3. Parsing the source-specific response
    4. Normalizing the BGP model
    5. Saving the requested snapshot

Example:
    python runners/snapshot_capture/__init__.py \
        --stage before \
        --protocol bgp \
        --source ssh \
        --device all \
        --mw-id MW_CORE_001
"""

from __future__ import annotations

import sys
from typing import Sequence

from maintenance_window.runners.snapshot_capture.arguments import parse_args
from maintenance_window.runners.snapshot_capture.commands import (
    MAIN_FILE,
    PYTHON,
    build_capture_command,
)
from maintenance_window.runners.snapshot_capture.config import (
    IMPLEMENTED_PROTOCOLS,
    LIVE_SOURCES,
    PROJECT_ROOT,
    VALID_STAGES,
    build_config,
    resolve_project_path,
    validate_configuration,
    validate_file_exists,
)
from maintenance_window.runners.snapshot_capture.execution import (
    print_configuration,
    run_command,
    run_flow,
    subprocess,
)
from maintenance_window.runners.snapshot_capture.models import SnapshotRunnerConfig


__all__ = [
    "IMPLEMENTED_PROTOCOLS",
    "LIVE_SOURCES",
    "MAIN_FILE",
    "PROJECT_ROOT",
    "PYTHON",
    "SnapshotRunnerConfig",
    "VALID_STAGES",
    "build_capture_command",
    "build_config",
    "main",
    "parse_args",
    "print_configuration",
    "resolve_project_path",
    "run_command",
    "run_flow",
    "subprocess",
    "validate_configuration",
    "validate_file_exists",
]


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Parse, validate, and run one snapshot capture."""
    try:
        args = parse_args(argv)
        config = build_config(args)
        validate_configuration(config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_flow(config)


if __name__ == "__main__":
    raise SystemExit(main())
