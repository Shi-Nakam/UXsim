# Unit tests for leading non-participating decision-window confirmation
# (design memo §25.25.34.40).
#
# Run from the repository root:
#   python tests_order_control_tvt_leading_nonparticipating_confirmation.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock, patch

from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
)
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtResolvedUndeterminedVisit,
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
    OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
    confirm_leading_nonparticipating_decision_window_visits,
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


def _fork_result(
    *,
    target_node_names: tuple[str, ...],
    baseline_timestep_T: int,
    configured_horizon_steps: int = 6,
) -> OrderControlBaselineForkResult:
    return OrderControlBaselineForkResult(
        collector=MagicMock(),
        target_node_names=target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=configured_horizon_steps,
        fork_steps_executed=configured_horizon_steps,
        final_fork_timestep=baseline_timestep_T + configured_horizon_steps,
        registered_visit_count=1,
    )


def _arrived_confirmation_result(
    *,
    target_node_names: tuple[str, ...],
    baseline_timestep_T: int,
    configured_horizon_steps: int = 6,
    alignment_results: tuple[OrderControlTvtSnapshotUndeterminedAlignmentResult, ...],
) -> OrderControlTvtArrivedUndeterminedConfirmationResult:
    fork_result = _fork_result(
        target_node_names=target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=configured_horizon_steps,
    )
    alignment_fork_result = OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=alignment_results,
    )
    node_arrived_results = tuple(
        OrderControlTvtNodeArrivedUndeterminedConfirmationResult(
            node_name=node_name,
            confirmed_arrived_visit_keys=(),
            confirm_result=OrderControlTvtConfirmResult(
                k_confirmed_before=0,
                k_confirmed_after=0,
                newly_confirmed_count=0,
            ),
        )
        for node_name in target_node_names
    )
    return OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment_fork_result,
        node_confirmation_results=node_arrived_results,
    )


def _participation_mapping(
    *items: tuple[OrderControlTvtVisitKey, bool],
) -> dict[OrderControlTvtVisitKey, bool]:
    return dict(items)


def _confirm(
    arrived_confirmation_result: OrderControlTvtArrivedUndeterminedConfirmationResult,
    rank_states_by_node_name: dict[str, OrderControlTvtNodeRankState],
    participates_by_visit_key: dict[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtLeadingNonparticipatingConfirmationResult:
    return confirm_leading_nonparticipating_decision_window_visits(
        arrived_confirmation_result,
        rank_states_by_node_name=rank_states_by_node_name,
        participates_by_visit_key=participates_by_visit_key,
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


# --- tests ---


def test_returns_result_types_and_preserves_arrived_confirmation_result():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1), ("veh_p1", 2))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_p1", 2, baseline_arrival_timestep=12),
                ),
            ),
        ),
    )
    result = _confirm(
        arrived_result,
        {"merge": rank_state},
        _participation_mapping((("veh_n1", 1), False), (("veh_p1", 2), True)),
    )
    assert isinstance(result, OrderControlTvtLeadingNonparticipatingConfirmationResult)
    node_result = result.node_confirmation_results[0]
    assert isinstance(
        node_result,
        OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
    )
    assert result.arrived_confirmation_result is arrived_result
    assert node_result.confirmed_leading_nonparticipating_visit_keys == (("veh_n1", 1),)
    assert node_result.remaining_decision_window_visit_keys == (("veh_p1", 2),)


def test_horizon_five_raises_before_any_confirm():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        configured_horizon_steps=5,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_n1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    confirm_count = 0
    original_confirm = rank_state.confirm_visits_in_order

    def counting_confirm(visit_keys_in_order):
        nonlocal confirm_count
        confirm_count += 1
        return original_confirm(visit_keys_in_order)

    rank_state.confirm_visits_in_order = counting_confirm  # type: ignore[method-assign]
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            _participation_mapping((("veh_n1", 1), False)),
        ),
        "configured_horizon_steps=5",
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            _participation_mapping((("veh_n1", 1), False)),
        ),
        "at least 6",
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            _participation_mapping((("veh_n1", 1), False)),
        ),
        "full decision window",
    )
    assert confirm_count == 0


