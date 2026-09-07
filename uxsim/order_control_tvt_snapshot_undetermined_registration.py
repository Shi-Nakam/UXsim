"""
Register undetermined visits from a snapshot-fixed registration plan onto
per-Node TVT rank ledgers.

Connects OrderControlBaselineSnapshotRegistrationPlan to multiple
OrderControlTvtNodeRankState instances. Does not build snapshot plans,
register on baseline collectors, confirm ranks, select right-of-entry
vehicles, or run baseline alignment.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from uxsim.order_control_baseline_snapshot import (
    OrderControlBaselineSnapshotRegistrationPlan,
    OrderControlBaselineSnapshotVisitEntry,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)


def register_undetermined_visits_from_snapshot_plan(
    plan: OrderControlBaselineSnapshotRegistrationPlan,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
) -> int:
    """
    Register new undetermined visits from a validated snapshot plan onto rank ledgers.

    Reads ``plan`` entries and the current undetermined or confirmed membership on
    each supplied rank ledger, then registers only VisitKeys that are neither
    undetermined nor confirmed. Mutates the ``OrderControlTvtNodeRankState``
    objects in ``rank_states_by_node_name``. Does not modify ``plan``, World
    state, Vehicles, Nodes, Links, or any baseline collector.

    This function registers undetermined visits onto TVT rank ledgers. It is not
    ``apply_snapshot_fixed_visit_registration_plan``, which registers snapshot
    visits onto a baseline collector.

    Parameters
    ----------
    plan
        Validated snapshot-fixed visit registration plan from prepare.
    rank_states_by_node_name
        Mapping from Node name to the real-World rank ledger for that Node.
        Extra Node keys not present in ``plan.target_node_names`` are ignored.

    Returns
    -------
    int
        Total number of newly registered undetermined visits across all Nodes.
    """
    registration_keys_by_node_name = _prepare_registration_keys_by_node_name(
        plan,
        rank_states_by_node_name,
    )
    return _apply_registration_keys_by_node_name(
        plan,
        rank_states_by_node_name,
        registration_keys_by_node_name,
    )


def _prepare_registration_keys_by_node_name(
    plan: Any,
    rank_states_by_node_name: Any,
) -> dict[str, tuple[OrderControlTvtVisitKey, ...]]:
    """
    Read plan entries and rank ledgers without mutating any rank state.

    Returns newly registerable VisitKeys grouped by Node name. Node inner order
    follows ``plan.entries`` order. This order is for test and diagnostic
    reproducibility only; it does not assign formal ranks.
    """
    if not isinstance(plan, OrderControlBaselineSnapshotRegistrationPlan):
        raise ValueError(
            "plan must be an OrderControlBaselineSnapshotRegistrationPlan; "
            f"got {type(plan).__name__}."
        )
    if not isinstance(rank_states_by_node_name, Mapping):
        raise ValueError(
            "rank_states_by_node_name must be a Mapping from node name str to "
            f"OrderControlTvtNodeRankState; got {type(rank_states_by_node_name).__name__}."
        )

    target_node_names = plan.target_node_names
    target_node_name_set = set(target_node_names)
    rank_states_for_target_nodes: dict[str, OrderControlTvtNodeRankState] = {}

    for node_name in target_node_names:
        if node_name not in rank_states_by_node_name:
            raise ValueError(
                f"Missing rank state for target node {node_name!r} in "
                "rank_states_by_node_name."
            )
        rank_state = rank_states_by_node_name[node_name]
        if not isinstance(rank_state, OrderControlTvtNodeRankState):
            raise ValueError(
                f"rank_states_by_node_name[{node_name!r}] must be an "
                f"OrderControlTvtNodeRankState; got {type(rank_state).__name__}."
            )
        if rank_state.node_name != node_name:
            raise ValueError(
                f"rank_states_by_node_name key {node_name!r} does not match "
                f"rank_state.node_name {rank_state.node_name!r}."
            )
        rank_states_for_target_nodes[node_name] = rank_state

    registration_keys_by_node_name: dict[str, list[OrderControlTvtVisitKey]] = {
        node_name: [] for node_name in target_node_names
    }

    for entry in plan.entries:
        if not isinstance(entry, OrderControlBaselineSnapshotVisitEntry):
            raise ValueError(
                "plan.entries must contain OrderControlBaselineSnapshotVisitEntry "
                f"objects; got {type(entry).__name__}."
            )
        node_name = entry.node_name
        if node_name not in target_node_name_set:
            raise ValueError(
                f"plan entry node_name {node_name!r} is not listed in "
                f"plan.target_node_names {target_node_names!r}."
            )

        visit_key = entry.visit_key
        rank_state = rank_states_for_target_nodes[node_name]
        if rank_state.is_undetermined(visit_key):
            continue
        if rank_state.is_confirmed(visit_key):
            continue
        registration_keys_by_node_name[node_name].append(visit_key)

    return {
        node_name: tuple(registration_keys_by_node_name[node_name])
        for node_name in target_node_names
    }


def _apply_registration_keys_by_node_name(
    plan: OrderControlBaselineSnapshotRegistrationPlan,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
    registration_keys_by_node_name: dict[str, tuple[OrderControlTvtVisitKey, ...]],
) -> int:
    """
    Register prepared VisitKeys onto each Node rank ledger.

    Calls register_undetermined_visits at most once per Node.
    """
    total_newly_registered_count = 0

    for node_name in plan.target_node_names:
        visit_keys_to_register = registration_keys_by_node_name[node_name]
        if len(visit_keys_to_register) == 0:
            continue

        rank_state = rank_states_by_node_name[node_name]
        rank_state.register_undetermined_visits(visit_keys_to_register)
        total_newly_registered_count += len(visit_keys_to_register)

    return total_newly_registered_count
