"""
Read-only real-world trace for the T=600 northeast_intersection trade whose
Candidate P and Actual P differ by one timestep.

One 600-vehicle simulation is run. Production passage checks are called once.
Their return values are recorded. This script does not change routes, ranks,
capacity, or RNG, and it does not run a counterfactual route comparison.
"""

from __future__ import annotations

import ast
import csv
import datetime
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import uxsim.order_control_tvt_mp_physical_transfer as physical_transfer_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualNodePassageRecord,
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
        "600_vehicle_eval_900_timestep_seed_1_t600_route_divergence_trace"
    )
)

NODE_TRACE_NAME = "t600_node_timestep_trace.csv"
TARGET_TRACE_NAME = "t600_target_visit_trace.csv"
PASSAGE_EVENTS_NAME = "t600_passage_events.csv"
ROUTE_EVENTS_NAME = "t600_route_change_events.csv"
CAUSE_SUMMARY_NAME = "t600_direct_cause_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    NODE_TRACE_NAME,
    TARGET_TRACE_NAME,
    PASSAGE_EVENTS_NAME,
    ROUTE_EVENTS_NAME,
    CAUSE_SUMMARY_NAME,
    MANIFEST_NAME,
)

TARGET_NODE_NAME = "northeast_intersection"
TRACE_START = 598
TRACE_END = 610
EXPECTED_WORLD_T = 900

BUYER_NAME = "veh_ne_wn_base_034"
BUYER_VISIT_ID = 1
SELLER_NAME = "veh_wn_en_base_042"
SELLER_VISIT_ID = 2
DECISION_TIMESTEP = 600

BUYER_PREDICTED_ROUTE = "northeast_intersection_to_southeast_intersection"
BUYER_ACTUAL_ROUTE = "northeast_intersection_to_northwest_intersection"
SELLER_ROUTE = "northeast_intersection_to_east_north_od"

BUYER_BASELINE_PASSAGE = 609
BUYER_CANDIDATE_PASSAGE = 606
BUYER_ACTUAL_PASSAGE = 607
BUYER_ASSIGNED_RANK = 208
BUYER_ACTUAL_RANK = 208
SELLER_BASELINE_PASSAGE = 607
SELLER_CANDIDATE_PASSAGE = 608
SELLER_ACTUAL_PASSAGE = 609
SELLER_ASSIGNED_RANK = 209
SELLER_ACTUAL_RANK = 209

REASON_NOT_IN_INCOMING = "not_in_incoming"
REASON_NOT_PHYSICAL_HEAD = "not_physical_head"
REASON_CLEARANCE_UNMET = "clearance_unmet"
REASON_NOT_REACHED = "not_reached_because_clearance_stop"
REASON_PASSED = "passed"
REASON_NOT_CANDIDATE = "not_a_confirmed_passage_candidate"


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_transfer = None
        self.original_try = None
        self.original_head = None
        self.original_first = None
        self.original_clearance = None
        self.original_move = None
        self.original_route_choice = None
        self.original_commit_history = None
        self.last_real_move = None
        self.attempt_events = []
        self.index_by_vehicle_id = {}
        self.pending_vehicle_id = None
        self.node_rows = []
        self.target_rows = []
        self.passage_rows = []
        self.route_rows = []
        self.foreign_record_count = 0
        self.seen_timesteps = []


GATE = _Gate()


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _visit_text(vehicle_name, visit_id) -> str:
    return f"{vehicle_name}:{visit_id}"


def _plain_visit_from_vehicle(vehicle):
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        return None
    return (vehicle.name, visit_id)


def _is_real_target_node(node) -> bool:
    if GATE.real_world is None:
        return False
    if node.W is not GATE.real_world:
        return False
    collector = getattr(node.W, "_order_control_baseline_collector", None)
    if collector is not None:
        return False
    if node.name != TARGET_NODE_NAME:
        return False
    timestep = node.W.T
    if type(timestep) is not int:
        return False
    if timestep < TRACE_START or timestep > TRACE_END:
        return False
    return True


def _is_real_target_vehicle(vehicle) -> bool:
    if GATE.real_world is None:
        return False
    if vehicle.W is not GATE.real_world:
        return False
    collector = getattr(vehicle.W, "_order_control_baseline_collector", None)
    if collector is not None:
        return False
    if vehicle.name != BUYER_NAME and vehicle.name != SELLER_NAME:
        return False
    timestep = vehicle.W.T
    if type(timestep) is not int:
        return False
    if timestep < TRACE_START or timestep > TRACE_END:
        return False
    return True


def _read_vehicle_route_next_link(vehicle):
    """Read-only live route; attribute may not exist yet on some Vehicles."""
    return getattr(vehicle, "route_next_link", None)


def _link_name(link):
    if link is None:
        return None
    return link.name


def _entry_open(link, world):
    """Read the same entry comparison production uses. Do not move vehicles."""
    if link is None:
        return None
    if len(link.vehicles) < link.number_of_lanes:
        return True
    entrance_vehicle = link.vehicles[-link.number_of_lanes]
    entry_gap = link.delta_per_lane * world.DELTAN
    if entrance_vehicle.x <= entry_gap:
        return False
    return True


def _entrance_name(link):
    if link is None:
        return None
    if len(link.vehicles) < link.number_of_lanes:
        return None
    return link.vehicles[-link.number_of_lanes].name


def _entrance_x(link):
    if link is None:
        return None
    if len(link.vehicles) < link.number_of_lanes:
        return None
    return link.vehicles[-link.number_of_lanes].x


def _rank_state(world):
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return None
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return None
    return rank_state


def _assigned_rank(world, visit_key):
    rank_state = _rank_state(world)
    if rank_state is None:
        return None
    return rank_state.assigned_rank(visit_key)


def _formal_route(world, visit_key):
    rank_state = _rank_state(world)
    if rank_state is None:
        return None
    return rank_state.formal_route_next_link_name(visit_key)


def _append_event(vehicle, inlink, outlink, reason, extra, visit_pair=None) -> None:
    if vehicle.W is not GATE.real_world:
        GATE.foreign_record_count = GATE.foreign_record_count + 1
        return
    if visit_pair is None:
        visit_pair = _plain_visit_from_vehicle(vehicle)
    if visit_pair is None:
        visit_text = None
        visit_id = None
    else:
        visit_text = _visit_text(visit_pair[0], visit_pair[1])
        visit_id = visit_pair[1]
    event = {
        "world_timestep": vehicle.W.T,
        "vehicle_object_id": id(vehicle),
        "vehicle_name": vehicle.name,
        "visit_id": visit_id,
        "visit_key": visit_text,
        "candidate_index": GATE.index_by_vehicle_id.get(id(vehicle)),
        "reason": reason,
        "inlink_name": _link_name(inlink),
        "live_route_next_link_name": _link_name(outlink),
        "assigned_rank": _assigned_rank(vehicle.W, visit_pair) if visit_pair is not None else None,
    }
    for key in extra:
        event[key] = extra[key]
    GATE.attempt_events.append(event)


def wrapped_transfer(node):
    tracing = _is_real_target_node(node)
    if tracing is True:
        GATE.attempt_events = []
        GATE.index_by_vehicle_id = {}
        GATE.pending_vehicle_id = None
        GATE.last_real_move = None
        pre_node = _read_node_pre_state(node)
        pre_targets = _read_target_pre_states(node)
    result = GATE.original_transfer(node)
    if tracing is True:
        _store_timestep(node, pre_node, pre_targets, GATE.attempt_events)
    return result


