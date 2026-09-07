from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maintenance_window.protocols.bgp import manual


def test_manual_upload_parses_and_stores_archived_raw(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_file = tmp_path / "MX204_06_before.json"
    input_file.write_text('{"bgp-information": []}', encoding="utf-8")

    snapshot_root = tmp_path / "outputs" / "snapshots" / "bgp"
    raw_root = tmp_path / "outputs" / "raw" / "manual"
    db_path = tmp_path / "data" / "maintenance.sqlite3"

    captured: dict[str, Any] = {}

    def fake_parse_input_file(
        *,
        path: Path,
        source: str,
        fallback_device: str,
    ) -> list[Any]:
        captured["parse_path"] = path
        captured["parse_source"] = source
        captured["fallback_device"] = fallback_device
        return []

    def fake_write_bgp_snapshot(
        *,
        snapshot_root: Path,
        mw_id: str,
        stage: str,
        device: str,
        source_requested: str,
        source_actual: str,
        raw_file: Path,
        sessions: list[Any],
    ) -> Path:
        snapshot_file = snapshot_root / mw_id / stage / f"{device}.json"
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(
            json.dumps(
                {
                    "protocol": "bgp",
                    "mw_id": mw_id,
                    "stage": stage,
                    "device": device,
                    "source_requested": source_requested,
                    "source_actual": source_actual,
                    "raw_file": str(raw_file),
                    "summary": {},
                    "sessions": sessions,
                }
            ),
            encoding="utf-8",
        )
        captured["snapshot_raw_file"] = raw_file
        return snapshot_file

    def fake_insert_manual_output(**kwargs: Any) -> int:
        captured["database_input_file"] = kwargs["input_file"]
        captured["snapshot_json"] = kwargs["snapshot_json"]
        return 77

    monkeypatch.setattr(manual, "parse_input_file", fake_parse_input_file)
    monkeypatch.setattr(manual, "write_bgp_snapshot", fake_write_bgp_snapshot)
    monkeypatch.setattr(manual, "insert_manual_output", fake_insert_manual_output)

    result = manual.store_manual_bgp_upload(
        input_file=input_file,
        input_format="json-file",
        db_path=db_path,
        snapshot_root=snapshot_root,
        mw_id="MW_MANUAL_RAW_001",
        stage="before",
        device="MX204_06",
        raw_root=raw_root,
    )

    assert result.database_id == 77
    assert result.original_input_file == input_file.resolve()
    assert result.raw_file != input_file.resolve()
    assert result.raw_file.exists()
    assert result.raw_file.parent == (
        raw_root / "bgp" / "MW_MANUAL_RAW_001" / "before"
    )
    assert result.raw_file.name.startswith("MX204_06_")
    assert captured["parse_path"] == result.raw_file
    assert captured["snapshot_raw_file"] == result.raw_file
    assert captured["database_input_file"] == result.raw_file

    snapshot_json = captured["snapshot_json"]

    assert snapshot_json["raw_file"] == str(result.raw_file)
    assert snapshot_json["original_input_file"] == str(input_file.resolve())
    assert snapshot_json["raw_sha256"] == result.raw_sha256
    assert snapshot_json["raw_archived_at_utc"]
