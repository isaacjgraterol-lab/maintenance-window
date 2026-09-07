from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from maintenance_window.core.files import load_json_documents, load_xml_root
from maintenance_window.protocols.bgp.parsers.gnmic_json import parse_gnmic_json
from maintenance_window.protocols.bgp.session_health.family_map import family_from_table
from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpSessionHealthRecord,
)
from maintenance_window.protocols.bgp.session_health.uptime import (
    parse_bgp_uptime_to_seconds,
)
from maintenance_window.protocols.bgp.state.models import normalize_state


def _local_name(tag: object) -> str:
    return str(tag).rsplit("}", maxsplit=1)[-1].rsplit(":", maxsplit=1)[-1]


def _clean_neighbor(value: object) -> str:
    text = str(value).strip()
    return re.sub(r"\+\d+$", "", text)


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _child(element: ET.Element, expected_name: str) -> ET.Element | None:
    for child in element:
        if _local_name(child.tag) == expected_name:
            return child
    return None


def _child_text(element: ET.Element, expected_name: str) -> str | None:
    child = _child(element, expected_name)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _first_child_text(element: ET.Element, *names: str) -> str | None:
    for name in names:
        value = _child_text(element, name)
        if value is not None:
            return value
    return None


def _child_texts(element: ET.Element, *names: str) -> list[str]:
    expected = set(names)
    values: list[str] = []
    for child in element:
        if _local_name(child.tag) not in expected or child.text is None:
            continue
        text = child.text.strip()
        if text:
            values.append(text)
    return values


def _attribute(element: ET.Element | None, expected_name: str) -> str | None:
    if element is None:
        return None
    for key, value in element.attrib.items():
        if _local_name(key) == expected_name:
            return value
    return None


def _xml_counter(element: ET.Element, *names: str) -> int | None:
    return _to_int(_first_child_text(element, *names))


def _sum_xml_child_ints(
    elements: list[ET.Element],
    *child_names: str,
) -> int | None:
    values = [
        value
        for element in elements
        for value in [_xml_counter(element, *child_names)]
        if value is not None
    ]
    if not values:
        return None
    return sum(values)


def _sum_family_counter(
    families: list[BgpFamilyHealthCounters],
    field_name: str,
) -> int | None:
    values = [
        value
        for value in (getattr(family, field_name) for family in families)
        if value is not None
    ]
    if not values:
        return None
    return sum(values)


def _xml_family_from_rib(rib: ET.Element) -> BgpFamilyHealthCounters | None:
    table = _child_text(rib, "name")
    if not table:
        return None

    return BgpFamilyHealthCounters(
        table=table,
        family=family_from_table(table),
        rib_state=_child_texts(rib, "bgp-rib-state", "rib-state"),
        send_state=_first_child_text(rib, "send-state", "send-state-string"),
        active_prefix_count=_xml_counter(rib, "active-prefix-count"),
        received_prefix_count=_xml_counter(rib, "received-prefix-count"),
        accepted_prefix_count=_xml_counter(rib, "accepted-prefix-count"),
        suppressed_prefix_count=_xml_counter(
            rib,
            "suppressed-prefix-count",
            "damped-prefix-count",
        ),
        advertised_prefix_count=_xml_counter(
            rib,
            "advertised-prefix-count",
            "advertised-prefixes",
        ),
    )


