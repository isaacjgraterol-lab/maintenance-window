"""CLI arguments for automatic snapshot capture."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from maintenance_window.runners.snapshot_capture.config import (
    IMPLEMENTED_PROTOCOLS,
    LIVE_SOURCES,
    VALID_STAGES,
)


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse automatic snapshot capture arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Capture one automatic BGP BEFORE or AFTER snapshot. "
            "This runner never compares snapshots."
        )
    )

    parser.add_argument(
        "--stage",
        choices=sorted(VALID_STAGES),
        required=True,
        help="Snapshot stage to capture: before or after.",
    )
    parser.add_argument(
        "--protocol",
        choices=sorted(IMPLEMENTED_PROTOCOLS),
        default="bgp",
        help="Protocol workflow.",
    )
    parser.add_argument(
        "--source",
        choices=sorted(LIVE_SOURCES),
        default="auto",
        help="Live source: auto, pyez, ssh, or gnmic.",
    )
    parser.add_argument(
        "--device",
        default="all",
        help="Device IP, comma-separated IPs, or all.",
    )
    parser.add_argument(
        "--mw-id",
        required=True,
        help="Unique Maintenance Window identifier.",
    )
    parser.add_argument(
        "--filter",
        dest="session_filter",
        choices=("all", "healthy", "unhealthy"),
        default="all",
        help="BGP session filter used during collection.",
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("inventory/devices.txt"),
        help="Device inventory path.",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("auth/credentials.json"),
        help="Credentials JSON path.",
    )
    parser.add_argument(
        "--connection-settings",
        dest="connection_settings",
        type=Path,
        default=Path("config/connections/settings.json"),
        help="Connection adapter settings JSON path.",
    )
    parser.add_argument(
        "--audit-settings",
        type=Path,
        help=(
            "Protocol audit settings JSON path. When omitted, "
            "config/audits/<protocol>/state.json is used."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the child command without executing it.",
    )

    return parser.parse_args(argv)
