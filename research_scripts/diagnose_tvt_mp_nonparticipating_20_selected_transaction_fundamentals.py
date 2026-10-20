"""
Read-only fundamentals for selected established TVT-MP transactions.

Replays the nonparticipating-20 two-cross trial once. Established
transactions are kept when nonparticipating_count >= 1, or buyer_count
>= 2, or seller_count >= 2. One transaction is stored once. Every
trade-scope role of a selected transaction is written.

Local ranks are read from the saved driver result at that decision.
They are not reconstructed from an existing CSV row order.

- baseline_local_rank is the 1-based position in the saved
  candidate_visits order. That order is not sorted again.
- post_trade_local_rank is OrderControlTvtMpGeneralTradeRankResult
  .assigned_rank for the same candidate Visit set.
- assigned_rank is the real-world OrderControlTvtNodeRankState
  passage-attempt priority. It is not a candidate passage time.
- actual_node_passage_rank comes from the real-world actual node
  passage history. Unobserved visits stay blank.

binding_sequence_auxiliary_rank is only the binding-sequence position.
It is not used as any of the four ranks above.

Baseline arrival comes from the same decision's baseline collector.
Actual arrival is recorded by a read-only hook on the real World only.
Baseline, candidate, and actual passage times stay in separate fields.
An unobserved actual passage is not filled from the candidate passage.
"""

from __future__ import annotations

import ast
import csv
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
    OrderControlTvtMpCandidateTrafficObservationRecord,
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

import run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_nonparticipating_20_trial as nonparticipating_trial


SCENARIO_NAME = nonparticipating_trial.SCENARIO_NAME
TRIAL_SCRIPT_NAME = (
    "run_tvt_mp_two_cross_intersections_downstream_spillback_"
    "extended_south_pulse_nonparticipating_20_trial.py"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_seed_1_nonparticipation_seed_3_"
        "selected_transaction_fundamentals_diagnostic"
    )
)
SUMMARY_CSV_NAME = "selected_transaction_fundamentals_summary.csv"
PARTIES_CSV_NAME = "selected_transaction_fundamentals_parties.csv"
OUTPUT_FILE_NAMES = (SUMMARY_CSV_NAME, PARTIES_CSV_NAME)

PAYMENT_BALANCE_REL_TOL = 1e-12
PAYMENT_BALANCE_ABS_TOL = 1e-12

# Counts below are the established-transaction rows already written by the
# completed trial. They are not ranks, and they are not guessed. Runtime
# still rebuilds the selection from the driver result and must match them.
EXPECTED_SELECTED_TRANSACTION_COUNT = 63
EXPECTED_SELECTED_PARTY_VISIT_COUNT = 233
EXPECTED_SELECTED_BUYER_VISIT_COUNT = 83
EXPECTED_SELECTED_SELLER_VISIT_COUNT = 126
EXPECTED_SELECTED_NONPARTICIPATING_VISIT_COUNT = 24
EXPECTED_NONPARTICIPATING_TRANSACTION_COUNT = 21
EXPECTED_MULTIPLE_BUYER_TRANSACTION_COUNT = 19
EXPECTED_MULTIPLE_SELLER_TRANSACTION_COUNT = 44
EXPECTED_ONLY_NONPARTICIPATING_TRANSACTION_COUNT = 7
EXPECTED_ONLY_MULTIPLE_BUYER_TRANSACTION_COUNT = 8
EXPECTED_ONLY_MULTIPLE_SELLER_TRANSACTION_COUNT = 27
EXPECTED_NONPARTICIPATING_AND_MULTIPLE_BUYER_COUNT = 4
EXPECTED_NONPARTICIPATING_AND_MULTIPLE_SELLER_COUNT = 10
EXPECTED_MULTIPLE_BUYER_AND_SELLER_COUNT = 7
EXPECTED_ALL_THREE_REASONS_COUNT = 0

REASON_NONPARTICIPATING = "nonparticipating_present"
REASON_MULTIPLE_BUYERS = "multiple_buyers"
REASON_MULTIPLE_SELLERS = "multiple_sellers"

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
    "formal_route_next_link_name",
    "predicted_route_next_link_name",
    "actual_route_next_link_name",
    "selected_because_nonparticipating_present",
    "selected_because_multiple_buyers",
    "selected_because_multiple_sellers",
    "selection_reasons",
    "baseline_arrival_timestep",
    "actual_arrival_timestep",
    "baseline_minus_actual_arrival_timesteps",
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


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_run_tvt_mp_driver = None
        self.original_record_order_control_node_arrival = None
        self.selected: list[dict] = []
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
    return "|".join(_visit_text(visit_key) for visit_key in visit_keys)


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


def _is_numeric_zero(value) -> bool:
    if type(value) is bool or type(value) not in (int, float):
        return False
    return value == 0


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
    """Keep the raw payment fields separate from the effective transfer.

    A missing nonparticipating record stays None on the raw field. The
    effective amount is the explicit number 0 because that visit is outside
    the payment transaction. An unexpected record does not become 0.
    """
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
        or (payment_status == RECORD_PRESENT and official_payment is None)
        or (compensation_status == RECORD_PRESENT and official_compensation is None)
    ):
        participation = MONETARY_UNEXPECTED
        if payment_status != RECORD_PRESENT:
            if payment_status != RECORD_ABSENT_NOT_APPLICABLE:
                effective_payment = None
        elif official_payment is None:
            effective_payment = None
        if compensation_status != RECORD_PRESENT:
            if compensation_status != RECORD_ABSENT_NOT_APPLICABLE:
                effective_compensation = None
        elif official_compensation is None:
            effective_compensation = None
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
    """Raw reference amounts stay unchanged. Status names the formal scope."""
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


def selection_flags(buyer_count: int, seller_count: int, nonparticipating_count: int) -> dict:
    """One established transaction matches if any count condition holds."""
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
        "selected": len(reasons) > 0,
        "selected_because_nonparticipating_present": because_nonparticipating,
        "selected_because_multiple_buyers": because_multiple_buyers,
        "selected_because_multiple_sellers": because_multiple_sellers,
        "selection_reasons": "|".join(reasons),
    }


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
        "final_rank_nodes": final_rank_set.node_final_rank_results,
        "payment_nodes": payment_set.node_payment_and_compensation_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
    }


def _baseline_local_ranks(candidate_visits, node_name: str, timestep: int):
    """1-based ranks in the saved candidate_visits order. No re-sort."""
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
    """assigned_rank from the selected general trade rank result."""
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
            f"{_decision_label(node_name, timestep)} post_trade_local_rank "
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
                "results share the selected buyers."
            )
        found = trade_result
    if found is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: no general trade rank result "
            "matches the selected buyers."
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


def _infeasibility_text(reasons) -> str:
    values = []
    for reason in reasons:
        values.append(reason.value)
    return "|".join(values)


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


def _is_finite_transaction_total(value) -> bool:
    if type(value) is bool or type(value) not in (int, float):
        return False
    return math.isfinite(value)


