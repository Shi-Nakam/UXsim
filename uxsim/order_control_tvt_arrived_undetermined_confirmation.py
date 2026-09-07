"""
Confirm already-arrived undetermined visits after baseline fork alignment.

Uses per-Node alignment results to confirm visits whose baseline arrival
timestep is at or before baseline start T, preserving formal baseline arrival
order. Does not rerun baseline fork, alignment, or collector export.
"""

from __future__ import annotations

from collections.abc import Mapping
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


def confirm_already_arrived_undetermined_visits(
    alignment_fork_result: OrderControlTvtBaselineForkAlignmentResult,
    *,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
) -> OrderControlTvtArrivedUndeterminedConfirmationResult:
    """
    Confirm undetermined visits that already arrived at or before baseline start T.

    Walks ``fork_result.target_node_names`` in order, extracts resolved visits
    with ``baseline_arrival_timestep <= T`` without re-sorting, and calls
    ``confirm_visits_in_order`` once per Node. Raises ``RuntimeError`` on Node
    name mismatch. Does not modify World state, rerun baseline fork, or rerun
    alignment.
    """
    fork_result = alignment_fork_result.fork_result
    baseline_timestep_T = fork_result.baseline_timestep_T

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

        node_rank_state = rank_states_by_node_name[node_name]
        confirm_result = node_rank_state.confirm_visits_in_order(
            confirmed_arrived_visit_keys
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
