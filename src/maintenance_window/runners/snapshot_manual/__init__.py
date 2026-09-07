"""
Manual Maintenance Window snapshot capture runner.

This executable creates one BEFORE or AFTER snapshot from a JSON or XML file.
The device is inferred from the filename. It does not compare snapshots and it
does not list database rows.

Examples:
    python -m maintenance_window.runners_snapshot_manual \
        --stage before \
        --input .\\inputs\\manual\\uploads\\MX204_06.json \
        --mw-id MW_MX204_06_001

    python -m maintenance_window.runners_snapshot_manual \
        --stage after \
        --input .\\inputs\\manual\\uploads\\MX204_06.xml \
        --mw-id MW_MX204_06_001
"""

from __future__ import annotations

import sys
from typing import Sequence

from maintenance_window.runners.snapshot_manual.arguments import parse_args
from maintenance_window.runners.snapshot_manual.commands import (
    MAIN_FILE,
    PYTHON,
    build_manual_snapshot_command,
)
from maintenance_window.runners.snapshot_manual.config import (
    IMPLEMENTED_PROTOCOLS,
    INPUT_FORMAT_BY_EXTENSION,
    PROJECT_ROOT,
    VALID_STAGES,
    build_config,
    infer_device_from_filename,
    infer_input_metadata,
    resolve_project_path,
    validate_configuration,
    validate_input_file,
)
from maintenance_window.runners.snapshot_manual.execution import (
    print_configuration,
    run_command,
    run_flow,
    subprocess,
)
from maintenance_window.runners.snapshot_manual.models import (
    SnapshotManualRunnerConfig,
)


__all__ = [
    "IMPLEMENTED_PROTOCOLS",
    "INPUT_FORMAT_BY_EXTENSION",
    "MAIN_FILE",
    "PROJECT_ROOT",
    "PYTHON",
    "SnapshotManualRunnerConfig",
    "VALID_STAGES",
    "build_config",
    "build_manual_snapshot_command",
    "infer_device_from_filename",
    "infer_input_metadata",
    "main",
    "parse_args",
    "print_configuration",
    "resolve_project_path",
    "run_command",
    "run_flow",
    "subprocess",
    "validate_configuration",
    "validate_input_file",
]


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Parse, validate, and run one manual snapshot capture."""
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
