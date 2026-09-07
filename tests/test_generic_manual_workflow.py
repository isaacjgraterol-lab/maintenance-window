from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from maintenance_window.engine.manual import input_format
from maintenance_window.engine.manual import metadata
from maintenance_window.engine.manual import paths
from maintenance_window.engine.manual.execution import store_manual_upload


def test_generic_manual_format_detection_uses_extension() -> None:
    assert input_format.detect_manual_input_format(Path("capture.json"), None) == "json-file"
    assert input_format.detect_manual_input_format(Path("capture.XML"), None) == "xml-file"


def test_generic_manual_format_detection_accepts_explicit_value() -> None:
    assert input_format.detect_manual_input_format(Path("capture.bin"), "custom-file") == "custom-file"


def test_generic_manual_format_detection_supports_custom_suffix_map() -> None:
    assert input_format.detect_manual_input_format(Path("capture.txt"), None, {".txt": "text-file"}) == "text-file"


def test_generic_manual_format_detection_rejects_unknown_extension() -> None:
    with pytest.raises(ValueError, match="Unable to detect"):
        input_format.detect_manual_input_format(Path("capture.txt"), None)


def test_generic_manual_default_raw_root() -> None:
    assert paths.default_manual_raw_root(Path("outputs/snapshots/bgp")) == Path("outputs/raw/manual")


def test_generic_manual_metadata_patch(tmp_path: Path) -> None:
    snapshot_file = tmp_path / "snapshot.json"
    snapshot_file.write_text(json.dumps({"protocol": "bgp"}), encoding="utf-8")

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
    assert result["raw_sha256"] == "abc123"


def test_generic_manual_workflow_preserves_operation_order(tmp_path: Path) -> None:
    input_file = tmp_path / "capture.json"
    input_file.write_text("{}", encoding="utf-8")
    archived_file = tmp_path / "raw" / "capture.json"
    snapshot_file = tmp_path / "snapshot.json"
    items = [object()]
    calls: list[str] = []
    raw_evidence = SimpleNamespace(
        original_file=input_file.resolve(),
        archived_file=archived_file,
        content_sha256="sha256-value",
        archived_at_utc="2026-06-26T12:00:00+00:00",
    )

    def detect_input_format_fn(**kwargs: Any) -> str:
        calls.append("detect")
        return "json-file"

    def archive_raw_evidence_fn(**kwargs: Any) -> SimpleNamespace:
        calls.append("archive")
        assert kwargs["protocol"] == "example"
        return raw_evidence

    def parse_input_file_fn(**kwargs: Any) -> list[object]:
        calls.append("parse")
        assert kwargs["path"] == archived_file
        return items

    def write_snapshot_fn(**kwargs: Any) -> Path:
        calls.append("snapshot")
        assert kwargs["things"] is items
        return snapshot_file

    def patch_snapshot_metadata_fn(**kwargs: Any) -> dict[str, Any]:
        calls.append("metadata")
        return {"summary": {"total_items": 1}}

    def insert_manual_output_fn(**kwargs: Any) -> int:
        calls.append("database")
        assert kwargs["protocol"] == "example"
        assert kwargs["input_file"] == archived_file
        return 42

    def result_builder(**kwargs: Any) -> SimpleNamespace:
        calls.append("result")
        return SimpleNamespace(**kwargs)

    result = store_manual_upload(
        protocol="example",
        input_file=input_file,
        input_format=None,
        db_path=tmp_path / "manual.db",
        snapshot_root=tmp_path / "outputs/snapshots/example",
        mw_id="MW-001",
        stage="before",
        device="router-a",
        raw_root=None,
        detect_input_format_fn=detect_input_format_fn,
        archive_raw_evidence_fn=archive_raw_evidence_fn,
        parse_input_file_fn=parse_input_file_fn,
        write_snapshot_fn=write_snapshot_fn,
        patch_snapshot_metadata_fn=patch_snapshot_metadata_fn,
        insert_manual_output_fn=insert_manual_output_fn,
        default_raw_root_fn=lambda value: tmp_path / "raw",
        result_builder=result_builder,
        snapshot_items_arg="things",
        result_items_arg="things",
    )

    assert calls == ["detect", "archive", "parse", "snapshot", "metadata", "database", "result"]
    assert result.things is items
    assert result.snapshot_file == snapshot_file
    assert result.database_id == 42
    assert result.raw_file == archived_file
    assert result.raw_sha256 == "sha256-value"
