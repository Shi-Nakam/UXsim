"""
Read-only paired trace of the T=600 northeast candidate local World and the
real World from T=600 through T=610.

Official phases are common_origin and after_timestep. before_node_passage
and after_node_passage stay in the CSV as reference rows only.
The selected candidate is kept after the driver returns. Other candidates
are not written. This script does not rerun the candidate calculation and
does not fix the buyer route.
"""

from __future__ import annotations

import ast
import csv
import datetime
import json
import numbers
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import uxsim.order_control_tvt_mp_candidate_local_virtual_calculation as local_calc_module
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.order_control_tvt_mp_local_virtual_calculation_set as local_set_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
)
from uxsim.order_control_tvt_mp_research_output import build_tvt_mp_research_output
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState

import run_tvt_mp_four_cross_intersections_grid_medium_all_participating_trial as four_cross_trial


SCENARIO_NAME = four_cross_trial.SCENARIO_NAME
DIAGNOSTIC_SCRIPT_NAME = SCRIPT_PATH.name
OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900_timestep_seed_1_t600_candidate_actual_paired_trace"
    )
)

VEHICLE_CSV = "paired_vehicle_snapshots.csv"
NODE_CSV = "paired_node_snapshots.csv"
LINK_CSV = "paired_link_snapshots.csv"
PASSAGE_CSV = "paired_passage_events.csv"
DECISION_CSV = "paired_decision_events.csv"
DIFFERENCE_CSV = "paired_differences.csv"
SUMMARY_NAME = "first_divergence_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    VEHICLE_CSV,
    NODE_CSV,
    LINK_CSV,
    PASSAGE_CSV,
    DECISION_CSV,
    DIFFERENCE_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)

TARGET_NODE_NAME = "northeast_intersection"
DECISION_TIMESTEP = 600
TRACE_START = 600
TRACE_END = 610
CANDIDATE_REQUIRED_END = 608
EXPECTED_WORLD_T = 900
EXPECTED_EVALUATION_INDEX = 1
ABSOLUTE_TOLERANCE = 1e-9

PHASE_COMMON_ORIGIN = "common_origin"
PHASE_BEFORE = "before_node_passage"
PHASE_AFTER_PASSAGE = "after_node_passage"
PHASE_AFTER_TIMESTEP = "after_timestep"
PHASE_AFTER_ADVANCE = PHASE_AFTER_TIMESTEP
REFERENCE_PHASES = (PHASE_BEFORE, PHASE_AFTER_PASSAGE)
COMPARABLE_COMMON = "comparable_common_origin"
COMPARABLE_AFTER = "comparable_after_timestep"
NONCOMPARABLE = "non_comparable_intermediate"

BUYER_NAME = "veh_ne_wn_base_034"
BUYER_VISIT_ID = 1
SELLER_NAME = "veh_wn_en_base_042"
SELLER_VISIT_ID = 2
BUYER_VISIT = (BUYER_NAME, BUYER_VISIT_ID)
SELLER_VISIT = (SELLER_NAME, SELLER_VISIT_ID)
BUYER_PREDICTED_ROUTE = "northeast_intersection_to_southeast_intersection"
BUYER_ACTUAL_ROUTE = "northeast_intersection_to_northwest_intersection"
SELLER_ROUTE = "northeast_intersection_to_east_north_od"
BUYER_CANDIDATE_PASSAGE = 606
BUYER_ACTUAL_PASSAGE = 607
SELLER_CANDIDATE_PASSAGE = 608
SELLER_ACTUAL_PASSAGE = 609
BUYER_ASSIGNED_RANK = 208
SELLER_ASSIGNED_RANK = 209
BUYER_ACTUAL_RANK = 208
SELLER_ACTUAL_RANK = 209

WORLD_CANDIDATE = "candidate"
WORLD_ACTUAL = "actual"


class _Bucket:
    def __init__(self) -> None:
        self.evaluation_index = None
        self.local_world_id = None
        self.result_id = None
        self.buyers_sorted = None
        self.candidate_identity = None
        self.real_id_by_name = {}
        self.local_name_by_real_name = {}
        self.binding_by_visit = {}
        self.common_origin_captured = False
        self.vehicle_rows = []
        self.node_rows = []
        self.link_rows = []
        self.passage_rows = []


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_run = None
        self.original_one = None
        self.original_scan = None
        self.original_advance = None
        self.original_driver = None
        self.original_transfer = None
        self.original_move = None
        self.original_build = None
        self.next_evaluation_index = 0
        self.common_origin_actual_vehicle_raw = []
        self.common_origin_actual_node_raw = []
        self.common_origin_actual_link_raw = []
        self.common_origin_actual_capture_count = 0
        self.common_origin_compared_vehicle_count = 0
        self.common_origin_compared_node_count = 0
        self.common_origin_compared_link_count = 0
        self.compared_after_timesteps = []
        self.buckets_by_world_id = {}
        self.selected_bucket = None
        self.actual_vehicle_rows = []
        self.actual_node_rows = []
        self.actual_link_rows = []
        self.actual_passage_rows = []
        self.decision_rows = []
        self.difference_rows = []
        self.first_divergence = None
        self.expected_initial_rows = []
        self.unexpected_initial_rows = []
        self.unexpected_common_origin_rows = []


GATE = _Gate()


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        if value is True:
            return "True"
        return "False"
    return str(value)


def _visit_text(vehicle_name, visit_id) -> str:
    return f"{vehicle_name}:{visit_id}"


def _enum_name(value):
    if value is None:
        return None
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    return str(value)


def _link_name(link):
    if link is None:
        return None
    return getattr(link, "name", None)


def _read_route_next_link(vehicle):
    return getattr(vehicle, "route_next_link", None)


def _plain_visit(vehicle):
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        return None
    vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str):
        return None
    return (vehicle_name, visit_id)


def _entry_open(link, world):
    if link is None or world is None:
        return None
    vehicles = getattr(link, "vehicles", None)
    if vehicles is None:
        return None
    lane_count = getattr(link, "number_of_lanes", None)
    if type(lane_count) is not int:
        return None
    if len(vehicles) < lane_count:
        return True
    entrance_vehicle = vehicles[-lane_count]
    delta = getattr(link, "delta_per_lane", None)
    deltan = getattr(world, "DELTAN", None)
    if delta is None or deltan is None:
        return None
    if entrance_vehicle.x <= delta * deltan:
        return False
    return True


def _entrance_name(link):
    if link is None:
        return None
    vehicles = getattr(link, "vehicles", None)
    lane_count = getattr(link, "number_of_lanes", None)
    if vehicles is None or type(lane_count) is not int:
        return None
    if len(vehicles) < lane_count:
        return None
    return getattr(vehicles[-lane_count], "name", None)


def _latest_cum(series):
    if series is None:
        return None
    if len(series) == 0:
        return None
    return series[-1]


def _physical_index(link, vehicle):
    if link is None:
        return None
    vehicles = getattr(link, "vehicles", None)
    if vehicles is None:
        return None
    index = 0
    for current in vehicles:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _incoming_index(node, vehicle):
    incoming = getattr(node, "incoming_vehicles", None)
    if incoming is None:
        return None
    index = 0
    for current in incoming:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _rank_state(world):
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return None
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return None
    return rank_state


def _assigned_rank(world, visit_pair):
    if visit_pair is None or world is None:
        return None
    rank_state = _rank_state(world)
    if rank_state is None:
        return None
    return rank_state.assigned_rank(visit_pair)


def _formal_route(world, visit_pair):
    if visit_pair is None or world is None:
        return None
    rank_state = _rank_state(world)
    if rank_state is None:
        return None
    return rank_state.formal_route_next_link_name(visit_pair)


def _clearance_satisfied(node, inlink):
    """Read the same clearance inputs production uses. Do not call production."""
    if node is None or inlink is None:
        return None
    last_inlink = node.last_order_control_inlink
    last_timestep = node.last_order_control_entry_timestep
    if (last_inlink is None) != (last_timestep is None):
        return None
    if last_inlink is None:
        return True
    if inlink is last_inlink:
        return True
    if type(node.W.T) is not int or type(last_timestep) is not int:
        return None
    gap = node.W.T - last_timestep
    return gap > node.order_control_clearance_timesteps


def _named_link(node, link_name):
    if node is None or link_name is None:
        return None
    outlinks = getattr(node, "outlinks", None)
    if not isinstance(outlinks, dict):
        return None
    return outlinks.get(link_name)


def _is_real_target_node(node) -> bool:
    if GATE.real_world is None or node is None:
        return False
    if node.W is not GATE.real_world:
        return False
    if getattr(node.W, "_order_control_baseline_collector", None) is not None:
        return False
    if node.name != TARGET_NODE_NAME:
        return False
    timestep = node.W.T
    if type(timestep) is not int:
        return False
    if timestep < TRACE_START or timestep > TRACE_END:
        return False
    return True


def _is_target_local_state(local_state) -> bool:
    if local_state is None or GATE.real_world is None:
        return False
    if local_state.target_node_name != TARGET_NODE_NAME:
        return False
    if local_state.real_world_timestep_T != DECISION_TIMESTEP:
        return False
    if local_state.local_world is GATE.real_world:
        return False
    if GATE.real_world.T != DECISION_TIMESTEP:
        return False
    return True


def _should_trace_local(local_state, timestep) -> bool:
    if _is_target_local_state(local_state) is not True:
        return False
    if type(timestep) is not int:
        return False
    if timestep < TRACE_START or timestep > TRACE_END:
        return False
    return True


def _identity_text(evaluation_index, buyers_sorted) -> str:
    parts = []
    for visit_key in buyers_sorted:
        parts.append(_visit_text(visit_key[0], visit_key[1]))
    joined = "|".join(parts)
    return (
        f"T={DECISION_TIMESTEP}|{TARGET_NODE_NAME}|index={evaluation_index}|{joined}"
    )


def _copy_binding(local_state) -> dict:
    copied = {}
    sequence = local_state.binding_rank_sequence
    for visit in sequence.visits_in_binding_order:
        visit_key = visit.visit_key
        text = _visit_text(visit_key[0], visit_key[1])
        copied[text] = {
            "visit_key": text,
            "vehicle_name": visit_key[0],
            "visit_id": visit_key[1],
            "trade_role": _enum_name(visit.trade_role),
            "binding_partition": _enum_name(visit.binding_partition),
            "binding_rank": visit.binding_rank,
            "route_next_link_name": visit.route_next_link_name,
            "route_origin": _enum_name(visit.route_origin),
            "inlink_name": visit.inlink_name,
            "baseline_arrival_timestep": visit.baseline_arrival_timestep,
            "arrival_tiebreaker": visit.arrival_tiebreaker,
        }
    return copied


