"""TVT-MP research aggregation and CSV export (explicit post-evaluation API)."""

from __future__ import annotations

import csv
import os
import tempfile
from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path
from typing import Any

from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitStatus,
    OrderControlTvtMpActualPassageWaitRegistry,
    OrderControlTvtMpIndividualExPostEvaluationResult,
    OrderControlTvtMpIndividualSatisfactionStatus,
    OrderControlTvtMpTradeExPostEvaluationResult,
    OrderControlTvtMpTradeExPostEvaluationStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)

_ROLE_SORT_ORDER = {
    OrderControlTvtMpActualPassageRole.BUYER: 0,
    OrderControlTvtMpActualPassageRole.SELLER: 1,
    OrderControlTvtMpActualPassageRole.NONPARTICIPATING: 2,
}

_CSV_FILENAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)


@dataclass(frozen=True)
class OrderControlTvtMpResearchOutputTransactionRow:
    scenario_name: str
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    buyer_visit_count: int
    seller_visit_count: int
    nonparticipating_visit_count: int
    trade_scope_visit_count: int
    trade_ex_post_evaluation_status: str
    buyer_actual_declared_time_saving_value_total: int | float | None
    seller_actual_required_compensation_total: int | float | None
    buyer_official_payment_total: int | float
    seller_official_compensation_total: int | float
    buyer_reference_payment_total: int | float | None
    seller_reference_compensation_total: int | float | None
    buyer_evaluated_count: int
    buyer_satisfied_count: int
    buyer_unsatisfied_count: int
    buyer_unevaluated_count: int
    seller_evaluated_count: int
    seller_satisfied_count: int
    seller_unsatisfied_count: int
    seller_unevaluated_count: int
    buyer_realized_gain_total: int | float | None
    seller_realized_gain_total: int | float | None
    buyer_actual_observed_count: int
    buyer_actual_unobserved_count: int
    seller_actual_observed_count: int
    seller_actual_unobserved_count: int
    nonparticipating_actual_observed_count: int
    nonparticipating_actual_unobserved_count: int
    nonparticipating_candidate_predictable_count: int
    nonparticipating_candidate_unpredictable_count: int
    nonparticipating_predicted_external_effect_total: int | float | None
    nonparticipating_actual_external_effect_total: int | float | None
    nonparticipating_candidate_minus_actual_total: int | float | None
    rank_difference_evaluated_count: int
    rank_difference_unavailable_count: int
    moved_earlier_count: int
    rank_exact_count: int
    moved_later_count: int
    rank_difference_total: int | float | None


@dataclass(frozen=True)
class OrderControlTvtMpResearchOutputVisitRow:
    scenario_name: str
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    vehicle_name: str
    visit_id: int
    role: str
    actual_observation_status: str
    predicted_observation_status: str
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    actual_passage_timestep: int | None
    baseline_minus_candidate_passage_seconds: int | float | None
    baseline_minus_actual_passage_seconds: int | float | None
    candidate_minus_actual_passage_seconds: int | float | None
    baseline_minus_candidate_time_value: int | float | None
    baseline_minus_actual_time_value: int | float | None
    candidate_minus_actual_time_value: int | float | None
    predicted_route_next_link_name: str
    actual_route_next_link_name: str | None
    formal_route_next_link_name: str | None
    true_vot_per_second: float
    declared_vot_per_second: float | None
    official_payment: int | float | None
    official_compensation: int | float | None
    reference_payment: int | float | None
    reference_compensation: int | float | None
    realized_time_value: int | float | None
    realized_delay_loss: int | float | None
    realized_gain: int | float | None
    satisfaction_status: str | None
    satisfaction_reason: str | None
    assigned_rank: int
    actual_node_passage_rank: int | None
    actual_rank_change: int | None


@dataclass(frozen=True)
class OrderControlTvtMpResearchOutputVehicleRow:
    scenario_name: str
    vehicle_name: str
    trade_scope_visit_count: int
    transaction_count: int
    buyer_count: int
    seller_count: int
    nonparticipating_count: int
    buyer_evaluated_count: int
    buyer_unevaluated_count: int
    seller_evaluated_count: int
    seller_unevaluated_count: int
    buyer_satisfied_count: int
    buyer_unsatisfied_count: int
    seller_satisfied_count: int
    seller_unsatisfied_count: int
    buyer_realized_gain_total: int | float | None
    seller_realized_gain_total: int | float | None
    nonparticipating_predicted_external_effect_total: int | float | None
    nonparticipating_actual_external_effect_total: int | float | None
    nonparticipating_candidate_minus_actual_total: int | float | None
    trade_scope_actual_observed_count: int
    trade_scope_actual_unobserved_count: int
    trade_scope_rank_difference_evaluated_count: int
    trade_scope_rank_difference_unavailable_count: int
    trade_scope_moved_earlier_count: int
    trade_scope_rank_exact_count: int
    trade_scope_moved_later_count: int
    trade_scope_rank_difference_total: int | float | None
    assigned_visit_count: int
    assigned_actual_passed_count: int
    assigned_actual_unpassed_count: int
    assigned_rank_difference_evaluated_count: int
    assigned_rank_difference_unavailable_count: int
    assigned_moved_earlier_count: int
    assigned_rank_exact_count: int
    assigned_moved_later_count: int
    assigned_rank_difference_total: int | float | None


@dataclass(frozen=True)
class OrderControlTvtMpResearchOutputNodeRow:
    scenario_name: str
    node_name: str
    transaction_count: int
    feasible_count: int
    infeasible_count: int
    unavailable_count: int
    buyer_visit_count: int
    seller_visit_count: int
    nonparticipating_visit_count: int
    assigned_visit_count: int
    actual_passed_assigned_visit_count: int
    actual_unpassed_assigned_visit_count: int
    rank_difference_evaluated_count: int
    rank_difference_unavailable_count: int
    moved_earlier_count: int
    rank_exact_count: int
    moved_later_count: int
    rank_difference_total: int | float | None
    buyer_evaluated_count: int
    buyer_unevaluated_count: int
    buyer_satisfied_count: int
    buyer_unsatisfied_count: int
    seller_evaluated_count: int
    seller_unevaluated_count: int
    seller_satisfied_count: int
    seller_unsatisfied_count: int
    buyer_realized_gain_total: int | float | None
    seller_realized_gain_total: int | float | None
    buyer_official_payment_total: int | float
    seller_official_compensation_total: int | float
    buyer_reference_payment_total: int | float | None
    seller_reference_compensation_total: int | float | None
    buyer_actual_observed_count: int
    buyer_actual_unobserved_count: int
    seller_actual_observed_count: int
    seller_actual_unobserved_count: int
    nonparticipating_actual_observed_count: int
    nonparticipating_actual_unobserved_count: int
    nonparticipating_candidate_predictable_count: int
    nonparticipating_candidate_unpredictable_count: int
    nonparticipating_predicted_external_effect_total: int | float | None
    nonparticipating_actual_external_effect_total: int | float | None
    nonparticipating_candidate_minus_actual_total: int | float | None


@dataclass(frozen=True)
class OrderControlTvtMpResearchOutputScenarioRow:
    scenario_name: str
    evaluation_end_timestep: int
    transaction_count: int
    feasible_count: int
    infeasible_count: int
    unavailable_count: int
    buyer_visit_count: int
    seller_visit_count: int
    nonparticipating_visit_count: int
    actual_observed_count: int
    actual_unobserved_count: int
    candidate_predictable_count: int
    candidate_unpredictable_count: int
    buyer_evaluated_count: int
    buyer_unevaluated_count: int
    buyer_satisfied_count: int
    buyer_unsatisfied_count: int
    seller_evaluated_count: int
    seller_unevaluated_count: int
    seller_satisfied_count: int
    seller_unsatisfied_count: int
    buyer_realized_gain_total: int | float | None
    seller_realized_gain_total: int | float | None
    nonparticipating_predicted_external_effect_total: int | float | None
    nonparticipating_actual_external_effect_total: int | float | None
    nonparticipating_candidate_minus_actual_total: int | float | None
    assigned_visit_count: int
    actual_passed_assigned_visit_count: int
    actual_unpassed_assigned_visit_count: int
    rank_difference_evaluated_count: int
    rank_difference_unavailable_count: int
    moved_earlier_count: int
    rank_exact_count: int
    moved_later_count: int
    rank_difference_total: int | float | None


@dataclass(frozen=True)
class OrderControlTvtMpResearchOutputBundle:
    scenario_name: str
    transactions: tuple[OrderControlTvtMpResearchOutputTransactionRow, ...]
    visits: tuple[OrderControlTvtMpResearchOutputVisitRow, ...]
    vehicles: tuple[OrderControlTvtMpResearchOutputVehicleRow, ...]
    nodes: tuple[OrderControlTvtMpResearchOutputNodeRow, ...]
    scenario: tuple[OrderControlTvtMpResearchOutputScenarioRow, ...]


@dataclass(frozen=True)
class _ResearchBuildContext:
    scenario_name: str
    evaluation_end_timestep: int
    wait_registry: OrderControlTvtMpActualPassageWaitRegistry
    history_registry: OrderControlTvtMpActualNodePassageHistoryRegistry
    rank_states_by_node_name: dict[str, OrderControlTvtMpNodeRankState]
    history_by_node_and_visit_key: dict[
        tuple[str, OrderControlTvtVisitKey],
        int,
    ]


