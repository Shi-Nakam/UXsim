"""
TVT-MP final consistency validation.

This module reads one saved final-rank set and checks that the final rank,
the payment and compensation records, and the upstream objects they already
reference describe the same decision. It returns one frozen approval result
only when every target Node agrees.

It does not write a rank ledger, does not update monetary attributes, does
not call atomic apply, and does not rerun upstream calculations. Success
means the saved frozen results agree. It does not mean a later write to the
live ledger will succeed.
"""

from __future__ import annotations

from dataclasses import dataclass

from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
)
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
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtMpSellerEconomicRecord,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpFifoInspectionSetResult,
)
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankSetResult,
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalRankVisitRecord,
    OrderControlTvtMpFinalizationSource,
    OrderControlTvtNodeMpFinalRankResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankSetResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpBuyerPaymentRecord,
    OrderControlTvtMpPaymentAndCompensationSetResult,
    OrderControlTvtMpPaymentAndCompensationStatus,
    OrderControlTvtMpSellerCompensationRecord,
    OrderControlTvtNodeMpPaymentAndCompensationResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtRightOfEntrySelectionResult,
)


_INFORMATION_SHORTAGE_STATUSES = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
)


@dataclass(frozen=True)
class OrderControlTvtMpFinalConsistencyValidationSetResult:
    """Approval of one final-rank set. The set itself is not copied."""

    final_rank_set_result: OrderControlTvtMpFinalRankSetResult


@dataclass(frozen=True)
class _SavedNodeColumns:
    """Aligned columns reached from one final-rank set. Same objects."""

    final_rank_nodes: tuple[OrderControlTvtNodeMpFinalRankResult, ...]
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


def validate_tvt_mp_final_consistency(
    final_rank_set_result,
) -> OrderControlTvtMpFinalConsistencyValidationSetResult:
    """
    Check every target Node in one saved final-rank set.

    The only public input is that set. Empty-window Nodes, information-shortage
    Nodes, rejected-candidate Nodes, fully preconfirmed Nodes, and selected
    Nodes are all read from it. This function does not search live traffic
    objects, does not read a rank ledger, and returns no partial approval.
    """
    final_rank_set = _require_final_rank_set(final_rank_set_result)
    saved_columns = _saved_node_columns_from_final_rank_set(final_rank_set)

    node_index = 0
    for final_rank_node in saved_columns.final_rank_nodes:
        _validate_one_node(
            saved_columns=saved_columns,
            node_index=node_index,
            final_rank_node=final_rank_node,
        )
        node_index = node_index + 1

    return OrderControlTvtMpFinalConsistencyValidationSetResult(
        final_rank_set_result=final_rank_set,
    )


def _require_final_rank_set(value: object) -> OrderControlTvtMpFinalRankSetResult:
    if not isinstance(value, OrderControlTvtMpFinalRankSetResult):
        raise ValueError(
            "validate_tvt_mp_final_consistency accepts only "
            "OrderControlTvtMpFinalRankSetResult; got "
            f"type {type(value).__name__}."
        )
    return value


def _require_tuple_column(column: object, column_name: str) -> tuple:
    if not isinstance(column, tuple):
        raise RuntimeError(
            f"{column_name} must be a tuple; got type {type(column).__name__}. "
            "A missing Node column is not a normal empty-Node outcome."
        )
    return column


def _require_node_name(node_name: object, field_name: str) -> str:
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"{field_name} must be a non-empty str; got {node_name!r}."
        )
    return node_name


def _require_same_node_name(
    expected_name: str,
    actual_name: object,
    column_label: str,
    node_index: int,
) -> None:
    if actual_name != expected_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: final rank Node "
            f"{expected_name!r} does not match {column_label} Node "
            f"{actual_name!r}. A missing Node is not a normal empty result."
        )


