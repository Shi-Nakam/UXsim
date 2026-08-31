"""
Fixed-horizon full-World baseline driver for snapshot-fixed TVT research visits.

Connects World.copy(), OrderControlBaselineCollector, snapshot registration, and a
single fork-side exec_simulation() batch forward. Institutional TVT logic stays outside.
"""

from __future__ import annotations

from dataclasses import dataclass

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_snapshot import register_snapshot_fixed_visits
from uxsim.uxsim import World


@dataclass
class OrderControlBaselineForkResult:
    """Result of one snapshot-fixed baseline fork run."""

    collector: OrderControlBaselineCollector
    target_node_names: tuple[str, ...]
    baseline_timestep_T: int
    configured_horizon_steps: int
    fork_steps_executed: int
    final_fork_timestep: int
    registered_visit_count: int


def _validate_and_freeze_target_node_names(target_node_names) -> tuple[str, ...]:
    if not isinstance(target_node_names, (list, tuple)):
        raise ValueError(
            "target_node_names must be a list or tuple of node name strings; "
            f"got {type(target_node_names).__name__}."
        )
    if len(target_node_names) == 0:
        raise ValueError(
            "target_node_names must contain at least one target node name; "
            "an empty node list is an input error and is not the same as a "
            "non-empty node list with zero registered snapshot-fixed visits."
        )
    return tuple(target_node_names)


def _validate_baseline_horizon_steps(baseline_horizon_steps) -> int:
    if (
        isinstance(baseline_horizon_steps, bool)
        or not isinstance(baseline_horizon_steps, int)
        or baseline_horizon_steps < 1
    ):
        raise ValueError(
            "baseline_horizon_steps must be a Python int greater than or equal "
            "to 1 and must not be bool; "
            f"got value={baseline_horizon_steps!r}, "
            f"type={type(baseline_horizon_steps).__name__}."
        )
    return baseline_horizon_steps


def _count_exported_baseline_visits(
    collector: OrderControlBaselineCollector,
    fixed_target_node_names: tuple[str, ...],
) -> int:
    return sum(
        len(collector.export_node_baseline_visits(node_name))
        for node_name in fixed_target_node_names
    )


def _validate_registered_visit_count(
    *,
    registered_visit_count: int,
    collector: OrderControlBaselineCollector,
    fixed_target_node_names: tuple[str, ...],
    reconciliation_phase: str,
) -> None:
    exported_visit_count = _count_exported_baseline_visits(
        collector, fixed_target_node_names
    )
    if exported_visit_count != registered_visit_count:
        raise RuntimeError(
            "Snapshot-fixed baseline visit count mismatch during "
            f"{reconciliation_phase}: registered_visit_count="
            f"{registered_visit_count}, exported_visit_count="
            f"{exported_visit_count}, fixed_target_node_names="
            f"{fixed_target_node_names!r}."
        )


def _validate_copied_fork(
    *,
    real_W: World,
    fork_W: World,
    baseline_timestep_T: int,
) -> None:
    if fork_W is real_W:
        raise RuntimeError(
            "fork_W must be a distinct copy of real_W; got the same object."
        )
    if fork_W.T != baseline_timestep_T:
        raise RuntimeError(
            "fork_W.T must equal baseline_timestep_T immediately after copy: "
            f"baseline_timestep_T={baseline_timestep_T}, fork_W.T={fork_W.T}."
        )
    if fork_W._order_control_baseline_collector is not None:
        raise RuntimeError(
            "fork_W._order_control_baseline_collector must be None immediately "
            f"after copy; got {fork_W._order_control_baseline_collector!r}."
        )


def _validate_remaining_baseline_steps(
    fork_W: World,
    baseline_horizon_steps: int,
) -> None:
    remaining_steps = fork_W.TSIZE - fork_W.T
    required_steps = baseline_horizon_steps + 1
    if remaining_steps < required_steps:
        raise ValueError(
            "Insufficient remaining fork timesteps for baseline_horizon_steps "
            "plus one post-horizon timestep margin: "
            f"baseline_horizon_steps={baseline_horizon_steps}, "
            f"remaining_steps={remaining_steps}, "
            f"required_steps={required_steps}, fork_W.T={fork_W.T}, "
            f"fork_W.TSIZE={fork_W.TSIZE}. "
            "The baseline forward must leave at least one timestep before World "
            "termination."
        )


def _validate_completed_fork_forward(
    *,
    fork_W: World,
    fork_timestep_before: int,
    baseline_horizon_steps: int,
) -> None:
    expected_fork_timestep_after = (
        fork_timestep_before + baseline_horizon_steps
    )
    if fork_W.T != expected_fork_timestep_after:
        raise RuntimeError(
            "fork_W.T did not advance by baseline_horizon_steps after forward: "
            f"fork_timestep_before={fork_timestep_before}, fork_W.T={fork_W.T}, "
            f"baseline_horizon_steps={baseline_horizon_steps}, "
            f"expected_fork_timestep_after={expected_fork_timestep_after}."
        )
    if fork_W.T >= fork_W.TSIZE:
        raise RuntimeError(
            "fork_W reached or passed World termination after baseline forward: "
            f"fork_W.T={fork_W.T}, fork_W.TSIZE={fork_W.TSIZE}. "
            "The baseline forward must leave at least one timestep before World "
            "termination."
        )


