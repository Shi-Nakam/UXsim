# Tests for one local advance after binding-rank node passage.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_local_vehicle_advance.py

from __future__ import annotations

import copy

from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    initialize_tvt_mp_candidate_binding_transfer_state,
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_local_vehicle_advance import (
    OrderControlTvtMpLocalVehicleAdvanceResult,
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals,
    initialize_tvt_mp_candidate_local_vehicle_advance_state,
)
from uxsim.order_control_tvt_mp_candidate_virtual_time import (
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
        tmax=40,
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


def _prepare(world, visits, before_scan=None):
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10
    sequence = _sequence(visits)
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    transfer_state = initialize_tvt_mp_candidate_binding_transfer_state(clock)
    # Capacity changes that must affect the passage scan are applied here,
    # after the offset-0 clock keeps the snapshot remainder and before the scan.
    if before_scan is not None:
        before_scan(local_state)
    scan_result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    advance_state = initialize_tvt_mp_candidate_local_vehicle_advance_state(
        transfer_state
    )
    return local_state, transfer_state, scan_result, advance_state


def _local_vehicle(local_state, vehicle_name: str):
    return local_state.local_vehicle_by_real_vehicle_name[vehicle_name]


def _incoming_names(target_node) -> list[str]:
    names = []
    for vehicle in target_node.incoming_vehicles:
        names.append(vehicle.name)
    return names


def _visit_arrival(vehicle) -> tuple:
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        return (None, None)
    return (current_visit.get("arrival_time"), current_visit.get("arrival_tiebreaker"))


def _background_snapshot(local_state, transfer_state) -> dict:
    local_world = local_state.local_world
    target_node = local_state.target_node
    last_inlink_name = None
    if target_node.last_order_control_inlink is not None:
        last_inlink_name = target_node.last_order_control_inlink.name
    link_records = {}
    for link_name in ("in_a", "in_b", "out", "side", "far"):
        link = local_world.get_link(link_name)
        enter_log = {}
        for entry_time, entered_vehicle in link.vehicles_enter_log.items():
            enter_log[entry_time] = entered_vehicle.name
        link_records[link_name] = {
            "capacity_out_remain": link.capacity_out_remain,
            "capacity_in_remain": link.capacity_in_remain,
            "cum_arrival": list(link.cum_arrival),
            "cum_departure": list(link.cum_departure),
            "vehicles_enter_log": enter_log,
        }
    return {
        "T": local_world.T,
        "flow_capacity_remain": target_node.flow_capacity_remain,
        "last_inlink_name": last_inlink_name,
        "last_entry_timestep": target_node.last_order_control_entry_timestep,
        "clearance_timesteps": target_node.order_control_clearance_timesteps,
        "links": link_records,
        "transferred_keys": transfer_state.transferred_binding_visit_keys,
        "binding_sequence": local_state.binding_rank_sequence,
    }


def _vehicle_motion_snapshot(local_state) -> dict:
    records = {}
    for vehicle in local_state.local_world.VEHICLES_LIVING.values():
        records[vehicle.name] = (
            None if vehicle.link is None else vehicle.link.name,
            vehicle.x,
            vehicle.x_old,
            vehicle.x_next,
            vehicle.v,
            vehicle.move_remain,
            vehicle.state,
        )
    return records


def test_same_inlink_preexisting_arrivals_keep_order_and_arrival_record():
    world = _new_world("preexisting_same_inlink")
    first = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second = world.addVehicle("orig_a", "dest_b", 0, name="second_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    side = world.get_link("side")
    merge = world.get_node("merge")
    _place(world, first, in_a, outlink, x=in_a.length)
    _place(world, second, in_a, side, x=in_a.length)
    first.follower = second
    second.leader = first
    in_a.vehicles.append(first)
    in_a.vehicles.append(second)
    first.begin_order_control_visit_on_link_entry()
    second.begin_order_control_visit_on_link_entry()
    _record_existing_arrival(first, merge, 4.0, 0.125)
    _record_existing_arrival(second, merge, 4.0, 0.875)
    # Deliberately not physical order, to show the existing queue is kept as-is.
    merge.incoming_vehicles.append(second)
    merge.incoming_vehicles.append(first)
    visits = (
        _binding_visit(first, rank=1, route_name="out", inlink_name="in_a"),
        _binding_visit(second, rank=2, route_name="side", inlink_name="in_a"),
    )

    def _block_inlink_outflow(local_state):
        # Both vehicles are already waiting. No outflow, so neither passes.
        local_state.local_world.get_link("in_a").capacity_out_remain = 0.0

    local_state, transfer_state, scan_result, advance_state = _prepare(
        world,
        visits,
        before_scan=_block_inlink_outflow,
    )
    copied_first = _local_vehicle(local_state, "first_veh")
    copied_second = _local_vehicle(local_state, "second_veh")
    arrival_before = {
        "first_veh": _visit_arrival(copied_first),
        "second_veh": _visit_arrival(copied_second),
    }
    rng_before = local_state.local_world.rng.bit_generator.state
    order_rng_before = local_state.local_world.order_control_rng.bit_generator.state
    result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    assert _incoming_names(local_state.target_node) == ["second_veh", "first_veh"]
    assert result.preexisting_incoming_vehicle_names == ("second_veh", "first_veh")
    assert result.newly_arrived_vehicle_names == ()
    assert result.incoming_vehicle_names_before == ("second_veh", "first_veh")
    assert result.incoming_vehicle_names_after == ("second_veh", "first_veh")
    assert _visit_arrival(copied_first) == arrival_before["first_veh"]
    assert _visit_arrival(copied_second) == arrival_before["second_veh"]
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert local_state.local_world.order_control_rng.bit_generator.state == order_rng_before
    assert copied_first.x == in_a.length
    assert copied_second.x == in_a.length
    assert list(local_state.local_world.get_link("in_a").vehicles) == [
        copied_first,
        copied_second,
    ]


def test_binding_transfer_passes_multiple_same_inlink_arrivals_before_advance():
    world = _new_world("multiple_pass_then_advance")
    first = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second = world.addVehicle("orig_a", "dest_b", 0, name="second_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    side = world.get_link("side")
    merge = world.get_node("merge")
    _place(world, first, in_a, outlink, x=in_a.length)
    _place(world, second, in_a, side, x=in_a.length)
    first.follower = second
    second.leader = first
    in_a.vehicles.append(first)
    in_a.vehicles.append(second)
    first.begin_order_control_visit_on_link_entry()
    second.begin_order_control_visit_on_link_entry()
    _record_existing_arrival(first, merge, 4.0, 0.2)
    _record_existing_arrival(second, merge, 4.0, 0.3)
    merge.incoming_vehicles.append(first)
    merge.incoming_vehicles.append(second)
    visits = (
        _binding_visit(first, rank=1, route_name="out", inlink_name="in_a"),
        _binding_visit(second, rank=2, route_name="side", inlink_name="in_a"),
    )
    local_state, transfer_state, scan_result, advance_state = _prepare(world, visits)
    assert scan_result.transferred_binding_visit_keys == (
        ("first_veh", 1),
        ("second_veh", 1),
    )
    assert _incoming_names(local_state.target_node) == []
    copied_first = _local_vehicle(local_state, "first_veh")
    copied_second = _local_vehicle(local_state, "second_veh")
    first_x_before = copied_first.x
    second_x_before = copied_second.x
    transferred_before = transfer_state.transferred_binding_visit_keys
    result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    assert copied_first.link.name == "out"
    assert copied_second.link.name == "side"
    assert copied_first not in local_state.local_world.get_link("in_a").vehicles
    assert copied_second not in local_state.local_world.get_link("in_a").vehicles
    assert copied_first.x != first_x_before
    assert copied_second.x != second_x_before
    assert result.newly_arrived_vehicle_names == ()
    assert result.incoming_vehicle_names_after == ()
    assert transfer_state.transferred_binding_visit_keys == transferred_before


def test_unpassed_preexisting_arrival_stays_after_advance():
    world = _new_world("one_pass_one_remains")
    first = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second = world.addVehicle("orig_a", "dest_b", 0, name="second_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    side = world.get_link("side")
    merge = world.get_node("merge")
    _place(world, first, in_a, outlink, x=in_a.length)
    _place(world, second, in_a, side, x=in_a.length)
    first.follower = second
    second.leader = first
    in_a.vehicles.append(first)
    in_a.vehicles.append(second)
    first.begin_order_control_visit_on_link_entry()
    second.begin_order_control_visit_on_link_entry()
    _record_existing_arrival(first, merge, 6.0, 0.4)
    _record_existing_arrival(second, merge, 6.0, 0.5)
    merge.incoming_vehicles.append(first)
    merge.incoming_vehicles.append(second)
    visits = (
        _binding_visit(first, rank=1, route_name="out", inlink_name="in_a"),
        _binding_visit(second, rank=2, route_name="side", inlink_name="in_a"),
    )

    def _allow_only_one_node_passage(local_state):
        # Shared node capacity allows the physical head only. The second stays.
        local_state.target_node.flow_capacity_remain = local_state.local_world.DELTAN

    local_state, transfer_state, scan_result, advance_state = _prepare(
        world,
        visits,
        before_scan=_allow_only_one_node_passage,
    )
    assert scan_result.transferred_binding_visit_keys == (("first_veh", 1),)
    assert _incoming_names(local_state.target_node) == ["second_veh"]
    copied_second = _local_vehicle(local_state, "second_veh")
    arrival_before = _visit_arrival(copied_second)
    result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    assert _incoming_names(local_state.target_node) == ["second_veh"]
    assert result.preexisting_incoming_vehicle_names == ("second_veh",)
    assert result.newly_arrived_vehicle_names == ()
    assert _visit_arrival(copied_second) == arrival_before
    assert copied_second.link.name == "in_a"
    assert _local_vehicle(local_state, "first_veh").link.name == "out"
    assert transfer_state.transferred_binding_visit_keys == (("first_veh", 1),)


def test_new_inlink_arrival_is_appended_once_without_rescan():
    world = _new_world("new_arrival")
    vehicle = world.addVehicle("orig_a", "dest", 0, name="arriving_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    step = in_a.u * world.DELTAT
    _place(world, vehicle, in_a, outlink, x=in_a.length - step)
    in_a.vehicles.append(vehicle)
    vehicle.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(vehicle, rank=1, route_name="out", inlink_name="in_a"),
    )
    local_state, transfer_state, scan_result, advance_state = _prepare(world, visits)
    assert scan_result.transferred_binding_visit_keys == ()
    assert _incoming_names(local_state.target_node) == []
    transferred_before = transfer_state.transferred_binding_visit_keys
    calls = {"scan": 0}

    def _forbid_rescan(*_args, **_kwargs):
        calls["scan"] += 1
        raise AssertionError("binding transfer was called again during advance")

    import uxsim.order_control_tvt_mp_candidate_binding_transfer as binding_module
    import uxsim.order_control_tvt_mp_candidate_local_vehicle_advance as advance_module

    original_scan = binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = _forbid_rescan
    advance_module_scan = getattr(
        advance_module,
        "scan_and_transfer_tvt_mp_binding_visits_at_current_timestep",
        None,
    )
    if advance_module_scan is not None:
        advance_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            _forbid_rescan
        )
    try:
        result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
            advance_state,
            scan_result,
        )
    finally:
        binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            original_scan
        )
        if advance_module_scan is not None:
            advance_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
                advance_module_scan
            )
    copied = _local_vehicle(local_state, "arriving_veh")
    assert calls["scan"] == 0
    assert isinstance(result, OrderControlTvtMpLocalVehicleAdvanceResult)
    assert result.newly_arrived_vehicle_names == ("arriving_veh",)
    assert result.newly_arrived_binding_visit_keys == (("arriving_veh", 1),)
    assert result.incoming_vehicle_names_before == ()
    assert result.incoming_vehicle_names_after == ("arriving_veh",)
    assert _incoming_names(local_state.target_node) == ["arriving_veh"]
    assert copied.x == in_a.length
    assert copied.link.name == "in_a"
    arrival_time, tiebreaker = _visit_arrival(copied)
    assert arrival_time == local_state.local_world.T * local_state.local_world.DELTAT
    assert isinstance(tiebreaker, float)
    assert transfer_state.transferred_binding_visit_keys == transferred_before
    assert ("arriving_veh", 1) not in transfer_state.transferred_binding_visit_keys