def _saved_node_columns_from_final_rank_set(
    final_rank_set: OrderControlTvtMpFinalRankSetResult,
) -> _SavedNodeColumns:
    """
    Walk the saved reference chain once and keep the same objects.

    This is the only place that reaches payment, selection, economics,
    binding partitions, decision windows, build status, and the collector.
    """
    final_rank_nodes = _require_tuple_column(
        final_rank_set.node_final_rank_results,
        "node_final_rank_results",
    )
    payment_set = final_rank_set.payment_and_compensation_set_result
    if not isinstance(payment_set, OrderControlTvtMpPaymentAndCompensationSetResult):
        raise RuntimeError(
            "payment_and_compensation_set_result must be "
            "OrderControlTvtMpPaymentAndCompensationSetResult; got "
            f"type {type(payment_set).__name__}."
        )
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
    if not isinstance(arrived_set, OrderControlTvtArrivedUndeterminedConfirmationResult):
        raise RuntimeError(
            "arrived_confirmation_result must be "
            "OrderControlTvtArrivedUndeterminedConfirmationResult; got "
            f"type {type(arrived_set).__name__}."
        )
    arrived_nodes = _require_tuple_column(
        arrived_set.node_confirmation_results,
        "arrived node_confirmation_results",
    )
    alignment_fork = arrived_set.alignment_fork_result
    if not isinstance(alignment_fork, OrderControlTvtBaselineForkAlignmentResult):
        raise RuntimeError(
            "alignment_fork_result must be "
            "OrderControlTvtBaselineForkAlignmentResult; got "
            f"type {type(alignment_fork).__name__}."
        )
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
        ("final rank", final_rank_nodes),
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
    expected_count = len(final_rank_nodes)
    for column_label, column in columns_to_count:
        if len(column) != expected_count:
            raise RuntimeError(
                f"{column_label} Node count {len(column)} does not match "
                f"final rank Node count {expected_count}. A missing Node "
                "result is not a normal empty-Node outcome."
            )

    arrived_confirmed_by_node: list[tuple[OrderControlTvtVisitKey, ...]] = []
    node_index = 0
    for final_rank_node in final_rank_nodes:
        if not isinstance(final_rank_node, OrderControlTvtNodeMpFinalRankResult):
            raise RuntimeError(
                f"Final rank Node result at index {node_index} must be "
                "OrderControlTvtNodeMpFinalRankResult; got "
                f"type {type(final_rank_node).__name__}."
            )
        node_name = _require_node_name(
            final_rank_node.node_name,
            "final rank node_name",
        )
        _require_same_node_name(
            node_name,
            payment_nodes[node_index].node_name,
            "payment",
            node_index,
        )
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
        final_rank_nodes=final_rank_nodes,
        payment_nodes=payment_nodes,
        selection_nodes=selection_nodes,
        economic_nodes=economic_nodes,
        local_nodes=local_nodes,
        candidate_visit_nodes=candidate_visit_nodes,
        leading_nodes=leading_nodes,
        arrived_confirmed_visit_keys_by_node=tuple(arrived_confirmed_by_node),
        collector=collector,
    )


def _validate_one_node(
    *,
    saved_columns: _SavedNodeColumns,
    node_index: int,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
) -> None:
    node_name = final_rank_node.node_name
    payment_node = saved_columns.payment_nodes[node_index]
    selection_node = saved_columns.selection_nodes[node_index]
    economic_node = saved_columns.economic_nodes[node_index]
    local_node = saved_columns.local_nodes[node_index]
    candidate_visit_node = saved_columns.candidate_visit_nodes[node_index]
    leading_node = saved_columns.leading_nodes[node_index]

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
    final_rank_visits = _require_final_rank_visits(
        node_name=node_name,
        final_rank_visits=final_rank_node.final_rank_visits,
    )
    _require_money_record_tuples(
        node_name=node_name,
        payment_node=payment_node,
    )

    final_status = final_rank_node.final_rank_status
    if final_status is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
        # Branch 1. Do not relabel a broken selected candidate as fallback.
        _validate_selected_candidate_node(
            node_name=node_name,
            final_rank_node=final_rank_node,
            final_rank_visits=final_rank_visits,
            payment_node=payment_node,
            selection_node=selection_node,
            economic_node=economic_node,
            remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
            confirmed_leading_visit_keys=confirmed_leading_visit_keys,
            arrived_confirmed_visit_keys=(
                saved_columns.arrived_confirmed_visit_keys_by_node[node_index]
            ),
        )
        return

    if final_status is OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS:
        # Branch 2 or 3. build_status keeps the cause. Both use fallback.
        _validate_fallback_node(
            node_name=node_name,
            final_rank_visits=final_rank_visits,
            payment_node=payment_node,
            selection_node=selection_node,
            final_rank_node=final_rank_node,
            build_status=build_status,
            remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
            confirmed_leading_visit_keys=confirmed_leading_visit_keys,
            arrived_confirmed_visit_keys=(
                saved_columns.arrived_confirmed_visit_keys_by_node[node_index]
            ),
            collector=saved_columns.collector,
        )
        return

    if final_status is OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM:
        # Branch 4 or 5. The shared status is not a shared cause.
        _validate_no_visits_node(
            node_name=node_name,
            final_rank_visits=final_rank_visits,
            payment_node=payment_node,
            selection_node=selection_node,
            final_rank_node=final_rank_node,
            build_status=build_status,
            decision_window_visit_keys=decision_window_visit_keys,
            remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
        )
        return

    raise RuntimeError(
        f"Node {node_name!r}: unexpected final rank status {final_status!r}."
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
            "suffix. Branch 4 and branch 5 cannot be told apart from a "
            "broken window."
        )
    for visit_key in remaining_decision_window_visit_keys:
        if visit_key in confirmed_leading_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: remaining decision-window VisitKey "
                f"{visit_key!r} is already preconfirmed. A preconfirmed visit "
                "is not newly confirmed and is not dropped automatically."
            )


def _require_matching_build_status(
    *,
    node_name: str,
    candidate_visit_node: OrderControlTvtNodeCandidateVisitSetResult,
    local_node: OrderControlTvtNodeMpLocalVirtualCalculationResult,
) -> OrderControlTvtCandidateVisitSetStatus:
    if not isinstance(candidate_visit_node, OrderControlTvtNodeCandidateVisitSetResult):
        raise RuntimeError(
            f"Node {node_name!r}: candidate visit Node result has type "
            f"{type(candidate_visit_node).__name__}."
        )
    if not isinstance(local_node, OrderControlTvtNodeMpLocalVirtualCalculationResult):
        raise RuntimeError(
            f"Node {node_name!r}: local virtual calculation Node result has "
            f"type {type(local_node).__name__}."
        )
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
            f"{candidate_status!r} does not match local virtual calculation "
            f"build_status {local_status!r}."
        )
    return candidate_status


