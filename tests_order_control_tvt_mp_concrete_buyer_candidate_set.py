# Unit tests for TVT-MP concrete buyer candidate set generation
# (design notes 2, concrete buyer candidate set pre-implementation spec).
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_concrete_buyer_candidate_set.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import ast
import dataclasses
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import numpy as np

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    OrderControlTvtInlinkCandidateVisitPhysicalOrder,
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
    OrderControlTvtMpInlinkBuyerPrefixResult,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
    build_tvt_mp_concrete_buyer_candidate_sets,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


COMPLETE = OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
NOT_BUILT_NO_RIGHT_OF_ENTRY = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
)
NOT_BUILT_UNRESOLVED_ARRIVALS = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS
)
UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE = (
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE
)
UNRESOLVED_CANDIDATE_PASSAGES = (
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
)
_TEST_ONLY_UNEXPECTED_BUILD_STATUS = "test_only_unexpected_build_status"

ROE = ("veh_roe", 1)
B1 = ("veh_b1", 1)
B2 = ("veh_b2", 1)
C1 = ("veh_c1", 1)
D1 = ("veh_d1", 1)
NP = ("veh_np", 1)
BEHIND_NP = ("veh_behind_np", 1)
ROE_FOLLOWER = ("veh_roe_follower", 1)


def _candidate_visit(
    visit_key: OrderControlTvtVisitKey,
    *,
    inlink_name: str,
    vehicle_id: int = 1,
    arrival: int = 11,
    tiebreaker: float = 0.0,
    passage: int | None = 20,
) -> OrderControlTvtCandidateVisit:
    return OrderControlTvtCandidateVisit(
        visit_key=visit_key,
        vehicle_id=vehicle_id,
        inlink_name=inlink_name,
        baseline_arrival_timestep=arrival,
        arrival_tiebreaker=tiebreaker,
        route_next_link_name="out",
        baseline_passage_timestep=passage,
    )


def _node_candidate_result(
    node_name: str,
    *,
    build_status,
    right_of_entry_visit_key: OrderControlTvtVisitKey | None,
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
) -> OrderControlTvtNodeCandidateVisitSetResult:
    return OrderControlTvtNodeCandidateVisitSetResult(
        node_name=node_name,
        build_status=build_status,
        right_of_entry_visit_key=right_of_entry_visit_key,
        right_of_entry_baseline_passage_timestep=18,
        k_confirmed_before=0,
        p_minus_one_eligible_visit_count_before_limit=len(candidate_visits),
        candidate_visits=candidate_visits,
    )


def _inlink_physical_order(
    node_name: str,
    inlink_name: str,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtInlinkCandidateVisitPhysicalOrder:
    return OrderControlTvtInlinkCandidateVisitPhysicalOrder(
        node_name=node_name,
        inlink_name=inlink_name,
        candidate_visit_keys_head_to_tail=visit_keys,
    )


def _node_inlink_result(
    node_name: str,
    *,
    build_status,
    inlink_orders: tuple[OrderControlTvtInlinkCandidateVisitPhysicalOrder, ...],
) -> OrderControlTvtNodeInlinkCandidatePhysicalOrderResult:
    return OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
        node_name=node_name,
        build_status=build_status,
        inlink_candidate_physical_orders=inlink_orders,
    )


def _physical_order_set_result(
    node_candidate_results: tuple[OrderControlTvtNodeCandidateVisitSetResult, ...],
    node_inlink_results: tuple[
        OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
        ...,
    ],
) -> OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    # This component never reads the nested right-of-entry selection tree.
    candidate_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=object(),
        max_tvt_candidate_visit_count=10,
        node_candidate_set_results=node_candidate_results,
    )
    return OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=candidate_set,
        node_inlink_candidate_physical_order_results=node_inlink_results,
    )


def _participates(*visit_keys: OrderControlTvtVisitKey) -> dict[OrderControlTvtVisitKey, bool]:
    mapping: dict[OrderControlTvtVisitKey, bool] = {}
    for visit_key in visit_keys:
        mapping[visit_key] = True
    return mapping


def _empty_status_input(
    node_name: str,
    build_status,
) -> OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    return _physical_order_set_result(
        (
            _node_candidate_result(
                node_name,
                build_status=build_status,
                right_of_entry_visit_key=None,
                candidate_visits=(),
            ),
        ),
        (
            _node_inlink_result(
                node_name,
                build_status=build_status,
                inlink_orders=(),
            ),
        ),
    )


def _roe_only_input(
    node_name: str = "merge",
) -> OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
    )
    return _physical_order_set_result(
        (
            _node_candidate_result(
                node_name,
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                node_name,
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order(node_name, "in_a", (ROE,)),
                ),
            ),
        ),
    )


def _two_buyer_inlink_input(
    node_name: str = "merge",
) -> OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    # Official baseline order toward the target Node:
    # ROE, C1, B1, B2
    # Snapshot physical order on in_b is B1 then B2 (Node-nearest first).
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(C1, inlink_name="in_c", vehicle_id=4, arrival=11),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=12),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=13),
    )
    return _physical_order_set_result(
        (
            _node_candidate_result(
                node_name,
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                node_name,
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order(node_name, "in_a", (ROE,)),
                    _inlink_physical_order(node_name, "in_b", (B1, B2)),
                    _inlink_physical_order(node_name, "in_c", (C1,)),
                ),
            ),
        ),
    )


