# Tests for unbound temporary FCFS node passage at one virtual timestep.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_unbound_fcfs_transfer.py

from __future__ import annotations

import copy
import dataclasses

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferScanResult,
    OrderControlTvtMpBindingTransferStopReason,
    initialize_tvt_mp_candidate_binding_transfer_state,
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_unbound_fcfs_transfer import (
    OrderControlTvtMpUnboundFcfsStopReason,
    OrderControlTvtMpUnboundFcfsTransferResult,
    OrderControlTvtMpUnboundRouteClassification,
    OrderControlTvtMpUnboundTemporarySkipReason,
    initialize_tvt_mp_candidate_unbound_fcfs_transfer_state,
    scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep,
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
        baseline_arrival_timestep=8,
        arrival_tiebreaker=0.1,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
    )


def _place(vehicle, link, route_link, arrival_time, tiebreaker) -> None:
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
    vehicle.move_remain = 150.0
    vehicle.begin_order_control_visit_on_link_entry()
    vehicle.order_control_current_visit["arrival_time"] = arrival_time
    vehicle.order_control_current_visit["arrival_tiebreaker"] = tiebreaker


def _register(collector, vehicle, *, arrived: bool, route_name):
    visit = vehicle.order_control_current_visit
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle.id,
        node_name="merge",
        inlink_name=vehicle.link.name,
        visit_id=visit["visit_id"],
        was_arrived_at_snapshot=arrived,
        baseline_arrival_timestep=8 if arrived else None,
        arrival_tiebreaker=0.1 if arrived else None,
        route_next_link_name=route_name if arrived else None,
        baseline_passage_timestep=None,
    )
    if not arrived and route_name is not None:
        collector.record_baseline_arrival(
            vehicle_name=vehicle.name,
            visit_id=visit["visit_id"],
            node_name="merge",
            baseline_arrival_timestep=9,
            arrival_tiebreaker=0.2,
            route_next_link_name=route_name,
        )


def _completed_binding_result(node_name="merge", timestep=10):
    return OrderControlTvtMpBindingTransferScanResult(
        node_name=node_name,
        virtual_timestep=timestep,
        transferred_binding_visit_keys=(),
        temporarily_skipped_visits=(),
        stop_reason=OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED,
        stopped_binding_visit_key=None,
    )


def _prepare(vehicles_spec):
    world = World(
        name="tvt_mp_unbound_fcfs",
        deltan=1,
        tmax=40,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    world.addNode("orig_a", 0, 0)
    world.addNode("orig_b", 0, 1)
    world.addNode("orig_c", 0, 2)
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
    world.addLink("in_c", "orig_c", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1)
    created = {}
    for spec in vehicles_spec:
        created[spec["name"]] = world.addVehicle(
            spec["origin"], spec["dest"], 0, name=spec["name"]
        )
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10
    merge = world.get_node("merge")
    collector = OrderControlBaselineCollector()
    binding_vehicles = []
    for spec in vehicles_spec:
        vehicle = created[spec["name"]]
        inlink = world.get_link(spec["inlink"])
        route = world.get_link(spec["route"])
        _place(vehicle, inlink, route, spec["arrival"], spec["tie"])
        inlink.vehicles.append(vehicle)
        if spec.get("incoming", True):
            merge.incoming_vehicles.append(vehicle)
        if spec.get("register", True):
            _register(
                collector,
                vehicle,
                arrived=spec.get("arrived", False),
                route_name=spec.get("collector_route"),
            )
        if spec.get("binding"):
            binding_vehicles.append(vehicle)
    if not binding_vehicles:
        raise AssertionError("fixture needs one binding vehicle")
    visits = tuple(
        _binding_visit(
            vehicle,
            rank=index + 1,
            route_name=vehicle.route_next_link.name,
            inlink_name=vehicle.link.name,
        )
        for index, vehicle in enumerate(binding_vehicles)
    )
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=((binding_vehicles[0].name, 1),),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=visits,
        k_last_buyer=1,
        k_decision_window=1,
        k_fixed=1,
    )
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    node = local_state.target_node
    node.flow_capacity_remain = 10.0
    node.order_control_clearance_timesteps = 0
    for link in local_state.inlinks + local_state.outlinks:
        link.capacity_out_remain = 10.0
        link.capacity_in_remain = 10.0
    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    binding_state = initialize_tvt_mp_candidate_binding_transfer_state(clock)
    return world, local_state, binding_state, collector


