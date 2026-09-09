# Unit tests for snapshot-plan undetermined rank-ledger registration
# (design memo §25.25.34.33).
#
# Run from the repository root:
#   python tests_order_control_tvt_snapshot_undetermined_registration.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import patch

from uxsim.order_control_baseline_snapshot import (
    OrderControlBaselineSnapshotRegistrationPlan,
    OrderControlBaselineSnapshotVisitEntry,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)
from uxsim.order_control_tvt_snapshot_undetermined_registration import (
    register_undetermined_visits_from_snapshot_plan,
)


def _new_rank_state(node_name: str) -> OrderControlTvtNodeRankState:
    return OrderControlTvtNodeRankState(node_name)


def _snapshot_rank_state(state: OrderControlTvtNodeRankState) -> dict[str, object]:
    return {
        "undetermined": state.undetermined_visit_keys(),
        "confirmed": state.confirmed_visit_keys_in_order(),
    }


def _entry(
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
) -> OrderControlBaselineSnapshotVisitEntry:
    return OrderControlBaselineSnapshotVisitEntry(
        vehicle_name=vehicle_name,
        vehicle_id=vehicle_id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=was_arrived_at_snapshot,
        baseline_arrival_timestep=baseline_arrival_timestep,
        arrival_tiebreaker=arrival_tiebreaker,
        route_next_link_name=route_next_link_name,
        baseline_passage_timestep=baseline_passage_timestep,
    )


def _plan(
    *,
    target_node_names: tuple[str, ...] = ("merge",),
    entries: tuple[OrderControlBaselineSnapshotVisitEntry, ...] = (),
    baseline_timestep_T: int = 10,
) -> OrderControlBaselineSnapshotRegistrationPlan:
    return OrderControlBaselineSnapshotRegistrationPlan(
        baseline_timestep_T=baseline_timestep_T,
        target_node_names=target_node_names,
        entries=entries,
        inlink_physical_orders=(),
    )


def _expect_value_error(test_callable, expected_substring: str) -> None:
    try:
        test_callable()
    except ValueError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected ValueError")


def test_empty_plan_returns_zero_without_mutating_rank_state():
    state = _new_rank_state("merge")
    before = _snapshot_rank_state(state)
    plan = _plan(target_node_names=("merge",), entries=())
    count = register_undetermined_visits_from_snapshot_plan(
        plan,
        {"merge": state},
    )
    assert count == 0
    assert _snapshot_rank_state(state) == before


def test_registers_unregistered_visit_as_undetermined():
    state = _new_rank_state("merge")
    plan = _plan(
        entries=(
            _entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),
        ),
    )
    count = register_undetermined_visits_from_snapshot_plan(
        plan,
        {"merge": state},
    )
    assert count == 1
    assert state.is_undetermined(("veh_a", 1))
    assert not state.is_confirmed(("veh_a", 1))


def test_registers_multiple_unregistered_visits_on_same_node_in_one_batch():
    state = _new_rank_state("merge")
    plan = _plan(
        entries=(
            _entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_b", visit_id=1, node_name="merge"),
        ),
    )
    register_call_count = 0
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def counting_register(self, visit_keys):
        nonlocal register_call_count
        register_call_count += 1
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        counting_register,
    ):
        count = register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": state},
        )
    assert count == 2
    assert register_call_count == 1
    assert state.is_undetermined(("veh_a", 1))
    assert state.is_undetermined(("veh_b", 1))


def test_registers_unregistered_visits_on_multiple_nodes():
    merge_state = _new_rank_state("merge")
    junction_state = _new_rank_state("junction")
    plan = _plan(
        target_node_names=("merge", "junction"),
        entries=(
            _entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_b", visit_id=1, node_name="junction"),
        ),
    )
    count = register_undetermined_visits_from_snapshot_plan(
        plan,
        {"merge": merge_state, "junction": junction_state},
    )
    assert count == 2
    assert merge_state.is_undetermined(("veh_a", 1))
    assert junction_state.is_undetermined(("veh_b", 1))


def test_return_value_is_total_new_registration_count_int():
    merge_state = _new_rank_state("merge")
    junction_state = _new_rank_state("junction")
    merge_state.register_undetermined_visit(("veh_existing", 1))
    plan = _plan(
        target_node_names=("merge", "junction"),
        entries=(
            _entry(vehicle_name="veh_existing", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_new_merge", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_new_junction", visit_id=1, node_name="junction"),
        ),
    )
    count = register_undetermined_visits_from_snapshot_plan(
        plan,
        {"merge": merge_state, "junction": junction_state},
    )
    assert isinstance(count, int)
    assert count == 2


def test_does_not_reregister_already_undetermined_visit():
    state = _new_rank_state("merge")
    state.register_undetermined_visit(("veh_a", 1))
    plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    count = register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert count == 0
    assert state.undetermined_visit_keys() == frozenset({("veh_a", 1)})