def _field_names(cls) -> set[str]:
    names: set[str] = set()
    for field in dataclasses.fields(cls):
        names.add(field.name)
    return names


def _buyers_tuples(
    node_result: OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
) -> tuple[tuple[OrderControlTvtVisitKey, ...], ...]:
    buyers_tuples: list[tuple[OrderControlTvtVisitKey, ...]] = []
    for concrete_set in node_result.concrete_buyer_candidate_sets:
        buyers_tuples.append(concrete_set.buyers_sorted)
    return tuple(buyers_tuples)


# --- public API and result types ---


def test_public_types_importable():
    assert OrderControlTvtMpInlinkBuyerPrefixResult is not None
    assert OrderControlTvtMpConcreteBuyerCandidateSet is not None
    assert OrderControlTvtNodeMpConcreteBuyerCandidateSetResult is not None
    assert OrderControlTvtMpConcreteBuyerCandidateSetResult is not None
    assert build_tvt_mp_concrete_buyer_candidate_sets is not None


def test_result_types_are_frozen_dataclasses():
    result_types = (
        OrderControlTvtMpInlinkBuyerPrefixResult,
        OrderControlTvtMpConcreteBuyerCandidateSet,
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
        OrderControlTvtMpConcreteBuyerCandidateSetResult,
    )
    for result_type in result_types:
        assert dataclasses.is_dataclass(result_type)
        assert result_type.__dataclass_params__.frozen is True


def test_result_type_field_sets_match_specification():
    assert _field_names(OrderControlTvtMpInlinkBuyerPrefixResult) == {
        "node_name",
        "inlink_name",
        "buyer_prefixes_empty_to_max",
    }
    assert _field_names(OrderControlTvtMpConcreteBuyerCandidateSet) == {
        "buyers_sorted",
    }
    assert _field_names(OrderControlTvtNodeMpConcreteBuyerCandidateSetResult) == {
        "node_name",
        "build_status",
        "buyer_candidate_inlink_prefix_results",
        "concrete_buyer_candidate_sets",
    }
    assert _field_names(OrderControlTvtMpConcreteBuyerCandidateSetResult) == {
        "inlink_candidate_physical_order_result",
        "node_concrete_buyer_candidate_set_results",
    }


def test_result_types_reject_field_assignment():
    physical_order_result = _roe_only_input()
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    try:
        node_result.node_name = "other"
        raise AssertionError("Expected FrozenInstanceError")
    except FrozenInstanceError:
        pass
    try:
        result.inlink_candidate_physical_order_result = physical_order_result
        raise AssertionError("Expected FrozenInstanceError")
    except FrozenInstanceError:
        pass


def test_overall_result_keeps_same_input_object():
    physical_order_result = _two_buyer_inlink_input()
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    assert result.inlink_candidate_physical_order_result is physical_order_result


def test_overall_result_does_not_store_candidate_visit_set_result_field():
    assert "candidate_visit_set_result" not in _field_names(
        OrderControlTvtMpConcreteBuyerCandidateSetResult
    )


def test_result_types_have_no_forbidden_fields():
    forbidden_fields = {
        "max_prefix",
        "excluded_right_of_entry_inlink_name",
        "candidate_id",
        "selected_prefix_combination",
        "sellers_sorted",
        "nonparticipating_visits",
        "trade_scope",
        "last_buyer_rank",
        "trade_rank",
        "trade_order",
        "fifo_result",
        "local_virtual_result",
        "economic_evaluation_result",
        "surplus",
        "payment",
        "compensation",
        "baseline_rank_by_visit_key",
        "candidate_visit_set_result",
    }
    result_types = (
        OrderControlTvtMpInlinkBuyerPrefixResult,
        OrderControlTvtMpConcreteBuyerCandidateSet,
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
        OrderControlTvtMpConcreteBuyerCandidateSetResult,
    )
    for result_type in result_types:
        overlap = forbidden_fields & _field_names(result_type)
        assert overlap == set()


def test_result_types_have_no_update_rollback_or_export_api():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _roe_only_input(),
        participates_by_visit_key=_participates(ROE),
    )
    public_names = dir(result)
    assert "update" not in public_names
    assert "rollback" not in public_names
    assert "export" not in public_names
    assert "to_dict" not in public_names
    assert "export_state" not in public_names


# --- normal generation ---


def test_baseline_information_complete_generates_prefixes_and_concrete_sets():
    physical_order_result = _two_buyer_inlink_input()
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.build_status == COMPLETE
    assert len(node_result.buyer_candidate_inlink_prefix_results) == 2
    assert len(node_result.concrete_buyer_candidate_sets) == 5


def test_right_of_entry_only_candidate_set_has_zero_concrete_sets():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _roe_only_input(),
        participates_by_visit_key=_participates(ROE),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.build_status == COMPLETE
    assert node_result.buyer_candidate_inlink_prefix_results == ()
    assert node_result.concrete_buyer_candidate_sets == ()


