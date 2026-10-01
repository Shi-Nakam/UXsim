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
    OrderControlTvtMpBindingVisitTemporarySkip,
    OrderControlTvtMpBindingVisitTemporarySkipReason,
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
    OrderControlTvtMpCandidatePassageObservationStatus,
    OrderControlTvtMpCandidatePassageRecord,
    OrderControlTvtMpCandidateClearanceScanStopContext,
    OrderControlTvtMpCandidateTrafficObservationRecord,
    OrderControlTvtMpCandidateUnresolvedReason,
    OrderControlTvtMpCandidateVirtualTimestepResult,
    initialize_tvt_mp_candidate_local_virtual_calculation_state,
    _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer,
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
        if "vot_true" in spec:
            vehicle.vot_true = spec["vot_true"]
        else:
            vehicle.vot_true = 1.0
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
            if "baseline_passage" in spec:
                baseline_passage_timestep = spec["baseline_passage"]
            elif spec.get("binding", True) and spec.get("arrived", True):
                baseline_passage_timestep = BASELINE_T
            else:
                baseline_passage_timestep = None
            _register_snapshot(
                collector,
                vehicle,
                route_name=spec.get("collector_route", spec["route"]),
                arrived=spec.get("arrived", True),
                baseline_passage_timestep=baseline_passage_timestep,
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
    assert OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED.value == "observed"
    assert (
        OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON.value
        == "unobserved_at_horizon"
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
    assert _field_names(OrderControlTvtMpCandidateClearanceScanStopContext) == (
        "virtual_timestep",
        "offset",
        "stopped_binding_visit_key",
    )
    assert _field_names(OrderControlTvtMpCandidateTrafficObservationRecord) == (
        "visit_key",
        "vehicle_name",
        "vehicle_id",
        "trade_role",
        "binding_partition",
        "binding_rank",
        "trade_scope_rank",
        "inlink_name",
        "route_next_link_name",
        "true_vot_per_second",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "passage_observation_status",
        "observed_offset",
        "observed_virtual_timestep",
        "predicted_time_difference_timesteps",
        "predicted_time_difference_seconds",
        "predicted_signed_time_value_change",
        "last_checked_offset",
        "last_checked_virtual_timestep",
        "last_temporary_skip_reason",
        "last_temporary_skip_offset",
        "latest_clearance_stop_context",
        "horizon_exhausted",
        "observation_complete",
    )
    for cls in (
        OrderControlTvtMpCandidatePassageRecord,
        OrderControlTvtMpCandidateVirtualTimestepResult,
        OrderControlTvtMpCandidateFinalVehicleRecord,
        OrderControlTvtMpCandidateFinalLinkRecord,
        OrderControlTvtMpCandidateFinalNodeRecord,
        OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord,
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
        OrderControlTvtMpCandidateClearanceScanStopContext,
        OrderControlTvtMpCandidateTrafficObservationRecord,
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


def test_traffic_observation_initialization_keeps_trade_scope_only():
    world, _unused_local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "before_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
                "vot_true": 9.0,
                "baseline_passage": 20,
            },
            {
                "name": "pre_veh",
                "origin": "orig_b",
                "dest": "dest_b",
                "inlink": "in_b",
                "route": "side",
                "role": OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
                "vot_true": 7.0,
                "baseline_passage": 19,
            },
            {
                "name": "buyer_veh",
                "origin": "orig_c",
                "dest": "dest",
                "inlink": "in_c",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.BUYER,
                "vot_true": 2,
                "baseline_passage": 12,
            },
            {
                "name": "seller_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.SELLER,
                "vot_true": 3.5,
                "baseline_passage": 13,
            },
            {
                "name": "np_veh",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
                "vot_true": 4,
                "baseline_passage": 14,
            },
            {
                "name": "after_veh",
                "origin": "orig_c",
                "dest": "dest_b",
                "inlink": "in_c",
                "route": "side",
                "role": OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
                "vot_true": 8.0,
                "baseline_passage": 21,
            },
        ]
    )
    before_visit, pre_visit, buyer_visit, seller_visit, np_visit, after_visit = visits
    before_fixed = dataclasses.replace(
        before_visit,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.CONFIRMED_BEFORE_THIS_BASELINE
        ),
        binding_rank=1,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
    )
    pre_fixed = dataclasses.replace(
        pre_visit,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.PRECONFIRMED_BY_THIS_BASELINE
        ),
        binding_rank=2,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
    )
    buyer_fixed = dataclasses.replace(buyer_visit, binding_rank=3)
    seller_fixed = dataclasses.replace(seller_visit, binding_rank=4)
    np_fixed = dataclasses.replace(np_visit, binding_rank=5)
    outside_fixed = dataclasses.replace(
        after_visit,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED
        ),
        binding_rank=6,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
    )
    trade_scope = (buyer_fixed, seller_fixed, np_fixed)
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=BASELINE_T,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(buyer_fixed.visit_key,),
        ),
        confirmed_before_this_baseline_visits=(before_fixed,),
        preconfirmed_by_this_baseline_visits=(pre_fixed,),
        trade_scope_of_this_candidate_visits=trade_scope,
        outside_trade_scope_inside_k_fixed_visits=(outside_fixed,),
        visits_in_binding_order=(
            before_fixed,
            pre_fixed,
            buyer_fixed,
            seller_fixed,
            np_fixed,
            outside_fixed,
        ),
        k_last_buyer=4,
        k_decision_window=6,
        k_fixed=6,
    )
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    state = _init_state(local_state, collector, horizon=2)
    records = state.traffic_observation_records_in_public_order
    assert isinstance(records, tuple)
    assert len(records) == 3
    assert [record.vehicle_name for record in records] == [
        "buyer_veh",
        "seller_veh",
        "np_veh",
    ]
    assert [record.trade_scope_rank for record in records] == [1, 2, 3]
    assert [record.binding_rank for record in records] == [3, 4, 5]
    assert [record.trade_role for record in records] == [
        OrderControlTvtMpLocalBindingTradeRole.BUYER,
        OrderControlTvtMpLocalBindingTradeRole.SELLER,
        OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
    ]
    for record in records:
        assert (
            record.binding_partition
            is OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        )
    stored_names = [record.vehicle_name for record in records]
    assert "before_veh" not in stored_names
    assert "pre_veh" not in stored_names
    assert "after_veh" not in stored_names
    buyer_record = records[0]
    assert buyer_record.true_vot_per_second == 2.0
    assert type(buyer_record.true_vot_per_second) is float
    assert buyer_record.baseline_passage_timestep == 12
    assert records[1].baseline_passage_timestep == 13
    assert records[1].true_vot_per_second == 3.5
    assert records[2].baseline_passage_timestep == 14
    assert records[2].true_vot_per_second == 4.0
    for record in records:
        assert record.candidate_passage_timestep is None
        assert record.passage_observation_status is None
        assert record.observed_offset is None
        assert record.observed_virtual_timestep is None
        assert record.predicted_time_difference_timesteps is None
        assert record.predicted_time_difference_seconds is None
        assert record.predicted_signed_time_value_change is None
        assert record.last_checked_offset is None
        assert record.last_checked_virtual_timestep is None
        assert record.last_temporary_skip_reason is None
        assert record.last_temporary_skip_offset is None
        assert record.latest_clearance_stop_context is None
        assert record.horizon_exhausted is None
        assert record.observation_complete is None
        _assert_frozen(record)
    assert state.economic_required_passages_complete_offset is None
    assert state.economic_required_passages_complete_virtual_timestep is None
    assert state.all_trade_scope_passages_complete_offset is None
    assert state.all_trade_scope_passages_complete_virtual_timestep is None
    pairs = state.traffic_observation_record_by_visit_key
    assert isinstance(pairs, tuple)
    assert len(pairs) == 3
    for record, pair in zip(records, pairs):
        assert pair[0] == record.visit_key
        assert pair[1] is record
        assert state.traffic_observation_record_for_visit_key(record.visit_key) is record
    _assert_frozen(
        OrderControlTvtMpCandidateClearanceScanStopContext(
            virtual_timestep=15,
            offset=5,
            stopped_binding_visit_key=buyer_record.visit_key,
        )
    )
    required_names = [
        record.vehicle_name for record in state.required_passage_records
    ]
    assert "np_veh" not in required_names


