# -*- coding: utf-8 -*-
"""Minimal full-run audit helper for one later TVT-MP trial.

The helper reads a completed driver result and the existing research-output
bundle. It does not change production code, traffic RNG, order-control RNG,
traffic behavior, or transaction results.

The saved result keeps scalars, strings, and VisitKey tuples for established
trades and their trade-scope visits. Live World, Vehicle, Node, and Link
objects are not part of that result.
"""

import ast
import csv
from dataclasses import dataclass
from pathlib import Path

import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as vehicle_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualNodePassageRecord,
    OrderControlTvtMpTradeExPostEvaluationStatus,
)
from uxsim.order_control_tvt_mp_atomic_apply import (
    OrderControlTvtMpTradeEstablishmentLogRecord,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateTrafficObservationRecord,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionStatus,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpCandidateEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpPaymentAndCompensationStatus,
)
from uxsim.order_control_tvt_mp_research_output import (
    OrderControlTvtMpResearchOutputTransactionRow,
    OrderControlTvtMpResearchOutputVisitRow,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
)


TRANSACTION_AUDIT_CSV_NAME = "tvt_mp_transaction_audit.csv"
VISIT_AUDIT_CSV_NAME = "tvt_mp_visit_audit.csv"

TRANSACTION_AUDIT_COLUMNS = (
    "decision_timestep",
    "node_name",
    "candidate_identity",
    "right_of_entry_visit_key",
    "right_of_entry_vehicle_name",
    "right_of_entry_baseline_arrival_timestep",
    "right_of_entry_baseline_rank",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "buyer_visit_keys",
    "seller_visit_keys",
    "nonparticipating_visit_keys",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "total_G",
    "total_R",
    "surplus",
    "economically_feasible",
    "infeasibility_reasons",
    "fifo_inspection_passed",
    "fifo_violation_count",
    "trade_ex_post_evaluation_status",
    "actual_evaluation_available",
    "max_same_inlink_party_count",
    "max_same_inlink_buyer_count",
    "max_same_inlink_seller_count",
    "max_same_inlink_nonparticipating_count",
)

# Party columns used by the existing side-by-side diagnostic, without the
# predecessor and successor strings, and with the real-world arrival column
# placed immediately after baseline arrival.
VISIT_AUDIT_COLUMNS = (
    "decision_timestep",
    "node_name",
    "candidate_identity",
    "visit_key",
    "vehicle_name",
    "visit_id",
    "role",
    "is_right_of_entry_holder",
    "inlink_name",
    "formal_route_next_link_name",
    "baseline_arrival_timestep",
    "actual_node_arrival_timestep",
    "arrival_tiebreaker",
    "baseline_local_rank",
    "post_trade_local_rank",
    "assigned_rank",
    "actual_node_passage_rank",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "predicted_observation_status",
    "actual_observation_status",
    "declared_vot_per_second",
    "true_vot_per_second",
    "buyer_value_G_b",
    "seller_required_compensation_R_s",
    "payment_P_b",
    "compensation_C_s",
    "realized_gain",
    "realized_delay_loss",
    "satisfaction_status",
    "binding_sequence_auxiliary_rank",
    "same_inlink_fifo_preserved",
)

PUBLIC_AUDIT_FUNCTION_NAMES = (
    "install_tvt_mp_full_run_audit",
    "finalize_tvt_mp_full_run_audit",
    "write_tvt_mp_full_run_audit_csv",
)
STATIC_VALIDATION_FUNCTION_NAME = (
    "validate_tvt_mp_full_run_audit_helper_static_contract"
)

EVALUATION_UNAVAILABLE = (
    OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE.value
)

ALLOWED_STANDARD_LIBRARY_MODULES = (
    "ast",
    "csv",
    "dataclasses",
    "pathlib",
)

ALLOWED_IMPORTED_MODULES = (
    "uxsim.order_control_tvt_mp_driver",
    "uxsim.uxsim",
    "uxsim.order_control_baseline_collector",
    "uxsim.order_control_baseline_driver",
    "uxsim.order_control_tvt_candidate_visit_set",
    "uxsim.order_control_tvt_mp_actual_passage",
    "uxsim.order_control_tvt_mp_atomic_apply",
    "uxsim.order_control_tvt_mp_candidate_local_virtual_calculation",
    "uxsim.order_control_tvt_mp_candidate_selection",
    "uxsim.order_control_tvt_mp_concrete_buyer_candidate_set",
    "uxsim.order_control_tvt_mp_economic_evaluation",
    "uxsim.order_control_tvt_mp_fifo_inspection",
    "uxsim.order_control_tvt_mp_general_trade_rank",
    "uxsim.order_control_tvt_mp_local_binding_rank_sequence",
    "uxsim.order_control_tvt_mp_payment_and_compensation",
    "uxsim.order_control_tvt_mp_research_output",
    "uxsim.order_control_tvt_node_rank_state",
    "uxsim.order_control_tvt_right_of_entry_selection",
)

ALLOWED_HOOK_ASSIGNMENTS = (
    "driver_module.run_tvt_mp_driver",
    "vehicle_module.Vehicle.record_order_control_node_arrival",
)


@dataclass(frozen=True)
class _TvtMpFullRunTransactionAuditRow:
    decision_timestep: int
    node_name: str
    candidate_identity: str
    right_of_entry_visit_key: str
    right_of_entry_vehicle_name: str
    right_of_entry_baseline_arrival_timestep: int
    right_of_entry_baseline_rank: int
    buyer_count: int
    seller_count: int
    nonparticipating_count: int
    trade_scope_count: int
    buyer_visit_keys: str
    seller_visit_keys: str
    nonparticipating_visit_keys: str
    baseline_order_visit_keys: str
    candidate_order_visit_keys: str
    total_G: object
    total_R: object
    surplus: object
    economically_feasible: object
    infeasibility_reasons: str
    fifo_inspection_passed: bool
    fifo_violation_count: int
    trade_ex_post_evaluation_status: object
    actual_evaluation_available: object
    max_same_inlink_party_count: int
    max_same_inlink_buyer_count: int
    max_same_inlink_seller_count: int
    max_same_inlink_nonparticipating_count: int


@dataclass(frozen=True)
class _TvtMpFullRunVisitAuditRow:
    decision_timestep: int
    node_name: str
    candidate_identity: str
    visit_key: str
    vehicle_name: str
    visit_id: int
    role: str
    is_right_of_entry_holder: bool
    inlink_name: object
    formal_route_next_link_name: object
    baseline_arrival_timestep: object
    actual_node_arrival_timestep: object
    arrival_tiebreaker: object
    baseline_local_rank: int
    post_trade_local_rank: int
    assigned_rank: object
    actual_node_passage_rank: object
    baseline_passage_timestep: object
    candidate_passage_timestep: object
    actual_passage_timestep: object
    predicted_observation_status: object
    actual_observation_status: object
    declared_vot_per_second: object
    true_vot_per_second: object
    buyer_value_G_b: object
    seller_required_compensation_R_s: object
    payment_P_b: object
    compensation_C_s: object
    realized_gain: object
    realized_delay_loss: object
    satisfaction_status: object
    binding_sequence_auxiliary_rank: object
    same_inlink_fifo_preserved: object


@dataclass(frozen=True)
class _TvtMpFullRunAuditResult:
    transaction_rows: tuple
    visit_rows: tuple


class _FullRunAuditState:
    def __init__(self):
        self.installed = False
        self.real_world = None
        self.original_run_tvt_mp_driver = None
        self.original_record_order_control_node_arrival = None
        self.decisions = {}
        self.actual_node_arrivals = {}


_STATE = _FullRunAuditState()


def _decision_label(node_name: str, timestep: int) -> str:
    return f"{node_name} T={timestep}"


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _join_visit_keys(visit_keys) -> str:
    parts = []
    for visit_key in visit_keys:
        parts.append(_visit_text(visit_key))
    return "|".join(parts)


def _plain_visit_key(visit_key):
    if (
        not isinstance(visit_key, tuple)
        or len(visit_key) != 2
        or not isinstance(visit_key[0], str)
        or visit_key[0] == ""
        or type(visit_key[1]) is not int
        or visit_key[1] < 1
    ):
        raise RuntimeError(
            f"VisitKey is not a (vehicle_name, visit_id) pair: {visit_key!r}."
        )
    return (visit_key[0], visit_key[1])


