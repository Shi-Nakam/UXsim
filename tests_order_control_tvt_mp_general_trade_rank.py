# Unit tests for TVT-MP general trade-rank reconstruction
# (design notes 2, general trade-rank reconstruction pre-implementation spec).
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_general_trade_rank.py
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
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtMpGeneralTradeRankSetResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
    _verify_general_trade_rank_state,
    build_tvt_mp_general_trade_ranks,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.order_control_tvt_trade_rank import (
    build_tvt_trade_rank_without_nonparticipants,
)


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
S1 = ("veh_s1", 1)
S2 = ("veh_s2", 1)
B1 = ("veh_b1", 1)
B2 = ("veh_b2", 1)
NP1 = ("veh_np1", 1)
NP2 = ("veh_np2", 1)
OUT = ("veh_out", 1)
ROE_FOLLOWER = ("veh_roe_follower", 1)

PRODUCTION_SOURCE_PATH = Path(__file__).resolve().parent / (
    "uxsim/order_control_tvt_mp_general_trade_rank.py"
)


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


def _physical_order_set_result(
    node_candidate_results: tuple[OrderControlTvtNodeCandidateVisitSetResult, ...],
) -> OrderControlTvtInlinkCandidatePhysicalOrderSetResult:
    # This component never reads nested right-of-entry selection or
    # inlink snapshot physical orders. Dummy values keep the upstream
    # reference chain intact.
    candidate_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=object(),
        max_tvt_candidate_visit_count=10,
        node_candidate_set_results=node_candidate_results,
    )
    dummy_inlink_results: list[
        OrderControlTvtNodeInlinkCandidatePhysicalOrderResult
    ] = []
    for node_candidate in node_candidate_results:
        dummy_inlink_results.append(
            OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
                node_name=node_candidate.node_name,
                build_status=node_candidate.build_status,
                inlink_candidate_physical_orders=(),
            )
        )
    return OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=candidate_set,
        node_inlink_candidate_physical_order_results=tuple(
            dummy_inlink_results
        ),
    )


def _concrete_node_result(
    node_name: str,
    *,
    build_status,
    buyers_tuples: tuple[tuple[OrderControlTvtVisitKey, ...], ...],
) -> OrderControlTvtNodeMpConcreteBuyerCandidateSetResult:
    concrete_sets: list[OrderControlTvtMpConcreteBuyerCandidateSet] = []
    for buyers_sorted in buyers_tuples:
        concrete_sets.append(
            OrderControlTvtMpConcreteBuyerCandidateSet(
                buyers_sorted=buyers_sorted,
            )
        )
    return OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
        node_name=node_name,
        build_status=build_status,
        buyer_candidate_inlink_prefix_results=(),
        concrete_buyer_candidate_sets=tuple(concrete_sets),
    )


def _overall_input(
    node_candidate_results: tuple[OrderControlTvtNodeCandidateVisitSetResult, ...],
    node_concrete_results: tuple[
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
        ...,
    ],
) -> OrderControlTvtMpConcreteBuyerCandidateSetResult:
    return OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=_physical_order_set_result(
            node_candidate_results
        ),
        node_concrete_buyer_candidate_set_results=node_concrete_results,
    )


def _complete_input(
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
    buyers_tuples: tuple[tuple[OrderControlTvtVisitKey, ...], ...],
    *,
    node_name: str = "merge",
    right_of_entry_visit_key: OrderControlTvtVisitKey | None = ROE,
) -> OrderControlTvtMpConcreteBuyerCandidateSetResult:
    return _overall_input(
        (
            _node_candidate_result(
                node_name,
                build_status=COMPLETE,
                right_of_entry_visit_key=right_of_entry_visit_key,
                candidate_visits=candidate_visits,
            ),
        ),
        (
            _concrete_node_result(
                node_name,
                build_status=COMPLETE,
                buyers_tuples=buyers_tuples,
            ),
        ),
    )


def _empty_status_input(
    node_name: str,
    build_status,
) -> OrderControlTvtMpConcreteBuyerCandidateSetResult:
    return _overall_input(
        (
            _node_candidate_result(
                node_name,
                build_status=build_status,
                right_of_entry_visit_key=None,
                candidate_visits=(),
            ),
        ),
        (
            _concrete_node_result(
                node_name,
                build_status=build_status,
                buyers_tuples=(),
            ),
        ),
    )


def _participates(
    *visit_keys: OrderControlTvtVisitKey,
) -> dict[OrderControlTvtVisitKey, bool]:
    mapping: dict[OrderControlTvtVisitKey, bool] = {}
    for visit_key in visit_keys:
        mapping[visit_key] = True
    return mapping


def _participation_with_false(
    true_keys: tuple[OrderControlTvtVisitKey, ...],
    false_keys: tuple[OrderControlTvtVisitKey, ...],
) -> dict[OrderControlTvtVisitKey, bool]:
    mapping = _participates(*true_keys)
    for visit_key in false_keys:
        mapping[visit_key] = False
    return mapping


def _first_rank_result(
    overall: OrderControlTvtMpGeneralTradeRankSetResult,
) -> OrderControlTvtMpGeneralTradeRankResult:
    return overall.node_trade_rank_results[0].candidate_trade_rank_results[0]


def _direct_rank_result(
    **overrides,
) -> OrderControlTvtMpGeneralTradeRankResult:
    concrete = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=(("veh_a", 1),),
    )
    kwargs = {
        "concrete_buyer_candidate_set": concrete,
        "buyers_sorted": (("veh_a", 1),),
        "sellers_sorted": (),
        "nonparticipating_visits_sorted": (),
        "last_buyer_rank": 1,
        "trade_scope": (("veh_a", 1),),
        "trade_order": (("veh_a", 1),),
        "trade_rank_by_visit_key": {("veh_a", 1): 1},
    }
    kwargs.update(overrides)
    return OrderControlTvtMpGeneralTradeRankResult(**kwargs)


def _field_names(cls) -> set[str]:
    names: set[str] = set()
    for field in dataclasses.fields(cls):
        names.add(field.name)
    return names


def _seller_buyer_visits() -> tuple[OrderControlTvtCandidateVisit, ...]:
    return (
        _candidate_visit(ROE, inlink_name="in_a", vehicle_id=1, arrival=10),
        _candidate_visit(B1, inlink_name="in_b", vehicle_id=2, arrival=11),
        _candidate_visit(OUT, inlink_name="in_b", vehicle_id=3, arrival=12),
    )


def _valid_verify_kwargs() -> dict:
    veh_a = ("veh_a", 1)
    veh_b = ("veh_b", 1)
    return {
        "baseline_order": (veh_a, veh_b),
        "baseline_rank_by_visit_key": {veh_a: 1, veh_b: 2},
        "buyers_sorted": (veh_b,),
        "sellers_sorted": (veh_a,),
        "nonparticipating_visits_sorted": (),
        "last_buyer_rank": 2,
        "trade_scope": (veh_a, veh_b),
        "trade_rank": {veh_b: 1, veh_a: 2},
        "trade_order": (veh_b, veh_a),
        "participates_by_visit_key": {veh_a: True, veh_b: True},
    }


# --- public API and result types ---


def test_public_types_importable():
    assert OrderControlTvtMpGeneralTradeRankResult is not None
    assert OrderControlTvtNodeMpGeneralTradeRankResult is not None
    assert OrderControlTvtMpGeneralTradeRankSetResult is not None
    assert build_tvt_mp_general_trade_ranks is not None


def test_public_function_rejects_participation_mapping_as_positional():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    participates_mapping = _participates(ROE, B1, OUT)
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_mapping,
        )
        raise AssertionError("Expected TypeError for positional mapping")
    except TypeError:
        pass


