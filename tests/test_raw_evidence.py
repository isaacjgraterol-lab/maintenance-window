from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from maintenance_window.core.hashing import file_sha256
from maintenance_window.core.raw_evidence import archive_raw_evidence


def test_archive_raw_evidence_uses_device_timestamp_and_hash(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "MX204_06_before.json"
    input_file.write_text('{"status": "ok"}', encoding="utf-8")

    raw_root = tmp_path / "outputs" / "raw" / "manual"
    archived_at = datetime(
        2026,
        6,
        23,
        14,
        30,
        15,
        tzinfo=timezone.utc,
    )

    result = archive_raw_evidence(
        input_file=input_file,
        raw_root=raw_root,
        protocol="bgp",
        mw_id="MW_CORE_001",
        stage="before",
        device="MX204_06",
        archived_at=archived_at,
    )

    assert result.original_file == input_file.resolve()
    assert result.archived_file.parent == (
        raw_root / "bgp" / "MW_CORE_001" / "before"
    )
    assert result.archived_file.name.startswith(
        "MX204_06_20260623T143015000000Z_"
    )
    assert result.archived_file.suffix == ".json"
    assert result.archived_file.read_bytes() == input_file.read_bytes()
    assert result.content_sha256 == file_sha256(input_file)
    assert file_sha256(result.archived_file) == result.content_sha256


def test_archive_raw_evidence_never_overwrites_existing_file(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "capture.xml"
    input_file.write_text("<rpc-reply />", encoding="utf-8")

    raw_root = tmp_path / "raw"
    archived_at = datetime(
        2026,
        6,
        23,
        15,
        0,
        0,
        tzinfo=timezone.utc,
    )

    first = archive_raw_evidence(
        input_file=input_file,
        raw_root=raw_root,
        protocol="bgp",
        mw_id="MW_REPEAT_001",
        stage="after",
        device="MX204_06",
        archived_at=archived_at,
    )
    second = archive_raw_evidence(
        input_file=input_file,
        raw_root=raw_root,
        protocol="bgp",
        mw_id="MW_REPEAT_001",
        stage="after",
        device="MX204_06",
        archived_at=archived_at,
    )

    assert first.archived_file != second.archived_file
    assert first.archived_file.exists()
    assert second.archived_file.exists()
    assert second.archived_file.stem.endswith("_1")
