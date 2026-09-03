# Unit tests for non-participant TVT trade rank (design memo §25.25.32.20).
#
# Run from the repository root:
#   python tests_order_control_tvt_trade_rank.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import numpy as np

from uxsim.order_control_tvt_trade_rank import (
    OrderControlTvtNoNonparticipantTradeRankResult,
    _verify_local_trade_rank_state,
    build_tvt_trade_rank_without_nonparticipants,
    preserves_inlink_fifo,
)


def _baseline(*visit_keys: tuple[str, int]) -> list[tuple[str, int]]:
    return list(visit_keys)


def test_public_types_importable():
    assert OrderControlTvtNoNonparticipantTradeRankResult is not None
    assert build_tvt_trade_rank_without_nonparticipants is not None
    assert preserves_inlink_fifo is not None


def test_single_buyer_rank():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1)],
    )
    assert result.buyers_sorted == (("veh_b", 1),)
    assert result.sellers_sorted == (("veh_a", 1),)
    assert result.last_buyer_rank == 2
    assert result.assigned_rank(("veh_b", 1)) == 1
    assert result.assigned_rank(("veh_a", 1)) == 2
    assert result.assigned_rank(("veh_c", 1)) == 3


def test_multiple_buyer_ranks():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
        ("veh_e", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1), ("veh_d", 1)],
    )
    assert result.buyers_sorted == (("veh_b", 1), ("veh_d", 1))
    assert result.sellers_sorted == (("veh_a", 1), ("veh_c", 1))
    assert result.assigned_rank(("veh_b", 1)) == 1
    assert result.assigned_rank(("veh_d", 1)) == 2
    assert result.assigned_rank(("veh_a", 1)) == 3
    assert result.assigned_rank(("veh_c", 1)) == 4
    assert result.assigned_rank(("veh_e", 1)) == 5


def test_buyers_input_order_differs_from_baseline_order():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_d", 1), ("veh_a", 1)],
    )
    assert result.buyers_sorted == (("veh_a", 1), ("veh_d", 1))


def test_buyers_preserve_baseline_relative_order():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_c", 1), ("veh_b", 1)],
    )
    assert result.buyers_sorted == (("veh_b", 1), ("veh_c", 1))


def test_sellers_preserve_baseline_relative_order():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
        ("veh_e", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_c", 1)],
    )
    assert result.sellers_sorted == (("veh_a", 1), ("veh_b", 1))


def test_seller_retreat_zero_buyers_behind():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1))
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_a", 1)],
    )
    assert result.sellers_sorted == ()
    assert result.assigned_rank(("veh_b", 1)) == 2


def test_seller_retreat_one_buyer_behind():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_c", 1)],
    )
    assert result.assigned_rank(("veh_a", 1)) == 2
    assert result.assigned_rank(("veh_b", 1)) == 3
    assert result.assigned_rank(("veh_c", 1)) == 1


def test_seller_retreat_multiple_buyers_behind():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
        ("veh_e", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1), ("veh_d", 1)],
    )
    assert result.assigned_rank(("veh_a", 1)) == 3
    assert result.assigned_rank(("veh_c", 1)) == 4


def test_seller_retreat_formula_concrete_expected_values():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1), ("veh_d", 1)],
    )
    assert result.trade_order == (
        ("veh_b", 1),
        ("veh_d", 1),
        ("veh_a", 1),
        ("veh_c", 1),
    )


def test_outside_trade_scope_visit_rank_unchanged():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1)],
    )
    assert result.assigned_rank(("veh_c", 1)) == 3
    assert result.assigned_rank(("veh_d", 1)) == 4


def test_multiple_outside_trade_scope_visits_preserve_relative_order():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
        ("veh_e", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1)],
    )
    outside = result.trade_order[result.last_buyer_rank:]
    assert outside == (("veh_c", 1), ("veh_d", 1), ("veh_e", 1))


def test_ranks_are_contiguous_from_one_to_count():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_c", 1), ("veh_a", 1)],
    )
    ranks = [result.assigned_rank(key) for key in result.trade_order]
    assert ranks == [1, 2, 3, 4]


def test_no_duplicate_ranks():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1)],
    )
    ranks = [result.assigned_rank(key) for key in result.trade_order]
    assert len(ranks) == len(set(ranks))


def test_no_missing_ranks():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_d", 1)],
    )
    rank_set = {result.assigned_rank(key) for key in result.trade_order}
    assert rank_set == {1, 2, 3, 4}


def test_trade_order_matches_assigned_rank():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1), ("veh_d", 1)],
    )
    for position, visit_key in enumerate(result.trade_order, start=1):
        assert result.assigned_rank(visit_key) == position


def test_trade_rank_items_sorted_by_rank():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_c", 1)],
    )
    items = result.trade_rank_items()
    assert items == (
        (("veh_c", 1), 1),
        (("veh_a", 1), 2),
        (("veh_b", 1), 3),
    )


def test_zero_sellers_candidate():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_a", 1), ("veh_b", 1), ("veh_c", 1)],
    )
    assert result.sellers_sorted == ()
    assert result.assigned_rank(("veh_a", 1)) == 1
    assert result.assigned_rank(("veh_b", 1)) == 2
    assert result.assigned_rank(("veh_c", 1)) == 3