def test_node_and_overall_result_types_are_frozen_dataclasses():
    assert dataclasses.is_dataclass(OrderControlTvtNodeMpGeneralTradeRankResult)
    assert dataclasses.is_dataclass(OrderControlTvtMpGeneralTradeRankSetResult)
    assert OrderControlTvtNodeMpGeneralTradeRankResult.__dataclass_params__.frozen
    assert OrderControlTvtMpGeneralTradeRankSetResult.__dataclass_params__.frozen


def test_one_candidate_result_is_not_a_dataclass():
    assert dataclasses.is_dataclass(OrderControlTvtMpGeneralTradeRankResult) is False


def test_node_and_overall_field_sets_match_specification():
    assert _field_names(OrderControlTvtNodeMpGeneralTradeRankResult) == {
        "node_name",
        "build_status",
        "candidate_trade_rank_results",
    }
    assert _field_names(OrderControlTvtMpGeneralTradeRankSetResult) == {
        "concrete_buyer_candidate_set_result",
        "node_trade_rank_results",
    }


def test_node_and_overall_reject_field_assignment():
    overall_input = _complete_input(
        _seller_buyer_visits(),
        ((B1,),),
    )
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    node_result = result.node_trade_rank_results[0]
    try:
        node_result.node_name = "other"
        raise AssertionError("Expected FrozenInstanceError")
    except FrozenInstanceError:
        pass
    try:
        result.node_trade_rank_results = ()
        raise AssertionError("Expected FrozenInstanceError")
    except FrozenInstanceError:
        pass


def test_one_candidate_result_keyword_only_constructor():
    result = _direct_rank_result()
    assert result.buyers_sorted == (("veh_a", 1),)


def test_one_candidate_result_rejects_positional_constructor():
    concrete = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=(("veh_a", 1),),
    )
    try:
        OrderControlTvtMpGeneralTradeRankResult(
            concrete,
            (("veh_a", 1),),
            (),
            (),
            1,
            (("veh_a", 1),),
            (("veh_a", 1),),
            {("veh_a", 1): 1},
        )
        raise AssertionError("Expected TypeError for positional args")
    except TypeError:
        pass


def test_one_candidate_result_public_properties_exist():
    result = _direct_rank_result()
    assert result.concrete_buyer_candidate_set is not None
    assert result.buyers_sorted == (("veh_a", 1),)
    assert result.sellers_sorted == ()
    assert result.nonparticipating_visits_sorted == ()
    assert result.last_buyer_rank == 1
    assert result.trade_scope == (("veh_a", 1),)
    assert result.trade_order == (("veh_a", 1),)


def test_one_candidate_result_properties_have_no_setters():
    property_names = (
        "concrete_buyer_candidate_set",
        "buyers_sorted",
        "sellers_sorted",
        "nonparticipating_visits_sorted",
        "last_buyer_rank",
        "trade_scope",
        "trade_order",
    )
    for property_name in property_names:
        property_object = getattr(
            OrderControlTvtMpGeneralTradeRankResult,
            property_name,
        )
        assert isinstance(property_object, property)
        assert property_object.fset is None


def test_one_candidate_result_has_no_forbidden_public_methods():
    public_methods = {
        name
        for name in dir(OrderControlTvtMpGeneralTradeRankResult)
        if callable(getattr(OrderControlTvtMpGeneralTradeRankResult, name))
        and not name.startswith("_")
    }
    assert public_methods == {"assigned_rank", "trade_rank_items"}
    assert not hasattr(OrderControlTvtMpGeneralTradeRankResult, "update")
    assert not hasattr(OrderControlTvtMpGeneralTradeRankResult, "rollback")
    assert not hasattr(OrderControlTvtMpGeneralTradeRankResult, "export")
    assert not hasattr(OrderControlTvtMpGeneralTradeRankResult, "export_state")
    assert not hasattr(OrderControlTvtMpGeneralTradeRankResult, "to_dict")


def test_assigned_rank_returns_rank():
    result = _direct_rank_result()
    assert result.assigned_rank(("veh_a", 1)) == 1


def test_assigned_rank_rejects_invalid_visit_key():
    result = _direct_rank_result()
    try:
        result.assigned_rank("veh_a")
        raise AssertionError("Expected ValueError for invalid VisitKey")
    except ValueError:
        pass


def test_assigned_rank_rejects_missing_visit_key():
    result = _direct_rank_result()
    try:
        result.assigned_rank(("veh_missing", 1))
        raise AssertionError("Expected ValueError for missing VisitKey")
    except ValueError as error:
        assert "not present" in str(error)


def test_assigned_rank_does_not_return_none():
    result = _direct_rank_result()
    rank_value = result.assigned_rank(("veh_a", 1))
    assert rank_value is not None
    assert type(rank_value) is int
    assert rank_value >= 1


def test_trade_rank_items_returns_rank_order_tuple():
    concrete = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=(("veh_b", 1),),
    )
    result = OrderControlTvtMpGeneralTradeRankResult(
        concrete_buyer_candidate_set=concrete,
        buyers_sorted=(("veh_b", 1),),
        sellers_sorted=(("veh_a", 1),),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(("veh_a", 1), ("veh_b", 1)),
        trade_order=(("veh_b", 1), ("veh_a", 1)),
        trade_rank_by_visit_key={("veh_b", 1): 1, ("veh_a", 1): 2},
    )
    items = result.trade_rank_items()
    assert items == ((("veh_b", 1), 1), (("veh_a", 1), 2))
    assert isinstance(items, tuple)


def test_trade_rank_items_does_not_return_internal_dict():
    result = _direct_rank_result()
    items = result.trade_rank_items()
    assert not isinstance(items, dict)


def test_result_defensive_copy_of_rank_dict():
    source_rank_dict = {("veh_a", 1): 1}
    result = _direct_rank_result(trade_rank_by_visit_key=source_rank_dict)
    source_rank_dict[("veh_a", 1)] = 99
    assert result.assigned_rank(("veh_a", 1)) == 1


def test_constructor_rejects_non_concrete_set():
    try:
        _direct_rank_result(concrete_buyer_candidate_set=object())
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_list_for_buyers_sorted():
    try:
        _direct_rank_result(buyers_sorted=[("veh_a", 1)])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_empty_buyers_sorted():
    try:
        _direct_rank_result(buyers_sorted=())
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_duplicate_buyers():
    try:
        _direct_rank_result(buyers_sorted=(("veh_a", 1), ("veh_a", 1)))
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


# Result-class-only minimum constructor contract: empty sellers and
# non-participants tuples are accepted. This does not mean a normal
# TVT-MP public build path can produce zero sellers. In valid upstream
# results, the right-of-entry visit is a participating seller when it
# lies inside trade_scope.
def test_constructor_accepts_empty_sellers_and_nonparticipants():
    result = _direct_rank_result(
        sellers_sorted=(),
        nonparticipating_visits_sorted=(),
    )
    assert result.sellers_sorted == ()
    assert result.nonparticipating_visits_sorted == ()


