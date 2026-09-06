"""
Align Node baseline collector records with Node rank-state undetermined visits.

Classifies snapshot-fixed baseline visit records against the per-Node rank ledger
for TVT upper-control research. Does not confirm ranks, select right-of-entry
vehicles, or modify collector or rank-state objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a bool; got {value!r}.")
    return value


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative int (not bool); got {value!r}."
        )
    return value


def _require_timestep(value: Any, field_name: str) -> int:
    return _require_non_negative_int(value, field_name)


def _require_arrival_tiebreaker(value: Any, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be an int or float (not bool); got {value!r}."
        )
    return value


def _extract_visit_key_from_record(
    record: dict[str, Any],
    record_index: int,
) -> OrderControlTvtVisitKey:
    prefix = f"node_baseline_visit_records[{record_index}]"
    vehicle_name = record.get("vehicle_name")
    visit_id = record.get("visit_id")

    vehicle_name = _require_non_empty_str(
        vehicle_name,
        f"{prefix}.vehicle_name",
    )
    if type(visit_id) is not int:
        raise ValueError(
            f"{prefix}.visit_id must be a Python int (not bool); "
            f"got type {type(visit_id).__name__} with value {visit_id!r}."
        )
    if visit_id < 1:
        raise ValueError(
            f"{prefix}.visit_id must be >= 1; got {visit_id!r}."
        )
    return (vehicle_name, visit_id)


def _visit_key_sort_key(visit_key: OrderControlTvtVisitKey) -> tuple[str, int]:
    return (visit_key[0], visit_key[1])


def _resolved_visit_sort_key(
    resolved_visit: OrderControlTvtResolvedUndeterminedVisit,
) -> tuple[int, int | float, int]:
    return (
        resolved_visit.baseline_arrival_timestep,
        resolved_visit.arrival_tiebreaker,
        resolved_visit.vehicle_id,
    )


def _verify_no_cross_bucket_duplicate_visit_keys(
    resolved_visits: tuple[OrderControlTvtResolvedUndeterminedVisit, ...],
    unresolved_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    unregistered_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> None:
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    for resolved_visit in resolved_visits:
        visit_key = resolved_visit.visit_key
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                "Internal alignment inconsistency: duplicate VisitKey "
                f"{visit_key!r} across result buckets."
            )
        seen_visit_keys.add(visit_key)

    for visit_key in unresolved_visit_keys:
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                "Internal alignment inconsistency: duplicate VisitKey "
                f"{visit_key!r} across result buckets."
            )
        seen_visit_keys.add(visit_key)

    for visit_key in unregistered_visit_keys:
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                "Internal alignment inconsistency: duplicate VisitKey "
                f"{visit_key!r} across result buckets."
            )
        seen_visit_keys.add(visit_key)


@dataclass(frozen=True)
class OrderControlTvtResolvedUndeterminedVisit:
    visit_key: OrderControlTvtVisitKey
    baseline_arrival_timestep: int
    arrival_tiebreaker: int | float
    vehicle_id: int


@dataclass(frozen=True)
class OrderControlTvtSnapshotUndeterminedAlignmentResult:
    node_name: str
    resolved_undetermined_visits: tuple[
        OrderControlTvtResolvedUndeterminedVisit, ...
    ]
    unresolved_undetermined_visits: tuple[
        OrderControlTvtVisitKey, ...
    ]
    unregistered_collector_visit_keys: tuple[
        OrderControlTvtVisitKey, ...
    ]

    @property
    def all_collector_undetermined_arrivals_resolved(self) -> bool:
        return len(self.unresolved_undetermined_visits) == 0

    @property
    def has_unregistered_collector_visits(self) -> bool:
        return len(self.unregistered_collector_visit_keys) > 0


def align_snapshot_undetermined_visits_with_node_baseline(
    *,
    node_name: str,
    node_baseline_visit_records: list[dict],
    node_rank_state: OrderControlTvtNodeRankState,
) -> OrderControlTvtSnapshotUndeterminedAlignmentResult:
    """
    Classify collector visit records against rank-state undetermined visits.

    Processing starts from collector records. Only visits that are both present
    in the collector input and undetermined in the rank ledger are classified
    into resolved or unresolved buckets.
    """
    validated_node_name = _require_non_empty_str(node_name, "node_name")
    if node_rank_state.node_name != validated_node_name:
        raise ValueError(
            f"node_name mismatch: input node_name={validated_node_name!r}, "
            f"node_rank_state.node_name={node_rank_state.node_name!r}."
        )

    seen_input_visit_keys: set[OrderControlTvtVisitKey] = set()
    resolved_visits: list[OrderControlTvtResolvedUndeterminedVisit] = []
    unresolved_visit_keys: list[OrderControlTvtVisitKey] = []
    unregistered_visit_keys: list[OrderControlTvtVisitKey] = []

    for record_index, record in enumerate(node_baseline_visit_records):
        if not isinstance(record, dict):
            raise ValueError(
                "node_baseline_visit_records must contain dict records; "
                f"got type {type(record).__name__} at index {record_index}."
            )

        visit_key = _extract_visit_key_from_record(record, record_index)
        if visit_key in seen_input_visit_keys:
            raise ValueError(
                f"Duplicate VisitKey {visit_key!r} in node_baseline_visit_records."
            )
        seen_input_visit_keys.add(visit_key)

        if node_rank_state.is_confirmed(visit_key):
            continue

        if not node_rank_state.is_undetermined(visit_key):
            unregistered_visit_keys.append(visit_key)
            continue

        record_prefix = f"node_baseline_visit_records[{record_index}]"
        baseline_arrival_timestep = record.get("baseline_arrival_timestep")
        arrival_tiebreaker = record.get("arrival_tiebreaker")

        arrival_both_present = (
            baseline_arrival_timestep is not None
            and arrival_tiebreaker is not None
        )
        arrival_both_none = (
            baseline_arrival_timestep is None and arrival_tiebreaker is None
        )
        arrival_partially_present = (
            baseline_arrival_timestep is None
        ) != (arrival_tiebreaker is None)

        if arrival_partially_present:
            raise ValueError(
                f"Partial arrival state for VisitKey {visit_key!r} in "
                f"{record_prefix}: baseline_arrival_timestep="
                f"{baseline_arrival_timestep!r}, arrival_tiebreaker="
                f"{arrival_tiebreaker!r}."
            )

        if arrival_both_present:
            validated_baseline_arrival_timestep = _require_timestep(
                baseline_arrival_timestep,
                f"{record_prefix}.baseline_arrival_timestep",
            )
            validated_arrival_tiebreaker = _require_arrival_tiebreaker(
                arrival_tiebreaker,
                f"{record_prefix}.arrival_tiebreaker",
            )
            validated_vehicle_id = _require_non_negative_int(
                record.get("vehicle_id"),
                f"{record_prefix}.vehicle_id",
            )
            resolved_visits.append(
                OrderControlTvtResolvedUndeterminedVisit(
                    visit_key=visit_key,
                    baseline_arrival_timestep=validated_baseline_arrival_timestep,
                    arrival_tiebreaker=validated_arrival_tiebreaker,
                    vehicle_id=validated_vehicle_id,
                )
            )
            continue

        if arrival_both_none:
            was_arrived_at_snapshot = record.get("was_arrived_at_snapshot")
            if was_arrived_at_snapshot is True:
                raise ValueError(
                    f"Missing arrival facts for snapshot-arrived visit "
                    f"{visit_key!r} in {record_prefix}."
                )
            if was_arrived_at_snapshot is not False:
                raise ValueError(
                    f"was_arrived_at_snapshot must be False for unresolved "
                    f"B-type visit {visit_key!r} in {record_prefix}; "
                    f"got {was_arrived_at_snapshot!r}."
                )
            unresolved_visit_keys.append(visit_key)
            continue

        raise RuntimeError(
            "Internal alignment inconsistency: undetermined VisitKey "
            f"{visit_key!r} reached an unhandled arrival-state branch."
        )

    resolved_visits.sort(key=_resolved_visit_sort_key)
    unresolved_visit_keys.sort(key=_visit_key_sort_key)
    unregistered_visit_keys.sort(key=_visit_key_sort_key)

    resolved_visits_tuple = tuple(resolved_visits)
    unresolved_visit_keys_tuple = tuple(unresolved_visit_keys)
    unregistered_visit_keys_tuple = tuple(unregistered_visit_keys)

    _verify_no_cross_bucket_duplicate_visit_keys(
        resolved_visits_tuple,
        unresolved_visit_keys_tuple,
        unregistered_visit_keys_tuple,
    )

    return OrderControlTvtSnapshotUndeterminedAlignmentResult(
        node_name=validated_node_name,
        resolved_undetermined_visits=resolved_visits_tuple,
        unresolved_undetermined_visits=unresolved_visit_keys_tuple,
        unregistered_collector_visit_keys=unregistered_visit_keys_tuple,
    )
