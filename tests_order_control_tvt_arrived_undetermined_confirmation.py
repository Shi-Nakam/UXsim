# Unit tests for already-arrived undetermined-visit confirmation
# (design memo §25.25.34.38).
#
# Run from the repository root:
#   python tests_order_control_tvt_arrived_undetermined_confirmation.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock, patch

from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryResult,
)
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim import World
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
    _valid_outlink_names_at_target_node,
    confirm_already_arrived_undetermined_visits,
)
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtResolvedUndeterminedVisit,
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
    align_snapshot_undetermined_visits_with_node_baseline,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)


# --- shared helpers ---


def _new_rank_state(node_name: str) -> OrderControlTvtNodeRankState:
    return OrderControlTvtNodeRankState(node_name)


def _register_undetermined(
    state: OrderControlTvtNodeRankState,
    *visit_keys: OrderControlTvtVisitKey,
) -> None:
    for visit_key in visit_keys:
        state.register_undetermined_visit(visit_key)


def _resolved(
    vehicle_name: str,
    visit_id: int,
    *,
    baseline_arrival_timestep: int,
    arrival_tiebreaker: int | float = 0.5,
    vehicle_id: int = 0,
) -> OrderControlTvtResolvedUndeterminedVisit:
    return OrderControlTvtResolvedUndeterminedVisit(
        visit_key=(vehicle_name, visit_id),
        baseline_arrival_timestep=baseline_arrival_timestep,
        arrival_tiebreaker=arrival_tiebreaker,
        vehicle_id=vehicle_id,
    )


def _alignment_result(
    node_name: str,
    *,
    resolved: tuple[OrderControlTvtResolvedUndeterminedVisit, ...] = (),
    unresolved: tuple[OrderControlTvtVisitKey, ...] = (),
) -> OrderControlTvtSnapshotUndeterminedAlignmentResult:
    return OrderControlTvtSnapshotUndeterminedAlignmentResult(
        node_name=node_name,
        resolved_undetermined_visits=resolved,
        unresolved_undetermined_visits=unresolved,
        unregistered_collector_visit_keys=(),
    )


class _NamedOutlink:
    def __init__(self, name: str) -> None:
        self.name = name


class _TargetNode:
    def __init__(self, outlink_names: tuple[str, ...]) -> None:
        self.outlinks = {
            outlink_name: _NamedOutlink(outlink_name)
            for outlink_name in outlink_names
        }


class _RealWorldAtBaselineTime:
    def __init__(self, timestep_T: int, node_names: tuple[str, ...]) -> None:
        self.T = timestep_T
        self._node_by_name = {
            node_name: _TargetNode(("out", "side"))
            for node_name in node_names
        }

    def get_node(self, node_name: str) -> _TargetNode:
        if node_name not in self._node_by_name:
            raise Exception(f"'{node_name}' is not Node in this World")
        return self._node_by_name[node_name]


def _collector_with_arrival_route(route_next_link_name: str = "out") -> MagicMock:
    collector = MagicMock()

    def snapshot(vehicle_name: str, visit_id: int) -> dict[str, object]:
        return {
            "vehicle_name": vehicle_name,
            "visit_id": visit_id,
            "route_next_link_name": route_next_link_name,
        }

    collector.get_baseline_visit_snapshot.side_effect = snapshot
    return collector


def _fork_result(
    *,
    target_node_names: tuple[str, ...],
    baseline_timestep_T: int,
) -> OrderControlBaselineForkResult:
    return OrderControlBaselineForkResult(
        collector=_collector_with_arrival_route(),
        target_node_names=target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=3,
        fork_steps_executed=3,
        final_fork_timestep=baseline_timestep_T + 3,
        registered_visit_count=1,
        inlink_physical_orders=(),
        # This test helper does not exercise downstream boundary observation.
        downstream_boundary_result=OrderControlBaselineDownstreamBoundaryResult(
            node_results=(),
        ),
    )


def _alignment_fork_result(
    *,
    target_node_names: tuple[str, ...],
    baseline_timestep_T: int,
    alignment_results: tuple[OrderControlTvtSnapshotUndeterminedAlignmentResult, ...],
) -> OrderControlTvtBaselineForkAlignmentResult:
    fork_result = _fork_result(
        target_node_names=target_node_names,
        baseline_timestep_T=baseline_timestep_T,
    )
    return OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=alignment_results,
    )


