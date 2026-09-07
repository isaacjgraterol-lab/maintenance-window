"""Public BGP snapshot storage facade."""

from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshot,
    BgpSnapshotComparison,
    BgpSnapshotDuplicateSession,
    BgpSnapshotSessionKey,
    BgpSnapshotStateChange,
)
from maintenance_window.protocols.bgp.snapshot_store.paths import (
    build_snapshot_path,
    safe_path_part as _safe_path_part,
)
from maintenance_window.protocols.bgp.snapshot_store.reader import (
    load_bgp_snapshot,
)
from maintenance_window.protocols.bgp.snapshot_store.serialization import (
    session_from_dict as _session_from_dict,
    session_to_dict as _session_to_dict,
)
from maintenance_window.protocols.bgp.snapshot_store.sessions import (
    build_session_groups as _build_session_groups,
    build_session_key as _build_session_key,
    build_session_map as _build_session_map,
    duplicate_count as _duplicate_count,
    find_duplicates as _find_duplicates,
    is_healthy_state as _is_healthy_state,
    is_unhealthy_session as _is_unhealthy_session,
)
from maintenance_window.protocols.bgp.snapshot_store.writer import (
    write_bgp_snapshot,
)

__all__ = [
    "build_snapshot_path",
    "load_bgp_snapshot",
    "write_bgp_snapshot",
]