def wrapped_try(node, confirmed_candidates):
    if _is_real_target_node(node) is True:
        index = 0
        for candidate in confirmed_candidates:
            index = index + 1
            GATE.index_by_vehicle_id[id(candidate.vehicle)] = index
    result = GATE.original_try(node, confirmed_candidates)
    if _is_real_target_node(node) is True:
        _annotate_candidates_without_terminal_event(confirmed_candidates)
    return result


def wrapped_head(vehicle, inlink):
    skip = GATE.original_head(vehicle, inlink)
    if _is_real_target_node(inlink.end_node) is True:
        if skip is True:
            GATE.pending_vehicle_id = None
            route_next_link = _read_vehicle_route_next_link(vehicle)
            _append_event(
                vehicle,
                inlink,
                route_next_link,
                REASON_NOT_PHYSICAL_HEAD,
                _physical_snapshot(vehicle.W, inlink, route_next_link),
            )
        else:
            GATE.pending_vehicle_id = id(vehicle)
    return skip


def wrapped_clearance(node, vehicle, inlink):
    blocked = GATE.original_clearance(node, vehicle, inlink)
    if _is_real_target_node(node) is True and blocked is True:
        GATE.pending_vehicle_id = None
        route_next_link = _read_vehicle_route_next_link(vehicle)
        extra = _physical_snapshot(node.W, inlink, route_next_link)
        extra["clearance_last_inlink_name"] = _link_name(node.last_order_control_inlink)
        extra["clearance_last_entry_timestep"] = node.last_order_control_entry_timestep
        extra["clearance_timesteps"] = node.order_control_clearance_timesteps
        _append_event(vehicle, inlink, route_next_link, REASON_CLEARANCE_UNMET, extra)
    return blocked


def wrapped_first(node, inlink, outlink):
    extra = _physical_snapshot(node.W, inlink, outlink)
    shortage = GATE.original_first(node, inlink, outlink)
    if _is_real_target_node(node) is True and shortage is not None:
        vehicle = _vehicle_by_id(node, GATE.pending_vehicle_id)
        if vehicle is not None:
            _append_event(vehicle, inlink, outlink, shortage, extra)
        GATE.pending_vehicle_id = None
    return shortage


def wrapped_move(node, vehicle, inlink, outlink):
    extra = _physical_snapshot(node.W, inlink, outlink)
    extra["clearance_last_inlink_name_before_move"] = _link_name(node.last_order_control_inlink)
    extra["clearance_last_entry_timestep_before_move"] = node.last_order_control_entry_timestep
    visit_pair_before_move = _plain_visit_from_vehicle(vehicle)
    result = GATE.original_move(node, vehicle, inlink, outlink)
    if _is_real_target_node(node) is True:
        if visit_pair_before_move is None:
            visit_text = None
        else:
            visit_text = _visit_text(visit_pair_before_move[0], visit_pair_before_move[1])
        GATE.last_real_move = {
            "node": node,
            "visit_text": visit_text,
            "world_timestep": node.W.T,
        }
        _append_event(
            vehicle,
            inlink,
            outlink,
            REASON_PASSED,
            extra,
            visit_pair_before_move,
        )
        GATE.passage_rows.append(
            _passage_row_from_move(
                node,
                vehicle,
                inlink,
                outlink,
                extra,
                visit_pair_before_move,
            )
        )
        GATE.pending_vehicle_id = None
    return result


def wrapped_commit_history(prepared_update):
    move = GATE.last_real_move
    if move is not None and getattr(prepared_update, "node_name", None) == TARGET_NODE_NAME:
        node = move["node"]
        if node.W is GATE.real_world and node.name == TARGET_NODE_NAME:
            _stamp_clearance_after_move(move, node)
        GATE.last_real_move = None
    return GATE.original_commit_history(prepared_update)


def _stamp_clearance_after_move(move, node) -> None:
    after_name = _link_name(node.last_order_control_inlink)
    after_timestep = node.last_order_control_entry_timestep
    for event in GATE.attempt_events:
        if event["reason"] != REASON_PASSED:
            continue
        if event["visit_key"] != move["visit_text"]:
            continue
        if event["world_timestep"] != move["world_timestep"]:
            continue
        event["clearance_last_inlink_name_after_move"] = after_name
        event["clearance_last_entry_timestep_after_move"] = after_timestep
    for row in GATE.passage_rows:
        if row["visit_key"] != move["visit_text"]:
            continue
        if row["world_timestep"] != move["world_timestep"]:
            continue
        row["clearance_last_inlink_name_after_move"] = after_name
        row["clearance_last_entry_timestep_after_move"] = after_timestep


def wrapped_route_choice(vehicle):
    if _is_real_target_vehicle(vehicle) is not True:
        return GATE.original_route_choice(vehicle)

    before_link = getattr(vehicle, "route_next_link", None)
    before_name = _link_name(before_link)

    result = GATE.original_route_choice(vehicle)

    after_link = getattr(vehicle, "route_next_link", None)
    after_name = _link_name(after_link)

    if before_name == after_name:
        return result
    end_node = None
    if vehicle.link is not None:
        end_node = vehicle.link.end_node
    GATE.route_rows.append(
        {
            "world_timestep": vehicle.W.T,
            "vehicle_name": vehicle.name,
            "visit_id": _visit_id_or_none(vehicle),
            "visit_key": _visit_text_or_none(vehicle),
            "previous_live_route_next_link_name": before_name,
            "new_live_route_next_link_name": after_name,
            "previous_outlink_capacity_in_remain": _capacity_in(before_link),
            "new_outlink_capacity_in_remain": _capacity_in(after_link),
            "previous_outlink_entry_open": _entry_open(before_link, vehicle.W),
            "new_outlink_entry_open": _entry_open(after_link, vehicle.W),
            "previous_entrance_vehicle_name": _entrance_name(before_link),
            "new_entrance_vehicle_name": _entrance_name(after_link),
            "end_node_name": None if end_node is None else end_node.name,
        }
    )
    return result


def _visit_id_or_none(vehicle):
    pair = _plain_visit_from_vehicle(vehicle)
    if pair is None:
        return None
    return pair[1]


def _visit_text_or_none(vehicle):
    pair = _plain_visit_from_vehicle(vehicle)
    if pair is None:
        return None
    return _visit_text(pair[0], pair[1])


def _capacity_in(link):
    if link is None:
        return None
    return link.capacity_in_remain


def _vehicle_by_id(node, vehicle_id):
    if vehicle_id is None:
        return None
    for vehicle in node.incoming_vehicles:
        if id(vehicle) == vehicle_id:
            return vehicle
    for link in node.inlinks.values():
        for vehicle in link.vehicles:
            if id(vehicle) == vehicle_id:
                return vehicle
    return None


def _physical_snapshot(world, inlink, outlink) -> dict:
    flow_remain = None
    if inlink is not None:
        flow_remain = inlink.end_node.flow_capacity_remain
    return {
        "inlink_capacity_out_remain": None if inlink is None else inlink.capacity_out_remain,
        "node_flow_capacity_remain": flow_remain,
        "selected_outlink_capacity_in_remain": _capacity_in(outlink),
        "selected_outlink_entry_open": _entry_open(outlink, world),
        "selected_outlink_entrance_vehicle_name": _entrance_name(outlink),
        "selected_outlink_entrance_x": _entrance_x(outlink),
        "selected_outlink_vehicle_count": None if outlink is None else len(outlink.vehicles),
    }


