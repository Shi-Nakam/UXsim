"""
Review the T=392 northwest selected trade under candidate visit limit N=5.

Captures the pre-limit six-visit population, selected five-visit trade scope,
all considered candidates, and beyond-limit C-rank follow-up through T=430.
Does not infer inlinks from vehicle names or OD labels.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial as trial
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateTrafficObservationRecord,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpSellerEconomicRecord,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_TIMESTEP = 392
TARGET_NODE_NAME = "northwest_intersection"
SIMULATION_UNTIL_TIMESTEP = 430
EXPECTED_WORLD_T_AFTER_SIM = 431
FLOAT_REL_TOL = 1e-12
FLOAT_ABS_TOL = 1e-12
SCENARIO_NAME = trial.SCENARIO_NAME

BEYOND_LIMIT_VISIT_KEY = ("veh_wn_se_base_025", 1)
ARRIVAL_TRACKED_VISIT_KEYS = frozenset(
    {
        ("veh_en_sw_base_026", 2),
        ("veh_sw_nw_base_039", 2),
        ("veh_sw_nw_base_040", 2),
        ("veh_wn_en_base_025", 1),
        ("veh_nw_sw_base_048", 1),
        BEYOND_LIMIT_VISIT_KEY,
    }
)
REASON_NOT_STORED = "not_stored_on_formal_object"
REASON_NOT_CANDIDATE_TARGET = "not_candidate_visit_target"
REASON_C_RANK_NOT_ASSIGNED = "c_rank_not_assigned_at_snapshot"
REASON_C_SOURCE_UNKNOWN = "c_rank_source_not_observed_yet"

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t392_maximum_party_transaction_review"
    )
)
SIX_VISIT_CSV = "t392_n5_six_visit_side_by_side.csv"
CANDIDATE_ORDER_CSV = "t392_n5_selected_candidate_order.csv"
TRANSACTION_CSV = "t392_n5_selected_transaction_summary.csv"
CONSIDERED_CANDIDATES_CSV = "t392_n5_considered_candidates.csv"
SUMMARY_NAME = "t392_n5_review.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    SIX_VISIT_CSV,
    CANDIDATE_ORDER_CSV,
    TRANSACTION_CSV,
    CONSIDERED_CANDIDATES_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)

SIX_VISIT_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "baseline_local_rank",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "formal_inlink_name",
    "within_limit",
    "beyond_limit",
    "selected_trade_role",
    "candidate_local_rank",
    "baseline_arrival_timestep",
    "candidate_arrival_status_or_timestep",
    "actual_first_arrival_timestep",
    "baseline_passage_timestep",
    "candidate_passage_status_or_timestep",
    "actual_passage_timestep",
    "assigned_node_continuous_rank",
    "c_rank_confirmation_timestep",
    "c_rank_confirmation_source",
    "hook_raw_arrival_time",
    "world_deltat",
    "hook_arrival_time_over_deltat",
    "hook_formal_arrival_timestep",
)

CONSIDERED_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "evaluation_index",
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
    "infeasibility_reasons",
    "selection_reason",
    "k_last_buyer",
    "k_decision_window",
    "k_fixed",
)

PARTY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "selected_candidate_evaluation_index",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "role",
    "participates_in_order_exchange",
    "is_right_of_entry_holder",
    "formal_inlink_name",
    "predicted_route_next_link_name",
    "formal_route_next_link_name",
    "actual_route_next_link_name",
    "baseline_arrival_timestep",
    "actual_first_arrival_timestep",
    "actual_minus_baseline_arrival_timesteps",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "baseline_local_rank",
    "post_trade_local_rank",
    "binding_rank",
    "binding_partition",
    "assigned_node_continuous_rank",
    "actual_node_passage_rank",
    "actual_rank_change",
    "true_vot_per_second",
    "declared_vot_per_second",
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "individual_economic_condition_status",
    "passes_positive_buyer_value_condition",
    "official_payment",
    "official_compensation",
    "reference_payment",
    "reference_compensation",
    "realized_time_value",
    "realized_delay_loss",
    "realized_gain",
    "satisfaction_status",
    "satisfaction_reason",
)

TRANSACTION_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "selected_candidate_evaluation_index",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "total_G",
    "total_R",
    "surplus",
    "total_official_payment",
    "total_official_compensation",
    "payment_balance_difference",
    "payment_balance_satisfied",
    "total_reference_payment",
    "total_reference_compensation",
    "buyer_realized_gain_total",
    "seller_realized_gain_total",
    "buyer_satisfied_count",
    "seller_satisfied_count",
    "buyer_unsatisfied_count",
    "seller_unsatisfied_count",
    "actual_observed_party_count",
    "rank_difference_total",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.original_arrival = None
        self.captured = False
        self.parties: list[dict] = []
        self.six_visits: list[dict] = []
        self.considered_candidates: list[dict] = []
        self.transaction: dict | None = None
        self.arrivals: dict[tuple[str, int], int] = {}
        self.arrival_audit: dict[tuple[str, int], dict] = {}
        self.tracked_visit_keys: set[tuple[str, int]] = set()
        self.c_rank_first_timestep: dict[tuple[str, int], int] = {}
        self.c_rank_finalization_source: dict[tuple[str, int], str] = {}
        self.beyond_limit: dict = {}
        self.csv_compare_notes: list[str] = []
        self.deltat = None
        self.selected_evaluation_index: int | None = None
        self.p_minus_one_count: int | None = None


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _require_bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise RuntimeError(f"{label} must be bool; got {type(value).__name__}.")
    return value


def _require_non_negative_int(value, label: str) -> int:
    if type(value) is not int or type(value) is bool or value < 0:
        raise RuntimeError(f"{label} must be a non-negative int; got {value!r}.")
    return value


def _snapshot_pre_driver_rank_membership(world) -> dict:
    rank_states = world.order_control_tvt_rank_states_by_node_name
    rank_state = rank_states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError("Northwest rank state is missing before T=392 driver.")
    confirmed_visit_keys = frozenset(
        _plain_visit_key(visit_key) for visit_key in rank_state.confirmed_visit_keys_in_order()
    )
    undetermined_visit_keys = frozenset(
        _plain_visit_key(visit_key) for visit_key in rank_state.undetermined_visit_keys()
    )
    overlap = confirmed_visit_keys & undetermined_visit_keys
    if len(overlap) != 0:
        raise RuntimeError("Pre-driver confirmed and undetermined visit keys overlap.")
    return {
        "confirmed_visit_keys": confirmed_visit_keys,
        "undetermined_visit_keys": undetermined_visit_keys,
    }


def _p_minus_one_export_records(
    collector, pre_driver_rank_membership, node_name: str, p: int
) -> list[dict]:
    confirmed_visit_keys = pre_driver_rank_membership["confirmed_visit_keys"]
    undetermined_visit_keys = pre_driver_rank_membership["undetermined_visit_keys"]
    exported = collector.export_node_baseline_visits(node_name)
    selected: list[dict] = []
    for record in exported:
        if _require_bool(record["was_arrived_at_snapshot"], "was_arrived_at_snapshot"):
            continue
        visit_key = (record["vehicle_name"], record["visit_id"])
        if visit_key in undetermined_visit_keys:
            pass
        elif visit_key in confirmed_visit_keys:
            continue
        else:
            raise RuntimeError(f"{_visit_text(visit_key)} is neither undetermined nor confirmed.")
        arrival_value = record["baseline_arrival_timestep"]
        if arrival_value is None:
            continue
        arrival_timestep = _require_non_negative_int(arrival_value, "baseline_arrival_timestep")
        if arrival_timestep > p - 1:
            continue
        selected.append(record)
    selected.sort(
        key=lambda record: (
            record["baseline_arrival_timestep"],
            record["arrival_tiebreaker"],
            record["vehicle_id"],
        )
    )
    return selected


def _candidate_order_keys(trade_result) -> list:
    ordered = []
    for visit_key in trade_result.trade_order:
        ordered.append(_plain_visit_key(visit_key))
    return ordered


def _serialize_reasons(reasons) -> str:
    if len(reasons) == 0:
        return ""
    parts = []
    for reason in reasons:
        parts.append(reason.value if hasattr(reason, "value") else str(reason))
    return "|".join(parts)


def _track_rank_events(world, result) -> None:
    if world is not GATE.real_world:
        return
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return
    for visit_key in ARRIVAL_TRACKED_VISIT_KEYS:
        assigned = rank_state.assigned_rank(visit_key)
        if assigned is not None and visit_key not in GATE.c_rank_first_timestep:
            GATE.c_rank_first_timestep[visit_key] = world.T
            if visit_key == BEYOND_LIMIT_VISIT_KEY and GATE.beyond_limit:
                if GATE.beyond_limit.get("first_confirmation_timestep") is None:
                    GATE.beyond_limit["first_confirmation_timestep"] = world.T
    if isinstance(result, OrderControlTvtMpDriverResult):
        atomic = result.atomic_apply_set_result
        if atomic is None:
            return
        validation_set = atomic.final_consistency_validation_set_result
        final_rank_set = validation_set.final_rank_set_result
        for node_result in final_rank_set.node_final_rank_results:
            if node_result.node_name != TARGET_NODE_NAME:
                continue
            GATE.beyond_limit["last_final_rank_status"] = node_result.final_rank_status.value
            for final_visit in node_result.final_rank_visits:
                visit_key = _plain_visit_key(final_visit.visit_key)
                GATE.c_rank_finalization_source[visit_key] = final_visit.finalization_source.value
                if visit_key == BEYOND_LIMIT_VISIT_KEY:
                    GATE.beyond_limit["final_rank_status"] = node_result.final_rank_status.value
                    GATE.beyond_limit["finalization_source"] = final_visit.finalization_source.value


def _close(left, right) -> bool:
    return math.isclose(left, right, rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


def _require_close(left, right, label: str) -> None:
    if type(left) is bool or type(right) is bool:
        raise RuntimeError(f"{label} is bool.")
    if _close(float(left), float(right)) is not True:
        raise RuntimeError(f"{label}: {left!r} != {right!r}.")


def _formal_arrival_timestep(arrival_time, deltat) -> int:
    formal_timestep = int(round(arrival_time / deltat))
    if type(formal_timestep) is not int or type(formal_timestep) is bool or formal_timestep < 0:
        raise RuntimeError(f"Formal arrival timestep is {formal_timestep!r}.")
    return formal_timestep


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _one_node(results, node_name: str, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"T={TARGET_TIMESTEP} {node_name}: {label} count is {count}.")
    return matched


def _saved_columns(atomic) -> dict:
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
    fork_result = arrived_set.alignment_fork_result.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError("Saved fork_result type is wrong.")
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError("Saved collector type is wrong.")
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
    }


def _evaluation_index(economic_results, selected_economic) -> int:
    found = None
    index = 0
    for candidate_economic in economic_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if found is not None:
                raise RuntimeError("Selected economic result appears more than once.")
            found = index
    if found is None:
        raise RuntimeError("Selected economic result is missing from the node list.")
    return found


def _role_name(role) -> str:
    if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return "buyer"
    if role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return "seller"
    if role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return "nonparticipating"
    raise RuntimeError(f"Unsupported trade role {role!r}.")


def _baseline_order(candidate_visits) -> list:
    ordered = []
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError("candidate_visits entry type is wrong.")
        ordered.append(_plain_visit_key(candidate_visit.visit_key))
    return ordered


def _trade_result_for_buyers(trade_rank_node, buyers_sorted):
    if not isinstance(trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError("Trade rank node type is wrong.")
    found = None
    for trade_result in trade_rank_node.candidate_trade_rank_results:
        candidate_buyers = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted)
        if candidate_buyers != buyers_sorted:
            continue
        if found is not None:
            raise RuntimeError("Two trade results share the selected buyers.")
        found = trade_result
    if found is None or not isinstance(found, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError("No trade result matches the selected buyers.")
    return found


def _records_by_key(records, label: str) -> dict:
    mapping = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(f"{label} repeats {_visit_text(visit_key)}.")
        mapping[visit_key] = record
    return mapping


def _capture_t392(world, result, pre_driver_rank_membership) -> None:
    if GATE.captured is True:
        raise RuntimeError("T=392 northwest transaction was saved twice.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"Driver result type is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError("T=392 atomic_apply_set_result is None.")
    if pre_driver_rank_membership is None:
        raise RuntimeError("T=392 pre-driver rank membership snapshot is missing.")
    columns = _saved_columns(atomic)
    selection_node = _one_node(columns["selection_nodes"], TARGET_NODE_NAME, "selection")
    selected_economic = selection_node.selected_candidate_economic_result
    if selected_economic is None:
        raise RuntimeError("T=392 northwest has no selected candidate.")
    economic_node = _one_node(columns["economic_nodes"], TARGET_NODE_NAME, "economic")
    evaluation_index = _evaluation_index(
        economic_node.candidate_economic_evaluation_results,
        selected_economic,
    )
    local_result = selected_economic.candidate_local_virtual_calculation_result
    sequence = local_result.binding_rank_sequence
    buyers_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    trade_rank_node = _one_node(columns["trade_rank_nodes"], TARGET_NODE_NAME, "trade rank")
    trade_result = _trade_result_for_buyers(trade_rank_node, buyers_sorted)
    candidate_visit_node = _one_node(
        columns["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate visits"
    )
    if trial.MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("Trial MAX_CANDIDATE_VISIT_COUNT is not 5.")
    count_before = candidate_visit_node.p_minus_one_eligible_visit_count_before_limit
    if count_before != 6:
        raise RuntimeError(f"P-1 eligible count before limit is {count_before}, not 6.")
    p = candidate_visit_node.right_of_entry_baseline_passage_timestep
    if type(p) is not int or type(p) is bool:
        raise RuntimeError("Right-of-entry passage timestep is missing.")
    before_limit_records = _p_minus_one_export_records(
        columns["collector"], pre_driver_rank_membership, TARGET_NODE_NAME, p
    )
    if len(before_limit_records) != 6:
        raise RuntimeError(f"Rebuilt P-1 population count is {len(before_limit_records)}, not 6.")
    baseline_order = _baseline_order(candidate_visit_node.candidate_visits)
    if len(baseline_order) != 5:
        raise RuntimeError("candidate_visits count is not 5.")
    rebuilt_keys = [
        (record["vehicle_name"], record["visit_id"]) for record in before_limit_records
    ]
    if rebuilt_keys[:5] != baseline_order:
        raise RuntimeError("First five P-1 visits do not match candidate_visits order.")
    sixth_key = rebuilt_keys[5]
    if sixth_key != BEYOND_LIMIT_VISIT_KEY:
        raise RuntimeError(f"Sixth P-1 visit is {_visit_text(sixth_key)}, not beyond-limit visit.")
    undetermined_before = pre_driver_rank_membership["undetermined_visit_keys"]
    for visit_key in rebuilt_keys:
        if visit_key not in undetermined_before:
            raise RuntimeError(
                f"{_visit_text(visit_key)} was not undetermined in the pre-driver rank snapshot."
            )
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError("Northwest rank state is missing after T=392.")
    candidate_order = _candidate_order_keys(trade_result)
    binding_by_key = {}
    for binding_visit in sequence.visits_in_binding_order:
        binding_by_key[_plain_visit_key(binding_visit.visit_key)] = binding_visit
    traffic_by_key = _records_by_key(local_result.traffic_observation_records, "traffic")
    buyer_records = _records_by_key(selected_economic.buyer_economic_records, "buyer economic")
    seller_records = _records_by_key(selected_economic.seller_economic_records, "seller economic")
    right_node = _one_node(columns["right_of_entry_nodes"], TARGET_NODE_NAME, "right of entry")
    right_of_entry = None
    if right_node.right_of_entry_visit_key is not None:
        right_of_entry = _plain_visit_key(right_node.right_of_entry_visit_key)
    scope = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.trade_scope)
    buyer_keys = []
    seller_keys = []
    nonparticipating_keys = []
    for visit_key in scope:
        binding_visit = binding_by_key.get(visit_key)
        if binding_visit is None:
            raise RuntimeError(f"{_visit_text(visit_key)} missing from binding sequence.")
        role_name = _role_name(binding_visit.trade_role)
        if role_name == "buyer":
            buyer_keys.append(visit_key)
        elif role_name == "seller":
            seller_keys.append(visit_key)
        else:
            nonparticipating_keys.append(visit_key)
    if len(buyer_keys) != 1 or len(seller_keys) != 4 or len(nonparticipating_keys) != 0:
        raise RuntimeError("Selected trade scope role counts differ from N=5 expectation.")
    if len(scope) != 5:
        raise RuntimeError("Selected trade scope count is not 5.")
    if sixth_key in scope:
        raise RuntimeError("Beyond-limit visit is inside selected trade scope.")
    expected_c_ranks_after_driver = {
        ("veh_nw_sw_base_048", 1): 179,
        ("veh_en_sw_base_026", 2): 180,
        ("veh_sw_nw_base_039", 2): 181,
        ("veh_sw_nw_base_040", 2): 182,
        ("veh_wn_en_base_025", 1): 183,
    }
    for visit_key in scope:
        assigned_after = rank_state.assigned_rank(visit_key)
        if assigned_after != expected_c_ranks_after_driver[visit_key]:
            raise RuntimeError(
                f"{_visit_text(visit_key)} post-driver C rank is {assigned_after!r}."
            )
    identity = f"T={TARGET_TIMESTEP}|{TARGET_NODE_NAME}|index={evaluation_index}"
    GATE.tracked_visit_keys = set(rebuilt_keys)
    GATE.p_minus_one_count = count_before
    GATE.selected_evaluation_index = evaluation_index
    GATE.beyond_limit = {
        "visit_key": _visit_text(BEYOND_LIMIT_VISIT_KEY),
        "c_rank_at_t392": rank_state.assigned_rank(BEYOND_LIMIT_VISIT_KEY),
        "first_confirmation_timestep": None,
        "assigned_c_rank": None,
        "final_rank_status": None,
        "finalization_source": None,
        "last_final_rank_status": None,
    }
    six_visits = []
    scope_set = set(scope)
    within_keys = set(baseline_order)
    for baseline_rank, record in enumerate(before_limit_records, start=1):
        visit_key = (record["vehicle_name"], record["visit_id"])
        formal_inlink = record["inlink_name"]
        if type(formal_inlink) is not str or formal_inlink == "":
            raise RuntimeError(f"{_visit_text(visit_key)} collector inlink is missing.")
        within_limit = visit_key in within_keys
        beyond_limit = visit_key == sixth_key
        if within_limit and beyond_limit:
            raise RuntimeError("Visit cannot be both within limit and beyond limit.")
        selected_role = ""
        if visit_key in scope_set:
            selected_role = _role_name(binding_by_key[visit_key].trade_role)
        elif beyond_limit:
            selected_role = "beyond_candidate_limit"
        candidate_local_rank = ""
        if visit_key in scope_set:
            candidate_local_rank = str(trade_result.assigned_rank(visit_key))
        elif within_limit:
            candidate_local_rank = REASON_NOT_CANDIDATE_TARGET
        else:
            candidate_local_rank = REASON_NOT_CANDIDATE_TARGET
        baseline_arrival = record["baseline_arrival_timestep"]
        baseline_passage = record["baseline_passage_timestep"]
        candidate_arrival_field = REASON_NOT_STORED
        candidate_passage_field = REASON_NOT_CANDIDATE_TARGET
        if visit_key in scope_set:
            traffic = traffic_by_key.get(visit_key)
            if not isinstance(traffic, OrderControlTvtMpCandidateTrafficObservationRecord):
                raise RuntimeError(f"{_visit_text(visit_key)} traffic record is missing.")
            binding_visit = binding_by_key[visit_key]
            if formal_inlink != binding_visit.inlink_name:
                raise RuntimeError(f"{_visit_text(visit_key)} collector/binding inlink differ.")
            candidate_passage_field = str(traffic.candidate_passage_timestep)
        assigned_c = rank_state.assigned_rank(visit_key)
        c_confirm_t = GATE.c_rank_first_timestep.get(visit_key)
        if c_confirm_t is None and assigned_c is not None:
            c_confirm_t = TARGET_TIMESTEP
        c_source = GATE.c_rank_finalization_source.get(visit_key, REASON_C_SOURCE_UNKNOWN)
        audit = GATE.arrival_audit.get(visit_key, {})
        six_visits.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": TARGET_TIMESTEP,
                "node_name": TARGET_NODE_NAME,
                "baseline_local_rank": baseline_rank,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "formal_inlink_name": formal_inlink,
                "within_limit": within_limit,
                "beyond_limit": beyond_limit,
                "selected_trade_role": selected_role,
                "candidate_local_rank": candidate_local_rank,
                "baseline_arrival_timestep": baseline_arrival,
                "candidate_arrival_status_or_timestep": candidate_arrival_field,
                "actual_first_arrival_timestep": GATE.arrivals.get(visit_key),
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_status_or_timestep": candidate_passage_field,
                "actual_passage_timestep": None,
                "assigned_node_continuous_rank": assigned_c,
                "c_rank_confirmation_timestep": c_confirm_t,
                "c_rank_confirmation_source": c_source,
                "hook_raw_arrival_time": audit.get("raw_arrival_time"),
                "world_deltat": audit.get("deltat"),
                "hook_arrival_time_over_deltat": audit.get("arrival_time_over_deltat"),
                "hook_formal_arrival_timestep": audit.get("formal_arrival_timestep"),
            }
        )
    considered = []
    selection_status_text = selection_node.selection_status.value
    for index, candidate_economic in enumerate(
        economic_node.candidate_economic_evaluation_results, start=1
    ):
        candidate_local = candidate_economic.candidate_local_virtual_calculation_result
        candidate_sequence = candidate_local.binding_rank_sequence
        candidate_buyers = tuple(
            _plain_visit_key(visit_key)
            for visit_key in candidate_sequence.concrete_buyer_candidate_set.buyers_sorted
        )
        candidate_trade = _trade_result_for_buyers(trade_rank_node, candidate_buyers)
        candidate_scope = tuple(
            _plain_visit_key(visit_key) for visit_key in candidate_trade.trade_scope
        )
        counts = {"buyer": 0, "seller": 0, "nonparticipating": 0}
        for visit_key in candidate_scope:
            binding_visit = None
            for visit in candidate_sequence.visits_in_binding_order:
                if _plain_visit_key(visit.visit_key) == visit_key:
                    binding_visit = visit
                    break
            if binding_visit is None:
                raise RuntimeError(f"Candidate {index} scope visit missing binding.")
            counts[_role_name(binding_visit.trade_role)] = counts[_role_name(binding_visit.trade_role)] + 1
        selected_flag = candidate_economic is selected_economic
        if selected_flag:
            selection_reason = selection_status_text
        elif candidate_economic.economically_feasible is not True:
            selection_reason = "not_selected_infeasible"
        else:
            selection_reason = "not_selected"
        considered.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": TARGET_TIMESTEP,
                "node_name": TARGET_NODE_NAME,
                "evaluation_index": index,
                "selected": selected_flag,
                "buyers_sorted": "|".join(_visit_text(key) for key in candidate_buyers),
                "buyer_count": counts["buyer"],
                "seller_count": counts["seller"],
                "nonparticipating_count": counts["nonparticipating"],
                "trade_scope_count": len(candidate_scope),
                "total_G": candidate_economic.total_buyer_value_G,
                "total_R": candidate_economic.total_required_compensation_R,
                "surplus": candidate_economic.surplus,
                "economically_feasible": candidate_economic.economically_feasible,
                "infeasibility_reasons": _serialize_reasons(candidate_economic.infeasibility_reasons),
                "selection_reason": selection_reason,
                "k_last_buyer": candidate_sequence.k_last_buyer,
                "k_decision_window": candidate_sequence.k_decision_window,
                "k_fixed": candidate_sequence.k_fixed,
            }
        )
    parties = []
    for visit_key in scope:
        binding_visit = binding_by_key[visit_key]
        traffic = traffic_by_key.get(visit_key)
        if not isinstance(traffic, OrderControlTvtMpCandidateTrafficObservationRecord):
            raise RuntimeError(f"{_visit_text(visit_key)} is missing traffic.")
        role_name = _role_name(binding_visit.trade_role)
        if traffic.inlink_name != binding_visit.inlink_name:
            raise RuntimeError(f"{_visit_text(visit_key)} inlink sources differ.")
        snapshot = columns["collector"].get_baseline_visit_snapshot(visit_key[0], visit_key[1])
        if snapshot is None:
            raise RuntimeError(f"{_visit_text(visit_key)} baseline snapshot is missing.")
        if snapshot.get("inlink_name") != binding_visit.inlink_name:
            raise RuntimeError(f"{_visit_text(visit_key)} snapshot inlink differs from binding.")
        if snapshot.get("baseline_arrival_timestep") != binding_visit.baseline_arrival_timestep:
            raise RuntimeError(f"{_visit_text(visit_key)} baseline arrival sources differ.")
        vehicle = world.VEHICLES.get(visit_key[0])
        if vehicle is None:
            raise RuntimeError(f"Vehicle {visit_key[0]!r} is missing.")
        participates = vehicle.participates_in_order_exchange
        if role_name == "buyer":
            buyer_record = buyer_records.get(visit_key)
            if not isinstance(buyer_record, OrderControlTvtMpBuyerEconomicRecord):
                raise RuntimeError(f"{_visit_text(visit_key)} buyer economic record is missing.")
            if visit_key in seller_records:
                raise RuntimeError(f"{_visit_text(visit_key)} also has a seller record.")
            gross = buyer_record.gross_time_value_G_b
            required = None
            passes = buyer_record.passes_positive_buyer_value_condition
            declared = buyer_record.declared_vot_per_second
            if passes is True:
                status = "passes_positive_buyer_value_condition"
            elif passes is False:
                status = "fails_positive_buyer_value_condition"
            else:
                raise RuntimeError("passes_positive_buyer_value_condition is not bool.")
            expected_g = (
                (buyer_record.baseline_passage_timestep - buyer_record.candidate_passage_timestep)
                * world.DELTAT
                * declared
            )
            _require_close(gross, expected_g, f"{_visit_text(visit_key)} G_b")
        else:
            seller_record = seller_records.get(visit_key)
            if not isinstance(seller_record, OrderControlTvtMpSellerEconomicRecord):
                raise RuntimeError(f"{_visit_text(visit_key)} seller economic record is missing.")
            if visit_key in buyer_records:
                raise RuntimeError(f"{_visit_text(visit_key)} also has a buyer record.")
            gross = None
            required = seller_record.required_compensation_R_s
            passes = None
            declared = seller_record.declared_vot_per_second
            status = None
            expected_r = (
                (seller_record.candidate_passage_timestep - seller_record.baseline_passage_timestep)
                * world.DELTAT
                * declared
            )
            _require_close(required, expected_r, f"{_visit_text(visit_key)} R_s")
        baseline_passage = snapshot.get("baseline_passage_timestep")
        candidate_passage = traffic.candidate_passage_timestep
        post_trade_rank = trade_result.assigned_rank(visit_key)
        assigned_rank = rank_state.assigned_rank(visit_key)
        parties.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": TARGET_TIMESTEP,
                "node_name": TARGET_NODE_NAME,
                "candidate_identity": identity,
                "selected_candidate_evaluation_index": evaluation_index,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "visit_key_tuple": visit_key,
                "role": role_name,
                "participates_in_order_exchange": participates,
                "is_right_of_entry_holder": visit_key == right_of_entry,
                "formal_inlink_name": binding_visit.inlink_name,
                "predicted_route_next_link_name": binding_visit.route_next_link_name,
                "formal_route_next_link_name": rank_state.formal_route_next_link_name(visit_key),
                "baseline_arrival_timestep": binding_visit.baseline_arrival_timestep,
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_passage,
                "baseline_local_rank": baseline_order.index(visit_key) + 1,
                "post_trade_local_rank": post_trade_rank,
                "binding_rank": binding_visit.binding_rank,
                "binding_partition": binding_visit.binding_partition.value,
                "assigned_node_continuous_rank": assigned_rank,
                "true_vot_per_second": traffic.true_vot_per_second,
                "declared_vot_per_second": declared,
                "gross_time_value_G_b": gross,
                "required_compensation_R_s": required,
                "individual_economic_condition_status": status,
                "passes_positive_buyer_value_condition": passes,
            }
        )
    if len(buyer_records) != 1 or len(seller_records) != 4:
        raise RuntimeError("Buyer or seller economic record count differs from N=5 expectation.")
    GATE.captured = True
    GATE.deltat = world.DELTAT
    GATE.parties = parties
    GATE.six_visits = six_visits
    GATE.considered_candidates = considered
    GATE.transaction = {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": TARGET_TIMESTEP,
        "node_name": TARGET_NODE_NAME,
        "candidate_identity": identity,
        "selected_candidate_evaluation_index": evaluation_index,
        "buyers_sorted": buyers_sorted,
        "candidate_local_order": candidate_order,
        "baseline_local_order": baseline_order,
        "total_G": selected_economic.total_buyer_value_G,
        "total_R": selected_economic.total_required_compensation_R,
        "surplus": selected_economic.surplus,
        "buyer_count": len(buyer_keys),
        "seller_count": len(seller_keys),
        "nonparticipating_count": len(nonparticipating_keys),
        "trade_scope_count": len(scope),
    }


def wrapped_driver(world):
    pre_driver_rank_membership = None
    if world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is None:
            if world.T == TARGET_TIMESTEP:
                pre_driver_rank_membership = _snapshot_pre_driver_rank_membership(world)
    result = GATE.original_driver(world)
    if world is GATE.real_world:
        _track_rank_events(world, result)
        if world.T == TARGET_TIMESTEP:
            if pre_driver_rank_membership is None:
                raise RuntimeError("T=392 pre-driver rank membership snapshot is missing.")
            _capture_t392(world, result, pre_driver_rank_membership)
    return result


def wrapped_arrival(vehicle, node):
    result = GATE.original_arrival(vehicle, node)
    if vehicle.W is not GATE.real_world:
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
    key = (vehicle.name, visit_id)
    if key not in ARRIVAL_TRACKED_VISIT_KEYS:
        return result
    arrival_time = current_visit.get("arrival_time")
    if arrival_time is None:
        return result
    deltat = vehicle.W.DELTAT
    formal_timestep = _formal_arrival_timestep(arrival_time, deltat)
    ratio = arrival_time / deltat
    if key not in GATE.arrival_audit:
        GATE.arrival_audit[key] = {
            "raw_arrival_time": arrival_time,
            "deltat": deltat,
            "arrival_time_over_deltat": ratio,
            "formal_arrival_timestep": formal_timestep,
        }
    if key not in GATE.arrivals:
        if formal_timestep != vehicle.W.T:
            raise RuntimeError(
                f"First arrival {_visit_text(key)} formal {formal_timestep} != World.T {vehicle.W.T}."
            )
        GATE.arrivals[key] = formal_timestep
    else:
        from_production = _formal_arrival_timestep(arrival_time, deltat)
        if GATE.arrivals[key] != from_production:
            raise RuntimeError(f"Re-registration changed arrival for {_visit_text(key)}.")
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Diagnostic hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = GATE.original_arrival
    GATE.original_driver = None
    GATE.original_arrival = None
    GATE.real_world = None
    GATE.installed = False


def _selected_buyers_sorted_text() -> str:
    return "|".join(_visit_text(visit_key) for visit_key in GATE.transaction["buyers_sorted"])


def _require_csv_number(text, label: str):
    value = _parse_number(text)
    if value is None:
        raise RuntimeError(f"{label} is missing in trial CSV.")
    return value


def _require_csv_blank(value, label: str) -> None:
    if value is None or value == "":
        return
    raise RuntimeError(f"{label} must be blank in trial CSV.")


def _transaction_adapter_from_csv(csv_transaction: dict):
    """Adapter for post-T=900 formal trial transaction CSV (read-only ex-post totals)."""
    return SimpleNamespace(
        buyer_official_payment_total=_require_csv_number(
            csv_transaction["buyer_official_payment_total"],
            "buyer_official_payment_total",
        ),
        seller_official_compensation_total=_require_csv_number(
            csv_transaction["seller_official_compensation_total"],
            "seller_official_compensation_total",
        ),
        buyer_reference_payment_total=_require_csv_number(
            csv_transaction["buyer_reference_payment_total"],
            "buyer_reference_payment_total",
        ),
        seller_reference_compensation_total=_require_csv_number(
            csv_transaction["seller_reference_compensation_total"],
            "seller_reference_compensation_total",
        ),
        buyer_realized_gain_total=_require_csv_number(
            csv_transaction["buyer_realized_gain_total"],
            "buyer_realized_gain_total",
        ),
        seller_realized_gain_total=_require_csv_number(
            csv_transaction["seller_realized_gain_total"],
            "seller_realized_gain_total",
        ),
        buyer_satisfied_count=_require_csv_number(
            csv_transaction["buyer_satisfied_count"],
            "buyer_satisfied_count",
        ),
        buyer_unsatisfied_count=_require_csv_number(
            csv_transaction["buyer_unsatisfied_count"],
            "buyer_unsatisfied_count",
        ),
        seller_satisfied_count=_require_csv_number(
            csv_transaction["seller_satisfied_count"],
            "seller_satisfied_count",
        ),
        seller_unsatisfied_count=_require_csv_number(
            csv_transaction["seller_unsatisfied_count"],
            "seller_unsatisfied_count",
        ),
        rank_difference_evaluated_count=_require_csv_number(
            csv_transaction["rank_difference_evaluated_count"],
            "rank_difference_evaluated_count",
        ),
        rank_difference_unavailable_count=_require_csv_number(
            csv_transaction["rank_difference_unavailable_count"],
            "rank_difference_unavailable_count",
        ),
    )


def _apply_trial_visit_csv_to_party(party: dict, visit: dict) -> None:
    """Merge T=900 formal visit CSV ex-post fields; compare pre-ex-post fields to T=392 capture."""
    if visit["role"] != party["role"]:
        raise RuntimeError(f"{party['visit_key']} CSV role differs from formal object.")
    baseline_passage_csv = _require_csv_number(
        visit["baseline_passage_timestep"], f"{party['visit_key']} CSV baseline passage"
    )
    if baseline_passage_csv != party["baseline_passage_timestep"]:
        raise RuntimeError(f"{party['visit_key']} baseline passage differs from formal object.")
    candidate_passage_csv = _require_csv_number(
        visit["candidate_passage_timestep"], f"{party['visit_key']} CSV candidate passage"
    )
    if candidate_passage_csv != party["candidate_passage_timestep"]:
        raise RuntimeError(f"{party['visit_key']} candidate passage differs from formal object.")
    assigned_rank_csv = _require_csv_number(visit["assigned_rank"], f"{party['visit_key']} CSV assigned rank")
    if assigned_rank_csv != party["assigned_node_continuous_rank"]:
        raise RuntimeError(f"{party['visit_key']} assigned rank differs from formal object.")
    if visit["predicted_route_next_link_name"] != party["predicted_route_next_link_name"]:
        raise RuntimeError(f"{party['visit_key']} predicted route differs from formal object.")
    _require_close(
        _require_csv_number(visit["true_vot_per_second"], f"{party['visit_key']} CSV true VOT"),
        party["true_vot_per_second"],
        f"{party['visit_key']} true VOT",
    )
    formal_route_csv = visit.get("formal_route_next_link_name", "")
    if formal_route_csv != "" and formal_route_csv != party["formal_route_next_link_name"]:
        raise RuntimeError(f"{party['visit_key']} formal route differs from formal object.")

    arrival = GATE.arrivals.get(party["visit_key_tuple"])
    party["actual_first_arrival_timestep"] = arrival
    if arrival is None:
        party["actual_minus_baseline_arrival_timesteps"] = None
    else:
        party["actual_minus_baseline_arrival_timesteps"] = arrival - party["baseline_arrival_timestep"]

    actual_passage = _require_csv_number(
        visit["actual_passage_timestep"], f"{party['visit_key']} CSV actual passage"
    )
    party["actual_passage_timestep"] = actual_passage
    party["actual_route_next_link_name"] = visit["actual_route_next_link_name"]
    party["actual_node_passage_rank"] = _require_csv_number(
        visit["actual_node_passage_rank"], f"{party['visit_key']} CSV actual passage rank"
    )
    party["actual_rank_change"] = _parse_number(visit["actual_rank_change"])

    role = party["role"]
    if role not in ("buyer", "seller"):
        raise RuntimeError(f"{party['visit_key']} unsupported role {role!r}.")
    satisfaction_status = visit["satisfaction_status"]
    if satisfaction_status == "":
        raise RuntimeError(f"{party['visit_key']} satisfaction_status is blank in trial CSV.")
    party["satisfaction_status"] = satisfaction_status
    party["satisfaction_reason"] = visit["satisfaction_reason"]
    party["realized_gain"] = _require_csv_number(
        visit["realized_gain"], f"{party['visit_key']} CSV realized gain"
    )

    visit_key_label = party["visit_key"]
    if role == "buyer":
        _require_csv_blank(visit["official_compensation"], f"{visit_key_label} CSV official compensation")
        _require_csv_blank(visit["reference_compensation"], f"{visit_key_label} CSV reference compensation")
        _require_csv_blank(visit["realized_delay_loss"], f"{visit_key_label} CSV realized delay loss")
        party["official_payment"] = _require_csv_number(
            visit["official_payment"], f"{visit_key_label} CSV official payment"
        )
        party["official_compensation"] = None
        party["reference_payment"] = _require_csv_number(
            visit["reference_payment"], f"{visit_key_label} CSV reference payment"
        )
        party["reference_compensation"] = None
        party["realized_time_value"] = _require_csv_number(
            visit["realized_time_value"], f"{visit_key_label} CSV realized time value"
        )
        party["realized_delay_loss"] = None
    else:
        _require_csv_blank(visit["official_payment"], f"{visit_key_label} CSV official payment")
        _require_csv_blank(visit["reference_payment"], f"{visit_key_label} CSV reference payment")
        _require_csv_blank(visit["realized_time_value"], f"{visit_key_label} CSV realized time value")
        party["official_payment"] = None
        party["official_compensation"] = _require_csv_number(
            visit["official_compensation"], f"{visit_key_label} CSV official compensation"
        )
        party["reference_payment"] = None
        party["reference_compensation"] = _require_csv_number(
            visit["reference_compensation"], f"{visit_key_label} CSV reference compensation"
        )
        party["realized_time_value"] = None
        party["realized_delay_loss"] = _require_csv_number(
            visit["realized_delay_loss"], f"{visit_key_label} CSV realized delay loss"
        )

    if party["baseline_passage_timestep"] is None or party["candidate_passage_timestep"] is None:
        raise RuntimeError(f"{party['visit_key']} passage is missing.")
    party["baseline_minus_candidate_passage_timesteps"] = (
        party["baseline_passage_timestep"] - party["candidate_passage_timestep"]
    )
    party["baseline_minus_actual_passage_timesteps"] = (
        party["baseline_passage_timestep"] - actual_passage
    )
    party["candidate_minus_actual_passage_timesteps"] = (
        party["candidate_passage_timestep"] - actual_passage
    )


def _join_existing_trial_csv():
    """
    Read existing N=5 T=900 formal trial CSV (read-only).

    Ex-post passage, payment, compensation, satisfaction, and realized gains come from
    the formal CSV. Actual first arrival remains from the T=430 real-World hook (GATE.arrivals).
    """
    transactions = _read_csv(trial.TRIAL_OUTPUT_DIR / "tvt_mp_transactions.csv")
    visits = _read_csv(trial.TRIAL_OUTPUT_DIR / "tvt_mp_visits.csv")
    buyers_text = _selected_buyers_sorted_text()
    matched_transactions = [
        row
        for row in transactions
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
        and row["buyers_sorted"] == buyers_text
    ]
    if len(matched_transactions) != 1:
        raise RuntimeError(f"Trial transaction CSV matched {len(matched_transactions)} rows.")
    csv_transaction = matched_transactions[0]
    transaction_row = _transaction_adapter_from_csv(csv_transaction)
    GATE.csv_compare_notes.append("join_existing_trial_csv: selected transaction matched")

    for party in GATE.parties:
        visit_matches = [
            row
            for row in visits
            if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
            and row["node_name"] == TARGET_NODE_NAME
            and row["buyers_sorted"] == buyers_text
            and row["vehicle_name"] == party["vehicle_name"]
            and row["visit_id"] == str(party["visit_id"])
            and row["role"] == party["role"]
        ]
        if len(visit_matches) != 1:
            raise RuntimeError(f"Trial visit CSV match count for {party['visit_key']} is {len(visit_matches)}.")
        _apply_trial_visit_csv_to_party(party, visit_matches[0])

    GATE.csv_compare_notes.append("join_existing_trial_csv: selected visit rows merged")
    _sync_six_visit_rows_from_parties()
    return transaction_row


def _sync_six_visit_rows_from_parties() -> None:
    party_by_key = {(party["vehicle_name"], party["visit_id"]): party for party in GATE.parties}
    for row in GATE.six_visits:
        visit_key = (row["vehicle_name"], row["visit_id"])
        party = party_by_key.get(visit_key)
        if party is None:
            continue
        row["actual_passage_timestep"] = party.get("actual_passage_timestep")
        row["actual_first_arrival_timestep"] = party.get("actual_first_arrival_timestep")
        audit = GATE.arrival_audit.get(visit_key, {})
        row["hook_raw_arrival_time"] = audit.get("raw_arrival_time")
        row["world_deltat"] = audit.get("deltat")
        row["hook_arrival_time_over_deltat"] = audit.get("arrival_time_over_deltat")
        row["hook_formal_arrival_timestep"] = audit.get("formal_arrival_timestep")


def _finalize_beyond_limit(world) -> None:
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError("Northwest rank state missing at end of simulation.")
    key = BEYOND_LIMIT_VISIT_KEY
    GATE.beyond_limit["assigned_c_rank"] = rank_state.assigned_rank(key)
    GATE.beyond_limit["first_confirmation_timestep"] = GATE.c_rank_first_timestep.get(key)
    for row in GATE.six_visits:
        if (row["vehicle_name"], row["visit_id"]) != key:
            continue
        row["assigned_node_continuous_rank"] = rank_state.assigned_rank(key)
        row["c_rank_confirmation_timestep"] = GATE.c_rank_first_timestep.get(key)
        row["c_rank_confirmation_source"] = GATE.c_rank_finalization_source.get(
            key, REASON_C_SOURCE_UNKNOWN
        )


def _finish_transaction(transaction_row) -> dict:
    buyer_g = 0.0
    seller_r = 0.0
    payment = 0.0
    compensation = 0.0
    reference_payment = 0.0
    reference_compensation = 0.0
    buyer_gain = 0.0
    seller_gain = 0.0
    buyer_satisfied = 0
    seller_satisfied = 0
    buyer_unsatisfied = 0
    seller_unsatisfied = 0
    observed = 0
    rank_difference = 0
    for party in GATE.parties:
        if party["role"] == "buyer":
            buyer_g = buyer_g + party["gross_time_value_G_b"]
            payment = payment + party["official_payment"]
            reference_payment = reference_payment + party["reference_payment"]
            buyer_gain = buyer_gain + party["realized_gain"]
            if party["satisfaction_status"] == "satisfied":
                buyer_satisfied = buyer_satisfied + 1
            else:
                buyer_unsatisfied = buyer_unsatisfied + 1
            if party["official_compensation"] is not None or party["required_compensation_R_s"] is not None:
                raise RuntimeError(f"{party['visit_key']} buyer compensation field is present.")
        else:
            seller_r = seller_r + party["required_compensation_R_s"]
            compensation = compensation + party["official_compensation"]
            reference_compensation = reference_compensation + party["reference_compensation"]
            seller_gain = seller_gain + party["realized_gain"]
            if party["satisfaction_status"] == "satisfied":
                seller_satisfied = seller_satisfied + 1
            else:
                seller_unsatisfied = seller_unsatisfied + 1
            if party["official_payment"] is not None or party["gross_time_value_G_b"] is not None:
                raise RuntimeError(f"{party['visit_key']} seller payment field is present.")
        if party["actual_passage_timestep"] is not None:
            observed = observed + 1
        rank_difference = rank_difference + (
            party["assigned_node_continuous_rank"] - party["actual_node_passage_rank"]
        )
    surplus = GATE.transaction["surplus"]
    _require_close(buyer_g, GATE.transaction["total_G"], "sum G_b")
    _require_close(seller_r, GATE.transaction["total_R"], "sum R_s")
    _require_close(surplus, GATE.transaction["total_G"] - GATE.transaction["total_R"], "surplus")
    _require_close(payment, transaction_row.buyer_official_payment_total, "payment sum")
    _require_close(compensation, transaction_row.seller_official_compensation_total, "compensation sum")
    difference = payment - compensation
    balanced = _close(payment, compensation)
    row = {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": TARGET_TIMESTEP,
        "node_name": TARGET_NODE_NAME,
        "candidate_identity": GATE.transaction["candidate_identity"],
        "selected_candidate_evaluation_index": GATE.selected_evaluation_index,
        "buyer_count": GATE.transaction["buyer_count"],
        "seller_count": GATE.transaction["seller_count"],
        "nonparticipating_count": GATE.transaction["nonparticipating_count"],
        "trade_scope_count": GATE.transaction["trade_scope_count"],
        "total_G": GATE.transaction["total_G"],
        "total_R": GATE.transaction["total_R"],
        "surplus": surplus,
        "total_official_payment": payment,
        "total_official_compensation": compensation,
        "payment_balance_difference": difference,
        "payment_balance_satisfied": balanced,
        "total_reference_payment": reference_payment,
        "total_reference_compensation": reference_compensation,
        "buyer_realized_gain_total": buyer_gain,
        "seller_realized_gain_total": seller_gain,
        "buyer_satisfied_count": buyer_satisfied,
        "seller_satisfied_count": seller_satisfied,
        "buyer_unsatisfied_count": buyer_unsatisfied,
        "seller_unsatisfied_count": seller_unsatisfied,
        "actual_observed_party_count": observed,
        "rank_difference_total": rank_difference,
    }
    return row


def _validate_runtime(world, transaction_row, summary_row) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T_AFTER_SIM}.")
    if GATE.captured is not True or len(GATE.parties) != 5:
        raise RuntimeError("T=392 selected five-party capture is missing.")
    if len(GATE.six_visits) != 6:
        raise RuntimeError("Six-visit side-by-side capture is missing.")
    expected_scope_roles = {
        ("veh_nw_sw_base_048", 1): "buyer",
        ("veh_en_sw_base_026", 2): "seller",
        ("veh_sw_nw_base_039", 2): "seller",
        ("veh_sw_nw_base_040", 2): "seller",
        ("veh_wn_en_base_025", 1): "seller",
    }
    if set(party["visit_key_tuple"] for party in GATE.parties) != set(expected_scope_roles):
        raise RuntimeError("Selected trade scope VisitKey set differs.")
    for party in GATE.parties:
        expected_role = expected_scope_roles[party["visit_key_tuple"]]
        if party["role"] != expected_role:
            raise RuntimeError(f"{party['visit_key']} role is {party['role']!r}.")
        if party["actual_first_arrival_timestep"] is None or party["actual_passage_timestep"] is None:
            raise RuntimeError(f"{party['visit_key']} arrival or actual passage is missing.")
        if party["actual_node_passage_rank"] is None:
            raise RuntimeError(f"{party['visit_key']} actual passage rank is missing.")
        if party["participates_in_order_exchange"] is not True:
            raise RuntimeError(f"{party['visit_key']} participation flag is wrong.")
    expected_candidate_order = [
        ("veh_nw_sw_base_048", 1),
        ("veh_en_sw_base_026", 2),
        ("veh_sw_nw_base_039", 2),
        ("veh_sw_nw_base_040", 2),
        ("veh_wn_en_base_025", 1),
    ]
    if GATE.transaction["candidate_local_order"] != expected_candidate_order:
        raise RuntimeError("Selected candidate local order differs from formal trade_order.")
    expected_c_ranks = {
        ("veh_nw_sw_base_048", 1): 179,
        ("veh_en_sw_base_026", 2): 180,
        ("veh_sw_nw_base_039", 2): 181,
        ("veh_sw_nw_base_040", 2): 182,
        ("veh_wn_en_base_025", 1): 183,
    }
    for party in GATE.parties:
        if party["assigned_node_continuous_rank"] != expected_c_ranks[party["visit_key_tuple"]]:
            raise RuntimeError(f"{party['visit_key']} assigned C rank differs.")
    beyond = GATE.beyond_limit
    if beyond.get("c_rank_at_t392") is not None:
        raise RuntimeError("Beyond-limit visit should not have C rank at T=392.")
    if beyond.get("first_confirmation_timestep") != 404:
        raise RuntimeError(
            f"Beyond-limit first C-rank timestep is {beyond.get('first_confirmation_timestep')!r}."
        )
    if beyond.get("assigned_c_rank") != 185:
        raise RuntimeError(f"Beyond-limit assigned C rank is {beyond.get('assigned_c_rank')!r}.")
    if beyond.get("finalization_source") != "baseline":
        raise RuntimeError("Beyond-limit finalization source is not baseline.")
    if beyond.get("final_rank_status") != "baseline_fallback_ranks":
        raise RuntimeError("Beyond-limit final rank status is not baseline_fallback_ranks.")
    if summary_row["payment_balance_satisfied"] is not True:
        raise RuntimeError("Payment balance is not satisfied.")
    if summary_row["buyer_count"] != 1 or summary_row["seller_count"] != 4:
        raise RuntimeError("Summary role counts differ.")
    if summary_row["actual_observed_party_count"] != 5:
        raise RuntimeError("Observed party count is not 5.")
    _compare_trial_csv(summary_row, transaction_row)


def _parse_number(text):
    if text is None or text == "":
        return None
    if "." in text:
        return float(text)
    return int(text)


def _read_csv(path: Path) -> list[dict]:
    if path.is_file() is not True:
        raise RuntimeError(f"Missing trial CSV {path}.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _compare_trial_csv(summary_row, transaction_row) -> None:
    transactions = _read_csv(trial.TRIAL_OUTPUT_DIR / "tvt_mp_transactions.csv")
    visits = _read_csv(trial.TRIAL_OUTPUT_DIR / "tvt_mp_visits.csv")
    buyers_text = _selected_buyers_sorted_text()
    matched = [
        row
        for row in transactions
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
        and row["buyers_sorted"] == buyers_text
    ]
    if len(matched) != 1:
        raise RuntimeError("Trial transaction CSV does not contain one T=392 northwest row.")
    csv_transaction = matched[0]
    GATE.csv_compare_notes.append("transaction_csv: matched one row")
    if int(csv_transaction["buyer_visit_count"]) != summary_row["buyer_count"]:
        raise RuntimeError("CSV buyer_visit_count differs.")
    if int(csv_transaction["seller_visit_count"]) != summary_row["seller_count"]:
        raise RuntimeError("CSV seller_visit_count differs.")
    if int(csv_transaction["nonparticipating_visit_count"]) != summary_row["nonparticipating_count"]:
        raise RuntimeError("CSV nonparticipating_visit_count differs.")
    if int(csv_transaction["trade_scope_visit_count"]) != summary_row["trade_scope_count"]:
        raise RuntimeError("CSV trade_scope_visit_count differs.")
    _require_close(
        _parse_number(csv_transaction["buyer_official_payment_total"]),
        summary_row["total_official_payment"],
        "CSV payment",
    )
    _require_close(
        _parse_number(csv_transaction["seller_official_compensation_total"]),
        summary_row["total_official_compensation"],
        "CSV compensation",
    )
    _require_close(
        _parse_number(csv_transaction["buyer_actual_declared_time_saving_value_total"]),
        summary_row["total_G"],
        "CSV total_G",
    )
    _require_close(
        _parse_number(csv_transaction["seller_actual_required_compensation_total"]),
        summary_row["total_R"],
        "CSV total_R",
    )
    for party in GATE.parties:
        visit_matches = [
            row
            for row in visits
            if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
            and row["node_name"] == TARGET_NODE_NAME
            and row["buyers_sorted"] == buyers_text
            and row["vehicle_name"] == party["vehicle_name"]
            and row["visit_id"] == str(party["visit_id"])
            and row["role"] == party["role"]
        ]
        if len(visit_matches) != 1:
            raise RuntimeError(f"Trial visit CSV match count for {party['visit_key']} is {len(visit_matches)}.")
        visit = visit_matches[0]
        if _parse_number(visit["baseline_passage_timestep"]) != party["baseline_passage_timestep"]:
            raise RuntimeError(f"CSV baseline passage differs for {party['visit_key']}.")
        if _parse_number(visit["candidate_passage_timestep"]) != party["candidate_passage_timestep"]:
            raise RuntimeError(f"CSV candidate passage differs for {party['visit_key']}.")
        if _parse_number(visit["actual_passage_timestep"]) != party["actual_passage_timestep"]:
            raise RuntimeError(f"CSV actual passage differs for {party['visit_key']}.")
        if _parse_number(visit["assigned_rank"]) != party["assigned_node_continuous_rank"]:
            raise RuntimeError(f"CSV assigned rank differs for {party['visit_key']}.")
        if visit["satisfaction_status"] != party["satisfaction_status"]:
            raise RuntimeError(f"CSV satisfaction differs for {party['visit_key']}.")
        if _parse_number(visit["actual_node_passage_rank"]) != party["actual_node_passage_rank"]:
            raise RuntimeError(f"CSV actual passage rank differs for {party['visit_key']}.")
        if party["role"] == "buyer":
            _require_close(
                _parse_number(visit["official_payment"]),
                party["official_payment"],
                f"{party['visit_key']} CSV payment",
            )
        else:
            _require_close(
                _parse_number(visit["official_compensation"]),
                party["official_compensation"],
                f"{party['visit_key']} CSV compensation",
            )
    GATE.csv_compare_notes.append("visit_csv: selected trade scope fields matched")


def _build_summary(summary_row) -> str:
    baseline_rows = sorted(GATE.parties, key=lambda row: row["baseline_local_rank"])
    candidate_rows = sorted(GATE.parties, key=lambda row: row["post_trade_local_rank"])
    lines = [
        "1. 診断条件",
        (
            f"T={TARGET_TIMESTEP} node={TARGET_NODE_NAME} "
            f"max_candidate_visits={trial.MAX_CANDIDATE_VISIT_COUNT} "
            f"sim_until_T={SIMULATION_UNTIL_TIMESTEP} World.T_after={EXPECTED_WORLD_T_AFTER_SIM}"
        ),
        (
            "Actual arrival=T=430 real World hook。selected ex-post=T=900 formal trial CSV照合後。"
        ),
        f"selected_evaluation_index={GATE.selected_evaluation_index}",
        f"P-1 eligible before limit={GATE.p_minus_one_count}",
        "",
        "2. 上限前6 Visits横並び",
    ]
    for row in GATE.six_visits:
        lines.append(
            f"  B{row['baseline_local_rank']} {row['visit_key']} inlink={row['formal_inlink_name']} "
            f"within={row['within_limit']} beyond={row['beyond_limit']} role={row['selected_trade_role']} "
            f"CandRank={row['candidate_local_rank']} "
            f"A B/C/Act {row['baseline_arrival_timestep']}/{row['candidate_arrival_status_or_timestep']}/"
            f"{row['actual_first_arrival_timestep']} "
            f"P B/C/Act {row['baseline_passage_timestep']}/{row['candidate_passage_status_or_timestep']}/"
            f"{row['actual_passage_timestep']} C{row['assigned_node_continuous_rank']} "
            f"confirm_t={row['c_rank_confirmation_timestep']} source={row['c_rank_confirmation_source']}"
        )
    lines.append("")
    lines.append("3. selected 5 Visits Baseline順")
    for row in baseline_rows:
        lines.append(
            f"  {row['visit_key']} {row['role']} {row['formal_inlink_name']} "
            f"baseline_rank={row['baseline_local_rank']} binding_rank={row['binding_rank']}"
        )
    lines.append("")
    lines.append("4. selected 5 Visits Candidate順")
    for row in candidate_rows:
        lines.append(
            f"  {row['visit_key']} {row['role']} {row['formal_inlink_name']} "
            f"candidate_rank={row['post_trade_local_rank']} baseline_rank={row['baseline_local_rank']}"
        )
    lines.append("")
    lines.append("5. selected取引の経済条件")
    for row in candidate_rows:
        lines.append(
            f"  {row['visit_key']} G_b={row['gross_time_value_G_b']} R_s={row['required_compensation_R_s']} "
            f"pay={row['official_payment']} comp={row['official_compensation']} "
            f"gain={row['realized_gain']} {row['satisfaction_status']}"
        )
    lines.extend(
        [
            (
                f"  total_G={summary_row['total_G']} total_R={summary_row['total_R']} "
                f"surplus={summary_row['surplus']} payment={summary_row['total_official_payment']} "
                f"compensation={summary_row['total_official_compensation']}"
            ),
            "",
            "6. 全considered Candidateの経済条件",
        ]
    )
    for row in GATE.considered_candidates:
        lines.append(
            f"  index={row['evaluation_index']} selected={row['selected']} "
            f"buyers={row['buyers_sorted']} G={row['total_G']} R={row['total_R']} "
            f"surplus={row['surplus']} feasible={row['economically_feasible']} "
            f"reason={row['selection_reason']} infeasible={row['infeasibility_reasons']}"
        )
    beyond = GATE.beyond_limit
    lines.extend(
        [
            "",
            "7. 上限外Visitの後続C順位確定",
            (
                f"  {beyond.get('visit_key')} at_T392_C={beyond.get('c_rank_at_t392')} "
                f"first_confirm_t={beyond.get('first_confirmation_timestep')} "
                f"assigned_C={beyond.get('assigned_c_rank')} "
                f"final_rank_status={beyond.get('final_rank_status')} "
                f"source={beyond.get('finalization_source')}"
            ),
            "",
            "8. 到着時刻の元arrival_timeと変換後timestep",
        ]
    )
    for visit_key in sorted(ARRIVAL_TRACKED_VISIT_KEYS):
        audit = GATE.arrival_audit.get(visit_key, {})
        lines.append(
            f"  {_visit_text(visit_key)} raw={audit.get('raw_arrival_time')} "
            f"DELTAT={audit.get('deltat')} ratio={audit.get('arrival_time_over_deltat')} "
            f"timestep={audit.get('formal_arrival_timestep')}"
        )
    lines.append("")
    lines.append("9. 正式N=5 CSV照合結果")
    if len(GATE.csv_compare_notes) == 0:
        lines.append("  (照合未実行)")
    else:
        for note in GATE.csv_compare_notes:
            lines.append(f"  {note}")
    lines.extend(
        [
            "",
            "10. 検証結論",
            "保存済み正式object・hook・N=5 trial CSVの範囲で矛盾は確認されなかった。",
            "これはproduction全体の完全な正当性証明ではない。",
        ]
    )
    return "\n".join(lines) + "\n"


def _prepare_world():
    world = trial.build_world()
    vot_values = trial._true_vot_sequence()
    vot_records = trial.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
    trial.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
    trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    return world


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
    GATE.captured = False
    GATE.parties = []
    GATE.six_visits = []
    GATE.considered_candidates = []
    GATE.transaction = None
    GATE.arrivals = {}
    GATE.arrival_audit = {}
    GATE.tracked_visit_keys = set()
    GATE.c_rank_first_timestep = {}
    GATE.c_rank_finalization_source = {}
    GATE.beyond_limit = {}
    GATE.csv_compare_notes = []
    GATE.selected_evaluation_index = None
    GATE.p_minus_one_count = None
    original_limit = sys.getrecursionlimit()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
            raise RuntimeError("Diagnostic output directory is the trial output directory.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation(until_t=SIMULATION_UNTIL_TIMESTEP * world.DELTAT)
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        _finalize_beyond_limit(world)
        transaction_row = _join_existing_trial_csv()
        summary_row = _finish_transaction(transaction_row)
        _validate_runtime(world, transaction_row, summary_row)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        baseline_rows = sorted(GATE.parties, key=lambda row: row["baseline_local_rank"])
        candidate_rows = sorted(GATE.parties, key=lambda row: row["post_trade_local_rank"])
        _write_csv(OUTPUT_DIR / SIX_VISIT_CSV, SIX_VISIT_COLUMNS, GATE.six_visits)
        _write_csv(OUTPUT_DIR / CANDIDATE_ORDER_CSV, PARTY_COLUMNS, candidate_rows)
        _write_csv(OUTPUT_DIR / TRANSACTION_CSV, TRANSACTION_COLUMNS, [summary_row])
        _write_csv(OUTPUT_DIR / CONSIDERED_CANDIDATES_CSV, CONSIDERED_COLUMNS, GATE.considered_candidates)
        (OUTPUT_DIR / SUMMARY_NAME).write_text(_build_summary(summary_row), encoding="utf-8")
        manifest = {
            "diagnostic_script": SCRIPT_PATH.name,
            "scenario_name": SCENARIO_NAME,
            "target_timestep": TARGET_TIMESTEP,
            "target_node_name": TARGET_NODE_NAME,
            "max_candidate_visit_count": trial.MAX_CANDIDATE_VISIT_COUNT,
            "simulation_until_timestep": SIMULATION_UNTIL_TIMESTEP,
            "candidate_identity": GATE.transaction["candidate_identity"],
            "selected_candidate_evaluation_index": GATE.selected_evaluation_index,
            "selected_trade_scope_count": 5,
            "pre_limit_visit_count": 6,
            "output_files": list(OUTPUT_FILE_NAMES),
            "validation_result": "passed",
            "mismatch_count": 0,
        }
        (OUTPUT_DIR / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        trial.reference.restore_real_world_spillback_observation()
        restore_hooks()
        sys.setrecursionlimit(original_limit)


def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_count(function_node, owner: str, attr: str) -> int:
    count = 0
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != attr:
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == owner:
            count = count + 1
    return count


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    n10_source_path = SCRIPT_DIR / (
        "diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py"
    )
    if n10_source_path.is_file() is not True:
        raise RuntimeError("N=10 diagnostic source file is missing.")
    n10_source = n10_source_path.read_text(encoding="utf-8")
    if "candidate_limit_5_trial" in n10_source:
        raise RuntimeError("N=10 diagnostic source appears modified for N=5 trial.")
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory equals the trial directory.")
    if "candidate_limit_5" not in str(OUTPUT_DIR) or "t392_maximum_party_transaction_review" not in str(
        OUTPUT_DIR
    ):
        raise RuntimeError("Output directory name is wrong.")
    for file_name in OUTPUT_FILE_NAMES:
        if file_name not in source:
            raise RuntimeError(f"Missing output name {file_name}.")
    for text in (
        "northwest_intersection",
        "gross_time_value_G_b",
        "required_compensation_R_s",
        "buyer_economic_records",
        "seller_economic_records",
        "p_minus_one_eligible_visit_count_before_limit",
        "candidate_limit_5_trial",
    ):
        if text not in source:
            raise RuntimeError(f"Missing contract text {text}.")
    if TARGET_TIMESTEP != 392:
        raise RuntimeError("TARGET_TIMESTEP must be 392.")
    if trial.MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("trial.MAX_CANDIDATE_VISIT_COUNT must be 5.")
    if SIMULATION_UNTIL_TIMESTEP != 430 or EXPECTED_WORLD_T_AFTER_SIM != 431:
        raise RuntimeError("Simulation stop contract is wrong.")
    driver = _function_node(tree, "wrapped_driver")
    arrival = _function_node(tree, "wrapped_arrival")
    if driver is None or arrival is None:
        raise RuntimeError("Wrapper is missing.")
    if _call_count(driver, "GATE", "original_driver") != 1:
        raise RuntimeError("wrapped_driver must call original_driver once.")
    if _call_count(arrival, "GATE", "original_arrival") != 1:
        raise RuntimeError("wrapped_arrival must call original_arrival once.")
    install_node = _function_node(tree, "install_hooks")
    restore_node = _function_node(tree, "restore_hooks")
    if install_node is None or restore_node is None:
        raise RuntimeError("Hook install or restore is missing.")
    main_node = _function_node(tree, "main")
    validate_line = None
    mkdir_line = None
    sim_until_found = False
    join_existing_found = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_validate_runtime":
                validate_line = node.lineno
            if node.func.id == "_join_existing_trial_csv":
                join_existing_found = True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "mkdir":
                mkdir_line = node.lineno
            if node.func.attr == "exec_simulation":
                for keyword in node.keywords:
                    if keyword.arg == "until_t":
                        sim_until_found = True
    if validate_line is None or mkdir_line is None or validate_line >= mkdir_line:
        raise RuntimeError("Runtime validation must run before mkdir.")
    if sim_until_found is not True:
        raise RuntimeError("main must call exec_simulation with until_t.")
    if join_existing_found is not True:
        raise RuntimeError("main must call _join_existing_trial_csv.")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "uxsim.order_control_tvt_mp_research_output":
                raise RuntimeError("Diagnostic must not import build_tvt_mp_research_output.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "build_tvt_mp_research_output":
                raise RuntimeError("Diagnostic must not call build_tvt_mp_research_output.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation runs simulation, hooks, or mkdir.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
    forbidden_limit_activation_module = (
        "diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_"
        "candidate_limit_5_t392_limit_activation"
    )

    def _imports_forbidden_limit_activation(module_name: str | None) -> bool:
        if module_name is None:
            return False
        if module_name == forbidden_limit_activation_module:
            return True
        suffix = "." + forbidden_limit_activation_module
        if module_name.endswith(suffix):
            return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _imports_forbidden_limit_activation(alias.name):
                    raise RuntimeError("Diagnostic must not import the N=5 limit activation script.")
        elif isinstance(node, ast.ImportFrom):
            if _imports_forbidden_limit_activation(node.module):
                raise RuntimeError("Diagnostic must not import the N=5 limit activation script.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
