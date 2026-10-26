"""
Compare the T=392 baseline fork with the actual World for one buyer.

The question is why veh_wn_se_base_025:1 has baseline arrival 410 and
actual first arrival 406. This script records formal arrival calls and
same-phase physical snapshots. It does not infer the cause from the vehicle
name or the final arrival times alone.
"""

from __future__ import annotations

import ast
import csv
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial as trial
import uxsim.order_control_baseline_driver as baseline_driver_module
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalizationSource,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_NODE_NAME = "northwest_intersection"
TARGET_DECISION_TIMESTEP = 392
TRACE_END_TIMESTEP = 410
ABSOLUTE_TOLERANCE = 1e-9
TARGET_VEHICLE_NAME = "veh_wn_se_base_025"
TARGET_VISIT_ID = 1
TARGET_INLINK_NAME = "west_north_od_to_northwest_intersection"
EXPECTED_CANDIDATE_IDENTITY = (
    "T=392|northwest_intersection|index=5|"
    "veh_wn_en_base_025:1|veh_nw_sw_base_048:1|veh_wn_se_base_025:1"
)
EXPECTED_BASELINE_ARRIVAL = 410
EXPECTED_ACTUAL_ARRIVAL = 406
EXPECTED_BASELINE_PASSAGE = 420
EXPECTED_CANDIDATE_PASSAGE = 416
EXPECTED_ACTUAL_PASSAGE = 416
EXPECTED_BASELINE_LOCAL_RANK = 6
EXPECTED_POST_TRADE_LOCAL_RANK = 3
EXPECTED_ASSIGNED_RANK = 181
EXPECTED_ACTUAL_PASSAGE_RANK = 184
EXPECTED_EVALUATION_INDEX = 5

PHASE_COMMON_ORIGIN = "common_origin"
PHASE_BEFORE_LINK_UPDATE = "before_link_update"
PHASE_AFTER_LINK_UPDATE = "after_link_update"
PHASE_BEFORE_NODE_TRANSFER = "before_node_transfer"
PHASE_AFTER_NODE_TRANSFER = "after_node_transfer"
PHASE_AFTER_VEHICLE_UPDATE = "after_vehicle_update"
PHASE_AFTER_TIMESTEP = "after_timestep"
PHASE_ORDER = (
    PHASE_COMMON_ORIGIN,
    PHASE_BEFORE_LINK_UPDATE,
    PHASE_AFTER_LINK_UPDATE,
    PHASE_BEFORE_NODE_TRANSFER,
    PHASE_AFTER_NODE_TRANSFER,
    PHASE_AFTER_VEHICLE_UPDATE,
    PHASE_AFTER_TIMESTEP,
)
VEHICLE_COMPARE_FIELDS = (
    "vehicle_id",
    "visit_key",
    "current_link_name",
    "physical_index",
    "leader_vehicle_name",
    "follower_vehicle_name",
    "position_x",
    "x_old",
    "x_next",
    "speed_v",
    "move_remain",
    "lane",
    "in_incoming",
    "incoming_index",
    "state",
    "route_next_link_name",
    "assigned_rank",
    "link_vehicle_count",
    "link_capacity_out_remain",
    "node_flow_capacity_remain",
)
INLINK_COMPARE_FIELDS = (
    "vehicle_count",
    "vehicle_order",
    "position_order",
    "speed_order",
    "physical_head_vehicle_name",
    "capacity_out_remain",
    "cum_arrival_latest",
    "cum_departure_latest",
)

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t392_veh_wn_se_base_025_arrival_divergence"
    )
)
VEHICLE_CSV = "t392_target_vehicle_snapshots.csv"
INLINK_CSV = "t392_target_inlink_snapshots.csv"
INLINK_VEHICLE_CSV = "t392_target_inlink_vehicle_snapshots.csv"
VEHICLE_DIFF_CSV = "t392_first_vehicle_differences.csv"
INLINK_DIFF_CSV = "t392_first_inlink_differences.csv"
FRONT_DIFF_CSV = "t392_front_vehicle_first_differences.csv"
ACTUAL_ARRIVAL_CSV = "t392_actual_arrival_registration_calls.csv"
BASELINE_ARRIVAL_CSV = "t392_baseline_arrival_observation.csv"
DECISION_CSV = "t392_to_t410_decisions_and_rank_changes.csv"
SUMMARY_NAME = "t392_arrival_divergence_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    VEHICLE_CSV,
    INLINK_CSV,
    INLINK_VEHICLE_CSV,
    VEHICLE_DIFF_CSV,
    INLINK_DIFF_CSV,
    FRONT_DIFF_CSV,
    ACTUAL_ARRIVAL_CSV,
    BASELINE_ARRIVAL_CSV,
    DECISION_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)


class _StopAfterActualT410(Exception):
    """Stop the actual World after T=410 after_timestep has been saved."""


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.baseline_world = None
        self.baseline_collector = None
        self.baseline_identity_confirmed = False
        self.original_prepare = None
        self.original_align = None
        self.original_driver = None
        self.original_link_update = None
        self.original_transfer = None
        self.original_vehicle_update = None
        self.original_arrival = None
        self.vehicle_rows = []
        self.inlink_rows = []
        self.inlink_vehicle_rows = []
        self.vehicle_difference_rows = []
        self.inlink_difference_rows = []
        self.front_difference_rows = []
        self.actual_arrival_rows = []
        self.baseline_arrival_rows = []
        self.decision_rows = []
        self.actual_arrivals = {}
        self.baseline_arrivals = {}
        self.phase_seen = set()
        self.link_ends = {}
        self.node_ends = {}
        self.vehicle_last_name = {}
        self.actual_trace_completed = False
        self.analysis = None


GATE = _Gate()


def _visit_text(vehicle_name, visit_id) -> str:
    return f"{vehicle_name}:{visit_id}"


def _plain_visit(vehicle):
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return None
    return (vehicle.name, visit_id)


def _formal_arrival_timestep(arrival_time, deltat) -> int:
    formal_timestep = int(round(arrival_time / deltat))
    if formal_timestep < 0:
        raise RuntimeError(f"Formal arrival timestep is {formal_timestep}.")
    return formal_timestep


def _same_value(left, right) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    if type(left) is bool or type(right) is bool:
        return left is right
    if type(left) in (int, float) and type(right) in (int, float):
        return abs(float(left) - float(right)) <= ABSOLUTE_TOLERANCE
    return left == right


