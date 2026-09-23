"""
Build one candidate's read-only local binding rank sequence.

This stage only organizes which visits must pass the target Node, in which
order, and on which outlink. It does not move vehicles, write the rank
ledger, or run the candidate-specific virtual calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtMpFifoInspectionSetResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)


class OrderControlTvtMpLocalBindingPartition(Enum):
    """Which confirmed range a binding visit came from. Not a route class."""

    CONFIRMED_BEFORE_THIS_BASELINE = "confirmed_before_this_baseline"
    PRECONFIRMED_BY_THIS_BASELINE = "preconfirmed_by_this_baseline"
    TRADE_SCOPE_OF_THIS_CANDIDATE = "trade_scope_of_this_candidate"
    OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED = "outside_trade_scope_inside_k_fixed"


class OrderControlTvtMpLocalBindingRouteOrigin(Enum):
    """Where the outlink used for local passage was read from."""

    RANK_LEDGER_FORMAL_ROUTE = "rank_ledger_formal_route"
    SNAPSHOT_ROUTE_ALREADY_DECIDED = "snapshot_route_already_decided"
    BASELINE_TARGET_NODE_ARRIVAL_ROUTE = "baseline_target_node_arrival_route"


class OrderControlTvtMpLocalBindingTradeRole(Enum):
    """Role of a binding visit toward this candidate. Not a time-value sign."""

    BUYER = "buyer"
    SELLER = "seller"
    NONPARTICIPATING = "nonparticipating"
    OUTSIDE_TRADE_SCOPE = "outside_trade_scope"


@dataclass(frozen=True)
class OrderControlTvtMpLocalBindingRankVisit:
    """One visit in the completed local binding order."""

    visit_key: OrderControlTvtVisitKey
    vehicle_id: int
    binding_partition: OrderControlTvtMpLocalBindingPartition
    binding_rank: int
    route_next_link_name: str
    route_origin: OrderControlTvtMpLocalBindingRouteOrigin
    inlink_name: str
    baseline_arrival_timestep: int
    arrival_tiebreaker: int | float
    trade_role: OrderControlTvtMpLocalBindingTradeRole


@dataclass(frozen=True)
class OrderControlTvtMpLocalBindingRankSequence:
    """Read-only binding order for one FIFO-passed concrete buyer candidate."""

    node_name: str
    baseline_timestep_T: int
    concrete_buyer_candidate_set: OrderControlTvtMpConcreteBuyerCandidateSet
    confirmed_before_this_baseline_visits: tuple[
        OrderControlTvtMpLocalBindingRankVisit,
        ...,
    ]
    preconfirmed_by_this_baseline_visits: tuple[
        OrderControlTvtMpLocalBindingRankVisit,
        ...,
    ]
    trade_scope_of_this_candidate_visits: tuple[
        OrderControlTvtMpLocalBindingRankVisit,
        ...,
    ]
    outside_trade_scope_inside_k_fixed_visits: tuple[
        OrderControlTvtMpLocalBindingRankVisit,
        ...,
    ]
    visits_in_binding_order: tuple[OrderControlTvtMpLocalBindingRankVisit, ...]
    k_last_buyer: int
    k_decision_window: int
    k_fixed: int


def _require_fork_baseline_timestep_T(
    baseline_timestep_T: object,
    *,
    node_name: str,
) -> int:
    """Baseline start timestep T from the upstream fork result, not a visit arrival."""
    if type(baseline_timestep_T) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: fork_result.baseline_timestep_T must be a "
            f"Python int, not bool; got type {type(baseline_timestep_T).__name__} "
            f"with value {baseline_timestep_T!r}."
        )
    if baseline_timestep_T < 0:
        raise RuntimeError(
            f"Node {node_name!r}: fork_result.baseline_timestep_T must be >= 0; "
            f"got {baseline_timestep_T!r}."
        )
    return baseline_timestep_T


def _require_fifo_passed_candidate(
    candidate_fifo_inspection_result: object,
) -> OrderControlTvtMpCandidateFifoInspectionResult:
    if not isinstance(
        candidate_fifo_inspection_result,
        OrderControlTvtMpCandidateFifoInspectionResult,
    ):
        raise ValueError(
            "candidate_fifo_inspection_result must be "
            "OrderControlTvtMpCandidateFifoInspectionResult; got "
            f"type {type(candidate_fifo_inspection_result).__name__}."
        )
    if candidate_fifo_inspection_result.preserves_inlink_fifo is not True:
        raise ValueError(
            "local binding rank sequence is built only for a FIFO-passed "
            "candidate; preserves_inlink_fifo is not True."
        )
    return candidate_fifo_inspection_result


def _locate_candidate_node_index(
    fifo_inspection_set_result: OrderControlTvtMpFifoInspectionSetResult,
    candidate_fifo_inspection_result: OrderControlTvtMpCandidateFifoInspectionResult,
) -> tuple[int, str]:
    for node_index, node_result in enumerate(
        fifo_inspection_set_result.node_fifo_inspection_results
    ):
        for stored_candidate in node_result.candidate_fifo_inspection_results:
            if stored_candidate is candidate_fifo_inspection_result:
                return node_index, node_result.node_name
    raise ValueError(
        "candidate_fifo_inspection_result is not one of the candidates "
        "stored on fifo_inspection_set_result."
    )


def _node_name_at(results: tuple, node_index: int, source_label: str) -> str:
    if node_index >= len(results):
        raise RuntimeError(
            f"{source_label} has no result at node index {node_index}."
        )
    node_name = results[node_index].node_name
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"{source_label} node index {node_index} has no node_name."
        )
    return node_name


def _require_same_node_name(
    expected_node_name: str,
    actual_node_name: str,
    source_label: str,
) -> None:
    if actual_node_name != expected_node_name:
        raise RuntimeError(
            f"Node name mismatch while building the binding sequence: "
            f"FIFO node is {expected_node_name!r}, but {source_label} has "
            f"{actual_node_name!r}."
        )


def _read_collector_snapshot(
    collector: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> dict | None:
    vehicle_name, visit_id = visit_key
    snapshot = collector.get_baseline_visit_snapshot(vehicle_name, visit_id)
    if snapshot is None:
        return None
    if not isinstance(snapshot, dict):
        raise ValueError(
            f"Node {node_name!r}: collector snapshot for VisitKey {visit_key!r} "
            f"must be a dict; got type {type(snapshot).__name__}."
        )
    record_node_name = snapshot.get("node_name")
    if record_node_name != node_name:
        raise ValueError(
            f"Node {node_name!r}: collector snapshot for VisitKey {visit_key!r} "
            f"belongs to node {record_node_name!r}."
        )
    return snapshot


def _require_snapshot_text(snapshot: dict, field_name: str, visit_key: OrderControlTvtVisitKey) -> str:
    value = snapshot.get(field_name)
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"VisitKey {visit_key!r}: collector field {field_name} must be a "
            f"non-empty str; got {value!r}."
        )
    return value


def _require_snapshot_int(snapshot: dict, field_name: str, visit_key: OrderControlTvtVisitKey) -> int:
    value = snapshot.get(field_name)
    if type(value) is not int:
        raise ValueError(
            f"VisitKey {visit_key!r}: collector field {field_name} must be a "
            f"Python int; got {value!r}."
        )
    return value


def _snapshot_route_already_decided(snapshot: dict) -> bool:
    route_next_link_name = snapshot.get("route_next_link_name")
    return (
        snapshot.get("was_arrived_at_snapshot") is True
        and isinstance(route_next_link_name, str)
        and route_next_link_name != ""
    )


def _binding_visit_from_snapshot(
    *,
    visit_key: OrderControlTvtVisitKey,
    snapshot: dict,
    binding_partition: OrderControlTvtMpLocalBindingPartition,
    route_next_link_name: str,
    route_origin: OrderControlTvtMpLocalBindingRouteOrigin,
    trade_role: OrderControlTvtMpLocalBindingTradeRole,
) -> OrderControlTvtMpLocalBindingRankVisit:
    arrival_tiebreaker = snapshot.get("arrival_tiebreaker")
    if not isinstance(arrival_tiebreaker, (int, float)) or isinstance(arrival_tiebreaker, bool):
        raise ValueError(
            f"VisitKey {visit_key!r}: collector arrival_tiebreaker must be a "
            f"number; got {arrival_tiebreaker!r}."
        )
    return OrderControlTvtMpLocalBindingRankVisit(
        visit_key=visit_key,
        vehicle_id=_require_snapshot_int(snapshot, "vehicle_id", visit_key),
        binding_partition=binding_partition,
        binding_rank=0,
        route_next_link_name=route_next_link_name,
        route_origin=route_origin,
        inlink_name=_require_snapshot_text(snapshot, "inlink_name", visit_key),
        baseline_arrival_timestep=_require_snapshot_int(
            snapshot,
            "baseline_arrival_timestep",
            visit_key,
        ),
        arrival_tiebreaker=arrival_tiebreaker,
        trade_role=trade_role,
    )


def _partition_1_visits(
    *,
    node_name: str,
    rank_state: OrderControlTvtNodeRankState,
    collector: object,
    k_confirmed_before: int,
) -> tuple[OrderControlTvtMpLocalBindingRankVisit, ...]:
    """
    Visits confirmed before this baseline that are still in the snapshot scope.

    ``k_confirmed_before`` is a 1-based count, so the ledger prefix length is
    that same integer. Collector records exist only for vehicles still on an
    inlink or in incoming vehicles at time T.
    """
    confirmed_visit_keys = rank_state.confirmed_visit_keys_in_order()
    if k_confirmed_before < 0 or k_confirmed_before > len(confirmed_visit_keys):
        raise RuntimeError(
            f"Node {node_name!r}: k_confirmed_before {k_confirmed_before} is "
            "outside the confirmed rank ledger."
        )
    visits: list[OrderControlTvtMpLocalBindingRankVisit] = []
    for ledger_position, visit_key in enumerate(
        confirmed_visit_keys[:k_confirmed_before],
        start=1,
    ):
        assigned_rank = rank_state.assigned_rank(visit_key)
        if assigned_rank != ledger_position:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is at ledger "
                f"position {ledger_position} but assigned_rank is {assigned_rank!r}."
            )
        snapshot = _read_collector_snapshot(collector, node_name, visit_key)
        if snapshot is None:
            continue
        if _snapshot_route_already_decided(snapshot):
            route_next_link_name = _require_snapshot_text(
                snapshot,
                "route_next_link_name",
                visit_key,
            )
            route_origin = (
                OrderControlTvtMpLocalBindingRouteOrigin.SNAPSHOT_ROUTE_ALREADY_DECIDED
            )
        else:
            route_next_link_name = rank_state.formal_route_next_link_name(visit_key)
            if not isinstance(route_next_link_name, str) or route_next_link_name == "":
                raise RuntimeError(
                    f"Node {node_name!r}: partition confirmed_before_this_baseline "
                    f"VisitKey {visit_key!r} has no snapshot route and no formal "
                    "route on the rank ledger."
                )
            route_origin = (
                OrderControlTvtMpLocalBindingRouteOrigin.RANK_LEDGER_FORMAL_ROUTE
            )
        visits.append(
            _binding_visit_from_snapshot(
                visit_key=visit_key,
                snapshot=snapshot,
                binding_partition=(
                    OrderControlTvtMpLocalBindingPartition.CONFIRMED_BEFORE_THIS_BASELINE
                ),
                route_next_link_name=route_next_link_name,
                route_origin=route_origin,
                trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
            )
        )
    return tuple(visits)


def _partition_2_visits(
    *,
    node_name: str,
    rank_state: OrderControlTvtNodeRankState,
    collector: object,
    confirmed_arrived_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_nonparticipating_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> tuple[OrderControlTvtMpLocalBindingRankVisit, ...]:
    """Already-arrived visits, then the leading non-participating prefix."""
    visit_keys = (
        confirmed_arrived_visit_keys
        + confirmed_leading_nonparticipating_visit_keys
    )
    visits: list[OrderControlTvtMpLocalBindingRankVisit] = []
    for visit_key in visit_keys:
        formal_route_next_link_name = rank_state.formal_route_next_link_name(visit_key)
        if (
            not isinstance(formal_route_next_link_name, str)
            or formal_route_next_link_name == ""
        ):
            raise ValueError(
                f"Node {node_name!r}: preconfirmed VisitKey {visit_key!r} has no "
                "formal_route_next_link_name on the rank ledger."
            )
        snapshot = _read_collector_snapshot(collector, node_name, visit_key)
        if snapshot is None:
            raise ValueError(
                f"Node {node_name!r}: preconfirmed VisitKey {visit_key!r} has no "
                "baseline collector snapshot."
            )
        visits.append(
            _binding_visit_from_snapshot(
                visit_key=visit_key,
                snapshot=snapshot,
                binding_partition=(
                    OrderControlTvtMpLocalBindingPartition.PRECONFIRMED_BY_THIS_BASELINE
                ),
                route_next_link_name=formal_route_next_link_name,
                route_origin=(
                    OrderControlTvtMpLocalBindingRouteOrigin.RANK_LEDGER_FORMAL_ROUTE
                ),
                trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
            )
        )
    return tuple(visits)


def _trade_role_for_scope_visit(
    visit_key: OrderControlTvtVisitKey,
    trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
) -> OrderControlTvtMpLocalBindingTradeRole:
    buyer_count = 1 if visit_key in trade_rank_result.buyers_sorted else 0
    seller_count = 1 if visit_key in trade_rank_result.sellers_sorted else 0
    nonparticipating_count = (
        1 if visit_key in trade_rank_result.nonparticipating_visits_sorted else 0
    )
    role_count = buyer_count + seller_count + nonparticipating_count
    if role_count != 1:
        raise RuntimeError(
            f"VisitKey {visit_key!r} must belong to exactly one of buyer, "
            "seller, or nonparticipating inside the trade scope; "
            f"matched {role_count} roles."
        )
    if buyer_count == 1:
        return OrderControlTvtMpLocalBindingTradeRole.BUYER
    if seller_count == 1:
        return OrderControlTvtMpLocalBindingTradeRole.SELLER
    return OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING


def _route_for_unconfirmed_binding_visit(
    *,
    node_name: str,
    collector: object,
    visit_key: OrderControlTvtVisitKey,
) -> tuple[dict, str, OrderControlTvtMpLocalBindingRouteOrigin]:
    snapshot = _read_collector_snapshot(collector, node_name, visit_key)
    if snapshot is None:
        raise ValueError(
            f"Node {node_name!r}: binding VisitKey {visit_key!r} has no "
            "baseline collector snapshot."
        )
    if _snapshot_route_already_decided(snapshot):
        return (
            snapshot,
            _require_snapshot_text(snapshot, "route_next_link_name", visit_key),
            OrderControlTvtMpLocalBindingRouteOrigin.SNAPSHOT_ROUTE_ALREADY_DECIDED,
        )
    route_next_link_name = snapshot.get("route_next_link_name")
    if not isinstance(route_next_link_name, str) or route_next_link_name == "":
        raise ValueError(
            f"Node {node_name!r}: binding VisitKey {visit_key!r} has no "
            "target-Node route from the snapshot or the baseline arrival."
        )
    return (
        snapshot,
        route_next_link_name,
        OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE,
    )


def _require_non_negative_python_int(
    value: object,
    *,
    node_name: str,
    field_name: str,
) -> int:
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a Python int, not bool; "
            f"got type {type(value).__name__} with value {value!r}."
        )
    if value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be >= 0; got {value!r}."
        )
    return value


def _verify_confirm_result_matches_visit_keys(
    *,
    node_name: str,
    source_label: str,
    confirm_result: OrderControlTvtConfirmResult,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    """Check one confirmation stage's counts against the visit column it claims."""
    k_confirmed_before = _require_non_negative_python_int(
        confirm_result.k_confirmed_before,
        node_name=node_name,
        field_name=f"{source_label}.k_confirmed_before",
    )
    k_confirmed_after = _require_non_negative_python_int(
        confirm_result.k_confirmed_after,
        node_name=node_name,
        field_name=f"{source_label}.k_confirmed_after",
    )
    newly_confirmed_count = _require_non_negative_python_int(
        confirm_result.newly_confirmed_count,
        node_name=node_name,
        field_name=f"{source_label}.newly_confirmed_count",
    )
    expected_count = len(visit_keys)
    if newly_confirmed_count != expected_count:
        raise RuntimeError(
            f"Node {node_name!r}: {source_label}.newly_confirmed_count "
            f"{newly_confirmed_count} does not equal the visit column length "
            f"{expected_count}."
        )
    expected_after = k_confirmed_before + newly_confirmed_count
    if k_confirmed_after != expected_after:
        raise RuntimeError(
            f"Node {node_name!r}: {source_label}.k_confirmed_after "
            f"{k_confirmed_after} does not equal k_confirmed_before + "
            f"newly_confirmed_count ({expected_after})."
        )


