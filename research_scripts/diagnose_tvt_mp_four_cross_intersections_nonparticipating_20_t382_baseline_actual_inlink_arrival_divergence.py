"""
Compare the T=382 northwest baseline fork with the actual World.

The four T=382 parties were already on their formal inlinks. Their baseline
and actual arrivals differ. This script records physical snapshots, the
selected northwest candidate at each actual decision from T=382 through
T=407, and the visits that first receive a C rank at those decisions.

It does not change production, the trial, or other diagnostics.
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
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidatePassageRecord,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_NODE_NAME = "northwest_intersection"
TARGET_DECISION_TIMESTEP = 382
ACTUAL_TRACE_END_TIMESTEP = 407
BASELINE_TRACE_END_TIMESTEP = 394
ABSOLUTE_TOLERANCE = 1e-9

INLINK_SOUTHWEST_TO_NORTHWEST = "southwest_intersection_to_northwest_intersection"
INLINK_NORTH_WEST_OD_TO_NORTHWEST = "north_west_od_to_northwest_intersection"
INLINK_WEST_NORTH_OD_TO_NORTHWEST = "west_north_od_to_northwest_intersection"
INLINK_NORTHEAST_TO_NORTHWEST = "northeast_intersection_to_northwest_intersection"
TARGET_INLINK_NAMES = (
    INLINK_SOUTHWEST_TO_NORTHWEST,
    INLINK_NORTH_WEST_OD_TO_NORTHWEST,
    INLINK_WEST_NORTH_OD_TO_NORTHWEST,
    INLINK_NORTHEAST_TO_NORTHWEST,
)

TARGET_PARTIES = (
    {
        "vehicle_name": "veh_sw_nw_base_037",
        "visit_id": 2,
        "role": "seller",
        "inlink_name": INLINK_SOUTHWEST_TO_NORTHWEST,
        "baseline_arrival_timestep": 388,
    },
    {
        "vehicle_name": "veh_nw_sw_base_047",
        "visit_id": 1,
        "role": "seller",
        "inlink_name": INLINK_NORTH_WEST_OD_TO_NORTHWEST,
        "baseline_arrival_timestep": 390,
    },
    {
        "vehicle_name": "veh_wn_se_base_024",
        "visit_id": 1,
        "role": "nonparticipating",
        "inlink_name": INLINK_WEST_NORTH_OD_TO_NORTHWEST,
        "baseline_arrival_timestep": 392,
    },
    {
        "vehicle_name": "veh_en_sw_base_025",
        "visit_id": 2,
        "role": "buyer",
        "inlink_name": INLINK_NORTHEAST_TO_NORTHWEST,
        "baseline_arrival_timestep": 394,
    },
)

# The existing T=382 rank diagnostic names these two T=392 confirmations.
# It does not name a T=390 visit, so this diagnostic does not invent one.
# assigned_rank is the node-continuous C rank from the rank ledger at passage time,
# not the Actual node continuous physical passage order (which can differ).
KNOWN_LATER_CONFIRMATIONS = (
    {
        "vehicle_name": "veh_sw_nw_base_039",
        "visit_id": 2,
        "decision_timestep": 392,
        "assigned_rank": 183,
        "actual_passage_timestep": 402,
    },
    {
        "vehicle_name": "veh_wn_en_base_025",
        "visit_id": 1,
        "decision_timestep": 392,
        "assigned_rank": 179,
        "actual_passage_timestep": 406,
    },
)

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
PHASES_AFTER_TRANSFER = (
    PHASE_AFTER_NODE_TRANSFER,
    PHASE_AFTER_VEHICLE_UPDATE,
    PHASE_AFTER_TIMESTEP,
)

VEHICLE_COMPARE_FIELDS = (
    "current_link_name",
    "physical_index",
    "leader_vehicle_name",
    "follower_vehicle_name",
    "position_x",
    "speed_v",
    "move_remain",
    "x_next",
    "in_incoming",
    "route_next_link_name",
)

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t382_baseline_actual_inlink_arrival_divergence"
    )
)
VEHICLE_SNAPSHOT_CSV = "t382_baseline_actual_target_vehicle_snapshots.csv"
INLINK_VEHICLE_SNAPSHOT_CSV = "t382_baseline_actual_target_inlink_vehicle_snapshots.csv"
INLINK_SNAPSHOT_CSV = "t382_baseline_actual_target_inlink_snapshots.csv"
FIRST_DIFFERENCE_CSV = "t382_baseline_actual_first_differences.csv"
SELECTED_DECISION_CSV = "t382_to_t407_selected_decisions.csv"
SELECTED_PARTY_CSV = "t382_to_t407_selected_candidate_parties.csv"
NEWLY_CONFIRMED_CSV = "t382_to_t407_newly_confirmed_ranks.csv"
FRONT_VEHICLE_CSV = "t382_baseline_actual_front_vehicles.csv"
ARRIVAL_CALL_CSV = "t382_actual_arrival_registration_calls.csv"
SUMMARY_NAME = "t382_baseline_actual_arrival_divergence_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    VEHICLE_SNAPSHOT_CSV,
    INLINK_VEHICLE_SNAPSHOT_CSV,
    INLINK_SNAPSHOT_CSV,
    FIRST_DIFFERENCE_CSV,
    SELECTED_DECISION_CSV,
    SELECTED_PARTY_CSV,
    NEWLY_CONFIRMED_CSV,
    FRONT_VEHICLE_CSV,
    ARRIVAL_CALL_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)


class _StopAfterActualT407(Exception):
    """Stop the actual World after T=407 has finished, before T=408."""


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.baseline_world = None
        self.baseline_collector = None
        self.baseline_prepare_count = 0
        self.baseline_identity_confirmed = False
        self.baseline_target_node_names = None
        self.actual_trace_completed = False
        self.original_prepare = None
        self.original_align = None
        self.original_driver = None
        self.original_link_update = None
        self.original_transfer = None
        self.original_vehicle_update = None
        self.original_move = None
        self.original_arrival = None
        self.vehicle_rows = []
        self.inlink_vehicle_rows = []
        self.inlink_rows = []
        self.decision_rows = []
        self.party_rows = []
        self.newly_confirmed_rows = []
        self.newly_confirmed_by_key = {}
        self.actual_arrivals = {}
        self.actual_arrival_call_rows = []
        self.actual_arrival_call_index = 0
        self.party_arrival_by_vehicle = {}
        self.actual_passes = []
        self.phase_seen = set()
        self.link_ends = {}
        self.node_ends = {}
        self.vehicle_last_name = {}
        self.first_difference_rows = []
        self.front_rows = []
        self.party_reports = []
        self.inlink_reports = []


GATE = _Gate()


def _reset_gate() -> None:
    GATE.__init__()


def _party_by_name(vehicle_name):
    for party in TARGET_PARTIES:
        if party["vehicle_name"] == vehicle_name:
            return party
    return None


def _party_by_visit(vehicle_name, visit_id):
    for party in TARGET_PARTIES:
        if party["vehicle_name"] == vehicle_name and party["visit_id"] == visit_id:
            return party
    return None


def _actual_arrival_key(node_name, vehicle_name, visit_id):
    return (node_name, vehicle_name, visit_id)


def _formal_arrival_timestep_from_time(arrival_time, deltat) -> int:
    return int(round(arrival_time / deltat))


def _arrival_call_rows_for_party(party):
    rows = []
    for row in GATE.actual_arrival_call_rows:
        if row["vehicle_name"] != party["vehicle_name"]:
            continue
        if row["visit_id"] != party["visit_id"]:
            continue
        rows.append(row)
    return rows


def _visit_text(vehicle_name, visit_id) -> str:
    return f"{vehicle_name}:{visit_id}"


def _plain_visit_key(visit_key) -> tuple:
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is {vehicle_name!r}.")
    if type(visit_id) is not int or type(visit_id) is bool:
        raise RuntimeError(f"VisitKey visit id is {visit_id!r}.")
    return (vehicle_name, visit_id)


def _plain_visit(vehicle):
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return None
    vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        return None
    return (vehicle_name, visit_id)


def _link_name(link):
    if link is None:
        return None
    name = getattr(link, "name", None)
    if name is None:
        return None
    return name


def _enum_text(value):
    if value is None:
        return None
    text = getattr(value, "value", None)
    if isinstance(text, str):
        return text
    return str(value)


def _join_text(values) -> str:
    parts = []
    for value in values:
        if value is None:
            parts.append("")
        else:
            parts.append(str(value))
    return "|".join(parts)


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


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        if value is True:
            return "True"
        return "False"
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            cells = {}
            for column in columns:
                cells[column] = _csv_cell(row.get(column))
            writer.writerow(cells)


def _world_kind(world):
    if GATE.real_world is not None and world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is not None:
            raise RuntimeError("Real World is carrying a baseline collector.")
        return "actual"
    if GATE.baseline_world is not None and world is GATE.baseline_world:
        return "baseline"
    return None


def _in_record_window(kind, timestep) -> bool:
    if type(timestep) is not int or type(timestep) is bool:
        return False
    if kind == "actual":
        return TARGET_DECISION_TIMESTEP <= timestep <= ACTUAL_TRACE_END_TIMESTEP
    if kind == "baseline":
        return TARGET_DECISION_TIMESTEP <= timestep <= BASELINE_TRACE_END_TIMESTEP
    return False


def _target_node(world):
    return world.get_node(TARGET_NODE_NAME)


def _link_by_name(world, link_name):
    found = None
    for link in world.LINKS:
        if getattr(link, "name", None) != link_name:
            continue
        if found is not None:
            raise RuntimeError(f"Link {link_name} appears more than once.")
        found = link
    if found is None:
        raise RuntimeError(f"Link {link_name} is missing.")
    return found


def _latest_cum(series):
    if series is None:
        return None
    if len(series) == 0:
        return None
    return series[-1]


def _physical_index(link, vehicle):
    if link is None or vehicle is None:
        return None
    vehicles = getattr(link, "vehicles", None)
    if vehicles is None:
        return None
    index = 0
    for current in vehicles:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _incoming_index(node, vehicle):
    if node is None or vehicle is None:
        return None
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
    if visit_pair is None or world is None:
        return None
    rank_state = _rank_state(world)
    if rank_state is None:
        return None
    return rank_state.assigned_rank(visit_pair)


def _rank_map(world) -> dict:
    rank_state = _rank_state(world)
    if rank_state is None:
        return {}
    ranks = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        ranks[plain] = rank_state.assigned_rank(visit_key)
    return ranks


def _vehicle_snapshot(world, node, vehicle, world_kind, timestep, phase) -> dict:
    visit_pair = None if vehicle is None else _plain_visit(vehicle)
    visit_id = None if visit_pair is None else visit_pair[1]
    visit_key = None if visit_pair is None else _visit_text(visit_pair[0], visit_pair[1])
    link = None if vehicle is None else getattr(vehicle, "link", None)
    leader = None if vehicle is None else getattr(vehicle, "leader", None)
    follower = None if vehicle is None else getattr(vehicle, "follower", None)
    physical_index = _physical_index(link, vehicle)
    incoming_index = _incoming_index(node, vehicle)
    vehicle_count = None
    if link is not None and getattr(link, "vehicles", None) is not None:
        vehicle_count = len(link.vehicles)
    vehicle_name = None if vehicle is None else getattr(vehicle, "name", None)
    vehicle_id = None if vehicle is None else getattr(vehicle, "id", None)
    if type(vehicle_id) is bool:
        vehicle_id = None
    return {
        "world_kind": world_kind,
        "world_timestep": timestep,
        "phase": phase,
        "node_name": TARGET_NODE_NAME,
        "vehicle_name": vehicle_name,
        "vehicle_id": vehicle_id,
        "visit_id": visit_id,
        "visit_key": visit_key,
        "current_link_name": _link_name(link),
        "position_x": None if vehicle is None else getattr(vehicle, "x", None),
        "x_old": None if vehicle is None else getattr(vehicle, "x_old", None),
        "x_next": None if vehicle is None else getattr(vehicle, "x_next", None),
        "speed_v": None if vehicle is None else getattr(vehicle, "v", None),
        "move_remain": None if vehicle is None else getattr(vehicle, "move_remain", None),
        "lane": None if vehicle is None else getattr(vehicle, "lane", None),
        "physical_index": physical_index,
        "is_physical_head": physical_index == 0,
        "leader_vehicle_name": None if leader is None else getattr(leader, "name", None),
        "follower_vehicle_name": None if follower is None else getattr(follower, "name", None),
        "in_incoming": incoming_index is not None,
        "incoming_index": incoming_index,
        "state": None if vehicle is None else getattr(vehicle, "state", None),
        "route_next_link_name": _link_name(
            None if vehicle is None else getattr(vehicle, "route_next_link", None)
        ),
        "assigned_rank": _assigned_rank(world, visit_pair),
        "link_vehicle_count": vehicle_count,
        "link_capacity_out_remain": None if link is None else getattr(link, "capacity_out_remain", None),
        "node_flow_capacity_remain": None if node is None else getattr(node, "flow_capacity_remain", None),
    }


def _append_inlink_snapshots(world, link, world_kind, timestep, phase) -> None:
    vehicles = list(link.vehicles)
    names = []
    positions = []
    speeds = []
    index = 0
    for vehicle in vehicles:
        visit_pair = _plain_visit(vehicle)
        leader = getattr(vehicle, "leader", None)
        follower = getattr(vehicle, "follower", None)
        vehicle_name = getattr(vehicle, "name", None)
        position_x = getattr(vehicle, "x", None)
        speed_v = getattr(vehicle, "v", None)
        names.append(vehicle_name)
        positions.append(position_x)
        speeds.append(speed_v)
        GATE.inlink_vehicle_rows.append(
            {
                "world_kind": world_kind,
                "world_timestep": timestep,
                "phase": phase,
                "link_name": link.name,
                "vehicle_name": vehicle_name,
                "vehicle_id": getattr(vehicle, "id", None),
                "position_x": position_x,
                "speed_v": speed_v,
                "physical_index": index,
                "leader_vehicle_name": None if leader is None else getattr(leader, "name", None),
                "follower_vehicle_name": None if follower is None else getattr(follower, "name", None),
                "state": getattr(vehicle, "state", None),
                "visit_key": None if visit_pair is None else _visit_text(visit_pair[0], visit_pair[1]),
                "visit_pair": visit_pair,
                "assigned_rank": _assigned_rank(world, visit_pair),
            }
        )
        index = index + 1
    head_name = None
    if len(vehicles) > 0:
        head_name = getattr(vehicles[0], "name", None)
    GATE.inlink_rows.append(
        {
            "world_kind": world_kind,
            "world_timestep": timestep,
            "phase": phase,
            "link_name": link.name,
            "vehicle_count": len(vehicles),
            "vehicle_names": tuple(names),
            "position_values": tuple(positions),
            "speed_values": tuple(speeds),
            "vehicle_order": _join_text(names),
            "position_order": _join_text(positions),
            "speed_order": _join_text(speeds),
            "physical_head_vehicle_name": head_name,
            "capacity_out_remain": getattr(link, "capacity_out_remain", None),
            "cum_arrival_latest": _latest_cum(getattr(link, "cum_arrival", None)),
            "cum_departure_latest": _latest_cum(getattr(link, "cum_departure", None)),
        }
    )


def _capture_phase(world, world_kind, timestep, phase) -> None:
    seen_key = (world_kind, timestep, phase)
    if seen_key in GATE.phase_seen:
        return
    GATE.phase_seen.add(seen_key)
    node = _target_node(world)
    for party in TARGET_PARTIES:
        vehicle = world.VEHICLES.get(party["vehicle_name"])
        GATE.vehicle_rows.append(
            _vehicle_snapshot(world, node, vehicle, world_kind, timestep, phase)
        )
    for link_name in TARGET_INLINK_NAMES:
        link = _link_by_name(world, link_name)
        _append_inlink_snapshots(world, link, world_kind, timestep, phase)


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


def _require_common_origin_match() -> None:
    for party in TARGET_PARTIES:
        vehicle_name = party["vehicle_name"]
        baseline_rows = _rows_matching(
            GATE.vehicle_rows,
            world_kind="baseline",
            world_timestep=TARGET_DECISION_TIMESTEP,
            phase=PHASE_COMMON_ORIGIN,
            vehicle_name=vehicle_name,
        )
        actual_rows = _rows_matching(
            GATE.vehicle_rows,
            world_kind="actual",
            world_timestep=TARGET_DECISION_TIMESTEP,
            phase=PHASE_COMMON_ORIGIN,
            vehicle_name=vehicle_name,
        )
        baseline = _one_row(baseline_rows, f"common origin baseline {vehicle_name}")
        actual = _one_row(actual_rows, f"common origin actual {vehicle_name}")
        expected_visit = _visit_text(vehicle_name, party["visit_id"])
        compared = (
            "vehicle_id",
            "visit_key",
            "current_link_name",
            "position_x",
            "speed_v",
            "physical_index",
            "leader_vehicle_name",
            "follower_vehicle_name",
            "route_next_link_name",
        )
        for field_name in compared:
            if _same_value(baseline[field_name], actual[field_name]) is not True:
                raise RuntimeError(
                    f"Common origin {vehicle_name} {field_name} differs: "
                    f"baseline={baseline[field_name]!r} actual={actual[field_name]!r}."
                )
        if type(baseline["vehicle_id"]) is not int or type(baseline["vehicle_id"]) is bool:
            raise RuntimeError(
                f"Common origin {vehicle_name} vehicle id is {baseline['vehicle_id']!r}."
            )
        if baseline["visit_key"] != expected_visit:
            raise RuntimeError(
                f"Common origin {vehicle_name} live VisitKey is {baseline['visit_key']!r}, "
                f"not {expected_visit}."
            )
        if baseline["current_link_name"] != party["inlink_name"]:
            raise RuntimeError(
                f"Common origin {vehicle_name} is on {baseline['current_link_name']!r}, "
                f"not formal inlink {party['inlink_name']}."
            )
    for link_name in TARGET_INLINK_NAMES:
        baseline_links = _rows_matching(
            GATE.inlink_rows,
            world_kind="baseline",
            world_timestep=TARGET_DECISION_TIMESTEP,
            phase=PHASE_COMMON_ORIGIN,
            link_name=link_name,
        )
        actual_links = _rows_matching(
            GATE.inlink_rows,
            world_kind="actual",
            world_timestep=TARGET_DECISION_TIMESTEP,
            phase=PHASE_COMMON_ORIGIN,
            link_name=link_name,
        )
        baseline_link = _one_row(baseline_links, f"common origin baseline {link_name}")
        actual_link = _one_row(actual_links, f"common origin actual {link_name}")
        if baseline_link["vehicle_count"] != actual_link["vehicle_count"]:
            raise RuntimeError(f"Common origin {link_name} vehicle count differs.")
        if _sequences_equal(baseline_link["vehicle_names"], actual_link["vehicle_names"]) is not True:
            raise RuntimeError(f"Common origin {link_name} vehicle order differs.")
        if _sequences_equal(baseline_link["position_values"], actual_link["position_values"]) is not True:
            raise RuntimeError(f"Common origin {link_name} position order differs.")
        if _sequences_equal(baseline_link["speed_values"], actual_link["speed_values"]) is not True:
            raise RuntimeError(f"Common origin {link_name} speed order differs.")


def _saved_columns(atomic, timestep: int) -> dict:
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
    return {
        "timestep": timestep,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
    }


def _one_node(results, label: str, timestep: int):
    matched = None
    count = 0
    for result in results:
        if result.node_name != TARGET_NODE_NAME:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: {label} count is {count}."
        )
    return matched


def _find_one_based_evaluation_index(candidate_economic_results, selected_economic, timestep: int):
    evaluation_index = None
    index = 0
    for candidate_economic in candidate_economic_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if evaluation_index is not None:
                raise RuntimeError(
                    f"T={timestep} {TARGET_NODE_NAME}: selected economic result appears more than once."
                )
            evaluation_index = index
    if evaluation_index is None:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: selected economic result is missing from the node list."
        )
    if type(evaluation_index) is not int or type(evaluation_index) is bool:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: evaluation index must be a Python int, not bool."
        )
    if evaluation_index < 1:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: evaluation index must be >= 1, got {evaluation_index}."
        )
    return evaluation_index


def _buyers_visit_identity_suffix(buyers) -> str:
    parts = []
    for buyer in buyers:
        parts.append(_visit_text(buyer[0], buyer[1]))
    return "|".join(parts)


def _find_unique_trade_result_for_buyers(candidate_trade_rank_results, buyers, timestep: int):
    found = None
    for candidate_trade in candidate_trade_rank_results:
        candidate_buyers = tuple(
            _plain_visit_key(visit_key) for visit_key in candidate_trade.buyers_sorted
        )
        if candidate_buyers != buyers:
            continue
        if found is not None:
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: more than one general "
                "trade-rank result matches the selected buyers."
            )
        found = candidate_trade
    if found is None:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: no general trade-rank result "
            "matches the selected buyers."
        )
    if not isinstance(found, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: matched general trade-rank result "
            f"is {type(found).__name__}."
        )
    return found


def _same_optional(left, right, label: str):
    if left is None:
        return right
    if right is None:
        return left
    if left != right:
        raise RuntimeError(f"{label} has two different saved values: {left!r} and {right!r}.")
    return left


def _append_all_selected_parties(
    timestep: int,
    identity: str,
    evaluation_index: int,
    local_result,
    trade_result,
    candidate_visits,
    right_of_entry,
) -> set:
    if not isinstance(local_result, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: local result is {type(local_result).__name__}."
        )
    if local_result is GATE.real_world or local_result is GATE.baseline_world:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: local result is a traced World object."
        )
    binding_sequence = local_result.binding_rank_sequence
    if not isinstance(binding_sequence, OrderControlTvtMpLocalBindingRankSequence):
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: binding sequence is {type(binding_sequence).__name__}."
        )
    buyers = []
    for visit_key in trade_result.buyers_sorted:
        buyers.append(_plain_visit_key(visit_key))
    sellers = []
    for visit_key in trade_result.sellers_sorted:
        sellers.append(_plain_visit_key(visit_key))
    nonparticipating = []
    for visit_key in trade_result.nonparticipating_visits_sorted:
        nonparticipating.append(_plain_visit_key(visit_key))
    trade_scope = []
    for visit_key in trade_result.trade_scope:
        trade_scope.append(_plain_visit_key(visit_key))
    trade_order = []
    for visit_key in trade_result.trade_order:
        trade_order.append(_plain_visit_key(visit_key))
    trade_order_set = set(trade_order)
    candidate_by_plain = {}
    baseline_order = []
    baseline_rank = {}
    rank_value = 1
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: candidate visit is {type(candidate_visit).__name__}."
            )
        plain = _plain_visit_key(candidate_visit.visit_key)
        if plain in candidate_by_plain:
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: duplicate candidate visit {_visit_text(plain[0], plain[1])}."
            )
        candidate_by_plain[plain] = candidate_visit
        baseline_order.append(plain)
        baseline_rank[plain] = rank_value
        rank_value = rank_value + 1
    passage_by_plain = {}
    for passage_record in local_result.required_passage_records:
        if not isinstance(passage_record, OrderControlTvtMpCandidatePassageRecord):
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: passage record is {type(passage_record).__name__}."
            )
        plain = _plain_visit_key(passage_record.visit_key)
        if plain in passage_by_plain:
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: duplicate passage record {_visit_text(plain[0], plain[1])}."
            )
        passage_by_plain[plain] = passage_record
    binding_by_plain = {}
    binding_order = []
    for binding_visit in binding_sequence.visits_in_binding_order:
        if not isinstance(binding_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: binding visit is {type(binding_visit).__name__}."
            )
        plain = _plain_visit_key(binding_visit.visit_key)
        if plain in binding_by_plain:
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: duplicate binding visit {_visit_text(plain[0], plain[1])}."
            )
        binding_by_plain[plain] = binding_visit
        binding_order.append(plain)
    ordered_plains = list(baseline_order)
    for plain in binding_order:
        if plain not in candidate_by_plain:
            ordered_plains.append(plain)
    saved_keys = set()
    for plain in ordered_plains:
        candidate_visit = candidate_by_plain.get(plain)
        binding_visit = binding_by_plain.get(plain)
        passage_record = passage_by_plain.get(plain)
        trade_role = None
        inlink_name = None
        baseline_arrival = None
        baseline_passage = None
        predicted_route = None
        binding_partition = None
        binding_rank = None
        if candidate_visit is not None:
            inlink_name = candidate_visit.inlink_name
            baseline_arrival = candidate_visit.baseline_arrival_timestep
            baseline_passage = candidate_visit.baseline_passage_timestep
            predicted_route = candidate_visit.route_next_link_name
        if binding_visit is not None:
            trade_role = _enum_text(binding_visit.trade_role)
            binding_partition = _enum_text(binding_visit.binding_partition)
            binding_rank = binding_visit.binding_rank
            inlink_name = _same_optional(
                inlink_name,
                binding_visit.inlink_name,
                f"T={timestep} {_visit_text(plain[0], plain[1])} inlink",
            )
            baseline_arrival = _same_optional(
                baseline_arrival,
                binding_visit.baseline_arrival_timestep,
                f"T={timestep} {_visit_text(plain[0], plain[1])} baseline arrival",
            )
            predicted_route = _same_optional(
                predicted_route,
                binding_visit.route_next_link_name,
                f"T={timestep} {_visit_text(plain[0], plain[1])} route",
            )
        if passage_record is not None:
            if trade_role is None:
                trade_role = _enum_text(passage_record.trade_role)
            if binding_partition is None:
                binding_partition = _enum_text(passage_record.binding_partition)
            inlink_name = _same_optional(
                inlink_name,
                passage_record.inlink_name,
                f"T={timestep} {_visit_text(plain[0], plain[1])} passage inlink",
            )
            baseline_passage = _same_optional(
                baseline_passage,
                passage_record.baseline_passage_timestep,
                f"T={timestep} {_visit_text(plain[0], plain[1])} baseline passage",
            )
            predicted_route = _same_optional(
                predicted_route,
                passage_record.route_next_link_name,
                f"T={timestep} {_visit_text(plain[0], plain[1])} predicted route",
            )
        candidate_local_rank = None
        if plain in trade_order_set:
            source_key = plain
            if candidate_visit is not None:
                source_key = candidate_visit.visit_key
            elif binding_visit is not None:
                source_key = binding_visit.visit_key
            candidate_local_rank = trade_result.assigned_rank(source_key)
        candidate_order_position = None
        if plain in trade_order_set:
            candidate_order_position = trade_order.index(plain) + 1
        GATE.party_rows.append(
            {
                "tvt_decision_timestep": timestep,
                "node_name": TARGET_NODE_NAME,
                "selected": True,
                "selected_candidate_evaluation_index": evaluation_index,
                "candidate_identity": identity,
                "vehicle_name": plain[0],
                "visit_id": plain[1],
                "visit_key": _visit_text(plain[0], plain[1]),
                "trade_role": trade_role,
                "inlink_name": inlink_name,
                "in_candidate_visits": plain in candidate_by_plain,
                "in_trade_scope": plain in trade_scope,
                "in_binding_sequence": plain in binding_by_plain,
                "binding_partition": binding_partition,
                "baseline_order_position": baseline_rank.get(plain),
                "candidate_order_position": candidate_order_position,
                "baseline_local_rank": baseline_rank.get(plain),
                "candidate_local_rank": candidate_local_rank,
                "binding_rank": binding_rank,
                "baseline_arrival_timestep": baseline_arrival,
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": None
                if passage_record is None
                else passage_record.candidate_passage_timestep,
                "predicted_route_next_link_name": predicted_route,
                "buyers_sorted": _join_text(
                    [_visit_text(item[0], item[1]) for item in buyers]
                ),
                "sellers_sorted": _join_text(
                    [_visit_text(item[0], item[1]) for item in sellers]
                ),
                "nonparticipating_visits_sorted": _join_text(
                    [_visit_text(item[0], item[1]) for item in nonparticipating]
                ),
                "trade_scope": _join_text(
                    [_visit_text(item[0], item[1]) for item in trade_scope]
                ),
                "baseline_order": _join_text(
                    [_visit_text(item[0], item[1]) for item in baseline_order]
                ),
                "candidate_order": _join_text(
                    [_visit_text(item[0], item[1]) for item in trade_order]
                ),
                "right_of_entry_visit_key": None
                if right_of_entry is None
                else _visit_text(right_of_entry[0], right_of_entry[1]),
                "k_last_buyer": binding_sequence.k_last_buyer,
                "k_decision_window": binding_sequence.k_decision_window,
                "k_fixed": binding_sequence.k_fixed,
                "visits_in_binding_order": _join_text(
                    [_visit_text(item[0], item[1]) for item in binding_order]
                ),
                "local_calculation_resolved": local_result.resolved,
                "local_calculation_stop_reason": _enum_text(local_result.stop_reason),
                "newly_confirmed_by_this_decision": False,
                "newly_assigned_node_continuous_rank": None,
            }
        )
        saved_keys.add(plain)
    return saved_keys


def _read_selected_candidate(columns, economic, timestep: int) -> dict:
    local_result = economic.candidate_local_virtual_calculation_result
    if not isinstance(local_result, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: selected local result is {type(local_result).__name__}."
        )
    if local_result.baseline_timestep_T != timestep:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: local result baseline timestep is "
            f"{local_result.baseline_timestep_T}."
        )
    if local_result.node_name != TARGET_NODE_NAME:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: local result node is {local_result.node_name!r}."
        )
    local_node = _one_node(columns["local_nodes"], "local virtual calculation", timestep)
    matched_local = False
    for saved_local in local_node.candidate_local_virtual_calculation_results:
        if saved_local is local_result:
            if matched_local is True:
                raise RuntimeError(
                    f"T={timestep} {TARGET_NODE_NAME}: selected local result object appears more than once."
                )
            matched_local = True
    if matched_local is not True:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: selected economic result's local result "
            "is not the saved local virtual calculation result object."
        )
    buyers = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    economic_node = _one_node(columns["economic_nodes"], "economic", timestep)
    evaluation_index = _find_one_based_evaluation_index(
        economic_node.candidate_economic_evaluation_results,
        economic,
        timestep,
    )
    trade_node = _one_node(columns["trade_rank_nodes"], "trade rank", timestep)
    if not isinstance(trade_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: trade rank node is {type(trade_node).__name__}."
        )
    trade_result = _find_unique_trade_result_for_buyers(
        trade_node.candidate_trade_rank_results,
        buyers,
        timestep,
    )
    visit_node = _one_node(columns["candidate_visit_nodes"], "candidate visits", timestep)
    right_of_entry = None
    if visit_node.right_of_entry_visit_key is not None:
        right_of_entry = _plain_visit_key(visit_node.right_of_entry_visit_key)
    identity = (
        f"T={timestep}|{TARGET_NODE_NAME}|index={evaluation_index}|"
        f"{_buyers_visit_identity_suffix(buyers)}"
    )
    saved_keys = _append_all_selected_parties(
        timestep,
        identity,
        evaluation_index,
        local_result,
        trade_result,
        tuple(visit_node.candidate_visits),
        right_of_entry,
    )
    if len(saved_keys) == 0:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: selected candidate has no saved visits."
        )
    return {
        "selected": True,
        "selected_candidate_evaluation_index": evaluation_index,
        "candidate_identity": identity,
        "saved_visit_keys": saved_keys,
        "local_calculation_resolved": local_result.resolved,
        "local_calculation_stop_reason": _enum_text(local_result.stop_reason),
    }


def _blank_selected_fields() -> dict:
    return {
        "selected": False,
        "selected_candidate_evaluation_index": None,
        "candidate_identity": None,
        "saved_visit_keys": set(),
        "local_calculation_resolved": None,
        "local_calculation_stop_reason": None,
    }


def _record_newly_confirmed(timestep: int, before: dict, after: dict, selected_detail: dict) -> list:
    new_rows = []
    for visit_key, rank_value in after.items():
        if visit_key in before:
            if before[visit_key] != rank_value:
                raise RuntimeError(
                    f"T={timestep} {TARGET_NODE_NAME}: confirmed visit "
                    f"{_visit_text(visit_key[0], visit_key[1])} changed C rank from "
                    f"{before[visit_key]!r} to {rank_value!r}. This diagnostic does not "
                    "record that change as a new confirmation."
                )
            continue
        if type(rank_value) is not int or type(rank_value) is bool:
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: new rank for "
                f"{_visit_text(visit_key[0], visit_key[1])} is {rank_value!r}."
            )
        if visit_key in GATE.newly_confirmed_by_key:
            previous = GATE.newly_confirmed_by_key[visit_key]
            raise RuntimeError(
                f"{_visit_text(visit_key[0], visit_key[1])} is newly confirmed at "
                f"T={previous['tvt_decision_timestep']} and T={timestep}."
            )
        row = {
            "tvt_decision_timestep": timestep,
            "node_name": TARGET_NODE_NAME,
            "vehicle_name": visit_key[0],
            "visit_id": visit_key[1],
            "visit_key": _visit_text(visit_key[0], visit_key[1]),
            "assigned_rank": rank_value,
            "decision_selected_candidate_identity": selected_detail["candidate_identity"],
            "selected_candidate_evaluation_index": selected_detail[
                "selected_candidate_evaluation_index"
            ],
            "in_selected_candidate_parties": visit_key in selected_detail["saved_visit_keys"],
        }
        GATE.newly_confirmed_rows.append(row)
        GATE.newly_confirmed_by_key[visit_key] = row
        new_rows.append(row)
    return new_rows


def _mark_newly_confirmed_party_rows(timestep: int) -> None:
    confirmed = {}
    for row in GATE.newly_confirmed_rows:
        if row["tvt_decision_timestep"] != timestep:
            continue
        confirmed[(row["vehicle_name"], row["visit_id"])] = row["assigned_rank"]
    for row in GATE.party_rows:
        if row["tvt_decision_timestep"] != timestep:
            continue
        key = (row["vehicle_name"], row["visit_id"])
        if key not in confirmed:
            row["newly_confirmed_by_this_decision"] = False
            row["newly_assigned_node_continuous_rank"] = None
            continue
        row["newly_confirmed_by_this_decision"] = True
        row["newly_assigned_node_continuous_rank"] = confirmed[key]


def _record_decision(world, timestep: int, before: dict, after: dict, result) -> None:
    if world is not GATE.real_world:
        raise RuntimeError("Selected decision recording saw a World that is not the real World.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={timestep} driver result is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(f"T={timestep} {TARGET_NODE_NAME}: driver returned no atomic apply result.")
    columns = _saved_columns(atomic, timestep)
    selection_node = _one_node(columns["selection_nodes"], "selection", timestep)
    economic = selection_node.selected_candidate_economic_result
    if economic is None:
        selected_detail = _blank_selected_fields()
    else:
        selected_detail = _read_selected_candidate(columns, economic, timestep)
    new_rows = _record_newly_confirmed(timestep, before, after, selected_detail)
    _mark_newly_confirmed_party_rows(timestep)
    new_keys = []
    new_ranks = []
    for row in new_rows:
        new_keys.append(row["visit_key"])
        new_ranks.append(row["assigned_rank"])
    first_party = None
    for row in GATE.party_rows:
        if row["tvt_decision_timestep"] == timestep:
            first_party = row
            break
    GATE.decision_rows.append(
        {
            "tvt_decision_timestep": timestep,
            "node_name": TARGET_NODE_NAME,
            "selected": selected_detail["selected"],
            "selected_candidate_evaluation_index": selected_detail[
                "selected_candidate_evaluation_index"
            ],
            "candidate_identity": selected_detail["candidate_identity"],
            "buyers_sorted": None if first_party is None else first_party["buyers_sorted"],
            "sellers_sorted": None if first_party is None else first_party["sellers_sorted"],
            "nonparticipating_visits_sorted": None
            if first_party is None
            else first_party["nonparticipating_visits_sorted"],
            "trade_scope": None if first_party is None else first_party["trade_scope"],
            "baseline_order": None if first_party is None else first_party["baseline_order"],
            "candidate_order": None if first_party is None else first_party["candidate_order"],
            "right_of_entry_visit_key": None
            if first_party is None
            else first_party["right_of_entry_visit_key"],
            "k_last_buyer": None if first_party is None else first_party["k_last_buyer"],
            "k_decision_window": None if first_party is None else first_party["k_decision_window"],
            "k_fixed": None if first_party is None else first_party["k_fixed"],
            "visits_in_binding_order": None
            if first_party is None
            else first_party["visits_in_binding_order"],
            "local_calculation_resolved": selected_detail["local_calculation_resolved"],
            "local_calculation_stop_reason": selected_detail["local_calculation_stop_reason"],
            "newly_confirmed_visit_keys": _join_text(new_keys),
            "newly_confirmed_assigned_ranks": _join_text(new_ranks),
        }
    )


def _append_actual_arrival_call_row(
    *,
    world_timestep,
    node_name,
    vehicle_name,
    visit_id,
    arrival_time_before,
    arrival_time_after,
    formal_arrival_timestep_after,
    was_first_recorded_call,
    was_already_recorded_in_diagnostic,
    diagnostic_first_arrival_timestep,
) -> None:
    GATE.actual_arrival_call_index = GATE.actual_arrival_call_index + 1
    GATE.actual_arrival_call_rows.append(
        {
            "call_index": GATE.actual_arrival_call_index,
            "world_timestep": world_timestep,
            "node_name": node_name,
            "vehicle_name": vehicle_name,
            "visit_id": visit_id,
            "visit_key": _visit_text(vehicle_name, visit_id),
            "arrival_time_before": arrival_time_before,
            "arrival_time_after": arrival_time_after,
            "formal_arrival_timestep_after": formal_arrival_timestep_after,
            "was_first_recorded_call": was_first_recorded_call,
            "was_already_recorded_in_diagnostic": was_already_recorded_in_diagnostic,
            "diagnostic_first_arrival_timestep": diagnostic_first_arrival_timestep,
        }
    )


def wrapped_prepare_baseline_fork(
    real_W,
    *,
    target_node_names,
    baseline_horizon_steps,
    apply_copied_tvt_confirmed_ranks,
):
    prepared = GATE.original_prepare(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=baseline_horizon_steps,
        apply_copied_tvt_confirmed_ranks=apply_copied_tvt_confirmed_ranks,
    )
    if (
        real_W is GATE.real_world
        and real_W.T == TARGET_DECISION_TIMESTEP
        and apply_copied_tvt_confirmed_ranks is True
    ):
        if GATE.baseline_world is not None:
            raise RuntimeError("T=382 baseline fork was prepared more than once.")
        if prepared.fork_W is real_W:
            raise RuntimeError("Prepared baseline fork is the real World.")
        if prepared.baseline_timestep_T != TARGET_DECISION_TIMESTEP:
            raise RuntimeError("Prepared baseline timestep is not T=382.")
        if getattr(real_W, "_order_control_baseline_collector", None) is not None:
            raise RuntimeError("Real World has a baseline collector during T=382 prepare.")
        GATE.baseline_world = prepared.fork_W
        GATE.baseline_collector = prepared.collector
        GATE.baseline_prepare_count = GATE.baseline_prepare_count + 1
        _capture_phase(real_W, "actual", TARGET_DECISION_TIMESTEP, PHASE_COMMON_ORIGIN)
        _capture_phase(prepared.fork_W, "baseline", TARGET_DECISION_TIMESTEP, PHASE_COMMON_ORIGIN)
        _require_common_origin_match()
    return prepared


def wrapped_align_baseline(
    real_W,
    *,
    target_node_names,
    baseline_horizon_steps,
    rank_states_by_node_name,
):
    result = GATE.original_align(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=baseline_horizon_steps,
        rank_states_by_node_name=rank_states_by_node_name,
    )
    if real_W is GATE.real_world and real_W.T == TARGET_DECISION_TIMESTEP:
        fork_result = result.fork_result
        if fork_result.baseline_timestep_T != TARGET_DECISION_TIMESTEP:
            raise RuntimeError("Aligned baseline fork is not the T=382 fork.")
        if TARGET_NODE_NAME not in fork_result.target_node_names:
            raise RuntimeError("T=382 baseline fork does not include northwest_intersection.")
        if fork_result.collector is not GATE.baseline_collector:
            raise RuntimeError("Aligned baseline collector is not the prepared T=382 collector.")
        if GATE.baseline_world is None or GATE.baseline_world is real_W:
            raise RuntimeError("Aligned T=382 baseline World is missing or is the real World.")
        GATE.baseline_identity_confirmed = True
        GATE.baseline_target_node_names = tuple(fork_result.target_node_names)
    return result


def wrapped_driver(world):
    kind = _world_kind(world)
    timestep = world.T
    if kind == "actual" and timestep == ACTUAL_TRACE_END_TIMESTEP + 1:
        _capture_phase(world, "actual", ACTUAL_TRACE_END_TIMESTEP, PHASE_AFTER_TIMESTEP)
        GATE.actual_trace_completed = True
        raise _StopAfterActualT407()
    if (
        kind == "actual"
        and type(timestep) is int
        and TARGET_DECISION_TIMESTEP < timestep <= ACTUAL_TRACE_END_TIMESTEP
    ):
        _capture_phase(world, "actual", timestep - 1, PHASE_AFTER_TIMESTEP)
    if (
        kind == "baseline"
        and type(timestep) is int
        and TARGET_DECISION_TIMESTEP < timestep <= BASELINE_TRACE_END_TIMESTEP + 1
    ):
        _capture_phase(world, "baseline", timestep - 1, PHASE_AFTER_TIMESTEP)
    record_decision = (
        kind == "actual"
        and type(timestep) is int
        and TARGET_DECISION_TIMESTEP <= timestep <= ACTUAL_TRACE_END_TIMESTEP
    )
    before_ranks = None
    if record_decision is True:
        before_ranks = _rank_map(world)
    result = GATE.original_driver(world)
    if record_decision is True:
        after_ranks = _rank_map(world)
        _record_decision(world, timestep, before_ranks, after_ranks, result)
    return result


def _link_ends_for(world, kind):
    order_key = (kind, id(world), world.T)
    if order_key not in GATE.link_ends:
        links = list(world.LINKS)
        if len(links) == 0:
            GATE.link_ends[order_key] = (None, None)
        else:
            GATE.link_ends[order_key] = (links[0], links[-1])
    return GATE.link_ends[order_key]


def wrapped_link_update(link):
    world = link.W
    kind = _world_kind(world)
    record = kind is not None and _in_record_window(kind, world.T)
    first_link = None
    last_link = None
    if record is True or kind == "baseline":
        first_link, last_link = _link_ends_for(world, kind)
    if record is True and link is first_link:
        _capture_phase(world, kind, world.T, PHASE_BEFORE_LINK_UPDATE)
    # The baseline fork clears evaluation end, so it never enters the driver.
    # End of baseline timestep T is the state at the next Link.update entry.
    if kind == "baseline" and type(world.T) is int and link is first_link:
        previous_timestep = world.T - 1
        if TARGET_DECISION_TIMESTEP <= previous_timestep <= BASELINE_TRACE_END_TIMESTEP:
            _capture_phase(world, "baseline", previous_timestep, PHASE_AFTER_TIMESTEP)
    result = GATE.original_link_update(link)
    if record is True and link is last_link:
        _capture_phase(world, kind, world.T, PHASE_AFTER_LINK_UPDATE)
    return result


def _node_ends_for(world, kind):
    order_key = (kind, id(world), world.T)
    if order_key not in GATE.node_ends:
        nodes = list(world.NODES)
        if len(nodes) == 0:
            GATE.node_ends[order_key] = (None, None)
        else:
            GATE.node_ends[order_key] = (nodes[0], nodes[-1])
    return GATE.node_ends[order_key]


def wrapped_transfer(node):
    world = node.W
    kind = _world_kind(world)
    record = kind is not None and _in_record_window(kind, world.T)
    first_node = None
    last_node = None
    if record is True:
        first_node, last_node = _node_ends_for(world, kind)
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
        order_key = (kind, id(world), world.T)
        if order_key not in GATE.vehicle_last_name:
            names = list(world.VEHICLES_LIVING.keys())
            if len(names) == 0:
                GATE.vehicle_last_name[order_key] = None
            else:
                GATE.vehicle_last_name[order_key] = names[-1]
        last_name = GATE.vehicle_last_name[order_key]
    result = GATE.original_vehicle_update(vehicle)
    if record is True and last_name is not None and getattr(vehicle, "name", None) == last_name:
        _capture_phase(world, kind, world.T, PHASE_AFTER_VEHICLE_UPDATE)
    return result


def wrapped_move(node, vehicle, inlink, outlink):
    world = node.W
    kind = _world_kind(world)
    record = (
        kind == "actual"
        and getattr(node, "name", None) == TARGET_NODE_NAME
        and _in_record_window("actual", world.T)
    )
    visit_pair = _plain_visit(vehicle) if record is True else None
    assigned_rank = _assigned_rank(world, visit_pair) if record is True else None
    vehicle_name = getattr(vehicle, "name", None) if record is True else None
    inlink_name = _link_name(inlink) if record is True else None
    outlink_name = _link_name(outlink) if record is True else None
    timestep = world.T if record is True else None
    result = GATE.original_move(node, vehicle, inlink, outlink)
    if record is True:
        GATE.actual_passes.append(
            {
                "world_timestep": timestep,
                "vehicle_name": vehicle_name,
                "visit_pair": visit_pair,
                "visit_key": None if visit_pair is None else _visit_text(visit_pair[0], visit_pair[1]),
                "inlink_name": inlink_name,
                "outlink_name": outlink_name,
                "assigned_rank": assigned_rank,
            }
        )
    return result


def wrapped_arrival(vehicle, node):
    world = vehicle.W
    current_visit_before = getattr(vehicle, "order_control_current_visit", None)
    arrival_time_before = None
    if isinstance(current_visit_before, dict):
        arrival_time_before = current_visit_before.get("arrival_time")
    result = GATE.original_arrival(vehicle, node)
    if world is not GATE.real_world:
        return result
    if getattr(world, "_order_control_baseline_collector", None) is not None:
        return result
    if node is None or getattr(node, "name", None) != TARGET_NODE_NAME:
        return result
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return result
    if current_visit.get("node") is not node:
        return result
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return result
    party = _party_by_visit(vehicle.name, visit_id)
    if party is None:
        return result
    arrival_time_after = current_visit.get("arrival_time")
    world_timestep = world.T
    formal_arrival_timestep_after = None
    if arrival_time_after is not None:
        formal_arrival_timestep_after = _formal_arrival_timestep_from_time(
            arrival_time_after,
            world.DELTAT,
        )
    key = _actual_arrival_key(node.name, vehicle.name, visit_id)
    was_already_recorded_in_diagnostic = key in GATE.actual_arrivals
    was_first_recorded_call = False
    diagnostic_first_arrival_timestep = None
    if arrival_time_after is not None:
        if type(world_timestep) is not int or type(world_timestep) is bool:
            raise RuntimeError(
                f"Actual arrival for {_visit_text(vehicle.name, visit_id)} at "
                f"{node.name}: World.T is {world_timestep!r}."
            )
        if was_already_recorded_in_diagnostic is not True:
            if formal_arrival_timestep_after != world_timestep:
                raise RuntimeError(
                    f"First actual arrival for {_visit_text(vehicle.name, visit_id)}: "
                    f"formal timestep {formal_arrival_timestep_after} does not match "
                    f"World.T={world_timestep}."
                )
            GATE.actual_arrivals[key] = {
                "timestep": formal_arrival_timestep_after,
                "formal_arrival_time": arrival_time_after,
                "current_link_name": _link_name(getattr(vehicle, "link", None)),
                "vehicle_name": vehicle.name,
                "visit_id": visit_id,
                "node_name": node.name,
            }
            was_first_recorded_call = True
            diagnostic_first_arrival_timestep = formal_arrival_timestep_after
        else:
            stored = GATE.actual_arrivals[key]
            diagnostic_first_arrival_timestep = stored["timestep"]
            stored_formal = _formal_arrival_timestep_from_time(
                stored["formal_arrival_time"],
                world.DELTAT,
            )
            if stored_formal != formal_arrival_timestep_after:
                raise RuntimeError(
                    f"Re-registration for {_visit_text(vehicle.name, visit_id)} at T={world_timestep}: "
                    f"production arrival_time implies timestep {formal_arrival_timestep_after}, "
                    f"but diagnostic first arrival is {stored_formal}."
                )
            if stored["formal_arrival_time"] != arrival_time_after:
                raise RuntimeError(
                    f"Re-registration for {_visit_text(vehicle.name, visit_id)} at T={world_timestep}: "
                    "production arrival_time changed from the diagnostic first value."
                )
    _append_actual_arrival_call_row(
        world_timestep=world_timestep,
        node_name=node.name,
        vehicle_name=vehicle.name,
        visit_id=visit_id,
        arrival_time_before=arrival_time_before,
        arrival_time_after=arrival_time_after,
        formal_arrival_timestep_after=formal_arrival_timestep_after,
        was_first_recorded_call=was_first_recorded_call,
        was_already_recorded_in_diagnostic=was_already_recorded_in_diagnostic,
        diagnostic_first_arrival_timestep=diagnostic_first_arrival_timestep,
    )
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Arrival divergence hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_prepare = baseline_driver_module._prepare_baseline_fork
    GATE.original_align = driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_link_update = uxsim_module.Link.update
    GATE.original_transfer = uxsim_module.Node.transfer
    GATE.original_vehicle_update = uxsim_module.Vehicle.update
    GATE.original_move = uxsim_module.Node._transfer_one_vehicle_between_links
    GATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    GATE.installed = True
    baseline_driver_module._prepare_baseline_fork = wrapped_prepare_baseline_fork
    driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits = wrapped_align_baseline
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Link.update = wrapped_link_update
    uxsim_module.Node.transfer = wrapped_transfer
    uxsim_module.Vehicle.update = wrapped_vehicle_update
    uxsim_module.Node._transfer_one_vehicle_between_links = wrapped_move
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    baseline_driver_module._prepare_baseline_fork = GATE.original_prepare
    driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits = GATE.original_align
    driver_module.run_tvt_mp_driver = GATE.original_driver
    uxsim_module.Link.update = GATE.original_link_update
    uxsim_module.Node.transfer = GATE.original_transfer
    uxsim_module.Vehicle.update = GATE.original_vehicle_update
    uxsim_module.Node._transfer_one_vehicle_between_links = GATE.original_move
    uxsim_module.Vehicle.record_order_control_node_arrival = GATE.original_arrival
    GATE.original_prepare = None
    GATE.original_align = None
    GATE.original_driver = None
    GATE.original_link_update = None
    GATE.original_transfer = None
    GATE.original_vehicle_update = None
    GATE.original_move = None
    GATE.original_arrival = None
    GATE.real_world = None
    GATE.installed = False


def _snapshot_pair(rows, kind_filters):
    found = {}
    for kind in ("baseline", "actual"):
        matched = _rows_matching(rows, world_kind=kind, **kind_filters)
        if len(matched) > 1:
            raise RuntimeError(f"Duplicate snapshot for {kind} {kind_filters!r}.")
        if len(matched) == 1:
            found[kind] = matched[0]
    return found.get("baseline"), found.get("actual")


def _append_difference(subject_kind, subject_name, timestep, phase, field_name, baseline_value, actual_value, field_order):
    if baseline_value is None and actual_value is None:
        raise RuntimeError(
            f"Empty {subject_kind} {subject_name} {field_name} was treated as a difference."
        )
    GATE.first_difference_rows.append(
        {
            "subject_kind": subject_kind,
            "subject_name": subject_name,
            "world_timestep": timestep,
            "phase": phase,
            "field_name": field_name,
            "field_order": field_order,
            "is_first_field": field_order == 1,
            "baseline_value": baseline_value,
            "actual_value": actual_value,
        }
    )


def _first_vehicle_divergence(party):
    vehicle_name = party["vehicle_name"]
    timesteps = []
    for row in GATE.vehicle_rows:
        if row["vehicle_name"] != vehicle_name:
            continue
        if row["world_timestep"] not in timesteps:
            timesteps.append(row["world_timestep"])
    timesteps.sort()
    for timestep in timesteps:
        for phase in PHASE_ORDER:
            baseline, actual = _snapshot_pair(
                GATE.vehicle_rows,
                {
                    "vehicle_name": vehicle_name,
                    "world_timestep": timestep,
                    "phase": phase,
                },
            )
            if baseline is None or actual is None:
                continue
            differing = []
            for field_name in VEHICLE_COMPARE_FIELDS:
                if _same_value(baseline[field_name], actual[field_name]) is not True:
                    differing.append(field_name)
            if len(differing) == 0:
                continue
            field_order = 1
            for field_name in differing:
                _append_difference(
                    "target_vehicle",
                    vehicle_name,
                    timestep,
                    phase,
                    field_name,
                    baseline[field_name],
                    actual[field_name],
                    field_order,
                )
                field_order = field_order + 1
            return {
                "timestep": timestep,
                "phase": phase,
                "field": differing[0],
                "baseline": baseline,
                "actual": actual,
            }
    return None


def _inlink_field_differs(baseline, actual, field_name) -> bool:
    if field_name == "vehicle_order":
        return _sequences_equal(baseline["vehicle_names"], actual["vehicle_names"]) is not True
    if field_name == "position_order":
        return _sequences_equal(baseline["position_values"], actual["position_values"]) is not True
    if field_name == "speed_order":
        return _sequences_equal(baseline["speed_values"], actual["speed_values"]) is not True
    return _same_value(baseline[field_name], actual[field_name]) is not True


def _first_inlink_divergence(link_name):
    timesteps = []
    for row in GATE.inlink_rows:
        if row["link_name"] != link_name:
            continue
        if row["world_timestep"] not in timesteps:
            timesteps.append(row["world_timestep"])
    timesteps.sort()
    comparable = 0
    for timestep in timesteps:
        for phase in PHASE_ORDER:
            baseline, actual = _snapshot_pair(
                GATE.inlink_rows,
                {
                    "link_name": link_name,
                    "world_timestep": timestep,
                    "phase": phase,
                },
            )
            if baseline is None or actual is None:
                continue
            comparable = comparable + 1
            differing = []
            for field_name in (
                "vehicle_order",
                "position_order",
                "speed_order",
                "vehicle_count",
                "cum_departure_latest",
                "capacity_out_remain",
            ):
                if _inlink_field_differs(baseline, actual, field_name) is True:
                    differing.append(field_name)
            if len(differing) == 0:
                continue
            field_order = 1
            for field_name in differing:
                _append_difference(
                    "target_inlink",
                    link_name,
                    timestep,
                    phase,
                    field_name,
                    baseline[field_name],
                    actual[field_name],
                    field_order,
                )
                field_order = field_order + 1
            return {
                "timestep": timestep,
                "phase": phase,
                "field": differing[0],
                "baseline": baseline,
                "actual": actual,
                "comparable_count": comparable,
            }
    return {
        "timestep": None,
        "phase": None,
        "field": None,
        "baseline": None,
        "actual": None,
        "comparable_count": comparable,
    }


def _pass_is_before_divergence(pass_timestep, divergence_timestep, phase) -> bool:
    if pass_timestep < divergence_timestep:
        return True
    if pass_timestep > divergence_timestep:
        return False
    return phase in PHASES_AFTER_TRANSFER


def _preceding_inlink_pass(party, divergence):
    chosen = None
    for pass_row in GATE.actual_passes:
        if pass_row["inlink_name"] != party["inlink_name"]:
            continue
        if _pass_is_before_divergence(
            pass_row["world_timestep"],
            divergence["timestep"],
            divergence["phase"],
        ) is not True:
            continue
        chosen = pass_row
    return chosen


def _front_vehicles(link_name, world_kind, timestep, phase, party_index):
    rows = _rows_matching(
        GATE.inlink_vehicle_rows,
        world_kind=world_kind,
        world_timestep=timestep,
        phase=phase,
        link_name=link_name,
    )
    front = []
    for row in rows:
        if type(row["physical_index"]) is not int:
            continue
        if party_index is None or row["physical_index"] >= party_index:
            continue
        front.append(row)
    front.sort(key=lambda row: row["physical_index"])
    return front


def _front_state_differs(baseline_row, actual_row) -> bool:
    if baseline_row is None or actual_row is None:
        return True
    for field_name in ("physical_index", "position_x", "speed_v", "leader_vehicle_name"):
        if _same_value(baseline_row[field_name], actual_row[field_name]) is not True:
            return True
    return False


def _pass_for_vehicle(vehicle_name, visit_pair):
    chosen = None
    for pass_row in GATE.actual_passes:
        if pass_row["vehicle_name"] != vehicle_name:
            continue
        if visit_pair is not None and pass_row["visit_pair"] != visit_pair:
            continue
        if chosen is None or pass_row["world_timestep"] < chosen["world_timestep"]:
            chosen = pass_row
    return chosen


def _confirmation_text(visit_pair, assigned_rank):
    if visit_pair is None:
        return None
    found = GATE.newly_confirmed_by_key.get(visit_pair)
    if found is not None:
        return found["tvt_decision_timestep"]
    if assigned_rank is not None:
        return "confirmed_before_trace_window"
    return None


def _record_front_vehicles(party, divergence) -> dict:
    link_name = party["inlink_name"]
    baseline_party = divergence["baseline"]
    actual_party = divergence["actual"]
    on_baseline_inlink = baseline_party["current_link_name"] == link_name
    on_actual_inlink = actual_party["current_link_name"] == link_name
    baseline_index = baseline_party["physical_index"] if on_baseline_inlink is True else None
    actual_index = actual_party["physical_index"] if on_actual_inlink is True else None
    baseline_front = _front_vehicles(
        link_name,
        "baseline",
        divergence["timestep"],
        divergence["phase"],
        baseline_index,
    )
    actual_front = _front_vehicles(
        link_name,
        "actual",
        divergence["timestep"],
        divergence["phase"],
        actual_index,
    )
    by_name = {"baseline": {}, "actual": {}}
    for row in baseline_front:
        by_name["baseline"][row["vehicle_name"]] = row
    for row in actual_front:
        by_name["actual"][row["vehicle_name"]] = row
    ordered_names = []
    for row in baseline_front:
        if row["vehicle_name"] not in ordered_names:
            ordered_names.append(row["vehicle_name"])
    for row in actual_front:
        if row["vehicle_name"] not in ordered_names:
            ordered_names.append(row["vehicle_name"])

    def _node_side_index(vehicle_name):
        indexes = []
        for world_kind in ("baseline", "actual"):
            row = by_name[world_kind].get(vehicle_name)
            if row is not None:
                indexes.append(row["physical_index"])
        return min(indexes)

    ordered_names.sort(key=_node_side_index)
    first_name = None
    first_baseline = None
    first_actual = None
    for vehicle_name in ordered_names:
        baseline_row = by_name["baseline"].get(vehicle_name)
        actual_row = by_name["actual"].get(vehicle_name)
        differs = _front_state_differs(baseline_row, actual_row)
        if first_name is None and differs is True:
            first_name = vehicle_name
            first_baseline = baseline_row
            first_actual = actual_row
        for world_kind, row in (("baseline", baseline_row), ("actual", actual_row)):
            if row is None:
                continue
            pass_row = _pass_for_vehicle(vehicle_name, row["visit_pair"])
            GATE.front_rows.append(
                {
                    "party_vehicle_name": party["vehicle_name"],
                    "party_visit_key": _visit_text(party["vehicle_name"], party["visit_id"]),
                    "world_kind": world_kind,
                    "world_timestep": divergence["timestep"],
                    "phase": divergence["phase"],
                    "inlink_name": link_name,
                    "front_order_from_node": row["physical_index"] + 1,
                    "vehicle_name": vehicle_name,
                    "physical_index": row["physical_index"],
                    "position_x": row["position_x"],
                    "speed_v": row["speed_v"],
                    "leader_vehicle_name": row["leader_vehicle_name"],
                    "state_differs_from_other_world": differs,
                    "is_first_divergent_front_vehicle": vehicle_name == first_name and differs is True,
                    "actual_passage_timestep": None if pass_row is None else pass_row["world_timestep"],
                    "assigned_rank": row["assigned_rank"],
                    "rank_confirmation_decision_timestep": _confirmation_text(
                        row["visit_pair"],
                        row["assigned_rank"],
                    ),
                }
            )
    observed = first_actual if first_actual is not None else first_baseline
    pass_row = None if first_name is None else _pass_for_vehicle(
        first_name,
        None if observed is None else observed["visit_pair"],
    )
    return {
        "name": first_name,
        "physical_index": None if observed is None else observed["physical_index"],
        "position_x": None if observed is None else observed["position_x"],
        "speed_v": None if observed is None else observed["speed_v"],
        "leader_vehicle_name": None if observed is None else observed["leader_vehicle_name"],
        "actual_passage_timestep": None if pass_row is None else pass_row["world_timestep"],
        "assigned_rank": None if observed is None else observed["assigned_rank"],
        "rank_confirmation_decision_timestep": None
        if observed is None
        else _confirmation_text(observed["visit_pair"], observed["assigned_rank"]),
    }


def _relevant_decision_timesteps(divergence) -> list:
    timesteps = []
    for row in GATE.decision_rows:
        if row["selected"] is not True:
            continue
        timestep = row["tvt_decision_timestep"]
        if divergence["phase"] == PHASE_COMMON_ORIGIN:
            include = timestep < divergence["timestep"]
        else:
            include = timestep <= divergence["timestep"]
        if include is True:
            timesteps.append(timestep)
    return timesteps


def _local_prediction_text(decision_timestep, visit_pair) -> str:
    if visit_pair is None:
        return "通過VisitKeyが記録されていない。"
    decision = None
    for row in GATE.decision_rows:
        if row["tvt_decision_timestep"] == decision_timestep:
            decision = row
    if decision is None:
        return f"T={decision_timestep} の decision 行がない。"
    if decision["selected"] is not True:
        return f"T={decision_timestep} は selected Candidate を持たない。"
    party_row = None
    for row in GATE.party_rows:
        if row["tvt_decision_timestep"] != decision_timestep:
            continue
        if row["vehicle_name"] == visit_pair[0] and row["visit_id"] == visit_pair[1]:
            party_row = row
    if party_row is None:
        return (
            f"T={decision_timestep} の selected Candidate 保存結果に "
            f"{_visit_text(visit_pair[0], visit_pair[1])} は含まれない。"
        )
    return (
        f"T={decision_timestep} identity={decision['candidate_identity']} "
        f"candidate_passage={party_row['candidate_passage_timestep']} "
        f"baseline_passage={party_row['baseline_passage_timestep']} "
        f"predicted_route={party_row['predicted_route_next_link_name']} "
        f"resolved={party_row['local_calculation_resolved']} "
        f"stop_reason={party_row['local_calculation_stop_reason']}."
    )


def _eight_points(party, divergence, inlink_report, preceding, front) -> list:
    baseline = divergence["baseline"]
    actual = divergence["actual"]
    field_name = divergence["field"]
    points = []
    points.append(
        "1. 最初の物理差は "
        f"T={divergence['timestep']} phase={divergence['phase']} の {field_name} である。"
        f" Baseline={baseline[field_name]!r} Actual={actual[field_name]!r}。"
        f" この時点の leader は Baseline={baseline['leader_vehicle_name']!r} "
        f"Actual={actual['leader_vehicle_name']!r}、physical index は "
        f"Baseline={baseline['physical_index']!r} Actual={actual['physical_index']!r}。"
        f" 最初に状態が異なった前方Vehicleは {front['name']!r}。"
    )
    if inlink_report["field"] is None:
        points.append(
            f"2. 対象inlink {party['inlink_name']} では、比較できた phase に "
            "Vehicle順、位置順、速度順、台数、cum departure、capacity out の差はない。"
        )
    else:
        points.append(
            "2. 対象inlinkの最初の差は "
            f"T={inlink_report['timestep']} phase={inlink_report['phase']} の "
            f"{inlink_report['field']} である。"
            f" Baseline={inlink_report['baseline'][inlink_report['field']]!r} "
            f"Actual={inlink_report['actual'][inlink_report['field']]!r}。"
        )
    if preceding is None:
        points.append("3. この物理差より前に、同じ対象inlinkから northwest_intersection へ出た Actual 通過は記録されていない。")
        confirmation_timestep = None
        visit_pair = None
    else:
        visit_pair = preceding["visit_pair"]
        points.append(
            "3. この物理差より前の最後の対象inlink流出は "
            f"T={preceding['world_timestep']} {_visit_text_or_name(preceding)} "
            f"inlink={preceding['inlink_name']} outlink={preceding['outlink_name']} "
            f"assigned_rank={preceding['assigned_rank']!r}。"
        )
        confirmation = None if visit_pair is None else GATE.newly_confirmed_by_key.get(visit_pair)
        if confirmation is None:
            confirmation_timestep = None
            if preceding["assigned_rank"] is None:
                points.append("4. その通過Visitは、通過時点の記録では C 順位が付いていない。")
            else:
                points.append(
                    "4. その通過Visitの C 順位は、この追跡窓の decision では新規確定として現れていない。"
                    " T=382 より前に確定済みの可能性がある。"
                )
        else:
            confirmation_timestep = confirmation["tvt_decision_timestep"]
            points.append(
                "4. その通過Visitの C 順位は "
                f"T={confirmation_timestep} で初めて確定し、assigned rank は "
                f"{confirmation['assigned_rank']} である。"
            )
    if preceding is None or confirmation_timestep is None:
        points.append("5. 直前の流出に対応する順位確定 decision がないため、selected Candidate の局所予測はここに結び付かない。")
    else:
        points.append(
            "5. その順位確定 decision の selected Candidate 局所予測: "
            + _local_prediction_text(confirmation_timestep, visit_pair)
        )
    points.append(
        "6. 後続 decision がこの物理差の直接原因かどうかは、反事実を計算していないため未確定である。"
    )
    points.append(
        "7. 後続 decision が単なる先行事象で、直接原因が spillback、clearance、entry space、"
        "進路、または Vehicle 運動の別にあるかどうかも、現在の snapshot だけでは未確定である。"
    )
    points.append(
        "8. T=390 の特定 Visit は既存の確認一覧にない。最初の差が到着差の何 timestep を説明するかも、"
        "この記録だけでは分解していない。"
    )
    return points


def _visit_text_or_name(pass_row) -> str:
    if pass_row["visit_key"] is not None:
        return pass_row["visit_key"]
    return str(pass_row["vehicle_name"])


def _arrival_audit_summary(party) -> dict:
    rows = _arrival_call_rows_for_party(party)
    first_rows = []
    for row in rows:
        if row["was_first_recorded_call"] is True:
            first_rows.append(row)
    first_call_timestep = None
    if len(first_rows) == 1:
        first_call_timestep = first_rows[0]["world_timestep"]
    first_formal = None
    later_timesteps = []
    for row in rows:
        if row["was_first_recorded_call"] is True:
            first_formal = row["formal_arrival_timestep_after"]
        elif row["formal_arrival_timestep_after"] is not None:
            later_timesteps.append(row["world_timestep"])
    later_kept = True
    if first_formal is not None:
        for row in rows:
            if row["was_first_recorded_call"] is True:
                continue
            if row["formal_arrival_timestep_after"] is None:
                continue
            if row["formal_arrival_timestep_after"] != first_formal:
                later_kept = False
    return {
        "arrival_method_call_count": len(rows),
        "first_arrival_call_timestep": first_call_timestep,
        "later_re_registration_call_timesteps": _join_text(later_timesteps),
        "later_calls_kept_production_arrival_time": later_kept,
    }


def _points_without_physical_divergence(party, arrival_info, audit_info) -> list:
    return [
        (
            "1. 追跡窓内で Baseline と Actual の対象 Vehicle snapshot に物理差は見つからなかった。"
        ),
        (
            "2. 正式な初回 Actual arrival は "
            f"T={arrival_info['actual_arrival_timestep']}、Baseline arrival は "
            f"T={arrival_info['baseline_arrival_timestep']}、差は "
            f"{arrival_info['arrival_difference_timesteps']} timestep。"
        ),
        (
            "3. record_order_control_node_arrival の呼出し回数は "
            f"{audit_info['arrival_method_call_count']}。初回記録呼出しは "
            f"T={audit_info['first_arrival_call_timestep']}。"
        ),
        (
            "4. 再呼出し timestep: "
            f"{audit_info['later_re_registration_call_timesteps'] or '(なし)'}。"
            f" 再呼出しでも production arrival_time は初回値を維持した: "
            f"{audit_info['later_calls_kept_production_arrival_time']}。"
        ),
        (
            "5. 旧 rank_and_passage_trace は production 呼出し後に同一 VisitKey を"
            "無条件上書きしていたため、その Actual 到着値は初回到着ではない。"
        ),
        "6. 到着差は正式な初回 Actual arrival と Baseline arrival の差として扱う。",
        "7. 途中の物理状態差が無い場合でも、到着差 0 は許容する。",
        "8. 到着差が 0 以外なのに物理差が無い場合は runtime validation で停止する。",
    ]


def _build_analysis() -> None:
    GATE.first_difference_rows = []
    GATE.front_rows = []
    GATE.party_reports = []
    GATE.inlink_reports = []
    inlink_by_name = {}
    for link_name in TARGET_INLINK_NAMES:
        report = _first_inlink_divergence(link_name)
        inlink_by_name[link_name] = report
        GATE.inlink_reports.append(report)
    for party in TARGET_PARTIES:
        arrival_info = GATE.party_arrival_by_vehicle[party["vehicle_name"]]
        audit_info = _arrival_audit_summary(party)
        divergence = _first_vehicle_divergence(party)
        inlink_report = inlink_by_name[party["inlink_name"]]
        common_baseline, common_actual = _snapshot_pair(
            GATE.vehicle_rows,
            {
                "vehicle_name": party["vehicle_name"],
                "world_timestep": TARGET_DECISION_TIMESTEP,
                "phase": PHASE_COMMON_ORIGIN,
            },
        )
        if divergence is None:
            points = _points_without_physical_divergence(party, arrival_info, audit_info)
            report = {
                "vehicle_name": party["vehicle_name"],
                "visit_id": party["visit_id"],
                "inlink_name": party["inlink_name"],
                "baseline_arrival_timestep": arrival_info["baseline_arrival_timestep"],
                "actual_arrival_timestep": arrival_info["actual_arrival_timestep"],
                "arrival_difference_timesteps": arrival_info["arrival_difference_timesteps"],
                "arrival_method_call_count": audit_info["arrival_method_call_count"],
                "first_arrival_call_timestep": audit_info["first_arrival_call_timestep"],
                "later_re_registration_call_timesteps": audit_info[
                    "later_re_registration_call_timesteps"
                ],
                "later_calls_kept_production_arrival_time": audit_info[
                    "later_calls_kept_production_arrival_time"
                ],
                "common_origin_position_baseline": common_baseline["position_x"],
                "common_origin_position_actual": common_actual["position_x"],
                "common_origin_speed_baseline": common_baseline["speed_v"],
                "common_origin_speed_actual": common_actual["speed_v"],
                "common_origin_physical_index_baseline": common_baseline["physical_index"],
                "common_origin_physical_index_actual": common_actual["physical_index"],
                "first_divergence_timestep": None,
                "first_divergence_phase": None,
                "first_divergence_field": None,
                "baseline_value_at_first_divergence": None,
                "actual_value_at_first_divergence": None,
                "baseline_leader_at_first_divergence": None,
                "actual_leader_at_first_divergence": None,
                "baseline_physical_index_at_first_divergence": None,
                "actual_physical_index_at_first_divergence": None,
                "first_divergent_front_vehicle_name": None,
                "relevant_selected_decision_timesteps": "",
                "immediate_explanation": " ".join(points[0:5]),
                "remaining_uncertainty": " ".join(points[5:8]),
                "points": points,
            }
        else:
            preceding = _preceding_inlink_pass(party, divergence)
            front = _record_front_vehicles(party, divergence)
            points = _eight_points(party, divergence, inlink_report, preceding, front)
            relevant = _relevant_decision_timesteps(divergence)
            arrival_diff = arrival_info["arrival_difference_timesteps"]
            if arrival_diff != 0:
                points[0] = (
                    points[0]
                    + f" 正式な初回 Actual arrival は T={arrival_info['actual_arrival_timestep']}、"
                    f"Baseline arrival は T={arrival_info['baseline_arrival_timestep']}、"
                    f"到着差は {arrival_diff} timestep。"
                )
            report = {
                "vehicle_name": party["vehicle_name"],
                "visit_id": party["visit_id"],
                "inlink_name": party["inlink_name"],
                "baseline_arrival_timestep": arrival_info["baseline_arrival_timestep"],
                "actual_arrival_timestep": arrival_info["actual_arrival_timestep"],
                "arrival_difference_timesteps": arrival_info["arrival_difference_timesteps"],
                "arrival_method_call_count": audit_info["arrival_method_call_count"],
                "first_arrival_call_timestep": audit_info["first_arrival_call_timestep"],
                "later_re_registration_call_timesteps": audit_info[
                    "later_re_registration_call_timesteps"
                ],
                "later_calls_kept_production_arrival_time": audit_info[
                    "later_calls_kept_production_arrival_time"
                ],
                "common_origin_position_baseline": common_baseline["position_x"],
                "common_origin_position_actual": common_actual["position_x"],
                "common_origin_speed_baseline": common_baseline["speed_v"],
                "common_origin_speed_actual": common_actual["speed_v"],
                "common_origin_physical_index_baseline": common_baseline["physical_index"],
                "common_origin_physical_index_actual": common_actual["physical_index"],
                "first_divergence_timestep": divergence["timestep"],
                "first_divergence_phase": divergence["phase"],
                "first_divergence_field": divergence["field"],
                "baseline_value_at_first_divergence": divergence["baseline"][divergence["field"]],
                "actual_value_at_first_divergence": divergence["actual"][divergence["field"]],
                "baseline_leader_at_first_divergence": divergence["baseline"]["leader_vehicle_name"],
                "actual_leader_at_first_divergence": divergence["actual"]["leader_vehicle_name"],
                "baseline_physical_index_at_first_divergence": divergence["baseline"]["physical_index"],
                "actual_physical_index_at_first_divergence": divergence["actual"]["physical_index"],
                "first_divergent_front_vehicle_name": front["name"],
                "relevant_selected_decision_timesteps": _join_text(relevant),
                "immediate_explanation": " ".join(points[0:5]),
                "remaining_uncertainty": " ".join(points[5:8]),
                "points": points,
            }
        GATE.party_reports.append(report)


def _require_phase(kind, timestep, phase, vehicle_name) -> None:
    rows = _rows_matching(
        GATE.vehicle_rows,
        world_kind=kind,
        world_timestep=timestep,
        phase=phase,
        vehicle_name=vehicle_name,
    )
    if len(rows) != 1:
        raise RuntimeError(
            f"{kind} T={timestep} {phase} {vehicle_name} snapshot count is {len(rows)}."
        )


def _validate_phase_coverage() -> None:
    for party in TARGET_PARTIES:
        vehicle_name = party["vehicle_name"]
        for kind, end_timestep in (
            ("baseline", BASELINE_TRACE_END_TIMESTEP),
            ("actual", ACTUAL_TRACE_END_TIMESTEP),
        ):
            timestep = TARGET_DECISION_TIMESTEP
            while timestep <= end_timestep:
                for phase in PHASE_ORDER:
                    if phase == PHASE_COMMON_ORIGIN and timestep != TARGET_DECISION_TIMESTEP:
                        continue
                    if phase == PHASE_COMMON_ORIGIN:
                        _require_phase(kind, timestep, phase, vehicle_name)
                        continue
                    _require_phase(kind, timestep, phase, vehicle_name)
                timestep = timestep + 1


def _validate_trace_bounds(world) -> None:
    for row in GATE.vehicle_rows:
        if row["world_kind"] not in ("baseline", "actual"):
            raise RuntimeError(f"Unexpected world kind {row['world_kind']!r}.")
        if row["world_kind"] == "baseline" and row["world_timestep"] > BASELINE_TRACE_END_TIMESTEP:
            raise RuntimeError("Baseline snapshot was saved after T=394.")
        if row["world_kind"] == "actual" and row["world_timestep"] > ACTUAL_TRACE_END_TIMESTEP:
            raise RuntimeError("Actual snapshot was saved after T=407.")
    if GATE.baseline_prepare_count != 1:
        raise RuntimeError(f"T=382 baseline prepare count is {GATE.baseline_prepare_count}.")
    if GATE.baseline_identity_confirmed is not True:
        raise RuntimeError("T=382 aligned baseline identity was not confirmed.")
    if GATE.baseline_world is None:
        raise RuntimeError("T=382 baseline World was not captured.")
    if GATE.baseline_world is world:
        raise RuntimeError("T=382 baseline World is the real World.")
    if GATE.baseline_target_node_names is None or TARGET_NODE_NAME not in GATE.baseline_target_node_names:
        raise RuntimeError("T=382 baseline target nodes do not include northwest_intersection.")
    if GATE.actual_trace_completed is not True:
        raise RuntimeError("Actual trace did not record completion of T=407.")


def _validate_formal_arrivals() -> None:
    if GATE.baseline_collector is None:
        raise RuntimeError("T=382 baseline collector is missing.")
    GATE.party_arrival_by_vehicle = {}
    for party in TARGET_PARTIES:
        snapshot = GATE.baseline_collector.get_baseline_visit_snapshot(
            party["vehicle_name"],
            party["visit_id"],
        )
        if snapshot is None:
            raise RuntimeError(
                f"Baseline collector has no snapshot for "
                f"{_visit_text(party['vehicle_name'], party['visit_id'])}."
            )
        if snapshot["node_name"] != TARGET_NODE_NAME:
            raise RuntimeError(
                f"{party['vehicle_name']} baseline snapshot node is {snapshot['node_name']!r}."
            )
        if snapshot["inlink_name"] != party["inlink_name"]:
            raise RuntimeError(
                f"{party['vehicle_name']} formal inlink is {snapshot['inlink_name']!r}, "
                f"not {party['inlink_name']}."
            )
        if snapshot["baseline_arrival_timestep"] != party["baseline_arrival_timestep"]:
            raise RuntimeError(
                f"{party['vehicle_name']} baseline arrival is "
                f"{snapshot['baseline_arrival_timestep']!r}, "
                f"not {party['baseline_arrival_timestep']}."
            )
        key = _actual_arrival_key(TARGET_NODE_NAME, party["vehicle_name"], party["visit_id"])
        arrival = GATE.actual_arrivals.get(key)
        if arrival is None:
            raise RuntimeError(
                f"Actual first arrival was not recorded for {_visit_text(party['vehicle_name'], party['visit_id'])}."
            )
        actual_timestep = arrival["timestep"]
        if type(actual_timestep) is not int or type(actual_timestep) is bool:
            raise RuntimeError(
                f"{party['vehicle_name']} actual first arrival timestep is {actual_timestep!r}."
            )
        if arrival["visit_id"] != party["visit_id"]:
            raise RuntimeError(
                f"{party['vehicle_name']} actual arrival visit id is {arrival['visit_id']!r}."
            )
        if actual_timestep < TARGET_DECISION_TIMESTEP:
            raise RuntimeError(
                f"{party['vehicle_name']} actual first arrival {actual_timestep} is before T=382."
            )
        if actual_timestep > ACTUAL_TRACE_END_TIMESTEP:
            raise RuntimeError(
                f"{party['vehicle_name']} actual first arrival {actual_timestep} is after T=407."
            )
        if arrival["current_link_name"] != party["inlink_name"]:
            raise RuntimeError(
                f"{party['vehicle_name']} actual arrival link is {arrival['current_link_name']!r}."
            )
        arrival_difference = actual_timestep - snapshot["baseline_arrival_timestep"]
        call_rows = _arrival_call_rows_for_party(party)
        first_record_rows = []
        for row in call_rows:
            if row["was_first_recorded_call"] is True:
                first_record_rows.append(row)
        if len(first_record_rows) != 1:
            raise RuntimeError(
                f"{party['vehicle_name']} must have exactly one first-recorded arrival call, "
                f"got {len(first_record_rows)}."
            )
        first_formal = first_record_rows[0]["formal_arrival_timestep_after"]
        if first_formal != actual_timestep:
            raise RuntimeError(
                f"{party['vehicle_name']} first call formal timestep {first_formal} "
                f"does not match diagnostic first arrival {actual_timestep}."
            )
        for row in call_rows:
            if row["was_first_recorded_call"] is True:
                continue
            if row["formal_arrival_timestep_after"] is None:
                continue
            if row["formal_arrival_timestep_after"] != first_formal:
                raise RuntimeError(
                    f"{party['vehicle_name']} re-registration at T={row['world_timestep']} "
                    "changed production formal arrival timestep."
                )
            if row["diagnostic_first_arrival_timestep"] != actual_timestep:
                raise RuntimeError(
                    f"{party['vehicle_name']} re-registration row does not reference "
                    "the diagnostic first arrival timestep."
                )
        GATE.party_arrival_by_vehicle[party["vehicle_name"]] = {
            "baseline_arrival_timestep": snapshot["baseline_arrival_timestep"],
            "actual_arrival_timestep": actual_timestep,
            "arrival_difference_timesteps": arrival_difference,
        }


def _validate_decisions() -> None:
    timesteps = []
    for row in GATE.decision_rows:
        timesteps.append(row["tvt_decision_timestep"])
        if row["node_name"] != TARGET_NODE_NAME:
            raise RuntimeError("Decision row node is not northwest_intersection.")
        if row["selected"] is True:
            index = row["selected_candidate_evaluation_index"]
            if type(index) is not int or type(index) is bool or index < 1:
                raise RuntimeError(f"T={row['tvt_decision_timestep']} evaluation index is {index!r}.")
            if row["candidate_identity"] is None:
                raise RuntimeError(f"T={row['tvt_decision_timestep']} selected identity is missing.")
        elif row["selected"] is False:
            if row["selected_candidate_evaluation_index"] is not None:
                raise RuntimeError("Unselected decision has an evaluation index.")
            if row["candidate_identity"] is not None:
                raise RuntimeError("Unselected decision has a candidate identity.")
        else:
            raise RuntimeError("Decision selected flag is not True or False.")
    expected = []
    timestep = TARGET_DECISION_TIMESTEP
    while timestep <= ACTUAL_TRACE_END_TIMESTEP:
        expected.append(timestep)
        timestep = timestep + 1
    if timesteps != expected:
        raise RuntimeError(
            f"Northwest decision timesteps are {timesteps!r}, not {expected!r}."
        )
    selected_timesteps = set()
    for row in GATE.decision_rows:
        if row["selected"] is True:
            selected_timesteps.add(row["tvt_decision_timestep"])
    for timestep in selected_timesteps:
        party_count = 0
        for row in GATE.party_rows:
            if row["tvt_decision_timestep"] == timestep:
                party_count = party_count + 1
        if party_count == 0:
            raise RuntimeError(f"T={timestep} selected candidate has no saved party rows.")
    for row in GATE.party_rows:
        if row["selected"] is not True:
            raise RuntimeError("Party row is not a selected candidate row.")
        if row["tvt_decision_timestep"] not in selected_timesteps:
            raise RuntimeError("Party row belongs to an unselected decision.")
        if row["newly_confirmed_by_this_decision"] is True:
            key = (row["vehicle_name"], row["visit_id"])
            confirmed = GATE.newly_confirmed_by_key.get(key)
            if confirmed is None or confirmed["tvt_decision_timestep"] != row["tvt_decision_timestep"]:
                raise RuntimeError(
                    f"{row['visit_key']} is marked newly confirmed without a ledger diff."
                )
    seen = {}
    for row in GATE.newly_confirmed_rows:
        key = (row["vehicle_name"], row["visit_id"])
        if key in seen:
            raise RuntimeError(f"{row['visit_key']} is newly confirmed more than once.")
        seen[key] = row
    for known in KNOWN_LATER_CONFIRMATIONS:
        key = (known["vehicle_name"], known["visit_id"])
        found = seen.get(key)
        if found is None:
            raise RuntimeError(
                f"Known later visit {_visit_text(key[0], key[1])} was not newly confirmed."
            )
        if found["tvt_decision_timestep"] != known["decision_timestep"]:
            raise RuntimeError(
                f"{_visit_text(key[0], key[1])} confirmation timestep is "
                f"{found['tvt_decision_timestep']}, not {known['decision_timestep']}."
            )
        if found["assigned_rank"] != known["assigned_rank"]:
            raise RuntimeError(
                f"{_visit_text(key[0], key[1])} assigned rank is "
                f"{found['assigned_rank']}, not {known['assigned_rank']}."
            )
        pass_row = _pass_for_vehicle(known["vehicle_name"], key)
        if pass_row is None:
            raise RuntimeError(
                f"Known later visit {_visit_text(key[0], key[1])} has no actual passage."
            )
        if pass_row["world_timestep"] != known["actual_passage_timestep"]:
            raise RuntimeError(
                f"{_visit_text(key[0], key[1])} actual passage is "
                f"{pass_row['world_timestep']}, not {known['actual_passage_timestep']}."
            )
        if pass_row["assigned_rank"] != known["assigned_rank"]:
            raise RuntimeError(
                f"{_visit_text(key[0], key[1])} assigned C rank at passage is "
                f"{pass_row['assigned_rank']!r}, not {known['assigned_rank']}."
            )


def _validate_analysis() -> None:
    if len(GATE.party_reports) != len(TARGET_PARTIES):
        raise RuntimeError("Party divergence count does not match the four parties.")
    reported_names = []
    for report in GATE.party_reports:
        reported_names.append(report["vehicle_name"])
        vehicle_differences = _rows_matching(
            GATE.first_difference_rows,
            subject_kind="target_vehicle",
            subject_name=report["vehicle_name"],
        )
        arrival_diff = report["arrival_difference_timesteps"]
        has_divergence = report["first_divergence_timestep"] is not None
        if arrival_diff != 0 and has_divergence is not True:
            raise RuntimeError(
                f"{report['vehicle_name']} has arrival difference {arrival_diff} "
                "but no baseline/actual first divergence."
            )
        if has_divergence is not True:
            if len(vehicle_differences) != 0:
                raise RuntimeError(
                    f"{report['vehicle_name']} has first-difference rows without a divergence report."
                )
            continue
        if len(vehicle_differences) == 0:
            raise RuntimeError(f"{report['vehicle_name']} has no first-difference row.")
        first_rows = []
        for row in vehicle_differences:
            if row["is_first_field"] is True:
                first_rows.append(row)
        if len(first_rows) != 1:
            raise RuntimeError(f"{report['vehicle_name']} first-field row count is {len(first_rows)}.")
    if reported_names != [party["vehicle_name"] for party in TARGET_PARTIES]:
        raise RuntimeError("Party report order does not match the four parties.")
    if len(GATE.inlink_reports) != len(TARGET_INLINK_NAMES):
        raise RuntimeError("Inlink report count is not 4.")
    for link_name in TARGET_INLINK_NAMES:
        comparable = 0
        for phase in PHASE_ORDER:
            baseline, actual = _snapshot_pair(
                GATE.inlink_rows,
                {
                    "link_name": link_name,
                    "world_timestep": TARGET_DECISION_TIMESTEP,
                    "phase": phase,
                },
            )
            if baseline is not None and actual is not None:
                comparable = comparable + 1
        if comparable == 0:
            raise RuntimeError(f"{link_name} has no comparable baseline/actual snapshot.")
    for row in GATE.first_difference_rows:
        if row["baseline_value"] is None and row["actual_value"] is None:
            raise RuntimeError("A first-difference row has no values on either side.")


def _validate_runtime(world) -> None:
    if trial.reference.NORTHWEST_INTERSECTION != TARGET_NODE_NAME:
        raise RuntimeError("Trial northwest node name does not match northwest_intersection.")
    if world.T != ACTUAL_TRACE_END_TIMESTEP + 1:
        raise RuntimeError(f"Actual World stopped at T={world.T}, not at the T=408 entry.")
    _require_common_origin_match()
    _validate_trace_bounds(world)
    _validate_phase_coverage()
    _validate_formal_arrivals()
    _validate_decisions()
    _build_analysis()
    _validate_analysis()


def _summary_text() -> str:
    lines = [
        "T=382 northwest_intersection baseline fork と Actual World の到着差診断",
        "系列: T=382 baseline fork / Actual 実 World / T=382〜407 の selected Candidate",
        "phase: " + ", ".join(PHASE_ORDER),
        "Actual は T=407 の処理完了後、T=408 の driver 入口で診断用 sentinel により停止した。",
        "Baseline fork 自体は停止していない。記録だけを T=394 までに限った。",
        "原因は事前に固定していない。後続 decision、spillback、clearance、entry space、進路、Vehicle 運動のどれが直接原因かは、下の各 party の未確定項目に残している。",
        "T=390 の特定 Visit は、既存確認一覧が T=392 の2件だけなので照合していない。",
        "旧 rank_and_passage_trace は production の record_order_control_node_arrival 呼出し後に"
        "同一 VisitKey の到着時刻を無条件上書きしていたため、その Actual 到着値は初回到着ではない。",
        "本診断の Actual 到着は production current_visit['arrival_time'] の初回設定値のみを記録する。",
        "",
    ]
    for report in GATE.party_reports:
        lines.append(f"## {report['vehicle_name']}:{report['visit_id']}")
        for field_name in (
            "vehicle_name",
            "visit_id",
            "inlink_name",
            "baseline_arrival_timestep",
            "actual_arrival_timestep",
            "arrival_difference_timesteps",
            "arrival_method_call_count",
            "first_arrival_call_timestep",
            "later_re_registration_call_timesteps",
            "later_calls_kept_production_arrival_time",
            "common_origin_position_baseline",
            "common_origin_position_actual",
            "common_origin_speed_baseline",
            "common_origin_speed_actual",
            "common_origin_physical_index_baseline",
            "common_origin_physical_index_actual",
            "first_divergence_timestep",
            "first_divergence_phase",
            "first_divergence_field",
            "baseline_value_at_first_divergence",
            "actual_value_at_first_divergence",
            "baseline_leader_at_first_divergence",
            "actual_leader_at_first_divergence",
            "baseline_physical_index_at_first_divergence",
            "actual_physical_index_at_first_divergence",
            "first_divergent_front_vehicle_name",
            "relevant_selected_decision_timesteps",
            "immediate_explanation",
            "remaining_uncertainty",
        ):
            lines.append(f"{field_name}: {report[field_name]}")
        for point in report["points"]:
            lines.append(point)
        lines.append("")
    return "\n".join(lines) + "\n"


def _write_outputs() -> None:
    if OUTPUT_DIR.parent.exists() is not True:
        raise RuntimeError(f"Output parent directory does not exist: {OUTPUT_DIR.parent}.")
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    vehicle_columns = [
        "world_kind",
        "world_timestep",
        "phase",
        "node_name",
        "vehicle_name",
        "vehicle_id",
        "visit_id",
        "visit_key",
        "current_link_name",
        "position_x",
        "x_old",
        "x_next",
        "speed_v",
        "move_remain",
        "lane",
        "physical_index",
        "is_physical_head",
        "leader_vehicle_name",
        "follower_vehicle_name",
        "in_incoming",
        "incoming_index",
        "state",
        "route_next_link_name",
        "assigned_rank",
        "link_vehicle_count",
        "link_capacity_out_remain",
        "node_flow_capacity_remain",
    ]
    inlink_vehicle_columns = [
        "world_kind",
        "world_timestep",
        "phase",
        "link_name",
        "vehicle_name",
        "vehicle_id",
        "position_x",
        "speed_v",
        "physical_index",
        "leader_vehicle_name",
        "follower_vehicle_name",
        "state",
        "visit_key",
        "assigned_rank",
    ]
    inlink_columns = [
        "world_kind",
        "world_timestep",
        "phase",
        "link_name",
        "vehicle_count",
        "vehicle_order",
        "position_order",
        "speed_order",
        "physical_head_vehicle_name",
        "capacity_out_remain",
        "cum_arrival_latest",
        "cum_departure_latest",
    ]
    difference_columns = [
        "subject_kind",
        "subject_name",
        "world_timestep",
        "phase",
        "field_name",
        "field_order",
        "is_first_field",
        "baseline_value",
        "actual_value",
    ]
    decision_columns = [
        "tvt_decision_timestep",
        "node_name",
        "selected",
        "selected_candidate_evaluation_index",
        "candidate_identity",
        "buyers_sorted",
        "sellers_sorted",
        "nonparticipating_visits_sorted",
        "trade_scope",
        "baseline_order",
        "candidate_order",
        "right_of_entry_visit_key",
        "k_last_buyer",
        "k_decision_window",
        "k_fixed",
        "visits_in_binding_order",
        "local_calculation_resolved",
        "local_calculation_stop_reason",
        "newly_confirmed_visit_keys",
        "newly_confirmed_assigned_ranks",
    ]
    party_columns = [
        "tvt_decision_timestep",
        "node_name",
        "selected",
        "selected_candidate_evaluation_index",
        "candidate_identity",
        "vehicle_name",
        "visit_id",
        "visit_key",
        "trade_role",
        "inlink_name",
        "in_candidate_visits",
        "in_trade_scope",
        "in_binding_sequence",
        "binding_partition",
        "baseline_order_position",
        "candidate_order_position",
        "baseline_local_rank",
        "candidate_local_rank",
        "binding_rank",
        "baseline_arrival_timestep",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "predicted_route_next_link_name",
        "buyers_sorted",
        "sellers_sorted",
        "nonparticipating_visits_sorted",
        "trade_scope",
        "baseline_order",
        "candidate_order",
        "right_of_entry_visit_key",
        "k_last_buyer",
        "k_decision_window",
        "k_fixed",
        "visits_in_binding_order",
        "local_calculation_resolved",
        "local_calculation_stop_reason",
        "newly_confirmed_by_this_decision",
        "newly_assigned_node_continuous_rank",
    ]
    confirmed_columns = [
        "tvt_decision_timestep",
        "node_name",
        "vehicle_name",
        "visit_id",
        "visit_key",
        "assigned_rank",
        "decision_selected_candidate_identity",
        "selected_candidate_evaluation_index",
        "in_selected_candidate_parties",
    ]
    front_columns = [
        "party_vehicle_name",
        "party_visit_key",
        "world_kind",
        "world_timestep",
        "phase",
        "inlink_name",
        "front_order_from_node",
        "vehicle_name",
        "physical_index",
        "position_x",
        "speed_v",
        "leader_vehicle_name",
        "state_differs_from_other_world",
        "is_first_divergent_front_vehicle",
        "actual_passage_timestep",
        "assigned_rank",
        "rank_confirmation_decision_timestep",
    ]
    _write_csv(OUTPUT_DIR / VEHICLE_SNAPSHOT_CSV, vehicle_columns, GATE.vehicle_rows)
    _write_csv(OUTPUT_DIR / INLINK_VEHICLE_SNAPSHOT_CSV, inlink_vehicle_columns, GATE.inlink_vehicle_rows)
    _write_csv(OUTPUT_DIR / INLINK_SNAPSHOT_CSV, inlink_columns, GATE.inlink_rows)
    _write_csv(OUTPUT_DIR / FIRST_DIFFERENCE_CSV, difference_columns, GATE.first_difference_rows)
    _write_csv(OUTPUT_DIR / SELECTED_DECISION_CSV, decision_columns, GATE.decision_rows)
    _write_csv(OUTPUT_DIR / SELECTED_PARTY_CSV, party_columns, GATE.party_rows)
    _write_csv(OUTPUT_DIR / NEWLY_CONFIRMED_CSV, confirmed_columns, GATE.newly_confirmed_rows)
    _write_csv(OUTPUT_DIR / FRONT_VEHICLE_CSV, front_columns, GATE.front_rows)
    arrival_call_columns = [
        "call_index",
        "world_timestep",
        "node_name",
        "vehicle_name",
        "visit_id",
        "visit_key",
        "arrival_time_before",
        "arrival_time_after",
        "formal_arrival_timestep_after",
        "was_first_recorded_call",
        "was_already_recorded_in_diagnostic",
        "diagnostic_first_arrival_timestep",
    ]
    _write_csv(OUTPUT_DIR / ARRIVAL_CALL_CSV, arrival_call_columns, GATE.actual_arrival_call_rows)
    (OUTPUT_DIR / SUMMARY_NAME).write_text(_summary_text(), encoding="utf-8")
    manifest = {
        "scenario_name": trial.SCENARIO_NAME,
        "diagnostic_script": SCRIPT_PATH.name,
        "target_node_name": TARGET_NODE_NAME,
        "target_decision_timestep": TARGET_DECISION_TIMESTEP,
        "actual_trace_end_timestep": ACTUAL_TRACE_END_TIMESTEP,
        "baseline_trace_end_timestep": BASELINE_TRACE_END_TIMESTEP,
        "phases": list(PHASE_ORDER),
        "series": ["baseline_fork", "actual_world", "selected_candidate"],
        "early_stop": "Raise _StopAfterActualT407 at real driver entry of T=408, after saving actual after_timestep of T=407.",
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "generated_files": list(OUTPUT_FILE_NAMES),
        "output_directory": str(OUTPUT_DIR),
    }
    (OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _prepare_world():
    if trial.reference.NORTHWEST_INTERSECTION != TARGET_NODE_NAME:
        raise RuntimeError("Trial northwest node name does not match northwest_intersection.")
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
    _reset_gate()
    original_limit = sys.getrecursionlimit()
    world = None
    stopped = False
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
            try:
                world.exec_simulation()
            except _StopAfterActualT407:
                stopped = True
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        if stopped is not True:
            raise RuntimeError("Actual trace did not stop after T=407.")
        if world is None:
            raise RuntimeError("Actual World is missing after the early stop.")
        _validate_runtime(world)
        _write_outputs()
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        trial.reference.restore_real_world_spillback_observation()
        restore_hooks()
        sys.setrecursionlimit(original_limit)


def _ast_label(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_label(node.value)
        if parent is None:
            return None
        return parent + "." + node.attr
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    return None


def _assignment_pairs(function_node):
    pairs = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = _ast_label(node.targets[0])
        value = _ast_label(node.value)
        if target is None or value is None:
            continue
        pairs.append((target, value))
    return pairs


def _require_assignment(pairs, target, value, label: str) -> None:
    for pair in pairs:
        if pair[0] == target and pair[1] == value:
            return
    raise RuntimeError(f"Static hook binding is missing: {label}.")


def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _restore_returns_when_not_installed(function_node) -> bool:
    if len(function_node.body) == 0:
        return False
    first = function_node.body[0]
    if not isinstance(first, ast.If):
        return False
    test = first.test
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Attribute) or test.left.attr != "installed":
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.IsNot):
        return False
    compared = test.comparators[0]
    if not isinstance(compared, ast.Constant) or compared.value is not True:
        return False
    for statement in first.body:
        if isinstance(statement, ast.Return):
            return True
    return False


def _validate_hook_install_restore(tree) -> None:
    install_node = _function_node(tree, "install_hooks")
    restore_node = _function_node(tree, "restore_hooks")
    if install_node is None or restore_node is None:
        raise RuntimeError("install_hooks or restore_hooks is missing.")
    if _restore_returns_when_not_installed(restore_node) is not True:
        raise RuntimeError("restore_hooks does not return immediately when hooks are not installed.")
    install_pairs = _assignment_pairs(install_node)
    restore_pairs = _assignment_pairs(restore_node)
    bindings = (
        (
            "baseline_driver_module._prepare_baseline_fork",
            "GATE.original_prepare",
            "wrapped_prepare_baseline_fork",
        ),
        (
            "driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
            "GATE.original_align",
            "wrapped_align_baseline",
        ),
        (
            "driver_module.run_tvt_mp_driver",
            "GATE.original_driver",
            "wrapped_driver",
        ),
        (
            "uxsim_module.Link.update",
            "GATE.original_link_update",
            "wrapped_link_update",
        ),
        (
            "uxsim_module.Node.transfer",
            "GATE.original_transfer",
            "wrapped_transfer",
        ),
        (
            "uxsim_module.Vehicle.update",
            "GATE.original_vehicle_update",
            "wrapped_vehicle_update",
        ),
        (
            "uxsim_module.Node._transfer_one_vehicle_between_links",
            "GATE.original_move",
            "wrapped_move",
        ),
        (
            "uxsim_module.Vehicle.record_order_control_node_arrival",
            "GATE.original_arrival",
            "wrapped_arrival",
        ),
    )
    for target_name, original_name, wrapper_name in bindings:
        if _function_node(tree, wrapper_name) is None:
            raise RuntimeError(f"Wrapper function {wrapper_name} is missing.")
        _require_assignment(install_pairs, original_name, target_name, f"install saves {target_name}")
        _require_assignment(install_pairs, target_name, wrapper_name, f"install patches {target_name}")
        _require_assignment(restore_pairs, target_name, original_name, f"restore writes back {target_name}")
        _require_assignment(restore_pairs, original_name, "None", f"restore clears {original_name}")


def _call_names(function_node) -> list:
    names = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
        elif isinstance(node.func, ast.Name):
            names.append(node.func.id)
    return names


def _function_calls(function_node, callee_name: str) -> bool:
    return callee_name in _call_names(function_node)


def _name_ids_in_function(function_node) -> list:
    names = []
    for node in ast.walk(function_node):
        if isinstance(node, ast.Name):
            names.append(node.id)
    return names


def _append_to_gate_party_rows(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "append":
            continue
        target = func.value
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "party_rows"
            and isinstance(target.value, ast.Name)
            and target.value.id == "GATE"
        ):
            return True
    return False


def _returns_variable(function_node, variable_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        if isinstance(node.value, ast.Name) and node.value.id == variable_name:
            return True
    return False


def _compare_tests_economic_is_none(test) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    comparator = test.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value is not None:
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != "economic":
        return False
    return isinstance(test.ops[0], ast.Is)


def _record_decision_branches_on_selected_economic(record_node) -> bool:
    if _function_calls(record_node, "_read_selected_candidate") is not True:
        return False
    if _function_calls(record_node, "_blank_selected_fields") is not True:
        return False
    for node in ast.walk(record_node):
        if not isinstance(node, ast.If):
            continue
        if _compare_tests_economic_is_none(node.test) is not True:
            continue
        body_calls = _call_names(ast.Module(body=node.body, type_ignores=[]))
        orelse_calls = _call_names(ast.Module(body=node.orelse, type_ignores=[]))
        if "_blank_selected_fields" in body_calls and "_read_selected_candidate" in orelse_calls:
            return True
        if "_read_selected_candidate" in body_calls and "_blank_selected_fields" in orelse_calls:
            return True
    return False


def _validate_selected_save_static(tree) -> None:
    record_node = _function_node(tree, "_record_decision")
    read_node = _function_node(tree, "_read_selected_candidate")
    append_node = _function_node(tree, "_append_all_selected_parties")
    index_node = _function_node(tree, "_find_one_based_evaluation_index")
    trade_node = _function_node(tree, "_find_unique_trade_result_for_buyers")
    if record_node is None:
        raise RuntimeError("_record_decision is missing.")
    if read_node is None:
        raise RuntimeError("_read_selected_candidate is missing.")
    if append_node is None:
        raise RuntimeError("_append_all_selected_parties is missing.")
    if index_node is None:
        raise RuntimeError("_find_one_based_evaluation_index is missing.")
    if trade_node is None:
        raise RuntimeError("_find_unique_trade_result_for_buyers is missing.")
    if _function_calls(record_node, "_read_selected_candidate") is not True:
        raise RuntimeError("_record_decision does not call _read_selected_candidate.")
    if _record_decision_branches_on_selected_economic(record_node) is not True:
        raise RuntimeError(
            "_record_decision does not branch on selected_candidate_economic_result "
            "between _blank_selected_fields and _read_selected_candidate."
        )
    if _function_calls(read_node, "_append_all_selected_parties") is not True:
        raise RuntimeError("_read_selected_candidate does not call _append_all_selected_parties.")
    if _function_calls(read_node, "_find_one_based_evaluation_index") is not True:
        raise RuntimeError("_read_selected_candidate does not call _find_one_based_evaluation_index.")
    if _function_calls(read_node, "_find_unique_trade_result_for_buyers") is not True:
        raise RuntimeError(
            "_read_selected_candidate does not call _find_unique_trade_result_for_buyers."
        )
    append_names = _name_ids_in_function(append_node)
    if "TARGET_PARTIES" in append_names:
        raise RuntimeError("Selected party save filters visits with the four target parties.")
    for name in append_names:
        if "related" in name:
            raise RuntimeError("Selected party save uses a related-vehicle filter.")
    if _append_to_gate_party_rows(append_node) is not True:
        raise RuntimeError("_append_all_selected_parties does not append to GATE.party_rows.")
    if _returns_variable(append_node, "saved_keys") is not True:
        raise RuntimeError("_append_all_selected_parties does not return saved_keys.")
    trade_source = ast.get_source_segment(SCRIPT_PATH.read_text(encoding="utf-8"), trade_node)
    if trade_source is None:
        raise RuntimeError("Unique trade-rank helper source is unavailable.")
    if "found = None" not in trade_source:
        raise RuntimeError("Unique trade-rank helper does not start from no match.")
    if "if found is not None:" not in trade_source:
        raise RuntimeError("Unique trade-rank helper does not stop on a second match.")
    if "if found is None:" not in trade_source:
        raise RuntimeError("Unique trade-rank helper does not stop when no match exists.")
    if "return found" not in trade_source:
        raise RuntimeError("Unique trade-rank helper does not return the one match.")


def _dict_literal_keys(node) -> list:
    keys = []
    if not isinstance(node, ast.Dict):
        return keys
    for key_node in node.keys:
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            keys.append(key_node.value)
    return keys


def _known_later_confirmations_from_ast(tree) -> dict:
    entries = {}
    for body_node in tree.body:
        if not isinstance(body_node, ast.Assign):
            continue
        matched = False
        for target in body_node.targets:
            if isinstance(target, ast.Name) and target.id == "KNOWN_LATER_CONFIRMATIONS":
                matched = True
        if matched is not True:
            continue
        if not isinstance(body_node.value, ast.Tuple):
            raise RuntimeError("KNOWN_LATER_CONFIRMATIONS is not a tuple literal.")
        for element in body_node.value.elts:
            if not isinstance(element, ast.Dict):
                raise RuntimeError("KNOWN_LATER_CONFIRMATIONS entry is not a dict literal.")
            record = {}
            for key_node, value_node in zip(element.keys, element.values):
                if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                    raise RuntimeError("KNOWN_LATER_CONFIRMATIONS dict key is not a string constant.")
                field_name = key_node.value
                if not isinstance(value_node, ast.Constant):
                    raise RuntimeError(
                        f"KNOWN_LATER_CONFIRMATIONS[{field_name!r}] is not a constant."
                    )
                record[field_name] = value_node.value
            vehicle_name = record.get("vehicle_name")
            visit_id = record.get("visit_id")
            if not isinstance(vehicle_name, str) or vehicle_name == "":
                raise RuntimeError("KNOWN_LATER_CONFIRMATIONS entry vehicle_name is invalid.")
            if type(visit_id) is not int or type(visit_id) is bool:
                raise RuntimeError("KNOWN_LATER_CONFIRMATIONS entry visit_id is invalid.")
            entries[(vehicle_name, visit_id)] = record
    if len(entries) == 0:
        raise RuntimeError("KNOWN_LATER_CONFIRMATIONS is missing from module AST.")
    return entries


def _validate_known_later_confirmations_static(tree) -> None:
    entries = _known_later_confirmations_from_ast(tree)
    expected_by_visit = {
        ("veh_sw_nw_base_039", 2): {
            "decision_timestep": 392,
            "assigned_rank": 183,
            "actual_passage_timestep": 402,
        },
        ("veh_wn_en_base_025", 1): {
            "decision_timestep": 392,
            "assigned_rank": 179,
            "actual_passage_timestep": 406,
        },
    }
    for visit_key, expected_fields in expected_by_visit.items():
        if visit_key not in entries:
            raise RuntimeError(
                f"KNOWN_LATER_CONFIRMATIONS missing {_visit_text(visit_key[0], visit_key[1])}."
            )
        record = entries[visit_key]
        if "actual_node_passage_rank" in record:
            raise RuntimeError(
                "KNOWN_LATER_CONFIRMATIONS must not define actual_node_passage_rank."
            )
        for field_name, expected_value in expected_fields.items():
            actual_value = record.get(field_name)
            if actual_value != expected_value:
                raise RuntimeError(
                    f"KNOWN_LATER_CONFIRMATIONS {_visit_text(visit_key[0], visit_key[1])} "
                    f"{field_name} is {actual_value!r}, not {expected_value!r}."
                )
    for visit_key, record in entries.items():
        if "actual_node_passage_rank" in record:
            raise RuntimeError(
                f"KNOWN_LATER_CONFIRMATIONS {_visit_text(visit_key[0], visit_key[1])} "
                "defines actual_node_passage_rank."
            )


def _validate_target_parties_no_fixed_actual_arrivals(tree) -> None:
    for body_node in tree.body:
        if not isinstance(body_node, ast.Assign):
            continue
        matched = False
        for target in body_node.targets:
            if isinstance(target, ast.Name) and target.id == "TARGET_PARTIES":
                matched = True
        if matched is not True:
            continue
        for dict_node in ast.walk(body_node.value):
            for key_name in _dict_literal_keys(dict_node):
                if key_name in ("actual_arrival_timestep", "arrival_difference_timesteps"):
                    raise RuntimeError(
                        f"TARGET_PARTIES still defines fixed {key_name!r}."
                    )


def _function_uses_subscript_key(function_node, container_name: str, key_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Subscript):
            continue
        key = node.slice
        if isinstance(key, ast.Constant) and key.value == key_name:
            if isinstance(node.value, ast.Name) and node.value.id == container_name:
                return True
    return False


def _call_is_dict_get_on_name(call_node, variable_name: str, key_name: str) -> bool:
    if not isinstance(call_node, ast.Call):
        return False
    func = call_node.func
    if not isinstance(func, ast.Attribute) or func.attr != "get":
        return False
    if not isinstance(func.value, ast.Name) or func.value.id != variable_name:
        return False
    if len(call_node.args) < 1:
        return False
    first_arg = call_node.args[0]
    if not isinstance(first_arg, ast.Constant):
        return False
    return first_arg.value == key_name


def _function_calls_dict_get_key(function_node, variable_name: str, key_name: str) -> bool:
    for node in ast.walk(function_node):
        if _call_is_dict_get_on_name(node, variable_name, key_name) is True:
            return True
    return False


def _dict_get_call_linenos(function_node, variable_name: str, key_name: str) -> list:
    lines = []
    for node in ast.walk(function_node):
        if _call_is_dict_get_on_name(node, variable_name, key_name) is not True:
            continue
        lines.append(node.lineno)
    return lines


def _original_arrival_call_lineno(function_node) -> int | None:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "original_arrival":
            return node.lineno
    return None


def _assign_target_lineno(function_node, target_name: str) -> int | None:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == target_name:
                return node.lineno
    return None


def _is_gate_attribute(node, owner_name: str, attribute_name: str) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr != attribute_name:
        return False
    if not isinstance(node.value, ast.Name):
        return False
    return node.value.id == owner_name


def _is_gate_actual_arrivals_attribute(node) -> bool:
    return _is_gate_attribute(node, "GATE", "actual_arrivals")


def _function_uses_attribute(function_node, owner_name: str, attribute_name: str) -> bool:
    for node in ast.walk(function_node):
        if _is_gate_attribute(node, owner_name, attribute_name) is True:
            return True
    return False


def _is_gate_actual_arrivals_subscript(node) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    return _is_gate_actual_arrivals_attribute(node.value)


def _function_uses_gate_actual_arrivals_in_membership(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Compare):
            continue
        has_in = False
        for op in node.ops:
            if isinstance(op, ast.In):
                has_in = True
        if has_in is not True:
            continue
        for comparator in node.comparators:
            if _is_gate_actual_arrivals_attribute(comparator):
                return True
    return False


def _function_assigns_gate_actual_arrivals_entry(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if _is_gate_actual_arrivals_subscript(target):
                return True
    return False


def _function_loads_gate_actual_arrivals_entry(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        if _is_gate_actual_arrivals_subscript(node.value):
            return True
    return False


def _function_subscripts_party_key(function_node, key_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != "party":
            continue
        if isinstance(node.slice, ast.Constant) and node.slice.value == key_name:
            return True
    return False


def _count_original_arrival_calls(function_node) -> int:
    count = 0
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "original_arrival":
            count = count + 1
    return count


def _is_party_vehicle_name_subscript(node) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name) or node.value.id != "party":
        return False
    if isinstance(node.slice, ast.Constant) and node.slice.value == "vehicle_name":
        return True
    return False


def _is_gate_party_arrival_by_vehicle_party_key_subscript(node) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if _is_gate_attribute(node.value, "GATE", "party_arrival_by_vehicle") is not True:
        return False
    return _is_party_vehicle_name_subscript(node.slice)


def _function_assigns_arrival_info_from_gate_party_arrivals(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != "arrival_info":
                continue
            if _is_gate_party_arrival_by_vehicle_party_key_subscript(node.value) is True:
                return True
    return False


def _function_reads_name_subscript_key(function_node, container_name: str, key_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != container_name:
            continue
        if isinstance(node.slice, ast.Constant) and node.slice.value == key_name:
            return True
    return False


def _function_writes_gate_party_arrival_by_vehicle(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if _is_gate_party_arrival_by_vehicle_party_key_subscript(target) is True:
                return True
    return False


def _function_appends_gate_attribute(function_node, owner_name: str, attribute_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "append":
            continue
        if _is_gate_attribute(func.value, owner_name, attribute_name) is not True:
            continue
        return True
    return False


def _validate_build_analysis_arrival_connection_static(build_node) -> None:
    if _function_uses_attribute(build_node, "GATE", "party_arrival_by_vehicle") is not True:
        raise RuntimeError("_build_analysis does not use GATE.party_arrival_by_vehicle.")
    if _function_subscripts_party_key(build_node, "vehicle_name") is not True:
        raise RuntimeError("_build_analysis does not index party by vehicle_name.")
    if _function_assigns_arrival_info_from_gate_party_arrivals(build_node) is not True:
        raise RuntimeError(
            "_build_analysis does not assign arrival_info from GATE.party_arrival_by_vehicle."
        )
    for key_name in (
        "baseline_arrival_timestep",
        "actual_arrival_timestep",
        "arrival_difference_timesteps",
    ):
        if _function_reads_name_subscript_key(build_node, "arrival_info", key_name) is not True:
            raise RuntimeError(f"_build_analysis does not read arrival_info[{key_name!r}].")
    if _function_subscripts_party_key(build_node, "actual_arrival_timestep") is True:
        raise RuntimeError("_build_analysis reads fixed actual_arrival_timestep from TARGET_PARTIES.")


def _write_outputs_writes_arrival_call_csv(write_node) -> bool:
    for node in ast.walk(write_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "_write_csv":
            continue
        for arg in node.args:
            if not isinstance(arg, ast.BinOp) or not isinstance(arg.op, ast.Div):
                continue
            if isinstance(arg.right, ast.Name) and arg.right.id == "ARRIVAL_CALL_CSV":
                return True
    return False


def _validate_arrival_recording_static(tree) -> None:
    _validate_target_parties_no_fixed_actual_arrivals(tree)
    wrapped_node = _function_node(tree, "wrapped_arrival")
    validate_arrivals_node = _function_node(tree, "_validate_formal_arrivals")
    build_node = _function_node(tree, "_build_analysis")
    write_node = _function_node(tree, "_write_outputs")
    if wrapped_node is None or validate_arrivals_node is None or build_node is None:
        raise RuntimeError("Arrival recording functions are missing.")
    if _count_original_arrival_calls(wrapped_node) != 1:
        raise RuntimeError("wrapped_arrival must call GATE.original_arrival exactly once.")
    if _function_calls(wrapped_node, "_append_actual_arrival_call_row") is not True:
        raise RuntimeError("wrapped_arrival does not append arrival call audit rows.")
    uses_arrival_time_subscript = _function_uses_subscript_key(
        wrapped_node,
        "current_visit",
        "arrival_time",
    )
    uses_arrival_time_get = _function_calls_dict_get_key(
        wrapped_node,
        "current_visit",
        "arrival_time",
    )
    if uses_arrival_time_subscript is not True and uses_arrival_time_get is not True:
        raise RuntimeError("wrapped_arrival does not read current_visit arrival_time.")
    original_line = _original_arrival_call_lineno(wrapped_node)
    if original_line is None:
        raise RuntimeError("wrapped_arrival original_arrival call line is missing.")
    current_visit_line = _assign_target_lineno(wrapped_node, "current_visit")
    if current_visit_line is None or current_visit_line <= original_line:
        raise RuntimeError(
            "wrapped_arrival must assign current_visit after GATE.original_arrival."
        )
    post_original_get_lines = []
    for line_number in _dict_get_call_linenos(wrapped_node, "current_visit", "arrival_time"):
        if line_number > original_line:
            post_original_get_lines.append(line_number)
    if len(post_original_get_lines) == 0 and uses_arrival_time_subscript is not True:
        raise RuntimeError(
            "wrapped_arrival must read current_visit arrival_time after GATE.original_arrival."
        )
    if uses_arrival_time_subscript is True:
        for node in ast.walk(wrapped_node):
            if not isinstance(node, ast.Subscript):
                continue
            if not isinstance(node.value, ast.Name) or node.value.id != "current_visit":
                continue
            if not isinstance(node.slice, ast.Constant) or node.slice.value != "arrival_time":
                continue
            if node.lineno <= original_line:
                continue
            post_original_get_lines.append(node.lineno)
    if len(post_original_get_lines) == 0:
        raise RuntimeError(
            "wrapped_arrival must read current_visit arrival_time after GATE.original_arrival."
        )
    arrival_time_after_line = _assign_target_lineno(wrapped_node, "arrival_time_after")
    if arrival_time_after_line is not None and arrival_time_after_line <= original_line:
        raise RuntimeError(
            "wrapped_arrival arrival_time_after must be read after GATE.original_arrival."
        )
    wrapped_names = _name_ids_in_function(wrapped_node)
    if "was_already_recorded_in_diagnostic" not in wrapped_names:
        raise RuntimeError("wrapped_arrival does not guard against overwriting recorded arrivals.")
    if _function_uses_attribute(wrapped_node, "GATE", "actual_arrivals") is not True:
        raise RuntimeError("wrapped_arrival does not use GATE.actual_arrivals.")
    if _function_uses_gate_actual_arrivals_in_membership(wrapped_node) is not True:
        raise RuntimeError("wrapped_arrival does not test key in GATE.actual_arrivals.")
    if _function_assigns_gate_actual_arrivals_entry(wrapped_node) is not True:
        raise RuntimeError("wrapped_arrival does not assign GATE.actual_arrivals[key].")
    if _function_loads_gate_actual_arrivals_entry(wrapped_node) is not True:
        raise RuntimeError("wrapped_arrival does not read GATE.actual_arrivals[key].")
    if _function_subscripts_party_key(validate_arrivals_node, "actual_arrival_timestep") is True:
        raise RuntimeError("_validate_formal_arrivals compares fixed actual_arrival_timestep.")
    if _function_subscripts_party_key(validate_arrivals_node, "arrival_difference_timesteps") is True:
        raise RuntimeError("_validate_formal_arrivals compares fixed arrival_difference_timesteps.")
    if _function_uses_attribute(validate_arrivals_node, "GATE", "party_arrival_by_vehicle") is not True:
        raise RuntimeError("_validate_formal_arrivals does not use GATE.party_arrival_by_vehicle.")
    if _function_writes_gate_party_arrival_by_vehicle(validate_arrivals_node) is not True:
        raise RuntimeError("_validate_formal_arrivals does not populate GATE.party_arrival_by_vehicle.")
    append_row_node = _function_node(tree, "_append_actual_arrival_call_row")
    if append_row_node is None:
        raise RuntimeError("_append_actual_arrival_call_row is missing.")
    if _function_appends_gate_attribute(append_row_node, "GATE", "actual_arrival_call_rows") is not True:
        raise RuntimeError("_append_actual_arrival_call_row does not append to GATE.actual_arrival_call_rows.")
    _validate_build_analysis_arrival_connection_static(build_node)
    output_names = []
    for body_node in tree.body:
        if not isinstance(body_node, ast.Assign):
            continue
        for target in body_node.targets:
            if isinstance(target, ast.Name) and target.id == "OUTPUT_FILE_NAMES":
                for element in body_node.value.elts:
                    if isinstance(element, ast.Name):
                        output_names.append(element.id)
    if "ARRIVAL_CALL_CSV" not in output_names:
        raise RuntimeError("OUTPUT_FILE_NAMES does not list ARRIVAL_CALL_CSV.")
    if write_node is None:
        raise RuntimeError("_write_outputs is missing.")
    if _write_outputs_writes_arrival_call_csv(write_node) is not True:
        raise RuntimeError("_write_outputs does not write ARRIVAL_CALL_CSV.")


def _validate_main_stop(tree) -> None:
    main_node = _function_node(tree, "main")
    if main_node is None:
        raise RuntimeError("main is missing.")
    saw_sentinel = False
    for node in ast.walk(main_node):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            raise RuntimeError("main has a bare except.")
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            raise RuntimeError("main catches Exception.")
        if isinstance(node.type, ast.Name) and node.type.id == "_StopAfterActualT407":
            saw_sentinel = True
    if saw_sentinel is not True:
        raise RuntimeError("main does not catch _StopAfterActualT407.")


def _module_constants(tree):
    strings = set()
    integers = set()
    for body_node in tree.body:
        if isinstance(body_node, ast.Assign):
            value_root = body_node.value
        elif isinstance(body_node, ast.AnnAssign) and body_node.value is not None:
            value_root = body_node.value
        else:
            continue
        for subnode in ast.walk(value_root):
            if not isinstance(subnode, ast.Constant):
                continue
            if isinstance(subnode.value, str):
                strings.add(subnode.value)
            if type(subnode.value) is int and type(subnode.value) is not bool:
                integers.add(subnode.value)
    return strings, integers


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory equals the trial output directory.")
    strings, integers = _module_constants(tree)
    required_strings = [
        TARGET_NODE_NAME,
        "veh_sw_nw_base_037",
        "veh_nw_sw_base_047",
        "veh_wn_se_base_024",
        "veh_en_sw_base_025",
        INLINK_SOUTHWEST_TO_NORTHWEST,
        INLINK_NORTH_WEST_OD_TO_NORTHWEST,
        INLINK_WEST_NORTH_OD_TO_NORTHWEST,
        INLINK_NORTHEAST_TO_NORTHWEST,
    ]
    for text in required_strings:
        if text not in strings:
            raise RuntimeError(f"Module-level constants do not include {text!r}.")
    if TARGET_DECISION_TIMESTEP not in integers:
        raise RuntimeError("Module-level constants do not include T=382.")
    forbidden_t600_module_strings = (
        "veh_ne_wn_base_032",
        "veh_ne_wn_base_034",
        "veh_wn_en_base_042",
        "northeast_intersection_to_southeast_intersection",
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_t600_candidate_actual_paired_trace",
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_t600_baseline_actual_route_choice_trace",
    )
    for forbidden in forbidden_t600_module_strings:
        for text in strings:
            if forbidden in text:
                raise RuntimeError(f"This diagnostic embeds a T=600 module constant: {forbidden!r}.")
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
    for name in ("system", "rmtree", "unlink", "rmdir"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
    forbidden_calls = (
        "_order_control_clearance_blocks_passage",
        "_first_ordinary_physical_shortage",
        "route_next_link_choice",
    )
    for name in forbidden_calls:
        if name in called:
            raise RuntimeError(f"Diagnostic calls production judgment {name}.")
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    for module_name in imported:
        if module_name in ("subprocess", "shutil", "git"):
            raise RuntimeError(f"Diagnostic imports {module_name}.")
    static_function = _function_node(tree, "validate_static_contract")
    if static_function is None:
        raise RuntimeError("validate_static_contract is missing.")
    for node in ast.walk(static_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "install_hooks", "restore_hooks", "mkdir"):
                raise RuntimeError("Static validation runs the simulation, hooks, or mkdir.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("install_hooks", "restore_hooks", "exec_simulation"):
                raise RuntimeError("Static validation runs the simulation or hooks.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
    sentinel = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "_StopAfterActualT407":
            sentinel = node
    if sentinel is None:
        raise RuntimeError("Diagnostic sentinel exception is missing.")
    _validate_hook_install_restore(tree)
    _validate_selected_save_static(tree)
    _validate_arrival_recording_static(tree)
    _validate_known_later_confirmations_static(tree)
    _validate_main_stop(tree)
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
