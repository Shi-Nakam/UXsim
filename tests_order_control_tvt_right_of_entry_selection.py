# Unit tests for right-of-entry visit selection after leading non-participating
# confirmation (design memo §25.25.34.42).
#
# Run from the repository root:
#   python tests_order_control_tvt_right_of_entry_selection.py
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
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionStatus,
    select_right_of_entry_decision_window_visits,
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
        inlink_physical_orders=(),
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


def _leading_confirmation_via_pipeline(
    arrived_result: OrderControlTvtArrivedUndeterminedConfirmationResult,
    rank_states_by_node_name: dict[str, OrderControlTvtNodeRankState],
    participates_by_visit_key: dict[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtLeadingNonparticipatingConfirmationResult:
    return confirm_leading_nonparticipating_decision_window_visits(
        arrived_result,
        rank_states_by_node_name=rank_states_by_node_name,
        participates_by_visit_key=participates_by_visit_key,
    )


def _manual_leading_node_result(
    node_name: str,
    *,
    decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...] = (),
    confirmed_leading_nonparticipating_visit_keys: tuple[
        OrderControlTvtVisitKey,
        ...
    ] = (),
    remaining_decision_window_visit_keys: tuple[OrderControlTvtVisitKey, ...] = (),
) -> OrderControlTvtNodeLeadingNonparticipatingConfirmationResult:
    return OrderControlTvtNodeLeadingNonparticipatingConfirmationResult(
        node_name=node_name,
        decision_window_visit_keys=decision_window_visit_keys,
        confirmed_leading_nonparticipating_visit_keys=(
            confirmed_leading_nonparticipating_visit_keys
        ),
        remaining_decision_window_visit_keys=remaining_decision_window_visit_keys,
        confirm_result=OrderControlTvtConfirmResult(
            k_confirmed_before=0,
            k_confirmed_after=0,
            newly_confirmed_count=0,
        ),
    )


def _manual_leading_confirmation_result(
    arrived_result: OrderControlTvtArrivedUndeterminedConfirmationResult,
    leading_node_results: tuple[
        OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
        ...
    ],
) -> OrderControlTvtLeadingNonparticipatingConfirmationResult:
    return OrderControlTvtLeadingNonparticipatingConfirmationResult(
        arrived_confirmation_result=arrived_result,
        node_confirmation_results=leading_node_results,
    )


def _select(
    leading_result: OrderControlTvtLeadingNonparticipatingConfirmationResult,
    rank_states_by_node_name: dict[str, OrderControlTvtNodeRankState],
    participates_by_visit_key: dict[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtRightOfEntrySelectionResult:
    return select_right_of_entry_decision_window_visits(
        leading_result,
        rank_states_by_node_name=rank_states_by_node_name,
        participates_by_visit_key=participates_by_visit_key,
    )


def _rank_state_snapshot(
    state: OrderControlTvtNodeRankState,
) -> tuple[int, tuple[OrderControlTvtVisitKey, ...], frozenset[OrderControlTvtVisitKey]]:
    return (
        state.k_confirmed(),
        state.confirmed_visit_keys_in_order(),
        state.undetermined_visit_keys(),
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


def test_enum_and_result_types_are_frozen():
    assert list(OrderControlTvtRightOfEntrySelectionStatus) == [
        OrderControlTvtRightOfEntrySelectionStatus.SELECTED,
        OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY,
        OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS,
    ]
    assert dataclasses.is_dataclass(OrderControlTvtNodeRightOfEntrySelectionResult)
    assert dataclasses.is_dataclass(OrderControlTvtRightOfEntrySelectionResult)
    node_fields = {
        field.name
        for field in dataclasses.fields(OrderControlTvtNodeRightOfEntrySelectionResult)
    }
    assert node_fields == {
        "node_name",
        "selection_status",
        "right_of_entry_visit_key",
        "k_confirmed_before",
    }
    assert "remaining_decision_window_visit_keys" not in node_fields
    assert "decision_window_visit_keys" not in node_fields
    assert "unresolved_undetermined_visits" not in node_fields


def test_selected_when_unresolved_empty_and_remaining_nonempty():
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
    participation = _participation_mapping(
        (("veh_n1", 1), False),
        (("veh_p1", 2), True),
    )
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    result = _select(leading_result, {"merge": rank_state}, participation)
    node_result = result.node_selection_results[0]
    assert node_result.selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.SELECTED
    )
    assert node_result.right_of_entry_visit_key == ("veh_p1", 2)
    assert result.leading_confirmation_result is leading_result


def test_institutional_example_selects_remaining_head_participant():
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
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    result = _select(leading_result, {"merge": rank_state}, participation)
    node_result = result.node_selection_results[0]
    assert node_result.selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.SELECTED
    )
    assert node_result.right_of_entry_visit_key == ("veh_p1", 3)
    assert rank_state.is_undetermined(("veh_n5", 5))
    assert rank_state.is_undetermined(("veh_p4", 8))


def test_does_not_select_trailing_visits():
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
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    result = _select(leading_result, {"merge": rank_state}, participation)
    assert result.node_selection_results[0].right_of_entry_visit_key == ("veh_p1", 2)


def test_no_right_of_entry_when_remaining_empty_via_manual_result():
    rank_state = _new_rank_state("merge")
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge"),),
    )
    leading_result = _manual_leading_confirmation_result(
        arrived_result,
        (
            _manual_leading_node_result(
                "merge",
                decision_window_visit_keys=(),
                remaining_decision_window_visit_keys=(),
            ),
        ),
    )
    result = _select(leading_result, {"merge": rank_state}, {})
    node_result = result.node_selection_results[0]
    assert node_result.selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY
    )
    assert node_result.right_of_entry_visit_key is None


