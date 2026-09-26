"""
TVT-MP payment and compensation calculation for one selected candidate per Node.

This module reads a saved candidate-selection set result and, for each
target Node, computes buyer payments and seller compensations from the
already saved economic values. It does not search the real World, does
not update Vehicle ledgers, does not build a final rank, and does not
change the input results.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionSetResult,
    OrderControlTvtMpCandidateSelectionStatus,
    OrderControlTvtNodeMpCandidateSelectionResult,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtMpSellerEconomicRecord,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


class OrderControlTvtMpPaymentAndCompensationStatus(Enum):
    """Outcome of payment and compensation calculation for one target Node."""

    CALCULATED = "calculated"
    NO_SELECTED_CANDIDATE = "no_selected_candidate"


@dataclass(frozen=True)
class OrderControlTvtMpBuyerPaymentRecord:
    """One buyer's predicted payment for the selected candidate."""

    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    payment_P_b: float


@dataclass(frozen=True)
class OrderControlTvtMpSellerCompensationRecord:
    """One seller's predicted compensation for the selected candidate."""

    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    compensation_amount: float


@dataclass(frozen=True)
class OrderControlTvtNodeMpPaymentAndCompensationResult:
    """Payment and compensation outcome for one target Node."""

    node_name: str
    payment_and_compensation_status: OrderControlTvtMpPaymentAndCompensationStatus
    selected_candidate_economic_result: (
        OrderControlTvtMpCandidateEconomicEvaluationResult | None
    )
    buyer_payment_records: tuple[OrderControlTvtMpBuyerPaymentRecord, ...]
    seller_compensation_records: tuple[
        OrderControlTvtMpSellerCompensationRecord,
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtMpPaymentAndCompensationSetResult:
    """All-Node payment and compensation result for one selection set."""

    candidate_selection_set_result: OrderControlTvtMpCandidateSelectionSetResult
    node_payment_and_compensation_results: tuple[
        OrderControlTvtNodeMpPaymentAndCompensationResult,
        ...,
    ]


def calculate_tvt_mp_payments_and_compensations(
    candidate_selection_set_result,
) -> OrderControlTvtMpPaymentAndCompensationSetResult:
    """
    Calculate predicted buyer payments and seller compensations.

    The only public input is a saved candidate-selection set result.
    Real World objects are not accepted and not searched. Each selected
    candidate pays P_b = R * G_b / G and each selected seller receives
    the already saved R_s. This function does not update Vehicle
    payment ledgers and returns no partial overall result.
    """
    selection_set_result = _require_candidate_selection_set_result(
        candidate_selection_set_result,
    )
    node_selection_results, node_economic_results = (
        _require_matching_node_result_columns(selection_set_result)
    )

    node_payment_results: list[OrderControlTvtNodeMpPaymentAndCompensationResult] = []
    node_index = 0
    for node_selection_result in node_selection_results:
        node_economic_result = node_economic_results[node_index]
        node_payment_result = _calculate_for_one_node(
            node_selection_result=node_selection_result,
            node_economic_result=node_economic_result,
        )
        node_payment_results.append(node_payment_result)
        node_index = node_index + 1

    return _build_overall_result(
        selection_set_result=selection_set_result,
        node_payment_results=tuple(node_payment_results),
    )


def _require_candidate_selection_set_result(
    candidate_selection_set_result: object,
) -> OrderControlTvtMpCandidateSelectionSetResult:
    if not isinstance(
        candidate_selection_set_result,
        OrderControlTvtMpCandidateSelectionSetResult,
    ):
        raise ValueError(
            "candidate_selection_set_result must be "
            "OrderControlTvtMpCandidateSelectionSetResult; got "
            f"type {type(candidate_selection_set_result).__name__}."
        )
    return candidate_selection_set_result


def _require_matching_node_result_columns(
    selection_set_result: OrderControlTvtMpCandidateSelectionSetResult,
) -> tuple[
    tuple[OrderControlTvtNodeMpCandidateSelectionResult, ...],
    tuple[OrderControlTvtNodeMpEconomicEvaluationResult, ...],
]:
    node_selection_results = selection_set_result.node_candidate_selection_results
    if not isinstance(node_selection_results, tuple):
        raise RuntimeError(
            "node_candidate_selection_results must be a tuple; got "
            f"type {type(node_selection_results).__name__}."
        )

    economic_set_result = selection_set_result.economic_evaluation_set_result
    if not isinstance(
        economic_set_result,
        OrderControlTvtMpEconomicEvaluationSetResult,
    ):
        raise RuntimeError(
            "economic_evaluation_set_result must be "
            "OrderControlTvtMpEconomicEvaluationSetResult; got "
            f"type {type(economic_set_result).__name__}."
        )

    node_economic_results = economic_set_result.node_economic_evaluation_results
    if not isinstance(node_economic_results, tuple):
        raise RuntimeError(
            "node_economic_evaluation_results must be a tuple; got "
            f"type {type(node_economic_results).__name__}."
        )

    if len(node_selection_results) != len(node_economic_results):
        raise RuntimeError(
            "selection Node results and economic Node results must have "
            "the same length; got "
            f"{len(node_selection_results)} selection Node results and "
            f"{len(node_economic_results)} economic Node results."
        )
    return node_selection_results, node_economic_results


def _calculate_for_one_node(
    *,
    node_selection_result: object,
    node_economic_result: object,
) -> OrderControlTvtNodeMpPaymentAndCompensationResult:
    if not isinstance(
        node_selection_result,
        OrderControlTvtNodeMpCandidateSelectionResult,
    ):
        raise RuntimeError(
            "Each node candidate-selection result must be "
            "OrderControlTvtNodeMpCandidateSelectionResult; got "
            f"type {type(node_selection_result).__name__}."
        )
    if not isinstance(
        node_economic_result,
        OrderControlTvtNodeMpEconomicEvaluationResult,
    ):
        raise RuntimeError(
            "Each node economic-evaluation result must be "
            "OrderControlTvtNodeMpEconomicEvaluationResult; got "
            f"type {type(node_economic_result).__name__}."
        )

    node_name = _require_node_name_string(
        node_selection_result.node_name,
        field_name="selection node_name",
    )
    economic_node_name = _require_node_name_string(
        node_economic_result.node_name,
        field_name="economic node_name",
    )
    if economic_node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: economic node_name {economic_node_name!r} "
            "does not match the selection Node result."
        )

    selection_status = node_selection_result.selection_status
    selected_candidate = node_selection_result.selected_candidate_economic_result
    _require_status_matches_selected_candidate(
        selection_status=selection_status,
        selected_candidate=selected_candidate,
        node_name=node_name,
    )

    if (
        selection_status
        is OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    ):
        return _build_no_selected_candidate_node_result(node_name=node_name)

    candidate_economic_results = (
        node_economic_result.candidate_economic_evaluation_results
    )
    if not isinstance(candidate_economic_results, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: candidate_economic_evaluation_results "
            "must be a tuple; got "
            f"type {type(candidate_economic_results).__name__}."
        )
    _require_selected_candidate_is_input_object(
        selected_candidate=selected_candidate,
        candidate_economic_results=candidate_economic_results,
        node_name=node_name,
    )
    buyer_payment_records, seller_compensation_records = (
        _calculate_for_selected_candidate(
            selected_candidate=selected_candidate,
            node_name=node_name,
        )
    )
    return _build_calculated_node_result(
        node_name=node_name,
        selected_candidate_economic_result=selected_candidate,
        buyer_payment_records=buyer_payment_records,
        seller_compensation_records=seller_compensation_records,
    )