def test_no_buyer_candidate_inlink_is_normal_empty_result():
    # Right-of-entry inlink plus an inlink whose physical head is non-participating.
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(NP, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(BEHIND_NP, inlink_name="in_b", vehicle_id=3, arrival=12),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (NP, BEHIND_NP)),
                ),
            ),
        ),
    )
    participates = _participates(ROE, BEHIND_NP)
    participates[NP] = False
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=participates,
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.build_status == COMPLETE
    assert node_result.buyer_candidate_inlink_prefix_results == ()
    assert node_result.concrete_buyer_candidate_sets == ()


def test_multiple_nodes_follow_upstream_node_order():
    first = _two_buyer_inlink_input("junction_a")
    second = _roe_only_input("junction_b")
    physical_order_result = _physical_order_set_result(
        first.candidate_visit_set_result.node_candidate_set_results
        + second.candidate_visit_set_result.node_candidate_set_results,
        first.node_inlink_candidate_physical_order_results
        + second.node_inlink_candidate_physical_order_results,
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_results = result.node_concrete_buyer_candidate_set_results
    assert len(node_results) == 2
    assert node_results[0].node_name == "junction_a"
    assert node_results[1].node_name == "junction_b"
    assert len(node_results[0].concrete_buyer_candidate_sets) == 5
    assert node_results[1].concrete_buyer_candidate_sets == ()


def test_nodes_return_independent_results():
    complete_input = _two_buyer_inlink_input("junction_a")
    empty_input = _empty_status_input("junction_b", NOT_BUILT_NO_RIGHT_OF_ENTRY)
    physical_order_result = _physical_order_set_result(
        complete_input.candidate_visit_set_result.node_candidate_set_results
        + empty_input.candidate_visit_set_result.node_candidate_set_results,
        complete_input.node_inlink_candidate_physical_order_results
        + empty_input.node_inlink_candidate_physical_order_results,
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    first_node = result.node_concrete_buyer_candidate_set_results[0]
    second_node = result.node_concrete_buyer_candidate_set_results[1]
    assert first_node.build_status == COMPLETE
    assert len(first_node.concrete_buyer_candidate_sets) == 5
    assert second_node.build_status == NOT_BUILT_NO_RIGHT_OF_ENTRY
    assert second_node.buyer_candidate_inlink_prefix_results == ()
    assert second_node.concrete_buyer_candidate_sets == ()


# --- non-generation statuses ---


def _assert_empty_non_generation_result(build_status):
    physical_order_result = _empty_status_input("merge", build_status)
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key={},
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.node_name == "merge"
    assert node_result.build_status == build_status
    assert node_result.buyer_candidate_inlink_prefix_results == ()
    assert node_result.concrete_buyer_candidate_sets == ()


def test_not_built_no_right_of_entry_returns_empty_results():
    _assert_empty_non_generation_result(NOT_BUILT_NO_RIGHT_OF_ENTRY)


def test_not_built_unresolved_arrivals_returns_empty_results():
    _assert_empty_non_generation_result(NOT_BUILT_UNRESOLVED_ARRIVALS)


def test_unresolved_right_of_entry_passage_returns_empty_results():
    _assert_empty_non_generation_result(UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE)


def test_unresolved_candidate_passages_returns_empty_results():
    _assert_empty_non_generation_result(UNRESOLVED_CANDIDATE_PASSAGES)


def test_not_generated_status_does_not_validate_participation_mapping():
    statuses = (
        NOT_BUILT_NO_RIGHT_OF_ENTRY,
        NOT_BUILT_UNRESOLVED_ARRIVALS,
        UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
        UNRESOLVED_CANDIDATE_PASSAGES,
    )
    for build_status in statuses:
        candidate_visits = (
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        )
        physical_order_result = _physical_order_set_result(
            (
                _node_candidate_result(
                    "merge",
                    build_status=build_status,
                    right_of_entry_visit_key=ROE,
                    candidate_visits=candidate_visits,
                ),
            ),
            (
                _node_inlink_result(
                    "merge",
                    build_status=build_status,
                    inlink_orders=(
                        _inlink_physical_order("merge", "in_a", (ROE,)),
                        _inlink_physical_order("merge", "in_b", (B1,)),
                    ),
                ),
            ),
        )
        result = build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key={ROE: 1, B1: "True"},
        )
        node_result = result.node_concrete_buyer_candidate_set_results[0]
        assert node_result.buyer_candidate_inlink_prefix_results == ()
        assert node_result.concrete_buyer_candidate_sets == ()


def test_unresolved_candidate_passages_does_not_generate_even_with_candidates():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", passage=None),
        _candidate_visit(B1, inlink_name="in_b", passage=None),
        _candidate_visit(B2, inlink_name="in_b", passage=None),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=UNRESOLVED_CANDIDATE_PASSAGES,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=UNRESOLVED_CANDIDATE_PASSAGES,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B1, B2)),
                ),
            ),
        ),
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.build_status == UNRESOLVED_CANDIDATE_PASSAGES
    assert node_result.buyer_candidate_inlink_prefix_results == ()
    assert node_result.concrete_buyer_candidate_sets == ()


# --- right-of-entry inlink ---