def test_result_keyword_only_constructor():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    assert result.buyers_sorted == (("veh_a", 1),)


def test_result_rejects_positional_constructor():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            (("veh_a", 1),),
            (),
            1,
            (("veh_a", 1),),
            {("veh_a", 1): 1},
        )
        raise AssertionError("Expected TypeError for positional args")
    except TypeError:
        pass


def test_result_constructor_rejects_list_for_buyers_sorted():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=[("veh_a", 1)],
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for list buyers_sorted")
    except ValueError as exc:
        assert "buyers_sorted" in str(exc)
        assert "tuple" in str(exc)


def test_result_constructor_rejects_list_for_sellers_sorted():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=[("veh_b", 1)],
            last_buyer_rank=2,
            trade_order=(("veh_a", 1), ("veh_b", 1)),
            trade_rank_by_visit_key={("veh_a", 1): 1, ("veh_b", 1): 2},
        )
        raise AssertionError("Expected ValueError for list sellers_sorted")
    except ValueError as exc:
        assert "sellers_sorted" in str(exc)
        assert "tuple" in str(exc)


def test_result_constructor_rejects_list_for_trade_order():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=[("veh_a", 1)],
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for list trade_order")
    except ValueError as exc:
        assert "trade_order" in str(exc)
        assert "tuple" in str(exc)


def test_result_constructor_accepts_tuple_containers():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1), ("veh_b", 1)),
        sellers_sorted=(("veh_c", 1),),
        last_buyer_rank=2,
        trade_order=(("veh_a", 1), ("veh_b", 1), ("veh_c", 1)),
        trade_rank_by_visit_key={
            ("veh_a", 1): 1,
            ("veh_b", 1): 2,
            ("veh_c", 1): 3,
        },
    )
    assert isinstance(result.buyers_sorted, tuple)
    assert isinstance(result.sellers_sorted, tuple)
    assert isinstance(result.trade_order, tuple)


def test_last_buyer_rank_uses_trailing_buyer_in_baseline_order():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
        ("veh_e", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1), ("veh_d", 1)],
    )
    assert result.last_buyer_rank == 4
    assert result.buyers_sorted == (("veh_b", 1), ("veh_d", 1))


def test_last_buyer_rank_unchanged_when_buyers_input_order_differs():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_d", 1), ("veh_b", 1)],
    )
    assert result.last_buyer_rank == 4
    assert result.buyers_sorted == (("veh_b", 1), ("veh_d", 1))


def test_result_accepts_empty_sellers_sorted():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    assert result.sellers_sorted == ()


def test_result_last_buyer_rank_property():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1), ("veh_b", 1)),
        sellers_sorted=(),
        last_buyer_rank=2,
        trade_order=(("veh_a", 1), ("veh_b", 1)),
        trade_rank_by_visit_key={("veh_a", 1): 1, ("veh_b", 1): 2},
    )
    assert result.last_buyer_rank == 2


def test_result_defensive_copy_of_rank_dict():
    source_rank_dict = {("veh_a", 1): 1}
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key=source_rank_dict,
    )
    source_rank_dict[("veh_a", 1)] = 99
    assert result.assigned_rank(("veh_a", 1)) == 1


def test_result_assigned_rank_returns_rank():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    assert result.assigned_rank(("veh_a", 1)) == 1


def test_result_assigned_rank_rejects_invalid_visit_key():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    try:
        result.assigned_rank(("", 1))
        raise AssertionError("Expected ValueError for invalid visit key")
    except ValueError:
        pass


def test_result_assigned_rank_rejects_out_of_scope_visit_key():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    try:
        result.assigned_rank(("veh_other", 1))
        raise AssertionError("Expected ValueError for out-of-scope visit key")
    except ValueError as exc:
        assert "not present" in str(exc)


def test_result_assigned_rank_does_not_return_none():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    try:
        result.assigned_rank(("veh_missing", 1))
        raise AssertionError("Expected ValueError instead of None")
    except ValueError:
        pass


def test_result_trade_rank_items_structure_and_order():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_b", 1),),
        sellers_sorted=(("veh_a", 1),),
        last_buyer_rank=2,
        trade_order=(("veh_b", 1), ("veh_a", 1)),
        trade_rank_by_visit_key={("veh_a", 1): 2, ("veh_b", 1): 1},
    )
    items = result.trade_rank_items()
    assert items == ((("veh_b", 1), 1), (("veh_a", 1), 2))


def test_result_trade_rank_items_does_not_return_internal_dict():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    items = result.trade_rank_items()
    assert not isinstance(items, dict)


def test_result_properties_have_no_setters():
    result = OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=(("veh_a", 1),),
        sellers_sorted=(),
        last_buyer_rank=1,
        trade_order=(("veh_a", 1),),
        trade_rank_by_visit_key={("veh_a", 1): 1},
    )
    for property_name in (
        "buyers_sorted",
        "sellers_sorted",
        "last_buyer_rank",
        "trade_order",
    ):
        property_object = getattr(
            OrderControlTvtNoNonparticipantTradeRankResult,
            property_name,
        )
        assert isinstance(property_object, property)
        assert property_object.fset is None
    assert result.buyers_sorted == (("veh_a", 1),)


