"""JSON validation report rendering."""

from __future__ import annotations

import json
from typing import Any


def render_json_report(payload: dict[str, Any]) -> str:
    """Render one validation payload as pretty JSON."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
