"""
Generate TVT-MP concrete buyer candidate sets from limited candidate visits.

Reads an existing inlink-grouped candidate physical-order result and a
VisitKey-level participation mapping. For each target Node whose baseline
information is complete, it excludes the right-of-entry inlink, builds
buyer prefixes from remaining inlink snapshot physical heads, and combines
those prefixes into concrete buyer candidate sets. Combined VisitKeys are
sorted by their position in ``candidate_visits``, which is already the
cross-inlink official baseline order toward that target Node.

This is a read-only stage before economic evaluation. It does not choose
confirmed buyers, sellers, ``trade_scope``, or trade ranks, and it does not
modify upstream results or re-run baseline processing.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from dataclasses import dataclass

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    OrderControlTvtInlinkCandidateVisitPhysicalOrder,
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


@dataclass(frozen=True)
class OrderControlTvtMpInlinkBuyerPrefixResult:
    """
    Empty-to-max buyer prefixes on one buyer-candidate inlink.

    ``buyer_prefixes_empty_to_max`` starts with the empty prefix and then
    grows one snapshot-physical head visit at a time up to the maximum
    prefix. Index 0 of each non-empty prefix is the candidate visit closest
    to the target Node on that inlink at snapshot time. This is not the
    cross-inlink official baseline order.
    """

    node_name: str
    inlink_name: str
    buyer_prefixes_empty_to_max: tuple[tuple[OrderControlTvtVisitKey, ...], ...]


@dataclass(frozen=True)
class OrderControlTvtMpConcreteBuyerCandidateSet:
    """
    One pre-evaluation concrete buyer candidate set.

    ``buyers_sorted`` is a non-empty participating VisitKey tuple in
    cross-inlink official baseline relative order toward the target Node.
    It is not a confirmed buyer set.
    """

    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]


@dataclass(frozen=True)
class OrderControlTvtNodeMpConcreteBuyerCandidateSetResult:
    """Per-target-Node TVT-MP concrete buyer candidate generation result."""

    node_name: str
    build_status: OrderControlTvtCandidateVisitSetStatus
    buyer_candidate_inlink_prefix_results: tuple[
        OrderControlTvtMpInlinkBuyerPrefixResult,
        ...,
    ]
    concrete_buyer_candidate_sets: tuple[
        OrderControlTvtMpConcreteBuyerCandidateSet,
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtMpConcreteBuyerCandidateSetResult:
    """Overall TVT-MP concrete buyer candidate generation result."""

    inlink_candidate_physical_order_result: (
        OrderControlTvtInlinkCandidatePhysicalOrderSetResult
    )
    node_concrete_buyer_candidate_set_results: tuple[
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
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


def _build_status_requires_buyer_candidate_generation(
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
) -> OrderControlTvtNodeMpConcreteBuyerCandidateSetResult:
    return OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
        node_name=node_name,
        build_status=build_status,
        buyer_candidate_inlink_prefix_results=(),
        concrete_buyer_candidate_sets=(),
    )


def _verify_node_result_counts(
    *,
    node_candidate_set_results: tuple[
        OrderControlTvtNodeCandidateVisitSetResult,
        ...,
    ],
    node_inlink_results: tuple[
        OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
        ...,
    ],
) -> None:
    candidate_count = len(node_candidate_set_results)
    inlink_count = len(node_inlink_results)
    if candidate_count != inlink_count:
        raise RuntimeError(
            "Node candidate set result count does not match inlink "
            "candidate physical-order result count: "
            f"node_candidate_set_results={candidate_count}, "
            f"node_inlink_candidate_physical_order_results={inlink_count}."
        )


def _verify_node_alignment_at_index(
    *,
    node_index: int,
    node_candidate_result: OrderControlTvtNodeCandidateVisitSetResult,
    node_inlink_result: OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
) -> None:
    candidate_node_name = node_candidate_result.node_name
    inlink_node_name = node_inlink_result.node_name
    if candidate_node_name != inlink_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: expected "
            f"candidate result {candidate_node_name!r}, but inlink "
            f"candidate physical-order result has {inlink_node_name!r}."
        )

    candidate_build_status = node_candidate_result.build_status
    inlink_build_status = node_inlink_result.build_status
    if candidate_build_status != inlink_build_status:
        raise RuntimeError(
            f"Build status mismatch at index {node_index} for Node "
            f"{candidate_node_name!r}: expected candidate result "
            f"{candidate_build_status!r}, but inlink candidate "
            f"physical-order result has {inlink_build_status!r}."
        )


def _validate_participation_for_candidate_visits(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> None:
    for candidate_visit in candidate_visits:
        visit_key = candidate_visit.visit_key
        if visit_key not in participates_by_visit_key:
            raise ValueError(
                "participates_by_visit_key is missing candidate VisitKey "
                f"{visit_key!r}."
            )
        participation_value = participates_by_visit_key[visit_key]
        if type(participation_value) is not bool:
            raise ValueError(
                f"participates_by_visit_key[{visit_key!r}] must be a Python "
                f"bool; got type {type(participation_value).__name__} with "
                f"value {participation_value!r}."
            )


def _visit_key_to_inlink_name_from_candidates(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
) -> dict[OrderControlTvtVisitKey, str]:
    """
    Map each limited candidate VisitKey to its approach-inlink name.

    This temporary dict is used only to identify the right-of-entry inlink.
    It is not stored on the result type.
    """
    visit_key_to_inlink_name: dict[OrderControlTvtVisitKey, str] = {}
    for candidate_visit in candidate_visits:
        visit_key_to_inlink_name[candidate_visit.visit_key] = (
            candidate_visit.inlink_name
        )
    return visit_key_to_inlink_name


def _visit_key_to_baseline_index_from_candidates(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
) -> dict[OrderControlTvtVisitKey, int]:
    """
    Map each limited candidate VisitKey to its official baseline position.

    ``candidate_visits`` is already sorted in the cross-inlink official
    baseline order toward the target Node. This temporary dict is used only
    to restore that relative order after prefix combination.
    """
    visit_key_to_baseline_index: dict[OrderControlTvtVisitKey, int] = {}
    baseline_index = 0
    for candidate_visit in candidate_visits:
        visit_key_to_baseline_index[candidate_visit.visit_key] = baseline_index
        baseline_index += 1
    return visit_key_to_baseline_index


def _visit_keys_from_inlink_physical_orders(
    inlink_candidate_physical_orders: tuple[
        OrderControlTvtInlinkCandidateVisitPhysicalOrder,
        ...,
    ],
) -> set[OrderControlTvtVisitKey]:
    physical_order_visit_keys: set[OrderControlTvtVisitKey] = set()
    for inlink_order in inlink_candidate_physical_orders:
        for visit_key in inlink_order.candidate_visit_keys_head_to_tail:
            physical_order_visit_keys.add(visit_key)
    return physical_order_visit_keys


def _verify_candidate_and_physical_order_visit_key_sets(
    *,
    node_name: str,
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
    inlink_candidate_physical_orders: tuple[
        OrderControlTvtInlinkCandidateVisitPhysicalOrder,
        ...,
    ],
) -> None:
    candidate_visit_keys: set[OrderControlTvtVisitKey] = set()
    for candidate_visit in candidate_visits:
        candidate_visit_keys.add(candidate_visit.visit_key)

    physical_order_visit_keys = _visit_keys_from_inlink_physical_orders(
        inlink_candidate_physical_orders,
    )
    if candidate_visit_keys == physical_order_visit_keys:
        return

    only_in_candidate_visits = candidate_visit_keys - physical_order_visit_keys
    only_in_physical_orders = physical_order_visit_keys - candidate_visit_keys
    raise RuntimeError(
        f"Node {node_name!r}: candidate_visits VisitKey set does not match "
        "inlink candidate physical-order VisitKey set. Only in "
        f"candidate_visits: {sorted(only_in_candidate_visits)!r}. Only in "
        f"inlink physical orders: {sorted(only_in_physical_orders)!r}."
    )


def _resolve_right_of_entry_inlink_name(
    *,
    node_name: str,
    right_of_entry_visit_key: OrderControlTvtVisitKey | None,
    visit_key_to_inlink_name: dict[OrderControlTvtVisitKey, str],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> str:
    if right_of_entry_visit_key is None:
        raise RuntimeError(
            f"Node {node_name!r}: BASELINE_INFORMATION_COMPLETE but "
            "right_of_entry_visit_key is None."
        )
    if right_of_entry_visit_key not in visit_key_to_inlink_name:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} is missing from candidate_visits."
        )
    if not participates_by_visit_key[right_of_entry_visit_key]:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} is not a participating Visit."
        )
    return visit_key_to_inlink_name[right_of_entry_visit_key]


def _build_max_prefix_for_inlink(
    candidate_visit_keys_head_to_tail: tuple[OrderControlTvtVisitKey, ...],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> tuple[OrderControlTvtVisitKey, ...]:
    """
    Collect the snapshot-physical head run of participating candidate visits.

    The first non-participating visit stops the prefix. That visit and every
    visit behind it stay out of the buyer prefix, because a non-participant
    at the physical head cannot be overtaken on the same inlink.
    """
    max_prefix_visit_keys: list[OrderControlTvtVisitKey] = []
    for visit_key in candidate_visit_keys_head_to_tail:
        participates = participates_by_visit_key[visit_key]
        if participates:
            max_prefix_visit_keys.append(visit_key)
            continue
        break
    return tuple(max_prefix_visit_keys)


def _build_all_prefixes_empty_to_max(
    max_prefix: tuple[OrderControlTvtVisitKey, ...],
) -> tuple[tuple[OrderControlTvtVisitKey, ...], ...]:
    """
    Build every prefix from the empty tuple through the maximum prefix.

    Shorter prefixes remain selectable even when a non-participant later
    limits the maximum prefix length.
    """
    prefixes: list[tuple[OrderControlTvtVisitKey, ...]] = []
    prefixes.append(())
    prefix_length = 1
    while prefix_length <= len(max_prefix):
        next_prefix = max_prefix[:prefix_length]
        prefixes.append(next_prefix)
        prefix_length += 1
    return tuple(prefixes)


def _collect_buyer_candidate_inlink_prefix_results(
    *,
    node_name: str,
    right_of_entry_inlink_name: str,
    inlink_candidate_physical_orders: tuple[
        OrderControlTvtInlinkCandidateVisitPhysicalOrder,
        ...,
    ],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> tuple[OrderControlTvtMpInlinkBuyerPrefixResult, ...]:
    buyer_candidate_inlink_prefix_results: list[
        OrderControlTvtMpInlinkBuyerPrefixResult
    ] = []
    for inlink_order in inlink_candidate_physical_orders:
        if inlink_order.inlink_name == right_of_entry_inlink_name:
            continue

        max_prefix = _build_max_prefix_for_inlink(
            inlink_order.candidate_visit_keys_head_to_tail,
            participates_by_visit_key,
        )
        if len(max_prefix) == 0:
            continue

        buyer_prefixes_empty_to_max = _build_all_prefixes_empty_to_max(
            max_prefix,
        )
        buyer_candidate_inlink_prefix_results.append(
            OrderControlTvtMpInlinkBuyerPrefixResult(
                node_name=node_name,
                inlink_name=inlink_order.inlink_name,
                buyer_prefixes_empty_to_max=buyer_prefixes_empty_to_max,
            )
        )
    return tuple(buyer_candidate_inlink_prefix_results)


def _baseline_index_from_indexed_visit(
    indexed_visit: tuple[int, OrderControlTvtVisitKey],
) -> int:
    return indexed_visit[0]


def _sort_visit_keys_by_baseline_index(
    merged_visit_keys: list[OrderControlTvtVisitKey],
    visit_key_to_baseline_index: dict[OrderControlTvtVisitKey, int],
) -> list[OrderControlTvtVisitKey]:
    indexed_visit_keys: list[tuple[int, OrderControlTvtVisitKey]] = []
    for visit_key in merged_visit_keys:
        baseline_index = visit_key_to_baseline_index[visit_key]
        indexed_visit_keys.append((baseline_index, visit_key))
    indexed_visit_keys.sort(key=_baseline_index_from_indexed_visit)

    sorted_visit_keys: list[OrderControlTvtVisitKey] = []
    for _baseline_index, visit_key in indexed_visit_keys:
        sorted_visit_keys.append(visit_key)
    return sorted_visit_keys


def _prefix_combination_is_all_empty(
    prefix_combination: tuple[tuple[OrderControlTvtVisitKey, ...], ...],
) -> bool:
    for selected_prefix in prefix_combination:
        if len(selected_prefix) > 0:
            return False
    return True


def _concrete_sets_from_prefix_product(
    buyer_candidate_inlink_prefix_results: tuple[
        OrderControlTvtMpInlinkBuyerPrefixResult,
        ...,
    ],
    visit_key_to_baseline_index: dict[OrderControlTvtVisitKey, int],
) -> tuple[OrderControlTvtMpConcreteBuyerCandidateSet, ...]:
    if len(buyer_candidate_inlink_prefix_results) == 0:
        return ()

    prefix_product_axes: list[tuple[tuple[OrderControlTvtVisitKey, ...], ...]] = []
    for prefix_result in buyer_candidate_inlink_prefix_results:
        prefix_product_axes.append(prefix_result.buyer_prefixes_empty_to_max)

    concrete_buyer_candidate_sets: list[
        OrderControlTvtMpConcreteBuyerCandidateSet
    ] = []
    for prefix_combination in itertools.product(*prefix_product_axes):
        if _prefix_combination_is_all_empty(prefix_combination):
            continue

        merged_visit_keys: list[OrderControlTvtVisitKey] = []
        for selected_prefix in prefix_combination:
            for visit_key in selected_prefix:
                merged_visit_keys.append(visit_key)

        sorted_visit_keys = _sort_visit_keys_by_baseline_index(
            merged_visit_keys,
            visit_key_to_baseline_index,
        )
        buyers_sorted = tuple(sorted_visit_keys)
        concrete_buyer_candidate_sets.append(
            OrderControlTvtMpConcreteBuyerCandidateSet(
                buyers_sorted=buyers_sorted,
            )
        )
    return tuple(concrete_buyer_candidate_sets)


def _build_node_concrete_buyer_candidate_set_result(
    *,
    node_candidate_result: OrderControlTvtNodeCandidateVisitSetResult,
    node_inlink_result: OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtNodeMpConcreteBuyerCandidateSetResult:
    node_name = node_candidate_result.node_name
    candidate_visits = node_candidate_result.candidate_visits
    inlink_candidate_physical_orders = (
        node_inlink_result.inlink_candidate_physical_orders
    )

    _validate_participation_for_candidate_visits(
        candidate_visits,
        participates_by_visit_key,
    )
    visit_key_to_inlink_name = _visit_key_to_inlink_name_from_candidates(
        candidate_visits,
    )
    visit_key_to_baseline_index = _visit_key_to_baseline_index_from_candidates(
        candidate_visits,
    )
    _verify_candidate_and_physical_order_visit_key_sets(
        node_name=node_name,
        candidate_visits=candidate_visits,
        inlink_candidate_physical_orders=inlink_candidate_physical_orders,
    )
    right_of_entry_inlink_name = _resolve_right_of_entry_inlink_name(
        node_name=node_name,
        right_of_entry_visit_key=node_candidate_result.right_of_entry_visit_key,
        visit_key_to_inlink_name=visit_key_to_inlink_name,
        participates_by_visit_key=participates_by_visit_key,
    )
    buyer_candidate_inlink_prefix_results = (
        _collect_buyer_candidate_inlink_prefix_results(
            node_name=node_name,
            right_of_entry_inlink_name=right_of_entry_inlink_name,
            inlink_candidate_physical_orders=inlink_candidate_physical_orders,
            participates_by_visit_key=participates_by_visit_key,
        )
    )
    concrete_buyer_candidate_sets = _concrete_sets_from_prefix_product(
        buyer_candidate_inlink_prefix_results,
        visit_key_to_baseline_index,
    )
    return OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
        node_name=node_name,
        build_status=node_candidate_result.build_status,
        buyer_candidate_inlink_prefix_results=(
            buyer_candidate_inlink_prefix_results
        ),
        concrete_buyer_candidate_sets=concrete_buyer_candidate_sets,
    )


def build_tvt_mp_concrete_buyer_candidate_sets(
    inlink_candidate_physical_order_result: (
        OrderControlTvtInlinkCandidatePhysicalOrderSetResult
    ),
    *,
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtMpConcreteBuyerCandidateSetResult:
    """
    Build TVT-MP concrete buyer candidate sets for each target Node.

    Walks the existing inlink physical-order Node results in stored order.
    Only ``BASELINE_INFORMATION_COMPLETE`` Nodes generate prefixes and
    concrete buyer candidate sets. Other formal statuses keep empty tuples.
    Does not modify the input result or the participation mapping, and does
    not re-run upstream candidate construction.
    """
    candidate_visit_set_result = (
        inlink_candidate_physical_order_result.candidate_visit_set_result
    )
    node_candidate_set_results = (
        candidate_visit_set_result.node_candidate_set_results
    )
    node_inlink_results = (
        inlink_candidate_physical_order_result.node_inlink_candidate_physical_order_results
    )
    _verify_node_result_counts(
        node_candidate_set_results=node_candidate_set_results,
        node_inlink_results=node_inlink_results,
    )

    node_concrete_buyer_candidate_set_results: list[
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult
    ] = []
    node_index = 0
    while node_index < len(node_candidate_set_results):
        node_candidate_result = node_candidate_set_results[node_index]
        node_inlink_result = node_inlink_results[node_index]
        _verify_node_alignment_at_index(
            node_index=node_index,
            node_candidate_result=node_candidate_result,
            node_inlink_result=node_inlink_result,
        )

        build_status = node_candidate_result.build_status
        if _build_status_is_normal_not_generated_status(build_status):
            node_concrete_buyer_candidate_set_results.append(
                _empty_node_result(
                    node_name=node_candidate_result.node_name,
                    build_status=build_status,
                )
            )
            node_index += 1
            continue

        if _build_status_requires_buyer_candidate_generation(build_status):
            node_result = _build_node_concrete_buyer_candidate_set_result(
                node_candidate_result=node_candidate_result,
                node_inlink_result=node_inlink_result,
                participates_by_visit_key=participates_by_visit_key,
            )
            node_concrete_buyer_candidate_set_results.append(node_result)
            node_index += 1
            continue

        raise RuntimeError(
            f"Node {node_candidate_result.node_name!r}: unexpected "
            f"candidate visit set build status {build_status!r}."
        )

    return OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=(
            inlink_candidate_physical_order_result
        ),
        node_concrete_buyer_candidate_set_results=tuple(
            node_concrete_buyer_candidate_set_results
        ),
    )
