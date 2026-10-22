"""
Read-only diagnostic for every established TVT-MP transaction and every
considered candidate in the four-cross 600-vehicle trial.

One simulation is run. The real-world driver result is saved as it returns.
Baseline arrival is read from that decision's baseline collector. Actual
arrival is recorded only on the real World. Unresolved candidates keep a
missing candidate passage as missing. Non-selected candidates do not receive
actual passage, actual rank, payment, or compensation.
"""

from __future__ import annotations

import ast
import csv
import datetime
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualNodePassageRecord,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateTrafficObservationRecord,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionStatus,
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
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpBuyerPaymentRecord,
    OrderControlTvtMpSellerCompensationRecord,
    OrderControlTvtNodeMpPaymentAndCompensationResult,
)
from uxsim.order_control_tvt_mp_research_output import build_tvt_mp_research_output
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
)

import run_tvt_mp_four_cross_intersections_grid_medium_all_participating_trial as four_cross_trial


SCENARIO_NAME = four_cross_trial.SCENARIO_NAME
DIAGNOSTIC_SCRIPT_NAME = SCRIPT_PATH.name
OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900_timestep_seed_1_all_transactions_and_candidates_diagnostic"
    )
)

ESTABLISHED_SUMMARY_CSV_NAME = "all_established_transactions_summary.csv"
ESTABLISHED_PARTIES_CSV_NAME = "all_established_transaction_parties.csv"
CANDIDATE_SUMMARY_CSV_NAME = "all_considered_candidates_summary.csv"
CANDIDATE_PARTIES_CSV_NAME = "all_considered_candidate_parties.csv"
SPECIAL_PARTIES_CSV_NAME = "special_established_transaction_parties.csv"
SUMMARY_TEXT_NAME = "diagnostic_summary.txt"
MANIFEST_JSON_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    ESTABLISHED_SUMMARY_CSV_NAME,
    ESTABLISHED_PARTIES_CSV_NAME,
    CANDIDATE_SUMMARY_CSV_NAME,
    CANDIDATE_PARTIES_CSV_NAME,
    SPECIAL_PARTIES_CSV_NAME,
    SUMMARY_TEXT_NAME,
    MANIFEST_JSON_NAME,
)

PAYMENT_BALANCE_REL_TOL = 1e-12
PAYMENT_BALANCE_ABS_TOL = 1e-12

EXPECTED_WORLD_T = 900
EXPECTED_ESTABLISHED_TRANSACTION_COUNT = 307
EXPECTED_BUYER_VISIT_COUNT = 361
EXPECTED_SELLER_VISIT_COUNT = 486
EXPECTED_TRADE_SCOPE_PARTY_OBSERVATION_COUNT = 847
EXPECTED_CANDIDATE_EQUALS_ACTUAL_COUNT = 842
EXPECTED_CANDIDATE_DIFFERS_FROM_ACTUAL_COUNT = 5
EXPECTED_ACTUAL_UNOBSERVED_COUNT = 0
EXPECTED_MULTIPLE_BUYER_TRANSACTION_COUNT = 48
EXPECTED_MULTIPLE_SELLER_TRANSACTION_COUNT = 152
EXPECTED_BOTH_MULTIPLE_TRANSACTION_COUNT = 15
EXPECTED_EITHER_MULTIPLE_TRANSACTION_COUNT = 185
EXPECTED_ROUTE_MISMATCH_TRANSACTION_COUNT = 5
EXPECTED_PASSAGE_MISMATCH_WITHOUT_ROUTE_COUNT = 0
EXPECTED_ROUTE_AND_PASSAGE_MISMATCH_COUNT = 3
EXPECTED_ROUTE_MISMATCH_WITHOUT_PASSAGE_COUNT = 2
EXPECTED_MULTIPLE_AND_ROUTE_PASSAGE_OVERLAP_COUNT = 0
EXPECTED_SPECIAL_TRANSACTION_COUNT = 188

REASON_NONPARTICIPATING = "nonparticipating_present"
REASON_MULTIPLE_BUYERS = "multiple_buyers"
REASON_MULTIPLE_SELLERS = "multiple_sellers"

REASON_SELECTED = "selected"
REASON_FEASIBLE_NOT_SELECTED = "feasible_not_selected"
REASON_ECONOMICALLY_INFEASIBLE = "economically_infeasible"
REASON_UNRESOLVED = "unresolved"

SUMMARY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "right_of_entry_visit_key",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "selected_because_nonparticipating_present",
    "selected_because_multiple_buyers",
    "selected_because_multiple_sellers",
    "selection_reasons",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "nonparticipating_baseline_candidate_rank_all_equal",
    "economically_feasible",
    "candidate_infeasibility_reasons",
    "total_G",
    "total_R",
    "surplus",
    "total_official_payment",
    "total_official_compensation",
    "payment_balance_difference",
    "payment_balance_satisfied",
    "actual_evaluation_available",
    "trade_ex_post_evaluation_status",
    "route_mismatch_visit_count",
    "passage_mismatch_visit_count",
    "any_route_mismatch",
    "any_passage_mismatch",
    "same_inlink_multiple_buyer",
    "same_inlink_multiple_seller",
    "multiple_buyer",
    "multiple_seller",
    "multiple_buyer_and_seller",
)

PARTY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "role",
    "participates_in_order_exchange",
    "is_right_of_entry_holder",
    "inlink_name",
    "baseline_arrival_timestep",
    "baseline_arrival_tiebreaker",
    "vehicle_id",
    "actual_arrival_timestep",
    "baseline_minus_actual_arrival_timesteps",
    "formal_route_next_link_name",
    "predicted_route_next_link_name",
    "actual_route_next_link_name",
    "selected_because_nonparticipating_present",
    "selected_because_multiple_buyers",
    "selected_because_multiple_sellers",
    "selection_reasons",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "predicted_observation_status",
    "actual_observation_status",
    "baseline_local_rank",
    "post_trade_local_rank",
    "assigned_rank",
    "actual_node_passage_rank",
    "binding_sequence_auxiliary_rank",
    "baseline_minus_candidate_local_rank",
    "assigned_minus_actual_node_rank",
    "actual_rank_change",
    "true_vot_per_second",
    "declared_vot_per_second",
    "economically_feasible",
    "candidate_infeasibility_reasons",
    "individual_economic_condition_status",
    "individual_economic_condition_reason",
    "passes_positive_buyer_value_condition",
    "expected_time_saving_timesteps",
    "expected_waiting_increase_timesteps",
    "expected_delay_timesteps",
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "official_payment",
    "official_compensation",
    "reference_payment",
    "reference_compensation",
    "effective_payment_amount",
    "effective_compensation_amount",
    "monetary_transfer_participation_status",
    "payment_record_status",
    "compensation_record_status",
    "reference_payment_status",
    "reference_compensation_status",
    "realized_time_value",
    "realized_delay_loss",
    "realized_gain",
    "satisfaction_status",
    "satisfaction_reason",
    "trade_ex_post_evaluation_status",
    "actual_evaluation_available",
    "predicted_signed_time_difference_timesteps",
    "actual_signed_time_difference_timesteps",
    "predicted_external_effect_value",
    "actual_external_effect_value",
)

CANDIDATE_SUMMARY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "candidate_evaluation_index",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "right_of_entry_visit_key",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "local_virtual_calculation_status",
    "candidate_passage_resolved",
    "unresolved_reasons",
    "economically_feasible",
    "candidate_infeasibility_reasons",
    "selected",
    "selection_status",
    "selection_reason",
    "total_G",
    "total_R",
    "surplus",
    "multiple_buyer",
    "multiple_seller",
    "multiple_buyer_and_seller",
    "same_inlink_multiple_buyer",
    "same_inlink_multiple_seller",
)

CANDIDATE_PARTY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "candidate_evaluation_index",
    "selected",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "role",
    "inlink_name",
    "baseline_arrival_timestep",
    "baseline_arrival_tiebreaker",
    "vehicle_id",
    "is_right_of_entry_holder",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "baseline_local_rank",
    "candidate_local_rank",
    "binding_sequence_auxiliary_rank",
    "predicted_route_next_link_name",
    "true_vot_per_second",
    "declared_vot_per_second",
    "individual_economic_condition_status",
    "individual_economic_condition_reason",
    "passes_positive_buyer_value_condition",
    "expected_time_saving_timesteps",
    "expected_waiting_increase_timesteps",
    "expected_delay_timesteps",
    "gross_time_value_G_b",
    "required_compensation_R_s",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_run_tvt_mp_driver = None
        self.original_record_order_control_node_arrival = None
        self.established: list[dict] = []
        self.considered: list[dict] = []
        self.actual_node_arrivals: dict[tuple, int] = {}


GATE = _Gate()


def _decision_label(node_name: str, timestep: int) -> str:
    return f"T={timestep} {node_name}"


def _plain_visit_key(visit_key) -> tuple:
    if not isinstance(visit_key, tuple) or len(visit_key) != 2:
        raise RuntimeError(f"VisitKey is not a pair: {visit_key!r}.")
    vehicle_name, visit_id = visit_key
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is {vehicle_name!r}.")
    if type(visit_id) is not int:
        raise RuntimeError(f"VisitKey visit id is {visit_id!r}.")
    return (vehicle_name, visit_id)


def _visit_text(visit_key) -> str:
    vehicle_name, visit_id = _plain_visit_key(visit_key)
    return f"{vehicle_name}:{visit_id}"


def _join_visit_keys(visit_keys) -> str:
    texts = []
    for visit_key in visit_keys:
        texts.append(_visit_text(visit_key))
    return "|".join(texts)


def _candidate_identity(timestep: int, node_name: str, evaluation_index: int, buyers_sorted) -> str:
    return (
        f"T={timestep}|{node_name}|index={evaluation_index}|"
        f"{_join_visit_keys(buyers_sorted)}"
    )


def _require_python_int(value, label: str):
    if type(value) is not int:
        raise RuntimeError(f"{label} must be a Python int, not bool; got {value!r}.")
    return value


def _subtract_ints(left, right):
    if type(left) is not int or type(right) is not int:
        return None
    return left - right


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _enum_values_text(reasons) -> str:
    values = []
    for reason in reasons:
        values.append(reason.value)
    return "|".join(values)


RECORD_PRESENT = "present"
RECORD_ABSENT_NOT_APPLICABLE = "absent_not_applicable"
RECORD_UNEXPECTED_MISSING = "unexpected_missing"
RECORD_UNEXPECTED_PRESENT = "unexpected_present"
MONETARY_BUYER = "buyer"
MONETARY_SELLER = "seller"
MONETARY_EXCLUDED_NONPARTICIPATING = "excluded_nonparticipating"
MONETARY_UNEXPECTED = "unexpected_or_unresolved"


def _record_status(role_expects_record: bool, record_present: bool) -> str:
    if role_expects_record is True and record_present is True:
        return RECORD_PRESENT
    if role_expects_record is True and record_present is not True:
        return RECORD_UNEXPECTED_MISSING
    if role_expects_record is not True and record_present is True:
        return RECORD_UNEXPECTED_PRESENT
    return RECORD_ABSENT_NOT_APPLICABLE


def _monetary_transfer_fields(
    role_name: str,
    payment_amount,
    compensation_amount,
    payment_present: bool,
    compensation_present: bool,
) -> dict:
    if payment_present is True:
        official_payment = payment_amount
    else:
        official_payment = None
    if compensation_present is True:
        official_compensation = compensation_amount
    else:
        official_compensation = None
    payment_status = _record_status(role_name == "buyer", payment_present)
    compensation_status = _record_status(role_name == "seller", compensation_present)
    if payment_status == RECORD_PRESENT:
        effective_payment = official_payment
    elif payment_status == RECORD_ABSENT_NOT_APPLICABLE:
        effective_payment = 0
    else:
        effective_payment = None
    if compensation_status == RECORD_PRESENT:
        effective_compensation = official_compensation
    elif compensation_status == RECORD_ABSENT_NOT_APPLICABLE:
        effective_compensation = 0
    else:
        effective_compensation = None
    if role_name == "buyer":
        participation = MONETARY_BUYER
    elif role_name == "seller":
        participation = MONETARY_SELLER
    elif role_name == "nonparticipating":
        participation = MONETARY_EXCLUDED_NONPARTICIPATING
    else:
        participation = MONETARY_UNEXPECTED
    if (
        payment_status == RECORD_UNEXPECTED_MISSING
        or payment_status == RECORD_UNEXPECTED_PRESENT
        or compensation_status == RECORD_UNEXPECTED_MISSING
        or compensation_status == RECORD_UNEXPECTED_PRESENT
    ):
        participation = MONETARY_UNEXPECTED
    return {
        "official_payment": official_payment,
        "official_compensation": official_compensation,
        "effective_payment_amount": effective_payment,
        "effective_compensation_amount": effective_compensation,
        "monetary_transfer_participation_status": participation,
        "payment_record_status": payment_status,
        "compensation_record_status": compensation_status,
    }


def _reference_amount_status(role_name: str, side: str, value) -> str:
    if side == "payment":
        formally_excluded = role_name == "seller" or role_name == "nonparticipating"
    elif side == "compensation":
        formally_excluded = role_name == "buyer" or role_name == "nonparticipating"
    else:
        raise RuntimeError(f"Reference side is {side!r}.")
    if formally_excluded is True:
        if value is None:
            return RECORD_ABSENT_NOT_APPLICABLE
        return RECORD_UNEXPECTED_PRESENT
    if value is None:
        return RECORD_UNEXPECTED_MISSING
    return RECORD_PRESENT


