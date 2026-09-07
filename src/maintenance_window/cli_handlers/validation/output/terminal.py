"""Terminal rendering for validation reports."""

from __future__ import annotations

from typing import Any

from maintenance_window.cli_handlers.validation.output.detail import (
    render_detail_report,
)
from maintenance_window.cli_handlers.validation.output.json_report import (
    render_json_report,
)
from maintenance_window.cli_handlers.validation.output.summary import (
    render_summary_report,
)


def render_terminal_output(
    *,
    output_mode: str,
    payload: dict[str, Any],
) -> str:
    """Render the report mode requested for terminal output."""
    if output_mode == "detail":
        return render_detail_report(payload)
    if output_mode == "json":
        return render_json_report(payload)
    return render_summary_report(payload)