def test_traffic_observation_accepts_true_vot_zero_and_rejects_invalid_values():
    _world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "vot_true": 0,
            }
        ]
    )
    state = _init_state(local_state, collector, horizon=1)
    record = state.traffic_observation_records_in_public_order[0]
    assert record.true_vot_per_second == 0.0
    invalid_values = [None, True, False, "high", float("nan"), float("inf"), -1]
    for invalid_value in invalid_values:
        prepared = _prepare_world_with_vehicles(
            [
                {
                    "name": "buyer_veh",
                    "origin": "orig_a",
                    "dest": "dest",
                    "inlink": "in_a",
                    "route": "out",
                    "vot_true": invalid_value,
                }
            ]
        )
        try:
            _init_state(prepared[1], prepared[2], horizon=1)
            raise AssertionError(f"expected RuntimeError for vot_true={invalid_value!r}")
        except RuntimeError as error:
            assert "vot_true" in str(error)


def test_traffic_observation_rejects_missing_baseline_bad_role_and_duplicate_visit():
    _world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "baseline_passage": None,
            }
        ]
    )
    try:
        _init_state(local_state, collector, horizon=1)
        raise AssertionError("expected RuntimeError for missing baseline passage")
    except RuntimeError as error:
        assert "baseline" in str(error)

    prepared = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            },
            {
                "name": "np_veh",
                "origin": "orig_b",
                "dest": "dest_b",
                "inlink": "in_b",
                "route": "side",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
            },
        ]
    )
    world = prepared[0]
    collector = prepared[2]
    buyer_visit, np_visit = prepared[3]
    outside_visit = dataclasses.replace(
        np_visit,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED
        ),
        trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
    )
    sequence = _build_sequence(
        (buyer_visit, outside_visit),
        (buyer_visit.visit_key,),
    )
    rebuilt = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(rebuilt)
    try:
        _init_state(rebuilt, collector, horizon=1)
        raise AssertionError("expected RuntimeError for outside trade scope")
    except RuntimeError as error:
        assert "trade role" in str(error) or "binding partition" in str(error)

    duplicate_scope = _build_sequence(
        (buyer_visit,),
        (buyer_visit.visit_key,),
    )
    duplicate_scope = dataclasses.replace(
        duplicate_scope,
        trade_scope_of_this_candidate_visits=(buyer_visit, buyer_visit),
    )
    rebuilt_duplicate = build_tvt_mp_candidate_local_state(world, duplicate_scope)
    _open_capacities(rebuilt_duplicate)
    try:
        _init_state(rebuilt_duplicate, collector, horizon=1)
        raise AssertionError("expected RuntimeError for duplicated VisitKey")
    except RuntimeError as error:
        assert "duplicated" in str(error)


def _binding_transfer_scan_template(state):
    return orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        state.binding_transfer_state
    )


def _binding_transfer_with_transferred_keys(state, visit_keys):
    template = _binding_transfer_scan_template(state)
    return dataclasses.replace(
        template,
        transferred_binding_visit_keys=tuple(visit_keys),
    )


def _traffic_observation_three_role_state(horizon=2):
    world, _local, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.BUYER,
                "vot_true": 2.0,
                "baseline_passage": 12,
            },
            {
                "name": "seller_veh",
                "origin": "orig_a",
                "dest": "dest_b",
                "inlink": "in_a",
                "route": "side",
                "role": OrderControlTvtMpLocalBindingTradeRole.SELLER,
                "vot_true": 3.0,
                "baseline_passage": 13,
            },
            {
                "name": "np_veh",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
                "vot_true": 4.0,
                "baseline_passage": 14,
            },
        ]
    )
    buyer_visit, seller_visit, np_visit = visits
    sequence = _build_sequence(visits, (buyer_visit.visit_key,))
    local_state = build_tvt_mp_candidate_local_state(world, sequence)
    _open_capacities(local_state)
    state = _init_state(local_state, collector, horizon=horizon)
    return world, local_state, state, buyer_visit, seller_visit, np_visit