def test_does_not_register_already_confirmed_visit():
    state = _new_rank_state("merge")
    state.register_undetermined_visit(("veh_a", 1))
    state.confirm_visits_in_order([("veh_a", 1)])
    plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    count = register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert count == 0
    assert state.is_confirmed(("veh_a", 1))
    assert not state.is_undetermined(("veh_a", 1))


def test_registers_only_unregistered_visits_when_mixed_with_existing_states():
    state = _new_rank_state("merge")
    state.register_undetermined_visit(("veh_undetermined", 1))
    state.register_undetermined_visit(("veh_confirmed", 1))
    state.confirm_visits_in_order([("veh_confirmed", 1)])
    plan = _plan(
        entries=(
            _entry(vehicle_name="veh_undetermined", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_confirmed", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_new", visit_id=1, node_name="merge"),
        ),
    )
    count = register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert count == 1
    assert state.is_undetermined(("veh_new", 1))
    assert state.is_confirmed(("veh_confirmed", 1))


def test_skips_register_undetermined_visits_when_node_has_no_new_targets():
    state = _new_rank_state("merge")
    state.register_undetermined_visit(("veh_a", 1))
    plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    register_call_count = 0
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def counting_register(self, visit_keys):
        nonlocal register_call_count
        register_call_count += 1
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        counting_register,
    ):
        count = register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert count == 0
    assert register_call_count == 0


def test_processes_nodes_in_plan_target_node_names_order():
    merge_state = _new_rank_state("merge")
    junction_state = _new_rank_state("junction")
    plan = _plan(
        target_node_names=("junction", "merge"),
        entries=(
            _entry(vehicle_name="veh_j", visit_id=1, node_name="junction"),
            _entry(vehicle_name="veh_m", visit_id=1, node_name="merge"),
        ),
    )
    processed_node_names: list[str] = []
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def recording_register(self, visit_keys):
        processed_node_names.append(self.node_name)
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        recording_register,
    ):
        register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": merge_state, "junction": junction_state},
        )
    assert processed_node_names == ["junction", "merge"]


def test_preserves_plan_entry_order_within_each_node_registration_batch():
    state = _new_rank_state("merge")
    plan = _plan(
        entries=(
            _entry(vehicle_name="veh_b", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),
        ),
    )
    captured_visit_keys: list[OrderControlTvtVisitKey] = []
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def capturing_register(self, visit_keys):
        captured_visit_keys.extend(visit_keys)
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        capturing_register,
    ):
        register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert captured_visit_keys == [("veh_b", 1), ("veh_a", 1)]


def test_registration_order_does_not_assign_confirmed_ranks():
    state = _new_rank_state("merge")
    plan = _plan(
        entries=(
            _entry(vehicle_name="veh_b", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),
        ),
    )
    register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert state.k_confirmed() == 0
    assert state.assigned_rank(("veh_b", 1)) is None
    assert state.assigned_rank(("veh_a", 1)) is None


def test_raises_when_target_node_rank_state_is_missing():
    state = _new_rank_state("merge")
    plan = _plan(
        target_node_names=("merge", "junction"),
        entries=(_entry(node_name="merge"),),
    )
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": state},
        ),
        "Missing rank state for target node 'junction'",
    )
    assert state.undetermined_visit_keys() == frozenset()


def test_raises_when_rank_state_value_has_wrong_type():
    plan = _plan(entries=(_entry(node_name="merge"),))
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": object()},
        ),
        "OrderControlTvtNodeRankState",
    )


def test_raises_when_mapping_key_does_not_match_rank_state_node_name():
    state = _new_rank_state("junction")
    plan = _plan(entries=(_entry(node_name="merge"),))
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": state},
        ),
        "rank_states_by_node_name key 'merge' does not match rank_state.node_name 'junction'",
    )


def test_raises_when_entry_node_name_not_in_target_node_names():
    state = _new_rank_state("merge")
    plan = _plan(
        target_node_names=("merge",),
        entries=(_entry(node_name="junction"),),
    )
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": state},
        ),
        "plan entry node_name 'junction'",
    )
    assert state.undetermined_visit_keys() == frozenset()


def test_raises_when_plan_has_wrong_type():
    state = _new_rank_state("merge")
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            {"not": "a plan"},
            {"merge": state},
        ),
        "OrderControlBaselineSnapshotRegistrationPlan",
    )


def test_raises_when_rank_states_mapping_has_wrong_type():
    plan = _plan(entries=(_entry(node_name="merge"),))
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            plan,
            ["merge"],
        ),
        "rank_states_by_node_name must be a Mapping",
    )


