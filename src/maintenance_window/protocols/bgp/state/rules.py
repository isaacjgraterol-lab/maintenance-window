from __future__ import annotations

from maintenance_window.engine.comparison.models import ComparisonDiff
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.snapshot_comparison.snapshot_models import (
    BgpSnapshotSessionKey,
)


def build_bgp_fail_reasons(
    diff: ComparisonDiff[
        BgpSession,
        BgpSnapshotSessionKey,
    ],
) -> list[str]:
    """Apply the initial BGP State PASS/FAIL policy."""
    fail_reasons: list[str] = []

    if diff.lost_items:
        fail_reasons.append("lost_sessions")

    if diff.new_unhealthy:
        fail_reasons.append("new_unhealthy_sessions")

    return fail_reasons
