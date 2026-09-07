"""Generic live collection executors."""

from maintenance_window.engine.live_collection.models import (
    LiveCollectionFailure,
    LiveCollectionResult,
    LiveCollectionSuccess,
)
from maintenance_window.engine.live_collection.parallel import collect_parallel
from maintenance_window.engine.live_collection.sequential import collect_sequential

__all__ = [
    "LiveCollectionFailure",
    "LiveCollectionResult",
    "LiveCollectionSuccess",
    "collect_parallel",
    "collect_sequential",
]
