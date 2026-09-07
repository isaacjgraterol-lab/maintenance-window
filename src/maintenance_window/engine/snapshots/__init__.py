"""Generic snapshot storage primitives."""

from maintenance_window.engine.snapshots.contracts import SnapshotAdapter
from maintenance_window.engine.snapshots.models import StoredSnapshot
from maintenance_window.engine.snapshots.paths import (
    build_snapshot_path,
    safe_path_part,
)
from maintenance_window.engine.snapshots.reader import load_snapshot
from maintenance_window.engine.snapshots.writer import write_snapshot

__all__ = [
    "SnapshotAdapter",
    "StoredSnapshot",
    "build_snapshot_path",
    "load_snapshot",
    "safe_path_part",
    "write_snapshot",
]
