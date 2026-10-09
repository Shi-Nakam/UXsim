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
    OrderControlTvtMpActualNodePassageRecord,
    OrderControlTvtMpActualPassageCommonFrozenInput,
    OrderControlTvtMpActualPassageMonetaryFrozenInput,
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitStatus,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRouteOrigin,
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


def _register_unconfirmed_baseline_snapshot(
    collector,
    vehicle,
    *,
    baseline_arrival_timestep=10,
    arrival_tiebreaker=0.1,
    route_next_link_name=None,
    inlink_name=None,
    vehicle_id=None,
):
    """Record one arrived unconfirmed visit so the baseline scan can order it."""
    if inlink_name is None:
        inlink_name = vehicle.link.name
    if route_next_link_name is None:
        route_next_link_name = vehicle.route_next_link.name
    if vehicle_id is None:
        vehicle_id = vehicle.id
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle_id,
        node_name="junction",
        inlink_name=inlink_name,
        visit_id=vehicle.order_control_current_visit["visit_id"],
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=baseline_arrival_timestep,
        arrival_tiebreaker=arrival_tiebreaker,
        route_next_link_name=route_next_link_name,
        baseline_passage_timestep=None,
    )


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
    for vehicle in fork.VEHICLES.values():
        if vehicle.name == "new_car":
            _register_unconfirmed_baseline_snapshot(
                fork._order_control_baseline_collector,
                vehicle,
                baseline_arrival_timestep=12,
            )
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
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        ordinary,
        baseline_arrival_timestep=12,
    )
    junction.transfer()
    assert confirmed.link.name == "out"
    assert ordinary.link.name == "in_a"


def test_skipped_past_confirmed_vehicle_is_excluded_from_ordinary_merge():
    world = _world("fork_exclude_skip")
    skipped = _place(world, "skipped_confirmed", "in_a", visit_id=1, behind=True)
    ordinary = _place(world, "ordinary_passes", "in_b", visit_id=2)
    _confirm(world, [skipped])
    _register_only(world, [ordinary])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        ordinary,
        baseline_arrival_timestep=12,
    )
    seen = []
    original = physical_transfer._try_unconfirmed_baseline_vehicles

    def spy(node, unconfirmed_baseline_vehicles):
        seen.append(unconfirmed_baseline_vehicles)
        return original(node, unconfirmed_baseline_vehicles)

    with patch.object(
        physical_transfer,
        "_try_unconfirmed_baseline_vehicles",
        spy,
    ):
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
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        ordinary,
        baseline_arrival_timestep=12,
    )
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 0
    junction.last_order_control_inlink = world.get_link("side")
    junction.last_order_control_entry_timestep = world.T
    seen = []
    original = physical_transfer._try_unconfirmed_baseline_vehicles

    def spy(node, unconfirmed_baseline_vehicles):
        seen.append(unconfirmed_baseline_vehicles)
        return original(node, unconfirmed_baseline_vehicles)

    with patch.object(
        physical_transfer,
        "_try_unconfirmed_baseline_vehicles",
        spy,
    ):
        junction.transfer()
    assert seen == []
    assert confirmed.link.name == "in_a"
    assert ordinary.link.name == "in_b"


def test_unconfirmed_baseline_group_uses_arrival_order_not_merge_priority():
    world = _world(
        "fork_arrival_not_priority",
        hard_deterministic_mode=True,
        flow_capacity=1,
    )
    early = _place(world, "early_arrival", "in_a", visit_id=1)
    late = _place(world, "late_high_priority", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 5
    _register_only(world, [early, late])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        early,
        baseline_arrival_timestep=8,
        arrival_tiebreaker=0.9,
    )
    _register_unconfirmed_baseline_snapshot(
        collector,
        late,
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.1,
    )
    _junction(world).transfer()
    assert early.link.name == "out"
    assert late.link.name == "in_b"


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
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        ordinary,
        baseline_arrival_timestep=12,
    )
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
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        first,
        baseline_arrival_timestep=8,
    )
    _register_unconfirmed_baseline_snapshot(
        collector,
        second,
        baseline_arrival_timestep=12,
    )
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
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(collector, vehicle)
    junction = _junction(world)
    junction.transfer()
    assert vehicle.link.name == "out"
    assert junction.last_order_control_inlink is world.get_link("in_a")
    assert junction.last_order_control_entry_timestep == world.T


def test_same_inlink_ordinary_group_needs_no_extra_clearance_wait():
    world = _world("same_inlink_ordinary")
    vehicle = _place(world, "same_inlink_car", "in_a", visit_id=1)
    _register_only(world, [vehicle])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(collector, vehicle)
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
    confirmed_collector = _as_fork(confirmed_world)
    _register_unconfirmed_baseline_snapshot(
        confirmed_collector,
        ordinary,
        baseline_arrival_timestep=12,
    )
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
    ordinary_collector = _as_fork(ordinary_world)
    # Arrival order, not merge priority, decides who is tried first.
    _register_unconfirmed_baseline_snapshot(
        ordinary_collector,
        winner,
        baseline_arrival_timestep=8,
        arrival_tiebreaker=0.2,
    )
    _register_unconfirmed_baseline_snapshot(
        ordinary_collector,
        loser,
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.1,
    )
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
    for vehicle in fork.VEHICLES.values():
        if vehicle.name == "ordinary_later":
            _register_unconfirmed_baseline_snapshot(
                fork_collector,
                vehicle,
                baseline_arrival_timestep=12,
            )
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


_PASSAGE_BASELINE_TIMESTEP = 15
_PASSAGE_CANDIDATE_TIMESTEP = 11
_PASSAGE_TRUE_VOT = 2.0
_PASSAGE_PEER_VISIT_ID = 99