def _sequences_equal(left, right) -> bool:
    if len(left) != len(right):
        return False
    index = 0
    while index < len(left):
        if _same_value(left[index], right[index]) is not True:
            return False
        index = index + 1
    return True


def _join_text(values) -> str:
    return "|".join("" if value is None else str(value) for value in values)


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


def _world_kind(world):
    if GATE.real_world is not None and world is GATE.real_world:
        return "actual"
    if GATE.baseline_world is not None and world is GATE.baseline_world:
        return "baseline"
    return None


def _in_record_window(kind, timestep) -> bool:
    if type(timestep) is not int or type(timestep) is bool:
        return False
    return TARGET_DECISION_TIMESTEP <= timestep <= TRACE_END_TIMESTEP


def _link_by_name(world, link_name):
    found = None
    for link in world.LINKS:
        if getattr(link, "name", None) == link_name:
            if found is not None:
                raise RuntimeError(f"Link {link_name} appears more than once.")
            found = link
    if found is None:
        raise RuntimeError(f"Link {link_name} is missing.")
    return found


def _physical_index(link, vehicle):
    if link is None:
        return None
    index = 0
    for current in link.vehicles:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _incoming_index(node, vehicle):
    incoming = getattr(node, "incoming_vehicles", None)
    if incoming is None:
        return None
    index = 0
    for current in incoming:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _rank_state(world):
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return None
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return None
    return rank_state


def _assigned_rank(world, visit_pair):
    rank_state = _rank_state(world)
    if rank_state is None or visit_pair is None:
        return None
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        if (visit_key[0], visit_key[1]) == visit_pair:
            return rank_state.assigned_rank(visit_key)
    return None


def _rank_map(world) -> dict:
    rank_state = _rank_state(world)
    if rank_state is None:
        return {}
    ranks = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = (visit_key[0], visit_key[1])
        ranks[plain] = rank_state.assigned_rank(visit_key)
    return ranks


def _latest_cum(series):
    if series is None or len(series) == 0:
        return None
    return series[-1]


def _vehicle_snapshot(world, node, vehicle, world_kind, timestep, phase) -> dict:
    visit_pair = None if vehicle is None else _plain_visit(vehicle)
    link = None if vehicle is None else getattr(vehicle, "link", None)
    leader = None if vehicle is None else getattr(vehicle, "leader", None)
    follower = None if vehicle is None else getattr(vehicle, "follower", None)
    route_link = None if vehicle is None else getattr(vehicle, "route_next_link", None)
    current_visit = None if vehicle is None else getattr(vehicle, "order_control_current_visit", None)
    arrival_time = None
    if isinstance(current_visit, dict):
        arrival_time = current_visit.get("arrival_time")
    formal_arrival = None
    if arrival_time is not None:
        formal_arrival = _formal_arrival_timestep(arrival_time, world.DELTAT)
    return {
        "world_kind": world_kind,
        "world_timestep": timestep,
        "phase": phase,
        "vehicle_name": None if vehicle is None else vehicle.name,
        "vehicle_id": None if vehicle is None else getattr(vehicle, "id", None),
        "visit_key": None if visit_pair is None else _visit_text(visit_pair[0], visit_pair[1]),
        "current_link_name": None if link is None else getattr(link, "name", None),
        "physical_index": _physical_index(link, vehicle),
        "leader_vehicle_name": None if leader is None else getattr(leader, "name", None),
        "follower_vehicle_name": None if follower is None else getattr(follower, "name", None),
        "position_x": None if vehicle is None else getattr(vehicle, "x", None),
        "x_old": None if vehicle is None else getattr(vehicle, "x_old", None),
        "x_next": None if vehicle is None else getattr(vehicle, "x_next", None),
        "speed_v": None if vehicle is None else getattr(vehicle, "v", None),
        "move_remain": None if vehicle is None else getattr(vehicle, "move_remain", None),
        "lane": None if vehicle is None else getattr(vehicle, "lane", None),
        "in_incoming": _incoming_index(node, vehicle) is not None,
        "incoming_index": _incoming_index(node, vehicle),
        "state": None if vehicle is None else getattr(vehicle, "state", None),
        "route_next_link_name": None if route_link is None else getattr(route_link, "name", None),
        "assigned_rank": _assigned_rank(world, visit_pair),
        "link_vehicle_count": None if link is None else len(link.vehicles),
        "link_capacity_out_remain": None if link is None else getattr(link, "capacity_out_remain", None),
        "node_flow_capacity_remain": None if node is None else getattr(node, "flow_capacity_remain", None),
        "formal_arrival_timestep": formal_arrival,
    }


def _capture_phase(world, world_kind, timestep, phase) -> None:
    seen_key = (world_kind, timestep, phase)
    if seen_key in GATE.phase_seen:
        return
    GATE.phase_seen.add(seen_key)
    node = world.get_node(TARGET_NODE_NAME)
    vehicle = world.VEHICLES.get(TARGET_VEHICLE_NAME)
    GATE.vehicle_rows.append(_vehicle_snapshot(world, node, vehicle, world_kind, timestep, phase))
    link = _link_by_name(world, TARGET_INLINK_NAME)
    names = []
    positions = []
    speeds = []
    index = 0
    for current in link.vehicles:
        visit_pair = _plain_visit(current)
        leader = getattr(current, "leader", None)
        follower = getattr(current, "follower", None)
        names.append(current.name)
        positions.append(getattr(current, "x", None))
        speeds.append(getattr(current, "v", None))
        GATE.inlink_vehicle_rows.append(
            {
                "world_kind": world_kind,
                "world_timestep": timestep,
                "phase": phase,
                "link_name": TARGET_INLINK_NAME,
                "vehicle_name": current.name,
                "vehicle_id": getattr(current, "id", None),
                "visit_key": None if visit_pair is None else _visit_text(visit_pair[0], visit_pair[1]),
                "physical_index": index,
                "position_x": getattr(current, "x", None),
                "speed_v": getattr(current, "v", None),
                "leader_vehicle_name": None if leader is None else getattr(leader, "name", None),
                "follower_vehicle_name": None if follower is None else getattr(follower, "name", None),
                "state": getattr(current, "state", None),
                "assigned_rank": _assigned_rank(world, visit_pair),
            }
        )
        index = index + 1
    GATE.inlink_rows.append(
        {
            "world_kind": world_kind,
            "world_timestep": timestep,
            "phase": phase,
            "link_name": TARGET_INLINK_NAME,
            "vehicle_count": len(link.vehicles),
            "vehicle_names": tuple(names),
            "position_values": tuple(positions),
            "speed_values": tuple(speeds),
            "vehicle_order": _join_text(names),
            "position_order": _join_text(positions),
            "speed_order": _join_text(speeds),
            "physical_head_vehicle_name": None if len(link.vehicles) == 0 else link.vehicles[0].name,
            "capacity_out_remain": getattr(link, "capacity_out_remain", None),
            "cum_arrival_latest": _latest_cum(getattr(link, "cum_arrival", None)),
            "cum_departure_latest": _latest_cum(getattr(link, "cum_departure", None)),
        }
    )


