# Tests for the TVT-MP one-candidate local virtual calculation loop.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_local_virtual_calculation.py

from __future__ import annotations

import ast
import copy
import dataclasses
import inspect
from enum import Enum

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferScanResult,
    OrderControlTvtMpBindingTransferStopReason,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateFinalLinkRecord,
    OrderControlTvtMpCandidateFinalLinkRole,
    OrderControlTvtMpCandidateFinalNodeRecord,
    OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord,
    OrderControlTvtMpCandidateFinalVehicleRecord,
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateLocalVirtualCalculationState,
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
    OrderControlTvtMpCandidatePassageRecord,
    OrderControlTvtMpCandidateUnresolvedReason,
    OrderControlTvtMpCandidateVirtualTimestepResult,
    initialize_tvt_mp_candidate_local_virtual_calculation_state,
    run_tvt_mp_candidate_local_virtual_calculation,
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep,
)
from uxsim.order_control_tvt_mp_candidate_outlink_boundary import (
    OrderControlTvtMpOutlinkBoundaryMode,
)
from uxsim.order_control_tvt_mp_candidate_unbound_fcfs_transfer import (
    OrderControlTvtMpUnboundFcfsStopReason,
    OrderControlTvtMpUnboundRouteClassification,
    OrderControlTvtMpUnboundTemporarySkipReason,
    OrderControlTvtMpUnboundVehicleTransferRecord,
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
import uxsim.order_control_tvt_mp_candidate_local_virtual_calculation as orch_mod


BASELINE_T = 10

_FORBIDDEN_RESULT_FIELD_NAMES = {
    "terminal_virtual_timestep",
    "final_observation_timestep",
    "executed_traffic_timestep_count",
    "processed_timestep_count",
    "v",
    "lane",
    "leader",
    "follower",
    "move_remain",
    "link_arrival_time",
    "x_old",
    "x_next",
    "one_step_performed",
}


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
    return world


def _place(world, vehicle, link, route_link) -> None:
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
    vehicle.flag_waiting_for_trip_end = 0
    world.VEHICLES_RUNNING[vehicle.name] = vehicle


def _binding_visit(
    vehicle,
    *,
    rank: int,
    route_name: str,
    inlink_name: str,
    trade_role: OrderControlTvtMpLocalBindingTradeRole,
):
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
        trade_role=trade_role,
    )


def _register_snapshot(
    collector,
    vehicle,
    *,
    route_name: str | None,
    arrived: bool = True,
    baseline_passage_timestep: int | None = None,
) -> None:
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
    if baseline_passage_timestep is not None:
        record = collector.prepare_baseline_passage_recording(
            vehicle_name=vehicle.name,
            visit_id=visit["visit_id"],
            node_name="merge",
        )
        collector.apply_baseline_passage_timestep(record, baseline_passage_timestep)


def _outlink_boundary(name: str, terminal: str, active: int, transferred: int):
    return OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name=name,
        terminal_node_name=terminal,
        active_timestep_count=active,
        transferred_vehicle_count=transferred,
    )


def _constrained_sink_boundary():
    return OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="merge",
        outlink_results=(
            _outlink_boundary("out", "dest", 0, 0),
            _outlink_boundary("side", "dest_b", 0, 0),
        ),
    )


def _wait_without_outflow_boundary():
    return OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="merge",
        outlink_results=(
            _outlink_boundary("out", "dest", 3, 0),
            _outlink_boundary("side", "dest_b", 0, 0),
        ),
    )


def _open_capacities(local_state) -> None:
    node = local_state.target_node
    node.flow_capacity_remain = 10.0
    node.order_control_clearance_timesteps = 0
    node.last_order_control_inlink = None
    node.last_order_control_entry_timestep = None
    for link in local_state.inlinks + local_state.outlinks:
        link.capacity_out_remain = 10.0
        link.capacity_in_remain = 10.0


def _block_clearance_from_other_inlink(local_state) -> None:
    node = local_state.target_node
    other_inlink = local_state.local_world.get_link("in_b")
    node.last_order_control_inlink = other_inlink
    node.last_order_control_entry_timestep = BASELINE_T
    node.order_control_clearance_timesteps = 100


def _local_vehicle(local_state, vehicle_name: str):
    return local_state.local_vehicle_by_real_vehicle_name[vehicle_name]


def _build_sequence(visits, buyers_sorted):
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=BASELINE_T,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=buyers_sorted,
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


def _prepare_world_with_vehicles(vehicle_specs, buyers_sorted=None):
    world = _new_world("tvt_mp_one_candidate_loop")
    created = {}
    for spec in vehicle_specs:
        created[spec["name"]] = world.addVehicle(
            spec["origin"],
            spec["dest"],
            0,
            name=spec["name"],
        )
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = BASELINE_T
    merge = world.get_node("merge")
    collector = OrderControlBaselineCollector()
    binding_visits = []
    buyer_keys = []
    for spec in vehicle_specs:
        vehicle = created[spec["name"]]
        inlink = world.get_link(spec["inlink"])
        route = world.get_link(spec["route"])
        _place(world, vehicle, inlink, route)
        vehicle.begin_order_control_visit_on_link_entry()
        if spec.get("incoming", True):
            vehicle.order_control_current_visit["arrival_time"] = spec.get(
                "arrival", 1.0
            )
            vehicle.order_control_current_visit["arrival_tiebreaker"] = spec.get(
                "tie", 0.1
            )
        inlink.vehicles.append(vehicle)
        if spec.get("incoming", True):
            merge.incoming_vehicles.append(vehicle)
        if spec.get("register", True):
            _register_snapshot(
                collector,
                vehicle,
                route_name=spec.get("collector_route", spec["route"]),
                arrived=spec.get("arrived", True),
                baseline_passage_timestep=spec.get("baseline_passage"),
            )
        if spec.get("binding", True):
            role = spec.get(
                "role",
                OrderControlTvtMpLocalBindingTradeRole.BUYER,
            )
            visit = _binding_visit(
                vehicle,
                rank=len(binding_visits) + 1,
                route_name=spec["route"],
                inlink_name=spec["inlink"],
                trade_role=role,
            )
            binding_visits.append(visit)
            if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
                buyer_keys.append(visit.visit_key)
    visits = tuple(binding_visits)
    if buyers_sorted is None:
        buyers_sorted = tuple(buyer_keys)
    sequence = _build_sequence(visits, buyers_sorted)
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    return world, local_state, collector, visits


