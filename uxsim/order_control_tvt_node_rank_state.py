"""
Node-specific TVT rank state for order-control research.

Stores a confirmed rank block and an undetermined visit set per Node.
External institutional logic decides which visits to register and in which
order to confirm them; this module only validates inputs and persists ranks
safely without partial updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

OrderControlTvtVisitKey = tuple[str, int]


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _validate_visit_key(value: Any, field_name: str = "visit_key") -> OrderControlTvtVisitKey:
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


def _find_duplicate_visit_keys(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    seen: set[OrderControlTvtVisitKey] = set()
    for visit_key in visit_keys:
        if visit_key in seen:
            return visit_key
        seen.add(visit_key)
    return None


def _verify_candidate_confirmed_state(
    candidate_confirmed_visit_keys_in_order: list[OrderControlTvtVisitKey],
    candidate_confirmed_rank_by_visit_key: dict[OrderControlTvtVisitKey, int],
    candidate_undetermined_visit_keys: set[OrderControlTvtVisitKey],
    *,
    k_confirmed_before: int,
    k_confirmed_after: int,
    newly_confirmed_count: int,
    newly_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    list_length = len(candidate_confirmed_visit_keys_in_order)
    dict_length = len(candidate_confirmed_rank_by_visit_key)
    if list_length != dict_length:
        raise RuntimeError(
            "Internal rank-state inconsistency: confirmed list length "
            f"{list_length} does not match confirmed rank dict length "
            f"{dict_length}."
        )

    if k_confirmed_after != list_length:
        raise RuntimeError(
            "Internal rank-state inconsistency: k_confirmed_after "
            f"{k_confirmed_after} does not match confirmed list length "
            f"{list_length}."
        )

    seen_in_list: set[OrderControlTvtVisitKey] = set()
    for position, visit_key in enumerate(
        candidate_confirmed_visit_keys_in_order,
        start=1,
    ):
        if visit_key in seen_in_list:
            raise RuntimeError(
                "Internal rank-state inconsistency: duplicate confirmed "
                f"VisitKey {visit_key!r} in confirmed list."
            )
        seen_in_list.add(visit_key)

        rank_in_dict = candidate_confirmed_rank_by_visit_key.get(visit_key)
        if rank_in_dict is None:
            raise RuntimeError(
                "Internal rank-state inconsistency: confirmed VisitKey "
                f"{visit_key!r} is missing from confirmed rank dict."
            )
        if rank_in_dict != position:
            raise RuntimeError(
                "Internal rank-state inconsistency: confirmed VisitKey "
                f"{visit_key!r} has list position {position} but rank dict "
                f"stores assigned_rank {rank_in_dict}."
            )

        if visit_key in candidate_undetermined_visit_keys:
            raise RuntimeError(
                "Internal rank-state inconsistency: confirmed VisitKey "
                f"{visit_key!r} is still present in the undetermined set."
            )

    for visit_key in newly_confirmed_visit_keys:
        if visit_key in candidate_undetermined_visit_keys:
            raise RuntimeError(
                "Internal rank-state inconsistency: newly confirmed VisitKey "
                f"{visit_key!r} was not removed from the undetermined set."
            )

    expected_newly_confirmed_count = k_confirmed_after - k_confirmed_before
    if newly_confirmed_count != expected_newly_confirmed_count:
        raise RuntimeError(
            "Internal rank-state inconsistency: newly_confirmed_count "
            f"{newly_confirmed_count} does not equal "
            f"k_confirmed_after - k_confirmed_before "
            f"({k_confirmed_after} - {k_confirmed_before} = "
            f"{expected_newly_confirmed_count})."
        )


@dataclass(frozen=True)
class OrderControlTvtConfirmResult:
    k_confirmed_before: int
    k_confirmed_after: int
    newly_confirmed_count: int


class OrderControlTvtNodeRankState:
    """Per-Node ledger of confirmed ranks and undetermined visits."""

    def __init__(self, node_name: str) -> None:
        self._node_name = _require_non_empty_str(node_name, "node_name")
        self._confirmed_visit_keys_in_order: list[OrderControlTvtVisitKey] = []
        self._confirmed_rank_by_visit_key: dict[OrderControlTvtVisitKey, int] = {}
        self._undetermined_visit_keys: set[OrderControlTvtVisitKey] = set()

    @property
    def node_name(self) -> str:
        return self._node_name

    def k_confirmed(self) -> int:
        return len(self._confirmed_visit_keys_in_order)

    def register_undetermined_visit(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> None:
        validated_visit_key = _validate_visit_key(visit_key)

        if validated_visit_key in self._confirmed_rank_by_visit_key:
            assigned_rank = self._confirmed_rank_by_visit_key[validated_visit_key]
            raise ValueError(
                f"VisitKey {validated_visit_key!r} is already confirmed with "
                f"assigned_rank {assigned_rank}; cannot register as undetermined."
            )

        if validated_visit_key in self._undetermined_visit_keys:
            raise ValueError(
                f"VisitKey {validated_visit_key!r} is already registered as "
                "undetermined."
            )

        self._undetermined_visit_keys.add(validated_visit_key)

    def register_undetermined_visits(
        self,
        visit_keys: list[OrderControlTvtVisitKey]
        | tuple[OrderControlTvtVisitKey, ...],
    ) -> None:
        visit_keys_tuple = _require_list_or_tuple_container(
            visit_keys,
            "visit_keys",
        )
        if len(visit_keys_tuple) == 0:
            return

        validated_visit_keys: list[OrderControlTvtVisitKey] = []
        for index, visit_key in enumerate(visit_keys_tuple):
            validated_visit_keys.append(
                _validate_visit_key(visit_key, field_name=f"visit_keys[{index}]")
            )
        validated_visit_keys_tuple = tuple(validated_visit_keys)

        duplicate_in_input = _find_duplicate_visit_keys(validated_visit_keys_tuple)
        if duplicate_in_input is not None:
            raise ValueError(
                f"Duplicate VisitKey {duplicate_in_input!r} in visit_keys input."
            )

        for visit_key in validated_visit_keys_tuple:
            if visit_key in self._undetermined_visit_keys:
                raise ValueError(
                    f"VisitKey {visit_key!r} is already registered as undetermined."
                )

        for visit_key in validated_visit_keys_tuple:
            if visit_key in self._confirmed_rank_by_visit_key:
                assigned_rank = self._confirmed_rank_by_visit_key[visit_key]
                raise ValueError(
                    f"VisitKey {visit_key!r} is already confirmed with "
                    f"assigned_rank {assigned_rank}; cannot register as undetermined."
                )

        candidate_undetermined_visit_keys = set(self._undetermined_visit_keys)
        for visit_key in validated_visit_keys_tuple:
            candidate_undetermined_visit_keys.add(visit_key)

        self._undetermined_visit_keys = candidate_undetermined_visit_keys

    def confirm_visits_in_order(
        self,
        visit_keys_in_order: list[OrderControlTvtVisitKey]
        | tuple[OrderControlTvtVisitKey, ...],
    ) -> OrderControlTvtConfirmResult:
        visit_keys_tuple = _require_list_or_tuple_container(
            visit_keys_in_order,
            "visit_keys_in_order",
        )

        if len(visit_keys_tuple) == 0:
            current_k_confirmed = self.k_confirmed()
            return OrderControlTvtConfirmResult(
                k_confirmed_before=current_k_confirmed,
                k_confirmed_after=current_k_confirmed,
                newly_confirmed_count=0,
            )

        validated_visit_keys: list[OrderControlTvtVisitKey] = []
        for index, visit_key in enumerate(visit_keys_tuple):
            validated_visit_keys.append(
                _validate_visit_key(
                    visit_key,
                    field_name=f"visit_keys_in_order[{index}]",
                )
            )
        validated_visit_keys_tuple = tuple(validated_visit_keys)

        duplicate_in_input = _find_duplicate_visit_keys(validated_visit_keys_tuple)
        if duplicate_in_input is not None:
            raise ValueError(
                "Duplicate VisitKey "
                f"{duplicate_in_input!r} in visit_keys_in_order input."
            )

        for visit_key in validated_visit_keys_tuple:
            if visit_key in self._confirmed_rank_by_visit_key:
                assigned_rank = self._confirmed_rank_by_visit_key[visit_key]
                raise ValueError(
                    f"VisitKey {visit_key!r} is already confirmed with "
                    f"assigned_rank {assigned_rank}; cannot confirm again."
                )

        for visit_key in validated_visit_keys_tuple:
            if visit_key not in self._undetermined_visit_keys:
                raise ValueError(
                    f"VisitKey {visit_key!r} is not pre-registered as an undetermined "
                    "visit; cannot confirm."
                )

        k_confirmed_before = self.k_confirmed()

        candidate_confirmed_visit_keys_in_order = list(
            self._confirmed_visit_keys_in_order
        )
        candidate_confirmed_rank_by_visit_key = dict(
            self._confirmed_rank_by_visit_key
        )
        candidate_undetermined_visit_keys = set(self._undetermined_visit_keys)

        next_rank = k_confirmed_before + 1
        for visit_key in validated_visit_keys_tuple:
            candidate_confirmed_visit_keys_in_order.append(visit_key)
            candidate_confirmed_rank_by_visit_key[visit_key] = next_rank
            candidate_undetermined_visit_keys.discard(visit_key)
            next_rank += 1

        k_confirmed_after = len(candidate_confirmed_visit_keys_in_order)
        newly_confirmed_count = len(validated_visit_keys_tuple)

        _verify_candidate_confirmed_state(
            candidate_confirmed_visit_keys_in_order,
            candidate_confirmed_rank_by_visit_key,
            candidate_undetermined_visit_keys,
            k_confirmed_before=k_confirmed_before,
            k_confirmed_after=k_confirmed_after,
            newly_confirmed_count=newly_confirmed_count,
            newly_confirmed_visit_keys=validated_visit_keys_tuple,
        )

        self._confirmed_visit_keys_in_order = candidate_confirmed_visit_keys_in_order
        self._confirmed_rank_by_visit_key = candidate_confirmed_rank_by_visit_key
        self._undetermined_visit_keys = candidate_undetermined_visit_keys

        return OrderControlTvtConfirmResult(
            k_confirmed_before=k_confirmed_before,
            k_confirmed_after=k_confirmed_after,
            newly_confirmed_count=newly_confirmed_count,
        )

    def confirmed_visit_keys_in_order(
        self,
    ) -> tuple[OrderControlTvtVisitKey, ...]:
        return tuple(self._confirmed_visit_keys_in_order)

    def undetermined_visit_keys(
        self,
    ) -> frozenset[OrderControlTvtVisitKey]:
        return frozenset(self._undetermined_visit_keys)

    def is_confirmed(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> bool:
        validated_visit_key = _validate_visit_key(visit_key)
        return validated_visit_key in self._confirmed_rank_by_visit_key

    def is_undetermined(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> bool:
        validated_visit_key = _validate_visit_key(visit_key)
        return validated_visit_key in self._undetermined_visit_keys

    def assigned_rank(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> int | None:
        validated_visit_key = _validate_visit_key(visit_key)
        return self._confirmed_rank_by_visit_key.get(validated_visit_key)

    def export_state(self) -> dict[str, object]:
        confirmed_visits: list[dict[str, object]] = []
        for visit_key in self._confirmed_visit_keys_in_order:
            vehicle_name, visit_id = visit_key
            assigned_rank = self._confirmed_rank_by_visit_key[visit_key]
            confirmed_visits.append(
                {
                    "vehicle_name": vehicle_name,
                    "visit_id": visit_id,
                    "assigned_rank": assigned_rank,
                }
            )

        undetermined_visit_list = sorted(
            self._undetermined_visit_keys,
            key=lambda item: (item[0], item[1]),
        )
        undetermined_visits: list[dict[str, object]] = []
        for vehicle_name, visit_id in undetermined_visit_list:
            undetermined_visits.append(
                {
                    "vehicle_name": vehicle_name,
                    "visit_id": visit_id,
                }
            )

        return {
            "node_name": self._node_name,
            "k_confirmed": self.k_confirmed(),
            "confirmed_visits": confirmed_visits,
            "undetermined_visits": undetermined_visits,
        }
