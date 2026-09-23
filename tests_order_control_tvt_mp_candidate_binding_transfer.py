# Tests for binding-rank node passage at one virtual timestep.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_binding_transfer.py

from __future__ import annotations

import dataclasses

from uxsim.order_control_batch_level_2_reference import (
    _transfer_vehicle_reference,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferScanResult,
    OrderControlTvtMpBindingTransferStopReason,
    OrderControlTvtMpBindingVisitTemporarySkipReason,
    OrderControlTvtMpCandidateBindingTransferState,
    initialize_tvt_mp_candidate_binding_transfer_state,
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
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
from uxsim.uxsim import World


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


def _place(vehicle, link, route_link) -> None:
    vehicle.link = link
    vehicle.state = "run"
    vehicle.x = link.length
    vehicle.x_old = link.length
    vehicle.x_next = link.length
    vehicle.v = 4.0
    vehicle.lane = 0
    vehicle.leader = None
    vehicle.follower = None
    vehicle.route_next_link = route_link
    vehicle.link_arrival_time = 5.0
    vehicle.move_remain = 2.0


def _open_capacities(local_state) -> None:
    node = local_state.target_node
    node.flow_capacity_remain = 10.0
    for link in local_state.inlinks + local_state.outlinks:
        link.capacity_out_remain = 10.0
        link.capacity_in_remain = 10.0


def _visit_record(current_visit) -> tuple | None:
    if current_visit is None:
        return None
    visit_node = current_visit.get("node")
    visit_inlink = current_visit.get("inlink")
    return (
        current_visit.get("visit_id"),
        None if visit_node is None else visit_node.name,
        None if visit_inlink is None else visit_inlink.name,
        current_visit.get("earliest_arrival_timestep"),
        current_visit.get("arrival_time"),
        current_visit.get("arrival_tiebreaker"),
        current_visit.get("batch_assignment"),
    )


def _vehicle_motion_snapshot(vehicle) -> dict:
    leader_name = None
    if vehicle.leader is not None:
        leader_name = vehicle.leader.name
    follower_name = None
    if vehicle.follower is not None:
        follower_name = vehicle.follower.name
    route_name = None
    if vehicle.route_next_link is not None:
        route_name = vehicle.route_next_link.name
    return {
        "link_name": vehicle.link.name,
        "x": vehicle.x,
        "x_old": vehicle.x_old,
        "x_next": vehicle.x_next,
        "v": vehicle.v,
        "lane": vehicle.lane,
        "leader_name": leader_name,
        "follower_name": follower_name,
        "move_remain": vehicle.move_remain,
        "link_arrival_time": vehicle.link_arrival_time,
        "order_control_visit_id": vehicle.order_control_visit_id,
        "current_visit": _visit_record(vehicle.order_control_current_visit),
        "route_next_link_name": route_name,
    }


def _link_traffic_snapshot(link) -> dict:
    vehicle_names = []
    for queued_vehicle in link.vehicles:
        vehicle_names.append(queued_vehicle.name)
    enter_log = {}
    for entry_time, entered_vehicle in link.vehicles_enter_log.items():
        enter_log[entry_time] = entered_vehicle.name
    return {
        "vehicle_names": vehicle_names,
        "capacity_out_remain": link.capacity_out_remain,
        "capacity_in_remain": link.capacity_in_remain,
        "cum_arrival": list(link.cum_arrival),
        "cum_departure": list(link.cum_departure),
        "traveltime_actual": list(link.traveltime_actual),
        "vehicles_enter_log": enter_log,
    }


def _node_traffic_snapshot(target_node) -> dict:
    incoming_names = []
    for incoming_vehicle in target_node.incoming_vehicles:
        incoming_names.append(incoming_vehicle.name)
    last_inlink_name = None
    if target_node.last_order_control_inlink is not None:
        last_inlink_name = target_node.last_order_control_inlink.name
    return {
        "incoming_vehicle_names": incoming_names,
        "flow_capacity_remain": target_node.flow_capacity_remain,
        "last_inlink_name": last_inlink_name,
        "last_order_control_entry_timestep": target_node.last_order_control_entry_timestep,
        "order_control_clearance_timesteps": target_node.order_control_clearance_timesteps,
    }


def _traffic_state_snapshot(local_state, transfer_state) -> dict:
    local_world = local_state.local_world
    return {
        "first_veh": _vehicle_motion_snapshot(
            _local_vehicle(local_state, "first_veh")
        ),
        "second_veh": _vehicle_motion_snapshot(
            _local_vehicle(local_state, "second_veh")
        ),
        "in_a": _link_traffic_snapshot(local_world.get_link("in_a")),
        "in_b": _link_traffic_snapshot(local_world.get_link("in_b")),
        "out": _link_traffic_snapshot(local_world.get_link("out")),
        "side": _link_traffic_snapshot(local_world.get_link("side")),
        "node": _node_traffic_snapshot(local_state.target_node),
        "transferred_binding_visit_keys": transfer_state.transferred_binding_visit_keys,
    }


def _fixture_from_world_and_visits(world, visits):
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(("first_veh", 1),),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=visits,
        k_last_buyer=1,
        k_decision_window=2,
        k_fixed=2,
    )
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    transfer_state = initialize_tvt_mp_candidate_binding_transfer_state(clock)
    return world, local_state, clock, transfer_state