def test_result_has_no_update_public_methods():
    public_methods = {
        name
        for name in dir(OrderControlTvtNoNonparticipantTradeRankResult)
        if callable(getattr(OrderControlTvtNoNonparticipantTradeRankResult, name))
        and not name.startswith("_")
    }
    assert public_methods == {"assigned_rank", "trade_rank_items"}


def test_result_has_no_export_state():
    assert not hasattr(OrderControlTvtNoNonparticipantTradeRankResult, "export_state")


def test_result_has_no_to_dict():
    assert not hasattr(OrderControlTvtNoNonparticipantTradeRankResult, "to_dict")


def test_result_constructor_rejects_empty_buyers_sorted():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for empty buyers_sorted")
    except ValueError:
        pass


def test_result_constructor_rejects_duplicate_buyers():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1), ("veh_a", 1)),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for duplicate buyers")
    except ValueError:
        pass


def test_result_constructor_rejects_empty_trade_order():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for empty trade_order")
    except ValueError:
        pass


def test_result_constructor_rejects_empty_trade_rank_dict():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={},
        )
        raise AssertionError("Expected ValueError for empty trade_rank dict")
    except ValueError:
        pass


def test_result_constructor_rejects_bool_last_buyer_rank():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=True,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for bool last_buyer_rank")
    except ValueError:
        pass


def test_result_constructor_rejects_zero_last_buyer_rank():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=0,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError("Expected ValueError for zero last_buyer_rank")
    except ValueError as exc:
        assert "last_buyer_rank" in str(exc)


def test_result_constructor_rejects_invalid_visit_key_in_sellers_sorted():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("", 1),),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError(
            "Expected ValueError for invalid VisitKey in sellers_sorted"
        )
    except ValueError as exc:
        assert "sellers_sorted" in str(exc)


def test_result_constructor_rejects_duplicate_visit_key_in_sellers_sorted():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1), ("veh_b", 1)),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError(
            "Expected ValueError for duplicate VisitKey in sellers_sorted"
        )
    except ValueError as exc:
        assert "sellers_sorted" in str(exc)
        assert "Duplicate VisitKey" in str(exc)


def test_result_constructor_rejects_invalid_visit_key_in_trade_order():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError(
            "Expected ValueError for invalid VisitKey in trade_order"
        )
    except ValueError as exc:
        assert "trade_order" in str(exc)


def test_result_constructor_rejects_duplicate_visit_key_in_trade_order():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1), ("veh_a", 1)),
            trade_rank_by_visit_key={("veh_a", 1): 1},
        )
        raise AssertionError(
            "Expected ValueError for duplicate VisitKey in trade_order"
        )
    except ValueError as exc:
        assert "trade_order" in str(exc)
        assert "Duplicate VisitKey" in str(exc)


def test_result_constructor_rejects_non_dict_trade_rank_by_visit_key():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key=[],
        )
        raise AssertionError(
            "Expected ValueError for non-dict trade_rank_by_visit_key"
        )
    except ValueError as exc:
        assert "trade_rank_by_visit_key" in str(exc)


def test_result_constructor_rejects_invalid_visit_key_in_trade_rank_dict():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("", 1): 1},
        )
        raise AssertionError(
            "Expected ValueError for invalid VisitKey in trade_rank dict"
        )
    except ValueError as exc:
        assert "trade_rank_by_visit_key" in str(exc)


def test_result_constructor_rejects_non_int_rank_value_in_trade_rank_dict():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): "1"},
        )
        raise AssertionError(
            "Expected ValueError for non-int rank in trade_rank dict"
        )
    except ValueError as exc:
        assert "trade_rank_by_visit_key" in str(exc)


def test_result_constructor_rejects_zero_rank_value_in_trade_rank_dict():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): 0},
        )
        raise AssertionError(
            "Expected ValueError for zero rank in trade_rank dict"
        )
    except ValueError as exc:
        assert "trade_rank_by_visit_key" in str(exc)


def test_baseline_order_input_list_not_mutated():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1))
    baseline_copy = list(baseline)
    _ = build_tvt_trade_rank_without_nonparticipants(baseline, [("veh_a", 1)])
    assert baseline == baseline_copy


def test_buyers_input_list_not_mutated():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1))
    buyers = [("veh_b", 1)]
    buyers_copy = list(buyers)
    _ = build_tvt_trade_rank_without_nonparticipants(baseline, buyers)
    assert buyers == buyers_copy


def test_result_rank_dict_mutation_after_construction_does_not_change_result():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1))
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_a", 1)],
    )
    items = result.trade_rank_items()
    copied_items = list(items)
    copied_items[0] = (("veh_x", 1), 99)
    assert result.assigned_rank(("veh_a", 1)) == 1


def test_trade_rank_items_return_value_mutation_does_not_change_result():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1))
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_a", 1)],
    )
    items = list(result.trade_rank_items())
    items[0] = (("veh_x", 1), 99)
    assert result.assigned_rank(("veh_a", 1)) == 1


