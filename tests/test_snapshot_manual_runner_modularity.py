"""Contract tests for the manual snapshot facade."""

from maintenance_window.runners import snapshot_manual as facade
from maintenance_window.runners.snapshot_manual.arguments import parse_args
from maintenance_window.runners.snapshot_manual.commands import (
    build_manual_snapshot_command,
)
from maintenance_window.runners.snapshot_manual.config import (
    build_config,
    infer_device_from_filename,
    infer_input_metadata,
)
from maintenance_window.runners.snapshot_manual.execution import (
    run_command,
    run_flow,
)
from maintenance_window.runners.snapshot_manual.models import (
    SnapshotManualRunnerConfig,
)


def test_manual_snapshot_facade_reexports_components() -> None:
    assert facade.SnapshotManualRunnerConfig is SnapshotManualRunnerConfig
    assert facade.parse_args is parse_args
    assert facade.build_config is build_config
    assert facade.infer_device_from_filename is infer_device_from_filename
    assert facade.infer_input_metadata is infer_input_metadata
    assert (
        facade.build_manual_snapshot_command
        is build_manual_snapshot_command
    )
    assert facade.run_command is run_command
    assert facade.run_flow is run_flow
