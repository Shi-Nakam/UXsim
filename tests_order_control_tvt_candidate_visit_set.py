# Unit tests for TVT candidate visit set construction after right-of-entry
# selection (design memo §25.25.34.46).
#
# Run from the repository root:
#   python tests_order_control_tvt_candidate_visit_set.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import patch

from uxsim import World
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
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
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
    build_tvt_candidate_visit_set,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
    OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
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


def _register_b_visit(
    collector: OrderControlBaselineCollector,
    *,
    vehicle_name: str,
    visit_id: int,
    vehicle_id: int,
    node_name: str = "merge",
    inlink_name: str = "in1",
    arrival: int,
    tiebreaker: int | float = 0.5,
    route_next_link_name: str = "out",
    passage: int | None = None,
) -> None:
    collector.register_snapshot_visit(
        vehicle_name=vehicle_name,
        vehicle_id=vehicle_id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )
    collector.record_baseline_arrival(
        vehicle_name=vehicle_name,
        visit_id=visit_id,
        node_name=node_name,
        baseline_arrival_timestep=arrival,
        arrival_tiebreaker=tiebreaker,
        route_next_link_name=route_next_link_name,
    )
    if passage is not None:
        record = collector._visit_records_by_primary_key[(vehicle_name, visit_id)]
        collector.apply_baseline_passage_timestep(record, passage)


def _register_a_visit(
    collector: OrderControlBaselineCollector,
    *,
    vehicle_name: str,
    visit_id: int,
    vehicle_id: int,
    node_name: str = "merge",
    inlink_name: str = "in1",
    arrival: int,
    tiebreaker: int | float = 0.5,
    route_next_link_name: str = "out",
    passage: int | None = None,
) -> None:
    collector.register_snapshot_visit(
        vehicle_name=vehicle_name,
        vehicle_id=vehicle_id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=arrival,
        arrival_tiebreaker=tiebreaker,
        route_next_link_name=route_next_link_name,
        baseline_passage_timestep=None,
    )
    if passage is not None:
        record = collector._visit_records_by_primary_key[(vehicle_name, visit_id)]
        collector.apply_baseline_passage_timestep(record, passage)


def _fork_result(
    *,
    collector: OrderControlBaselineCollector,
    target_node_names: tuple[str, ...],
    baseline_timestep_T: int = 10,
    configured_horizon_steps: int = 50,
) -> OrderControlBaselineForkResult:
    return OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=configured_horizon_steps,
        fork_steps_executed=configured_horizon_steps,
        final_fork_timestep=baseline_timestep_T + configured_horizon_steps,
        registered_visit_count=1,
        inlink_physical_orders=(),
    )


def _selection_result(
    *,
    collector: OrderControlBaselineCollector,
    target_node_names: tuple[str, ...],
    node_selection_results: tuple[OrderControlTvtNodeRightOfEntrySelectionResult, ...],
) -> OrderControlTvtRightOfEntrySelectionResult:
    fork_result = _fork_result(
        collector=collector,
        target_node_names=target_node_names,
    )
    alignment_fork_result = OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=tuple(
            OrderControlTvtSnapshotUndeterminedAlignmentResult(
                node_name=node_name,
                resolved_undetermined_visits=(),
                unresolved_undetermined_visits=(),
                unregistered_collector_visit_keys=(),
            )
            for node_name in target_node_names
        ),
    )
    arrived_result = OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment_fork_result,
        node_confirmation_results=tuple(
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
        ),
    )
    leading_result = OrderControlTvtLeadingNonparticipatingConfirmationResult(
        arrived_confirmation_result=arrived_result,
        node_confirmation_results=tuple(
            OrderControlTvtNodeLeadingNonparticipatingConfirmationResult(
                node_name=node_name,
                decision_window_visit_keys=(),
                confirmed_leading_nonparticipating_visit_keys=(),
                remaining_decision_window_visit_keys=(),
                confirm_result=OrderControlTvtConfirmResult(
                    k_confirmed_before=0,
                    k_confirmed_after=0,
                    newly_confirmed_count=0,
                ),
            )
            for node_name in target_node_names
        ),
    )
    return OrderControlTvtRightOfEntrySelectionResult(
        leading_confirmation_result=leading_result,
        node_selection_results=node_selection_results,
    )


