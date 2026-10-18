"""
Post-fix audit of seven multiple-buyer TVT-MP transactions.

Replays the extended-south-pulse two-cross trial once. At seven decision
keys only, reads the saved driver result: baseline arrival A from the
fork collector, economics from the selected candidate, the four official
ranks described below, right-of-entry from the saved node selection
result, and FIFO pass/fail counts for that decision's concrete candidates.

The four ranks are not substitutes for one another.

- baseline_local_rank is the pre-trade local rank. It is the 1-based
  position in the saved candidate_visits order. That order is not sorted
  again.
- post_trade_local_rank is the post-trade local rank. It is
  OrderControlTvtMpGeneralTradeRankResult.assigned_rank for the same
  candidate Visit set.
- assigned_rank is the Node-continuous candidate rank stored on the real
  World's OrderControlTvtNodeRankState. It is the same meaning as
  ledger_assigned_rank on a buyer or seller establishment record.
- actual_node_passage_rank is the Node-continuous actual passage rank
  stored on OrderControlTvtMpActualNodePassageHistoryRegistry. A visit
  still unobserved at evaluation end stays blank. It is not filled with 0.

binding_sequence_auxiliary_rank is only the position on the fully
constrained binding sequence used by candidate local virtual calculation.
It is not a before/after trade rank and not a Node-continuous rank.

After the same simulation, actual passage and ex-post fields are read
from the in-memory research-output bundle. The two Node-continuous ranks
are read from the same real World, not from candidate_binding_rank.
This script does not read an existing CSV to fill those fields, does not
write the research-output CSV set, and does not keep scan events, motion
traces, or non-target decisions.

The same T=35 east_intersection driver result also supplies one
all-candidate audit. Every concrete buyer candidate at that decision is
matched across the saved stages by buyer VisitKeys, node name, and
decision timestep. Other decisions are not expanded.

A fourth CSV lists, for each selected party whose Node-continuous
assigned rank and actual passage rank both exist and differ, the nearby
visits from that Node's rank ledger and actual passage history. It does
not change the three transaction CSVs.

Two further CSVs describe those same context visits. One timeline keeps
baseline arrival A separate from the real-world node arrival timestep.
One physical trace records, for real-world timesteps 324 through 334
only, the passage judgment production already made. That window is a
limited diagnostic for one known rank swap. It is not a general contract,
and it is not derived from arrival time. Visit selection still comes
from the mismatch context after the simulation. This script does not
keep motion traces.
"""

from __future__ import annotations

import ast
import csv
import json
import sys
from dataclasses import fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import numpy as np

import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.order_control_tvt_mp_physical_transfer as physical_transfer_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualNodePassageRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpTradeExPostEvaluationStatus,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.order_control_tvt_mp_atomic_apply import (
    OrderControlTvtMpTradeEstablishmentLogRecord,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
    OrderControlTvtMpCandidateTrafficObservationRecord,
    OrderControlTvtMpCandidateUnresolvedReason,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionStatus,
    OrderControlTvtNodeMpCandidateSelectionResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpCandidateEconomicInfeasibilityReason,
    OrderControlTvtMpSellerEconomicRecord,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtNodeMpFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpBuyerPaymentRecord,
    OrderControlTvtMpPaymentAndCompensationStatus,
    OrderControlTvtMpSellerCompensationRecord,
    OrderControlTvtNodeMpPaymentAndCompensationResult,
)
from uxsim.order_control_tvt_mp_research_output import (
    OrderControlTvtMpResearchOutputTransactionRow,
    OrderControlTvtMpResearchOutputVisitRow,
    build_tvt_mp_research_output,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
)

import run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_trial as extended_trial


OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_seed_1_post_fix_multiple_buyer_"
        "transaction_diagnostic"
    )
)
SUMMARY_CSV_NAME = "multiple_buyer_transaction_summary.csv"
PARTIES_CSV_NAME = "multiple_buyer_transaction_parties.csv"
EAST_T35_AUDIT_CSV_NAME = "east_t35_all_candidate_audit.csv"
NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_CSV_NAME = (
    "node_continuous_rank_mismatch_context.csv"
)
NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_CSV_NAME = (
    "node_continuous_rank_mismatch_vehicle_timeline.csv"
)
NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_CSV_NAME = (
    "node_continuous_rank_mismatch_physical_trace.csv"
)
OUTPUT_FILE_NAMES = (
    SUMMARY_CSV_NAME,
    PARTIES_CSV_NAME,
    EAST_T35_AUDIT_CSV_NAME,
    NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_CSV_NAME,
    NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_CSV_NAME,
    NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_CSV_NAME,
)
CONTEXT_RANK_PADDING = 2
# Limited diagnostic window for one known west_intersection rank swap.
# The swap is centered on passage times that were already observed. This
# window is not a general production contract. Do not derive it from an
# arrival timestep, and do not use it to choose which Visit is traced.
PHYSICAL_TRACE_TIMESTEP_START = 324
PHYSICAL_TRACE_TIMESTEP_END = 334

EAST_NODE = "east_intersection"
WEST_NODE = "west_intersection"
EAST_T35_AUDIT_KEY = (EAST_NODE, 35)
EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT = 7
EAST_T35_EXPECTED_FIFO_PASSED_COUNT = 7
EAST_T35_EXPECTED_FIFO_FAILED_COUNT = 0
EXCLUSION_STAGE_FIFO_FAILED = "fifo_failed"
EXCLUSION_STAGE_LOCAL_UNRESOLVED = "local_virtual_calculation_unresolved"
EXCLUSION_STAGE_ECONOMICALLY_INFEASIBLE = "economically_infeasible"
EXCLUSION_STAGE_FEASIBLE_NOT_SELECTED = "economically_feasible_but_not_selected"
EXCLUSION_STAGE_SELECTED = "selected"

TARGET_DECISION_KEYS = (
    (EAST_NODE, 35),
    (WEST_NODE, 310),
    (WEST_NODE, 316),
    (WEST_NODE, 331),
    (WEST_NODE, 338),
    (WEST_NODE, 344),
    (EAST_NODE, 582),
)
EXPECTED_BUYER_SELLER_COUNTS = {
    (EAST_NODE, 35): (2, 2),
    (WEST_NODE, 310): (2, 1),
    (WEST_NODE, 316): (3, 1),
    (WEST_NODE, 331): (3, 1),
    (WEST_NODE, 338): (2, 1),
    (WEST_NODE, 344): (4, 1),
    (EAST_NODE, 582): (3, 1),
}
T582_KEY = (EAST_NODE, 582)
T582_EXPECTED_UNOBSERVED_PARTIES = (
    ("buyer", ("veh_es_83", 1)),
    ("seller", ("veh_en_74", 1)),
)
EVALUATION_UNAVAILABLE = (
    OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE.value
)
ACTUAL_UNOBSERVED = (
    OrderControlTvtMpActualPassageObservationStatus
    .ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    .value
)

SUMMARY_COLUMNS = (
    "decision_timestep",
    "node_name",
    "candidate_identity",
    "right_of_entry_visit_key",
    "right_of_entry_vehicle_name",
    "right_of_entry_baseline_arrival_timestep",
    "right_of_entry_baseline_rank",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "buyer_visit_keys",
    "seller_visit_keys",
    "nonparticipating_visit_keys",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "total_G",
    "total_R",
    "surplus",
    "economically_feasible",
    "infeasibility_reasons",
    "selected",
    "fifo_inspection_passed",
    "fifo_violation_count",
    "trade_ex_post_evaluation_status",
    "actual_evaluation_available",
    "t582_unavailable_contract_consistent",
    "concrete_candidate_count",
    "fifo_passed_candidate_count",
    "fifo_failed_candidate_count",
    "selected_candidate_was_fifo_passed",
    "fifo_candidate_pass_fail",
    "right_of_entry_is_selected_seller",
)
PARTY_COLUMNS = (
    "decision_timestep",
    "node_name",
    "candidate_identity",
    "visit_key",
    "vehicle_name",
    "visit_id",
    "role",
    "is_right_of_entry_holder",
    "inlink_name",
    "formal_route_next_link_name",
    "baseline_arrival_timestep",
    "arrival_tiebreaker",
    "baseline_local_rank",
    "post_trade_local_rank",
    "assigned_rank",
    "actual_node_passage_rank",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "predicted_observation_status",
    "actual_observation_status",
    "declared_vot_per_second",
    "true_vot_per_second",
    "buyer_value_G_b",
    "seller_required_compensation_R_s",
    "payment_P_b",
    "compensation_C_s",
    "realized_gain",
    "realized_delay_loss",
    "satisfaction_status",
    "binding_sequence_auxiliary_rank",
    "same_inlink_fifo_predecessor_visit_keys",
    "same_inlink_fifo_successor_visit_keys",
    "same_inlink_fifo_preserved",
)
EAST_T35_AUDIT_COLUMNS = (
    "decision_timestep",
    "node_name",
    "candidate_identity",
    "candidate_index_in_stored_order",
    "buyer_visit_keys",
    "seller_visit_keys",
    "nonparticipating_visit_keys",
    "trade_scope_visit_keys",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "fifo_inspection_passed",
    "local_virtual_calculation_resolved",
    "local_virtual_calculation_stop_reason",
    "economically_evaluated",
    "total_G",
    "total_R",
    "surplus",
    "economically_feasible",
    "infeasibility_reasons",
    "selected",
    "selection_exclusion_stage",
    "selection_exclusion_reason",
    "visit_key",
    "vehicle_name",
    "visit_id",
    "role",
    "is_right_of_entry_holder",
    "inlink_name",
    "formal_route_next_link_name",
    "baseline_arrival_timestep",
    "arrival_tiebreaker",
    "baseline_local_rank",
    "post_trade_local_rank",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "predicted_time_difference_timesteps",
    "declared_vot_per_second",
    "buyer_value_G_b",
    "seller_required_compensation_R_s",
    "same_inlink_fifo_preserved",
)
NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_COLUMNS = (
    "mismatch_decision_timestep",
    "mismatch_node_name",
    "mismatch_visit_key",
    "mismatch_assigned_rank",
    "mismatch_actual_node_passage_rank",
    "context_visit_key",
    "vehicle_name",
    "visit_id",
    "assigned_rank",
    "actual_node_passage_rank",
    "actual_passage_timestep",
    "formal_route_next_link_name",
    "actual_route_next_link_name",
    "inlink_name",
    "is_mismatch_visit",
    "is_between_mismatch_ranks",
    "rank_relation_note",
)
NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_COLUMNS = (
    "mismatch_decision_timestep",
    "node_name",
    "mismatch_visit_key",
    "context_visit_key",
    "vehicle_name",
    "visit_id",
    "is_mismatch_visit",
    "is_between_mismatch_ranks",
    "role_at_mismatch_transaction",
    "inlink_name",
    "formal_route_next_link_name",
    "actual_route_next_link_name",
    "baseline_arrival_timestep",
    "actual_node_arrival_timestep",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "baseline_local_rank",
    "post_trade_local_rank",
    "assigned_rank",
    "actual_node_passage_rank",
    "predicted_observation_status",
    "actual_observation_status",
    "timeline_data_status",
    "timeline_data_note",
)
NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_COLUMNS = (
    "mismatch_decision_timestep",
    "node_name",
    "mismatch_visit_key",
    "real_world_timestep",
    "scan_sequence_index",
    "context_visit_key",
    "vehicle_name",
    "visit_id",
    "assigned_rank",
    "actual_node_passage_rank",
    "inlink_name",
    "intended_outlink_name",
    "actual_node_arrival_timestep",
    "was_arrived_at_node",
    "was_already_passed_before_scan",
    "was_inlink_physical_head",
    "clearance_required_timesteps",
    "last_order_control_inlink_name",
    "last_order_control_entry_timestep",
    "clearance_satisfied",
    "inlink_capacity_out_remain_before",
    "inlink_outflow_capacity_satisfied",
    "node_flow_capacity_remain_before",
    "node_flow_capacity_satisfied",
    "outlink_capacity_in_remain_before",
    "outlink_inflow_capacity_satisfied",
    "outlink_entrance_space_available",
    "outlink_entrance_space_detail",
    "first_blocking_reason",
    "action",
    "passed_this_scan",
    "temporary_skipped",
    "clearance_stopped_node_scan",
    "actual_passage_timestep_if_passed",
    "scan_note",
)
# Names below follow the order production uses for one confirmed visit:
# arrived, inlink physical head, clearance, inlink outflow, node flow,
# outlink inflow, outlink entrance space, then pass. The later names are
# outcomes of that scan, not extra checks inserted into the order.
PHYSICAL_TRACE_REASON_ORDER = (
    "not_arrived",
    "not_inlink_physical_head",
    "clearance_not_satisfied",
    "inlink_outflow_capacity_insufficient",
    "node_flow_capacity_insufficient",
    "outlink_inflow_capacity_insufficient",
    "outlink_entrance_space_insufficient",
    "none_passed",
    "not_scanned_after_clearance_stop",
    "already_passed",
    "not_present_at_target_node",
    "route_unavailable",
)
PHYSICAL_TRACE_ACTIONS = (
    "passed",
    "temporary_skip",
    "clearance_stop",
    "not_scanned_after_clearance_stop",
    "already_passed",
    "not_yet_arrived",
    "not_present",
)


class _DiagnosticGate:
    def __init__(self) -> None:
        self.original_run_tvt_mp_driver = None
        self.original_record_order_control_node_arrival = None
        self.original_transfer_tvt_mp_passage_attempts = None
        self.original_inlink_physical_head_should_skip = None
        self.original_first_ordinary_physical_shortage = None
        self.original_order_control_clearance_blocks_passage = None
        self.original_transfer_one_vehicle_between_links = None
        self.installed = False
        self.real_world = None
        self.decisions: dict[tuple[str, int], dict] = {}
        self.east_t35_audit_rows: list[dict] = []
        self.node_continuous_rank_mismatch_context_rows: list[dict] = []
        self.vehicle_timeline_rows: list[dict] = []
        self.physical_trace_rows: list[dict] = []
        self.actual_node_arrivals: dict[tuple[str, str, int], int] = {}
        self.physical_trace_events: list[dict] = []
        self.physical_trace_active = None


GATE = _DiagnosticGate()


def _visit_text(visit_key: tuple[str, int]) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _join_visit_keys(visit_keys) -> str:
    return "|".join(_visit_text(visit_key) for visit_key in visit_keys)


def _plain_visit_key(visit_key) -> tuple[str, int]:
    if (
        not isinstance(visit_key, tuple)
        or len(visit_key) != 2
        or not isinstance(visit_key[0], str)
        or visit_key[0] == ""
        or type(visit_key[1]) is not int
        or visit_key[1] < 1
    ):
        raise RuntimeError(f"VisitKey is not a (vehicle_name, visit_id) pair: {visit_key!r}.")
    return (visit_key[0], visit_key[1])


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if value is True:
        return "True"
    if value is False:
        return "False"
    return str(value)


def _decision_label(node_name: str, timestep: int) -> str:
    return f"{node_name} T={timestep}"


def _require_node_result(results, node_name: str, timestep: int, stage_name: str):
    matched = None
    match_count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        match_count = match_count + 1
        matched = result
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {stage_name} has "
            f"{match_count} results for the target node."
        )
    return matched


def _saved_driver_columns(atomic):
    """Walk saved attributes only. Does not call production helpers."""
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
        raise RuntimeError(
            "Saved alignment fork_result is not OrderControlBaselineForkResult: "
            f"{type(fork_result).__name__}."
        )
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError(
            "Saved fork_result.collector is not OrderControlBaselineCollector: "
            f"{type(collector).__name__}."
        )
    return {
        "payment_nodes": payment_set.node_payment_and_compensation_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "fifo_nodes": fifo_set.node_fifo_inspection_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "concrete_nodes": concrete_set.node_concrete_buyer_candidate_set_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
    }


def _baseline_local_ranks(candidate_visits, node_name: str, timestep: int):
    """1-based baseline_local_rank in the saved candidate_visits order.

    This is the same contract as
    OrderControlTvtMp atomic apply `_baseline_local_rank`: walk the saved
    tuple from front to back, do not sort it, and stop when one VisitKey
    matches zero times or more than once. The returned order is that saved
    order. Rank numbers are checked separately for 1..count.
    """
    ordered_visit_keys = []
    ranks = {}
    position = 0
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits entry "
                f"is {type(candidate_visit).__name__}."
            )
        position = position + 1
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits repeats "
                f"{_visit_text(visit_key)}. baseline_local_rank is not unique."
            )
        ordered_visit_keys.append(visit_key)
        ranks[visit_key] = position
    return tuple(ordered_visit_keys), ranks


def _require_python_int_rank(rank_value, rank_name: str, node_name: str, timestep: int, visit_key) -> int:
    if type(rank_value) is not int:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {rank_name} for "
            f"{_visit_text(visit_key)} must be a Python int, not bool; "
            f"got {rank_value!r}."
        )
    return rank_value


def _require_ranks_are_one_through_count(
    ranks_by_visit_key: dict,
    visit_count: int,
    rank_name: str,
    node_name: str,
    timestep: int,
) -> None:
    """Check that rank numbers are exactly 1..count, without reordering visits."""
    seen = []
    index = 0
    while index < visit_count:
        seen.append(False)
        index = index + 1
    for visit_key, rank_value in ranks_by_visit_key.items():
        checked = _require_python_int_rank(
            rank_value, rank_name, node_name, timestep, visit_key
        )
        if checked < 1 or checked > visit_count:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {rank_name} for "
                f"{_visit_text(visit_key)} is {checked}, not inside 1..{visit_count}."
            )
        slot = checked - 1
        if seen[slot] is True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {rank_name} {checked} "
                "is duplicated inside the candidate Visit set."
            )
        seen[slot] = True
    index = 0
    while index < visit_count:
        if seen[index] is not True:
            missing = index + 1
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {rank_name} is missing "
                f"{missing}. Ranks must be continuous from 1 through {visit_count}."
            )
        index = index + 1


def _require_same_population_and_continuous_local_ranks(
    ordered_visit_keys,
    baseline_local_ranks: dict,
    post_trade_local_ranks: dict,
    node_name: str,
    timestep: int,
    population_label: str,
) -> None:
    """B and C local ranks share one candidate Visit population and one scale.

    Individual visits may change rank. The two columns must still name the
    same visits and both use 1..count with no gaps and no duplicates.
    """
    baseline_keys = set(baseline_local_ranks)
    post_trade_keys = set(post_trade_local_ranks)
    saved_keys = set(ordered_visit_keys)
    if baseline_keys != saved_keys or post_trade_keys != saved_keys:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {population_label} "
            "baseline_local_rank and post_trade_local_rank do not share the "
            "saved candidate Visit set."
        )
    if len(ordered_visit_keys) != len(saved_keys):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {population_label} "
            "saved candidate Visit order repeats a VisitKey."
        )
    visit_count = len(ordered_visit_keys)
    _require_ranks_are_one_through_count(
        baseline_local_ranks,
        visit_count,
        "baseline_local_rank",
        node_name,
        timestep,
    )
    _require_ranks_are_one_through_count(
        post_trade_local_ranks,
        visit_count,
        "post_trade_local_rank",
        node_name,
        timestep,
    )


def _post_trade_local_ranks(
    trade_result,
    ordered_visit_keys,
    node_name: str,
    timestep: int,
    population_label: str,
) -> dict:
    """post_trade_local_rank from one general trade rank result.

    Same contract as atomic apply `_post_trade_local_rank`: read
    assigned_rank(visit_key), stop when the VisitKey is absent, and stop
    when the value is not a Python int.
    """
    if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {population_label} trade "
            f"rank result is {type(trade_result).__name__}."
        )
    ranks = {}
    for visit_key in ordered_visit_keys:
        try:
            rank_value = trade_result.assigned_rank(visit_key)
        except ValueError as error:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {population_label} "
                f"has no post_trade_local_rank for {_visit_text(visit_key)}."
            ) from error
        ranks[visit_key] = _require_python_int_rank(
            rank_value, "post_trade_local_rank", node_name, timestep, visit_key
        )
    return ranks


def _establishment_record(world, timestep: int, node_name: str, visit_key):
    """Buyer or seller establishment row for this decision, or None.

    The walk uses the live Vehicle log already written by atomic apply.
    It does not search other vehicles or other decisions.
    """
    vehicle_name = visit_key[0]
    if vehicle_name not in world.VEHICLES:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {vehicle_name} is not on the real World."
        )
    vehicle = world.VEHICLES[vehicle_name]
    found = None
    for record in vehicle.order_exchange_log:
        if not isinstance(record, OrderControlTvtMpTradeEstablishmentLogRecord):
            continue
        if record.tvt_decision_timestep != timestep or record.node_name != node_name:
            continue
        if _plain_visit_key(record.visit_key) != visit_key:
            continue
        if found is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate establishment "
                f"record for {_visit_text(visit_key)}."
            )
        found = record
    return found


def _establishment_baseline_rank(world, timestep: int, node_name: str, visit_key):
    found = _establishment_record(world, timestep, node_name, visit_key)
    if found is None:
        return None
    _require_python_int_rank(
        found.baseline_local_rank,
        "establishment baseline_local_rank",
        node_name,
        timestep,
        visit_key,
    )
    return found.baseline_local_rank


def _require_rank_change_matches_local_ranks(
    establishment,
    baseline_local_rank: int,
    post_trade_local_rank: int,
    node_name: str,
    timestep: int,
    visit_key,
) -> None:
    """Use rank_change only when the establishment row already stores it."""
    rank_change = establishment.rank_change
    _require_python_int_rank(
        rank_change, "rank_change", node_name, timestep, visit_key
    )
    expected = baseline_local_rank - post_trade_local_rank
    if rank_change != expected:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rank_change {rank_change} "
            f"for {_visit_text(visit_key)} is not baseline_local_rank "
            f"{baseline_local_rank} minus post_trade_local_rank "
            f"{post_trade_local_rank}."
        )


def _require_ledger_assigned_rank(world, node_name: str, timestep: int, visit_key) -> int:
    """Node-continuous candidate rank from the real World rank ledger."""
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict) or node_name not in states:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: real World has no "
            f"OrderControlTvtNodeRankState for {node_name}."
        )
    rank_state = states[node_name]
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rank state is "
            f"{type(rank_state).__name__}."
        )
    if rank_state.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rank state node_name "
            f"is {rank_state.node_name!r}."
        )
    assigned_rank = rank_state.assigned_rank(visit_key)
    if assigned_rank is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected party "
            f"{_visit_text(visit_key)} has no ledger assigned_rank."
        )
    checked = _require_python_int_rank(
        assigned_rank, "assigned_rank", node_name, timestep, visit_key
    )
    if checked < 1:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: assigned_rank for "
            f"{_visit_text(visit_key)} is {checked}."
        )
    return checked


def _actual_passage_records_in_stored_order(world, node_name: str) -> tuple:
    """Read one Node's actual passage history in its stored order.

    The stored tuple is not sorted and the rank numbers are not rebuilt.
    The existing contract is that stored position 1, 2, 3, ... matches
    actual_node_passage_rank. A repeated VisitKey or a gap stops the run.
    """
    registry = getattr(
        world, "order_control_tvt_mp_actual_node_passage_history_registry", None
    )
    if not isinstance(registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError(
            f"Node {node_name}: actual passage history registry is "
            f"{type(registry).__name__}."
        )
    stored_records = registry.records_by_node_name.get(node_name, ())
    if not isinstance(stored_records, tuple):
        raise RuntimeError(
            f"Node {node_name}: actual passage history is "
            f"{type(stored_records).__name__}, not the stored tuple."
        )
    checked_records = []
    seen_visit_keys = {}
    expected_rank = 1
    for record in stored_records:
        if not isinstance(record, OrderControlTvtMpActualNodePassageRecord):
            raise RuntimeError(
                f"Node {node_name}: actual passage history entry is "
                f"{type(record).__name__}."
            )
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name}: actual passage history repeats "
                f"{_visit_text(visit_key)}."
            )
        rank_value = record.actual_node_passage_rank
        if type(rank_value) is not int:
            raise RuntimeError(
                f"Node {node_name}: actual_node_passage_rank for "
                f"{_visit_text(visit_key)} must be a Python int, not bool; "
                f"got {rank_value!r}."
            )
        if rank_value < 1:
            raise RuntimeError(
                f"Node {node_name}: actual_node_passage_rank for "
                f"{_visit_text(visit_key)} is {rank_value}."
            )
        if rank_value != expected_rank:
            raise RuntimeError(
                f"Node {node_name}: stored actual_node_passage_rank {rank_value} "
                f"for {_visit_text(visit_key)} is not continuous position "
                f"{expected_rank}. Stored history order was not rearranged."
            )
        seen_visit_keys[visit_key] = True
        checked_records.append(record)
        expected_rank = expected_rank + 1
    return tuple(checked_records)


def _actual_passage_ranks_in_stored_order(world, node_name: str) -> dict:
    """Map VisitKey to actual_node_passage_rank without reordering history.

    A VisitKey absent from this map is unobserved and must stay None.
    Missing ranks are not filled from assigned_rank or from the binding sequence.
    """
    records = _actual_passage_records_in_stored_order(world, node_name)
    ranks = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        ranks[visit_key] = record.actual_node_passage_rank
    return ranks


def _collector_snapshot(collector, timestep: int, node_name: str, visit_key) -> dict:
    snapshot = collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
    if snapshot is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: collector has no baseline "
            f"snapshot for {_visit_text(visit_key)}."
        )
    arrival = snapshot["baseline_arrival_timestep"]
    if type(arrival) is not int:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: baseline_arrival_timestep for "
            f"{_visit_text(visit_key)} is {arrival!r}."
        )
    return snapshot


def _records_by_visit_key(records, node_name: str, timestep: int, record_name: str) -> dict:
    mapping = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {record_name} repeats "
                f"{_visit_text(visit_key)}."
            )
        mapping[visit_key] = record
    return mapping


def _require_same_visit_keys(left, right, node_name: str, timestep: int, label: str) -> None:
    if set(left) != set(right):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: VisitKey sets differ for {label}. "
            f"left={_join_visit_keys(sorted(left))} right={_join_visit_keys(sorted(right))}."
        )


def _candidate_identity(node_name: str, buyers_sorted) -> str:
    return node_name + "|" + _join_visit_keys(buyers_sorted)


