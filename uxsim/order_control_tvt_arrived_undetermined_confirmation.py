"""
Confirm already-arrived undetermined visits after baseline fork alignment.

Uses per-Node alignment results to confirm visits whose baseline arrival
timestep is at or before baseline start T, preserving formal baseline arrival
order. Does not rerun baseline fork, alignment, or collector export.
"""

from __future__ import annotations

from dataclasses import dataclass

from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtResolvedUndeterminedVisit,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
    OrderControlTvtVisitKeyWithFormalRoute,
)


@dataclass(frozen=True)
class OrderControlTvtNodeArrivedUndeterminedConfirmationResult:
    """Per-Node result of confirming already-arrived undetermined visits."""

    node_name: str
    confirmed_arrived_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    confirm_result: OrderControlTvtConfirmResult


@dataclass(frozen=True)
class OrderControlTvtArrivedUndeterminedConfirmationResult:
    """Overall result of already-arrived undetermined-visit confirmation."""

    alignment_fork_result: OrderControlTvtBaselineForkAlignmentResult
    node_confirmation_results: tuple[
        OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
        ...
    ]


def _extract_arrived_visit_keys(
    resolved_undetermined_visits: tuple[
        OrderControlTvtResolvedUndeterminedVisit,
        ...
    ],
    baseline_timestep_T: int,
) -> tuple[OrderControlTvtVisitKey, ...]:
    arrived_visit_keys: list[OrderControlTvtVisitKey] = []
    for resolved_visit in resolved_undetermined_visits:
        if resolved_visit.baseline_arrival_timestep <= baseline_timestep_T:
            arrived_visit_keys.append(resolved_visit.visit_key)
    return tuple(arrived_visit_keys)


def _require_real_world_at_baseline_timestep(real_W: object, baseline_timestep_T: int) -> None:
    real_world_timestep = getattr(real_W, "T", None)
    if real_world_timestep != baseline_timestep_T:
        raise ValueError(
            "real_W.T must equal baseline_timestep_T before already-arrived "
            f"visits are confirmed; got real_W.T={real_world_timestep!r}, "
            f"baseline_timestep_T={baseline_timestep_T!r}."
        )


def _valid_outlink_names_at_target_node(real_W: object, node_name: str) -> frozenset[str]:
    """
    Collect every outlink name registered on the target Node in the real World.

    UXsim Nodes keep outlinks as a mapping to Link objects. Use the public
    World.get_node() lookup and walk node.outlinks.values(), not World.NODES
    indexing or iterating outlink keys alone.

    These names are the validation set for formal routes. They are not taken
    from the visits being confirmed.
    """
    get_node = getattr(real_W, "get_node", None)
    if get_node is None or not callable(get_node):
        raise ValueError(
            f"Target Node {node_name!r} cannot be resolved because real_W has no "
            "callable get_node() at baseline time T."
        )

    expected_missing_node_message = f"'{node_name}' is not Node in this World"
    try:
        target_node = get_node(node_name)
    except Exception as exc:
        if str(exc) == expected_missing_node_message:
            raise ValueError(
                f"Target Node {node_name!r} is not registered in the real World "
                "at baseline time T."
            ) from exc
        raise

    outlink_names: list[str] = []
    for outlink in target_node.outlinks.values():
        outlink_name = outlink.name
        if not isinstance(outlink_name, str) or outlink_name == "":
            raise ValueError(
                f"Target Node {node_name!r} has an outlink without a non-empty name."
            )
        outlink_names.append(outlink_name)
    return frozenset(outlink_names)


def _formal_route_pairs_from_collector(
    collector: object,
    node_name: str,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> tuple[OrderControlTvtVisitKeyWithFormalRoute, ...]:
    """
    Pair each visit with the outlink recorded when it arrived at the target Node.

    ``route_next_link_name`` is the baseline arrival route, not the vehicle's
    route at the end of the baseline and not a downstream choice.
    """
    if len(visit_keys) == 0:
        return ()

    formal_route_pairs: list[OrderControlTvtVisitKeyWithFormalRoute] = []
    for visit_key in visit_keys:
        vehicle_name, visit_id = visit_key
        snapshot = collector.get_baseline_visit_snapshot(vehicle_name, visit_id)
        if snapshot is None:
            raise ValueError(
                f"Node {node_name!r}: baseline collector has no visit snapshot "
                f"for VisitKey {visit_key!r}."
            )
        route_next_link_name = snapshot["route_next_link_name"]
        if not isinstance(route_next_link_name, str) or route_next_link_name == "":
            raise ValueError(
                f"Node {node_name!r}: VisitKey {visit_key!r} requires a non-empty "
                "route_next_link_name from the target-Node arrival record; "
                f"got {route_next_link_name!r}."
            )
        formal_route_pairs.append((visit_key, route_next_link_name))
    return tuple(formal_route_pairs)


def confirm_already_arrived_undetermined_visits(
    alignment_fork_result: OrderControlTvtBaselineForkAlignmentResult,
    *,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
    real_W: object,
) -> OrderControlTvtArrivedUndeterminedConfirmationResult:
    """
    Confirm undetermined visits that already arrived at or before baseline start T.

    Walks ``fork_result.target_node_names`` in order and extracts resolved visits
    with ``baseline_arrival_timestep <= T`` without re-sorting. Each visit is
    paired with the collector's target-Node arrival route, then ranks and formal
    routes are saved together by one atomic confirmation per Node. Raises
    ``RuntimeError`` on Node name mismatch. Does not modify the real World,
    rerun baseline fork, or rerun alignment.
    """
    fork_result = alignment_fork_result.fork_result
    baseline_timestep_T = fork_result.baseline_timestep_T
    _require_real_world_at_baseline_timestep(real_W, baseline_timestep_T)

    node_confirmation_results: list[
        OrderControlTvtNodeArrivedUndeterminedConfirmationResult
    ] = []

    for node_index, node_name in enumerate(fork_result.target_node_names):
        alignment_result = alignment_fork_result.alignment_results[node_index]

        if alignment_result.node_name != node_name:
            raise RuntimeError(
                "Node name mismatch at alignment index "
                f"{node_index}: expected target_node_names entry "
                f"{node_name!r}, but alignment result has "
                f"{alignment_result.node_name!r}."
            )

        confirmed_arrived_visit_keys = _extract_arrived_visit_keys(
            alignment_result.resolved_undetermined_visits,
            baseline_timestep_T,
        )
        formal_route_pairs = _formal_route_pairs_from_collector(
            fork_result.collector,
            node_name,
            confirmed_arrived_visit_keys,
        )
        target_node_outlink_names = _valid_outlink_names_at_target_node(
            real_W,
            node_name,
        )

        node_rank_state = rank_states_by_node_name[node_name]
        confirm_result = (
            node_rank_state.confirm_visits_and_formal_target_node_routes_atomically(
                formal_route_pairs,
                target_node_outlink_names,
            )
        )

        node_confirmation_results.append(
            OrderControlTvtNodeArrivedUndeterminedConfirmationResult(
                node_name=node_name,
                confirmed_arrived_visit_keys=confirmed_arrived_visit_keys,
                confirm_result=confirm_result,
            )
        )

    return OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment_fork_result,
        node_confirmation_results=tuple(node_confirmation_results),
    )
