# Unit tests for OrderControlTvt baseline alignment (design memo §25.25.34.30).
#
# Run from the repository root:
#   python tests_order_control_tvt_baseline_alignment.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import copy
import dataclasses

from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtResolvedUndeterminedVisit,
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
    align_snapshot_undetermined_visits_with_node_baseline,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)


def _new_rank_state(node_name: str = "merge") -> OrderControlTvtNodeRankState:
    return OrderControlTvtNodeRankState(node_name)


def _register_undetermined(
    state: OrderControlTvtNodeRankState,
    *visit_keys: OrderControlTvtVisitKey,
) -> None:
    for visit_key in visit_keys:
        state.register_undetermined_visit(visit_key)


def _minimal_record(
    *,
    vehicle_name: str = "veh_a",
    vehicle_id: int = 0,
    node_name: str = "merge",
    inlink_name: str = "in1",
    visit_id: int = 1,
    was_arrived_at_snapshot: bool = False,
    baseline_arrival_timestep: int | None = None,
    arrival_tiebreaker: int | float | None = None,
    route_next_link_name: str | None = None,
    baseline_passage_timestep: int | None = None,
) -> dict:
    return {
        "vehicle_name": vehicle_name,
        "vehicle_id": vehicle_id,
        "node_name": node_name,
        "inlink_name": inlink_name,
        "visit_id": visit_id,
        "was_arrived_at_snapshot": was_arrived_at_snapshot,
        "baseline_arrival_timestep": baseline_arrival_timestep,
        "arrival_tiebreaker": arrival_tiebreaker,
        "route_next_link_name": route_next_link_name,
        "baseline_passage_timestep": baseline_passage_timestep,
    }


def _align(
    records: list[dict],
    state: OrderControlTvtNodeRankState | None = None,
    node_name: str = "merge",
) -> OrderControlTvtSnapshotUndeterminedAlignmentResult:
    rank_state = state if state is not None else _new_rank_state(node_name)
    return align_snapshot_undetermined_visits_with_node_baseline(
        node_name=node_name,
        node_baseline_visit_records=records,
        node_rank_state=rank_state,
    )


def test_empty_collector_records_return_three_empty_columns():
    state = _new_rank_state()
    result = _align([], state)
    assert result.node_name == "merge"
    assert result.resolved_undetermined_visits == ()
    assert result.unresolved_undetermined_visits == ()
    assert result.unregistered_collector_visit_keys == ()


def test_resolved_undetermined_visit_goes_to_resolved_column():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    record = _minimal_record(
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.5,
        route_next_link_name="out",
    )
    result = _align([record], state)
    assert len(result.resolved_undetermined_visits) == 1
    resolved = result.resolved_undetermined_visits[0]
    assert resolved.visit_key == ("veh_a", 1)
    assert resolved.baseline_arrival_timestep == 10
    assert resolved.arrival_tiebreaker == 0.5
    assert resolved.vehicle_id == 0


def test_resolved_column_uses_three_key_sort_order():
    state = _new_rank_state()
    _register_undetermined(
        state,
        ("veh_c", 3),
        ("veh_a", 1),
        ("veh_b", 2),
    )
    records = [
        _minimal_record(
            vehicle_name="veh_c",
            vehicle_id=2,
            visit_id=3,
            baseline_arrival_timestep=20,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.2,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
    ]
    result = _align(records, state)
    visit_keys = [item.visit_key for item in result.resolved_undetermined_visits]
    assert visit_keys == [("veh_b", 2), ("veh_a", 1), ("veh_c", 3)]


def test_resolved_order_is_independent_of_collector_input_order():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    record_a = _minimal_record(
        vehicle_name="veh_a",
        vehicle_id=0,
        visit_id=1,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.5,
        route_next_link_name="out",
    )
    record_b = _minimal_record(
        vehicle_name="veh_b",
        vehicle_id=1,
        visit_id=2,
        baseline_arrival_timestep=5,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
    )
    result_forward = _align([record_a, record_b], state)
    result_reverse = _align([record_b, record_a], state)
    assert (
        [item.visit_key for item in result_forward.resolved_undetermined_visits]
        == [item.visit_key for item in result_reverse.resolved_undetermined_visits]
    )


def test_same_arrival_timestep_uses_arrival_tiebreaker():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.9,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
    ]
    result = _align(records, state)
    visit_keys = [item.visit_key for item in result.resolved_undetermined_visits]
    assert visit_keys == [("veh_b", 2), ("veh_a", 1)]


def test_same_arrival_timestep_and_tiebreaker_uses_vehicle_id():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=5,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.5,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.5,
            route_next_link_name="out",
        ),
    ]
    result = _align(records, state)
    visit_keys = [item.visit_key for item in result.resolved_undetermined_visits]
    assert visit_keys == [("veh_b", 2), ("veh_a", 1)]


def test_b_type_with_both_arrival_fields_none_goes_to_unresolved():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_b", 2))
    record = _minimal_record(
        vehicle_name="veh_b",
        vehicle_id=1,
        visit_id=2,
        was_arrived_at_snapshot=False,
    )
    result = _align([record], state)
    assert result.resolved_undetermined_visits == ()
    assert result.unresolved_undetermined_visits == (("veh_b", 2),)