def _copy_visit_keys(visit_keys):
    copied = []
    for visit_key in visit_keys:
        copied.append(_plain_visit_key(visit_key))
    return tuple(copied)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if value is True:
        return "True"
    if value is False:
        return "False"
    return str(value)


def _require_node_result(results, node_name: str, timestep: int, stage_name: str):
    matched = None
    match_count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        match_count = match_count + 1
        matched = result
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {stage_name} has "
            f"{match_count} results for the target node."
        )
    return matched


def _saved_driver_columns(atomic):
    """Walk saved attributes only. Does not call production helpers."""
    validation_set = atomic.final_consistency_validation_set_result
    final_rank_set = validation_set.final_rank_set_result
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection_set = payment_set.candidate_selection_set_result
    economic_set = selection_set.economic_evaluation_set_result
    local_set = economic_set.local_virtual_calculation_set_result
    fifo_set = local_set.fifo_inspection_set_result
    trade_rank_set = fifo_set.general_trade_rank_set_result
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    inlink_order_set = concrete_set.inlink_candidate_physical_order_result
    candidate_visit_set = inlink_order_set.candidate_visit_set_result
    right_of_entry_set = candidate_visit_set.right_of_entry_selection_result
    leading_set = right_of_entry_set.leading_confirmation_result
    arrived_set = leading_set.arrived_confirmation_result
    alignment_set = arrived_set.alignment_fork_result
    fork_result = alignment_set.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError(
            "Saved alignment fork_result is not OrderControlBaselineForkResult: "
            f"{type(fork_result).__name__}."
        )
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError(
            "Saved fork_result.collector is not OrderControlBaselineCollector: "
            f"{type(collector).__name__}."
        )
    return {
        "payment_nodes": payment_set.node_payment_and_compensation_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "fifo_nodes": fifo_set.node_fifo_inspection_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "concrete_nodes": concrete_set.node_concrete_buyer_candidate_set_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
    }


def _baseline_local_ranks(candidate_visits, node_name: str, timestep: int):
    ordered_visit_keys = []
    ranks = {}
    position = 0
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits entry "
                f"is {type(candidate_visit).__name__}."
            )
        position = position + 1
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits repeats "
                f"{_visit_text(visit_key)}. baseline_local_rank is not unique."
            )
        ordered_visit_keys.append(visit_key)
        ranks[visit_key] = position
    return tuple(ordered_visit_keys), ranks


def _require_python_int_rank(rank_value, rank_name: str, node_name: str, timestep: int, visit_key) -> int:
    if type(rank_value) is not int:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {rank_name} for "
            f"{_visit_text(visit_key)} must be a Python int, not bool; "
            f"got {rank_value!r}."
        )
    return rank_value


def _require_ranks_are_one_through_count(
    ranks_by_visit_key: dict,
    visit_count: int,
    rank_name: str,
    node_name: str,
    timestep: int,
) -> None:
    seen = []
    index = 0
    while index < visit_count:
        seen.append(False)
        index = index + 1
    for visit_key, rank_value in ranks_by_visit_key.items():
        checked = _require_python_int_rank(
            rank_value, rank_name, node_name, timestep, visit_key
        )
        if checked < 1 or checked > visit_count:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {rank_name} for "
                f"{_visit_text(visit_key)} is {checked}, not inside 1..{visit_count}."
            )
        slot = checked - 1
        if seen[slot] is True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {rank_name} {checked} "
                "is duplicated inside the candidate Visit set."
            )
        seen[slot] = True
    index = 0
    while index < visit_count:
        if seen[index] is not True:
            missing = index + 1
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {rank_name} is missing "
                f"{missing}. Ranks must be continuous from 1 through {visit_count}."
            )
        index = index + 1


def _require_same_population_and_continuous_local_ranks(
    ordered_visit_keys,
    baseline_local_ranks: dict,
    post_trade_local_ranks: dict,
    node_name: str,
    timestep: int,
    population_label: str,
) -> None:
    baseline_keys = set(baseline_local_ranks)
    post_trade_keys = set(post_trade_local_ranks)
    saved_keys = set(ordered_visit_keys)
    if baseline_keys != saved_keys or post_trade_keys != saved_keys:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {population_label} "
            "baseline_local_rank and post_trade_local_rank do not share the "
            "saved candidate Visit set."
        )
    if len(ordered_visit_keys) != len(saved_keys):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {population_label} "
            "saved candidate Visit order repeats a VisitKey."
        )
    visit_count = len(ordered_visit_keys)
    _require_ranks_are_one_through_count(
        baseline_local_ranks,
        visit_count,
        "baseline_local_rank",
        node_name,
        timestep,
    )
    _require_ranks_are_one_through_count(
        post_trade_local_ranks,
        visit_count,
        "post_trade_local_rank",
        node_name,
        timestep,
    )


def _post_trade_local_ranks(
    trade_result,
    ordered_visit_keys,
    node_name: str,
    timestep: int,
    population_label: str,
) -> dict:
    if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {population_label} trade "
            f"rank result is {type(trade_result).__name__}."
        )
    ranks = {}
    for visit_key in ordered_visit_keys:
        try:
            rank_value = trade_result.assigned_rank(visit_key)
        except ValueError as error:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {population_label} "
                f"has no post_trade_local_rank for {_visit_text(visit_key)}."
            ) from error
        ranks[visit_key] = _require_python_int_rank(
            rank_value, "post_trade_local_rank", node_name, timestep, visit_key
        )
    return ranks


def _establishment_record(world, timestep: int, node_name: str, visit_key):
    vehicle_name = visit_key[0]
    if vehicle_name not in world.VEHICLES:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {vehicle_name} is not on the real World."
        )
    vehicle = world.VEHICLES[vehicle_name]
    found = None
    for record in vehicle.order_exchange_log:
        if not isinstance(record, OrderControlTvtMpTradeEstablishmentLogRecord):
            continue
        if record.tvt_decision_timestep != timestep or record.node_name != node_name:
            continue
        if _plain_visit_key(record.visit_key) != visit_key:
            continue
        if found is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate establishment "
                f"record for {_visit_text(visit_key)}."
            )
        found = record
    return found


def _establishment_baseline_rank(world, timestep: int, node_name: str, visit_key):
    found = _establishment_record(world, timestep, node_name, visit_key)
    if found is None:
        return None
    return _require_python_int_rank(
        found.baseline_local_rank,
        "establishment baseline_local_rank",
        node_name,
        timestep,
        visit_key,
    )


def _require_rank_change_matches_local_ranks(
    establishment,
    baseline_local_rank: int,
    post_trade_local_rank: int,
    node_name: str,
    timestep: int,
    visit_key,
) -> None:
    rank_change = establishment.rank_change
    _require_python_int_rank(
        rank_change, "rank_change", node_name, timestep, visit_key
    )
    expected = baseline_local_rank - post_trade_local_rank
    if rank_change != expected:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rank_change {rank_change} "
            f"for {_visit_text(visit_key)} is not baseline_local_rank "
            f"{baseline_local_rank} minus post_trade_local_rank "
            f"{post_trade_local_rank}."
        )


def _resolve_baseline_rank(
    world,
    timestep: int,
    node_name: str,
    visit_key,
    role_name: str,
    saved_baseline_local_rank: int,
) -> int:
    checked = _require_python_int_rank(
        saved_baseline_local_rank,
        "baseline_local_rank",
        node_name,
        timestep,
        visit_key,
    )
    establishment_rank = _establishment_baseline_rank(
        world, timestep, node_name, visit_key
    )
    if role_name == "nonparticipating":
        if establishment_rank is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: nonparticipating "
                f"{_visit_text(visit_key)} has an establishment baseline rank."
            )
        return checked
    if establishment_rank is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {role_name} "
            f"{_visit_text(visit_key)} has no establishment baseline rank."
        )
    if establishment_rank != checked:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: establishment "
            f"baseline_local_rank {establishment_rank} for {_visit_text(visit_key)} "
            f"does not match saved candidate_visits rank {checked}."
        )
    return checked