def _verify_partition_2_matches_rank_ledger(
    *,
    node_name: str,
    rank_state: OrderControlTvtNodeRankState,
    arrived_confirm_result: OrderControlTvtConfirmResult,
    leading_confirm_result: OrderControlTvtConfirmResult,
    confirmed_arrived_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_nonparticipating_visit_keys: tuple[
        OrderControlTvtVisitKey,
        ...,
    ],
) -> None:
    """
    Require the two preconfirmation stages and the rank ledger to be one path.

    Ranks are 1-based. The slices below are 0-based Python indexes:
    ``ledger[k_confirmed_before:k_confirmed_after]``.
    """
    _verify_confirm_result_matches_visit_keys(
        node_name=node_name,
        source_label="already-arrived confirmation",
        confirm_result=arrived_confirm_result,
        visit_keys=confirmed_arrived_visit_keys,
    )
    _verify_confirm_result_matches_visit_keys(
        node_name=node_name,
        source_label="leading non-participating confirmation",
        confirm_result=leading_confirm_result,
        visit_keys=confirmed_leading_nonparticipating_visit_keys,
    )
    if (
        leading_confirm_result.k_confirmed_before
        != arrived_confirm_result.k_confirmed_after
    ):
        raise RuntimeError(
            f"Node {node_name!r}: leading confirmation does not continue "
            "from the already-arrived confirmation end; "
            "leading.k_confirmed_before="
            f"{leading_confirm_result.k_confirmed_before!r}, "
            "arrived.k_confirmed_after="
            f"{arrived_confirm_result.k_confirmed_after!r}."
        )

    ledger_confirmed_visit_keys = rank_state.confirmed_visit_keys_in_order()
    if len(ledger_confirmed_visit_keys) < leading_confirm_result.k_confirmed_after:
        raise RuntimeError(
            f"Node {node_name!r}: rank ledger length "
            f"{len(ledger_confirmed_visit_keys)} is shorter than "
            "leading.k_confirmed_after "
            f"{leading_confirm_result.k_confirmed_after}."
        )

    # 0-based slices. The rank number of ledger[index] is index + 1.
    arrived_start_index = arrived_confirm_result.k_confirmed_before
    arrived_end_index = arrived_confirm_result.k_confirmed_after
    leading_start_index = leading_confirm_result.k_confirmed_before
    leading_end_index = leading_confirm_result.k_confirmed_after
    actual_arrived_visit_keys = ledger_confirmed_visit_keys[
        arrived_start_index:arrived_end_index
    ]
    if actual_arrived_visit_keys != confirmed_arrived_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: rank ledger slice "
            f"[{arrived_start_index}:{arrived_end_index}] is "
            f"{actual_arrived_visit_keys!r}, but confirmed_arrived_visit_keys "
            f"is {confirmed_arrived_visit_keys!r}."
        )
    actual_leading_visit_keys = ledger_confirmed_visit_keys[
        leading_start_index:leading_end_index
    ]
    if actual_leading_visit_keys != confirmed_leading_nonparticipating_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: rank ledger slice "
            f"[{leading_start_index}:{leading_end_index}] is "
            f"{actual_leading_visit_keys!r}, but "
            "confirmed_leading_nonparticipating_visit_keys is "
            f"{confirmed_leading_nonparticipating_visit_keys!r}."
        )

    for ledger_index, visit_key in enumerate(
        ledger_confirmed_visit_keys[:leading_end_index]
    ):
        expected_assigned_rank = ledger_index + 1
        actual_assigned_rank = rank_state.assigned_rank(visit_key)
        if actual_assigned_rank != expected_assigned_rank:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is at 0-based "
                f"ledger index {ledger_index}, so assigned_rank must be "
                f"{expected_assigned_rank}; got {actual_assigned_rank!r}."
            )


