# Unit tests for TVT-MP FIFO inspection connection
# (design notes 2, FIFO inspection connection pre-implementation spec).
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_fifo_inspection.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import ast
import dataclasses
import inspect
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
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtMpFifoInspectionSetResult,
    OrderControlTvtNodeMpFifoInspectionResult,
    build_tvt_mp_fifo_inspection_results,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtMpGeneralTradeRankSetResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
    build_tvt_mp_general_trade_ranks,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.order_control_tvt_trade_rank import preserves_inlink_fifo


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
B1 = ("veh_b1", 1)
B2 = ("veh_b2", 1)
NP1 = ("veh_np1", 1)
OUT = ("veh_out", 1)

PRODUCTION_SOURCE_PATH = Path(__file__).resolve().parent / (
    "uxsim/order_control_tvt_mp_fifo_inspection.py"
)
FIFO_SOURCE_PATH = Path(__file__).resolve().parent / (
    "uxsim/order_control_tvt_trade_rank.py"
)

FORBIDDEN_RESULT_FIELDS = (
    "fifo_violation_reason",
    "violating_inlink_name",
    "violating_inlink_names",
    "fifo_diagnostics",
    "fifo_diagnostic_log",
    "true_only_results",
    "false_only_results",
    "participates_by_visit_key",
    "inlink_name_by_visit_key",
    "trade_scope",
    "trade_order",
    "concrete_buyer_candidate_set",
    "concrete_buyer_candidate_set_result",
    "candidate_visit_set_result",
    "local_virtual_result",
    "G",
    "R",
    "surplus",
    "accepted_candidate_flag",
    "selected_candidate_flag",
    "rng_result",
    "payment",
    "compensation",
    "final_confirmed_order",
    "confirmed_rank_block",
    "world",
    "vehicle",
    "node",
    "link",
    "collector",
    "rank_state",
)

FORBIDDEN_PUBLIC_METHODS = (
    "update",
    "rollback",
    "export",
    "export_state",
    "to_dict",
)


class _FifoMaterialStub:
    """Handwritten rank-result stub for one isolated material inconsistency."""

    def __init__(
        self,
        *,
        concrete_buyer_candidate_set,
        last_buyer_rank,
        trade_scope,
        trade_order,
    ):
        self.concrete_buyer_candidate_set = concrete_buyer_candidate_set
        self.last_buyer_rank = last_buyer_rank
        self.trade_scope = trade_scope
        self.trade_order = trade_order


class _TradeOrderWithShortSlice:
    """Sequence whose slice is empty so after_trade length can be tested alone."""

    def __init__(self, items):
        self._items = items

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return ()
        return self._items[key]


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
    concrete_sets: tuple[OrderControlTvtMpConcreteBuyerCandidateSet, ...],
) -> OrderControlTvtNodeMpConcreteBuyerCandidateSetResult:
    return OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
        node_name=node_name,
        build_status=build_status,
        buyer_candidate_inlink_prefix_results=(),
        concrete_buyer_candidate_sets=concrete_sets,
    )


def _rank_set(
    *,
    node_candidate_results: tuple[
        OrderControlTvtNodeCandidateVisitSetResult,
        ...,
    ],
    node_concrete_results: tuple[
        OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
        ...,
    ],
    node_rank_results: tuple[
        OrderControlTvtNodeMpGeneralTradeRankResult,
        ...,
    ],
) -> OrderControlTvtMpGeneralTradeRankSetResult:
    concrete_overall = OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=_physical_order_set_result(
            node_candidate_results
        ),
        node_concrete_buyer_candidate_set_results=node_concrete_results,
    )
    return OrderControlTvtMpGeneralTradeRankSetResult(
        concrete_buyer_candidate_set_result=concrete_overall,
        node_trade_rank_results=node_rank_results,
    )


def _complete_rank_set(
    *,
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
    concrete_sets: tuple[OrderControlTvtMpConcreteBuyerCandidateSet, ...],
    rank_results: tuple,
    node_name: str = "merge",
    right_of_entry_visit_key: OrderControlTvtVisitKey | None = ROE,
) -> OrderControlTvtMpGeneralTradeRankSetResult:
    return _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                node_name,
                build_status=COMPLETE,
                right_of_entry_visit_key=right_of_entry_visit_key,
                candidate_visits=candidate_visits,
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                node_name,
                build_status=COMPLETE,
                concrete_sets=concrete_sets,
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name=node_name,
                build_status=COMPLETE,
                candidate_trade_rank_results=rank_results,
            ),
        ),
    )


def _empty_status_rank_set(
    node_name: str,
    build_status,
) -> OrderControlTvtMpGeneralTradeRankSetResult:
    return _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                node_name,
                build_status=build_status,
                right_of_entry_visit_key=None,
                candidate_visits=(),
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                node_name,
                build_status=build_status,
                concrete_sets=(),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name=node_name,
                build_status=build_status,
                candidate_trade_rank_results=(),
            ),
        ),
    )


def _make_concrete(
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtMpConcreteBuyerCandidateSet:
    return OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=buyers_sorted,
    )


def _make_rank_result(
    *,
    concrete: OrderControlTvtMpConcreteBuyerCandidateSet,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    sellers_sorted: tuple[OrderControlTvtVisitKey, ...],
    nonparticipating_visits_sorted: tuple[OrderControlTvtVisitKey, ...],
    last_buyer_rank: int,
    trade_scope: tuple[OrderControlTvtVisitKey, ...],
    trade_order: tuple[OrderControlTvtVisitKey, ...],
    trade_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
) -> OrderControlTvtMpGeneralTradeRankResult:
    return OrderControlTvtMpGeneralTradeRankResult(
        concrete_buyer_candidate_set=concrete,
        buyers_sorted=buyers_sorted,
        sellers_sorted=sellers_sorted,
        nonparticipating_visits_sorted=nonparticipating_visits_sorted,
        last_buyer_rank=last_buyer_rank,
        trade_scope=trade_scope,
        trade_order=trade_order,
        trade_rank_by_visit_key=trade_rank_by_visit_key,
    )