def _validate_real_world_unchanged(
    *,
    real_W: World,
    real_world_t_before: int,
    real_world_time_before: float,
    real_world_collector_before,
) -> None:
    if real_W.T != real_world_t_before:
        raise RuntimeError(
            "real_W.T changed during baseline fork driver execution: "
            f"before={real_world_t_before}, after={real_W.T}."
        )
    if real_W.TIME != real_world_time_before:
        raise RuntimeError(
            "real_W.TIME changed during baseline fork driver execution: "
            f"before={real_world_time_before}, after={real_W.TIME}."
        )
    if real_W._order_control_baseline_collector is not real_world_collector_before:
        raise RuntimeError(
            "real_W._order_control_baseline_collector changed during baseline "
            "fork driver execution: "
            f"before={real_world_collector_before!r}, "
            f"after={real_W._order_control_baseline_collector!r}."
        )


def _build_empty_baseline_result(
    *,
    collector: OrderControlBaselineCollector,
    fixed_target_node_names: tuple[str, ...],
    baseline_timestep_T: int,
    baseline_horizon_steps: int,
) -> OrderControlBaselineForkResult:
    return OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=fixed_target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=baseline_horizon_steps,
        fork_steps_executed=0,
        final_fork_timestep=baseline_timestep_T,
        registered_visit_count=0,
    )


def _build_completed_baseline_result(
    *,
    collector: OrderControlBaselineCollector,
    fixed_target_node_names: tuple[str, ...],
    baseline_timestep_T: int,
    baseline_horizon_steps: int,
    fork_W: World,
    registered_visit_count: int,
) -> OrderControlBaselineForkResult:
    return OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=fixed_target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=baseline_horizon_steps,
        fork_steps_executed=baseline_horizon_steps,
        final_fork_timestep=fork_W.T,
        registered_visit_count=registered_visit_count,
    )


def run_snapshot_fixed_baseline_fork(
    real_W: World,
    *,
    target_node_names: list[str] | tuple[str, ...],
    baseline_horizon_steps: int,
) -> OrderControlBaselineForkResult:
    """
    Copy real_W, register snapshot-fixed visits on fork_W, and run one fixed horizon.

    Does not modify real_W. Does not return fork_W. Raises on invalid input or
    internal inconsistency; does not return partial results on failure.
    """
    fixed_target_node_names = _validate_and_freeze_target_node_names(
        target_node_names
    )
    baseline_horizon_steps = _validate_baseline_horizon_steps(
        baseline_horizon_steps
    )

    if real_W._order_control_baseline_collector is not None:
        raise ValueError(
            "real_W._order_control_baseline_collector must be None before "
            f"baseline fork; got {real_W._order_control_baseline_collector!r}."
        )

    real_world_t_before = real_W.T
    real_world_time_before = real_W.TIME
    real_world_collector_before = real_W._order_control_baseline_collector
    baseline_timestep_T = real_W.T

    fork_W = real_W.copy()
    _validate_copied_fork(
        real_W=real_W,
        fork_W=fork_W,
        baseline_timestep_T=baseline_timestep_T,
    )

    collector = OrderControlBaselineCollector()
    fork_W._order_control_baseline_collector = collector

    registered_visit_count = register_snapshot_fixed_visits(
        fork_W,
        collector,
        target_node_names=fixed_target_node_names,
    )
    _validate_registered_visit_count(
        registered_visit_count=registered_visit_count,
        collector=collector,
        fixed_target_node_names=fixed_target_node_names,
        reconciliation_phase="after snapshot registration",
    )

    if registered_visit_count == 0:
        _validate_real_world_unchanged(
            real_W=real_W,
            real_world_t_before=real_world_t_before,
            real_world_time_before=real_world_time_before,
            real_world_collector_before=real_world_collector_before,
        )
        return _build_empty_baseline_result(
            collector=collector,
            fixed_target_node_names=fixed_target_node_names,
            baseline_timestep_T=baseline_timestep_T,
            baseline_horizon_steps=baseline_horizon_steps,
        )

    _validate_remaining_baseline_steps(fork_W, baseline_horizon_steps)

    fork_timestep_before = fork_W.T
    fork_W.exec_simulation(
        duration_t2=baseline_horizon_steps * fork_W.DELTAT
    )

    _validate_completed_fork_forward(
        fork_W=fork_W,
        fork_timestep_before=fork_timestep_before,
        baseline_horizon_steps=baseline_horizon_steps,
    )
    _validate_registered_visit_count(
        registered_visit_count=registered_visit_count,
        collector=collector,
        fixed_target_node_names=fixed_target_node_names,
        reconciliation_phase="after baseline forward",
    )
    _validate_real_world_unchanged(
        real_W=real_W,
        real_world_t_before=real_world_t_before,
        real_world_time_before=real_world_time_before,
        real_world_collector_before=real_world_collector_before,
    )

    return _build_completed_baseline_result(
        collector=collector,
        fixed_target_node_names=fixed_target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        baseline_horizon_steps=baseline_horizon_steps,
        fork_W=fork_W,
        registered_visit_count=registered_visit_count,
    )