def _verify_decision_window_decomposition(
    *,
    node_name: str,
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_nonparticipating_visit_keys: tuple[
        OrderControlTvtVisitKey,
        ...,
    ],
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    """The full window is the removed leading prefix plus the remaining suffix."""
    expected_decision_window_visit_keys = (
        confirmed_leading_nonparticipating_visit_keys
        + remaining_decision_window_visit_keys
    )
    if decision_window_visit_keys != expected_decision_window_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: decision_window_visit_keys "
            f"{decision_window_visit_keys!r} is not the leading prefix "
            f"{confirmed_leading_nonparticipating_visit_keys!r} plus the "
            f"remaining suffix {remaining_decision_window_visit_keys!r}."
        )


def _visit_key_set_without_hiding_duplicates(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
    *,
    node_name: str,
    column_name: str,
) -> set[OrderControlTvtVisitKey]:
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    for visit_key in visit_keys:
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: duplicate VisitKey {visit_key!r} in "
                f"{column_name}."
            )
        seen_visit_keys.add(visit_key)
    return seen_visit_keys


def _verify_trade_scope_matches_trade_order_prefix(
    *,
    node_name: str,
    trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
) -> int:
    """
    Partition 3 uses post-trade order, but the visit set must match trade_scope.

    ``last_buyer_rank`` is a 1-based count. ``trade_order[:last_buyer_rank]``
    is the 0-based prefix of that length. Order is not required to match
    ``trade_scope``.
    """
    last_buyer_rank = trade_rank_result.last_buyer_rank
    trade_order = trade_rank_result.trade_order
    trade_scope = trade_rank_result.trade_scope
    if type(last_buyer_rank) is not int or last_buyer_rank < 1:
        raise ValueError(
            f"Node {node_name!r}: last_buyer_rank must be an int >= 1; "
            f"got {last_buyer_rank!r}."
        )
    if last_buyer_rank > len(trade_order):
        raise ValueError(
            f"Node {node_name!r}: last_buyer_rank {last_buyer_rank} is longer "
            f"than trade_order ({len(trade_order)})."
        )
    if len(trade_scope) != last_buyer_rank:
        raise RuntimeError(
            f"Node {node_name!r}: trade_scope length {len(trade_scope)} does "
            f"not equal last_buyer_rank {last_buyer_rank}."
        )
    trade_order_prefix = trade_order[:last_buyer_rank]
    trade_scope_visit_keys = _visit_key_set_without_hiding_duplicates(
        trade_scope,
        node_name=node_name,
        column_name="trade_scope",
    )
    trade_order_prefix_visit_keys = _visit_key_set_without_hiding_duplicates(
        trade_order_prefix,
        node_name=node_name,
        column_name="trade_order[:last_buyer_rank]",
    )
    if trade_scope_visit_keys != trade_order_prefix_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: trade_scope VisitKeys "
            f"{trade_scope!r} do not match trade_order prefix "
            f"{trade_order_prefix!r}."
        )
    return last_buyer_rank