def test_no_right_of_entry_zero_decision_window_and_all_nonparticipating():
    rank_state_empty = _new_rank_state("merge")
    arrived_empty = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge"),),
    )
    leading_empty = _leading_confirmation_via_pipeline(
        arrived_empty,
        {"merge": rank_state_empty},
        {},
    )
    result_empty = _select(leading_empty, {"merge": rank_state_empty}, {})
    assert result_empty.node_selection_results[0].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY
    )
    assert leading_empty.node_confirmation_results[0].decision_window_visit_keys == ()

    rank_state_all_n = _new_rank_state("merge")
    _register_undetermined(rank_state_all_n, ("veh_n1", 1), ("veh_n2", 2))
    arrived_all_n = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_n2", 2, baseline_arrival_timestep=12),
                ),
            ),
        ),
    )
    participation_all_n = _participation_mapping(
        (("veh_n1", 1), False),
        (("veh_n2", 2), False),
    )
    leading_all_n = _leading_confirmation_via_pipeline(
        arrived_all_n,
        {"merge": rank_state_all_n},
        participation_all_n,
    )
    result_all_n = _select(
        leading_all_n,
        {"merge": rank_state_all_n},
        participation_all_n,
    )
    assert result_all_n.node_selection_results[0].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY
    )
    assert leading_all_n.node_confirmation_results[0].decision_window_visit_keys != ()


def test_unresolved_cases_and_priority_over_remaining():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_p1", 1))
    arrived_nonempty = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_p1", 1, baseline_arrival_timestep=11),),
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    participation = {("veh_p1", 1): True}
    leading_nonempty = _manual_leading_confirmation_result(
        arrived_nonempty,
        (
            _manual_leading_node_result(
                "merge",
                decision_window_visit_keys=(("veh_p1", 1),),
                remaining_decision_window_visit_keys=(("veh_p1", 1),),
            ),
        ),
    )
    result_nonempty = _select(
        leading_nonempty,
        {"merge": rank_state},
        participation,
    )
    assert result_nonempty.node_selection_results[0].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS
    )
    assert result_nonempty.node_selection_results[0].right_of_entry_visit_key is None

    rank_state_empty = _new_rank_state("merge")
    arrived_empty = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    leading_empty = _manual_leading_confirmation_result(
        arrived_empty,
        (
            _manual_leading_node_result(
                "merge",
                decision_window_visit_keys=(),
                remaining_decision_window_visit_keys=(),
            ),
        ),
    )
    result_empty = _select(leading_empty, {"merge": rank_state_empty}, {})
    assert result_empty.node_selection_results[0].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS
    )