def _cross_inlink_true_rank_set():
    """ROE on in_a, B1 on in_b: cross-inlink reorder, same-inlink order kept."""
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    rank_set = _complete_rank_set(
        candidate_visits=visits,
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    return rank_set, rank_result


def _same_inlink_buyer_seller_false_rank_set():
    """S1 then B1 on in_b become B1 then S1 after trade: FIFO violation."""
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE, S1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, S1, B1),
        trade_order=(B1, ROE, S1),
        trade_rank_by_visit_key={B1: 1, ROE: 2, S1: 3},
    )
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(S1, inlink_name="in_b"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    rank_set = _complete_rank_set(
        candidate_visits=visits,
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    return rank_set, rank_result


def _inspect_with_fifo_recorder(rank_set):
    recorded_calls: list[tuple] = []
    real_fifo = preserves_inlink_fifo

    def wrapper(before_trade, after_trade, inlink_name_by_visit_key):
        recorded_calls.append(
            (before_trade, after_trade, inlink_name_by_visit_key)
        )
        return real_fifo(
            before_trade,
            after_trade,
            inlink_name_by_visit_key,
        )

    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        wrapper,
    ):
        result = build_tvt_mp_fifo_inspection_results(rank_set)
    return result, recorded_calls


def _first_candidate_inspection(result):
    return result.node_fifo_inspection_results[0].candidate_fifo_inspection_results[0]


def test_public_types_and_function_importable():
    assert OrderControlTvtMpCandidateFifoInspectionResult is not None
    assert OrderControlTvtNodeMpFifoInspectionResult is not None
    assert OrderControlTvtMpFifoInspectionSetResult is not None
    assert callable(build_tvt_mp_fifo_inspection_results)


def test_result_types_are_frozen_dataclasses():
    assert dataclasses.is_dataclass(
        OrderControlTvtMpCandidateFifoInspectionResult
    )
    assert dataclasses.is_dataclass(OrderControlTvtNodeMpFifoInspectionResult)
    assert dataclasses.is_dataclass(OrderControlTvtMpFifoInspectionSetResult)
    assert OrderControlTvtMpCandidateFifoInspectionResult.__dataclass_params__.frozen
    assert OrderControlTvtNodeMpFifoInspectionResult.__dataclass_params__.frozen
    assert OrderControlTvtMpFifoInspectionSetResult.__dataclass_params__.frozen


def test_result_type_field_sets_match_specification():
    candidate_fields = tuple(
        field.name
        for field in dataclasses.fields(
            OrderControlTvtMpCandidateFifoInspectionResult
        )
    )
    node_fields = tuple(
        field.name
        for field in dataclasses.fields(
            OrderControlTvtNodeMpFifoInspectionResult
        )
    )
    overall_fields = tuple(
        field.name
        for field in dataclasses.fields(OrderControlTvtMpFifoInspectionSetResult)
    )
    assert candidate_fields == (
        "general_trade_rank_result",
        "preserves_inlink_fifo",
    )
    assert node_fields == (
        "node_name",
        "build_status",
        "candidate_fifo_inspection_results",
    )
    assert overall_fields == (
        "general_trade_rank_set_result",
        "node_fifo_inspection_results",
    )


def test_result_types_reject_field_assignment():
    rank_set, rank_result = _cross_inlink_true_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    node_result = result.node_fifo_inspection_results[0]
    candidate_result = node_result.candidate_fifo_inspection_results[0]
    try:
        candidate_result.preserves_inlink_fifo = False
        raise AssertionError("expected FrozenInstanceError")
    except FrozenInstanceError:
        pass
    try:
        node_result.node_name = "other"
        raise AssertionError("expected FrozenInstanceError")
    except FrozenInstanceError:
        pass
    try:
        result.general_trade_rank_set_result = rank_set
        raise AssertionError("expected FrozenInstanceError")
    except FrozenInstanceError:
        pass
    assert candidate_result.general_trade_rank_result is rank_result


def test_public_function_takes_one_positional_input():
    signature = inspect.signature(build_tvt_mp_fifo_inspection_results)
    parameters = list(signature.parameters.values())
    assert len(parameters) == 1
    parameter = parameters[0]
    assert parameter.name == "general_trade_rank_set_result"
    assert parameter.default is inspect.Parameter.empty
    assert parameter.kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def test_public_function_rejects_participation_mapping_keyword():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    try:
        build_tvt_mp_fifo_inspection_results(
            rank_set,
            participates_by_visit_key={ROE: True, B1: True},
        )
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


def test_overall_result_keeps_same_input_object():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert result.general_trade_rank_set_result is rank_set


def test_one_candidate_result_keeps_same_general_rank_object():
    rank_set, rank_result = _cross_inlink_true_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    candidate_result = _first_candidate_inspection(result)
    assert candidate_result.general_trade_rank_result is rank_result


def test_preserves_inlink_fifo_field_is_python_bool():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    candidate_result = _first_candidate_inspection(result)
    assert type(candidate_result.preserves_inlink_fifo) is bool
    assert candidate_result.preserves_inlink_fifo is True


def test_result_types_have_no_forbidden_fields_or_public_api():
    result_types = (
        OrderControlTvtMpCandidateFifoInspectionResult,
        OrderControlTvtNodeMpFifoInspectionResult,
        OrderControlTvtMpFifoInspectionSetResult,
    )
    for result_type in result_types:
        field_names = {
            field.name for field in dataclasses.fields(result_type)
        }
        for forbidden_field in FORBIDDEN_RESULT_FIELDS:
            assert forbidden_field not in field_names
        for method_name in FORBIDDEN_PUBLIC_METHODS:
            assert not hasattr(result_type, method_name)


def test_complete_with_rank_candidates_runs_fifo_inspection():
    rank_set, rank_result = _cross_inlink_true_rank_set()
    result, calls = _inspect_with_fifo_recorder(rank_set)
    node_result = result.node_fifo_inspection_results[0]
    assert node_result.node_name == "merge"
    assert node_result.build_status == COMPLETE
    assert len(node_result.candidate_fifo_inspection_results) == 1
    assert len(calls) == 1
    candidate_result = node_result.candidate_fifo_inspection_results[0]
    assert candidate_result.general_trade_rank_result is rank_result
    assert candidate_result.preserves_inlink_fifo is True


def test_complete_with_zero_rank_candidates_is_normal_empty():
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(),
        rank_results=(),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo, patch(
        "uxsim.order_control_tvt_mp_fifo_inspection._build_inlink_name_by_visit_key"
    ) as mock_inlink_dict:
        result = build_tvt_mp_fifo_inspection_results(rank_set)
        mock_fifo.assert_not_called()
        mock_inlink_dict.assert_not_called()
    node_result = result.node_fifo_inspection_results[0]
    assert node_result.build_status == COMPLETE
    assert node_result.candidate_fifo_inspection_results == ()


def test_not_built_no_right_of_entry_returns_empty_and_does_not_call_fifo():
    rank_set = _empty_status_rank_set("merge", NOT_BUILT_NO_RIGHT_OF_ENTRY)
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo, patch(
        "uxsim.order_control_tvt_mp_fifo_inspection._build_inlink_name_by_visit_key"
    ) as mock_inlink_dict:
        result = build_tvt_mp_fifo_inspection_results(rank_set)
        mock_fifo.assert_not_called()
        mock_inlink_dict.assert_not_called()
    node_result = result.node_fifo_inspection_results[0]
    assert node_result.node_name == "merge"
    assert node_result.build_status == NOT_BUILT_NO_RIGHT_OF_ENTRY
    assert node_result.candidate_fifo_inspection_results == ()


def test_not_built_unresolved_arrivals_returns_empty_and_does_not_call_fifo():
    rank_set = _empty_status_rank_set("merge", NOT_BUILT_UNRESOLVED_ARRIVALS)
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo:
        result = build_tvt_mp_fifo_inspection_results(rank_set)
        mock_fifo.assert_not_called()
    assert (
        result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
        == ()
    )


def test_unresolved_right_of_entry_passage_returns_empty_and_does_not_call_fifo():
    rank_set = _empty_status_rank_set(
        "merge",
        UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo:
        result = build_tvt_mp_fifo_inspection_results(rank_set)
        mock_fifo.assert_not_called()
    assert (
        result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
        == ()
    )


def test_unresolved_candidate_passages_returns_empty_and_does_not_call_fifo():
    rank_set = _empty_status_rank_set("merge", UNRESOLVED_CANDIDATE_PASSAGES)
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo:
        result = build_tvt_mp_fifo_inspection_results(rank_set)
        mock_fifo.assert_not_called()
    assert (
        result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
        == ()
    )


def test_unexpected_status_raises_runtime_error_with_node_name_and_status():
    rank_set = _empty_status_rank_set(
        "junction_x",
        _TEST_ONLY_UNEXPECTED_BUILD_STATUS,
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "junction_x" in message
        assert _TEST_ONLY_UNEXPECTED_BUILD_STATUS in message


def test_unexpected_status_on_later_node_does_not_return_partial_result():
    first_concrete = _make_concrete((B1,))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    rank_set = _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(
                    _candidate_visit(ROE, inlink_name="in_a"),
                    _candidate_visit(B1, inlink_name="in_b"),
                ),
            ),
            _node_candidate_result(
                "junction_b",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                right_of_entry_visit_key=None,
                candidate_visits=(),
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                "junction_a",
                build_status=COMPLETE,
                concrete_sets=(first_concrete,),
            ),
            _concrete_node_result(
                "junction_b",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                concrete_sets=(),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="junction_a",
                build_status=COMPLETE,
                candidate_trade_rank_results=(first_rank,),
            ),
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="junction_b",
                build_status=_TEST_ONLY_UNEXPECTED_BUILD_STATUS,
                candidate_trade_rank_results=(),
            ),
        ),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        wraps=preserves_inlink_fifo,
    ) as mock_fifo:
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "junction_b" in message
            assert _TEST_ONLY_UNEXPECTED_BUILD_STATUS in message
        assert mock_fifo.call_count == 1


