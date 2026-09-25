"""
TVT-MP economic evaluation of resolved FIFO-True candidates.

This module reads saved one-candidate local virtual-calculation results
and, for each resolved candidate, computes expected time differences and
declared time values. It identifies whether a candidate is economically
feasible. It does not choose among feasible candidates, does not compute
payment or compensation, and does not change the real World.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
    OrderControlTvtMpCandidatePassageRecord,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.uxsim import Vehicle, World


class OrderControlTvtMpCandidateEconomicInfeasibilityReason(Enum):
    """Why a resolved candidate failed the economic feasibility conditions."""

    BUYER_NONPOSITIVE_VALUE = "buyer_nonpositive_value"
    TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION = (
        "total_buyer_value_below_required_compensation"
    )


@dataclass(frozen=True)
class OrderControlTvtMpBuyerEconomicRecord:
    """One buyer visit's expected time saving and gross time value G_b."""

    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    declared_vot_per_second: float
    baseline_passage_timestep: int
    candidate_passage_timestep: int
    expected_time_saving_timesteps: int
    expected_time_saving_seconds: int | float
    # Payment-deduction-free gross value of the expected time saving.
    # This is not the buyer's payment and not the buyer's final utility.
    gross_time_value_G_b: float
    passes_positive_buyer_value_condition: bool


@dataclass(frozen=True)
class OrderControlTvtMpSellerEconomicRecord:
    """One seller visit's expected waiting increase and reservation R_s."""

    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    declared_vot_per_second: float
    baseline_passage_timestep: int
    candidate_passage_timestep: int
    raw_passage_difference_timesteps: int
    expected_waiting_increase_timesteps: int
    raw_passage_difference_seconds: int | float
    expected_waiting_increase_seconds: int | float
    # Lowest compensation the seller must receive for the expected delay.
    # This is a reservation amount, not the compensation actually paid.
    required_compensation_R_s: float


