from __future__ import annotations

from typing import Hashable, TypeVar

from maintenance_window.engine.comparison.contracts import (
    ComparisonAdapter,
)
from maintenance_window.engine.comparison.models import DuplicateItem


ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT", bound=Hashable)


def build_item_map(
    items: list[ItemT],
    adapter: ComparisonAdapter[ItemT, KeyT],
) -> dict[KeyT, ItemT]:
    """Build a unique map where the last duplicate record wins."""
    item_map: dict[KeyT, ItemT] = {}

    for item in items:
        item_map[adapter.item_key(item)] = item

    return item_map


def build_item_groups(
    items: list[ItemT],
    adapter: ComparisonAdapter[ItemT, KeyT],
) -> dict[KeyT, list[ItemT]]:
    """Group normalized protocol items by their comparison key."""
    groups: dict[KeyT, list[ItemT]] = {}

    for item in items:
        key = adapter.item_key(item)
        groups.setdefault(key, []).append(item)

    return groups


def find_duplicates(
    items: list[ItemT],
    adapter: ComparisonAdapter[ItemT, KeyT],
) -> list[DuplicateItem[KeyT]]:
    """Find duplicate entries inside one normalized item collection."""
    groups = build_item_groups(items, adapter)
    duplicates: list[DuplicateItem[KeyT]] = []

    for key, grouped_items in sorted(
        groups.items(),
        key=lambda entry: adapter.key_sort_value(entry[0]),
    ):
        if len(grouped_items) <= 1:
            continue

        duplicates.append(
            DuplicateItem(
                key=key,
                count=len(grouped_items),
                states=sorted(
                    {
                        adapter.item_state(item)
                        for item in grouped_items
                    }
                ),
            )
        )

    return duplicates


def duplicate_count(
    duplicates: list[DuplicateItem[KeyT]],
) -> int:
    """Count duplicate entries beyond each first unique record."""
    return sum(item.count - 1 for item in duplicates)