def _partition_3_visits(
    *,
    node_name: str,
    collector: object,
    trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
) -> tuple[OrderControlTvtMpLocalBindingRankVisit, ...]:
    """
    Post-trade order through the last buyer.

    ``last_buyer_rank`` is a 1-based count, so the Python slice end index is
    that same integer.
    """
    last_buyer_rank = _verify_trade_scope_matches_trade_order_prefix(
        node_name=node_name,
        trade_rank_result=trade_rank_result,
    )
    visits: list[OrderControlTvtMpLocalBindingRankVisit] = []
    for visit_key in trade_rank_result.trade_order[:last_buyer_rank]:
        snapshot, route_next_link_name, route_origin = (
            _route_for_unconfirmed_binding_visit(
                node_name=node_name,
                collector=collector,
                visit_key=visit_key,
            )
        )
        visits.append(
            _binding_visit_from_snapshot(
                visit_key=visit_key,
                snapshot=snapshot,
                binding_partition=(
                    OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
                ),
                route_next_link_name=route_next_link_name,
                route_origin=route_origin,
                trade_role=_trade_role_for_scope_visit(visit_key, trade_rank_result),
            )
        )
    return tuple(visits)


def _partition_4_visits(
    *,
    node_name: str,
    collector: object,
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    k_last_buyer: int,
) -> tuple[OrderControlTvtMpLocalBindingRankVisit, ...]:
    """
    Baseline-order suffix after the last buyer.

    Ranks are 1-based. ``remaining_decision_window_visit_keys[0]`` is rank 1,
    so dropping the first ``k_last_buyer`` visits starts at Python index
    ``k_last_buyer``.
    """
    k_decision_window = len(remaining_decision_window_visit_keys)
    if k_last_buyer >= k_decision_window:
        return ()
    visits: list[OrderControlTvtMpLocalBindingRankVisit] = []
    for visit_key in remaining_decision_window_visit_keys[k_last_buyer:]:
        snapshot, route_next_link_name, route_origin = (
            _route_for_unconfirmed_binding_visit(
                node_name=node_name,
                collector=collector,
                visit_key=visit_key,
            )
        )
        visits.append(
            _binding_visit_from_snapshot(
                visit_key=visit_key,
                snapshot=snapshot,
                binding_partition=(
                    OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED
                ),
                route_next_link_name=route_next_link_name,
                route_origin=route_origin,
                trade_role=OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE,
            )
        )
    return tuple(visits)


