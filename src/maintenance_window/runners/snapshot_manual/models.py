"""Data models for manual snapshot capture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SnapshotManualRunnerConfig:
    """Resolved configuration for one JSON or XML snapshot capture."""

    protocol: str
    stage: str
    input_type: str
    input_format: str
    device: str
    mw_id: str
    input_file: Path
    local_db: Path
    session_filter: str
    dry_run: bool