def _count_flags(buyer_count: int, seller_count: int, nonparticipating_count: int) -> dict:
    because_nonparticipating = nonparticipating_count >= 1
    because_multiple_buyers = buyer_count >= 2
    because_multiple_sellers = seller_count >= 2
    reasons = []
    if because_nonparticipating is True:
        reasons.append(REASON_NONPARTICIPATING)
    if because_multiple_buyers is True:
        reasons.append(REASON_MULTIPLE_BUYERS)
    if because_multiple_sellers is True:
        reasons.append(REASON_MULTIPLE_SELLERS)
    return {
        "selected_because_nonparticipating_present": because_nonparticipating,
        "selected_because_multiple_buyers": because_multiple_buyers,
        "selected_because_multiple_sellers": because_multiple_sellers,
        "selection_reasons": "|".join(reasons),
        "multiple_buyer": because_multiple_buyers,
        "multiple_seller": because_multiple_sellers,
        "multiple_buyer_and_seller": because_multiple_buyers and because_multiple_sellers,
    }


def _same_inlink_multiple(parties, role_name: str) -> bool:
    counts = {}
    for party in parties:
        if party["role"] != role_name:
            continue
        inlink_name = party["inlink_name"]
        if inlink_name not in counts:
            counts[inlink_name] = 0
        counts[inlink_name] = counts[inlink_name] + 1
    for inlink_name in counts:
        if counts[inlink_name] >= 2:
            return True
    return False


def _require_one(results, node_name: str, timestep: int, stage_name: str):
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
            f"{match_count} results for the node."
        )
    return matched


def _saved_driver_columns(atomic):
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
            "Saved fork_result is not OrderControlBaselineForkResult: "
            f"{type(fork_result).__name__}."
        )
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError(
            "Saved fork collector is not OrderControlBaselineCollector: "
            f"{type(collector).__name__}."
        )
    return {
        "payment_nodes": payment_set.node_payment_and_compensation_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
    }


def _baseline_local_ranks(candidate_visits, node_name: str, timestep: int):
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
                f"{_visit_text(visit_key)}."
            )
        ordered_visit_keys.append(visit_key)
        ranks[visit_key] = position
    return tuple(ordered_visit_keys), ranks


def _post_trade_local_ranks(trade_result, ordered_visit_keys, node_name: str, timestep: int):
    if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade rank result is "
            f"{type(trade_result).__name__}."
        )
    ranks = {}
    for visit_key in ordered_visit_keys:
        try:
            rank_value = trade_result.assigned_rank(visit_key)
        except ValueError as error:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: general trade rank "
                f"result has no assigned_rank for {_visit_text(visit_key)}."
            ) from error
        ranks[visit_key] = _require_python_int(
            rank_value,
            f"{_decision_label(node_name, timestep)} candidate local rank "
            f"for {_visit_text(visit_key)}",
        )
    return ranks


def _matching_trade_result(trade_rank_node, buyers_sorted, node_name: str, timestep: int):
    if not isinstance(trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: node trade rank result is "
            f"{type(trade_rank_node).__name__}."
        )
    found = None
    for trade_result in trade_rank_node.candidate_trade_rank_results:
        candidate_buyers = tuple(
            _plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted
        )
        if candidate_buyers != buyers_sorted:
            continue
        if found is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: two general trade rank "
                "results share the same buyers."
            )
        found = trade_result
    if found is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: no general trade rank result "
            "matches the candidate buyers."
        )
    return found


def _role_name(role, node_name: str, timestep: int, visit_key) -> str:
    if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return "buyer"
    if role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return "seller"
    if role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return "nonparticipating"
    raise RuntimeError(
        f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
        f"has trade role {role!r}."
    )


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


def _sum_payments(payment_node, node_name: str, timestep: int) -> float:
    if not isinstance(payment_node, OrderControlTvtNodeMpPaymentAndCompensationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment result is "
            f"{type(payment_node).__name__}."
        )
    total_payment = 0.0
    for record in payment_node.buyer_payment_records:
        if not isinstance(record, OrderControlTvtMpBuyerPaymentRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: buyer payment record is "
                f"{type(record).__name__}."
            )
        amount = record.payment_P_b
        if type(amount) not in (int, float) or type(amount) is bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: payment_P_b is {amount!r}."
            )
        total_payment = total_payment + amount
    return total_payment


def _sum_compensations(payment_node, node_name: str, timestep: int) -> float:
    total_compensation = 0.0
    for record in payment_node.seller_compensation_records:
        if not isinstance(record, OrderControlTvtMpSellerCompensationRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: compensation record is "
                f"{type(record).__name__}."
            )
        amount = record.compensation_amount
        if type(amount) not in (int, float) or type(amount) is bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: compensation_amount is {amount!r}."
            )
        total_compensation = total_compensation + amount
    return total_compensation


def _payment_balance_satisfied(total_official_payment, total_official_compensation) -> bool:
    if type(total_official_payment) is bool or type(total_official_payment) not in (int, float):
        return False
    if type(total_official_compensation) is bool or type(total_official_compensation) not in (int, float):
        return False
    if math.isfinite(total_official_payment) is not True:
        return False
    if math.isfinite(total_official_compensation) is not True:
        return False
    return math.isclose(
        total_official_payment,
        total_official_compensation,
        rel_tol=PAYMENT_BALANCE_REL_TOL,
        abs_tol=PAYMENT_BALANCE_ABS_TOL,
    )


def _require_distinct_roles(buyers_sorted, sellers_sorted, nonparticipating_sorted, node_name, timestep):
    seen = {}
    columns = (
        ("buyer", buyers_sorted),
        ("seller", sellers_sorted),
        ("nonparticipating", nonparticipating_sorted),
    )
    for role_name, visit_keys in columns:
        for visit_key in visit_keys:
            if visit_key in seen:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                    f"is both {seen[visit_key]} and {role_name}."
                )
            seen[visit_key] = role_name


def _traffic_by_visit_key(local_result, node_name: str, timestep: int) -> dict:
    traffic_by_key = {}
    for traffic_record in local_result.traffic_observation_records:
        if not isinstance(traffic_record, OrderControlTvtMpCandidateTrafficObservationRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: traffic observation is "
                f"{type(traffic_record).__name__}."
            )
        visit_key = _plain_visit_key(traffic_record.visit_key)
        if visit_key in traffic_by_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: traffic observation repeats "
                f"{_visit_text(visit_key)}."
            )
        traffic_by_key[visit_key] = traffic_record
    return traffic_by_key


def _require_non_negative_int(value, label: str) -> int:
    if type(value) is not int:
        raise RuntimeError(f"{label} must be a Python int, not bool; got {value!r}.")
    if value < 0:
        raise RuntimeError(f"{label} must be >= 0; got {value!r}.")
    return value


def _require_numeric_not_bool(value, label: str):
    if type(value) is bool:
        raise RuntimeError(f"{label} must not be bool; got {value!r}.")
    if type(value) not in (int, float):
        raise RuntimeError(f"{label} must be a number; got {value!r}.")
    if type(value) is float and math.isfinite(value) is not True:
        raise RuntimeError(f"{label} must be finite; got {value!r}.")
    return value


def _baseline_fields_from_collector(
    collector,
    node_name,
    timestep,
    visit_key,
    traffic_record=None,
):
    snapshot = collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
    if snapshot is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: collector has no baseline "
            f"snapshot for {_visit_text(visit_key)}."
        )
    if snapshot["node_name"] != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: baseline snapshot for "
            f"{_visit_text(visit_key)} belongs to {snapshot['node_name']!r}."
        )
    vehicle_id = _require_non_negative_int(
        snapshot["vehicle_id"],
        f"{_decision_label(node_name, timestep)} collector vehicle_id for "
        f"{_visit_text(visit_key)}",
    )
    if traffic_record is not None:
        if traffic_record.vehicle_id != vehicle_id:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: traffic observation "
                f"vehicle_id {traffic_record.vehicle_id!r} differs from collector "
                f"snapshot {vehicle_id!r} for {_visit_text(visit_key)}."
            )
    baseline_arrival = snapshot["baseline_arrival_timestep"]
    arrival_tiebreaker = snapshot["arrival_tiebreaker"]
    if baseline_arrival is None:
        return {
            "baseline_arrival_timestep": None,
            "baseline_arrival_tiebreaker": None,
            "vehicle_id": vehicle_id,
        }
    baseline_arrival = _require_non_negative_int(
        baseline_arrival,
        f"{_decision_label(node_name, timestep)} baseline_arrival_timestep for "
        f"{_visit_text(visit_key)}",
    )
    if arrival_tiebreaker is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: collector snapshot for "
            f"{_visit_text(visit_key)} has baseline_arrival_timestep but no "
            "arrival_tiebreaker."
        )
    arrival_tiebreaker = _require_numeric_not_bool(
        arrival_tiebreaker,
        f"{_decision_label(node_name, timestep)} arrival_tiebreaker for "
        f"{_visit_text(visit_key)}",
    )
    return {
        "baseline_arrival_timestep": baseline_arrival,
        "baseline_arrival_tiebreaker": arrival_tiebreaker,
        "vehicle_id": vehicle_id,
    }


def _optional_passage(value, node_name, timestep, visit_key, field_name):
    if value is None:
        return None
    if type(value) is not int:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {field_name} for "
            f"{_visit_text(visit_key)} is {value!r}."
        )
    return value


def _buyer_seller_fields(role_name, buyer_record, seller_record, node_name, timestep, visit_key):
    expected_time_saving = None
    expected_waiting_increase = None
    gross_time_value = None
    required_compensation = None
    passes_positive = None
    individual_status = None
    declared_vot = None
    if role_name == "buyer":
        if buyer_record is None:
            return (
                expected_time_saving,
                expected_waiting_increase,
                gross_time_value,
                required_compensation,
                passes_positive,
                individual_status,
                declared_vot,
            )
        if not isinstance(buyer_record, OrderControlTvtMpBuyerEconomicRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: buyer "
                f"{_visit_text(visit_key)} economic record is {type(buyer_record).__name__}."
            )
        expected_time_saving = buyer_record.expected_time_saving_timesteps
        gross_time_value = buyer_record.gross_time_value_G_b
        passes_positive = buyer_record.passes_positive_buyer_value_condition
        declared_vot = buyer_record.declared_vot_per_second
        if passes_positive is True:
            individual_status = "passes_positive_buyer_value_condition"
        elif passes_positive is False:
            individual_status = "fails_positive_buyer_value_condition"
        else:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: "
                f"passes_positive_buyer_value_condition is {passes_positive!r}."
            )
    elif role_name == "seller":
        if seller_record is None:
            return (
                expected_time_saving,
                expected_waiting_increase,
                gross_time_value,
                required_compensation,
                passes_positive,
                individual_status,
                declared_vot,
            )
        if not isinstance(seller_record, OrderControlTvtMpSellerEconomicRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: seller "
                f"{_visit_text(visit_key)} economic record is {type(seller_record).__name__}."
            )
        expected_waiting_increase = seller_record.expected_waiting_increase_timesteps
        required_compensation = seller_record.required_compensation_R_s
        declared_vot = seller_record.declared_vot_per_second
    elif role_name == "nonparticipating":
        if buyer_record is not None or seller_record is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: nonparticipating "
                f"{_visit_text(visit_key)} has a buyer or seller economic record."
            )
    return (
        expected_time_saving,
        expected_waiting_increase,
        gross_time_value,
        required_compensation,
        passes_positive,
        individual_status,
        declared_vot,
    )


def _selection_fact(local_result, economic_result, selected_economic, selection_node, node_name, timestep):
    if not isinstance(selection_node.selection_status, OrderControlTvtMpCandidateSelectionStatus):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selection_status is "
            f"{selection_node.selection_status!r}."
        )
    status_text = selection_node.selection_status.value
    if local_result.resolved is False:
        if economic_result is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: unresolved candidate has "
                "an economic result."
            )
        return False, status_text, REASON_UNRESOLVED, None, ""
    if economic_result is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: resolved candidate has no "
            "economic result."
        )
    feasible = economic_result.economically_feasible
    if type(feasible) is not bool:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: economically_feasible is {feasible!r}."
        )
    infeasibility_text = _enum_values_text(economic_result.infeasibility_reasons)
    if feasible is True and infeasibility_text != "":
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: feasible candidate has "
            "infeasibility reasons."
        )
    if feasible is not True and infeasibility_text == "":
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: infeasible candidate has "
            "no infeasibility reason."
        )
    if economic_result is selected_economic:
        if feasible is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected candidate is "
                "not economically feasible."
            )
        return True, status_text, REASON_SELECTED, True, infeasibility_text
    if feasible is True:
        if selected_economic is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: a feasible candidate is "
                "saved while the selection result has no selected candidate."
            )
        return False, status_text, REASON_FEASIBLE_NOT_SELECTED, True, infeasibility_text
    return False, status_text, REASON_ECONOMICALLY_INFEASIBLE, False, infeasibility_text