def _selected_node(
    node_name: str,
    right_of_entry_visit_key: OrderControlTvtVisitKey,
    *,
    k_confirmed_before: int = 0,
) -> OrderControlTvtNodeRightOfEntrySelectionResult:
    return OrderControlTvtNodeRightOfEntrySelectionResult(
        node_name=node_name,
        selection_status=OrderControlTvtRightOfEntrySelectionStatus.SELECTED,
        right_of_entry_visit_key=right_of_entry_visit_key,
        k_confirmed_before=k_confirmed_before,
    )


def _not_built_node(
    node_name: str,
    selection_status: OrderControlTvtRightOfEntrySelectionStatus,
    *,
    k_confirmed_before: int = 0,
) -> OrderControlTvtNodeRightOfEntrySelectionResult:
    return OrderControlTvtNodeRightOfEntrySelectionResult(
        node_name=node_name,
        selection_status=selection_status,
        right_of_entry_visit_key=None,
        k_confirmed_before=k_confirmed_before,
    )


def _build(
    selection_result: OrderControlTvtRightOfEntrySelectionResult,
    rank_states_by_node_name: dict[str, OrderControlTvtNodeRankState],
    *,
    max_tvt_candidate_visit_count: int = 100,
) -> OrderControlTvtCandidateVisitSetResult:
    return build_tvt_candidate_visit_set(
        selection_result,
        rank_states_by_node_name=rank_states_by_node_name,
        max_tvt_candidate_visit_count=max_tvt_candidate_visit_count,
    )


def _collector_snapshot(collector: OrderControlBaselineCollector) -> dict:
    return {
        key: collector.get_baseline_visit_snapshot(key[0], key[1])
        for key in collector._visit_records_by_primary_key
    }


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


def _expect_value_error(test_callable) -> None:
    try:
        test_callable()
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def _register_p_minus_one_chain(
    collector: OrderControlBaselineCollector,
    rank_state: OrderControlTvtNodeRankState,
    *,
    p: int,
    visit_count: int,
    unresolved_rank: int | None = None,
    beyond_limit_bad_fields: bool = False,
) -> OrderControlTvtRightOfEntrySelectionResult:
    visit_keys: list[OrderControlTvtVisitKey] = []
    for index in range(visit_count):
        vehicle_name = f"veh_{index}"
        visit_id = index + 1
        visit_keys.append((vehicle_name, visit_id))
        arrival = 10 + index
        passage: int | None = p + index
        route_next_link_name = "out"
        if unresolved_rank is not None and index + 1 == unresolved_rank:
            passage = None
        if beyond_limit_bad_fields and index + 1 == visit_count:
            passage = None
        _register_b_visit(
            collector,
            vehicle_name=vehicle_name,
            visit_id=visit_id,
            vehicle_id=index + 1,
            arrival=arrival,
            tiebreaker=float(index) * 0.1,
            route_next_link_name=route_next_link_name,
            passage=passage,
        )
        if beyond_limit_bad_fields and index + 1 == visit_count:
            record = collector._visit_records_by_primary_key[(vehicle_name, visit_id)]
            record.baseline_passage_timestep = True  # type: ignore[assignment]
            record.route_next_link_name = None
    _register_undetermined(rank_state, *visit_keys)
    return _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", visit_keys[0]),),
    )


# --- tests ---


def test_enum_and_result_types_are_frozen():
    assert list(OrderControlTvtCandidateVisitSetStatus) == [
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE,
    ]
    assert dataclasses.is_dataclass(OrderControlTvtCandidateVisit)
    assert dataclasses.is_dataclass(OrderControlTvtNodeCandidateVisitSetResult)
    assert dataclasses.is_dataclass(OrderControlTvtCandidateVisitSetResult)
    for cls in (
        OrderControlTvtCandidateVisit,
        OrderControlTvtNodeCandidateVisitSetResult,
        OrderControlTvtCandidateVisitSetResult,
    ):
        assert dataclasses.is_dataclass(cls)
        for field in dataclasses.fields(cls):
            assert field.repr is not False
    assert {
        field.name
        for field in dataclasses.fields(OrderControlTvtNodeCandidateVisitSetResult)
    } == {
        "node_name",
        "build_status",
        "right_of_entry_visit_key",
        "right_of_entry_baseline_passage_timestep",
        "k_confirmed_before",
        "p_minus_one_eligible_visit_count_before_limit",
        "candidate_visits",
    }
    assert {
        field.name
        for field in dataclasses.fields(OrderControlTvtCandidateVisitSetResult)
    } == {
        "right_of_entry_selection_result",
        "max_tvt_candidate_visit_count",
        "node_candidate_set_results",
    }


