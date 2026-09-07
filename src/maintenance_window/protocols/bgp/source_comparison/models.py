from __future__ import annotations

from dataclasses import dataclass

from maintenance_window.protocols.bgp.state.models import BgpSession


@dataclass(frozen=True, slots=True)
class BgpSessionKey:
    """
    Unique key used to compare BGP sessions between collectors.

    The same neighbor on the same device should represent the same BGP session.
    """

    device: str
    neighbor: str


@dataclass(frozen=True, slots=True)
class BgpSessionStateDifference:
    """
    Represents a session that exists in both sources but has a different state.
    """

    device: str
    neighbor: str
    left_state: str
    right_state: str


@dataclass(frozen=True, slots=True)
class BgpDuplicateSession:
    """
    Represents duplicate records for the same device/neighbor key.
    """

    device: str
    neighbor: str
    count: int
    states: list[str]


@dataclass(frozen=True, slots=True)
class BgpSourceComparison:
    """
    Result of comparing two BGP collection sources.
    """

    left_source: str
    right_source: str

    left_count: int
    right_count: int

    left_unique_count: int
    right_unique_count: int
    common_count: int

    left_duplicate_count: int
    right_duplicate_count: int
    left_duplicates: list[BgpDuplicateSession]
    right_duplicates: list[BgpDuplicateSession]

    only_left: list[BgpSession]
    only_right: list[BgpSession]
    different_state: list[BgpSessionStateDifference]
