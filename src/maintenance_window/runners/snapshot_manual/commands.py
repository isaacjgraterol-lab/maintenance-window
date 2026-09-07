"""Command builder for manual JSON/XML snapshot capture."""

from __future__ import annotations

import sys

from maintenance_window.runners.snapshot_manual.config import (
    PROJECT_ROOT,
)
from maintenance_window.runners.snapshot_manual.models import (
    SnapshotManualRunnerConfig,
)


MAIN_FILE = PROJECT_ROOT / "main.py"
PYTHON = sys.executable


def build_manual_snapshot_command(
    config: SnapshotManualRunnerConfig,
) -> list[str]:
    """Build one manual BEFORE or AFTER snapshot command."""
    return [
        PYTHON,
        str(MAIN_FILE),
        "--protocol",
        config.protocol,
        "--source",
        "manual",
        "--input",
        str(config.input_file),
        "--device",
        config.device,
        "--snapshot",
        config.stage,
        "--mw-id",
        config.mw_id,
        "--local-db",
        str(config.local_db),
        "--filter",
        config.session_filter,
        "--input-format",
        config.input_format,
    ]
