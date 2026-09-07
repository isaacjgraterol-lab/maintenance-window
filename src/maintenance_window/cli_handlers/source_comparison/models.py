"""Data exchanged by source-comparison handler modules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maintenance_window.core.models import CredentialProfile, Device


@dataclass(frozen=True, slots=True)
class SourceComparisonRequest:
    """Normalized CLI request for one source-comparison run."""

    left_source: str
    right_source: str
    devices: list[Device]
    export_path: Path | None


@dataclass(frozen=True, slots=True)
class SourceComparisonRuntime:
    """Credentials and settings shared by every selected device."""

    defaults: dict[str, str]
    profiles: dict[str, CredentialProfile]
    settings: dict[str, object]
    project_root: Path


@dataclass(frozen=True, slots=True)
class DeviceSourceComparison:
    """Comparison artifacts produced for one inventory device."""

    comparison: Any
    report: dict[str, object]
    raw_files: dict[str, Path]
    actual_sources: dict[str, str]