def _payment_balance_satisfied(
    total_official_payment,
    total_official_compensation,
) -> bool:
    """True only when both totals are finite and within tolerance.

    The raw payment_balance_difference is stored separately and is not
    rounded to zero for this check.
    """
    if not _is_finite_transaction_total(total_official_payment):
        return False
    if not _is_finite_transaction_total(total_official_compensation):
        return False
    return math.isclose(
        total_official_payment,
        total_official_compensation,
        rel_tol=PAYMENT_BALANCE_REL_TOL,
        abs_tol=PAYMENT_BALANCE_ABS_TOL,
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


def _capture_selected_node(world, columns, node_name: str, timestep: int) -> dict | None:
    payment_node = _require_one(
        columns["payment_nodes"], node_name, timestep, "payment_and_compensation"
    )
    selection_node = _require_one(
        columns["selection_nodes"], node_name, timestep, "candidate_selection"
    )
    final_rank_node = _require_one(
        columns["final_rank_nodes"], node_name, timestep, "final_rank"
    )
    economic_node = _require_one(
        columns["economic_nodes"], node_name, timestep, "economic_evaluation"
    )
    trade_rank_node = _require_one(
        columns["trade_rank_nodes"], node_name, timestep, "general_trade_rank"
    )
    candidate_visit_node = _require_one(
        columns["candidate_visit_nodes"], node_name, timestep, "candidate_visit_set"
    )
    right_of_entry_node = _require_one(
        columns["right_of_entry_nodes"], node_name, timestep, "right_of_entry"
    )
    if not isinstance(candidate_visit_node, OrderControlTvtNodeCandidateVisitSetResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: candidate visit node is "
            f"{type(candidate_visit_node).__name__}."
        )
    if not isinstance(right_of_entry_node, OrderControlTvtNodeRightOfEntrySelectionResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry node is "
            f"{type(right_of_entry_node).__name__}."
        )
    selected = payment_node.selected_candidate_economic_result
    if selected is None:
        if selection_node.selected_candidate_economic_result is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selection has a candidate "
                "while payment does not."
            )
        if final_rank_node.selected_candidate_economic_result is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: final rank has a candidate "
                "while payment does not."
            )
        return None
    if not isinstance(selected, OrderControlTvtMpCandidateEconomicEvaluationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result is "
            f"{type(selected).__name__}."
        )
    if selection_node.selected_candidate_economic_result is not selected:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selection and payment do not "
            "share the selected economic result."
        )
    if final_rank_node.selected_candidate_economic_result is not selected:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: final rank and payment do not "
            "share the selected economic result."
        )
    economic_identity_found = False
    for economic_result in economic_node.candidate_economic_evaluation_results:
        if economic_result is selected:
            economic_identity_found = True
    if economic_identity_found is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result is "
            "not in the node economic results."
        )
    local_result = selected.candidate_local_virtual_calculation_result
    if local_result.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local result belongs "
            f"to {local_result.node_name!r}."
        )
    if local_result.baseline_timestep_T != timestep:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local "
            "baseline_timestep_T does not match the decision."
        )
    if world.T != timestep:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: World.T is {world.T!r}."
        )
    buyers_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    trade_result = _matching_trade_result(
        trade_rank_node, buyers_sorted, node_name, timestep
    )
    if tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted) != buyers_sorted:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade result buyers changed."
        )
    sellers_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.sellers_sorted
    )
    nonparticipating_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in trade_result.nonparticipating_visits_sorted
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
    flags = selection_flags(
        len(buyers_sorted), len(sellers_sorted), len(nonparticipating_sorted)
    )
    if flags["selected"] is not True:
        return None
    ordered_visit_keys, baseline_ranks = _baseline_local_ranks(
        candidate_visit_node.candidate_visits, node_name, timestep
    )
    post_trade_ranks = _post_trade_local_ranks(
        trade_result, ordered_visit_keys, node_name, timestep
    )
    if set(baseline_ranks) != set(post_trade_ranks):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: baseline_local_rank and "
            "post_trade_local_rank do not share the saved candidate_visits."
        )
    candidate_order = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.trade_order
    )
    if tuple(candidate_order) != tuple(ordered_visit_keys) and set(candidate_order) != set(ordered_visit_keys):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: trade_order VisitKeys differ "
            "from saved candidate_visits."
        )
    buyer_economics = _records_by_visit_key(
        selected.buyer_economic_records, node_name, timestep, "buyer_economic_records"
    )
    seller_economics = _records_by_visit_key(
        selected.seller_economic_records, node_name, timestep, "seller_economic_records"
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
    if right_of_entry_node.right_of_entry_visit_key is None:
        right_of_entry_key = None
    else:
        right_of_entry_key = _plain_visit_key(right_of_entry_node.right_of_entry_visit_key)
    collector = columns["collector"]
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
                "is missing a local rank."
            )
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
        baseline_arrival = snapshot["baseline_arrival_timestep"]
        if type(baseline_arrival) is not int:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: baseline_arrival_timestep "
                f"for {_visit_text(visit_key)} is {baseline_arrival!r}."
            )
        baseline_passage = traffic_record.baseline_passage_timestep
        candidate_passage = traffic_record.candidate_passage_timestep
        if type(baseline_passage) is not int and baseline_passage is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: baseline passage for "
                f"{_visit_text(visit_key)} is {baseline_passage!r}."
            )
        if type(candidate_passage) is not int and candidate_passage is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate passage for "
                f"{_visit_text(visit_key)} is {candidate_passage!r}."
            )
        predicted_status = traffic_record.passage_observation_status
        if predicted_status is None:
            predicted_status_text = None
        else:
            predicted_status_text = predicted_status.value
        vehicle = world.VEHICLES[visit_key[0]]
        participates = vehicle.participates_in_order_exchange
        if type(participates) is not bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: participates_in_order_exchange "
                f"for {_visit_text(visit_key)} is {participates!r}."
            )
        declared_vot = vehicle.vot_declared
        true_vot = traffic_record.true_vot_per_second
        if type(true_vot) not in (int, float) or type(true_vot) is bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: true_vot_per_second for "
                f"{_visit_text(visit_key)} is {true_vot!r}."
            )
        buyer_record = buyer_economics.get(visit_key)
        seller_record = seller_economics.get(visit_key)
        expected_time_saving = None
        expected_waiting_increase = None
        gross_time_value = None
        required_compensation = None
        passes_positive = None
        individual_status = None
        payment_record = payments.get(visit_key)
        compensation_record = compensations.get(visit_key)
        if role_name == "buyer":
            if not isinstance(buyer_record, OrderControlTvtMpBuyerEconomicRecord):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer "
                    f"{_visit_text(visit_key)} has no buyer economic record."
                )
            expected_time_saving = buyer_record.expected_time_saving_timesteps
            gross_time_value = buyer_record.gross_time_value_G_b
            passes_positive = buyer_record.passes_positive_buyer_value_condition
            if passes_positive is True:
                individual_status = "passes_positive_buyer_value_condition"
            elif passes_positive is False:
                individual_status = "fails_positive_buyer_value_condition"
            else:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    "passes_positive_buyer_value_condition is "
                    f"{passes_positive!r}."
                )
        elif role_name == "seller":
            if not isinstance(seller_record, OrderControlTvtMpSellerEconomicRecord):
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller "
                    f"{_visit_text(visit_key)} has no seller economic record."
                )
            expected_waiting_increase = seller_record.expected_waiting_increase_timesteps
            required_compensation = seller_record.required_compensation_R_s
        elif role_name == "nonparticipating":
            if buyer_record is not None or seller_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: nonparticipating "
                    f"{_visit_text(visit_key)} has a buyer or seller economic record."
                )
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
        predicted_signed = _subtract_ints(baseline_passage, candidate_passage)
        if role_name == "nonparticipating":
            stored_predicted = traffic_record.predicted_time_difference_timesteps
            if stored_predicted != predicted_signed:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    "predicted_time_difference_timesteps for "
                    f"{_visit_text(visit_key)} is {stored_predicted!r}, while "
                    f"baseline passage minus candidate passage is {predicted_signed!r}."
                )
            predicted_external = traffic_record.predicted_signed_time_value_change
            predicted_signed_for_row = predicted_signed
        else:
            predicted_external = None
            predicted_signed_for_row = None
        baseline_local_rank = baseline_ranks[visit_key]
        post_trade_local_rank = post_trade_ranks[visit_key]
        parties.append(
            {
                "visit_key": visit_key,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "role": role_name,
                "participates_in_order_exchange": participates,
                "is_right_of_entry_holder": visit_key == right_of_entry_key,
                "inlink_name": traffic_record.inlink_name,
                "predicted_route_next_link_name": traffic_record.route_next_link_name,
                "formal_route_next_link_name": None,
                "actual_route_next_link_name": None,
                "baseline_arrival_timestep": baseline_arrival,
                "actual_arrival_timestep": None,
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_passage,
                "actual_passage_timestep": None,
                "predicted_observation_status": predicted_status_text,
                "actual_observation_status": None,
                "baseline_local_rank": baseline_local_rank,
                "post_trade_local_rank": post_trade_local_rank,
                "assigned_rank": None,
                "actual_node_passage_rank": None,
                "binding_sequence_auxiliary_rank": traffic_record.binding_rank,
                "true_vot_per_second": true_vot,
                "declared_vot_per_second": declared_vot,
                "passes_positive_buyer_value_condition": passes_positive,
                "individual_economic_condition_status": individual_status,
                "individual_economic_condition_reason": None,
                "expected_time_saving_timesteps": expected_time_saving,
                "expected_waiting_increase_timesteps": expected_waiting_increase,
                "gross_time_value_G_b": gross_time_value,
                "required_compensation_R_s": required_compensation,
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
    payment_balance_difference = total_official_payment - total_official_compensation
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
        "candidate_identity": f"{node_name}|{_join_visit_keys(buyers_sorted)}",
        "buyers_sorted": buyers_sorted,
        "sellers_sorted": sellers_sorted,
        "nonparticipating_visits_sorted": nonparticipating_sorted,
        "right_of_entry_visit_key": right_of_entry_key,
        "buyer_count": len(buyers_sorted),
        "seller_count": len(sellers_sorted),
        "nonparticipating_count": len(nonparticipating_sorted),
        "trade_scope_count": len(trade_scope),
        "selected_because_nonparticipating_present": flags[
            "selected_because_nonparticipating_present"
        ],
        "selected_because_multiple_buyers": flags["selected_because_multiple_buyers"],
        "selected_because_multiple_sellers": flags["selected_because_multiple_sellers"],
        "selection_reasons": flags["selection_reasons"],
        "baseline_order_visit_keys": ordered_visit_keys,
        "candidate_order_visit_keys": candidate_order,
        "nonparticipating_baseline_candidate_rank_all_equal": rank_equal,
        "economically_feasible": selected.economically_feasible,
        "candidate_infeasibility_reasons": _infeasibility_text(selected.infeasibility_reasons),
        "total_G": selected.total_buyer_value_G,
        "total_R": selected.total_required_compensation_R,
        "surplus": selected.surplus,
        "total_official_payment": total_official_payment,
        "total_official_compensation": total_official_compensation,
        "payment_balance_difference": payment_balance_difference,
        "payment_balance_satisfied": _payment_balance_satisfied(
            total_official_payment,
            total_official_compensation,
        ),
        "actual_evaluation_available": None,
        "trade_ex_post_evaluation_status": None,
        "parties": parties,
    }


def _extract_selected_transactions(world, result) -> list[dict]:
    timestep = world.T
    if type(timestep) is not int:
        raise RuntimeError(f"Driver World.T is not an int: {timestep!r}.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={timestep}: driver result is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        return []
    columns = _saved_driver_columns(atomic)
    extracted = []
    seen_nodes = []
    for payment_node in columns["payment_nodes"]:
        node_name = payment_node.node_name
        if node_name in seen_nodes:
            raise RuntimeError(f"T={timestep}: payment results repeat {node_name}.")
        seen_nodes.append(node_name)
        captured = _capture_selected_node(world, columns, node_name, timestep)
        if captured is not None:
            extracted.append(captured)
    return extracted


def wrapped_run_tvt_mp_driver(world):
    result = GATE.original_run_tvt_mp_driver(world)
    if world is not GATE.real_world:
        return result
    extracted = _extract_selected_transactions(world, result)
    GATE.selected.extend(extracted)
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
    for transaction in GATE.selected:
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
            if arrival_key in GATE.actual_node_arrivals:
                party["actual_arrival_timestep"] = GATE.actual_node_arrivals[arrival_key]
            assigned_rank = rank_state.assigned_rank(visit_key)
            if type(assigned_rank) is int:
                party["assigned_rank"] = assigned_rank
            elif assigned_rank is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: assigned_rank for "
                    f"{_visit_text(visit_key)} is {assigned_rank!r}."
                )
            formal_route = rank_state.formal_route_next_link_name(visit_key)
            party["formal_route_next_link_name"] = formal_route
            passage_record = node_history.get(visit_key)
            if passage_record is not None:
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
                    f"for {_visit_text(visit_key)} differs from the traffic observation."
                )
            if research_visit.candidate_passage_timestep != party["candidate_passage_timestep"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research candidate passage "
                    f"for {_visit_text(visit_key)} differs from the traffic observation."
                )
            if research_visit.actual_passage_timestep != party["actual_passage_timestep"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research actual passage "
                    f"for {_visit_text(visit_key)} differs from the passage history."
                )
            if research_visit.assigned_rank != party["assigned_rank"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research assigned_rank "
                    f"for {_visit_text(visit_key)} differs from the rank state."
                )
            if research_visit.actual_node_passage_rank != party["actual_node_passage_rank"]:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research actual rank for "
                    f"{_visit_text(visit_key)} differs from the passage history."
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
                    f"for {_visit_text(visit_key)} is {research_visit.actual_rank_change!r}, "
                    "while assigned_rank minus actual_node_passage_rank is "
                    f"{computed_rank_change!r}."
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
                if research_visit.official_payment != party["official_payment"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: research official_payment "
                        f"for nonparticipating {_visit_text(visit_key)} differs."
                    )
                if research_visit.official_compensation != party["official_compensation"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: research "
                        "official_compensation for nonparticipating "
                        f"{_visit_text(visit_key)} differs."
                    )
                if research_visit.baseline_minus_candidate_time_value != party["predicted_external_effect_value"]:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: research "
                        "baseline_minus_candidate_time_value for "
                        f"{_visit_text(visit_key)} differs from "
                        "predicted_signed_time_value_change."
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
            party["candidate_infeasibility_reasons"] = transaction["candidate_infeasibility_reasons"]