@dataclass(frozen=True)
class OrderControlTvtMpCandidateEconomicEvaluationResult:
    """Economic evaluation of one resolved local virtual-calculation candidate."""

    candidate_local_virtual_calculation_result: (
        OrderControlTvtMpCandidateLocalVirtualCalculationResult
    )
    buyer_economic_records: tuple[OrderControlTvtMpBuyerEconomicRecord, ...]
    seller_economic_records: tuple[OrderControlTvtMpSellerEconomicRecord, ...]
    total_buyer_value_G: float
    total_required_compensation_R: float
    surplus: float
    economically_feasible: bool
    infeasibility_reasons: tuple[
        OrderControlTvtMpCandidateEconomicInfeasibilityReason,
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtNodeMpEconomicEvaluationResult:
    """Resolved-candidate economic results for one target Node, in stored order."""

    node_name: str
    candidate_economic_evaluation_results: tuple[
        OrderControlTvtMpCandidateEconomicEvaluationResult,
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtMpEconomicEvaluationSetResult:
    """All-Node economic evaluation result for one local virtual-calculation set."""

    local_virtual_calculation_set_result: (
        OrderControlTvtMpLocalVirtualCalculationSetResult
    )
    node_economic_evaluation_results: tuple[
        OrderControlTvtNodeMpEconomicEvaluationResult,
        ...,
    ]


def evaluate_tvt_mp_candidate_economics(
    local_virtual_calculation_set_result,
    real_W,
) -> OrderControlTvtMpEconomicEvaluationSetResult:
    """
    Evaluate expected economics for every resolved FIFO-True candidate.

    Unresolved candidates are skipped and kept only on the input local
    set result. FIFO False candidates are not present on that input and
    are not evaluated here. Declared VOT is read from
    Vehicle.vot_declared on real_W.VEHICLES only for required buyers and
    sellers of resolved candidates. vot_true is not read and is not
    stored. VOT=0 is legal. This function does not compute payment or
    compensation and returns no partial overall result.
    """
    local_set_result = _require_local_virtual_calculation_set_result(
        local_virtual_calculation_set_result,
    )
    real_world = _require_real_world(real_W)
    deltat_seconds = _require_positive_finite_deltat(real_world.DELTAT)

    node_economic_results: list[OrderControlTvtNodeMpEconomicEvaluationResult] = []
    node_local_results = local_set_result.node_local_virtual_calculation_results
    if not isinstance(node_local_results, tuple):
        raise RuntimeError(
            "node_local_virtual_calculation_results must be a tuple; got "
            f"type {type(node_local_results).__name__}."
        )
    for node_local_result in node_local_results:
        node_economic_result = _evaluate_one_node(
            node_local_result=node_local_result,
            real_world=real_world,
            deltat_seconds=deltat_seconds,
        )
        node_economic_results.append(node_economic_result)

    return OrderControlTvtMpEconomicEvaluationSetResult(
        local_virtual_calculation_set_result=local_set_result,
        node_economic_evaluation_results=tuple(node_economic_results),
    )


def _require_local_virtual_calculation_set_result(
    local_virtual_calculation_set_result: object,
) -> OrderControlTvtMpLocalVirtualCalculationSetResult:
    if not isinstance(
        local_virtual_calculation_set_result,
        OrderControlTvtMpLocalVirtualCalculationSetResult,
    ):
        raise ValueError(
            "local_virtual_calculation_set_result must be "
            "OrderControlTvtMpLocalVirtualCalculationSetResult; got "
            f"type {type(local_virtual_calculation_set_result).__name__}."
        )
    return local_virtual_calculation_set_result


def _require_real_world(real_W: object) -> World:
    if not isinstance(real_W, World):
        raise ValueError(
            "real_W must be a World; got "
            f"type {type(real_W).__name__}."
        )
    return real_W


def _require_positive_finite_deltat(deltat: object) -> int | float:
    """Return World.DELTAT after checking it is a positive finite number of seconds."""
    # bool is a subclass of int, so it must be rejected before the number check.
    if isinstance(deltat, bool) or not isinstance(deltat, (int, float)):
        raise ValueError(
            "real_W.DELTAT must be a finite number greater than 0; got "
            f"type {type(deltat).__name__} with value {deltat!r}."
        )
    if not math.isfinite(deltat):
        raise ValueError(
            "real_W.DELTAT must be a finite number greater than 0; got "
            f"{deltat!r}."
        )
    if not (deltat > 0):
        raise ValueError(
            "real_W.DELTAT must be a finite number greater than 0; got "
            f"{deltat!r}."
        )
    return deltat


def _evaluate_one_node(
    *,
    node_local_result: object,
    real_world: World,
    deltat_seconds: int | float,
) -> OrderControlTvtNodeMpEconomicEvaluationResult:
    if not isinstance(
        node_local_result,
        OrderControlTvtNodeMpLocalVirtualCalculationResult,
    ):
        raise RuntimeError(
            "Each node local virtual-calculation result must be "
            "OrderControlTvtNodeMpLocalVirtualCalculationResult; got "
            f"type {type(node_local_result).__name__}."
        )
    node_name = node_local_result.node_name
    candidate_local_results = (
        node_local_result.candidate_local_virtual_calculation_results
    )
    if not isinstance(candidate_local_results, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: candidate_local_virtual_calculation_results "
            "must be a tuple; got "
            f"type {type(candidate_local_results).__name__}."
        )

    candidate_economic_results: list[
        OrderControlTvtMpCandidateEconomicEvaluationResult
    ] = []
    for candidate_local_result in candidate_local_results:
        _require_candidate_local_result_type(
            candidate_local_result,
            node_name=node_name,
        )
        _require_candidate_node_name_matches_node_result(
            candidate_local_result,
            node_name=node_name,
        )
        _require_resolved_agrees_with_stop_reason(
            candidate_local_result,
            node_name=node_name,
        )
        if candidate_local_result.resolved is False:
            # Normal unresolved: keep it on the input set result only.
            continue
        candidate_economic_result = _evaluate_one_resolved_candidate(
            candidate_local_result=candidate_local_result,
            real_world=real_world,
            deltat_seconds=deltat_seconds,
            node_name=node_name,
        )
        candidate_economic_results.append(candidate_economic_result)

    return OrderControlTvtNodeMpEconomicEvaluationResult(
        node_name=node_name,
        candidate_economic_evaluation_results=tuple(candidate_economic_results),
    )


def _require_candidate_local_result_type(
    candidate_local_result: object,
    *,
    node_name: str,
) -> None:
    if not isinstance(
        candidate_local_result,
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: each candidate local virtual-calculation "
            "result must be "
            "OrderControlTvtMpCandidateLocalVirtualCalculationResult; got "
            f"type {type(candidate_local_result).__name__}."
        )


def _require_candidate_node_name_matches_node_result(
    candidate_local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    *,
    node_name: str,
) -> None:
    if candidate_local_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: candidate local result node_name "
            f"{candidate_local_result.node_name!r} does not match the Node "
            "result."
        )


def _require_resolved_agrees_with_stop_reason(
    candidate_local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    *,
    node_name: str,
) -> None:
    resolved = candidate_local_result.resolved
    stop_reason = candidate_local_result.stop_reason
    if resolved is True:
        if (
            stop_reason
            is not OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
        ):
            raise RuntimeError(
                f"Node {node_name!r}: resolved is True but stop_reason is "
                f"{stop_reason!r}."
            )
        return
    if resolved is False:
        if (
            stop_reason
            is not OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
        ):
            raise RuntimeError(
                f"Node {node_name!r}: resolved is False but stop_reason is "
                f"{stop_reason!r}."
            )
        return
    raise RuntimeError(
        f"Node {node_name!r}: resolved must be a strict Python bool; got "
        f"type {type(resolved).__name__} with value {resolved!r}."
    )


def _evaluate_one_resolved_candidate(
    *,
    candidate_local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    real_world: World,
    deltat_seconds: int | float,
    node_name: str,
) -> OrderControlTvtMpCandidateEconomicEvaluationResult:
    buyer_passage_records, seller_passage_records = (
        _validate_and_classify_resolved_passage_records(
            candidate_local_result,
            node_name=node_name,
        )
    )

    buyer_economic_records: list[OrderControlTvtMpBuyerEconomicRecord] = []
    for buyer_passage_record in buyer_passage_records:
        buyer_economic_record = _build_buyer_economic_record(
            buyer_passage_record,
            real_world=real_world,
            deltat_seconds=deltat_seconds,
            node_name=node_name,
        )
        buyer_economic_records.append(buyer_economic_record)

    seller_economic_records: list[OrderControlTvtMpSellerEconomicRecord] = []
    for seller_passage_record in seller_passage_records:
        seller_economic_record = _build_seller_economic_record(
            seller_passage_record,
            real_world=real_world,
            deltat_seconds=deltat_seconds,
            node_name=node_name,
        )
        seller_economic_records.append(seller_economic_record)

    total_buyer_value_G = 0.0
    for buyer_economic_record in buyer_economic_records:
        total_buyer_value_G = (
            total_buyer_value_G + buyer_economic_record.gross_time_value_G_b
        )

    total_required_compensation_R = 0.0
    for seller_economic_record in seller_economic_records:
        total_required_compensation_R = (
            total_required_compensation_R
            + seller_economic_record.required_compensation_R_s
        )

    surplus = total_buyer_value_G - total_required_compensation_R
    infeasibility_reasons = _build_infeasibility_reasons(
        buyer_economic_records=buyer_economic_records,
        total_buyer_value_G=total_buyer_value_G,
        total_required_compensation_R=total_required_compensation_R,
    )
    if len(infeasibility_reasons) == 0:
        economically_feasible = True
    else:
        economically_feasible = False

    return OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=candidate_local_result,
        buyer_economic_records=tuple(buyer_economic_records),
        seller_economic_records=tuple(seller_economic_records),
        total_buyer_value_G=total_buyer_value_G,
        total_required_compensation_R=total_required_compensation_R,
        surplus=surplus,
        economically_feasible=economically_feasible,
        infeasibility_reasons=infeasibility_reasons,
    )


