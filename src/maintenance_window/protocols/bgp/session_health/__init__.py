"""BGP session health comparison module."""

from maintenance_window.protocols.bgp.session_health.comparison import (
    compare_session_health_snapshots,
)
from maintenance_window.protocols.bgp.session_health.uptime import (
    parse_bgp_uptime_to_seconds,
)
from maintenance_window.protocols.bgp.session_health.family_map import family_from_table
from maintenance_window.protocols.bgp.session_health.models import (
    BgpFamilyHealthCounters,
    BgpFamilyHealthResult,
    BgpSessionHealthComparison,
    BgpSessionHealthFinding,
    BgpSessionHealthRecord,
    BgpSessionHealthResult,
)

__all__ = [
    "BgpFamilyHealthCounters",
    "BgpFamilyHealthResult",
    "BgpSessionHealthComparison",
    "BgpSessionHealthFinding",
    "BgpSessionHealthRecord",
    "BgpSessionHealthResult",
    "compare_session_health_snapshots",
    "family_from_table",
    "parse_bgp_uptime_to_seconds",
]