def test_not_built_statuses_do_not_query_collector():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(
            _not_built_node(
                "merge",
                OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY,
            ),
        ),
    )
    with patch.object(
        collector,
        "get_baseline_visit_snapshot",
        wraps=collector.get_baseline_visit_snapshot,
    ) as get_snapshot, patch.object(
        collector,
        "export_node_baseline_visits",
        wraps=collector.export_node_baseline_visits,
    ) as export_node:
        result = _build(selection_result, {"merge": rank_state})
        get_snapshot.assert_not_called()
        export_node.assert_not_called()
    node_result = result.node_candidate_set_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
    )
    assert node_result.right_of_entry_visit_key is None
    assert node_result.right_of_entry_baseline_passage_timestep is None
    assert node_result.candidate_visits == ()
    assert node_result.p_minus_one_eligible_visit_count_before_limit is None
    assert result.max_tvt_candidate_visit_count == 100
    assert result.right_of_entry_selection_result is selection_result

    collector2 = OrderControlBaselineCollector()
    selection_result2 = _selection_result(
        collector=collector2,
        target_node_names=("merge",),
        node_selection_results=(
            _not_built_node(
                "merge",
                OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS,
            ),
        ),
    )
    with patch.object(
        collector2,
        "get_baseline_visit_snapshot",
        wraps=collector2.get_baseline_visit_snapshot,
    ) as get_snapshot2, patch.object(
        collector2,
        "export_node_baseline_visits",
        wraps=collector2.export_node_baseline_visits,
    ) as export_node2:
        result2 = _build(selection_result2, {"merge": rank_state})
        get_snapshot2.assert_not_called()
        export_node2.assert_not_called()
    assert result2.node_candidate_set_results[0].build_status == (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS
    )


def test_unresolved_right_of_entry_passage_and_no_export():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=10,
        arrival=12,
        passage=None,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    with patch.object(
        collector,
        "export_node_baseline_visits",
        wraps=collector.export_node_baseline_visits,
    ) as export_node:
        result = _build(selection_result, {"merge": rank_state})
        export_node.assert_not_called()
    node_result = result.node_candidate_set_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE
    )
    assert node_result.right_of_entry_visit_key == ("veh_roe", 1)
    assert node_result.right_of_entry_baseline_passage_timestep is None
    assert node_result.candidate_visits == ()
    assert node_result.p_minus_one_eligible_visit_count_before_limit is None


def test_baseline_information_complete_with_p_minus_one_boundary():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_roe", 1),
        ("veh_in", 2),
        ("veh_out", 3),
        ("veh_late", 4),
    )
    p = 15
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=10,
        arrival=12,
        tiebreaker=0.1,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_in",
        visit_id=2,
        vehicle_id=20,
        arrival=p - 1,
        tiebreaker=0.2,
        passage=p + 1,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_out",
        visit_id=3,
        vehicle_id=30,
        arrival=p,
        tiebreaker=0.3,
        passage=p + 2,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_late",
        visit_id=4,
        vehicle_id=40,
        arrival=20,
        tiebreaker=0.4,
        passage=p + 3,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(
            _selected_node("merge", ("veh_roe", 1), k_confirmed_before=3),
        ),
    )
    with patch.object(
        collector,
        "get_baseline_visit_snapshot",
        wraps=collector.get_baseline_visit_snapshot,
    ) as get_snapshot, patch.object(
        collector,
        "export_node_baseline_visits",
        wraps=collector.export_node_baseline_visits,
    ) as export_node:
        result = _build(selection_result, {"merge": rank_state})
        get_snapshot.assert_called_once_with("veh_roe", 1)
        export_node.assert_called_once_with("merge")
    node_result = result.node_candidate_set_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )
    assert node_result.right_of_entry_baseline_passage_timestep == p
    assert node_result.k_confirmed_before == 3
    assert [item.visit_key for item in node_result.candidate_visits] == [
        ("veh_roe", 1),
        ("veh_in", 2),
    ]
    assert node_result.candidate_visits[0].baseline_passage_timestep == p
    assert node_result.candidate_visits[1].baseline_passage_timestep == p + 1