def _match_selected_trade_and_fifo(
    selected_local,
    trade_node,
    fifo_node,
    node_name: str,
    timestep: int,
):
    concrete_set = selected_local.concrete_buyer_candidate_set
    if not isinstance(concrete_set, OrderControlTvtMpConcreteBuyerCandidateSet):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected concrete buyer set "
            f"is {type(concrete_set).__name__}."
        )
    matched_trade = None
    for trade_result in trade_node.candidate_trade_rank_results:
        if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade rank result is "
                f"{type(trade_result).__name__}."
            )
        if trade_result.concrete_buyer_candidate_set is concrete_set:
            if matched_trade is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: selected concrete set "
                    "matches two trade-rank results."
                )
            matched_trade = trade_result
    if matched_trade is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate has no "
            "saved general trade-rank result."
        )
    matched_fifo = None
    for fifo_result in fifo_node.candidate_fifo_inspection_results:
        if not isinstance(fifo_result, OrderControlTvtMpCandidateFifoInspectionResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result is "
                f"{type(fifo_result).__name__}."
            )
        if fifo_result.general_trade_rank_result is matched_trade:
            if matched_fifo is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: selected trade rank "
                    "matches two FIFO results."
                )
            matched_fifo = fifo_result
    if matched_fifo is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate has no "
            "saved FIFO inspection result."
        )
    return matched_trade, matched_fifo


def _fifo_candidate_summary(concrete_node, fifo_node, node_name: str, timestep: int) -> dict:
    concrete_sets = concrete_node.concrete_buyer_candidate_sets
    fifo_results = fifo_node.candidate_fifo_inspection_results
    if len(concrete_sets) != len(fifo_results):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: concrete candidate count "
            f"{len(concrete_sets)} does not match FIFO result count {len(fifo_results)}."
        )
    passed = 0
    failed = 0
    brief = []
    for index, fifo_result in enumerate(fifo_results):
        trade_result = fifo_result.general_trade_rank_result
        buyers_sorted = tuple(
            _plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted
        )
        if trade_result.concrete_buyer_candidate_set is not concrete_sets[index]:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result {index} is not "
                "the concrete candidate at the same index."
            )
        preserves = fifo_result.preserves_inlink_fifo
        if preserves is True:
            passed = passed + 1
        elif preserves is False:
            failed = failed + 1
        else:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: preserves_inlink_fifo is "
                f"{preserves!r}."
            )
        brief.append(
            {
                "candidate_identity": _candidate_identity(node_name, buyers_sorted),
                "preserves_inlink_fifo": preserves,
            }
        )
    return {
        "concrete_candidate_count": len(concrete_sets),
        "fifo_passed_candidate_count": passed,
        "fifo_failed_candidate_count": failed,
        "fifo_candidate_pass_fail": json.dumps(brief, separators=(",", ":")),
    }


def _resolve_baseline_rank(
    world,
    timestep: int,
    node_name: str,
    visit_key,
    role: str,
    candidate_visit_rank: int,
) -> int:
    establishment_rank = _establishment_baseline_rank(world, timestep, node_name, visit_key)
    if role == "buyer" or role == "seller":
        if establishment_rank is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "has no saved establishment baseline_local_rank."
            )
        if establishment_rank != candidate_visit_rank:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: establishment baseline rank "
                f"{establishment_rank} for {_visit_text(visit_key)} does not match "
                f"candidate_visits position {candidate_visit_rank}."
            )
        return establishment_rank
    if establishment_rank is not None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: nonparticipating "
            f"{_visit_text(visit_key)} has an establishment baseline rank."
        )
    return candidate_visit_rank


def _build_parties(
    world,
    timestep: int,
    node_name: str,
    candidate_identity: str,
    binding_visits,
    trade_result,
    economic_result,
    payment_node,
    traffic_by_key: dict,
    baseline_local_ranks: dict,
    post_trade_local_ranks: dict,
    collector,
    right_of_entry_key,
) -> list[dict]:
    buyer_records = _records_by_visit_key(
        economic_result.buyer_economic_records, node_name, timestep, "buyer_economic_records"
    )
    seller_records = _records_by_visit_key(
        economic_result.seller_economic_records, node_name, timestep, "seller_economic_records"
    )
    payment_by_key = _records_by_visit_key(
        payment_node.buyer_payment_records, node_name, timestep, "buyer_payment_records"
    )
    compensation_by_key = _records_by_visit_key(
        payment_node.seller_compensation_records,
        node_name,
        timestep,
        "seller_compensation_records",
    )
    buyers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted)
    sellers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.sellers_sorted)
    nonparticipating_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.nonparticipating_visits_sorted
    )
    trade_scope = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.trade_scope)
    _require_same_visit_keys(
        trade_scope,
        tuple(buyers_sorted) + tuple(sellers_sorted) + tuple(nonparticipating_sorted),
        node_name,
        timestep,
        "trade_scope versus role columns",
    )
    _require_same_visit_keys(
        buyers_sorted, tuple(buyer_records), node_name, timestep, "buyers versus buyer economics"
    )
    _require_same_visit_keys(
        sellers_sorted, tuple(seller_records), node_name, timestep, "sellers versus seller economics"
    )
    _require_same_visit_keys(
        buyers_sorted, tuple(payment_by_key), node_name, timestep, "buyers versus payments"
    )
    _require_same_visit_keys(
        sellers_sorted,
        tuple(compensation_by_key),
        node_name,
        timestep,
        "sellers versus compensations",
    )
    binding_keys = []
    parties = []
    for binding_visit in binding_visits:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: binding visit is "
                f"{type(binding_visit).__name__}."
            )
        if (
            binding_visit.binding_partition
            is not OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope binding visit "
                f"{binding_visit.visit_key!r} has partition {binding_visit.binding_partition!r}."
            )
        visit_key = _plain_visit_key(binding_visit.visit_key)
        binding_keys.append(visit_key)
        role = binding_visit.trade_role
        if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
            role_name = "buyer"
        elif role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
            role_name = "seller"
        elif role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
            role_name = "nonparticipating"
        else:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope visit "
                f"{_visit_text(visit_key)} has role {role!r}."
            )
        if visit_key not in baseline_local_ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "is missing from saved candidate_visits."
            )
        if visit_key not in post_trade_local_ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "is missing from the selected post_trade_local_rank map."
            )
        snapshot = _collector_snapshot(collector, timestep, node_name, visit_key)
        if snapshot["baseline_arrival_timestep"] != binding_visit.baseline_arrival_timestep:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector A for "
                f"{_visit_text(visit_key)} does not match the binding visit."
            )
        if snapshot["arrival_tiebreaker"] != binding_visit.arrival_tiebreaker:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector tiebreaker for "
                f"{_visit_text(visit_key)} does not match the binding visit."
            )
        if snapshot["vehicle_id"] != binding_visit.vehicle_id:
            raise RuntimeError(
                f"node_name={node_name!r}, decision_timestep={timestep}, "
                f"visit_key={_visit_text(visit_key)!r}: collector vehicle_id "
                f"{snapshot['vehicle_id']!r} does not match binding_visit.vehicle_id "
                f"{binding_visit.vehicle_id!r}."
            )
        if snapshot["inlink_name"] != binding_visit.inlink_name:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector inlink for "
                f"{_visit_text(visit_key)} does not match the binding visit."
            )
        observation = traffic_by_key.get(visit_key)
        if observation is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected candidate has no "
                f"traffic observation for {_visit_text(visit_key)}."
            )
        baseline_passage = observation.baseline_passage_timestep
        candidate_passage = observation.candidate_passage_timestep
        buyer_record = buyer_records.get(visit_key)
        seller_record = seller_records.get(visit_key)
        if role_name == "buyer":
            if buyer_record is None or seller_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer role does not match "
                    f"economic records for {_visit_text(visit_key)}."
                )
            if buyer_record.baseline_passage_timestep != baseline_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer baseline passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            if buyer_record.candidate_passage_timestep != candidate_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer candidate passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            declared_vot = buyer_record.declared_vot_per_second
            buyer_value = buyer_record.gross_time_value_G_b
            seller_compensation = None
            payment = payment_by_key[visit_key].payment_P_b
            compensation = None
        elif role_name == "seller":
            if seller_record is None or buyer_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller role does not match "
                    f"economic records for {_visit_text(visit_key)}."
                )
            if seller_record.baseline_passage_timestep != baseline_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller baseline passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            if seller_record.candidate_passage_timestep != candidate_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller candidate passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            declared_vot = seller_record.declared_vot_per_second
            buyer_value = None
            seller_compensation = seller_record.required_compensation_R_s
            payment = None
            compensation = compensation_by_key[visit_key].compensation_amount
        else:
            if buyer_record is not None or seller_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: nonparticipating "
                    f"{_visit_text(visit_key)} has an economic record."
                )
            declared_vot = None
            buyer_value = None
            seller_compensation = None
            payment = None
            compensation = None
        if role_name == "buyer" and buyer_value is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: buyer {_visit_text(visit_key)} "
                "is missing gross_time_value_G_b."
            )
        if role_name == "seller" and seller_compensation is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: seller {_visit_text(visit_key)} "
                "is missing required_compensation_R_s."
            )
        baseline_local_rank = _resolve_baseline_rank(
            world,
            timestep,
            node_name,
            visit_key,
            role_name,
            baseline_local_ranks[visit_key],
        )
        post_trade_local_rank = _require_python_int_rank(
            post_trade_local_ranks[visit_key],
            "post_trade_local_rank",
            node_name,
            timestep,
            visit_key,
        )
        establishment = _establishment_record(world, timestep, node_name, visit_key)
        if role_name == "buyer" or role_name == "seller":
            if establishment is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                    "has no saved establishment record."
                )
            establishment_post_trade = _require_python_int_rank(
                establishment.post_trade_local_rank,
                "establishment post_trade_local_rank",
                node_name,
                timestep,
                visit_key,
            )
            if establishment_post_trade != post_trade_local_rank:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: establishment "
                    f"post_trade_local_rank {establishment_post_trade} "
                    f"for {_visit_text(visit_key)} does not match the selected "
                    f"general trade rank {post_trade_local_rank}."
                )
            _require_rank_change_matches_local_ranks(
                establishment,
                baseline_local_rank,
                post_trade_local_rank,
                node_name,
                timestep,
                visit_key,
            )
        elif establishment is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: nonparticipating "
                f"{_visit_text(visit_key)} has an establishment record."
            )
        parties.append(
            {
                "decision_timestep": timestep,
                "node_name": node_name,
                "candidate_identity": candidate_identity,
                "visit_key": _visit_text(visit_key),
                "visit_key_tuple": visit_key,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "vehicle_id": binding_visit.vehicle_id,
                "role": role_name,
                "is_right_of_entry_holder": visit_key == right_of_entry_key,
                "inlink_name": binding_visit.inlink_name,
                "formal_route_next_link_name": binding_visit.route_next_link_name,
                "baseline_arrival_timestep": snapshot["baseline_arrival_timestep"],
                "arrival_tiebreaker": snapshot["arrival_tiebreaker"],
                "baseline_local_rank": baseline_local_rank,
                "post_trade_local_rank": post_trade_local_rank,
                "assigned_rank": None,
                "actual_node_passage_rank": None,
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_passage,
                "actual_passage_timestep": None,
                "predicted_observation_status": None,
                "actual_observation_status": None,
                "declared_vot_per_second": declared_vot,
                "true_vot_per_second": observation.true_vot_per_second,
                "buyer_value_G_b": buyer_value,
                "seller_required_compensation_R_s": seller_compensation,
                "payment_P_b": payment,
                "compensation_C_s": compensation,
                "realized_gain": None,
                "realized_delay_loss": None,
                "satisfaction_status": None,
                "binding_sequence_auxiliary_rank": binding_visit.binding_rank,
                "same_inlink_fifo_predecessor_visit_keys": "",
                "same_inlink_fifo_successor_visit_keys": "",
                "same_inlink_fifo_preserved": None,
            }
        )
    _require_same_visit_keys(
        binding_keys, trade_scope, node_name, timestep, "binding trade scope versus trade_scope"
    )
    _require_same_visit_keys(
        binding_keys, tuple(traffic_by_key), node_name, timestep, "binding trade scope versus observations"
    )
    binding_ranks = [party["binding_sequence_auxiliary_rank"] for party in parties]
    if len(binding_ranks) != len(set(binding_ranks)):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade-scope binding ranks are not unique."
        )
    baseline_ranks = [party["baseline_local_rank"] for party in parties]
    if len(baseline_ranks) != len(set(baseline_ranks)):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade-scope baseline_local_rank "
            "values are not unique."
        )
    post_trade_ranks = [party["post_trade_local_rank"] for party in parties]
    if len(post_trade_ranks) != len(set(post_trade_ranks)):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade-scope post_trade_local_rank "
            "values are not unique."
        )
    return parties


def _annotate_same_inlink_fifo(parties: list[dict]) -> int:
    grouped: dict[str, list[dict]] = {}
    for party in parties:
        grouped.setdefault(party["inlink_name"], []).append(party)
    violation_count = 0
    for inlink_parties in grouped.values():
        baseline_order = sorted(
            inlink_parties,
            key=lambda party: (
                party["baseline_local_rank"],
                party["baseline_arrival_timestep"],
                party["arrival_tiebreaker"],
                party["vehicle_id"],
                party["visit_key_tuple"],
            ),
        )
        candidate_position = {}
        candidate_order = sorted(
            inlink_parties,
            key=lambda party: (
                party["binding_sequence_auxiliary_rank"],
                party["visit_key_tuple"],
            ),
        )
        for index, party in enumerate(candidate_order):
            candidate_position[party["visit_key_tuple"]] = index
        baseline_position = {}
        for index, party in enumerate(baseline_order):
            baseline_position[party["visit_key_tuple"]] = index
        for index, party in enumerate(baseline_order):
            predecessors = baseline_order[:index]
            successors = baseline_order[index + 1 :]
            party["same_inlink_fifo_predecessor_visit_keys"] = _join_visit_keys(
                item["visit_key_tuple"] for item in predecessors
            )
            party["same_inlink_fifo_successor_visit_keys"] = _join_visit_keys(
                item["visit_key_tuple"] for item in successors
            )
            preserved = True
            own_candidate = candidate_position[party["visit_key_tuple"]]
            for other in inlink_parties:
                if other is party:
                    continue
                baseline_before = (
                    baseline_position[party["visit_key_tuple"]]
                    < baseline_position[other["visit_key_tuple"]]
                )
                candidate_before = own_candidate < candidate_position[other["visit_key_tuple"]]
                if baseline_before != candidate_before:
                    preserved = False
            party["same_inlink_fifo_preserved"] = preserved
        for left_index, left in enumerate(baseline_order):
            for right in baseline_order[left_index + 1 :]:
                if (
                    candidate_position[left["visit_key_tuple"]]
                    > candidate_position[right["visit_key_tuple"]]
                ):
                    violation_count = violation_count + 1
    return violation_count


def _plain_visit_keys(visit_keys) -> tuple[tuple[str, int], ...]:
    return tuple(_plain_visit_key(visit_key) for visit_key in visit_keys)


def _require_unique_visit_keys(visit_keys, node_name: str, timestep: int, label: str) -> None:
    if len(visit_keys) != len(set(visit_keys)):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {label} repeats a VisitKey."
        )


def _require_saved_finite_number(value, node_name: str, timestep: int, label: str):
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {label} is {value!r}."
        )
    if value != value or value == float("inf") or value == float("-inf"):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {label} is not finite: {value!r}."
        )
    return value


def _require_audit_node(result, expected_type, node_name: str, timestep: int, stage_name: str):
    if not isinstance(result, expected_type):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {stage_name} is "
            f"{type(result).__name__}."
        )
    if result.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {stage_name} node_name "
            f"is {result.node_name!r}."
        )
    return result


def _require_same_saved_value(
    node_name: str,
    timestep: int,
    visit_key,
    field_name: str,
    left,
    right,
) -> None:
    if left != right:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {field_name} for "
            f"{_visit_text(visit_key)} disagrees: {left!r} versus {right!r}."
        )


def _require_snapshot_matches_candidate_visit(
    snapshot: dict,
    candidate_visit,
    node_name: str,
    timestep: int,
    visit_key,
) -> None:
    _require_same_saved_value(
        node_name, timestep, visit_key, "vehicle_id",
        snapshot["vehicle_id"], candidate_visit.vehicle_id,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "node_name",
        snapshot["node_name"], node_name,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "inlink_name",
        snapshot["inlink_name"], candidate_visit.inlink_name,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "baseline_arrival_timestep",
        snapshot["baseline_arrival_timestep"], candidate_visit.baseline_arrival_timestep,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "arrival_tiebreaker",
        snapshot["arrival_tiebreaker"], candidate_visit.arrival_tiebreaker,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "route_next_link_name",
        snapshot["route_next_link_name"], candidate_visit.route_next_link_name,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "baseline_passage_timestep",
        snapshot["baseline_passage_timestep"], candidate_visit.baseline_passage_timestep,
    )


def _require_snapshot_matches_binding_visit(
    snapshot: dict,
    binding_visit,
    node_name: str,
    timestep: int,
    visit_key,
) -> None:
    _require_same_saved_value(
        node_name, timestep, visit_key, "binding vehicle_id",
        snapshot["vehicle_id"], binding_visit.vehicle_id,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "binding inlink_name",
        snapshot["inlink_name"], binding_visit.inlink_name,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "binding baseline_arrival_timestep",
        snapshot["baseline_arrival_timestep"], binding_visit.baseline_arrival_timestep,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "binding arrival_tiebreaker",
        snapshot["arrival_tiebreaker"], binding_visit.arrival_tiebreaker,
    )
    _require_same_saved_value(
        node_name, timestep, visit_key, "binding route_next_link_name",
        snapshot["route_next_link_name"], binding_visit.route_next_link_name,
    )


def _require_saved_economic_totals(economic_result, buyers, node_name: str, timestep: int) -> None:
    total_g = _require_saved_finite_number(
        economic_result.total_buyer_value_G, node_name, timestep, "total_buyer_value_G"
    )
    total_r = _require_saved_finite_number(
        economic_result.total_required_compensation_R,
        node_name,
        timestep,
        "total_required_compensation_R",
    )
    surplus = _require_saved_finite_number(
        economic_result.surplus, node_name, timestep, "surplus"
    )
    summed_g = 0.0
    for record in economic_result.buyer_economic_records:
        summed_g = summed_g + _require_saved_finite_number(
            record.gross_time_value_G_b, node_name, timestep, "gross_time_value_G_b"
        )
    if summed_g != total_g:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: total_buyer_value_G does not "
            "equal the saved buyer gross_time_value_G_b values."
        )
    summed_r = 0.0
    for record in economic_result.seller_economic_records:
        summed_r = summed_r + _require_saved_finite_number(
            record.required_compensation_R_s,
            node_name,
            timestep,
            "required_compensation_R_s",
        )
    if summed_r != total_r:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: total_required_compensation_R "
            "does not equal the saved required_compensation_R_s values."
        )
    if surplus != total_g - total_r:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: saved surplus does not equal "
            "total_buyer_value_G - total_required_compensation_R."
        )
    if len(economic_result.buyer_economic_records) != len(buyers):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: buyer economic record count "
            "does not match buyers_sorted."
        )


def _binding_visits_for_candidate(
    local_result,
    concrete_set,
    buyers,
    trade_scope,
    node_name: str,
    timestep: int,
) -> dict:
    binding_sequence = local_result.binding_rank_sequence
    if not isinstance(binding_sequence, OrderControlTvtMpLocalBindingRankSequence):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding rank sequence is "
            f"{type(binding_sequence).__name__}."
        )
    if binding_sequence.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding sequence node_name "
            f"is {binding_sequence.node_name!r}."
        )
    if binding_sequence.baseline_timestep_T != timestep:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding sequence "
            f"baseline_timestep_T is {binding_sequence.baseline_timestep_T!r}."
        )
    if binding_sequence.concrete_buyer_candidate_set is not concrete_set:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding sequence concrete "
            "set is not this candidate."
        )
    binding_buyers = _plain_visit_keys(
        binding_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    if binding_buyers != buyers:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding sequence buyers "
            "do not match this candidate."
        )
    binding_by_key = {}
    for binding_visit in binding_sequence.trade_scope_of_this_candidate_visits:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: binding visit is "
                f"{type(binding_visit).__name__}."
            )
        if (
            binding_visit.binding_partition
            is not OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope binding visit "
                f"has partition {binding_visit.binding_partition!r}."
            )
        visit_key = _plain_visit_key(binding_visit.visit_key)
        if visit_key in binding_by_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: binding trade scope repeats "
                f"{_visit_text(visit_key)}."
            )
        if type(binding_visit.binding_rank) is not int or binding_visit.binding_rank < 1:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: binding_rank for "
                f"{_visit_text(visit_key)} is {binding_visit.binding_rank!r}."
            )
        binding_by_key[visit_key] = binding_visit
    _require_same_visit_keys(
        tuple(binding_by_key),
        trade_scope,
        node_name,
        timestep,
        "binding trade scope versus trade_scope",
    )
    if len(binding_by_key) != len(trade_scope):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding trade-scope length "
            "does not match trade_scope."
        )
    return binding_by_key


def _saved_selection_comparison_name(
    candidate_surplus,
    selected_surplus,
    candidate_buyer_count: int,
    selected_buyer_count: int,
    rng_was_used: bool,
    node_name: str,
    timestep: int,
    candidate_identity: str,
) -> str:
    """Classify from saved surplus, buyer count, and rng_was_used only."""
    if candidate_surplus < selected_surplus:
        return "surplus"
    if (
        candidate_surplus == selected_surplus
        and candidate_buyer_count < selected_buyer_count
    ):
        return "buyer_count"
    if (
        candidate_surplus == selected_surplus
        and candidate_buyer_count == selected_buyer_count
        and rng_was_used is True
    ):
        return "rng_was_used"
    raise RuntimeError(
        f"{_decision_label(node_name, timestep)}: {candidate_identity} is "
        "economically feasible but saved surplus, buyer count, and "
        "rng_was_used do not determine a selection comparison."
    )


def _require_saved_selection_consistent(
    feasible_entries: list[dict],
    selected_buyers,
    selected_surplus,
    selected_buyer_count: int,
    rng_was_used: bool,
    node_name: str,
    timestep: int,
) -> None:
    if len(feasible_entries) == 0:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: a candidate is selected "
            "but no saved economic result is economically_feasible."
        )
    maximum_surplus = feasible_entries[0]["surplus"]
    for entry in feasible_entries:
        if entry["surplus"] > maximum_surplus:
            maximum_surplus = entry["surplus"]
    at_surplus = []
    for entry in feasible_entries:
        if entry["surplus"] == maximum_surplus:
            at_surplus.append(entry)
    maximum_buyer_count = at_surplus[0]["buyer_count"]
    for entry in at_surplus:
        if entry["buyer_count"] > maximum_buyer_count:
            maximum_buyer_count = entry["buyer_count"]
    tied = []
    for entry in at_surplus:
        if entry["buyer_count"] == maximum_buyer_count:
            tied.append(entry)
    selected_found = False
    for entry in tied:
        if entry["buyers"] == selected_buyers:
            selected_found = True
    if selected_found is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: the saved selected "
            "candidate is not among the saved maximum surplus and maximum "
            "buyer-count candidates."
        )
    if selected_surplus != maximum_surplus or selected_buyer_count != maximum_buyer_count:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: saved selected surplus or "
            "buyer count is not the saved maximum."
        )
    expected_rng = len(tied) >= 2
    if rng_was_used is not expected_rng:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rng_was_used={rng_was_used!r} "
            f"does not match saved tie size {len(tied)}."
        )


def _annotate_audit_same_inlink_fifo(parties: list[dict], node_name: str, timestep: int) -> bool:
    """Recompare same-inlink order using baseline_local_rank and post_trade_local_rank.

    Those two ranks are the audit's before/after local ranks. This comparison
    does not read the binding sequence.
    """
    grouped: dict[str, list[dict]] = {}
    for party in parties:
        grouped.setdefault(party["inlink_name"], []).append(party)
    any_violation = False
    for inlink_parties in grouped.values():
        for party in inlink_parties:
            party["same_inlink_fifo_preserved"] = True
        for left_index, left in enumerate(inlink_parties):
            for right in inlink_parties[left_index + 1 :]:
                if left["baseline_local_rank"] == right["baseline_local_rank"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: baseline_local_rank "
                        "values are not unique inside one inlink."
                    )
                if left["post_trade_local_rank"] == right["post_trade_local_rank"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: post_trade_local_rank "
                        "values are not unique inside one inlink."
                    )
                baseline_before = left["baseline_local_rank"] < right["baseline_local_rank"]
                candidate_before = (
                    left["post_trade_local_rank"] < right["post_trade_local_rank"]
                )
                if baseline_before != candidate_before:
                    left["same_inlink_fifo_preserved"] = False
                    right["same_inlink_fifo_preserved"] = False
                    any_violation = True
    return any_violation is False