def _require_ledger_assigned_rank(world, node_name: str, timestep: int, visit_key) -> int:
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict) or node_name not in states:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: real World has no "
            f"OrderControlTvtNodeRankState for {node_name}."
        )
    rank_state = states[node_name]
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rank state is "
            f"{type(rank_state).__name__}."
        )
    if rank_state.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: rank state node_name "
            f"is {rank_state.node_name!r}."
        )
    assigned_rank = rank_state.assigned_rank(visit_key)
    if assigned_rank is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected party "
            f"{_visit_text(visit_key)} has no ledger assigned_rank."
        )
    checked = _require_python_int_rank(
        assigned_rank, "assigned_rank", node_name, timestep, visit_key
    )
    if checked < 1:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: assigned_rank for "
            f"{_visit_text(visit_key)} is {checked}."
        )
    return checked


def _actual_passage_records_in_stored_order(world, node_name: str) -> tuple:
    registry = getattr(
        world, "order_control_tvt_mp_actual_node_passage_history_registry", None
    )
    if not isinstance(registry, OrderControlTvtMpActualNodePassageHistoryRegistry):
        raise RuntimeError(
            f"Node {node_name}: actual passage history registry is "
            f"{type(registry).__name__}."
        )
    stored_records = registry.records_by_node_name.get(node_name, ())
    if not isinstance(stored_records, tuple):
        raise RuntimeError(
            f"Node {node_name}: actual passage history is "
            f"{type(stored_records).__name__}, not the stored tuple."
        )
    checked_records = []
    seen_visit_keys = {}
    expected_rank = 1
    for record in stored_records:
        if not isinstance(record, OrderControlTvtMpActualNodePassageRecord):
            raise RuntimeError(
                f"Node {node_name}: actual passage history entry is "
                f"{type(record).__name__}."
            )
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name}: actual passage history repeats "
                f"{_visit_text(visit_key)}."
            )
        rank_value = record.actual_node_passage_rank
        if type(rank_value) is not int:
            raise RuntimeError(
                f"Node {node_name}: actual_node_passage_rank for "
                f"{_visit_text(visit_key)} must be a Python int, not bool; "
                f"got {rank_value!r}."
            )
        if rank_value < 1:
            raise RuntimeError(
                f"Node {node_name}: actual_node_passage_rank for "
                f"{_visit_text(visit_key)} is {rank_value}."
            )
        if rank_value != expected_rank:
            raise RuntimeError(
                f"Node {node_name}: stored actual_node_passage_rank {rank_value} "
                f"for {_visit_text(visit_key)} is not continuous position "
                f"{expected_rank}. Stored history order was not rearranged."
            )
        seen_visit_keys[visit_key] = True
        checked_records.append(record)
        expected_rank = expected_rank + 1
    return tuple(checked_records)


def _actual_passage_ranks_in_stored_order(world, node_name: str) -> dict:
    records = _actual_passage_records_in_stored_order(world, node_name)
    ranks = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        ranks[visit_key] = record.actual_node_passage_rank
    return ranks


def _collector_snapshot(collector, timestep: int, node_name: str, visit_key) -> dict:
    snapshot = collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
    if snapshot is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: collector has no baseline "
            f"snapshot for {_visit_text(visit_key)}."
        )
    arrival = snapshot["baseline_arrival_timestep"]
    if type(arrival) is not int:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: baseline_arrival_timestep for "
            f"{_visit_text(visit_key)} is {arrival!r}."
        )
    return snapshot


def _records_by_visit_key(records, node_name: str, timestep: int, record_name: str) -> dict:
    mapping = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {record_name} repeats "
                f"{_visit_text(visit_key)}."
            )
        mapping[visit_key] = record
    return mapping


def _require_same_visit_keys(left, right, node_name: str, timestep: int, label: str) -> None:
    if set(left) != set(right):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: VisitKey sets differ for {label}."
        )


def _candidate_identity(node_name: str, buyers_sorted) -> str:
    return node_name + "|" + _join_visit_keys(buyers_sorted)


def _match_selected_trade_and_fifo(
    selected_local,
    trade_node,
    fifo_node,
    node_name: str,
    timestep: int,
):
    concrete_set = selected_local.concrete_buyer_candidate_set
    if not isinstance(concrete_set, OrderControlTvtMpConcreteBuyerCandidateSet):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected concrete buyer set "
            f"is {type(concrete_set).__name__}."
        )
    matched_trade = None
    for trade_result in trade_node.candidate_trade_rank_results:
        if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade rank result is "
                f"{type(trade_result).__name__}."
            )
        if trade_result.concrete_buyer_candidate_set is concrete_set:
            if matched_trade is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: selected concrete set "
                    "matches two trade-rank results."
                )
            matched_trade = trade_result
    if matched_trade is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate has no "
            "saved general trade-rank result."
        )
    matched_fifo = None
    for fifo_result in fifo_node.candidate_fifo_inspection_results:
        if not isinstance(fifo_result, OrderControlTvtMpCandidateFifoInspectionResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result is "
                f"{type(fifo_result).__name__}."
            )
        if fifo_result.general_trade_rank_result is matched_trade:
            if matched_fifo is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: selected trade rank "
                    "matches two FIFO results."
                )
            matched_fifo = fifo_result
    if matched_fifo is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate has no "
            "saved FIFO inspection result."
        )
    return matched_trade, matched_fifo


def _require_unique_rank_values(parties, rank_name: str, node_name: str, timestep: int) -> None:
    seen = {}
    for party in parties:
        rank_value = party[rank_name]
        if rank_value in seen:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope {rank_name} "
                "values are not unique."
            )
        seen[rank_value] = True


