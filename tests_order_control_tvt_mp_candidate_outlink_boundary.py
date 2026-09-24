# Tests for TVT-MP outlink terminal boundary handling.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_outlink_boundary.py

from __future__ import annotations

import dataclasses

from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_local_vehicle_advance import (
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals,
    initialize_tvt_mp_candidate_local_vehicle_advance_state,
)
from uxsim.order_control_tvt_mp_candidate_outlink_boundary import (
    OrderControlTvtMpCandidateOutlinkBoundaryLinkState,
    OrderControlTvtMpCandidateOutlinkBoundaryState,
    OrderControlTvtMpOutlinkBoundaryLinkProcessResult,
    OrderControlTvtMpOutlinkBoundaryMode,
    OrderControlTvtMpOutlinkBoundaryProcessResult,
    OrderControlTvtMpOutlinkBoundaryRemovalKind,
    OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord,
    initialize_tvt_mp_candidate_outlink_boundary_state,
    process_tvt_mp_candidate_outlink_boundaries_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_virtual_time import (
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
from uxsim.uxsim import Vehicle, World


def _binding_visit(vehicle, *, rank: int, route_name: str, inlink_name: str):
    current_visit = vehicle.order_control_current_visit
    return OrderControlTvtMpLocalBindingRankVisit(
        visit_key=(vehicle.name, current_visit["visit_id"]),
        vehicle_id=vehicle.id,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        binding_rank=rank,
        route_next_link_name=route_name,
        route_origin=(
            OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
        ),
        inlink_name=inlink_name,
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.2,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
    )


def _new_world(name: str) -> World:
    world = World(
        name=name,
        deltan=1,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig_a", 0, 0)
    world.addNode("orig_b", 0, 1)
    world.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
        flow_capacity=1.0,
        number_of_lanes=1,
    )
    world.addNode("dest", 2, 0)
    world.addNode("dest_b", 2, 1)
    world.addNode("west", 0, 2)
    world.addNode("sink", 1, 2)
    world.addLink(
        "in_a", "orig_a", "merge", length=200, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "in_b", "orig_b", "merge", length=200, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "far", "west", "sink", length=200, free_flow_speed=20, number_of_lanes=1
    )
    return world


def _place(world, vehicle, link, route_link, *, x: float) -> None:
    vehicle.link = link
    vehicle.state = "run"
    vehicle.x = x
    vehicle.x_old = x
    vehicle.x_next = x
    vehicle.v = 4.0
    vehicle.lane = 0
    vehicle.leader = None
    vehicle.follower = None
    vehicle.route_next_link = route_link
    vehicle.link_arrival_time = 5.0
    vehicle.move_remain = 2.0
    vehicle.flag_waiting_for_trip_end = 0
    world.VEHICLES_RUNNING[vehicle.name] = vehicle


def _record_existing_arrival(vehicle, node, arrival_time: float, tiebreaker: float) -> None:
    current_visit = vehicle.order_control_current_visit
    current_visit["arrival_time"] = arrival_time
    current_visit["arrival_tiebreaker"] = tiebreaker
    vehicle.order_control_node_arrival_times[node.name] = arrival_time
    vehicle.order_control_node_arrival_tiebreakers[node.name] = tiebreaker


def _sequence(visits):
    buyer_keys = []
    for visit in visits:
        buyer_keys.append(visit.visit_key)
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(buyer_keys[0],),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=visits,
        k_last_buyer=1,
        k_decision_window=len(visits),
        k_fixed=len(visits),
    )


def _open_capacities(local_state) -> None:
    local_state.target_node.flow_capacity_remain = 10.0
    for link in local_state.inlinks + local_state.outlinks:
        link.capacity_out_remain = 10.0
        link.capacity_in_remain = 10.0


def _prepare(world, visits):
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10
    sequence = _sequence(visits)
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    transfer_state = __import__(
        "uxsim.order_control_tvt_mp_candidate_binding_transfer",
        fromlist=["initialize_tvt_mp_candidate_binding_transfer_state"],
    ).initialize_tvt_mp_candidate_binding_transfer_state(clock)
    local_state.local_world.get_link("in_a").capacity_out_remain = 0.0
    scan_result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    advance_state = initialize_tvt_mp_candidate_local_vehicle_advance_state(
        transfer_state
    )
    advance_result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    return local_state, transfer_state, advance_state, advance_result


def _local_vehicle(local_state, vehicle_name: str):
    return local_state.local_vehicle_by_real_vehicle_name[vehicle_name]


def _outlink_result(name: str, terminal: str, active: int, transferred: int):
    return OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name=name,
        terminal_node_name=terminal,
        active_timestep_count=active,
        transferred_vehicle_count=transferred,
    )


def _make_node_result(*outlink_results):
    return OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="merge",
        outlink_results=tuple(outlink_results),
    )