def test_constructor_rejects_list_for_sellers_sorted():
    try:
        _direct_rank_result(sellers_sorted=[("veh_a", 1)])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_duplicate_sellers_sorted():
    try:
        _direct_rank_result(
            sellers_sorted=(("veh_a", 1), ("veh_a", 1)),
            trade_scope=(("veh_a", 1), ("veh_b", 1)),
            trade_order=(("veh_a", 1), ("veh_b", 1)),
            trade_rank_by_visit_key={("veh_a", 1): 1, ("veh_b", 1): 2},
            buyers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
        )
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_list_for_nonparticipating_visits_sorted():
    try:
        _direct_rank_result(nonparticipating_visits_sorted=[("veh_np", 1)])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_duplicate_nonparticipating_visits_sorted():
    try:
        _direct_rank_result(
            nonparticipating_visits_sorted=(("veh_np", 1), ("veh_np", 1)),
        )
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_list_for_trade_scope():
    try:
        _direct_rank_result(trade_scope=[("veh_a", 1)])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_duplicate_trade_scope():
    try:
        _direct_rank_result(
            trade_scope=(("veh_a", 1), ("veh_a", 1)),
            trade_order=(("veh_a", 1), ("veh_b", 1)),
            trade_rank_by_visit_key={("veh_a", 1): 1, ("veh_b", 1): 2},
            buyers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
        )
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_list_for_trade_order():
    try:
        _direct_rank_result(trade_order=[("veh_a", 1)])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_duplicate_trade_order():
    try:
        _direct_rank_result(
            trade_order=(("veh_a", 1), ("veh_a", 1)),
            trade_rank_by_visit_key={("veh_a", 1): 1, ("veh_b", 1): 2},
            buyers_sorted=(("veh_b", 1),),
            sellers_sorted=(),
            trade_scope=(("veh_a", 1), ("veh_b", 1)),
            last_buyer_rank=2,
        )
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_non_dict_trade_rank_by_visit_key():
    try:
        _direct_rank_result(trade_rank_by_visit_key=[])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_bool_last_buyer_rank():
    try:
        _direct_rank_result(last_buyer_rank=True)
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_zero_last_buyer_rank():
    try:
        _direct_rank_result(last_buyer_rank=0)
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_empty_trade_scope():
    try:
        _direct_rank_result(trade_scope=())
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_empty_trade_order():
    try:
        _direct_rank_result(trade_order=())
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_empty_trade_rank_dict():
    try:
        _direct_rank_result(trade_rank_by_visit_key={})
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_constructor_rejects_bool_rank_value():
    try:
        _direct_rank_result(trade_rank_by_visit_key={("veh_a", 1): True})
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_overall_result_keeps_same_input_object():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    assert result.concrete_buyer_candidate_set_result is overall_input


def test_one_candidate_result_keeps_same_concrete_set_object():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    concrete_set = (
        overall_input.node_concrete_buyer_candidate_set_results[0]
        .concrete_buyer_candidate_sets[0]
    )
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.concrete_buyer_candidate_set is concrete_set


def test_overall_result_does_not_store_candidate_visit_set_result_field():
    assert "candidate_visit_set_result" not in _field_names(
        OrderControlTvtMpGeneralTradeRankSetResult
    )


def test_result_types_have_no_forbidden_fields():
    forbidden_fields = {
        "candidate_id",
        "prefix_combination",
        "max_prefix",
        "excluded_right_of_entry_inlink_name",
        "fifo_result",
        "fifo_violation_reason",
        "local_virtual_result",
        "economic_evaluation_result",
        "surplus",
        "buyer_value_g",
        "seller_compensation_r",
        "payment",
        "compensation",
        "accepted_candidate_flag",
        "selected_candidate_flag",
        "rng_result",
        "final_confirmed_order",
        "confirmed_rank_block",
        "baseline_rank_by_visit_key",
        "world",
        "vehicle",
        "node",
        "link",
        "collector",
        "rank_ledger",
    }
    overlap = forbidden_fields & _field_names(
        OrderControlTvtNodeMpGeneralTradeRankResult
    )
    assert overlap == set()
    overlap = forbidden_fields & _field_names(
        OrderControlTvtMpGeneralTradeRankSetResult
    )
    assert overlap == set()
    one_result = _direct_rank_result()
    for field_name in forbidden_fields:
        assert not hasattr(one_result, field_name)


# --- status ---


def test_complete_with_concrete_sets_builds_ranks():
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    node_result = result.node_trade_rank_results[0]
    assert node_result.build_status == COMPLETE
    assert len(node_result.candidate_trade_rank_results) == 1


def test_complete_with_zero_concrete_sets_is_normal_empty():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
    )
    overall_input = _complete_input(visits, ())
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key={},
    )
    node_result = result.node_trade_rank_results[0]
    assert node_result.build_status == COMPLETE
    assert node_result.candidate_trade_rank_results == ()


def test_complete_with_zero_concrete_sets_does_not_validate_mapping():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    overall_input = _complete_input(visits, ())
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key={B1: 1},
    )
    assert result.node_trade_rank_results[0].candidate_trade_rank_results == ()


def _assert_empty_non_generation_result(build_status):
    result = build_tvt_mp_general_trade_ranks(
        _empty_status_input("merge", build_status),
        participates_by_visit_key={},
    )
    node_result = result.node_trade_rank_results[0]
    assert node_result.node_name == "merge"
    assert node_result.build_status == build_status
    assert node_result.candidate_trade_rank_results == ()


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
        visits = (
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        )
        overall_input = _overall_input(
            (
                _node_candidate_result(
                    "merge",
                    build_status=build_status,
                    right_of_entry_visit_key=ROE,
                    candidate_visits=visits,
                ),
            ),
            (
                _concrete_node_result(
                    "merge",
                    build_status=build_status,
                    buyers_tuples=((B1,),),
                ),
            ),
        )
        result = build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key={},
        )
        assert result.node_trade_rank_results[0].candidate_trade_rank_results == ()


def test_unexpected_status_raises_runtime_error_with_node_name_and_status():
    overall_input = _overall_input(
        (
            _node_candidate_result(
                "merge",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                right_of_entry_visit_key=ROE,
                candidate_visits=(),
            ),
        ),
        (
            _concrete_node_result(
                "merge",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                buyers_tuples=(),
            ),
        ),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key={},
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert _TEST_ONLY_UNEXPECTED_BUILD_STATUS in message
        assert "unexpected" in message


def test_unexpected_status_on_later_node_does_not_return_partial_result():
    first_visits = _seller_buyer_visits()
    overall_input = _overall_input(
        (
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=first_visits,
            ),
            _node_candidate_result(
                "junction_b",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                right_of_entry_visit_key=None,
                candidate_visits=(),
            ),
        ),
        (
            _concrete_node_result(
                "junction_a",
                build_status=COMPLETE,
                buyers_tuples=((B1,),),
            ),
            _concrete_node_result(
                "junction_b",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                buyers_tuples=(),
            ),
        ),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "junction_b" in str(error)


# --- trade_scope and handwritten vacant-slot cases ---


def test_trade_scope_starts_at_candidate_head_and_ends_at_last_buyer():
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.trade_scope == (ROE, B1)
    assert rank_result.trade_scope[0] == ROE
    assert rank_result.trade_scope[-1] == B1
    assert rank_result.last_buyer_rank == 2
    assert len(rank_result.trade_scope) == rank_result.last_buyer_rank
    assert rank_result.trade_scope != (ROE, B1, OUT)


def test_trade_scope_outside_visit_rank_unchanged():
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.assigned_rank(OUT) == 3


def test_trade_scope_outside_nonparticipant_keeps_baseline_rank():
    # Baseline toward target Node: ROE=1, B1=2, OUT=3.
    # trade_scope is (ROE, B1). ROE is the right-of-entry seller inside
    # scope. OUT is non-participating and lies after trade_scope.
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(OUT, inlink_name="in_c"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (OUT,),
        ),
    )
    rank_result = _first_rank_result(result)
    assert ROE in rank_result.sellers_sorted
    assert rank_result.buyers_sorted == (B1,)
    assert OUT not in rank_result.buyers_sorted
    assert OUT not in rank_result.sellers_sorted
    assert OUT not in rank_result.nonparticipating_visits_sorted
    assert OUT not in rank_result.trade_scope
    assert rank_result.assigned_rank(OUT) == 3
    assert rank_result.trade_order.index(OUT) == 2
    assert rank_result.trade_order[2] == OUT
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(ROE) == 2
    assert rank_result.trade_order == (B1, ROE, OUT)