def _validate_and_classify_resolved_passage_records(
    candidate_local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    *,
    node_name: str,
) -> tuple[
    tuple[OrderControlTvtMpCandidatePassageRecord, ...],
    tuple[OrderControlTvtMpCandidatePassageRecord, ...],
]:
    _require_candidate_identity_matches_binding_sequence(
        candidate_local_result,
        node_name=node_name,
    )
    passage_records = candidate_local_result.required_passage_records
    if not isinstance(passage_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: required_passage_records must be a tuple; "
            f"got type {type(passage_records).__name__}."
        )

    buyer_passage_records: list[OrderControlTvtMpCandidatePassageRecord] = []
    seller_passage_records: list[OrderControlTvtMpCandidatePassageRecord] = []
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    for passage_record in passage_records:
        _require_passage_record_type(passage_record, node_name=node_name)
        visit_key = passage_record.visit_key
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: required VisitKey {visit_key!r} appears "
                "more than once among required passage records."
            )
        seen_visit_keys.add(visit_key)
        _require_vehicle_name_matches_visit_key(
            passage_record,
            node_name=node_name,
        )
        _require_python_int_timestep(
            passage_record.baseline_passage_timestep,
            field_name="baseline_passage_timestep",
            visit_key=visit_key,
            node_name=node_name,
        )
        _require_python_int_timestep(
            passage_record.candidate_passage_timestep,
            field_name="candidate_passage_timestep",
            visit_key=visit_key,
            node_name=node_name,
        )
        trade_role = passage_record.trade_role
        if trade_role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
            buyer_passage_records.append(passage_record)
            continue
        if trade_role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
            seller_passage_records.append(passage_record)
            continue
        raise RuntimeError(
            f"Node {node_name!r}: required VisitKey {visit_key!r} has trade "
            f"role {trade_role!r}; resolved economic evaluation accepts only "
            "BUYER and SELLER."
        )

    if len(buyer_passage_records) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: resolved candidate has no BUYER required "
            "passage records."
        )

    _require_buyer_visit_keys_match_concrete_set(
        buyer_passage_records=buyer_passage_records,
        concrete_buyer_candidate_set=(
            candidate_local_result.concrete_buyer_candidate_set
        ),
        node_name=node_name,
    )
    _require_seller_visit_keys_match_binding_sequence(
        seller_passage_records=seller_passage_records,
        binding_rank_sequence=candidate_local_result.binding_rank_sequence,
        node_name=node_name,
    )
    return tuple(buyer_passage_records), tuple(seller_passage_records)


