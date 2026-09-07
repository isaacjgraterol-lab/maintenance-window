"""Snapshot persistence helpers for collected validation sessions."""

from __future__ import annotations

import argparse
from pathlib import Path

from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshots import write_bgp_snapshot


def sessions_by_device(
    sessions: list[BgpSession],
) -> dict[str, list[BgpSession]]:
    """Group normalized sessions using their device field."""
    grouped: dict[str, list[BgpSession]] = {}

    for session in sessions:
        grouped.setdefault(session.device, []).append(session)

    return grouped


def write_file_snapshots(
    *,
    args: argparse.Namespace,
    sessions: list[BgpSession],
    fallback_device: str,
    snapshot_root: Path,
) -> list[Path]:
    """Persist per-device snapshots for an existing JSON or XML input."""
    if not args.snapshot:
        return []

    grouped = sessions_by_device(sessions)

    if not grouped:
        grouped = {fallback_device: []}

    return [
        write_bgp_snapshot(
            snapshot_root=snapshot_root,
            mw_id=args.mw_id,
            stage=args.snapshot,
            device=device_name,
            source_requested=args.source,
            source_actual=args.source,
            raw_file=args.input.resolve(),
            sessions=device_sessions,
        )
        for device_name, device_sessions in grouped.items()
    ]


def write_live_snapshot(
    *,
    args: argparse.Namespace,
    device_name: str,
    actual_source: str,
    raw_file: Path,
    sessions: list[BgpSession],
    snapshot_root: Path,
) -> Path | None:
    """Persist one live-device snapshot when snapshot mode is enabled."""
    if not args.snapshot:
        return None

    return write_bgp_snapshot(
        snapshot_root=snapshot_root,
        mw_id=args.mw_id,
        stage=args.snapshot,
        device=device_name,
        source_requested=args.source,
        source_actual=actual_source,
        raw_file=raw_file,
        sessions=sessions,
    )
