"""Removal guards for the superseded manual workflow."""

from importlib.util import find_spec

from maintenance_window.runners import snapshot_manual as runners_snapshot_manual
from maintenance_window.runners.snapshot_manual import (
    SnapshotManualRunnerConfig,
)


def test_legacy_manual_runner_package_is_removed() -> None:
    assert find_spec("maintenance_window.manual_runner") is None


def test_official_manual_runner_remains_available() -> None:
    assert runners_snapshot_manual.SnapshotManualRunnerConfig is (
        SnapshotManualRunnerConfig
    )