def _require_candidate_identity_matches_binding_sequence(
    candidate_local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    *,
    node_name: str,
) -> None:
    binding_rank_sequence = candidate_local_result.binding_rank_sequence
    if not isinstance(binding_rank_sequence, OrderControlTvtMpLocalBindingRankSequence):
        raise RuntimeError(
            f"Node {node_name!r}: binding_rank_sequence must be "
            "OrderControlTvtMpLocalBindingRankSequence; got "
            f"type {type(binding_rank_sequence).__name__}."
        )
    if binding_rank_sequence.node_name != candidate_local_result.node_name:
        raise RuntimeError(
            f"Node {node_name!r}: binding_rank_sequence.node_name "
            f"{binding_rank_sequence.node_name!r} does not match the "
            "candidate local result."
        )
    if (
        binding_rank_sequence.concrete_buyer_candidate_set
        is not candidate_local_result.concrete_buyer_candidate_set
    ):
        raise RuntimeError(
            f"Node {node_name!r}: concrete_buyer_candidate_set on the "
            "candidate local result is not the same object as on the "
            "binding rank sequence."
        )
    if (
        binding_rank_sequence.baseline_timestep_T
        != candidate_local_result.baseline_timestep_T
    ):
        raise RuntimeError(
            f"Node {node_name!r}: baseline_timestep_T "
            f"{candidate_local_result.baseline_timestep_T!r} does not match "
            "binding_rank_sequence.baseline_timestep_T "
            f"{binding_rank_sequence.baseline_timestep_T!r}."
        )