def test_propose_traffic_observation_binding_transfer_buyer_update():
    _world, _local, state, buyer_visit, _seller, _np = _traffic_observation_three_role_state()
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (buyer_visit.visit_key,),
    )
    offset = 1
    virtual_timestep = BASELINE_T + 1
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        offset,
        virtual_timestep,
    )
    assert len(proposed) == 1
    updated = proposed[0]
    assert updated.trade_role is OrderControlTvtMpLocalBindingTradeRole.BUYER
    assert updated.candidate_passage_timestep == virtual_timestep
    assert updated.observed_offset == offset
    assert updated.observed_virtual_timestep == virtual_timestep
    assert updated.last_checked_offset == offset
    assert updated.last_checked_virtual_timestep == virtual_timestep
    assert updated.predicted_time_difference_timesteps == 12 - virtual_timestep
    assert updated.predicted_time_difference_seconds == 12 - virtual_timestep
    assert updated.predicted_signed_time_value_change == 2.0 * (12 - virtual_timestep)


def test_propose_traffic_observation_binding_transfer_seller_update():
    _world, _local, state, _buyer, seller_visit, _np = _traffic_observation_three_role_state()
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (seller_visit.visit_key,),
    )
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    assert len(proposed) == 1
    assert proposed[0].trade_role is OrderControlTvtMpLocalBindingTradeRole.SELLER
    assert proposed[0].vehicle_name == "seller_veh"
    assert proposed[0].baseline_passage_timestep == 13
    assert proposed[0].candidate_passage_timestep == BASELINE_T


def test_propose_traffic_observation_binding_transfer_nonparticipating_update():
    _world, _local, state, _buyer, _seller, np_visit = _traffic_observation_three_role_state()
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (np_visit.visit_key,),
    )
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    assert len(proposed) == 1
    assert (
        proposed[0].trade_role
        is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING
    )
    assert proposed[0].vehicle_name == "np_veh"


def test_propose_traffic_observation_binding_transfer_ignores_outside_trade_scope_key():
    _world, _local, state, buyer_visit, _seller, _np = _traffic_observation_three_role_state()
    outside_key = ("outside_veh", 99)
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (outside_key, buyer_visit.visit_key),
    )
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    assert len(proposed) == 1
    assert proposed[0].visit_key == buyer_visit.visit_key


def test_propose_traffic_observation_binding_transfer_positive_time_difference():
    _world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "vot_true": 2.0,
                "baseline_passage": 15,
            }
        ]
    )
    state = _init_state(local_state, collector, horizon=2)
    buyer_key = state.traffic_observation_records_in_public_order[0].visit_key
    binding_result = _binding_transfer_with_transferred_keys(state, (buyer_key,))
    virtual_timestep = BASELINE_T
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        virtual_timestep,
    )
    assert proposed[0].predicted_time_difference_timesteps == 5
    assert proposed[0].predicted_time_difference_seconds == 5
    assert proposed[0].predicted_signed_time_value_change == 10.0


def test_propose_traffic_observation_binding_transfer_negative_time_difference():
    _world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "vot_true": 3.0,
                "baseline_passage": 8,
            }
        ]
    )
    state = _init_state(local_state, collector, horizon=2)
    buyer_key = state.traffic_observation_records_in_public_order[0].visit_key
    binding_result = _binding_transfer_with_transferred_keys(state, (buyer_key,))
    virtual_timestep = BASELINE_T
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        virtual_timestep,
    )
    assert proposed[0].predicted_time_difference_timesteps == -2
    assert proposed[0].predicted_time_difference_seconds == -2
    assert proposed[0].predicted_signed_time_value_change == -6.0


def test_propose_traffic_observation_binding_transfer_zero_time_difference():
    _world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "vot_true": 4.0,
                "baseline_passage": BASELINE_T,
            }
        ]
    )
    state = _init_state(local_state, collector, horizon=1)
    buyer_key = state.traffic_observation_records_in_public_order[0].visit_key
    binding_result = _binding_transfer_with_transferred_keys(state, (buyer_key,))
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    assert proposed[0].predicted_time_difference_timesteps == 0
    assert proposed[0].predicted_time_difference_seconds == 0
    assert proposed[0].predicted_signed_time_value_change == 0


def test_propose_traffic_observation_binding_transfer_uses_frozen_true_vot():
    _world, local_state, collector, _visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "vot_true": 5.0,
                "baseline_passage": 12,
            }
        ]
    )
    state = _init_state(local_state, collector, horizon=2)
    buyer_key = state.traffic_observation_records_in_public_order[0].visit_key
    _local_vehicle(local_state, "buyer_veh").vot_true = 100.0
    binding_result = _binding_transfer_with_transferred_keys(state, (buyer_key,))
    proposed = _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        BASELINE_T + 1,
    )
    assert proposed[0].true_vot_per_second == 5.0
    assert proposed[0].predicted_signed_time_value_change == 5.0


def test_propose_traffic_observation_binding_transfer_does_not_mutate_state():
    _world, _local, state, buyer_visit, seller_visit, np_visit = (
        _traffic_observation_three_role_state()
    )
    records_before = state.traffic_observation_records_in_public_order
    pairs_before = state.traffic_observation_record_by_visit_key
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (buyer_visit.visit_key, seller_visit.visit_key, np_visit.visit_key),
    )
    _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    records_after = state.traffic_observation_records_in_public_order
    pairs_after = state.traffic_observation_record_by_visit_key
    assert records_after == records_before
    assert pairs_after == pairs_before
    for record in records_after:
        assert record.candidate_passage_timestep is None


