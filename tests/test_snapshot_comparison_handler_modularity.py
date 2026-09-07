from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintenance_window.cli_handlers import snapshot_comparison
from maintenance_window.cli_handlers.snapshot_comparison import (
    comparison,
    execution,
    exporting,
    request,
    summary,
)
from maintenance_window.core.models import Device


def _args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "mw_id": "MW-001",
        "compare_snapshots": "before,after",
        "device": "router-a",
        "inventory": Path("inventory/devices.txt"),
        "export": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_public_snapshot_comparison_handler_is_small_facade() -> None:
    path = Path(snapshot_comparison.__file__).resolve()

    assert len(path.read_text(encoding="utf-8").splitlines()) < 35
    assert (
        snapshot_comparison.run_bgp_snapshot_comparison
        is execution.run_bgp_snapshot_comparison
    )


def test_parse_snapshot_compare_argument_normalizes_stages() -> None:
    assert request.parse_snapshot_compare_argument(
        " BEFORE , after "
    ) == ("before", "after")


@pytest.mark.parametrize(
    "value",
    ["before", "before,after,verify", "before,before"],
)
def test_parse_snapshot_compare_argument_rejects_invalid_values(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        request.parse_snapshot_compare_argument(value)


def test_resolve_snapshot_device_names_supports_all_and_manual_names() -> None:
    devices = {
        "192.0.2.1": Device(host="router-a"),
        "192.0.2.2": Device(host="router-b"),
    }

    assert request.resolve_snapshot_device_names("all", devices) == [
        "router-a",
        "router-b",
    ]
    assert request.resolve_snapshot_device_names(
        "manual-a, manual-b",
        devices,
    ) == ["manual-a", "manual-b"]


def test_build_global_summary_aggregates_device_reports() -> None:
    reports = [
        {
            "device": "router-a",
            "result": "PASS",
            "new_sessions_count": 1,
            "resolved_unhealthy_count": 2,
        },
        {
            "device": "router-b",
            "result": "FAIL",
            "lost_sessions_count": 1,
            "state_changes_count": 2,
            "new_unhealthy_count": 1,
            "persistent_unhealthy_count": 3,
        },
    ]

    result = summary._build_snapshot_global_summary(reports)

    assert result["overall_result"] == "FAIL"
    assert result["total_devices"] == 2
    assert result["passed_devices"] == 1
    assert result["failed_devices"] == 1
    assert result["total_lost_sessions"] == 1
    assert result["total_new_sessions"] == 1
    assert result["total_state_changes"] == 2
    assert result["total_new_unhealthy"] == 1
    assert result["total_resolved_unhealthy"] == 2
    assert result["total_persistent_unhealthy"] == 3
    assert result["devices_with_lost_sessions"] == ["router-b"]


def test_extract_snapshot_comparison_parts_rejects_bad_contract() -> None:
    with pytest.raises(RuntimeError, match="must return"):
        comparison._extract_snapshot_comparison_parts("not-a-tuple")

    with pytest.raises(RuntimeError, match="Expected exactly 3"):
        comparison._extract_snapshot_comparison_parts((1, 2))


def test_export_payload_preserves_request_and_reports() -> None:
    normalized_request = request.SnapshotComparisonRequest(
        mw_id="MW-001",
        before_stage="before",
        after_stage="after",
        device_names=["router-a"],
        export_path=Path("report.json"),
    )
    result = SimpleNamespace(report={"device": "router-a"})

    payload = exporting.build_snapshot_comparison_export_payload(
        normalized_request,
        [result],
        {"overall_result": "PASS"},
    )

    assert payload["mw_id"] == "MW-001"
    assert payload["devices"] == ["router-a"]
    assert payload["reports"] == [{"device": "router-a"}]


def test_execution_orchestrates_devices_summary_and_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized_request = request.SnapshotComparisonRequest(
        mw_id="MW-001",
        before_stage="before",
        after_stage="after",
        device_names=["router-a", "router-b"],
        export_path=None,
    )
    calls: list[str] = []

    monkeypatch.setattr(
        execution,
        "build_snapshot_comparison_request",
        lambda args: normalized_request,
    )
    monkeypatch.setattr(
        execution,
        "compare_snapshot_device",
        lambda req, device_name: SimpleNamespace(
            report={
                "device": device_name,
                "result": "FAIL" if device_name == "router-b" else "PASS",
            },
            comparison=object(),
        ),
    )
    monkeypatch.setattr(
        execution,
        "print_device_comparison_heading",
        lambda device_name: calls.append(f"heading:{device_name}"),
    )
    monkeypatch.setattr(
        execution,
        "print_device_comparison",
        lambda result: calls.append(f"report:{result.report['device']}"),
    )
    monkeypatch.setattr(
        execution,
        "_print_snapshot_global_summary",
        lambda global_summary: calls.append(
            f"summary:{global_summary['overall_result']}"
        ),
    )
    monkeypatch.setattr(
        execution,
        "print_exit_code",
        lambda exit_code: calls.append(f"exit:{exit_code}"),
    )

    assert execution.run_bgp_snapshot_comparison(_args()) == 1
    assert calls == [
        "heading:router-a",
        "report:router-a",
        "heading:router-b",
        "report:router-b",
        "summary:FAIL",
        "exit:1",
    ]