def extract_pyez_xml_records(
    path: Path,
    *,
    device_name: str,
    source: str | None = None,
) -> list[BgpSessionHealthRecord]:
    """Extract peer-level session-health fields from Junos XML."""
    root = load_xml_root(path)
    records: list[BgpSessionHealthRecord] = []

    for peer in root.iter():
        if _local_name(peer.tag) != "bgp-peer":
            continue

        neighbor = (
            _child_text(peer, "peer-address")
            or _child_text(peer, "neighbor")
            or _child_text(peer, "neighbor-address")
        )
        state = (
            _child_text(peer, "peer-state")
            or _child_text(peer, "state")
            or _child_text(peer, "session-state")
        )

        if neighbor is None or state is None:
            continue

        elapsed = _child(peer, "elapsed-time")
        rib_elements = [
            child
            for child in peer
            if _local_name(child.tag) == "bgp-rib"
        ]
        families = [
            family
            for family in (_xml_family_from_rib(rib) for rib in rib_elements)
            if family is not None
        ]

        records.append(
            BgpSessionHealthRecord(
                device=device_name,
                source=source,
                neighbor=_clean_neighbor(neighbor),
                peer_state=normalize_state(state),
                peer_as=_to_int(_child_text(peer, "peer-as")),
                elapsed_time_raw=(
                    elapsed.text.strip()
                    if elapsed is not None and elapsed.text
                    else None
                ),
                elapsed_time_seconds=(
                    _to_int(_attribute(elapsed, "seconds"))
                    or parse_bgp_uptime_to_seconds(
                        elapsed.text if elapsed is not None else None
                    )
                ),
                flap_count=_to_int(_child_text(peer, "flap-count")),
                received_prefix_count=_sum_family_counter(
                    families,
                    "received_prefix_count",
                ),
                accepted_prefix_count=_sum_family_counter(
                    families,
                    "accepted_prefix_count",
                ),
                active_prefix_count=_sum_family_counter(
                    families,
                    "active_prefix_count",
                ),
                suppressed_prefix_count=_sum_family_counter(
                    families,
                    "suppressed_prefix_count",
                ),
                advertised_prefix_count=_sum_family_counter(
                    families,
                    "advertised_prefix_count",
                ),
                total_prefix_count=_sum_xml_child_ints(
                    rib_elements,
                    "total-prefix-count",
                ),
                families=families,
            )
        )

    return records


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
            if _local_name(key) == "bgp-peer":
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
        if _local_name(key).lower() in expected:
            return _scalar(value)
    return None


def _field_node(record: dict[str, Any], *names: str) -> Any:
    expected = {name.lower() for name in names}
    for key, value in record.items():
        if _local_name(key).lower() in expected:
            return value
    return None


