"""
TVT trade-rank construction without non-participating vehicles
and inlink FIFO inspection.

Builds trade ranks for one concrete trade candidate without
non-participating vehicles, using a completed baseline order and a
pre-selected buyer set. Does not modify rank ledgers, collector state,
or simulation objects.
"""

from __future__ import annotations

from typing import Any

from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtVisitKey,
)


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _validate_visit_key(
    value: Any,
    field_name: str = "visit_key",
) -> OrderControlTvtVisitKey:
    if not isinstance(value, tuple):
        raise ValueError(
            f"{field_name} must be a length-2 tuple (vehicle_name, visit_id); "
            f"got type {type(value).__name__} with value {value!r}."
        )
    if len(value) != 2:
        raise ValueError(
            f"{field_name} must be a length-2 tuple (vehicle_name, visit_id); "
            f"got length {len(value)} with value {value!r}."
        )
    vehicle_name, visit_id = value
    vehicle_name = _require_non_empty_str(
        vehicle_name,
        f"{field_name}[0] (vehicle_name)",
    )
    if type(visit_id) is not int:
        raise ValueError(
            f"{field_name}[1] (visit_id) must be a Python int (not bool); "
            f"got type {type(visit_id).__name__} with value {visit_id!r}."
        )
    if visit_id < 1:
        raise ValueError(
            f"{field_name}[1] (visit_id) must be >= 1; got {visit_id!r}."
        )
    return (vehicle_name, visit_id)


def _require_tuple_container(
    value: Any,
    field_name: str,
) -> tuple[OrderControlTvtVisitKey, ...]:
    if not isinstance(value, tuple):
        raise ValueError(
            f"{field_name} must be a tuple of VisitKey tuples; "
            f"got type {type(value).__name__} with value {value!r}."
        )
    return value


def _require_list_or_tuple_container(
    value: Any,
    field_name: str,
) -> tuple[OrderControlTvtVisitKey, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(
            f"{field_name} must be a list or tuple of VisitKey tuples; "
            f"got type {type(value).__name__} with value {value!r}."
        )
    return tuple(value)


def _validate_visit_key_sequence(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
    *,
    field_name: str,
    allow_empty: bool,
) -> tuple[OrderControlTvtVisitKey, ...]:
    if not allow_empty and len(visit_keys) == 0:
        raise ValueError(f"{field_name} must not be empty.")

    validated_visit_keys: list[OrderControlTvtVisitKey] = []
    for index, visit_key in enumerate(visit_keys):
        validated_visit_keys.append(
            _validate_visit_key(
                visit_key,
                field_name=f"{field_name}[{index}]",
            )
        )
    validated_visit_keys_tuple = tuple(validated_visit_keys)

    duplicate_visit_key = _find_duplicate_visit_keys(validated_visit_keys_tuple)
    if duplicate_visit_key is not None:
        raise ValueError(
            f"Duplicate VisitKey {duplicate_visit_key!r} in {field_name}."
        )

    return validated_visit_keys_tuple


def _find_duplicate_visit_keys(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    seen: set[OrderControlTvtVisitKey] = set()
    for visit_key in visit_keys:
        if visit_key in seen:
            return visit_key
        seen.add(visit_key)
    return None


def _require_python_int_rank(value: Any, field_name: str) -> int:
    if type(value) is not int:
        raise ValueError(
            f"{field_name} must be a Python int (not bool); "
            f"got type {type(value).__name__} with value {value!r}."
        )
    if value < 1:
        raise ValueError(f"{field_name} must be >= 1; got {value!r}.")
    return value


def _validate_internal_trade_rank_value(
    rank_value: Any,
    visit_key: OrderControlTvtVisitKey,
) -> int:
    if type(rank_value) is not int:
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_rank "
            f"{visit_key!r} must be a Python int (not bool); "
            f"got type {type(rank_value).__name__} with value {rank_value!r}."
        )
    if rank_value < 1:
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_rank "
            f"{visit_key!r} must be >= 1; got {rank_value!r}."
        )
    return rank_value


