"""
Read-only diagnostic: C184/C185 rank assignment between T=393 and T=404 (N=5 trial).

Uses formal driver result objects and rank ledger snapshots only.
Does not rebuild production logic or infer rank sources from vehicle names.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

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
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_final_rank import OrderControlTvtMpFinalizationSource
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState

TARGET_NODE_NAME = "northwest_intersection"
TARGET_TIMESTEP = 392
RANK_GAP_TRACKING_START_TIMESTEP = 393
RANK_GAP_TRACKING_END_TIMESTEP = 404
SIMULATION_UNTIL_TIMESTEP = 404
EXPECTED_WORLD_T_AFTER_SIM = 405
SCENARIO_NAME = trial.SCENARIO_NAME

BEYOND_LIMIT_VISIT_KEY = ("veh_wn_se_base_025", 1)

EXPECTED_T392_C_RANKS = {
    ("veh_nw_sw_base_048", 1): 179,
    ("veh_en_sw_base_026", 2): 180,
    ("veh_sw_nw_base_039", 2): 181,
    ("veh_sw_nw_base_040", 2): 182,
    ("veh_wn_en_base_025", 1): 183,
}

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t404_c184_c185_rank_gap"
    )
)
NEW_C_RANK_EVENTS_CSV = "t393_t404_new_c_rank_events.csv"
TARGET_VISIT_STATE_CSV = "t393_t404_target_visit_state.csv"
T404_FINAL_RANK_ORDER_CSV = "t404_final_rank_order.csv"
REVIEW_NAME = "t404_c184_c185_rank_gap_review.txt"
OUTPUT_FILE_NAMES = (
    NEW_C_RANK_EVENTS_CSV,
    TARGET_VISIT_STATE_CSV,
    T404_FINAL_RANK_ORDER_CSV,
    REVIEW_NAME,
)

NEW_C_RANK_EVENT_COLUMNS = (
    "decision_timestep",
    "node_name",
    "visit_key",
    "assigned_c_rank",
    "pre_undetermined",
    "pre_confirmed",
    "post_confirmed",
    "finalization_source",
    "final_rank_status",
    "final_local_rank",
    "formal_route_next_link_name",
    "route_origin",
    "arrived_undetermined_confirmation",
    "leading_nonparticipating_confirmation",
    "selected_candidate",
    "selected_candidate_outside_trade_scope_baseline",
    "baseline_fallback",
    "official_source",
    "source_objects_used",
)

TARGET_VISIT_STATE_COLUMNS = (
    "timestep",
    "right_of_entry",
    "in_decision_window",
    "leading_nonparticipating_confirmed",
    "in_candidate_visits",
    "considered_candidate_count",
    "appears_as_buyer_in_any_candidate",
    "appears_in_any_candidate_trade_scope",
    "selected_candidate_present",
    "selected_role",
    "selected_evaluation_index",
    "in_final_rank",
    "assigned_c_rank_after_driver",
    "newly_confirmed_this_driver",
    "finalization_source",
    "final_rank_status",
)

T404_FINAL_RANK_COLUMNS = (
    "decision_timestep",
    "final_local_rank",
    "visit_key",
    "assigned_c_rank",
    "finalization_source",
    "route_origin",
    "formal_route_next_link_name",
    "baseline_arrival_timestep",
    "baseline_passage_timestep",
    "formal_inlink_name",
    "arrival_tiebreaker",
    "vehicle_id",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.original_arrival = None
        self.new_c_rank_events: list[dict] = []
        self.target_visit_states: list[dict] = []
        self.t404_final_rank_rows: list[dict] = []
        self.t392_beyond_c_rank = None
        self.c184_holder: dict | None = None
        self.c185_holder: dict | None = None
        self.c184_c185_same_decision = False


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _validate_csv_rows(columns, rows, label: str) -> None:
    column_set = set(columns)
    for index, row in enumerate(rows):
        if type(row) is not dict:
            raise RuntimeError(f"{label} row {index} is not a dict.")
        row_keys = set(row.keys())
        extra = row_keys - column_set
        if len(extra) != 0:
            raise RuntimeError(f"{label} row {index} has extra keys {sorted(extra)!r}.")
        missing = column_set - row_keys
        if len(missing) != 0:
            raise RuntimeError(f"{label} row {index} is missing keys {sorted(missing)!r}.")


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row[column]) for column in columns})


def _rank_state(world) -> OrderControlTvtNodeRankState:
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(f"Northwest rank state is missing at World.T={world.T}.")
    return rank_state


def _rank_membership_snapshot(rank_state: OrderControlTvtNodeRankState) -> dict:
    confirmed_visit_keys: dict[tuple, int] = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        assigned = rank_state.assigned_rank(visit_key)
        if assigned is None:
            raise RuntimeError(f"{_visit_text(plain)} is confirmed but has no assigned rank.")
        confirmed_visit_keys[plain] = assigned
    undetermined_visit_keys = frozenset(
        _plain_visit_key(visit_key) for visit_key in rank_state.undetermined_visit_keys()
    )
    overlap = set(confirmed_visit_keys) & undetermined_visit_keys
    if len(overlap) != 0:
        raise RuntimeError("Confirmed and undetermined visit keys overlap in rank snapshot.")
    return {
        "confirmed_visit_keys": confirmed_visit_keys,
        "undetermined_visit_keys": undetermined_visit_keys,
    }


def _one_node(results, node_name: str, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"World.T decision {node_name}: {label} count is {count}.")
    return matched


def _driver_columns(atomic) -> dict:
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
        "arrived_nodes": arrived_set.node_confirmation_results,
        "leading_nodes": leading_set.node_confirmation_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "final_rank_nodes": final_rank_set.node_final_rank_results,
        "collector": collector,
    }


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


def _final_rank_visit_by_key(final_rank_node, visit_key: tuple):
    for final_visit in final_rank_node.final_rank_visits:
        if _plain_visit_key(final_visit.visit_key) == visit_key:
            return final_visit
    return None


def _binding_partition_for_visit(columns, visit_key: tuple):
    selection_node = _one_node(columns["selection_nodes"], TARGET_NODE_NAME, "selection")
    selected = selection_node.selected_candidate_economic_result
    if selected is None:
        return None
    sequence = selected.candidate_local_virtual_calculation_result.binding_rank_sequence
    matched = []
    for binding_visit in sequence.visits_in_binding_order:
        if _plain_visit_key(binding_visit.visit_key) == visit_key:
            matched.append(binding_visit.binding_partition)
    if len(matched) == 0:
        return None
    if len(matched) != 1:
        raise RuntimeError(
            f"{_visit_text(visit_key)} appears {len(matched)} times in the selected binding sequence."
        )
    return matched[0]


def _classify_official_source(
    visit_key: tuple,
    columns: dict,
    arrived_keys: frozenset,
    leading_keys: frozenset,
    final_visit,
    final_rank_node,
) -> tuple[str, dict]:
    flags = {
        "arrived_undetermined_confirmation": visit_key in arrived_keys,
        "leading_nonparticipating_confirmation": visit_key in leading_keys,
        "selected_candidate": False,
        "selected_candidate_outside_trade_scope_baseline": False,
        "baseline_fallback": False,
    }
    in_arrived = flags["arrived_undetermined_confirmation"]
    in_leading = flags["leading_nonparticipating_confirmation"]
    if in_arrived and in_leading:
        raise RuntimeError(
            f"{_visit_text(visit_key)} matches both arrived and leading confirmation in one driver."
        )
    if (in_arrived or in_leading) and final_visit is not None:
        raise RuntimeError(
            f"{_visit_text(visit_key)} matches early confirmation and final-rank record in one driver."
        )
    if in_arrived:
        return "arrived_undetermined_confirmation", flags
    if in_leading:
        return "leading_nonparticipating_confirmation", flags

    if final_visit is None or final_rank_node is None:
        return "unknown_official_source", flags

    finalization = final_visit.finalization_source
    final_status = final_rank_node.final_rank_status.value
    partition = _binding_partition_for_visit(columns, visit_key)

    if finalization == OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE:
        if partition is None:
            raise RuntimeError(
                f"{_visit_text(visit_key)} has SELECTED_CANDIDATE finalization but no binding partition."
            )
        if partition == OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED:
            raise RuntimeError(
                f"{_visit_text(visit_key)} has SELECTED_CANDIDATE finalization with outside-trade-scope partition."
            )
        if partition != OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE:
            raise RuntimeError(
                f"{_visit_text(visit_key)} has SELECTED_CANDIDATE finalization with partition {partition!r}."
            )
        flags["selected_candidate"] = True
        return "selected_candidate", flags

    if finalization == OrderControlTvtMpFinalizationSource.BASELINE:
        if final_status == "selected_candidate_ranks":
            if partition is None:
                raise RuntimeError(
                    f"{_visit_text(visit_key)} has BASELINE finalization under selected_candidate_ranks "
                    "but no binding partition."
                )
            if partition != OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED:
                raise RuntimeError(
                    f"{_visit_text(visit_key)} has BASELINE finalization under selected_candidate_ranks "
                    f"with partition {partition!r}."
                )
            flags["selected_candidate_outside_trade_scope_baseline"] = True
            return "selected_candidate_outside_trade_scope_baseline", flags
        if final_status == "baseline_fallback_ranks":
            flags["baseline_fallback"] = True
            return "baseline_fallback", flags
        raise RuntimeError(
            f"{_visit_text(visit_key)} has BASELINE finalization with unexpected final_rank_status {final_status!r}."
        )

    return "unknown_official_source", flags


def _record_new_c_rank_events(world, pre_snapshot: dict, post_snapshot: dict, columns: dict | None) -> None:
    pre_confirmed = pre_snapshot["confirmed_visit_keys"]
    post_confirmed = post_snapshot["confirmed_visit_keys"]
    pre_undetermined = pre_snapshot["undetermined_visit_keys"]
    post_undetermined = post_snapshot["undetermined_visit_keys"]

    all_keys = set(pre_confirmed) | set(post_confirmed) | pre_undetermined | post_undetermined
    arrived_keys: frozenset = frozenset()
    leading_keys: frozenset = frozenset()
    final_rank_node = None
    if columns is not None:
        arrived_node = _one_node(columns["arrived_nodes"], TARGET_NODE_NAME, "arrived confirmation")
        arrived_keys = frozenset(
            _plain_visit_key(visit_key) for visit_key in arrived_node.confirmed_arrived_visit_keys
        )
        leading_node = _one_node(columns["leading_nodes"], TARGET_NODE_NAME, "leading confirmation")
        leading_keys = frozenset(
            _plain_visit_key(visit_key)
            for visit_key in leading_node.confirmed_leading_nonparticipating_visit_keys
        )
        final_rank_node = _one_node(columns["final_rank_nodes"], TARGET_NODE_NAME, "final rank")

    for visit_key in sorted(all_keys):
        pre_rank = pre_confirmed.get(visit_key)
        post_rank = post_confirmed.get(visit_key)
        if pre_rank is not None and post_rank is not None and pre_rank != post_rank:
            raise RuntimeError(
                f"{_visit_text(visit_key)} C rank overwritten {pre_rank} -> {post_rank} at T={world.T}."
            )
        if pre_rank is not None or post_rank is None:
            continue
        final_visit = None
        if final_rank_node is not None:
            final_visit = _final_rank_visit_by_key(final_rank_node, visit_key)
        official_source = "unknown_official_source"
        flags = {
            "arrived_undetermined_confirmation": False,
            "leading_nonparticipating_confirmation": False,
            "selected_candidate": False,
            "selected_candidate_outside_trade_scope_baseline": False,
            "baseline_fallback": False,
        }
        source_objects_used = ""
        if columns is not None:
            official_source, flags = _classify_official_source(
                visit_key, columns, arrived_keys, leading_keys, final_visit, final_rank_node
            )
            source_objects_used = "driver_atomic_apply_set_result"
        event = {
            "decision_timestep": world.T,
            "node_name": TARGET_NODE_NAME,
            "visit_key": _visit_text(visit_key),
            "assigned_c_rank": post_rank,
            "pre_undetermined": visit_key in pre_undetermined,
            "pre_confirmed": visit_key in pre_confirmed,
            "post_confirmed": visit_key in post_confirmed,
            "finalization_source": (
                final_visit.finalization_source.value if final_visit is not None else ""
            ),
            "final_rank_status": (
                final_rank_node.final_rank_status.value if final_rank_node is not None else ""
            ),
            "final_local_rank": final_visit.final_local_rank if final_visit is not None else "",
            "formal_route_next_link_name": (
                final_visit.formal_route_next_link_name if final_visit is not None else ""
            ),
            "route_origin": final_visit.route_origin.value if final_visit is not None else "",
            "arrived_undetermined_confirmation": flags["arrived_undetermined_confirmation"],
            "leading_nonparticipating_confirmation": flags["leading_nonparticipating_confirmation"],
            "selected_candidate": flags["selected_candidate"],
            "selected_candidate_outside_trade_scope_baseline": flags[
                "selected_candidate_outside_trade_scope_baseline"
            ],
            "baseline_fallback": flags["baseline_fallback"],
            "official_source": official_source,
            "source_objects_used": source_objects_used,
        }
        GATE.new_c_rank_events.append(event)
        if post_rank == 184:
            if GATE.c184_holder is not None:
                raise RuntimeError("C184 holder was already recorded.")
            GATE.c184_holder = dict(event)
        if post_rank == 185:
            if GATE.c185_holder is not None:
                raise RuntimeError("C185 holder was already recorded.")
            GATE.c185_holder = dict(event)


def _record_t404_final_rank_order(world, columns: dict) -> None:
    if world.T != RANK_GAP_TRACKING_END_TIMESTEP:
        return
    final_rank_node = _one_node(columns["final_rank_nodes"], TARGET_NODE_NAME, "final rank")
    collector = columns["collector"]
    GATE.t404_final_rank_rows = []
    for final_visit in final_rank_node.final_rank_visits:
        visit_key = _plain_visit_key(final_visit.visit_key)
        assigned = _rank_state(world).assigned_rank(visit_key)
        snapshot = collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])
        row = {
            "decision_timestep": world.T,
            "final_local_rank": final_visit.final_local_rank,
            "visit_key": _visit_text(visit_key),
            "assigned_c_rank": assigned,
            "finalization_source": final_visit.finalization_source.value,
            "route_origin": final_visit.route_origin.value,
            "formal_route_next_link_name": final_visit.formal_route_next_link_name,
            "baseline_arrival_timestep": snapshot.get("baseline_arrival_timestep") if snapshot else "",
            "baseline_passage_timestep": snapshot.get("baseline_passage_timestep") if snapshot else "",
            "formal_inlink_name": snapshot.get("inlink_name") if snapshot else "",
            "arrival_tiebreaker": snapshot.get("arrival_tiebreaker") if snapshot else "",
            "vehicle_id": snapshot.get("vehicle_id") if snapshot else "",
        }
        GATE.t404_final_rank_rows.append(row)


def _record_target_visit_state(world, pre_snapshot: dict, post_snapshot: dict, columns: dict | None) -> None:
    visit_key = BEYOND_LIMIT_VISIT_KEY
    right_of_entry = ""
    in_decision_window = False
    leading_confirmed = False
    in_candidate_visits = False
    considered_count = 0
    appears_buyer = False
    appears_scope = False
    selected_present = False
    selected_role = ""
    selected_index = ""
    in_final_rank = False
    finalization_source = ""
    final_rank_status = ""
    newly_confirmed = visit_key in post_snapshot["confirmed_visit_keys"] and visit_key not in pre_snapshot[
        "confirmed_visit_keys"
    ]

    if columns is not None:
        right_node = _one_node(columns["right_of_entry_nodes"], TARGET_NODE_NAME, "right of entry")
        if right_node.right_of_entry_visit_key is not None:
            right_of_entry = _visit_text(_plain_visit_key(right_node.right_of_entry_visit_key))
        leading_node = _one_node(columns["leading_nodes"], TARGET_NODE_NAME, "leading confirmation")
        decision_window = frozenset(
            _plain_visit_key(key) for key in leading_node.decision_window_visit_keys
        )
        in_decision_window = visit_key in decision_window
        leading_confirmed = visit_key in frozenset(
            _plain_visit_key(key) for key in leading_node.confirmed_leading_nonparticipating_visit_keys
        )
        candidate_node = _one_node(columns["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate visits")
        candidate_keys = frozenset(
            _plain_visit_key(cv.visit_key) for cv in candidate_node.candidate_visits
        )
        in_candidate_visits = visit_key in candidate_keys
        economic_node = _one_node(columns["economic_nodes"], TARGET_NODE_NAME, "economic")
        considered_count = len(economic_node.candidate_economic_evaluation_results)
        trade_rank_node = _one_node(columns["trade_rank_nodes"], TARGET_NODE_NAME, "trade rank")
        for index, candidate_economic in enumerate(
            economic_node.candidate_economic_evaluation_results, start=1
        ):
            sequence = candidate_economic.candidate_local_virtual_calculation_result.binding_rank_sequence
            buyers = tuple(
                _plain_visit_key(key) for key in sequence.concrete_buyer_candidate_set.buyers_sorted
            )
            if visit_key in buyers:
                appears_buyer = True
            for trade_result in trade_rank_node.candidate_trade_rank_results:
                trade_buyers = tuple(
                    _plain_visit_key(key) for key in trade_result.buyers_sorted
                )
                if trade_buyers != buyers:
                    continue
                scope = frozenset(_plain_visit_key(key) for key in trade_result.trade_scope)
                if visit_key in scope:
                    appears_scope = True
        selection_node = _one_node(columns["selection_nodes"], TARGET_NODE_NAME, "selection")
        selected = selection_node.selected_candidate_economic_result
        if selected is not None:
            selected_present = True
            for index, candidate_economic in enumerate(
                economic_node.candidate_economic_evaluation_results, start=1
            ):
                if candidate_economic is selected:
                    selected_index = str(index)
                    break
            sequence = selected.candidate_local_virtual_calculation_result.binding_rank_sequence
            for binding_visit in sequence.visits_in_binding_order:
                if _plain_visit_key(binding_visit.visit_key) != visit_key:
                    continue
                selected_role = _role_name(binding_visit.trade_role)
        final_rank_node = _one_node(columns["final_rank_nodes"], TARGET_NODE_NAME, "final rank")
        final_rank_status = final_rank_node.final_rank_status.value
        final_visit = _final_rank_visit_by_key(final_rank_node, visit_key)
        if final_visit is not None:
            in_final_rank = True
            finalization_source = final_visit.finalization_source.value

    assigned_after = post_snapshot["confirmed_visit_keys"].get(visit_key)
    GATE.target_visit_states.append(
        {
            "timestep": world.T,
            "right_of_entry": right_of_entry,
            "in_decision_window": in_decision_window,
            "leading_nonparticipating_confirmed": leading_confirmed,
            "in_candidate_visits": in_candidate_visits,
            "considered_candidate_count": considered_count,
            "appears_as_buyer_in_any_candidate": appears_buyer,
            "appears_in_any_candidate_trade_scope": appears_scope,
            "selected_candidate_present": selected_present,
            "selected_role": selected_role,
            "selected_evaluation_index": selected_index,
            "in_final_rank": in_final_rank,
            "assigned_c_rank_after_driver": assigned_after,
            "newly_confirmed_this_driver": newly_confirmed,
            "finalization_source": finalization_source,
            "final_rank_status": final_rank_status,
        }
    )


def _verify_t392(world) -> None:
    if world.T != TARGET_TIMESTEP:
        return
    rank_state = _rank_state(world)
    for visit_key, expected_rank in EXPECTED_T392_C_RANKS.items():
        assigned = rank_state.assigned_rank(visit_key)
        if assigned != expected_rank:
            raise RuntimeError(
                f"T=392 {_visit_text(visit_key)} C rank is {assigned!r}, expected {expected_rank}."
            )
    beyond = rank_state.assigned_rank(BEYOND_LIMIT_VISIT_KEY)
    GATE.t392_beyond_c_rank = beyond
    if beyond is not None:
        raise RuntimeError("Beyond-limit visit should not have C rank at T=392.")


def wrapped_driver(world):
    pre_snapshot = None
    if world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is None:
            if RANK_GAP_TRACKING_START_TIMESTEP <= world.T <= RANK_GAP_TRACKING_END_TIMESTEP:
                pre_snapshot = _rank_membership_snapshot(_rank_state(world))
    result = GATE.original_driver(world)
    if world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is None:
            if world.T == TARGET_TIMESTEP:
                _verify_t392(world)
            if RANK_GAP_TRACKING_START_TIMESTEP <= world.T <= RANK_GAP_TRACKING_END_TIMESTEP:
                if pre_snapshot is None:
                    raise RuntimeError(f"T={world.T} pre-driver rank snapshot is missing.")
                post_snapshot = _rank_membership_snapshot(_rank_state(world))
                columns = None
                if isinstance(result, OrderControlTvtMpDriverResult):
                    atomic = result.atomic_apply_set_result
                    if atomic is not None:
                        columns = _driver_columns(atomic)
                _record_new_c_rank_events(world, pre_snapshot, post_snapshot, columns)
                _record_target_visit_state(world, pre_snapshot, post_snapshot, columns)
                if columns is not None and world.T == RANK_GAP_TRACKING_END_TIMESTEP:
                    _record_t404_final_rank_order(world, columns)
    return result


def wrapped_arrival(vehicle, node):
    return GATE.original_arrival(vehicle, node)


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


def _validate_c184_c185() -> None:
    expected_timesteps = set(range(RANK_GAP_TRACKING_START_TIMESTEP, RANK_GAP_TRACKING_END_TIMESTEP + 1))
    if len(GATE.target_visit_states) != 12:
        raise RuntimeError(
            f"Target visit state row count is {len(GATE.target_visit_states)}, not 12."
        )
    seen_timesteps: set[int] = set()
    for row in GATE.target_visit_states:
        timestep = row["timestep"]
        if timestep in seen_timesteps:
            raise RuntimeError(f"Duplicate target visit state timestep {timestep}.")
        seen_timesteps.add(timestep)
    if seen_timesteps != expected_timesteps:
        raise RuntimeError("Target visit state timesteps do not match 393..404 exactly.")

    holders_184 = [event for event in GATE.new_c_rank_events if event["assigned_c_rank"] == 184]
    holders_185 = [event for event in GATE.new_c_rank_events if event["assigned_c_rank"] == 185]
    if len(holders_184) != 1:
        raise RuntimeError(f"C184 new-assignment event count is {len(holders_184)}, not 1.")
    if len(holders_185) != 1:
        raise RuntimeError(f"C185 new-assignment event count is {len(holders_185)}, not 1.")
    if holders_184[0]["visit_key"] == holders_185[0]["visit_key"]:
        raise RuntimeError("C184 and C185 share the same VisitKey.")
    if holders_184[0]["assigned_c_rank"] != 184 or holders_185[0]["assigned_c_rank"] != 185:
        raise RuntimeError("C184/C185 assigned rank values are wrong.")

    for event in GATE.new_c_rank_events:
        if event["pre_confirmed"] is True:
            raise RuntimeError(f"{event['visit_key']} new C-rank event has pre_confirmed=True.")
        if event["post_confirmed"] is not True:
            raise RuntimeError(f"{event['visit_key']} new C-rank event has post_confirmed=False.")
        if event["pre_undetermined"] is not True:
            raise RuntimeError(f"{event['visit_key']} new C-rank event was not pre-undetermined.")
        if event["official_source"] == "unknown_official_source":
            if event["assigned_c_rank"] in (184, 185):
                raise RuntimeError(f"C-rank {event['assigned_c_rank']} has unknown official source.")

    if holders_185[0]["visit_key"] != _visit_text(BEYOND_LIMIT_VISIT_KEY):
        raise RuntimeError("C185 holder is not the beyond-limit visit.")
    if holders_185[0]["decision_timestep"] != 404:
        raise RuntimeError(f"C185 first assignment timestep is {holders_185[0]['decision_timestep']}.")
    if holders_185[0]["official_source"] != "baseline_fallback":
        raise RuntimeError(f"C185 official source is {holders_185[0]['official_source']!r}.")
    if holders_184[0]["official_source"] == "unknown_official_source":
        raise RuntimeError("C184 official source is unknown.")
    GATE.c184_c185_same_decision = (
        holders_184[0]["decision_timestep"] == holders_185[0]["decision_timestep"]
    )

    rank_to_visit: dict[int, str] = {}
    for event in GATE.new_c_rank_events:
        rank = event["assigned_c_rank"]
        if rank in rank_to_visit:
            raise RuntimeError(f"C rank {rank} assigned to multiple visits.")
        rank_to_visit[rank] = event["visit_key"]

    if len(GATE.t404_final_rank_rows) == 0:
        raise RuntimeError("T=404 final-rank rows are empty.")
    c185_in_final = [
        row for row in GATE.t404_final_rank_rows if row["assigned_c_rank"] == 185
    ]
    if len(c185_in_final) != 1:
        raise RuntimeError(f"T=404 final-rank rows with C185 count is {len(c185_in_final)}, not 1.")
    if c185_in_final[0]["visit_key"] != _visit_text(BEYOND_LIMIT_VISIT_KEY):
        raise RuntimeError("T=404 final-rank C185 row is not the beyond-limit visit.")


def _build_review() -> str:
    c184 = GATE.c184_holder
    c185 = GATE.c185_holder
    if c184 is None or c185 is None:
        raise RuntimeError("C184 or C185 holder was not recorded.")
    same = GATE.c184_c185_same_decision
    target_rows = GATE.target_visit_states
    was_buyer = any(row["selected_role"] == "buyer" for row in target_rows)
    was_right_of_entry = any(
        row["right_of_entry"] == _visit_text(BEYOND_LIMIT_VISIT_KEY) for row in target_rows
    )
    selected_roles = sorted({row["selected_role"] for row in target_rows if row["selected_role"] != ""})
    was_selected_party = len(selected_roles) > 0
    appears_buyer_any = any(row["appears_as_buyer_in_any_candidate"] for row in target_rows)
    appears_scope_any = any(row["appears_in_any_candidate_trade_scope"] for row in target_rows)
    if was_right_of_entry or was_buyer:
        hypothesis_verdict = "支持"
    elif was_selected_party:
        hypothesis_verdict = "反証"
    elif appears_buyer_any or appears_scope_any:
        hypothesis_verdict = "この診断の正式objectだけでは未確定"
    else:
        hypothesis_verdict = "反証"
    lines = [
        "1. C184取得Visit",
        f"   {c184['visit_key']}",
        "2. C184付与timestep",
        f"   {c184['decision_timestep']}",
        "3. C184正式source",
        f"   {c184['official_source']} (finalization_source={c184['finalization_source']})",
        "4. C185取得Visit",
        f"   {c185['visit_key']}",
        "5. C185付与timestep",
        f"   {c185['decision_timestep']}",
        "6. C185正式source",
        f"   {c185['official_source']} (final_rank_status={c185['final_rank_status']})",
        "7. C184とC185が同じdecisionか",
        f"   {'yes' if same else 'no'} (C184 T={c184['decision_timestep']}, C185 T={c185['decision_timestep']})",
        "8. T=404のfinal rank順",
    ]
    for row in GATE.t404_final_rank_rows:
        lines.append(
            f"   local_rank={row['final_local_rank']} {row['visit_key']} "
            f"C{row['assigned_c_rank']} source={row['finalization_source']} "
            f"route_origin={row['route_origin']}"
        )
    lines.extend(
        [
            "9. veh_wn_se_base_025:1 がT=393〜404でselected Candidate buyerだったか",
            f"   {'yes' if was_buyer else 'no'}",
            "10. right-of-entryだったか",
            f"   {'yes' if was_right_of_entry else 'no'}",
            "11. selected Candidate当事者だったか",
            f"   {'yes' if was_selected_party else 'no'}",
            f"   selected roles observed: {', '.join(selected_roles) if len(selected_roles) > 0 else '(none)'}",
            "12. 当初仮説（後続TVT取引で権利保有車両／buyerとして順位を後続車へ譲った）",
            f"   {hypothesis_verdict}",
            "13. C185となった直接原因",
            (
                f"   T={c185['decision_timestep']} driver result: official_source="
                f"{c185['official_source']}, final_rank_status={c185['final_rank_status']}, "
                f"finalization_source={c185['finalization_source']}"
            ),
            "",
            f"T=392 beyond-limit C rank: {GATE.t392_beyond_c_rank!r}",
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

    GATE.new_c_rank_events = []
    GATE.target_visit_states = []
    GATE.t404_final_rank_rows = []
    GATE.t392_beyond_c_rank = None
    GATE.c184_holder = None
    GATE.c185_holder = None
    GATE.c184_c185_same_decision = False

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
        if world.T != EXPECTED_WORLD_T_AFTER_SIM:
            raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T_AFTER_SIM}.")
        _validate_c184_c185()
        _validate_csv_rows(NEW_C_RANK_EVENT_COLUMNS, GATE.new_c_rank_events, NEW_C_RANK_EVENTS_CSV)
        _validate_csv_rows(TARGET_VISIT_STATE_COLUMNS, GATE.target_visit_states, TARGET_VISIT_STATE_CSV)
        _validate_csv_rows(T404_FINAL_RANK_COLUMNS, GATE.t404_final_rank_rows, T404_FINAL_RANK_ORDER_CSV)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_csv(OUTPUT_DIR / NEW_C_RANK_EVENTS_CSV, NEW_C_RANK_EVENT_COLUMNS, GATE.new_c_rank_events)
        _write_csv(OUTPUT_DIR / TARGET_VISIT_STATE_CSV, TARGET_VISIT_STATE_COLUMNS, GATE.target_visit_states)
        _write_csv(OUTPUT_DIR / T404_FINAL_RANK_ORDER_CSV, T404_FINAL_RANK_COLUMNS, GATE.t404_final_rank_rows)
        (OUTPUT_DIR / REVIEW_NAME).write_text(_build_review(), encoding="utf-8")
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
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    if TARGET_NODE_NAME != "northwest_intersection":
        raise RuntimeError("TARGET_NODE_NAME must be northwest_intersection.")
    if RANK_GAP_TRACKING_START_TIMESTEP != 393 or RANK_GAP_TRACKING_END_TIMESTEP != 404:
        raise RuntimeError("Rank gap tracking timesteps must be 393..404.")
    if SIMULATION_UNTIL_TIMESTEP != 404 or EXPECTED_WORLD_T_AFTER_SIM != 405:
        raise RuntimeError("Simulation end contract must be T=404 / World.T=405.")
    for file_name in OUTPUT_FILE_NAMES:
        if file_name not in SCRIPT_PATH.read_text(encoding="utf-8"):
            raise RuntimeError(f"Missing output file name {file_name}.")
    driver = _function_node(tree, "wrapped_driver")
    if driver is None:
        raise RuntimeError("wrapped_driver is missing.")
    if _call_count(driver, "GATE", "original_driver") != 1:
        raise RuntimeError("wrapped_driver must call original_driver once.")
    if _function_node(tree, "_rank_membership_snapshot") is None:
        raise RuntimeError("Pre/post rank membership snapshot helper is missing.")
    if _function_node(tree, "_validate_c184_c185") is None:
        raise RuntimeError("C184/C185 validation is missing.")
    main_node = _function_node(tree, "main")
    validate_line = None
    mkdir_line = None
    sim_until_found = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_join_existing_trial_csv":
                raise RuntimeError("This diagnostic must not call _join_existing_trial_csv.")
            if node.func.id == "_validate_c184_c185":
                validate_line = node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "mkdir":
                mkdir_line = node.lineno
            if node.func.attr == "exec_simulation":
                for keyword in node.keywords:
                    if keyword.arg == "until_t":
                        sim_until_found = True
    if validate_line is None or mkdir_line is None or validate_line >= mkdir_line:
        raise RuntimeError("C184/C185 validation must run before mkdir.")
    if sim_until_found is not True:
        raise RuntimeError("main must call exec_simulation with until_t.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation must not run simulation, hooks, or mkdir.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
        if isinstance(node, ast.ImportFrom):
            if node.module == "uxsim.order_control_tvt_mp_research_output":
                raise RuntimeError("Diagnostic must not import build_tvt_mp_research_output.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "build_tvt_mp_research_output":
                raise RuntimeError("Diagnostic must not call build_tvt_mp_research_output.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