def _park_at_outlink_end(local_state, vehicle_names, outlink_name: str) -> list:
    local_world = local_state.local_world
    outlink = local_world.get_link(outlink_name)
    parked = []
    previous = None
    for vehicle_name in vehicle_names:
        vehicle = _local_vehicle(local_state, vehicle_name)
        if vehicle.link is not None and vehicle in list(vehicle.link.vehicles):
            vehicle.link.vehicles.remove(vehicle)
        incoming = local_state.target_node.incoming_vehicles
        incoming[:] = [queued for queued in incoming if queued is not vehicle]
        vehicle.link = outlink
        vehicle.state = "run"
        vehicle.x = outlink.length
        vehicle.x_old = outlink.length
        vehicle.x_next = outlink.length
        vehicle.v = 4.0
        vehicle.move_remain = 2.0
        vehicle.leader = previous
        vehicle.follower = None
        vehicle.order_control_current_visit = None
        if previous is not None:
            previous.follower = vehicle
        outlink.vehicles.append(vehicle)
        previous = vehicle
        parked.append(vehicle)
    return parked


def _started(active_by_outlink):
    world = _new_world("boundary")
    first = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second = world.addVehicle("orig_a", "dest", 0, name="second_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    merge = world.get_node("merge")
    _place(world, first, in_a, outlink, x=10)
    _place(world, second, in_a, outlink, x=0)
    first.follower = second
    second.leader = first
    in_a.vehicles.append(first)
    in_a.vehicles.append(second)
    first.begin_order_control_visit_on_link_entry()
    second.begin_order_control_visit_on_link_entry()
    del merge
    visits = (
        _binding_visit(first, rank=1, route_name="out", inlink_name="in_a"),
        _binding_visit(second, rank=2, route_name="out", inlink_name="in_a"),
    )
    local_state, transfer_state, advance_state, advance_result = _prepare(
        world,
        visits,
    )
    observed = []
    for outlink in local_state.outlinks:
        active, transferred = active_by_outlink[outlink.name]
        observed.append(
            _outlink_result(
                outlink.name,
                outlink.end_node.name,
                active,
                transferred,
            )
        )
    node_result = _make_node_result(*observed)
    boundary_state = initialize_tvt_mp_candidate_outlink_boundary_state(
        advance_state,
        node_result,
    )
    return world, local_state, transfer_state, advance_result, boundary_state, node_result


def _assert_removal_record_fields(record) -> None:
    names = [field.name for field in dataclasses.fields(record)]
    assert names == [
        "vehicle_name",
        "outlink_name",
        "terminal_node_name",
        "virtual_timestep",
        "boundary_exit_time_seconds",
        "removal_kind",
    ]
    assert not hasattr(record, "visit_key")
    assert not hasattr(record, "current_visit_key_at_removal")


def test_public_types_are_frozen_and_removal_record_has_six_fields():
    assert OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITH_OUTFLOW
    assert OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
    assert OrderControlTvtMpOutlinkBoundaryMode.NO_OBSERVED_WAIT_CONSTRAINED_SINK
    assert (
        OrderControlTvtMpOutlinkBoundaryRemovalKind.OBSERVED_OUTFLOW_BOUNDARY_EXIT
    )
    assert OrderControlTvtMpOutlinkBoundaryRemovalKind.CONSTRAINED_SINK_END_TRIP
    record = OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord(
        vehicle_name="first_veh",
        outlink_name="out",
        terminal_node_name="dest",
        virtual_timestep=10,
        boundary_exit_time_seconds=55.0,
        removal_kind=(
            OrderControlTvtMpOutlinkBoundaryRemovalKind.OBSERVED_OUTFLOW_BOUNDARY_EXIT
        ),
    )
    _assert_removal_record_fields(record)
    assert dataclasses.is_dataclass(record) and record.__dataclass_params__.frozen
    result = OrderControlTvtMpOutlinkBoundaryProcessResult(
        node_name="merge",
        virtual_timestep=10,
        outlink_results=(),
    )
    link_result = OrderControlTvtMpOutlinkBoundaryLinkProcessResult(
        outlink_name="out",
        terminal_node_name="dest",
        boundary_mode=OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITH_OUTFLOW,
        flow_allowance_before=0,
        flow_allowance_added=0,
        flow_allowance_after=0,
        vehicle_names_at_end_before=(),
        observed_outflow_boundary_exit_vehicle_names=(),
        constrained_sink_end_trip_vehicle_names=(),
        waiting_vehicle_names_after=(),
        capacity_out_remain_before=1,
        capacity_out_remain_after=1,
        terminal_node_flow_capacity_remain_before=1,
        terminal_node_flow_capacity_remain_after=1,
    )
    assert result.__dataclass_params__.frozen
    assert link_result.__dataclass_params__.frozen
    assert isinstance(link_result.vehicle_names_at_end_before, tuple)
    try:
        record.vehicle_name = "other"
        raise AssertionError("removal record must be frozen")
    except dataclasses.FrozenInstanceError:
        pass


def test_initialization_matches_node_outlink_order_and_modes():
    _world, local_state, _transfer, _advance_result, boundary_state, node_result = (
        _started({"out": (4, 2), "side": (3, 0)})
    )
    assert boundary_state.downstream_boundary_node_result is node_result
    assert [state.outlink_name for state in boundary_state.outlink_states] == [
        link.name for link in local_state.outlinks
    ]
    by_name = {state.outlink_name: state for state in boundary_state.outlink_states}
    assert (
        by_name["out"].boundary_mode
        is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITH_OUTFLOW
    )
    assert by_name["out"].observed_average_outflow_rate == 2 / 4
    assert by_name["out"].flow_allowance == 0
    assert (
        by_name["side"].boundary_mode
        is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
    )
    assert by_name["side"].observed_average_outflow_rate is None
    assert by_name["side"].flow_allowance == 0
    assert by_name["out"].terminal_node_name == "dest"
    assert isinstance(
        boundary_state.outlink_states[0],
        OrderControlTvtMpCandidateOutlinkBoundaryLinkState,
    )
    assert isinstance(boundary_state, OrderControlTvtMpCandidateOutlinkBoundaryState)
    before = (
        local_state.local_world.T,
        list(local_state.local_world.get_link("out").cum_departure),
        local_state.local_world.get_link("out").capacity_out_remain,
    )
    assert before[0] == 10
    assert node_result.outlink_results[0].active_timestep_count == 4


def test_missing_boundary_result_is_not_active_zero():
    world, local_state, _transfer, _advance_result, boundary_state, _observed = (
        _started({"out": (0, 0), "side": (0, 0)})
    )
    advance_state = boundary_state.local_vehicle_advance_state
    try:
        initialize_tvt_mp_candidate_outlink_boundary_state(advance_state, None)
        raise AssertionError("None must be RuntimeError")
    except RuntimeError as error:
        assert "missing" in str(error)
    sink_state = initialize_tvt_mp_candidate_outlink_boundary_state(
        advance_state,
        _make_node_result(
            _outlink_result("out", "dest", 0, 0),
            _outlink_result("side", "dest_b", 0, 0),
        ),
    )
    assert (
        sink_state.outlink_states[0].boundary_mode
        is OrderControlTvtMpOutlinkBoundaryMode.NO_OBSERVED_WAIT_CONSTRAINED_SINK
    )
    assert world.get_link("out").capacity_out_remain != local_state.local_world.get_link(
        "out"
    ).capacity_out_remain or world is not local_state.local_world


def test_initialization_rejects_reordered_outlinks_without_repair():
    _world, _local_state, _transfer, _advance_result, boundary_state, _node_result = (
        _started({"out": (1, 1), "side": (1, 0)})
    )
    advance_state = boundary_state.local_vehicle_advance_state
    swapped = _make_node_result(
        _outlink_result("side", "dest_b", 1, 0),
        _outlink_result("out", "dest", 1, 1),
    )
    try:
        initialize_tvt_mp_candidate_outlink_boundary_state(advance_state, swapped)
        raise AssertionError("order mismatch must fail")
    except RuntimeError as error:
        assert "order" in str(error)


def test_observed_outflow_exits_without_end_trip_or_visit_key():
    _world, local_state, transfer_state, advance_result, boundary_state, node_result = (
        _started({"out": (1, 2), "side": (1, 0)})
    )
    local_world = local_state.local_world
    parked = _park_at_outlink_end(local_state, ["first_veh", "second_veh"], "out")
    first, second = parked
    assert first.order_control_current_visit is None
    visit_id_before = first.order_control_visit_id
    arrival_before = first.arrival_time
    travel_before = first.travel_time
    link_arrival_before = first.link_arrival_time
    route_before = first.route_next_link
    flag_before = first.flag_waiting_for_trip_end
    x_before = (first.x, first.x_old, first.x_next, first.v, first.move_remain)
    end_trip_calls = {"n": 0}
    log_calls = {"n": 0}
    original_end_trip = Vehicle.end_trip
    original_record_log = Vehicle.record_log

    def _count_end_trip(self):
        end_trip_calls["n"] += 1
        return original_end_trip(self)

    def _count_log(self, enforce_log=0):
        log_calls["n"] += 1
        return original_record_log(self, enforce_log)

    Vehicle.end_trip = _count_end_trip
    Vehicle.record_log = _count_log
    outlink = local_world.get_link("out")
    dest = local_world.get_node("dest")
    assert dest.flow_capacity is None
    unlimited_before = dest.flow_capacity_remain
    downstream_in_before = local_world.get_link("far").capacity_in_remain
    cum_before = list(outlink.cum_departure)
    assert len(cum_before) == local_world.T + 1
    incoming_before = list(local_state.target_node.incoming_vehicles)
    dest_incoming_before = list(dest.incoming_vehicles)
    transferred_before = transfer_state.transferred_binding_visit_keys
    advance_completed_before = boundary_state.local_vehicle_advance_state.completed_virtual_timesteps
    outlink.capacity_out_remain = 5
    counts_before = (
        node_result.outlink_results[0].active_timestep_count,
        node_result.outlink_results[0].transferred_vehicle_count,
    )
    try:
        result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
    finally:
        Vehicle.end_trip = original_end_trip
        Vehicle.record_log = original_record_log
    assert end_trip_calls["n"] == 0
    assert log_calls["n"] == 0
    out_result = result.outlink_results[0]
    assert out_result.observed_outflow_boundary_exit_vehicle_names == (
        "first_veh",
        "second_veh",
    )
    assert out_result.flow_allowance_added == 2
    assert out_result.flow_allowance_before == 0
    assert out_result.flow_allowance_after == 0
    assert outlink.capacity_out_remain == 3
    assert dest.flow_capacity_remain == unlimited_before
    assert local_world.get_link("far").capacity_in_remain == downstream_in_before
    assert outlink.cum_departure[-1] == cum_before[-1] + 2 * local_world.DELTAN
    start = int(link_arrival_before / local_world.DELTAT)
    expected_travel = (local_world.T + 1) * local_world.DELTAT - link_arrival_before
    assert outlink.traveltime_actual[start] == expected_travel
    assert first.arrival_time == arrival_before
    assert first.travel_time == travel_before
    assert first.link_arrival_time == link_arrival_before
    assert (first.x, first.x_old, first.x_next, first.v, first.move_remain) == x_before
    assert first.route_next_link is route_before
    assert first.flag_waiting_for_trip_end == flag_before
    assert first.order_control_current_visit is None
    assert first.order_control_visit_id == visit_id_before
    assert local_world.VEHICLES[first.name] is first
    assert first.name not in local_world.VEHICLES_RUNNING
    assert first.name not in local_world.VEHICLES_LIVING
    assert first.state == "end"
    assert first.link is None
    assert first.leader is None
    assert first.follower is None
    assert second.leader is None
    assert list(outlink.vehicles) == []
    assert len(boundary_state.vehicle_removal_records) == 2
    _assert_removal_record_fields(boundary_state.vehicle_removal_records[0])
    assert boundary_state.vehicle_removal_records[0].removal_kind is (
        OrderControlTvtMpOutlinkBoundaryRemovalKind.OBSERVED_OUTFLOW_BOUNDARY_EXIT
    )
    assert boundary_state.vehicle_removal_records[0].vehicle_name == "first_veh"
    assert boundary_state.vehicle_removal_records[0].boundary_exit_time_seconds == (
        (local_world.T + 1) * local_world.DELTAT
    )
    assert list(local_state.target_node.incoming_vehicles) == incoming_before
    assert list(dest.incoming_vehicles) == dest_incoming_before
    assert transfer_state.transferred_binding_visit_keys == transferred_before
    assert (
        boundary_state.local_vehicle_advance_state.completed_virtual_timesteps
        == advance_completed_before
    )
    assert local_world.T == 10
    assert counts_before == (1, 2)
    assert boundary_state.outlink_states[0].cumulative_observed_outflow_exit_vehicle_names == (
        "first_veh",
        "second_veh",
    )


def test_allowance_waits_and_carries_fraction_then_next_timestep():
    _world, local_state, transfer_state, advance_result, boundary_state, _node_result = (
        _started({"out": (5, 2), "side": (1, 0)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    outlink = local_state.local_world.get_link("out")
    outlink.capacity_out_remain = 5
    first = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert first.outlink_results[0].observed_outflow_boundary_exit_vehicle_names == ()
    assert first.outlink_results[0].waiting_vehicle_names_after == ("first_veh",)
    assert first.outlink_results[0].flow_allowance_after == 0.4
    assert boundary_state.outlink_states[0].flow_allowance == 0.4
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("second call must fail")
    except RuntimeError:
        assert boundary_state.outlink_states[0].flow_allowance == 0.4
    clock = transfer_state.virtual_time_state
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    next_timestep = clock.current_virtual_timestep
    boundary_state.local_vehicle_advance_state._completed_virtual_timesteps.append(
        next_timestep
    )
    next_advance = type(advance_result)(
        node_name=advance_result.node_name,
        virtual_timestep=next_timestep,
        advanced_vehicle_names=(),
        preexisting_incoming_vehicle_names=(),
        newly_arrived_vehicle_names=(),
        newly_arrived_binding_visit_keys=(),
        incoming_vehicle_names_before=(),
        incoming_vehicle_names_after=(),
    )
    # Clock refill must not be treated as the boundary adding capacity.
    outlink.capacity_out_remain = 5
    second = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        next_advance,
    )
    assert second.outlink_results[0].flow_allowance_before == 0.4
    assert second.outlink_results[0].flow_allowance_added == 0.4
    assert second.outlink_results[0].observed_outflow_boundary_exit_vehicle_names == ()
    assert boundary_state.outlink_states[0].flow_allowance == 0.8


def test_integer_allowance_is_not_reset_when_capacity_blocks_exit():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 2), "side": (1, 0)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    local_state.local_world.get_link("out").capacity_out_remain = 0
    result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert result.outlink_results[0].flow_allowance_added == 2
    assert result.outlink_results[0].flow_allowance_after == 2
    assert result.outlink_results[0].observed_outflow_boundary_exit_vehicle_names == ()
    assert result.outlink_results[0].capacity_out_remain_after == 0
    assert boundary_state.vehicle_removal_records == ()


def test_finite_terminal_capacity_is_consumed_and_shortage_waits():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 3), "side": (1, 0)})
    )
    parked = _park_at_outlink_end(local_state, ["first_veh", "second_veh"], "out")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    dest = local_world.get_node("dest")
    dest.flow_capacity = 1.0
    dest.flow_capacity_remain = local_world.DELTAN
    outlink.capacity_out_remain = 5
    result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert result.outlink_results[0].observed_outflow_boundary_exit_vehicle_names == (
        "first_veh",
    )
    assert result.outlink_results[0].waiting_vehicle_names_after == ("second_veh",)
    assert dest.flow_capacity_remain == 0
    assert outlink.capacity_out_remain == 4
    assert parked[1].link is outlink
    assert parked[1].leader is None
    assert result.outlink_results[0].flow_allowance_after == 2


