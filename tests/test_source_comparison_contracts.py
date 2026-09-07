from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from maintenance_window.cli_handlers import source_comparison as handler
from maintenance_window.core.models import Device
from maintenance_window.protocols.bgp import service


def _inventory() -> dict[str, Device]:
    return {
        "198.51.100.8": Device(host="198.51.100.8"),
        "198.51.100.12": Device(host="198.51.100.12"),
    }


def test_resolve_devices_returns_device_objects_for_single_and_all() -> None:
    devices = _inventory()

    selected = handler._resolve_devices("198.51.100.8", devices)
    selected_all = handler._resolve_devices("all", devices)

    assert [device.host for device in selected] == ["198.51.100.8"]
    assert [device.host for device in selected_all] == [
        "198.51.100.8",
        "198.51.100.12",
    ]


def test_resolve_devices_supports_multiple_and_rejects_missing() -> None:
    devices = _inventory()

    selected = handler._resolve_devices(
        "198.51.100.8,198.51.100.12",
        devices,
    )

    assert [device.host for device in selected] == [
        "198.51.100.8",
        "198.51.100.12",
    ]

    with pytest.raises(
        ValueError,
        match=r"Device\(s\) not found in inventory: 198\.51\.100\.15",
    ):
        handler._resolve_devices("198.51.100.15", devices)


def test_compare_live_sources_returns_comparison_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = Device(host="198.51.100.8")
    left_sessions = [object()]
    right_sessions = [object()]
    expected_comparison = object()

    calls: list[str] = []

    def fake_collect_with_source(
        source: str,
        device: Device,
        defaults: dict[str, str],
        profiles: dict[str, object],
        settings: dict[str, object],
        project_root: Path,
    ) -> tuple[list[object], Path, str]:
        calls.append(source)

        if source == "pyez":
            return left_sessions, Path("left.xml"), "pyez"

        return right_sessions, Path("right.json"), "ssh"

    def fake_compare_bgp_sources(
        left_source: str,
        left_sessions: list[object],
        right_source: str,
        right_sessions: list[object],
    ) -> object:
        assert left_source == "pyez"
        assert right_source == "ssh"
        assert left_sessions is not right_sessions
        return expected_comparison

    monkeypatch.setattr(
        service,
        "collect_with_source",
        fake_collect_with_source,
    )
    monkeypatch.setattr(
        service,
        "compare_bgp_sources",
        fake_compare_bgp_sources,
    )

    comparison, raw_files, actual_sources = service.compare_live_sources(
        left_source="pyez",
        right_source="ssh",
        device=device,
        defaults={},
        profiles={},
        settings={},
        project_root=Path("."),
    )

    assert comparison is expected_comparison
    assert calls == ["pyez", "ssh"]
    assert raw_files == {
        "pyez": Path("left.xml"),
        "ssh": Path("right.json"),
    }
    assert actual_sources == {
        "pyez": "pyez",
        "ssh": "ssh",
    }


def test_source_comparison_handler_unpacks_service_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = Device(host="198.51.100.8")
    expected_comparison = object()
    printed: list[object] = []
    serialized: list[object] = []

    monkeypatch.setattr(
        handler,
        "load_devices",
        lambda path: {device.host: device},
    )
    monkeypatch.setattr(
        handler,
        "load_credentials",
        lambda path: ({}, {}),
    )
    monkeypatch.setattr(
        handler,
        "_load_protocol_runtime_settings",
        lambda args: {},
    )
    monkeypatch.setattr(
        handler,
        "compare_live_sources",
        lambda **kwargs: (
            expected_comparison,
            {
                "pyez": Path("left.xml"),
                "ssh": Path("right.json"),
            },
            {
                "pyez": "pyez",
                "ssh": "ssh",
            },
        ),
    )
    monkeypatch.setattr(
        handler,
        "print_comparison_report",
        lambda comparison: printed.append(comparison),
    )

    def fake_comparison_to_dict(comparison: object) -> dict[str, object]:
        serialized.append(comparison)
        return {"result": "PASS"}

    monkeypatch.setattr(
        handler,
        "comparison_to_dict",
        fake_comparison_to_dict,
    )

    args = Namespace(
        compare_source="pyez,ssh",
        inventory=Path("inventory/devices.txt"),
        device="198.51.100.8",
        credentials=Path("auth/credentials.json"),
        connection_settings=Path(
            "config/connections/settings.json"
        ),
        audit_settings=Path(
            "config/audits/bgp/state.json"
        ),
        export=None,
    )

    exit_code = handler.run_bgp_source_comparison(args)

    assert exit_code == 0
    assert printed == [expected_comparison]
    assert serialized == [expected_comparison]
