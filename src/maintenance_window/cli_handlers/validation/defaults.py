"""Constants used by the standard validation handler."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

MANUAL_SOURCE = "manual"
FILE_SOURCES = frozenset({"json-file", "xml-file"})
LIVE_SOURCES = frozenset({"auto", "pyez", "gnmic", "ssh"})

DEFAULT_BGP_SNAPSHOT_ROOT = (
    PROJECT_ROOT
    / "outputs"
    / "snapshots"
    / "bgp"
)