def test_propose_traffic_observation_binding_transfer_rejects_duplicate_candidate_passage():
    _world, _local, state, buyer_visit, _seller, _np = _traffic_observation_three_role_state()
    existing = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    already_passed = dataclasses.replace(
        existing,
        candidate_passage_timestep=BASELINE_T,
    )
    state._traffic_observation_record_by_visit_key[buyer_visit.visit_key] = already_passed
    for index, record in enumerate(state._traffic_observation_records_in_public_order):
        if record.visit_key == buyer_visit.visit_key:
            state._traffic_observation_records_in_public_order[index] = already_passed
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (buyer_visit.visit_key,),
    )
    try:
        _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
            state,
            binding_result,
            0,
            BASELINE_T + 1,
        )
        raise AssertionError("expected RuntimeError for duplicate candidate passage")
    except RuntimeError as error:
        assert "already has candidate passage" in str(error)


def test_propose_traffic_observation_binding_transfer_rejects_duplicate_transferred_keys():
    _world, _local, state, buyer_visit, _seller, _np = _traffic_observation_three_role_state()
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (buyer_visit.visit_key, buyer_visit.visit_key),
    )
    try:
        _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
            state,
            binding_result,
            0,
            BASELINE_T,
        )
        raise AssertionError("expected RuntimeError for duplicated transferred keys")
    except RuntimeError as error:
        assert "twice" in str(error)


def test_one_timestep_binding_updates_buyer_required_and_traffic_timesteps_match():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    required = state._passage_record_by_visit_key[buyer_visit.visit_key]
    traffic = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    assert type(required.candidate_passage_timestep) is int
    assert required.candidate_passage_timestep == traffic.candidate_passage_timestep
    assert required.candidate_passage_timestep == BASELINE_T


def test_one_timestep_binding_updates_seller_required_and_traffic_timesteps_match():
    _world, _local, _collector, state, visits = _buyer_and_seller_same_inlink_case(
        horizon=1
    )
    seller_visit = visits[1]
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    required = state._passage_record_by_visit_key[seller_visit.visit_key]
    traffic = state.traffic_observation_record_for_visit_key(seller_visit.visit_key)
    assert type(required.candidate_passage_timestep) is int
    assert required.candidate_passage_timestep == traffic.candidate_passage_timestep


def test_one_timestep_binding_updates_nonparticipating_traffic_only():
    _world, local_state, collector, visits = _prepare_world_with_vehicles(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.BUYER,
                "incoming": False,
            },
            {
                "name": "np_veh",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
            },
        ]
    )
    np_visit = visits[1]
    state = _init_state(local_state, collector, horizon=2)
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep

    def only_np(binding_state):
        result = original_binding(binding_state)
        return dataclasses.replace(
            result,
            transferred_binding_visit_keys=(np_visit.visit_key,),
        )

    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = only_np
    try:
        run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    finally:
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            original_binding
        )
    assert np_visit.visit_key not in state._passage_record_by_visit_key
    traffic = state.traffic_observation_record_for_visit_key(np_visit.visit_key)
    assert type(traffic.candidate_passage_timestep) is int
    buyer_key = visits[0].visit_key
    assert state._passage_record_by_visit_key[buyer_key].candidate_passage_timestep is None


def _buyer_seller_np_staggered_passage_state(*, horizon: int):
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
                "incoming": False,
            },
            {
                "name": "np_veh",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
                "role": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
                "incoming": False,
            },
        ]
    )
    buyer_visit, seller_visit, np_visit = visits
    in_a = local_state.local_world.get_link("in_a")
    buyer = _local_vehicle(local_state, "buyer_veh")
    seller = _local_vehicle(local_state, "seller_veh")
    in_a.vehicles.clear()
    in_a.vehicles.append(buyer)
    in_a.vehicles.append(seller)
    seller.leader = buyer
    buyer.follower = seller
    state = _init_state(local_state, collector, horizon=horizon)
    return world, local_state, state, buyer_visit, seller_visit, np_visit


def test_one_timestep_binding_updates_public_order_and_map_share_updated_records():
    _world, _local, state, buyer_visit, seller_visit, np_visit = (
        _buyer_seller_np_staggered_passage_state(horizon=2)
    )
    public_before = state.traffic_observation_records_in_public_order
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    updated = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    for index, record in enumerate(state.traffic_observation_records_in_public_order):
        assert public_before[index].visit_key == record.visit_key
        if record.visit_key == buyer_visit.visit_key:
            assert record is updated
            assert state._traffic_observation_record_by_visit_key[
                buyer_visit.visit_key
            ] is updated
    np_traffic = state.traffic_observation_record_for_visit_key(np_visit.visit_key)
    assert np_traffic.candidate_passage_timestep is None
    for record in state.traffic_observation_records_in_public_order:
        if record.visit_key == np_visit.visit_key:
            assert record is np_traffic


def test_one_timestep_binding_updates_do_not_apply_required_when_traffic_propose_fails():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    passage_before = copy.deepcopy(state.required_passage_records)
    traffic_before = copy.deepcopy(state.traffic_observation_records_in_public_order)
    original_propose = (
        orch_mod._propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer
    )

    def fail_traffic_propose(*args, **kwargs):
        raise RuntimeError("traffic observation propose failed for test")

    orch_mod._propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer = (
        fail_traffic_propose
    )
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep

    def only_buyer(binding_state):
        result = original_binding(binding_state)
        return dataclasses.replace(
            result,
            transferred_binding_visit_keys=(buyer_visit.visit_key,),
        )

    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = only_buyer
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
            raise AssertionError("expected RuntimeError from traffic propose failure")
        except RuntimeError as error:
            assert "traffic observation propose failed" in str(error)
    finally:
        orch_mod._propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer = (
            original_propose
        )
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            original_binding
        )
    assert state.required_passage_records == passage_before
    assert state.traffic_observation_records_in_public_order == traffic_before