def test_right_of_entry_inlink_excluded_from_prefix_results():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    inlink_names = []
    for prefix_result in node_result.buyer_candidate_inlink_prefix_results:
        inlink_names.append(prefix_result.inlink_name)
    assert "in_a" not in inlink_names
    assert inlink_names == ["in_b", "in_c"]


def test_right_of_entry_visit_not_in_concrete_sets():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    for concrete_set in node_result.concrete_buyer_candidate_sets:
        assert ROE not in concrete_set.buyers_sorted
        assert len(concrete_set.buyers_sorted) > 0


def test_other_candidates_on_right_of_entry_inlink_not_buyers():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(ROE_FOLLOWER, inlink_name="in_a", vehicle_id=2, arrival=11),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=3, arrival=12),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE, ROE_FOLLOWER)),
                    _inlink_physical_order("merge", "in_b", (B1,)),
                ),
            ),
        ),
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, ROE_FOLLOWER, B1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.buyer_candidate_inlink_prefix_results[0].inlink_name == "in_b"
    assert _buyers_tuples(node_result) == ((B1,),)
    for concrete_set in node_result.concrete_buyer_candidate_sets:
        assert ROE_FOLLOWER not in concrete_set.buyers_sorted


def test_does_not_modify_upstream_candidate_visits():
    physical_order_result = _two_buyer_inlink_input()
    original_visits = (
        physical_order_result.candidate_visit_set_result.node_candidate_set_results[0].candidate_visits
    )
    build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    later_visits = (
        physical_order_result.candidate_visit_set_result.node_candidate_set_results[0].candidate_visits
    )
    assert later_visits is original_visits
    assert later_visits == (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(C1, inlink_name="in_c", vehicle_id=4, arrival=11),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=12),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=13),
    )


def test_does_not_modify_upstream_inlink_physical_orders():
    physical_order_result = _two_buyer_inlink_input()
    original_orders = (
        physical_order_result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders
    )
    original_keys = original_orders[1].candidate_visit_keys_head_to_tail
    build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    later_orders = (
        physical_order_result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders
    )
    assert later_orders is original_orders
    assert later_orders[1].candidate_visit_keys_head_to_tail is original_keys
    assert later_orders[1].candidate_visit_keys_head_to_tail == (B1, B2)


def test_result_has_no_excluded_right_of_entry_inlink_name():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert not hasattr(node_result, "excluded_right_of_entry_inlink_name")
    assert "excluded_right_of_entry_inlink_name" not in _field_names(
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult
    )


# --- maximum prefix ---


def test_max_prefix_is_leading_participating_run():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=12),
        _candidate_visit(NP, inlink_name="in_b", vehicle_id=4, arrival=13),
        _candidate_visit(BEHIND_NP, inlink_name="in_b", vehicle_id=5, arrival=14),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order(
                        "merge",
                        "in_b",
                        (B1, B2, NP, BEHIND_NP),
                    ),
                ),
            ),
        ),
    )
    participates = _participates(ROE, B1, B2, BEHIND_NP)
    participates[NP] = False
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=participates,
    )
    prefix_result = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[0]
    assert prefix_result.buyer_prefixes_empty_to_max[0] == ()
    assert prefix_result.buyer_prefixes_empty_to_max[-1] == (B1, B2)


def test_nonparticipating_physical_head_excludes_inlink():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(NP, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(B1, inlink_name="in_c", vehicle_id=3, arrival=12),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (NP,)),
                    _inlink_physical_order("merge", "in_c", (B1,)),
                ),
            ),
        ),
    )
    participates = _participates(ROE, B1)
    participates[NP] = False
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=participates,
    )
    prefix_results = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results
    assert len(prefix_results) == 1
    assert prefix_results[0].inlink_name == "in_c"


def test_participating_then_nonparticipating_then_participating_stops_at_first_nonparticipant():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=12),
        _candidate_visit(NP, inlink_name="in_b", vehicle_id=4, arrival=13),
        _candidate_visit(BEHIND_NP, inlink_name="in_b", vehicle_id=5, arrival=14),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order(
                        "merge",
                        "in_b",
                        (B1, B2, NP, BEHIND_NP),
                    ),
                ),
            ),
        ),
    )
    participates = _participates(ROE, B1, B2, BEHIND_NP)
    participates[NP] = False
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=participates,
    )
    max_prefix = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[0].buyer_prefixes_empty_to_max[-1]
    assert max_prefix == (B1, B2)
    assert NP not in max_prefix
    assert BEHIND_NP not in max_prefix
    for concrete_set in result.node_concrete_buyer_candidate_set_results[0].concrete_buyer_candidate_sets:
        assert NP not in concrete_set.buyers_sorted
        assert BEHIND_NP not in concrete_set.buyers_sorted


def test_all_participating_inlink_uses_full_physical_column():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    prefix_b = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[0]
    prefix_c = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[1]
    assert prefix_b.buyer_prefixes_empty_to_max[-1] == (B1, B2)
    assert prefix_c.buyer_prefixes_empty_to_max[-1] == (C1,)


