from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

from maintenance_window.cli_handlers.validation import collection
from maintenance_window.cli_handlers.validation.models import (
    DeviceCollectionError,
    ValidationArtifacts,
)
from maintenance_window.cli_handlers.validation.rendering import (
    render_validation_result,
)
from maintenance_window.protocols.bgp.state.models import BgpSession


def test_collect_live_source_continues_after_device_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bad_device = SimpleNamespace(host="198.51.100.13")
    good_device = SimpleNamespace(host="198.51.100.14")

    args = argparse.Namespace(
        inventory=tmp_path / "devices.txt",
        credentials=tmp_path / "credentials.json",
        source="ssh",
        device="all",
        snapshot=None,
        auth_backend="auto",
    )

    monkeypatch.setattr(collection, "load_devices", lambda path: [])
    monkeypatch.setattr(
        collection,
        "resolve_devices",
        lambda selector, devices: [bad_device, good_device],
    )
    monkeypatch.setattr(
        collection,
        "load_credentials",
        lambda path: ({}, {}),
    )
    monkeypatch.setattr(
        collection,
        "load_protocol_runtime_settings",
        lambda args: {},
    )

    def fake_collect_live_sessions(**kwargs):
        device = kwargs["device"]
        if device.host == bad_device.host:
            raise RuntimeError("authentication failed")

        return (
            [
                BgpSession(
                    device=good_device.host,
                    neighbor="192.0.2.1",
                    state="Established",
                )
            ],
            tmp_path / "good_raw.json",
            "ssh",
        )

    monkeypatch.setattr(
        collection,
        "collect_live_sessions",
        fake_collect_live_sessions,
    )
    monkeypatch.setattr(
        collection,
        "write_live_snapshot",
        lambda **kwargs: tmp_path / "good_snapshot.json",
    )

    artifacts = collection.collect_live_source(args)

    assert len(artifacts.sessions) == 1
    assert artifacts.sessions[0].device == good_device.host
    assert len(artifacts.device_errors) == 1
    assert artifacts.device_errors[0] == DeviceCollectionError(
        device=bad_device.host,
        source="ssh",
        error_type="RuntimeError",
        error="authentication failed",
    )
    assert artifacts.snapshot_files == [tmp_path / "good_snapshot.json"]


def test_render_validation_result_returns_error_when_device_failed(
    capsys,
) -> None:
    args = argparse.Namespace(
        protocol="bgp",
        source="ssh",
        export=None,
    )
    artifacts = ValidationArtifacts(
        sessions=[],
        device_errors=[
            DeviceCollectionError(
                device="198.51.100.13",
                source="ssh",
                error_type="RuntimeError",
                error="authentication failed",
            )
        ],
    )

    exit_code = render_validation_result(
        args=args,
        status_filter="all",
        artifacts=artifacts,
        filtered_sessions=[],
    )

    output = capsys.readouterr().out

    assert exit_code == 2
    assert "Devices failed: 1" in output
    assert "Collection errors:" in output
    assert "PARTIAL_COLLECTION" in output
    assert "198.51.100.13" in output
    assert "ssh" in output
    assert "RuntimeError" in output
    assert "authentication failed" in output
