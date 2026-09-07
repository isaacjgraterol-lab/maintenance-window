"""Snapshot Store discovery helpers for the local GUI.

The Snapshot Store is the filesystem location used by the maintenance-window
comparison workflow:

    outputs/snapshots/<protocol>/<MW_ID>/before/*.json
    outputs/snapshots/<protocol>/<MW_ID>/after/*.json

This module does not connect to devices and does not read the Manual DB.
It only summarizes snapshot folders that already exist on disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SnapshotMwRecord:
    mw_id: str
    before_count: int
    after_count: int
    common_count: int
    ready: bool
    reason: str
    common_devices: tuple[str, ...]
    before_only_devices: tuple[str, ...]
    after_only_devices: tuple[str, ...]
    before_last_modified_timestamp: float | None
    after_last_modified_timestamp: float | None
    last_modified_timestamp: float | None
    before_last_modified: str
    after_last_modified: str
    last_modified: str


def _json_files(path: Path) -> list[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _device_names(files: list[Path]) -> set[str]:
    return {path.stem for path in files}


def _last_modified(paths: list[Path]) -> float | None:
    timestamps: list[float] = []
    for path in paths:
        try:
            timestamps.append(path.stat().st_mtime)
        except OSError:
            continue
    if not timestamps:
        return None
    return max(timestamps)


def _format_timestamp(value: float | None) -> str:
    if value is None:
        return "N/A"
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _reason(
    *,
    before_devices: set[str],
    after_devices: set[str],
    common_devices: set[str],
) -> str:
    if common_devices:
        return "Ready"

    if before_devices and not after_devices:
        return "Missing after snapshot"
    if after_devices and not before_devices:
        return "Missing before snapshot"
    if before_devices or after_devices:
        return "No common before/after devices"
    return "No snapshot files"


def discover_snapshot_mw_records(
    project_root: Path,
    *,
    protocol: str = "bgp",
) -> list[SnapshotMwRecord]:
    """Return MW snapshot folder summaries ordered by most recent first."""
    snapshot_root = project_root / "outputs" / "snapshots" / protocol
    if not snapshot_root.exists() or not snapshot_root.is_dir():
        return []

    records: list[SnapshotMwRecord] = []

    for mw_path in sorted(snapshot_root.iterdir()):
        if not mw_path.is_dir():
            continue

        before_files = _json_files(mw_path / "before")
        after_files = _json_files(mw_path / "after")

        before_devices = _device_names(before_files)
        after_devices = _device_names(after_files)
        common_devices = before_devices & after_devices

        all_paths = before_files + after_files
        if not all_paths:
            all_paths = [mw_path]

        before_last_ts = _last_modified(before_files)
        after_last_ts = _last_modified(after_files)
        last_ts = _last_modified(all_paths)

        records.append(
            SnapshotMwRecord(
                mw_id=mw_path.name,
                before_count=len(before_devices),
                after_count=len(after_devices),
                common_count=len(common_devices),
                ready=bool(common_devices),
                reason=_reason(
                    before_devices=before_devices,
                    after_devices=after_devices,
                    common_devices=common_devices,
                ),
                common_devices=tuple(sorted(common_devices)),
                before_only_devices=tuple(sorted(before_devices - after_devices)),
                after_only_devices=tuple(sorted(after_devices - before_devices)),
                before_last_modified_timestamp=before_last_ts,
                after_last_modified_timestamp=after_last_ts,
                last_modified_timestamp=last_ts,
                before_last_modified=_format_timestamp(before_last_ts),
                after_last_modified=_format_timestamp(after_last_ts),
                last_modified=_format_timestamp(last_ts),
            )
        )

    return sorted(
        records,
        key=lambda item: item.last_modified_timestamp or 0,
        reverse=True,
    )