def _build_parties(
    world,
    timestep: int,
    node_name: str,
    candidate_identity: str,
    binding_visits,
    trade_result,
    economic_result,
    payment_node,
    traffic_by_key: dict,
    baseline_local_ranks: dict,
    post_trade_local_ranks: dict,
    collector,
    right_of_entry_key,
) -> list:
    buyer_records = _records_by_visit_key(
        economic_result.buyer_economic_records,
        node_name,
        timestep,
        "buyer_economic_records",
    )
    seller_records = _records_by_visit_key(
        economic_result.seller_economic_records,
        node_name,
        timestep,
        "seller_economic_records",
    )
    payment_by_key = _records_by_visit_key(
        payment_node.buyer_payment_records,
        node_name,
        timestep,
        "buyer_payment_records",
    )
    compensation_by_key = _records_by_visit_key(
        payment_node.seller_compensation_records,
        node_name,
        timestep,
        "seller_compensation_records",
    )
    buyers_sorted = _copy_visit_keys(trade_result.buyers_sorted)
    sellers_sorted = _copy_visit_keys(trade_result.sellers_sorted)
    nonparticipating_sorted = _copy_visit_keys(
        trade_result.nonparticipating_visits_sorted
    )
    trade_scope = _copy_visit_keys(trade_result.trade_scope)
    role_columns = []
    for visit_key in buyers_sorted:
        role_columns.append(visit_key)
    for visit_key in sellers_sorted:
        role_columns.append(visit_key)
    for visit_key in nonparticipating_sorted:
        role_columns.append(visit_key)
    _require_same_visit_keys(
        trade_scope,
        tuple(role_columns),
        node_name,
        timestep,
        "trade_scope versus role columns",
    )
    _require_same_visit_keys(
        buyers_sorted,
        tuple(buyer_records),
        node_name,
        timestep,
        "buyers versus buyer economics",
    )
    _require_same_visit_keys(
        sellers_sorted,
        tuple(seller_records),
        node_name,
        timestep,
        "sellers versus seller economics",
    )
    _require_same_visit_keys(
        buyers_sorted,
        tuple(payment_by_key),
        node_name,
        timestep,
        "buyers versus payments",
    )
    _require_same_visit_keys(
        sellers_sorted,
        tuple(compensation_by_key),
        node_name,
        timestep,
        "sellers versus compensations",
    )
    binding_keys = []
    parties = []
    for binding_visit in binding_visits:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: binding visit is "
                f"{type(binding_visit).__name__}."
            )
        if (
            binding_visit.binding_partition
            is not OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope binding visit "
                f"{binding_visit.visit_key!r} has partition "
                f"{binding_visit.binding_partition!r}."
            )
        visit_key = _plain_visit_key(binding_visit.visit_key)
        binding_keys.append(visit_key)
        role = binding_visit.trade_role
        if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
            role_name = "buyer"
        elif role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
            role_name = "seller"
        elif role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
            role_name = "nonparticipating"
        else:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-scope visit "
                f"{_visit_text(visit_key)} has role {role!r}."
            )
        if visit_key not in baseline_local_ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "is missing from saved candidate_visits."
            )
        if visit_key not in post_trade_local_ranks:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                "is missing from the selected post_trade_local_rank map."
            )
        snapshot = _collector_snapshot(collector, timestep, node_name, visit_key)
        if snapshot["baseline_arrival_timestep"] != binding_visit.baseline_arrival_timestep:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector A for "
                f"{_visit_text(visit_key)} does not match the binding visit."
            )
        if snapshot["arrival_tiebreaker"] != binding_visit.arrival_tiebreaker:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector tiebreaker for "
                f"{_visit_text(visit_key)} does not match the binding visit."
            )
        if snapshot["vehicle_id"] != binding_visit.vehicle_id:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector vehicle_id "
                f"for {_visit_text(visit_key)} does not match the binding visit."
            )
        if snapshot["inlink_name"] != binding_visit.inlink_name:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: collector inlink for "
                f"{_visit_text(visit_key)} does not match the binding visit."
            )
        observation = traffic_by_key.get(visit_key)
        if observation is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected candidate has no "
                f"traffic observation for {_visit_text(visit_key)}."
            )
        baseline_passage = observation.baseline_passage_timestep
        candidate_passage = observation.candidate_passage_timestep
        buyer_record = buyer_records.get(visit_key)
        seller_record = seller_records.get(visit_key)
        if role_name == "buyer":
            if buyer_record is None or seller_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer role does not match "
                    f"economic records for {_visit_text(visit_key)}."
                )
            if buyer_record.baseline_passage_timestep != baseline_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer baseline passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            if buyer_record.candidate_passage_timestep != candidate_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: buyer candidate passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            declared_vot = buyer_record.declared_vot_per_second
            buyer_value = buyer_record.gross_time_value_G_b
            seller_compensation = None
            payment = payment_by_key[visit_key].payment_P_b
            compensation = None
        elif role_name == "seller":
            if seller_record is None or buyer_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller role does not match "
                    f"economic records for {_visit_text(visit_key)}."
                )
            if seller_record.baseline_passage_timestep != baseline_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller baseline passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            if seller_record.candidate_passage_timestep != candidate_passage:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: seller candidate passage "
                    f"disagrees with traffic observation for {_visit_text(visit_key)}."
                )
            declared_vot = seller_record.declared_vot_per_second
            buyer_value = None
            seller_compensation = seller_record.required_compensation_R_s
            payment = None
            compensation = compensation_by_key[visit_key].compensation_amount
        else:
            if buyer_record is not None or seller_record is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: nonparticipating "
                    f"{_visit_text(visit_key)} has an economic record."
                )
            declared_vot = None
            buyer_value = None
            seller_compensation = None
            payment = None
            compensation = None
        if role_name == "buyer" and buyer_value is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: buyer {_visit_text(visit_key)} "
                "is missing gross_time_value_G_b."
            )
        if role_name == "seller" and seller_compensation is None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: seller {_visit_text(visit_key)} "
                "is missing required_compensation_R_s."
            )
        baseline_local_rank = _resolve_baseline_rank(
            world,
            timestep,
            node_name,
            visit_key,
            role_name,
            baseline_local_ranks[visit_key],
        )
        post_trade_local_rank = _require_python_int_rank(
            post_trade_local_ranks[visit_key],
            "post_trade_local_rank",
            node_name,
            timestep,
            visit_key,
        )
        establishment = _establishment_record(world, timestep, node_name, visit_key)
        if role_name == "buyer" or role_name == "seller":
            if establishment is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: {_visit_text(visit_key)} "
                    "has no saved establishment record."
                )
            establishment_post_trade = _require_python_int_rank(
                establishment.post_trade_local_rank,
                "establishment post_trade_local_rank",
                node_name,
                timestep,
                visit_key,
            )
            if establishment_post_trade != post_trade_local_rank:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: establishment "
                    f"post_trade_local_rank {establishment_post_trade} "
                    f"for {_visit_text(visit_key)} does not match the selected "
                    f"general trade rank {post_trade_local_rank}."
                )
            _require_rank_change_matches_local_ranks(
                establishment,
                baseline_local_rank,
                post_trade_local_rank,
                node_name,
                timestep,
                visit_key,
            )
        elif establishment is not None:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: nonparticipating "
                f"{_visit_text(visit_key)} has an establishment record."
            )
        binding_rank = _require_python_int_rank(
            binding_visit.binding_rank,
            "binding_sequence_auxiliary_rank",
            node_name,
            timestep,
            visit_key,
        )
        parties.append(
            {
                "decision_timestep": timestep,
                "node_name": node_name,
                "candidate_identity": candidate_identity,
                "visit_key": _visit_text(visit_key),
                "visit_key_tuple": visit_key,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "vehicle_id": binding_visit.vehicle_id,
                "role": role_name,
                "is_right_of_entry_holder": visit_key == right_of_entry_key,
                "inlink_name": binding_visit.inlink_name,
                "formal_route_next_link_name": binding_visit.route_next_link_name,
                "baseline_arrival_timestep": snapshot["baseline_arrival_timestep"],
                "actual_node_arrival_timestep": None,
                "arrival_tiebreaker": snapshot["arrival_tiebreaker"],
                "baseline_local_rank": baseline_local_rank,
                "post_trade_local_rank": post_trade_local_rank,
                "assigned_rank": None,
                "actual_node_passage_rank": None,
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_passage,
                "actual_passage_timestep": None,
                "predicted_observation_status": None,
                "actual_observation_status": None,
                "declared_vot_per_second": declared_vot,
                "true_vot_per_second": observation.true_vot_per_second,
                "buyer_value_G_b": buyer_value,
                "seller_required_compensation_R_s": seller_compensation,
                "payment_P_b": payment,
                "compensation_C_s": compensation,
                "realized_gain": None,
                "realized_delay_loss": None,
                "satisfaction_status": None,
                "binding_sequence_auxiliary_rank": binding_rank,
                "same_inlink_fifo_preserved": None,
            }
        )
    _require_same_visit_keys(
        binding_keys,
        trade_scope,
        node_name,
        timestep,
        "binding trade scope versus trade_scope",
    )
    _require_same_visit_keys(
        binding_keys,
        tuple(traffic_by_key),
        node_name,
        timestep,
        "binding trade scope versus observations",
    )
    _require_unique_rank_values(
        parties, "binding_sequence_auxiliary_rank", node_name, timestep
    )
    _require_unique_rank_values(
        parties, "baseline_local_rank", node_name, timestep
    )
    _require_unique_rank_values(
        parties, "post_trade_local_rank", node_name, timestep
    )
    return parties


def _baseline_fifo_sort_key(party):
    return (
        party["baseline_local_rank"],
        party["baseline_arrival_timestep"],
        party["arrival_tiebreaker"],
        party["vehicle_id"],
        party["visit_key_tuple"],
    )


def _candidate_fifo_sort_key(party):
    return (
        party["binding_sequence_auxiliary_rank"],
        party["visit_key_tuple"],
    )


def _annotate_same_inlink_fifo(parties) -> int:
    """Count same-inlink order changes.

    Baseline order is baseline local rank, then arrival, tiebreaker, vehicle id,
    and VisitKey. Candidate order is the binding auxiliary rank. The grouping
    key is the saved inlink name. Predecessor and successor strings are not
    stored.
    """
    grouped = {}
    for party in parties:
        inlink_name = party["inlink_name"]
        if inlink_name not in grouped:
            grouped[inlink_name] = []
        grouped[inlink_name].append(party)
    violation_count = 0
    for inlink_parties in grouped.values():
        baseline_order = sorted(inlink_parties, key=_baseline_fifo_sort_key)
        candidate_order = sorted(inlink_parties, key=_candidate_fifo_sort_key)
        candidate_position = {}
        candidate_index = 0
        for party in candidate_order:
            candidate_position[party["visit_key_tuple"]] = candidate_index
            candidate_index = candidate_index + 1
        baseline_position = {}
        baseline_index = 0
        for party in baseline_order:
            baseline_position[party["visit_key_tuple"]] = baseline_index
            baseline_index = baseline_index + 1
        for party in baseline_order:
            preserved = True
            own_candidate = candidate_position[party["visit_key_tuple"]]
            for other in inlink_parties:
                if other is party:
                    continue
                baseline_before = (
                    baseline_position[party["visit_key_tuple"]]
                    < baseline_position[other["visit_key_tuple"]]
                )
                candidate_before = (
                    own_candidate < candidate_position[other["visit_key_tuple"]]
                )
                if baseline_before != candidate_before:
                    preserved = False
            party["same_inlink_fifo_preserved"] = preserved
        left_index = 0
        while left_index < len(baseline_order):
            left = baseline_order[left_index]
            right_index = left_index + 1
            while right_index < len(baseline_order):
                right = baseline_order[right_index]
                if (
                    candidate_position[left["visit_key_tuple"]]
                    > candidate_position[right["visit_key_tuple"]]
                ):
                    violation_count = violation_count + 1
                right_index = right_index + 1
            left_index = left_index + 1
    return violation_count


