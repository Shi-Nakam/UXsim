# Unit tests for inlink-grouped limited TVT candidate visit physical ordering
# (design memo §25.25.34.50).
#
# Run from the repository root:
#   python tests_order_control_tvt_inlink_candidate_physical_order.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_baseline_snapshot import (
    OrderControlBaselineSnapshotInlinkPhysicalOrder,
)
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
)
from uxsim.order_control_tvt_baseline_alignment import (
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
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidateVisitPhysicalOrder,
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
    build_tvt_inlink_candidate_physical_orders,
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
def _new_rank_state(node_name: str) -> OrderControlTvtNodeRankState:
    return OrderControlTvtNodeRankState(node_name)


def _register_undetermined(
    rank_state: OrderControlTvtNodeRankState,
    *visit_keys: OrderControlTvtVisitKey,
) -> None:
    for visit_key in visit_keys:
        rank_state.register_undetermined_visit(visit_key)


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
    inlink_physical_orders: tuple[
        OrderControlBaselineSnapshotInlinkPhysicalOrder, ...
    ] = (),
) -> OrderControlBaselineForkResult:
    return OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=target_node_names,
        baseline_timestep_T=10,
        configured_horizon_steps=50,
        fork_steps_executed=50,
        final_fork_timestep=60,
        registered_visit_count=1,
        inlink_physical_orders=inlink_physical_orders,
    )


def _selection_result(
    *,
    collector: OrderControlBaselineCollector,
    target_node_names: tuple[str, ...],
    node_selection_results: tuple[OrderControlTvtNodeRightOfEntrySelectionResult, ...],
    inlink_physical_orders: tuple[
        OrderControlBaselineSnapshotInlinkPhysicalOrder, ...
    ] = (),
) -> OrderControlTvtRightOfEntrySelectionResult:
    fork_result = _fork_result(
        collector=collector,
        target_node_names=target_node_names,
        inlink_physical_orders=inlink_physical_orders,
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
) -> OrderControlTvtNodeRightOfEntrySelectionResult:
    return OrderControlTvtNodeRightOfEntrySelectionResult(
        node_name=node_name,
        selection_status=selection_status,
        right_of_entry_visit_key=None,
        k_confirmed_before=0,
    )


