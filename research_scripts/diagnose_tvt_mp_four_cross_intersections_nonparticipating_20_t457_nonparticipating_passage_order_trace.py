"""
Trace why two nonparticipating visits at the T=457 northwest trade pass in
physical order rather than C-rank order.

Candidate judgments come from the saved binding-transfer result. Actual
judgments come from the production passage hooks. This script does not call
those judgment functions again and does not decide the reason in advance.
"""

from __future__ import annotations

import ast
import csv
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial as trial
import uxsim.order_control_tvt_mp_candidate_binding_transfer as binding_module
import uxsim.order_control_tvt_mp_candidate_local_virtual_calculation as local_calc_module
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.order_control_tvt_mp_physical_transfer as physical_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_DECISION_TIMESTEP = 457
TARGET_NODE_NAME = "northwest_intersection"
CANDIDATE_TRACE_START = 470
CANDIDATE_TRACE_END = 477
ACTUAL_TRACE_START = 470
ACTUAL_TRACE_END = 477
EXPECTED_BUYER = ("veh_ne_ws_base_012", 2)
TARGET_PARTIES = {
    ("veh_ne_ws_base_012", 2): {
        "role": "buyer",
        "baseline_passage": 477,
        "candidate_passage": 470,
        "actual_passage": 470,
        "baseline_local_rank": 4,
        "candidate_local_rank": 1,
        "c_rank": 212,
        "actual_passage_rank": 212,
        "formal_inlink_name": None,
    },
    ("veh_nw_sw_pulse_004", 1): {
        "role": "nonparticipating",
        "baseline_passage": 475,
        "candidate_passage": 475,
        "actual_passage": 475,
        "baseline_local_rank": 2,
        "candidate_local_rank": 2,
        "c_rank": 213,
        "actual_passage_rank": 214,
        "formal_inlink_name": "north_west_od_to_northwest_intersection",
    },
    ("veh_sw_nw_base_050", 2): {
        "role": "nonparticipating",
        "baseline_passage": 473,
        "candidate_passage": 472,
        "actual_passage": 472,
        "baseline_local_rank": 3,
        "candidate_local_rank": 3,
        "c_rank": 214,
        "actual_passage_rank": 213,
        "formal_inlink_name": "southwest_intersection_to_northwest_intersection",
    },
    ("veh_wn_se_base_029", 1): {
        "role": "seller",
        "baseline_passage": 471,
        "candidate_passage": 477,
        "actual_passage": 477,
        "baseline_local_rank": 1,
        "candidate_local_rank": 4,
        "c_rank": 215,
        "actual_passage_rank": 215,
        "formal_inlink_name": None,
    },
}
C213 = ("veh_nw_sw_pulse_004", 1)
C214 = ("veh_sw_nw_base_050", 2)
HOOK_NAMES = ("try_confirmed", "head_skip", "clearance", "shortage", "actual_transfer")

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t457_nonparticipating_passage_order_trace"
    )
)
CANDIDATE_CSV = "t457_candidate_passage_events.csv"
ACTUAL_CSV = "t457_actual_passage_events.csv"
PAIRED_CSV = "t457_candidate_actual_paired_events.csv"
TIMELINE_CSV = "t457_target_nonparticipating_timeline.csv"
SCAN_ORDER_CSV = "t457_scan_order_and_prior_events.csv"
SUMMARY_NAME = "t457_nonparticipating_passage_order_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    CANDIDATE_CSV,
    ACTUAL_CSV,
    PAIRED_CSV,
    TIMELINE_CSV,
    SCAN_ORDER_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)


class _StopAfterActualT477(Exception):
    """Stop after real T=477 has finished, at the T=478 driver entry."""


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.original_binding_scan = None
        self.original_try_confirmed = None
        self.original_head_skip = None
        self.original_clearance = None
        self.original_shortage = None
        self.original_actual_transfer = None
        self.selected = None
        self.rank_confirmation = {}
        self.scan_before = {}
        self.actual_events = []
        self.actual_scan = None
        self.actual_scan_serial = 0
        self.wrapper_call_counts = {name: 0 for name in HOOK_NAMES}
        self.original_call_counts = {name: 0 for name in HOOK_NAMES}
        self.actual_trace_completed = False


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    if hasattr(value, "value") and type(value.value) is str:
        return value.value
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _rank_map(world) -> dict:
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return {}
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return {}
    ranks = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        ranks[plain] = rank_state.assigned_rank(visit_key)
    return ranks


def _saved_columns(atomic) -> dict:
    validation_set = atomic.final_consistency_validation_set_result
    final_rank_set = validation_set.final_rank_set_result
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection_set = payment_set.candidate_selection_set_result
    economic_set = selection_set.economic_evaluation_set_result
    local_set = economic_set.local_virtual_calculation_set_result
    fifo_set = local_set.fifo_inspection_set_result
    trade_rank_set = fifo_set.general_trade_rank_set_result
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    inlink_set = concrete_set.inlink_candidate_physical_order_result
    candidate_set = inlink_set.candidate_visit_set_result
    right_set = candidate_set.right_of_entry_selection_result
    leading_set = right_set.leading_confirmation_result
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_set.node_candidate_set_results,
        "leading_nodes": leading_set.node_confirmation_results,
    }


def _one_node(results, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != TARGET_NODE_NAME:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"T=457 {label} count is {count}.")
    return matched


def _note_new_ranks(world, timestep: int) -> None:
    if world is not GATE.real_world:
        return
    if getattr(world, "_order_control_baseline_collector", None) is not None:
        return
    for visit_key, rank_value in _rank_map(world).items():
        if visit_key in GATE.rank_confirmation:
            if GATE.rank_confirmation[visit_key]["assigned_rank"] != rank_value:
                raise RuntimeError(f"{_visit_text(visit_key)} C rank changed after confirmation.")
            continue
        GATE.rank_confirmation[visit_key] = {
            "decision_timestep": timestep,
            "assigned_rank": rank_value,
            "source": "tvt_mp_driver_rank_ledger",
        }


