from __future__ import annotations

from typing import Any

from maintenance_window.engine.snapshots.contracts import (
    SnapshotAdapter,
)
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_store.serialization import (
    duplicate_to_dict,
    session_from_dict,
    session_to_dict,
)
from maintenance_window.protocols.bgp.snapshot_store.sessions import (
    build_session_map,
    duplicate_count,
    find_duplicates,
    is_unhealthy_session,
)


def _build_bgp_snapshot_summary(
    sessions: list[BgpSession],
) -> dict[str, Any]:
    session_map = build_session_map(sessions)
    duplicates = find_duplicates(sessions)
    unhealthy_sessions = [
        session
        for session in sessions
        if is_unhealthy_session(session)
    ]

    return {
        "total_sessions": len(sessions),
        "unique_sessions": len(session_map),
        "duplicate_entries": duplicate_count(
            duplicates
        ),
        "unhealthy_sessions": len(
            unhealthy_sessions
        ),
    }


def _build_bgp_snapshot_details(
    sessions: list[BgpSession],
) -> dict[str, Any]:
    return {
        "duplicates": [
            duplicate_to_dict(item)
            for item in find_duplicates(sessions)
        ]
    }


BGP_SNAPSHOT_ADAPTER = SnapshotAdapter[BgpSession](
    protocol="bgp",
    items_field="sessions",
    serialize_item=session_to_dict,
    deserialize_item=session_from_dict,
    build_summary=_build_bgp_snapshot_summary,
    build_details=_build_bgp_snapshot_details,
)
