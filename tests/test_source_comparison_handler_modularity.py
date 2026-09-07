from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintenance_window.cli_handlers import source_comparison
from maintenance_window.cli_handlers.source_comparison import (
    comparison,
    execution,
    exporting,
    request,
)
from maintenance_window.cli_handlers.source_comparison.models import (
    DeviceSourceComparison,
    SourceComparisonRequest,
    SourceComparisonRuntime,
)
from maintenance_window.core.models import Device


def _args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "protocol": "bgp",
        "compare_source": "pyez,ssh",
        "device": "192.0.2.1",
        "inventory": Path("inventory/devices.txt"),
        "credentials": Path("auth/credentials.json"),
        "connection_settings": Path(
            "config/connections/settings.json"
        ),
        "audit_settings": Path("config/audits/bgp/state.json"),
        "export": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_public_source_comparison_handler_is_small_facade() -> None:
    path = Path(source_comparison.__file__).resolve()

    assert len(path.read_text(encoding="utf-8").splitlines()) < 55
    assert callable(source_comparison.run_bgp_source_comparison)


def test_parse_source_compare_argument_normalizes_sources() -> None:
    assert request.parse_source_compare_argument(
        " PyEZ , SSH "
    ) == ("pyez", "ssh")


@pytest.mark.parametrize(
    "value",
    ["pyez", "pyez,ssh,gnmic", "ssh,ssh"],
)
def test_parse_source_compare_argument_rejects_invalid_values(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        request.parse_source_compare_argument(value)


def test_resolve_devices_preserves_inventory_order() -> None:
    devices = {
        "192.0.2.1": Device(host="router-a"),
        "192.0.2.2": Device(host="router-b"),
    }

    assert request.resolve_devices(
        "192.0.2.2,192.0.2.1",
        devices,
    ) == [devices["192.0.2.1"], devices["192.0.2.2"]]
    assert request.resolve_devices("all", devices) == list(devices.values())


def test_build_request_normalizes_devices_and_export_path() -> None:
    devices = {"192.0.2.1": Device(host="router-a")}

    result = request.build_source_comparison_request(
        _args(export=Path("reports/result.json")),
        load_devices_fn=lambda path: devices,
    )

    assert result.left_source == "pyez"
    assert result.right_source == "ssh"
    assert result.devices == [devices["192.0.2.1"]]
    assert result.export_path == Path("reports/result.json").resolve()


def test_compare_device_sources_normalizes_metadata() -> None:
    device = Device(host="router-a")
    normalized_request = SourceComparisonRequest(
        left_source="pyez",
        right_source="ssh",
        devices=[device],
        export_path=None,
    )
    runtime = SourceComparisonRuntime(
        defaults={},
        profiles={},
        settings={},
        project_root=Path("."),
    )
    expected_comparison = object()

    result = comparison.compare_device_sources(
        normalized_request,
        runtime,
        device,
        compare_live_sources_fn=lambda **kwargs: (
            expected_comparison,
            {
                "pyez": Path("left.xml"),
                "ssh": Path("right.json"),
            },
            {"pyez": "pyez", "ssh": "ssh"},
        ),
        comparison_to_dict_fn=lambda value: {"result": "PASS"},
    )

    assert result.comparison is expected_comparison
    assert result.report["raw_files"] == {
        "pyez": "left.xml",
        "ssh": "right.json",
    }
    assert result.report["actual_sources"] == {
        "pyez": "pyez",
        "ssh": "ssh",
    }


def test_export_payload_preserves_request_and_reports() -> None:
    device = Device(host="router-a")
    normalized_request = SourceComparisonRequest(
        left_source="pyez",
        right_source="ssh",
        devices=[device],
        export_path=Path("report.json"),
    )
    result = DeviceSourceComparison(
        comparison=object(),
        report={"device": "router-a", "result": "PASS"},
        raw_files={},
        actual_sources={},
    )

    payload = exporting.build_source_comparison_export_payload(
        normalized_request,
        [result],
    )

    assert payload["left_source"] == "pyez"
    assert payload["right_source"] == "ssh"
    assert payload["devices"] == ["router-a"]
    assert payload["reports"] == [result.report]


def test_execution_orchestrates_devices_and_failure_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    devices = [Device(host="router-a"), Device(host="router-b")]
    normalized_request = SourceComparisonRequest(
        left_source="pyez",
        right_source="ssh",
        devices=devices,
        export_path=None,
    )
    runtime = SourceComparisonRuntime(
        defaults={},
        profiles={},
        settings={},
        project_root=Path("."),
    )
    calls: list[str] = []

    monkeypatch.setattr(
        execution,
        "build_source_comparison_request",
        lambda args, **kwargs: normalized_request,
    )
    monkeypatch.setattr(
        execution,
        "build_source_comparison_runtime",
        lambda args, **kwargs: runtime,
    )
    monkeypatch.setattr(
        execution,
        "compare_device_sources",
        lambda req, ctx, device, **kwargs: DeviceSourceComparison(
            comparison=object(),
            report={
                "device": device.host,
                "result": "FAIL" if device.host == "router-b" else "PASS",
            },
            raw_files={},
            actual_sources={},
        ),
    )
    monkeypatch.setattr(
        execution,
        "print_device_comparison_heading",
        lambda req, device: calls.append(f"heading:{device.host}"),
    )
    monkeypatch.setattr(
        execution,
        "print_device_comparison",
        lambda result, **kwargs: calls.append(
            f"report:{result.report['device']}"
        ),
    )
    monkeypatch.setattr(
        execution,
        "export_source_comparison_report",
        lambda req, results, **kwargs: None,
    )

    assert execution.run_bgp_source_comparison(_args()) == 1
    assert calls == [
        "heading:router-a",
        "report:router-a",
        "heading:router-b",
        "report:router-b",
    ]