def test_one_timestep_binding_updates_reject_buyer_seller_timestep_mismatch():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    original_apply_traffic = orch_mod._apply_traffic_observation_apply_plan_to_state

    def apply_wrong_timestep(calculation_state, apply_plan):
        broken_plan = []
        for visit_key, public_index, record in apply_plan:
            broken_plan.append(
                (
                    visit_key,
                    public_index,
                    OrderControlTvtMpCandidateTrafficObservationRecord(
                        visit_key=record.visit_key,
                        vehicle_name=record.vehicle_name,
                        vehicle_id=record.vehicle_id,
                        trade_role=record.trade_role,
                        binding_partition=record.binding_partition,
                        binding_rank=record.binding_rank,
                        trade_scope_rank=record.trade_scope_rank,
                        inlink_name=record.inlink_name,
                        route_next_link_name=record.route_next_link_name,
                        true_vot_per_second=record.true_vot_per_second,
                        baseline_passage_timestep=record.baseline_passage_timestep,
                        candidate_passage_timestep=record.candidate_passage_timestep + 1,
                        passage_observation_status=record.passage_observation_status,
                        observed_offset=record.observed_offset,
                        observed_virtual_timestep=record.observed_virtual_timestep + 1,
                        predicted_time_difference_timesteps=(
                            record.predicted_time_difference_timesteps
                        ),
                        predicted_time_difference_seconds=(
                            record.predicted_time_difference_seconds
                        ),
                        predicted_signed_time_value_change=(
                            record.predicted_signed_time_value_change
                        ),
                        last_checked_offset=record.last_checked_offset,
                        last_checked_virtual_timestep=(
                            record.last_checked_virtual_timestep + 1
                        ),
                        last_temporary_skip_reason=record.last_temporary_skip_reason,
                        last_temporary_skip_offset=record.last_temporary_skip_offset,
                        latest_clearance_stop_context=record.latest_clearance_stop_context,
                        horizon_exhausted=record.horizon_exhausted,
                        observation_complete=record.observation_complete,
                    ),
                )
            )
        original_apply_traffic(calculation_state, tuple(broken_plan))

    orch_mod._apply_traffic_observation_apply_plan_to_state = apply_wrong_timestep
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep

    def only_buyer(binding_state):
        result = original_binding(binding_state)
        return dataclasses.replace(
            result,
            transferred_binding_visit_keys=(buyer_visit.visit_key,),
        )

    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = only_buyer
    try:
        try:
            run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
            raise AssertionError("expected RuntimeError for timestep mismatch")
        except RuntimeError as error:
            assert "does not match traffic observation" in str(error)
    finally:
        orch_mod._apply_traffic_observation_apply_plan_to_state = (
            original_apply_traffic
        )
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            original_binding
        )


def _passage_and_traffic_snapshot(state):
    return (
        copy.deepcopy(state.required_passage_records),
        copy.deepcopy(state.traffic_observation_records_in_public_order),
    )


def _candidate_passage_timesteps_unchanged(state, buyer_visit, seller_visit):
    buyer_required = state._passage_record_by_visit_key.get(buyer_visit.visit_key)
    seller_required = state._passage_record_by_visit_key.get(seller_visit.visit_key)
    if buyer_required is not None:
        assert buyer_required.candidate_passage_timestep is None
    if seller_required is not None:
        assert seller_required.candidate_passage_timestep is None
    buyer_traffic = state._traffic_observation_record_by_visit_key.get(
        buyer_visit.visit_key
    )
    seller_traffic = state._traffic_observation_record_by_visit_key.get(
        seller_visit.visit_key
    )
    if buyer_traffic is not None:
        assert buyer_traffic.candidate_passage_timestep is None
    if seller_traffic is not None:
        assert seller_traffic.candidate_passage_timestep is None


def _buyer_only_binding_result(state, buyer_visit):
    return _binding_transfer_with_transferred_keys(
        state,
        (buyer_visit.visit_key,),
    )


def test_binding_apply_rejects_missing_traffic_map_key_without_partial_update():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    binding_result = _buyer_only_binding_result(state, buyer_visit)
    passage_before, traffic_before = _passage_and_traffic_snapshot(state)
    del state._traffic_observation_record_by_visit_key[buyer_visit.visit_key]
    try:
        orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
            state,
            binding_result,
            0,
            BASELINE_T,
        )
        raise AssertionError("expected RuntimeError for missing traffic map key")
    except RuntimeError:
        pass
    assert state.required_passage_records == passage_before
    assert state.traffic_observation_records_in_public_order == traffic_before


def test_binding_apply_rejects_missing_traffic_public_order_without_partial_update():
    _world, _local, state, buyer_visit, seller_visit, _np = (
        _traffic_observation_three_role_state()
    )
    binding_result = _buyer_only_binding_result(state, buyer_visit)
    filtered = []
    for record in state._traffic_observation_records_in_public_order:
        if record.visit_key != buyer_visit.visit_key:
            filtered.append(record)
    state._traffic_observation_records_in_public_order[:] = filtered
    try:
        orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
            state,
            binding_result,
            0,
            BASELINE_T,
        )
        raise AssertionError(
            "expected RuntimeError for missing traffic public order entry"
        )
    except RuntimeError:
        pass
    _candidate_passage_timesteps_unchanged(state, buyer_visit, seller_visit)


def test_binding_apply_rejects_missing_required_passage_map_key_without_partial_update():
    _world, _local, state, buyer_visit, seller_visit, _np = (
        _traffic_observation_three_role_state()
    )
    binding_result = _buyer_only_binding_result(state, buyer_visit)
    del state._passage_record_by_visit_key[buyer_visit.visit_key]
    try:
        orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
            state,
            binding_result,
            0,
            BASELINE_T,
        )
        raise AssertionError("expected RuntimeError for missing required map key")
    except RuntimeError:
        pass
    _candidate_passage_timesteps_unchanged(state, buyer_visit, seller_visit)


def test_binding_apply_rejects_missing_required_public_order_without_partial_update():
    _world, _local, state, buyer_visit, seller_visit, _np = (
        _traffic_observation_three_role_state()
    )
    binding_result = _buyer_only_binding_result(state, buyer_visit)
    filtered = []
    for record in state._passage_records_in_public_order:
        if record.visit_key != buyer_visit.visit_key:
            filtered.append(record)
    state._passage_records_in_public_order[:] = filtered
    try:
        orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
            state,
            binding_result,
            0,
            BASELINE_T,
        )
        raise AssertionError(
            "expected RuntimeError for missing required public order entry"
        )
    except RuntimeError:
        pass
    _candidate_passage_timesteps_unchanged(state, buyer_visit, seller_visit)


