"""Stable CLI defaults and supported option values."""

from __future__ import annotations

from pathlib import Path


PACKAGE_FILE = Path(__file__).resolve()
PROJECT_ROOT = PACKAGE_FILE.parents[3]

DEFAULT_INVENTORY = PROJECT_ROOT / "inventory" / "devices.txt"
DEFAULT_CREDENTIALS = PROJECT_ROOT / "auth" / "credentials.json"
DEFAULT_CONNECTION_SETTINGS = (
    PROJECT_ROOT / "config" / "connections" / "settings.json"
)
DEFAULT_LOCAL_DB = PROJECT_ROOT / "data" / "maintenance_window.sqlite3"

IMPLEMENTED_PROTOCOLS = frozenset({"bgp"})

SOURCE_CHOICES = (
    "pyez",
    "ssh",
    "gnmic",
    "json-file",
    "xml-file",
    "auto",
    "manual",
)

SNAPSHOT_CHOICES = (
    "before",
    "after",
)

INPUT_FORMAT_CHOICES = (
    "json-file",
    "xml-file",
)
