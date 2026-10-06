"""Contract tests for TVT-MP Node actual rank difference (ledger + history)."""

from __future__ import annotations

import dataclasses
import inspect

import numpy as np
import pytest

import uxsim.order_control_tvt_mp_actual_passage as actual_passage_module
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualNodePassageRecord,
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageWaitEntry,
    commit_tvt_mp_actual_node_passage_history,
    prepare_tvt_mp_actual_node_passage_history,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)
from uxsim.uxsim import World


def _visit_key(vehicle_name: str, visit_id: int = 1) -> OrderControlTvtVisitKey:
    return (vehicle_name, visit_id)


def _actual_rank_change(
    assigned_rank: int,
    actual_node_passage_rank: int | None,
) -> int | None:
    if actual_node_passage_rank is None:
        return None
    return assigned_rank - actual_node_passage_rank


def _fresh_rank_state(node_name: str = "junction") -> OrderControlTvtNodeRankState:
    return OrderControlTvtNodeRankState(node_name)


def _register_and_confirm(
    rank_state: OrderControlTvtNodeRankState,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    for visit_key in visit_keys:
        rank_state.register_undetermined_visit(visit_key)
    rank_state.confirm_visits_in_order(visit_keys)


def _minimal_world(name: str) -> World:
    world = World(
        name=name,
        deltan=1,
        reaction_time=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig_a", 0, 1)
    world.addNode("orig_b", 0, -1)
    world.addNode(
        "junction",
        1,
        0,
        order_control_type="time_value",
        order_control_eligible=True,
    )
    world.addNode("dest", 2, 0)
    world.addLink(
        "in_a",
        "orig_a",
        "junction",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
        merge_priority=1,
    )
    world.addLink(
        "in_b",
        "orig_b",
        "junction",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
        merge_priority=1,
    )
    world.addLink(
        "out",
        "junction",
        "dest",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    world.T = 10
    size = world.T + 5
    for link in world.LINKS:
        if len(link.cum_arrival) == 0:
            link.cum_arrival.append(0)
            link.cum_departure.append(0)
        if len(link.traveltime_actual) <= world.T:
            link.traveltime_actual = np.zeros(size)
    return world


def _junction(world: World):
    return world.get_node("junction")


def _attach_rank_state(world: World, rank_state: OrderControlTvtNodeRankState) -> None:
    world.order_control_tvt_rank_states_by_node_name[rank_state.node_name] = rank_state


def _commit_history_passage(
    world: World,
    *,
    visit_key: OrderControlTvtVisitKey,
    vehicle_name: str,
    outlink_name: str = "out",
) -> OrderControlTvtMpActualNodePassageRecord:
    node = _junction(world)
    vehicle = world.VEHICLES_RUNNING[vehicle_name]
    outlink = world.get_link(outlink_name)
    prepared = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    commit_tvt_mp_actual_node_passage_history(prepared)
    return prepared.record


def _history_record_for_visit(
    registry: OrderControlTvtMpActualNodePassageHistoryRegistry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> OrderControlTvtMpActualNodePassageRecord | None:
    records = registry.records_by_node_name.get(node_name, ())
    for record in records:
        if record.visit_key == visit_key:
            return record
    return None


# --- assigned rank ---


def test_first_confirmed_visit_has_assigned_rank_one():
    state = _fresh_rank_state()
    key = _visit_key("v1")
    _register_and_confirm(state, (key,))
    assert state.assigned_rank(key) == 1


def test_multiple_visits_receive_continuous_assigned_ranks():
    state = _fresh_rank_state()
    keys = (_visit_key("a"), _visit_key("b"), _visit_key("c"))
    _register_and_confirm(state, keys)
    assert state.assigned_rank(keys[0]) == 1
    assert state.assigned_rank(keys[1]) == 2
    assert state.assigned_rank(keys[2]) == 3


def test_next_decision_batch_continues_after_existing_confirmed_count():
    state = _fresh_rank_state()
    first_batch = (_visit_key("old1"), _visit_key("old2"), _visit_key("old3"))
    _register_and_confirm(state, first_batch)
    assert state.k_confirmed() == 3
    second_batch = (_visit_key("new1"), _visit_key("new2"), _visit_key("new3"))
    _register_and_confirm(state, second_batch)
    assert state.assigned_rank(second_batch[0]) == 4
    assert state.assigned_rank(second_batch[1]) == 5
    assert state.assigned_rank(second_batch[2]) == 6


def test_empty_confirm_leaves_ledger_unchanged():
    state = _fresh_rank_state()
    _register_and_confirm(state, (_visit_key("keep"),))
    before = state.export_state()
    result = state.confirm_visits_in_order(())
    after = state.export_state()
    assert result.newly_confirmed_count == 0
    assert before == after


def test_duplicate_visit_key_on_confirm_is_rejected():
    state = _fresh_rank_state()
    key = _visit_key("dup")
    _register_and_confirm(state, (key,))
    state.register_undetermined_visit(_visit_key("other"))
    with pytest.raises(ValueError, match="already confirmed"):
        state.confirm_visits_in_order((key,))


def test_undetermined_visit_has_no_assigned_rank():
    state = _fresh_rank_state()
    key = _visit_key("waiting")
    state.register_undetermined_visit(key)
    assert state.assigned_rank(key) is None


def test_confirmed_list_order_matches_assigned_ranks():
    state = _fresh_rank_state()
    keys = (_visit_key("x"), _visit_key("y"))
    _register_and_confirm(state, keys)
    ordered = state.confirmed_visit_keys_in_order()
    assert ordered == keys
    for index, visit_key in enumerate(ordered, start=1):
        assert state.assigned_rank(visit_key) == index


def test_formal_route_confirm_uses_same_continuous_assigned_ranks():
    state = _fresh_rank_state()
    keys = (_visit_key("f1"), _visit_key("f2"))
    for visit_key in keys:
        state.register_undetermined_visit(visit_key)
    pairs = ((keys[0], "out"), (keys[1], "out"))
    state.confirm_visits_and_formal_target_node_routes_atomically(pairs, ["out"])
    assert state.assigned_rank(keys[0]) == 1
    assert state.assigned_rank(keys[1]) == 2


def test_rank_state_has_no_delete_confirmed_visit_api():
    public_names = {
        name
        for name in dir(OrderControlTvtNodeRankState)
        if not name.startswith("_")
    }
    for forbidden in ("remove", "delete", "unregister", "revoke"):
        assert not any(forbidden in name.lower() for name in public_names)


# --- final local rank vs assigned ---


def test_local_ranks_one_two_three_become_assigned_four_five_six_after_three_prior():
    state = _fresh_rank_state()
    _register_and_confirm(
        state,
        (_visit_key("p1"), _visit_key("p2"), _visit_key("p3")),
    )
    local_one = _visit_key("local_a")
    local_two = _visit_key("local_b")
    local_three = _visit_key("local_c")
    _register_and_confirm(state, (local_one, local_two, local_three))
    assert state.assigned_rank(local_one) == 4
    assert state.assigned_rank(local_two) == 5
    assert state.assigned_rank(local_three) == 6
    assert state.assigned_rank(local_one) != 1


# --- actual node passage rank ---


def test_node_history_starts_at_rank_one():
    world = _minimal_world("hist_one")
    state = _fresh_rank_state()
    key = _visit_key("car_a")
    _register_and_confirm(state, (key,))
    _attach_rank_state(world, state)
    world.VEHICLES_RUNNING["car_a"] = type("V", (), {"name": "car_a"})()
    record = _commit_history_passage(world, visit_key=key, vehicle_name="car_a")
    assert record.actual_node_passage_rank == 1


def test_successive_passages_use_continuous_actual_ranks():
    world = _minimal_world("hist_two")
    state = _fresh_rank_state()
    key_a = _visit_key("car_a")
    key_b = _visit_key("car_b", 2)
    _register_and_confirm(state, (key_a, key_b))
    _attach_rank_state(world, state)
    world.VEHICLES_RUNNING["car_a"] = type("V", (), {"name": "car_a"})()
    world.VEHICLES_RUNNING["car_b"] = type("V", (), {"name": "car_b"})()
    first = _commit_history_passage(world, visit_key=key_a, vehicle_name="car_a")
    second = _commit_history_passage(world, visit_key=key_b, vehicle_name="car_b")
    assert first.actual_node_passage_rank == 1
    assert second.actual_node_passage_rank == 2
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    ranks = [
        record.actual_node_passage_rank
        for record in registry.records_by_node_name["junction"]
    ]
    assert ranks == [1, 2]


def test_same_timestep_can_assign_different_actual_ranks_in_success_order():
    world = _minimal_world("same_t")
    state = _fresh_rank_state()
    key_a = _visit_key("t_a")
    key_b = _visit_key("t_b", 2)
    _register_and_confirm(state, (key_a, key_b))
    _attach_rank_state(world, state)
    world.VEHICLES_RUNNING["t_a"] = type("V", (), {"name": "t_a"})()
    world.VEHICLES_RUNNING["t_b"] = type("V", (), {"name": "t_b"})()
    first = _commit_history_passage(world, visit_key=key_a, vehicle_name="t_a")
    second = _commit_history_passage(world, visit_key=key_b, vehicle_name="t_b")
    assert first.actual_passage_timestep == second.actual_passage_timestep == world.T
    assert first.actual_node_passage_rank == 1
    assert second.actual_node_passage_rank == 2


def test_revisit_uses_distinct_visit_key():
    world = _minimal_world("revisit")
    state = _fresh_rank_state()
    first_visit = _visit_key("same_car", 1)
    second_visit = _visit_key("same_car", 2)
    _register_and_confirm(state, (first_visit, second_visit))
    _attach_rank_state(world, state)
    world.VEHICLES_RUNNING["same_car"] = type("V", (), {"name": "same_car"})()
    _commit_history_passage(world, visit_key=first_visit, vehicle_name="same_car")
    second = _commit_history_passage(
        world,
        visit_key=second_visit,
        vehicle_name="same_car",
    )
    assert second.actual_node_passage_rank == 2


def test_separate_nodes_each_start_actual_rank_at_one():
    world_a = _minimal_world("node_a_hist")
    world_b = _minimal_world("node_b_hist")
    world_b.addNode(
        "junction_b",
        3,
        0,
        order_control_type="time_value",
        order_control_eligible=True,
    )
    world_b.addLink(
        "out_b",
        "junction_b",
        "dest",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    key = _visit_key("car")
    state_a = _fresh_rank_state("junction")
    state_b = _fresh_rank_state("junction_b")
    _register_and_confirm(state_a, (key,))
    _register_and_confirm(state_b, (key,))
    _attach_rank_state(world_a, state_a)
    _attach_rank_state(world_b, state_b)
    world_a.VEHICLES_RUNNING["car"] = type("V", (), {"name": "car"})()
    world_b.VEHICLES_RUNNING["car"] = type("V", (), {"name": "car"})()
    record_a = _commit_history_passage(world_a, visit_key=key, vehicle_name="car")
    node_b = world_b.get_node("junction_b")
    out_b = world_b.get_link("out_b")
    prepared_b = prepare_tvt_mp_actual_node_passage_history(
        node=node_b,
        vehicle=world_b.VEHICLES_RUNNING["car"],
        visit_key=key,
        actual_outlink=out_b,
        actual_passage_timestep=world_b.T,
    )
    commit_tvt_mp_actual_node_passage_history(prepared_b)
    assert record_a.actual_node_passage_rank == 1
    assert prepared_b.record.actual_node_passage_rank == 1


def test_history_rejects_gap_in_actual_node_passage_rank():
    world = _minimal_world("gap")
    state = _fresh_rank_state()
    next_key = _visit_key("next")
    _register_and_confirm(state, (next_key,))
    _attach_rank_state(world, state)
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    broken = OrderControlTvtMpActualNodePassageRecord(
        _visit_key("broken"),
        world.T,
        "out",
        2,
    )
    registry.records_by_node_name["junction"] = (broken,)
    world.VEHICLES_RUNNING["next"] = type("V", (), {"name": "next"})()
    node = _junction(world)
    outlink = world.get_link("out")
    with pytest.raises(RuntimeError, match="continuous"):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=world.VEHICLES_RUNNING["next"],
            visit_key=next_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )


def test_history_rejects_duplicate_visit_key_on_same_node():
    world = _minimal_world("dup_hist")
    state = _fresh_rank_state()
    key = _visit_key("once")
    _register_and_confirm(state, (key,))
    _attach_rank_state(world, state)
    world.VEHICLES_RUNNING["once"] = type("V", (), {"name": "once"})()
    _commit_history_passage(world, visit_key=key, vehicle_name="once")
    with pytest.raises(RuntimeError, match="already"):
        _commit_history_passage(world, visit_key=key, vehicle_name="once")


def test_unpassed_visit_has_no_history_record():
    world = _minimal_world("no_hist")
    state = _fresh_rank_state()
    key = _visit_key("never")
    _register_and_confirm(state, (key,))
    _attach_rank_state(world, state)
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    assert _history_record_for_visit(registry, "junction", key) is None


# --- rank difference ---


def test_rank_difference_zero_when_assigned_equals_actual():
    assert _actual_rank_change(4, 4) == 0


def test_rank_difference_positive_when_actual_is_smaller_than_assigned():
    assert _actual_rank_change(5, 4) == 1
    assert _actual_rank_change(6, 5) == 1


def test_rank_difference_negative_when_actual_is_larger_than_assigned():
    assert _actual_rank_change(4, 6) == -2


def test_rank_difference_none_without_actual_record():
    assert _actual_rank_change(4, None) is None


def test_unpassed_visit_difference_is_none_not_zero():
    assigned = 4
    actual = None
    difference = _actual_rank_change(assigned, actual)
    assert difference is None
    assert difference != 0


def test_documented_abc_skip_pattern_without_renumbering():
    state = _fresh_rank_state()
    key_a = _visit_key("A")
    key_b = _visit_key("B", 2)
    key_c = _visit_key("C", 3)
    _register_and_confirm(state, (key_a, key_b, key_c))
    assigned_a = state.assigned_rank(key_a)
    assigned_b = state.assigned_rank(key_b)
    assigned_c = state.assigned_rank(key_c)
    assert assigned_a == 1
    assert assigned_b == 2
    assert assigned_c == 3
    actual_b = 1
    actual_c = 2
    assert _actual_rank_change(assigned_a, None) is None
    assert _actual_rank_change(assigned_b, actual_b) == 1
    assert _actual_rank_change(assigned_c, actual_c) == 1
    assert state.assigned_rank(key_a) == 1


def test_observed_only_subset_does_not_use_relative_ranks_one_two():
    actual_ranks_observed = [4, 5]
    assert actual_ranks_observed != [1, 2]


def test_route_mismatch_does_not_change_rank_difference_formula():
    assigned = 5
    actual = 4
    difference = _actual_rank_change(assigned, actual)
    assert difference == 1
    formal_route = "link_formal"
    actual_route = "link_other"
    assert formal_route != actual_route
    assert difference == assigned - actual


# --- role / partition (labels only) ---


def test_same_node_ledger_accepts_buyer_seller_and_nonparticipating_labels():
    state = _fresh_rank_state()
    buyer = _visit_key("buyer_role")
    seller = _visit_key("seller_role", 2)
    watcher = _visit_key("np_role", 3)
    _register_and_confirm(state, (buyer, seller, watcher))
    assert state.assigned_rank(buyer) == 1
    assert state.assigned_rank(seller) == 2
    assert state.assigned_rank(watcher) == 3


def test_partition_four_style_visit_without_wait_entry_still_has_assigned_rank():
    state = _fresh_rank_state()
    outside = _visit_key("partition_four_style")
    _register_and_confirm(state, (outside,))
    assert state.is_confirmed(outside)
    assert state.assigned_rank(outside) == 1


def test_fallback_style_visit_without_wait_entry_still_has_assigned_rank():
    state = _fresh_rank_state()
    fallback = _visit_key("fallback_style")
    _register_and_confirm(state, (fallback,))
    assert state.assigned_rank(fallback) == 1


def test_no_visits_style_empty_confirm_adds_no_new_assigned_ranks():
    state = _fresh_rank_state()
    _register_and_confirm(state, (_visit_key("prior"),))
    before = state.k_confirmed()
    state.confirm_visits_in_order(())
    assert state.k_confirmed() == before


# --- skip / unpassed ---


def test_later_assigned_visit_can_have_actual_history_while_earlier_stays_none():
    world = _minimal_world("skip_pattern")
    state = _fresh_rank_state()
    key_early = _visit_key("early")
    key_late = _visit_key("late", 2)
    _register_and_confirm(state, (key_early, key_late))
    _attach_rank_state(world, state)
    world.VEHICLES_RUNNING["late"] = type("V", (), {"name": "late"})()
    record = _commit_history_passage(world, visit_key=key_late, vehicle_name="late")
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    assert state.assigned_rank(key_early) == 1
    assert state.assigned_rank(key_late) == 2
    assert _history_record_for_visit(registry, "junction", key_early) is None
    assert record.actual_node_passage_rank == 1
    assert _actual_rank_change(state.assigned_rank(key_early), None) is None
    assert _actual_rank_change(state.assigned_rank(key_late), 1) == 1


# --- absence of new APIs / fields ---


def test_actual_passage_module_has_no_rank_difference_result_type():
    forbidden = (
        "OrderControlTvtMpNodeActualRankDifferenceResult",
        "OrderControlTvtMpRankComparisonResult",
        "OrderControlTvtMpRankComparisonEvaluationStatus",
        "OrderControlTvtMpRankComparisonEvaluationReason",
    )
    for name in forbidden:
        assert not hasattr(actual_passage_module, name)


def test_actual_passage_module_has_no_rank_difference_prepare_or_commit():
    source = inspect.getsource(actual_passage_module)
    for fragment in (
        "prepare_tvt_mp_node_actual_rank_difference",
        "commit_tvt_mp_node_actual_rank_difference",
        "prepare_tvt_mp_rank_comparison",
        "commit_tvt_mp_rank_comparison",
    ):
        assert fragment not in source


def test_observation_record_has_no_rank_difference_fields():
    names = {field.name for field in dataclasses.fields(
        OrderControlTvtMpActualPassageObservationRecord
    )}
    for forbidden in (
        "actual_rank_change",
        "assigned_rank",
        "actual_node_passage_rank",
        "rank_difference",
    ):
        assert forbidden not in names


def test_wait_entry_has_no_rank_result_field():
    names = {field.name for field in dataclasses.fields(
        OrderControlTvtMpActualPassageWaitEntry
    )}
    for forbidden in (
        "actual_rank_change",
        "rank_comparison",
        "assigned_rank",
    ):
        assert forbidden not in names


def test_node_passage_record_has_no_assigned_rank_copy_field():
    names = {field.name for field in dataclasses.fields(
        OrderControlTvtMpActualNodePassageRecord
    )}
    assert "assigned_rank" not in names
    assert "actual_rank_change" not in names