def _require_passage_record_type(
    passage_record: object,
    *,
    node_name: str,
) -> None:
    if not isinstance(passage_record, OrderControlTvtMpCandidatePassageRecord):
        raise RuntimeError(
            f"Node {node_name!r}: each required passage record must be "
            "OrderControlTvtMpCandidatePassageRecord; got "
            f"type {type(passage_record).__name__}."
        )


def _require_vehicle_name_matches_visit_key(
    passage_record: OrderControlTvtMpCandidatePassageRecord,
    *,
    node_name: str,
) -> None:
    visit_key = passage_record.visit_key
    if not isinstance(visit_key, tuple) or len(visit_key) != 2:
        raise RuntimeError(
            f"Node {node_name!r}: visit_key must be a length-2 tuple "
            f"(vehicle_name, visit_id); got {visit_key!r}."
        )
    visit_key_vehicle_name = visit_key[0]
    if passage_record.vehicle_name != visit_key_vehicle_name:
        raise RuntimeError(
            f"Node {node_name!r}: passage vehicle_name "
            f"{passage_record.vehicle_name!r} does not match VisitKey "
            f"{visit_key!r}."
        )


def _require_python_int_timestep(
    value: object,
    *,
    field_name: str,
    visit_key: OrderControlTvtVisitKey,
    node_name: str,
) -> None:
    # type(value) is int rejects bool, because type(True) is bool.
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: resolved VisitKey {visit_key!r} "
            f"{field_name} must be a Python int, not bool or None; got "
            f"type {type(value).__name__} with value {value!r}."
        )


def _require_buyer_visit_keys_match_concrete_set(
    *,
    buyer_passage_records: list[OrderControlTvtMpCandidatePassageRecord],
    concrete_buyer_candidate_set: object,
    node_name: str,
) -> None:
    buyers_sorted = getattr(concrete_buyer_candidate_set, "buyers_sorted", None)
    if not isinstance(buyers_sorted, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: concrete_buyer_candidate_set.buyers_sorted "
            "must be a tuple."
        )
    buyer_keys_from_passages: set[OrderControlTvtVisitKey] = set()
    for buyer_passage_record in buyer_passage_records:
        buyer_keys_from_passages.add(buyer_passage_record.visit_key)
    buyer_keys_from_concrete_set = set(buyers_sorted)
    if buyer_keys_from_passages != buyer_keys_from_concrete_set:
        raise RuntimeError(
            f"Node {node_name!r}: BUYER VisitKeys from required passage "
            "records do not match concrete_buyer_candidate_set.buyers_sorted."
        )


def _required_seller_visit_keys_from_binding_sequence(
    binding_rank_sequence: OrderControlTvtMpLocalBindingRankSequence,
    *,
    node_name: str,
) -> set[OrderControlTvtVisitKey]:
    """
    Required sellers are SELLER visits inside this candidate's trade scope.

    This is the same definition used by the one-candidate orchestrator:
    walk trade_scope_of_this_candidate_visits and keep SELLER roles.
    Empty sellers are allowed.
    """
    trade_scope_visits = binding_rank_sequence.trade_scope_of_this_candidate_visits
    if not isinstance(trade_scope_visits, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: trade_scope_of_this_candidate_visits must "
            "be a tuple."
        )
    seller_keys: set[OrderControlTvtVisitKey] = set()
    for visit in trade_scope_visits:
        if visit.trade_role is not OrderControlTvtMpLocalBindingTradeRole.SELLER:
            continue
        visit_key = visit.visit_key
        if visit_key in seller_keys:
            raise RuntimeError(
                f"Node {node_name!r}: required seller VisitKey {visit_key!r} "
                "is duplicated in the binding rank sequence."
            )
        seller_keys.add(visit_key)
    return seller_keys


