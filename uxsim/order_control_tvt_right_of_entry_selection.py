"""
Select right-of-entry visits after leading non-participating confirmation.

Reads leading confirmation results, rank states, and participation mappings to
select the top participating visit as right-of-entry when baseline arrivals are
fully resolved. Does not modify rank ledgers or rerun upstream processing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)


class OrderControlTvtRightOfEntrySelectionStatus(Enum):
    """Per-Node outcome of right-of-entry visit selection."""

    SELECTED = "selected"
    NO_RIGHT_OF_ENTRY = "no_right_of_entry"
    UNRESOLVED_BASELINE_ARRIVALS = "unresolved_baseline_arrivals"


@dataclass(frozen=True)
class OrderControlTvtNodeRightOfEntrySelectionResult:
    """Per-Node result of right-of-entry visit selection."""

    node_name: str
    selection_status: OrderControlTvtRightOfEntrySelectionStatus
    right_of_entry_visit_key: OrderControlTvtVisitKey | None
    k_confirmed_before: int


@dataclass(frozen=True)
class OrderControlTvtRightOfEntrySelectionResult:
    """Overall result of right-of-entry visit selection."""

    leading_confirmation_result: OrderControlTvtLeadingNonparticipatingConfirmationResult
    node_selection_results: tuple[
        OrderControlTvtNodeRightOfEntrySelectionResult,
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


def _validate_participation_for_candidate(
    visit_key: OrderControlTvtVisitKey,
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> None:
    if visit_key not in participates_by_visit_key:
        raise ValueError(
            f"participates_by_visit_key is missing right-of-entry candidate "
            f"VisitKey {visit_key!r}."
        )
    participation_value = participates_by_visit_key[visit_key]
    if type(participation_value) is not bool:
        raise ValueError(
            f"participates_by_visit_key[{visit_key!r}] must be a Python bool; "
            f"got type {type(participation_value).__name__} with value "
            f"{participation_value!r}."
        )
    if not participation_value:
        raise RuntimeError(
            f"Leading remaining-decision-window prefix contract violated for "
            f"VisitKey {visit_key!r}: participates_by_visit_key[{visit_key!r}] "
            f"is False, but remaining_decision_window_visit_keys head must be "
            f"a participating Visit."
        )


def _validate_undetermined_candidate(
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    rank_state: OrderControlTvtNodeRankState,
) -> None:
    if rank_state.is_undetermined(visit_key):
        return
    if rank_state.is_confirmed(visit_key):
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry candidate VisitKey {visit_key!r} "
            f"is already confirmed and cannot be selected."
        )
    raise RuntimeError(
        f"Node {node_name!r}: right-of-entry candidate VisitKey {visit_key!r} "
        f"is not pre-registered in the rank ledger."
    )


def select_right_of_entry_decision_window_visits(
    leading_confirmation_result: OrderControlTvtLeadingNonparticipatingConfirmationResult,
    *,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
    participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtRightOfEntrySelectionResult:
    """
    Select right-of-entry visits from leading non-participating confirmation results.

    Walks ``fork_result.target_node_names`` in order, reads unresolved visits and
    remaining decision-window VisitKeys without modifying rank ledgers, and
    returns per-Node selection status plus ``k_confirmed_before`` snapshots. Does
    not rerun baseline fork, alignment, arrived confirmation, leading
    non-participating confirmation, or collector export.
    """
    arrived_confirmation_result = leading_confirmation_result.arrived_confirmation_result
    alignment_fork_result = arrived_confirmation_result.alignment_fork_result
    fork_result = alignment_fork_result.fork_result
    alignment_results = alignment_fork_result.alignment_results
    leading_node_results = leading_confirmation_result.node_confirmation_results

    node_selection_results: list[OrderControlTvtNodeRightOfEntrySelectionResult] = []

    for node_index, node_name in enumerate(fork_result.target_node_names):
        alignment_result = alignment_results[node_index]
        leading_node_result = leading_node_results[node_index]

        _verify_node_name_at_index(
            node_index=node_index,
            expected_node_name=node_name,
            actual_node_name=alignment_result.node_name,
            source_label="alignment result",
        )
        _verify_node_name_at_index(
            node_index=node_index,
            expected_node_name=node_name,
            actual_node_name=leading_node_result.node_name,
            source_label="leading confirmation result",
        )

        node_rank_state = rank_states_by_node_name[node_name]
        k_confirmed_before = node_rank_state.k_confirmed()

        if len(alignment_result.unresolved_undetermined_visits) > 0:
            node_selection_results.append(
                OrderControlTvtNodeRightOfEntrySelectionResult(
                    node_name=node_name,
                    selection_status=(
                        OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS
                    ),
                    right_of_entry_visit_key=None,
                    k_confirmed_before=k_confirmed_before,
                )
            )
            continue

        remaining_visit_keys = (
            leading_node_result.remaining_decision_window_visit_keys
        )
        if len(remaining_visit_keys) == 0:
            node_selection_results.append(
                OrderControlTvtNodeRightOfEntrySelectionResult(
                    node_name=node_name,
                    selection_status=(
                        OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY
                    ),
                    right_of_entry_visit_key=None,
                    k_confirmed_before=k_confirmed_before,
                )
            )
            continue

        candidate_visit_key = remaining_visit_keys[0]
        _validate_participation_for_candidate(
            candidate_visit_key,
            participates_by_visit_key,
        )
        _validate_undetermined_candidate(
            node_name,
            candidate_visit_key,
            node_rank_state,
        )

        node_selection_results.append(
            OrderControlTvtNodeRightOfEntrySelectionResult(
                node_name=node_name,
                selection_status=OrderControlTvtRightOfEntrySelectionStatus.SELECTED,
                right_of_entry_visit_key=candidate_visit_key,
                k_confirmed_before=k_confirmed_before,
            )
        )

    return OrderControlTvtRightOfEntrySelectionResult(
        leading_confirmation_result=leading_confirmation_result,
        node_selection_results=tuple(node_selection_results),
    )