def test_candidate_filtering_sorting_and_nonparticipant_inclusion():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_roe", 1),
        ("veh_b2", 2),
        ("veh_b3", 3),
        ("veh_b4", 4),
        ("veh_confirmed", 5),
    )
    rank_state.confirm_visits_in_order((("veh_confirmed", 5),))
    p = 18
    _register_a_visit(
        collector,
        vehicle_name="veh_a",
        visit_id=9,
        vehicle_id=99,
        arrival=10,
        passage=12,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=14,
        tiebreaker=0.5,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b2",
        visit_id=2,
        vehicle_id=2,
        arrival=16,
        tiebreaker=0.5,
        inlink_name="in2",
        passage=p + 1,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b3",
        visit_id=3,
        vehicle_id=3,
        arrival=16,
        tiebreaker=0.1,
        inlink_name="in3",
        passage=p + 2,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b4",
        visit_id=4,
        vehicle_id=4,
        arrival=25,
        tiebreaker=0.0,
        passage=p + 3,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_confirmed",
        visit_id=5,
        vehicle_id=5,
        arrival=15,
        passage=p + 4,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    result = _build(selection_result, {"merge": rank_state})
    node_result = result.node_candidate_set_results[0]
    assert [item.visit_key for item in node_result.candidate_visits] == [
        ("veh_roe", 1),
        ("veh_b3", 3),
        ("veh_b2", 2),
    ]
    assert node_result.candidate_visits[1].inlink_name == "in3"


def test_unresolved_candidate_passages_keeps_full_candidate_set():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_other", 2))
    p = 14
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_other",
        visit_id=2,
        vehicle_id=2,
        arrival=13,
        passage=None,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    result = _build(selection_result, {"merge": rank_state})
    node_result = result.node_candidate_set_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
    )
    assert len(node_result.candidate_visits) == 2
    assert node_result.candidate_visits[1].baseline_passage_timestep is None


def test_right_of_entry_only_candidate_set_is_normal():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    result = _build(selection_result, {"merge": rank_state})
    node_result = result.node_candidate_set_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )
    assert len(node_result.candidate_visits) == 1


