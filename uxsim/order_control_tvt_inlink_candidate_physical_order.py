"""
Organize limited TVT candidate visits by inlink snapshot physical order.

Reads an existing candidate visit set result and fork snapshot inlink physical
orders, then groups each Node's limited candidate visits by inlink while
preserving snapshot-time queue order on each approach link. Does not modify
upstream results, re-run baseline fork, or build buyer or seller sets.
"""

from __future__ import annotations

from dataclasses import dataclass

from uxsim.order_control_baseline_snapshot import (
    OrderControlBaselineSnapshotInlinkPhysicalOrder,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


@dataclass(frozen=True)
class OrderControlTvtInlinkCandidateVisitPhysicalOrder:
    """
    Limited candidate visits on one inlink in snapshot physical order.

    ``candidate_visit_keys_head_to_tail`` lists only visits that appear in the
    upstream limited ``candidate_visits`` for this Node and inlink. Index 0 is
    the candidate visit closest to the target Node on that inlink at snapshot
    time. This is not the cross-inlink official baseline order used for
    variable-N selection, and it does not encode consecutive baseline rank
    numbers. It is not a buyer prefix, buyer list, or seller list.
    """

    node_name: str
    inlink_name: str
    candidate_visit_keys_head_to_tail: tuple[OrderControlTvtVisitKey, ...]


@dataclass(frozen=True)
class OrderControlTvtNodeInlinkCandidatePhysicalOrderResult:
    """Per-Node inlink-grouped limited candidate visits in snapshot physical order."""

    node_name: str
    build_status: OrderControlTvtCandidateVisitSetStatus
    inlink_candidate_physical_orders: tuple[
        OrderControlTvtInlinkCandidateVisitPhysicalOrder, ...
    ]


@dataclass(frozen=True)
class OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    """Overall result of inlink-grouped limited candidate visit physical ordering."""

    candidate_visit_set_result: OrderControlTvtCandidateVisitSetResult
    node_inlink_candidate_physical_order_results: tuple[
        OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
        ...
    ]


def _verify_node_name_at_index(
    *,
    node_index: int,
    expected_node_name: str,
    actual_node_name: str,
    source_label: str,
) -> None:
    if actual_node_name != expected_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: expected "
            f"target_node_names entry {expected_node_name!r}, but "
            f"{source_label} has {actual_node_name!r}."
        )