def test_node_result_count_mismatch_raises_runtime_error():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    rank_set = _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=visits,
            ),
            _node_candidate_result(
                "other",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=visits,
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                "merge",
                build_status=COMPLETE,
                concrete_sets=(concrete,),
            ),
            _concrete_node_result(
                "other",
                build_status=COMPLETE,
                concrete_sets=(concrete,),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="merge",
                build_status=COMPLETE,
                candidate_trade_rank_results=(rank_result,),
            ),
        ),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "expected" in message
        assert "actual" in message
        assert "2" in message
        assert "1" in message


def test_node_name_mismatch_raises_runtime_error():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    rank_set = _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=visits,
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                "other_node",
                build_status=COMPLETE,
                concrete_sets=(concrete,),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="merge",
                build_status=COMPLETE,
                candidate_trade_rank_results=(rank_result,),
            ),
        ),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "index 0" in message
        assert "expected" in message
        assert "actual" in message
        assert "merge" in message
        assert "other_node" in message


def test_build_status_mismatch_raises_runtime_error():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    rank_set = _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                "merge",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=visits,
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                "merge",
                build_status=COMPLETE,
                concrete_sets=(concrete,),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="merge",
                build_status=NOT_BUILT_NO_RIGHT_OF_ENTRY,
                candidate_trade_rank_results=(rank_result,),
            ),
        ),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "index 0" in message
        assert "expected" in message
        assert "actual" in message
        assert "merge" in message


