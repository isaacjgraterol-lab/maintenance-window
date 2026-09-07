from pathlib import Path

import pytest

from maintenance_window.core.inventory import load_devices


def test_load_devices_txt(tmp_path: Path) -> None:
    inventory = tmp_path / "devices.txt"
    inventory.write_text("# lab\n\n192.0.2.1\n2001:db8::1\n", encoding="utf-8")

    devices = load_devices(inventory)

    assert list(devices) == ["192.0.2.1", "2001:db8::1"]
    assert devices["192.0.2.1"].host == "192.0.2.1"


def test_reject_invalid_device_ip(tmp_path: Path) -> None:
    inventory = tmp_path / "devices.txt"
    inventory.write_text("router-one\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid IP address"):
        load_devices(inventory)


def test_load_devices_accepts_utf8_bom(tmp_path: Path) -> None:
    inventory = tmp_path / "devices.txt"
    inventory.write_bytes(b"\xef\xbb\xbf# inventory\n192.0.2.10\n")

    devices = load_devices(inventory)

    assert list(devices) == ["192.0.2.10"]


def test_public_example_inventory_is_directly_loadable() -> None:
    root = Path(__file__).resolve().parents[1]
    devices = load_devices(root / "inventory" / "devices.example.txt")
    assert list(devices) == ["192.0.2.1", "192.0.2.2"]