def _capture_one_candidate(
    *,
    world,
    columns,
    local_result,
    evaluation_index: int,
    node_name: str,
    timestep: int,
):
    if not isinstance(local_result, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: local result is "
            f"{type(local_result).__name__}."
        )
    if local_result.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: local result node is "
            f"{local_result.node_name!r}."
        )
    if local_result.baseline_timestep_T != timestep:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: local baseline_timestep_T "
            f"is {local_result.baseline_timestep_T!r}."
        )
    if world.T != timestep:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: World.T is {world.T!r}."
        )
    buyers_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    trade_rank_node = _require_one(
        columns["trade_rank_nodes"], node_name, timestep, "general_trade_rank"
    )
    trade_result = _matching_trade_result(
        trade_rank_node, buyers_sorted, node_name, timestep
    )
    sellers_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.sellers_sorted
    )
    nonparticipating_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in trade_result.nonparticipating_visits_sorted
    )
    _require_distinct_roles(
        buyers_sorted,
        sellers_sorted,
        nonparticipating_sorted,
        node_name,
        timestep,
    )
    trade_scope = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.trade_scope
    )
    expected_scope = buyers_sorted + sellers_sorted + nonparticipating_sorted
    if len(trade_scope) != len(expected_scope) or set(trade_scope) != set(expected_scope):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade_scope is not the "
            "buyer, seller, and nonparticipating Visit set."
        )
    candidate_visit_node = _require_one(
        columns["candidate_visit_nodes"], node_name, timestep, "candidate_visit_set"
    )
    if not isinstance(candidate_visit_node, OrderControlTvtNodeCandidateVisitSetResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: candidate visit node is "
            f"{type(candidate_visit_node).__name__}."
        )
    ordered_visit_keys, baseline_ranks = _baseline_local_ranks(
        candidate_visit_node.candidate_visits, node_name, timestep
    )
    post_trade_ranks = _post_trade_local_ranks(
        trade_result, ordered_visit_keys, node_name, timestep
    )
    candidate_order = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.trade_order
    )
    if set(candidate_order) != set(ordered_visit_keys):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade_order VisitKeys differ "
            "from saved candidate_visits."
        )
    right_of_entry_node = _require_one(
        columns["right_of_entry_nodes"], node_name, timestep, "right_of_entry"
    )
    if not isinstance(right_of_entry_node, OrderControlTvtNodeRightOfEntrySelectionResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry node is "
            f"{type(right_of_entry_node).__name__}."
        )
    if right_of_entry_node.right_of_entry_visit_key is None:
        right_of_entry_key = None
    else:
        right_of_entry_key = _plain_visit_key(right_of_entry_node.right_of_entry_visit_key)
    economic_node = _require_one(
        columns["economic_nodes"], node_name, timestep, "economic_evaluation"
    )
    economic_result = None
    for candidate_economic in economic_node.candidate_economic_evaluation_results:
        if candidate_economic.candidate_local_virtual_calculation_result is local_result:
            if economic_result is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: two economic results "
                    "point at the same local result."
                )
            economic_result = candidate_economic
    selection_node = _require_one(
        columns["selection_nodes"], node_name, timestep, "candidate_selection"
    )
    selected_economic = selection_node.selected_candidate_economic_result
    selected, selection_status, selection_reason, feasible, infeasibility_text = (
        _selection_fact(
            local_result,
            economic_result,
            selected_economic,
            selection_node,
            node_name,
            timestep,
        )
    )
    if economic_result is None:
        total_g = None
        total_r = None
        surplus = None
        buyer_economics = {}
        seller_economics = {}
    else:
        total_g = economic_result.total_buyer_value_G
        total_r = economic_result.total_required_compensation_R
        surplus = economic_result.surplus
        buyer_economics = _records_by_visit_key(
            economic_result.buyer_economic_records,
            node_name,
            timestep,
            "buyer_economic_records",
        )
        seller_economics = _records_by_visit_key(
            economic_result.seller_economic_records,
            node_name,
            timestep,
            "seller_economic_records",
        )
    traffic_by_key = _traffic_by_visit_key(local_result, node_name, timestep)
    collector = columns["collector"]
    identity = _candidate_identity(timestep, node_name, evaluation_index, buyers_sorted)
    flags = _count_flags(
        len(buyers_sorted), len(sellers_sorted), len(nonparticipating_sorted)
    )
    parties = []
    for visit_key in trade_scope:
        traffic_record = traffic_by_key.get(visit_key)
        if traffic_record is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope "
                f"{_visit_text(visit_key)} has no traffic observation."
            )
        role_name = _role_name(traffic_record.trade_role, node_name, timestep, visit_key)
        if visit_key not in baseline_ranks or visit_key not in post_trade_ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "is missing a saved local rank."
            )
        baseline_fields = _baseline_fields_from_collector(
            collector,
            node_name,
            timestep,
            visit_key,
            traffic_record=traffic_record,
        )
        baseline_passage = _optional_passage(
            traffic_record.baseline_passage_timestep,
            node_name,
            timestep,
            visit_key,
            "baseline_passage_timestep",
        )
        candidate_passage = _optional_passage(
            traffic_record.candidate_passage_timestep,
            node_name,
            timestep,
            visit_key,
            "candidate_passage_timestep",
        )
        buyer_record = buyer_economics.get(visit_key)
        seller_record = seller_economics.get(visit_key)
        (
            expected_time_saving,
            expected_waiting_increase,
            gross_time_value,
            required_compensation,
            passes_positive,
            individual_status,
            declared_vot,
        ) = _buyer_seller_fields(
            role_name,
            buyer_record,
            seller_record,
            node_name,
            timestep,
            visit_key,
        )
        if selected is True and role_name == "buyer" and buyer_record is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected buyer "
                f"{_visit_text(visit_key)} has no buyer economic record."
            )
        if selected is True and role_name == "seller" and seller_record is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected seller "
                f"{_visit_text(visit_key)} has no seller economic record."
            )
        parties.append(
            {
                "visit_key": visit_key,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "role": role_name,
                "inlink_name": traffic_record.inlink_name,
                "is_right_of_entry_holder": visit_key == right_of_entry_key,
                "baseline_arrival_timestep": baseline_fields["baseline_arrival_timestep"],
                "baseline_arrival_tiebreaker": baseline_fields["baseline_arrival_tiebreaker"],
                "vehicle_id": baseline_fields["vehicle_id"],
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_passage,
                "baseline_local_rank": baseline_ranks[visit_key],
                "candidate_local_rank": post_trade_ranks[visit_key],
                "binding_sequence_auxiliary_rank": traffic_record.binding_rank,
                "predicted_route_next_link_name": traffic_record.route_next_link_name,
                "true_vot_per_second": traffic_record.true_vot_per_second,
                "declared_vot_per_second": declared_vot,
                "individual_economic_condition_status": individual_status,
                "individual_economic_condition_reason": None,
                "passes_positive_buyer_value_condition": passes_positive,
                "expected_time_saving_timesteps": expected_time_saving,
                "expected_waiting_increase_timesteps": expected_waiting_increase,
                "expected_delay_timesteps": expected_waiting_increase,
                "gross_time_value_G_b": gross_time_value,
                "required_compensation_R_s": required_compensation,
                "post_trade_local_rank": post_trade_ranks[visit_key],
            }
        )
    unresolved_text = ""
    if local_result.resolved is False:
        unresolved_text = _enum_values_text(local_result.unresolved_reasons)
    candidate = {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": timestep,
        "node_name": node_name,
        "candidate_identity": identity,
        "candidate_evaluation_index": evaluation_index,
        "buyers_sorted": buyers_sorted,
        "sellers_sorted": sellers_sorted,
        "nonparticipating_visits_sorted": nonparticipating_sorted,
        "buyer_count": len(buyers_sorted),
        "seller_count": len(sellers_sorted),
        "nonparticipating_count": len(nonparticipating_sorted),
        "trade_scope_count": len(trade_scope),
        "right_of_entry_visit_key": right_of_entry_key,
        "baseline_order_visit_keys": ordered_visit_keys,
        "candidate_order_visit_keys": candidate_order,
        "local_virtual_calculation_status": local_result.stop_reason.value,
        "candidate_passage_resolved": local_result.resolved,
        "unresolved_reasons": unresolved_text,
        "economically_feasible": feasible,
        "candidate_infeasibility_reasons": infeasibility_text,
        "selected": selected,
        "selection_status": selection_status,
        "selection_reason": selection_reason,
        "total_G": total_g,
        "total_R": total_r,
        "surplus": surplus,
        "multiple_buyer": flags["multiple_buyer"],
        "multiple_seller": flags["multiple_seller"],
        "multiple_buyer_and_seller": flags["multiple_buyer_and_seller"],
        "same_inlink_multiple_buyer": _same_inlink_multiple(parties, "buyer"),
        "same_inlink_multiple_seller": _same_inlink_multiple(parties, "seller"),
        "parties": parties,
        "local_result": local_result,
        "economic_result": economic_result,
        "flags": flags,
        "traffic_by_key": traffic_by_key,
        "baseline_ranks": baseline_ranks,
        "post_trade_ranks": post_trade_ranks,
    }
    return candidate


def _build_established_from_candidate(world, columns, candidate, payment_node):
    node_name = candidate["node_name"]
    timestep = candidate["tvt_decision_timestep"]
    if candidate["selected"] is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: established builder received "
            "a candidate that was not selected."
        )
    economic_result = candidate["economic_result"]
    if not isinstance(economic_result, OrderControlTvtMpCandidateEconomicEvaluationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result is "
            f"{type(economic_result).__name__}."
        )
    payments = _records_by_visit_key(
        payment_node.buyer_payment_records, node_name, timestep, "buyer_payment_records"
    )
    compensations = _records_by_visit_key(
        payment_node.seller_compensation_records,
        node_name,
        timestep,
        "seller_compensation_records",
    )
    flags = candidate["flags"]
    parties = []
    for source_party in candidate["parties"]:
        visit_key = source_party["visit_key"]
        role_name = source_party["role"]
        traffic_record = candidate["traffic_by_key"][visit_key]
        vehicle = world.VEHICLES[visit_key[0]]
        participates = vehicle.participates_in_order_exchange
        if type(participates) is not bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: participates_in_order_exchange "
                f"for {_visit_text(visit_key)} is {participates!r}."
            )
        if source_party["baseline_arrival_timestep"] is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: established "
                f"{_visit_text(visit_key)} has no baseline_arrival_timestep."
            )
        if source_party["baseline_arrival_tiebreaker"] is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: established "
                f"{_visit_text(visit_key)} has no baseline_arrival_tiebreaker."
            )
        if source_party["vehicle_id"] is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: established "
                f"{_visit_text(visit_key)} has no vehicle_id."
            )
        if type(source_party["baseline_passage_timestep"]) is not int:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: established "
                f"{_visit_text(visit_key)} has no baseline passage."
            )
        if type(source_party["candidate_passage_timestep"]) is not int:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: established "
                f"{_visit_text(visit_key)} has no candidate passage."
            )
        payment_record = payments.get(visit_key)
        compensation_record = compensations.get(visit_key)
        if payment_record is None:
            payment_amount = None
            payment_present = False
        else:
            payment_amount = payment_record.payment_P_b
            payment_present = True
        if compensation_record is None:
            compensation_amount = None
            compensation_present = False
        else:
            compensation_amount = compensation_record.compensation_amount
            compensation_present = True
        money = _monetary_transfer_fields(
            role_name,
            payment_amount,
            compensation_amount,
            payment_present,
            compensation_present,
        )
        predicted_signed = _subtract_ints(
            source_party["baseline_passage_timestep"],
            source_party["candidate_passage_timestep"],
        )
        if role_name == "nonparticipating":
            stored_predicted = traffic_record.predicted_time_difference_timesteps
            if stored_predicted != predicted_signed:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    "predicted_time_difference_timesteps for "
                    f"{_visit_text(visit_key)} is {stored_predicted!r}."
                )
            predicted_external = traffic_record.predicted_signed_time_value_change
            predicted_signed_for_row = predicted_signed
        else:
            predicted_external = None
            predicted_signed_for_row = None
        predicted_status = traffic_record.passage_observation_status
        if predicted_status is None:
            predicted_status_text = None
        else:
            predicted_status_text = predicted_status.value
        parties.append(
            {
                "visit_key": visit_key,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "role": role_name,
                "participates_in_order_exchange": participates,
                "is_right_of_entry_holder": source_party["is_right_of_entry_holder"],
                "inlink_name": source_party["inlink_name"],
                "predicted_route_next_link_name": source_party["predicted_route_next_link_name"],
                "formal_route_next_link_name": None,
                "actual_route_next_link_name": None,
                "baseline_arrival_timestep": source_party["baseline_arrival_timestep"],
                "baseline_arrival_tiebreaker": source_party["baseline_arrival_tiebreaker"],
                "vehicle_id": source_party["vehicle_id"],
                "actual_arrival_timestep": None,
                "baseline_passage_timestep": source_party["baseline_passage_timestep"],
                "candidate_passage_timestep": source_party["candidate_passage_timestep"],
                "actual_passage_timestep": None,
                "predicted_observation_status": predicted_status_text,
                "actual_observation_status": None,
                "baseline_local_rank": source_party["baseline_local_rank"],
                "post_trade_local_rank": source_party["post_trade_local_rank"],
                "assigned_rank": None,
                "actual_node_passage_rank": None,
                "binding_sequence_auxiliary_rank": source_party[
                    "binding_sequence_auxiliary_rank"
                ],
                "true_vot_per_second": source_party["true_vot_per_second"],
                "declared_vot_per_second": source_party["declared_vot_per_second"],
                "passes_positive_buyer_value_condition": source_party[
                    "passes_positive_buyer_value_condition"
                ],
                "individual_economic_condition_status": source_party[
                    "individual_economic_condition_status"
                ],
                "individual_economic_condition_reason": None,
                "expected_time_saving_timesteps": source_party["expected_time_saving_timesteps"],
                "expected_waiting_increase_timesteps": source_party[
                    "expected_waiting_increase_timesteps"
                ],
                "gross_time_value_G_b": source_party["gross_time_value_G_b"],
                "required_compensation_R_s": source_party["required_compensation_R_s"],
                "official_payment": money["official_payment"],
                "official_compensation": money["official_compensation"],
                "effective_payment_amount": money["effective_payment_amount"],
                "effective_compensation_amount": money["effective_compensation_amount"],
                "monetary_transfer_participation_status": money[
                    "monetary_transfer_participation_status"
                ],
                "payment_record_status": money["payment_record_status"],
                "compensation_record_status": money["compensation_record_status"],
                "reference_payment": None,
                "reference_compensation": None,
                "reference_payment_status": None,
                "reference_compensation_status": None,
                "realized_time_value": None,
                "realized_delay_loss": None,
                "realized_gain": None,
                "satisfaction_status": None,
                "satisfaction_reason": None,
                "predicted_signed_time_difference_timesteps": predicted_signed_for_row,
                "actual_signed_time_difference_timesteps": None,
                "predicted_external_effect_value": predicted_external,
                "actual_external_effect_value": None,
                "actual_rank_change": None,
            }
        )
    total_official_payment = _sum_payments(payment_node, node_name, timestep)
    total_official_compensation = _sum_compensations(payment_node, node_name, timestep)
    rank_equal = True
    for party in parties:
        if party["role"] != "nonparticipating":
            continue
        if party["baseline_local_rank"] != party["post_trade_local_rank"]:
            rank_equal = False
    return {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": timestep,
        "node_name": node_name,
        "candidate_identity": candidate["candidate_identity"],
        "candidate_evaluation_index": candidate["candidate_evaluation_index"],
        "buyers_sorted": candidate["buyers_sorted"],
        "sellers_sorted": candidate["sellers_sorted"],
        "nonparticipating_visits_sorted": candidate["nonparticipating_visits_sorted"],
        "right_of_entry_visit_key": candidate["right_of_entry_visit_key"],
        "buyer_count": candidate["buyer_count"],
        "seller_count": candidate["seller_count"],
        "nonparticipating_count": candidate["nonparticipating_count"],
        "trade_scope_count": candidate["trade_scope_count"],
        "selected_because_nonparticipating_present": flags[
            "selected_because_nonparticipating_present"
        ],
        "selected_because_multiple_buyers": flags["selected_because_multiple_buyers"],
        "selected_because_multiple_sellers": flags["selected_because_multiple_sellers"],
        "selection_reasons": flags["selection_reasons"],
        "baseline_order_visit_keys": candidate["baseline_order_visit_keys"],
        "candidate_order_visit_keys": candidate["candidate_order_visit_keys"],
        "nonparticipating_baseline_candidate_rank_all_equal": rank_equal,
        "economically_feasible": economic_result.economically_feasible,
        "candidate_infeasibility_reasons": _enum_values_text(
            economic_result.infeasibility_reasons
        ),
        "total_G": economic_result.total_buyer_value_G,
        "total_R": economic_result.total_required_compensation_R,
        "surplus": economic_result.surplus,
        "total_official_payment": total_official_payment,
        "total_official_compensation": total_official_compensation,
        "payment_balance_difference": total_official_payment - total_official_compensation,
        "payment_balance_satisfied": _payment_balance_satisfied(
            total_official_payment,
            total_official_compensation,
        ),
        "actual_evaluation_available": None,
        "trade_ex_post_evaluation_status": None,
        "parties": parties,
    }


