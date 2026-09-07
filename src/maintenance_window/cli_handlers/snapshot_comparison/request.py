from __future__ import annotations

import argparse

from maintenance_window.core.inventory import load_devices
from maintenance_window.core.models import Device
from maintenance_window.core.path_safety import validate_mw_id

from maintenance_window.cli_handlers.snapshot_comparison.models import (
    SnapshotComparisonRequest,
)


def resolve_snapshot_device_names(
    requested: str | None,
    devices: dict[str, Device],
) -> list[str]:
    """Resolve inventory or manual device names for snapshot comparison."""
    if not requested:
        raise ValueError("--device is required for snapshot comparison.")

    if requested.lower() == "all":
        return [
            device.host
            for device in devices.values()
        ]

    return [
        item.strip()
        for item in requested.split(",")
        if item.strip()
    ]


def parse_snapshot_compare_argument(
    compare_value: str,
) -> tuple[str, str]:
    """Parse ``--compare-snapshots before,after``."""
    stages = [
        item.strip().lower()
        for item in compare_value.split(",")
        if item.strip()
    ]

    if len(stages) != 2:
        raise ValueError(
            "--compare-snapshots requires exactly two stages. "
            "Example: --compare-snapshots before,after"
        )

    before_stage, after_stage = stages

    if before_stage == after_stage:
        raise ValueError(
            "Snapshot comparison requires two different stages."
        )

    return before_stage, after_stage


def build_snapshot_comparison_request(
    args: argparse.Namespace,
) -> SnapshotComparisonRequest:
    """Validate CLI arguments and normalize one comparison request."""
    if not args.mw_id:
        raise ValueError(
            "--mw-id is required when using --compare-snapshots"
        )

    mw_id = validate_mw_id(args.mw_id)

    before_stage, after_stage = parse_snapshot_compare_argument(
        args.compare_snapshots
    )

    devices = load_devices(args.inventory.resolve())
    device_names = resolve_snapshot_device_names(
        args.device,
        devices,
    )

    export_path = (
        args.export.resolve()
        if args.export
        else None
    )

    return SnapshotComparisonRequest(
        mw_id=mw_id,
        before_stage=before_stage,
        after_stage=after_stage,
        device_names=device_names,
        export_path=export_path,
        module=getattr(args, "module", "state"),
        output=getattr(args, "output", "summary"),
    )