def _require_node_name_string(node_name: object, *, field_name: str) -> str:
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"{field_name} must be a non-empty str; got {node_name!r}."
        )
    return node_name


def _require_status_matches_selected_candidate(
    *,
    selection_status: object,
    selected_candidate: object,
    node_name: str,
) -> None:
    if not isinstance(selection_status, OrderControlTvtMpCandidateSelectionStatus):
        raise RuntimeError(
            f"Node {node_name!r}: selection_status must be "
            "OrderControlTvtMpCandidateSelectionStatus; got "
            f"{selection_status!r}."
        )
    if selection_status is OrderControlTvtMpCandidateSelectionStatus.SELECTED:
        if selected_candidate is None:
            raise RuntimeError(
                f"Node {node_name!r}: SELECTED requires a selected candidate."
            )
        if not isinstance(
            selected_candidate,
            OrderControlTvtMpCandidateEconomicEvaluationResult,
        ):
            raise RuntimeError(
                f"Node {node_name!r}: selected_candidate_economic_result "
                "must be OrderControlTvtMpCandidateEconomicEvaluationResult; "
                f"got type {type(selected_candidate).__name__}."
            )
        return
    if (
        selection_status
        is OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    ):
        if selected_candidate is not None:
            raise RuntimeError(
                f"Node {node_name!r}: NO_ECONOMICALLY_FEASIBLE_CANDIDATE "
                "requires selected_candidate_economic_result is None."
            )
        return
    raise RuntimeError(
        f"Node {node_name!r}: unknown selection_status {selection_status!r}."
    )


