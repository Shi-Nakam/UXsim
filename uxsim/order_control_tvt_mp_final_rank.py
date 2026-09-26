"""
TVT-MP final rank construction.

This module reads one saved payment-and-compensation set result and, for
every target Node, builds the visits that are newly confirmed in this cycle
together with each visit's formal route after the target Node.

It does not write the rank ledger, does not update Vehicle monetary
attributes, does not call atomic apply, and does not rerun upstream stages.
A payment status is a downstream label, not the cause of a final-rank branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
    OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionSetResult,
    OrderControlTvtMpCandidateSelectionStatus,
    OrderControlTvtNodeMpCandidateSelectionResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpFifoInspectionSetResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankSetResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpPaymentAndCompensationSetResult,
    OrderControlTvtMpPaymentAndCompensationStatus,
    OrderControlTvtNodeMpPaymentAndCompensationResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtRightOfEntrySelectionResult,
)


class OrderControlTvtMpFinalRankStatus(Enum):
    """Why this Node's newly confirmed visit column was built, or left empty."""

    SELECTED_CANDIDATE_RANKS = "selected_candidate_ranks"
    BASELINE_FALLBACK_RANKS = "baseline_fallback_ranks"
    NO_VISITS_TO_CONFIRM = "no_visits_to_confirm"


class OrderControlTvtMpFinalizationSource(Enum):
    """Whether one visit's rank came from the selected candidate or baseline."""

    SELECTED_CANDIDATE = "selected_candidate"
    BASELINE = "baseline"


_INFORMATION_SHORTAGE_STATUSES = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
)


@dataclass(frozen=True)
class OrderControlTvtMpFinalRankVisitRecord:
    """One newly confirmed visit: local rank, formal route, and source."""

    visit_key: OrderControlTvtVisitKey
    final_local_rank: int
    formal_route_next_link_name: str
    finalization_source: OrderControlTvtMpFinalizationSource


@dataclass(frozen=True)
class OrderControlTvtNodeMpFinalRankResult:
    """Final-rank outcome for one target Node."""

    node_name: str
    final_rank_status: OrderControlTvtMpFinalRankStatus
    selected_candidate_economic_result: (
        OrderControlTvtMpCandidateEconomicEvaluationResult | None
    )
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...]


@dataclass(frozen=True)
class OrderControlTvtMpFinalRankSetResult:
    """All-Node final-rank result for one payment-and-compensation set."""

    payment_and_compensation_set_result: OrderControlTvtMpPaymentAndCompensationSetResult
    node_final_rank_results: tuple[OrderControlTvtNodeMpFinalRankResult, ...]


@dataclass(frozen=True)
class _SavedNodeColumns:
    """Aligned per-Node columns reached from one payment set. Same objects."""

    payment_nodes: tuple[OrderControlTvtNodeMpPaymentAndCompensationResult, ...]
    selection_nodes: tuple[OrderControlTvtNodeMpCandidateSelectionResult, ...]
    economic_nodes: tuple[OrderControlTvtNodeMpEconomicEvaluationResult, ...]
    local_nodes: tuple[OrderControlTvtNodeMpLocalVirtualCalculationResult, ...]
    candidate_visit_nodes: tuple[OrderControlTvtNodeCandidateVisitSetResult, ...]
    leading_nodes: tuple[
        OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
        ...,
    ]
    arrived_confirmed_visit_keys_by_node: tuple[
        tuple[OrderControlTvtVisitKey, ...],
        ...,
    ]
    collector: object


def build_tvt_mp_final_ranks(
    payment_and_compensation_set_result,
) -> OrderControlTvtMpFinalRankSetResult:
    """
    Build newly confirmed visit ranks and formal routes for every target Node.

    The only public input is a saved payment-and-compensation set result.
    Empty-window Nodes, information-shortage Nodes, rejected-candidate Nodes,
    fully preconfirmed Nodes, and selected-candidate Nodes are all read from
    that one set. This function does not search traffic objects, does not read a rank
    ledger, and returns no partial overall result.
    """
    payment_set = _require_payment_set_result(payment_and_compensation_set_result)
    saved_columns = _saved_node_columns_from_payment_set(payment_set)

    node_final_rank_results: list[OrderControlTvtNodeMpFinalRankResult] = []
    node_index = 0
    for payment_node_result in saved_columns.payment_nodes:
        node_final_rank_result = _build_one_node_final_rank(
            saved_columns=saved_columns,
            node_index=node_index,
            payment_node_result=payment_node_result,
        )
        node_final_rank_results.append(node_final_rank_result)
        node_index = node_index + 1

    return OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=payment_set,
        node_final_rank_results=tuple(node_final_rank_results),
    )


def _require_payment_set_result(
    payment_and_compensation_set_result: object,
) -> OrderControlTvtMpPaymentAndCompensationSetResult:
    if not isinstance(
        payment_and_compensation_set_result,
        OrderControlTvtMpPaymentAndCompensationSetResult,
    ):
        raise ValueError(
            "payment_and_compensation_set_result must be "
            "OrderControlTvtMpPaymentAndCompensationSetResult; got "
            f"type {type(payment_and_compensation_set_result).__name__}."
        )
    return payment_and_compensation_set_result