def test_build_function_does_not_mutate_input_containers():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    buyers = [("veh_b", 1)]
    baseline_before = list(baseline)
    buyers_before = list(buyers)
    _ = build_tvt_trade_rank_without_nonparticipants(baseline, buyers)
    assert baseline == baseline_before
    assert buyers == buyers_before


def test_baseline_order_rejects_non_list_or_tuple():
    try:
        build_tvt_trade_rank_without_nonparticipants("bad", [("veh_a", 1)])
        raise AssertionError("Expected ValueError for bad baseline_order type")
    except ValueError as exc:
        assert "baseline_order" in str(exc)


def test_baseline_order_rejects_empty_list():
    try:
        build_tvt_trade_rank_without_nonparticipants([], [("veh_a", 1)])
        raise AssertionError("Expected ValueError for empty baseline_order")
    except ValueError:
        pass


def test_baseline_order_rejects_empty_tuple():
    try:
        build_tvt_trade_rank_without_nonparticipants((), [("veh_a", 1)])
        raise AssertionError("Expected ValueError for empty baseline_order tuple")
    except ValueError:
        pass


def test_baseline_order_rejects_non_tuple_visit_key():
    try:
        build_tvt_trade_rank_without_nonparticipants(["veh_a"], [("veh_a", 1)])
        raise AssertionError("Expected ValueError for non-tuple VisitKey")
    except ValueError:
        pass


def test_baseline_order_rejects_wrong_length_visit_key():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1, 2)],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for wrong-length VisitKey")
    except ValueError:
        pass


def test_baseline_order_rejects_empty_vehicle_name():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("", 1)],
            [("", 1)],
        )
        raise AssertionError("Expected ValueError for empty vehicle_name")
    except ValueError:
        pass


def test_baseline_order_rejects_non_string_vehicle_name():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [(123, 1)],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for non-str vehicle_name")
    except ValueError:
        pass


def test_baseline_order_rejects_bool_visit_id():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", True)],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for bool visit_id")
    except ValueError:
        pass


def test_baseline_order_rejects_non_int_visit_id():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", "1")],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for non-int visit_id")
    except ValueError:
        pass


def test_baseline_order_rejects_zero_visit_id():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 0)],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for zero visit_id")
    except ValueError:
        pass


def test_baseline_order_rejects_negative_visit_id():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", -1)],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for negative visit_id")
    except ValueError:
        pass


def test_baseline_order_rejects_numpy_integer_visit_id():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", np.int64(1))],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for numpy visit_id")
    except ValueError:
        pass


def test_baseline_order_rejects_list_form_visit_key():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [["veh_a", 1]],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for list-form VisitKey")
    except ValueError:
        pass


def test_baseline_order_rejects_duplicate_visit_key():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1), ("veh_a", 1)],
            [("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for duplicate baseline VisitKey")
    except ValueError:
        pass


def test_buyers_rejects_non_list_or_tuple():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1)],
            "bad",
        )
        raise AssertionError("Expected ValueError for bad buyers type")
    except ValueError as exc:
        assert "buyers" in str(exc)


def test_buyers_rejects_empty_list():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1)],
            [],
        )
        raise AssertionError("Expected ValueError for empty buyers")
    except ValueError:
        pass


def test_buyers_rejects_empty_tuple():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1)],
            (),
        )
        raise AssertionError("Expected ValueError for empty buyers tuple")
    except ValueError:
        pass


def test_buyers_rejects_invalid_visit_key():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1)],
            [("veh_a", True)],
        )
        raise AssertionError("Expected ValueError for invalid buyer VisitKey")
    except ValueError:
        pass


def test_buyers_rejects_duplicate_visit_key():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1), ("veh_b", 1)],
            [("veh_a", 1), ("veh_a", 1)],
        )
        raise AssertionError("Expected ValueError for duplicate buyer VisitKey")
    except ValueError:
        pass


def test_buyers_rejects_buyer_not_in_baseline():
    try:
        build_tvt_trade_rank_without_nonparticipants(
            [("veh_a", 1)],
            [("veh_missing", 1)],
        )
        raise AssertionError("Expected ValueError for buyer not in baseline")
    except ValueError as exc:
        assert "not present in baseline_order" in str(exc)


def test_result_constructor_rejects_bool_rank_value_in_trade_rank_dict():
    try:
        OrderControlTvtNoNonparticipantTradeRankResult(
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_order=(("veh_a", 1),),
            trade_rank_by_visit_key={("veh_a", 1): True},
        )
        raise AssertionError("Expected ValueError for bool rank in constructor")
    except ValueError:
        pass


def test_verify_runtime_error_on_bool_rank_value():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1, ("veh_b", 1): True},
            trade_order=(("veh_a", 1), ("veh_b", 1)),
        )
        raise AssertionError("Expected RuntimeError for bool rank value")
    except RuntimeError as exc:
        assert "Internal trade-rank inconsistency" in str(exc)
        assert "('veh_b', 1)" in str(exc)


def test_verify_runtime_error_on_non_int_rank_value():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1, ("veh_b", 1): "2"},
            trade_order=(("veh_a", 1), ("veh_b", 1)),
        )
        raise AssertionError("Expected RuntimeError for non-int rank value")
    except RuntimeError as exc:
        assert "Internal trade-rank inconsistency" in str(exc)
        assert "('veh_b', 1)" in str(exc)


