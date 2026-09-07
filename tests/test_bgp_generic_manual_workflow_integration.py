from __future__ import annotations

from pathlib import Path

from maintenance_window.engine.manual import execution as generic_execution
from maintenance_window.engine.manual import input_format as generic_input_format
from maintenance_window.engine.manual import metadata as generic_metadata
from maintenance_window.engine.manual import paths as generic_paths
from maintenance_window.protocols.bgp.manual_workflow import execution
from maintenance_window.protocols.bgp.manual_workflow import input_format
from maintenance_window.protocols.bgp.manual_workflow import metadata
from maintenance_window.protocols.bgp.manual_workflow import paths


def test_bgp_manual_workflow_uses_generic_helpers() -> None:
    assert input_format.detect_manual_input_format is generic_input_format.detect_manual_input_format
    assert metadata.load_snapshot_json is generic_metadata.load_snapshot_json
    assert metadata.write_snapshot_json is generic_metadata.write_snapshot_json
    assert metadata.patch_manual_snapshot_metadata is generic_metadata.patch_manual_snapshot_metadata
    assert paths.default_manual_raw_root is generic_paths.default_manual_raw_root


def test_bgp_manual_execution_delegates_to_generic_workflow(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_store_manual_upload(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(execution, "store_manual_upload", fake_store_manual_upload)

    result = execution.store_manual_bgp_upload(
        input_file=tmp_path / "capture.json",
        input_format=None,
        db_path=tmp_path / "manual.db",
        snapshot_root=tmp_path / "snapshots",
        mw_id="MW-001",
        stage="before",
        device="router-a",
        raw_root=None,
        detect_input_format_fn=lambda **kwargs: "json-file",
        archive_raw_evidence_fn=lambda **kwargs: object(),
        parse_input_file_fn=lambda **kwargs: [],
        write_bgp_snapshot_fn=lambda **kwargs: tmp_path / "snapshot.json",
        patch_snapshot_metadata_fn=lambda **kwargs: {},
        insert_manual_output_fn=lambda **kwargs: 1,
        default_raw_root_fn=lambda value: tmp_path / "raw",
    )

    assert result is sentinel
    assert captured["protocol"] == "bgp"
    assert captured["snapshot_items_arg"] == "sessions"
    assert captured["result_items_arg"] == "sessions"