def _party_row(transaction, party) -> dict:
    baseline_arrival = party["baseline_arrival_timestep"]
    actual_arrival = party["actual_arrival_timestep"]
    baseline_passage = party["baseline_passage_timestep"]
    candidate_passage = party["candidate_passage_timestep"]
    actual_passage = party["actual_passage_timestep"]
    assigned_rank = party["assigned_rank"]
    actual_rank = party["actual_node_passage_rank"]
    row = {
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
        "formal_route_next_link_name": party["formal_route_next_link_name"],
        "predicted_route_next_link_name": party["predicted_route_next_link_name"],
        "actual_route_next_link_name": party["actual_route_next_link_name"],
        "selected_because_nonparticipating_present": transaction[
            "selected_because_nonparticipating_present"
        ],
        "selected_because_multiple_buyers": transaction["selected_because_multiple_buyers"],
        "selected_because_multiple_sellers": transaction["selected_because_multiple_sellers"],
        "selection_reasons": transaction["selection_reasons"],
        "baseline_arrival_timestep": baseline_arrival,
        "actual_arrival_timestep": actual_arrival,
        "baseline_minus_actual_arrival_timesteps": _subtract_ints(
            baseline_arrival, actual_arrival
        ),
        "baseline_passage_timestep": baseline_passage,
        "candidate_passage_timestep": candidate_passage,
        "actual_passage_timestep": actual_passage,
        "baseline_minus_candidate_passage_timesteps": _subtract_ints(
            baseline_passage, candidate_passage
        ),
        "baseline_minus_actual_passage_timesteps": _subtract_ints(
            baseline_passage, actual_passage
        ),
        "candidate_minus_actual_passage_timesteps": _subtract_ints(
            candidate_passage, actual_passage
        ),
        "predicted_observation_status": party["predicted_observation_status"],
        "actual_observation_status": party["actual_observation_status"],
        "baseline_local_rank": party["baseline_local_rank"],
        "post_trade_local_rank": party["post_trade_local_rank"],
        "assigned_rank": assigned_rank,
        "actual_node_passage_rank": actual_rank,
        "binding_sequence_auxiliary_rank": party["binding_sequence_auxiliary_rank"],
        "baseline_minus_candidate_local_rank": _subtract_ints(
            party["baseline_local_rank"], party["post_trade_local_rank"]
        ),
        "assigned_minus_actual_node_rank": _subtract_ints(assigned_rank, actual_rank),
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
    return row


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
    }


