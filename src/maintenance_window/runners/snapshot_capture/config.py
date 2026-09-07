"""Configuration and validation for automatic snapshot capture."""

from __future__ import annotations

import argparse
from pathlib import Path

from maintenance_window.core.path_safety import validate_mw_id

from maintenance_window.runners.snapshot_capture.models import SnapshotRunnerConfig


PROJECT_ROOT = Path(__file__).resolve().parents[3]

VALID_STAGES = {
    "before",
    "after",
}

IMPLEMENTED_PROTOCOLS = {
    "bgp",
}

LIVE_SOURCES = {
    "auto",
    "pyez",
    "ssh",
    "gnmic",
}


def resolve_project_path(path: Path) -> Path:
    """Resolve a relative path from the project root."""
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def build_config(
    args: argparse.Namespace,
) -> SnapshotRunnerConfig:
    """Resolve parsed CLI arguments into an immutable config."""
    protocol = args.protocol.strip().lower()
    raw_connection_settings = args.connection_settings
    raw_audit_settings = getattr(args, "audit_settings", None)

    audit_settings = (
        raw_audit_settings
        if raw_audit_settings is not None
        else Path("config") / "audits" / protocol / "state.json"
    )

    return SnapshotRunnerConfig(
        protocol=protocol,
        stage=args.stage.strip().lower(),
        source=args.source.strip().lower(),
        device=args.device.strip(),
        mw_id=args.mw_id.strip(),
        session_filter=args.session_filter,
        inventory=resolve_project_path(args.inventory),
        credentials=resolve_project_path(args.credentials),
        connection_settings=resolve_project_path(raw_connection_settings),
        audit_settings=resolve_project_path(audit_settings),
        dry_run=args.dry_run,
    )


def validate_file_exists(
    path: Path,
    label: str,
) -> None:
    """Validate a required regular file."""
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")

    if not path.is_file():
        raise FileNotFoundError(f"{label} is not a file: {path}")


def validate_configuration(
    config: SnapshotRunnerConfig,
) -> None:
    """Validate an automatic snapshot capture configuration."""
    if config.stage not in VALID_STAGES:
        raise ValueError(
            f"Invalid stage={config.stage!r}. "
            f"Valid stages: {sorted(VALID_STAGES)}"
        )

    if config.protocol not in IMPLEMENTED_PROTOCOLS:
        raise ValueError(
            f"Protocol {config.protocol!r} is not implemented. "
            f"Implemented protocols: {sorted(IMPLEMENTED_PROTOCOLS)}"
        )

    if config.source not in LIVE_SOURCES:
        raise ValueError(
            f"Invalid source={config.source!r}. "
            f"Valid sources: {sorted(LIVE_SOURCES)}"
        )

    if not config.mw_id:
        raise ValueError("MW ID cannot be empty.")
    validate_mw_id(config.mw_id)

    if not config.device:
        raise ValueError("Device selector cannot be empty.")

    validate_file_exists(config.inventory, "Inventory")
    validate_file_exists(config.credentials, "Credentials")
    validate_file_exists(
        config.connection_settings,
        "Connection settings",
    )
    validate_file_exists(
        config.audit_settings,
        "Audit settings",
    )