def _require_seller_visit_keys_match_binding_sequence(
    *,
    seller_passage_records: list[OrderControlTvtMpCandidatePassageRecord],
    binding_rank_sequence: OrderControlTvtMpLocalBindingRankSequence,
    node_name: str,
) -> None:
    seller_keys_from_passages: set[OrderControlTvtVisitKey] = set()
    for seller_passage_record in seller_passage_records:
        seller_keys_from_passages.add(seller_passage_record.visit_key)
    seller_keys_from_binding = _required_seller_visit_keys_from_binding_sequence(
        binding_rank_sequence,
        node_name=node_name,
    )
    if seller_keys_from_passages != seller_keys_from_binding:
        raise RuntimeError(
            f"Node {node_name!r}: SELLER VisitKeys from required passage "
            "records do not match SELLER visits in the binding rank "
            "sequence trade scope."
        )


def _build_buyer_economic_record(
    buyer_passage_record: OrderControlTvtMpCandidatePassageRecord,
    *,
    real_world: World,
    deltat_seconds: int | float,
    node_name: str,
) -> OrderControlTvtMpBuyerEconomicRecord:
    vehicle_name = buyer_passage_record.vehicle_name
    declared_vot_per_second = _declared_vot_per_second_for_vehicle(
        real_world,
        vehicle_name=vehicle_name,
        node_name=node_name,
    )
    baseline_passage_timestep = buyer_passage_record.baseline_passage_timestep
    candidate_passage_timestep = buyer_passage_record.candidate_passage_timestep
    # Positive means the candidate lets this buyer pass earlier than baseline.
    # Zero means no expected saving. Negative means the candidate is slower.
    # Negative values are kept so G_b <= 0 can be detected correctly.
    expected_time_saving_timesteps = (
        baseline_passage_timestep - candidate_passage_timestep
    )
    expected_time_saving_seconds = (
        expected_time_saving_timesteps * deltat_seconds
    )
    # G_b is the gross value of the expected time saving before payment.
    gross_time_value_G_b = (
        expected_time_saving_seconds * declared_vot_per_second
    )
    if gross_time_value_G_b > 0:
        passes_positive_buyer_value_condition = True
    else:
        passes_positive_buyer_value_condition = False
    return OrderControlTvtMpBuyerEconomicRecord(
        visit_key=buyer_passage_record.visit_key,
        vehicle_name=vehicle_name,
        declared_vot_per_second=declared_vot_per_second,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        expected_time_saving_timesteps=expected_time_saving_timesteps,
        expected_time_saving_seconds=expected_time_saving_seconds,
        gross_time_value_G_b=gross_time_value_G_b,
        passes_positive_buyer_value_condition=passes_positive_buyer_value_condition,
    )


def _build_seller_economic_record(
    seller_passage_record: OrderControlTvtMpCandidatePassageRecord,
    *,
    real_world: World,
    deltat_seconds: int | float,
    node_name: str,
) -> OrderControlTvtMpSellerEconomicRecord:
    vehicle_name = seller_passage_record.vehicle_name
    declared_vot_per_second = _declared_vot_per_second_for_vehicle(
        real_world,
        vehicle_name=vehicle_name,
        node_name=node_name,
    )
    baseline_passage_timestep = seller_passage_record.baseline_passage_timestep
    candidate_passage_timestep = seller_passage_record.candidate_passage_timestep
    # Positive raw difference means the seller passes later than baseline.
    # Negative means the seller passes earlier. Early passage is not a
    # buyer-side gain and does not create a payment obligation.
    raw_passage_difference_timesteps = (
        candidate_passage_timestep - baseline_passage_timestep
    )
    if raw_passage_difference_timesteps > 0:
        expected_waiting_increase_timesteps = raw_passage_difference_timesteps
    else:
        expected_waiting_increase_timesteps = 0
    raw_passage_difference_seconds = (
        raw_passage_difference_timesteps * deltat_seconds
    )
    expected_waiting_increase_seconds = (
        expected_waiting_increase_timesteps * deltat_seconds
    )
    # R_s is the seller's reservation for the expected waiting increase.
    required_compensation_R_s = (
        expected_waiting_increase_seconds * declared_vot_per_second
    )
    return OrderControlTvtMpSellerEconomicRecord(
        visit_key=seller_passage_record.visit_key,
        vehicle_name=vehicle_name,
        declared_vot_per_second=declared_vot_per_second,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        raw_passage_difference_timesteps=raw_passage_difference_timesteps,
        expected_waiting_increase_timesteps=expected_waiting_increase_timesteps,
        raw_passage_difference_seconds=raw_passage_difference_seconds,
        expected_waiting_increase_seconds=expected_waiting_increase_seconds,
        required_compensation_R_s=required_compensation_R_s,
    )