def _build_east_t35_all_candidate_audit(
    world,
    timestep: int,
    node_name: str,
    concrete_node,
    trade_node,
    fifo_node,
    local_node,
    economic_node,
    selection_node,
    payment_node,
    candidate_visit_node,
    right_of_entry_node,
    collector,
) -> list[dict]:
    """
    One row per trade-scope visit of every stored east T=35 concrete candidate.

    Later stages are matched by object identity and by buyer VisitKeys, node
    name, and decision timestep. Passage and economics come from that
    candidate's own saved result.
    """
    if (node_name, timestep) != EAST_T35_AUDIT_KEY:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)} is outside the east T=35 "
            "all-candidate audit."
        )
    _require_audit_node(
        concrete_node,
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
        node_name,
        timestep,
        "concrete candidates",
    )
    _require_audit_node(
        trade_node,
        OrderControlTvtNodeMpGeneralTradeRankResult,
        node_name,
        timestep,
        "trade rank",
    )
    _require_audit_node(
        fifo_node,
        OrderControlTvtNodeMpFifoInspectionResult,
        node_name,
        timestep,
        "fifo",
    )
    _require_audit_node(
        local_node,
        OrderControlTvtNodeMpLocalVirtualCalculationResult,
        node_name,
        timestep,
        "local virtual calculation",
    )
    _require_audit_node(
        economic_node,
        OrderControlTvtNodeMpEconomicEvaluationResult,
        node_name,
        timestep,
        "economic evaluation",
    )
    _require_audit_node(
        selection_node,
        OrderControlTvtNodeMpCandidateSelectionResult,
        node_name,
        timestep,
        "candidate selection",
    )
    _require_audit_node(
        payment_node,
        OrderControlTvtNodeMpPaymentAndCompensationResult,
        node_name,
        timestep,
        "payment",
    )
    _require_audit_node(
        candidate_visit_node,
        OrderControlTvtNodeCandidateVisitSetResult,
        node_name,
        timestep,
        "candidate visits",
    )
    _require_audit_node(
        right_of_entry_node,
        OrderControlTvtNodeRightOfEntrySelectionResult,
        node_name,
        timestep,
        "right of entry",
    )
    if (
        selection_node.selection_status
        is not OrderControlTvtMpCandidateSelectionStatus.SELECTED
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selection_status is "
            f"{selection_node.selection_status!r}."
        )
    if type(selection_node.rng_was_used) is not bool:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rng_was_used is "
            f"{selection_node.rng_was_used!r}."
        )
    if (
        payment_node.payment_and_compensation_status
        is not OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment status is "
            f"{payment_node.payment_and_compensation_status!r}."
        )
    selected_economic_result = selection_node.selected_candidate_economic_result
    if not isinstance(
        selected_economic_result, OrderControlTvtMpCandidateEconomicEvaluationResult
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result "
            f"is {type(selected_economic_result).__name__}."
        )
    if payment_node.selected_candidate_economic_result is not selected_economic_result:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment selected result "
            "is not the selection result."
        )
    concrete_sets = concrete_node.concrete_buyer_candidate_sets
    trade_results = trade_node.candidate_trade_rank_results
    fifo_results = fifo_node.candidate_fifo_inspection_results
    if len(concrete_sets) != len(trade_results) or len(concrete_sets) != len(fifo_results):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: concrete, trade-rank, and "
            "FIFO result counts differ."
        )
    aligned = []
    seen_buyers = set()
    for stored_index, concrete_set in enumerate(concrete_sets):
        if not isinstance(concrete_set, OrderControlTvtMpConcreteBuyerCandidateSet):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: concrete set {stored_index} "
                f"is {type(concrete_set).__name__}."
            )
        trade_result = trade_results[stored_index]
        fifo_result = fifo_results[stored_index]
        if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade rank {stored_index} "
                f"is {type(trade_result).__name__}."
            )
        if not isinstance(fifo_result, OrderControlTvtMpCandidateFifoInspectionResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result {stored_index} "
                f"is {type(fifo_result).__name__}."
            )
        if trade_result.concrete_buyer_candidate_set is not concrete_set:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade rank {stored_index} "
                "does not reference the concrete set at that index."
            )
        buyers = _plain_visit_keys(concrete_set.buyers_sorted)
        trade_buyers = _plain_visit_keys(trade_result.buyers_sorted)
        if trade_buyers != buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-rank buyers at "
                f"index {stored_index} do not match the concrete buyer set."
            )
        if fifo_result.general_trade_rank_result is not trade_result:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result {stored_index} "
                "does not reference the trade-rank result at that index."
            )
        fifo_buyers = _plain_visit_keys(
            fifo_result.general_trade_rank_result.buyers_sorted
        )
        if fifo_buyers != buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO buyers at index "
                f"{stored_index} do not match the concrete buyer set."
            )
        if type(fifo_result.preserves_inlink_fifo) is not bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: preserves_inlink_fifo "
                f"is {fifo_result.preserves_inlink_fifo!r}."
            )
        sellers = _plain_visit_keys(trade_result.sellers_sorted)
        nonparticipating = _plain_visit_keys(trade_result.nonparticipating_visits_sorted)
        trade_scope = _plain_visit_keys(trade_result.trade_scope)
        _require_unique_visit_keys(buyers, node_name, timestep, "buyers_sorted")
        _require_unique_visit_keys(sellers, node_name, timestep, "sellers_sorted")
        _require_unique_visit_keys(
            nonparticipating, node_name, timestep, "nonparticipating_visits_sorted"
        )
        _require_unique_visit_keys(trade_scope, node_name, timestep, "trade_scope")
        if len(buyers) < 1 or len(sellers) < 1 or len(trade_scope) < 1:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate {stored_index} "
                "has an empty buyer, seller, or trade_scope sequence."
            )
        if len(trade_scope) != len(buyers) + len(sellers) + len(nonparticipating):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade_scope length does "
                "not equal buyers, sellers, and nonparticipating visits."
            )
        _require_same_visit_keys(
            trade_scope,
            buyers + sellers + nonparticipating,
            node_name,
            timestep,
            "trade_scope versus role columns",
        )
        if buyers in seen_buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate concrete buyers "
                f"{_join_visit_keys(buyers)}."
            )
        seen_buyers.add(buyers)
        aligned.append(
            {
                "stored_index": stored_index,
                "concrete_set": concrete_set,
                "trade_result": trade_result,
                "fifo_passed": fifo_result.preserves_inlink_fifo,
                "buyers": buyers,
                "sellers": sellers,
                "nonparticipating": nonparticipating,
                "trade_scope": trade_scope,
            }
        )
    passed = 0
    failed = 0
    for item in aligned:
        if item["fifo_passed"] is True:
            passed = passed + 1
        else:
            failed = failed + 1
    if (
        len(aligned) != EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT
        or passed != EAST_T35_EXPECTED_FIFO_PASSED_COUNT
        or failed != EAST_T35_EXPECTED_FIFO_FAILED_COUNT
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: concrete candidate count "
            f"{len(aligned)}, FIFO passed {passed}, FIFO failed {failed}; "
            f"expected {EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT}, "
            f"{EAST_T35_EXPECTED_FIFO_PASSED_COUNT}, "
            f"{EAST_T35_EXPECTED_FIFO_FAILED_COUNT}."
        )
    local_by_buyers = {}
    for local_result in local_node.candidate_local_virtual_calculation_results:
        if not isinstance(
            local_result, OrderControlTvtMpCandidateLocalVirtualCalculationResult
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result is "
                f"{type(local_result).__name__}."
            )
        if local_result.node_name != node_name:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result node_name "
                f"is {local_result.node_name!r}."
            )
        if local_result.baseline_timestep_T != timestep:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result "
                f"baseline_timestep_T is {local_result.baseline_timestep_T!r}."
            )
        if type(local_result.resolved) is not bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local resolved is "
                f"{local_result.resolved!r}."
            )
        if (
            not isinstance(
                local_result.stop_reason,
                OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
            )
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: stop_reason is "
                f"{local_result.stop_reason!r}."
            )
        if local_result.resolved is True:
            if (
                local_result.stop_reason
                is not OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
            ):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: resolved local result "
                    f"has stop_reason {local_result.stop_reason!r}."
                )
            if len(local_result.unresolved_reasons) != 0:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: resolved local result "
                    "has unresolved_reasons."
                )
        if local_result.resolved is False:
            if (
                local_result.stop_reason
                is not OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
            ):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: unresolved local "
                    f"result has stop_reason {local_result.stop_reason!r}."
                )
        local_buyers = _plain_visit_keys(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        matched_item = None
        for item in aligned:
            if item["buyers"] == local_buyers:
                matched_item = item
        if matched_item is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result buyers "
                f"{_join_visit_keys(local_buyers)} match no concrete candidate."
            )
        if local_result.concrete_buyer_candidate_set is not matched_item["concrete_set"]:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result concrete "
                "set is not the concrete candidate with the same buyers."
            )
        if matched_item["fifo_passed"] is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: a FIFO-failed candidate "
                "has a local virtual-calculation result."
            )
        if local_buyers in local_by_buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate local result "
                f"for {_join_visit_keys(local_buyers)}."
            )
        local_by_buyers[local_buyers] = local_result
    if len(local_by_buyers) != passed:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: local result count "
            f"{len(local_by_buyers)} does not match FIFO passed count {passed}."
        )
    economic_by_buyers = {}
    for economic_result in economic_node.candidate_economic_evaluation_results:
        if not isinstance(
            economic_result, OrderControlTvtMpCandidateEconomicEvaluationResult
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic result is "
                f"{type(economic_result).__name__}."
            )
        economic_local = economic_result.candidate_local_virtual_calculation_result
        if not isinstance(
            economic_local, OrderControlTvtMpCandidateLocalVirtualCalculationResult
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic local result "
                f"is {type(economic_local).__name__}."
            )
        if economic_local.node_name != node_name or economic_local.baseline_timestep_T != timestep:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic result is for "
                f"node {economic_local.node_name!r} at "
                f"T={economic_local.baseline_timestep_T}."
            )
        economic_buyers = _plain_visit_keys(
            economic_local.concrete_buyer_candidate_set.buyers_sorted
        )
        if local_by_buyers.get(economic_buyers) is not economic_local:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic result does "
                "not reference the saved local result for "
                f"{_join_visit_keys(economic_buyers)}."
            )
        if economic_local.resolved is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic result exists "
                "for an unresolved local result."
            )
        if economic_buyers in economic_by_buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate economic "
                f"result for {_join_visit_keys(economic_buyers)}."
            )
        _require_saved_economic_totals(
            economic_result, economic_buyers, node_name, timestep
        )
        economic_by_buyers[economic_buyers] = economic_result
    resolved_count = 0
    for local_result in local_by_buyers.values():
        if local_result.resolved is True:
            resolved_count = resolved_count + 1
    if len(economic_by_buyers) != resolved_count:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: economic result count "
            f"{len(economic_by_buyers)} does not match resolved local count "
            f"{resolved_count}."
        )
    for local_buyers, local_result in local_by_buyers.items():
        if local_result.resolved is True and local_buyers not in economic_by_buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: resolved candidate "
                f"{_join_visit_keys(local_buyers)} has no economic result."
            )
        if local_result.resolved is False and local_buyers in economic_by_buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: unresolved candidate "
                f"{_join_visit_keys(local_buyers)} has an economic result."
            )
    selection_local_result = (
        selected_economic_result.candidate_local_virtual_calculation_result
    )
    if selection_local_result.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local node_name "
            f"is {selection_local_result.node_name!r}."
        )
    if selection_local_result.baseline_timestep_T != timestep:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local "
            "baseline_timestep_T does not match the decision timestep."
        )
    selected_buyers = _plain_visit_keys(
        selection_local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    if local_by_buyers.get(selected_buyers) is not selection_local_result:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local result is "
            "not the saved local result for the selected buyers."
        )
    if economic_by_buyers.get(selected_buyers) is not selected_economic_result:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result "
            "is not the saved economic result for the selected buyers."
        )
    if selected_economic_result.economically_feasible is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result "
            "is not economically_feasible."
        )
    selected_sellers = None
    for item in aligned:
        if item["buyers"] == selected_buyers:
            selected_sellers = item["sellers"]
    if selected_sellers is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected buyers match no "
            "concrete candidate."
        )
    payment_buyer_keys = []
    for record in payment_node.buyer_payment_records:
        if not isinstance(record, OrderControlTvtMpBuyerPaymentRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: payment record is "
                f"{type(record).__name__}."
            )
        payment_buyer_keys.append(_plain_visit_key(record.visit_key))
    payment_seller_keys = []
    for record in payment_node.seller_compensation_records:
        if not isinstance(record, OrderControlTvtMpSellerCompensationRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: compensation record is "
                f"{type(record).__name__}."
            )
        payment_seller_keys.append(_plain_visit_key(record.visit_key))
    _require_unique_visit_keys(
        tuple(payment_buyer_keys), node_name, timestep, "buyer_payment_records"
    )
    _require_unique_visit_keys(
        tuple(payment_seller_keys), node_name, timestep, "seller_compensation_records"
    )
    _require_same_visit_keys(
        tuple(payment_buyer_keys),
        selected_buyers,
        node_name,
        timestep,
        "payment buyers versus selected buyers",
    )
    _require_same_visit_keys(
        tuple(payment_seller_keys),
        selected_sellers,
        node_name,
        timestep,
        "payment sellers versus selected sellers",
    )
    if len(payment_buyer_keys) != len(selected_buyers):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment buyer count does "
            "not match selected buyers."
        )
    if len(payment_seller_keys) != len(selected_sellers):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: compensation seller count "
            "does not match selected sellers."
        )
    selected_surplus = selected_economic_result.surplus
    selected_buyer_count = len(selected_buyers)
    if type(selected_buyer_count) is not int or selected_buyer_count < 1:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected buyer count is "
            f"{selected_buyer_count!r}."
        )
    feasible_entries = []
    for buyers, economic_result in economic_by_buyers.items():
        if economic_result.economically_feasible is True:
            feasible_entries.append(
                {
                    "buyers": buyers,
                    "surplus": economic_result.surplus,
                    "buyer_count": len(buyers),
                }
            )
    _require_saved_selection_consistent(
        feasible_entries,
        selected_buyers,
        selected_surplus,
        selected_buyer_count,
        selection_node.rng_was_used,
        node_name,
        timestep,
    )
    if right_of_entry_node.right_of_entry_visit_key is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right_of_entry_visit_key "
            "is missing."
        )
    right_of_entry_key = _plain_visit_key(right_of_entry_node.right_of_entry_visit_key)
    candidate_visit_by_key = {}
    for candidate_visit in candidate_visit_node.candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate visit is "
                f"{type(candidate_visit).__name__}."
            )
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in candidate_visit_by_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits repeats "
                f"{_visit_text(visit_key)}."
            )
        candidate_visit_by_key[visit_key] = candidate_visit
    ordered_candidate_keys, baseline_ranks = _baseline_local_ranks(
        candidate_visit_node.candidate_visits, node_name, timestep
    )
    if right_of_entry_key not in baseline_ranks:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry "
            f"{_visit_text(right_of_entry_key)} is not in candidate_visits."
        )
    role_by_name = {
        "buyer": OrderControlTvtMpLocalBindingTradeRole.BUYER,
        "seller": OrderControlTvtMpLocalBindingTradeRole.SELLER,
        "nonparticipating": OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
    }
    rows = []
    for item in aligned:
        buyers = item["buyers"]
        sellers = item["sellers"]
        nonparticipating = item["nonparticipating"]
        trade_scope = item["trade_scope"]
        trade_result = item["trade_result"]
        concrete_set = item["concrete_set"]
        fifo_passed = item["fifo_passed"]
        candidate_identity = _candidate_identity(node_name, buyers)
        matched_local = local_by_buyers.get(buyers)
        if fifo_passed is True and matched_local is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO-passed "
                f"{candidate_identity} has no local result."
            )
        if fifo_passed is not True and matched_local is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO-failed "
                f"{candidate_identity} has a local result."
            )
        matched_economic = None
        if matched_local is not None and matched_local.resolved is True:
            matched_economic = economic_by_buyers.get(buyers)
            if matched_economic is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: resolved "
                    f"{candidate_identity} has no economic result."
                )
            if (
                matched_economic.candidate_local_virtual_calculation_result
                is not matched_local
            ):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: economic result "
                    f"for {candidate_identity} points at another local result."
                )
        if matched_local is not None and matched_local.resolved is False:
            if buyers in economic_by_buyers:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: unresolved "
                    f"{candidate_identity} has an economic result."
                )
        buyer_set = set(buyers)
        seller_set = set(sellers)
        nonparticipating_set = set(nonparticipating)
        post_trade_local_ranks = _post_trade_local_ranks(
            trade_result,
            ordered_candidate_keys,
            node_name,
            timestep,
            candidate_identity,
        )
        _require_same_population_and_continuous_local_ranks(
            ordered_candidate_keys,
            baseline_ranks,
            post_trade_local_ranks,
            node_name,
            timestep,
            candidate_identity,
        )
        binding_by_key = {}
        observations = {}
        local_resolved = None
        stop_reason_text = None
        if matched_local is not None:
            binding_by_key = _binding_visits_for_candidate(
                matched_local,
                concrete_set,
                buyers,
                trade_scope,
                node_name,
                timestep,
            )
            for observation in matched_local.traffic_observation_records:
                if not isinstance(
                    observation, OrderControlTvtMpCandidateTrafficObservationRecord
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: traffic "
                        f"observation is {type(observation).__name__}."
                    )
                observation_key = _plain_visit_key(observation.visit_key)
                if observation_key in observations:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"{candidate_identity} repeats traffic observation "
                        f"{_visit_text(observation_key)}."
                    )
                observations[observation_key] = observation
            local_resolved = matched_local.resolved
            stop_reason_text = matched_local.stop_reason.value
        infeasibility_values = []
        if matched_economic is not None:
            if type(matched_economic.economically_feasible) is not bool:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{candidate_identity} economically_feasible is "
                    f"{matched_economic.economically_feasible!r}."
                )
            for reason in matched_economic.infeasibility_reasons:
                if not isinstance(
                    reason, OrderControlTvtMpCandidateEconomicInfeasibilityReason
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"{candidate_identity} infeasibility reason is {reason!r}."
                    )
                infeasibility_values.append(reason.value)
            if matched_economic.economically_feasible is True and len(infeasibility_values) != 0:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: feasible "
                    f"{candidate_identity} has infeasibility_reasons."
                )
            if matched_economic.economically_feasible is not True and len(infeasibility_values) == 0:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: infeasible "
                    f"{candidate_identity} has no infeasibility_reasons."
                )
        infeasibility_text = "|".join(infeasibility_values)
        unresolved_values = []
        if matched_local is not None:
            for reason in matched_local.unresolved_reasons:
                if not isinstance(reason, OrderControlTvtMpCandidateUnresolvedReason):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"{candidate_identity} unresolved reason is {reason!r}."
                    )
                unresolved_values.append(reason.value)
        unresolved_text = "|".join(unresolved_values)
        if fifo_passed is not True:
            exclusion_stage = EXCLUSION_STAGE_FIFO_FAILED
            exclusion_reason = "preserves_inlink_fifo=False"
            economically_evaluated = False
        elif matched_local.resolved is not True:
            exclusion_stage = EXCLUSION_STAGE_LOCAL_UNRESOLVED
            exclusion_reason = (
                f"stop_reason={stop_reason_text};"
                f"unresolved_reasons={unresolved_text}"
            )
            economically_evaluated = False
        elif matched_economic.economically_feasible is not True:
            exclusion_stage = EXCLUSION_STAGE_ECONOMICALLY_INFEASIBLE
            exclusion_reason = infeasibility_text
            economically_evaluated = True
        elif buyers != selected_buyers:
            comparison_name = _saved_selection_comparison_name(
                matched_economic.surplus,
                selected_surplus,
                len(buyers),
                selected_buyer_count,
                selection_node.rng_was_used,
                node_name,
                timestep,
                candidate_identity,
            )
            exclusion_stage = EXCLUSION_STAGE_FEASIBLE_NOT_SELECTED
            exclusion_reason = (
                f"candidate_surplus={matched_economic.surplus};"
                f"selected_surplus={selected_surplus};"
                f"candidate_buyer_count={len(buyers)};"
                f"selected_buyer_count={selected_buyer_count};"
                f"rng_was_used={selection_node.rng_was_used};"
                f"saved_comparison={comparison_name}"
            )
            economically_evaluated = True
        else:
            exclusion_stage = EXCLUSION_STAGE_SELECTED
            exclusion_reason = None
            economically_evaluated = True
        is_selected = buyers == selected_buyers
        if is_selected is True and exclusion_stage != EXCLUSION_STAGE_SELECTED:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected "
                f"{candidate_identity} was staged as {exclusion_stage}."
            )
        if is_selected is not True and exclusion_stage == EXCLUSION_STAGE_SELECTED:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: unselected "
                f"{candidate_identity} was staged as selected."
            )
        total_g = None
        total_r = None
        surplus = None
        economically_feasible = None
        infeasibility_cell = None
        buyer_records = {}
        seller_records = {}
        if economically_evaluated is True:
            total_g = matched_economic.total_buyer_value_G
            total_r = matched_economic.total_required_compensation_R
            surplus = matched_economic.surplus
            economically_feasible = matched_economic.economically_feasible
            infeasibility_cell = infeasibility_text
            buyer_records = _records_by_visit_key(
                matched_economic.buyer_economic_records,
                node_name,
                timestep,
                "buyer_economic_records",
            )
            seller_records = _records_by_visit_key(
                matched_economic.seller_economic_records,
                node_name,
                timestep,
                "seller_economic_records",
            )
            _require_same_visit_keys(
                buyers, tuple(buyer_records), node_name, timestep, "buyers versus buyer economics"
            )
            _require_same_visit_keys(
                sellers,
                tuple(seller_records),
                node_name,
                timestep,
                "sellers versus seller economics",
            )
        visit_rows = []
        for visit_key in trade_scope:
            if visit_key in buyer_set:
                role_name = "buyer"
            elif visit_key in seller_set:
                role_name = "seller"
            elif visit_key in nonparticipating_set:
                role_name = "nonparticipating"
            else:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{_visit_text(visit_key)} is in trade_scope but is not a "
                    "saved buyer, seller, or nonparticipating visit."
                )
            if visit_key not in baseline_ranks or visit_key not in candidate_visit_by_key:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{_visit_text(visit_key)} is missing from candidate_visits."
                )
            candidate_visit = candidate_visit_by_key[visit_key]
            snapshot = _collector_snapshot(collector, timestep, node_name, visit_key)
            _require_snapshot_matches_candidate_visit(
                snapshot, candidate_visit, node_name, timestep, visit_key
            )
            binding_visit = binding_by_key.get(visit_key)
            if matched_local is not None and binding_visit is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{_visit_text(visit_key)} has no binding visit on "
                    f"{candidate_identity}."
                )
            if binding_visit is not None:
                _require_snapshot_matches_binding_visit(
                    snapshot, binding_visit, node_name, timestep, visit_key
                )
                if binding_visit.trade_role is not role_by_name[role_name]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: binding role "
                        f"{binding_visit.trade_role!r} does not match trade-rank "
                        f"role {role_name!r} for {_visit_text(visit_key)}."
                    )
            baseline_rank = baseline_ranks[visit_key]
            establishment_rank = _establishment_baseline_rank(
                world, timestep, node_name, visit_key
            )
            if establishment_rank is not None and establishment_rank != baseline_rank:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: establishment "
                    f"baseline rank {establishment_rank} for {_visit_text(visit_key)} "
                    f"does not match candidate_visits position {baseline_rank}."
                )
            baseline_passage = snapshot["baseline_passage_timestep"]
            if type(baseline_passage) is not int:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: baseline passage for "
                    f"{_visit_text(visit_key)} is {baseline_passage!r}."
                )
            observation = None
            if matched_local is not None:
                observation = observations.get(visit_key)
                if observation is None:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"{candidate_identity} has no traffic observation for "
                        f"{_visit_text(visit_key)}."
                    )
                if observation.baseline_passage_timestep != baseline_passage:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: traffic "
                        f"observation baseline passage disagrees for "
                        f"{_visit_text(visit_key)}."
                    )
            candidate_passage = None
            predicted_difference = None
            if observation is not None:
                candidate_passage = observation.candidate_passage_timestep
                predicted_difference = observation.predicted_time_difference_timesteps
                if candidate_passage is None:
                    if predicted_difference is not None:
                        raise RuntimeError(
                            f"{_decision_label(node_name, timestep)}: "
                            f"{_visit_text(visit_key)} has a predicted time "
                            "difference without candidate passage."
                        )
                else:
                    if type(candidate_passage) is not int or type(predicted_difference) is not int:
                        raise RuntimeError(
                            f"{_decision_label(node_name, timestep)}: candidate "
                            f"passage for {_visit_text(visit_key)} is "
                            f"{candidate_passage!r} with difference "
                            f"{predicted_difference!r}."
                        )
                    if predicted_difference != baseline_passage - candidate_passage:
                        raise RuntimeError(
                            f"{_decision_label(node_name, timestep)}: "
                            "predicted_time_difference_timesteps does not match "
                            f"saved passage times for {_visit_text(visit_key)}."
                        )
            if (
                matched_local is not None
                and matched_local.resolved is True
                and role_name != "nonparticipating"
                and type(candidate_passage) is not int
            ):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: resolved "
                    f"{role_name} {_visit_text(visit_key)} has no candidate passage."
                )
            buyer_record = buyer_records.get(visit_key)
            seller_record = seller_records.get(visit_key)
            if role_name == "buyer":
                if economically_evaluated is True and (
                    buyer_record is None or seller_record is not None
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: buyer economics "
                        f"do not match {_visit_text(visit_key)}."
                    )
                if economically_evaluated is not True and (
                    buyer_record is not None or seller_record is not None
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: unevaluated "
                        f"{_visit_text(visit_key)} has an economic record."
                    )
            elif role_name == "seller":
                if economically_evaluated is True and (
                    seller_record is None or buyer_record is not None
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: seller economics "
                        f"do not match {_visit_text(visit_key)}."
                    )
                if economically_evaluated is not True and (
                    buyer_record is not None or seller_record is not None
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: unevaluated "
                        f"{_visit_text(visit_key)} has an economic record."
                    )
            elif buyer_record is not None or seller_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: nonparticipating "
                    f"{_visit_text(visit_key)} has an economic record."
                )
            declared_vot = None
            buyer_value = None
            seller_compensation = None
            if buyer_record is not None:
                if buyer_record.baseline_passage_timestep != baseline_passage:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: buyer baseline "
                        f"passage disagrees for {_visit_text(visit_key)}."
                    )
                if buyer_record.candidate_passage_timestep != candidate_passage:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: buyer candidate "
                        f"passage disagrees for {_visit_text(visit_key)}."
                    )
                if buyer_record.expected_time_saving_timesteps != predicted_difference:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        "expected_time_saving_timesteps disagrees with "
                        f"predicted_time_difference_timesteps for "
                        f"{_visit_text(visit_key)}."
                    )
                declared_vot = buyer_record.declared_vot_per_second
                buyer_value = buyer_record.gross_time_value_G_b
            if seller_record is not None:
                if seller_record.baseline_passage_timestep != baseline_passage:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: seller baseline "
                        f"passage disagrees for {_visit_text(visit_key)}."
                    )
                if seller_record.candidate_passage_timestep != candidate_passage:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: seller candidate "
                        f"passage disagrees for {_visit_text(visit_key)}."
                    )
                raw_difference = seller_record.raw_passage_difference_timesteps
                if (
                    type(raw_difference) is not int
                    or type(predicted_difference) is not int
                    or raw_difference + predicted_difference != 0
                ):
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        "raw_passage_difference_timesteps disagrees with "
                        f"predicted_time_difference_timesteps for "
                        f"{_visit_text(visit_key)}."
                    )
                declared_vot = seller_record.declared_vot_per_second
                seller_compensation = seller_record.required_compensation_R_s
            visit_rows.append(
                {
                    "visit_key": _visit_text(visit_key),
                    "visit_key_tuple": visit_key,
                    "vehicle_name": visit_key[0],
                    "visit_id": visit_key[1],
                    "role": role_name,
                    "is_right_of_entry_holder": visit_key == right_of_entry_key,
                    "inlink_name": candidate_visit.inlink_name,
                    "formal_route_next_link_name": candidate_visit.route_next_link_name,
                    "baseline_arrival_timestep": snapshot["baseline_arrival_timestep"],
                    "arrival_tiebreaker": snapshot["arrival_tiebreaker"],
                    "baseline_local_rank": baseline_rank,
                    "post_trade_local_rank": post_trade_local_ranks[visit_key],
                    "baseline_passage_timestep": baseline_passage,
                    "candidate_passage_timestep": candidate_passage,
                    "predicted_time_difference_timesteps": predicted_difference,
                    "declared_vot_per_second": declared_vot,
                    "buyer_value_G_b": buyer_value,
                    "seller_required_compensation_R_s": seller_compensation,
                }
            )
        if len(visit_rows) != len(trade_scope):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {candidate_identity} "
                "did not emit every trade-scope visit."
            )
        baseline_order = sorted(visit_rows, key=lambda row: row["baseline_local_rank"])
        candidate_order = sorted(visit_rows, key=lambda row: row["post_trade_local_rank"])
        header = {
            "decision_timestep": timestep,
            "node_name": node_name,
            "candidate_identity": candidate_identity,
            "candidate_index_in_stored_order": item["stored_index"],
            "buyer_visit_keys": _join_visit_keys(buyers),
            "seller_visit_keys": _join_visit_keys(sellers),
            "nonparticipating_visit_keys": _join_visit_keys(nonparticipating),
            "trade_scope_visit_keys": _join_visit_keys(trade_scope),
            "baseline_order_visit_keys": _join_visit_keys(
                row["visit_key_tuple"] for row in baseline_order
            ),
            "candidate_order_visit_keys": _join_visit_keys(
                row["visit_key_tuple"] for row in candidate_order
            ),
            "buyer_count": len(buyers),
            "seller_count": len(sellers),
            "nonparticipating_count": len(nonparticipating),
            "fifo_inspection_passed": fifo_passed,
            "local_virtual_calculation_resolved": local_resolved,
            "local_virtual_calculation_stop_reason": stop_reason_text,
            "economically_evaluated": economically_evaluated,
            "total_G": total_g,
            "total_R": total_r,
            "surplus": surplus,
            "economically_feasible": economically_feasible,
            "infeasibility_reasons": infeasibility_cell,
            "selected": is_selected,
            "selection_exclusion_stage": exclusion_stage,
            "selection_exclusion_reason": exclusion_reason,
        }
        candidate_rows = []
        for visit_row in baseline_order:
            merged = {}
            merged.update(header)
            merged.update(visit_row)
            candidate_rows.append(merged)
        diagnostic_fifo_preserved = _annotate_audit_same_inlink_fifo(
            candidate_rows, node_name, timestep
        )
        if diagnostic_fifo_preserved is not fifo_passed:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {candidate_identity} "
                f"production preserves_inlink_fifo={fifo_passed} but same-inlink "
                f"baseline/candidate rank comparison is {diagnostic_fifo_preserved}."
            )
        for candidate_row in candidate_rows:
            if type(candidate_row["same_inlink_fifo_preserved"]) is not bool:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{candidate_row['visit_key']} is missing the FIFO recomparison."
                )
        rows.extend(candidate_rows)
    identities = []
    for row in rows:
        if row["decision_timestep"] != timestep or row["node_name"] != node_name:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: audit row escaped the "
                "east T=35 decision."
            )
        if row["candidate_identity"] not in identities:
            identities.append(row["candidate_identity"])
    if len(identities) != EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: audit identity count is "
            f"{len(identities)}."
        )
    if len(rows) < EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: audit did not emit a row "
            "for every concrete candidate."
        )
    return rows


