from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintenance_window.protocols.bgp import manual
from maintenance_window.protocols.bgp.manual_workflow import execution
from maintenance_window.protocols.bgp.manual_workflow import input_format
from maintenance_window.protocols.bgp.manual_workflow import metadata
from maintenance_window.protocols.bgp.manual_workflow import paths


def test_manual_module_is_small_compatibility_facade() -> None:
    module_path = Path(manual.__file__)

    assert len(module_path.read_text(encoding="utf-8").splitlines()) <= 80
    assert callable(manual.store_manual_bgp_upload)
    assert manual.ManualBgpUploadResult.__name__ == "ManualBgpUploadResult"


@pytest.mark.parametrize(
    ("filename", "explicit", "expected"),
    [
        ("capture.json", None, "json-file"),
        ("capture.XML", None, "xml-file"),
        ("capture.bin", "json-file", "json-file"),
    ],
)
def test_detect_manual_input_format(
    filename: str,
    explicit: str | None,
    expected: str,
) -> None:
    assert (
        input_format.detect_manual_input_format(
            Path(filename),
            explicit,
        )
        == expected
    )


def test_detect_manual_input_format_rejects_unknown_extension() -> None:
    with pytest.raises(ValueError, match="Unable to detect"):
        input_format.detect_manual_input_format(
            Path("capture.txt"),
            None,
        )


def test_default_manual_raw_root() -> None:
    assert paths.default_manual_raw_root(
        Path("outputs/snapshots/bgp")
    ) == Path("outputs/raw/manual")


def test_patch_manual_snapshot_metadata(tmp_path: Path) -> None:
    snapshot_file = tmp_path / "snapshot.json"
    snapshot_file.write_text(
        json.dumps({"protocol": "bgp"}),
        encoding="utf-8",
    )

    result = metadata.patch_manual_snapshot_metadata(
        snapshot_file=snapshot_file,
        input_format="json-file",
        original_input_file=Path("inputs/capture.json"),
        raw_sha256="abc123",
        raw_archived_at_utc="2026-06-26T12:00:00+00:00",
    )

    assert result["source_requested"] == "Manual"
    assert result["source_actual"] == "Local DB"
    assert result["input_format"] == "json-file"
    assert result["original_input_file"] == str(
        Path("inputs/capture.json")
    )
    assert result["raw_sha256"] == "abc123"


def test_execution_preserves_manual_upload_workflow(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "capture.json"
    input_file.write_text("{}", encoding="utf-8")

    archived_file = tmp_path / "raw" / "capture.json"
    snapshot_file = tmp_path / "snapshot.json"
    sessions = [object()]
    calls: list[str] = []

    raw_evidence = SimpleNamespace(
        original_file=input_file.resolve(),
        archived_file=archived_file,
        content_sha256="sha256-value",
        archived_at_utc="2026-06-26T12:00:00+00:00",
    )

    def detect_input_format_fn(**kwargs):
        calls.append("detect")
        return "json-file"

    def archive_raw_evidence_fn(**kwargs):
        calls.append("archive")
        return raw_evidence

    def parse_input_file_fn(**kwargs):
        calls.append("parse")
        return sessions

    def write_bgp_snapshot_fn(**kwargs):
        calls.append("snapshot")
        return snapshot_file

    def patch_snapshot_metadata_fn(**kwargs):
        calls.append("metadata")
        return {"summary": {"total_sessions": 1}}

    def insert_manual_output_fn(**kwargs):
        calls.append("database")
        return 42

    result = execution.store_manual_bgp_upload(
        input_file=input_file,
        input_format=None,
        db_path=tmp_path / "manual.db",
        snapshot_root=tmp_path / "outputs/snapshots/bgp",
        mw_id="MW-001",
        stage="before",
        device="router-a",
        raw_root=None,
        detect_input_format_fn=detect_input_format_fn,
        archive_raw_evidence_fn=archive_raw_evidence_fn,
        parse_input_file_fn=parse_input_file_fn,
        write_bgp_snapshot_fn=write_bgp_snapshot_fn,
        patch_snapshot_metadata_fn=patch_snapshot_metadata_fn,
        insert_manual_output_fn=insert_manual_output_fn,
        default_raw_root_fn=lambda value: tmp_path / "raw",
    )

    assert calls == [
        "detect",
        "archive",
        "parse",
        "snapshot",
        "metadata",
        "database",
    ]
    assert result.sessions is sessions
    assert result.snapshot_file == snapshot_file
    assert result.database_id == 42
    assert result.raw_file == archived_file
    assert result.raw_sha256 == "sha256-value"


def test_facade_passes_patchable_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_execute(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(
        manual,
        "_execute_manual_bgp_upload",
        fake_execute,
    )

    result = manual.store_manual_bgp_upload(
        input_file=tmp_path / "capture.json",
        input_format=None,
        db_path=tmp_path / "manual.db",
        snapshot_root=tmp_path / "snapshots",
        mw_id="MW-001",
        stage="before",
        device="router-a",
    )

    assert result is sentinel
    assert captured["archive_raw_evidence_fn"] is manual.archive_raw_evidence
    assert captured["parse_input_file_fn"] is manual.parse_input_file
    assert captured["write_bgp_snapshot_fn"] is manual.write_bgp_snapshot
    assert captured["insert_manual_output_fn"] is manual.insert_manual_output