def test_right_of_entry_validation_errors():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_other", 2))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_missing", 9)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_result, {"merge": rank_state}),
        "collector has no record",
    )

    collector2 = OrderControlBaselineCollector()
    rank_state2 = _new_rank_state("merge")
    _register_undetermined(rank_state2, ("veh_roe", 1))
    _register_b_visit(
        collector2,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_wrong_node = _selection_result(
        collector=collector2,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    record = collector2._visit_records_by_primary_key[("veh_roe", 1)]
    record.node_name = "wrong_node"
    _expect_runtime_error(
        lambda: _build(selection_wrong_node, {"merge": rank_state2}),
        "node_name='wrong_node'",
    )

    collector3 = OrderControlBaselineCollector()
    rank_state3 = _new_rank_state("merge")
    _register_undetermined(rank_state3, ("veh_roe", 1))
    _register_a_visit(
        collector3,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_a = _selection_result(
        collector=collector3,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_a, {"merge": rank_state3}),
        "must be B-type",
    )

    collector4 = OrderControlBaselineCollector()
    rank_state4 = _new_rank_state("merge")
    _register_undetermined(rank_state4, ("veh_roe", 1))
    _register_b_visit(
        collector4,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=12,
    )
    selection_passage_eq_arrival = _selection_result(
        collector=collector4,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_passage_eq_arrival, {"merge": rank_state4}),
        "baseline_passage_timestep=12",
    )

    collector5 = OrderControlBaselineCollector()
    rank_state5 = _new_rank_state("merge")
    _register_undetermined(rank_state5, ("veh_roe", 1))
    _register_b_visit(
        collector5,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_bad_p = _selection_result(
        collector=collector5,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    record5 = collector5._visit_records_by_primary_key[("veh_roe", 1)]
    record5.baseline_passage_timestep = True  # type: ignore[assignment]
    _expect_runtime_error(
        lambda: _build(selection_bad_p, {"merge": rank_state5}),
        "baseline_passage_timestep",
    )


def test_candidate_record_validation_and_missing_right_of_entry():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_b", 2))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b",
        visit_id=2,
        vehicle_id=2,
        arrival=13,
        passage=15,
    )
    rank_state.confirm_visits_in_order((("veh_roe", 1),))
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_result, {"merge": rank_state}),
        "missing from the candidate visit set",
    )

    collector2 = OrderControlBaselineCollector()
    rank_state2 = _new_rank_state("merge")
    _register_undetermined(rank_state2, ("veh_roe", 1), ("veh_dup", 9))
    _register_b_visit(
        collector2,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    collector2.register_snapshot_visit(
        vehicle_name="veh_dup",
        vehicle_id=9,
        node_name="merge",
        inlink_name="in9",
        visit_id=9,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )
    collector2.record_baseline_arrival(
        vehicle_name="veh_dup",
        visit_id=9,
        node_name="merge",
        baseline_arrival_timestep=12,
        arrival_tiebreaker=1.0,
        route_next_link_name="out",
    )
    record_dup = collector2._visit_records_by_primary_key[("veh_dup", 9)]
    collector2.apply_baseline_passage_timestep(record_dup, 15)
    selection_dup = _selection_result(
        collector=collector2,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    result_dup = _build(selection_dup, {"merge": rank_state2})
    assert result_dup.node_candidate_set_results[0].build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )
    assert len(result_dup.node_candidate_set_results[0].candidate_visits) == 2

    collector3 = OrderControlBaselineCollector()
    rank_state3 = _new_rank_state("merge")
    _register_undetermined(rank_state3, ("veh_roe", 1), ("veh_bad", 8))
    _register_b_visit(
        collector3,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    collector3.register_snapshot_visit(
        vehicle_name="veh_bad",
        vehicle_id=8,
        node_name="merge",
        inlink_name="in8",
        visit_id=8,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )
    selection_bad = _selection_result(
        collector=collector3,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_bad, {"merge": rank_state3}),
        "baseline_arrival_timestep=None",
    )

    collector4 = OrderControlBaselineCollector()
    rank_state4 = _new_rank_state("merge")
    _register_undetermined(rank_state4, ("veh_roe", 1))
    _register_b_visit(
        collector4,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    collector4.register_snapshot_visit(
        vehicle_name="veh_unreg",
        vehicle_id=7,
        node_name="merge",
        inlink_name="in7",
        visit_id=7,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )
    collector4.record_baseline_arrival(
        vehicle_name="veh_unreg",
        visit_id=7,
        node_name="merge",
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.0,
        route_next_link_name="out",
    )
    selection_unreg = _selection_result(
        collector=collector4,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_unreg, {"merge": rank_state4}),
        "not undetermined and not confirmed",
    )


def test_multi_node_independent_status_and_failure_stops_later_nodes():
    collector = OrderControlBaselineCollector()
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    rank_state_c = _new_rank_state("node_c")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2), ("veh_b_other", 3))
    _register_undetermined(rank_state_c, ("veh_c", 3))
    _register_b_visit(
        collector,
        vehicle_name="veh_a",
        visit_id=1,
        vehicle_id=1,
        node_name="node_a",
        arrival=12,
        passage=None,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b",
        visit_id=2,
        vehicle_id=2,
        node_name="node_b",
        arrival=12,
        passage=14,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b_other",
        visit_id=3,
        vehicle_id=3,
        node_name="node_b",
        arrival=13,
        passage=None,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_c",
        visit_id=3,
        vehicle_id=3,
        node_name="node_c",
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("node_a", "node_b", "node_c"),
        node_selection_results=(
            _selected_node("node_a", ("veh_a", 1)),
            _selected_node("node_b", ("veh_b", 2)),
            _selected_node("node_c", ("veh_c", 3)),
        ),
    )
    result = _build(
        selection_result,
        {
            "node_a": rank_state_a,
            "node_b": rank_state_b,
            "node_c": rank_state_c,
        },
    )
    assert [item.node_name for item in result.node_candidate_set_results] == [
        "node_a",
        "node_b",
        "node_c",
    ]
    assert result.node_candidate_set_results[0].build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE
    )
    assert result.node_candidate_set_results[1].build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
    )
    assert result.node_candidate_set_results[2].build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )

    collector_fail = OrderControlBaselineCollector()
    rank_state_fail_a = _new_rank_state("node_a")
    rank_state_fail_b = _new_rank_state("node_b")
    _register_undetermined(rank_state_fail_a, ("veh_a", 1))
    _register_undetermined(rank_state_fail_b, ("veh_b", 2))
    _register_b_visit(
        collector_fail,
        vehicle_name="veh_a",
        visit_id=1,
        vehicle_id=1,
        node_name="node_a",
        arrival=12,
        passage=14,
    )
    _register_b_visit(
        collector_fail,
        vehicle_name="veh_b",
        visit_id=2,
        vehicle_id=2,
        node_name="node_b",
        arrival=12,
        passage=14,
    )
    rank_state_fail_b.confirm_visits_in_order((("veh_b", 2),))
    selection_fail = _selection_result(
        collector=collector_fail,
        target_node_names=("node_a", "node_b"),
        node_selection_results=(
            _selected_node("node_a", ("veh_a", 1)),
            _selected_node("node_b", ("veh_b", 2)),
        ),
    )
    _expect_runtime_error(
        lambda: _build(
            selection_fail,
            {"node_a": rank_state_fail_a, "node_b": rank_state_fail_b},
        ),
        "candidate_visits is empty",
    )


