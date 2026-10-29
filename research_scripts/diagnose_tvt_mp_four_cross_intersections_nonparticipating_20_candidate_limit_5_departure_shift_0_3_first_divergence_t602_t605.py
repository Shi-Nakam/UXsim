"""
Read-only comparison of the first established-trade divergence between departure shift 0 and shift 3.

Shift 0 is the completed base N=5 trial, captured at real decision T=602 (aligned T=602).
Shift 3 is the aligned departure-shift trial, captured at real decision T=605 (aligned T=602).
Target node is northeast_intersection. Target buyer visit is veh_wn_en_base_041:2.

This diagnostic does not call trial main, does not write research output, and does not
modify production, trials, or existing outputs.
"""

from __future__ import annotations

import ast
import csv
import math
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_shift_trial as shift_trial
import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial as shift0_trial
import uxsim.order_control_tvt_mp_driver as driver_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateTrafficObservationRecord,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtNodeMpCandidateSelectionResult,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpSellerEconomicRecord,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
)

SHIFT0_DEPARTURE_SHIFT = 0
SHIFT0_CAPTURE_TIMESTEP = 602
SHIFT3_DEPARTURE_SHIFT = 3
SHIFT3_CAPTURE_TIMESTEP = 605
ALIGNED_TIMESTEP = 602
TARGET_NODE_NAME = "northeast_intersection"
TARGET_BUYER_VISIT_KEY = ("veh_wn_en_base_041", 2)
FLOAT_REL_TOL = 1e-12
FLOAT_ABS_TOL = 1e-12

OUTPUT_DIR = (
    shift0_trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_"
        "departure_shift_0_3_first_divergence_t602_t605"
    )
)
NODE_SUMMARY_CSV = "shift_0_3_t602_t605_node_summary.csv"
CANDIDATE_VISITS_CSV = "shift_0_3_t602_t605_candidate_visits.csv"
CONSIDERED_CANDIDATES_CSV = "shift_0_3_t602_t605_considered_candidates.csv"
REVIEW_TXT = "shift_0_3_t602_t605_first_divergence_review.txt"
OUTPUT_FILE_NAMES = (
    NODE_SUMMARY_CSV,
    CANDIDATE_VISITS_CSV,
    CONSIDERED_CANDIDATES_CSV,
    REVIEW_TXT,
)

NODE_SUMMARY_COLUMNS = (
    "shift",
    "actual_capture_timestep",
    "aligned_timestep",
    "node_name",
    "selection_status",
    "selected_candidate_present",
    "selected_evaluation_index",
    "selected_buyers_sorted",
    "selected_trade_scope",
    "selected_total_G",
    "selected_total_R",
    "selected_surplus",
    "p_minus_one_eligible_visit_count_before_limit",
    "candidate_visit_count",
    "candidate_visit_keys",
    "reconstructed_sort_order",
    "formal_candidate_order_matches_sort_key",
    "right_of_entry_visit_key",
    "right_of_entry_selection_status",
    "right_of_entry_baseline_passage_timestep",
    "considered_candidate_count",
    "target_buyer_candidate_count",
)

CANDIDATE_VISIT_COLUMNS = (
    "shift",
    "actual_capture_timestep",
    "aligned_timestep",
    "node_name",
    "candidate_order",
    "baseline_local_rank",
    "visit_key",
    "formal_inlink_name",
    "baseline_arrival_timestep",
    "aligned_baseline_arrival_timestep",
    "baseline_passage_timestep",
    "aligned_baseline_passage_timestep",
    "pre_driver_rank_status",
    "post_driver_c_rank",
    "vehicle_id",
    "arrival_tiebreaker",
    "aligned_sort_arrival_timestep",
    "baseline_alignment_sort_key_text",
)

ORDER_FOCUS_VISIT_KEYS = (
    ("veh_wn_en_base_041", 2),
    ("veh_ne_ws_base_031", 1),
)

