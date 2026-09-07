from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from maintenance_window.engine.manual.execution import store_manual_upload
from maintenance_window.protocols.bgp.manual_workflow.models import (
    ManualBgpUploadResult,
)


def store_manual_bgp_upload(
    *,
    input_file: Path,
    input_format: str | None,
    db_path: Path,
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
    raw_root: Path | None,
    detect_input_format_fn: Callable[..., str],
    archive_raw_evidence_fn: Callable[..., Any],
    parse_input_file_fn: Callable[..., Any],
    write_bgp_snapshot_fn: Callable[..., Path],
    patch_snapshot_metadata_fn: Callable[..., dict[str, Any]],
    insert_manual_output_fn: Callable[..., int],
    default_raw_root_fn: Callable[[Path], Path],
) -> ManualBgpUploadResult:
    """Archive, parse, snapshot, and persist one manual BGP upload."""
    return store_manual_upload(
        protocol="bgp",
        input_file=input_file,
        input_format=input_format,
        db_path=db_path,
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
        raw_root=raw_root,
        detect_input_format_fn=detect_input_format_fn,
        archive_raw_evidence_fn=archive_raw_evidence_fn,
        parse_input_file_fn=parse_input_file_fn,
        write_snapshot_fn=write_bgp_snapshot_fn,
        patch_snapshot_metadata_fn=patch_snapshot_metadata_fn,
        insert_manual_output_fn=insert_manual_output_fn,
        default_raw_root_fn=default_raw_root_fn,
        result_builder=ManualBgpUploadResult,
        snapshot_items_arg="sessions",
        result_items_arg="sessions",
    )