def test_each_buyer_inlink_starts_with_empty_prefix_and_grows_one_visit():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    prefix_b = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[0]
    assert prefix_b.buyer_prefixes_empty_to_max == (
        (),
        (B1,),
        (B1, B2),
    )
    prefix_c = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[1]
    assert prefix_c.buyer_prefixes_empty_to_max == (
        (),
        (C1,),
    )


def test_prefix_visit_order_is_snapshot_physical_order():
    # Physical head is B2 (closer to the Node); official baseline has B1 first.
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=12),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B2, B1)),
                ),
            ),
        ),
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2),
    )
    prefix_b = result.node_concrete_buyer_candidate_set_results[0].buyer_candidate_inlink_prefix_results[0]
    assert prefix_b.buyer_prefixes_empty_to_max == (
        (),
        (B2,),
        (B2, B1),
    )


def test_zero_nonparticipants_uses_same_general_prefix_rule():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.buyer_candidate_inlink_prefix_results[0].buyer_prefixes_empty_to_max[-1] == (
        B1,
        B2,
    )
    assert len(node_result.concrete_buyer_candidate_sets) == 5


# --- product and concrete sets ---


def test_two_inlink_product_has_five_handwritten_concrete_sets():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    buyers = _buyers_tuples(node_result)
    # Axes are in_b then in_c, following upstream inlink_candidate_physical_orders.
    # itertools.product enumerates the last axis fastest.
    assert buyers == (
        (C1,),
        (B1,),
        (C1, B1),
        (B1, B2),
        (C1, B1, B2),
    )
    assert len(buyers) == 5


def test_all_empty_combination_is_excluded_and_partial_empty_combinations_remain():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    buyers = _buyers_tuples(result.node_concrete_buyer_candidate_set_results[0])
    assert () not in buyers
    assert (B1,) in buyers
    assert (C1,) in buyers
    assert (B1, B2) in buyers


def test_concrete_sets_are_nonempty_unique_participating_and_exclude_right_of_entry():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    buyers = _buyers_tuples(result.node_concrete_buyer_candidate_set_results[0])
    seen = []
    for buyers_sorted in buyers:
        assert len(buyers_sorted) > 0
        assert len(buyers_sorted) == len(set(buyers_sorted))
        assert ROE not in buyers_sorted
        for visit_key in buyers_sorted:
            assert visit_key in {B1, B2, C1}
        assert buyers_sorted not in seen
        seen.append(buyers_sorted)


# --- official baseline relative order ---


def test_merged_buyers_follow_candidate_visits_baseline_order_not_inlink_axis_order():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    buyers = _buyers_tuples(result.node_concrete_buyer_candidate_set_results[0])
    # inlink axis order is B then C, but official baseline order is C1 before B1.
    assert (C1, B1) in buyers
    assert (B1, C1) not in buyers
    assert (C1, B1, B2) in buyers
    assert (B1, B2, C1) not in buyers


def test_physical_versus_baseline_order_are_not_confused():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=12),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B2, B1)),
                ),
            ),
        ),
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.buyer_candidate_inlink_prefix_results[0].buyer_prefixes_empty_to_max[-1] == (
        B2,
        B1,
    )
    assert _buyers_tuples(node_result) == (
        (B2,),
        (B1, B2),
    )


def test_participation_is_not_used_to_decide_baseline_order():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(NP, inlink_name="in_d", vehicle_id=2, arrival=11),
        _candidate_visit(C1, inlink_name="in_c", vehicle_id=3, arrival=12),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=4, arrival=13),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B1,)),
                    _inlink_physical_order("merge", "in_c", (C1,)),
                    _inlink_physical_order("merge", "in_d", (NP,)),
                ),
            ),
        ),
    )
    participates = _participates(ROE, C1, B1)
    participates[NP] = False
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=participates,
    )
    buyers = _buyers_tuples(result.node_concrete_buyer_candidate_set_results[0])
    assert (C1, B1) in buyers
    assert (B1, C1) not in buyers


# --- participation mapping ---


def test_missing_candidate_visit_key_raises_value_error():
    physical_order_result = _two_buyer_inlink_input()
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1, B2),
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "missing candidate VisitKey" in message
        assert repr(C1) in message


def test_missing_non_right_of_entry_candidate_visit_key_raises_value_error():
    physical_order_result = _two_buyer_inlink_input()
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1, C1),
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        assert repr(B2) in str(error)


def test_participation_value_one_raises_value_error():
    mapping = _participates(ROE, B1, B2, C1)
    mapping[B2] = 1
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            _two_buyer_inlink_input(),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "must be a Python bool" in message
        assert "int" in message
        assert repr(B2) in message


def test_participation_value_zero_raises_value_error():
    mapping = _participates(ROE, B1, B2, C1)
    mapping[B1] = 0
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            _two_buyer_inlink_input(),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "must be a Python bool" in message
        assert "int" in message


def test_participation_string_true_raises_value_error():
    mapping = _participates(ROE, B1, B2, C1)
    mapping[C1] = "True"
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            _two_buyer_inlink_input(),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "must be a Python bool" in message
        assert "str" in message
        assert "True" in message


def test_numpy_bool_raises_value_error():
    mapping = _participates(ROE, B1, B2, C1)
    mapping[B1] = np.bool_(True)
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            _two_buyer_inlink_input(),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "must be a Python bool" in message
        assert "bool_" in message or "numpy" in message.lower() or "bool" in message