def _capture_decision(world, result) -> None:
    timestep = world.T
    if type(timestep) is not int:
        raise RuntimeError(f"Driver World.T is not an int: {timestep!r}.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={timestep}: driver result is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        return
    columns = _saved_driver_columns(atomic)
    seen_nodes = []
    for local_node in columns["local_nodes"]:
        if not isinstance(local_node, OrderControlTvtNodeMpLocalVirtualCalculationResult):
            raise RuntimeError(
                f"T={timestep}: local node result is {type(local_node).__name__}."
            )
        node_name = local_node.node_name
        if node_name in seen_nodes:
            raise RuntimeError(f"T={timestep}: local results repeat {node_name}.")
        seen_nodes.append(node_name)
        payment_node = _require_one(
            columns["payment_nodes"], node_name, timestep, "payment_and_compensation"
        )
        selection_node = _require_one(
            columns["selection_nodes"], node_name, timestep, "candidate_selection"
        )
        selected_seen = False
        evaluation_index = 0
        for local_result in local_node.candidate_local_virtual_calculation_results:
            evaluation_index = evaluation_index + 1
            candidate = _capture_one_candidate(
                world=world,
                columns=columns,
                local_result=local_result,
                evaluation_index=evaluation_index,
                node_name=node_name,
                timestep=timestep,
            )
            GATE.considered.append(candidate)
            if candidate["selected"] is True:
                if selected_seen is True:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: two candidates "
                        "are marked selected."
                    )
                selected_seen = True
                if payment_node.selected_candidate_economic_result is not candidate["economic_result"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: payment and "
                        "selection do not share the selected economic result."
                    )
                GATE.established.append(
                    _build_established_from_candidate(
                        world, columns, candidate, payment_node
                    )
                )
        selected_economic = selection_node.selected_candidate_economic_result
        if selected_economic is None and selected_seen is True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: a candidate was selected "
                "while the selection result is empty."
            )
        if selected_economic is not None and selected_seen is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected economic result "
                "is not one of the saved local candidates."
            )


def wrapped_run_tvt_mp_driver(world):
    result = GATE.original_run_tvt_mp_driver(world)
    if world is not GATE.real_world:
        return result
    _capture_decision(world, result)
    return result


def _remember_real_world_node_arrival(vehicle, node) -> None:
    if vehicle.W is not GATE.real_world:
        return
    collector = getattr(vehicle.W, "_order_control_baseline_collector", None)
    if collector is not None:
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
            f"Node {node.name}: vehicle {vehicle.name} arrival visit_id is {visit_id!r}."
        )
    timestep = vehicle.W.T
    if type(timestep) is not int:
        raise RuntimeError(f"Node {node.name}: arrival World.T is {timestep!r}.")
    key = (node.name, vehicle.name, visit_id)
    if key in GATE.actual_node_arrivals:
        return
    GATE.actual_node_arrivals[key] = timestep


def wrapped_record_order_control_node_arrival(vehicle, node):
    result = GATE.original_record_order_control_node_arrival(vehicle, node)
    _remember_real_world_node_arrival(vehicle, node)
    return result


def install_observation_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Observation hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_run_tvt_mp_driver = driver_module.run_tvt_mp_driver
    GATE.original_record_order_control_node_arrival = (
        uxsim_module.Vehicle.record_order_control_node_arrival
    )
    GATE.installed = True
    driver_module.run_tvt_mp_driver = wrapped_run_tvt_mp_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = (
        wrapped_record_order_control_node_arrival
    )


def restore_observation_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_run_tvt_mp_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = (
        GATE.original_record_order_control_node_arrival
    )
    GATE.original_run_tvt_mp_driver = None
    GATE.original_record_order_control_node_arrival = None
    GATE.real_world = None
    GATE.installed = False


def _history_by_node(world) -> dict:
    registry = getattr(world, "order_control_tvt_mp_actual_node_passage_history_registry", None)
    if not isinstance(registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError(
            "Actual passage history registry is "
            f"{type(registry).__name__}."
        )
    by_node = {}
    for node_name, records in registry.records_by_node_name.items():
        by_visit = {}
        for record in records:
            if not isinstance(record, OrderControlTvtMpActualNodePassageRecord):
                raise RuntimeError(
                    f"Node {node_name}: actual passage record is {type(record).__name__}."
                )
            visit_key = _plain_visit_key(record.visit_key)
            if visit_key in by_visit:
                raise RuntimeError(
                    f"Node {node_name}: actual passage history repeats {_visit_text(visit_key)}."
                )
            by_visit[visit_key] = record
        by_node[node_name] = by_visit
    return by_node


def _rank_state(world, node_name: str) -> OrderControlTvtNodeRankState:
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        raise RuntimeError("Rank states are not a dict.")
    rank_state = states.get(node_name)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(f"Node {node_name}: rank state is {type(rank_state).__name__}.")
    return rank_state


def _research_indexes(bundle):
    transactions = {}
    visits = {}
    for row in bundle.transactions:
        buyers = tuple(_plain_visit_key(visit_key) for visit_key in row.buyers_sorted)
        key = (row.tvt_decision_timestep, row.node_name, buyers)
        if key in transactions:
            raise RuntimeError(f"Research output repeats transaction {key!r}.")
        transactions[key] = row
    for row in bundle.visits:
        buyers = tuple(_plain_visit_key(visit_key) for visit_key in row.buyers_sorted)
        visit_key = (row.vehicle_name, row.visit_id)
        key = (row.tvt_decision_timestep, row.node_name, buyers, visit_key)
        if key in visits:
            raise RuntimeError(f"Research output repeats visit {key!r}.")
        visits[key] = row
    return transactions, visits


def _attach_actual_and_research(world, bundle) -> None:
    history = _history_by_node(world)
    research_transactions, research_visits = _research_indexes(bundle)
    for transaction in GATE.established:
        timestep = transaction["tvt_decision_timestep"]
        node_name = transaction["node_name"]
        buyers = transaction["buyers_sorted"]
        research_transaction = research_transactions.get((timestep, node_name, buyers))
        if research_transaction is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: research output has no "
                "transaction for the selected buyers."
            )
        status = research_transaction.trade_ex_post_evaluation_status
        transaction["trade_ex_post_evaluation_status"] = status
        transaction["actual_evaluation_available"] = status != "evaluation_unavailable"
        if research_transaction.buyer_official_payment_total != transaction["total_official_payment"]:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: research payment total does "
                "not match summed payment_P_b."
            )
        if (
            research_transaction.seller_official_compensation_total
            != transaction["total_official_compensation"]
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: research compensation total "
                "does not match summed compensation_amount."
            )
        rank_state = _rank_state(world, node_name)
        node_history = history.get(node_name, {})
        for party in transaction["parties"]:
            visit_key = party["visit_key"]
            arrival_key = (node_name, visit_key[0], visit_key[1])
            if arrival_key not in GATE.actual_node_arrivals:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: real World has no "
                    f"actual arrival for {_visit_text(visit_key)}."
                )
            party["actual_arrival_timestep"] = GATE.actual_node_arrivals[arrival_key]
            assigned_rank = rank_state.assigned_rank(visit_key)
            if type(assigned_rank) is not int:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: assigned_rank for "
                    f"{_visit_text(visit_key)} is {assigned_rank!r}."
                )
            party["assigned_rank"] = assigned_rank
            formal_route = rank_state.formal_route_next_link_name(visit_key)
            party["formal_route_next_link_name"] = formal_route
            passage_record = node_history.get(visit_key)
            if passage_record is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: actual passage history "
                    f"has no record for {_visit_text(visit_key)}."
                )
            party["actual_passage_timestep"] = passage_record.actual_passage_timestep
            party["actual_node_passage_rank"] = passage_record.actual_node_passage_rank
            party["actual_route_next_link_name"] = passage_record.actual_route_next_link_name
            research_visit = research_visits.get((timestep, node_name, buyers, visit_key))
            if research_visit is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research output has no "
                    f"visit {_visit_text(visit_key)}."
                )
            if research_visit.role != party["role"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research role for "
                    f"{_visit_text(visit_key)} is {research_visit.role!r}."
                )
            if research_visit.baseline_passage_timestep != party["baseline_passage_timestep"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research baseline passage "
                    f"for {_visit_text(visit_key)} differs."
                )
            if research_visit.candidate_passage_timestep != party["candidate_passage_timestep"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research candidate passage "
                    f"for {_visit_text(visit_key)} differs."
                )
            if research_visit.actual_passage_timestep != party["actual_passage_timestep"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research actual passage "
                    f"for {_visit_text(visit_key)} differs."
                )
            if research_visit.assigned_rank != party["assigned_rank"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research assigned_rank "
                    f"for {_visit_text(visit_key)} differs."
                )
            if research_visit.actual_node_passage_rank != party["actual_node_passage_rank"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research actual rank for "
                    f"{_visit_text(visit_key)} differs."
                )
            if research_visit.formal_route_next_link_name != party["formal_route_next_link_name"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research formal route for "
                    f"{_visit_text(visit_key)} differs."
                )
            if research_visit.predicted_route_next_link_name != party["predicted_route_next_link_name"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research predicted route "
                    f"for {_visit_text(visit_key)} differs."
                )
            if research_visit.actual_route_next_link_name != party["actual_route_next_link_name"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research actual route for "
                    f"{_visit_text(visit_key)} differs."
                )
            if research_visit.true_vot_per_second != party["true_vot_per_second"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research true VOT for "
                    f"{_visit_text(visit_key)} differs."
                )
            if research_visit.declared_vot_per_second != party["declared_vot_per_second"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research declared VOT for "
                    f"{_visit_text(visit_key)} differs."
                )
            party["actual_observation_status"] = research_visit.actual_observation_status
            party["reference_payment"] = research_visit.reference_payment
            party["reference_compensation"] = research_visit.reference_compensation
            party["reference_payment_status"] = _reference_amount_status(
                party["role"], "payment", research_visit.reference_payment
            )
            party["reference_compensation_status"] = _reference_amount_status(
                party["role"], "compensation", research_visit.reference_compensation
            )
            party["realized_time_value"] = research_visit.realized_time_value
            party["realized_delay_loss"] = research_visit.realized_delay_loss
            party["realized_gain"] = research_visit.realized_gain
            party["satisfaction_status"] = research_visit.satisfaction_status
            party["satisfaction_reason"] = research_visit.satisfaction_reason
            party["actual_rank_change"] = research_visit.actual_rank_change
            computed_rank_change = _subtract_ints(
                party["assigned_rank"], party["actual_node_passage_rank"]
            )
            if research_visit.actual_rank_change != computed_rank_change:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research actual_rank_change "
                    f"for {_visit_text(visit_key)} differs from assigned minus actual."
                )
            if party["role"] == "buyer" and research_visit.official_payment != party["official_payment"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research official_payment "
                    f"for {_visit_text(visit_key)} differs from payment_P_b."
                )
            if (
                party["role"] == "seller"
                and research_visit.official_compensation != party["official_compensation"]
            ):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research official_compensation "
                    f"for {_visit_text(visit_key)} differs from compensation_amount."
                )
            if party["role"] == "nonparticipating":
                if research_visit.baseline_minus_candidate_time_value != party["predicted_external_effect_value"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: research "
                        "baseline_minus_candidate_time_value for "
                        f"{_visit_text(visit_key)} differs from the traffic observation."
                    )
                if party["actual_passage_timestep"] is None:
                    party["actual_external_effect_value"] = None
                    party["actual_signed_time_difference_timesteps"] = None
                else:
                    party["actual_external_effect_value"] = (
                        research_visit.baseline_minus_actual_time_value
                    )
                    party["actual_signed_time_difference_timesteps"] = _subtract_ints(
                        party["baseline_passage_timestep"],
                        party["actual_passage_timestep"],
                    )
            party["trade_ex_post_evaluation_status"] = status
            party["actual_evaluation_available"] = transaction["actual_evaluation_available"]
            party["economically_feasible"] = transaction["economically_feasible"]
            party["candidate_infeasibility_reasons"] = transaction[
                "candidate_infeasibility_reasons"
            ]