def test_node_name_mismatch_stops_processing():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("wrong_name", ("veh_roe", 1)),),
    )
    _expect_runtime_error(
        lambda: _build(selection_result, {"merge": rank_state}),
        "right-of-entry selection result has 'wrong_name'",
    )


def test_read_only_and_no_upstream_rerun():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    before_collector = _collector_snapshot(collector)
    before_k = rank_state.k_confirmed()
    with patch(
        "uxsim.order_control_tvt_right_of_entry_selection."
        "select_right_of_entry_decision_window_visits",
    ) as patched_select, patch(
        "uxsim.order_control_tvt_leading_nonparticipating_confirmation."
        "confirm_leading_nonparticipating_decision_window_visits",
    ) as patched_leading, patch(
        "uxsim.order_control_tvt_arrived_undetermined_confirmation."
        "confirm_already_arrived_undetermined_visits",
    ) as patched_arrived, patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
    ) as patched_fork:
        _build(selection_result, {"merge": rank_state})
        patched_select.assert_not_called()
        patched_leading.assert_not_called()
        patched_arrived.assert_not_called()
        patched_fork.assert_not_called()
    assert _collector_snapshot(collector) == before_collector
    assert rank_state.k_confirmed() == before_k


def test_k_confirmed_before_uses_upstream_snapshot_not_current_rank_state():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(
            _selected_node("merge", ("veh_roe", 1), k_confirmed_before=2),
        ),
    )
    result = _build(selection_result, {"merge": rank_state})
    assert result.node_candidate_set_results[0].k_confirmed_before == 2
    assert rank_state.k_confirmed() == 0