def _rows_matching(rows, **filters):
    matched = []
    for row in rows:
        same = True
        for key, value in filters.items():
            if row.get(key) != value:
                same = False
        if same is True:
            matched.append(row)
    return matched


def _one_row(rows, label: str):
    if len(rows) != 1:
        raise RuntimeError(f"{label} count is {len(rows)}.")
    return rows[0]


def _require_common_origin() -> None:
    baseline = _one_row(
        _rows_matching(GATE.vehicle_rows, world_kind="baseline", world_timestep=TARGET_DECISION_TIMESTEP, phase=PHASE_COMMON_ORIGIN),
        "baseline common origin vehicle",
    )
    actual = _one_row(
        _rows_matching(GATE.vehicle_rows, world_kind="actual", world_timestep=TARGET_DECISION_TIMESTEP, phase=PHASE_COMMON_ORIGIN),
        "actual common origin vehicle",
    )
    for field_name in VEHICLE_COMPARE_FIELDS:
        if _same_value(baseline[field_name], actual[field_name]) is not True:
            raise RuntimeError(
                f"Common origin {field_name} differs: baseline={baseline[field_name]!r} actual={actual[field_name]!r}."
            )
    if actual["current_link_name"] != TARGET_INLINK_NAME:
        raise RuntimeError("Common origin target vehicle is not on the formal inlink.")
    baseline_link = _one_row(
        _rows_matching(GATE.inlink_rows, world_kind="baseline", world_timestep=TARGET_DECISION_TIMESTEP, phase=PHASE_COMMON_ORIGIN),
        "baseline common origin inlink",
    )
    actual_link = _one_row(
        _rows_matching(GATE.inlink_rows, world_kind="actual", world_timestep=TARGET_DECISION_TIMESTEP, phase=PHASE_COMMON_ORIGIN),
        "actual common origin inlink",
    )
    for field_name in INLINK_COMPARE_FIELDS:
        if field_name in ("vehicle_order", "position_order", "speed_order"):
            continue
        if _same_value(baseline_link[field_name], actual_link[field_name]) is not True:
            raise RuntimeError(f"Common origin inlink {field_name} differs.")
    if _sequences_equal(baseline_link["vehicle_names"], actual_link["vehicle_names"]) is not True:
        raise RuntimeError("Common origin inlink vehicle order differs.")
    if _sequences_equal(baseline_link["position_values"], actual_link["position_values"]) is not True:
        raise RuntimeError("Common origin inlink positions differ.")
    if _sequences_equal(baseline_link["speed_values"], actual_link["speed_values"]) is not True:
        raise RuntimeError("Common origin inlink speeds differ.")


def _saved_columns(atomic):
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
        raise RuntimeError("Saved fork result type is wrong.")
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "final_rank_nodes": final_rank_set.node_final_rank_results,
        "leading_nodes": leading_set.node_confirmation_results,
        "arrived_nodes": arrived_set.node_confirmation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
    }


def _one_node(results, timestep: int):
    matched = None
    count = 0
    for result in results:
        if result.node_name != TARGET_NODE_NAME:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"T={timestep} northwest node result count is {count}.")
    return matched


def _confirmation_source(visit_key, columns, timestep: int) -> str:
    arrived = _one_node(columns["arrived_nodes"], timestep)
    leading = _one_node(columns["leading_nodes"], timestep)
    final_rank = _one_node(columns["final_rank_nodes"], timestep)
    plain = (visit_key[0], visit_key[1])
    hits = []
    for key in arrived.confirmed_arrived_visit_keys:
        if (key[0], key[1]) == plain:
            hits.append("already_arrived_undetermined_confirmation")
    for key in leading.confirmed_leading_nonparticipating_visit_keys:
        if (key[0], key[1]) == plain:
            hits.append("leading_nonparticipating_confirmation")
    record = None
    for item in final_rank.final_rank_visits:
        if (item.visit_key[0], item.visit_key[1]) == plain:
            if record is not None:
                raise RuntimeError(f"Duplicate final rank record for {_visit_text(plain[0], plain[1])}.")
            record = item
    if record is not None:
        if record.finalization_source is OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE:
            hits.append("selected_candidate_final_rank")
        elif record.finalization_source is OrderControlTvtMpFinalizationSource.BASELINE:
            if final_rank.final_rank_status is OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS:
                hits.append("baseline_fallback_final_rank")
            elif final_rank.final_rank_status is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
                hits.append("selected_candidate_outside_trade_scope_baseline_rank")
            else:
                raise RuntimeError("Unsupported baseline final rank status.")
        else:
            raise RuntimeError("Unsupported finalization source.")
    if len(hits) != 1:
        raise RuntimeError(f"Confirmation source count for {_visit_text(plain[0], plain[1])} is {len(hits)}.")
    return hits[0]


