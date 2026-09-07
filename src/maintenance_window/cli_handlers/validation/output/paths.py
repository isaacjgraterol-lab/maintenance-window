"""Path helpers for validation reports saved under snapshot stages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from maintenance_window.core.path_safety import safe_path_part


@dataclass(frozen=True, slots=True)
class SnapshotValidationReportPaths:
    """Concrete files produced for one snapshot validation run."""

    root: Path
    summary: Path
    detail: Path
    json: Path

    def as_dict(self) -> dict[str, Path]:
        """Return files keyed by report mode."""
        return {
            "summary": self.summary,
            "detail": self.detail,
            "json": self.json,
        }


def timestamp_utc() -> str:
    """Return a UTC timestamp suitable for one report directory."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def build_snapshot_validation_report_paths(
    *,
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    timestamp: str | None = None,
) -> SnapshotValidationReportPaths:
    """Build outputs/snapshots/bgp/<mw-id>/<stage>/reports/<timestamp>."""
    report_root = (
        snapshot_root
        / safe_path_part(mw_id)
        / safe_path_part(stage)
        / "reports"
        / (timestamp or timestamp_utc())
    )
    return SnapshotValidationReportPaths(
        root=report_root,
        summary=report_root / "summary.txt",
        detail=report_root / "detail.txt",
        json=report_root / "report.json",
    )