def test_multi_node_unresolved_on_one_node_other_selected():
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    _register_undetermined(rank_state_a, ("veh_p_a", 1))
    _register_undetermined(rank_state_b, ("veh_n_b", 2), ("veh_p_b", 3))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("node_a", "node_b"),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "node_a",
                resolved=(_resolved("veh_p_a", 1, baseline_arrival_timestep=11),),
                unresolved=(("veh_unresolved_a", 9),),
            ),
            _alignment_result(
                "node_b",
                resolved=(
                    _resolved("veh_n_b", 2, baseline_arrival_timestep=12),
                    _resolved("veh_p_b", 3, baseline_arrival_timestep=13),
                ),
            ),
        ),
    )
    participation_b = _participation_mapping(
        (("veh_n_b", 2), False),
        (("veh_p_b", 3), True),
    )
    leading_a = _manual_leading_node_result(
        "node_a",
        decision_window_visit_keys=(("veh_p_a", 1),),
        remaining_decision_window_visit_keys=(("veh_p_a", 1),),
    )
    leading_b = _leading_confirmation_via_pipeline(
        _arrived_confirmation_result(
            target_node_names=("node_b",),
            baseline_timestep_T=10,
            alignment_results=(arrived_result.alignment_fork_result.alignment_results[1],),
        ),
        {"node_b": rank_state_b},
        participation_b,
    ).node_confirmation_results[0]
    leading_result = _manual_leading_confirmation_result(
        arrived_result,
        (leading_a, leading_b),
    )
    result = _select(
        leading_result,
        {"node_a": rank_state_a, "node_b": rank_state_b},
        participation_b,
    )
    assert [item.node_name for item in result.node_selection_results] == [
        "node_a",
        "node_b",
    ]
    assert result.node_selection_results[0].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS
    )
    assert result.node_selection_results[1].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.SELECTED
    )
    assert result.node_selection_results[1].right_of_entry_visit_key == ("veh_p_b", 3)


def test_selection_status_invariant_on_right_of_entry_visit_key():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_p1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_p1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    participation = {("veh_p1", 1): True}
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    selected = _select(leading_result, {"merge": rank_state}, participation)
    assert selected.node_selection_results[0].right_of_entry_visit_key is not None

    arrived_unresolved = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    leading_unresolved = _manual_leading_confirmation_result(
        arrived_unresolved,
        (_manual_leading_node_result("merge"),),
    )
    unresolved = _select(leading_unresolved, {"merge": rank_state}, {})
    assert unresolved.node_selection_results[0].right_of_entry_visit_key is None

    arrived_empty = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge"),),
    )
    leading_empty = _leading_confirmation_via_pipeline(
        arrived_empty,
        {"merge": rank_state},
        {},
    )
    no_entry = _select(leading_empty, {"merge": rank_state}, {})
    assert no_entry.node_selection_results[0].right_of_entry_visit_key is None


def test_participation_validation_only_when_selecting():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_p1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_p1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        {("veh_p1", 1): True},
    )
    _expect_value_error(
        lambda: _select(leading_result, {"merge": rank_state}, {}),
        "missing right-of-entry candidate VisitKey ('veh_p1', 1)",
    )
    _expect_value_error(
        lambda: _select(
            leading_result,
            {"merge": rank_state},
            {("veh_p1", 1): 1},
        ),
        "must be a Python bool",
    )
    _expect_value_error(
        lambda: _select(
            leading_result,
            {"merge": rank_state},
            {("veh_p1", 1): "True"},
        ),
        "must be a Python bool",
    )

    arrived_unresolved = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    leading_unresolved = _manual_leading_confirmation_result(
        arrived_unresolved,
        (_manual_leading_node_result("merge"),),
    )
    _select(leading_unresolved, {"merge": rank_state}, {})

    arrived_empty = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge"),),
    )
    leading_empty = _leading_confirmation_via_pipeline(
        arrived_empty,
        {"merge": rank_state},
        {},
    )
    _select(leading_empty, {"merge": rank_state}, {})