def _record_decision(world, timestep: int, before: dict, after: dict, result) -> None:
    selected = False
    evaluation_index = None
    identity = ""
    columns = None
    if isinstance(result, OrderControlTvtMpDriverResult) and result.atomic_apply_set_result is not None:
        columns = _saved_columns(result.atomic_apply_set_result)
        selection = _one_node(columns["selection_nodes"], timestep)
        selected_economic = selection.selected_candidate_economic_result
        selected = selected_economic is not None
        if selected is True:
            economic = _one_node(columns["economic_nodes"], timestep)
            index = 0
            for candidate in economic.candidate_economic_evaluation_results:
                index = index + 1
                if candidate is selected_economic:
                    evaluation_index = index
            local_result = selected_economic.candidate_local_virtual_calculation_result
            buyers = [
                _visit_text(visit_key[0], visit_key[1])
                for visit_key in local_result.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
            ]
            identity = f"T={timestep}|{TARGET_NODE_NAME}|index={evaluation_index}|" + "|".join(buyers)
            if timestep == TARGET_DECISION_TIMESTEP:
                if identity != EXPECTED_CANDIDATE_IDENTITY:
                    raise RuntimeError(f"T=392 candidate identity is {identity!r}.")
                if evaluation_index != EXPECTED_EVALUATION_INDEX:
                    raise RuntimeError("T=392 evaluation index is not 5.")
    new_keys = []
    for visit_key, rank_after in after.items():
        if visit_key in before:
            if after[visit_key] != before[visit_key]:
                raise RuntimeError(f"T={timestep} changed an existing rank for {_visit_text(visit_key[0], visit_key[1])}.")
            continue
        source = ""
        if columns is not None:
            source = _confirmation_source(visit_key, columns, timestep)
        new_keys.append(f"{_visit_text(visit_key[0], visit_key[1])}=C{rank_after}:{source}")
    target = (TARGET_VEHICLE_NAME, TARGET_VISIT_ID)
    GATE.decision_rows.append(
        {
            "tvt_decision_timestep": timestep,
            "node_name": TARGET_NODE_NAME,
            "selected": selected,
            "selected_candidate_evaluation_index": evaluation_index,
            "candidate_identity": identity,
            "newly_confirmed_visits": "|".join(new_keys),
            "target_assigned_rank_before": before.get(target),
            "target_assigned_rank_after": after.get(target),
        }
    )


def wrapped_prepare_baseline_fork(real_W, *, target_node_names, baseline_horizon_steps, apply_copied_tvt_confirmed_ranks):
    prepared = GATE.original_prepare(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=baseline_horizon_steps,
        apply_copied_tvt_confirmed_ranks=apply_copied_tvt_confirmed_ranks,
    )
    if real_W is GATE.real_world and real_W.T == TARGET_DECISION_TIMESTEP and apply_copied_tvt_confirmed_ranks is True:
        if GATE.baseline_world is not None:
            raise RuntimeError("T=392 baseline fork was prepared more than once.")
        if prepared.fork_W is real_W:
            raise RuntimeError("Prepared baseline fork is the real World.")
        if prepared.baseline_timestep_T != TARGET_DECISION_TIMESTEP:
            raise RuntimeError("Prepared baseline timestep is not T=392.")
        if not isinstance(prepared.collector, OrderControlBaselineCollector):
            raise RuntimeError("Prepared collector type is wrong.")
        GATE.baseline_world = prepared.fork_W
        GATE.baseline_collector = prepared.collector
        _capture_phase(real_W, "actual", TARGET_DECISION_TIMESTEP, PHASE_COMMON_ORIGIN)
        _capture_phase(prepared.fork_W, "baseline", TARGET_DECISION_TIMESTEP, PHASE_COMMON_ORIGIN)
        _require_common_origin()
    return prepared


def wrapped_align_baseline(real_W, *, target_node_names, baseline_horizon_steps, rank_states_by_node_name):
    result = GATE.original_align(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=baseline_horizon_steps,
        rank_states_by_node_name=rank_states_by_node_name,
    )
    if real_W is GATE.real_world and real_W.T == TARGET_DECISION_TIMESTEP:
        fork_result = result.fork_result
        if fork_result.collector is not GATE.baseline_collector:
            raise RuntimeError("Aligned collector is not the prepared collector.")
        if TARGET_NODE_NAME not in fork_result.target_node_names:
            raise RuntimeError("T=392 fork does not include northwest_intersection.")
        if GATE.baseline_world is None or GATE.baseline_world is real_W:
            raise RuntimeError("T=392 baseline World is missing.")
        GATE.baseline_identity_confirmed = True
    return result


def wrapped_driver(world):
    kind = _world_kind(world)
    timestep = world.T
    if kind == "actual" and timestep == TRACE_END_TIMESTEP + 1:
        _capture_phase(world, "actual", TRACE_END_TIMESTEP, PHASE_AFTER_TIMESTEP)
        GATE.actual_trace_completed = True
        raise _StopAfterActualT410()
    if kind == "actual" and type(timestep) is int and TARGET_DECISION_TIMESTEP < timestep <= TRACE_END_TIMESTEP:
        _capture_phase(world, "actual", timestep - 1, PHASE_AFTER_TIMESTEP)
    if kind == "baseline" and type(timestep) is int and TARGET_DECISION_TIMESTEP < timestep <= TRACE_END_TIMESTEP + 1:
        _capture_phase(world, "baseline", timestep - 1, PHASE_AFTER_TIMESTEP)
    record = kind == "actual" and type(timestep) is int and TARGET_DECISION_TIMESTEP <= timestep <= TRACE_END_TIMESTEP
    before = _rank_map(world) if record is True else None
    result = GATE.original_driver(world)
    if record is True:
        _record_decision(world, timestep, before, _rank_map(world), result)
    return result


def _ends(storage, world, kind, values):
    key = (kind, id(world), world.T)
    if key not in storage:
        storage[key] = (None, None) if len(values) == 0 else (values[0], values[-1])
    return storage[key]


def wrapped_link_update(link):
    world = link.W
    kind = _world_kind(world)
    record = kind is not None and _in_record_window(kind, world.T)
    first_link = None
    last_link = None
    if record is True or kind == "baseline":
        first_link, last_link = _ends(GATE.link_ends, world, kind, list(world.LINKS))
    if record is True and link is first_link:
        _capture_phase(world, kind, world.T, PHASE_BEFORE_LINK_UPDATE)
    if kind == "baseline" and type(world.T) is int and link is first_link:
        previous = world.T - 1
        if TARGET_DECISION_TIMESTEP <= previous <= TRACE_END_TIMESTEP:
            _capture_phase(world, "baseline", previous, PHASE_AFTER_TIMESTEP)
    result = GATE.original_link_update(link)
    if record is True and link is last_link:
        _capture_phase(world, kind, world.T, PHASE_AFTER_LINK_UPDATE)
    return result