def test_two_new_arrivals_append_in_living_registration_order():
    world = _new_world("two_new_arrivals")
    world.addLink(
        "in_wide",
        "orig_a",
        "merge",
        length=200,
        free_flow_speed=20,
        number_of_lanes=2,
    )
    # Added first, but physically behind. UXsim update order is living registration.
    living_first = world.addVehicle("orig_a", "dest", 0, name="living_first")
    living_second = world.addVehicle("orig_a", "dest_b", 0, name="living_second")
    in_wide = world.get_link("in_wide")
    outlink = world.get_link("out")
    side = world.get_link("side")
    step = in_wide.u * world.DELTAT
    _place(world, living_first, in_wide, outlink, x=in_wide.length - step)
    _place(world, living_second, in_wide, side, x=in_wide.length - step / 2)
    in_wide.vehicles.append(living_second)
    in_wide.vehicles.append(living_first)
    living_first.begin_order_control_visit_on_link_entry()
    living_second.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(living_first, rank=1, route_name="out", inlink_name="in_wide"),
        _binding_visit(living_second, rank=2, route_name="side", inlink_name="in_wide"),
    )
    local_state, _transfer_state, scan_result, advance_state = _prepare(world, visits)
    assert scan_result.transferred_binding_visit_keys == ()
    result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    assert result.newly_arrived_vehicle_names == ("living_first", "living_second")
    assert _incoming_names(local_state.target_node) == ["living_first", "living_second"]
    assert [vehicle.name for vehicle in local_state.local_world.get_link("in_wide").vehicles] == [
        "living_second",
        "living_first",
    ]


