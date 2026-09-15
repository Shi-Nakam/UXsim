"""
TVT-MP FIFO inspection connection for general trade-rank results.

Reads an existing general trade-rank set result, takes each candidate's
``trade_scope`` (before trade) and ``trade_order[:last_buyer_rank]``
(after trade), and asks the existing ``preserves_inlink_fifo()`` whether
relative order toward the target Node is preserved on each approach
inlink. Buyers, sellers, and non-participating visits in the scope are
all inspected. A False result is a normal candidate rejection, not an
error.

This is a read-only stage after rank reconstruction and before local
virtual calculation. It does not rebuild ranks, run economic evaluation,
or modify upstream results.
"""

from __future__ import annotations

from dataclasses import dataclass

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtMpGeneralTradeRankSetResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.order_control_tvt_trade_rank import preserves_inlink_fifo


@dataclass(frozen=True)
class OrderControlTvtMpCandidateFifoInspectionResult:
    """
    FIFO inspection ticket for one general trade-rank candidate.

    ``general_trade_rank_result`` is the upstream rank result for this
    candidate, kept by identity. ``preserves_inlink_fifo`` is the bool
    returned by the existing inspection function of the same name; it is
    not that function. True means every approach inlink toward the
    target Node kept its relative visit order. False is a normal FIFO
    violation for this candidate only.
    """

    general_trade_rank_result: OrderControlTvtMpGeneralTradeRankResult
    preserves_inlink_fifo: bool


