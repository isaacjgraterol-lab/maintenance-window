from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.core.path_safety import safe_path_part, validate_mw_id
from maintenance_window.engine.snapshots.paths import build_snapshot_path


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "CON", "nul", "COM1", "MW/ONE", "MW\\ONE", ".hidden", "MW."],
)
def test_validate_mw_id_rejects_unsafe_windows_path_values(value: str) -> None:
    with pytest.raises(ValueError):
        validate_mw_id(value)


def test_validate_mw_id_accepts_release_style_identifier() -> None:
    assert validate_mw_id("MW_DEMO-BGP.001") == "MW_DEMO-BGP.001"


def test_safe_path_part_neutralizes_windows_reserved_names() -> None:
    assert safe_path_part("CON") == "_CON"
    assert safe_path_part("..")== "unknown"
    assert safe_path_part("router/1") == "router_1"


def test_snapshot_path_cannot_escape_mw_namespace(tmp_path: Path) -> None:
    path = build_snapshot_path(tmp_path, "..", "before", "192.0.2.10")
    assert path == tmp_path / "unknown" / "before" / "192.0.2.10.json"
    assert path.resolve().is_relative_to(tmp_path.resolve())


def test_snapshot_path_module_exports_only_available_public_names() -> None:
    import maintenance_window.engine.snapshots.paths as paths

    assert set(paths.__all__) == {"build_snapshot_path", "safe_path_part"}
    assert all(hasattr(paths, name) for name in paths.__all__)