def test_three_way_classification_partitions_trade_scope():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(OUT, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1, OUT),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.buyers_sorted == (B1,)
    assert rank_result.sellers_sorted == (ROE,)
    assert rank_result.nonparticipating_visits_sorted == (NP1,)
    classified = (
        set(rank_result.buyers_sorted)
        | set(rank_result.sellers_sorted)
        | set(rank_result.nonparticipating_visits_sorted)
    )
    assert classified == set(rank_result.trade_scope)
    assert set(rank_result.buyers_sorted).isdisjoint(rank_result.sellers_sorted)
    assert set(rank_result.buyers_sorted).isdisjoint(
        rank_result.nonparticipating_visits_sorted
    )
    assert set(rank_result.sellers_sorted).isdisjoint(
        rank_result.nonparticipating_visits_sorted
    )


def test_right_of_entry_visit_in_scope_is_seller():
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    assert ROE in rank_result.sellers_sorted
    assert ROE not in rank_result.buyers_sorted
    assert ROE not in rank_result.nonparticipating_visits_sorted


def test_right_of_entry_inlink_participating_follower_can_be_seller():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(ROE_FOLLOWER, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, ROE_FOLLOWER, B1),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.sellers_sorted == (ROE, ROE_FOLLOWER)


def test_right_of_entry_inlink_nonparticipant_is_fixed_rank():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.nonparticipating_visits_sorted == (NP1,)
    assert rank_result.assigned_rank(NP1) == 2
    assert NP1 not in rank_result.buyers_sorted
    assert NP1 not in rank_result.sellers_sorted


def test_non_buyer_participant_is_seller():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, S1, B1),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.sellers_sorted == (ROE, S1)


def test_one_nonparticipant():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    # Baseline: ROE=1, NP1=2, B1=3.
    # Fixed: NP1=2. Vacant: 1, 3. Buyer B1=1. Seller ROE=3.
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(NP1) == 2
    assert rank_result.assigned_rank(ROE) == 3
    assert rank_result.trade_order == (B1, NP1, ROE)


def test_multiple_nonparticipants():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(NP2, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (NP1, NP2),
        ),
    )
    rank_result = _first_rank_result(result)
    # Fixed: NP1=2, NP2=3. Vacant: 1, 4. Buyer B1=1. Seller ROE=4.
    assert rank_result.nonparticipating_visits_sorted == (NP1, NP2)
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(NP1) == 2
    assert rank_result.assigned_rank(NP2) == 3
    assert rank_result.assigned_rank(ROE) == 4
    assert rank_result.trade_order == (B1, NP1, NP2, ROE)


def test_nonparticipant_at_trade_scope_head():
    visits = (
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    # Fixed: NP1=1. Vacant: 2, 3. Buyer B1=2. Seller ROE=3.
    assert rank_result.assigned_rank(NP1) == 1
    assert rank_result.assigned_rank(B1) == 2
    assert rank_result.assigned_rank(ROE) == 3
    assert rank_result.trade_order == (NP1, B1, ROE)


def test_nonparticipant_in_trade_scope_middle():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(NP1) == 2
    assert rank_result.assigned_rank(ROE) == 3


def test_distant_fixed_ranks_with_sellers_crossing_them():
    visits = (
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(S2, inlink_name="in_a"),
        _candidate_visit(NP2, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    overall_input = _complete_input(
        visits,
        ((B1,),),
        right_of_entry_visit_key=S2,
    )
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=_participation_with_false(
            (S1, S2, B1),
            (NP1, NP2),
        ),
    )
    rank_result = _first_rank_result(result)
    # Baseline: S1=1, NP1=2, S2=3, NP2=4, B1=5.
    # Fixed: 2, 4. Vacant: 1, 3, 5.
    # Buyer B1=1. Sellers S1=3, S2=5.
    # S1 crosses NP1 (1 -> 3). S2 crosses NP2 (3 -> 5).
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(NP1) == 2
    assert rank_result.assigned_rank(S1) == 3
    assert rank_result.assigned_rank(NP2) == 4
    assert rank_result.assigned_rank(S2) == 5
    assert rank_result.trade_order == (B1, NP1, S1, NP2, S2)
    assert rank_result.assigned_rank(S1) > 1
    assert rank_result.assigned_rank(S2) > 3


def test_buyers_use_leading_vacant_ranks_in_baseline_order():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(B2, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1, B2),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1, B2),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    # Fixed: NP1=2. Vacant: 1, 3, 4. Buyers B1=1, B2=3. Seller ROE=4.
    assert rank_result.buyers_sorted == (B1, B2)
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(B2) == 3
    assert rank_result.assigned_rank(B1) < rank_result.assigned_rank(B2)


def test_sellers_use_remaining_vacant_ranks_in_baseline_order():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, S1, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    # Fixed: NP1=3. Vacant: 1, 2, 4. Buyer B1=1. Sellers ROE=2, S1=4.
    assert rank_result.sellers_sorted == (ROE, S1)
    assert rank_result.assigned_rank(ROE) == 2
    assert rank_result.assigned_rank(S1) == 4
    assert rank_result.assigned_rank(ROE) < rank_result.assigned_rank(S1)


def test_all_sellers_retreat():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, S1, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.assigned_rank(ROE) > 1
    assert rank_result.assigned_rank(S1) > 2


def test_ranks_are_contiguous_unique_and_match_trade_order():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(OUT, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1, OUT),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    items = rank_result.trade_rank_items()
    ranks = []
    for visit_key, rank_value in items:
        ranks.append(rank_value)
        assert rank_result.assigned_rank(visit_key) == rank_value
    assert ranks == [1, 2, 3, 4]
    assert len(set(ranks)) == 4
    assert rank_result.trade_order == (B1, NP1, ROE, OUT)


def test_last_candidate_visit_is_buyer():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.trade_scope == (ROE, B1)
    assert rank_result.trade_scope[-1] == B1
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(ROE) == 2


def test_fifo_materials_are_available_from_result():
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    before_trade = rank_result.trade_scope
    after_trade = rank_result.trade_order[: rank_result.last_buyer_rank]
    assert before_trade == (ROE, B1)
    assert after_trade == (B1, ROE)
    candidate_visits = (
        result.concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .node_candidate_set_results[0]
        .candidate_visits
    )
    inlink_name_by_visit_key: dict[OrderControlTvtVisitKey, str] = {}
    for candidate_visit in candidate_visits:
        inlink_name_by_visit_key[candidate_visit.visit_key] = (
            candidate_visit.inlink_name
        )
    assert inlink_name_by_visit_key[ROE] == "in_a"
    assert inlink_name_by_visit_key[B1] == "in_b"
    assert not hasattr(rank_result, "fifo_result")


# --- participation mapping ---


def test_missing_candidate_visit_key_raises_value_error():
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=_participates(ROE, B1),
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        assert "OUT" in str(error) or "veh_out" in str(error)


def test_missing_outside_scope_candidate_visit_key_raises_value_error():
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=_participates(ROE, B1),
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "missing" in message
        assert "veh_out" in message


def test_participation_value_one_raises_value_error():
    mapping = _participates(ROE, B1, OUT)
    mapping[B1] = 1
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        assert "bool" in str(error)


def test_participation_value_zero_raises_value_error():
    mapping = _participates(ROE, B1, OUT)
    mapping[NP1] = True
    mapping[ROE] = 0
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        assert "bool" in str(error)


def test_participation_string_raises_value_error():
    mapping = _participates(ROE, B1, OUT)
    mapping[B1] = "true"
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        assert "bool" in str(error)


def test_numpy_bool_raises_value_error():
    mapping = _participates(ROE, B1, OUT)
    mapping[B1] = np.bool_(True)
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected ValueError")
    except ValueError as error:
        assert "bool" in str(error)


def test_extra_visit_keys_are_allowed_and_not_used():
    mapping = _participates(ROE, B1, OUT, ("veh_extra", 1))
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=mapping,
    )
    rank_result = _first_rank_result(result)
    try:
        rank_result.assigned_rank(("veh_extra", 1))
        raise AssertionError("Expected ValueError for extra VisitKey")
    except ValueError:
        pass
    assert ("veh_extra", 1) not in rank_result.trade_order