def test_extra_visit_keys_are_allowed_and_not_used():
    mapping = _participates(ROE, B1, B2, C1, D1)
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=mapping,
    )
    buyers = _buyers_tuples(result.node_concrete_buyer_candidate_set_results[0])
    for buyers_sorted in buyers:
        assert D1 not in buyers_sorted
    assert len(buyers) == 5


def test_does_not_modify_participation_mapping():
    mapping = _participates(ROE, B1, B2, C1)
    original_items = dict(mapping)
    build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=mapping,
    )
    assert mapping == original_items


def test_right_of_entry_false_raises_runtime_error():
    mapping = _participates(B1, B2, C1)
    mapping[ROE] = False
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            _two_buyer_inlink_input(),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "right-of-entry" in message
        assert repr(ROE) in message


def test_nonparticipating_non_roe_visit_is_prefix_boundary():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(NP, inlink_name="in_b", vehicle_id=3, arrival=12),
        _candidate_visit(BEHIND_NP, inlink_name="in_b", vehicle_id=4, arrival=13),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B1, NP, BEHIND_NP)),
                ),
            ),
        ),
    )
    participates = _participates(ROE, B1, BEHIND_NP)
    participates[NP] = False
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=participates,
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.buyer_candidate_inlink_prefix_results[0].buyer_prefixes_empty_to_max == (
        (),
        (B1,),
    )
    assert _buyers_tuples(node_result) == ((B1,),)


# --- serious inconsistencies ---


def test_node_result_count_mismatch_raises_runtime_error():
    complete_input = _two_buyer_inlink_input()
    physical_order_result = OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=complete_input.candidate_visit_set_result,
        node_inlink_candidate_physical_order_results=(),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1, B2, C1),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "count" in message
        assert "1" in message
        assert "0" in message


def test_node_name_mismatch_raises_runtime_error():
    candidate_result = _node_candidate_result(
        "junction_a",
        build_status=COMPLETE,
        right_of_entry_visit_key=ROE,
        candidate_visits=(_candidate_visit(ROE, inlink_name="in_a"),),
    )
    inlink_result = _node_inlink_result(
        "junction_b",
        build_status=COMPLETE,
        inlink_orders=(_inlink_physical_order("junction_b", "in_a", (ROE,)),),
    )
    physical_order_result = _physical_order_set_result(
        (candidate_result,),
        (inlink_result,),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "index 0" in message
        assert "junction_a" in message
        assert "junction_b" in message


def test_build_status_mismatch_raises_runtime_error():
    candidate_result = _node_candidate_result(
        "merge",
        build_status=COMPLETE,
        right_of_entry_visit_key=ROE,
        candidate_visits=(_candidate_visit(ROE, inlink_name="in_a"),),
    )
    inlink_result = _node_inlink_result(
        "merge",
        build_status=UNRESOLVED_CANDIDATE_PASSAGES,
        inlink_orders=(_inlink_physical_order("merge", "in_a", (ROE,)),),
    )
    physical_order_result = _physical_order_set_result(
        (candidate_result,),
        (inlink_result,),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "index 0" in message
        assert "merge" in message
        assert "BASELINE_INFORMATION_COMPLETE" in message or "baseline_information_complete" in message


def test_unexpected_status_raises_runtime_error_with_node_name_and_status():
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                right_of_entry_visit_key=ROE,
                candidate_visits=(),
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                inlink_orders=(),
            ),
        ),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key={},
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert _TEST_ONLY_UNEXPECTED_BUILD_STATUS in message
        assert "unexpected" in message


def test_complete_with_none_right_of_entry_raises_runtime_error():
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=None,
                candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(_inlink_physical_order("merge", "in_b", (B1,)),),
            ),
        ),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(B1),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "right_of_entry_visit_key is None" in message


def test_right_of_entry_missing_from_candidate_visits_raises_runtime_error():
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(_inlink_physical_order("merge", "in_b", (B1,)),),
            ),
        ),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(B1),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert repr(ROE) in message
        assert "missing from candidate_visits" in message


def test_visit_key_only_in_candidate_visits_raises_runtime_error():
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(
                    _candidate_visit(ROE, inlink_name="in_a"),
                    _candidate_visit(B1, inlink_name="in_b"),
                ),
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(_inlink_physical_order("merge", "in_a", (ROE,)),),
            ),
        ),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "Only in candidate_visits" in message
        assert repr(B1) in message


def test_visit_key_only_in_physical_orders_raises_runtime_error():
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(_candidate_visit(ROE, inlink_name="in_a"),),
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B1,)),
                ),
            ),
        ),
    )
    try:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "Only in inlink physical orders" in message
        assert repr(B1) in message


