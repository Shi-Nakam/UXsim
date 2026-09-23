# Tests for one candidate's virtual clock and local capacity refill.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_virtual_time.py

from __future__ import annotations

import copy

from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_virtual_time import (
    OrderControlTvtMpCandidateVirtualTimeState,
    advance_tvt_mp_candidate_virtual_time_one_step,
    initialize_tvt_mp_candidate_virtual_time_state,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.uxsim import World


def _world() -> World:
    world = World(
        name="tvt_mp_candidate_virtual_time",
        deltan=1,
        tmax=40,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig", 0, 0)
    world.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
        flow_capacity=0.5,
        number_of_lanes=1,
    )
    world.addNode("dest", 2, 0)
    world.addNode("dest_b", 2, 1)
    world.addNode("west", 0, 1)
    world.addNode("sink", 0, 2)
    world.addLink(
        "in",
        "orig",
        "merge",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
        capacity_in=0.4,
        capacity_out=0.3,
    )
    world.addLink(
        "out",
        "merge",
        "dest",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
        capacity_in=0.2,
        capacity_out=0.2,
    )
    world.addLink(
        "side",
        "merge",
        "dest_b",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    world.addLink("far", "west", "sink", length=200, free_flow_speed=20, number_of_lanes=1)
    return world


def _place(vehicle, link, route_link) -> None:
    vehicle.link = link
    vehicle.state = "run"
    vehicle.x = 180.0
    vehicle.v = 4.0
    vehicle.lane = 0
    vehicle.leader = None
    vehicle.follower = None
    vehicle.route_next_link = route_link
    vehicle.link_arrival_time = 5.0
    vehicle.move_remain = 1.0


def _local_state():
    world = _world()
    vehicle = world.addVehicle("orig", "dest", 0, name="in_front")
    far_vehicle = world.addVehicle("west", "sink", 0, name="far_veh")
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10
    inlink = world.get_link("in")
    outlink = world.get_link("out")
    far_link = world.get_link("far")
    merge = world.get_node("merge")
    _place(vehicle, inlink, outlink)
    _place(far_vehicle, far_link, None)
    vehicle.begin_order_control_visit_on_link_entry()
    inlink.vehicles.append(vehicle)
    far_link.vehicles.append(far_vehicle)
    merge.incoming_vehicles.append(vehicle)
    merge.flow_capacity_remain = 0.0
    merge.last_order_control_inlink = inlink
    merge.last_order_control_entry_timestep = 4
    merge.order_control_clearance_timesteps = 2
    inlink.capacity_out_remain = 0.0
    inlink.capacity_in_remain = 0.1
    outlink.capacity_out_remain = 0.0
    outlink.capacity_in_remain = 0.0
    far_link.capacity_out_remain = 1.25
    far_link.capacity_in_remain = 1.25
    visit = OrderControlTvtMpLocalBindingRankVisit(
        visit_key=(vehicle.name, vehicle.order_control_current_visit["visit_id"]),
        vehicle_id=vehicle.id,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        binding_rank=1,
        route_next_link_name="out",
        route_origin=(
            OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
        ),
        inlink_name="in",
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.2,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
    )
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(("in_front", 1),),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=(visit,),
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=(visit,),
        k_last_buyer=1,
        k_decision_window=1,
        k_fixed=1,
    )
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    return world, local_state


def _unchanged_traffic(local_state) -> dict:
    vehicle = local_state.local_vehicles[0]
    node = local_state.target_node
    return {
        "x": vehicle.x,
        "v": vehicle.v,
        "lane": vehicle.lane,
        "leader": vehicle.leader,
        "follower": vehicle.follower,
        "incoming": [item.name for item in node.incoming_vehicles],
        "clearance_link": node.last_order_control_inlink,
        "clearance_time": node.last_order_control_entry_timestep,
        "clearance_count": node.order_control_clearance_timesteps,
        "pairs": local_state.binding_visit_local_vehicle_pairs,
    }


def test_initialize_starts_at_offset_zero_without_refill():
    world, local_state = _local_state()
    before_capacity = (
        local_state.target_node.flow_capacity_remain,
        local_state.inlinks[0].capacity_out_remain,
        local_state.inlinks[0].capacity_in_remain,
        local_state.outlinks[0].capacity_out_remain,
    )
    before_traffic = _unchanged_traffic(local_state)
    before_far = world.get_link("far").capacity_out_remain
    arrival_before = list(local_state.inlinks[0].cum_arrival)
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    assert isinstance(clock, OrderControlTvtMpCandidateVirtualTimeState)
    assert clock.current_offset == 0
    assert clock.current_virtual_timestep == 10
    assert clock.simulated_timestep_count == 0
    assert clock.baseline_timestep_T == 10
    assert local_state.local_world.T == 10
    assert (
        local_state.target_node.flow_capacity_remain,
        local_state.inlinks[0].capacity_out_remain,
        local_state.inlinks[0].capacity_in_remain,
        local_state.outlinks[0].capacity_out_remain,
    ) == before_capacity
    assert _unchanged_traffic(local_state) == before_traffic
    assert world.get_link("far").capacity_out_remain == before_far
    assert local_state.inlinks[0].cum_arrival[: len(arrival_before)] == arrival_before
    assert len(local_state.inlinks[0].cum_arrival) == 11
    assert len(local_state.inlinks[0].cum_departure) == 11


def test_one_step_refills_local_capacity_once():
    _world_object, local_state = _local_state()
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    deltat = local_state.local_world.DELTAT
    inlink = local_state.inlinks[0]
    outlink = local_state.outlinks[0]
    side = local_state.outlinks[1]
    far = local_state.local_world.get_link("far")
    before_far_arrival = list(far.cum_arrival)
    before_traveltime = inlink.traveltime_actual.copy()
    before_enter_log = dict(inlink.vehicles_enter_log)
    before_traffic = _unchanged_traffic(local_state)
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    assert clock.current_offset == 1
    assert clock.current_virtual_timestep == 11
    assert clock.simulated_timestep_count == 1
    assert local_state.local_world.T == 11
    assert inlink.capacity_out_remain == 0.0 + inlink.capacity_out * deltat
    assert inlink.capacity_in_remain == 0.1 + inlink.capacity_in * deltat
    assert outlink.capacity_in_remain == 0.0 + outlink.capacity_in * deltat
    assert local_state.target_node.flow_capacity_remain == (
        0.0 + local_state.target_node.flow_capacity * deltat
    )
    assert len(inlink.cum_arrival) == 12
    assert inlink.cum_arrival[10] == inlink.cum_arrival[9]
    assert list(inlink.traveltime_actual) == list(before_traveltime)
    assert inlink.vehicles_enter_log == before_enter_log
    assert far.cum_arrival == before_far_arrival
    assert far.capacity_out_remain == 1.25
    assert side.name == "side"
    assert _unchanged_traffic(local_state) == before_traffic


def test_repeated_steps_are_one_timestep_each():
    _world_object, local_state = _local_state()
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    inlink = local_state.inlinks[0]
    expected_out_remain = inlink.capacity_out_remain
    added_each_step = inlink.capacity_out * local_state.local_world.DELTAT
    for step_number in range(1, 4):
        advance_tvt_mp_candidate_virtual_time_one_step(clock)
        expected_out_remain += added_each_step
        assert clock.current_offset == step_number
        assert clock.current_virtual_timestep == 10 + step_number
        assert clock.simulated_timestep_count == step_number
        assert local_state.local_world.T == 10 + step_number
        assert inlink.capacity_out_remain == expected_out_remain
        assert len(inlink.cum_arrival) == 10 + step_number + 1


def test_remainder_at_or_above_threshold_is_not_refilled():
    _world_object, local_state = _local_state()
    inlink = local_state.inlinks[0]
    threshold = local_state.local_world.DELTAN * inlink.number_of_lanes
    inlink.capacity_out_remain = threshold
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    assert inlink.capacity_out_remain == threshold


def test_unset_capacity_uses_uxsim_unlimited_sentinel():
    _world_object, local_state = _local_state()
    side = local_state.outlinks[1]
    side.capacity_in = None
    side.capacity_out_remain = 3.0
    side.capacity_in_remain = 4.0
    local_state.target_node.flow_capacity = None
    local_state.target_node.flow_capacity_remain = 1.0
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    assert side.capacity_out_remain == 3.0
    assert local_state.target_node.flow_capacity_remain == 1.0
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    assert side.capacity_out_remain == 10e10
    assert side.capacity_in_remain == 10e10
    assert local_state.target_node.flow_capacity_remain == 10e10


def test_clock_mismatch_does_not_refill():
    _world_object, local_state = _local_state()
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    before_remain = local_state.inlinks[0].capacity_out_remain
    before_length = len(local_state.inlinks[0].cum_arrival)
    local_state.local_world.T = 99
    try:
        advance_tvt_mp_candidate_virtual_time_one_step(clock)
        raise AssertionError("expected clock mismatch RuntimeError")
    except RuntimeError as exc:
        assert "99" in str(exc)
    assert clock.current_offset == 0
    assert local_state.inlinks[0].capacity_out_remain == before_remain
    assert len(local_state.inlinks[0].cum_arrival) == before_length


def test_initial_timestep_mismatch_is_value_error():
    _world_object, local_state = _local_state()
    local_state.local_world.T = 11
    before_remain = local_state.inlinks[0].capacity_out_remain
    try:
        initialize_tvt_mp_candidate_virtual_time_state(local_state)
        raise AssertionError("expected timestep ValueError")
    except ValueError as exc:
        assert "11" in str(exc)
    assert local_state.inlinks[0].capacity_out_remain == before_remain


def test_bad_deltat_is_value_error_without_refill():
    _world_object, local_state = _local_state()
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    before_remain = local_state.inlinks[0].capacity_out_remain
    local_state.local_world.DELTAT = True
    try:
        advance_tvt_mp_candidate_virtual_time_one_step(clock)
        raise AssertionError("expected DELTAT ValueError")
    except ValueError as exc:
        assert "DELTAT" in str(exc)
    assert clock.current_offset == 0
    assert local_state.local_world.T == 10
    assert local_state.inlinks[0].capacity_out_remain == before_remain


def test_bad_cumulative_array_is_runtime_error_without_clock_move():
    _world_object, local_state = _local_state()
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    local_state.inlinks[0].cum_arrival = "broken"
    before_remain = local_state.inlinks[0].capacity_out_remain
    try:
        advance_tvt_mp_candidate_virtual_time_one_step(clock)
        raise AssertionError("expected cumulative array RuntimeError")
    except RuntimeError as exc:
        assert "cum_arrival" in str(exc)
    assert clock.current_offset == 0
    assert local_state.local_world.T == 10
    assert local_state.inlinks[0].capacity_out_remain == before_remain


def test_other_candidate_and_real_world_stay_unchanged():
    world, local_state = _local_state()
    other = build_tvt_mp_candidate_local_state(
        world,
        local_state.binding_rank_sequence,
    )
    real_x = world.VEHICLES["in_front"].x
    real_rng = copy.deepcopy(world.rng.bit_generator.state)
    other_remain = other.inlinks[0].capacity_out_remain
    other_t = other.local_world.T
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    assert world.VEHICLES["in_front"].x == real_x
    assert world.T == 10
    assert world.rng.bit_generator.state == real_rng
    assert other.local_world.T == other_t
    assert other.inlinks[0].capacity_out_remain == other_remain
    assert other.inlinks[0] is not local_state.inlinks[0]


def test_update_and_transfer_methods_are_not_called():
    _world_object, local_state = _local_state()
    called = []
    local_state.local_world.exec_simulation = lambda *args, **kwargs: called.append(
        "exec"
    )
    local_state.target_node.update = lambda *args, **kwargs: called.append("node")
    local_state.target_node.transfer = lambda *args, **kwargs: called.append("transfer")
    for link in local_state.inlinks + local_state.outlinks:
        link.update = lambda *args, **kwargs: called.append("link")
    for vehicle in local_state.local_vehicles:
        vehicle.update = lambda *args, **kwargs: called.append("vehicle")
        vehicle.carfollow = lambda *args, **kwargs: called.append("carfollow")
        vehicle.end_trip = lambda *args, **kwargs: called.append("end")
        vehicle.route_next_link_choice = lambda *args, **kwargs: called.append("route")
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    assert called == []


def test_candidate_local_state_type_error_is_value_error():
    try:
        initialize_tvt_mp_candidate_virtual_time_state(object())  # type: ignore[arg-type]
        raise AssertionError("expected type ValueError")
    except ValueError as exc:
        assert "candidate_local_state" in str(exc)


TESTS = (
    test_initialize_starts_at_offset_zero_without_refill,
    test_one_step_refills_local_capacity_once,
    test_repeated_steps_are_one_timestep_each,
    test_remainder_at_or_above_threshold_is_not_refilled,
    test_unset_capacity_uses_uxsim_unlimited_sentinel,
    test_clock_mismatch_does_not_refill,
    test_initial_timestep_mismatch_is_value_error,
    test_bad_deltat_is_value_error_without_refill,
    test_bad_cumulative_array_is_runtime_error_without_clock_move,
    test_other_candidate_and_real_world_stay_unchanged,
    test_update_and_transfer_methods_are_not_called,
    test_candidate_local_state_type_error_is_value_error,
)


if __name__ == "__main__":
    for test_function in TESTS:
        test_function()
    print(f"candidate virtual time tests passed ({len(TESTS)} tests).")
