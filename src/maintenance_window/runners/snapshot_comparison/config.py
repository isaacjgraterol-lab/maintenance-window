"""Configuration for requested snapshot comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

from maintenance_window.core.path_safety import validate_mw_id

from maintenance_window.runners.snapshot_comparison.models import (
    SnapshotComparisonConfig,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

IMPLEMENTED_PROTOCOLS = {
    "bgp",
}


def resolve_project_path(path: Path) -> Path:
    """Resolve a relative path from the project root."""
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def build_config(
    args: argparse.Namespace,
) -> SnapshotComparisonConfig:
    """Resolve CLI arguments into an immutable config."""
    mw_id = validate_mw_id(args.mw_id.strip())
    export_report = (
        resolve_project_path(args.export)
        if args.export is not None
        else (
            PROJECT_ROOT
            / "outputs"
            / "reports"
            / f"{mw_id}_snapshot_before_after.json"
        )
    )

    return SnapshotComparisonConfig(
        protocol=args.protocol.strip().lower(),
        mw_id=mw_id,
        device=args.device.strip(),
        before_stage=args.before_stage.strip().lower(),
        after_stage=args.after_stage.strip().lower(),
        export_report=export_report,
        dry_run=args.dry_run,
    )


def validate_configuration(
    config: SnapshotComparisonConfig,
) -> None:
    """Validate a snapshot comparison configuration."""
    if config.protocol not in IMPLEMENTED_PROTOCOLS:
        raise ValueError(
            f"Protocol {config.protocol!r} is not implemented."
        )

    if not config.mw_id:
        raise ValueError("MW ID cannot be empty.")
    validate_mw_id(config.mw_id)

    if not config.device:
        raise ValueError("Device selector cannot be empty.")

    if not config.before_stage:
        raise ValueError("Before stage cannot be empty.")

    if not config.after_stage:
        raise ValueError("After stage cannot be empty.")

    if config.before_stage == config.after_stage:
        raise ValueError(
            "Before and after stages must be different."
        )