def _selection_counts(transactions) -> dict:
    counts = {
        "selected_transaction_count": len(transactions),
        "selected_party_visit_count": 0,
        "selected_buyer_visit_count": 0,
        "selected_seller_visit_count": 0,
        "selected_nonparticipating_visit_count": 0,
        "nonparticipating_transaction_count": 0,
        "multiple_buyer_transaction_count": 0,
        "multiple_seller_transaction_count": 0,
        "only_nonparticipating": 0,
        "only_multiple_buyers": 0,
        "only_multiple_sellers": 0,
        "nonparticipating_and_multiple_buyers": 0,
        "nonparticipating_and_multiple_sellers": 0,
        "multiple_buyers_and_sellers": 0,
        "all_three_reasons": 0,
    }
    seen = set()
    for transaction in transactions:
        key = (
            transaction["tvt_decision_timestep"],
            transaction["node_name"],
            transaction["buyers_sorted"],
        )
        if key in seen:
            raise RuntimeError(f"Selected transaction {key!r} was stored twice.")
        seen.add(key)
        because_nonparticipating = transaction["selected_because_nonparticipating_present"]
        because_buyers = transaction["selected_because_multiple_buyers"]
        because_sellers = transaction["selected_because_multiple_sellers"]
        if because_nonparticipating is True:
            counts["nonparticipating_transaction_count"] += 1
        if because_buyers is True:
            counts["multiple_buyer_transaction_count"] += 1
        if because_sellers is True:
            counts["multiple_seller_transaction_count"] += 1
        reason_count = 0
        if because_nonparticipating is True:
            reason_count = reason_count + 1
        if because_buyers is True:
            reason_count = reason_count + 1
        if because_sellers is True:
            reason_count = reason_count + 1
        if reason_count == 3:
            counts["all_three_reasons"] += 1
        elif because_nonparticipating is True and because_buyers is True:
            counts["nonparticipating_and_multiple_buyers"] += 1
        elif because_nonparticipating is True and because_sellers is True:
            counts["nonparticipating_and_multiple_sellers"] += 1
        elif because_buyers is True and because_sellers is True:
            counts["multiple_buyers_and_sellers"] += 1
        elif because_nonparticipating is True:
            counts["only_nonparticipating"] += 1
        elif because_buyers is True:
            counts["only_multiple_buyers"] += 1
        elif because_sellers is True:
            counts["only_multiple_sellers"] += 1
        for party in transaction["parties"]:
            counts["selected_party_visit_count"] += 1
            if party["role"] == "buyer":
                counts["selected_buyer_visit_count"] += 1
            elif party["role"] == "seller":
                counts["selected_seller_visit_count"] += 1
            elif party["role"] == "nonparticipating":
                counts["selected_nonparticipating_visit_count"] += 1
            else:
                raise RuntimeError(f"Unexpected role {party['role']!r}.")
    return counts


def _require_expected_counts(counts) -> None:
    expected = (
        ("selected_transaction_count", EXPECTED_SELECTED_TRANSACTION_COUNT),
        ("selected_party_visit_count", EXPECTED_SELECTED_PARTY_VISIT_COUNT),
        ("selected_buyer_visit_count", EXPECTED_SELECTED_BUYER_VISIT_COUNT),
        ("selected_seller_visit_count", EXPECTED_SELECTED_SELLER_VISIT_COUNT),
        ("selected_nonparticipating_visit_count", EXPECTED_SELECTED_NONPARTICIPATING_VISIT_COUNT),
        ("nonparticipating_transaction_count", EXPECTED_NONPARTICIPATING_TRANSACTION_COUNT),
        ("multiple_buyer_transaction_count", EXPECTED_MULTIPLE_BUYER_TRANSACTION_COUNT),
        ("multiple_seller_transaction_count", EXPECTED_MULTIPLE_SELLER_TRANSACTION_COUNT),
        ("only_nonparticipating", EXPECTED_ONLY_NONPARTICIPATING_TRANSACTION_COUNT),
        ("only_multiple_buyers", EXPECTED_ONLY_MULTIPLE_BUYER_TRANSACTION_COUNT),
        ("only_multiple_sellers", EXPECTED_ONLY_MULTIPLE_SELLER_TRANSACTION_COUNT),
        ("nonparticipating_and_multiple_buyers", EXPECTED_NONPARTICIPATING_AND_MULTIPLE_BUYER_COUNT),
        ("nonparticipating_and_multiple_sellers", EXPECTED_NONPARTICIPATING_AND_MULTIPLE_SELLER_COUNT),
        ("multiple_buyers_and_sellers", EXPECTED_MULTIPLE_BUYER_AND_SELLER_COUNT),
        ("all_three_reasons", EXPECTED_ALL_THREE_REASONS_COUNT),
    )
    for name, expected_value in expected:
        if counts[name] != expected_value:
            raise RuntimeError(
                f"{name} is {counts[name]}, expected {expected_value} from the "
                "existing established-transaction CSV."
            )


def _nonparticipating_rank_failures(transactions) -> list[str]:
    failures = []
    for transaction in transactions:
        for party in transaction["parties"]:
            if party["role"] != "nonparticipating":
                continue
            if party["baseline_local_rank"] == party["post_trade_local_rank"]:
                continue
            failures.append(
                "\n".join(
                    (
                        f"decision T={transaction['tvt_decision_timestep']}",
                        f"Node={transaction['node_name']}",
                        f"VisitKey={_visit_text(party['visit_key'])}",
                        f"baseline_local_rank={party['baseline_local_rank']}",
                        f"post_trade_local_rank={party['post_trade_local_rank']}",
                        "baseline_order_visit_keys="
                        + _join_visit_keys(transaction["baseline_order_visit_keys"]),
                        "candidate_order_visit_keys="
                        + _join_visit_keys(transaction["candidate_order_visit_keys"]),
                        "buyers_sorted=" + _join_visit_keys(transaction["buyers_sorted"]),
                        "sellers_sorted=" + _join_visit_keys(transaction["sellers_sorted"]),
                        "nonparticipating_visits_sorted="
                        + _join_visit_keys(transaction["nonparticipating_visits_sorted"]),
                    )
                )
            )
    return failures


def _nonparticipating_payment_failures(transactions) -> list[str]:
    """Raw official amounts stay None. Effective transfer amounts are 0.

    Absence of a payment or compensation record is the production exclusion.
    A record on a nonparticipating visit is a failure, and its raw amount is
    not rewritten to 0.
    """
    failures = []
    for transaction in transactions:
        for party in transaction["parties"]:
            if party["role"] != "nonparticipating":
                continue
            label = (
                f"T={transaction['tvt_decision_timestep']} {transaction['node_name']} "
                f"{_visit_text(party['visit_key'])}"
            )
            if party["participates_in_order_exchange"] is not False:
                failures.append(
                    f"{label}: participates_in_order_exchange is "
                    f"{party['participates_in_order_exchange']!r}."
                )
            if party["declared_vot_per_second"] is not None:
                failures.append(
                    f"{label}: declared_vot_per_second is {party['declared_vot_per_second']!r}."
                )
            if party["true_vot_per_second"] is None:
                failures.append(f"{label}: true_vot_per_second is missing.")
            if party["monetary_transfer_participation_status"] != MONETARY_EXCLUDED_NONPARTICIPATING:
                failures.append(
                    f"{label}: monetary_transfer_participation_status is "
                    f"{party['monetary_transfer_participation_status']!r}."
                )
            if party["payment_record_status"] != RECORD_ABSENT_NOT_APPLICABLE:
                failures.append(
                    f"{label}: payment_record_status is {party['payment_record_status']!r}."
                )
            if party["compensation_record_status"] != RECORD_ABSENT_NOT_APPLICABLE:
                failures.append(
                    f"{label}: compensation_record_status is "
                    f"{party['compensation_record_status']!r}."
                )
            if party["official_payment"] is not None:
                failures.append(
                    f"{label}: official_payment raw value is {party['official_payment']!r}."
                )
            if party["official_compensation"] is not None:
                failures.append(
                    f"{label}: official_compensation raw value is "
                    f"{party['official_compensation']!r}."
                )
            if _is_numeric_zero(party["effective_payment_amount"]) is not True:
                failures.append(
                    f"{label}: effective_payment_amount is "
                    f"{party['effective_payment_amount']!r}."
                )
            if _is_numeric_zero(party["effective_compensation_amount"]) is not True:
                failures.append(
                    f"{label}: effective_compensation_amount is "
                    f"{party['effective_compensation_amount']!r}."
                )
            if party["reference_payment"] is not None:
                failures.append(
                    f"{label}: reference_payment raw value is {party['reference_payment']!r}."
                )
            if party["reference_compensation"] is not None:
                failures.append(
                    f"{label}: reference_compensation raw value is "
                    f"{party['reference_compensation']!r}."
                )
            if party["reference_payment_status"] != RECORD_ABSENT_NOT_APPLICABLE:
                failures.append(
                    f"{label}: reference_payment_status is "
                    f"{party['reference_payment_status']!r}."
                )
            if party["reference_compensation_status"] != RECORD_ABSENT_NOT_APPLICABLE:
                failures.append(
                    f"{label}: reference_compensation_status is "
                    f"{party['reference_compensation_status']!r}."
                )
    return failures