def _require_final_rank_visits(
    *,
    node_name: str,
    final_rank_visits: object,
) -> tuple[OrderControlTvtMpFinalRankVisitRecord, ...]:
    if not isinstance(final_rank_visits, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: final_rank_visits must be a tuple; got "
            f"type {type(final_rank_visits).__name__}."
        )
    for final_rank_visit in final_rank_visits:
        if not isinstance(final_rank_visit, OrderControlTvtMpFinalRankVisitRecord):
            raise RuntimeError(
                f"Node {node_name!r}: final rank column contains "
                f"type {type(final_rank_visit).__name__}, not a final rank "
                "visit record."
            )
    return final_rank_visits


def _require_money_record_tuples(
    *,
    node_name: str,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
) -> None:
    if not isinstance(payment_node, OrderControlTvtNodeMpPaymentAndCompensationResult):
        raise RuntimeError(
            f"Node {node_name!r}: payment Node result has type "
            f"{type(payment_node).__name__}."
        )
    if not isinstance(payment_node.buyer_payment_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: buyer_payment_records must be a tuple."
        )
    if not isinstance(payment_node.seller_compensation_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: seller_compensation_records must be a tuple."
        )


def _require_empty_money_records(
    *,
    node_name: str,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    cause: str,
) -> None:
    if len(payment_node.buyer_payment_records) != 0:
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires empty buyer payment "
            "records. A monetary record is not created when no candidate "
            "was selected."
        )
    if len(payment_node.seller_compensation_records) != 0:
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires empty seller compensation "
            "records. A monetary record is not created when no candidate "
            "was selected."
        )


def _require_no_selected_labels(
    *,
    node_name: str,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selection_node: OrderControlTvtNodeMpCandidateSelectionResult,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    cause: str,
) -> None:
    if not isinstance(selection_node, OrderControlTvtNodeMpCandidateSelectionResult):
        raise RuntimeError(
            f"Node {node_name!r}: selection Node result has type "
            f"{type(selection_node).__name__}."
        )
    if (
        payment_node.payment_and_compensation_status
        is not OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
    ):
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires payment status "
            "NO_SELECTED_CANDIDATE. Payment status is a label, not a reason "
            "to invent a selected candidate."
        )
    if (
        selection_node.selection_status
        is not OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    ):
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires selection status "
            "NO_ECONOMICALLY_FEASIBLE_CANDIDATE. That label covers an empty "
            "window, information shortage, and a completed review with no "
            "adopted candidate."
        )
    if payment_node.selected_candidate_economic_result is not None:
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires payment selected candidate "
            "to be None."
        )
    if selection_node.selected_candidate_economic_result is not None:
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires selection selected "
            "candidate to be None."
        )
    if final_rank_node.selected_candidate_economic_result is not None:
        raise RuntimeError(
            f"Node {node_name!r}: {cause} requires final rank selected "
            "candidate to be None."
        )


def _validate_selected_candidate_node(
    *,
    node_name: str,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...],
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selection_node: OrderControlTvtNodeMpCandidateSelectionResult,
    economic_node: OrderControlTvtNodeMpEconomicEvaluationResult,
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    arrived_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    if not isinstance(selection_node, OrderControlTvtNodeMpCandidateSelectionResult):
        raise RuntimeError(
            f"Node {node_name!r}: selection Node result has type "
            f"{type(selection_node).__name__}."
        )
    if not isinstance(economic_node, OrderControlTvtNodeMpEconomicEvaluationResult):
        raise RuntimeError(
            f"Node {node_name!r}: economic Node result has type "
            f"{type(economic_node).__name__}."
        )
    if (
        payment_node.payment_and_compensation_status
        is not OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    ):
        raise RuntimeError(
            f"Node {node_name!r}: SELECTED_CANDIDATE_RANKS requires payment "
            "status CALCULATED."
        )
    if (
        selection_node.selection_status
        is not OrderControlTvtMpCandidateSelectionStatus.SELECTED
    ):
        raise RuntimeError(
            f"Node {node_name!r}: SELECTED_CANDIDATE_RANKS requires selection "
            "status SELECTED."
        )
    if len(remaining_decision_window_visit_keys) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: a selected candidate cannot be approved "
            "when the remaining decision window is empty. This is not "
            "converted into NO_VISITS_TO_CONFIRM."
        )
    selected_candidate = _require_same_selected_candidate(
        node_name=node_name,
        final_rank_node=final_rank_node,
        payment_node=payment_node,
        selection_node=selection_node,
        economic_node=economic_node,
    )
    binding_sequence = _require_binding_rank_sequence(
        node_name=node_name,
        selected_candidate=selected_candidate,
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
            f"Node {node_name!r}: selected candidate partition 3 is empty."
        )
    already_confirmed_visit_keys = _already_confirmed_visit_keys(
        binding_sequence=binding_sequence,
        confirmed_leading_visit_keys=confirmed_leading_visit_keys,
        arrived_confirmed_visit_keys=arrived_confirmed_visit_keys,
    )
    _validate_buyer_payment_correspondence(
        node_name=node_name,
        selected_candidate=selected_candidate,
        payment_node=payment_node,
        trade_scope_visits=trade_scope_visits,
    )
    _validate_seller_compensation_correspondence(
        node_name=node_name,
        selected_candidate=selected_candidate,
        payment_node=payment_node,
        trade_scope_visits=trade_scope_visits,
    )
    _require_buyer_and_seller_keys_are_disjoint(
        node_name=node_name,
        payment_node=payment_node,
    )
    _require_no_money_on_nonparticipants_or_partition_4(
        node_name=node_name,
        payment_node=payment_node,
        trade_scope_visits=trade_scope_visits,
        outside_visits=outside_visits,
    )
    _require_final_rank_matches_partitions_3_and_4(
        node_name=node_name,
        final_rank_visits=final_rank_visits,
        trade_scope_visits=trade_scope_visits,
        outside_visits=outside_visits,
        already_confirmed_visit_keys=already_confirmed_visit_keys,
    )


