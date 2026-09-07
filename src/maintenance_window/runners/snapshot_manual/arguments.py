"""CLI arguments for manual JSON/XML snapshot capture."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from maintenance_window.runners.snapshot_manual.config import (
    IMPLEMENTED_PROTOCOLS,
    VALID_STAGES,
)


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse manual snapshot capture arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create one BEFORE or AFTER protocol-state snapshot from a "
            "JSON or XML file. The device is inferred from the filename "
            "and the input type from its extension. This runner never "
            "compares snapshots."
        )
    )

    parser.add_argument(
        "--stage",
        choices=sorted(VALID_STAGES),
        required=True,
        help="Snapshot stage to create: before or after.",
    )
    parser.add_argument(
        "--protocol",
        choices=sorted(IMPLEMENTED_PROTOCOLS),
        default="bgp",
        help="Protocol selected by the operator.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=(
            "JSON/XML upload path. Name the file with the device hostname, "
            "for example router-a.json."
        ),
    )
    parser.add_argument(
        "--mw-id",
        required=True,
        help="Unique Maintenance Window identifier.",
    )
    parser.add_argument(
        "--local-db",
        type=Path,
        default=Path("data/maintenance_window.sqlite3"),
        help="SQLite database path.",
    )
    parser.add_argument(
        "--filter",
        dest="session_filter",
        choices=("all", "healthy", "unhealthy"),
        default="all",
        help="Protocol-state record filter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the child command without executing it.",
    )

    return parser.parse_args(argv)
