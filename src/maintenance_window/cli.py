"""Public Maintenance Window command-line interface."""

from __future__ import annotations

import json
from collections.abc import Sequence

from maintenance_window.cli_app.arguments import build_parser
from maintenance_window.cli_app.defaults import (
    DEFAULT_CONNECTION_SETTINGS,
    DEFAULT_CREDENTIALS,
    DEFAULT_INVENTORY,
    DEFAULT_LOCAL_DB,
    IMPLEMENTED_PROTOCOLS,
    PROJECT_ROOT,
)
from maintenance_window.cli_app.dispatch import dispatch


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments, dispatch one flow, and report clean errors."""
    args = build_parser().parse_args(argv)

    try:
        return dispatch(args)
    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ) as exc:
        print(f"\nError: {exc}")
        return 1


__all__ = [
    "DEFAULT_CONNECTION_SETTINGS",
    "DEFAULT_CREDENTIALS",
    "DEFAULT_INVENTORY",
    "DEFAULT_LOCAL_DB",
    "IMPLEMENTED_PROTOCOLS",
    "PROJECT_ROOT",
    "build_parser",
    "main",
]