def wrapped_transfer(node):
    world = node.W
    kind = _world_kind(world)
    record = kind is not None and _in_record_window(kind, world.T)
    first_node = None
    last_node = None
    if record is True:
        first_node, last_node = _ends(GATE.node_ends, world, kind, list(world.NODES))
        if node is first_node:
            _capture_phase(world, kind, world.T, PHASE_BEFORE_NODE_TRANSFER)
    result = GATE.original_transfer(node)
    if record is True and node is last_node:
        _capture_phase(world, kind, world.T, PHASE_AFTER_NODE_TRANSFER)
    return result


def wrapped_vehicle_update(vehicle):
    world = vehicle.W
    kind = _world_kind(world)
    record = kind is not None and _in_record_window(kind, world.T)
    last_name = None
    if record is True:
        key = (kind, id(world), world.T)
        if key not in GATE.vehicle_last_name:
            names = list(world.VEHICLES_LIVING.keys())
            GATE.vehicle_last_name[key] = None if len(names) == 0 else names[-1]
        last_name = GATE.vehicle_last_name[key]
    result = GATE.original_vehicle_update(vehicle)
    if record is True and last_name is not None and vehicle.name == last_name:
        _capture_phase(world, kind, world.T, PHASE_AFTER_VEHICLE_UPDATE)
    return result


def _record_arrival(storage, vehicle, node, arrival_time_before, arrival_time_after, rows, world_kind):
    visit_id = None
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if isinstance(current_visit, dict):
        visit_id = current_visit.get("visit_id")
    if vehicle.name != TARGET_VEHICLE_NAME or visit_id != TARGET_VISIT_ID:
        return
    if node is None or node.name != TARGET_NODE_NAME:
        return
    if arrival_time_after is None:
        return
    formal = _formal_arrival_timestep(arrival_time_after, vehicle.W.DELTAT)
    key = (vehicle.name, visit_id)
    first = key not in storage
    if first is True:
        if formal != vehicle.W.T:
            raise RuntimeError(f"{world_kind} first arrival formal {formal} != World.T {vehicle.W.T}.")
        storage[key] = {"timestep": formal, "arrival_time": arrival_time_after}
    else:
        stored_formal = _formal_arrival_timestep(storage[key]["arrival_time"], vehicle.W.DELTAT)
        if stored_formal != formal or storage[key]["arrival_time"] != arrival_time_after:
            raise RuntimeError(f"{world_kind} re-registration changed arrival_time.")
    link = getattr(vehicle, "link", None)
    rows.append(
        {
            "call_index": len(rows) + 1,
            "world_kind": world_kind,
            "world_timestep": vehicle.W.T,
            "arrival_time_before": arrival_time_before,
            "arrival_time_after": arrival_time_after,
            "formal_arrival_timestep": formal,
            "was_first_call": first,
            "was_already_recorded": first is not True,
            "stored_first_arrival": storage[key]["timestep"],
            "current_link_name": None if link is None else getattr(link, "name", None),
            "position_x": getattr(vehicle, "x", None),
            "speed_v": getattr(vehicle, "v", None),
            "physical_index": _physical_index(link, vehicle),
        }
    )


def wrapped_arrival(vehicle, node):
    current_before = getattr(vehicle, "order_control_current_visit", None)
    arrival_before = current_before.get("arrival_time") if isinstance(current_before, dict) else None
    result = GATE.original_arrival(vehicle, node)
    world = vehicle.W
    current_after = getattr(vehicle, "order_control_current_visit", None)
    arrival_after = current_after.get("arrival_time") if isinstance(current_after, dict) else None
    if world is GATE.real_world and getattr(world, "_order_control_baseline_collector", None) is None:
        _record_arrival(GATE.actual_arrivals, vehicle, node, arrival_before, arrival_after, GATE.actual_arrival_rows, "actual")
    elif world is GATE.baseline_world:
        _record_arrival(GATE.baseline_arrivals, vehicle, node, arrival_before, arrival_after, GATE.baseline_arrival_rows, "baseline")
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_prepare = baseline_driver_module._prepare_baseline_fork
    GATE.original_align = driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_link_update = uxsim_module.Link.update
    GATE.original_transfer = uxsim_module.Node.transfer
    GATE.original_vehicle_update = uxsim_module.Vehicle.update
    GATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    baseline_driver_module._prepare_baseline_fork = wrapped_prepare_baseline_fork
    driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits = wrapped_align_baseline
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Link.update = wrapped_link_update
    uxsim_module.Node.transfer = wrapped_transfer
    uxsim_module.Vehicle.update = wrapped_vehicle_update
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    baseline_driver_module._prepare_baseline_fork = GATE.original_prepare
    driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits = GATE.original_align
    driver_module.run_tvt_mp_driver = GATE.original_driver
    uxsim_module.Link.update = GATE.original_link_update
    uxsim_module.Node.transfer = GATE.original_transfer
    uxsim_module.Vehicle.update = GATE.original_vehicle_update
    uxsim_module.Vehicle.record_order_control_node_arrival = GATE.original_arrival
    GATE.original_prepare = None
    GATE.original_align = None
    GATE.original_driver = None
    GATE.original_link_update = None
    GATE.original_transfer = None
    GATE.original_vehicle_update = None
    GATE.original_arrival = None
    GATE.installed = False


def _pair(rows, filters):
    baseline = _rows_matching(rows, world_kind="baseline", **filters)
    actual = _rows_matching(rows, world_kind="actual", **filters)
    if len(baseline) != 1 or len(actual) != 1:
        return None, None
    return baseline[0], actual[0]


def _first_divergence(rows, fields, sequence_fields=()):
    timesteps = sorted({row["world_timestep"] for row in rows if row["world_kind"] == "actual"})
    for timestep in timesteps:
        for phase in PHASE_ORDER:
            baseline, actual = _pair(rows, {"world_timestep": timestep, "phase": phase})
            if baseline is None or actual is None:
                continue
            differing = []
            for field_name in fields:
                if field_name in sequence_fields:
                    left_name = "vehicle_names" if field_name == "vehicle_order" else "position_values" if field_name == "position_order" else "speed_values"
                    differs = _sequences_equal(baseline[left_name], actual[left_name]) is not True
                else:
                    differs = _same_value(baseline[field_name], actual[field_name]) is not True
                if differs is True:
                    differing.append(field_name)
            if len(differing) > 0:
                return timestep, phase, differing, baseline, actual
    return None