def _build(vehicles_spec):
    world, local_state, binding_state, collector = _prepare(vehicles_spec)
    unbound_state = initialize_tvt_mp_candidate_unbound_fcfs_transfer_state(
        binding_state, collector
    )
    return world, local_state, binding_state, unbound_state, collector


def _local(local_state, name):
    return local_state.local_vehicle_by_real_vehicle_name[name]


def _rng_state(local_world):
    return copy.deepcopy(local_world.rng.bit_generator.state)


def _traffic_fingerprint(local_state):
    node = local_state.target_node
    incoming_names = []
    for vehicle in node.incoming_vehicles:
        incoming_names.append(vehicle.name)
    inlink_states = []
    for link in local_state.inlinks:
        vehicle_names = []
        for queued in link.vehicles:
            vehicle_names.append(queued.name)
        inlink_states.append((link.name, link.capacity_out_remain, tuple(vehicle_names)))
    outlink_states = []
    for link in local_state.outlinks:
        vehicle_names = []
        for queued in link.vehicles:
            vehicle_names.append(queued.name)
        outlink_states.append((link.name, link.capacity_in_remain, tuple(vehicle_names)))
    return {
        "incoming_names": incoming_names,
        "flow_capacity_remain": node.flow_capacity_remain,
        "inlinks": tuple(inlink_states),
        "outlinks": tuple(outlink_states),
    }


def _scan(unbound_state, binding_result=None):
    if binding_result is None:
        binding_result = _completed_binding_result()
    return scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep(
        unbound_state, binding_result
    )


def _spec(name, inlink, route, arrival, tie, **kwargs):
    origin = {"in_a": "orig_a", "in_b": "orig_b", "in_c": "orig_c"}[inlink]
    dest = "dest" if route == "out" else "dest_b"
    row = {
        "name": name,
        "origin": origin,
        "dest": dest,
        "inlink": inlink,
        "route": route,
        "arrival": arrival,
        "tie": tie,
    }
    row.update(kwargs)
    return row


def test_public_types_are_frozen_and_second_scan_is_rejected():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, collector_route="side"),
        ]
    )
    result = _scan(unbound_state)
    assert isinstance(result, OrderControlTvtMpUnboundFcfsTransferResult)
    assert isinstance(result.transferred_vehicle_records, tuple)
    assert isinstance(result.temporary_skips, tuple)
    assert isinstance(result.candidate_vehicle_names_in_fcfs_order, tuple)
    assert isinstance(unbound_state.completed_virtual_timesteps, tuple)
    assert isinstance(unbound_state.transferred_unbound_vehicle_names, tuple)
    assert result.stop_reason is OrderControlTvtMpUnboundFcfsStopReason.CANDIDATES_COMPLETED
    assert unbound_state.completed_virtual_timesteps == (10,)
    assert result.transferred_vehicle_records[0].vehicle_name == "free"
    assert (
        result.transferred_vehicle_records[0].route_classification
        is OrderControlTvtMpUnboundRouteClassification.BASELINE_ARRIVAL_ROUTE
    )
    try:
        result.stop_reason = None  # type: ignore[misc]
        raise AssertionError("expected frozen result")
    except dataclasses.FrozenInstanceError:
        pass
    for member in OrderControlTvtMpUnboundRouteClassification:
        assert isinstance(member, OrderControlTvtMpUnboundRouteClassification)
    for member in OrderControlTvtMpUnboundFcfsStopReason:
        assert isinstance(member, OrderControlTvtMpUnboundFcfsStopReason)
    for member in OrderControlTvtMpUnboundTemporarySkipReason:
        assert isinstance(member, OrderControlTvtMpUnboundTemporarySkipReason)
    before = unbound_state.transferred_unbound_vehicle_names
    try:
        _scan(unbound_state)
        raise AssertionError("expected second scan to fail")
    except RuntimeError as error:
        assert "already completed" in str(error)
    assert unbound_state.transferred_unbound_vehicle_names == before
    assert _local(local_state, "free").link.name == "side"