def _bucket_for(local_state) -> _Bucket:
    world_id = id(local_state.local_world)
    bucket = GATE.buckets_by_world_id.get(world_id)
    if bucket is not None:
        return bucket
    GATE.next_evaluation_index = GATE.next_evaluation_index + 1
    bucket = _Bucket()
    bucket.evaluation_index = GATE.next_evaluation_index
    bucket.local_world_id = world_id
    buyers = tuple(
        local_state.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    bucket.buyers_sorted = buyers
    bucket.candidate_identity = _identity_text(bucket.evaluation_index, buyers)
    for local_name, real_name in local_state.real_vehicle_name_by_local_vehicle_name.items():
        bucket.local_name_by_real_name[real_name] = local_name
        bucket.real_id_by_name[real_name] = local_state.real_vehicle_id(real_name)
    bucket.binding_by_visit = _copy_binding(local_state)
    GATE.buckets_by_world_id[world_id] = bucket
    return bucket


def _selected_names():
    if GATE.selected_bucket is None:
        return {}
    return GATE.selected_bucket.real_id_by_name


def _binding_info_for_selected():
    if GATE.selected_bucket is None:
        return {}
    return GATE.selected_bucket.binding_by_visit


def _role_for_visit(visit_text, binding_info):
    if visit_text == _visit_text(BUYER_NAME, BUYER_VISIT_ID):
        return "buyer"
    if visit_text == _visit_text(SELLER_NAME, SELLER_VISIT_ID):
        return "seller"
    info = binding_info.get(visit_text)
    if info is None:
        return None
    return info["trade_role"]


def _scope_for(real_name, visit_text, name_to_id, binding_info):
    if visit_text in binding_info:
        return "binding"
    if real_name in name_to_id:
        return "unbound_or_nonbinding_local"
    return "outside_initial_local_set"


def _predicted_route_for(visit_text):
    if visit_text == _visit_text(BUYER_NAME, BUYER_VISIT_ID):
        return BUYER_PREDICTED_ROUTE
    if visit_text == _visit_text(SELLER_NAME, SELLER_VISIT_ID):
        return SELLER_ROUTE
    return None


def _actual_route_constant_for(visit_text):
    if visit_text == _visit_text(BUYER_NAME, BUYER_VISIT_ID):
        return BUYER_ACTUAL_ROUTE
    if visit_text == _visit_text(SELLER_NAME, SELLER_VISIT_ID):
        return SELLER_ROUTE
    return None


def _passage_for(world_kind, timestep, vehicle_name):
    if world_kind == WORLD_CANDIDATE and GATE.selected_bucket is not None:
        events = GATE.selected_bucket.passage_rows
    elif world_kind == WORLD_ACTUAL:
        events = GATE.actual_passage_rows
    else:
        events = []
    found = None
    for event in events:
        if event["world_kind"] != world_kind:
            continue
        if event["world_timestep"] != timestep:
            continue
        if event["real_vehicle_name"] != vehicle_name:
            continue
        found = event
    return found


def _capture_vehicle(
    world,
    node,
    vehicle,
    *,
    world_kind,
    timestep,
    phase,
    candidate_identity,
    evaluation_index,
    name_to_id,
    binding_info,
):
    local_name = getattr(vehicle, "name", None)
    vehicle_id = getattr(vehicle, "id", None)
    if type(vehicle_id) is bool:
        vehicle_id = None
    correspondence = "not_in_initial_map"
    real_name = local_name
    if isinstance(local_name, str) and local_name in name_to_id:
        if vehicle_id == name_to_id[local_name]:
            correspondence = "official_initial_map"
        else:
            correspondence = "id_mismatch_do_not_pair"
            real_name = None
    link = getattr(vehicle, "link", None)
    link_name = _link_name(link)
    inlink_names = set(node.inlinks.keys())
    outlink_names = set(node.outlinks.keys())
    on_inlink = link_name in inlink_names
    on_outlink = link_name in outlink_names
    incoming_index = _incoming_index(node, vehicle)
    in_incoming = incoming_index is not None
    in_compared_set = on_inlink or on_outlink or in_incoming or (
        isinstance(local_name, str) and local_name in name_to_id
    )
    visit_pair = _plain_visit(vehicle)
    if visit_pair is None:
        visit_text = None
        visit_id = None
    else:
        visit_text = _visit_text(visit_pair[0], visit_pair[1])
        visit_id = visit_pair[1]
    binding = None
    if visit_text is not None:
        binding = binding_info.get(visit_text)
    live_link = _read_route_next_link(vehicle)
    live_name = _link_name(live_link)
    predicted_name = _predicted_route_for(visit_text)
    actual_constant = _actual_route_constant_for(visit_text)
    predicted_link = _named_link(node, predicted_name)
    actual_side_link = _named_link(node, actual_constant)
    leader = getattr(vehicle, "leader", None)
    follower = getattr(vehicle, "follower", None)
    physical_index = _physical_index(link, vehicle)
    vehicle_count = None
    if link is not None and getattr(link, "vehicles", None) is not None:
        vehicle_count = len(link.vehicles)
    is_head = physical_index == 0
    passage = None
    if phase != PHASE_BEFORE and phase != PHASE_COMMON_ORIGIN:
        passage = _passage_for(world_kind, timestep, real_name)
    route_origin = None
    binding_rank = None
    arrival_timestep = None
    arrival_tiebreaker = None
    if binding is not None:
        route_origin = binding["route_origin"]
        binding_rank = binding["binding_rank"]
        arrival_timestep = binding["baseline_arrival_timestep"]
        arrival_tiebreaker = binding["arrival_tiebreaker"]
    inlink_for_capacity = link if on_inlink else None
    row = {
        "world_kind": world_kind,
        "tvt_decision_timestep": DECISION_TIMESTEP,
        "world_timestep": timestep,
        "phase": phase,
        "node_name": node.name,
        "candidate_identity": candidate_identity,
        "candidate_evaluation_index": evaluation_index,
        "real_vehicle_name": real_name,
        "local_vehicle_name": local_name,
        "real_vehicle_id": name_to_id.get(local_name) if isinstance(local_name, str) else None,
        "observed_vehicle_id": vehicle_id,
        "visit_id": visit_id,
        "visit_key": visit_text,
        "trade_role": _role_for_visit(visit_text, binding_info),
        "local_scope": _scope_for(local_name, visit_text, name_to_id, binding_info),
        "correspondence_status": correspondence,
        "in_compared_set": in_compared_set,
        "current_link_name": link_name,
        "on_target_inlink": on_inlink,
        "on_target_outlink": on_outlink,
        "position_x": getattr(vehicle, "x", None),
        "x_old": getattr(vehicle, "x_old", None),
        "x_next": getattr(vehicle, "x_next", None),
        "speed_v": getattr(vehicle, "v", None),
        "move_remain": getattr(vehicle, "move_remain", None),
        "lane": getattr(vehicle, "lane", None),
        "physical_index": physical_index,
        "link_vehicle_count": vehicle_count,
        "is_physical_head": is_head,
        "leader_vehicle_name": None if leader is None else getattr(leader, "name", None),
        "follower_vehicle_name": None if follower is None else getattr(follower, "name", None),
        "in_incoming": in_incoming,
        "incoming_index": incoming_index,
        "state": getattr(vehicle, "state", None),
        "mode": getattr(vehicle, "mode", None),
        "assigned_rank": _assigned_rank(world, visit_pair),
        "binding_rank": binding_rank,
        "baseline_local_rank": None,
        "post_trade_local_rank": None,
        "actual_passage_rank": None,
        "already_passed_target_node": None,
        "passage_timestep": None if passage is None else passage["world_timestep"] if passage["passed"] is True else None,
        "arrival_timestep": arrival_timestep,
        "arrival_tiebreaker": arrival_tiebreaker,
        "live_route_next_link_name": live_name,
        "formal_route_next_link_name": _formal_route(world, visit_pair),
        "predicted_route_next_link_name": predicted_name,
        "actual_route_next_link_name": None if passage is None or passage["passed"] is not True else passage["route_next_link_name"],
        "acceptable_outlink_names": None if binding is None else binding["route_next_link_name"],
        "route_origin": route_origin,
        "inlink_capacity_out_remain": None if inlink_for_capacity is None else inlink_for_capacity.capacity_out_remain,
        "node_flow_capacity_remain": node.flow_capacity_remain,
        "live_outlink_capacity_in_remain": None if live_link is None else getattr(live_link, "capacity_in_remain", None),
        "live_outlink_entry_open": _entry_open(live_link, world),
        "predicted_outlink_capacity_in_remain": None if predicted_link is None else predicted_link.capacity_in_remain,
        "predicted_outlink_entry_open": _entry_open(predicted_link, world),
        "actual_side_outlink_capacity_in_remain": None if actual_side_link is None else actual_side_link.capacity_in_remain,
        "actual_side_outlink_entry_open": _entry_open(actual_side_link, world),
        "last_order_control_inlink_name": _link_name(node.last_order_control_inlink),
        "last_order_control_entry_timestep": node.last_order_control_entry_timestep,
        "clearance_timesteps": node.order_control_clearance_timesteps,
        "clearance_satisfied": _clearance_satisfied(node, link if on_inlink else None),
        "passage_attempted": False if passage is None else passage["attempted"],
        "passage_succeeded": False if passage is None else passage["passed"],
        "temporary_skip_reason": None if passage is None else passage["reason"],
        "stop_reason": None if passage is None else passage["stop_reason"],
        "earlier_attempted_visit_keys": None if passage is None else passage["earlier_attempted_visit_keys"],
        "earlier_passed_visit_keys": None if passage is None else passage["earlier_passed_visit_keys"],
    }
    if passage is not None and passage["passed"] is True:
        row["already_passed_target_node"] = True
    return row


def _iter_compared_vehicles(world, node, name_to_id):
    seen = set()
    ordered = []

    def add(vehicle) -> None:
        if vehicle is None:
            return
        identity = id(vehicle)
        if identity in seen:
            return
        seen.add(identity)
        ordered.append(vehicle)

    for link in node.inlinks.values():
        for vehicle in link.vehicles:
            add(vehicle)
    for link in node.outlinks.values():
        for vehicle in link.vehicles:
            add(vehicle)
    for vehicle in node.incoming_vehicles:
        add(vehicle)
    for name in name_to_id:
        add(world.VEHICLES.get(name))
    return ordered


def _capture_node_row(world_kind, node, timestep, phase, candidate_identity, evaluation_index, passed_keys):
    incoming_parts = []
    for vehicle in node.incoming_vehicles:
        visit_pair = _plain_visit(vehicle)
        if visit_pair is None:
            visit_text = ""
            assigned = None
        else:
            visit_text = _visit_text(visit_pair[0], visit_pair[1])
            assigned = _assigned_rank(node.W, visit_pair)
        assigned_text = "" if assigned is None else str(assigned)
        live_name = _link_name(_read_route_next_link(vehicle))
        live_text = "" if live_name is None else live_name
        incoming_parts.append(f"{visit_text}|rank={assigned_text}|route={live_text}")
    return {
        "world_kind": world_kind,
        "tvt_decision_timestep": DECISION_TIMESTEP,
        "world_timestep": timestep,
        "phase": phase,
        "node_name": node.name,
        "candidate_identity": candidate_identity,
        "candidate_evaluation_index": evaluation_index,
        "flow_capacity_remain": node.flow_capacity_remain,
        "last_order_control_inlink_name": _link_name(node.last_order_control_inlink),
        "last_order_control_entry_timestep": node.last_order_control_entry_timestep,
        "clearance_timesteps": node.order_control_clearance_timesteps,
        "incoming_vehicle_count": len(node.incoming_vehicles),
        "incoming_vehicle_order": "|".join(incoming_parts),
        "passed_visit_keys_this_timestep": "|".join(passed_keys),
    }


def _capture_link_row(world_kind, world, link, link_role, timestep, phase, candidate_identity, evaluation_index):
    names = []
    positions = []
    for vehicle in link.vehicles:
        names.append(str(getattr(vehicle, "name", "")))
        positions.append(str(getattr(vehicle, "x", "")))
    return {
        "world_kind": world_kind,
        "tvt_decision_timestep": DECISION_TIMESTEP,
        "world_timestep": timestep,
        "phase": phase,
        "node_name": TARGET_NODE_NAME,
        "candidate_identity": candidate_identity,
        "candidate_evaluation_index": evaluation_index,
        "link_role": link_role,
        "link_name": link.name,
        "capacity_in_remain": link.capacity_in_remain,
        "capacity_out_remain": link.capacity_out_remain,
        "vehicle_count": len(link.vehicles),
        "vehicle_order": "|".join(names),
        "position_order": "|".join(positions),
        "entrance_vehicle_name": _entrance_name(link),
        "entry_open": _entry_open(link, world),
        "cum_arrival_latest": _latest_cum(getattr(link, "cum_arrival", None)),
        "cum_departure_latest": _latest_cum(getattr(link, "cum_departure", None)),
    }


def _passed_keys(world_kind, timestep):
    if world_kind == WORLD_CANDIDATE and GATE.selected_bucket is not None:
        events = GATE.selected_bucket.passage_rows
    elif world_kind == WORLD_ACTUAL:
        events = GATE.actual_passage_rows
    else:
        events = []
    keys = []
    for event in events:
        if event["world_timestep"] != timestep or event["passed"] is not True:
            continue
        if event["visit_key"] is None:
            continue
        keys.append(event["visit_key"])
    return keys


def _capture_tables(world, node, world_kind, timestep, phase, candidate_identity, evaluation_index, name_to_id, binding_info, vehicle_rows, node_rows, link_rows) -> None:
    for vehicle in _iter_compared_vehicles(world, node, name_to_id):
        row = _capture_vehicle(
            world,
            node,
            vehicle,
            world_kind=world_kind,
            timestep=timestep,
            phase=phase,
            candidate_identity=candidate_identity,
            evaluation_index=evaluation_index,
            name_to_id=name_to_id,
            binding_info=binding_info,
        )
        if row["in_compared_set"] is True or row["correspondence_status"] == "official_initial_map":
            vehicle_rows.append(row)
    node_rows.append(
        _capture_node_row(
            world_kind,
            node,
            timestep,
            phase,
            candidate_identity,
            evaluation_index,
            _passed_keys(world_kind, timestep),
        )
    )
    for link in node.inlinks.values():
        link_rows.append(
            _capture_link_row(
                world_kind, world, link, "inlink", timestep, phase, candidate_identity, evaluation_index
            )
        )
    for link in node.outlinks.values():
        link_rows.append(
            _capture_link_row(
                world_kind, world, link, "outlink", timestep, phase, candidate_identity, evaluation_index
            )
        )


def _capture_candidate(local_state, timestep, phase) -> None:
    bucket = _bucket_for(local_state)
    if GATE.selected_bucket is not None and bucket is not GATE.selected_bucket:
        return
    _capture_tables(
        local_state.local_world,
        local_state.target_node,
        WORLD_CANDIDATE,
        timestep,
        phase,
        bucket.candidate_identity,
        bucket.evaluation_index,
        bucket.real_id_by_name,
        bucket.binding_by_visit,
        bucket.vehicle_rows,
        bucket.node_rows,
        bucket.link_rows,
    )


def _capture_actual(node, phase, timestep=None) -> None:
    if GATE.selected_bucket is None:
        raise RuntimeError("Actual snapshot started before the selected candidate was known.")
    if timestep is None:
        timestep = node.W.T
    bucket = GATE.selected_bucket
    _capture_tables(
        node.W,
        node,
        WORLD_ACTUAL,
        timestep,
        phase,
        bucket.candidate_identity,
        bucket.evaluation_index,
        bucket.real_id_by_name,
        bucket.binding_by_visit,
        GATE.actual_vehicle_rows,
        GATE.actual_node_rows,
        GATE.actual_link_rows,
    )


def _freeze_value(value):
    if value is None or type(value) is str or type(value) is bool:
        return value
    if isinstance(value, numbers.Integral) and type(value) is not bool:
        return int(value)
    if isinstance(value, numbers.Real) and type(value) is not bool:
        return float(value)
    if type(value) is tuple:
        frozen = []
        for item in value:
            frozen.append(_freeze_value(item))
        return tuple(frozen)
    raise RuntimeError(
        "common origin temporary snapshot cannot store a live object "
        f"of type {type(value).__name__}."
    )


def _freeze_row(row):
    frozen = {}
    for key in row:
        frozen[key] = _freeze_value(row[key])
    return frozen


def _freeze_row_list(rows):
    frozen = []
    for row in rows:
        frozen.append(_freeze_row(row))
    return frozen


def _freeze_row_span(rows, start) -> None:
    index = start
    while index < len(rows):
        rows[index] = _freeze_row(rows[index])
        index = index + 1


def _capture_actual_common_origin_raw(world) -> None:
    if GATE.common_origin_actual_capture_count != 0:
        raise RuntimeError("Actual common origin was captured more than once.")
    if world is not GATE.real_world:
        raise RuntimeError("Actual common origin was read from a world that is not the real World.")
    if world.T != DECISION_TIMESTEP:
        raise RuntimeError("Actual common origin was read outside T=600.")
    node = world.get_node(TARGET_NODE_NAME)
    vehicle_rows = []
    node_rows = []
    link_rows = []
    _capture_tables(
        world,
        node,
        WORLD_ACTUAL,
        DECISION_TIMESTEP,
        PHASE_COMMON_ORIGIN,
        None,
        None,
        {},
        {},
        vehicle_rows,
        node_rows,
        link_rows,
    )
    if len(node_rows) != 1 or len(link_rows) == 0 or len(vehicle_rows) == 0:
        raise RuntimeError("Actual common origin did not record the target neighborhood.")
    GATE.common_origin_actual_vehicle_raw = _freeze_row_list(vehicle_rows)
    GATE.common_origin_actual_node_raw = _freeze_row_list(node_rows)
    GATE.common_origin_actual_link_raw = _freeze_row_list(link_rows)
    GATE.common_origin_actual_capture_count = 1


def _promote_vehicle_row(row, bucket):
    copied = dict(row)
    local_name = copied["local_vehicle_name"]
    if isinstance(local_name, str) and local_name in bucket.local_name_by_real_name:
        copied["local_vehicle_name"] = bucket.local_name_by_real_name[local_name]
        local_name = copied["local_vehicle_name"]
    copied["candidate_identity"] = bucket.candidate_identity
    copied["candidate_evaluation_index"] = bucket.evaluation_index
    copied["real_vehicle_id"] = None
    copied["real_vehicle_name"] = local_name
    copied["correspondence_status"] = "not_in_initial_map"
    if isinstance(local_name, str) and local_name in bucket.real_id_by_name:
        expected_id = bucket.real_id_by_name[local_name]
        copied["real_vehicle_id"] = expected_id
        if copied["observed_vehicle_id"] == expected_id:
            copied["correspondence_status"] = "official_initial_map"
            copied["real_vehicle_name"] = local_name
        else:
            copied["correspondence_status"] = "id_mismatch_do_not_pair"
            copied["real_vehicle_name"] = None
    visit_text = copied["visit_key"]
    binding = None
    if visit_text is not None:
        binding = bucket.binding_by_visit.get(visit_text)
    copied["trade_role"] = _role_for_visit(visit_text, bucket.binding_by_visit)
    copied["local_scope"] = _scope_for(
        local_name,
        visit_text,
        bucket.real_id_by_name,
        bucket.binding_by_visit,
    )
    copied["in_compared_set"] = (
        copied["on_target_inlink"] is True
        or copied["on_target_outlink"] is True
        or copied["in_incoming"] is True
        or (isinstance(local_name, str) and local_name in bucket.real_id_by_name)
    )
    if binding is None:
        copied["route_origin"] = None
        copied["binding_rank"] = None
        copied["arrival_timestep"] = None
        copied["arrival_tiebreaker"] = None
        copied["acceptable_outlink_names"] = None
    else:
        copied["route_origin"] = binding["route_origin"]
        copied["binding_rank"] = binding["binding_rank"]
        copied["arrival_timestep"] = binding["baseline_arrival_timestep"]
        copied["arrival_tiebreaker"] = binding["arrival_tiebreaker"]
        copied["acceptable_outlink_names"] = binding["route_next_link_name"]
    return copied


def _promote_actual_common_origin() -> None:
    bucket = GATE.selected_bucket
    if bucket is None:
        raise RuntimeError("Cannot attach Actual common origin before candidate selection.")
    if GATE.common_origin_actual_capture_count != 1:
        raise RuntimeError("Actual common origin was not captured once.")
    for row in GATE.common_origin_actual_vehicle_raw:
        GATE.actual_vehicle_rows.append(_promote_vehicle_row(row, bucket))
    for row in GATE.common_origin_actual_node_raw:
        copied = dict(row)
        copied["candidate_identity"] = bucket.candidate_identity
        copied["candidate_evaluation_index"] = bucket.evaluation_index
        GATE.actual_node_rows.append(copied)
    for row in GATE.common_origin_actual_link_raw:
        copied = dict(row)
        copied["candidate_identity"] = bucket.candidate_identity
        copied["candidate_evaluation_index"] = bucket.evaluation_index
        GATE.actual_link_rows.append(copied)


def _blank_event(world_kind, timestep, vehicle_name, visit_key, attempted, passed, reason, stop_reason, route_name, inlink_name, earlier_attempted, earlier_passed):
    return {
        "world_kind": world_kind,
        "tvt_decision_timestep": DECISION_TIMESTEP,
        "world_timestep": timestep,
        "node_name": TARGET_NODE_NAME,
        "candidate_identity": None if GATE.selected_bucket is None else GATE.selected_bucket.candidate_identity,
        "candidate_evaluation_index": None if GATE.selected_bucket is None else GATE.selected_bucket.evaluation_index,
        "real_vehicle_name": vehicle_name,
        "visit_key": visit_key,
        "attempted": attempted,
        "passed": passed,
        "reason": reason,
        "stop_reason": stop_reason,
        "route_next_link_name": route_name,
        "inlink_name": inlink_name,
        "earlier_attempted_visit_keys": earlier_attempted,
        "earlier_passed_visit_keys": earlier_passed,
        "assigned_rank": None,
        "actual_passage_rank": None,
    }


def _record_candidate_passages(bucket, timestep_result) -> None:
    timestep = timestep_result.virtual_timestep
    binding_result = timestep_result.binding_transfer_result
    earlier_attempted = []
    earlier_passed = []
    transferred = set()
    for visit_key in binding_result.transferred_binding_visit_keys:
        text = _visit_text(visit_key[0], visit_key[1])
        transferred.add(text)
        info = bucket.binding_by_visit.get(text)
        route_name = None if info is None else info["route_next_link_name"]
        inlink_name = None if info is None else info["inlink_name"]
        bucket.passage_rows.append(
            _blank_event(
                WORLD_CANDIDATE,
                timestep,
                visit_key[0],
                text,
                True,
                True,
                "passed",
                None,
                route_name,
                inlink_name,
                "|".join(earlier_attempted),
                "|".join(earlier_passed),
            )
        )
        earlier_attempted.append(text)
        earlier_passed.append(text)
    for skip in binding_result.temporarily_skipped_visits:
        text = _visit_text(skip.binding_visit_key[0], skip.binding_visit_key[1])
        info = bucket.binding_by_visit.get(text)
        bucket.passage_rows.append(
            _blank_event(
                WORLD_CANDIDATE,
                timestep,
                skip.vehicle_name,
                text,
                True,
                False,
                _enum_name(skip.skip_reason),
                None,
                None if info is None else info["route_next_link_name"],
                None if info is None else info["inlink_name"],
                "|".join(earlier_attempted),
                "|".join(earlier_passed),
            )
        )
        earlier_attempted.append(text)
    stopped = binding_result.stopped_binding_visit_key
    if stopped is not None:
        stopped_text = _visit_text(stopped[0], stopped[1])
        if stopped_text not in transferred:
            info = bucket.binding_by_visit.get(stopped_text)
            bucket.passage_rows.append(
                _blank_event(
                    WORLD_CANDIDATE,
                    timestep,
                    stopped[0],
                    stopped_text,
                    True,
                    False,
                    "clearance_or_scan_stop",
                    _enum_name(binding_result.stop_reason),
                    None if info is None else info["route_next_link_name"],
                    None if info is None else info["inlink_name"],
                    "|".join(earlier_attempted),
                    "|".join(earlier_passed),
                )
            )
            earlier_attempted.append(stopped_text)
            seen_stop = False
            for visit in bucket.binding_by_visit.values():
                if visit["visit_key"] == stopped_text:
                    seen_stop = True
                    continue
                if seen_stop is not True:
                    continue
                bucket.passage_rows.append(
                    _blank_event(
                        WORLD_CANDIDATE,
                        timestep,
                        visit["vehicle_name"],
                        visit["visit_key"],
                        False,
                        False,
                        "not_reached_because_scan_stop",
                        _enum_name(binding_result.stop_reason),
                        visit["route_next_link_name"],
                        visit["inlink_name"],
                        "|".join(earlier_attempted),
                        "|".join(earlier_passed),
                    )
                )
    unbound = timestep_result.unbound_fcfs_result
    unbound_earlier_attempted = []
    unbound_earlier_passed = []
    for record in unbound.transferred_vehicle_records:
        bucket.passage_rows.append(
            _blank_event(
                WORLD_CANDIDATE,
                timestep,
                record.vehicle_name,
                None,
                True,
                True,
                "passed",
                None,
                record.outlink_name,
                record.inlink_name,
                "|".join(unbound_earlier_attempted),
                "|".join(unbound_earlier_passed),
            )
        )
        unbound_earlier_attempted.append(record.vehicle_name)
        unbound_earlier_passed.append(record.vehicle_name)
    for skip in unbound.temporary_skips:
        bucket.passage_rows.append(
            _blank_event(
                WORLD_CANDIDATE,
                timestep,
                skip.vehicle_name,
                None,
                True,
                False,
                _enum_name(skip.skip_reason),
                None,
                None,
                None,
                "|".join(unbound_earlier_attempted),
                "|".join(unbound_earlier_passed),
            )
        )
        unbound_earlier_attempted.append(skip.vehicle_name)


def _refresh_passage_fields(rows, world_kind, timestep) -> None:
    for row in rows:
        if row["world_kind"] != world_kind or row["world_timestep"] != timestep:
            continue
        if row["phase"] == PHASE_BEFORE or row["phase"] == PHASE_COMMON_ORIGIN:
            continue
        passage = _passage_for(world_kind, timestep, row["real_vehicle_name"])
        if passage is None:
            continue
        row["passage_attempted"] = passage["attempted"]
        row["passage_succeeded"] = passage["passed"]
        row["temporary_skip_reason"] = passage["reason"]
        row["stop_reason"] = passage["stop_reason"]
        row["earlier_attempted_visit_keys"] = passage["earlier_attempted_visit_keys"]
        row["earlier_passed_visit_keys"] = passage["earlier_passed_visit_keys"]
        if passage["passed"] is True:
            row["already_passed_target_node"] = True
            row["passage_timestep"] = timestep
            row["actual_route_next_link_name"] = passage["route_next_link_name"]


def wrapped_run(calculation_state):
    local_state = calculation_state.candidate_local_state
    tracing = _is_target_local_state(local_state)
    bucket = None
    if tracing is True:
        bucket = _bucket_for(local_state)
    result = GATE.original_run(calculation_state)
    if tracing is True and bucket is not None:
        bucket.result_id = id(result)
    return result


def wrapped_scan(binding_transfer_state):
    local_state = binding_transfer_state.virtual_time_state.candidate_local_state
    timestep = binding_transfer_state.virtual_time_state.current_virtual_timestep
    if _should_trace_local(local_state, timestep) is True:
        _capture_candidate(local_state, timestep, PHASE_BEFORE)
    result = GATE.original_scan(binding_transfer_state)
    return result


def wrapped_advance(
    local_vehicle_advance_state,
    binding_transfer_scan_result,
):
    binding_transfer_state = local_vehicle_advance_state.binding_transfer_state
    local_state = binding_transfer_state.virtual_time_state.candidate_local_state
    timestep = binding_transfer_state.virtual_time_state.current_virtual_timestep
    if _should_trace_local(local_state, timestep) is True:
        _capture_candidate(local_state, timestep, PHASE_AFTER_PASSAGE)
    result = GATE.original_advance(
        local_vehicle_advance_state,
        binding_transfer_scan_result,
    )
    return result


def wrapped_one_timestep(calculation_state):
    local_state = calculation_state.candidate_local_state
    result = GATE.original_one(calculation_state)
    timestep = result.virtual_timestep
    if _should_trace_local(local_state, timestep) is True:
        bucket = _bucket_for(local_state)
        if GATE.selected_bucket is None or bucket is GATE.selected_bucket:
            _record_candidate_passages(bucket, result)
            _refresh_passage_fields(bucket.vehicle_rows, WORLD_CANDIDATE, timestep)
            _capture_candidate(local_state, timestep, PHASE_AFTER_ADVANCE)
    return result


def wrapped_transfer(node):
    tracing = _is_real_target_node(node)
    if tracing is True:
        _capture_actual(node, PHASE_BEFORE)
    result = GATE.original_transfer(node)
    if tracing is True:
        _capture_actual(node, PHASE_AFTER_PASSAGE)
        _refresh_passage_fields(GATE.actual_vehicle_rows, WORLD_ACTUAL, node.W.T)
    return result


def wrapped_move(node, vehicle, inlink, outlink):
    visit_pair = _plain_visit(vehicle)
    tracing = _is_real_target_node(node)
    result = GATE.original_move(node, vehicle, inlink, outlink)
    if tracing is True:
        if visit_pair is None:
            visit_text = None
            vehicle_name = getattr(vehicle, "name", None)
        else:
            visit_text = _visit_text(visit_pair[0], visit_pair[1])
            vehicle_name = visit_pair[0]
        earlier_passed = []
        for event in GATE.actual_passage_rows:
            if event["world_timestep"] != node.W.T or event["passed"] is not True:
                continue
            if event["visit_key"] is not None:
                earlier_passed.append(event["visit_key"])
        GATE.actual_passage_rows.append(
            _blank_event(
                WORLD_ACTUAL,
                node.W.T,
                vehicle_name,
                visit_text,
                True,
                True,
                "passed",
                None,
                _link_name(outlink),
                _link_name(inlink),
                "|".join(earlier_passed),
                "|".join(earlier_passed),
            )
        )
    return result


def _read_target_ranks(world):
    node = world.get_node(TARGET_NODE_NAME)
    ranks = {}
    routes = {}
    inlink_names = []
    for link in node.inlinks.values():
        for vehicle in link.vehicles:
            visit_pair = _plain_visit(vehicle)
            if visit_pair is None:
                continue
            text = _visit_text(visit_pair[0], visit_pair[1])
            ranks[text] = _assigned_rank(world, visit_pair)
            routes[text] = _formal_route(world, visit_pair)
            inlink_names.append(text)
    for visit_pair in (BUYER_VISIT, SELLER_VISIT):
        text = _visit_text(visit_pair[0], visit_pair[1])
        if text not in ranks:
            ranks[text] = _assigned_rank(world, visit_pair)
            routes[text] = _formal_route(world, visit_pair)
    return ranks, routes, inlink_names


def _selection_for_northeast(driver_result):
    atomic = getattr(driver_result, "atomic_apply_set_result", None)
    if atomic is None:
        return None
    validation_set = atomic.final_consistency_validation_set_result
    if validation_set is None:
        raise RuntimeError(
            "atomic_apply_set_result has no final_consistency_validation_set_result."
        )
    final_rank_set = validation_set.final_rank_set_result
    if final_rank_set is None:
        raise RuntimeError(
            "final_consistency_validation_set_result has no final_rank_set_result."
        )
    payment_set = final_rank_set.payment_and_compensation_set_result
    if payment_set is None:
        raise RuntimeError("final_rank_set_result has no payment_and_compensation_set_result.")
    selection_set = payment_set.candidate_selection_set_result
    if selection_set is None:
        raise RuntimeError(
            "payment_and_compensation_set_result has no candidate_selection_set_result."
        )
    for node_result in selection_set.node_candidate_selection_results:
        if node_result.node_name == TARGET_NODE_NAME:
            return node_result
    return None


def _local_result_of_selected(selection_node):
    if selection_node is None:
        return None
    economic = selection_node.selected_candidate_economic_result
    if economic is None:
        return None
    return economic.candidate_local_virtual_calculation_result


def _resolve_selected(driver_result) -> None:
    selection_node = _selection_for_northeast(driver_result)
    local_result = _local_result_of_selected(selection_node)
    if local_result is None:
        raise RuntimeError("T=600 northeast selection has no local virtual-calculation result.")
    found = None
    for bucket in GATE.buckets_by_world_id.values():
        if bucket.result_id == id(local_result):
            if found is not None:
                raise RuntimeError("Selected local result matched two candidate traces.")
            found = bucket
    if found is None:
        raise RuntimeError("Selected local result has no captured candidate trace.")
    if found.evaluation_index != EXPECTED_EVALUATION_INDEX:
        raise RuntimeError(
            f"Selected evaluation index is {found.evaluation_index}, expected {EXPECTED_EVALUATION_INDEX}."
        )
    if found.buyers_sorted != (BUYER_VISIT,):
        raise RuntimeError(f"Selected buyers_sorted is {found.buyers_sorted!r}.")
    for bucket in GATE.buckets_by_world_id.values():
        if bucket.common_origin_captured is not True:
            raise RuntimeError("A traced candidate has no common origin snapshot.")
    GATE.selected_bucket = found
    retained = {}
    retained[found.local_world_id] = found
    GATE.buckets_by_world_id = retained


def _decision_row(world, timestep, before_ranks, before_routes, before_inlink, driver_result):
    after_ranks, after_routes, after_inlink = _read_target_ranks(world)
    selection_node = _selection_for_northeast(driver_result)
    local_result = _local_result_of_selected(selection_node)
    identity = None
    selected_present = False
    if local_result is not None and GATE.selected_bucket is not None:
        if id(local_result) == GATE.selected_bucket.result_id and timestep == DECISION_TIMESTEP:
            identity = GATE.selected_bucket.candidate_identity
            selected_present = True
        elif selection_node is not None and selection_node.selected_candidate_economic_result is not None:
            selected_present = True
            buyers = local_result.concrete_buyer_candidate_set.buyers_sorted
            identity = _identity_text("later", buyers)
    buyer_text = _visit_text(BUYER_NAME, BUYER_VISIT_ID)
    seller_text = _visit_text(SELLER_NAME, SELLER_VISIT_ID)
    changed_names = []
    for visit_text in before_inlink:
        if before_ranks.get(visit_text) != after_ranks.get(visit_text):
            changed_names.append(visit_text)
    return {
        "decision_timestep": timestep,
        "node_name": TARGET_NODE_NAME,
        "selected_candidate_present": selected_present,
        "candidate_identity": identity,
        "selection_status": None if selection_node is None else _enum_name(selection_node.selection_status),
        "buyer_assigned_rank_before": before_ranks.get(buyer_text),
        "buyer_assigned_rank_after": after_ranks.get(buyer_text),
        "buyer_rank_changed": before_ranks.get(buyer_text) != after_ranks.get(buyer_text),
        "buyer_formal_route_before": before_routes.get(buyer_text),
        "buyer_formal_route_after": after_routes.get(buyer_text),
        "buyer_formal_route_changed": before_routes.get(buyer_text) != after_routes.get(buyer_text),
        "seller_assigned_rank_before": before_ranks.get(seller_text),
        "seller_assigned_rank_after": after_ranks.get(seller_text),
        "seller_rank_changed": before_ranks.get(seller_text) != after_ranks.get(seller_text),
        "seller_formal_route_before": before_routes.get(seller_text),
        "seller_formal_route_after": after_routes.get(seller_text),
        "seller_formal_route_changed": before_routes.get(seller_text) != after_routes.get(seller_text),
        "inlink_vehicle_rank_changed": len(changed_names) > 0,
        "changed_inlink_visit_keys": "|".join(changed_names),
        "inlink_visit_keys_before_decision": "|".join(before_inlink),
        "inlink_visit_keys_after_decision": "|".join(after_inlink),
    }


def wrapped_build_local_state(real_W, binding_rank_sequence):
    local_state = GATE.original_build(real_W, binding_rank_sequence)
    if _is_target_local_state(local_state) is True:
        bucket = _bucket_for(local_state)
        if bucket.common_origin_captured is True:
            raise RuntimeError("Candidate common origin was captured twice.")
        vehicle_start = len(bucket.vehicle_rows)
        node_start = len(bucket.node_rows)
        link_start = len(bucket.link_rows)
        _capture_tables(
            local_state.local_world,
            local_state.target_node,
            WORLD_CANDIDATE,
            DECISION_TIMESTEP,
            PHASE_COMMON_ORIGIN,
            bucket.candidate_identity,
            bucket.evaluation_index,
            bucket.real_id_by_name,
            bucket.binding_by_visit,
            bucket.vehicle_rows,
            bucket.node_rows,
            bucket.link_rows,
        )
        _freeze_row_span(bucket.vehicle_rows, vehicle_start)
        _freeze_row_span(bucket.node_rows, node_start)
        _freeze_row_span(bucket.link_rows, link_start)
        if len(bucket.node_rows) != node_start + 1:
            raise RuntimeError("Candidate common origin did not record the target node once.")
        bucket.common_origin_captured = True
    return local_state


def wrapped_driver(world):
    if world is not GATE.real_world:
        return GATE.original_driver(world)
    timestep = world.T
    if timestep == DECISION_TIMESTEP:
        _capture_actual_common_origin_raw(world)
    if type(timestep) is int and TRACE_START < timestep <= TRACE_END + 1:
        if GATE.selected_bucket is None:
            raise RuntimeError("Real after-advance snapshot started before candidate selection.")
        node = world.get_node(TARGET_NODE_NAME)
        previous_timestep = timestep - 1
        _capture_actual(node, PHASE_AFTER_ADVANCE, previous_timestep)
        _refresh_passage_fields(GATE.actual_vehicle_rows, WORLD_ACTUAL, previous_timestep)
    record_decision = type(timestep) is int and TRACE_START <= timestep <= TRACE_END
    before_ranks = None
    before_routes = None
    before_inlink = None
    if record_decision is True:
        before_ranks, before_routes, before_inlink = _read_target_ranks(world)
    result = GATE.original_driver(world)
    if timestep == DECISION_TIMESTEP:
        _resolve_selected(result)
        _promote_actual_common_origin()
    if record_decision is True:
        GATE.decision_rows.append(
            _decision_row(world, timestep, before_ranks, before_routes, before_inlink, result)
        )
    return result


def install_paired_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Paired trace hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_run = local_set_module.run_tvt_mp_candidate_local_virtual_calculation
    GATE.original_one = local_calc_module.run_tvt_mp_candidate_local_virtual_calculation_one_timestep
    GATE.original_scan = local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    GATE.original_advance = (
        local_calc_module.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals
    )
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_transfer = uxsim_module.Node.transfer
    GATE.original_move = uxsim_module.Node._transfer_one_vehicle_between_links
    GATE.original_build = local_set_module.build_tvt_mp_candidate_local_state
    GATE.installed = True
    local_set_module.build_tvt_mp_candidate_local_state = wrapped_build_local_state
    local_set_module.run_tvt_mp_candidate_local_virtual_calculation = wrapped_run
    local_calc_module.run_tvt_mp_candidate_local_virtual_calculation_one_timestep = wrapped_one_timestep
    local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = wrapped_scan
    local_calc_module.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = wrapped_advance
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Node.transfer = wrapped_transfer
    uxsim_module.Node._transfer_one_vehicle_between_links = wrapped_move


def restore_paired_hooks() -> None:
    if GATE.installed is not True:
        return
    local_set_module.build_tvt_mp_candidate_local_state = GATE.original_build
    local_set_module.run_tvt_mp_candidate_local_virtual_calculation = GATE.original_run
    local_calc_module.run_tvt_mp_candidate_local_virtual_calculation_one_timestep = GATE.original_one
    local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = GATE.original_scan
    local_calc_module.advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals = (
        GATE.original_advance
    )
    driver_module.run_tvt_mp_driver = GATE.original_driver
    uxsim_module.Node.transfer = GATE.original_transfer
    uxsim_module.Node._transfer_one_vehicle_between_links = GATE.original_move
    GATE.original_run = None
    GATE.original_one = None
    GATE.original_scan = None
    GATE.original_advance = None
    GATE.original_driver = None
    GATE.original_transfer = None
    GATE.original_move = None
    GATE.original_build = None
    GATE.real_world = None
    GATE.installed = False


def _prepare_trial_world():
    four_cross_trial.SPILLBACK_TIMESTEP_ROWS.clear()
    vot_rng = four_cross_trial.np.random.default_rng(four_cross_trial.VOT_SEED)
    vot_values = four_cross_trial.generate_vehicle_vots(
        vot_rng, len(four_cross_trial.VEHICLE_SPECS)
    )
    vot_records = four_cross_trial.build_vehicle_vot_records(
        four_cross_trial.VEHICLE_SPECS,
        vot_values,
    )
    world = four_cross_trial.build_world_and_network()
    four_cross_trial.add_vehicles_to_world(world, four_cross_trial.VEHICLE_SPECS, vot_records)
    world.finalize_scenario()
    if world.TSIZE != four_cross_trial.INTERNAL_TSIZE:
        raise RuntimeError(f"Expected TSIZE=={four_cross_trial.INTERNAL_TSIZE}, got {world.TSIZE}.")
    if world.name != four_cross_trial.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name was not kept.")
    return world


def _rows_for(rows, world_kind, timestep, phase):
    found = []
    for row in rows:
        if row["world_kind"] != world_kind:
            continue
        if row["world_timestep"] != timestep or row["phase"] != phase:
            continue
        found.append(row)
    return found


def _require_one_phase(rows, world_kind, timestep, phase) -> None:
    for row in rows:
        if row["world_kind"] != world_kind:
            continue
        if row["world_timestep"] == timestep and row["phase"] == phase:
            return
    raise RuntimeError(f"Missing {world_kind} node snapshot T={timestep} phase={phase}.")


def _require_phase_coverage(rows, world_kind, start, end) -> None:
    _require_one_phase(rows, world_kind, DECISION_TIMESTEP, PHASE_COMMON_ORIGIN)
    timestep = start
    while timestep <= end:
        for phase in (PHASE_BEFORE, PHASE_AFTER_PASSAGE, PHASE_AFTER_TIMESTEP):
            _require_one_phase(rows, world_kind, timestep, phase)
        timestep = timestep + 1


def _attach_actual_ranks(world) -> None:
    registry = getattr(world, "order_control_tvt_mp_actual_node_passage_history_registry", None)
    if not isinstance(registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError("Actual passage history registry is missing.")
    by_visit = {}
    for record in registry.records_by_node_name.get(TARGET_NODE_NAME, ()):
        by_visit[record.visit_key] = record
    for row in GATE.actual_passage_rows:
        if row["visit_key"] is None:
            continue
        vehicle_name, separator, visit_id_text = row["visit_key"].partition(":")
        if separator != ":":
            continue
        visit_id = int(visit_id_text)
        record = by_visit.get((vehicle_name, visit_id))
        if record is None:
            continue
        if record.actual_passage_timestep != row["world_timestep"]:
            continue
        row["actual_passage_rank"] = record.actual_node_passage_rank
        row["assigned_rank"] = _assigned_rank(world, (vehicle_name, visit_id))
    for row in GATE.actual_vehicle_rows:
        if row["visit_key"] is None:
            continue
        vehicle_name, separator, visit_id_text = row["visit_key"].partition(":")
        if separator != ":":
            continue
        record = by_visit.get((vehicle_name, int(visit_id_text)))
        if record is None:
            continue
        row["actual_passage_rank"] = record.actual_node_passage_rank


def _research_visit(bundle, vehicle_name, visit_id):
    found = None
    for visit in bundle.visits:
        if visit.tvt_decision_timestep != DECISION_TIMESTEP:
            continue
        if visit.node_name != TARGET_NODE_NAME:
            continue
        if visit.vehicle_name == vehicle_name and visit.visit_id == visit_id:
            if found is not None:
                raise RuntimeError(f"Repeated research visit {vehicle_name}:{visit_id}.")
            found = visit
    if found is None:
        raise RuntimeError(f"Research output has no {vehicle_name}:{visit_id}.")
    return found


def _require_research(bundle) -> None:
    buyer = _research_visit(bundle, BUYER_NAME, BUYER_VISIT_ID)
    seller = _research_visit(bundle, SELLER_NAME, SELLER_VISIT_ID)
    if buyer.candidate_passage_timestep != BUYER_CANDIDATE_PASSAGE:
        raise RuntimeError("Buyer candidate passage is not 606.")
    if seller.candidate_passage_timestep != SELLER_CANDIDATE_PASSAGE:
        raise RuntimeError("Seller candidate passage is not 608.")
    if buyer.actual_passage_timestep != BUYER_ACTUAL_PASSAGE:
        raise RuntimeError("Buyer actual passage is not 607.")
    if seller.actual_passage_timestep != SELLER_ACTUAL_PASSAGE:
        raise RuntimeError("Seller actual passage is not 609.")
    if buyer.assigned_rank != BUYER_ASSIGNED_RANK or seller.assigned_rank != SELLER_ASSIGNED_RANK:
        raise RuntimeError("Assigned ranks do not match 208 and 209.")
    if buyer.actual_node_passage_rank != BUYER_ACTUAL_RANK:
        raise RuntimeError("Buyer actual rank is not 208.")
    if seller.actual_node_passage_rank != SELLER_ACTUAL_RANK:
        raise RuntimeError("Seller actual rank is not 209.")
    if buyer.predicted_route_next_link_name != BUYER_PREDICTED_ROUTE:
        raise RuntimeError("Buyer predicted route is not southeast.")
    if buyer.actual_route_next_link_name != BUYER_ACTUAL_ROUTE:
        raise RuntimeError("Buyer actual route is not northwest.")
    if seller.predicted_route_next_link_name != SELLER_ROUTE:
        raise RuntimeError("Seller predicted route differs.")
    if seller.actual_route_next_link_name != SELLER_ROUTE:
        raise RuntimeError("Seller actual route differs.")


def _require_passage_event(world_kind, vehicle_name, timestep) -> None:
    if world_kind == WORLD_CANDIDATE:
        events = GATE.selected_bucket.passage_rows
    else:
        events = GATE.actual_passage_rows
    for event in events:
        if event["real_vehicle_name"] != vehicle_name:
            continue
        if event["world_timestep"] != timestep or event["passed"] is not True:
            continue
        return
    raise RuntimeError(f"Missing {world_kind} passage {vehicle_name} at T={timestep}.")


def _pair_key(row):
    if row["correspondence_status"] == "id_mismatch_do_not_pair":
        return None
    if row["correspondence_status"] == "official_initial_map":
        return row["real_vehicle_name"]
    if row["real_vehicle_name"] is None:
        return None
    return row["real_vehicle_name"]


def _values_equal(field_name, left, right) -> bool:
    if left is None and right is None:
        return True
    tolerant = field_name in (
        "position_x",
        "x_old",
        "x_next",
        "speed_v",
        "move_remain",
        "inlink_capacity_out_remain",
        "node_flow_capacity_remain",
        "live_outlink_capacity_in_remain",
        "flow_capacity_remain",
        "capacity_in_remain",
        "capacity_out_remain",
        "cum_arrival_latest",
        "cum_departure_latest",
        "position_order",
    )
    if tolerant is True:
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            if type(left) is bool or type(right) is bool:
                return left == right
            if abs(float(left) - float(right)) <= ABSOLUTE_TOLERANCE:
                return True
            return False
    return left == right


COMMON_ORIGIN_VEHICLE_FIELDS = (
    "real_vehicle_name",
    "observed_vehicle_id",
    "visit_key",
    "current_link_name",
    "position_x",
    "x_old",
    "x_next",
    "speed_v",
    "move_remain",
    "lane",
    "in_incoming",
    "incoming_index",
    "state",
    "mode",
    "live_route_next_link_name",
    "physical_index",
    "leader_vehicle_name",
    "follower_vehicle_name",
)

AFTER_TIMESTEP_VEHICLE_FIELDS = (
    "current_link_name",
    "visit_key",
    "position_x",
    "x_old",
    "x_next",
    "speed_v",
    "move_remain",
    "lane",
    "in_incoming",
    "incoming_index",
    "state",
    "mode",
    "live_route_next_link_name",
    "passage_attempted",
    "passage_succeeded",
    "physical_index",
    "leader_vehicle_name",
    "follower_vehicle_name",
    "assigned_rank",
    "formal_route_next_link_name",
)

NODE_COMPARE_FIELDS = (
    "flow_capacity_remain",
    "clearance_timesteps",
    "last_order_control_inlink_name",
    "last_order_control_entry_timestep",
    "incoming_vehicle_order",
)

COMMON_ORIGIN_LINK_FIELDS = (
    "vehicle_order",
    "position_order",
    "capacity_in_remain",
    "capacity_out_remain",
    "entry_open",
    "entrance_vehicle_name",
    "cum_arrival_latest",
    "cum_departure_latest",
)

AFTER_LINK_FIELDS = (
    "vehicle_order",
    "position_order",
    "entrance_vehicle_name",
    "capacity_in_remain",
    "capacity_out_remain",
    "entry_open",
)


def _phase_comparability(phase) -> str:
    if phase == PHASE_COMMON_ORIGIN:
        return COMPARABLE_COMMON
    if phase == PHASE_AFTER_TIMESTEP:
        return COMPARABLE_AFTER
    if phase in REFERENCE_PHASES:
        return NONCOMPARABLE
    return NONCOMPARABLE


def _preceding_step(phase) -> str:
    if phase == PHASE_COMMON_ORIGIN:
        return "real_world_copy_and_driver_entry_before_link_update"
    if phase == PHASE_BEFORE:
        return "reference_before_node_passage"
    if phase == PHASE_AFTER_PASSAGE:
        return "reference_after_node_passage"
    if phase == PHASE_AFTER_TIMESTEP:
        return "completed_timestep_before_next_capacity_refill"
    return "unknown_phase"


def _append_difference(
    timestep,
    phase,
    entity_kind,
    entity_identity,
    field_name,
    candidate_value,
    actual_value,
    classification,
    excluded,
    exclusion_reason,
    link_vehicle_sets_match,
) -> None:
    row = {
        "world_timestep": timestep,
        "phase": phase,
        "entity_kind": entity_kind,
        "entity_identity": entity_identity,
        "field_name": field_name,
        "candidate_value": candidate_value,
        "actual_value": actual_value,
        "classification": classification,
        "preceding_production_step": _preceding_step(phase),
        "phase_comparability": _phase_comparability(phase),
        "excluded_from_first_divergence": excluded,
        "exclusion_reason": exclusion_reason,
        "link_vehicle_sets_match": link_vehicle_sets_match,
    }
    GATE.difference_rows.append(row)
    if classification == "expected_binding_route_difference":
        GATE.expected_initial_rows.append(row)
    elif classification == "unexpected_common_origin_difference":
        GATE.unexpected_common_origin_rows.append(row)


def _split_order(order_text):
    if order_text is None or order_text == "":
        return []
    if type(order_text) is not str:
        raise RuntimeError("An order field is not text.")
    return order_text.split("|")


def _official_vehicle_order(order_text, real_id_by_name):
    kept = []
    for name in _split_order(order_text):
        if name in real_id_by_name:
            kept.append(name)
    return tuple(kept)


def _plain_float(text):
    if type(text) is not str or text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _position_orders_equal(left, right) -> bool:
    left_parts = _split_order(left)
    right_parts = _split_order(right)
    if len(left_parts) != len(right_parts):
        return False
    index = 0
    while index < len(left_parts):
        left_number = _plain_float(left_parts[index])
        right_number = _plain_float(right_parts[index])
        if left_number is None or right_number is None:
            if left_parts[index] != right_parts[index]:
                return False
        elif _values_equal("position_x", left_number, right_number) is not True:
            return False
        index = index + 1
    return True


def _incoming_tokens(order_text):
    parts = _split_order(order_text)
    if len(parts) % 3 != 0:
        return None
    visits = []
    ranks = []
    routes = []
    index = 0
    while index < len(parts):
        visits.append(parts[index])
        ranks.append(parts[index + 1])
        routes.append(parts[index + 2])
        index = index + 3
    return (tuple(visits), tuple(ranks), tuple(routes))


def _order_dependent_field_is_comparable(field_name, link_vehicle_orders_match) -> bool:
    if field_name != "physical_index" and field_name != "leader_vehicle_name" and field_name != "follower_vehicle_name":
        return True
    if link_vehicle_orders_match is True:
        return True
    return False


def _is_binding_route_difference(candidate_row, actual_row) -> bool:
    binding_route = candidate_row.get("acceptable_outlink_names")
    if binding_route is None:
        return False
    candidate_route = candidate_row["live_route_next_link_name"]
    actual_route = actual_row["live_route_next_link_name"]
    if candidate_route == actual_route:
        return False
    if candidate_route == binding_route:
        return True
    return False


def _sorted_pair_keys(left_index, right_index):
    names = []
    for name in left_index:
        names.append(name)
    for name in right_index:
        if name not in names:
            names.append(name)
    names.sort()
    return names


def _reference_decision(link_vehicle_sets_match):
    return (
        "non_comparable_intermediate_phase",
        True,
        "candidate_local_order_and_actual_node_registration_order_differ",
        link_vehicle_sets_match,
    )


def _vehicle_absence_decision(phase, present_row):
    if phase == PHASE_COMMON_ORIGIN:
        return ("unexpected_common_origin_difference", False, "", None)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        return _reference_decision(None)
    if present_row["correspondence_status"] != "official_initial_map":
        return ("outside_candidate_local_set", True, "outside_candidate_local_set", None)
    return ("dynamic_divergence", False, "", None)


def _identity_decision(phase):
    if phase == PHASE_COMMON_ORIGIN:
        return ("unexpected_common_origin_difference", False, "", None)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        return _reference_decision(None)
    return ("id_mismatch_do_not_pair", True, "id_mismatch_do_not_pair", None)


def _vehicle_field_decision(phase, field_name, candidate_row, actual_row, link_vehicle_orders_match):
    comparable = _order_dependent_field_is_comparable(field_name, link_vehicle_orders_match)
    if phase == PHASE_COMMON_ORIGIN:
        if comparable is not True:
            return (
                "excluded_until_link_vehicle_sets_match",
                True,
                "link_vehicle_set_differs",
                False,
            )
        return ("unexpected_common_origin_difference", False, "", link_vehicle_orders_match)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        if field_name == "live_route_next_link_name" and _is_binding_route_difference(candidate_row, actual_row) is True:
            return (
                "expected_binding_route_difference",
                True,
                "binding_route_applied_after_common_origin",
                link_vehicle_orders_match,
            )
        return _reference_decision(link_vehicle_orders_match)
    if comparable is not True:
        return (
            "excluded_until_link_vehicle_sets_match",
            True,
            "link_vehicle_set_differs",
            False,
        )
    if field_name == "live_route_next_link_name" and _is_binding_route_difference(candidate_row, actual_row) is True:
        return (
            "expected_binding_route_difference",
            True,
            "binding_route_applied_after_common_origin",
            link_vehicle_orders_match,
        )
    if field_name == "assigned_rank" or field_name == "formal_route_next_link_name":
        return (
            "later_actual_decision_rank_difference",
            True,
            "candidate_does_not_store_a_later_real_decision_rank",
            link_vehicle_orders_match,
        )
    sets_match = link_vehicle_orders_match
    if field_name == "physical_index" or field_name == "leader_vehicle_name" or field_name == "follower_vehicle_name":
        sets_match = True
    return ("dynamic_divergence", False, "", sets_match)


def _link_absence_decision(phase):
    if phase == PHASE_COMMON_ORIGIN:
        return ("unexpected_common_origin_difference", False, "", False)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        return _reference_decision(False)
    return ("dynamic_divergence", False, "", False)


def _link_field_decision(phase, field_name, candidate_row, actual_row, real_id_by_name):
    full_match = candidate_row["vehicle_order"] == actual_row["vehicle_order"]
    local_match = _official_vehicle_order(
        candidate_row["vehicle_order"],
        real_id_by_name,
    ) == _official_vehicle_order(actual_row["vehicle_order"], real_id_by_name)
    if phase == PHASE_COMMON_ORIGIN:
        return ("unexpected_common_origin_difference", False, "", full_match)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        return _reference_decision(full_match)
    order_text_field = (
        field_name == "vehicle_order"
        or field_name == "position_order"
        or field_name == "entrance_vehicle_name"
    )
    if order_text_field is True and local_match is True and full_match is not True:
        return (
            "downstream_boundary_or_outside_vehicle_representation",
            True,
            "link_vehicle_set_includes_outside_or_boundary_vehicle",
            False,
        )
    if field_name != "vehicle_order" and full_match is not True and order_text_field is True:
        return (
            "excluded_until_link_vehicle_sets_match",
            True,
            "link_vehicle_set_differs",
            False,
        )
    return ("dynamic_divergence", False, "", full_match)


def _plain_state_decision(phase):
    if phase == PHASE_COMMON_ORIGIN:
        return ("unexpected_common_origin_difference", False, "", None)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        return _reference_decision(None)
    return ("dynamic_divergence", False, "", None)


def _node_incoming_decision(phase, candidate_value, actual_value):
    if candidate_value == actual_value:
        return None
    tokens_left = _incoming_tokens(candidate_value)
    tokens_right = _incoming_tokens(actual_value)
    if phase == PHASE_COMMON_ORIGIN:
        if tokens_left is None or tokens_right is None:
            return ("unexpected_common_origin_difference", False, "", None)
        if tokens_left[0] != tokens_right[0] or tokens_left[2] != tokens_right[2]:
            return ("unexpected_common_origin_difference", False, "", None)
        if tokens_left[1] != tokens_right[1]:
            return (
                "later_actual_decision_rank_difference",
                True,
                "rank_text_is_not_a_common_origin_traffic_field",
                None,
            )
        return ("unexpected_common_origin_difference", False, "", None)
    if phase == PHASE_BEFORE or phase == PHASE_AFTER_PASSAGE:
        return _reference_decision(None)
    tokens_left = _incoming_tokens(candidate_value)
    tokens_right = _incoming_tokens(actual_value)
    if tokens_left is None or tokens_right is None:
        return ("dynamic_divergence", False, "", None)
    if tokens_left[0] != tokens_right[0]:
        return ("dynamic_divergence", False, "", None)
    if tokens_left[1] != tokens_right[1]:
        return (
            "later_actual_decision_rank_difference",
            True,
            "incoming_text_includes_rank_or_live_route",
            None,
        )
    if tokens_left[2] != tokens_right[2]:
        return (
            "expected_binding_route_difference",
            True,
            "incoming_text_includes_rank_or_live_route",
            None,
        )
    return ("dynamic_divergence", False, "", None)


def _vehicle_fields_for(phase):
    if phase == PHASE_COMMON_ORIGIN:
        return COMMON_ORIGIN_VEHICLE_FIELDS
    return AFTER_TIMESTEP_VEHICLE_FIELDS


def _link_fields_for(phase):
    if phase == PHASE_COMMON_ORIGIN:
        return COMMON_ORIGIN_LINK_FIELDS
    return AFTER_LINK_FIELDS


def _link_values_differ(field_name, left, right) -> bool:
    if field_name == "position_order":
        if _position_orders_equal(left, right) is True:
            return False
        return True
    if _values_equal(field_name, left, right) is True:
        return False
    return True


def _paired_vehicle_is_official(candidate_row, actual_row) -> bool:
    if candidate_row["correspondence_status"] != "official_initial_map":
        return False
    if actual_row["correspondence_status"] != "official_initial_map":
        return False
    return True


def _vehicle_link_orders_match(candidate_row, actual_row, orders_match_by_link) -> bool:
    candidate_link = candidate_row["current_link_name"]
    actual_link = actual_row["current_link_name"]
    if candidate_link != actual_link:
        return False
    if type(candidate_link) is not str:
        return False
    if orders_match_by_link.get(candidate_link) is True:
        return True
    return False


def _index_by_key(rows):
    indexed = {}
    for row in rows:
        if row.get("in_compared_set") is False and row.get("correspondence_status") != "official_initial_map":
            continue
        key = _pair_key(row)
        if key is None:
            key = f"unpaired:{row['world_kind']}:{row['local_vehicle_name']}"
        if key in indexed:
            raise RuntimeError(f"Duplicate paired vehicle {key} at one snapshot.")
        indexed[key] = row
    return indexed


def _compare_links(timestep, phase, candidate_links, actual_links, real_id_by_name):
    candidate_by_name = {}
    for row in candidate_links:
        if row["link_name"] in candidate_by_name:
            raise RuntimeError(f"Duplicate candidate link {row['link_name']} at T={timestep} {phase}.")
        candidate_by_name[row["link_name"]] = row
    actual_by_name = {}
    for row in actual_links:
        if row["link_name"] in actual_by_name:
            raise RuntimeError(f"Duplicate actual link {row['link_name']} at T={timestep} {phase}.")
        actual_by_name[row["link_name"]] = row
    names = _sorted_pair_keys(candidate_by_name, actual_by_name)
    orders_match = {}
    compared = 0
    fields = _link_fields_for(phase)
    for name in names:
        candidate_row = candidate_by_name.get(name)
        actual_row = actual_by_name.get(name)
        if candidate_row is None or actual_row is None:
            classification, excluded, exclusion_reason, sets_match = _link_absence_decision(phase)
            _append_difference(
                timestep,
                phase,
                "link",
                name,
                "link_set",
                None if candidate_row is None else "present",
                None if actual_row is None else "present",
                classification,
                excluded,
                exclusion_reason,
                sets_match,
            )
            orders_match[name] = False
            continue
        compared = compared + 1
        orders_match[name] = candidate_row["vehicle_order"] == actual_row["vehicle_order"]
        for field_name in fields:
            if _link_values_differ(field_name, candidate_row[field_name], actual_row[field_name]) is not True:
                continue
            classification, excluded, exclusion_reason, sets_match = _link_field_decision(
                phase,
                field_name,
                candidate_row,
                actual_row,
                real_id_by_name,
            )
            _append_difference(
                timestep,
                phase,
                "link",
                name,
                field_name,
                candidate_row[field_name],
                actual_row[field_name],
                classification,
                excluded,
                exclusion_reason,
                sets_match,
            )
    return orders_match, compared


def _compare_vehicles(timestep, phase, candidate_rows, actual_rows, orders_match_by_link):
    candidate_index = _index_by_key(candidate_rows)
    actual_index = _index_by_key(actual_rows)
    names = _sorted_pair_keys(candidate_index, actual_index)
    compared = 0
    fields = _vehicle_fields_for(phase)
    for name in names:
        candidate_row = candidate_index.get(name)
        actual_row = actual_index.get(name)
        if candidate_row is None or actual_row is None:
            present_row = candidate_row if candidate_row is not None else actual_row
            classification, excluded, exclusion_reason, sets_match = _vehicle_absence_decision(phase, present_row)
            _append_difference(
                timestep,
                phase,
                "vehicle",
                name,
                "vehicle_set",
                None if candidate_row is None else "present",
                None if actual_row is None else "present",
                classification,
                excluded,
                exclusion_reason,
                sets_match,
            )
            continue
        compared = compared + 1
        if candidate_row["observed_vehicle_id"] != actual_row["observed_vehicle_id"]:
            classification, excluded, exclusion_reason, sets_match = _identity_decision(phase)
            _append_difference(
                timestep,
                phase,
                "vehicle",
                name,
                "observed_vehicle_id",
                candidate_row["observed_vehicle_id"],
                actual_row["observed_vehicle_id"],
                classification,
                excluded,
                exclusion_reason,
                sets_match,
            )
            continue
        link_vehicle_orders_match = _vehicle_link_orders_match(
            candidate_row,
            actual_row,
            orders_match_by_link,
        )
        official = _paired_vehicle_is_official(candidate_row, actual_row)
        for field_name in fields:
            if _values_equal(field_name, candidate_row[field_name], actual_row[field_name]) is True:
                continue
            classification, excluded, exclusion_reason, sets_match = _vehicle_field_decision(
                phase,
                field_name,
                candidate_row,
                actual_row,
                link_vehicle_orders_match,
            )
            if phase == PHASE_AFTER_TIMESTEP and official is not True and classification == "dynamic_divergence":
                classification = "outside_candidate_local_set"
                excluded = True
                exclusion_reason = "outside_candidate_local_set"
            _append_difference(
                timestep,
                phase,
                "vehicle",
                name,
                field_name,
                candidate_row[field_name],
                actual_row[field_name],
                classification,
                excluded,
                exclusion_reason,
                sets_match,
            )
    return compared


def _compare_nodes(timestep, phase, candidate_nodes, actual_nodes) -> None:
    if len(candidate_nodes) != 1 or len(actual_nodes) != 1:
        raise RuntimeError(f"Expected one node row at T={timestep} {phase}.")
    candidate_row = candidate_nodes[0]
    actual_row = actual_nodes[0]
    for field_name in NODE_COMPARE_FIELDS:
        if field_name == "incoming_vehicle_order":
            decision = _node_incoming_decision(
                phase,
                candidate_row[field_name],
                actual_row[field_name],
            )
            if decision is None:
                continue
        else:
            if _values_equal(field_name, candidate_row[field_name], actual_row[field_name]) is True:
                continue
            decision = _plain_state_decision(phase)
        classification, excluded, exclusion_reason, sets_match = decision
        _append_difference(
            timestep,
            phase,
            "node",
            TARGET_NODE_NAME,
            field_name,
            candidate_row[field_name],
            actual_row[field_name],
            classification,
            excluded,
            exclusion_reason,
            sets_match,
        )


def _compare_phase(timestep, phase, require_rows) -> None:
    bucket = GATE.selected_bucket
    candidate_vehicles = _rows_for(bucket.vehicle_rows, WORLD_CANDIDATE, timestep, phase)
    actual_vehicles = _rows_for(GATE.actual_vehicle_rows, WORLD_ACTUAL, timestep, phase)
    candidate_nodes = _rows_for(bucket.node_rows, WORLD_CANDIDATE, timestep, phase)
    actual_nodes = _rows_for(GATE.actual_node_rows, WORLD_ACTUAL, timestep, phase)
    candidate_links = _rows_for(bucket.link_rows, WORLD_CANDIDATE, timestep, phase)
    actual_links = _rows_for(GATE.actual_link_rows, WORLD_ACTUAL, timestep, phase)
    if len(candidate_nodes) == 0 or len(actual_nodes) == 0:
        if require_rows is True:
            raise RuntimeError(f"Missing common origin rows at T={timestep}.")
        return
    if require_rows is True:
        if len(candidate_vehicles) == 0 or len(actual_vehicles) == 0:
            raise RuntimeError("Missing common origin vehicle rows.")
        if len(candidate_links) == 0 or len(actual_links) == 0:
            raise RuntimeError("Missing common origin link rows.")
    if phase == PHASE_AFTER_TIMESTEP:
        GATE.compared_after_timesteps.append(timestep)
    orders_match, link_count = _compare_links(
        timestep,
        phase,
        candidate_links,
        actual_links,
        bucket.real_id_by_name,
    )
    vehicle_count = _compare_vehicles(
        timestep,
        phase,
        candidate_vehicles,
        actual_rows=actual_vehicles,
        orders_match_by_link=orders_match,
    )
    _compare_nodes(timestep, phase, candidate_nodes, actual_nodes)
    if phase == PHASE_COMMON_ORIGIN:
        GATE.common_origin_compared_vehicle_count = vehicle_count
        GATE.common_origin_compared_node_count = 1
        GATE.common_origin_compared_link_count = link_count


def _raise_if_common_origin_differs() -> None:
    count = len(GATE.unexpected_common_origin_rows)
    if count == 0:
        return
    first = GATE.unexpected_common_origin_rows[0]
    raise RuntimeError(
        "unexpected_common_origin_difference count is "
        f"{count}. First difference is "
        f"T={first['world_timestep']} {first['entity_kind']} "
        f"{first['entity_identity']} field {first['field_name']} "
        f"candidate={first['candidate_value']!r} actual={first['actual_value']!r}. "
        "Output was not written."
    )


def _select_first_divergence() -> None:
    found = None
    for row in GATE.difference_rows:
        if row["phase_comparability"] != COMPARABLE_AFTER:
            continue
        if row["excluded_from_first_divergence"] is True:
            continue
        if row["classification"] != "dynamic_divergence":
            continue
        found = row
        break
    if found is None:
        raise RuntimeError("No dynamic divergence was found on comparable after_timestep.")
    GATE.first_divergence = found


def _require_first_divergence_contract() -> None:
    if len(GATE.unexpected_common_origin_rows) != 0:
        raise RuntimeError("unexpected_common_origin_difference is not zero.")
    first = GATE.first_divergence
    if first is None:
        raise RuntimeError("First divergence was not selected.")
    if first["phase"] != PHASE_AFTER_TIMESTEP:
        raise RuntimeError("First divergence is not a comparable after_timestep.")
    if first["phase_comparability"] != COMPARABLE_AFTER:
        raise RuntimeError("First divergence phase_comparability is not comparable_after_timestep.")
    if first["classification"] != "dynamic_divergence":
        raise RuntimeError("First divergence classification is not dynamic_divergence.")
    if first["excluded_from_first_divergence"] is not False:
        raise RuntimeError("First divergence is marked excluded.")
    if first["phase"] == PHASE_BEFORE or first["phase"] == PHASE_AFTER_PASSAGE:
        raise RuntimeError("A non-comparable intermediate phase was used as first divergence.")
    scanned = None
    for row in GATE.difference_rows:
        if row["classification"] == "non_comparable_intermediate_phase":
            if row["excluded_from_first_divergence"] is not True:
                raise RuntimeError("A non-comparable phase difference was not excluded.")
            if row["phase_comparability"] != NONCOMPARABLE:
                raise RuntimeError("A reference phase was marked comparable.")
        if row["classification"] == "expected_binding_route_difference":
            if row["excluded_from_first_divergence"] is not True:
                raise RuntimeError("A binding route difference was not excluded.")
        if row["field_name"] == "physical_index" or row["field_name"] == "leader_vehicle_name" or row["field_name"] == "follower_vehicle_name":
            if row["classification"] == "dynamic_divergence" and row["link_vehicle_sets_match"] is not True:
                raise RuntimeError("physical_index was compared without matching link vehicle sets.")
        if row["phase_comparability"] != COMPARABLE_AFTER:
            continue
        if row["excluded_from_first_divergence"] is True:
            continue
        if row["classification"] != "dynamic_divergence":
            continue
        scanned = row
        break
    if scanned is not first:
        raise RuntimeError("First divergence is not the unique first comparable after_timestep difference.")


def _compare() -> None:
    _compare_phase(DECISION_TIMESTEP, PHASE_COMMON_ORIGIN, True)
    _raise_if_common_origin_differs()
    timestep = TRACE_START
    while timestep <= TRACE_END:
        _compare_phase(timestep, PHASE_AFTER_TIMESTEP, False)
        timestep = timestep + 1
    timestep = TRACE_START
    while timestep <= TRACE_END:
        _compare_phase(timestep, PHASE_BEFORE, False)
        _compare_phase(timestep, PHASE_AFTER_PASSAGE, False)
        timestep = timestep + 1
    _select_first_divergence()
    _require_first_divergence_contract()


def _vehicle_at(rows, world_kind, timestep, phase, vehicle_name):
    for row in rows:
        if row["world_kind"] != world_kind:
            continue
        if row["world_timestep"] != timestep or row["phase"] != phase:
            continue
        if row["real_vehicle_name"] == vehicle_name:
            return row
    return None


def _first_buyer_position_difference():
    for row in GATE.difference_rows:
        if row["phase"] != PHASE_AFTER_TIMESTEP:
            continue
        if row["classification"] != "dynamic_divergence":
            continue
        if row["excluded_from_first_divergence"] is True:
            continue
        if row["entity_kind"] != "vehicle" or row["entity_identity"] != BUYER_NAME:
            continue
        if row["field_name"] != "position_x" and row["field_name"] != "current_link_name":
            continue
        return row
    return None


def _leading_dynamic_lines(last_timestep):
    wanted = (
        "vehicle_order",
        "position_order",
        "speed_v",
        "move_remain",
        "flow_capacity_remain",
        "capacity_in_remain",
        "capacity_out_remain",
        "current_link_name",
        "position_x",
    )
    lines = []
    for row in GATE.difference_rows:
        if row["phase"] != PHASE_AFTER_TIMESTEP:
            continue
        if row["classification"] != "dynamic_divergence":
            continue
        if row["excluded_from_first_divergence"] is True:
            continue
        if row["world_timestep"] > last_timestep:
            continue
        if row["field_name"] not in wanted:
            continue
        lines.append(
            f"  T={row['world_timestep']} {row['entity_kind']} {row['entity_identity']} "
            f"{row['field_name']}: candidate={row['candidate_value']} actual={row['actual_value']}"
        )
        if len(lines) == 20:
            break
    return lines


def _summary_text() -> str:
    first = GATE.first_divergence
    bucket = GATE.selected_bucket
    buyer_lines = []
    buyer_lines.append("  common_origin と after_timestep の buyer snapshot:")
    snapshot_requests = [(DECISION_TIMESTEP, PHASE_COMMON_ORIGIN)]
    timestep = DECISION_TIMESTEP
    while timestep <= CANDIDATE_REQUIRED_END:
        snapshot_requests.append((timestep, PHASE_AFTER_TIMESTEP))
        timestep = timestep + 1
    for timestep, phase in snapshot_requests:
        candidate_row = _vehicle_at(
            bucket.vehicle_rows,
            WORLD_CANDIDATE,
            timestep,
            phase,
            BUYER_NAME,
        )
        actual_row = _vehicle_at(
            GATE.actual_vehicle_rows,
            WORLD_ACTUAL,
            timestep,
            phase,
            BUYER_NAME,
        )
        candidate_link = None if candidate_row is None else candidate_row["current_link_name"]
        actual_link = None if actual_row is None else actual_row["current_link_name"]
        candidate_x = None if candidate_row is None else candidate_row["position_x"]
        actual_x = None if actual_row is None else actual_row["position_x"]
        candidate_speed = None if candidate_row is None else candidate_row["speed_v"]
        actual_speed = None if actual_row is None else actual_row["speed_v"]
        buyer_lines.append(
            f"  T={timestep} {phase}: candidate link={candidate_link} x={candidate_x} "
            f"v={candidate_speed}; actual link={actual_link} x={actual_x} v={actual_speed}"
        )
    after_text_parts = []
    for timestep in GATE.compared_after_timesteps:
        after_text_parts.append(str(timestep))
    after_text = ", ".join(after_text_parts)
    buyer_position = _first_buyer_position_difference()
    if buyer_position is None:
        buyer_position_text = (
            "7. buyerの位置差が最初に発生したafter_timestep: "
            "comparable after_timestep に buyer の current_link または position_x の "
            "dynamic divergence は記録されなかった。"
        )
        leading_limit = first["world_timestep"]
    else:
        buyer_position_text = (
            "7. buyerの位置差が最初に発生したafter_timestep: "
            f"T={buyer_position['world_timestep']} field={buyer_position['field_name']} "
            f"candidate={buyer_position['candidate_value']} actual={buyer_position['actual_value']}"
        )
        leading_limit = buyer_position["world_timestep"]
    leading_lines = _leading_dynamic_lines(leading_limit)
    if len(leading_lines) == 0:
        leading_text = "  この時刻までにVehicle順、速度、容量のdynamic divergenceは記録されなかった。"
    else:
        leading_text = "\n".join(leading_lines)
    decision_lines = []
    for row in GATE.decision_rows:
        if row["decision_timestep"] == DECISION_TIMESTEP:
            continue
        if (
            row["buyer_rank_changed"] is True
            or row["seller_rank_changed"] is True
            or row["inlink_vehicle_rank_changed"] is True
        ):
            decision_lines.append(
                f"  T={row['decision_timestep']} status={row['selection_status']} "
                f"buyer_rank_changed={row['buyer_rank_changed']} "
                f"seller_rank_changed={row['seller_rank_changed']} "
                f"inlink_changes={row['changed_inlink_visit_keys']}"
            )
    if len(decision_lines) == 0:
        decision_text = "T=601〜610でbuyer、seller、対象inlink上Visitのassigned rank変化は記録されなかった。"
    else:
        decision_text = "T=601以降のrank変化:\n" + "\n".join(decision_lines)
    if first["world_timestep"] == DECISION_TIMESTEP:
        decision_relation = (
            "正式な最初のdynamic divergenceはT=600 after_timestepにある。"
            "Actualのこの状態は、T=601のdriver入口で、T=600のdriver意思決定と"
            "そのtimestepのLink、Node、Vehicle更新が終わった後の状態として保存する。"
            "T=601以降の意思決定は、この最初の差より後である。"
        )
    else:
        decision_relation = (
            f"正式な最初のdynamic divergenceはT={first['world_timestep']} after_timestepにある。"
            "それより前のT=601以降の意思決定は、下のrank変化として残る。"
            "rank変化が無い場合、新規意思決定をこの差の直接原因としては記録しない。"
        )
    lines = [
        "T=600 northeast candidate/actual paired trace",
        "反実仮想比較は実装していない。",
        "",
        "1. common_origin比較結果: 一致。",
        "   Candidateはreal_world.copy()完了直後、binding進路適用前。",
        "   ActualはT=600のdriver入口で、original_driverを呼ぶ前。",
        f"2. 共通起点で比較した数: Vehicle {GATE.common_origin_compared_vehicle_count}、"
        f"Node {GATE.common_origin_compared_node_count}、"
        f"Link {GATE.common_origin_compared_link_count}。",
        "3. unexpected_common_origin_difference: 0件。",
        "4. before_node_passage と after_node_passage は参考phase。"
        "分類は non_comparable_intermediate_phase であり、first divergence には使わない。",
        f"5. 正式比較した after_timestep: {after_text}。",
        "   Candidate T の after_timestep と Actual T の after_timestep だけを時間発展の比較に使う。",
        "6. 正式な first dynamic divergence:",
        f"   T={first['world_timestep']} phase={first['phase']} "
        f"{first['entity_kind']} {first['entity_identity']} "
        f"field={first['field_name']}",
        f"   candidate={first['candidate_value']}",
        f"   actual={first['actual_value']}",
        f"   classification={first['classification']}",
        f"   preceding_step={first['preceding_production_step']}",
        buyer_position_text,
        "8. buyer到着差へ至るVehicle順・速度・容量差:",
        leading_text,
        "9. T=601以降の実World意思決定との関係:",
        decision_relation,
        decision_text,
        "10. seller clearance遅延への波及: "
        "Candidate seller通過はT=608、Actual seller通過はT=609としてruntimeで照合する。"
        "上に記録した順、速度、容量の差がsellerのclearanceを遅らせたかどうかは、"
        "このsnapshotだけでは未確定。",
        "11. 観測だけで原因を説明できるか: 未確定。"
        "正式な最初のdynamic divergenceのfieldは上で特定できる。"
        "その差がbuyerの到着差とsellerのclearance遅延の両方を一意に説明するかは未確定。",
        "12. 反実仮想比較が必要か: 必要。反実仮想比較は実装していない。",
        "",
        "buyer snapshot:",
    ]
    lines.extend(buyer_lines)
    return "\n".join(lines) + "\n"


VEHICLE_COLUMNS = (
    "world_kind",
    "tvt_decision_timestep",
    "world_timestep",
    "phase",
    "node_name",
    "candidate_identity",
    "candidate_evaluation_index",
    "real_vehicle_name",
    "local_vehicle_name",
    "real_vehicle_id",
    "observed_vehicle_id",
    "visit_id",
    "visit_key",
    "trade_role",
    "local_scope",
    "correspondence_status",
    "in_compared_set",
    "current_link_name",
    "on_target_inlink",
    "on_target_outlink",
    "position_x",
    "x_old",
    "x_next",
    "speed_v",
    "move_remain",
    "lane",
    "physical_index",
    "link_vehicle_count",
    "is_physical_head",
    "leader_vehicle_name",
    "follower_vehicle_name",
    "in_incoming",
    "incoming_index",
    "state",
    "mode",
    "assigned_rank",
    "binding_rank",
    "baseline_local_rank",
    "post_trade_local_rank",
    "actual_passage_rank",
    "already_passed_target_node",
    "passage_timestep",
    "arrival_timestep",
    "arrival_tiebreaker",
    "live_route_next_link_name",
    "formal_route_next_link_name",
    "predicted_route_next_link_name",
    "actual_route_next_link_name",
    "acceptable_outlink_names",
    "route_origin",
    "inlink_capacity_out_remain",
    "node_flow_capacity_remain",
    "live_outlink_capacity_in_remain",
    "live_outlink_entry_open",
    "predicted_outlink_capacity_in_remain",
    "predicted_outlink_entry_open",
    "actual_side_outlink_capacity_in_remain",
    "actual_side_outlink_entry_open",
    "last_order_control_inlink_name",
    "last_order_control_entry_timestep",
    "clearance_timesteps",
    "clearance_satisfied",
    "passage_attempted",
    "passage_succeeded",
    "temporary_skip_reason",
    "stop_reason",
    "earlier_attempted_visit_keys",
    "earlier_passed_visit_keys",
)

NODE_COLUMNS = (
    "world_kind",
    "tvt_decision_timestep",
    "world_timestep",
    "phase",
    "node_name",
    "candidate_identity",
    "candidate_evaluation_index",
    "flow_capacity_remain",
    "last_order_control_inlink_name",
    "last_order_control_entry_timestep",
    "clearance_timesteps",
    "incoming_vehicle_count",
    "incoming_vehicle_order",
    "passed_visit_keys_this_timestep",
)

LINK_COLUMNS = (
    "world_kind",
    "tvt_decision_timestep",
    "world_timestep",
    "phase",
    "node_name",
    "candidate_identity",
    "candidate_evaluation_index",
    "link_role",
    "link_name",
    "capacity_in_remain",
    "capacity_out_remain",
    "vehicle_count",
    "vehicle_order",
    "position_order",
    "entrance_vehicle_name",
    "entry_open",
    "cum_arrival_latest",
    "cum_departure_latest",
)

PASSAGE_COLUMNS = (
    "world_kind",
    "tvt_decision_timestep",
    "world_timestep",
    "node_name",
    "candidate_identity",
    "candidate_evaluation_index",
    "real_vehicle_name",
    "visit_key",
    "attempted",
    "passed",
    "reason",
    "stop_reason",
    "route_next_link_name",
    "inlink_name",
    "earlier_attempted_visit_keys",
    "earlier_passed_visit_keys",
    "assigned_rank",
    "actual_passage_rank",
)

DECISION_COLUMNS = (
    "decision_timestep",
    "node_name",
    "selected_candidate_present",
    "candidate_identity",
    "selection_status",
    "buyer_assigned_rank_before",
    "buyer_assigned_rank_after",
    "buyer_rank_changed",
    "buyer_formal_route_before",
    "buyer_formal_route_after",
    "buyer_formal_route_changed",
    "seller_assigned_rank_before",
    "seller_assigned_rank_after",
    "seller_rank_changed",
    "seller_formal_route_before",
    "seller_formal_route_after",
    "seller_formal_route_changed",
    "inlink_vehicle_rank_changed",
    "changed_inlink_visit_keys",
    "inlink_visit_keys_before_decision",
    "inlink_visit_keys_after_decision",
)

DIFFERENCE_COLUMNS = (
    "world_timestep",
    "phase",
    "entity_kind",
    "entity_identity",
    "field_name",
    "candidate_value",
    "actual_value",
    "classification",
    "preceding_production_step",
    "phase_comparability",
    "excluded_from_first_divergence",
    "exclusion_reason",
)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cells = {}
            for column in columns:
                cells[column] = _csv_cell(row.get(column))
            writer.writerow(cells)


def _reject_duplicate_snapshots(rows, key_fields) -> None:
    seen = set()
    for row in rows:
        key = []
        for field in key_fields:
            key.append(row.get(field))
        key_tuple = tuple(key)
        if key_tuple in seen:
            raise RuntimeError(f"Duplicate snapshot {key_tuple!r}.")
        seen.add(key_tuple)


def _write_outputs(summary_text: str) -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    if OUTPUT_DIR == four_cross_trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory is the trial output directory.")
    bucket = GATE.selected_bucket
    vehicle_rows = []
    for row in bucket.vehicle_rows:
        vehicle_rows.append(row)
    for row in GATE.actual_vehicle_rows:
        vehicle_rows.append(row)
    node_rows = []
    for row in bucket.node_rows:
        node_rows.append(row)
    for row in GATE.actual_node_rows:
        node_rows.append(row)
    link_rows = []
    for row in bucket.link_rows:
        link_rows.append(row)
    for row in GATE.actual_link_rows:
        link_rows.append(row)
    passage_rows = []
    for row in bucket.passage_rows:
        row["candidate_identity"] = bucket.candidate_identity
        row["candidate_evaluation_index"] = bucket.evaluation_index
        passage_rows.append(row)
    for row in GATE.actual_passage_rows:
        row["candidate_identity"] = bucket.candidate_identity
        row["candidate_evaluation_index"] = bucket.evaluation_index
        passage_rows.append(row)
    _reject_duplicate_snapshots(
        vehicle_rows,
        ("world_kind", "world_timestep", "phase", "local_vehicle_name"),
    )
    _reject_duplicate_snapshots(node_rows, ("world_kind", "world_timestep", "phase"))
    _reject_duplicate_snapshots(link_rows, ("world_kind", "world_timestep", "phase", "link_name"))
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    _write_csv(OUTPUT_DIR / VEHICLE_CSV, VEHICLE_COLUMNS, vehicle_rows)
    _write_csv(OUTPUT_DIR / NODE_CSV, NODE_COLUMNS, node_rows)
    _write_csv(OUTPUT_DIR / LINK_CSV, LINK_COLUMNS, link_rows)
    _write_csv(OUTPUT_DIR / PASSAGE_CSV, PASSAGE_COLUMNS, passage_rows)
    _write_csv(OUTPUT_DIR / DECISION_CSV, DECISION_COLUMNS, GATE.decision_rows)
    _write_csv(OUTPUT_DIR / DIFFERENCE_CSV, DIFFERENCE_COLUMNS, GATE.difference_rows)
    (OUTPUT_DIR / SUMMARY_NAME).write_text(summary_text, encoding="utf-8")
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "diagnostic_script_name": DIAGNOSTIC_SCRIPT_NAME,
        "target_node_name": TARGET_NODE_NAME,
        "decision_timestep": DECISION_TIMESTEP,
        "trace_start": TRACE_START,
        "trace_end": TRACE_END,
        "candidate_identity": bucket.candidate_identity,
        "candidate_evaluation_index": bucket.evaluation_index,
        "output_filenames": list(OUTPUT_FILE_NAMES),
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "counterfactual_route_comparison": "not_implemented",
        "first_divergence_timestep": GATE.first_divergence["world_timestep"],
        "first_divergence_phase": GATE.first_divergence["phase"],
        "first_divergence_field": GATE.first_divergence["field_name"],
        "completion_status": "completed",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "generated_at_meaning": "file write time, not a simulation timestep",
    }
    (OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected_names = set(OUTPUT_FILE_NAMES)
    for path in OUTPUT_DIR.iterdir():
        if path.name not in expected_names:
            raise RuntimeError(f"Unexpected output file {path.name}.")


def _validate_runtime(world) -> None:
    if world.T != EXPECTED_WORLD_T:
        raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T}.")
    evaluation = four_cross_trial.verify_evaluation_end(world)
    if evaluation["world_t_ok"] is not True:
        raise RuntimeError("Evaluation-end check did not pass.")
    if GATE.selected_bucket is None:
        raise RuntimeError("Selected candidate trace is missing.")
    if GATE.common_origin_actual_capture_count != 1:
        raise RuntimeError("T=600 Actual common origin was not captured once at driver entry.")
    if GATE.selected_bucket.common_origin_captured is not True:
        raise RuntimeError("Selected candidate common origin was not captured once after copy.")
    if GATE.selected_bucket.local_world_id == id(world):
        raise RuntimeError("Selected candidate trace used the real World object.")
    bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
    _require_research(bundle)
    _attach_actual_ranks(world)
    _require_phase_coverage(GATE.selected_bucket.node_rows, WORLD_CANDIDATE, TRACE_START, CANDIDATE_REQUIRED_END)
    _require_phase_coverage(GATE.actual_node_rows, WORLD_ACTUAL, TRACE_START, TRACE_END)
    _require_passage_event(WORLD_CANDIDATE, BUYER_NAME, BUYER_CANDIDATE_PASSAGE)
    _require_passage_event(WORLD_CANDIDATE, SELLER_NAME, SELLER_CANDIDATE_PASSAGE)
    _require_passage_event(WORLD_ACTUAL, BUYER_NAME, BUYER_ACTUAL_PASSAGE)
    _require_passage_event(WORLD_ACTUAL, SELLER_NAME, SELLER_ACTUAL_PASSAGE)
    _compare()


def _reset_gate() -> None:
    GATE.next_evaluation_index = 0
    GATE.buckets_by_world_id = {}
    GATE.selected_bucket = None
    GATE.actual_vehicle_rows = []
    GATE.actual_node_rows = []
    GATE.actual_link_rows = []
    GATE.actual_passage_rows = []
    GATE.decision_rows = []
    GATE.difference_rows = []
    GATE.first_divergence = None
    GATE.expected_initial_rows = []
    GATE.unexpected_initial_rows = []
    GATE.unexpected_common_origin_rows = []
    GATE.common_origin_actual_vehicle_raw = []
    GATE.common_origin_actual_node_raw = []
    GATE.common_origin_actual_link_raw = []
    GATE.common_origin_actual_capture_count = 0
    GATE.common_origin_compared_vehicle_count = 0
    GATE.common_origin_compared_node_count = 0
    GATE.common_origin_compared_link_count = 0
    GATE.compared_after_timesteps = []


def main() -> int:
    original_python_recursion_limit = sys.getrecursionlimit()
    _reset_gate()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if original_python_recursion_limit < four_cross_trial.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(four_cross_trial.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_trial_world()
        install_paired_hooks(world)
        four_cross_trial.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            four_cross_trial.restore_real_world_spillback_observation()
            restore_paired_hooks()
        _validate_runtime(world)
        _write_outputs(_summary_text())
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        four_cross_trial.restore_real_world_spillback_observation()
        restore_paired_hooks()
        sys.setrecursionlimit(original_python_recursion_limit)


def _function_by_name(tree, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Function {name} is missing.")


def _call_names(function_node) -> list[str]:
    names = []
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                names.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                names.append(node.func.id)
    return names


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    for module_name in imported:
        if module_name in ("subprocess", "shutil", "git"):
            raise RuntimeError(f"Diagnostic imports {module_name}.")
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
            if node.func.attr == "main":
                raise RuntimeError("Diagnostic calls a main function.")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
    for name in ("system", "rmtree", "unlink", "rmdir", "eval", "exec"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr in (
                "route_next_link",
                "flow_capacity_remain",
                "capacity_out_remain",
                "capacity_in_remain",
                "rng",
                "x",
                "v",
                "state",
                "mode",
                "assigned_rank",
            ):
                raise RuntimeError(f"Diagnostic assigns {target.attr}.")
    if tuple(OUTPUT_FILE_NAMES) != (
        "paired_vehicle_snapshots.csv",
        "paired_node_snapshots.csv",
        "paired_link_snapshots.csv",
        "paired_passage_events.csv",
        "paired_decision_events.csv",
        "paired_differences.csv",
        "first_divergence_summary.txt",
        "manifest.json",
    ):
        raise RuntimeError("Output filenames are not the fixed eight files.")
    if "反実仮想比較は実装していない" not in source:
        raise RuntimeError("Counterfactual comparison is not marked unimplemented.")
    if "GATE.real_world" not in source:
        raise RuntimeError("Real World identity check is missing.")
    if "local_state.local_world is GATE.real_world" not in source:
        raise RuntimeError("Candidate World is not distinguished from the real World.")
    main_function = _function_by_name(tree, "main")
    finally_count = 0
    for node in ast.walk(main_function):
        if isinstance(node, ast.Try) and len(node.finalbody) > 0:
            finally_count = finally_count + 1
    if finally_count < 2:
        raise RuntimeError("main() does not restore hooks in finally.")
    main_called = _call_names(main_function)
    if "restore_paired_hooks" not in main_called:
        raise RuntimeError("main() does not restore paired hooks.")
    if "restore_real_world_spillback_observation" not in main_called:
        raise RuntimeError("main() does not restore spillback observation.")
    for wrapper_name in (
        "wrapped_build_local_state",
        "wrapped_run",
        "wrapped_one_timestep",
        "wrapped_scan",
        "wrapped_advance",
        "wrapped_driver",
        "wrapped_transfer",
        "wrapped_move",
    ):
        wrapper = _function_by_name(tree, wrapper_name)
        original_calls = 0
        for node in ast.walk(wrapper):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("original_"):
                    original_calls = original_calls + 1
        if wrapper_name == "wrapped_driver":
            if original_calls != 2:
                raise RuntimeError("wrapped_driver does not call the original once per branch.")
        elif original_calls != 1:
            raise RuntimeError(f"{wrapper_name} does not call the original once.")
    advance_wrapper = _function_by_name(tree, "wrapped_advance")
    advance_arg_names = [arg.arg for arg in advance_wrapper.args.args]
    if advance_arg_names != [
        "local_vehicle_advance_state",
        "binding_transfer_scan_result",
    ]:
        raise RuntimeError("wrapped_advance argument names do not match production.")
    original_advance_two_args = False
    for node in ast.walk(advance_wrapper):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "original_advance":
            continue
        if len(node.args) != 2:
            raise RuntimeError("GATE.original_advance is not called with two arguments.")
        original_advance_two_args = True
    if original_advance_two_args is not True:
        raise RuntimeError("wrapped_advance does not forward to GATE.original_advance.")
    selection_helper = _function_by_name(tree, "_selection_for_northeast")
    selection_source = ast.get_source_segment(source, selection_helper)
    if selection_source is None:
        raise RuntimeError("_selection_for_northeast source segment is missing.")
    if "final_consistency_validation_set_result" not in selection_source:
        raise RuntimeError(
            "_selection_for_northeast does not use final_consistency_validation_set_result."
        )
    if "validation_result" in selection_source:
        raise RuntimeError("_selection_for_northeast references validation_result.")
    for node in ast.walk(selection_helper):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr != "validation_result":
            continue
        raise RuntimeError(
            "_selection_for_northeast uses a validation_result attribute at runtime."
        )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "build_tvt_mp_candidate_local_state":
            raise RuntimeError("Diagnostic calls build_tvt_mp_candidate_local_state again.")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "build_tvt_mp_candidate_local_state":
            raise RuntimeError("Diagnostic calls build_tvt_mp_candidate_local_state again.")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "copy":
            raise RuntimeError("Diagnostic calls copy().")
    build_wrapper = _function_by_name(tree, "wrapped_build_local_state")
    build_arg_names = [arg.arg for arg in build_wrapper.args.args]
    if build_arg_names != ["real_W", "binding_rank_sequence"]:
        raise RuntimeError("wrapped_build_local_state argument names do not match production.")
    build_source = ast.get_source_segment(source, build_wrapper)
    if build_source is None:
        raise RuntimeError("wrapped_build_local_state source segment is missing.")
    original_build_at = build_source.find("GATE.original_build(real_W, binding_rank_sequence)")
    capture_at = build_source.find("_capture_tables(")
    if original_build_at < 0 or capture_at < 0 or original_build_at > capture_at:
        raise RuntimeError("Candidate common origin is not saved after the original build call.")
    driver_wrapper = _function_by_name(tree, "wrapped_driver")
    driver_source = ast.get_source_segment(source, driver_wrapper)
    if driver_source is None:
        raise RuntimeError("wrapped_driver source segment is missing.")
    raw_at = driver_source.find("_capture_actual_common_origin_raw(world)")
    original_driver_at = driver_source.find("result = GATE.original_driver(world)")
    if raw_at < 0 or original_driver_at < 0 or raw_at > original_driver_at:
        raise RuntimeError("Actual common origin is not saved before the T=600 original driver call.")
    restore_source = ast.get_source_segment(source, _function_by_name(tree, "restore_paired_hooks"))
    if restore_source is None or "build_tvt_mp_candidate_local_state = GATE.original_build" not in restore_source:
        raise RuntimeError("restore_paired_hooks does not restore the candidate build function.")
    raw_function = _function_by_name(tree, "_capture_actual_common_origin_raw")
    raw_source = ast.get_source_segment(source, raw_function)
    if raw_source is None or "_freeze_row_list" not in raw_source:
        raise RuntimeError("Actual common origin temporary snapshot is not frozen.")
    if "cannot store a live object" not in source:
        raise RuntimeError("Live-object rejection for the common origin snapshot is missing.")
    order_helper = _function_by_name(tree, "_order_dependent_field_is_comparable")
    order_source = ast.get_source_segment(source, order_helper)
    if order_source is None or "link_vehicle_orders_match" not in order_source or "physical_index" not in order_source:
        raise RuntimeError("physical_index is not gated on matching link vehicle sets.")
    field_decision = ast.get_source_segment(source, _function_by_name(tree, "_vehicle_field_decision"))
    if field_decision is None or "_order_dependent_field_is_comparable" not in field_decision:
        raise RuntimeError("Vehicle comparison does not check link vehicle set agreement.")
    if "expected_binding_route_difference" not in field_decision or "True" not in field_decision:
        raise RuntimeError("Binding route differences are not excluded from first divergence.")
    reference_source = ast.get_source_segment(source, _function_by_name(tree, "_reference_decision"))
    if reference_source is None or "non_comparable_intermediate_phase" not in reference_source:
        raise RuntimeError("Reference phases are not classified as non-comparable.")
    select_source = ast.get_source_segment(source, _function_by_name(tree, "_select_first_divergence"))
    if select_source is None or "COMPARABLE_AFTER" not in select_source or "dynamic_divergence" not in select_source:
        raise RuntimeError("First divergence is not limited to comparable after_timestep.")
    if "excluded_from_first_divergence" not in source:
        raise RuntimeError("Difference rows do not record first-divergence exclusion.")
    print("static contract ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
    else:
        raise SystemExit(main())
