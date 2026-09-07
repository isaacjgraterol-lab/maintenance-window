from __future__ import annotations

from typing import Any


def _session_to_dict(session: Any) -> dict[str, Any]:
    """
    Convert a BGP session-like object to a report dictionary.

    Kept local so source_reports.py does not need to import service.py.
    """
    return {
        "device": session.device,
        "neighbor": session.neighbor,
        "state": session.state,
    }


def print_comparison_report(
    comparison: BgpSourceComparison,
) -> None:
    """
    Print a readable BGP comparison report.
    """
    print(
        f"\nBGP source comparison: "
        f"{comparison.left_source} vs {comparison.right_source}\n"
    )

    print(f"{comparison.left_source} total sessions: {comparison.left_count}")
    print(f"{comparison.right_source} total sessions: {comparison.right_count}")
    print(f"{comparison.left_source} unique sessions: {comparison.left_unique_count}")
    print(f"{comparison.right_source} unique sessions: {comparison.right_unique_count}")
    print(f"Common unique sessions: {comparison.common_count}")
    print(f"Only in {comparison.left_source}: {len(comparison.only_left)}")
    print(f"Only in {comparison.right_source}: {len(comparison.only_right)}")
    print(f"Different state: {len(comparison.different_state)}")
    print(f"{comparison.left_source} duplicate entries: {comparison.left_duplicate_count}")
    print(f"{comparison.right_source} duplicate entries: {comparison.right_duplicate_count}")

    if comparison.left_duplicates:
        print(f"\nDuplicates in {comparison.left_source}:")
        for item in comparison.left_duplicates:
            states = ", ".join(item.states)
            print(
                f"  {item.device} {item.neighbor} "
                f"count={item.count} states={states}"
            )

    if comparison.right_duplicates:
        print(f"\nDuplicates in {comparison.right_source}:")
        for item in comparison.right_duplicates:
            states = ", ".join(item.states)
            print(
                f"  {item.device} {item.neighbor} "
                f"count={item.count} states={states}"
            )

    if comparison.only_left:
        print(f"\nOnly in {comparison.left_source}:")
        for session in comparison.only_left:
            print(
                f"  {session.device} "
                f"{session.neighbor} "
                f"{session.state}"
            )

    if comparison.only_right:
        print(f"\nOnly in {comparison.right_source}:")
        for session in comparison.only_right:
            print(
                f"  {session.device} "
                f"{session.neighbor} "
                f"{session.state}"
            )

    if comparison.different_state:
        print("\nSame neighbor with different state:")
        for item in comparison.different_state:
            print(
                f"  {item.device} {item.neighbor}: "
                f"{comparison.left_source}={item.left_state}, "
                f"{comparison.right_source}={item.right_state}"
            )


def comparison_to_dict(
    comparison: BgpSourceComparison,
) -> dict[str, Any]:
    """
    Convert a BGP source comparison into a JSON-serializable dictionary.
    """
    return {
        "left_source": comparison.left_source,
        "right_source": comparison.right_source,
        "left_count": comparison.left_count,
        "right_count": comparison.right_count,
        "left_unique_count": comparison.left_unique_count,
        "right_unique_count": comparison.right_unique_count,
        "common_count": comparison.common_count,
        "only_left_count": len(comparison.only_left),
        "only_right_count": len(comparison.only_right),
        "different_state_count": len(comparison.different_state),
        "left_duplicate_count": comparison.left_duplicate_count,
        "right_duplicate_count": comparison.right_duplicate_count,
        "left_duplicates": [
            {
                "device": item.device,
                "neighbor": item.neighbor,
                "count": item.count,
                "states": item.states,
            }
            for item in comparison.left_duplicates
        ],
        "right_duplicates": [
            {
                "device": item.device,
                "neighbor": item.neighbor,
                "count": item.count,
                "states": item.states,
            }
            for item in comparison.right_duplicates
        ],
        "only_left": [
            session.to_dict()
            for session in comparison.only_left
        ],
        "only_right": [
            session.to_dict()
            for session in comparison.only_right
        ],
        "different_state": [
            {
                "device": item.device,
                "neighbor": item.neighbor,
                "left_state": item.left_state,
                "right_state": item.right_state,
            }
            for item in comparison.different_state
        ],
    }