def _init_state(
    local_state,
    collector,
    *,
    horizon: int,
    boundary=None,
):
    if boundary is None:
        boundary = _constrained_sink_boundary()
    return initialize_tvt_mp_candidate_local_virtual_calculation_state(
        local_state,
        collector,
        boundary,
        horizon,
    )


def _buyer_ready_case(*, horizon: int, boundary=None, incoming: bool = True):
    world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": incoming,
            }
        ]
    )
    state = _init_state(local_state, collector, horizon=horizon, boundary=boundary)
    return world, local_state, collector, state, visits


def _forward_visit_clearance_stops_before_rear_required_buyer_case(*, horizon: int):
    """Front Visit A blocks clearance; rear required buyer B is never scanned."""
    world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "front_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
            },
            {
                "name": "rear_buyer",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.BUYER,
                "incoming": False,
            },
        ]
    )
    in_a = local_state.local_world.get_link("in_a")
    front = _local_vehicle(local_state, "front_veh")
    rear = _local_vehicle(local_state, "rear_buyer")
    in_a.vehicles.clear()
    in_a.vehicles.append(front)
    in_a.vehicles.append(rear)
    rear.leader = front
    front.follower = rear
    merge = local_state.target_node
    merge.incoming_vehicles.clear()
    merge.incoming_vehicles.append(front)
    _block_clearance_from_other_inlink(local_state)
    state = _init_state(local_state, collector, horizon=horizon)
    return world, local_state, collector, state, visits


def _buyer_and_seller_same_inlink_case(*, horizon: int):
    world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.BUYER,
            },
            {
                "name": "seller_veh",
                "origin": "orig_a",
                "dest": "dest_b",
                "inlink": "in_a",
                "route": "side",
                "role": OrderControlTvtMpLocalBindingTradeRole.SELLER,
            },
        ]
    )
    in_a = local_state.local_world.get_link("in_a")
    buyer = _local_vehicle(local_state, "buyer_veh")
    seller = _local_vehicle(local_state, "seller_veh")
    in_a.vehicles.clear()
    in_a.vehicles.append(buyer)
    in_a.vehicles.append(seller)
    seller.leader = buyer
    buyer.follower = seller
    state = _init_state(local_state, collector, horizon=horizon)
    return world, local_state, collector, state, visits


def _field_names(cls) -> tuple[str, ...]:
    names = []
    for field in dataclasses.fields(cls):
        names.append(field.name)
    return tuple(names)


def _assert_frozen(instance) -> None:
    field_name = dataclasses.fields(instance)[0].name
    try:
        setattr(instance, field_name, None)
        raise AssertionError(f"expected frozen type {type(instance).__name__}")
    except dataclasses.FrozenInstanceError:
        pass


def _assert_no_live_objects(value, *, path: str) -> None:
    if value is None:
        return
    if isinstance(value, (str, bytes, int, float, bool)):
        return
    if isinstance(value, Enum):
        return
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            _assert_no_live_objects(item, path=f"{path}[{index}]")
        return
    type_name = type(value).__name__
    if type_name in {"World", "Node", "Link", "Vehicle"}:
        raise AssertionError(f"{path} holds live {type_name}")
    if dataclasses.is_dataclass(value):
        for field in dataclasses.fields(value):
            _assert_no_live_objects(
                getattr(value, field.name),
                path=f"{path}.{field.name}",
            )
        return


def test_public_enums_members_and_values():
    assert (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED.value
        == "resolved"
    )
    assert (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED.value
        == "horizon_exhausted_unresolved"
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON.value
        == "required_buyer_or_seller_did_not_pass_within_horizon"
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_REMAINED_BLOCKED_WITHIN_HORIZON.value
        == "downstream_boundary_remained_blocked_within_horizon"
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_HAD_WAITING_VEHICLES_BUT_NO_TRANSFER.value
        == "downstream_boundary_had_waiting_vehicles_but_no_transfer"
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON.value
        == "clearance_or_capacity_blocked_through_horizon"
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.NO_ACCEPTABLE_OUTLINK_FOR_ROUTE_UNDETERMINED_VEHICLE_WITHIN_HORIZON.value
        == "no_acceptable_outlink_for_route_undetermined_vehicle_within_horizon"
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION.value
        == "downstream_boundary_prevented_required_passage_information"
    )
    assert OrderControlTvtMpCandidateFinalLinkRole.TARGET_INLINK.value == "target_inlink"
    assert (
        OrderControlTvtMpCandidateFinalLinkRole.TARGET_OUTLINK.value == "target_outlink"
    )


def test_public_frozen_types_field_order_and_forbidden_fields():
    assert _field_names(OrderControlTvtMpCandidatePassageRecord) == (
        "visit_key",
        "vehicle_name",
        "trade_role",
        "binding_partition",
        "binding_rank",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "route_next_link_name",
        "route_origin",
        "inlink_name",
    )
    assert _field_names(OrderControlTvtMpCandidateVirtualTimestepResult) == (
        "node_name",
        "virtual_timestep",
        "offset",
        "binding_transfer_result",
        "unbound_fcfs_result",
        "newly_recorded_required_passage_visit_keys",
        "local_vehicle_advance_result",
        "outlink_boundary_result",
        "required_passages_complete_after_node_passage",
        "calculation_finished_after_timestep_end",
        "resolved_after_timestep_end",
    )
    assert _field_names(OrderControlTvtMpCandidateFinalVehicleRecord) == (
        "vehicle_name",
        "current_link_name",
        "position_x",
        "state",
        "current_visit_key",
        "current_visit_node_name",
    )
    assert _field_names(OrderControlTvtMpCandidateFinalLinkRecord) == (
        "link_name",
        "start_node_name",
        "end_node_name",
        "link_role",
        "vehicle_names_in_physical_order",
        "capacity_out_remain",
        "capacity_in_remain",
    )
    assert _field_names(OrderControlTvtMpCandidateFinalNodeRecord) == (
        "node_name",
        "incoming_vehicle_names",
        "flow_capacity_remain",
        "last_order_control_inlink_name",
        "last_order_control_entry_timestep",
        "order_control_clearance_timesteps",
    )
    assert _field_names(OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord) == (
        "outlink_name",
        "terminal_node_name",
        "boundary_mode",
        "observed_average_outflow_rate",
        "flow_allowance_after",
        "waiting_vehicle_names_after",
        "capacity_out_remain_after",
        "terminal_node_flow_capacity_remain_after",
        "cumulative_observed_outflow_exit_vehicle_names",
        "cumulative_constrained_sink_end_trip_vehicle_names",
    )
    assert _field_names(OrderControlTvtMpCandidateLocalVirtualCalculationResult) == (
        "node_name",
        "concrete_buyer_candidate_set",
        "binding_rank_sequence",
        "baseline_timestep_T",
        "configured_horizon_steps",
        "final_virtual_timestep",
        "final_offset",
        "simulated_timestep_count",
        "stop_reason",
        "resolved",
        "required_passage_records",
        "unresolved_reasons",
        "timestep_results",
        "final_vehicle_records",
        "final_inlink_records",
        "final_outlink_records",
        "final_node_record",
        "final_boundary_records",
    )
    for cls in (
        OrderControlTvtMpCandidatePassageRecord,
        OrderControlTvtMpCandidateVirtualTimestepResult,
        OrderControlTvtMpCandidateFinalVehicleRecord,
        OrderControlTvtMpCandidateFinalLinkRecord,
        OrderControlTvtMpCandidateFinalNodeRecord,
        OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord,
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    ):
        for field_name in _field_names(cls):
            assert field_name not in _FORBIDDEN_RESULT_FIELD_NAMES