def test_head_not_at_end_does_not_exit_the_follower():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 5), "side": (1, 0)})
    )
    parked = _park_at_outlink_end(local_state, ["first_veh", "second_veh"], "out")
    parked[0].x = parked[0].link.length - 10
    result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert result.outlink_results[0].observed_outflow_boundary_exit_vehicle_names == ()
    assert result.outlink_results[0].vehicle_names_at_end_before == ()
    assert parked[1].link is local_state.local_world.get_link("out")
    assert parked[1].state == "run"


def test_wait_without_outflow_keeps_vehicles_and_allowance():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (4, 0), "side": (1, 1)})
    )
    parked = _park_at_outlink_end(local_state, ["first_veh"], "out")
    outlink = local_state.local_world.get_link("out")
    cum_before = list(outlink.cum_departure)
    travel_before = outlink.traveltime_actual.copy()
    capacity_before = outlink.capacity_out_remain
    result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    out_result = result.outlink_results[0]
    assert (
        out_result.boundary_mode
        is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
    )
    assert out_result.flow_allowance_added == 0
    assert out_result.flow_allowance_after == 0
    assert out_result.waiting_vehicle_names_after == ("first_veh",)
    assert out_result.observed_outflow_boundary_exit_vehicle_names == ()
    assert list(outlink.cum_departure) == cum_before
    assert (outlink.traveltime_actual == travel_before).all()
    assert outlink.capacity_out_remain == capacity_before
    assert parked[0].state == "run"
    assert parked[0].link is outlink
    assert boundary_state.vehicle_removal_records == ()