def _annotate_candidates_without_terminal_event(confirmed_candidates) -> None:
    logged_ids = set()
    stopped_index = None
    for event in GATE.attempt_events:
        logged_ids.add(event["vehicle_object_id"])
        if event["reason"] == REASON_CLEARANCE_UNMET:
            stopped_index = event["candidate_index"]
    for candidate in confirmed_candidates:
        vehicle_id = id(candidate.vehicle)
        if vehicle_id in logged_ids:
            continue
        index = GATE.index_by_vehicle_id.get(vehicle_id)
        if stopped_index is not None and index is not None and index > stopped_index:
            reason = REASON_NOT_REACHED
        else:
            reason = REASON_NOT_IN_INCOMING
        _append_event(
            candidate.vehicle,
            candidate.inlink,
            candidate.outlink,
            reason,
            _physical_snapshot(candidate.vehicle.W, candidate.inlink, candidate.outlink),
        )


def _read_target_vehicle_pre(node, vehicle_name, visit_id) -> dict:
    vehicle = node.W.VEHICLES.get(vehicle_name)
    pre = {
        "current_link_name": None,
        "position_x": None,
        "live_route_next_link_name": None,
        "in_incoming": False,
        "in_inlink_vehicles": False,
        "is_head": False,
        "on_this_visit": False,
    }
    if vehicle is None:
        return pre
    pre["current_link_name"] = _link_name(vehicle.link)
    pre["position_x"] = vehicle.x
    route_next_link = _read_vehicle_route_next_link(vehicle)
    pre["live_route_next_link_name"] = _link_name(route_next_link)
    pair = _plain_visit_from_vehicle(vehicle)
    pre["on_this_visit"] = pair == (vehicle_name, visit_id)
    if vehicle.link is not None and vehicle in vehicle.link.vehicles:
        pre["in_inlink_vehicles"] = True
        if len(vehicle.link.vehicles) > 0 and vehicle.link.vehicles[0] is vehicle:
            pre["is_head"] = True
    for incoming_vehicle in node.incoming_vehicles:
        if incoming_vehicle is vehicle and pre["on_this_visit"] is True:
            pre["in_incoming"] = True
    if pre["on_this_visit"] is not True:
        pre["in_inlink_vehicles"] = False
        pre["is_head"] = False
    return pre


def _read_target_pre_states(node) -> dict:
    return {
        "buyer": _read_target_vehicle_pre(node, BUYER_NAME, BUYER_VISIT_ID),
        "seller": _read_target_vehicle_pre(node, SELLER_NAME, SELLER_VISIT_ID),
        "buyer_predicted_outlink": _named_link_state(node, BUYER_PREDICTED_ROUTE),
        "buyer_actual_outlink": _named_link_state(node, BUYER_ACTUAL_ROUTE),
        "seller_outlink": _named_link_state(node, SELLER_ROUTE),
    }


def _read_node_pre_state(node) -> dict:
    incoming_parts = []
    for vehicle in node.incoming_vehicles:
        pair = _plain_visit_from_vehicle(vehicle)
        if pair is None:
            visit_text = ""
            assigned = None
        else:
            visit_text = _visit_text(pair[0], pair[1])
            assigned = _assigned_rank(node.W, pair)
        route_name = _link_name(_read_vehicle_route_next_link(vehicle))
        assigned_text = "" if assigned is None else str(assigned)
        incoming_parts.append(f"{visit_text}|rank={assigned_text}|route={route_name}")
    return {
        "incoming_vehicle_count": len(node.incoming_vehicles),
        "incoming_vehicle_order": "|".join(incoming_parts),
        "node_flow_capacity_remain": node.flow_capacity_remain,
        "last_order_control_inlink_name": _link_name(node.last_order_control_inlink),
        "last_order_control_entry_timestep": node.last_order_control_entry_timestep,
        "order_control_clearance_timesteps": node.order_control_clearance_timesteps,
    }


def _passage_row_from_move(node, vehicle, inlink, outlink, extra, pair) -> dict:
    if pair is None:
        visit_id = None
        visit_text = None
        assigned = None
    else:
        visit_id = pair[1]
        visit_text = _visit_text(pair[0], pair[1])
        assigned = _assigned_rank(node.W, pair)
    return {
        "world_timestep": node.W.T,
        "node_name": node.name,
        "vehicle_name": vehicle.name,
        "visit_id": visit_id,
        "visit_key": visit_text,
        "assigned_rank": assigned,
        "actual_node_passage_rank": None,
        "inlink_name": _link_name(inlink),
        "actual_route_next_link_name": _link_name(outlink),
        "candidate_index": GATE.index_by_vehicle_id.get(id(vehicle)),
        "consumed_node_or_outlink_before_target": None,
        "clearance_last_inlink_name_before_move": extra.get("clearance_last_inlink_name_before_move"),
        "clearance_last_entry_timestep_before_move": extra.get(
            "clearance_last_entry_timestep_before_move"
        ),
        "clearance_last_inlink_name_after_move": None,
        "clearance_last_entry_timestep_after_move": None,
    }


def _target_spec(role_name):
    if role_name == "buyer":
        return BUYER_NAME, BUYER_VISIT_ID, BUYER_PREDICTED_ROUTE
    return SELLER_NAME, SELLER_VISIT_ID, SELLER_ROUTE


def _terminal_event_for_visit(events, visit_text):
    found = None
    for event in events:
        if event["visit_key"] != visit_text:
            continue
        found = event
    return found


def _prior_visit_keys(events, candidate_index, success_only: bool) -> str:
    texts = []
    for event in events:
        other_index = event["candidate_index"]
        if other_index is None or candidate_index is None:
            continue
        if other_index >= candidate_index:
            continue
        if success_only is True and event["reason"] != REASON_PASSED:
            continue
        if event["visit_key"] is None:
            continue
        if event["visit_key"] in texts:
            continue
        texts.append(event["visit_key"])
    return "|".join(texts)


def _named_link_state(node, link_name):
    link = node.outlinks.get(link_name)
    if link is None:
        return None, None, None
    return link.capacity_in_remain, _entry_open(link, node.W), _entrance_name(link)


def _store_timestep(node, pre_node, pre_targets, events) -> None:
    timestep = node.W.T
    GATE.seen_timesteps.append(timestep)
    passed_keys = []
    for event in events:
        if event["reason"] == REASON_PASSED and event["visit_key"] is not None:
            passed_keys.append(event["visit_key"])
    node_row = {
        "world_timestep": timestep,
        "node_name": node.name,
        "node_flow_capacity_remain_before": pre_node["node_flow_capacity_remain"],
        "node_flow_capacity_remain_after": node.flow_capacity_remain,
        "last_order_control_inlink_name_before": pre_node["last_order_control_inlink_name"],
        "last_order_control_entry_timestep_before": pre_node["last_order_control_entry_timestep"],
        "last_order_control_inlink_name_after": _link_name(node.last_order_control_inlink),
        "last_order_control_entry_timestep_after": node.last_order_control_entry_timestep,
        "order_control_clearance_timesteps": pre_node["order_control_clearance_timesteps"],
        "incoming_vehicle_count_before": pre_node["incoming_vehicle_count"],
        "incoming_vehicle_order_before": pre_node["incoming_vehicle_order"],
        "passed_visit_keys": "|".join(passed_keys),
    }
    GATE.node_rows.append(node_row)
    for role_name in ("buyer", "seller"):
        GATE.target_rows.append(_target_row(node, role_name, pre_targets, events))