def _max_same_inlink_role_counts(parties):
    grouped = {}
    for party in parties:
        inlink_name = party["inlink_name"]
        if inlink_name not in grouped:
            grouped[inlink_name] = []
        grouped[inlink_name].append(party)
    max_party_count = 0
    max_buyer_count = 0
    max_seller_count = 0
    max_nonparticipating_count = 0
    for inlink_parties in grouped.values():
        buyer_count = 0
        seller_count = 0
        nonparticipating_count = 0
        for party in inlink_parties:
            if party["role"] == "buyer":
                buyer_count = buyer_count + 1
            elif party["role"] == "seller":
                seller_count = seller_count + 1
            elif party["role"] == "nonparticipating":
                nonparticipating_count = nonparticipating_count + 1
            else:
                raise RuntimeError(f"Unexpected trade role {party['role']!r}.")
        party_count = len(inlink_parties)
        if party_count > max_party_count:
            max_party_count = party_count
        if buyer_count > max_buyer_count:
            max_buyer_count = buyer_count
        if seller_count > max_seller_count:
            max_seller_count = seller_count
        if nonparticipating_count > max_nonparticipating_count:
            max_nonparticipating_count = nonparticipating_count
    return (
        max_party_count,
        max_buyer_count,
        max_seller_count,
        max_nonparticipating_count,
    )


def _baseline_order_sort_key(party):
    return party["baseline_local_rank"]


def _candidate_order_sort_key(party):
    return party["post_trade_local_rank"]


def _capture_selected_node(world, columns, node_name: str, timestep: int) -> None:
    decision_key = (node_name, timestep)
    if decision_key in _STATE.decisions:
        raise RuntimeError(f"{_decision_label(node_name, timestep)} was observed twice.")
    payment_node = _require_node_result(
        columns["payment_nodes"], node_name, timestep, "payment"
    )
    selection_node = _require_node_result(
        columns["selection_nodes"], node_name, timestep, "selection"
    )
    economic_node = _require_node_result(
        columns["economic_nodes"], node_name, timestep, "economic"
    )
    local_node = _require_node_result(
        columns["local_nodes"], node_name, timestep, "local virtual calculation"
    )
    fifo_node = _require_node_result(
        columns["fifo_nodes"], node_name, timestep, "fifo"
    )
    trade_node = _require_node_result(
        columns["trade_rank_nodes"], node_name, timestep, "trade rank"
    )
    candidate_visit_node = _require_node_result(
        columns["candidate_visit_nodes"], node_name, timestep, "candidate visits"
    )
    right_of_entry_node = _require_node_result(
        columns["right_of_entry_nodes"], node_name, timestep, "right of entry"
    )
    if not isinstance(right_of_entry_node, OrderControlTvtNodeRightOfEntrySelectionResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry result type is "
            f"{type(right_of_entry_node).__name__}."
        )
    selected_economic = selection_node.selected_candidate_economic_result
    if (
        selection_node.selection_status
        is not OrderControlTvtMpCandidateSelectionStatus.SELECTED
        or selected_economic is None
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: no selected candidate."
        )
    if not isinstance(selected_economic, OrderControlTvtMpCandidateEconomicEvaluationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected economic result type is "
            f"{type(selected_economic).__name__}."
        )
    if payment_node.selected_candidate_economic_result is not selected_economic:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment result points at a "
            "different selected candidate."
        )
    if (
        payment_node.payment_and_compensation_status
        is not OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    ):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: payment status is "
            f"{payment_node.payment_and_compensation_status!r}."
        )
    selected_in_node = False
    for economic_result in economic_node.candidate_economic_evaluation_results:
        if economic_result is selected_economic:
            selected_in_node = True
    if selected_in_node is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate is not in "
            "the node economic results."
        )
    selected_local = selected_economic.candidate_local_virtual_calculation_result
    if not isinstance(selected_local, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local result type is "
            f"{type(selected_local).__name__}."
        )
    local_saved = False
    for local_result in local_node.candidate_local_virtual_calculation_results:
        if local_result is selected_local:
            local_saved = True
    if local_saved is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected local result is not "
            "stored on the node local-calculation result."
        )
    trade_result, fifo_result = _match_selected_trade_and_fifo(
        selected_local, trade_node, fifo_node, node_name, timestep
    )
    if fifo_result.preserves_inlink_fifo is not True:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected candidate did not "
            "pass FIFO inspection."
        )
    buyers_sorted = _copy_visit_keys(trade_result.buyers_sorted)
    sellers_sorted = _copy_visit_keys(trade_result.sellers_sorted)
    nonparticipating_sorted = _copy_visit_keys(
        trade_result.nonparticipating_visits_sorted
    )
    if len(buyers_sorted) < 1 or len(sellers_sorted) < 1:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selected trade has "
            f"{len(buyers_sorted)} buyers and {len(sellers_sorted)} sellers."
        )
    binding_sequence = selected_local.binding_rank_sequence
    if binding_sequence.node_name != node_name:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: binding sequence node is "
            f"{binding_sequence.node_name!r}."
        )
    traffic_by_key = {}
    for observation in selected_local.traffic_observation_records:
        if not isinstance(observation, OrderControlTvtMpCandidateTrafficObservationRecord):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: traffic observation type is "
                f"{type(observation).__name__}."
            )
        observation_key = _plain_visit_key(observation.visit_key)
        if observation_key in traffic_by_key:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate traffic observation "
                f"for {_visit_text(observation_key)}."
            )
        traffic_by_key[observation_key] = observation
    candidate_identity = _candidate_identity(node_name, buyers_sorted)
    ordered_candidate_keys, candidate_visit_ranks = _baseline_local_ranks(
        candidate_visit_node.candidate_visits, node_name, timestep
    )
    post_trade_local_ranks = _post_trade_local_ranks(
        trade_result,
        ordered_candidate_keys,
        node_name,
        timestep,
        candidate_identity,
    )
    _require_same_population_and_continuous_local_ranks(
        ordered_candidate_keys,
        candidate_visit_ranks,
        post_trade_local_ranks,
        node_name,
        timestep,
        candidate_identity,
    )
    if right_of_entry_node.right_of_entry_visit_key is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right_of_entry_visit_key is missing."
        )
    right_of_entry_key = _plain_visit_key(right_of_entry_node.right_of_entry_visit_key)
    if right_of_entry_key not in candidate_visit_ranks:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry "
            f"{_visit_text(right_of_entry_key)} is not in candidate_visits."
        )
    right_snapshot = _collector_snapshot(
        columns["collector"], timestep, node_name, right_of_entry_key
    )
    parties = _build_parties(
        world,
        timestep,
        node_name,
        candidate_identity,
        binding_sequence.trade_scope_of_this_candidate_visits,
        trade_result,
        selected_economic,
        payment_node,
        traffic_by_key,
        candidate_visit_ranks,
        post_trade_local_ranks,
        columns["collector"],
        right_of_entry_key,
    )
    for party in parties:
        if party["role"] == "buyer" or party["role"] == "seller":
            if party["baseline_arrival_timestep"] is None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: "
                    f"{party['visit_key']} is missing baseline arrival A."
                )
    violation_count = _annotate_same_inlink_fifo(parties)
    max_counts = _max_same_inlink_role_counts(parties)
    baseline_order = sorted(parties, key=_baseline_order_sort_key)
    candidate_order = sorted(parties, key=_candidate_order_sort_key)
    baseline_order_keys = []
    for party in baseline_order:
        baseline_order_keys.append(party["visit_key_tuple"])
    candidate_order_keys = []
    for party in candidate_order:
        candidate_order_keys.append(party["visit_key_tuple"])
    reasons = []
    for reason in selected_economic.infeasibility_reasons:
        reasons.append(reason.value)
    decision = {
        "decision_timestep": timestep,
        "node_name": node_name,
        "candidate_identity": candidate_identity,
        "buyers_sorted": buyers_sorted,
        "right_of_entry_visit_key": _visit_text(right_of_entry_key),
        "right_of_entry_vehicle_name": right_of_entry_key[0],
        "right_of_entry_baseline_arrival_timestep": right_snapshot[
            "baseline_arrival_timestep"
        ],
        "right_of_entry_baseline_rank": candidate_visit_ranks[right_of_entry_key],
        "buyer_count": len(buyers_sorted),
        "seller_count": len(sellers_sorted),
        "nonparticipating_count": len(nonparticipating_sorted),
        "trade_scope_count": len(parties),
        "buyer_visit_keys": _join_visit_keys(buyers_sorted),
        "seller_visit_keys": _join_visit_keys(sellers_sorted),
        "nonparticipating_visit_keys": _join_visit_keys(nonparticipating_sorted),
        "baseline_order_visit_keys": _join_visit_keys(baseline_order_keys),
        "candidate_order_visit_keys": _join_visit_keys(candidate_order_keys),
        "total_G": selected_economic.total_buyer_value_G,
        "total_R": selected_economic.total_required_compensation_R,
        "surplus": selected_economic.surplus,
        "economically_feasible": selected_economic.economically_feasible,
        "infeasibility_reasons": "|".join(reasons),
        "fifo_inspection_passed": True,
        "fifo_violation_count": violation_count,
        "trade_ex_post_evaluation_status": None,
        "actual_evaluation_available": None,
        "max_same_inlink_party_count": max_counts[0],
        "max_same_inlink_buyer_count": max_counts[1],
        "max_same_inlink_seller_count": max_counts[2],
        "max_same_inlink_nonparticipating_count": max_counts[3],
        "parties": parties,
    }
    _STATE.decisions[decision_key] = decision


