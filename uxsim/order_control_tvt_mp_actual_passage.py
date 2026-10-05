from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)

if TYPE_CHECKING:
    from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
        OrderControlTvtMpCandidatePassageObservationStatus,
    )


class OrderControlTvtMpActualPassageRole(Enum):
    BUYER = "buyer"
    SELLER = "seller"
    NONPARTICIPATING = "nonparticipating"


class OrderControlTvtMpActualPassageObservationStatus(Enum):
    ACTUAL_PASSAGE_OBSERVED = "actual_passage_observed"
    ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END = (
        "actual_passage_unobserved_at_evaluation_end"
    )


class OrderControlTvtMpActualPassageWaitStatus(Enum):
    WAITING_FOR_ACTUAL_PASSAGE = "waiting_for_actual_passage"
    ACTUAL_PASSAGE_OBSERVED = "actual_passage_observed"
    ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END = (
        "actual_passage_unobserved_at_evaluation_end"
    )


class OrderControlTvtMpTradeExPostEvaluationStatus(Enum):
    EVALUATION_UNAVAILABLE = "evaluation_unavailable"
    EX_POST_INFEASIBLE = "ex_post_infeasible"
    EX_POST_FEASIBLE = "ex_post_feasible"


@dataclass(frozen=True)
class OrderControlTvtMpActualPassageObservationRecord:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    role: OrderControlTvtMpActualPassageRole
    observation_status: OrderControlTvtMpActualPassageObservationStatus
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    true_vot_per_second: float
    predicted_observation_status: OrderControlTvtMpCandidatePassageObservationStatus
    predicted_route_next_link_name: str
    baseline_minus_candidate_passage_timesteps: int | None
    baseline_minus_candidate_passage_seconds: int | float | None
    baseline_minus_candidate_time_value: int | float | None
    baseline_minus_actual_passage_timesteps: int | None
    baseline_minus_actual_passage_seconds: int | float | None
    baseline_minus_actual_time_value: int | float | None
    candidate_minus_actual_passage_timesteps: int | None
    candidate_minus_actual_passage_seconds: int | float | None
    candidate_minus_actual_time_value: int | float | None
    actual_passage_timestep: int | None
    actual_route_next_link_name: str | None


@dataclass(frozen=True)
class OrderControlTvtMpActualPassageCommonFrozenInput:
    """Establishment ranks and route origin copied for later evaluation.

    Identity fields that already live on the wait entry are not repeated
    here. The formal route and the Node rank stay on the rank ledger.
    """

    baseline_local_rank: int
    post_trade_local_rank: int
    rank_change: int
    route_origin: OrderControlTvtMpLocalBindingRouteOrigin

    def __post_init__(self) -> None:
        # Imported here because uxsim.py loads this module while World is
        # still being defined. The binding module reaches World.
        from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
            OrderControlTvtMpLocalBindingRouteOrigin,
        )
        if type(self.baseline_local_rank) is not int:
            raise RuntimeError(
                "baseline_local_rank must be a Python int, not bool; got "
                f"{self.baseline_local_rank!r}."
            )
        if type(self.post_trade_local_rank) is not int:
            raise RuntimeError(
                "post_trade_local_rank must be a Python int, not bool; got "
                f"{self.post_trade_local_rank!r}."
            )
        if type(self.rank_change) is not int:
            raise RuntimeError(
                "rank_change must be a Python int, not bool; got "
                f"{self.rank_change!r}."
            )
        expected_rank_change = (
            self.baseline_local_rank - self.post_trade_local_rank
        )
        if self.rank_change != expected_rank_change:
            raise RuntimeError(
                "rank_change must equal baseline_local_rank minus "
                "post_trade_local_rank; got "
                f"{self.rank_change!r}, expected {expected_rank_change!r}."
            )
        if not isinstance(
            self.route_origin,
            OrderControlTvtMpLocalBindingRouteOrigin,
        ):
            raise RuntimeError(
                "route_origin must be "
                "OrderControlTvtMpLocalBindingRouteOrigin; got type "
                f"{type(self.route_origin).__name__} with value "
                f"{self.route_origin!r}."
            )


@dataclass(frozen=True)
class OrderControlTvtMpActualPassageMonetaryFrozenInput:
    """Buyer or seller transaction amounts copied at establishment.

    Zero is a real computed amount. None is not used in these fields.
    Buyer and seller share this one type.
    """

    declared_vot_per_second: float
    payment_paid_in_this_transaction: int | float
    payment_received_in_this_transaction: int | float

    def __post_init__(self) -> None:
        _require_non_negative_money_number(
            self.declared_vot_per_second,
            "declared_vot_per_second",
        )
        _require_non_negative_money_number(
            self.payment_paid_in_this_transaction,
            "payment_paid_in_this_transaction",
        )
        _require_non_negative_money_number(
            self.payment_received_in_this_transaction,
            "payment_received_in_this_transaction",
        )


def _require_non_negative_money_number(value: object, field_name: str) -> None:
    """Reject None, bool, and non-finite numbers. Zero is allowed."""
    if value is None:
        raise RuntimeError(
            f"{field_name} must be a formal number, not None."
        )
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"{field_name} must be a Python int or float, not bool; got "
            f"{value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"{field_name} must be finite and >= 0; got {value!r}."
        )


def _require_finite_number(value: object, field_name: str) -> None:
    """Reject None, bool, and non-finite numbers. Negative and zero allowed."""
    if value is None:
        raise RuntimeError(
            f"{field_name} must be a formal number, not None."
        )
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"{field_name} must be a Python int or float, not bool; got "
            f"{value!r}."
        )
    if not math.isfinite(value):
        raise RuntimeError(
            f"{field_name} must be finite; got {value!r}."
        )


def _require_positive_finite_number(value: object, field_name: str) -> None:
    _require_finite_number(value, field_name)
    if value <= 0:
        raise RuntimeError(
            f"{field_name} must be > 0; got {value!r}."
        )


def _require_ex_post_record_visit_key_and_vehicle_name(
    visit_key: object,
    vehicle_name: object,
    *,
    record_kind: str,
) -> None:
    _require_history_visit_key(visit_key)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"{record_kind} vehicle_name must be a non-empty str; got "
            f"{vehicle_name!r}."
        )
    if visit_key[0] != vehicle_name:
        raise RuntimeError(
            f"{record_kind} VisitKey vehicle_name {visit_key[0]!r} does not "
            f"match vehicle_name {vehicle_name!r}."
        )


@dataclass(frozen=True)
class OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord:
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    buyer_actual_declared_time_saving_value: int | float
    reference_payment: int | float

    def __post_init__(self) -> None:
        _require_ex_post_record_visit_key_and_vehicle_name(
            self.visit_key,
            self.vehicle_name,
            record_kind="buyer reference payment record",
        )
        _require_finite_number(
            self.buyer_actual_declared_time_saving_value,
            "buyer_actual_declared_time_saving_value",
        )
        _require_non_negative_money_number(
            self.reference_payment,
            "reference_payment",
        )


@dataclass(frozen=True)
class OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord:
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    seller_actual_required_compensation: int | float
    reference_compensation: int | float

    def __post_init__(self) -> None:
        _require_ex_post_record_visit_key_and_vehicle_name(
            self.visit_key,
            self.vehicle_name,
            record_kind="seller reference compensation record",
        )
        _require_non_negative_money_number(
            self.seller_actual_required_compensation,
            "seller_actual_required_compensation",
        )
        _require_non_negative_money_number(
            self.reference_compensation,
            "reference_compensation",
        )


@dataclass(frozen=True)
class OrderControlTvtMpTradeExPostEvaluationResult:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    ex_post_evaluation_status: OrderControlTvtMpTradeExPostEvaluationStatus
    buyer_actual_declared_time_saving_value_total: int | float | None
    seller_actual_required_compensation_total: int | float | None
    buyer_reference_payment_records: (
        tuple[OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord, ...] | None
    )
    seller_reference_compensation_records: (
        tuple[OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord, ...]
        | None
    )

    def __post_init__(self) -> None:
        if type(self.tvt_decision_timestep) is not int:
            raise RuntimeError(
                "tvt_decision_timestep must be a Python int, not bool; got "
                f"{self.tvt_decision_timestep!r}."
            )
        if self.tvt_decision_timestep < 0:
            raise RuntimeError(
                "tvt_decision_timestep must be >= 0; got "
                f"{self.tvt_decision_timestep!r}."
            )
        if not isinstance(self.node_name, str) or self.node_name == "":
            raise RuntimeError(
                "node_name must be a non-empty str; got "
                f"{self.node_name!r}."
            )
        if not isinstance(self.buyers_sorted, tuple):
            raise RuntimeError(
                "buyers_sorted must be a tuple; got type "
                f"{type(self.buyers_sorted).__name__}."
            )
        seen_buyers_sorted: set[OrderControlTvtVisitKey] = set()
        for visit_key in self.buyers_sorted:
            _require_history_visit_key(visit_key)
            if visit_key in seen_buyers_sorted:
                raise RuntimeError(
                    "buyers_sorted must not contain duplicate VisitKey "
                    f"{visit_key!r}."
                )
            seen_buyers_sorted.add(visit_key)
        if not isinstance(
            self.ex_post_evaluation_status,
            OrderControlTvtMpTradeExPostEvaluationStatus,
        ):
            raise RuntimeError(
                "ex_post_evaluation_status must be "
                "OrderControlTvtMpTradeExPostEvaluationStatus; got type "
                f"{type(self.ex_post_evaluation_status).__name__}."
            )
        status = self.ex_post_evaluation_status
        if status is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE:
            _validate_ex_post_evaluation_unavailable_shape(self)
            return
        if status is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE:
            _validate_ex_post_evaluation_infeasible_shape(self)
            return
        if status is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE:
            _validate_ex_post_evaluation_feasible_shape(self)
            return
        raise RuntimeError(
            f"unsupported ex_post_evaluation_status {status!r}."
        )