def test_outlink_vehicle_stops_at_end_without_downstream_registration():
    world = _new_world("outlink_end")
    binding_vehicle = world.addVehicle("orig_a", "dest", 0, name="binding_veh")
    out_vehicle = world.addVehicle("orig_a", "dest", 0, name="out_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    _place(world, binding_vehicle, in_a, outlink, x=10.0)
    _place(world, out_vehicle, outlink, None, x=outlink.length - 10.0)
    in_a.vehicles.append(binding_vehicle)
    outlink.vehicles.append(out_vehicle)
    binding_vehicle.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(binding_vehicle, rank=1, route_name="out", inlink_name="in_a"),
    )
    local_state, _transfer_state, scan_result, advance_state = _prepare(world, visits)
    copied_out = _local_vehicle(local_state, "out_veh")
    dest = local_state.local_world.get_node("dest")

    def _forbid_end_trip():
        raise AssertionError("end_trip was called")

    copied_out.end_trip = _forbid_end_trip
    result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    copied_outlink = local_state.local_world.get_link("out")
    assert copied_out in copied_outlink.vehicles
    assert copied_out.x == copied_outlink.length
    assert copied_out.x_next == copied_outlink.length
    assert copied_out.move_remain == 10.0
    assert copied_out.state == "run"
    assert copied_out.link is copied_outlink
    assert dest.incoming_vehicles == []
    assert "out_veh" not in result.newly_arrived_vehicle_names
    assert "out_veh" not in _incoming_names(local_state.target_node)


