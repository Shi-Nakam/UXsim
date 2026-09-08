"""
Build TVT candidate visit sets after right-of-entry selection.

Reads right-of-entry selection results and rank states, obtains baseline passage
timestep P from the fork collector, determines the P - 1 candidate population,
and checks baseline information completeness for all candidates. Does not
modify rank ledgers, collector records, or rerun upstream processing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionStatus,
)


class OrderControlTvtCandidateVisitSetStatus(Enum):
    """Per-Node outcome of TVT candidate visit set construction."""

    NOT_BUILT_NO_RIGHT_OF_ENTRY = "not_built_no_right_of_entry"
    NOT_BUILT_UNRESOLVED_ARRIVALS = "not_built_unresolved_arrivals"
    UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE = "unresolved_right_of_entry_passage"
    UNRESOLVED_CANDIDATE_PASSAGES = "unresolved_candidate_passages"
    BASELINE_INFORMATION_COMPLETE = "baseline_information_complete"


@dataclass(frozen=True)
class OrderControlTvtCandidateVisit:
    """One candidate visit in the TVT candidate population."""

    visit_key: OrderControlTvtVisitKey
    vehicle_id: int
    inlink_name: str
    baseline_arrival_timestep: int
    arrival_tiebreaker: int | float
    route_next_link_name: str
    baseline_passage_timestep: int | None


@dataclass(frozen=True)
class OrderControlTvtNodeCandidateVisitSetResult:
    """Per-Node result of TVT candidate visit set construction."""

    node_name: str
    build_status: OrderControlTvtCandidateVisitSetStatus
    right_of_entry_visit_key: OrderControlTvtVisitKey | None
    right_of_entry_baseline_passage_timestep: int | None
    k_confirmed_before: int
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...]


@dataclass(frozen=True)
class OrderControlTvtCandidateVisitSetResult:
    """Overall result of TVT candidate visit set construction."""

    right_of_entry_selection_result: OrderControlTvtRightOfEntrySelectionResult
    node_candidate_set_results: tuple[
        OrderControlTvtNodeCandidateVisitSetResult,
        ...
    ]


def _verify_node_name_at_index(
    *,
    node_index: int,
    expected_node_name: str,
    actual_node_name: str,
    source_label: str,
) -> None:
    if actual_node_name != expected_node_name:
        raise RuntimeError(
            f"Node name mismatch at index {node_index}: expected "
            f"target_node_names entry {expected_node_name!r}, but "
            f"{source_label} has {actual_node_name!r}."
        )


def _require_non_empty_str(value: object, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise RuntimeError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _require_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise RuntimeError(f"{field_name} must be a Python bool; got {value!r}.")
    return value


def _require_non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(
            f"{field_name} must be a non-negative int (not bool); got {value!r}."
        )
    return value


def _require_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RuntimeError(
            f"{field_name} must be a positive int (not bool); got {value!r}."
        )
    return value


def _require_arrival_tiebreaker(value: object, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(
            f"{field_name} must be an int or float (not bool); got {value!r}."
        )
    return value


def _require_optional_passage_timestep(
    value: object,
    field_name: str,
) -> int | None:
    if value is None:
        return None
    return _require_non_negative_int(value, field_name)


def _verify_passage_not_before_arrival(
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    baseline_arrival_timestep: int,
    baseline_passage_timestep: int,
) -> None:
    if baseline_passage_timestep < baseline_arrival_timestep + 1:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} has "
            f"baseline_passage_timestep={baseline_passage_timestep}, but "
            f"baseline_arrival_timestep={baseline_arrival_timestep}; "
            f"expected baseline_passage_timestep >= baseline_arrival_timestep + 1."
        )


def _visit_key_from_record(record: Mapping[str, object]) -> OrderControlTvtVisitKey:
    vehicle_name = _require_non_empty_str(record["vehicle_name"], "vehicle_name")
    visit_id = _require_positive_int(record["visit_id"], "visit_id")
    return (vehicle_name, visit_id)


def _verify_record_node_name(
    *,
    node_name: str,
    record: Mapping[str, object],
    visit_key: OrderControlTvtVisitKey,
) -> None:
    record_node_name = _require_non_empty_str(record["node_name"], "node_name")
    if record_node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: collector record for VisitKey {visit_key!r} "
            f"has node_name={record_node_name!r}."
        )


def _verify_right_of_entry_record(
    *,
    node_name: str,
    right_of_entry_visit_key: OrderControlTvtVisitKey,
    record: Mapping[str, object],
) -> tuple[int, int]:
    record_visit_key = _visit_key_from_record(record)
    if record_visit_key != right_of_entry_visit_key:
        raise RuntimeError(
            f"Node {node_name!r}: collector record VisitKey {record_visit_key!r} "
            f"does not match right_of_entry_visit_key {right_of_entry_visit_key!r}."
        )
    _verify_record_node_name(
        node_name=node_name,
        record=record,
        visit_key=right_of_entry_visit_key,
    )
    was_arrived_at_snapshot = _require_bool(
        record["was_arrived_at_snapshot"],
        "was_arrived_at_snapshot",
    )
    if was_arrived_at_snapshot:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} was_arrived_at_snapshot is True, but "
            f"right-of-entry Visit must be B-type (was_arrived_at_snapshot=False)."
        )
    baseline_arrival_timestep = _require_non_negative_int(
        record["baseline_arrival_timestep"],
        "baseline_arrival_timestep",
    )
    passage_timestep = _require_optional_passage_timestep(
        record["baseline_passage_timestep"],
        "baseline_passage_timestep",
    )
    if passage_timestep is not None:
        _verify_passage_not_before_arrival(
            node_name=node_name,
            visit_key=right_of_entry_visit_key,
            baseline_arrival_timestep=baseline_arrival_timestep,
            baseline_passage_timestep=passage_timestep,
        )
    return baseline_arrival_timestep, passage_timestep


def _candidate_visit_from_record(
    *,
    node_name: str,
    record: Mapping[str, object],
) -> OrderControlTvtCandidateVisit:
    visit_key = _visit_key_from_record(record)
    _verify_record_node_name(node_name=node_name, record=record, visit_key=visit_key)
    vehicle_id = _require_non_negative_int(record["vehicle_id"], "vehicle_id")
    inlink_name = _require_non_empty_str(record["inlink_name"], "inlink_name")
    baseline_arrival_timestep = _require_non_negative_int(
        record["baseline_arrival_timestep"],
        "baseline_arrival_timestep",
    )
    arrival_tiebreaker = _require_arrival_tiebreaker(
        record["arrival_tiebreaker"],
        "arrival_tiebreaker",
    )
    route_next_link_name = _require_non_empty_str(
        record["route_next_link_name"],
        "route_next_link_name",
    )
    baseline_passage_timestep = _require_optional_passage_timestep(
        record["baseline_passage_timestep"],
        "baseline_passage_timestep",
    )
    if baseline_passage_timestep is not None:
        _verify_passage_not_before_arrival(
            node_name=node_name,
            visit_key=visit_key,
            baseline_arrival_timestep=baseline_arrival_timestep,
            baseline_passage_timestep=baseline_passage_timestep,
        )
    return OrderControlTvtCandidateVisit(
        visit_key=visit_key,
        vehicle_id=vehicle_id,
        inlink_name=inlink_name,
        baseline_arrival_timestep=baseline_arrival_timestep,
        arrival_tiebreaker=arrival_tiebreaker,
        route_next_link_name=route_next_link_name,
        baseline_passage_timestep=baseline_passage_timestep,
    )


def _verify_right_of_entry_in_candidate_visits(
    *,
    node_name: str,
    right_of_entry_visit_key: OrderControlTvtVisitKey,
    candidate_visits: tuple[OrderControlTvtCandidateVisit, ...],
) -> None:
    matches = [
        candidate
        for candidate in candidate_visits
        if candidate.visit_key == right_of_entry_visit_key
    ]
    if len(matches) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} is missing from the candidate visit set."
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"Node {node_name!r}: right-of-entry VisitKey "
            f"{right_of_entry_visit_key!r} appears more than once in the "
            f"candidate visit set."
        )


def _build_not_built_node_result(
    *,
    node_name: str,
    build_status: OrderControlTvtCandidateVisitSetStatus,
    k_confirmed_before: int,
) -> OrderControlTvtNodeCandidateVisitSetResult:
    return OrderControlTvtNodeCandidateVisitSetResult(
        node_name=node_name,
        build_status=build_status,
        right_of_entry_visit_key=None,
        right_of_entry_baseline_passage_timestep=None,
        k_confirmed_before=k_confirmed_before,
        candidate_visits=(),
    )


def build_tvt_candidate_visit_set(
    right_of_entry_selection_result: OrderControlTvtRightOfEntrySelectionResult,
    *,
    rank_states_by_node_name: Mapping[str, OrderControlTvtNodeRankState],
) -> OrderControlTvtCandidateVisitSetResult:
    """
    Build TVT candidate visit sets from right-of-entry selection results.

    Walks ``fork_result.target_node_names`` in order, reads the fork collector
    for selected Nodes, obtains passage timestep P, builds the P - 1 candidate
    population, and checks baseline information completeness. Does not modify
    rank ledgers, collector records, World state, or rerun upstream processing.
    """
    leading_confirmation_result = (
        right_of_entry_selection_result.leading_confirmation_result
    )
    arrived_confirmation_result = leading_confirmation_result.arrived_confirmation_result
    alignment_fork_result = arrived_confirmation_result.alignment_fork_result
    fork_result = alignment_fork_result.fork_result
    collector = fork_result.collector
    selection_node_results = right_of_entry_selection_result.node_selection_results

    node_candidate_set_results: list[OrderControlTvtNodeCandidateVisitSetResult] = []

    for node_index, node_name in enumerate(fork_result.target_node_names):
        selection_node_result = selection_node_results[node_index]
        _verify_node_name_at_index(
            node_index=node_index,
            expected_node_name=node_name,
            actual_node_name=selection_node_result.node_name,
            source_label="right-of-entry selection result",
        )

        k_confirmed_before = selection_node_result.k_confirmed_before
        selection_status = selection_node_result.selection_status

        if selection_status == OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY:
            node_candidate_set_results.append(
                _build_not_built_node_result(
                    node_name=node_name,
                    build_status=(
                        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
                    ),
                    k_confirmed_before=k_confirmed_before,
                )
            )
            continue

        if (
            selection_status
            == OrderControlTvtRightOfEntrySelectionStatus.UNRESOLVED_BASELINE_ARRIVALS
        ):
            node_candidate_set_results.append(
                _build_not_built_node_result(
                    node_name=node_name,
                    build_status=(
                        OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS
                    ),
                    k_confirmed_before=k_confirmed_before,
                )
            )
            continue

        if selection_status != OrderControlTvtRightOfEntrySelectionStatus.SELECTED:
            raise RuntimeError(
                f"Node {node_name!r}: unexpected right-of-entry selection status "
                f"{selection_status!r}."
            )

        right_of_entry_visit_key = selection_node_result.right_of_entry_visit_key
        if right_of_entry_visit_key is None:
            raise RuntimeError(
                f"Node {node_name!r}: selection_status is SELECTED but "
                f"right_of_entry_visit_key is None."
            )

        vehicle_name, visit_id = right_of_entry_visit_key
        right_of_entry_record = collector.get_baseline_visit_snapshot(
            vehicle_name,
            visit_id,
        )
        if right_of_entry_record is None:
            raise RuntimeError(
                f"Node {node_name!r}: collector has no record for right-of-entry "
                f"VisitKey {right_of_entry_visit_key!r}."
            )

        _, passage_timestep = _verify_right_of_entry_record(
            node_name=node_name,
            right_of_entry_visit_key=right_of_entry_visit_key,
            record=right_of_entry_record,
        )

        if passage_timestep is None:
            node_candidate_set_results.append(
                OrderControlTvtNodeCandidateVisitSetResult(
                    node_name=node_name,
                    build_status=(
                        OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE
                    ),
                    right_of_entry_visit_key=right_of_entry_visit_key,
                    right_of_entry_baseline_passage_timestep=None,
                    k_confirmed_before=k_confirmed_before,
                    candidate_visits=(),
                )
            )
            continue

        p = passage_timestep
        node_rank_state = rank_states_by_node_name[node_name]
        exported_records = collector.export_node_baseline_visits(node_name)

        candidate_visits_list: list[OrderControlTvtCandidateVisit] = []
        for record in exported_records:
            record_visit_key = _visit_key_from_record(record)
            _verify_record_node_name(
                node_name=node_name,
                record=record,
                visit_key=record_visit_key,
            )

            was_arrived_at_snapshot = _require_bool(
                record["was_arrived_at_snapshot"],
                "was_arrived_at_snapshot",
            )
            if was_arrived_at_snapshot:
                continue

            if not node_rank_state.is_undetermined(record_visit_key):
                if node_rank_state.is_confirmed(record_visit_key):
                    continue
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {record_visit_key!r} is not "
                    f"undetermined and not confirmed in the rank ledger."
                )

            baseline_arrival_timestep_value = record["baseline_arrival_timestep"]
            if baseline_arrival_timestep_value is None:
                raise RuntimeError(
                    f"Node {node_name!r}: undetermined B-type VisitKey "
                    f"{record_visit_key!r} has baseline_arrival_timestep=None."
                )
            baseline_arrival_timestep = _require_non_negative_int(
                baseline_arrival_timestep_value,
                "baseline_arrival_timestep",
            )
            if baseline_arrival_timestep > p - 1:
                continue

            candidate_visits_list.append(
                _candidate_visit_from_record(
                    node_name=node_name,
                    record=record,
                )
            )

        candidate_visits_list.sort(
            key=lambda candidate: (
                candidate.baseline_arrival_timestep,
                candidate.arrival_tiebreaker,
                candidate.vehicle_id,
            )
        )
        candidate_visits = tuple(candidate_visits_list)

        _verify_right_of_entry_in_candidate_visits(
            node_name=node_name,
            right_of_entry_visit_key=right_of_entry_visit_key,
            candidate_visits=candidate_visits,
        )

        has_unresolved_candidate_passage = any(
            candidate.baseline_passage_timestep is None
            for candidate in candidate_visits
        )
        if has_unresolved_candidate_passage:
            build_status = (
                OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
            )
        else:
            build_status = (
                OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
            )

        node_candidate_set_results.append(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name=node_name,
                build_status=build_status,
                right_of_entry_visit_key=right_of_entry_visit_key,
                right_of_entry_baseline_passage_timestep=p,
                k_confirmed_before=k_confirmed_before,
                candidate_visits=candidate_visits,
            )
        )

    return OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=right_of_entry_selection_result,
        node_candidate_set_results=tuple(node_candidate_set_results),
    )