def test_binding_clearance_and_node_capacity_do_not_start():
    world, local_state, _binding, unbound_state, collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, collector_route="side"),
        ]
    )
    export_before = collector.export_node_baseline_visits("merge")
    rng_before = _rng_state(local_state.local_world)
    clearance = OrderControlTvtMpBindingTransferScanResult(
        node_name="merge",
        virtual_timestep=10,
        transferred_binding_visit_keys=(),
        temporarily_skipped_visits=(),
        stop_reason=OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED,
        stopped_binding_visit_key=("bound", 1),
    )
    result = _scan(unbound_state, clearance)
    assert (
        result.stop_reason
        is OrderControlTvtMpUnboundFcfsStopReason.BINDING_CLEARANCE_STOPPED_NOT_STARTED
    )
    assert result.candidate_vehicle_names_in_fcfs_order == ()
    assert _local(local_state, "free").link.name == "in_b"
    assert unbound_state.completed_virtual_timesteps == (10,)
    assert collector.export_node_baseline_visits("merge") == export_before
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert world.T == 10

    _world2, local2, _b2, unbound2, _c2 = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, collector_route="side"),
        ]
    )
    local2.target_node.flow_capacity_remain = 0.0
    result2 = _scan(unbound2)
    assert (
        result2.stop_reason
        is OrderControlTvtMpUnboundFcfsStopReason.NODE_FLOW_CAPACITY_UNAVAILABLE_BEFORE_START
    )
    assert _local(local2, "free").link.name == "in_b"
    assert unbound2.completed_virtual_timesteps == (10,)
    try:
        _scan(unbound2)
        raise AssertionError("expected second scan to fail")
    except RuntimeError:
        pass


def test_scan_result_identity_must_match():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
        ]
    )
    traffic_before = _traffic_fingerprint(local_state)
    wrong_node = _completed_binding_result(node_name="other")
    try:
        _scan(unbound_state, wrong_node)
        raise AssertionError("expected node mismatch")
    except RuntimeError as error:
        assert "does not match" in str(error)
    assert unbound_state.completed_virtual_timesteps == ()
    assert _traffic_fingerprint(local_state) == traffic_before
    wrong_time = _completed_binding_result(timestep=9)
    try:
        _scan(unbound_state, wrong_time)
        raise AssertionError("expected timestep mismatch")
    except RuntimeError as error:
        assert "timestep" in str(error)
    assert unbound_state.completed_virtual_timesteps == ()
    assert _traffic_fingerprint(local_state) == traffic_before


def test_missing_collector_record_is_not_class_4():
    _world, local_state, _binding, unbound_state, collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, collector_route=None),
        ]
    )
    free = _local(local_state, "free")
    visit_id = free.order_control_current_visit["visit_id"]
    collector._visit_records_by_primary_key.pop(("free", visit_id))
    traffic_before = _traffic_fingerprint(local_state)
    incoming_before = list(local_state.target_node.incoming_vehicles)
    try:
        _scan(unbound_state)
        raise AssertionError("expected missing collector record to fail")
    except RuntimeError as error:
        message = str(error)
        assert "not route class 4" in message
        assert "free" in message
    assert collector.get_baseline_visit_snapshot("free", visit_id) is None
    assert free.link.name == "in_b"
    assert unbound_state.completed_virtual_timesteps == ()
    assert unbound_state.transferred_unbound_vehicle_names == ()
    assert _traffic_fingerprint(local_state) == traffic_before
    assert local_state.target_node.incoming_vehicles == incoming_before


def test_snapshot_outside_research_vehicle_is_inconsistency():
    world, local_state, binding_state, unbound_state, collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, register=False),
        ]
    )
    free = _local(local_state, "free")
    visit_key = (free.name, free.order_control_current_visit["visit_id"])
    assert visit_key not in unbound_state.snapshot_fixed_visit_keys
    traffic_before = _traffic_fingerprint(local_state)
    incoming_before = list(local_state.target_node.incoming_vehicles)
    export_before = collector.export_node_baseline_visits("merge")
    binding_before = binding_state.transferred_binding_visit_keys
    try:
        _scan(unbound_state)
        raise AssertionError("expected snapshot-outside research vehicle to fail")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "free" in message
        assert str(visit_key) in message
        assert "snapshot-fixed set" in message
        assert "not route class 4" in message
    assert free.link.name == "in_b"
    assert free in local_state.target_node.incoming_vehicles
    assert unbound_state.completed_virtual_timesteps == ()
    assert unbound_state.transferred_unbound_vehicle_names == ()
    assert _traffic_fingerprint(local_state) == traffic_before
    assert local_state.target_node.incoming_vehicles == incoming_before
    assert collector.export_node_baseline_visits("merge") == export_before
    assert binding_state.transferred_binding_visit_keys == binding_before
    assert collector.get_baseline_visit_snapshot(free.name, visit_key[1]) is None
    assert world.T == 10