def _classify(field_name, phase, front_before_target) -> str:
    if front_before_target is True and field_name in ("position_x", "speed_v", "x_next", "move_remain", "leader_vehicle_name"):
        return "speed／car-following propagation"
    if field_name == "route_next_link_name":
        return "route choice difference"
    if field_name == "assigned_rank":
        return "rank-state difference"
    if field_name in ("vehicle_order", "vehicle_count", "physical_index"):
        return "vehicle order difference"
    if field_name in ("capacity_out_remain", "link_capacity_out_remain", "node_flow_capacity_remain"):
        return "link capacity difference"
    if field_name in ("current_link_name", "in_incoming") and phase == PHASE_AFTER_NODE_TRANSFER:
        return "Node transfer difference"
    if field_name == "current_link_name":
        return "upstream inflow difference"
    if field_name == "formal_arrival_timestep":
        return "arrival registration difference"
    if field_name in ("position_x", "speed_v", "x_next", "move_remain"):
        return "preceding vehicle movement difference" if front_before_target is True else "other observed physical difference"
    return "first physical divergence identified; root cause unresolved"


def _build_analysis() -> None:
    vehicle = _first_divergence(GATE.vehicle_rows, VEHICLE_COMPARE_FIELDS)
    inlink = _first_divergence(GATE.inlink_rows, INLINK_COMPARE_FIELDS, ("vehicle_order", "position_order", "speed_order"))
    if vehicle is None:
        raise RuntimeError("Target vehicle first divergence was not found.")
    timestep, phase, fields, baseline, actual = vehicle
    if phase == PHASE_COMMON_ORIGIN:
        raise RuntimeError("First divergence is common origin.")
    order = 1
    for field_name in fields:
        GATE.vehicle_difference_rows.append(
            {
                "world_timestep": timestep,
                "phase": phase,
                "field_name": field_name,
                "field_order": order,
                "baseline_value": baseline[field_name],
                "actual_value": actual[field_name],
                "current_link_name_baseline": baseline["current_link_name"],
                "current_link_name_actual": actual["current_link_name"],
                "physical_index_baseline": baseline["physical_index"],
                "physical_index_actual": actual["physical_index"],
                "position_baseline": baseline["position_x"],
                "position_actual": actual["position_x"],
                "speed_baseline": baseline["speed_v"],
                "speed_actual": actual["speed_v"],
                "leader_baseline": baseline["leader_vehicle_name"],
                "leader_actual": actual["leader_vehicle_name"],
                "follower_baseline": baseline["follower_vehicle_name"],
                "follower_actual": actual["follower_vehicle_name"],
                "route_baseline": baseline["route_next_link_name"],
                "route_actual": actual["route_next_link_name"],
                "assigned_rank_baseline": baseline["assigned_rank"],
                "assigned_rank_actual": actual["assigned_rank"],
            }
        )
        order = order + 1
    if inlink is not None:
        inlink_timestep, inlink_phase, inlink_fields, inlink_baseline, inlink_actual = inlink
        order = 1
        for field_name in inlink_fields:
            GATE.inlink_difference_rows.append(
                {
                    "world_timestep": inlink_timestep,
                    "phase": inlink_phase,
                    "field_name": field_name,
                    "field_order": order,
                    "baseline_value": inlink_baseline[field_name],
                    "actual_value": inlink_actual[field_name],
                    "vehicle_count_baseline": inlink_baseline["vehicle_count"],
                    "vehicle_count_actual": inlink_actual["vehicle_count"],
                    "vehicle_order_baseline": inlink_baseline["vehicle_order"],
                    "vehicle_order_actual": inlink_actual["vehicle_order"],
                }
            )
            order = order + 1
    front_name = None
    front_report = None
    common_actual = _one_row(
        _rows_matching(GATE.inlink_vehicle_rows, world_kind="actual", world_timestep=TARGET_DECISION_TIMESTEP, phase=PHASE_COMMON_ORIGIN, vehicle_name=TARGET_VEHICLE_NAME),
        "common origin target on inlink",
    )
    front_names = []
    for row in _rows_matching(GATE.inlink_vehicle_rows, world_kind="actual", world_timestep=TARGET_DECISION_TIMESTEP, phase=PHASE_COMMON_ORIGIN):
        if row["physical_index"] < common_actual["physical_index"]:
            front_names.append(row["vehicle_name"])
    earliest = None
    for vehicle_name in front_names:
        report = _first_divergence(
            _rows_matching(GATE.inlink_vehicle_rows, vehicle_name=vehicle_name),
            ("physical_index", "position_x", "speed_v", "leader_vehicle_name", "follower_vehicle_name", "state", "assigned_rank"),
        )
        if report is None:
            continue
        if earliest is None or (report[0], PHASE_ORDER.index(report[1])) < (earliest[0], PHASE_ORDER.index(earliest[1])):
            earliest = report
            front_name = vehicle_name
            front_report = report
    if front_report is not None:
        order = 1
        for field_name in front_report[2]:
            GATE.front_difference_rows.append(
                {
                    "vehicle_name": front_name,
                    "world_timestep": front_report[0],
                    "phase": front_report[1],
                    "field_name": field_name,
                    "field_order": order,
                    "baseline_value": front_report[3][field_name],
                    "actual_value": front_report[4][field_name],
                }
            )
            order = order + 1
    front_before = False
    if front_report is not None:
        front_before = (front_report[0], PHASE_ORDER.index(front_report[1])) <= (timestep, PHASE_ORDER.index(phase))
    GATE.analysis = {
        "vehicle_timestep": timestep,
        "vehicle_phase": phase,
        "vehicle_field": fields[0],
        "vehicle_fields": fields,
        "baseline": baseline,
        "actual": actual,
        "inlink": None if inlink is None else {"timestep": inlink[0], "phase": inlink[1], "field": inlink[2][0]},
        "front_vehicle": front_name,
        "front_before_target": front_before,
        "classification": _classify(fields[0], phase, front_before),
    }