def _require_tuple_column(column: object, column_name: str) -> tuple:
    if not isinstance(column, tuple):
        raise RuntimeError(
            f"{column_name} must be a tuple; got type {type(column).__name__}."
        )
    return column


def _saved_node_columns_from_payment_set(
    payment_set: OrderControlTvtMpPaymentAndCompensationSetResult,
) -> _SavedNodeColumns:
    """
    Walk the saved reference chain once and keep the same objects.

    Payment status is not used here as a branch cause. The chain is the
    single place that reaches decision windows, build status, and the
    baseline collector.
    """
    payment_nodes = _require_tuple_column(
        payment_set.node_payment_and_compensation_results,
        "node_payment_and_compensation_results",
    )
    selection_set = payment_set.candidate_selection_set_result
    if not isinstance(selection_set, OrderControlTvtMpCandidateSelectionSetResult):
        raise RuntimeError(
            "candidate_selection_set_result must be "
            "OrderControlTvtMpCandidateSelectionSetResult; got "
            f"type {type(selection_set).__name__}."
        )
    selection_nodes = _require_tuple_column(
        selection_set.node_candidate_selection_results,
        "node_candidate_selection_results",
    )
    economic_set = selection_set.economic_evaluation_set_result
    if not isinstance(economic_set, OrderControlTvtMpEconomicEvaluationSetResult):
        raise RuntimeError(
            "economic_evaluation_set_result must be "
            "OrderControlTvtMpEconomicEvaluationSetResult; got "
            f"type {type(economic_set).__name__}."
        )
    economic_nodes = _require_tuple_column(
        economic_set.node_economic_evaluation_results,
        "node_economic_evaluation_results",
    )
    local_set = economic_set.local_virtual_calculation_set_result
    if not isinstance(local_set, OrderControlTvtMpLocalVirtualCalculationSetResult):
        raise RuntimeError(
            "local_virtual_calculation_set_result must be "
            "OrderControlTvtMpLocalVirtualCalculationSetResult; got "
            f"type {type(local_set).__name__}."
        )
    local_nodes = _require_tuple_column(
        local_set.node_local_virtual_calculation_results,
        "node_local_virtual_calculation_results",
    )
    fifo_set = local_set.fifo_inspection_set_result
    if not isinstance(fifo_set, OrderControlTvtMpFifoInspectionSetResult):
        raise RuntimeError(
            "fifo_inspection_set_result must be "
            "OrderControlTvtMpFifoInspectionSetResult; got "
            f"type {type(fifo_set).__name__}."
        )
    fifo_nodes = _require_tuple_column(
        fifo_set.node_fifo_inspection_results,
        "node_fifo_inspection_results",
    )
    trade_rank_set = fifo_set.general_trade_rank_set_result
    if not isinstance(trade_rank_set, OrderControlTvtMpGeneralTradeRankSetResult):
        raise RuntimeError(
            "general_trade_rank_set_result must be "
            "OrderControlTvtMpGeneralTradeRankSetResult; got "
            f"type {type(trade_rank_set).__name__}."
        )
    trade_rank_nodes = _require_tuple_column(
        trade_rank_set.node_trade_rank_results,
        "node_trade_rank_results",
    )
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    if not isinstance(concrete_set, OrderControlTvtMpConcreteBuyerCandidateSetResult):
        raise RuntimeError(
            "concrete_buyer_candidate_set_result must be "
            "OrderControlTvtMpConcreteBuyerCandidateSetResult; got "
            f"type {type(concrete_set).__name__}."
        )
    concrete_nodes = _require_tuple_column(
        concrete_set.node_concrete_buyer_candidate_set_results,
        "node_concrete_buyer_candidate_set_results",
    )
    inlink_set = concrete_set.inlink_candidate_physical_order_result
    if not isinstance(inlink_set, OrderControlTvtInlinkCandidatePhysicalOrderSetResult):
        raise RuntimeError(
            "inlink_candidate_physical_order_result must be "
            "OrderControlTvtInlinkCandidatePhysicalOrderSetResult; got "
            f"type {type(inlink_set).__name__}."
        )
    inlink_nodes = _require_tuple_column(
        inlink_set.node_inlink_candidate_physical_order_results,
        "node_inlink_candidate_physical_order_results",
    )
    candidate_visit_set = inlink_set.candidate_visit_set_result
    if not isinstance(candidate_visit_set, OrderControlTvtCandidateVisitSetResult):
        raise RuntimeError(
            "candidate_visit_set_result must be "
            "OrderControlTvtCandidateVisitSetResult; got "
            f"type {type(candidate_visit_set).__name__}."
        )
    candidate_visit_nodes = _require_tuple_column(
        candidate_visit_set.node_candidate_set_results,
        "node_candidate_set_results",
    )
    right_of_entry_set = candidate_visit_set.right_of_entry_selection_result
    if not isinstance(right_of_entry_set, OrderControlTvtRightOfEntrySelectionResult):
        raise RuntimeError(
            "right_of_entry_selection_result must be "
            "OrderControlTvtRightOfEntrySelectionResult; got "
            f"type {type(right_of_entry_set).__name__}."
        )
    right_of_entry_nodes = _require_tuple_column(
        right_of_entry_set.node_selection_results,
        "node_selection_results",
    )
    leading_set = right_of_entry_set.leading_confirmation_result
    if not isinstance(
        leading_set,
        OrderControlTvtLeadingNonparticipatingConfirmationResult,
    ):
        raise RuntimeError(
            "leading_confirmation_result must be "
            "OrderControlTvtLeadingNonparticipatingConfirmationResult; got "
            f"type {type(leading_set).__name__}."
        )
    leading_nodes = _require_tuple_column(
        leading_set.node_confirmation_results,
        "node_confirmation_results",
    )
    arrived_set = leading_set.arrived_confirmation_result
    arrived_nodes = _require_tuple_column(
        arrived_set.node_confirmation_results,
        "arrived node_confirmation_results",
    )
    alignment_fork = arrived_set.alignment_fork_result
    alignment_nodes = _require_tuple_column(
        alignment_fork.alignment_results,
        "alignment_results",
    )
    fork_result = alignment_fork.fork_result
    target_node_names = _require_tuple_column(
        fork_result.target_node_names,
        "target_node_names",
    )
    collector = fork_result.collector

    columns_to_count = (
        ("payment", payment_nodes),
        ("selection", selection_nodes),
        ("economic", economic_nodes),
        ("local", local_nodes),
        ("fifo", fifo_nodes),
        ("trade rank", trade_rank_nodes),
        ("concrete buyer", concrete_nodes),
        ("inlink", inlink_nodes),
        ("candidate visit", candidate_visit_nodes),
        ("right of entry", right_of_entry_nodes),
        ("leading confirmation", leading_nodes),
        ("arrived confirmation", arrived_nodes),
        ("alignment", alignment_nodes),
        ("target node names", target_node_names),
    )
    expected_count = len(payment_nodes)
    for column_label, column in columns_to_count:
        if len(column) != expected_count:
            raise RuntimeError(
                f"{column_label} Node count {len(column)} does not match "
                f"payment Node count {expected_count}. A missing Node result "
                "is not a normal empty-Node outcome."
            )

    arrived_confirmed_by_node: list[tuple[OrderControlTvtVisitKey, ...]] = []
    node_index = 0
    for payment_node in payment_nodes:
        node_name = _require_node_name(payment_node.node_name, "payment node_name")
        _require_same_node_name(
            node_name,
            selection_nodes[node_index].node_name,
            "selection",
            node_index,
        )
        _require_same_node_name(
            node_name,
            economic_nodes[node_index].node_name,
            "economic",
            node_index,
        )
        _require_same_node_name(
            node_name,
            local_nodes[node_index].node_name,
            "local",
            node_index,
        )
        _require_same_node_name(
            node_name,
            fifo_nodes[node_index].node_name,
            "fifo",
            node_index,
        )
        _require_same_node_name(
            node_name,
            trade_rank_nodes[node_index].node_name,
            "trade rank",
            node_index,
        )
        _require_same_node_name(
            node_name,
            concrete_nodes[node_index].node_name,
            "concrete buyer",
            node_index,
        )
        _require_same_node_name(
            node_name,
            inlink_nodes[node_index].node_name,
            "inlink",
            node_index,
        )
        _require_same_node_name(
            node_name,
            candidate_visit_nodes[node_index].node_name,
            "candidate visit",
            node_index,
        )
        _require_same_node_name(
            node_name,
            right_of_entry_nodes[node_index].node_name,
            "right of entry",
            node_index,
        )
        _require_same_node_name(
            node_name,
            leading_nodes[node_index].node_name,
            "leading confirmation",
            node_index,
        )
        _require_same_node_name(
            node_name,
            arrived_nodes[node_index].node_name,
            "arrived confirmation",
            node_index,
        )
        _require_same_node_name(
            node_name,
            alignment_nodes[node_index].node_name,
            "alignment",
            node_index,
        )
        _require_same_node_name(
            node_name,
            target_node_names[node_index],
            "target node names",
            node_index,
        )
        arrived_confirmed_by_node.append(
            _require_visit_key_tuple(
                arrived_nodes[node_index].confirmed_arrived_visit_keys,
                node_name=node_name,
                field_name="confirmed_arrived_visit_keys",
            )
        )
        node_index = node_index + 1

    return _SavedNodeColumns(
        payment_nodes=payment_nodes,
        selection_nodes=selection_nodes,
        economic_nodes=economic_nodes,
        local_nodes=local_nodes,
        candidate_visit_nodes=candidate_visit_nodes,
        leading_nodes=leading_nodes,
        arrived_confirmed_visit_keys_by_node=tuple(arrived_confirmed_by_node),
        collector=collector,
    )