def test_constrained_sink_calls_end_trip_once_per_vehicle_without_visit_key():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (0, 0), "side": (2, 1)})
    )
    parked = _park_at_outlink_end(local_state, ["first_veh", "second_veh"], "out")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    dest = local_world.get_node("dest")
    dest.flow_capacity = 1.0
    dest.flow_capacity_remain = 2 * local_world.DELTAN
    outlink.capacity_out_remain = 2 * local_world.DELTAN
    downstream_in = local_world.get_link("in_b").capacity_in_remain
    cum_before = outlink.cum_departure[-1]
    end_trip_calls = {"n": 0}
    original_end_trip = Vehicle.end_trip

    def _count_end_trip(self):
        end_trip_calls["n"] += 1
        cum_at_entry = self.link.cum_departure[-1]
        original_end_trip(self)
        assert self.link is None
        assert outlink.cum_departure[-1] == cum_at_entry + local_world.DELTAN

    Vehicle.end_trip = _count_end_trip
    try:
        result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
    finally:
        Vehicle.end_trip = original_end_trip
    assert end_trip_calls["n"] == 2
    assert result.outlink_results[0].constrained_sink_end_trip_vehicle_names == (
        "first_veh",
        "second_veh",
    )
    assert result.outlink_results[0].flow_allowance_added == 0
    assert result.outlink_results[0].flow_allowance_after == 0
    assert outlink.capacity_out_remain == 0
    assert dest.flow_capacity_remain == 0
    assert outlink.cum_departure[-1] == cum_before + 2 * local_world.DELTAN
    assert local_world.get_link("in_b").capacity_in_remain == downstream_in
    assert boundary_state.vehicle_removal_records[0].removal_kind is (
        OrderControlTvtMpOutlinkBoundaryRemovalKind.CONSTRAINED_SINK_END_TRIP
    )
    assert parked[0].order_control_current_visit is None
    _assert_removal_record_fields(boundary_state.vehicle_removal_records[1])
    assert (
        boundary_state.outlink_states[0].cumulative_constrained_sink_end_trip_vehicle_names
        == ("first_veh", "second_veh")
    )