def _require_selected_candidate_is_input_object(
    *,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
    candidate_economic_results: tuple[object, ...],
    node_name: str,
) -> None:
    for input_candidate in candidate_economic_results:
        if input_candidate is selected_candidate:
            return
    raise RuntimeError(
        f"Node {node_name!r}: selected candidate is not an object from the "
        "input economic Node result."
    )


def _calculate_for_selected_candidate(
    *,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
    node_name: str,
) -> tuple[
    tuple[OrderControlTvtMpBuyerPaymentRecord, ...],
    tuple[OrderControlTvtMpSellerCompensationRecord, ...],
]:
    economically_feasible = selected_candidate.economically_feasible
    if type(economically_feasible) is not bool:
        raise RuntimeError(
            f"Node {node_name!r}: economically_feasible must be a strict "
            "Python bool; got "
            f"type {type(economically_feasible).__name__} with value "
            f"{economically_feasible!r}."
        )
    if economically_feasible is not True:
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate is not economically "
            "feasible; payment and compensation are computed only for an "
            "economically feasible selected candidate."
        )

    total_buyer_value_G = _require_positive_finite_number(
        selected_candidate.total_buyer_value_G,
        field_name="total_buyer_value_G",
        node_name=node_name,
    )
    total_required_compensation_R = _require_non_negative_finite_number(
        selected_candidate.total_required_compensation_R,
        field_name="total_required_compensation_R",
        node_name=node_name,
    )
    if not (total_buyer_value_G >= total_required_compensation_R):
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate has "
            "total_buyer_value_G < total_required_compensation_R."
        )

    buyer_economic_records = selected_candidate.buyer_economic_records
    if not isinstance(buyer_economic_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: buyer_economic_records must be a tuple; "
            f"got type {type(buyer_economic_records).__name__}."
        )
    if len(buyer_economic_records) < 1:
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate has no buyer economic "
            "records."
        )

    seller_economic_records = selected_candidate.seller_economic_records
    if not isinstance(seller_economic_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: seller_economic_records must be a tuple; "
            f"got type {type(seller_economic_records).__name__}."
        )

    buyer_payment_records = _build_buyer_payment_records(
        buyer_economic_records=buyer_economic_records,
        total_buyer_value_G=total_buyer_value_G,
        total_required_compensation_R=total_required_compensation_R,
        node_name=node_name,
    )
    seller_compensation_records = _build_seller_compensation_records(
        seller_economic_records=seller_economic_records,
        total_required_compensation_R=total_required_compensation_R,
        node_name=node_name,
    )
    return buyer_payment_records, seller_compensation_records


def _build_buyer_payment_records(
    *,
    buyer_economic_records: tuple[object, ...],
    total_buyer_value_G: int | float,
    total_required_compensation_R: int | float,
    node_name: str,
) -> tuple[OrderControlTvtMpBuyerPaymentRecord, ...]:
    summed_buyer_value_G = 0.0
    for buyer_economic_record in buyer_economic_records:
        _require_buyer_economic_record_type(
            buyer_economic_record,
            node_name=node_name,
        )
        gross_time_value_G_b = _require_positive_finite_number(
            buyer_economic_record.gross_time_value_G_b,
            field_name="gross_time_value_G_b",
            node_name=node_name,
        )
        summed_buyer_value_G = summed_buyer_value_G + gross_time_value_G_b

    if summed_buyer_value_G != total_buyer_value_G:
        raise RuntimeError(
            f"Node {node_name!r}: saved total_buyer_value_G "
            f"{total_buyer_value_G!r} does not equal the explicit sum of "
            f"buyer G_b values {summed_buyer_value_G!r}."
        )

    buyer_payment_records: list[OrderControlTvtMpBuyerPaymentRecord] = []
    for buyer_economic_record in buyer_economic_records:
        visit_key = buyer_economic_record.visit_key
        vehicle_name = buyer_economic_record.vehicle_name
        gross_time_value_G_b = buyer_economic_record.gross_time_value_G_b
        # Each buyer pays a share of R equal to that buyer's share of G.
        # P_b = R * G_b / G. The last buyer does not receive a leftover
        # residual, and buyer order is not used to correct float error.
        R = total_required_compensation_R
        G = total_buyer_value_G
        G_b = gross_time_value_G_b
        payment_P_b = R * G_b / G
        payment_P_b = _require_non_negative_finite_number(
            payment_P_b,
            field_name="payment_P_b",
            node_name=node_name,
        )
        buyer_payment_records.append(
            OrderControlTvtMpBuyerPaymentRecord(
                visit_key=visit_key,
                vehicle_name=vehicle_name,
                payment_P_b=payment_P_b,
            )
        )
    return tuple(buyer_payment_records)