def _validate_ex_post_evaluation_unavailable_shape(
    result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> None:
    if result.buyer_actual_declared_time_saving_value_total is not None:
        raise RuntimeError(
            "EVALUATION_UNAVAILABLE requires "
            "buyer_actual_declared_time_saving_value_total to be None."
        )
    if result.seller_actual_required_compensation_total is not None:
        raise RuntimeError(
            "EVALUATION_UNAVAILABLE requires "
            "seller_actual_required_compensation_total to be None."
        )
    if result.buyer_reference_payment_records is not None:
        raise RuntimeError(
            "EVALUATION_UNAVAILABLE requires buyer_reference_payment_records "
            "to be None."
        )
    if result.seller_reference_compensation_records is not None:
        raise RuntimeError(
            "EVALUATION_UNAVAILABLE requires "
            "seller_reference_compensation_records to be None."
        )


def _validate_ex_post_evaluation_infeasible_shape(
    result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> None:
    _require_ex_post_evaluated_totals_present(result)
    _require_finite_number(
        result.buyer_actual_declared_time_saving_value_total,
        "buyer_actual_declared_time_saving_value_total",
    )
    _require_non_negative_money_number(
        result.seller_actual_required_compensation_total,
        "seller_actual_required_compensation_total",
    )
    buyer_records = _require_ex_post_buyer_record_tuple(result)
    seller_records = _require_ex_post_seller_record_tuple(result)
    for buyer_record in buyer_records:
        if buyer_record.reference_payment != 0:
            raise RuntimeError(
                "EX_POST_INFEASIBLE requires every buyer reference_payment "
                f"to be 0; got {buyer_record.reference_payment!r} for "
                f"VisitKey {buyer_record.visit_key!r}."
            )
    for seller_record in seller_records:
        if seller_record.reference_compensation != 0:
            raise RuntimeError(
                "EX_POST_INFEASIBLE requires every seller "
                "reference_compensation to be 0; got "
                f"{seller_record.reference_compensation!r} for VisitKey "
                f"{seller_record.visit_key!r}."
            )
    buyer_value_total = 0
    for buyer_record in buyer_records:
        buyer_value_total += buyer_record.buyer_actual_declared_time_saving_value
    if (
        buyer_value_total
        != result.buyer_actual_declared_time_saving_value_total
    ):
        raise RuntimeError(
            "EX_POST_INFEASIBLE requires buyer_actual_declared_time_saving_"
            "value_total to equal the sum of buyer record values; got "
            f"{result.buyer_actual_declared_time_saving_value_total!r}, "
            f"expected {buyer_value_total!r}."
        )
    seller_compensation_total = 0
    for seller_record in seller_records:
        seller_compensation_total += (
            seller_record.seller_actual_required_compensation
        )
    if (
        seller_compensation_total
        != result.seller_actual_required_compensation_total
    ):
        raise RuntimeError(
            "EX_POST_INFEASIBLE requires seller_actual_required_compensation_"
            "total to equal the sum of seller record values; got "
            f"{result.seller_actual_required_compensation_total!r}, "
            f"expected {seller_compensation_total!r}."
        )
    _validate_ex_post_buyer_records_match_buyers_sorted(
        result.buyers_sorted,
        buyer_records,
    )
    _validate_ex_post_record_visit_keys_no_duplicates_or_overlap(
        buyer_records,
        seller_records,
    )


def _validate_ex_post_evaluation_feasible_shape(
    result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> None:
    _require_ex_post_evaluated_totals_present(result)
    _require_positive_finite_number(
        result.buyer_actual_declared_time_saving_value_total,
        "buyer_actual_declared_time_saving_value_total",
    )
    _require_non_negative_money_number(
        result.seller_actual_required_compensation_total,
        "seller_actual_required_compensation_total",
    )
    buyer_records = _require_ex_post_buyer_record_tuple(result)
    seller_records = _require_ex_post_seller_record_tuple(result)
    buyer_value_total = 0
    for buyer_record in buyer_records:
        _require_positive_finite_number(
            buyer_record.buyer_actual_declared_time_saving_value,
            "buyer_actual_declared_time_saving_value",
        )
        _require_non_negative_money_number(
            buyer_record.reference_payment,
            "reference_payment",
        )
        buyer_value_total += buyer_record.buyer_actual_declared_time_saving_value
    if (
        buyer_value_total
        != result.buyer_actual_declared_time_saving_value_total
    ):
        raise RuntimeError(
            "EX_POST_FEASIBLE requires buyer_actual_declared_time_saving_"
            "value_total to equal the sum of buyer record values; got "
            f"{result.buyer_actual_declared_time_saving_value_total!r}, "
            f"expected {buyer_value_total!r}."
        )
    seller_compensation_total = 0
    for seller_record in seller_records:
        if (
            seller_record.reference_compensation
            != seller_record.seller_actual_required_compensation
        ):
            raise RuntimeError(
                "EX_POST_FEASIBLE requires reference_compensation to equal "
                "seller_actual_required_compensation for every seller; "
                f"VisitKey {seller_record.visit_key!r} has "
                f"{seller_record.reference_compensation!r} and "
                f"{seller_record.seller_actual_required_compensation!r}."
            )
        seller_compensation_total += (
            seller_record.seller_actual_required_compensation
        )
    if (
        seller_compensation_total
        != result.seller_actual_required_compensation_total
    ):
        raise RuntimeError(
            "EX_POST_FEASIBLE requires seller_actual_required_compensation_"
            "total to equal the sum of seller record values; got "
            f"{result.seller_actual_required_compensation_total!r}, "
            f"expected {seller_compensation_total!r}."
        )
    _validate_ex_post_buyer_records_match_buyers_sorted(
        result.buyers_sorted,
        buyer_records,
    )
    _validate_ex_post_record_visit_keys_no_duplicates_or_overlap(
        buyer_records,
        seller_records,
    )


def _require_ex_post_evaluated_totals_present(
    result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> None:
    if result.buyer_actual_declared_time_saving_value_total is None:
        raise RuntimeError(
            "evaluated ex-post status requires "
            "buyer_actual_declared_time_saving_value_total, not None."
        )
    if result.seller_actual_required_compensation_total is None:
        raise RuntimeError(
            "evaluated ex-post status requires "
            "seller_actual_required_compensation_total, not None."
        )


def _require_ex_post_buyer_record_tuple(
    result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> tuple[OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord, ...]:
    buyer_records = result.buyer_reference_payment_records
    if buyer_records is None:
        raise RuntimeError(
            "evaluated ex-post status requires buyer_reference_payment_records "
            "to be a tuple, not None."
        )
    if not isinstance(buyer_records, tuple):
        raise RuntimeError(
            "buyer_reference_payment_records must be a tuple; got type "
            f"{type(buyer_records).__name__}."
        )
    for buyer_record in buyer_records:
        if not isinstance(
            buyer_record,
            OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord,
        ):
            raise RuntimeError(
                "buyer_reference_payment_records must contain "
                "OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord "
                "elements only."
            )
    return buyer_records


def _require_ex_post_seller_record_tuple(
    result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> tuple[OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord, ...]:
    seller_records = result.seller_reference_compensation_records
    if seller_records is None:
        raise RuntimeError(
            "evaluated ex-post status requires "
            "seller_reference_compensation_records to be a tuple, not None."
        )
    if not isinstance(seller_records, tuple):
        raise RuntimeError(
            "seller_reference_compensation_records must be a tuple; got type "
            f"{type(seller_records).__name__}."
        )
    for seller_record in seller_records:
        if not isinstance(
            seller_record,
            OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord,
        ):
            raise RuntimeError(
                "seller_reference_compensation_records must contain "
                "OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord "
                "elements only."
            )
    return seller_records


def _validate_ex_post_buyer_records_match_buyers_sorted(
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    buyer_records: tuple[
        OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord,
        ...,
    ],
) -> None:
    if len(buyer_records) != len(buyers_sorted):
        raise RuntimeError(
            "buyer_reference_payment_records length must match "
            "buyers_sorted length; got "
            f"{len(buyer_records)!r} records and "
            f"{len(buyers_sorted)!r} buyers_sorted entries."
        )
    for index, expected_visit_key in enumerate(buyers_sorted):
        buyer_record = buyer_records[index]
        if buyer_record.visit_key != expected_visit_key:
            raise RuntimeError(
                "buyer_reference_payment_records must follow buyers_sorted "
                f"order; index {index} expected VisitKey "
                f"{expected_visit_key!r}, got {buyer_record.visit_key!r}."
            )


def _validate_ex_post_record_visit_keys_no_duplicates_or_overlap(
    buyer_records: tuple[
        OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord,
        ...,
    ],
    seller_records: tuple[
        OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord,
        ...,
    ],
) -> None:
    seen_buyer_visit_keys: set[OrderControlTvtVisitKey] = set()
    for buyer_record in buyer_records:
        if buyer_record.visit_key in seen_buyer_visit_keys:
            raise RuntimeError(
                "buyer_reference_payment_records must not contain duplicate "
                f"VisitKey {buyer_record.visit_key!r}."
            )
        seen_buyer_visit_keys.add(buyer_record.visit_key)
    seen_seller_visit_keys: set[OrderControlTvtVisitKey] = set()
    for seller_record in seller_records:
        if seller_record.visit_key in seen_seller_visit_keys:
            raise RuntimeError(
                "seller_reference_compensation_records must not contain "
                f"duplicate VisitKey {seller_record.visit_key!r}."
            )
        if seller_record.visit_key in seen_buyer_visit_keys:
            raise RuntimeError(
                "buyer and seller reference records must not share VisitKey "
                f"{seller_record.visit_key!r}."
            )
        seen_seller_visit_keys.add(seller_record.visit_key)


@dataclass
class OrderControlTvtMpActualPassageWaitEntry:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    role: OrderControlTvtMpActualPassageRole
    wait_status: OrderControlTvtMpActualPassageWaitStatus
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    true_vot_per_second: float
    baseline_minus_candidate_passage_timesteps: int | None
    baseline_minus_candidate_passage_seconds: int | float | None
    baseline_minus_candidate_time_value: int | float | None
    predicted_observation_status: OrderControlTvtMpCandidatePassageObservationStatus
    predicted_route_next_link_name: str
    common_frozen_input: OrderControlTvtMpActualPassageCommonFrozenInput
    monetary_frozen_input: OrderControlTvtMpActualPassageMonetaryFrozenInput | None
    actual_passage_observation_record: (
        OrderControlTvtMpActualPassageObservationRecord | None
    ) = None

    def __post_init__(self) -> None:
        """Check this object's shape only. Do not search logs or ledgers."""
        if not isinstance(
            self.common_frozen_input,
            OrderControlTvtMpActualPassageCommonFrozenInput,
        ):
            raise RuntimeError(
                "common_frozen_input must be "
                "OrderControlTvtMpActualPassageCommonFrozenInput; got type "
                f"{type(self.common_frozen_input).__name__}."
            )
        if (
            self.role is OrderControlTvtMpActualPassageRole.BUYER
            or self.role is OrderControlTvtMpActualPassageRole.SELLER
        ):
            if not isinstance(
                self.monetary_frozen_input,
                OrderControlTvtMpActualPassageMonetaryFrozenInput,
            ):
                raise RuntimeError(
                    f"{self.role.value} wait entry requires "
                    "OrderControlTvtMpActualPassageMonetaryFrozenInput; got "
                    f"{self.monetary_frozen_input!r}."
                )
            return
        if self.role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
            if self.monetary_frozen_input is not None:
                raise RuntimeError(
                    "nonparticipating wait entry must not carry a monetary "
                    "frozen input; None means no monetary contract."
                )
            return
        raise RuntimeError(
            "wait entry role must be buyer, seller, or nonparticipating; "
            f"got {self.role!r}."
        )


@dataclass
class OrderControlTvtMpActualPassageTradeWait:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    all_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    buyer_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    seller_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    nonparticipating_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    buyer_seller_actual_passage_completion_notified: bool = False


@dataclass
class OrderControlTvtMpActualPassageWaitRegistry:
    entries_by_node_name_and_visit_key: dict[
        tuple[str, OrderControlTvtVisitKey],
        OrderControlTvtMpActualPassageWaitEntry,
    ] = field(default_factory=dict)
    trades_by_transaction_key: dict[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpActualPassageTradeWait,
    ] = field(default_factory=dict)
    trade_ex_post_evaluation_results_by_transaction_key: dict[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpTradeExPostEvaluationResult,
    ] = field(default_factory=dict)
    # Not the evaluation-end timestep authority; prevents duplicate finalization.
    evaluation_end_unobserved_finalized_timestep: int | None = None
    # Not the evaluation-end timestep authority; prevents duplicate ex-post runs.
    trade_ex_post_evaluation_finalized_timestep: int | None = None


@dataclass(frozen=True)
class OrderControlTvtMpActualNodePassageRecord:
    """One successful real-world passage, in Node order. Not a trade rank.

    node_name stays on the history registry key. vehicle_name stays inside
    visit_key. Assigned rank and the formal route stay on the rank ledger.
    """

    visit_key: OrderControlTvtVisitKey
    actual_passage_timestep: int
    actual_route_next_link_name: str
    actual_node_passage_rank: int

    def __post_init__(self) -> None:
        _require_history_visit_key(self.visit_key)
        if type(self.actual_passage_timestep) is not int:
            raise RuntimeError(
                "actual_passage_timestep must be a Python int, not bool; "
                f"got {self.actual_passage_timestep!r}."
            )
        if self.actual_passage_timestep < 0:
            raise RuntimeError(
                "actual_passage_timestep must be >= 0; got "
                f"{self.actual_passage_timestep!r}."
            )
        if (
            not isinstance(self.actual_route_next_link_name, str)
            or self.actual_route_next_link_name == ""
        ):
            raise RuntimeError(
                "actual_route_next_link_name must be a non-empty str; got "
                f"{self.actual_route_next_link_name!r}."
            )
        if type(self.actual_node_passage_rank) is not int:
            raise RuntimeError(
                "actual_node_passage_rank must be a Python int, not bool; "
                f"got {self.actual_node_passage_rank!r}."
            )
        if self.actual_node_passage_rank < 1:
            raise RuntimeError(
                "actual_node_passage_rank must be >= 1; got "
                f"{self.actual_node_passage_rank!r}."
            )


@dataclass
class OrderControlTvtMpActualNodePassageHistoryRegistry:
    """Successful passages per Node. The next rank is the tuple length + 1."""

    records_by_node_name: dict[
        str,
        tuple[OrderControlTvtMpActualNodePassageRecord, ...],
    ] = field(default_factory=dict)


@dataclass(frozen=True)
class _PreparedTvtMpActualNodePassageHistoryUpdate:
    """One history tuple ready to assign. The live registry is unchanged."""

    registry: OrderControlTvtMpActualNodePassageHistoryRegistry
    node_name: str
    record: OrderControlTvtMpActualNodePassageRecord
    updated_node_records: tuple[OrderControlTvtMpActualNodePassageRecord, ...]


@dataclass(frozen=True)
class _PreparedTvtMpActualPassageObservationUpdate:
    """One actual passage observation ready to assign. Not yet assigned."""

    vehicle: object
    updated_order_exchange_log: list
    wait_entry: OrderControlTvtMpActualPassageWaitEntry
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus
    target_trade_wait: OrderControlTvtMpActualPassageTradeWait
    should_emit_buyer_seller_completion_notification: bool


def prepare_tvt_mp_actual_passage_observation(
    *,
    node,
    vehicle,
    visit_key,
    actual_outlink,
    actual_passage_timestep,
):
    """
    Build one actual passage observation, or return None when no entry waits.

    This does not move the vehicle, append the live log, or change the wait
    entry. A missing registry entry is a normal confirmed visit outside the
    selected trade scope.
    """
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    if not isinstance(registry, OrderControlTvtMpActualPassageWaitRegistry):
        raise RuntimeError(
            f"Node {node.name!r}: actual passage wait registry must be "
            "OrderControlTvtMpActualPassageWaitRegistry; got type "
            f"{type(registry).__name__}."
        )
    entry_key = (node.name, visit_key)
    wait_entry = registry.entries_by_node_name_and_visit_key.get(entry_key)
    if wait_entry is None:
        return None

    _require_waiting_entry_identity(
        wait_entry,
        node_name=node.name,
        visit_key=visit_key,
        vehicle=vehicle,
    )
    checked_actual_timestep = _require_actual_passage_timestep(
        actual_passage_timestep,
        wait_entry.tvt_decision_timestep,
        node.name,
        visit_key,
    )
    baseline_passage_timestep = _require_baseline_passage_timestep(
        wait_entry.baseline_passage_timestep,
        node.name,
        visit_key,
    )
    candidate_passage_timestep = _require_candidate_passage_timestep(
        wait_entry.candidate_passage_timestep,
        node.name,
        visit_key,
    )
    deltat = _require_positive_deltat(node.W.DELTAT, node.name)
    true_vot_per_second = _require_frozen_true_vot(
        wait_entry.true_vot_per_second,
        node.name,
        visit_key,
    )
    actual_route_next_link_name = _require_actual_route_name(
        actual_outlink,
        node.name,
        visit_key,
    )
    (
        baseline_minus_actual_passage_timesteps,
        baseline_minus_actual_passage_seconds,
        baseline_minus_actual_time_value,
    ) = _passage_difference_from_saved_timestep(
        baseline_passage_timestep,
        checked_actual_timestep,
        deltat,
        true_vot_per_second,
    )
    if candidate_passage_timestep is None:
        candidate_minus_actual_passage_timesteps = None
        candidate_minus_actual_passage_seconds = None
        candidate_minus_actual_time_value = None
    else:
        (
            candidate_minus_actual_passage_timesteps,
            candidate_minus_actual_passage_seconds,
            candidate_minus_actual_time_value,
        ) = _passage_difference_from_saved_timestep(
            candidate_passage_timestep,
            checked_actual_timestep,
            deltat,
            true_vot_per_second,
        )

    # baseline_minus_candidate is already stored. Do not recompute it.
    actual_observation_record = OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=wait_entry.tvt_decision_timestep,
        node_name=wait_entry.node_name,
        buyers_sorted=wait_entry.buyers_sorted,
        visit_key=wait_entry.visit_key,
        vehicle_name=wait_entry.vehicle_name,
        role=wait_entry.role,
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
        ),
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        true_vot_per_second=true_vot_per_second,
        predicted_observation_status=wait_entry.predicted_observation_status,
        predicted_route_next_link_name=wait_entry.predicted_route_next_link_name,
        baseline_minus_candidate_passage_timesteps=(
            wait_entry.baseline_minus_candidate_passage_timesteps
        ),
        baseline_minus_candidate_passage_seconds=(
            wait_entry.baseline_minus_candidate_passage_seconds
        ),
        baseline_minus_candidate_time_value=(
            wait_entry.baseline_minus_candidate_time_value
        ),
        baseline_minus_actual_passage_timesteps=(
            baseline_minus_actual_passage_timesteps
        ),
        baseline_minus_actual_passage_seconds=baseline_minus_actual_passage_seconds,
        baseline_minus_actual_time_value=baseline_minus_actual_time_value,
        candidate_minus_actual_passage_timesteps=(
            candidate_minus_actual_passage_timesteps
        ),
        candidate_minus_actual_passage_seconds=(
            candidate_minus_actual_passage_seconds
        ),
        candidate_minus_actual_time_value=candidate_minus_actual_time_value,
        actual_passage_timestep=checked_actual_timestep,
        actual_route_next_link_name=actual_route_next_link_name,
    )
    if not isinstance(vehicle.order_exchange_log, list):
        raise RuntimeError(
            f"Node {node.name!r}: Vehicle {vehicle.name!r} "
            "order_exchange_log must be a list; got type "
            f"{type(vehicle.order_exchange_log).__name__}."
        )
    updated_order_exchange_log = list(vehicle.order_exchange_log)
    updated_order_exchange_log.append(actual_observation_record)
    committed_wait_status = (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    trade_wait, should_emit_notification = (
        _prepare_buyer_seller_completion_notification(
            registry=registry,
            node_name=node.name,
            visit_key=visit_key,
            wait_entry=wait_entry,
            actual_passage_observation_record=actual_observation_record,
            committed_wait_status=committed_wait_status,
        )
    )
    return _PreparedTvtMpActualPassageObservationUpdate(
        vehicle=vehicle,
        updated_order_exchange_log=updated_order_exchange_log,
        wait_entry=wait_entry,
        actual_passage_observation_record=actual_observation_record,
        committed_wait_status=committed_wait_status,
        target_trade_wait=trade_wait,
        should_emit_buyer_seller_completion_notification=should_emit_notification,
    )


def commit_tvt_mp_actual_passage_observation(
    prepared_update,
) -> OrderControlTvtMpActualPassageTradeWait | None:
    """Assign one prepared observation. No search, check, or recalculation."""
    prepared_update.vehicle.order_exchange_log = (
        prepared_update.updated_order_exchange_log
    )
    prepared_update.wait_entry.actual_passage_observation_record = (
        prepared_update.actual_passage_observation_record
    )
    prepared_update.wait_entry.wait_status = prepared_update.committed_wait_status
    if not prepared_update.should_emit_buyer_seller_completion_notification:
        return None
    prepared_update.target_trade_wait.buyer_seller_actual_passage_completion_notified = (
        True
    )
    return prepared_update.target_trade_wait


def _require_waiting_entry_identity(
    wait_entry,
    *,
    node_name,
    visit_key,
    vehicle,
) -> None:
    if wait_entry.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: wait entry node_name "
            f"{wait_entry.node_name!r} does not match."
        )
    if wait_entry.visit_key != visit_key:
        raise RuntimeError(
            f"Node {node_name!r}: wait entry VisitKey {wait_entry.visit_key!r} "
            f"does not match {visit_key!r}."
        )
    if wait_entry.vehicle_name != vehicle.name:
        raise RuntimeError(
            f"Node {node_name!r}: wait entry vehicle_name "
            f"{wait_entry.vehicle_name!r} does not match {vehicle.name!r}."
        )
    if (
        wait_entry.wait_status
        is not OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} wait_status is "
            f"{wait_entry.wait_status!r}, not WAITING_FOR_ACTUAL_PASSAGE."
        )
    if wait_entry.actual_passage_observation_record is not None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} already has an "
            "actual passage observation record."
        )


def _require_actual_passage_timestep(
    value,
    decision_timestep,
    node_name,
    visit_key,
) -> int:
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "actual_passage_timestep must be a Python int, not bool; got "
            f"{value!r}."
        )
    if type(decision_timestep) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "tvt_decision_timestep must be a Python int, not bool; got "
            f"{decision_timestep!r}."
        )
    if value < decision_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            f"actual_passage_timestep {value!r} is before "
            f"tvt_decision_timestep {decision_timestep!r}."
        )
    return value


