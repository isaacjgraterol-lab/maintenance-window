from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maintenance_window.protocols.bgp.snapshot_comparison.snapshots import (
    BgpSnapshot,
    BgpSnapshotComparison,
)


@dataclass(frozen=True, slots=True)
class SnapshotComparisonRequest:
    """Normalized CLI request for one BGP snapshot comparison run."""

    mw_id: str
    before_stage: str
    after_stage: str
    device_names: list[str]
    export_path: Path | None
    module: str = "state"
    output: str = "summary"


@dataclass(frozen=True, slots=True)
class SnapshotDeviceComparison:
    """Comparison artifacts for one device."""

    device_name: str
    comparison: BgpSnapshotComparison
    before_snapshot: BgpSnapshot
    after_snapshot: BgpSnapshot
    report: dict[str, object]