def test_fcfs_order_ignores_merge_priority_and_rng():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 9.0, 0.9, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("late", "in_b", "side", 5.0, 0.1, collector_route="side"),
            _spec("early", "in_c", "out", 1.0, 0.8, collector_route="out"),
        ]
    )
    local_state.target_node.merge_priority = "ignored"
    rng_before = _rng_state(local_state.local_world)
    result = _scan(unbound_state)
    assert result.candidate_vehicle_names_in_fcfs_order == ("early", "late")
    assert [record.vehicle_name for record in result.transferred_vehicle_records] == [
        "early"
    ]
    assert result.stop_reason is OrderControlTvtMpUnboundFcfsStopReason.CLEARANCE_NOT_SATISFIED
    assert result.stopped_vehicle_name == "late"
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert local_state.local_world.T == 10


def test_tiebreaker_then_vehicle_id():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("b_veh", "in_b", "side", 3.0, 0.4, collector_route="side"),
            _spec("c_veh", "in_c", "out", 3.0, 0.2, collector_route="out"),
        ]
    )
    result = _scan(unbound_state)
    assert result.candidate_vehicle_names_in_fcfs_order[0] == "c_veh"


def test_binding_visits_are_not_unbound_even_if_skipped():
    world, local_state, binding_state, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, collector_route="side"),
        ]
    )
    bound = _local(local_state, "bound")
    blocker = _local(local_state, "free")
    in_a = local_state.local_world.get_link("in_a")
    real_incoming_before = [item.name for item in world.get_node("merge").incoming_vehicles]
    in_a.vehicles.clear()
    in_a.vehicles.append(blocker)
    in_a.vehicles.append(bound)
    local_state.target_node.incoming_vehicles = [bound, blocker]
    blocker.link = in_a
    binding_result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        binding_state
    )
    assert binding_result.transferred_binding_visit_keys == ()
    assert len(binding_result.temporarily_skipped_visits) == 1
    result = _scan(unbound_state, binding_result)
    names = result.candidate_vehicle_names_in_fcfs_order
    assert "bound" not in names
    assert bound.link is in_a
    assert [item.name for item in world.get_node("merge").incoming_vehicles] == real_incoming_before
    assert binding_state.transferred_binding_visit_keys == ()


def test_class1_keeps_snapshot_route_when_other_outlink_is_open():
    _world, local_state, _binding, unbound_state, collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("snap", "in_b", "side", 2.0, 0.2, arrived=True, collector_route="side"),
        ]
    )
    ledger_before = collector.export_node_baseline_visits("merge")
    side = local_state.local_world.get_link("side")
    side.capacity_in_remain = 0.0
    result = _scan(unbound_state)
    assert result.transferred_vehicle_records == ()
    assert result.temporary_skips[0].skip_reason is (
        OrderControlTvtMpUnboundTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE
    )
    assert _local(local_state, "snap").link.name == "in_b"
    assert _local(local_state, "snap").route_next_link.name == "side"
    assert collector.export_node_baseline_visits("merge") == ledger_before


def test_class3_uses_collector_route_not_copy_route():
    _world, local_state, binding_state, unbound_state, collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("mid", "in_b", "side", 2.0, 0.2, collector_route="out"),
        ]
    )
    local_vehicle = _local(local_state, "mid")
    assert local_vehicle.route_next_link.name == "side"
    export_before = collector.export_node_baseline_visits("merge")
    binding_before = binding_state.transferred_binding_visit_keys
    result = _scan(unbound_state)
    record = result.transferred_vehicle_records[0]
    assert record.outlink_name == "out"
    assert record.route_classification is (
        OrderControlTvtMpUnboundRouteClassification.BASELINE_ARRIVAL_ROUTE
    )
    assert record.selection_index is None
    assert local_vehicle.route_next_link.name == "side"
    assert local_vehicle.link.name == "out"
    assert collector.export_node_baseline_visits("merge") == export_before
    assert binding_state.transferred_binding_visit_keys == binding_before
    outlink = local_state.local_world.get_link("out")
    outlink.capacity_in_remain = 0.0
    # Already passed. A fresh case must not fall through to class 4.
    _w2, local2, _b2, unbound2, _c2 = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("mid", "in_b", "side", 2.0, 0.2, collector_route="out"),
        ]
    )
    local2.local_world.get_link("out").capacity_in_remain = 0.0
    blocked = _scan(unbound2)
    assert blocked.transferred_vehicle_records == ()
    assert blocked.temporary_skips[0].skip_reason is (
        OrderControlTvtMpUnboundTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE
    )
    assert blocked.temporary_skips[0].vehicle_name == "mid"