def _require_node_name(node_name: object, field_name: str) -> str:
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"{field_name} must be a non-empty str; got {node_name!r}."
        )
    return node_name


def _require_same_node_name(
    expected_node_name: str,
    actual_node_name: object,
    source_label: str,
    node_index: int,
) -> None:
    if actual_node_name != expected_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: payment Node "
            f"{expected_node_name!r} but {source_label} has {actual_node_name!r}."
        )


def _build_one_node_final_rank(
    *,
    saved_columns: _SavedNodeColumns,
    node_index: int,
    payment_node_result: OrderControlTvtNodeMpPaymentAndCompensationResult,
) -> OrderControlTvtNodeMpFinalRankResult:
    if not isinstance(
        payment_node_result,
        OrderControlTvtNodeMpPaymentAndCompensationResult,
    ):
        raise RuntimeError(
            f"Payment Node result at index {node_index} must be "
            "OrderControlTvtNodeMpPaymentAndCompensationResult; got "
            f"type {type(payment_node_result).__name__}."
        )
    node_name = payment_node_result.node_name
    selection_node = saved_columns.selection_nodes[node_index]
    economic_node = saved_columns.economic_nodes[node_index]
    local_node = saved_columns.local_nodes[node_index]
    candidate_visit_node = saved_columns.candidate_visit_nodes[node_index]
    leading_node = saved_columns.leading_nodes[node_index]

    _require_payment_status_matches_selection(
        node_name=node_name,
        payment_node_result=payment_node_result,
        selection_node=selection_node,
    )
    decision_window_visit_keys = _require_visit_key_tuple(
        leading_node.decision_window_visit_keys,
        node_name=node_name,
        field_name="decision_window_visit_keys",
    )
    remaining_decision_window_visit_keys = _require_visit_key_tuple(
        leading_node.remaining_decision_window_visit_keys,
        node_name=node_name,
        field_name="remaining_decision_window_visit_keys",
    )
    confirmed_leading_visit_keys = _require_visit_key_tuple(
        leading_node.confirmed_leading_nonparticipating_visit_keys,
        node_name=node_name,
        field_name="confirmed_leading_nonparticipating_visit_keys",
    )
    _require_decision_window_decomposition(
        node_name=node_name,
        decision_window_visit_keys=decision_window_visit_keys,
        confirmed_leading_visit_keys=confirmed_leading_visit_keys,
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
    )
    build_status = _require_matching_build_status(
        node_name=node_name,
        candidate_visit_node=candidate_visit_node,
        local_node=local_node,
    )
    selected_candidate = payment_node_result.selected_candidate_economic_result
    if selected_candidate is not None:
        _require_selected_candidate_is_input_object(
            node_name=node_name,
            selected_candidate=selected_candidate,
            economic_node=economic_node,
        )

    # Remaining window empty: no visit is newly confirmed. Branch 4 if the
    # decision window was empty from the start. Branch 5 if visits existed
    # but were all preconfirmed. Neither case is baseline fallback.
    if len(remaining_decision_window_visit_keys) == 0:
        return _build_no_visits_node_result(
            node_name=node_name,
            selected_candidate=selected_candidate,
            payment_node_result=payment_node_result,
            decision_window_visit_keys=decision_window_visit_keys,
            build_status=build_status,
        )

    if selected_candidate is not None:
        return _build_selected_candidate_node_result(
            node_name=node_name,
            selected_candidate=selected_candidate,
            remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
            confirmed_leading_visit_keys=confirmed_leading_visit_keys,
            arrived_confirmed_visit_keys=(
                saved_columns.arrived_confirmed_visit_keys_by_node[node_index]
            ),
        )

    return _build_baseline_fallback_node_result(
        node_name=node_name,
        build_status=build_status,
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
        confirmed_leading_visit_keys=confirmed_leading_visit_keys,
        arrived_confirmed_visit_keys=(
            saved_columns.arrived_confirmed_visit_keys_by_node[node_index]
        ),
        collector=saved_columns.collector,
    )