def test_binding_apply_rejects_duplicate_proposed_visit_keys_without_partial_update():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    binding_result = _buyer_only_binding_result(state, buyer_visit)
    passage_before, traffic_before = _passage_and_traffic_snapshot(state)
    original_propose_required = (
        orch_mod._propose_required_passage_updates_from_binding_transfer
    )

    def duplicate_required_propose(calculation_state, transfer_result, virtual_timestep):
        keys, records = original_propose_required(
            calculation_state,
            transfer_result,
            virtual_timestep,
        )
        if not records:
            return keys, records
        duplicated = (records[0], records[0])
        duplicated_keys = (keys[0], keys[0])
        return duplicated_keys, duplicated

    orch_mod._propose_required_passage_updates_from_binding_transfer = (
        duplicate_required_propose
    )
    try:
        try:
            orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
                state,
                binding_result,
                0,
                BASELINE_T,
            )
            raise AssertionError("expected RuntimeError for duplicate VisitKey")
        except RuntimeError as error:
            assert "more than once" in str(error)
    finally:
        orch_mod._propose_required_passage_updates_from_binding_transfer = (
            original_propose_required
        )
    assert state.required_passage_records == passage_before
    assert state.traffic_observation_records_in_public_order == traffic_before


def test_binding_apply_rejects_missing_trade_scope_nonparticipating_traffic_record():
    _world, _local, state, buyer_visit, seller_visit, np_visit = (
        _traffic_observation_three_role_state()
    )
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (np_visit.visit_key,),
    )
    del state._traffic_observation_record_by_visit_key[np_visit.visit_key]
    try:
        orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
            state,
            binding_result,
            0,
            BASELINE_T,
        )
        raise AssertionError(
            "expected RuntimeError for missing trade-scope traffic record"
        )
    except RuntimeError as error:
        assert "no traffic observation record" in str(error)
    _candidate_passage_timesteps_unchanged(state, buyer_visit, seller_visit)


def test_binding_apply_ignores_outside_trade_scope_transferred_visit_key():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    outside_key = ("outside_veh", 99)
    binding_result = _binding_transfer_with_transferred_keys(
        state,
        (outside_key,),
    )
    passage_before, traffic_before = _passage_and_traffic_snapshot(state)
    orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    assert state.required_passage_records == passage_before
    assert state.traffic_observation_records_in_public_order == traffic_before


def test_binding_apply_updates_both_passage_and_traffic_with_shared_frozen_records():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    binding_result = _buyer_only_binding_result(state, buyer_visit)
    orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
        state,
        binding_result,
        0,
        BASELINE_T,
    )
    required = state._passage_record_by_visit_key[buyer_visit.visit_key]
    traffic = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    assert type(required.candidate_passage_timestep) is int
    assert required.candidate_passage_timestep == traffic.candidate_passage_timestep
    for record in state._traffic_observation_records_in_public_order:
        if record.visit_key == buyer_visit.visit_key:
            assert record is traffic
            assert state._traffic_observation_record_by_visit_key[
                buyer_visit.visit_key
            ] is traffic


def _binding_scan_result(state):
    return orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        state.binding_transfer_state
    )


def _apply_traffic_observation_skip_and_clearance_updates(
    state,
    binding_result,
    *,
    offset=0,
    virtual_timestep=BASELINE_T,
):
    orch_mod._apply_binding_transfer_traffic_observation_skip_and_clearance_updates(
        state,
        binding_result,
        offset,
        virtual_timestep,
    )


def _traffic_metadata_snapshot(state, visit_key):
    record = state.traffic_observation_record_for_visit_key(visit_key)
    return (
        record.candidate_passage_timestep,
        record.observed_offset,
        record.observed_virtual_timestep,
        record.predicted_time_difference_timesteps,
        record.predicted_time_difference_seconds,
        record.predicted_signed_time_value_change,
        record.true_vot_per_second,
        record.baseline_passage_timestep,
        record.last_checked_offset,
        record.last_checked_virtual_timestep,
        record.last_temporary_skip_reason,
        record.last_temporary_skip_offset,
        record.latest_clearance_stop_context,
    )


def test_traffic_observation_temporary_skip_records_buyer_seller_and_nonparticipating():
    _world, _local, _collector, state, visits = _buyer_ready_case(
        horizon=1,
        incoming=False,
    )
    buyer_visit = visits[0]
    binding_result = _binding_scan_result(state)
    assert binding_result.temporarily_skipped_visits
    before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    after = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    assert after.last_checked_offset == 0
    assert after.last_checked_virtual_timestep == BASELINE_T
    assert after.last_temporary_skip_offset == 0
    assert (
        after.last_temporary_skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
    )
    assert before[0] == after.candidate_passage_timestep
    assert before[6] == after.true_vot_per_second
    assert before[7] == after.baseline_passage_timestep

    _world2, _local2, state2, _buyer2, seller_visit, _np2 = (
        _buyer_seller_np_staggered_passage_state(horizon=1)
    )
    binding2 = _binding_scan_result(state2)
    seller_skip = None
    for skip in binding2.temporarily_skipped_visits:
        if skip.binding_visit_key == seller_visit.visit_key:
            seller_skip = skip
            break
    assert seller_skip is not None
    _apply_traffic_observation_skip_and_clearance_updates(state2, binding2)
    seller_traffic = state2.traffic_observation_record_for_visit_key(
        seller_visit.visit_key
    )
    assert seller_traffic.last_temporary_skip_reason == seller_skip.skip_reason
    assert seller_traffic.last_checked_offset == 0

    _world3, _local3, state3, _buyer3, _seller3, np_visit = (
        _buyer_seller_np_staggered_passage_state(horizon=1)
    )
    template3 = _binding_transfer_scan_template(state3)
    np_skip = OrderControlTvtMpBindingVisitTemporarySkip(
        binding_visit_key=np_visit.visit_key,
        vehicle_name="np_veh",
        skip_reason=(
            OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
        ),
    )
    binding3 = dataclasses.replace(
        template3,
        transferred_binding_visit_keys=(),
        temporarily_skipped_visits=(np_skip,),
        stop_reason=OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED,
        stopped_binding_visit_key=None,
    )
    _apply_traffic_observation_skip_and_clearance_updates(state3, binding3)
    np_traffic = state3.traffic_observation_record_for_visit_key(np_visit.visit_key)
    assert np_traffic.last_temporary_skip_reason == np_skip.skip_reason