def _require_same_selected_candidate(
    *,
    node_name: str,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selection_node: OrderControlTvtNodeMpCandidateSelectionResult,
    economic_node: OrderControlTvtNodeMpEconomicEvaluationResult,
) -> OrderControlTvtMpCandidateEconomicEvaluationResult:
    """Equal values are not enough. The four references must be one object."""
    final_selected = final_rank_node.selected_candidate_economic_result
    payment_selected = payment_node.selected_candidate_economic_result
    selection_selected = selection_node.selected_candidate_economic_result
    if not isinstance(
        final_selected,
        OrderControlTvtMpCandidateEconomicEvaluationResult,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: SELECTED_CANDIDATE_RANKS requires a "
            "selected candidate on the final rank Node. This is not converted "
            "into baseline fallback."
        )
    if payment_selected is not final_selected:
        raise RuntimeError(
            f"Node {node_name!r}: payment selected candidate is not the same "
            "object as the final rank selected candidate."
        )
    if selection_selected is not final_selected:
        raise RuntimeError(
            f"Node {node_name!r}: selection selected candidate is not the "
            "same object as the final rank selected candidate."
        )
    economic_candidates = economic_node.candidate_economic_evaluation_results
    if not isinstance(economic_candidates, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: candidate_economic_evaluation_results must "
            "be a tuple."
        )
    found_same_object = False
    for economic_candidate in economic_candidates:
        if economic_candidate is final_selected:
            found_same_object = True
    if found_same_object is False:
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate is not the same object "
            "as an entry in the economic candidate tuple. A copied candidate "
            "is not accepted."
        )
    return final_selected


def _require_binding_rank_sequence(
    *,
    node_name: str,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
) -> OrderControlTvtMpLocalBindingRankSequence:
    local_result = selected_candidate.candidate_local_virtual_calculation_result
    binding_sequence = getattr(local_result, "binding_rank_sequence", None)
    if not isinstance(binding_sequence, OrderControlTvtMpLocalBindingRankSequence):
        raise RuntimeError(
            f"Node {node_name!r}: selected candidate has no saved binding "
            "rank sequence. The final rank column is not rebuilt."
        )
    if binding_sequence.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: binding rank sequence node_name "
            f"{binding_sequence.node_name!r} does not match."
        )
    return binding_sequence


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
                f"type {type(binding_visit).__name__}."
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
    partition_1 = binding_sequence.confirmed_before_this_baseline_visits
    partition_2 = binding_sequence.preconfirmed_by_this_baseline_visits
    if not isinstance(partition_1, tuple) or not isinstance(partition_2, tuple):
        raise RuntimeError(
            "Partitions 1 and 2 must be tuples so already confirmed visits "
            "can be kept out of the new final rank column."
        )
    for binding_visit in partition_1:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                "Partition 1 must contain saved binding visits; got "
                f"type {type(binding_visit).__name__}."
            )
        confirmed_visit_keys.append(binding_visit.visit_key)
    for binding_visit in partition_2:
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


