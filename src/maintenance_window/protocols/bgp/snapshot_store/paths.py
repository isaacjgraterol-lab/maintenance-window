"""BGP compatibility exports for generic snapshot paths."""

from maintenance_window.engine.snapshots.paths import (
    build_snapshot_path,
    safe_path_part,
)

__all__ = [
    "build_snapshot_path",
    "safe_path_part",
]