def _confirm(
    alignment_fork_result: OrderControlTvtBaselineForkAlignmentResult,
    rank_states_by_node_name: dict[str, OrderControlTvtNodeRankState],
) -> OrderControlTvtArrivedUndeterminedConfirmationResult:
    fork_result = alignment_fork_result.fork_result
    return confirm_already_arrived_undetermined_visits(
        alignment_fork_result,
        rank_states_by_node_name=rank_states_by_node_name,
        real_W=_RealWorldAtBaselineTime(
            fork_result.baseline_timestep_T,
            fork_result.target_node_names,
        ),
    )


def _expect_runtime_error(test_callable, expected_substring: str) -> None:
    try:
        test_callable()
    except RuntimeError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected RuntimeError")


def _expect_value_error(test_callable, expected_substring: str) -> None:
    try:
        test_callable()
    except ValueError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected ValueError")


def _minimal_record(
    *,
    vehicle_name: str,
    vehicle_id: int,
    visit_id: int,
    baseline_arrival_timestep: int | None,
    arrival_tiebreaker: int | float | None = 0.5,
) -> dict:
    return {
        "vehicle_name": vehicle_name,
        "vehicle_id": vehicle_id,
        "node_name": "merge",
        "inlink_name": "in1",
        "visit_id": visit_id,
        "was_arrived_at_snapshot": False,
        "baseline_arrival_timestep": baseline_arrival_timestep,
        "arrival_tiebreaker": arrival_tiebreaker,
        "route_next_link_name": "out",
        "baseline_passage_timestep": None,
    }


# --- tests ---


def test_returns_result_types_and_preserves_alignment_fork_result_object():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=8),
                ),
            ),
        ),
    )
    result = _confirm(
        alignment_fork_result,
        {"merge": rank_state},
    )
    assert isinstance(result, OrderControlTvtArrivedUndeterminedConfirmationResult)
    assert len(result.node_confirmation_results) == 1
    node_result = result.node_confirmation_results[0]
    assert isinstance(
        node_result,
        OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
    )
    assert result.alignment_fork_result is alignment_fork_result
    assert node_result.node_name == "merge"
    assert node_result.confirmed_arrived_visit_keys == (("veh_a", 1),)
    assert isinstance(node_result.confirm_result, OrderControlTvtConfirmResult)


def test_uses_baseline_timestep_T_from_fork_result():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                    _resolved("veh_b", 2, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_a", 1),
    )
    assert rank_state.is_confirmed(("veh_a", 1))
    assert rank_state.is_undetermined(("veh_b", 2))


def test_confirms_timestep_less_than_T():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=9),
                ),
            ),
        ),
    )
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert rank_state.is_confirmed(("veh_a", 1))


def test_confirms_timestep_equal_to_T():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert rank_state.is_confirmed(("veh_b", 2))


def test_does_not_confirm_timestep_greater_than_T():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_c", 3))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_c", 3, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert rank_state.is_undetermined(("veh_c", 3))
    assert not rank_state.is_confirmed(("veh_c", 3))


def test_mixed_timesteps_confirm_only_less_or_equal_T():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_a", 1),
        ("veh_b", 2),
        ("veh_c", 3),
    )
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=9),
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                    _resolved("veh_c", 3, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_a", 1),
        ("veh_b", 2),
    )
    assert rank_state.is_confirmed(("veh_a", 1))
    assert rank_state.is_confirmed(("veh_b", 2))
    assert rank_state.is_undetermined(("veh_c", 3))


def test_preserves_resolved_column_order_not_vehicle_name_sort():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_z", 9),
        ("veh_a", 1),
        ("veh_m", 5),
    )
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=20,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved(
                        "veh_m",
                        5,
                        baseline_arrival_timestep=10,
                        arrival_tiebreaker=0.1,
                        vehicle_id=2,
                    ),
                    _resolved(
                        "veh_z",
                        9,
                        baseline_arrival_timestep=5,
                        arrival_tiebreaker=0.1,
                        vehicle_id=3,
                    ),
                    _resolved(
                        "veh_a",
                        1,
                        baseline_arrival_timestep=10,
                        arrival_tiebreaker=0.2,
                        vehicle_id=0,
                    ),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_m", 5),
        ("veh_z", 9),
        ("veh_a", 1),
    )
    assert rank_state.confirmed_visit_keys_in_order() == (
        ("veh_m", 5),
        ("veh_z", 9),
        ("veh_a", 1),
    )