def test_horizon_six_is_accepted():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        configured_horizon_steps=6,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_n1", 1, baseline_arrival_timestep=16),),
            ),
        ),
    )
    result = _confirm(
        arrived_result,
        {"merge": rank_state},
        _participation_mapping((("veh_n1", 1), False)),
    )
    assert result.node_confirmation_results[0].decision_window_visit_keys == (
        ("veh_n1", 1),
    )


def test_decision_window_boundary_excludes_T_includes_T_plus_one_and_six_excludes_T_plus_seven():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_at_t", 1),
        ("veh_t1", 2),
        ("veh_t6", 3),
        ("veh_t7", 4),
    )
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_at_t", 1, baseline_arrival_timestep=10),
                    _resolved("veh_t1", 2, baseline_arrival_timestep=11),
                    _resolved("veh_t6", 3, baseline_arrival_timestep=16),
                    _resolved("veh_t7", 4, baseline_arrival_timestep=17),
                ),
            ),
        ),
    )
    participation = _participation_mapping(
        (("veh_at_t", 1), False),
        (("veh_t1", 2), False),
        (("veh_t6", 3), False),
        (("veh_t7", 4), False),
    )
    result = _confirm(arrived_result, {"merge": rank_state}, participation)
    assert result.node_confirmation_results[0].decision_window_visit_keys == (
        ("veh_t1", 2),
        ("veh_t6", 3),
    )


def test_zero_decision_window_visits_calls_empty_confirm_and_empty_remaining():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_arrived", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_arrived", 1, baseline_arrival_timestep=10),),
            ),
        ),
    )
    confirm_count = 0
    original_confirm = rank_state.confirm_visits_in_order

    def counting_confirm(visit_keys_in_order):
        nonlocal confirm_count
        confirm_count += 1
        return original_confirm(visit_keys_in_order)

    rank_state.confirm_visits_in_order = counting_confirm  # type: ignore[method-assign]
    result = _confirm(arrived_result, {"merge": rank_state}, {})
    assert confirm_count == 1
    node_result = result.node_confirmation_results[0]
    assert node_result.decision_window_visit_keys == ()
    assert node_result.confirmed_leading_nonparticipating_visit_keys == ()
    assert node_result.remaining_decision_window_visit_keys == ()
    assert node_result.confirm_result.newly_confirmed_count == 0


def test_leading_participant_or_all_participant_confirms_empty_and_keeps_full_remaining():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_p1", 1), ("veh_p2", 2), ("veh_n3", 3))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_p1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_p2", 2, baseline_arrival_timestep=12),
                    _resolved("veh_n3", 3, baseline_arrival_timestep=13),
                ),
            ),
        ),
    )
    participation = _participation_mapping(
        (("veh_p1", 1), True),
        (("veh_p2", 2), True),
        (("veh_n3", 3), False),
    )
    result = _confirm(arrived_result, {"merge": rank_state}, participation)
    node_result = result.node_confirmation_results[0]
    assert node_result.confirmed_leading_nonparticipating_visit_keys == ()
    assert node_result.remaining_decision_window_visit_keys == (
        ("veh_p1", 1),
        ("veh_p2", 2),
        ("veh_n3", 3),
    )
    assert rank_state.is_undetermined(("veh_p1", 1))


def test_leading_nonparticipating_prefix_and_n_p_n_pattern():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1), ("veh_p1", 2), ("veh_n3", 3))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_p1", 2, baseline_arrival_timestep=12),
                    _resolved("veh_n3", 3, baseline_arrival_timestep=13),
                ),
            ),
        ),
    )
    participation = _participation_mapping(
        (("veh_n1", 1), False),
        (("veh_p1", 2), True),
        (("veh_n3", 3), False),
    )
    result = _confirm(arrived_result, {"merge": rank_state}, participation)
    node_result = result.node_confirmation_results[0]
    assert node_result.confirmed_leading_nonparticipating_visit_keys == (("veh_n1", 1),)
    assert node_result.remaining_decision_window_visit_keys == (
        ("veh_p1", 2),
        ("veh_n3", 3),
    )
    assert rank_state.is_confirmed(("veh_n1", 1))
    assert rank_state.is_undetermined(("veh_n3", 3))