def _require_east_t35_audit_selected_identity(decision) -> None:
    label = _decision_label(decision["node_name"], decision["decision_timestep"])
    if decision["concrete_candidate_count"] != EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT:
        raise RuntimeError(
            f"{label}: saved concrete candidate count is "
            f"{decision['concrete_candidate_count']!r}."
        )
    if decision["fifo_passed_candidate_count"] != EAST_T35_EXPECTED_FIFO_PASSED_COUNT:
        raise RuntimeError(
            f"{label}: saved FIFO passed count is "
            f"{decision['fifo_passed_candidate_count']!r}."
        )
    if decision["fifo_failed_candidate_count"] != EAST_T35_EXPECTED_FIFO_FAILED_COUNT:
        raise RuntimeError(
            f"{label}: saved FIFO failed count is "
            f"{decision['fifo_failed_candidate_count']!r}."
        )
    identities = []
    selected_identities = []
    for row in GATE.east_t35_audit_rows:
        if (
            row["node_name"] != EAST_T35_AUDIT_KEY[0]
            or row["decision_timestep"] != EAST_T35_AUDIT_KEY[1]
        ):
            raise RuntimeError(f"{label}: audit row is outside east T=35.")
        identity = row["candidate_identity"]
        if identity not in identities:
            identities.append(identity)
        if row["selected"] is True and identity not in selected_identities:
            selected_identities.append(identity)
        if identity == decision["candidate_identity"] and row["selected"] is not True:
            raise RuntimeError(
                f"{label}: saved selected identity has an unselected audit row."
            )
        if identity != decision["candidate_identity"] and row["selected"] is not False:
            raise RuntimeError(
                f"{label}: audit marked {identity} selected."
            )
    if len(identities) != EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT:
        raise RuntimeError(f"{label}: audit did not keep seven candidate identities.")
    if selected_identities != [decision["candidate_identity"]]:
        raise RuntimeError(
            f"{label}: audit selected identities {selected_identities!r} do not "
            f"match saved selected identity {decision['candidate_identity']!r}."
        )


def _capture_target_node(world, columns, node_name: str, timestep: int) -> None:
    decision_key = (node_name, timestep)
    if decision_key in GATE.decisions:
        raise RuntimeError(f"{_decision_label(node_name, timestep)} was observed twice.")
    payment_node = _require_node_result(
        columns["payment_nodes"], node_name, timestep, "payment"
    )
    selection_node = _require_node_result(
        columns["selection_nodes"], node_name, timestep, "selection"
    )
    economic_node = _require_node_result(
        columns["economic_nodes"], node_name, timestep, "economic"
    )
    local_node = _require_node_result(
        columns["local_nodes"], node_name, timestep, "local virtual calculation"
    )
    fifo_node = _require_node_result(columns["fifo_nodes"], node_name, timestep, "fifo")
    trade_node = _require_node_result(
        columns["trade_rank_nodes"], node_name, timestep, "trade rank"
    )
    concrete_node = _require_node_result(
        columns["concrete_nodes"], node_name, timestep, "concrete candidates"
    )
    candidate_visit_node = _require_node_result(
        columns["candidate_visit_nodes"], node_name, timestep, "candidate visits"
    )
    right_of_entry_node = _require_node_result(
        columns["right_of_entry_nodes"], node_name, timestep, "right of entry"
    )
    if not isinstance(right_of_entry_node, OrderControlTvtNodeRightOfEntrySelectionResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry result type is "
            f"{type(right_of_entry_node).__name__}."
        )
    selected_economic = selection_node.selected_candidate_economic_result
    if (
        selection_node.selection_status
        is not OrderControlTvtMpCandidateSelectionStatus.SELECTED
        or selected_economic is None
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: no selected candidate."
        )
    if not isinstance(selected_economic, OrderControlTvtMpCandidateEconomicEvaluationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result type is "
            f"{type(selected_economic).__name__}."
        )
    if payment_node.selected_candidate_economic_result is not selected_economic:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment result points at a "
            "different selected candidate."
        )
    if (
        payment_node.payment_and_compensation_status
        is not OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment status is "
            f"{payment_node.payment_and_compensation_status!r}."
        )
    selected_in_node = False
    for economic_result in economic_node.candidate_economic_evaluation_results:
        if economic_result is selected_economic:
            selected_in_node = True
    if selected_in_node is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate is not in "
            "the node economic results."
        )
    selected_local = selected_economic.candidate_local_virtual_calculation_result
    if not isinstance(selected_local, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local result type is "
            f"{type(selected_local).__name__}."
        )
    local_saved = False
    for local_result in local_node.candidate_local_virtual_calculation_results:
        if local_result is selected_local:
            local_saved = True
    if local_saved is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local result is not "
            "stored on the node local-calculation result."
        )
    trade_result, fifo_result = _match_selected_trade_and_fifo(
        selected_local, trade_node, fifo_node, node_name, timestep
    )
    if fifo_result.preserves_inlink_fifo is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate did not "
            "pass FIFO inspection."
        )
    buyers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted)
    sellers_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.sellers_sorted
    )
    if len(buyers_sorted) < 2:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: buyer_count is {len(buyers_sorted)}."
        )
    binding_sequence = selected_local.binding_rank_sequence
    if binding_sequence.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding sequence node is "
            f"{binding_sequence.node_name!r}."
        )
    traffic_by_key = {}
    for observation in selected_local.traffic_observation_records:
        if not isinstance(observation, OrderControlTvtMpCandidateTrafficObservationRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: traffic observation type is "
                f"{type(observation).__name__}."
            )
        observation_key = _plain_visit_key(observation.visit_key)
        if observation_key in traffic_by_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate traffic observation "
                f"for {_visit_text(observation_key)}."
            )
        traffic_by_key[observation_key] = observation
    candidate_identity = _candidate_identity(node_name, buyers_sorted)
    ordered_candidate_keys, candidate_visit_ranks = _baseline_local_ranks(
        candidate_visit_node.candidate_visits, node_name, timestep
    )
    post_trade_local_ranks = _post_trade_local_ranks(
        trade_result,
        ordered_candidate_keys,
        node_name,
        timestep,
        candidate_identity,
    )
    _require_same_population_and_continuous_local_ranks(
        ordered_candidate_keys,
        candidate_visit_ranks,
        post_trade_local_ranks,
        node_name,
        timestep,
        candidate_identity,
    )
    if right_of_entry_node.right_of_entry_visit_key is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right_of_entry_visit_key is missing."
        )
    right_of_entry_key = _plain_visit_key(right_of_entry_node.right_of_entry_visit_key)
    if right_of_entry_key not in candidate_visit_ranks:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry "
            f"{_visit_text(right_of_entry_key)} is not in candidate_visits."
        )
    right_snapshot = _collector_snapshot(
        columns["collector"], timestep, node_name, right_of_entry_key
    )
    parties = _build_parties(
        world,
        timestep,
        node_name,
        candidate_identity,
        binding_sequence.trade_scope_of_this_candidate_visits,
        trade_result,
        selected_economic,
        payment_node,
        traffic_by_key,
        candidate_visit_ranks,
        post_trade_local_ranks,
        columns["collector"],
        right_of_entry_key,
    )
    for party in parties:
        if party["role"] == "buyer" or party["role"] == "seller":
            if party["baseline_arrival_timestep"] is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{party['visit_key']} is missing baseline arrival A."
                )
    violation_count = _annotate_same_inlink_fifo(parties)
    fifo_summary = _fifo_candidate_summary(concrete_node, fifo_node, node_name, timestep)
    nonparticipating_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.nonparticipating_visits_sorted
    )
    baseline_order = sorted(parties, key=lambda party: party["baseline_local_rank"])
    candidate_order = sorted(parties, key=lambda party: party["post_trade_local_rank"])
    candidate_baseline_arrival_by_visit = {}
    candidate_inlink_by_visit = {}
    for candidate_visit in candidate_visit_node.candidate_visits:
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in candidate_baseline_arrival_by_visit:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits repeats "
                f"{_visit_text(visit_key)} while saving baseline arrival A."
            )
        candidate_baseline_arrival_by_visit[visit_key] = (
            candidate_visit.baseline_arrival_timestep
        )
        candidate_inlink_by_visit[visit_key] = candidate_visit.inlink_name
    traffic_passage_by_visit = {}
    for observation_key, observation in traffic_by_key.items():
        traffic_passage_by_visit[observation_key] = {
            "baseline_passage_timestep": observation.baseline_passage_timestep,
            "candidate_passage_timestep": observation.candidate_passage_timestep,
        }
    reasons = []
    for reason in selected_economic.infeasibility_reasons:
        reasons.append(reason.value)
    decision = {
        "decision_timestep": timestep,
        "node_name": node_name,
        "candidate_identity": candidate_identity,
        "buyers_sorted": buyers_sorted,
        "right_of_entry_visit_key": _visit_text(right_of_entry_key),
        "right_of_entry_vehicle_name": right_of_entry_key[0],
        "right_of_entry_baseline_arrival_timestep": right_snapshot[
            "baseline_arrival_timestep"
        ],
        "right_of_entry_baseline_rank": candidate_visit_ranks[right_of_entry_key],
        "right_of_entry_is_selected_seller": right_of_entry_key in sellers_sorted,
        "buyer_count": len(buyers_sorted),
        "seller_count": len(sellers_sorted),
        "nonparticipating_count": len(nonparticipating_sorted),
        "trade_scope_count": len(parties),
        "buyer_visit_keys": _join_visit_keys(buyers_sorted),
        "seller_visit_keys": _join_visit_keys(sellers_sorted),
        "nonparticipating_visit_keys": _join_visit_keys(nonparticipating_sorted),
        "baseline_order_visit_keys": _join_visit_keys(
            party["visit_key_tuple"] for party in baseline_order
        ),
        "candidate_order_visit_keys": _join_visit_keys(
            party["visit_key_tuple"] for party in candidate_order
        ),
        "total_G": selected_economic.total_buyer_value_G,
        "total_R": selected_economic.total_required_compensation_R,
        "surplus": selected_economic.surplus,
        "economically_feasible": selected_economic.economically_feasible,
        "infeasibility_reasons": "|".join(reasons),
        "selected": True,
        "fifo_inspection_passed": True,
        "fifo_violation_count": violation_count,
        "trade_ex_post_evaluation_status": None,
        "actual_evaluation_available": None,
        "t582_unavailable_contract_consistent": None,
        "parties": parties,
        "contract_failures": [],
        "baseline_local_rank_by_visit": candidate_visit_ranks,
        "post_trade_local_rank_by_visit": post_trade_local_ranks,
        "candidate_baseline_arrival_by_visit": candidate_baseline_arrival_by_visit,
        "candidate_inlink_by_visit": candidate_inlink_by_visit,
        "traffic_passage_by_visit": traffic_passage_by_visit,
        "baseline_collector": columns["collector"],
    }
    decision.update(fifo_summary)
    decision["selected_candidate_was_fifo_passed"] = True
    GATE.decisions[decision_key] = decision
    if decision_key == EAST_T35_AUDIT_KEY:
        GATE.east_t35_audit_rows = _build_east_t35_all_candidate_audit(
            world,
            timestep,
            node_name,
            concrete_node,
            trade_node,
            fifo_node,
            local_node,
            economic_node,
            selection_node,
            payment_node,
            candidate_visit_node,
            right_of_entry_node,
            columns["collector"],
        )
        _require_east_t35_audit_selected_identity(decision)


def _capture_target_decision(world, result) -> None:
    timestep = world.T
    if type(timestep) is not int:
        raise RuntimeError(f"Driver World.T is not an int: {timestep!r}.")
    target_nodes = []
    for node_name, target_timestep in TARGET_DECISION_KEYS:
        if target_timestep == timestep:
            target_nodes.append(node_name)
    if len(target_nodes) == 0:
        return
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(
            f"T={timestep}: driver result is {type(result).__name__}."
        )
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(f"T={timestep}: atomic_apply_set_result is None.")
    columns = _saved_driver_columns(atomic)
    for node_name in target_nodes:
        _capture_target_node(world, columns, node_name, timestep)


def wrapped_run_tvt_mp_driver(world):
    result = GATE.original_run_tvt_mp_driver(world)
    if world is not GATE.real_world:
        return result
    timestep = world.T
    if type(timestep) is int and any(
        target_timestep == timestep for _node_name, target_timestep in TARGET_DECISION_KEYS
    ):
        _capture_target_decision(world, result)
    return result


def install_driver_hook() -> None:
    if GATE.installed:
        raise RuntimeError("Driver observation hook is already installed.")
    GATE.original_run_tvt_mp_driver = driver_module.run_tvt_mp_driver
    GATE.original_record_order_control_node_arrival = (
        uxsim_module.Vehicle.record_order_control_node_arrival
    )
    GATE.original_transfer_tvt_mp_passage_attempts = (
        physical_transfer_module.transfer_tvt_mp_passage_attempts
    )
    GATE.original_inlink_physical_head_should_skip = (
        physical_transfer_module._inlink_physical_head_should_skip
    )
    GATE.original_first_ordinary_physical_shortage = (
        physical_transfer_module._first_ordinary_physical_shortage
    )
    GATE.original_order_control_clearance_blocks_passage = (
        uxsim_module.Node._order_control_clearance_blocks_passage
    )
    GATE.original_transfer_one_vehicle_between_links = (
        uxsim_module.Node._transfer_one_vehicle_between_links
    )
    driver_module.run_tvt_mp_driver = wrapped_run_tvt_mp_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = (
        _wrapped_record_order_control_node_arrival
    )
    physical_transfer_module.transfer_tvt_mp_passage_attempts = (
        _wrapped_transfer_tvt_mp_passage_attempts
    )
    physical_transfer_module._inlink_physical_head_should_skip = (
        _wrapped_inlink_physical_head_should_skip
    )
    physical_transfer_module._first_ordinary_physical_shortage = (
        _wrapped_first_ordinary_physical_shortage
    )
    uxsim_module.Node._order_control_clearance_blocks_passage = (
        _wrapped_order_control_clearance_blocks_passage
    )
    uxsim_module.Node._transfer_one_vehicle_between_links = (
        _wrapped_transfer_one_vehicle_between_links
    )
    GATE.installed = True


def restore_driver_hook() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_run_tvt_mp_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = (
        GATE.original_record_order_control_node_arrival
    )
    physical_transfer_module.transfer_tvt_mp_passage_attempts = (
        GATE.original_transfer_tvt_mp_passage_attempts
    )
    physical_transfer_module._inlink_physical_head_should_skip = (
        GATE.original_inlink_physical_head_should_skip
    )
    physical_transfer_module._first_ordinary_physical_shortage = (
        GATE.original_first_ordinary_physical_shortage
    )
    uxsim_module.Node._order_control_clearance_blocks_passage = (
        GATE.original_order_control_clearance_blocks_passage
    )
    uxsim_module.Node._transfer_one_vehicle_between_links = (
        GATE.original_transfer_one_vehicle_between_links
    )
    GATE.original_run_tvt_mp_driver = None
    GATE.original_record_order_control_node_arrival = None
    GATE.original_transfer_tvt_mp_passage_attempts = None
    GATE.original_inlink_physical_head_should_skip = None
    GATE.original_first_ordinary_physical_shortage = None
    GATE.original_order_control_clearance_blocks_passage = None
    GATE.original_transfer_one_vehicle_between_links = None
    GATE.physical_trace_active = None
    GATE.installed = False


def _find_research_transaction(bundle, decision):
    found = None
    for row in bundle.transactions:
        if not isinstance(row, OrderControlTvtMpResearchOutputTransactionRow):
            raise RuntimeError(f"Research transaction row is {type(row).__name__}.")
        if row.tvt_decision_timestep != decision["decision_timestep"]:
            continue
        if row.node_name != decision["node_name"]:
            continue
        buyers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in row.buyers_sorted)
        if buyers_sorted != decision["buyers_sorted"]:
            continue
        if found is not None:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                "two research transaction rows match the selected buyers."
            )
        found = row
    return found


def _research_visits_by_key(bundle, decision) -> dict:
    found = {}
    for row in bundle.visits:
        if not isinstance(row, OrderControlTvtMpResearchOutputVisitRow):
            raise RuntimeError(f"Research visit row is {type(row).__name__}.")
        if row.tvt_decision_timestep != decision["decision_timestep"]:
            continue
        if row.node_name != decision["node_name"]:
            continue
        buyers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in row.buyers_sorted)
        if buyers_sorted != decision["buyers_sorted"]:
            continue
        visit_key = (row.vehicle_name, row.visit_id)
        if visit_key in found:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"duplicate research visit {_visit_text(visit_key)}."
            )
        found[visit_key] = row
    return found


def _attach_research_output(bundle) -> None:
    for decision in GATE.decisions.values():
        transaction = _find_research_transaction(bundle, decision)
        label = _decision_label(decision["node_name"], decision["decision_timestep"])
        if transaction is None:
            decision["contract_failures"].append(
                f"{label}: research output has no transaction for the selected buyers."
            )
            continue
        decision["trade_ex_post_evaluation_status"] = (
            transaction.trade_ex_post_evaluation_status
        )
        decision["buyer_actual_declared_time_saving_value_total"] = (
            transaction.buyer_actual_declared_time_saving_value_total
        )
        decision["seller_actual_required_compensation_total"] = (
            transaction.seller_actual_required_compensation_total
        )
        status = transaction.trade_ex_post_evaluation_status
        decision["actual_evaluation_available"] = status != EVALUATION_UNAVAILABLE
        visits = _research_visits_by_key(bundle, decision)
        for party in decision["parties"]:
            visit_row = visits.get(party["visit_key_tuple"])
            if visit_row is None:
                decision["contract_failures"].append(
                    f"{label}: research output has no visit row for {party['visit_key']}."
                )
                continue
            if visit_row.role != party["role"]:
                decision["contract_failures"].append(
                    f"{label}: research role {visit_row.role!r} does not match "
                    f"{party['role']!r} for {party['visit_key']}."
                )
            if (
                visit_row.baseline_passage_timestep is not None
                and visit_row.baseline_passage_timestep != party["baseline_passage_timestep"]
            ):
                decision["contract_failures"].append(
                    f"{label}: research baseline passage disagrees for {party['visit_key']}."
                )
            if (
                visit_row.candidate_passage_timestep is not None
                and visit_row.candidate_passage_timestep != party["candidate_passage_timestep"]
            ):
                decision["contract_failures"].append(
                    f"{label}: research candidate passage disagrees for {party['visit_key']}."
                )
            party["actual_passage_timestep"] = visit_row.actual_passage_timestep
            party["predicted_observation_status"] = visit_row.predicted_observation_status
            party["actual_observation_status"] = visit_row.actual_observation_status
            party["research_output_actual_node_passage_rank"] = (
                visit_row.actual_node_passage_rank
            )
            party["realized_gain"] = visit_row.realized_gain
            party["realized_delay_loss"] = visit_row.realized_delay_loss
            party["satisfaction_status"] = visit_row.satisfaction_status
            if party["true_vot_per_second"] != visit_row.true_vot_per_second:
                decision["contract_failures"].append(
                    f"{label}: research true VOT disagrees for {party['visit_key']}."
                )
            if (
                party["declared_vot_per_second"] is None
                and visit_row.declared_vot_per_second is not None
            ):
                party["declared_vot_per_second"] = visit_row.declared_vot_per_second


def _attach_node_continuous_ranks(world) -> None:
    """Read Node-continuous candidate and actual ranks from the real World.

    assigned_rank comes from OrderControlTvtNodeRankState. For a buyer or
    seller it must match ledger_assigned_rank on that visit's establishment
    record. actual_node_passage_rank comes from the stored passage history.
    Unobserved visits stay None. These two ranks are not required to match,
    and neither is treated as a local rank.
    """
    history_by_node = {}
    for decision in GATE.decisions.values():
        node_name = decision["node_name"]
        timestep = decision["decision_timestep"]
        if node_name not in history_by_node:
            history_by_node[node_name] = _actual_passage_ranks_in_stored_order(
                world, node_name
            )
        actual_ranks = history_by_node[node_name]
        for party in decision["parties"]:
            visit_key = party["visit_key_tuple"]
            assigned_rank = _require_ledger_assigned_rank(
                world, node_name, timestep, visit_key
            )
            establishment = _establishment_record(world, timestep, node_name, visit_key)
            if party["role"] == "buyer" or party["role"] == "seller":
                if establishment is None:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"{party['visit_key']} has no establishment record for "
                        "the ledger_assigned_rank check."
                    )
                ledger_assigned_rank = _require_python_int_rank(
                    establishment.ledger_assigned_rank,
                    "ledger_assigned_rank",
                    node_name,
                    timestep,
                    visit_key,
                )
                if ledger_assigned_rank != assigned_rank:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"ledger_assigned_rank {ledger_assigned_rank} for "
                        f"{party['visit_key']} does not match rank-ledger "
                        f"assigned_rank {assigned_rank}."
                    )
            elif establishment is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: nonparticipating "
                    f"{party['visit_key']} has an establishment record."
                )
            if visit_key in actual_ranks:
                actual_rank = actual_ranks[visit_key]
                if type(actual_rank) is not int or actual_rank < 1:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"actual_node_passage_rank for {party['visit_key']} "
                        f"is {actual_rank!r}."
                    )
            else:
                actual_rank = None
            research_rank = party.get("research_output_actual_node_passage_rank")
            if "research_output_actual_node_passage_rank" in party:
                if research_rank != actual_rank:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: research output "
                        f"actual_node_passage_rank {research_rank!r} for "
                        f"{party['visit_key']} does not match the passage "
                        f"history rank {actual_rank!r}."
                    )
            party["assigned_rank"] = assigned_rank
            party["actual_node_passage_rank"] = actual_rank


def _expected_unobserved_parties_present(decision) -> bool:
    roles = {}
    for party in decision["parties"]:
        roles[(party["role"], party["visit_key_tuple"])] = party
    for role_name, visit_key in T582_EXPECTED_UNOBSERVED_PARTIES:
        if (role_name, visit_key) not in roles:
            return False
    return True


