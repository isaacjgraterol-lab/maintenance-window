"""Generic result models for live multi-item collection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
V = TypeVar("V")


@dataclass(frozen=True, slots=True)
class LiveCollectionSuccess(Generic[T, V]):
    """Successful collection result for one item."""

    item: T
    value: V


@dataclass(frozen=True, slots=True)
class LiveCollectionFailure(Generic[T]):
    """Failed collection result for one item."""

    item: T
    error: Exception


LiveCollectionResult = LiveCollectionSuccess[T, V] | LiveCollectionFailure[T]
