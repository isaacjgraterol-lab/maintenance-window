"""Sequential live collection executor."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from maintenance_window.engine.live_collection.models import (
    LiveCollectionFailure,
    LiveCollectionResult,
    LiveCollectionSuccess,
)

T = TypeVar("T")
V = TypeVar("V")


def collect_sequential(
    items: Sequence[T],
    collect_item: Callable[[T], V],
) -> list[LiveCollectionResult[T, V]]:
    """Collect items one by one and preserve input order."""
    results: list[LiveCollectionResult[T, V]] = []

    for item in items:
        try:
            results.append(
                LiveCollectionSuccess(
                    item=item,
                    value=collect_item(item),
                )
            )
        except Exception as exc:
            results.append(
                LiveCollectionFailure(
                    item=item,
                    error=exc,
                )
            )

    return results