def _capture_real_world_driver_result(world, result) -> None:
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(
            f"TVT-MP driver result is {type(result).__name__}."
        )
    atomic = result.atomic_apply_set_result
    if atomic is None:
        return
    timestep = world.T
    if type(timestep) is not int:
        raise RuntimeError(f"Real World.T is {timestep!r}.")
    columns = _saved_driver_columns(atomic)
    for selection_node in columns["selection_nodes"]:
        if (
            selection_node.selection_status
            is not OrderControlTvtMpCandidateSelectionStatus.SELECTED
        ):
            continue
        if selection_node.selected_candidate_economic_result is None:
            raise RuntimeError(
                f"{_decision_label(selection_node.node_name, timestep)}: "
                "selection status is selected but the economic result is missing."
            )
        _capture_selected_node(world, columns, selection_node.node_name, timestep)


def _wrapped_run_tvt_mp_driver(world):
    result = _STATE.original_run_tvt_mp_driver(world)
    if world is not _STATE.real_world:
        return result
    _capture_real_world_driver_result(world, result)
    return result


def _remember_real_world_node_arrival(vehicle, node) -> None:
    """Store the first real-world arrival timestep after production records it.

    A baseline World and a copied evaluation World are ignored. If the VisitKey
    is already stored, later wrapper calls return without comparing World.T.
    Passage time is not used, and baseline arrival is not copied.
    """
    if vehicle.W is not _STATE.real_world:
        return
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        return
    if current_visit.get("node") is not node:
        return
    arrival_time = current_visit.get("arrival_time")
    if arrival_time is None:
        return
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} arrival visit_id "
            f"is {visit_id!r}."
        )
    key = (node.name, vehicle.name, visit_id)
    if key in _STATE.actual_node_arrivals:
        return
    timestep = vehicle.W.T
    if type(timestep) is not int or timestep < 0:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} arrival World.T "
            f"is {timestep!r}."
        )
    converted = int(round(arrival_time / vehicle.W.DELTAT))
    if converted != timestep:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} visit {visit_id} "
            f"arrival_time converts to {converted}, but World.T is {timestep}."
        )
    _STATE.actual_node_arrivals[key] = converted


def _wrapped_record_order_control_node_arrival(vehicle, node):
    result = _STATE.original_record_order_control_node_arrival(vehicle, node)
    _remember_real_world_node_arrival(vehicle, node)
    return result


def _find_research_transaction(bundle, decision):
    found = None
    for row in bundle.transactions:
        if not isinstance(row, OrderControlTvtMpResearchOutputTransactionRow):
            raise RuntimeError(f"Research transaction row is {type(row).__name__}.")
        if row.tvt_decision_timestep != decision["decision_timestep"]:
            continue
        if row.node_name != decision["node_name"]:
            continue
        buyers_sorted = _copy_visit_keys(row.buyers_sorted)
        if buyers_sorted != decision["buyers_sorted"]:
            continue
        if found is not None:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                "two research transaction rows match the selected buyers."
            )
        found = row
    return found


def _research_visits_by_key(bundle, decision) -> dict:
    found = {}
    for row in bundle.visits:
        if not isinstance(row, OrderControlTvtMpResearchOutputVisitRow):
            raise RuntimeError(f"Research visit row is {type(row).__name__}.")
        if row.tvt_decision_timestep != decision["decision_timestep"]:
            continue
        if row.node_name != decision["node_name"]:
            continue
        buyers_sorted = _copy_visit_keys(row.buyers_sorted)
        if buyers_sorted != decision["buyers_sorted"]:
            continue
        visit_key = (row.vehicle_name, row.visit_id)
        if visit_key in found:
            raise RuntimeError(
                f"{_decision_label(decision['node_name'], decision['decision_timestep'])}: "
                f"duplicate research visit {_visit_text(visit_key)}."
            )
        found[visit_key] = row
    return found


def _attach_research_output(bundle) -> None:
    if not hasattr(bundle, "transactions") or not hasattr(bundle, "visits"):
        raise RuntimeError(
            "Research output bundle does not provide transactions and visits."
        )
    for decision in _STATE.decisions.values():
        transaction = _find_research_transaction(bundle, decision)
        label = _decision_label(decision["node_name"], decision["decision_timestep"])
        if transaction is None:
            raise RuntimeError(
                f"{label}: research output has no transaction for the selected buyers."
            )
        decision["trade_ex_post_evaluation_status"] = (
            transaction.trade_ex_post_evaluation_status
        )
        status = transaction.trade_ex_post_evaluation_status
        decision["actual_evaluation_available"] = status != EVALUATION_UNAVAILABLE
        visits = _research_visits_by_key(bundle, decision)
        for party in decision["parties"]:
            visit_row = visits.get(party["visit_key_tuple"])
            if visit_row is None:
                raise RuntimeError(
                    f"{label}: research output has no visit row for {party['visit_key']}."
                )
            if visit_row.role != party["role"]:
                raise RuntimeError(
                    f"{label}: research role {visit_row.role!r} does not match "
                    f"{party['role']!r} for {party['visit_key']}."
                )
            if (
                visit_row.baseline_passage_timestep is not None
                and visit_row.baseline_passage_timestep != party["baseline_passage_timestep"]
            ):
                raise RuntimeError(
                    f"{label}: research baseline passage disagrees for {party['visit_key']}."
                )
            if (
                visit_row.candidate_passage_timestep is not None
                and visit_row.candidate_passage_timestep != party["candidate_passage_timestep"]
            ):
                raise RuntimeError(
                    f"{label}: research candidate passage disagrees for {party['visit_key']}."
                )
            party["actual_passage_timestep"] = visit_row.actual_passage_timestep
            party["predicted_observation_status"] = visit_row.predicted_observation_status
            party["actual_observation_status"] = visit_row.actual_observation_status
            party["research_output_actual_node_passage_rank"] = (
                visit_row.actual_node_passage_rank
            )
            party["realized_gain"] = visit_row.realized_gain
            party["realized_delay_loss"] = visit_row.realized_delay_loss
            party["satisfaction_status"] = visit_row.satisfaction_status
            if party["true_vot_per_second"] != visit_row.true_vot_per_second:
                raise RuntimeError(
                    f"{label}: research true VOT disagrees for {party['visit_key']}."
                )
            if (
                party["declared_vot_per_second"] is None
                and visit_row.declared_vot_per_second is not None
            ):
                party["declared_vot_per_second"] = visit_row.declared_vot_per_second


