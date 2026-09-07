"""Data models for automatic snapshot capture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SnapshotRunnerConfig:
    """Resolved configuration for one BEFORE or AFTER capture."""

    protocol: str
    stage: str
    source: str
    device: str
    mw_id: str
    session_filter: str
    inventory: Path
    credentials: Path
    connection_settings: Path
    audit_settings: Path
    dry_run: bool