def test_same_timestep_uses_arrival_tiebreaker_order():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved(
                        "veh_b",
                        2,
                        baseline_arrival_timestep=10,
                        arrival_tiebreaker=0.1,
                        vehicle_id=1,
                    ),
                    _resolved(
                        "veh_a",
                        1,
                        baseline_arrival_timestep=10,
                        arrival_tiebreaker=0.9,
                        vehicle_id=0,
                    ),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_b", 2),
        ("veh_a", 1),
    )


def test_same_timestep_and_tiebreaker_uses_vehicle_id_order():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved(
                        "veh_b",
                        2,
                        baseline_arrival_timestep=10,
                        arrival_tiebreaker=0.5,
                        vehicle_id=1,
                    ),
                    _resolved(
                        "veh_a",
                        1,
                        baseline_arrival_timestep=10,
                        arrival_tiebreaker=0.5,
                        vehicle_id=5,
                    ),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_b", 2),
        ("veh_a", 1),
    )


def test_zero_arrived_still_calls_confirm_once_per_node():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    confirm_count = 0
    original_confirm = rank_state.confirm_visits_and_formal_target_node_routes_atomically

    def counting_confirm(visits_with_formal_routes_in_order, target_node_outlink_names):
        nonlocal confirm_count
        confirm_count += 1
        return original_confirm(
            visits_with_formal_routes_in_order,
            target_node_outlink_names,
        )

    rank_state.confirm_visits_and_formal_target_node_routes_atomically = counting_confirm  # type: ignore[method-assign]
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert confirm_count == 1


def test_zero_arrived_confirm_result_is_no_op():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_pre", 1))
    rank_state.confirm_visits_in_order((("veh_pre", 1),))
    _register_undetermined(rank_state, ("veh_future", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_future", 2, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    confirm_result = result.node_confirmation_results[0].confirm_result
    assert confirm_result.k_confirmed_before == 1
    assert confirm_result.k_confirmed_after == 1
    assert confirm_result.newly_confirmed_count == 0
    assert rank_state.k_confirmed() == 1
    assert rank_state.is_undetermined(("veh_future", 2))


def test_all_resolved_visits_confirmed_when_all_arrived():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=8),
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert rank_state.undetermined_visit_keys() == frozenset()


def test_unarrived_resolved_remain_undetermined():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                    _resolved("veh_b", 2, baseline_arrival_timestep=12),
                ),
            ),
        ),
    )
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert rank_state.is_confirmed(("veh_a", 1))
    assert rank_state.is_undetermined(("veh_b", 2))


def test_unresolved_non_empty_still_confirms_arrived_resolved():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_a", 1),
        ("veh_unresolved", 9),
    )
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_a", 1),
    )
    assert rank_state.is_confirmed(("veh_a", 1))
    assert rank_state.is_undetermined(("veh_unresolved", 9))