def test_unresolved_column_uses_visit_key_sort_order():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_z", 9), ("veh_a", 1), ("veh_m", 5))
    records = [
        _minimal_record(
            vehicle_name="veh_z",
            vehicle_id=3,
            visit_id=9,
            was_arrived_at_snapshot=False,
        ),
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            was_arrived_at_snapshot=False,
        ),
        _minimal_record(
            vehicle_name="veh_m",
            vehicle_id=2,
            visit_id=5,
            was_arrived_at_snapshot=False,
        ),
    ]
    result = _align(records, state)
    assert result.unresolved_undetermined_visits == (
        ("veh_a", 1),
        ("veh_m", 5),
        ("veh_z", 9),
    )


def test_a_type_with_both_arrival_fields_none_raises():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    record = _minimal_record(
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
    )
    try:
        _align([record], state)
        raise AssertionError("Expected ValueError for A-type missing arrival facts")
    except ValueError as exc:
        assert "snapshot-arrived visit" in str(exc)


def test_partial_arrival_fields_raise():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    for baseline, tiebreaker in ((10, None), (None, 0.5)):
        record = _minimal_record(
            was_arrived_at_snapshot=False,
            baseline_arrival_timestep=baseline,
            arrival_tiebreaker=tiebreaker,
            route_next_link_name="out" if baseline is not None else None,
        )
        try:
            _align([record], state)
            raise AssertionError("Expected ValueError for partial arrival state")
        except ValueError as exc:
            assert "Partial arrival state" in str(exc)


def test_confirmed_collector_visit_is_excluded_from_all_columns():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    state.confirm_visits_in_order((("veh_a", 1),))
    records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            was_arrived_at_snapshot=True,
            baseline_arrival_timestep=5,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            was_arrived_at_snapshot=False,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.2,
            route_next_link_name="out",
        ),
    ]
    result = _align(records, state)
    assert ("veh_a", 1) not in [
        item.visit_key for item in result.resolved_undetermined_visits
    ]
    assert ("veh_a", 1) not in result.unresolved_undetermined_visits
    assert ("veh_a", 1) not in result.unregistered_collector_visit_keys
    assert len(result.resolved_undetermined_visits) == 1
    assert result.resolved_undetermined_visits[0].visit_key == ("veh_b", 2)


def test_unregistered_collector_visit_goes_to_unregistered_column():
    state = _new_rank_state()
    record = _minimal_record(
        vehicle_name="veh_x",
        vehicle_id=4,
        visit_id=3,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.3,
        route_next_link_name="out",
    )
    result = _align([record], state)
    assert result.unregistered_collector_visit_keys == (("veh_x", 3),)
    assert result.resolved_undetermined_visits == ()
    assert result.unresolved_undetermined_visits == ()


def test_unregistered_column_uses_visit_key_sort_order():
    state = _new_rank_state()
    records = [
        _minimal_record(vehicle_name="veh_z", vehicle_id=3, visit_id=9),
        _minimal_record(vehicle_name="veh_a", vehicle_id=0, visit_id=1),
        _minimal_record(vehicle_name="veh_m", vehicle_id=2, visit_id=5),
    ]
    result = _align(records, state)
    assert result.unregistered_collector_visit_keys == (
        ("veh_a", 1),
        ("veh_m", 5),
        ("veh_z", 9),
    )


def test_ledger_only_visit_is_not_in_result():
    state = _new_rank_state()
    _register_undetermined(state, ("ledger_only", 1))
    result = _align([], state)
    assert result.resolved_undetermined_visits == ()
    assert result.unresolved_undetermined_visits == ()
    assert result.unregistered_collector_visit_keys == ()


def test_different_visit_ids_for_same_vehicle_are_distinct():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_a", 2))
    records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=2,
            was_arrived_at_snapshot=False,
        ),
    ]
    result = _align(records, state)
    assert [item.visit_key for item in result.resolved_undetermined_visits] == [
        ("veh_a", 1)
    ]
    assert result.unresolved_undetermined_visits == (("veh_a", 2),)


def test_duplicate_visit_key_in_collector_records_raises():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    record = _minimal_record(
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
    )
    try:
        _align([record, copy.deepcopy(record)], state)
        raise AssertionError("Expected ValueError for duplicate VisitKey")
    except ValueError as exc:
        assert "Duplicate VisitKey" in str(exc)


def test_node_name_mismatch_with_rank_state_raises():
    state = _new_rank_state("other_node")
    try:
        align_snapshot_undetermined_visits_with_node_baseline(
            node_name="merge",
            node_baseline_visit_records=[],
            node_rank_state=state,
        )
        raise AssertionError("Expected ValueError for node_name mismatch")
    except ValueError as exc:
        assert "node_name mismatch" in str(exc)


def test_invalid_vehicle_id_for_resolved_visit_raises():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    for bad_vehicle_id in (-1, "bad", 1.5):
        record = _minimal_record(
            vehicle_id=bad_vehicle_id,  # type: ignore[arg-type]
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        )
        try:
            _align([record], state)
            raise AssertionError(
                f"Expected ValueError for invalid vehicle_id {bad_vehicle_id!r}"
            )
        except ValueError as exc:
            assert "vehicle_id" in str(exc)


