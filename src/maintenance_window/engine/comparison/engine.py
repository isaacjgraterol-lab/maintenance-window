from __future__ import annotations

from typing import Hashable, TypeVar

from maintenance_window.engine.comparison.contracts import (
    ComparisonAdapter,
)
from maintenance_window.engine.comparison.indexing import (
    build_item_map,
    find_duplicates,
)
from maintenance_window.engine.comparison.models import (
    ComparisonDiff,
    ItemStateChange,
)


ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT", bound=Hashable)


def compare_items(
    before_items: list[ItemT],
    after_items: list[ItemT],
    adapter: ComparisonAdapter[ItemT, KeyT],
) -> ComparisonDiff[ItemT, KeyT]:
    """Compare normalized PRE and POST protocol items."""
    before_map = build_item_map(before_items, adapter)
    after_map = build_item_map(after_items, adapter)

    before_keys = set(before_map)
    after_keys = set(after_map)

    common_keys = before_keys & after_keys
    lost_keys = before_keys - after_keys
    new_keys = after_keys - before_keys

    state_changes: list[ItemStateChange[KeyT]] = []

    for key in sorted(
        common_keys,
        key=adapter.key_sort_value,
    ):
        before_item = before_map[key]
        after_item = after_map[key]
        before_state = adapter.item_state(before_item)
        after_state = adapter.item_state(after_item)

        if before_state != after_state:
            state_changes.append(
                ItemStateChange(
                    key=key,
                    before_state=before_state,
                    after_state=after_state,
                )
            )

    before_unhealthy = [
        item
        for item in before_map.values()
        if not adapter.is_healthy(item)
    ]
    after_unhealthy = [
        item
        for item in after_map.values()
        if not adapter.is_healthy(item)
    ]

    before_unhealthy_keys = {
        adapter.item_key(item)
        for item in before_unhealthy
    }
    after_unhealthy_keys = {
        adapter.item_key(item)
        for item in after_unhealthy
    }

    new_unhealthy_keys = (
        after_unhealthy_keys - before_unhealthy_keys
    )
    resolved_unhealthy_keys = (
        before_unhealthy_keys - after_unhealthy_keys
    )
    persistent_unhealthy_keys = (
        before_unhealthy_keys & after_unhealthy_keys
    )

    sorted_keys = adapter.key_sort_value

    return ComparisonDiff(
        before_count=len(before_items),
        after_count=len(after_items),
        before_unique_count=len(before_keys),
        after_unique_count=len(after_keys),
        common_count=len(common_keys),
        before_duplicates=find_duplicates(
            before_items,
            adapter,
        ),
        after_duplicates=find_duplicates(
            after_items,
            adapter,
        ),
        lost_items=[
            before_map[key]
            for key in sorted(lost_keys, key=sorted_keys)
        ],
        new_items=[
            after_map[key]
            for key in sorted(new_keys, key=sorted_keys)
        ],
        state_changes=state_changes,
        before_unhealthy=before_unhealthy,
        after_unhealthy=after_unhealthy,
        new_unhealthy=[
            after_map[key]
            for key in sorted(
                new_unhealthy_keys,
                key=sorted_keys,
            )
        ],
        resolved_unhealthy=[
            before_map[key]
            for key in sorted(
                resolved_unhealthy_keys,
                key=sorted_keys,
            )
            if key in after_map
        ],
        persistent_unhealthy=[
            after_map[key]
            for key in sorted(
                persistent_unhealthy_keys,
                key=sorted_keys,
            )
        ],
    )