def test_appends_after_existing_confirmed_block():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_pre", 1))
    rank_state.confirm_visits_in_order((("veh_pre", 1),))
    _register_undetermined(rank_state, ("veh_a", 2), ("veh_b", 3))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 2, baseline_arrival_timestep=8),
                    _resolved("veh_b", 3, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert rank_state.confirmed_visit_keys_in_order() == (
        ("veh_pre", 1),
        ("veh_a", 2),
        ("veh_b", 3),
    )
    assert rank_state.assigned_rank(("veh_pre", 1)) == 1
    assert rank_state.assigned_rank(("veh_a", 2)) == 2
    assert rank_state.assigned_rank(("veh_b", 3)) == 3


def test_confirm_result_counts_for_nonempty_confirmation():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_pre", 1))
    rank_state.confirm_visits_in_order((("veh_pre", 1),))
    _register_undetermined(rank_state, ("veh_a", 2), ("veh_b", 3))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 2, baseline_arrival_timestep=9),
                    _resolved("veh_b", 3, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    confirm_result = result.node_confirmation_results[0].confirm_result
    assert confirm_result.k_confirmed_before == 1
    assert confirm_result.k_confirmed_after == 3
    assert confirm_result.newly_confirmed_count == 2


def test_single_node_calls_confirm_once_using_same_rank_state_object():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    confirm_calls: list[tuple[OrderControlTvtNodeRankState, tuple]] = []
    original_confirm = rank_state.confirm_visits_and_formal_target_node_routes_atomically

    def tracking_confirm(visits_with_formal_routes_in_order, target_node_outlink_names):
        confirm_calls.append((rank_state, tuple(visits_with_formal_routes_in_order)))
        return original_confirm(
            visits_with_formal_routes_in_order,
            target_node_outlink_names,
        )

    rank_state.confirm_visits_and_formal_target_node_routes_atomically = tracking_confirm  # type: ignore[method-assign]
    _confirm(alignment_fork_result, {"merge": rank_state})
    assert len(confirm_calls) == 1
    assert confirm_calls[0][0] is rank_state
    assert confirm_calls[0][1] == ((("veh_a", 1), "out"),)


def test_multi_node_processes_in_target_node_names_order():
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("node_a", "node_b"),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "node_a",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
            _alignment_result(
                "node_b",
                resolved=(
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    result = _confirm(
        alignment_fork_result,
        {"node_a": rank_state_a, "node_b": rank_state_b},
    )
    assert [item.node_name for item in result.node_confirmation_results] == [
        "node_a",
        "node_b",
    ]
    assert rank_state_a.is_confirmed(("veh_a", 1))
    assert rank_state_b.is_confirmed(("veh_b", 2))


def test_multi_node_calls_confirm_once_per_node():
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("node_a", "node_b"),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "node_a",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
            _alignment_result(
                "node_b",
                resolved=(
                    _resolved("veh_b", 2, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    confirm_events: list[str] = []
    original_confirm_a = rank_state_a.confirm_visits_and_formal_target_node_routes_atomically
    original_confirm_b = rank_state_b.confirm_visits_and_formal_target_node_routes_atomically

    def tracking_confirm_a(visits_with_formal_routes_in_order, target_node_outlink_names):
        confirm_events.append("node_a")
        return original_confirm_a(
            visits_with_formal_routes_in_order,
            target_node_outlink_names,
        )

    def tracking_confirm_b(visits_with_formal_routes_in_order, target_node_outlink_names):
        confirm_events.append("node_b")
        return original_confirm_b(
            visits_with_formal_routes_in_order,
            target_node_outlink_names,
        )

    rank_state_a.confirm_visits_and_formal_target_node_routes_atomically = tracking_confirm_a  # type: ignore[method-assign]
    rank_state_b.confirm_visits_and_formal_target_node_routes_atomically = tracking_confirm_b  # type: ignore[method-assign]
    _confirm(
        alignment_fork_result,
        {"node_a": rank_state_a, "node_b": rank_state_b},
    )
    assert confirm_events == ["node_a", "node_b"]


def test_node_name_mismatch_raises_before_confirm():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "wrong_name",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    confirm_count = 0
    original_confirm = rank_state.confirm_visits_and_formal_target_node_routes_atomically

    def counting_confirm(visits_with_formal_routes_in_order, target_node_outlink_names):
        nonlocal confirm_count
        confirm_count += 1
        return original_confirm(
            visits_with_formal_routes_in_order,
            target_node_outlink_names,
        )

    rank_state.confirm_visits_and_formal_target_node_routes_atomically = counting_confirm  # type: ignore[method-assign]
    _expect_runtime_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "merge",
    )
    assert confirm_count == 0
    assert rank_state.is_undetermined(("veh_a", 1))


def test_node_name_mismatch_message_includes_expected_and_actual_names():
    rank_state = _new_rank_state("merge")
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result("other_name"),
        ),
    )
    _expect_runtime_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "expected target_node_names entry 'merge'",
    )
    _expect_runtime_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "alignment result has 'other_name'",
    )
    _expect_runtime_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "alignment index 0",
    )