def test_second_advance_at_same_timestep_raises_without_further_changes():
    world = _new_world("double_advance")
    vehicle = world.addVehicle("orig_a", "dest", 0, name="moving_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    _place(world, vehicle, in_a, outlink, x=20.0)
    in_a.vehicles.append(vehicle)
    vehicle.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(vehicle, rank=1, route_name="out", inlink_name="in_a"),
    )
    local_state, _transfer_state, scan_result, advance_state = _prepare(world, visits)
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    motion_after_first = _vehicle_motion_snapshot(local_state)
    incoming_after_first = _incoming_names(local_state.target_node)
    try:
        advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
            advance_state,
            scan_result,
        )
        raise AssertionError("expected RuntimeError on a second advance")
    except RuntimeError as error:
        assert "already advanced" in str(error)
    assert _vehicle_motion_snapshot(local_state) == motion_after_first
    assert _incoming_names(local_state.target_node) == incoming_after_first


def test_clock_capacity_clearance_and_other_worlds_stay_unchanged():
    world = _new_world("invariants")
    vehicle = world.addVehicle("orig_a", "dest", 0, name="moving_veh")
    far_vehicle = world.addVehicle("west", "sink", 0, name="far_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    far = world.get_link("far")
    _place(world, vehicle, in_a, outlink, x=30.0)
    _place(world, far_vehicle, far, None, x=40.0)
    in_a.vehicles.append(vehicle)
    far.vehicles.append(far_vehicle)
    vehicle.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(vehicle, rank=1, route_name="out", inlink_name="in_a"),
    )
    other_world = _new_world("other_candidate")
    other_vehicle = other_world.addVehicle("orig_a", "dest", 0, name="other_veh")
    _place(other_world, other_vehicle, other_world.get_link("in_a"), other_world.get_link("out"), x=50.0)
    other_world.get_link("in_a").vehicles.append(other_vehicle)
    other_vehicle.begin_order_control_visit_on_link_entry()
    other_visits = (
        _binding_visit(other_vehicle, rank=1, route_name="out", inlink_name="in_a"),
    )
    local_state, transfer_state, scan_result, advance_state = _prepare(world, visits)
    other_local, _other_transfer, _other_scan, _other_advance = _prepare(
        other_world,
        other_visits,
    )
    real_x = world.VEHICLES["moving_veh"].x
    real_far_x = world.VEHICLES["far_veh"].x
    real_rng = world.rng.bit_generator.state
    other_x = _local_vehicle(other_local, "other_veh").x
    other_T = other_local.local_world.T
    background_before = _background_snapshot(local_state, transfer_state)
    far_before = local_state.local_world.VEHICLES["far_veh"].x
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )
    assert _background_snapshot(local_state, transfer_state) == background_before
    assert world.VEHICLES["moving_veh"].x == real_x
    assert world.VEHICLES["far_veh"].x == real_far_x
    assert world.T == 10
    assert world.rng.bit_generator.state == real_rng
    assert _local_vehicle(other_local, "other_veh").x == other_x
    assert other_local.local_world.T == other_T
    assert local_state.local_world.VEHICLES["far_veh"].x == far_before
    assert _local_vehicle(local_state, "moving_veh").x == 50.0