@dataclass(frozen=True)
class OrderControlTvtNodeMpFifoInspectionResult:
    """Per-target-Node FIFO inspection results in upstream candidate order."""

    node_name: str
    build_status: OrderControlTvtCandidateVisitSetStatus
    candidate_fifo_inspection_results: tuple[
        OrderControlTvtMpCandidateFifoInspectionResult,
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtMpFifoInspectionSetResult:
    """Overall FIFO inspection connection result."""

    general_trade_rank_set_result: OrderControlTvtMpGeneralTradeRankSetResult
    node_fifo_inspection_results: tuple[
        OrderControlTvtNodeMpFifoInspectionResult,
        ...,
    ]


def _build_status_is_normal_not_generated_status(
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> bool:
    return build_status in (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
    )


def _build_status_requires_fifo_inspection(
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> bool:
    return (
        build_status
        == OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )


def _empty_node_result(
    *,
    node_name: str,
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> OrderControlTvtNodeMpFifoInspectionResult:
    return OrderControlTvtNodeMpFifoInspectionResult(
        node_name=node_name,
        build_status=build_status,
        candidate_fifo_inspection_results=(),
    )


def _verify_node_result_counts(
    *,
    node_candidate_set_results: tuple[
        OrderControlTvtNodeCandidateVisitSetResult,
        ...,
    ],
    node_concrete_buyer_candidate_set_results: tuple[
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
        ...,
    ],
    node_trade_rank_results: tuple[
        OrderControlTvtNodeMpGeneralTradeRankResult,
        ...,
    ],
) -> None:
    candidate_count = len(node_candidate_set_results)
    concrete_count = len(node_concrete_buyer_candidate_set_results)
    rank_count = len(node_trade_rank_results)
    if candidate_count != concrete_count or candidate_count != rank_count:
        raise RuntimeError(
            "Target-Node result counts do not match: expected "
            f"node_candidate_set_results={candidate_count}, actual "
            "node_concrete_buyer_candidate_set_results="
            f"{concrete_count}, actual node_trade_rank_results="
            f"{rank_count}."
        )


def _verify_node_alignment_at_index(
    *,
    node_index: int,
    node_candidate_result: OrderControlTvtNodeCandidateVisitSetResult,
    node_concrete_result: OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
    node_rank_result: OrderControlTvtNodeMpGeneralTradeRankResult,
) -> None:
    candidate_node_name = node_candidate_result.node_name
    concrete_node_name = node_concrete_result.node_name
    rank_node_name = node_rank_result.node_name
    if candidate_node_name != concrete_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: expected "
            f"candidate result {candidate_node_name!r}, actual concrete "
            f"buyer candidate set result {concrete_node_name!r}."
        )
    if candidate_node_name != rank_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: expected "
            f"candidate result {candidate_node_name!r}, actual general "
            f"trade-rank result {rank_node_name!r}."
        )

    candidate_build_status = node_candidate_result.build_status
    concrete_build_status = node_concrete_result.build_status
    rank_build_status = node_rank_result.build_status
    if candidate_build_status != concrete_build_status:
        raise RuntimeError(
            f"Build status mismatch at index {node_index} for Node "
            f"{candidate_node_name!r}: expected candidate result "
            f"{candidate_build_status!r}, actual concrete buyer "
            f"candidate set result {concrete_build_status!r}."
        )
    if candidate_build_status != rank_build_status:
        raise RuntimeError(
            f"Build status mismatch at index {node_index} for Node "
            f"{candidate_node_name!r}: expected candidate result "
            f"{candidate_build_status!r}, actual general trade-rank "
            f"result {rank_build_status!r}."
        )


def _verify_candidate_counts(
    *,
    node_name: str,
    candidate_trade_rank_results: tuple[
        OrderControlTvtMpGeneralTradeRankResult,
        ...,
    ],
    concrete_buyer_candidate_sets: tuple[
        OrderControlTvtMpConcreteBuyerCandidateSet,
        ...,
    ],
) -> None:
    rank_count = len(candidate_trade_rank_results)
    concrete_count = len(concrete_buyer_candidate_sets)
    if rank_count != concrete_count:
        raise RuntimeError(
            f"Node {node_name!r}: candidate trade-rank result count "
            f"does not match concrete buyer candidate set count: "
            f"expected {concrete_count}, actual {rank_count}."
        )


def _verify_candidate_identity_at_index(
    *,
    node_name: str,
    candidate_index: int,
    general_trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
    expected_concrete_buyer_candidate_set: (
        OrderControlTvtMpConcreteBuyerCandidateSet
    ),
) -> None:
    actual_concrete = general_trade_rank_result.concrete_buyer_candidate_set
    if actual_concrete is not expected_concrete_buyer_candidate_set:
        raise RuntimeError(
            f"Node {node_name!r}: concrete buyer candidate set identity "
            f"mismatch at candidate index {candidate_index}: expected "
            f"object {id(expected_concrete_buyer_candidate_set)}, "
            f"actual object {id(actual_concrete)}."
        )


def _build_inlink_name_by_visit_key(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
) -> dict[OrderControlTvtVisitKey, str]:
    """
    Map each limited candidate VisitKey to its approach-inlink name.

    ``candidate_visits`` already stores the inlink of each visit toward
    the target Node. This temporary dict is not stored on the result.
    """
    inlink_name_by_visit_key: dict[OrderControlTvtVisitKey, str] = {}
    for candidate_visit in candidate_visits:
        inlink_name_by_visit_key[candidate_visit.visit_key] = (
            candidate_visit.inlink_name
        )
    return inlink_name_by_visit_key


def _get_before_trade(
    general_trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
) -> tuple[OrderControlTvtVisitKey, ...]:
    return general_trade_rank_result.trade_scope


def _get_after_trade(
    general_trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
) -> tuple[OrderControlTvtVisitKey, ...]:
    last_buyer_rank = general_trade_rank_result.last_buyer_rank
    trade_order = general_trade_rank_result.trade_order
    if type(last_buyer_rank) is not int:
        after_trade = ()
        return after_trade
    if last_buyer_rank < 0:
        after_trade = ()
        return after_trade
    after_trade = trade_order[:last_buyer_rank]
    return after_trade


def _verify_fifo_materials(
    *,
    node_name: str,
    candidate_index: int,
    before_trade: tuple[OrderControlTvtVisitKey, ...],
    after_trade: tuple[OrderControlTvtVisitKey, ...],
    last_buyer_rank: object,
    trade_order: tuple[OrderControlTvtVisitKey, ...],
    inlink_name_by_visit_key: dict[OrderControlTvtVisitKey, str],
) -> None:
    if len(before_trade) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "before_trade (trade_scope) must not be empty."
        )
    if type(last_buyer_rank) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "last_buyer_rank must be a Python int (not bool); got type "
            f"{type(last_buyer_rank).__name__} with value "
            f"{last_buyer_rank!r}."
        )
    if last_buyer_rank < 1:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            f"last_buyer_rank must be >= 1; got {last_buyer_rank!r}."
        )
    if last_buyer_rank > len(trade_order):
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "last_buyer_rank exceeds trade_order length: expected at "
            f"most {len(trade_order)}, actual {last_buyer_rank}."
        )
    if len(before_trade) != last_buyer_rank:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "before_trade length does not match last_buyer_rank: "
            f"expected {last_buyer_rank}, actual {len(before_trade)}."
        )
    if len(after_trade) != last_buyer_rank:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "after_trade length does not match last_buyer_rank: "
            f"expected {last_buyer_rank}, actual {len(after_trade)}."
        )
    before_set = set(before_trade)
    after_set = set(after_trade)
    if before_set != after_set:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "before_trade and after_trade VisitKey sets do not match."
        )

    for visit_key in before_trade:
        if visit_key not in inlink_name_by_visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: candidate index {candidate_index}: "
                "missing inlink name for FIFO VisitKey "
                f"{visit_key!r}."
            )
    for visit_key in after_trade:
        if visit_key not in inlink_name_by_visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: candidate index {candidate_index}: "
                "missing inlink name for FIFO VisitKey "
                f"{visit_key!r}."
            )