def _passage_wait_entry_kwargs(
    *,
    visit_key,
    vehicle_name,
    role,
    decision_timestep,
    buyers_sorted,
):
    return {
        "tvt_decision_timestep": decision_timestep,
        "node_name": "junction",
        "buyers_sorted": buyers_sorted,
        "visit_key": visit_key,
        "vehicle_name": vehicle_name,
        "role": role,
        "wait_status": OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        "baseline_passage_timestep": _PASSAGE_BASELINE_TIMESTEP,
        "candidate_passage_timestep": _PASSAGE_CANDIDATE_TIMESTEP,
        "true_vot_per_second": _PASSAGE_TRUE_VOT,
        "baseline_minus_candidate_passage_timesteps": 100,
        "baseline_minus_candidate_passage_seconds": 101,
        "baseline_minus_candidate_time_value": 102,
        "predicted_observation_status": (
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        "predicted_route_next_link_name": "not-the-live-outlink",
        "common_frozen_input": OrderControlTvtMpActualPassageCommonFrozenInput(
            baseline_local_rank=2,
            post_trade_local_rank=1,
            rank_change=1,
            route_origin=(
                OrderControlTvtMpLocalBindingRouteOrigin
                .BASELINE_TARGET_NODE_ARRIVAL_ROUTE
            ),
        ),
        "monetary_frozen_input": (
            None
            if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING
            else OrderControlTvtMpActualPassageMonetaryFrozenInput(
                declared_vot_per_second=1.0,
                payment_paid_in_this_transaction=(
                    1.0
                    if role is OrderControlTvtMpActualPassageRole.BUYER
                    else 0
                ),
                payment_received_in_this_transaction=(
                    1.0
                    if role is OrderControlTvtMpActualPassageRole.SELLER
                    else 0
                ),
            )
        ),
    }


def _register_passage_wait_entry(
    registry,
    *,
    visit_key,
    vehicle_name,
    role,
    decision_timestep,
    buyers_sorted,
):
    entry = OrderControlTvtMpActualPassageWaitEntry(
        **_passage_wait_entry_kwargs(
            visit_key=visit_key,
            vehicle_name=vehicle_name,
            role=role,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
    )
    registry.entries_by_node_name_and_visit_key[("junction", visit_key)] = entry
    return entry


def _mark_wait_entry_actually_observed(entry, *, actual_timestep):
    record = OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=entry.tvt_decision_timestep,
        node_name=entry.node_name,
        buyers_sorted=entry.buyers_sorted,
        visit_key=entry.visit_key,
        vehicle_name=entry.vehicle_name,
        role=entry.role,
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
        ),
        baseline_passage_timestep=entry.baseline_passage_timestep,
        candidate_passage_timestep=entry.candidate_passage_timestep,
        true_vot_per_second=entry.true_vot_per_second,
        predicted_observation_status=entry.predicted_observation_status,
        predicted_route_next_link_name=entry.predicted_route_next_link_name,
        baseline_minus_candidate_passage_timesteps=(
            entry.baseline_minus_candidate_passage_timesteps
        ),
        baseline_minus_candidate_passage_seconds=(
            entry.baseline_minus_candidate_passage_seconds
        ),
        baseline_minus_candidate_time_value=entry.baseline_minus_candidate_time_value,
        baseline_minus_actual_passage_timesteps=(
            entry.baseline_passage_timestep - actual_timestep
        ),
        baseline_minus_actual_passage_seconds=(
            entry.baseline_passage_timestep - actual_timestep
        ),
        baseline_minus_actual_time_value=(
            (entry.baseline_passage_timestep - actual_timestep) * entry.true_vot_per_second
        ),
        candidate_minus_actual_passage_timesteps=(
            entry.candidate_passage_timestep - actual_timestep
        ),
        candidate_minus_actual_passage_seconds=(
            entry.candidate_passage_timestep - actual_timestep
        ),
        candidate_minus_actual_time_value=(
            (entry.candidate_passage_timestep - actual_timestep) * entry.true_vot_per_second
        ),
        actual_passage_timestep=actual_timestep,
        actual_route_next_link_name="out",
    )
    entry.actual_passage_observation_record = record
    entry.wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    return entry


def _register_formal_trade_wait_for_passage(
    registry,
    *,
    decision_timestep,
    buyers_sorted,
    buyer_visit_keys,
    seller_visit_keys,
    nonparticipating_visit_keys=(),
):
    all_visit_keys = tuple(
        list(buyer_visit_keys)
        + list(seller_visit_keys)
        + list(nonparticipating_visit_keys)
    )
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=decision_timestep,
        node_name="junction",
        buyers_sorted=buyers_sorted,
        all_visit_keys=all_visit_keys,
        buyer_visit_keys=buyer_visit_keys,
        seller_visit_keys=seller_visit_keys,
        nonparticipating_visit_keys=nonparticipating_visit_keys,
    )
    transaction_key = (decision_timestep, "junction", buyers_sorted)
    registry.trades_by_transaction_key[transaction_key] = trade
    return trade