def test_remaining_head_false_runtime_error_without_skipping():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_n1", 1), ("veh_p2", 2))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 1, baseline_arrival_timestep=11),
                    _resolved("veh_p2", 2, baseline_arrival_timestep=12),
                ),
            ),
        ),
    )
    leading_result = _manual_leading_confirmation_result(
        arrived_result,
        (
            _manual_leading_node_result(
                "merge",
                decision_window_visit_keys=(("veh_n1", 1), ("veh_p2", 2)),
                remaining_decision_window_visit_keys=(("veh_n1", 1), ("veh_p2", 2)),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: _select(
            leading_result,
            {"merge": rank_state},
            {("veh_n1", 1): False, ("veh_p2", 2): True},
        ),
        "remaining_decision_window_visit_keys head must be a participating Visit",
    )


def test_rank_state_validation_for_candidate():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_p1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_p1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    participation = {("veh_p1", 1): True}
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    result = _select(leading_result, {"merge": rank_state}, participation)
    assert result.node_selection_results[0].selection_status == (
        OrderControlTvtRightOfEntrySelectionStatus.SELECTED
    )

    rank_state_confirmed = _new_rank_state("merge")
    _register_undetermined(rank_state_confirmed, ("veh_p1", 1))
    rank_state_confirmed.confirm_visits_in_order((("veh_p1", 1),))
    leading_confirmed = _manual_leading_confirmation_result(
        arrived_result,
        (
            _manual_leading_node_result(
                "merge",
                remaining_decision_window_visit_keys=(("veh_p1", 1),),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: _select(
            leading_confirmed,
            {"merge": rank_state_confirmed},
            participation,
        ),
        "already confirmed",
    )

    rank_state_missing = _new_rank_state("merge")
    leading_missing = _manual_leading_confirmation_result(
        arrived_result,
        (
            _manual_leading_node_result(
                "merge",
                remaining_decision_window_visit_keys=(("veh_p1", 1),),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: _select(
            leading_missing,
            {"merge": rank_state_missing},
            participation,
        ),
        "not pre-registered",
    )


def test_k_confirmed_before_from_current_rank_state_all_statuses():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_arrived", 1), ("veh_n1", 2), ("veh_p1", 3))
    rank_state.confirm_visits_in_order((("veh_arrived", 1),))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(
                    _resolved("veh_n1", 2, baseline_arrival_timestep=11),
                    _resolved("veh_p1", 3, baseline_arrival_timestep=12),
                ),
            ),
        ),
    )
    participation = _participation_mapping(
        (("veh_n1", 2), False),
        (("veh_p1", 3), True),
    )
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    selected = _select(leading_result, {"merge": rank_state}, participation)
    assert selected.node_selection_results[0].k_confirmed_before == 2
    assert rank_state.k_confirmed() == 2

    rank_state_zero = _new_rank_state("merge")
    arrived_empty = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge"),),
    )
    leading_empty = _leading_confirmation_via_pipeline(
        arrived_empty,
        {"merge": rank_state_zero},
        {},
    )
    no_entry = _select(leading_empty, {"merge": rank_state_zero}, {})
    assert no_entry.node_selection_results[0].k_confirmed_before == 0

    rank_state_unresolved = _new_rank_state("merge")
    arrived_unresolved = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                unresolved=(("veh_unresolved", 9),),
            ),
        ),
    )
    leading_unresolved = _manual_leading_confirmation_result(
        arrived_unresolved,
        (_manual_leading_node_result("merge"),),
    )
    unresolved = _select(leading_unresolved, {"merge": rank_state_unresolved}, {})
    assert unresolved.node_selection_results[0].k_confirmed_before == 0


