from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Hashable, TypeVar


ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT", bound=Hashable)


@dataclass(frozen=True, slots=True)
class ComparisonAdapter(Generic[ItemT, KeyT]):
    """Protocol-specific operations required by the generic comparator."""

    item_key: Callable[[ItemT], KeyT]
    item_state: Callable[[ItemT], str]
    is_healthy: Callable[[ItemT], bool]
    key_sort_value: Callable[[KeyT], tuple[str, ...]]