def _collect_end_errors() -> list[str]:
    errors = []
    for decision_key in TARGET_DECISION_KEYS:
        if decision_key not in GATE.decisions:
            errors.append(f"{_decision_label(*decision_key)} was not observed.")
    for decision_key in TARGET_DECISION_KEYS:
        decision = GATE.decisions.get(decision_key)
        if decision is None:
            continue
        label = _decision_label(decision["node_name"], decision["decision_timestep"])
        expected_counts = EXPECTED_BUYER_SELLER_COUNTS[decision_key]
        measured = (decision["buyer_count"], decision["seller_count"])
        if measured != expected_counts:
            errors.append(
                f"{label}: measured buyer/seller counts {measured} differ from "
                f"expected {expected_counts}. Measured parties were kept: "
                f"buyers={decision['buyer_visit_keys']} sellers={decision['seller_visit_keys']}."
            )
        if decision["fifo_violation_count"] != 0:
            errors.append(
                f"{label}: same-inlink FIFO violation count is "
                f"{decision['fifo_violation_count']}."
            )
        if decision["selected_candidate_was_fifo_passed"] is not True:
            errors.append(f"{label}: selected candidate was not FIFO-passed.")
        if decision["right_of_entry_baseline_arrival_timestep"] is None:
            errors.append(f"{label}: right-of-entry baseline arrival A is missing.")
        if decision["right_of_entry_baseline_rank"] is None:
            errors.append(f"{label}: right-of-entry baseline rank is missing.")
        status = decision["trade_ex_post_evaluation_status"]
        for party in decision["parties"]:
            if party["baseline_arrival_timestep"] is None:
                errors.append(f"{label}: {party['visit_key']} is missing baseline A.")
            if party["baseline_passage_timestep"] is None:
                errors.append(f"{label}: {party['visit_key']} is missing baseline passage.")
            if party["candidate_passage_timestep"] is None:
                errors.append(f"{label}: {party['visit_key']} is missing candidate passage.")
            observation = party["actual_observation_status"]
            actual_passage = party["actual_passage_timestep"]
            actual_rank = party["actual_node_passage_rank"]
            if actual_rank == 0 or type(actual_rank) is bool:
                errors.append(
                    f"{label}: {party['visit_key']} actual_node_passage_rank "
                    f"is {actual_rank!r}."
                )
            if observation == ACTUAL_UNOBSERVED:
                if actual_passage is not None:
                    errors.append(
                        f"{label}: {party['visit_key']} is unobserved but has actual passage."
                    )
                if actual_rank is not None:
                    errors.append(
                        f"{label}: {party['visit_key']} is unobserved but "
                        "actual_node_passage_rank is not empty."
                    )
            elif observation is None:
                errors.append(f"{label}: {party['visit_key']} has no actual observation status.")
            elif actual_passage is None:
                errors.append(
                    f"{label}: {party['visit_key']} is observed but actual passage is missing."
                )
            elif type(actual_rank) is not int or actual_rank < 1:
                errors.append(
                    f"{label}: {party['visit_key']} is observed but "
                    f"actual_node_passage_rank is {actual_rank!r}."
                )
            if type(party["assigned_rank"]) is not int or party["assigned_rank"] < 1:
                errors.append(
                    f"{label}: {party['visit_key']} assigned_rank is "
                    f"{party['assigned_rank']!r}."
                )
        if decision_key != T582_KEY:
            if status == EVALUATION_UNAVAILABLE:
                errors.append(
                    f"{label}: trade_ex_post_evaluation_status is evaluation_unavailable."
                )
            decision["t582_unavailable_contract_consistent"] = None
            continue
        predicted_complete = True
        for party in decision["parties"]:
            if party["role"] == "buyer" and party["buyer_value_G_b"] is None:
                predicted_complete = False
            if party["role"] == "seller" and party["seller_required_compensation_R_s"] is None:
                predicted_complete = False
        totals_none = (
            decision.get("buyer_actual_declared_time_saving_value_total") is None
            and decision.get("seller_actual_required_compensation_total") is None
        )
        same_parties = _expected_unobserved_parties_present(decision)
        unobserved_ok = False
        if same_parties:
            unobserved_ok = True
            roles = {
                (party["role"], party["visit_key_tuple"]): party
                for party in decision["parties"]
            }
            for role_name, visit_key in T582_EXPECTED_UNOBSERVED_PARTIES:
                party = roles[(role_name, visit_key)]
                if party["actual_observation_status"] != ACTUAL_UNOBSERVED:
                    unobserved_ok = False
                if party["actual_passage_timestep"] is not None:
                    unobserved_ok = False
        else:
            errors.append(
                f"{label}: selected parties differ from the post-fix unobserved-party "
                "contract. Measured composition was kept: "
                f"buyers={decision['buyer_visit_keys']} sellers={decision['seller_visit_keys']}."
            )
        consistent = (
            status == EVALUATION_UNAVAILABLE
            and totals_none
            and predicted_complete
            and same_parties
            and unobserved_ok
        )
        decision["t582_unavailable_contract_consistent"] = consistent
        if status != EVALUATION_UNAVAILABLE:
            errors.append(
                f"{label}: expected evaluation_unavailable, measured status is {status!r}. "
                "Measured economics were kept."
            )
        if totals_none is not True:
            errors.append(
                f"{label}: evaluation_unavailable requires transaction-level actual "
                "buyer value and seller compensation totals to be None."
            )
        if predicted_complete is not True:
            errors.append(f"{label}: a predicted G_b or R_s value is missing.")
        if same_parties and unobserved_ok is not True:
            errors.append(
                f"{label}: veh_es_83:1 or veh_en_74:1 is not actual-passage unobserved."
            )
        errors.extend(decision["contract_failures"])
    for decision_key, decision in GATE.decisions.items():
        if decision_key in TARGET_DECISION_KEYS and decision_key != T582_KEY:
            errors.extend(decision["contract_failures"])
    return errors


def _saved_party_inlink_name(node_name: str, visit_key):
    """Inlink saved on a selected party for this Node and VisitKey, if any.

    The rank ledger and the actual passage history do not store inlink.
    The vehicle's link at evaluation end is not the inlink of this passage,
    so it is not used. When no selected party saved this VisitKey, the cell
    stays empty.
    """
    found = None
    for decision_key in TARGET_DECISION_KEYS:
        decision = GATE.decisions.get(decision_key)
        if decision is None or decision["node_name"] != node_name:
            continue
        for party in decision["parties"]:
            if party["visit_key_tuple"] != visit_key:
                continue
            inlink_name = party["inlink_name"]
            if not isinstance(inlink_name, str) or inlink_name == "":
                raise RuntimeError(
                    f"Node {node_name}: saved party {_visit_text(visit_key)} "
                    f"has inlink_name {inlink_name!r}."
                )
            if found is None:
                found = inlink_name
            elif found != inlink_name:
                raise RuntimeError(
                    f"Node {node_name}: saved inlink for {_visit_text(visit_key)} "
                    f"disagrees: {found!r} versus {inlink_name!r}."
                )
    return found


def _rank_relation_note(assigned_rank, actual_rank: int | None) -> str:
    if assigned_rank is None and actual_rank is None:
        raise RuntimeError(
            "A context visit has neither assigned_rank nor actual_node_passage_rank."
        )
    if assigned_rank is None:
        return "actual_only_no_assigned_rank"
    if actual_rank is None:
        return "assigned_only_actual_unobserved"
    if actual_rank == assigned_rank:
        return "exact_match"
    if actual_rank < assigned_rank:
        return "actual_earlier_than_assigned"
    return "actual_later_than_assigned"


def _rank_falls_inside(rank_value, lower_rank: int, upper_rank: int) -> bool:
    if rank_value is None:
        return False
    if rank_value < lower_rank:
        return False
    if rank_value > upper_rank:
        return False
    return True


def _mismatch_rank_bounds(assigned_rank: int, actual_rank: int):
    """Window around the two unequal Node-continuous ranks.

    The closed mismatch span is the smaller rank through the larger rank.
    The context window extends two ranks outside that span and never below 1.
    """
    smaller_rank = assigned_rank
    if actual_rank < smaller_rank:
        smaller_rank = actual_rank
    larger_rank = assigned_rank
    if actual_rank > larger_rank:
        larger_rank = actual_rank
    lower_rank = smaller_rank - CONTEXT_RANK_PADDING
    if lower_rank < 1:
        lower_rank = 1
    upper_rank = larger_rank + CONTEXT_RANK_PADDING
    return lower_rank, upper_rank, smaller_rank, larger_rank


def _load_node_continuous_rank_sides(world, node_name: str) -> dict:
    """Read one Node's ledger and its stored actual passage history.

    assigned_rank and the formal route come from OrderControlTvtNodeRankState.
    actual rank, passage timestep, and actual route come from the history
    record. History is walked in stored order by
    _actual_passage_records_in_stored_order. Neither side is sorted here.
    """
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict) or node_name not in states:
        raise RuntimeError(
            f"Node {node_name}: real World has no OrderControlTvtNodeRankState."
        )
    rank_state = states[node_name]
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(
            f"Node {node_name}: rank state is {type(rank_state).__name__}."
        )
    if rank_state.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name}: rank state node_name is {rank_state.node_name!r}."
        )
    assigned_by_visit = {}
    formal_route_by_visit = {}
    ledger_order = []
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain_visit_key = _plain_visit_key(visit_key)
        if plain_visit_key in assigned_by_visit:
            raise RuntimeError(
                f"Node {node_name}: rank ledger repeats {_visit_text(plain_visit_key)}."
            )
        assigned_rank = rank_state.assigned_rank(plain_visit_key)
        if type(assigned_rank) is not int or assigned_rank < 1:
            raise RuntimeError(
                f"Node {node_name}: ledger assigned_rank for "
                f"{_visit_text(plain_visit_key)} is {assigned_rank!r}."
            )
        formal_route = rank_state.formal_route_next_link_name(plain_visit_key)
        if formal_route is not None and (
            not isinstance(formal_route, str) or formal_route == ""
        ):
            raise RuntimeError(
                f"Node {node_name}: formal_route_next_link_name for "
                f"{_visit_text(plain_visit_key)} is {formal_route!r}."
            )
        assigned_by_visit[plain_visit_key] = assigned_rank
        formal_route_by_visit[plain_visit_key] = formal_route
        ledger_order.append(plain_visit_key)
    history_records = _actual_passage_records_in_stored_order(world, node_name)
    actual_by_visit = {}
    for record in history_records:
        visit_key = _plain_visit_key(record.visit_key)
        actual_by_visit[visit_key] = record
    return {
        "ledger_order": tuple(ledger_order),
        "assigned_by_visit": assigned_by_visit,
        "formal_route_by_visit": formal_route_by_visit,
        "history_records": history_records,
        "actual_by_visit": actual_by_visit,
    }


def _context_visit_row(
    mismatch: dict,
    visit_key,
    sides: dict,
    smaller_rank: int,
    larger_rank: int,
) -> dict:
    assigned_rank = sides["assigned_by_visit"].get(visit_key)
    actual_record = sides["actual_by_visit"].get(visit_key)
    if actual_record is None:
        actual_rank = None
        actual_passage_timestep = None
        actual_route_next_link_name = None
    else:
        actual_rank = actual_record.actual_node_passage_rank
        actual_passage_timestep = actual_record.actual_passage_timestep
        actual_route_next_link_name = actual_record.actual_route_next_link_name
    assigned_inside = _rank_falls_inside(assigned_rank, smaller_rank, larger_rank)
    actual_inside = _rank_falls_inside(actual_rank, smaller_rank, larger_rank)
    return {
        "mismatch_decision_timestep": mismatch["decision_timestep"],
        "mismatch_node_name": mismatch["node_name"],
        "mismatch_visit_key": _visit_text(mismatch["visit_key"]),
        "mismatch_assigned_rank": mismatch["assigned_rank"],
        "mismatch_actual_node_passage_rank": mismatch["actual_node_passage_rank"],
        "context_visit_key": _visit_text(visit_key),
        "vehicle_name": visit_key[0],
        "visit_id": visit_key[1],
        "assigned_rank": assigned_rank,
        "actual_node_passage_rank": actual_rank,
        "actual_passage_timestep": actual_passage_timestep,
        "formal_route_next_link_name": sides["formal_route_by_visit"].get(visit_key),
        "actual_route_next_link_name": actual_route_next_link_name,
        "inlink_name": _saved_party_inlink_name(mismatch["node_name"], visit_key),
        "is_mismatch_visit": visit_key == mismatch["visit_key"],
        "is_between_mismatch_ranks": assigned_inside or actual_inside,
        "rank_relation_note": _rank_relation_note(assigned_rank, actual_rank),
    }


def _context_visit_keys_in_saved_order(sides: dict, lower_rank: int, upper_rank: int):
    """Ledger order first, then history-only visits in stored history order."""
    selected = []
    already_selected = {}
    for visit_key in sides["ledger_order"]:
        assigned_rank = sides["assigned_by_visit"][visit_key]
        actual_record = sides["actual_by_visit"].get(visit_key)
        actual_rank = None
        if actual_record is not None:
            actual_rank = actual_record.actual_node_passage_rank
        assigned_inside = _rank_falls_inside(assigned_rank, lower_rank, upper_rank)
        actual_inside = _rank_falls_inside(actual_rank, lower_rank, upper_rank)
        if assigned_inside or actual_inside:
            selected.append(visit_key)
            already_selected[visit_key] = True
    for record in sides["history_records"]:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in already_selected:
            continue
        if _rank_falls_inside(record.actual_node_passage_rank, lower_rank, upper_rank):
            selected.append(visit_key)
            already_selected[visit_key] = True
    return tuple(selected)


def _selected_node_continuous_rank_mismatches() -> list[dict]:
    """Selected parties whose two Node-continuous ranks both exist and differ."""
    mismatches = []
    for decision_key in TARGET_DECISION_KEYS:
        decision = GATE.decisions.get(decision_key)
        if decision is None:
            continue
        for party in decision["parties"]:
            assigned_rank = party["assigned_rank"]
            actual_rank = party["actual_node_passage_rank"]
            if assigned_rank is None or actual_rank is None:
                continue
            if type(assigned_rank) is not int or type(actual_rank) is not int:
                raise RuntimeError(
                    f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                    f"{party['visit_key']} Node-continuous ranks are "
                    f"{assigned_rank!r} and {actual_rank!r}."
                )
            if assigned_rank == actual_rank:
                continue
            mismatches.append(
                {
                    "decision_timestep": decision["decision_timestep"],
                    "node_name": decision["node_name"],
                    "visit_key": party["visit_key_tuple"],
                    "assigned_rank": assigned_rank,
                    "actual_node_passage_rank": actual_rank,
                }
            )
    return mismatches


def _build_node_continuous_rank_mismatch_context(world) -> list[dict]:
    """Nearby ledger and history visits for each unequal Node-continuous pair.

    No VisitKey, rank, or passage time is fixed in this search. Zero mismatches
    produce no rows; the caller still writes the header.
    """
    mismatches = _selected_node_continuous_rank_mismatches()
    sides_by_node = {}
    rows = []
    for mismatch in mismatches:
        node_name = mismatch["node_name"]
        if node_name not in sides_by_node:
            sides_by_node[node_name] = _load_node_continuous_rank_sides(world, node_name)
        sides = sides_by_node[node_name]
        lower_rank, upper_rank, smaller_rank, larger_rank = _mismatch_rank_bounds(
            mismatch["assigned_rank"],
            mismatch["actual_node_passage_rank"],
        )
        visit_keys = _context_visit_keys_in_saved_order(sides, lower_rank, upper_rank)
        for visit_key in visit_keys:
            rows.append(
                _context_visit_row(
                    mismatch,
                    visit_key,
                    sides,
                    smaller_rank,
                    larger_rank,
                )
            )
    return rows


def _visit_key_from_text(text: str):
    if not isinstance(text, str):
        raise RuntimeError(f"Visit text is not a string: {text!r}.")
    separator = text.rfind(":")
    if separator <= 0:
        raise RuntimeError(f"Visit text has no vehicle/visit separator: {text!r}.")
    vehicle_name = text[:separator]
    visit_id_text = text[separator + 1 :]
    if vehicle_name == "" or visit_id_text.isdigit() is not True:
        raise RuntimeError(f"Visit text is not vehicle_name:visit_id: {text!r}.")
    return (vehicle_name, int(visit_id_text))


def _stored_actual_node_arrival(node_name: str, visit_key):
    """First real-world incoming registration timestep, or None.

    The value comes only from the arrival observation filled when production
    registers the Visit on the real World. It is not baseline arrival A, not
    earliest arrival, and not a passage timestep shifted backward.
    """
    key = (node_name, visit_key[0], visit_key[1])
    if key not in GATE.actual_node_arrivals:
        return None
    arrival = GATE.actual_node_arrivals[key]
    if type(arrival) is not int or arrival < 0:
        raise RuntimeError(
            f"Node {node_name}: stored actual arrival for {_visit_text(visit_key)} "
            f"is {arrival!r}."
        )
    return arrival


def _require_actual_passage_follows_arrival(
    node_name: str,
    visit_key,
    actual_arrival,
    actual_passage,
) -> None:
    """Stop when a stored arrival does not precede actual passage.

    In exec_simulation the timestep body runs Node.transfer before
    Vehicle.update. record_order_control_node_arrival runs from that update,
    when the vehicle is appended to incoming_vehicles. A visit registered at
    timestep T can therefore pass on a later timestep only. The earliest
    passage is T + 1.
    """
    if actual_arrival is None or actual_passage is None:
        return
    if type(actual_arrival) is not int or type(actual_passage) is not int:
        raise RuntimeError(
            f"Node {node_name}: arrival/passage types for {_visit_text(visit_key)} "
            f"are {actual_arrival!r} and {actual_passage!r}."
        )
    if actual_arrival < 0 or actual_passage < 0:
        raise RuntimeError(
            f"Node {node_name}: arrival/passage for {_visit_text(visit_key)} "
            f"are {actual_arrival!r} and {actual_passage!r}."
        )
    if actual_passage < actual_arrival + 1:
        raise RuntimeError(
            f"Node {node_name}: {_visit_text(visit_key)} actual passage "
            f"{actual_passage} is not after actual node arrival {actual_arrival}. "
            "Node.transfer runs before Vehicle.update in the same timestep, so "
            "the arrival registration cannot be passed until a later timestep."
        )


def _remember_real_world_node_arrival(vehicle, node) -> None:
    """Copy the first real-world arrival timestep after production records it.

    Production is not called again here. A copied World is ignored. The same
    Node and VisitKey is stored once. order_control_node_arrival_times is not
    read: that dictionary keeps one time per Node name, not per Visit.
    """
    if vehicle.W is not GATE.real_world:
        return
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        return
    if current_visit.get("node") is not node:
        return
    arrival_time = current_visit.get("arrival_time")
    if arrival_time is None:
        return
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} arrival visit_id "
            f"is {visit_id!r}."
        )
    key = (node.name, vehicle.name, visit_id)
    if key in GATE.actual_node_arrivals:
        return
    timestep = vehicle.W.T
    if type(timestep) is not int or timestep < 0:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} arrival World.T "
            f"is {timestep!r}."
        )
    converted = int(round(arrival_time / vehicle.W.DELTAT))
    if converted != timestep:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} visit {visit_id} "
            f"arrival_time converts to {converted}, but World.T is {timestep}."
        )
    GATE.actual_node_arrivals[key] = timestep


def _wrapped_record_order_control_node_arrival(vehicle, node):
    result = GATE.original_record_order_control_node_arrival(vehicle, node)
    _remember_real_world_node_arrival(vehicle, node)
    return result


def _physical_trace_window_applies(node) -> bool:
    """True only for the real World's time_value transfer inside the fixed window."""
    if node.W is not GATE.real_world:
        return False
    collector = getattr(node.W, "_order_control_baseline_collector", None)
    if collector is not None:
        return False
    if node.order_control_eligible is not True:
        return False
    if node.order_control_type != "time_value":
        return False
    timestep = node.W.T
    if type(timestep) is not int:
        return False
    if timestep < PHYSICAL_TRACE_TIMESTEP_START:
        return False
    if timestep > PHYSICAL_TRACE_TIMESTEP_END:
        return False
    return True


def _assigned_rank_now(node_name: str, visit_key):
    world = GATE.real_world
    if world is None:
        return None
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return None
    rank_state = states.get(node_name)
    if rank_state is None:
        return None
    return rank_state.assigned_rank(visit_key)


def _ensure_trace_event(active, vehicle):
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        return None
    visit_key = (vehicle.name, visit_id)
    existing = active["events"].get(visit_key)
    if existing is not None:
        return existing
    inlink_name = None
    if vehicle.link is not None:
        inlink_name = vehicle.link.name
    outlink_name = None
    if vehicle.route_next_link is not None:
        outlink_name = vehicle.route_next_link.name
    event = {
        "node_name": active["node_name"],
        "real_world_timestep": active["timestep"],
        "scan_sequence_index": active["next_sequence_index"],
        "visit_key": visit_key,
        "vehicle_name": vehicle.name,
        "visit_id": visit_id,
        "assigned_rank": _assigned_rank_now(active["node_name"], visit_key),
        "inlink_name": inlink_name,
        "intended_outlink_name": outlink_name,
        "was_arrived_at_node": True,
        "was_already_passed_before_scan": False,
        "was_inlink_physical_head": None,
        "clearance_required_timesteps": None,
        "last_order_control_inlink_name": None,
        "last_order_control_entry_timestep": None,
        "clearance_satisfied": None,
        "inlink_capacity_out_remain_before": None,
        "inlink_outflow_capacity_satisfied": None,
        "node_flow_capacity_remain_before": None,
        "node_flow_capacity_satisfied": None,
        "outlink_capacity_in_remain_before": None,
        "outlink_inflow_capacity_satisfied": None,
        "outlink_entrance_space_available": None,
        "outlink_entrance_space_detail": None,
        "first_blocking_reason": None,
        "action": None,
        "passed_this_scan": False,
        "temporary_skipped": False,
        "clearance_stopped_node_scan": False,
        "actual_passage_timestep_if_passed": None,
        "scan_note": "",
    }
    active["next_sequence_index"] = active["next_sequence_index"] + 1
    active["events"][visit_key] = event
    active["judged_order"].append(visit_key)
    return event


def _note_physical_head(vehicle, inlink, result) -> None:
    active = GATE.physical_trace_active
    if active is None:
        return
    node = inlink.end_node
    if node is None or active["node_name"] != node.name:
        return
    event = _ensure_trace_event(active, vehicle)
    if event is None:
        return
    if result is True:
        event["was_inlink_physical_head"] = False
        event["first_blocking_reason"] = "not_inlink_physical_head"
        event["action"] = "temporary_skip"
        event["temporary_skipped"] = True
        event["passed_this_scan"] = False
        event["scan_note"] = "production inlink physical-head check returned skip"
        return
    event["was_inlink_physical_head"] = True
    event["scan_note"] = "production inlink physical-head check returned continue"


def _note_clearance(node, vehicle, inlink, result) -> None:
    del inlink
    active = GATE.physical_trace_active
    if active is None or active["node_name"] != node.name:
        return
    event = _ensure_trace_event(active, vehicle)
    if event is None:
        return
    event["clearance_required_timesteps"] = node.order_control_clearance_timesteps
    last_inlink = node.last_order_control_inlink
    if last_inlink is None:
        event["last_order_control_inlink_name"] = None
    else:
        event["last_order_control_inlink_name"] = last_inlink.name
    event["last_order_control_entry_timestep"] = node.last_order_control_entry_timestep
    if result is True:
        event["clearance_satisfied"] = False
        event["first_blocking_reason"] = "clearance_not_satisfied"
        event["action"] = "clearance_stop"
        event["clearance_stopped_node_scan"] = True
        event["passed_this_scan"] = False
        event["temporary_skipped"] = False
        active["clearance_stopped"] = True
        event["scan_note"] = "production clearance check stopped the node scan"
        return
    event["clearance_satisfied"] = True


def _current_trace_event(active):
    if len(active["judged_order"]) == 0:
        return None
    visit_key = active["judged_order"][-1]
    return active["events"][visit_key]


def _note_shortage(node, inlink, outlink, before, result) -> None:
    """Record production's shortage string. Do not compare capacities again."""
    del inlink
    active = GATE.physical_trace_active
    if active is None or active["node_name"] != node.name:
        return
    event = _current_trace_event(active)
    if event is None:
        return
    event["inlink_capacity_out_remain_before"] = before["inlink_capacity_out_remain"]
    event["node_flow_capacity_remain_before"] = before["node_flow_capacity_remain"]
    event["outlink_capacity_in_remain_before"] = before["outlink_capacity_in_remain"]
    if event["intended_outlink_name"] is None and outlink is not None:
        event["intended_outlink_name"] = outlink.name
    if result == "inlink_outflow_capacity_unavailable":
        event["inlink_outflow_capacity_satisfied"] = False
        event["first_blocking_reason"] = "inlink_outflow_capacity_insufficient"
        event["action"] = "temporary_skip"
        event["temporary_skipped"] = True
        event["scan_note"] = (
            "production ordinary-limit check returned inlink outflow shortage"
        )
        return
    if result == "node_flow_capacity_unavailable":
        event["inlink_outflow_capacity_satisfied"] = True
        event["node_flow_capacity_satisfied"] = False
        event["first_blocking_reason"] = "node_flow_capacity_insufficient"
        event["action"] = "temporary_skip"
        event["temporary_skipped"] = True
        event["scan_note"] = (
            "production ordinary-limit check returned node flow shortage"
        )
        return
    if result == "outlink_inflow_capacity_unavailable":
        event["inlink_outflow_capacity_satisfied"] = True
        event["node_flow_capacity_satisfied"] = True
        event["outlink_inflow_capacity_satisfied"] = False
        event["first_blocking_reason"] = "outlink_inflow_capacity_insufficient"
        event["action"] = "temporary_skip"
        event["temporary_skipped"] = True
        event["scan_note"] = (
            "production ordinary-limit check returned outlink inflow shortage"
        )
        return
    if result == "outlink_entry_space_unavailable":
        event["inlink_outflow_capacity_satisfied"] = True
        event["node_flow_capacity_satisfied"] = True
        event["outlink_inflow_capacity_satisfied"] = True
        event["outlink_entrance_space_available"] = False
        event["outlink_entrance_space_detail"] = (
            "production returned outlink_entry_space_unavailable; "
            f"outlink_vehicle_count={len(outlink.vehicles)}; "
            f"number_of_lanes={outlink.number_of_lanes}"
        )
        event["first_blocking_reason"] = "outlink_entrance_space_insufficient"
        event["action"] = "temporary_skip"
        event["temporary_skipped"] = True
        event["scan_note"] = (
            "production ordinary-limit check returned outlink entrance shortage"
        )
        return
    if result is None:
        event["inlink_outflow_capacity_satisfied"] = True
        event["node_flow_capacity_satisfied"] = True
        event["outlink_inflow_capacity_satisfied"] = True
        event["outlink_entrance_space_available"] = True
        event["outlink_entrance_space_detail"] = (
            "production ordinary-limit check returned no shortage"
        )
        event["scan_note"] = "production ordinary-limit check returned no shortage"
        return
    event["first_blocking_reason"] = "not_observable"
    event["action"] = "not_present"
    event["scan_note"] = f"production shortage result was {result!r}"


def _passage_identity_before_transfer(node, vehicle, inlink, outlink):
    """Read the VisitKey production is about to transfer.

    This runs only while this node's physical trace is open. The returned
    values are taken before production moves the vehicle. After a successful
    transfer, order_control_current_visit is the next visit and must not be
    read again to name the passed row.
    """
    active = GATE.physical_trace_active
    if active is None or active["node_name"] != node.name:
        return None
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} has no current visit "
            "before passage."
        )
    if current_visit.get("node") is not node:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} current visit node does "
            "not match the passage node."
        )
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} visit_id before passage "
            f"is {visit_id!r}."
        )
    visit_key = (vehicle.name, visit_id)
    event = active["events"].get(visit_key)
    if event is None:
        raise RuntimeError(
            f"Node {node.name}: passage VisitKey {_visit_text(visit_key)} was "
            "not the VisitKey judged in this physical trace."
        )
    timestep = node.W.T
    if type(timestep) is not int:
        raise RuntimeError(
            f"Node {node.name}: passage World.T before transfer is {timestep!r}."
        )
    return {
        "visit_key": visit_key,
        "vehicle_name": vehicle.name,
        "visit_id": visit_id,
        "node_name": node.name,
        "timestep": timestep,
        "inlink_name": inlink.name,
        "outlink_name": outlink.name,
        "assigned_rank": event["assigned_rank"],
    }


