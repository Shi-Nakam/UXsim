"""
Connect TVT baseline fork execution with per-Node alignment of undetermined visits.

Runs one snapshot-fixed baseline fork, then classifies each target Node's baseline
collector records against caller-owned rank ledgers. Does not confirm ranks,
process leading non-participating visits, or select right-of-entry vehicles.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from uxsim.order_control_baseline_driver import (
    OrderControlBaselineForkResult,
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration,
)
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
    align_snapshot_undetermined_visits_with_node_baseline,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import World


@dataclass(frozen=True)
class OrderControlTvtBaselineForkAlignmentResult:
    """Baseline fork result plus per-Node undetermined-visit alignment results."""

    fork_result: OrderControlBaselineForkResult
    alignment_results: tuple[
        OrderControlTvtSnapshotUndeterminedAlignmentResult,
        ...
    ]


def run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
    real_W: World,
    *,
    target_node_names: list[str] | tuple[str, ...],
    baseline_horizon_steps: int,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
) -> OrderControlTvtBaselineForkAlignmentResult:
    """
    Run one TVT baseline fork, then align collector records with rank ledgers.

    Calls the TVT rank-ledger registration baseline fork driver once. After it
    completes successfully, exports each target Node's baseline collector records
    and runs the alignment helper once per Node in ``fork_result.target_node_names``
    order. Raises ``RuntimeError`` when any Node reports
    ``unregistered_collector_visit_keys``. Does not modify ``real_W``, own rank
    ledgers, confirm ranks, or return partial results on failure.
    """
    fork_result = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=baseline_horizon_steps,
        rank_states_by_node_name=rank_states_by_node_name,
    )

    alignment_results: list[OrderControlTvtSnapshotUndeterminedAlignmentResult] = []

    for node_name in fork_result.target_node_names:
        node_baseline_visit_records = fork_result.collector.export_node_baseline_visits(
            node_name
        )
        alignment_result = align_snapshot_undetermined_visits_with_node_baseline(
            node_name=node_name,
            node_baseline_visit_records=node_baseline_visit_records,
            node_rank_state=rank_states_by_node_name[node_name],
        )

        unregistered_visit_keys = alignment_result.unregistered_collector_visit_keys
        if len(unregistered_visit_keys) > 0:
            raise RuntimeError(
                "unregistered_collector_visit_keys must be empty after baseline "
                f"fork alignment for node {node_name!r}; got "
                f"{list(unregistered_visit_keys)!r}."
            )

        alignment_results.append(alignment_result)

    return OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=tuple(alignment_results),
    )
