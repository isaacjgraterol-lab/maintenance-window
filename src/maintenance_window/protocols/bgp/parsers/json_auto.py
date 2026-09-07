from __future__ import annotations

from pathlib import Path

from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.parsers.gnmic_json import parse_gnmic_json
from maintenance_window.protocols.bgp.parsers.ssh_json import parse_ssh_json


def parse_json_bgp_file(
    path: Path,
    fallback_device: str = "file-input",
) -> list[BgpSession]:
    """Detect normalized/gNMIc JSON or Junos CLI JSON and normalize it."""
    ssh_sessions = parse_ssh_json(
        path,
        device_name=fallback_device,
        require_sessions=False,
    )
    if ssh_sessions:
        return ssh_sessions

    try:
        return parse_gnmic_json(path, fallback_device=fallback_device)
    except ValueError as exc:
        raise ValueError(
            "The JSON file is not recognized as normalized BGP data, "
            "gNMIc output, or Junos `show bgp summary | display json` output."
        ) from exc