def test_initialization_normal_horizon_1_and_2():
    _world, local_state, _collector, state, visits = _buyer_ready_case(horizon=1)
    assert isinstance(state, OrderControlTvtMpCandidateLocalVirtualCalculationState)
    assert state.configured_horizon_steps == 1
    assert state.required_buyer_visit_keys == (visits[0].visit_key,)
    assert state.required_seller_visit_keys == ()
    assert state.virtual_time_state.current_virtual_timestep == BASELINE_T
    assert state.virtual_time_state.current_offset == 0
    assert state.virtual_time_state.simulated_timestep_count == 0
    assert state.finished is False
    assert state.final_result is None
    assert isinstance(state.required_passage_records, tuple)
    assert state.required_passage_records[0].candidate_passage_timestep is None
    _world2, _local2, _collector2, state2, _visits2 = _buyer_ready_case(horizon=2)
    assert state2.configured_horizon_steps == 2


def test_initialization_rejects_horizon_0_negative_bool_and_non_int():
    world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            }
        ]
    )
    boundary = _constrained_sink_boundary()
    for bad_horizon in (0, -1, True, False, 1.5, "1"):
        try:
            initialize_tvt_mp_candidate_local_virtual_calculation_state(
                local_state,
                collector,
                boundary,
                bad_horizon,
            )
            raise AssertionError(f"expected ValueError for horizon {bad_horizon!r}")
        except ValueError:
            pass
    assert world.T == BASELINE_T


def test_initialization_rejects_empty_buyers_and_allows_empty_sellers():
    world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
            }
        ],
        buyers_sorted=(),
    )
    try:
        _init_state(local_state, collector, horizon=1)
        raise AssertionError("expected ValueError for empty buyers")
    except ValueError as error:
        assert "required buyers are empty" in str(error)
    _world, local_state2, collector2, state, visits2 = _buyer_ready_case(horizon=1)
    assert state.required_seller_visit_keys == ()
    assert visits2[0].trade_role is OrderControlTvtMpLocalBindingTradeRole.BUYER
    assert world.T == BASELINE_T


def test_initialization_rejects_duplicate_required_and_buyer_seller_overlap():
    world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            }
        ]
    )
    buyer_key = visits[0].visit_key
    local_state.binding_rank_sequence.concrete_buyer_candidate_set  # kept for readability
    sequence = _build_sequence(visits, (buyer_key, buyer_key))
    duplicated = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(duplicated)
    try:
        _init_state(duplicated, collector, horizon=1)
        raise AssertionError("expected RuntimeError for duplicated buyers")
    except RuntimeError as error:
        assert "duplicated" in str(error)
    _world, local_state2, collector2, visits2 = _prepare_world_with_vehicles(
        [
            {
                "name": "seller_as_buyer",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.SELLER,
            }
        ]
    )
    seller_key = visits2[0].visit_key
    overlap_sequence = _build_sequence(visits2, (seller_key,))
    overlap_state = build_tvt_mp_candidate_local_state(_world, overlap_sequence)
    _open_capacities(overlap_state)
    try:
        _init_state(overlap_state, collector2, horizon=1)
        raise AssertionError("expected RuntimeError for buyer/seller overlap")
    except RuntimeError:
        pass


def test_initialization_rejects_missing_snapshot_and_boundary_none():
    world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "register": False,
            }
        ]
    )
    try:
        _init_state(local_state, collector, horizon=1)
        raise AssertionError("expected RuntimeError for missing snapshot")
    except RuntimeError as error:
        assert "collector snapshot" in str(error)
    world2, local_state2, collector2, _visits2 = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            }
        ]
    )
    real_x = world2.VEHICLES["buyer_veh"].x
    try:
        initialize_tvt_mp_candidate_local_virtual_calculation_state(
            local_state2,
            collector2,
            None,
            1,
        )
        raise AssertionError("expected RuntimeError for missing boundary")
    except RuntimeError as error:
        assert "downstream boundary result is missing" in str(error)
    assert world2.T == BASELINE_T
    assert world2.VEHICLES["buyer_veh"].x == real_x


def test_initialization_rejects_node_and_timestep_mismatch_without_side_effects():
    world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            }
        ]
    )
    real_x = world.VEHICLES["buyer_veh"].x
    snapshot_before = collector.get_baseline_visit_snapshot("buyer_veh", 1)
    other_boundary = OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="other",
        outlink_results=(
            _outlink_boundary("out", "dest", 0, 0),
            _outlink_boundary("side", "dest_b", 0, 0),
        ),
    )
    try:
        initialize_tvt_mp_candidate_local_virtual_calculation_state(
            local_state,
            collector,
            other_boundary,
            1,
        )
        raise AssertionError("expected RuntimeError for node mismatch")
    except RuntimeError:
        pass
    local_state.local_world.T = BASELINE_T + 1
    try:
        _init_state(local_state, collector, horizon=1)
        raise AssertionError("expected RuntimeError for timestep mismatch")
    except RuntimeError:
        pass
    assert world.T == BASELINE_T
    assert world.VEHICLES["buyer_veh"].x == real_x
    assert collector.get_baseline_visit_snapshot("buyer_veh", 1) == snapshot_before


