"""Data exchanged by validation collection and rendering modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from maintenance_window.protocols.bgp.state.models import BgpSession


@dataclass(slots=True, frozen=True)
class DeviceCollectionError:
    """Collection failure captured for one selected live device."""

    device: str
    source: str
    error_type: str
    error: str


@dataclass(slots=True)
class ValidationArtifacts:
    """Normalized result of one standard validation collection flow."""

    sessions: list[BgpSession] = field(default_factory=list)
    raw_files: list[Path] = field(default_factory=list)
    actual_sources: list[str] = field(default_factory=list)
    snapshot_files: list[Path] = field(default_factory=list)
    manual_database_ids: list[int] = field(default_factory=list)
    detail_lines: list[str] = field(default_factory=list)
    device_errors: list[DeviceCollectionError] = field(default_factory=list)
    validation_report_files: dict[str, Path] = field(default_factory=dict)