def _annotate_established_mismatches() -> None:
    for transaction in GATE.established:
        route_mismatch_count = 0
        passage_mismatch_count = 0
        for party in transaction["parties"]:
            predicted_route = party["predicted_route_next_link_name"]
            actual_route = party["actual_route_next_link_name"]
            if (
                isinstance(predicted_route, str)
                and predicted_route != ""
                and isinstance(actual_route, str)
                and actual_route != ""
                and predicted_route != actual_route
            ):
                route_mismatch_count = route_mismatch_count + 1
            candidate_passage = party["candidate_passage_timestep"]
            actual_passage = party["actual_passage_timestep"]
            if (
                type(candidate_passage) is int
                and type(actual_passage) is int
                and candidate_passage != actual_passage
            ):
                passage_mismatch_count = passage_mismatch_count + 1
        transaction["route_mismatch_visit_count"] = route_mismatch_count
        transaction["passage_mismatch_visit_count"] = passage_mismatch_count
        transaction["any_route_mismatch"] = route_mismatch_count > 0
        transaction["any_passage_mismatch"] = passage_mismatch_count > 0
        transaction["same_inlink_multiple_buyer"] = _same_inlink_multiple(
            transaction["parties"], "buyer"
        )
        transaction["same_inlink_multiple_seller"] = _same_inlink_multiple(
            transaction["parties"], "seller"
        )
        transaction["multiple_buyer"] = transaction["buyer_count"] >= 2
        transaction["multiple_seller"] = transaction["seller_count"] >= 2
        transaction["multiple_buyer_and_seller"] = (
            transaction["multiple_buyer"] is True and transaction["multiple_seller"] is True
        )


def _party_row(transaction, party) -> dict:
    return {
        "scenario_name": transaction["scenario_name"],
        "tvt_decision_timestep": transaction["tvt_decision_timestep"],
        "node_name": transaction["node_name"],
        "candidate_identity": transaction["candidate_identity"],
        "buyers_sorted": _join_visit_keys(transaction["buyers_sorted"]),
        "sellers_sorted": _join_visit_keys(transaction["sellers_sorted"]),
        "nonparticipating_visits_sorted": _join_visit_keys(
            transaction["nonparticipating_visits_sorted"]
        ),
        "baseline_order_visit_keys": _join_visit_keys(transaction["baseline_order_visit_keys"]),
        "candidate_order_visit_keys": _join_visit_keys(transaction["candidate_order_visit_keys"]),
        "vehicle_name": party["vehicle_name"],
        "visit_id": party["visit_id"],
        "visit_key": _visit_text(party["visit_key"]),
        "role": party["role"],
        "participates_in_order_exchange": party["participates_in_order_exchange"],
        "is_right_of_entry_holder": party["is_right_of_entry_holder"],
        "inlink_name": party["inlink_name"],
        "baseline_arrival_timestep": party["baseline_arrival_timestep"],
        "baseline_arrival_tiebreaker": party["baseline_arrival_tiebreaker"],
        "vehicle_id": party["vehicle_id"],
        "actual_arrival_timestep": party["actual_arrival_timestep"],
        "baseline_minus_actual_arrival_timesteps": _subtract_ints(
            party["baseline_arrival_timestep"], party["actual_arrival_timestep"]
        ),
        "formal_route_next_link_name": party["formal_route_next_link_name"],
        "predicted_route_next_link_name": party["predicted_route_next_link_name"],
        "actual_route_next_link_name": party["actual_route_next_link_name"],
        "selected_because_nonparticipating_present": transaction[
            "selected_because_nonparticipating_present"
        ],
        "selected_because_multiple_buyers": transaction["selected_because_multiple_buyers"],
        "selected_because_multiple_sellers": transaction["selected_because_multiple_sellers"],
        "selection_reasons": transaction["selection_reasons"],
        "baseline_passage_timestep": party["baseline_passage_timestep"],
        "candidate_passage_timestep": party["candidate_passage_timestep"],
        "actual_passage_timestep": party["actual_passage_timestep"],
        "baseline_minus_candidate_passage_timesteps": _subtract_ints(
            party["baseline_passage_timestep"], party["candidate_passage_timestep"]
        ),
        "baseline_minus_actual_passage_timesteps": _subtract_ints(
            party["baseline_passage_timestep"], party["actual_passage_timestep"]
        ),
        "candidate_minus_actual_passage_timesteps": _subtract_ints(
            party["candidate_passage_timestep"], party["actual_passage_timestep"]
        ),
        "predicted_observation_status": party["predicted_observation_status"],
        "actual_observation_status": party["actual_observation_status"],
        "baseline_local_rank": party["baseline_local_rank"],
        "post_trade_local_rank": party["post_trade_local_rank"],
        "assigned_rank": party["assigned_rank"],
        "actual_node_passage_rank": party["actual_node_passage_rank"],
        "binding_sequence_auxiliary_rank": party["binding_sequence_auxiliary_rank"],
        "baseline_minus_candidate_local_rank": _subtract_ints(
            party["baseline_local_rank"], party["post_trade_local_rank"]
        ),
        "assigned_minus_actual_node_rank": _subtract_ints(
            party["assigned_rank"], party["actual_node_passage_rank"]
        ),
        "actual_rank_change": party["actual_rank_change"],
        "true_vot_per_second": party["true_vot_per_second"],
        "declared_vot_per_second": party["declared_vot_per_second"],
        "economically_feasible": party["economically_feasible"],
        "candidate_infeasibility_reasons": party["candidate_infeasibility_reasons"],
        "individual_economic_condition_status": party["individual_economic_condition_status"],
        "individual_economic_condition_reason": party["individual_economic_condition_reason"],
        "passes_positive_buyer_value_condition": party["passes_positive_buyer_value_condition"],
        "expected_time_saving_timesteps": party["expected_time_saving_timesteps"],
        "expected_waiting_increase_timesteps": party["expected_waiting_increase_timesteps"],
        "expected_delay_timesteps": party["expected_waiting_increase_timesteps"],
        "gross_time_value_G_b": party["gross_time_value_G_b"],
        "required_compensation_R_s": party["required_compensation_R_s"],
        "official_payment": party["official_payment"],
        "official_compensation": party["official_compensation"],
        "reference_payment": party["reference_payment"],
        "reference_compensation": party["reference_compensation"],
        "effective_payment_amount": party["effective_payment_amount"],
        "effective_compensation_amount": party["effective_compensation_amount"],
        "monetary_transfer_participation_status": party[
            "monetary_transfer_participation_status"
        ],
        "payment_record_status": party["payment_record_status"],
        "compensation_record_status": party["compensation_record_status"],
        "reference_payment_status": party["reference_payment_status"],
        "reference_compensation_status": party["reference_compensation_status"],
        "realized_time_value": party["realized_time_value"],
        "realized_delay_loss": party["realized_delay_loss"],
        "realized_gain": party["realized_gain"],
        "satisfaction_status": party["satisfaction_status"],
        "satisfaction_reason": party["satisfaction_reason"],
        "trade_ex_post_evaluation_status": party["trade_ex_post_evaluation_status"],
        "actual_evaluation_available": party["actual_evaluation_available"],
        "predicted_signed_time_difference_timesteps": party[
            "predicted_signed_time_difference_timesteps"
        ],
        "actual_signed_time_difference_timesteps": party[
            "actual_signed_time_difference_timesteps"
        ],
        "predicted_external_effect_value": party["predicted_external_effect_value"],
        "actual_external_effect_value": party["actual_external_effect_value"],
    }


def _summary_row(transaction) -> dict:
    right_of_entry = transaction["right_of_entry_visit_key"]
    if right_of_entry is None:
        right_of_entry_text = None
    else:
        right_of_entry_text = _visit_text(right_of_entry)
    return {
        "scenario_name": transaction["scenario_name"],
        "tvt_decision_timestep": transaction["tvt_decision_timestep"],
        "node_name": transaction["node_name"],
        "candidate_identity": transaction["candidate_identity"],
        "buyers_sorted": _join_visit_keys(transaction["buyers_sorted"]),
        "sellers_sorted": _join_visit_keys(transaction["sellers_sorted"]),
        "nonparticipating_visits_sorted": _join_visit_keys(
            transaction["nonparticipating_visits_sorted"]
        ),
        "right_of_entry_visit_key": right_of_entry_text,
        "buyer_count": transaction["buyer_count"],
        "seller_count": transaction["seller_count"],
        "nonparticipating_count": transaction["nonparticipating_count"],
        "trade_scope_count": transaction["trade_scope_count"],
        "selected_because_nonparticipating_present": transaction[
            "selected_because_nonparticipating_present"
        ],
        "selected_because_multiple_buyers": transaction["selected_because_multiple_buyers"],
        "selected_because_multiple_sellers": transaction["selected_because_multiple_sellers"],
        "selection_reasons": transaction["selection_reasons"],
        "baseline_order_visit_keys": _join_visit_keys(transaction["baseline_order_visit_keys"]),
        "candidate_order_visit_keys": _join_visit_keys(transaction["candidate_order_visit_keys"]),
        "nonparticipating_baseline_candidate_rank_all_equal": transaction[
            "nonparticipating_baseline_candidate_rank_all_equal"
        ],
        "economically_feasible": transaction["economically_feasible"],
        "candidate_infeasibility_reasons": transaction["candidate_infeasibility_reasons"],
        "total_G": transaction["total_G"],
        "total_R": transaction["total_R"],
        "surplus": transaction["surplus"],
        "total_official_payment": transaction["total_official_payment"],
        "total_official_compensation": transaction["total_official_compensation"],
        "payment_balance_difference": transaction["payment_balance_difference"],
        "payment_balance_satisfied": transaction["payment_balance_satisfied"],
        "actual_evaluation_available": transaction["actual_evaluation_available"],
        "trade_ex_post_evaluation_status": transaction["trade_ex_post_evaluation_status"],
        "route_mismatch_visit_count": transaction["route_mismatch_visit_count"],
        "passage_mismatch_visit_count": transaction["passage_mismatch_visit_count"],
        "any_route_mismatch": transaction["any_route_mismatch"],
        "any_passage_mismatch": transaction["any_passage_mismatch"],
        "same_inlink_multiple_buyer": transaction["same_inlink_multiple_buyer"],
        "same_inlink_multiple_seller": transaction["same_inlink_multiple_seller"],
        "multiple_buyer": transaction["multiple_buyer"],
        "multiple_seller": transaction["multiple_seller"],
        "multiple_buyer_and_seller": transaction["multiple_buyer_and_seller"],
    }