def test_class4_selects_by_real_vehicle_id_and_passes_immediately():
    world, local_state, binding_state, collector = _prepare(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("virt", "in_b", "side", 2.0, 0.2, collector_route=None),
        ]
    )
    local_vehicle = _local(local_state, "virt")
    real_vehicle = world.VEHICLES["virt"]
    assert real_vehicle is not local_vehicle
    assert real_vehicle.name == local_vehicle.name
    real_vehicle_id = real_vehicle.id
    if isinstance(real_vehicle_id, bool) or not isinstance(real_vehicle_id, int):
        raise AssertionError(f"real vehicle id is not an int: {real_vehicle_id!r}")
    local_vehicle.id = real_vehicle_id + 1
    assert local_vehicle.id != real_vehicle_id
    unbound_state = initialize_tvt_mp_candidate_unbound_fcfs_transfer_state(
        binding_state, collector
    )
    assert local_state.real_vehicle_id("virt") == real_vehicle_id
    assert real_vehicle.id == real_vehicle_id
    outlinks = [
        local_state.local_world.get_link("out"),
        local_state.local_world.get_link("side"),
    ]
    outlinks.sort(key=lambda link: link.id)
    expected_index = real_vehicle_id % len(outlinks)
    expected = outlinks[expected_index]
    copy_index = local_vehicle.id % len(outlinks)
    assert copy_index != expected_index
    rng_before = _rng_state(local_state.local_world)
    result = _scan(unbound_state)
    record = result.transferred_vehicle_records[0]
    assert record.route_classification is (
        OrderControlTvtMpUnboundRouteClassification.DETERMINISTIC_VIRTUAL_ROUTE
    )
    assert record.selection_index == expected_index
    assert record.acceptable_outlink_names == tuple(link.name for link in outlinks)
    assert record.outlink_name == expected.name
    assert local_vehicle.link is expected
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert real_vehicle.id == real_vehicle_id
    assert real_vehicle.link.name == "in_b"


def test_class4_empty_acceptable_is_ordinary_wait():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("virt", "in_b", "side", 2.0, 0.2, collector_route=None),
            _spec("other", "in_c", "out", 3.0, 0.3, collector_route="out"),
        ]
    )
    for name in ("out", "side"):
        local_state.local_world.get_link(name).capacity_in_remain = 0.0
    result = _scan(unbound_state)
    reasons = {skip.vehicle_name: skip.skip_reason for skip in result.temporary_skips}
    assert reasons["virt"] is OrderControlTvtMpUnboundTemporarySkipReason.ACCEPTABLE_OUTLINKS_EMPTY
    assert reasons["other"] is (
        OrderControlTvtMpUnboundTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE
    )
    assert _local(local_state, "virt").link.name == "in_b"
    assert _local(local_state, "other").link.name == "in_c"


def test_same_inlink_does_not_overtake_and_other_inlink_can_pass():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 9.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("head", "in_b", "side", 1.0, 0.1, collector_route="side"),
            _spec("tail", "in_b", "side", 2.0, 0.1, collector_route="side"),
            _spec("other", "in_c", "out", 3.0, 0.1, collector_route="out"),
        ]
    )
    in_b = local_state.local_world.get_link("in_b")
    head = _local(local_state, "head")
    tail = _local(local_state, "tail")
    in_b.vehicles.clear()
    in_b.vehicles.append(head)
    in_b.vehicles.append(tail)
    tail.leader = head
    head.follower = tail
    result = _scan(unbound_state)
    transferred = [record.vehicle_name for record in result.transferred_vehicle_records]
    assert transferred == ["head", "tail"]
    assert result.stop_reason is OrderControlTvtMpUnboundFcfsStopReason.CLEARANCE_NOT_SATISFIED
    assert result.stopped_vehicle_name == "other"
    assert tail.link.name == "side"
    assert _local(local_state, "other").link.name == "in_c"