def _require_baseline_passage_timestep(value, node_name, visit_key) -> int:
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "baseline_passage_timestep must be a Python int, not bool; got "
            f"{value!r}."
        )
    return value


def _require_candidate_passage_timestep(value, node_name, visit_key):
    if value is None:
        return None
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "candidate_passage_timestep must be a Python int or None; got "
            f"{value!r}."
        )
    return value


def _require_positive_deltat(value, node_name):
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: DELTAT must be a Python int or float, not "
            f"bool or None; got {value!r}."
        )
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(
            f"Node {node_name!r}: DELTAT must be finite and > 0; got {value!r}."
        )
    return value


def _require_frozen_true_vot(value, node_name, visit_key):
    """Use the value stored on the wait entry. Do not read Vehicle.vot_true."""
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} true_vot_per_second "
            f"must be a Python int or float, not bool or None; got {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} true_vot_per_second "
            f"must be finite and >= 0; got {value!r}."
        )
    return value


def _require_actual_route_name(actual_outlink, node_name, visit_key) -> str:
    route_name = getattr(actual_outlink, "name", None)
    if not isinstance(route_name, str) or route_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} actual outlink name "
            f"must be a non-empty str; got {route_name!r}."
        )
    return route_name


def _passage_difference_from_saved_timestep(
    earlier_saved_timestep,
    actual_passage_timestep,
    deltat,
    true_vot_per_second,
):
    """saved timestep minus actual timestep, then seconds and time value."""
    passage_timesteps = earlier_saved_timestep - actual_passage_timestep
    passage_seconds = passage_timesteps * deltat
    time_value = passage_seconds * true_vot_per_second
    return passage_timesteps, passage_seconds, time_value