def test_horizon_1_processes_only_t_and_rejects_horizon_0_normal_path():
    world, local_state, collector, state, visits = _buyer_ready_case(horizon=1)
    _block_clearance_from_other_inlink(local_state)
    one_step_calls = []
    binding_times = []
    unbound_times = []
    advance_times = []
    boundary_times = []
    original_one_step = orch_mod.advance_tvt_mp_candidate_virtual_time_one_step
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    original_unbound = orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep
    original_advance = orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals
    original_boundary = orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep

    def counting_one_step(virtual_time_state):
        one_step_calls.append(virtual_time_state.current_virtual_timestep)
        return original_one_step(virtual_time_state)

    def counting_binding(binding_state):
        binding_times.append(
            binding_state.virtual_time_state.current_virtual_timestep
        )
        return original_binding(binding_state)

    def counting_unbound(unbound_state, binding_result):
        unbound_times.append(binding_result.virtual_timestep)
        return original_unbound(unbound_state, binding_result)

    def counting_advance(advance_state, binding_result):
        advance_times.append(binding_result.virtual_timestep)
        return original_advance(advance_state, binding_result)

    def counting_boundary(boundary_state, advance_result):
        boundary_times.append(advance_result.virtual_timestep)
        return original_boundary(boundary_state, advance_result)

    orch_mod.advance_tvt_mp_candidate_virtual_time_one_step = counting_one_step
    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = counting_binding
    orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = counting_unbound
    orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = counting_advance
    orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep = counting_boundary
    try:
        result = run_tvt_mp_candidate_local_virtual_calculation(state)
    finally:
        orch_mod.advance_tvt_mp_candidate_virtual_time_one_step = original_one_step
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = original_binding
        orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = original_unbound
        orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = original_advance
        orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep = original_boundary
    assert result.final_virtual_timestep == BASELINE_T
    assert result.final_offset == 0
    assert result.simulated_timestep_count == 0
    assert len(result.timestep_results) == 1
    assert result.timestep_results[0].virtual_timestep == BASELINE_T
    assert one_step_calls == []
    assert binding_times == [BASELINE_T]
    assert unbound_times == [BASELINE_T]
    assert advance_times == [BASELINE_T]
    assert boundary_times == [BASELINE_T]
    assert BASELINE_T + 1 not in binding_times
    assert result.required_passage_records[0].candidate_passage_timestep is None
    assert world.T == BASELINE_T


def test_horizon_2_and_3_process_t_through_t_plus_h_minus_1():
    counts = {}
    for horizon in (2, 3):
        _world, local_state, _collector, state, _visits = _buyer_ready_case(
            horizon=horizon
        )
        _block_clearance_from_other_inlink(local_state)
        one_step_calls = []
        processed = []
        original_one_step = orch_mod.advance_tvt_mp_candidate_virtual_time_one_step
        original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep

        def counting_one_step(virtual_time_state, _calls=one_step_calls):
            _calls.append(virtual_time_state.current_virtual_timestep)
            return original_one_step(virtual_time_state)

        def counting_binding(binding_state, _processed=processed):
            _processed.append(
                binding_state.virtual_time_state.current_virtual_timestep
            )
            return original_binding(binding_state)

        orch_mod.advance_tvt_mp_candidate_virtual_time_one_step = counting_one_step
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            counting_binding
        )
        try:
            result = run_tvt_mp_candidate_local_virtual_calculation(state)
        finally:
            orch_mod.advance_tvt_mp_candidate_virtual_time_one_step = original_one_step
            orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
                original_binding
            )
        expected_times = []
        for offset in range(horizon):
            expected_times.append(BASELINE_T + offset)
        assert processed == expected_times
        assert BASELINE_T + horizon not in processed
        assert result.final_virtual_timestep == BASELINE_T + horizon - 1
        assert result.final_offset == horizon - 1
        assert result.simulated_timestep_count == horizon - 1
        assert len(result.timestep_results) == horizon
        assert len(one_step_calls) == horizon - 1
        counts[horizon] = result
        for record in result.required_passage_records:
            if record.candidate_passage_timestep is not None:
                assert record.candidate_passage_timestep <= BASELINE_T + horizon - 1
    assert counts[2].timestep_results[0].virtual_timestep == BASELINE_T
    assert counts[2].timestep_results[1].virtual_timestep == BASELINE_T + 1
    assert counts[3].timestep_results[2].virtual_timestep == BASELINE_T + 2


def test_process_order_offset_0_has_no_one_step_and_unbound_always_runs():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=2)
    _block_clearance_from_other_inlink(local_state)
    order = []
    original_one_step = orch_mod.advance_tvt_mp_candidate_virtual_time_one_step
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    original_unbound = orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep
    original_advance = orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals
    original_boundary = orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep

    def one_step(virtual_time_state):
        order.append(("one_step", virtual_time_state.current_offset))
        return original_one_step(virtual_time_state)

    def binding(binding_state):
        order.append(("binding", binding_state.virtual_time_state.current_offset))
        return original_binding(binding_state)

    def unbound(unbound_state, binding_result):
        order.append(("unbound", binding_result.virtual_timestep))
        return original_unbound(unbound_state, binding_result)

    def advance(advance_state, binding_result):
        order.append(("advance", binding_result.virtual_timestep))
        return original_advance(advance_state, binding_result)

    def boundary(boundary_state, advance_result):
        order.append(("boundary", advance_result.virtual_timestep))
        return original_boundary(boundary_state, advance_result)

    orch_mod.advance_tvt_mp_candidate_virtual_time_one_step = one_step
    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = binding
    orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = unbound
    orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = advance
    orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep = boundary
    try:
        first = run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
        second = run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    finally:
        orch_mod.advance_tvt_mp_candidate_virtual_time_one_step = original_one_step
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = original_binding
        orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = original_unbound
        orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = original_advance
        orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep = original_boundary
    assert first.offset == 0
    assert second.offset == 1
    assert order[0] == ("binding", 0)
    assert order[1][0] == "unbound"
    assert order[2][0] == "advance"
    assert order[3][0] == "boundary"
    assert order[4] == ("one_step", 0)
    assert order[5] == ("binding", 1)
    assert first.unbound_fcfs_result is not None
    assert second.unbound_fcfs_result is not None
    assert state.completed_virtual_timesteps == (BASELINE_T, BASELINE_T + 1)


