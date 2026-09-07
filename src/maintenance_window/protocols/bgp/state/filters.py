from __future__ import annotations

from collections import defaultdict
from typing import Literal

from maintenance_window.protocols.bgp.state.models import BgpSession


StatusFilter = Literal["healthy", "unhealthy", "all"]
VALID_FILTERS: set[str] = {"healthy", "unhealthy", "all"}


def filter_sessions(
    sessions: list[BgpSession],
    status_filter: StatusFilter,
) -> list[BgpSession]:
    if status_filter not in VALID_FILTERS:
        raise ValueError("Filter must be healthy, unhealthy, or all.")

    if status_filter == "all":
        return list(sessions)
    if status_filter == "healthy":
        return [session for session in sessions if session.is_healthy]
    return [session for session in sessions if not session.is_healthy]


def group_sessions(
    sessions: list[BgpSession],
) -> dict[str, list[dict[str, str]]]:
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for session in sessions:
        grouped[session.device].append(
            {"neighbor": session.neighbor, "state": session.state}
        )
    return dict(grouped)
