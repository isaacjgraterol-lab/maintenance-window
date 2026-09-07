from __future__ import annotations

from pathlib import Path

from maintenance_window.core.path_safety import safe_path_part


def build_snapshot_path(
    snapshot_root: Path,
    mw_id: str,
    stage: str,
    device: str,
) -> Path:
    """Build the normalized per-device snapshot path."""
    safe_mw_id = safe_path_part(mw_id)
    safe_stage = safe_path_part(stage.lower())
    safe_device = safe_path_part(device)

    return (
        snapshot_root
        / safe_mw_id
        / safe_stage
        / f"{safe_device}.json"
    )


__all__ = ["build_snapshot_path", "safe_path_part"]
