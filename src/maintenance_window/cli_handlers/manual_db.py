"""
CLI handler for manual DB listing.

Purpose:
    Keep manual DB listing and table output out of cli.py.

Rules:
    - Do not parse protocol data here.
    - Do not upload manual JSON/XML here.
    - Do not implement SQLite schema here.
    - This handler only translates CLI args into a local DB query and prints rows.
"""

from __future__ import annotations

import argparse
from typing import Any

from maintenance_window.core.local_db import list_manual_outputs


def _format_manual_db_table_value(value: object, width: int) -> str:
    """
    Format one table cell for manual DB listing.

    Values longer than the configured width are truncated.
    Column headers are configured with enough width to stay readable.
    """
    text = str(value)

    if len(text) > width:
        return text[: max(width - 3, 1)] + "..."

    return text.ljust(width)


def _print_manual_db_rows(rows: list[dict[str, Any]]) -> None:
    """
    Print manual DB rows as a readable fixed-width table.

    The displayed labels are intentionally shorter than the DB column names
    where needed, but the values still come from the real DB fields.
    """
    if not rows:
        print("No manual DB rows found.")
        return

    columns = [
        ("id", "id", 4),
        ("protocol", "protocol", 8),
        ("mw_id", "mw_id", 24),
        ("stage", "stage", 7),
        ("device", "device", 20),
        ("input_format", "input_format", 12),
        ("total", "total_sessions", 5),
        ("unique", "unique_sessions", 6),
        ("duplicates", "duplicate_entries", 10),
        ("unhealthy", "unhealthy_sessions", 9),
        ("created_at", "created_at", 25),
    ]

    header = "  ".join(
        _format_manual_db_table_value(label, width)
        for label, _, width in columns
    )
    separator = "  ".join("-" * width for _, _, width in columns)

    print(header)
    print(separator)

    for row in rows:
        print(
            "  ".join(
                _format_manual_db_table_value(row.get(key, ""), width)
                for _, key, width in columns
            )
        )


def run_manual_db_listing(args: argparse.Namespace) -> int:
    """
    List manual JSON/XML uploads stored in the local SQLite DB.

    Filters:
        --protocol
        --mw-id
        --snapshot before|after
        --device
        --manual-db-with-unhealthy
        --manual-db-with-duplicates
        --manual-db-limit
    """
    device_filter = args.device

    if device_filter and device_filter.lower() == "all":
        device_filter = None

    rows = list_manual_outputs(
        db_path=args.local_db.resolve(),
        protocol=args.protocol,
        mw_id=args.mw_id,
        stage=args.snapshot,
        device=device_filter,
        with_unhealthy=args.manual_db_with_unhealthy,
        with_duplicates=args.manual_db_with_duplicates,
        limit=args.manual_db_limit,
    )

    print(f"Manual DB: {args.local_db.resolve()}")
    print(f"Rows found: {len(rows)}\n")

    _print_manual_db_rows(rows)

    return 0