def test_unbound_empty_completion_on_clearance_and_node_capacity_and_no_candidates():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    _block_clearance_from_other_inlink(local_state)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    timestep = result.timestep_results[0]
    assert timestep.unbound_fcfs_result is not None
    assert (
        timestep.unbound_fcfs_result.stop_reason
        is OrderControlTvtMpUnboundFcfsStopReason.BINDING_CLEARANCE_STOPPED_NOT_STARTED
    )
    assert BASELINE_T in state.unbound_fcfs_transfer_state.completed_virtual_timesteps
    _world2, local_state2, collector2, _visits2 = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": False,
            }
        ]
    )
    local_state2.target_node.flow_capacity_remain = 0.0
    state2 = _init_state(local_state2, collector2, horizon=1)
    result2 = run_tvt_mp_candidate_local_virtual_calculation(state2)
    unbound2 = result2.timestep_results[0].unbound_fcfs_result
    assert unbound2 is not None
    assert unbound2.stop_reason in (
        OrderControlTvtMpUnboundFcfsStopReason.NODE_FLOW_CAPACITY_UNAVAILABLE_BEFORE_START,
        OrderControlTvtMpUnboundFcfsStopReason.CANDIDATES_COMPLETED,
        OrderControlTvtMpUnboundFcfsStopReason.BINDING_CLEARANCE_STOPPED_NOT_STARTED,
    )


def test_passage_records_buyer_seller_visit_keys_and_ignores_unbound_names():
    _world, local_state, collector, state, visits = _buyer_and_seller_same_inlink_case(
        horizon=1
    )
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is True
    buyer_record = result.required_passage_records[0]
    seller_record = result.required_passage_records[1]
    assert buyer_record.visit_key == visits[0].visit_key
    assert seller_record.visit_key == visits[1].visit_key
    assert buyer_record.trade_role is OrderControlTvtMpLocalBindingTradeRole.BUYER
    assert seller_record.trade_role is OrderControlTvtMpLocalBindingTradeRole.SELLER
    assert buyer_record.candidate_passage_timestep == BASELINE_T
    assert seller_record.candidate_passage_timestep == BASELINE_T
    assert buyer_record.vehicle_name != seller_record.vehicle_name
    _world2, local_state2, collector2, _visits2 = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": False,
                "baseline_passage": BASELINE_T,
            },
            {
                "name": "free_veh",
                "origin": "orig_c",
                "dest": "dest_b",
                "inlink": "in_c",
                "route": "side",
                "binding": False,
                "collector_route": "side",
            },
        ]
    )
    state2 = _init_state(local_state2, collector2, horizon=1)
    result2 = run_tvt_mp_candidate_local_virtual_calculation(state2)
    buyer2 = result2.required_passage_records[0]
    assert buyer2.baseline_passage_timestep == BASELINE_T
    assert buyer2.candidate_passage_timestep is None
    unbound_names = []
    for record in result2.timestep_results[0].unbound_fcfs_result.transferred_vehicle_records:
        unbound_names.append(record.vehicle_name)
    if "free_veh" in unbound_names:
        assert buyer2.vehicle_name not in unbound_names


def test_duplicate_passage_and_required_unbound_vehicle_are_runtime_errors():
    _world, local_state, collector, state, visits = _buyer_ready_case(horizon=1)
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep

    def duplicate_binding(binding_state):
        result = original_binding(binding_state)
        if result.transferred_binding_visit_keys:
            duplicated_keys = (
                result.transferred_binding_visit_keys
                + result.transferred_binding_visit_keys
            )
            return dataclasses.replace(
                result,
                transferred_binding_visit_keys=duplicated_keys,
            )
        return result

    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        duplicate_binding
    )
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
            raise AssertionError("expected RuntimeError for duplicate passage")
        except RuntimeError as error:
            assert "twice" in str(error) or "already has candidate" in str(error)
    finally:
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            original_binding
        )
    assert state.completed_virtual_timesteps == ()
    assert state.finished is False

    _world2, local_state2, collector2, state2, visits2 = _buyer_ready_case(
        horizon=1,
        incoming=False,
    )
    original_unbound = orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep

    def fake_unbound(unbound_state, binding_result):
        real = original_unbound(unbound_state, binding_result)
        fake_record = OrderControlTvtMpUnboundVehicleTransferRecord(
            vehicle_name="buyer_veh",
            inlink_name="in_a",
            outlink_name="out",
            route_classification=(
                OrderControlTvtMpUnboundRouteClassification.DETERMINISTIC_VIRTUAL_ROUTE
            ),
            virtual_timestep=binding_result.virtual_timestep,
        )
        return dataclasses.replace(
            real,
            transferred_vehicle_records=(fake_record,),
        )

    orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = (
        fake_unbound
    )
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state2)
            raise AssertionError("expected RuntimeError for required unbound pass")
        except RuntimeError as error:
            assert "unbound" in str(error)
    finally:
        orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = (
            original_unbound
        )
    assert state2.completed_virtual_timesteps == ()


def test_resolved_at_offset_0_completes_seven_steps_and_does_not_continue():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=2)
    parked = _local_vehicle(local_state, "buyer_veh")
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is True
    assert result.stop_reason is (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
    )
    assert result.unresolved_reasons == ()
    assert result.final_offset == 0
    assert result.final_virtual_timestep == BASELINE_T
    assert result.simulated_timestep_count == 0
    assert len(result.timestep_results) == 1
    timestep = result.timestep_results[0]
    assert timestep.required_passages_complete_after_node_passage is True
    assert timestep.calculation_finished_after_timestep_end is True
    assert timestep.resolved_after_timestep_end is True
    assert timestep.unbound_fcfs_result is not None
    assert timestep.local_vehicle_advance_result is not None
    assert timestep.outlink_boundary_result is not None
    assert state.virtual_time_state.current_virtual_timestep == BASELINE_T
    assert parked is _local_vehicle(local_state, "buyer_veh")
    try:
        run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
        raise AssertionError("expected RuntimeError after resolved")
    except RuntimeError:
        pass