def _target_row(node, role_name, pre_targets, events) -> dict:
    vehicle_name, visit_id, predicted_route = _target_spec(role_name)
    visit_text = _visit_text(vehicle_name, visit_id)
    event = _terminal_event_for_visit(events, visit_text)
    formal = _formal_route(node.W, (vehicle_name, visit_id))
    assigned = _assigned_rank(node.W, (vehicle_name, visit_id))
    vehicle_pre = pre_targets[role_name]
    if role_name == "buyer":
        predicted_capacity, predicted_entry, predicted_entrance = pre_targets["buyer_predicted_outlink"]
        actual_side_capacity, actual_side_entry, actual_side_entrance = pre_targets["buyer_actual_outlink"]
    else:
        predicted_capacity, predicted_entry, predicted_entrance = pre_targets["seller_outlink"]
        actual_side_capacity, actual_side_entry, actual_side_entrance = pre_targets["seller_outlink"]
    row = {
        "world_timestep": node.W.T,
        "node_name": node.name,
        "role": role_name,
        "vehicle_name": vehicle_name,
        "visit_id": visit_id,
        "visit_key": visit_text,
        "current_link_name": None,
        "position_x": None,
        "live_route_next_link_name": None,
        "formal_route_next_link_name": formal,
        "predicted_route_next_link_name": predicted_route,
        "in_target_incoming_before_attempt": False,
        "in_inlink_vehicles": False,
        "is_inlink_physical_head": False,
        "assigned_rank": assigned,
        "not_yet_passed": None,
        "terminal_reason": REASON_NOT_CANDIDATE,
        "clearance_evaluated": False,
        "clearance_unmet": False,
        "inlink_capacity_out_remain_at_check": None,
        "node_flow_capacity_remain_at_check": None,
        "selected_outlink_capacity_in_remain_at_check": None,
        "selected_outlink_entry_open_at_check": None,
        "selected_outlink_entrance_vehicle_name": None,
        "selected_outlink_name": None,
        "passed_this_timestep": False,
        "candidate_index": None,
        "earlier_attempted_visit_keys": "",
        "earlier_passed_visit_keys": "",
        "clearance_last_inlink_name": None,
        "clearance_last_entry_timestep": None,
        "clearance_last_inlink_name_after_move": None,
        "clearance_last_entry_timestep_after_move": None,
        "predicted_outlink_capacity_in_remain_before_attempts": predicted_capacity,
        "predicted_outlink_entry_open_before_attempts": predicted_entry,
        "predicted_outlink_entrance_vehicle_name_before_attempts": predicted_entrance,
        "actual_side_outlink_capacity_in_remain_before_attempts": actual_side_capacity,
        "actual_side_outlink_entry_open_before_attempts": actual_side_entry,
        "actual_side_outlink_entrance_vehicle_name_before_attempts": actual_side_entrance,
    }
    row["current_link_name"] = vehicle_pre["current_link_name"]
    row["position_x"] = vehicle_pre["position_x"]
    row["live_route_next_link_name"] = vehicle_pre["live_route_next_link_name"]
    row["not_yet_passed"] = vehicle_pre["on_this_visit"]
    row["in_inlink_vehicles"] = vehicle_pre["in_inlink_vehicles"]
    row["is_inlink_physical_head"] = vehicle_pre["is_head"]
    row["in_target_incoming_before_attempt"] = vehicle_pre["in_incoming"]
    if event is None:
        return row
    row["terminal_reason"] = event["reason"]
    row["candidate_index"] = event["candidate_index"]
    row["selected_outlink_name"] = event["live_route_next_link_name"]
    row["inlink_capacity_out_remain_at_check"] = event.get("inlink_capacity_out_remain")
    row["node_flow_capacity_remain_at_check"] = event.get("node_flow_capacity_remain")
    row["selected_outlink_capacity_in_remain_at_check"] = event.get(
        "selected_outlink_capacity_in_remain"
    )
    row["selected_outlink_entry_open_at_check"] = event.get("selected_outlink_entry_open")
    row["selected_outlink_entrance_vehicle_name"] = event.get(
        "selected_outlink_entrance_vehicle_name"
    )
    row["clearance_last_inlink_name"] = event.get("clearance_last_inlink_name")
    if row["clearance_last_inlink_name"] is None:
        row["clearance_last_inlink_name"] = event.get("clearance_last_inlink_name_before_move")
    row["clearance_last_entry_timestep"] = event.get("clearance_last_entry_timestep")
    if row["clearance_last_entry_timestep"] is None:
        row["clearance_last_entry_timestep"] = event.get(
            "clearance_last_entry_timestep_before_move"
        )
    row["clearance_last_inlink_name_after_move"] = event.get(
        "clearance_last_inlink_name_after_move"
    )
    row["clearance_last_entry_timestep_after_move"] = event.get(
        "clearance_last_entry_timestep_after_move"
    )
    row["passed_this_timestep"] = event["reason"] == REASON_PASSED
    row["clearance_unmet"] = event["reason"] == REASON_CLEARANCE_UNMET
    if event["reason"] in (
        REASON_CLEARANCE_UNMET,
        REASON_PASSED,
        "inlink_outflow_capacity_unavailable",
        "node_flow_capacity_unavailable",
        "outlink_inflow_capacity_unavailable",
        "outlink_entry_space_unavailable",
    ):
        row["clearance_evaluated"] = True
        row["is_inlink_physical_head"] = True
    if event["reason"] == REASON_NOT_PHYSICAL_HEAD:
        row["is_inlink_physical_head"] = False
    row["earlier_attempted_visit_keys"] = _prior_visit_keys(
        events, event["candidate_index"], False
    )
    row["earlier_passed_visit_keys"] = _prior_visit_keys(
        events, event["candidate_index"], True
    )
    return row


def install_trace_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Trace hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_transfer = physical_transfer_module.transfer_tvt_mp_passage_attempts
    GATE.original_try = physical_transfer_module._try_confirmed_candidates
    GATE.original_head = physical_transfer_module._inlink_physical_head_should_skip
    GATE.original_first = physical_transfer_module._first_ordinary_physical_shortage
    GATE.original_clearance = uxsim_module.Node._order_control_clearance_blocks_passage
    GATE.original_move = uxsim_module.Node._transfer_one_vehicle_between_links
    GATE.original_route_choice = uxsim_module.Vehicle.route_next_link_choice
    GATE.original_commit_history = (
        physical_transfer_module.commit_tvt_mp_actual_node_passage_history
    )
    GATE.installed = True
    physical_transfer_module.transfer_tvt_mp_passage_attempts = wrapped_transfer
    physical_transfer_module._try_confirmed_candidates = wrapped_try
    physical_transfer_module._inlink_physical_head_should_skip = wrapped_head
    physical_transfer_module._first_ordinary_physical_shortage = wrapped_first
    physical_transfer_module.commit_tvt_mp_actual_node_passage_history = wrapped_commit_history
    uxsim_module.Node._order_control_clearance_blocks_passage = wrapped_clearance
    uxsim_module.Node._transfer_one_vehicle_between_links = wrapped_move
    uxsim_module.Vehicle.route_next_link_choice = wrapped_route_choice


