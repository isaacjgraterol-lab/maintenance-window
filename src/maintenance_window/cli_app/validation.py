"""Cross-mode CLI validation rules."""

from __future__ import annotations

import argparse


def validate_mode_selection(args: argparse.Namespace) -> None:
    """Reject combinations that select incompatible execution modes."""
    if args.compare_source and args.compare_snapshots:
        raise ValueError(
            "Use either --compare-source or --compare-snapshots, not both."
        )