def _participating_record_failures(transactions) -> list[str]:
    """Buyer and seller formal records stay on their own production amounts."""
    failures = []
    for transaction in transactions:
        for party in transaction["parties"]:
            if party["role"] == "nonparticipating":
                continue
            if party["monetary_transfer_participation_status"] == MONETARY_UNEXPECTED:
                label = (
                    f"T={transaction['tvt_decision_timestep']} {transaction['node_name']} "
                    f"{_visit_text(party['visit_key'])}"
                )
                failures.append(
                    f"{label}: monetary_transfer_participation_status is "
                    f"{party['monetary_transfer_participation_status']!r}, "
                    f"payment_record_status={party['payment_record_status']!r}, "
                    f"compensation_record_status={party['compensation_record_status']!r}."
                )
    return failures


def _diagnostic_counts(transactions) -> dict:
    counts = _selection_counts(transactions)
    counts["nonparticipating_rank_equal"] = 0
    counts["nonparticipating_rank_unequal"] = 0
    counts["payment_record_absent_not_applicable"] = 0
    counts["compensation_record_absent_not_applicable"] = 0
    counts["effective_payment_zero"] = 0
    counts["effective_compensation_zero"] = 0
    counts["unexpected_payment_record"] = 0
    counts["unexpected_compensation_record"] = 0
    counts["participating_false"] = 0
    counts["declared_vot_none"] = 0
    counts["passage_both_observed"] = 0
    counts["passage_equal"] = 0
    counts["passage_unequal"] = 0
    counts["passage_actual_unobserved"] = 0
    counts["node_rank_both_observed"] = 0
    counts["node_rank_equal"] = 0
    counts["node_rank_unequal"] = 0
    counts["payment_balance_satisfied"] = 0
    counts["payment_balance_unsatisfied"] = 0
    counts["payment_balance_max_abs_difference"] = 0.0
    counts["economic_fit"] = 0
    counts["economic_unfit"] = 0
    counts["economic_out_of_scope"] = 0
    counts["economic_unobserved"] = 0
    node_rank_mismatches = []
    for transaction in transactions:
        if transaction["payment_balance_satisfied"] is True:
            counts["payment_balance_satisfied"] += 1
        else:
            counts["payment_balance_unsatisfied"] += 1
        difference = transaction["payment_balance_difference"]
        if _is_finite_transaction_total(difference):
            abs_difference = abs(difference)
            if abs_difference > counts["payment_balance_max_abs_difference"]:
                counts["payment_balance_max_abs_difference"] = abs_difference
        for party in transaction["parties"]:
            if party["role"] == "nonparticipating":
                if party["baseline_local_rank"] == party["post_trade_local_rank"]:
                    counts["nonparticipating_rank_equal"] += 1
                else:
                    counts["nonparticipating_rank_unequal"] += 1
                if party["payment_record_status"] == RECORD_ABSENT_NOT_APPLICABLE:
                    counts["payment_record_absent_not_applicable"] += 1
                elif (
                    party["payment_record_status"] == RECORD_UNEXPECTED_PRESENT
                    or party["payment_record_status"] == RECORD_UNEXPECTED_MISSING
                ):
                    counts["unexpected_payment_record"] += 1
                if party["compensation_record_status"] == RECORD_ABSENT_NOT_APPLICABLE:
                    counts["compensation_record_absent_not_applicable"] += 1
                elif (
                    party["compensation_record_status"] == RECORD_UNEXPECTED_PRESENT
                    or party["compensation_record_status"] == RECORD_UNEXPECTED_MISSING
                ):
                    counts["unexpected_compensation_record"] += 1
                if _is_numeric_zero(party["effective_payment_amount"]) is True:
                    counts["effective_payment_zero"] += 1
                if _is_numeric_zero(party["effective_compensation_amount"]) is True:
                    counts["effective_compensation_zero"] += 1
                if party["participates_in_order_exchange"] is False:
                    counts["participating_false"] += 1
                if party["declared_vot_per_second"] is None:
                    counts["declared_vot_none"] += 1
            if party["candidate_passage_timestep"] is not None and party["actual_passage_timestep"] is not None:
                counts["passage_both_observed"] += 1
                if party["candidate_passage_timestep"] == party["actual_passage_timestep"]:
                    counts["passage_equal"] += 1
                else:
                    counts["passage_unequal"] += 1
            elif party["actual_passage_timestep"] is None:
                counts["passage_actual_unobserved"] += 1
            if party["assigned_rank"] is not None and party["actual_node_passage_rank"] is not None:
                counts["node_rank_both_observed"] += 1
                if party["assigned_rank"] == party["actual_node_passage_rank"]:
                    counts["node_rank_equal"] += 1
                else:
                    counts["node_rank_unequal"] += 1
                    if party["role"] == "nonparticipating":
                        node_rank_mismatches.append(party)
            status = party["individual_economic_condition_status"]
            if status == "passes_positive_buyer_value_condition":
                counts["economic_fit"] += 1
            elif status == "fails_positive_buyer_value_condition":
                counts["economic_unfit"] += 1
            elif status is None:
                counts["economic_out_of_scope"] += 1
            else:
                counts["economic_unobserved"] += 1
    counts["node_rank_mismatches"] = node_rank_mismatches
    return counts


