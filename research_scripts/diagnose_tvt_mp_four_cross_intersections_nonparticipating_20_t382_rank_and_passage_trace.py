"""
Read-only trace of the T=382 northwest_intersection selected transaction
on the four-cross nonparticipating 20 percent trial.

This script reruns that trial once. It does not change production, the trial,
or other diagnostics. Candidate local rank, node-continuous assigned rank,
and actual physical passage rank stay separate.
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
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
)
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_NODE_NAME = trial.reference.NORTHWEST_INTERSECTION
TARGET_DECISION_TIMESTEP = 382
TARGET_NONPARTICIPATING = ("veh_wn_se_base_024", 1)
TARGET_BUYER = ("veh_en_sw_base_025", 2)
TARGET_SELLERS = (
    ("veh_sw_nw_base_037", 2),
    ("veh_nw_sw_base_047", 1),
)
ACTUAL_TRACE_START = 382
ACTUAL_TRACE_END = 408
CANDIDATE_TRACE_MUST_INCLUDE_START = 396
CANDIDATE_TRACE_MUST_INCLUDE_END = 408
ACTUAL_RANK_WINDOW_START = 174
ACTUAL_RANK_WINDOW_END = 180

DIAGNOSTIC_EVALUATION_END_TIMESTEP = 999
DIAGNOSTIC_INTERNAL_TSIZE = 1030
DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM = 1000
DIAGNOSTIC_ADDED_TIMESTEPS = 100

DIAGNOSTIC_SCENARIO_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
    "600_vehicle_eval_1000_timestep_t382_rank_and_passage_trace"
)

# Saved all-participating-era trial aggregates for eval_900 only (not used for validation).
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_TRANSACTIONS = 228
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_BUYER_VISITS = 263
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_SELLER_VISITS = 324
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_NONPARTICIPATING_VISITS = 39
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_BOTH_OBSERVED = 626
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_EQUAL_PASSAGES = 611
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_UNEQUAL_PASSAGES = 15
HISTORICAL_SAVED_TRIAL_EVAL_900_EXPECTED_UNOBSERVED = 0

EXPECTED_TARGET_ACTUAL_ARRIVALS = {
    ("veh_sw_nw_base_037", 2): 388,
    ("veh_nw_sw_base_047", 1): 390,
    ("veh_wn_se_base_024", 1): 392,
    ("veh_en_sw_base_025", 2): 394,
}
EXPECTED_NP_BASELINE_PASSAGE = 404
EXPECTED_NP_CANDIDATE_PASSAGE = 403
EXPECTED_NP_ACTUAL_PASSAGE = 404
EXPECTED_NP_CANDIDATE_NODE_RANK = 176
EXPECTED_NP_ACTUAL_NODE_RANK = 178
KNOWN_LATER_VISITS = (
    {
        "visit_key": ("veh_sw_nw_base_039", 2),
        "decision_timestep": 392,
        "actual_passage_timestep": 402,
        "actual_node_passage_rank": 177,
    },
    {
        "visit_key": ("veh_wn_en_base_025", 1),
        "decision_timestep": 392,
        "actual_passage_timestep": 406,
        "actual_node_passage_rank": 179,
    },
)

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_1000_timestep_seed_1_nonparticipation_seed_3_"
        "t382_rank_and_passage_trace"
    )
)
RANK_CSV = "t382_rank_side_by_side.csv"
CANDIDATE_EVENTS_CSV = "t382_candidate_passage_events.csv"
ACTUAL_EVENTS_CSV = "t382_actual_passage_events.csv"
LATER_DECISION_CSV = "t382_later_decision_intervening_visits.csv"
SUMMARY_NAME = "t382_nonparticipating_difference_summary.txt"
MANIFEST_NAME = "manifest.json"
ACTUAL_SEQUENTIAL_HOOK_NAMES = (
    "try_confirmed",
    "head_skip",
    "clearance",
    "shortage",
    "actual_transfer",
)
FORMAL_ORDINARY_SHORTAGE_REASONS = (
    "inlink_outflow_capacity_unavailable",
    "node_flow_capacity_unavailable",
    "outlink_inflow_capacity_unavailable",
    "outlink_entry_space_unavailable",
)


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
        self.original_arrival = None
        self.selected = None
        self.rank_confirmation = {}
        self.actual_arrivals = {}
        self.scan_before = {}
        self.candidate_scan_timesteps = []
        self.actual_events = []
        self.actual_scan = None
        self.actual_scan_serial = 0
        self.wrapper_call_counts = {}
        self.original_call_counts = {}
        self.summary_lines = []
        for hook_name in ACTUAL_SEQUENTIAL_HOOK_NAMES:
            self.wrapper_call_counts[hook_name] = 0
            self.original_call_counts[hook_name] = 0


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _assert_diagnostic_time_relationships() -> None:
    baseline_horizon = trial.reference.BASELINE_HORIZON_STEPS
    if DIAGNOSTIC_INTERNAL_TSIZE != DIAGNOSTIC_EVALUATION_END_TIMESTEP + baseline_horizon + 1:
        raise RuntimeError(
            "DIAGNOSTIC_INTERNAL_TSIZE must equal evaluation end + baseline horizon + 1."
        )
    if DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM != DIAGNOSTIC_EVALUATION_END_TIMESTEP + 1:
        raise RuntimeError(
            "DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM must equal evaluation end + 1."
        )
    if DIAGNOSTIC_ADDED_TIMESTEPS != 100:
        raise RuntimeError("DIAGNOSTIC_ADDED_TIMESTEPS must be 100.")
    if trial.reference.EVALUATION_END_TIMESTEP != 899:
        raise RuntimeError("trial.reference.EVALUATION_END_TIMESTEP must remain 899.")
    if trial.reference.INTERNAL_TSIZE != 930:
        raise RuntimeError("trial.reference.INTERNAL_TSIZE must remain 930.")


def _formal_arrival_timestep_from_time(arrival_time, deltat) -> int:
    formal_timestep = int(round(arrival_time / deltat))
    if type(formal_timestep) is not int or type(formal_timestep) is bool:
        raise RuntimeError(f"Formal arrival timestep is {formal_timestep!r}.")
    if formal_timestep < 0:
        raise RuntimeError(f"Formal arrival timestep is negative: {formal_timestep}.")
    return formal_timestep


def _apply_diagnostic_world_horizon(world) -> None:
    world.TMAX = DIAGNOSTIC_INTERNAL_TSIZE
    world.order_control_tvt_evaluation_end_timestep = DIAGNOSTIC_EVALUATION_END_TIMESTEP
    world.name = DIAGNOSTIC_SCENARIO_NAME


def _validate_world_horizon_after_finalize(world) -> None:
    if world.TMAX != DIAGNOSTIC_INTERNAL_TSIZE:
        raise RuntimeError(f"world.TMAX is {world.TMAX}, not {DIAGNOSTIC_INTERNAL_TSIZE}.")
    if world.TSIZE != DIAGNOSTIC_INTERNAL_TSIZE:
        raise RuntimeError(f"world.TSIZE is {world.TSIZE}, not {DIAGNOSTIC_INTERNAL_TSIZE}.")
    if world.order_control_tvt_evaluation_end_timestep != DIAGNOSTIC_EVALUATION_END_TIMESTEP:
        raise RuntimeError(
            "world.order_control_tvt_evaluation_end_timestep is not "
            f"{DIAGNOSTIC_EVALUATION_END_TIMESTEP}."
        )
    if world.order_control_tvt_baseline_horizon_steps != trial.reference.BASELINE_HORIZON_STEPS:
        raise RuntimeError("world.order_control_tvt_baseline_horizon_steps differs from trial.")


def _build_extended_evaluation_counts(bundle) -> dict:
    buyer_visit_count = 0
    seller_visit_count = 0
    nonparticipating_visit_count = 0
    both_candidate_and_actual_observed_count = 0
    equal_candidate_actual_passage_count = 0
    unequal_candidate_actual_passage_count = 0
    actual_passage_unobserved_count = 0
    for visit in bundle.visits:
        if visit.role == "buyer":
            buyer_visit_count = buyer_visit_count + 1
        elif visit.role == "seller":
            seller_visit_count = seller_visit_count + 1
        elif visit.role == "nonparticipating":
            nonparticipating_visit_count = nonparticipating_visit_count + 1
        if visit.actual_passage_timestep is None:
            actual_passage_unobserved_count = actual_passage_unobserved_count + 1
        if visit.candidate_passage_timestep is not None and visit.actual_passage_timestep is not None:
            both_candidate_and_actual_observed_count = both_candidate_and_actual_observed_count + 1
            if visit.candidate_passage_timestep == visit.actual_passage_timestep:
                equal_candidate_actual_passage_count = equal_candidate_actual_passage_count + 1
            else:
                unequal_candidate_actual_passage_count = unequal_candidate_actual_passage_count + 1
    return {
        "transaction_count": len(bundle.transactions),
        "buyer_visit_count": buyer_visit_count,
        "seller_visit_count": seller_visit_count,
        "nonparticipating_visit_count": nonparticipating_visit_count,
        "both_candidate_and_actual_observed_count": both_candidate_and_actual_observed_count,
        "equal_candidate_actual_passage_count": equal_candidate_actual_passage_count,
        "unequal_candidate_actual_passage_count": unequal_candidate_actual_passage_count,
        "actual_passage_unobserved_count": actual_passage_unobserved_count,
    }


def _validate_target_actual_arrivals(rank_rows, later_rows) -> None:
    for visit_key, expected_timestep in EXPECTED_TARGET_ACTUAL_ARRIVALS.items():
        if GATE.actual_arrivals.get(visit_key) != expected_timestep:
            raise RuntimeError(
                f"Formal first actual arrival for {_visit_text(visit_key)} is "
                f"{GATE.actual_arrivals.get(visit_key)!r}, not {expected_timestep}."
            )
        row = _row_for(rank_rows, visit_key)
        if row is None:
            raise RuntimeError(f"Rank row for {_visit_text(visit_key)} is missing.")
        if row["actual_arrival_timestep"] != expected_timestep:
            raise RuntimeError(
                f"Rank row actual_arrival_timestep for {_visit_text(visit_key)} is "
                f"{row['actual_arrival_timestep']!r}, not {expected_timestep}."
            )
    later_by_key = {}
    for row in later_rows:
        later_by_key[(row["vehicle_name"], row["visit_id"])] = row
    for visit_key, expected_timestep in EXPECTED_TARGET_ACTUAL_ARRIVALS.items():
        later = later_by_key.get(visit_key)
        if later is not None and later.get("actual_arrival_timestep") != expected_timestep:
            raise RuntimeError(
                f"Later row actual_arrival_timestep for {_visit_text(visit_key)} differs."
            )


def _plain_visit_key(visit_key) -> tuple:
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is {vehicle_name!r}.")
    if type(visit_id) is not int or type(visit_id) is bool:
        raise RuntimeError(f"VisitKey visit id is {visit_id!r}.")
    return (vehicle_name, visit_id)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        if value is True:
            return "True"
        return "False"
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            cells = {}
            for column in columns:
                cells[column] = _csv_cell(row.get(column))
            writer.writerow(cells)


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


def _saved_columns(atomic):
    validation_set = atomic.final_consistency_validation_set_result
    final_rank_set = validation_set.final_rank_set_result
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection_set = payment_set.candidate_selection_set_result
    economic_set = selection_set.economic_evaluation_set_result
    local_set = economic_set.local_virtual_calculation_set_result
    fifo_set = local_set.fifo_inspection_set_result
    trade_rank_set = fifo_set.general_trade_rank_set_result
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    inlink_order_set = concrete_set.inlink_candidate_physical_order_result
    candidate_visit_set = inlink_order_set.candidate_visit_set_result
    right_of_entry_set = candidate_visit_set.right_of_entry_selection_result
    leading_set = right_of_entry_set.leading_confirmation_result
    arrived_set = leading_set.arrived_confirmation_result
    alignment_set = arrived_set.alignment_fork_result
    fork_result = alignment_set.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError("Saved fork_result is not a baseline fork result.")
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "leading_nodes": leading_set.node_confirmation_results,
        "collector": fork_result.collector,
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
        raise RuntimeError(
            f"T={TARGET_DECISION_TIMESTEP} {TARGET_NODE_NAME}: {label} count is {count}."
        )
    return matched


def _note_new_ranks(world, timestep: int) -> None:
    if world is not GATE.real_world:
        return
    if getattr(world, "_order_control_baseline_collector", None) is not None:
        return
    after = _rank_map(world)
    for visit_key, rank_value in after.items():
        if visit_key in GATE.rank_confirmation:
            continue
        GATE.rank_confirmation[visit_key] = {
            "decision_timestep": timestep,
            "assigned_rank": rank_value,
            "source": "tvt_mp_driver_rank_ledger",
        }


def _find_one_based_evaluation_index(candidate_economic_results, selected_economic):
    evaluation_index = None
    index = 0
    for candidate_economic in candidate_economic_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if evaluation_index is not None:
                raise RuntimeError(
                    "Selected economic result appears more than once in the node list."
                )
            evaluation_index = index
    if evaluation_index is None:
        raise RuntimeError("Selected economic result is missing from the node list.")
    if type(evaluation_index) is not int or type(evaluation_index) is bool:
        raise RuntimeError(
            f"evaluation_index must be a Python int, not bool; got {evaluation_index!r}."
        )
    if evaluation_index < 1:
        raise RuntimeError(f"evaluation_index must be >= 1, got {evaluation_index}.")
    return evaluation_index


def _buyers_visit_identity_suffix(buyers) -> str:
    parts = []
    for buyer in buyers:
        parts.append(_visit_text(buyer))
    return "|".join(parts)


def _find_unique_trade_result_for_buyers(candidate_trade_rank_results, buyers):
    found = None
    for candidate_trade in candidate_trade_rank_results:
        candidate_buyers = tuple(
            _plain_visit_key(visit_key) for visit_key in candidate_trade.buyers_sorted
        )
        if candidate_buyers != buyers:
            continue
        if found is not None:
            raise RuntimeError(
                f"T={TARGET_DECISION_TIMESTEP} {TARGET_NODE_NAME}: more than one general "
                "trade-rank result matches the selected buyers."
            )
        found = candidate_trade
    if found is None:
        raise RuntimeError(
            f"T={TARGET_DECISION_TIMESTEP} {TARGET_NODE_NAME}: no general trade-rank "
            "result matches the selected buyers."
        )
    if not isinstance(found, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(
            f"T={TARGET_DECISION_TIMESTEP} {TARGET_NODE_NAME}: matched general trade-rank "
            f"result is {type(found).__name__}."
        )
    return found


def _capture_selected(world, result) -> None:
    if world.T != TARGET_DECISION_TIMESTEP:
        return
    if GATE.selected is not None:
        raise RuntimeError("T=382 northwest selection was captured more than once.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"Driver result is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError("T=382 driver returned no atomic apply result.")
    columns = _saved_columns(atomic)
    selection_node = _one_node(columns["selection_nodes"], "selection")
    economic = selection_node.selected_candidate_economic_result
    if economic is None:
        raise RuntimeError("T=382 northwest has no selected candidate.")
    local_result = economic.candidate_local_virtual_calculation_result
    buyers = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    if TARGET_BUYER not in buyers:
        raise RuntimeError("Selected candidate buyers do not include veh_en_sw_base_025:2.")
    economic_node = _one_node(columns["economic_nodes"], "economic")
    evaluation_index = _find_one_based_evaluation_index(
        economic_node.candidate_economic_evaluation_results,
        economic,
    )
    trade_node = _one_node(columns["trade_rank_nodes"], "trade rank")
    if not isinstance(trade_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError(f"Trade rank node is {type(trade_node).__name__}.")
    trade_result = _find_unique_trade_result_for_buyers(
        trade_node.candidate_trade_rank_results,
        buyers,
    )
    visit_node = _one_node(columns["candidate_visit_nodes"], "candidate visits")
    leading_node = _one_node(columns["leading_nodes"], "leading confirmation")
    identity = (
        f"T={TARGET_DECISION_TIMESTEP}|{TARGET_NODE_NAME}|"
        f"index={evaluation_index}|{_buyers_visit_identity_suffix(buyers)}"
    )
    GATE.selected = {
        "identity": identity,
        "evaluation_index": evaluation_index,
        "buyers": buyers,
        "local_result": local_result,
        "trade_result": trade_result,
        "candidate_visits": tuple(visit_node.candidate_visits),
        "right_of_entry": None
        if visit_node.right_of_entry_visit_key is None
        else _plain_visit_key(visit_node.right_of_entry_visit_key),
        "decision_window": tuple(
            _plain_visit_key(visit_key) for visit_key in leading_node.decision_window_visit_keys
        ),
        "confirmed_leading": tuple(
            _plain_visit_key(visit_key)
            for visit_key in leading_node.confirmed_leading_nonparticipating_visit_keys
        ),
        "remaining_window": tuple(
            _plain_visit_key(visit_key)
            for visit_key in leading_node.remaining_decision_window_visit_keys
        ),
        "collector": columns["collector"],
        "ranks_after_decision": _rank_map(world),
    }


def wrapped_driver(world):
    result = GATE.original_driver(world)
    if world is GATE.real_world:
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
    if type(virtual_timestep) is not int or type(virtual_timestep) is bool:
        return None
    if virtual_timestep < CANDIDATE_TRACE_MUST_INCLUDE_START:
        return None
    if virtual_timestep > CANDIDATE_TRACE_MUST_INCLUDE_END:
        return None
    buyers = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_state.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    return {
        "buyers": buyers,
        "virtual_timestep": virtual_timestep,
        "node": local_state.target_node,
        "local_state": local_state,
    }


def _outlink_by_name(node, link_name):
    outlinks = getattr(node, "outlinks", None)
    if isinstance(outlinks, dict):
        for link in outlinks.values():
            if getattr(link, "name", None) == link_name:
                return link
    return None


def _entry_open(outlink, world):
    if outlink is None:
        return None
    vehicles = getattr(outlink, "vehicles", None)
    lane_count = getattr(outlink, "number_of_lanes", None)
    if vehicles is None or type(lane_count) is not int:
        return None
    if len(vehicles) < lane_count:
        return True
    entrance = vehicles[-lane_count]
    delta = getattr(outlink, "delta_per_lane", None)
    deltan = getattr(world, "DELTAN", None)
    if delta is None or deltan is None:
        return None
    if entrance.x <= delta * deltan:
        return False
    return True


def _snapshot_binding_visit(node, binding_visit, vehicle):
    world = node.W
    link = getattr(vehicle, "link", None)
    on_inlink = (
        link is not None
        and getattr(link, "name", None) == binding_visit.inlink_name
        and getattr(link, "end_node", None) is node
    )
    is_head = False
    if on_inlink is True and len(link.vehicles) > 0 and link.vehicles[0] is vehicle:
        is_head = True
    outlink = _outlink_by_name(node, binding_visit.route_next_link_name)
    in_incoming = vehicle in node.incoming_vehicles
    out_capacity = None
    if outlink is not None:
        out_capacity = outlink.capacity_in_remain >= world.DELTAN
    in_capacity = None
    if on_inlink is True:
        in_capacity = link.capacity_out_remain >= world.DELTAN
    return {
        "on_target_inlink_before_judgment": on_inlink,
        "in_target_node_incoming_before_judgment": in_incoming,
        "is_physical_head_before_judgment": is_head,
        "current_link_name_before_judgment": None if link is None else link.name,
        "formal_inlink_name": binding_visit.inlink_name,
        "route_next_link_name": binding_visit.route_next_link_name,
        "entry_open_before_judgment": _entry_open(outlink, world),
        "outlink_capacity_available_before_judgment": out_capacity,
        "inlink_capacity_available_before_judgment": in_capacity,
        "clearance_satisfied_before_judgment": None,
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
                picture = _snapshot_binding_visit(
                    context["node"],
                    binding_visit,
                    pair.local_vehicle,
                )
                GATE.scan_before[(context["buyers"], context["virtual_timestep"], visit_key)] = picture
        if context["virtual_timestep"] not in GATE.candidate_scan_timesteps:
            GATE.candidate_scan_timesteps.append(context["virtual_timestep"])
    return GATE.original_binding_scan(binding_transfer_state)


def _actual_window(node) -> bool:
    if GATE.real_world is None or node.W is not GATE.real_world:
        return False
    if getattr(node.W, "_order_control_baseline_collector", None) is not None:
        return False
    if node.name != TARGET_NODE_NAME:
        return False
    timestep = node.W.T
    if type(timestep) is not int:
        return False
    if timestep < ACTUAL_TRACE_START or timestep > ACTUAL_TRACE_END:
        return False
    return True


def _count_wrapper_call(hook_name: str) -> None:
    GATE.wrapper_call_counts[hook_name] = GATE.wrapper_call_counts[hook_name] + 1


def _count_original_call(hook_name: str) -> None:
    GATE.original_call_counts[hook_name] = GATE.original_call_counts[hook_name] + 1


def _assigned_rank_now(node, visit_key):
    states = getattr(node.W, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return None
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return None
    try:
        return rank_state.assigned_rank(visit_key)
    except ValueError:
        return None


def _capture_attempt_state(node, vehicle, inlink, outlink, visit_key, previous):
    """Read link and node fields. Do not call a production judgment function."""
    arrived = vehicle in node.incoming_vehicles
    read_head = False
    if vehicle.link is inlink and len(inlink.vehicles) > 0 and inlink.vehicles[0] is vehicle:
        read_head = True
    route = getattr(vehicle, "route_next_link", None)
    live_route = None if route is None else getattr(route, "name", None)
    is_head = read_head
    head_formally_known = False
    clearance = None
    if previous is not None and previous["head_formally_known"] is True:
        is_head = previous["is_physical_head_before_attempt"]
        head_formally_known = True
    if previous is not None and previous["clearance_satisfied_before_attempt"] is not None:
        clearance = previous["clearance_satisfied_before_attempt"]
    return {
        "arrived_before_attempt": arrived,
        "in_target_incoming_before_attempt": arrived,
        "is_physical_head_before_attempt": is_head,
        "head_formally_known": head_formally_known,
        "current_link_name_before_attempt": None if vehicle.link is None else vehicle.link.name,
        "formal_inlink_name": inlink.name,
        "live_route_next_link_name_before_attempt": live_route,
        "entry_open_before_attempt": _entry_open(outlink, node.W),
        "outlink_capacity_available_before_attempt": outlink.capacity_in_remain >= node.W.DELTAN,
        "inlink_capacity_available_before_attempt": inlink.capacity_out_remain >= node.W.DELTAN,
        "clearance_satisfied_before_attempt": clearance,
        "assigned_rank_before_attempt": _assigned_rank_now(node, visit_key),
    }


def _refresh_slot_state(node, slot) -> None:
    candidate = slot["candidate"]
    previous = slot["state"]
    if previous is None:
        previous = slot["pre_scan_state"]
    slot["state"] = _capture_attempt_state(
        node,
        candidate.vehicle,
        candidate.inlink,
        candidate.outlink,
        candidate.visit_key,
        previous,
    )


def _active_actual_scan(node):
    scan = GATE.actual_scan
    if scan is None or node is None:
        return None
    if node is not scan["node"]:
        return None
    if _actual_window(node) is not True:
        return None
    return scan


def _open_slot_for_vehicle(scan, vehicle, inlink):
    for slot in scan["slots"]:
        if slot["finalized"] is True:
            continue
        candidate = slot["candidate"]
        if candidate.vehicle is vehicle and candidate.inlink is inlink:
            return slot
    return None


def _open_slot_for_shortage(scan, inlink, outlink):
    if len(inlink.vehicles) == 0:
        return None
    head_vehicle = inlink.vehicles[0]
    for slot in scan["slots"]:
        if slot["finalized"] is True:
            continue
        candidate = slot["candidate"]
        if candidate.vehicle is not head_vehicle:
            continue
        if candidate.inlink is inlink and candidate.outlink is outlink:
            return slot
    return None


def _begin_actual_scan(node, confirmed_candidates):
    GATE.actual_scan_serial = GATE.actual_scan_serial + 1
    slots = []
    scan_order = 0
    for candidate in confirmed_candidates:
        scan_order = scan_order + 1
        visit_key = _plain_visit_key(candidate.visit_key)
        vehicle = candidate.vehicle
        in_incoming = vehicle in node.incoming_vehicles
        pre_scan_state = _capture_attempt_state(
            node,
            vehicle,
            candidate.inlink,
            candidate.outlink,
            candidate.visit_key,
            None,
        )
        slots.append(
            {
                "candidate": candidate,
                "visit_key": visit_key,
                "scan_order": scan_order,
                "in_incoming_before_production": in_incoming,
                "pre_scan_state": pre_scan_state,
                "state": None,
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
    return {
        "token": GATE.actual_scan_serial,
        "node": node,
        "timestep": node.W.T,
        "slots": slots,
    }


def _read_committed_passage(node, visit_key):
    registry = getattr(node.W, "order_control_tvt_mp_actual_node_passage_history_registry", None)
    if registry is None:
        raise RuntimeError("Actual passage history registry is missing after transfer.")
    records = registry.records_by_node_name.get(node.name, ())
    matched = None
    for record in records:
        if _plain_visit_key(record.visit_key) != visit_key:
            continue
        if matched is not None:
            raise RuntimeError(
                f"Passage history has more than one record for {_visit_text(visit_key)}."
            )
        matched = record
    if matched is None:
        raise RuntimeError(
            f"Passed visit {_visit_text(visit_key)} has no committed passage history record."
        )
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


def _append_slot_event(scan, slot, earlier_attempted, earlier_passed, clearance_stop_visit) -> None:
    state = slot["state"]
    if state is None:
        state = dict(slot["pre_scan_state"])
        state["is_physical_head_before_attempt"] = None
        state["entry_open_before_attempt"] = None
        state["outlink_capacity_available_before_attempt"] = None
        state["inlink_capacity_available_before_attempt"] = None
        state["clearance_satisfied_before_attempt"] = None
    visit_key = slot["visit_key"]
    confirmation = GATE.rank_confirmation.get(visit_key)
    judgment = slot["judgment"]
    attempted, passed, temporary_skip_reason, stop_reason, not_reached = _judgment_columns(judgment)
    prior = ""
    if judgment == "not_reached":
        prior = clearance_stop_visit
    rank_value = None
    if passed is True:
        rank_value = slot["registry_rank"]
    GATE.actual_events.append(
        {
            "real_timestep": scan["timestep"],
            "node_name": scan["node"].name,
            "vehicle_name": visit_key[0],
            "visit_id": visit_key[1],
            "visit_key": _visit_text(visit_key),
            "visit_key_tuple": visit_key,
            "assigned_rank_before_attempt": state["assigned_rank_before_attempt"],
            "rank_confirmation_decision_timestep": None
            if confirmation is None
            else confirmation["decision_timestep"],
            "rank_confirmation_source": None if confirmation is None else confirmation["source"],
            "attempted": attempted,
            "passed": passed,
            "temporary_skip_reason": temporary_skip_reason,
            "stop_reason": stop_reason,
            "not_reached": not_reached,
            "earlier_attempted_visit_keys": "|".join(earlier_attempted),
            "earlier_passed_visit_keys": "|".join(earlier_passed),
            "arrived_before_attempt": state["arrived_before_attempt"],
            "in_target_incoming_before_attempt": state["in_target_incoming_before_attempt"],
            "is_physical_head_before_attempt": state["is_physical_head_before_attempt"],
            "current_link_name_before_attempt": state["current_link_name_before_attempt"],
            "formal_inlink_name": state["formal_inlink_name"],
            "live_route_next_link_name_before_attempt": state[
                "live_route_next_link_name_before_attempt"
            ],
            "entry_open_before_attempt": state["entry_open_before_attempt"],
            "outlink_capacity_available_before_attempt": state[
                "outlink_capacity_available_before_attempt"
            ],
            "inlink_capacity_available_before_attempt": state[
                "inlink_capacity_available_before_attempt"
            ],
            "clearance_satisfied_before_attempt": state["clearance_satisfied_before_attempt"],
            "actual_passage_rank_if_passed": rank_value,
            "production_judgment": judgment,
            "prior_clearance_stop_visit_key": prior,
            "called_head": slot["called_head"],
            "head_result": slot["head_result"],
            "called_clearance": slot["called_clearance"],
            "clearance_result": slot["clearance_result"],
            "called_shortage": slot["called_shortage"],
            "shortage_result": slot["shortage_result"],
            "called_transfer": slot["called_transfer"],
            "registry_passage_timestep": slot["registry_passage_timestep"],
            "scan_token": scan["token"],
            "scan_order": slot["scan_order"],
            "scan_stopped_here": judgment == "clearance_not_satisfied",
        }
    )


def _finish_actual_scan(scan) -> None:
    earlier_attempted = []
    earlier_passed = []
    clearance_stop_visit = None
    for slot in scan["slots"]:
        if slot["finalized"] is not True:
            hook_called = (
                slot["called_head"] is True
                or slot["called_clearance"] is True
                or slot["called_shortage"] is True
                or slot["called_transfer"] is True
            )
            if clearance_stop_visit is not None:
                if hook_called is True:
                    raise RuntimeError(
                        f"{_visit_text(slot['visit_key'])} was judged after a clearance stop."
                    )
                slot["judgment"] = "not_reached"
                slot["finalized"] = True
            elif slot["in_incoming_before_production"] is not True:
                if hook_called is True:
                    raise RuntimeError(
                        f"{_visit_text(slot['visit_key'])} was not in incoming_vehicles "
                        "but a production judgment hook ran."
                    )
                slot["judgment"] = "not_in_incoming"
                slot["finalized"] = True
            else:
                raise RuntimeError(
                    f"{_visit_text(slot['visit_key'])} at real T={scan['timestep']} "
                    "was in incoming_vehicles before the scan and received no production judgment."
                )
        if slot["judgment"] == "passed":
            rank_value, passage_timestep = _read_committed_passage(scan["node"], slot["visit_key"])
            slot["registry_rank"] = rank_value
            slot["registry_passage_timestep"] = passage_timestep
        _append_slot_event(
            scan,
            slot,
            earlier_attempted,
            earlier_passed,
            clearance_stop_visit,
        )
        if slot["judgment"] == "clearance_not_satisfied":
            clearance_stop_visit = _visit_text(slot["visit_key"])
        attempted, passed, _temporary, _stop, _not_reached = _judgment_columns(slot["judgment"])
        if attempted is True:
            earlier_attempted.append(_visit_text(slot["visit_key"]))
        if passed is True:
            earlier_passed.append(_visit_text(slot["visit_key"]))


def _remember_missing_slot(scan, hook_name: str) -> None:
    raise RuntimeError(
        f"Actual {hook_name} hook at real T={scan['timestep']} "
        "did not match an open confirmed candidate."
    )


def wrapped_try_confirmed(node, confirmed_candidates):
    _count_wrapper_call("try_confirmed")
    scan = None
    if _actual_window(node) is True:
        scan = _begin_actual_scan(node, confirmed_candidates)
        GATE.actual_scan = scan
    completed = False
    try:
        result = GATE.original_try_confirmed(node, confirmed_candidates)
        completed = True
    finally:
        _count_original_call("try_confirmed")
        GATE.actual_scan = None
    if scan is not None and completed is True:
        _finish_actual_scan(scan)
    return result


def wrapped_head_skip(vehicle, inlink):
    _count_wrapper_call("head_skip")
    node = getattr(inlink, "end_node", None)
    scan = _active_actual_scan(node)
    slot = None
    if scan is not None:
        slot = _open_slot_for_vehicle(scan, vehicle, inlink)
        if slot is not None:
            _refresh_slot_state(node, slot)
    result = GATE.original_head_skip(vehicle, inlink)
    _count_original_call("head_skip")
    if scan is not None and slot is None:
        _remember_missing_slot(scan, "head_skip")
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
    _count_wrapper_call("clearance")
    scan = _active_actual_scan(node)
    slot = None
    if scan is not None:
        slot = _open_slot_for_vehicle(scan, vehicle, inlink)
        if slot is not None:
            _refresh_slot_state(node, slot)
    result = GATE.original_clearance(node, vehicle, inlink)
    _count_original_call("clearance")
    if scan is not None and slot is None:
        _remember_missing_slot(scan, "clearance")
    if slot is not None:
        slot["called_clearance"] = True
        slot["clearance_result"] = result
        slot["state"]["clearance_satisfied_before_attempt"] = result is False
        if result is True:
            slot["judgment"] = "clearance_not_satisfied"
            slot["finalized"] = True
    return result


def wrapped_shortage(node, inlink, outlink):
    _count_wrapper_call("shortage")
    scan = _active_actual_scan(node)
    slot = None
    if scan is not None:
        slot = _open_slot_for_shortage(scan, inlink, outlink)
        if slot is not None:
            _refresh_slot_state(node, slot)
    result = GATE.original_shortage(node, inlink, outlink)
    _count_original_call("shortage")
    if scan is not None and slot is None:
        _remember_missing_slot(scan, "shortage")
    if slot is not None:
        slot["called_shortage"] = True
        slot["shortage_result"] = result
        if result is not None:
            slot["judgment"] = result
            slot["finalized"] = True
    return result


def wrapped_actual_transfer(node, vehicle, inlink, outlink):
    _count_wrapper_call("actual_transfer")
    scan = _active_actual_scan(node)
    slot = None
    if scan is not None:
        slot = _open_slot_for_vehicle(scan, vehicle, inlink)
        if slot is not None and slot["candidate"].outlink is not outlink:
            slot = None
        if slot is not None:
            _refresh_slot_state(node, slot)
    result = GATE.original_actual_transfer(node, vehicle, inlink, outlink)
    _count_original_call("actual_transfer")
    if scan is not None and slot is None:
        _remember_missing_slot(scan, "actual_transfer")
    if slot is not None:
        slot["called_transfer"] = True
        slot["judgment"] = "passed"
        slot["finalized"] = True
    return result


def wrapped_arrival(vehicle, node):
    result = GATE.original_arrival(vehicle, node)
    if vehicle.W is not GATE.real_world:
        return result
    if getattr(vehicle.W, "_order_control_baseline_collector", None) is not None:
        return result
    if node is None:
        return result
    if node.name != TARGET_NODE_NAME:
        return result
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return result
    if current_visit.get("node") is not node:
        return result
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return result
    arrival_time = current_visit.get("arrival_time")
    if arrival_time is None:
        return result
    formal_timestep = _formal_arrival_timestep_from_time(arrival_time, vehicle.W.DELTAT)
    key = (vehicle.name, visit_id)
    if key not in GATE.actual_arrivals:
        if formal_timestep != vehicle.W.T:
            raise RuntimeError(
                f"First actual arrival for {_visit_text(key)}: formal timestep "
                f"{formal_timestep} does not match World.T={vehicle.W.T}."
            )
        GATE.actual_arrivals[key] = formal_timestep
    else:
        stored_timestep = GATE.actual_arrivals[key]
        from_production = _formal_arrival_timestep_from_time(arrival_time, vehicle.W.DELTAT)
        if stored_timestep != from_production:
            raise RuntimeError(
                f"Re-registration for {_visit_text(key)} at T={vehicle.W.T}: production "
                f"arrival_time implies timestep {from_production}, stored {stored_timestep}."
            )
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Diagnostic hooks are already installed.")
    local_scan = local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    binding_scan = binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    if local_scan is not binding_scan:
        raise RuntimeError("Binding scan references are not the same function.")
    GATE.real_world = real_world
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_binding_scan = (
        local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep
    )
    GATE.original_try_confirmed = physical_module._try_confirmed_candidates
    GATE.original_head_skip = physical_module._inlink_physical_head_should_skip
    GATE.original_clearance = uxsim_module.Node._order_control_clearance_blocks_passage
    GATE.original_shortage = physical_module._first_ordinary_physical_shortage
    GATE.original_actual_transfer = uxsim_module.Node._transfer_one_vehicle_between_links
    GATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    driver_module.run_tvt_mp_driver = wrapped_driver
    local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        wrapped_binding_scan
    )
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = wrapped_binding_scan
    physical_module._try_confirmed_candidates = wrapped_try_confirmed
    physical_module._inlink_physical_head_should_skip = wrapped_head_skip
    uxsim_module.Node._order_control_clearance_blocks_passage = wrapped_clearance
    physical_module._first_ordinary_physical_shortage = wrapped_shortage
    uxsim_module.Node._transfer_one_vehicle_between_links = wrapped_actual_transfer
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_driver
    local_calc_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        GATE.original_binding_scan
    )
    binding_module.scan_and_transfer_tvt_mp_binding_visits_at_current_timestep = (
        GATE.original_binding_scan
    )
    physical_module._try_confirmed_candidates = GATE.original_try_confirmed
    physical_module._inlink_physical_head_should_skip = GATE.original_head_skip
    uxsim_module.Node._order_control_clearance_blocks_passage = GATE.original_clearance
    physical_module._first_ordinary_physical_shortage = GATE.original_shortage
    uxsim_module.Node._transfer_one_vehicle_between_links = GATE.original_actual_transfer
    uxsim_module.Vehicle.record_order_control_node_arrival = GATE.original_arrival
    GATE.original_driver = None
    GATE.original_binding_scan = None
    GATE.original_try_confirmed = None
    GATE.original_head_skip = None
    GATE.original_clearance = None
    GATE.original_shortage = None
    GATE.original_actual_transfer = None
    GATE.original_arrival = None
    GATE.actual_scan = None
    GATE.installed = False


def _role_of(trade_result, visit_key) -> str:
    buyers = {_plain_visit_key(item) for item in trade_result.buyers_sorted}
    sellers = {_plain_visit_key(item) for item in trade_result.sellers_sorted}
    nonparticipating = {_plain_visit_key(item) for item in trade_result.nonparticipating_visits_sorted}
    if visit_key in buyers:
        return "buyer"
    if visit_key in sellers:
        return "seller"
    if visit_key in nonparticipating:
        return "nonparticipating"
    return ""


def _passage_maps(local_result):
    candidate_passage = {}
    for record in local_result.required_passage_records:
        visit_key = _plain_visit_key(record.visit_key)
        candidate_passage[visit_key] = record.candidate_passage_timestep
    for timestep_result in local_result.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        for visit_key in binding_result.transferred_binding_visit_keys:
            plain = _plain_visit_key(visit_key)
            if plain not in candidate_passage or candidate_passage[plain] is None:
                candidate_passage[plain] = binding_result.virtual_timestep
    return candidate_passage


def _history_by_visit(world) -> dict:
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    records = registry.records_by_node_name.get(TARGET_NODE_NAME, ())
    by_visit = {}
    for record in records:
        by_visit[_plain_visit_key(record.visit_key)] = record
    return by_visit


def _build_rank_rows(world, bundle) -> list:
    selected = GATE.selected
    local_result = selected["local_result"]
    sequence = local_result.binding_rank_sequence
    trade_result = selected["trade_result"]
    candidate_visits = selected["candidate_visits"]
    baseline_order = []
    baseline_rank = {}
    position = 0
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                "candidate_visits element is not OrderControlTvtCandidateVisit: "
                f"{type(candidate_visit).__name__}."
            )
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in baseline_rank:
            raise RuntimeError(
                f"Duplicate candidate visit key in candidate_visits: {_visit_text(visit_key)}."
            )
        position = position + 1
        baseline_order.append(visit_key)
        baseline_rank[visit_key] = position
    if len(baseline_rank) != len(candidate_visits):
        raise RuntimeError(
            "baseline_rank size differs from candidate_visits size: "
            f"{len(baseline_rank)} != {len(candidate_visits)}."
        )
    binding_by_key = {}
    for binding_visit in sequence.visits_in_binding_order:
        binding_by_key[_plain_visit_key(binding_visit.visit_key)] = binding_visit
    trade_scope = {
        _plain_visit_key(visit_key) for visit_key in trade_result.trade_scope
    }
    candidate_passage = _passage_maps(local_result)
    history = _history_by_visit(world)
    research_by_key = {}
    for row in bundle.visits:
        if row.node_name != TARGET_NODE_NAME:
            continue
        if row.tvt_decision_timestep != TARGET_DECISION_TIMESTEP:
            continue
        research_by_key[(row.vehicle_name, row.visit_id)] = row
    keys = list(baseline_order)
    for visit_key, record in history.items():
        if ACTUAL_RANK_WINDOW_START <= record.actual_node_passage_rank <= ACTUAL_RANK_WINDOW_END:
            if visit_key not in baseline_rank:
                keys.append(visit_key)
    rows = []
    for visit_key in keys:
        binding_visit = binding_by_key.get(visit_key)
        confirmation = GATE.rank_confirmation.get(visit_key)
        history_record = history.get(visit_key)
        research = research_by_key.get(visit_key)
        snapshot = None
        if visit_key in baseline_rank:
            snapshot = selected["collector"].get_baseline_visit_snapshot(
                visit_key[0],
                visit_key[1],
            )
        candidate_local = None
        if visit_key in baseline_rank:
            try:
                candidate_local = trade_result.assigned_rank(visit_key)
            except ValueError:
                candidate_local = None
        candidate_node = selected["ranks_after_decision"].get(visit_key)
        vehicle = world.VEHICLES.get(visit_key[0])
        participates = None
        if vehicle is not None:
            participates = vehicle.participates_in_order_exchange
        formal_route = None
        rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
        if isinstance(rank_state, OrderControlTvtNodeRankState):
            formal_route = rank_state.formal_route_next_link_name(visit_key)
        actual_rank = None if history_record is None else history_record.actual_node_passage_rank
        actual_passage = None if history_record is None else history_record.actual_passage_timestep
        candidate_time = candidate_passage.get(visit_key)
        baseline_passage = None if snapshot is None else snapshot.get("baseline_passage_timestep")
        difference = None
        if candidate_time is not None and actual_passage is not None:
            difference = candidate_time - actual_passage
        role = _role_of(trade_result, visit_key)
        if role == "" and research is not None:
            role = research.role
        rows.append(
            {
                "scenario_name": DIAGNOSTIC_SCENARIO_NAME,
                "target_decision_timestep": TARGET_DECISION_TIMESTEP,
                "target_node_name": TARGET_NODE_NAME,
                "selected_candidate_identity": selected["identity"],
                "selected_candidate_evaluation_index": selected["evaluation_index"],
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "participates_in_order_exchange": participates,
                "role": role,
                "is_right_of_entry_holder": visit_key == selected["right_of_entry"],
                "in_candidate_visits": visit_key in baseline_rank,
                "in_trade_scope": visit_key in trade_scope,
                "in_decision_window": visit_key in selected["decision_window"],
                "in_confirmed_leading_nonparticipating": visit_key in selected["confirmed_leading"],
                "in_remaining_decision_window": visit_key in selected["remaining_window"],
                "in_outside_trade_scope_inside_k_fixed": binding_visit is not None
                and binding_visit.binding_partition.value == "outside_trade_scope_inside_k_fixed",
                "in_binding_sequence": binding_visit is not None,
                "binding_partition": None if binding_visit is None else binding_visit.binding_partition.value,
                "baseline_local_rank": baseline_rank.get(visit_key),
                "candidate_local_rank": candidate_local,
                "candidate_node_continuous_rank": candidate_node,
                "actual_node_continuous_rank": actual_rank,
                "rank_confirmation_decision_timestep": None
                if confirmation is None
                else confirmation["decision_timestep"],
                "rank_confirmation_source": None if confirmation is None else confirmation["source"],
                "baseline_arrival_timestep": None
                if snapshot is None
                else snapshot.get("baseline_arrival_timestep"),
                "baseline_arrival_tiebreaker": None
                if snapshot is None
                else snapshot.get("arrival_tiebreaker"),
                "actual_arrival_timestep": GATE.actual_arrivals.get(visit_key),
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_time,
                "actual_passage_timestep": actual_passage,
                "formal_route_next_link_name": formal_route,
                "predicted_route_next_link_name": None
                if research is None
                else research.predicted_route_next_link_name,
                "actual_route_next_link_name": None
                if history_record is None
                else history_record.actual_route_next_link_name,
                "candidate_minus_actual_passage_timesteps": difference,
                "_sort_baseline": baseline_rank.get(visit_key, 10**9),
                "_sort_actual": 10**9 if actual_rank is None else actual_rank,
            }
        )
    rows.sort(key=lambda item: (item["_sort_baseline"], item["_sort_actual"], item["visit_key"]))
    for row in rows:
        row.pop("_sort_baseline")
        row.pop("_sort_actual")
    return rows


def _clearance_from_formal_candidate_scan(passed, stopped, stop_reason, skip_reason, not_reached):
    if not_reached is True:
        return None
    stop_enum = binding_module.OrderControlTvtMpBindingTransferStopReason
    if stopped is True and stop_reason is stop_enum.CLEARANCE_NOT_SATISFIED:
        return False
    if passed is True:
        return True
    skip_enum = binding_module.OrderControlTvtMpBindingVisitTemporarySkipReason
    if skip_reason is skip_enum.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE:
        return True
    if skip_reason is skip_enum.NODE_FLOW_CAPACITY_UNAVAILABLE:
        return True
    if skip_reason is skip_enum.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE:
        return True
    if skip_reason is skip_enum.OUTLINK_ENTRY_SPACE_UNAVAILABLE:
        return True
    if skip_reason is skip_enum.NOT_ARRIVED_AT_TARGET_NODE:
        return None
    if skip_reason is skip_enum.NOT_INLINK_PHYSICAL_HEAD:
        return None
    return None


def _candidate_timestep_in_trace(virtual_timestep) -> bool:
    if type(virtual_timestep) is not int or type(virtual_timestep) is bool:
        return False
    if virtual_timestep < CANDIDATE_TRACE_MUST_INCLUDE_START:
        return False
    if virtual_timestep > CANDIDATE_TRACE_MUST_INCLUDE_END:
        return False
    return True


def _build_candidate_events() -> list:
    selected = GATE.selected
    local_result = selected["local_result"]
    sequence = local_result.binding_rank_sequence
    visits = sequence.visits_in_binding_order
    buyers = selected["buyers"]
    rows = []
    already_passed = set()
    for timestep_result in local_result.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        virtual_timestep = binding_result.virtual_timestep
        keep_timestep = _candidate_timestep_in_trace(virtual_timestep)
        transferred = {_plain_visit_key(item) for item in binding_result.transferred_binding_visit_keys}
        skipped = {}
        for skip in binding_result.temporarily_skipped_visits:
            skipped[_plain_visit_key(skip.binding_visit_key)] = skip.skip_reason
        stopped_key = None
        if binding_result.stopped_binding_visit_key is not None:
            stopped_key = _plain_visit_key(binding_result.stopped_binding_visit_key)
        blocked = False
        earlier_attempted = []
        earlier_passed = []
        scan_order = 0
        for binding_visit in visits:
            scan_order = scan_order + 1
            visit_key = _plain_visit_key(binding_visit.visit_key)
            picture = GATE.scan_before.get((buyers, virtual_timestep, visit_key), {})
            passed = visit_key in transferred
            skip_reason = skipped.get(visit_key)
            skip_reason_text = ""
            if skip_reason is not None:
                skip_reason_text = skip_reason.value
            stopped = stopped_key == visit_key
            not_reached = blocked is True
            attempted = not_reached is not True and visit_key not in already_passed
            if visit_key in already_passed:
                attempted = False
            clearance_satisfied = _clearance_from_formal_candidate_scan(
                passed,
                stopped,
                binding_result.stop_reason,
                skip_reason,
                not_reached,
            )
            row = {
                "candidate_identity": selected["identity"],
                "candidate_evaluation_index": selected["evaluation_index"],
                "virtual_timestep": virtual_timestep,
                "scan_order": scan_order,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "binding_rank": binding_visit.binding_rank,
                "binding_partition": binding_visit.binding_partition.value,
                "attempted": attempted,
                "passed": passed,
                "temporarily_skipped": skip_reason is not None,
                "skip_reason": skip_reason_text,
                "stopped": stopped,
                "stop_reason": binding_result.stop_reason.value if stopped is True else "",
                "not_reached_because_prior_clearance_stop": not_reached,
                "earlier_attempted_visit_keys": "|".join(earlier_attempted),
                "earlier_passed_visit_keys": "|".join(earlier_passed),
                "baseline_arrival_timestep": picture.get(
                    "baseline_arrival_timestep",
                    binding_visit.baseline_arrival_timestep,
                ),
                "on_target_inlink_before_judgment": picture.get("on_target_inlink_before_judgment"),
                "in_target_node_incoming_before_judgment": picture.get(
                    "in_target_node_incoming_before_judgment"
                ),
                "is_physical_head_before_judgment": picture.get("is_physical_head_before_judgment"),
                "current_link_name_before_judgment": picture.get("current_link_name_before_judgment"),
                "formal_inlink_name": picture.get("formal_inlink_name", binding_visit.inlink_name),
                "route_next_link_name": picture.get(
                    "route_next_link_name",
                    binding_visit.route_next_link_name,
                ),
                "entry_open_before_judgment": picture.get("entry_open_before_judgment"),
                "outlink_capacity_available_before_judgment": picture.get(
                    "outlink_capacity_available_before_judgment"
                ),
                "inlink_capacity_available_before_judgment": picture.get(
                    "inlink_capacity_available_before_judgment"
                ),
                "clearance_satisfied_before_judgment": clearance_satisfied,
                "passage_timestep_if_passed": virtual_timestep if passed is True else None,
            }
            if keep_timestep is True:
                rows.append(row)
            if attempted is True:
                earlier_attempted.append(_visit_text(visit_key))
            if passed is True:
                earlier_passed.append(_visit_text(visit_key))
                already_passed.add(visit_key)
            if stopped is True:
                blocked = True
    return rows


def _build_later_rows(history) -> list:
    rows = []
    target_record = history.get(TARGET_NONPARTICIPATING)
    target_passage = None if target_record is None else target_record.actual_passage_timestep
    target_rank = None if target_record is None else target_record.actual_node_passage_rank
    for visit_key, confirmation in GATE.rank_confirmation.items():
        if confirmation["decision_timestep"] <= TARGET_DECISION_TIMESTEP:
            continue
        record = history.get(visit_key)
        if record is None:
            continue
        in_window = ACTUAL_RANK_WINDOW_START <= record.actual_node_passage_rank <= ACTUAL_RANK_WINDOW_END
        before_target = (
            target_passage is not None and record.actual_passage_timestep < target_passage
        )
        if in_window is not True and before_target is not True:
            continue
        relation = "later_decision_visit"
        if before_target is True:
            relation = "passed_before_target_nonparticipating"
        elif target_rank is not None and record.actual_node_passage_rank < target_rank:
            relation = "actual_rank_before_target"
        rows.append(
            {
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "rank_confirmation_decision_timestep": confirmation["decision_timestep"],
                "assigned_rank": confirmation["assigned_rank"],
                "actual_arrival_timestep": GATE.actual_arrivals.get(visit_key),
                "actual_passage_timestep": record.actual_passage_timestep,
                "actual_node_passage_rank": record.actual_node_passage_rank,
                "relation_to_target_nonparticipating": relation,
                "whether_passed_before_target": before_target,
                "whether_assigned_after_target_decision": True,
            }
        )
    rows.sort(key=lambda item: (item["actual_node_passage_rank"], item["visit_key"]))
    return rows


def _row_for(rows, visit_key):
    text = _visit_text(visit_key)
    for row in rows:
        if row["visit_key"] == text:
            return row
    return None


def _event_at(rows, visit_key, timestep, time_field):
    text = _visit_text(visit_key)
    for row in rows:
        if row["visit_key"] == text and row[time_field] == timestep:
            return row
    return None


def _build_summary(
    rank_rows,
    candidate_events,
    later_rows,
    world,
    completion,
    extended_counts,
) -> str:
    target = _row_for(rank_rows, TARGET_NONPARTICIPATING)
    lines = [
        "T=382 northwest_intersection selected candidate rank and passage trace (eval_1000 diagnostic)",
        f"scenario: {DIAGNOSTIC_SCENARIO_NAME}",
        f"diagnostic evaluation: T=0..{DIAGNOSTIC_EVALUATION_END_TIMESTEP}",
        f"internal TSIZE: {DIAGNOSTIC_INTERNAL_TSIZE}",
        f"World.T after simulation: {world.T}",
        f"completed trip count: {completion['completed_trip_count']}",
        f"incomplete vehicle count: {completion['incomplete_vehicle_count']}",
        f"extended transaction count: {extended_counts['transaction_count']}",
        f"extended buyer visits: {extended_counts['buyer_visit_count']}",
        f"extended seller visits: {extended_counts['seller_visit_count']}",
        f"extended nonparticipating visits: {extended_counts['nonparticipating_visit_count']}",
        (
            "extended passage comparison: "
            f"both_observed={extended_counts['both_candidate_and_actual_observed_count']} "
            f"equal={extended_counts['equal_candidate_actual_passage_count']} "
            f"unequal={extended_counts['unequal_candidate_actual_passage_count']} "
            f"unobserved={extended_counts['actual_passage_unobserved_count']}"
        ),
        f"selected candidate: {None if GATE.selected is None else GATE.selected['identity']}",
        "",
    ]
    if target is None:
        lines.append("対象nonparticipating Visitの横並び行がありません。")
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            f"対象 {_visit_text(TARGET_NONPARTICIPATING)}",
            f"  baseline arrival: {target['baseline_arrival_timestep']}",
            f"  actual arrival: {target['actual_arrival_timestep']}",
            f"  baseline passage: {target['baseline_passage_timestep']}",
            f"  candidate passage: {target['candidate_passage_timestep']}",
            f"  actual passage: {target['actual_passage_timestep']}",
            f"  baseline local rank: {target['baseline_local_rank']}",
            f"  candidate local rank: {target['candidate_local_rank']}",
            f"  candidate node continuous rank: {target['candidate_node_continuous_rank']}",
            f"  actual node continuous rank: {target['actual_node_continuous_rank']}",
            "",
        ]
    )
    candidate_403 = _event_at(candidate_events, TARGET_NONPARTICIPATING, 403, "virtual_timestep")
    actual_403 = _event_at(GATE.actual_events, TARGET_NONPARTICIPATING, 403, "real_timestep")
    actual_404 = _event_at(GATE.actual_events, TARGET_NONPARTICIPATING, 404, "real_timestep")
    lines.append("Candidate T=403:")
    if candidate_403 is None:
        lines.append("  記録なし。")
    else:
        lines.append(
            "  "
            f"passed={candidate_403['passed']} skip={candidate_403['skip_reason']} "
            f"stop={candidate_403['stop_reason']} "
            f"incoming={candidate_403['in_target_node_incoming_before_judgment']} "
            f"head={candidate_403['is_physical_head_before_judgment']} "
            f"entry_open={candidate_403['entry_open_before_judgment']} "
            f"clearance={candidate_403['clearance_satisfied_before_judgment']}"
        )
    lines.append("Actual T=403:")
    if actual_403 is None:
        lines.append("  記録なし。直接の不通過理由は未確定。")
    else:
        lines.append(
            "  "
            f"judgment={actual_403['production_judgment']} "
            f"passed={actual_403['passed']} skip={actual_403['temporary_skip_reason']} "
            f"stop={actual_403['stop_reason']} not_reached={actual_403['not_reached']} "
            f"prior_clearance_stop={actual_403['prior_clearance_stop_visit_key']} "
            f"incoming={actual_403['in_target_incoming_before_attempt']} "
            f"head={actual_403['is_physical_head_before_attempt']} "
            f"entry_open={actual_403['entry_open_before_attempt']} "
            f"clearance={actual_403['clearance_satisfied_before_attempt']}"
        )
        lines.append(
            "  earlier attempted: " + str(actual_403["earlier_attempted_visit_keys"])
        )
        lines.append("  earlier passed: " + str(actual_403["earlier_passed_visit_keys"]))
    lines.append("Actual T=404:")
    if actual_404 is None:
        lines.append("  記録なし。")
    else:
        lines.append(
            "  "
            f"judgment={actual_404['production_judgment']} "
            f"passed={actual_404['passed']} skip={actual_404['temporary_skip_reason']} "
            f"stop={actual_404['stop_reason']} "
            f"rank={actual_404['actual_passage_rank_if_passed']} "
            f"incoming={actual_404['in_target_incoming_before_attempt']} "
            f"head={actual_404['is_physical_head_before_attempt']} "
            f"entry_open={actual_404['entry_open_before_attempt']} "
            f"clearance={actual_404['clearance_satisfied_before_attempt']}"
        )
    lines.append("")
    lines.append("T=382より後に順位確定し、対象より先に通過したVisit、またはActual順位174〜180のVisit:")
    if len(later_rows) == 0:
        lines.append("  なし。")
    for row in later_rows:
        lines.append(
            "  "
            f"{row['visit_key']} decision T={row['rank_confirmation_decision_timestep']} "
            f"assigned_rank={row['assigned_rank']} "
            f"actual passage T={row['actual_passage_timestep']} "
            f"actual rank={row['actual_node_passage_rank']} "
            f"before_target={row['whether_passed_before_target']}"
        )
    lines.append("")
    direct = "未確定"
    if actual_403 is not None:
        judgment = actual_403["production_judgment"]
        if judgment == "not_reached":
            prior = actual_403["prior_clearance_stop_visit_key"]
            direct = f"not_reached_because_prior_clearance_stop ({prior})"
        elif judgment == "passed":
            direct = "actual T=403では通過している。期待と異なる。"
        else:
            direct = judgment
    before_count = 0
    for row in later_rows:
        if row["whether_passed_before_target"] is True:
            before_count = before_count + 1
    lines.append(f"Actual T=403の直接判定理由: {direct}")
    lines.append(
        "後続decision Visitの介在: "
        f"{before_count} VisitがT=382より後に順位確定し、対象より先にActual通過した。"
    )
    lines.append(
        "この診断は反実仮想を再実行しない。"
        "後続decision Visitが1 timestep差の必要条件かどうかは、直接判定理由とは別に未証明である。"
        "確定したのは、productionの逐次判定hookが返した直接理由と、後続decision Visitが対象より先に通過した事実である。"
    )
    return "\n".join(lines) + "\n"


def _require_one_actual_event(visit_key, timestep):
    text = _visit_text(visit_key)
    found = []
    for row in GATE.actual_events:
        if row["visit_key"] == text and row["real_timestep"] == timestep:
            found.append(row)
    if len(found) != 1:
        raise RuntimeError(
            f"{text} at real T={timestep} has {len(found)} actual events; expected one."
        )
    return found[0]


def _individual_hook_called(row) -> bool:
    if row["called_head"] is True:
        return True
    if row["called_clearance"] is True:
        return True
    if row["called_shortage"] is True:
        return True
    if row["called_transfer"] is True:
        return True
    return False


def _require_nonpassage_stage(row) -> None:
    stage = row["production_judgment"]
    if stage == "not_in_incoming":
        if row["temporary_skip_reason"] != "not_in_incoming" or row["stop_reason"] != "":
            raise RuntimeError("Actual not_in_incoming stage does not match the event columns.")
        if row["attempted"] is not False or row["passed"] is not False or row["not_reached"] is not False:
            raise RuntimeError("Actual not_in_incoming stage has the wrong attempt flags.")
        if _individual_hook_called(row) is True:
            raise RuntimeError("Actual not_in_incoming stage received an individual judgment hook.")
        return
    if stage == "not_inlink_physical_head":
        if row["called_head"] is not True or row["head_result"] is not True:
            raise RuntimeError("Actual physical-head skip is missing the formal head result.")
        if row["temporary_skip_reason"] != "not_inlink_physical_head" or row["stop_reason"] != "":
            raise RuntimeError("Actual physical-head skip columns do not match the formal result.")
        if row["attempted"] is not True or row["passed"] is not False:
            raise RuntimeError("Actual physical-head skip flags are wrong.")
        if row["called_clearance"] is True or row["called_shortage"] is True or row["called_transfer"] is True:
            raise RuntimeError("Actual physical-head skip continued to a later judgment hook.")
        return
    if stage == "clearance_not_satisfied":
        if row["called_head"] is not True or row["head_result"] is not False:
            raise RuntimeError("Actual clearance stop is missing the formal head pass.")
        if row["called_clearance"] is not True or row["clearance_result"] is not True:
            raise RuntimeError("Actual clearance stop is missing the formal clearance result.")
        if row["stop_reason"] != "clearance_not_satisfied" or row["temporary_skip_reason"] != "":
            raise RuntimeError("Actual clearance stop columns do not match the formal result.")
        if row["attempted"] is not True or row["passed"] is not False:
            raise RuntimeError("Actual clearance stop flags are wrong.")
        if row["called_shortage"] is True or row["called_transfer"] is True:
            raise RuntimeError("Actual clearance stop continued to a later judgment hook.")
        return
    if stage in FORMAL_ORDINARY_SHORTAGE_REASONS:
        if row["called_shortage"] is not True or row["shortage_result"] != stage:
            raise RuntimeError("Actual ordinary shortage is missing the formal shortage result.")
        if row["temporary_skip_reason"] != stage or row["stop_reason"] != "":
            raise RuntimeError("Actual ordinary shortage columns do not match the formal result.")
        if row["attempted"] is not True or row["passed"] is not False or row["not_reached"] is not False:
            raise RuntimeError("Actual ordinary shortage flags are wrong.")
        if row["scan_stopped_here"] is True:
            raise RuntimeError("Actual ordinary shortage is treated as a scan stop.")
        if row["called_transfer"] is True:
            raise RuntimeError("Actual ordinary shortage also transferred.")
        return
    if stage == "not_reached":
        if row["not_reached"] is not True or row["attempted"] is not False or row["passed"] is not False:
            raise RuntimeError("Actual not_reached flags are wrong.")
        if row["stop_reason"] != "" or row["temporary_skip_reason"] != "":
            raise RuntimeError("Actual not_reached carries its own skip or stop reason.")
        if row["prior_clearance_stop_visit_key"] == "":
            raise RuntimeError("Actual not_reached does not name the prior clearance stop.")
        if _individual_hook_called(row) is True:
            raise RuntimeError("Actual not_reached received an individual judgment hook.")
        return
    raise RuntimeError(
        f"Actual non-passage stage {stage!r} is not one of the formal production outcomes."
    )


def _validate_actual_hook_call_counts() -> None:
    for hook_name in ACTUAL_SEQUENTIAL_HOOK_NAMES:
        wrapper_calls = GATE.wrapper_call_counts[hook_name]
        original_calls = GATE.original_call_counts[hook_name]
        if wrapper_calls != original_calls:
            raise RuntimeError(
                f"Actual hook {hook_name} called its original {original_calls} times "
                f"across {wrapper_calls} wrapper calls."
            )


def _validate_actual_scans(world) -> None:
    seen = {}
    for row in GATE.actual_events:
        key = (row["real_timestep"], row["visit_key"])
        if key in seen:
            raise RuntimeError(
                f"Actual event is duplicated for {row['visit_key']} at real T={row['real_timestep']}."
            )
        seen[key] = True
    history = _history_by_visit(world)
    for row in GATE.actual_events:
        if row["passed"] is not True:
            continue
        record = history.get(row["visit_key_tuple"])
        if record is None:
            raise RuntimeError(
                f"Passed actual event {row['visit_key']} at real T={row['real_timestep']} "
                "has no formal passage-history record."
            )
        if row["actual_passage_rank_if_passed"] != record.actual_node_passage_rank:
            raise RuntimeError(
                f"Passed actual event {row['visit_key']} rank does not match the formal registry."
            )
        if record.actual_passage_timestep != row["real_timestep"]:
            raise RuntimeError(
                f"Passed actual event {row['visit_key']} passage timestep does not match "
                "the event timestep."
            )
        if row["registry_passage_timestep"] != row["real_timestep"]:
            raise RuntimeError(
                f"Passed actual event {row['visit_key']} did not keep the committed passage timestep."
            )
    groups = {}
    for row in GATE.actual_events:
        token = row["scan_token"]
        if token not in groups:
            groups[token] = []
        groups[token].append(row)
    for rows in groups.values():
        ordered = sorted(rows, key=lambda item: item["scan_order"])
        stopped = False
        stop_visit = ""
        for row in ordered:
            if row["not_reached"] is True and stopped is not True:
                raise RuntimeError(
                    f"{row['visit_key']} is not_reached without an earlier clearance stop "
                    "in the same scan."
                )
            if stopped is True:
                if row["not_reached"] is not True:
                    raise RuntimeError(
                        f"{row['visit_key']} follows a clearance stop but is not not_reached."
                    )
                if _individual_hook_called(row) is True:
                    raise RuntimeError(
                        f"{row['visit_key']} received an individual hook after a clearance stop."
                    )
                if row["prior_clearance_stop_visit_key"] != stop_visit:
                    raise RuntimeError(
                        f"{row['visit_key']} does not name the clearance stop that blocked it."
                    )
            if row["scan_stopped_here"] is True:
                if row["stop_reason"] != "clearance_not_satisfied":
                    raise RuntimeError("A scan-stopping row is not a clearance stop.")
                if row["production_judgment"] != "clearance_not_satisfied":
                    raise RuntimeError("A scan-stopping row has a different production judgment.")
                stopped = True
                stop_visit = row["visit_key"]
            if row["temporary_skip_reason"] in FORMAL_ORDINARY_SHORTAGE_REASONS:
                if row["stop_reason"] != "" or row["scan_stopped_here"] is True:
                    raise RuntimeError(
                        f"{row['visit_key']} ordinary shortage is treated as a clearance stop."
                    )
                if row["production_judgment"] != row["temporary_skip_reason"]:
                    raise RuntimeError(
                        f"{row['visit_key']} ordinary shortage reason does not match "
                        "the formal production return."
                    )


def _validate_runtime(
    world,
    bundle,
    rank_rows,
    candidate_events,
    later_rows,
    completion,
    extended_counts,
) -> None:
    _assert_diagnostic_time_relationships()
    if world.T != DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"World.T is {world.T}, expected {DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM}."
        )
    if world.T != 1000:
        raise RuntimeError(f"World.T is {world.T}, expected 1000.")
    if bundle.scenario[0].scenario_name != DIAGNOSTIC_SCENARIO_NAME:
        raise RuntimeError("Research scenario name is not the diagnostic eval_1000 scenario.")
    if completion["completed_trip_count"] != 600:
        raise RuntimeError(f"completed_trip_count is {completion['completed_trip_count']}, not 600.")
    if completion["incomplete_vehicle_count"] != 0:
        raise RuntimeError(
            "Diagnostic evaluation extension still has incomplete vehicles: "
            f"{completion['incomplete_vehicle_names']!r}."
        )
    if completion["incomplete_vehicle_names"] != []:
        raise RuntimeError(
            f"incomplete_vehicle_names is not empty: {completion['incomplete_vehicle_names']!r}."
        )
    if type(extended_counts["transaction_count"]) is not int:
        raise RuntimeError("extended transaction_count is not an int.")
    participating = 0
    nonparticipating = 0
    for vehicle in world.VEHICLES.values():
        if vehicle.participates_in_order_exchange is True:
            participating = participating + 1
        elif vehicle.participates_in_order_exchange is False:
            nonparticipating = nonparticipating + 1
    if participating != trial.EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError(f"Participating count is {participating}.")
    if nonparticipating != trial.EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError(f"Nonparticipating count is {nonparticipating}.")
    if GATE.selected is None:
        raise RuntimeError("T=382 selected candidate was not captured.")
    trade_result = GATE.selected["trade_result"]
    scope = {_plain_visit_key(item) for item in trade_result.trade_scope}
    for visit_key in (TARGET_NONPARTICIPATING,) + TARGET_SELLERS:
        if visit_key not in scope:
            raise RuntimeError(f"{_visit_text(visit_key)} is outside the selected trade scope.")
    buyer_rank = trade_result.assigned_rank(TARGET_BUYER)
    for seller in TARGET_SELLERS:
        if buyer_rank >= trade_result.assigned_rank(seller):
            raise RuntimeError("Buyer candidate local rank is not before every seller.")
    ranks_after = GATE.selected["ranks_after_decision"]
    buyer_node = ranks_after.get(TARGET_BUYER)
    for seller in TARGET_SELLERS:
        seller_node = ranks_after.get(seller)
        if buyer_node is None or seller_node is None or buyer_node >= seller_node:
            raise RuntimeError("Buyer node-continuous rank is not before every seller.")
    target = _row_for(rank_rows, TARGET_NONPARTICIPATING)
    if target is None:
        raise RuntimeError("Target nonparticipating row is missing.")
    if target["baseline_passage_timestep"] != EXPECTED_NP_BASELINE_PASSAGE:
        raise RuntimeError("Target baseline passage is not 404.")
    if target["candidate_passage_timestep"] != EXPECTED_NP_CANDIDATE_PASSAGE:
        raise RuntimeError("Target candidate passage is not 403.")
    if target["actual_passage_timestep"] != EXPECTED_NP_ACTUAL_PASSAGE:
        raise RuntimeError("Target actual passage is not 404.")
    if target["candidate_node_continuous_rank"] != EXPECTED_NP_CANDIDATE_NODE_RANK:
        raise RuntimeError("Target candidate node rank is not 176.")
    if target["actual_node_continuous_rank"] != EXPECTED_NP_ACTUAL_NODE_RANK:
        raise RuntimeError("Target actual node rank is not 178.")
    if target["candidate_local_rank"] != target["baseline_local_rank"]:
        raise RuntimeError("Target nonparticipating local rank differs from baseline local rank.")
    _validate_target_actual_arrivals(rank_rows, later_rows)
    if len(bundle.transactions) != extended_counts["transaction_count"]:
        raise RuntimeError("bundle transaction count differs from extended_counts.")
    candidate_403 = _event_at(candidate_events, TARGET_NONPARTICIPATING, 403, "virtual_timestep")
    if candidate_403 is None:
        raise RuntimeError(
            f"Target nonparticipating {_visit_text(TARGET_NONPARTICIPATING)} "
            "has no candidate event at virtual T=403."
        )
    if candidate_403["passed"] is not True:
        raise RuntimeError("Target nonparticipating candidate event at virtual T=403 did not pass.")
    if candidate_403["attempted"] is not True:
        raise RuntimeError("Target nonparticipating candidate event at virtual T=403 was not attempted.")
    if candidate_403["passage_timestep_if_passed"] != 403:
        raise RuntimeError("Target nonparticipating candidate passage_timestep_if_passed is not 403.")
    _validate_actual_hook_call_counts()
    _validate_actual_scans(world)
    actual_403 = _require_one_actual_event(TARGET_NONPARTICIPATING, 403)
    if actual_403["passed"] is not False:
        raise RuntimeError("Target nonparticipating actual event at real T=403 passed unexpectedly.")
    _require_nonpassage_stage(actual_403)
    actual_404 = _require_one_actual_event(TARGET_NONPARTICIPATING, 404)
    if actual_404["attempted"] is not True:
        raise RuntimeError("Target nonparticipating actual event at real T=404 was not attempted.")
    if actual_404["passed"] is not True:
        raise RuntimeError("Target nonparticipating actual event at real T=404 did not pass.")
    if actual_404["production_judgment"] != "passed":
        raise RuntimeError("Target nonparticipating actual T=404 is not a formal pass.")
    if actual_404["called_transfer"] is not True:
        raise RuntimeError("Target nonparticipating actual T=404 did not record the transfer hook.")
    if actual_404["called_head"] is not True or actual_404["head_result"] is not False:
        raise RuntimeError("Target nonparticipating actual T=404 is missing the formal head pass.")
    if actual_404["called_clearance"] is not True or actual_404["clearance_result"] is not False:
        raise RuntimeError("Target nonparticipating actual T=404 is missing the formal clearance pass.")
    if actual_404["called_shortage"] is not True or actual_404["shortage_result"] is not None:
        raise RuntimeError("Target nonparticipating actual T=404 is missing the formal shortage pass.")
    if actual_404["actual_passage_rank_if_passed"] != 178:
        raise RuntimeError("Target nonparticipating actual_passage_rank_if_passed at T=404 is not 178.")
    for row in candidate_events:
        virtual_timestep = row["virtual_timestep"]
        if (
            virtual_timestep < CANDIDATE_TRACE_MUST_INCLUDE_START
            or virtual_timestep > CANDIDATE_TRACE_MUST_INCLUDE_END
        ):
            raise RuntimeError(
                f"Candidate event virtual_timestep {virtual_timestep} "
                "is outside the intended candidate trace range."
            )
    for row in GATE.actual_events:
        real_timestep = row["real_timestep"]
        if real_timestep < ACTUAL_TRACE_START or real_timestep > ACTUAL_TRACE_END:
            raise RuntimeError(
                f"Actual event real_timestep {real_timestep} is outside ACTUAL_TRACE_START..END."
            )
    later_by_key = {}
    for row in later_rows:
        later_by_key[(row["vehicle_name"], row["visit_id"])] = row
    for known in KNOWN_LATER_VISITS:
        found = later_by_key.get(known["visit_key"])
        if found is None:
            raise RuntimeError(f"Known later visit {_visit_text(known['visit_key'])} was not extracted.")
        if found["rank_confirmation_decision_timestep"] != known["decision_timestep"]:
            raise RuntimeError(f"{_visit_text(known['visit_key'])} confirmation timestep differs.")
        if found["actual_passage_timestep"] != known["actual_passage_timestep"]:
            raise RuntimeError(f"{_visit_text(known['visit_key'])} actual passage differs.")
        if found["actual_node_passage_rank"] != known["actual_node_passage_rank"]:
            raise RuntimeError(f"{_visit_text(known['visit_key'])} actual rank differs.")


def _reset_gate() -> None:
    GATE.selected = None
    GATE.rank_confirmation = {}
    GATE.actual_arrivals = {}
    GATE.scan_before = {}
    GATE.candidate_scan_timesteps = []
    GATE.actual_events = []
    GATE.actual_scan = None
    GATE.actual_scan_serial = 0
    GATE.summary_lines = []
    for hook_name in ACTUAL_SEQUENTIAL_HOOK_NAMES:
        GATE.wrapper_call_counts[hook_name] = 0
        GATE.original_call_counts[hook_name] = 0


def main() -> int:
    _reset_gate()
    original_limit = sys.getrecursionlimit()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
            raise RuntimeError("Diagnostic output directory is the trial output directory.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = trial.build_world()
        vot_values = trial._true_vot_sequence()
        vot_records = trial.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
        trial.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
        trial.verify_world_participation(world, vot_records)
        _assert_diagnostic_time_relationships()
        _apply_diagnostic_world_horizon(world)
        world.finalize_scenario()
        _validate_world_horizon_after_finalize(world)
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        bundle = build_tvt_mp_research_output(world, DIAGNOSTIC_SCENARIO_NAME)
        rank_rows = _build_rank_rows(world, bundle)
        candidate_events = _build_candidate_events()
        history = _history_by_visit(world)
        later_rows = _build_later_rows(history)
        completion = trial.reference.collect_trip_completion(world)
        extended_counts = _build_extended_evaluation_counts(bundle)
        _validate_runtime(
            world,
            bundle,
            rank_rows,
            candidate_events,
            later_rows,
            completion,
            extended_counts,
        )
        summary = _build_summary(
            rank_rows,
            candidate_events,
            later_rows,
            world,
            completion,
            extended_counts,
        )
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        rank_columns = [
            "scenario_name",
            "target_decision_timestep",
            "target_node_name",
            "selected_candidate_identity",
            "selected_candidate_evaluation_index",
            "vehicle_name",
            "visit_id",
            "visit_key",
            "participates_in_order_exchange",
            "role",
            "is_right_of_entry_holder",
            "in_candidate_visits",
            "in_trade_scope",
            "in_decision_window",
            "in_confirmed_leading_nonparticipating",
            "in_remaining_decision_window",
            "in_outside_trade_scope_inside_k_fixed",
            "in_binding_sequence",
            "binding_partition",
            "baseline_local_rank",
            "candidate_local_rank",
            "candidate_node_continuous_rank",
            "actual_node_continuous_rank",
            "rank_confirmation_decision_timestep",
            "rank_confirmation_source",
            "baseline_arrival_timestep",
            "baseline_arrival_tiebreaker",
            "actual_arrival_timestep",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
            "actual_passage_timestep",
            "formal_route_next_link_name",
            "predicted_route_next_link_name",
            "actual_route_next_link_name",
            "candidate_minus_actual_passage_timesteps",
        ]
        candidate_columns = [
            "candidate_identity",
            "candidate_evaluation_index",
            "virtual_timestep",
            "scan_order",
            "vehicle_name",
            "visit_id",
            "visit_key",
            "binding_rank",
            "binding_partition",
            "attempted",
            "passed",
            "temporarily_skipped",
            "skip_reason",
            "stopped",
            "stop_reason",
            "not_reached_because_prior_clearance_stop",
            "earlier_attempted_visit_keys",
            "earlier_passed_visit_keys",
            "baseline_arrival_timestep",
            "on_target_inlink_before_judgment",
            "in_target_node_incoming_before_judgment",
            "is_physical_head_before_judgment",
            "current_link_name_before_judgment",
            "formal_inlink_name",
            "route_next_link_name",
            "entry_open_before_judgment",
            "outlink_capacity_available_before_judgment",
            "inlink_capacity_available_before_judgment",
            "clearance_satisfied_before_judgment",
            "passage_timestep_if_passed",
        ]
        actual_columns = [
            "real_timestep",
            "node_name",
            "vehicle_name",
            "visit_id",
            "visit_key",
            "assigned_rank_before_attempt",
            "rank_confirmation_decision_timestep",
            "rank_confirmation_source",
            "attempted",
            "passed",
            "temporary_skip_reason",
            "stop_reason",
            "earlier_attempted_visit_keys",
            "earlier_passed_visit_keys",
            "arrived_before_attempt",
            "in_target_incoming_before_attempt",
            "is_physical_head_before_attempt",
            "current_link_name_before_attempt",
            "formal_inlink_name",
            "live_route_next_link_name_before_attempt",
            "entry_open_before_attempt",
            "outlink_capacity_available_before_attempt",
            "inlink_capacity_available_before_attempt",
            "clearance_satisfied_before_attempt",
            "actual_passage_rank_if_passed",
        ]
        later_columns = [
            "vehicle_name",
            "visit_id",
            "visit_key",
            "rank_confirmation_decision_timestep",
            "assigned_rank",
            "actual_arrival_timestep",
            "actual_passage_timestep",
            "actual_node_passage_rank",
            "relation_to_target_nonparticipating",
            "whether_passed_before_target",
            "whether_assigned_after_target_decision",
        ]
        _write_csv(OUTPUT_DIR / RANK_CSV, rank_columns, rank_rows)
        _write_csv(OUTPUT_DIR / CANDIDATE_EVENTS_CSV, candidate_columns, candidate_events)
        actual_rows = []
        for row in GATE.actual_events:
            copied = dict(row)
            copied.pop("visit_key_tuple", None)
            copied.pop("not_reached", None)
            copied.pop("production_judgment", None)
            copied.pop("prior_clearance_stop_visit_key", None)
            copied.pop("called_head", None)
            copied.pop("head_result", None)
            copied.pop("called_clearance", None)
            copied.pop("clearance_result", None)
            copied.pop("called_shortage", None)
            copied.pop("shortage_result", None)
            copied.pop("called_transfer", None)
            copied.pop("registry_passage_timestep", None)
            copied.pop("scan_token", None)
            copied.pop("scan_order", None)
            copied.pop("scan_stopped_here", None)
            actual_rows.append(copied)
        _write_csv(OUTPUT_DIR / ACTUAL_EVENTS_CSV, actual_columns, actual_rows)
        _write_csv(OUTPUT_DIR / LATER_DECISION_CSV, later_columns, later_rows)
        (OUTPUT_DIR / SUMMARY_NAME).write_text(summary, encoding="utf-8")
        generated = [
            RANK_CSV,
            CANDIDATE_EVENTS_CSV,
            ACTUAL_EVENTS_CSV,
            LATER_DECISION_CSV,
            SUMMARY_NAME,
            MANIFEST_NAME,
        ]
        manifest = {
            "scenario_name": DIAGNOSTIC_SCENARIO_NAME,
            "diagnostic_script": SCRIPT_PATH.name,
            "diagnostic_evaluation_end_timestep": DIAGNOSTIC_EVALUATION_END_TIMESTEP,
            "diagnostic_internal_tsize": DIAGNOSTIC_INTERNAL_TSIZE,
            "diagnostic_world_t_after_sim": DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM,
            "diagnostic_added_timesteps": DIAGNOSTIC_ADDED_TIMESTEPS,
            "completed_trip_count": completion["completed_trip_count"],
            "incomplete_vehicle_count": completion["incomplete_vehicle_count"],
            "incomplete_vehicle_names": completion["incomplete_vehicle_names"],
            "extended_evaluation_counts": extended_counts,
            "target_node_name": TARGET_NODE_NAME,
            "target_decision_timestep": TARGET_DECISION_TIMESTEP,
            "selected_candidate_identity": GATE.selected["identity"],
            "selected_candidate_evaluation_index": GATE.selected["evaluation_index"],
            "target_nonparticipating_visit": _visit_text(TARGET_NONPARTICIPATING),
            "output_directory": str(OUTPUT_DIR),
            "generated_files": generated,
        }
        (OUTPUT_DIR / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        trial.reference.restore_real_world_spillback_observation()
        restore_hooks()
        sys.setrecursionlimit(original_limit)


def _ast_label(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_label(node.value)
        if parent is None:
            return None
        return parent + "." + node.attr
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    return None


def _assignment_pairs(function_node):
    pairs = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = _ast_label(node.targets[0])
        value = _ast_label(node.value)
        if target is None or value is None:
            continue
        pairs.append((target, value))
    return pairs


def _require_assignment(pairs, target, value, label: str) -> None:
    for pair in pairs:
        if pair[0] == target and pair[1] == value:
            return
    raise RuntimeError(f"Static hook binding is missing: {label}.")


def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _restore_returns_when_not_installed(function_node) -> bool:
    if len(function_node.body) == 0:
        return False
    first = function_node.body[0]
    if not isinstance(first, ast.If):
        return False
    test = first.test
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Attribute) or test.left.attr != "installed":
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.IsNot):
        return False
    compared = test.comparators[0]
    if not isinstance(compared, ast.Constant) or compared.value is not True:
        return False
    for statement in first.body:
        if isinstance(statement, ast.Return):
            return True
    return False


def _validate_actual_hook_install_restore(tree) -> None:
    install_node = _function_node(tree, "install_hooks")
    restore_node = _function_node(tree, "restore_hooks")
    if install_node is None or restore_node is None:
        raise RuntimeError("install_hooks or restore_hooks is missing.")
    if _restore_returns_when_not_installed(restore_node) is not True:
        raise RuntimeError("restore_hooks does not return immediately when hooks are not installed.")
    install_pairs = _assignment_pairs(install_node)
    restore_pairs = _assignment_pairs(restore_node)
    bindings = (
        (
            "driver_module.run_tvt_mp_driver",
            "GATE.original_driver",
            "wrapped_driver",
        ),
        (
            "physical_module._try_confirmed_candidates",
            "GATE.original_try_confirmed",
            "wrapped_try_confirmed",
        ),
        (
            "physical_module._inlink_physical_head_should_skip",
            "GATE.original_head_skip",
            "wrapped_head_skip",
        ),
        (
            "uxsim_module.Node._order_control_clearance_blocks_passage",
            "GATE.original_clearance",
            "wrapped_clearance",
        ),
        (
            "physical_module._first_ordinary_physical_shortage",
            "GATE.original_shortage",
            "wrapped_shortage",
        ),
        (
            "uxsim_module.Node._transfer_one_vehicle_between_links",
            "GATE.original_actual_transfer",
            "wrapped_actual_transfer",
        ),
        (
            "uxsim_module.Vehicle.record_order_control_node_arrival",
            "GATE.original_arrival",
            "wrapped_arrival",
        ),
    )
    for target_name, original_name, wrapper_name in bindings:
        if _function_node(tree, wrapper_name) is None:
            raise RuntimeError(f"Wrapper function {wrapper_name} is missing.")
        _require_assignment(
            install_pairs,
            original_name,
            target_name,
            f"install saves {target_name}",
        )
        _require_assignment(
            install_pairs,
            target_name,
            wrapper_name,
            f"install patches {target_name}",
        )
        _require_assignment(
            restore_pairs,
            target_name,
            original_name,
            f"restore writes back {target_name}",
        )
        _require_assignment(
            restore_pairs,
            original_name,
            "None",
            f"restore clears {original_name}",
        )
    binding_attribute = "scan_and_transfer_tvt_mp_binding_visits_at_current_timestep"
    binding_targets = (
        "local_calc_module." + binding_attribute,
        "binding_module." + binding_attribute,
    )
    _require_assignment(
        install_pairs,
        "GATE.original_binding_scan",
        binding_targets[0],
        "install saves the shared binding scan",
    )
    for target_name in binding_targets:
        _require_assignment(
            install_pairs,
            target_name,
            "wrapped_binding_scan",
            f"install patches {target_name}",
        )
        _require_assignment(
            restore_pairs,
            target_name,
            "GATE.original_binding_scan",
            f"restore writes back {target_name}",
        )
    _require_assignment(
        restore_pairs,
        "GATE.original_binding_scan",
        "None",
        "restore clears GATE.original_binding_scan",
    )


def _function_calls_name(function_node, name: str) -> bool:
    if function_node is None:
        return False
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == name:
                return True
    return False


def _function_uses_buyers_zero_subscript(function_node) -> bool:
    if function_node is None:
        return False
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != "buyers":
            continue
        if isinstance(node.slice, ast.Constant) and node.slice.value == 0:
            return True
    return False


def _validate_one_based_evaluation_index_helper(helper_node) -> None:
    if helper_node is None:
        raise RuntimeError("_find_one_based_evaluation_index is missing.")
    has_eval_none_init = False
    has_index_increment = False
    has_identity_compare = False
    for node in ast.walk(helper_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "evaluation_index":
                    if isinstance(node.value, ast.Constant) and node.value.value is None:
                        has_eval_none_init = True
        if isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "index":
                if isinstance(node.op, ast.Add):
                    has_index_increment = True
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id == "index" and isinstance(node.value, ast.BinOp):
                    if isinstance(node.value.op, ast.Add):
                        has_index_increment = True
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Name) and comparator.id == "selected_economic":
                    has_identity_compare = True
    if has_eval_none_init is not True:
        raise RuntimeError("_find_one_based_evaluation_index does not initialize evaluation_index to None.")
    if has_index_increment is not True:
        raise RuntimeError("_find_one_based_evaluation_index does not increment index in the loop.")
    if has_identity_compare is not True:
        raise RuntimeError(
            "_find_one_based_evaluation_index does not compare candidate objects by identity."
        )


def _if_body_raises(function_node) -> bool:
    if not isinstance(function_node, ast.If):
        return False
    for statement in function_node.body:
        if isinstance(statement, ast.Raise):
            return True
    return False


def _validate_unique_trade_result_helper(helper_node) -> None:
    if helper_node is None:
        raise RuntimeError("_find_unique_trade_result_for_buyers is missing.")
    has_found_none_init = False
    rejects_duplicate = False
    rejects_missing = False
    checks_result_type = False
    returns_found = False
    for node in ast.walk(helper_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "found":
                    if isinstance(node.value, ast.Constant) and node.value.value is None:
                        has_found_none_init = True
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare):
                left_name = test.left.id if isinstance(test.left, ast.Name) else None
                if left_name == "found":
                    for op, comparator in zip(test.ops, test.comparators):
                        if not isinstance(comparator, ast.Constant):
                            continue
                        if isinstance(op, ast.IsNot) and comparator.value is None:
                            if _if_body_raises(node) is True:
                                rejects_duplicate = True
                        if isinstance(op, ast.Is) and comparator.value is None:
                            if _if_body_raises(node) is True:
                                rejects_missing = True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "isinstance":
                checks_result_type = True
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Name) and node.value.id == "found":
                returns_found = True
    if has_found_none_init is not True:
        raise RuntimeError("_find_unique_trade_result_for_buyers does not initialize found to None.")
    if rejects_duplicate is not True:
        raise RuntimeError(
            "_find_unique_trade_result_for_buyers does not stop on a second buyers match."
        )
    if rejects_missing is not True:
        raise RuntimeError(
            "_find_unique_trade_result_for_buyers does not stop when no buyers match exists."
        )
    if checks_result_type is not True:
        raise RuntimeError(
            "_find_unique_trade_result_for_buyers does not validate the matched result type."
        )
    if returns_found is not True:
        raise RuntimeError("_find_unique_trade_result_for_buyers does not return the unique match.")


def _validate_capture_selected_static(tree) -> None:
    capture = _function_node(tree, "_capture_selected")
    if capture is None:
        raise RuntimeError("_capture_selected is missing.")
    if _function_calls_name(capture, "_find_one_based_evaluation_index") is not True:
        raise RuntimeError("_capture_selected does not call _find_one_based_evaluation_index.")
    if _function_calls_name(capture, "_find_unique_trade_result_for_buyers") is not True:
        raise RuntimeError("_capture_selected does not call _find_unique_trade_result_for_buyers.")
    if _function_calls_name(capture, "_buyers_visit_identity_suffix") is not True:
        raise RuntimeError("_capture_selected does not build identity from all buyers.")
    if _function_uses_buyers_zero_subscript(capture) is True:
        raise RuntimeError("_capture_selected still uses buyers[0] for candidate identity.")
    _validate_one_based_evaluation_index_helper(
        _function_node(tree, "_find_one_based_evaluation_index")
    )
    _validate_unique_trade_result_helper(
        _function_node(tree, "_find_unique_trade_result_for_buyers")
    )


def _validate_build_rank_rows_static(tree) -> None:
    rank_rows = _function_node(tree, "_build_rank_rows")
    if rank_rows is None:
        raise RuntimeError("_build_rank_rows is missing.")
    uses_visit_key_baseline_membership = False
    for node in ast.walk(rank_rows):
        if isinstance(node, ast.Attribute) and node.attr == "vehicle_name":
            if isinstance(node.value, ast.Name) and node.value.id in (
                "item",
                "candidate_visit",
            ):
                raise RuntimeError(
                    "_build_rank_rows references vehicle_name on a candidate visit object."
                )
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or not isinstance(node.ops[0], ast.In):
                continue
            if not isinstance(node.left, ast.Name) or node.left.id != "visit_key":
                continue
            for comparator in node.comparators:
                if isinstance(comparator, ast.Name) and comparator.id == "baseline_rank":
                    uses_visit_key_baseline_membership = True
    if uses_visit_key_baseline_membership is not True:
        raise RuntimeError(
            "_build_rank_rows does not gate baseline snapshots with visit_key in baseline_rank."
        )


def _validate_candidate_trace_static(tree) -> None:
    binding_context = _function_node(tree, "_binding_context")
    snapshot = _function_node(tree, "_snapshot_binding_visit")
    if binding_context is None or snapshot is None:
        raise RuntimeError("Candidate trace functions are missing.")
    referenced_names = []
    for node in ast.walk(binding_context):
        if isinstance(node, ast.Name):
            referenced_names.append(node.id)
    for constant_name in (
        "CANDIDATE_TRACE_MUST_INCLUDE_START",
        "CANDIDATE_TRACE_MUST_INCLUDE_END",
    ):
        if constant_name not in referenced_names:
            raise RuntimeError(f"_binding_context does not reference {constant_name}.")
    forbidden_snapshot_calls = (
        "_order_control_clearance_blocks_passage",
        "_first_ordinary_physical_shortage",
        "_inlink_physical_head_should_skip",
        "_ordinary_physical_limits_should_skip",
        "_try_confirmed_candidates",
        "_transfer_one_vehicle_between_links",
    )
    for node in ast.walk(snapshot):
        if not isinstance(node, ast.Call):
            continue
        called_name = None
        if isinstance(node.func, ast.Attribute):
            called_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            called_name = node.func.id
        if called_name in forbidden_snapshot_calls:
            raise RuntimeError(
                f"_snapshot_binding_visit calls production judgment {called_name}."
            )


def _wrapped_arrival_calls_original_once(function_node) -> bool:
    call_count = 0
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "original_arrival":
            if isinstance(func.value, ast.Name) and func.value.id == "GATE":
                call_count = call_count + 1
    return call_count == 1


def _is_gate_actual_arrivals_attribute(node) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "actual_arrivals"
        and isinstance(node.value, ast.Name)
        and node.value.id == "GATE"
    )


def _is_gate_actual_arrivals_key_subscript(node) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if _is_gate_actual_arrivals_attribute(node.value) is not True:
        return False
    slice_node = node.slice
    return isinstance(slice_node, ast.Name) and slice_node.id == "key"


def _function_reads_arrival_time(function_node) -> bool:
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "get":
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "current_visit":
                continue
            if len(node.args) < 1:
                continue
            arg0 = node.args[0]
            if isinstance(arg0, ast.Constant) and arg0.value == "arrival_time":
                return True
        if isinstance(node, ast.Subscript):
            if not isinstance(node.value, ast.Name) or node.value.id != "current_visit":
                continue
            if isinstance(node.slice, ast.Constant) and node.slice.value == "arrival_time":
                return True
    return False


def _line_original_arrival_call(function_node) -> int | None:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "original_arrival":
            if isinstance(func.value, ast.Name) and func.value.id == "GATE":
                return node.lineno
    return None


def _line_current_visit_getattr_assign(function_node) -> int | None:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != "current_visit":
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name):
            continue
        if value.func.id != "getattr" or len(value.args) < 2:
            continue
        attribute_arg = value.args[1]
        if isinstance(attribute_arg, ast.Constant) and attribute_arg.value == "order_control_current_visit":
            return node.lineno
    return None


def _line_arrival_time_assign(function_node) -> int | None:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != "arrival_time":
            continue
        value = node.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            if value.func.attr == "get" and isinstance(value.func.value, ast.Name):
                if value.func.value.id != "current_visit":
                    continue
                if len(value.args) < 1:
                    continue
                if isinstance(value.args[0], ast.Constant) and value.args[0].value == "arrival_time":
                    return node.lineno
        if isinstance(value, ast.Subscript):
            if isinstance(value.value, ast.Name) and value.value.id == "current_visit":
                if isinstance(value.slice, ast.Constant) and value.slice.value == "arrival_time":
                    return node.lineno
    return None


def _validate_wrapped_arrival_read_order(function_node) -> None:
    original_line = _line_original_arrival_call(function_node)
    current_visit_line = _line_current_visit_getattr_assign(function_node)
    arrival_line = _line_arrival_time_assign(function_node)
    if original_line is None or current_visit_line is None or arrival_line is None:
        raise RuntimeError("wrapped_arrival read-order AST nodes are missing.")
    if original_line >= current_visit_line or current_visit_line > arrival_line:
        raise RuntimeError(
            "wrapped_arrival must read arrival_time after GATE.original_arrival and current_visit."
        )


def _function_stores_actual_arrivals_only_when_new(function_node) -> bool:
    has_not_in = False
    gate_assign_count = 0
    has_stored_read = False
    has_reconcile_compare = False
    for node in ast.walk(function_node):
        if isinstance(node, ast.Compare):
            left = node.left
            if isinstance(left, ast.Name) and left.id == "key":
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, ast.NotIn) and _is_gate_actual_arrivals_attribute(comparator):
                        has_not_in = True
            if isinstance(left, ast.Name) and left.id == "stored_timestep":
                for op in node.ops:
                    if isinstance(op, ast.NotEq):
                        for comparator in node.comparators:
                            if isinstance(comparator, ast.Name) and comparator.id == "from_production":
                                has_reconcile_compare = True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if _is_gate_actual_arrivals_key_subscript(target):
                    gate_assign_count = gate_assign_count + 1
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id == "stored_timestep":
                    value = node.value
                    if _is_gate_actual_arrivals_key_subscript(value):
                        has_stored_read = True
    if has_not_in is not True:
        return False
    if gate_assign_count != 1:
        return False
    if has_stored_read is not True:
        return False
    if has_reconcile_compare is not True:
        return False
    return True


def _validate_wrapped_arrival_static(tree) -> None:
    function_node = _function_node(tree, "wrapped_arrival")
    if function_node is None:
        raise RuntimeError("wrapped_arrival is missing.")
    if _wrapped_arrival_calls_original_once(function_node) is not True:
        raise RuntimeError("wrapped_arrival must call GATE.original_arrival exactly once.")
    if _function_reads_arrival_time(function_node) is not True:
        raise RuntimeError("wrapped_arrival must read current_visit arrival_time.")
    _validate_wrapped_arrival_read_order(function_node)
    if _function_stores_actual_arrivals_only_when_new(function_node) is not True:
        raise RuntimeError("wrapped_arrival must store GATE.actual_arrivals only when key is new.")


def _validate_main_diagnostic_horizon(main_node) -> None:
    apply_line = None
    finalize_line = None
    for node in ast.walk(main_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "_apply_diagnostic_world_horizon":
            apply_line = node.lineno
        if isinstance(func, ast.Attribute) and func.attr == "finalize_scenario":
            finalize_line = node.lineno
    if apply_line is None or finalize_line is None or apply_line >= finalize_line:
        raise RuntimeError("main must call _apply_diagnostic_world_horizon before finalize_scenario.")


def _validate_runtime_trip_completion(function_node) -> None:
    if function_node is None:
        raise RuntimeError("_validate_runtime is missing.")
    source = ast.get_source_segment(
        SCRIPT_PATH.read_text(encoding="utf-8"),
        function_node,
    )
    if source is None:
        raise RuntimeError("_validate_runtime source is missing.")
    if "incomplete_vehicle_count" not in source or "!= 0" not in source:
        raise RuntimeError("_validate_runtime must require incomplete_vehicle_count == 0.")


def _validate_no_eval_900_aggregate_checks(function_node) -> None:
    if function_node is None:
        raise RuntimeError("_validate_runtime is missing.")
    forbidden = (
        "EXPECTED_TRANSACTIONS",
        "EXPECTED_BUYER_VISITS",
        "EXPECTED_SELLER_VISITS",
        "EXPECTED_NONPARTICIPATING_VISITS",
        "EXPECTED_BOTH_OBSERVED",
        "EXPECTED_EQUAL_PASSAGES",
        "EXPECTED_UNEQUAL_PASSAGES",
        "EXPECTED_UNOBSERVED",
    )
    for name in forbidden:
        for node in ast.walk(function_node):
            if isinstance(node, ast.Name) and node.id == name:
                raise RuntimeError(f"_validate_runtime must not compare bundle to {name}.")


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    _assert_diagnostic_time_relationships()
    if DIAGNOSTIC_EVALUATION_END_TIMESTEP != 999:
        raise RuntimeError("DIAGNOSTIC_EVALUATION_END_TIMESTEP must be 999.")
    if DIAGNOSTIC_INTERNAL_TSIZE != 1030:
        raise RuntimeError("DIAGNOSTIC_INTERNAL_TSIZE must be 1030.")
    if DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM != 1000:
        raise RuntimeError("DIAGNOSTIC_EXPECTED_WORLD_T_AFTER_SIM must be 1000.")
    if DIAGNOSTIC_ADDED_TIMESTEPS != 100:
        raise RuntimeError("DIAGNOSTIC_ADDED_TIMESTEPS must be 100.")
    output_text = str(OUTPUT_DIR)
    if "eval_1000_timestep" not in output_text:
        raise RuntimeError("OUTPUT_DIR must include eval_1000_timestep.")
    if "eval_900_timestep" in output_text:
        raise RuntimeError("OUTPUT_DIR must not include eval_900_timestep.")
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory equals the trial output directory.")
    forbidden_t600_module_strings = (
        "veh_ne_wn_base_032",
        "veh_ne_wn_base_034",
        "veh_wn_en_base_042",
        "northeast_intersection_to_southeast_intersection",
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_t600_candidate_actual_paired_trace",
    )
    for body_node in tree.body:
        if isinstance(body_node, ast.Assign):
            value_root = body_node.value
        elif isinstance(body_node, ast.AnnAssign) and body_node.value is not None:
            value_root = body_node.value
        else:
            continue
        for subnode in ast.walk(value_root):
            if not isinstance(subnode, ast.Constant) or not isinstance(subnode.value, str):
                continue
            for forbidden in forbidden_t600_module_strings:
                if forbidden in subnode.value:
                    raise RuntimeError(
                        "This diagnostic still embeds a T=600 all-participating module constant: "
                        f"{forbidden!r}."
                    )
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
    for name in ("system", "rmtree", "unlink", "rmdir"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
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
    static_function = None
    main_function = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "validate_static_contract":
            static_function = node
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_function = node
    if static_function is None or main_function is None:
        raise RuntimeError("main or validate_static_contract is missing.")
    for node in ast.walk(static_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "exec_simulation":
                raise RuntimeError("Static validation calls exec_simulation.")
            if node.func.attr in ("install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation installs or restores hooks.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("install_hooks", "restore_hooks", "exec_simulation"):
                raise RuntimeError("Static validation installs hooks or runs the simulation.")
    _validate_actual_hook_install_restore(tree)
    _validate_candidate_trace_static(tree)
    _validate_capture_selected_static(tree)
    _validate_build_rank_rows_static(tree)
    _validate_wrapped_arrival_static(tree)
    _validate_main_diagnostic_horizon(main_function)
    _validate_runtime_trip_completion(_function_node(tree, "_validate_runtime"))
    _validate_no_eval_900_aggregate_checks(_function_node(tree, "_validate_runtime"))
    main_source = ast.get_source_segment(source, main_function)
    if main_source is None or "collect_trip_completion" not in main_source:
        raise RuntimeError("main must call collect_trip_completion.")
    if _function_node(tree, "_build_extended_evaluation_counts") is None:
        raise RuntimeError("_build_extended_evaluation_counts is missing.")
    if _function_node(tree, "_validate_target_actual_arrivals") is None:
        raise RuntimeError("_validate_target_actual_arrivals is missing.")
    for forbidden_vehicle_iter in ast.walk(tree):
        if not isinstance(forbidden_vehicle_iter, ast.For):
            continue
        iter_node = forbidden_vehicle_iter.iter
        if isinstance(iter_node, ast.Attribute):
            if (
                iter_node.attr == "VEHICLES"
                and isinstance(iter_node.value, ast.Name)
                and iter_node.value.id == "world"
            ):
                raise RuntimeError("Diagnostic must not iterate world.VEHICLES directly.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
    if "install_hooks" not in source or "restore_hooks" not in source:
        raise RuntimeError("Hook install and restore are not both present.")
    print("static contract ok")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("Unexpected CLI arguments.")
    if len(sys.argv) == 2:
        if sys.argv[1] != "--static-validate-only":
            raise SystemExit(f"Unknown CLI option: {sys.argv[1]!r}")
        validate_static_contract()
        raise SystemExit(0)
    raise SystemExit(main())