def _field_strings(record: dict[str, Any], *names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        node = _field_node(record, name)
        if node is None:
            continue
        node_items = node if isinstance(node, list) else [node]
        for item in node_items:
            value = _scalar(item)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                values.append(text)
    return values


def _node_attribute(node: Any, expected_name: str) -> Any:
    if isinstance(node, list):
        for item in node:
            value = _node_attribute(item, expected_name)
            if value is not None:
                return value
        return None

    if isinstance(node, dict):
        attributes = node.get("attributes")
        if isinstance(attributes, dict):
            for key, value in attributes.items():
                if _local_name(key).lower() == expected_name.lower():
                    return value

        for value in node.values():
            found = _node_attribute(value, expected_name)
            if found is not None:
                return found

    return None


def _list_field(record: dict[str, Any], name: str) -> list[Any]:
    for key, value in record.items():
        if _local_name(key).lower() == name.lower():
            return value if isinstance(value, list) else [value]
    return []


def _json_counter(record: dict[str, Any], *field_names: str) -> int | None:
    return _to_int(_field(record, *field_names))


def _sum_json_child_ints(
    records: list[Any],
    *field_names: str,
) -> int | None:
    values: list[int] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        value = _json_counter(record, *field_names)
        if value is not None:
            values.append(value)
    if not values:
        return None
    return sum(values)


def _json_family_from_rib(rib: dict[str, Any]) -> BgpFamilyHealthCounters | None:
    table = _field(rib, "name")
    if table is None:
        return None

    table_text = str(table)
    return BgpFamilyHealthCounters(
        table=table_text,
        family=family_from_table(table_text),
        rib_state=_field_strings(rib, "bgp-rib-state", "rib-state"),
        send_state=(
            str(value)
            if (value := _field(rib, "send-state", "send-state-string")) is not None
            else None
        ),
        active_prefix_count=_json_counter(rib, "active-prefix-count"),
        received_prefix_count=_json_counter(rib, "received-prefix-count"),
        accepted_prefix_count=_json_counter(rib, "accepted-prefix-count"),
        suppressed_prefix_count=_json_counter(
            rib,
            "suppressed-prefix-count",
            "damped-prefix-count",
        ),
        advertised_prefix_count=_json_counter(
            rib,
            "advertised-prefix-count",
            "advertised-prefixes",
        ),
    )


def extract_ssh_json_records(
    path: Path,
    *,
    device_name: str,
    source: str | None = None,
) -> list[BgpSessionHealthRecord]:
    """Extract peer-level session-health fields from Junos JSON."""
    records: list[BgpSessionHealthRecord] = []

    for document in load_json_documents(path):
        for peer in _iter_peer_records(document):
            neighbor = _field(
                peer,
                "peer-address",
                "neighbor-address",
                "neighbor",
            )
            state = _field(
                peer,
                "peer-state",
                "session-state",
                "state",
            )

            if neighbor is None or state is None:
                continue

            elapsed_node = _field_node(peer, "elapsed-time")
            rib_records = _list_field(peer, "bgp-rib")
            families = [
                family
                for family in (
                    _json_family_from_rib(rib)
                    for rib in rib_records
                    if isinstance(rib, dict)
                )
                if family is not None
            ]

            records.append(
                BgpSessionHealthRecord(
                    device=device_name,
                    source=source,
                    neighbor=_clean_neighbor(neighbor),
                    peer_state=normalize_state(state),
                    peer_as=_to_int(_field(peer, "peer-as")),
                    elapsed_time_raw=(
                        str(_scalar(elapsed_node))
                        if _scalar(elapsed_node) is not None
                        else None
                    ),
                    elapsed_time_seconds=(
                        _to_int(_node_attribute(elapsed_node, "seconds"))
                        or parse_bgp_uptime_to_seconds(_scalar(elapsed_node))
                    ),
                    flap_count=_to_int(_field(peer, "flap-count")),
                    received_prefix_count=_sum_family_counter(
                        families,
                        "received_prefix_count",
                    ),
                    accepted_prefix_count=_sum_family_counter(
                        families,
                        "accepted_prefix_count",
                    ),
                    active_prefix_count=_sum_family_counter(
                        families,
                        "active_prefix_count",
                    ),
                    suppressed_prefix_count=_sum_family_counter(
                        families,
                        "suppressed_prefix_count",
                    ),
                    advertised_prefix_count=_sum_family_counter(
                        families,
                        "advertised_prefix_count",
                    ),
                    total_prefix_count=_sum_json_child_ints(
                        rib_records,
                        "total-prefix-count",
                    ),
                    families=families,
                )
            )

    return records


_GNMI_NEIGHBOR_KEY_NAMES = {
    "neighbor",
    "neighbor-address",
    "neighbor_address",
    "neighbor-ip",
    "neighbor_ip",
    "peer",
    "peer-address",
    "peer_address",
}

_GNMI_AFI_SAFI_KEY_NAMES = {
    "afi-safi-name",
    "afi_safi_name",
    "afi-safi",
    "afi_safi",
    "family",
}

_GNMI_PEER_FIELD_MAP = {
    "session-state": "peer_state",
    "peer-state": "peer_state",
    "peer-as": "peer_as",
    "remote-as": "peer_as",
    "established-transitions": "flap_count",
    "flap-count": "flap_count",
    "enabled": "enabled",
    "peer-type": "peer_type",
    "last-established": "last_established_ns",
    "uptime": "elapsed_time_raw",
    "elapsed-time": "elapsed_time_raw",
}

_GNMI_FAMILY_COUNTER_MAP = {
    "active-prefix-count": "active_prefix_count",
    "active-prefixes": "active_prefix_count",
    "installed-prefix-count": "active_prefix_count",
    "installed-prefixes": "active_prefix_count",
    "received-prefix-count": "received_prefix_count",
    "received-prefixes": "received_prefix_count",
    "prefixes-received": "received_prefix_count",
    "accepted-prefix-count": "accepted_prefix_count",
    "accepted-prefixes": "accepted_prefix_count",
    "suppressed-prefix-count": "suppressed_prefix_count",
    "suppressed-prefixes": "suppressed_prefix_count",
    "advertised-prefix-count": "advertised_prefix_count",
    "advertised-prefixes": "advertised_prefix_count",
    "sent-prefix-count": "advertised_prefix_count",
    "sent-prefixes": "advertised_prefix_count",
    "prefixes-sent": "advertised_prefix_count",
}


def _gnmi_path_elements(path: Any) -> list[dict[str, Any]]:
    if not isinstance(path, dict):
        return []
    elements = path.get("elem", [])
    return [element for element in elements if isinstance(element, dict)]


def _gnmi_key_value(
    elements: list[dict[str, Any]],
    names: set[str],
) -> str | None:
    for element in elements:
        keys = element.get("key", {})
        if not isinstance(keys, dict):
            continue
        for key, value in keys.items():
            if str(key).lower() in names:
                return str(value)
    return None


def _gnmi_neighbor_from_text(text: str) -> str | None:
    match = re.search(
        r"(?:neighbor(?:[-_]address|[-_]ip)?|peer(?:[-_]address)?)=([^\]\s/]+)",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _gnmi_afi_safi_from_text(text: str) -> str | None:
    match = re.search(
        r"(?:afi[-_]safi[-_]name|afi[-_]safi|family|name)=([^\]\s/]+)",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _gnmi_leaf_name(elements: list[dict[str, Any]]) -> str | None:
    for element in reversed(elements):
        name = str(element.get("name", "")).strip()
        if name:
            return name.lower()
    return None


def _gnmi_value(value: Any) -> Any:
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
                return json.loads(raw)
            except Exception:  # noqa: BLE001 - best effort parser for raw telemetry
                return raw
        return raw

    if len(value) == 1:
        return next(iter(value.values()))
    return value


def _gnmi_iter_notifications(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        updates = node.get("update")
        if "prefix" in node and isinstance(updates, list):
            yield node
        for value in node.values():
            yield from _gnmi_iter_notifications(value)
    elif isinstance(node, list):
        for value in node:
            yield from _gnmi_iter_notifications(value)


def _gnmi_iter_event_values(document: Any) -> Iterable[tuple[str, str | None, str | None, str, Any]]:
    events = document if isinstance(document, list) else [document]
    for event in events:
        if not isinstance(event, dict):
            continue
        values = event.get("values", {})
        tags = event.get("tags", {})
        if not isinstance(values, dict) or not isinstance(tags, dict):
            continue
        device = str(event.get("source") or event.get("target") or "")
        neighbor = None
        afi_safi = None
        for key, value in tags.items():
            lowered = str(key).lower()
            if lowered in _GNMI_NEIGHBOR_KEY_NAMES:
                neighbor = str(value)
            if lowered in _GNMI_AFI_SAFI_KEY_NAMES:
                afi_safi = str(value)
        for path_text, value in values.items():
            leaf = str(path_text).rstrip("/").split("/")[-1].lower()
            path_string = str(path_text)
            yield (
                device,
                neighbor or _gnmi_neighbor_from_text(path_string),
                afi_safi or _gnmi_afi_safi_from_text(path_string),
                leaf,
                value,
            )


def _to_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "enabled"}:
        return True
    if text in {"false", "0", "no", "disabled"}:
        return False
    return None


def _valid_gnmi_state(value: object) -> str | None:
    state = normalize_state(value)
    if state in {
        "Established",
        "Idle",
        "Connect",
        "Active",
        "OpenSent",
        "OpenConfirm",
        "Unknown",
    }:
        return state
    return None


def _apply_gnmi_leaf(
    *,
    peers: dict[tuple[str, str], dict[str, Any]],
    families: dict[tuple[str, str, str], dict[str, Any]],
    device: str,
    neighbor: str | None,
    afi_safi: str | None,
    leaf: str | None,
    value: Any,
) -> None:
    if not neighbor or not leaf:
        return

    peer_key = (device, _clean_neighbor(neighbor))
    peer_payload = peers.setdefault(peer_key, {})

    if isinstance(value, dict):
        for nested_leaf, nested_value in value.items():
            _apply_gnmi_leaf(
                peers=peers,
                families=families,
                device=device,
                neighbor=neighbor,
                afi_safi=afi_safi,
                leaf=str(nested_leaf).lower(),
                value=nested_value,
            )
        return

    peer_field = _GNMI_PEER_FIELD_MAP.get(leaf)
    if peer_field == "peer_state":
        state = _valid_gnmi_state(value)
        if state is not None:
            peer_payload[peer_field] = state
        return
    if peer_field in {"peer_as", "flap_count", "last_established_ns"}:
        peer_payload[peer_field] = _to_int(value)
        return
    if peer_field == "enabled":
        peer_payload[peer_field] = _to_bool(value)
        return
    if peer_field == "peer_type":
        text = str(value).strip()
        if text:
            peer_payload[peer_field] = text
        return
    if peer_field == "elapsed_time_raw":
        text = str(value).strip()
        if text:
            peer_payload[peer_field] = text
            peer_payload["elapsed_time_seconds"] = parse_bgp_uptime_to_seconds(text)
        return

    counter_field = _GNMI_FAMILY_COUNTER_MAP.get(leaf)
    if counter_field is None or not afi_safi:
        return

    table = str(afi_safi).strip()
    if not table:
        return
    family_payload = families.setdefault((peer_key[0], peer_key[1], table), {})
    family_payload[counter_field] = _to_int(value)


def _extract_gnmi_payloads(
    documents: list[Any],
    *,
    fallback_device: str,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]]]:
    peers: dict[tuple[str, str], dict[str, Any]] = {}
    families: dict[tuple[str, str, str], dict[str, Any]] = {}

    for document in documents:
        for notification in _gnmi_iter_notifications(document):
            prefix = notification.get("prefix", {})
            prefix_elements = _gnmi_path_elements(prefix)
            device = str(
                prefix.get("target")
                or notification.get("source")
                or fallback_device
            )
            for update in notification.get("update", []):
                if not isinstance(update, dict):
                    continue
                update_elements = _gnmi_path_elements(update.get("path"))
                all_elements = prefix_elements + update_elements
                path_text = repr(all_elements)
                neighbor = (
                    _gnmi_key_value(all_elements, _GNMI_NEIGHBOR_KEY_NAMES)
                    or _gnmi_neighbor_from_text(path_text)
                )
                if neighbor:
                    peer_key = (device, _clean_neighbor(neighbor))
                    timestamp_ns = _to_int(notification.get("timestamp"))
                    if timestamp_ns is not None:
                        peer_payload = peers.setdefault(peer_key, {})
                        current_timestamp_ns = _to_int(
                            peer_payload.get("_notification_timestamp_ns")
                        )
                        if (
                            current_timestamp_ns is None
                            or timestamp_ns > current_timestamp_ns
                        ):
                            peer_payload["_notification_timestamp_ns"] = timestamp_ns

                _apply_gnmi_leaf(
                    peers=peers,
                    families=families,
                    device=device,
                    neighbor=neighbor,
                    afi_safi=(
                        _gnmi_key_value(all_elements, _GNMI_AFI_SAFI_KEY_NAMES)
                        or _gnmi_afi_safi_from_text(path_text)
                    ),
                    leaf=_gnmi_leaf_name(all_elements),
                    value=_gnmi_value(update.get("val")),
                )

        for event_device, event_neighbor, event_afi_safi, leaf, value in _gnmi_iter_event_values(document):
            _apply_gnmi_leaf(
                peers=peers,
                families=families,
                device=event_device or fallback_device,
                neighbor=event_neighbor,
                afi_safi=event_afi_safi,
                leaf=leaf,
                value=value,
            )

    return peers, families


def _gnmi_elapsed_fields(
    payload: dict[str, Any],
) -> tuple[str | None, int | None]:
    """Return elapsed uptime, deriving it safely from OpenConfig timestamps."""
    raw = payload.get("elapsed_time_raw")
    seconds = payload.get("elapsed_time_seconds")
    if raw is not None or seconds is not None:
        return (
            str(raw) if raw is not None else None,
            _to_int(seconds),
        )

    notification_ns = _to_int(payload.get("_notification_timestamp_ns"))
    last_established_ns = _to_int(payload.get("last_established_ns"))
    if (
        notification_ns is None
        or last_established_ns is None
        or notification_ns < last_established_ns
    ):
        return None, None

    elapsed_seconds = (notification_ns - last_established_ns) // 1_000_000_000
    return f"{elapsed_seconds}s", elapsed_seconds



def _families_for_gnmi_peer(
    families: dict[tuple[str, str, str], dict[str, Any]],
    *,
    device: str,
    neighbor: str,
) -> list[BgpFamilyHealthCounters]:
    records: list[BgpFamilyHealthCounters] = []
    for family_device, family_neighbor, table in sorted(families):
        if family_device != device or family_neighbor != neighbor:
            continue
        payload = families[(family_device, family_neighbor, table)]
        records.append(
            BgpFamilyHealthCounters(
                table=table,
                family=family_from_table(table),
                active_prefix_count=payload.get("active_prefix_count"),
                received_prefix_count=payload.get("received_prefix_count"),
                accepted_prefix_count=payload.get("accepted_prefix_count"),
                suppressed_prefix_count=payload.get("suppressed_prefix_count"),
                advertised_prefix_count=payload.get("advertised_prefix_count"),
            )
        )
    return records


def extract_gnmic_json_records(
    path: Path,
    *,
    device_name: str,
    source: str | None = None,
) -> list[BgpSessionHealthRecord]:
    """Extract peer-level session-health records from gNMIc output.

    Basic gNMI evidence may contain more than ``session-state``.  This parser
    consumes neighbor state leaves plus AFI-SAFI counter leaves when the device
    exposes them.  Missing leaves remain ``None``; rule evaluation must not
    invent counters that are not present in the raw evidence.
    """
    documents = load_json_documents(path)
    peers, families = _extract_gnmi_payloads(
        documents,
        fallback_device=device_name,
    )

    try:
        state_sessions = parse_gnmic_json(path, fallback_device=device_name)
    except ValueError:
        state_sessions = []

    for session in state_sessions:
        key = (session.device or device_name, _clean_neighbor(session.neighbor))
        payload = peers.setdefault(key, {})
        payload.setdefault("peer_state", normalize_state(session.state))

    records: list[BgpSessionHealthRecord] = []
    for (device, neighbor), payload in sorted(peers.items()):
        state = payload.get("peer_state")
        if state is None:
            continue
        peer_families = _families_for_gnmi_peer(
            families,
            device=device,
            neighbor=neighbor,
        )
        elapsed_time_raw, elapsed_time_seconds = _gnmi_elapsed_fields(payload)
        records.append(
            BgpSessionHealthRecord(
                device=device or device_name,
                source=source,
                neighbor=neighbor,
                peer_state=normalize_state(state),
                peer_as=payload.get("peer_as"),
                elapsed_time_raw=elapsed_time_raw,
                elapsed_time_seconds=elapsed_time_seconds,
                flap_count=payload.get("flap_count"),
                enabled=payload.get("enabled"),
                peer_type=payload.get("peer_type"),
                last_established_ns=payload.get("last_established_ns"),
                received_prefix_count=_sum_family_counter(
                    peer_families,
                    "received_prefix_count",
                ),
                accepted_prefix_count=_sum_family_counter(
                    peer_families,
                    "accepted_prefix_count",
                ),
                active_prefix_count=_sum_family_counter(
                    peer_families,
                    "active_prefix_count",
                ),
                suppressed_prefix_count=_sum_family_counter(
                    peer_families,
                    "suppressed_prefix_count",
                ),
                advertised_prefix_count=_sum_family_counter(
                    peer_families,
                    "advertised_prefix_count",
                ),
                families=peer_families,
            )
        )

    if not records:
        raise ValueError(
            "No BGP sessions were found in the gNMIc JSON file. "
            "The gNMI path or output shape may require a parser adapter."
        )

    return records


def extract_records_from_raw(
    path: Path,
    *,
    device_name: str,
    source: str | None = None,
) -> list[BgpSessionHealthRecord]:
    """Extract session-health records from a raw snapshot file."""
    suffix = path.suffix.lower()

    if suffix == ".xml":
        return extract_pyez_xml_records(
            path,
            device_name=device_name,
            source=source,
        )

    if suffix == ".json":
        if str(source or "").lower() == "gnmic":
            return extract_gnmic_json_records(
                path,
                device_name=device_name,
                source=source,
            )

        return extract_ssh_json_records(
            path,
            device_name=device_name,
            source=source,
        )

    raise ValueError(f"Unsupported BGP session-health raw format: {path}")