def test_verify_runtime_error_on_zero_rank_value():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1, ("veh_b", 1): 0},
            trade_order=(("veh_a", 1), ("veh_b", 1)),
        )
        raise AssertionError("Expected RuntimeError for zero rank value")
    except RuntimeError as exc:
        assert "Internal trade-rank inconsistency" in str(exc)
        assert "('veh_b', 1)" in str(exc)


def test_verify_runtime_error_on_empty_buyers_sorted():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(),
            sellers_sorted=(("veh_a", 1), ("veh_b", 1)),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1, ("veh_b", 1): 2},
            trade_order=baseline_order,
        )
        raise AssertionError("Expected RuntimeError for empty buyers_sorted")
    except RuntimeError as exc:
        assert "buyers_sorted must not be empty" in str(exc)


def test_verify_runtime_error_on_duplicate_ranks():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1, ("veh_b", 1): 1},
            trade_order=(("veh_a", 1), ("veh_b", 1)),
        )
        raise AssertionError("Expected RuntimeError for duplicate ranks")
    except RuntimeError:
        pass


def test_verify_runtime_error_on_missing_rank():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1, ("veh_b", 1): 3},
            trade_order=(("veh_a", 1), ("veh_b", 1)),
        )
        raise AssertionError("Expected RuntimeError for missing rank")
    except RuntimeError:
        pass


def test_verify_runtime_error_on_visit_key_set_mismatch():
    baseline_order = (("veh_a", 1), ("veh_b", 1))
    baseline_rank = {("veh_a", 1): 1, ("veh_b", 1): 2}
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(("veh_b", 1),),
            last_buyer_rank=2,
            trade_scope=baseline_order,
            trade_rank={("veh_a", 1): 1},
            trade_order=(("veh_a", 1),),
        )
        raise AssertionError("Expected RuntimeError for VisitKey set mismatch")
    except RuntimeError:
        pass


def test_verify_runtime_error_on_seller_retreat_mismatch():
    baseline_order = (("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    baseline_rank = {
        ("veh_a", 1): 1,
        ("veh_b", 1): 2,
        ("veh_c", 1): 3,
    }
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_c", 1),),
            sellers_sorted=(("veh_a", 1), ("veh_b", 1)),
            last_buyer_rank=3,
            trade_scope=baseline_order,
            trade_rank={
                ("veh_c", 1): 1,
                ("veh_a", 1): 3,
                ("veh_b", 1): 2,
            },
            trade_order=(
                ("veh_c", 1),
                ("veh_b", 1),
                ("veh_a", 1),
            ),
        )
        raise AssertionError("Expected RuntimeError for seller retreat mismatch")
    except RuntimeError as exc:
        assert "seller retreat formula" in str(exc)


def test_verify_runtime_error_on_outside_scope_rank_change():
    baseline_order = (("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    baseline_rank = {
        ("veh_a", 1): 1,
        ("veh_b", 1): 2,
        ("veh_c", 1): 3,
    }
    try:
        _verify_local_trade_rank_state(
            baseline_order=baseline_order,
            baseline_rank=baseline_rank,
            buyers_sorted=(("veh_a", 1),),
            sellers_sorted=(),
            last_buyer_rank=1,
            trade_scope=(("veh_a", 1),),
            trade_rank={
                ("veh_a", 1): 1,
                ("veh_b", 1): 3,
                ("veh_c", 1): 2,
            },
            trade_order=(
                ("veh_a", 1),
                ("veh_c", 1),
                ("veh_b", 1),
            ),
        )
        raise AssertionError(
            "Expected RuntimeError for outside-scope rank change"
        )
    except RuntimeError as exc:
        assert "outside trade_scope" in str(exc)


def test_build_runtime_error_via_public_path_when_verify_fails():
    baseline = _baseline(("veh_a", 1), ("veh_b", 1))
    with patch(
        "uxsim.order_control_tvt_trade_rank._verify_local_trade_rank_state",
        side_effect=RuntimeError("forced verification failure"),
    ):
        try:
            build_tvt_trade_rank_without_nonparticipants(
                baseline,
                [("veh_a", 1)],
            )
            raise AssertionError(
                "Expected RuntimeError from public build path"
            )
        except RuntimeError as exc:
            assert "forced verification failure" in str(exc)


def test_fifo_single_inlink_preserved_returns_true():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade = [("veh_a", 1), ("veh_b", 1)]
    inlinks = {("veh_a", 1): "in_1", ("veh_b", 1): "in_1"}
    assert preserves_inlink_fifo(baseline, trade, inlinks) is True


def test_fifo_multiple_inlinks_all_preserved_returns_true():
    baseline = [("veh_a", 1), ("veh_b", 1), ("veh_c", 1)]
    trade = [("veh_a", 1), ("veh_c", 1), ("veh_b", 1)]
    inlinks = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_2",
        ("veh_c", 1): "in_1",
    }
    assert preserves_inlink_fifo(baseline, trade, inlinks) is True


