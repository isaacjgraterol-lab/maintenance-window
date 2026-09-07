from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from maintenance_window.protocols.bgp.state.models import BgpSession, normalize_state
from maintenance_window.core.files import load_xml_root


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _child_text(element: ET.Element, expected_name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == expected_name and child.text:
            return child.text.strip()
    return None


def parse_pyez_xml(path: Path, device_name: str) -> list[BgpSession]:
    """Normalize Junos XML returned by a BGP operational RPC."""
    root = load_xml_root(path)
    sessions: list[BgpSession] = []

    for element in root.iter():
        if _local_name(element.tag) not in {"bgp-peer", "session"}:
            continue

        neighbor = (
            _child_text(element, "peer-address")
            or _child_text(element, "neighbor")
            or _child_text(element, "neighbor-address")
        )
        state = (
            _child_text(element, "peer-state")
            or _child_text(element, "state")
            or _child_text(element, "session-state")
        )

        if neighbor and state:
            sessions.append(
                BgpSession(
                    device=device_name,
                    neighbor=neighbor,
                    state=normalize_state(state),
                )
            )

    if not sessions:
        raise ValueError(
            "No BGP sessions were found in the XML file. "
            "Confirm that it contains get-bgp-summary-information output."
        )
    return sessions
