"""Compatibility tests for the automatic snapshot facade."""

from maintenance_window.runners import snapshot_capture as facade
from maintenance_window.runners.snapshot_capture.arguments import parse_args
from maintenance_window.runners.snapshot_capture.commands import (
    build_capture_command,
)
from maintenance_window.runners.snapshot_capture.config import build_config
from maintenance_window.runners.snapshot_capture.execution import (
    run_command,
    run_flow,
)
from maintenance_window.runners.snapshot_capture.models import SnapshotRunnerConfig


def test_snapshot_facade_reexports_components() -> None:
    assert facade.SnapshotRunnerConfig is SnapshotRunnerConfig
    assert facade.parse_args is parse_args
    assert facade.build_config is build_config
    assert facade.build_capture_command is build_capture_command
    assert facade.run_command is run_command
    assert facade.run_flow is run_flow