def _attach_node_continuous_ranks(world) -> None:
    """Read node-continuous ranks from the real World after the run.

    assigned_rank comes from the rank ledger. For a buyer or seller it must
    match the establishment record. actual_node_passage_rank comes from the
    stored passage history and stays None when that Visit was not observed.
    A missing history rank is not filled from passage time or from baseline
    arrival.
    """
    history_by_node = {}
    for decision in _STATE.decisions.values():
        node_name = decision["node_name"]
        timestep = decision["decision_timestep"]
        if node_name not in history_by_node:
            history_by_node[node_name] = _actual_passage_ranks_in_stored_order(
                world, node_name
            )
        actual_ranks = history_by_node[node_name]
        for party in decision["parties"]:
            visit_key = party["visit_key_tuple"]
            assigned_rank = _require_ledger_assigned_rank(
                world, node_name, timestep, visit_key
            )
            establishment = _establishment_record(world, timestep, node_name, visit_key)
            if party["role"] == "buyer" or party["role"] == "seller":
                if establishment is None:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"{party['visit_key']} has no establishment record for "
                        "the ledger_assigned_rank check."
                    )
                ledger_assigned_rank = _require_python_int_rank(
                    establishment.ledger_assigned_rank,
                    "ledger_assigned_rank",
                    node_name,
                    timestep,
                    visit_key,
                )
                if ledger_assigned_rank != assigned_rank:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"ledger_assigned_rank {ledger_assigned_rank} for "
                        f"{party['visit_key']} does not match rank-ledger "
                        f"assigned_rank {assigned_rank}."
                    )
            elif establishment is not None:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: nonparticipating "
                    f"{party['visit_key']} has an establishment record."
                )
            if visit_key in actual_ranks:
                actual_rank = actual_ranks[visit_key]
                if type(actual_rank) is not int or actual_rank < 1:
                    raise RuntimeError(
                        f"{_decision_label(node_name, timestep)}: "
                        f"actual_node_passage_rank for {party['visit_key']} "
                        f"is {actual_rank!r}."
                    )
            else:
                actual_rank = None
            research_rank = party.get("research_output_actual_node_passage_rank")
            if research_rank != actual_rank:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: research output "
                    f"actual_node_passage_rank {research_rank!r} for "
                    f"{party['visit_key']} does not match the passage "
                    f"history rank {actual_rank!r}."
                )
            party["assigned_rank"] = assigned_rank
            party["actual_node_passage_rank"] = actual_rank
            del party["research_output_actual_node_passage_rank"]


def _attach_actual_node_arrivals() -> None:
    for decision in _STATE.decisions.values():
        node_name = decision["node_name"]
        for party in decision["parties"]:
            key = (node_name, party["vehicle_name"], party["visit_id"])
            if key not in _STATE.actual_node_arrivals:
                party["actual_node_arrival_timestep"] = None
                continue
            party["actual_node_arrival_timestep"] = _STATE.actual_node_arrivals[key]


def _require_actual_passage_follows_arrival(
    node_name: str,
    visit_key,
    actual_arrival,
    actual_passage,
) -> None:
    if actual_arrival is None or actual_passage is None:
        return
    if type(actual_arrival) is not int or type(actual_passage) is not int:
        raise RuntimeError(
            f"Node {node_name}: arrival/passage types for {_visit_text(visit_key)} "
            f"are {actual_arrival!r} and {actual_passage!r}."
        )
    if actual_arrival < 0 or actual_passage < 0:
        raise RuntimeError(
            f"Node {node_name}: arrival/passage for {_visit_text(visit_key)} "
            f"are {actual_arrival!r} and {actual_passage!r}."
        )
    if actual_passage < actual_arrival + 1:
        raise RuntimeError(
            f"Node {node_name}: {_visit_text(visit_key)} actual passage "
            f"{actual_passage} is not after actual node arrival {actual_arrival}."
        )


def _require_stored_passages_follow_arrivals() -> None:
    for decision in _STATE.decisions.values():
        for party in decision["parties"]:
            _require_actual_passage_follows_arrival(
                decision["node_name"],
                party["visit_key_tuple"],
                party["actual_node_arrival_timestep"],
                party["actual_passage_timestep"],
            )


def _decision_output_sort_key(item):
    decision = item[1]
    return (
        decision["decision_timestep"],
        decision["node_name"],
        decision["candidate_identity"],
    )


def _freeze_transaction_row(decision):
    return _TvtMpFullRunTransactionAuditRow(
        decision_timestep=decision["decision_timestep"],
        node_name=decision["node_name"],
        candidate_identity=decision["candidate_identity"],
        right_of_entry_visit_key=decision["right_of_entry_visit_key"],
        right_of_entry_vehicle_name=decision["right_of_entry_vehicle_name"],
        right_of_entry_baseline_arrival_timestep=decision[
            "right_of_entry_baseline_arrival_timestep"
        ],
        right_of_entry_baseline_rank=decision["right_of_entry_baseline_rank"],
        buyer_count=decision["buyer_count"],
        seller_count=decision["seller_count"],
        nonparticipating_count=decision["nonparticipating_count"],
        trade_scope_count=decision["trade_scope_count"],
        buyer_visit_keys=decision["buyer_visit_keys"],
        seller_visit_keys=decision["seller_visit_keys"],
        nonparticipating_visit_keys=decision["nonparticipating_visit_keys"],
        baseline_order_visit_keys=decision["baseline_order_visit_keys"],
        candidate_order_visit_keys=decision["candidate_order_visit_keys"],
        total_G=decision["total_G"],
        total_R=decision["total_R"],
        surplus=decision["surplus"],
        economically_feasible=decision["economically_feasible"],
        infeasibility_reasons=decision["infeasibility_reasons"],
        fifo_inspection_passed=decision["fifo_inspection_passed"],
        fifo_violation_count=decision["fifo_violation_count"],
        trade_ex_post_evaluation_status=decision["trade_ex_post_evaluation_status"],
        actual_evaluation_available=decision["actual_evaluation_available"],
        max_same_inlink_party_count=decision["max_same_inlink_party_count"],
        max_same_inlink_buyer_count=decision["max_same_inlink_buyer_count"],
        max_same_inlink_seller_count=decision["max_same_inlink_seller_count"],
        max_same_inlink_nonparticipating_count=decision[
            "max_same_inlink_nonparticipating_count"
        ],
    )


def _freeze_visit_row(party):
    return _TvtMpFullRunVisitAuditRow(
        decision_timestep=party["decision_timestep"],
        node_name=party["node_name"],
        candidate_identity=party["candidate_identity"],
        visit_key=party["visit_key"],
        vehicle_name=party["vehicle_name"],
        visit_id=party["visit_id"],
        role=party["role"],
        is_right_of_entry_holder=party["is_right_of_entry_holder"],
        inlink_name=party["inlink_name"],
        formal_route_next_link_name=party["formal_route_next_link_name"],
        baseline_arrival_timestep=party["baseline_arrival_timestep"],
        actual_node_arrival_timestep=party["actual_node_arrival_timestep"],
        arrival_tiebreaker=party["arrival_tiebreaker"],
        baseline_local_rank=party["baseline_local_rank"],
        post_trade_local_rank=party["post_trade_local_rank"],
        assigned_rank=party["assigned_rank"],
        actual_node_passage_rank=party["actual_node_passage_rank"],
        baseline_passage_timestep=party["baseline_passage_timestep"],
        candidate_passage_timestep=party["candidate_passage_timestep"],
        actual_passage_timestep=party["actual_passage_timestep"],
        predicted_observation_status=party["predicted_observation_status"],
        actual_observation_status=party["actual_observation_status"],
        declared_vot_per_second=party["declared_vot_per_second"],
        true_vot_per_second=party["true_vot_per_second"],
        buyer_value_G_b=party["buyer_value_G_b"],
        seller_required_compensation_R_s=party["seller_required_compensation_R_s"],
        payment_P_b=party["payment_P_b"],
        compensation_C_s=party["compensation_C_s"],
        realized_gain=party["realized_gain"],
        realized_delay_loss=party["realized_delay_loss"],
        satisfaction_status=party["satisfaction_status"],
        binding_sequence_auxiliary_rank=party["binding_sequence_auxiliary_rank"],
        same_inlink_fifo_preserved=party["same_inlink_fifo_preserved"],
    )