def test_fifo_cross_inlink_reorder_with_inlink_order_preserved_returns_true():
    baseline = [("veh_a", 1), ("veh_b", 1), ("veh_c", 1)]
    trade = [("veh_a", 1), ("veh_c", 1), ("veh_b", 1)]
    inlinks = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_2",
        ("veh_c", 1): "in_1",
    }
    assert preserves_inlink_fifo(baseline, trade, inlinks) is True


def test_fifo_single_visit_per_inlink_returns_true():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade = [("veh_b", 1), ("veh_a", 1)]
    inlinks = {("veh_a", 1): "in_1", ("veh_b", 1): "in_2"}
    assert preserves_inlink_fifo(baseline, trade, inlinks) is True


def test_fifo_extra_inlink_info_ignored_returns_true():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade = [("veh_a", 1), ("veh_b", 1)]
    inlinks = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_1",
        ("veh_extra", 1): "in_9",
    }
    assert preserves_inlink_fifo(baseline, trade, inlinks) is True


def test_fifo_extra_inlink_info_does_not_affect_judgment():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade = [("veh_b", 1), ("veh_a", 1)]
    inlinks_without_extra = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_1",
    }
    inlinks_with_extra = {
        **inlinks_without_extra,
        ("veh_extra", 1): "in_1",
        ("veh_other", 2): "in_2",
    }
    assert preserves_inlink_fifo(
        baseline,
        trade,
        inlinks_without_extra,
    ) is False
    assert preserves_inlink_fifo(
        baseline,
        trade,
        inlinks_with_extra,
    ) is False


def test_fifo_single_inlink_reversal_returns_false():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade = [("veh_b", 1), ("veh_a", 1)]
    inlinks = {("veh_a", 1): "in_1", ("veh_b", 1): "in_1"}
    assert preserves_inlink_fifo(baseline, trade, inlinks) is False


def test_fifo_one_of_multiple_inlinks_reversed_returns_false():
    baseline = [("veh_a", 1), ("veh_b", 1), ("veh_c", 1)]
    trade = [("veh_a", 1), ("veh_c", 1), ("veh_b", 1)]
    inlinks = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_2",
        ("veh_c", 1): "in_2",
    }
    assert preserves_inlink_fifo(baseline, trade, inlinks) is False


def test_fifo_multiple_inlinks_reversed_returns_false():
    baseline = [("veh_a", 1), ("veh_b", 1), ("veh_c", 1), ("veh_d", 1)]
    trade = [("veh_b", 1), ("veh_a", 1), ("veh_d", 1), ("veh_c", 1)]
    inlinks = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_1",
        ("veh_c", 1): "in_2",
        ("veh_d", 1): "in_2",
    }
    assert preserves_inlink_fifo(baseline, trade, inlinks) is False


def test_fifo_violation_does_not_raise():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade = [("veh_b", 1), ("veh_a", 1)]
    inlinks = {("veh_a", 1): "in_1", ("veh_b", 1): "in_1"}
    result = preserves_inlink_fifo(baseline, trade, inlinks)
    assert result is False


def test_fifo_no_automatic_recalculation_on_violation():
    baseline = [("veh_a", 1), ("veh_b", 1)]
    trade_bad = [("veh_b", 1), ("veh_a", 1)]
    inlinks = {("veh_a", 1): "in_1", ("veh_b", 1): "in_1"}
    first = preserves_inlink_fifo(baseline, trade_bad, inlinks)
    second = preserves_inlink_fifo(baseline, trade_bad, inlinks)
    assert first is False
    assert second is False


def test_fifo_baseline_order_rejects_bad_container_type():
    try:
        preserves_inlink_fifo("bad", [("veh_a", 1)], {("veh_a", 1): "in_1"})
        raise AssertionError("Expected ValueError for bad baseline container")
    except ValueError:
        pass


def test_fifo_trade_order_rejects_bad_container_type():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1)],
            "bad",
            {("veh_a", 1): "in_1"},
        )
        raise AssertionError("Expected ValueError for bad trade container")
    except ValueError:
        pass


def test_fifo_baseline_order_rejects_empty():
    try:
        preserves_inlink_fifo([], [("veh_a", 1)], {("veh_a", 1): "in_1"})
        raise AssertionError("Expected ValueError for empty baseline_order")
    except ValueError:
        pass


def test_fifo_trade_order_rejects_empty():
    try:
        preserves_inlink_fifo([("veh_a", 1)], [], {("veh_a", 1): "in_1"})
        raise AssertionError("Expected ValueError for empty trade_order")
    except ValueError:
        pass


def test_fifo_rejects_invalid_visit_key():
    try:
        preserves_inlink_fifo(
            [("veh_a", True)],
            [("veh_a", 1)],
            {("veh_a", 1): "in_1"},
        )
        raise AssertionError("Expected ValueError for invalid VisitKey")
    except ValueError:
        pass


def test_fifo_rejects_numpy_integer_visit_id():
    try:
        preserves_inlink_fifo(
            [("veh_a", np.int64(1))],
            [("veh_a", np.int64(1))],
            {("veh_a", np.int64(1)): "in_1"},
        )
        raise AssertionError("Expected ValueError for numpy visit_id")
    except ValueError:
        pass


