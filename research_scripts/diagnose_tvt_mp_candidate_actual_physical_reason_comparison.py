"""Compare Candidate local passage reasons with real-world passage reasons.

This diagnostic does not change production behavior. Wrappers call each
production function once and return its result unchanged. Official reasons
come from the frozen candidate binding result and from the real-world
functions' return values. This script does not decide passage itself.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferStopReason,
    OrderControlTvtMpBindingVisitTemporarySkipReason,
)
import uxsim.order_control_tvt_mp_candidate_binding_transfer as binding_module
import uxsim.order_control_tvt_mp_candidate_local_virtual_calculation as virtual_calculation_module
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.order_control_tvt_mp_physical_transfer as physical_transfer
from uxsim.uxsim import Link, Node, World

import research_scripts.run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_trial as extended_trial


EAST_NODE = "east_intersection"
TARGET_OUTLINK = "east_intersection_to_east_south"
OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_seed_1_initial_candidate_actual_physical_reason"
    )
)
VISIT_CSV_NAME = "candidate_actual_visit_physical_comparison.csv"
BOUNDARY_CSV_NAME = "candidate_actual_outlink_boundary_comparison.csv"
COMPARISON_PHASE = "not_equivalent"

REASON_NOT_ARRIVED = "not_arrived_at_target_node"
REASON_NOT_HEAD = "not_inlink_physical_head"
REASON_CLEARANCE = "clearance_not_satisfied"
REASON_INLINK_OUTFLOW = "inlink_outflow_capacity_unavailable"
REASON_NODE_FLOW = "node_flow_capacity_unavailable"
REASON_OUTLINK_INFLOW = "outlink_inflow_capacity_unavailable"
REASON_ENTRY = "outlink_entry_space_unavailable"
REASON_PASSED = "passed"
REASON_NOT_SCANNED = "not_scanned"
REASON_NOT_OBSERVABLE = "not_observable"

SCAN_REACHED = "reached"
SCAN_NOT_IN_CONFIRMED = "not_in_confirmed_candidates"
SCAN_PRIOR_CLEARANCE = "not_reached_after_prior_clearance_stop"
SCAN_UNEXPLAINED = "unexplained_not_reached"

CLASS_STRONG_PHYSICAL = "strong_physical_match"
CLASS_TIMING_PHYSICAL_DIFFERENCE = "timing_match_with_physical_difference"
CLASS_INCONSISTENCY = "implementation_inconsistency_suspected"
CLASS_INDETERMINATE = "indeterminate"

SEMANTIC_EXACT = "exact_match"
SEMANTIC_SCAN_PROCEDURE = "different_due_to_scan_procedure"
SEMANTIC_PHYSICAL_REASON = "physical_reason_mismatch"
SEMANTIC_NOT_COMPARABLE = "not_comparable"

PHYSICAL_REASONS = (
    REASON_NOT_ARRIVED,
    REASON_NOT_HEAD,
    REASON_CLEARANCE,
    REASON_INLINK_OUTFLOW,
    REASON_NODE_FLOW,
    REASON_OUTLINK_INFLOW,
    REASON_ENTRY,
    REASON_PASSED,
)

STATE_FIELDS = (
    "was_arrived",
    "was_inlink_physical_head",
    "clearance_satisfied",
    "inlink_outflow_capacity_satisfied",
    "node_flow_capacity_satisfied",
    "outlink_inflow_capacity_satisfied",
    "outlink_entry_space_available",
)

VISIT_COLUMNS = (
    "case_id",
    "decision_timestep",
    "node_name",
    "vehicle_name",
    "visit_id",
    "role",
    "numeric_timestep",
    "candidate_virtual_timestep",
    "actual_real_timestep",
    "inlink_name",
    "candidate_route_next_link_name",
    "actual_route_next_link_name",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "candidate_was_arrived",
    "candidate_was_inlink_physical_head",
    "candidate_clearance_satisfied",
    "candidate_inlink_outflow_capacity_satisfied",
    "candidate_node_flow_capacity_satisfied",
    "candidate_outlink_inflow_capacity_satisfied",
    "candidate_outlink_entry_space_available",
    "candidate_inlink_capacity_out_remain",
    "candidate_node_flow_capacity_remain",
    "candidate_outlink_capacity_in_remain",
    "candidate_outlink_vehicle_count",
    "candidate_outlink_vehicle_names_head_to_tail",
    "candidate_entrance_vehicle_name",
    "candidate_entrance_vehicle_position",
    "candidate_entry_gap",
    "candidate_last_order_control_inlink_name",
    "candidate_last_order_control_entry_timestep",
    "candidate_official_reason",
    "candidate_scan_reach_status",
    "candidate_prior_clearance_stop_visit_key",
    "candidate_passed",
    "candidate_temporary_skipped",
    "candidate_clearance_stopped",
    "actual_was_arrived",
    "actual_was_inlink_physical_head",
    "actual_clearance_satisfied",
    "actual_inlink_outflow_capacity_satisfied",
    "actual_node_flow_capacity_satisfied",
    "actual_outlink_inflow_capacity_satisfied",
    "actual_outlink_entry_space_available",
    "actual_inlink_capacity_out_remain",
    "actual_node_flow_capacity_remain",
    "actual_outlink_capacity_in_remain",
    "actual_outlink_vehicle_count",
    "actual_outlink_vehicle_names_head_to_tail",
    "actual_entrance_vehicle_name",
    "actual_entrance_vehicle_position",
    "actual_entry_gap",
    "actual_last_order_control_inlink_name",
    "actual_last_order_control_entry_timestep",
    "actual_official_reason",
    "actual_scan_reach_status",
    "actual_prior_clearance_stop_visit_key",
    "actual_passed",
    "actual_temporary_skipped",
    "actual_clearance_stopped",
    "state_tuple_match",
    "official_reason_match",
    "passage_flag_match",
    "scan_reach_status_match",
    "physical_comparison_stage",
    "physical_state_match",
    "scan_procedure_match",
    "official_reason_semantic_status",
    "row_comparison_status",
    "comparison_note",
)

BOUNDARY_COLUMNS = (
    "case_id",
    "decision_timestep",
    "numeric_timestep",
    "candidate_virtual_timestep",
    "actual_real_timestep",
    "outlink_name",
    "comparison_phase",
    "candidate_boundary_mode",
    "candidate_flow_allowance_before",
    "candidate_flow_allowance_added",
    "candidate_flow_allowance_after",
    "candidate_vehicle_names_at_end_before",
    "candidate_observed_outflow_exit_vehicle_names",
    "candidate_constrained_sink_exit_vehicle_names",
    "candidate_waiting_vehicle_names_after",
    "candidate_capacity_out_remain_before",
    "candidate_capacity_out_remain_after",
    "candidate_terminal_node_flow_capacity_before",
    "candidate_terminal_node_flow_capacity_after",
    "actual_downstream_exit_vehicle_names",
    "actual_outlink_vehicle_count_before_target_passage",
    "actual_outlink_vehicle_names_head_to_tail_before_target_passage",
    "actual_entrance_space_available_before_target_passage",
    "boundary_comparison_note",
)

CASES = (
    {
        "case_id": "buyer_t60_veh_ee_10_1",
        "decision_timestep": 60,
        "node_name": EAST_NODE,
        "vehicle_name": "veh_ee_10",
        "visit_id": 1,
        "role": "buyer",
        "baseline_passage_timestep": 80,
        "candidate_passage_timestep": 73,
        "actual_passage_timestep": 73,
        "route_next_link_name": TARGET_OUTLINK,
        "timestep_start": 60,
        "timestep_end": 73,
        "pre_arrival_start": 60,
        "pre_arrival_end": 72,
        "critical_start": 73,
        "critical_end": 73,
    },
    {
        "case_id": "seller_t135_veh_ee_19_1",
        "decision_timestep": 135,
        "node_name": EAST_NODE,
        "vehicle_name": "veh_ee_19",
        "visit_id": 1,
        "role": "seller",
        "baseline_passage_timestep": 149,
        "candidate_passage_timestep": 155,
        "actual_passage_timestep": 155,
        "route_next_link_name": TARGET_OUTLINK,
        "timestep_start": 135,
        "timestep_end": 155,
        "pre_arrival_start": 135,
        "pre_arrival_end": 152,
        "critical_start": 153,
        "critical_end": 155,
    },
)


class _Gate:
    def __init__(self) -> None:
        self.real_world = None
        self.observation_installed = False
        self.candidate_context = None
        self.candidate_events = []
        self.selected = {}
        self.actual_judgments = {}
        self.actual_clearance_stops = {}
        self.actual_scan_ran = {}
        self.actual_outlink_before = {}
        self.downstream_exits = {}
        self.downstream_ran = {}
        self.original_binding_scan = None
        self.original_candidate_transfer = None
        self.original_try_confirmed = None
        self.original_head_skip = None
        self.original_clearance = None
        self.original_shortage = None
        self.original_actual_transfer = None
        self.original_node_transfer = None
        self.original_world_copy = None
        self.original_driver = None


GATE = _Gate()


def _case_by_decision(decision_timestep: int):
    for case in CASES:
        if case["decision_timestep"] == decision_timestep:
            return case
    return None


def _case_by_numeric_timestep(timestep: int):
    for case in CASES:
        if case["timestep_start"] <= timestep <= case["timestep_end"]:
            return case
    return None


def _visit_key_of_case(case) -> tuple:
    return (case["vehicle_name"], case["visit_id"])


def _format_visit_key(visit_key) -> str:
    plain = _plain_visit_key(visit_key)
    return plain[0] + ":" + str(plain[1])


def _plain_visit_key(visit_key) -> tuple:
    if not isinstance(visit_key, tuple) or len(visit_key) != 2:
        raise RuntimeError(f"VisitKey must be a pair; got {visit_key!r}.")
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is invalid: {visit_key!r}.")
    if type(visit_id) is not int:
        raise RuntimeError(f"VisitKey visit id is invalid: {visit_key!r}.")
    return (vehicle_name, visit_id)


def _buyers_id(buyers) -> str:
    parts = []
    for visit_key in buyers:
        plain = _plain_visit_key(visit_key)
        parts.append(plain[0] + ":" + str(plain[1]))
    return "|".join(parts)


def _cell(value) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _join_names(names) -> str:
    if names is None:
        return ""
    return "|".join(names)


def _number_or_blank(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    return value


def _snapshot_link(link) -> dict:
    names = []
    for vehicle in list(link.vehicles):
        names.append(vehicle.name)
    lanes = link.number_of_lanes
    entrance_name = ""
    entrance_position = ""
    if len(names) >= lanes and lanes > 0:
        entrance_vehicle = link.vehicles[-lanes]
        entrance_name = entrance_vehicle.name
        entrance_position = entrance_vehicle.x
    entry_gap = ""
    delta = getattr(link, "delta_per_lane", None)
    if not isinstance(delta, bool) and isinstance(delta, (int, float)):
        deltan = link.W.DELTAN
        if not isinstance(deltan, bool) and isinstance(deltan, (int, float)):
            entry_gap = delta * deltan
    return {
        "capacity_out_remain": _number_or_blank(link.capacity_out_remain),
        "capacity_in_remain": _number_or_blank(link.capacity_in_remain),
        "vehicle_names": tuple(names),
        "lanes": lanes,
        "entrance_name": entrance_name,
        "entrance_position": entrance_position,
        "entry_gap": entry_gap,
    }


def _snapshot_node(node) -> dict:
    incoming_names = []
    for vehicle in list(node.incoming_vehicles):
        incoming_names.append(vehicle.name)
    links = {}
    for link in list(node.inlinks.values()) + list(node.outlinks.values()):
        links[link.name] = _snapshot_link(link)
    last_inlink = node.last_order_control_inlink
    last_name = ""
    if last_inlink is not None:
        last_name = last_inlink.name
    last_entry = node.last_order_control_entry_timestep
    if last_entry is None:
        last_entry = ""
    return {
        "incoming_names": tuple(incoming_names),
        "last_inlink_name": last_name,
        "last_entry_timestep": last_entry,
        "clearance_required": node.order_control_clearance_timesteps,
        "node_flow_capacity_remain": _number_or_blank(node.flow_capacity_remain),
        "deltan": _number_or_blank(node.W.DELTAN),
        "links": links,
    }


def _reject_real_node(node) -> None:
    real_world = GATE.real_world
    if real_world is None:
        return
    real_node = real_world.get_node(node.name)
    if node is real_node:
        raise RuntimeError(
            f"Candidate observation saw the real Node {node.name!r}."
        )


def _in_candidate_window(decision_timestep: int, virtual_timestep: int) -> bool:
    case = _case_by_decision(decision_timestep)
    if case is None:
        return False
    return case["timestep_start"] <= virtual_timestep <= case["timestep_end"]


def _context_from_binding_state(binding_transfer_state):
    local_state = binding_transfer_state.virtual_time_state.candidate_local_state
    if local_state.target_node_name != EAST_NODE:
        return None
    decision_timestep = local_state.real_world_timestep_T
    virtual_timestep = local_state.local_world.T
    if not _in_candidate_window(decision_timestep, virtual_timestep):
        return None
    if local_state.local_world is GATE.real_world:
        raise RuntimeError(
            "Candidate binding scan is running on the real World."
        )
    _reject_real_node(local_state.target_node)
    buyers = (
        local_state.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    return {
        "decision_timestep": decision_timestep,
        "buyers_id": _buyers_id(buyers),
        "virtual_timestep": virtual_timestep,
        "node": local_state.target_node,
    }


def _append_candidate_event(kind: str, visit_key, picture: dict) -> None:
    context = GATE.candidate_context
    GATE.candidate_events.append(
        {
            "decision_timestep": context["decision_timestep"],
            "buyers_id": context["buyers_id"],
            "virtual_timestep": context["virtual_timestep"],
            "kind": kind,
            "visit_key": visit_key,
            "picture": picture,
        }
    )


def _is_case_visit_key(visit_key) -> bool:
    for case in CASES:
        if _visit_key_of_case(case) == visit_key:
            return True
    return False


def _snapshot_case_visits(binding_transfer_state):
    local_state = binding_transfer_state.virtual_time_state.candidate_local_state
    node = local_state.target_node
    pairs = local_state.binding_visit_local_vehicle_pairs
    visits = local_state.binding_rank_sequence.visits_in_binding_order
    observations = {}
    if len(pairs) != len(visits):
        return observations
    for pair, binding_visit in zip(pairs, visits):
        try:
            visit_key = _plain_visit_key(binding_visit.visit_key)
        except RuntimeError:
            continue
        if not _is_case_visit_key(visit_key):
            continue
        vehicle = pair.local_vehicle
        identity = {
            "visit_identity_confirmed": False,
            "current_link_name": "",
            "on_target_inlink": "",
            "in_incoming": "",
            "is_physical_head": "",
            "formal_inlink": binding_visit.inlink_name,
            "formal_route": binding_visit.route_next_link_name,
        }
        if getattr(vehicle, "name", None) != visit_key[0]:
            observations[_format_visit_key(visit_key)] = identity
            continue
        current_visit = getattr(vehicle, "order_control_current_visit", None)
        if (
            not isinstance(current_visit, dict)
            or current_visit.get("node") is not node
            or current_visit.get("visit_id") != visit_key[1]
        ):
            observations[_format_visit_key(visit_key)] = identity
            continue
        link = getattr(vehicle, "link", None)
        on_target_inlink = (
            link is not None
            and link.name == binding_visit.inlink_name
            and getattr(link, "end_node", None) is node
        )
        is_head = ""
        if on_target_inlink:
            vehicle_list = list(link.vehicles)
            is_head = len(vehicle_list) > 0 and vehicle_list[0] is vehicle
        identity["visit_identity_confirmed"] = True
        identity["current_link_name"] = "" if link is None else link.name
        identity["on_target_inlink"] = on_target_inlink
        identity["in_incoming"] = vehicle in node.incoming_vehicles
        identity["is_physical_head"] = is_head
        observations[_format_visit_key(visit_key)] = identity
    return observations


def wrapped_binding_scan(binding_transfer_state):
    context = _context_from_binding_state(binding_transfer_state)
    GATE.candidate_context = context
    if context is not None:
        picture = _snapshot_node(context["node"])
        picture["visit_observations"] = _snapshot_case_visits(binding_transfer_state)
        _append_candidate_event(
            "scan_start",
            None,
            picture,
        )
    try:
        result = GATE.original_binding_scan(binding_transfer_state)
    finally:
        GATE.candidate_context = None
    return result


def _candidate_visit_key_before_move(local_vehicle, target_node):
    current_visit = local_vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        raise RuntimeError(
            f"Vehicle {local_vehicle.name!r} has no current visit before "
            "the candidate transfer."
        )
    if current_visit.get("node") is not target_node:
        raise RuntimeError(
            f"Vehicle {local_vehicle.name!r} current visit is not the "
            "candidate target Node before transfer."
        )
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        raise RuntimeError(
            f"Vehicle {local_vehicle.name!r} visit id is invalid before "
            "the candidate transfer."
        )
    return (local_vehicle.name, visit_id)


def wrapped_candidate_transfer(
    *,
    target_node,
    local_world,
    local_vehicle,
    inlink,
    outlink,
):
    saved_key = None
    if GATE.candidate_context is not None:
        saved_key = _candidate_visit_key_before_move(local_vehicle, target_node)
    result = GATE.original_candidate_transfer(
        target_node=target_node,
        local_world=local_world,
        local_vehicle=local_vehicle,
        inlink=inlink,
        outlink=outlink,
    )
    if saved_key is not None:
        _append_candidate_event(
            "transfer_after",
            saved_key,
            _snapshot_node(target_node),
        )
    return result


def _actual_should_record(node) -> bool:
    if GATE.real_world is None or node.W is not GATE.real_world:
        return False
    if node.W._order_control_baseline_collector is not None:
        return False
    if node.name != EAST_NODE:
        return False
    return _case_by_numeric_timestep(node.W.T) is not None


def _remember_actual(visit_key, timestep: int, **fields) -> None:
    key = (visit_key, timestep)
    individual = fields.pop("individual", False)
    current = GATE.actual_judgments.get(key)
    if current is None:
        current = {
            "official_reason": "",
            "picture": None,
            "passed": False,
            "temporary_skipped": False,
            "clearance_stopped": False,
            "route_next_link_name": "",
            "inlink_name": "",
            "individual": False,
            "scan_reach_status": "",
            "prior_clearance_stop_visit_key": "",
            "formal_not_arrived": False,
            "observed_head": "",
            "visit_identity_confirmed": False,
            "in_confirmed": "",
            "confirmed_position": "",
            "assigned_rank": "",
            "in_incoming": "",
        }
        GATE.actual_judgments[key] = current
    if current.get("individual") is True and individual is not True:
        protected = {
            "official_reason",
            "picture",
            "passed",
            "temporary_skipped",
            "clearance_stopped",
            "route_next_link_name",
            "inlink_name",
        }
        for field_name, field_value in fields.items():
            if field_name in protected:
                continue
            current[field_name] = field_value
        return
    for field_name, field_value in fields.items():
        current[field_name] = field_value
    if individual is True:
        current["individual"] = True


def _visit_key_on_node(vehicle, node):
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return None
    if current_visit.get("node") is not node:
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        return None
    vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        return None
    return (vehicle_name, visit_id)


def _confirmed_candidate_identity(node, candidate):
    try:
        visit_key = _plain_visit_key(candidate.visit_key)
    except RuntimeError:
        return None
    vehicle = getattr(candidate, "vehicle", None)
    if vehicle is None or getattr(vehicle, "name", None) != visit_key[0]:
        return None
    if _visit_key_on_node(vehicle, node) != visit_key:
        return None
    return visit_key


def _formal_target_visit_observation(node, visit_key):
    vehicles = getattr(node.W, "VEHICLES", None)
    if not isinstance(vehicles, dict):
        return None
    vehicle = vehicles.get(visit_key[0])
    if vehicle is None or getattr(vehicle, "name", None) != visit_key[0]:
        return None
    if _visit_key_on_node(vehicle, node) != visit_key:
        return None
    current_visit = vehicle.order_control_current_visit
    inlink = current_visit.get("inlink")
    if inlink is None or getattr(vehicle, "link", None) is not inlink:
        return None
    if getattr(inlink, "end_node", None) is not node:
        return None
    vehicle_list = list(inlink.vehicles)
    route = getattr(vehicle, "route_next_link", None)
    route_name = ""
    if route is not None and getattr(route, "start_node", None) is node:
        route_name = route.name
    return {
        "in_incoming": vehicle in node.incoming_vehicles,
        "current_link_name": inlink.name,
        "inlink_name": inlink.name,
        "is_physical_head": len(vehicle_list) > 0 and vehicle_list[0] is vehicle,
        "on_target_inlink": True,
        "route_next_link_name": route_name,
        "formal_not_arrived": vehicle not in node.incoming_vehicles,
    }


def _save_confirmed_visit_positions_before_production(node, confirmed_candidates):
    picture = _snapshot_node(node)
    timestep = node.W.T
    positions = {}
    for index, candidate in enumerate(confirmed_candidates):
        identity = _confirmed_candidate_identity(node, candidate)
        if identity is None or identity in positions:
            continue
        positions[identity] = index
    targets = {}
    for case in CASES:
        if not (case["timestep_start"] <= timestep <= case["timestep_end"]):
            continue
        visit_key = _visit_key_of_case(case)
        assigned_rank = ""
        confirmed_index = positions.get(visit_key)
        if confirmed_index is not None:
            assigned_rank = confirmed_candidates[confirmed_index].assigned_rank
        targets[visit_key] = {
            "in_confirmed": confirmed_index is not None,
            "confirmed_index": confirmed_index,
            "assigned_rank": assigned_rank,
            "observation": _formal_target_visit_observation(node, visit_key),
        }
    return {
        "timestep": timestep,
        "picture": picture,
        "positions": positions,
        "targets": targets,
    }


def _earlier_clearance_stop(target_index, positions, stop_keys):
    if type(target_index) is not int:
        return None
    for stop_key in stop_keys:
        stop_index = positions.get(stop_key)
        if type(stop_index) is not int:
            continue
        if stop_index < target_index:
            return stop_key
    return None


def _physical_observation_fields(observation):
    if observation is None:
        return {
            "visit_identity_confirmed": False,
            "formal_not_arrived": False,
            "observed_head": "",
            "in_incoming": "",
            "inlink_name": "",
            "route_next_link_name": "",
        }
    return {
        "visit_identity_confirmed": True,
        "formal_not_arrived": observation["formal_not_arrived"] is True,
        "observed_head": observation["is_physical_head"],
        "in_incoming": observation["in_incoming"],
        "inlink_name": observation["inlink_name"],
        "route_next_link_name": observation["route_next_link_name"],
    }


def _reach_decision(target, positions, stop_keys):
    physical = _physical_observation_fields(target["observation"])
    formal_not_arrived = physical["formal_not_arrived"] is True
    if target["in_confirmed"] is not True:
        if formal_not_arrived is True:
            official_reason = REASON_NOT_ARRIVED
        else:
            official_reason = REASON_NOT_SCANNED
            formal_not_arrived = False
        physical["formal_not_arrived"] = formal_not_arrived
        return {
            "official_reason": official_reason,
            "scan_reach_status": SCAN_NOT_IN_CONFIRMED,
            "prior": "",
            **physical,
        }
    prior = _earlier_clearance_stop(target["confirmed_index"], positions, stop_keys)
    if prior is not None:
        physical["formal_not_arrived"] = False
        return {
            "official_reason": REASON_NOT_SCANNED,
            "scan_reach_status": SCAN_PRIOR_CLEARANCE,
            "prior": _format_visit_key(prior),
            **physical,
        }
    physical["formal_not_arrived"] = False
    return {
        "official_reason": REASON_NOT_OBSERVABLE,
        "scan_reach_status": SCAN_UNEXPLAINED,
        "prior": "",
        **physical,
    }


def _finalize_actual_scan_reach(prescan) -> None:
    timestep = prescan["timestep"]
    stop_keys = tuple(GATE.actual_clearance_stops.get(timestep, ()))
    for visit_key, target in prescan["targets"].items():
        decision = _reach_decision(target, prescan["positions"], stop_keys)
        meta = {
            "scan_reach_status": decision["scan_reach_status"],
            "prior_clearance_stop_visit_key": decision["prior"],
            "formal_not_arrived": decision["formal_not_arrived"],
            "observed_head": decision["observed_head"],
            "visit_identity_confirmed": decision["visit_identity_confirmed"],
            "in_confirmed": target["in_confirmed"],
            "confirmed_position": (
                ""
                if target["confirmed_index"] is None
                else target["confirmed_index"] + 1
            ),
            "assigned_rank": target["assigned_rank"],
            "in_incoming": decision["in_incoming"],
        }
        current = GATE.actual_judgments.get((visit_key, timestep))
        if current is not None and current.get("individual") is True:
            current["scan_reach_status"] = SCAN_REACHED
            current["prior_clearance_stop_visit_key"] = ""
            current["in_confirmed"] = target["in_confirmed"]
            current["confirmed_position"] = meta["confirmed_position"]
            current["assigned_rank"] = target["assigned_rank"]
            current["in_incoming"] = decision["in_incoming"]
            continue
        _remember_actual(
            visit_key,
            timestep,
            official_reason=decision["official_reason"],
            picture=prescan["picture"],
            passed=False,
            temporary_skipped=False,
            clearance_stopped=False,
            inlink_name=decision["inlink_name"],
            route_next_link_name=decision["route_next_link_name"],
            **meta,
        )


def wrapped_try_confirmed(node, confirmed_candidates):
    prescan = None
    if _actual_should_record(node):
        timestep = node.W.T
        GATE.actual_scan_ran[timestep] = True
        GATE.actual_clearance_stops[timestep] = []
        prescan = _save_confirmed_visit_positions_before_production(
            node,
            confirmed_candidates,
        )
        GATE.actual_outlink_before[timestep] = prescan["picture"]["links"].get(TARGET_OUTLINK)
    try:
        result = GATE.original_try_confirmed(node, confirmed_candidates)
    except BaseException:
        raise
    else:
        if prescan is not None:
            _finalize_actual_scan_reach(prescan)
    return result


def wrapped_head_skip(vehicle, inlink):
    node = inlink.end_node
    visit_key = None
    picture = None
    if _actual_should_record(node):
        visit_key = _current_visit_key_or_none(vehicle, node)
        if visit_key is not None:
            picture = _snapshot_node(node)
    result = GATE.original_head_skip(vehicle, inlink)
    if visit_key is not None and result is True:
        _remember_actual(
            visit_key,
            node.W.T,
            official_reason=REASON_NOT_HEAD,
            picture=picture,
            temporary_skipped=True,
            inlink_name=inlink.name,
            route_next_link_name=_route_name(vehicle),
            individual=True,
        )
    return result


def wrapped_clearance(node, vehicle, inlink):
    observed_key = None
    target_key = None
    picture = None
    if _actual_should_record(node):
        observed_key = _visit_key_on_node(vehicle, node)
        target_key = _current_visit_key_or_none(vehicle, node)
        if target_key is not None:
            picture = _snapshot_node(node)
    result = GATE.original_clearance(node, vehicle, inlink)
    if observed_key is not None and result is True:
        GATE.actual_clearance_stops.setdefault(node.W.T, []).append(observed_key)
    if target_key is not None and result is True:
        _remember_actual(
            target_key,
            node.W.T,
            official_reason=REASON_CLEARANCE,
            picture=picture,
            clearance_stopped=True,
            inlink_name=inlink.name,
            route_next_link_name=_route_name(vehicle),
            individual=True,
        )
    return result


def wrapped_shortage(node, inlink, outlink):
    picture = None
    if _actual_should_record(node):
        picture = _snapshot_node(node)
    result = GATE.original_shortage(node, inlink, outlink)
    if picture is not None and result is not None and len(inlink.vehicles) > 0:
        vehicle = inlink.vehicles[0]
        visit_key = _current_visit_key_or_none(vehicle, node)
        if visit_key is not None:
            _remember_actual(
                visit_key,
                node.W.T,
                official_reason=result,
                picture=picture,
                temporary_skipped=True,
                inlink_name=inlink.name,
                route_next_link_name=outlink.name,
                individual=True,
            )
    return result


def _current_visit_key_or_none(vehicle, node):
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return None
    if current_visit.get("node") is not node:
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        return None
    visit_key = (vehicle.name, visit_id)
    if _case_by_numeric_timestep(node.W.T) is None:
        return None
    for case in CASES:
        if _visit_key_of_case(case) == visit_key:
            if case["timestep_start"] <= node.W.T <= case["timestep_end"]:
                return visit_key
    return None


def _route_name(vehicle) -> str:
    route = getattr(vehicle, "route_next_link", None)
    if route is None:
        return ""
    return route.name


def _passage_identity_before_actual_transfer(node, vehicle):
    if not _actual_should_record(node):
        return None
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        return None
    if current_visit.get("node") is not node:
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        return None
    visit_key = (vehicle.name, visit_id)
    for case in CASES:
        if _visit_key_of_case(case) != visit_key:
            continue
        if case["timestep_start"] <= node.W.T <= case["timestep_end"]:
            return visit_key
    return None


def wrapped_actual_transfer(node, vehicle, inlink, outlink):
    saved_key = _passage_identity_before_actual_transfer(node, vehicle)
    saved_picture = None
    if saved_key is not None:
        saved_picture = _snapshot_node(node)
    result = GATE.original_actual_transfer(node, vehicle, inlink, outlink)
    if saved_key is not None:
        _remember_actual(
            saved_key,
            node.W.T,
            official_reason=REASON_PASSED,
            picture=saved_picture,
            passed=True,
            temporary_skipped=False,
            clearance_stopped=False,
            inlink_name=inlink.name,
            route_next_link_name=outlink.name,
            individual=True,
        )
    return result


def _downstream_should_record(node) -> bool:
    if GATE.real_world is None or node.W is not GATE.real_world:
        return False
    if node.W._order_control_baseline_collector is not None:
        return False
    if _case_by_numeric_timestep(node.W.T) is None:
        return False
    outlink = node.W.get_link(TARGET_OUTLINK)
    return outlink.end_node is node


def wrapped_node_transfer(node):
    before_names = None
    timestep = None
    if _downstream_should_record(node):
        timestep = node.W.T
        outlink = node.W.get_link(TARGET_OUTLINK)
        before_names = []
        for vehicle in list(outlink.vehicles):
            before_names.append(vehicle.name)
    result = GATE.original_node_transfer(node)
    if before_names is not None:
        outlink = node.W.get_link(TARGET_OUTLINK)
        after_names = []
        for vehicle in list(outlink.vehicles):
            after_names.append(vehicle.name)
        exits = []
        after_set = set(after_names)
        for vehicle_name in before_names:
            if vehicle_name not in after_set:
                exits.append(vehicle_name)
        GATE.downstream_ran[timestep] = True
        GATE.downstream_exits[timestep] = tuple(exits)
    return result


def wrapped_world_copy(world):
    installed = GATE.observation_installed
    restore_observation_hooks()
    try:
        return GATE.original_world_copy(world)
    finally:
        if installed:
            install_observation_hooks()


def wrapped_driver(world):
    result = GATE.original_driver(world)
    if world is GATE.real_world and _case_by_decision(world.T) is not None:
        _keep_selected_candidate(world.T, result)
    return result


def _selected_local_result(driver_result, decision_timestep: int):
    atomic = driver_result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(
            f"T={decision_timestep}: driver returned no atomic apply result."
        )
    validation = atomic.final_consistency_validation_set_result
    final_rank = validation.final_rank_set_result
    payment = final_rank.payment_and_compensation_set_result
    selection = payment.candidate_selection_set_result
    selected_node = None
    for node_result in selection.node_candidate_selection_results:
        if node_result.node_name == EAST_NODE:
            selected_node = node_result
            break
    if selected_node is None:
        raise RuntimeError(
            f"T={decision_timestep}: east_intersection has no selection result."
        )
    economic = selected_node.selected_candidate_economic_result
    if economic is None:
        raise RuntimeError(
            f"T={decision_timestep}: east_intersection selected no candidate."
        )
    local_result = economic.candidate_local_virtual_calculation_result
    if local_result.node_name != EAST_NODE:
        raise RuntimeError(
            f"T={decision_timestep}: selected local result node is "
            f"{local_result.node_name!r}."
        )
    if local_result.baseline_timestep_T != decision_timestep:
        raise RuntimeError(
            f"T={decision_timestep}: selected local baseline timestep is "
            f"{local_result.baseline_timestep_T}."
        )
    return local_result


def _keep_selected_candidate(decision_timestep: int, driver_result) -> None:
    local_result = _selected_local_result(driver_result, decision_timestep)
    buyers_id = _buyers_id(local_result.concrete_buyer_candidate_set.buyers_sorted)
    kept = []
    for event in GATE.candidate_events:
        if event["decision_timestep"] != decision_timestep:
            kept.append(event)
            continue
        if event["buyers_id"] == buyers_id:
            kept.append(event)
    GATE.candidate_events = kept
    GATE.selected[decision_timestep] = {
        "local_result": local_result,
        "buyers_id": buyers_id,
    }


def install_observation_hooks() -> None:
    if GATE.observation_installed:
        return
    GATE.original_binding_scan = (
        binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    )
    GATE.original_candidate_transfer = binding_module._transfer_one_vehicle_like_uxsim
    GATE.original_try_confirmed = physical_transfer._try_confirmed_candidates
    GATE.original_head_skip = physical_transfer._inlink_physical_head_should_skip
    GATE.original_clearance = Node._order_control_clearance_blocks_passage
    GATE.original_shortage = physical_transfer._first_ordinary_physical_shortage
    GATE.original_actual_transfer = Node._transfer_one_vehicle_between_links
    GATE.original_node_transfer = Node.transfer
    GATE.original_world_copy = World.copy
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        wrapped_binding_scan
    )
    virtual_calculation_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        wrapped_binding_scan
    )
    binding_module._transfer_one_vehicle_like_uxsim = wrapped_candidate_transfer
    physical_transfer._try_confirmed_candidates = wrapped_try_confirmed
    physical_transfer._inlink_physical_head_should_skip = wrapped_head_skip
    Node._order_control_clearance_blocks_passage = wrapped_clearance
    physical_transfer._first_ordinary_physical_shortage = wrapped_shortage
    Node._transfer_one_vehicle_between_links = wrapped_actual_transfer
    Node.transfer = wrapped_node_transfer
    World.copy = wrapped_world_copy
    GATE.observation_installed = True


def restore_observation_hooks() -> None:
    if GATE.observation_installed is not True:
        return
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        GATE.original_binding_scan
    )
    virtual_calculation_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        GATE.original_binding_scan
    )
    binding_module._transfer_one_vehicle_like_uxsim = GATE.original_candidate_transfer
    physical_transfer._try_confirmed_candidates = GATE.original_try_confirmed
    physical_transfer._inlink_physical_head_should_skip = GATE.original_head_skip
    Node._order_control_clearance_blocks_passage = GATE.original_clearance
    physical_transfer._first_ordinary_physical_shortage = GATE.original_shortage
    Node._transfer_one_vehicle_between_links = GATE.original_actual_transfer
    Node.transfer = GATE.original_node_transfer
    World.copy = GATE.original_world_copy
    GATE.observation_installed = False


def install_driver_hook() -> None:
    GATE.original_driver = driver_module.run_tvt_mp_driver
    driver_module.run_tvt_mp_driver = wrapped_driver


def restore_driver_hook() -> None:
    driver_module.run_tvt_mp_driver = GATE.original_driver


def _capacity_satisfied(remain, deltan):
    if remain == "" or deltan == "":
        return ""
    return remain >= deltan


def _entry_available(link_picture) -> bool:
    if link_picture["lanes"] == "" or link_picture["vehicle_names"] is None:
        return ""
    if len(link_picture["vehicle_names"]) < link_picture["lanes"]:
        return True
    if link_picture["entrance_position"] == "" or link_picture["entry_gap"] == "":
        return ""
    return link_picture["entrance_position"] > link_picture["entry_gap"]


def _clearance_satisfied(picture, inlink_name: str, timestep: int):
    last_name = picture["last_inlink_name"]
    if last_name == "":
        return True
    if last_name == inlink_name:
        return True
    last_entry = picture["last_entry_timestep"]
    required = picture["clearance_required"]
    if last_entry == "" or required == "":
        return ""
    return (timestep - last_entry) > required


def _state_from_picture(picture, vehicle_name: str, inlink_name: str, outlink_name: str, timestep: int):
    if picture is None or inlink_name == "" or outlink_name == "":
        return None
    inlink = picture["links"].get(inlink_name)
    outlink = picture["links"].get(outlink_name)
    if inlink is None or outlink is None:
        return None
    arrived = vehicle_name in picture["incoming_names"]
    head = len(inlink["vehicle_names"]) > 0 and inlink["vehicle_names"][0] == vehicle_name
    return {
        "was_arrived": arrived,
        "was_inlink_physical_head": head,
        "clearance_satisfied": _clearance_satisfied(picture, inlink_name, timestep),
        "inlink_outflow_capacity_satisfied": _capacity_satisfied(
            inlink["capacity_out_remain"],
            picture["deltan"],
        ),
        "node_flow_capacity_satisfied": _capacity_satisfied(
            picture["node_flow_capacity_remain"],
            picture["deltan"],
        ),
        "outlink_inflow_capacity_satisfied": _capacity_satisfied(
            outlink["capacity_in_remain"],
            picture["deltan"],
        ),
        "outlink_entry_space_available": _entry_available(outlink),
        "inlink_capacity_out_remain": inlink["capacity_out_remain"],
        "node_flow_capacity_remain": picture["node_flow_capacity_remain"],
        "outlink_capacity_in_remain": outlink["capacity_in_remain"],
        "outlink_vehicle_count": len(outlink["vehicle_names"]),
        "outlink_vehicle_names_head_to_tail": _join_names(outlink["vehicle_names"]),
        "entrance_vehicle_name": outlink["entrance_name"],
        "entrance_vehicle_position": outlink["entrance_position"],
        "entry_gap": outlink["entry_gap"],
        "last_inlink_name": picture["last_inlink_name"],
        "last_entry_timestep": picture["last_entry_timestep"],
    }


def _candidate_reason(binding_result, visit_key):
    plain_key = _plain_visit_key(visit_key)
    transferred = []
    for transferred_key in binding_result.transferred_binding_visit_keys:
        transferred.append(_plain_visit_key(transferred_key))
    if plain_key in transferred:
        return REASON_PASSED, True, False, False
    stopped_key = None
    if binding_result.stopped_binding_visit_key is not None:
        stopped_key = _plain_visit_key(binding_result.stopped_binding_visit_key)
    if (
        binding_result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
        and stopped_key == plain_key
    ):
        return REASON_CLEARANCE, False, False, True
    for skip in binding_result.temporarily_skipped_visits:
        if _plain_visit_key(skip.binding_visit_key) != plain_key:
            continue
        reason = skip.skip_reason.value
        if not isinstance(skip.skip_reason, OrderControlTvtMpBindingVisitTemporarySkipReason):
            raise RuntimeError(f"Unexpected candidate skip reason {reason!r}.")
        return reason, False, True, False
    return REASON_NOT_SCANNED, False, False, False


def _candidate_scan_fields(local_result, binding_result, visit_key):
    reason, passed, skipped, stopped = _candidate_reason(binding_result, visit_key)
    if reason != REASON_NOT_SCANNED:
        return reason, passed, skipped, stopped, SCAN_REACHED, ""
    stopped_key = None
    if binding_result.stopped_binding_visit_key is not None:
        stopped_key = _plain_visit_key(binding_result.stopped_binding_visit_key)
    target_key = _plain_visit_key(visit_key)
    if (
        binding_result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
        and stopped_key is not None
        and stopped_key != target_key
    ):
        stopped_index = None
        target_index = None
        for index, binding_visit in enumerate(
            local_result.binding_rank_sequence.visits_in_binding_order
        ):
            key = _plain_visit_key(binding_visit.visit_key)
            if key == stopped_key:
                stopped_index = index
            if key == target_key:
                target_index = index
        if (
            stopped_index is not None
            and target_index is not None
            and stopped_index < target_index
        ):
            return (
                reason,
                passed,
                skipped,
                stopped,
                SCAN_PRIOR_CLEARANCE,
                _format_visit_key(stopped_key),
            )
    return reason, passed, skipped, stopped, "", ""


def _events_for(decision_timestep: int, buyers_id: str, virtual_timestep: int):
    matched = []
    for event in GATE.candidate_events:
        if event["decision_timestep"] != decision_timestep:
            continue
        if event["buyers_id"] != buyers_id:
            continue
        if event["virtual_timestep"] != virtual_timestep:
            continue
        matched.append(event)
    return matched


def _picture_before_target(local_result, buyers_id: str, timestep_result, visit_key):
    events = _events_for(
        local_result.baseline_timestep_T,
        buyers_id,
        timestep_result.virtual_timestep,
    )
    scan_start = None
    after_by_visit = {}
    for event in events:
        if event["kind"] == "scan_start":
            scan_start = event["picture"]
        elif event["kind"] == "transfer_after":
            after_by_visit[_plain_visit_key(event["visit_key"])] = event["picture"]
    if scan_start is None:
        raise RuntimeError(
            "Missing candidate scan-start snapshot at virtual timestep "
            f"{timestep_result.virtual_timestep}."
        )
    earlier = set()
    for previous in local_result.timestep_results:
        if previous.virtual_timestep >= timestep_result.virtual_timestep:
            break
        for transferred_key in previous.binding_transfer_result.transferred_binding_visit_keys:
            earlier.add(_plain_visit_key(transferred_key))
    picture = scan_start
    binding_result = timestep_result.binding_transfer_result
    transferred_now = set()
    for transferred_key in binding_result.transferred_binding_visit_keys:
        transferred_now.add(_plain_visit_key(transferred_key))
    stopped_key = None
    if binding_result.stopped_binding_visit_key is not None:
        stopped_key = _plain_visit_key(binding_result.stopped_binding_visit_key)
    target_key = _plain_visit_key(visit_key)
    target_visit = None
    for binding_visit in local_result.binding_rank_sequence.visits_in_binding_order:
        if _plain_visit_key(binding_visit.visit_key) == target_key:
            target_visit = binding_visit
            break
    if target_visit is None:
        return None, "", "", "missing"
    for binding_visit in local_result.binding_rank_sequence.visits_in_binding_order:
        key = _plain_visit_key(binding_visit.visit_key)
        if key in earlier:
            continue
        if key == target_key:
            return picture, binding_visit.inlink_name, binding_visit.route_next_link_name, "before_judgment"
        if key in transferred_now:
            if key not in after_by_visit:
                raise RuntimeError(
                    "Missing candidate post-transfer snapshot for "
                    f"{key!r} at virtual timestep {timestep_result.virtual_timestep}."
                )
            picture = after_by_visit[key]
            continue
        if (
            binding_result.stop_reason
            is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
            and stopped_key == key
        ):
            return (
                scan_start,
                target_visit.inlink_name,
                target_visit.route_next_link_name,
                "scan_start",
            )
    return (
        scan_start,
        target_visit.inlink_name,
        target_visit.route_next_link_name,
        "scan_start",
    )


def _traffic_observation(local_result, visit_key):
    for record in local_result.traffic_observation_records:
        if record.visit_key == visit_key:
            return record
    raise RuntimeError(f"Selected candidate has no traffic observation for {visit_key!r}.")


def _require_case_identity(case, observation, actual_route: str) -> None:
    if observation.inlink_name == "":
        raise RuntimeError(f"{case['case_id']}: traffic observation has no inlink.")
    if observation.baseline_passage_timestep != case["baseline_passage_timestep"]:
        raise RuntimeError(
            f"{case['case_id']}: Baseline P is "
            f"{observation.baseline_passage_timestep}, expected "
            f"{case['baseline_passage_timestep']}."
        )
    if observation.candidate_passage_timestep != case["candidate_passage_timestep"]:
        raise RuntimeError(
            f"{case['case_id']}: Candidate P is "
            f"{observation.candidate_passage_timestep}, expected "
            f"{case['candidate_passage_timestep']}."
        )
    if observation.route_next_link_name != case["route_next_link_name"]:
        raise RuntimeError(
            f"{case['case_id']}: predicted route is "
            f"{observation.route_next_link_name!r}."
        )
    if actual_route != case["route_next_link_name"]:
        raise RuntimeError(f"{case['case_id']}: actual route is {actual_route!r}.")


def _find_timestep_result(local_result, numeric_timestep: int):
    for timestep_result in local_result.timestep_results:
        if timestep_result.virtual_timestep == numeric_timestep:
            return timestep_result
    return None


def _values_for_side(prefix: str, state, reason: str, passed: bool, skipped: bool, stopped: bool):
    row = {}
    if state is None:
        for field_name in STATE_FIELDS:
            row[prefix + field_name] = ""
        row[prefix + "inlink_capacity_out_remain"] = ""
        row[prefix + "node_flow_capacity_remain"] = ""
        row[prefix + "outlink_capacity_in_remain"] = ""
        row[prefix + "outlink_vehicle_count"] = ""
        row[prefix + "outlink_vehicle_names_head_to_tail"] = ""
        row[prefix + "entrance_vehicle_name"] = ""
        row[prefix + "entrance_vehicle_position"] = ""
        row[prefix + "entry_gap"] = ""
        row[prefix + "last_order_control_inlink_name"] = ""
        row[prefix + "last_order_control_entry_timestep"] = ""
    else:
        for field_name in STATE_FIELDS:
            row[prefix + field_name] = state[field_name]
        row[prefix + "inlink_capacity_out_remain"] = state["inlink_capacity_out_remain"]
        row[prefix + "node_flow_capacity_remain"] = state["node_flow_capacity_remain"]
        row[prefix + "outlink_capacity_in_remain"] = state["outlink_capacity_in_remain"]
        row[prefix + "outlink_vehicle_count"] = state["outlink_vehicle_count"]
        row[prefix + "outlink_vehicle_names_head_to_tail"] = state[
            "outlink_vehicle_names_head_to_tail"
        ]
        row[prefix + "entrance_vehicle_name"] = state["entrance_vehicle_name"]
        row[prefix + "entrance_vehicle_position"] = state["entrance_vehicle_position"]
        row[prefix + "entry_gap"] = state["entry_gap"]
        row[prefix + "last_order_control_inlink_name"] = state["last_inlink_name"]
        row[prefix + "last_order_control_entry_timestep"] = state["last_entry_timestep"]
    if reason == REASON_NOT_SCANNED or reason == REASON_NOT_OBSERVABLE:
        row[prefix + "official_reason"] = reason
    else:
        row[prefix + "official_reason"] = reason
    row[prefix + "passed"] = passed
    row[prefix + "temporary_skipped"] = skipped
    row[prefix + "clearance_stopped"] = stopped
    return row


def _reason_contradicts_state(reason: str, state) -> bool:
    if state is None or reason in ("", REASON_NOT_SCANNED, REASON_NOT_OBSERVABLE):
        return False
    arrived = state["was_arrived"]
    head = state["was_inlink_physical_head"]
    clearance = state["clearance_satisfied"]
    inlink_out = state["inlink_outflow_capacity_satisfied"]
    node_flow = state["node_flow_capacity_satisfied"]
    outlink_in = state["outlink_inflow_capacity_satisfied"]
    entry = state["outlink_entry_space_available"]
    if reason == REASON_NOT_ARRIVED:
        return arrived is not False
    if reason == REASON_NOT_HEAD:
        return arrived is not True or head is not False
    if reason == REASON_CLEARANCE:
        return arrived is not True or head is not True or clearance is not False
    if reason == REASON_INLINK_OUTFLOW:
        return inlink_out is not False
    if reason == REASON_NODE_FLOW:
        return node_flow is not False
    if reason == REASON_OUTLINK_INFLOW:
        return outlink_in is not False
    if reason == REASON_ENTRY:
        return entry is not False
    if reason == REASON_PASSED:
        return (
            arrived is not True
            or head is not True
            or clearance is not True
            or inlink_out is not True
            or node_flow is not True
            or outlink_in is not True
            or entry is not True
        )
    return False


def _tuple_match(candidate_state, actual_state):
    if candidate_state is None or actual_state is None:
        return ""
    for field_name in STATE_FIELDS:
        if candidate_state[field_name] == "" or actual_state[field_name] == "":
            return ""
        if candidate_state[field_name] != actual_state[field_name]:
            return False
    return True


def _empty_state():
    state = {}
    for field_name in STATE_FIELDS:
        state[field_name] = ""
    state["inlink_capacity_out_remain"] = ""
    state["node_flow_capacity_remain"] = ""
    state["outlink_capacity_in_remain"] = ""
    state["outlink_vehicle_count"] = ""
    state["outlink_vehicle_names_head_to_tail"] = ""
    state["entrance_vehicle_name"] = ""
    state["entrance_vehicle_position"] = ""
    state["entry_gap"] = ""
    state["last_inlink_name"] = ""
    state["last_entry_timestep"] = ""
    return state


def _apply_identity_position(state, in_incoming, is_head):
    if in_incoming is False:
        state["was_arrived"] = False
    elif in_incoming is True:
        state["was_arrived"] = True
    if is_head is True or is_head is False:
        state["was_inlink_physical_head"] = is_head
    return state


def _state_from_scan_start(picture, visit_key, timestep: int):
    if picture is None:
        return None
    observations = picture.get("visit_observations", {})
    observation = observations.get(_format_visit_key(visit_key))
    if observation is None or observation.get("visit_identity_confirmed") is not True:
        return None
    state = _state_from_picture(
        picture,
        visit_key[0],
        observation["formal_inlink"],
        observation["formal_route"],
        timestep,
    )
    if state is None:
        state = _empty_state()
    return _apply_identity_position(
        state,
        observation["in_incoming"],
        observation["is_physical_head"],
    )


def _staged_capacity_comparison(candidate_state, actual_state, candidate_passed, actual_passed):
    stages = (
        ("inlink_outflow", "inlink_outflow_capacity_satisfied"),
        ("node_flow", "node_flow_capacity_satisfied"),
        ("outlink_inflow", "outlink_inflow_capacity_satisfied"),
        ("entry_space", "outlink_entry_space_available"),
    )
    for stage_name, field_name in stages:
        left = candidate_state[field_name]
        right = actual_state[field_name]
        if left == "" or right == "":
            return "not_comparable", ""
        if left is False or right is False:
            return stage_name, left == right
    return "passage", candidate_passed == actual_passed


def _staged_physical_comparison(candidate_state, actual_state, candidate_passed, actual_passed):
    if candidate_state is None or actual_state is None:
        return "not_comparable", ""
    left_arrived = candidate_state["was_arrived"]
    right_arrived = actual_state["was_arrived"]
    if left_arrived == "" or right_arrived == "":
        return "not_comparable", ""
    if left_arrived is False and right_arrived is False:
        return "arrival", True
    if left_arrived is False or right_arrived is False:
        return "arrival", False
    left_head = candidate_state["was_inlink_physical_head"]
    right_head = actual_state["was_inlink_physical_head"]
    if left_head == "" or right_head == "":
        return "not_comparable", ""
    if left_head is False or right_head is False:
        return "physical_head", left_head == right_head
    left_clearance = candidate_state["clearance_satisfied"]
    right_clearance = actual_state["clearance_satisfied"]
    if left_clearance == "" or right_clearance == "":
        return "not_comparable", ""
    if left_clearance is False or right_clearance is False:
        return "clearance", left_clearance == right_clearance
    return _staged_capacity_comparison(
        candidate_state,
        actual_state,
        candidate_passed,
        actual_passed,
    )


def _applicable_note(stage: str, candidate_state, actual_state) -> str:
    if stage in ("arrival", "physical_head", "not_comparable", ""):
        return ""
    if candidate_state is None or actual_state is None:
        return ""
    fields_by_stage = {
        "clearance": (
            "last_inlink_name",
            "last_entry_timestep",
        ),
        "inlink_outflow": (
            "last_inlink_name",
            "last_entry_timestep",
            "inlink_capacity_out_remain",
        ),
        "node_flow": (
            "last_inlink_name",
            "last_entry_timestep",
            "inlink_capacity_out_remain",
            "node_flow_capacity_remain",
        ),
        "outlink_inflow": (
            "last_inlink_name",
            "last_entry_timestep",
            "inlink_capacity_out_remain",
            "node_flow_capacity_remain",
            "outlink_capacity_in_remain",
        ),
        "entry_space": (
            "last_inlink_name",
            "last_entry_timestep",
            "inlink_capacity_out_remain",
            "node_flow_capacity_remain",
            "outlink_capacity_in_remain",
            "outlink_vehicle_count",
            "outlink_vehicle_names_head_to_tail",
            "entrance_vehicle_name",
            "entrance_vehicle_position",
            "entry_gap",
        ),
        "passage": (
            "last_inlink_name",
            "last_entry_timestep",
            "inlink_capacity_out_remain",
            "node_flow_capacity_remain",
            "outlink_capacity_in_remain",
            "outlink_vehicle_count",
            "outlink_vehicle_names_head_to_tail",
            "entrance_vehicle_name",
            "entrance_vehicle_position",
            "entry_gap",
        ),
    }
    pieces = []
    for field_name in fields_by_stage.get(stage, ()):
        if candidate_state[field_name] != actual_state[field_name]:
            pieces.append(field_name)
    if len(pieces) == 0:
        return ""
    return "applicable_observation_difference=" + ",".join(pieces)


def _semantic_status(candidate_reason, actual_reason, stage, physical_match, scan_match):
    if (
        stage == "not_comparable"
        or physical_match == ""
        or candidate_reason in ("", REASON_NOT_OBSERVABLE)
        or actual_reason in ("", REASON_NOT_OBSERVABLE)
    ):
        return SEMANTIC_NOT_COMPARABLE
    if candidate_reason == actual_reason:
        return SEMANTIC_EXACT
    if (
        physical_match is True
        and scan_match is False
        and REASON_NOT_SCANNED in (candidate_reason, actual_reason)
    ):
        return SEMANTIC_SCAN_PROCEDURE
    if candidate_reason in PHYSICAL_REASONS and actual_reason in PHYSICAL_REASONS:
        return SEMANTIC_PHYSICAL_REASON
    if physical_match is True and REASON_NOT_SCANNED in (candidate_reason, actual_reason):
        return SEMANTIC_SCAN_PROCEDURE
    return SEMANTIC_NOT_COMPARABLE


def _actual_state_for_row(case, actual, timestep: int):
    if actual is None:
        return None
    reason = actual["official_reason"]
    if reason in (REASON_NOT_SCANNED, REASON_NOT_OBSERVABLE):
        if actual.get("visit_identity_confirmed") is not True:
            return None
        state = _state_from_picture(
            actual["picture"],
            case["vehicle_name"],
            actual["inlink_name"],
            actual["route_next_link_name"],
            timestep,
        )
        if state is None:
            state = _empty_state()
        return _apply_identity_position(
            state,
            actual.get("in_incoming", ""),
            actual.get("observed_head", ""),
        )
    state = _state_from_picture(
        actual["picture"],
        case["vehicle_name"],
        actual["inlink_name"],
        actual["route_next_link_name"],
        timestep,
    )
    if actual.get("formal_not_arrived") is True and reason == REASON_NOT_ARRIVED:
        if state is None:
            state = _empty_state()
        state["was_arrived"] = False
        observed_head = actual.get("observed_head", "")
        if observed_head is True or observed_head is False:
            state["was_inlink_physical_head"] = observed_head
    return state


def _scan_fact_note(actual) -> str:
    if actual is None:
        return ""
    pieces = []
    if actual.get("in_confirmed") != "":
        pieces.append("actual_in_confirmed=" + _cell(actual.get("in_confirmed")))
    if actual.get("confirmed_position") != "":
        pieces.append(
            "actual_confirmed_position=" + _cell(actual.get("confirmed_position"))
        )
    if actual.get("assigned_rank") != "":
        pieces.append("actual_assigned_rank=" + _cell(actual.get("assigned_rank")))
    if actual.get("in_incoming") != "":
        pieces.append("actual_in_incoming=" + _cell(actual.get("in_incoming")))
    if actual.get("observed_head") != "":
        pieces.append(
            "actual_inlink_physical_head=" + _cell(actual.get("observed_head"))
        )
    return "; ".join(pieces)


def _numeric_note(candidate_state, actual_state) -> str:
    if candidate_state is None or actual_state is None:
        return ""
    pieces = []
    for field_name in (
        "inlink_capacity_out_remain",
        "node_flow_capacity_remain",
        "outlink_capacity_in_remain",
        "outlink_vehicle_count",
        "outlink_vehicle_names_head_to_tail",
        "entrance_vehicle_name",
        "entrance_vehicle_position",
        "entry_gap",
        "last_inlink_name",
        "last_entry_timestep",
    ):
        if candidate_state[field_name] != actual_state[field_name]:
            pieces.append(field_name)
    if len(pieces) == 0:
        return ""
    return "numeric_or_name_difference=" + ",".join(pieces)


def _build_visit_rows():
    rows = []
    summaries = []
    for case in CASES:
        selected = GATE.selected.get(case["decision_timestep"])
        if selected is None:
            raise RuntimeError(
                f"{case['case_id']}: selected candidate was not captured."
            )
        local_result = selected["local_result"]
        visit_key = _visit_key_of_case(case)
        observation = _traffic_observation(local_result, visit_key)
        actual_route = ""
        passage_timestep = case["actual_passage_timestep"]
        passage_judgment = GATE.actual_judgments.get((visit_key, passage_timestep))
        if passage_judgment is not None:
            actual_route = passage_judgment["route_next_link_name"]
            if passage_judgment["official_reason"] != REASON_PASSED:
                raise RuntimeError(
                    f"{case['case_id']}: actual judgment at "
                    f"{passage_timestep} is {passage_judgment['official_reason']!r}, "
                    "not passed."
                )
        _require_case_identity(case, observation, actual_route)
        physical_mismatch_count = 0
        scan_procedure_mismatch_count = 0
        exact_reason_mismatch_count = 0
        physical_reason_mismatch_count = 0
        passage_mismatch_count = 0
        comparable_physical_count = 0
        pre_arrival_count = 0
        critical_indeterminate = False
        critical_physical_reason_mismatch = False
        critical_notes = []
        suspect = False
        for numeric_timestep in range(case["timestep_start"], case["timestep_end"] + 1):
            timestep_result = _find_timestep_result(local_result, numeric_timestep)
            if timestep_result is None:
                raise RuntimeError(
                    f"{case['case_id']}: no candidate timestep result at "
                    f"{numeric_timestep}."
                )
            (
                reason,
                passed,
                skipped,
                stopped,
                candidate_reach,
                candidate_prior,
            ) = _candidate_scan_fields(
                local_result,
                timestep_result.binding_transfer_result,
                visit_key,
            )
            picture, seen_inlink, seen_route, picture_source = _picture_before_target(
                local_result,
                selected["buyers_id"],
                timestep_result,
                visit_key,
            )
            binding_inlink = observation.inlink_name
            binding_route = observation.route_next_link_name
            if seen_inlink != "":
                binding_inlink = seen_inlink
            if seen_route != "":
                binding_route = seen_route
            if picture_source == "scan_start":
                candidate_state = _state_from_scan_start(
                    picture,
                    visit_key,
                    numeric_timestep,
                )
            elif picture_source == "before_judgment":
                candidate_state = _state_from_picture(
                    picture,
                    case["vehicle_name"],
                    binding_inlink,
                    binding_route,
                    numeric_timestep,
                )
            else:
                candidate_state = None
            actual = GATE.actual_judgments.get((visit_key, numeric_timestep))
            if actual is None:
                actual_reason = REASON_NOT_OBSERVABLE
                actual_state = None
                actual_passed = False
                actual_skipped = False
                actual_stopped = False
                actual_reach = ""
                actual_prior = ""
            else:
                actual_reason = actual["official_reason"]
                actual_passed = actual["passed"]
                actual_skipped = actual["temporary_skipped"]
                actual_stopped = actual["clearance_stopped"]
                actual_reach = actual.get("scan_reach_status", "")
                actual_prior = actual.get("prior_clearance_stop_visit_key", "")
                actual_state = _actual_state_for_row(case, actual, numeric_timestep)
            if actual_reason != REASON_NOT_OBSERVABLE and _reason_contradicts_state(
                reason,
                candidate_state,
            ):
                suspect = True
            if actual_reason != REASON_NOT_OBSERVABLE and _reason_contradicts_state(
                actual_reason,
                actual_state,
            ):
                suspect = True
            if candidate_reach == "" or actual_reach == "":
                scan_match = ""
            else:
                scan_match = candidate_reach == actual_reach
            if reason == "" or actual_reason == "" or reason == REASON_NOT_OBSERVABLE or actual_reason == REASON_NOT_OBSERVABLE:
                reason_match = ""
            else:
                reason_match = reason == actual_reason
            stage, physical_match = _staged_physical_comparison(
                candidate_state,
                actual_state,
                passed,
                actual_passed,
            )
            if stage == "passage":
                passage_match = physical_match
            else:
                passage_match = ""
            semantic = _semantic_status(
                reason,
                actual_reason,
                stage,
                physical_match,
                scan_match,
            )
            if semantic == SEMANTIC_PHYSICAL_REASON and physical_match is True:
                suspect = True
            note_parts = []
            applicable_note = _applicable_note(stage, candidate_state, actual_state)
            if applicable_note != "":
                note_parts.append(applicable_note)
            scan_note = _scan_fact_note(actual)
            if scan_note != "":
                note_parts.append(scan_note)
            if (
                candidate_prior != ""
                and actual_prior != ""
                and candidate_prior != actual_prior
            ):
                note_parts.append("prior_clearance_stop_visit_key_difference")
            note = "; ".join(note_parts)
            if stage == "not_comparable" or physical_match == "":
                status = "not_comparable"
            elif physical_match is False:
                status = "physical_mismatch"
            else:
                status = "physical_match"
            if case["pre_arrival_start"] <= numeric_timestep <= case["pre_arrival_end"]:
                pre_arrival_count += 1
            if physical_match is True or physical_match is False:
                comparable_physical_count += 1
            if physical_match is False:
                physical_mismatch_count += 1
            if scan_match is False:
                scan_procedure_mismatch_count += 1
            if reason_match is False:
                exact_reason_mismatch_count += 1
            if semantic == SEMANTIC_PHYSICAL_REASON:
                physical_reason_mismatch_count += 1
            if passage_match is False:
                passage_mismatch_count += 1
            in_critical = case["critical_start"] <= numeric_timestep <= case["critical_end"]
            if in_critical:
                if stage == "not_comparable" or physical_match == "" or semantic == SEMANTIC_NOT_COMPARABLE:
                    if not (
                        stage == "arrival"
                        and physical_match is True
                        and semantic == SEMANTIC_SCAN_PROCEDURE
                    ):
                        critical_indeterminate = True
                if semantic == SEMANTIC_PHYSICAL_REASON:
                    critical_physical_reason_mismatch = True
                if numeric_timestep == case["actual_passage_timestep"] and (
                    stage != "passage" or physical_match is not True or semantic != SEMANTIC_EXACT
                ):
                    if physical_match is not False:
                        critical_indeterminate = True
                critical_notes.append(
                    "T="
                    + str(numeric_timestep)
                    + ":"
                    + stage
                    + ":"
                    + semantic
                )
            row = {
                "case_id": case["case_id"],
                "decision_timestep": case["decision_timestep"],
                "node_name": case["node_name"],
                "vehicle_name": case["vehicle_name"],
                "visit_id": case["visit_id"],
                "role": case["role"],
                "numeric_timestep": numeric_timestep,
                "candidate_virtual_timestep": timestep_result.virtual_timestep,
                "actual_real_timestep": numeric_timestep,
                "inlink_name": observation.inlink_name,
                "candidate_route_next_link_name": observation.route_next_link_name,
                "actual_route_next_link_name": actual_route,
                "baseline_passage_timestep": observation.baseline_passage_timestep,
                "candidate_passage_timestep": observation.candidate_passage_timestep,
                "actual_passage_timestep": case["actual_passage_timestep"],
            }
            row.update(
                _values_for_side(
                    "candidate_",
                    candidate_state,
                    reason,
                    passed,
                    skipped,
                    stopped,
                )
            )
            row.update(
                _values_for_side(
                    "actual_",
                    actual_state,
                    actual_reason,
                    actual_passed,
                    actual_skipped,
                    actual_stopped,
                )
            )
            row["candidate_scan_reach_status"] = candidate_reach
            row["candidate_prior_clearance_stop_visit_key"] = candidate_prior
            row["actual_scan_reach_status"] = actual_reach
            row["actual_prior_clearance_stop_visit_key"] = actual_prior
            row["state_tuple_match"] = physical_match
            row["official_reason_match"] = reason_match
            row["passage_flag_match"] = passage_match
            row["scan_reach_status_match"] = scan_match
            row["physical_comparison_stage"] = stage
            row["physical_state_match"] = physical_match
            row["scan_procedure_match"] = scan_match
            row["official_reason_semantic_status"] = semantic
            row["row_comparison_status"] = status
            row["comparison_note"] = note
            rows.append(row)
        if (
            observation.candidate_passage_timestep
            != case["actual_passage_timestep"]
        ):
            suspect = True
        if suspect:
            classification = CLASS_INCONSISTENCY
        elif critical_indeterminate:
            classification = CLASS_INDETERMINATE
        elif (
            physical_mismatch_count > 0
            or passage_mismatch_count > 0
            or critical_physical_reason_mismatch
        ):
            classification = CLASS_TIMING_PHYSICAL_DIFFERENCE
        elif comparable_physical_count != (
            case["timestep_end"] - case["timestep_start"] + 1
        ):
            classification = CLASS_INDETERMINATE
        else:
            classification = CLASS_STRONG_PHYSICAL
        summaries.append(
            {
                "case": case,
                "candidate_p": observation.candidate_passage_timestep,
                "actual_p": case["actual_passage_timestep"],
                "timestep_count": case["timestep_end"] - case["timestep_start"] + 1,
                "pre_arrival_count": pre_arrival_count,
                "comparable_physical_count": comparable_physical_count,
                "physical_mismatch_count": physical_mismatch_count,
                "scan_procedure_mismatch_count": scan_procedure_mismatch_count,
                "exact_reason_mismatch_count": exact_reason_mismatch_count,
                "physical_reason_mismatch_count": physical_reason_mismatch_count,
                "passage_mismatch_count": passage_mismatch_count,
                "critical_result": " ".join(critical_notes),
                "classification": classification,
            }
        )
    return rows, summaries


def _boundary_link_result(timestep_result):
    for link_result in timestep_result.outlink_boundary_result.outlink_results:
        if link_result.outlink_name == TARGET_OUTLINK:
            return link_result
    return None


def _build_boundary_rows():
    rows = []
    for case in CASES:
        selected = GATE.selected[case["decision_timestep"]]
        local_result = selected["local_result"]
        for numeric_timestep in range(case["timestep_start"], case["timestep_end"] + 1):
            timestep_result = _find_timestep_result(local_result, numeric_timestep)
            link_result = None
            if timestep_result is not None:
                link_result = _boundary_link_result(timestep_result)
            before = GATE.actual_outlink_before.get(numeric_timestep)
            exits = GATE.downstream_exits.get(numeric_timestep)
            note_parts = []
            if link_result is None:
                note_parts.append("candidate boundary result missing")
            if GATE.downstream_ran.get(numeric_timestep) is not True:
                note_parts.append("actual downstream transfer was not observed")
            if exits is not None and len(exits) == 0:
                note_parts.append("no vehicle left the outlink at the terminal node")
            entrance_available = ""
            vehicle_count = ""
            vehicle_names = ""
            if before is not None:
                vehicle_count = len(before["vehicle_names"])
                vehicle_names = _join_names(before["vehicle_names"])
                entrance_available = _entry_available(before)
            row = {
                "case_id": case["case_id"],
                "decision_timestep": case["decision_timestep"],
                "numeric_timestep": numeric_timestep,
                "candidate_virtual_timestep": numeric_timestep,
                "actual_real_timestep": numeric_timestep,
                "outlink_name": TARGET_OUTLINK,
                "comparison_phase": COMPARISON_PHASE,
                "candidate_boundary_mode": "",
                "candidate_flow_allowance_before": "",
                "candidate_flow_allowance_added": "",
                "candidate_flow_allowance_after": "",
                "candidate_vehicle_names_at_end_before": "",
                "candidate_observed_outflow_exit_vehicle_names": "",
                "candidate_constrained_sink_exit_vehicle_names": "",
                "candidate_waiting_vehicle_names_after": "",
                "candidate_capacity_out_remain_before": "",
                "candidate_capacity_out_remain_after": "",
                "candidate_terminal_node_flow_capacity_before": "",
                "candidate_terminal_node_flow_capacity_after": "",
                "actual_downstream_exit_vehicle_names": _join_names(exits),
                "actual_outlink_vehicle_count_before_target_passage": vehicle_count,
                "actual_outlink_vehicle_names_head_to_tail_before_target_passage": vehicle_names,
                "actual_entrance_space_available_before_target_passage": entrance_available,
                "boundary_comparison_note": "; ".join(note_parts),
            }
            if link_result is not None:
                row["candidate_boundary_mode"] = link_result.boundary_mode.value
                row["candidate_flow_allowance_before"] = link_result.flow_allowance_before
                row["candidate_flow_allowance_added"] = link_result.flow_allowance_added
                row["candidate_flow_allowance_after"] = link_result.flow_allowance_after
                row["candidate_vehicle_names_at_end_before"] = _join_names(
                    link_result.vehicle_names_at_end_before
                )
                row["candidate_observed_outflow_exit_vehicle_names"] = _join_names(
                    link_result.observed_outflow_boundary_exit_vehicle_names
                )
                row["candidate_constrained_sink_exit_vehicle_names"] = _join_names(
                    link_result.constrained_sink_end_trip_vehicle_names
                )
                row["candidate_waiting_vehicle_names_after"] = _join_names(
                    link_result.waiting_vehicle_names_after
                )
                row["candidate_capacity_out_remain_before"] = (
                    link_result.capacity_out_remain_before
                )
                row["candidate_capacity_out_remain_after"] = (
                    link_result.capacity_out_remain_after
                )
                row["candidate_terminal_node_flow_capacity_before"] = (
                    link_result.terminal_node_flow_capacity_remain_before
                )
                row["candidate_terminal_node_flow_capacity_after"] = (
                    link_result.terminal_node_flow_capacity_remain_after
                )
            rows.append(row)
    return rows


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            output = {}
            for column in columns:
                output[column] = _cell(row.get(column, ""))
            writer.writerow(output)


def _require_fresh_output_directory() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists and will not be overwritten: {OUTPUT_DIR}."
        )
    parent = OUTPUT_DIR.parent
    if not parent.exists():
        raise RuntimeError(f"Output parent directory does not exist: {parent}.")
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)


def _print_summaries(summaries) -> None:
    for summary in summaries:
        case = summary["case"]
        print(f"case_id={case['case_id']}")
        print(f"Candidate P={summary['candidate_p']}")
        print(f"Actual P={summary['actual_p']}")
        print(f"全時刻数={summary['timestep_count']}")
        print(f"到着前時刻数={summary['pre_arrival_count']}")
        print(f"物理状態比較可能時刻数={summary['comparable_physical_count']}")
        print(f"physical state mismatch数={summary['physical_mismatch_count']}")
        print(f"scan procedure mismatch数={summary['scan_procedure_mismatch_count']}")
        print(f"exact official reason mismatch数={summary['exact_reason_mismatch_count']}")
        print(f"physical official reason mismatch数={summary['physical_reason_mismatch_count']}")
        print(f"passage flag mismatch数={summary['passage_mismatch_count']}")
        print(f"通過直前期間の結果={summary['critical_result']}")
        print(f"最終分類={summary['classification']}")
        print(f"visit_csv={OUTPUT_DIR / VISIT_CSV_NAME}")
        print(f"boundary_csv={OUTPUT_DIR / BOUNDARY_CSV_NAME}")


def main() -> int:
    _require_fresh_output_directory()
    original_recursion_limit = sys.getrecursionlimit()
    world = None
    try:
        if original_recursion_limit < extended_trial.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(extended_trial.WORLD_COPY_RECURSION_LIMIT)
        vot_rng = np.random.default_rng(extended_trial.VOT_SEED)
        vot_values = extended_trial.generate_vehicle_vots(
            vot_rng,
            len(extended_trial.VEHICLE_SPECS),
        )
        vot_records = extended_trial.build_vehicle_vot_records(
            extended_trial.VEHICLE_SPECS,
            vot_values,
        )
        world = extended_trial.build_world_and_network()
        extended_trial.add_vehicles_to_world(
            world,
            extended_trial.VEHICLE_SPECS,
            vot_records,
        )
        world.finalize_scenario()
        GATE.real_world = world
        install_observation_hooks()
        install_driver_hook()
        try:
            world.exec_simulation()
        finally:
            restore_driver_hook()
            restore_observation_hooks()
            GATE.real_world = None
        visit_rows, summaries = _build_visit_rows()
        boundary_rows = _build_boundary_rows()
        _write_csv(OUTPUT_DIR / VISIT_CSV_NAME, VISIT_COLUMNS, visit_rows)
        _write_csv(OUTPUT_DIR / BOUNDARY_CSV_NAME, BOUNDARY_COLUMNS, boundary_rows)
        expected_names = {VISIT_CSV_NAME, BOUNDARY_CSV_NAME}
        for path in OUTPUT_DIR.iterdir():
            if path.name not in expected_names:
                raise RuntimeError(f"Unexpected file in output directory: {path.name}.")
        _print_summaries(summaries)
    finally:
        restore_driver_hook()
        restore_observation_hooks()
        if original_recursion_limit != sys.getrecursionlimit():
            sys.setrecursionlimit(original_recursion_limit)
    return 0


def _function_by_name(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Missing function {name}.")


def _call_linenos(function: ast.FunctionDef, name: str):
    lines = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        called = node.func
        if isinstance(called, ast.Name) and called.id == name:
            lines.append(node.lineno)
        elif isinstance(called, ast.Attribute) and called.attr == name:
            lines.append(node.lineno)
    return lines


def _call_count(function: ast.FunctionDef, attribute_name: str) -> int:
    count = 0
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        called = node.func
        if isinstance(called, ast.Attribute) and called.attr == attribute_name:
            count += 1
    return count


def _source_segment(source: str, function: ast.FunctionDef) -> str:
    return ast.get_source_segment(source, function) or ""


def _assert_original_once(tree: ast.Module, function_name: str, original_name: str) -> None:
    function = _function_by_name(tree, function_name)
    if _call_count(function, original_name) != 1:
        raise RuntimeError(
            f"{function_name} must call {original_name} exactly once."
        )
    if any(isinstance(node, ast.Try) for node in ast.walk(function)):
        if function_name in (
            "wrapped_candidate_transfer",
            "wrapped_actual_transfer",
            "wrapped_node_transfer",
        ):
            raise RuntimeError(
                f"{function_name} must not record passed from a try/finally."
            )


def _run_static_validation() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    if len(CASES) != 2:
        raise RuntimeError("The diagnostic must contain exactly two cases.")
    buyer = CASES[0]
    seller = CASES[1]
    if buyer["decision_timestep"] != 60 or buyer["role"] != "buyer":
        raise RuntimeError("Case 1 must be the T=60 buyer.")
    if buyer["vehicle_name"] != "veh_ee_10" or buyer["visit_id"] != 1:
        raise RuntimeError("Case 1 VisitKey must be veh_ee_10:1.")
    if (
        buyer["baseline_passage_timestep"] != 80
        or buyer["candidate_passage_timestep"] != 73
        or buyer["actual_passage_timestep"] != 73
        or buyer["route_next_link_name"] != TARGET_OUTLINK
    ):
        raise RuntimeError("Case 1 passage contract does not match.")
    if seller["decision_timestep"] != 135 or seller["role"] != "seller":
        raise RuntimeError("Case 2 must be the T=135 seller.")
    if seller["vehicle_name"] != "veh_ee_19" or seller["visit_id"] != 1:
        raise RuntimeError("Case 2 VisitKey must be veh_ee_19:1.")
    if (
        seller["baseline_passage_timestep"] != 149
        or seller["candidate_passage_timestep"] != 155
        or seller["actual_passage_timestep"] != 155
        or seller["route_next_link_name"] != TARGET_OUTLINK
    ):
        raise RuntimeError("Case 2 passage contract does not match.")
    if VISIT_CSV_NAME not in source or BOUNDARY_CSV_NAME not in source:
        raise RuntimeError("Both CSV names must be present.")
    for column in VISIT_COLUMNS:
        if column not in source:
            raise RuntimeError(f"Visit column missing from source: {column}.")
    for column in BOUNDARY_COLUMNS:
        if column not in source:
            raise RuntimeError(f"Boundary column missing from source: {column}.")
    if "candidate_virtual_timestep" not in VISIT_COLUMNS:
        raise RuntimeError("Candidate virtual timestep must be its own field.")
    if "actual_real_timestep" not in VISIT_COLUMNS:
        raise RuntimeError("Actual real timestep must be its own field.")
    if COMPARISON_PHASE != "not_equivalent":
        raise RuntimeError("Boundary comparison phase must be not_equivalent.")
    if "strong_physical_match" not in source:
        raise RuntimeError("The strong physical match class is missing.")
    writer = _function_by_name(tree, "_write_csv")
    writer_source = _source_segment(source, writer)
    if "writeheader" not in writer_source:
        raise RuntimeError("CSV writer must write a header for zero rows.")
    directory_source = _source_segment(source, _function_by_name(tree, "_require_fresh_output_directory"))
    if "already exists" not in directory_source:
        raise RuntimeError("Existing output directory must stop the diagnostic.")
    reason_source = _source_segment(source, _function_by_name(tree, "_candidate_reason"))
    if "binding_result" not in reason_source:
        raise RuntimeError("Candidate official reason must come from the binding result.")
    if "capacity_out_remain" in reason_source:
        raise RuntimeError("Candidate official reason must not be recomputed from capacity.")
    shortage = _function_by_name(tree, "wrapped_shortage")
    if _call_count(shortage, "original_shortage") != 1:
        raise RuntimeError("Shortage wrapper must call production once.")
    shortage_source = _source_segment(source, shortage)
    if "official_reason=result" not in shortage_source:
        raise RuntimeError("Actual shortage reason must be the production return value.")
    for function_name, original_name in (
        ("wrapped_binding_scan", "original_binding_scan"),
        ("wrapped_candidate_transfer", "original_candidate_transfer"),
        ("wrapped_try_confirmed", "original_try_confirmed"),
        ("wrapped_head_skip", "original_head_skip"),
        ("wrapped_clearance", "original_clearance"),
        ("wrapped_shortage", "original_shortage"),
        ("wrapped_actual_transfer", "original_actual_transfer"),
        ("wrapped_node_transfer", "original_node_transfer"),
        ("wrapped_driver", "original_driver"),
        ("wrapped_world_copy", "original_world_copy"),
    ):
        _assert_original_once(tree, function_name, original_name)
    actual_transfer = _source_segment(source, _function_by_name(tree, "wrapped_actual_transfer"))
    if "order_control_current_visit" in actual_transfer:
        raise RuntimeError(
            "Actual passed recording must not read the current visit after production."
        )
    if "candidate_passage_timestep" in actual_transfer:
        raise RuntimeError("Actual transfer must not read Candidate P.")
    identity = _source_segment(
        source,
        _function_by_name(tree, "_passage_identity_before_actual_transfer"),
    )
    if "order_control_current_visit" not in identity:
        raise RuntimeError("Actual VisitKey must be saved before production transfer.")
    copy_source = _source_segment(source, _function_by_name(tree, "wrapped_world_copy"))
    if "original_world_copy" not in copy_source:
        raise RuntimeError("World.copy wrapper must call the saved production copy.")
    if ".random(" in copy_source:
        raise RuntimeError("World.copy wrapper must not consume a random number.")
    main_function = _function_by_name(tree, "main")
    main_source = _source_segment(source, main_function)
    if "exec_simulation" not in main_source:
        raise RuntimeError("The simulation entry must remain available for a later run.")
    if "restore_observation_hooks" not in main_source or "finally" not in main_source:
        raise RuntimeError("Hooks must be restored in finally.")
    static_function = _function_by_name(tree, "_run_static_validation")
    if _call_count(static_function, "exec_simulation") != 0:
        raise RuntimeError("Static validation must not start the simulation.")
    build_source = _source_segment(source, _function_by_name(tree, "_build_visit_rows"))
    for class_name in (
        "CLASS_STRONG_PHYSICAL",
        "CLASS_TIMING_PHYSICAL_DIFFERENCE",
        "CLASS_INCONSISTENCY",
        "CLASS_INDETERMINATE",
    ):
        if class_name not in build_source:
            raise RuntimeError(f"Visit comparison is missing {class_name}.")
    if build_source.find("physical_mismatch_count > 0") > build_source.find("CLASS_STRONG_PHYSICAL"):
        raise RuntimeError("Candidate P equality alone must not select strong_physical_match.")
    boundary_source = _source_segment(source, _function_by_name(tree, "_build_boundary_rows"))
    if "COMPARISON_PHASE" not in boundary_source:
        raise RuntimeError("Boundary rows must use the fixed not_equivalent phase.")
    if "strong_physical_match" in boundary_source:
        raise RuntimeError("Boundary comparison must not decide the strong-match class.")
    install_source = _source_segment(source, _function_by_name(tree, "install_observation_hooks"))
    if "virtual_calculation_module" not in install_source:
        raise RuntimeError(
            "The candidate scan hook must patch the virtual-calculation binding."
        )
    if Path(__file__).name != "diagnose_tvt_mp_candidate_actual_physical_reason_comparison.py":
        raise RuntimeError("Static validation ran against an unexpected module.")
    for column_name in (
        "candidate_scan_reach_status",
        "actual_scan_reach_status",
        "candidate_prior_clearance_stop_visit_key",
        "actual_prior_clearance_stop_visit_key",
        "scan_reach_status_match",
    ):
        if column_name not in VISIT_COLUMNS:
            raise RuntimeError(f"Visit comparison is missing {column_name}.")
    if column_name in BOUNDARY_COLUMNS:
        raise RuntimeError("Boundary comparison columns must stay unchanged.")
    try_confirmed = _function_by_name(tree, "wrapped_try_confirmed")
    save_lines = _call_linenos(try_confirmed, "_save_confirmed_visit_positions_before_production")
    original_lines = _call_linenos(try_confirmed, "original_try_confirmed")
    finalize_lines = _call_linenos(try_confirmed, "_finalize_actual_scan_reach")
    if len(save_lines) != 1 or len(original_lines) != 1 or len(finalize_lines) != 1:
        raise RuntimeError("Confirmed scan positions must be saved once and finalized once.")
    if not (save_lines[0] < original_lines[0] < finalize_lines[0]):
        raise RuntimeError(
            "Confirmed VisitKey positions must be saved before production and "
            "scan reach finalized only after it returns."
        )
    for node in ast.walk(try_confirmed):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call):
                raise RuntimeError(
                    "A failed confirmed scan must not record success or agreement."
                )
    clearance_source = _source_segment(source, _function_by_name(tree, "wrapped_clearance"))
    if "actual_clearance_stops" not in clearance_source or "result is True" not in clearance_source:
        raise RuntimeError(
            "Prior clearance stop must come from the production clearance return."
        )
    observation_source = _source_segment(
        source,
        _function_by_name(tree, "_formal_target_visit_observation"),
    )
    if "confirmed_candidates" in observation_source:
        raise RuntimeError(
            "Actual arrival must not be inferred from confirmed-candidate membership."
        )
    reach_source = _source_segment(source, _function_by_name(tree, "_reach_decision"))
    if "if formal_not_arrived is True" not in reach_source:
        raise RuntimeError(
            "Actual not-arrived requires the visit identity observation."
        )
    unexplained_prefix = reach_source.split("SCAN_UNEXPLAINED")[0]
    if "REASON_NOT_OBSERVABLE" not in unexplained_prefix[-120:]:
        raise RuntimeError("unexplained_not_reached must stay not_observable.")
    if "REASON_NOT_SCANNED" in unexplained_prefix[-120:]:
        raise RuntimeError(
            "unexplained_not_reached must not be rewritten as not_scanned."
        )
    candidate_scan_source = _source_segment(
        source,
        _function_by_name(tree, "_candidate_scan_fields"),
    )
    if "stopped_binding_visit_key" not in candidate_scan_source:
        raise RuntimeError(
            "Candidate prior clearance stop must come from the frozen binding result."
        )
    if "CLEARANCE_NOT_SATISFIED" not in candidate_scan_source:
        raise RuntimeError(
            "Candidate prior clearance stop must use the frozen clearance stop reason."
        )
    if "strong_physical_match" in boundary_source or "scan_reach_status" in boundary_source:
        raise RuntimeError("Boundary comparison must not decide the strong-match class.")
    if buyer["critical_start"] != 73 or buyer["critical_end"] != 73:
        raise RuntimeError("Buyer passage timestep must be the critical comparison.")
    if buyer["pre_arrival_start"] != 60 or buyer["pre_arrival_end"] != 72:
        raise RuntimeError("Buyer pre-arrival window must be T=60-72.")
    if seller["critical_start"] != 153 or seller["critical_end"] != 155:
        raise RuntimeError("Seller critical window must be T=153-155.")
    if seller["pre_arrival_start"] != 135 or seller["pre_arrival_end"] != 152:
        raise RuntimeError("Seller pre-arrival window must be T=135-152.")
    staged_source = _source_segment(source, _function_by_name(tree, "_staged_physical_comparison"))
    if 'return "arrival", True' not in staged_source:
        raise RuntimeError("Both-unarrived comparison must stop at arrival.")
    if "inlink_outflow_capacity_satisfied" in staged_source or "outlink_entry_space_available" in staged_source:
        raise RuntimeError("Unarrived comparison must not use capacity or entry space.")
    if staged_source.find('return "physical_head"') > staged_source.find("clearance_satisfied"):
        raise RuntimeError("Physical head must be compared before clearance.")
    if staged_source.find('return "clearance"') > staged_source.find("_staged_capacity_comparison"):
        raise RuntimeError("Clearance must be compared before capacity.")
    if "scan_reach" in staged_source:
        raise RuntimeError("Scan procedure must not decide physical state match.")
    capacity_source = _source_segment(source, _function_by_name(tree, "_staged_capacity_comparison"))
    capacity_names = (
        "inlink_outflow_capacity_satisfied",
        "node_flow_capacity_satisfied",
        "outlink_inflow_capacity_satisfied",
        "outlink_entry_space_available",
    )
    capacity_positions = []
    for capacity_name in capacity_names:
        capacity_positions.append(capacity_source.find(capacity_name))
    if capacity_positions != sorted(capacity_positions) or min(capacity_positions) < 0:
        raise RuntimeError("Capacity stages must follow production order.")
    if capacity_source.find('return "passage"') < capacity_positions[-1]:
        raise RuntimeError("Passage is compared only after entry space.")
    if "visit_observations" not in _source_segment(source, _function_by_name(tree, "_state_from_scan_start")):
        raise RuntimeError("Candidate scan-start must supply the target visit state.")
    if '"scan_start"' not in _source_segment(source, _function_by_name(tree, "_picture_before_target")):
        raise RuntimeError("A prior clearance stop must keep the scan-start snapshot.")
    if "_state_from" in reason_source or "visit_observations" in reason_source:
        raise RuntimeError("Candidate official reason must not be recomputed from a snapshot.")
    for column_name in (
        "physical_comparison_stage",
        "physical_state_match",
        "scan_procedure_match",
        "official_reason_semantic_status",
    ):
        if column_name not in VISIT_COLUMNS:
            raise RuntimeError(f"Visit comparison is missing {column_name}.")
    if "state_tuple_match" not in VISIT_COLUMNS or "physical_state_match" not in build_source:
        raise RuntimeError("state_tuple_match must remain as the staged physical match.")
    print("Static contract validation passed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        _run_static_validation()
    else:
        raise SystemExit(main())