def _build_status_is_normal_not_built_status(
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> bool:
    return build_status in (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
    )


def _build_status_requires_inlink_physical_ordering(
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> bool:
    return build_status in (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE,
    )


def _visit_key_to_inlink_name_from_candidates(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
    *,
    node_name: str,
) -> dict[OrderControlTvtVisitKey, str]:
    """
    Map each limited candidate VisitKey to its inlink name for one target Node.
    """
    visit_key_to_inlink_name: dict[OrderControlTvtVisitKey, str] = {}
    for candidate_visit in candidate_visits:
        visit_key = candidate_visit.visit_key
        if visit_key in visit_key_to_inlink_name:
            raise RuntimeError(
                f"Node {node_name!r}: duplicate VisitKey {visit_key!r} in "
                f"candidate_visits."
            )
        visit_key_to_inlink_name[visit_key] = candidate_visit.inlink_name
    return visit_key_to_inlink_name


def _physical_orders_for_node(
    inlink_physical_orders: tuple[OrderControlBaselineSnapshotInlinkPhysicalOrder, ...],
    node_name: str,
) -> list[OrderControlBaselineSnapshotInlinkPhysicalOrder]:
    """
    Collect snapshot physical-order records for one target Node in stored order.
    """
    physical_orders_on_node: list[OrderControlBaselineSnapshotInlinkPhysicalOrder] = []
    for physical_order in inlink_physical_orders:
        if physical_order.node_name == node_name:
            physical_orders_on_node.append(physical_order)
    return physical_orders_on_node


def _build_inlink_candidate_physical_orders_for_node(
    *,
    node_name: str,
    visit_key_to_inlink_name: dict[OrderControlTvtVisitKey, str],
    physical_orders_on_node: list[OrderControlBaselineSnapshotInlinkPhysicalOrder],
) -> tuple[OrderControlTvtInlinkCandidateVisitPhysicalOrder, ...]:
    """
    Walk snapshot physical orders and collect limited candidate VisitKeys per inlink.
    """
    matched_visit_keys: set[OrderControlTvtVisitKey] = set()
    inlink_results: list[OrderControlTvtInlinkCandidateVisitPhysicalOrder] = []

    for physical_order in physical_orders_on_node:
        inlink_name = physical_order.inlink_name
        candidate_keys_on_inlink: list[OrderControlTvtVisitKey] = []

        for visit_key in physical_order.visit_keys_head_to_tail:
            if visit_key not in visit_key_to_inlink_name:
                continue

            expected_inlink_name = visit_key_to_inlink_name[visit_key]
            if expected_inlink_name != inlink_name:
                raise RuntimeError(
                    f"Node {node_name!r}: candidate VisitKey {visit_key!r} has "
                    f"inlink_name={expected_inlink_name!r}, but appears on snapshot "
                    f"physical order for inlink {inlink_name!r}."
                )

            if visit_key in matched_visit_keys:
                raise RuntimeError(
                    f"Node {node_name!r}: candidate VisitKey {visit_key!r} "
                    f"appears in more than one snapshot physical-order record."
                )

            matched_visit_keys.add(visit_key)
            candidate_keys_on_inlink.append(visit_key)

        if len(candidate_keys_on_inlink) == 0:
            continue

        inlink_results.append(
            OrderControlTvtInlinkCandidateVisitPhysicalOrder(
                node_name=node_name,
                inlink_name=inlink_name,
                candidate_visit_keys_head_to_tail=tuple(candidate_keys_on_inlink),
            )
        )

    expected_visit_keys = set(visit_key_to_inlink_name.keys())
    if matched_visit_keys != expected_visit_keys:
        missing_visit_keys = expected_visit_keys - matched_visit_keys
        raise RuntimeError(
            f"Node {node_name!r}: limited candidate VisitKeys missing from "
            f"snapshot physical orders: {sorted(missing_visit_keys)!r}."
        )

    return tuple(inlink_results)


def build_tvt_inlink_candidate_physical_orders(
    candidate_visit_set_result: OrderControlTvtCandidateVisitSetResult,
) -> OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    """
    Group limited candidate visits by inlink snapshot physical order per Node.

    Walks ``fork_result.target_node_names`` in order, reads
    ``fork_result.inlink_physical_orders``, and arranges each Node's limited
    ``candidate_visits`` by inlink using snapshot-time queue order on each
    approach link. Does not modify upstream results, re-export the collector,
    or re-run baseline fork or candidate selection.
    """
    right_of_entry_selection_result = (
        candidate_visit_set_result.right_of_entry_selection_result
    )
    leading_confirmation_result = (
        right_of_entry_selection_result.leading_confirmation_result
    )
    arrived_confirmation_result = (
        leading_confirmation_result.arrived_confirmation_result
    )
    alignment_fork_result = arrived_confirmation_result.alignment_fork_result
    fork_result = alignment_fork_result.fork_result
    target_node_names = fork_result.target_node_names
    inlink_physical_orders = fork_result.inlink_physical_orders

    node_candidate_set_results = (
        candidate_visit_set_result.node_candidate_set_results
    )
    if len(node_candidate_set_results) != len(target_node_names):
        raise RuntimeError(
            "Node candidate set result count does not match "
            f"fork_result.target_node_names: "
            f"node_candidate_set_results={len(node_candidate_set_results)}, "
            f"target_node_names={len(target_node_names)}."
        )

    node_inlink_results: list[OrderControlTvtNodeInlinkCandidatePhysicalOrderResult] = []

    for node_index, node_name in enumerate(target_node_names):
        node_candidate_result = node_candidate_set_results[node_index]
        _verify_node_name_at_index(
            node_index=node_index,
            expected_node_name=node_name,
            actual_node_name=node_candidate_result.node_name,
            source_label="node candidate set result",
        )

        build_status = node_candidate_result.build_status

        if _build_status_is_normal_not_built_status(build_status):
            node_inlink_results.append(
                OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
                    node_name=node_name,
                    build_status=build_status,
                    inlink_candidate_physical_orders=(),
                )
            )
            continue

        if _build_status_requires_inlink_physical_ordering(build_status):
            visit_key_to_inlink_name = _visit_key_to_inlink_name_from_candidates(
                node_candidate_result.candidate_visits,
                node_name=node_name,
            )
            physical_orders_on_node = _physical_orders_for_node(
                inlink_physical_orders,
                node_name,
            )
            inlink_candidate_physical_orders = (
                _build_inlink_candidate_physical_orders_for_node(
                    node_name=node_name,
                    visit_key_to_inlink_name=visit_key_to_inlink_name,
                    physical_orders_on_node=physical_orders_on_node,
                )
            )

            node_inlink_results.append(
                OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
                    node_name=node_name,
                    build_status=build_status,
                    inlink_candidate_physical_orders=inlink_candidate_physical_orders,
                )
            )
            continue

        raise RuntimeError(
            f"Node {node_name!r}: unexpected candidate visit set build status "
            f"{build_status!r}."
        )

    return OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=candidate_visit_set_result,
        node_inlink_candidate_physical_order_results=tuple(node_inlink_results),
    )