def _require_payment_status_matches_selection(
    *,
    node_name: str,
    payment_node_result: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selection_node: OrderControlTvtNodeMpCandidateSelectionResult,
) -> None:
    """Check labels agree. Do not choose a final-rank branch from them alone."""
    payment_status = payment_node_result.payment_and_compensation_status
    selection_status = selection_node.selection_status
    selected_on_payment = payment_node_result.selected_candidate_economic_result
    selected_on_selection = selection_node.selected_candidate_economic_result
    buyer_records = payment_node_result.buyer_payment_records
    seller_records = payment_node_result.seller_compensation_records
    if not isinstance(buyer_records, tuple) or not isinstance(seller_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: payment record columns must be tuples."
        )

    if payment_status is OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED:
        if selection_status is not OrderControlTvtMpCandidateSelectionStatus.SELECTED:
            raise RuntimeError(
                f"Node {node_name!r}: payment status CALCULATED requires "
                "selection status SELECTED. Payment status is a result label, "
                "not a substitute for the saved selection."
            )
        if selected_on_payment is None or selected_on_selection is None:
            raise RuntimeError(
                f"Node {node_name!r}: payment status CALCULATED requires a "
                "selected candidate. This is not converted into fallback or "
                "NO_VISITS_TO_CONFIRM."
            )
        if selected_on_payment is not selected_on_selection:
            raise RuntimeError(
                f"Node {node_name!r}: payment selected candidate is not the "
                "same object as the selection selected candidate."
            )
        return

    if (
        payment_status
        is not OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
    ):
        raise RuntimeError(
            f"Node {node_name!r}: unexpected payment status {payment_status!r}."
        )
    if (
        selection_status
        is not OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    ):
        raise RuntimeError(
            f"Node {node_name!r}: payment status NO_SELECTED_CANDIDATE requires "
            "selection status NO_ECONOMICALLY_FEASIBLE_CANDIDATE. That label "
            "does not by itself mean economic infeasibility, an empty window, "
            "or baseline fallback."
        )
    if selected_on_payment is not None or selected_on_selection is not None:
        raise RuntimeError(
            f"Node {node_name!r}: NO_SELECTED_CANDIDATE requires selected "
            "candidate to be None."
        )
    if len(buyer_records) != 0 or len(seller_records) != 0:
        raise RuntimeError(
            f"Node {node_name!r}: NO_SELECTED_CANDIDATE requires empty payment "
            "and compensation records. Non-empty records are not an empty "
            "normal result."
        )


