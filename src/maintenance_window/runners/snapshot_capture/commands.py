"""Command builder for automatic snapshot capture."""

from __future__ import annotations

import sys

from maintenance_window.runners.snapshot_capture.config import PROJECT_ROOT
from maintenance_window.runners.snapshot_capture.models import SnapshotRunnerConfig


MAIN_FILE = PROJECT_ROOT / "main.py"
PYTHON = sys.executable


def build_capture_command(
    config: SnapshotRunnerConfig,
) -> list[str]:
    """Build one BEFORE or AFTER live collection command."""
    return [
        PYTHON,
        str(MAIN_FILE),
        "--protocol",
        config.protocol,
        "--source",
        config.source,
        "--device",
        config.device,
        "--filter",
        config.session_filter,
        "--snapshot",
        config.stage,
        "--mw-id",
        config.mw_id,
        "--inventory",
        str(config.inventory),
        "--credentials",
        str(config.credentials),
        "--connection-settings",
        str(config.connection_settings),
        "--audit-settings",
        str(config.audit_settings),
    ]