def test_mid_failure_leaves_prior_node_confirmed_and_skips_later_nodes():
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    rank_state_c = _new_rank_state("node_c")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2))
    _register_undetermined(rank_state_c, ("veh_c", 3))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("node_a", "node_b", "node_c"),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "node_a",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
            _alignment_result(
                "node_b",
                resolved=(
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                ),
            ),
            _alignment_result(
                "node_c",
                resolved=(
                    _resolved("veh_c", 3, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    confirm_events: list[str] = []
    original_confirm_a = rank_state_a.confirm_visits_and_formal_target_node_routes_atomically

    def fail_confirm_b(visits_with_formal_routes_in_order, target_node_outlink_names):
        confirm_events.append("node_b")
        raise ValueError("confirm failed on node_b")

    rank_state_b.confirm_visits_and_formal_target_node_routes_atomically = fail_confirm_b  # type: ignore[method-assign]

    def tracking_confirm_a(visits_with_formal_routes_in_order, target_node_outlink_names):
        confirm_events.append("node_a")
        return original_confirm_a(
            visits_with_formal_routes_in_order,
            target_node_outlink_names,
        )

    rank_state_a.confirm_visits_and_formal_target_node_routes_atomically = tracking_confirm_a  # type: ignore[method-assign]

    _expect_value_error(
        lambda: _confirm(
            alignment_fork_result,
            {
                "node_a": rank_state_a,
                "node_b": rank_state_b,
                "node_c": rank_state_c,
            },
        ),
        "confirm failed on node_b",
    )
    assert confirm_events == ["node_a", "node_b"]
    assert rank_state_a.is_confirmed(("veh_a", 1))
    assert rank_state_b.is_undetermined(("veh_b", 2))
    assert rank_state_c.is_undetermined(("veh_c", 3))


def test_failed_node_leaves_no_partial_confirmation():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                    _resolved("veh_missing", 9, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    before = {
        "k_confirmed": rank_state.k_confirmed(),
        "confirmed": rank_state.confirmed_visit_keys_in_order(),
        "undetermined": rank_state.undetermined_visit_keys(),
    }
    _expect_value_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "not pre-registered",
    )
    after = {
        "k_confirmed": rank_state.k_confirmed(),
        "confirmed": rank_state.confirmed_visit_keys_in_order(),
        "undetermined": rank_state.undetermined_visit_keys(),
    }
    assert before == after


def test_unregistered_visit_value_error_propagates():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_missing", 9, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    _expect_value_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "not pre-registered",
    )


def test_already_confirmed_visit_value_error_propagates():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    rank_state.confirm_visits_in_order((("veh_a", 1),))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    _expect_value_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "already confirmed",
    )


def test_duplicate_input_value_error_propagates():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    _expect_value_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "Duplicate VisitKey",
    )


def test_failure_does_not_return_partial_overall_result():
    rank_state = _new_rank_state("merge")
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_missing", 9, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    try:
        _confirm(alignment_fork_result, {"merge": rank_state})
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_does_not_rerun_baseline_fork_alignment_or_collector():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )
    with patch(
        "uxsim.order_control_tvt_arrived_undetermined_confirmation."
        "OrderControlTvtBaselineForkAlignmentResult",
    ) as patched_result_type, patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
    ) as patched_align, patch(
        "uxsim.order_control_baseline_driver."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
    ) as patched_fork:
        _confirm(alignment_fork_result, {"merge": rank_state})
        patched_fork.assert_not_called()
        patched_align.assert_not_called()
        patched_result_type.assert_not_called()


def test_integration_with_real_alignment_types_and_confirm():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_b", 2),
        ("veh_a", 1),
        ("veh_future", 3),
        ("veh_unresolved", 9),
    )
    records = [
        _minimal_record(
            vehicle_name="veh_b",
            vehicle_id=1,
            visit_id=2,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.1,
        ),
        _minimal_record(
            vehicle_name="veh_a",
            vehicle_id=0,
            visit_id=1,
            baseline_arrival_timestep=10,
            arrival_tiebreaker=0.2,
        ),
        _minimal_record(
            vehicle_name="veh_future",
            vehicle_id=2,
            visit_id=3,
            baseline_arrival_timestep=12,
            arrival_tiebreaker=0.1,
        ),
        _minimal_record(
            vehicle_name="veh_unresolved",
            vehicle_id=3,
            visit_id=9,
            baseline_arrival_timestep=None,
            arrival_tiebreaker=None,
        ),
    ]
    alignment_result = align_snapshot_undetermined_visits_with_node_baseline(
        node_name="merge",
        node_baseline_visit_records=records,
        node_rank_state=rank_state,
    )
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(alignment_result,),
    )
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_b", 2),
        ("veh_a", 1),
    )
    assert rank_state.is_confirmed(("veh_b", 2))
    assert rank_state.is_confirmed(("veh_a", 1))
    assert rank_state.is_undetermined(("veh_future", 3))
    assert rank_state.is_undetermined(("veh_unresolved", 9))
    assert alignment_result.unresolved_undetermined_visits == (("veh_unresolved", 9),)


