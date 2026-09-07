from __future__ import annotations

from argparse import Namespace
from importlib import import_module
from pathlib import Path

import pytest

from maintenance_window.cli_handlers import validation
from maintenance_window.cli_handlers.validation import collection
from maintenance_window.cli_handlers.validation import execution
from maintenance_window.cli_handlers.validation import rendering
from maintenance_window.cli_handlers.validation import request
from maintenance_window.cli_handlers.validation.models import (
    ValidationArtifacts,
)
from maintenance_window.protocols.bgp.state.models import BgpSession


def _args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "source": "ssh",
        "snapshot": None,
        "mw_id": None,
        "filter": "all",
        "protocol": "bgp",
        "export": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_public_validation_handler_is_a_small_facade() -> None:
    path = Path(validation.__file__).resolve()

    assert len(path.read_text(encoding="utf-8").splitlines()) < 25
    assert validation.run_bgp_validation is execution.run_bgp_validation


def test_validation_request_requires_source() -> None:
    with pytest.raises(
        ValueError,
        match="--source is required",
    ):
        request.validate_validation_request(_args(source=None))


def test_validation_request_requires_mw_id_for_snapshot() -> None:
    with pytest.raises(
        ValueError,
        match="--mw-id is required",
    ):
        request.validate_validation_request(
            _args(snapshot="before")
        )


@pytest.mark.parametrize(
    ("source", "function_name"),
    [
        ("manual", "collect_manual_source"),
        ("json-file", "collect_file_source"),
        ("ssh", "collect_live_source"),
    ],
)
def test_collection_dispatches_by_source(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    function_name: str,
) -> None:
    calls: list[str] = []

    for name in (
        "collect_manual_source",
        "collect_file_source",
        "collect_live_source",
    ):
        monkeypatch.setattr(
            collection,
            name,
            lambda args, name=name: (
                calls.append(name) or ValidationArtifacts()
            ),
        )

    result = collection.collect_validation_source(_args(source=source))

    assert isinstance(result, ValidationArtifacts)
    assert calls == [function_name]


def test_rendering_groups_normalized_sessions() -> None:
    sessions = [
        BgpSession(
            device="router-a",
            neighbor="192.0.2.1",
            state="Established",
        ),
        BgpSession(
            device="router-a",
            neighbor="192.0.2.2",
            state="Idle",
        ),
    ]

    assert rendering.group_sessions_for_output(sessions) == {
        "router-a": [
            {"neighbor": "192.0.2.1", "state": "Established"},
            {"neighbor": "192.0.2.2", "state": "Idle"},
        ]
    }


def test_execution_orchestrates_collection_filter_and_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifacts = ValidationArtifacts(
        sessions=[
            BgpSession(
                device="router-a",
                neighbor="192.0.2.1",
                state="Established",
            )
        ]
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        execution,
        "collect_validation_source",
        lambda args: artifacts,
    )

    def fake_render(**kwargs: object) -> int:
        captured.update(kwargs)
        return 17

    monkeypatch.setattr(
        execution,
        "render_validation_result",
        fake_render,
    )

    assert execution.run_bgp_validation(_args()) == 17
    assert captured["artifacts"] is artifacts
    assert captured["filtered_sessions"] == artifacts.sessions