def _declared_vot_per_second_for_vehicle(
    real_world: World,
    *,
    vehicle_name: str,
    node_name: str,
) -> float:
    vehicle = _vehicle_from_real_world(
        real_world,
        vehicle_name=vehicle_name,
        node_name=node_name,
    )
    if not hasattr(vehicle, "vot_declared"):
        raise ValueError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} has no "
            "vot_declared attribute."
        )
    declared_vot = vehicle.vot_declared
    return _require_declared_vot(
        declared_vot,
        vehicle_name=vehicle_name,
        node_name=node_name,
    )


def _vehicle_from_real_world(
    real_world: World,
    *,
    vehicle_name: str,
    node_name: str,
) -> Vehicle:
    vehicles = real_world.VEHICLES
    if vehicle_name not in vehicles:
        raise ValueError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} is not in "
            "real_W.VEHICLES."
        )
    vehicle = vehicles[vehicle_name]
    if not isinstance(vehicle, Vehicle):
        raise ValueError(
            f"Node {node_name!r}: real_W.VEHICLES[{vehicle_name!r}] is not a "
            f"Vehicle; got type {type(vehicle).__name__}."
        )
    return vehicle


def _require_declared_vot(
    declared_vot: object,
    *,
    vehicle_name: str,
    node_name: str,
) -> float:
    """
    Accept a non-negative finite declared VOT in abstract currency per second.

    VOT=0 is legal. It is a preference that places no money value on time
    change, not a missing value and not non-participation. bool is rejected
    first because bool is a subclass of int. numpy.bool_ is rejected by the
    number check. numpy.float64 is accepted when it is an instance of float.
    numpy.integer values are rejected because they are not Python int.
    """
    if isinstance(declared_vot, bool):
        raise ValueError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} vot_declared must "
            "be a finite number >= 0; got type bool with value "
            f"{declared_vot!r}."
        )
    if not isinstance(declared_vot, (int, float)):
        raise ValueError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} vot_declared must "
            "be a finite number >= 0; got type "
            f"{type(declared_vot).__name__} with value {declared_vot!r}."
        )
    if not math.isfinite(declared_vot):
        raise ValueError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} vot_declared must "
            "be a finite number >= 0; got {declared_vot!r}."
        )
    if declared_vot < 0:
        raise ValueError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} vot_declared must "
            f"be a finite number >= 0; got {declared_vot!r}."
        )
    return float(declared_vot)


def _build_infeasibility_reasons(
    *,
    buyer_economic_records: list[OrderControlTvtMpBuyerEconomicRecord],
    total_buyer_value_G: float,
    total_required_compensation_R: float,
) -> tuple[OrderControlTvtMpCandidateEconomicInfeasibilityReason, ...]:
    all_buyers_have_positive_value = True
    for buyer_economic_record in buyer_economic_records:
        if buyer_economic_record.passes_positive_buyer_value_condition is True:
            continue
        all_buyers_have_positive_value = False

    reasons: list[OrderControlTvtMpCandidateEconomicInfeasibilityReason] = []
    if all_buyers_have_positive_value is False:
        reasons.append(
            OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE
        )
    # Exact comparison. G = R is feasible. No tolerance is used.
    if total_buyer_value_G < total_required_compensation_R:
        reasons.append(
            OrderControlTvtMpCandidateEconomicInfeasibilityReason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION
        )
    return tuple(reasons)