def _call_preserves_inlink_fifo(
    *,
    node_name: str,
    candidate_index: int,
    before_trade: tuple[OrderControlTvtVisitKey, ...],
    after_trade: tuple[OrderControlTvtVisitKey, ...],
    inlink_name_by_visit_key: dict[OrderControlTvtVisitKey, str],
) -> bool:
    try:
        preserves_fifo = preserves_inlink_fifo(
            before_trade,
            after_trade,
            inlink_name_by_visit_key,
        )
    except ValueError as error:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "FIFO inspection materials have a serious inconsistency; "
            "preserves_inlink_fifo() raised ValueError: "
            f"{error}"
        ) from error
    return preserves_fifo


def _require_python_bool_fifo_result(
    *,
    node_name: str,
    candidate_index: int,
    preserves_fifo: object,
) -> bool:
    if type(preserves_fifo) is not bool:
        raise RuntimeError(
            f"Node {node_name!r}: candidate index {candidate_index}: "
            "preserves_inlink_fifo() must return a Python bool; got "
            f"{type(preserves_fifo)!r} with value {preserves_fifo!r}."
        )
    return preserves_fifo


def _inspect_one_candidate(
    *,
    node_name: str,
    candidate_index: int,
    general_trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
    expected_concrete_buyer_candidate_set: (
        OrderControlTvtMpConcreteBuyerCandidateSet
    ),
    inlink_name_by_visit_key: dict[OrderControlTvtVisitKey, str],
) -> OrderControlTvtMpCandidateFifoInspectionResult:
    _verify_candidate_identity_at_index(
        node_name=node_name,
        candidate_index=candidate_index,
        general_trade_rank_result=general_trade_rank_result,
        expected_concrete_buyer_candidate_set=(
            expected_concrete_buyer_candidate_set
        ),
    )

    before_trade = _get_before_trade(general_trade_rank_result)
    after_trade = _get_after_trade(general_trade_rank_result)
    last_buyer_rank = general_trade_rank_result.last_buyer_rank
    trade_order = general_trade_rank_result.trade_order
    _verify_fifo_materials(
        node_name=node_name,
        candidate_index=candidate_index,
        before_trade=before_trade,
        after_trade=after_trade,
        last_buyer_rank=last_buyer_rank,
        trade_order=trade_order,
        inlink_name_by_visit_key=inlink_name_by_visit_key,
    )

    preserves_fifo = _call_preserves_inlink_fifo(
        node_name=node_name,
        candidate_index=candidate_index,
        before_trade=before_trade,
        after_trade=after_trade,
        inlink_name_by_visit_key=inlink_name_by_visit_key,
    )
    preserves_fifo = _require_python_bool_fifo_result(
        node_name=node_name,
        candidate_index=candidate_index,
        preserves_fifo=preserves_fifo,
    )

    return OrderControlTvtMpCandidateFifoInspectionResult(
        general_trade_rank_result=general_trade_rank_result,
        preserves_inlink_fifo=preserves_fifo,
    )


