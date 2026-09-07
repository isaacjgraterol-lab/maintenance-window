from __future__ import annotations

from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshotDuplicateSession,
    BgpSnapshotSessionKey,
)


def is_healthy_state(state: str) -> bool:
    """Return whether a BGP state is Established."""
    return state.strip().lower() == "established"


def is_unhealthy_session(session: BgpSession) -> bool:
    """Return whether a BGP session is not Established."""
    return not is_healthy_state(session.state)


def build_session_key(
    session: BgpSession,
) -> BgpSnapshotSessionKey:
    """Build the device-and-neighbor comparison key."""
    return BgpSnapshotSessionKey(
        device=session.device,
        neighbor=session.neighbor,
    )


def build_session_map(
    sessions: list[BgpSession],
) -> dict[BgpSnapshotSessionKey, BgpSession]:
    """Build a unique map where the last duplicate record wins."""
    session_map: dict[BgpSnapshotSessionKey, BgpSession] = {}

    for session in sessions:
        session_map[build_session_key(session)] = session

    return session_map


def build_session_groups(
    sessions: list[BgpSession],
) -> dict[BgpSnapshotSessionKey, list[BgpSession]]:
    """Group sessions by device and neighbor."""
    groups: dict[
        BgpSnapshotSessionKey,
        list[BgpSession],
    ] = {}

    for session in sessions:
        key = build_session_key(session)
        groups.setdefault(key, []).append(session)

    return groups


def find_duplicates(
    sessions: list[BgpSession],
) -> list[BgpSnapshotDuplicateSession]:
    """Find duplicate BGP entries inside a snapshot."""
    groups = build_session_groups(sessions)
    duplicates: list[BgpSnapshotDuplicateSession] = []

    for key, grouped_sessions in sorted(
        groups.items(),
        key=lambda item: (
            item[0].device,
            item[0].neighbor,
        ),
    ):
        if len(grouped_sessions) <= 1:
            continue

        duplicates.append(
            BgpSnapshotDuplicateSession(
                device=key.device,
                neighbor=key.neighbor,
                count=len(grouped_sessions),
                states=sorted(
                    {
                        session.state
                        for session in grouped_sessions
                    }
                ),
            )
        )

    return duplicates


def duplicate_count(
    duplicates: list[BgpSnapshotDuplicateSession],
) -> int:
    """Count duplicate entries beyond each first unique record."""
    return sum(
        item.count - 1
        for item in duplicates
    )