def test_later_vehicle_inconsistency_leaves_every_vehicle_unmoved():
    world = _new_world("atomic_advance")
    world.addLink(
        "in_wide",
        "orig_a",
        "merge",
        length=200,
        free_flow_speed=20,
        number_of_lanes=2,
    )
    first = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second = world.addVehicle("orig_a", "dest_b", 0, name="second_veh")
    in_wide = world.get_link("in_wide")
    outlink = world.get_link("out")
    side = world.get_link("side")
    step = in_wide.u * world.DELTAT
    _place(world, first, in_wide, outlink, x=in_wide.length - step)
    _place(world, second, in_wide, side, x=in_wide.length - step)
    in_wide.vehicles.append(first)
    in_wide.vehicles.append(second)
    first.begin_order_control_visit_on_link_entry()
    second.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(first, rank=1, route_name="out", inlink_name="in_wide"),
        _binding_visit(second, rank=2, route_name="side", inlink_name="in_wide"),
    )
    local_state, _transfer_state, scan_result, advance_state = _prepare(world, visits)
    copied_second = _local_vehicle(local_state, "second_veh")
    # living_first is checked before living_second. The bad visit is the later one.
    broken_visit = dict(copied_second.order_control_current_visit)
    broken_visit["node"] = world.get_node("merge")
    copied_second.order_control_current_visit = broken_visit
    motion_before = _vehicle_motion_snapshot(local_state)
    incoming_before = _incoming_names(local_state.target_node)
    try:
        advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
            advance_state,
            scan_result,
        )
        raise AssertionError("expected RuntimeError for a bad current visit")
    except RuntimeError as error:
        assert "second_veh" in str(error)
    assert _vehicle_motion_snapshot(local_state) == motion_before
    assert _incoming_names(local_state.target_node) == incoming_before
    assert advance_state.completed_virtual_timesteps == ()


