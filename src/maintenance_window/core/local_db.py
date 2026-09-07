from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from maintenance_window.core.hashing import file_sha256


SCHEMA = """
CREATE TABLE IF NOT EXISTS manual_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    mw_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    device TEXT NOT NULL,
    source_requested TEXT NOT NULL,
    source_actual TEXT NOT NULL,
    input_format TEXT NOT NULL,
    input_file TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    normalized_snapshot_json TEXT NOT NULL,
    total_sessions INTEGER NOT NULL,
    unique_sessions INTEGER NOT NULL,
    duplicate_entries INTEGER NOT NULL,
    unhealthy_sessions INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_manual_outputs_protocol_mw_stage
ON manual_outputs (protocol, mw_id, stage);

CREATE INDEX IF NOT EXISTS idx_manual_outputs_device
ON manual_outputs (device);

CREATE INDEX IF NOT EXISTS idx_manual_outputs_source
ON manual_outputs (source_requested, source_actual);

CREATE INDEX IF NOT EXISTS idx_manual_outputs_content_sha256
ON manual_outputs (content_sha256);
"""


def initialize_local_db(db_path: Path) -> None:
    """
    Create the local SQLite DB and required tables if they do not exist.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


def insert_manual_output(
    *,
    db_path: Path,
    protocol: str,
    mw_id: str,
    stage: str,
    device: str,
    input_format: str,
    input_file: Path,
    snapshot_json: dict[str, Any],
) -> int:
    """
    Insert one manual JSON/XML upload into the local DB.

    The DB stores:
    - original raw content
    - normalized snapshot JSON
    - searchable summary fields
    """
    initialize_local_db(db_path)

    raw_content = input_file.read_text(
        encoding="utf-8",
        errors="replace",
    )

    summary = snapshot_json.get("summary", {})

    total_sessions = int(summary.get("total_sessions", 0))
    unique_sessions = int(summary.get("unique_sessions", 0))
    duplicate_entries = int(summary.get("duplicate_entries", 0))
    unhealthy_sessions = int(summary.get("unhealthy_sessions", 0))

    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO manual_outputs (
                protocol,
                mw_id,
                stage,
                device,
                source_requested,
                source_actual,
                input_format,
                input_file,
                content_sha256,
                raw_content,
                normalized_snapshot_json,
                total_sessions,
                unique_sessions,
                duplicate_entries,
                unhealthy_sessions,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                protocol,
                mw_id,
                stage,
                device,
                "Manual",
                "Local DB",
                input_format,
                str(input_file),
                file_sha256(input_file),
                raw_content,
                json.dumps(snapshot_json, indent=2, sort_keys=True),
                total_sessions,
                unique_sessions,
                duplicate_entries,
                unhealthy_sessions,
                created_at,
            ),
        )

        connection.commit()

        return int(cursor.lastrowid)


def list_manual_outputs(
    *,
    db_path: Path,
    protocol: str | None = None,
    mw_id: str | None = None,
    stage: str | None = None,
    device: str | None = None,
    with_unhealthy: bool = False,
    with_duplicates: bool = False,
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    """
    List manual JSON/XML uploads stored in the local DB.

    Filters are optional and map to searchable DB columns:
    - protocol
    - mw_id
    - stage
    - device
    - unhealthy_sessions > 0
    - duplicate_entries > 0
    """
    initialize_local_db(db_path)

    query = """
        SELECT
            id,
            protocol,
            mw_id,
            stage,
            device,
            source_requested,
            source_actual,
            input_format,
            input_file,
            total_sessions,
            unique_sessions,
            duplicate_entries,
            unhealthy_sessions,
            created_at
        FROM manual_outputs
        WHERE 1 = 1
    """
    parameters: list[Any] = []

    if protocol:
        query += " AND protocol = ?"
        parameters.append(protocol)

    if mw_id:
        query += " AND mw_id = ?"
        parameters.append(mw_id)

    if stage:
        query += " AND stage = ?"
        parameters.append(stage)

    if device:
        query += " AND device = ?"
        parameters.append(device)

    if with_unhealthy:
        query += " AND unhealthy_sessions > 0"

    if with_duplicates:
        query += " AND duplicate_entries > 0"

    query += " ORDER BY id"

    if limit is not None:
        if limit <= 0:
            raise ValueError("manual DB limit must be greater than zero.")
        query += " LIMIT ?"
        parameters.append(limit)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()

    return [dict(row) for row in rows]
