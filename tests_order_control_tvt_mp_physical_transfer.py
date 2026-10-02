"""
Tests for TVT-MP confirmed-rank physical passage.

Run from the repository root:
    python tests_order_control_tvt_mp_physical_transfer.py
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import numpy as np

import uxsim.order_control_tvt_mp_physical_transfer as physical_transfer
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import run_snapshot_fixed_baseline_fork
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import Node, World
from tests_order_control_baseline_driver import _build_time_value_junction_world


def _world(
    name,
    *,
    order_control_type="time_value",
    order_control_eligible=True,
    flow_capacity=None,
    hard_deterministic_mode=False,
    signal=None,
):
    world = World(
        name=name,
        deltan=1,
        reaction_time=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=hard_deterministic_mode,
    )
    world.addNode("orig_a", 0, 1)
    world.addNode("orig_b", 0, -1)
    node_kwargs = {
        "order_control_type": order_control_type,
        "order_control_eligible": order_control_eligible,
        "flow_capacity": flow_capacity,
    }
    if signal is not None:
        node_kwargs["signal"] = signal
    world.addNode("junction", 1, 0, **node_kwargs)
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
    world.addLink(
        "side",
        "orig_a",
        "dest",
        length=50,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    world.T = 10
    _prepare_logs(world)
    return world


def _prepare_logs(world):
    size = world.T + 5
    for link in world.LINKS:
        if len(link.cum_arrival) == 0:
            link.cum_arrival.append(0)
            link.cum_departure.append(0)
        if len(link.traveltime_actual) <= world.T:
            link.traveltime_actual = np.zeros(size)


def _junction(world):
    return world.get_node("junction")


def _place(
    world,
    vehicle_name,
    inlink_name,
    *,
    visit_id,
    outlink_name="out",
    behind=False,
    state="run",
    route_next_link="unset",
    waiting=False,
    in_incoming=True,
):
    """Place one research vehicle at the end of an inlink.

    behind=True keeps an earlier vehicle as the physical head, so this
    vehicle is not inlink.vehicles[0].
    """
    inlink = world.get_link(inlink_name)
    junction = _junction(world)
    vehicle = world.addVehicle(inlink.start_node.name, "dest", 0, name=vehicle_name)
    vehicle.state = state
    vehicle.link = inlink
    vehicle.x = inlink.length
    vehicle.x_old = inlink.length
    vehicle.link_arrival_time = 0
    vehicle.move_remain = 0
    vehicle.v = 0
    vehicle.payment_paid = 3
    vehicle.payment_received = 4
    if route_next_link == "unset":
        vehicle.route_next_link = world.get_link(outlink_name)
    else:
        vehicle.route_next_link = route_next_link
    vehicle.order_control_visit_id = visit_id
    vehicle.order_control_current_visit = {
        "visit_id": visit_id,
        "node": junction,
        "inlink": inlink,
        "earliest_arrival_timestep": 0,
        "arrival_time": 0.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": None,
    }
    if behind:
        blocker = world.addVehicle("orig_a", "dest", 0, name=vehicle_name + "_blocker")
        blocker.state = "run"
        blocker.link = inlink
        blocker.x = inlink.length
        blocker.x_old = inlink.length
        inlink.vehicles.append(blocker)
    inlink.vehicles.append(vehicle)
    if waiting:
        vehicle.flag_waiting_for_trip_end = 1
    if in_incoming:
        junction.incoming_vehicles.append(vehicle)
    world.VEHICLES_RUNNING[vehicle.name] = vehicle
    return vehicle


def _confirm(world, vehicles_in_rank_order, *, formal_outlink_name=None):
    junction = _junction(world)
    rank_state = OrderControlTvtNodeRankState(junction.name)
    visit_keys = []
    for vehicle in vehicles_in_rank_order:
        current_visit = vehicle.order_control_current_visit
        visit_key = (vehicle.name, current_visit["visit_id"])
        rank_state.register_undetermined_visit(visit_key)
        visit_keys.append(visit_key)
    if formal_outlink_name is None:
        if len(visit_keys) > 0:
            rank_state.confirm_visits_in_order(visit_keys)
    else:
        pairs = []
        for visit_key in visit_keys:
            pairs.append((visit_key, formal_outlink_name))
        rank_state.confirm_visits_and_formal_target_node_routes_atomically(
            pairs,
            ["out", formal_outlink_name],
        )
    world.order_control_tvt_rank_states_by_node_name[junction.name] = rank_state
    return rank_state


def _register_only(world, vehicles):
    junction = _junction(world)
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(junction.name)
    if rank_state is None:
        rank_state = OrderControlTvtNodeRankState(junction.name)
        world.order_control_tvt_rank_states_by_node_name[junction.name] = rank_state
    for vehicle in vehicles:
        current_visit = vehicle.order_control_current_visit
        visit_key = (vehicle.name, current_visit["visit_id"])
        if not rank_state.is_confirmed(visit_key) and not rank_state.is_undetermined(visit_key):
            rank_state.register_undetermined_visit(visit_key)
    return rank_state


def _as_fork(world, *, apply_copied_tvt_confirmed_ranks=True):
    # Existing fork fixtures reproduce a TVT rank-applying baseline fork.
    # A generic baseline fork passes False explicitly.
    world._order_control_baseline_collector = OrderControlBaselineCollector(
        apply_copied_tvt_confirmed_ranks=apply_copied_tvt_confirmed_ranks,
    )
    return world._order_control_baseline_collector


def _expect_runtime_error(function):
    try:
        function()
    except RuntimeError as error:
        return error
    raise AssertionError("Expected RuntimeError")


def test_time_value_branch_is_only_for_eligible_time_value():
    # order_control_type none uses ordinary merge and does not need a ledger.
    plain = _world("branch_plain", order_control_type="none", order_control_eligible=False)
    plain_vehicle = _place(plain, "plain_car", "in_a", visit_id=1)
    _junction(plain).transfer()
    assert plain_vehicle.link.name == "out"

    # eligible must be bool True. A truthy non-bool does not enter TVT.
    truthy = _world("branch_truthy")
    _junction(truthy).order_control_eligible = 1
    truthy_vehicle = _place(truthy, "truthy_car", "in_a", visit_id=1)
    _junction(truthy).transfer()
    assert truthy_vehicle.link.name == "out"

    ineligible = _world("branch_ineligible")
    _junction(ineligible).order_control_eligible = False
    ineligible_vehicle = _place(ineligible, "ineligible_car", "in_a", visit_id=1)
    _junction(ineligible).transfer()
    assert ineligible_vehicle.link.name == "out"

    missing_ledger = _world("branch_tvt")
    _place(missing_ledger, "tvt_car", "in_a", visit_id=1)
    error = _expect_runtime_error(_junction(missing_ledger).transfer)
    assert "junction" in str(error)


def test_candidates_are_only_current_incoming_vehicles():
    world = _world("incoming_only")
    waiting_outside = _place(
        world,
        "outside_car",
        "in_b",
        visit_id=2,
        in_incoming=False,
    )
    arrived = _place(world, "arrived_car", "in_a", visit_id=1)
    _junction(world).incoming_vehicles.append(arrived)
    _confirm(world, [arrived, waiting_outside])
    _junction(world).transfer()
    assert arrived.link.name == "out"
    assert waiting_outside.link.name == "in_b"
    assert len(world.get_link("out").vehicles) == 1


def test_does_not_retry_passed_or_unarrived_visits():
    world = _world("no_retry")
    vehicle = _place(world, "once_car", "in_a", visit_id=1)
    unarrived = _place(world, "later_car", "in_b", visit_id=2, in_incoming=False)
    _confirm(world, [vehicle, unarrived])
    junction = _junction(world)
    junction.transfer()
    assert vehicle.link.name == "out"
    out_count = len(world.get_link("out").vehicles)
    junction.transfer()
    assert vehicle.link.name == "out"
    assert unarrived.link.name == "in_b"
    assert len(world.get_link("out").vehicles) == out_count


def test_attempts_follow_assigned_rank_not_baseline_order():
    world = _world("rank_order", flow_capacity=1)
    later_rank = _place(world, "later_rank", "in_a", visit_id=1)
    first_rank = _place(world, "first_rank", "in_b", visit_id=2)
    junction = _junction(world)
    # Incoming order is the opposite of assigned_rank.
    junction.incoming_vehicles = [later_rank, first_rank]
    _confirm(world, [first_rank, later_rank])
    junction.transfer()
    assert first_rank.link.name == "out"
    assert later_rank.link.name == "in_a"


def test_nonparticipant_attempts_in_confirmed_rank():
    world = _world("nonparticipant")
    vehicle = _place(world, "nonparticipant_car", "in_a", visit_id=1)
    vehicle.participates_in_order_exchange = False
    _confirm(world, [vehicle])
    _junction(world).transfer()
    assert vehicle.link.name == "out"
    assert vehicle.participates_in_order_exchange is False


def test_passage_uses_live_route_next_link_without_rewriting_ledger_or_payments():
    world = _world("live_route")
    vehicle = _place(world, "live_car", "in_a", visit_id=1)
    rank_state = _confirm(world, [vehicle], formal_outlink_name="out_formal")
    visit_key = (vehicle.name, 1)
    live_link = vehicle.route_next_link
    _junction(world).transfer()
    assert vehicle.link is live_link
    assert vehicle.route_next_link is live_link
    assert rank_state.formal_route_next_link_name(visit_key) == "out_formal"
    assert vehicle.payment_paid == 3
    assert vehicle.payment_received == 4
    assert rank_state.assigned_rank(visit_key) == 1


def test_temporary_skip_tries_the_next_rank():
    # Not the physical head: the next rank still passes.
    world = _world("skip_not_head")
    blocked = _place(world, "blocked_head", "in_a", visit_id=1, behind=True)
    follower = _place(world, "next_head", "in_b", visit_id=2)
    _confirm(world, [blocked, follower])
    _junction(world).transfer()
    assert blocked.link.name == "in_a"
    assert follower.link.name == "out"

    # The inlink deque is empty, so this rank is skipped and the next passes.
    empty_world = _world("skip_empty_inlink")
    missing_head = _place(empty_world, "missing_head", "in_a", visit_id=1)
    empty_world.get_link("in_a").vehicles.clear()
    next_after_empty = _place(empty_world, "next_after_empty", "in_b", visit_id=2)
    _confirm(empty_world, [missing_head, next_after_empty])
    _junction(empty_world).transfer()
    assert missing_head.link.name == "in_a"
    assert next_after_empty.link.name == "out"

    # Shared node flow is zero. Both ranks are skipped, and that is not an error.
    flow_world = _world("skip_flow", flow_capacity=1)
    flow_world.get_node("junction").flow_capacity_remain = 0
    flow_first = _place(flow_world, "flow_first", "in_a", visit_id=1)
    flow_second = _place(flow_world, "flow_second", "in_b", visit_id=2)
    _confirm(flow_world, [flow_first, flow_second])
    _junction(flow_world).transfer()
    assert flow_first.link.name == "in_a"
    assert flow_second.link.name == "in_b"

    # Inlink outflow is short only for the first rank.
    out_world = _world("skip_out_capacity")
    starved = _place(out_world, "starved", "in_a", visit_id=1)
    ready = _place(out_world, "ready_out", "in_b", visit_id=2)
    out_world.get_link("in_a").capacity_out_remain = 0
    _confirm(out_world, [starved, ready])
    _junction(out_world).transfer()
    assert starved.link.name == "in_a"
    assert ready.link.name == "out"

    # Outlink inflow is short only for the first rank's outlink.
    in_world = _world("skip_in_capacity")
    in_world.addNode("dest_b", 2, 1)
    in_world.addLink(
        "out_b",
        "junction",
        "dest_b",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    blocked_out = _place(in_world, "blocked_out", "in_a", visit_id=1, outlink_name="out")
    other_out = _place(in_world, "other_out", "in_b", visit_id=2, outlink_name="out_b")
    in_world.get_link("out").capacity_in_remain = 0
    _confirm(in_world, [blocked_out, other_out])
    _prepare_logs(in_world)
    _junction(in_world).transfer()
    assert blocked_out.link.name == "in_a"
    assert other_out.link.name == "out_b"

    # Entry space is closed only on the first rank's outlink.
    space_world = _world("skip_entry")
    space_world.addNode("dest_c", 2, -1)
    space_world.addLink(
        "out_c",
        "junction",
        "dest_c",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    parked = space_world.addVehicle("orig_a", "dest", 0, name="parked")
    parked.state = "run"
    parked.link = space_world.get_link("out")
    parked.x = 0
    parked.x_old = 0
    space_world.get_link("out").vehicles.append(parked)
    no_room = _place(space_world, "no_room", "in_a", visit_id=1, outlink_name="out")
    has_room = _place(space_world, "has_room", "in_b", visit_id=2, outlink_name="out_c")
    _confirm(space_world, [no_room, has_room])
    _prepare_logs(space_world)
    _junction(space_world).transfer()
    assert no_room.link.name == "in_a"
    assert has_room.link.name == "out_c"


def test_clearance_ends_the_timestep_and_the_next_timestep_retries():
    world = _world("clearance_stop_retry")
    world.order_control_clearance_timesteps = 1
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 1
    first = _place(world, "clear_first", "in_a", visit_id=1)
    second = _place(world, "clear_second", "in_b", visit_id=2)
    _confirm(world, [first, second])
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = world.T
    junction.transfer()
    assert first.link.name == "in_a"
    assert second.link.name == "in_b"

    world.T = 12
    junction.incoming_vehicles = [first, second]
    junction.transfer()
    assert first.link.name == "out"
    assert second.link.name == "in_b"


def test_clearance_zero_allows_different_inlink_only_from_next_timestep():
    world = _world("clearance_zero")
    world.order_control_clearance_timesteps = 0
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 0
    vehicle = _place(world, "zero_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = world.T
    junction.transfer()
    assert vehicle.link.name == "in_a"
    world.T = world.T + 1
    junction.incoming_vehicles = [vehicle]
    junction.transfer()
    assert vehicle.link.name == "out"


def test_clearance_one_requires_one_full_empty_timestep():
    world = _world("clearance_one")
    world.order_control_clearance_timesteps = 1
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 1
    vehicle = _place(world, "one_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = 10
    world.T = 11
    junction.transfer()
    assert vehicle.link.name == "in_a"
    world.T = 12
    junction.incoming_vehicles = [vehicle]
    junction.transfer()
    assert vehicle.link.name == "out"


def test_finish_runs_once_and_ends_waiting_trips():
    world = _world("finish_waiting")
    passer = _place(world, "passer", "in_a", visit_id=1)
    waiting = _place(world, "waiting_car", "in_b", visit_id=2, waiting=True)
    _confirm(world, [passer])
    junction = _junction(world)
    junction.transfer()
    assert passer.link.name == "out"
    assert waiting.state == "end"
    assert junction.incoming_vehicles == []

    broken = _world("finish_not_on_error")
    stuck = _place(broken, "stuck", "in_a", visit_id=1)
    stuck.order_control_current_visit = None
    _confirm_without_visit = OrderControlTvtNodeRankState("junction")
    broken.order_control_tvt_rank_states_by_node_name["junction"] = _confirm_without_visit
    error = _expect_runtime_error(_junction(broken).transfer)
    assert "stuck" in str(error)
    assert stuck in _junction(broken).incoming_vehicles


def test_broken_current_visit_or_unconfirmed_on_real_world_raises():
    missing = _world("broken_missing")
    missing_vehicle = _place(missing, "missing_car", "in_a", visit_id=1)
    missing_vehicle.order_control_current_visit = None
    missing.order_control_tvt_rank_states_by_node_name["junction"] = (
        OrderControlTvtNodeRankState("junction")
    )
    error = _expect_runtime_error(_junction(missing).transfer)
    assert "junction" in str(error)
    assert "missing_car" in str(error)

    mismatch = _world("broken_mismatch")
    mismatch_vehicle = _place(mismatch, "mismatch_car", "in_a", visit_id=1)
    mismatch_vehicle.order_control_current_visit["inlink"] = mismatch.get_link("in_b")
    _confirm(mismatch, [mismatch_vehicle])
    error = _expect_runtime_error(_junction(mismatch).transfer)
    assert "mismatch_car" in str(error)

    unconfirmed = _world("broken_unconfirmed")
    loose = _place(unconfirmed, "loose_car", "in_a", visit_id=1)
    _register_only(unconfirmed, [loose])
    error = _expect_runtime_error(_junction(unconfirmed).transfer)
    assert "loose_car" in str(error)
    assert loose.link.name == "in_a"

    # Capacity shortage is a temporary skip, not RuntimeError.
    starved = _world("not_an_error_capacity")
    held = _place(starved, "held_car", "in_a", visit_id=1)
    starved.get_link("in_a").capacity_out_remain = 0
    _confirm(starved, [held])
    _junction(starved).transfer()
    assert held.link.name == "in_a"

    one_sided = _world("one_sided_history")
    waiting_car = _place(one_sided, "history_car", "in_a", visit_id=1)
    _confirm(one_sided, [waiting_car])
    junction = _junction(one_sided)
    junction.last_order_control_inlink = one_sided.get_link("side")
    junction.last_order_control_entry_timestep = None
    error = _expect_runtime_error(junction.transfer)
    assert "history_car" in str(error)


def test_fork_ledger_stays_at_pre_decision_confirms():
    world = _world("fork_ledger")
    old_vehicle = _place(world, "old_car", "in_a", visit_id=1)
    new_vehicle = _place(world, "new_car", "in_b", visit_id=2)
    _confirm(world, [old_vehicle])
    _register_only(world, [new_vehicle])
    fork = world.copy()
    real_state = world.order_control_tvt_rank_states_by_node_name["junction"]
    real_state.confirm_visits_in_order([("new_car", 2)])
    fork_state = fork.order_control_tvt_rank_states_by_node_name["junction"]
    assert fork_state.is_confirmed(("new_car", 2)) is False
    assert real_state.is_confirmed(("new_car", 2)) is True
    _as_fork(fork)
    fork.get_node("junction").flow_capacity = 1
    fork.get_node("junction").flow_capacity_remain = 1
    fork.get_node("junction").transfer()
    fork_old = None
    fork_new = None
    for vehicle in fork.VEHICLES.values():
        if vehicle.name == "old_car":
            fork_old = vehicle
        if vehicle.name == "new_car":
            fork_new = vehicle
    assert fork_old.link.name == "out"
    assert fork_new.link.name == "in_b"


def test_fork_tries_past_confirmed_before_ordinary_group():
    world = _world("fork_order", flow_capacity=1)
    confirmed = _place(world, "confirmed_car", "in_b", visit_id=1)
    ordinary = _place(world, "ordinary_car", "in_a", visit_id=2)
    junction = _junction(world)
    junction.incoming_vehicles = [ordinary, confirmed]
    _confirm(world, [confirmed])
    _register_only(world, [ordinary])
    _as_fork(world)
    junction.transfer()
    assert confirmed.link.name == "out"
    assert ordinary.link.name == "in_a"


def test_skipped_past_confirmed_vehicle_is_excluded_from_ordinary_merge():
    world = _world("fork_exclude_skip")
    skipped = _place(world, "skipped_confirmed", "in_a", visit_id=1, behind=True)
    ordinary = _place(world, "ordinary_passes", "in_b", visit_id=2)
    _confirm(world, [skipped])
    _register_only(world, [ordinary])
    _as_fork(world)
    seen = []
    original = Node._transfer_normal_merge

    def spy(node, allowed_vehicles=None, enforce_order_control_clearance=False):
        seen.append(allowed_vehicles)
        return original(node, allowed_vehicles, enforce_order_control_clearance)

    with patch.object(Node, "_transfer_normal_merge", spy):
        _junction(world).transfer()
    assert len(seen) == 1
    assert skipped not in seen[0]
    assert ordinary in seen[0]
    assert skipped.link.name == "in_a"
    assert ordinary.link.name == "out"


def test_clearance_stop_skips_ordinary_group():
    world = _world("fork_clearance_stops_ordinary")
    confirmed = _place(world, "confirmed_wait", "in_a", visit_id=1)
    ordinary = _place(world, "ordinary_wait", "in_b", visit_id=2)
    _confirm(world, [confirmed])
    _register_only(world, [ordinary])
    _as_fork(world)
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 0
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = world.T
    seen = []
    original = Node._transfer_normal_merge

    def spy(node, allowed_vehicles=None, enforce_order_control_clearance=False):
        seen.append(allowed_vehicles)
        return original(node, allowed_vehicles, enforce_order_control_clearance)

    with patch.object(Node, "_transfer_normal_merge", spy):
        junction.transfer()
    assert seen == []
    assert confirmed.link.name == "in_a"
    assert ordinary.link.name == "in_b"


def test_ordinary_group_keeps_merge_priority_and_hard_deterministic_choice():
    world = _world("fork_priority", hard_deterministic_mode=True, flow_capacity=1)
    low = _place(world, "low_priority", "in_a", visit_id=1)
    high = _place(world, "high_priority", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 5
    _register_only(world, [low, high])
    _as_fork(world)
    _junction(world).transfer()
    assert high.link.name == "out"
    assert low.link.name == "in_a"


def test_ordinary_group_sees_capacity_after_past_confirmed_passage():
    # Same inlink: after the confirmed head leaves, the ordinary follower is
    # the new head and can use the remaining node flow in this timestep.
    world = _world("fork_remaining_capacity", flow_capacity=2)
    # Two lanes so the vehicle that just entered does not close the entrance.
    # Link capacities are raised so the binding limit is the node flow of 2.
    world.get_link("out").number_of_lanes = 2
    world.get_link("out").capacity_in_remain = 10
    world.get_link("in_a").capacity_out_remain = 10
    confirmed = _place(world, "confirmed_head", "in_a", visit_id=1)
    ordinary = _place(world, "ordinary_follower", "in_a", visit_id=2)
    _confirm(world, [confirmed])
    _register_only(world, [ordinary])
    _as_fork(world)
    _junction(world).transfer()
    assert confirmed.link.name == "out"
    assert ordinary.link.name == "out"


def test_ordinary_group_stops_on_unmet_order_control_clearance():
    world = _world("ordinary_clearance_stop", hard_deterministic_mode=True)
    first = _place(world, "ordinary_first", "in_a", visit_id=1)
    second = _place(world, "ordinary_second", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 1
    _register_only(world, [first, second])
    _as_fork(world)
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 0
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = world.T
    junction.transfer()
    assert first.link.name == "in_a"
    assert second.link.name == "in_b"
    assert junction.last_order_control_inlink is world.get_link("side")


def test_ordinary_passage_updates_order_control_clearance_history():
    world = _world("ordinary_history")
    vehicle = _place(world, "ordinary_moves", "in_a", visit_id=1)
    _register_only(world, [vehicle])
    _as_fork(world)
    junction = _junction(world)
    junction.transfer()
    assert vehicle.link.name == "out"
    assert junction.last_order_control_inlink is world.get_link("in_a")
    assert junction.last_order_control_entry_timestep == world.T


def test_same_inlink_ordinary_group_needs_no_extra_clearance_wait():
    world = _world("same_inlink_ordinary")
    vehicle = _place(world, "same_inlink_car", "in_a", visit_id=1)
    _register_only(world, [vehicle])
    _as_fork(world)
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 5
    junction.last_order_control_inlink = world.get_link("in_a")
    junction.last_order_control_entry_timestep = world.T
    junction.transfer()
    assert vehicle.link.name == "out"


def test_different_inlink_after_passage_does_not_pass_in_the_same_timestep():
    confirmed_world = _world("different_after_confirmed")
    confirmed = _place(confirmed_world, "past_car", "in_a", visit_id=1)
    ordinary = _place(confirmed_world, "other_inlink_car", "in_b", visit_id=2)
    _confirm(confirmed_world, [confirmed])
    _register_only(confirmed_world, [ordinary])
    _as_fork(confirmed_world)
    confirmed_world.order_control_clearance_timesteps = 0
    _junction(confirmed_world).order_control_clearance_timesteps = 0
    _junction(confirmed_world).transfer()
    assert confirmed.link.name == "out"
    assert ordinary.link.name == "in_b"

    ordinary_world = _world(
        "different_after_ordinary",
        hard_deterministic_mode=True,
    )
    winner = _place(ordinary_world, "winner", "in_b", visit_id=1)
    loser = _place(ordinary_world, "loser", "in_a", visit_id=2)
    ordinary_world.get_link("in_b").merge_priority = 5
    ordinary_world.get_link("in_a").merge_priority = 1
    _register_only(ordinary_world, [winner, loser])
    _as_fork(ordinary_world)
    ordinary_world.order_control_clearance_timesteps = 0
    _junction(ordinary_world).order_control_clearance_timesteps = 0
    _junction(ordinary_world).transfer()
    assert winner.link.name == "out"
    assert loser.link.name == "in_a"


def test_ordinary_signal_node_does_not_update_order_control_clearance_history():
    world = _world(
        "signal_node",
        order_control_type="none",
        order_control_eligible=False,
        signal=[60, 5, 60],
    )
    vehicle = _place(world, "signal_car", "in_a", visit_id=1)
    world.get_link("in_a").signal_group = [0]
    junction = _junction(world)
    signal_before = list(junction.signal)
    junction.transfer()
    assert vehicle.link.name == "out"
    assert junction.last_order_control_inlink is None
    assert junction.last_order_control_entry_timestep is None
    assert list(junction.signal) == signal_before

    blocked = _world(
        "signal_blocked",
        order_control_type="none",
        order_control_eligible=False,
        signal=[60, 60],
    )
    held = _place(blocked, "held_signal", "in_a", visit_id=1)
    blocked.get_link("in_a").signal_group = [1]
    blocked_junction = _junction(blocked)
    blocked_junction.transfer()
    assert held.link.name == "in_a"
    assert blocked_junction.last_order_control_inlink is None


def test_collector_prepare_and_apply_once_per_passage():
    world = _world("collector_once")
    vehicle = _place(world, "recorded_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    collector = _as_fork(world)
    # Fork rule would treat an unconfirmed vehicle as ordinary. This visit
    # is confirmed, so the confirmed scan records the passage.
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle.id,
        node_name="junction",
        inlink_name="in_a",
        visit_id=1,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
        baseline_passage_timestep=None,
    )
    _junction(world).transfer()
    snapshot = collector.get_baseline_visit_snapshot(vehicle.name, 1)
    assert snapshot["baseline_passage_timestep"] == world.T
    _junction(world).transfer()
    again = collector.get_baseline_visit_snapshot(vehicle.name, 1)
    assert again["baseline_passage_timestep"] == world.T


def test_transfer_does_not_call_downstream_observer():
    world = _world("no_observer_call")
    vehicle = _place(world, "observer_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])

    class Spy:
        def __init__(self):
            self.calls = []

        def capture_before_transfer(self, node):
            self.calls.append("capture")
            return False

        def commit_after_transfer(self, node):
            self.calls.append("commit")

        def clear_pending(self):
            self.calls.append("clear")

    spy = Spy()
    world._order_control_baseline_downstream_boundary_observer = spy
    _junction(world).transfer()
    assert spy.calls == []
    assert vehicle.link.name == "out"


def test_zero_visits_skip_forward_and_fork_does_not_terminate():
    world = _build_time_value_junction_world(name="physical_zero_visits", tmax=300)
    world.T = 9
    world.order_control_tvt_evaluation_end_timestep = 9
    copied = []
    original_copy = World.copy

    def capture_copy(real_world):
        fork = original_copy(real_world)
        copied.append(fork)
        return fork

    with patch.object(World, "copy", capture_copy):
        result = run_snapshot_fixed_baseline_fork(
            world,
            target_node_names=["junction"],
            baseline_horizon_steps=50,
        )
    assert result.fork_steps_executed == 0
    assert result.final_fork_timestep == 9
    assert copied[0].order_control_tvt_evaluation_end_timestep is None
    assert world.order_control_tvt_evaluation_end_timestep == 9


def test_ordinary_node_merge_is_unchanged():
    world = _world(
        "ordinary_merge",
        order_control_type="none",
        order_control_eligible=False,
        hard_deterministic_mode=True,
        flow_capacity=1,
    )
    low = _place(world, "ordinary_low", "in_a", visit_id=1)
    high = _place(world, "ordinary_high", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 4
    junction = _junction(world)
    junction.transfer()
    assert high.link.name == "out"
    assert low.link.name == "in_a"
    assert junction.last_order_control_inlink is None
    assert junction.last_order_control_entry_timestep is None


def test_fcfs_and_batch_return_before_tvt():
    source = inspect.getsource(Node.transfer)
    fcfs_at = source.index("transfer_fcfs_clearance")
    batch_at = source.index("transfer_batch")
    tvt_at = source.index("transfer_tvt_mp_passage_attempts")
    assert fcfs_at < batch_at < tvt_at
    assert "run_tvt_mp_driver" not in source

    fcfs_world = _world(
        "fcfs_before_tvt",
        order_control_type="fcfs",
        order_control_eligible=True,
    )
    fcfs_vehicle = _place(fcfs_world, "fcfs_car", "in_a", visit_id=1)
    _junction(fcfs_world).transfer()
    assert fcfs_vehicle.link.name == "out"

    batch_world = _world(
        "batch_before_tvt",
        order_control_type="batch",
        order_control_eligible=True,
    )
    _place(batch_world, "batch_car", "in_a", visit_id=1)
    try:
        _junction(batch_world).transfer()
    except Exception as error:
        assert "TVT rank ledger" not in str(error)


def test_route_next_link_none_is_runtime_error_for_tvt_candidate():
    cases = []

    real_world = _world("none_real")
    real_vehicle = _place(real_world, "real_none", "in_a", visit_id=1, route_next_link=None)
    real_state = _confirm(real_world, [real_vehicle], formal_outlink_name="out_formal")
    cases.append((real_world, real_vehicle, real_state))

    past_world = _world("none_past")
    past_vehicle = _place(past_world, "past_none", "in_a", visit_id=1, route_next_link=None)
    past_state = _confirm(past_world, [past_vehicle], formal_outlink_name="out_formal")
    _as_fork(past_world)
    cases.append((past_world, past_vehicle, past_state))

    ordinary_world = _world("none_ordinary")
    ordinary_vehicle = _place(
        ordinary_world,
        "ordinary_none",
        "in_a",
        visit_id=1,
        route_next_link=None,
    )
    ordinary_state = _register_only(ordinary_world, [ordinary_vehicle])
    _as_fork(ordinary_world)
    cases.append((ordinary_world, ordinary_vehicle, ordinary_state))

    for world, vehicle, rank_state in cases:
        visit_key = (vehicle.name, 1)
        rank_before = rank_state.assigned_rank(visit_key)
        error = _expect_runtime_error(_junction(world).transfer)
        message = str(error)
        assert "junction" in message
        assert vehicle.name in message
        assert "route_next_link=None" in message
        assert vehicle.link.name == "in_a"
        assert rank_state.formal_route_next_link_name(visit_key) in (None, "out_formal")
        assert rank_state.assigned_rank(visit_key) == rank_before
        assert vehicle.payment_paid == 3
        assert vehicle.payment_received == 4


def test_generic_baseline_fork_uses_ordinary_merge_without_rank_ledger():
    # Generic baseline fork: no TVT ledger, ordinary merge, passage still recorded.
    world = _world("generic_fork")
    vehicle = _place(world, "generic_car", "in_a", visit_id=1)
    collector = _as_fork(world, apply_copied_tvt_confirmed_ranks=False)
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle.id,
        node_name="junction",
        inlink_name="in_a",
        visit_id=1,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
        baseline_passage_timestep=None,
    )
    junction = _junction(world)
    junction.transfer()
    assert collector.apply_copied_tvt_confirmed_ranks is False
    assert vehicle.link.name == "out"
    snapshot = collector.get_baseline_visit_snapshot(vehicle.name, 1)
    assert snapshot["baseline_passage_timestep"] == world.T
    assert junction.last_order_control_inlink is None
    assert junction.last_order_control_entry_timestep is None
    assert "junction" not in world.order_control_tvt_rank_states_by_node_name


def test_tvt_rank_applying_baseline_fork_applies_copied_confirmed_ranks():
    # TVT baseline fork tries the copied confirmed rank before the ordinary group.
    world = _world("tvt_rank_fork", flow_capacity=1)
    confirmed = _place(world, "copied_confirmed", "in_b", visit_id=1)
    ordinary = _place(world, "ordinary_later", "in_a", visit_id=2)
    junction = _junction(world)
    junction.incoming_vehicles = [ordinary, confirmed]
    _confirm(world, [confirmed])
    _register_only(world, [ordinary])
    fork = world.copy()
    world.order_control_tvt_rank_states_by_node_name["junction"].confirm_visits_in_order(
        [("ordinary_later", 2)]
    )
    fork_state = fork.order_control_tvt_rank_states_by_node_name["junction"]
    assert fork_state.is_confirmed(("ordinary_later", 2)) is False
    fork_junction = fork.get_node("junction")
    fork_junction.flow_capacity = 1
    fork_junction.flow_capacity_remain = 1
    fork_collector = _as_fork(fork, apply_copied_tvt_confirmed_ranks=True)
    assert fork_collector.apply_copied_tvt_confirmed_ranks is True
    fork_junction.transfer()
    fork_confirmed = None
    fork_ordinary = None
    for vehicle in fork.VEHICLES.values():
        if vehicle.name == "copied_confirmed":
            fork_confirmed = vehicle
        if vehicle.name == "ordinary_later":
            fork_ordinary = vehicle
    assert fork_confirmed.link.name == "out"
    assert fork_ordinary.link.name == "in_a"
    assert fork_state.is_confirmed(("ordinary_later", 2)) is False


def test_tvt_rank_applying_baseline_fork_missing_node_ledger_is_runtime_error():
    # mode True does not fall back to ordinary merge when the node ledger is absent.
    world = _world("tvt_fork_missing_ledger")
    vehicle = _place(world, "needs_ledger", "in_a", visit_id=1)
    collector = _as_fork(world, apply_copied_tvt_confirmed_ranks=True)
    assert collector.apply_copied_tvt_confirmed_ranks is True
    junction = _junction(world)
    error = _expect_runtime_error(junction.transfer)
    assert "junction" in str(error)
    assert "TVT rank ledger is missing" in str(error)
    assert vehicle.link.name == "in_a"
    assert vehicle in junction.incoming_vehicles


def test_empty_incoming_vehicles_do_not_require_rank_ledger():
    # No arrival candidates means there is no rank to check.
    cases = []

    real_world = _world("empty_real")
    cases.append((real_world, None))

    tvt_fork = _world("empty_tvt_fork")
    tvt_collector = _as_fork(tvt_fork, apply_copied_tvt_confirmed_ranks=True)
    cases.append((tvt_fork, tvt_collector))

    generic_fork = _world("empty_generic_fork")
    generic_collector = _as_fork(
        generic_fork,
        apply_copied_tvt_confirmed_ranks=False,
    )
    cases.append((generic_fork, generic_collector))

    for world, collector in cases:
        junction = _junction(world)
        assert junction.incoming_vehicles == []
        assert world.order_control_tvt_rank_states_by_node_name == {}
        link_vehicles_before = []
        for link in world.LINKS:
            link_vehicles_before.append((link.name, list(link.vehicles)))
        record_count_before = None
        if collector is not None:
            record_count_before = len(collector._visit_records_by_primary_key)
            assert record_count_before == 0
        finish_calls = []
        original_finish = junction._finish_node_transfer

        def counting_finish(original_finish=original_finish, finish_calls=finish_calls):
            finish_calls.append(1)
            return original_finish()

        with patch.object(junction, "_finish_node_transfer", counting_finish):
            junction.transfer()
        assert finish_calls == [1]
        assert junction.incoming_vehicles == []
        assert world.order_control_tvt_rank_states_by_node_name == {}
        assert junction.last_order_control_inlink is None
        assert junction.last_order_control_entry_timestep is None
        assert world.T == 10
        link_vehicles_after = []
        for link in world.LINKS:
            link_vehicles_after.append((link.name, list(link.vehicles)))
        assert link_vehicles_after == link_vehicles_before
        if collector is None:
            assert world._order_control_baseline_collector is None
        else:
            assert len(collector._visit_records_by_primary_key) == record_count_before
    assert cases[1][1].apply_copied_tvt_confirmed_ranks is True
    assert cases[2][1].apply_copied_tvt_confirmed_ranks is False


def _waiting_passage_entry(world, vehicle, *, role):
    visit_key = (vehicle.name, vehicle.order_control_current_visit["visit_id"])
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=world.T,
        node_name="junction",
        buyers_sorted=((vehicle.name, 1),),
        visit_key=visit_key,
        vehicle_name=vehicle.name,
        role=role,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=15,
        candidate_passage_timestep=11,
        true_vot_per_second=2.0,
        baseline_minus_candidate_passage_timesteps=100,
        baseline_minus_candidate_passage_seconds=101,
        baseline_minus_candidate_time_value=102,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="not-the-live-outlink",
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.entries_by_node_name_and_visit_key[("junction", visit_key)] = entry
    return visit_key, entry


def _forbid_actual_prepare(calls):
    def spy(**kwargs):
        calls.append(kwargs["visit_key"])
        raise AssertionError("actual passage prepare must not be called")

    return patch.object(
        physical_transfer,
        "prepare_tvt_mp_actual_passage_observation",
        spy,
    )


def test_real_world_passage_records_actual_observation_after_clearance_update():
    world = _world("actual_on_real_passage")
    vehicle = _place(world, "buyer_car", "in_a", visit_id=1)
    vehicle.vot_true = None
    vehicle.order_exchange_log = ["establishment"]
    old_log = vehicle.order_exchange_log
    _confirm(world, [vehicle])
    visit_key, entry = _waiting_passage_entry(
        world,
        vehicle,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    junction = _junction(world)
    inlink = world.get_link("in_a")
    calls = []
    original_prepare = physical_transfer.prepare_tvt_mp_actual_passage_observation
    original_commit = physical_transfer.commit_tvt_mp_actual_passage_observation

    def prepare_spy(**kwargs):
        assert junction.last_order_control_inlink is None
        assert junction.last_order_control_entry_timestep is None
        assert kwargs["visit_key"] == visit_key
        assert kwargs["actual_outlink"] is world.get_link("out")
        assert kwargs["actual_passage_timestep"] == world.T
        calls.append("prepare")
        return original_prepare(**kwargs)

    def commit_spy(prepared):
        assert vehicle.link.name == "out"
        assert junction.last_order_control_inlink is inlink
        assert junction.last_order_control_entry_timestep == world.T
        calls.append("commit")
        return original_commit(prepared)

    with patch.object(
        physical_transfer,
        "prepare_tvt_mp_actual_passage_observation",
        prepare_spy,
    ):
        with patch.object(
            physical_transfer,
            "commit_tvt_mp_actual_passage_observation",
            commit_spy,
        ):
            junction.transfer()
    assert calls == ["prepare", "commit"]
    record = entry.actual_passage_observation_record
    assert vehicle.order_exchange_log[-1] is record
    assert vehicle.order_exchange_log is not old_log
    assert old_log == ["establishment"]
    assert record.actual_passage_timestep == 10
    assert record.actual_route_next_link_name == "out"
    assert record.true_vot_per_second == 2.0
    assert record.baseline_minus_candidate_passage_timesteps == 100
    assert record.baseline_minus_actual_passage_timesteps == 5
    assert record.baseline_minus_actual_passage_seconds == 5
    assert record.baseline_minus_actual_time_value == 10.0
    assert record.candidate_minus_actual_passage_timesteps == 1
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    assert registry.entries_by_node_name_and_visit_key[("junction", visit_key)] is entry
    assert vehicle.vot_true is None


def test_passage_without_wait_entry_does_not_record_actual_observation():
    world = _world("actual_without_entry")
    vehicle = _place(world, "fallback_car", "in_a", visit_id=1)
    vehicle.order_exchange_log = ["old"]
    _confirm(world, [vehicle])
    _junction(world).transfer()
    assert vehicle.link.name == "out"
    assert vehicle.order_exchange_log == ["old"]
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    assert registry.entries_by_node_name_and_visit_key == {}
    assert registry.trades_by_transaction_key == {}


def test_temporary_skip_does_not_prepare_actual_observation():
    world = _world("actual_skip_not_head")
    blocked = _place(world, "blocked_actual", "in_a", visit_id=1, behind=True)
    _confirm(world, [blocked])
    visit_key, entry = _waiting_passage_entry(
        world,
        blocked,
        role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
    )
    calls = []
    with _forbid_actual_prepare(calls):
        _junction(world).transfer()
    assert calls == []
    assert blocked.link.name == "in_a"
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    assert entry.actual_passage_observation_record is None
    assert ("junction", visit_key) in (
        world.order_control_tvt_mp_actual_passage_wait_registry
        .entries_by_node_name_and_visit_key
    )


def test_capacity_shortage_does_not_prepare_actual_observation():
    world = _world("actual_skip_flow", flow_capacity=1)
    junction = _junction(world)
    junction.flow_capacity_remain = 0
    vehicle = _place(world, "flow_actual", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    visit_key, entry = _waiting_passage_entry(
        world,
        vehicle,
        role=OrderControlTvtMpActualPassageRole.SELLER,
    )
    calls = []
    with _forbid_actual_prepare(calls):
        junction.transfer()
    assert calls == []
    assert vehicle.link.name == "in_a"
    assert entry.actual_passage_observation_record is None
    assert ("junction", visit_key) in (
        world.order_control_tvt_mp_actual_passage_wait_registry
        .entries_by_node_name_and_visit_key
    )


def test_clearance_stop_does_not_prepare_actual_observation():
    world = _world("actual_clearance_stop")
    world.order_control_clearance_timesteps = 1
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 1
    vehicle = _place(world, "clear_actual", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    _waiting_passage_entry(
        world,
        vehicle,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = world.T
    calls = []
    with _forbid_actual_prepare(calls):
        junction.transfer()
    assert calls == []
    assert vehicle.link.name == "in_a"
    assert junction.last_order_control_inlink.name == "side"
    assert junction.last_order_control_entry_timestep == world.T


def test_baseline_fork_does_not_prepare_actual_observation():
    world = _world("actual_not_on_fork")
    vehicle = _place(world, "fork_car", "in_a", visit_id=1)
    vehicle.order_exchange_log = ["old"]
    _confirm(world, [vehicle])
    visit_key, entry = _waiting_passage_entry(
        world,
        vehicle,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    collector = _as_fork(world)
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle.id,
        node_name="junction",
        inlink_name="in_a",
        visit_id=1,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
        baseline_passage_timestep=None,
    )
    calls = []
    with _forbid_actual_prepare(calls):
        _junction(world).transfer()
    assert calls == []
    assert vehicle.link.name == "out"
    assert vehicle.order_exchange_log == ["old"]
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    assert entry.actual_passage_observation_record is None
    snapshot = collector.get_baseline_visit_snapshot(vehicle.name, 1)
    assert snapshot["baseline_passage_timestep"] == world.T
    assert ("junction", visit_key) in (
        world.order_control_tvt_mp_actual_passage_wait_registry
        .entries_by_node_name_and_visit_key
    )


def test_prepare_failure_stops_before_physical_passage():
    world = _world("actual_prepare_stops_transfer")
    vehicle = _place(world, "bad_log_car", "in_a", visit_id=1)
    vehicle.order_exchange_log = ("not-a-list",)
    _confirm(world, [vehicle])
    visit_key, entry = _waiting_passage_entry(
        world,
        vehicle,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    junction = _junction(world)
    inlink = world.get_link("in_a")
    outlink = world.get_link("out")
    junction.last_order_control_inlink = inlink
    junction.last_order_control_entry_timestep = 4
    inlink_vehicles = list(inlink.vehicles)
    outlink_vehicles = list(outlink.vehicles)
    incoming_before = list(junction.incoming_vehicles)
    capacity_out = inlink.capacity_out_remain
    capacity_in = outlink.capacity_in_remain
    flow_remain = junction.flow_capacity_remain
    try:
        junction.transfer()
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True
    assert vehicle.link is inlink
    assert list(inlink.vehicles) == inlink_vehicles
    assert list(outlink.vehicles) == outlink_vehicles
    assert list(junction.incoming_vehicles) == incoming_before
    assert inlink.capacity_out_remain == capacity_out
    assert outlink.capacity_in_remain == capacity_in
    assert junction.flow_capacity_remain == flow_remain
    assert junction.last_order_control_inlink is inlink
    assert junction.last_order_control_entry_timestep == 4
    assert vehicle.order_exchange_log == ("not-a-list",)
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    assert entry.actual_passage_observation_record is None
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    assert registry.entries_by_node_name_and_visit_key[("junction", visit_key)] is entry


def test_registry_matches_defined_functions():
    defined_names = []
    defined_functions = []
    for name, value in list(globals().items()):
        if name.startswith("test_") and callable(value):
            defined_names.append(name)
            defined_functions.append(value)
    tests_names = []
    for function in TESTS:
        tests_names.append(function.__name__)
    assert tests_names == defined_names
    assert list(TESTS) == defined_functions


TESTS = tuple(
    value
    for name, value in list(globals().items())
    if name.startswith("test_") and callable(value)
)


if __name__ == "__main__":
    for current_case in TESTS:
        current_case()
        print("PASS", current_case.__name__)
    print(len(TESTS), "tests passed")