def _validate_buyer_payment_correspondence(
    *,
    node_name: str,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    trade_scope_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
) -> None:
    """
    Match buyer economic records to payment records.

    The payment amount formula is not evaluated again. Only identity of the
    visit, its saved order, and the BUYER role are checked.
    """
    buyer_economic_records = selected_candidate.buyer_economic_records
    buyer_payment_records = payment_node.buyer_payment_records
    if not isinstance(buyer_economic_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: buyer_economic_records must be a tuple."
        )
    if len(buyer_economic_records) < 1:
        raise RuntimeError(
            f"Node {node_name!r}: a selected candidate requires one or more "
            "buyer economic records."
        )
    if len(buyer_payment_records) < 1:
        raise RuntimeError(
            f"Node {node_name!r}: a selected candidate requires one or more "
            "buyer payment records."
        )
    if len(buyer_economic_records) != len(buyer_payment_records):
        raise RuntimeError(
            f"Node {node_name!r}: buyer economic record count "
            f"{len(buyer_economic_records)} does not match buyer payment "
            f"record count {len(buyer_payment_records)}."
        )

    payment_visit_keys: list[OrderControlTvtVisitKey] = []
    record_index = 0
    for buyer_economic_record in buyer_economic_records:
        buyer_payment_record = buyer_payment_records[record_index]
        if not isinstance(buyer_economic_record, OrderControlTvtMpBuyerEconomicRecord):
            raise RuntimeError(
                f"Node {node_name!r}: buyer economic record at index "
                f"{record_index} has type {type(buyer_economic_record).__name__}."
            )
        if not isinstance(buyer_payment_record, OrderControlTvtMpBuyerPaymentRecord):
            raise RuntimeError(
                f"Node {node_name!r}: buyer payment record at index "
                f"{record_index} has type {type(buyer_payment_record).__name__}."
            )
        economic_visit_key = buyer_economic_record.visit_key
        payment_visit_key = buyer_payment_record.visit_key
        if economic_visit_key != payment_visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: buyer record index {record_index} has "
                f"economic VisitKey {economic_visit_key!r} and payment "
                f"VisitKey {payment_visit_key!r}. Saved order is not repaired."
            )
        if buyer_economic_record.vehicle_name != buyer_payment_record.vehicle_name:
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {economic_visit_key!r} has "
                "economic vehicle_name "
                f"{buyer_economic_record.vehicle_name!r} and payment "
                f"vehicle_name {buyer_payment_record.vehicle_name!r}."
            )
        if economic_visit_key in payment_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {economic_visit_key!r} is "
                "duplicated. Duplicates are not dropped."
            )
        payment_visit_keys.append(economic_visit_key)
        record_index = record_index + 1

    partition_buyer_visit_keys: list[OrderControlTvtVisitKey] = []
    for binding_visit in trade_scope_visits:
        if binding_visit.trade_role is not OrderControlTvtMpLocalBindingTradeRole.BUYER:
            continue
        if binding_visit.visit_key in partition_buyer_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 3 repeats BUYER VisitKey "
                f"{binding_visit.visit_key!r}."
            )
        partition_buyer_visit_keys.append(binding_visit.visit_key)

    for visit_key in payment_visit_keys:
        role = _trade_role_for_visit_key(
            node_name=node_name,
            trade_scope_visits=trade_scope_visits,
            visit_key=visit_key,
        )
        if role is not OrderControlTvtMpLocalBindingTradeRole.BUYER:
            raise RuntimeError(
                f"Node {node_name!r}: buyer payment VisitKey {visit_key!r} has "
                f"trade role {role!r}, not BUYER. A payment record is not "
                "attached outside the buyer role."
            )
    for visit_key in partition_buyer_visit_keys:
        if visit_key not in payment_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 3 BUYER VisitKey {visit_key!r} "
                "has no buyer payment record."
            )
    for visit_key in payment_visit_keys:
        if visit_key not in partition_buyer_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: buyer payment VisitKey {visit_key!r} is "
                "not in the partition 3 BUYER set."
            )


