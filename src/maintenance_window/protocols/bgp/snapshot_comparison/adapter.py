from __future__ import annotations

from maintenance_window.engine.comparison.contracts import (
    ComparisonAdapter,
)
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshotSessionKey,
)
from maintenance_window.protocols.bgp.snapshot_store.sessions import (
    build_session_key,
    is_healthy_state,
)


def _session_state(session: BgpSession) -> str:
    return session.state


def _session_is_healthy(session: BgpSession) -> bool:
    return is_healthy_state(session.state)


def _session_key_sort_value(
    key: BgpSnapshotSessionKey,
) -> tuple[str, ...]:
    return key.device, key.neighbor


BGP_COMPARISON_ADAPTER = ComparisonAdapter[
    BgpSession,
    BgpSnapshotSessionKey,
](
    item_key=build_session_key,
    item_state=_session_state,
    is_healthy=_session_is_healthy,
    key_sort_value=_session_key_sort_value,
)
