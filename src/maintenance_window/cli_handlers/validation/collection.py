"""Collect normalized BGP sessions from manual, file, or live sources."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from maintenance_window.core.credentials import load_credentials
from maintenance_window.core.inventory import load_devices
from maintenance_window.core.models import Device
from maintenance_window.engine.live_collection import (
    LiveCollectionFailure,
    LiveCollectionSuccess,
    collect_parallel,
    collect_sequential,
)
from maintenance_window.protocols.bgp.manual import store_manual_bgp_upload
from maintenance_window.protocols.bgp.service import (
    collect_live as collect_live_sessions,
    parse_input_file,
)
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.cli_handlers.validation.defaults import (
    DEFAULT_BGP_SNAPSHOT_ROOT,
    FILE_SOURCES,
    LIVE_SOURCES,
    MANUAL_SOURCE,
    PROJECT_ROOT,
)
from maintenance_window.cli_handlers.validation.models import (
    DeviceCollectionError,
    ValidationArtifacts,
)
from maintenance_window.cli_handlers.validation.persistence import (
    write_file_snapshots,
    write_live_snapshot,
)
from maintenance_window.cli_handlers.validation.request import (
    load_protocol_runtime_settings,
    resolve_devices,
)

LiveDevicePayload = tuple[list[BgpSession], Path, str, Path | None]


def collect_manual_source(
    args: argparse.Namespace,
) -> ValidationArtifacts:
    """Archive, parse, store, and snapshot one operator-supplied input."""
    if args.input is None:
        raise ValueError("--input is required for manual upload.")

    if not args.snapshot:
        raise ValueError(
            "--snapshot before|after is required for manual upload."
        )

    manual_device = args.device or "Manual Input"
    manual_result = store_manual_bgp_upload(
        input_file=args.input,
        input_format=args.input_format,
        db_path=args.local_db.resolve(),
        snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
        mw_id=args.mw_id,
        stage=args.snapshot,
        device=manual_device,
    )

    return ValidationArtifacts(
        sessions=list(manual_result.sessions),
        raw_files=[manual_result.raw_file],
        actual_sources=[f"{manual_device}: Local DB"],
        snapshot_files=[manual_result.snapshot_file],
        manual_database_ids=[manual_result.database_id],
        detail_lines=[
            f"Manual DB: {args.local_db.resolve()}",
            f"Manual DB row ID: {manual_result.database_id}",
            f"Manual input format: {manual_result.input_format}",
            (
                "Original manual input: "
                f"{manual_result.original_input_file}"
            ),
            f"Manual raw SHA256: {manual_result.raw_sha256}",
        ],
    )


def collect_file_source(
    args: argparse.Namespace,
) -> ValidationArtifacts:
    """Parse one existing JSON or XML file and optionally snapshot it."""
    if args.input is None:
        raise ValueError("--input is required for file collection.")

    fallback_device = args.device or "file-input"
    sessions = parse_input_file(
        path=args.input.resolve(),
        source=args.source,
        fallback_device=fallback_device,
    )

    return ValidationArtifacts(
        sessions=list(sessions),
        snapshot_files=write_file_snapshots(
            args=args,
            sessions=sessions,
            fallback_device=fallback_device,
            snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
        ),
    )


def _build_device_collection_error(
    *,
    device_name: str,
    source: str,
    exc: Exception,
) -> DeviceCollectionError:
    """Convert one live collection exception into reportable metadata."""
    return DeviceCollectionError(
        device=device_name,
        source=source,
        error_type=type(exc).__name__,
        error=str(exc),
    )


def _collect_one_live_device(
    *,
    args: argparse.Namespace,
    device: Device,
    defaults: dict[str, object],
    profiles: dict[str, Any],
    settings: dict[str, Any],
) -> LiveDevicePayload:
    """Collect and optionally snapshot one live device."""
    collected, raw_file, actual_source = collect_live_sessions(
        source=args.source,
        device=device,
        defaults=defaults,
        profiles=profiles,
        settings=settings,
        project_root=PROJECT_ROOT,
        auth_backend=args.auth_backend,
    )

    snapshot_file = write_live_snapshot(
        args=args,
        device_name=device.host,
        actual_source=actual_source,
        raw_file=raw_file,
        sessions=collected,
        snapshot_root=DEFAULT_BGP_SNAPSHOT_ROOT,
    )

    return collected, raw_file, actual_source, snapshot_file


def _collect_selected_live_devices(
    *,
    args: argparse.Namespace,
    selected_devices: list[Device],
    defaults: dict[str, object],
    profiles: dict[str, Any],
    settings: dict[str, Any],
) -> list[
    LiveCollectionSuccess[Device, LiveDevicePayload]
    | LiveCollectionFailure[Device]
]:
    """Run live collection using the requested worker count."""
    workers = getattr(args, "workers", 1) or 1

    def collect_device(device: Device) -> LiveDevicePayload:
        return _collect_one_live_device(
            args=args,
            device=device,
            defaults=defaults,
            profiles=profiles,
            settings=settings,
        )

    if workers == 1:
        return collect_sequential(selected_devices, collect_device)

    return collect_parallel(
        selected_devices,
        collect_device,
        max_workers=workers,
    )


def _store_live_result(
    *,
    artifacts: ValidationArtifacts,
    result: (
        LiveCollectionSuccess[Device, LiveDevicePayload]
        | LiveCollectionFailure[Device]
    ),
    requested_source: str,
) -> None:
    """Store one per-device live collection result in validation artifacts."""
    if isinstance(result, LiveCollectionFailure):
        artifacts.device_errors.append(
            _build_device_collection_error(
                device_name=result.item.host,
                source=requested_source,
                exc=result.error,
            )
        )
        return

    collected, raw_file, actual_source, snapshot_file = result.value
    artifacts.sessions.extend(collected)
    artifacts.raw_files.append(raw_file)
    artifacts.actual_sources.append(
        f"{result.item.host}: {actual_source}"
    )

    if snapshot_file is not None:
        artifacts.snapshot_files.append(snapshot_file)


def collect_live_source(
    args: argparse.Namespace,
) -> ValidationArtifacts:
    """Collect all selected inventory devices through a live adapter.

    Multi-device live collection is resilient by design. A failure on one
    device is stored as a per-device collection error and does not prevent
    the remaining selected devices from being collected.
    """
    devices = load_devices(args.inventory.resolve())
    selected_devices = resolve_devices(args.device, devices)
    defaults, profiles = load_credentials(args.credentials.resolve())
    settings = load_protocol_runtime_settings(args)
    artifacts = ValidationArtifacts()

    results = _collect_selected_live_devices(
        args=args,
        selected_devices=selected_devices,
        defaults=defaults,
        profiles=profiles,
        settings=settings,
    )

    for result in results:
        _store_live_result(
            artifacts=artifacts,
            result=result,
            requested_source=args.source,
        )

    return artifacts


def collect_validation_source(
    args: argparse.Namespace,
) -> ValidationArtifacts:
    """Dispatch collection using the source selected by the operator."""
    if args.source == MANUAL_SOURCE:
        return collect_manual_source(args)

    if args.source in FILE_SOURCES:
        return collect_file_source(args)

    if args.source in LIVE_SOURCES:
        return collect_live_source(args)

    raise ValueError(f"Unsupported source: {args.source}")
