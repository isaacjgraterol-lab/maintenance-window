"""Data models for requested snapshot comparison."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SnapshotComparisonConfig:
    """Resolved configuration for one snapshot comparison."""

    protocol: str
    mw_id: str
    device: str
    before_stage: str
    after_stage: str
    export_report: Path
    dry_run: bool
