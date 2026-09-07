from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from maintenance_window.cli_handlers.snapshot_comparison import (
    execution,
    exporting,
    request,
    summary,
)


def test_global_summary_prioritizes_error_over_fail() -> None:
    reports = [
        {
            "device": "router-a",
            "result": "PASS",
        },
        {
            "device": "router-b",
            "result": "FAIL",
            "lost_sessions_count": 1,
        },
        {
            "device": "router-c",
            "result": "ERROR",
            "error": "snapshot missing",
        },
    ]

    result = summary._build_snapshot_global_summary(reports)

    assert result["overall_result"] == "ERROR"
    assert result["total_devices"] == 3
    assert result["passed_devices"] == 1
    assert result["failed_devices"] == 1
    assert result["error_devices"] == 1
    assert result["devices_with_errors"] == ["router-c"]
    assert result["devices_with_lost_sessions"] == ["router-b"]


def test_snapshot_exit_code_mapping() -> None:
    assert execution._snapshot_exit_code(
        {"overall_result": "PASS"}
    ) == 0
    assert execution._snapshot_exit_code(
        {"overall_result": "FAIL"}
    ) == 1
    assert execution._snapshot_exit_code(
        {"overall_result": "ERROR"}
    ) == 2


def test_execution_continues_and_returns_error_for_device_failure(
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

    def fake_compare_snapshot_device(req, device_name):
        del req

        if device_name == "router-b":
            raise FileNotFoundError("missing snapshot")

        return SimpleNamespace(
            report={
                "device": device_name,
                "result": "PASS",
            },
            comparison=object(),
        )

    monkeypatch.setattr(
        execution,
        "compare_snapshot_device",
        fake_compare_snapshot_device,
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
        "print_device_comparison_error",
        lambda device_name, exc: calls.append(
            f"error:{device_name}:{type(exc).__name__}"
        ),
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

    assert execution.run_bgp_snapshot_comparison(object()) == 2
    assert calls == [
        "heading:router-a",
        "report:router-a",
        "heading:router-b",
        "error:router-b:FileNotFoundError",
        "summary:ERROR",
        "exit:2",
    ]


def test_export_payload_includes_device_error_reports() -> None:
    normalized_request = request.SnapshotComparisonRequest(
        mw_id="MW-001",
        before_stage="before",
        after_stage="after",
        device_names=["router-a", "router-b"],
        export_path=Path("report.json"),
    )
    results = [
        SimpleNamespace(
            report={
                "device": "router-a",
                "result": "PASS",
            }
        ),
        SimpleNamespace(
            report={
                "device": "router-b",
                "result": "ERROR",
                "error": "missing snapshot",
            }
        ),
    ]

    payload = exporting.build_snapshot_comparison_export_payload(
        normalized_request,
        results,
        {"overall_result": "ERROR"},
    )

    assert payload["reports"] == [
        {
            "device": "router-a",
            "result": "PASS",
        },
        {
            "device": "router-b",
            "result": "ERROR",
            "error": "missing snapshot",
        },
    ]
