"""Archive immutable-by-workflow raw evidence files."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from maintenance_window.core.hashing import file_sha256
from maintenance_window.core.path_safety import safe_path_part


@dataclass(frozen=True, slots=True)
class RawEvidence:
    """Metadata for one archived raw evidence file."""

    original_file: Path
    archived_file: Path
    content_sha256: str
    archived_at_utc: str



def _build_archive_path(
    *,
    raw_root: Path,
    protocol: str,
    mw_id: str,
    stage: str,
    device: str,
    suffix: str,
    archived_at: datetime,
    content_sha256: str,
) -> Path:
    """Build a unique path without overwriting prior evidence."""
    archive_directory = (
        raw_root
        / safe_path_part(protocol.lower())
        / safe_path_part(mw_id)
        / safe_path_part(stage.lower())
    )
    archive_directory.mkdir(parents=True, exist_ok=True)

    timestamp = archived_at.strftime("%Y%m%dT%H%M%S%fZ")
    base_name = (
        f"{safe_path_part(device)}_"
        f"{timestamp}_"
        f"{content_sha256[:12]}"
    )

    candidate = archive_directory / f"{base_name}{suffix}"
    counter = 1

    while candidate.exists():
        candidate = archive_directory / f"{base_name}_{counter}{suffix}"
        counter += 1

    return candidate


def archive_raw_evidence(
    *,
    input_file: Path,
    raw_root: Path,
    protocol: str,
    mw_id: str,
    stage: str,
    device: str,
    archived_at: datetime | None = None,
) -> RawEvidence:
    """
    Copy an input file into a unique historical evidence location.

    The archived file is never overwritten by this workflow. Its SHA-256
    hash allows later integrity verification.
    """
    original_file = input_file.resolve()

    if not original_file.exists():
        raise FileNotFoundError(
            f"Raw evidence input does not exist: {original_file}"
        )

    if not original_file.is_file():
        raise ValueError(
            f"Raw evidence input is not a file: {original_file}"
        )

    captured_at = archived_at or datetime.now(timezone.utc)

    if captured_at.tzinfo is None:
        raise ValueError(
            "Raw evidence archived_at must be timezone-aware."
        )

    captured_at_utc = captured_at.astimezone(timezone.utc)
    content_sha256 = file_sha256(original_file)
    suffix = original_file.suffix.lower() or ".raw"

    archived_file = _build_archive_path(
        raw_root=raw_root,
        protocol=protocol,
        mw_id=mw_id,
        stage=stage,
        device=device,
        suffix=suffix,
        archived_at=captured_at_utc,
        content_sha256=content_sha256,
    )

    temporary_path: Path | None = None

    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{archived_file.name}.",
            suffix=".tmp",
            dir=archived_file.parent,
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(file_descriptor, "wb") as destination:
            with original_file.open("rb") as source:
                shutil.copyfileobj(source, destination)

            destination.flush()
            os.fsync(destination.fileno())

        archived_sha256 = file_sha256(temporary_path)

        if archived_sha256 != content_sha256:
            raise IOError(
                "Archived raw evidence hash does not match the "
                "original file."
            )

        os.replace(temporary_path, archived_file)
        temporary_path = None

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return RawEvidence(
        original_file=original_file,
        archived_file=archived_file,
        content_sha256=content_sha256,
        archived_at_utc=captured_at_utc.isoformat(),
    )