def _verify_local_trade_rank_state(
    *,
    baseline_order: tuple[OrderControlTvtVisitKey, ...],
    baseline_rank: dict[OrderControlTvtVisitKey, int],
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    sellers_sorted: tuple[OrderControlTvtVisitKey, ...],
    last_buyer_rank: int,
    trade_scope: tuple[OrderControlTvtVisitKey, ...],
    trade_rank: dict[OrderControlTvtVisitKey, int],
    trade_order: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    baseline_visit_set = set(baseline_order)
    trade_rank_visit_set = set(trade_rank)
    trade_order_visit_set = set(trade_order)

    if trade_rank_visit_set != baseline_visit_set:
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_rank VisitKey set "
            "does not match baseline_order."
        )
    if trade_order_visit_set != baseline_visit_set:
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_order VisitKey set "
            "does not match baseline_order."
        )
    if len(trade_order) != len(baseline_order):
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_order length "
            f"{len(trade_order)} does not match baseline_order length "
            f"{len(baseline_order)}."
        )

    rank_values: list[int] = []
    for visit_key, rank_value in trade_rank.items():
        validated_rank_value = _validate_internal_trade_rank_value(
            rank_value,
            visit_key,
        )
        rank_values.append(validated_rank_value)

    expected_rank_set = set(range(1, len(baseline_order) + 1))
    actual_rank_set = set(rank_values)
    if actual_rank_set != expected_rank_set:
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_rank values are not "
            f"exactly 1..{len(baseline_order)}."
        )

    for position, visit_key in enumerate(trade_order, start=1):
        rank_in_dict = trade_rank.get(visit_key)
        if rank_in_dict is None:
            raise RuntimeError(
                "Internal trade-rank inconsistency: trade_order VisitKey "
                f"{visit_key!r} is missing from trade_rank."
            )
        if rank_in_dict != position:
            raise RuntimeError(
                "Internal trade-rank inconsistency: trade_order position "
                f"{position} for VisitKey {visit_key!r} does not match "
                f"trade_rank value {rank_in_dict}."
            )

    buyer_set = set(buyers_sorted)
    seller_set = set(sellers_sorted)
    if buyer_set & seller_set:
        raise RuntimeError(
            "Internal trade-rank inconsistency: buyers_sorted and "
            "sellers_sorted overlap."
        )
    if buyer_set | seller_set != set(trade_scope):
        raise RuntimeError(
            "Internal trade-rank inconsistency: buyers_sorted and "
            "sellers_sorted do not partition trade_scope."
        )

    for index in range(1, len(buyers_sorted)):
        previous_buyer = buyers_sorted[index - 1]
        current_buyer = buyers_sorted[index]
        if baseline_rank[previous_buyer] >= baseline_rank[current_buyer]:
            raise RuntimeError(
                "Internal trade-rank inconsistency: buyers_sorted does not "
                "preserve baseline relative order."
            )

    for index in range(1, len(sellers_sorted)):
        previous_seller = sellers_sorted[index - 1]
        current_seller = sellers_sorted[index]
        if baseline_rank[previous_seller] >= baseline_rank[current_seller]:
            raise RuntimeError(
                "Internal trade-rank inconsistency: sellers_sorted does not "
                "preserve baseline relative order."
            )

    if len(buyers_sorted) == 0:
        raise RuntimeError(
            "Internal trade-rank inconsistency: "
            "buyers_sorted must not be empty."
        )

    if last_buyer_rank < 1:
        raise RuntimeError(
            "Internal trade-rank inconsistency: last_buyer_rank must be >= 1."
        )
    if last_buyer_rank > len(baseline_order):
        raise RuntimeError(
            "Internal trade-rank inconsistency: last_buyer_rank exceeds "
            "baseline_order length."
        )

    expected_last_buyer = buyers_sorted[-1]
    expected_last_buyer_rank = baseline_rank[expected_last_buyer]
    if last_buyer_rank != expected_last_buyer_rank:
        raise RuntimeError(
            "Internal trade-rank inconsistency: last_buyer_rank does not "
            "match the trailing buyer baseline rank."
        )

    expected_trade_scope = baseline_order[:last_buyer_rank]
    if trade_scope != expected_trade_scope:
        raise RuntimeError(
            "Internal trade-rank inconsistency: trade_scope does not match "
            "baseline_order[:last_buyer_rank]."
        )

    for expected_rank, buyer in enumerate(buyers_sorted, start=1):
        actual_rank = trade_rank[buyer]
        if actual_rank != expected_rank:
            raise RuntimeError(
                "Internal trade-rank inconsistency: buyer "
                f"{buyer!r} does not have contiguous trade rank "
                f"{expected_rank}."
            )

    for seller in sellers_sorted:
        seller_baseline_rank = baseline_rank[seller]

        buyers_behind = 0
        for buyer in buyers_sorted:
            buyer_baseline_rank = baseline_rank[buyer]

            if buyer_baseline_rank > seller_baseline_rank:
                buyers_behind += 1

        expected_seller_rank = (
            seller_baseline_rank
            + buyers_behind
        )
        actual_seller_rank = trade_rank[seller]
        if actual_seller_rank != expected_seller_rank:
            raise RuntimeError(
                "Internal trade-rank inconsistency: seller "
                f"{seller!r} trade rank does not match seller retreat formula."
            )

    trade_scope_set = set(trade_scope)
    for visit_key in baseline_order:
        if visit_key not in trade_scope_set:
            if trade_rank[visit_key] != baseline_rank[visit_key]:
                raise RuntimeError(
                    "Internal trade-rank inconsistency: visit outside "
                    f"trade_scope {visit_key!r} changed rank."
                )


