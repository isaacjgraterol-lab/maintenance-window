"""Compatibility tests for the comparison runner facade."""

from maintenance_window.runners import snapshot_comparison as facade
from maintenance_window.runners.snapshot_comparison.arguments import (
    parse_args,
)
from maintenance_window.runners.snapshot_comparison.commands import (
    build_compare_command,
)
from maintenance_window.runners.snapshot_comparison.config import (
    build_config,
)
from maintenance_window.runners.snapshot_comparison.execution import (
    run_command,
    run_flow,
)
from maintenance_window.runners.snapshot_comparison.models import (
    SnapshotComparisonConfig,
)


def test_comparison_facade_reexports_components() -> None:
    assert facade.SnapshotComparisonConfig is SnapshotComparisonConfig
    assert facade.parse_args is parse_args
    assert facade.build_config is build_config
    assert facade.build_compare_command is build_compare_command
    assert facade.run_command is run_command
    assert facade.run_flow is run_flow