def test_does_not_modify_participation_mapping():
    mapping = _participates(ROE, B1, OUT)
    mapping_copy = dict(mapping)
    build_tvt_mp_general_trade_ranks(
        _complete_input(_seller_buyer_visits(), ((B1,),)),
        participates_by_visit_key=mapping,
    )
    assert mapping == mapping_copy


def test_right_of_entry_false_raises_runtime_error():
    mapping = _participation_with_false((B1, OUT), (ROE,))
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "non-participating" in message


def test_buyer_false_raises_runtime_error():
    mapping = _participation_with_false((ROE, OUT), (B1,))
    try:
        build_tvt_mp_general_trade_ranks(
            _complete_input(_seller_buyer_visits(), ((B1,),)),
            participates_by_visit_key=mapping,
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "veh_b1" in message


def test_nonparticipating_visit_is_classified_to_fixed_rank():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, B1),
            (NP1,),
        ),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.nonparticipating_visits_sorted == (NP1,)
    assert rank_result.assigned_rank(NP1) == 2


# --- public-path serious inconsistencies ---


def test_node_result_count_mismatch_raises_runtime_error():
    complete_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    broken_input = OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=(
            complete_input.inlink_candidate_physical_order_result
        ),
        node_concrete_buyer_candidate_set_results=(),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            broken_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "expected" in message
        assert "actual" in message
        assert "1" in message
        assert "0" in message


def test_node_name_mismatch_raises_runtime_error():
    visits = (_candidate_visit(ROE, inlink_name="in_a"),)
    overall_input = _overall_input(
        (
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=visits,
            ),
        ),
        (
            _concrete_node_result(
                "junction_b",
                build_status=COMPLETE,
                buyers_tuples=(),
            ),
        ),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "index 0" in message
        assert "junction_a" in message
        assert "junction_b" in message
        assert "expected" in message
        assert "actual" in message


def test_build_status_mismatch_raises_runtime_error():
    visits = (_candidate_visit(ROE, inlink_name="in_a"),)
    overall_input = _overall_input(
        (
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=visits,
            ),
        ),
        (
            _concrete_node_result(
                "merge",
                build_status=UNRESOLVED_CANDIDATE_PASSAGES,
                buyers_tuples=(),
            ),
        ),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "index 0" in message
        assert "merge" in message
        assert "expected" in message
        assert "actual" in message


def test_complete_with_none_right_of_entry_raises_runtime_error():
    overall_input = _complete_input(
        _seller_buyer_visits(),
        ((B1,),),
        right_of_entry_visit_key=None,
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "right_of_entry_visit_key is None" in message


def test_right_of_entry_missing_from_candidate_visits_raises_runtime_error():
    visits = (
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(OUT, inlink_name="in_b"),
    )
    overall_input = _complete_input(
        visits,
        ((B1,),),
        right_of_entry_visit_key=ROE,
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(B1, OUT, ROE),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "not present in candidate_visits" in message


def test_buyer_missing_from_candidate_visits_raises_runtime_error():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(OUT, inlink_name="in_b"),
    )
    overall_input = _complete_input(visits, ((B1,),))
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, OUT, B1),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "not present in candidate_visits" in message


def test_empty_buyers_sorted_raises_runtime_error():
    overall_input = _complete_input(_seller_buyer_visits(), ((),))
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "must not be empty" in message


def test_buyers_sorted_baseline_order_mismatch_raises_runtime_error():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(B2, inlink_name="in_b"),
    )
    overall_input = _complete_input(visits, ((B2, B1),))
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, B2),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "baseline relative order" in message


def test_later_candidate_inconsistency_does_not_process_following_candidates():
    overall_input = _complete_input(
        _seller_buyer_visits(),
        ((B1,), ()),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "must not be empty" in str(error)


def test_later_node_inconsistency_does_not_return_partial_result():
    first_visits = _seller_buyer_visits()
    second_visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    overall_input = _overall_input(
        (
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=first_visits,
            ),
            _node_candidate_result(
                "junction_b",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=second_visits,
            ),
        ),
        (
            _concrete_node_result(
                "junction_a",
                build_status=COMPLETE,
                buyers_tuples=((B1,),),
            ),
            _concrete_node_result(
                "junction_b",
                build_status=COMPLETE,
                buyers_tuples=((),),
            ),
        ),
    )
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "junction_b" in str(error)


def test_public_path_propagates_internal_verify_runtime_error():
    with patch(
        "uxsim.order_control_tvt_mp_general_trade_rank._verify_general_trade_rank_state",
        side_effect=RuntimeError("forced general verification failure"),
    ):
        try:
            build_tvt_mp_general_trade_ranks(
                _complete_input(_seller_buyer_visits(), ((B1,),)),
                participates_by_visit_key=_participates(ROE, B1, OUT),
            )
            raise AssertionError("Expected RuntimeError")
        except RuntimeError as error:
            assert "forced general verification failure" in str(error)


# --- internal consistency helper, one anomaly each ---


def test_verify_runtime_error_on_empty_buyers_sorted():
    kwargs = _valid_verify_kwargs()
    kwargs["buyers_sorted"] = ()
    kwargs["sellers_sorted"] = (("veh_a", 1), ("veh_b", 1))
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "buyers_sorted must not be empty" in str(error)


def test_verify_runtime_error_on_buyer_missing_from_baseline():
    kwargs = _valid_verify_kwargs()
    kwargs["buyers_sorted"] = (("veh_missing", 1),)
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "not present in baseline_order" in str(error)


def test_verify_runtime_error_on_nonparticipating_buyer():
    kwargs = _valid_verify_kwargs()
    kwargs["participates_by_visit_key"] = {
        ("veh_a", 1): True,
        ("veh_b", 1): False,
    }
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "not a participating visit" in str(error)


def test_verify_runtime_error_on_buyers_relative_order():
    kwargs = _valid_verify_kwargs()
    veh_a = ("veh_a", 1)
    veh_b = ("veh_b", 1)
    kwargs["buyers_sorted"] = (veh_b, veh_a)
    kwargs["sellers_sorted"] = ()
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "buyers_sorted" in str(error)
        assert "baseline relative order" in str(error)


def test_verify_runtime_error_on_last_buyer_rank_too_small():
    kwargs = _valid_verify_kwargs()
    kwargs["last_buyer_rank"] = 0
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "last_buyer_rank" in str(error)


def test_verify_runtime_error_on_last_buyer_rank_mismatch():
    kwargs = _valid_verify_kwargs()
    kwargs["last_buyer_rank"] = 1
    kwargs["trade_scope"] = (("veh_a", 1),)
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "trailing buyer baseline rank" in str(error)


def test_verify_runtime_error_on_trade_scope_mismatch():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_scope"] = (("veh_b", 1),)
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "trade_scope" in str(error)


def test_verify_runtime_error_on_three_way_overlap():
    kwargs = _valid_verify_kwargs()
    kwargs["sellers_sorted"] = (("veh_a", 1), ("veh_b", 1))
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "overlap" in str(error)


def test_verify_runtime_error_on_three_way_not_covering_scope():
    kwargs = _valid_verify_kwargs()
    kwargs["sellers_sorted"] = ()
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "do not partition trade_scope" in str(error)