def test_fifo_rejects_duplicate_in_baseline_order():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1), ("veh_a", 1)],
            [("veh_a", 1)],
            {("veh_a", 1): "in_1"},
        )
        raise AssertionError("Expected ValueError for duplicate baseline key")
    except ValueError:
        pass


def test_fifo_rejects_duplicate_in_trade_order():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1), ("veh_b", 1)],
            [("veh_a", 1), ("veh_a", 1)],
            {
                ("veh_a", 1): "in_1",
                ("veh_b", 1): "in_1",
            },
        )
        raise AssertionError("Expected ValueError for duplicate trade_order key")
    except ValueError as exc:
        assert "trade_order" in str(exc) or "Duplicate VisitKey" in str(exc)


def test_fifo_rejects_length_mismatch():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1), ("veh_b", 1)],
            [("veh_a", 1)],
            {
                ("veh_a", 1): "in_1",
                ("veh_b", 1): "in_1",
            },
        )
        raise AssertionError("Expected ValueError for length mismatch")
    except ValueError:
        pass


def test_fifo_rejects_visit_key_set_mismatch():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1), ("veh_b", 1)],
            [("veh_a", 1), ("veh_c", 1)],
            {
                ("veh_a", 1): "in_1",
                ("veh_b", 1): "in_1",
                ("veh_c", 1): "in_1",
            },
        )
        raise AssertionError("Expected ValueError for VisitKey set mismatch")
    except ValueError:
        pass


def test_fifo_rejects_non_dict_inlink_mapping():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1)],
            [("veh_a", 1)],
            [],
        )
        raise AssertionError("Expected ValueError for non-dict inlink mapping")
    except ValueError:
        pass


def test_fifo_rejects_missing_inlink_info():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1), ("veh_b", 1)],
            [("veh_a", 1), ("veh_b", 1)],
            {("veh_a", 1): "in_1"},
        )
        raise AssertionError("Expected ValueError for missing inlink info")
    except ValueError:
        pass


def test_fifo_rejects_empty_inlink_name():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1)],
            [("veh_a", 1)],
            {("veh_a", 1): ""},
        )
        raise AssertionError("Expected ValueError for empty inlink name")
    except ValueError:
        pass


def test_fifo_rejects_non_string_inlink_name():
    try:
        preserves_inlink_fifo(
            [("veh_a", 1)],
            [("veh_a", 1)],
            {("veh_a", 1): 123},
        )
        raise AssertionError("Expected ValueError for non-str inlink name")
    except ValueError:
        pass


def test_integration_build_result_and_fifo_on_trade_scope():
    baseline = _baseline(
        ("veh_a", 1),
        ("veh_b", 1),
        ("veh_c", 1),
        ("veh_d", 1),
    )
    result = build_tvt_trade_rank_without_nonparticipants(
        baseline,
        [("veh_b", 1), ("veh_d", 1)],
    )
    trade_scope = tuple(baseline[: result.last_buyer_rank])
    trade_scope_after = result.trade_order[: result.last_buyer_rank]
    inlinks = {
        ("veh_a", 1): "in_1",
        ("veh_b", 1): "in_2",
        ("veh_c", 1): "in_1",
        ("veh_d", 1): "in_2",
    }
    assert preserves_inlink_fifo(
        trade_scope,
        trade_scope_after,
        inlinks,
    ) is True


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