def _print_summary(counts) -> None:
    print(f"selected transaction count: {counts['selected_transaction_count']}")
    print(f"selected party Visit count: {counts['selected_party_visit_count']}")
    print(f"selected buyer Visit count: {counts['selected_buyer_visit_count']}")
    print(f"selected seller Visit count: {counts['selected_seller_visit_count']}")
    print(
        "selected nonparticipating Visit count: "
        f"{counts['selected_nonparticipating_visit_count']}"
    )
    print(
        "transactions containing nonparticipating: "
        f"{counts['nonparticipating_transaction_count']}"
    )
    print(f"multiple buyer transactions: {counts['multiple_buyer_transaction_count']}")
    print(f"multiple seller transactions: {counts['multiple_seller_transaction_count']}")
    print(
        "nonparticipating baseline/local Candidate rank equal: "
        f"{counts['nonparticipating_rank_equal']}"
    )
    print(
        "nonparticipating baseline/local Candidate rank unequal: "
        f"{counts['nonparticipating_rank_unequal']}"
    )
    print(
        "nonparticipating payment record absent_not_applicable: "
        f"{counts['payment_record_absent_not_applicable']}"
    )
    print(
        "nonparticipating compensation record absent_not_applicable: "
        f"{counts['compensation_record_absent_not_applicable']}"
    )
    print(
        "nonparticipating effective payment amount = 0: "
        f"{counts['effective_payment_zero']}"
    )
    print(
        "nonparticipating effective compensation amount = 0: "
        f"{counts['effective_compensation_zero']}"
    )
    print(
        "nonparticipating unexpected payment record: "
        f"{counts['unexpected_payment_record']}"
    )
    print(
        "nonparticipating unexpected compensation record: "
        f"{counts['unexpected_compensation_record']}"
    )
    print(f"nonparticipating participating = False: {counts['participating_false']}")
    print(f"nonparticipating declared VOT = None: {counts['declared_vot_none']}")
    print(f"Candidate P and Actual P both observed: {counts['passage_both_observed']}")
    print(f"Candidate P = Actual P: {counts['passage_equal']}")
    print(f"Candidate P != Actual P: {counts['passage_unequal']}")
    print(f"Actual P unobserved: {counts['passage_actual_unobserved']}")
    print(
        "assigned rank and actual rank both observed: "
        f"{counts['node_rank_both_observed']}"
    )
    print(f"assigned rank = actual rank: {counts['node_rank_equal']}")
    print(f"assigned rank != actual rank: {counts['node_rank_unequal']}")
    print(f"payment balance satisfied transactions: {counts['payment_balance_satisfied']}")
    print(
        "payment balance unsatisfied transactions: "
        f"{counts['payment_balance_unsatisfied']}"
    )
    print(
        "payment balance maximum absolute difference: "
        f"{counts['payment_balance_max_abs_difference']}"
    )
    print(f"payment balance relative tolerance: {PAYMENT_BALANCE_REL_TOL}")
    print(f"payment balance absolute tolerance: {PAYMENT_BALANCE_ABS_TOL}")
    print(f"economic condition fit: {counts['economic_fit']}")
    print(f"economic condition unfit: {counts['economic_unfit']}")
    print(f"economic condition out of scope: {counts['economic_out_of_scope']}")
    print(f"economic condition unobserved: {counts['economic_unobserved']}")
    if counts["node_rank_unequal"] > 0:
        print(
            "assigned rank differs from actual rank for "
            f"{counts['node_rank_unequal']} visits. "
            "This is reported and is not classified as a production defect."
        )


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row[column]) for column in columns})


def _write_outputs(transactions) -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    if OUTPUT_DIR == nonparticipating_trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory is the trial output directory.")
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    summary_rows = [_summary_row(transaction) for transaction in transactions]
    party_rows = []
    for transaction in transactions:
        for party in transaction["parties"]:
            party_rows.append(_party_row(transaction, party))
    _write_csv(OUTPUT_DIR / SUMMARY_CSV_NAME, SUMMARY_COLUMNS, summary_rows)
    _write_csv(OUTPUT_DIR / PARTIES_CSV_NAME, PARTY_COLUMNS, party_rows)
    expected_names = set(OUTPUT_FILE_NAMES)
    for path in OUTPUT_DIR.iterdir():
        if path.name not in expected_names:
            raise RuntimeError(f"Unexpected file in output directory: {path.name}.")


def _prepare_trial_world():
    reference = nonparticipating_trial.reference
    reference.SPILLBACK_TIMESTEP_ROWS.clear()
    vot_values = nonparticipating_trial._true_vot_sequence()
    vot_records = reference.build_vehicle_vot_records(
        nonparticipating_trial.VEHICLE_SPECS,
        vot_values,
    )
    world = nonparticipating_trial.build_world()
    reference.add_vehicles_to_world(
        world,
        nonparticipating_trial.VEHICLE_SPECS,
        vot_records,
    )
    world.finalize_scenario()
    if world.TSIZE != reference.INTERNAL_TSIZE:
        raise RuntimeError(f"Expected TSIZE=={reference.INTERNAL_TSIZE}, got {world.TSIZE}.")
    if world.name != nonparticipating_trial.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name was not kept.")
    return world


