from __future__ import annotations

import pytest

from maintenance_window.cli_handlers import validation
from maintenance_window.core.models import Device


def _inventory() -> dict[str, Device]:
    return {
        "198.51.100.8": Device(host="198.51.100.8"),
        "198.51.100.9": Device(host="198.51.100.9"),
        "198.51.100.11": Device(host="198.51.100.11"),
    }


def test_resolve_single_device_from_inventory_mapping() -> None:
    selected = validation._resolve_devices(
        "198.51.100.8",
        _inventory(),
    )

    assert [device.host for device in selected] == [
        "198.51.100.8",
    ]


def test_resolve_all_returns_device_objects() -> None:
    selected = validation._resolve_devices(
        "all",
        _inventory(),
    )

    assert [device.host for device in selected] == [
        "198.51.100.8",
        "198.51.100.9",
        "198.51.100.11",
    ]


def test_resolve_multiple_preserves_requested_order() -> None:
    selected = validation._resolve_devices(
        "198.51.100.11,198.51.100.8",
        _inventory(),
    )

    assert [device.host for device in selected] == [
        "198.51.100.11",
        "198.51.100.8",
    ]


def test_resolve_missing_device_raises_clean_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"Device\(s\) not found in inventory: "
            r"198\.51\.100\.15"
        ),
    ):
        validation._resolve_devices(
            "198.51.100.15",
            _inventory(),
        )