def _record_passed_for_saved_visit(saved) -> None:
    """Mark the VisitKey saved before production passage. Do not reread it."""
    active = GATE.physical_trace_active
    if active is None or active["node_name"] != saved["node_name"]:
        raise RuntimeError(
            "Passed trace record has no active physical trace for "
            f"{saved['node_name']!r}."
        )
    visit_key = saved["visit_key"]
    event = active["events"].get(visit_key)
    if event is None:
        raise RuntimeError(
            f"Node {saved['node_name']}: saved passage VisitKey "
            f"{_visit_text(visit_key)} is not in the active trace."
        )
    if event["assigned_rank"] != saved["assigned_rank"]:
        raise RuntimeError(
            f"Node {saved['node_name']}: saved passage rank for "
            f"{_visit_text(visit_key)} changed before the pass was recorded."
        )
    event["first_blocking_reason"] = "none_passed"
    event["action"] = "passed"
    event["passed_this_scan"] = True
    event["temporary_skipped"] = False
    event["clearance_stopped_node_scan"] = False
    event["actual_passage_timestep_if_passed"] = saved["timestep"]
    if event["inlink_name"] is None:
        event["inlink_name"] = saved["inlink_name"]
    if event["intended_outlink_name"] is None:
        event["intended_outlink_name"] = saved["outlink_name"]
    event["scan_note"] = (
        "production transferred the VisitKey saved before the passage call"
    )


def _open_physical_trace(node) -> None:
    if GATE.physical_trace_active is not None:
        raise RuntimeError(
            f"Node {node.name}: physical trace observation is already open."
        )
    incoming_records = []
    seen = {}
    for vehicle in node.incoming_vehicles:
        current_visit = vehicle.order_control_current_visit
        if not isinstance(current_visit, dict):
            continue
        if current_visit.get("node") is not node:
            continue
        visit_id = current_visit.get("visit_id")
        if type(visit_id) is not int:
            continue
        visit_key = (vehicle.name, visit_id)
        if visit_key in seen:
            continue
        seen[visit_key] = True
        inlink_name = None
        if vehicle.link is not None:
            inlink_name = vehicle.link.name
        outlink_name = None
        if vehicle.route_next_link is not None:
            outlink_name = vehicle.route_next_link.name
        incoming_records.append(
            {
                "visit_key": visit_key,
                "inlink_name": inlink_name,
                "intended_outlink_name": outlink_name,
            }
        )
    GATE.physical_trace_active = {
        "node_name": node.name,
        "timestep": node.W.T,
        "incoming_records": incoming_records,
        "events": {},
        "judged_order": [],
        "clearance_stopped": False,
        "next_sequence_index": 1,
    }


def _blank_unjudged_event(active, record):
    visit_key = record["visit_key"]
    event = {
        "node_name": active["node_name"],
        "real_world_timestep": active["timestep"],
        "scan_sequence_index": None,
        "visit_key": visit_key,
        "vehicle_name": visit_key[0],
        "visit_id": visit_key[1],
        "assigned_rank": _assigned_rank_now(active["node_name"], visit_key),
        "inlink_name": record["inlink_name"],
        "intended_outlink_name": record["intended_outlink_name"],
        "was_arrived_at_node": True,
        "was_already_passed_before_scan": False,
        "was_inlink_physical_head": None,
        "clearance_required_timesteps": None,
        "last_order_control_inlink_name": None,
        "last_order_control_entry_timestep": None,
        "clearance_satisfied": None,
        "inlink_capacity_out_remain_before": None,
        "inlink_outflow_capacity_satisfied": None,
        "node_flow_capacity_remain_before": None,
        "node_flow_capacity_satisfied": None,
        "outlink_capacity_in_remain_before": None,
        "outlink_inflow_capacity_satisfied": None,
        "outlink_entrance_space_available": None,
        "outlink_entrance_space_detail": None,
        "first_blocking_reason": None,
        "action": None,
        "passed_this_scan": False,
        "temporary_skipped": False,
        "clearance_stopped_node_scan": False,
        "actual_passage_timestep_if_passed": None,
        "scan_note": "",
    }
    if active["clearance_stopped"] is True:
        event["first_blocking_reason"] = "not_scanned_after_clearance_stop"
        event["action"] = "not_scanned_after_clearance_stop"
        event["clearance_stopped_node_scan"] = True
        event["scan_note"] = (
            "production clearance stop ended the scan before this incoming visit"
        )
        return event
    event["first_blocking_reason"] = "not_observable"
    event["action"] = "not_present"
    event["scan_note"] = (
        "incoming visit was not judged and production did not report a clearance stop"
    )
    return event


def _close_physical_trace(node) -> None:
    active = GATE.physical_trace_active
    GATE.physical_trace_active = None
    if active is None:
        return
    if active["node_name"] != node.name:
        raise RuntimeError(
            f"Node {node.name}: physical trace closed for {active['node_name']!r}."
        )
    for visit_key in active["judged_order"]:
        event = active["events"][visit_key]
        if event["action"] is None:
            if event["intended_outlink_name"] is None:
                event["first_blocking_reason"] = "route_unavailable"
                event["action"] = "not_present"
                event["scan_note"] = (
                    "production did not pass this visit and route_next_link was missing"
                )
            else:
                event["first_blocking_reason"] = "not_observable"
                event["action"] = "not_present"
                event["scan_note"] = (
                    "production did not return a blocking reason or a pass"
                )
        GATE.physical_trace_events.append(event)
    for record in active["incoming_records"]:
        visit_key = record["visit_key"]
        if visit_key in active["events"]:
            continue
        GATE.physical_trace_events.append(_blank_unjudged_event(active, record))


def _wrapped_transfer_tvt_mp_passage_attempts(node):
    trace_this_call = _physical_trace_window_applies(node)
    if trace_this_call:
        _open_physical_trace(node)
    try:
        result = GATE.original_transfer_tvt_mp_passage_attempts(node)
    finally:
        if trace_this_call:
            _close_physical_trace(node)
    return result


def _wrapped_inlink_physical_head_should_skip(vehicle, inlink):
    result = GATE.original_inlink_physical_head_should_skip(vehicle, inlink)
    _note_physical_head(vehicle, inlink, result)
    return result


def _wrapped_first_ordinary_physical_shortage(node, inlink, outlink):
    before = {
        "inlink_capacity_out_remain": inlink.capacity_out_remain,
        "node_flow_capacity_remain": node.flow_capacity_remain,
        "outlink_capacity_in_remain": outlink.capacity_in_remain,
    }
    result = GATE.original_first_ordinary_physical_shortage(node, inlink, outlink)
    _note_shortage(node, inlink, outlink, before, result)
    return result


def _wrapped_order_control_clearance_blocks_passage(node, vehicle, inlink):
    result = GATE.original_order_control_clearance_blocks_passage(
        node, vehicle, inlink
    )
    _note_clearance(node, vehicle, inlink, result)
    return result


def _wrapped_transfer_one_vehicle_between_links(node, vehicle, inlink, outlink):
    saved = _passage_identity_before_transfer(node, vehicle, inlink, outlink)
    result = GATE.original_transfer_one_vehicle_between_links(
        node, vehicle, inlink, outlink
    )
    if saved is not None:
        _record_passed_for_saved_visit(saved)
    return result


def _unique_mismatch_rows():
    found = {}
    order = []
    for row in GATE.node_continuous_rank_mismatch_context_rows:
        identity = (
            row["mismatch_node_name"],
            row["mismatch_decision_timestep"],
            row["mismatch_visit_key"],
        )
        if identity not in found:
            order.append(identity)
            found[identity] = row
        if row["is_mismatch_visit"] is True:
            found[identity] = row
    rows = []
    for identity in order:
        rows.append(found[identity])
    return rows


def _context_rows_for_mismatch(mismatch_row):
    rows = []
    for row in GATE.node_continuous_rank_mismatch_context_rows:
        if row["mismatch_node_name"] != mismatch_row["mismatch_node_name"]:
            continue
        if row["mismatch_decision_timestep"] != mismatch_row["mismatch_decision_timestep"]:
            continue
        if row["mismatch_visit_key"] != mismatch_row["mismatch_visit_key"]:
            continue
        rows.append(row)
    return rows


def _party_for_mismatch(decision, visit_key):
    if decision is None:
        return None
    found = None
    for party in decision["parties"]:
        if party["visit_key_tuple"] != visit_key:
            continue
        if found is not None:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"{_visit_text(visit_key)} appears twice in the selected parties."
            )
        found = party
    return found


def _read_same_decision_baseline_arrival(decision, node_name: str, visit_key):
    """Baseline A from this mismatch decision's own collector snapshot.

    The caller selects the decision with mismatch_node_name and
    mismatch_decision_timestep. get_baseline_visit_snapshot is called with
    both vehicle_name and visit_id. A snapshot for another node is not used.
    """
    if decision["node_name"] != node_name:
        raise RuntimeError(
            f"Baseline A lookup node {node_name!r} is not the captured decision "
            f"node {decision['node_name']!r}."
        )
    collector = decision["baseline_collector"]
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError(
            f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
            "saved baseline collector is "
            f"{type(collector).__name__}."
        )
    snapshot = collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
    label = _decision_label(decision["node_name"], decision["decision_timestep"])
    visit_text = _visit_text(visit_key)
    if snapshot is None:
        return (
            None,
            "no_snapshot",
            f"{label}: collector has no snapshot for {visit_text}.",
        )
    if (
        snapshot.get("vehicle_name") != visit_key[0]
        or snapshot.get("visit_id") != visit_key[1]
    ):
        raise RuntimeError(
            f"{label}: collector snapshot identity does not match {visit_text}."
        )
    if snapshot.get("node_name") != node_name:
        return (
            None,
            "other_node",
            f"{label}: collector snapshot for {visit_text} belongs to node "
            f"{snapshot.get('node_name')!r}, so its baseline arrival was not used.",
        )
    arrival = snapshot.get("baseline_arrival_timestep")
    if arrival is None:
        return (
            None,
            "unresolved",
            f"{label}: collector snapshot for {visit_text} has unresolved "
            "baseline arrival inside this decision's baseline horizon.",
        )
    if type(arrival) is not int or arrival < 0:
        raise RuntimeError(
            f"{label}: baseline_arrival_timestep for {visit_text} is {arrival!r}."
        )
    return (
        arrival,
        "resolved",
        f"{label}: baseline_arrival_timestep for {visit_text} is the resolved "
        "collector snapshot value.",
    )


def _baseline_arrival_for_timeline(decision, party, node_name: str, visit_key):
    """Baseline A for one context Visit of this mismatch decision.

    Trade-scope output stays the saved party value, and that value must match
    the same decision's resolved collector snapshot. A context Visit outside
    the trade scope still uses that same collector when the snapshot resolves.
    """
    if decision is None:
        return (
            None,
            "decision_missing",
            "The mismatch decision was not captured, so its baseline collector "
            "was not available.",
        )
    arrival, outcome, detail = _read_same_decision_baseline_arrival(
        decision, node_name, visit_key
    )
    if party is None:
        if (
            outcome == "resolved"
            and visit_key in decision["candidate_baseline_arrival_by_visit"]
            and decision["candidate_baseline_arrival_by_visit"][visit_key] != arrival
        ):
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"{_visit_text(visit_key)} collector Baseline A {arrival!r} disagrees "
                "with candidate_visits."
            )
        return arrival, outcome, detail
    party_arrival = party["baseline_arrival_timestep"]
    if outcome != "resolved" or party_arrival != arrival:
        raise RuntimeError(
            f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
            f"{_visit_text(visit_key)} trade-scope Baseline A {party_arrival!r} "
            f"does not match collector outcome {outcome} value {arrival!r}."
        )
    if visit_key in decision["candidate_baseline_arrival_by_visit"]:
        candidate_arrival = decision["candidate_baseline_arrival_by_visit"][visit_key]
        if candidate_arrival != party_arrival:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"{_visit_text(visit_key)} baseline arrival A disagrees between the "
                f"saved party ({party_arrival!r}) and candidate_visits "
                f"({candidate_arrival!r})."
            )
    return party_arrival, outcome, detail


def _prediction_passages_for_timeline(decision, party, visit_key):
    """Passage predictions from this decision's traffic observation only."""
    if decision is None:
        return None, None
    traffic = decision["traffic_passage_by_visit"].get(visit_key)
    if traffic is None:
        if party is not None:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"{_visit_text(visit_key)} is in the trade scope but has no traffic "
                "observation on this decision."
            )
        return None, None
    baseline_passage = traffic["baseline_passage_timestep"]
    candidate_passage = traffic["candidate_passage_timestep"]
    if party is not None:
        if party["baseline_passage_timestep"] != baseline_passage:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"{_visit_text(visit_key)} baseline passage disagrees."
            )
        if party["candidate_passage_timestep"] != candidate_passage:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"{_visit_text(visit_key)} candidate passage disagrees."
            )
    return baseline_passage, candidate_passage


def _join_timeline_notes(notes) -> str:
    text = ""
    for note in notes:
        if note is None or note == "":
            continue
        if text == "":
            text = note
        else:
            text = text + " " + note
    return text


def _timeline_data_status(
    party,
    baseline_outcome: str,
    baseline_detail: str,
    actual_arrival,
    baseline_passage,
    candidate_passage,
    actual_passage,
    actual_observation_status,
):
    """Choose one existing status and describe every retrieval result in the note."""
    notes = [f"baseline collector result is {baseline_outcome}.", baseline_detail]
    if baseline_passage is None or candidate_passage is None:
        notes.append(
            "baseline_passage_timestep and candidate_passage_timestep stay blank "
            "where this mismatch transaction has no traffic observation for the Visit."
        )
    if actual_arrival is None:
        notes.append(
            "actual_node_arrival_timestep was not in the real-world arrival record. "
            "Baseline arrival A was not copied into that field."
        )
    if actual_passage is None or actual_observation_status == ACTUAL_UNOBSERVED:
        notes.append(
            "actual passage was unobserved at evaluation end."
        )
    if party is None:
        return "context_visit_outside_trade_scope", _join_timeline_notes(notes)
    if actual_arrival is None:
        return "actual_arrival_unavailable", _join_timeline_notes(notes)
    if baseline_passage is None or candidate_passage is None:
        return "candidate_prediction_unavailable", _join_timeline_notes(notes)
    if actual_passage is None or actual_observation_status == ACTUAL_UNOBSERVED:
        return "actual_unobserved_at_evaluation_end", _join_timeline_notes(notes)
    if baseline_outcome != "resolved":
        return "candidate_prediction_unavailable", _join_timeline_notes(notes)
    return (
        "complete_for_trade_scope_visit",
        "Trade-scope Baseline A matches this decision's collector snapshot. "
        "Candidate predictions, actual node arrival, and actual passage are present.",
    )


def _timeline_inlink_name(context_row, decision, visit_key):
    saved = context_row["inlink_name"]
    if isinstance(saved, str) and saved != "":
        return saved
    if decision is None:
        return None
    return decision["candidate_inlink_by_visit"].get(visit_key)


def _vehicle_timeline_row(context_row) -> dict:
    node_name = context_row["mismatch_node_name"]
    decision_timestep = context_row["mismatch_decision_timestep"]
    visit_key = _visit_key_from_text(context_row["context_visit_key"])
    decision = GATE.decisions.get((node_name, decision_timestep))
    party = _party_for_mismatch(decision, visit_key)
    baseline_local_rank = None
    post_trade_local_rank = None
    if decision is not None and visit_key in decision["candidate_baseline_arrival_by_visit"]:
        baseline_local_rank = decision["baseline_local_rank_by_visit"].get(visit_key)
        post_trade_local_rank = decision["post_trade_local_rank_by_visit"].get(visit_key)
    baseline_arrival, baseline_outcome, baseline_detail = _baseline_arrival_for_timeline(
        decision, party, node_name, visit_key
    )
    baseline_passage, candidate_passage = _prediction_passages_for_timeline(
        decision, party, visit_key
    )
    actual_arrival = _stored_actual_node_arrival(node_name, visit_key)
    actual_passage = context_row["actual_passage_timestep"]
    _require_actual_passage_follows_arrival(
        node_name, visit_key, actual_arrival, actual_passage
    )
    if party is None:
        role = "outside_mismatch_transaction_scope"
        predicted_observation_status = None
        actual_observation_status = None
    else:
        role = party["role"]
        predicted_observation_status = party["predicted_observation_status"]
        actual_observation_status = party["actual_observation_status"]
    status, note = _timeline_data_status(
        party,
        baseline_outcome,
        baseline_detail,
        actual_arrival,
        baseline_passage,
        candidate_passage,
        actual_passage,
        actual_observation_status,
    )
    return {
        "mismatch_decision_timestep": decision_timestep,
        "node_name": node_name,
        "mismatch_visit_key": context_row["mismatch_visit_key"],
        "context_visit_key": context_row["context_visit_key"],
        "vehicle_name": context_row["vehicle_name"],
        "visit_id": context_row["visit_id"],
        "is_mismatch_visit": context_row["is_mismatch_visit"],
        "is_between_mismatch_ranks": context_row["is_between_mismatch_ranks"],
        "role_at_mismatch_transaction": role,
        "inlink_name": _timeline_inlink_name(context_row, decision, visit_key),
        "formal_route_next_link_name": context_row["formal_route_next_link_name"],
        "actual_route_next_link_name": context_row["actual_route_next_link_name"],
        "baseline_arrival_timestep": baseline_arrival,
        "actual_node_arrival_timestep": actual_arrival,
        "baseline_passage_timestep": baseline_passage,
        "candidate_passage_timestep": candidate_passage,
        "actual_passage_timestep": actual_passage,
        "baseline_local_rank": baseline_local_rank,
        "post_trade_local_rank": post_trade_local_rank,
        "assigned_rank": context_row["assigned_rank"],
        "actual_node_passage_rank": context_row["actual_node_passage_rank"],
        "predicted_observation_status": predicted_observation_status,
        "actual_observation_status": actual_observation_status,
        "timeline_data_status": status,
        "timeline_data_note": note,
    }


def _build_vehicle_timeline_rows():
    rows = []
    for context_row in GATE.node_continuous_rank_mismatch_context_rows:
        rows.append(_vehicle_timeline_row(context_row))
    return rows


def _empty_trace_row():
    row = {}
    for column in NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_COLUMNS:
        row[column] = None
    return row


def _observed_trace_csv_row(mismatch_row, event, context_row, actual_by_visit):
    visit_key = event["visit_key"]
    node_name = mismatch_row["mismatch_node_name"]
    actual_arrival = _stored_actual_node_arrival(node_name, visit_key)
    if context_row is None:
        assigned_rank = event["assigned_rank"]
        actual_record = actual_by_visit.get(visit_key)
        if actual_record is None:
            actual_rank = None
            history_passage = None
        else:
            actual_rank = actual_record.actual_node_passage_rank
            history_passage = actual_record.actual_passage_timestep
        context_visit_key = _visit_text(visit_key)
    else:
        assigned_rank = context_row["assigned_rank"]
        actual_rank = context_row["actual_node_passage_rank"]
        history_passage = context_row["actual_passage_timestep"]
        context_visit_key = context_row["context_visit_key"]
        event_assigned = event["assigned_rank"]
        if (
            type(assigned_rank) is int
            and type(event_assigned) is int
            and assigned_rank != event_assigned
        ):
            raise RuntimeError(
                f"Node {node_name}: {_visit_text(visit_key)} assigned_rank during "
                f"the trace was {event_assigned}, but the ledger rank is "
                f"{assigned_rank}."
            )
    _require_actual_passage_follows_arrival(
        node_name, visit_key, actual_arrival, history_passage
    )
    row = _empty_trace_row()
    row["mismatch_decision_timestep"] = mismatch_row["mismatch_decision_timestep"]
    row["node_name"] = node_name
    row["mismatch_visit_key"] = mismatch_row["mismatch_visit_key"]
    row["real_world_timestep"] = event["real_world_timestep"]
    row["scan_sequence_index"] = event["scan_sequence_index"]
    row["context_visit_key"] = context_visit_key
    row["vehicle_name"] = event["vehicle_name"]
    row["visit_id"] = event["visit_id"]
    row["assigned_rank"] = assigned_rank
    row["actual_node_passage_rank"] = actual_rank
    row["inlink_name"] = event["inlink_name"]
    row["intended_outlink_name"] = event["intended_outlink_name"]
    row["actual_node_arrival_timestep"] = actual_arrival
    row["was_arrived_at_node"] = event["was_arrived_at_node"]
    row["was_already_passed_before_scan"] = event["was_already_passed_before_scan"]
    row["was_inlink_physical_head"] = event["was_inlink_physical_head"]
    row["clearance_required_timesteps"] = event["clearance_required_timesteps"]
    row["last_order_control_inlink_name"] = event["last_order_control_inlink_name"]
    row["last_order_control_entry_timestep"] = event[
        "last_order_control_entry_timestep"
    ]
    row["clearance_satisfied"] = event["clearance_satisfied"]
    row["inlink_capacity_out_remain_before"] = event[
        "inlink_capacity_out_remain_before"
    ]
    row["inlink_outflow_capacity_satisfied"] = event[
        "inlink_outflow_capacity_satisfied"
    ]
    row["node_flow_capacity_remain_before"] = event["node_flow_capacity_remain_before"]
    row["node_flow_capacity_satisfied"] = event["node_flow_capacity_satisfied"]
    row["outlink_capacity_in_remain_before"] = event[
        "outlink_capacity_in_remain_before"
    ]
    row["outlink_inflow_capacity_satisfied"] = event[
        "outlink_inflow_capacity_satisfied"
    ]
    row["outlink_entrance_space_available"] = event["outlink_entrance_space_available"]
    row["outlink_entrance_space_detail"] = event["outlink_entrance_space_detail"]
    row["first_blocking_reason"] = event["first_blocking_reason"]
    row["action"] = event["action"]
    row["passed_this_scan"] = event["passed_this_scan"]
    row["temporary_skipped"] = event["temporary_skipped"]
    row["clearance_stopped_node_scan"] = event["clearance_stopped_node_scan"]
    row["actual_passage_timestep_if_passed"] = event[
        "actual_passage_timestep_if_passed"
    ]
    row["scan_note"] = event["scan_note"]
    return row


def _synthetic_trace_csv_row(mismatch_row, context_row, timestep: int):
    """One context Visit that production did not judge at this timestep."""
    node_name = mismatch_row["mismatch_node_name"]
    visit_key = _visit_key_from_text(context_row["context_visit_key"])
    actual_arrival = _stored_actual_node_arrival(node_name, visit_key)
    actual_passage = context_row["actual_passage_timestep"]
    _require_actual_passage_follows_arrival(
        node_name, visit_key, actual_arrival, actual_passage
    )
    was_arrived = False
    already_passed = False
    if type(actual_passage) is int and actual_passage < timestep:
        reason = "already_passed"
        action = "already_passed"
        already_passed = True
        note = "actual passage history is earlier than this timestep"
    elif actual_arrival is None or actual_arrival >= timestep:
        action = "not_yet_arrived"
        if actual_arrival is None:
            reason = "not_observable"
            note = "actual node arrival was not recorded, so arrival was not inferred"
        elif actual_arrival == timestep:
            reason = "not_arrived"
            note = (
                "arrival is registered in Vehicle.update after Node.transfer, "
                "so this scan has not seen the arrival yet"
            )
        else:
            reason = "not_arrived"
            note = "actual node arrival is later than this timestep"
    elif type(actual_passage) is int and actual_passage == timestep:
        reason = "not_observable"
        action = "not_present"
        was_arrived = True
        note = (
            "actual passage history uses this timestep, but the production "
            "observation did not record a pass"
        )
    else:
        reason = "not_present_at_target_node"
        action = "not_present"
        note = (
            "the Visit had already arrived and had not passed, and it was not "
            "in this node scan"
        )
    row = _empty_trace_row()
    row["mismatch_decision_timestep"] = mismatch_row["mismatch_decision_timestep"]
    row["node_name"] = node_name
    row["mismatch_visit_key"] = mismatch_row["mismatch_visit_key"]
    row["real_world_timestep"] = timestep
    row["context_visit_key"] = context_row["context_visit_key"]
    row["vehicle_name"] = context_row["vehicle_name"]
    row["visit_id"] = context_row["visit_id"]
    row["assigned_rank"] = context_row["assigned_rank"]
    row["actual_node_passage_rank"] = context_row["actual_node_passage_rank"]
    row["inlink_name"] = context_row["inlink_name"]
    row["actual_node_arrival_timestep"] = actual_arrival
    row["was_arrived_at_node"] = was_arrived
    row["was_already_passed_before_scan"] = already_passed
    row["passed_this_scan"] = False
    row["temporary_skipped"] = False
    row["clearance_stopped_node_scan"] = False
    row["first_blocking_reason"] = reason
    row["action"] = action
    row["scan_note"] = note
    return row


def _append_trace_rows_for_timestep(
    rows,
    mismatch_row,
    context_rows,
    context_by_key,
    events,
    timestep: int,
    actual_by_visit,
) -> None:
    seen_context_keys = {}
    max_context_sequence = None
    context_was_cut_off = False
    for event in events:
        event_key = _visit_text(event["visit_key"])
        if event_key not in context_by_key:
            continue
        seen_context_keys[event_key] = True
        if event["action"] == "not_scanned_after_clearance_stop":
            context_was_cut_off = True
        sequence = event["scan_sequence_index"]
        if type(sequence) is not int:
            continue
        if max_context_sequence is None or sequence > max_context_sequence:
            max_context_sequence = sequence
    for event in events:
        event_key = _visit_text(event["visit_key"])
        keep = False
        if event_key in context_by_key:
            keep = True
        else:
            sequence = event["scan_sequence_index"]
            if (
                type(sequence) is int
                and max_context_sequence is not None
                and sequence <= max_context_sequence
            ):
                keep = True
            elif context_was_cut_off is True and type(sequence) is int:
                keep = True
        if keep is not True:
            continue
        rows.append(
            _observed_trace_csv_row(
                mismatch_row,
                event,
                context_by_key.get(event_key),
                actual_by_visit,
            )
        )
    for context_row in context_rows:
        if context_row["context_visit_key"] in seen_context_keys:
            continue
        rows.append(_synthetic_trace_csv_row(mismatch_row, context_row, timestep))


def _build_physical_trace_rows(world):
    mismatches = _unique_mismatch_rows()
    if len(mismatches) == 0:
        return []
    grouped = {}
    for event in GATE.physical_trace_events:
        node_name = event["node_name"]
        timestep = event["real_world_timestep"]
        if node_name not in grouped:
            grouped[node_name] = {}
        node_group = grouped[node_name]
        if timestep not in node_group:
            node_group[timestep] = []
        node_group[timestep].append(event)
    sides_by_node = {}
    rows = []
    for mismatch_row in mismatches:
        node_name = mismatch_row["mismatch_node_name"]
        if node_name not in sides_by_node:
            sides_by_node[node_name] = _load_node_continuous_rank_sides(world, node_name)
        actual_by_visit = sides_by_node[node_name]["actual_by_visit"]
        context_rows = _context_rows_for_mismatch(mismatch_row)
        context_by_key = {}
        for context_row in context_rows:
            context_by_key[context_row["context_visit_key"]] = context_row
        node_events = grouped.get(node_name, {})
        timestep = PHYSICAL_TRACE_TIMESTEP_START
        while timestep <= PHYSICAL_TRACE_TIMESTEP_END:
            events = node_events.get(timestep, [])
            _append_trace_rows_for_timestep(
                rows,
                mismatch_row,
                context_rows,
                context_by_key,
                events,
                timestep,
                actual_by_visit,
            )
            timestep = timestep + 1
    return rows