def test_verify_runtime_error_on_sellers_relative_order():
    veh_a = ("veh_a", 1)
    veh_b = ("veh_b", 1)
    veh_c = ("veh_c", 1)
    try:
        _verify_general_trade_rank_state(
            baseline_order=(veh_a, veh_b, veh_c),
            baseline_rank_by_visit_key={veh_a: 1, veh_b: 2, veh_c: 3},
            buyers_sorted=(veh_c,),
            sellers_sorted=(veh_b, veh_a),
            nonparticipating_visits_sorted=(),
            last_buyer_rank=3,
            trade_scope=(veh_a, veh_b, veh_c),
            trade_rank={veh_c: 1, veh_a: 2, veh_b: 3},
            trade_order=(veh_c, veh_a, veh_b),
            participates_by_visit_key={
                veh_a: True,
                veh_b: True,
                veh_c: True,
            },
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "sellers_sorted" in str(error)
        assert "baseline relative order" in str(error)


def test_verify_runtime_error_on_nonparticipants_relative_order():
    veh_np1 = ("veh_np1", 1)
    veh_np2 = ("veh_np2", 1)
    veh_b = ("veh_b", 1)
    try:
        _verify_general_trade_rank_state(
            baseline_order=(veh_np1, veh_np2, veh_b),
            baseline_rank_by_visit_key={veh_np1: 1, veh_np2: 2, veh_b: 3},
            buyers_sorted=(veh_b,),
            sellers_sorted=(),
            nonparticipating_visits_sorted=(veh_np2, veh_np1),
            last_buyer_rank=3,
            trade_scope=(veh_np1, veh_np2, veh_b),
            trade_rank={veh_b: 3, veh_np1: 1, veh_np2: 2},
            trade_order=(veh_np1, veh_np2, veh_b),
            participates_by_visit_key={
                veh_np1: False,
                veh_np2: False,
                veh_b: True,
            },
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "nonparticipating_visits_sorted" in str(error)
        assert "baseline relative order" in str(error)


def test_verify_runtime_error_on_trade_rank_key_set_mismatch():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_rank"] = {("veh_b", 1): 1}
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "trade_rank" in str(error)


def test_verify_runtime_error_on_trade_order_key_set_mismatch():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_order"] = (("veh_b", 1),)
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "trade_order" in str(error)


def test_verify_runtime_error_on_trade_order_length_mismatch():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_order"] = (("veh_b", 1), ("veh_a", 1), ("veh_b", 1))
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "length" in str(error)


def test_verify_runtime_error_on_bool_rank_value():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_rank"] = {("veh_b", 1): 1, ("veh_a", 1): True}
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "Python int" in str(error)


def test_verify_runtime_error_on_zero_rank_value():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_rank"] = {("veh_b", 1): 1, ("veh_a", 1): 0}
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert ">= 1" in str(error)


def test_verify_runtime_error_on_duplicate_ranks():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_rank"] = {("veh_b", 1): 1, ("veh_a", 1): 1}
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "1..2" in str(error)


def test_verify_runtime_error_on_missing_rank():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_rank"] = {("veh_b", 1): 1, ("veh_a", 1): 3}
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "1..2" in str(error)


def test_verify_runtime_error_on_trade_order_position_mismatch():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_order"] = (("veh_a", 1), ("veh_b", 1))
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "trade_order position" in str(error)


def test_verify_runtime_error_on_nonparticipant_rank_change():
    veh_np = ("veh_np", 1)
    veh_b = ("veh_b", 1)
    try:
        _verify_general_trade_rank_state(
            baseline_order=(veh_np, veh_b),
            baseline_rank_by_visit_key={veh_np: 1, veh_b: 2},
            buyers_sorted=(veh_b,),
            sellers_sorted=(),
            nonparticipating_visits_sorted=(veh_np,),
            last_buyer_rank=2,
            trade_scope=(veh_np, veh_b),
            trade_rank={veh_b: 1, veh_np: 2},
            trade_order=(veh_b, veh_np),
            participates_by_visit_key={veh_np: False, veh_b: True},
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "non-participating visit" in str(error)
        assert "changed rank" in str(error)


def test_verify_runtime_error_on_seller_not_retreating():
    kwargs = _valid_verify_kwargs()
    kwargs["trade_rank"] = {("veh_a", 1): 1, ("veh_b", 1): 2}
    kwargs["trade_order"] = (("veh_a", 1), ("veh_b", 1))
    try:
        _verify_general_trade_rank_state(**kwargs)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "did not retreat" in str(error)


def test_verify_runtime_error_on_buyer_not_using_leading_vacant():
    veh_a = ("veh_a", 1)
    veh_b = ("veh_b", 1)
    veh_c = ("veh_c", 1)
    try:
        _verify_general_trade_rank_state(
            baseline_order=(veh_a, veh_b, veh_c),
            baseline_rank_by_visit_key={veh_a: 1, veh_b: 2, veh_c: 3},
            buyers_sorted=(veh_b, veh_c),
            sellers_sorted=(veh_a,),
            nonparticipating_visits_sorted=(),
            last_buyer_rank=3,
            trade_scope=(veh_a, veh_b, veh_c),
            trade_rank={veh_c: 1, veh_b: 2, veh_a: 3},
            trade_order=(veh_c, veh_b, veh_a),
            participates_by_visit_key={
                veh_a: True,
                veh_b: True,
                veh_c: True,
            },
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "leading vacant rank" in str(error)


def test_verify_runtime_error_on_seller_not_using_remaining_vacant():
    veh_a = ("veh_a", 1)
    veh_b = ("veh_b", 1)
    veh_c = ("veh_c", 1)
    veh_d = ("veh_d", 1)
    try:
        _verify_general_trade_rank_state(
            baseline_order=(veh_a, veh_b, veh_c, veh_d),
            baseline_rank_by_visit_key={
                veh_a: 1,
                veh_b: 2,
                veh_c: 3,
                veh_d: 4,
            },
            buyers_sorted=(veh_c, veh_d),
            sellers_sorted=(veh_a, veh_b),
            nonparticipating_visits_sorted=(),
            last_buyer_rank=4,
            trade_scope=(veh_a, veh_b, veh_c, veh_d),
            trade_rank={
                veh_c: 1,
                veh_d: 2,
                veh_b: 3,
                veh_a: 4,
            },
            trade_order=(veh_c, veh_d, veh_b, veh_a),
            participates_by_visit_key={
                veh_a: True,
                veh_b: True,
                veh_c: True,
                veh_d: True,
            },
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "remaining vacant rank" in str(error)


def test_verify_runtime_error_on_outside_scope_rank_change():
    veh_a = ("veh_a", 1)
    veh_b = ("veh_b", 1)
    veh_c = ("veh_c", 1)
    try:
        _verify_general_trade_rank_state(
            baseline_order=(veh_a, veh_b, veh_c),
            baseline_rank_by_visit_key={veh_a: 1, veh_b: 2, veh_c: 3},
            buyers_sorted=(veh_a,),
            sellers_sorted=(),
            nonparticipating_visits_sorted=(),
            last_buyer_rank=1,
            trade_scope=(veh_a,),
            trade_rank={veh_a: 1, veh_b: 3, veh_c: 2},
            trade_order=(veh_a, veh_c, veh_b),
            participates_by_visit_key={
                veh_a: True,
                veh_b: True,
                veh_c: True,
            },
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "outside trade_scope" in str(error)


# --- zero non-participants: equivalence with the existing function ---


def _assert_equivalent_to_existing(
    baseline: tuple[OrderControlTvtVisitKey, ...],
    buyers: tuple[OrderControlTvtVisitKey, ...],
    general_result: OrderControlTvtMpGeneralTradeRankResult,
) -> None:
    existing = build_tvt_trade_rank_without_nonparticipants(baseline, buyers)
    assert general_result.buyers_sorted == existing.buyers_sorted
    assert general_result.sellers_sorted == existing.sellers_sorted
    assert general_result.last_buyer_rank == existing.last_buyer_rank
    assert general_result.trade_order == existing.trade_order
    assert general_result.nonparticipating_visits_sorted == ()
    for visit_key in baseline:
        assert general_result.assigned_rank(visit_key) == existing.assigned_rank(
            visit_key
        )
    assert general_result.trade_scope == baseline[: existing.last_buyer_rank]


def test_zero_nonparticipants_single_buyer_matches_existing():
    visits = _seller_buyer_visits()
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    _assert_equivalent_to_existing((ROE, B1, OUT), (B1,), rank_result)
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(ROE) == 2
    assert rank_result.assigned_rank(OUT) == 3


def test_zero_nonparticipants_multiple_buyers_matches_existing():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(B2, inlink_name="in_b"),
        _candidate_visit(OUT, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1, B2),)),
        participates_by_visit_key=_participates(ROE, B1, S1, B2, OUT),
    )
    rank_result = _first_rank_result(result)
    _assert_equivalent_to_existing(
        (ROE, B1, S1, B2, OUT),
        (B1, B2),
        rank_result,
    )
    assert rank_result.assigned_rank(B1) == 1
    assert rank_result.assigned_rank(B2) == 2
    assert rank_result.assigned_rank(ROE) == 3
    assert rank_result.assigned_rank(S1) == 4
    assert rank_result.assigned_rank(OUT) == 5


def test_zero_nonparticipants_multiple_sellers_matches_existing():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, S1, B1),
    )
    rank_result = _first_rank_result(result)
    _assert_equivalent_to_existing((ROE, S1, B1), (B1,), rank_result)
    assert rank_result.sellers_sorted == (ROE, S1)


def test_zero_nonparticipants_outside_scope_matches_existing():
    visits = _seller_buyer_visits()
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    rank_result = _first_rank_result(result)
    _assert_equivalent_to_existing((ROE, B1, OUT), (B1,), rank_result)
    assert rank_result.assigned_rank(OUT) == 3


def test_zero_nonparticipants_last_visit_is_buyer_matches_existing():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1,),)),
        participates_by_visit_key=_participates(ROE, B1),
    )
    rank_result = _first_rank_result(result)
    _assert_equivalent_to_existing((ROE, B1), (B1,), rank_result)