def test_atomic_confirm_saves_arrival_route_without_old_rank_only_api():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=8),
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )

    def snapshot(vehicle_name: str, visit_id: int) -> dict[str, object]:
        routes = {("veh_a", 1): "out", ("veh_b", 2): "side"}
        return {"route_next_link_name": routes[(vehicle_name, visit_id)]}

    alignment_fork_result.fork_result.collector.get_baseline_visit_snapshot.side_effect = snapshot

    def reject_rank_only_confirm(*args, **kwargs):
        raise AssertionError("confirm_visits_in_order must not be called")

    rank_state.confirm_visits_in_order = reject_rank_only_confirm  # type: ignore[method-assign]
    result = _confirm(alignment_fork_result, {"merge": rank_state})
    assert result.node_confirmation_results[0].confirmed_arrived_visit_keys == (
        ("veh_a", 1),
        ("veh_b", 2),
    )
    assert result.node_confirmation_results[0].confirm_result.newly_confirmed_count == 2
    assert rank_state.formal_route_next_link_name(("veh_a", 1)) == "out"
    assert rank_state.formal_route_next_link_name(("veh_b", 2)) == "side"
    assert rank_state.assigned_rank(("veh_a", 1)) == 1
    assert rank_state.assigned_rank(("veh_b", 2)) == 2


def test_missing_arrival_route_leaves_arrived_confirmation_unchanged():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_b", 2))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=8),
                    _resolved("veh_b", 2, baseline_arrival_timestep=10),
                ),
            ),
        ),
    )

    def snapshot(vehicle_name: str, visit_id: int) -> dict[str, object]:
        route = "out" if (vehicle_name, visit_id) == ("veh_a", 1) else None
        return {"route_next_link_name": route}

    alignment_fork_result.fork_result.collector.get_baseline_visit_snapshot.side_effect = snapshot
    before_export = rank_state.export_state()
    _expect_value_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "route_next_link_name",
    )
    assert rank_state.k_confirmed() == 0
    assert rank_state.export_state() == before_export
    assert rank_state.is_undetermined(("veh_a", 1))
    assert rank_state.is_undetermined(("veh_b", 2))


def test_confirm_uses_real_world_get_node_for_outlink_names():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_a", 1, baseline_arrival_timestep=10),),
            ),
        ),
    )
    real_W = _RealWorldAtBaselineTime(10, ("merge",))
    with patch.object(real_W, "get_node", wraps=real_W.get_node) as get_node_mock:
        confirm_already_arrived_undetermined_visits(
            alignment_fork_result,
            rank_states_by_node_name={"merge": rank_state},
            real_W=real_W,
        )
        get_node_mock.assert_called_once_with("merge")


class _RealWorldWithUnexpectedGetNodeFailure:
    def __init__(self, timestep_T: int) -> None:
        self.T = timestep_T

    def get_node(self, node_name: str) -> _TargetNode:
        raise RuntimeError("internal world failure")


class _RealWorldWithoutCallableGetNode:
    T = 10
    get_node = "not-callable"


def test_missing_target_node_via_get_node_leaves_arrived_confirmation_unchanged():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_a", 1, baseline_arrival_timestep=10),),
            ),
        ),
    )
    real_W = _RealWorldAtBaselineTime(10, ())
    before_export = rank_state.export_state()
    _expect_value_error(
        lambda: confirm_already_arrived_undetermined_visits(
            alignment_fork_result,
            rank_states_by_node_name={"merge": rank_state},
            real_W=real_W,
        ),
        "merge",
    )
    assert rank_state.export_state() == before_export