def test_rank_candidate_count_mismatch_raises_runtime_error():
    concrete_a = _make_concrete((B1,))
    concrete_b = _make_concrete((B2,))
    rank_result = _make_rank_result(
        concrete=concrete_a,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(B2, inlink_name="in_c"),
        ),
        concrete_sets=(concrete_a, concrete_b),
        rank_results=(rank_result,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "expected" in message
        assert "actual" in message


def test_concrete_set_identity_mismatch_raises_runtime_error():
    expected_concrete = _make_concrete((B1,))
    actual_concrete = _make_concrete((B1,))
    assert expected_concrete is not actual_concrete
    rank_result = _make_rank_result(
        concrete=actual_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(expected_concrete,),
        rank_results=(rank_result,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "expected" in message
        assert "actual" in message


def test_same_content_different_concrete_object_raises_runtime_error():
    first = _make_concrete((B1,))
    second = _make_concrete((B1,))
    assert first.buyers_sorted == second.buyers_sorted
    assert first is not second
    rank_result = _make_rank_result(
        concrete=second,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(first,),
        rank_results=(rank_result,),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo:
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError:
            pass
        mock_fifo.assert_not_called()


def test_multiple_nodes_follow_upstream_node_order():
    first_concrete = _make_concrete((B1,))
    second_concrete = _make_concrete((B2,))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    second_rank = _make_rank_result(
        concrete=second_concrete,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B2),
        trade_order=(B2, ROE),
        trade_rank_by_visit_key={B2: 1, ROE: 2},
    )
    rank_set = _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(
                    _candidate_visit(ROE, inlink_name="in_a"),
                    _candidate_visit(B1, inlink_name="in_b"),
                ),
            ),
            _node_candidate_result(
                "junction_b",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(
                    _candidate_visit(ROE, inlink_name="in_a"),
                    _candidate_visit(B2, inlink_name="in_c"),
                ),
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                "junction_a",
                build_status=COMPLETE,
                concrete_sets=(first_concrete,),
            ),
            _concrete_node_result(
                "junction_b",
                build_status=COMPLETE,
                concrete_sets=(second_concrete,),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="junction_a",
                build_status=COMPLETE,
                candidate_trade_rank_results=(first_rank,),
            ),
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="junction_b",
                build_status=COMPLETE,
                candidate_trade_rank_results=(second_rank,),
            ),
        ),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert result.node_fifo_inspection_results[0].node_name == "junction_a"
    assert result.node_fifo_inspection_results[1].node_name == "junction_b"
    assert (
        result.node_fifo_inspection_results[0]
        .candidate_fifo_inspection_results[0]
        .general_trade_rank_result
        is first_rank
    )
    assert (
        result.node_fifo_inspection_results[1]
        .candidate_fifo_inspection_results[0]
        .general_trade_rank_result
        is second_rank
    )


def test_candidate_results_follow_upstream_candidate_order():
    first_concrete = _make_concrete((B1,))
    second_concrete = _make_concrete((B2,))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    second_rank = _make_rank_result(
        concrete=second_concrete,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE, B1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, B1, B2),
        trade_order=(B2, ROE, B1),
        trade_rank_by_visit_key={B2: 1, ROE: 2, B1: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(B2, inlink_name="in_c"),
        ),
        concrete_sets=(first_concrete, second_concrete),
        rank_results=(first_rank, second_rank),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    inspections = result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
    assert inspections[0].general_trade_rank_result is first_rank
    assert inspections[1].general_trade_rank_result is second_rank
    assert inspections[0].preserves_inlink_fifo is True
    assert inspections[1].preserves_inlink_fifo is True