def _validate_runtime() -> None:
    if GATE.baseline_identity_confirmed is not True:
        raise RuntimeError("Baseline fork identity was not confirmed.")
    if GATE.actual_trace_completed is not True:
        raise RuntimeError("Actual trace did not reach T=410.")
    key = (TARGET_VEHICLE_NAME, TARGET_VISIT_ID)
    actual = GATE.actual_arrivals.get(key)
    if actual is None or actual["timestep"] != EXPECTED_ACTUAL_ARRIVAL:
        raise RuntimeError("Actual first arrival is not 406.")
    snapshot = GATE.baseline_collector.get_baseline_visit_snapshot(TARGET_VEHICLE_NAME, TARGET_VISIT_ID)
    if snapshot is None:
        raise RuntimeError("Baseline collector snapshot is missing.")
    if snapshot.get("baseline_arrival_timestep") != EXPECTED_BASELINE_ARRIVAL:
        raise RuntimeError("Collector baseline arrival is not 410.")
    if snapshot.get("inlink_name") != TARGET_INLINK_NAME:
        raise RuntimeError("Collector inlink differs.")
    if snapshot.get("baseline_passage_timestep") != EXPECTED_BASELINE_PASSAGE:
        raise RuntimeError("Collector baseline passage is not 420.")
    baseline_hook = GATE.baseline_arrivals.get(key)
    baseline_state_rows = _rows_matching(
        GATE.vehicle_rows,
        world_kind="baseline",
        world_timestep=EXPECTED_BASELINE_ARRIVAL,
        phase=PHASE_AFTER_TIMESTEP,
    )
    if baseline_hook is not None and baseline_hook["timestep"] != EXPECTED_BASELINE_ARRIVAL:
        raise RuntimeError("Baseline fork arrival hook is not 410.")
    if baseline_hook is None:
        if len(baseline_state_rows) != 1:
            raise RuntimeError("Baseline T=410 after_timestep snapshot is missing.")
        if baseline_state_rows[0]["formal_arrival_timestep"] != EXPECTED_BASELINE_ARRIVAL:
            raise RuntimeError("Baseline T=410 state does not show formal arrival 410.")
    for phase in PHASE_ORDER:
        for kind in ("actual", "baseline"):
            found = _rows_matching(GATE.vehicle_rows, world_kind=kind, world_timestep=TARGET_DECISION_TIMESTEP, phase=phase)
            if phase != PHASE_COMMON_ORIGIN and len(found) != 1 and phase == PHASE_AFTER_TIMESTEP:
                raise RuntimeError(f"Missing {kind} T=392 {phase}.")
    target_rank_rows = [
        row for row in GATE.decision_rows
        if row["target_assigned_rank_after"] not in (None, EXPECTED_ASSIGNED_RANK)
        or (row["tvt_decision_timestep"] != TARGET_DECISION_TIMESTEP and row["target_assigned_rank_before"] not in (None, EXPECTED_ASSIGNED_RANK))
    ]
    if len(target_rank_rows) != 0:
        raise RuntimeError("Target C rank changed after T=392.")
    if GATE.analysis is None or GATE.analysis["vehicle_phase"] == PHASE_COMMON_ORIGIN:
        raise RuntimeError("First divergence is missing or is common origin.")
    visits = []
    path = trial.TRIAL_OUTPUT_DIR / "tvt_mp_visits.csv"
    if path.is_file() is not True:
        raise RuntimeError("Trial visit CSV is missing.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        visits = list(csv.DictReader(handle))
    matched = [
        row for row in visits
        if row["vehicle_name"] == TARGET_VEHICLE_NAME
        and row["visit_id"] == str(TARGET_VISIT_ID)
        and row["tvt_decision_timestep"] == str(TARGET_DECISION_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
    ]
    if len(matched) != 1:
        raise RuntimeError("Trial CSV does not contain one target visit.")
    if int(matched[0]["candidate_passage_timestep"]) != EXPECTED_CANDIDATE_PASSAGE:
        raise RuntimeError("Saved candidate passage is not 416.")
    if int(matched[0]["actual_passage_timestep"]) != EXPECTED_ACTUAL_PASSAGE:
        raise RuntimeError("Saved actual passage is not 416.")
    if int(matched[0]["actual_node_passage_rank"]) != EXPECTED_ACTUAL_PASSAGE_RANK:
        raise RuntimeError("Saved actual passage rank is not 184.")


def _summary() -> str:
    analysis = GATE.analysis
    lines = [
        "対象: T=392 northwest_intersection buyer veh_wn_se_base_025:1。",
        "Actual初回arrival 406は、production arrival_timeの初回値から得た。診断辞書の上書き値ではない。",
        "Baseline arrival 410は、T=392 collector snapshotとBaseline fork内の到着観測に基づく。",
        "common originの対象Vehicleと対象inlinkは一致した。",
        (
            f"対象Vehicleのfirst divergenceは T={analysis['vehicle_timestep']} "
            f"phase={analysis['vehicle_phase']} field={analysis['vehicle_field']}。"
        ),
        (
            f"その時点のBaseline link={analysis['baseline']['current_link_name']} "
            f"position={analysis['baseline']['position_x']} speed={analysis['baseline']['speed_v']}。"
        ),
        (
            f"Actual link={analysis['actual']['current_link_name']} "
            f"position={analysis['actual']['position_x']} speed={analysis['actual']['speed_v']}。"
        ),
        f"直接観測された分類: {analysis['classification']}。",
        "先行Vehicleが原因だった、またはあるdecisionが必要条件だった、という反実仮想は証明していない。",
        "arrival差は Actual 406 - Baseline 410 = -4 timestep。",
        "この範囲だけでは、production欠陥かBaseline予測誤差かを断定しない。",
    ]
    if analysis["front_vehicle"] is not None:
        lines.append(f"最も早い前方Vehicle差: {analysis['front_vehicle']}。対象より前または同時={analysis['front_before_target']}。")
    if analysis["inlink"] is not None:
        lines.append(
            f"対象inlinkのfirst divergenceは T={analysis['inlink']['timestep']} "
            f"{analysis['inlink']['phase']} {analysis['inlink']['field']}。"
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
    original_limit = sys.getrecursionlimit()
    stopped = False
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            try:
                world.exec_simulation()
            except _StopAfterActualT410:
                stopped = True
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        if stopped is not True:
            raise RuntimeError("Actual trace did not stop after T=410.")
        _build_analysis()
        _validate_runtime()
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_csv(OUTPUT_DIR / VEHICLE_CSV, (
            "world_kind", "world_timestep", "phase", "vehicle_name", "vehicle_id", "visit_key",
            "current_link_name", "physical_index", "leader_vehicle_name", "follower_vehicle_name",
            "position_x", "x_old", "x_next", "speed_v", "move_remain", "lane", "in_incoming",
            "incoming_index", "state", "route_next_link_name", "assigned_rank",
            "link_vehicle_count", "link_capacity_out_remain", "node_flow_capacity_remain",
            "formal_arrival_timestep",
        ), GATE.vehicle_rows)
        _write_csv(OUTPUT_DIR / INLINK_CSV, (
            "world_kind", "world_timestep", "phase", "link_name", "vehicle_count", "vehicle_order",
            "position_order", "speed_order", "physical_head_vehicle_name", "capacity_out_remain",
            "cum_arrival_latest", "cum_departure_latest",
        ), GATE.inlink_rows)
        _write_csv(OUTPUT_DIR / INLINK_VEHICLE_CSV, (
            "world_kind", "world_timestep", "phase", "link_name", "vehicle_name", "vehicle_id",
            "visit_key", "physical_index", "position_x", "speed_v", "leader_vehicle_name",
            "follower_vehicle_name", "state", "assigned_rank",
        ), GATE.inlink_vehicle_rows)
        _write_csv(OUTPUT_DIR / VEHICLE_DIFF_CSV, tuple(GATE.vehicle_difference_rows[0].keys()) if GATE.vehicle_difference_rows else ("world_timestep", "phase", "field_name"), GATE.vehicle_difference_rows)
        _write_csv(OUTPUT_DIR / INLINK_DIFF_CSV, tuple(GATE.inlink_difference_rows[0].keys()) if GATE.inlink_difference_rows else ("world_timestep", "phase", "field_name"), GATE.inlink_difference_rows)
        _write_csv(OUTPUT_DIR / FRONT_DIFF_CSV, tuple(GATE.front_difference_rows[0].keys()) if GATE.front_difference_rows else ("vehicle_name", "world_timestep", "phase", "field_name"), GATE.front_difference_rows)
        _write_csv(OUTPUT_DIR / ACTUAL_ARRIVAL_CSV, tuple(GATE.actual_arrival_rows[0].keys()) if GATE.actual_arrival_rows else ("call_index", "formal_arrival_timestep"), GATE.actual_arrival_rows)
        baseline_observation = list(GATE.baseline_arrival_rows)
        snapshot = GATE.baseline_collector.get_baseline_visit_snapshot(TARGET_VEHICLE_NAME, TARGET_VISIT_ID)
        baseline_observation.insert(0, {
            "call_index": 0,
            "world_kind": "collector",
            "world_timestep": TARGET_DECISION_TIMESTEP,
            "formal_arrival_timestep": snapshot.get("baseline_arrival_timestep"),
            "baseline_passage_timestep": snapshot.get("baseline_passage_timestep"),
            "inlink_name": snapshot.get("inlink_name"),
            "was_first_call": True,
        })
        _write_csv(OUTPUT_DIR / BASELINE_ARRIVAL_CSV, (
            "call_index", "world_kind", "world_timestep", "arrival_time_before", "arrival_time_after",
            "formal_arrival_timestep", "was_first_call", "was_already_recorded", "stored_first_arrival",
            "current_link_name", "position_x", "speed_v", "physical_index", "baseline_passage_timestep", "inlink_name",
        ), baseline_observation)
        _write_csv(OUTPUT_DIR / DECISION_CSV, (
            "tvt_decision_timestep", "node_name", "selected", "selected_candidate_evaluation_index",
            "candidate_identity", "newly_confirmed_visits", "target_assigned_rank_before", "target_assigned_rank_after",
        ), GATE.decision_rows)
        (OUTPUT_DIR / SUMMARY_NAME).write_text(_summary(), encoding="utf-8")
        manifest = {
            "diagnostic_script": SCRIPT_PATH.name,
            "target_visit": _visit_text(TARGET_VEHICLE_NAME, TARGET_VISIT_ID),
            "trace_start": TARGET_DECISION_TIMESTEP,
            "trace_end": TRACE_END_TIMESTEP,
            "classification": GATE.analysis["classification"],
            "first_divergence_timestep": GATE.analysis["vehicle_timestep"],
            "first_divergence_phase": GATE.analysis["vehicle_phase"],
            "first_divergence_field": GATE.analysis["vehicle_field"],
            "output_files": list(OUTPUT_FILE_NAMES),
        }
        (OUTPUT_DIR / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


def _call_count(function_node, owner: str, attribute: str) -> int:
    count = 0
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == attribute and isinstance(node.func.value, ast.Name) and node.func.value.id == owner:
                count = count + 1
    return count


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if "t392_veh_wn_se_base_025_arrival_divergence" not in str(OUTPUT_DIR):
        raise RuntimeError("Output directory name is wrong.")
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory equals the trial directory.")
    for name in OUTPUT_FILE_NAMES:
        if name not in source:
            raise RuntimeError(f"Missing output name {name}.")
    for text in (TARGET_VEHICLE_NAME, TARGET_INLINK_NAME, "common_origin", "first divergence"):
        if text not in source and text != "first divergence":
            raise RuntimeError(f"Missing {text}.")
    if "first divergence" not in source and "_first_divergence" not in source:
        raise RuntimeError("First divergence helper is missing.")
    wrappers = (
        ("wrapped_prepare_baseline_fork", "GATE", "original_prepare"),
        ("wrapped_align_baseline", "GATE", "original_align"),
        ("wrapped_driver", "GATE", "original_driver"),
        ("wrapped_link_update", "GATE", "original_link_update"),
        ("wrapped_transfer", "GATE", "original_transfer"),
        ("wrapped_vehicle_update", "GATE", "original_vehicle_update"),
        ("wrapped_arrival", "GATE", "original_arrival"),
    )
    for function_name, owner, attribute in wrappers:
        function_node = _function_node(tree, function_name)
        if function_node is None or _call_count(function_node, owner, attribute) != 1:
            raise RuntimeError(f"{function_name} must call {attribute} once.")
    main_node = _function_node(tree, "main")
    validate_line = None
    mkdir_line = None
    saw_sentinel = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_validate_runtime":
            validate_line = node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "mkdir":
            mkdir_line = node.lineno
        if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name):
            if node.type.id == "_StopAfterActualT410":
                saw_sentinel = True
    if saw_sentinel is not True:
        raise RuntimeError("main does not catch the sentinel.")
    if validate_line is None or mkdir_line is None or validate_line >= mkdir_line:
        raise RuntimeError("Validation must run before mkdir.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation runs simulation, hooks, or mkdir.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name) and node.func.value.id == "trial":
                raise RuntimeError("Diagnostic calls trial.main.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