CONSIDERED_COLUMNS = (
    "shift",
    "actual_capture_timestep",
    "aligned_timestep",
    "node_name",
    "evaluation_index",
    "selected",
    "contains_target_buyer",
    "buyers_sorted",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "trade_scope_visit_keys",
    "candidate_ranks",
    "total_G",
    "total_R",
    "surplus",
    "economically_feasible",
    "infeasibility_reasons",
    "selection_reason",
    "k_last_buyer",
    "k_decision_window",
    "k_fixed",
    "target_buyer_baseline_arrival_timestep",
    "target_buyer_aligned_baseline_arrival_timestep",
    "target_buyer_baseline_passage_timestep",
    "target_buyer_aligned_baseline_passage_timestep",
    "target_buyer_candidate_arrival_timestep",
    "target_buyer_candidate_passage_timestep",
    "target_buyer_aligned_candidate_passage_timestep",
    "target_buyer_predicted_saving_timesteps",
    "target_buyer_declared_vot_per_second",
    "target_buyer_G_b",
    "seller_visit_keys",
    "seller_baseline_passage_timesteps",
    "seller_candidate_passage_timesteps",
    "seller_aligned_baseline_passage_timesteps",
    "seller_aligned_candidate_passage_timesteps",
    "seller_predicted_delay_timesteps",
    "seller_declared_vot_per_second",
    "seller_R_s",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.capture_timestep = None
        self.shift = None
        self.captured = False
        self.pre_driver_rank_membership = None
        self.snapshot = None


GATE = _Gate()


def _reset_gate() -> None:
    GATE.installed = False
    GATE.real_world = None
    GATE.original_driver = None
    GATE.capture_timestep = None
    GATE.shift = None
    GATE.captured = False
    GATE.pre_driver_rank_membership = None
    GATE.snapshot = None


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(columns),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _close(left, right) -> bool:
    return math.isclose(float(left), float(right), rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


def _one_node(results, node_name: str, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"{node_name}: {label} count is {count}.")
    return matched


def _role_name(role) -> str:
    if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return "buyer"
    if role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return "seller"
    if role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return "nonparticipating"
    raise RuntimeError(f"Unsupported trade role {role!r}.")


def _serialize_reasons(reasons) -> str:
    parts = []
    for reason in reasons:
        parts.append(reason.value if hasattr(reason, "value") else str(reason))
    return "|".join(parts)


def _join_keys(keys) -> str:
    return "|".join(_visit_text(key) for key in keys)


def _snapshot_pre_driver_rank_membership(world) -> dict:
    rank_states = world.order_control_tvt_rank_states_by_node_name
    rank_state = rank_states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(f"{TARGET_NODE_NAME} rank state is missing before the driver.")
    confirmed = frozenset(
        _plain_visit_key(visit_key) for visit_key in rank_state.confirmed_visit_keys_in_order()
    )
    undetermined = frozenset(
        _plain_visit_key(visit_key) for visit_key in rank_state.undetermined_visit_keys()
    )
    overlap = confirmed & undetermined
    if len(overlap) != 0:
        raise RuntimeError("Pre-driver confirmed and undetermined visit keys overlap.")
    return {"confirmed_visit_keys": confirmed, "undetermined_visit_keys": undetermined}


def _baseline_alignment_sort_key(
    aligned_sort_arrival_timestep: int,
    arrival_tiebreaker: int | float,
    vehicle_id: int,
) -> tuple:
    return (aligned_sort_arrival_timestep, arrival_tiebreaker, vehicle_id)


def _snapshot_alignment_fields(snapshot, visit_key, candidate_arrival) -> tuple:
    if snapshot is None:
        raise RuntimeError(
            f"{_visit_text(visit_key)} collector snapshot is missing; "
            "vehicle_id and arrival_tiebreaker are not inferred."
        )
    vehicle_id = snapshot.get("vehicle_id")
    arrival_tiebreaker = snapshot.get("arrival_tiebreaker")
    baseline_arrival_timestep = snapshot.get("baseline_arrival_timestep")
    if type(vehicle_id) is not int or type(vehicle_id) is bool or vehicle_id < 0:
        raise RuntimeError(
            f"{_visit_text(visit_key)} vehicle_id must be a non-negative int; got {vehicle_id!r}."
        )
    if arrival_tiebreaker is None or type(arrival_tiebreaker) is bool:
        raise RuntimeError(
            f"{_visit_text(visit_key)} arrival_tiebreaker is {arrival_tiebreaker!r}."
        )
    if type(arrival_tiebreaker) not in (int, float) or math.isfinite(float(arrival_tiebreaker)) is not True:
        raise RuntimeError(
            f"{_visit_text(visit_key)} arrival_tiebreaker is not a finite int or float; "
            f"got {arrival_tiebreaker!r}."
        )
    if (
        type(baseline_arrival_timestep) is not int
        or type(baseline_arrival_timestep) is bool
        or baseline_arrival_timestep < 0
    ):
        raise RuntimeError(
            f"{_visit_text(visit_key)} baseline_arrival_timestep must be a non-negative int; "
            f"got {baseline_arrival_timestep!r}."
        )
    if baseline_arrival_timestep != candidate_arrival:
        raise RuntimeError(
            f"{_visit_text(visit_key)} collector arrival {baseline_arrival_timestep!r} "
            f"differs from candidate visit arrival {candidate_arrival!r}."
        )
    return vehicle_id, arrival_tiebreaker, baseline_arrival_timestep


def _assert_candidate_order_matches_alignment_sort(candidate_rows: list[dict]) -> str:
    sort_keys = [row["alignment_sort_key"] for row in candidate_rows]
    if len(sort_keys) != len(set(sort_keys)):
        raise RuntimeError("Candidate Visit alignment sort keys are not unique.")
    reconstructed = sorted(candidate_rows, key=lambda row: row["alignment_sort_key"])
    formal_keys = tuple(row["visit_key_tuple"] for row in candidate_rows)
    rebuilt_keys = tuple(row["visit_key_tuple"] for row in reconstructed)
    if formal_keys != rebuilt_keys:
        raise RuntimeError(
            "Formal candidate_visits order does not match Baseline alignment sort key order."
        )
    return "|".join(row["visit_key"] for row in reconstructed)


def _rank_status(visit_key, membership) -> str:
    if visit_key in membership["confirmed_visit_keys"]:
        return "confirmed"
    if visit_key in membership["undetermined_visit_keys"]:
        return "undetermined"
    return "absent"


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
    inlink_order_set = concrete_set.inlink_candidate_physical_order_result
    candidate_visit_set = inlink_order_set.candidate_visit_set_result
    right_of_entry_set = candidate_visit_set.right_of_entry_selection_result
    leading_set = right_of_entry_set.leading_confirmation_result
    arrived_set = leading_set.arrived_confirmation_result
    fork_result = arrived_set.alignment_fork_result.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError("Saved fork_result type is wrong.")
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError("Saved collector type is wrong.")
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
        "inlink_physical_orders": fork_result.inlink_physical_orders,
    }


def _trade_result_for_buyers(trade_rank_node, buyers_sorted):
    if not isinstance(trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError("Trade rank node type is wrong.")
    found = None
    for trade_result in trade_rank_node.candidate_trade_rank_results:
        candidate_buyers = tuple(
            _plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted
        )
        if candidate_buyers != buyers_sorted:
            continue
        if found is not None:
            raise RuntimeError("Two trade results share the same buyers_sorted.")
        found = trade_result
    if found is None or not isinstance(found, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError("No trade result matches buyers_sorted.")
    return found


def _records_by_key(records, label: str) -> dict:
    mapping = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(f"{label} repeats {_visit_text(visit_key)}.")
        mapping[visit_key] = record
    return mapping


def _selection_fields(selection_node, economic_node) -> dict:
    if not isinstance(selection_node, OrderControlTvtNodeMpCandidateSelectionResult):
        raise RuntimeError("Selection node type is wrong.")
    selected_economic = selection_node.selected_candidate_economic_result
    status_value = selection_node.selection_status.value
    if selected_economic is None:
        return {
            "selected_candidate_present": False,
            "selection_status": status_value,
            "selected_evaluation_index": None,
            "selected_buyers_sorted": None,
            "selected_trade_scope": None,
            "selected_total_G": None,
            "selected_total_R": None,
            "selected_surplus": None,
            "selected_economic": None,
        }
    if not isinstance(selected_economic, OrderControlTvtMpCandidateEconomicEvaluationResult):
        raise RuntimeError("Selected economic result type is wrong.")
    found = None
    index = 0
    for candidate_economic in economic_node.candidate_economic_evaluation_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if found is not None:
                raise RuntimeError("Selected economic result appears more than once.")
            found = index
    if found is None:
        raise RuntimeError("Selected economic result is missing from the node list.")
    sequence = selected_economic.candidate_local_virtual_calculation_result.binding_rank_sequence
    buyers_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    return {
        "selected_candidate_present": True,
        "selection_status": status_value,
        "selected_evaluation_index": found,
        "selected_buyers_sorted": buyers_sorted,
        "selected_economic": selected_economic,
        "selected_total_G": selected_economic.total_buyer_value_G,
        "selected_total_R": selected_economic.total_required_compensation_R,
        "selected_surplus": selected_economic.surplus,
    }


def _target_buyer_fields(shift, candidate_economic, trade_result, collector) -> dict:
    local_result = candidate_economic.candidate_local_virtual_calculation_result
    sequence = local_result.binding_rank_sequence
    buyers = tuple(
        _plain_visit_key(visit_key)
        for visit_key in sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    if TARGET_BUYER_VISIT_KEY not in buyers:
        return {}
    traffic_by_key = _records_by_key(local_result.traffic_observation_records, "traffic")
    buyer_records = _records_by_key(candidate_economic.buyer_economic_records, "buyer")
    seller_records = _records_by_key(candidate_economic.seller_economic_records, "seller")
    buyer_record = buyer_records.get(TARGET_BUYER_VISIT_KEY)
    if not isinstance(buyer_record, OrderControlTvtMpBuyerEconomicRecord):
        raise RuntimeError("Target buyer economic record is missing.")
    traffic = traffic_by_key.get(TARGET_BUYER_VISIT_KEY)
    if not isinstance(traffic, OrderControlTvtMpCandidateTrafficObservationRecord):
        raise RuntimeError("Target buyer traffic record is missing.")
    snapshot = collector.get_baseline_visit_snapshot(
        TARGET_BUYER_VISIT_KEY[0], TARGET_BUYER_VISIT_KEY[1]
    )
    baseline_arrival = None
    if snapshot is not None:
        baseline_arrival = snapshot.get("baseline_arrival_timestep")
    seller_keys = []
    seller_baseline = []
    seller_candidate = []
    seller_aligned_baseline = []
    seller_aligned_candidate = []
    seller_delay = []
    seller_vot = []
    seller_r = []
    for visit_key, seller_record in seller_records.items():
        if not isinstance(seller_record, OrderControlTvtMpSellerEconomicRecord):
            raise RuntimeError("Seller economic record type is wrong.")
        seller_keys.append(visit_key)
        baseline_passage = seller_record.baseline_passage_timestep
        candidate_passage_seller = seller_record.candidate_passage_timestep
        seller_baseline.append(str(baseline_passage))
        seller_candidate.append(str(candidate_passage_seller))
        if type(baseline_passage) is int and type(baseline_passage) is not bool:
            seller_aligned_baseline.append(str(baseline_passage - shift))
        else:
            seller_aligned_baseline.append("")
        if type(candidate_passage_seller) is int and type(candidate_passage_seller) is not bool:
            seller_aligned_candidate.append(str(candidate_passage_seller - shift))
        else:
            seller_aligned_candidate.append("")
        seller_delay.append(str(seller_record.expected_waiting_increase_timesteps))
        seller_vot.append(str(seller_record.declared_vot_per_second))
        seller_r.append(str(seller_record.required_compensation_R_s))
    candidate_passage = traffic.candidate_passage_timestep
    aligned_passage = None
    if type(candidate_passage) is int and type(candidate_passage) is not bool:
        aligned_passage = candidate_passage - shift
    aligned_arrival = None
    if type(baseline_arrival) is int and type(baseline_arrival) is not bool:
        aligned_arrival = baseline_arrival - shift
    aligned_baseline_passage = None
    if (
        type(buyer_record.baseline_passage_timestep) is int
        and type(buyer_record.baseline_passage_timestep) is not bool
    ):
        aligned_baseline_passage = buyer_record.baseline_passage_timestep - shift
    return {
        "target_buyer_baseline_arrival_timestep": baseline_arrival,
        "target_buyer_aligned_baseline_arrival_timestep": aligned_arrival,
        "target_buyer_baseline_passage_timestep": buyer_record.baseline_passage_timestep,
        "target_buyer_aligned_baseline_passage_timestep": aligned_baseline_passage,
        "target_buyer_candidate_arrival_timestep": None,
        "target_buyer_candidate_passage_timestep": candidate_passage,
        "target_buyer_aligned_candidate_passage_timestep": aligned_passage,
        "target_buyer_predicted_saving_timesteps": buyer_record.expected_time_saving_timesteps,
        "target_buyer_declared_vot_per_second": buyer_record.declared_vot_per_second,
        "target_buyer_G_b": buyer_record.gross_time_value_G_b,
        "seller_visit_keys": _join_keys(seller_keys),
        "seller_baseline_passage_timesteps": "|".join(seller_baseline),
        "seller_candidate_passage_timesteps": "|".join(seller_candidate),
        "seller_aligned_baseline_passage_timesteps": "|".join(seller_aligned_baseline),
        "seller_aligned_candidate_passage_timesteps": "|".join(seller_aligned_candidate),
        "seller_predicted_delay_timesteps": "|".join(seller_delay),
        "seller_declared_vot_per_second": "|".join(seller_vot),
        "seller_R_s": "|".join(seller_r),
    }


def _capture_decision(world, result, pre_driver_rank_membership, shift, capture_timestep) -> dict:
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"Driver result type is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(f"T={capture_timestep} atomic_apply_set_result is None.")
    columns = _saved_columns(atomic)
    selection_node = _one_node(columns["selection_nodes"], TARGET_NODE_NAME, "selection")
    economic_node = _one_node(columns["economic_nodes"], TARGET_NODE_NAME, "economic")
    trade_rank_node = _one_node(columns["trade_rank_nodes"], TARGET_NODE_NAME, "trade rank")
    candidate_visit_node = _one_node(
        columns["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate visits"
    )
    right_node = _one_node(columns["right_of_entry_nodes"], TARGET_NODE_NAME, "right of entry")
    if not isinstance(candidate_visit_node, OrderControlTvtNodeCandidateVisitSetResult):
        raise RuntimeError("Candidate visit node type is wrong.")
    if not isinstance(right_node, OrderControlTvtNodeRightOfEntrySelectionResult):
        raise RuntimeError("Right-of-entry node type is wrong.")
    selection = _selection_fields(selection_node, economic_node)
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(f"{TARGET_NODE_NAME} rank state is missing after the driver.")

    candidate_rows = []
    candidate_keys = []
    for order_index, candidate_visit in enumerate(candidate_visit_node.candidate_visits, start=1):
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError("candidate_visits entry type is wrong.")
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        candidate_keys.append(visit_key)
        snapshot = columns["collector"].get_baseline_visit_snapshot(visit_key[0], visit_key[1])
        collector_inlink = None if snapshot is None else snapshot.get("inlink_name")
        collector_passage = None if snapshot is None else snapshot.get("baseline_passage_timestep")
        vehicle_id, arrival_tiebreaker, collector_arrival = _snapshot_alignment_fields(
            snapshot,
            visit_key,
            candidate_visit.baseline_arrival_timestep,
        )
        if collector_inlink is not None and collector_inlink != candidate_visit.inlink_name:
            raise RuntimeError(f"{_visit_text(visit_key)} collector inlink differs from candidate visit.")
        aligned_sort_arrival = collector_arrival - shift
        alignment_sort_key = _baseline_alignment_sort_key(
            aligned_sort_arrival,
            arrival_tiebreaker,
            vehicle_id,
        )
        assigned = rank_state.assigned_rank(visit_key)
        candidate_rows.append(
            {
                "shift": shift,
                "actual_capture_timestep": capture_timestep,
                "aligned_timestep": capture_timestep - shift,
                "node_name": TARGET_NODE_NAME,
                "candidate_order": order_index,
                "baseline_local_rank": order_index,
                "visit_key": _visit_text(visit_key),
                "visit_key_tuple": visit_key,
                "formal_inlink_name": candidate_visit.inlink_name,
                "baseline_arrival_timestep": candidate_visit.baseline_arrival_timestep,
                "aligned_baseline_arrival_timestep": aligned_sort_arrival,
                "baseline_passage_timestep": (
                    collector_passage
                    if collector_passage is not None
                    else candidate_visit.baseline_passage_timestep
                ),
                "aligned_baseline_passage_timestep": (
                    None
                    if candidate_visit.baseline_passage_timestep is None
                    else candidate_visit.baseline_passage_timestep - shift
                ),
                "pre_driver_rank_status": _rank_status(visit_key, pre_driver_rank_membership),
                "post_driver_c_rank": assigned,
                "vehicle_id": vehicle_id,
                "arrival_tiebreaker": arrival_tiebreaker,
                "aligned_sort_arrival_timestep": aligned_sort_arrival,
                "baseline_alignment_sort_key_text": (
                    f"{aligned_sort_arrival}|{arrival_tiebreaker!r}|{vehicle_id}"
                ),
                "alignment_sort_key": alignment_sort_key,
            }
        )
    reconstructed_sort_order = _assert_candidate_order_matches_alignment_sort(candidate_rows)

    right_key = None
    if right_node.right_of_entry_visit_key is not None:
        right_key = _plain_visit_key(right_node.right_of_entry_visit_key)
    considered_rows = []
    target_buyer_rows = []
    selection_status_text = selection["selection_status"]
    for index, candidate_economic in enumerate(
        economic_node.candidate_economic_evaluation_results, start=1
    ):
        if not isinstance(candidate_economic, OrderControlTvtMpCandidateEconomicEvaluationResult):
            raise RuntimeError("Considered economic result type is wrong.")
        local_result = candidate_economic.candidate_local_virtual_calculation_result
        sequence = local_result.binding_rank_sequence
        buyers = tuple(
            _plain_visit_key(visit_key)
            for visit_key in sequence.concrete_buyer_candidate_set.buyers_sorted
        )
        trade_result = _trade_result_for_buyers(trade_rank_node, buyers)
        scope = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.trade_scope)
        counts = {"buyer": 0, "seller": 0, "nonparticipating": 0}
        binding_by_key = {}
        for binding_visit in sequence.visits_in_binding_order:
            binding_by_key[_plain_visit_key(binding_visit.visit_key)] = binding_visit
        for visit_key in scope:
            binding_visit = binding_by_key.get(visit_key)
            if binding_visit is None:
                raise RuntimeError(f"Candidate {index} scope visit missing binding.")
            counts[_role_name(binding_visit.trade_role)] = (
                counts[_role_name(binding_visit.trade_role)] + 1
            )
        ranks = []
        for visit_key in scope:
            ranks.append(str(trade_result.assigned_rank(visit_key)))
        selected_flag = candidate_economic is selection["selected_economic"]
        if selected_flag:
            selection_reason = selection_status_text
        elif candidate_economic.economically_feasible is not True:
            selection_reason = "not_selected_infeasible"
        else:
            selection_reason = "not_selected"
        row = {
            "shift": shift,
            "actual_capture_timestep": capture_timestep,
            "aligned_timestep": capture_timestep - shift,
            "node_name": TARGET_NODE_NAME,
            "evaluation_index": index,
            "selected": selected_flag,
            "contains_target_buyer": TARGET_BUYER_VISIT_KEY in buyers,
            "buyers_sorted": _join_keys(buyers),
            "buyers_sorted_tuple": buyers,
            "buyer_count": counts["buyer"],
            "seller_count": counts["seller"],
            "nonparticipating_count": counts["nonparticipating"],
            "trade_scope_count": len(scope),
            "trade_scope_visit_keys": _join_keys(scope),
            "trade_scope_tuple": scope,
            "candidate_ranks": "|".join(ranks),
            "total_G": candidate_economic.total_buyer_value_G,
            "total_R": candidate_economic.total_required_compensation_R,
            "surplus": candidate_economic.surplus,
            "economically_feasible": candidate_economic.economically_feasible,
            "infeasibility_reasons": _serialize_reasons(candidate_economic.infeasibility_reasons),
            "selection_reason": selection_reason,
            "k_last_buyer": sequence.k_last_buyer,
            "k_decision_window": sequence.k_decision_window,
            "k_fixed": sequence.k_fixed,
        }
        row.update(
            _target_buyer_fields(shift, candidate_economic, trade_result, columns["collector"])
        )
        considered_rows.append(row)
        if row["contains_target_buyer"] is True:
            target_buyer_rows.append(row)

    selected_scope_text = None
    if selection["selected_candidate_present"] is True:
        selected_row = None
        for row in considered_rows:
            if row["selected"] is True:
                selected_row = row
                break
        if selected_row is None:
            raise RuntimeError("Selected flag is missing from considered candidates.")
        selection["selected_trade_scope"] = selected_row["trade_scope_tuple"]
        selected_scope_text = selected_row["trade_scope_visit_keys"]
        selection["selected_buyer_count"] = selected_row["buyer_count"]
        selection["selected_seller_count"] = selected_row["seller_count"]
        selection["selected_nonparticipating_count"] = selected_row["nonparticipating_count"]
        selection["selected_trade_scope_count"] = selected_row["trade_scope_count"]
    else:
        selection["selected_buyer_count"] = None
        selection["selected_seller_count"] = None
        selection["selected_nonparticipating_count"] = None
        selection["selected_trade_scope_count"] = None

    summary = {
        "shift": shift,
        "actual_capture_timestep": capture_timestep,
        "aligned_timestep": capture_timestep - shift,
        "node_name": TARGET_NODE_NAME,
        "selection_status": selection["selection_status"],
        "selected_candidate_present": selection["selected_candidate_present"],
        "selected_evaluation_index": selection["selected_evaluation_index"],
        "selected_buyers_sorted": (
            None
            if selection["selected_buyers_sorted"] is None
            else _join_keys(selection["selected_buyers_sorted"])
        ),
        "selected_buyers_tuple": selection["selected_buyers_sorted"],
        "selected_trade_scope": selected_scope_text,
        "selected_trade_scope_tuple": selection["selected_trade_scope"],
        "selected_total_G": selection["selected_total_G"],
        "selected_total_R": selection["selected_total_R"],
        "selected_surplus": selection["selected_surplus"],
        "selected_buyer_count": selection["selected_buyer_count"],
        "selected_seller_count": selection["selected_seller_count"],
        "selected_nonparticipating_count": selection["selected_nonparticipating_count"],
        "selected_trade_scope_count": selection["selected_trade_scope_count"],
        "p_minus_one_eligible_visit_count_before_limit": (
            candidate_visit_node.p_minus_one_eligible_visit_count_before_limit
        ),
        "candidate_visit_count": len(candidate_keys),
        "candidate_visit_keys": _join_keys(candidate_keys),
        "candidate_visit_key_tuples": tuple(candidate_keys),
        "reconstructed_sort_order": reconstructed_sort_order,
        "formal_candidate_order_matches_sort_key": True,
        "right_of_entry_visit_key": None if right_key is None else _visit_text(right_key),
        "right_of_entry_visit_key_tuple": right_key,
        "right_of_entry_selection_status": right_node.selection_status.value,
        "right_of_entry_baseline_passage_timestep": (
            candidate_visit_node.right_of_entry_baseline_passage_timestep
        ),
        "considered_candidate_count": len(considered_rows),
        "target_buyer_candidate_count": len(target_buyer_rows),
    }
    return {
        "summary": summary,
        "candidate_visits": candidate_rows,
        "considered": considered_rows,
        "target_buyer_candidates": target_buyer_rows,
    }


def wrapped_driver(world):
    pre_driver_rank_membership = None
    if world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is None:
            if world.T == GATE.capture_timestep:
                pre_driver_rank_membership = _snapshot_pre_driver_rank_membership(world)
    result = GATE.original_driver(world)
    if world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is None:
            if world.T == GATE.capture_timestep:
                if pre_driver_rank_membership is None:
                    raise RuntimeError("Pre-driver rank snapshot is missing.")
                if GATE.captured is True:
                    raise RuntimeError("Target decision was captured twice.")
                GATE.snapshot = _capture_decision(
                    world,
                    result,
                    pre_driver_rank_membership,
                    GATE.shift,
                    GATE.capture_timestep,
                )
                GATE.captured = True
    return result


def install_hooks(real_world, shift: int, capture_timestep: int) -> None:
    if GATE.installed is True:
        raise RuntimeError("Diagnostic hooks are already installed.")
    GATE.real_world = real_world
    GATE.shift = shift
    GATE.capture_timestep = capture_timestep
    GATE.original_driver = driver_module.run_tvt_mp_driver
    driver_module.run_tvt_mp_driver = wrapped_driver
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_driver
    GATE.original_driver = None
    GATE.real_world = None
    GATE.capture_timestep = None
    GATE.shift = None
    GATE.installed = False


def _prepare_shift0_world():
    world = shift0_trial.build_world()
    vot_values = shift0_trial._true_vot_sequence()
    vot_records = shift0_trial.build_vehicle_vot_records(shift0_trial.VEHICLE_SPECS, vot_values)
    shift0_trial.add_vehicles_to_world(world, shift0_trial.VEHICLE_SPECS, vot_records)
    shift0_trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    return world


def _prepare_shift3_world():
    config = shift_trial.shift_trial_config(SHIFT3_DEPARTURE_SHIFT)
    if config.evaluation_end_timestep != 902:
        raise RuntimeError("Shift 3 evaluation end is not 902.")
    if config.internal_tsize != 933:
        raise RuntimeError("Shift 3 internal TSIZE is not 933.")
    if config.expected_world_t_after_sim != 903:
        raise RuntimeError("Shift 3 expected World.T is not 903.")
    world = shift_trial.build_world(config)
    vehicle_specs = shift_trial.build_vehicle_specs(SHIFT3_DEPARTURE_SHIFT)
    vot_values = shift_trial._true_vot_sequence()
    vot_records = shift_trial.build_vehicle_vot_records(vehicle_specs, vot_values)
    shift_trial.add_vehicles_to_world(world, vehicle_specs, vot_records)
    shift_trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    if world.TSIZE != 933:
        raise RuntimeError(f"Shift 3 World.TSIZE is {world.TSIZE}, expected 933.")
    if world.order_control_tvt_evaluation_end_timestep != 902:
        raise RuntimeError("Shift 3 evaluation end on the world is not 902.")
    return world


def _run_capture(shift: int, capture_timestep: int, world) -> dict:
    _reset_gate()
    install_hooks(world, shift, capture_timestep)
    try:
        world.exec_simulation(until_t=capture_timestep * world.DELTAT)
    finally:
        restore_hooks()
    if world.T != capture_timestep + 1:
        raise RuntimeError(
            f"Shift {shift}: World.T is {world.T}, expected {capture_timestep + 1}."
        )
    if GATE.captured is not True or GATE.snapshot is None:
        raise RuntimeError(f"Shift {shift}: decision T={capture_timestep} was not captured.")
    snapshot = GATE.snapshot
    _reset_gate()
    return snapshot


def _assert_finite_numeric_economic_value(value, label: str) -> float:
    if value is None:
        raise RuntimeError(f"{label} is None.")
    if type(value) is bool:
        raise RuntimeError(f"{label} is bool.")
    if type(value) not in (int, float):
        raise RuntimeError(f"{label} must be int or float; got {type(value).__name__}.")
    numeric = float(value)
    if math.isfinite(numeric) is not True:
        raise RuntimeError(f"{label} is not finite: {value!r}.")
    return numeric


def _validate_runtime_expectations(shift0: dict, shift3: dict) -> None:
    summary0 = shift0["summary"]
    summary3 = shift3["summary"]
    if summary0["actual_capture_timestep"] != SHIFT0_CAPTURE_TIMESTEP:
        raise RuntimeError("Shift 0 capture timestep is not 602.")
    if summary0["aligned_timestep"] != ALIGNED_TIMESTEP:
        raise RuntimeError("Shift 0 aligned timestep is not 602.")
    if summary0["node_name"] != TARGET_NODE_NAME:
        raise RuntimeError("Shift 0 node is not northeast_intersection.")
    if summary0["selected_candidate_present"] is not False:
        raise RuntimeError("Shift 0 T=602 was expected to have no selected candidate.")
    if summary3["actual_capture_timestep"] != SHIFT3_CAPTURE_TIMESTEP:
        raise RuntimeError("Shift 3 capture timestep is not 605.")
    if summary3["aligned_timestep"] != ALIGNED_TIMESTEP:
        raise RuntimeError("Shift 3 aligned timestep is not 602.")
    if summary3["node_name"] != TARGET_NODE_NAME:
        raise RuntimeError("Shift 3 node is not northeast_intersection.")
    if summary3["selected_candidate_present"] is not True:
        raise RuntimeError("Shift 3 T=605 was expected to have a selected candidate.")
    if summary3["selected_buyers_tuple"] is None:
        raise RuntimeError("Shift 3 selected buyers are missing.")
    if TARGET_BUYER_VISIT_KEY not in summary3["selected_buyers_tuple"]:
        raise RuntimeError("Shift 3 selected buyers do not include veh_wn_en_base_041:2.")
    if summary3["selected_buyer_count"] != 1:
        raise RuntimeError("Shift 3 selected buyer_count is not 1.")
    if summary3["selected_seller_count"] != 1:
        raise RuntimeError("Shift 3 selected seller_count is not 1.")
    if summary3["selected_nonparticipating_count"] != 0:
        raise RuntimeError("Shift 3 selected nonparticipating_count is not 0.")
    if summary3["selected_trade_scope_count"] != 2:
        raise RuntimeError("Shift 3 selected trade_scope_count is not 2.")
    total_g = _assert_finite_numeric_economic_value(
        summary3["selected_total_G"], "Shift 3 selected total_G"
    )
    total_r = _assert_finite_numeric_economic_value(
        summary3["selected_total_R"], "Shift 3 selected total_R"
    )
    surplus = _assert_finite_numeric_economic_value(
        summary3["selected_surplus"], "Shift 3 selected surplus"
    )
    if _close(surplus, total_g - total_r) is not True:
        raise RuntimeError(
            f"Shift 3 selected surplus {surplus!r} is not total_G - total_R "
            f"({total_g!r} - {total_r!r})."
        )


def _same_optional_number(left, right) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    if type(left) is bool or type(right) is bool:
        return False
    return _close(left, right)


def _candidate_correspondence_key(row: dict) -> tuple:
    return (row["buyers_sorted_tuple"], row["trade_scope_tuple"])


def _target_buyer_candidate_map(rows: list[dict]) -> dict[tuple, dict]:
    mapping: dict[tuple, dict] = {}
    for row in rows:
        key = _candidate_correspondence_key(row)
        if key in mapping:
            raise RuntimeError(
                "Duplicate target buyer Candidate correspondence key "
                f"(buyers_sorted, trade_scope): {row['buyers_sorted']!r} "
                f"{row['trade_scope_visit_keys']!r}."
            )
        mapping[key] = row
    return mapping


def _focus_rows(capture: dict) -> dict:
    rows = {
        row["visit_key_tuple"]: row
        for row in capture["candidate_visits"]
        if row["visit_key_tuple"] in ORDER_FOCUS_VISIT_KEYS
    }
    return rows


def _relation_text(left_key, right_key, left_label: str, right_label: str) -> str:
    if left_key < right_key:
        return f"{left_label} < {right_label}"
    if right_key < left_key:
        return f"{right_label} < {left_label}"
    return "equal"


def _classify_candidate_order_divergence(shift0: dict, shift3: dict) -> tuple[str, list[str]]:
    rows0 = _focus_rows(shift0)
    rows3 = _focus_rows(shift3)
    notes = []
    if len(rows0) != 2 or len(rows3) != 2:
        notes.append("対象2 Visitsが両shiftのCandidate Visitsに揃っていない。")
        return "candidate_visit_order_divergence_unresolved", notes
    left_key = ORDER_FOCUS_VISIT_KEYS[0]
    right_key = ORDER_FOCUS_VISIT_KEYS[1]
    a0 = rows0[left_key]
    b0 = rows0[right_key]
    a3 = rows3[left_key]
    b3 = rows3[right_key]
    arrivals_match = (
        a0["aligned_sort_arrival_timestep"] == a3["aligned_sort_arrival_timestep"]
        and b0["aligned_sort_arrival_timestep"] == b3["aligned_sort_arrival_timestep"]
        and a0["aligned_sort_arrival_timestep"] == b0["aligned_sort_arrival_timestep"]
        and a3["aligned_sort_arrival_timestep"] == b3["aligned_sort_arrival_timestep"]
    )
    vehicle_ids_match = a0["vehicle_id"] == a3["vehicle_id"] and b0["vehicle_id"] == b3["vehicle_id"]
    tiebreakers_match = (
        a0["arrival_tiebreaker"] == a3["arrival_tiebreaker"]
        and b0["arrival_tiebreaker"] == b3["arrival_tiebreaker"]
    )
    relation0 = _relation_text(a0["alignment_sort_key"], b0["alignment_sort_key"], _visit_text(left_key), _visit_text(right_key))
    relation3 = _relation_text(a3["alignment_sort_key"], b3["alignment_sort_key"], _visit_text(left_key), _visit_text(right_key))
    tiebreaker_relation0 = _relation_text(
        (a0["arrival_tiebreaker"],),
        (b0["arrival_tiebreaker"],),
        _visit_text(left_key),
        _visit_text(right_key),
    )
    tiebreaker_relation3 = _relation_text(
        (a3["arrival_tiebreaker"],),
        (b3["arrival_tiebreaker"],),
        _visit_text(left_key),
        _visit_text(right_key),
    )
    formal_pair0 = [row["visit_key_tuple"] for row in shift0["candidate_visits"] if row["visit_key_tuple"] in ORDER_FOCUS_VISIT_KEYS]
    formal_pair3 = [row["visit_key_tuple"] for row in shift3["candidate_visits"] if row["visit_key_tuple"] in ORDER_FOCUS_VISIT_KEYS]
    notes.append(f"shift 0 tiebreaker relation: {tiebreaker_relation0}")
    notes.append(f"shift 3 tiebreaker relation: {tiebreaker_relation3}")
    notes.append(f"shift 0 full sort relation: {relation0}")
    notes.append(f"shift 3 full sort relation: {relation3}")
    notes.append(f"vehicle_id match across shifts: {vehicle_ids_match}")
    if (
        a0["alignment_sort_key"] == a3["alignment_sort_key"]
        and b0["alignment_sort_key"] == b3["alignment_sort_key"]
        and formal_pair0 != formal_pair3
    ):
        raise RuntimeError(
            "sort_order_contract_violation: aligned arrival, arrival_tiebreaker, and "
            "vehicle_id match, but formal Candidate order reversed."
        )
    tiebreaker_flipped = (
        tiebreaker_relation0 != "equal"
        and tiebreaker_relation3 != "equal"
        and tiebreaker_relation0 != tiebreaker_relation3
    )
    if arrivals_match and vehicle_ids_match and tiebreaker_flipped and tiebreakers_match is not True:
        notes.append(
            "aligned Baseline arrivalは同一、vehicle_idは同一、arrival_tiebreakerがshift間で変化し、"
            "大小関係が反転した。正式sort keyに従ってCandidate順が反転した。"
            "Candidate順実装がsort keyに反したのではない。"
            "別simulation間のarrival_tiebreaker乱数割当てが時間平行移動不変でない。"
        )
        return "arrival_tiebreaker_assignment_divergence", notes
    if arrivals_match and tiebreakers_match and vehicle_ids_match is not True:
        notes.append("arrival_tiebreakerは同一だがvehicle_idがshift間で変化した。")
        return "vehicle_id_divergence", notes
    notes.append("対象2 Visitsのsort key比較だけでは反転原因をA/B/Cに分類できない。")
    return "candidate_visit_order_divergence_unresolved", notes


def _first_divergence(shift0: dict, shift3: dict) -> tuple[str, list[str], str | None]:
    notes = []
    keys0 = shift0["summary"]["candidate_visit_key_tuples"]
    keys3 = shift3["summary"]["candidate_visit_key_tuples"]
    if set(keys0) != set(keys3):
        notes.append(
            "Candidate Visit集合が異なる。"
            f" shift0={shift0['summary']['candidate_visit_keys']}"
            f" shift3={shift3['summary']['candidate_visit_keys']}"
        )
        return "candidate_visit_set_divergence", notes, None
    notes.append("A. Candidate Visit集合は同一。")
    if keys0 != keys3:
        notes.append("Candidate Visit順が異なる。")
        detail_cause, detail_notes = _classify_candidate_order_divergence(shift0, shift3)
        notes.extend(detail_notes)
        notes.append(f"detail_cause={detail_cause}")
        return "candidate_visit_order_divergence", notes, detail_cause
    notes.append("B. Candidate Visit順は同一。")
    if (
        shift0["summary"]["right_of_entry_visit_key_tuple"]
        != shift3["summary"]["right_of_entry_visit_key_tuple"]
    ):
        notes.append(
            "right-of-entryが異なる。"
            f" shift0={shift0['summary']['right_of_entry_visit_key']}"
            f" shift3={shift3['summary']['right_of_entry_visit_key']}"
        )
        return "right_of_entry_divergence", notes, None
    notes.append("C. right-of-entryは同一。")

    visits0 = {row["visit_key_tuple"]: row for row in shift0["candidate_visits"]}
    visits3 = {row["visit_key_tuple"]: row for row in shift3["candidate_visits"]}
    baseline_differs = False
    for visit_key in keys0:
        left = visits0[visit_key]
        right = visits3[visit_key]
        if left["aligned_baseline_arrival_timestep"] != right["aligned_baseline_arrival_timestep"]:
            baseline_differs = True
        if left["aligned_baseline_passage_timestep"] != right["aligned_baseline_passage_timestep"]:
            baseline_differs = True
    if baseline_differs is True:
        notes.append("shift補正後のBaseline arrivalまたはpassageが異なる。")
        return "baseline_prediction_divergence", notes, None
    notes.append("F. shift補正後のBaseline arrival／passageは同一。")

    count0 = shift0["summary"]["target_buyer_candidate_count"]
    count3 = shift3["summary"]["target_buyer_candidate_count"]
    notes.append(f"D. target buyer Candidate件数 shift0={count0} shift3={count3}。")
    if count0 != count3:
        notes.append(
            "target buyerを含むconsidered Candidateの形成件数が異なる。"
            "selected Candidate選択より上流の差（concrete buyer候補・trade rank・"
            "local calculation）。current captureでは内部小段階までは分離しない。"
        )
        return "candidate_local_calculation_divergence", notes, None

    map0 = _target_buyer_candidate_map(shift0["target_buyer_candidates"])
    map3 = _target_buyer_candidate_map(shift3["target_buyer_candidates"])
    keys0 = set(map0.keys())
    keys3 = set(map3.keys())
    if keys0 != keys3:
        notes.append(
            "target buyer Candidateの対応key集合"
            "（buyers_sorted, trade_scope VisitKey順）が異なる。"
        )
        return "candidate_local_calculation_divergence", notes, None

    for key in sorted(keys0, key=lambda item: (_join_keys(item[0]), _join_keys(item[1]))):
        left = map0[key]
        right = map3[key]
        if left["candidate_ranks"] != right["candidate_ranks"]:
            notes.append(
                "対応するtarget buyer CandidateのCandidate順位が異なる。"
                f" buyers={left['buyers_sorted']} scope={left['trade_scope_visit_keys']}"
            )
            return "candidate_local_calculation_divergence", notes, None
        if (
            left.get("target_buyer_aligned_baseline_arrival_timestep")
            != right.get("target_buyer_aligned_baseline_arrival_timestep")
            or left.get("target_buyer_aligned_baseline_passage_timestep")
            != right.get("target_buyer_aligned_baseline_passage_timestep")
            or left.get("target_buyer_aligned_candidate_passage_timestep")
            != right.get("target_buyer_aligned_candidate_passage_timestep")
            or left.get("seller_aligned_baseline_passage_timesteps")
            != right.get("seller_aligned_baseline_passage_timesteps")
            or left.get("seller_aligned_candidate_passage_timesteps")
            != right.get("seller_aligned_candidate_passage_timesteps")
        ):
            notes.append(
                "shift補正後のbuyer／seller BaselineまたはCandidate passageが異なる。"
                f" buyers={left['buyers_sorted']} scope={left['trade_scope_visit_keys']}"
            )
            return "candidate_local_calculation_divergence", notes, None
        if (
            _same_optional_number(left["total_G"], right["total_G"]) is not True
            or _same_optional_number(left["total_R"], right["total_R"]) is not True
            or _same_optional_number(left["surplus"], right["surplus"]) is not True
        ):
            notes.append(
                "対応するtarget buyer Candidateのtotal_G／total_R／surplusが異なる。"
                f" buyers={left['buyers_sorted']}"
            )
            return "candidate_local_calculation_divergence", notes, None
        if left["economically_feasible"] != right["economically_feasible"]:
            notes.append(
                "対応するtarget buyer Candidateのeconomically_feasibleが異なる。"
                f" buyers={left['buyers_sorted']}"
            )
            return "economic_feasibility_divergence", notes, None
        if left["infeasibility_reasons"] != right["infeasibility_reasons"]:
            notes.append(
                "対応するtarget buyer Candidateのinfeasibility reasonsが異なる。"
                f" buyers={left['buyers_sorted']}"
            )
            return "economic_feasibility_divergence", notes, None
        notes.append(
            "E-J. 対応keyのtarget buyer CandidateはCandidate順位・aligned時刻・"
            "経済値・feasible・reasonsが一致。"
            f" buyers={left['buyers_sorted']} scope={left['trade_scope_visit_keys']} "
            f"(ref index shift0={left['evaluation_index']} shift3={right['evaluation_index']})"
        )

    if (
        shift0["summary"]["selected_candidate_present"]
        != shift3["summary"]["selected_candidate_present"]
    ):
        notes.append(
            "Candidate Visit・right-of-entry・aligned Baseline・対応target buyer Candidateは一致したが、"
            "selected Candidateの有無またはselected indexだけが異なる。"
            f" shift0={shift0['summary']['selected_candidate_present']}"
            f" status={shift0['summary']['selection_status']}"
            f" shift3={shift3['summary']['selected_candidate_present']}"
            f" status={shift3['summary']['selection_status']}"
            f" index={shift3['summary']['selected_evaluation_index']}"
        )
        return "candidate_selection_divergence", notes, None
    if (
        shift0["summary"]["selected_evaluation_index"]
        != shift3["summary"]["selected_evaluation_index"]
    ):
        notes.append(
            "selected Candidate indexのみが異なる。"
            f" shift0={shift0['summary']['selected_evaluation_index']}"
            f" shift3={shift3['summary']['selected_evaluation_index']}"
        )
        return "candidate_selection_divergence", notes, None
    notes.append("K. selectedの有無は同一。現在の捕捉範囲では最初の差を特定できない。")
    return "unresolved_with_current_capture", notes, None


def _alignment_review_lines(shift0: dict, shift3: dict, detail_cause: str | None) -> list[str]:
    lines = [
        "Baseline alignment sort key:",
        f"detail_cause: {detail_cause}",
        (
            "fixed arrival tiebreakerは同一simulation内の同一Visitへ一度付与された後は固定される。"
            "別simulation間で同じVehicle・Visitへ同じ乱数値が保証されるとは限らない。"
            "初回訪問ではW.rng.random()、再訪ではW.order_control_rng.random()。"
            "本診断は正式snapshotの値を比較し、乱数消費順の推測だけで結論づけない。"
        ),
    ]
    for capture in (shift0, shift3):
        summary = capture["summary"]
        lines.append(
            f"shift {summary['shift']} reconstructed_sort_order={summary['reconstructed_sort_order']} "
            f"formal_candidate_order_matches_sort_key="
            f"{summary['formal_candidate_order_matches_sort_key']}"
        )
        focus = _focus_rows(capture)
        for visit_key in ORDER_FOCUS_VISIT_KEYS:
            row = focus.get(visit_key)
            if row is None:
                lines.append(f"  shift {summary['shift']} {_visit_text(visit_key)}: not in Candidate Visits")
                continue
            lines.append(
                f"  shift {summary['shift']} {_visit_text(visit_key)} "
                f"sort_key={row['baseline_alignment_sort_key_text']} "
                f"vehicle_id={row['vehicle_id']} tiebreaker={row['arrival_tiebreaker']!r}"
            )
    rows0 = _focus_rows(shift0)
    rows3 = _focus_rows(shift3)
    if len(rows0) == 2 and len(rows3) == 2:
        left_key = ORDER_FOCUS_VISIT_KEYS[0]
        right_key = ORDER_FOCUS_VISIT_KEYS[1]
        lines.append(
            "shift 0 tiebreaker relation: "
            + _relation_text(
                (rows0[left_key]["arrival_tiebreaker"],),
                (rows0[right_key]["arrival_tiebreaker"],),
                _visit_text(left_key),
                _visit_text(right_key),
            )
        )
        lines.append(
            "shift 3 tiebreaker relation: "
            + _relation_text(
                (rows3[left_key]["arrival_tiebreaker"],),
                (rows3[right_key]["arrival_tiebreaker"],),
                _visit_text(left_key),
                _visit_text(right_key),
            )
        )
        vehicle_ids_match = (
            rows0[left_key]["vehicle_id"] == rows3[left_key]["vehicle_id"]
            and rows0[right_key]["vehicle_id"] == rows3[right_key]["vehicle_id"]
        )
        lines.append(f"vehicle_id match across shifts: {vehicle_ids_match}")
        arrivals_same = (
            rows0[left_key]["aligned_sort_arrival_timestep"]
            == rows3[left_key]["aligned_sort_arrival_timestep"]
            == rows0[right_key]["aligned_sort_arrival_timestep"]
            == rows3[right_key]["aligned_sort_arrival_timestep"]
        )
        tiebreakers_same = (
            rows0[left_key]["arrival_tiebreaker"] == rows3[left_key]["arrival_tiebreaker"]
            and rows0[right_key]["arrival_tiebreaker"] == rows3[right_key]["arrival_tiebreaker"]
        )
        lines.append(f"aligned arrival same for both visits and both shifts: {arrivals_same}")
        lines.append(f"arrival_tiebreaker same across shifts: {tiebreakers_same}")
        lines.append(
            "shift 0 full sort relation: "
            + _relation_text(
                rows0[left_key]["alignment_sort_key"],
                rows0[right_key]["alignment_sort_key"],
                _visit_text(left_key),
                _visit_text(right_key),
            )
        )
        lines.append(
            "shift 3 full sort relation: "
            + _relation_text(
                rows3[left_key]["alignment_sort_key"],
                rows3[right_key]["alignment_sort_key"],
                _visit_text(left_key),
                _visit_text(right_key),
            )
        )
        relation0 = _relation_text(
            (rows0[left_key]["arrival_tiebreaker"],),
            (rows0[right_key]["arrival_tiebreaker"],),
            _visit_text(left_key),
            _visit_text(right_key),
        )
        relation3 = _relation_text(
            (rows3[left_key]["arrival_tiebreaker"],),
            (rows3[right_key]["arrival_tiebreaker"],),
            _visit_text(left_key),
            _visit_text(right_key),
        )
        lines.append(
            "tiebreaker inequality reversed across shifts: "
            f"{relation0 != 'equal' and relation3 != 'equal' and relation0 != relation3}"
        )
        reaches_vehicle_id = (
            rows0[left_key]["aligned_sort_arrival_timestep"]
            == rows0[right_key]["aligned_sort_arrival_timestep"]
            and rows0[left_key]["arrival_tiebreaker"] == rows0[right_key]["arrival_tiebreaker"]
        ) or (
            rows3[left_key]["aligned_sort_arrival_timestep"]
            == rows3[right_key]["aligned_sort_arrival_timestep"]
            and rows3[left_key]["arrival_tiebreaker"] == rows3[right_key]["arrival_tiebreaker"]
        )
        lines.append(f"vehicle_id comparison reached within a shift: {reaches_vehicle_id}")
    return lines


def _build_review(
    shift0: dict,
    shift3: dict,
    label: str,
    notes: list[str],
    detail_cause: str | None,
) -> str:
    lines = [
        "departure shift 0 / 3 first divergence review",
        f"aligned timestep: {ALIGNED_TIMESTEP}",
        f"node: {TARGET_NODE_NAME}",
        f"target buyer: {_visit_text(TARGET_BUYER_VISIT_KEY)}",
        f"first_divergence_layer: {label}",
        f"detail_cause: {detail_cause}",
        "",
        "判定メモ（上流の差がある場合、後段を原因としない）:",
    ]
    for note in notes:
        lines.append(f"  {note}")
    lines.append("")
    lines.append(
        "Candidate arrivalは正式traffic／economic recordのfieldではないため保存値は空。"
        "時刻差の判定にはBaseline arrival／passageとCandidate passageを使う。"
    )
    lines.append(
        "公式支払・公式補償が0.0であっても、Candidate経済評価のtotal_G／total_R／"
        "surplusが0.0とは限らない。本診断のselected_total_G／R／surplusはCandidate "
        "economic evaluation objectの値である。公式支払・補償は正式research CSV上の"
        "別の値であり、本診断ではresearch outputを生成・読込みしない。"
    )
    lines.append("")
    lines.extend(_alignment_review_lines(shift0, shift3, detail_cause))
    lines.append("")
    for capture in (shift0, shift3):
        summary = capture["summary"]
        lines.append(
            f"shift {summary['shift']}: actual T={summary['actual_capture_timestep']} "
            f"aligned T={summary['aligned_timestep']} "
            f"selection_status={summary['selection_status']} "
            f"selected={summary['selected_candidate_present']} "
            f"index={summary['selected_evaluation_index']} "
            f"buyers={summary['selected_buyers_sorted']} "
            f"scope={summary['selected_trade_scope']} "
            f"G={summary['selected_total_G']} R={summary['selected_total_R']} "
            f"surplus={summary['selected_surplus']} "
            f"P-1={summary['p_minus_one_eligible_visit_count_before_limit']} "
            f"candidate_visits={summary['candidate_visit_count']} "
            f"ROE={summary['right_of_entry_visit_key']} "
            f"considered={summary['considered_candidate_count']} "
            f"target_buyer_candidates={summary['target_buyer_candidate_count']}"
        )
    lines.append("")
    lines.append("target buyer candidates:")
    for capture in (shift0, shift3):
        if len(capture["target_buyer_candidates"]) == 0:
            lines.append(f"  shift {capture['summary']['shift']}: 0件")
            continue
        for row in capture["target_buyer_candidates"]:
            lines.append(
                f"  shift {row['shift']} index={row['evaluation_index']} selected={row['selected']} "
                f"buyers={row['buyers_sorted']} scope={row['trade_scope_visit_keys']} "
                f"ranks={row['candidate_ranks']} "
                f"G={row['total_G']} R={row['total_R']} surplus={row['surplus']} "
                f"feasible={row['economically_feasible']} reasons={row['infeasibility_reasons']} "
                f"buyer_save={row.get('target_buyer_predicted_saving_timesteps')} "
                f"G_b={row.get('target_buyer_G_b')} "
                f"sellers={row.get('seller_visit_keys')} "
                f"seller_aligned_P={row.get('seller_aligned_candidate_passage_timesteps')} "
                f"R_s={row.get('seller_R_s')}"
            )
    lines.append("")
    lines.append(
        "candidate_selection_divergence は、Candidate Visit・順・right-of-entry・"
        "aligned Baseline・対応target buyer Candidate（形成・scope・aligned時刻・"
        "経済値・feasible・reasons）が一致したうえで、selected の有無または index "
        "だけが異なる場合に限る。"
    )
    return "\n".join(lines) + "\n"


def _function_node(tree, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_count(function_node, owner: str, attr: str) -> int:
    count = 0
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == attr:
            if isinstance(func.value, ast.Name) and func.value.id == owner:
                count = count + 1
    return count


def _module_level_string_constants(tree) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant):
            continue
        if type(node.value.value) is not str:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


def _test_is_selected_economic_none(test) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Is):
        return False
    if len(test.comparators) != 1:
        return False
    comparator = test.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value is not None:
        return False
    if not isinstance(test.left, ast.Name):
        return False
    return test.left.id == "selected_economic"


def _dict_literal_has_false_keyword(value_node, keyword: str) -> bool:
    if not isinstance(value_node, ast.Dict):
        return False
    for key_node, val_node in zip(value_node.keys, value_node.values):
        if not isinstance(key_node, ast.Constant) or key_node.value != keyword:
            continue
        if isinstance(val_node, ast.Constant) and val_node.value is False:
            return True
    return False


def _dict_literal_has_none_keyword(value_node, keyword: str) -> bool:
    if not isinstance(value_node, ast.Dict):
        return False
    for key_node, val_node in zip(value_node.keys, value_node.values):
        if not isinstance(key_node, ast.Constant) or key_node.value != keyword:
            continue
        if isinstance(val_node, ast.Constant) and val_node.value is None:
            return True
    return False


def _assert_selection_fields_none_branch(selection_fields_node) -> None:
    found_none_branch = False
    for node in ast.walk(selection_fields_node):
        if not isinstance(node, ast.If):
            continue
        if _test_is_selected_economic_none(node.test) is not True:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Raise):
                raise RuntimeError(
                    "_selection_fields must not raise when selected_economic is None."
                )
            if not isinstance(stmt, ast.Return):
                continue
            if _dict_literal_has_false_keyword(stmt.value, "selected_candidate_present") is not True:
                raise RuntimeError(
                    "None branch must return selected_candidate_present=False."
                )
            if _dict_literal_has_none_keyword(stmt.value, "selected_economic") is not True:
                raise RuntimeError("None branch must return selected_economic=None.")
            found_none_branch = True
    if found_none_branch is not True:
        raise RuntimeError(
            "_selection_fields must branch on selected_economic is None and return a dict."
        )


def _main_output_dir_contract(main_node) -> None:
    exists_lineno = None
    mkdir_lineno = None
    run_capture_lineno = None
    runtime_error_after_exists = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "exists":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "OUTPUT_DIR":
                    if exists_lineno is None or node.lineno < exists_lineno:
                        exists_lineno = node.lineno
            if node.func.attr == "mkdir":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "OUTPUT_DIR":
                    if mkdir_lineno is None or node.lineno < mkdir_lineno:
                        mkdir_lineno = node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_run_capture":
                if run_capture_lineno is None or node.lineno < run_capture_lineno:
                    run_capture_lineno = node.lineno
        if isinstance(node, ast.Raise):
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                if node.exc.func.id == "RuntimeError":
                    if exists_lineno is not None and node.lineno > exists_lineno:
                        runtime_error_after_exists = True
    if exists_lineno is None:
        raise RuntimeError("main must call OUTPUT_DIR.exists().")
    if runtime_error_after_exists is not True:
        raise RuntimeError("main must raise RuntimeError when OUTPUT_DIR already exists.")
    if run_capture_lineno is None:
        raise RuntimeError("main must call _run_capture().")
    if mkdir_lineno is None:
        raise RuntimeError("main must call OUTPUT_DIR.mkdir().")
    if not (exists_lineno < run_capture_lineno < mkdir_lineno):
        raise RuntimeError(
            "main must order OUTPUT_DIR.exists(), _run_capture(), OUTPUT_DIR.mkdir()."
        )


def _assert_runtime_expectations_contract(tree) -> None:
    runtime_node = _function_node(tree, "_validate_runtime_expectations")
    if runtime_node is None:
        raise RuntimeError("_validate_runtime_expectations is missing.")
    if _function_node(tree, "_require_zero") is not None:
        raise RuntimeError("_require_zero must not remain in this diagnostic.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_require_zero":
                raise RuntimeError("Diagnostic must not call _require_zero.")
    required_summary3_fields = (
        "selected_candidate_present",
        "selected_buyer_count",
        "selected_seller_count",
        "selected_nonparticipating_count",
        "selected_trade_scope_count",
        "selected_total_G",
        "selected_total_R",
        "selected_surplus",
    )
    seen_summary3_fields: set[str] = set()
    for node in ast.walk(runtime_node):
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "summary3":
                if isinstance(node.slice, ast.Constant) and type(node.slice.value) is str:
                    seen_summary3_fields.add(node.slice.value)
    missing_fields = set(required_summary3_fields) - seen_summary3_fields
    if len(missing_fields) != 0:
        raise RuntimeError(
            "_validate_runtime_expectations must reference shift 3 summary fields "
            f"{sorted(missing_fields)!r}."
        )
    calls_finite_helper = False
    for node in ast.walk(runtime_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_assert_finite_numeric_economic_value":
                calls_finite_helper = True
    if calls_finite_helper is not True:
        raise RuntimeError(
            "_validate_runtime_expectations must validate selected economics via "
            "_assert_finite_numeric_economic_value."
        )


def _tuple_constant_strings(tree, name: str) -> list[str]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if name not in targets or not isinstance(node.value, ast.Tuple):
            continue
        values = []
        for element in node.value.elts:
            if isinstance(element, ast.Constant) and type(element.value) is str:
                values.append(element.value)
        return values
    raise RuntimeError(f"Tuple constant {name} is missing.")


def _assert_alignment_sort_contract(tree) -> None:
    visit_columns = _tuple_constant_strings(tree, "CANDIDATE_VISIT_COLUMNS")
    for column_name in (
        "vehicle_id",
        "arrival_tiebreaker",
        "aligned_sort_arrival_timestep",
        "baseline_alignment_sort_key_text",
    ):
        if column_name not in visit_columns:
            raise RuntimeError(f"Candidate Visit CSV column {column_name!r} is missing.")
    summary_columns = _tuple_constant_strings(tree, "NODE_SUMMARY_COLUMNS")
    for column_name in (
        "reconstructed_sort_order",
        "formal_candidate_order_matches_sort_key",
    ):
        if column_name not in summary_columns:
            raise RuntimeError(f"Node summary CSV column {column_name!r} is missing.")
    sort_key_function = _function_node(tree, "_baseline_alignment_sort_key")
    if sort_key_function is None:
        raise RuntimeError("_baseline_alignment_sort_key is missing.")
    returned_names = None
    for node in ast.walk(sort_key_function):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
            returned_names = [
                element.id for element in node.value.elts if isinstance(element, ast.Name)
            ]
    if returned_names != [
        "aligned_sort_arrival_timestep",
        "arrival_tiebreaker",
        "vehicle_id",
    ]:
        raise RuntimeError(
            "Alignment sort key order must be aligned arrival, arrival_tiebreaker, vehicle_id."
        )
    snapshot_function = _function_node(tree, "_snapshot_alignment_fields")
    if snapshot_function is None:
        raise RuntimeError("_snapshot_alignment_fields is missing.")
    snapshot_gets = set()
    for node in ast.walk(snapshot_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "get" and len(node.args) == 1:
                if isinstance(node.args[0], ast.Constant) and type(node.args[0].value) is str:
                    snapshot_gets.add(node.args[0].value)
    if "vehicle_id" not in snapshot_gets or "arrival_tiebreaker" not in snapshot_gets:
        raise RuntimeError("Collector snapshot must supply vehicle_id and arrival_tiebreaker.")
    order_function = _function_node(tree, "_assert_candidate_order_matches_alignment_sort")
    if order_function is None:
        raise RuntimeError("_assert_candidate_order_matches_alignment_sort is missing.")
    uses_sorted = False
    raises_on_mismatch = False
    for node in ast.walk(order_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sorted":
            uses_sorted = True
        if isinstance(node, ast.Raise):
            raises_on_mismatch = True
    if uses_sorted is not True or raises_on_mismatch is not True:
        raise RuntimeError("Formal Candidate order must be rebuilt from the alignment sort key.")
    review_function = _function_node(tree, "_build_review")
    if review_function is None:
        raise RuntimeError("_build_review is missing.")
    if "detail_cause" not in [arg.arg for arg in review_function.args.args]:
        raise RuntimeError("review must receive detail_cause.")
    classifier = _function_node(tree, "_classify_candidate_order_divergence")
    if classifier is None:
        raise RuntimeError("_classify_candidate_order_divergence is missing.")
    returned_causes = set()
    for node in ast.walk(classifier):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
            if len(node.value.elts) >= 1 and isinstance(node.value.elts[0], ast.Constant):
                if type(node.value.elts[0].value) is str:
                    returned_causes.add(node.value.elts[0].value)
    if "arrival_tiebreaker_assignment_divergence" not in returned_causes:
        raise RuntimeError("detail_cause arrival_tiebreaker_assignment_divergence is missing.")
    cause_constants = set()
    for node in ast.walk(classifier):
        if isinstance(node, ast.Constant) and type(node.value) is str:
            cause_constants.add(node.value)
    for cause_name in (
        "vehicle_id_divergence",
        "sort_order_contract_violation",
        "candidate_visit_order_divergence_unresolved",
    ):
        if cause_name not in cause_constants and not any(
            cause_name in value for value in cause_constants
        ):
            raise RuntimeError(f"detail_cause {cause_name!r} is missing.")


def validate_static_contract() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    if SHIFT0_CAPTURE_TIMESTEP != 602 or SHIFT3_CAPTURE_TIMESTEP != 605:
        raise RuntimeError("Capture timesteps must be 602 and 605.")
    if ALIGNED_TIMESTEP != 602:
        raise RuntimeError("Aligned timestep must be 602.")
    if TARGET_NODE_NAME != "northeast_intersection":
        raise RuntimeError("Target node must be northeast_intersection.")
    if TARGET_BUYER_VISIT_KEY != ("veh_wn_en_base_041", 2):
        raise RuntimeError("Target buyer visit key is wrong.")
    module_strings = _module_level_string_constants(tree)
    expected_output_names = {
        "NODE_SUMMARY_CSV": "shift_0_3_t602_t605_node_summary.csv",
        "CANDIDATE_VISITS_CSV": "shift_0_3_t602_t605_candidate_visits.csv",
        "CONSIDERED_CANDIDATES_CSV": "shift_0_3_t602_t605_considered_candidates.csv",
        "REVIEW_TXT": "shift_0_3_t602_t605_first_divergence_review.txt",
    }
    for constant_name, expected_value in expected_output_names.items():
        if module_strings.get(constant_name) != expected_value:
            raise RuntimeError(
                f"Module constant {constant_name!r} must equal {expected_value!r}."
            )
    driver = _function_node(tree, "wrapped_driver")
    if driver is None:
        raise RuntimeError("wrapped_driver is missing.")
    if _call_count(driver, "GATE", "original_driver") != 1:
        raise RuntimeError("wrapped_driver must call original_driver once.")
    saved = _function_node(tree, "_saved_columns")
    if saved is None:
        raise RuntimeError("_saved_columns is missing.")
    required_attrs = {
        "node_candidate_selection_results",
        "node_economic_evaluation_results",
        "node_trade_rank_results",
        "node_candidate_set_results",
        "node_selection_results",
        "fork_result",
        "collector",
        "candidate_visits",
    }
    seen_attrs = set()
    for node in ast.walk(saved):
        if isinstance(node, ast.Attribute):
            seen_attrs.add(node.attr)
    capture = _function_node(tree, "_capture_decision")
    if capture is None:
        raise RuntimeError("_capture_decision is missing.")
    for node in ast.walk(capture):
        if isinstance(node, ast.Attribute):
            seen_attrs.add(node.attr)
    missing = required_attrs - seen_attrs
    if len(missing) != 0:
        raise RuntimeError(f"Atomic chain attributes missing: {sorted(missing)!r}.")
    selection_fields = _function_node(tree, "_selection_fields")
    if selection_fields is None:
        raise RuntimeError("_selection_fields is missing.")
    _assert_selection_fields_none_branch(selection_fields)
    _assert_runtime_expectations_contract(tree)
    _assert_alignment_sort_contract(tree)
    main_node = _function_node(tree, "main")
    if main_node is None:
        raise RuntimeError("main is missing.")
    _main_output_dir_contract(main_node)
    static_node = _function_node(tree, "validate_static_contract")
    if static_node is None:
        raise RuntimeError("validate_static_contract is missing.")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir"):
                raise RuntimeError("Static validation must not simulate or mkdir.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("install_hooks", "main", "_run_capture"):
                raise RuntimeError("Static validation must not install hooks or run simulation.")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "uxsim.order_control_tvt_mp_research_output":
                raise RuntimeError("Diagnostic must not import research output.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id in ("shift0_trial", "shift_trial"):
                    raise RuntimeError("Diagnostic must not call trial main.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "build_tvt_mp_research_output":
                raise RuntimeError("Diagnostic must not build research output.")


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
        print("Static contract validation passed.", file=sys.stderr)
        return 0
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    original_limit = sys.getrecursionlimit()
    try:
        if original_limit < shift0_trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(shift0_trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world0 = _prepare_shift0_world()
        shift0 = _run_capture(SHIFT0_DEPARTURE_SHIFT, SHIFT0_CAPTURE_TIMESTEP, world0)
        _reset_gate()
        restore_hooks()
        world3 = _prepare_shift3_world()
        shift3 = _run_capture(SHIFT3_DEPARTURE_SHIFT, SHIFT3_CAPTURE_TIMESTEP, world3)
        _validate_runtime_expectations(shift0, shift3)
        label, notes, detail_cause = _first_divergence(shift0, shift3)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_csv(OUTPUT_DIR / NODE_SUMMARY_CSV, NODE_SUMMARY_COLUMNS, [shift0["summary"], shift3["summary"]])
        _write_csv(
            OUTPUT_DIR / CANDIDATE_VISITS_CSV,
            CANDIDATE_VISIT_COLUMNS,
            shift0["candidate_visits"] + shift3["candidate_visits"],
        )
        _write_csv(
            OUTPUT_DIR / CONSIDERED_CANDIDATES_CSV,
            CONSIDERED_COLUMNS,
            shift0["considered"] + shift3["considered"],
        )
        (OUTPUT_DIR / REVIEW_TXT).write_text(
            _build_review(shift0, shift3, label, notes, detail_cause),
            encoding="utf-8",
        )
        print(f"first_divergence_layer: {label}")
        print(f"output directory: {OUTPUT_DIR}")
        return 0
    finally:
        restore_hooks()
        sys.setrecursionlimit(original_limit)


if __name__ == "__main__":
    raise SystemExit(main())
