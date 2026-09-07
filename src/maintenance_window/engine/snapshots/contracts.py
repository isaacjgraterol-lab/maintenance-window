from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar


ItemT = TypeVar("ItemT")


@dataclass(frozen=True, slots=True)
class SnapshotAdapter(Generic[ItemT]):
    """Protocol-specific operations required by snapshot storage."""

    protocol: str
    items_field: str
    serialize_item: Callable[[ItemT], dict[str, Any]]
    deserialize_item: Callable[[dict[str, Any], str], ItemT]
    build_summary: Callable[[list[ItemT]], dict[str, Any]]
    build_details: Callable[[list[ItemT]], dict[str, Any]]