def test_traffic_observation_temporary_skip_ignores_outside_trade_scope():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    outside_key = ("outside_veh", 99)
    template = _binding_transfer_scan_template(state)
    outside_skip = OrderControlTvtMpBindingVisitTemporarySkip(
        binding_visit_key=outside_key,
        vehicle_name="outside_veh",
        skip_reason=(
            OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD
        ),
    )
    binding_result = dataclasses.replace(
        template,
        temporarily_skipped_visits=(outside_skip,),
    )
    before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    assert _traffic_metadata_snapshot(state, buyer_visit.visit_key) == before


def test_traffic_observation_temporary_skip_rejects_duplicate_and_transfer_overlap():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    template = _binding_transfer_scan_template(state)
    skip = OrderControlTvtMpBindingVisitTemporarySkip(
        binding_visit_key=buyer_visit.visit_key,
        vehicle_name="buyer_veh",
        skip_reason=(
            OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD
        ),
    )
    duplicate_binding = dataclasses.replace(
        template,
        transferred_binding_visit_keys=(),
        temporarily_skipped_visits=(skip, skip),
        stop_reason=OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED,
        stopped_binding_visit_key=None,
    )
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, duplicate_binding)
        raise AssertionError("expected RuntimeError for duplicate temporary skip")
    except RuntimeError as error:
        assert "twice" in str(error)

    overlap_binding = dataclasses.replace(
        template,
        transferred_binding_visit_keys=(buyer_visit.visit_key,),
        temporarily_skipped_visits=(skip,),
        stop_reason=OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED,
        stopped_binding_visit_key=None,
    )
    before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, overlap_binding)
        raise AssertionError("expected RuntimeError for transfer and skip overlap")
    except RuntimeError as error:
        assert "temporarily_skipped_visits" in str(error)
    assert _traffic_metadata_snapshot(state, buyer_visit.visit_key) == before


def test_traffic_observation_temporary_skip_rejects_observed_visit():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    binding_passage = _buyer_only_binding_result(state, buyer_visit)
    orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
        state,
        binding_passage,
        0,
        BASELINE_T,
    )
    template = _binding_transfer_scan_template(state)
    skip = OrderControlTvtMpBindingVisitTemporarySkip(
        binding_visit_key=buyer_visit.visit_key,
        vehicle_name="buyer_veh",
        skip_reason=(
            OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD
        ),
    )
    binding_skip = dataclasses.replace(
        template,
        temporarily_skipped_visits=(skip,),
    )
    metadata_before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, binding_skip)
        raise AssertionError("expected RuntimeError for skip on observed visit")
    except RuntimeError as error:
        assert "new temporary skip" in str(error)
    assert _traffic_metadata_snapshot(state, buyer_visit.visit_key) == metadata_before


def test_traffic_observation_clearance_records_context_and_preserves_skip_fields():
    _world, local_state, _collector, state, visits = _buyer_ready_case(horizon=1)
    buyer_visit = visits[0]
    _block_clearance_from_other_inlink(local_state)
    binding_result = _binding_scan_result(state)
    assert binding_result.stop_reason is (
        OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
    )
    skip_binding = dataclasses.replace(
        binding_result,
        stop_reason=OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED,
        stopped_binding_visit_key=None,
        temporarily_skipped_visits=(
            OrderControlTvtMpBindingVisitTemporarySkip(
                binding_visit_key=buyer_visit.visit_key,
                vehicle_name="buyer_veh",
                skip_reason=(
                    OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
                ),
            ),
        ),
    )
    _apply_traffic_observation_skip_and_clearance_updates(state, skip_binding)
    traffic_with_skip = state.traffic_observation_record_for_visit_key(
        buyer_visit.visit_key
    )
    assert traffic_with_skip.last_temporary_skip_offset == 0
    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    traffic = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    assert traffic.last_checked_offset == 0
    assert traffic.last_checked_virtual_timestep == BASELINE_T
    assert traffic.last_temporary_skip_offset == 0
    assert (
        traffic.last_temporary_skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
    )
    context = traffic.latest_clearance_stop_context
    assert context is not None
    assert context.offset == 0
    assert context.virtual_timestep == BASELINE_T
    assert context.stopped_binding_visit_key == buyer_visit.visit_key


def test_traffic_observation_clearance_does_not_update_rear_unreached_visit():
    _world, _local, _collector, state, visits = (
        _forward_visit_clearance_stops_before_rear_required_buyer_case(horizon=1)
    )
    rear_visit = visits[1]
    binding_result = _binding_scan_result(state)
    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    rear_traffic = state.traffic_observation_record_for_visit_key(rear_visit.visit_key)
    assert rear_traffic.last_checked_offset is None
    assert rear_traffic.latest_clearance_stop_context is None


def test_traffic_observation_clearance_ignores_outside_trade_scope_stop_target():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    outside_key = ("outside_veh", 99)
    template = _binding_transfer_scan_template(state)
    binding_result = dataclasses.replace(
        template,
        stop_reason=OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED,
        stopped_binding_visit_key=outside_key,
    )
    before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    assert _traffic_metadata_snapshot(state, buyer_visit.visit_key) == before


def test_traffic_observation_clearance_rejects_missing_stopped_key_and_duplicates():
    _world, local_state, _collector, state, visits = _buyer_ready_case(horizon=1)
    buyer_visit = visits[0]
    _block_clearance_from_other_inlink(local_state)
    binding_result = _binding_scan_result(state)
    broken_binding = dataclasses.replace(
        binding_result,
        stopped_binding_visit_key=None,
    )
    before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, broken_binding)
        raise AssertionError("expected RuntimeError for missing stopped visit key")
    except RuntimeError as error:
        assert "stopped_binding_visit_key is missing" in str(error)
    assert _traffic_metadata_snapshot(state, buyer_visit.visit_key) == before

    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
        raise AssertionError("expected RuntimeError for duplicate clearance context")
    except RuntimeError as error:
        assert "clearance stop context at offset" in str(error)