def test_constrained_sink_waits_when_capacity_is_short():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (0, 0), "side": (1, 0)})
    )
    parked = _park_at_outlink_end(local_state, ["first_veh"], "out")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    dest = local_world.get_node("dest")
    dest.flow_capacity = 1.0
    dest.flow_capacity_remain = 0
    outlink.capacity_out_remain = 5
    result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert result.outlink_results[0].constrained_sink_end_trip_vehicle_names == ()
    assert parked[0].state == "run"
    assert parked[0].link is outlink
    assert dest.flow_capacity_remain == 0
    assert outlink.capacity_out_remain == 5


def test_cum_departure_length_mismatch_changes_nothing():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 1), "side": (1, 0)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    outlink = local_state.local_world.get_link("out")
    outlink.cum_departure.pop()
    allowance_before = boundary_state.outlink_states[0].flow_allowance
    vehicles_before = list(outlink.vehicles)
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("bad cum_departure length must fail")
    except RuntimeError as error:
        assert "cum_departure" in str(error)
    assert boundary_state.outlink_states[0].flow_allowance == allowance_before
    assert list(outlink.vehicles) == vehicles_before
    assert boundary_state.completed_virtual_timesteps == ()
    assert boundary_state.vehicle_removal_records == ()


def test_head_leader_is_rejected_before_allowance_changes():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 1), "side": (1, 0)})
    )
    parked = _park_at_outlink_end(local_state, ["first_veh"], "out")
    parked[0].leader = parked[0]
    outlink = local_state.local_world.get_link("out")
    cum_before = list(outlink.cum_departure)
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("leader on the head must fail")
    except RuntimeError:
        pass
    assert boundary_state.outlink_states[0].flow_allowance == 0
    assert list(outlink.cum_departure) == cum_before
    assert parked[0].state == "run"