def _build_candidate_set(
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


def _physical_order(
    node_name: str,
    inlink_name: str,
    visit_keys_head_to_tail: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlBaselineSnapshotInlinkPhysicalOrder:
    return OrderControlBaselineSnapshotInlinkPhysicalOrder(
        node_name=node_name,
        inlink_name=inlink_name,
        visit_keys_head_to_tail=visit_keys_head_to_tail,
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


def test_result_types_are_frozen_dataclasses():
    for cls in (
        OrderControlTvtInlinkCandidateVisitPhysicalOrder,
        OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
        OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    ):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True


def test_single_node_single_inlink_physical_order():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    physical_orders = (
        _physical_order("merge", "in1", (("veh_roe", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    assert result.candidate_visit_set_result is candidate_set
    node_result = result.node_inlink_candidate_physical_order_results[0]
    assert node_result.node_name == "merge"
    assert (
        node_result.build_status
        == OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )
    assert len(node_result.inlink_candidate_physical_orders) == 1
    inlink_result = node_result.inlink_candidate_physical_orders[0]
    assert inlink_result.candidate_visit_keys_head_to_tail == (("veh_roe", 1),)


def test_single_node_multiple_inlinks_baseline_rank_numbers_not_consecutive():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_roe", 1),
        ("veh_b2", 2),
        ("veh_b3", 3),
    )
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b2",
        visit_id=2,
        vehicle_id=2,
        inlink_name="in2",
        arrival=16,
        tiebreaker=0.5,
        passage=p + 1,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b3",
        visit_id=3,
        vehicle_id=3,
        inlink_name="in3",
        arrival=16,
        tiebreaker=0.1,
        passage=p + 2,
    )
    physical_orders = (
        _physical_order("merge", "in1", (("veh_roe", 1),)),
        _physical_order("merge", "in2", (("veh_b2", 2),)),
        _physical_order("merge", "in3", (("veh_b3", 3),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    baseline_order_keys = [
        visit.visit_key for visit in candidate_set.node_candidate_set_results[0].candidate_visits
    ]
    assert baseline_order_keys == [
        ("veh_roe", 1),
        ("veh_b3", 3),
        ("veh_b2", 2),
    ]
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    node_result = result.node_inlink_candidate_physical_order_results[0]
    assert [item.inlink_name for item in node_result.inlink_candidate_physical_orders] == [
        "in1",
        "in2",
        "in3",
    ]
    assert node_result.inlink_candidate_physical_orders[0].candidate_visit_keys_head_to_tail == (
        ("veh_roe", 1),
    )
    assert node_result.inlink_candidate_physical_orders[1].candidate_visit_keys_head_to_tail == (
        ("veh_b2", 2),
    )
    assert node_result.inlink_candidate_physical_orders[2].candidate_visit_keys_head_to_tail == (
        ("veh_b3", 3),
    )


def test_rights_holder_inlink_and_visit_included_in_inlink_physical_order():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_b2", 2))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="rights_in",
        arrival=14,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b2",
        visit_id=2,
        vehicle_id=2,
        inlink_name="other_in",
        arrival=16,
        passage=p + 1,
    )
    physical_orders = (
        _physical_order("merge", "rights_in", (("veh_roe", 1),)),
        _physical_order("merge", "other_in", (("veh_b2", 2),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    inlink_names = [
        item.inlink_name
        for item in result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders
    ]
    assert inlink_names == ["rights_in", "other_in"]
    rights_inlink = result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders[0]
    assert rights_inlink.inlink_name == "rights_in"
    assert rights_inlink.candidate_visit_keys_head_to_tail == (("veh_roe", 1),)


def test_same_inlink_two_candidates_follow_snapshot_physical_order():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_near", 2), ("veh_far", 3))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_near",
        visit_id=2,
        vehicle_id=2,
        inlink_name="in1",
        arrival=15,
        passage=p + 1,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_far",
        visit_id=3,
        vehicle_id=3,
        inlink_name="in1",
        arrival=17,
        passage=p + 2,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in2",
        arrival=14,
        passage=p,
    )
    physical_orders = (
        _physical_order(
            "merge",
            "in1",
            (("veh_near", 2), ("veh_far", 3)),
        ),
        _physical_order("merge", "in2", (("veh_roe", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    in1_result = None
    for item in result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders:
        if item.inlink_name == "in1":
            in1_result = item
    assert in1_result is not None
    assert in1_result.candidate_visit_keys_head_to_tail == (
        ("veh_near", 2),
        ("veh_far", 3),
    )


def test_multiple_nodes_follow_target_node_names_order():
    collector = OrderControlBaselineCollector()
    rank_a = _new_rank_state("junction_a")
    rank_b = _new_rank_state("junction_b")
    _register_undetermined(rank_a, ("veh_a", 1))
    _register_undetermined(rank_b, ("veh_b", 1))
    p = 15
    _register_b_visit(
        collector,
        vehicle_name="veh_a",
        visit_id=1,
        vehicle_id=1,
        node_name="junction_a",
        inlink_name="in_a",
        arrival=10,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b",
        visit_id=1,
        vehicle_id=2,
        node_name="junction_b",
        inlink_name="in_b",
        arrival=10,
        passage=p,
    )
    physical_orders = (
        _physical_order("junction_a", "in_a", (("veh_a", 1),)),
        _physical_order("junction_b", "in_b", (("veh_b", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("junction_a", "junction_b"),
        node_selection_results=(
            _selected_node("junction_a", ("veh_a", 1)),
            _selected_node("junction_b", ("veh_b", 1)),
        ),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(
        selection, {"junction_a": rank_a, "junction_b": rank_b}
    )
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    assert [
        node.node_name
        for node in result.node_inlink_candidate_physical_order_results
    ] == ["junction_a", "junction_b"]


def test_a_type_and_beyond_limit_visits_omitted_from_inlink_candidate_result():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(
        rank_state,
        ("veh_roe", 1),
        ("veh_b2", 2),
        ("veh_b3", 3),
    )
    p = 18
    _register_a_visit(
        collector,
        vehicle_name="veh_a",
        visit_id=9,
        vehicle_id=99,
        inlink_name="in1",
        arrival=10,
        passage=12,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b2",
        visit_id=2,
        vehicle_id=2,
        inlink_name="in1",
        arrival=16,
        passage=p + 1,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b3",
        visit_id=3,
        vehicle_id=3,
        inlink_name="in1",
        arrival=25,
        passage=p + 2,
    )
    physical_orders = (
        _physical_order(
            "merge",
            "in1",
            (
                ("veh_a", 9),
                ("veh_roe", 1),
                ("veh_b2", 2),
                ("veh_b3", 3),
            ),
        ),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(
        selection, {"merge": rank_state}, max_tvt_candidate_visit_count=2
    )
    limited_keys = [
        visit.visit_key
        for visit in candidate_set.node_candidate_set_results[0].candidate_visits
    ]
    assert limited_keys == [("veh_roe", 1), ("veh_b2", 2)]
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    inlink_result = result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders[0]
    assert inlink_result.candidate_visit_keys_head_to_tail == (
        ("veh_roe", 1),
        ("veh_b2", 2),
    )


def test_empty_inlink_with_no_candidates_is_omitted():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    physical_orders = (
        _physical_order("merge", "in1", (("veh_roe", 1),)),
        _physical_order("merge", "in2", ()),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    assert len(
        result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders
    ) == 1


def test_not_built_no_right_of_entry_returns_empty_inlink_orders():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(
            _not_built_node(
                "merge",
                OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY,
            ),
        ),
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    node_result = result.node_inlink_candidate_physical_order_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
    )
    assert node_result.inlink_candidate_physical_orders == ()


def test_not_built_unresolved_arrivals_returns_empty_inlink_orders():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(
            _not_built_node(
                "merge",
                OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS,
            ),
        ),
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    node_result = result.node_inlink_candidate_physical_order_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS
    )
    assert node_result.inlink_candidate_physical_orders == ()


def test_unresolved_right_of_entry_passage_returns_empty_inlink_orders():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        arrival=14,
        passage=None,
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    node_result = result.node_inlink_candidate_physical_order_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE
    )
    assert node_result.inlink_candidate_physical_orders == ()


def test_unresolved_candidate_passages_still_builds_inlink_orders():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_tail", 2))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_tail",
        visit_id=2,
        vehicle_id=2,
        inlink_name="in1",
        arrival=16,
        passage=None,
    )
    physical_orders = (
        _physical_order(
            "merge",
            "in1",
            (("veh_roe", 1), ("veh_tail", 2)),
        ),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    node_result = result.node_inlink_candidate_physical_order_results[0]
    assert node_result.build_status == (
        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
    )
    assert node_result.inlink_candidate_physical_orders[0].candidate_visit_keys_head_to_tail == (
        ("veh_roe", 1),
        ("veh_tail", 2),
    )


_TEST_ONLY_UNEXPECTED_BUILD_STATUS = "test_only_unexpected_build_status"


def _manual_candidate_visit_set_result(
    selection: OrderControlTvtRightOfEntrySelectionResult,
    node_candidate_set_results: tuple[OrderControlTvtNodeCandidateVisitSetResult, ...],
) -> OrderControlTvtCandidateVisitSetResult:
    return OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=selection,
        max_tvt_candidate_visit_count=10,
        node_candidate_set_results=node_candidate_set_results,
    )


def test_unexpected_build_status_raises_runtime_error_with_node_and_status():
    collector = OrderControlBaselineCollector()
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
    )
    candidate_set = _manual_candidate_visit_set_result(
        selection,
        (
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="merge",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                right_of_entry_visit_key=("veh_roe", 1),
                right_of_entry_baseline_passage_timestep=18,
                k_confirmed_before=0,
                p_minus_one_eligible_visit_count_before_limit=0,
                candidate_visits=(),
            ),
        ),
    )
    try:
        build_tvt_inlink_candidate_physical_orders(candidate_set)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert _TEST_ONLY_UNEXPECTED_BUILD_STATUS in message
        assert "unexpected candidate visit set build status" in message


def test_unexpected_build_status_on_second_node_raises_without_partial_result():
    collector = OrderControlBaselineCollector()
    physical_orders = (
        _physical_order("junction_a", "in_a", (("veh_a", 1),)),
        _physical_order("junction_b", "in_b", (("veh_b", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("junction_a", "junction_b"),
        node_selection_results=(
            _selected_node("junction_a", ("veh_a", 1)),
            _selected_node("junction_b", ("veh_b", 1)),
        ),
        inlink_physical_orders=physical_orders,
    )
    built_visit = OrderControlTvtCandidateVisit(
        visit_key=("veh_a", 1),
        vehicle_id=1,
        inlink_name="in_a",
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.0,
        route_next_link_name="out",
        baseline_passage_timestep=15,
    )
    candidate_set = _manual_candidate_visit_set_result(
        selection,
        (
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="junction_a",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                right_of_entry_visit_key=("veh_a", 1),
                right_of_entry_baseline_passage_timestep=15,
                k_confirmed_before=0,
                p_minus_one_eligible_visit_count_before_limit=1,
                candidate_visits=(built_visit,),
            ),
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="junction_b",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                right_of_entry_visit_key=("veh_b", 1),
                right_of_entry_baseline_passage_timestep=15,
                k_confirmed_before=0,
                p_minus_one_eligible_visit_count_before_limit=1,
                candidate_visits=(),
            ),
        ),
    )
    try:
        build_tvt_inlink_candidate_physical_orders(candidate_set)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "junction_b" in message
        assert _TEST_ONLY_UNEXPECTED_BUILD_STATUS in message
        assert "unexpected candidate visit set build status" in message


def test_node_candidate_result_count_mismatch_raises_runtime_error():
    collector = OrderControlBaselineCollector()
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge", "junction_b"),
        node_selection_results=(
            _selected_node("merge", ("veh_roe", 1)),
            _selected_node("junction_b", ("veh_b", 1)),
        ),
    )
    candidate_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=selection,
        max_tvt_candidate_visit_count=10,
        node_candidate_set_results=(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="merge",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                right_of_entry_visit_key=("veh_roe", 1),
                right_of_entry_baseline_passage_timestep=18,
                k_confirmed_before=0,
                p_minus_one_eligible_visit_count_before_limit=1,
                candidate_visits=(),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: build_tvt_inlink_candidate_physical_orders(candidate_set),
        "does not match",
    )


def test_candidate_visit_key_missing_from_physical_order_raises_runtime_error():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1), ("veh_b2", 2))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b2",
        visit_id=2,
        vehicle_id=2,
        inlink_name="in2",
        arrival=16,
        passage=p + 1,
    )
    physical_orders = (
        _physical_order("merge", "in1", (("veh_roe", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    _expect_runtime_error(
        lambda: build_tvt_inlink_candidate_physical_orders(candidate_set),
        "missing from snapshot physical orders",
    )


def test_candidate_inlink_name_mismatch_raises_runtime_error():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    p = 18
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=p,
    )
    physical_orders = (
        _physical_order("merge", "in2", (("veh_roe", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    _expect_runtime_error(
        lambda: build_tvt_inlink_candidate_physical_orders(candidate_set),
        "inlink_name=",
    )


def test_duplicate_candidate_visit_key_raises_runtime_error():
    visit_a = OrderControlTvtCandidateVisit(
        visit_key=("veh_dup", 1),
        vehicle_id=1,
        inlink_name="in1",
        baseline_arrival_timestep=10,
        arrival_tiebreaker=0.0,
        route_next_link_name="out",
        baseline_passage_timestep=20,
    )
    visit_b = OrderControlTvtCandidateVisit(
        visit_key=("veh_dup", 1),
        vehicle_id=1,
        inlink_name="in1",
        baseline_arrival_timestep=11,
        arrival_tiebreaker=0.0,
        route_next_link_name="out",
        baseline_passage_timestep=21,
    )
    collector = OrderControlBaselineCollector()
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=(
            _physical_order("merge", "in1", (("veh_dup", 1),)),
        ),
    )
    candidate_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=selection,
        max_tvt_candidate_visit_count=10,
        node_candidate_set_results=(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="merge",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                right_of_entry_visit_key=("veh_roe", 1),
                right_of_entry_baseline_passage_timestep=18,
                k_confirmed_before=0,
                p_minus_one_eligible_visit_count_before_limit=2,
                candidate_visits=(visit_a, visit_b),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: build_tvt_inlink_candidate_physical_orders(candidate_set),
        "duplicate VisitKey",
    )


def test_same_candidate_visit_key_on_two_physical_orders_raises_runtime_error():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=18,
    )
    physical_orders = (
        _physical_order(
            "merge",
            "in1",
            (("veh_roe", 1), ("veh_roe", 1)),
        ),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    _expect_runtime_error(
        lambda: build_tvt_inlink_candidate_physical_orders(candidate_set),
        "more than one snapshot physical-order",
    )


def test_second_node_mismatch_raises_without_returning_partial_result():
    collector = OrderControlBaselineCollector()
    rank_a = _new_rank_state("junction_a")
    rank_b = _new_rank_state("junction_b")
    _register_undetermined(rank_a, ("veh_a", 1))
    _register_undetermined(rank_b, ("veh_b", 1))
    p = 15
    _register_b_visit(
        collector,
        vehicle_name="veh_a",
        visit_id=1,
        vehicle_id=1,
        node_name="junction_a",
        inlink_name="in_a",
        arrival=10,
        passage=p,
    )
    _register_b_visit(
        collector,
        vehicle_name="veh_b",
        visit_id=1,
        vehicle_id=2,
        node_name="junction_b",
        inlink_name="in_b",
        arrival=10,
        passage=p,
    )
    physical_orders = (
        _physical_order("junction_a", "in_a", (("veh_a", 1),)),
        _physical_order("junction_b", "in_b", ()),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("junction_a", "junction_b"),
        node_selection_results=(
            _selected_node("junction_a", ("veh_a", 1)),
            _selected_node("junction_b", ("veh_b", 1)),
        ),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(
        selection, {"junction_a": rank_a, "junction_b": rank_b}
    )
    try:
        build_tvt_inlink_candidate_physical_orders(candidate_set)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "missing from snapshot physical orders" in str(error)


def test_node_name_mismatch_raises_runtime_error():
    collector = OrderControlBaselineCollector()
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("wrong_name", ("veh_roe", 1)),),
    )
    candidate_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=selection,
        max_tvt_candidate_visit_count=10,
        node_candidate_set_results=(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="wrong_name",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                right_of_entry_visit_key=("veh_roe", 1),
                right_of_entry_baseline_passage_timestep=18,
                k_confirmed_before=0,
                p_minus_one_eligible_visit_count_before_limit=1,
                candidate_visits=(),
            ),
        ),
    )
    _expect_runtime_error(
        lambda: build_tvt_inlink_candidate_physical_orders(candidate_set),
        "Node name mismatch",
    )


def test_does_not_modify_input_objects():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=18,
    )
    physical_orders = (
        _physical_order("merge", "in1", (("veh_roe", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    candidate_visits_before = candidate_set.node_candidate_set_results[0].candidate_visits
    fork_result = (
        candidate_set.right_of_entry_selection_result.leading_confirmation_result.arrived_confirmation_result.alignment_fork_result.fork_result
    )
    physical_orders_before = fork_result.inlink_physical_orders
    k_confirmed_before = rank_state.k_confirmed()
    build_tvt_inlink_candidate_physical_orders(candidate_set)
    assert (
        candidate_set.node_candidate_set_results[0].candidate_visits
        is candidate_visits_before
    )
    assert fork_result.inlink_physical_orders is physical_orders_before
    assert rank_state.k_confirmed() == k_confirmed_before


def test_does_not_rerun_upstream_or_collector_export():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=18,
    )
    physical_orders = (
        _physical_order("merge", "in1", (("veh_roe", 1),)),
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=physical_orders,
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    with patch(
        "uxsim.order_control_tvt_candidate_visit_set.build_tvt_candidate_visit_set"
    ) as build_candidates, patch.object(
        collector,
        "export_node_baseline_visits",
        wraps=collector.export_node_baseline_visits,
    ) as export_node:
        build_tvt_inlink_candidate_physical_orders(candidate_set)
        build_candidates.assert_not_called()
        export_node.assert_not_called()


def test_overall_result_has_no_buyer_seller_prefix_fields():
    collector = OrderControlBaselineCollector()
    rank_state = _new_rank_state("merge")
    _register_undetermined(rank_state, ("veh_roe", 1))
    _register_b_visit(
        collector,
        vehicle_name="veh_roe",
        visit_id=1,
        vehicle_id=1,
        inlink_name="in1",
        arrival=14,
        passage=18,
    )
    selection = _selection_result(
        collector=collector,
        target_node_names=("merge",),
        node_selection_results=(_selected_node("merge", ("veh_roe", 1)),),
        inlink_physical_orders=(
            _physical_order("merge", "in1", (("veh_roe", 1),)),
        ),
    )
    candidate_set = _build_candidate_set(selection, {"merge": rank_state})
    result = build_tvt_inlink_candidate_physical_orders(candidate_set)
    forbidden_names = {
        "buyer",
        "seller",
        "prefix",
        "trade_scope",
        "trade_rank",
    }
    for cls in (
        OrderControlTvtInlinkCandidateVisitPhysicalOrder,
        OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
        OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    ):
        field_names = {field.name for field in dataclasses.fields(cls)}
        assert forbidden_names.isdisjoint(field_names)


def test_inlink_result_type_is_immutable():
    physical_order = OrderControlTvtInlinkCandidateVisitPhysicalOrder(
        node_name="merge",
        inlink_name="in1",
        candidate_visit_keys_head_to_tail=(("veh_roe", 1),),
    )
    try:
        physical_order.node_name = "other"
        raise AssertionError("Expected FrozenInstanceError")
    except FrozenInstanceError:
        pass


TESTS = [
    test_result_types_are_frozen_dataclasses,
    test_single_node_single_inlink_physical_order,
    test_single_node_multiple_inlinks_baseline_rank_numbers_not_consecutive,
    test_rights_holder_inlink_and_visit_included_in_inlink_physical_order,
    test_same_inlink_two_candidates_follow_snapshot_physical_order,
    test_multiple_nodes_follow_target_node_names_order,
    test_a_type_and_beyond_limit_visits_omitted_from_inlink_candidate_result,
    test_empty_inlink_with_no_candidates_is_omitted,
    test_not_built_no_right_of_entry_returns_empty_inlink_orders,
    test_not_built_unresolved_arrivals_returns_empty_inlink_orders,
    test_unresolved_right_of_entry_passage_returns_empty_inlink_orders,
    test_unresolved_candidate_passages_still_builds_inlink_orders,
    test_unexpected_build_status_raises_runtime_error_with_node_and_status,
    test_unexpected_build_status_on_second_node_raises_without_partial_result,
    test_node_candidate_result_count_mismatch_raises_runtime_error,
    test_candidate_visit_key_missing_from_physical_order_raises_runtime_error,
    test_candidate_inlink_name_mismatch_raises_runtime_error,
    test_duplicate_candidate_visit_key_raises_runtime_error,
    test_same_candidate_visit_key_on_two_physical_orders_raises_runtime_error,
    test_second_node_mismatch_raises_without_returning_partial_result,
    test_node_name_mismatch_raises_runtime_error,
    test_does_not_modify_input_objects,
    test_does_not_rerun_upstream_or_collector_export,
    test_overall_result_has_no_buyer_seller_prefix_fields,
    test_inlink_result_type_is_immutable,
]


if __name__ == "__main__":
    if len(TESTS) != len({test.__name__ for test in TESTS}):
        raise RuntimeError("Duplicate test names in TESTS")
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT inlink candidate physical order tests passed "
        f"({len(TESTS)} tests)."
    )