def _require_visit_key_tuple(
    visit_keys: object,
    *,
    node_name: str,
    field_name: str,
) -> tuple[OrderControlTvtVisitKey, ...]:
    if not isinstance(visit_keys, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a tuple; got "
            f"type {type(visit_keys).__name__}."
        )
    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    for visit_key in visit_keys:
        if (
            not isinstance(visit_key, tuple)
            or len(visit_key) != 2
            or not isinstance(visit_key[0], str)
            or visit_key[0] == ""
            or type(visit_key[1]) is not int
            or isinstance(visit_key[1], bool)
            or visit_key[1] < 1
        ):
            raise RuntimeError(
                f"Node {node_name!r}: {field_name} contains an invalid "
                f"VisitKey {visit_key!r}."
            )
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: {field_name} repeats VisitKey "
                f"{visit_key!r}. Duplicates are not dropped automatically."
            )
        seen_visit_keys.append(visit_key)
    return visit_keys


def _require_decision_window_decomposition(
    *,
    node_name: str,
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    expected_decision_window = (
        confirmed_leading_visit_keys + remaining_decision_window_visit_keys
    )
    if decision_window_visit_keys != expected_decision_window:
        raise RuntimeError(
            f"Node {node_name!r}: decision_window_visit_keys is not the "
            "leading preconfirmed prefix plus the remaining decision-window "
            "suffix. Saved window counts are inconsistent."
        )
    for visit_key in remaining_decision_window_visit_keys:
        if visit_key in confirmed_leading_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: remaining decision-window VisitKey "
                f"{visit_key!r} is already in the preconfirmed leading prefix. "
                "A preconfirmed visit is not newly confirmed and is not "
                "removed automatically."
            )


def _require_matching_build_status(
    *,
    node_name: str,
    candidate_visit_node: OrderControlTvtNodeCandidateVisitSetResult,
    local_node: OrderControlTvtNodeMpLocalVirtualCalculationResult,
) -> OrderControlTvtCandidateVisitSetStatus:
    candidate_status = candidate_visit_node.build_status
    local_status = local_node.build_status
    if not isinstance(candidate_status, OrderControlTvtCandidateVisitSetStatus):
        raise RuntimeError(
            f"Node {node_name!r}: candidate visit build_status must be "
            "OrderControlTvtCandidateVisitSetStatus; got "
            f"{candidate_status!r}."
        )
    if candidate_status is not local_status:
        raise RuntimeError(
            f"Node {node_name!r}: candidate visit build_status "
            f"{candidate_status!r} does not match local virtual-calculation "
            f"build_status {local_status!r}."
        )
    return candidate_status


def _require_selected_candidate_is_input_object(
    *,
    node_name: str,
    selected_candidate: object,
    economic_node: OrderControlTvtNodeMpEconomicEvaluationResult,
) -> None:
    if not isinstance(
        selected_candidate,
        OrderControlTvtMpCandidateEconomicEvaluationResult,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate must be "
            "OrderControlTvtMpCandidateEconomicEvaluationResult; got "
            f"type {type(selected_candidate).__name__}."
        )
    economic_candidates = economic_node.candidate_economic_evaluation_results
    if not isinstance(economic_candidates, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: candidate_economic_evaluation_results must "
            "be a tuple."
        )
    found_same_object = False
    for economic_candidate in economic_candidates:
        if economic_candidate is selected_candidate:
            found_same_object = True
            break
    if not found_same_object:
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate is not the same object "
            "as a candidate in the saved economic result. A copied candidate "
            "is not accepted, and this inconsistency is not converted into "
            "baseline fallback or NO_VISITS_TO_CONFIRM."
        )