def test_inconsistency_on_later_node_does_not_return_partial_result():
    first = _two_buyer_inlink_input("junction_a")
    second_candidate = _node_candidate_result(
        "junction_b",
        build_status=COMPLETE,
        right_of_entry_visit_key=None,
        candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
    )
    second_inlink = _node_inlink_result(
        "junction_b",
        build_status=COMPLETE,
        inlink_orders=(_inlink_physical_order("junction_b", "in_b", (B1,)),),
    )
    physical_order_result = _physical_order_set_result(
        first.candidate_visit_set_result.node_candidate_set_results
        + (second_candidate,),
        first.node_inlink_candidate_physical_order_results + (second_inlink,),
    )
    returned_result = None
    try:
        returned_result = build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1, B2, C1),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert returned_result is None
        assert "junction_b" in str(error)


# --- read-only / no upstream rerun ---


def test_input_object_identity_and_tuples_are_unchanged():
    physical_order_result = _two_buyer_inlink_input()
    mapping = _participates(ROE, B1, B2, C1)
    original_mapping = dict(mapping)
    original_candidate_visits = (
        physical_order_result.candidate_visit_set_result.node_candidate_set_results[0].candidate_visits
    )
    original_inlink_orders = (
        physical_order_result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders
    )
    original_head_to_tail = original_inlink_orders[1].candidate_visit_keys_head_to_tail
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=mapping,
    )
    assert result.inlink_candidate_physical_order_result is physical_order_result
    assert (
        physical_order_result.candidate_visit_set_result.node_candidate_set_results[0].candidate_visits
        is original_candidate_visits
    )
    assert (
        physical_order_result.node_inlink_candidate_physical_order_results[0].inlink_candidate_physical_orders
        is original_inlink_orders
    )
    assert original_inlink_orders[1].candidate_visit_keys_head_to_tail is original_head_to_tail
    assert mapping == original_mapping


def test_does_not_rerun_upstream_processing():
    physical_order_result = _two_buyer_inlink_input()
    with patch(
        "uxsim.order_control_tvt_candidate_visit_set.build_tvt_candidate_visit_set"
    ) as mock_candidate_set, patch(
        "uxsim.order_control_tvt_inlink_candidate_physical_order.build_tvt_inlink_candidate_physical_orders"
    ) as mock_physical_orders, patch(
        "uxsim.order_control_tvt_right_of_entry_selection.select_right_of_entry_decision_window_visits"
    ) as mock_roe, patch(
        "uxsim.order_control_tvt_leading_nonparticipating_confirmation.confirm_leading_nonparticipating_decision_window_visits"
    ) as mock_leading:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1, B2, C1),
        )
        mock_candidate_set.assert_not_called()
        mock_physical_orders.assert_not_called()
        mock_roe.assert_not_called()
        mock_leading.assert_not_called()


def test_does_not_export_collector_or_access_rank_state_world_or_vehicle():
    physical_order_result = _two_buyer_inlink_input()
    with patch(
        "uxsim.order_control_baseline_collector.OrderControlBaselineCollector.export_records",
        create=True,
    ) as mock_export, patch(
        "uxsim.order_control_tvt_node_rank_state.OrderControlTvtNodeRankState",
    ) as mock_rank_state, patch(
        "uxsim.uxsim.World",
        create=True,
    ) as mock_world, patch(
        "uxsim.uxsim.Vehicle",
        create=True,
    ) as mock_vehicle:
        build_tvt_mp_concrete_buyer_candidate_sets(
            physical_order_result,
            participates_by_visit_key=_participates(ROE, B1, B2, C1),
        )
        mock_export.assert_not_called()
        mock_rank_state.assert_not_called()
        mock_world.assert_not_called()
        mock_vehicle.assert_not_called()


def test_single_buyer_inlink_handwritten_prefixes_and_sets():
    candidate_visits = (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(B2, inlink_name="in_b", vehicle_id=3, arrival=12),
    )
    physical_order_result = _physical_order_set_result(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _node_inlink_result(
                "merge",
                build_status=COMPLETE,
                inlink_orders=(
                    _inlink_physical_order("merge", "in_a", (ROE,)),
                    _inlink_physical_order("merge", "in_b", (B1, B2)),
                ),
            ),
        ),
    )
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        physical_order_result,
        participates_by_visit_key=_participates(ROE, B1, B2),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert node_result.buyer_candidate_inlink_prefix_results[0].buyer_prefixes_empty_to_max == (
        (),
        (B1,),
        (B1, B2),
    )
    assert _buyers_tuples(node_result) == (
        (B1,),
        (B1, B2),
    )


def test_buyers_sorted_field_is_tuple():
    result = build_tvt_mp_concrete_buyer_candidate_sets(
        _two_buyer_inlink_input(),
        participates_by_visit_key=_participates(ROE, B1, B2, C1),
    )
    node_result = result.node_concrete_buyer_candidate_set_results[0]
    assert isinstance(node_result.buyer_candidate_inlink_prefix_results, tuple)
    assert isinstance(node_result.concrete_buyer_candidate_sets, tuple)
    for prefix_result in node_result.buyer_candidate_inlink_prefix_results:
        assert isinstance(prefix_result.buyer_prefixes_empty_to_max, tuple)
    for concrete_set in node_result.concrete_buyer_candidate_sets:
        assert isinstance(concrete_set.buyers_sorted, tuple)
        assert len(concrete_set.buyers_sorted) > 0