def test_institutional_example_n_n_p_p_n_p_n_p_p():
    rank_state = _new_rank_state("merge")
    visit_specs = [
        ("veh_n1", 1, 11, False),
        ("veh_n2", 2, 12, False),
        ("veh_p1", 3, 13, True),
        ("veh_p2", 4, 14, True),
        ("veh_n5", 5, 15, False),
        ("veh_p3", 6, 16, True),
        ("veh_n7", 7, 17, False),
        ("veh_p4", 8, 18, True),
        ("veh_p5", 9, 19, True),
    ]
    resolved = tuple(
        _resolved(name, vid, baseline_arrival_timestep=ts)
        for name, vid, ts, _ in visit_specs
    )
    _register_undetermined(rank_state, *((name, vid) for name, vid, _, _ in visit_specs))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge", resolved=resolved),),
    )
    participation = _participation_mapping(
        *(((name, vid), participates) for name, vid, _, participates in visit_specs)
    )
    result = _confirm(arrived_result, {"merge": rank_state}, participation)
    node_result = result.node_confirmation_results[0]
    assert node_result.confirmed_leading_nonparticipating_visit_keys == (
        ("veh_n1", 1),
        ("veh_n2", 2),
    )
    assert node_result.remaining_decision_window_visit_keys[0] == ("veh_p1", 3)
    assert rank_state.is_undetermined(("veh_n5", 5))


def test_all_nonparticipating_confirms_all_and_empty_remaining():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1), ("veh_n2", 2), ("veh_n3", 3))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_n2", 2, baseline_arrival_timestep=12),
                    _resolved("veh_n3", 3, baseline_arrival_timestep=13),
                ),
            ),
        ),
    )
    participation = _participation_mapping(
        (("veh_n1", 1), False),
        (("veh_n2", 2), False),
        (("veh_n3", 3), False),
    )
    result = _confirm(arrived_result, {"merge": rank_state}, participation)
    node_result = result.node_confirmation_results[0]
    assert node_result.confirmed_leading_nonparticipating_visit_keys == (
        ("veh_n1", 1),
        ("veh_n2", 2),
        ("veh_n3", 3),
    )
    assert node_result.remaining_decision_window_visit_keys == ()
    assert rank_state.undetermined_visit_keys() == frozenset()


def test_preserves_resolved_order_not_vehicle_name_sort():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_z", 9),
        ("veh_a", 1),
        ("veh_m", 5),
    )
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved(
                        "veh_m",
                        5,
                        baseline_arrival_timestep=11,
                        arrival_tiebreaker=0.1,
                        vehicle_id=2,
                    ),
                    _resolved(
                        "veh_z",
                        9,
                        baseline_arrival_timestep=11,
                        arrival_tiebreaker=0.2,
                        vehicle_id=3,
                    ),
                    _resolved(
                        "veh_a",
                        1,
                        baseline_arrival_timestep=12,
                        arrival_tiebreaker=0.1,
                        vehicle_id=0,
                    ),
                ),
            ),
        ),
    )
    participation = _participation_mapping(
        (("veh_m", 5), False),
        (("veh_z", 9), False),
        (("veh_a", 1), True),
    )
    result = _confirm(arrived_result, {"merge": rank_state}, participation)
    node_result = result.node_confirmation_results[0]
    assert node_result.decision_window_visit_keys == (
        ("veh_m", 5),
        ("veh_z", 9),
        ("veh_a", 1),
    )
    assert node_result.confirmed_leading_nonparticipating_visit_keys == (
        ("veh_m", 5),
        ("veh_z", 9),
    )


def test_participation_mapping_missing_nonbool_and_integer_rejected():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_n1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    _expect_value_error(
        lambda: _confirm(arrived_result, {"merge": rank_state}, {}),
        "missing decision-window VisitKey ('veh_n1', 1)",
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            {("veh_n1", 1): 1},
        ),
        "must be a Python bool",
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            {("veh_n1", 1): "True"},
        ),
        "must be a Python bool",
    )