def _build_seller_compensation_records(
    *,
    seller_economic_records: tuple[object, ...],
    total_required_compensation_R: int | float,
    node_name: str,
) -> tuple[OrderControlTvtMpSellerCompensationRecord, ...]:
    summed_required_compensation_R = 0.0
    for seller_economic_record in seller_economic_records:
        _require_seller_economic_record_type(
            seller_economic_record,
            node_name=node_name,
        )
        required_compensation_R_s = _require_non_negative_finite_number(
            seller_economic_record.required_compensation_R_s,
            field_name="required_compensation_R_s",
            node_name=node_name,
        )
        summed_required_compensation_R = (
            summed_required_compensation_R + required_compensation_R_s
        )

    if summed_required_compensation_R != total_required_compensation_R:
        raise RuntimeError(
            f"Node {node_name!r}: saved total_required_compensation_R "
            f"{total_required_compensation_R!r} does not equal the explicit "
            f"sum of seller R_s values {summed_required_compensation_R!r}."
        )

    seller_compensation_records: list[OrderControlTvtMpSellerCompensationRecord] = []
    for seller_economic_record in seller_economic_records:
        visit_key = seller_economic_record.visit_key
        vehicle_name = seller_economic_record.vehicle_name
        required_compensation_R_s = seller_economic_record.required_compensation_R_s
        # compensation_amount is the saved reservation R_s. This module
        # does not recompute R_s from declared VOT or passage times.
        # A delayed seller with declared VOT = 0 still has saved R_s = 0
        # because reservation is waiting-increase seconds times declared
        # VOT. An on-time or early seller also has saved R_s = 0 because
        # waiting increase is clipped at 0. Copy that saved R_s. Do not
        # inflate a zero compensation to a positive amount, and do not
        # change the seller role.
        compensation_amount = required_compensation_R_s
        compensation_amount = _require_non_negative_finite_number(
            compensation_amount,
            field_name="compensation_amount",
            node_name=node_name,
        )
        seller_compensation_records.append(
            OrderControlTvtMpSellerCompensationRecord(
                visit_key=visit_key,
                vehicle_name=vehicle_name,
                compensation_amount=compensation_amount,
            )
        )
    return tuple(seller_compensation_records)


def _require_buyer_economic_record_type(
    buyer_economic_record: object,
    *,
    node_name: str,
) -> None:
    if not isinstance(buyer_economic_record, OrderControlTvtMpBuyerEconomicRecord):
        raise RuntimeError(
            f"Node {node_name!r}: each buyer economic record must be "
            "OrderControlTvtMpBuyerEconomicRecord; got "
            f"type {type(buyer_economic_record).__name__}."
        )


def _require_seller_economic_record_type(
    seller_economic_record: object,
    *,
    node_name: str,
) -> None:
    if not isinstance(seller_economic_record, OrderControlTvtMpSellerEconomicRecord):
        raise RuntimeError(
            f"Node {node_name!r}: each seller economic record must be "
            "OrderControlTvtMpSellerEconomicRecord; got "
            f"type {type(seller_economic_record).__name__}."
        )


def _require_positive_finite_number(
    value: object,
    *,
    field_name: str,
    node_name: str,
) -> int | float:
    number = _require_finite_number(
        value,
        field_name=field_name,
        node_name=node_name,
    )
    if not (number > 0):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a positive finite "
            f"number; got {number!r}."
        )
    return number