def _transaction_key_from_wait_entry(
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
) -> tuple[int, str, tuple[OrderControlTvtVisitKey, ...]]:
    return (
        wait_entry.tvt_decision_timestep,
        wait_entry.node_name,
        wait_entry.buyers_sorted,
    )


def _prepare_buyer_seller_completion_notification(
    *,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord,
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus,
) -> tuple[OrderControlTvtMpActualPassageTradeWait, bool]:
    transaction_key = _transaction_key_from_wait_entry(wait_entry)
    trade_wait = registry.trades_by_transaction_key.get(transaction_key)
    if trade_wait is None:
        raise RuntimeError(
            f"Node {node_name!r}: no TradeWait for transaction key "
            f"{transaction_key!r}."
        )
    _validate_trade_wait_matches_wait_entry(trade_wait, wait_entry, node_name)
    _validate_trade_wait_buyer_seller_visit_keys(trade_wait, node_name)
    _validate_current_visit_trade_membership(
        trade_wait,
        wait_entry,
        node_name,
        visit_key,
    )
    _validate_role_visit_keys_for_trade(
        registry,
        trade_wait,
        node_name,
    )
    _validate_saved_wait_entries_for_trade(
        registry,
        trade_wait,
        node_name,
        current_visit_key=visit_key,
    )
    all_buyer_seller_complete_after_commit = (
        _all_buyer_seller_visits_complete_after_commit(
            trade_wait,
            registry,
            node_name,
            current_visit_key=visit_key,
            actual_passage_observation_record=actual_passage_observation_record,
            committed_wait_status=committed_wait_status,
        )
    )
    _validate_completion_flag_consistency(
        trade_wait,
        registry,
        node_name,
        wait_entry,
    )
    should_emit = (
        all_buyer_seller_complete_after_commit
        and not trade_wait.buyer_seller_actual_passage_completion_notified
    )
    return trade_wait, should_emit


def _validate_trade_wait_matches_wait_entry(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
) -> None:
    if trade_wait.tvt_decision_timestep != wait_entry.tvt_decision_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait tvt_decision_timestep "
            f"{trade_wait.tvt_decision_timestep!r} does not match wait entry "
            f"{wait_entry.tvt_decision_timestep!r}."
        )
    if trade_wait.node_name != wait_entry.node_name:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait node_name {trade_wait.node_name!r} "
            f"does not match wait entry {wait_entry.node_name!r}."
        )
    if trade_wait.buyers_sorted != wait_entry.buyers_sorted:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait buyers_sorted does not match "
            "wait entry buyers_sorted."
        )


def _validate_trade_wait_buyer_seller_visit_keys(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    node_name: str,
) -> None:
    if len(trade_wait.buyer_visit_keys) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait buyer_visit_keys must not be empty."
        )
    if len(trade_wait.seller_visit_keys) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait seller_visit_keys must not be empty."
        )
    duplicate_buyer_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.buyer_visit_keys,
    )
    if duplicate_buyer_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait buyer_visit_keys contains duplicate "
            f"VisitKey {duplicate_buyer_visit_key!r}."
        )
    duplicate_seller_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.seller_visit_keys,
    )
    if duplicate_seller_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait seller_visit_keys contains duplicate "
            f"VisitKey {duplicate_seller_visit_key!r}."
        )
    duplicate_nonparticipating_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.nonparticipating_visit_keys,
    )
    if duplicate_nonparticipating_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait nonparticipating_visit_keys contains "
            f"duplicate VisitKey {duplicate_nonparticipating_visit_key!r}."
        )
    duplicate_all_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.all_visit_keys,
    )
    if duplicate_all_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait all_visit_keys contains duplicate "
            f"VisitKey {duplicate_all_visit_key!r}."
        )
    shared_buyer_seller_visit_key = _find_shared_visit_key_between_sequences(
        trade_wait.buyer_visit_keys,
        trade_wait.seller_visit_keys,
    )
    if shared_buyer_seller_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait has VisitKey shared by buyer and "
            f"seller role lists: {shared_buyer_seller_visit_key!r}."
        )
    shared_buyer_nonparticipating_visit_key = _find_shared_visit_key_between_sequences(
        trade_wait.buyer_visit_keys,
        trade_wait.nonparticipating_visit_keys,
    )
    if shared_buyer_nonparticipating_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait has VisitKey shared by buyer and "
            "nonparticipating role lists: "
            f"{shared_buyer_nonparticipating_visit_key!r}."
        )
    shared_seller_nonparticipating_visit_key = _find_shared_visit_key_between_sequences(
        trade_wait.seller_visit_keys,
        trade_wait.nonparticipating_visit_keys,
    )
    if shared_seller_nonparticipating_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait has VisitKey shared by seller and "
            "nonparticipating role lists: "
            f"{shared_seller_nonparticipating_visit_key!r}."
        )
    for visit_key in trade_wait.buyer_visit_keys:
        if not _visit_key_listed_in_sequence(visit_key, trade_wait.all_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait buyer VisitKey {visit_key!r} is "
                "not listed in all_visit_keys."
            )
    for visit_key in trade_wait.seller_visit_keys:
        if not _visit_key_listed_in_sequence(visit_key, trade_wait.all_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait seller VisitKey {visit_key!r} is "
                "not listed in all_visit_keys."
            )
    for visit_key in trade_wait.nonparticipating_visit_keys:
        if not _visit_key_listed_in_sequence(visit_key, trade_wait.all_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait nonparticipating VisitKey "
                f"{visit_key!r} is not listed in all_visit_keys."
            )
    for visit_key in trade_wait.all_visit_keys:
        in_buyer_visit_keys = _visit_key_listed_in_sequence(
            visit_key,
            trade_wait.buyer_visit_keys,
        )
        in_seller_visit_keys = _visit_key_listed_in_sequence(
            visit_key,
            trade_wait.seller_visit_keys,
        )
        in_nonparticipating_visit_keys = _visit_key_listed_in_sequence(
            visit_key,
            trade_wait.nonparticipating_visit_keys,
        )
        role_list_count = 0
        if in_buyer_visit_keys:
            role_list_count += 1
        if in_seller_visit_keys:
            role_list_count += 1
        if in_nonparticipating_visit_keys:
            role_list_count += 1
        if role_list_count == 0:
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait all_visit_keys contains VisitKey "
                f"{visit_key!r} that is not listed in buyer_visit_keys, "
                "seller_visit_keys, or nonparticipating_visit_keys."
            )


def _find_duplicate_visit_key_in_sequence(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    for visit_key in visit_keys:
        if visit_key in seen_visit_keys:
            return visit_key
        seen_visit_keys.add(visit_key)
    return None


def _find_shared_visit_key_between_sequences(
    left_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    right_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    for left_visit_key in left_visit_keys:
        if _visit_key_listed_in_sequence(left_visit_key, right_visit_keys):
            return left_visit_key
    return None


def _visit_key_listed_in_sequence(
    visit_key: OrderControlTvtVisitKey,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> bool:
    for listed_visit_key in visit_keys:
        if listed_visit_key == visit_key:
            return True
    return False


def _validate_current_visit_trade_membership(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    if visit_key not in trade_wait.all_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is not listed in "
            "TradeWait all_visit_keys."
        )
    role = wait_entry.role
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        if visit_key not in trade_wait.buyer_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {visit_key!r} is not in "
                "TradeWait buyer_visit_keys."
            )
        return
    if role is OrderControlTvtMpActualPassageRole.SELLER:
        if visit_key not in trade_wait.seller_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: seller VisitKey {visit_key!r} is not in "
                "TradeWait seller_visit_keys."
            )
        return
    if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        if visit_key not in trade_wait.nonparticipating_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: nonparticipating VisitKey {visit_key!r} "
                "is not in TradeWait nonparticipating_visit_keys."
            )
        return
    raise RuntimeError(
        f"Node {node_name!r}: VisitKey {visit_key!r} has unknown role "
        f"{role!r}."
    )