def test_before_trade_is_trade_scope_and_after_trade_is_prefix():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE, OUT),
        trade_rank_by_visit_key={B1: 1, ROE: 2, OUT: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(OUT, inlink_name="in_a"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    _result, calls = _inspect_with_fifo_recorder(rank_set)
    assert len(calls) == 1
    before_trade, after_trade, _inlink_dict = calls[0]
    assert before_trade is rank_result.trade_scope
    assert after_trade == rank_result.trade_order[:rank_result.last_buyer_rank]
    assert after_trade == (B1, ROE)
    assert OUT not in before_trade
    assert OUT not in after_trade
    assert len(after_trade) != len(rank_result.trade_order)


def test_fifo_materials_include_buyers_sellers_and_nonparticipants():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=3,
        trade_scope=(ROE, NP1, B1),
        trade_order=(B1, NP1, ROE),
        trade_rank_by_visit_key={B1: 1, NP1: 2, ROE: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(NP1, inlink_name="in_c"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result, calls = _inspect_with_fifo_recorder(rank_set)
    before_trade, after_trade, _inlink_dict = calls[0]
    assert set(before_trade) == {ROE, NP1, B1}
    assert set(after_trade) == {ROE, NP1, B1}
    assert len(before_trade) == len(after_trade)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is True


def test_inlink_dict_is_built_once_per_node_from_candidate_visits():
    first_concrete = _make_concrete((B1,))
    second_concrete = _make_concrete((B2,))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    second_rank = _make_rank_result(
        concrete=second_concrete,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE, B1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, B1, B2),
        trade_order=(B2, ROE, B1),
        trade_rank_by_visit_key={B2: 1, ROE: 2, B1: 3},
    )
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
        _candidate_visit(B2, inlink_name="in_c"),
    )
    rank_set = _complete_rank_set(
        candidate_visits=visits,
        concrete_sets=(first_concrete, second_concrete),
        rank_results=(first_rank, second_rank),
    )
    _result, calls = _inspect_with_fifo_recorder(rank_set)
    assert len(calls) == 2
    first_dict = calls[0][2]
    second_dict = calls[1][2]
    assert first_dict is second_dict
    assert type(first_dict) is dict
    assert first_dict[ROE] == "in_a"
    assert first_dict[B1] == "in_b"
    assert first_dict[B2] == "in_c"


def test_extra_outside_scope_inlink_keys_are_allowed():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE, OUT),
        trade_rank_by_visit_key={B1: 1, ROE: 2, OUT: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(OUT, inlink_name="in_a"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result, calls = _inspect_with_fifo_recorder(rank_set)
    before_trade, after_trade, inlink_dict = calls[0]
    assert OUT in inlink_dict
    assert OUT not in before_trade
    assert OUT not in after_trade
    assert _first_candidate_inspection(result).preserves_inlink_fifo is True


def test_same_inlink_relative_order_preserved_is_true():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE, S1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, S1, B1),
        trade_order=(B1, ROE, S1),
        trade_rank_by_visit_key={B1: 1, ROE: 2, S1: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(S1, inlink_name="in_c"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is True


def test_cross_inlink_order_change_only_is_true():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is True


def test_true_case_with_buyers_sellers_and_nonparticipants():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=3,
        trade_scope=(ROE, NP1, B1),
        trade_order=(B1, NP1, ROE),
        trade_rank_by_visit_key={B1: 1, NP1: 2, ROE: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(NP1, inlink_name="in_c"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is True


def test_buyer_seller_same_inlink_reversal_is_false():
    rank_set, rank_result = _same_inlink_buyer_seller_false_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    candidate_result = _first_candidate_inspection(result)
    assert candidate_result.preserves_inlink_fifo is False
    assert type(candidate_result.preserves_inlink_fifo) is bool
    assert candidate_result.general_trade_rank_result is rank_result


def test_buyer_nonparticipant_same_inlink_reversal_is_false():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=3,
        trade_scope=(ROE, NP1, B1),
        trade_order=(B1, NP1, ROE),
        trade_rank_by_visit_key={B1: 1, NP1: 2, ROE: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(NP1, inlink_name="in_b"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is False


def test_seller_nonparticipant_same_inlink_reversal_is_false():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE, S1),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=4,
        trade_scope=(ROE, S1, NP1, B1),
        trade_order=(B1, ROE, NP1, S1),
        trade_rank_by_visit_key={B1: 1, ROE: 2, NP1: 3, S1: 4},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(S1, inlink_name="in_b"),
            _candidate_visit(NP1, inlink_name="in_b"),
            _candidate_visit(B1, inlink_name="in_c"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is False


def test_one_inlink_violation_among_several_is_false():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE, S1),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=4,
        trade_scope=(ROE, S1, NP1, B1),
        trade_order=(B1, ROE, NP1, S1),
        trade_rank_by_visit_key={B1: 1, ROE: 2, NP1: 3, S1: 4},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(S1, inlink_name="in_b"),
            _candidate_visit(NP1, inlink_name="in_c"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    assert _first_candidate_inspection(result).preserves_inlink_fifo is False


def test_false_does_not_raise_and_keeps_the_candidate():
    rank_set, rank_result = _same_inlink_buyer_seller_false_rank_set()
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    inspections = result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
    assert len(inspections) == 1
    assert inspections[0].preserves_inlink_fifo is False
    assert inspections[0].general_trade_rank_result is rank_result


def test_false_candidate_is_not_reinspected_and_later_candidates_are_inspected():
    false_concrete = _make_concrete((B1,))
    true_concrete = _make_concrete((B2,))
    false_rank = _make_rank_result(
        concrete=false_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE, S1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, S1, B1),
        trade_order=(B1, ROE, S1),
        trade_rank_by_visit_key={B1: 1, ROE: 2, S1: 3},
    )
    true_rank = _make_rank_result(
        concrete=true_concrete,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE, S1, B1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=4,
        trade_scope=(ROE, S1, B1, B2),
        trade_order=(B2, ROE, S1, B1),
        trade_rank_by_visit_key={B2: 1, ROE: 2, S1: 3, B1: 4},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(S1, inlink_name="in_b"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(B2, inlink_name="in_c"),
        ),
        concrete_sets=(false_concrete, true_concrete),
        rank_results=(false_rank, true_rank),
    )
    result, calls = _inspect_with_fifo_recorder(rank_set)
    inspections = result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
    assert len(calls) == 2
    assert inspections[0].preserves_inlink_fifo is False
    assert inspections[1].preserves_inlink_fifo is True
    assert inspections[0].general_trade_rank_result is false_rank
    assert inspections[1].general_trade_rank_result is true_rank


def test_all_candidates_false_still_returns_normal_result():
    first_concrete = _make_concrete((B1,))
    second_concrete = _make_concrete((B2,))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=3,
        trade_scope=(ROE, NP1, B1),
        trade_order=(B1, NP1, ROE),
        trade_rank_by_visit_key={B1: 1, NP1: 2, ROE: 3},
    )
    second_rank = _make_rank_result(
        concrete=second_concrete,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE, B1),
        nonparticipating_visits_sorted=(NP1,),
        last_buyer_rank=4,
        trade_scope=(ROE, NP1, B1, B2),
        trade_order=(B2, NP1, ROE, B1),
        trade_rank_by_visit_key={B2: 1, NP1: 2, ROE: 3, B1: 4},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(NP1, inlink_name="in_b"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(B2, inlink_name="in_b"),
        ),
        concrete_sets=(first_concrete, second_concrete),
        rank_results=(first_rank, second_rank),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    inspections = result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
    assert len(inspections) == 2
    assert inspections[0].preserves_inlink_fifo is False
    assert inspections[1].preserves_inlink_fifo is False
    assert result.general_trade_rank_set_result is rank_set


def test_mixed_true_false_keeps_upstream_candidate_order():
    true_concrete = _make_concrete((B2,))
    false_concrete = _make_concrete((B1,))
    true_rank = _make_rank_result(
        concrete=true_concrete,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE, S1, B1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=4,
        trade_scope=(ROE, S1, B1, B2),
        trade_order=(B2, ROE, S1, B1),
        trade_rank_by_visit_key={B2: 1, ROE: 2, S1: 3, B1: 4},
    )
    false_rank = _make_rank_result(
        concrete=false_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE, S1),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, S1, B1),
        trade_order=(B1, ROE, S1),
        trade_rank_by_visit_key={B1: 1, ROE: 2, S1: 3, B2: 4},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(S1, inlink_name="in_b"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(B2, inlink_name="in_c"),
        ),
        concrete_sets=(true_concrete, false_concrete),
        rank_results=(true_rank, false_rank),
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    inspections = result.node_fifo_inspection_results[0].candidate_fifo_inspection_results
    assert inspections[0].general_trade_rank_result is true_rank
    assert inspections[1].general_trade_rank_result is false_rank
    assert inspections[0].preserves_inlink_fifo is True
    assert inspections[1].preserves_inlink_fifo is False


def test_fifo_function_called_once_per_candidate():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    _result, calls = _inspect_with_fifo_recorder(rank_set)
    assert len(calls) == 1


def test_empty_before_trade_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=1,
        trade_scope=(),
        trade_order=(B1,),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo:
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "empty" in message
        mock_fifo.assert_not_called()


def test_bool_last_buyer_rank_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=True,
        trade_scope=(B1,),
        trade_order=(B1,),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "bool" in message


def test_non_int_last_buyer_rank_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank="2",
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "str" in message


def test_zero_last_buyer_rank_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=0,
        trade_scope=(B1,),
        trade_order=(B1,),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "0" in message


def test_last_buyer_rank_exceeds_trade_order_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=5,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "5" in message


def test_before_trade_length_mismatch_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=2,
        trade_scope=(B1,),
        trade_order=(B1, ROE),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
        ),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "before_trade" in message


def test_after_trade_length_mismatch_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=1,
        trade_scope=(B1,),
        trade_order=_TradeOrderWithShortSlice((B1,)),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(_candidate_visit(B1, inlink_name="in_b"),),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "after_trade" in message


def test_visit_key_set_mismatch_raises_runtime_error():
    concrete = _make_concrete((B1,))
    stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=concrete,
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, OUT),
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(OUT, inlink_name="in_a"),
        ),
        concrete_sets=(concrete,),
        rank_results=(stub,),
    )
    try:
        build_tvt_mp_fifo_inspection_results(rank_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        message = str(error)
        assert "merge" in message
        assert "candidate index 0" in message
        assert "VisitKey" in message


def test_missing_inlink_name_raises_runtime_error():
    concrete = _make_concrete((B1,))
    rank_result = _make_rank_result(
        concrete=concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(_candidate_visit(ROE, inlink_name="in_a"),),
        concrete_sets=(concrete,),
        rank_results=(rank_result,),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo"
    ) as mock_fifo:
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "inlink" in message
        mock_fifo.assert_not_called()


def test_fifo_value_error_is_converted_to_runtime_error_with_chain():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    original = ValueError("test-only fifo material error")
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        side_effect=original,
    ):
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "serious inconsistency" in message
            assert "test-only fifo material error" in message
            assert error.__cause__ is original


def test_fifo_non_bool_return_one_raises_runtime_error():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        return_value=1,
    ):
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "int" in message
            assert "1" in message