def _one_new_arrival_ready(world_name: str):
    world = _new_world(world_name)
    vehicle = world.addVehicle("orig_a", "dest", 0, name="arriving_veh")
    in_a = world.get_link("in_a")
    outlink = world.get_link("out")
    step = in_a.u * world.DELTAT
    _place(world, vehicle, in_a, outlink, x=in_a.length - step)
    in_a.vehicles.append(vehicle)
    vehicle.begin_order_control_visit_on_link_entry()
    visits = (
        _binding_visit(vehicle, rank=1, route_name="out", inlink_name="in_a"),
    )
    return _prepare(world, visits)


def _assert_advance_rejected_without_changes(
    local_state,
    transfer_state,
    advance_state,
    scan_result,
    *,
    vehicle_name: str,
):
    copied = _local_vehicle(local_state, vehicle_name)
    motion_before = _vehicle_motion_snapshot(local_state)
    incoming_before = _incoming_names(local_state.target_node)
    arrival_before = _visit_arrival(copied)
    times_before = dict(copied.order_control_node_arrival_times)
    tiebreakers_before = dict(copied.order_control_node_arrival_tiebreakers)
    rng_before = local_state.local_world.rng.bit_generator.state
    order_rng_before = local_state.local_world.order_control_rng.bit_generator.state
    transferred_before = transfer_state.transferred_binding_visit_keys
    try:
        advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
            advance_state,
            scan_result,
        )
        raise AssertionError("expected RuntimeError for a preset arrival record")
    except RuntimeError as error:
        message = str(error)
        assert vehicle_name in message
        assert "arrival_time" in message
        assert "arrival_tiebreaker" in message
    assert _vehicle_motion_snapshot(local_state) == motion_before
    assert _incoming_names(local_state.target_node) == incoming_before
    assert _visit_arrival(copied) == arrival_before
    assert copied.order_control_node_arrival_times == times_before
    assert copied.order_control_node_arrival_tiebreakers == tiebreakers_before
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert (
        local_state.local_world.order_control_rng.bit_generator.state
        == order_rng_before
    )
    assert advance_state.completed_virtual_timesteps == ()
    assert transfer_state.transferred_binding_visit_keys == transferred_before


def test_new_arrival_with_only_arrival_time_changes_nothing():
    local_state, transfer_state, scan_result, advance_state = _one_new_arrival_ready(
        "preset_arrival_time"
    )
    current_visit = _local_vehicle(local_state, "arriving_veh").order_control_current_visit
    current_visit["arrival_time"] = 3.0
    _assert_advance_rejected_without_changes(
        local_state,
        transfer_state,
        advance_state,
        scan_result,
        vehicle_name="arriving_veh",
    )


def test_new_arrival_with_only_arrival_tiebreaker_changes_nothing():
    local_state, transfer_state, scan_result, advance_state = _one_new_arrival_ready(
        "preset_tiebreaker"
    )
    current_visit = _local_vehicle(local_state, "arriving_veh").order_control_current_visit
    current_visit["arrival_tiebreaker"] = 0.5
    _assert_advance_rejected_without_changes(
        local_state,
        transfer_state,
        advance_state,
        scan_result,
        vehicle_name="arriving_veh",
    )


def test_new_arrival_with_both_arrival_fields_changes_nothing():
    local_state, transfer_state, scan_result, advance_state = _one_new_arrival_ready(
        "preset_both_arrival_fields"
    )
    current_visit = _local_vehicle(local_state, "arriving_veh").order_control_current_visit
    current_visit["arrival_time"] = 3.0
    current_visit["arrival_tiebreaker"] = 0.5
    _assert_advance_rejected_without_changes(
        local_state,
        transfer_state,
        advance_state,
        scan_result,
        vehicle_name="arriving_veh",
    )


