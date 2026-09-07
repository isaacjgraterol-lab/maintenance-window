"""Build safe CLI commands for the local GUI.

The GUI must not duplicate BGP protocol logic. It builds the same CLI commands
operators already validated and lets the existing CLI modules execute the work.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from maintenance_window.core.path_safety import validate_mw_id
from maintenance_window.ui.options import (
    AUTH_BACKEND_OPTIONS,
    DEVICE_MODE_OPTIONS,
    HEALTH_DEPTH_OPTIONS,
    CAPTURE_LEVEL_OPTIONS,
    MANUAL_DB_LIMIT_OPTIONS,
    MANUAL_INPUT_FORMAT_OPTIONS,
    MODULE_OPTIONS,
    SOURCE_OPTIONS,
    WORKER_OPTIONS,
)


VALID_ACTIONS = frozenset(
    {
        "capture-before",
        "capture-after",
        "compare-state",
        "compare-session-health",
        "compare-full",
        "list-manual-db",
    }
)

LIVE_SOURCES = frozenset({"pyez", "ssh", "gnmic"})
COMPARE_ACTIONS = frozenset(
    {"compare-state", "compare-session-health", "compare-full"}
)
CAPTURE_ACTIONS = frozenset({"capture-before", "capture-after"})


@dataclass(frozen=True, slots=True)
class UiCommandRequest:
    action: str
    protocol: str
    source: str
    device_mode: str
    device: str
    mw_id: str
    auth_backend: str = "radius"
    health_depth: str = "auto"
    capture_level: str = "basic"
    filter_value: str = "all"
    workers: int = 1
    credentials_path: Path | None = None
    inventory_path: Path | None = None
    manual_input_path: Path | None = None
    manual_input_format: str = "auto"
    manual_db_limit: int = 200


@dataclass(frozen=True, slots=True)
class UiCommand:
    command: list[str]
    export_path: Path | None



def _validate_request(request: UiCommandRequest) -> None:
    if request.action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported GUI action: {request.action}")
    if request.protocol != "bgp":
        raise ValueError("Only BGP is available in the current GUI foundation.")
    if request.source not in SOURCE_OPTIONS:
        raise ValueError(f"Unsupported source: {request.source}")
    if request.device_mode not in DEVICE_MODE_OPTIONS:
        raise ValueError(f"Unsupported device mode: {request.device_mode}")
    if request.auth_backend not in AUTH_BACKEND_OPTIONS:
        raise ValueError(f"Unsupported auth backend: {request.auth_backend}")
    if request.health_depth not in HEALTH_DEPTH_OPTIONS:
        raise ValueError(f"Unsupported health depth: {request.health_depth}")
    if request.capture_level not in CAPTURE_LEVEL_OPTIONS:
        raise ValueError(f"Unsupported capture level: {request.capture_level}")
    if request.manual_input_format not in MANUAL_INPUT_FORMAT_OPTIONS:
        raise ValueError(
            f"Unsupported manual input format: {request.manual_input_format}"
        )
    if request.manual_db_limit not in MANUAL_DB_LIMIT_OPTIONS:
        raise ValueError("Manual DB limit must be one of: 50, 100, 200, or 500.")
    if request.workers not in WORKER_OPTIONS:
        raise ValueError("Workers must be one of: 1, 5, 10, 15, or 20.")
    if request.source == "gnmic" and request.health_depth == "full-health":
        raise ValueError("gNMIc does not support full-health with the current path.")
    if request.health_depth == "state-only" and request.action in {
        "compare-session-health",
        "compare-full",
    }:
        raise ValueError(
            "Health depth state-only only supports Compare State. "
            "Select auto, partial-health, or full-health for this comparison."
        )

    if request.action in CAPTURE_ACTIONS:
        if request.device_mode == "individual" and not request.device.strip():
            raise ValueError("Device IP / Hostname is required.")
        if request.device_mode == "db" and request.inventory_path is None:
            raise ValueError("Inventory path is required for Database Inventory mode.")
        if request.device_mode == "db" and request.source == "manual":
            raise ValueError("Manual source does not support Database Inventory mode.")
        if request.source == "manual" and request.manual_input_path is None:
            raise ValueError("Manual source requires a JSON/XML input path.")


def _compare_module_for_action(action: str) -> str:
    if action == "compare-state":
        return "state"
    if action == "compare-session-health":
        return "session-health"
    if action == "compare-full":
        return "full"
    raise ValueError(f"Action does not map to a comparison module: {action}")


def _snapshot_devices_for_mw(
    *,
    project_root: Path,
    mw_id: str,
) -> list[str]:
    """Return devices that have both before and after snapshots for this MW."""
    snapshot_root = project_root / "outputs" / "snapshots" / "bgp" / mw_id
    before_dir = snapshot_root / "before"
    after_dir = snapshot_root / "after"

    if not before_dir.exists():
        raise ValueError(f"Before snapshot directory not found: {before_dir}")
    if not after_dir.exists():
        raise ValueError(f"After snapshot directory not found: {after_dir}")

    before_devices = {
        path.stem
        for path in before_dir.glob("*.json")
        if path.is_file()
    }
    after_devices = {
        path.stem
        for path in after_dir.glob("*.json")
        if path.is_file()
    }

    common_devices = sorted(before_devices & after_devices)

    if not common_devices:
        raise ValueError(
            "No devices have both before and after snapshots for MW "
            f"{mw_id}."
        )

    return common_devices


def _capture_command(
    request: UiCommandRequest,
    *,
    base: list[str],
    mw_id: str,
) -> UiCommand:
    stage = "before" if request.action == "capture-before" else "after"
    device_argument = "all" if request.device_mode == "db" else request.device.strip()

    command = base + [
        "--source",
        request.source,
        "--snapshot",
        stage,
        "--mw-id",
        mw_id,
        "--device",
        device_argument,
    ]

    if request.device_mode == "db" and request.inventory_path is not None:
        command.extend(["--inventory", str(request.inventory_path)])

    command.extend(
        [
            "--filter",
            request.filter_value,
            "--output",
            "summary",
        ]
    )

    if request.source in LIVE_SOURCES:
        command.extend(
            [
                "--auth-backend",
                request.auth_backend,
                "--workers",
                str(request.workers),
            ]
        )
        if request.credentials_path is not None:
            command.extend(["--credentials", str(request.credentials_path)])

    if request.source == "manual":
        if request.manual_input_path is not None:
            command.extend(["--input", str(request.manual_input_path)])
        if request.manual_input_format != "auto":
            command.extend(["--input-format", request.manual_input_format])

    return UiCommand(command=command, export_path=None)


def build_mw_command(
    request: UiCommandRequest,
    *,
    project_root: Path,
    python_executable: str | None = None,
) -> UiCommand:
    """Build the CLI command executed by the local GUI."""
    _validate_request(request)

    python_bin = python_executable or sys.executable
    main_py = project_root / "main.py"

    base = [
        python_bin,
        str(main_py),
        "--protocol",
        "bgp",
    ]

    if request.action == "list-manual-db":
        return UiCommand(
            command=base
            + [
                "--list-manual-db",
                "--manual-db-limit",
                str(request.manual_db_limit),
            ],
            export_path=None,
        )

    mw_id = validate_mw_id(request.mw_id)

    if request.action in CAPTURE_ACTIONS:
        return _capture_command(request, base=base, mw_id=mw_id)

    module = _compare_module_for_action(request.action)
    if module not in MODULE_OPTIONS:
        raise ValueError(f"Unsupported comparison module: {module}")

    devices = _snapshot_devices_for_mw(project_root=project_root, mw_id=mw_id)
    device_argument = ",".join(devices)

    export_path = (
        project_root
        / "outputs"
        / "reports"
        / f"gui_{mw_id}_{module.replace('-', '_')}.json"
    )

    return UiCommand(
        command=base
        + [
            "--module",
            module,
            "--compare-snapshots",
            "before,after",
            "--mw-id",
            mw_id,
            "--device",
            device_argument,
            "--output",
            "summary",
            "--export",
            str(export_path),
        ],
        export_path=export_path,
    )