def _build_no_visits_node_result(
    *,
    node_name: str,
    selected_candidate: object,
    payment_node_result: OrderControlTvtNodeMpPaymentAndCompensationResult,
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> OrderControlTvtNodeMpFinalRankResult:
    """
    Branch 4 or branch 5.

    Both return NO_VISITS_TO_CONFIRM and an empty column. Branch 4 is an
    empty decision window from the start. Branch 5 is a non-empty decision
    window whose visits were all preconfirmed before this component.
    """
    if selected_candidate is not None:
        raise RuntimeError(
            f"Node {node_name!r}: a selected candidate exists while the "
            "remaining decision window is empty. Saved counts contradict a "
            "selected candidate. This is not converted into "
            "NO_VISITS_TO_CONFIRM."
        )
    if (
        payment_node_result.payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    ):
        raise RuntimeError(
            f"Node {node_name!r}: payment status CALCULATED while the "
            "remaining decision window is empty."
        )
    if (
        build_status
        is not OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
    ):
        raise RuntimeError(
            f"Node {node_name!r}: remaining decision window is empty, so "
            "build_status must be NOT_BUILT_NO_RIGHT_OF_ENTRY; got "
            f"{build_status!r}. Information shortage and completed candidate "
            "review are not recorded as NO_VISITS_TO_CONFIRM."
        )
    if len(decision_window_visit_keys) == 0:
        # Branch 4: no decision-window visit existed, so no TVT review ran.
        return _empty_no_visits_result(node_name)
    # Branch 5: visits existed and were already confirmed. Do not repeat them.
    return _empty_no_visits_result(node_name)


def _empty_no_visits_result(node_name: str) -> OrderControlTvtNodeMpFinalRankResult:
    return OrderControlTvtNodeMpFinalRankResult(
        node_name=node_name,
        final_rank_status=OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM,
        selected_candidate_economic_result=None,
        final_rank_visits=(),
    )


def _build_selected_candidate_node_result(
    *,
    node_name: str,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    arrived_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtNodeMpFinalRankResult:
    """
    Branch 1.

    Reuse saved partition 3 then partition 4. Do not rebuild the selected
    rank and do not use payment amounts as rank material.
    """
    binding_sequence = _require_binding_rank_sequence(
        node_name=node_name,
        selected_candidate=selected_candidate,
    )
    _require_binding_counts_match_remaining_window(
        node_name=node_name,
        binding_sequence=binding_sequence,
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
    )
    trade_scope_visits = _require_partition_visits(
        node_name=node_name,
        visits=binding_sequence.trade_scope_of_this_candidate_visits,
        expected_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        field_name="trade_scope_of_this_candidate_visits",
    )
    outside_visits = _require_partition_visits(
        node_name=node_name,
        visits=binding_sequence.outside_trade_scope_inside_k_fixed_visits,
        expected_partition=(
            OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED
        ),
        field_name="outside_trade_scope_inside_k_fixed_visits",
    )
    if len(trade_scope_visits) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate partition 3 is empty. "
            "A selected candidate must confirm at least the trade-scope visits."
        )
    already_confirmed_visit_keys = _already_confirmed_visit_keys(
        binding_sequence=binding_sequence,
        confirmed_leading_visit_keys=confirmed_leading_visit_keys,
        arrived_confirmed_visit_keys=arrived_confirmed_visit_keys,
    )
    _require_saved_binding_order(
        node_name=node_name,
        binding_sequence=binding_sequence,
        trade_scope_visits=trade_scope_visits,
        outside_visits=outside_visits,
        already_confirmed_visit_keys=already_confirmed_visit_keys,
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
    )

    final_rank_visits: list[OrderControlTvtMpFinalRankVisitRecord] = []
    next_local_rank = 1
    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    for binding_visit in trade_scope_visits:
        final_rank_visits.append(
            _final_rank_record_from_binding_visit(
                node_name=node_name,
                binding_visit=binding_visit,
                final_local_rank=next_local_rank,
                finalization_source=(
                    OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE
                ),
                seen_visit_keys=seen_visit_keys,
                already_confirmed_visit_keys=already_confirmed_visit_keys,
            )
        )
        next_local_rank = next_local_rank + 1
    for binding_visit in outside_visits:
        final_rank_visits.append(
            _final_rank_record_from_binding_visit(
                node_name=node_name,
                binding_visit=binding_visit,
                final_local_rank=next_local_rank,
                finalization_source=OrderControlTvtMpFinalizationSource.BASELINE,
                seen_visit_keys=seen_visit_keys,
                already_confirmed_visit_keys=already_confirmed_visit_keys,
            )
        )
        next_local_rank = next_local_rank + 1

    return OrderControlTvtNodeMpFinalRankResult(
        node_name=node_name,
        final_rank_status=OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS,
        selected_candidate_economic_result=selected_candidate,
        final_rank_visits=tuple(final_rank_visits),
    )


def _require_binding_rank_sequence(
    *,
    node_name: str,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
) -> OrderControlTvtMpLocalBindingRankSequence:
    local_result = selected_candidate.candidate_local_virtual_calculation_result
    binding_sequence = getattr(local_result, "binding_rank_sequence", None)
    if not isinstance(binding_sequence, OrderControlTvtMpLocalBindingRankSequence):
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate has no saved "
            "OrderControlTvtMpLocalBindingRankSequence. The selected rank is "
            "not rebuilt and this is not converted into baseline fallback."
        )
    if binding_sequence.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: binding rank sequence node_name "
            f"{binding_sequence.node_name!r} does not match."
        )
    return binding_sequence


def _require_binding_counts_match_remaining_window(
    *,
    node_name: str,
    binding_sequence: OrderControlTvtMpLocalBindingRankSequence,
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    k_last_buyer = binding_sequence.k_last_buyer
    k_decision_window = binding_sequence.k_decision_window
    k_fixed = binding_sequence.k_fixed
    trade_scope_count = len(binding_sequence.trade_scope_of_this_candidate_visits)
    outside_count = len(binding_sequence.outside_trade_scope_inside_k_fixed_visits)
    if type(k_last_buyer) is not int or type(k_decision_window) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: k_last_buyer and k_decision_window must be "
            "Python ints."
        )
    if type(k_fixed) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: k_fixed must be a Python int."
        )
    if k_last_buyer != trade_scope_count:
        raise RuntimeError(
            f"Node {node_name!r}: k_last_buyer {k_last_buyer} does not match "
            f"partition 3 length {trade_scope_count}."
        )
    if k_decision_window != len(remaining_decision_window_visit_keys):
        raise RuntimeError(
            f"Node {node_name!r}: k_decision_window {k_decision_window} does "
            "not match remaining decision-window length "
            f"{len(remaining_decision_window_visit_keys)}."
        )
    if k_fixed != max(k_last_buyer, k_decision_window):
        raise RuntimeError(
            f"Node {node_name!r}: k_fixed {k_fixed} is not "
            "max(k_last_buyer, k_decision_window)."
        )
    if k_last_buyer < k_decision_window:
        expected_outside_count = k_decision_window - k_last_buyer
    else:
        expected_outside_count = 0
    if outside_count != expected_outside_count:
        raise RuntimeError(
            f"Node {node_name!r}: partition 4 length {outside_count} does not "
            f"match the saved k_fixed relationship {expected_outside_count}."
        )


