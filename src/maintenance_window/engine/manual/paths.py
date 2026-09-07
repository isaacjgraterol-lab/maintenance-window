from __future__ import annotations

from pathlib import Path


def default_manual_raw_root(snapshot_root: Path) -> Path:
    """Resolve outputs/raw/manual from outputs/snapshots/<protocol>."""
    try:
        outputs_root = snapshot_root.parents[1]
    except IndexError as exc:
        raise ValueError(
            "Snapshot root is too shallow to resolve raw evidence root: "
            f"{snapshot_root}"
        ) from exc

    return outputs_root / "raw" / "manual"