def test_node_capacity_and_clearance_stop_without_looking_further():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 9.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("first", "in_b", "side", 1.0, 0.1, collector_route="side"),
            _spec("second", "in_b", "side", 2.0, 0.1, collector_route="side"),
        ]
    )
    in_b = local_state.local_world.get_link("in_b")
    first = _local(local_state, "first")
    second = _local(local_state, "second")
    in_b.vehicles.clear()
    in_b.vehicles.append(first)
    in_b.vehicles.append(second)
    local_state.target_node.flow_capacity_remain = 1.0
    result = _scan(unbound_state)
    assert [record.vehicle_name for record in result.transferred_vehicle_records] == ["first"]
    assert result.stop_reason is (
        OrderControlTvtMpUnboundFcfsStopReason.NODE_FLOW_CAPACITY_UNAVAILABLE
    )
    assert result.stopped_vehicle_name == "second"
    assert result.temporary_skips == ()
    assert _local(local_state, "first").link.name == "side"
    assert _local(local_state, "second").link.name == "in_b"

    _w2, local2, _b2, unbound2, _c2 = _build(
        [
            _spec("bound", "in_a", "out", 9.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("first", "in_b", "side", 1.0, 0.1, collector_route="side"),
            _spec("second", "in_c", "out", 2.0, 0.1, collector_route="out"),
        ]
    )
    node = local2.target_node
    node.last_order_control_inlink = local2.local_world.get_link("in_a")
    node.last_order_control_entry_timestep = 10
    node.order_control_clearance_timesteps = 5
    result2 = _scan(unbound2)
    assert result2.transferred_vehicle_records == ()
    assert result2.stop_reason is OrderControlTvtMpUnboundFcfsStopReason.CLEARANCE_NOT_SATISFIED
    assert result2.stopped_vehicle_name == "first"
    assert _local(local2, "second").link.name == "in_c"


def test_passage_updates_traffic_and_leaves_outside_state_unchanged():
    world, local_state, binding_state, unbound_state, collector = _build(
        [
            _spec("bound", "in_a", "out", 9.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 1.0, 0.2, collector_route="side"),
        ]
    )
    local_world = local_state.local_world
    vehicle = _local(local_state, "free")
    in_b = local_world.get_link("in_b")
    side = local_world.get_link("side")
    node = local_state.target_node
    in_before = in_b.capacity_out_remain
    out_before = side.capacity_in_remain
    node_before = node.flow_capacity_remain
    cum_departure_before = in_b.cum_departure[-1]
    cum_arrival_before = side.cum_arrival[-1]
    real_incoming = [item.name for item in world.get_node("merge").incoming_vehicles]
    export_before = collector.export_node_baseline_visits("merge")
    sequence_before = local_state.binding_rank_sequence.visits_in_binding_order
    result = _scan(unbound_state)
    assert result.transferred_vehicle_records[0].inlink_name == "in_b"
    assert in_b.capacity_out_remain == in_before - 1
    assert side.capacity_in_remain == out_before - 1
    assert node.flow_capacity_remain == node_before - 1
    assert in_b.cum_departure[-1] == cum_departure_before + 1
    assert side.cum_arrival[-1] == cum_arrival_before + 1
    assert vehicle not in in_b.vehicles
    assert vehicle in side.vehicles
    assert vehicle not in node.incoming_vehicles
    assert "bound" not in [item.name for item in node.incoming_vehicles]
    assert "free" not in [item.name for item in node.incoming_vehicles]
    entered_time = local_world.T * local_world.DELTAT
    assert side.vehicles_enter_log[entered_time] is vehicle
    assert vehicle.link is side
    expected_x = 150.0 * side.u / in_b.u
    if expected_x >= side.length:
        expected_x = side.length
    assert vehicle.x == expected_x
    assert vehicle.move_remain == 0
    assert vehicle.v == 4.0 + vehicle.x / local_world.DELTAT
    assert vehicle.lane == 0
    assert vehicle.link_arrival_time == entered_time
    assert vehicle.leader is None
    assert vehicle.follower is None
    assert list(side.vehicles)[-1] is vehicle
    assert node.last_order_control_inlink is in_b
    assert node.last_order_control_entry_timestep == 10
    assert vehicle.order_control_visit_id >= 1
    assert vehicle.order_control_current_visit is None
    assert [item.name for item in world.get_node("merge").incoming_vehicles] == real_incoming
    assert collector.export_node_baseline_visits("merge") == export_before
    assert binding_state.transferred_binding_visit_keys == ()
    assert local_state.binding_rank_sequence.visits_in_binding_order == sequence_before
    assert local_world.T == 10
    assert world.T == 10


def test_duplicate_incoming_vehicle_raises_before_completion():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("free", "in_b", "side", 2.0, 0.2, collector_route="side"),
        ]
    )
    free = _local(local_state, "free")
    traffic_before = _traffic_fingerprint(local_state)
    local_state.target_node.incoming_vehicles.append(free)
    try:
        _scan(unbound_state)
        raise AssertionError("expected duplicate incoming to fail")
    except RuntimeError as error:
        assert "twice" in str(error)
    assert unbound_state.completed_virtual_timesteps == ()
    assert unbound_state.transferred_unbound_vehicle_names == ()
    assert free.link.name == "in_b"
    assert _traffic_fingerprint(local_state)["flow_capacity_remain"] == traffic_before["flow_capacity_remain"]
    assert _traffic_fingerprint(local_state)["inlinks"] == traffic_before["inlinks"]
    assert _traffic_fingerprint(local_state)["outlinks"] == traffic_before["outlinks"]