def _require_partition_visits(
    *,
    node_name: str,
    visits: object,
    expected_partition: OrderControlTvtMpLocalBindingPartition,
    field_name: str,
) -> tuple[OrderControlTvtMpLocalBindingRankVisit, ...]:
    if not isinstance(visits, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a tuple; got "
            f"type {type(visits).__name__}."
        )
    for binding_visit in visits:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"Node {node_name!r}: {field_name} contains "
                f"type {type(binding_visit).__name__}, not a binding visit."
            )
        if binding_visit.binding_partition is not expected_partition:
            raise RuntimeError(
                f"Node {node_name!r}: {field_name} VisitKey "
                f"{binding_visit.visit_key!r} has binding partition "
                f"{binding_visit.binding_partition!r}, expected "
                f"{expected_partition!r}."
            )
    return visits


def _already_confirmed_visit_keys(
    *,
    binding_sequence: OrderControlTvtMpLocalBindingRankSequence,
    confirmed_leading_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    arrived_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> tuple[OrderControlTvtVisitKey, ...]:
    confirmed_visit_keys: list[OrderControlTvtVisitKey] = []
    for binding_visit in binding_sequence.confirmed_before_this_baseline_visits:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                "Partition 1 must contain saved binding visits; got "
                f"type {type(binding_visit).__name__}."
            )
        confirmed_visit_keys.append(binding_visit.visit_key)
    for binding_visit in binding_sequence.preconfirmed_by_this_baseline_visits:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                "Partition 2 must contain saved binding visits; got "
                f"type {type(binding_visit).__name__}."
            )
        confirmed_visit_keys.append(binding_visit.visit_key)
    for visit_key in confirmed_leading_visit_keys:
        if visit_key not in confirmed_visit_keys:
            confirmed_visit_keys.append(visit_key)
    for visit_key in arrived_confirmed_visit_keys:
        if visit_key not in confirmed_visit_keys:
            confirmed_visit_keys.append(visit_key)
    return tuple(confirmed_visit_keys)


def _require_saved_binding_order(
    *,
    node_name: str,
    binding_sequence: OrderControlTvtMpLocalBindingRankSequence,
    trade_scope_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    outside_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    already_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    partition_1 = binding_sequence.confirmed_before_this_baseline_visits
    partition_2 = binding_sequence.preconfirmed_by_this_baseline_visits
    if not isinstance(partition_1, tuple) or not isinstance(partition_2, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: partitions 1 and 2 must be tuples."
        )
    saved_order = binding_sequence.visits_in_binding_order
    if not isinstance(saved_order, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: visits_in_binding_order must be a tuple."
        )
    expected_order = partition_1 + partition_2 + trade_scope_visits + outside_visits
    if saved_order != expected_order:
        raise RuntimeError(
            f"Node {node_name!r}: saved binding order does not equal "
            "partition 1, partition 2, partition 3, then partition 4."
        )
    expected_binding_rank = 1
    for binding_visit in saved_order:
        if binding_visit.binding_rank != expected_binding_rank:
            raise RuntimeError(
                f"Node {node_name!r}: binding rank {binding_visit.binding_rank} "
                f"for VisitKey {binding_visit.visit_key!r} is not the saved "
                f"consecutive rank {expected_binding_rank}."
            )
        expected_binding_rank = expected_binding_rank + 1
    for binding_visit in trade_scope_visits:
        if binding_visit.visit_key in already_confirmed_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 3 VisitKey "
                f"{binding_visit.visit_key!r} is already confirmed in "
                "partition 1 or 2. Already confirmed ranks are not overwritten."
            )
    k_last_buyer = binding_sequence.k_last_buyer
    expected_outside_keys = remaining_decision_window_visit_keys[k_last_buyer:]
    outside_keys: list[OrderControlTvtVisitKey] = []
    for binding_visit in outside_visits:
        outside_keys.append(binding_visit.visit_key)
        if binding_visit.visit_key in already_confirmed_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 4 VisitKey "
                f"{binding_visit.visit_key!r} is already confirmed. Already "
                "confirmed ranks and formal routes are not overwritten."
            )
    if tuple(outside_keys) != expected_outside_keys:
        raise RuntimeError(
            f"Node {node_name!r}: partition 4 VisitKeys {tuple(outside_keys)!r} "
            "do not match the remaining decision-window suffix "
            f"{expected_outside_keys!r}."
        )


