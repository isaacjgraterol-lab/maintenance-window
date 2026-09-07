from __future__ import annotations

from argparse import Namespace
from importlib import import_module
from pathlib import Path

import pytest

from maintenance_window import cli
from maintenance_window.cli_app import arguments, defaults, validation


dispatch_module = import_module(
    "maintenance_window.cli_app.dispatch"
)


def _args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "list_manual_db": False,
        "compare_source": None,
        "compare_snapshots": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_public_cli_is_a_small_facade() -> None:
    cli_path = Path(cli.__file__).resolve()

    assert len(cli_path.read_text(encoding="utf-8").splitlines()) < 60
    assert cli.build_parser is arguments.build_parser


def test_defaults_resolve_from_project_root() -> None:
    assert defaults.DEFAULT_INVENTORY == (
        defaults.PROJECT_ROOT / "inventory" / "devices.txt"
    )
    assert defaults.DEFAULT_CONNECTION_SETTINGS == (
        defaults.PROJECT_ROOT
        / "config"
        / "connections"
        / "settings.json"
    )


def test_parser_contract_remains_public() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--protocol",
            "bgp",
            "--source",
            "ssh",
            "--device",
            "all",
        ]
    )

    assert args.protocol == "bgp"
    assert args.source == "ssh"
    assert args.connection_settings == (
        defaults.DEFAULT_CONNECTION_SETTINGS
    )


def test_mode_validation_rejects_both_comparisons() -> None:
    with pytest.raises(
        ValueError,
        match="Use either --compare-source or --compare-snapshots",
    ):
        validation.validate_mode_selection(
            _args(
                compare_source="pyez,ssh",
                compare_snapshots="before,after",
            )
        )


@pytest.mark.parametrize(
    ("overrides", "handler_name"),
    [
        ({"list_manual_db": True}, "run_manual_db_listing"),
        ({"compare_source": "pyez,ssh"}, "run_bgp_source_comparison"),
        (
            {"compare_snapshots": "before,after"},
            "run_bgp_snapshot_comparison",
        ),
        ({}, "run_bgp_validation"),
    ],
)
def test_dispatch_routes_one_mode(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, object],
    handler_name: str,
) -> None:
    calls: list[str] = []

    for name in (
        "run_manual_db_listing",
        "run_bgp_source_comparison",
        "run_bgp_snapshot_comparison",
        "run_bgp_validation",
    ):
        monkeypatch.setattr(
            dispatch_module,
            name,
            lambda args, name=name: calls.append(name) or 0,
        )

    assert dispatch_module.dispatch(_args(**overrides)) == 0
    assert calls == [handler_name]


def test_main_accepts_explicit_argv_and_reports_clean_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_value_error(args: Namespace) -> int:
        raise ValueError("bad request")

    monkeypatch.setattr(cli, "dispatch", raise_value_error)

    exit_code = cli.main(["--protocol", "bgp"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: bad request" in captured.out
    assert "Traceback" not in captured.out
