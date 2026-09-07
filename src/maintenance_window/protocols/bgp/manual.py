"""
BGP manual upload compatibility facade.

The implementation is split under manual_workflow. This module keeps the
existing import path and facade-level dependencies patchable for tests.
"""

from __future__ import annotations

from pathlib import Path

from maintenance_window.core.local_db import insert_manual_output
from maintenance_window.core.raw_evidence import archive_raw_evidence
from maintenance_window.protocols.bgp.manual_workflow.execution import (
    store_manual_bgp_upload as _execute_manual_bgp_upload,
)
from maintenance_window.protocols.bgp.manual_workflow.input_format import (
    detect_manual_input_format,
)
from maintenance_window.protocols.bgp.manual_workflow.metadata import (
    load_snapshot_json as _load_snapshot_json,
)
from maintenance_window.protocols.bgp.manual_workflow.metadata import (
    patch_manual_snapshot_metadata as _patch_manual_snapshot_metadata,
)
from maintenance_window.protocols.bgp.manual_workflow.metadata import (
    write_snapshot_json as _write_snapshot_json,
)
from maintenance_window.protocols.bgp.manual_workflow.models import (
    ManualBgpUploadResult,
)
from maintenance_window.protocols.bgp.manual_workflow.paths import (
    default_manual_raw_root as _default_manual_raw_root,
)
from maintenance_window.protocols.bgp.service import parse_input_file
from maintenance_window.protocols.bgp.snapshot_comparison.snapshots import write_bgp_snapshot


def store_manual_bgp_upload(
    *,
    input_file: Path,
    input_format: str | None,
    db_path: Path,
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
    raw_root: Path | None = None,
) -> ManualBgpUploadResult:
    """Archive, parse, snapshot, and persist one manual BGP upload."""
    return _execute_manual_bgp_upload(
        input_file=input_file,
        input_format=input_format,
        db_path=db_path,
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
        raw_root=raw_root,
        detect_input_format_fn=detect_manual_input_format,
        archive_raw_evidence_fn=archive_raw_evidence,
        parse_input_file_fn=parse_input_file,
        write_bgp_snapshot_fn=write_bgp_snapshot,
        patch_snapshot_metadata_fn=_patch_manual_snapshot_metadata,
        insert_manual_output_fn=insert_manual_output,
        default_raw_root_fn=_default_manual_raw_root,
    )
