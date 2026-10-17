"""
Post-fix audit of seven multiple-buyer TVT-MP transactions.

Replays the extended-south-pulse two-cross trial once. At seven decision
keys only, reads the saved driver result: baseline arrival A from the
fork collector, binding rank and economics from the selected candidate,
baseline rank from the saved candidate-visit order and establishment
records, right-of-entry from the saved node selection result, and FIFO
pass/fail counts for that decision's concrete candidates.

After the same simulation, actual passage and ex-post fields are read
from the in-memory research-output bundle. This script does not read an
existing CSV to fill those fields, does not write the research-output
CSV set, and does not keep scan events, motion traces, or non-target
decisions.

The same T=35 east_intersection driver result also supplies one
all-candidate audit. Every concrete buyer candidate at that decision is
matched across the saved stages by buyer VisitKeys, node name, and
decision timestep. Other decisions are not expanded.

Clearance-stop and temporary-skip timelines are not recorded here.
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
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpTradeExPostEvaluationStatus,
)
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
OUTPUT_FILE_NAMES = (
    SUMMARY_CSV_NAME,
    PARTIES_CSV_NAME,
    EAST_T35_AUDIT_CSV_NAME,
)

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
    "baseline_rank",
    "candidate_binding_rank",
    "actual_rank",
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
    "baseline_rank",
    "candidate_rank",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "predicted_time_difference_timesteps",
    "declared_vot_per_second",
    "buyer_value_G_b",
    "seller_required_compensation_R_s",
    "same_inlink_fifo_preserved",
)


class _DiagnosticGate:
    def __init__(self) -> None:
        self.original_run_tvt_mp_driver = None
        self.installed = False
        self.real_world = None
        self.decisions: dict[tuple[str, int], dict] = {}
        self.east_t35_audit_rows: list[dict] = []


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


def _baseline_rank_by_visit_key(candidate_visits, node_name: str, timestep: int) -> dict:
    """1-based position in the saved candidate_visits tuple.

    Production treats that stored order as the official baseline local rank.
    This walk only reads the tuple. It does not call atomic-apply helpers.
    """
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
                f"{_visit_text(visit_key)}."
            )
        ranks[visit_key] = position
    return ranks


def _establishment_baseline_rank(world, timestep: int, node_name: str, visit_key):
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
    if found is None:
        return None
    if type(found.baseline_local_rank) is not int:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: establishment baseline_local_rank "
            f"for {_visit_text(visit_key)} is {found.baseline_local_rank!r}."
        )
    return found.baseline_local_rank


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
    candidate_visit_ranks: dict,
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
        if visit_key not in candidate_visit_ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "is missing from saved candidate_visits."
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
        baseline_rank = _resolve_baseline_rank(
            world,
            timestep,
            node_name,
            visit_key,
            role_name,
            candidate_visit_ranks[visit_key],
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
                "baseline_rank": baseline_rank,
                "candidate_binding_rank": binding_visit.binding_rank,
                "actual_rank": None,
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
    binding_ranks = [party["candidate_binding_rank"] for party in parties]
    if len(binding_ranks) != len(set(binding_ranks)):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade-scope binding ranks are not unique."
        )
    baseline_ranks = [party["baseline_rank"] for party in parties]
    if len(baseline_ranks) != len(set(baseline_ranks)):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade-scope baseline ranks are not unique."
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
                party["baseline_rank"],
                party["baseline_arrival_timestep"],
                party["arrival_tiebreaker"],
                party["vehicle_id"],
                party["visit_key_tuple"],
            ),
        )
        candidate_position = {}
        candidate_order = sorted(
            inlink_parties,
            key=lambda party: (party["candidate_binding_rank"], party["visit_key_tuple"]),
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
    """Recompare same-inlink order using each row's own baseline and candidate ranks."""
    grouped: dict[str, list[dict]] = {}
    for party in parties:
        grouped.setdefault(party["inlink_name"], []).append(party)
    any_violation = False
    for inlink_parties in grouped.values():
        for party in inlink_parties:
            party["same_inlink_fifo_preserved"] = True
        for left_index, left in enumerate(inlink_parties):
            for right in inlink_parties[left_index + 1 :]:
                if left["baseline_rank"] == right["baseline_rank"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: baseline ranks "
                        "are not unique inside one inlink."
                    )
                if left["candidate_rank"] == right["candidate_rank"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: candidate ranks "
                        "are not unique inside one inlink."
                    )
                baseline_before = left["baseline_rank"] < right["baseline_rank"]
                candidate_before = left["candidate_rank"] < right["candidate_rank"]
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
    baseline_ranks = _baseline_rank_by_visit_key(
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
        assigned_ranks = {}
        for visit_key in trade_scope:
            try:
                rank_value = trade_result.assigned_rank(visit_key)
            except ValueError as error:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: {candidate_identity} "
                    f"has no general trade rank for {_visit_text(visit_key)}."
                ) from error
            if type(rank_value) is not int or rank_value < 1:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: candidate rank for "
                    f"{_visit_text(visit_key)} is {rank_value!r}."
                )
            assigned_ranks[visit_key] = rank_value
        if len(set(assigned_ranks.values())) != len(assigned_ranks):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {candidate_identity} "
                "candidate ranks are not unique."
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
            by_binding = tuple(
                sorted(trade_scope, key=lambda key: binding_by_key[key].binding_rank)
            )
            by_trade = tuple(
                sorted(trade_scope, key=lambda key: assigned_ranks[key])
            )
            if by_binding != by_trade:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: {candidate_identity} "
                    "binding rank order does not match its general trade rank."
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
                    "baseline_rank": baseline_rank,
                    "candidate_rank": assigned_ranks[visit_key],
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
        baseline_order = sorted(visit_rows, key=lambda row: row["baseline_rank"])
        candidate_order = sorted(visit_rows, key=lambda row: row["candidate_rank"])
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
    candidate_visit_ranks = _baseline_rank_by_visit_key(
        candidate_visit_node.candidate_visits, node_name, timestep
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
    candidate_identity = _candidate_identity(node_name, buyers_sorted)
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
    baseline_order = sorted(parties, key=lambda party: party["baseline_rank"])
    candidate_order = sorted(parties, key=lambda party: party["candidate_binding_rank"])
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
    driver_module.run_tvt_mp_driver = wrapped_run_tvt_mp_driver
    GATE.installed = True


def restore_driver_hook() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_run_tvt_mp_driver
    GATE.original_run_tvt_mp_driver = None
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
            party["actual_rank"] = visit_row.actual_node_passage_rank
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
            if observation == ACTUAL_UNOBSERVED:
                if actual_passage is not None:
                    errors.append(
                        f"{label}: {party['visit_key']} is unobserved but has actual passage."
                    )
            elif observation is None:
                errors.append(f"{label}: {party['visit_key']} has no actual observation status.")
            elif actual_passage is None:
                errors.append(
                    f"{label}: {party['visit_key']} is observed but actual passage is missing."
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
            key=lambda party: (party["baseline_rank"], party["visit_key_tuple"]),
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
        "baseline_rank",
        "candidate_rank",
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
        "candidate_rank",
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
        "trade_result.assigned_rank",
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
    ):
        raise RuntimeError(
            "Diagnostic output must stay the two transaction CSVs plus "
            "east_t35_all_candidate_audit.csv."
        )
    if SUMMARY_CSV_NAME != "multiple_buyer_transaction_summary.csv":
        raise RuntimeError("Summary CSV name changed.")
    if PARTIES_CSV_NAME != "multiple_buyer_transaction_parties.csv":
        raise RuntimeError("Parties CSV name changed.")
    if len(SUMMARY_COLUMNS) != 33 or len(PARTY_COLUMNS) != 32:
        raise RuntimeError("Existing transaction CSV columns changed.")
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
    _assert_main_block_static_validate_contract(tree)
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
    _assert_east_t35_audit_static_contract(source, tree)


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
        errors = _collect_end_errors()
        _write_outputs()
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
