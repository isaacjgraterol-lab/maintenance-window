"""Public facade for the standard BGP validation CLI handler."""

from maintenance_window.cli_handlers.validation.execution import (
    run_bgp_validation,
)
from maintenance_window.cli_handlers.validation.request import (
    load_protocol_runtime_settings as _load_protocol_runtime_settings,
    resolve_devices as _resolve_devices,
)

__all__ = ["run_bgp_validation"]
