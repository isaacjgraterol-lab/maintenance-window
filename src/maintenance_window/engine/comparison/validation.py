from __future__ import annotations

from typing import Protocol


class SnapshotMetadata(Protocol):
    """Metadata required to validate a PRE/POST snapshot pair."""

    mw_id: str
    stage: str
    device: str


def _normalized(value: str) -> str:
    return value.strip().lower()


def validate_snapshot_pair(
    before: SnapshotMetadata,
    after: SnapshotMetadata,
    *,
    expected_mw_id: str | None = None,
    expected_device: str | None = None,
    expected_before_stage: str | None = None,
    expected_after_stage: str | None = None,
) -> None:
    """Validate that two snapshots belong to one comparable operation."""
    if before.mw_id != after.mw_id:
        raise ValueError(
            "Snapshot MW ID mismatch: "
            f"{before.mw_id!r} != {after.mw_id!r}."
        )

    if before.device != after.device:
        raise ValueError(
            "Snapshot device mismatch: "
            f"{before.device!r} != {after.device!r}."
        )

    if _normalized(before.stage) == _normalized(after.stage):
        raise ValueError(
            "Snapshot stages must be different: "
            f"{before.stage!r} and {after.stage!r}."
        )

    if expected_mw_id is not None and before.mw_id != expected_mw_id:
        raise ValueError(
            "Snapshot MW ID does not match the requested value: "
            f"{before.mw_id!r} != {expected_mw_id!r}."
        )

    if expected_device is not None and before.device != expected_device:
        raise ValueError(
            "Snapshot device does not match the requested value: "
            f"{before.device!r} != {expected_device!r}."
        )

    if (
        expected_before_stage is not None
        and _normalized(before.stage)
        != _normalized(expected_before_stage)
    ):
        raise ValueError(
            "PRE snapshot stage does not match the requested value: "
            f"{before.stage!r} != {expected_before_stage!r}."
        )

    if (
        expected_after_stage is not None
        and _normalized(after.stage)
        != _normalized(expected_after_stage)
    ):
        raise ValueError(
            "POST snapshot stage does not match the requested value: "
            f"{after.stage!r} != {expected_after_stage!r}."
        )
