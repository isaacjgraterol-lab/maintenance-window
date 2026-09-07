"""Persist validation output reports for snapshot runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maintenance_window.cli_handlers.validation.output.detail import (
    render_detail_report,
)
from maintenance_window.cli_handlers.validation.output.paths import (
    SnapshotValidationReportPaths,
    build_snapshot_validation_report_paths,
)
from maintenance_window.cli_handlers.validation.output.summary import (
    render_summary_report,
)


def build_report_paths_for_snapshot_run(
    *,
    snapshot_root: Path,
    mw_id: str | None,
    stage: str | None,
) -> SnapshotValidationReportPaths | None:
    """Return report paths only when the command is a snapshot run."""
    if not mw_id or not stage:
        return None
    return build_snapshot_validation_report_paths(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
    )


def write_snapshot_validation_reports(
    *,
    paths: SnapshotValidationReportPaths,
    payload: dict[str, Any],
) -> dict[str, Path]:
    """Write summary.txt, detail.txt, and report.json."""
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.summary.write_text(render_summary_report(payload), encoding="utf-8")
    paths.detail.write_text(render_detail_report(payload), encoding="utf-8")
    paths.json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths.as_dict()
