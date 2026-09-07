"""
Maintenance Window CLI entry point.

This file must stay small.
All real logic lives under src/maintenance_window/.
"""

from __future__ import annotations

from maintenance_window.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
