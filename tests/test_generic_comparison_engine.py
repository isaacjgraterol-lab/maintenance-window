from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from maintenance_window.engine.comparison.contracts import (
    ComparisonAdapter,
)
from maintenance_window.engine.comparison.engine import compare_items
from maintenance_window.engine.comparison.indexing import (
    build_item_map,
    duplicate_count,
    find_duplicates,
)
from maintenance_window.engine.comparison.validation import (
    validate_snapshot_pair,
)


@dataclass(frozen=True)
class ExampleItem:
    key: str
    state: str


EXAMPLE_ADAPTER = ComparisonAdapter[
    ExampleItem,
    str,
](
    item_key=lambda item: item.key,
    item_state=lambda item: item.state,
    is_healthy=lambda item: item.state == "up",
    key_sort_value=lambda key: (key,),
)


def _snapshot(
    *,
    mw_id: str = "MW-001",
    stage: str = "before",
    device: str = "router-a",
) -> SimpleNamespace:
    return SimpleNamespace(
        mw_id=mw_id,
        stage=stage,
        device=device,
    )


def test_generic_item_map_uses_last_duplicate_record() -> None:
    values = [
        ExampleItem("peer-a", "down"),
        ExampleItem("peer-a", "up"),
    ]

    result = build_item_map(values, EXAMPLE_ADAPTER)

    assert result == {
        "peer-a": ExampleItem("peer-a", "up"),
    }


def test_generic_duplicate_detection_is_sorted_and_counted() -> None:
    values = [
        ExampleItem("peer-b", "down"),
        ExampleItem("peer-a", "up"),
        ExampleItem("peer-b", "active"),
        ExampleItem("peer-a", "up"),
    ]

    duplicates = find_duplicates(values, EXAMPLE_ADAPTER)

    assert [item.key for item in duplicates] == [
        "peer-a",
        "peer-b",
    ]
    assert duplicates[1].count == 2
    assert duplicates[1].states == [
        "active",
        "down",
    ]
    assert duplicate_count(duplicates) == 2


def test_generic_engine_detects_pre_post_differences() -> None:
    before = [
        ExampleItem("peer-a", "up"),
        ExampleItem("peer-b", "down"),
        ExampleItem("peer-lost", "up"),
    ]
    after = [
        ExampleItem("peer-a", "down"),
        ExampleItem("peer-b", "up"),
        ExampleItem("peer-new", "up"),
    ]

    result = compare_items(
        before,
        after,
        EXAMPLE_ADAPTER,
    )

    assert [item.key for item in result.lost_items] == [
        "peer-lost",
    ]
    assert [item.key for item in result.new_items] == [
        "peer-new",
    ]
    assert [
        (
            item.key,
            item.before_state,
            item.after_state,
        )
        for item in result.state_changes
    ] == [
        ("peer-a", "up", "down"),
        ("peer-b", "down", "up"),
    ]
    assert [item.key for item in result.new_unhealthy] == [
        "peer-a",
    ]
    assert [item.key for item in result.resolved_unhealthy] == [
        "peer-b",
    ]


def test_generic_engine_preserves_persistent_unhealthy_items() -> None:
    before = [ExampleItem("peer-a", "down")]
    after = [ExampleItem("peer-a", "active")]

    result = compare_items(
        before,
        after,
        EXAMPLE_ADAPTER,
    )

    assert result.new_unhealthy == []
    assert result.resolved_unhealthy == []
    assert result.persistent_unhealthy == [
        ExampleItem("peer-a", "active"),
    ]


def test_snapshot_validation_accepts_matching_pair() -> None:
    validate_snapshot_pair(
        _snapshot(stage=" BEFORE "),
        _snapshot(stage="after"),
        expected_mw_id="MW-001",
        expected_device="router-a",
        expected_before_stage="before",
        expected_after_stage="AFTER",
    )


def test_snapshot_validation_rejects_mw_id_mismatch() -> None:
    with pytest.raises(ValueError, match="MW ID mismatch"):
        validate_snapshot_pair(
            _snapshot(mw_id="MW-001"),
            _snapshot(
                mw_id="MW-002",
                stage="after",
            ),
        )


def test_snapshot_validation_rejects_device_mismatch() -> None:
    with pytest.raises(ValueError, match="device mismatch"):
        validate_snapshot_pair(
            _snapshot(device="router-a"),
            _snapshot(
                device="router-b",
                stage="after",
            ),
        )


def test_snapshot_validation_rejects_same_stage() -> None:
    with pytest.raises(
        ValueError,
        match="stages must be different",
    ):
        validate_snapshot_pair(
            _snapshot(stage="BEFORE"),
            _snapshot(stage=" before "),
        )


@pytest.mark.parametrize(
    ("field", "kwargs", "message"),
    [
        (
            "mw_id",
            {"expected_mw_id": "MW-999"},
            "requested value",
        ),
        (
            "device",
            {"expected_device": "router-z"},
            "requested value",
        ),
        (
            "before_stage",
            {"expected_before_stage": "pre"},
            "PRE snapshot stage",
        ),
        (
            "after_stage",
            {"expected_after_stage": "post"},
            "POST snapshot stage",
        ),
    ],
)
def test_snapshot_validation_rejects_requested_metadata_mismatch(
    field: str,
    kwargs: dict[str, str],
    message: str,
) -> None:
    del field

    with pytest.raises(ValueError, match=message):
        validate_snapshot_pair(
            _snapshot(stage="before"),
            _snapshot(stage="after"),
            **kwargs,
        )
