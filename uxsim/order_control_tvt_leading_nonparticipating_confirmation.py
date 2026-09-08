"""
Confirm leading non-participating visits in the decision window after arrived visits.

Uses arrived-visit confirmation results to confirm the leading prefix of
non-participating visits in the formal baseline order within the decision window.
Does not rerun baseline fork, alignment, arrived confirmation, or collector export.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
)
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtResolvedUndeterminedVisit,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)

_DECISION_WINDOW_MIN_HORIZON_STEPS = 6


@dataclass(frozen=True)
class OrderControlTvtNodeLeadingNonparticipatingConfirmationResult:
    """Per-Node result of leading non-participating decision-window confirmation."""

    node_name: str
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    confirmed_leading_nonparticipating_visit_keys: tuple[
        OrderControlTvtVisitKey,
        ...
    ]
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    confirm_result: OrderControlTvtConfirmResult


@dataclass(frozen=True)
class OrderControlTvtLeadingNonparticipatingConfirmationResult:
    """Overall result of leading non-participating decision-window confirmation."""

    arrived_confirmation_result: OrderControlTvtArrivedUndeterminedConfirmationResult
    node_confirmation_results: tuple[
        OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
        ...
    ]


def _require_decision_window_horizon(configured_horizon_steps: int) -> None:
    if configured_horizon_steps < _DECISION_WINDOW_MIN_HORIZON_STEPS:
        raise ValueError(
            "configured_horizon_steps must be at least "
            f"{_DECISION_WINDOW_MIN_HORIZON_STEPS} to observe the full decision "
            f"window (T < baseline_arrival_timestep <= T + 6); got "
            f"configured_horizon_steps={configured_horizon_steps!r}."
        )


def _extract_decision_window_visit_keys(
    resolved_undetermined_visits: tuple[
        OrderControlTvtResolvedUndeterminedVisit,
        ...
    ],
    baseline_timestep_T: int,
) -> tuple[OrderControlTvtVisitKey, ...]:
    decision_window_visit_keys: list[OrderControlTvtVisitKey] = []
    for resolved_visit in resolved_undetermined_visits:
        arrival_timestep = resolved_visit.baseline_arrival_timestep
        if baseline_timestep_T < arrival_timestep <= baseline_timestep_T + 6:
            decision_window_visit_keys.append(resolved_visit.visit_key)
    return tuple(decision_window_visit_keys)


def _validate_participation_for_decision_window_visits(
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> None:
    for visit_key in decision_window_visit_keys:
        if visit_key not in participates_by_visit_key:
            raise ValueError(
                f"participates_by_visit_key is missing decision-window VisitKey "
                f"{visit_key!r}."
            )
        participation_value = participates_by_visit_key[visit_key]
        if type(participation_value) is not bool:
            raise ValueError(
                f"participates_by_visit_key[{visit_key!r}] must be a Python bool; "
                f"got type {type(participation_value).__name__} with value "
                f"{participation_value!r}."
            )


def _extract_leading_nonparticipating_prefix(
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> tuple[OrderControlTvtVisitKey, ...]:
    leading_nonparticipating_visit_keys: list[OrderControlTvtVisitKey] = []
    for visit_key in decision_window_visit_keys:
        if participates_by_visit_key[visit_key]:
            break
        leading_nonparticipating_visit_keys.append(visit_key)
    return tuple(leading_nonparticipating_visit_keys)


def _remaining_decision_window_visit_keys(
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    confirmed_leading_nonparticipating_visit_keys: tuple[
        OrderControlTvtVisitKey,
        ...
    ],
) -> tuple[OrderControlTvtVisitKey, ...]:
    if len(confirmed_leading_nonparticipating_visit_keys) == 0:
        return decision_window_visit_keys
    prefix_length = len(confirmed_leading_nonparticipating_visit_keys)
    return decision_window_visit_keys[prefix_length:]


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


def confirm_leading_nonparticipating_decision_window_visits(
    arrived_confirmation_result: OrderControlTvtArrivedUndeterminedConfirmationResult,
    *,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtLeadingNonparticipatingConfirmationResult:
    """
    Confirm leading non-participating visits in the decision window.

    Walks ``fork_result.target_node_names`` in order, extracts resolved visits
    with ``T < baseline_arrival_timestep <= T + 6`` without re-sorting, validates
    ``participates_by_visit_key`` for every decision-window VisitKey, confirms
    the leading non-participating prefix once per Node, and returns the formal
    decision-window order plus the remaining suffix. Requires
    ``configured_horizon_steps >= 6``. Does not modify World state or rerun
    baseline fork, alignment, arrived confirmation, or collector export.
    """
    alignment_fork_result = arrived_confirmation_result.alignment_fork_result
    fork_result = alignment_fork_result.fork_result
    baseline_timestep_T = fork_result.baseline_timestep_T

    _require_decision_window_horizon(fork_result.configured_horizon_steps)

    node_confirmation_results: list[
        OrderControlTvtNodeLeadingNonparticipatingConfirmationResult
    ] = []

    for node_index, node_name in enumerate(fork_result.target_node_names):
        alignment_result = alignment_fork_result.alignment_results[node_index]
        arrived_node_result = (
            arrived_confirmation_result.node_confirmation_results[node_index]
        )

        _verify_node_name_at_index(
            node_index=node_index,
            expected_node_name=node_name,
            actual_node_name=alignment_result.node_name,
            source_label="alignment result",
        )
        _verify_node_name_at_index(
            node_index=node_index,
            expected_node_name=node_name,
            actual_node_name=arrived_node_result.node_name,
            source_label="arrived confirmation result",
        )

        decision_window_visit_keys = _extract_decision_window_visit_keys(
            alignment_result.resolved_undetermined_visits,
            baseline_timestep_T,
        )
        _validate_participation_for_decision_window_visits(
            decision_window_visit_keys,
            participates_by_visit_key,
        )
        confirmed_leading_nonparticipating_visit_keys = (
            _extract_leading_nonparticipating_prefix(
                decision_window_visit_keys,
                participates_by_visit_key,
            )
        )
        remaining_decision_window_visit_keys = _remaining_decision_window_visit_keys(
            decision_window_visit_keys,
            confirmed_leading_nonparticipating_visit_keys,
        )

        node_rank_state = rank_states_by_node_name[node_name]
        confirm_result = node_rank_state.confirm_visits_in_order(
            confirmed_leading_nonparticipating_visit_keys
        )

        node_confirmation_results.append(
            OrderControlTvtNodeLeadingNonparticipatingConfirmationResult(
                node_name=node_name,
                decision_window_visit_keys=decision_window_visit_keys,
                confirmed_leading_nonparticipating_visit_keys=(
                    confirmed_leading_nonparticipating_visit_keys
                ),
                remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
                confirm_result=confirm_result,
            )
        )

    return OrderControlTvtLeadingNonparticipatingConfirmationResult(
        arrived_confirmation_result=arrived_confirmation_result,
        node_confirmation_results=tuple(node_confirmation_results),
    )