class OrderControlTvtNoNonparticipantTradeRankResult:
    """Trade-rank result for one candidate without non-participating vehicles."""

    def __init__(
        self,
        *,
        buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
        sellers_sorted: tuple[OrderControlTvtVisitKey, ...],
        last_buyer_rank: int,
        trade_order: tuple[OrderControlTvtVisitKey, ...],
        trade_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    ) -> None:
        buyers_tuple = _require_tuple_container(
            buyers_sorted,
            "buyers_sorted",
        )
        self._buyers_sorted = _validate_visit_key_sequence(
            buyers_tuple,
            field_name="buyers_sorted",
            allow_empty=False,
        )
        sellers_tuple = _require_tuple_container(
            sellers_sorted,
            "sellers_sorted",
        )
        self._sellers_sorted = _validate_visit_key_sequence(
            sellers_tuple,
            field_name="sellers_sorted",
            allow_empty=True,
        )
        self._last_buyer_rank = _require_python_int_rank(
            last_buyer_rank,
            field_name="last_buyer_rank",
        )
        trade_order_tuple = _require_tuple_container(
            trade_order,
            "trade_order",
        )
        self._trade_order = _validate_visit_key_sequence(
            trade_order_tuple,
            field_name="trade_order",
            allow_empty=False,
        )

        if not isinstance(trade_rank_by_visit_key, dict):
            raise ValueError(
                "trade_rank_by_visit_key must be a dict; got "
                f"type {type(trade_rank_by_visit_key).__name__}."
            )
        if len(trade_rank_by_visit_key) == 0:
            raise ValueError("trade_rank_by_visit_key must not be empty.")

        validated_trade_rank: dict[OrderControlTvtVisitKey, int] = {}
        for visit_key, rank_value in trade_rank_by_visit_key.items():
            validated_visit_key = _validate_visit_key(
                visit_key,
                field_name="trade_rank_by_visit_key key",
            )
            validated_trade_rank[validated_visit_key] = _require_python_int_rank(
                rank_value,
                field_name=f"trade_rank_by_visit_key[{validated_visit_key!r}]",
            )

        self._trade_rank_by_visit_key = dict(validated_trade_rank)

    @property
    def buyers_sorted(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._buyers_sorted

    @property
    def sellers_sorted(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._sellers_sorted

    @property
    def last_buyer_rank(self) -> int:
        return self._last_buyer_rank

    @property
    def trade_order(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._trade_order

    def assigned_rank(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> int:
        validated_visit_key = _validate_visit_key(visit_key)
        rank_value = self._trade_rank_by_visit_key.get(validated_visit_key)
        if rank_value is None:
            raise ValueError(
                f"VisitKey {validated_visit_key!r} is not present in this "
                "trade-rank result."
            )
        return rank_value

    def trade_rank_items(
        self,
    ) -> tuple[tuple[OrderControlTvtVisitKey, int], ...]:
        items: list[tuple[OrderControlTvtVisitKey, int]] = []
        for visit_key in self._trade_order:
            items.append((visit_key, self._trade_rank_by_visit_key[visit_key]))
        return tuple(items)


def build_tvt_trade_rank_without_nonparticipants(
    baseline_order:
        list[OrderControlTvtVisitKey]
        | tuple[OrderControlTvtVisitKey, ...],
    buyers:
        list[OrderControlTvtVisitKey]
        | tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtNoNonparticipantTradeRankResult:
    baseline_order_tuple = _require_list_or_tuple_container(
        baseline_order,
        "baseline_order",
    )
    baseline_order_tuple = _validate_visit_key_sequence(
        baseline_order_tuple,
        field_name="baseline_order",
        allow_empty=False,
    )

    baseline_rank: dict[OrderControlTvtVisitKey, int] = {}
    for rank, visit_key in enumerate(baseline_order_tuple, start=1):
        baseline_rank[visit_key] = rank

    buyers_tuple = _require_list_or_tuple_container(buyers, "buyers")
    buyers_tuple = _validate_visit_key_sequence(
        buyers_tuple,
        field_name="buyers",
        allow_empty=False,
    )

    for buyer in buyers_tuple:
        if buyer not in baseline_rank:
            raise ValueError(
                f"Buyer VisitKey {buyer!r} is not present in baseline_order."
            )

    buyers_sorted = tuple(
        sorted(buyers_tuple, key=lambda visit_key: baseline_rank[visit_key])
    )

    last_buyer = buyers_sorted[-1]
    last_buyer_rank = baseline_rank[last_buyer]
    trade_scope = baseline_order_tuple[:last_buyer_rank]
    buyer_set = set(buyers_sorted)

    sellers_sorted_list: list[OrderControlTvtVisitKey] = []
    for visit_key in trade_scope:
        if visit_key not in buyer_set:
            sellers_sorted_list.append(visit_key)
    sellers_sorted = tuple(sellers_sorted_list)

    trade_rank: dict[OrderControlTvtVisitKey, int] = {}

    for new_rank, buyer in enumerate(buyers_sorted, start=1):
        trade_rank[buyer] = new_rank

    for seller in sellers_sorted:
        seller_baseline_rank = baseline_rank[seller]

        buyers_behind = 0
        for buyer in buyers_sorted:
            buyer_baseline_rank = baseline_rank[buyer]

            if buyer_baseline_rank > seller_baseline_rank:
                buyers_behind += 1

        seller_trade_rank = (
            seller_baseline_rank
            + buyers_behind
        )
        trade_rank[seller] = seller_trade_rank

    trade_scope_set = set(trade_scope)
    for visit_key in baseline_order_tuple:
        if visit_key not in trade_scope_set:
            trade_rank[visit_key] = baseline_rank[visit_key]

    trade_order = tuple(
        sorted(
            baseline_order_tuple,
            key=lambda visit_key: trade_rank[visit_key],
        )
    )

    _verify_local_trade_rank_state(
        baseline_order=baseline_order_tuple,
        baseline_rank=baseline_rank,
        buyers_sorted=buyers_sorted,
        sellers_sorted=sellers_sorted,
        last_buyer_rank=last_buyer_rank,
        trade_scope=trade_scope,
        trade_rank=trade_rank,
        trade_order=trade_order,
    )

    return OrderControlTvtNoNonparticipantTradeRankResult(
        buyers_sorted=buyers_sorted,
        sellers_sorted=sellers_sorted,
        last_buyer_rank=last_buyer_rank,
        trade_order=trade_order,
        trade_rank_by_visit_key=trade_rank,
    )


def preserves_inlink_fifo(
    baseline_order:
        list[OrderControlTvtVisitKey]
        | tuple[OrderControlTvtVisitKey, ...],
    trade_order:
        list[OrderControlTvtVisitKey]
        | tuple[OrderControlTvtVisitKey, ...],
    inlink_name_by_visit_key: dict[OrderControlTvtVisitKey, str],
) -> bool:
    """Return whether inlink-relative order is preserved within trade_scope.

    Both ``baseline_order`` and ``trade_order`` must be the trade_scope
    sequences (before trade and after trade within the same scope).
    """
    baseline_order_tuple = _require_list_or_tuple_container(
        baseline_order,
        "baseline_order",
    )
    baseline_order_tuple = _validate_visit_key_sequence(
        baseline_order_tuple,
        field_name="baseline_order",
        allow_empty=False,
    )

    trade_order_tuple = _require_list_or_tuple_container(
        trade_order,
        "trade_order",
    )
    trade_order_tuple = _validate_visit_key_sequence(
        trade_order_tuple,
        field_name="trade_order",
        allow_empty=False,
    )

    if len(baseline_order_tuple) != len(trade_order_tuple):
        raise ValueError(
            "baseline_order and trade_order must have the same length; "
            f"got {len(baseline_order_tuple)} and {len(trade_order_tuple)}."
        )

    if set(baseline_order_tuple) != set(trade_order_tuple):
        raise ValueError(
            "baseline_order and trade_order must contain the same VisitKey set."
        )

    if not isinstance(inlink_name_by_visit_key, dict):
        raise ValueError(
            "inlink_name_by_visit_key must be a dict; got "
            f"type {type(inlink_name_by_visit_key).__name__}."
        )

    inlink_names_for_scope: set[str] = set()
    for visit_key in baseline_order_tuple:
        inlink_name = inlink_name_by_visit_key.get(visit_key)
        if inlink_name is None:
            raise ValueError(
                f"Missing inlink name for VisitKey {visit_key!r} in "
                "inlink_name_by_visit_key."
            )
        inlink_name = _require_non_empty_str(
            inlink_name,
            f"inlink_name_by_visit_key[{visit_key!r}]",
        )
        inlink_names_for_scope.add(inlink_name)

    for inlink_name in sorted(inlink_names_for_scope):
        baseline_inlink_order: list[OrderControlTvtVisitKey] = []
        for visit_key in baseline_order_tuple:
            if inlink_name_by_visit_key[visit_key] == inlink_name:
                baseline_inlink_order.append(visit_key)

        trade_inlink_order: list[OrderControlTvtVisitKey] = []
        for visit_key in trade_order_tuple:
            if inlink_name_by_visit_key[visit_key] == inlink_name:
                trade_inlink_order.append(visit_key)

        if baseline_inlink_order != trade_inlink_order:
            return False

    return True