def test_resolved_despite_unrelated_unbound_and_boundary_waiting():
    world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            },
            {
                "name": "wait_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "binding": False,
                "incoming": False,
                "register": True,
            },
        ]
    )
    wait_vehicle = _local_vehicle(local_state, "wait_veh")
    outlink = local_state.local_world.get_link("out")
    in_a = local_state.local_world.get_link("in_a")
    if wait_vehicle in list(in_a.vehicles):
        in_a.vehicles.remove(wait_vehicle)
    wait_vehicle.link = outlink
    wait_vehicle.x = outlink.length
    outlink.vehicles.append(wait_vehicle)
    state = _init_state(
        local_state,
        collector,
        horizon=2,
        boundary=_wait_without_outflow_boundary(),
    )
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is True
    waiting_names = result.final_boundary_records[0].waiting_vehicle_names_after
    assert "wait_veh" in waiting_names
    assert result.final_boundary_records[0].boundary_mode is (
        OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
    )
    assert world.T == BASELINE_T


def test_unresolved_at_last_offset_assigns_required_reason_in_canon_order():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=2)
    _block_clearance_from_other_inlink(local_state)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is False
    assert result.stop_reason is (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON
        in result.unresolved_reasons
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION
        not in result.unresolved_reasons
    )
    last = result.timestep_results[-1]
    assert last.offset == 1
    assert last.virtual_timestep == BASELINE_T + 1
    assert last.calculation_finished_after_timestep_end is True
    assert last.resolved_after_timestep_end is False
    reason_order = list(OrderControlTvtMpCandidateUnresolvedReason)
    indexes = []
    for reason in result.unresolved_reasons:
        indexes.append(reason_order.index(reason))
    assert indexes == sorted(indexes)
    assert len(set(result.unresolved_reasons)) == len(result.unresolved_reasons)


def test_through_horizon_not_inferred_from_forward_visit_clearance_stop():
    _world, local_state, _collector, state, visits = (
        _forward_visit_clearance_stops_before_rear_required_buyer_case(horizon=2)
    )
    front_key = visits[0].visit_key
    rear_key = visits[1].visit_key
    assert rear_key in state.required_buyer_visit_keys
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is False
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON
        in result.unresolved_reasons
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON
        not in result.unresolved_reasons
    )
    for timestep_result in result.timestep_results:
        binding = timestep_result.binding_transfer_result
        assert binding.stop_reason is (
            OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
        )
        assert binding.stopped_binding_visit_key == front_key
        rear_skip = None
        for skip in binding.temporarily_skipped_visits:
            if skip.binding_visit_key == rear_key:
                rear_skip = skip
                break
        assert rear_skip is None
    rear_record = None
    for record in result.required_passage_records:
        if record.visit_key == rear_key:
            rear_record = record
            break
    assert rear_record is not None
    assert rear_record.candidate_passage_timestep is None


def test_through_horizon_positive_when_required_visit_has_two_direct_clearance_stops():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=2)
    _block_clearance_from_other_inlink(local_state)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    buyer_key = state.required_buyer_visit_keys[0]
    for timestep_result in result.timestep_results:
        binding = timestep_result.binding_transfer_result
        assert binding.stop_reason is (
            OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
        )
        assert binding.stopped_binding_visit_key == buyer_key
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON
        in result.unresolved_reasons
    )


def test_unresolved_fact_rules_through_horizon_single_step_and_not_arrived():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    _block_clearance_from_other_inlink(local_state)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON
        not in result.unresolved_reasons
    )
    _world2, local_state2, _collector2, state2, _visits2 = _buyer_ready_case(
        horizon=2
    )
    _block_clearance_from_other_inlink(local_state2)
    result2 = run_tvt_mp_candidate_local_virtual_calculation(state2)
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON
        in result2.unresolved_reasons
    )
    _world3, local_state3, collector3, _visits3 = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": False,
            }
        ]
    )
    _block_clearance_from_other_inlink(local_state3)
    in_a = local_state3.local_world.get_link("in_a")
    buyer = _local_vehicle(local_state3, "buyer_veh")
    buyer.x = 20.0
    buyer.x_old = 20.0
    buyer.x_next = 20.0
    state3 = _init_state(local_state3, collector3, horizon=2)
    result3 = run_tvt_mp_candidate_local_virtual_calculation(state3)
    first_skip = result3.timestep_results[0].binding_transfer_result.temporarily_skipped_visits
    if first_skip:
        assert (
            first_skip[0].skip_reason.name == "NOT_ARRIVED_AT_TARGET_NODE"
            or result3.required_passage_records[0].candidate_passage_timestep is None
        )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON
        in result3.unresolved_reasons
    )


def test_unresolved_boundary_wait_facts_and_acceptable_outlink_empty():
    world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": False,
            },
            {
                "name": "wait_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "binding": False,
                "incoming": False,
            },
        ]
    )
    wait_vehicle = _local_vehicle(local_state, "wait_veh")
    outlink = local_state.local_world.get_link("out")
    in_a = local_state.local_world.get_link("in_a")
    if wait_vehicle in list(in_a.vehicles):
        in_a.vehicles.remove(wait_vehicle)
    wait_vehicle.link = outlink
    wait_vehicle.x = outlink.length
    outlink.vehicles.append(wait_vehicle)
    state = _init_state(
        local_state,
        collector,
        horizon=1,
        boundary=_wait_without_outflow_boundary(),
    )
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_HAD_WAITING_VEHICLES_BUT_NO_TRANSFER
        in result.unresolved_reasons
    )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_REMAINED_BLOCKED_WITHIN_HORIZON
        in result.unresolved_reasons
    )
    world2, local_state2, collector2, _visits2 = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": False,
            },
            {
                "name": "virt",
                "origin": "orig_b",
                "dest": "dest_b",
                "inlink": "in_b",
                "route": "side",
                "binding": False,
                "collector_route": None,
                "arrived": False,
            },
        ]
    )
    for name in ("out", "side"):
        local_state2.local_world.get_link(name).capacity_in_remain = 0.0
    state2 = _init_state(local_state2, collector2, horizon=1)
    result2 = run_tvt_mp_candidate_local_virtual_calculation(state2)
    skip_reasons = []
    for skip in result2.timestep_results[0].unbound_fcfs_result.temporary_skips:
        skip_reasons.append(skip.skip_reason)
    if OrderControlTvtMpUnboundTemporarySkipReason.ACCEPTABLE_OUTLINKS_EMPTY in skip_reasons:
        assert (
            OrderControlTvtMpCandidateUnresolvedReason.NO_ACCEPTABLE_OUTLINK_FOR_ROUTE_UNDETERMINED_VEHICLE_WITHIN_HORIZON
            in result2.unresolved_reasons
        )
    assert (
        OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION
        not in result2.unresolved_reasons
    )
    assert world.T == BASELINE_T
    assert world2.T == BASELINE_T


