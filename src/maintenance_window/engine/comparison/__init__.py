"""Generic PRE/POST comparison primitives."""

from maintenance_window.engine.comparison.engine import compare_items
from maintenance_window.engine.comparison.validation import (
    validate_snapshot_pair,
)

__all__ = [
    "compare_items",
    "validate_snapshot_pair",
]