def _assign_binding_ranks(
    partition_visits: tuple[tuple[OrderControlTvtMpLocalBindingRankVisit, ...], ...],
) -> tuple[OrderControlTvtMpLocalBindingRankVisit, ...]:
    completed_visits: list[OrderControlTvtMpLocalBindingRankVisit] = []
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    next_binding_rank = 1
    for visits in partition_visits:
        for visit in visits:
            if visit.visit_key in seen_visit_keys:
                raise RuntimeError(
                    "Duplicate VisitKey "
                    f"{visit.visit_key!r} inside or across binding partitions."
                )
            seen_visit_keys.add(visit.visit_key)
            completed_visits.append(
                OrderControlTvtMpLocalBindingRankVisit(
                    visit_key=visit.visit_key,
                    vehicle_id=visit.vehicle_id,
                    binding_partition=visit.binding_partition,
                    binding_rank=next_binding_rank,
                    route_next_link_name=visit.route_next_link_name,
                    route_origin=visit.route_origin,
                    inlink_name=visit.inlink_name,
                    baseline_arrival_timestep=visit.baseline_arrival_timestep,
                    arrival_tiebreaker=visit.arrival_tiebreaker,
                    trade_role=visit.trade_role,
                )
            )
            next_binding_rank += 1
    return tuple(completed_visits)


