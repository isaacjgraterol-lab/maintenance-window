"""Execute the live BGP source-comparison workflow."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maintenance_window.core.credentials import load_credentials
from maintenance_window.core.inventory import load_devices
from maintenance_window.core.output import export_json_report
from maintenance_window.protocols.bgp.service import compare_live_sources
from maintenance_window.protocols.bgp.source_comparison.reports import (
    comparison_to_dict,
    print_comparison_report,
)
from maintenance_window.cli_handlers.source_comparison.comparison import (
    compare_device_sources,
)
from maintenance_window.cli_handlers.source_comparison.defaults import (
    PROJECT_ROOT,
)
from maintenance_window.cli_handlers.source_comparison.exporting import (
    export_source_comparison_report,
)
from maintenance_window.cli_handlers.source_comparison.rendering import (
    print_device_comparison,
    print_device_comparison_heading,
    print_source_comparison_export,
)
from maintenance_window.cli_handlers.source_comparison.request import (
    build_source_comparison_request,
)
from maintenance_window.cli_handlers.source_comparison.runtime import (
    build_source_comparison_runtime,
    load_protocol_runtime_settings,
)


def run_bgp_source_comparison(
    args: argparse.Namespace,
    *,
    load_devices_fn: Callable[..., Any] = load_devices,
    load_credentials_fn: Callable[..., Any] = load_credentials,
    load_settings_fn: Callable[..., Any] = load_protocol_runtime_settings,
    compare_live_sources_fn: Callable[..., Any] = compare_live_sources,
    print_comparison_report_fn: Callable[..., Any] = print_comparison_report,
    comparison_to_dict_fn: Callable[..., Any] = comparison_to_dict,
    export_json_report_fn: Callable[..., Any] = export_json_report,
    project_root: Path = PROJECT_ROOT,
) -> int:
    """Compare selected devices and return zero only when all reports pass."""
    request = build_source_comparison_request(
        args,
        load_devices_fn=load_devices_fn,
    )
    runtime = build_source_comparison_runtime(
        args,
        load_credentials_fn=load_credentials_fn,
        load_settings_fn=load_settings_fn,
        project_root=project_root,
    )
    results = []

    for device in request.devices:
        print_device_comparison_heading(request, device)
        result = compare_device_sources(
            request,
            runtime,
            device,
            compare_live_sources_fn=compare_live_sources_fn,
            comparison_to_dict_fn=comparison_to_dict_fn,
        )
        results.append(result)
        print_device_comparison(
            result,
            print_comparison_report_fn=print_comparison_report_fn,
        )

    export_path = export_source_comparison_report(
        request,
        results,
        export_json_report_fn=export_json_report_fn,
    )
    if export_path is not None:
        print_source_comparison_export(export_path)

    has_failure = any(
        result.report.get("result") == "FAIL"
        for result in results
    )
    return 1 if has_failure else 0