def _verify_tests_registry() -> None:
    module_path = Path(__file__).resolve()
    module_source = module_path.read_text(encoding="utf-8")
    ast.parse(module_source, filename=str(module_path))

    module_globals = globals()
    defined_test_functions = sorted(
        name
        for name, value in module_globals.items()
        if name.startswith("test_")
        and callable(value)
        and getattr(value, "__module__", None) == __name__
        and getattr(value, "__name__", None) == name
    )

    registered_names = [test_func.__name__ for test_func in TESTS]
    registered_set = set(registered_names)

    if len(registered_names) != len(registered_set):
        duplicates = sorted(
            name
            for name in registered_set
            if registered_names.count(name) > 1
        )
        raise AssertionError(f"Duplicate TESTS entries: {duplicates}")

    missing = sorted(set(defined_test_functions) - registered_set)
    if missing:
        raise AssertionError(f"Unregistered test functions: {missing}")

    unknown = sorted(registered_set - set(defined_test_functions))
    if unknown:
        raise AssertionError(f"TESTS references unknown functions: {unknown}")


def test_tests_list_registration():
    _verify_tests_registry()


TESTS = [
    test_public_types_importable,
    test_result_types_are_frozen_dataclasses,
    test_result_type_field_sets_match_specification,
    test_result_types_reject_field_assignment,
    test_overall_result_keeps_same_input_object,
    test_overall_result_does_not_store_candidate_visit_set_result_field,
    test_result_types_have_no_forbidden_fields,
    test_result_types_have_no_update_rollback_or_export_api,
    test_baseline_information_complete_generates_prefixes_and_concrete_sets,
    test_right_of_entry_only_candidate_set_has_zero_concrete_sets,
    test_no_buyer_candidate_inlink_is_normal_empty_result,
    test_multiple_nodes_follow_upstream_node_order,
    test_nodes_return_independent_results,
    test_not_built_no_right_of_entry_returns_empty_results,
    test_not_built_unresolved_arrivals_returns_empty_results,
    test_unresolved_right_of_entry_passage_returns_empty_results,
    test_unresolved_candidate_passages_returns_empty_results,
    test_not_generated_status_does_not_validate_participation_mapping,
    test_unresolved_candidate_passages_does_not_generate_even_with_candidates,
    test_right_of_entry_inlink_excluded_from_prefix_results,
    test_right_of_entry_visit_not_in_concrete_sets,
    test_other_candidates_on_right_of_entry_inlink_not_buyers,
    test_does_not_modify_upstream_candidate_visits,
    test_does_not_modify_upstream_inlink_physical_orders,
    test_result_has_no_excluded_right_of_entry_inlink_name,
    test_max_prefix_is_leading_participating_run,
    test_nonparticipating_physical_head_excludes_inlink,
    test_participating_then_nonparticipating_then_participating_stops_at_first_nonparticipant,
    test_all_participating_inlink_uses_full_physical_column,
    test_each_buyer_inlink_starts_with_empty_prefix_and_grows_one_visit,
    test_prefix_visit_order_is_snapshot_physical_order,
    test_zero_nonparticipants_uses_same_general_prefix_rule,
    test_two_inlink_product_has_five_handwritten_concrete_sets,
    test_all_empty_combination_is_excluded_and_partial_empty_combinations_remain,
    test_concrete_sets_are_nonempty_unique_participating_and_exclude_right_of_entry,
    test_merged_buyers_follow_candidate_visits_baseline_order_not_inlink_axis_order,
    test_physical_versus_baseline_order_are_not_confused,
    test_participation_is_not_used_to_decide_baseline_order,
    test_missing_candidate_visit_key_raises_value_error,
    test_missing_non_right_of_entry_candidate_visit_key_raises_value_error,
    test_participation_value_one_raises_value_error,
    test_participation_value_zero_raises_value_error,
    test_participation_string_true_raises_value_error,
    test_numpy_bool_raises_value_error,
    test_extra_visit_keys_are_allowed_and_not_used,
    test_does_not_modify_participation_mapping,
    test_right_of_entry_false_raises_runtime_error,
    test_nonparticipating_non_roe_visit_is_prefix_boundary,
    test_node_result_count_mismatch_raises_runtime_error,
    test_node_name_mismatch_raises_runtime_error,
    test_build_status_mismatch_raises_runtime_error,
    test_unexpected_status_raises_runtime_error_with_node_name_and_status,
    test_complete_with_none_right_of_entry_raises_runtime_error,
    test_right_of_entry_missing_from_candidate_visits_raises_runtime_error,
    test_visit_key_only_in_candidate_visits_raises_runtime_error,
    test_visit_key_only_in_physical_orders_raises_runtime_error,
    test_inconsistency_on_later_node_does_not_return_partial_result,
    test_input_object_identity_and_tuples_are_unchanged,
    test_does_not_rerun_upstream_processing,
    test_does_not_export_collector_or_access_rank_state_world_or_vehicle,
    test_single_buyer_inlink_handwritten_prefixes_and_sets,
    test_buyers_sorted_field_is_tuple,
    test_tests_list_registration,
]


if __name__ == "__main__":
    _verify_tests_registry()
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT-MP concrete buyer candidate set tests passed "
        f"({len(TESTS)} tests)."
    )