def test_final_vehicle_link_node_boundary_records_and_no_live_objects():
    world, local_state, collector, state, _visits = _buyer_ready_case(horizon=1)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    _assert_frozen(result)
    _assert_no_live_objects(result, path="result")
    assert isinstance(result.final_vehicle_records, tuple)
    assert isinstance(result.final_inlink_records, tuple)
    assert isinstance(result.final_outlink_records, tuple)
    assert isinstance(result.final_boundary_records, tuple)
    vehicle_names = []
    for record in result.final_vehicle_records:
        vehicle_names.append(record.vehicle_name)
        assert not hasattr(record, "v")
        assert not hasattr(record, "lane")
        assert not hasattr(record, "leader")
        assert not hasattr(record, "follower")
        assert not hasattr(record, "move_remain")
    assert "buyer_veh" in vehicle_names
    inlink_names = []
    for record in result.final_inlink_records:
        inlink_names.append(record.link_name)
        assert record.link_role is OrderControlTvtMpCandidateFinalLinkRole.TARGET_INLINK
    assert inlink_names == ["in_a", "in_b", "in_c"]
    outlink_names = []
    for record in result.final_outlink_records:
        outlink_names.append(record.link_name)
        assert record.link_role is OrderControlTvtMpCandidateFinalLinkRole.TARGET_OUTLINK
    assert outlink_names == ["out", "side"]
    assert result.final_node_record.node_name == "merge"
    assert result.final_node_record.incoming_vehicle_names == tuple(
        vehicle.name for vehicle in local_state.target_node.incoming_vehicles
    )
    boundary_names = []
    for record in result.final_boundary_records:
        boundary_names.append(record.outlink_name)
        assert not hasattr(record, "downstream_boundary_node_result")
    assert boundary_names == ["out", "side"]
    assert world.T == BASELINE_T


def test_boundary_exit_vehicle_is_not_in_final_vehicle_records():
    world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "incoming": False,
            },
            {
                "name": "exit_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "binding": False,
                "incoming": False,
            },
        ]
    )
    exit_vehicle = _local_vehicle(local_state, "exit_veh")
    outlink = local_state.local_world.get_link("out")
    in_a = local_state.local_world.get_link("in_a")
    if exit_vehicle in list(in_a.vehicles):
        in_a.vehicles.remove(exit_vehicle)
    exit_vehicle.link = outlink
    exit_vehicle.x = outlink.length
    outlink.vehicles.append(exit_vehicle)
    observed_outflow = OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="merge",
        outlink_results=(
            _outlink_boundary("out", "dest", 4, 4),
            _outlink_boundary("side", "dest_b", 0, 0),
        ),
    )
    state = _init_state(
        local_state,
        collector,
        horizon=1,
        boundary=observed_outflow,
    )
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    remaining_names = []
    for record in result.final_vehicle_records:
        remaining_names.append(record.vehicle_name)
    cumulative_exit = result.final_boundary_records[0].cumulative_observed_outflow_exit_vehicle_names
    if "exit_veh" in cumulative_exit:
        assert "exit_veh" not in remaining_names
    assert world.T == BASELINE_T


def test_frozen_result_does_not_change_when_local_world_is_mutated():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    saved_x = result.final_vehicle_records[0].position_x
    saved_inlink_vehicles = result.final_inlink_records[0].vehicle_names_in_physical_order
    saved_incoming = result.final_node_record.incoming_vehicle_names
    saved_waiting = result.final_boundary_records[0].waiting_vehicle_names_after
    buyer = _local_vehicle(local_state, "buyer_veh")
    buyer.x = 999.0
    local_state.local_world.get_link("in_a").vehicles.clear()
    local_state.target_node.incoming_vehicles.clear()
    for link_state in state.outlink_boundary_state.outlink_states:
        link_state._cumulative_observed_outflow_exit_vehicle_names.append("mutated")
    assert result.final_vehicle_records[0].position_x == saved_x
    assert result.final_inlink_records[0].vehicle_names_in_physical_order == saved_inlink_vehicles
    assert result.final_node_record.incoming_vehicle_names == saved_incoming
    assert result.final_boundary_records[0].waiting_vehicle_names_after == saved_waiting


def test_double_execution_and_finished_guards():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    first = run_tvt_mp_candidate_local_virtual_calculation(state)
    fingerprint = (
        first.final_virtual_timestep,
        first.resolved,
        len(first.timestep_results),
        state.completed_virtual_timesteps,
    )
    try:
        run_tvt_mp_candidate_local_virtual_calculation(state)
        raise AssertionError("expected RuntimeError on second run-to-completion")
    except RuntimeError:
        pass
    try:
        run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
        raise AssertionError("expected RuntimeError on one-timestep after finish")
    except RuntimeError:
        pass
    assert (
        first.final_virtual_timestep,
        first.resolved,
        len(first.timestep_results),
        state.completed_virtual_timesteps,
    ) == fingerprint
    _world2, local_state2, _collector2, state2, _visits2 = _buyer_ready_case(horizon=2)
    _block_clearance_from_other_inlink(local_state2)
    first_step = run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state2)
    assert first_step.virtual_timestep == BASELINE_T
    second_step = run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state2)
    assert second_step.virtual_timestep == BASELINE_T + 1
    assert state2.completed_virtual_timesteps == (BASELINE_T, BASELINE_T + 1)
    assert len(state2.timestep_results) == 2


def test_exception_after_binding_does_not_publish_partial_or_rollback():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    original_unbound = orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep

    def failing_unbound(unbound_state, binding_result):
        raise RuntimeError("forced unbound failure")

    orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = (
        failing_unbound
    )
    buyer_before = _local_vehicle(local_state, "buyer_veh")
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
            raise AssertionError("expected forced unbound failure")
        except RuntimeError as error:
            assert "forced unbound failure" in str(error)
    finally:
        orch_mod.scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep = (
            original_unbound
        )
    assert state.completed_virtual_timesteps == ()
    assert state.finished is False
    assert state.final_result is None
    assert state.timestep_results == ()
    buyer_after = _local_vehicle(local_state, "buyer_veh")
    assert buyer_after.link.name == "out"
    assert buyer_before is buyer_after