def _require_non_negative_finite_number(
    value: object,
    *,
    field_name: str,
    node_name: str,
) -> int | float:
    number = _require_finite_number(
        value,
        field_name=field_name,
        node_name=node_name,
    )
    if number < 0:
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a non-negative "
            f"finite number; got {number!r}."
        )
    return number


def _require_finite_number(
    value: object,
    *,
    field_name: str,
    node_name: str,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a finite number; got "
            f"type {type(value).__name__} with value {value!r}."
        )
    if not math.isfinite(value):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a finite number; got "
            f"{value!r}."
        )
    return value


def _build_no_selected_candidate_node_result(
    *,
    node_name: str,
) -> OrderControlTvtNodeMpPaymentAndCompensationResult:
    return _build_node_payment_and_compensation_result(
        node_name=node_name,
        payment_and_compensation_status=(
            OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
        ),
        selected_candidate_economic_result=None,
        buyer_payment_records=(),
        seller_compensation_records=(),
    )


def _build_calculated_node_result(
    *,
    node_name: str,
    selected_candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
    buyer_payment_records: tuple[OrderControlTvtMpBuyerPaymentRecord, ...],
    seller_compensation_records: tuple[
        OrderControlTvtMpSellerCompensationRecord,
        ...,
    ],
) -> OrderControlTvtNodeMpPaymentAndCompensationResult:
    return _build_node_payment_and_compensation_result(
        node_name=node_name,
        payment_and_compensation_status=(
            OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
        ),
        selected_candidate_economic_result=selected_candidate_economic_result,
        buyer_payment_records=buyer_payment_records,
        seller_compensation_records=seller_compensation_records,
    )


def _build_node_payment_and_compensation_result(
    *,
    node_name: str,
    payment_and_compensation_status: OrderControlTvtMpPaymentAndCompensationStatus,
    selected_candidate_economic_result: (
        OrderControlTvtMpCandidateEconomicEvaluationResult | None
    ),
    buyer_payment_records: tuple[OrderControlTvtMpBuyerPaymentRecord, ...],
    seller_compensation_records: tuple[
        OrderControlTvtMpSellerCompensationRecord,
        ...,
    ],
) -> OrderControlTvtNodeMpPaymentAndCompensationResult:
    if not isinstance(
        buyer_payment_records,
        tuple,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: buyer_payment_records must be a tuple; "
            f"got type {type(buyer_payment_records).__name__}."
        )
    if not isinstance(
        seller_compensation_records,
        tuple,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: seller_compensation_records must be a "
            f"tuple; got type {type(seller_compensation_records).__name__}."
        )

    if (
        payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    ):
        if selected_candidate_economic_result is None:
            raise RuntimeError(
                f"Node {node_name!r}: CALCULATED requires a selected "
                "candidate."
            )
        if len(buyer_payment_records) < 1:
            raise RuntimeError(
                f"Node {node_name!r}: CALCULATED requires one or more "
                "buyer payment records."
            )
    elif (
        payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
    ):
        if selected_candidate_economic_result is not None:
            raise RuntimeError(
                f"Node {node_name!r}: NO_SELECTED_CANDIDATE requires "
                "selected_candidate_economic_result is None."
            )
        if len(buyer_payment_records) != 0:
            raise RuntimeError(
                f"Node {node_name!r}: NO_SELECTED_CANDIDATE requires empty "
                "buyer_payment_records."
            )
        if len(seller_compensation_records) != 0:
            raise RuntimeError(
                f"Node {node_name!r}: NO_SELECTED_CANDIDATE requires empty "
                "seller_compensation_records."
            )
    else:
        raise RuntimeError(
            f"Node {node_name!r}: unknown payment_and_compensation_status "
            f"{payment_and_compensation_status!r}."
        )

    return OrderControlTvtNodeMpPaymentAndCompensationResult(
        node_name=node_name,
        payment_and_compensation_status=payment_and_compensation_status,
        selected_candidate_economic_result=selected_candidate_economic_result,
        buyer_payment_records=buyer_payment_records,
        seller_compensation_records=seller_compensation_records,
    )


def _build_overall_result(
    *,
    selection_set_result: OrderControlTvtMpCandidateSelectionSetResult,
    node_payment_results: tuple[
        OrderControlTvtNodeMpPaymentAndCompensationResult,
        ...,
    ],
) -> OrderControlTvtMpPaymentAndCompensationSetResult:
    return OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=selection_set_result,
        node_payment_and_compensation_results=node_payment_results,
    )