def test_dedicated_exit_rollback_restores_the_outlink_only():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 3), "side": (1, 1)})
    )

    class _BoomTravelTime:
        def __init__(self, values):
            self.values = list(values)

        def __len__(self):
            return len(self.values)

        def __getitem__(self, item):
            return self.values[item]

        def __setitem__(self, key, value):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                raise RuntimeError("traveltime failed")
            self.values[:] = list(value)

    _park_at_outlink_end(local_state, ["first_veh"], "out")
    _park_at_outlink_end(local_state, ["second_veh"], "side")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    side = local_world.get_link("side")
    outlink.capacity_out_remain = 5
    side.capacity_out_remain = 5
    side.traveltime_actual = _BoomTravelTime(side.traveltime_actual)
    out_cum_before = list(outlink.cum_departure)
    side_vehicles = list(side.vehicles)
    side_capacity = side.capacity_out_remain
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("side failure must propagate")
    except RuntimeError as error:
        assert "traveltime failed" in str(error)
    first = _local_vehicle(local_state, "first_veh")
    second = _local_vehicle(local_state, "second_veh")
    assert first.state == "end"
    assert first.name not in local_world.VEHICLES_RUNNING
    assert outlink.cum_departure[-1] == out_cum_before[-1] + local_world.DELTAN
    assert list(side.vehicles) == side_vehicles
    assert side.capacity_out_remain == side_capacity
    assert second.state == "run"
    assert second.link is side
    assert [record.vehicle_name for record in boundary_state.vehicle_removal_records] == [
        "first_veh"
    ]
    assert boundary_state.completed_virtual_timesteps == ()
    assert local_world.T in boundary_state.outlink_states[0].completed_virtual_timesteps
    assert boundary_state.outlink_states[0].completed_process_result(local_world.T) is not None
    assert local_world.T not in boundary_state.outlink_states[1].completed_virtual_timesteps


def test_end_trip_failure_rolls_back_that_outlink():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 1), "side": (0, 0)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    _park_at_outlink_end(local_state, ["second_veh"], "side")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    side = local_world.get_link("side")
    for link in (outlink, side):
        link.capacity_out_remain = 5
    dest = local_world.get_node("dest")
    dest_b = local_world.get_node("dest_b")
    dest.flow_capacity = 1.0
    dest.flow_capacity_remain = 5
    dest_b.flow_capacity = 1.0
    dest_b.flow_capacity_remain = 5
    original_end_trip = Vehicle.end_trip
    calls = {"n": 0}

    def _end_trip(self):
        calls["n"] += 1
        if self.name == "second_veh":
            raise RuntimeError("end_trip failed")
        return original_end_trip(self)

    Vehicle.end_trip = _end_trip
    side_capacity = side.capacity_out_remain
    second = _local_vehicle(local_state, "second_veh")
    second_arrival = second.arrival_time
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("end_trip failure must propagate")
    except RuntimeError as error:
        assert "end_trip failed" in str(error)
    finally:
        Vehicle.end_trip = original_end_trip
    assert calls["n"] >= 1
    assert second.state == "run"
    assert second.link is side
    assert second.arrival_time == second_arrival
    assert second.name in local_world.VEHICLES_LIVING
    assert side.capacity_out_remain == side_capacity
    assert list(side.vehicles) == [second]
    assert all(
        record.vehicle_name != "second_veh"
        for record in boundary_state.vehicle_removal_records
    )
    # out is observed outflow, not sink, so it should have exited and stayed.
    first = _local_vehicle(local_state, "first_veh")
    assert first.state == "end"
    assert boundary_state.vehicle_removal_records[0].vehicle_name == "first_veh"
    assert boundary_state.completed_virtual_timesteps == ()
    assert local_world.T in boundary_state.outlink_states[0].completed_virtual_timesteps
    assert local_world.T not in boundary_state.outlink_states[1].completed_virtual_timesteps