def test_exception_after_advance_and_during_final_record_build():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    original_advance = orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals

    def failing_advance(advance_state, binding_result):
        raise RuntimeError("forced advance failure")

    orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = (
        failing_advance
    )
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
            raise AssertionError("expected forced advance failure")
        except RuntimeError as error:
            assert "forced advance failure" in str(error)
    finally:
        orch_mod.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = (
            original_advance
        )
    assert state.completed_virtual_timesteps == ()
    assert state.finished is False
    assert state.final_result is None
    assert BASELINE_T in state.unbound_fcfs_transfer_state.completed_virtual_timesteps

    _world_b, local_state_b, _collector_b, state_b, _visits_b = _buyer_ready_case(
        horizon=1
    )
    original_boundary = orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep

    def failing_boundary(boundary_state, advance_result):
        raise RuntimeError("forced boundary failure")

    orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep = (
        failing_boundary
    )
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state_b)
            raise AssertionError("expected forced boundary failure")
        except RuntimeError as error:
            assert "forced boundary failure" in str(error)
    finally:
        orch_mod.process_tvt_mp_candidate_outlink_boundaries_at_current_timestep = (
            original_boundary
        )
    assert state_b.completed_virtual_timesteps == ()
    assert BASELINE_T in state_b.local_vehicle_advance_state.completed_virtual_timesteps
    assert state_b.finished is False
    assert state_b.final_result is None

    _world2, local_state2, _collector2, state2, _visits2 = _buyer_ready_case(horizon=1)
    original_build = orch_mod._build_final_vehicle_records

    def failing_build(calculation_state):
        raise RuntimeError("forced final-record failure")

    orch_mod._build_final_vehicle_records = failing_build
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state2)
            raise AssertionError("expected forced final-record failure")
        except RuntimeError as error:
            assert "forced final-record failure" in str(error)
    finally:
        orch_mod._build_final_vehicle_records = original_build
    assert state2.completed_virtual_timesteps == ()
    assert state2.finished is False
    assert state2.final_result is None
    assert BASELINE_T in state2.outlink_boundary_state.completed_virtual_timesteps


def test_invariants_real_world_collector_sequence_rng_and_other_candidate():
    world, local_state, collector, state, visits = _buyer_ready_case(horizon=1)
    other_world, other_local, other_collector, other_state, _other_visits = (
        _buyer_ready_case(horizon=1)
    )
    real_x = world.VEHICLES["buyer_veh"].x
    real_t = world.T
    snapshot_before = collector.get_baseline_visit_snapshot("buyer_veh", 1)
    sequence_before = local_state.binding_rank_sequence
    buyers_before = sequence_before.concrete_buyer_candidate_set.buyers_sorted
    rng_before = copy.deepcopy(local_state.local_world.rng.bit_generator.state)
    other_x = other_world.VEHICLES["buyer_veh"].x
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is True
    assert world.T == real_t
    assert world.VEHICLES["buyer_veh"].x == real_x
    assert collector.get_baseline_visit_snapshot("buyer_veh", 1) == snapshot_before
    assert local_state.binding_rank_sequence is sequence_before
    assert sequence_before.concrete_buyer_candidate_set.buyers_sorted == buyers_before
    assert local_state.local_world.rng.bit_generator.state == rng_before
    assert other_world.T == BASELINE_T
    assert other_world.VEHICLES["buyer_veh"].x == other_x
    assert other_state.finished is False
    assert other_state.virtual_time_state.current_virtual_timestep == BASELINE_T
    assert result.binding_rank_sequence is sequence_before
    assert result.concrete_buyer_candidate_set is sequence_before.concrete_buyer_candidate_set


def test_source_has_no_forbidden_live_writes_or_terminal_fields():
    source_path = inspect.getsourcefile(orch_mod)
    with open(source_path, "r", encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
    assert "exec_simulation" not in called_names
    assert "transfer" not in called_names
    assert "update" not in called_names or "Vehicle.update" not in source
    assert "route_pref" not in source
    assert "route_next_link_choice" not in source
    assert "random.random" not in source
    class_fields = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.append(item.target.id)
            class_fields[node.name] = names
    result_fields = class_fields["OrderControlTvtMpCandidateLocalVirtualCalculationResult"]
    vehicle_fields = class_fields["OrderControlTvtMpCandidateFinalVehicleRecord"]
    for forbidden in _FORBIDDEN_RESULT_FIELD_NAMES:
        assert forbidden not in result_fields
        assert forbidden not in vehicle_fields
    assert "DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION" in source
    assert "_collect_unresolved_reasons" in source
    reason_fn = ast.parse(inspect.getsource(orch_mod._collect_unresolved_reasons))
    assigned = []
    for node in ast.walk(reason_fn):
        if isinstance(node, ast.Attribute):
            assigned.append(node.attr)
    assert "DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION" not in assigned


def test_same_name_different_vehicle_object_is_rejected():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=1)
    original_build = orch_mod._build_final_vehicle_records

    class _Alias:
        def __init__(self, original):
            self.original = original
            self.name = original.name
            self.link = original.link
            self.x = original.x
            self.state = original.state
            self.order_control_current_visit = original.order_control_current_visit

    def colliding_build(calculation_state):
        vehicles = original_build(calculation_state)
        if not vehicles:
            return vehicles
        first = _local_vehicle(calculation_state.candidate_local_state, "buyer_veh")
        alias = _Alias(first)
        calculation_state.candidate_local_state.outlinks[0].vehicles.append(alias)
        try:
            return original_build(calculation_state)
        finally:
            queued = list(calculation_state.candidate_local_state.outlinks[0].vehicles)
            if alias in queued:
                calculation_state.candidate_local_state.outlinks[0].vehicles.remove(alias)

    orch_mod._build_final_vehicle_records = colliding_build
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
            raise AssertionError("expected RuntimeError for same name, different object")
        except RuntimeError as error:
            assert "different Vehicle objects" in str(error)
    finally:
        orch_mod._build_final_vehicle_records = original_build
    assert state.finished is False
    assert state.final_result is None


def test_run_to_completion_from_partial_one_timestep_state():
    _world, local_state, _collector, state, _visits = _buyer_ready_case(horizon=2)
    _block_clearance_from_other_inlink(local_state)
    first = run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    assert first.offset == 0
    assert state.finished is False
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert len(result.timestep_results) == 2
    assert result.final_offset == 1
    assert result.resolved is False


def test_tests_registry_matches_defined_functions():
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
    assert len(TESTS) == len(defined_functions)
    assert len(set(TESTS)) == len(TESTS)


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
