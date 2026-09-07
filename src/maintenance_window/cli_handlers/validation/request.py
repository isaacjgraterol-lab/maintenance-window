"""Resolve and validate inputs for the standard validation flow."""

from __future__ import annotations

import argparse
from pathlib import Path

from maintenance_window.core.models import Device
from maintenance_window.core.path_safety import validate_mw_id
from maintenance_window.core.settings import load_runtime_settings
from maintenance_window.cli_handlers.validation.defaults import (
    PROJECT_ROOT,
)


def validate_validation_request(args: argparse.Namespace) -> None:
    """Validate requirements shared by every standard validation source."""
    if args.source is None:
        raise ValueError(
            "--source is required unless comparison mode is used."
        )

    if args.snapshot and not args.mw_id:
        raise ValueError("--mw-id is required when --snapshot is used.")
    if args.snapshot:
        args.mw_id = validate_mw_id(args.mw_id)

    workers = getattr(args, "workers", 1)
    if workers is None:
        args.workers = 1
        workers = 1

    if workers < 1 or workers > 50:
        raise ValueError("--workers must be between 1 and 50.")


def load_protocol_runtime_settings(
    args: argparse.Namespace,
) -> dict[str, object]:
    """Load split connection and protocol audit settings."""
    connection_path = Path(args.connection_settings).resolve()
    audit_path = getattr(args, "audit_settings", None)
    protocol = str(args.protocol).strip().lower()

    if audit_path is None:
        audit_path = (
            PROJECT_ROOT
            / "config"
            / "audits"
            / protocol
            / "state.json"
        )

    return load_runtime_settings(
        protocol=protocol,
        connection_path=connection_path,
        audit_path=Path(audit_path).resolve(),
    )


def resolve_devices(
    device_selector: str,
    devices: dict[str, Device],
) -> list[Device]:
    """Resolve one, many, or all inventory devices by management address."""
    selector = device_selector.strip()

    if selector.lower() == "all":
        return list(devices.values())

    requested = [
        item.strip()
        for item in selector.split(",")
        if item.strip()
    ]

    if not requested:
        raise ValueError("Device selector cannot be empty.")

    missing = sorted(
        address
        for address in requested
        if address not in devices
    )

    if missing:
        raise ValueError(
            "Device(s) not found in inventory: "
            + ", ".join(missing)
        )

    return [devices[address] for address in requested]
