"""Execute the standard BGP validation workflow."""

from __future__ import annotations

import argparse
from typing import cast

from maintenance_window.protocols.bgp.state.filters import (
    StatusFilter,
    filter_sessions,
)
from maintenance_window.cli_handlers.validation.collection import (
    collect_validation_source,
)
from maintenance_window.cli_handlers.validation.rendering import (
    render_validation_result,
)
from maintenance_window.cli_handlers.validation.request import (
    validate_validation_request,
)


def run_bgp_validation(args: argparse.Namespace) -> int:
    """Collect, filter, render, and optionally persist BGP state."""
    validate_validation_request(args)
    status_filter = cast(StatusFilter, args.filter)
    artifacts = collect_validation_source(args)
    filtered = filter_sessions(
        sessions=artifacts.sessions,
        status_filter=status_filter,
    )

    return render_validation_result(
        args=args,
        status_filter=status_filter,
        artifacts=artifacts,
        filtered_sessions=filtered,
    )
