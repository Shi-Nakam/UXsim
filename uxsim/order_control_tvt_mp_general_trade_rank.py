"""
TVT-MP general trade-rank reconstruction with and without
non-participating visits.

Reads an existing concrete buyer candidate set result and a VisitKey-level
participation mapping. For each target Node whose baseline information is
complete and that has at least one concrete buyer candidate set, it builds
``trade_scope``, classifies visits in that scope into buyers, sellers, and
non-participating visits, then reconstructs post-trade ranks by the vacant
rank-slot method.

This is a read-only stage before FIFO inspection. It does not run
inlink FIFO inspection, local virtual calculation, or economic
evaluation, and it does not modify upstream results or re-run baseline
processing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


@dataclass(frozen=True)
class OrderControlTvtNodeMpGeneralTradeRankResult:
    """Per-target-Node TVT-MP general trade-rank reconstruction result."""

    node_name: str
    build_status: OrderControlTvtCandidateVisitSetStatus
    candidate_trade_rank_results: tuple[
        "OrderControlTvtMpGeneralTradeRankResult",
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtMpGeneralTradeRankSetResult:
    """Overall TVT-MP general trade-rank reconstruction result."""

    concrete_buyer_candidate_set_result: (
        OrderControlTvtMpConcreteBuyerCandidateSetResult
    )
    node_trade_rank_results: tuple[
        OrderControlTvtNodeMpGeneralTradeRankResult,
        ...,
    ]


class OrderControlTvtMpGeneralTradeRankResult:
    """
    General trade-rank result for one concrete buyer candidate set.

    Holds the reconstructed post-trade ranks for every limited candidate
    VisitKey toward one target Node, including visits outside
    ``trade_scope``. The rank dictionary is the source of truth;
    ``trade_order`` is derived from it.
    """

    def __init__(
        self,
        *,
        concrete_buyer_candidate_set: OrderControlTvtMpConcreteBuyerCandidateSet,
        buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
        sellers_sorted: tuple[OrderControlTvtVisitKey, ...],
        nonparticipating_visits_sorted: tuple[OrderControlTvtVisitKey, ...],
        last_buyer_rank: int,
        trade_scope: tuple[OrderControlTvtVisitKey, ...],
        trade_order: tuple[OrderControlTvtVisitKey, ...],
        trade_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    ) -> None:
        if not isinstance(
            concrete_buyer_candidate_set,
            OrderControlTvtMpConcreteBuyerCandidateSet,
        ):
            raise ValueError(
                "concrete_buyer_candidate_set must be "
                "OrderControlTvtMpConcreteBuyerCandidateSet; got "
                f"type {type(concrete_buyer_candidate_set).__name__}."
            )
        self._concrete_buyer_candidate_set = concrete_buyer_candidate_set

        buyers_tuple = _require_tuple_container(
            buyers_sorted,
            "buyers_sorted",
        )
        self._buyers_sorted = _validate_visit_key_sequence(
            buyers_tuple,
            field_name="buyers_sorted",
            allow_empty=False,
        )

        sellers_tuple = _require_tuple_container(
            sellers_sorted,
            "sellers_sorted",
        )
        self._sellers_sorted = _validate_visit_key_sequence(
            sellers_tuple,
            field_name="sellers_sorted",
            allow_empty=True,
        )

        nonparticipating_tuple = _require_tuple_container(
            nonparticipating_visits_sorted,
            "nonparticipating_visits_sorted",
        )
        self._nonparticipating_visits_sorted = _validate_visit_key_sequence(
            nonparticipating_tuple,
            field_name="nonparticipating_visits_sorted",
            allow_empty=True,
        )

        self._last_buyer_rank = _require_python_int_rank(
            last_buyer_rank,
            field_name="last_buyer_rank",
        )

        trade_scope_tuple = _require_tuple_container(
            trade_scope,
            "trade_scope",
        )
        self._trade_scope = _validate_visit_key_sequence(
            trade_scope_tuple,
            field_name="trade_scope",
            allow_empty=False,
        )

        trade_order_tuple = _require_tuple_container(
            trade_order,
            "trade_order",
        )
        self._trade_order = _validate_visit_key_sequence(
            trade_order_tuple,
            field_name="trade_order",
            allow_empty=False,
        )

        if not isinstance(trade_rank_by_visit_key, dict):
            raise ValueError(
                "trade_rank_by_visit_key must be a dict; got "
                f"type {type(trade_rank_by_visit_key).__name__}."
            )
        if len(trade_rank_by_visit_key) == 0:
            raise ValueError("trade_rank_by_visit_key must not be empty.")

        validated_trade_rank: dict[OrderControlTvtVisitKey, int] = {}
        for visit_key, rank_value in trade_rank_by_visit_key.items():
            validated_visit_key = _validate_visit_key(
                visit_key,
                field_name="trade_rank_by_visit_key key",
            )
            validated_trade_rank[validated_visit_key] = (
                _require_python_int_rank(
                    rank_value,
                    field_name=(
                        "trade_rank_by_visit_key["
                        f"{validated_visit_key!r}]"
                    ),
                )
            )

        # Defensive copy so later mutation of the caller's dict cannot
        # change the stored post-trade ranks.
        self._trade_rank_by_visit_key = dict(validated_trade_rank)

    @property
    def concrete_buyer_candidate_set(
        self,
    ) -> OrderControlTvtMpConcreteBuyerCandidateSet:
        return self._concrete_buyer_candidate_set

    @property
    def buyers_sorted(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._buyers_sorted

    @property
    def sellers_sorted(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._sellers_sorted

    @property
    def nonparticipating_visits_sorted(
        self,
    ) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._nonparticipating_visits_sorted

    @property
    def last_buyer_rank(self) -> int:
        return self._last_buyer_rank

    @property
    def trade_scope(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._trade_scope

    @property
    def trade_order(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._trade_order

    def assigned_rank(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> int:
        validated_visit_key = _validate_visit_key(visit_key)
        rank_value = self._trade_rank_by_visit_key.get(validated_visit_key)
        if rank_value is None:
            raise ValueError(
                f"VisitKey {validated_visit_key!r} is not present in this "
                "general trade-rank result."
            )
        return rank_value

    def trade_rank_items(
        self,
    ) -> tuple[tuple[OrderControlTvtVisitKey, int], ...]:
        items: list[tuple[OrderControlTvtVisitKey, int]] = []
        for visit_key in self._trade_order:
            items.append(
                (visit_key, self._trade_rank_by_visit_key[visit_key])
            )
        return tuple(items)


def _require_non_empty_str(value: object, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _validate_visit_key(
    value: object,
    field_name: str = "visit_key",
) -> OrderControlTvtVisitKey:
    if not isinstance(value, tuple):
        raise ValueError(
            f"{field_name} must be a length-2 tuple (vehicle_name, visit_id); "
            f"got type {type(value).__name__} with value {value!r}."
        )
    if len(value) != 2:
        raise ValueError(
            f"{field_name} must be a length-2 tuple (vehicle_name, visit_id); "
            f"got length {len(value)} with value {value!r}."
        )
    vehicle_name, visit_id = value
    vehicle_name = _require_non_empty_str(
        vehicle_name,
        f"{field_name}[0] (vehicle_name)",
    )
    if type(visit_id) is not int:
        raise ValueError(
            f"{field_name}[1] (visit_id) must be a Python int (not bool); "
            f"got type {type(visit_id).__name__} with value {visit_id!r}."
        )
    if visit_id < 1:
        raise ValueError(
            f"{field_name}[1] (visit_id) must be >= 1; got {visit_id!r}."
        )
    return (vehicle_name, visit_id)


def _require_tuple_container(
    value: object,
    field_name: str,
) -> tuple[OrderControlTvtVisitKey, ...]:
    if not isinstance(value, tuple):
        raise ValueError(
            f"{field_name} must be a tuple of VisitKey tuples; "
            f"got type {type(value).__name__} with value {value!r}."
        )
    return value


def _find_duplicate_visit_keys(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    seen: set[OrderControlTvtVisitKey] = set()
    for visit_key in visit_keys:
        if visit_key in seen:
            return visit_key
        seen.add(visit_key)
    return None


def _validate_visit_key_sequence(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
    *,
    field_name: str,
    allow_empty: bool,
) -> tuple[OrderControlTvtVisitKey, ...]:
    if not allow_empty and len(visit_keys) == 0:
        raise ValueError(f"{field_name} must not be empty.")

    validated_visit_keys: list[OrderControlTvtVisitKey] = []
    for index, visit_key in enumerate(visit_keys):
        validated_visit_keys.append(
            _validate_visit_key(
                visit_key,
                field_name=f"{field_name}[{index}]",
            )
        )
    validated_visit_keys_tuple = tuple(validated_visit_keys)

    duplicate_visit_key = _find_duplicate_visit_keys(
        validated_visit_keys_tuple
    )
    if duplicate_visit_key is not None:
        raise ValueError(
            f"Duplicate VisitKey {duplicate_visit_key!r} in {field_name}."
        )

    return validated_visit_keys_tuple


def _require_python_int_rank(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValueError(
            f"{field_name} must be a Python int (not bool); "
            f"got type {type(value).__name__} with value {value!r}."
        )
    if value < 1:
        raise ValueError(f"{field_name} must be >= 1; got {value!r}.")
    return value


def _build_status_is_normal_not_generated_status(
    build_status: OrderControlTvtCandidateVisitSetStatus,
) -> bool:
    return build_status in (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
    )


def _build_status_requires_trade_rank_reconstruction(
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
) -> OrderControlTvtNodeMpGeneralTradeRankResult:
    return OrderControlTvtNodeMpGeneralTradeRankResult(
        node_name=node_name,
        build_status=build_status,
        candidate_trade_rank_results=(),
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
) -> None:
    candidate_count = len(node_candidate_set_results)
    concrete_count = len(node_concrete_buyer_candidate_set_results)
    if candidate_count != concrete_count:
        raise RuntimeError(
            "Node candidate set result count does not match concrete "
            "buyer candidate set result count: expected "
            f"node_candidate_set_results={candidate_count}, actual "
            "node_concrete_buyer_candidate_set_results="
            f"{concrete_count}."
        )


def _verify_node_alignment_at_index(
    *,
    node_index: int,
    node_candidate_result: OrderControlTvtNodeCandidateVisitSetResult,
    node_concrete_result: OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
) -> None:
    candidate_node_name = node_candidate_result.node_name
    concrete_node_name = node_concrete_result.node_name
    if candidate_node_name != concrete_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: expected "
            f"candidate result {candidate_node_name!r}, actual concrete "
            f"buyer candidate set result {concrete_node_name!r}."
        )

    candidate_build_status = node_candidate_result.build_status
    concrete_build_status = node_concrete_result.build_status
    if candidate_build_status != concrete_build_status:
        raise RuntimeError(
            f"Build status mismatch at index {node_index} for Node "
            f"{candidate_node_name!r}: expected candidate result "
            f"{candidate_build_status!r}, actual concrete buyer "
            f"candidate set result {concrete_build_status!r}."
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


def _build_baseline_order_and_ranks(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
) -> tuple[
    tuple[OrderControlTvtVisitKey, ...],
    dict[OrderControlTvtVisitKey, int],
]:
    """
    Read the official baseline order from ``candidate_visits`` positions.

    ``candidate_visits`` is already the cross-inlink official baseline
    order toward the target Node. This helper does not re-sort by arrival
    timestep, tiebreaker, or vehicle id, and it does not use participation.
    Ranks are 1-based. The rank dict is temporary and is not stored on the
    result type.
    """
    baseline_order_list: list[OrderControlTvtVisitKey] = []
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int] = {}
    rank_value = 1
    for candidate_visit in candidate_visits:
        visit_key = candidate_visit.visit_key
        baseline_order_list.append(visit_key)
        baseline_rank_by_visit_key[visit_key] = rank_value
        rank_value += 1
    baseline_order = tuple(baseline_order_list)
    return baseline_order, baseline_rank_by_visit_key


def _sequence_preserves_baseline_relative_order(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
) -> bool:
    index = 1
    while index < len(visit_keys):
        previous_visit_key = visit_keys[index - 1]
        current_visit_key = visit_keys[index]
        previous_rank = baseline_rank_by_visit_key[previous_visit_key]
        current_rank = baseline_rank_by_visit_key[current_visit_key]
        if previous_rank >= current_rank:
            return False
        index += 1
    return True


def _verify_right_of_entry_visit(
    *,
    node_name: str,
    right_of_entry_visit_key: OrderControlTvtVisitKey | None,
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> None:
    if right_of_entry_visit_key is None:
        raise RuntimeError(
            f"Node {node_name!r}: BASELINE_INFORMATION_COMPLETE with "
            "concrete buyer candidate sets, but right_of_entry_visit_key "
            "is None."
        )
    if right_of_entry_visit_key not in baseline_rank_by_visit_key:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} is not present in "
            "candidate_visits."
        )
    right_of_entry_participation = participates_by_visit_key[
        right_of_entry_visit_key
    ]
    if right_of_entry_participation is False:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} is non-participating."
        )


def _verify_buyers_sorted_against_baseline(
    *,
    node_name: str,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> None:
    if len(buyers_sorted) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: concrete buyer candidate set "
            "buyers_sorted must not be empty."
        )

    for buyer in buyers_sorted:
        if buyer not in baseline_rank_by_visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {buyer!r} is not "
                "present in candidate_visits."
            )
        participation_value = participates_by_visit_key[buyer]
        if participation_value is False:
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {buyer!r} is "
                "non-participating."
            )

    if not _sequence_preserves_baseline_relative_order(
        buyers_sorted,
        baseline_rank_by_visit_key,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: buyers_sorted does not preserve the "
            "cross-inlink official baseline relative order."
        )


def _classify_trade_scope_visits(
    *,
    trade_scope: tuple[OrderControlTvtVisitKey, ...],
    buyer_set: set[OrderControlTvtVisitKey],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> tuple[
    tuple[OrderControlTvtVisitKey, ...],
    tuple[OrderControlTvtVisitKey, ...],
    tuple[OrderControlTvtVisitKey, ...],
]:
    """
    Classify each ``trade_scope`` visit in official baseline order.

    Classification order:

    1. A visit in the concrete buyer candidate set is a buyer.
    2. A non-buyer with participation False is a non-participating visit.
    3. A non-buyer with participation True is a seller.

    Right-of-entry visits and other visits on the right-of-entry inlink
    are classified by the same rule when they appear in ``trade_scope``.
    They are not excluded here; right-of-entry inlink exclusion applies
    only when generating buyer candidates.
    """
    classified_buyers: list[OrderControlTvtVisitKey] = []
    classified_sellers: list[OrderControlTvtVisitKey] = []
    classified_nonparticipants: list[OrderControlTvtVisitKey] = []

    for visit_key in trade_scope:
        if visit_key in buyer_set:
            classified_buyers.append(visit_key)
            continue
        participation_value = participates_by_visit_key[visit_key]
        if participation_value is False:
            classified_nonparticipants.append(visit_key)
            continue
        classified_sellers.append(visit_key)

    return (
        tuple(classified_buyers),
        tuple(classified_sellers),
        tuple(classified_nonparticipants),
    )


def _build_vacant_ranks(
    *,
    last_buyer_rank: int,
    nonparticipating_visits_sorted: tuple[OrderControlTvtVisitKey, ...],
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
) -> list[int]:
    """
    Build unused local ranks in ``trade_scope`` after non-participant
    baseline ranks are reserved.

    Local ranks run from 1 to ``last_buyer_rank``. Non-participating
    visits keep their official baseline local ranks. The remaining ranks
    are vacant slots, returned in ascending order.
    """
    fixed_rank_set: set[int] = set()
    for visit_key in nonparticipating_visits_sorted:
        fixed_rank = baseline_rank_by_visit_key[visit_key]
        fixed_rank_set.add(fixed_rank)

    vacant_ranks: list[int] = []
    rank_value = 1
    while rank_value <= last_buyer_rank:
        if rank_value not in fixed_rank_set:
            vacant_ranks.append(rank_value)
        rank_value += 1
    return vacant_ranks


def _assign_buyers_to_leading_vacant_ranks(
    *,
    trade_rank: dict[OrderControlTvtVisitKey, int],
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    vacant_ranks: list[int],
) -> None:
    buyer_index = 0
    for buyer in buyers_sorted:
        trade_rank[buyer] = vacant_ranks[buyer_index]
        buyer_index += 1


def _assign_sellers_to_remaining_vacant_ranks(
    *,
    trade_rank: dict[OrderControlTvtVisitKey, int],
    sellers_sorted: tuple[OrderControlTvtVisitKey, ...],
    vacant_ranks: list[int],
    buyer_count: int,
) -> None:
    seller_index = 0
    for seller in sellers_sorted:
        remaining_rank = vacant_ranks[buyer_count + seller_index]
        trade_rank[seller] = remaining_rank
        seller_index += 1


def _assign_outside_trade_scope_baseline_ranks(
    *,
    trade_rank: dict[OrderControlTvtVisitKey, int],
    baseline_order: tuple[OrderControlTvtVisitKey, ...],
    last_buyer_rank: int,
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
) -> None:
    outside_index = last_buyer_rank
    while outside_index < len(baseline_order):
        visit_key = baseline_order[outside_index]
        trade_rank[visit_key] = baseline_rank_by_visit_key[visit_key]
        outside_index += 1


def _build_trade_order_from_trade_rank(
    *,
    baseline_order: tuple[OrderControlTvtVisitKey, ...],
    trade_rank: dict[OrderControlTvtVisitKey, int],
) -> tuple[OrderControlTvtVisitKey, ...]:
    """
    Derive ``trade_order`` from ``trade_rank``.

    ``trade_rank`` remains the source of truth. Visits are listed by
    increasing post-trade rank. Rank values are unique, so this order is
    unique.
    """
    ranked_pairs: list[tuple[int, OrderControlTvtVisitKey]] = []
    for visit_key in baseline_order:
        rank_value = trade_rank[visit_key]
        ranked_pairs.append((rank_value, visit_key))

    ranked_pairs.sort()

    trade_order_list: list[OrderControlTvtVisitKey] = []
    for rank_value, visit_key in ranked_pairs:
        trade_order_list.append(visit_key)
    return tuple(trade_order_list)


def _validate_internal_trade_rank_value(
    rank_value: object,
    visit_key: OrderControlTvtVisitKey,
) -> int:
    if type(rank_value) is not int:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_rank "
            f"{visit_key!r} must be a Python int (not bool); "
            f"got type {type(rank_value).__name__} with value {rank_value!r}."
        )
    if rank_value < 1:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_rank "
            f"{visit_key!r} must be >= 1; got {rank_value!r}."
        )
    return rank_value


def _verify_general_trade_rank_state(
    *,
    baseline_order: tuple[OrderControlTvtVisitKey, ...],
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    sellers_sorted: tuple[OrderControlTvtVisitKey, ...],
    nonparticipating_visits_sorted: tuple[OrderControlTvtVisitKey, ...],
    last_buyer_rank: int,
    trade_scope: tuple[OrderControlTvtVisitKey, ...],
    trade_rank: dict[OrderControlTvtVisitKey, int],
    trade_order: tuple[OrderControlTvtVisitKey, ...],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> None:
    """
    General-form internal consistency checks for the vacant rank-slot
    method.

    This is not the non-participant-free seller-retreat formula used by
    the existing dedicated trade-rank helper. Failure is ``RuntimeError``.
    """
    if len(buyers_sorted) == 0:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: "
            "buyers_sorted must not be empty."
        )

    for buyer in buyers_sorted:
        if buyer not in baseline_rank_by_visit_key:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: buyer "
                f"{buyer!r} is not present in baseline_order."
            )
        participation_value = participates_by_visit_key[buyer]
        if participation_value is not True:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: buyer "
                f"{buyer!r} is not a participating visit."
            )

    if not _sequence_preserves_baseline_relative_order(
        buyers_sorted,
        baseline_rank_by_visit_key,
    ):
        raise RuntimeError(
            "Internal general trade-rank inconsistency: buyers_sorted "
            "does not preserve baseline relative order."
        )

    if type(last_buyer_rank) is not int:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: last_buyer_rank "
            "must be a Python int (not bool); got type "
            f"{type(last_buyer_rank).__name__} with value "
            f"{last_buyer_rank!r}."
        )
    if last_buyer_rank < 1:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: last_buyer_rank "
            "must be >= 1."
        )
    if last_buyer_rank > len(baseline_order):
        raise RuntimeError(
            "Internal general trade-rank inconsistency: last_buyer_rank "
            "exceeds baseline_order length."
        )

    last_buyer = buyers_sorted[-1]
    expected_last_buyer_rank = baseline_rank_by_visit_key[last_buyer]
    if last_buyer_rank != expected_last_buyer_rank:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: last_buyer_rank "
            "does not match the trailing buyer baseline rank."
        )

    expected_trade_scope = baseline_order[:last_buyer_rank]
    if trade_scope != expected_trade_scope:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_scope does "
            "not match baseline_order[:last_buyer_rank]."
        )
    if trade_scope[-1] != last_buyer:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_scope must "
            "end with the trailing buyer."
        )

    buyer_set = set(buyers_sorted)
    seller_set = set(sellers_sorted)
    nonparticipant_set = set(nonparticipating_visits_sorted)
    if buyer_set & seller_set:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: buyers_sorted "
            "and sellers_sorted overlap."
        )
    if buyer_set & nonparticipant_set:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: buyers_sorted "
            "and nonparticipating_visits_sorted overlap."
        )
    if seller_set & nonparticipant_set:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: sellers_sorted "
            "and nonparticipating_visits_sorted overlap."
        )
    classified_union = buyer_set | seller_set | nonparticipant_set
    if classified_union != set(trade_scope):
        raise RuntimeError(
            "Internal general trade-rank inconsistency: buyers, sellers, "
            "and non-participating visits do not partition trade_scope."
        )

    if not _sequence_preserves_baseline_relative_order(
        sellers_sorted,
        baseline_rank_by_visit_key,
    ):
        raise RuntimeError(
            "Internal general trade-rank inconsistency: sellers_sorted "
            "does not preserve baseline relative order."
        )
    if not _sequence_preserves_baseline_relative_order(
        nonparticipating_visits_sorted,
        baseline_rank_by_visit_key,
    ):
        raise RuntimeError(
            "Internal general trade-rank inconsistency: "
            "nonparticipating_visits_sorted does not preserve baseline "
            "relative order."
        )

    baseline_visit_set = set(baseline_order)
    trade_rank_visit_set = set(trade_rank)
    trade_order_visit_set = set(trade_order)
    if trade_rank_visit_set != baseline_visit_set:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_rank "
            "VisitKey set does not match baseline_order."
        )
    if trade_order_visit_set != baseline_visit_set:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_order "
            "VisitKey set does not match baseline_order."
        )
    if len(trade_order) != len(baseline_order):
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_order "
            f"length {len(trade_order)} does not match baseline_order "
            f"length {len(baseline_order)}."
        )

    rank_values: list[int] = []
    for visit_key, rank_value in trade_rank.items():
        validated_rank_value = _validate_internal_trade_rank_value(
            rank_value,
            visit_key,
        )
        rank_values.append(validated_rank_value)

    expected_rank_set = set(range(1, len(baseline_order) + 1))
    actual_rank_set = set(rank_values)
    if actual_rank_set != expected_rank_set:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: trade_rank "
            f"values are not exactly 1..{len(baseline_order)}."
        )

    position = 1
    for visit_key in trade_order:
        rank_in_dict = trade_rank[visit_key]
        if rank_in_dict != position:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: trade_order "
                f"position {position} for VisitKey {visit_key!r} does "
                f"not match trade_rank value {rank_in_dict}."
            )
        position += 1

    for visit_key in nonparticipating_visits_sorted:
        baseline_local_rank = baseline_rank_by_visit_key[visit_key]
        actual_rank = trade_rank[visit_key]
        if actual_rank != baseline_local_rank:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: "
                "non-participating visit "
                f"{visit_key!r} changed rank from baseline local rank "
                f"{baseline_local_rank} to {actual_rank}."
            )

    for seller in sellers_sorted:
        seller_baseline_rank = baseline_rank_by_visit_key[seller]
        seller_trade_rank = trade_rank[seller]
        if seller_trade_rank <= seller_baseline_rank:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: seller "
                f"{seller!r} did not retreat; baseline rank "
                f"{seller_baseline_rank}, trade rank {seller_trade_rank}."
            )

    vacant_ranks = _build_vacant_ranks(
        last_buyer_rank=last_buyer_rank,
        nonparticipating_visits_sorted=nonparticipating_visits_sorted,
        baseline_rank_by_visit_key=baseline_rank_by_visit_key,
    )
    buyer_count = len(buyers_sorted)
    expected_buyer_count_and_seller_count = buyer_count + len(sellers_sorted)
    if len(vacant_ranks) != expected_buyer_count_and_seller_count:
        raise RuntimeError(
            "Internal general trade-rank inconsistency: vacant rank "
            f"count {len(vacant_ranks)} does not match buyers plus "
            f"sellers {expected_buyer_count_and_seller_count}."
        )

    buyer_index = 0
    for buyer in buyers_sorted:
        expected_rank = vacant_ranks[buyer_index]
        actual_rank = trade_rank[buyer]
        if actual_rank != expected_rank:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: buyer "
                f"{buyer!r} does not occupy leading vacant rank "
                f"{expected_rank}; got {actual_rank}."
            )
        buyer_index += 1

    seller_index = 0
    for seller in sellers_sorted:
        expected_rank = vacant_ranks[buyer_count + seller_index]
        actual_rank = trade_rank[seller]
        if actual_rank != expected_rank:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: seller "
                f"{seller!r} does not occupy remaining vacant rank "
                f"{expected_rank}; got {actual_rank}."
            )
        seller_index += 1

    trade_scope_set = set(trade_scope)
    for visit_key in baseline_order:
        if visit_key in trade_scope_set:
            continue
        if trade_rank[visit_key] != baseline_rank_by_visit_key[visit_key]:
            raise RuntimeError(
                "Internal general trade-rank inconsistency: visit "
                f"outside trade_scope {visit_key!r} changed rank."
            )


def _build_one_general_trade_rank_result(
    *,
    node_name: str,
    concrete_buyer_candidate_set: OrderControlTvtMpConcreteBuyerCandidateSet,
    baseline_order: tuple[OrderControlTvtVisitKey, ...],
    baseline_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtMpGeneralTradeRankResult:
    buyers_sorted = concrete_buyer_candidate_set.buyers_sorted
    _verify_buyers_sorted_against_baseline(
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        baseline_rank_by_visit_key=baseline_rank_by_visit_key,
        participates_by_visit_key=participates_by_visit_key,
    )

    last_buyer = buyers_sorted[-1]
    last_buyer_rank = baseline_rank_by_visit_key[last_buyer]
    trade_scope = baseline_order[:last_buyer_rank]

    buyer_set = set(buyers_sorted)
    classified_buyers, sellers_sorted, nonparticipating_visits_sorted = (
        _classify_trade_scope_visits(
            trade_scope=trade_scope,
            buyer_set=buyer_set,
            participates_by_visit_key=participates_by_visit_key,
        )
    )
    if classified_buyers != buyers_sorted:
        raise RuntimeError(
            f"Node {node_name!r}: classified buyers "
            f"{classified_buyers!r} do not match buyers_sorted "
            f"{buyers_sorted!r}."
        )

    trade_rank: dict[OrderControlTvtVisitKey, int] = {}

    for visit_key in nonparticipating_visits_sorted:
        trade_rank[visit_key] = baseline_rank_by_visit_key[visit_key]

    vacant_ranks = _build_vacant_ranks(
        last_buyer_rank=last_buyer_rank,
        nonparticipating_visits_sorted=nonparticipating_visits_sorted,
        baseline_rank_by_visit_key=baseline_rank_by_visit_key,
    )
    expected_vacant_count = len(buyers_sorted) + len(sellers_sorted)
    if len(vacant_ranks) != expected_vacant_count:
        raise RuntimeError(
            f"Node {node_name!r}: vacant rank count {len(vacant_ranks)} "
            f"does not match buyers plus sellers {expected_vacant_count}."
        )

    _assign_buyers_to_leading_vacant_ranks(
        trade_rank=trade_rank,
        buyers_sorted=buyers_sorted,
        vacant_ranks=vacant_ranks,
    )
    _assign_sellers_to_remaining_vacant_ranks(
        trade_rank=trade_rank,
        sellers_sorted=sellers_sorted,
        vacant_ranks=vacant_ranks,
        buyer_count=len(buyers_sorted),
    )
    _assign_outside_trade_scope_baseline_ranks(
        trade_rank=trade_rank,
        baseline_order=baseline_order,
        last_buyer_rank=last_buyer_rank,
        baseline_rank_by_visit_key=baseline_rank_by_visit_key,
    )

    trade_order = _build_trade_order_from_trade_rank(
        baseline_order=baseline_order,
        trade_rank=trade_rank,
    )

    _verify_general_trade_rank_state(
        baseline_order=baseline_order,
        baseline_rank_by_visit_key=baseline_rank_by_visit_key,
        buyers_sorted=buyers_sorted,
        sellers_sorted=sellers_sorted,
        nonparticipating_visits_sorted=nonparticipating_visits_sorted,
        last_buyer_rank=last_buyer_rank,
        trade_scope=trade_scope,
        trade_rank=trade_rank,
        trade_order=trade_order,
        participates_by_visit_key=participates_by_visit_key,
    )

    return OrderControlTvtMpGeneralTradeRankResult(
        concrete_buyer_candidate_set=concrete_buyer_candidate_set,
        buyers_sorted=buyers_sorted,
        sellers_sorted=sellers_sorted,
        nonparticipating_visits_sorted=nonparticipating_visits_sorted,
        last_buyer_rank=last_buyer_rank,
        trade_scope=trade_scope,
        trade_order=trade_order,
        trade_rank_by_visit_key=trade_rank,
    )


def _build_node_general_trade_rank_result(
    *,
    node_candidate_result: OrderControlTvtNodeCandidateVisitSetResult,
    node_concrete_result: OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtNodeMpGeneralTradeRankResult:
    node_name = node_candidate_result.node_name
    candidate_visits = node_candidate_result.candidate_visits
    concrete_buyer_candidate_sets = (
        node_concrete_result.concrete_buyer_candidate_sets
    )

    if len(concrete_buyer_candidate_sets) == 0:
        return _empty_node_result(
            node_name=node_name,
            build_status=node_candidate_result.build_status,
        )

    _validate_participation_for_candidate_visits(
        candidate_visits,
        participates_by_visit_key,
    )
    baseline_order, baseline_rank_by_visit_key = (
        _build_baseline_order_and_ranks(candidate_visits)
    )
    _verify_right_of_entry_visit(
        node_name=node_name,
        right_of_entry_visit_key=node_candidate_result.right_of_entry_visit_key,
        baseline_rank_by_visit_key=baseline_rank_by_visit_key,
        participates_by_visit_key=participates_by_visit_key,
    )

    candidate_trade_rank_results_list: list[
        OrderControlTvtMpGeneralTradeRankResult
    ] = []
    for concrete_buyer_candidate_set in concrete_buyer_candidate_sets:
        one_result = _build_one_general_trade_rank_result(
            node_name=node_name,
            concrete_buyer_candidate_set=concrete_buyer_candidate_set,
            baseline_order=baseline_order,
            baseline_rank_by_visit_key=baseline_rank_by_visit_key,
            participates_by_visit_key=participates_by_visit_key,
        )
        candidate_trade_rank_results_list.append(one_result)

    return OrderControlTvtNodeMpGeneralTradeRankResult(
        node_name=node_name,
        build_status=node_candidate_result.build_status,
        candidate_trade_rank_results=tuple(candidate_trade_rank_results_list),
    )


def build_tvt_mp_general_trade_ranks(
    concrete_buyer_candidate_set_result: (
        OrderControlTvtMpConcreteBuyerCandidateSetResult
    ),
    *,
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtMpGeneralTradeRankSetResult:
    """
    Build general TVT-MP trade ranks for each concrete buyer candidate.

    Walks the existing concrete-buyer-candidate Node results in stored
    order. Only ``BASELINE_INFORMATION_COMPLETE`` Nodes with at least one
    concrete buyer candidate set reconstruct ranks. Other formal statuses
    keep empty tuples. Does not modify the input result or the
    participation mapping, and does not re-run upstream candidate
    construction.
    """
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
    )

    node_trade_rank_results: list[
        OrderControlTvtNodeMpGeneralTradeRankResult
    ] = []
    node_index = 0
    while node_index < len(node_candidate_set_results):
        node_candidate_result = node_candidate_set_results[node_index]
        node_concrete_result = node_concrete_buyer_candidate_set_results[
            node_index
        ]
        _verify_node_alignment_at_index(
            node_index=node_index,
            node_candidate_result=node_candidate_result,
            node_concrete_result=node_concrete_result,
        )

        build_status = node_candidate_result.build_status
        if _build_status_is_normal_not_generated_status(build_status):
            node_trade_rank_results.append(
                _empty_node_result(
                    node_name=node_candidate_result.node_name,
                    build_status=build_status,
                )
            )
            node_index += 1
            continue

        if _build_status_requires_trade_rank_reconstruction(build_status):
            node_result = _build_node_general_trade_rank_result(
                node_candidate_result=node_candidate_result,
                node_concrete_result=node_concrete_result,
                participates_by_visit_key=participates_by_visit_key,
            )
            node_trade_rank_results.append(node_result)
            node_index += 1
            continue

        raise RuntimeError(
            f"Node {node_candidate_result.node_name!r}: unexpected "
            f"candidate visit set build status {build_status!r}."
        )

    return OrderControlTvtMpGeneralTradeRankSetResult(
        concrete_buyer_candidate_set_result=(
            concrete_buyer_candidate_set_result
        ),
        node_trade_rank_results=tuple(node_trade_rank_results),
    )
