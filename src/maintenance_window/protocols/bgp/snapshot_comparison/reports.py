from __future__ import annotations

from typing import Any


def _session_to_dict(session: BgpSession) -> dict[str, Any]:
    """
    Convert a BGP session to dictionary.
    """
    return session.to_dict()



def _is_established_state(value: object) -> bool:
    return str(value).strip().lower() == "established"


def _unhealthy_fsm_transitions(
    comparison: BgpSnapshotComparison,
) -> list[BgpSnapshotStateChange]:
    return [
        item
        for item in comparison.state_changes
        if not _is_established_state(item.before_state)
        and not _is_established_state(item.after_state)
    ]


def print_snapshot_comparison_report(
    comparison: BgpSnapshotComparison,
) -> None:
    """
    Print a readable BGP before/after comparison report.
    """
    print(
        f"\nBGP snapshot comparison: "
        f"{comparison.before_stage} vs {comparison.after_stage}\n"
    )

    print(f"Maintenance Window: {comparison.mw_id}")
    print(f"Device: {comparison.device}")
    print(f"Result: {comparison.result}")

    if comparison.fail_reasons:
        print(f"Fail reasons: {', '.join(comparison.fail_reasons)}")

    print(f"\n{comparison.before_stage} total sessions: {comparison.before_count}")
    print(f"{comparison.after_stage} total sessions: {comparison.after_count}")
    print(f"{comparison.before_stage} unique sessions: {comparison.before_unique_count}")
    print(f"{comparison.after_stage} unique sessions: {comparison.after_unique_count}")
    print(f"Common unique sessions: {comparison.common_count}")

    print(f"\nLost sessions: {len(comparison.lost_sessions)}")
    print(f"New sessions: {len(comparison.new_sessions)}")
    print(f"State changes: {len(comparison.state_changes)}")
    print(
        "Unhealthy FSM transitions: "
        f"{len(_unhealthy_fsm_transitions(comparison))}"
    )
    print(f"New unhealthy sessions: {len(comparison.new_unhealthy)}")
    print(f"Resolved unhealthy sessions: {len(comparison.resolved_unhealthy)}")
    print(f"Persistent unhealthy sessions: {len(comparison.persistent_unhealthy)}")

    print(f"\n{comparison.before_stage} duplicate entries: {comparison.before_duplicate_count}")
    print(f"{comparison.after_stage} duplicate entries: {comparison.after_duplicate_count}")

    if comparison.lost_sessions:
        print("\nLost sessions:")
        for session in comparison.lost_sessions:
            print(f"  {session.device} {session.neighbor} {session.state}")

    if comparison.new_sessions:
        print("\nNew sessions:")
        for session in comparison.new_sessions:
            print(f"  {session.device} {session.neighbor} {session.state}")

    if comparison.state_changes:
        print("\nState changes:")
        for item in comparison.state_changes:
            print(
                f"  {item.device} {item.neighbor}: "
                f"{item.before_state} -> {item.after_state}"
            )

    if comparison.new_unhealthy:
        print("\nNew unhealthy sessions:")
        for session in comparison.new_unhealthy:
            print(f"  {session.device} {session.neighbor} {session.state}")

    if comparison.resolved_unhealthy:
        print("\nResolved unhealthy sessions:")
        for session in comparison.resolved_unhealthy:
            print(f"  {session.device} {session.neighbor} {session.state}")

    if comparison.persistent_unhealthy:
        print("\nPersistent unhealthy sessions:")
        for session in comparison.persistent_unhealthy:
            print(f"  {session.device} {session.neighbor} {session.state}")


def snapshot_comparison_to_dict(
    comparison: BgpSnapshotComparison,
    before_snapshot: BgpSnapshot,
    after_snapshot: BgpSnapshot,
) -> dict[str, Any]:
    """
    Convert a BGP snapshot comparison to a JSON-serializable dictionary.
    """
    return {
        "mw_id": comparison.mw_id,
        "device": comparison.device,
        "result": comparison.result,
        "fail_reasons": comparison.fail_reasons,
        "before": {
            "stage": before_snapshot.stage,
            "source_requested": before_snapshot.source_requested,
            "source_actual": before_snapshot.source_actual,
            "source_fallback": (
                before_snapshot.source_requested != before_snapshot.source_actual
            ),
            "raw_file": before_snapshot.raw_file,
            "snapshot_file": str(before_snapshot.path),
            "total_sessions": comparison.before_count,
            "unique_sessions": comparison.before_unique_count,
            "duplicate_entries": comparison.before_duplicate_count,
        },
        "after": {
            "stage": after_snapshot.stage,
            "source_requested": after_snapshot.source_requested,
            "source_actual": after_snapshot.source_actual,
            "source_fallback": (
                after_snapshot.source_requested != after_snapshot.source_actual
            ),
            "raw_file": after_snapshot.raw_file,
            "snapshot_file": str(after_snapshot.path),
            "total_sessions": comparison.after_count,
            "unique_sessions": comparison.after_unique_count,
            "duplicate_entries": comparison.after_duplicate_count,
        },
        "common_count": comparison.common_count,
        "lost_sessions_count": len(comparison.lost_sessions),
        "new_sessions_count": len(comparison.new_sessions),
        "state_changes_count": len(comparison.state_changes),
        "unhealthy_fsm_transitions_count": len(
            _unhealthy_fsm_transitions(comparison)
        ),
        "new_unhealthy_count": len(comparison.new_unhealthy),
        "resolved_unhealthy_count": len(comparison.resolved_unhealthy),
        "persistent_unhealthy_count": len(comparison.persistent_unhealthy),
        "lost_sessions": [
            session.to_dict()
            for session in comparison.lost_sessions
        ],
        "new_sessions": [
            session.to_dict()
            for session in comparison.new_sessions
        ],
        "state_changes": [
            {
                "device": item.device,
                "neighbor": item.neighbor,
                "before_state": item.before_state,
                "after_state": item.after_state,
            }
            for item in comparison.state_changes
        ],
        "unhealthy_fsm_transitions": [
            {
                "device": item.device,
                "neighbor": item.neighbor,
                "before_state": item.before_state,
                "after_state": item.after_state,
            }
            for item in _unhealthy_fsm_transitions(comparison)
        ],
        "new_unhealthy": [
            session.to_dict()
            for session in comparison.new_unhealthy
        ],
        "resolved_unhealthy": [
            session.to_dict()
            for session in comparison.resolved_unhealthy
        ],
        "persistent_unhealthy": [
            session.to_dict()
            for session in comparison.persistent_unhealthy
        ],
    }