def _two_vehicle_world_and_visits(
    *,
    first_arrived: bool = True,
    first_is_physical_head: bool = True,
    same_inlink: bool = False,
):
    world = World(
        name="tvt_mp_binding_transfer",
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
    world.addLink("in_a", "orig_a", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("in_b", "orig_b", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1)
    first_vehicle = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second_vehicle = world.addVehicle("orig_b", "dest_b", 0, name="second_veh")
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10
    in_a = world.get_link("in_a")
    in_b = world.get_link("in_b")
    outlink = world.get_link("out")
    side = world.get_link("side")
    merge = world.get_node("merge")
    first_inlink = in_a
    second_inlink = in_a if same_inlink else in_b
    _place(first_vehicle, first_inlink, outlink)
    _place(second_vehicle, second_inlink, side)
    first_vehicle.begin_order_control_visit_on_link_entry()
    second_vehicle.begin_order_control_visit_on_link_entry()
    if first_is_physical_head:
        first_inlink.vehicles.append(first_vehicle)
        if same_inlink:
            first_inlink.vehicles.append(second_vehicle)
        else:
            second_inlink.vehicles.append(second_vehicle)
    else:
        # The second binding vehicle is the physical head. The first is behind it.
        first_inlink.vehicles.append(second_vehicle)
        first_inlink.vehicles.append(first_vehicle)
        first_vehicle.leader = second_vehicle
        second_vehicle.follower = first_vehicle
    if first_arrived:
        merge.incoming_vehicles.append(first_vehicle)
    merge.incoming_vehicles.append(second_vehicle)
    visits = (
        _binding_visit(first_vehicle, rank=1, route_name="out", inlink_name="in_a"),
        _binding_visit(
            second_vehicle,
            rank=2,
            route_name="side",
            inlink_name=second_inlink.name,
        ),
    )
    return world, visits


def _two_vehicle_case(
    *,
    first_arrived: bool = True,
    first_is_physical_head: bool = True,
    same_inlink: bool = False,
):
    world, visits = _two_vehicle_world_and_visits(
        first_arrived=first_arrived,
        first_is_physical_head=first_is_physical_head,
        same_inlink=same_inlink,
    )
    return _fixture_from_world_and_visits(world, visits)


def _local_vehicle(local_state, vehicle_name: str):
    return local_state.local_vehicle_by_real_vehicle_name[vehicle_name]


def test_public_scan_result_is_frozen():
    # The first visit is not arrived, so it is skipped. The second visit can
    # pass. Nothing after that remains, so the scan completes.
    _world_object, _local_state, _clock, transfer_state = _two_vehicle_case(
        first_arrived=False
    )
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert isinstance(result, OrderControlTvtMpBindingTransferScanResult)
    assert isinstance(result.transferred_binding_visit_keys, tuple)
    assert isinstance(result.temporarily_skipped_visits, tuple)
    assert result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert (
        result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED
    )
    try:
        result.stop_reason = None  # type: ignore[misc]
        raise AssertionError("expected frozen scan result")
    except dataclasses.FrozenInstanceError:
        pass


def _passage_snapshot(local_state, vehicle_name: str) -> dict:
    """Fields updated by one UXsim / BATCH reference passage."""
    local_world = local_state.local_world
    vehicle = _local_vehicle(local_state, vehicle_name)
    in_a = local_world.get_link("in_a")
    outlink = local_world.get_link("out")
    target_node = local_state.target_node
    leader_name = None
    if vehicle.leader is not None:
        leader_name = vehicle.leader.name
    follower_name = None
    if vehicle.follower is not None:
        follower_name = vehicle.follower.name
    current_visit = vehicle.order_control_current_visit
    current_visit_record = None
    if current_visit is not None:
        visit_node = current_visit.get("node")
        visit_inlink = current_visit.get("inlink")
        current_visit_record = (
            current_visit.get("visit_id"),
            None if visit_node is None else visit_node.name,
            None if visit_inlink is None else visit_inlink.name,
            current_visit.get("earliest_arrival_timestep"),
            current_visit.get("arrival_time"),
            current_visit.get("arrival_tiebreaker"),
            current_visit.get("batch_assignment"),
        )
    entered_names = {}
    for entry_time, entered_vehicle in outlink.vehicles_enter_log.items():
        entered_names[entry_time] = entered_vehicle.name
    last_inlink_name = None
    if target_node.last_order_control_inlink is not None:
        last_inlink_name = target_node.last_order_control_inlink.name
    incoming_names = []
    for incoming_vehicle in target_node.incoming_vehicles:
        incoming_names.append(incoming_vehicle.name)
    inlink_names = []
    for queued_vehicle in in_a.vehicles:
        inlink_names.append(queued_vehicle.name)
    outlink_names = []
    for queued_vehicle in outlink.vehicles:
        outlink_names.append(queued_vehicle.name)
    return {
        "link_name": vehicle.link.name,
        "x": vehicle.x,
        "v": vehicle.v,
        "lane": vehicle.lane,
        "move_remain": vehicle.move_remain,
        "link_arrival_time": vehicle.link_arrival_time,
        "current_visit": current_visit_record,
        "leader_name": leader_name,
        "follower_name": follower_name,
        "inlink_vehicle_names": inlink_names,
        "outlink_vehicle_names": outlink_names,
        "inlink_capacity_out_remain": in_a.capacity_out_remain,
        "outlink_capacity_in_remain": outlink.capacity_in_remain,
        "node_flow_capacity_remain": target_node.flow_capacity_remain,
        "cum_departure_last": in_a.cum_departure[-1],
        "cum_arrival_last": outlink.cum_arrival[-1],
        "traveltime_actual": list(in_a.traveltime_actual),
        "vehicles_enter_log": entered_names,
        "incoming_vehicle_names": incoming_names,
        "last_inlink_name": last_inlink_name,
        "last_entry_timestep": target_node.last_order_control_entry_timestep,
    }


def test_one_transfer_matches_uxsim_passage_update():
    world, local_state, _clock, transfer_state = _two_vehicle_case()
    reference_world, reference_local_state, _reference_clock, _reference_transfer = (
        _two_vehicle_case()
    )
    # After the first vehicle passes, the second is on another inlink.
    # Clearance is not met in the same timestep, so the scan stops there.
    local_state.target_node.order_control_clearance_timesteps = 5
    reference_local_state.target_node.order_control_clearance_timesteps = 5
    real_x = world.VEHICLES["first_veh"].x
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    reference_vehicle = _local_vehicle(reference_local_state, "first_veh")
    _transfer_vehicle_reference(
        reference_local_state.target_node,
        reference_local_state.local_world,
        reference_vehicle,
        reference_vehicle.link,
        reference_local_state.local_world.get_link("out"),
    )
    first = _local_vehicle(local_state, "first_veh")
    outlink = local_state.local_world.get_link("out")
    in_a = local_state.local_world.get_link("in_a")
    assert result.transferred_binding_visit_keys == (("first_veh", 1),)
    assert result.stopped_binding_visit_key == ("second_veh", 1)
    assert (
        result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
    )
    assert first.link is outlink
    assert first not in in_a.vehicles
    assert first in outlink.vehicles
    assert first not in local_state.target_node.incoming_vehicles
    assert in_a.capacity_out_remain == 9.0
    assert outlink.capacity_in_remain == 9.0
    assert local_state.target_node.flow_capacity_remain == 9.0
    assert in_a.cum_departure[-1] == local_state.local_world.DELTAN
    assert outlink.cum_arrival[-1] == local_state.local_world.DELTAN
    assert outlink.vehicles_enter_log[10 * local_state.local_world.DELTAT] is first
    assert local_state.target_node.last_order_control_inlink is in_a
    assert local_state.target_node.last_order_control_entry_timestep == 10
    assert first.order_control_current_visit is None
    assert first.move_remain == 0
    assert world.VEHICLES["first_veh"].x == real_x
    assert world.T == 10
    assert reference_world.T == 10
    assert reference_world.VEHICLES["first_veh"].x == real_x
    # Node.transfer() would also end waiting trips and clear every incoming
    # vehicle. This one-vehicle update matches the shared passage body, and
    # the vehicle that did not pass stays in incoming_vehicles.
    assert _passage_snapshot(local_state, "first_veh") == _passage_snapshot(
        reference_local_state,
        "first_veh",
    )
    assert _passage_snapshot(local_state, "second_veh") == _passage_snapshot(
        reference_local_state,
        "second_veh",
    )
    assert "second_veh" in [
        vehicle.name for vehicle in local_state.target_node.incoming_vehicles
    ]


def test_unarrived_first_visit_does_not_block_a_later_visit():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case(
        first_arrived=False
    )
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert result.temporarily_skipped_visits[0].binding_visit_key == ("first_veh", 1)
    assert (
        result.temporarily_skipped_visits[0].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
    )
    assert result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert _local_vehicle(local_state, "first_veh").link.name == "in_a"
    assert _local_vehicle(local_state, "second_veh").link.name == "side"
    assert ("first_veh", 1) not in transfer_state.transferred_binding_visit_keys


def test_vehicle_behind_the_head_does_not_block_the_physical_head():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case(
        same_inlink=True,
        first_is_physical_head=False,
    )
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert (
        result.temporarily_skipped_visits[0].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD
    )
    assert result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert _local_vehicle(local_state, "first_veh").link.name == "in_a"
    assert _local_vehicle(local_state, "second_veh").link.name == "side"


def test_same_inlink_allows_the_next_head_in_the_same_timestep():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case(
        same_inlink=True
    )
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert result.transferred_binding_visit_keys == (
        ("first_veh", 1),
        ("second_veh", 1),
    )
    assert result.temporarily_skipped_visits == ()
    assert (
        result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED
    )
    assert _local_vehicle(local_state, "first_veh").link.name == "out"
    assert _local_vehicle(local_state, "second_veh").link.name == "side"
    assert list(local_state.local_world.get_link("in_a").vehicles) == []


def test_inlink_capacity_shortage_does_not_block_another_inlink():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case()
    local_state.local_world.get_link("in_a").capacity_out_remain = 0.0
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert (
        result.temporarily_skipped_visits[0].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE
    )
    assert result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert local_state.local_world.get_link("in_a").capacity_out_remain == 0.0
    assert _local_vehicle(local_state, "first_veh").x == 200.0


def test_outlink_entry_space_shortage_skips_only_that_visit():
    world = World(
        name="tvt_mp_binding_entry_space",
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
    world.addLink("in_a", "orig_a", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("in_b", "orig_b", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1)
    first_vehicle = world.addVehicle("orig_a", "dest", 0, name="first_veh")
    second_vehicle = world.addVehicle("orig_b", "dest_b", 0, name="second_veh")
    blocker = world.addVehicle("orig_a", "dest", 0, name="blocker")
    world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10
    in_a = world.get_link("in_a")
    in_b = world.get_link("in_b")
    outlink = world.get_link("out")
    side = world.get_link("side")
    merge = world.get_node("merge")
    _place(first_vehicle, in_a, outlink)
    _place(second_vehicle, in_b, side)
    _place(blocker, outlink, None)
    blocker.x = 0.0
    first_vehicle.begin_order_control_visit_on_link_entry()
    second_vehicle.begin_order_control_visit_on_link_entry()
    in_a.vehicles.append(first_vehicle)
    in_b.vehicles.append(second_vehicle)
    outlink.vehicles.append(blocker)
    merge.incoming_vehicles.append(first_vehicle)
    merge.incoming_vehicles.append(second_vehicle)
    visits = (
        _binding_visit(first_vehicle, rank=1, route_name="out", inlink_name="in_a"),
        _binding_visit(second_vehicle, rank=2, route_name="side", inlink_name="in_b"),
    )
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(("first_veh", 1),),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=visits,
        k_last_buyer=1,
        k_decision_window=2,
        k_fixed=2,
    )
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    transfer_state = initialize_tvt_mp_candidate_binding_transfer_state(clock)
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert (
        result.temporarily_skipped_visits[0].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE
    )
    assert result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert _local_vehicle(local_state, "first_veh").link.name == "in_a"
    assert local_state.local_world.get_link("out").capacity_in_remain == 10.0


def test_clearance_stops_the_scan_before_later_visits():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case()
    local_state.target_node.last_order_control_inlink = local_state.local_world.get_link(
        "in_b"
    )
    local_state.target_node.last_order_control_entry_timestep = 10
    local_state.target_node.order_control_clearance_timesteps = 3
    before_x = _local_vehicle(local_state, "second_veh").x
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert result.transferred_binding_visit_keys == ()
    assert result.temporarily_skipped_visits == ()
    assert (
        result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
    )
    assert result.stopped_binding_visit_key == ("first_veh", 1)
    assert _local_vehicle(local_state, "second_veh").x == before_x
    assert _local_vehicle(local_state, "second_veh").link.name == "in_b"
    assert local_state.target_node.last_order_control_entry_timestep == 10


def test_skipped_visit_is_retried_from_the_front_next_timestep():
    _world_object, local_state, clock, transfer_state = _two_vehicle_case(
        first_arrived=False
    )
    local_state.target_node.order_control_clearance_timesteps = 0
    first_result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert first_result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert ("first_veh", 1) not in transfer_state.transferred_binding_visit_keys
    first_vehicle = _local_vehicle(local_state, "first_veh")
    local_state.target_node.incoming_vehicles.append(first_vehicle)
    advance_tvt_mp_candidate_virtual_time_one_step(clock)
    second_result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert second_result.virtual_timestep == 11
    assert second_result.transferred_binding_visit_keys == (("first_veh", 1),)
    assert ("second_veh", 1) not in second_result.transferred_binding_visit_keys
    assert transfer_state.transferred_binding_visit_keys == (
        ("second_veh", 1),
        ("first_veh", 1),
    )
    assert first_vehicle.link.name == "out"


def test_binding_sequence_still_contains_a_skipped_visit():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case(
        first_arrived=False
    )
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(transfer_state)
    remaining_keys = [
        visit.visit_key
        for visit in local_state.binding_rank_sequence.visits_in_binding_order
    ]
    assert remaining_keys == [("first_veh", 1), ("second_veh", 1)]
    assert transfer_state.transferred_binding_visit_keys == (("second_veh", 1),)


def test_outlink_inflow_capacity_shortage_does_not_block_another_outlink():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case()
    local_world = local_state.local_world
    outlink = local_world.get_link("out")
    side = local_world.get_link("side")
    in_a = local_world.get_link("in_a")
    deltan = local_world.DELTAN
    # Only the first visit's formal outlink lacks inflow capacity.
    outlink.capacity_in_remain = deltan - 1.0
    in_a.capacity_out_remain = 10.0
    side.capacity_in_remain = 10.0
    local_state.target_node.flow_capacity_remain = 10.0
    before_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    after_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    assert (
        result.temporarily_skipped_visits[0].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE
    )
    assert result.temporarily_skipped_visits[0].binding_visit_key == ("first_veh", 1)
    assert result.transferred_binding_visit_keys == (("second_veh", 1),)
    assert ("first_veh", 1) not in transfer_state.transferred_binding_visit_keys
    assert (
        result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED
    )
    assert outlink.capacity_in_remain == deltan - 1.0
    assert in_a.capacity_out_remain == 10.0
    assert local_state.target_node.flow_capacity_remain == 9.0
    assert _local_vehicle(local_state, "first_veh").link.name == "in_a"
    assert _local_vehicle(local_state, "second_veh").link.name == "side"
    assert before_snapshot["first_veh"] == after_snapshot["first_veh"]
    assert before_snapshot["in_a"] == after_snapshot["in_a"]
    assert before_snapshot["out"] == after_snapshot["out"]


def test_node_flow_capacity_shortage_skips_all_binding_visits_in_order():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case()
    local_world = local_state.local_world
    target_node = local_state.target_node
    deltan = local_world.DELTAN
    # Node flow capacity is shared by every visit at this Node.
    target_node.flow_capacity = 1.0
    target_node.flow_capacity_remain = deltan - 1.0
    before_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    after_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    assert result.transferred_binding_visit_keys == ()
    assert transfer_state.transferred_binding_visit_keys == ()
    assert (
        result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED
    )
    assert (
        result.stop_reason
        is not OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
    )
    assert len(result.temporarily_skipped_visits) == 2
    assert (
        result.temporarily_skipped_visits[0].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NODE_FLOW_CAPACITY_UNAVAILABLE
    )
    assert (
        result.temporarily_skipped_visits[1].skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NODE_FLOW_CAPACITY_UNAVAILABLE
    )
    assert result.temporarily_skipped_visits[0].binding_visit_key == ("first_veh", 1)
    assert result.temporarily_skipped_visits[1].binding_visit_key == ("second_veh", 1)
    assert before_snapshot == after_snapshot


def test_invalid_formal_route_name_raises_before_any_traffic_change():
    world, visits = _two_vehicle_world_and_visits()
    invalid_route_name = "in_a"
    invalid_first_visit = dataclasses.replace(
        visits[0],
        route_next_link_name=invalid_route_name,
    )
    invalid_visits = (invalid_first_visit, visits[1])
    _world_object, local_state, _clock, transfer_state = _fixture_from_world_and_visits(
        world,
        invalid_visits,
    )
    before_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    try:
        scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(transfer_state)
        raise AssertionError("expected ValueError for invalid formal route")
    except ValueError as error:
        message = str(error)
        assert "merge" in message
        assert invalid_route_name in message
        assert "outlink" in message
    after_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    assert before_snapshot == after_snapshot


def test_route_next_link_mismatch_raises_before_any_traffic_change():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case()
    first_vehicle = _local_vehicle(local_state, "first_veh")
    formal_outlink = local_state.local_world.get_link("out")
    mismatched_outlink = local_state.local_world.get_link("side")
    assert formal_outlink.name == "out"
    first_vehicle.route_next_link = mismatched_outlink
    before_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    try:
        scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(transfer_state)
        raise AssertionError("expected RuntimeError for route_next_link mismatch")
    except RuntimeError as error:
        message = str(error)
        assert "first_veh" in message
        assert "side" in message
        assert "out" in message
    after_snapshot = _traffic_state_snapshot(local_state, transfer_state)
    assert before_snapshot == after_snapshot


def test_transferred_binding_visit_keys_are_protected_via_public_api():
    _world_object, local_state, _clock, transfer_state = _two_vehicle_case(
        first_arrived=False
    )
    assert isinstance(
        transfer_state,
        OrderControlTvtMpCandidateBindingTransferState,
    )
    first_scan = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    public_keys = transfer_state.transferred_binding_visit_keys
    assert isinstance(public_keys, tuple)
    assert public_keys == (("second_veh", 1),)
    assert ("first_veh", 1) not in public_keys
    for skipped_visit in first_scan.temporarily_skipped_visits:
        assert skipped_visit.binding_visit_key not in public_keys
    try:
        public_keys.append(("fake_veh", 99))  # type: ignore[attr-defined]
        raise AssertionError("tuple append should fail")
    except AttributeError:
        pass
    combined_keys = public_keys + (("fake_veh", 99),)
    assert combined_keys == (("second_veh", 1), ("fake_veh", 99))
    assert transfer_state.transferred_binding_visit_keys == (("second_veh", 1),)
    try:
        transfer_state.transferred_binding_visit_keys = ()  # type: ignore[misc]
        raise AssertionError("property assignment should fail")
    except AttributeError:
        pass
    assert transfer_state.transferred_binding_visit_keys == (("second_veh", 1),)
    second_scan = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    assert second_scan.transferred_binding_visit_keys == ()
    assert transfer_state.transferred_binding_visit_keys == (("second_veh", 1),)


TESTS = (
    test_public_scan_result_is_frozen,
    test_one_transfer_matches_uxsim_passage_update,
    test_same_inlink_allows_the_next_head_in_the_same_timestep,
    test_unarrived_first_visit_does_not_block_a_later_visit,
    test_vehicle_behind_the_head_does_not_block_the_physical_head,
    test_inlink_capacity_shortage_does_not_block_another_inlink,
    test_outlink_inflow_capacity_shortage_does_not_block_another_outlink,
    test_node_flow_capacity_shortage_skips_all_binding_visits_in_order,
    test_invalid_formal_route_name_raises_before_any_traffic_change,
    test_route_next_link_mismatch_raises_before_any_traffic_change,
    test_transferred_binding_visit_keys_are_protected_via_public_api,
    test_outlink_entry_space_shortage_skips_only_that_visit,
    test_clearance_stops_the_scan_before_later_visits,
    test_skipped_visit_is_retried_from_the_front_next_timestep,
    test_binding_sequence_still_contains_a_skipped_visit,
)


if __name__ == "__main__":
    for test_function in TESTS:
        test_function()
    print(f"binding transfer scan tests passed ({len(TESTS)} tests).")