def _validate_role_visit_keys_for_trade(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    node_name: str,
) -> None:
    for visit_key in trade_wait.buyer_visit_keys:
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="buyer",
        )
        if entry.role is not OrderControlTvtMpActualPassageRole.BUYER:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is listed as "
                "buyer but wait entry role is not BUYER."
            )
    for visit_key in trade_wait.seller_visit_keys:
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="seller",
        )
        if entry.role is not OrderControlTvtMpActualPassageRole.SELLER:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is listed as "
                "seller but wait entry role is not SELLER."
            )


def _require_wait_entry_for_visit_key(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    *,
    role_label: str,
) -> OrderControlTvtMpActualPassageWaitEntry:
    entry = registry.entries_by_node_name_and_visit_key.get((node_name, visit_key))
    if entry is None:
        raise RuntimeError(
            f"Node {node_name!r}: no WaitEntry for {role_label} VisitKey "
            f"{visit_key!r}."
        )
    return entry


def _validate_saved_wait_entries_for_trade(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    node_name: str,
    *,
    current_visit_key: OrderControlTvtVisitKey,
) -> None:
    for visit_key in trade_wait.buyer_visit_keys + trade_wait.seller_visit_keys:
        if visit_key == current_visit_key:
            continue
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="buyer or seller",
        )
        _validate_wait_entry_identity_matches_trade(trade_wait, entry, node_name)
        _validate_saved_wait_entry_observation_consistency(
            entry,
            node_name,
            visit_key,
        )


def _validate_wait_entry_identity_matches_trade(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
) -> None:
    if entry.tvt_decision_timestep != trade_wait.tvt_decision_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: WaitEntry transaction identity "
            "tvt_decision_timestep does not match TradeWait."
        )
    if entry.node_name != trade_wait.node_name:
        raise RuntimeError(
            f"Node {node_name!r}: WaitEntry transaction identity node_name "
            "does not match TradeWait."
        )
    if entry.buyers_sorted != trade_wait.buyers_sorted:
        raise RuntimeError(
            f"Node {node_name!r}: WaitEntry transaction identity buyers_sorted "
            "does not match TradeWait."
        )


def _validate_saved_wait_entry_observation_consistency(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    _validate_wait_entry_formal_three_state(entry, node_name, visit_key)


def _validate_wait_entry_formal_three_state(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    """Accept only waiting, observed, or evaluation-end unobserved."""
    waiting = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    observed = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    evaluation_end_unobserved = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    )
    record = entry.actual_passage_observation_record
    if waiting:
        if record is not None:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is "
                "WAITING_FOR_ACTUAL_PASSAGE but already has an actual passage "
                "observation record."
            )
        return
    if observed:
        if record is None:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is "
                "ACTUAL_PASSAGE_OBSERVED but has no actual passage observation "
                "record."
            )
        if (
            record.observation_status
            is not OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} wait_status is "
                "ACTUAL_PASSAGE_OBSERVED but observation record status is "
                f"{record.observation_status!r}."
            )
        if type(record.actual_passage_timestep) is not int:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} observed record "
                "actual_passage_timestep must be a Python int; got "
                f"{record.actual_passage_timestep!r}."
            )
        if (
            not isinstance(record.actual_route_next_link_name, str)
            or record.actual_route_next_link_name == ""
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} observed record "
                "actual_route_next_link_name must be a non-empty str; got "
                f"{record.actual_route_next_link_name!r}."
            )
        return
    if evaluation_end_unobserved:
        if record is None:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is "
                "ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END but has no "
                "actual passage observation record."
            )
        if (
            record.observation_status
            is not OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} wait_status is "
                "ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END but observation "
                f"record status is {record.observation_status!r}."
            )
        if record.actual_passage_timestep is not None:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} evaluation-end "
                "unobserved record actual_passage_timestep must be None; got "
                f"{record.actual_passage_timestep!r}."
            )
        if record.actual_route_next_link_name is not None:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} evaluation-end "
                "unobserved record actual_route_next_link_name must be None; "
                f"got {record.actual_route_next_link_name!r}."
            )
        actual_side_fields = (
            record.baseline_minus_actual_passage_timesteps,
            record.baseline_minus_actual_passage_seconds,
            record.baseline_minus_actual_time_value,
            record.candidate_minus_actual_passage_timesteps,
            record.candidate_minus_actual_passage_seconds,
            record.candidate_minus_actual_time_value,
        )
        for field_value in actual_side_fields:
            if field_value is not None:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {visit_key!r} evaluation-end "
                    "unobserved record actual-side field must be None; got "
                    f"{field_value!r}."
                )
        return
    raise RuntimeError(
        f"Node {node_name!r}: VisitKey {visit_key!r} has unknown wait_status "
        f"{entry.wait_status!r}."
    )


def _all_buyer_seller_visits_complete_after_commit(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    *,
    current_visit_key: OrderControlTvtVisitKey,
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord,
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus,
) -> bool:
    for visit_key in trade_wait.buyer_visit_keys:
        if not _visit_complete_after_commit(
            visit_key,
            registry,
            node_name,
            current_visit_key=current_visit_key,
            actual_passage_observation_record=actual_passage_observation_record,
            committed_wait_status=committed_wait_status,
        ):
            return False
    for visit_key in trade_wait.seller_visit_keys:
        if not _visit_complete_after_commit(
            visit_key,
            registry,
            node_name,
            current_visit_key=current_visit_key,
            actual_passage_observation_record=actual_passage_observation_record,
            committed_wait_status=committed_wait_status,
        ):
            return False
    return True


def _all_buyer_seller_visits_complete_on_live_state(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
) -> bool:
    for visit_key in trade_wait.buyer_visit_keys + trade_wait.seller_visit_keys:
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="buyer or seller",
        )
        if (
            entry.wait_status
            is not OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
            or entry.actual_passage_observation_record is None
        ):
            return False
    return True


def _visit_complete_after_commit(
    visit_key: OrderControlTvtVisitKey,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    *,
    current_visit_key: OrderControlTvtVisitKey,
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord,
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus,
) -> bool:
    if visit_key == current_visit_key:
        return (
            committed_wait_status
            is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
            and actual_passage_observation_record is not None
        )
    entry = _require_wait_entry_for_visit_key(
        registry,
        node_name,
        visit_key,
        role_label="buyer or seller",
    )
    return (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
        and entry.actual_passage_observation_record is not None
    )


def _validate_completion_flag_consistency(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
) -> None:
    if trade_wait.buyer_seller_actual_passage_completion_notified:
        all_buyer_seller_complete_on_live_state = (
            _all_buyer_seller_visits_complete_on_live_state(
                trade_wait,
                registry,
                node_name,
            )
        )
        if not all_buyer_seller_complete_on_live_state:
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait completion flag is True but "
                "buyer and seller are not all complete on live saved state "
                "before this commit."
            )
    if wait_entry.role is not OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        return
    all_buyer_seller_already_complete = (
        _all_buyer_seller_visits_complete_on_live_state(
            trade_wait,
            registry,
            node_name,
        )
    )
    if (
        all_buyer_seller_already_complete
        and not trade_wait.buyer_seller_actual_passage_completion_notified
    ):
        raise RuntimeError(
            f"Node {node_name!r}: buyer and seller are already complete but "
            "TradeWait completion flag is still False during nonparticipating "
            "passage."
        )


def _require_history_visit_key(visit_key) -> OrderControlTvtVisitKey:
    """Check the VisitKey shape only. Do not look up a vehicle or a ledger."""
    if not isinstance(visit_key, tuple) or len(visit_key) != 2:
        raise RuntimeError(
            "visit_key must be a length-2 tuple (vehicle_name, visit_id); "
            f"got {visit_key!r}."
        )
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            "visit_key vehicle_name must be a non-empty str; "
            f"got {vehicle_name!r}."
        )
    if type(visit_id) is not int:
        raise RuntimeError(
            "visit_key visit_id must be a Python int, not bool; "
            f"got {visit_id!r}."
        )
    if visit_id < 1:
        raise RuntimeError(
            f"visit_key visit_id must be >= 1; got {visit_id!r}."
        )
    return visit_key


def _vehicle_name_for_history(vehicle) -> str:
    if isinstance(vehicle, str):
        vehicle_name = vehicle
    else:
        vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            "vehicle name must be a non-empty str; "
            f"got {vehicle_name!r}."
        )
    return vehicle_name


def _require_real_world_for_passage_history(node) -> None:
    collector = getattr(node.W, "_order_control_baseline_collector", None)
    if collector is not None:
        raise RuntimeError(
            f"Node {node.name!r}: node passage history is recorded on the "
            "real world only. A baseline fork does not prepare it."
        )


def _require_passage_history_registry(node):
    registry = getattr(
        node.W,
        "order_control_tvt_mp_actual_node_passage_history_registry",
        None,
    )
    if not isinstance(registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError(
            f"Node {node.name!r}: node passage history registry must be "
            "OrderControlTvtMpActualNodePassageHistoryRegistry; got type "
            f"{type(registry).__name__}."
        )
    if not isinstance(registry.records_by_node_name, dict):
        raise RuntimeError(
            f"Node {node.name!r}: node passage history records_by_node_name "
            "must be a dict; got type "
            f"{type(registry.records_by_node_name).__name__}."
        )
    return registry


def _require_history_node_name(node) -> str:
    node_name = getattr(node, "name", None)
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"node name must be a non-empty str; got {node_name!r}."
        )
    return node_name


def _require_history_passage_timestep(actual_passage_timestep, node) -> int:
    if type(actual_passage_timestep) is not int:
        raise RuntimeError(
            f"Node {node.name!r}: actual_passage_timestep must be a Python "
            f"int, not bool; got {actual_passage_timestep!r}."
        )
    if actual_passage_timestep < 0:
        raise RuntimeError(
            f"Node {node.name!r}: actual_passage_timestep must be >= 0; got "
            f"{actual_passage_timestep!r}."
        )
    if actual_passage_timestep != node.W.T:
        raise RuntimeError(
            f"Node {node.name!r}: actual_passage_timestep "
            f"{actual_passage_timestep!r} does not match World timestep "
            f"{node.W.T!r}."
        )
    return actual_passage_timestep