def test_broken_upstream_buyers_order_is_inconsistency_not_resorted():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(B2, inlink_name="in_b"),
    )
    overall_input = _complete_input(visits, ((B2, B1),))
    try:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, B2),
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as error:
        assert "baseline relative order" in str(error)


# --- read-only, no rerun, no FIFO ---


def test_does_not_modify_input_objects():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    candidate_visits = (
        overall_input.inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .node_candidate_set_results[0]
        .candidate_visits
    )
    concrete_sets = (
        overall_input.node_concrete_buyer_candidate_set_results[0]
        .concrete_buyer_candidate_sets
    )
    buyers = concrete_sets[0].buyers_sorted
    mapping = _participates(ROE, B1, OUT)
    mapping_copy = dict(mapping)
    build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=mapping,
    )
    assert (
        overall_input.inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .node_candidate_set_results[0]
        .candidate_visits
        is candidate_visits
    )
    assert (
        overall_input.node_concrete_buyer_candidate_set_results[0]
        .concrete_buyer_candidate_sets
        is concrete_sets
    )
    assert concrete_sets[0].buyers_sorted is buyers
    assert mapping == mapping_copy


def test_does_not_rerun_upstream_processing():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    with patch(
        "uxsim.order_control_tvt_candidate_visit_set.build_tvt_candidate_visit_set"
    ) as mock_candidate_set, patch(
        "uxsim.order_control_tvt_inlink_candidate_physical_order.build_tvt_inlink_candidate_physical_orders"
    ) as mock_physical_orders, patch(
        "uxsim.order_control_tvt_mp_concrete_buyer_candidate_set.build_tvt_mp_concrete_buyer_candidate_sets"
    ) as mock_concrete, patch(
        "uxsim.order_control_tvt_right_of_entry_selection.select_right_of_entry_decision_window_visits"
    ) as mock_roe, patch(
        "uxsim.order_control_tvt_leading_nonparticipating_confirmation.confirm_leading_nonparticipating_decision_window_visits"
    ) as mock_leading:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        mock_candidate_set.assert_not_called()
        mock_physical_orders.assert_not_called()
        mock_concrete.assert_not_called()
        mock_roe.assert_not_called()
        mock_leading.assert_not_called()


def test_does_not_export_collector_or_access_rank_state_world_or_vehicle():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
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
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        mock_export.assert_not_called()
        mock_rank_state.assert_not_called()
        mock_world.assert_not_called()
        mock_vehicle.assert_not_called()


def test_production_source_does_not_call_existing_rank_or_fifo():
    source = PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8")
    assert "build_tvt_trade_rank_without_nonparticipants" not in source
    assert "preserves_inlink_fifo" not in source
    assert "_verify_local_trade_rank_state" not in source


def test_production_does_not_call_existing_rank_function_or_fifo():
    overall_input = _complete_input(_seller_buyer_visits(), ((B1,),))
    with patch(
        "uxsim.order_control_tvt_trade_rank.build_tvt_trade_rank_without_nonparticipants"
    ) as mock_rank, patch(
        "uxsim.order_control_tvt_trade_rank.preserves_inlink_fifo"
    ) as mock_fifo:
        build_tvt_mp_general_trade_ranks(
            overall_input,
            participates_by_visit_key=_participates(ROE, B1, OUT),
        )
        mock_rank.assert_not_called()
        mock_fifo.assert_not_called()


def test_multiple_nodes_follow_upstream_node_order():
    first_visits = _seller_buyer_visits()
    second_visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
    )
    overall_input = _overall_input(
        (
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=first_visits,
            ),
            _node_candidate_result(
                "junction_b",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=second_visits,
            ),
        ),
        (
            _concrete_node_result(
                "junction_a",
                build_status=COMPLETE,
                buyers_tuples=((B1,),),
            ),
            _concrete_node_result(
                "junction_b",
                build_status=COMPLETE,
                buyers_tuples=(),
            ),
        ),
    )
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=_participates(ROE, B1, OUT),
    )
    assert result.node_trade_rank_results[0].node_name == "junction_a"
    assert result.node_trade_rank_results[1].node_name == "junction_b"
    assert len(result.node_trade_rank_results[0].candidate_trade_rank_results) == 1
    assert result.node_trade_rank_results[1].candidate_trade_rank_results == ()


def test_candidate_results_follow_upstream_concrete_set_order():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(B2, inlink_name="in_b"),
    )
    overall_input = _complete_input(visits, ((B1,), (B1, B2)))
    result = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key=_participates(ROE, B1, B2),
    )
    rank_results = result.node_trade_rank_results[0].candidate_trade_rank_results
    assert rank_results[0].buyers_sorted == (B1,)
    assert rank_results[1].buyers_sorted == (B1, B2)