def _final_rank_record_from_binding_visit(
    *,
    node_name: str,
    binding_visit: OrderControlTvtMpLocalBindingRankVisit,
    final_local_rank: int,
    finalization_source: OrderControlTvtMpFinalizationSource,
    seen_visit_keys: list[OrderControlTvtVisitKey],
    already_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtMpFinalRankVisitRecord:
    visit_key = binding_visit.visit_key
    if visit_key in seen_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is repeated in "
            "partitions 3 and 4. Duplicates are not dropped."
        )
    if visit_key in already_confirmed_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} was already confirmed "
            "and cannot be placed in the new final-rank column."
        )
    seen_visit_keys.append(visit_key)
    if not isinstance(
        binding_visit.route_origin,
        OrderControlTvtMpLocalBindingRouteOrigin,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} route_origin "
            f"{binding_visit.route_origin!r} is not a saved route origin."
        )
    formal_route = _require_non_empty_route(
        binding_visit.route_next_link_name,
        node_name=node_name,
        visit_key=visit_key,
    )
    return OrderControlTvtMpFinalRankVisitRecord(
        visit_key=visit_key,
        final_local_rank=final_local_rank,
        formal_route_next_link_name=formal_route,
        finalization_source=finalization_source,
    )


def _require_non_empty_route(
    route_next_link_name: object,
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> str:
    if route_next_link_name is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} formal route is "
            "missing. A route is not guessed."
        )
    if not isinstance(route_next_link_name, str) or route_next_link_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} formal route must be "
            f"a non-empty str; got {route_next_link_name!r}. A route is not guessed."
        )
    return route_next_link_name


def _build_baseline_fallback_node_result(
    *,
    node_name: str,
    build_status: OrderControlTvtCandidateVisitSetStatus,
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    arrived_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    collector: object,
) -> OrderControlTvtNodeMpFinalRankResult:
    """
    Branch 2 or branch 3.

    Both confirm the whole remaining decision window in saved baseline order.
    Branch 2 is a completed candidate review with zero adopted candidates.
    Branch 3 is missing baseline information and is not economic infeasibility.
    """
    if (
        build_status
        is OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    ):
        # Branch 2 cause stays on the upstream results. Status is fallback.
        pass
    elif build_status in _INFORMATION_SHORTAGE_STATUSES:
        # Branch 3: do not relabel information shortage as economic failure.
        pass
    else:
        raise RuntimeError(
            f"Node {node_name!r}: remaining decision window has "
            f"{len(remaining_decision_window_visit_keys)} visits and no "
            f"selected candidate, but build_status is {build_status!r}. "
            "That status does not match rejected-candidate fallback or "
            "information-shortage fallback."
        )

    final_rank_visits: list[OrderControlTvtMpFinalRankVisitRecord] = []
    next_local_rank = 1
    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    for visit_key in remaining_decision_window_visit_keys:
        if visit_key in confirmed_leading_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: fallback VisitKey {visit_key!r} was "
                "already preconfirmed. Already confirmed ranks are not "
                "overwritten and duplicates are not dropped."
            )
        if visit_key in arrived_confirmed_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: fallback VisitKey {visit_key!r} was "
                "already confirmed before this baseline. Already confirmed "
                "formal routes are not overwritten."
            )
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: fallback VisitKey {visit_key!r} is "
                "repeated. Duplicates are not dropped."
            )
        seen_visit_keys.append(visit_key)
        formal_route = _formal_route_from_collector(
            collector=collector,
            node_name=node_name,
            visit_key=visit_key,
        )
        final_rank_visits.append(
            OrderControlTvtMpFinalRankVisitRecord(
                visit_key=visit_key,
                final_local_rank=next_local_rank,
                formal_route_next_link_name=formal_route,
                finalization_source=OrderControlTvtMpFinalizationSource.BASELINE,
            )
        )
        next_local_rank = next_local_rank + 1

    if len(final_rank_visits) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: baseline fallback requires at least one "
            "remaining decision-window visit."
        )
    return OrderControlTvtNodeMpFinalRankResult(
        node_name=node_name,
        final_rank_status=OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS,
        selected_candidate_economic_result=None,
        final_rank_visits=tuple(final_rank_visits),
    )


def _formal_route_from_collector(
    *,
    collector: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> str:
    """Read the saved baseline arrival route. Do not search traffic objects."""
    snapshot_reader = getattr(collector, "get_baseline_visit_snapshot", None)
    if not callable(snapshot_reader):
        raise RuntimeError(
            f"Node {node_name!r}: baseline collector cannot return a saved "
            f"snapshot for VisitKey {visit_key!r}."
        )
    vehicle_name, visit_id = visit_key
    snapshot = snapshot_reader(vehicle_name, visit_id)
    if snapshot is None:
        raise RuntimeError(
            f"Node {node_name!r}: baseline collector has no snapshot for "
            f"VisitKey {visit_key!r}. The formal route is not guessed."
        )
    if not isinstance(snapshot, dict):
        raise RuntimeError(
            f"Node {node_name!r}: baseline snapshot for VisitKey {visit_key!r} "
            f"must be a dict; got type {type(snapshot).__name__}."
        )
    return _require_non_empty_route(
        snapshot.get("route_next_link_name"),
        node_name=node_name,
        visit_key=visit_key,
    )