def _validate_seller_compensation_correspondence(
    *,
    node_name: str,
    selected_candidate: OrderControlTvtMpCandidateEconomicEvaluationResult,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    trade_scope_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
) -> None:
    """
    Match seller economic records to compensation records.

    Zero compensation stays a record. The reservation formula is not run
    again; the saved required_compensation_R_s must already equal
    compensation_amount.
    """
    seller_economic_records = selected_candidate.seller_economic_records
    seller_compensation_records = payment_node.seller_compensation_records
    if not isinstance(seller_economic_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: seller_economic_records must be a tuple."
        )
    if len(seller_economic_records) != len(seller_compensation_records):
        raise RuntimeError(
            f"Node {node_name!r}: seller economic record count "
            f"{len(seller_economic_records)} does not match seller "
            "compensation record count "
            f"{len(seller_compensation_records)}. A zero compensation does "
            "not remove the seller record."
        )

    compensation_visit_keys: list[OrderControlTvtVisitKey] = []
    record_index = 0
    for seller_economic_record in seller_economic_records:
        seller_compensation_record = seller_compensation_records[record_index]
        if not isinstance(seller_economic_record, OrderControlTvtMpSellerEconomicRecord):
            raise RuntimeError(
                f"Node {node_name!r}: seller economic record at index "
                f"{record_index} has type {type(seller_economic_record).__name__}."
            )
        if not isinstance(
            seller_compensation_record,
            OrderControlTvtMpSellerCompensationRecord,
        ):
            raise RuntimeError(
                f"Node {node_name!r}: seller compensation record at index "
                f"{record_index} has type "
                f"{type(seller_compensation_record).__name__}."
            )
        economic_visit_key = seller_economic_record.visit_key
        compensation_visit_key = seller_compensation_record.visit_key
        if economic_visit_key != compensation_visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: seller record index {record_index} has "
                f"economic VisitKey {economic_visit_key!r} and compensation "
                f"VisitKey {compensation_visit_key!r}."
            )
        if (
            seller_economic_record.vehicle_name
            != seller_compensation_record.vehicle_name
        ):
            raise RuntimeError(
                f"Node {node_name!r}: seller VisitKey {economic_visit_key!r} "
                "has economic vehicle_name "
                f"{seller_economic_record.vehicle_name!r} and compensation "
                "vehicle_name "
                f"{seller_compensation_record.vehicle_name!r}."
            )
        if (
            seller_compensation_record.compensation_amount
            != seller_economic_record.required_compensation_R_s
        ):
            raise RuntimeError(
                f"Node {node_name!r}: compensation_amount "
                f"{seller_compensation_record.compensation_amount!r} does not "
                "equal saved required_compensation_R_s "
                f"{seller_economic_record.required_compensation_R_s!r} for "
                f"VisitKey {economic_visit_key!r}. The compensation formula "
                "is not recomputed."
            )
        if economic_visit_key in compensation_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: seller VisitKey {economic_visit_key!r} "
                "is duplicated. Duplicates are not dropped."
            )
        for buyer_payment_record in payment_node.buyer_payment_records:
            if buyer_payment_record.visit_key == economic_visit_key:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {economic_visit_key!r} is "
                    "both a buyer and a seller. One trade-scope visit has "
                    "one role, and the duplicate is not dropped."
                )
        compensation_visit_keys.append(economic_visit_key)
        record_index = record_index + 1

    partition_seller_visit_keys: list[OrderControlTvtVisitKey] = []
    for binding_visit in trade_scope_visits:
        if binding_visit.trade_role is not OrderControlTvtMpLocalBindingTradeRole.SELLER:
            continue
        if binding_visit.visit_key in partition_seller_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 3 repeats SELLER VisitKey "
                f"{binding_visit.visit_key!r}."
            )
        partition_seller_visit_keys.append(binding_visit.visit_key)

    for visit_key in compensation_visit_keys:
        role = _trade_role_for_visit_key(
            node_name=node_name,
            trade_scope_visits=trade_scope_visits,
            visit_key=visit_key,
        )
        if role is not OrderControlTvtMpLocalBindingTradeRole.SELLER:
            raise RuntimeError(
                f"Node {node_name!r}: seller compensation VisitKey "
                f"{visit_key!r} has trade role {role!r}, not SELLER."
            )
    for visit_key in partition_seller_visit_keys:
        if visit_key not in compensation_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 3 SELLER VisitKey "
                f"{visit_key!r} has no seller compensation record. Zero "
                "compensation does not delete the record."
            )
    for visit_key in compensation_visit_keys:
        if visit_key not in partition_seller_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: seller compensation VisitKey "
                f"{visit_key!r} is not in the partition 3 SELLER set."
            )


def _require_buyer_and_seller_keys_are_disjoint(
    *,
    node_name: str,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
) -> None:
    for buyer_payment_record in payment_node.buyer_payment_records:
        for seller_compensation_record in payment_node.seller_compensation_records:
            if buyer_payment_record.visit_key == seller_compensation_record.visit_key:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey "
                    f"{buyer_payment_record.visit_key!r} is both a buyer and "
                    "a seller. One trade-scope visit has one role, and the "
                    "duplicate is not dropped."
                )


def _trade_role_for_visit_key(
    *,
    node_name: str,
    trade_scope_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    visit_key: OrderControlTvtVisitKey,
) -> OrderControlTvtMpLocalBindingTradeRole:
    found_role = None
    for binding_visit in trade_scope_visits:
        if binding_visit.visit_key != visit_key:
            continue
        if found_role is not None:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} appears more "
                "than once in partition 3."
            )
        found_role = binding_visit.trade_role
    if found_role is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is not in partition "
            "3, so it cannot carry a buyer payment or seller compensation."
        )
    return found_role


def _require_no_money_on_nonparticipants_or_partition_4(
    *,
    node_name: str,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    trade_scope_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    outside_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
) -> None:
    money_visit_keys: list[OrderControlTvtVisitKey] = []
    for buyer_payment_record in payment_node.buyer_payment_records:
        money_visit_keys.append(buyer_payment_record.visit_key)
    for seller_compensation_record in payment_node.seller_compensation_records:
        money_visit_keys.append(seller_compensation_record.visit_key)

    for binding_visit in trade_scope_visits:
        if (
            binding_visit.trade_role
            is not OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING
        ):
            continue
        if binding_visit.visit_key in money_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: nonparticipating VisitKey "
                f"{binding_visit.visit_key!r} has a monetary record. "
                "Partition 3 nonparticipants stay in the final rank and do "
                "not pay or receive compensation."
            )
    for binding_visit in outside_visits:
        if (
            binding_visit.trade_role
            is not OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE
        ):
            raise RuntimeError(
                f"Node {node_name!r}: partition 4 VisitKey "
                f"{binding_visit.visit_key!r} has trade role "
                f"{binding_visit.trade_role!r}, not OUTSIDE_TRADE_SCOPE."
            )
        if binding_visit.visit_key in money_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 4 VisitKey "
                f"{binding_visit.visit_key!r} has a monetary record. Visits "
                "outside the trade scope are ranked from baseline and are "
                "not buyers or sellers of this candidate."
            )


