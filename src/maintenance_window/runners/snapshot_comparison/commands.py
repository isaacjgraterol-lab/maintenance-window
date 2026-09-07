"""Command builder for requested snapshot comparison."""

from __future__ import annotations

import sys

from maintenance_window.runners.snapshot_comparison.config import (
    PROJECT_ROOT,
)
from maintenance_window.runners.snapshot_comparison.models import (
    SnapshotComparisonConfig,
)


MAIN_FILE = PROJECT_ROOT / "main.py"
PYTHON = sys.executable


def build_compare_command(
    config: SnapshotComparisonConfig,
) -> list[str]:
    """Build a comparison command using existing snapshots only."""
    return [
        PYTHON,
        str(MAIN_FILE),
        "--protocol",
        config.protocol,
        "--compare-snapshots",
        f"{config.before_stage},{config.after_stage}",
        "--mw-id",
        config.mw_id,
        "--device",
        config.device,
        "--export",
        str(config.export_report),
    ]