def restore_trace_hooks() -> None:
    if GATE.installed is not True:
        return
    physical_transfer_module.transfer_tvt_mp_passage_attempts = GATE.original_transfer
    physical_transfer_module._try_confirmed_candidates = GATE.original_try
    physical_transfer_module._inlink_physical_head_should_skip = GATE.original_head
    physical_transfer_module._first_ordinary_physical_shortage = GATE.original_first
    physical_transfer_module.commit_tvt_mp_actual_node_passage_history = (
        GATE.original_commit_history
    )
    uxsim_module.Node._order_control_clearance_blocks_passage = GATE.original_clearance
    uxsim_module.Node._transfer_one_vehicle_between_links = GATE.original_move
    uxsim_module.Vehicle.route_next_link_choice = GATE.original_route_choice
    GATE.original_transfer = None
    GATE.original_try = None
    GATE.original_head = None
    GATE.original_first = None
    GATE.original_clearance = None
    GATE.original_move = None
    GATE.original_route_choice = None
    GATE.original_commit_history = None
    GATE.last_real_move = None
    GATE.real_world = None
    GATE.installed = False


def _history_by_visit(world) -> dict:
    registry = getattr(world, "order_control_tvt_mp_actual_node_passage_history_registry", None)
    if not isinstance(registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError("Actual passage history registry is missing.")
    records = registry.records_by_node_name.get(TARGET_NODE_NAME, ())
    by_visit = {}
    for record in records:
        if not isinstance(record, OrderControlTvtMpActualNodePassageRecord):
            raise RuntimeError("Actual passage record has the wrong type.")
        visit_key = record.visit_key
        if visit_key in by_visit:
            raise RuntimeError(f"Duplicate actual passage history for {visit_key!r}.")
        by_visit[visit_key] = record
    return by_visit


def _attach_history_ranks(world) -> None:
    by_visit = _history_by_visit(world)
    for row in GATE.passage_rows:
        if row["visit_id"] is None:
            continue
        record = by_visit.get((row["vehicle_name"], row["visit_id"]))
        if record is None:
            continue
        if record.actual_passage_timestep != row["world_timestep"]:
            continue
        row["actual_node_passage_rank"] = record.actual_node_passage_rank
        if record.actual_route_next_link_name != row["actual_route_next_link_name"]:
            raise RuntimeError(
                f"{row['visit_key']} logged route {row['actual_route_next_link_name']!r} "
                f"differs from history {record.actual_route_next_link_name!r}."
            )


def _mark_capacity_before_targets() -> None:
    target_keys = {
        _visit_text(BUYER_NAME, BUYER_VISIT_ID),
        _visit_text(SELLER_NAME, SELLER_VISIT_ID),
    }
    for row in GATE.passage_rows:
        if row["world_timestep"] < DECISION_TIMESTEP or row["world_timestep"] > SELLER_ACTUAL_PASSAGE:
            row["consumed_node_or_outlink_before_target"] = False
            continue
        earlier = False
        for other in GATE.passage_rows:
            if other["world_timestep"] != row["world_timestep"]:
                continue
            if other["visit_key"] in target_keys:
                continue
            other_index = other["candidate_index"]
            this_index = row["candidate_index"]
            if other_index is None or this_index is None:
                continue
            if other_index < this_index and row["visit_key"] in target_keys:
                earlier = True
        if row["visit_key"] in target_keys:
            row["consumed_node_or_outlink_before_target"] = earlier
        else:
            buyer_index = None
            seller_index = None
            for target in GATE.target_rows:
                if target["world_timestep"] != row["world_timestep"]:
                    continue
                if target["role"] == "buyer":
                    buyer_index = target["candidate_index"]
                if target["role"] == "seller":
                    seller_index = target["candidate_index"]
            before_buyer = buyer_index is not None and row["candidate_index"] is not None and row["candidate_index"] < buyer_index
            before_seller = seller_index is not None and row["candidate_index"] is not None and row["candidate_index"] < seller_index
            row["consumed_node_or_outlink_before_target"] = before_buyer is True or before_seller is True


def _research_visit(bundle, vehicle_name, visit_id):
    found = None
    for visit in bundle.visits:
        if visit.tvt_decision_timestep != DECISION_TIMESTEP:
            continue
        if visit.node_name != TARGET_NODE_NAME:
            continue
        if visit.vehicle_name != vehicle_name or visit.visit_id != visit_id:
            continue
        if found is not None:
            raise RuntimeError(f"Research output repeats {vehicle_name}:{visit_id}.")
        found = visit
    if found is None:
        raise RuntimeError(f"Research output has no {vehicle_name}:{visit_id} at T=600.")
    return found


def _require_research(bundle) -> None:
    buyer = _research_visit(bundle, BUYER_NAME, BUYER_VISIT_ID)
    seller = _research_visit(bundle, SELLER_NAME, SELLER_VISIT_ID)
    if buyer.role != "buyer":
        raise RuntimeError(f"Buyer role is {buyer.role!r}.")
    if seller.role != "seller":
        raise RuntimeError(f"Seller role is {seller.role!r}.")
    if buyer.actual_passage_timestep != BUYER_ACTUAL_PASSAGE:
        raise RuntimeError(f"Buyer actual passage is {buyer.actual_passage_timestep!r}.")
    if seller.actual_passage_timestep != SELLER_ACTUAL_PASSAGE:
        raise RuntimeError(f"Seller actual passage is {seller.actual_passage_timestep!r}.")
    if buyer.candidate_passage_timestep != BUYER_CANDIDATE_PASSAGE:
        raise RuntimeError(f"Buyer candidate passage is {buyer.candidate_passage_timestep!r}.")
    if seller.candidate_passage_timestep != SELLER_CANDIDATE_PASSAGE:
        raise RuntimeError(f"Seller candidate passage is {seller.candidate_passage_timestep!r}.")
    if buyer.baseline_passage_timestep != BUYER_BASELINE_PASSAGE:
        raise RuntimeError(f"Buyer baseline passage is {buyer.baseline_passage_timestep!r}.")
    if seller.baseline_passage_timestep != SELLER_BASELINE_PASSAGE:
        raise RuntimeError(f"Seller baseline passage is {seller.baseline_passage_timestep!r}.")
    if buyer.assigned_rank != BUYER_ASSIGNED_RANK or seller.assigned_rank != SELLER_ASSIGNED_RANK:
        raise RuntimeError("Assigned ranks do not match the T=600 trade.")
    if buyer.actual_node_passage_rank != BUYER_ACTUAL_RANK:
        raise RuntimeError("Buyer actual rank does not match.")
    if seller.actual_node_passage_rank != SELLER_ACTUAL_RANK:
        raise RuntimeError("Seller actual rank does not match.")
    if buyer.predicted_route_next_link_name != BUYER_PREDICTED_ROUTE:
        raise RuntimeError("Buyer predicted route does not match.")
    if buyer.actual_route_next_link_name != BUYER_ACTUAL_ROUTE:
        raise RuntimeError("Buyer actual route does not match.")
    if seller.predicted_route_next_link_name != SELLER_ROUTE:
        raise RuntimeError("Seller predicted route does not match.")
    if seller.actual_route_next_link_name != SELLER_ROUTE:
        raise RuntimeError("Seller actual route does not match.")


def _target_at(role_name, timestep):
    found = None
    for row in GATE.target_rows:
        if row["role"] != role_name or row["world_timestep"] != timestep:
            continue
        if found is not None:
            raise RuntimeError(f"Duplicate {role_name} trace at T={timestep}.")
        found = row
    if found is None:
        raise RuntimeError(f"Missing {role_name} trace at T={timestep}.")
    return found


def _require_trace_contract() -> None:
    if GATE.foreign_record_count != 0:
        raise RuntimeError("Trace recorded a world that is not the real World.")
    timestep = TRACE_START
    while timestep <= TRACE_END:
        if timestep not in GATE.seen_timesteps:
            raise RuntimeError(f"Node trace is missing T={timestep}.")
        _target_at("buyer", timestep)
        _target_at("seller", timestep)
        timestep = timestep + 1
    buyer_fail = _target_at("buyer", BUYER_CANDIDATE_PASSAGE)
    buyer_pass = _target_at("buyer", BUYER_ACTUAL_PASSAGE)
    seller_fail = _target_at("seller", SELLER_CANDIDATE_PASSAGE)
    seller_pass = _target_at("seller", SELLER_ACTUAL_PASSAGE)
    if buyer_fail["passed_this_timestep"] is True:
        raise RuntimeError("Buyer passed at the candidate timestep.")
    if buyer_pass["terminal_reason"] != REASON_PASSED:
        raise RuntimeError(
            f"Buyer T={BUYER_ACTUAL_PASSAGE} reason is {buyer_pass['terminal_reason']!r}."
        )
    if seller_fail["passed_this_timestep"] is True:
        raise RuntimeError("Seller passed at the candidate timestep.")
    if seller_pass["terminal_reason"] != REASON_PASSED:
        raise RuntimeError(
            f"Seller T={SELLER_ACTUAL_PASSAGE} reason is {seller_pass['terminal_reason']!r}."
        )
    buyer_event = None
    seller_event = None
    seen_passage = set()
    for row in GATE.passage_rows:
        key = (row["world_timestep"], row["visit_key"])
        if key in seen_passage:
            raise RuntimeError(f"Duplicate passage event {key!r}.")
        seen_passage.add(key)
        if row["visit_key"] == _visit_text(BUYER_NAME, BUYER_VISIT_ID):
            if row["world_timestep"] == BUYER_ACTUAL_PASSAGE:
                buyer_event = row
        if row["visit_key"] == _visit_text(SELLER_NAME, SELLER_VISIT_ID):
            if row["world_timestep"] == SELLER_ACTUAL_PASSAGE:
                seller_event = row
    if buyer_event is None:
        raise RuntimeError("Buyer passage event at T=607 is missing.")
    if seller_event is None:
        raise RuntimeError("Seller passage event at T=609 is missing.")
    if buyer_event["assigned_rank"] != BUYER_ASSIGNED_RANK:
        raise RuntimeError("Buyer passage event rank differs.")
    if seller_event["assigned_rank"] != SELLER_ASSIGNED_RANK:
        raise RuntimeError("Seller passage event rank differs.")
    if buyer_event["actual_node_passage_rank"] != BUYER_ACTUAL_RANK:
        raise RuntimeError("Buyer passage event actual rank differs.")
    if seller_event["actual_node_passage_rank"] != SELLER_ACTUAL_RANK:
        raise RuntimeError("Seller passage event actual rank differs.")
    if buyer_event["actual_route_next_link_name"] != BUYER_ACTUAL_ROUTE:
        raise RuntimeError("Buyer passage route differs.")
    if seller_event["actual_route_next_link_name"] != SELLER_ROUTE:
        raise RuntimeError("Seller passage route differs.")


def _first_route_change_to_actual():
    found = None
    for row in GATE.route_rows:
        if row["vehicle_name"] != BUYER_NAME:
            continue
        if row["new_live_route_next_link_name"] != BUYER_ACTUAL_ROUTE:
            continue
        if found is None or row["world_timestep"] < found["world_timestep"]:
            found = row
    return found


def _route_relation(buyer_reason) -> str:
    outlink_reasons = (
        "outlink_inflow_capacity_unavailable",
        "outlink_entry_space_unavailable",
    )
    if buyer_reason in outlink_reasons:
        return (
            "未確定。停止理由は選択中outlinkの流入容量または入口空間である。"
            "予測進路なら通過できたかは、今回観測していない。"
        )
    return (
        "未確定。観測された停止理由だけでは、buyerの進路変更が"
        "1 timestep遅れの直接原因とは断定できない。"
    )


def _seller_spill_text(seller_reason, buyer_pass_row) -> str:
    if seller_reason != REASON_CLEARANCE_UNMET:
        return (
            "未確定。sellerの候補時刻での停止理由はclearance未充足ではない。"
            "buyer通過の1 timestep遅れがsellerへ波及したかは断定しない。"
        )
    last_inlink = seller_reason and buyer_pass_row["current_link_name"]
    return (
        "sellerの候補時刻の停止理由はclearance未充足である。"
        "その直前clearance履歴とbuyer通過時刻はCSVに保存した。"
        f"buyer通過時のlinkは {last_inlink!r}。"
        "時系列の前後関係は記録するが、波及の因果は未確定。"
    )


def _summary_text() -> str:
    buyer_fail = _target_at("buyer", BUYER_CANDIDATE_PASSAGE)
    buyer_pass = _target_at("buyer", BUYER_ACTUAL_PASSAGE)
    seller_fail = _target_at("seller", SELLER_CANDIDATE_PASSAGE)
    seller_pass = _target_at("seller", SELLER_ACTUAL_PASSAGE)
    route_change = _first_route_change_to_actual()
    if route_change is None:
        route_line = (
            "観測窓T="
            f"{TRACE_START}〜{TRACE_END}では、buyerのlive routeが"
            f"{BUYER_ACTUAL_ROUTE}へ変わったroute_next_link_choiceは記録されなかった。"
        )
    else:
        route_line = (
            f"buyerのlive routeが{BUYER_ACTUAL_ROUTE}になったtimestepは"
            f"T={route_change['world_timestep']}。"
            f"変更前進路={route_change['previous_live_route_next_link_name']}、"
            f"変更前進路のcapacity_in={route_change['previous_outlink_capacity_in_remain']}、"
            f"入口空間={route_change['previous_outlink_entry_open']}。"
            f"変更後capacity_in={route_change['new_outlink_capacity_in_remain']}、"
            f"入口空間={route_change['new_outlink_entry_open']}。"
        )
    buyer_live_lines = []
    timestep = DECISION_TIMESTEP
    while timestep <= BUYER_ACTUAL_PASSAGE:
        row = _target_at("buyer", timestep)
        buyer_live_lines.append(
            f"  T={timestep}: live={row['live_route_next_link_name']}, "
            f"reason={row['terminal_reason']}, "
            f"predicted_outlink_entry_open_before_attempts={row['predicted_outlink_entry_open_before_attempts']}, "
            f"actual_side_outlink_entry_open_before_attempts={row['actual_side_outlink_entry_open_before_attempts']}"
        )
        timestep = timestep + 1
    other_before_buyer = []
    other_before_seller = []
    for row in GATE.passage_rows:
        if row["consumed_node_or_outlink_before_target"] is not True:
            continue
        if row["visit_key"] == _visit_text(BUYER_NAME, BUYER_VISIT_ID):
            continue
        if row["visit_key"] == _visit_text(SELLER_NAME, SELLER_VISIT_ID):
            continue
        text = (
            f"T={row['world_timestep']} {row['visit_key']} "
            f"rank={row['assigned_rank']} route={row['actual_route_next_link_name']}"
        )
        if row["world_timestep"] <= BUYER_ACTUAL_PASSAGE:
            other_before_buyer.append(text)
        if row["world_timestep"] <= SELLER_ACTUAL_PASSAGE:
            other_before_seller.append(text)
    if len(other_before_buyer) == 0:
        other_buyer_text = "対象buyerより前に同一timestepで通過した別Visitは、保存したpassage event上は無い。"
    else:
        other_buyer_text = "別Visitの先行通過: " + "; ".join(other_before_buyer)
    lines = [
        "T=600 northeast_intersection route divergence trace",
        "反実仮想比較は実装していない。",
        "",
        f"buyerがT={BUYER_CANDIDATE_PASSAGE}に通過できなかった直接理由: {buyer_fail['terminal_reason']}",
        f"  live route: {buyer_fail['live_route_next_link_name']}",
        f"  selected outlink: {buyer_fail['selected_outlink_name']}",
        f"  inlink outflow remain: {buyer_fail['inlink_capacity_out_remain_at_check']}",
        f"  node flow remain: {buyer_fail['node_flow_capacity_remain_at_check']}",
        f"  outlink inflow remain: {buyer_fail['selected_outlink_capacity_in_remain_at_check']}",
        f"  outlink entry open: {buyer_fail['selected_outlink_entry_open_at_check']}",
        f"  earlier passed visits: {buyer_fail['earlier_passed_visit_keys']}",
        f"buyerがT={BUYER_ACTUAL_PASSAGE}に通過できた理由: {buyer_pass['terminal_reason']}",
        f"  live route: {buyer_pass['live_route_next_link_name']}",
        f"  selected outlink: {buyer_pass['selected_outlink_name']}",
        f"sellerがT={SELLER_CANDIDATE_PASSAGE}に通過できなかった直接理由: {seller_fail['terminal_reason']}",
        f"  live route: {seller_fail['live_route_next_link_name']}",
        f"  clearance last inlink: {seller_fail['clearance_last_inlink_name']}",
        f"  clearance last timestep: {seller_fail['clearance_last_entry_timestep']}",
        f"  earlier passed visits: {seller_fail['earlier_passed_visit_keys']}",
        f"sellerがT={SELLER_ACTUAL_PASSAGE}に通過できた理由: {seller_pass['terminal_reason']}",
        "",
        route_line,
        "buyer live route T=600〜607:",
    ]
    lines.extend(buyer_live_lines)
    lines.append("")
    lines.append("buyerの進路変更と1 timestep遅れの関係: " + _route_relation(buyer_fail["terminal_reason"]))
    lines.append("buyerの遅れがsellerへ波及したか: " + _seller_spill_text(seller_fail["terminal_reason"], buyer_pass))
    lines.append("別Visitまたはclearance更新: " + other_buyer_text)
    if len(other_before_seller) == 0:
        lines.append("seller以前の別Visit先行通過は、保存したevent上は無い。")
    else:
        lines.append("seller以前の別Visit先行通過: " + "; ".join(other_before_seller))
    lines.append(
        "Candidate予測とActualの差を観測事実だけで説明できるか: "
        "各停止timestepのproduction判定結果は上に記録した。"
        "進路変更が無かった場合の通過時刻は観測していないため、差の全体は未確定。"
    )
    lines.append("進路変更の分類: 未確定。")
    lines.append(
        "次に反実仮想比較が必要か: 必要。今回はbuyer進路を固定した比較を実装していない。"
    )
    lines.append(
        "判定順はproductionのまま観測した。到着済み、inlink物理先頭、clearance、"
        "inlink outflow、node flow、outlink inflow、outlink入口空間、通過成功。"
        "値の再判定で容量やRNGは消費していない。"
    )
    return "\n".join(lines) + "\n"


NODE_COLUMNS = (
    "world_timestep",
    "node_name",
    "node_flow_capacity_remain_before",
    "node_flow_capacity_remain_after",
    "last_order_control_inlink_name_before",
    "last_order_control_entry_timestep_before",
    "last_order_control_inlink_name_after",
    "last_order_control_entry_timestep_after",
    "order_control_clearance_timesteps",
    "incoming_vehicle_count_before",
    "incoming_vehicle_order_before",
    "passed_visit_keys",
)

TARGET_COLUMNS = (
    "world_timestep",
    "node_name",
    "role",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "current_link_name",
    "position_x",
    "live_route_next_link_name",
    "formal_route_next_link_name",
    "predicted_route_next_link_name",
    "in_target_incoming_before_attempt",
    "in_inlink_vehicles",
    "is_inlink_physical_head",
    "assigned_rank",
    "not_yet_passed",
    "terminal_reason",
    "clearance_evaluated",
    "clearance_unmet",
    "inlink_capacity_out_remain_at_check",
    "node_flow_capacity_remain_at_check",
    "selected_outlink_capacity_in_remain_at_check",
    "selected_outlink_entry_open_at_check",
    "selected_outlink_entrance_vehicle_name",
    "selected_outlink_name",
    "passed_this_timestep",
    "candidate_index",
    "earlier_attempted_visit_keys",
    "earlier_passed_visit_keys",
    "clearance_last_inlink_name",
    "clearance_last_entry_timestep",
    "clearance_last_inlink_name_after_move",
    "clearance_last_entry_timestep_after_move",
    "predicted_outlink_capacity_in_remain_before_attempts",
    "predicted_outlink_entry_open_before_attempts",
    "predicted_outlink_entrance_vehicle_name_before_attempts",
    "actual_side_outlink_capacity_in_remain_before_attempts",
    "actual_side_outlink_entry_open_before_attempts",
    "actual_side_outlink_entrance_vehicle_name_before_attempts",
)

PASSAGE_COLUMNS = (
    "world_timestep",
    "node_name",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "assigned_rank",
    "actual_node_passage_rank",
    "inlink_name",
    "actual_route_next_link_name",
    "candidate_index",
    "consumed_node_or_outlink_before_target",
    "clearance_last_inlink_name_before_move",
    "clearance_last_entry_timestep_before_move",
    "clearance_last_inlink_name_after_move",
    "clearance_last_entry_timestep_after_move",
)

ROUTE_COLUMNS = (
    "world_timestep",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "previous_live_route_next_link_name",
    "new_live_route_next_link_name",
    "previous_outlink_capacity_in_remain",
    "new_outlink_capacity_in_remain",
    "previous_outlink_entry_open",
    "new_outlink_entry_open",
    "previous_entrance_vehicle_name",
    "new_entrance_vehicle_name",
    "end_node_name",
)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            cells = {}
            for column in columns:
                cells[column] = _csv_cell(row[column])
            writer.writerow(cells)


def _write_outputs(summary_text: str) -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    if OUTPUT_DIR == four_cross_trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory is the trial output directory.")
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    _write_csv(OUTPUT_DIR / NODE_TRACE_NAME, NODE_COLUMNS, GATE.node_rows)
    _write_csv(OUTPUT_DIR / TARGET_TRACE_NAME, TARGET_COLUMNS, GATE.target_rows)
    _write_csv(OUTPUT_DIR / PASSAGE_EVENTS_NAME, PASSAGE_COLUMNS, GATE.passage_rows)
    _write_csv(OUTPUT_DIR / ROUTE_EVENTS_NAME, ROUTE_COLUMNS, GATE.route_rows)
    (OUTPUT_DIR / CAUSE_SUMMARY_NAME).write_text(summary_text, encoding="utf-8")
    file_write_time = datetime.datetime.now().isoformat(timespec="seconds")
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "diagnostic_script_name": DIAGNOSTIC_SCRIPT_NAME,
        "target_node_name": TARGET_NODE_NAME,
        "decision_timestep": DECISION_TIMESTEP,
        "trace_start": TRACE_START,
        "trace_end": TRACE_END,
        "buyer_visit_key": _visit_text(BUYER_NAME, BUYER_VISIT_ID),
        "seller_visit_key": _visit_text(SELLER_NAME, SELLER_VISIT_ID),
        "output_filenames": list(OUTPUT_FILE_NAMES),
        "row_counts": {
            "node_timesteps": len(GATE.node_rows),
            "target_rows": len(GATE.target_rows),
            "passage_events": len(GATE.passage_rows),
            "route_change_events": len(GATE.route_rows),
        },
        "counterfactual_route_comparison": "not_implemented",
        "completion_status": "completed",
        "generated_at": file_write_time,
        "generated_at_meaning": "file write time, not a simulation timestep",
    }
    (OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected_names = set(OUTPUT_FILE_NAMES)
    for path in OUTPUT_DIR.iterdir():
        if path.name not in expected_names:
            raise RuntimeError(f"Unexpected file in output directory: {path.name}.")


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
    four_cross_trial.add_vehicles_to_world(
        world,
        four_cross_trial.VEHICLE_SPECS,
        vot_records,
    )
    world.finalize_scenario()
    if world.TSIZE != four_cross_trial.INTERNAL_TSIZE:
        raise RuntimeError(
            f"Expected TSIZE=={four_cross_trial.INTERNAL_TSIZE}, got {world.TSIZE}."
        )
    if world.name != four_cross_trial.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name was not kept.")
    return world


def _reset_gate_records() -> None:
    GATE.node_rows = []
    GATE.target_rows = []
    GATE.passage_rows = []
    GATE.route_rows = []
    GATE.attempt_events = []
    GATE.seen_timesteps = []
    GATE.foreign_record_count = 0
    GATE.index_by_vehicle_id = {}
    GATE.pending_vehicle_id = None
    GATE.last_real_move = None


def main() -> int:
    original_python_recursion_limit = sys.getrecursionlimit()
    _reset_gate_records()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if original_python_recursion_limit < four_cross_trial.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(four_cross_trial.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_trial_world()
        install_trace_hooks(world)
        four_cross_trial.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            four_cross_trial.restore_real_world_spillback_observation()
            restore_trace_hooks()
        if world.T != EXPECTED_WORLD_T:
            raise RuntimeError(f"World.T is {world.T!r}, expected {EXPECTED_WORLD_T}.")
        evaluation = four_cross_trial.verify_evaluation_end(world)
        if evaluation["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        _require_research(bundle)
        _attach_history_ranks(world)
        _mark_capacity_before_targets()
        _require_trace_contract()
        summary_text = _summary_text()
        _write_outputs(summary_text)
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        four_cross_trial.restore_real_world_spillback_observation()
        restore_trace_hooks()
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
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
            if node.func.attr == "main":
                raise RuntimeError("Diagnostic calls a main function.")
    for name in ("system", "rmtree", "unlink", "rmdir", "eval", "exec"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
    if "write_tvt_mp_research_output_csv" in called:
        raise RuntimeError("Diagnostic writes the trial research CSVs.")
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
            ):
                raise RuntimeError(f"Diagnostic assigns {target.attr}.")
    if tuple(OUTPUT_FILE_NAMES) != (
        "t600_node_timestep_trace.csv",
        "t600_target_visit_trace.csv",
        "t600_passage_events.csv",
        "t600_route_change_events.csv",
        "t600_direct_cause_summary.txt",
        "manifest.json",
    ):
        raise RuntimeError("Output file names are not the fixed six files.")
    if "反実仮想比較は実装していない" not in source:
        raise RuntimeError("Counterfactual comparison is not marked unimplemented.")
    if "GATE.real_world" not in source:
        raise RuntimeError("Real-world identity check is missing.")
    main_function = _function_by_name(tree, "main")
    finally_count = 0
    for node in ast.walk(main_function):
        if isinstance(node, ast.Try) and len(node.finalbody) > 0:
            finally_count = finally_count + 1
    if finally_count < 2:
        raise RuntimeError("main() does not restore hooks in finally blocks.")
    main_called = _call_names(main_function)
    if "restore_trace_hooks" not in main_called:
        raise RuntimeError("main() does not restore trace hooks.")
    if "restore_real_world_spillback_observation" not in main_called:
        raise RuntimeError("main() does not restore spillback observation.")
    if "exec_simulation" not in main_called:
        raise RuntimeError("main() does not run one simulation.")
    write_outputs = _function_by_name(tree, "_write_outputs")
    for node in ast.walk(write_outputs):
        if isinstance(node, ast.Attribute) and node.attr == "TRIAL_OUTPUT_DIR":
            break
    else:
        raise RuntimeError("Diagnostic output is not checked against the trial output.")
    route_wrapper = _function_by_name(tree, "wrapped_route_choice")
    route_source = ast.get_source_segment(source, route_wrapper)
    if route_source is None:
        raise RuntimeError("wrapped_route_choice source segment is missing.")
    if "_is_real_target_vehicle(vehicle) is not True" not in route_source:
        raise RuntimeError("wrapped_route_choice does not exclude non-target vehicles first.")
    if route_source.find("getattr(vehicle, \"route_next_link\", None)") < 0:
        raise RuntimeError("wrapped_route_choice does not read route_next_link with getattr.")
    if "vehicle.route_next_link" in route_source:
        raise RuntimeError("wrapped_route_choice uses direct vehicle.route_next_link access.")
    original_call_count = 0
    for node in ast.walk(route_wrapper):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "original_route_choice":
            continue
        original_call_count = original_call_count + 1
    if original_call_count != 2:
        raise RuntimeError(
            "wrapped_route_choice must call original_route_choice once per branch."
        )
    for node in ast.walk(route_wrapper):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                if isinstance(target.value, ast.Name) and target.value.id == "vehicle":
                    if target.attr == "route_next_link":
                        raise RuntimeError(
                            "wrapped_route_choice assigns vehicle.route_next_link."
                        )
    pre_reader = _function_by_name(tree, "_read_target_vehicle_pre")
    pre_source = ast.get_source_segment(source, pre_reader)
    if pre_source is None:
        raise RuntimeError("_read_target_vehicle_pre source segment is missing.")
    if "_read_vehicle_route_next_link(vehicle)" not in pre_source:
        raise RuntimeError("_read_target_vehicle_pre does not read route via getattr helper.")
    if "vehicle.route_next_link" in pre_source:
        raise RuntimeError("_read_target_vehicle_pre uses direct vehicle.route_next_link access.")
    for func_node in tree.body:
        if not isinstance(func_node, ast.FunctionDef):
            continue
        if func_node.name == "validate_static_contract":
            continue
        if func_node.name == "_read_vehicle_route_next_link":
            continue
        for node in ast.walk(func_node):
            if not isinstance(node, ast.Attribute):
                continue
            if node.attr != "route_next_link":
                continue
            if not isinstance(node.value, ast.Name):
                continue
            if node.value.id != "vehicle":
                continue
            raise RuntimeError(
                f"{func_node.name} uses direct vehicle.route_next_link attribute access."
            )
    print("static contract ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
    else:
        raise SystemExit(main())
