from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from maintenance_window.protocols.bgp.state.models import BgpSession, normalize_state
from maintenance_window.core.files import load_json_documents


def _local_key(value: object) -> str:
    return str(value).rsplit(":", maxsplit=1)[-1].lower()


def _scalar(node: Any) -> Any:
    """Unwrap Junos JSON containers such as [{"data": "value"}]."""
    if isinstance(node, list):
        for item in node:
            value = _scalar(item)
            if value is not None:
                return value
        return None

    if isinstance(node, dict):
        for key in ("data", "value"):
            if key in node:
                return _scalar(node[key])
        if len(node) == 1:
            return _scalar(next(iter(node.values())))
        return None

    return node


def _iter_peer_records(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if _local_key(key) == "bgp-peer":
                records = value if isinstance(value, list) else [value]
                for record in records:
                    if isinstance(record, dict):
                        yield record
            else:
                yield from _iter_peer_records(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_peer_records(item)


def _field(record: dict[str, Any], *names: str) -> Any:
    expected = {name.lower() for name in names}
    for key, value in record.items():
        if _local_key(key) in expected:
            return _scalar(value)
    return None


def _clean_neighbor(value: object) -> str:
    text = str(value).strip()
    return re.sub(r"\+\d+$", "", text)


def parse_ssh_json(
    path: Path,
    device_name: str,
    *,
    require_sessions: bool = True,
) -> list[BgpSession]:
    """Normalize `show bgp summary | display json` output."""
    sessions: list[BgpSession] = []

    for document in load_json_documents(path):
        for record in _iter_peer_records(document):
            neighbor = _field(
                record,
                "peer-address",
                "neighbor-address",
                "neighbor",
            )
            state = _field(
                record,
                "peer-state",
                "session-state",
                "state",
            )

            if neighbor is None or state is None:
                continue

            sessions.append(
                BgpSession(
                    device=device_name,
                    neighbor=_clean_neighbor(neighbor),
                    state=normalize_state(state),
                )
            )

    if require_sessions and not sessions:
        raise ValueError(
            "No BGP sessions were found in the Junos SSH JSON file. "
            "Confirm that it contains `show bgp summary | display json` output."
        )

    return sessions
