"""Argument parser construction for the Maintenance Window CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from maintenance_window.cli_app.defaults import (
    DEFAULT_CONNECTION_SETTINGS,
    DEFAULT_CREDENTIALS,
    DEFAULT_INVENTORY,
    DEFAULT_LOCAL_DB,
    IMPLEMENTED_PROTOCOLS,
    INPUT_FORMAT_CHOICES,
    SNAPSHOT_CHOICES,
    SOURCE_CHOICES,
)
from maintenance_window.protocols.bgp.state.filters import VALID_FILTERS


def build_parser() -> argparse.ArgumentParser:
    """Build the public Maintenance Window command-line parser."""
    parser = argparse.ArgumentParser(
        description="Maintenance Window protocol validation"
    )

    parser.add_argument(
        "--protocol",
        choices=sorted(IMPLEMENTED_PROTOCOLS),
        default="bgp",
        help="Protocol module to run.",
    )

    parser.add_argument(
        "--module",
        choices=("state", "session-health", "full"),
        default="state",
        help=(
            "Protocol validation module. "
            "state keeps the current BGP state behavior. "
            "session-health compares uptime, flap count, and peer prefix "
            "counters from before/after snapshot raw files."
        ),
    )

    parser.add_argument(
        "--source",
        choices=SOURCE_CHOICES,
        help=(
            "Collection source. Required for normal validation. "
            "Use manual for local DB manual JSON/XML uploads. "
            "Not used with source or snapshot comparison."
        ),
    )

    parser.add_argument(
        "--compare-source",
        "--compare",
        dest="compare_source",
        help=(
            "Compare two live BGP collection sources. "
            "Examples: ssh,gnmic | ssh,pyez | pyez,gnmic"
        ),
    )

    parser.add_argument(
        "--snapshot",
        choices=SNAPSHOT_CHOICES,
        help=(
            "Save a BGP snapshot for a maintenance window stage. "
            "Requires --mw-id."
        ),
    )

    parser.add_argument(
        "--compare-snapshots",
        help=(
            "Compare two BGP snapshot stages. "
            "Example: before,after. Requires --mw-id."
        ),
    )

    parser.add_argument(
        "--mw-id",
        help="Maintenance Window identifier used for snapshots.",
    )

    parser.add_argument(
        "--device",
        help="Device IP, comma-separated IPs, all, or Manual Input.",
    )

    parser.add_argument(
        "--input",
        type=Path,
        help="JSON or XML input file.",
    )

    parser.add_argument(
        "--input-format",
        choices=INPUT_FORMAT_CHOICES,
        help=(
            "Input format for --source manual. "
            "If omitted, format is detected from .json or .xml extension."
        ),
    )

    parser.add_argument(
        "--filter",
        choices=sorted(VALID_FILTERS),
        default="all",
        help="Session filter: healthy, unhealthy, or all.",
    )

    parser.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help="Path to device inventory TXT file.",
    )

    parser.add_argument(
        "--credentials",
        type=Path,
        default=DEFAULT_CREDENTIALS,
        help="Path to credentials JSON file.",
    )

    parser.add_argument(
        "--auth-backend",
        choices=("auto", "local", "radius"),
        default="auto",
        help=(
            "Credential backend selector for live collection. "
            "auto uses the configured profile order; local and radius "
            "force profiles with that authentication_backend."
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Maximum number of live devices to collect in parallel. "
            "Allowed range: 1 to 50. Default: 1."
        ),
    )

    parser.add_argument(
        "--connection-settings",
        dest="connection_settings",
        type=Path,
        default=DEFAULT_CONNECTION_SETTINGS,
        help="Path to connection adapter settings JSON.",
    )

    parser.add_argument(
        "--audit-settings",
        type=Path,
        help=(
            "Path to protocol audit settings JSON. When omitted, "
            "config/audits/<protocol>/state.json is used."
        ),
    )

    parser.add_argument(
        "--local-db",
        type=Path,
        default=DEFAULT_LOCAL_DB,
        help="Path to local SQLite DB for manual uploads.",
    )

    parser.add_argument(
        "--list-manual-db",
        action="store_true",
        help=(
            "List manual JSON/XML uploads stored in the local SQLite DB. "
            "Can be filtered with --protocol, --mw-id, --snapshot, and --device."
        ),
    )

    parser.add_argument(
        "--manual-db-limit",
        type=int,
        default=50,
        help="Maximum number of manual DB rows to list. Default: 50.",
    )

    parser.add_argument(
        "--manual-db-with-unhealthy",
        action="store_true",
        help="List only manual DB rows where unhealthy_sessions > 0.",
    )

    parser.add_argument(
        "--manual-db-with-duplicates",
        action="store_true",
        help="List only manual DB rows where duplicate_entries > 0.",
    )

    parser.add_argument(
        "--output",
        choices=("summary", "detail", "json"),
        default="summary",
        help=(
            "Terminal output mode for standard validation: "
            "summary, detail, or json. Snapshot runs always save "
            "summary.txt, detail.txt, and report.json under the "
            "snapshot stage reports folder."
        ),
    )

    parser.add_argument(
        "--export",
        type=Path,
        help="Optional path to export a JSON report.",
    )

    return parser