def test_rejects_other_node_or_timestep_and_unfinished_advance():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 1), "side": (1, 0)})
    )
    other = type(advance_result)(
        node_name="other",
        virtual_timestep=advance_result.virtual_timestep,
        advanced_vehicle_names=(),
        preexisting_incoming_vehicle_names=(),
        newly_arrived_vehicle_names=(),
        newly_arrived_binding_visit_keys=(),
        incoming_vehicle_names_before=(),
        incoming_vehicle_names_after=(),
    )
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            other,
        )
        raise AssertionError("other node must fail")
    except RuntimeError:
        pass
    other_time = type(advance_result)(
        node_name=advance_result.node_name,
        virtual_timestep=advance_result.virtual_timestep + 3,
        advanced_vehicle_names=(),
        preexisting_incoming_vehicle_names=(),
        newly_arrived_vehicle_names=(),
        newly_arrived_binding_visit_keys=(),
        incoming_vehicle_names_before=(),
        incoming_vehicle_names_after=(),
    )
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            other_time,
        )
        raise AssertionError("other timestep must fail")
    except RuntimeError:
        pass
    fresh_world = _new_world("no_advance")
    vehicle = fresh_world.addVehicle("orig_a", "dest", 0, name="only_veh")
    in_a = fresh_world.get_link("in_a")
    outlink = fresh_world.get_link("out")
    merge = fresh_world.get_node("merge")
    _place(fresh_world, vehicle, in_a, outlink, x=in_a.length)
    in_a.vehicles.append(vehicle)
    vehicle.begin_order_control_visit_on_link_entry()
    _record_existing_arrival(vehicle, merge, 4.0, 0.2)
    visit = _binding_visit(vehicle, rank=1, route_name="out", inlink_name="in_a")
    if not getattr(fresh_world, "finalized", 0):
        fresh_world.finalize_scenario()
    for link in fresh_world.LINKS:
        link.update()
    fresh_world.T = 10
    local_only = build_tvt_mp_candidate_local_state(fresh_world, _sequence((visit,)))
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_only)
    from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
        initialize_tvt_mp_candidate_binding_transfer_state,
    )

    transfer = initialize_tvt_mp_candidate_binding_transfer_state(clock)
    not_advanced = initialize_tvt_mp_candidate_local_vehicle_advance_state(transfer)
    not_ready = initialize_tvt_mp_candidate_outlink_boundary_state(
        not_advanced,
        _make_node_result(
            _outlink_result("out", "dest", 1, 1),
            _outlink_result("side", "dest_b", 1, 0),
        ),
    )
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            not_ready,
            advance_result,
        )
        raise AssertionError("advance must already be complete")
    except RuntimeError as error:
        assert "has not finished" in str(error)


class _BoomTravelTime:
    def __init__(self, values):
        self.values = list(values)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, item):
        return self.values[item]

    def __setitem__(self, key, value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            raise RuntimeError("traveltime failed")
        self.values[:] = list(value)


class _BoomAppendList(list):
    def append(self, value):
        raise RuntimeError("completion append failed")


def test_retry_same_timestep_skips_completed_outlink():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 2), "side": (1, 1)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    _park_at_outlink_end(local_state, ["second_veh"], "side")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    side = local_world.get_link("side")
    outlink.capacity_out_remain = 5
    side.capacity_out_remain = 5
    original_side_traveltime = side.traveltime_actual.copy()
    side.traveltime_actual = _BoomTravelTime(original_side_traveltime)
    side_cum_before = list(side.cum_departure)
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("side failure must propagate")
    except RuntimeError as error:
        assert "traveltime failed" in str(error)
    out_state = boundary_state.outlink_states[0]
    side_state = boundary_state.outlink_states[1]
    assert local_world.T in out_state.completed_virtual_timesteps
    first_saved = out_state.completed_process_result(local_world.T)
    assert first_saved is not None
    assert first_saved.observed_outflow_boundary_exit_vehicle_names == ("first_veh",)
    assert local_world.T not in side_state.completed_virtual_timesteps
    assert boundary_state.completed_virtual_timesteps == ()
    assert list(side.vehicles)[0].name == "second_veh"
    assert list(side.cum_departure) == side_cum_before
    allowance_after_first = out_state.flow_allowance
    out_capacity_after_first = outlink.capacity_out_remain
    out_cum_after_first = list(outlink.cum_departure)
    out_travel_after_first = outlink.traveltime_actual.copy()
    removal_names_after_first = [
        record.vehicle_name for record in boundary_state.vehicle_removal_records
    ]
    observed_names_after_first = out_state.cumulative_observed_outflow_exit_vehicle_names
    side.traveltime_actual = original_side_traveltime
    second_result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert out_state.flow_allowance == allowance_after_first
    assert outlink.capacity_out_remain == out_capacity_after_first
    assert list(outlink.cum_departure) == out_cum_after_first
    assert (outlink.traveltime_actual == out_travel_after_first).all()
    assert [
        record.vehicle_name for record in boundary_state.vehicle_removal_records
    ] == removal_names_after_first + ["second_veh"]
    assert out_state.cumulative_observed_outflow_exit_vehicle_names == (
        observed_names_after_first
    )
    assert local_world.T in side_state.completed_virtual_timesteps
    assert boundary_state.completed_virtual_timesteps == (local_world.T,)
    assert len(second_result.outlink_results) == 2
    assert second_result.outlink_results[0] is first_saved
    assert second_result.outlink_results[1].observed_outflow_boundary_exit_vehicle_names == (
        "second_veh",
    )
    allowance_after_second = out_state.flow_allowance
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("third call must fail")
    except RuntimeError:
        pass
    assert out_state.flow_allowance == allowance_after_second
    assert list(outlink.cum_departure) == out_cum_after_first
    assert out_state.completed_process_result(local_world.T) is first_saved
    assert [
        record.vehicle_name for record in boundary_state.vehicle_removal_records
    ] == removal_names_after_first + ["second_veh"]


