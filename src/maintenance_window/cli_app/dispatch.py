"""Dispatch parsed CLI arguments to the selected application handler."""

from __future__ import annotations

import argparse

from maintenance_window.cli_app.validation import validate_mode_selection
from maintenance_window.cli_handlers.manual_db import run_manual_db_listing
from maintenance_window.cli_handlers.snapshot_comparison import (
    run_bgp_snapshot_comparison,
)
from maintenance_window.cli_handlers.source_comparison import (
    run_bgp_source_comparison,
)
from maintenance_window.cli_handlers.validation import run_bgp_validation


def dispatch(args: argparse.Namespace) -> int:
    """Run exactly one CLI flow using the established priority order."""
    validate_mode_selection(args)

    if args.list_manual_db:
        return run_manual_db_listing(args)

    if args.compare_source:
        return run_bgp_source_comparison(args)

    if args.compare_snapshots:
        return run_bgp_snapshot_comparison(args)

    return run_bgp_validation(args)