def _require_final_rank_matches_partitions_3_and_4(
    *,
    node_name: str,
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...],
    trade_scope_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    outside_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    already_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    expected_binding_visits: list[OrderControlTvtMpLocalBindingRankVisit] = []
    for binding_visit in trade_scope_visits:
        expected_binding_visits.append(binding_visit)
    for binding_visit in outside_visits:
        expected_binding_visits.append(binding_visit)
    if len(final_rank_visits) != len(expected_binding_visits):
        raise RuntimeError(
            f"Node {node_name!r}: final rank length {len(final_rank_visits)} "
            "does not equal partition 3 plus partition 4 length "
            f"{len(expected_binding_visits)}. The column is not rebuilt."
        )

    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    record_index = 0
    for binding_visit in trade_scope_visits:
        final_rank_visit = final_rank_visits[record_index]
        _require_final_rank_visit_matches_binding(
            node_name=node_name,
            final_rank_visit=final_rank_visit,
            binding_visit=binding_visit,
            expected_local_rank=record_index + 1,
            expected_source=OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE,
            already_confirmed_visit_keys=already_confirmed_visit_keys,
            seen_visit_keys=seen_visit_keys,
        )
        record_index = record_index + 1
    for binding_visit in outside_visits:
        final_rank_visit = final_rank_visits[record_index]
        _require_final_rank_visit_matches_binding(
            node_name=node_name,
            final_rank_visit=final_rank_visit,
            binding_visit=binding_visit,
            expected_local_rank=record_index + 1,
            expected_source=OrderControlTvtMpFinalizationSource.BASELINE,
            already_confirmed_visit_keys=already_confirmed_visit_keys,
            seen_visit_keys=seen_visit_keys,
        )
        record_index = record_index + 1


def _require_final_rank_visit_matches_binding(
    *,
    node_name: str,
    final_rank_visit: OrderControlTvtMpFinalRankVisitRecord,
    binding_visit: OrderControlTvtMpLocalBindingRankVisit,
    expected_local_rank: int,
    expected_source: OrderControlTvtMpFinalizationSource,
    already_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    seen_visit_keys: list[OrderControlTvtVisitKey],
) -> None:
    visit_key = final_rank_visit.visit_key
    if visit_key != binding_visit.visit_key:
        raise RuntimeError(
            f"Node {node_name!r}: final rank position {expected_local_rank} "
            f"has VisitKey {visit_key!r}, but the saved binding visit has "
            f"{binding_visit.visit_key!r}. Partition 1 and 2 are not inserted "
            "and the column is not rebuilt."
        )
    if visit_key in already_confirmed_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: final rank repeats already confirmed "
            f"VisitKey {visit_key!r}. Confirmed ranks and formal routes are "
            "not overwritten."
        )
    if visit_key in seen_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: final rank repeats VisitKey {visit_key!r}."
        )
    seen_visit_keys.append(visit_key)
    if final_rank_visit.final_local_rank != expected_local_rank:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} has final_local_rank "
            f"{final_rank_visit.final_local_rank!r}, expected "
            f"{expected_local_rank}. Ranks in this column start at 1 and "
            "follow tuple order."
        )
    if final_rank_visit.finalization_source is not expected_source:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} has finalization "
            f"source {final_rank_visit.finalization_source!r}, expected "
            f"{expected_source!r}."
        )
    saved_route = _require_non_empty_route(
        binding_visit.route_next_link_name,
        node_name=node_name,
        visit_key=visit_key,
        source_label="binding visit",
    )
    final_route = _require_non_empty_route(
        final_rank_visit.formal_route_next_link_name,
        node_name=node_name,
        visit_key=visit_key,
        source_label="final rank visit",
    )
    if final_route != saved_route:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} formal route "
            f"{final_route!r} does not match saved binding route "
            f"{saved_route!r}. The route is not guessed."
        )


def _require_non_empty_route(
    route_next_link_name: object,
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    source_label: str,
) -> str:
    if route_next_link_name is None:
        raise RuntimeError(
            f"Node {node_name!r}: {source_label} route for VisitKey "
            f"{visit_key!r} is None. The route is not guessed."
        )
    if not isinstance(route_next_link_name, str):
        raise RuntimeError(
            f"Node {node_name!r}: {source_label} route for VisitKey "
            f"{visit_key!r} must be str; got "
            f"type {type(route_next_link_name).__name__}."
        )
    if route_next_link_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: {source_label} route for VisitKey "
            f"{visit_key!r} is empty. The route is not guessed."
        )
    return route_next_link_name


