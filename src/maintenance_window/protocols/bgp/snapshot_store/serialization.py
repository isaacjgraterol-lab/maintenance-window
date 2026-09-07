from __future__ import annotations

from typing import Any

from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshotDuplicateSession,
)


def session_to_dict(
    session: BgpSession,
) -> dict[str, Any]:
    """Convert a normalized BGP session to a JSON-ready dictionary."""
    return session.to_dict()


def session_from_dict(
    data: dict[str, Any],
    fallback_device: str,
) -> BgpSession:
    """Build a normalized BGP session from snapshot JSON."""
    return BgpSession(
        device=str(
            data.get("device", fallback_device)
        ),
        neighbor=str(data["neighbor"]),
        state=str(data["state"]),
    )


def duplicate_to_dict(
    duplicate: BgpSnapshotDuplicateSession,
) -> dict[str, Any]:
    """Convert duplicate metadata to a JSON-ready dictionary."""
    return {
        "device": duplicate.device,
        "neighbor": duplicate.neighbor,
        "count": duplicate.count,
        "states": duplicate.states,
    }