def _build_node_fifo_inspection_result(
    *,
    node_candidate_result: OrderControlTvtNodeCandidateVisitSetResult,
    node_concrete_result: OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
    node_rank_result: OrderControlTvtNodeMpGeneralTradeRankResult,
) -> OrderControlTvtNodeMpFifoInspectionResult:
    node_name = node_candidate_result.node_name
    candidate_trade_rank_results = node_rank_result.candidate_trade_rank_results
    if len(candidate_trade_rank_results) == 0:
        return _empty_node_result(
            node_name=node_name,
            build_status=node_candidate_result.build_status,
        )

    concrete_buyer_candidate_sets = (
        node_concrete_result.concrete_buyer_candidate_sets
    )
    _verify_candidate_counts(
        node_name=node_name,
        candidate_trade_rank_results=candidate_trade_rank_results,
        concrete_buyer_candidate_sets=concrete_buyer_candidate_sets,
    )

    inlink_name_by_visit_key = _build_inlink_name_by_visit_key(
        node_candidate_result.candidate_visits,
    )

    candidate_fifo_inspection_results_list: list[
        OrderControlTvtMpCandidateFifoInspectionResult
    ] = []
    for candidate_index, general_trade_rank_result in enumerate(
        candidate_trade_rank_results
    ):
        expected_concrete = concrete_buyer_candidate_sets[candidate_index]
        one_result = _inspect_one_candidate(
            node_name=node_name,
            candidate_index=candidate_index,
            general_trade_rank_result=general_trade_rank_result,
            expected_concrete_buyer_candidate_set=expected_concrete,
            inlink_name_by_visit_key=inlink_name_by_visit_key,
        )
        candidate_fifo_inspection_results_list.append(one_result)

    return OrderControlTvtNodeMpFifoInspectionResult(
        node_name=node_name,
        build_status=node_candidate_result.build_status,
        candidate_fifo_inspection_results=tuple(
            candidate_fifo_inspection_results_list
        ),
    )


def build_tvt_mp_fifo_inspection_results(
    general_trade_rank_set_result: OrderControlTvtMpGeneralTradeRankSetResult,
) -> OrderControlTvtMpFifoInspectionSetResult:
    """
    Inspect each general trade-rank candidate for inlink FIFO.

    Walks upstream Node results in stored order. Only
    ``BASELINE_INFORMATION_COMPLETE`` Nodes with at least one rank
    candidate call ``preserves_inlink_fifo()``. False results stay in
    the output in the same candidate order. Does not modify the input
    or re-run rank reconstruction.
    """
    concrete_buyer_candidate_set_result = (
        general_trade_rank_set_result.concrete_buyer_candidate_set_result
    )
    node_trade_rank_results = (
        general_trade_rank_set_result.node_trade_rank_results
    )
    inlink_candidate_physical_order_result = (
        concrete_buyer_candidate_set_result.inlink_candidate_physical_order_result
    )
    candidate_visit_set_result = (
        inlink_candidate_physical_order_result.candidate_visit_set_result
    )
    node_candidate_set_results = (
        candidate_visit_set_result.node_candidate_set_results
    )
    node_concrete_buyer_candidate_set_results = (
        concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )

    _verify_node_result_counts(
        node_candidate_set_results=node_candidate_set_results,
        node_concrete_buyer_candidate_set_results=(
            node_concrete_buyer_candidate_set_results
        ),
        node_trade_rank_results=node_trade_rank_results,
    )

    node_fifo_inspection_results: list[
        OrderControlTvtNodeMpFifoInspectionResult
    ] = []
    for node_index, node_candidate_result in enumerate(
        node_candidate_set_results
    ):
        node_concrete_result = node_concrete_buyer_candidate_set_results[
            node_index
        ]
        node_rank_result = node_trade_rank_results[node_index]
        _verify_node_alignment_at_index(
            node_index=node_index,
            node_candidate_result=node_candidate_result,
            node_concrete_result=node_concrete_result,
            node_rank_result=node_rank_result,
        )

        build_status = node_candidate_result.build_status
        if _build_status_is_normal_not_generated_status(build_status):
            node_fifo_inspection_results.append(
                _empty_node_result(
                    node_name=node_candidate_result.node_name,
                    build_status=build_status,
                )
            )
            continue

        if _build_status_requires_fifo_inspection(build_status):
            node_result = _build_node_fifo_inspection_result(
                node_candidate_result=node_candidate_result,
                node_concrete_result=node_concrete_result,
                node_rank_result=node_rank_result,
            )
            node_fifo_inspection_results.append(node_result)
            continue

        raise RuntimeError(
            f"Node {node_candidate_result.node_name!r}: unexpected "
            f"candidate visit set build status {build_status!r}."
        )

    return OrderControlTvtMpFifoInspectionSetResult(
        general_trade_rank_set_result=general_trade_rank_set_result,
        node_fifo_inspection_results=tuple(node_fifo_inspection_results),
    )