def _two_new_arrivals_with_one_revisit(world_name: str, *, second_is_revisit: bool):
    world = _new_world(world_name)
    world.addLink(
        "in_wide",
        "orig_a",
        "merge",
        length=200,
        free_flow_speed=20,
        number_of_lanes=2,
    )
    waiting = world.addVehicle("orig_a", "dest", 0, name="waiting_veh")
    living_first = world.addVehicle("orig_a", "dest", 0, name="living_first")
    living_second = world.addVehicle("orig_a", "dest_b", 0, name="living_second")
    in_a = world.get_link("in_a")
    in_wide = world.get_link("in_wide")
    outlink = world.get_link("out")
    side = world.get_link("side")
    merge = world.get_node("merge")
    step = in_wide.u * world.DELTAT
    _place(world, waiting, in_a, outlink, x=in_a.length)
    _place(world, living_first, in_wide, outlink, x=in_wide.length - step)
    _place(world, living_second, in_wide, side, x=in_wide.length - step)
    in_a.vehicles.append(waiting)
    in_wide.vehicles.append(living_second)
    in_wide.vehicles.append(living_first)
    waiting.begin_order_control_visit_on_link_entry()
    living_first.begin_order_control_visit_on_link_entry()
    living_second.begin_order_control_visit_on_link_entry()
    _record_existing_arrival(waiting, merge, 4.0, 0.25)
    if second_is_revisit:
        # Legacy first-arrival dict already has merge. The current visit does not.
        # The official method then draws the tiebreaker from order_control_rng.
        living_second.order_control_node_arrival_times["merge"] = 1.0
        living_second.order_control_node_arrival_tiebreakers["merge"] = 0.01
    merge.incoming_vehicles.append(waiting)
    visits = (
        _binding_visit(living_first, rank=1, route_name="out", inlink_name="in_wide"),
        _binding_visit(living_second, rank=2, route_name="side", inlink_name="in_wide"),
    )
    return world, visits


def test_second_arrival_record_failure_restores_the_whole_advance():
    _world_object, visits = _two_new_arrivals_with_one_revisit(
        "second_arrival_fails",
        second_is_revisit=False,
    )
    local_state, transfer_state, scan_result, advance_state = _prepare(
        _world_object,
        visits,
    )
    motion_before = _vehicle_motion_snapshot(local_state)
    incoming_before = _incoming_names(local_state.target_node)
    first = _local_vehicle(local_state, "living_first")
    second = _local_vehicle(local_state, "living_second")
    waiting = _local_vehicle(local_state, "waiting_veh")
    arrivals_before = {
        "living_first": _visit_arrival(first),
        "living_second": _visit_arrival(second),
        "waiting_veh": _visit_arrival(waiting),
    }
    times_before = {
        "living_first": dict(first.order_control_node_arrival_times),
        "living_second": dict(second.order_control_node_arrival_times),
        "waiting_veh": dict(waiting.order_control_node_arrival_times),
    }
    tiebreakers_before = {
        "living_first": dict(first.order_control_node_arrival_tiebreakers),
        "living_second": dict(second.order_control_node_arrival_tiebreakers),
        "waiting_veh": dict(waiting.order_control_node_arrival_tiebreakers),
    }
    rng_before = copy.deepcopy(local_state.local_world.rng.bit_generator.state)
    order_rng_before = copy.deepcopy(
        local_state.local_world.order_control_rng.bit_generator.state
    )
    transferred_before = transfer_state.transferred_binding_visit_keys
    original_record = Vehicle.record_order_control_node_arrival

    def _record_first_and_fail_second(self, node):
        if self.name == "living_second":
            raise RuntimeError("forced second arrival failure")
        return original_record(self, node)

    Vehicle.record_order_control_node_arrival = _record_first_and_fail_second
    try:
        try:
            advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
                advance_state,
                scan_result,
            )
            raise AssertionError("expected the second arrival record to fail")
        except RuntimeError as error:
            assert "forced second arrival failure" in str(error)
    finally:
        Vehicle.record_order_control_node_arrival = original_record
    assert _vehicle_motion_snapshot(local_state) == motion_before
    assert _incoming_names(local_state.target_node) == incoming_before
    assert _visit_arrival(first) == arrivals_before["living_first"]
    assert _visit_arrival(second) == arrivals_before["living_second"]
    assert _visit_arrival(waiting) == arrivals_before["waiting_veh"]
    assert first.order_control_node_arrival_times == times_before["living_first"]
    assert second.order_control_node_arrival_times == times_before["living_second"]
    assert waiting.order_control_node_arrival_times == times_before["waiting_veh"]
    assert (
        first.order_control_node_arrival_tiebreakers
        == tiebreakers_before["living_first"]
    )
    assert (
        second.order_control_node_arrival_tiebreakers
        == tiebreakers_before["living_second"]
    )
    assert (
        waiting.order_control_node_arrival_tiebreakers
        == tiebreakers_before["waiting_veh"]
    )
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert (
        local_state.local_world.order_control_rng.bit_generator.state
        == order_rng_before
    )
    assert advance_state.completed_virtual_timesteps == ()
    assert transfer_state.transferred_binding_visit_keys == transferred_before


