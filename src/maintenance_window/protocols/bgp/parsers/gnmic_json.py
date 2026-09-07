from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from maintenance_window.core.files import load_json_documents
from maintenance_window.protocols.bgp.state.models import BgpSession, normalize_state


_NEIGHBOR_KEY_NAMES = {
    "neighbor",
    "neighbor_address",
    "neighbor-address",
    "neighbor_ip",
    "neighbor-ip",
    "peer",
    "peer_address",
    "peer-address",
}

_VALID_SESSION_STATES = frozenset(
    {
        "Established",
        "Idle",
        "Connect",
        "Active",
        "OpenSent",
        "OpenConfirm",
        "Unknown",
    }
)

_SESSION_STATE_LEAVES = frozenset({"session-state", "peer-state"})


def _deduplicate(sessions: Iterable[BgpSession]) -> list[BgpSession]:
    result: list[BgpSession] = []
    seen: set[tuple[str, str, str]] = set()
    for session in sessions:
        key = (session.device, session.neighbor, session.state)
        if key not in seen:
            seen.add(key)
            result.append(session)
    return result


def _normalized_state(value: object) -> str | None:
    """Return a canonical BGP FSM state or ``None`` for loose values."""
    state = normalize_state(value)
    return state if state in _VALID_SESSION_STATES else None


def _normalized_records(node: Any, fallback_device: str) -> list[BgpSession]:
    """Read already-normalized records without losing their device field."""
    records = node if isinstance(node, list) else [node]
    sessions: list[BgpSession] = []

    for record in records:
        if not isinstance(record, dict):
            continue

        neighbor = (
            record.get("neighbor")
            or record.get("neighbor-address")
            or record.get("neighbor_address")
        )
        state_value = (
            record.get("state")
            if "state" in record
            else record.get("peer_state", record.get("session_state"))
        )
        if neighbor is None or state_value is None:
            continue

        state = _normalized_state(state_value)
        if state is None:
            continue

        sessions.append(
            BgpSession(
                device=str(record.get("device") or fallback_device),
                neighbor=str(neighbor),
                state=state,
            )
        )

    return sessions


def _iter_notifications(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        updates = node.get("update")
        if "prefix" in node and isinstance(updates, list):
            yield node
        for value in node.values():
            yield from _iter_notifications(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_notifications(value)


def _path_elements(path: Any) -> list[dict[str, Any]]:
    if not isinstance(path, dict):
        return []
    elements = path.get("elem", [])
    return [item for item in elements if isinstance(item, dict)]


def _neighbor_from_elements(elements: list[dict[str, Any]]) -> str | None:
    for element in elements:
        keys = element.get("key", {})
        if not isinstance(keys, dict):
            continue
        for key, value in keys.items():
            if str(key).lower() in _NEIGHBOR_KEY_NAMES:
                return str(value)
    return None


def _neighbor_from_text(text: str) -> str | None:
    pattern = re.compile(
        r"(?:neighbor(?:[-_]address|[-_]ip)?|peer(?:[-_]address)?)=([^\]\s/]+)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def _value_from_typed_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value

    for key in (
        "stringVal",
        "asciiVal",
        "intVal",
        "uintVal",
        "boolVal",
        "floatVal",
        "decimalVal",
    ):
        if key in value:
            return value[key]

    for key in ("jsonVal", "jsonIetfVal"):
        if key not in value:
            continue
        raw = value[key]
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return raw
            if isinstance(parsed, dict):
                for state_key in ("session-state", "peer-state"):
                    if state_key in parsed:
                        return parsed[state_key]
            return parsed
        return raw

    if len(value) == 1:
        return next(iter(value.values()))
    return value


def _final_leaf(elements: list[dict[str, Any]]) -> str | None:
    for element in reversed(elements):
        name = str(element.get("name", "")).strip().lower()
        if name:
            return name
    return None


def _parse_protojson(document: Any, fallback_device: str) -> list[BgpSession]:
    """Parse only explicit session-state leaves, never the ``state`` container."""
    sessions: list[BgpSession] = []

    for notification in _iter_notifications(document):
        prefix = notification.get("prefix", {})
        prefix_elements = _path_elements(prefix)
        device = str(
            prefix.get("target")
            or notification.get("source")
            or fallback_device
        )

        for update in notification.get("update", []):
            if not isinstance(update, dict):
                continue

            update_elements = _path_elements(update.get("path"))
            all_elements = prefix_elements + update_elements
            if _final_leaf(all_elements) not in _SESSION_STATE_LEAVES:
                continue

            neighbor = _neighbor_from_elements(all_elements)
            if neighbor is None:
                neighbor = _neighbor_from_text(json.dumps(all_elements))

            state = _normalized_state(
                _value_from_typed_value(update.get("val"))
            )
            if neighbor and state is not None:
                sessions.append(
                    BgpSession(
                        device=device,
                        neighbor=neighbor,
                        state=state,
                    )
                )

    return sessions


def _parse_event_format(document: Any, fallback_device: str) -> list[BgpSession]:
    events = document if isinstance(document, list) else [document]
    sessions: list[BgpSession] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        values = event.get("values", {})
        tags = event.get("tags", {})
        if not isinstance(values, dict) or not isinstance(tags, dict):
            continue

        device = str(event.get("source") or event.get("target") or fallback_device)
        neighbor = None
        for key, value in tags.items():
            if str(key).lower() in _NEIGHBOR_KEY_NAMES:
                neighbor = str(value)
                break

        for path, value in values.items():
            leaf = str(path).rstrip("/").split("/")[-1].lower()
            if leaf not in _SESSION_STATE_LEAVES:
                continue

            event_neighbor = neighbor or _neighbor_from_text(str(path))
            state = _normalized_state(value)
            if event_neighbor and state is not None:
                sessions.append(
                    BgpSession(
                        device=device,
                        neighbor=event_neighbor,
                        state=state,
                    )
                )

    return sessions


def parse_gnmic_json(path: Path, fallback_device: str = "unknown") -> list[BgpSession]:
    """Normalize gNMIc JSON/protojson/event output or normalized JSON records."""
    documents = load_json_documents(path)
    sessions: list[BgpSession] = []

    for document in documents:
        sessions.extend(_normalized_records(document, fallback_device))
        sessions.extend(_parse_protojson(document, fallback_device))
        sessions.extend(_parse_event_format(document, fallback_device))

    sessions = _deduplicate(sessions)
    if not sessions:
        raise ValueError(
            "No BGP sessions were found in the JSON file. "
            "The gNMI path or output shape may require a parser adapter."
        )
    return sessions