def _split_completed_visits(
    visits_in_binding_order: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
) -> tuple[
    tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
]:
    confirmed_before: list[OrderControlTvtMpLocalBindingRankVisit] = []
    preconfirmed: list[OrderControlTvtMpLocalBindingRankVisit] = []
    trade_scope: list[OrderControlTvtMpLocalBindingRankVisit] = []
    outside_trade_scope: list[OrderControlTvtMpLocalBindingRankVisit] = []
    for visit in visits_in_binding_order:
        if (
            visit.binding_partition
            is OrderControlTvtMpLocalBindingPartition.CONFIRMED_BEFORE_THIS_BASELINE
        ):
            confirmed_before.append(visit)
        elif (
            visit.binding_partition
            is OrderControlTvtMpLocalBindingPartition.PRECONFIRMED_BY_THIS_BASELINE
        ):
            preconfirmed.append(visit)
        elif (
            visit.binding_partition
            is OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ):
            trade_scope.append(visit)
        elif (
            visit.binding_partition
            is OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED
        ):
            outside_trade_scope.append(visit)
        else:
            raise RuntimeError(
                f"Unknown binding partition {visit.binding_partition!r}."
            )
    return (
        tuple(confirmed_before),
        tuple(preconfirmed),
        tuple(trade_scope),
        tuple(outside_trade_scope),
    )