def _candidate_summary_row(candidate) -> dict:
    right_of_entry = candidate["right_of_entry_visit_key"]
    if right_of_entry is None:
        right_of_entry_text = None
    else:
        right_of_entry_text = _visit_text(right_of_entry)
    return {
        "scenario_name": candidate["scenario_name"],
        "tvt_decision_timestep": candidate["tvt_decision_timestep"],
        "node_name": candidate["node_name"],
        "candidate_identity": candidate["candidate_identity"],
        "candidate_evaluation_index": candidate["candidate_evaluation_index"],
        "buyers_sorted": _join_visit_keys(candidate["buyers_sorted"]),
        "sellers_sorted": _join_visit_keys(candidate["sellers_sorted"]),
        "nonparticipating_visits_sorted": _join_visit_keys(
            candidate["nonparticipating_visits_sorted"]
        ),
        "buyer_count": candidate["buyer_count"],
        "seller_count": candidate["seller_count"],
        "nonparticipating_count": candidate["nonparticipating_count"],
        "trade_scope_count": candidate["trade_scope_count"],
        "right_of_entry_visit_key": right_of_entry_text,
        "baseline_order_visit_keys": _join_visit_keys(candidate["baseline_order_visit_keys"]),
        "candidate_order_visit_keys": _join_visit_keys(candidate["candidate_order_visit_keys"]),
        "local_virtual_calculation_status": candidate["local_virtual_calculation_status"],
        "candidate_passage_resolved": candidate["candidate_passage_resolved"],
        "unresolved_reasons": candidate["unresolved_reasons"],
        "economically_feasible": candidate["economically_feasible"],
        "candidate_infeasibility_reasons": candidate["candidate_infeasibility_reasons"],
        "selected": candidate["selected"],
        "selection_status": candidate["selection_status"],
        "selection_reason": candidate["selection_reason"],
        "total_G": candidate["total_G"],
        "total_R": candidate["total_R"],
        "surplus": candidate["surplus"],
        "multiple_buyer": candidate["multiple_buyer"],
        "multiple_seller": candidate["multiple_seller"],
        "multiple_buyer_and_seller": candidate["multiple_buyer_and_seller"],
        "same_inlink_multiple_buyer": candidate["same_inlink_multiple_buyer"],
        "same_inlink_multiple_seller": candidate["same_inlink_multiple_seller"],
    }


def _candidate_party_row(candidate, party) -> dict:
    return {
        "scenario_name": candidate["scenario_name"],
        "tvt_decision_timestep": candidate["tvt_decision_timestep"],
        "node_name": candidate["node_name"],
        "candidate_identity": candidate["candidate_identity"],
        "candidate_evaluation_index": candidate["candidate_evaluation_index"],
        "selected": candidate["selected"],
        "vehicle_name": party["vehicle_name"],
        "visit_id": party["visit_id"],
        "visit_key": _visit_text(party["visit_key"]),
        "role": party["role"],
        "inlink_name": party["inlink_name"],
        "baseline_arrival_timestep": party["baseline_arrival_timestep"],
        "baseline_arrival_tiebreaker": party["baseline_arrival_tiebreaker"],
        "vehicle_id": party["vehicle_id"],
        "is_right_of_entry_holder": party["is_right_of_entry_holder"],
        "baseline_passage_timestep": party["baseline_passage_timestep"],
        "candidate_passage_timestep": party["candidate_passage_timestep"],
        "baseline_local_rank": party["baseline_local_rank"],
        "candidate_local_rank": party["candidate_local_rank"],
        "binding_sequence_auxiliary_rank": party["binding_sequence_auxiliary_rank"],
        "predicted_route_next_link_name": party["predicted_route_next_link_name"],
        "true_vot_per_second": party["true_vot_per_second"],
        "declared_vot_per_second": party["declared_vot_per_second"],
        "individual_economic_condition_status": party["individual_economic_condition_status"],
        "individual_economic_condition_reason": party["individual_economic_condition_reason"],
        "passes_positive_buyer_value_condition": party["passes_positive_buyer_value_condition"],
        "expected_time_saving_timesteps": party["expected_time_saving_timesteps"],
        "expected_waiting_increase_timesteps": party["expected_waiting_increase_timesteps"],
        "expected_delay_timesteps": party["expected_delay_timesteps"],
        "gross_time_value_G_b": party["gross_time_value_G_b"],
        "required_compensation_R_s": party["required_compensation_R_s"],
    }


def _special_transactions(transactions) -> list[dict]:
    selected = []
    for transaction in transactions:
        if transaction["multiple_buyer"] is True:
            selected.append(transaction)
            continue
        if transaction["multiple_seller"] is True:
            selected.append(transaction)
            continue
        if transaction["same_inlink_multiple_buyer"] is True:
            selected.append(transaction)
            continue
        if transaction["same_inlink_multiple_seller"] is True:
            selected.append(transaction)
            continue
        if (
            transaction["any_route_mismatch"] is True
            and transaction["any_passage_mismatch"] is True
        ):
            selected.append(transaction)
    return selected


def _increment_reason_counts(counter: dict, text: str) -> None:
    if text is None or text == "":
        return
    for reason in text.split("|"):
        if reason == "":
            continue
        if reason not in counter:
            counter[reason] = 0
        counter[reason] = counter[reason] + 1


def _format_reason_counts(counter: dict) -> list[str]:
    names = []
    for name in counter:
        names.append(name)
    names.sort()
    lines = []
    for name in names:
        lines.append(f"  {name}: {counter[name]}")
    if len(lines) == 0:
        lines.append("  (none)")
    return lines


def _collect_counts(bundle) -> dict:
    buyer_visits = 0
    seller_visits = 0
    nonparticipating_visits = 0
    equal_count = 0
    unequal_count = 0
    unobserved = 0
    multiple_buyer = 0
    multiple_seller = 0
    both_multiple = 0
    either_multiple = 0
    same_inlink_buyer = 0
    same_inlink_seller = 0
    same_inlink_both = 0
    route_mismatch = 0
    passage_mismatch = 0
    route_and_passage = 0
    route_only = 0
    passage_only = 0
    overlap = 0
    identities = set()
    for transaction in GATE.established:
        if transaction["candidate_identity"] in identities:
            raise RuntimeError(
                "Duplicate established candidate_identity "
                f"{transaction['candidate_identity']!r}."
            )
        identities.add(transaction["candidate_identity"])
        if transaction["multiple_buyer"] is True:
            multiple_buyer = multiple_buyer + 1
        if transaction["multiple_seller"] is True:
            multiple_seller = multiple_seller + 1
        if transaction["multiple_buyer_and_seller"] is True:
            both_multiple = both_multiple + 1
        either = transaction["multiple_buyer"] is True or transaction["multiple_seller"] is True
        if either is True:
            either_multiple = either_multiple + 1
        if transaction["same_inlink_multiple_buyer"] is True:
            same_inlink_buyer = same_inlink_buyer + 1
        if transaction["same_inlink_multiple_seller"] is True:
            same_inlink_seller = same_inlink_seller + 1
        if (
            transaction["same_inlink_multiple_buyer"] is True
            and transaction["same_inlink_multiple_seller"] is True
        ):
            same_inlink_both = same_inlink_both + 1
        if transaction["any_route_mismatch"] is True:
            route_mismatch = route_mismatch + 1
        if transaction["any_passage_mismatch"] is True:
            passage_mismatch = passage_mismatch + 1
        if transaction["any_route_mismatch"] is True and transaction["any_passage_mismatch"] is True:
            route_and_passage = route_and_passage + 1
            if either is True:
                overlap = overlap + 1
        if transaction["any_route_mismatch"] is True and transaction["any_passage_mismatch"] is not True:
            route_only = route_only + 1
        if transaction["any_route_mismatch"] is not True and transaction["any_passage_mismatch"] is True:
            passage_only = passage_only + 1
        if transaction["tvt_decision_timestep"] is None:
            raise RuntimeError("Established transaction has no tvt_decision_timestep.")
        _validate_established_transaction_baseline_ranks(transaction)
        for party in transaction["parties"]:
            if party["visit_key"] is None:
                raise RuntimeError("Established party has no VisitKey.")
            if not isinstance(party["inlink_name"], str) or party["inlink_name"] == "":
                raise RuntimeError("Established party has no inlink_name.")
            _validate_established_party_arrival_fields(
                party, transaction["node_name"], transaction["tvt_decision_timestep"]
            )
            if type(party["actual_arrival_timestep"]) is not int:
                raise RuntimeError("Established party has no actual_arrival_timestep.")
            if type(party["baseline_passage_timestep"]) is not int:
                raise RuntimeError("Established party has no baseline_passage_timestep.")
            if type(party["candidate_passage_timestep"]) is not int:
                raise RuntimeError("Established party has no candidate_passage_timestep.")
            if type(party["actual_passage_timestep"]) is not int:
                raise RuntimeError("Established party has no actual_passage_timestep.")
            trade_scope_party = party["role"] == "buyer" or party["role"] == "seller"
            if party["role"] == "buyer":
                buyer_visits = buyer_visits + 1
            elif party["role"] == "seller":
                seller_visits = seller_visits + 1
            elif party["role"] == "nonparticipating":
                nonparticipating_visits = nonparticipating_visits + 1
            else:
                raise RuntimeError(f"Established party role is {party['role']!r}.")
            if trade_scope_party is True:
                if party["candidate_passage_timestep"] == party["actual_passage_timestep"]:
                    equal_count = equal_count + 1
                else:
                    unequal_count = unequal_count + 1
    research_buyers = 0
    research_sellers = 0
    research_equal = 0
    research_unequal = 0
    research_unobserved = 0
    for visit in bundle.visits:
        trade_scope_visit = visit.role == "buyer" or visit.role == "seller"
        if visit.role == "buyer":
            research_buyers = research_buyers + 1
        elif visit.role == "seller":
            research_sellers = research_sellers + 1
        if trade_scope_visit is not True:
            continue
        if visit.actual_passage_timestep is None:
            research_unobserved = research_unobserved + 1
        if visit.candidate_passage_timestep is not None and visit.actual_passage_timestep is not None:
            if visit.candidate_passage_timestep == visit.actual_passage_timestep:
                research_equal = research_equal + 1
            else:
                research_unequal = research_unequal + 1
    candidate_identities = set()
    previous_index_by_decision = {}
    resolved = 0
    unresolved = 0
    feasible = 0
    infeasible = 0
    selected = 0
    not_selected = 0
    candidate_multiple_buyer = 0
    candidate_multiple_seller = 0
    candidate_same_buyer = 0
    candidate_same_seller = 0
    unresolved_reasons = {}
    infeasibility_reasons = {}
    selection_reasons = {}
    for candidate in GATE.considered:
        if candidate["candidate_identity"] in candidate_identities:
            raise RuntimeError(
                "Duplicate considered candidate_identity "
                f"{candidate['candidate_identity']!r}."
            )
        candidate_identities.add(candidate["candidate_identity"])
        decision_key = (candidate["tvt_decision_timestep"], candidate["node_name"])
        previous_index = previous_index_by_decision.get(decision_key, 0)
        if candidate["candidate_evaluation_index"] != previous_index + 1:
            raise RuntimeError(
                f"{_decision_label(decision_key[1], decision_key[0])}: candidate "
                "evaluation index is not the saved order."
            )
        previous_index_by_decision[decision_key] = candidate["candidate_evaluation_index"]
        if candidate["candidate_passage_resolved"] is True:
            resolved = resolved + 1
        elif candidate["candidate_passage_resolved"] is False:
            unresolved = unresolved + 1
        else:
            raise RuntimeError("candidate_passage_resolved is not bool.")
        for party in candidate["parties"]:
            traffic_record = candidate["traffic_by_key"][party["visit_key"]]
            if party["baseline_passage_timestep"] != traffic_record.baseline_passage_timestep:
                raise RuntimeError(
                    "Candidate baseline passage differs from the saved traffic observation."
                )
            if party["candidate_passage_timestep"] != traffic_record.candidate_passage_timestep:
                raise RuntimeError(
                    "Candidate passage was not copied from the saved traffic observation."
                )
            _validate_candidate_party_arrival_fields(
                party, candidate["node_name"], candidate["tvt_decision_timestep"]
            )
        if candidate["economically_feasible"] is True:
            feasible = feasible + 1
        elif candidate["economically_feasible"] is False:
            infeasible = infeasible + 1
        elif candidate["economically_feasible"] is not None:
            raise RuntimeError("economically_feasible is not True, False, or None.")
        if candidate["selected"] is True:
            selected = selected + 1
        else:
            not_selected = not_selected + 1
            for party in candidate["parties"]:
                if "official_payment" in party or "official_compensation" in party:
                    raise RuntimeError("A non-selected candidate party stores payment.")
                if "actual_passage_timestep" in party or "actual_node_passage_rank" in party:
                    raise RuntimeError("A non-selected candidate party stores an actual value.")
                if "actual_route_next_link_name" in party:
                    raise RuntimeError("A non-selected candidate party stores an actual route.")
        if candidate["multiple_buyer"] is True:
            candidate_multiple_buyer = candidate_multiple_buyer + 1
        if candidate["multiple_seller"] is True:
            candidate_multiple_seller = candidate_multiple_seller + 1
        if candidate["same_inlink_multiple_buyer"] is True:
            candidate_same_buyer = candidate_same_buyer + 1
        if candidate["same_inlink_multiple_seller"] is True:
            candidate_same_seller = candidate_same_seller + 1
        _increment_reason_counts(unresolved_reasons, candidate["unresolved_reasons"])
        _increment_reason_counts(infeasibility_reasons, candidate["candidate_infeasibility_reasons"])
        _increment_reason_counts(selection_reasons, candidate["selection_reason"])
    selected_identities = set()
    established_identities = set()
    for candidate in GATE.considered:
        if candidate["selected"] is True:
            selected_identities.add(candidate["candidate_identity"])
    for transaction in GATE.established:
        established_identities.add(transaction["candidate_identity"])
    if selected_identities != established_identities:
        raise RuntimeError(
            "Selected candidate identities do not match established transaction identities."
        )
    special = _special_transactions(GATE.established)
    return {
        "established_transaction_count": len(GATE.established),
        "buyer_visit_count": buyer_visits,
        "seller_visit_count": seller_visits,
        "nonparticipating_visit_count": nonparticipating_visits,
        "trade_scope_party_observation_count": buyer_visits + seller_visits,
        "candidate_equals_actual_count": equal_count,
        "candidate_differs_from_actual_count": unequal_count,
        "actual_unobserved_count": unobserved,
        "multiple_buyer_transaction_count": multiple_buyer,
        "multiple_seller_transaction_count": multiple_seller,
        "both_multiple_transaction_count": both_multiple,
        "either_multiple_transaction_count": either_multiple,
        "same_inlink_multiple_buyer_transaction_count": same_inlink_buyer,
        "same_inlink_multiple_seller_transaction_count": same_inlink_seller,
        "same_inlink_both_transaction_count": same_inlink_both,
        "route_mismatch_transaction_count": route_mismatch,
        "passage_mismatch_transaction_count": passage_mismatch,
        "route_and_passage_mismatch_count": route_and_passage,
        "route_mismatch_without_passage_count": route_only,
        "passage_mismatch_without_route_count": passage_only,
        "multiple_and_route_passage_overlap_count": overlap,
        "special_transaction_count": len(special),
        "considered_candidate_count": len(GATE.considered),
        "resolved_candidate_count": resolved,
        "unresolved_candidate_count": unresolved,
        "feasible_candidate_count": feasible,
        "infeasible_candidate_count": infeasible,
        "selected_candidate_count": selected,
        "not_selected_candidate_count": not_selected,
        "candidate_multiple_buyer_count": candidate_multiple_buyer,
        "candidate_multiple_seller_count": candidate_multiple_seller,
        "candidate_same_inlink_buyer_count": candidate_same_buyer,
        "candidate_same_inlink_seller_count": candidate_same_seller,
        "unresolved_reasons": unresolved_reasons,
        "infeasibility_reasons": infeasibility_reasons,
        "selection_reasons": selection_reasons,
        "research_transaction_count": bundle.scenario[0].transaction_count,
        "research_buyer_visit_count": research_buyers,
        "research_seller_visit_count": research_sellers,
        "research_equal_count": research_equal,
        "research_unequal_count": research_unequal,
        "research_unobserved_count": research_unobserved,
        "special_transactions": special,
    }