def test_trailing_decision_window_visit_mapping_is_validated():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1), ("veh_p1", 2), ("veh_n3", 3))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_p1", 2, baseline_arrival_timestep=12),
                    _resolved("veh_n3", 3, baseline_arrival_timestep=13),
                ),
            ),
        ),
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            {("veh_n1", 1): False, ("veh_p1", 2): True},
        ),
        "missing decision-window VisitKey ('veh_n3', 3)",
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            {
                ("veh_n1", 1): False,
                ("veh_p1", 2): True,
                ("veh_n3", 3): 0,
            },
        ),
        "must be a Python bool",
    )


def test_out_of_window_and_unresolved_mapping_gaps_are_not_validated():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_n1", 1, baseline_arrival_timestep=11),),
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    _confirm(
        arrived_result,
        {"merge": rank_state},
        {("veh_n1", 1): False},
    )


def test_node_revisit_uses_distinct_visit_keys():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_a", 1), ("veh_a", 2))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_a", 1, baseline_arrival_timestep=11),
                    _resolved("veh_a", 2, baseline_arrival_timestep=12),
                ),
            ),
        ),
    )
    result = _confirm(
        arrived_result,
        {"merge": rank_state},
        {("veh_a", 1): False, ("veh_a", 2): True},
    )
    assert result.node_confirmation_results[0].confirmed_leading_nonparticipating_visit_keys == (
        ("veh_a", 1),
    )


def test_appends_after_existing_arrived_confirmed_block():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_arrived", 1), ("veh_n1", 2))
    rank_state.confirm_visits_in_order((("veh_arrived", 1),))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_arrived", 1, baseline_arrival_timestep=10),
                    _resolved("veh_n1", 2, baseline_arrival_timestep=11),
                ),
            ),
        ),
    )
    _confirm(
        arrived_result,
        {"merge": rank_state},
        {("veh_n1", 2): False},
    )
    assert rank_state.confirmed_visit_keys_in_order() == (
        ("veh_arrived", 1),
        ("veh_n1", 2),
    )
    assert rank_state.assigned_rank(("veh_n1", 2)) == 2


def test_unresolved_non_empty_still_confirms_leading_nonparticipating():
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_n1", 1),
        ("veh_unresolved", 9),
    )
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_n1", 1, baseline_arrival_timestep=11),),
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    result = _confirm(
        arrived_result,
        {"merge": rank_state},
        {("veh_n1", 1): False},
    )
    assert rank_state.is_confirmed(("veh_n1", 1))
    assert rank_state.is_undetermined(("veh_unresolved", 9))


def test_multi_node_processes_in_target_node_order():
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    _register_undetermined(rank_state_a, ("veh_n_a", 1))
    _register_undetermined(rank_state_b, ("veh_n_b", 2))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("node_a", "node_b"),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "node_a",
                resolved=(_resolved("veh_n_a", 1, baseline_arrival_timestep=11),),
            ),
            _alignment_result(
                "node_b",
                resolved=(_resolved("veh_n_b", 2, baseline_arrival_timestep=12),),
            ),
        ),
    )
    confirm_events: list[str] = []
    original_confirm_a = rank_state_a.confirm_visits_in_order
    original_confirm_b = rank_state_b.confirm_visits_in_order

    def tracking_confirm_a(visit_keys_in_order):
        confirm_events.append("node_a")
        return original_confirm_a(visit_keys_in_order)

    def tracking_confirm_b(visit_keys_in_order):
        confirm_events.append("node_b")
        return original_confirm_b(visit_keys_in_order)

    rank_state_a.confirm_visits_in_order = tracking_confirm_a  # type: ignore[method-assign]
    rank_state_b.confirm_visits_in_order = tracking_confirm_b  # type: ignore[method-assign]
    result = _confirm(
        arrived_result,
        {"node_a": rank_state_a, "node_b": rank_state_b},
        {
            ("veh_n_a", 1): False,
            ("veh_n_b", 2): False,
        },
    )
    assert confirm_events == ["node_a", "node_b"]
    assert [item.node_name for item in result.node_confirmation_results] == [
        "node_a",
        "node_b",
    ]


