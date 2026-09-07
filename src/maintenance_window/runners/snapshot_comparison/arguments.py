"""CLI arguments for requested snapshot comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from maintenance_window.runners.snapshot_comparison.config import (
    IMPLEMENTED_PROTOCOLS,
)


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse snapshot comparison arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare existing normalized snapshots. "
            "This runner never connects to network devices."
        )
    )

    parser.add_argument(
        "--protocol",
        choices=sorted(IMPLEMENTED_PROTOCOLS),
        default="bgp",
        help="Protocol workflow.",
    )
    parser.add_argument(
        "--mw-id",
        required=True,
        help="Maintenance Window identifier containing the snapshots.",
    )
    parser.add_argument(
        "--device",
        default="all",
        help="Device selector or all.",
    )
    parser.add_argument(
        "--before-stage",
        default="before",
        help="Baseline snapshot stage.",
    )
    parser.add_argument(
        "--after-stage",
        default="after",
        help="Candidate snapshot stage.",
    )
    parser.add_argument(
        "--export",
        type=Path,
        help="Optional comparison report path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the command without executing it.",
    )

    return parser.parse_args(argv)