def _require_expected_counts(counts) -> None:
    expectations = (
        ("established_transaction_count", EXPECTED_ESTABLISHED_TRANSACTION_COUNT),
        ("buyer_visit_count", EXPECTED_BUYER_VISIT_COUNT),
        ("seller_visit_count", EXPECTED_SELLER_VISIT_COUNT),
        ("trade_scope_party_observation_count", EXPECTED_TRADE_SCOPE_PARTY_OBSERVATION_COUNT),
        ("candidate_equals_actual_count", EXPECTED_CANDIDATE_EQUALS_ACTUAL_COUNT),
        ("candidate_differs_from_actual_count", EXPECTED_CANDIDATE_DIFFERS_FROM_ACTUAL_COUNT),
        ("actual_unobserved_count", EXPECTED_ACTUAL_UNOBSERVED_COUNT),
        ("multiple_buyer_transaction_count", EXPECTED_MULTIPLE_BUYER_TRANSACTION_COUNT),
        ("multiple_seller_transaction_count", EXPECTED_MULTIPLE_SELLER_TRANSACTION_COUNT),
        ("both_multiple_transaction_count", EXPECTED_BOTH_MULTIPLE_TRANSACTION_COUNT),
        ("either_multiple_transaction_count", EXPECTED_EITHER_MULTIPLE_TRANSACTION_COUNT),
        ("route_mismatch_transaction_count", EXPECTED_ROUTE_MISMATCH_TRANSACTION_COUNT),
        ("passage_mismatch_without_route_count", EXPECTED_PASSAGE_MISMATCH_WITHOUT_ROUTE_COUNT),
        ("route_and_passage_mismatch_count", EXPECTED_ROUTE_AND_PASSAGE_MISMATCH_COUNT),
        ("route_mismatch_without_passage_count", EXPECTED_ROUTE_MISMATCH_WITHOUT_PASSAGE_COUNT),
        ("multiple_and_route_passage_overlap_count", EXPECTED_MULTIPLE_AND_ROUTE_PASSAGE_OVERLAP_COUNT),
        ("special_transaction_count", EXPECTED_SPECIAL_TRANSACTION_COUNT),
        ("research_transaction_count", EXPECTED_ESTABLISHED_TRANSACTION_COUNT),
        ("research_buyer_visit_count", EXPECTED_BUYER_VISIT_COUNT),
        ("research_seller_visit_count", EXPECTED_SELLER_VISIT_COUNT),
        ("research_equal_count", EXPECTED_CANDIDATE_EQUALS_ACTUAL_COUNT),
        ("research_unequal_count", EXPECTED_CANDIDATE_DIFFERS_FROM_ACTUAL_COUNT),
        ("research_unobserved_count", EXPECTED_ACTUAL_UNOBSERVED_COUNT),
        ("selected_candidate_count", EXPECTED_ESTABLISHED_TRANSACTION_COUNT),
    )
    for field_name, expected in expectations:
        actual = counts[field_name]
        if actual != expected:
            raise RuntimeError(
                f"{field_name} is {actual}, expected {expected}. "
                "The diagnostic does not rewrite the saved records."
            )


def _summary_text(world, counts) -> str:
    lines = [
        "Four-cross 600-vehicle all-transaction and all-candidate diagnostic",
        "",
        "Simulation conditions",
        f"  nodes: {len(world.NODES)}",
        f"  links: {len(world.LINKS)}",
        f"  tvt-mp nodes: {len(four_cross_trial.TVT_MP_NODE_NAMES)}",
        f"  vehicles: {len(world.VEHICLES)}",
        (
            "  evaluation timesteps: "
            f"{four_cross_trial.EVALUATION_START_TIMESTEP}..{four_cross_trial.EVALUATION_END_TIMESTEP}"
        ),
        f"  world end timestep: {world.T}",
        f"  vot seed: {four_cross_trial.VOT_SEED}",
        f"  traffic seed: {four_cross_trial.TRAFFIC_SEED}",
        f"  horizon steps: {world.order_control_tvt_baseline_horizon_steps}",
        f"  clearance timesteps: {four_cross_trial.CLEARANCE_TIMESTEPS}",
        f"  candidate visit limit: {world.order_control_tvt_max_candidate_visit_count}",
        "",
        "Established transactions",
        f"  established transactions: {counts['established_transaction_count']}",
        f"  buyer visits: {counts['buyer_visit_count']}",
        f"  seller visits: {counts['seller_visit_count']}",
        f"  nonparticipating visits: {counts['nonparticipating_visit_count']}",
        f"  multiple buyer: {counts['multiple_buyer_transaction_count']}",
        f"  multiple seller: {counts['multiple_seller_transaction_count']}",
        f"  multiple buyer and seller: {counts['both_multiple_transaction_count']}",
        f"  multiple buyer or seller: {counts['either_multiple_transaction_count']}",
        (
            "  same inlink multiple buyer: "
            f"{counts['same_inlink_multiple_buyer_transaction_count']}"
        ),
        (
            "  same inlink multiple seller: "
            f"{counts['same_inlink_multiple_seller_transaction_count']}"
        ),
        (
            "  same inlink multiple buyer and seller: "
            f"{counts['same_inlink_both_transaction_count']}"
        ),
        f"  route mismatch: {counts['route_mismatch_transaction_count']}",
        f"  passage mismatch: {counts['passage_mismatch_transaction_count']}",
        f"  route and passage mismatch: {counts['route_and_passage_mismatch_count']}",
        f"  special transactions: {counts['special_transaction_count']}",
        "",
        "Considered candidates",
        f"  considered candidates: {counts['considered_candidate_count']}",
        f"  resolved: {counts['resolved_candidate_count']}",
        f"  unresolved: {counts['unresolved_candidate_count']}",
        f"  economically feasible: {counts['feasible_candidate_count']}",
        f"  economically infeasible: {counts['infeasible_candidate_count']}",
        f"  selected: {counts['selected_candidate_count']}",
        f"  not selected: {counts['not_selected_candidate_count']}",
        f"  multiple buyer: {counts['candidate_multiple_buyer_count']}",
        f"  multiple seller: {counts['candidate_multiple_seller_count']}",
        f"  same inlink multiple buyer: {counts['candidate_same_inlink_buyer_count']}",
        f"  same inlink multiple seller: {counts['candidate_same_inlink_seller_count']}",
        "  unresolved reasons:",
    ]
    lines.extend(_format_reason_counts(counts["unresolved_reasons"]))
    lines.append("  infeasibility reasons:")
    lines.extend(_format_reason_counts(counts["infeasibility_reasons"]))
    lines.append("  selection reasons:")
    lines.extend(_format_reason_counts(counts["selection_reasons"]))
    lines.append("")
    lines.append(
        "generated_at in manifest.json is the file write time, not a simulation timestep."
    )
    return "\n".join(lines) + "\n"


def _parties_for_display(parties) -> list:
    """Display order follows saved baseline_local_rank only."""
    ordered = list(parties)
    ordered.sort(key=lambda party: party["baseline_local_rank"])
    return ordered


def _validate_established_transaction_baseline_ranks(transaction) -> None:
    node_name = transaction["node_name"]
    timestep = transaction["tvt_decision_timestep"]
    baseline_order_visit_keys = transaction["baseline_order_visit_keys"]
    if not isinstance(baseline_order_visit_keys, tuple):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: baseline_order_visit_keys "
            f"is {type(baseline_order_visit_keys).__name__}, not tuple."
        )
    position_by_visit_key = {}
    for position, visit_key in enumerate(baseline_order_visit_keys, start=1):
        visit_key = _plain_visit_key(visit_key)
        if visit_key in position_by_visit_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: baseline_order_visit_keys "
                f"repeats {_visit_text(visit_key)}."
            )
        position_by_visit_key[visit_key] = position
    seen_party_visit_keys = set()
    for party in transaction["parties"]:
        visit_key = _plain_visit_key(party["visit_key"])
        if visit_key in seen_party_visit_keys:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate party "
                f"{_visit_text(visit_key)}."
            )
        seen_party_visit_keys.add(visit_key)
        saved_rank = party["baseline_local_rank"]
        if type(saved_rank) is not int:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: baseline_local_rank for "
                f"{_visit_text(visit_key)} is {saved_rank!r}."
            )
        if saved_rank < 1:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: baseline_local_rank for "
                f"{_visit_text(visit_key)} must be >= 1; got {saved_rank!r}."
            )
        if visit_key not in position_by_visit_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: party "
                f"{_visit_text(visit_key)} is not in baseline_order_visit_keys."
            )
        expected_rank = position_by_visit_key[visit_key]
        if saved_rank != expected_rank:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: baseline_local_rank for "
                f"{_visit_text(visit_key)} is {saved_rank!r}, expected {expected_rank!r} "
                "from saved candidate_visits order."
            )
    previous_rank = None
    for party in _parties_for_display(transaction["parties"]):
        current_rank = party["baseline_local_rank"]
        if previous_rank is not None and current_rank <= previous_rank:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: party baseline_local_rank "
                f"values are not strictly increasing in display order: "
                f"{previous_rank!r} then {current_rank!r}."
            )
        previous_rank = current_rank


def _validate_established_party_arrival_fields(party, node_name, timestep) -> None:
    label = f"{_decision_label(node_name, timestep)} {_visit_text(party['visit_key'])}"
    _require_non_negative_int(
        party["baseline_arrival_timestep"],
        f"{label} baseline_arrival_timestep",
    )
    _require_numeric_not_bool(
        party["baseline_arrival_tiebreaker"],
        f"{label} baseline_arrival_tiebreaker",
    )
    _require_non_negative_int(party["vehicle_id"], f"{label} vehicle_id")


def _validate_candidate_party_arrival_fields(party, node_name, timestep) -> None:
    baseline_arrival = party["baseline_arrival_timestep"]
    if baseline_arrival is None:
        return
    label = f"{_decision_label(node_name, timestep)} {_visit_text(party['visit_key'])}"
    _require_non_negative_int(baseline_arrival, f"{label} baseline_arrival_timestep")
    tiebreaker = party["baseline_arrival_tiebreaker"]
    if tiebreaker is None:
        raise RuntimeError(
            f"{label}: baseline_arrival_timestep is set but "
            "baseline_arrival_tiebreaker is missing."
        )
    _require_numeric_not_bool(tiebreaker, f"{label} baseline_arrival_tiebreaker")
    _require_non_negative_int(party["vehicle_id"], f"{label} vehicle_id")


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            cells = {}
            for column in columns:
                cells[column] = _csv_cell(row[column])
            writer.writerow(cells)