def test_raises_before_mutating_any_node_when_later_target_has_input_error():
    merge_state = _new_rank_state("merge")
    junction_state = _new_rank_state("junction")
    merge_before = _snapshot_rank_state(merge_state)
    junction_before = _snapshot_rank_state(junction_state)
    plan = _plan(
        target_node_names=("merge", "junction"),
        entries=(
            _entry(vehicle_name="veh_merge", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_bad", visit_id=1, node_name="unknown"),
        ),
    )
    _expect_value_error(
        lambda: register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": merge_state, "junction": junction_state},
        ),
        "plan entry node_name 'unknown'",
    )
    assert _snapshot_rank_state(merge_state) == merge_before
    assert _snapshot_rank_state(junction_state) == junction_before


def test_registers_different_visit_ids_for_same_vehicle_as_distinct_visits():
    state = _new_rank_state("merge")
    plan = _plan(
        entries=(
            _entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_a", visit_id=2, node_name="merge"),
        ),
    )
    count = register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert count == 2
    assert state.is_undetermined(("veh_a", 1))
    assert state.is_undetermined(("veh_a", 2))


def test_does_not_reregister_same_visit_key_on_subsequent_plan():
    state = _new_rank_state("merge")
    first_plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    second_plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    first_count = register_undetermined_visits_from_snapshot_plan(
        first_plan,
        {"merge": state},
    )
    second_count = register_undetermined_visits_from_snapshot_plan(
        second_plan,
        {"merge": state},
    )
    assert first_count == 1
    assert second_count == 0


def test_does_not_mutate_plan():
    entry = _entry(vehicle_name="veh_a", visit_id=1, node_name="merge")
    plan = _plan(entries=(entry,))
    plan_before = dataclasses.asdict(plan)
    entry_before = dataclasses.asdict(entry)
    state = _new_rank_state("merge")
    register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert dataclasses.asdict(plan) == plan_before
    assert dataclasses.asdict(entry) == entry_before


def test_does_not_require_world_collector_or_vehicle_objects():
    state = _new_rank_state("merge")
    plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    count = register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert count == 1


def test_does_not_confirm_ranks():
    state = _new_rank_state("merge")
    plan = _plan(entries=(_entry(vehicle_name="veh_a", visit_id=1, node_name="merge"),))
    register_undetermined_visits_from_snapshot_plan(plan, {"merge": state})
    assert state.k_confirmed() == 0
    assert state.confirmed_visit_keys_in_order() == ()


def test_calls_register_undetermined_visits_at_most_once_per_node():
    merge_state = _new_rank_state("merge")
    junction_state = _new_rank_state("junction")
    plan = _plan(
        target_node_names=("merge", "junction"),
        entries=(
            _entry(vehicle_name="veh_m1", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_m2", visit_id=1, node_name="merge"),
            _entry(vehicle_name="veh_j1", visit_id=1, node_name="junction"),
        ),
    )
    per_node_call_count: dict[str, int] = {}
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def counting_register(self, visit_keys):
        per_node_call_count[self.node_name] = (
            per_node_call_count.get(self.node_name, 0) + 1
        )
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        counting_register,
    ):
        register_undetermined_visits_from_snapshot_plan(
            plan,
            {"merge": merge_state, "junction": junction_state},
        )
    assert per_node_call_count == {"merge": 1, "junction": 1}


TESTS = [
    test_empty_plan_returns_zero_without_mutating_rank_state,
    test_registers_unregistered_visit_as_undetermined,
    test_registers_multiple_unregistered_visits_on_same_node_in_one_batch,
    test_registers_unregistered_visits_on_multiple_nodes,
    test_return_value_is_total_new_registration_count_int,
    test_does_not_reregister_already_undetermined_visit,
    test_does_not_register_already_confirmed_visit,
    test_registers_only_unregistered_visits_when_mixed_with_existing_states,
    test_skips_register_undetermined_visits_when_node_has_no_new_targets,
    test_processes_nodes_in_plan_target_node_names_order,
    test_preserves_plan_entry_order_within_each_node_registration_batch,
    test_registration_order_does_not_assign_confirmed_ranks,
    test_raises_when_target_node_rank_state_is_missing,
    test_raises_when_rank_state_value_has_wrong_type,
    test_raises_when_mapping_key_does_not_match_rank_state_node_name,
    test_raises_when_entry_node_name_not_in_target_node_names,
    test_raises_when_plan_has_wrong_type,
    test_raises_when_rank_states_mapping_has_wrong_type,
    test_raises_before_mutating_any_node_when_later_target_has_input_error,
    test_registers_different_visit_ids_for_same_vehicle_as_distinct_visits,
    test_does_not_reregister_same_visit_key_on_subsequent_plan,
    test_does_not_mutate_plan,
    test_does_not_require_world_collector_or_vehicle_objects,
    test_does_not_confirm_ranks,
    test_calls_register_undetermined_visits_at_most_once_per_node,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT snapshot undetermined registration tests passed "
        f"({len(TESTS)} tests)."
    )