def test_fifo_non_bool_return_zero_raises_runtime_error():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        return_value=0,
    ):
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "int" in message


def test_fifo_non_bool_return_numpy_bool_raises_runtime_error():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        return_value=np.bool_(True),
    ):
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "numpy.bool" in message
            assert "np.True_" in message


def test_fifo_non_bool_return_string_raises_runtime_error():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        return_value="true",
    ):
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "str" in message
            assert "true" in message


def test_fifo_non_bool_return_none_raises_runtime_error():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        return_value=None,
    ):
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 0" in message
            assert "None" in message


def test_later_candidate_inconsistency_does_not_process_following_candidates():
    first_concrete = _make_concrete((B1,))
    second_concrete = _make_concrete((B2,))
    third_concrete = _make_concrete((B1, B2))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    second_stub = _FifoMaterialStub(
        concrete_buyer_candidate_set=second_concrete,
        last_buyer_rank=1,
        trade_scope=(),
        trade_order=(B2,),
    )
    third_rank = _make_rank_result(
        concrete=third_concrete,
        buyers_sorted=(B1, B2),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=3,
        trade_scope=(ROE, B1, B2),
        trade_order=(B1, B2, ROE),
        trade_rank_by_visit_key={B1: 1, B2: 2, ROE: 3},
    )
    rank_set = _complete_rank_set(
        candidate_visits=(
            _candidate_visit(ROE, inlink_name="in_a"),
            _candidate_visit(B1, inlink_name="in_b"),
            _candidate_visit(B2, inlink_name="in_c"),
        ),
        concrete_sets=(first_concrete, second_concrete, third_concrete),
        rank_results=(first_rank, second_stub, third_rank),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        wraps=preserves_inlink_fifo,
    ) as mock_fifo:
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "merge" in message
            assert "candidate index 1" in message
        assert mock_fifo.call_count == 1