def test_node_name_mismatch_and_failure_stops_later_nodes():
    rank_state = _new_rank_state("merge")
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("wrong_alignment"),),
    )
    leading_result = _manual_leading_confirmation_result(
        arrived_result,
        (_manual_leading_node_result("merge"),),
    )
    _expect_runtime_error(
        lambda: _select(leading_result, {"merge": rank_state}, {}),
        "alignment result has 'wrong_alignment'",
    )

    arrived_result2 = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(_alignment_result("merge"),),
    )
    leading_result2 = _manual_leading_confirmation_result(
        arrived_result2,
        (_manual_leading_node_result("wrong_leading"),),
    )
    _expect_runtime_error(
        lambda: _select(leading_result2, {"merge": rank_state}, {}),
        "leading confirmation result has 'wrong_leading'",
    )

    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    rank_state_c = _new_rank_state("node_c")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2))
    _register_undetermined(rank_state_c, ("veh_c", 3))
    arrived_multi = _arrived_confirmation_result(
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
    participation = _participation_mapping(
        (("veh_a", 1), True),
        (("veh_b", 2), True),
        (("veh_c", 3), True),
        (("veh_missing", 99), True),
    )
    leading_a = _leading_confirmation_via_pipeline(
        _arrived_confirmation_result(
            target_node_names=("node_a",),
            baseline_timestep_T=10,
            alignment_results=(arrived_multi.alignment_fork_result.alignment_results[0],),
        ),
        {"node_a": rank_state_a},
        {("veh_a", 1): True},
    ).node_confirmation_results[0]
    leading_b = _manual_leading_node_result(
        "node_b",
        remaining_decision_window_visit_keys=(("veh_missing", 99),),
    )
    leading_c = _manual_leading_node_result(
        "node_c",
        remaining_decision_window_visit_keys=(("veh_c", 3),),
    )
    leading_multi = _manual_leading_confirmation_result(
        arrived_multi,
        (leading_a, leading_b, leading_c),
    )
    _expect_runtime_error(
        lambda: _select(
            leading_multi,
            {
                "node_a": rank_state_a,
                "node_b": rank_state_b,
                "node_c": rank_state_c,
            },
            participation,
        ),
        "not pre-registered",
    )
    assert rank_state_a.is_undetermined(("veh_a", 1))
    assert rank_state_c.is_undetermined(("veh_c", 3))


def test_read_only_and_no_upstream_rerun():
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_p1", 1))
    arrived_result = _arrived_confirmation_result(
        target_node_names=("merge",),
        baseline_timestep_T=10,
        alignment_results=(
            _alignment_result(
                "merge",
                resolved=(_resolved("veh_p1", 1, baseline_arrival_timestep=11),),
            ),
        ),
    )
    participation = {("veh_p1", 1): True}
    leading_result = _leading_confirmation_via_pipeline(
        arrived_result,
        {"merge": rank_state},
        participation,
    )
    before = _rank_state_snapshot(rank_state)
    original_confirm = rank_state.confirm_visits_in_order
    confirm_called = False

    def tracking_confirm(visit_keys_in_order):
        nonlocal confirm_called
        confirm_called = True
        return original_confirm(visit_keys_in_order)

    rank_state.confirm_visits_in_order = tracking_confirm  # type: ignore[method-assign]
    with patch(
        "uxsim.order_control_tvt_leading_nonparticipating_confirmation."
        "confirm_leading_nonparticipating_decision_window_visits",
    ) as patched_leading, patch(
        "uxsim.order_control_tvt_arrived_undetermined_confirmation."
        "confirm_already_arrived_undetermined_visits",
    ) as patched_arrived, patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
    ) as patched_align:
        _select(leading_result, {"merge": rank_state}, participation)
        patched_leading.assert_not_called()
        patched_arrived.assert_not_called()
        patched_align.assert_not_called()
    assert confirm_called is False
    assert _rank_state_snapshot(rank_state) == before


def test_existing_result_types_remain_unchanged():
    leading_fields = {
        field.name
        for field in dataclasses.fields(OrderControlTvtLeadingNonparticipatingConfirmationResult)
    }
    assert leading_fields == {
        "arrived_confirmation_result",
        "node_confirmation_results",
    }
    rank_state = _new_rank_state("merge")
    assert hasattr(rank_state, "is_undetermined")
    assert hasattr(rank_state, "is_confirmed")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