def _require_registered_history_outlink(node, actual_outlink, visit_key) -> str:
    route_name = getattr(actual_outlink, "name", None)
    if not isinstance(route_name, str) or route_name == "":
        raise RuntimeError(
            f"Node {node.name!r}: VisitKey {visit_key!r} actual outlink name "
            f"must be a non-empty str; got {route_name!r}."
        )
    outlink_is_registered = False
    registered_outlinks = getattr(node, "outlinks", None)
    if isinstance(registered_outlinks, dict):
        for registered_outlink in registered_outlinks.values():
            if registered_outlink is actual_outlink:
                outlink_is_registered = True
                break
    if not outlink_is_registered:
        raise RuntimeError(
            f"Node {node.name!r}: VisitKey {visit_key!r} actual outlink "
            f"{route_name!r} is not a registered outlink of this node."
        )
    return route_name


def _require_visit_confirmed_on_node_ledger(node, visit_key) -> None:
    """Confirm the visit is on this node's ledger. Do not copy its rank."""
    ledgers = getattr(node.W, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(ledgers, dict) or node.name not in ledgers:
        raise RuntimeError(
            f"Node {node.name!r}: VisitKey {visit_key!r} is not confirmed "
            "on this node's rank ledger."
        )
    rank_state = ledgers[node.name]
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(
            f"Node {node.name!r}: VisitKey {visit_key!r} is not confirmed "
            "on this node's rank ledger."
        )
    if rank_state.node_name != node.name:
        raise RuntimeError(
            f"Node {node.name!r}: VisitKey {visit_key!r} is not confirmed "
            "on this node's rank ledger."
        )
    if not rank_state.is_confirmed(visit_key):
        raise RuntimeError(
            f"Node {node.name!r}: VisitKey {visit_key!r} is not confirmed "
            "on this node's rank ledger."
        )


def _require_existing_node_passage_records(node_name, stored_records):
    """Read one node's saved history. Do not sort it or change it."""
    if not isinstance(stored_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: node passage history must be a tuple; got "
            f"type {type(stored_records).__name__}."
        )
    seen_visit_keys = []
    expected_rank = 1
    for record in stored_records:
        if not isinstance(record, OrderControlTvtMpActualNodePassageRecord):
            raise RuntimeError(
                f"Node {node_name!r}: node passage history contains "
                f"{type(record).__name__}, not "
                "OrderControlTvtMpActualNodePassageRecord."
            )
        if record.actual_node_passage_rank != expected_rank:
            raise RuntimeError(
                f"Node {node_name!r}: node passage history rank "
                f"{record.actual_node_passage_rank!r} is not the continuous "
                f"rank {expected_rank}."
            )
        if record.visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: node passage history already contains "
                f"duplicate VisitKey {record.visit_key!r}."
            )
        seen_visit_keys.append(record.visit_key)
        expected_rank = expected_rank + 1
    return stored_records, seen_visit_keys


def prepare_tvt_mp_actual_node_passage_history(
    *,
    node,
    vehicle,
    visit_key,
    actual_outlink,
    actual_passage_timestep,
):
    """Build one node-passage history update. Do not change live state.

    The next rank is the saved tuple length plus one. This does not move
    the vehicle, update clearance, or append the history. Physical transfer
    calls this before the move, and only on the real world.
    """
    _require_real_world_for_passage_history(node)
    registry = _require_passage_history_registry(node)
    node_name = _require_history_node_name(node)
    checked_visit_key = _require_history_visit_key(visit_key)
    vehicle_name = _vehicle_name_for_history(vehicle)
    if checked_visit_key[0] != vehicle_name:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey vehicle_name "
            f"{checked_visit_key[0]!r} does not match {vehicle_name!r}."
        )
    checked_timestep = _require_history_passage_timestep(
        actual_passage_timestep,
        node,
    )
    route_name = _require_registered_history_outlink(
        node,
        actual_outlink,
        checked_visit_key,
    )
    _require_visit_confirmed_on_node_ledger(node, checked_visit_key)

    stored_records = registry.records_by_node_name.get(node_name, ())
    existing_records, seen_visit_keys = _require_existing_node_passage_records(
        node_name,
        stored_records,
    )
    if checked_visit_key in seen_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {checked_visit_key!r} is already "
            "in this node's passage history."
        )
    new_rank = len(existing_records) + 1
    record = OrderControlTvtMpActualNodePassageRecord(
        visit_key=checked_visit_key,
        actual_passage_timestep=checked_timestep,
        actual_route_next_link_name=route_name,
        actual_node_passage_rank=new_rank,
    )
    if record.actual_node_passage_rank != len(existing_records) + 1:
        raise RuntimeError(
            f"Node {node_name!r}: new passage rank "
            f"{record.actual_node_passage_rank!r} is not "
            f"{len(existing_records) + 1}."
        )
    updated_node_records = existing_records + (record,)
    return _PreparedTvtMpActualNodePassageHistoryUpdate(
        registry=registry,
        node_name=node_name,
        record=record,
        updated_node_records=updated_node_records,
    )


def commit_tvt_mp_actual_node_passage_history(prepared_update) -> None:
    """Assign one prepared node history tuple.

    Does not sort, recompute ranks, search the ledger, or rebuild the
    record. This assignment is separate from the physical move and from
    the actual observation commit.
    """
    if not isinstance(
        prepared_update,
        _PreparedTvtMpActualNodePassageHistoryUpdate,
    ):
        raise RuntimeError(
            "prepared node passage history update must be "
            "_PreparedTvtMpActualNodePassageHistoryUpdate; got type "
            f"{type(prepared_update).__name__}."
        )
    prepared_update.registry.records_by_node_name[prepared_update.node_name] = (
        prepared_update.updated_node_records
    )


@dataclass(frozen=True)
class _PreparedTvtMpActualPassageEvaluationEndUnobservedFinalization:
    """Prepared evaluation-end unobserved updates. Live registry unchanged."""

    wait_registry: OrderControlTvtMpActualPassageWaitRegistry
    waiting_entry_updates: tuple[
        tuple[
            OrderControlTvtMpActualPassageWaitEntry,
            OrderControlTvtMpActualPassageObservationRecord,
        ],
        ...,
    ]
    evaluation_end_unobserved_finalized_timestep: int


def _require_real_world_for_evaluation_end_unobserved(world) -> None:
    baseline_collector = getattr(world, "_order_control_baseline_collector", None)
    if baseline_collector is not None:
        raise RuntimeError(
            "evaluation-end unobserved finalization runs on the real world only; "
            "a baseline fork must not finalize unobserved waits."
        )


def _require_evaluation_end_timestep_for_unobserved(world) -> int:
    require_timestep = getattr(world, "_require_tvt_evaluation_end_timestep", None)
    if require_timestep is None:
        raise RuntimeError(
            "World is missing _require_tvt_evaluation_end_timestep."
        )
    evaluation_end_timestep = require_timestep()
    if evaluation_end_timestep is None:
        raise ValueError(
            "order_control_tvt_evaluation_end_timestep must be None or a "
            "Python int greater than or equal to 0 and less than TSIZE; "
            f"got None, TSIZE={world.TSIZE}."
        )
    return evaluation_end_timestep


def _require_world_timestep_matches_evaluation_end_plus_one(
    world,
    evaluation_end_timestep: int,
) -> None:
    if type(world.T) is not int:
        raise RuntimeError(
            f"World.T must be a Python int, not bool; got {world.T!r}."
        )
    expected_timestep = evaluation_end_timestep + 1
    if world.T != expected_timestep:
        raise RuntimeError(
            "evaluation-end unobserved finalization requires "
            f"World.T == evaluation_end_timestep + 1; got World.T={world.T!r}, "
            f"evaluation_end_timestep={evaluation_end_timestep!r}."
        )


def _require_wait_registry_not_already_finalized(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
) -> None:
    finalized = registry.evaluation_end_unobserved_finalized_timestep
    if finalized is not None:
        if type(finalized) is not int:
            raise RuntimeError(
                "evaluation_end_unobserved_finalized_timestep must be a Python "
                f"int or None; got {finalized!r}."
            )
        raise RuntimeError(
            "evaluation-end unobserved finalization was already completed for "
            f"timestep {finalized!r}."
        )


def _require_no_partial_evaluation_end_unobserved_entries(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
) -> None:
    for entry_key, entry in registry.entries_by_node_name_and_visit_key.items():
        node_name = entry_key[0]
        visit_key = entry_key[1]
        if (
            entry.wait_status
            is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is already "
                "ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END but "
                "evaluation_end_unobserved_finalized_timestep is still None."
            )


def _require_wait_and_history_registries_for_evaluation_end(world):
    wait_registry = getattr(
        world,
        "order_control_tvt_mp_actual_passage_wait_registry",
        None,
    )
    if not isinstance(wait_registry, OrderControlTvtMpActualPassageWaitRegistry):
        raise RuntimeError(
            "order_control_tvt_mp_actual_passage_wait_registry must be "
            "OrderControlTvtMpActualPassageWaitRegistry; got type "
            f"{type(wait_registry).__name__}."
        )
    history_registry = getattr(
        world,
        "order_control_tvt_mp_actual_node_passage_history_registry",
        None,
    )
    if not isinstance(history_registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError(
            "order_control_tvt_mp_actual_node_passage_history_registry must be "
            "OrderControlTvtMpActualNodePassageHistoryRegistry; got type "
            f"{type(history_registry).__name__}."
        )
    if not isinstance(
        wait_registry.entries_by_node_name_and_visit_key,
        dict,
    ):
        raise RuntimeError(
            "entries_by_node_name_and_visit_key must be a dict; got type "
            f"{type(wait_registry.entries_by_node_name_and_visit_key).__name__}."
        )
    if not isinstance(wait_registry.trades_by_transaction_key, dict):
        raise RuntimeError(
            "trades_by_transaction_key must be a dict; got type "
            f"{type(wait_registry.trades_by_transaction_key).__name__}."
        )
    return wait_registry, history_registry


def _validate_all_saved_node_passage_histories(
    history_registry: OrderControlTvtMpActualNodePassageHistoryRegistry,
) -> None:
    node_names = sorted(history_registry.records_by_node_name.keys())
    for node_name in node_names:
        stored_records = history_registry.records_by_node_name[node_name]
        _require_existing_node_passage_records(node_name, stored_records)


def _node_history_contains_visit_key(
    history_registry: OrderControlTvtMpActualNodePassageHistoryRegistry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> bool:
    stored_records = history_registry.records_by_node_name.get(node_name, ())
    for record in stored_records:
        if record.visit_key == visit_key:
            return True
    return False


def _validate_wait_entry_matches_node_passage_history(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    history_registry: OrderControlTvtMpActualNodePassageHistoryRegistry,
) -> None:
    has_history = _node_history_contains_visit_key(
        history_registry,
        node_name,
        visit_key,
    )
    waiting = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    observed = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    if observed and not has_history:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is observed but has "
            "no matching node passage history record."
        )
    if waiting and has_history:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is waiting but "
            "already has a node passage history record."
        )