def test_research_excluded_vehicle_is_not_a_candidate():
    _world, local_state, _binding, unbound_state, _collector = _build(
        [
            _spec("bound", "in_a", "out", 1.0, 0.1, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("taxi_veh", "in_b", "side", 2.0, 0.2, register=False),
        ]
    )
    taxi = _local(local_state, "taxi_veh")
    taxi.mode = "taxi"
    result = _scan(unbound_state)
    assert result.candidate_vehicle_names_in_fcfs_order == ()
    assert taxi.link.name == "in_b"


def test_fcfs_third_key_uses_stored_real_vehicle_id():
    world, local_state, binding_state, collector = _prepare(
        [
            _spec("bound", "in_a", "out", 9.0, 0.9, binding=True, incoming=False, arrived=True, collector_route="out"),
            _spec("first_real", "in_b", "side", 2.0, 0.2, collector_route="side"),
            _spec("second_real", "in_c", "out", 2.0, 0.2, collector_route="out"),
        ]
    )
    local_first = _local(local_state, "first_real")
    local_second = _local(local_state, "second_real")
    real_first = world.VEHICLES["first_real"].id
    real_second = world.VEHICLES["second_real"].id
    assert real_first != real_second
    if real_first < real_second:
        local_first.id = real_second + 50
        local_second.id = real_first
        expected_order = ("first_real", "second_real")
    else:
        local_first.id = real_second
        local_second.id = real_first + 50
        expected_order = ("second_real", "first_real")
    assert local_state.real_vehicle_id("first_real") == real_first
    assert local_state.real_vehicle_id("second_real") == real_second
    unbound_state = initialize_tvt_mp_candidate_unbound_fcfs_transfer_state(
        binding_state, collector
    )
    result = _scan(unbound_state)
    assert result.candidate_vehicle_names_in_fcfs_order == expected_order
    assert world.VEHICLES["first_real"].id == real_first
    assert world.VEHICLES["second_real"].id == real_second


def _run_all() -> None:
    tests = [
        test_public_types_are_frozen_and_second_scan_is_rejected,
        test_binding_clearance_and_node_capacity_do_not_start,
        test_scan_result_identity_must_match,
        test_missing_collector_record_is_not_class_4,
        test_snapshot_outside_research_vehicle_is_inconsistency,
        test_fcfs_order_ignores_merge_priority_and_rng,
        test_tiebreaker_then_vehicle_id,
        test_binding_visits_are_not_unbound_even_if_skipped,
        test_class1_keeps_snapshot_route_when_other_outlink_is_open,
        test_class3_uses_collector_route_not_copy_route,
        test_class4_selects_by_real_vehicle_id_and_passes_immediately,
        test_class4_empty_acceptable_is_ordinary_wait,
        test_same_inlink_does_not_overtake_and_other_inlink_can_pass,
        test_node_capacity_and_clearance_stop_without_looking_further,
        test_passage_updates_traffic_and_leaves_outside_state_unchanged,
        test_duplicate_incoming_vehicle_raises_before_completion,
        test_research_excluded_vehicle_is_not_a_candidate,
        test_fcfs_third_key_uses_stored_real_vehicle_id,
    ]
    for test in tests:
        test()
        print(f"ok {test.__name__}")
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