def test_uxsim_regression_passage_not_before_arrival():
    W = World(
        name="candidate_visit_set_passage_arrival",
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="fcfs",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(0)
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()

    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    target_node_name = "merge"

    veh = W.addVehicle("orig1", "dest", 0, name="probe")
    max_advance_steps = W.TMAX + 1
    for _ in range(max_advance_steps):
        if veh.link is not None and veh.link.name == "link1":
            break
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not reach link1 before simulation ended.")
        W.exec_simulation(duration_t2=1)
    else:
        raise AssertionError("Vehicle did not reach link1 within the step limit.")

    visit_id = veh.order_control_visit_id
    collector.register_snapshot_visit(
        vehicle_name=veh.name,
        vehicle_id=veh.id,
        node_name=target_node_name,
        inlink_name="link1",
        visit_id=visit_id,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )

    snapshot_before_forward = collector.get_baseline_visit_snapshot(veh.name, visit_id)
    assert snapshot_before_forward is not None
    assert snapshot_before_forward["node_name"] == target_node_name
    assert snapshot_before_forward["vehicle_name"] == veh.name
    assert snapshot_before_forward["visit_id"] == visit_id
    assert snapshot_before_forward["was_arrived_at_snapshot"] is False
    assert snapshot_before_forward["baseline_arrival_timestep"] is None
    assert snapshot_before_forward["baseline_passage_timestep"] is None

    snapshot = None
    for _ in range(max_advance_steps):
        snapshot = collector.get_baseline_visit_snapshot(veh.name, visit_id)
        if (
            snapshot is not None
            and snapshot["baseline_arrival_timestep"] is not None
            and snapshot["baseline_passage_timestep"] is not None
        ):
            break
        if not W.check_simulation_ongoing():
            break
        W.exec_simulation(duration_t2=1)
    else:
        raise AssertionError(
            "Collector did not record both arrival and passage within the step limit."
        )

    assert snapshot is not None
    arrival = snapshot["baseline_arrival_timestep"]
    passage = snapshot["baseline_passage_timestep"]
    assert arrival is not None
    assert passage is not None
    assert snapshot["node_name"] == target_node_name
    assert snapshot["vehicle_name"] == veh.name
    assert snapshot["visit_id"] == visit_id
    assert passage >= arrival + 1


def test_existing_result_types_remain_unchanged():
    selection_fields = {
        field.name
        for field in dataclasses.fields(OrderControlTvtRightOfEntrySelectionResult)
    }
    assert selection_fields == {
        "leading_confirmation_result",
        "node_selection_results",
    }
    rank_state = _new_rank_state("merge")
    assert hasattr(rank_state, "is_undetermined")
    assert hasattr(rank_state, "is_confirmed")


def test_invalid_max_tvt_candidate_visit_count_rejects_before_collector():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    invalid_values = [True, False, 0, -1, 1.0, "10", None]
    for invalid_value in invalid_values:
        with patch.object(
            collector,
            "get_baseline_visit_snapshot",
            wraps=collector.get_baseline_visit_snapshot,
        ) as get_snapshot, patch.object(
            collector,
            "export_node_baseline_visits",
            wraps=collector.export_node_baseline_visits,
        ) as export_node:
            _expect_value_error(
                lambda invalid_value=invalid_value: build_tvt_candidate_visit_set(
                    selection_result,
                    rank_states_by_node_name={"merge": rank_state},
                    max_tvt_candidate_visit_count=invalid_value,
                )
            )
            get_snapshot.assert_not_called()
            export_node.assert_not_called()


def test_max_tvt_candidate_visit_count_limits_and_result_fields():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    p = 30
    selection_result = _register_p_minus_one_chain(
        collector,
        rank_state,
        p=p,
        visit_count=11,
        unresolved_rank=11,
    )
    result_n1 = _build(
        selection_result,
        {"merge": rank_state},
        max_tvt_candidate_visit_count=1,
    )
    node_n1 = result_n1.node_candidate_set_results[0]
    assert result_n1.max_tvt_candidate_visit_count == 1
    assert node_n1.p_minus_one_eligible_visit_count_before_limit == 11
    assert len(node_n1.candidate_visits) == 1
    assert node_n1.candidate_visits[0].visit_key == ("veh_0", 1)
    assert node_n1.build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )

    result_n10 = _build(
        selection_result,
        {"merge": rank_state},
        max_tvt_candidate_visit_count=10,
    )
    node_n10 = result_n10.node_candidate_set_results[0]
    assert result_n10.max_tvt_candidate_visit_count == 10
    assert node_n10.p_minus_one_eligible_visit_count_before_limit == 11
    assert len(node_n10.candidate_visits) == 10
    assert [item.visit_key for item in node_n10.candidate_visits] == [
        (f"veh_{index}", index + 1) for index in range(10)
    ]
    assert node_n10.candidate_visits[0].visit_key == ("veh_0", 1)
    assert node_n10.build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )

    for limit in (15, 20):
        result_large = _build(
            selection_result,
            {"merge": rank_state},
            max_tvt_candidate_visit_count=limit,
        )
        assert result_large.max_tvt_candidate_visit_count == limit
        node_large = result_large.node_candidate_set_results[0]
        assert len(node_large.candidate_visits) == 11
        assert node_large.p_minus_one_eligible_visit_count_before_limit == 11

    collector_small = OrderControlBaselineCollector()
    rank_state_small = _new_rank_state("merge")
    selection_small = _register_p_minus_one_chain(
        collector_small,
        rank_state_small,
        p=p,
        visit_count=3,
    )
    result_below = _build(
        selection_small,
        {"merge": rank_state_small},
        max_tvt_candidate_visit_count=10,
    )
    node_below = result_below.node_candidate_set_results[0]
    assert node_below.p_minus_one_eligible_visit_count_before_limit == 3
    assert len(node_below.candidate_visits) == 3

    collector_equal = OrderControlBaselineCollector()
    rank_state_equal = _new_rank_state("merge")
    selection_equal = _register_p_minus_one_chain(
        collector_equal,
        rank_state_equal,
        p=p,
        visit_count=5,
    )
    result_equal = _build(
        selection_equal,
        {"merge": rank_state_equal},
        max_tvt_candidate_visit_count=5,
    )
    node_equal = result_equal.node_candidate_set_results[0]
    assert node_equal.p_minus_one_eligible_visit_count_before_limit == 5
    assert len(node_equal.candidate_visits) == 5