def test_later_node_inconsistency_does_not_process_following_nodes():
    first_concrete = _make_concrete((B1,))
    first_rank = _make_rank_result(
        concrete=first_concrete,
        buyers_sorted=(B1,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B1),
        trade_order=(B1, ROE),
        trade_rank_by_visit_key={B1: 1, ROE: 2},
    )
    second_expected = _make_concrete((B2,))
    second_actual = _make_concrete((B2,))
    second_rank = _make_rank_result(
        concrete=second_actual,
        buyers_sorted=(B2,),
        sellers_sorted=(ROE,),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(ROE, B2),
        trade_order=(B2, ROE),
        trade_rank_by_visit_key={B2: 1, ROE: 2},
    )
    rank_set = _rank_set(
        node_candidate_results=(
            _node_candidate_result(
                "junction_a",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(
                    _candidate_visit(ROE, inlink_name="in_a"),
                    _candidate_visit(B1, inlink_name="in_b"),
                ),
            ),
            _node_candidate_result(
                "junction_b",
                build_status=COMPLETE,
                right_of_entry_visit_key=ROE,
                candidate_visits=(
                    _candidate_visit(ROE, inlink_name="in_a"),
                    _candidate_visit(B2, inlink_name="in_c"),
                ),
            ),
        ),
        node_concrete_results=(
            _concrete_node_result(
                "junction_a",
                build_status=COMPLETE,
                concrete_sets=(first_concrete,),
            ),
            _concrete_node_result(
                "junction_b",
                build_status=COMPLETE,
                concrete_sets=(second_expected,),
            ),
        ),
        node_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="junction_a",
                build_status=COMPLETE,
                candidate_trade_rank_results=(first_rank,),
            ),
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="junction_b",
                build_status=COMPLETE,
                candidate_trade_rank_results=(second_rank,),
            ),
        ),
    )
    with patch(
        "uxsim.order_control_tvt_mp_fifo_inspection.preserves_inlink_fifo",
        wraps=preserves_inlink_fifo,
    ) as mock_fifo:
        try:
            build_tvt_mp_fifo_inspection_results(rank_set)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            message = str(error)
            assert "junction_b" in message
            assert "candidate index 0" in message
        assert mock_fifo.call_count == 1


def test_does_not_modify_input_or_upstream_results():
    rank_set, rank_result = _cross_inlink_true_rank_set()
    node_rank_results = rank_set.node_trade_rank_results
    candidate_trade_rank_results = (
        node_rank_results[0].candidate_trade_rank_results
    )
    trade_scope = rank_result.trade_scope
    trade_order = rank_result.trade_order
    last_buyer_rank = rank_result.last_buyer_rank
    candidate_visits = (
        rank_set.concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .node_candidate_set_results[0]
        .candidate_visits
    )
    concrete_sets = (
        rank_set.concrete_buyer_candidate_set_result
        .node_concrete_buyer_candidate_set_results[0]
        .concrete_buyer_candidate_sets
    )
    build_tvt_mp_fifo_inspection_results(rank_set)
    assert rank_set.node_trade_rank_results is node_rank_results
    assert (
        node_rank_results[0].candidate_trade_rank_results
        is candidate_trade_rank_results
    )
    assert rank_result.trade_scope is trade_scope
    assert rank_result.trade_order is trade_order
    assert rank_result.last_buyer_rank == last_buyer_rank
    assert (
        rank_set.concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .node_candidate_set_results[0]
        .candidate_visits
        is candidate_visits
    )
    assert (
        rank_set.concrete_buyer_candidate_set_result
        .node_concrete_buyer_candidate_set_results[0]
        .concrete_buyer_candidate_sets
        is concrete_sets
    )


def test_does_not_rerun_upstream_processing():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    with patch(
        "uxsim.order_control_tvt_candidate_visit_set.build_tvt_candidate_visit_set"
    ) as mock_candidate_set, patch(
        "uxsim.order_control_tvt_inlink_candidate_physical_order.build_tvt_inlink_candidate_physical_orders"
    ) as mock_physical_orders, patch(
        "uxsim.order_control_tvt_mp_concrete_buyer_candidate_set.build_tvt_mp_concrete_buyer_candidate_sets"
    ) as mock_concrete, patch(
        "uxsim.order_control_tvt_mp_general_trade_rank.build_tvt_mp_general_trade_ranks"
    ) as mock_general_ranks, patch(
        "uxsim.order_control_tvt_trade_rank.build_tvt_trade_rank_without_nonparticipants"
    ) as mock_existing_rank, patch(
        "uxsim.order_control_tvt_right_of_entry_selection.select_right_of_entry_decision_window_visits"
    ) as mock_roe, patch(
        "uxsim.order_control_tvt_leading_nonparticipating_confirmation.confirm_leading_nonparticipating_decision_window_visits"
    ) as mock_leading:
        build_tvt_mp_fifo_inspection_results(rank_set)
        mock_candidate_set.assert_not_called()
        mock_physical_orders.assert_not_called()
        mock_concrete.assert_not_called()
        mock_general_ranks.assert_not_called()
        mock_existing_rank.assert_not_called()
        mock_roe.assert_not_called()
        mock_leading.assert_not_called()


def test_does_not_export_collector_or_access_rank_state_world_or_vehicle():
    rank_set, _rank_result = _cross_inlink_true_rank_set()
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
    ) as mock_vehicle, patch(
        "uxsim.uxsim.Node",
        create=True,
    ) as mock_node, patch(
        "uxsim.uxsim.Link",
        create=True,
    ) as mock_link:
        build_tvt_mp_fifo_inspection_results(rank_set)
        mock_export.assert_not_called()
        mock_rank_state.assert_not_called()
        mock_world.assert_not_called()
        mock_vehicle.assert_not_called()
        mock_node.assert_not_called()
        mock_link.assert_not_called()


def test_does_not_modify_existing_fifo_function():
    original_source = FIFO_SOURCE_PATH.read_text(encoding="utf-8")
    original_function = preserves_inlink_fifo
    rank_set, _rank_result = _cross_inlink_true_rank_set()
    build_tvt_mp_fifo_inspection_results(rank_set)
    assert FIFO_SOURCE_PATH.read_text(encoding="utf-8") == original_source
    assert preserves_inlink_fifo is original_function