TESTS = [
    test_public_types_importable,
    test_single_buyer_rank,
    test_multiple_buyer_ranks,
    test_buyers_input_order_differs_from_baseline_order,
    test_buyers_preserve_baseline_relative_order,
    test_sellers_preserve_baseline_relative_order,
    test_seller_retreat_zero_buyers_behind,
    test_seller_retreat_one_buyer_behind,
    test_seller_retreat_multiple_buyers_behind,
    test_seller_retreat_formula_concrete_expected_values,
    test_outside_trade_scope_visit_rank_unchanged,
    test_multiple_outside_trade_scope_visits_preserve_relative_order,
    test_ranks_are_contiguous_from_one_to_count,
    test_no_duplicate_ranks,
    test_no_missing_ranks,
    test_trade_order_matches_assigned_rank,
    test_trade_rank_items_sorted_by_rank,
    test_zero_sellers_candidate,
    test_result_keyword_only_constructor,
    test_result_rejects_positional_constructor,
    test_result_constructor_rejects_list_for_buyers_sorted,
    test_result_constructor_rejects_list_for_sellers_sorted,
    test_result_constructor_rejects_list_for_trade_order,
    test_result_constructor_accepts_tuple_containers,
    test_last_buyer_rank_uses_trailing_buyer_in_baseline_order,
    test_last_buyer_rank_unchanged_when_buyers_input_order_differs,
    test_result_accepts_empty_sellers_sorted,
    test_result_last_buyer_rank_property,
    test_result_defensive_copy_of_rank_dict,
    test_result_assigned_rank_returns_rank,
    test_result_assigned_rank_rejects_invalid_visit_key,
    test_result_assigned_rank_rejects_out_of_scope_visit_key,
    test_result_assigned_rank_does_not_return_none,
    test_result_trade_rank_items_structure_and_order,
    test_result_trade_rank_items_does_not_return_internal_dict,
    test_result_properties_have_no_setters,
    test_result_has_no_update_public_methods,
    test_result_has_no_export_state,
    test_result_has_no_to_dict,
    test_result_constructor_rejects_empty_buyers_sorted,
    test_result_constructor_rejects_duplicate_buyers,
    test_result_constructor_rejects_empty_trade_order,
    test_result_constructor_rejects_empty_trade_rank_dict,
    test_result_constructor_rejects_bool_last_buyer_rank,
    test_result_constructor_rejects_zero_last_buyer_rank,
    test_result_constructor_rejects_invalid_visit_key_in_sellers_sorted,
    test_result_constructor_rejects_duplicate_visit_key_in_sellers_sorted,
    test_result_constructor_rejects_invalid_visit_key_in_trade_order,
    test_result_constructor_rejects_duplicate_visit_key_in_trade_order,
    test_result_constructor_rejects_non_dict_trade_rank_by_visit_key,
    test_result_constructor_rejects_invalid_visit_key_in_trade_rank_dict,
    test_result_constructor_rejects_non_int_rank_value_in_trade_rank_dict,
    test_result_constructor_rejects_zero_rank_value_in_trade_rank_dict,
    test_result_constructor_rejects_bool_rank_value_in_trade_rank_dict,
    test_baseline_order_input_list_not_mutated,
    test_buyers_input_list_not_mutated,
    test_result_rank_dict_mutation_after_construction_does_not_change_result,
    test_trade_rank_items_return_value_mutation_does_not_change_result,
    test_build_function_does_not_mutate_input_containers,
    test_baseline_order_rejects_non_list_or_tuple,
    test_baseline_order_rejects_empty_list,
    test_baseline_order_rejects_empty_tuple,
    test_baseline_order_rejects_non_tuple_visit_key,
    test_baseline_order_rejects_wrong_length_visit_key,
    test_baseline_order_rejects_empty_vehicle_name,
    test_baseline_order_rejects_non_string_vehicle_name,
    test_baseline_order_rejects_bool_visit_id,
    test_baseline_order_rejects_non_int_visit_id,
    test_baseline_order_rejects_zero_visit_id,
    test_baseline_order_rejects_negative_visit_id,
    test_baseline_order_rejects_numpy_integer_visit_id,
    test_baseline_order_rejects_list_form_visit_key,
    test_baseline_order_rejects_duplicate_visit_key,
    test_buyers_rejects_non_list_or_tuple,
    test_buyers_rejects_empty_list,
    test_buyers_rejects_empty_tuple,
    test_buyers_rejects_invalid_visit_key,
    test_buyers_rejects_duplicate_visit_key,
    test_buyers_rejects_buyer_not_in_baseline,
    test_verify_runtime_error_on_bool_rank_value,
    test_verify_runtime_error_on_non_int_rank_value,
    test_verify_runtime_error_on_zero_rank_value,
    test_verify_runtime_error_on_empty_buyers_sorted,
    test_verify_runtime_error_on_duplicate_ranks,
    test_verify_runtime_error_on_missing_rank,
    test_verify_runtime_error_on_visit_key_set_mismatch,
    test_verify_runtime_error_on_seller_retreat_mismatch,
    test_verify_runtime_error_on_outside_scope_rank_change,
    test_build_runtime_error_via_public_path_when_verify_fails,
    test_fifo_single_inlink_preserved_returns_true,
    test_fifo_multiple_inlinks_all_preserved_returns_true,
    test_fifo_cross_inlink_reorder_with_inlink_order_preserved_returns_true,
    test_fifo_single_visit_per_inlink_returns_true,
    test_fifo_extra_inlink_info_ignored_returns_true,
    test_fifo_extra_inlink_info_does_not_affect_judgment,
    test_fifo_single_inlink_reversal_returns_false,
    test_fifo_one_of_multiple_inlinks_reversed_returns_false,
    test_fifo_multiple_inlinks_reversed_returns_false,
    test_fifo_violation_does_not_raise,
    test_fifo_no_automatic_recalculation_on_violation,
    test_fifo_baseline_order_rejects_bad_container_type,
    test_fifo_trade_order_rejects_bad_container_type,
    test_fifo_baseline_order_rejects_empty,
    test_fifo_trade_order_rejects_empty,
    test_fifo_rejects_invalid_visit_key,
    test_fifo_rejects_numpy_integer_visit_id,
    test_fifo_rejects_duplicate_in_baseline_order,
    test_fifo_rejects_duplicate_in_trade_order,
    test_fifo_rejects_length_mismatch,
    test_fifo_rejects_visit_key_set_mismatch,
    test_fifo_rejects_non_dict_inlink_mapping,
    test_fifo_rejects_missing_inlink_info,
    test_fifo_rejects_empty_inlink_name,
    test_fifo_rejects_non_string_inlink_name,
    test_integration_build_result_and_fifo_on_trade_scope,
]


if __name__ == "__main__":
    _verify_tests_registry()
    for test_func in TESTS:
        test_func()
    print(
        f"Order-control TVT trade rank tests passed ({len(TESTS)} tests)."
    )