def _write_outputs(world, counts) -> dict:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    if OUTPUT_DIR == four_cross_trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory is the trial output directory.")
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    established_summary_rows = []
    established_party_rows = []
    for transaction in GATE.established:
        established_summary_rows.append(_summary_row(transaction))
        for party in _parties_for_display(transaction["parties"]):
            established_party_rows.append(_party_row(transaction, party))
    candidate_summary_rows = []
    candidate_party_rows = []
    for candidate in GATE.considered:
        candidate_summary_rows.append(_candidate_summary_row(candidate))
        for party in _parties_for_display(candidate["parties"]):
            candidate_party_rows.append(_candidate_party_row(candidate, party))
    special_party_rows = []
    for transaction in counts["special_transactions"]:
        for party in _parties_for_display(transaction["parties"]):
            special_party_rows.append(_party_row(transaction, party))
    _write_csv(
        OUTPUT_DIR / ESTABLISHED_SUMMARY_CSV_NAME,
        SUMMARY_COLUMNS,
        established_summary_rows,
    )
    _write_csv(
        OUTPUT_DIR / ESTABLISHED_PARTIES_CSV_NAME,
        PARTY_COLUMNS,
        established_party_rows,
    )
    _write_csv(
        OUTPUT_DIR / CANDIDATE_SUMMARY_CSV_NAME,
        CANDIDATE_SUMMARY_COLUMNS,
        candidate_summary_rows,
    )
    _write_csv(
        OUTPUT_DIR / CANDIDATE_PARTIES_CSV_NAME,
        CANDIDATE_PARTY_COLUMNS,
        candidate_party_rows,
    )
    _write_csv(
        OUTPUT_DIR / SPECIAL_PARTIES_CSV_NAME,
        PARTY_COLUMNS,
        special_party_rows,
    )
    summary_text = _summary_text(world, counts)
    (OUTPUT_DIR / SUMMARY_TEXT_NAME).write_text(summary_text, encoding="utf-8")
    file_write_time = datetime.datetime.now().isoformat(timespec="seconds")
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "diagnostic_script_name": DIAGNOSTIC_SCRIPT_NAME,
        "simulation_conditions": {
            "node_count": len(world.NODES),
            "link_count": len(world.LINKS),
            "tvt_mp_node_count": len(four_cross_trial.TVT_MP_NODE_NAMES),
            "vehicle_count": len(world.VEHICLES),
            "evaluation_start_timestep": four_cross_trial.EVALUATION_START_TIMESTEP,
            "evaluation_end_timestep": four_cross_trial.EVALUATION_END_TIMESTEP,
            "world_end_timestep": world.T,
            "vot_seed": four_cross_trial.VOT_SEED,
            "traffic_seed": four_cross_trial.TRAFFIC_SEED,
            "horizon_steps": world.order_control_tvt_baseline_horizon_steps,
            "clearance_timesteps": four_cross_trial.CLEARANCE_TIMESTEPS,
            "max_candidate_visit_count": world.order_control_tvt_max_candidate_visit_count,
        },
        "seed": {
            "vot_seed": four_cross_trial.VOT_SEED,
            "traffic_seed": four_cross_trial.TRAFFIC_SEED,
        },
        "output_filenames": list(OUTPUT_FILE_NAMES),
        "row_counts": {
            "established_summary_rows": len(established_summary_rows),
            "established_party_rows": len(established_party_rows),
            "considered_candidate_summary_rows": len(candidate_summary_rows),
            "considered_candidate_party_rows": len(candidate_party_rows),
            "special_party_rows": len(special_party_rows),
        },
        "established_transaction_count": counts["established_transaction_count"],
        "considered_candidate_count": counts["considered_candidate_count"],
        "special_transaction_count": counts["special_transaction_count"],
        "completion_status": "completed",
        "generated_at": file_write_time,
        "generated_at_meaning": (
            "file write time on the machine that created this manifest; "
            "not a simulation timestep"
        ),
    }
    (OUTPUT_DIR / MANIFEST_JSON_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected_names = set(OUTPUT_FILE_NAMES)
    for path in OUTPUT_DIR.iterdir():
        if path.name not in expected_names:
            raise RuntimeError(f"Unexpected file in output directory: {path.name}.")
    return {
        "established_summary_rows": len(established_summary_rows),
        "established_party_rows": len(established_party_rows),
        "candidate_summary_rows": len(candidate_summary_rows),
        "candidate_party_rows": len(candidate_party_rows),
        "special_party_rows": len(special_party_rows),
    }


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


def main() -> int:
    original_python_recursion_limit = sys.getrecursionlimit()
    GATE.established.clear()
    GATE.considered.clear()
    GATE.actual_node_arrivals.clear()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if original_python_recursion_limit < four_cross_trial.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(four_cross_trial.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_trial_world()
        # Arrival and driver hooks are installed first. The trial spillback
        # wrapper then saves those hooks and calls them once.
        install_observation_hooks(world)
        four_cross_trial.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            four_cross_trial.restore_real_world_spillback_observation()
            restore_observation_hooks()
        if world.T != EXPECTED_WORLD_T:
            raise RuntimeError(f"World.T is {world.T!r}, expected {EXPECTED_WORLD_T}.")
        evaluation = four_cross_trial.verify_evaluation_end(world)
        if evaluation["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")
        four_cross_trial.verify_spillback_observation(four_cross_trial.SPILLBACK_TIMESTEP_ROWS)
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        _attach_actual_and_research(world, bundle)
        _annotate_established_mismatches()
        counts = _collect_counts(bundle)
        _require_expected_counts(counts)
        _write_outputs(world, counts)
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        four_cross_trial.restore_real_world_spillback_observation()
        restore_observation_hooks()
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


def _imported_module_names(tree) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def _called_attribute_names(tree) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
        elif isinstance(node.func, ast.Name):
            names.append(node.func.id)
    return names


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = _imported_module_names(tree)
    for module_name in imported:
        if module_name == "subprocess" or module_name == "shutil" or module_name == "git":
            raise RuntimeError(f"Diagnostic imports {module_name}.")
    called = _called_attribute_names(tree)
    for called_name in called:
        if called_name in ("system", "rmtree", "unlink", "rmdir"):
            raise RuntimeError(f"Diagnostic calls {called_name}.")
        if called_name in ("eval", "exec"):
            raise RuntimeError(f"Diagnostic calls {called_name}.")
        if called_name == "write_tvt_mp_research_output_csv":
            raise RuntimeError("Diagnostic writes the original trial research CSVs.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main":
                raise RuntimeError("Diagnostic calls the original trial main().")
    required_output_names = (
        "all_established_transactions_summary.csv",
        "all_established_transaction_parties.csv",
        "all_considered_candidates_summary.csv",
        "all_considered_candidate_parties.csv",
        "special_established_transaction_parties.csv",
        "diagnostic_summary.txt",
        "manifest.json",
    )
    if tuple(OUTPUT_FILE_NAMES) != required_output_names:
        raise RuntimeError("Output file names are not the fixed seven files.")
    if "baseline_arrival_timestep" not in PARTY_COLUMNS:
        raise RuntimeError("Established parties do not keep baseline arrival.")
    if "baseline_arrival_tiebreaker" not in PARTY_COLUMNS:
        raise RuntimeError("Established parties do not keep baseline_arrival_tiebreaker.")
    if "vehicle_id" not in PARTY_COLUMNS:
        raise RuntimeError("Established parties do not keep vehicle_id.")
    if "actual_arrival_timestep" not in PARTY_COLUMNS:
        raise RuntimeError("Established parties do not keep actual arrival.")
    if "baseline_arrival_timestep" not in CANDIDATE_PARTY_COLUMNS:
        raise RuntimeError("Candidate parties do not keep baseline arrival.")
    if "baseline_arrival_tiebreaker" not in CANDIDATE_PARTY_COLUMNS:
        raise RuntimeError("Candidate parties do not keep baseline_arrival_tiebreaker.")
    if "vehicle_id" not in CANDIDATE_PARTY_COLUMNS:
        raise RuntimeError("Candidate parties do not keep vehicle_id.")
    if "actual_arrival_timestep" in CANDIDATE_PARTY_COLUMNS:
        raise RuntimeError("Candidate party columns include an actual arrival field.")
    party_index = list(PARTY_COLUMNS).index("inlink_name")
    if list(PARTY_COLUMNS)[party_index + 1 : party_index + 6] != [
        "baseline_arrival_timestep",
        "baseline_arrival_tiebreaker",
        "vehicle_id",
        "actual_arrival_timestep",
        "baseline_minus_actual_arrival_timesteps",
    ]:
        raise RuntimeError(
            "Established party arrival columns are not separate fields in order."
        )
    candidate_index = list(CANDIDATE_PARTY_COLUMNS).index("inlink_name")
    if list(CANDIDATE_PARTY_COLUMNS)[candidate_index + 1 : candidate_index + 4] != [
        "baseline_arrival_timestep",
        "baseline_arrival_tiebreaker",
        "vehicle_id",
    ]:
        raise RuntimeError("Candidate party arrival columns are not separate fields in order.")
    if "SPECIAL_PARTIES_CSV_NAME" not in source or "PARTY_COLUMNS" not in source:
        raise RuntimeError("Special parties do not use the established party column contract.")
    if "_baseline_local_ranks" not in source:
        raise RuntimeError("baseline_local_rank is not read from saved candidate_visits.")
    display_function = _function_by_name(tree, "_parties_for_display")
    display_source = ast.get_source_segment(source, display_function)
    if display_source is None or "baseline_local_rank" not in display_source:
        raise RuntimeError("Display order does not follow baseline_local_rank.")
    if "baseline_arrival_tiebreaker" in display_source or "vehicle_id" in display_source:
        raise RuntimeError("Display order uses arrival_tiebreaker or vehicle_id.")
    if "arrival_tiebreaker" not in source:
        raise RuntimeError("Collector arrival_tiebreaker is not read from the snapshot.")
    if "_baseline_fields_from_collector" not in source:
        raise RuntimeError("Baseline arrival fields are not read from the collector snapshot.")
    write_outputs = _function_by_name(tree, "_write_outputs")
    write_called = _call_names(write_outputs)
    if "_parties_for_display" not in write_called:
        raise RuntimeError("Party CSV rows are not ordered for baseline_local_rank display.")
    rank_validate_function = _function_by_name(
        tree, "_validate_established_transaction_baseline_ranks"
    )
    rank_validate_source = ast.get_source_segment(source, rank_validate_function)
    if rank_validate_source is None:
        raise RuntimeError("Established baseline rank validation source is unavailable.")
    if "consecutive" in rank_validate_source:
        raise RuntimeError(
            "Established party baseline_local_rank must not be required consecutive from 1."
        )
    if "has no party row" in rank_validate_source:
        raise RuntimeError(
            "baseline_order_visit_keys must not require a party row for every visit."
        )
    if "position_by_visit_key" not in rank_validate_source:
        raise RuntimeError(
            "Established party rank must match baseline_order_visit_keys positions."
        )
    if "is not in baseline_order_visit_keys" not in rank_validate_source:
        raise RuntimeError(
            "Each party VisitKey must be required to appear in baseline_order_visit_keys."
        )
    if "exists" not in write_called or "mkdir" not in write_called or "iterdir" not in write_called:
        raise RuntimeError("Output writing does not refuse an existing directory.")
    trial_dir_guard = False
    for node in ast.walk(write_outputs):
        if isinstance(node, ast.Attribute) and node.attr == "TRIAL_OUTPUT_DIR":
            trial_dir_guard = True
    if trial_dir_guard is not True:
        raise RuntimeError("Diagnostic output is not checked against the trial output.")
    arrival_function = _function_by_name(tree, "_remember_real_world_node_arrival")
    real_world_guard = False
    for node in ast.walk(arrival_function):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.IsNot):
            compared = ast.dump(node)
            if "real_world" in compared:
                real_world_guard = True
    if real_world_guard is not True:
        raise RuntimeError("Actual arrival is not limited to the real World.")
    capture = _function_by_name(tree, "_capture_decision")
    capture_attributes = []
    for node in ast.walk(capture):
        if isinstance(node, ast.Attribute):
            capture_attributes.append(node.attr)
    if "established" not in capture_attributes or "considered" not in capture_attributes:
        raise RuntimeError("Established transactions and considered candidates are not both saved.")
    special = _function_by_name(tree, "_special_transactions")
    for called_name in _call_names(special):
        if called_name in ("clear", "pop", "remove", "unlink"):
            raise RuntimeError("Special extraction changes the saved transactions.")
    main_function = _function_by_name(tree, "main")
    finally_count = 0
    for node in ast.walk(main_function):
        if isinstance(node, ast.Try) and len(node.finalbody) > 0:
            finally_count = finally_count + 1
    if finally_count < 2:
        raise RuntimeError("main() does not restore hooks in finally blocks.")
    main_called = _call_names(main_function)
    if "restore_observation_hooks" not in main_called:
        raise RuntimeError("main() does not restore observation hooks.")
    if "restore_real_world_spillback_observation" not in main_called:
        raise RuntimeError("main() does not restore spillback observation.")
    if "exec_simulation" not in main_called:
        raise RuntimeError("main() does not run one simulation.")
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
                continue
            if child.func.attr == "write_text" and node.name != "_write_outputs":
                raise RuntimeError("A file write is outside the diagnostic output writer.")
            if child.func.attr == "mkdir" and node.name != "_write_outputs":
                raise RuntimeError("A directory is created outside the diagnostic output writer.")
            if child.func.attr == "open" and node.name != "_write_csv":
                raise RuntimeError("A file is opened outside the diagnostic CSV writer.")
    print("static contract ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
    else:
        raise SystemExit(main())