def test_uxsim_missing_node_exception_becomes_value_error_with_node_name():
    real_W = _RealWorldAtBaselineTime(10, ())
    try:
        _valid_outlink_names_at_target_node(real_W, "merge")
        raise AssertionError("Expected ValueError for missing target Node")
    except ValueError as exc:
        assert "merge" in str(exc)
        assert exc.__cause__ is not None
        assert str(exc.__cause__) == "'merge' is not Node in this World"


def test_unexpected_get_node_runtime_error_is_reraised_without_conversion():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_a", 1, baseline_arrival_timestep=10),),
            ),
        ),
    )
    real_W = _RealWorldWithUnexpectedGetNodeFailure(10)
    before_export = rank_state.export_state()
    atomic_called = False

    def reject_atomic_confirm(*args, **kwargs):
        nonlocal atomic_called
        atomic_called = True
        raise AssertionError("atomic confirm must not be called")

    rank_state.confirm_visits_and_formal_target_node_routes_atomically = reject_atomic_confirm  # type: ignore[method-assign]
    try:
        confirm_already_arrived_undetermined_visits(
            alignment_fork_result,
            rank_states_by_node_name={"merge": rank_state},
            real_W=real_W,
        )
        raise AssertionError("Expected RuntimeError from get_node")
    except RuntimeError as exc:
        assert str(exc) == "internal world failure"
    assert atomic_called is False
    assert rank_state.export_state() == before_export


def test_non_callable_get_node_raises_value_error_without_type_error():
    rank_state = _new_rank_state("merge")
    before_export = rank_state.export_state()
    _expect_value_error(
        lambda: _valid_outlink_names_at_target_node(
            _RealWorldWithoutCallableGetNode(),
            "merge",
        ),
        "callable get_node",
    )
    assert rank_state.export_state() == before_export


def test_empty_outlink_name_from_values_raises_and_leaves_ledger_unchanged():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    real_W = _RealWorldAtBaselineTime(10, ("merge",))
    real_W._node_by_name["merge"] = _TargetNode(("",))
    before_export = rank_state.export_state()
    _expect_value_error(
        lambda: _valid_outlink_names_at_target_node(real_W, "merge"),
        "non-empty name",
    )
    assert rank_state.export_state() == before_export


def _build_uxsim_merge_two_outlinks_world() -> World:
    W = World(
        name="tvt_arrived_atomic_outlink_names",
        deltan=1,
        tmax=20,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("dest_a", 2, 0)
    W.addNode("dest_b", 2, 1)
    W.addLink("in", "orig", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest_a", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1)
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()
    W.T = 10
    return W


def test_uxsim_world_outlink_names_use_get_node_and_outlinks_values():
    W = _build_uxsim_merge_two_outlinks_world()
    outlink_names = _valid_outlink_names_at_target_node(W, "merge")
    assert outlink_names == frozenset({"out", "side"})
    merge_node = W.get_node("merge")
    value_names = {link.name for link in merge_node.outlinks.values()}
    assert value_names == outlink_names


def test_route_outside_target_node_outlinks_leaves_arrived_confirmation_unchanged():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1))
    alignment_fork_result = _alignment_fork_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_a", 1, baseline_arrival_timestep=10),),
            ),
        ),
    )
    alignment_fork_result.fork_result.collector = _collector_with_arrival_route("north")
    before_export = rank_state.export_state()
    _expect_value_error(
        lambda: _confirm(alignment_fork_result, {"merge": rank_state}),
        "formal_route_next_link_name",
    )
    assert rank_state.export_state() == before_export
    assert rank_state.confirmed_visit_keys_in_order() == ()


def test_existing_alignment_and_rank_state_types_remain_unchanged():
    alignment_fields = {
        field.name for field in dataclasses.fields(OrderControlTvtBaselineForkAlignmentResult)
    }
    assert alignment_fields == {"fork_result", "alignment_results"}
    snapshot_fields = {
        field.name
        for field in dataclasses.fields(OrderControlTvtSnapshotUndeterminedAlignmentResult)
    }
    assert snapshot_fields == {
        "node_name",
        "resolved_undetermined_visits",
        "unresolved_undetermined_visits",
        "unregistered_collector_visit_keys",
    }
    rank_state = _new_rank_state("merge")
    assert hasattr(rank_state, "confirm_visits_in_order")
    assert hasattr(rank_state, "register_undetermined_visit")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
