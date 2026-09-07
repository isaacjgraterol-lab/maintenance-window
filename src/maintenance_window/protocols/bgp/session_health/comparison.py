from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from maintenance_window.protocols.bgp.source_guard import (
    validate_same_actual_source,
)
from maintenance_window.protocols.bgp.session_health.extractors import (
    extract_records_from_raw,
)
from maintenance_window.protocols.bgp.session_health.models import (
    BgpSessionHealthComparison,
    BgpSessionHealthRecord,
    BgpSessionHealthResult,
)
from maintenance_window.protocols.bgp.session_health.rules import (
    evaluate_family_health_for_peer,
    evaluate_session_health,
    result_from_peer_and_family_results,
)
from maintenance_window.protocols.bgp.snapshot_comparison.snapshots import (
    load_bgp_snapshot,
)


def _resolve_raw_file(raw_file: str | None) -> Path | None:
    if raw_file is None:
        return None

    path = Path(raw_file)
    if path.exists():
        return path

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path

    return path




def _snapshot_elapsed_seconds(before_created_at: str, after_created_at: str) -> float | None:
    """Return elapsed wall-clock seconds between two snapshot timestamps."""
    try:
        before_dt = datetime.fromisoformat(str(before_created_at).replace("Z", "+00:00"))
        after_dt = datetime.fromisoformat(str(after_created_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

    elapsed = (after_dt - before_dt).total_seconds()
    return elapsed if elapsed >= 0 else None

def _records_by_key(
    records: list[BgpSessionHealthRecord],
) -> dict[tuple[str, str], BgpSessionHealthRecord]:
    """Build a stable peer map. One peer record can contain many families."""
    return {record.key: record for record in records}


def _extract_snapshot_records(
    snapshot: Any,
) -> tuple[Path | None, list[BgpSessionHealthRecord]]:
    raw_file = _resolve_raw_file(snapshot.raw_file)
    if raw_file is None:
        return None, []
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_file}")

    records = extract_records_from_raw(
        raw_file,
        device_name=snapshot.device,
        source=snapshot.source_actual,
    )
    return raw_file, records




_PEER_PREFIX_FIELDS = (
    "active_prefix_count",
    "received_prefix_count",
    "accepted_prefix_count",
    "suppressed_prefix_count",
    "advertised_prefix_count",
)


def _has_prefix_counters(record: BgpSessionHealthRecord | None) -> bool:
    if record is None:
        return False
    if any(getattr(record, name) is not None for name in _PEER_PREFIX_FIELDS):
        return True
    return any(
        any(getattr(family, name) is not None for name in _PEER_PREFIX_FIELDS)
        for family in record.families
    )


def _peer_coverage(
    before: BgpSessionHealthRecord | None,
    after: BgpSessionHealthRecord | None,
    family_results: list[object],
) -> tuple[str, list[str]]:
    """Return data coverage independently from the operational result."""
    if before is None or after is None:
        return "NOT_EVALUATED", ["peer_present_in_both_snapshots"]

    missing: list[str] = []
    for check, attribute in (
        ("peer_as", "peer_as"),
        ("uptime", "elapsed_time_seconds"),
        ("flap_count", "flap_count"),
    ):
        if getattr(before, attribute) is None or getattr(after, attribute) is None:
            missing.append(check)

    if before.is_established or after.is_established:
        if not (_has_prefix_counters(before) and _has_prefix_counters(after)):
            missing.append("prefix_counters")
        if not before.families or not after.families:
            missing.append("afi_safi_families")

    if any(getattr(item, "result", None) == "NOT_EVALUATED" for item in family_results):
        missing.append("afi_safi_comparison")

    unique_missing = list(dict.fromkeys(missing))
    if unique_missing:
        return "PARTIAL", unique_missing
    return "FULL", []


def _comparison_result(
    peer_results: list[BgpSessionHealthResult],
) -> tuple[str, list[str]]:
    fail_reasons: list[str] = []

    if any(item.result == "FAIL" for item in peer_results):
        fail_reasons.append("session_health_failures")
        return "FAIL", fail_reasons

    if any(
        family.result == "FAIL"
        for item in peer_results
        for family in item.family_results
    ):
        fail_reasons.append("session_health_family_failures")
        return "FAIL", fail_reasons

    if any(item.result == "WARNING" for item in peer_results):
        return "WARNING", fail_reasons

    if any(
        family.result == "WARNING"
        for item in peer_results
        for family in item.family_results
    ):
        return "WARNING", fail_reasons

    if any(item.result == "UNHEALTHY" for item in peer_results):
        return "PASS_WITH_UNHEALTHY_SESSIONS", fail_reasons

    return "PASS", fail_reasons


def compare_session_health_snapshots(
    *,
    snapshot_root: Path,
    mw_id: str,
    before_stage: str,
    after_stage: str,
    device: str,
) -> BgpSessionHealthComparison:
    """Compare BGP session-health data using snapshot raw files."""
    before_snapshot = load_bgp_snapshot(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=before_stage,
        device=device,
    )
    after_snapshot = load_bgp_snapshot(
        snapshot_root=snapshot_root,
        mw_id=mw_id,
        stage=after_stage,
        device=device,
    )

    validate_same_actual_source(
        before_snapshot.source_actual,
        after_snapshot.source_actual,
    )

    before_raw_file, before_records = _extract_snapshot_records(before_snapshot)
    after_raw_file, after_records = _extract_snapshot_records(after_snapshot)
    snapshot_elapsed_seconds = _snapshot_elapsed_seconds(
        before_snapshot.created_at_utc,
        after_snapshot.created_at_utc,
    )

    before_map = _records_by_key(before_records)
    after_map = _records_by_key(after_records)
    all_keys = sorted(set(before_map) | set(after_map))

    peer_results: list[BgpSessionHealthResult] = []
    for device_name, neighbor in all_keys:
        before = before_map.get((device_name, neighbor))
        after = after_map.get((device_name, neighbor))
        findings = evaluate_session_health(
            before,
            after,
            snapshot_elapsed_seconds=snapshot_elapsed_seconds,
        )
        family_results = evaluate_family_health_for_peer(
            before,
            after,
            device=device_name,
            neighbor=neighbor,
        )
        coverage, not_evaluated_checks = _peer_coverage(
            before,
            after,
            family_results,
        )
        peer_results.append(
            BgpSessionHealthResult(
                device=device_name,
                neighbor=neighbor,
                result=result_from_peer_and_family_results(
                    findings,
                    family_results,
                ),
                before=before,
                after=after,
                findings=findings,
                family_results=family_results,
                coverage=coverage,
                not_evaluated_checks=not_evaluated_checks,
            )
        )

    result, fail_reasons = _comparison_result(peer_results)

    return BgpSessionHealthComparison(
        mw_id=mw_id,
        device=device,
        before_stage=before_stage,
        after_stage=after_stage,
        result=result,
        before_raw_file=before_raw_file,
        after_raw_file=after_raw_file,
        peer_results=peer_results,
        fail_reasons=fail_reasons,
        before_source_requested=before_snapshot.source_requested,
        after_source_requested=after_snapshot.source_requested,
        before_source_actual=before_snapshot.source_actual,
        after_source_actual=after_snapshot.source_actual,
    )
