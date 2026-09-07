from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar


ResultT = TypeVar("ResultT")


def store_manual_upload(
    *,
    protocol: str,
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
    parse_input_file_fn: Callable[..., list[Any]],
    write_snapshot_fn: Callable[..., Path],
    patch_snapshot_metadata_fn: Callable[..., dict[str, Any]],
    insert_manual_output_fn: Callable[..., int],
    default_raw_root_fn: Callable[[Path], Path],
    result_builder: Callable[..., ResultT],
    snapshot_items_arg: str,
    result_items_arg: str,
) -> ResultT:
    """
    Archive a manual upload, parse it, create a snapshot, and persist it.

    Evidence policy:
        - copy operator input to outputs/raw/manual/<protocol>
        - parse the archived copy
        - point snapshot and DB row to the archived copy
        - preserve original input path and SHA-256 in snapshot metadata
    """
    resolved_input_file = input_file.resolve()
    detected_input_format = detect_input_format_fn(
        input_file=resolved_input_file,
        input_format=input_format,
    )

    resolved_raw_root = (
        raw_root.resolve()
        if raw_root is not None
        else default_raw_root_fn(snapshot_root)
    )

    raw_evidence = archive_raw_evidence_fn(
        input_file=resolved_input_file,
        raw_root=resolved_raw_root,
        protocol=protocol,
        mw_id=mw_id,
        stage=stage,
        device=device,
    )

    items = parse_input_file_fn(
        path=raw_evidence.archived_file,
        source=detected_input_format,
        fallback_device=device,
    )

    snapshot_file = write_snapshot_fn(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=stage,
        device=device,
        source_requested="Manual",
        source_actual="Local DB",
        raw_file=raw_evidence.archived_file,
        **{snapshot_items_arg: items},
    )

    snapshot_json = patch_snapshot_metadata_fn(
        snapshot_file=snapshot_file,
        input_format=detected_input_format,
        original_input_file=raw_evidence.original_file,
        raw_sha256=raw_evidence.content_sha256,
        raw_archived_at_utc=raw_evidence.archived_at_utc,
    )

    database_id = insert_manual_output_fn(
        db_path=db_path,
        protocol=protocol,
        mw_id=mw_id,
        stage=stage,
        device=device,
        input_format=detected_input_format,
        input_file=raw_evidence.archived_file,
        snapshot_json=snapshot_json,
    )

    return result_builder(
        **{result_items_arg: items},
        snapshot_file=snapshot_file,
        database_id=database_id,
        input_format=detected_input_format,
        original_input_file=raw_evidence.original_file,
        raw_file=raw_evidence.archived_file,
        raw_sha256=raw_evidence.content_sha256,
    )
