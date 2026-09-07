"""Removal guards for superseded generic helper runners."""

from importlib.util import find_spec

from maintenance_window.runners import (
    snapshot_capture as runners_snapshot,
    snapshot_comparison as runners_snapshot_comparison,
    snapshot_manual as runners_snapshot_manual,
)
from maintenance_window.cli import build_parser


def test_legacy_generic_runner_is_removed() -> None:
    assert find_spec("maintenance_window.runners") is not None
    assert find_spec("maintenance_window.workflow_runner") is None


def test_legacy_db_runner_is_removed() -> None:
    assert find_spec("maintenance_window.runners_db") is None


def test_official_runner_entrypoints_remain_available() -> None:
    assert callable(runners_snapshot.main)
    assert callable(runners_snapshot_manual.main)
    assert callable(runners_snapshot_comparison.main)


def test_main_cli_keeps_manual_db_listing() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--protocol",
            "bgp",
            "--list-manual-db",
        ]
    )

    assert args.list_manual_db is True