def build_tvt_mp_local_binding_rank_sequence(
    fifo_inspection_set_result: OrderControlTvtMpFifoInspectionSetResult,
    candidate_fifo_inspection_result: OrderControlTvtMpCandidateFifoInspectionResult,
    rank_state: OrderControlTvtNodeRankState,
) -> OrderControlTvtMpLocalBindingRankSequence:
    """
    Build the read-only binding order for one FIFO-passed candidate.

    The candidate is located by object identity inside
    ``fifo_inspection_set_result``. From that node index the function reads
    the general trade-rank result, the candidate-visit chain, the leading
    non-participating confirmation, the already-arrived confirmation, and
    ``fork_result.collector``. It does not receive those objects again as
    separate arguments.

    ``k_last_buyer`` is the existing ``last_buyer_rank``. Partition 3 uses
    ``trade_order[:k_last_buyer]``. Partition 4 uses
    ``remaining_decision_window_visit_keys[k_last_buyer:]`` when that count
    is smaller than the decision window.
    """
    if not isinstance(fifo_inspection_set_result, OrderControlTvtMpFifoInspectionSetResult):
        raise ValueError(
            "fifo_inspection_set_result must be "
            "OrderControlTvtMpFifoInspectionSetResult; got "
            f"type {type(fifo_inspection_set_result).__name__}."
        )
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise ValueError(
            "rank_state must be OrderControlTvtNodeRankState; got "
            f"type {type(rank_state).__name__}."
        )
    candidate = _require_fifo_passed_candidate(candidate_fifo_inspection_result)
    node_index, node_name = _locate_candidate_node_index(
        fifo_inspection_set_result,
        candidate,
    )
    if rank_state.node_name != node_name:
        raise ValueError(
            f"rank_state.node_name {rank_state.node_name!r} does not match "
            f"candidate node {node_name!r}."
        )

    general_trade_rank_set_result = (
        fifo_inspection_set_result.general_trade_rank_set_result
    )
    trade_rank_node_name = _node_name_at(
        general_trade_rank_set_result.node_trade_rank_results,
        node_index,
        "general trade-rank result",
    )
    _require_same_node_name(node_name, trade_rank_node_name, "general trade-rank result")
    trade_rank_node_result = general_trade_rank_set_result.node_trade_rank_results[
        node_index
    ]
    if candidate.general_trade_rank_result not in (
        trade_rank_node_result.candidate_trade_rank_results
    ):
        raise RuntimeError(
            f"Node {node_name!r}: FIFO candidate is not stored on the "
            "general trade-rank node result."
        )
    trade_rank_result = candidate.general_trade_rank_result

    concrete_set_result = (
        general_trade_rank_set_result.concrete_buyer_candidate_set_result
    )
    inlink_result = concrete_set_result.inlink_candidate_physical_order_result
    candidate_visit_set_result = inlink_result.candidate_visit_set_result
    right_of_entry_result = candidate_visit_set_result.right_of_entry_selection_result
    leading_result = right_of_entry_result.leading_confirmation_result
    arrived_result = leading_result.arrived_confirmation_result
    fork_result = arrived_result.alignment_fork_result.fork_result
    baseline_timestep_T = _require_fork_baseline_timestep_T(
        fork_result.baseline_timestep_T,
        node_name=node_name,
    )
    if node_index >= len(fork_result.target_node_names):
        raise RuntimeError(
            f"fork_result.target_node_names has no entry at index {node_index}."
        )
    _require_same_node_name(
        node_name,
        fork_result.target_node_names[node_index],
        "fork_result.target_node_names",
    )
    leading_node_name = _node_name_at(
        leading_result.node_confirmation_results,
        node_index,
        "leading non-participating confirmation",
    )
    _require_same_node_name(
        node_name,
        leading_node_name,
        "leading non-participating confirmation",
    )
    arrived_node_name = _node_name_at(
        arrived_result.node_confirmation_results,
        node_index,
        "already-arrived confirmation",
    )
    _require_same_node_name(
        node_name,
        arrived_node_name,
        "already-arrived confirmation",
    )

    arrived_node_result = arrived_result.node_confirmation_results[node_index]
    leading_node_result = leading_result.node_confirmation_results[node_index]
    confirmed_arrived_visit_keys = arrived_node_result.confirmed_arrived_visit_keys
    confirmed_leading_nonparticipating_visit_keys = (
        leading_node_result.confirmed_leading_nonparticipating_visit_keys
    )
    remaining_decision_window_visit_keys = (
        leading_node_result.remaining_decision_window_visit_keys
    )
    _verify_partition_2_matches_rank_ledger(
        node_name=node_name,
        rank_state=rank_state,
        arrived_confirm_result=arrived_node_result.confirm_result,
        leading_confirm_result=leading_node_result.confirm_result,
        confirmed_arrived_visit_keys=confirmed_arrived_visit_keys,
        confirmed_leading_nonparticipating_visit_keys=(
            confirmed_leading_nonparticipating_visit_keys
        ),
    )
    _verify_decision_window_decomposition(
        node_name=node_name,
        decision_window_visit_keys=leading_node_result.decision_window_visit_keys,
        confirmed_leading_nonparticipating_visit_keys=(
            confirmed_leading_nonparticipating_visit_keys
        ),
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
    )
    _verify_trade_scope_matches_trade_order_prefix(
        node_name=node_name,
        trade_rank_result=trade_rank_result,
    )
    k_confirmed_before = arrived_node_result.confirm_result.k_confirmed_before

    collector = fork_result.collector
    confirmed_before_visits = _partition_1_visits(
        node_name=node_name,
        rank_state=rank_state,
        collector=collector,
        k_confirmed_before=k_confirmed_before,
    )
    preconfirmed_visits = _partition_2_visits(
        node_name=node_name,
        rank_state=rank_state,
        collector=collector,
        confirmed_arrived_visit_keys=confirmed_arrived_visit_keys,
        confirmed_leading_nonparticipating_visit_keys=(
            confirmed_leading_nonparticipating_visit_keys
        ),
    )
    trade_scope_visits = _partition_3_visits(
        node_name=node_name,
        collector=collector,
        trade_rank_result=trade_rank_result,
    )
    k_last_buyer = trade_rank_result.last_buyer_rank
    k_decision_window = len(remaining_decision_window_visit_keys)
    k_fixed = max(k_last_buyer, k_decision_window)
    outside_trade_scope_visits = _partition_4_visits(
        node_name=node_name,
        collector=collector,
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
        k_last_buyer=k_last_buyer,
    )
    visits_in_binding_order = _assign_binding_ranks(
        (
            confirmed_before_visits,
            preconfirmed_visits,
            trade_scope_visits,
            outside_trade_scope_visits,
        )
    )
    (
        confirmed_before_visits,
        preconfirmed_visits,
        trade_scope_visits,
        outside_trade_scope_visits,
    ) = _split_completed_visits(visits_in_binding_order)
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=baseline_timestep_T,
        concrete_buyer_candidate_set=trade_rank_result.concrete_buyer_candidate_set,
        confirmed_before_this_baseline_visits=confirmed_before_visits,
        preconfirmed_by_this_baseline_visits=preconfirmed_visits,
        trade_scope_of_this_candidate_visits=trade_scope_visits,
        outside_trade_scope_inside_k_fixed_visits=outside_trade_scope_visits,
        visits_in_binding_order=visits_in_binding_order,
        k_last_buyer=k_last_buyer,
        k_decision_window=k_decision_window,
        k_fixed=k_fixed,
    )
