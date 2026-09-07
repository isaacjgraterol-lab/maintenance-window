from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path

from maintenance_window.core.models import Device


def load_devices(path: Path) -> dict[str, Device]:
    """Load one IPv4 or IPv6 management address per line."""
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Inventory path is not a file: {path}")

    devices: dict[str, Device] = {}

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue

        try:
            normalized_ip = str(ip_address(value))
        except ValueError as exc:
            raise ValueError(
                f"Invalid IP address on line {line_number} of {path}: {value}"
            ) from exc

        if normalized_ip in devices:
            raise ValueError(
                f"Duplicate IP address on line {line_number}: {normalized_ip}"
            )

        devices[normalized_ip] = Device(host=normalized_ip)

    if not devices:
        raise ValueError(f"No device IP addresses were found in: {path}")

    return devices