def _sorted_trade_items(
    trades_by_transaction_key: dict[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpActualPassageTradeWait,
    ],
):
    transaction_keys = list(trades_by_transaction_key.keys())
    transaction_keys.sort()
    sorted_items = []
    for transaction_key in transaction_keys:
        trade_wait = trades_by_transaction_key[transaction_key]
        sorted_items.append((transaction_key, trade_wait))
    return sorted_items


def _validate_trade_transaction_key_matches_trade_wait(
    transaction_key: tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
) -> None:
    expected_key = (
        trade_wait.tvt_decision_timestep,
        trade_wait.node_name,
        trade_wait.buyers_sorted,
    )
    if transaction_key != expected_key:
        raise RuntimeError(
            f"TradeWait transaction key {transaction_key!r} does not match "
            f"TradeWait identity {expected_key!r}."
        )


def _validate_registry_trade_and_entry_partition(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    history_registry: OrderControlTvtMpActualNodePassageHistoryRegistry,
) -> None:
    entry_keys_from_registry = set(registry.entries_by_node_name_and_visit_key.keys())
    entry_keys_from_trades = set()
    entry_owner_by_key = {}

    sorted_trades = _sorted_trade_items(registry.trades_by_transaction_key)
    for transaction_key, trade_wait in sorted_trades:
        _validate_trade_transaction_key_matches_trade_wait(
            transaction_key,
            trade_wait,
        )
        _validate_trade_wait_buyer_seller_visit_keys(
            trade_wait,
            trade_wait.node_name,
        )
        _validate_role_visit_keys_for_trade(
            registry,
            trade_wait,
            trade_wait.node_name,
        )
        node_name = trade_wait.node_name
        for visit_key in trade_wait.all_visit_keys:
            entry_key = (node_name, visit_key)
            entry_keys_from_trades.add(entry_key)
            if entry_key not in registry.entries_by_node_name_and_visit_key:
                raise RuntimeError(
                    f"Node {node_name!r}: TradeWait lists VisitKey {visit_key!r} "
                    "but no WaitEntry exists."
                )
            if entry_key in entry_owner_by_key:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {visit_key!r} belongs to more "
                    "than one TradeWait."
                )
            entry_owner_by_key[entry_key] = transaction_key
            entry = registry.entries_by_node_name_and_visit_key[entry_key]
            _validate_wait_entry_identity_matches_trade(
                trade_wait,
                entry,
                node_name,
            )
            _validate_current_visit_trade_membership(
                trade_wait,
                entry,
                node_name,
                visit_key,
            )
            _validate_wait_entry_formal_three_state(entry, node_name, visit_key)
            _validate_wait_entry_matches_node_passage_history(
                entry,
                node_name,
                visit_key,
                history_registry,
            )

    if entry_keys_from_registry != entry_keys_from_trades:
        orphan_entry_keys = entry_keys_from_registry - entry_keys_from_trades
        if orphan_entry_keys:
            orphan_example = sorted(orphan_entry_keys)[0]
            raise RuntimeError(
                f"Node {orphan_example[0]!r}: WaitEntry for VisitKey "
                f"{orphan_example[1]!r} is not listed in any TradeWait."
            )
        orphan_trade_only = entry_keys_from_trades - entry_keys_from_registry
        orphan_example = sorted(orphan_trade_only)[0]
        raise RuntimeError(
            f"Node {orphan_example[0]!r}: TradeWait lists VisitKey "
            f"{orphan_example[1]!r} without a matching WaitEntry."
        )


def _build_evaluation_end_unobserved_observation_record(
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
) -> OrderControlTvtMpActualPassageObservationRecord:
    return OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=wait_entry.tvt_decision_timestep,
        node_name=wait_entry.node_name,
        buyers_sorted=wait_entry.buyers_sorted,
        visit_key=wait_entry.visit_key,
        vehicle_name=wait_entry.vehicle_name,
        role=wait_entry.role,
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
        ),
        baseline_passage_timestep=wait_entry.baseline_passage_timestep,
        candidate_passage_timestep=wait_entry.candidate_passage_timestep,
        true_vot_per_second=wait_entry.true_vot_per_second,
        predicted_observation_status=wait_entry.predicted_observation_status,
        predicted_route_next_link_name=wait_entry.predicted_route_next_link_name,
        baseline_minus_candidate_passage_timesteps=(
            wait_entry.baseline_minus_candidate_passage_timesteps
        ),
        baseline_minus_candidate_passage_seconds=(
            wait_entry.baseline_minus_candidate_passage_seconds
        ),
        baseline_minus_candidate_time_value=(
            wait_entry.baseline_minus_candidate_time_value
        ),
        baseline_minus_actual_passage_timesteps=None,
        baseline_minus_actual_passage_seconds=None,
        baseline_minus_actual_time_value=None,
        candidate_minus_actual_passage_timesteps=None,
        candidate_minus_actual_passage_seconds=None,
        candidate_minus_actual_time_value=None,
        actual_passage_timestep=None,
        actual_route_next_link_name=None,
    )


def prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization(
    world,
) -> _PreparedTvtMpActualPassageEvaluationEndUnobservedFinalization:
    """Prepare evaluation-end unobserved finalization without changing live state."""
    _require_real_world_for_evaluation_end_unobserved(world)
    evaluation_end_timestep = _require_evaluation_end_timestep_for_unobserved(world)
    _require_world_timestep_matches_evaluation_end_plus_one(
        world,
        evaluation_end_timestep,
    )
    wait_registry, history_registry = _require_wait_and_history_registries_for_evaluation_end(
        world,
    )
    _require_wait_registry_not_already_finalized(wait_registry)
    _require_no_partial_evaluation_end_unobserved_entries(wait_registry)
    _validate_all_saved_node_passage_histories(history_registry)
    _validate_registry_trade_and_entry_partition(wait_registry, history_registry)

    waiting_entry_updates = []
    for entry_key in sorted(wait_registry.entries_by_node_name_and_visit_key.keys()):
        node_name = entry_key[0]
        visit_key = entry_key[1]
        entry = wait_registry.entries_by_node_name_and_visit_key[entry_key]
        if (
            entry.wait_status
            is not OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
        ):
            continue
        unobserved_record = _build_evaluation_end_unobserved_observation_record(entry)
        waiting_entry_updates.append((entry, unobserved_record))

    return _PreparedTvtMpActualPassageEvaluationEndUnobservedFinalization(
        wait_registry=wait_registry,
        waiting_entry_updates=tuple(waiting_entry_updates),
        evaluation_end_unobserved_finalized_timestep=evaluation_end_timestep,
    )


def commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization(
    prepared_update,
) -> None:
    """Assign prepared evaluation-end unobserved updates only."""
    if not isinstance(
        prepared_update,
        _PreparedTvtMpActualPassageEvaluationEndUnobservedFinalization,
    ):
        raise RuntimeError(
            "prepared evaluation-end unobserved update must be "
            "_PreparedTvtMpActualPassageEvaluationEndUnobservedFinalization; "
            f"got type {type(prepared_update).__name__}."
        )
    committed_status = (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    )
    for wait_entry, observation_record in prepared_update.waiting_entry_updates:
        wait_entry.actual_passage_observation_record = observation_record
        wait_entry.wait_status = committed_status
    prepared_update.wait_registry.evaluation_end_unobserved_finalized_timestep = (
        prepared_update.evaluation_end_unobserved_finalized_timestep
    )


@dataclass(frozen=True)
class _PreparedTvtMpTradeExPostEvaluation:
    """Prepared trade ex-post evaluation results. Live registry unchanged."""

    wait_registry: OrderControlTvtMpActualPassageWaitRegistry
    trade_ex_post_evaluation_results_by_transaction_key: dict[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpTradeExPostEvaluationResult,
    ]
    trade_ex_post_evaluation_finalized_timestep: int


def _require_evaluation_end_unobserved_finalized_for_ex_post(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    evaluation_end_timestep: int,
) -> None:
    finalized = registry.evaluation_end_unobserved_finalized_timestep
    if type(finalized) is not int:
        raise RuntimeError(
            "evaluation_end_unobserved_finalized_timestep must be a Python "
            f"int matching evaluation_end_timestep; got {finalized!r}."
        )
    if finalized != evaluation_end_timestep:
        raise RuntimeError(
            "trade ex-post evaluation requires "
            "evaluation_end_unobserved_finalized_timestep to equal "
            f"evaluation_end_timestep {evaluation_end_timestep!r}; got "
            f"{finalized!r}."
        )


def _require_trade_ex_post_evaluation_not_started(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
) -> None:
    finalized = registry.trade_ex_post_evaluation_finalized_timestep
    if finalized is not None:
        if type(finalized) is not int:
            raise RuntimeError(
                "trade_ex_post_evaluation_finalized_timestep must be a Python "
                f"int or None; got {finalized!r}."
            )
        raise RuntimeError(
            "trade ex-post evaluation was already completed for "
            f"timestep {finalized!r}."
        )
    if registry.trade_ex_post_evaluation_results_by_transaction_key:
        raise RuntimeError(
            "trade_ex_post_evaluation_results_by_transaction_key must be empty "
            "before prepare; found partial saved results while "
            "trade_ex_post_evaluation_finalized_timestep is still None."
        )


def _require_no_waiting_entries_for_trade_ex_post(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
) -> None:
    for entry_key, entry in registry.entries_by_node_name_and_visit_key.items():
        node_name = entry_key[0]
        visit_key = entry_key[1]
        if (
            entry.wait_status
            is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is still "
                "WAITING_FOR_ACTUAL_PASSAGE; trade ex-post evaluation requires "
                "observed or evaluation-end unobserved entries only."
            )


