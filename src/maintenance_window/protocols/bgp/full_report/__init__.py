"""BGP full Maintenance Window report module.

CLI entry points are exposed lazily so importing report helpers does not create a
circular dependency through the snapshot-comparison execution layer.
"""

from __future__ import annotations

from typing import Any


__all__ = [
    "run_bgp_full_report",
    "run_bgp_full_report_comparison",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)

    from maintenance_window.protocols.bgp.full_report.cli import (
        run_bgp_full_report,
        run_bgp_full_report_comparison,
    )

    exports = {
        "run_bgp_full_report": run_bgp_full_report,
        "run_bgp_full_report_comparison": run_bgp_full_report_comparison,
    }
    return exports[name]