def main() -> int:
    reference = nonparticipating_trial.reference
    original_python_recursion_limit = sys.getrecursionlimit()
    GATE.selected.clear()
    GATE.actual_node_arrivals.clear()
    try:
        if original_python_recursion_limit < reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_trial_world()
        install_observation_hooks(world)
        reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            reference.restore_real_world_spillback_observation()
            restore_observation_hooks()
        evaluation = reference.verify_evaluation_end(world)
        if evaluation["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")
        nonparticipating_trial.verify_world_participation(world)
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        _attach_actual_and_research(world, bundle)
        counts = _diagnostic_counts(GATE.selected)
        _require_expected_counts(counts)
        _print_summary(counts)
        rank_failures = _nonparticipating_rank_failures(GATE.selected)
        if len(rank_failures) > 0:
            raise RuntimeError(
                "Nonparticipating local rank protection failed:\n" + "\n".join(rank_failures)
            )
        payment_failures = _nonparticipating_payment_failures(GATE.selected)
        if len(payment_failures) > 0:
            raise RuntimeError(
                "Nonparticipating payment exclusion failed:\n" + "\n".join(payment_failures)
            )
        record_failures = _participating_record_failures(GATE.selected)
        if len(record_failures) > 0:
            raise RuntimeError(
                "Buyer or seller payment record check failed:\n" + "\n".join(record_failures)
            )
        _write_outputs(GATE.selected)
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        reference.restore_real_world_spillback_observation()
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
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def validate_static_contract() -> None:
    if SCENARIO_NAME != (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20_trial"
    ):
        raise RuntimeError("Scenario name does not match the nonparticipating trial.")
    if TRIAL_SCRIPT_NAME != (
        "run_tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20_trial.py"
    ):
        raise RuntimeError("Trial script name does not match.")
    if not (SCRIPT_DIR / TRIAL_SCRIPT_NAME).is_file():
        raise RuntimeError("Target trial script is missing.")
    if OUTPUT_DIR.name != (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_seed_1_nonparticipation_seed_3_"
        "selected_transaction_fundamentals_diagnostic"
    ):
        raise RuntimeError("Output directory name does not match.")
    if SUMMARY_CSV_NAME != "selected_transaction_fundamentals_summary.csv":
        raise RuntimeError("Summary CSV name does not match.")
    if PARTIES_CSV_NAME != "selected_transaction_fundamentals_parties.csv":
        raise RuntimeError("Parties CSV name does not match.")
    if EXPECTED_SELECTED_TRANSACTION_COUNT != 63:
        raise RuntimeError("Selected transaction count constant changed.")
    if EXPECTED_SELECTED_PARTY_VISIT_COUNT != 233:
        raise RuntimeError("Selected party count constant changed.")
    if EXPECTED_SELECTED_BUYER_VISIT_COUNT != 83:
        raise RuntimeError("Selected buyer count constant changed.")
    if EXPECTED_SELECTED_SELLER_VISIT_COUNT != 126:
        raise RuntimeError("Selected seller count constant changed.")
    if EXPECTED_SELECTED_NONPARTICIPATING_VISIT_COUNT != 24:
        raise RuntimeError("Selected nonparticipating count constant changed.")
    if EXPECTED_NONPARTICIPATING_TRANSACTION_COUNT != 21:
        raise RuntimeError("Nonparticipating transaction count constant changed.")
    if EXPECTED_MULTIPLE_BUYER_TRANSACTION_COUNT != 19:
        raise RuntimeError("Multiple-buyer transaction count constant changed.")
    if EXPECTED_MULTIPLE_SELLER_TRANSACTION_COUNT != 44:
        raise RuntimeError("Multiple-seller transaction count constant changed.")
    if EXPECTED_ONLY_NONPARTICIPATING_TRANSACTION_COUNT != 7:
        raise RuntimeError("Only-nonparticipating overlap constant changed.")
    if EXPECTED_ONLY_MULTIPLE_BUYER_TRANSACTION_COUNT != 8:
        raise RuntimeError("Only-multiple-buyer overlap constant changed.")
    if EXPECTED_ONLY_MULTIPLE_SELLER_TRANSACTION_COUNT != 27:
        raise RuntimeError("Only-multiple-seller overlap constant changed.")
    if EXPECTED_NONPARTICIPATING_AND_MULTIPLE_BUYER_COUNT != 4:
        raise RuntimeError("Nonparticipating and multiple-buyer overlap changed.")
    if EXPECTED_NONPARTICIPATING_AND_MULTIPLE_SELLER_COUNT != 10:
        raise RuntimeError("Nonparticipating and multiple-seller overlap changed.")
    if EXPECTED_MULTIPLE_BUYER_AND_SELLER_COUNT != 7:
        raise RuntimeError("Multiple-buyer and multiple-seller overlap changed.")
    if EXPECTED_ALL_THREE_REASONS_COUNT != 0:
        raise RuntimeError("All-three-reasons overlap changed.")
    overlap_total = (
        EXPECTED_ONLY_NONPARTICIPATING_TRANSACTION_COUNT
        + EXPECTED_ONLY_MULTIPLE_BUYER_TRANSACTION_COUNT
        + EXPECTED_ONLY_MULTIPLE_SELLER_TRANSACTION_COUNT
        + EXPECTED_NONPARTICIPATING_AND_MULTIPLE_BUYER_COUNT
        + EXPECTED_NONPARTICIPATING_AND_MULTIPLE_SELLER_COUNT
        + EXPECTED_MULTIPLE_BUYER_AND_SELLER_COUNT
        + EXPECTED_ALL_THREE_REASONS_COUNT
    )
    if overlap_total != EXPECTED_SELECTED_TRANSACTION_COUNT:
        raise RuntimeError("Selection overlap does not add up to one row per transaction.")
    single = selection_flags(1, 1, 0)
    if single["selected"] is not False or single["selection_reasons"] != "":
        raise RuntimeError("A one-buyer one-seller transaction must stay unselected.")
    nonparticipating_only = selection_flags(1, 1, 1)
    if nonparticipating_only["selection_reasons"] != REASON_NONPARTICIPATING:
        raise RuntimeError("Nonparticipating selection reason is wrong.")
    buyers_only = selection_flags(2, 1, 0)
    if buyers_only["selection_reasons"] != REASON_MULTIPLE_BUYERS:
        raise RuntimeError("Multiple-buyer selection reason is wrong.")
    sellers_only = selection_flags(1, 2, 0)
    if sellers_only["selection_reasons"] != REASON_MULTIPLE_SELLERS:
        raise RuntimeError("Multiple-seller selection reason is wrong.")
    combined = selection_flags(2, 2, 1)
    if combined["selection_reasons"] != (
        f"{REASON_NONPARTICIPATING}|{REASON_MULTIPLE_BUYERS}|{REASON_MULTIPLE_SELLERS}"
    ):
        raise RuntimeError("Combined selection reasons are not one transaction string.")
    if combined["selected_because_nonparticipating_present"] is not True:
        raise RuntimeError("Combined flags dropped nonparticipating.")
    required_summary = (
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
    )
    for column in required_summary:
        if column not in SUMMARY_COLUMNS:
            raise RuntimeError(f"Summary CSV is missing {column}.")
    required_party = (
        "baseline_arrival_timestep",
        "actual_arrival_timestep",
        "baseline_minus_actual_arrival_timesteps",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "actual_passage_timestep",
        "baseline_local_rank",
        "post_trade_local_rank",
        "assigned_rank",
        "actual_node_passage_rank",
        "binding_sequence_auxiliary_rank",
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
        "individual_economic_condition_status",
        "predicted_signed_time_difference_timesteps",
        "actual_signed_time_difference_timesteps",
        "predicted_external_effect_value",
        "actual_external_effect_value",
        "declared_vot_per_second",
        "true_vot_per_second",
        "participates_in_order_exchange",
    )
    for column in required_party:
        if column not in PARTY_COLUMNS:
            raise RuntimeError(f"Parties CSV is missing {column}.")
    if _csv_cell(None) != "":
        raise RuntimeError("None must stay blank.")
    if _csv_cell(0) != "0":
        raise RuntimeError("Numeric zero must stay visible.")
    if _csv_cell(False) != "False":
        raise RuntimeError("False must stay visible.")
    if _is_numeric_zero(None) is not False:
        raise RuntimeError("Blank must not count as zero.")
    if _is_numeric_zero(0) is not True or _is_numeric_zero(0.0) is not True:
        raise RuntimeError("Numeric zero must count as zero.")
    excluded = _monetary_transfer_fields(
        "nonparticipating", None, None, False, False
    )
    if excluded["official_payment"] is not None or excluded["official_compensation"] is not None:
        raise RuntimeError("Nonparticipating raw official amounts must stay None.")
    if excluded["effective_payment_amount"] != 0 or excluded["effective_compensation_amount"] != 0:
        raise RuntimeError("Excluded nonparticipating effective amounts must be 0.")
    if excluded["monetary_transfer_participation_status"] != MONETARY_EXCLUDED_NONPARTICIPATING:
        raise RuntimeError("Nonparticipating monetary status is not the exclusion status.")
    if excluded["payment_record_status"] != RECORD_ABSENT_NOT_APPLICABLE:
        raise RuntimeError("Missing nonparticipating payment record is not absent_not_applicable.")
    if excluded["compensation_record_status"] != RECORD_ABSENT_NOT_APPLICABLE:
        raise RuntimeError(
            "Missing nonparticipating compensation record is not absent_not_applicable."
        )
    unexpected = _monetary_transfer_fields(
        "nonparticipating", 3.0, None, True, False
    )
    if unexpected["official_payment"] != 3.0:
        raise RuntimeError("An unexpected nonparticipating payment raw value was rewritten.")
    if unexpected["effective_payment_amount"] is not None:
        raise RuntimeError("An unexpected nonparticipating payment was turned into 0.")
    if unexpected["payment_record_status"] != RECORD_UNEXPECTED_PRESENT:
        raise RuntimeError("An unexpected nonparticipating payment record was not flagged.")
    if unexpected["monetary_transfer_participation_status"] != MONETARY_UNEXPECTED:
        raise RuntimeError("An unexpected nonparticipating record stayed in the exclusion status.")
    buyer_money = _monetary_transfer_fields("buyer", 1.5, None, True, False)
    if buyer_money["official_payment"] != 1.5 or buyer_money["effective_payment_amount"] != 1.5:
        raise RuntimeError("Buyer payment record amount was changed.")
    if buyer_money["official_compensation"] is not None:
        raise RuntimeError("Buyer raw compensation was invented.")
    if buyer_money["effective_compensation_amount"] != 0:
        raise RuntimeError("Buyer compensation exclusion is not the explicit amount 0.")
    if buyer_money["compensation_record_status"] != RECORD_ABSENT_NOT_APPLICABLE:
        raise RuntimeError("Buyer compensation record status is wrong.")
    seller_money = _monetary_transfer_fields("seller", None, 2.5, False, True)
    if seller_money["official_compensation"] != 2.5 or seller_money["effective_compensation_amount"] != 2.5:
        raise RuntimeError("Seller compensation record amount was changed.")
    if seller_money["official_payment"] is not None or seller_money["effective_payment_amount"] != 0:
        raise RuntimeError("Seller payment exclusion does not keep raw None and effective 0.")
    if _reference_amount_status("nonparticipating", "payment", None) != RECORD_ABSENT_NOT_APPLICABLE:
        raise RuntimeError("Nonparticipating reference payment None is not absent_not_applicable.")
    if _reference_amount_status("nonparticipating", "compensation", None) != RECORD_ABSENT_NOT_APPLICABLE:
        raise RuntimeError(
            "Nonparticipating reference compensation None is not absent_not_applicable."
        )
    if _reference_amount_status("nonparticipating", "payment", 0) != RECORD_UNEXPECTED_PRESENT:
        raise RuntimeError("A stored nonparticipating reference 0 was treated as raw None.")
    excluded_party = {
        "visit_key": ("veh_np", 1),
        "role": "nonparticipating",
        "participates_in_order_exchange": False,
        "declared_vot_per_second": None,
        "true_vot_per_second": 0.2,
        "reference_payment": None,
        "reference_compensation": None,
        "reference_payment_status": RECORD_ABSENT_NOT_APPLICABLE,
        "reference_compensation_status": RECORD_ABSENT_NOT_APPLICABLE,
    }
    excluded_party.update(excluded)
    excluded_failures = _nonparticipating_payment_failures(
        (
            {
                "tvt_decision_timestep": 1,
                "node_name": "east_intersection",
                "parties": (excluded_party,),
            },
        )
    )
    if len(excluded_failures) != 0:
        raise RuntimeError("The nonparticipating exclusion contract rejected a valid exclusion.")
    rewritten = dict(excluded_party)
    rewritten["official_payment"] = 0
    rewritten_failures = _nonparticipating_payment_failures(
        (
            {
                "tvt_decision_timestep": 1,
                "node_name": "east_intersection",
                "parties": (rewritten,),
            },
        )
    )
    if len(rewritten_failures) == 0:
        raise RuntimeError("A raw official payment of 0 passed as a nonparticipating blank.")
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    validator = _function_by_name(tree, "validate_static_contract")
    validator_calls = _call_names(validator)
    if "exec_simulation" in validator_calls or "main" in validator_calls:
        raise RuntimeError("Static validation must not start the simulation.")
    driver_wrapper = _function_by_name(tree, "wrapped_run_tvt_mp_driver")
    driver_calls = _call_names(driver_wrapper)
    if driver_calls.count("original_run_tvt_mp_driver") != 1:
        raise RuntimeError("Driver wrapper must call the original function once.")
    arrival_wrapper = _function_by_name(tree, "wrapped_record_order_control_node_arrival")
    arrival_calls = _call_names(arrival_wrapper)
    if arrival_calls.count("original_record_order_control_node_arrival") != 1:
        raise RuntimeError("Arrival wrapper must call the original function once.")
    for function_node in (driver_wrapper, arrival_wrapper):
        returns_result = False
        for node in ast.walk(function_node):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id == "result":
                    returns_result = True
        if returns_result is not True:
            raise RuntimeError(f"{function_node.name} does not return the original result.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "copy":
            raise RuntimeError("Diagnostic source calls copy.")
        if isinstance(node, ast.Name) and node.id == "random":
            raise RuntimeError("Diagnostic source uses random.")
    main_function = _function_by_name(tree, "main")
    restores_in_finally = False
    for node in ast.walk(main_function):
        if not isinstance(node, ast.Try):
            continue
        for final_node in node.finalbody:
            for child in ast.walk(final_node):
                if isinstance(child, ast.Name) and child.id == "restore_observation_hooks":
                    restores_in_finally = True
    if restores_in_finally is not True:
        raise RuntimeError("Hooks are not restored in finally.")
    if "_order_control_baseline_collector" not in source:
        raise RuntimeError("Actual arrival hook does not reject a baseline collector.")
    if "get_baseline_visit_snapshot" not in source:
        raise RuntimeError("Baseline arrival is not read from the decision collector.")
    if "candidate_visits" not in source or "assigned_rank" not in source:
        raise RuntimeError("Local rank sources are missing.")
    if "order_control_tvt_rank_states_by_node_name" not in source:
        raise RuntimeError("Node rank state is not the assigned_rank source.")
    if "actual_node_passage_rank" not in source:
        raise RuntimeError("Actual passage history rank is missing.")
    if "binding_sequence_auxiliary_rank" not in source:
        raise RuntimeError("Binding rank is missing as an auxiliary column.")
    baseline_function = _function_by_name(tree, "_baseline_local_ranks")
    if "sorted" in _call_names(baseline_function):
        raise RuntimeError("baseline_local_rank re-sorts candidate_visits.")
    post_trade_function = _function_by_name(tree, "_post_trade_local_ranks")
    if "assigned_rank" not in _call_names(post_trade_function):
        raise RuntimeError("post_trade_local_rank does not read assigned_rank.")
    if "binding_rank" in _call_names(post_trade_function):
        raise RuntimeError("post_trade_local_rank uses the binding rank.")
    if "_nonparticipating_rank_failures" not in source:
        raise RuntimeError("Nonparticipating rank protection is missing.")
    if "_nonparticipating_payment_failures" not in source:
        raise RuntimeError("Nonparticipating payment exclusion check is missing.")
    sum_payments = _function_by_name(tree, "_sum_payments")
    sum_payment_attributes = []
    for node in ast.walk(sum_payments):
        if isinstance(node, ast.Attribute):
            sum_payment_attributes.append(node.attr)
    if "buyer_payment_records" not in sum_payment_attributes:
        raise RuntimeError("Payment balance does not read buyer payment records.")
    if "effective_payment_amount" in sum_payment_attributes:
        raise RuntimeError("Payment balance reads the effective amount.")
    sum_compensations = _function_by_name(tree, "_sum_compensations")
    sum_compensation_attributes = []
    for node in ast.walk(sum_compensations):
        if isinstance(node, ast.Attribute):
            sum_compensation_attributes.append(node.attr)
    if "seller_compensation_records" not in sum_compensation_attributes:
        raise RuntimeError("Payment balance does not read seller compensation records.")
    if PAYMENT_BALANCE_REL_TOL != 1e-12:
        raise RuntimeError("PAYMENT_BALANCE_REL_TOL is not 1e-12.")
    if PAYMENT_BALANCE_ABS_TOL != 1e-12:
        raise RuntimeError("PAYMENT_BALANCE_ABS_TOL is not 1e-12.")
    balance_function = _function_by_name(tree, "_payment_balance_satisfied")
    balance_calls = _call_names(balance_function)
    if balance_calls.count("isclose") != 1:
        raise RuntimeError("Payment balance must use math.isclose once.")
    capture_function = _function_by_name(tree, "_capture_selected_node")
    for node in ast.walk(capture_function):
        if not isinstance(node, ast.Compare):
            continue
        if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
            continue
        if not isinstance(node.left, ast.Name):
            continue
        if node.left.id != "payment_balance_difference":
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and comparator.value == 0:
                raise RuntimeError(
                    "Payment balance still uses exact equality on payment_balance_difference."
                )
    if _payment_balance_satisfied(1.0, 1.0) is not True:
        raise RuntimeError("Exact payment balance did not satisfy.")
    if _payment_balance_satisfied(1.0, 1.0 + 2.220446049250313e-16) is not True:
        raise RuntimeError("Machine-epsilon payment balance did not satisfy.")
    if _payment_balance_satisfied(1.0, 1.0 + 5e-13) is not True:
        raise RuntimeError("In-tolerance payment balance did not satisfy.")
    if _payment_balance_satisfied(1.0, 1.0 + 1e-8) is not False:
        raise RuntimeError("Out-of-tolerance payment balance was satisfied.")
    if _payment_balance_satisfied(float("nan"), 1.0) is not False:
        raise RuntimeError("NaN payment total was satisfied.")
    if _payment_balance_satisfied(1.0, float("inf")) is not False:
        raise RuntimeError("Infinite compensation total was satisfied.")
    if _payment_balance_satisfied(None, 1.0) is not False:
        raise RuntimeError("None payment total was satisfied.")
    if _payment_balance_satisfied(True, 1.0) is not False:
        raise RuntimeError("Boolean payment total was satisfied.")
    rank_function = _function_by_name(tree, "_nonparticipating_rank_failures")
    rank_source = ast.get_source_segment(source, rank_function)
    if rank_source is None or "baseline_local_rank" not in rank_source or "post_trade_local_rank" not in rank_source:
        raise RuntimeError("Local rank protection no longer compares the two local ranks.")
    if "OUTPUT_DIR.exists()" not in source:
        raise RuntimeError("Existing output directory is not refused.")
    if SCRIPT_PATH.name != (
        "diagnose_tvt_mp_nonparticipating_20_selected_transaction_fundamentals.py"
    ):
        raise RuntimeError("This validator is attached to the wrong file.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
        print("Static contract validation passed.")
    else:
        raise SystemExit(main())
