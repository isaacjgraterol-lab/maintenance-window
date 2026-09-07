"""Parallel live collection executor."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

from maintenance_window.engine.live_collection.models import (
    LiveCollectionFailure,
    LiveCollectionResult,
    LiveCollectionSuccess,
)

T = TypeVar("T")
V = TypeVar("V")


def collect_parallel(
    items: Sequence[T],
    collect_item: Callable[[T], V],
    *,
    max_workers: int,
) -> list[LiveCollectionResult[T, V]]:
    """Collect items concurrently and return results in input order."""
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1.")

    if not items:
        return []

    results: list[LiveCollectionResult[T, V] | None] = [None] * len(items)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(collect_item, item): index
            for index, item in enumerate(items)
        }

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            item = items[index]
            try:
                results[index] = LiveCollectionSuccess(
                    item=item,
                    value=future.result(),
                )
            except Exception as exc:
                results[index] = LiveCollectionFailure(
                    item=item,
                    error=exc,
                )

    return [result for result in results if result is not None]
