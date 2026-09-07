from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maintenance_window.protocols.bgp.state.models import BgpSession


@dataclass(frozen=True, slots=True)
class BgpSnapshotSessionKey:
    """
    Unique key for BGP snapshot comparison.
    """

    device: str
    neighbor: str


@dataclass(frozen=True, slots=True)
class BgpSnapshot:
    """
    Normalized BGP snapshot loaded from disk.
    """

    mw_id: str
    stage: str
    device: str
    source_requested: str
    source_actual: str
    raw_file: str | None
    created_at_utc: str
    sessions: list[BgpSession]
    path: Path


@dataclass(frozen=True, slots=True)
class BgpSnapshotStateChange:
    """
    Represents a BGP session that changed state between snapshots.
    """

    device: str
    neighbor: str
    before_state: str
    after_state: str


@dataclass(frozen=True, slots=True)
class BgpSnapshotDuplicateSession:
    """
    Represents duplicate session entries inside one snapshot.
    """

    device: str
    neighbor: str
    count: int
    states: list[str]


@dataclass(frozen=True, slots=True)
class BgpSnapshotComparison:
    """
    Result of comparing BGP before/after snapshots.
    """

    mw_id: str
    device: str
    before_stage: str
    after_stage: str
    result: str

    before_count: int
    after_count: int

    before_unique_count: int
    after_unique_count: int
    common_count: int

    before_duplicate_count: int
    after_duplicate_count: int
    before_duplicates: list[BgpSnapshotDuplicateSession]
    after_duplicates: list[BgpSnapshotDuplicateSession]

    lost_sessions: list[BgpSession]
    new_sessions: list[BgpSession]
    state_changes: list[BgpSnapshotStateChange]

    before_unhealthy: list[BgpSession]
    after_unhealthy: list[BgpSession]
    new_unhealthy: list[BgpSession]
    resolved_unhealthy: list[BgpSession]
    persistent_unhealthy: list[BgpSession]

    fail_reasons: list[str]
