from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Hashable, TypeVar


ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT", bound=Hashable)


@dataclass(frozen=True, slots=True)
class ItemStateChange(Generic[KeyT]):
    """State transition for one normalized protocol item."""

    key: KeyT
    before_state: str
    after_state: str


@dataclass(frozen=True, slots=True)
class DuplicateItem(Generic[KeyT]):
    """Duplicate normalized entries for one protocol item key."""

    key: KeyT
    count: int
    states: list[str]


@dataclass(frozen=True, slots=True)
class ComparisonDiff(Generic[ItemT, KeyT]):
    """Protocol-neutral differences between PRE and POST items."""

    before_count: int
    after_count: int
    before_unique_count: int
    after_unique_count: int
    common_count: int

    before_duplicates: list[DuplicateItem[KeyT]]
    after_duplicates: list[DuplicateItem[KeyT]]

    lost_items: list[ItemT]
    new_items: list[ItemT]
    state_changes: list[ItemStateChange[KeyT]]

    before_unhealthy: list[ItemT]
    after_unhealthy: list[ItemT]
    new_unhealthy: list[ItemT]
    resolved_unhealthy: list[ItemT]
    persistent_unhealthy: list[ItemT]
