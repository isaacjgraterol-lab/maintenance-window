from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintenance_window.cli import build_parser
from maintenance_window.cli_handlers.validation import collection
from maintenance_window.cli_handlers.validation.request import (
    validate_validation_request,
)
from maintenance_window.engine.live_collection.models import (
    LiveCollectionSuccess,
)
from maintenance_window.protocols.bgp.state.models import BgpSession


def test_workers_argument_defaults_to_one() -> None:
    args = build_parser().parse_args(["--source", "ssh"])

    assert args.workers == 1


def test_workers_argument_accepts_operator_value() -> None:
    args = build_parser().parse_args([
        "--source",
        "ssh",
        "--workers",
        "10",
    ])

    assert args.workers == 10


@pytest.mark.parametrize("workers", [0, 51])
def test_validation_request_rejects_invalid_workers(workers: int) -> None:
    args = argparse.Namespace(
        source="ssh",
        snapshot=None,
        mw_id=None,
        workers=workers,
    )

    with pytest.raises(ValueError, match="--workers"):
        validate_validation_request(args)


def test_collect_live_source_uses_parallel_workers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    device_a = SimpleNamespace(host="198.51.100.9")
    device_b = SimpleNamespace(host="198.51.100.11")
    worker_calls: list[int] = []

    args = argparse.Namespace(
        inventory=tmp_path / "devices.txt",
        credentials=tmp_path / "credentials.json",
        source="ssh",
        device="all",
        snapshot=None,
        auth_backend="auto",
        workers=2,
    )

    monkeypatch.setattr(collection, "load_devices", lambda path: {})
    monkeypatch.setattr(
        collection,
        "resolve_devices",
        lambda selector, devices: [device_a, device_b],
    )
    monkeypatch.setattr(collection, "load_credentials", lambda path: ({}, {}))
    monkeypatch.setattr(
        collection,
        "load_protocol_runtime_settings",
        lambda args: {},
    )

    def fake_collect_live_sessions(**kwargs):
        device = kwargs["device"]
        return (
            [
                BgpSession(
                    device=device.host,
                    neighbor="192.0.2.1",
                    state="Established",
                )
            ],
            tmp_path / f"{device.host}.json",
            "ssh",
        )

    def fake_parallel(items, collect_item, *, max_workers):
        worker_calls.append(max_workers)
        return [
            LiveCollectionSuccess(item=item, value=collect_item(item))
            for item in items
        ]

    monkeypatch.setattr(
        collection,
        "collect_live_sessions",
        fake_collect_live_sessions,
    )
    monkeypatch.setattr(
        collection,
        "collect_parallel",
        fake_parallel,
    )
    monkeypatch.setattr(
        collection,
        "write_live_snapshot",
        lambda **kwargs: None,
    )

    artifacts = collection.collect_live_source(args)

    assert worker_calls == [2]
    assert len(artifacts.sessions) == 2
    assert artifacts.device_errors == []


def test_collect_live_source_workers_one_uses_sequential(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    device = SimpleNamespace(host="198.51.100.9")
    sequential_called: list[bool] = []

    args = argparse.Namespace(
        inventory=tmp_path / "devices.txt",
        credentials=tmp_path / "credentials.json",
        source="ssh",
        device="all",
        snapshot=None,
        auth_backend="auto",
        workers=1,
    )

    monkeypatch.setattr(collection, "load_devices", lambda path: {})
    monkeypatch.setattr(
        collection,
        "resolve_devices",
        lambda selector, devices: [device],
    )
    monkeypatch.setattr(collection, "load_credentials", lambda path: ({}, {}))
    monkeypatch.setattr(
        collection,
        "load_protocol_runtime_settings",
        lambda args: {},
    )
    monkeypatch.setattr(
        collection,
        "collect_live_sessions",
        lambda **kwargs: (
            [
                BgpSession(
                    device=device.host,
                    neighbor="192.0.2.1",
                    state="Established",
                )
            ],
            tmp_path / "raw.json",
            "ssh",
        ),
    )
    monkeypatch.setattr(
        collection,
        "write_live_snapshot",
        lambda **kwargs: None,
    )

    def fake_sequential(items, collect_item):
        sequential_called.append(True)
        return [
            LiveCollectionSuccess(item=item, value=collect_item(item))
            for item in items
        ]

    monkeypatch.setattr(collection, "collect_sequential", fake_sequential)

    artifacts = collection.collect_live_source(args)

    assert sequential_called == [True]
    assert len(artifacts.sessions) == 1