def _swapped_partner_row(mismatch_row):
    """The context Visit that holds the other side of this rank exchange.

    Selection uses the two ranks already stored on the mismatch. It does not
    look up a fixed VisitKey or a fixed rank number.
    """
    assigned_rank = mismatch_row["mismatch_assigned_rank"]
    actual_rank = mismatch_row["mismatch_actual_node_passage_rank"]
    found = None
    for row in _context_rows_for_mismatch(mismatch_row):
        if row["context_visit_key"] == mismatch_row["mismatch_visit_key"]:
            continue
        if row["assigned_rank"] != actual_rank:
            continue
        if row["actual_node_passage_rank"] != assigned_rank:
            continue
        if found is not None:
            return None
        found = row
    return found


def _trace_rows_for_visit(mismatch_row, context_visit_key):
    rows = []
    for row in GATE.physical_trace_rows:
        if row["node_name"] != mismatch_row["mismatch_node_name"]:
            continue
        if row["mismatch_decision_timestep"] != mismatch_row["mismatch_decision_timestep"]:
            continue
        if row["mismatch_visit_key"] != mismatch_row["mismatch_visit_key"]:
            continue
        if row["context_visit_key"] != context_visit_key:
            continue
        rows.append(row)
    return rows


def _timeline_row_for(mismatch_row, context_visit_key):
    for row in GATE.vehicle_timeline_rows:
        if row["node_name"] != mismatch_row["mismatch_node_name"]:
            continue
        if row["mismatch_decision_timestep"] != mismatch_row["mismatch_decision_timestep"]:
            continue
        if row["mismatch_visit_key"] != mismatch_row["mismatch_visit_key"]:
            continue
        if row["context_visit_key"] != context_visit_key:
            continue
        return row
    return None


def _classify_rank_mismatch(mismatch_row, partner_row):
    """Explain a rank swap only from an observed production block.

    explained_by_physical_state requires the mismatch Visit's row at the
    partner's passage timestep to carry a concrete physical reason.
    A missing row, not_observable, or not_present stays insufficient_trace.
    none_passed without a pass, or already_passed while the partner is the
    one passing, is implementation_inconsistency_suspected.
    """
    if partner_row is None:
        return "insufficient_trace", None
    partner_passage = partner_row["actual_passage_timestep"]
    if type(partner_passage) is not int:
        return "insufficient_trace", None
    visit_rows = _trace_rows_for_visit(
        mismatch_row, mismatch_row["mismatch_visit_key"]
    )
    partner_timestep_row = None
    earliest_reason = None
    not_arrived_reason = None
    judgment_reasons = (
        "not_inlink_physical_head",
        "clearance_not_satisfied",
        "inlink_outflow_capacity_insufficient",
        "node_flow_capacity_insufficient",
        "outlink_inflow_capacity_insufficient",
        "outlink_entrance_space_insufficient",
        "not_scanned_after_clearance_stop",
    )
    for trace_row in visit_rows:
        timestep = trace_row["real_world_timestep"]
        if type(timestep) is not int or timestep > partner_passage:
            continue
        reason = trace_row["first_blocking_reason"]
        if timestep == partner_passage:
            partner_timestep_row = trace_row
        if reason == "not_arrived" and not_arrived_reason is None:
            not_arrived_reason = reason
        if earliest_reason is None and reason in judgment_reasons:
            earliest_reason = reason
    if earliest_reason is None:
        earliest_reason = not_arrived_reason
    if partner_timestep_row is None:
        return "insufficient_trace", earliest_reason
    reason = partner_timestep_row["first_blocking_reason"]
    action = partner_timestep_row["action"]
    physical_reasons = (
        "not_arrived",
        "not_inlink_physical_head",
        "clearance_not_satisfied",
        "inlink_outflow_capacity_insufficient",
        "node_flow_capacity_insufficient",
        "outlink_inflow_capacity_insufficient",
        "outlink_entrance_space_insufficient",
        "not_scanned_after_clearance_stop",
    )
    if reason in physical_reasons:
        if earliest_reason is None:
            earliest_reason = reason
        return "explained_by_physical_state", earliest_reason
    if reason == "already_passed" or (
        reason == "none_passed" and action != "passed"
    ):
        return "implementation_inconsistency_suspected", earliest_reason
    if reason == "none_passed" and action == "passed":
        return "implementation_inconsistency_suspected", earliest_reason
    return "insufficient_trace", earliest_reason


def _print_cell(value):
    if value is None:
        return "None"
    return str(value)


def _print_rank_mismatch_physical_summary() -> None:
    mismatches = _unique_mismatch_rows()
    if len(mismatches) == 0:
        print("Node-continuous rank mismatch physical summary: no mismatches.")
        return
    for mismatch_row in mismatches:
        partner_row = _swapped_partner_row(mismatch_row)
        provisional_class, blocking_reason = _classify_rank_mismatch(
            mismatch_row, partner_row
        )
        mismatch_timeline = _timeline_row_for(
            mismatch_row, mismatch_row["mismatch_visit_key"]
        )
        print(f"Node: {mismatch_row['mismatch_node_name']}")
        print(f"decision T: {mismatch_row['mismatch_decision_timestep']}")
        print(f"mismatch VisitKey: {mismatch_row['mismatch_visit_key']}")
        print(f"C continuous rank: {mismatch_row['mismatch_assigned_rank']}")
        print(
            "Actual continuous rank: "
            f"{mismatch_row['mismatch_actual_node_passage_rank']}"
        )
        if partner_row is None:
            print("swapped VisitKey: not uniquely identified")
            print("swapped C continuous rank: None")
            print("swapped Actual continuous rank: None")
            print("swapped actual_node_arrival_timestep: None")
            print("swapped candidate_passage_timestep: None")
            print("swapped actual_passage_timestep: None")
            partner_passage = None
        else:
            partner_timeline = _timeline_row_for(
                mismatch_row, partner_row["context_visit_key"]
            )
            print(f"swapped VisitKey: {partner_row['context_visit_key']}")
            print(f"swapped C continuous rank: {partner_row['assigned_rank']}")
            print(
                "swapped Actual continuous rank: "
                f"{partner_row['actual_node_passage_rank']}"
            )
            if partner_timeline is None:
                print("swapped actual_node_arrival_timestep: None")
                print("swapped candidate_passage_timestep: None")
            else:
                print(
                    "swapped actual_node_arrival_timestep: "
                    f"{_print_cell(partner_timeline['actual_node_arrival_timestep'])}"
                )
                print(
                    "swapped candidate_passage_timestep: "
                    f"{_print_cell(partner_timeline['candidate_passage_timestep'])}"
                )
            print(
                "swapped actual_passage_timestep: "
                f"{_print_cell(partner_row['actual_passage_timestep'])}"
            )
            partner_passage = partner_row["actual_passage_timestep"]
        if mismatch_timeline is None:
            print("mismatch actual_node_arrival_timestep: None")
            print("mismatch candidate_passage_timestep: None")
            print("mismatch actual_passage_timestep: None")
        else:
            print(
                "mismatch actual_node_arrival_timestep: "
                f"{_print_cell(mismatch_timeline['actual_node_arrival_timestep'])}"
            )
            print(
                "mismatch candidate_passage_timestep: "
                f"{_print_cell(mismatch_timeline['candidate_passage_timestep'])}"
            )
            print(
                "mismatch actual_passage_timestep: "
                f"{_print_cell(mismatch_timeline['actual_passage_timestep'])}"
            )
        print(
            "first blocking reason at or before swapped passage: "
            f"{_print_cell(blocking_reason)}"
        )
        print(f"swapped passage timestep: {_print_cell(partner_passage)}")
        print(f"provisional class: {provisional_class}")


def _print_node_continuous_rank_mismatch_summary() -> None:
    seen = {}
    mismatches = []
    for row in GATE.node_continuous_rank_mismatch_context_rows:
        identity = (
            row["mismatch_node_name"],
            row["mismatch_decision_timestep"],
            row["mismatch_visit_key"],
        )
        if identity in seen:
            continue
        seen[identity] = True
        mismatches.append(row)
    print(f"Node-continuous rank mismatch parties: {len(mismatches)}")
    for row in mismatches:
        print(
            f"{row['mismatch_node_name']} T={row['mismatch_decision_timestep']} "
            f"{row['mismatch_visit_key']} "
            f"assigned_rank={row['mismatch_assigned_rank']} "
            f"actual_node_passage_rank={row['mismatch_actual_node_passage_rank']}"
        )
    print(
        "Context CSV: "
        f"{OUTPUT_DIR / NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_CSV_NAME}"
    )


def _write_csv(path: Path, columns, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _write_outputs() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Refusing to overwrite {OUTPUT_DIR}.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    summary_rows = []
    party_rows = []
    for decision_key in TARGET_DECISION_KEYS:
        decision = GATE.decisions.get(decision_key)
        if decision is None:
            continue
        summary_rows.append(decision)
        ordered_parties = sorted(
            decision["parties"],
            key=lambda party: (party["baseline_local_rank"], party["visit_key_tuple"]),
        )
        party_rows.extend(ordered_parties)
    if (EAST_NODE, 35) in GATE.decisions and len(GATE.east_t35_audit_rows) == 0:
        raise RuntimeError(
            "east_intersection T=35 was observed but the all-candidate audit is empty."
        )
    _write_csv(OUTPUT_DIR / SUMMARY_CSV_NAME, SUMMARY_COLUMNS, summary_rows)
    _write_csv(OUTPUT_DIR / PARTIES_CSV_NAME, PARTY_COLUMNS, party_rows)
    _write_csv(
        OUTPUT_DIR / EAST_T35_AUDIT_CSV_NAME,
        EAST_T35_AUDIT_COLUMNS,
        GATE.east_t35_audit_rows,
    )
    _write_csv(
        OUTPUT_DIR / NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_CSV_NAME,
        NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_COLUMNS,
        GATE.node_continuous_rank_mismatch_context_rows,
    )
    _write_csv(
        OUTPUT_DIR / NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_CSV_NAME,
        NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_COLUMNS,
        GATE.vehicle_timeline_rows,
    )
    _write_csv(
        OUTPUT_DIR / NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_CSV_NAME,
        NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_COLUMNS,
        GATE.physical_trace_rows,
    )
    extra_names = []
    for path in OUTPUT_DIR.iterdir():
        if path.name not in OUTPUT_FILE_NAMES:
            extra_names.append(path.name)
    if len(extra_names) != 0:
        raise RuntimeError(f"Diagnostic directory has unexpected files: {extra_names}.")


def _assert_production_fields() -> None:
    required = {
        OrderControlTvtMpBuyerEconomicRecord: (
            "visit_key",
            "vehicle_name",
            "declared_vot_per_second",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
            "expected_time_saving_timesteps",
            "gross_time_value_G_b",
        ),
        OrderControlTvtMpSellerEconomicRecord: (
            "visit_key",
            "vehicle_name",
            "declared_vot_per_second",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
            "raw_passage_difference_timesteps",
            "required_compensation_R_s",
        ),
        OrderControlTvtMpCandidateEconomicEvaluationResult: (
            "candidate_local_virtual_calculation_result",
            "buyer_economic_records",
            "seller_economic_records",
            "total_buyer_value_G",
            "total_required_compensation_R",
            "surplus",
            "economically_feasible",
            "infeasibility_reasons",
        ),
        OrderControlTvtMpBuyerPaymentRecord: ("visit_key", "payment_P_b"),
        OrderControlTvtMpSellerCompensationRecord: ("visit_key", "compensation_amount"),
        OrderControlTvtMpLocalBindingRankSequence: (
            "node_name",
            "baseline_timestep_T",
            "concrete_buyer_candidate_set",
            "trade_scope_of_this_candidate_visits",
            "visits_in_binding_order",
        ),
        OrderControlTvtMpLocalBindingRankVisit: (
            "visit_key",
            "vehicle_id",
            "binding_partition",
            "binding_rank",
            "route_next_link_name",
            "inlink_name",
            "baseline_arrival_timestep",
            "arrival_tiebreaker",
            "trade_role",
        ),
        OrderControlTvtMpCandidateTrafficObservationRecord: (
            "visit_key",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
            "predicted_time_difference_timesteps",
            "true_vot_per_second",
            "trade_role",
        ),
        OrderControlTvtCandidateVisit: (
            "visit_key",
            "vehicle_id",
            "inlink_name",
            "baseline_arrival_timestep",
            "arrival_tiebreaker",
            "route_next_link_name",
            "baseline_passage_timestep",
        ),
        OrderControlTvtNodeRightOfEntrySelectionResult: (
            "node_name",
            "right_of_entry_visit_key",
        ),
        OrderControlTvtMpCandidateFifoInspectionResult: (
            "general_trade_rank_result",
            "preserves_inlink_fifo",
        ),
        OrderControlTvtMpTradeEstablishmentLogRecord: (
            "tvt_decision_timestep",
            "node_name",
            "visit_key",
            "baseline_local_rank",
            "post_trade_local_rank",
            "ledger_assigned_rank",
            "rank_change",
            "formal_route_next_link_name",
        ),
        OrderControlTvtMpResearchOutputTransactionRow: (
            "tvt_decision_timestep",
            "node_name",
            "buyers_sorted",
            "trade_ex_post_evaluation_status",
            "buyer_actual_declared_time_saving_value_total",
            "seller_actual_required_compensation_total",
        ),
        OrderControlTvtMpResearchOutputVisitRow: (
            "tvt_decision_timestep",
            "node_name",
            "buyers_sorted",
            "vehicle_name",
            "visit_id",
            "role",
            "actual_observation_status",
            "predicted_observation_status",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
            "actual_passage_timestep",
            "true_vot_per_second",
            "declared_vot_per_second",
            "realized_gain",
            "realized_delay_loss",
            "satisfaction_status",
            "actual_node_passage_rank",
        ),
        OrderControlTvtMpActualNodePassageRecord: (
            "visit_key",
            "actual_node_passage_rank",
        ),
        OrderControlTvtMpDriverResult: ("atomic_apply_set_result",),
        OrderControlBaselineForkResult: ("collector",),
        OrderControlTvtMpCandidateLocalVirtualCalculationResult: (
            "node_name",
            "concrete_buyer_candidate_set",
            "binding_rank_sequence",
            "baseline_timestep_T",
            "stop_reason",
            "resolved",
            "unresolved_reasons",
            "traffic_observation_records",
        ),
        OrderControlTvtNodeMpCandidateSelectionResult: (
            "node_name",
            "selection_status",
            "selected_candidate_economic_result",
            "rng_was_used",
        ),
        OrderControlTvtNodeMpPaymentAndCompensationResult: (
            "node_name",
            "payment_and_compensation_status",
            "selected_candidate_economic_result",
            "buyer_payment_records",
            "seller_compensation_records",
        ),
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult: (
            "node_name",
            "concrete_buyer_candidate_sets",
        ),
        OrderControlTvtNodeMpGeneralTradeRankResult: (
            "node_name",
            "candidate_trade_rank_results",
        ),
        OrderControlTvtNodeMpFifoInspectionResult: (
            "node_name",
            "candidate_fifo_inspection_results",
        ),
        OrderControlTvtNodeMpLocalVirtualCalculationResult: (
            "node_name",
            "candidate_local_virtual_calculation_results",
        ),
        OrderControlTvtNodeMpEconomicEvaluationResult: (
            "node_name",
            "candidate_economic_evaluation_results",
        ),
        OrderControlTvtNodeCandidateVisitSetResult: (
            "node_name",
            "candidate_visits",
        ),
        OrderControlTvtMpConcreteBuyerCandidateSet: ("buyers_sorted",),
    }
    for cls, names in required.items():
        present = {field.name for field in fields(cls)}
        for name in names:
            if name not in present:
                raise RuntimeError(f"{cls.__name__} is missing field {name}.")
    for name in (
        "trade_scope",
        "buyers_sorted",
        "sellers_sorted",
        "nonparticipating_visits_sorted",
        "concrete_buyer_candidate_set",
        "assigned_rank",
        "trade_order",
        "last_buyer_rank",
    ):
        if not hasattr(OrderControlTvtMpGeneralTradeRankResult, name):
            raise RuntimeError(f"General trade rank result is missing {name}.")
    if not hasattr(OrderControlBaselineCollector, "get_baseline_visit_snapshot"):
        raise RuntimeError("Collector is missing get_baseline_visit_snapshot.")
    if not hasattr(OrderControlTvtNodeRankState, "assigned_rank"):
        raise RuntimeError("Node rank state is missing assigned_rank.")
    if "records_by_node_name" not in getattr(
        OrderControlTvtMpActualNodePassageHistoryRegistry, "__dataclass_fields__", {}
    ):
        raise RuntimeError("Actual passage history registry is missing records_by_node_name.")


def _assert_trial_settings() -> None:
    if extended_trial.VOT_SEED != 1 or extended_trial.TRAFFIC_SEED != 0:
        raise RuntimeError("Trial seeds are not the seed-1 initial setting.")
    if extended_trial.EVALUATION_END_TIMESTEP != 599:
        raise RuntimeError("Trial evaluation_end_timestep is not 599.")
    if not extended_trial.TRIAL_OUTPUT_DIR.name.endswith("seed_1_initial"):
        raise RuntimeError("Trial output directory is not the seed-1 initial trial.")
    if extended_trial.SCENARIO_NAME != (
        "tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_trial"
    ):
        raise RuntimeError("Trial scenario name changed.")


def _assert_before_simulation() -> None:
    if len(TARGET_DECISION_KEYS) != 7 or len(set(TARGET_DECISION_KEYS)) != 7:
        raise RuntimeError("Target decision keys must be seven unique keys.")
    _assert_trial_settings()
    _assert_production_fields()
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Diagnostic output directory already exists: {OUTPUT_DIR}.")


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Missing function {name}.")


def _assert_wrapper_returns_original_once(tree: ast.Module) -> None:
    wrapper = _function_node(tree, "wrapped_run_tvt_mp_driver")
    original_calls = []
    returns = []

    class _Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "original_run_tvt_mp_driver"
            ):
                original_calls.append(node)
            self.generic_visit(node)

        def visit_Return(self, node: ast.Return) -> None:
            returns.append(node)

    _Visitor().visit(wrapper)
    if len(original_calls) != 1:
        raise RuntimeError("Driver wrapper must call the original driver once.")
    if len(returns) == 0:
        raise RuntimeError("Driver wrapper must return the original result.")
    for node in returns:
        if not isinstance(node.value, ast.Name) or node.value.id != "result":
            raise RuntimeError("Driver wrapper must return the original result unchanged.")
    source = ast.get_source_segment(SCRIPT_PATH.read_text(encoding="utf-8"), wrapper)
    if source is None or "return result" not in source:
        raise RuntimeError("Driver wrapper source does not return result.")
    if "world is not GATE.real_world" not in source:
        raise RuntimeError("Driver wrapper must ignore copied worlds before traversal.")
    if "World.copy" in source:
        raise RuntimeError("Driver wrapper must not copy a World.")


def _assert_observation_hooks_call_original_once(tree: ast.Module) -> None:
    """The diagnostic wrappers must call production once and return its result."""
    wrappers = (
        (
            "_wrapped_record_order_control_node_arrival",
            "original_record_order_control_node_arrival",
        ),
        (
            "_wrapped_transfer_tvt_mp_passage_attempts",
            "original_transfer_tvt_mp_passage_attempts",
        ),
        (
            "_wrapped_inlink_physical_head_should_skip",
            "original_inlink_physical_head_should_skip",
        ),
        (
            "_wrapped_first_ordinary_physical_shortage",
            "original_first_ordinary_physical_shortage",
        ),
        (
            "_wrapped_order_control_clearance_blocks_passage",
            "original_order_control_clearance_blocks_passage",
        ),
        (
            "_wrapped_transfer_one_vehicle_between_links",
            "original_transfer_one_vehicle_between_links",
        ),
    )
    for function_name, original_attribute in wrappers:
        wrapper = _function_node(tree, function_name)
        original_calls = []

        class _OriginalCallVisitor(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call) -> None:
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == original_attribute:
                    original_calls.append(node)
                self.generic_visit(node)

        _OriginalCallVisitor().visit(wrapper)
        if len(original_calls) != 1:
            raise RuntimeError(f"{function_name} must call production once.")
        function_source = ast.get_source_segment(
            SCRIPT_PATH.read_text(encoding="utf-8"), wrapper
        )
        if function_source is None or "return result" not in function_source:
            raise RuntimeError(f"{function_name} must return the production result.")
        for forbidden in ("World.copy", ".random(", "exec_simulation"):
            if forbidden in function_source:
                raise RuntimeError(
                    f"{function_name} must not introduce {forbidden}."
                )


def _is_name_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
        return False
    comparator = test.comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == "__main__"