def test_traffic_observation_clearance_rejects_observed_visit():
    _world, _local, state, buyer_visit, _seller, _np = (
        _traffic_observation_three_role_state()
    )
    binding_passage = _buyer_only_binding_result(state, buyer_visit)
    orch_mod._apply_binding_transfer_required_passage_and_traffic_observation_updates(
        state,
        binding_passage,
        0,
        BASELINE_T,
    )
    template = _binding_transfer_scan_template(state)
    binding_clearance = dataclasses.replace(
        template,
        stop_reason=OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED,
        stopped_binding_visit_key=buyer_visit.visit_key,
    )
    metadata_before = _traffic_metadata_snapshot(state, buyer_visit.visit_key)
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, binding_clearance)
        raise AssertionError("expected RuntimeError for clearance on observed visit")
    except RuntimeError as error:
        assert "stopped for clearance" in str(error)
    assert _traffic_metadata_snapshot(state, buyer_visit.visit_key) == metadata_before


def test_traffic_observation_skip_and_clearance_map_and_public_order_share_record():
    _world, _local, _collector, state, visits = _buyer_ready_case(
        horizon=1,
        incoming=False,
    )
    buyer_visit = visits[0]
    binding_result = _binding_scan_result(state)
    _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
    updated = state.traffic_observation_record_for_visit_key(buyer_visit.visit_key)
    for record in state.traffic_observation_records_in_public_order:
        if record.visit_key == buyer_visit.visit_key:
            assert record is updated
            assert state._traffic_observation_record_by_visit_key[
                buyer_visit.visit_key
            ] is updated


def test_traffic_observation_skip_apply_failure_does_not_partially_update_records():
    _world, _local, _collector, state, visits = _buyer_ready_case(
        horizon=1,
        incoming=False,
    )
    buyer_visit = visits[0]
    binding_result = _binding_scan_result(state)
    snapshots = {}
    for record in state.traffic_observation_records_in_public_order:
        snapshots[record.visit_key] = _traffic_metadata_snapshot(state, record.visit_key)
    filtered = []
    for record in state._traffic_observation_records_in_public_order:
        if record.visit_key != buyer_visit.visit_key:
            filtered.append(record)
    state._traffic_observation_records_in_public_order[:] = filtered
    try:
        _apply_traffic_observation_skip_and_clearance_updates(state, binding_result)
        raise AssertionError("expected RuntimeError for missing public order entry")
    except RuntimeError:
        pass
    for visit_key, snapshot in snapshots.items():
        assert _traffic_metadata_snapshot(state, visit_key) == snapshot


def test_traffic_observation_skip_and_clearance_one_timestep_keeps_finished_and_resolved():
    _world, _local, _collector, state, _visits = _buyer_ready_case(horizon=1)
    result = run_tvt_mp_candidate_local_virtual_calculation(state)
    assert result.resolved is True
    assert result.stop_reason is (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
    )
    traffic = state.traffic_observation_record_for_visit_key(
        state.required_buyer_visit_keys[0]
    )
    assert traffic.candidate_passage_timestep == BASELINE_T
    assert traffic.last_checked_offset == 0


def test_economic_required_completion_timestamps_recorded_once_at_first_completion():
    _world, _local, state, _buyer, _seller, _np = (
        _buyer_seller_np_staggered_passage_state(horizon=4)
    )
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    assert state.economic_required_passages_complete_offset is None
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    assert state.economic_required_passages_complete_offset == 1
    assert state.economic_required_passages_complete_virtual_timestep == BASELINE_T + 1
    orch_mod._record_first_passage_completion_timestamps_if_needed(state, 99, 999)
    assert state.economic_required_passages_complete_offset == 1
    assert state.economic_required_passages_complete_virtual_timestep == BASELINE_T + 1


def test_all_trade_scope_completion_timestamps_recorded_once_at_first_completion():
    _world, _local, _collector, state, _visits = _buyer_and_seller_same_inlink_case(
        horizon=1
    )
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    assert state.all_trade_scope_passages_complete_offset == 0
    assert state.all_trade_scope_passages_complete_virtual_timestep == BASELINE_T
    orch_mod._record_first_passage_completion_timestamps_if_needed(state, 99, 999)
    assert state.all_trade_scope_passages_complete_offset == 0
    assert state.all_trade_scope_passages_complete_virtual_timestep == BASELINE_T


def test_zero_nonparticipating_trade_scope_sets_both_completion_timestamps_equal():
    _world, _local, _collector, state, _visits = _buyer_and_seller_same_inlink_case(
        horizon=1
    )
    run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    assert state.economic_required_passages_complete_offset == 0
    assert state.all_trade_scope_passages_complete_offset == 0
    assert (
        state.economic_required_passages_complete_virtual_timestep
        == state.all_trade_scope_passages_complete_virtual_timestep
    )


def test_buyer_seller_complete_with_nonparticipating_unpassed_finishes_with_partial_trade_scope_completion():
    _world, _local, state, buyer_visit, seller_visit, np_visit = (
        _traffic_observation_three_role_state()
    )
    original_binding = orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep

    def buyer_and_seller_only(binding_state):
        result = original_binding(binding_state)
        return dataclasses.replace(
            result,
            transferred_binding_visit_keys=(
                buyer_visit.visit_key,
                seller_visit.visit_key,
            ),
        )

    orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        buyer_and_seller_only
    )
    try:
        result = run_tvt_mp_candidate_local_virtual_calculation(state)
    finally:
        orch_mod.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
            original_binding
        )
    assert result.resolved is True
    assert state.economic_required_passages_complete_offset == 0
    assert state.economic_required_passages_complete_virtual_timestep == BASELINE_T
    assert state.all_trade_scope_passages_complete_offset is None
    assert state.all_trade_scope_passages_complete_virtual_timestep is None
    np_traffic = state.traffic_observation_record_for_visit_key(np_visit.visit_key)
    assert np_traffic.candidate_passage_timestep is None


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