def test_classification_preserves_baseline_relative_order():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(S1, inlink_name="in_c"),
        _candidate_visit(NP1, inlink_name="in_c"),
        _candidate_visit(NP2, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(B2, inlink_name="in_b"),
    )
    result = build_tvt_mp_general_trade_ranks(
        _complete_input(visits, ((B1, B2),)),
        participates_by_visit_key=_participation_with_false(
            (ROE, S1, B1, B2),
            (NP1, NP2),
        ),
    )
    rank_result = _first_rank_result(result)
    assert rank_result.buyers_sorted == (B1, B2)
    assert rank_result.sellers_sorted == (ROE, S1)
    assert rank_result.nonparticipating_visits_sorted == (NP1, NP2)


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
    test_public_function_rejects_participation_mapping_as_positional,
    test_node_and_overall_result_types_are_frozen_dataclasses,
    test_one_candidate_result_is_not_a_dataclass,
    test_node_and_overall_field_sets_match_specification,
    test_node_and_overall_reject_field_assignment,
    test_one_candidate_result_keyword_only_constructor,
    test_one_candidate_result_rejects_positional_constructor,
    test_one_candidate_result_public_properties_exist,
    test_one_candidate_result_properties_have_no_setters,
    test_one_candidate_result_has_no_forbidden_public_methods,
    test_assigned_rank_returns_rank,
    test_assigned_rank_rejects_invalid_visit_key,
    test_assigned_rank_rejects_missing_visit_key,
    test_assigned_rank_does_not_return_none,
    test_trade_rank_items_returns_rank_order_tuple,
    test_trade_rank_items_does_not_return_internal_dict,
    test_result_defensive_copy_of_rank_dict,
    test_constructor_rejects_non_concrete_set,
    test_constructor_rejects_list_for_buyers_sorted,
    test_constructor_rejects_empty_buyers_sorted,
    test_constructor_rejects_duplicate_buyers,
    test_constructor_accepts_empty_sellers_and_nonparticipants,
    test_constructor_rejects_list_for_sellers_sorted,
    test_constructor_rejects_duplicate_sellers_sorted,
    test_constructor_rejects_list_for_nonparticipating_visits_sorted,
    test_constructor_rejects_duplicate_nonparticipating_visits_sorted,
    test_constructor_rejects_list_for_trade_scope,
    test_constructor_rejects_duplicate_trade_scope,
    test_constructor_rejects_list_for_trade_order,
    test_constructor_rejects_duplicate_trade_order,
    test_constructor_rejects_non_dict_trade_rank_by_visit_key,
    test_constructor_rejects_bool_last_buyer_rank,
    test_constructor_rejects_zero_last_buyer_rank,
    test_constructor_rejects_empty_trade_scope,
    test_constructor_rejects_empty_trade_order,
    test_constructor_rejects_empty_trade_rank_dict,
    test_constructor_rejects_bool_rank_value,
    test_overall_result_keeps_same_input_object,
    test_one_candidate_result_keeps_same_concrete_set_object,
    test_overall_result_does_not_store_candidate_visit_set_result_field,
    test_result_types_have_no_forbidden_fields,
    test_complete_with_concrete_sets_builds_ranks,
    test_complete_with_zero_concrete_sets_is_normal_empty,
    test_complete_with_zero_concrete_sets_does_not_validate_mapping,
    test_not_built_no_right_of_entry_returns_empty_results,
    test_not_built_unresolved_arrivals_returns_empty_results,
    test_unresolved_right_of_entry_passage_returns_empty_results,
    test_unresolved_candidate_passages_returns_empty_results,
    test_not_generated_status_does_not_validate_participation_mapping,
    test_unexpected_status_raises_runtime_error_with_node_name_and_status,
    test_unexpected_status_on_later_node_does_not_return_partial_result,
    test_trade_scope_starts_at_candidate_head_and_ends_at_last_buyer,
    test_trade_scope_outside_visit_rank_unchanged,
    test_trade_scope_outside_nonparticipant_keeps_baseline_rank,
    test_three_way_classification_partitions_trade_scope,
    test_right_of_entry_visit_in_scope_is_seller,
    test_right_of_entry_inlink_participating_follower_can_be_seller,
    test_right_of_entry_inlink_nonparticipant_is_fixed_rank,
    test_non_buyer_participant_is_seller,
    test_one_nonparticipant,
    test_multiple_nonparticipants,
    test_nonparticipant_at_trade_scope_head,
    test_nonparticipant_in_trade_scope_middle,
    test_distant_fixed_ranks_with_sellers_crossing_them,
    test_buyers_use_leading_vacant_ranks_in_baseline_order,
    test_sellers_use_remaining_vacant_ranks_in_baseline_order,
    test_all_sellers_retreat,
    test_ranks_are_contiguous_unique_and_match_trade_order,
    test_last_candidate_visit_is_buyer,
    test_fifo_materials_are_available_from_result,
    test_missing_candidate_visit_key_raises_value_error,
    test_missing_outside_scope_candidate_visit_key_raises_value_error,
    test_participation_value_one_raises_value_error,
    test_participation_value_zero_raises_value_error,
    test_participation_string_raises_value_error,
    test_numpy_bool_raises_value_error,
    test_extra_visit_keys_are_allowed_and_not_used,
    test_does_not_modify_participation_mapping,
    test_right_of_entry_false_raises_runtime_error,
    test_buyer_false_raises_runtime_error,
    test_nonparticipating_visit_is_classified_to_fixed_rank,
    test_node_result_count_mismatch_raises_runtime_error,
    test_node_name_mismatch_raises_runtime_error,
    test_build_status_mismatch_raises_runtime_error,
    test_complete_with_none_right_of_entry_raises_runtime_error,
    test_right_of_entry_missing_from_candidate_visits_raises_runtime_error,
    test_buyer_missing_from_candidate_visits_raises_runtime_error,
    test_empty_buyers_sorted_raises_runtime_error,
    test_buyers_sorted_baseline_order_mismatch_raises_runtime_error,
    test_later_candidate_inconsistency_does_not_process_following_candidates,
    test_later_node_inconsistency_does_not_return_partial_result,
    test_public_path_propagates_internal_verify_runtime_error,
    test_verify_runtime_error_on_empty_buyers_sorted,
    test_verify_runtime_error_on_buyer_missing_from_baseline,
    test_verify_runtime_error_on_nonparticipating_buyer,
    test_verify_runtime_error_on_buyers_relative_order,
    test_verify_runtime_error_on_last_buyer_rank_too_small,
    test_verify_runtime_error_on_last_buyer_rank_mismatch,
    test_verify_runtime_error_on_trade_scope_mismatch,
    test_verify_runtime_error_on_three_way_overlap,
    test_verify_runtime_error_on_three_way_not_covering_scope,
    test_verify_runtime_error_on_sellers_relative_order,
    test_verify_runtime_error_on_nonparticipants_relative_order,
    test_verify_runtime_error_on_trade_rank_key_set_mismatch,
    test_verify_runtime_error_on_trade_order_key_set_mismatch,
    test_verify_runtime_error_on_trade_order_length_mismatch,
    test_verify_runtime_error_on_bool_rank_value,
    test_verify_runtime_error_on_zero_rank_value,
    test_verify_runtime_error_on_duplicate_ranks,
    test_verify_runtime_error_on_missing_rank,
    test_verify_runtime_error_on_trade_order_position_mismatch,
    test_verify_runtime_error_on_nonparticipant_rank_change,
    test_verify_runtime_error_on_seller_not_retreating,
    test_verify_runtime_error_on_buyer_not_using_leading_vacant,
    test_verify_runtime_error_on_seller_not_using_remaining_vacant,
    test_verify_runtime_error_on_outside_scope_rank_change,
    test_zero_nonparticipants_single_buyer_matches_existing,
    test_zero_nonparticipants_multiple_buyers_matches_existing,
    test_zero_nonparticipants_multiple_sellers_matches_existing,
    test_zero_nonparticipants_outside_scope_matches_existing,
    test_zero_nonparticipants_last_visit_is_buyer_matches_existing,
    test_broken_upstream_buyers_order_is_inconsistency_not_resorted,
    test_does_not_modify_input_objects,
    test_does_not_rerun_upstream_processing,
    test_does_not_export_collector_or_access_rank_state_world_or_vehicle,
    test_production_source_does_not_call_existing_rank_or_fifo,
    test_production_does_not_call_existing_rank_function_or_fifo,
    test_multiple_nodes_follow_upstream_node_order,
    test_candidate_results_follow_upstream_concrete_set_order,
    test_classification_preserves_baseline_relative_order,
    test_tests_list_registration,
]


if __name__ == "__main__":
    _verify_tests_registry()
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT-MP general trade-rank tests passed "
        f"({len(TESTS)} tests)."
    )