def _validate_fallback_node(
    *,
    node_name: str,
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...],
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selection_node: OrderControlTvtNodeMpCandidateSelectionResult,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    build_status: OrderControlTvtCandidateVisitSetStatus,
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    arrived_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    collector: object,
) -> None:
    _require_no_selected_labels(
        node_name=node_name,
        payment_node=payment_node,
        selection_node=selection_node,
        final_rank_node=final_rank_node,
        cause="BASELINE_FALLBACK_RANKS",
    )
    _require_empty_money_records(
        node_name=node_name,
        payment_node=payment_node,
        cause="BASELINE_FALLBACK_RANKS",
    )
    if len(remaining_decision_window_visit_keys) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: baseline fallback requires a non-empty "
            "remaining decision window. An empty remaining window is "
            "NO_VISITS_TO_CONFIRM, not fallback."
        )
    if (
        build_status
        is OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    ):
        # Branch 2: review finished and no candidate was adopted.
        pass
    elif build_status in _INFORMATION_SHORTAGE_STATUSES:
        # Branch 3: shortage stays shortage. It is not economic failure.
        pass
    else:
        raise RuntimeError(
            f"Node {node_name!r}: BASELINE_FALLBACK_RANKS has build_status "
            f"{build_status!r}. Branch 2 requires "
            "BASELINE_INFORMATION_COMPLETE. Branch 3 requires an information "
            "shortage status. An empty-window status is not fallback."
        )
    if len(final_rank_visits) != len(remaining_decision_window_visit_keys):
        raise RuntimeError(
            f"Node {node_name!r}: fallback final rank length "
            f"{len(final_rank_visits)} does not equal remaining decision "
            f"window length {len(remaining_decision_window_visit_keys)}. "
            "The whole remaining window is confirmed, and the column is not "
            "cut or rebuilt."
        )

    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    record_index = 0
    for visit_key in remaining_decision_window_visit_keys:
        final_rank_visit = final_rank_visits[record_index]
        expected_local_rank = record_index + 1
        if final_rank_visit.visit_key != visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: fallback position {expected_local_rank} "
                f"has VisitKey {final_rank_visit.visit_key!r}, expected "
                f"{visit_key!r}."
            )
        if visit_key in confirmed_leading_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: fallback repeats preconfirmed VisitKey "
                f"{visit_key!r}. Already confirmed ranks are not overwritten."
            )
        if visit_key in arrived_confirmed_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: fallback repeats arrived confirmed "
                f"VisitKey {visit_key!r}. Already confirmed formal routes are "
                "not overwritten."
            )
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: fallback repeats VisitKey {visit_key!r}."
            )
        seen_visit_keys.append(visit_key)
        if final_rank_visit.final_local_rank != expected_local_rank:
            raise RuntimeError(
                f"Node {node_name!r}: fallback VisitKey {visit_key!r} has "
                f"final_local_rank {final_rank_visit.final_local_rank!r}, "
                f"expected {expected_local_rank}."
            )
        if (
            final_rank_visit.finalization_source
            is not OrderControlTvtMpFinalizationSource.BASELINE
        ):
            raise RuntimeError(
                f"Node {node_name!r}: fallback VisitKey {visit_key!r} has "
                f"source {final_rank_visit.finalization_source!r}, expected "
                "BASELINE."
            )
        saved_route = _formal_route_from_collector(
            collector=collector,
            node_name=node_name,
            visit_key=visit_key,
        )
        final_route = _require_non_empty_route(
            final_rank_visit.formal_route_next_link_name,
            node_name=node_name,
            visit_key=visit_key,
            source_label="final rank visit",
        )
        if final_route != saved_route:
            raise RuntimeError(
                f"Node {node_name!r}: fallback VisitKey {visit_key!r} formal "
                f"route {final_route!r} does not match the collector snapshot "
                f"route {saved_route!r}. The route is not guessed."
            )
        record_index = record_index + 1


def _formal_route_from_collector(
    *,
    collector: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> str:
    """Read the saved snapshot route. Do not search live traffic objects."""
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
        source_label="collector snapshot",
    )


def _validate_no_visits_node(
    *,
    node_name: str,
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...],
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selection_node: OrderControlTvtNodeMpCandidateSelectionResult,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    build_status: OrderControlTvtCandidateVisitSetStatus,
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    _require_no_selected_labels(
        node_name=node_name,
        payment_node=payment_node,
        selection_node=selection_node,
        final_rank_node=final_rank_node,
        cause="NO_VISITS_TO_CONFIRM",
    )
    _require_empty_money_records(
        node_name=node_name,
        payment_node=payment_node,
        cause="NO_VISITS_TO_CONFIRM",
    )
    if len(final_rank_visits) != 0:
        raise RuntimeError(
            f"Node {node_name!r}: NO_VISITS_TO_CONFIRM requires an empty "
            "final rank column. Preconfirmed visits are not repeated."
        )
    if len(remaining_decision_window_visit_keys) != 0:
        raise RuntimeError(
            f"Node {node_name!r}: NO_VISITS_TO_CONFIRM requires an empty "
            "remaining decision window. A non-empty remaining window is "
            "baseline fallback, not an empty confirmation."
        )
    if (
        build_status
        is not OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
    ):
        raise RuntimeError(
            f"Node {node_name!r}: NO_VISITS_TO_CONFIRM requires build_status "
            "NOT_BUILT_NO_RIGHT_OF_ENTRY; got "
            f"{build_status!r}. Information shortage and a completed review "
            "are not recorded as no visits to confirm."
        )
    if len(decision_window_visit_keys) == 0:
        # Branch 4: the decision window was empty from the start.
        return
    # Branch 5: visits existed and were already confirmed. Do not repeat them.
    return
