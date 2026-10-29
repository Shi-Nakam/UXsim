"""
N=5 four-cross trial diagnostic at T=392 northwest_intersection (candidate limit activation).

Captures official state through T=430, compares selected-candidate facts against the
existing N=5 T=900 formal research CSVs, and writes research outputs.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from enum import Enum

SCRIPT_PATH = __file__
# Path insert uses the same layout as the N=5 trial: script dir, then repo root.
from pathlib import Path

_SCRIPT = Path(SCRIPT_PATH).resolve()
_SCRIPT_DIR = _SCRIPT.parent
_REPO_ROOT = _SCRIPT.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial as trial
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionStatus,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpCandidateEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalizationSource,
    OrderControlTvtNodeMpFinalRankResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_TIMESTEP = 392
TARGET_NODE_NAME = "northwest_intersection"
CONTEXT_START_TIMESTEP = 388
CONTEXT_END_TIMESTEP = 396
DIAGNOSTIC_END_TIMESTEP = 430
# exec_simulation(until_t) sets end_ts = int(until_t / DELTAT) and runs
# for W.T in range(start_ts, end_ts + 1), then executes W.T += 1.
# Last processed decision timestep is therefore end_ts, and World.T afterwards is end_ts + 1.
DIAGNOSTIC_LAST_PROCESSED_TIMESTEP = DIAGNOSTIC_END_TIMESTEP
EXPECTED_WORLD_T_AFTER_STOP = DIAGNOSTIC_LAST_PROCESSED_TIMESTEP + 1
TARGET_VISIT_TRACKING_END_TIMESTEP = DIAGNOSTIC_LAST_PROCESSED_TIMESTEP
FORMAL_EVALUATION_END_TIMESTEP = 899

SCENARIO_NAME = trial.SCENARIO_NAME
EXISTING_FULL_TRIAL_OUTPUT_DIR_NAME = trial.TRIAL_OUTPUT_DIR_NAME
EXISTING_FULL_TRIAL_OUTPUT_DIR = trial.TRIAL_OUTPUT_DIR
FORMAL_TRANSACTIONS_CSV = EXISTING_FULL_TRIAL_OUTPUT_DIR / "tvt_mp_transactions.csv"
FORMAL_VISITS_CSV = EXISTING_FULL_TRIAL_OUTPUT_DIR / "tvt_mp_visits.csv"

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_t392_limit_activation"
    )
)

FLOAT_REL_TOL = 1e-12
FLOAT_ABS_TOL = 1e-12
VISIT_KEY_SEPARATOR = "|"

T392_CONTEXT_TIMESTEPS_CSV = "t392_context_timesteps.csv"
T392_CONTEXT_CANDIDATES_CSV = "t392_context_candidates.csv"
T392_CONTEXT_FINAL_RANK_VISITS_CSV = "t392_context_final_rank_visits.csv"
T392_LIMIT_POPULATION_CSV = "t392_limit_population.csv"
T392_CONSIDERED_CANDIDATES_CSV = "t392_considered_candidates.csv"
T392_CONSIDERED_CANDIDATE_PARTIES_CSV = "t392_considered_candidate_parties.csv"
T392_CANDIDATE_SIDE_BY_SIDE_CSV = "t392_candidate_side_by_side.csv"
T392_SELECTED_BINDING_SEQUENCE_CSV = "t392_selected_binding_sequence.csv"
T392_FINAL_RANK_AND_BEYOND_LIMIT_CSV = "t392_final_rank_and_beyond_limit.csv"
T392_LIMIT_ACTIVATION_SUMMARY = "t392_limit_activation_summary.txt"
MANIFEST_JSON = "manifest.json"

OUTPUT_FILE_NAMES = (
    T392_CONTEXT_TIMESTEPS_CSV,
    T392_CONTEXT_CANDIDATES_CSV,
    T392_CONTEXT_FINAL_RANK_VISITS_CSV,
    T392_LIMIT_POPULATION_CSV,
    T392_CONSIDERED_CANDIDATES_CSV,
    T392_CONSIDERED_CANDIDATE_PARTIES_CSV,
    T392_CANDIDATE_SIDE_BY_SIDE_CSV,
    T392_SELECTED_BINDING_SEQUENCE_CSV,
    T392_FINAL_RANK_AND_BEYOND_LIMIT_CSV,
    T392_LIMIT_ACTIVATION_SUMMARY,
    MANIFEST_JSON,
)

STATUS_PRESENT = "present"
REASON_BEYOND_LIMIT = "beyond_limit_not_in_candidate_set"
REASON_NO_CANDIDATE_EVALUATION = "no_candidate_evaluation_for_visit"
REASON_CANDIDATE_NOT_SELECTED = "candidate_not_selected"
REASON_UNRESOLVED = "candidate_calculation_unresolved"
REASON_ARRIVAL_NOT_OBSERVED = "actual_arrival_not_observed_by_diagnostic_end"
REASON_PASSAGE_NOT_OBSERVED = "actual_passage_not_observed_by_diagnostic_end"
REASON_NOT_STORED = "value_not_stored_in_official_object"
REASON_NOT_LOADED_THIS_PASS = "not_loaded_in_data_capture_pass"
REASON_EX_POST_FROM_FORMAL_CSV = "loaded_from_existing_t900_formal_csv_after_match"
REASON_EX_POST_NOT_SELECTED = "candidate_not_selected_ex_post_not_from_csv"
SUMMARY_NOT_IN_BINDING_SEQUENCE = "not_in_binding_sequence"

SOURCE_ARRIVED = "already_arrived_undetermined_confirmation"
SOURCE_LEADING = "leading_nonparticipating_confirmation"
SOURCE_SELECTED = "selected_candidate_final_rank"
SOURCE_BASELINE_FALLBACK = "baseline_fallback_final_rank"
SOURCE_SELECTED_OUTSIDE = "selected_candidate_outside_trade_scope_baseline_rank"


@dataclass
class TimedField:
    value: int | None
    status: str


@dataclass
class RankMembershipSnapshot:
    confirmed_keys: frozenset
    undetermined_keys: frozenset
    rank_by_visit: dict


@dataclass
class SavedOfficialColumns:
    atomic_apply_result: object
    collector: OrderControlBaselineCollector
    arrived_confirmation_result: object
    leading_confirmation_result: object
    right_of_entry_selection_result: object
    candidate_visit_set_result: object
    inlink_physical_order_result: object
    concrete_buyer_candidate_set_result: object
    general_trade_rank_result: object
    local_virtual_calculation_set_result: object
    economic_evaluation_set_result: object
    candidate_selection_set_result: object
    payment_and_compensation_set_result: object
    final_rank_set_result: object
    arrived_node: object
    leading_node: object
    right_of_entry_node: object
    candidate_visit_node: object
    economic_node: object
    selection_node: object
    trade_rank_node: object
    local_virtual_node: object
    final_rank_node: object


@dataclass
class ContextTimestepRecord:
    timestep: int
    right_of_entry_selection_status: object
    right_of_entry_visit_key: tuple | None
    decision_window_visit_keys: tuple
    confirmed_leading_nonparticipating_visit_keys: tuple
    remaining_decision_window_visit_keys: tuple
    candidate_visit_set_build_status: object
    p_minus_one_eligible_visit_count_before_limit: int | None
    candidate_visits: tuple
    candidate_visit_count_after_limit: int
    limit_activated: bool | None
    considered_candidate_count: int
    selected_candidate_present: bool
    selected_evaluation_index: int | None
    final_rank_status: object
    final_rank_visit_keys: tuple
    newly_confirmed_visit_keys: tuple
    already_confirmed_rank_changed: bool


@dataclass
class ContextCandidateRecord:
    timestep: int
    evaluation_index: int
    candidate_identity: str
    selected: bool
    buyers_sorted: tuple
    buyer_count: int
    seller_count: int
    nonparticipating_count: int
    trade_scope_count: int
    total_G: float | None
    total_R: float | None
    surplus: float | None
    economically_feasible: bool | None
    unresolved: bool
    unresolved_reasons: tuple
    infeasibility_reasons: tuple
    selection_reason: str


@dataclass
class ContextFinalRankVisitRecord:
    timestep: int
    final_rank_status: object
    visit_key: tuple
    final_local_rank: int
    finalization_source: object
    formal_route_next_link_name: str
    route_origin: object
    assigned_c_rank_after_apply: int | None
    newly_confirmed_at_this_timestep: bool


@dataclass
class PrelimitVisitRecord:
    baseline_order: int
    vehicle_name: str
    visit_id: int
    visit_key: tuple
    baseline_arrival_timestep: int | None
    baseline_passage_timestep: int | None
    arrival_tiebreaker: object
    vehicle_id: int
    within_limit: bool
    beyond_limit: bool
    right_of_entry: bool
    in_candidate_visits: bool
    in_selected_trade_scope: bool
    assigned_c_rank_after_t392: int | None
    baseline_arrival: TimedField
    candidate_arrival: TimedField
    actual_first_arrival: TimedField
    baseline_passage: TimedField
    candidate_passage: TimedField
    actual_passage: TimedField


@dataclass
class PartyRecord:
    evaluation_index: int
    candidate_identity: str
    candidate_selected: bool
    vehicle_name: str
    visit_id: int
    visit_key: tuple
    role: str
    participates_in_order_exchange: bool | None
    formal_inlink_name: str | None
    predicted_route_next_link_name: str | None
    baseline_local_rank: int | None
    baseline_local_rank_status: str
    candidate_local_rank: int | None
    candidate_local_rank_status: str
    binding_rank: int | None
    binding_partition: str | None
    right_of_entry_holder: bool
    in_trade_scope: bool
    outside_partition: bool
    baseline_arrival: TimedField
    candidate_arrival: TimedField
    actual_first_arrival: TimedField
    baseline_passage: TimedField
    candidate_passage: TimedField
    actual_passage: TimedField
    declared_vot_per_second: float | None
    true_vot_per_second: float | None
    expected_time_saving_timesteps: int | None
    gross_time_value_G_b: float | None
    passes_positive_buyer_value_condition: bool | None
    buyer_condition_status: str
    expected_waiting_increase_timesteps: int | None
    required_compensation_R_s: float | None
    seller_condition_status: str
    predicted_signed_time_value_change: float | None
    nonparticipating_external_effect_status: str
    actual_observation_available_for_visit: bool
    actual_is_not_realization_of_this_candidate: bool
    actual_comparison_interpretation: str
    official_payment: object
    official_compensation: object
    reference_payment: object
    reference_compensation: object
    realized_time_value: object
    realized_delay_loss: object
    realized_gain: object
    satisfaction_status: object
    satisfaction_reason: object
    assigned_c_rank: int | None
    actual_node_passage_rank: int | None
    candidate_route_next_link_name: str | None
    actual_route_next_link_name: str | None
    formal_route_next_link_name: str | None
    ex_post_fields_status: str


@dataclass
class ConsideredCandidateRecord:
    evaluation_index: int
    candidate_identity: str
    selected: bool
    local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult
    economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult | None
    buyers_sorted: tuple
    right_of_entry_visit_key: tuple | None
    buyer_visit_keys: tuple
    seller_visit_keys: tuple
    nonparticipating_visit_keys: tuple
    trade_scope_visit_keys: tuple
    buyer_count: int
    seller_count: int
    nonparticipating_count: int
    trade_scope_count: int
    baseline_local_order: tuple
    candidate_local_order: tuple
    baseline_local_rank_by_visit_key: dict
    candidate_local_rank_by_visit_key: dict
    trade_result: OrderControlTvtMpGeneralTradeRankResult
    binding_sequence: object
    trade_scope_of_this_candidate_visits: tuple
    outside_trade_scope_inside_k_fixed_visits: tuple
    k_last_buyer: int
    k_decision_window: int
    k_fixed: int
    candidate_build_status: object
    local_virtual_calculation_stop_reason: object
    resolved: bool
    unresolved: bool
    unresolved_reasons: tuple
    traffic_observation_count: int
    candidate_passage_missing_visit_keys: tuple
    candidate_route_missing_visit_keys: tuple
    total_G: float | None
    total_R: float | None
    surplus: float | None
    economically_feasible: bool | None
    candidate_infeasibility_reasons: tuple
    selection_status: object
    selection_reason_status: str
    parties: list


@dataclass
class FinalRankVisitRecord:
    visit_key: tuple
    final_local_rank: int
    finalization_source: object
    formal_route_next_link_name: str
    route_origin: object
    baseline_arrival: TimedField
    candidate_arrival: TimedField
    actual_first_arrival: TimedField
    baseline_passage: TimedField
    candidate_passage: TimedField
    actual_passage: TimedField
    assigned_c_rank: int | None


@dataclass
class BeyondLimitConfirmationRecord:
    visit_key: tuple
    in_t392_final_rank: bool
    assigned_c_rank_at_t392: int | None
    t392_finalization_source: object | None
    t392_final_rank_status: object | None
    confirmed_by_diagnostic_end: bool
    confirmation_decision_timestep: int | None
    node_name: str | None
    assigned_c_rank: int | None
    finalization_source: str | None
    final_rank_status: object | None
    source_selected_candidate: bool
    source_baseline_fallback: bool
    source_leading_nonparticipating: bool
    source_arrived_undetermined: bool
    last_checked_timestep: int | None
    last_official_state: str
    unresolved_reason: str | None


@dataclass
class RankHistoryEntry:
    timestep: int
    visit_key: tuple
    assigned_rank: int
    first_assignment: bool
    source: str | None


@dataclass
class RankOverwrite:
    timestep: int
    visit_key: tuple
    previous_rank: int
    new_rank: int


@dataclass
class DiagnosticState:
    real_world: object | None = None
    original_driver: object | None = None
    original_arrival: object | None = None
    installed: bool = False
    context_records: list = field(default_factory=list)
    context_candidate_records: list = field(default_factory=list)
    context_final_rank_visit_records: list = field(default_factory=list)
    formal_csv_comparison_result: str | None = None
    output_table_contracts_validated: bool = False
    t392_columns: SavedOfficialColumns | None = None
    t392_candidate_visit_node: object | None = None
    t392_prelimit_visits: list = field(default_factory=list)
    t392_within_limit_visit_keys: tuple = ()
    t392_beyond_limit_visit_keys: tuple = ()
    t392_considered_candidates: list = field(default_factory=list)
    t392_selected_candidate: ConsideredCandidateRecord | None = None
    t392_binding_sequence: object | None = None
    t392_final_rank_result: object | None = None
    t392_final_rank_visits: list = field(default_factory=list)
    actual_first_arrival_by_visit_key: dict = field(default_factory=dict)
    target_visit_keys: set = field(default_factory=set)
    beyond_limit_confirmations: dict = field(default_factory=dict)
    rank_history: list = field(default_factory=list)
    rank_overwrites: list = field(default_factory=list)
    current_rank_by_visit_key: dict = field(default_factory=dict)
    first_rank_by_visit_key: dict = field(default_factory=dict)
    diagnostic_last_processed_timestep: int = DIAGNOSTIC_LAST_PROCESSED_TIMESTEP
    world_t_after_stop: int | None = None
    t392_capture_count: int = 0
    pending_rank_snapshot: RankMembershipSnapshot | None = None


STATE = DiagnosticState()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _decision_label() -> str:
    return f"T={TARGET_TIMESTEP} {TARGET_NODE_NAME}"


def _require_python_int(value, label: str) -> int:
    if type(value) is not int:
        raise RuntimeError(f"{label} must be a Python int, not bool; got {value!r}.")
    return value


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _present(value: int | None) -> TimedField:
    if value is None:
        return TimedField(None, REASON_NOT_STORED)
    return TimedField(value, STATUS_PRESENT)


def _missing(reason: str) -> TimedField:
    return TimedField(None, reason)


def _one_node(results, node_name: str, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"{label} count for {node_name} is {count}.")
    return matched


def _saved_columns(atomic) -> SavedOfficialColumns:
    validation_set = atomic.final_consistency_validation_set_result
    final_rank_set = validation_set.final_rank_set_result
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection_set = payment_set.candidate_selection_set_result
    economic_set = selection_set.economic_evaluation_set_result
    local_set = economic_set.local_virtual_calculation_set_result
    fifo_set = local_set.fifo_inspection_set_result
    trade_rank_set = fifo_set.general_trade_rank_set_result
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    inlink_set = concrete_set.inlink_candidate_physical_order_result
    candidate_set = inlink_set.candidate_visit_set_result
    right_set = candidate_set.right_of_entry_selection_result
    leading_set = right_set.leading_confirmation_result
    arrived_set = leading_set.arrived_confirmation_result
    fork_result = arrived_set.alignment_fork_result.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError("Saved fork_result type is wrong.")
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError("Saved collector type is wrong.")
    return SavedOfficialColumns(
        atomic_apply_result=atomic,
        collector=collector,
        arrived_confirmation_result=arrived_set,
        leading_confirmation_result=leading_set,
        right_of_entry_selection_result=right_set,
        candidate_visit_set_result=candidate_set,
        inlink_physical_order_result=inlink_set,
        concrete_buyer_candidate_set_result=concrete_set,
        general_trade_rank_result=trade_rank_set,
        local_virtual_calculation_set_result=local_set,
        economic_evaluation_set_result=economic_set,
        candidate_selection_set_result=selection_set,
        payment_and_compensation_set_result=payment_set,
        final_rank_set_result=final_rank_set,
        arrived_node=_one_node(arrived_set.node_confirmation_results, TARGET_NODE_NAME, "arrived"),
        leading_node=_one_node(leading_set.node_confirmation_results, TARGET_NODE_NAME, "leading"),
        right_of_entry_node=_one_node(right_set.node_selection_results, TARGET_NODE_NAME, "right of entry"),
        candidate_visit_node=_one_node(candidate_set.node_candidate_set_results, TARGET_NODE_NAME, "candidate visits"),
        economic_node=_one_node(economic_set.node_economic_evaluation_results, TARGET_NODE_NAME, "economic"),
        selection_node=_one_node(selection_set.node_candidate_selection_results, TARGET_NODE_NAME, "selection"),
        trade_rank_node=_one_node(trade_rank_set.node_trade_rank_results, TARGET_NODE_NAME, "trade rank"),
        local_virtual_node=_one_node(local_set.node_local_virtual_calculation_results, TARGET_NODE_NAME, "local virtual"),
        final_rank_node=_one_node(final_rank_set.node_final_rank_results, TARGET_NODE_NAME, "final rank"),
    )


def _rank_state(world) -> OrderControlTvtNodeRankState:
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        raise RuntimeError("Rank state map is missing.")
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError("Northwest rank state is missing.")
    return rank_state


def _snapshot_rank_membership(world) -> RankMembershipSnapshot:
    rank_state = _rank_state(world)
    rank_by_visit = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        rank_by_visit[plain] = rank_state.assigned_rank(visit_key)
    confirmed = frozenset(rank_by_visit)
    undetermined = frozenset(_plain_visit_key(visit_key) for visit_key in rank_state.undetermined_visit_keys())
    return RankMembershipSnapshot(confirmed, undetermined, rank_by_visit)


def _role_name(role) -> str:
    if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return "buyer"
    if role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return "seller"
    if role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return "nonparticipating"
    if role is OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE:
        return "outside_trade_scope"
    raise RuntimeError(f"Unsupported trade role {role!r}.")


def _participation(world, vehicle_name: str):
    vehicles = getattr(world, "VEHICLES", None)
    if not isinstance(vehicles, dict):
        return None
    vehicle = vehicles.get(vehicle_name)
    if vehicle is None:
        return None
    participates = getattr(vehicle, "participates_in_order_exchange", None)
    if type(participates) is not bool:
        return None
    return participates


def _true_vot(world, vehicle_name: str):
    vehicles = getattr(world, "VEHICLES", None)
    if not isinstance(vehicles, dict):
        return None
    vehicle = vehicles.get(vehicle_name)
    if vehicle is None:
        return None
    return getattr(vehicle, "vot_true", None)


def _formal_arrival_timestep(arrival_time, deltat) -> int:
    formal_timestep = int(round(arrival_time / deltat))
    if type(formal_timestep) is bool or formal_timestep < 0:
        raise RuntimeError(f"Formal arrival timestep is {formal_timestep!r}.")
    return formal_timestep


def _keys_of(visits) -> tuple:
    keys = []
    for visit in visits:
        keys.append(_plain_visit_key(visit.visit_key))
    return tuple(keys)


def _classify_confirmation_source(columns: SavedOfficialColumns, visit_key) -> str | None:
    arrived_keys = {_plain_visit_key(item) for item in columns.arrived_node.confirmed_arrived_visit_keys}
    if visit_key in arrived_keys:
        return SOURCE_ARRIVED
    leading_keys = {
        _plain_visit_key(item)
        for item in columns.leading_node.confirmed_leading_nonparticipating_visit_keys
    }
    if visit_key in leading_keys:
        return SOURCE_LEADING
    final_node = columns.final_rank_node
    matched = None
    for record in final_node.final_rank_visits:
        if _plain_visit_key(record.visit_key) == visit_key:
            matched = record
    if matched is None:
        return None
    if matched.finalization_source is OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE:
        return SOURCE_SELECTED
    if matched.finalization_source is OrderControlTvtMpFinalizationSource.BASELINE:
        if final_node.final_rank_status is OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS:
            return SOURCE_BASELINE_FALLBACK
        if final_node.final_rank_status is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
            return SOURCE_SELECTED_OUTSIDE
    raise RuntimeError(
        f"{_visit_text(visit_key)} has an unclassified finalization source "
        f"{matched.finalization_source!r} / {final_node.final_rank_status!r}."
    )


def _require_driver_result(result) -> OrderControlTvtMpDriverResult:
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"Driver result type is {type(result).__name__}.")
    if result.atomic_apply_set_result is None:
        raise RuntimeError("Driver result has no atomic apply result.")
    return result


def _append_context_candidate_records(world, columns: SavedOfficialColumns, selected_index: int | None) -> None:
    selected_economic = columns.selection_node.selected_candidate_economic_result
    index = 0
    for local_result in columns.local_virtual_node.candidate_local_virtual_calculation_results:
        index = index + 1
        buyers_sorted = tuple(
            _plain_visit_key(visit_key)
            for visit_key in local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        identity = f"T={world.T}|{TARGET_NODE_NAME}|index={index}|" + VISIT_KEY_SEPARATOR.join(
            _visit_text(visit_key) for visit_key in buyers_sorted
        )
        economic = None
        for candidate_economic in columns.economic_node.candidate_economic_evaluation_results:
            if candidate_economic.candidate_local_virtual_calculation_result is local_result:
                economic = candidate_economic
                break
        selected = economic is not None and economic is selected_economic
        sequence = local_result.binding_rank_sequence
        buyers, sellers, nonparticipating = _role_keys(sequence)
        trade_scope = _keys_of(sequence.trade_scope_of_this_candidate_visits)
        if economic is None:
            total_g = None
            total_r = None
            surplus = None
            feasible = None
            reasons = ()
            selection_reason = (
                REASON_UNRESOLVED if local_result.resolved is not True else REASON_NOT_STORED
            )
        else:
            total_g = economic.total_buyer_value_G
            total_r = economic.total_required_compensation_R
            surplus = economic.surplus
            feasible = economic.economically_feasible
            reasons = tuple(economic.infeasibility_reasons)
            selection_reason = STATUS_PRESENT if selected is True else REASON_NOT_STORED
        STATE.context_candidate_records.append(
            ContextCandidateRecord(
                timestep=world.T,
                evaluation_index=index,
                candidate_identity=identity,
                selected=selected,
                buyers_sorted=buyers_sorted,
                buyer_count=len(buyers),
                seller_count=len(sellers),
                nonparticipating_count=len(nonparticipating),
                trade_scope_count=len(trade_scope),
                total_G=total_g,
                total_R=total_r,
                surplus=surplus,
                economically_feasible=feasible,
                unresolved=local_result.resolved is not True,
                unresolved_reasons=tuple(local_result.unresolved_reasons),
                infeasibility_reasons=reasons,
                selection_reason=selection_reason,
            )
        )


def _record_context(world, columns: SavedOfficialColumns, before: RankMembershipSnapshot) -> None:
    candidate_node = columns.candidate_visit_node
    candidate_visits = tuple(candidate_node.candidate_visits)
    count_before = candidate_node.p_minus_one_eligible_visit_count_before_limit
    limit_activated = None
    if type(count_before) is int:
        limit_activated = count_before > trial.MAX_CANDIDATE_VISIT_COUNT
    selected = columns.selection_node.selected_candidate_economic_result
    selected_index = None
    if selected is not None:
        index = 0
        for economic in columns.economic_node.candidate_economic_evaluation_results:
            index = index + 1
            if economic is selected:
                selected_index = index
    after = _snapshot_rank_membership(world)
    newly = []
    changed = False
    for visit_key, rank_value in after.rank_by_visit.items():
        if visit_key not in before.rank_by_visit:
            newly.append(visit_key)
        elif before.rank_by_visit[visit_key] != rank_value:
            changed = True
    final_keys = tuple(_plain_visit_key(record.visit_key) for record in columns.final_rank_node.final_rank_visits)
    right_key = columns.right_of_entry_node.right_of_entry_visit_key
    newly_set = set(newly)
    _append_context_candidate_records(world, columns, selected_index)
    for record in columns.final_rank_node.final_rank_visits:
        visit_key = _plain_visit_key(record.visit_key)
        STATE.context_final_rank_visit_records.append(
            ContextFinalRankVisitRecord(
                timestep=world.T,
                final_rank_status=columns.final_rank_node.final_rank_status,
                visit_key=visit_key,
                final_local_rank=record.final_local_rank,
                finalization_source=record.finalization_source,
                formal_route_next_link_name=record.formal_route_next_link_name,
                route_origin=record.route_origin,
                assigned_c_rank_after_apply=after.rank_by_visit.get(visit_key),
                newly_confirmed_at_this_timestep=visit_key in newly_set,
            )
        )
    STATE.context_records.append(
        ContextTimestepRecord(
            timestep=world.T,
            right_of_entry_selection_status=columns.right_of_entry_node.selection_status,
            right_of_entry_visit_key=None if right_key is None else _plain_visit_key(right_key),
            decision_window_visit_keys=tuple(
                _plain_visit_key(item) for item in columns.leading_node.decision_window_visit_keys
            ),
            confirmed_leading_nonparticipating_visit_keys=tuple(
                _plain_visit_key(item)
                for item in columns.leading_node.confirmed_leading_nonparticipating_visit_keys
            ),
            remaining_decision_window_visit_keys=tuple(
                _plain_visit_key(item)
                for item in columns.leading_node.remaining_decision_window_visit_keys
            ),
            candidate_visit_set_build_status=candidate_node.build_status,
            p_minus_one_eligible_visit_count_before_limit=count_before,
            candidate_visits=candidate_visits,
            candidate_visit_count_after_limit=len(candidate_visits),
            limit_activated=limit_activated,
            considered_candidate_count=len(columns.local_virtual_node.candidate_local_virtual_calculation_results),
            selected_candidate_present=selected is not None,
            selected_evaluation_index=selected_index,
            final_rank_status=columns.final_rank_node.final_rank_status,
            final_rank_visit_keys=final_keys,
            newly_confirmed_visit_keys=tuple(newly),
            already_confirmed_rank_changed=changed,
        )
    )


def _restore_prelimit_entries(columns: SavedOfficialColumns, before: RankMembershipSnapshot) -> list:
    """Rebuild the P-1 eligible column with the same filters as candidate-visit construction.

    The saved result stores the count and the limited head, not the visits past the limit.
    Eligibility uses the rank ledger from immediately before this driver call, because
    the call itself confirms new ranks before the wrapper reads the result.
    """
    candidate_node = columns.candidate_visit_node
    right_key = candidate_node.right_of_entry_visit_key
    if right_key is None:
        raise RuntimeError("T=392 candidate visit result has no right-of-entry.")
    right_plain = _plain_visit_key(right_key)
    right_record = columns.collector.get_baseline_visit_snapshot(right_plain[0], right_plain[1])
    if right_record is None:
        raise RuntimeError("Collector has no right-of-entry snapshot.")
    passage_timestep = right_record["baseline_passage_timestep"]
    if type(passage_timestep) is not int or type(passage_timestep) is bool:
        raise RuntimeError("Right-of-entry baseline passage is not an int.")
    exported = columns.collector.export_node_baseline_visits(TARGET_NODE_NAME)
    eligible = []
    for record in exported:
        vehicle_name = record["vehicle_name"]
        visit_id = record["visit_id"]
        if type(vehicle_name) is not str or vehicle_name == "":
            raise RuntimeError("Collector vehicle_name is empty.")
        if type(visit_id) is not int or type(visit_id) is bool or visit_id < 1:
            raise RuntimeError("Collector visit_id is not a positive int.")
        visit_key = (vehicle_name, visit_id)
        if record["node_name"] != TARGET_NODE_NAME:
            raise RuntimeError(f"{_visit_text(visit_key)} collector node_name differs.")
        arrived = record["was_arrived_at_snapshot"]
        if type(arrived) is not bool:
            raise RuntimeError(f"{_visit_text(visit_key)} was_arrived_at_snapshot is not bool.")
        if arrived is True:
            continue
        if visit_key in before.undetermined_keys:
            pass
        elif visit_key in before.confirmed_keys:
            continue
        else:
            raise RuntimeError(
                f"{_visit_text(visit_key)} was neither undetermined nor confirmed before T=392."
            )
        arrival = record["baseline_arrival_timestep"]
        if arrival is None:
            continue
        if type(arrival) is not int or type(arrival) is bool or arrival < 0:
            raise RuntimeError(f"{_visit_text(visit_key)} baseline arrival is not a non-negative int.")
        if arrival > passage_timestep - 1:
            continue
        eligible.append(record)
    eligible.sort(
        key=lambda record: (
            record["baseline_arrival_timestep"],
            record["arrival_tiebreaker"],
            record["vehicle_id"],
        )
    )
    return eligible


def _selected_trade_scope_keys(selected: ConsideredCandidateRecord | None) -> set:
    if selected is None:
        return set()
    return set(selected.trade_scope_visit_keys)


def _build_prelimit_records(
    columns: SavedOfficialColumns,
    before: RankMembershipSnapshot,
    world,
    selected: ConsideredCandidateRecord | None,
) -> list:
    eligible = _restore_prelimit_entries(columns, before)
    stored_count = columns.candidate_visit_node.p_minus_one_eligible_visit_count_before_limit
    if len(eligible) != stored_count:
        raise RuntimeError(
            f"Restored P-1 count {len(eligible)} != stored {stored_count}."
        )
    candidate_visits = tuple(columns.candidate_visit_node.candidate_visits)
    if len(candidate_visits) != trial.MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("candidate_visits length is not 5.")
    head_keys = []
    for record in eligible[: trial.MAX_CANDIDATE_VISIT_COUNT]:
        head_keys.append((record["vehicle_name"], record["visit_id"]))
    for index, candidate_visit in enumerate(candidate_visits):
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError("candidate_visits entry type is wrong.")
        if _plain_visit_key(candidate_visit.visit_key) != head_keys[index]:
            raise RuntimeError("Restored head does not match candidate_visits.")
    right_key = _plain_visit_key(columns.candidate_visit_node.right_of_entry_visit_key)
    if _plain_visit_key(candidate_visits[0].visit_key) != right_key:
        raise RuntimeError("Right-of-entry is not candidate_visits[0].")
    after = _snapshot_rank_membership(world)
    trade_scope = _selected_trade_scope_keys(selected)
    rows = []
    order = 0
    for record in eligible:
        order = order + 1
        visit_key = (record["vehicle_name"], record["visit_id"])
        within = order <= trial.MAX_CANDIDATE_VISIT_COUNT
        beyond = within is not True
        in_candidate = visit_key in set(head_keys)
        if within is True and in_candidate is not True:
            raise RuntimeError(f"{_visit_text(visit_key)} is within the head but not in candidate_visits.")
        if beyond is True and in_candidate is True:
            raise RuntimeError(f"{_visit_text(visit_key)} is beyond the limit and also in candidate_visits.")
        rows.append(
            PrelimitVisitRecord(
                baseline_order=order,
                vehicle_name=visit_key[0],
                visit_id=visit_key[1],
                visit_key=visit_key,
                baseline_arrival_timestep=record["baseline_arrival_timestep"],
                baseline_passage_timestep=record["baseline_passage_timestep"],
                arrival_tiebreaker=record["arrival_tiebreaker"],
                vehicle_id=record["vehicle_id"],
                within_limit=within,
                beyond_limit=beyond,
                right_of_entry=visit_key == right_key,
                in_candidate_visits=in_candidate,
                in_selected_trade_scope=visit_key in trade_scope,
                assigned_c_rank_after_t392=after.rank_by_visit.get(visit_key),
                baseline_arrival=_present(record["baseline_arrival_timestep"]),
                candidate_arrival=_missing(REASON_NOT_STORED),
                actual_first_arrival=_missing(REASON_ARRIVAL_NOT_OBSERVED),
                baseline_passage=_present(record["baseline_passage_timestep"])
                if record["baseline_passage_timestep"] is not None
                else _missing(REASON_NOT_STORED),
                candidate_passage=_missing(
                    REASON_BEYOND_LIMIT if beyond is True else REASON_NO_CANDIDATE_EVALUATION
                ),
                actual_passage=_missing(REASON_PASSAGE_NOT_OBSERVED),
            )
        )
    return rows


def _prelimit_head_visit_keys(columns: SavedOfficialColumns, before: RankMembershipSnapshot) -> tuple:
    eligible = _restore_prelimit_entries(columns, before)
    if len(eligible) < trial.MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError(
            f"{_decision_label()}: restored P-1 column has fewer than "
            f"{trial.MAX_CANDIDATE_VISIT_COUNT} visits."
        )
    head_keys = []
    for record in eligible[: trial.MAX_CANDIDATE_VISIT_COUNT]:
        head_keys.append((record["vehicle_name"], record["visit_id"]))
    return tuple(head_keys)


def _baseline_local_rank_material(
    candidate_visit_node,
    prelimit_head_visit_keys: tuple,
) -> tuple[tuple, dict]:
    label = _decision_label()
    candidate_visits = candidate_visit_node.candidate_visits
    ordered_visit_keys = []
    baseline_rank_by_visit_key = {}
    position = 0
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"{label}: candidate_visits entry is {type(candidate_visit).__name__}."
            )
        position = position + 1
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in baseline_rank_by_visit_key:
            raise RuntimeError(f"{label}: candidate_visits repeats {_visit_text(visit_key)}.")
        ordered_visit_keys.append(visit_key)
        baseline_rank_by_visit_key[visit_key] = position
    if len(ordered_visit_keys) != trial.MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError(
            f"{label}: candidate_visits count is {len(ordered_visit_keys)}, not "
            f"{trial.MAX_CANDIDATE_VISIT_COUNT}."
        )
    expected_ranks = list(range(1, trial.MAX_CANDIDATE_VISIT_COUNT + 1))
    if sorted(baseline_rank_by_visit_key.values()) != expected_ranks:
        raise RuntimeError(f"{label}: baseline local ranks are not 1..{trial.MAX_CANDIDATE_VISIT_COUNT}.")
    right_key = candidate_visit_node.right_of_entry_visit_key
    if right_key is None:
        raise RuntimeError(f"{label}: right-of-entry VisitKey is missing.")
    right_plain = _plain_visit_key(right_key)
    if baseline_rank_by_visit_key.get(right_plain) != 1:
        raise RuntimeError(f"{label}: right-of-entry is not baseline local rank 1.")
    if tuple(ordered_visit_keys) != prelimit_head_visit_keys:
        raise RuntimeError(
            f"{label}: candidate_visits order does not match the pre-limit formal head."
        )
    return tuple(ordered_visit_keys), baseline_rank_by_visit_key


def _matching_trade_result(
    trade_rank_node: OrderControlTvtNodeMpGeneralTradeRankResult,
    buyers_sorted: tuple,
) -> OrderControlTvtMpGeneralTradeRankResult:
    label = _decision_label()
    if not isinstance(trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError(
            f"{label}: node trade rank result is {type(trade_rank_node).__name__}."
        )
    found = None
    for trade_result in trade_rank_node.candidate_trade_rank_results:
        candidate_buyers = tuple(
            _plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted
        )
        if candidate_buyers != buyers_sorted:
            continue
        if found is not None:
            raise RuntimeError(f"{label}: two general trade rank results share the same buyers.")
        found = trade_result
    if found is None:
        raise RuntimeError(f"{label}: no general trade rank result matches the candidate buyers.")
    if not isinstance(found, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(f"{label}: matched trade rank result has wrong type.")
    return found


def _trade_result_role_material(trade_result: OrderControlTvtMpGeneralTradeRankResult) -> tuple:
    buyers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted)
    sellers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.sellers_sorted)
    nonparticipating_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.nonparticipating_visits_sorted
    )
    trade_scope = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.trade_scope)
    return buyers_sorted, sellers_sorted, nonparticipating_sorted, trade_scope


def _assert_binding_roles_match_trade_result(
    binding_buyers: tuple,
    binding_sellers: tuple,
    binding_nonparticipating: tuple,
    binding_trade_scope: tuple,
    trade_result: OrderControlTvtMpGeneralTradeRankResult,
    candidate_index: int,
) -> None:
    label = _decision_label()
    official_buyers, official_sellers, official_nonparticipating, official_scope = (
        _trade_result_role_material(trade_result)
    )
    if set(binding_buyers) != set(official_buyers):
        raise RuntimeError(
            f"{label}: candidate {candidate_index} binding buyers differ from trade result."
        )
    if set(binding_sellers) != set(official_sellers):
        raise RuntimeError(
            f"{label}: candidate {candidate_index} binding sellers differ from trade result."
        )
    if set(binding_nonparticipating) != set(official_nonparticipating):
        raise RuntimeError(
            f"{label}: candidate {candidate_index} binding nonparticipating visits differ "
            "from trade result."
        )
    if set(binding_trade_scope) != set(official_scope):
        raise RuntimeError(
            f"{label}: candidate {candidate_index} binding trade scope differs from trade result."
        )
    expected_scope = official_buyers + official_sellers + official_nonparticipating
    if len(official_scope) != len(expected_scope) or set(official_scope) != set(expected_scope):
        raise RuntimeError(f"{label}: trade_result.trade_scope is not the role Visit set.")


def _candidate_local_rank_material(
    trade_result: OrderControlTvtMpGeneralTradeRankResult,
    baseline_ordered_visit_keys: tuple,
) -> tuple[tuple, dict]:
    label = _decision_label()
    if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(f"{label}: trade rank result is {type(trade_result).__name__}.")
    candidate_ordered_visit_keys = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.trade_order
    )
    baseline_set = set(baseline_ordered_visit_keys)
    if set(candidate_ordered_visit_keys) != baseline_set:
        raise RuntimeError(f"{label}: trade_order VisitKeys differ from saved candidate_visits.")
    if len(candidate_ordered_visit_keys) != len(set(candidate_ordered_visit_keys)):
        raise RuntimeError(f"{label}: trade_order repeats a VisitKey.")
    candidate_rank_by_visit_key = {}
    for position, visit_key in enumerate(candidate_ordered_visit_keys, start=1):
        try:
            rank_value = trade_result.assigned_rank(visit_key)
        except ValueError as error:
            raise RuntimeError(
                f"{label}: general trade rank result has no assigned_rank for "
                f"{_visit_text(visit_key)}."
            ) from error
        rank_int = _require_python_int(
            rank_value,
            f"{label} candidate local rank for {_visit_text(visit_key)}",
        )
        if rank_int < 1:
            raise RuntimeError(
                f"{label}: candidate local rank for {_visit_text(visit_key)} is below 1."
            )
        if rank_int != position:
            raise RuntimeError(
                f"{label}: assigned_rank for {_visit_text(visit_key)} does not match "
                "trade_order position."
            )
        if visit_key in candidate_rank_by_visit_key:
            raise RuntimeError(f"{label}: duplicate candidate local rank for {_visit_text(visit_key)}.")
        candidate_rank_by_visit_key[visit_key] = rank_int
    visit_count = len(baseline_ordered_visit_keys)
    if sorted(candidate_rank_by_visit_key.values()) != list(range(1, visit_count + 1)):
        raise RuntimeError(f"{label}: candidate local ranks are not 1..{visit_count}.")
    if set(candidate_rank_by_visit_key.keys()) != baseline_set:
        raise RuntimeError(f"{label}: candidate local rank map keys differ from candidate_visits.")
    extra_keys = set(candidate_rank_by_visit_key.keys()) - baseline_set
    if extra_keys:
        raise RuntimeError(f"{label}: candidate local rank map has keys outside candidate_visits.")
    return candidate_ordered_visit_keys, candidate_rank_by_visit_key


def _binding_visit_local_rank_fields(
    visit_key: tuple,
    candidate_visit_keys: frozenset,
    binding_partition: OrderControlTvtMpLocalBindingPartition,
    baseline_rank_by_visit_key: dict,
    candidate_rank_by_visit_key: dict,
) -> tuple:
    if visit_key in candidate_visit_keys:
        return (
            baseline_rank_by_visit_key[visit_key],
            candidate_rank_by_visit_key[visit_key],
            STATUS_PRESENT,
            STATUS_PRESENT,
        )
    partition_status = binding_partition.value
    return (None, None, partition_status, partition_status)


def _role_keys(sequence) -> tuple:
    buyers = []
    sellers = []
    nonparticipating = []
    for visit in sequence.trade_scope_of_this_candidate_visits:
        visit_key = _plain_visit_key(visit.visit_key)
        role = _role_name(visit.trade_role)
        if role == "buyer":
            buyers.append(visit_key)
        elif role == "seller":
            sellers.append(visit_key)
        else:
            nonparticipating.append(visit_key)
    return tuple(buyers), tuple(sellers), tuple(nonparticipating)


def _traffic_by_key(local_result) -> dict:
    mapping = {}
    for record in local_result.traffic_observation_records:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(f"Traffic observation repeats {_visit_text(visit_key)}.")
        mapping[visit_key] = record
    return mapping


def _economic_by_key(economic_result) -> tuple:
    buyers = {}
    sellers = {}
    if economic_result is None:
        return buyers, sellers
    for record in economic_result.buyer_economic_records:
        buyers[_plain_visit_key(record.visit_key)] = record
    for record in economic_result.seller_economic_records:
        sellers[_plain_visit_key(record.visit_key)] = record
    return buyers, sellers


def _build_party(
    world,
    collector,
    candidate: ConsideredCandidateRecord,
    visit,
    baseline_local_rank: int | None,
    baseline_local_rank_status: str,
    candidate_local_rank: int | None,
    candidate_local_rank_status: str,
    binding_rank: int | None,
    traffic_by_key: dict,
    buyer_by_key: dict,
    seller_by_key: dict,
    right_key,
    rank_by_visit: dict,
) -> PartyRecord:
    visit_key = _plain_visit_key(visit.visit_key)
    role = _role_name(visit.trade_role)
    traffic = traffic_by_key.get(visit_key)
    buyer = buyer_by_key.get(visit_key)
    seller = seller_by_key.get(visit_key)
    in_trade_scope = visit.binding_partition.value == "trade_scope_of_this_candidate"
    outside = visit.binding_partition.value == "outside_trade_scope_inside_k_fixed"
    candidate_passage = _missing(REASON_NOT_STORED)
    candidate_arrival = _missing(REASON_NOT_STORED)
    if candidate.resolved is not True:
        candidate_passage = _missing(REASON_UNRESOLVED)
        candidate_arrival = _missing(REASON_UNRESOLVED)
    elif traffic is None and in_trade_scope is True:
        candidate_passage = _missing(REASON_NOT_STORED)
    elif traffic is not None and traffic.candidate_passage_timestep is None:
        candidate_passage = _missing(REASON_UNRESOLVED)
    elif traffic is not None:
        candidate_passage = _present(traffic.candidate_passage_timestep)
    baseline_arrival = _present(visit.baseline_arrival_timestep)
    baseline_passage_value = None
    snapshot = collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
    if snapshot is not None and snapshot["baseline_passage_timestep"] is not None:
        baseline_passage_value = snapshot["baseline_passage_timestep"]
    if traffic is not None and traffic.baseline_passage_timestep is not None:
        if (
            baseline_passage_value is not None
            and baseline_passage_value != traffic.baseline_passage_timestep
        ):
            raise RuntimeError(f"{_visit_text(visit_key)} baseline passage sources disagree.")
        baseline_passage_value = traffic.baseline_passage_timestep
    if baseline_passage_value is None:
        baseline_passage = _missing(REASON_NOT_STORED)
    else:
        baseline_passage = _present(baseline_passage_value)
    actual_arrival_value = STATE.actual_first_arrival_by_visit_key.get(visit_key)
    if actual_arrival_value is None:
        actual_arrival = _missing(REASON_ARRIVAL_NOT_OBSERVED)
    else:
        actual_arrival = _present(actual_arrival_value)
    declared = None
    true_vot = None
    if traffic is not None:
        true_vot = traffic.true_vot_per_second
    if true_vot is None:
        true_vot = _true_vot(world, visit_key[0])
    saving = None
    gross = None
    buyer_pass = None
    buyer_status = REASON_NOT_STORED
    waiting = None
    required = None
    seller_status = REASON_NOT_STORED
    external = None
    external_status = REASON_NOT_STORED
    if role == "buyer":
        if buyer is None:
            buyer_status = REASON_UNRESOLVED if candidate.resolved is not True else REASON_NOT_STORED
        else:
            declared = buyer.declared_vot_per_second
            saving = buyer.expected_time_saving_timesteps
            gross = buyer.gross_time_value_G_b
            buyer_pass = buyer.passes_positive_buyer_value_condition
            buyer_status = STATUS_PRESENT
    elif role == "seller":
        if seller is None:
            seller_status = REASON_UNRESOLVED if candidate.resolved is not True else REASON_NOT_STORED
        else:
            declared = seller.declared_vot_per_second
            waiting = seller.expected_waiting_increase_timesteps
            required = seller.required_compensation_R_s
            seller_status = STATUS_PRESENT
    else:
        if traffic is not None and traffic.predicted_signed_time_value_change is not None:
            external = traffic.predicted_signed_time_value_change
            external_status = STATUS_PRESENT
        else:
            external_status = REASON_NOT_STORED
    selected = candidate.selected
    if selected is True:
        interpretation = "selected_candidate_party"
        not_realization = False
    else:
        interpretation = "actual_observation_belongs_to_the_visit_not_this_unselected_candidate"
        not_realization = True
    route_name = visit.route_next_link_name
    return PartyRecord(
        evaluation_index=candidate.evaluation_index,
        candidate_identity=candidate.candidate_identity,
        candidate_selected=selected,
        vehicle_name=visit_key[0],
        visit_id=visit_key[1],
        visit_key=visit_key,
        role=role,
        participates_in_order_exchange=_participation(world, visit_key[0]),
        formal_inlink_name=visit.inlink_name,
        predicted_route_next_link_name=route_name,
        baseline_local_rank=baseline_local_rank,
        baseline_local_rank_status=baseline_local_rank_status,
        candidate_local_rank=candidate_local_rank,
        candidate_local_rank_status=candidate_local_rank_status,
        binding_rank=binding_rank,
        binding_partition=visit.binding_partition.value,
        right_of_entry_holder=visit_key == right_key,
        in_trade_scope=in_trade_scope,
        outside_partition=outside,
        baseline_arrival=baseline_arrival,
        candidate_arrival=candidate_arrival,
        actual_first_arrival=actual_arrival,
        baseline_passage=baseline_passage,
        candidate_passage=candidate_passage,
        actual_passage=_missing(REASON_PASSAGE_NOT_OBSERVED),
        declared_vot_per_second=declared,
        true_vot_per_second=true_vot,
        expected_time_saving_timesteps=saving,
        gross_time_value_G_b=gross,
        passes_positive_buyer_value_condition=buyer_pass,
        buyer_condition_status=buyer_status,
        expected_waiting_increase_timesteps=waiting,
        required_compensation_R_s=required,
        seller_condition_status=seller_status,
        predicted_signed_time_value_change=external,
        nonparticipating_external_effect_status=external_status,
        actual_observation_available_for_visit=actual_arrival_value is not None,
        actual_is_not_realization_of_this_candidate=not_realization,
        actual_comparison_interpretation=interpretation,
        official_payment=None,
        official_compensation=None,
        reference_payment=None,
        reference_compensation=None,
        realized_time_value=None,
        realized_delay_loss=None,
        realized_gain=None,
        satisfaction_status=None,
        satisfaction_reason=None,
        assigned_c_rank=rank_by_visit.get(visit_key),
        actual_node_passage_rank=None,
        candidate_route_next_link_name=route_name,
        actual_route_next_link_name=None,
        formal_route_next_link_name=None,
        ex_post_fields_status=REASON_NOT_LOADED_THIS_PASS,
    )


def _build_considered_candidates(
    world,
    columns: SavedOfficialColumns,
    before: RankMembershipSnapshot,
) -> list:
    local_results = columns.local_virtual_node.candidate_local_virtual_calculation_results
    economic_results = columns.economic_node.candidate_economic_evaluation_results
    economic_by_local = {}
    for economic in economic_results:
        local_result = economic.candidate_local_virtual_calculation_result
        if local_result in economic_by_local:
            raise RuntimeError("One local result appears in two economic results.")
        economic_by_local[local_result] = economic
    selected_economic = columns.selection_node.selected_candidate_economic_result
    right_key = columns.candidate_visit_node.right_of_entry_visit_key
    right_plain = None if right_key is None else _plain_visit_key(right_key)
    rank_by_visit = _snapshot_rank_membership(world).rank_by_visit
    prelimit_head = _prelimit_head_visit_keys(columns, before)
    baseline_ordered_visit_keys, baseline_rank_by_visit_key = _baseline_local_rank_material(
        columns.candidate_visit_node,
        prelimit_head,
    )
    candidate_visit_keys = frozenset(baseline_ordered_visit_keys)
    records = []
    index = 0
    for local_result in local_results:
        index = index + 1
        if not isinstance(local_result, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
            raise RuntimeError("Local virtual result type is wrong.")
        sequence = local_result.binding_rank_sequence
        buyers, sellers, nonparticipating = _role_keys(sequence)
        trade_scope = _keys_of(sequence.trade_scope_of_this_candidate_visits)
        if len(trade_scope) != len(set(trade_scope)):
            raise RuntimeError(f"Candidate {index} repeats a trade-scope VisitKey.")
        if len(buyers) < 1 or len(sellers) < 1:
            raise RuntimeError(f"Candidate {index} is missing a buyer or a seller.")
        if len(trade_scope) != len(buyers) + len(sellers) + len(nonparticipating):
            raise RuntimeError(f"Candidate {index} role counts do not match trade scope.")
        if len(trade_scope) > trial.MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError(f"Candidate {index} trade scope exceeds 5.")
        buyers_sorted = tuple(
            _plain_visit_key(visit_key) for visit_key in sequence.concrete_buyer_candidate_set.buyers_sorted
        )
        trade_result = _matching_trade_result(columns.trade_rank_node, buyers_sorted)
        _assert_binding_roles_match_trade_result(
            buyers,
            sellers,
            nonparticipating,
            trade_scope,
            trade_result,
            index,
        )
        candidate_ordered_visit_keys, candidate_rank_by_visit_key = _candidate_local_rank_material(
            trade_result,
            baseline_ordered_visit_keys,
        )
        identity = f"T={TARGET_TIMESTEP}|{TARGET_NODE_NAME}|index={index}|" + "|".join(
            _visit_text(visit_key) for visit_key in buyers_sorted
        )
        economic = economic_by_local.get(local_result)
        selected = economic is not None and economic is selected_economic
        missing_passage = []
        missing_route = []
        for traffic in local_result.traffic_observation_records:
            if traffic.candidate_passage_timestep is None:
                missing_passage.append(_plain_visit_key(traffic.visit_key))
            if traffic.route_next_link_name is None or traffic.route_next_link_name == "":
                missing_route.append(_plain_visit_key(traffic.visit_key))
        if economic is None:
            total_g = None
            total_r = None
            surplus = None
            feasible = None
            reasons = ()
            selection_status_text = REASON_UNRESOLVED if local_result.resolved is not True else REASON_NOT_STORED
        else:
            total_g = economic.total_buyer_value_G
            total_r = economic.total_required_compensation_R
            surplus = economic.surplus
            feasible = economic.economically_feasible
            reasons = tuple(economic.infeasibility_reasons)
            if selected is True:
                selection_status_text = STATUS_PRESENT
            else:
                selection_status_text = REASON_NOT_STORED
        candidate = ConsideredCandidateRecord(
            evaluation_index=index,
            candidate_identity=identity,
            selected=selected,
            local_result=local_result,
            economic_result=economic,
            buyers_sorted=buyers_sorted,
            right_of_entry_visit_key=right_plain,
            buyer_visit_keys=buyers,
            seller_visit_keys=sellers,
            nonparticipating_visit_keys=nonparticipating,
            trade_scope_visit_keys=trade_scope,
            buyer_count=len(buyers),
            seller_count=len(sellers),
            nonparticipating_count=len(nonparticipating),
            trade_scope_count=len(trade_scope),
            baseline_local_order=baseline_ordered_visit_keys,
            candidate_local_order=candidate_ordered_visit_keys,
            baseline_local_rank_by_visit_key=dict(baseline_rank_by_visit_key),
            candidate_local_rank_by_visit_key=dict(candidate_rank_by_visit_key),
            trade_result=trade_result,
            binding_sequence=sequence,
            trade_scope_of_this_candidate_visits=sequence.trade_scope_of_this_candidate_visits,
            outside_trade_scope_inside_k_fixed_visits=sequence.outside_trade_scope_inside_k_fixed_visits,
            k_last_buyer=sequence.k_last_buyer,
            k_decision_window=sequence.k_decision_window,
            k_fixed=sequence.k_fixed,
            candidate_build_status=columns.local_virtual_node.build_status,
            local_virtual_calculation_stop_reason=local_result.stop_reason,
            resolved=local_result.resolved,
            unresolved=local_result.resolved is not True,
            unresolved_reasons=tuple(local_result.unresolved_reasons),
            traffic_observation_count=len(local_result.traffic_observation_records),
            candidate_passage_missing_visit_keys=tuple(missing_passage),
            candidate_route_missing_visit_keys=tuple(missing_route),
            total_G=total_g,
            total_R=total_r,
            surplus=surplus,
            economically_feasible=feasible,
            candidate_infeasibility_reasons=reasons,
            selection_status=columns.selection_node.selection_status,
            selection_reason_status=selection_status_text,
            parties=[],
        )
        traffic_by_key = _traffic_by_key(local_result)
        buyer_by_key, seller_by_key = _economic_by_key(economic)
        for visit in sequence.visits_in_binding_order:
            visit_key = _plain_visit_key(visit.visit_key)
            baseline_local_rank, candidate_local_rank, baseline_status, candidate_status = (
                _binding_visit_local_rank_fields(
                    visit_key,
                    candidate_visit_keys,
                    visit.binding_partition,
                    baseline_rank_by_visit_key,
                    candidate_rank_by_visit_key,
                )
            )
            binding_rank_value = _require_python_int(
                visit.binding_rank,
                f"{_decision_label()} binding_rank for {_visit_text(visit_key)}",
            )
            candidate.parties.append(
                _build_party(
                    world,
                    columns.collector,
                    candidate,
                    visit,
                    baseline_local_rank,
                    baseline_status,
                    candidate_local_rank,
                    candidate_status,
                    binding_rank_value,
                    traffic_by_key,
                    buyer_by_key,
                    seller_by_key,
                    right_plain,
                    rank_by_visit,
                )
            )
        records.append(candidate)
    return records


def _fill_selected_candidate_passages(selected: ConsideredCandidateRecord) -> None:
    by_key = {}
    for party in selected.parties:
        by_key[party.visit_key] = party
    for row in STATE.t392_prelimit_visits:
        party = by_key.get(row.visit_key)
        if row.beyond_limit is True:
            row.candidate_arrival = _missing(REASON_BEYOND_LIMIT)
            row.candidate_passage = _missing(REASON_BEYOND_LIMIT)
            continue
        if party is None:
            row.candidate_passage = _missing(REASON_NO_CANDIDATE_EVALUATION)
            continue
        if selected.selected is not True:
            row.candidate_passage = _missing(REASON_CANDIDATE_NOT_SELECTED)
            continue
        row.candidate_arrival = party.candidate_arrival
        row.candidate_passage = party.candidate_passage


def _build_final_rank_rows(columns: SavedOfficialColumns, world) -> list:
    rank_by_visit = _snapshot_rank_membership(world).rank_by_visit
    rows = []
    for record in columns.final_rank_node.final_rank_visits:
        visit_key = _plain_visit_key(record.visit_key)
        snapshot = columns.collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
        if snapshot is None:
            baseline_arrival = _missing(REASON_NOT_STORED)
            baseline_passage = _missing(REASON_NOT_STORED)
        else:
            baseline_arrival = _present(snapshot["baseline_arrival_timestep"])
            if snapshot["baseline_passage_timestep"] is None:
                baseline_passage = _missing(REASON_NOT_STORED)
            else:
                baseline_passage = _present(snapshot["baseline_passage_timestep"])
        rows.append(
            FinalRankVisitRecord(
                visit_key=visit_key,
                final_local_rank=record.final_local_rank,
                finalization_source=record.finalization_source,
                formal_route_next_link_name=record.formal_route_next_link_name,
                route_origin=record.route_origin,
                baseline_arrival=baseline_arrival,
                candidate_arrival=_missing(REASON_NOT_STORED),
                actual_first_arrival=_missing(REASON_ARRIVAL_NOT_OBSERVED),
                baseline_passage=baseline_passage,
                candidate_passage=_missing(REASON_NO_CANDIDATE_EVALUATION),
                actual_passage=_missing(REASON_PASSAGE_NOT_OBSERVED),
                assigned_c_rank=rank_by_visit.get(visit_key),
            )
        )
    return rows


def _open_beyond_limit_tracking(columns: SavedOfficialColumns) -> None:
    final_by_key = {}
    for record in columns.final_rank_node.final_rank_visits:
        final_by_key[_plain_visit_key(record.visit_key)] = record
    for visit_key in STATE.t392_beyond_limit_visit_keys:
        matched = final_by_key.get(visit_key)
        confirmation = BeyondLimitConfirmationRecord(
            visit_key=visit_key,
            in_t392_final_rank=matched is not None,
            assigned_c_rank_at_t392=None if matched is None else STATE.current_rank_by_visit_key.get(visit_key),
            t392_finalization_source=None if matched is None else matched.finalization_source,
            t392_final_rank_status=columns.final_rank_node.final_rank_status,
            confirmed_by_diagnostic_end=matched is not None,
            confirmation_decision_timestep=TARGET_TIMESTEP if matched is not None else None,
            node_name=TARGET_NODE_NAME if matched is not None else None,
            assigned_c_rank=None if matched is None else STATE.current_rank_by_visit_key.get(visit_key),
            finalization_source=None if matched is None else _classify_confirmation_source(columns, visit_key),
            final_rank_status=columns.final_rank_node.final_rank_status if matched is not None else None,
            source_selected_candidate=False,
            source_baseline_fallback=False,
            source_leading_nonparticipating=False,
            source_arrived_undetermined=False,
            last_checked_timestep=TARGET_TIMESTEP,
            last_official_state="confirmed_at_t392" if matched is not None else "unconfirmed_at_t392",
            unresolved_reason=None if matched is not None else "not_confirmed_at_t392",
        )
        if confirmation.finalization_source == SOURCE_SELECTED:
            confirmation.source_selected_candidate = True
        elif confirmation.finalization_source == SOURCE_BASELINE_FALLBACK:
            confirmation.source_baseline_fallback = True
        elif confirmation.finalization_source == SOURCE_LEADING:
            confirmation.source_leading_nonparticipating = True
        elif confirmation.finalization_source == SOURCE_ARRIVED:
            confirmation.source_arrived_undetermined = True
        elif confirmation.finalization_source == SOURCE_SELECTED_OUTSIDE:
            confirmation.source_selected_candidate = True
        STATE.beyond_limit_confirmations[visit_key] = confirmation


def _track_beyond_limit(world, columns: SavedOfficialColumns) -> None:
    for visit_key, confirmation in STATE.beyond_limit_confirmations.items():
        confirmation.last_checked_timestep = world.T
        if confirmation.confirmed_by_diagnostic_end is True:
            confirmation.last_official_state = "already_confirmed"
            continue
        source = _classify_confirmation_source(columns, visit_key)
        rank_value = STATE.current_rank_by_visit_key.get(visit_key)
        if source is None and rank_value is None:
            confirmation.last_official_state = "still_unconfirmed"
            confirmation.unresolved_reason = "not_confirmed_by_this_timestep"
            continue
        if source is None or rank_value is None:
            raise RuntimeError(
                f"{_visit_text(visit_key)} at T={world.T} has a rank without a formal source, or the reverse."
            )
        confirmation.confirmed_by_diagnostic_end = True
        confirmation.confirmation_decision_timestep = world.T
        confirmation.node_name = TARGET_NODE_NAME
        confirmation.assigned_c_rank = rank_value
        confirmation.finalization_source = source
        confirmation.final_rank_status = columns.final_rank_node.final_rank_status
        confirmation.last_official_state = "first_confirmed"
        confirmation.unresolved_reason = None
        confirmation.source_selected_candidate = source in (SOURCE_SELECTED, SOURCE_SELECTED_OUTSIDE)
        confirmation.source_baseline_fallback = source == SOURCE_BASELINE_FALLBACK
        confirmation.source_leading_nonparticipating = source == SOURCE_LEADING
        confirmation.source_arrived_undetermined = source == SOURCE_ARRIVED


def _update_rank_history(world, before: RankMembershipSnapshot, columns: SavedOfficialColumns) -> None:
    after = _snapshot_rank_membership(world)
    seen_ranks = {}
    for visit_key, rank_value in after.rank_by_visit.items():
        if rank_value in seen_ranks:
            raise RuntimeError(
                f"T={world.T} assigned C rank {rank_value} is shared by "
                f"{_visit_text(seen_ranks[rank_value])} and {_visit_text(visit_key)}."
            )
        seen_ranks[rank_value] = visit_key
        previous = before.rank_by_visit.get(visit_key)
        if previous is None:
            source = _classify_confirmation_source(columns, visit_key)
            STATE.rank_history.append(
                RankHistoryEntry(
                    timestep=world.T,
                    visit_key=visit_key,
                    assigned_rank=rank_value,
                    first_assignment=True,
                    source=source,
                )
            )
            STATE.first_rank_by_visit_key[visit_key] = {
                "timestep": world.T,
                "assigned_rank": rank_value,
                "source": source,
            }
        elif previous != rank_value:
            STATE.rank_overwrites.append(
                RankOverwrite(
                    timestep=world.T,
                    visit_key=visit_key,
                    previous_rank=previous,
                    new_rank=rank_value,
                )
            )
        else:
            STATE.rank_history.append(
                RankHistoryEntry(
                    timestep=world.T,
                    visit_key=visit_key,
                    assigned_rank=rank_value,
                    first_assignment=False,
                    source=None,
                )
            )
    STATE.current_rank_by_visit_key = dict(after.rank_by_visit)


def _capture_t392(world, columns: SavedOfficialColumns, before: RankMembershipSnapshot) -> None:
    if STATE.t392_capture_count != 0:
        raise RuntimeError("T=392 northwest capture already exists.")
    STATE.t392_capture_count = 1
    STATE.t392_columns = columns
    STATE.t392_candidate_visit_node = columns.candidate_visit_node
    if columns.selection_node.selected_candidate_economic_result is None:
        raise RuntimeError("T=392 northwest has no selected candidate.")
    if not isinstance(columns.trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError("Trade rank node type is wrong.")
    if not isinstance(columns.final_rank_node, OrderControlTvtNodeMpFinalRankResult):
        raise RuntimeError("Final rank node type is wrong.")
    considered = _build_considered_candidates(world, columns, before)
    STATE.t392_considered_candidates = considered
    selected = None
    for candidate in considered:
        if candidate.selected is True:
            if selected is not None:
                raise RuntimeError("More than one considered candidate is selected.")
            selected = candidate
    if selected is None:
        raise RuntimeError("Selected economic result is not among considered local results.")
    if selected.economic_result is not columns.selection_node.selected_candidate_economic_result:
        raise RuntimeError("Selected candidate object identity does not match.")
    STATE.t392_selected_candidate = selected
    STATE.t392_binding_sequence = selected.binding_sequence
    STATE.t392_final_rank_result = columns.final_rank_node
    STATE.t392_prelimit_visits = _build_prelimit_records(columns, before, world, selected)
    within = []
    beyond = []
    seen = set()
    for row in STATE.t392_prelimit_visits:
        if row.visit_key in seen:
            raise RuntimeError(f"Duplicate prelimit VisitKey {_visit_text(row.visit_key)}.")
        seen.add(row.visit_key)
        if row.within_limit is True:
            within.append(row.visit_key)
        if row.beyond_limit is True:
            beyond.append(row.visit_key)
    if set(within) & set(beyond):
        raise RuntimeError("A visit is both within and beyond the limit.")
    STATE.t392_within_limit_visit_keys = tuple(within)
    STATE.t392_beyond_limit_visit_keys = tuple(beyond)
    _fill_selected_candidate_passages(selected)
    STATE.t392_final_rank_visits = _build_final_rank_rows(columns, world)
    target = set(seen)
    for candidate in considered:
        for party in candidate.parties:
            target.add(party.visit_key)
    for row in STATE.t392_final_rank_visits:
        target.add(row.visit_key)
    STATE.target_visit_keys = target
    _open_beyond_limit_tracking(columns)


def _note_real_driver(world, result, before: RankMembershipSnapshot) -> None:
    driver_result = _require_driver_result(result)
    columns = _saved_columns(driver_result.atomic_apply_set_result)
    _update_rank_history(world, before, columns)
    if CONTEXT_START_TIMESTEP <= world.T <= CONTEXT_END_TIMESTEP:
        _record_context(world, columns, before)
    if world.T == TARGET_TIMESTEP:
        _capture_t392(world, columns, before)
    elif STATE.t392_capture_count == 1 and world.T <= DIAGNOSTIC_LAST_PROCESSED_TIMESTEP:
        _track_beyond_limit(world, columns)


def wrapped_driver(world):
    before = None
    is_real_driver_call = (
        world is STATE.real_world
        and getattr(world, "_order_control_baseline_collector", None) is None
    )
    if (
        is_real_driver_call
        and type(world.T) is int
        and CONTEXT_START_TIMESTEP <= world.T <= DIAGNOSTIC_LAST_PROCESSED_TIMESTEP
    ):
        before = _snapshot_rank_membership(world)
    result = STATE.original_driver(world)
    if not is_real_driver_call:
        return result
    if before is None:
        return result
    if type(world.T) is int and CONTEXT_START_TIMESTEP <= world.T <= DIAGNOSTIC_LAST_PROCESSED_TIMESTEP:
        _note_real_driver(world, result, before)
    return result


def wrapped_arrival(vehicle, node):
    result = STATE.original_arrival(vehicle, node)
    if vehicle.W is not STATE.real_world:
        return result
    if getattr(vehicle.W, "_order_control_baseline_collector", None) is not None:
        return result
    if node is None or node.name != TARGET_NODE_NAME:
        return result
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return result
    if current_visit.get("node") is not node:
        return result
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return result
    arrival_time = current_visit.get("arrival_time")
    if arrival_time is None:
        return result
    visit_key = (vehicle.name, visit_id)
    formal_timestep = _formal_arrival_timestep(arrival_time, vehicle.W.DELTAT)
    stored = STATE.actual_first_arrival_by_visit_key.get(visit_key)
    if stored is None:
        if formal_timestep != vehicle.W.T:
            raise RuntimeError(
                f"First arrival {_visit_text(visit_key)} formal {formal_timestep} != World.T {vehicle.W.T}."
            )
        STATE.actual_first_arrival_by_visit_key[visit_key] = formal_timestep
    elif stored != formal_timestep:
        raise RuntimeError(f"Re-registration changed arrival for {_visit_text(visit_key)}.")
    return result


def install_hooks(real_world) -> None:
    if STATE.installed is True:
        raise RuntimeError("Diagnostic hooks are already installed.")
    STATE.real_world = real_world
    STATE.original_driver = driver_module.run_tvt_mp_driver
    STATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival
    STATE.installed = True


def restore_hooks() -> None:
    if STATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = STATE.original_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = STATE.original_arrival
    STATE.original_driver = None
    STATE.original_arrival = None
    STATE.installed = False


def _apply_actual_times(world) -> None:
    registry = getattr(world, "order_control_tvt_mp_actual_node_passage_history_registry", None)
    passage_by_key = {}
    rank_by_key = {}
    if registry is not None:
        for record in registry.records_by_node_name.get(TARGET_NODE_NAME, ()):
            visit_key = _plain_visit_key(record.visit_key)
            if visit_key in passage_by_key:
                raise RuntimeError(f"Duplicate actual passage for {_visit_text(visit_key)}.")
            passage_by_key[visit_key] = record.actual_passage_timestep
            rank_by_key[visit_key] = record.actual_node_passage_rank
    for row in STATE.t392_prelimit_visits:
        arrival = STATE.actual_first_arrival_by_visit_key.get(row.visit_key)
        if arrival is None:
            row.actual_first_arrival = _missing(REASON_ARRIVAL_NOT_OBSERVED)
        else:
            row.actual_first_arrival = _present(arrival)
        passage = passage_by_key.get(row.visit_key)
        if passage is None:
            row.actual_passage = _missing(REASON_PASSAGE_NOT_OBSERVED)
        else:
            row.actual_passage = _present(passage)
    for candidate in STATE.t392_considered_candidates:
        for party in candidate.parties:
            arrival = STATE.actual_first_arrival_by_visit_key.get(party.visit_key)
            party.actual_observation_available_for_visit = arrival is not None or party.visit_key in passage_by_key
            if arrival is None:
                party.actual_first_arrival = _missing(REASON_ARRIVAL_NOT_OBSERVED)
            else:
                party.actual_first_arrival = _present(arrival)
            passage = passage_by_key.get(party.visit_key)
            if passage is None:
                party.actual_passage = _missing(REASON_PASSAGE_NOT_OBSERVED)
            else:
                party.actual_passage = _present(passage)
            party.actual_node_passage_rank = rank_by_key.get(party.visit_key)
            if candidate.selected is not True:
                party.actual_is_not_realization_of_this_candidate = True
                party.official_payment = None
                party.official_compensation = None
                party.satisfaction_status = None
                party.realized_gain = None
    for row in STATE.t392_final_rank_visits:
        arrival = STATE.actual_first_arrival_by_visit_key.get(row.visit_key)
        if arrival is None:
            row.actual_first_arrival = _missing(REASON_ARRIVAL_NOT_OBSERVED)
        else:
            row.actual_first_arrival = _present(arrival)
        passage = passage_by_key.get(row.visit_key)
        if passage is None:
            row.actual_passage = _missing(REASON_PASSAGE_NOT_OBSERVED)
        else:
            row.actual_passage = _present(passage)


def _require_timed(field_value: TimedField, label: str) -> None:
    if field_value.status == STATUS_PRESENT and field_value.value is None:
        raise RuntimeError(f"{label} is present without a value.")
    if field_value.status != STATUS_PRESENT and field_value.value is not None:
        raise RuntimeError(f"{label} has a value without present status.")
    if field_value.status == "":
        raise RuntimeError(f"{label} has no status.")


def _validate_considered_candidate_local_ranks(
    candidate: ConsideredCandidateRecord,
    candidate_visit_node,
) -> None:
    label = _decision_label()
    formal_baseline_order = tuple(
        _plain_visit_key(candidate_visit.visit_key)
        for candidate_visit in candidate_visit_node.candidate_visits
    )
    if candidate.baseline_local_order != formal_baseline_order:
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} baseline_local_order "
            "does not match saved candidate_visits."
        )
    trade_order = tuple(
        _plain_visit_key(visit_key) for visit_key in candidate.trade_result.trade_order
    )
    if candidate.candidate_local_order != trade_order:
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} candidate_local_order "
            "does not match trade_result.trade_order."
        )
    visit_count = len(formal_baseline_order)
    if sorted(candidate.baseline_local_rank_by_visit_key.values()) != list(range(1, visit_count + 1)):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} baseline local ranks are not "
            f"1..{visit_count}."
        )
    if sorted(candidate.candidate_local_rank_by_visit_key.values()) != list(range(1, visit_count + 1)):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} candidate local ranks are not "
            f"1..{visit_count}."
        )
    if set(candidate.candidate_local_rank_by_visit_key.keys()) != set(formal_baseline_order):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} candidate rank keys differ "
            "from candidate_visits."
        )
    if set(trade_order) != set(formal_baseline_order):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} trade_order keys differ "
            "from candidate_visits."
        )
    official_buyers, official_sellers, official_nonparticipating, official_scope = (
        _trade_result_role_material(candidate.trade_result)
    )
    if set(candidate.buyer_visit_keys) != set(official_buyers):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} saved buyers differ from trade result."
        )
    if set(candidate.seller_visit_keys) != set(official_sellers):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} saved sellers differ from trade result."
        )
    if set(candidate.nonparticipating_visit_keys) != set(official_nonparticipating):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} saved nonparticipating visits "
            "differ from trade result."
        )
    if set(candidate.trade_scope_visit_keys) != set(official_scope):
        raise RuntimeError(
            f"{label}: candidate {candidate.evaluation_index} saved trade scope differs "
            "from trade result."
        )
    binding_by_key = {}
    for visit in candidate.binding_sequence.visits_in_binding_order:
        visit_key = _plain_visit_key(visit.visit_key)
        if visit_key in binding_by_key:
            raise RuntimeError(
                f"{label}: candidate {candidate.evaluation_index} binding sequence repeats "
                f"{_visit_text(visit_key)}."
            )
        binding_by_key[visit_key] = visit
    candidate_visit_keys = frozenset(formal_baseline_order)
    for party in candidate.parties:
        visit = binding_by_key.get(party.visit_key)
        if visit is None:
            raise RuntimeError(
                f"{label}: party {_visit_text(party.visit_key)} is missing from binding sequence."
            )
        official_binding_rank = _require_python_int(
            visit.binding_rank,
            f"{label} binding_rank for {_visit_text(party.visit_key)}",
        )
        if party.binding_rank != official_binding_rank:
            raise RuntimeError(
                f"{label}: party {_visit_text(party.visit_key)} binding_rank disagrees with "
                "binding visit."
            )
        if party.visit_key in candidate_visit_keys:
            if party.baseline_local_rank_status != STATUS_PRESENT:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} is in candidate_visits but "
                    "baseline_local_rank_status is not present."
                )
            if party.candidate_local_rank_status != STATUS_PRESENT:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} is in candidate_visits but "
                    "candidate_local_rank_status is not present."
                )
            expected_baseline = candidate.baseline_local_rank_by_visit_key[party.visit_key]
            expected_candidate = candidate.candidate_local_rank_by_visit_key[party.visit_key]
            if party.baseline_local_rank != expected_baseline:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} baseline_local_rank disagrees "
                    "with the baseline rank map."
                )
            if party.candidate_local_rank != expected_candidate:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} candidate_local_rank disagrees "
                    "with the candidate rank map."
                )
            if party.baseline_local_rank == party.binding_rank:
                if party.baseline_local_rank != expected_baseline:
                    raise RuntimeError(
                        f"{label}: party {_visit_text(party.visit_key)} uses binding_rank as "
                        "baseline_local_rank."
                    )
            if party.candidate_local_rank == party.binding_rank:
                if party.candidate_local_rank != expected_candidate:
                    raise RuntimeError(
                        f"{label}: party {_visit_text(party.visit_key)} uses binding_rank as "
                        "candidate_local_rank."
                    )
        else:
            if visit.binding_partition in (
                OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE,
                OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED,
            ):
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} is outside candidate_visits "
                    "but binding partition is trade-scope or outside-k-fixed."
                )
            if party.baseline_local_rank is not None or party.candidate_local_rank is not None:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} outside candidate_visits has "
                    "a non-null local rank."
                )
            partition_status = visit.binding_partition.value
            if party.baseline_local_rank_status != partition_status:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} baseline_local_rank_status "
                    "does not match binding partition."
                )
            if party.candidate_local_rank_status != partition_status:
                raise RuntimeError(
                    f"{label}: party {_visit_text(party.visit_key)} candidate_local_rank_status "
                    "does not match binding partition."
                )


def validate_captured_foundation(world) -> None:
    if trial.MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("Trial MAX_CANDIDATE_VISIT_COUNT is not 5.")
    if world.order_control_tvt_max_candidate_visit_count != 5:
        raise RuntimeError("World candidate limit is not 5.")
    if STATE.t392_capture_count != 1 or STATE.t392_columns is None:
        raise RuntimeError("T=392 capture is missing.")
    selected = STATE.t392_selected_candidate
    if selected is None:
        raise RuntimeError("T=392 selected candidate is missing.")
    if len(STATE.t392_within_limit_visit_keys) != 5:
        raise RuntimeError("Within-limit visit count is not 5.")
    count_before = STATE.t392_columns.candidate_visit_node.p_minus_one_eligible_visit_count_before_limit
    if type(count_before) is not int or count_before <= 5:
        raise RuntimeError("P-1 count before the limit is not greater than 5.")
    if set(STATE.t392_within_limit_visit_keys) & set(STATE.t392_beyond_limit_visit_keys):
        raise RuntimeError("Within-limit and beyond-limit visits overlap.")
    if len(STATE.t392_beyond_limit_visit_keys) != count_before - 5:
        raise RuntimeError("Beyond-limit visits disappeared.")
    if len(STATE.t392_considered_candidates) < 1:
        raise RuntimeError("No considered candidate was saved.")
    if selected.trade_scope_count != 5:
        raise RuntimeError("Selected trade scope is not 5.")
    if selected.buyer_count < 1 or selected.seller_count < 1:
        raise RuntimeError("Selected candidate is missing a buyer or a seller.")
    if selected.binding_sequence is None:
        raise RuntimeError("Selected binding sequence is missing.")
    if STATE.t392_final_rank_result is None:
        raise RuntimeError("Final rank result is missing.")
    if len(STATE.rank_overwrites) != 0:
        raise RuntimeError("An already confirmed C rank was overwritten.")
    if STATE.installed is not False:
        raise RuntimeError("Hooks are still installed.")
    for row in STATE.t392_prelimit_visits:
        _require_timed(row.baseline_arrival, _visit_text(row.visit_key) + " baseline arrival")
        _require_timed(row.candidate_arrival, _visit_text(row.visit_key) + " candidate arrival")
        _require_timed(row.actual_first_arrival, _visit_text(row.visit_key) + " actual arrival")
        _require_timed(row.baseline_passage, _visit_text(row.visit_key) + " baseline passage")
        _require_timed(row.candidate_passage, _visit_text(row.visit_key) + " candidate passage")
        _require_timed(row.actual_passage, _visit_text(row.visit_key) + " actual passage")
    for visit_key, confirmation in STATE.beyond_limit_confirmations.items():
        if confirmation.confirmed_by_diagnostic_end is not True:
            if confirmation.last_checked_timestep is None or confirmation.unresolved_reason is None:
                raise RuntimeError(f"{_visit_text(visit_key)} unconfirmed state is incomplete.")
    if STATE.t392_candidate_visit_node is None:
        raise RuntimeError("T=392 candidate visit node is missing.")
    for candidate in STATE.t392_considered_candidates:
        _validate_considered_candidate_local_ranks(candidate, STATE.t392_candidate_visit_node)


def _join_visit_keys(visit_keys) -> str:
    return VISIT_KEY_SEPARATOR.join(_visit_text(visit_key) for visit_key in visit_keys)


def _serialize_enum(value) -> str:
    if isinstance(value, Enum):
        return value.value
    if value is None:
        return ""
    return str(value)


def _serialize_scalar_for_csv(value) -> str:
    text = _serialize_enum(value)
    if type(text) is not str:
        text = str(text)
    return text


def _serialize_value_sequence_for_csv(values, separator: str) -> str:
    parts = []
    for value in values:
        parts.append(_serialize_scalar_for_csv(value))
    return separator.join(parts)


def _serialize_bool(value) -> str:
    if value is None:
        return ""
    if type(value) is not bool:
        raise RuntimeError(f"Expected bool, got {value!r}.")
    return "true" if value is True else "false"


def _serialize_optional_int(value) -> str:
    if value is None:
        return ""
    return str(_require_python_int(value, "CSV int"))


def _serialize_optional_float(value) -> str:
    if value is None:
        return ""
    if type(value) is not float:
        raise RuntimeError(f"Expected float, got {value!r}.")
    return repr(value)


def _serialize_manifest_value(value):
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bool):
        return value
    if type(value) is int and type(value) is not bool:
        return value
    if type(value) is float:
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, tuple):
        return [_serialize_manifest_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_manifest_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_manifest_value(item) for key, item in value.items()}
    return str(value)


def _timed_csv_columns(field: TimedField, value_name: str, status_name: str) -> dict:
    if field.status == STATUS_PRESENT:
        return {
            value_name: _serialize_optional_int(field.value),
            status_name: STATUS_PRESENT,
        }
    return {value_name: "", status_name: field.status}


def _subtract_optional_ints(left: int | None, right: int | None):
    if left is None or right is None:
        return ""
    return str(left - right)


def _close_float(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


def _require_close_float(left: float, right: float, label: str) -> None:
    if _close_float(left, right) is not True:
        raise RuntimeError(f"{label}: {left!r} != {right!r}.")


def _parse_csv_number(text: str):
    if text is None or text == "":
        return None
    if "." in text:
        return float(text)
    return int(text)


def _read_formal_csv(path: Path) -> list[dict]:
    if path.is_file() is not True:
        raise RuntimeError(f"Missing formal CSV {path}.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _refuse_existing_output_directory() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")


def _assert_existing_trial_output_paths() -> None:
    expected_name = (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_initial"
    )
    if EXISTING_FULL_TRIAL_OUTPUT_DIR_NAME != expected_name:
        raise RuntimeError("Existing trial output directory name is not the N=5 formal trial.")
    if "candidate_limit_5" not in EXISTING_FULL_TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Existing trial output directory name must include candidate_limit_5.")


def _find_formal_transaction_row(transactions: list[dict], buyers_sorted: tuple) -> dict:
    buyers_text = _join_visit_keys(buyers_sorted)
    matched = [
        row
        for row in transactions
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
        and row["buyers_sorted"] == buyers_text
    ]
    if len(matched) != 1:
        raise RuntimeError(
            f"Formal transaction CSV match count is {len(matched)} for T=392 northwest."
        )
    return matched[0]


def _compare_formal_transaction_row(transaction_row: dict, selected: ConsideredCandidateRecord) -> None:
    buyers_text = _join_visit_keys(selected.buyers_sorted)
    if transaction_row["buyers_sorted"] != buyers_text:
        raise RuntimeError("Formal CSV buyers_sorted text differs from selected candidate.")
    int_pairs = (
        ("buyer_visit_count", selected.buyer_count),
        ("seller_visit_count", selected.seller_count),
        ("nonparticipating_visit_count", selected.nonparticipating_count),
        ("trade_scope_visit_count", selected.trade_scope_count),
    )
    for csv_name, diagnostic_value in int_pairs:
        csv_value = _parse_csv_number(transaction_row[csv_name])
        if csv_value != diagnostic_value:
            raise RuntimeError(f"Formal CSV {csv_name} {csv_value!r} != diagnostic {diagnostic_value!r}.")
    for csv_name in (
        "buyer_satisfied_count",
        "buyer_unsatisfied_count",
        "seller_satisfied_count",
        "seller_unsatisfied_count",
        "rank_difference_evaluated_count",
        "rank_difference_unavailable_count",
    ):
        if transaction_row[csv_name] == "":
            raise RuntimeError(f"Formal CSV {csv_name} is empty.")
        if type(_parse_csv_number(transaction_row[csv_name])) is not int:
            raise RuntimeError(f"Formal CSV {csv_name} is not an int.")
    for csv_name in (
        "buyer_official_payment_total",
        "seller_official_compensation_total",
        "buyer_reference_payment_total",
        "seller_reference_compensation_total",
        "buyer_realized_gain_total",
        "seller_realized_gain_total",
    ):
        if _parse_csv_number(transaction_row[csv_name]) is None:
            raise RuntimeError(f"Formal CSV {csv_name} is empty.")
    economic = selected.economic_result
    if economic is not None:
        _require_close_float(
            _parse_csv_number(transaction_row["buyer_official_payment_total"]),
            economic.total_required_compensation_R,
            "buyer_official_payment_total vs diagnostic total_R",
        )
        _require_close_float(
            _parse_csv_number(transaction_row["seller_official_compensation_total"]),
            economic.total_required_compensation_R,
            "seller_official_compensation_total vs diagnostic total_R",
        )
        if selected.surplus is not None:
            _require_close_float(
                _parse_csv_number(transaction_row["buyer_realized_gain_total"]),
                selected.surplus,
                "buyer_realized_gain_total vs diagnostic surplus",
            )


def _find_formal_visit_row(visits: list[dict], buyers_sorted: tuple, party: PartyRecord) -> dict:
    buyers_text = _join_visit_keys(buyers_sorted)
    matched = [
        row
        for row in visits
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
        and row["buyers_sorted"] == buyers_text
        and row["vehicle_name"] == party.vehicle_name
        and row["visit_id"] == str(party.visit_id)
        and row["role"] == party.role
    ]
    if len(matched) != 1:
        raise RuntimeError(
            f"Formal visit CSV match count is {len(matched)} for {_visit_text(party.visit_key)}."
        )
    return matched[0]


def _compare_formal_visit_row(visit_row: dict, party: PartyRecord, selected: ConsideredCandidateRecord) -> None:
    if party.visit_key != (party.vehicle_name, party.visit_id):
        raise RuntimeError("Party VisitKey fields disagree.")
    if visit_row["role"] != party.role:
        raise RuntimeError(f"Formal CSV role differs for {_visit_text(party.visit_key)}.")
    int_fields = (
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "actual_passage_timestep",
        "assigned_rank",
        "actual_node_passage_rank",
    )
    for name in int_fields:
        csv_value = _parse_csv_number(visit_row[name])
        diagnostic_value = None
        if name == "baseline_passage_timestep":
            diagnostic_value = party.baseline_passage.value
        elif name == "candidate_passage_timestep":
            diagnostic_value = party.candidate_passage.value
        elif name == "actual_passage_timestep":
            diagnostic_value = party.actual_passage.value
        elif name == "assigned_rank":
            diagnostic_value = party.assigned_c_rank
        elif name == "actual_node_passage_rank":
            diagnostic_value = party.actual_node_passage_rank
        if csv_value != diagnostic_value:
            raise RuntimeError(f"Formal CSV {name} differs for {_visit_text(party.visit_key)}.")
    if visit_row["predicted_route_next_link_name"] != (party.predicted_route_next_link_name or ""):
        if party.predicted_route_next_link_name is not None:
            if visit_row["predicted_route_next_link_name"] != party.predicted_route_next_link_name:
                raise RuntimeError(
                    f"Formal CSV predicted route differs for {_visit_text(party.visit_key)}."
                )
    if visit_row.get("true_vot_per_second", "") != "":
        csv_vot = _parse_csv_number(visit_row["true_vot_per_second"])
        if party.true_vot_per_second is not None:
            _require_close_float(csv_vot, party.true_vot_per_second, "true VOT")
    for name in (
        "official_payment",
        "official_compensation",
        "reference_payment",
        "reference_compensation",
        "realized_time_value",
        "realized_delay_loss",
        "realized_gain",
    ):
        if visit_row[name] == "":
            continue
        _parse_csv_number(visit_row[name])
    if party.satisfaction_status is not None and visit_row["satisfaction_status"] != party.satisfaction_status:
        raise RuntimeError(f"Formal CSV satisfaction differs for {_visit_text(party.visit_key)}.")


def _apply_formal_csv_ex_post_to_selected_party(party: PartyRecord, visit_row: dict) -> None:
    party.official_payment = _parse_csv_number(visit_row["official_payment"])
    party.official_compensation = _parse_csv_number(visit_row["official_compensation"])
    party.reference_payment = _parse_csv_number(visit_row["reference_payment"])
    party.reference_compensation = _parse_csv_number(visit_row["reference_compensation"])
    party.realized_time_value = _parse_csv_number(visit_row["realized_time_value"])
    party.realized_delay_loss = _parse_csv_number(visit_row["realized_delay_loss"])
    party.realized_gain = _parse_csv_number(visit_row["realized_gain"])
    party.satisfaction_status = visit_row["satisfaction_status"]
    party.satisfaction_reason = visit_row.get("satisfaction_reason", "")
    party.formal_route_next_link_name = visit_row.get("formal_route_next_link_name") or None
    if visit_row.get("actual_route_next_link_name", "") != "":
        party.actual_route_next_link_name = visit_row["actual_route_next_link_name"]
    party.ex_post_fields_status = REASON_EX_POST_FROM_FORMAL_CSV


def _sum_role_exclusive_amount(parties, required_role: str, attribute: str) -> float:
    total = 0.0
    for party in parties:
        value = getattr(party, attribute)
        if party.role != required_role:
            if value is not None:
                raise RuntimeError(
                    f"{_visit_text(party.visit_key)} role {party.role} has non-applicable {attribute}."
                )
            continue
        if value is None:
            raise RuntimeError(f"{_visit_text(party.visit_key)} is missing {attribute}.")
        if type(value) is bool:
            raise RuntimeError(f"{_visit_text(party.visit_key)} {attribute} is bool.")
        if type(value) is not float and type(value) is not int:
            raise RuntimeError(f"{_visit_text(party.visit_key)} {attribute} is {value!r}.")
        total = total + float(value)
    return total


def _sum_role_filtered_amount(parties, required_role: str, attribute: str) -> float:
    total = 0.0
    for party in parties:
        if party.role != required_role:
            continue
        value = getattr(party, attribute)
        if value is None:
            raise RuntimeError(f"{_visit_text(party.visit_key)} is missing {attribute}.")
        if type(value) is bool:
            raise RuntimeError(f"{_visit_text(party.visit_key)} {attribute} is bool.")
        if type(value) is not float and type(value) is not int:
            raise RuntimeError(f"{_visit_text(party.visit_key)} {attribute} is {value!r}.")
        total = total + float(value)
    return total


def _count_satisfaction(parties, role: str, status: str) -> int:
    count = 0
    for party in parties:
        if party.role == role and party.satisfaction_status == status:
            count = count + 1
    return count


def _validate_selected_ex_post_aggregates(selected: ConsideredCandidateRecord, transaction_row: dict) -> None:
    scope = [party for party in selected.parties if party.in_trade_scope is True]
    if len(scope) != 5:
        raise RuntimeError(f"Selected trade-scope party count is {len(scope)}, expected 5.")
    for party in scope:
        if party.ex_post_fields_status != REASON_EX_POST_FROM_FORMAL_CSV:
            raise RuntimeError(
                f"{_visit_text(party.visit_key)} ex_post_fields_status is {party.ex_post_fields_status!r}."
            )
    _require_close_float(
        _sum_role_exclusive_amount(scope, "buyer", "official_payment"),
        _parse_csv_number(transaction_row["buyer_official_payment_total"]),
        "buyer official payment aggregate",
    )
    _require_close_float(
        _sum_role_exclusive_amount(scope, "seller", "official_compensation"),
        _parse_csv_number(transaction_row["seller_official_compensation_total"]),
        "seller official compensation aggregate",
    )
    _require_close_float(
        _sum_role_exclusive_amount(scope, "buyer", "reference_payment"),
        _parse_csv_number(transaction_row["buyer_reference_payment_total"]),
        "buyer reference payment aggregate",
    )
    _require_close_float(
        _sum_role_exclusive_amount(scope, "seller", "reference_compensation"),
        _parse_csv_number(transaction_row["seller_reference_compensation_total"]),
        "seller reference compensation aggregate",
    )
    _require_close_float(
        _sum_role_filtered_amount(scope, "buyer", "realized_gain"),
        _parse_csv_number(transaction_row["buyer_realized_gain_total"]),
        "buyer realized gain aggregate",
    )
    _require_close_float(
        _sum_role_filtered_amount(scope, "seller", "realized_gain"),
        _parse_csv_number(transaction_row["seller_realized_gain_total"]),
        "seller realized gain aggregate",
    )
    count_pairs = (
        ("buyer", "satisfied", "buyer_satisfied_count"),
        ("buyer", "unsatisfied", "buyer_unsatisfied_count"),
        ("buyer", "unevaluated", "buyer_unevaluated_count"),
        ("seller", "satisfied", "seller_satisfied_count"),
        ("seller", "unsatisfied", "seller_unsatisfied_count"),
        ("seller", "unevaluated", "seller_unevaluated_count"),
    )
    for role, status, csv_name in count_pairs:
        diagnostic_count = _count_satisfaction(scope, role, status)
        csv_count = _parse_csv_number(transaction_row[csv_name])
        if diagnostic_count != csv_count:
            raise RuntimeError(
                f"{csv_name} is {csv_count!r}; party count for {role}/{status} is {diagnostic_count}."
            )
    for candidate in STATE.t392_considered_candidates:
        if candidate.selected is True:
            continue
        for party in candidate.parties:
            if party.ex_post_fields_status != REASON_EX_POST_NOT_SELECTED:
                raise RuntimeError(
                    f"Unselected {_visit_text(party.visit_key)} ex_post status is "
                    f"{party.ex_post_fields_status!r}."
                )
            if party.actual_is_not_realization_of_this_candidate is not True:
                raise RuntimeError(f"Unselected {_visit_text(party.visit_key)} is marked as realization.")
            for attribute in (
                "official_payment",
                "official_compensation",
                "reference_payment",
                "reference_compensation",
                "realized_time_value",
                "realized_delay_loss",
                "realized_gain",
                "satisfaction_status",
                "satisfaction_reason",
            ):
                if getattr(party, attribute) is not None:
                    raise RuntimeError(
                        f"Unselected {_visit_text(party.visit_key)} has {attribute}."
                    )


def _require_selected_party_matches_formal_row(party: PartyRecord, visit_row: dict) -> None:
    if party.satisfaction_status != visit_row["satisfaction_status"]:
        raise RuntimeError(f"Satisfaction status differs for {_visit_text(party.visit_key)}.")
    if (party.satisfaction_reason or "") != visit_row.get("satisfaction_reason", ""):
        raise RuntimeError(f"Satisfaction reason differs for {_visit_text(party.visit_key)}.")
    if party.actual_node_passage_rank != _parse_csv_number(visit_row["actual_node_passage_rank"]):
        raise RuntimeError(f"Actual passage rank differs for {_visit_text(party.visit_key)}.")
    if party.assigned_c_rank != _parse_csv_number(visit_row["assigned_rank"]):
        raise RuntimeError(f"Assigned rank differs for {_visit_text(party.visit_key)}.")
    if party.baseline_passage.value != _parse_csv_number(visit_row["baseline_passage_timestep"]):
        raise RuntimeError(f"Baseline passage differs for {_visit_text(party.visit_key)}.")
    if party.candidate_passage.value != _parse_csv_number(visit_row["candidate_passage_timestep"]):
        raise RuntimeError(f"Candidate passage differs for {_visit_text(party.visit_key)}.")
    if party.actual_passage.value != _parse_csv_number(visit_row["actual_passage_timestep"]):
        raise RuntimeError(f"Actual passage differs for {_visit_text(party.visit_key)}.")
    predicted = party.predicted_route_next_link_name or party.candidate_route_next_link_name or ""
    if visit_row["predicted_route_next_link_name"] != predicted and predicted != "":
        if visit_row["predicted_route_next_link_name"] != party.predicted_route_next_link_name:
            raise RuntimeError(f"Predicted route differs for {_visit_text(party.visit_key)}.")


def compare_existing_formal_csvs(selected: ConsideredCandidateRecord) -> tuple[str, dict]:
    _assert_existing_trial_output_paths()
    transactions = _read_formal_csv(FORMAL_TRANSACTIONS_CSV)
    visits = _read_formal_csv(FORMAL_VISITS_CSV)
    transaction_row = _find_formal_transaction_row(transactions, selected.buyers_sorted)
    _compare_formal_transaction_row(transaction_row, selected)
    for party in selected.parties:
        if party.in_trade_scope is not True:
            continue
        visit_row = _find_formal_visit_row(visits, selected.buyers_sorted, party)
        _compare_formal_visit_row(visit_row, party, selected)
        _apply_formal_csv_ex_post_to_selected_party(party, visit_row)
        _require_selected_party_matches_formal_row(party, visit_row)
    for candidate in STATE.t392_considered_candidates:
        if candidate.selected is True:
            continue
        for party in candidate.parties:
            party.official_payment = None
            party.official_compensation = None
            party.reference_payment = None
            party.reference_compensation = None
            party.realized_time_value = None
            party.realized_delay_loss = None
            party.realized_gain = None
            party.satisfaction_status = None
            party.satisfaction_reason = None
            party.ex_post_fields_status = REASON_EX_POST_NOT_SELECTED
    _validate_selected_ex_post_aggregates(selected, transaction_row)
    STATE.formal_csv_comparison_result = "matched_existing_t900_formal_csv"
    return STATE.formal_csv_comparison_result, transaction_row


CONTEXT_TIMESTEP_COLUMNS = (
    "scenario_name",
    "timestep",
    "node_name",
    "right_of_entry_selection_status",
    "right_of_entry_visit_key",
    "decision_window_visit_count",
    "confirmed_leading_nonparticipating_count",
    "remaining_decision_window_count",
    "candidate_visit_set_build_status",
    "p_minus_one_eligible_visit_count_before_limit",
    "candidate_visit_count_after_limit",
    "limit_activated",
    "considered_candidate_count",
    "selected_candidate_present",
    "selected_evaluation_index",
    "final_rank_status",
    "final_rank_visit_count",
    "newly_confirmed_visit_count",
    "already_confirmed_rank_changed",
)

CONTEXT_CANDIDATE_COLUMNS = (
    "scenario_name",
    "timestep",
    "node_name",
    "evaluation_index",
    "candidate_identity",
    "selected",
    "buyers_sorted",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "total_G",
    "total_R",
    "surplus",
    "economically_feasible",
    "unresolved",
    "unresolved_reasons",
    "infeasibility_reasons",
    "selection_reason",
)

CONTEXT_FINAL_RANK_COLUMNS = (
    "scenario_name",
    "timestep",
    "node_name",
    "final_rank_status",
    "vehicle_name",
    "visit_id",
    "VisitKey",
    "final_local_rank",
    "finalization_source",
    "formal_route_next_link_name",
    "route_origin",
    "assigned_C_rank_after_apply",
    "newly_confirmed_at_this_timestep",
)

LIMIT_POPULATION_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "max_candidate_visit_count",
    "p_minus_one_eligible_visit_count_before_limit",
    "baseline_order",
    "vehicle_name",
    "visit_id",
    "VisitKey",
    "baseline_arrival_timestep",
    "baseline_arrival_status_or_reason",
    "candidate_arrival_timestep",
    "candidate_arrival_status_or_reason",
    "actual_first_arrival_timestep",
    "actual_arrival_status_or_reason",
    "baseline_passage_timestep",
    "baseline_passage_status_or_reason",
    "candidate_passage_timestep",
    "candidate_passage_status_or_reason",
    "actual_passage_timestep",
    "actual_passage_status_or_reason",
    "arrival_tiebreaker",
    "vehicle_id",
    "within_limit",
    "beyond_limit",
    "right_of_entry",
    "in_candidate_visits",
    "in_selected_trade_scope",
    "assigned_C_rank_after_T392_apply",
)

CONSIDERED_CANDIDATE_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "evaluation_index",
    "candidate_identity",
    "selected",
    "buyers_sorted",
    "buyer_visit_keys",
    "seller_visit_keys",
    "nonparticipating_visit_keys",
    "trade_scope_visit_keys",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "baseline_local_order",
    "candidate_local_order",
    "candidate_build_status",
    "local_virtual_calculation_stop_reason",
    "resolved",
    "unresolved",
    "unresolved_reasons",
    "traffic_observation_count",
    "candidate_passage_missing_visit_keys",
    "candidate_route_missing_visit_keys",
    "total_G",
    "total_R",
    "surplus",
    "economically_feasible",
    "candidate_infeasibility_reasons",
    "selection_status",
    "selection_reason_status",
    "k_last_buyer",
    "k_decision_window",
    "k_fixed",
)

PARTY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "evaluation_index",
    "candidate_identity",
    "candidate_selected",
    "candidate_economically_feasible",
    "candidate_infeasibility_reasons",
    "candidate_selection_reason",
    "vehicle_name",
    "visit_id",
    "VisitKey",
    "role",
    "participates_in_order_exchange",
    "formal_inlink_name",
    "predicted_route_next_link_name",
    "right_of_entry_holder",
    "in_trade_scope",
    "outside_partition",
    "baseline_local_rank",
    "baseline_local_rank_status",
    "candidate_local_rank",
    "candidate_local_rank_status",
    "binding_rank",
    "binding_partition",
    "assigned_C_rank",
    "baseline_arrival_timestep",
    "baseline_arrival_status_or_reason",
    "candidate_arrival_timestep",
    "candidate_arrival_status_or_reason",
    "actual_first_arrival_timestep",
    "actual_arrival_status_or_reason",
    "baseline_passage_timestep",
    "baseline_passage_status_or_reason",
    "candidate_passage_timestep",
    "candidate_passage_status_or_reason",
    "actual_passage_timestep",
    "actual_passage_status_or_reason",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "declared_vot_per_second",
    "true_vot_per_second",
    "expected_time_saving_timesteps",
    "gross_time_value_G_b",
    "passes_positive_buyer_value_condition",
    "buyer_condition_status",
    "expected_waiting_increase_timesteps",
    "required_compensation_R_s",
    "seller_condition_status",
    "predicted_signed_time_value_change",
    "nonparticipating_external_effect_status",
    "actual_observation_available_for_visit",
    "actual_is_not_realization_of_this_candidate",
    "actual_comparison_interpretation",
    "official_payment",
    "official_compensation",
    "reference_payment",
    "reference_compensation",
    "realized_time_value",
    "realized_delay_loss",
    "realized_gain",
    "satisfaction_status",
    "satisfaction_reason",
    "actual_node_passage_rank",
    "candidate_route_next_link_name",
    "actual_route_next_link_name",
    "ex_post_fields_status",
)

SIDE_BY_SIDE_COLUMNS = (
    "evaluation_index",
    "candidate_identity",
    "candidate_selected",
    "candidate_total_G",
    "candidate_total_R",
    "candidate_surplus",
    "candidate_economically_feasible",
    "candidate_infeasibility_reasons",
    "candidate_selection_reason",
    "VisitKey",
    "role",
    "formal_inlink_name",
    "baseline_local_rank",
    "candidate_local_rank",
    "binding_rank",
    "binding_partition",
    "baseline_arrival_timestep",
    "baseline_arrival_status_or_reason",
    "candidate_arrival_timestep",
    "candidate_arrival_status_or_reason",
    "actual_first_arrival_timestep",
    "actual_arrival_status_or_reason",
    "baseline_passage_timestep",
    "baseline_passage_status_or_reason",
    "candidate_passage_timestep",
    "candidate_passage_status_or_reason",
    "actual_passage_timestep",
    "actual_passage_status_or_reason",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "declared_vot_per_second",
    "true_vot_per_second",
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "passes_positive_buyer_value_condition",
    "official_payment",
    "official_compensation",
    "realized_gain",
    "satisfaction_status",
    "actual_is_not_realization_of_this_candidate",
)

BINDING_COLUMNS = (
    "evaluation_index",
    "candidate_identity",
    "k_last_buyer",
    "k_decision_window",
    "k_fixed",
    "vehicle_name",
    "visit_id",
    "VisitKey",
    "role",
    "binding_rank",
    "binding_partition",
    "baseline_local_rank",
    "baseline_local_rank_status",
    "candidate_local_rank",
    "candidate_local_rank_status",
    "formal_inlink_name",
    "predicted_route_next_link_name",
    "baseline_arrival_timestep",
    "baseline_arrival_status_or_reason",
    "candidate_arrival_timestep",
    "candidate_arrival_status_or_reason",
    "actual_first_arrival_timestep",
    "actual_arrival_status_or_reason",
    "baseline_passage_timestep",
    "baseline_passage_status_or_reason",
    "candidate_passage_timestep",
    "candidate_passage_status_or_reason",
    "actual_passage_timestep",
    "actual_passage_status_or_reason",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "assigned_C_rank",
)

FINAL_BEYOND_COLUMNS = (
    "row_type",
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "final_rank_status",
    "VisitKey",
    "vehicle_name",
    "visit_id",
    "final_local_rank",
    "finalization_source",
    "formal_route_next_link_name",
    "route_origin",
    "assigned_C_rank",
    "baseline_arrival_timestep",
    "baseline_arrival_status_or_reason",
    "candidate_arrival_timestep",
    "candidate_arrival_status_or_reason",
    "actual_first_arrival_timestep",
    "actual_arrival_status_or_reason",
    "baseline_passage_timestep",
    "baseline_passage_status_or_reason",
    "candidate_passage_timestep",
    "candidate_passage_status_or_reason",
    "actual_passage_timestep",
    "actual_passage_status_or_reason",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "in_t392_final_rank",
    "assigned_C_rank_at_t392",
    "t392_finalization_source",
    "t392_final_rank_status",
    "confirmed_by_diagnostic_end",
    "confirmation_decision_timestep",
    "source_selected_candidate",
    "source_baseline_fallback",
    "source_leading_nonparticipating",
    "source_arrived_undetermined",
    "last_checked_timestep",
    "last_official_state",
    "unresolved_reason",
)


def validate_final_completeness(world, formal_transaction_row: dict) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_STOP:
        raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T_AFTER_STOP}.")
    if STATE.installed is not False:
        raise RuntimeError("Hooks are still installed after restore.")
    if STATE.t392_capture_count != 1:
        raise RuntimeError("T=392 capture count is not 1.")
    timesteps = [record.timestep for record in STATE.context_records]
    if len(timesteps) != len(set(timesteps)):
        raise RuntimeError("Duplicate context timesteps.")
    for timestep in timesteps:
        if timestep < CONTEXT_START_TIMESTEP or timestep > CONTEXT_END_TIMESTEP:
            raise RuntimeError(f"Context timestep {timestep} is out of range.")
    expected_context = list(range(CONTEXT_START_TIMESTEP, CONTEXT_END_TIMESTEP + 1))
    if sorted(timesteps) != expected_context:
        raise RuntimeError("Context timestep records do not cover T=388..396 exactly once.")
    selected = STATE.t392_selected_candidate
    if selected is None:
        raise RuntimeError("Selected candidate missing in final completeness.")
    if selected.buyer_count != 1 or selected.seller_count != 4 or selected.nonparticipating_count != 0:
        raise RuntimeError("Selected T=392 role counts are not buyer=1 seller=4 nonparticipating=0.")
    if selected.trade_scope_count != 5:
        raise RuntimeError("Selected trade scope count is not 5.")
    if len(STATE.t392_beyond_limit_visit_keys) < 1:
        raise RuntimeError("Beyond-limit visit count is below 1.")
    scope_keys = set()
    for party in selected.parties:
        if party.in_trade_scope is True:
            scope_keys.add(party.visit_key)
    visits = _read_formal_csv(FORMAL_VISITS_CSV)
    csv_scope = set()
    buyers_text = _join_visit_keys(selected.buyers_sorted)
    for row in visits:
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP) and row["node_name"] == TARGET_NODE_NAME:
            if row["buyers_sorted"] == buyers_text:
                csv_scope.add((row["vehicle_name"], int(row["visit_id"])))
    if csv_scope != scope_keys:
        raise RuntimeError("Selected trade scope VisitKeys differ from formal CSV.")
    csv_ranks = sorted(
        _parse_csv_number(row["assigned_rank"])
        for row in visits
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
        and row["buyers_sorted"] == buyers_text
    )
    party_ranks = sorted(
        party.assigned_c_rank for party in selected.parties if party.in_trade_scope is True
    )
    if csv_ranks != party_ranks:
        raise RuntimeError("Selected party assigned C ranks differ from formal CSV.")
    if csv_ranks != [179, 180, 181, 182, 183]:
        raise RuntimeError("Selected assigned C ranks are not C179..C183.")
    for party in selected.parties:
        if party.in_trade_scope is not True:
            continue
        visit_row = _find_formal_visit_row(visits, selected.buyers_sorted, party)
        if _parse_csv_number(visit_row["candidate_passage_timestep"]) != party.candidate_passage.value:
            raise RuntimeError(f"Candidate passage mismatch for {_visit_text(party.visit_key)}.")
        if _parse_csv_number(visit_row["actual_passage_timestep"]) != party.actual_passage.value:
            raise RuntimeError(f"Actual passage mismatch for {_visit_text(party.visit_key)}.")
    if _parse_csv_number(formal_transaction_row["buyer_satisfied_count"]) != 1:
        raise RuntimeError("Formal CSV buyer_satisfied_count is not 1.")
    if _parse_csv_number(formal_transaction_row["seller_satisfied_count"]) != 4:
        raise RuntimeError("Formal CSV seller_satisfied_count is not 4.")
    for visit_key in STATE.t392_beyond_limit_visit_keys:
        if visit_key not in STATE.beyond_limit_confirmations:
            raise RuntimeError(f"Beyond-limit {_visit_text(visit_key)} is not tracked.")
    rank_values = list(STATE.current_rank_by_visit_key.values())
    if len(rank_values) != len(set(rank_values)):
        raise RuntimeError("Duplicate C ranks at diagnostic end.")
    if len(STATE.rank_overwrites) != 0:
        raise RuntimeError("C rank overwrites detected at final completeness.")
    _validate_selected_ex_post_aggregates(selected, formal_transaction_row)


def _validate_row_contract(row: dict, columns: tuple, label: str) -> None:
    extra = set(row.keys()) - set(columns)
    if extra:
        raise RuntimeError(f"{label} row has unexpected keys: {extra}.")
    missing = set(columns) - set(row.keys())
    if missing:
        raise RuntimeError(f"{label} row is missing keys: {missing}.")


def _write_csv(path: Path, columns: tuple, rows: list[dict]) -> None:
    for index, row in enumerate(rows):
        _validate_row_contract(row, columns, f"{path.name}[{index}]")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_context_timestep_rows() -> list[dict]:
    rows = []
    for record in STATE.context_records:
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "timestep": str(record.timestep),
                "node_name": TARGET_NODE_NAME,
                "right_of_entry_selection_status": _serialize_enum(record.right_of_entry_selection_status),
                "right_of_entry_visit_key": _visit_text(record.right_of_entry_visit_key)
                if record.right_of_entry_visit_key is not None
                else "",
                "decision_window_visit_count": str(len(record.decision_window_visit_keys)),
                "confirmed_leading_nonparticipating_count": str(
                    len(record.confirmed_leading_nonparticipating_visit_keys)
                ),
                "remaining_decision_window_count": str(len(record.remaining_decision_window_visit_keys)),
                "candidate_visit_set_build_status": _serialize_enum(record.candidate_visit_set_build_status),
                "p_minus_one_eligible_visit_count_before_limit": _serialize_optional_int(
                    record.p_minus_one_eligible_visit_count_before_limit
                ),
                "candidate_visit_count_after_limit": str(record.candidate_visit_count_after_limit),
                "limit_activated": _serialize_bool(record.limit_activated),
                "considered_candidate_count": str(record.considered_candidate_count),
                "selected_candidate_present": _serialize_bool(record.selected_candidate_present),
                "selected_evaluation_index": _serialize_optional_int(record.selected_evaluation_index),
                "final_rank_status": _serialize_enum(record.final_rank_status),
                "final_rank_visit_count": str(len(record.final_rank_visit_keys)),
                "newly_confirmed_visit_count": str(len(record.newly_confirmed_visit_keys)),
                "already_confirmed_rank_changed": _serialize_bool(record.already_confirmed_rank_changed),
            }
        )
    return rows


def build_context_candidate_rows() -> list[dict]:
    rows = []
    for record in STATE.context_candidate_records:
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "timestep": str(record.timestep),
                "node_name": TARGET_NODE_NAME,
                "evaluation_index": str(record.evaluation_index),
                "candidate_identity": record.candidate_identity,
                "selected": _serialize_bool(record.selected),
                "buyers_sorted": _join_visit_keys(record.buyers_sorted),
                "buyer_count": str(record.buyer_count),
                "seller_count": str(record.seller_count),
                "nonparticipating_count": str(record.nonparticipating_count),
                "trade_scope_count": str(record.trade_scope_count),
                "total_G": "" if record.total_G is None else repr(record.total_G),
                "total_R": "" if record.total_R is None else repr(record.total_R),
                "surplus": "" if record.surplus is None else repr(record.surplus),
                "economically_feasible": _serialize_bool(record.economically_feasible),
                "unresolved": _serialize_bool(record.unresolved),
                "unresolved_reasons": _serialize_value_sequence_for_csv(
                    record.unresolved_reasons, VISIT_KEY_SEPARATOR
                ),
                "infeasibility_reasons": _serialize_value_sequence_for_csv(
                    record.infeasibility_reasons, VISIT_KEY_SEPARATOR
                ),
                "selection_reason": record.selection_reason,
            }
        )
    return rows


def build_context_final_rank_rows() -> list[dict]:
    rows = []
    for record in STATE.context_final_rank_visit_records:
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "timestep": str(record.timestep),
                "node_name": TARGET_NODE_NAME,
                "final_rank_status": _serialize_enum(record.final_rank_status),
                "vehicle_name": record.visit_key[0],
                "visit_id": str(record.visit_key[1]),
                "VisitKey": _visit_text(record.visit_key),
                "final_local_rank": str(record.final_local_rank),
                "finalization_source": _serialize_enum(record.finalization_source),
                "formal_route_next_link_name": record.formal_route_next_link_name,
                "route_origin": _serialize_enum(record.route_origin),
                "assigned_C_rank_after_apply": _serialize_optional_int(record.assigned_c_rank_after_apply),
                "newly_confirmed_at_this_timestep": _serialize_bool(record.newly_confirmed_at_this_timestep),
            }
        )
    return rows


def build_limit_population_rows() -> list[dict]:
    count_before = STATE.t392_columns.candidate_visit_node.p_minus_one_eligible_visit_count_before_limit
    rows = []
    for row in STATE.t392_prelimit_visits:
        base = {
            "scenario_name": SCENARIO_NAME,
            "tvt_decision_timestep": str(TARGET_TIMESTEP),
            "node_name": TARGET_NODE_NAME,
            "max_candidate_visit_count": str(trial.MAX_CANDIDATE_VISIT_COUNT),
            "p_minus_one_eligible_visit_count_before_limit": str(count_before),
            "baseline_order": str(row.baseline_order),
            "vehicle_name": row.vehicle_name,
            "visit_id": str(row.visit_id),
            "VisitKey": _visit_text(row.visit_key),
            "arrival_tiebreaker": str(row.arrival_tiebreaker),
            "vehicle_id": str(row.vehicle_id),
            "within_limit": _serialize_bool(row.within_limit),
            "beyond_limit": _serialize_bool(row.beyond_limit),
            "right_of_entry": _serialize_bool(row.right_of_entry),
            "in_candidate_visits": _serialize_bool(row.in_candidate_visits),
            "in_selected_trade_scope": _serialize_bool(row.in_selected_trade_scope),
            "assigned_C_rank_after_T392_apply": _serialize_optional_int(row.assigned_c_rank_after_t392),
        }
        base.update(_timed_csv_columns(row.baseline_arrival, "baseline_arrival_timestep", "baseline_arrival_status_or_reason"))
        base.update(_timed_csv_columns(row.candidate_arrival, "candidate_arrival_timestep", "candidate_arrival_status_or_reason"))
        base.update(_timed_csv_columns(row.actual_first_arrival, "actual_first_arrival_timestep", "actual_arrival_status_or_reason"))
        base.update(_timed_csv_columns(row.baseline_passage, "baseline_passage_timestep", "baseline_passage_status_or_reason"))
        base.update(_timed_csv_columns(row.candidate_passage, "candidate_passage_timestep", "candidate_passage_status_or_reason"))
        base.update(_timed_csv_columns(row.actual_passage, "actual_passage_timestep", "actual_passage_status_or_reason"))
        rows.append(base)
    return rows


def build_considered_candidate_rows() -> list[dict]:
    rows = []
    for candidate in STATE.t392_considered_candidates:
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": str(TARGET_TIMESTEP),
                "node_name": TARGET_NODE_NAME,
                "evaluation_index": str(candidate.evaluation_index),
                "candidate_identity": candidate.candidate_identity,
                "selected": _serialize_bool(candidate.selected),
                "buyers_sorted": _join_visit_keys(candidate.buyers_sorted),
                "buyer_visit_keys": _join_visit_keys(candidate.buyer_visit_keys),
                "seller_visit_keys": _join_visit_keys(candidate.seller_visit_keys),
                "nonparticipating_visit_keys": _join_visit_keys(candidate.nonparticipating_visit_keys),
                "trade_scope_visit_keys": _join_visit_keys(candidate.trade_scope_visit_keys),
                "buyer_count": str(candidate.buyer_count),
                "seller_count": str(candidate.seller_count),
                "nonparticipating_count": str(candidate.nonparticipating_count),
                "trade_scope_count": str(candidate.trade_scope_count),
                "baseline_local_order": _join_visit_keys(candidate.baseline_local_order),
                "candidate_local_order": _join_visit_keys(candidate.candidate_local_order),
                "candidate_build_status": _serialize_enum(candidate.candidate_build_status),
                "local_virtual_calculation_stop_reason": _serialize_enum(
                    candidate.local_virtual_calculation_stop_reason
                ),
                "resolved": _serialize_bool(candidate.resolved),
                "unresolved": _serialize_bool(candidate.unresolved),
                "unresolved_reasons": _serialize_value_sequence_for_csv(
                    candidate.unresolved_reasons, VISIT_KEY_SEPARATOR
                ),
                "traffic_observation_count": str(candidate.traffic_observation_count),
                "candidate_passage_missing_visit_keys": _join_visit_keys(
                    candidate.candidate_passage_missing_visit_keys
                ),
                "candidate_route_missing_visit_keys": _join_visit_keys(candidate.candidate_route_missing_visit_keys),
                "total_G": "" if candidate.total_G is None else repr(candidate.total_G),
                "total_R": "" if candidate.total_R is None else repr(candidate.total_R),
                "surplus": "" if candidate.surplus is None else repr(candidate.surplus),
                "economically_feasible": _serialize_bool(candidate.economically_feasible),
                "candidate_infeasibility_reasons": _serialize_value_sequence_for_csv(
                    candidate.candidate_infeasibility_reasons, VISIT_KEY_SEPARATOR
                ),
                "selection_status": _serialize_enum(candidate.selection_status),
                "selection_reason_status": candidate.selection_reason_status,
                "k_last_buyer": str(candidate.k_last_buyer),
                "k_decision_window": str(candidate.k_decision_window),
                "k_fixed": str(candidate.k_fixed),
            }
        )
    return rows


def _party_common_timed_fields(party: PartyRecord) -> dict:
    fields = {}
    fields.update(_timed_csv_columns(party.baseline_arrival, "baseline_arrival_timestep", "baseline_arrival_status_or_reason"))
    fields.update(_timed_csv_columns(party.candidate_arrival, "candidate_arrival_timestep", "candidate_arrival_status_or_reason"))
    fields.update(_timed_csv_columns(party.actual_first_arrival, "actual_first_arrival_timestep", "actual_arrival_status_or_reason"))
    fields.update(_timed_csv_columns(party.baseline_passage, "baseline_passage_timestep", "baseline_passage_status_or_reason"))
    fields.update(_timed_csv_columns(party.candidate_passage, "candidate_passage_timestep", "candidate_passage_status_or_reason"))
    fields.update(_timed_csv_columns(party.actual_passage, "actual_passage_timestep", "actual_passage_status_or_reason"))
    fields["baseline_minus_candidate_passage_timesteps"] = _subtract_optional_ints(
        party.baseline_passage.value, party.candidate_passage.value
    )
    fields["baseline_minus_actual_passage_timesteps"] = _subtract_optional_ints(
        party.baseline_passage.value, party.actual_passage.value
    )
    fields["candidate_minus_actual_passage_timesteps"] = _subtract_optional_ints(
        party.candidate_passage.value, party.actual_passage.value
    )
    return fields


def build_party_rows() -> list[dict]:
    rows = []
    for candidate in STATE.t392_considered_candidates:
        for party in candidate.parties:
            row = {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": str(TARGET_TIMESTEP),
                "node_name": TARGET_NODE_NAME,
                "evaluation_index": str(candidate.evaluation_index),
                "candidate_identity": candidate.candidate_identity,
                "candidate_selected": _serialize_bool(candidate.selected),
                "candidate_economically_feasible": _serialize_bool(candidate.economically_feasible),
                "candidate_infeasibility_reasons": _serialize_value_sequence_for_csv(
                    candidate.candidate_infeasibility_reasons, VISIT_KEY_SEPARATOR
                ),
                "candidate_selection_reason": candidate.selection_reason_status,
                "vehicle_name": party.vehicle_name,
                "visit_id": str(party.visit_id),
                "VisitKey": _visit_text(party.visit_key),
                "role": party.role,
                "participates_in_order_exchange": _serialize_bool(party.participates_in_order_exchange),
                "formal_inlink_name": party.formal_inlink_name or "",
                "predicted_route_next_link_name": party.predicted_route_next_link_name or "",
                "right_of_entry_holder": _serialize_bool(party.right_of_entry_holder),
                "in_trade_scope": _serialize_bool(party.in_trade_scope),
                "outside_partition": _serialize_bool(party.outside_partition),
                "baseline_local_rank": _serialize_optional_int(party.baseline_local_rank),
                "baseline_local_rank_status": party.baseline_local_rank_status,
                "candidate_local_rank": _serialize_optional_int(party.candidate_local_rank),
                "candidate_local_rank_status": party.candidate_local_rank_status,
                "binding_rank": _serialize_optional_int(party.binding_rank),
                "binding_partition": party.binding_partition or "",
                "assigned_C_rank": _serialize_optional_int(party.assigned_c_rank),
                "declared_vot_per_second": "" if party.declared_vot_per_second is None else repr(party.declared_vot_per_second),
                "true_vot_per_second": "" if party.true_vot_per_second is None else repr(party.true_vot_per_second),
                "expected_time_saving_timesteps": _serialize_optional_int(party.expected_time_saving_timesteps),
                "gross_time_value_G_b": "" if party.gross_time_value_G_b is None else repr(party.gross_time_value_G_b),
                "passes_positive_buyer_value_condition": _serialize_bool(party.passes_positive_buyer_value_condition),
                "buyer_condition_status": party.buyer_condition_status,
                "expected_waiting_increase_timesteps": _serialize_optional_int(party.expected_waiting_increase_timesteps),
                "required_compensation_R_s": "" if party.required_compensation_R_s is None else repr(party.required_compensation_R_s),
                "seller_condition_status": party.seller_condition_status,
                "predicted_signed_time_value_change": "" if party.predicted_signed_time_value_change is None else repr(party.predicted_signed_time_value_change),
                "nonparticipating_external_effect_status": party.nonparticipating_external_effect_status,
                "actual_observation_available_for_visit": _serialize_bool(party.actual_observation_available_for_visit),
                "actual_is_not_realization_of_this_candidate": _serialize_bool(party.actual_is_not_realization_of_this_candidate),
                "actual_comparison_interpretation": party.actual_comparison_interpretation,
                "official_payment": "" if party.official_payment is None else repr(party.official_payment),
                "official_compensation": "" if party.official_compensation is None else repr(party.official_compensation),
                "reference_payment": "" if party.reference_payment is None else repr(party.reference_payment),
                "reference_compensation": "" if party.reference_compensation is None else repr(party.reference_compensation),
                "realized_time_value": "" if party.realized_time_value is None else repr(party.realized_time_value),
                "realized_delay_loss": "" if party.realized_delay_loss is None else repr(party.realized_delay_loss),
                "realized_gain": "" if party.realized_gain is None else repr(party.realized_gain),
                "satisfaction_status": "" if party.satisfaction_status is None else str(party.satisfaction_status),
                "satisfaction_reason": "" if party.satisfaction_reason is None else str(party.satisfaction_reason),
                "actual_node_passage_rank": _serialize_optional_int(party.actual_node_passage_rank),
                "candidate_route_next_link_name": party.candidate_route_next_link_name or "",
                "actual_route_next_link_name": party.actual_route_next_link_name or "",
                "ex_post_fields_status": party.ex_post_fields_status,
            }
            row.update(_party_common_timed_fields(party))
            rows.append(row)
    return rows


def build_side_by_side_rows() -> list[dict]:
    rows = []
    for candidate in STATE.t392_considered_candidates:
        for party in candidate.parties:
            if party.visit_key not in candidate.trade_scope_visit_keys:
                continue
            row = {
                "evaluation_index": str(candidate.evaluation_index),
                "candidate_identity": candidate.candidate_identity,
                "candidate_selected": _serialize_bool(candidate.selected),
                "candidate_total_G": "" if candidate.total_G is None else repr(candidate.total_G),
                "candidate_total_R": "" if candidate.total_R is None else repr(candidate.total_R),
                "candidate_surplus": "" if candidate.surplus is None else repr(candidate.surplus),
                "candidate_economically_feasible": _serialize_bool(candidate.economically_feasible),
                "candidate_infeasibility_reasons": _serialize_value_sequence_for_csv(
                    candidate.candidate_infeasibility_reasons, VISIT_KEY_SEPARATOR
                ),
                "candidate_selection_reason": candidate.selection_reason_status,
                "VisitKey": _visit_text(party.visit_key),
                "role": party.role,
                "formal_inlink_name": party.formal_inlink_name or "",
                "baseline_local_rank": _serialize_optional_int(party.baseline_local_rank),
                "candidate_local_rank": _serialize_optional_int(party.candidate_local_rank),
                "binding_rank": _serialize_optional_int(party.binding_rank),
                "binding_partition": party.binding_partition or "",
            }
            row.update(_party_common_timed_fields(party))
            row["declared_vot_per_second"] = "" if party.declared_vot_per_second is None else repr(party.declared_vot_per_second)
            row["true_vot_per_second"] = "" if party.true_vot_per_second is None else repr(party.true_vot_per_second)
            row["gross_time_value_G_b"] = "" if party.gross_time_value_G_b is None else repr(party.gross_time_value_G_b)
            row["required_compensation_R_s"] = "" if party.required_compensation_R_s is None else repr(party.required_compensation_R_s)
            row["passes_positive_buyer_value_condition"] = _serialize_bool(party.passes_positive_buyer_value_condition)
            row["official_payment"] = "" if party.official_payment is None else repr(party.official_payment)
            row["official_compensation"] = "" if party.official_compensation is None else repr(party.official_compensation)
            row["realized_gain"] = "" if party.realized_gain is None else repr(party.realized_gain)
            row["satisfaction_status"] = "" if party.satisfaction_status is None else str(party.satisfaction_status)
            row["actual_is_not_realization_of_this_candidate"] = _serialize_bool(
                party.actual_is_not_realization_of_this_candidate
            )
            rows.append(row)
    return rows


def build_binding_rows() -> list[dict]:
    selected = STATE.t392_selected_candidate
    if selected is None:
        return []
    rows = []
    parties_by_key = {party.visit_key: party for party in selected.parties}
    sequence = selected.binding_sequence
    visits = sorted(sequence.visits_in_binding_order, key=lambda visit: visit.binding_rank)
    for visit in visits:
        visit_key = _plain_visit_key(visit.visit_key)
        party = parties_by_key[visit_key]
        row = {
            "evaluation_index": str(selected.evaluation_index),
            "candidate_identity": selected.candidate_identity,
            "k_last_buyer": str(selected.k_last_buyer),
            "k_decision_window": str(selected.k_decision_window),
            "k_fixed": str(selected.k_fixed),
            "vehicle_name": visit_key[0],
            "visit_id": str(visit_key[1]),
            "VisitKey": _visit_text(visit_key),
            "role": _role_name(visit.trade_role),
            "binding_rank": str(visit.binding_rank),
            "binding_partition": visit.binding_partition.value,
            "baseline_local_rank": _serialize_optional_int(party.baseline_local_rank),
            "baseline_local_rank_status": party.baseline_local_rank_status,
            "candidate_local_rank": _serialize_optional_int(party.candidate_local_rank),
            "candidate_local_rank_status": party.candidate_local_rank_status,
            "formal_inlink_name": party.formal_inlink_name or "",
            "predicted_route_next_link_name": party.predicted_route_next_link_name or "",
            "assigned_C_rank": _serialize_optional_int(party.assigned_c_rank),
        }
        row.update(_party_common_timed_fields(party))
        rows.append(row)
    return rows


def _require_beyond_limit_prelimit(visit_key) -> PrelimitVisitRecord:
    matched = [row for row in STATE.t392_prelimit_visits if row.visit_key == visit_key]
    if len(matched) != 1:
        raise RuntimeError(
            f"Beyond-limit prelimit record count for {_visit_text(visit_key)} is {len(matched)}."
        )
    record = matched[0]
    if record.beyond_limit is not True:
        raise RuntimeError(f"{_visit_text(visit_key)} prelimit record is not beyond the limit.")
    if record.visit_key != visit_key:
        raise RuntimeError(f"{_visit_text(visit_key)} prelimit VisitKey disagrees.")
    return record


def _unique_candidate_party(candidate: ConsideredCandidateRecord, visit_key) -> PartyRecord:
    matched = [party for party in candidate.parties if party.visit_key == visit_key]
    if len(matched) != 1:
        raise RuntimeError(
            f"Candidate {candidate.evaluation_index} party count for {_visit_text(visit_key)} is {len(matched)}."
        )
    return matched[0]


def _optional_candidate_party(candidate: ConsideredCandidateRecord, visit_key) -> PartyRecord | None:
    matched = [party for party in candidate.parties if party.visit_key == visit_key]
    if len(matched) == 0:
        return None
    if len(matched) != 1:
        raise RuntimeError(
            f"Candidate {candidate.evaluation_index} party count for {_visit_text(visit_key)} is {len(matched)}."
        )
    return matched[0]


def _candidate_visit_inlink_name(visit_key) -> str:
    if STATE.t392_columns is None:
        return ""
    for candidate_visit in STATE.t392_columns.candidate_visit_node.candidate_visits:
        if _plain_visit_key(candidate_visit.visit_key) == visit_key:
            inlink = candidate_visit.inlink_name
            if type(inlink) is str and inlink != "":
                return inlink
            return ""
    return ""


def _validate_summary_candidate_rank_display(candidate: ConsideredCandidateRecord) -> None:
    visit_count = trial.MAX_CANDIDATE_VISIT_COUNT
    if len(candidate.baseline_local_order) != visit_count:
        raise RuntimeError(
            f"Candidate {candidate.evaluation_index} baseline_local_order length is not {visit_count}."
        )
    if len(candidate.candidate_local_order) != visit_count:
        raise RuntimeError(
            f"Candidate {candidate.evaluation_index} candidate_local_order length is not {visit_count}."
        )
    if set(candidate.baseline_local_order) != set(candidate.candidate_local_order):
        raise RuntimeError(
            f"Candidate {candidate.evaluation_index} baseline and candidate local orders differ in VisitKeys."
        )
    for visit_key in candidate.baseline_local_order:
        if visit_key not in candidate.baseline_local_rank_by_visit_key:
            raise RuntimeError(
                f"Candidate {candidate.evaluation_index} baseline rank map lacks {_visit_text(visit_key)}."
            )
        if visit_key not in candidate.candidate_local_rank_by_visit_key:
            raise RuntimeError(
                f"Candidate {candidate.evaluation_index} candidate rank map lacks {_visit_text(visit_key)}."
            )
    binding_keys = set()
    for visit in candidate.binding_sequence.visits_in_binding_order:
        binding_keys.add(_plain_visit_key(visit.visit_key))
    for party in candidate.parties:
        if party.visit_key not in binding_keys:
            raise RuntimeError(
                f"Candidate {candidate.evaluation_index} party {_visit_text(party.visit_key)} "
                "is not in the binding sequence."
            )


def _timed_display(field: TimedField) -> str:
    if field.status == STATUS_PRESENT:
        return str(field.value)
    return field.status


def validate_all_output_table_contracts(tables: dict) -> None:
    csv_names = {name for name in OUTPUT_FILE_NAMES if name.endswith(".csv")}
    if set(tables.keys()) != csv_names:
        raise RuntimeError("Output tables do not match the CSV output file names.")
    for name, pair in tables.items():
        columns, rows = pair
        if type(columns) is not tuple:
            raise RuntimeError(f"{name} columns are not a tuple.")
        if len(columns) != len(set(columns)):
            raise RuntimeError(f"{name} columns contain a duplicate.")
        if type(rows) is not list:
            raise RuntimeError(f"{name} rows are not a list.")
        for index, row in enumerate(rows):
            if type(row) is not dict:
                raise RuntimeError(f"{name}[{index}] is not a dict.")
            _validate_row_contract(row, columns, f"{name}[{index}]")
    STATE.output_table_contracts_validated = True


def validate_prepared_research_outputs(summary_text: str, manifest: dict) -> None:
    if STATE.output_table_contracts_validated is not True:
        raise RuntimeError("Output table contracts were not validated before directory creation.")
    if type(summary_text) is not str or summary_text == "":
        raise RuntimeError("Summary text is empty.")
    if type(manifest) is not dict:
        raise RuntimeError("Manifest is not a dict.")
    if tuple(manifest.get("output_files", ())) != OUTPUT_FILE_NAMES:
        raise RuntimeError("Manifest output_files does not match OUTPUT_FILE_NAMES.")
    if manifest.get("validation_result") != "passed":
        raise RuntimeError("Manifest validation_result is not passed.")


def build_final_and_beyond_rows() -> list[dict]:
    rows = []
    for record in STATE.t392_final_rank_visits:
        row = {
            "row_type": "t392_final_rank_visit",
            "scenario_name": SCENARIO_NAME,
            "tvt_decision_timestep": str(TARGET_TIMESTEP),
            "node_name": TARGET_NODE_NAME,
            "final_rank_status": _serialize_enum(STATE.t392_final_rank_result.final_rank_status),
            "VisitKey": _visit_text(record.visit_key),
            "vehicle_name": record.visit_key[0],
            "visit_id": str(record.visit_key[1]),
            "final_local_rank": str(record.final_local_rank),
            "finalization_source": _serialize_enum(record.finalization_source),
            "formal_route_next_link_name": record.formal_route_next_link_name,
            "route_origin": _serialize_enum(record.route_origin),
            "assigned_C_rank": _serialize_optional_int(record.assigned_c_rank),
            "in_t392_final_rank": "",
            "assigned_C_rank_at_t392": "",
            "t392_finalization_source": "",
            "t392_final_rank_status": "",
            "confirmed_by_diagnostic_end": "",
            "confirmation_decision_timestep": "",
            "source_selected_candidate": "",
            "source_baseline_fallback": "",
            "source_leading_nonparticipating": "",
            "source_arrived_undetermined": "",
            "last_checked_timestep": "",
            "last_official_state": "",
            "unresolved_reason": "",
        }
        row.update(_party_common_timed_fields(record))
        rows.append(row)
    for visit_key, confirmation in STATE.beyond_limit_confirmations.items():
        row = {
            "row_type": "beyond_limit_confirmation",
            "scenario_name": SCENARIO_NAME,
            "tvt_decision_timestep": str(TARGET_TIMESTEP),
            "node_name": TARGET_NODE_NAME,
            "final_rank_status": "",
            "VisitKey": _visit_text(visit_key),
            "vehicle_name": visit_key[0],
            "visit_id": str(visit_key[1]),
            "final_local_rank": "",
            "finalization_source": confirmation.finalization_source or "",
            "formal_route_next_link_name": "",
            "route_origin": "",
            "assigned_C_rank": _serialize_optional_int(confirmation.assigned_c_rank),
            "in_t392_final_rank": _serialize_bool(confirmation.in_t392_final_rank),
            "assigned_C_rank_at_t392": _serialize_optional_int(confirmation.assigned_c_rank_at_t392),
            "t392_finalization_source": _serialize_enum(confirmation.t392_finalization_source),
            "t392_final_rank_status": _serialize_enum(confirmation.t392_final_rank_status),
            "confirmed_by_diagnostic_end": _serialize_bool(confirmation.confirmed_by_diagnostic_end),
            "confirmation_decision_timestep": _serialize_optional_int(confirmation.confirmation_decision_timestep),
            "source_selected_candidate": _serialize_bool(confirmation.source_selected_candidate),
            "source_baseline_fallback": _serialize_bool(confirmation.source_baseline_fallback),
            "source_leading_nonparticipating": _serialize_bool(confirmation.source_leading_nonparticipating),
            "source_arrived_undetermined": _serialize_bool(confirmation.source_arrived_undetermined),
            "last_checked_timestep": _serialize_optional_int(confirmation.last_checked_timestep),
            "last_official_state": confirmation.last_official_state,
            "unresolved_reason": confirmation.unresolved_reason or "",
        }
        prelimit = _require_beyond_limit_prelimit(visit_key)
        row.update(_party_common_timed_fields(prelimit))
        rows.append(row)
    return rows


def build_all_output_tables() -> dict:
    return {
        T392_CONTEXT_TIMESTEPS_CSV: (CONTEXT_TIMESTEP_COLUMNS, build_context_timestep_rows()),
        T392_CONTEXT_CANDIDATES_CSV: (CONTEXT_CANDIDATE_COLUMNS, build_context_candidate_rows()),
        T392_CONTEXT_FINAL_RANK_VISITS_CSV: (CONTEXT_FINAL_RANK_COLUMNS, build_context_final_rank_rows()),
        T392_LIMIT_POPULATION_CSV: (LIMIT_POPULATION_COLUMNS, build_limit_population_rows()),
        T392_CONSIDERED_CANDIDATES_CSV: (CONSIDERED_CANDIDATE_COLUMNS, build_considered_candidate_rows()),
        T392_CONSIDERED_CANDIDATE_PARTIES_CSV: (PARTY_COLUMNS, build_party_rows()),
        T392_CANDIDATE_SIDE_BY_SIDE_CSV: (SIDE_BY_SIDE_COLUMNS, build_side_by_side_rows()),
        T392_SELECTED_BINDING_SEQUENCE_CSV: (BINDING_COLUMNS, build_binding_rows()),
        T392_FINAL_RANK_AND_BEYOND_LIMIT_CSV: (FINAL_BEYOND_COLUMNS, build_final_and_beyond_rows()),
    }


def build_summary_text(formal_result: str) -> str:
    selected = STATE.t392_selected_candidate
    lines = [
        "1. 診断条件",
        f"scenario={SCENARIO_NAME}",
        f"target T={TARGET_TIMESTEP} node={TARGET_NODE_NAME}",
        f"diagnostic end T={DIAGNOSTIC_END_TIMESTEP} World.T after stop={EXPECTED_WORLD_T_AFTER_STOP}",
        f"max candidate visits={trial.MAX_CANDIDATE_VISIT_COUNT}",
        "",
        "2. T=388〜396の前後観測",
        f"context timesteps recorded: {len(STATE.context_records)}",
        "",
        "3. T=392の上限作動",
        f"P-1 before limit={STATE.t392_columns.candidate_visit_node.p_minus_one_eligible_visit_count_before_limit}",
        f"within limit={len(STATE.t392_within_limit_visit_keys)} beyond={len(STATE.t392_beyond_limit_visit_keys)}",
        "",
        "4. 上限適用前正式Visit列",
        f"prelimit_visit_count={len(STATE.t392_prelimit_visits)}",
        "",
        "5. 全considered Candidateの経済条件横並び",
    ]
    for candidate in STATE.t392_considered_candidates:
        lines.append(
            f"  index={candidate.evaluation_index} selected={candidate.selected} "
            f"buyers={_join_visit_keys(candidate.buyers_sorted)} "
            f"b/s/n/t={candidate.buyer_count}/{candidate.seller_count}/"
            f"{candidate.nonparticipating_count}/{candidate.trade_scope_count} "
            f"resolved={candidate.resolved} G={candidate.total_G} R={candidate.total_R} "
            f"surplus={candidate.surplus} feasible={candidate.economically_feasible} "
            f"infeasibility={_serialize_value_sequence_for_csv(candidate.candidate_infeasibility_reasons, VISIT_KEY_SEPARATOR)} "
            f"selection={candidate.selection_reason_status} "
            f"k={candidate.k_last_buyer}/{candidate.k_decision_window}/{candidate.k_fixed}"
        )
    lines.append("")
    lines.append("6. 各CandidateのBaseline／Candidate順位横並び")
    for candidate in STATE.t392_considered_candidates:
        _validate_summary_candidate_rank_display(candidate)
        lines.append(f"  Candidate index={candidate.evaluation_index} identity={candidate.candidate_identity}")
        lines.append("  A. Baseline local order")
        for visit_key in candidate.baseline_local_order:
            baseline_rank = candidate.baseline_local_rank_by_visit_key[visit_key]
            candidate_rank = candidate.candidate_local_rank_by_visit_key[visit_key]
            party = _optional_candidate_party(candidate, visit_key)
            if party is not None:
                value_text = ""
                if party.role == "buyer":
                    value_text = (
                        f"G_b={party.gross_time_value_G_b} "
                        f"positive={party.passes_positive_buyer_value_condition}"
                    )
                elif party.role == "seller":
                    value_text = f"R_s={party.required_compensation_R_s}"
                lines.append(
                    f"    rank={baseline_rank} {_visit_text(visit_key)} "
                    f"role={party.role} inlink={party.formal_inlink_name} "
                    f"candidate_rank={candidate_rank} binding_rank={party.binding_rank} "
                    f"partition={party.binding_partition} "
                    f"arr B/C/A={_timed_display(party.baseline_arrival)}/"
                    f"{_timed_display(party.candidate_arrival)}/{_timed_display(party.actual_first_arrival)} "
                    f"pass B/C/A={_timed_display(party.baseline_passage)}/"
                    f"{_timed_display(party.candidate_passage)}/{_timed_display(party.actual_passage)} "
                    f"{value_text}"
                )
            else:
                inlink = _candidate_visit_inlink_name(visit_key)
                inlink_text = inlink if inlink != "" else ""
                lines.append(
                    f"    rank={baseline_rank} {_visit_text(visit_key)} "
                    f"role={SUMMARY_NOT_IN_BINDING_SEQUENCE} inlink={inlink_text} "
                    f"candidate_rank={candidate_rank} binding_rank={SUMMARY_NOT_IN_BINDING_SEQUENCE} "
                    f"partition={SUMMARY_NOT_IN_BINDING_SEQUENCE} "
                    f"detail_status={SUMMARY_NOT_IN_BINDING_SEQUENCE}"
                )
        lines.append("  B. Candidate local order")
        for visit_key in candidate.candidate_local_order:
            baseline_rank = candidate.baseline_local_rank_by_visit_key[visit_key]
            candidate_rank = candidate.candidate_local_rank_by_visit_key[visit_key]
            party = _optional_candidate_party(candidate, visit_key)
            if party is not None:
                lines.append(
                    f"    candidate_rank={candidate_rank} {_visit_text(visit_key)} "
                    f"role={party.role} baseline_rank={baseline_rank} "
                    f"binding_rank={party.binding_rank} partition={party.binding_partition}"
                )
            else:
                lines.append(
                    f"    candidate_rank={candidate_rank} {_visit_text(visit_key)} "
                    f"role={SUMMARY_NOT_IN_BINDING_SEQUENCE} baseline_rank={baseline_rank} "
                    f"binding_rank={SUMMARY_NOT_IN_BINDING_SEQUENCE} "
                    f"partition={SUMMARY_NOT_IN_BINDING_SEQUENCE}"
                )
    lines.append("")
    lines.append("7. selected Candidateのbinding sequence")
    if selected is not None:
        for visit in sorted(selected.binding_sequence.visits_in_binding_order, key=lambda item: item.binding_rank):
            visit_key = _plain_visit_key(visit.visit_key)
            party = _unique_candidate_party(selected, visit_key)
            lines.append(
                f"  bind={visit.binding_rank} partition={visit.binding_partition.value} "
                f"{_visit_text(visit_key)} role={party.role} "
                f"baseline_rank={party.baseline_local_rank} candidate_rank={party.candidate_local_rank} "
                f"C={party.assigned_c_rank}"
            )
    lines.append("")
    lines.append("8. selected CandidateのActual・経済実績")
    if selected is not None:
        for party in selected.parties:
            if party.in_trade_scope is not True:
                continue
            lines.append(
                f"  {_visit_text(party.visit_key)} pay={party.official_payment} comp={party.official_compensation} "
                f"gain={party.realized_gain} satisfaction={party.satisfaction_status} "
                f"ex_post_status={party.ex_post_fields_status}"
            )
    lines.append("")
    lines.append("9. 上限外Visitの順位確定結果")
    for visit_key, confirmation in STATE.beyond_limit_confirmations.items():
        lines.append(
            f"  {_visit_text(visit_key)} confirmed={confirmation.confirmed_by_diagnostic_end} "
            f"at T={confirmation.confirmation_decision_timestep} C={confirmation.assigned_c_rank} "
            f"state={confirmation.last_official_state}"
        )
    lines.append("")
    lines.append("10. C順位整合")
    lines.append(f"rank_overwrite_count={len(STATE.rank_overwrites)}")
    lines.append("")
    lines.append("11. 既存T=900正式CSVとの照合結果")
    lines.append(f"formal_csv_comparison_result={formal_result}")
    lines.append("")
    lines.append("12. 検証結論")
    lines.append("T=430までの診断simulationと正式CSV照合は矛盾なく完了した。")
    lines.append("")
    lines.append("13. この診断で一般証明していない事項")
    lines.append("T=900までの全decisionの再計算やproduction全体の正当性は証明しない。")
    lines.append("診断simulationはT=430まで処理し終了後World.T=431。T=900まで再計算していない。")
    lines.append("既存T=900 CSVから診断内未観測値を補完していない。Candidate arrivalを推定していない。")
    lines.append("非選択CandidateのActual値は当該Candidateの実現結果ではない。")
    return "\n".join(lines) + "\n"


def _count_timed_present(records, attribute: str) -> int:
    count = 0
    for record in records:
        field = getattr(record, attribute)
        if field.status == STATUS_PRESENT:
            count = count + 1
    return count


def build_manifest(row_counts: dict) -> dict:
    selected = STATE.t392_selected_candidate
    all_parties = []
    for candidate in STATE.t392_considered_candidates:
        all_parties.extend(candidate.parties)
    reason_counts: dict[str, int] = {}
    for party in all_parties:
        for field in (
            party.baseline_arrival,
            party.candidate_arrival,
            party.actual_first_arrival,
            party.baseline_passage,
            party.candidate_passage,
            party.actual_passage,
        ):
            if field.status != STATUS_PRESENT:
                reason_counts[field.status] = reason_counts.get(field.status, 0) + 1
    beyond_status_counts: dict[str, int] = {}
    for confirmation in STATE.beyond_limit_confirmations.values():
        key = confirmation.last_official_state
        beyond_status_counts[key] = beyond_status_counts.get(key, 0) + 1
    return {
        "diagnostic_script": _SCRIPT.name,
        "scenario_name": SCENARIO_NAME,
        "max_candidate_visit_count": trial.MAX_CANDIDATE_VISIT_COUNT,
        "target_timestep": TARGET_TIMESTEP,
        "target_node_name": TARGET_NODE_NAME,
        "context_start_timestep": CONTEXT_START_TIMESTEP,
        "context_end_timestep": CONTEXT_END_TIMESTEP,
        "diagnostic_end_timestep": DIAGNOSTIC_END_TIMESTEP,
        "diagnostic_last_processed_timestep": DIAGNOSTIC_LAST_PROCESSED_TIMESTEP,
        "diagnostic_world_t_after_execution": EXPECTED_WORLD_T_AFTER_STOP,
        "target_visit_tracking_end_timestep": TARGET_VISIT_TRACKING_END_TIMESTEP,
        "stopped_before_formal_evaluation_end": True,
        "existing_full_trial_output_used_for_read_only_comparison": True,
        "existing_full_trial_output_directory": str(EXISTING_FULL_TRIAL_OUTPUT_DIR),
        "output_files": list(OUTPUT_FILE_NAMES),
        "row_counts": row_counts,
        "context_timestep_count": len(STATE.context_records),
        "considered_candidate_count": len(STATE.t392_considered_candidates),
        "selected_evaluation_index": selected.evaluation_index if selected else None,
        "prelimit_visit_count": len(STATE.t392_prelimit_visits),
        "within_limit_visit_count": len(STATE.t392_within_limit_visit_keys),
        "beyond_limit_visit_count": len(STATE.t392_beyond_limit_visit_keys),
        "selected_trade_scope_count": selected.trade_scope_count if selected else None,
        "baseline_arrival_present_count": _count_timed_present(all_parties, "baseline_arrival"),
        "candidate_arrival_present_count": _count_timed_present(all_parties, "candidate_arrival"),
        "actual_arrival_present_count": _count_timed_present(all_parties, "actual_first_arrival"),
        "baseline_passage_present_count": _count_timed_present(all_parties, "baseline_passage"),
        "candidate_passage_present_count": _count_timed_present(all_parties, "candidate_passage"),
        "actual_passage_present_count": _count_timed_present(all_parties, "actual_passage"),
        "missing_value_reason_counts": reason_counts,
        "beyond_limit_confirmation_status_counts": beyond_status_counts,
        "rank_overwrite_count": len(STATE.rank_overwrites),
        "formal_csv_comparison_result": STATE.formal_csv_comparison_result,
        "validation_result": "passed",
    }


def write_research_outputs(tables: dict, summary_text: str, manifest: dict) -> None:
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    for name, (columns, rows) in tables.items():
        _write_csv(OUTPUT_DIR / name, columns, rows)
    (OUTPUT_DIR / T392_LIMIT_ACTIVATION_SUMMARY).write_text(summary_text, encoding="utf-8")
    manifest_path = OUTPUT_DIR / MANIFEST_JSON
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(_serialize_manifest_value(manifest), handle, indent=2, sort_keys=True)
        handle.write("\n")
    present = {path.name for path in OUTPUT_DIR.iterdir()}
    expected = set(OUTPUT_FILE_NAMES)
    if present != expected:
        raise RuntimeError(f"Output directory contents {present!r} != expected {expected!r}.")


def validate_static_contract() -> None:
    source = _SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if TARGET_TIMESTEP != 392:
        raise RuntimeError("TARGET_TIMESTEP must be 392.")
    if TARGET_NODE_NAME != "northwest_intersection":
        raise RuntimeError("TARGET_NODE_NAME must be northwest_intersection.")
    if CONTEXT_START_TIMESTEP != 388 or CONTEXT_END_TIMESTEP != 396:
        raise RuntimeError("Context window must be T=388..396.")
    if DIAGNOSTIC_END_TIMESTEP != 430 or EXPECTED_WORLD_T_AFTER_STOP != 431:
        raise RuntimeError("Diagnostic stop must leave World.T=431.")
    if trial.MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("Trial MAX_CANDIDATE_VISIT_COUNT must be 5.")
    if not (CONTEXT_START_TIMESTEP < TARGET_TIMESTEP < CONTEXT_END_TIMESTEP < DIAGNOSTIC_END_TIMESTEP):
        raise RuntimeError("Timestep ordering constant check failed.")
    if str(OUTPUT_DIR) == str(EXISTING_FULL_TRIAL_OUTPUT_DIR):
        raise RuntimeError("Output directory equals existing trial output directory.")
    if "candidate_limit_5" not in OUTPUT_DIR.name:
        raise RuntimeError("Output directory name must include candidate_limit_5.")
    if "t392_limit_activation" not in OUTPUT_DIR.name:
        raise RuntimeError("Output directory name must include t392_limit_activation.")
    if len(OUTPUT_FILE_NAMES) != len(set(OUTPUT_FILE_NAMES)):
        raise RuntimeError("OUTPUT_FILE_NAMES contains duplicates.")
    for name in OUTPUT_FILE_NAMES:
        if name not in source:
            raise RuntimeError(f"Missing output file name {name} in source.")
    required_symbols = (
        "wrapped_driver",
        "wrapped_arrival",
        "install_hooks",
        "restore_hooks",
        "_capture_t392",
        "compare_existing_formal_csvs",
        "validate_final_completeness",
        "write_research_outputs",
        "candidate_visits",
        "trade_order",
        "assigned_rank",
        "binding_rank",
        "actual_is_not_realization_of_this_candidate",
        "REASON_EX_POST_FROM_FORMAL_CSV",
        "REASON_EX_POST_NOT_SELECTED",
    )
    for symbol in required_symbols:
        if symbol not in source:
            raise RuntimeError(f"Missing required symbol {symbol} in source.")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != "main":
            continue
        if not isinstance(func.value, ast.Name):
            continue
        if func.value.id == "trial":
            raise RuntimeError("Diagnostic must not call trial.main.")
    static_functions: list[ast.FunctionDef] = []
    main_functions: list[ast.FunctionDef] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name == "validate_static_contract":
            static_functions.append(node)
        elif node.name == "main":
            main_functions.append(node)
    if len(static_functions) != 1:
        raise RuntimeError("validate_static_contract must exist once.")
    if len(main_functions) != 1:
        raise RuntimeError("main must exist once.")
    static_function = static_functions[0]
    main_function = main_functions[0]
    main_source = ast.get_source_segment(source, main_function) or ""
    call_names = []
    for node in ast.walk(main_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            call_names.append((getattr(node, "lineno", 0), node.func.id))
    call_names.sort(key=lambda item: item[0])
    ordered_calls = [name for _line, name in call_names]
    required_order = (
        "build_all_output_tables",
        "validate_all_output_table_contracts",
        "validate_prepared_research_outputs",
        "write_research_outputs",
    )
    previous = -1
    for name in required_order:
        if name not in ordered_calls:
            raise RuntimeError(f"main does not call {name}.")
        position = ordered_calls.index(name)
        if position < previous:
            raise RuntimeError(f"main calls {name} out of the required order.")
        previous = position
    if "write_research_outputs" not in main_source:
        raise RuntimeError("main must call write_research_outputs after validation.")
    if main_source.index("compare_existing_formal_csvs") > main_source.index("write_research_outputs"):
        raise RuntimeError("Output directory must be created after formal CSV comparison.")
    for node in ast.walk(static_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "exec_simulation":
                raise RuntimeError("Static validation must not call exec_simulation.")
            if node.func.attr == "mkdir":
                raise RuntimeError("Static validation must not mkdir.")
            if node.func.attr == "install_hooks":
                raise RuntimeError("Static validation must not install hooks.")
    print("static contract ok")

def _prepare_world():
    world = trial.build_world()
    vot_values = trial._true_vot_sequence()
    vot_records = trial.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
    trial.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
    trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    if world.order_control_tvt_max_candidate_visit_count != trial.MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("World candidate limit is not the N=5 trial constant.")
    if world.name != trial.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name is not the N=5 trial name.")
    return world


def _run_until_diagnostic_end(world) -> None:
    until_t = DIAGNOSTIC_LAST_PROCESSED_TIMESTEP * world.DELTAT
    end_ts = int(until_t / world.DELTAT)
    if end_ts != DIAGNOSTIC_LAST_PROCESSED_TIMESTEP:
        raise RuntimeError(
            f"until_t={until_t!r} does not select timestep {DIAGNOSTIC_LAST_PROCESSED_TIMESTEP}."
        )
    world.exec_simulation(until_t=until_t)
    STATE.world_t_after_stop = world.T
    if world.T != EXPECTED_WORLD_T_AFTER_STOP:
        raise RuntimeError(
            f"World.T after stop is {world.T}, expected {EXPECTED_WORLD_T_AFTER_STOP} "
            f"after processing T={DIAGNOSTIC_LAST_PROCESSED_TIMESTEP}."
        )


def main(argv=None) -> int:
    if argv is None:
        arguments = sys.argv[1:]
    else:
        arguments = list(argv)
    if len(arguments) > 1:
        raise SystemExit("Unexpected CLI arguments.")
    if len(arguments) == 1:
        if arguments[0] != "--static-validate-only":
            raise SystemExit(f"Unknown CLI option: {arguments[0]!r}.")
        validate_static_contract()
        return 0
    _refuse_existing_output_directory()
    original_limit = sys.getrecursionlimit()
    try:
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_hooks(world)
        try:
            _run_until_diagnostic_end(world)
        finally:
            restore_hooks()
        _apply_actual_times(world)
        validate_captured_foundation(world)
        selected = STATE.t392_selected_candidate
        if selected is None:
            raise RuntimeError("Selected candidate is missing before formal CSV comparison.")
        formal_result, formal_transaction_row = compare_existing_formal_csvs(selected)
        validate_final_completeness(world, formal_transaction_row)
        tables = build_all_output_tables()
        validate_all_output_table_contracts(tables)
        row_counts = {name: len(rows) for name, (_columns, rows) in tables.items()}
        summary_text = build_summary_text(formal_result)
        manifest = build_manifest(row_counts)
        validate_prepared_research_outputs(summary_text, manifest)
        write_research_outputs(tables, summary_text, manifest)
        print(f"diagnostic_end_timestep={DIAGNOSTIC_END_TIMESTEP}")
        print(f"world_T={world.T}")
        print(f"considered_candidate_count={len(STATE.t392_considered_candidates)}")
        print(f"selected_evaluation_index={selected.evaluation_index}")
        print(
            "before_limit_count="
            f"{STATE.t392_columns.candidate_visit_node.p_minus_one_eligible_visit_count_before_limit}"
        )
        print(f"within_limit_count={len(STATE.t392_within_limit_visit_keys)}")
        print(f"beyond_limit_count={len(STATE.t392_beyond_limit_visit_keys)}")
        print(f"output_directory={OUTPUT_DIR}")
        return 0
    finally:
        restore_hooks()
        sys.setrecursionlimit(original_limit)


if __name__ == "__main__":
    raise SystemExit(main())
