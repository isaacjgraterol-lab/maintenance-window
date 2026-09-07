"""Configuration for manual JSON/XML snapshot capture."""

from __future__ import annotations

import argparse
from pathlib import Path

from maintenance_window.core.path_safety import validate_mw_id

from maintenance_window.runners.snapshot_manual.models import (
    SnapshotManualRunnerConfig,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

VALID_STAGES = {
    "before",
    "after",
}

IMPLEMENTED_PROTOCOLS = {
    "bgp",
}

INPUT_FORMAT_BY_EXTENSION = {
    ".json": ("json", "json-file"),
    ".xml": ("xml", "xml-file"),
}


def resolve_project_path(path: Path) -> Path:
    """Resolve a path relative to the project root."""
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def infer_device_from_filename(path: Path) -> str:
    """Infer the device name from the uploaded filename."""
    device = path.stem.strip()

    if not device:
        raise ValueError(
            f"Unable to infer device from input filename: {path.name}"
        )

    return device


def infer_input_metadata(path: Path) -> tuple[str, str]:
    """Infer input type and CLI input format from the file extension."""
    suffix = path.suffix.lower()

    try:
        return INPUT_FORMAT_BY_EXTENSION[suffix]
    except KeyError as exc:
        supported = ", ".join(sorted(INPUT_FORMAT_BY_EXTENSION))
        raise ValueError(
            f"Unsupported manual input extension {suffix!r}. "
            f"Supported extensions: {supported}"
        ) from exc


def build_config(
    args: argparse.Namespace,
) -> SnapshotManualRunnerConfig:
    """Resolve parsed arguments into an immutable config."""
    input_file = resolve_project_path(args.input)
    input_type, input_format = infer_input_metadata(input_file)

    return SnapshotManualRunnerConfig(
        protocol=args.protocol.strip().lower(),
        stage=args.stage.strip().lower(),
        input_type=input_type,
        input_format=input_format,
        device=infer_device_from_filename(input_file),
        mw_id=args.mw_id.strip(),
        input_file=input_file,
        local_db=resolve_project_path(args.local_db),
        session_filter=args.session_filter,
        dry_run=args.dry_run,
    )


def validate_input_file(path: Path) -> None:
    """Validate the manual source file."""
    if not path.exists():
        raise FileNotFoundError(
            f"Manual input does not exist: {path}"
        )

    if not path.is_file():
        raise FileNotFoundError(
            f"Manual input is not a file: {path}"
        )

    infer_input_metadata(path)


def validate_configuration(
    config: SnapshotManualRunnerConfig,
) -> None:
    """Validate one manual protocol-state snapshot capture."""
    if config.protocol not in IMPLEMENTED_PROTOCOLS:
        raise ValueError(
            f"Protocol {config.protocol!r} is not implemented."
        )

    if config.stage not in VALID_STAGES:
        raise ValueError(
            f"Invalid stage={config.stage!r}. "
            f"Valid stages: {sorted(VALID_STAGES)}"
        )

    if not config.device:
        raise ValueError("Device cannot be empty.")

    if not config.mw_id:
        raise ValueError("MW ID cannot be empty.")
    validate_mw_id(config.mw_id)

    validate_input_file(config.input_file)
