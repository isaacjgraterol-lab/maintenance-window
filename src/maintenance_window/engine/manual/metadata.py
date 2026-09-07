from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_snapshot_json(snapshot_file: Path) -> dict[str, Any]:
    """Load snapshot JSON from disk."""
    return json.loads(snapshot_file.read_text(encoding="utf-8"))


def write_snapshot_json(
    snapshot_file: Path,
    snapshot_json: dict[str, Any],
) -> None:
    """Write normalized snapshot JSON to disk."""
    snapshot_file.write_text(
        json.dumps(snapshot_json, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def patch_manual_snapshot_metadata(
    *,
    snapshot_file: Path,
    input_format: str,
    original_input_file: Path,
    raw_sha256: str,
    raw_archived_at_utc: str,
) -> dict[str, Any]:
    """Mark manual snapshots and preserve raw evidence metadata."""
    snapshot_json = load_snapshot_json(snapshot_file)

    snapshot_json["source_requested"] = "Manual"
    snapshot_json["source_actual"] = "Local DB"
    snapshot_json["input_format"] = input_format
    snapshot_json["original_input_file"] = str(original_input_file)
    snapshot_json["raw_sha256"] = raw_sha256
    snapshot_json["raw_archived_at_utc"] = raw_archived_at_utc

    write_snapshot_json(snapshot_file, snapshot_json)

    return snapshot_json
