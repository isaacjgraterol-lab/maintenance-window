from __future__ import annotations

from pathlib import Path


PACKAGE_FILE = Path(__file__).resolve()
PROJECT_ROOT = PACKAGE_FILE.parents[4]
DEFAULT_BGP_SNAPSHOT_ROOT = (
    PROJECT_ROOT
    / "outputs"
    / "snapshots"
    / "bgp"
)
