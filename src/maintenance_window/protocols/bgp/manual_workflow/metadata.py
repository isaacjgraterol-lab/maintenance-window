"""BGP compatibility exports for generic manual snapshot metadata."""

from maintenance_window.engine.manual.metadata import (
    load_snapshot_json,
    patch_manual_snapshot_metadata,
    write_snapshot_json,
)

__all__ = [
    "load_snapshot_json",
    "patch_manual_snapshot_metadata",
    "write_snapshot_json",
]