def test_bool_vehicle_id_for_resolved_visit_raises():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    record = _minimal_record(
        vehicle_id=True,  # type: ignore[arg-type]
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
    )
    try:
        _align([record], state)
        raise AssertionError("Expected ValueError for bool vehicle_id")
    except ValueError as exc:
        assert "vehicle_id" in str(exc)


def test_all_collector_undetermined_arrivals_resolved_property():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    all_resolved_records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            baseline_arrival_timestep=11,
            arrival_tiebreaker=0.2,
            route_next_link_name="out",
        ),
    ]
    result_all_resolved = _align(all_resolved_records, state)
    assert result_all_resolved.all_collector_undetermined_arrivals_resolved is True

    state_with_unresolved = _new_rank_state()
    _register_undetermined(state_with_unresolved, ("veh_a", 1), ("veh_b", 2))
    mixed_records = [
        all_resolved_records[0],
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            was_arrived_at_snapshot=False,
        ),
    ]
    result_mixed = _align(mixed_records, state_with_unresolved)
    assert result_mixed.all_collector_undetermined_arrivals_resolved is False


def test_has_unregistered_collector_visits_property():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    with_unregistered = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(vehicle_name="veh_x", vehicle_id=2, visit_id=3),
    ]
    result = _align(with_unregistered, state)
    assert result.has_unregistered_collector_visits is True

    state_no_unregistered = _new_rank_state()
    _register_undetermined(state_no_unregistered, ("veh_a", 1))
    result_no_unregistered = _align([with_unregistered[0]], state_no_unregistered)
    assert result_no_unregistered.has_unregistered_collector_visits is False


def test_input_list_and_record_dicts_are_not_mutated():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            was_arrived_at_snapshot=False,
        ),
    ]
    records_snapshot = copy.deepcopy(records)
    state_snapshot = _snapshot_state(state)
    _align(records, state)
    assert records == records_snapshot
    assert _snapshot_state(state) == state_snapshot


def test_rank_state_is_not_mutated():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1), ("veh_b", 2))
    records = [
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
        ),
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            was_arrived_at_snapshot=False,
        ),
    ]
    state_snapshot = _snapshot_state(state)
    _align(records, state)
    assert _snapshot_state(state) == state_snapshot


def test_result_dataclasses_are_frozen():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    record = _minimal_record(
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
    )
    result = _align([record], state)
    assert dataclasses.is_dataclass(result)
    assert result.__dataclass_params__.frozen is True
    resolved = result.resolved_undetermined_visits[0]
    assert dataclasses.is_dataclass(resolved)
    assert resolved.__dataclass_params__.frozen is True


def test_unresolved_passage_fields_do_not_block_resolved_classification():
    state = _new_rank_state()
    _register_undetermined(state, ("veh_a", 1))
    record = _minimal_record(
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.5,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )
    result = _align([record], state)
    assert len(result.resolved_undetermined_visits) == 1
    assert result.resolved_undetermined_visits[0].visit_key == ("veh_a", 1)


def _snapshot_state(state: OrderControlTvtNodeRankState) -> dict[str, object]:
    return {
        "k_confirmed": state.k_confirmed(),
        "confirmed": state.confirmed_visit_keys_in_order(),
        "undetermined": state.undetermined_visit_keys(),
    }


TESTS = [
    test_empty_collector_records_return_three_empty_columns,
    test_resolved_undetermined_visit_goes_to_resolved_column,
    test_resolved_column_uses_three_key_sort_order,
    test_resolved_order_is_independent_of_collector_input_order,
    test_same_arrival_timestep_uses_arrival_tiebreaker,
    test_same_arrival_timestep_and_tiebreaker_uses_vehicle_id,
    test_b_type_with_both_arrival_fields_none_goes_to_unresolved,
    test_unresolved_column_uses_visit_key_sort_order,
    test_a_type_with_both_arrival_fields_none_raises,
    test_partial_arrival_fields_raise,
    test_confirmed_collector_visit_is_excluded_from_all_columns,
    test_unregistered_collector_visit_goes_to_unregistered_column,
    test_unregistered_column_uses_visit_key_sort_order,
    test_ledger_only_visit_is_not_in_result,
    test_different_visit_ids_for_same_vehicle_are_distinct,
    test_duplicate_visit_key_in_collector_records_raises,
    test_node_name_mismatch_with_rank_state_raises,
    test_invalid_vehicle_id_for_resolved_visit_raises,
    test_bool_vehicle_id_for_resolved_visit_raises,
    test_all_collector_undetermined_arrivals_resolved_property,
    test_has_unregistered_collector_visits_property,
    test_input_list_and_record_dicts_are_not_mutated,
    test_rank_state_is_not_mutated,
    test_result_dataclasses_are_frozen,
    test_unresolved_passage_fields_do_not_block_resolved_classification,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT baseline alignment tests passed "
        f"({len(TESTS)} tests)."
    )