def _capture_selected(world, result) -> None:
    if GATE.selected is not None:
        raise RuntimeError("T=457 northwest selection was captured twice.")
    if not isinstance(result, OrderControlTvtMpDriverResult) or result.atomic_apply_set_result is None:
        raise RuntimeError("T=457 driver result has no atomic apply result.")
    columns = _saved_columns(result.atomic_apply_set_result)
    selection = _one_node(columns["selection_nodes"], "selection")
    economic = selection.selected_candidate_economic_result
    if economic is None:
        raise RuntimeError("T=457 northwest has no selected candidate.")
    local_result = economic.candidate_local_virtual_calculation_result
    buyers = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    if buyers != (EXPECTED_BUYER,):
        return
    economic_node = _one_node(columns["economic_nodes"], "economic")
    evaluation_index = None
    index = 0
    for candidate in economic_node.candidate_economic_evaluation_results:
        index = index + 1
        if candidate is economic:
            evaluation_index = index
    if evaluation_index is None:
        raise RuntimeError("Selected economic result is missing from the node list.")
    trade_node = _one_node(columns["trade_rank_nodes"], "trade rank")
    if not isinstance(trade_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError("Trade rank node type is wrong.")
    trade_result = None
    for candidate_trade in trade_node.candidate_trade_rank_results:
        candidate_buyers = tuple(_plain_visit_key(item) for item in candidate_trade.buyers_sorted)
        if candidate_buyers == buyers:
            if trade_result is not None:
                raise RuntimeError("Two trade results share the T=457 buyer.")
            trade_result = candidate_trade
    if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError("T=457 trade result was not found.")
    identity = f"T=457|{TARGET_NODE_NAME}|index={evaluation_index}|{_visit_text(EXPECTED_BUYER)}"
    GATE.selected = {
        "identity": identity,
        "evaluation_index": evaluation_index,
        "buyers": buyers,
        "local_result": local_result,
        "trade_result": trade_result,
        "ranks_after_decision": _rank_map(world),
    }


def wrapped_driver(world):
    if world is GATE.real_world and world.T == ACTUAL_TRACE_END + 1:
        GATE.actual_trace_completed = True
        raise _StopAfterActualT477()
    result = GATE.original_driver(world)
    if world is GATE.real_world and getattr(world, "_order_control_baseline_collector", None) is None:
        if type(world.T) is int:
            _note_new_ranks(world, world.T)
        if world.T == TARGET_DECISION_TIMESTEP:
            _capture_selected(world, result)
    return result


def _binding_context(binding_transfer_state):
    local_state = binding_transfer_state.virtual_time_state.candidate_local_state
    if local_state.target_node_name != TARGET_NODE_NAME:
        return None
    if local_state.real_world_timestep_T != TARGET_DECISION_TIMESTEP:
        return None
    if local_state.local_world is GATE.real_world:
        raise RuntimeError("Candidate binding scan is running on the real World.")
    virtual_timestep = local_state.local_world.T
    if type(virtual_timestep) is not int or virtual_timestep < CANDIDATE_TRACE_START or virtual_timestep > CANDIDATE_TRACE_END:
        return None
    buyers = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_state.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    if buyers != (EXPECTED_BUYER,):
        return None
    return {"virtual_timestep": virtual_timestep, "node": local_state.target_node, "local_state": local_state}


def _entry_open(outlink, world):
    if outlink is None:
        return None
    vehicles = getattr(outlink, "vehicles", None)
    lane_count = getattr(outlink, "number_of_lanes", None)
    if vehicles is None or type(lane_count) is not int:
        return None
    if len(vehicles) < lane_count:
        return True
    delta = getattr(outlink, "delta_per_lane", None)
    if delta is None:
        return None
    return vehicles[-lane_count].x > delta * world.DELTAN


def _snapshot_binding_visit(node, binding_visit, vehicle) -> dict:
    world = node.W
    link = getattr(vehicle, "link", None)
    on_inlink = link is not None and getattr(link, "name", None) == binding_visit.inlink_name and getattr(link, "end_node", None) is node
    outlink = None
    outlinks = getattr(node, "outlinks", None)
    if isinstance(outlinks, dict):
        for candidate_link in outlinks.values():
            if getattr(candidate_link, "name", None) == binding_visit.route_next_link_name:
                outlink = candidate_link
    return {
        "in_target_node_incoming_before_judgment": vehicle in node.incoming_vehicles,
        "is_physical_head_before_judgment": on_inlink is True and len(link.vehicles) > 0 and link.vehicles[0] is vehicle,
        "current_link_name_before_judgment": None if link is None else link.name,
        "formal_inlink_name": binding_visit.inlink_name,
        "route_next_link_name": binding_visit.route_next_link_name,
        "entry_open_before_judgment": _entry_open(outlink, world),
        "outlink_capacity_available_before_judgment": None if outlink is None else outlink.capacity_in_remain >= world.DELTAN,
        "inlink_capacity_available_before_judgment": None if on_inlink is not True else link.capacity_out_remain >= world.DELTAN,
        "baseline_arrival_timestep": binding_visit.baseline_arrival_timestep,
    }


def wrapped_binding_scan(binding_transfer_state):
    context = _binding_context(binding_transfer_state)
    if context is not None:
        local_state = context["local_state"]
        pairs = local_state.binding_visit_local_vehicle_pairs
        visits = local_state.binding_rank_sequence.visits_in_binding_order
        if len(pairs) == len(visits):
            for pair, binding_visit in zip(pairs, visits):
                visit_key = _plain_visit_key(binding_visit.visit_key)
                GATE.scan_before[(context["virtual_timestep"], visit_key)] = _snapshot_binding_visit(
                    context["node"], binding_visit, pair.local_vehicle
                )
    result = GATE.original_binding_scan(binding_transfer_state)
    return result


def _actual_window(node) -> bool:
    if node is None or node.W is not GATE.real_world or node.name != TARGET_NODE_NAME:
        return False
    if getattr(node.W, "_order_control_baseline_collector", None) is not None:
        return False
    timestep = node.W.T
    return type(timestep) is int and ACTUAL_TRACE_START <= timestep <= ACTUAL_TRACE_END


def _count(storage, name: str) -> None:
    storage[name] = storage[name] + 1


def _assigned_rank_now(node, visit_key):
    states = getattr(node.W, "order_control_tvt_rank_states_by_node_name", None)
    rank_state = None if not isinstance(states, dict) else states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return None
    for confirmed in rank_state.confirmed_visit_keys_in_order():
        if _plain_visit_key(confirmed) == _plain_visit_key(visit_key):
            return rank_state.assigned_rank(confirmed)
    return None


def _capture_attempt_state(node, vehicle, inlink, outlink, visit_key, previous):
    route = getattr(vehicle, "route_next_link", None)
    is_head = vehicle.link is inlink and len(inlink.vehicles) > 0 and inlink.vehicles[0] is vehicle
    clearance = None
    if previous is not None and previous.get("clearance_satisfied_before_attempt") is not None:
        clearance = previous["clearance_satisfied_before_attempt"]
    if previous is not None and previous.get("head_formally_known") is True:
        is_head = previous["is_physical_head_before_attempt"]
    return {
        "arrived_before_attempt": vehicle in node.incoming_vehicles,
        "is_physical_head_before_attempt": is_head,
        "head_formally_known": previous is not None and previous.get("head_formally_known") is True,
        "current_link_name_before_attempt": None if vehicle.link is None else vehicle.link.name,
        "formal_inlink_name": inlink.name,
        "live_route_next_link_name_before_attempt": None if route is None else getattr(route, "name", None),
        "entry_open_before_attempt": _entry_open(outlink, node.W),
        "outlink_capacity_available_before_attempt": outlink.capacity_in_remain >= node.W.DELTAN,
        "inlink_capacity_available_before_attempt": inlink.capacity_out_remain >= node.W.DELTAN,
        "clearance_satisfied_before_attempt": clearance,
        "assigned_rank_before_attempt": _assigned_rank_now(node, visit_key),
    }


def _active_scan(node):
    scan = GATE.actual_scan
    if scan is None or node is None or node is not scan["node"] or _actual_window(node) is not True:
        return None
    return scan


def _open_slot(scan, vehicle, inlink):
    for slot in scan["slots"]:
        if slot["finalized"] is True:
            continue
        if slot["candidate"].vehicle is vehicle and slot["candidate"].inlink is inlink:
            return slot
    return None


def _begin_actual_scan(node, confirmed_candidates):
    GATE.actual_scan_serial = GATE.actual_scan_serial + 1
    slots = []
    scan_order = 0
    for candidate in confirmed_candidates:
        scan_order = scan_order + 1
        slots.append(
            {
                "candidate": candidate,
                "visit_key": _plain_visit_key(candidate.visit_key),
                "scan_order": scan_order,
                "in_incoming_before_production": candidate.vehicle in node.incoming_vehicles,
                "state": _capture_attempt_state(node, candidate.vehicle, candidate.inlink, candidate.outlink, candidate.visit_key, None),
                "finalized": False,
                "judgment": None,
                "called_head": False,
                "head_result": None,
                "called_clearance": False,
                "clearance_result": None,
                "called_shortage": False,
                "shortage_result": None,
                "called_transfer": False,
                "registry_rank": None,
                "registry_passage_timestep": None,
            }
        )
    return {"token": GATE.actual_scan_serial, "node": node, "timestep": node.W.T, "slots": slots}


def _read_committed_passage(node, visit_key):
    registry = node.W.order_control_tvt_mp_actual_node_passage_history_registry
    matched = None
    for record in registry.records_by_node_name.get(node.name, ()):
        if _plain_visit_key(record.visit_key) != visit_key:
            continue
        if matched is not None:
            raise RuntimeError(f"Duplicate passage history for {_visit_text(visit_key)}.")
        matched = record
    if matched is None:
        raise RuntimeError(f"Passed visit {_visit_text(visit_key)} has no passage history.")
    return matched.actual_node_passage_rank, matched.actual_passage_timestep


def _judgment_columns(judgment):
    if judgment == "not_in_incoming":
        return False, False, "not_in_incoming", "", False
    if judgment == "not_inlink_physical_head":
        return True, False, "not_inlink_physical_head", "", False
    if judgment == "clearance_not_satisfied":
        return True, False, "", "clearance_not_satisfied", False
    if judgment == "passed":
        return True, True, "", "", False
    if judgment == "not_reached":
        return False, False, "", "", True
    return True, False, judgment, "", False


def _finish_actual_scan(scan) -> None:
    earlier_attempted = []
    earlier_passed = []
    clearance_stop = None
    for slot in scan["slots"]:
        if clearance_stop is not None and slot["finalized"] is True and slot["judgment"] not in (None, "not_reached"):
            raise RuntimeError(
                f"{_visit_text(slot['visit_key'])} was judged after a clearance stop."
            )
        if slot["finalized"] is not True:
            if clearance_stop is not None:
                slot["judgment"] = "not_reached"
            elif slot["in_incoming_before_production"] is not True:
                slot["judgment"] = "not_in_incoming"
            else:
                raise RuntimeError(f"{_visit_text(slot['visit_key'])} at T={scan['timestep']} received no judgment.")
            slot["finalized"] = True
        if slot["judgment"] == "passed":
            rank_value, passage_timestep = _read_committed_passage(scan["node"], slot["visit_key"])
            slot["registry_rank"] = rank_value
            slot["registry_passage_timestep"] = passage_timestep
        state = slot["state"]
        attempted, passed, skip_reason, stop_reason, not_reached = _judgment_columns(slot["judgment"])
        confirmation = GATE.rank_confirmation.get(slot["visit_key"])
        GATE.actual_events.append(
            {
                "real_timestep": scan["timestep"],
                "scan_token": scan["token"],
                "scan_order": slot["scan_order"],
                "vehicle_name": slot["visit_key"][0],
                "visit_id": slot["visit_key"][1],
                "visit_key": _visit_text(slot["visit_key"]),
                "visit_key_tuple": slot["visit_key"],
                "assigned_rank_before_attempt": state["assigned_rank_before_attempt"],
                "rank_confirmation_decision_timestep": None if confirmation is None else confirmation["decision_timestep"],
                "rank_confirmation_source": None if confirmation is None else confirmation["source"],
                "arrived_before_attempt": state["arrived_before_attempt"],
                "in_incoming_before_attempt": state["arrived_before_attempt"],
                "current_link_name_before_attempt": state["current_link_name_before_attempt"],
                "formal_inlink_name": state["formal_inlink_name"],
                "is_physical_head_before_attempt": state["is_physical_head_before_attempt"],
                "live_route_next_link_name_before_attempt": state["live_route_next_link_name_before_attempt"],
                "entry_open_before_attempt": state["entry_open_before_attempt"],
                "outlink_capacity_available_before_attempt": state["outlink_capacity_available_before_attempt"],
                "inlink_capacity_available_before_attempt": state["inlink_capacity_available_before_attempt"],
                "clearance_satisfied_before_attempt": state["clearance_satisfied_before_attempt"],
                "attempted": attempted,
                "passed": passed,
                "temporary_skip_reason": skip_reason,
                "stop_reason": stop_reason,
                "not_reached": not_reached,
                "prior_clearance_stop_visit_key": "" if clearance_stop is None else clearance_stop,
                "earlier_attempted_visit_keys": "|".join(earlier_attempted),
                "earlier_passed_visit_keys": "|".join(earlier_passed),
                "called_head": slot["called_head"],
                "head_result": slot["head_result"],
                "called_clearance": slot["called_clearance"],
                "clearance_result": slot["clearance_result"],
                "called_shortage": slot["called_shortage"],
                "shortage_result": slot["shortage_result"],
                "called_transfer": slot["called_transfer"],
                "committed_actual_passage_timestep": slot["registry_passage_timestep"],
                "committed_actual_passage_rank": slot["registry_rank"],
                "production_judgment": slot["judgment"],
            }
        )
        if slot["judgment"] == "clearance_not_satisfied":
            clearance_stop = _visit_text(slot["visit_key"])
        if attempted is True:
            earlier_attempted.append(_visit_text(slot["visit_key"]))
        if passed is True:
            earlier_passed.append(_visit_text(slot["visit_key"]))


def wrapped_try_confirmed(node, confirmed_candidates):
    _count(GATE.wrapper_call_counts, "try_confirmed")
    scan = _begin_actual_scan(node, confirmed_candidates) if _actual_window(node) is True else None
    GATE.actual_scan = scan
    try:
        result = GATE.original_try_confirmed(node, confirmed_candidates)
    finally:
        _count(GATE.original_call_counts, "try_confirmed")
        GATE.actual_scan = None
    if scan is not None:
        _finish_actual_scan(scan)
    return result


def wrapped_head_skip(vehicle, inlink):
    _count(GATE.wrapper_call_counts, "head_skip")
    node = getattr(inlink, "end_node", None)
    scan = _active_scan(node)
    slot = None if scan is None else _open_slot(scan, vehicle, inlink)
    if slot is not None:
        slot["state"] = _capture_attempt_state(node, vehicle, inlink, slot["candidate"].outlink, slot["visit_key"], slot["state"])
    result = GATE.original_head_skip(vehicle, inlink)
    _count(GATE.original_call_counts, "head_skip")
    if slot is not None:
        slot["called_head"] = True
        slot["head_result"] = result
        slot["state"]["is_physical_head_before_attempt"] = result is False
        slot["state"]["head_formally_known"] = True
        if result is True:
            slot["judgment"] = "not_inlink_physical_head"
            slot["finalized"] = True
    return result


def wrapped_clearance(node, vehicle, inlink):
    _count(GATE.wrapper_call_counts, "clearance")
    scan = _active_scan(node)
    slot = None if scan is None else _open_slot(scan, vehicle, inlink)
    if slot is not None:
        slot["state"] = _capture_attempt_state(node, vehicle, inlink, slot["candidate"].outlink, slot["visit_key"], slot["state"])
    result = GATE.original_clearance(node, vehicle, inlink)
    _count(GATE.original_call_counts, "clearance")
    if slot is not None:
        slot["called_clearance"] = True
        slot["clearance_result"] = result
        slot["state"]["clearance_satisfied_before_attempt"] = result is False
        if result is True:
            slot["judgment"] = "clearance_not_satisfied"
            slot["finalized"] = True
    return result


def wrapped_shortage(node, inlink, outlink):
    _count(GATE.wrapper_call_counts, "shortage")
    scan = _active_scan(node)
    slot = None
    if scan is not None and len(inlink.vehicles) > 0:
        head = inlink.vehicles[0]
        for candidate_slot in scan["slots"]:
            candidate = candidate_slot["candidate"]
            if candidate_slot["finalized"] is not True and candidate.vehicle is head and candidate.inlink is inlink and candidate.outlink is outlink:
                slot = candidate_slot
    if slot is not None:
        slot["state"] = _capture_attempt_state(node, slot["candidate"].vehicle, inlink, outlink, slot["visit_key"], slot["state"])
    result = GATE.original_shortage(node, inlink, outlink)
    _count(GATE.original_call_counts, "shortage")
    if slot is not None:
        slot["called_shortage"] = True
        slot["shortage_result"] = result
        if result is not None:
            slot["judgment"] = result
            slot["finalized"] = True
    return result


def wrapped_actual_transfer(node, vehicle, inlink, outlink):
    _count(GATE.wrapper_call_counts, "actual_transfer")
    scan = _active_scan(node)
    slot = None if scan is None else _open_slot(scan, vehicle, inlink)
    if slot is not None and slot["candidate"].outlink is not outlink:
        slot = None
    if slot is not None:
        slot["state"] = _capture_attempt_state(node, vehicle, inlink, outlink, slot["visit_key"], slot["state"])
    result = GATE.original_actual_transfer(node, vehicle, inlink, outlink)
    _count(GATE.original_call_counts, "actual_transfer")
    if slot is not None:
        slot["called_transfer"] = True
        slot["judgment"] = "passed"
        slot["finalized"] = True
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Hooks are already installed.")
    if local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep is not binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep:
        raise RuntimeError("Binding scan references differ.")
    GATE.real_world = real_world
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_binding_scan = local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    GATE.original_try_confirmed = physical_module._try_confirmed_candidates
    GATE.original_head_skip = physical_module._inlink_physical_head_should_skip
    GATE.original_clearance = uxsim_module.Node._order_control_clearance_blocks_passage
    GATE.original_shortage = physical_module._first_ordinary_physical_shortage
    GATE.original_actual_transfer = uxsim_module.Node._transfer_one_vehicle_between_links
    driver_module.run_tvt_mp_driver = wrapped_driver
    local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = wrapped_binding_scan
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = wrapped_binding_scan
    physical_module._try_confirmed_candidates = wrapped_try_confirmed
    physical_module._inlink_physical_head_should_skip = wrapped_head_skip
    uxsim_module.Node._order_control_clearance_blocks_passage = wrapped_clearance
    physical_module._first_ordinary_physical_shortage = wrapped_shortage
    uxsim_module.Node._transfer_one_vehicle_between_links = wrapped_actual_transfer
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_driver
    local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = GATE.original_binding_scan
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = GATE.original_binding_scan
    physical_module._try_confirmed_candidates = GATE.original_try_confirmed
    physical_module._inlink_physical_head_should_skip = GATE.original_head_skip
    uxsim_module.Node._order_control_clearance_blocks_passage = GATE.original_clearance
    physical_module._first_ordinary_physical_shortage = GATE.original_shortage
    uxsim_module.Node._transfer_one_vehicle_between_links = GATE.original_actual_transfer
    GATE.installed = False
    GATE.actual_scan = None


def _clearance_from_candidate(passed, stopped, stop_reason, skip_reason, not_reached):
    if not_reached is True:
        return None
    stop_enum = binding_module.OrderControlTvtMpBindingTransferStopReason
    if stopped is True and stop_reason is stop_enum.CLEARANCE_NOT_SATISFIED:
        return False
    if passed is True:
        return True
    skip_enum = binding_module.OrderControlTvtMpBindingVisitTemporarySkipReason
    if skip_reason in (
        skip_enum.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE,
        skip_enum.NODE_FLOW_CAPACITY_UNAVAILABLE,
        skip_enum.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE,
        skip_enum.OUTLINK_ENTRY_SPACE_UNAVAILABLE,
    ):
        return True
    return None


def _build_candidate_events() -> list:
    selected = GATE.selected
    local_result = selected["local_result"]
    trade_result = selected["trade_result"]
    visits = local_result.binding_rank_sequence.visits_in_binding_order
    rows = []
    already_passed = set()
    for timestep_result in local_result.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        virtual_timestep = binding_result.virtual_timestep
        if type(virtual_timestep) is not int or virtual_timestep < CANDIDATE_TRACE_START or virtual_timestep > CANDIDATE_TRACE_END:
            continue
        transferred = {_plain_visit_key(item) for item in binding_result.transferred_binding_visit_keys}
        skipped = {_plain_visit_key(skip.binding_visit_key): skip.skip_reason for skip in binding_result.temporarily_skipped_visits}
        stopped_key = None if binding_result.stopped_binding_visit_key is None else _plain_visit_key(binding_result.stopped_binding_visit_key)
        blocked = False
        earlier_attempted = []
        earlier_passed = []
        scan_order = 0
        for binding_visit in visits:
            scan_order = scan_order + 1
            visit_key = _plain_visit_key(binding_visit.visit_key)
            picture = GATE.scan_before.get((virtual_timestep, visit_key), {})
            passed = visit_key in transferred
            skip_reason = skipped.get(visit_key)
            stopped = stopped_key == visit_key
            not_reached = blocked is True
            attempted = not_reached is not True and visit_key not in already_passed
            role = "buyer" if visit_key in {_plain_visit_key(item) for item in trade_result.buyers_sorted} else "seller" if visit_key in {_plain_visit_key(item) for item in trade_result.sellers_sorted} else "nonparticipating" if visit_key in {_plain_visit_key(item) for item in trade_result.nonparticipating_visits_sorted} else ""
            vehicle = GATE.real_world.VEHICLES.get(visit_key[0])
            rows.append(
                {
                    "virtual_timestep": virtual_timestep,
                    "scan_order": scan_order,
                    "vehicle_name": visit_key[0],
                    "visit_id": visit_key[1],
                    "visit_key": _visit_text(visit_key),
                    "visit_key_tuple": visit_key,
                    "role": role,
                    "participates_in_order_exchange": None if vehicle is None else vehicle.participates_in_order_exchange,
                    "assigned_c_rank": selected["ranks_after_decision"].get(visit_key),
                    "binding_rank": binding_visit.binding_rank,
                    "binding_partition": binding_visit.binding_partition.value,
                    "formal_inlink_name": picture.get("formal_inlink_name", binding_visit.inlink_name),
                    "formal_route_next_link_name": picture.get("route_next_link_name", binding_visit.route_next_link_name),
                    "baseline_arrival_timestep": picture.get("baseline_arrival_timestep", binding_visit.baseline_arrival_timestep),
                    "in_target_incoming_before_judgment": picture.get("in_target_node_incoming_before_judgment"),
                    "arrived_before_judgment": picture.get("in_target_node_incoming_before_judgment"),
                    "current_link_name": picture.get("current_link_name_before_judgment"),
                    "physical_head_before_judgment": picture.get("is_physical_head_before_judgment"),
                    "entry_open_before_judgment": picture.get("entry_open_before_judgment"),
                    "outlink_capacity_available": picture.get("outlink_capacity_available_before_judgment"),
                    "inlink_capacity_available": picture.get("inlink_capacity_available_before_judgment"),
                    "clearance_satisfied": _clearance_from_candidate(passed, stopped, binding_result.stop_reason, skip_reason, not_reached),
                    "attempted": attempted,
                    "passed": passed,
                    "temporarily_skipped": skip_reason is not None,
                    "skip_reason": "" if skip_reason is None else skip_reason.value,
                    "stopped": stopped,
                    "stop_reason": binding_result.stop_reason.value if stopped is True else "",
                    "not_reached_because_prior_clearance_stop": not_reached,
                    "earlier_attempted_visit_keys": "|".join(earlier_attempted),
                    "earlier_passed_visit_keys": "|".join(earlier_passed),
                    "passage_timestep_if_passed": virtual_timestep if passed is True else None,
                }
            )
            if attempted is True:
                earlier_attempted.append(_visit_text(visit_key))
            if passed is True:
                earlier_passed.append(_visit_text(visit_key))
                already_passed.add(visit_key)
            if stopped is True:
                blocked = True
    return rows


def _event(rows, visit_key, timestep, time_field):
    for row in rows:
        if row.get("visit_key_tuple") == visit_key and row.get(time_field) == timestep:
            return row
    return None


def _candidate_reason(row) -> str:
    if row is None:
        return ""
    if row["passed"] is True:
        return "passed"
    if row["stop_reason"] != "":
        return row["stop_reason"]
    if row["skip_reason"] != "":
        return row["skip_reason"]
    if row["not_reached_because_prior_clearance_stop"] is True:
        return "not_reached"
    return "not_passed"


def _actual_reason(row) -> str:
    if row is None:
        return ""
    if row["passed"] is True:
        return "passed"
    if row["stop_reason"] != "":
        return row["stop_reason"]
    if row["temporary_skip_reason"] != "":
        return row["temporary_skip_reason"]
    if row["not_reached"] is True:
        return "not_reached"
    return row["production_judgment"]


def _build_paired(candidate_rows) -> list:
    rows = []
    for visit_key in TARGET_PARTIES:
        for timestep in range(CANDIDATE_TRACE_START, CANDIDATE_TRACE_END + 1):
            candidate = _event(candidate_rows, visit_key, timestep, "virtual_timestep")
            actual = _event(GATE.actual_events, visit_key, timestep, "real_timestep")
            if candidate is None and actual is None:
                continue
            known = TARGET_PARTIES[visit_key]
            rows.append(
                {
                    "timestep": timestep,
                    "visit_key": _visit_text(visit_key),
                    "role": known["role"],
                    "c_rank": known["c_rank"],
                    "candidate_attempted": None if candidate is None else candidate["attempted"],
                    "actual_attempted": None if actual is None else actual["attempted"],
                    "candidate_judgment": _candidate_reason(candidate),
                    "actual_judgment": _actual_reason(actual),
                    "candidate_passed": None if candidate is None else candidate["passed"],
                    "actual_passed": None if actual is None else actual["passed"],
                    "candidate_temporary_skip_reason": None if candidate is None else candidate["skip_reason"],
                    "actual_temporary_skip_reason": None if actual is None else actual["temporary_skip_reason"],
                    "candidate_stop_reason": None if candidate is None else candidate["stop_reason"],
                    "actual_stop_reason": None if actual is None else actual["stop_reason"],
                    "candidate_arrived": None if candidate is None else candidate["arrived_before_judgment"],
                    "actual_arrived": None if actual is None else actual["arrived_before_attempt"],
                    "candidate_physical_head": None if candidate is None else candidate["physical_head_before_judgment"],
                    "actual_physical_head": None if actual is None else actual["is_physical_head_before_attempt"],
                    "candidate_entry_open": None if candidate is None else candidate["entry_open_before_judgment"],
                    "actual_entry_open": None if actual is None else actual["entry_open_before_attempt"],
                    "candidate_clearance": None if candidate is None else candidate["clearance_satisfied"],
                    "actual_clearance": None if actual is None else actual["clearance_satisfied_before_attempt"],
                    "candidate_passage_timestep": None if candidate is None else candidate["passage_timestep_if_passed"],
                    "actual_passage_timestep": None if actual is None else actual["committed_actual_passage_timestep"],
                    "actual_passage_rank": None if actual is None else actual["committed_actual_passage_rank"],
                }
            )
    return rows


def _build_timeline(paired_rows) -> list:
    return [row for row in paired_rows if row["visit_key"] in (_visit_text(C213), _visit_text(C214))]


def _build_scan_order(candidate_rows) -> list:
    rows = []
    for timestep in (472, 473, 474, 475):
        for source_name, events, time_field in (
            ("candidate", candidate_rows, "virtual_timestep"),
            ("actual", GATE.actual_events, "real_timestep"),
        ):
            ordered = [row for row in events if row.get(time_field) == timestep]
            ordered.sort(key=lambda item: item["scan_order"])
            for focus in (C213, C214):
                focus_row = _event(ordered, focus, timestep, time_field)
                if focus_row is None:
                    continue
                prior = [row["visit_key"] for row in ordered if row["scan_order"] < focus_row["scan_order"]]
                rows.append(
                    {
                        "source": source_name,
                        "timestep": timestep,
                        "focus_visit_key": _visit_text(focus),
                        "scan_order": focus_row["scan_order"],
                        "prior_visit_keys": "|".join(prior),
                        "judgment": _candidate_reason(focus_row) if source_name == "candidate" else _actual_reason(focus_row),
                        "passed": focus_row["passed"],
                    }
                )
    return rows


def _validate(candidate_rows, paired_rows) -> None:
    selected = GATE.selected
    if selected is None:
        raise RuntimeError("T=457 selected candidate was not captured.")
    trade = selected["trade_result"]
    buyers = {_plain_visit_key(item) for item in trade.buyers_sorted}
    sellers = {_plain_visit_key(item) for item in trade.sellers_sorted}
    nonparticipating = {_plain_visit_key(item) for item in trade.nonparticipating_visits_sorted}
    if len(buyers) != 1 or len(sellers) != 1 or len(nonparticipating) != 2:
        raise RuntimeError("T=457 role counts differ.")
    if set(TARGET_PARTIES) != buyers | sellers | nonparticipating:
        raise RuntimeError("T=457 party set differs.")
    for visit_key, known in TARGET_PARTIES.items():
        if selected["ranks_after_decision"].get(visit_key) != known["c_rank"]:
            raise RuntimeError(f"{_visit_text(visit_key)} C rank differs.")
        candidate_pass = [row for row in candidate_rows if row["visit_key_tuple"] == visit_key and row["passed"] is True]
        actual_pass = [row for row in GATE.actual_events if row["visit_key_tuple"] == visit_key and row["passed"] is True]
        if len(candidate_pass) != 1 or candidate_pass[0]["virtual_timestep"] != known["candidate_passage"]:
            raise RuntimeError(f"{_visit_text(visit_key)} candidate passage differs.")
        if len(actual_pass) != 1 or actual_pass[0]["real_timestep"] != known["actual_passage"]:
            raise RuntimeError(f"{_visit_text(visit_key)} actual passage differs.")
        if actual_pass[0]["committed_actual_passage_rank"] != known["actual_passage_rank"]:
            raise RuntimeError(f"{_visit_text(visit_key)} actual passage rank differs.")
        if known["formal_inlink_name"] is not None and candidate_pass[0]["formal_inlink_name"] != known["formal_inlink_name"]:
            raise RuntimeError(f"{_visit_text(visit_key)} formal inlink differs.")
    c214_472 = _event(GATE.actual_events, C214, 472, "real_timestep")
    c213_475 = _event(GATE.actual_events, C213, 475, "real_timestep")
    if c214_472 is None or c214_472["passed"] is not True:
        raise RuntimeError("Actual C214 did not pass at T=472.")
    if c213_475 is None or c213_475["passed"] is not True:
        raise RuntimeError("Actual C213 did not pass at T=475.")
    for timestep in (472, 473, 474):
        row = _event(GATE.actual_events, C213, timestep, "real_timestep")
        if row is None or row["passed"] is True or _actual_reason(row) in ("", "passed"):
            raise RuntimeError(f"Actual C213 non-passage reason at T={timestep} is missing.")
        if row["stop_reason"] == "clearance_not_satisfied":
            later = _event(GATE.actual_events, C214, timestep, "real_timestep")
            if later is not None and later["attempted"] is True:
                raise RuntimeError(f"C214 was attempted after C213 clearance stop at T={timestep}.")
    if c214_472["scan_order"] <= _event(GATE.actual_events, C213, 472, "real_timestep")["scan_order"]:
        raise RuntimeError("T=472 actual scan did not reach C214 after C213.")
    for name in HOOK_NAMES:
        if GATE.wrapper_call_counts[name] != GATE.original_call_counts[name]:
            raise RuntimeError(f"{name} wrapper count differs from original count.")
    for row in paired_rows:
        if row["candidate_passed"] is True and row["actual_passed"] is not True:
            raise RuntimeError(f"{row['visit_key']} candidate pass has no actual pass at T={row['timestep']}.")
        if row["actual_passed"] is True and row["candidate_passed"] is not True:
            raise RuntimeError(f"{row['visit_key']} actual pass has no candidate pass at T={row['timestep']}.")


def _summary(candidate_rows) -> str:
    reasons = []
    for timestep in (472, 473, 474):
        actual = _event(GATE.actual_events, C213, timestep, "real_timestep")
        candidate = _event(candidate_rows, C213, timestep, "virtual_timestep")
        reasons.append(f"T={timestep}: Candidate={_candidate_reason(candidate)} Actual={_actual_reason(actual)}")
    c214 = _event(GATE.actual_events, C214, 472, "real_timestep")
    c213_472 = _event(GATE.actual_events, C213, 472, "real_timestep")
    ordinary_skip = (
        c213_472 is not None
        and c213_472["stop_reason"] != "clearance_not_satisfied"
        and c213_472["passed"] is not True
        and c214 is not None
        and c214["passed"] is True
    )
    lines = [
        "T=457 northwest_intersection。buyer 1、seller 1、nonparticipating 2。",
        "C212 buyer veh_ne_ws_base_012:2 は Candidate/Actual passage T=470、Actual通過順位212。",
        "C213 nonparticipating veh_nw_sw_pulse_004:1 は Candidate/Actual passage T=475、Actual通過順位214。",
        "C214 nonparticipating veh_sw_nw_base_050:2 は Candidate/Actual passage T=472、Actual通過順位213。",
        "C215 seller veh_wn_se_base_029:1 は Candidate/Actual passage T=477、Actual通過順位215。",
        "C213がT=472〜474に通過しなかった正式理由: " + " / ".join(reasons),
        f"C214がT=472に通過した正式理由: Actual judgment={_actual_reason(c214)}。",
        "C順位は拘束された走査順であり、Actual passage rankは実通過順である。両者は同じ概念ではない。",
    ]
    if ordinary_skip is True:
        lines.append(
            "C213はT=472にclearance stopではなく、正式な一時skip理由 "
            f"{_actual_reason(c213_472)} で後続へ走査が続いた。"
            "C順位は走査優先順位であり、通常の物理制約で一時skipされたVisitを強制通過させる順位ではない。"
            "C213を一時skipしてC214を試すCandidate計算とActual実Worldの双方が同じ結果となったため、"
            "Candidate／Actual passageは一致した。"
        )
    else:
        lines.append("T=472の正式判定は、通常の一時skip後にC214へ継続した形とは一致しなかった。定型結論は使わない。")
    lines.append("ある条件を外したら結果が変わった、という反実仮想は証明していない。")
    return "\n".join(lines) + "\n"


def _prepare_world():
    world = trial.build_world()
    vot_values = trial._true_vot_sequence()
    vot_records = trial.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
    trial.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
    trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    return world


def main(argv=None) -> int:
    if argv is None:
        arguments = sys.argv[1:]
    else:
        arguments = list(argv)
    if len(arguments) > 1:
        raise SystemExit("Unexpected CLI arguments.")
    if len(arguments) == 1:
        if arguments[0] != "--static-validate-only":
            raise SystemExit(f"Unknown CLI option: {arguments[0]!r}.")
        validate_static_contract()
        return 0
    original_limit = sys.getrecursionlimit()
    stopped = False
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            try:
                world.exec_simulation()
            except _StopAfterActualT477:
                stopped = True
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        if stopped is not True:
            raise RuntimeError("Actual trace did not stop after T=477.")
        candidate_rows = _build_candidate_events()
        paired_rows = _build_paired(candidate_rows)
        _validate(candidate_rows, paired_rows)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_csv(OUTPUT_DIR / CANDIDATE_CSV, tuple(candidate_rows[0].keys()), candidate_rows)
        _write_csv(OUTPUT_DIR / ACTUAL_CSV, tuple(GATE.actual_events[0].keys()), GATE.actual_events)
        _write_csv(OUTPUT_DIR / PAIRED_CSV, tuple(paired_rows[0].keys()), paired_rows)
        timeline = _build_timeline(paired_rows)
        _write_csv(OUTPUT_DIR / TIMELINE_CSV, tuple(timeline[0].keys()) if timeline else ("timestep", "visit_key"), timeline)
        scan_rows = _build_scan_order(candidate_rows)
        _write_csv(OUTPUT_DIR / SCAN_ORDER_CSV, tuple(scan_rows[0].keys()) if scan_rows else ("source", "timestep", "focus_visit_key"), scan_rows)
        (OUTPUT_DIR / SUMMARY_NAME).write_text(_summary(candidate_rows), encoding="utf-8")
        manifest = {
            "diagnostic_script": SCRIPT_PATH.name,
            "target_decision_timestep": TARGET_DECISION_TIMESTEP,
            "target_node_name": TARGET_NODE_NAME,
            "candidate_identity": GATE.selected["identity"],
            "selected_candidate_evaluation_index": GATE.selected["evaluation_index"],
            "output_files": list(OUTPUT_FILE_NAMES),
        }
        (OUTPUT_DIR / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        trial.reference.restore_real_world_spillback_observation()
        restore_hooks()
        sys.setrecursionlimit(original_limit)


def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _original_call_count(function_node, attribute: str) -> int:
    count = 0
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == attribute and isinstance(node.func.value, ast.Name) and node.func.value.id == "GATE":
                count = count + 1
    return count


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if "t457_nonparticipating_passage_order_trace" not in str(OUTPUT_DIR):
        raise RuntimeError("Output directory name is wrong.")
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory equals the trial directory.")
    for name in OUTPUT_FILE_NAMES:
        if name not in source:
            raise RuntimeError(f"Missing output name {name}.")
    wrappers = (
        ("wrapped_binding_scan", "original_binding_scan"),
        ("wrapped_try_confirmed", "original_try_confirmed"),
        ("wrapped_head_skip", "original_head_skip"),
        ("wrapped_clearance", "original_clearance"),
        ("wrapped_shortage", "original_shortage"),
        ("wrapped_actual_transfer", "original_actual_transfer"),
    )
    for function_name, attribute in wrappers:
        function_node = _function_node(tree, function_name)
        if function_node is None or _original_call_count(function_node, attribute) != 1:
            raise RuntimeError(f"{function_name} must call {attribute} once.")
    main_node = _function_node(tree, "main")
    validate_line = None
    mkdir_line = None
    saw_sentinel = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_validate":
            validate_line = node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "mkdir":
            mkdir_line = node.lineno
        if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id == "_StopAfterActualT477":
            saw_sentinel = True
    if saw_sentinel is not True or validate_line is None or mkdir_line is None or validate_line >= mkdir_line:
        raise RuntimeError("Sentinel catch or validation-before-mkdir is missing.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation runs simulation, hooks, or mkdir.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name) and node.func.value.id == "trial":
                raise RuntimeError("Diagnostic calls trial.main.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