def _contains_static_validate_only_literal(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and child.value == "--static-validate-only":
            return True
    return False


def _call_callee_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _assert_main_block_static_validate_contract(tree: ast.Module) -> None:
    """Inspect only the --static-validate-only branch under __main__, not main()."""
    main_guard = None
    for node in tree.body:
        if isinstance(node, ast.If) and _is_name_main_guard(node.test):
            main_guard = node
            break
    if main_guard is None:
        raise RuntimeError("Missing if __name__ == '__main__' guard.")

    static_branch_if = None
    for stmt in main_guard.body:
        if isinstance(stmt, ast.If) and _contains_static_validate_only_literal(stmt.test):
            static_branch_if = stmt
            break
    if static_branch_if is None:
        raise RuntimeError(
            "Missing --static-validate-only branch under __main__."
        )

    assert_static_contract_calls = 0
    forbidden_in_static = (
        "main",
        "exec_simulation",
        "_write_outputs",
        "_write_csv",
    )

    class _StaticBranchVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            nonlocal assert_static_contract_calls
            callee = _call_callee_name(node)
            if callee == "_assert_static_contract":
                assert_static_contract_calls = assert_static_contract_calls + 1
            if callee in forbidden_in_static:
                raise RuntimeError(
                    f"Static validation branch must not call {callee}()."
                )
            if isinstance(node.func, ast.Attribute) and node.func.attr == "mkdir":
                raise RuntimeError(
                    "Static validation branch must not create the output directory."
                )
            self.generic_visit(node)

    for stmt in static_branch_if.body:
        _StaticBranchVisitor().visit(stmt)

    if assert_static_contract_calls != 1:
        raise RuntimeError(
            "Static validation branch must call _assert_static_contract() once."
        )

    calls_main = False
    for stmt in static_branch_if.orelse:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and _call_callee_name(node) == "main":
                calls_main = True
    if calls_main is not True:
        raise RuntimeError("Non-static __main__ branch must call main().")


def _assert_east_t35_audit_static_contract(source: str, tree: ast.Module) -> None:
    if EAST_T35_AUDIT_CSV_NAME != "east_t35_all_candidate_audit.csv":
        raise RuntimeError("East T=35 audit CSV name changed.")
    if EAST_T35_AUDIT_KEY != ("east_intersection", 35):
        raise RuntimeError("East T=35 audit target is not east_intersection T=35.")
    if EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT != 7:
        raise RuntimeError("East T=35 expected concrete candidate count is not 7.")
    if EAST_T35_EXPECTED_FIFO_PASSED_COUNT != 7:
        raise RuntimeError("East T=35 expected FIFO passed count is not 7.")
    if EAST_T35_EXPECTED_FIFO_FAILED_COUNT != 0:
        raise RuntimeError("East T=35 expected FIFO failed count is not 0.")
    for column in (
        "decision_timestep",
        "node_name",
        "candidate_identity",
        "candidate_index_in_stored_order",
        "buyer_visit_keys",
        "seller_visit_keys",
        "nonparticipating_visit_keys",
        "trade_scope_visit_keys",
        "baseline_order_visit_keys",
        "candidate_order_visit_keys",
        "buyer_count",
        "seller_count",
        "nonparticipating_count",
        "fifo_inspection_passed",
        "local_virtual_calculation_resolved",
        "local_virtual_calculation_stop_reason",
        "economically_evaluated",
        "total_G",
        "total_R",
        "surplus",
        "economically_feasible",
        "infeasibility_reasons",
        "selected",
        "selection_exclusion_stage",
        "selection_exclusion_reason",
        "visit_key",
        "vehicle_name",
        "visit_id",
        "role",
        "is_right_of_entry_holder",
        "inlink_name",
        "formal_route_next_link_name",
        "baseline_arrival_timestep",
        "arrival_tiebreaker",
        "baseline_local_rank",
        "post_trade_local_rank",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "predicted_time_difference_timesteps",
        "declared_vot_per_second",
        "buyer_value_G_b",
        "seller_required_compensation_R_s",
        "same_inlink_fifo_preserved",
    ):
        if column not in EAST_T35_AUDIT_COLUMNS:
            raise RuntimeError(f"East T=35 audit CSV is missing {column}.")
    for column in (
        "selection_exclusion_stage",
        "selection_exclusion_reason",
        "candidate_index_in_stored_order",
        "economically_evaluated",
        "local_virtual_calculation_resolved",
        "local_virtual_calculation_stop_reason",
    ):
        if column in SUMMARY_COLUMNS or column in PARTY_COLUMNS:
            raise RuntimeError(f"Existing transaction CSV absorbed audit column {column}.")
    audit_source = ast.get_source_segment(
        source, _function_node(tree, "_build_east_t35_all_candidate_audit")
    )
    if audit_source is None:
        raise RuntimeError("Could not read the east T=35 audit builder.")
    if "EAST_T35_AUDIT_KEY" not in audit_source:
        raise RuntimeError("East T=35 audit builder must reject other decisions.")
    for name in (
        "EAST_T35_EXPECTED_CONCRETE_CANDIDATE_COUNT",
        "EAST_T35_EXPECTED_FIFO_PASSED_COUNT",
        "EAST_T35_EXPECTED_FIFO_FAILED_COUNT",
        "for stored_index, concrete_set in enumerate(concrete_sets)",
        "trade_result.buyers_sorted",
        "trade_result.sellers_sorted",
        "trade_result.nonparticipating_visits_sorted",
        "trade_result.trade_scope",
        "_post_trade_local_ranks(",
        "_require_same_population_and_continuous_local_ranks(",
        "matched_local.traffic_observation_records",
        "matched_economic.buyer_economic_records",
        "matched_economic.seller_economic_records",
        "matched_economic.total_buyer_value_G",
        "matched_economic.total_required_compensation_R",
        "matched_economic.surplus",
        "gross_time_value_G_b",
        "required_compensation_R_s",
        "predicted_time_difference_timesteps",
        "preserves_inlink_fifo",
        "same_inlink_fifo_preserved",
        "rng_was_used",
        "EXCLUSION_STAGE_FIFO_FAILED",
        "EXCLUSION_STAGE_LOCAL_UNRESOLVED",
        "EXCLUSION_STAGE_ECONOMICALLY_INFEASIBLE",
        "EXCLUSION_STAGE_FEASIBLE_NOT_SELECTED",
        "EXCLUSION_STAGE_SELECTED",
        "_collector_snapshot",
    ):
        if name not in audit_source:
            raise RuntimeError(f"East T=35 audit builder is missing {name}.")
    if audit_source.count("traffic_observation_records") != 1:
        raise RuntimeError(
            "East T=35 audit must read traffic observations from one local result."
        )
    if "selected_local" in audit_source:
        raise RuntimeError(
            "East T=35 audit must not reuse the selected candidate local result."
        )
    if "contiguous" in audit_source:
        raise RuntimeError("East T=35 audit must not filter buyer contiguity.")
    for literal in ("veh_ee_6", "veh_es_7", "veh_wn_3", "veh_en_5"):
        if literal in audit_source:
            raise RuntimeError(
                "East T=35 audit must not hardcode candidate identities or economics."
            )
    capture_source = ast.get_source_segment(
        source, _function_node(tree, "_capture_target_node")
    )
    if capture_source is None:
        raise RuntimeError("Could not read _capture_target_node.")
    if capture_source.count("_build_east_t35_all_candidate_audit(") != 1:
        raise RuntimeError("East T=35 audit builder must be called once.")
    if "if decision_key == EAST_T35_AUDIT_KEY:" not in capture_source:
        raise RuntimeError("East T=35 audit must run only for east_intersection T=35.")
    collector_source = ast.get_source_segment(
        source, _function_node(tree, "_collector_snapshot")
    )
    if collector_source is None or "get_baseline_visit_snapshot" not in collector_source:
        raise RuntimeError(
            "Baseline arrival A must come from collector.get_baseline_visit_snapshot."
        )


def _assert_official_rank_sources(source: str, tree: ast.Module) -> None:
    """Check retrieval sources without running the long simulation."""
    baseline_source = ast.get_source_segment(
        source, _function_node(tree, "_baseline_local_ranks")
    )
    post_trade_source = ast.get_source_segment(
        source, _function_node(tree, "_post_trade_local_ranks")
    )
    ledger_source = ast.get_source_segment(
        source, _function_node(tree, "_require_ledger_assigned_rank")
    )
    history_source = ast.get_source_segment(
        source, _function_node(tree, "_actual_passage_records_in_stored_order")
    )
    history_rank_source = ast.get_source_segment(
        source, _function_node(tree, "_actual_passage_ranks_in_stored_order")
    )
    attach_source = ast.get_source_segment(
        source, _function_node(tree, "_attach_node_continuous_ranks")
    )
    capture_node = _function_node(tree, "_capture_target_node")
    capture_source = ast.get_source_segment(source, capture_node)
    if baseline_source is None or "for candidate_visit in candidate_visits:" not in baseline_source:
        raise RuntimeError("baseline_local_rank must walk saved candidate_visits in order.")
    if baseline_source is None or "sorted(" in baseline_source:
        raise RuntimeError("baseline_local_rank must not sort candidate_visits.")
    if post_trade_source is None or "trade_result.assigned_rank(visit_key)" not in post_trade_source:
        raise RuntimeError(
            "post_trade_local_rank must come from general trade rank assigned_rank."
        )
    if post_trade_source is None or "binding_rank" in post_trade_source:
        raise RuntimeError("post_trade_local_rank must not be read from binding_rank.")
    if (
        ledger_source is None
        or "order_control_tvt_rank_states_by_node_name" not in ledger_source
        or "rank_state.assigned_rank(visit_key)" not in ledger_source
    ):
        raise RuntimeError("assigned_rank must come from the real World node rank ledger.")
    if (
        history_source is None
        or "order_control_tvt_mp_actual_node_passage_history_registry" not in history_source
    ):
        raise RuntimeError(
            "actual_node_passage_rank must come from the actual passage history registry."
        )
    if history_source is None or "sorted(" in history_source:
        raise RuntimeError("Actual passage history must be read in stored order.")
    if (
        history_rank_source is None
        or "_actual_passage_records_in_stored_order(" not in history_rank_source
        or "sorted(" in history_rank_source
    ):
        raise RuntimeError(
            "actual_node_passage_rank must reuse the stored history order."
        )
    context_source = ast.get_source_segment(
        source, _function_node(tree, "_load_node_continuous_rank_sides")
    )
    if context_source is None or "rank_state.assigned_rank(" not in context_source:
        raise RuntimeError(
            "Mismatch context must read assigned_rank from the node rank ledger."
        )
    if (
        context_source is None
        or "_actual_passage_records_in_stored_order(" not in context_source
        or "sorted(" in context_source
    ):
        raise RuntimeError(
            "Mismatch context must read actual passage history in stored order."
        )
    if attach_source is None or "establishment.ledger_assigned_rank" not in attach_source:
        raise RuntimeError("assigned_rank must be checked against ledger_assigned_rank.")
    if attach_source is None or "binding_sequence_auxiliary_rank" in attach_source:
        raise RuntimeError(
            "Node-continuous ranks must not be filled from the binding sequence."
        )
    if capture_source is None:
        raise RuntimeError("Could not read _capture_target_node.")
    if 'key=lambda party: party["post_trade_local_rank"]' not in capture_source:
        raise RuntimeError(
            "candidate_order_visit_keys must follow post_trade_local_rank."
        )
    if 'key=lambda party: party["baseline_local_rank"]' not in capture_source:
        raise RuntimeError(
            "baseline_order_visit_keys must follow baseline_local_rank."
        )
    if "candidate_binding_rank" in capture_source or "binding_sequence_auxiliary_rank" in capture_source:
        raise RuntimeError(
            "Summary candidate order must not use the binding-sequence rank."
        )
    rank_change_source = ast.get_source_segment(
        source, _function_node(tree, "_require_rank_change_matches_local_ranks")
    )
    if (
        rank_change_source is None
        or "baseline_local_rank - post_trade_local_rank" not in rank_change_source
    ):
        raise RuntimeError(
            "rank_change must be checked as baseline_local_rank minus post_trade_local_rank."
        )


def _assert_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if TARGET_DECISION_KEYS != (
        (EAST_NODE, 35),
        (WEST_NODE, 310),
        (WEST_NODE, 316),
        (WEST_NODE, 331),
        (WEST_NODE, 338),
        (WEST_NODE, 344),
        (EAST_NODE, 582),
    ):
        raise RuntimeError("Target keys are not the seven post-fix decisions.")
    if set(EXPECTED_BUYER_SELLER_COUNTS) != set(TARGET_DECISION_KEYS):
        raise RuntimeError("Expected party counts do not cover the seven keys.")
    if OUTPUT_FILE_NAMES != (
        SUMMARY_CSV_NAME,
        PARTIES_CSV_NAME,
        EAST_T35_AUDIT_CSV_NAME,
        NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_CSV_NAME,
        NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_CSV_NAME,
        NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_CSV_NAME,
    ):
        raise RuntimeError(
            "Diagnostic output must be the two transaction CSVs, "
            "east_t35_all_candidate_audit.csv, "
            "node_continuous_rank_mismatch_context.csv, "
            "node_continuous_rank_mismatch_vehicle_timeline.csv, and "
            "node_continuous_rank_mismatch_physical_trace.csv."
        )
    if len(OUTPUT_FILE_NAMES) != 6:
        raise RuntimeError("Diagnostic output must be six CSV files.")
    if PHYSICAL_TRACE_TIMESTEP_START != 324 or PHYSICAL_TRACE_TIMESTEP_END != 334:
        raise RuntimeError(
            "The limited physical-trace window must stay at real-world T=324 through 334."
        )
    if PHYSICAL_TRACE_REASON_ORDER != (
        "not_arrived",
        "not_inlink_physical_head",
        "clearance_not_satisfied",
        "inlink_outflow_capacity_insufficient",
        "node_flow_capacity_insufficient",
        "outlink_inflow_capacity_insufficient",
        "outlink_entrance_space_insufficient",
        "none_passed",
        "not_scanned_after_clearance_stop",
        "already_passed",
        "not_present_at_target_node",
        "route_unavailable",
    ):
        raise RuntimeError(
            "Physical-trace reasons are not in production judgment order."
        )
    for column in (
        "baseline_arrival_timestep",
        "actual_node_arrival_timestep",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "actual_passage_timestep",
        "role_at_mismatch_transaction",
        "timeline_data_status",
        "timeline_data_note",
    ):
        if column not in NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_COLUMNS:
            raise RuntimeError(f"Timeline CSV is missing {column}.")
    if "actual_node_arrival_timestep" in PARTY_COLUMNS:
        raise RuntimeError("Parties CSV must not gain actual_node_arrival_timestep.")
    if "actual_node_arrival_timestep" in SUMMARY_COLUMNS:
        raise RuntimeError("Summary CSV must not gain actual_node_arrival_timestep.")
    if "actual_node_arrival_timestep" in EAST_T35_AUDIT_COLUMNS:
        raise RuntimeError("East audit CSV must not gain actual_node_arrival_timestep.")
    if "actual_node_arrival_timestep" in NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_COLUMNS:
        raise RuntimeError("Context CSV must not gain actual_node_arrival_timestep.")
    for column in NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_COLUMNS:
        if "difference" in column or "minus" in column or column.startswith("delta"):
            raise RuntimeError(f"Physical trace must not add a difference column {column}.")
    for column in NODE_CONTINUOUS_RANK_MISMATCH_VEHICLE_TIMELINE_COLUMNS:
        if "difference" in column or "minus" in column or column.startswith("delta"):
            raise RuntimeError(f"Timeline must not add a difference column {column}.")
    for column in (
        "real_world_timestep",
        "scan_sequence_index",
        "first_blocking_reason",
        "action",
        "was_inlink_physical_head",
        "clearance_satisfied",
        "actual_node_arrival_timestep",
        "passed_this_scan",
    ):
        if column not in NODE_CONTINUOUS_RANK_MISMATCH_PHYSICAL_TRACE_COLUMNS:
            raise RuntimeError(f"Physical trace CSV is missing {column}.")
    if NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_CSV_NAME != (
        "node_continuous_rank_mismatch_context.csv"
    ):
        raise RuntimeError("Node-continuous rank context CSV name changed.")
    for column in (
        "mismatch_decision_timestep",
        "mismatch_node_name",
        "mismatch_visit_key",
        "mismatch_assigned_rank",
        "mismatch_actual_node_passage_rank",
        "context_visit_key",
        "actual_route_next_link_name",
        "is_mismatch_visit",
        "is_between_mismatch_ranks",
        "rank_relation_note",
    ):
        if column in SUMMARY_COLUMNS or column in PARTY_COLUMNS or column in EAST_T35_AUDIT_COLUMNS:
            raise RuntimeError(
                f"Existing diagnostic CSV absorbed context column {column}."
            )
    for column in (
        "mismatch_decision_timestep",
        "mismatch_node_name",
        "mismatch_visit_key",
        "mismatch_assigned_rank",
        "mismatch_actual_node_passage_rank",
        "context_visit_key",
        "assigned_rank",
        "actual_node_passage_rank",
        "actual_passage_timestep",
        "formal_route_next_link_name",
        "actual_route_next_link_name",
        "inlink_name",
        "is_mismatch_visit",
        "is_between_mismatch_ranks",
        "rank_relation_note",
    ):
        if column not in NODE_CONTINUOUS_RANK_MISMATCH_CONTEXT_COLUMNS:
            raise RuntimeError(f"Context CSV is missing {column}.")
    for note in (
        "exact_match",
        "actual_earlier_than_assigned",
        "actual_later_than_assigned",
        "assigned_only_actual_unobserved",
        "actual_only_no_assigned_rank",
    ):
        if note not in source:
            raise RuntimeError(f"Context rank relation note {note} is missing.")
    for function_name in (
        "_build_node_continuous_rank_mismatch_context",
        "_load_node_continuous_rank_sides",
        "_selected_node_continuous_rank_mismatches",
        "_mismatch_rank_bounds",
        "_context_visit_keys_in_saved_order",
    ):
        function_source = ast.get_source_segment(
            source, _function_node(tree, function_name)
        )
        if function_source is None:
            raise RuntimeError(f"Could not read {function_name}.")
        for literal in ("veh_wn_116", "200", "201", "331"):
            if literal in function_source:
                raise RuntimeError(
                    f"{function_name} hardcodes context identity {literal}."
                )
    if SUMMARY_CSV_NAME != "multiple_buyer_transaction_summary.csv":
        raise RuntimeError("Summary CSV name changed.")
    if PARTIES_CSV_NAME != "multiple_buyer_transaction_parties.csv":
        raise RuntimeError("Parties CSV name changed.")
    if len(SUMMARY_COLUMNS) != 33 or len(PARTY_COLUMNS) != 34:
        raise RuntimeError(
            "Transaction CSV column counts are not the four-rank parties schema."
        )
    official_rank_columns = (
        "baseline_local_rank",
        "post_trade_local_rank",
        "assigned_rank",
        "actual_node_passage_rank",
    )
    for column in official_rank_columns:
        if column not in PARTY_COLUMNS:
            raise RuntimeError(f"Party CSV is missing {column}.")
    first_rank = PARTY_COLUMNS.index("baseline_local_rank")
    if PARTY_COLUMNS[first_rank : first_rank + 4] != official_rank_columns:
        raise RuntimeError("The four official ranks are not adjacent in the parties CSV.")
    if "binding_sequence_auxiliary_rank" not in PARTY_COLUMNS:
        raise RuntimeError("Party CSV is missing the binding-sequence auxiliary rank.")
    auxiliary_index = PARTY_COLUMNS.index("binding_sequence_auxiliary_rank")
    if auxiliary_index < first_rank + 4:
        raise RuntimeError(
            "binding_sequence_auxiliary_rank must stay after the four official ranks."
        )
    if "candidate_binding_rank" in PARTY_COLUMNS or "actual_rank" in PARTY_COLUMNS:
        raise RuntimeError("Parties CSV still uses a substitute rank column.")
    for column in (
        "baseline_arrival_timestep",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "same_inlink_fifo_predecessor_visit_keys",
        "same_inlink_fifo_successor_visit_keys",
        "same_inlink_fifo_preserved",
    ):
        if column not in PARTY_COLUMNS:
            raise RuntimeError(f"Party CSV is missing {column}.")
    for column in (
        "right_of_entry_baseline_arrival_timestep",
        "right_of_entry_baseline_rank",
        "fifo_inspection_passed",
        "fifo_violation_count",
    ):
        if column not in SUMMARY_COLUMNS:
            raise RuntimeError(f"Summary CSV is missing {column}.")
    if "east_intersection" not in {key[0] for key in TARGET_DECISION_KEYS}:
        raise RuntimeError("East decisions are missing.")
    west_timesteps = tuple(
        timestep for node_name, timestep in TARGET_DECISION_KEYS if node_name == WEST_NODE
    )
    if west_timesteps != (310, 316, 331, 338, 344):
        raise RuntimeError("West multiple-buyer decisions are not the five saved keys.")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and (
            "motion" in node.name or "scan_event" in node.name
        ):
            raise RuntimeError("This diagnostic must not record motion or scan events.")
    research_csv_calls = []

    class _CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "write_tvt_mp_research_output_csv":
                research_csv_calls.append(node)
            self.generic_visit(node)

    _CallVisitor().visit(tree)
    if len(research_csv_calls) != 0:
        raise RuntimeError("This diagnostic must not write the research-output CSV set.")
    capture_source = ast.get_source_segment(
        source, _function_node(tree, "_capture_target_decision")
    )
    if capture_source is None or "len(target_nodes) == 0" not in capture_source:
        raise RuntimeError("Non-target decisions must return before object traversal.")
    _assert_wrapper_returns_original_once(tree)
    _assert_trial_settings()
    _assert_production_fields()
    main_source = ast.get_source_segment(source, _function_node(tree, "main"))
    if main_source is None or "build_tvt_mp_research_output" not in main_source:
        raise RuntimeError("Actual fields must come from the same simulation bundle.")
    if "_attach_node_continuous_ranks(world)" not in main_source:
        raise RuntimeError(
            "Node-continuous ranks must be read from the real World after simulation."
        )
    if "_build_node_continuous_rank_mismatch_context(world)" not in main_source:
        raise RuntimeError(
            "Node-continuous rank mismatch context must be built from the real World."
        )
    _assert_main_block_static_validate_contract(tree)
    _assert_official_rank_sources(source, tree)
    build_parties_source = ast.get_source_segment(
        source, _function_node(tree, "_build_parties")
    )
    if build_parties_source is None:
        raise RuntimeError("Could not read _build_parties for static validation.")
    if '"vehicle_id": binding_visit.vehicle_id' not in build_parties_source:
        raise RuntimeError("Party dict must store vehicle_id from binding_visit.vehicle_id.")
    if (
        'snapshot["vehicle_id"] != binding_visit.vehicle_id'
        not in build_parties_source
    ):
        raise RuntimeError(
            "Party build must compare collector snapshot vehicle_id to binding_visit.vehicle_id."
        )
    if "binding_visit.vehicle_id" not in build_parties_source:
        raise RuntimeError("vehicle_id must come from OrderControlTvtMpLocalBindingRankVisit.")
    fifo_source = ast.get_source_segment(
        source, _function_node(tree, "_annotate_same_inlink_fifo")
    )
    if fifo_source is None or 'party["vehicle_id"]' not in fifo_source:
        raise RuntimeError("_annotate_same_inlink_fifo must sort by party['vehicle_id'].")
    if "vehicle_id" in PARTY_COLUMNS:
        raise RuntimeError("vehicle_id must not be a parties CSV output column.")
    if "_build_vehicle_timeline_rows()" not in main_source:
        raise RuntimeError("Vehicle timeline rows must be built after the simulation.")
    if "_build_physical_trace_rows(world)" not in main_source:
        raise RuntimeError("Physical trace rows must be built from the real World.")
    arrival_source = ast.get_source_segment(
        source, _function_node(tree, "_stored_actual_node_arrival")
    )
    if arrival_source is None or "GATE.actual_node_arrivals" not in arrival_source:
        raise RuntimeError("Actual node arrival must be read from the arrival observation.")
    for forbidden in ("baseline_arrival", "earliest_arrival", "actual_passage", "passage_timestep"):
        if forbidden in arrival_source:
            raise RuntimeError(
                "actual_node_arrival_timestep must not be taken from "
                f"{forbidden}."
            )
    for function_name in (
        "_build_vehicle_timeline_rows",
        "_build_physical_trace_rows",
        "_synthetic_trace_csv_row",
        "_append_trace_rows_for_timestep",
        "_swapped_partner_row",
        "_classify_rank_mismatch",
        "_remember_real_world_node_arrival",
        "_physical_trace_window_applies",
        "_vehicle_timeline_row",
        "_read_same_decision_baseline_arrival",
        "_baseline_arrival_for_timeline",
        "_timeline_data_status",
        "_passage_identity_before_transfer",
        "_record_passed_for_saved_visit",
        "_wrapped_transfer_one_vehicle_between_links",
    ):
        function_source = ast.get_source_segment(
            source, _function_node(tree, function_name)
        )
        if function_source is None:
            raise RuntimeError(f"Could not read {function_name}.")
        for literal in ("veh_wn_116", "veh_ws_85", "200", "201", "329", "331"):
            if literal in function_source:
                raise RuntimeError(
                    f"{function_name} hardcodes trace identity {literal}."
                )
    for status_name in (
        "complete_for_trade_scope_visit",
        "context_visit_outside_trade_scope",
        "actual_arrival_unavailable",
        "candidate_prediction_unavailable",
        "actual_unobserved_at_evaluation_end",
        "explained_by_physical_state",
        "implementation_inconsistency_suspected",
        "insufficient_trace",
        "not_observable",
    ):
        if status_name not in source:
            raise RuntimeError(f"Diagnostic status {status_name} is missing.")
    _assert_observation_hooks_call_original_once(tree)
    _assert_context_baseline_and_passage_identity(source, tree)
    _assert_east_t35_audit_static_contract(source, tree)


def _assert_context_baseline_and_passage_identity(source: str, tree: ast.Module) -> None:
    """Context Baseline A and the passed VisitKey stay on their formal sources."""
    baseline_source = ast.get_source_segment(
        source, _function_node(tree, "_read_same_decision_baseline_arrival")
    )
    timeline_source = ast.get_source_segment(
        source, _function_node(tree, "_vehicle_timeline_row")
    )
    prediction_source = ast.get_source_segment(
        source, _function_node(tree, "_prediction_passages_for_timeline")
    )
    capture_source = ast.get_source_segment(
        source, _function_node(tree, "_capture_target_node")
    )
    if baseline_source is None or timeline_source is None or prediction_source is None:
        raise RuntimeError("Could not read Baseline A timeline sources.")
    if capture_source is None or '"baseline_collector": columns["collector"]' not in capture_source:
        raise RuntimeError(
            "Each captured decision must keep its own baseline collector reference."
        )
    if "get_baseline_visit_snapshot(visit_key[0], visit_key[1])" not in baseline_source:
        raise RuntimeError(
            "Context Baseline A must use get_baseline_visit_snapshot(vehicle_name, visit_id)."
        )
    if 'snapshot.get("node_name")' not in baseline_source:
        raise RuntimeError("Collector snapshot node_name must be checked before use.")
    if 'context_row["mismatch_node_name"]' not in timeline_source:
        raise RuntimeError("Timeline Baseline A must be keyed by mismatch_node_name.")
    if 'context_row["mismatch_decision_timestep"]' not in timeline_source:
        raise RuntimeError(
            "Timeline Baseline A must be keyed by mismatch_decision_timestep."
        )
    if 'context_row["context_visit_key"]' not in timeline_source:
        raise RuntimeError("Timeline Baseline A must be keyed by context_visit_key.")
    if "GATE.decisions.get((node_name, decision_timestep))" not in timeline_source:
        raise RuntimeError(
            "Timeline Baseline A must use only the mismatch decision's saved decision."
        )
    for function_name in (
        "_read_same_decision_baseline_arrival",
        "_baseline_arrival_for_timeline",
        "_timeline_data_status",
        "_vehicle_timeline_row",
    ):
        function_source = ast.get_source_segment(
            source, _function_node(tree, function_name)
        )
        if function_source is None or "316" in function_source:
            raise RuntimeError(
                f"{function_name} must not fix Baseline A retrieval at T=316."
            )
    for forbidden in (
        "actual_node_arrival",
        "earliest_arrival",
        "actual_passage",
        "baseline_passage",
        "candidate_passage",
        "assigned_rank",
        "actual_node_passage_rank",
    ):
        if forbidden in baseline_source:
            raise RuntimeError(
                "baseline_arrival_timestep must not be filled from " f"{forbidden}."
            )
    for forbidden in ("actual_passage", "actual_node_arrival", "earliest_arrival"):
        if forbidden in prediction_source:
            raise RuntimeError(
                "Candidate passage must not be filled from " f"{forbidden}."
            )
    if "traffic_passage_by_visit" not in prediction_source:
        raise RuntimeError(
            "Candidate passage must come from this decision's traffic observation."
        )
    wrapper = _function_node(tree, "_wrapped_transfer_one_vehicle_between_links")
    for child in ast.walk(wrapper):
        if isinstance(child, ast.Try):
            raise RuntimeError(
                "Passage wrapper must not record passed from try/finally."
            )
    save_index = None
    original_index = None
    record_index = None
    for index, stmt in enumerate(wrapper.body):
        called_names = []
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                called_names.append(_call_callee_name(node))
        if "_passage_identity_before_transfer" in called_names:
            save_index = index
        if "original_transfer_one_vehicle_between_links" in called_names:
            original_index = index
        if "_record_passed_for_saved_visit" in called_names:
            record_index = index
    if save_index is None or original_index is None or record_index is None:
        raise RuntimeError("Passage wrapper must save, call production, then record.")
    if not save_index < original_index < record_index:
        raise RuntimeError(
            "Passed VisitKey must be saved before production and recorded only after it returns."
        )
    wrapper_source = ast.get_source_segment(source, wrapper)
    record_source = ast.get_source_segment(
        source, _function_node(tree, "_record_passed_for_saved_visit")
    )
    if wrapper_source is None or "return result" not in wrapper_source:
        raise RuntimeError("Passage wrapper must return the production result.")
    if wrapper_source is None or "order_control_current_visit" in wrapper_source:
        raise RuntimeError(
            "Passage wrapper must not rebuild the passed VisitKey from the current visit."
        )
    if record_source is None or "order_control_current_visit" in record_source:
        raise RuntimeError(
            "Passed recording must not read the current visit after production."
        )
    if record_source is None or 'event["action"] = "passed"' not in record_source:
        raise RuntimeError("Passed recording must set action to passed.")


def main() -> int:
    _assert_before_simulation()
    original_recursion_limit = sys.getrecursionlimit()
    world = None
    try:
        if original_recursion_limit < extended_trial.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(extended_trial.WORLD_COPY_RECURSION_LIMIT)
        vot_rng = np.random.default_rng(extended_trial.VOT_SEED)
        vot_values = extended_trial.generate_vehicle_vots(
            vot_rng, len(extended_trial.VEHICLE_SPECS)
        )
        vot_records = extended_trial.build_vehicle_vot_records(
            extended_trial.VEHICLE_SPECS, vot_values
        )
        world = extended_trial.build_world_and_network()
        extended_trial.add_vehicles_to_world(
            world, extended_trial.VEHICLE_SPECS, vot_records
        )
        world.finalize_scenario()
        GATE.real_world = world
        install_driver_hook()
        try:
            world.exec_simulation()
        finally:
            restore_driver_hook()
            GATE.real_world = None
        if world.T != extended_trial.EXPECTED_WORLD_T_AFTER_SIM:
            raise RuntimeError(
                f"World.T after simulation is {world.T}, expected "
                f"{extended_trial.EXPECTED_WORLD_T_AFTER_SIM}."
            )
        bundle = build_tvt_mp_research_output(world, extended_trial.SCENARIO_NAME)
        _attach_research_output(bundle)
        _attach_node_continuous_ranks(world)
        GATE.node_continuous_rank_mismatch_context_rows = (
            _build_node_continuous_rank_mismatch_context(world)
        )
        GATE.vehicle_timeline_rows = _build_vehicle_timeline_rows()
        GATE.physical_trace_rows = _build_physical_trace_rows(world)
        errors = _collect_end_errors()
        _write_outputs()
        _print_node_continuous_rank_mismatch_summary()
        _print_rank_mismatch_physical_summary()
        if len(errors) != 0:
            raise RuntimeError("\n".join(errors))
    finally:
        sys.setrecursionlimit(original_recursion_limit)
    print(
        f"Wrote {len(TARGET_DECISION_KEYS)} transactions and "
        f"{EAST_T35_AUDIT_CSV_NAME} to {OUTPUT_DIR}."
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        _assert_static_contract()
        print("Static contract validation passed.")
    else:
        raise SystemExit(main())