def build_tvt_mp_research_output(
    world,
    scenario_name: str,
) -> OrderControlTvtMpResearchOutputBundle:
    context = _validate_and_build_context(world, scenario_name)
    transactions = _build_transaction_rows(context)
    visits = _build_visit_rows(context)
    vehicles = _build_vehicle_rows(context, visits)
    nodes = _build_node_rows(context, transactions, visits)
    scenario_rows = _build_scenario_row(context, transactions, visits, nodes)
    return OrderControlTvtMpResearchOutputBundle(
        scenario_name=context.scenario_name,
        transactions=tuple(transactions),
        visits=tuple(visits),
        vehicles=tuple(vehicles),
        nodes=tuple(nodes),
        scenario=scenario_rows,
    )


def write_tvt_mp_research_output_csv(
    output: OrderControlTvtMpResearchOutputBundle,
    directory: str | os.PathLike[str],
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    directory_path = _resolve_output_directory(directory)
    target_paths = {
        filename: directory_path / filename for filename in _CSV_FILENAMES
    }
    if not overwrite:
        for filename, path in target_paths.items():
            if path.exists():
                raise FileExistsError(
                    f"refusing to overwrite existing CSV {path!s}; "
                    f"set overwrite=True to replace."
                )
    table_specs = (
        (_CSV_FILENAMES[0], output.transactions),
        (_CSV_FILENAMES[1], output.visits),
        (_CSV_FILENAMES[2], output.vehicles),
        (_CSV_FILENAMES[3], output.nodes),
        (_CSV_FILENAMES[4], output.scenario),
    )
    written_paths: dict[str, Path] = {}
    temp_paths: list[Path] = []
    try:
        for filename, rows in table_specs:
            target_path = target_paths[filename]
            temp_path = _write_csv_table_atomic(rows, target_path)
            temp_paths.append(temp_path)
            written_paths[filename] = target_path
    except Exception:
        for temp_path in temp_paths:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
        raise
    return written_paths


def _resolve_output_directory(directory: str | os.PathLike[str]) -> Path:
    directory_path = Path(directory)
    if directory_path.exists():
        if not directory_path.is_dir():
            raise NotADirectoryError(
                f"CSV output directory must be a directory; got file {directory_path!s}."
            )
        return directory_path
    parent = directory_path.parent
    if not parent.exists():
        raise FileNotFoundError(
            f"CSV output directory parent does not exist: {parent!s}."
        )
    directory_path.mkdir(parents=False, exist_ok=True)
    return directory_path


def _write_csv_table_atomic(rows: tuple[Any, ...], target_path: Path) -> Path:
    row_type = type(rows[0]) if rows else None
    if row_type is None:
        raise RuntimeError(
            f"cannot write empty CSV table for {target_path.name}; "
            "scenario table must contain exactly one row."
        )
    field_names = [field.name for field in fields(row_type)]
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(field_names)
            for row in rows:
                writer.writerow(_csv_row_values(row, field_names))
        os.replace(temp_path, target_path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise
    return temp_path


def _csv_row_values(row: Any, field_names: list[str]) -> list[str]:
    values: list[str] = []
    for field_name in field_names:
        value = getattr(row, field_name)
        values.append(_format_csv_cell(field_name, value))
    return values


def _format_csv_cell(field_name: str, value: Any) -> str:
    if value is None:
        return ""
    if field_name == "buyers_sorted":
        return _format_buyers_sorted(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _format_buyers_sorted(
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
) -> str:
    if not buyers_sorted:
        return ""
    parts = []
    for vehicle_name, visit_id in buyers_sorted:
        parts.append(f"{vehicle_name}:{visit_id}")
    return "|".join(parts)


def _validate_and_build_context(
    world,
    scenario_name: str,
) -> _ResearchBuildContext:
    if not isinstance(scenario_name, str) or scenario_name == "":
        raise ValueError(
            "scenario_name must be a non-empty str for TVT-MP research output."
        )
    baseline_collector = getattr(world, "_order_control_baseline_collector", None)
    if baseline_collector is not None:
        raise RuntimeError(
            "TVT-MP research output runs on the real world only; "
            "a baseline fork must not build research output."
        )
    require_timestep = getattr(world, "_require_tvt_evaluation_end_timestep", None)
    if require_timestep is None:
        raise RuntimeError(
            "World is missing _require_tvt_evaluation_end_timestep."
        )
    evaluation_end_timestep = require_timestep()
    if evaluation_end_timestep is None:
        raise ValueError(
            "order_control_tvt_evaluation_end_timestep must be set before "
            "building TVT-MP research output."
        )
    if type(evaluation_end_timestep) is not int:
        raise RuntimeError(
            "order_control_tvt_evaluation_end_timestep must be a Python int; "
            f"got {evaluation_end_timestep!r}."
        )
    if type(world.T) is not int:
        raise RuntimeError(
            f"World.T must be a Python int, not bool; got {world.T!r}."
        )
    expected_timestep = evaluation_end_timestep + 1
    if world.T != expected_timestep:
        raise RuntimeError(
            "TVT-MP research output requires World.T == evaluation_end_timestep + 1; "
            f"got World.T={world.T!r}, "
            f"evaluation_end_timestep={evaluation_end_timestep!r}."
        )
    wait_registry = getattr(
        world,
        "order_control_tvt_mp_actual_passage_wait_registry",
        None,
    )
    if not isinstance(wait_registry, OrderControlTvtMpActualPassageWaitRegistry):
        raise RuntimeError(
            "order_control_tvt_mp_actual_passage_wait_registry must be "
            "OrderControlTvtMpActualPassageWaitRegistry; got type "
            f"{type(wait_registry).__name__}."
        )
    history_registry = getattr(
        world,
        "order_control_tvt_mp_actual_node_passage_history_registry",
        None,
    )
    if not isinstance(
        history_registry,
        OrderControlTvtMpActualNodePassageHistoryRegistry,
    ):
        raise RuntimeError(
            "order_control_tvt_mp_actual_node_passage_history_registry must be "
            "OrderControlTvtMpActualNodePassageHistoryRegistry; got type "
            f"{type(history_registry).__name__}."
        )
    rank_states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(rank_states, dict):
        raise RuntimeError(
            "order_control_tvt_rank_states_by_node_name must be a dict; got type "
            f"{type(rank_states).__name__}."
        )
    for node_name, rank_state in rank_states.items():
        if not isinstance(node_name, str) or node_name == "":
            raise RuntimeError(
                "order_control_tvt_rank_states_by_node_name keys must be "
                f"non-empty str; got {node_name!r}."
            )
        if not isinstance(rank_state, OrderControlTvtNodeRankState):
            raise RuntimeError(
                f"Node {node_name!r}: rank state must be OrderControlTvtNodeRankState; "
                f"got type {type(rank_state).__name__}."
            )
    _require_finalized_timesteps_match(
        wait_registry,
        evaluation_end_timestep,
    )
    history_by_node_and_visit_key = _build_history_rank_lookup(history_registry)
    return _ResearchBuildContext(
        scenario_name=scenario_name,
        evaluation_end_timestep=evaluation_end_timestep,
        wait_registry=wait_registry,
        history_registry=history_registry,
        rank_states_by_node_name=rank_states,
        history_by_node_and_visit_key=history_by_node_and_visit_key,
    )


def _require_finalized_timesteps_match(
    wait_registry: OrderControlTvtMpActualPassageWaitRegistry,
    evaluation_end_timestep: int,
) -> None:
    finalized_fields = (
        (
            "evaluation_end_unobserved_finalized_timestep",
            wait_registry.evaluation_end_unobserved_finalized_timestep,
        ),
        (
            "trade_ex_post_evaluation_finalized_timestep",
            wait_registry.trade_ex_post_evaluation_finalized_timestep,
        ),
        (
            "individual_ex_post_evaluation_finalized_timestep",
            wait_registry.individual_ex_post_evaluation_finalized_timestep,
        ),
    )
    for field_name, finalized in finalized_fields:
        if finalized is None:
            raise RuntimeError(
                f"{field_name} is None; TVT-MP research output requires "
                "evaluation end, unobserved finalization, trade ex-post, and "
                "individual ex-post to be completed."
            )
        if type(finalized) is not int:
            raise RuntimeError(
                f"{field_name} must be a Python int; got {finalized!r}."
            )
        if finalized != evaluation_end_timestep:
            raise RuntimeError(
                f"{field_name} must equal evaluation_end_timestep; got "
                f"{finalized!r}, expected {evaluation_end_timestep!r}."
            )


def _build_history_rank_lookup(
    history_registry: OrderControlTvtMpActualNodePassageHistoryRegistry,
) -> dict[tuple[str, OrderControlTvtVisitKey], int]:
    lookup: dict[tuple[str, OrderControlTvtVisitKey], int] = {}
    for node_name, records in history_registry.records_by_node_name.items():
        for record in records:
            key = (node_name, record.visit_key)
            if key in lookup:
                raise RuntimeError(
                    f"Node {node_name!r}: duplicate node passage history for "
                    f"VisitKey {record.visit_key!r}."
                )
            lookup[key] = record.actual_node_passage_rank
    return lookup


def _sorted_transaction_items(
    wait_registry: OrderControlTvtMpActualPassageWaitRegistry,
) -> list[
    tuple[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        object,
    ]
]:
    transaction_keys = list(wait_registry.trades_by_transaction_key.keys())
    transaction_keys.sort()
    items = []
    for transaction_key in transaction_keys:
        trade_wait = wait_registry.trades_by_transaction_key[transaction_key]
        items.append((transaction_key, trade_wait))
    return items


def _wait_entry_for_trade_visit(
    context: _ResearchBuildContext,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    transaction_key: tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
) -> OrderControlTvtMpActualPassageWaitEntry:
    entry = context.wait_registry.entries_by_node_name_and_visit_key.get(
        (node_name, visit_key)
    )
    if entry is None:
        raise RuntimeError(
            f"transaction {transaction_key!r} on Node {node_name!r} lists "
            f"VisitKey {visit_key!r} but no WaitEntry exists."
        )
    return entry


def _trade_ex_post_result(
    context: _ResearchBuildContext,
    transaction_key: tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
) -> OrderControlTvtMpTradeExPostEvaluationResult:
    result = context.wait_registry.trade_ex_post_evaluation_results_by_transaction_key.get(
        transaction_key
    )
    if result is None:
        raise RuntimeError(
            f"transaction {transaction_key!r} has no trade ex-post evaluation result."
        )
    return result


def _individual_ex_post_result(
    context: _ResearchBuildContext,
    transaction_key: tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
) -> OrderControlTvtMpIndividualExPostEvaluationResult:
    result = (
        context.wait_registry.individual_ex_post_evaluation_results_by_transaction_key.get(
            transaction_key
        )
    )
    if result is None:
        raise RuntimeError(
            f"transaction {transaction_key!r} has no individual ex-post evaluation "
            "result."
        )
    return result


def _sum_optional_numeric(
    values: list[int | float | None],
) -> tuple[int | float | None, int, int]:
    if not values:
        return 0, 0, 0
    observed_count = 0
    missing_count = 0
    total = 0
    for value in values:
        if value is None:
            missing_count = missing_count + 1
        else:
            observed_count = observed_count + 1
            total = total + value
    if observed_count == 0 and missing_count > 0:
        return None, 0, missing_count
    if observed_count == 0:
        return 0, 0, 0
    return total, observed_count, missing_count


def _is_candidate_predictable(
    predicted_status: OrderControlTvtMpCandidatePassageObservationStatus,
) -> bool:
    return (
        predicted_status
        is OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
    )


def _entry_predicted_status(
    entry: OrderControlTvtMpActualPassageWaitEntry,
) -> OrderControlTvtMpCandidatePassageObservationStatus:
    observation = entry.actual_passage_observation_record
    if observation is not None:
        return observation.predicted_observation_status
    return entry.predicted_observation_status


def _entry_actual_observation_status(
    entry: OrderControlTvtMpActualPassageWaitEntry,
) -> OrderControlTvtMpActualPassageObservationStatus:
    observation = entry.actual_passage_observation_record
    if observation is not None:
        return observation.observation_status
    if (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    ):
        return OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
    return OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END


def _count_actual_observation_by_role(
    entries: list[OrderControlTvtMpActualPassageWaitEntry],
    role: OrderControlTvtMpActualPassageRole,
) -> tuple[int, int]:
    observed = 0
    unobserved = 0
    for entry in entries:
        if entry.role is not role:
            continue
        status = _entry_actual_observation_status(entry)
        if status is OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED:
            observed = observed + 1
        else:
            unobserved = unobserved + 1
    return observed, unobserved


def _np_external_effect_values(
    entries: list[OrderControlTvtMpActualPassageWaitEntry],
) -> tuple[
    list[int | float | None],
    list[int | float | None],
    list[int | float | None],
]:
    predicted_values: list[int | float | None] = []
    actual_values: list[int | float | None] = []
    candidate_minus_actual_values: list[int | float | None] = []
    for entry in entries:
        if entry.role is not OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
            continue
        observation = entry.actual_passage_observation_record
        if observation is None:
            predicted_values.append(entry.baseline_minus_candidate_time_value)
            actual_values.append(None)
            candidate_minus_actual_values.append(None)
        else:
            predicted_values.append(observation.baseline_minus_candidate_time_value)
            actual_values.append(observation.baseline_minus_actual_time_value)
            candidate_minus_actual_values.append(
                observation.candidate_minus_actual_time_value
            )
    return predicted_values, actual_values, candidate_minus_actual_values


def _np_candidate_predictability_counts(
    entries: list[OrderControlTvtMpActualPassageWaitEntry],
) -> tuple[int, int]:
    predictable = 0
    unpredictable = 0
    for entry in entries:
        if entry.role is not OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
            continue
        if _is_candidate_predictable(_entry_predicted_status(entry)):
            predictable = predictable + 1
        else:
            unpredictable = unpredictable + 1
    return predictable, unpredictable


def _rank_difference_stats_for_visit_keys(
    context: _ResearchBuildContext,
    node_name: str,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
    *,
    require_assigned_rank: bool,
) -> dict[str, int | float | None]:
    evaluated_count = 0
    unavailable_count = 0
    moved_earlier = 0
    rank_exact = 0
    moved_later = 0
    change_values: list[int | float | None] = []
    rank_state = context.rank_states_by_node_name.get(node_name)
    if rank_state is None and visit_keys:
        raise RuntimeError(
            f"Node {node_name!r} has assigned VisitKeys but no rank state entry."
        )
    for visit_key in visit_keys:
        assigned_rank = None
        if rank_state is not None:
            assigned_rank = rank_state.assigned_rank(visit_key)
        if assigned_rank is None:
            if require_assigned_rank:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {visit_key!r} has no assigned rank "
                    "on the rank ledger."
                )
            unavailable_count = unavailable_count + 1
            change_values.append(None)
            continue
        actual_rank = context.history_by_node_and_visit_key.get(
            (node_name, visit_key)
        )
        if actual_rank is None:
            unavailable_count = unavailable_count + 1
            change_values.append(None)
            continue
        change = assigned_rank - actual_rank
        evaluated_count = evaluated_count + 1
        change_values.append(change)
        if change > 0:
            moved_earlier = moved_earlier + 1
        elif change == 0:
            rank_exact = rank_exact + 1
        else:
            moved_later = moved_later + 1
    total, _observed, _missing = _sum_optional_numeric(change_values)
    if not visit_keys:
        total = 0
    return {
        "rank_difference_evaluated_count": evaluated_count,
        "rank_difference_unavailable_count": unavailable_count,
        "moved_earlier_count": moved_earlier,
        "rank_exact_count": rank_exact,
        "moved_later_count": moved_later,
        "rank_difference_total": total,
    }


def _buyer_official_payment_total_for_trade(
    trade_entries: list[OrderControlTvtMpActualPassageWaitEntry],
    individual_result: OrderControlTvtMpIndividualExPostEvaluationResult,
) -> int | float:
    buyer_entries = [
        entry
        for entry in trade_entries
        if entry.role is OrderControlTvtMpActualPassageRole.BUYER
    ]
    if not buyer_entries:
        return 0
    status = individual_result.trade_ex_post_evaluation_status
    if status is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE:
        total = 0
        for entry in buyer_entries:
            monetary = entry.monetary_frozen_input
            if monetary is None:
                raise RuntimeError(
                    f"Node {entry.node_name!r}: buyer VisitKey {entry.visit_key!r} "
                    "is missing monetary_frozen_input."
                )
            total = total + monetary.payment_paid_in_this_transaction
        return total
    records = individual_result.buyer_evaluation_records
    if records is None:
        raise RuntimeError(
            f"transaction on Node {buyer_entries[0].node_name!r} has evaluated "
            "trade status but buyer_evaluation_records is None."
        )
    total = 0
    for record in records:
        total = total + record.official_payment
    return total


def _seller_official_compensation_total_for_trade(
    trade_entries: list[OrderControlTvtMpActualPassageWaitEntry],
    individual_result: OrderControlTvtMpIndividualExPostEvaluationResult,
) -> int | float:
    seller_entries = [
        entry
        for entry in trade_entries
        if entry.role is OrderControlTvtMpActualPassageRole.SELLER
    ]
    if not seller_entries:
        return 0
    status = individual_result.trade_ex_post_evaluation_status
    if status is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE:
        total = 0
        for entry in seller_entries:
            monetary = entry.monetary_frozen_input
            if monetary is None:
                raise RuntimeError(
                    f"Node {entry.node_name!r}: seller VisitKey {entry.visit_key!r} "
                    "is missing monetary_frozen_input."
                )
            total = total + monetary.payment_received_in_this_transaction
        return total
    records = individual_result.seller_evaluation_records
    if records is None:
        raise RuntimeError(
            f"transaction on Node {seller_entries[0].node_name!r} has evaluated "
            "trade status but seller_evaluation_records is None."
        )
    total = 0
    for record in records:
        total = total + record.official_compensation
    return total


def _reference_payment_total_for_trade(
    trade_result: OrderControlTvtMpTradeExPostEvaluationResult,
    trade_entries: list[OrderControlTvtMpActualPassageWaitEntry],
) -> int | float | None:
    buyer_count = len(
        [
            entry
            for entry in trade_entries
            if entry.role is OrderControlTvtMpActualPassageRole.BUYER
        ]
    )
    if buyer_count == 0:
        return 0
    if (
        trade_result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    ):
        return None
    records = trade_result.buyer_reference_payment_records
    if records is None:
        raise RuntimeError(
            "evaluated trade ex-post result has buyer_reference_payment_records None."
        )
    total = 0
    for record in records:
        total = total + record.reference_payment
    return total


def _reference_compensation_total_for_trade(
    trade_result: OrderControlTvtMpTradeExPostEvaluationResult,
    trade_entries: list[OrderControlTvtMpActualPassageWaitEntry],
) -> int | float | None:
    seller_count = len(
        [
            entry
            for entry in trade_entries
            if entry.role is OrderControlTvtMpActualPassageRole.SELLER
        ]
    )
    if seller_count == 0:
        return 0
    if (
        trade_result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    ):
        return None
    records = trade_result.seller_reference_compensation_records
    if records is None:
        raise RuntimeError(
            "evaluated trade ex-post result has seller_reference_compensation_records "
            "None."
        )
    total = 0
    for record in records:
        total = total + record.reference_compensation
    return total


def _role_evaluation_counts(
    individual_result: OrderControlTvtMpIndividualExPostEvaluationResult,
    *,
    role: OrderControlTvtMpActualPassageRole,
    role_visit_count: int,
) -> tuple[int, int, int, int]:
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        records = individual_result.buyer_evaluation_records
    elif role is OrderControlTvtMpActualPassageRole.SELLER:
        records = individual_result.seller_evaluation_records
    else:
        return 0, 0, 0, 0
    if (
        individual_result.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    ):
        return 0, 0, 0, role_visit_count
    if records is None:
        raise RuntimeError(
            f"individual ex-post result on Node {individual_result.node_name!r} "
            f"has status {individual_result.trade_ex_post_evaluation_status!r} "
            f"but {role.value} evaluation records are None."
        )
    evaluated = len(records)
    satisfied = 0
    unsatisfied = 0
    for record in records:
        if (
            record.satisfaction_status
            is OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
        ):
            satisfied = satisfied + 1
        else:
            unsatisfied = unsatisfied + 1
    unevaluated = role_visit_count - evaluated
    if unevaluated < 0:
        unevaluated = 0
    return evaluated, satisfied, unsatisfied, unevaluated


def _realized_gain_total_for_role(
    individual_result: OrderControlTvtMpIndividualExPostEvaluationResult,
    *,
    role: OrderControlTvtMpActualPassageRole,
    role_visit_count: int,
) -> int | float | None:
    if role_visit_count == 0:
        return 0
    if (
        individual_result.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    ):
        return None
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        records = individual_result.buyer_evaluation_records
    else:
        records = individual_result.seller_evaluation_records
    if records is None:
        raise RuntimeError(
            f"individual ex-post result on Node {individual_result.node_name!r} "
            "has evaluated status but role records are None."
        )
    values = [record.realized_gain for record in records]
    total, _observed, _missing = _sum_optional_numeric(values)
    return total


def _build_transaction_rows(
    context: _ResearchBuildContext,
) -> list[OrderControlTvtMpResearchOutputTransactionRow]:
    rows: list[OrderControlTvtMpResearchOutputTransactionRow] = []
    for transaction_key, trade_wait in _sorted_transaction_items(context.wait_registry):
        node_name = trade_wait.node_name
        trade_entries = []
        for visit_key in trade_wait.all_visit_keys:
            trade_entries.append(
                _wait_entry_for_trade_visit(
                    context,
                    node_name,
                    visit_key,
                    transaction_key,
                )
            )
        trade_result = _trade_ex_post_result(context, transaction_key)
        individual_result = _individual_ex_post_result(context, transaction_key)
        buyer_evaluated, buyer_satisfied, buyer_unsatisfied, buyer_unevaluated = (
            _role_evaluation_counts(
                individual_result,
                role=OrderControlTvtMpActualPassageRole.BUYER,
                role_visit_count=len(trade_wait.buyer_visit_keys),
            )
        )
        seller_evaluated, seller_satisfied, seller_unsatisfied, seller_unevaluated = (
            _role_evaluation_counts(
                individual_result,
                role=OrderControlTvtMpActualPassageRole.SELLER,
                role_visit_count=len(trade_wait.seller_visit_keys),
            )
        )
        buyer_observed, buyer_unobserved = _count_actual_observation_by_role(
            trade_entries,
            OrderControlTvtMpActualPassageRole.BUYER,
        )
        seller_observed, seller_unobserved = _count_actual_observation_by_role(
            trade_entries,
            OrderControlTvtMpActualPassageRole.SELLER,
        )
        np_observed, np_unobserved = _count_actual_observation_by_role(
            trade_entries,
            OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        )
        np_predictable, np_unpredictable = _np_candidate_predictability_counts(
            trade_entries
        )
        predicted_values, actual_values, candidate_minus_values = (
            _np_external_effect_values(trade_entries)
        )
        np_predicted_total, _, _ = _sum_optional_numeric(predicted_values)
        if len(trade_wait.nonparticipating_visit_keys) == 0:
            np_predicted_total = 0
            np_actual_total = 0
            np_candidate_minus_total = 0
        else:
            np_actual_total, _, _ = _sum_optional_numeric(actual_values)
            np_candidate_minus_total, _, _ = _sum_optional_numeric(
                candidate_minus_values
            )
        rank_stats = _rank_difference_stats_for_visit_keys(
            context,
            node_name,
            trade_wait.all_visit_keys,
            require_assigned_rank=True,
        )
        rows.append(
            OrderControlTvtMpResearchOutputTransactionRow(
                scenario_name=context.scenario_name,
                tvt_decision_timestep=trade_wait.tvt_decision_timestep,
                node_name=node_name,
                buyers_sorted=trade_wait.buyers_sorted,
                buyer_visit_count=len(trade_wait.buyer_visit_keys),
                seller_visit_count=len(trade_wait.seller_visit_keys),
                nonparticipating_visit_count=len(
                    trade_wait.nonparticipating_visit_keys
                ),
                trade_scope_visit_count=len(trade_wait.all_visit_keys),
                trade_ex_post_evaluation_status=(
                    trade_result.ex_post_evaluation_status.value
                ),
                buyer_actual_declared_time_saving_value_total=(
                    trade_result.buyer_actual_declared_time_saving_value_total
                ),
                seller_actual_required_compensation_total=(
                    trade_result.seller_actual_required_compensation_total
                ),
                buyer_official_payment_total=_buyer_official_payment_total_for_trade(
                    trade_entries,
                    individual_result,
                ),
                seller_official_compensation_total=(
                    _seller_official_compensation_total_for_trade(
                        trade_entries,
                        individual_result,
                    )
                ),
                buyer_reference_payment_total=_reference_payment_total_for_trade(
                    trade_result,
                    trade_entries,
                ),
                seller_reference_compensation_total=(
                    _reference_compensation_total_for_trade(
                        trade_result,
                        trade_entries,
                    )
                ),
                buyer_evaluated_count=buyer_evaluated,
                buyer_satisfied_count=buyer_satisfied,
                buyer_unsatisfied_count=buyer_unsatisfied,
                buyer_unevaluated_count=buyer_unevaluated,
                seller_evaluated_count=seller_evaluated,
                seller_satisfied_count=seller_satisfied,
                seller_unsatisfied_count=seller_unsatisfied,
                seller_unevaluated_count=seller_unevaluated,
                buyer_realized_gain_total=_realized_gain_total_for_role(
                    individual_result,
                    role=OrderControlTvtMpActualPassageRole.BUYER,
                    role_visit_count=len(trade_wait.buyer_visit_keys),
                ),
                seller_realized_gain_total=_realized_gain_total_for_role(
                    individual_result,
                    role=OrderControlTvtMpActualPassageRole.SELLER,
                    role_visit_count=len(trade_wait.seller_visit_keys),
                ),
                buyer_actual_observed_count=buyer_observed,
                buyer_actual_unobserved_count=buyer_unobserved,
                seller_actual_observed_count=seller_observed,
                seller_actual_unobserved_count=seller_unobserved,
                nonparticipating_actual_observed_count=np_observed,
                nonparticipating_actual_unobserved_count=np_unobserved,
                nonparticipating_candidate_predictable_count=np_predictable,
                nonparticipating_candidate_unpredictable_count=np_unpredictable,
                nonparticipating_predicted_external_effect_total=np_predicted_total,
                nonparticipating_actual_external_effect_total=np_actual_total,
                nonparticipating_candidate_minus_actual_total=np_candidate_minus_total,
                rank_difference_evaluated_count=rank_stats[
                    "rank_difference_evaluated_count"
                ],
                rank_difference_unavailable_count=rank_stats[
                    "rank_difference_unavailable_count"
                ],
                moved_earlier_count=rank_stats["moved_earlier_count"],
                rank_exact_count=rank_stats["rank_exact_count"],
                moved_later_count=rank_stats["moved_later_count"],
                rank_difference_total=rank_stats["rank_difference_total"],
            )
        )
    return rows


def _sort_trade_scope_entries(
    trade_entries: list[OrderControlTvtMpActualPassageWaitEntry],
) -> list[OrderControlTvtMpActualPassageWaitEntry]:
    sorted_entries = list(trade_entries)
    sorted_entries.sort(
        key=lambda entry: (
            _ROLE_SORT_ORDER[entry.role],
            entry.visit_key[1],
            entry.visit_key[0],
        )
    )
    return sorted_entries


def _buyer_individual_by_visit_key(
    individual_result: OrderControlTvtMpIndividualExPostEvaluationResult,
) -> dict[OrderControlTvtVisitKey, object]:
    mapping = {}
    records = individual_result.buyer_evaluation_records
    if records is None:
        return mapping
    for record in records:
        mapping[record.visit_key] = record
    return mapping


def _seller_individual_by_visit_key(
    individual_result: OrderControlTvtMpIndividualExPostEvaluationResult,
) -> dict[OrderControlTvtVisitKey, object]:
    mapping = {}
    records = individual_result.seller_evaluation_records
    if records is None:
        return mapping
    for record in records:
        mapping[record.visit_key] = record
    return mapping


def _buyer_reference_by_visit_key(
    trade_result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> dict[OrderControlTvtVisitKey, int | float]:
    mapping: dict[OrderControlTvtVisitKey, int | float] = {}
    records = trade_result.buyer_reference_payment_records
    if records is None:
        return mapping
    for record in records:
        mapping[record.visit_key] = record.reference_payment
    return mapping


def _seller_reference_by_visit_key(
    trade_result: OrderControlTvtMpTradeExPostEvaluationResult,
) -> dict[OrderControlTvtVisitKey, int | float]:
    mapping: dict[OrderControlTvtVisitKey, int | float] = {}
    records = trade_result.seller_reference_compensation_records
    if records is None:
        return mapping
    for record in records:
        mapping[record.visit_key] = record.reference_compensation
    return mapping


def _observation_fields_for_visit_row(
    entry: OrderControlTvtMpActualPassageWaitEntry,
) -> dict[str, Any]:
    observation = entry.actual_passage_observation_record
    if observation is None:
        raise RuntimeError(
            f"Node {entry.node_name!r}: WaitEntry VisitKey {entry.visit_key!r} "
            "has no actual_passage_observation_record after evaluation end."
        )
    return {
        "actual_observation_status": observation.observation_status.value,
        "predicted_observation_status": observation.predicted_observation_status.value,
        "baseline_passage_timestep": observation.baseline_passage_timestep,
        "candidate_passage_timestep": observation.candidate_passage_timestep,
        "actual_passage_timestep": observation.actual_passage_timestep,
        "baseline_minus_candidate_passage_seconds": (
            observation.baseline_minus_candidate_passage_seconds
        ),
        "baseline_minus_actual_passage_seconds": (
            observation.baseline_minus_actual_passage_seconds
        ),
        "candidate_minus_actual_passage_seconds": (
            observation.candidate_minus_actual_passage_seconds
        ),
        "baseline_minus_candidate_time_value": (
            observation.baseline_minus_candidate_time_value
        ),
        "baseline_minus_actual_time_value": observation.baseline_minus_actual_time_value,
        "candidate_minus_actual_time_value": (
            observation.candidate_minus_actual_time_value
        ),
        "predicted_route_next_link_name": observation.predicted_route_next_link_name,
        "actual_route_next_link_name": observation.actual_route_next_link_name,
        "true_vot_per_second": observation.true_vot_per_second,
    }


def _build_visit_rows(
    context: _ResearchBuildContext,
) -> list[OrderControlTvtMpResearchOutputVisitRow]:
    rows: list[OrderControlTvtMpResearchOutputVisitRow] = []
    for transaction_key, trade_wait in _sorted_transaction_items(context.wait_registry):
        node_name = trade_wait.node_name
        rank_state = context.rank_states_by_node_name.get(node_name)
        if rank_state is None:
            raise RuntimeError(
                f"Node {node_name!r} has TradeWait entries but no rank state."
            )
        trade_result = _trade_ex_post_result(context, transaction_key)
        individual_result = _individual_ex_post_result(context, transaction_key)
        buyer_individual = _buyer_individual_by_visit_key(individual_result)
        seller_individual = _seller_individual_by_visit_key(individual_result)
        buyer_reference = _buyer_reference_by_visit_key(trade_result)
        seller_reference = _seller_reference_by_visit_key(trade_result)
        trade_entries = []
        for visit_key in trade_wait.all_visit_keys:
            trade_entries.append(
                _wait_entry_for_trade_visit(
                    context,
                    node_name,
                    visit_key,
                    transaction_key,
                )
            )
        for entry in _sort_trade_scope_entries(trade_entries):
            observation_fields = _observation_fields_for_visit_row(entry)
            assigned_rank = rank_state.assigned_rank(entry.visit_key)
            if assigned_rank is None:
                raise RuntimeError(
                    f"Node {node_name!r}: trade-scope VisitKey {entry.visit_key!r} "
                    "has no assigned rank on the rank ledger."
                )
            actual_rank = context.history_by_node_and_visit_key.get(
                (node_name, entry.visit_key)
            )
            if actual_rank is None:
                actual_rank_change = None
            else:
                actual_rank_change = assigned_rank - actual_rank
            formal_route = rank_state.formal_route_next_link_name(entry.visit_key)
            declared_vot = None
            official_payment = None
            official_compensation = None
            if entry.role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
                declared_vot = None
            else:
                monetary = entry.monetary_frozen_input
                if monetary is None:
                    raise RuntimeError(
                        f"Node {node_name!r}: {entry.role.value} VisitKey "
                        f"{entry.visit_key!r} is missing monetary_frozen_input."
                    )
                declared_vot = monetary.declared_vot_per_second
            reference_payment = None
            reference_compensation = None
            realized_time_value = None
            realized_delay_loss = None
            realized_gain = None
            satisfaction_status = None
            satisfaction_reason = None
            if entry.role is OrderControlTvtMpActualPassageRole.BUYER:
                official_payment = entry.monetary_frozen_input.payment_paid_in_this_transaction
                buyer_record = buyer_individual.get(entry.visit_key)
                if buyer_record is not None:
                    official_payment = buyer_record.official_payment
                    realized_time_value = buyer_record.realized_time_value
                    realized_gain = buyer_record.realized_gain
                    satisfaction_status = buyer_record.satisfaction_status.value
                    satisfaction_reason = buyer_record.satisfaction_reason.value
                if (
                    trade_result.ex_post_evaluation_status
                    is not OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
                ):
                    reference_payment = buyer_reference.get(entry.visit_key)
            elif entry.role is OrderControlTvtMpActualPassageRole.SELLER:
                official_compensation = (
                    entry.monetary_frozen_input.payment_received_in_this_transaction
                )
                seller_record = seller_individual.get(entry.visit_key)
                if seller_record is not None:
                    official_compensation = seller_record.official_compensation
                    realized_delay_loss = seller_record.realized_delay_loss
                    realized_gain = seller_record.realized_gain
                    satisfaction_status = seller_record.satisfaction_status.value
                    satisfaction_reason = seller_record.satisfaction_reason.value
                if (
                    trade_result.ex_post_evaluation_status
                    is not OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
                ):
                    reference_compensation = seller_reference.get(entry.visit_key)
            rows.append(
                OrderControlTvtMpResearchOutputVisitRow(
                    scenario_name=context.scenario_name,
                    tvt_decision_timestep=entry.tvt_decision_timestep,
                    node_name=entry.node_name,
                    buyers_sorted=entry.buyers_sorted,
                    vehicle_name=entry.visit_key[0],
                    visit_id=entry.visit_key[1],
                    role=entry.role.value,
                    actual_observation_status=observation_fields[
                        "actual_observation_status"
                    ],
                    predicted_observation_status=observation_fields[
                        "predicted_observation_status"
                    ],
                    baseline_passage_timestep=observation_fields[
                        "baseline_passage_timestep"
                    ],
                    candidate_passage_timestep=observation_fields[
                        "candidate_passage_timestep"
                    ],
                    actual_passage_timestep=observation_fields["actual_passage_timestep"],
                    baseline_minus_candidate_passage_seconds=observation_fields[
                        "baseline_minus_candidate_passage_seconds"
                    ],
                    baseline_minus_actual_passage_seconds=observation_fields[
                        "baseline_minus_actual_passage_seconds"
                    ],
                    candidate_minus_actual_passage_seconds=observation_fields[
                        "candidate_minus_actual_passage_seconds"
                    ],
                    baseline_minus_candidate_time_value=observation_fields[
                        "baseline_minus_candidate_time_value"
                    ],
                    baseline_minus_actual_time_value=observation_fields[
                        "baseline_minus_actual_time_value"
                    ],
                    candidate_minus_actual_time_value=observation_fields[
                        "candidate_minus_actual_time_value"
                    ],
                    predicted_route_next_link_name=observation_fields[
                        "predicted_route_next_link_name"
                    ],
                    actual_route_next_link_name=observation_fields[
                        "actual_route_next_link_name"
                    ],
                    formal_route_next_link_name=formal_route,
                    true_vot_per_second=observation_fields["true_vot_per_second"],
                    declared_vot_per_second=declared_vot,
                    official_payment=official_payment,
                    official_compensation=official_compensation,
                    reference_payment=reference_payment,
                    reference_compensation=reference_compensation,
                    realized_time_value=realized_time_value,
                    realized_delay_loss=realized_delay_loss,
                    realized_gain=realized_gain,
                    satisfaction_status=satisfaction_status,
                    satisfaction_reason=satisfaction_reason,
                    assigned_rank=assigned_rank,
                    actual_node_passage_rank=actual_rank,
                    actual_rank_change=actual_rank_change,
                )
            )
    return rows


def _aggregate_visit_rows_for_vehicle(
    visit_rows: list[OrderControlTvtMpResearchOutputVisitRow],
) -> dict[str, list[OrderControlTvtMpResearchOutputVisitRow]]:
    by_vehicle: dict[str, list[OrderControlTvtMpResearchOutputVisitRow]] = {}
    for row in visit_rows:
        by_vehicle.setdefault(row.vehicle_name, []).append(row)
    return by_vehicle


def _distinct_transaction_count_for_vehicle(
    visit_rows: list[OrderControlTvtMpResearchOutputVisitRow],
) -> int:
    identities = set()
    for row in visit_rows:
        identities.add(
            (row.tvt_decision_timestep, row.node_name, row.buyers_sorted)
        )
    return len(identities)


def _assigned_visit_keys_for_vehicle(
    context: _ResearchBuildContext,
    vehicle_name: str,
) -> list[tuple[str, OrderControlTvtVisitKey]]:
    assigned: list[tuple[str, OrderControlTvtVisitKey]] = []
    for node_name, rank_state in context.rank_states_by_node_name.items():
        for visit_key in rank_state.confirmed_visit_keys_in_order():
            if visit_key[0] == vehicle_name:
                assigned.append((node_name, visit_key))
    assigned.sort(key=lambda item: (item[0], item[1][1], item[1][0]))
    return assigned


def _build_vehicle_rows(
    context: _ResearchBuildContext,
    visits: list[OrderControlTvtMpResearchOutputVisitRow],
) -> list[OrderControlTvtMpResearchOutputVehicleRow]:
    visits_by_vehicle = _aggregate_visit_rows_for_vehicle(visits)
    vehicle_names = set(visits_by_vehicle.keys())
    for node_name, rank_state in context.rank_states_by_node_name.items():
        for visit_key in rank_state.confirmed_visit_keys_in_order():
            vehicle_names.add(visit_key[0])
    sorted_vehicle_names = sorted(vehicle_names)
    rows: list[OrderControlTvtMpResearchOutputVehicleRow] = []
    for vehicle_name in sorted_vehicle_names:
        vehicle_visit_rows = visits_by_vehicle.get(vehicle_name, [])
        buyer_count = 0
        seller_count = 0
        nonparticipating_count = 0
        buyer_evaluated = 0
        buyer_unevaluated = 0
        seller_evaluated = 0
        seller_unevaluated = 0
        buyer_satisfied = 0
        buyer_unsatisfied = 0
        seller_satisfied = 0
        seller_unsatisfied = 0
        buyer_gain_values: list[int | float | None] = []
        seller_gain_values: list[int | float | None] = []
        np_predicted_values: list[int | float | None] = []
        np_actual_values: list[int | float | None] = []
        np_candidate_minus_values: list[int | float | None] = []
        trade_scope_observed = 0
        trade_scope_unobserved = 0
        trade_scope_rank_changes: list[int | float | None] = []
        for row in vehicle_visit_rows:
            if row.role == OrderControlTvtMpActualPassageRole.BUYER.value:
                buyer_count = buyer_count + 1
            elif row.role == OrderControlTvtMpActualPassageRole.SELLER.value:
                seller_count = seller_count + 1
            else:
                nonparticipating_count = nonparticipating_count + 1
            if row.role == OrderControlTvtMpActualPassageRole.BUYER.value:
                if row.realized_gain is None:
                    buyer_unevaluated = buyer_unevaluated + 1
                else:
                    buyer_evaluated = buyer_evaluated + 1
                    buyer_gain_values.append(row.realized_gain)
                    if row.satisfaction_status == "satisfied":
                        buyer_satisfied = buyer_satisfied + 1
                    else:
                        buyer_unsatisfied = buyer_unsatisfied + 1
            if row.role == OrderControlTvtMpActualPassageRole.SELLER.value:
                if row.realized_gain is None:
                    seller_unevaluated = seller_unevaluated + 1
                else:
                    seller_evaluated = seller_evaluated + 1
                    seller_gain_values.append(row.realized_gain)
                    if row.satisfaction_status == "satisfied":
                        seller_satisfied = seller_satisfied + 1
                    else:
                        seller_unsatisfied = seller_unsatisfied + 1
            if (
                row.role
                == OrderControlTvtMpActualPassageRole.NONPARTICIPATING.value
            ):
                np_predicted_values.append(row.baseline_minus_candidate_time_value)
                np_actual_values.append(row.baseline_minus_actual_time_value)
                np_candidate_minus_values.append(row.candidate_minus_actual_time_value)
            if (
                row.actual_observation_status
                == OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED.value
            ):
                trade_scope_observed = trade_scope_observed + 1
            else:
                trade_scope_unobserved = trade_scope_unobserved + 1
            trade_scope_rank_changes.append(row.actual_rank_change)
        if buyer_count == 0:
            buyer_gain_total = 0
        elif not buyer_gain_values:
            buyer_gain_total = None
        else:
            buyer_gain_total, _, _ = _sum_optional_numeric(buyer_gain_values)
        if seller_count == 0:
            seller_gain_total = 0
        elif not seller_gain_values:
            seller_gain_total = None
        else:
            seller_gain_total, _, _ = _sum_optional_numeric(seller_gain_values)
        np_predicted_total, _, _ = _sum_optional_numeric(np_predicted_values)
        if nonparticipating_count == 0:
            np_predicted_total = 0
            np_actual_total = 0
            np_candidate_minus_total = 0
        else:
            np_actual_total, _, _ = _sum_optional_numeric(np_actual_values)
            np_candidate_minus_total, _, _ = _sum_optional_numeric(
                np_candidate_minus_values
            )
        trade_scope_rank_stats = _rank_stats_from_change_values(
            trade_scope_rank_changes
        )
        assigned_keys = _assigned_visit_keys_for_vehicle(context, vehicle_name)
        assigned_rank_changes: list[int | float | None] = []
        assigned_passed = 0
        assigned_unpassed = 0
        for node_name, visit_key in assigned_keys:
            rank_state = context.rank_states_by_node_name[node_name]
            assigned_rank = rank_state.assigned_rank(visit_key)
            if assigned_rank is None:
                raise RuntimeError(
                    f"Node {node_name!r}: assigned VisitKey {visit_key!r} "
                    "has no assigned rank."
                )
            actual_rank = context.history_by_node_and_visit_key.get(
                (node_name, visit_key)
            )
            if actual_rank is None:
                assigned_unpassed = assigned_unpassed + 1
                assigned_rank_changes.append(None)
            else:
                assigned_passed = assigned_passed + 1
                assigned_rank_changes.append(assigned_rank - actual_rank)
        assigned_rank_stats = _rank_stats_from_change_values(assigned_rank_changes)
        rows.append(
            OrderControlTvtMpResearchOutputVehicleRow(
                scenario_name=context.scenario_name,
                vehicle_name=vehicle_name,
                trade_scope_visit_count=len(vehicle_visit_rows),
                transaction_count=_distinct_transaction_count_for_vehicle(
                    vehicle_visit_rows
                ),
                buyer_count=buyer_count,
                seller_count=seller_count,
                nonparticipating_count=nonparticipating_count,
                buyer_evaluated_count=buyer_evaluated,
                buyer_unevaluated_count=buyer_unevaluated,
                seller_evaluated_count=seller_evaluated,
                seller_unevaluated_count=seller_unevaluated,
                buyer_satisfied_count=buyer_satisfied,
                buyer_unsatisfied_count=buyer_unsatisfied,
                seller_satisfied_count=seller_satisfied,
                seller_unsatisfied_count=seller_unsatisfied,
                buyer_realized_gain_total=buyer_gain_total,
                seller_realized_gain_total=seller_gain_total,
                nonparticipating_predicted_external_effect_total=np_predicted_total,
                nonparticipating_actual_external_effect_total=np_actual_total,
                nonparticipating_candidate_minus_actual_total=np_candidate_minus_total,
                trade_scope_actual_observed_count=trade_scope_observed,
                trade_scope_actual_unobserved_count=trade_scope_unobserved,
                trade_scope_rank_difference_evaluated_count=trade_scope_rank_stats[
                    "rank_difference_evaluated_count"
                ],
                trade_scope_rank_difference_unavailable_count=trade_scope_rank_stats[
                    "rank_difference_unavailable_count"
                ],
                trade_scope_moved_earlier_count=trade_scope_rank_stats[
                    "moved_earlier_count"
                ],
                trade_scope_rank_exact_count=trade_scope_rank_stats["rank_exact_count"],
                trade_scope_moved_later_count=trade_scope_rank_stats["moved_later_count"],
                trade_scope_rank_difference_total=trade_scope_rank_stats[
                    "rank_difference_total"
                ],
                assigned_visit_count=len(assigned_keys),
                assigned_actual_passed_count=assigned_passed,
                assigned_actual_unpassed_count=assigned_unpassed,
                assigned_rank_difference_evaluated_count=assigned_rank_stats[
                    "rank_difference_evaluated_count"
                ],
                assigned_rank_difference_unavailable_count=assigned_rank_stats[
                    "rank_difference_unavailable_count"
                ],
                assigned_moved_earlier_count=assigned_rank_stats["moved_earlier_count"],
                assigned_rank_exact_count=assigned_rank_stats["rank_exact_count"],
                assigned_moved_later_count=assigned_rank_stats["moved_later_count"],
                assigned_rank_difference_total=assigned_rank_stats[
                    "rank_difference_total"
                ],
            )
        )
    return rows


def _rank_stats_from_change_values(
    change_values: list[int | float | None],
) -> dict[str, int | float | None]:
    evaluated_count = 0
    unavailable_count = 0
    moved_earlier = 0
    rank_exact = 0
    moved_later = 0
    for change in change_values:
        if change is None:
            unavailable_count = unavailable_count + 1
            continue
        evaluated_count = evaluated_count + 1
        if change > 0:
            moved_earlier = moved_earlier + 1
        elif change == 0:
            rank_exact = rank_exact + 1
        else:
            moved_later = moved_later + 1
    total, _, _ = _sum_optional_numeric(change_values)
    if not change_values:
        total = 0
    return {
        "rank_difference_evaluated_count": evaluated_count,
        "rank_difference_unavailable_count": unavailable_count,
        "moved_earlier_count": moved_earlier,
        "rank_exact_count": rank_exact,
        "moved_later_count": moved_later,
        "rank_difference_total": total,
    }


def _entries_for_node(
    context: _ResearchBuildContext,
    node_name: str,
) -> list[OrderControlTvtMpActualPassageWaitEntry]:
    entries = []
    for (entry_node_name, _visit_key), entry in (
        context.wait_registry.entries_by_node_name_and_visit_key.items()
    ):
        if entry_node_name == node_name:
            entries.append(entry)
    return entries


def _build_node_rows(
    context: _ResearchBuildContext,
    transactions: list[OrderControlTvtMpResearchOutputTransactionRow],
    visits: list[OrderControlTvtMpResearchOutputVisitRow],
) -> list[OrderControlTvtMpResearchOutputNodeRow]:
    node_names = sorted(context.rank_states_by_node_name.keys())
    transactions_by_node: dict[str, list[OrderControlTvtMpResearchOutputTransactionRow]] = {}
    for row in transactions:
        transactions_by_node.setdefault(row.node_name, []).append(row)
    visits_by_node: dict[str, list[OrderControlTvtMpResearchOutputVisitRow]] = {}
    for row in visits:
        visits_by_node.setdefault(row.node_name, []).append(row)
    rows: list[OrderControlTvtMpResearchOutputNodeRow] = []
    for node_name in node_names:
        node_transactions = transactions_by_node.get(node_name, [])
        node_visits = visits_by_node.get(node_name, [])
        feasible = 0
        infeasible = 0
        unavailable = 0
        for transaction_row in node_transactions:
            status = transaction_row.trade_ex_post_evaluation_status
            if status == OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE.value:
                feasible = feasible + 1
            elif (
                status
                == OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE.value
            ):
                infeasible = infeasible + 1
            else:
                unavailable = unavailable + 1
        buyer_visit_count = 0
        seller_visit_count = 0
        nonparticipating_visit_count = 0
        for visit_row in node_visits:
            if visit_row.role == OrderControlTvtMpActualPassageRole.BUYER.value:
                buyer_visit_count = buyer_visit_count + 1
            elif visit_row.role == OrderControlTvtMpActualPassageRole.SELLER.value:
                seller_visit_count = seller_visit_count + 1
            else:
                nonparticipating_visit_count = nonparticipating_visit_count + 1
        rank_state = context.rank_states_by_node_name[node_name]
        assigned_visit_keys = rank_state.confirmed_visit_keys_in_order()
        rank_stats = _rank_difference_stats_for_visit_keys(
            context,
            node_name,
            assigned_visit_keys,
            require_assigned_rank=True,
        )
        node_entries = _entries_for_node(context, node_name)
        buyer_evaluated = 0
        buyer_unevaluated = 0
        seller_evaluated = 0
        seller_unevaluated = 0
        buyer_satisfied = 0
        buyer_unsatisfied = 0
        seller_satisfied = 0
        seller_unsatisfied = 0
        buyer_gain_values: list[int | float | None] = []
        seller_gain_values: list[int | float | None] = []
        for visit_row in node_visits:
            if visit_row.role == OrderControlTvtMpActualPassageRole.BUYER.value:
                if visit_row.realized_gain is None:
                    buyer_unevaluated = buyer_unevaluated + 1
                else:
                    buyer_evaluated = buyer_evaluated + 1
                    buyer_gain_values.append(visit_row.realized_gain)
                    if visit_row.satisfaction_status == "satisfied":
                        buyer_satisfied = buyer_satisfied + 1
                    else:
                        buyer_unsatisfied = buyer_unsatisfied + 1
            if visit_row.role == OrderControlTvtMpActualPassageRole.SELLER.value:
                if visit_row.realized_gain is None:
                    seller_unevaluated = seller_unevaluated + 1
                else:
                    seller_evaluated = seller_evaluated + 1
                    seller_gain_values.append(visit_row.realized_gain)
                    if visit_row.satisfaction_status == "satisfied":
                        seller_satisfied = seller_satisfied + 1
                    else:
                        seller_unsatisfied = seller_unsatisfied + 1
        if buyer_visit_count == 0:
            buyer_gain_total = 0
        elif not buyer_gain_values:
            buyer_gain_total = None
        else:
            buyer_gain_total, _, _ = _sum_optional_numeric(buyer_gain_values)
        if seller_visit_count == 0:
            seller_gain_total = 0
        elif not seller_gain_values:
            seller_gain_total = None
        else:
            seller_gain_total, _, _ = _sum_optional_numeric(seller_gain_values)
        buyer_official_total = 0
        seller_official_total = 0
        for transaction_row in node_transactions:
            buyer_official_total = (
                buyer_official_total + transaction_row.buyer_official_payment_total
            )
            seller_official_total = (
                seller_official_total + transaction_row.seller_official_compensation_total
            )
        buyer_reference_values = [
            row.buyer_reference_payment_total for row in node_transactions
        ]
        seller_reference_values = [
            row.seller_reference_compensation_total for row in node_transactions
        ]
        if not node_transactions:
            buyer_reference_total = 0
            seller_reference_total = 0
        else:
            buyer_reference_total, _, _ = _sum_optional_numeric(buyer_reference_values)
            seller_reference_total, _, _ = _sum_optional_numeric(
                seller_reference_values
            )
        buyer_observed, buyer_unobserved = _count_actual_observation_by_role(
            node_entries,
            OrderControlTvtMpActualPassageRole.BUYER,
        )
        seller_observed, seller_unobserved = _count_actual_observation_by_role(
            node_entries,
            OrderControlTvtMpActualPassageRole.SELLER,
        )
        np_observed, np_unobserved = _count_actual_observation_by_role(
            node_entries,
            OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        )
        np_predictable, np_unpredictable = _np_candidate_predictability_counts(
            node_entries
        )
        predicted_values, actual_values, candidate_minus_values = (
            _np_external_effect_values(node_entries)
        )
        np_predicted_total, _, _ = _sum_optional_numeric(predicted_values)
        if nonparticipating_visit_count == 0:
            np_predicted_total = 0
            np_actual_total = 0
            np_candidate_minus_total = 0
        else:
            np_actual_total, _, _ = _sum_optional_numeric(actual_values)
            np_candidate_minus_total, _, _ = _sum_optional_numeric(
                candidate_minus_values
            )
        passed = 0
        unpassed = 0
        for visit_key in assigned_visit_keys:
            if (node_name, visit_key) in context.history_by_node_and_visit_key:
                passed = passed + 1
            else:
                unpassed = unpassed + 1
        rows.append(
            OrderControlTvtMpResearchOutputNodeRow(
                scenario_name=context.scenario_name,
                node_name=node_name,
                transaction_count=len(node_transactions),
                feasible_count=feasible,
                infeasible_count=infeasible,
                unavailable_count=unavailable,
                buyer_visit_count=buyer_visit_count,
                seller_visit_count=seller_visit_count,
                nonparticipating_visit_count=nonparticipating_visit_count,
                assigned_visit_count=len(assigned_visit_keys),
                actual_passed_assigned_visit_count=passed,
                actual_unpassed_assigned_visit_count=unpassed,
                rank_difference_evaluated_count=rank_stats[
                    "rank_difference_evaluated_count"
                ],
                rank_difference_unavailable_count=rank_stats[
                    "rank_difference_unavailable_count"
                ],
                moved_earlier_count=rank_stats["moved_earlier_count"],
                rank_exact_count=rank_stats["rank_exact_count"],
                moved_later_count=rank_stats["moved_later_count"],
                rank_difference_total=rank_stats["rank_difference_total"],
                buyer_evaluated_count=buyer_evaluated,
                buyer_unevaluated_count=buyer_unevaluated,
                buyer_satisfied_count=buyer_satisfied,
                buyer_unsatisfied_count=buyer_unsatisfied,
                seller_evaluated_count=seller_evaluated,
                seller_unevaluated_count=seller_unevaluated,
                seller_satisfied_count=seller_satisfied,
                seller_unsatisfied_count=seller_unsatisfied,
                buyer_realized_gain_total=buyer_gain_total,
                seller_realized_gain_total=seller_gain_total,
                buyer_official_payment_total=buyer_official_total,
                seller_official_compensation_total=seller_official_total,
                buyer_reference_payment_total=buyer_reference_total,
                seller_reference_compensation_total=seller_reference_total,
                buyer_actual_observed_count=buyer_observed,
                buyer_actual_unobserved_count=buyer_unobserved,
                seller_actual_observed_count=seller_observed,
                seller_actual_unobserved_count=seller_unobserved,
                nonparticipating_actual_observed_count=np_observed,
                nonparticipating_actual_unobserved_count=np_unobserved,
                nonparticipating_candidate_predictable_count=np_predictable,
                nonparticipating_candidate_unpredictable_count=np_unpredictable,
                nonparticipating_predicted_external_effect_total=np_predicted_total,
                nonparticipating_actual_external_effect_total=np_actual_total,
                nonparticipating_candidate_minus_actual_total=np_candidate_minus_total,
            )
        )
    return rows


def _build_scenario_row(
    context: _ResearchBuildContext,
    transactions: list[OrderControlTvtMpResearchOutputTransactionRow],
    visits: list[OrderControlTvtMpResearchOutputVisitRow],
    nodes: list[OrderControlTvtMpResearchOutputNodeRow],
) -> tuple[OrderControlTvtMpResearchOutputScenarioRow, ...]:
    feasible = 0
    infeasible = 0
    unavailable = 0
    for row in transactions:
        status = row.trade_ex_post_evaluation_status
        if status == OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE.value:
            feasible = feasible + 1
        elif (
            status == OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE.value
        ):
            infeasible = infeasible + 1
        else:
            unavailable = unavailable + 1
    buyer_visit_count = 0
    seller_visit_count = 0
    nonparticipating_visit_count = 0
    actual_observed = 0
    actual_unobserved = 0
    candidate_predictable = 0
    candidate_unpredictable = 0
    buyer_evaluated = 0
    buyer_unevaluated = 0
    seller_evaluated = 0
    seller_unevaluated = 0
    buyer_satisfied = 0
    buyer_unsatisfied = 0
    seller_satisfied = 0
    seller_unsatisfied = 0
    buyer_gain_values: list[int | float | None] = []
    seller_gain_values: list[int | float | None] = []
    for visit_row in visits:
        if visit_row.role == OrderControlTvtMpActualPassageRole.BUYER.value:
            buyer_visit_count = buyer_visit_count + 1
        elif visit_row.role == OrderControlTvtMpActualPassageRole.SELLER.value:
            seller_visit_count = seller_visit_count + 1
        else:
            nonparticipating_visit_count = nonparticipating_visit_count + 1
        if (
            visit_row.actual_observation_status
            == OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED.value
        ):
            actual_observed = actual_observed + 1
        else:
            actual_unobserved = actual_unobserved + 1
        if visit_row.predicted_observation_status == (
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED.value
        ):
            candidate_predictable = candidate_predictable + 1
        else:
            candidate_unpredictable = candidate_unpredictable + 1
        if visit_row.role == OrderControlTvtMpActualPassageRole.BUYER.value:
            if visit_row.realized_gain is None:
                buyer_unevaluated = buyer_unevaluated + 1
            else:
                buyer_evaluated = buyer_evaluated + 1
                buyer_gain_values.append(visit_row.realized_gain)
                if visit_row.satisfaction_status == "satisfied":
                    buyer_satisfied = buyer_satisfied + 1
                else:
                    buyer_unsatisfied = buyer_unsatisfied + 1
        if visit_row.role == OrderControlTvtMpActualPassageRole.SELLER.value:
            if visit_row.realized_gain is None:
                seller_unevaluated = seller_unevaluated + 1
            else:
                seller_evaluated = seller_evaluated + 1
                seller_gain_values.append(visit_row.realized_gain)
                if visit_row.satisfaction_status == "satisfied":
                    seller_satisfied = seller_satisfied + 1
                else:
                    seller_unsatisfied = seller_unsatisfied + 1
    if buyer_visit_count == 0:
        buyer_gain_total = 0
    elif not buyer_gain_values:
        buyer_gain_total = None
    else:
        buyer_gain_total, _, _ = _sum_optional_numeric(buyer_gain_values)
    if seller_visit_count == 0:
        seller_gain_total = 0
    elif not seller_gain_values:
        seller_gain_total = None
    else:
        seller_gain_total, _, _ = _sum_optional_numeric(seller_gain_values)
    np_predicted_values: list[int | float | None] = []
    np_actual_values: list[int | float | None] = []
    np_candidate_minus_values: list[int | float | None] = []
    for visit_row in visits:
        if (
            visit_row.role
            != OrderControlTvtMpActualPassageRole.NONPARTICIPATING.value
        ):
            continue
        np_predicted_values.append(visit_row.baseline_minus_candidate_time_value)
        np_actual_values.append(visit_row.baseline_minus_actual_time_value)
        np_candidate_minus_values.append(visit_row.candidate_minus_actual_time_value)
    np_predicted_total, _, _ = _sum_optional_numeric(np_predicted_values)
    if nonparticipating_visit_count == 0:
        np_predicted_total = 0
        np_actual_total = 0
        np_candidate_minus_total = 0
    else:
        np_actual_total, _, _ = _sum_optional_numeric(np_actual_values)
        np_candidate_minus_total, _, _ = _sum_optional_numeric(
            np_candidate_minus_values
        )
    assigned_visit_count = 0
    actual_passed = 0
    actual_unpassed = 0
    global_rank_changes: list[int | float | None] = []
    for node_name in sorted(context.rank_states_by_node_name.keys()):
        rank_state = context.rank_states_by_node_name[node_name]
        assigned_keys = rank_state.confirmed_visit_keys_in_order()
        assigned_visit_count = assigned_visit_count + len(assigned_keys)
        for visit_key in assigned_keys:
            if (node_name, visit_key) in context.history_by_node_and_visit_key:
                actual_passed = actual_passed + 1
            else:
                actual_unpassed = actual_unpassed + 1
            assigned_rank = rank_state.assigned_rank(visit_key)
            actual_rank = context.history_by_node_and_visit_key.get(
                (node_name, visit_key)
            )
            if actual_rank is None:
                global_rank_changes.append(None)
            else:
                global_rank_changes.append(assigned_rank - actual_rank)
    global_rank_stats = _rank_stats_from_change_values(global_rank_changes)
    rank_evaluated = global_rank_stats["rank_difference_evaluated_count"]
    rank_unavailable = global_rank_stats["rank_difference_unavailable_count"]
    moved_earlier = global_rank_stats["moved_earlier_count"]
    rank_exact = global_rank_stats["rank_exact_count"]
    moved_later = global_rank_stats["moved_later_count"]
    rank_total = global_rank_stats["rank_difference_total"]
    scenario_row = OrderControlTvtMpResearchOutputScenarioRow(
        scenario_name=context.scenario_name,
        evaluation_end_timestep=context.evaluation_end_timestep,
        transaction_count=len(transactions),
        feasible_count=feasible,
        infeasible_count=infeasible,
        unavailable_count=unavailable,
        buyer_visit_count=buyer_visit_count,
        seller_visit_count=seller_visit_count,
        nonparticipating_visit_count=nonparticipating_visit_count,
        actual_observed_count=actual_observed,
        actual_unobserved_count=actual_unobserved,
        candidate_predictable_count=candidate_predictable,
        candidate_unpredictable_count=candidate_unpredictable,
        buyer_evaluated_count=buyer_evaluated,
        buyer_unevaluated_count=buyer_unevaluated,
        buyer_satisfied_count=buyer_satisfied,
        buyer_unsatisfied_count=buyer_unsatisfied,
        seller_evaluated_count=seller_evaluated,
        seller_unevaluated_count=seller_unevaluated,
        seller_satisfied_count=seller_satisfied,
        seller_unsatisfied_count=seller_unsatisfied,
        buyer_realized_gain_total=buyer_gain_total,
        seller_realized_gain_total=seller_gain_total,
        nonparticipating_predicted_external_effect_total=np_predicted_total,
        nonparticipating_actual_external_effect_total=np_actual_total,
        nonparticipating_candidate_minus_actual_total=np_candidate_minus_total,
        assigned_visit_count=assigned_visit_count,
        actual_passed_assigned_visit_count=actual_passed,
        actual_unpassed_assigned_visit_count=actual_unpassed,
        rank_difference_evaluated_count=rank_evaluated,
        rank_difference_unavailable_count=rank_unavailable,
        moved_earlier_count=moved_earlier,
        rank_exact_count=rank_exact,
        moved_later_count=moved_later,
        rank_difference_total=rank_total,
    )
    return (scenario_row,)