def test_zero_exit_outlink_is_complete_and_not_reprocessed():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (5, 2), "side": (3, 0)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    parked_head = _local_vehicle(local_state, "first_veh")
    parked_head.x = parked_head.link.length - 10
    local_world = local_state.local_world
    result = process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    out_state = boundary_state.outlink_states[0]
    side_state = boundary_state.outlink_states[1]
    assert result.outlink_results[0].observed_outflow_boundary_exit_vehicle_names == ()
    assert local_world.T in out_state.completed_virtual_timesteps
    assert local_world.T in side_state.completed_virtual_timesteps
    assert out_state.completed_process_result(local_world.T) is result.outlink_results[0]
    assert side_state.completed_process_result(local_world.T) is result.outlink_results[1]
    assert boundary_state.completed_virtual_timesteps == (local_world.T,)
    allowance_after = out_state.flow_allowance
    assert allowance_after == 0.4
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("completed timestep must not run again")
    except RuntimeError:
        pass
    assert out_state.flow_allowance == allowance_after
    assert out_state.completed_process_result(local_world.T) is result.outlink_results[0]


def test_completion_record_failure_rolls_back_that_outlink_only():
    _world, local_state, _transfer, advance_result, boundary_state, _node_result = (
        _started({"out": (1, 1), "side": (1, 1)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    _park_at_outlink_end(local_state, ["second_veh"], "side")
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    side = local_world.get_link("side")
    outlink.capacity_out_remain = 5
    side.capacity_out_remain = 5
    side_state = boundary_state.outlink_states[1]
    side_state._completed_virtual_timesteps = _BoomAppendList([3])
    side_cum_before = list(side.cum_departure)
    side_allowance_before = side_state.flow_allowance
    try:
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            boundary_state,
            advance_result,
        )
        raise AssertionError("completion failure must propagate")
    except RuntimeError as error:
        assert "completion append failed" in str(error)
    second = _local_vehicle(local_state, "second_veh")
    assert second.state == "run"
    assert second.link is side
    assert list(side.cum_departure) == side_cum_before
    assert side_state.flow_allowance == side_allowance_before
    assert side.capacity_out_remain == 5
    assert list(side_state._completed_virtual_timesteps) == [3]
    assert side_state.completed_process_result(local_world.T) is None
    assert all(
        record.vehicle_name != "second_veh"
        for record in boundary_state.vehicle_removal_records
    )
    out_state = boundary_state.outlink_states[0]
    assert local_world.T in out_state.completed_virtual_timesteps
    assert out_state.completed_process_result(local_world.T) is not None
    assert boundary_state.completed_virtual_timesteps == ()
    assert _local_vehicle(local_state, "first_veh").state == "end"


def test_real_world_and_baseline_result_stay_unchanged():
    world, local_state, _transfer, advance_result, boundary_state, node_result = (
        _started({"out": (2, 2), "side": (1, 0)})
    )
    _park_at_outlink_end(local_state, ["first_veh"], "out")
    real_running = set(world.VEHICLES_RUNNING)
    real_out_vehicles = list(world.get_link("out").vehicles)
    real_T = world.T
    process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
        boundary_state,
        advance_result,
    )
    assert set(world.VEHICLES_RUNNING) == real_running
    assert list(world.get_link("out").vehicles) == real_out_vehicles
    assert world.T == real_T
    assert node_result.outlink_results[0].transferred_vehicle_count == 2
    assert node_result.outlink_results[0].active_timestep_count == 2
    assert local_state.local_world is not world


def _run_all() -> None:
    tests = [
        test_public_types_are_frozen_and_removal_record_has_six_fields,
        test_initialization_matches_node_outlink_order_and_modes,
        test_missing_boundary_result_is_not_active_zero,
        test_initialization_rejects_reordered_outlinks_without_repair,
        test_observed_outflow_exits_without_end_trip_or_visit_key,
        test_allowance_waits_and_carries_fraction_then_next_timestep,
        test_integer_allowance_is_not_reset_when_capacity_blocks_exit,
        test_finite_terminal_capacity_is_consumed_and_shortage_waits,
        test_head_not_at_end_does_not_exit_the_follower,
        test_wait_without_outflow_keeps_vehicles_and_allowance,
        test_constrained_sink_calls_end_trip_once_per_vehicle_without_visit_key,
        test_constrained_sink_waits_when_capacity_is_short,
        test_cum_departure_length_mismatch_changes_nothing,
        test_head_leader_is_rejected_before_allowance_changes,
        test_dedicated_exit_rollback_restores_the_outlink_only,
        test_end_trip_failure_rolls_back_that_outlink,
        test_retry_same_timestep_skips_completed_outlink,
        test_zero_exit_outlink_is_complete_and_not_reprocessed,
        test_completion_record_failure_rolls_back_that_outlink_only,
        test_rejects_other_node_or_timestep_and_unfinished_advance,
        test_real_world_and_baseline_result_stay_unchanged,
    ]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print(len(tests), "tests passed")


if __name__ == "__main__":
    _run_all()
