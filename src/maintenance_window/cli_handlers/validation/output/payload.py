"""Build the shared validation output payload."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from maintenance_window.cli_handlers.validation.models import (
    ValidationArtifacts,
)
from maintenance_window.protocols.bgp.state.filters import StatusFilter
from maintenance_window.protocols.bgp.state.models import BgpSession


def _is_unhealthy(session: BgpSession) -> bool:
    return session.state.lower() != "established"


def _path(value: Path | None) -> str | None:
    if value is None:
        return None
    return str(value)


def group_sessions_for_output(
    sessions: list[BgpSession],
) -> dict[str, list[dict[str, str]]]:
    """Create the stable device/neighbor/state CLI report mapping."""
    grouped: dict[str, list[dict[str, str]]] = {}

    for session in sessions:
        grouped.setdefault(session.device, []).append(
            {
                "neighbor": session.neighbor,
                "state": session.state,
            }
        )

    return grouped


def build_collection_errors_for_output(
    artifacts: ValidationArtifacts,
) -> list[dict[str, str]]:
    """Create stable collection error records for CLI and export output."""
    return [
        {
            "device": error.device,
            "source": error.source,
            "error_type": error.error_type,
            "error": error.error,
        }
        for error in artifacts.device_errors
    ]


def _actual_source_by_device(artifacts: ValidationArtifacts) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in artifacts.actual_sources:
        if ": " in item:
            device, source = item.split(": ", 1)
            result[device] = source
        else:
            result[item] = "unknown"
    return result


def _session_count_by_device(sessions: list[BgpSession]) -> Counter[str]:
    return Counter(session.device for session in sessions)


def _unhealthy_count_by_device(sessions: list[BgpSession]) -> Counter[str]:
    return Counter(
        session.device
        for session in sessions
        if _is_unhealthy(session)
    )


def _per_device_summary(
    *,
    artifacts: ValidationArtifacts,
) -> list[dict[str, Any]]:
    actual_sources = _actual_source_by_device(artifacts)
    session_counts = _session_count_by_device(artifacts.sessions)
    unhealthy_counts = _unhealthy_count_by_device(artifacts.sessions)

    rows: list[dict[str, Any]] = []
    for device in sorted(set(actual_sources) | set(session_counts)):
        rows.append(
            {
                "device": device,
                "source": actual_sources.get(device, "unknown"),
                "sessions": session_counts.get(device, 0),
                "unhealthy": unhealthy_counts.get(device, 0),
                "status": "COLLECTED",
            }
        )

    for error in artifacts.device_errors:
        rows.append(
            {
                "device": error.device,
                "source": error.source,
                "sessions": 0,
                "unhealthy": 0,
                "status": "FAILED",
            }
        )

    return sorted(rows, key=lambda item: (item["status"], item["device"]))


def _session_state_summary(sessions: list[BgpSession]) -> dict[str, int]:
    counts = Counter(session.state for session in sessions)
    return dict(sorted(counts.items()))


def _report_files_for_payload(
    report_files: dict[str, Path] | None,
) -> dict[str, str] | None:
    if not report_files:
        return None
    return {key: str(value) for key, value in sorted(report_files.items())}


def build_validation_report_payload(
    *,
    args: argparse.Namespace,
    status_filter: StatusFilter,
    artifacts: ValidationArtifacts,
    filtered_sessions: list[BgpSession],
    exit_code: int,
    report_files: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Build one JSON-serializable validation report payload."""
    devices_collected = len(artifacts.actual_sources)
    devices_failed = len(artifacts.device_errors)

    result = "PASS"
    if devices_failed:
        result = "PARTIAL_COLLECTION"
    elif any(_is_unhealthy(session) for session in filtered_sessions):
        result = "PASS_WITH_UNHEALTHY_SESSIONS"

    payload: dict[str, Any] = {
        "protocol": str(getattr(args, "protocol", "bgp")).lower(),
        "source_requested": getattr(args, "source", None),
        "workers": getattr(args, "workers", None),
        "auth_backend": getattr(args, "auth_backend", None),
        "device_selector": getattr(args, "device", None),
        "mw_id": getattr(args, "mw_id", None),
        "snapshot_stage": getattr(args, "snapshot", None),
        "filter": str(status_filter),
        "collection_summary": {
            "devices_selected": devices_collected + devices_failed,
            "devices_collected": devices_collected,
            "devices_failed": devices_failed,
            "sessions_collected": len(artifacts.sessions),
            "sessions_selected": len(filtered_sessions),
        },
        "session_state_summary": _session_state_summary(filtered_sessions),
        "per_device_summary": _per_device_summary(artifacts=artifacts),
        "sessions": group_sessions_for_output(filtered_sessions),
        "collection_errors": build_collection_errors_for_output(artifacts),
        "artifacts": {
            "raw_files_saved": len(artifacts.raw_files),
            "raw_files": [_path(path) for path in artifacts.raw_files],
            "snapshots_saved": len(artifacts.snapshot_files),
            "snapshot_files": [_path(path) for path in artifacts.snapshot_files],
            "manual_database_ids": list(artifacts.manual_database_ids),
            "validation_report_files": _report_files_for_payload(report_files),
        },
        "detail_lines": list(artifacts.detail_lines),
        "result": result,
        "exit_code": exit_code,
    }
    return payload
