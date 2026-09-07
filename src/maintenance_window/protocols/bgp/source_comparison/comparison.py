"""
Pure BGP source-comparison logic.

This module compares already-normalized BGP sessions. It does not
collect from devices, read credentials, or print reports.
"""

from __future__ import annotations

from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.source_comparison.models import (
    BgpDuplicateSession,
    BgpSessionKey,
    BgpSessionStateDifference,
    BgpSourceComparison,
)


def _build_session_groups(
    sessions: list[BgpSession],
) -> dict[BgpSessionKey, list[BgpSession]]:
    """
    Group BGP sessions by device and neighbor.

    This preserves duplicate records instead of hiding them.
    """
    groups: dict[BgpSessionKey, list[BgpSession]] = {}

    for session in sessions:
        key = BgpSessionKey(
            device=session.device,
            neighbor=session.neighbor,
        )
        groups.setdefault(key, []).append(session)

    return groups


def _build_session_map(
    sessions: list[BgpSession],
) -> dict[BgpSessionKey, BgpSession]:
    """
    Convert a list of BGP sessions into a dictionary for comparison.

    If the same device/neighbor appears more than once, the last record wins
    for state comparison, but duplicates are reported separately.
    """
    session_map: dict[BgpSessionKey, BgpSession] = {}

    for session in sessions:
        key = BgpSessionKey(
            device=session.device,
            neighbor=session.neighbor,
        )
        session_map[key] = session

    return session_map


def _find_duplicates(
    sessions: list[BgpSession],
) -> list[BgpDuplicateSession]:
    """
    Find duplicate BGP entries for the same device/neighbor key.
    """
    groups = _build_session_groups(sessions)
    duplicates: list[BgpDuplicateSession] = []

    for key, grouped_sessions in sorted(
        groups.items(),
        key=lambda item: (item[0].device, item[0].neighbor),
    ):
        if len(grouped_sessions) <= 1:
            continue

        states = sorted(
            {
                session.state
                for session in grouped_sessions
            }
        )

        duplicates.append(
            BgpDuplicateSession(
                device=key.device,
                neighbor=key.neighbor,
                count=len(grouped_sessions),
                states=states,
            )
        )

    return duplicates


def compare_bgp_sources(
    left_source: str,
    left_sessions: list[BgpSession],
    right_source: str,
    right_sessions: list[BgpSession],
) -> BgpSourceComparison:
    """
    Compare normalized BGP sessions from two different sources.

    It reports:
    - total session records
    - unique device/neighbor sessions
    - duplicate records per source
    - sessions only in the left source
    - sessions only in the right source
    - sessions present in both sources but with different state
    """
    left_map = _build_session_map(left_sessions)
    right_map = _build_session_map(right_sessions)

    left_keys = set(left_map)
    right_keys = set(right_map)

    common_keys = left_keys & right_keys
    only_left_keys = left_keys - right_keys
    only_right_keys = right_keys - left_keys

    left_duplicates = _find_duplicates(left_sessions)
    right_duplicates = _find_duplicates(right_sessions)

    different_state: list[BgpSessionStateDifference] = []

    for key in sorted(
        common_keys,
        key=lambda item: (item.device, item.neighbor),
    ):
        left_session = left_map[key]
        right_session = right_map[key]

        if left_session.state != right_session.state:
            different_state.append(
                BgpSessionStateDifference(
                    device=key.device,
                    neighbor=key.neighbor,
                    left_state=left_session.state,
                    right_state=right_session.state,
                )
            )

    return BgpSourceComparison(
        left_source=left_source,
        right_source=right_source,
        left_count=len(left_sessions),
        right_count=len(right_sessions),
        left_unique_count=len(left_keys),
        right_unique_count=len(right_keys),
        common_count=len(common_keys),
        left_duplicate_count=sum(
            item.count - 1
            for item in left_duplicates
        ),
        right_duplicate_count=sum(
            item.count - 1
            for item in right_duplicates
        ),
        left_duplicates=left_duplicates,
        right_duplicates=right_duplicates,
        only_left=[
            left_map[key]
            for key in sorted(
                only_left_keys,
                key=lambda item: (item.device, item.neighbor),
            )
        ],
        only_right=[
            right_map[key]
            for key in sorted(
                only_right_keys,
                key=lambda item: (item.device, item.neighbor),
            )
        ],
        different_state=different_state,
    )
