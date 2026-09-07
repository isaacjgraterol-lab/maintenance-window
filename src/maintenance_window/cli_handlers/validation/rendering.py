"""Render, persist, and optionally export one validation result."""

from __future__ import annotations

import argparse

from maintenance_window.cli_handlers.validation.defaults import (
    DEFAULT_BGP_SNAPSHOT_ROOT,
)
from maintenance_window.cli_handlers.validation.models import (
    ValidationArtifacts,
)
from maintenance_window.cli_handlers.validation.output.payload import (
    build_collection_errors_for_output,
    build_validation_report_payload,
    group_sessions_for_output,
)
from maintenance_window.cli_handlers.validation.output.terminal import (
    render_terminal_output,
)
from maintenance_window.cli_handlers.validation.output.writer import (
    build_report_paths_for_snapshot_run,
    write_snapshot_validation_reports,
)
from maintenance_window.core.output import export_json_report
from maintenance_window.protocols.bgp.state.filters import StatusFilter
from maintenance_window.protocols.bgp.state.models import BgpSession


def render_collection_errors(artifacts: ValidationArtifacts) -> None:
    """Print per-device collection errors, if any. Kept for tests/helpers."""
    if not artifacts.device_errors:
        return

    print("\nCollection errors:")
    for error in artifacts.device_errors:
        print(
            "- "
            f"{error.device} "
            f"[{error.source}] "
            f"{error.error_type}: "
            f"{error.error}"
        )


def _exit_code_for_artifacts(artifacts: ValidationArtifacts) -> int:
    if artifacts.device_errors:
        return 2
    return 0


def _snapshot_report_paths(args: argparse.Namespace):
    return build_report_paths_for_snapshot_run(
        snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
        mw_id=getattr(args, "mw_id", None),
        stage=getattr(args, "snapshot", None),
    )


def render_validation_result(
    *,
    args: argparse.Namespace,
    status_filter: StatusFilter,
    artifacts: ValidationArtifacts,
    filtered_sessions: list[BgpSession],
) -> int:
    """Print selected output and save snapshot validation reports."""
    exit_code = _exit_code_for_artifacts(artifacts)
    report_paths = _snapshot_report_paths(args)
    report_files = report_paths.as_dict() if report_paths is not None else None

    payload = build_validation_report_payload(
        args=args,
        status_filter=status_filter,
        artifacts=artifacts,
        filtered_sessions=filtered_sessions,
        exit_code=exit_code,
        report_files=report_files,
    )

    if report_paths is not None:
        artifacts.validation_report_files.update(
            write_snapshot_validation_reports(
                paths=report_paths,
                payload=payload,
            )
        )

    output_mode = getattr(args, "output", "summary") or "summary"
    print(render_terminal_output(output_mode=output_mode, payload=payload), end="")

    if args.export:
        export_path = args.export.resolve()
        export_json_report(payload, export_path)
        print(f"Report saved: {export_path}")

    return exit_code
