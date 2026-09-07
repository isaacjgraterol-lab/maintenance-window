"""Parse source pairs and resolve selected inventory devices."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from maintenance_window.core.inventory import load_devices
from maintenance_window.core.models import Device
from maintenance_window.cli_handlers.source_comparison.models import (
    SourceComparisonRequest,
)


LoadDevices = Callable[[Path], dict[str, Device]]


def parse_source_compare_argument(compare_value: str) -> tuple[str, str]:
    """Parse and validate ``--compare-source left,right``."""
    parts = [
        part.strip().lower()
        for part in compare_value.split(",")
        if part.strip()
    ]

    if len(parts) != 2:
        raise ValueError(
            "--compare-source must have exactly two sources separated by comma. "
            "Example: --compare-source pyez,gnmic"
        )

    left_source, right_source = parts

    if left_source == right_source:
        raise ValueError(
            "--compare-source must compare two different sources."
        )

    return left_source, right_source


def resolve_devices(
    device_selector: str,
    devices: dict[str, Device],
) -> list[Device]:
    """Resolve one, many, or all devices by inventory management address."""
    selector = device_selector.strip()

    if selector.lower() == "all":
        return list(devices.values())

    requested = {
        item.strip()
        for item in selector.split(",")
        if item.strip()
    }

    if not requested:
        raise ValueError("Device selector cannot be empty.")

    missing = sorted(requested - devices.keys())

    if missing:
        raise ValueError(
            "Device(s) not found in inventory: "
            + ", ".join(missing)
        )

    return [
        devices[host]
        for host in devices
        if host in requested
    ]


def build_source_comparison_request(
    args: argparse.Namespace,
    *,
    load_devices_fn: LoadDevices = load_devices,
) -> SourceComparisonRequest:
    """Normalize source pair, selected devices, and optional export path."""
    left_source, right_source = parse_source_compare_argument(
        args.compare_source
    )
    devices = load_devices_fn(Path(args.inventory).resolve())
    selected_devices = resolve_devices(args.device, devices)
    export_path = Path(args.export).resolve() if args.export else None

    return SourceComparisonRequest(
        left_source=left_source,
        right_source=right_source,
        devices=selected_devices,
        export_path=export_path,
    )