def test_uses_existing_fifo_function_from_trade_rank_module():
    source = PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8")
    assert "from uxsim.order_control_tvt_trade_rank import preserves_inlink_fifo" in source
    assert "build_tvt_mp_general_trade_ranks" not in source
    assert "build_tvt_candidate_visit_set" not in source
    assert "build_tvt_inlink_candidate_physical_orders" not in source
    assert "build_tvt_mp_concrete_buyer_candidate_sets" not in source
    assert "build_tvt_trade_rank_without_nonparticipants" not in source


def test_built_general_rank_result_can_be_inspected():
    visits = (
        _candidate_visit(ROE, inlink_name="in_a"),
        _candidate_visit(B1, inlink_name="in_b"),
    )
    overall_input = OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=_physical_order_set_result(
            (
                _node_candidate_result(
                    "merge",
                    build_status=COMPLETE,
                    right_of_entry_visit_key=ROE,
                    candidate_visits=visits,
                ),
            )
        ),
        node_concrete_buyer_candidate_set_results=(
            _concrete_node_result(
                "merge",
                build_status=COMPLETE,
                concrete_sets=(_make_concrete((B1,)),),
            ),
        ),
    )
    rank_set = build_tvt_mp_general_trade_ranks(
        overall_input,
        participates_by_visit_key={ROE: True, B1: True},
    )
    result = build_tvt_mp_fifo_inspection_results(rank_set)
    candidate_result = _first_candidate_inspection(result)
    upstream_rank = (
        rank_set.node_trade_rank_results[0].candidate_trade_rank_results[0]
    )
    assert candidate_result.general_trade_rank_result is upstream_rank
    assert candidate_result.preserves_inlink_fifo is True
    assert result.general_trade_rank_set_result is rank_set


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
    test_public_types_and_function_importable,
    test_result_types_are_frozen_dataclasses,
    test_result_type_field_sets_match_specification,
    test_result_types_reject_field_assignment,
    test_public_function_takes_one_positional_input,
    test_public_function_rejects_participation_mapping_keyword,
    test_overall_result_keeps_same_input_object,
    test_one_candidate_result_keeps_same_general_rank_object,
    test_preserves_inlink_fifo_field_is_python_bool,
    test_result_types_have_no_forbidden_fields_or_public_api,
    test_complete_with_rank_candidates_runs_fifo_inspection,
    test_complete_with_zero_rank_candidates_is_normal_empty,
    test_not_built_no_right_of_entry_returns_empty_and_does_not_call_fifo,
    test_not_built_unresolved_arrivals_returns_empty_and_does_not_call_fifo,
    test_unresolved_right_of_entry_passage_returns_empty_and_does_not_call_fifo,
    test_unresolved_candidate_passages_returns_empty_and_does_not_call_fifo,
    test_unexpected_status_raises_runtime_error_with_node_name_and_status,
    test_unexpected_status_on_later_node_does_not_return_partial_result,
    test_node_result_count_mismatch_raises_runtime_error,
    test_node_name_mismatch_raises_runtime_error,
    test_build_status_mismatch_raises_runtime_error,
    test_rank_candidate_count_mismatch_raises_runtime_error,
    test_concrete_set_identity_mismatch_raises_runtime_error,
    test_same_content_different_concrete_object_raises_runtime_error,
    test_multiple_nodes_follow_upstream_node_order,
    test_candidate_results_follow_upstream_candidate_order,
    test_before_trade_is_trade_scope_and_after_trade_is_prefix,
    test_fifo_materials_include_buyers_sellers_and_nonparticipants,
    test_inlink_dict_is_built_once_per_node_from_candidate_visits,
    test_extra_outside_scope_inlink_keys_are_allowed,
    test_same_inlink_relative_order_preserved_is_true,
    test_cross_inlink_order_change_only_is_true,
    test_true_case_with_buyers_sellers_and_nonparticipants,
    test_buyer_seller_same_inlink_reversal_is_false,
    test_buyer_nonparticipant_same_inlink_reversal_is_false,
    test_seller_nonparticipant_same_inlink_reversal_is_false,
    test_one_inlink_violation_among_several_is_false,
    test_false_does_not_raise_and_keeps_the_candidate,
    test_false_candidate_is_not_reinspected_and_later_candidates_are_inspected,
    test_all_candidates_false_still_returns_normal_result,
    test_mixed_true_false_keeps_upstream_candidate_order,
    test_fifo_function_called_once_per_candidate,
    test_empty_before_trade_raises_runtime_error,
    test_bool_last_buyer_rank_raises_runtime_error,
    test_non_int_last_buyer_rank_raises_runtime_error,
    test_zero_last_buyer_rank_raises_runtime_error,
    test_last_buyer_rank_exceeds_trade_order_raises_runtime_error,
    test_before_trade_length_mismatch_raises_runtime_error,
    test_after_trade_length_mismatch_raises_runtime_error,
    test_visit_key_set_mismatch_raises_runtime_error,
    test_missing_inlink_name_raises_runtime_error,
    test_fifo_value_error_is_converted_to_runtime_error_with_chain,
    test_fifo_non_bool_return_one_raises_runtime_error,
    test_fifo_non_bool_return_zero_raises_runtime_error,
    test_fifo_non_bool_return_numpy_bool_raises_runtime_error,
    test_fifo_non_bool_return_string_raises_runtime_error,
    test_fifo_non_bool_return_none_raises_runtime_error,
    test_later_candidate_inconsistency_does_not_process_following_candidates,
    test_later_node_inconsistency_does_not_process_following_nodes,
    test_does_not_modify_input_or_upstream_results,
    test_does_not_rerun_upstream_processing,
    test_does_not_export_collector_or_access_rank_state_world_or_vehicle,
    test_does_not_modify_existing_fifo_function,
    test_uses_existing_fifo_function_from_trade_rank_module,
    test_built_general_rank_result_can_be_inspected,
    test_tests_list_registration,
]


if __name__ == "__main__":
    _verify_tests_registry()
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT-MP FIFO inspection tests passed "
        f"({len(TESTS)} tests)."
    )