def test_alignment_node_name_mismatch_raises_before_confirm():
    rank_state = _new_rank_state("merge")
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("wrong_name"),),
    )
    confirm_count = 0
    original_confirm = rank_state.confirm_visits_in_order

    def counting_confirm(visit_keys_in_order):
        nonlocal confirm_count
        confirm_count += 1
        return original_confirm(visit_keys_in_order)

    rank_state.confirm_visits_in_order = counting_confirm  # type: ignore[method-assign]
    _expect_runtime_error(
        lambda: _confirm(arrived_result, {"merge": rank_state}, {}),
        "expected target_node_names entry 'merge'",
    )
    _expect_runtime_error(
        lambda: _confirm(arrived_result, {"merge": rank_state}, {}),
        "alignment result has 'wrong_name'",
    )
    assert confirm_count == 0


def test_arrived_node_name_mismatch_raises_before_confirm():
    rank_state = _new_rank_state("merge")
    fork_result = _fork_result(target_node_names=("merge",), baseline_timestep_T=10)
    alignment_fork_result = OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=(_alignment_result("merge"),),
    )
    arrived_result = OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment_fork_result,
        node_confirmation_results=(
            OrderControlTvtNodeArrivedUndeterminedConfirmationResult(
                node_name="wrong_name",
                confirmed_arrived_visit_keys=(),
                confirm_result=OrderControlTvtConfirmResult(0, 0, 0),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: _confirm(arrived_result, {"merge": rank_state}, {}),
        "arrived confirmation result has 'wrong_name'",
    )


def test_mid_failure_preserves_prior_node_and_skips_later_nodes():
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    rank_state_c = _new_rank_state("node_c")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2))
    _register_undetermined(rank_state_c, ("veh_c", 3))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("node_a", "node_b", "node_c"),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "node_a",
                resolved=(_resolved("veh_a", 1, baseline_arrival_timestep=11),),
            ),
            _alignment_result(
                "node_b",
                resolved=(_resolved("veh_b", 2, baseline_arrival_timestep=12),),
            ),
            _alignment_result(
                "node_c",
                resolved=(_resolved("veh_c", 3, baseline_arrival_timestep=13),),
            ),
        ),
    )
    original_confirm_b = rank_state_b.confirm_visits_in_order

    def fail_confirm_b(visit_keys_in_order):
        raise ValueError("confirm failed on node_b")

    rank_state_b.confirm_visits_in_order = fail_confirm_b  # type: ignore[method-assign]
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {
                "node_a": rank_state_a,
                "node_b": rank_state_b,
                "node_c": rank_state_c,
            },
            {
                ("veh_a", 1): False,
                ("veh_b", 2): False,
                ("veh_c", 3): False,
            },
        ),
        "confirm failed on node_b",
    )
    assert rank_state_a.is_confirmed(("veh_a", 1))
    assert rank_state_b.is_undetermined(("veh_b", 2))
    assert rank_state_c.is_undetermined(("veh_c", 3))


def test_confirm_api_errors_propagate_without_partial_result():
    rank_state = _new_rank_state("merge")
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_missing", 9, baseline_arrival_timestep=11),),
            ),
        ),
    )
    _expect_value_error(
        lambda: _confirm(
            arrived_result,
            {"merge": rank_state},
            {("veh_missing", 9): False},
        ),
        "not pre-registered",
    )


def test_does_not_rerun_upstream_processing():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_n1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    with patch(
        "uxsim.order_control_tvt_arrived_undetermined_confirmation."
        "confirm_already_arrived_undetermined_visits",
    ) as patched_arrived, patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
    ) as patched_align, patch(
        "uxsim.order_control_baseline_driver."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
    ) as patched_fork:
        _confirm(
            arrived_result,
            {"merge": rank_state},
            {("veh_n1", 1): False},
        )
        patched_arrived.assert_not_called()
        patched_align.assert_not_called()
        patched_fork.assert_not_called()


def test_existing_result_types_remain_unchanged():
    arrived_fields = {
        field.name
        for field in dataclasses.fields(OrderControlTvtArrivedUndeterminedConfirmationResult)
    }
    assert arrived_fields == {
        "alignment_fork_result",
        "node_confirmation_results",
    }
    rank_state = _new_rank_state("merge")
    assert hasattr(rank_state, "confirm_visits_in_order")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