def test_nth_unresolved_candidate_does_not_promote_later_visit():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    p = 25
    selection_result = _register_p_minus_one_chain(
        collector,
        rank_state,
        p=p,
        visit_count=3,
        unresolved_rank=2,
    )
    rank3_visit_key = ("veh_2", 3)
    result = _build(
        selection_result,
        {"merge": rank_state},
        max_tvt_candidate_visit_count=2,
    )
    node_result = result.node_candidate_set_results[0]
    assert node_result.p_minus_one_eligible_visit_count_before_limit == 3
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
    )
    assert len(node_result.candidate_visits) == 2
    assert [item.visit_key for item in node_result.candidate_visits] == [
        ("veh_0", 1),
        ("veh_1", 2),
    ]
    assert node_result.candidate_visits[0].baseline_passage_timestep is not None
    assert node_result.candidate_visits[1].baseline_passage_timestep is None
    assert rank3_visit_key not in {
        item.visit_key for item in node_result.candidate_visits
    }
    rank3_record = collector._visit_records_by_primary_key[rank3_visit_key]
    assert rank3_record.baseline_passage_timestep is not None


def test_beyond_limit_incomplete_fields_do_not_affect_candidate_build():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    p = 30
    selection_result = _register_p_minus_one_chain(
        collector,
        rank_state,
        p=p,
        visit_count=11,
        beyond_limit_bad_fields=True,
    )
    result = _build(
        selection_result,
        {"merge": rank_state},
        max_tvt_candidate_visit_count=10,
    )
    node_result = result.node_candidate_set_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )
    assert node_result.p_minus_one_eligible_visit_count_before_limit == 11
    assert len(node_result.candidate_visits) == 10


def test_beyond_limit_invalid_rank_material_still_fails():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    p = 30
    selection_result = _register_p_minus_one_chain(
        collector,
        rank_state,
        p=p,
        visit_count=11,
    )
    record = collector._visit_records_by_primary_key[("veh_10", 11)]
    record.arrival_tiebreaker = True  # type: ignore[assignment]
    _expect_runtime_error(
        lambda: _build(
            selection_result,
            {"merge": rank_state},
            max_tvt_candidate_visit_count=10,
        ),
        "arrival_tiebreaker",
    )


def test_multi_node_uses_same_max_tvt_candidate_visit_count():
    collector = OrderControlBaselineCollector()
    rank_state_a = _new_rank_state("node_a")
    rank_state_b = _new_rank_state("node_b")
    _register_undetermined(rank_state_a, ("veh_a", 1))
    _register_undetermined(rank_state_b, ("veh_b", 2))
    _register_b_visit(
        collector,
        vehicle_name="veh_a",
        visit_id=1,
        vehicle_id=1,
        node_name="node_a",
        arrival=12,
        passage=14,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b",
        visit_id=2,
        vehicle_id=2,
        node_name="node_b",
        arrival=12,
        passage=14,
    )
    selection_result = _selection_result(
        collector=collector,
        target_node_names=("node_a", "node_b"),
        node_selection_results=(
            _selected_node("node_a", ("veh_a", 1)),
            _selected_node("node_b", ("veh_b", 2)),
        ),
    )
    result = _build(
        selection_result,
        {"node_a": rank_state_a, "node_b": rank_state_b},
        max_tvt_candidate_visit_count=7,
    )
    assert result.max_tvt_candidate_visit_count == 7
    for node_result in result.node_candidate_set_results:
        assert node_result.p_minus_one_eligible_visit_count_before_limit == 1
        assert len(node_result.candidate_visits) == 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
