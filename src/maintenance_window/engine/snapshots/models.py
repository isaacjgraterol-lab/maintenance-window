from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar


ItemT = TypeVar("ItemT")


@dataclass(frozen=True, slots=True)
class StoredSnapshot(Generic[ItemT]):
    """Protocol-neutral normalized snapshot loaded from disk."""

    protocol: str
    mw_id: str
    stage: str
    device: str
    source_requested: str
    source_actual: str
    raw_file: str | None
    created_at_utc: str
    items: list[ItemT]
    path: Path
