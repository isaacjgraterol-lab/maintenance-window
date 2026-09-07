"""Public compatibility facade for live BGP source comparison."""

from __future__ import annotations

import argparse

from maintenance_window.core.credentials import load_credentials
from maintenance_window.core.inventory import load_devices
from maintenance_window.core.output import export_json_report
from maintenance_window.protocols.bgp.service import compare_live_sources
from maintenance_window.protocols.bgp.source_comparison.reports import (
    comparison_to_dict,
    print_comparison_report,
)
from maintenance_window.cli_handlers.source_comparison.defaults import (
    PROJECT_ROOT,
)
from maintenance_window.cli_handlers.source_comparison.execution import (
    run_bgp_source_comparison as _run_bgp_source_comparison,
)
from maintenance_window.cli_handlers.source_comparison.request import (
    parse_source_compare_argument,
    resolve_devices as _resolve_devices,
)
from maintenance_window.cli_handlers.source_comparison.runtime import (
    load_protocol_runtime_settings as _load_protocol_runtime_settings,
)


def run_bgp_source_comparison(args: argparse.Namespace) -> int:
    """Run source comparison using facade-level compatibility dependencies."""
    return _run_bgp_source_comparison(
        args,
        load_devices_fn=load_devices,
        load_credentials_fn=load_credentials,
        load_settings_fn=_load_protocol_runtime_settings,
        compare_live_sources_fn=compare_live_sources,
        print_comparison_report_fn=print_comparison_report,
        comparison_to_dict_fn=comparison_to_dict,
        export_json_report_fn=export_json_report,
        project_root=PROJECT_ROOT,
    )


__all__ = [
    "parse_source_compare_argument",
    "run_bgp_source_comparison",
]