def test_new_arrivals_match_official_record_order_including_revisit():
    _advance_world, advance_visits = _two_new_arrivals_with_one_revisit(
        "official_arrival_advance",
        second_is_revisit=True,
    )
    _reference_world, reference_visits = _two_new_arrivals_with_one_revisit(
        "official_arrival_reference",
        second_is_revisit=True,
    )
    advance_local, _advance_transfer, advance_scan, advance_state = _prepare(
        _advance_world,
        advance_visits,
    )
    reference_local, _reference_transfer, _reference_scan, _reference_advance = _prepare(
        _reference_world,
        reference_visits,
    )
    reference_node = reference_local.target_node
    reference_first = _local_vehicle(reference_local, "living_first")
    reference_second = _local_vehicle(reference_local, "living_second")
    # Same living registration order as the advance: first visit, then revisit.
    reference_first.record_order_control_node_arrival(reference_node)
    reference_second.record_order_control_node_arrival(reference_node)
    result = advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        advance_scan,
    )
    assert result.newly_arrived_vehicle_names == ("living_first", "living_second")
    assert result.incoming_vehicle_names_before == ("waiting_veh",)
    assert result.incoming_vehicle_names_after == (
        "waiting_veh",
        "living_first",
        "living_second",
    )
    advance_first = _local_vehicle(advance_local, "living_first")
    advance_second = _local_vehicle(advance_local, "living_second")
    advance_waiting = _local_vehicle(advance_local, "waiting_veh")
    assert _visit_arrival(advance_first) == _visit_arrival(reference_first)
    assert _visit_arrival(advance_second) == _visit_arrival(reference_second)
    assert advance_first.order_control_node_arrival_times == (
        reference_first.order_control_node_arrival_times
    )
    assert advance_first.order_control_node_arrival_tiebreakers == (
        reference_first.order_control_node_arrival_tiebreakers
    )
    # Revisit must not rewrite the legacy first-arrival dictionaries.
    assert advance_second.order_control_node_arrival_times == {"merge": 1.0}
    assert advance_second.order_control_node_arrival_tiebreakers == {"merge": 0.01}
    assert _visit_arrival(advance_second)[0] == (
        advance_local.local_world.T * advance_local.local_world.DELTAT
    )
    assert _visit_arrival(advance_waiting) == (4.0, 0.25)
    assert (
        advance_local.local_world.rng.bit_generator.state
        == reference_local.local_world.rng.bit_generator.state
    )
    assert (
        advance_local.local_world.order_control_rng.bit_generator.state
        == reference_local.local_world.order_control_rng.bit_generator.state
    )


TESTS = (
    test_same_inlink_preexisting_arrivals_keep_order_and_arrival_record,
    test_binding_transfer_passes_multiple_same_inlink_arrivals_before_advance,
    test_unpassed_preexisting_arrival_stays_after_advance,
    test_new_inlink_arrival_is_appended_once_without_rescan,
    test_two_new_arrivals_append_in_living_registration_order,
    test_outlink_vehicle_stops_at_end_without_downstream_registration,
    test_second_advance_at_same_timestep_raises_without_further_changes,
    test_clock_capacity_clearance_and_other_worlds_stay_unchanged,
    test_later_vehicle_inconsistency_leaves_every_vehicle_unmoved,
    test_new_arrival_with_only_arrival_time_changes_nothing,
    test_new_arrival_with_only_arrival_tiebreaker_changes_nothing,
    test_new_arrival_with_both_arrival_fields_changes_nothing,
    test_second_arrival_record_failure_restores_the_whole_advance,
    test_new_arrivals_match_official_record_order_including_revisit,
)


if __name__ == "__main__":
    for test_function in TESTS:
        test_function()
    print(f"local vehicle advance tests passed ({len(TESTS)} tests).")
