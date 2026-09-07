from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maintenance_window.protocols.bgp.state.models import BgpSession


@dataclass(frozen=True)
class ManualBgpUploadResult:
    """Result of one manual BGP upload."""

    sessions: list[BgpSession]
    snapshot_file: Path
    database_id: int
    input_format: str
    original_input_file: Path
    raw_file: Path
    raw_sha256: str