def _waiting_passage_entry(
    world,
    vehicle,
    *,
    role,
    include_waiting_nonparticipant=False,
):
    visit_key = (vehicle.name, vehicle.order_control_current_visit["visit_id"])
    decision_timestep = world.T
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    peer_buyer_name = f"peer_buyer_for_{vehicle.name}"
    peer_seller_name = f"peer_seller_for_{vehicle.name}"
    peer_buyer_visit_key = (peer_buyer_name, _PASSAGE_PEER_VISIT_ID)
    peer_seller_visit_key = (peer_seller_name, _PASSAGE_PEER_VISIT_ID)
    nonparticipating_visit_keys = ()
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        buyer_visit_keys = (visit_key,)
        seller_visit_keys = (peer_seller_visit_key,)
        buyers_sorted = (visit_key,)
        _register_passage_wait_entry(
            registry,
            visit_key=peer_seller_visit_key,
            vehicle_name=peer_seller_name,
            role=OrderControlTvtMpActualPassageRole.SELLER,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
    elif role is OrderControlTvtMpActualPassageRole.SELLER:
        buyer_visit_keys = (peer_buyer_visit_key,)
        seller_visit_keys = (visit_key,)
        buyers_sorted = (peer_buyer_visit_key,)
        _register_passage_wait_entry(
            registry,
            visit_key=peer_buyer_visit_key,
            vehicle_name=peer_buyer_name,
            role=OrderControlTvtMpActualPassageRole.BUYER,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
    else:
        buyer_visit_keys = (peer_buyer_visit_key,)
        seller_visit_keys = (peer_seller_visit_key,)
        nonparticipating_visit_keys = (visit_key,)
        buyers_sorted = (peer_buyer_visit_key,)
        _register_passage_wait_entry(
            registry,
            visit_key=peer_buyer_visit_key,
            vehicle_name=peer_buyer_name,
            role=OrderControlTvtMpActualPassageRole.BUYER,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
        _register_passage_wait_entry(
            registry,
            visit_key=peer_seller_visit_key,
            vehicle_name=peer_seller_name,
            role=OrderControlTvtMpActualPassageRole.SELLER,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
    if include_waiting_nonparticipant and role is not OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        nonpart_name = f"peer_nonpart_for_{vehicle.name}"
        nonpart_visit_key = (nonpart_name, _PASSAGE_PEER_VISIT_ID + 1)
        nonparticipating_visit_keys = (nonpart_visit_key,)
        _register_passage_wait_entry(
            registry,
            visit_key=nonpart_visit_key,
            vehicle_name=nonpart_name,
            role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
        buyer_visit_keys = tuple(buyer_visit_keys)
        seller_visit_keys = tuple(seller_visit_keys)
    entry = _register_passage_wait_entry(
        registry,
        visit_key=visit_key,
        vehicle_name=vehicle.name,
        role=role,
        decision_timestep=decision_timestep,
        buyers_sorted=buyers_sorted,
    )
    trade = _register_formal_trade_wait_for_passage(
        registry,
        decision_timestep=decision_timestep,
        buyers_sorted=buyers_sorted,
        buyer_visit_keys=buyer_visit_keys,
        nonparticipating_visit_keys=nonparticipating_visit_keys,
        seller_visit_keys=seller_visit_keys,
    )
    return visit_key, entry, trade


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
    visit_key, entry, trade = _waiting_passage_entry(
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
    assert trade.buyer_seller_actual_passage_completion_notified is False
    peer_seller_key = trade.seller_visit_keys[0]
    peer_seller_entry = registry.entries_by_node_name_and_visit_key[
        ("junction", peer_seller_key)
    ]
    assert (
        peer_seller_entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )


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
    visit_key, entry, trade = _waiting_passage_entry(
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
    assert trade.buyer_seller_actual_passage_completion_notified is False
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
    visit_key, entry, trade = _waiting_passage_entry(
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
    assert trade.buyer_seller_actual_passage_completion_notified is False
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
    _visit_key, _entry, trade = _waiting_passage_entry(
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
    assert trade.buyer_seller_actual_passage_completion_notified is False


def test_baseline_fork_does_not_prepare_actual_observation():
    world = _world("actual_not_on_fork")
    vehicle = _place(world, "fork_car", "in_a", visit_id=1)
    vehicle.order_exchange_log = ["old"]
    _confirm(world, [vehicle])
    visit_key, entry, trade = _waiting_passage_entry(
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
    assert trade.buyer_seller_actual_passage_completion_notified is False


def test_prepare_failure_stops_before_physical_passage():
    world = _world("actual_prepare_stops_transfer")
    vehicle = _place(world, "bad_log_car", "in_a", visit_id=1)
    vehicle.order_exchange_log = ("not-a-list",)
    _confirm(world, [vehicle])
    visit_key, entry, trade = _waiting_passage_entry(
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
    assert trade.buyer_seller_actual_passage_completion_notified is False


def _place_peer_vehicle_for_visit_key(world, visit_key, *, inlink_name="in_b"):
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    return _place(world, vehicle_name, inlink_name, visit_id=visit_id)


def test_physical_buyer_first_records_observation_without_completion_flag():
    world = _world("physical_buyer_first")
    buyer = _place(world, "buyer_first", "in_a", visit_id=1)
    _confirm(world, [buyer])
    visit_key, entry, trade = _waiting_passage_entry(
        world,
        buyer,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    _junction(world).transfer()
    assert entry.actual_passage_observation_record is not None
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    assert trade.buyer_seller_actual_passage_completion_notified is False


def test_physical_seller_pre_observed_buyer_last_sets_completion_flag():
    world = _world("physical_buyer_last")
    buyer = _place(world, "buyer_last", "in_a", visit_id=1)
    _confirm(world, [buyer])
    visit_key, entry, trade = _waiting_passage_entry(
        world,
        buyer,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    peer_seller_key = trade.seller_visit_keys[0]
    peer_seller_entry = registry.entries_by_node_name_and_visit_key[
        ("junction", peer_seller_key)
    ]
    _mark_wait_entry_actually_observed(peer_seller_entry, actual_timestep=world.T)
    peer_seller_record_before = peer_seller_entry.actual_passage_observation_record
    _junction(world).transfer()
    assert buyer.link.name == "out"
    assert entry.actual_passage_observation_record is not None
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    assert trade.buyer_seller_actual_passage_completion_notified is True
    assert peer_seller_entry.actual_passage_observation_record is peer_seller_record_before


def test_physical_buyer_pre_observed_seller_last_sets_completion_flag():
    world = _world("physical_seller_last")
    seller = _place(world, "seller_last", "in_b", visit_id=2)
    _confirm(world, [seller])
    visit_key, entry, trade = _waiting_passage_entry(
        world,
        seller,
        role=OrderControlTvtMpActualPassageRole.SELLER,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    peer_buyer_key = trade.buyer_visit_keys[0]
    peer_buyer_entry = registry.entries_by_node_name_and_visit_key[
        ("junction", peer_buyer_key)
    ]
    _mark_wait_entry_actually_observed(peer_buyer_entry, actual_timestep=world.T)
    peer_buyer_record_before = peer_buyer_entry.actual_passage_observation_record
    _junction(world).transfer()
    assert seller.link.name == "out"
    assert entry.actual_passage_observation_record is not None
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    assert trade.buyer_seller_actual_passage_completion_notified is True
    assert peer_buyer_entry.actual_passage_observation_record is peer_buyer_record_before


def test_physical_completion_does_not_wait_for_nonparticipating():
    world = _world("physical_nonpart_unobserved")
    buyer = _place(world, "buyer_nonpart", "in_a", visit_id=1)
    _confirm(world, [buyer])
    _visit_key, _entry, trade = _waiting_passage_entry(
        world,
        buyer,
        role=OrderControlTvtMpActualPassageRole.BUYER,
        include_waiting_nonparticipant=True,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    peer_seller_key = trade.seller_visit_keys[0]
    peer_seller_entry = registry.entries_by_node_name_and_visit_key[
        ("junction", peer_seller_key)
    ]
    _mark_wait_entry_actually_observed(
        peer_seller_entry,
        actual_timestep=world.T,
    )
    peer_seller_record_before = (
        peer_seller_entry.actual_passage_observation_record
    )

    _junction(world).transfer()

    assert buyer.link.name == "out"
    assert trade.buyer_seller_actual_passage_completion_notified is True
    assert (
        peer_seller_entry.actual_passage_observation_record
        is peer_seller_record_before
    )
    nonpart_key = trade.nonparticipating_visit_keys[0]
    nonpart_entry = registry.entries_by_node_name_and_visit_key[
        ("junction", nonpart_key)
    ]
    assert (
        nonpart_entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )


def _node_history(world, node_name="junction"):
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    return registry.records_by_node_name.get(node_name, ())


def _assert_single_history(world, vehicle, *, route_name="out", visit_id=1):
    records = _node_history(world)
    assert len(records) == 1
    record = records[0]
    assert record.visit_key == (vehicle.name, visit_id)
    assert record.actual_passage_timestep == world.T
    assert record.actual_route_next_link_name == route_name
    assert record.actual_node_passage_rank == 1
    assert isinstance(record, OrderControlTvtMpActualNodePassageRecord)
    return record


def _forbid_history_prepare(calls):
    def spy(**kwargs):
        calls.append(kwargs["visit_key"])
        raise AssertionError("node passage history prepare must not be called")

    return patch.object(
        physical_transfer,
        "prepare_tvt_mp_actual_node_passage_history",
        spy,
    )


def _register_fork_snapshot(collector, vehicle):
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle.id,
        node_name="junction",
        inlink_name="in_a",
        visit_id=vehicle.order_control_current_visit["visit_id"],
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
        baseline_passage_timestep=None,
    )


def test_partition3_roles_record_node_passage_history_and_observation():
    assert "actual_node_passage_rank" not in (
        OrderControlTvtMpActualPassageObservationRecord.__dataclass_fields__
    )
    roles = [
        (OrderControlTvtMpActualPassageRole.BUYER, "buyer_history"),
        (OrderControlTvtMpActualPassageRole.SELLER, "seller_history"),
        (
            OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            "nonpart_history",
        ),
    ]
    for role, vehicle_name in roles:
        world = _world("history_" + vehicle_name)
        vehicle = _place(world, vehicle_name, "in_a", visit_id=1)
        _confirm(world, [vehicle])
        visit_key, entry, trade = _waiting_passage_entry(
            world,
            vehicle,
            role=role,
        )
        _junction(world).transfer()
        record = _assert_single_history(world, vehicle)
        assert record.visit_key == visit_key
        assert entry.actual_passage_observation_record is not None
        assert entry.actual_passage_observation_record.visit_key == visit_key
        if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
            assert trade.buyer_seller_actual_passage_completion_notified is False


def test_partition4_fallback_and_past_confirmed_visits_record_history():
    # These visits are confirmed on the rank ledger and have no WaitEntry.
    partition4 = _world("history_partition4")
    partition4_vehicle = _place(partition4, "partition4_car", "in_a", visit_id=1)
    _confirm(partition4, [partition4_vehicle])
    _junction(partition4).transfer()
    _assert_single_history(partition4, partition4_vehicle)
    assert (
        partition4.order_control_tvt_mp_actual_passage_wait_registry
        .entries_by_node_name_and_visit_key
        == {}
    )

    fallback = _world("history_fallback")
    fallback_vehicle = _place(fallback, "fallback_history_car", "in_a", visit_id=1)
    _confirm(fallback, [fallback_vehicle])
    _junction(fallback).transfer()
    _assert_single_history(fallback, fallback_vehicle)
    assert (
        fallback.order_control_tvt_mp_actual_passage_wait_registry
        .entries_by_node_name_and_visit_key
        == {}
    )

    past = _world("history_past_confirmed")
    past_vehicle = _place(past, "past_history_car", "in_a", visit_id=1)
    _confirm(past, [past_vehicle])
    past.T = 14
    _prepare_logs(past)
    junction = _junction(past)
    junction.incoming_vehicles = [past_vehicle]
    junction.transfer()
    record = _assert_single_history(past, past_vehicle)
    assert record.actual_passage_timestep == 14


def test_history_is_recorded_when_observation_prepare_returns_none():
    world = _world("history_observation_none")
    vehicle = _place(world, "no_entry_history", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    seen = []
    original = physical_transfer.prepare_tvt_mp_actual_passage_observation

    def spy(**kwargs):
        result = original(**kwargs)
        seen.append(result)
        return result

    vehicle.order_exchange_log = ["old"]
    with patch.object(
        physical_transfer,
        "prepare_tvt_mp_actual_passage_observation",
        spy,
    ):
        _junction(world).transfer()
    assert seen == [None]
    _assert_single_history(world, vehicle)
    assert vehicle.order_exchange_log == ["old"]


def test_same_timestep_successes_keep_attempt_order_ranks():
    world = _world("history_same_timestep")
    world.addNode("dest_b", 2, 1)
    world.addLink(
        "out_b",
        "junction",
        "dest_b",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    _prepare_logs(world)
    # Same inlink: after the first leaves, the next confirmed vehicle is the
    # physical head and clearance does not wait. Different outlinks keep an
    # open entrance for the second success in this timestep.
    first = _place(world, "z_first", "in_a", visit_id=1, outlink_name="out")
    second = _place(world, "a_second", "in_a", visit_id=2, outlink_name="out_b")
    junction = _junction(world)
    junction.incoming_vehicles = [second, first]
    _confirm(world, [first, second])
    for link in world.LINKS:
        link.capacity_in_remain = 10
        link.capacity_out_remain = 10
    junction.flow_capacity_remain = 10
    junction.transfer()
    records = _node_history(world)
    assert [record.visit_key[0] for record in records] == ["z_first", "a_second"]
    assert [record.actual_node_passage_rank for record in records] == [1, 2]
    assert records[0].actual_passage_timestep == world.T
    assert records[1].actual_passage_timestep == world.T
    assert records[0].actual_route_next_link_name == "out"
    assert records[1].actual_route_next_link_name == "out_b"


def test_later_timestep_continues_the_node_passage_rank():
    world = _world("history_continued_rank", flow_capacity=1)
    world.addNode("dest_b", 2, 1)
    world.addLink(
        "out_b",
        "junction",
        "dest_b",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    _prepare_logs(world)
    first = _place(world, "continued_first", "in_a", visit_id=1)
    second = _place(
        world,
        "continued_second",
        "in_b",
        visit_id=2,
        outlink_name="out_b",
    )
    _confirm(world, [first, second])
    junction = _junction(world)
    junction.transfer()
    assert first.link.name == "out"
    assert second.link.name == "in_b"
    assert [record.visit_key[0] for record in _node_history(world)] == [
        "continued_first",
    ]
    world.T = 12
    _prepare_logs(world)
    junction.flow_capacity_remain = 1
    junction.incoming_vehicles = [second]
    for link in world.LINKS:
        link.capacity_in_remain = 10
        link.capacity_out_remain = 10
    junction.transfer()
    assert second.link.name == "out_b"
    records = _node_history(world)
    assert [record.actual_node_passage_rank for record in records] == [1, 2]
    assert records[1].visit_key == ("continued_second", 2)
    assert records[1].actual_route_next_link_name == "out_b"
    assert records[0].actual_passage_timestep == 10
    assert records[1].actual_passage_timestep == 12


def test_another_node_starts_its_passage_rank_at_one():
    world = _world("history_second_node")
    first = _place(world, "node_a_car", "in_a", visit_id=1)
    _confirm(world, [first])
    _junction(world).transfer()
    world.addNode("dest_b", 4, 0)
    world.addNode(
        "junction_b",
        3,
        0,
        order_control_type="time_value",
        order_control_eligible=True,
    )
    world.addLink(
        "in_b2",
        "orig_b",
        "junction_b",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
        merge_priority=1,
    )
    world.addLink(
        "out_b2",
        "junction_b",
        "dest_b",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    _prepare_logs(world)
    node_b = world.get_node("junction_b")
    inlink = world.get_link("in_b2")
    outlink = world.get_link("out_b2")
    vehicle = world.addVehicle("orig_b", "dest_b", 0, name="node_b_car")
    vehicle.state = "run"
    vehicle.link = inlink
    vehicle.x = inlink.length
    vehicle.x_old = inlink.length
    vehicle.link_arrival_time = 0
    vehicle.move_remain = 0
    vehicle.v = 0
    vehicle.route_next_link = outlink
    vehicle.order_control_visit_id = 1
    vehicle.order_control_current_visit = {
        "visit_id": 1,
        "node": node_b,
        "inlink": inlink,
        "earliest_arrival_timestep": 0,
        "arrival_time": 0.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": None,
    }
    inlink.vehicles.append(vehicle)
    node_b.incoming_vehicles.append(vehicle)
    world.VEHICLES_RUNNING[vehicle.name] = vehicle
    rank_state = OrderControlTvtNodeRankState("junction_b")
    rank_state.register_undetermined_visit(("node_b_car", 1))
    rank_state.confirm_visits_in_order([("node_b_car", 1)])
    world.order_control_tvt_rank_states_by_node_name["junction_b"] = rank_state
    node_b.transfer()
    records_b = _node_history(world, "junction_b")
    assert len(records_b) == 1
    assert records_b[0].actual_node_passage_rank == 1
    assert records_b[0].visit_key == ("node_b_car", 1)
    assert _node_history(world)[0].actual_node_passage_rank == 1


def test_temporary_skip_does_not_record_the_skipped_visit():
    world = _world("history_not_head")
    blocked = _place(world, "blocked_history", "in_a", visit_id=1, behind=True)
    follower = _place(world, "follower_history", "in_b", visit_id=2)
    _confirm(world, [blocked, follower])
    _junction(world).transfer()
    assert blocked.link.name == "in_a"
    assert follower.link.name == "out"
    assert [record.visit_key[0] for record in _node_history(world)] == [
        "follower_history",
    ]

    empty_world = _world("history_empty_inlink")
    missing = _place(empty_world, "missing_history", "in_a", visit_id=1)
    empty_world.get_link("in_a").vehicles.clear()
    nxt = _place(empty_world, "next_history", "in_b", visit_id=2)
    _confirm(empty_world, [missing, nxt])
    _junction(empty_world).transfer()
    assert missing.link.name == "in_a"
    assert [record.visit_key[0] for record in _node_history(empty_world)] == [
        "next_history",
    ]


def test_capacity_entry_and_clearance_blocks_do_not_record_history():
    flow_world = _world("history_flow", flow_capacity=1)
    flow_world.get_node("junction").flow_capacity_remain = 0
    flow_vehicle = _place(flow_world, "flow_history", "in_a", visit_id=1)
    _confirm(flow_world, [flow_vehicle])
    flow_calls = []
    with _forbid_history_prepare(flow_calls):
        _junction(flow_world).transfer()
    assert flow_calls == []
    assert flow_vehicle.link.name == "in_a"
    assert _node_history(flow_world) == ()

    out_world = _world("history_out_capacity")
    out_vehicle = _place(out_world, "out_history", "in_a", visit_id=1)
    out_world.get_link("in_a").capacity_out_remain = 0
    _confirm(out_world, [out_vehicle])
    out_calls = []
    with _forbid_history_prepare(out_calls):
        _junction(out_world).transfer()
    assert out_calls == []
    assert out_vehicle.link.name == "in_a"
    assert _node_history(out_world) == ()

    in_world = _world("history_in_capacity")
    in_vehicle = _place(in_world, "in_history", "in_a", visit_id=1)
    in_world.get_link("out").capacity_in_remain = 0
    _confirm(in_world, [in_vehicle])
    in_calls = []
    with _forbid_history_prepare(in_calls):
        _junction(in_world).transfer()
    assert in_calls == []
    assert in_vehicle.link.name == "in_a"
    assert _node_history(in_world) == ()

    space_world = _world("history_entry_space")
    parked = space_world.addVehicle("orig_a", "dest", 0, name="parked_history")
    parked.state = "run"
    parked.link = space_world.get_link("out")
    parked.x = 0
    parked.x_old = 0
    space_world.get_link("out").vehicles.append(parked)
    no_room = _place(space_world, "no_room_history", "in_a", visit_id=1)
    _confirm(space_world, [no_room])
    space_calls = []
    with _forbid_history_prepare(space_calls):
        _junction(space_world).transfer()
    assert space_calls == []
    assert no_room.link.name == "in_a"
    assert _node_history(space_world) == ()

    clear_world = _world("history_clearance")
    clear_world.order_control_clearance_timesteps = 1
    junction = _junction(clear_world)
    junction.order_control_clearance_timesteps = 1
    clear_vehicle = _place(clear_world, "clear_history", "in_a", visit_id=1)
    _confirm(clear_world, [clear_vehicle])
    junction.last_order_control_inlink = clear_world.get_link("side")
    junction.last_order_control_entry_timestep = clear_world.T
    clear_calls = []
    with _forbid_history_prepare(clear_calls):
        junction.transfer()
    assert clear_calls == []
    assert clear_vehicle.link.name == "in_a"
    assert _node_history(clear_world) == ()
    assert junction.last_order_control_inlink.name == "side"


def test_baseline_forks_do_not_record_node_passage_history():
    world = _world("history_tvt_fork")
    vehicle = _place(world, "fork_history_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    collector = _as_fork(world)
    _register_fork_snapshot(collector, vehicle)
    calls = []
    with _forbid_history_prepare(calls):
        _junction(world).transfer()
    assert calls == []
    assert vehicle.link.name == "out"
    assert _node_history(world) == ()

    generic = _world("history_generic_fork")
    generic_vehicle = _place(generic, "generic_history_car", "in_a", visit_id=1)
    generic_collector = _as_fork(
        generic,
        apply_copied_tvt_confirmed_ranks=False,
    )
    _register_fork_snapshot(generic_collector, generic_vehicle)
    generic_calls = []
    with _forbid_history_prepare(generic_calls):
        _junction(generic).transfer()
    assert generic_calls == []
    assert generic_vehicle.link.name == "out"
    assert _node_history(generic) == ()
    assert generic_collector.apply_copied_tvt_confirmed_ranks is False


def test_fcfs_batch_and_no_order_control_do_not_record_history():
    plain = _world(
        "history_none",
        order_control_type="none",
        order_control_eligible=False,
    )
    plain_vehicle = _place(plain, "plain_history", "in_a", visit_id=1)
    _junction(plain).transfer()
    assert plain_vehicle.link.name == "out"
    assert _node_history(plain) == ()

    fcfs_world = _world(
        "history_fcfs",
        order_control_type="fcfs",
        order_control_eligible=True,
    )
    fcfs_vehicle = _place(fcfs_world, "fcfs_history", "in_a", visit_id=1)
    _junction(fcfs_world).transfer()
    assert fcfs_vehicle.link.name == "out"
    assert _node_history(fcfs_world) == ()

    batch_world = _world(
        "history_batch",
        order_control_type="batch",
        order_control_eligible=True,
    )
    _place(batch_world, "batch_history", "in_a", visit_id=1)
    try:
        _junction(batch_world).transfer()
    except Exception as error:
        assert "node passage history" not in str(error)
        assert "TVT rank ledger" not in str(error)
    assert _node_history(batch_world) == ()


def test_trip_end_does_not_record_node_passage_history():
    world = _world("history_trip_end")
    waiting = _place(world, "waiting_history", "in_a", visit_id=1, waiting=True)
    _confirm(world, [waiting])
    calls = []
    with _forbid_history_prepare(calls):
        _junction(world).transfer()
    assert calls == []
    assert waiting.state == "end"
    assert _node_history(world) == ()


def test_duplicate_visit_key_stops_before_physical_passage():
    world = _world("history_duplicate")
    vehicle = _place(world, "duplicate_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    existing = OrderControlTvtMpActualNodePassageRecord(
        ("duplicate_car", 1),
        0,
        "out",
        1,
    )
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    registry.records_by_node_name["junction"] = (existing,)
    junction = _junction(world)
    inlink = world.get_link("in_a")
    outlink = world.get_link("out")
    outlink_before = list(outlink.vehicles)
    vehicle.order_exchange_log = ["old"]
    error = _expect_runtime_error(junction.transfer)
    assert "duplicate_car" in str(error)
    assert vehicle.link is inlink
    assert list(outlink.vehicles) == outlink_before
    assert registry.records_by_node_name["junction"] == (existing,)
    assert junction.last_order_control_inlink is None
    assert junction.last_order_control_entry_timestep is None
    assert vehicle.order_exchange_log == ["old"]


def test_same_vehicle_new_visit_continues_the_node_rank():
    world = _world("history_revisit")
    vehicle = _place(world, "revisit_car", "in_a", visit_id=1)
    rank_state = _confirm(world, [vehicle])
    junction = _junction(world)
    junction.transfer()
    assert [record.visit_key for record in _node_history(world)] == [
        ("revisit_car", 1),
    ]
    inlink = world.get_link("in_a")
    outlink = world.get_link("out")
    outlink.vehicles.remove(vehicle)
    vehicle.link = inlink
    vehicle.x = inlink.length
    vehicle.x_old = inlink.length
    vehicle.state = "run"
    vehicle.route_next_link = outlink
    vehicle.order_control_visit_id = 2
    vehicle.order_control_current_visit = {
        "visit_id": 2,
        "node": junction,
        "inlink": inlink,
        "earliest_arrival_timestep": 0,
        "arrival_time": 0.0,
        "arrival_tiebreaker": 0.2,
        "batch_assignment": None,
    }
    inlink.vehicles.append(vehicle)
    junction.incoming_vehicles.append(vehicle)
    rank_state.register_undetermined_visit(("revisit_car", 2))
    rank_state.confirm_visits_in_order([("revisit_car", 2)])
    world.T = 12
    _prepare_logs(world)
    inlink.capacity_out_remain = 10
    outlink.capacity_in_remain = 10
    junction.transfer()
    records = _node_history(world)
    assert [record.visit_key for record in records] == [
        ("revisit_car", 1),
        ("revisit_car", 2),
    ]
    assert [record.actual_node_passage_rank for record in records] == [1, 2]
    assert records[0].actual_passage_timestep == 10
    assert records[1].actual_passage_timestep == 12


def test_history_commit_is_after_clearance_and_before_observation_commit():
    world = _world("history_commit_order")
    vehicle = _place(world, "order_car", "in_a", visit_id=1)
    _confirm(world, [vehicle])
    visit_key, entry, _trade = _waiting_passage_entry(
        world,
        vehicle,
        role=OrderControlTvtMpActualPassageRole.BUYER,
    )
    junction = _junction(world)
    inlink = world.get_link("in_a")
    order = []
    original_history_prepare = (
        physical_transfer.prepare_tvt_mp_actual_node_passage_history
    )
    original_observation_prepare = (
        physical_transfer.prepare_tvt_mp_actual_passage_observation
    )
    original_history_commit = (
        physical_transfer.commit_tvt_mp_actual_node_passage_history
    )
    original_observation_commit = (
        physical_transfer.commit_tvt_mp_actual_passage_observation
    )
    original_transfer = junction._transfer_one_vehicle_between_links

    def history_prepare_spy(**kwargs):
        order.append("prepare_history")
        assert vehicle.link is inlink
        assert kwargs["visit_key"] == visit_key
        return original_history_prepare(**kwargs)

    def observation_prepare_spy(**kwargs):
        order.append("prepare_observation")
        assert vehicle.link is inlink
        return original_observation_prepare(**kwargs)

    def transfer_spy(moved_vehicle, moved_inlink, moved_outlink):
        order.append("transfer")
        return original_transfer(moved_vehicle, moved_inlink, moved_outlink)

    def history_commit_spy(prepared):
        order.append("commit_history")
        assert vehicle.link.name == "out"
        assert junction.last_order_control_inlink is inlink
        assert junction.last_order_control_entry_timestep == world.T
        assert entry.actual_passage_observation_record is None
        return original_history_commit(prepared)

    def observation_commit_spy(prepared):
        order.append("commit_observation")
        stored = _node_history(world)
        assert len(stored) == 1
        assert stored[0].actual_node_passage_rank == 1
        return original_observation_commit(prepared)

    with patch.object(
        physical_transfer,
        "prepare_tvt_mp_actual_node_passage_history",
        history_prepare_spy,
    ):
        with patch.object(
            physical_transfer,
            "prepare_tvt_mp_actual_passage_observation",
            observation_prepare_spy,
        ):
            with patch.object(
                junction,
                "_transfer_one_vehicle_between_links",
                transfer_spy,
            ):
                with patch.object(
                    physical_transfer,
                    "commit_tvt_mp_actual_node_passage_history",
                    history_commit_spy,
                ):
                    with patch.object(
                        physical_transfer,
                        "commit_tvt_mp_actual_passage_observation",
                        observation_commit_spy,
                    ):
                        junction.transfer()
    assert order == [
        "prepare_history",
        "prepare_observation",
        "transfer",
        "commit_history",
        "commit_observation",
    ]
    assert entry.actual_passage_observation_record is not None


def test_unconfirmed_baseline_arrival_timestep_beats_merge_priority():
    world = _world("arrival_timestep_order", flow_capacity=1)
    early = _place(world, "timestep_early", "in_a", visit_id=1)
    late = _place(world, "timestep_late", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 9
    _register_only(world, [early, late])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector, early, baseline_arrival_timestep=8, arrival_tiebreaker=0.9
    )
    _register_unconfirmed_baseline_snapshot(
        collector, late, baseline_arrival_timestep=12, arrival_tiebreaker=0.1
    )
    _junction(world).transfer()
    assert early.link.name == "out"
    assert late.link.name == "in_b"


def test_unconfirmed_baseline_tiebreaker_breaks_same_arrival_timestep():
    world = _world("arrival_tiebreaker_order", flow_capacity=1)
    # Created first, so this vehicle has the smaller id. A larger tiebreaker
    # must still wait behind the later-created vehicle.
    larger_tie = _place(world, "larger_tie", "in_a", visit_id=1)
    smaller_tie = _place(world, "smaller_tie", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 9
    world.get_link("in_b").merge_priority = 1
    _register_only(world, [larger_tie, smaller_tie])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        larger_tie,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.8,
    )
    _register_unconfirmed_baseline_snapshot(
        collector,
        smaller_tie,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.1,
    )
    _junction(world).transfer()
    assert smaller_tie.link.name == "out"
    assert larger_tie.link.name == "in_a"


def test_unconfirmed_baseline_vehicle_id_breaks_equal_tiebreaker():
    world = _world("arrival_vehicle_id_order", flow_capacity=1)
    smaller_id = _place(world, "smaller_id", "in_a", visit_id=1)
    larger_id = _place(world, "larger_id", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 9
    assert smaller_id.id < larger_id.id
    _register_only(world, [smaller_id, larger_id])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector,
        smaller_id,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.4,
    )
    _register_unconfirmed_baseline_snapshot(
        collector,
        larger_id,
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.4,
    )
    _junction(world).transfer()
    assert smaller_id.link.name == "out"
    assert larger_id.link.name == "in_b"


def test_unconfirmed_baseline_order_ignores_hard_deterministic_mode():
    for mode in (False, True):
        world = _world(
            "arrival_mode_" + str(mode),
            hard_deterministic_mode=mode,
            flow_capacity=1,
        )
        early = _place(world, "mode_early", "in_a", visit_id=1)
        late = _place(world, "mode_late", "in_b", visit_id=2)
        world.get_link("in_a").merge_priority = 1
        world.get_link("in_b").merge_priority = 9
        _register_only(world, [early, late])
        collector = _as_fork(world)
        _register_unconfirmed_baseline_snapshot(
            collector, early, baseline_arrival_timestep=8
        )
        _register_unconfirmed_baseline_snapshot(
            collector, late, baseline_arrival_timestep=12
        )
        _junction(world).transfer()
        assert early.link.name == "out"
        assert late.link.name == "in_b"


def test_unconfirmed_baseline_scan_does_not_use_passage_rng():
    world = _world("arrival_no_rng", flow_capacity=1)
    early = _place(world, "rng_early", "in_a", visit_id=1)
    late = _place(world, "rng_late", "in_b", visit_id=2)
    world.get_link("in_b").merge_priority = 9
    _register_only(world, [early, late])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector, early, baseline_arrival_timestep=8
    )
    _register_unconfirmed_baseline_snapshot(
        collector, late, baseline_arrival_timestep=12
    )
    # numpy Generator.choice and Generator.shuffle cannot be replaced.
    # Any passage-selection draw would change this saved generator state.
    rng_state_before = world.rng.bit_generator.state
    order_rng_state_before = world.order_control_rng.bit_generator.state
    _junction(world).transfer()
    assert world.rng.bit_generator.state == rng_state_before
    assert world.order_control_rng.bit_generator.state == order_rng_state_before
    assert early.link.name == "out"
    assert late.link.name == "in_b"


def test_unconfirmed_baseline_missing_rank_facts_are_runtime_error():
    missing = _world("missing_snapshot")
    missing_vehicle = _place(missing, "missing_record", "in_a", visit_id=1)
    _register_only(missing, [missing_vehicle])
    _as_fork(missing)
    error = _expect_runtime_error(_junction(missing).transfer)
    assert "missing_record" in str(error)
    assert "visit_id 1" in str(error)
    assert "baseline_visit_snapshot" in str(error)
    assert missing_vehicle.link.name == "in_a"

    no_timestep = _world("missing_timestep")
    timestep_vehicle = _place(no_timestep, "no_timestep", "in_a", visit_id=1)
    _register_only(no_timestep, [timestep_vehicle])
    timestep_collector = _as_fork(no_timestep)
    _register_unconfirmed_baseline_snapshot(timestep_collector, timestep_vehicle)
    stored = timestep_collector._visit_records_by_primary_key[
        (timestep_vehicle.name, 1)
    ]
    stored.baseline_arrival_timestep = None
    error = _expect_runtime_error(_junction(no_timestep).transfer)
    assert "baseline_arrival_timestep" in str(error)
    assert timestep_vehicle.link.name == "in_a"

    no_tie = _world("missing_tiebreaker")
    tie_vehicle = _place(no_tie, "no_tie", "in_a", visit_id=1)
    _register_only(no_tie, [tie_vehicle])
    tie_collector = _as_fork(no_tie)
    _register_unconfirmed_baseline_snapshot(tie_collector, tie_vehicle)
    stored = tie_collector._visit_records_by_primary_key[(tie_vehicle.name, 1)]
    stored.arrival_tiebreaker = None
    error = _expect_runtime_error(_junction(no_tie).transfer)
    assert "arrival_tiebreaker" in str(error)

    wrong_id = _world("wrong_vehicle_id")
    id_vehicle = _place(wrong_id, "wrong_id", "in_a", visit_id=1)
    _register_only(wrong_id, [id_vehicle])
    id_collector = _as_fork(wrong_id)
    _register_unconfirmed_baseline_snapshot(
        id_collector,
        id_vehicle,
        vehicle_id=id_vehicle.id + 50,
    )
    error = _expect_runtime_error(_junction(wrong_id).transfer)
    assert "vehicle_id" in str(error)

    wrong_route = _world("wrong_route_name")
    route_vehicle = _place(wrong_route, "wrong_route", "in_a", visit_id=1)
    _register_only(wrong_route, [route_vehicle])
    route_collector = _as_fork(wrong_route)
    _register_unconfirmed_baseline_snapshot(
        route_collector,
        route_vehicle,
        route_next_link_name="side",
    )
    error = _expect_runtime_error(_junction(wrong_route).transfer)
    assert "route_next_link_name" in str(error)
    assert route_vehicle.link.name == "in_a"


def _add_junction_outlink(world, link_name):
    link = world.addLink(
        link_name,
        "junction",
        "dest",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    link.cum_arrival.append(0)
    link.cum_departure.append(0)
    link.traveltime_actual = np.zeros(world.T + 5)
    return link


def test_unconfirmed_physical_skip_tries_the_later_arrival():
    head = _world("skip_not_head", flow_capacity=2)
    early_blocked = _place(head, "not_head_early", "in_a", visit_id=1, behind=True)
    later = _place(head, "not_head_later", "in_b", visit_id=2)
    _register_only(head, [early_blocked, later])
    head_collector = _as_fork(head)
    _register_unconfirmed_baseline_snapshot(
        head_collector, early_blocked, baseline_arrival_timestep=8
    )
    _register_unconfirmed_baseline_snapshot(
        head_collector, later, baseline_arrival_timestep=12
    )
    _junction(head).transfer()
    assert early_blocked.link.name == "in_a"
    assert later.link.name == "out"

    outflow = _world("skip_outflow", flow_capacity=2)
    early_out = _place(outflow, "outflow_early", "in_a", visit_id=1)
    later_out = _place(outflow, "outflow_later", "in_b", visit_id=2)
    outflow.get_link("in_a").capacity_out_remain = 0
    _register_only(outflow, [early_out, later_out])
    outflow_collector = _as_fork(outflow)
    _register_unconfirmed_baseline_snapshot(
        outflow_collector, early_out, baseline_arrival_timestep=8
    )
    _register_unconfirmed_baseline_snapshot(
        outflow_collector, later_out, baseline_arrival_timestep=12
    )
    _junction(outflow).transfer()
    assert early_out.link.name == "in_a"
    assert later_out.link.name == "out"

    inflow = _world("skip_inflow", flow_capacity=2)
    out_b = _add_junction_outlink(inflow, "out_b")
    early_in = _place(inflow, "inflow_early", "in_a", visit_id=1, outlink_name="out")
    later_in = _place(inflow, "inflow_later", "in_b", visit_id=2, outlink_name="out_b")
    inflow.get_link("out").capacity_in_remain = 0
    out_b.capacity_in_remain = 10
    _register_only(inflow, [early_in, later_in])
    inflow_collector = _as_fork(inflow)
    _register_unconfirmed_baseline_snapshot(
        inflow_collector, early_in, baseline_arrival_timestep=8
    )
    _register_unconfirmed_baseline_snapshot(
        inflow_collector,
        later_in,
        baseline_arrival_timestep=12,
        route_next_link_name="out_b",
    )
    _junction(inflow).transfer()
    assert early_in.link.name == "in_a"
    assert later_in.link.name == "out_b"


def test_unconfirmed_node_flow_shortage_still_checks_the_later_visit():
    world = _world("node_flow_checks_later", flow_capacity=1)
    junction = _junction(world)
    junction.flow_capacity_remain = 0
    early = _place(world, "flow_early", "in_a", visit_id=1)
    late = _place(world, "flow_late", "in_b", visit_id=2)
    _register_only(world, [early, late])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector, early, baseline_arrival_timestep=8
    )
    _register_unconfirmed_baseline_snapshot(
        collector, late, baseline_arrival_timestep=12
    )
    checked = []
    original = physical_transfer._physical_passage_limits_should_skip

    def spy(node, vehicle, inlink, outlink):
        checked.append(vehicle.name)
        return original(node, vehicle, inlink, outlink)

    with patch.object(
        physical_transfer,
        "_physical_passage_limits_should_skip",
        spy,
    ):
        junction.transfer()
    assert checked == ["flow_early", "flow_late"]
    assert early.link.name == "in_a"
    assert late.link.name == "in_b"
    assert junction.last_order_control_inlink is None


def test_unconfirmed_clearance_of_earlier_arrival_blocks_later_same_outlink():
    world = _world("earlier_clearance_blocks_later", flow_capacity=2)
    early = _place(world, "clearance_early", "in_a", visit_id=1)
    late = _place(world, "clearance_late", "in_b", visit_id=2)
    world.get_link("in_a").merge_priority = 1
    world.get_link("in_b").merge_priority = 9
    _register_only(world, [early, late])
    collector = _as_fork(world)
    _register_unconfirmed_baseline_snapshot(
        collector, early, baseline_arrival_timestep=8, arrival_tiebreaker=0.2
    )
    _register_unconfirmed_baseline_snapshot(
        collector, late, baseline_arrival_timestep=12, arrival_tiebreaker=0.1
    )
    junction = _junction(world)
    junction.order_control_clearance_timesteps = 1
    previous_inlink = world.get_link("in_b")
    junction.last_order_control_inlink = previous_inlink
    junction.last_order_control_entry_timestep = world.T
    junction.transfer()
    assert early.link.name == "in_a"
    assert late.link.name == "in_b"
    assert junction.last_order_control_inlink is previous_inlink
    assert junction.last_order_control_entry_timestep == 10

    # The next timestep's Vehicle.update puts link-end vehicles back into
    # incoming_vehicles. This direct transfer test does that re-entry itself.
    world.T = 12
    junction.incoming_vehicles.append(early)
    junction.incoming_vehicles.append(late)
    junction.transfer()
    assert early.link.name == "out"
    assert late.link.name == "in_b"
    assert junction.last_order_control_inlink is world.get_link("in_a")
    assert junction.last_order_control_entry_timestep == 12


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