def _wait_entry_for_trade_visit_key(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    visit_key: OrderControlTvtVisitKey,
) -> OrderControlTvtMpActualPassageWaitEntry:
    entry_key = (trade_wait.node_name, visit_key)
    entry = registry.entries_by_node_name_and_visit_key.get(entry_key)
    if entry is None:
        raise RuntimeError(
            f"Node {trade_wait.node_name!r}: TradeWait lists VisitKey "
            f"{visit_key!r} but no WaitEntry exists."
        )
    return entry


def _role_is_evaluation_end_unobserved(
    entry: OrderControlTvtMpActualPassageWaitEntry,
) -> bool:
    return (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    )


def _trade_buyer_or_seller_is_evaluation_end_unobserved(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
) -> bool:
    for visit_key in trade_wait.buyer_visit_keys:
        entry = _wait_entry_for_trade_visit_key(
            registry,
            trade_wait,
            visit_key,
        )
        if _role_is_evaluation_end_unobserved(entry):
            return True
    for visit_key in trade_wait.seller_visit_keys:
        entry = _wait_entry_for_trade_visit_key(
            registry,
            trade_wait,
            visit_key,
        )
        if _role_is_evaluation_end_unobserved(entry):
            return True
    return False


def _require_observed_entry_for_ex_post_calculation(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    role_label: str,
) -> OrderControlTvtMpActualPassageObservationRecord:
    if (
        entry.wait_status
        is not OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} {role_label} must be "
            "ACTUAL_PASSAGE_OBSERVED for ex-post calculation; got "
            f"{entry.wait_status!r}."
        )
    record = entry.actual_passage_observation_record
    if record is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} {role_label} is "
            "observed but has no actual passage observation record."
        )
    if (
        record.observation_status
        is not OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} {role_label} "
            "observation record status must be ACTUAL_PASSAGE_OBSERVED; got "
            f"{record.observation_status!r}."
        )
    if record.baseline_minus_actual_passage_seconds is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} {role_label} "
            "observation record baseline_minus_actual_passage_seconds must "
            "not be None for ex-post calculation."
        )
    if not isinstance(
        entry.monetary_frozen_input,
        OrderControlTvtMpActualPassageMonetaryFrozenInput,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} {role_label} requires "
            "OrderControlTvtMpActualPassageMonetaryFrozenInput for ex-post "
            "calculation."
        )
    return record


def _buyer_actual_declared_time_saving_value_from_entry(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> int | float:
    record = _require_observed_entry_for_ex_post_calculation(
        entry,
        node_name=node_name,
        visit_key=visit_key,
        role_label="buyer",
    )
    monetary = entry.monetary_frozen_input
    actual_time_saving_seconds = record.baseline_minus_actual_passage_seconds
    declared_vot_per_second = monetary.declared_vot_per_second
    return actual_time_saving_seconds * declared_vot_per_second


def _seller_actual_required_compensation_from_entry(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> int | float:
    record = _require_observed_entry_for_ex_post_calculation(
        entry,
        node_name=node_name,
        visit_key=visit_key,
        role_label="seller",
    )
    monetary = entry.monetary_frozen_input
    actual_delay_seconds = -record.baseline_minus_actual_passage_seconds
    compensable_delay_seconds = 0
    if actual_delay_seconds > 0:
        compensable_delay_seconds = actual_delay_seconds
    declared_vot_per_second = monetary.declared_vot_per_second
    return compensable_delay_seconds * declared_vot_per_second


def _build_trade_ex_post_evaluation_unavailable_result(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
) -> OrderControlTvtMpTradeExPostEvaluationResult:
    return OrderControlTvtMpTradeExPostEvaluationResult(
        tvt_decision_timestep=trade_wait.tvt_decision_timestep,
        node_name=trade_wait.node_name,
        buyers_sorted=trade_wait.buyers_sorted,
        ex_post_evaluation_status=(
            OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
        ),
        buyer_actual_declared_time_saving_value_total=None,
        seller_actual_required_compensation_total=None,
        buyer_reference_payment_records=None,
        seller_reference_compensation_records=None,
    )


def _build_trade_ex_post_evaluation_evaluated_result(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
) -> OrderControlTvtMpTradeExPostEvaluationResult:
    node_name = trade_wait.node_name
    buyer_values_by_visit_key = {}
    for visit_key in trade_wait.buyers_sorted:
        entry = _wait_entry_for_trade_visit_key(registry, trade_wait, visit_key)
        buyer_value = _buyer_actual_declared_time_saving_value_from_entry(
            entry,
            node_name=node_name,
            visit_key=visit_key,
        )
        buyer_values_by_visit_key[visit_key] = buyer_value

    seller_values_by_visit_key = {}
    for visit_key in trade_wait.seller_visit_keys:
        entry = _wait_entry_for_trade_visit_key(registry, trade_wait, visit_key)
        seller_value = _seller_actual_required_compensation_from_entry(
            entry,
            node_name=node_name,
            visit_key=visit_key,
        )
        seller_values_by_visit_key[visit_key] = seller_value

    buyer_total = 0
    for visit_key in trade_wait.buyers_sorted:
        buyer_total += buyer_values_by_visit_key[visit_key]

    seller_total = 0
    for visit_key in trade_wait.seller_visit_keys:
        seller_total += seller_values_by_visit_key[visit_key]

    has_non_positive_buyer_value = False
    for visit_key in trade_wait.buyers_sorted:
        buyer_value = buyer_values_by_visit_key[visit_key]
        if buyer_value <= 0:
            has_non_positive_buyer_value = True
            break

    if has_non_positive_buyer_value:
        status = OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    elif buyer_total < seller_total:
        status = OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    else:
        status = OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE

    buyer_reference_records = []
    for visit_key in trade_wait.buyers_sorted:
        entry = _wait_entry_for_trade_visit_key(registry, trade_wait, visit_key)
        buyer_value = buyer_values_by_visit_key[visit_key]
        if status is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE:
            reference_payment = 0
        else:
            reference_payment = (
                seller_total * buyer_value / buyer_total
            )
        buyer_reference_records.append(
            OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord(
                visit_key=visit_key,
                vehicle_name=entry.vehicle_name,
                buyer_actual_declared_time_saving_value=buyer_value,
                reference_payment=reference_payment,
            )
        )

    seller_reference_records = []
    for visit_key in trade_wait.seller_visit_keys:
        entry = _wait_entry_for_trade_visit_key(registry, trade_wait, visit_key)
        seller_value = seller_values_by_visit_key[visit_key]
        if status is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE:
            reference_compensation = 0
        else:
            reference_compensation = seller_value
        seller_reference_records.append(
            OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord(
                visit_key=visit_key,
                vehicle_name=entry.vehicle_name,
                seller_actual_required_compensation=seller_value,
                reference_compensation=reference_compensation,
            )
        )

    return OrderControlTvtMpTradeExPostEvaluationResult(
        tvt_decision_timestep=trade_wait.tvt_decision_timestep,
        node_name=trade_wait.node_name,
        buyers_sorted=trade_wait.buyers_sorted,
        ex_post_evaluation_status=status,
        buyer_actual_declared_time_saving_value_total=buyer_total,
        seller_actual_required_compensation_total=seller_total,
        buyer_reference_payment_records=tuple(buyer_reference_records),
        seller_reference_compensation_records=tuple(seller_reference_records),
    )


def _build_trade_ex_post_evaluation_result_for_trade(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
) -> OrderControlTvtMpTradeExPostEvaluationResult:
    if _trade_buyer_or_seller_is_evaluation_end_unobserved(registry, trade_wait):
        return _build_trade_ex_post_evaluation_unavailable_result(trade_wait)
    return _build_trade_ex_post_evaluation_evaluated_result(registry, trade_wait)


def prepare_tvt_mp_trade_ex_post_evaluation(
    world,
) -> _PreparedTvtMpTradeExPostEvaluation:
    """Prepare trade ex-post evaluation without changing live registry state."""
    _require_real_world_for_evaluation_end_unobserved(world)
    evaluation_end_timestep = _require_evaluation_end_timestep_for_unobserved(world)
    _require_world_timestep_matches_evaluation_end_plus_one(
        world,
        evaluation_end_timestep,
    )
    wait_registry, history_registry = (
        _require_wait_and_history_registries_for_evaluation_end(world)
    )
    if not isinstance(
        wait_registry.trade_ex_post_evaluation_results_by_transaction_key,
        dict,
    ):
        raise RuntimeError(
            "trade_ex_post_evaluation_results_by_transaction_key must be a dict; "
            "got type "
            f"{type(wait_registry.trade_ex_post_evaluation_results_by_transaction_key).__name__}."
        )
    _require_evaluation_end_unobserved_finalized_for_ex_post(
        wait_registry,
        evaluation_end_timestep,
    )
    _require_trade_ex_post_evaluation_not_started(wait_registry)
    _require_no_waiting_entries_for_trade_ex_post(wait_registry)
    _validate_all_saved_node_passage_histories(history_registry)
    _validate_registry_trade_and_entry_partition(wait_registry, history_registry)

    prepared_results = {}
    sorted_trades = _sorted_trade_items(wait_registry.trades_by_transaction_key)
    for transaction_key, trade_wait in sorted_trades:
        prepared_results[transaction_key] = (
            _build_trade_ex_post_evaluation_result_for_trade(
                wait_registry,
                trade_wait,
            )
        )

    return _PreparedTvtMpTradeExPostEvaluation(
        wait_registry=wait_registry,
        trade_ex_post_evaluation_results_by_transaction_key=prepared_results,
        trade_ex_post_evaluation_finalized_timestep=evaluation_end_timestep,
    )


def commit_tvt_mp_trade_ex_post_evaluation(prepared_update) -> None:
    """Assign prepared trade ex-post evaluation results only."""
    if not isinstance(prepared_update, _PreparedTvtMpTradeExPostEvaluation):
        raise RuntimeError(
            "prepared trade ex-post evaluation update must be "
            "_PreparedTvtMpTradeExPostEvaluation; got type "
            f"{type(prepared_update).__name__}."
        )
    wait_registry = prepared_update.wait_registry
    wait_registry.trade_ex_post_evaluation_results_by_transaction_key = (
        prepared_update.trade_ex_post_evaluation_results_by_transaction_key
    )
    wait_registry.trade_ex_post_evaluation_finalized_timestep = (
        prepared_update.trade_ex_post_evaluation_finalized_timestep
    )