def _freeze_audit_result():
    ordered = sorted(_STATE.decisions.items(), key=_decision_output_sort_key)
    transaction_rows = []
    visit_rows = []
    for _decision_key, decision in ordered:
        transaction_rows.append(_freeze_transaction_row(decision))
        for party in decision["parties"]:
            visit_rows.append(_freeze_visit_row(party))
    return _TvtMpFullRunAuditResult(
        transaction_rows=tuple(transaction_rows),
        visit_rows=tuple(visit_rows),
    )


def _restore_hooks() -> None:
    if _STATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = _STATE.original_run_tvt_mp_driver
    vehicle_module.Vehicle.record_order_control_node_arrival = (
        _STATE.original_record_order_control_node_arrival
    )
    _STATE.original_run_tvt_mp_driver = None
    _STATE.original_record_order_control_node_arrival = None
    _STATE.installed = False


def _clear_live_state() -> None:
    _STATE.real_world = None
    _STATE.decisions = {}
    _STATE.actual_node_arrivals = {}


def install_tvt_mp_full_run_audit(real_world):
    """Attach the two read-only hooks to one real World, once."""
    if _STATE.installed is True:
        raise RuntimeError("The full-run audit hook is already installed.")
    if real_world is None:
        raise RuntimeError("real_world is missing.")
    _STATE.real_world = real_world
    _STATE.decisions = {}
    _STATE.actual_node_arrivals = {}
    _STATE.original_run_tvt_mp_driver = driver_module.run_tvt_mp_driver
    _STATE.original_record_order_control_node_arrival = (
        vehicle_module.Vehicle.record_order_control_node_arrival
    )
    driver_module.run_tvt_mp_driver = _wrapped_run_tvt_mp_driver
    vehicle_module.Vehicle.record_order_control_node_arrival = (
        _wrapped_record_order_control_node_arrival
    )
    _STATE.installed = True


def finalize_tvt_mp_full_run_audit(real_world, research_output_bundle):
    """Join saved trades with research output and drop live objects."""
    if _STATE.installed is not True:
        raise RuntimeError("The full-run audit hook is not installed.")
    if real_world is not _STATE.real_world:
        raise RuntimeError("finalize received a different World from install.")
    _attach_research_output(research_output_bundle)
    _attach_node_continuous_ranks(real_world)
    _attach_actual_node_arrivals()
    _require_stored_passages_follow_arrivals()
    audit_result = _freeze_audit_result()
    _restore_hooks()
    _clear_live_state()
    return audit_result


def _write_one_csv(path: Path, columns, rows) -> None:
    if path.exists():
        raise FileExistsError(f"Audit CSV already exists: {path}.")
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(columns)
        for row in rows:
            cells = []
            for column_name in columns:
                cells.append(_csv_cell(getattr(row, column_name)))
            writer.writerow(cells)


def write_tvt_mp_full_run_audit_csv(audit_result, output_directory):
    """Write the transaction audit CSV and the visit audit CSV."""
    if not isinstance(audit_result, _TvtMpFullRunAuditResult):
        raise RuntimeError("audit_result is not the helper audit result.")
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    _write_one_csv(
        directory / TRANSACTION_AUDIT_CSV_NAME,
        TRANSACTION_AUDIT_COLUMNS,
        audit_result.transaction_rows,
    )
    _write_one_csv(
        directory / VISIT_AUDIT_CSV_NAME,
        VISIT_AUDIT_COLUMNS,
        audit_result.visit_rows,
    )


def _attribute_chain(node):
    names = []
    current = node
    while isinstance(current, ast.Attribute):
        names.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    names.append(current.id)
    names.reverse()
    return ".".join(names)


def _module_level_function_names(tree):
    names = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.append(node.name)
    return names


def _imported_module_names(tree):
    names = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                names.append("")
            else:
                names.append(node.module)
    return names


def _forbidden_source_fragments():
    fragments = []
    fragments.append("EAST_" + "NODE")
    fragments.append("WEST_" + "NODE")
    fragments.append("east_" + "intersection")
    fragments.append("west_" + "intersection")
    fragments.append("T" + "35")
    fragments.append("T" + "310")
    fragments.append("T" + "582")
    fragments.append("physical_" + "trace")
    fragments.append("candidate_" + "node_arrival")
    fragments.append("candidate_" + "arrival")
    fragments.append("vehicle_name" + "[:")
    fragments.append("actual_passage_timestep" + " - 1")
    fragments.append("actual_passage" + " - 1")
    fragments.append("passage_timestep" + " - 1")
    fragments.append(
        '["actual_node_arrival_timestep"] = '
        + 'party["baseline_arrival_timestep"]'
    )
    fragments.append(
        "actual_node_arrival_timestep" + " = baseline_arrival_timestep"
    )
    fragments.append("predecessor_" + "visit_keys")
    fragments.append("successor_" + "visit_keys")
    fragments.append("exec_" + "simulation")
    return fragments


def _require_public_functions(tree) -> None:
    names = _module_level_function_names(tree)
    expected = []
    for name in PUBLIC_AUDIT_FUNCTION_NAMES:
        expected.append(name)
    expected.append(STATIC_VALIDATION_FUNCTION_NAME)
    public_names = []
    for name in names:
        if name.startswith("_"):
            continue
        public_names.append(name)
    if tuple(public_names) != tuple(expected):
        raise RuntimeError(
            "Public helper functions are "
            f"{public_names!r}, not the three audit functions plus "
            "the static-contract function."
        )


def _require_reused_function_names(tree) -> None:
    names = _module_level_function_names(tree)
    required = (
        "_saved_driver_columns",
        "_build_parties",
        "_annotate_same_inlink_fifo",
        "_remember_real_world_node_arrival",
        "_wrapped_record_order_control_node_arrival",
        "_attach_research_output",
        "_attach_node_continuous_ranks",
    )
    for required_name in required:
        if required_name not in names:
            raise RuntimeError(f"Helper is missing {required_name}.")


def _require_allowed_imports(tree) -> None:
    imported = _imported_module_names(tree)
    allowed_production = set(ALLOWED_IMPORTED_MODULES)
    allowed_standard = set(ALLOWED_STANDARD_LIBRARY_MODULES)
    for module_name in imported:
        if module_name in allowed_standard:
            continue
        if module_name not in allowed_production:
            raise RuntimeError(
                f"Helper imports {module_name!r}, which is outside the read/hook list."
            )


def _require_hook_assignments_only(tree) -> None:
    allowed = set(ALLOWED_HOOK_ASSIGNMENTS)
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                targets.append(target)
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
        elif isinstance(node, ast.AugAssign):
            targets.append(node.target)
        for target in targets:
            if not isinstance(target, ast.Attribute):
                continue
            chain = _attribute_chain(target)
            if chain is None:
                continue
            if chain.startswith("driver_module.") or chain.startswith("vehicle_module."):
                if chain not in allowed:
                    raise RuntimeError(
                        f"Helper assigns production attribute {chain!r}."
                    )


def _require_no_production_file_write(tree) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute):
            if function.attr == "write_text" or function.attr == "write_bytes":
                raise RuntimeError("Helper writes a file through Path.write_text.")
        if isinstance(function, ast.Name) and function.id == "open":
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    if "uxsim" in argument.value:
                        raise RuntimeError(
                            "Helper opens a production path: "
                            f"{argument.value!r}."
                        )


def _require_forbidden_fragments_absent(source_text: str) -> None:
    for fragment in _forbidden_source_fragments():
        if fragment in source_text:
            raise RuntimeError(
                "Helper source contains a forbidden full-run contract fragment."
            )


def _require_column_fields_match() -> None:
    transaction_fields = tuple(_TvtMpFullRunTransactionAuditRow.__dataclass_fields__)
    visit_fields = tuple(_TvtMpFullRunVisitAuditRow.__dataclass_fields__)
    if transaction_fields != TRANSACTION_AUDIT_COLUMNS:
        raise RuntimeError("Transaction audit fields do not match the CSV columns.")
    if visit_fields != VISIT_AUDIT_COLUMNS:
        raise RuntimeError("Visit audit fields do not match the CSV columns.")


def validate_tvt_mp_full_run_audit_helper_static_contract():
    """Check this file's public surface and the excluded diagnostic contracts."""
    source_path = Path(__file__)
    source_text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    _require_public_functions(tree)
    _require_reused_function_names(tree)
    _require_allowed_imports(tree)
    _require_hook_assignments_only(tree)
    _require_no_production_file_write(tree)
    _require_forbidden_fragments_absent(source_text)
    _require_column_fields_match()
