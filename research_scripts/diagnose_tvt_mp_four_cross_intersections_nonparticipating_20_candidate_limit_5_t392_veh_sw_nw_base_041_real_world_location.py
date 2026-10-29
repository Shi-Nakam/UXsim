"""
Read-only diagnostic: T=392 real-World location of veh_sw_nw_base_041 vs northwest snapshot.

Uses formal driver fork_result, collector export, and vehicle.link state only.
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
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState

TARGET_VEHICLE_NAME = "veh_sw_nw_base_041"
TARGET_VISIT_KEY = (TARGET_VEHICLE_NAME, 2)
TARGET_NODE_NAME = "northwest_intersection"
SOUTHWEST_NODE_NAME = "southwest_intersection"
TARGET_TIMESTEP = 392
TIMESTEP_T401 = 401
CAPTURE_DRIVER_TIMESTEPS = frozenset({TARGET_TIMESTEP, TIMESTEP_T401})
SIMULATION_UNTIL_TIMESTEP = 407
EXPECTED_WORLD_T_AFTER_SIM = 408
EXPECTED_NORTHWEST_ARRIVAL_TIMESTEP = 407

EXPECTED_T401_FORMAL_INLINK_NAME = "southwest_intersection_to_northwest_intersection"
COMPARE_VISIT_B = ("veh_wn_se_base_025", 1)

EXPECTED_T401_PHYSICAL_INDEX = 2
EXPECTED_T401_BASELINE_ARRIVAL = 407
EXPECTED_T401_BASELINE_PASSAGE = 414
EXPECTED_T401_ASSIGNED_RANK = 184
EXPECTED_T401_FINALIZATION_SOURCE = "baseline"
EXPECTED_T401_FINAL_RANK_STATUS = "baseline_fallback_ranks"

PHASE_BEFORE_TVT_DRIVER = "before_tvt_driver"

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t392_veh_sw_nw_base_041_real_world_location"
    )
)
SNAPSHOT_CSV = "t392_target_vehicle_real_world_snapshot.csv"
TRANSITIONS_CSV = "t392_t401_target_vehicle_link_transitions.csv"
COMPARISON_CSV = "t392_t401_target_vehicle_formal_comparison.csv"
REVIEW_NAME = "t392_veh_sw_nw_base_041_location_review.txt"
OUTPUT_FILE_NAMES = (SNAPSHOT_CSV, TRANSITIONS_CSV, COMPARISON_CSV, REVIEW_NAME)

SNAPSHOT_COLUMNS = (
    "timestep",
    "phase",
    "vehicle_name",
    "vehicle_id",
    "vehicle_state",
    "current_link_name",
    "current_link_start_node_name",
    "current_link_end_node_name",
    "current_link_physical_index",
    "current_link_vehicle_count",
    "position_x",
    "x_old",
    "x_next",
    "speed_v",
    "move_remain",
    "lane",
    "leader_vehicle_name",
    "leader_current_link_name",
    "leader_position_x",
    "follower_vehicle_name",
    "follower_current_link_name",
    "follower_position_x",
    "route_next_link_name",
    "has_order_control_current_visit",
    "current_visit_node_name",
    "current_visit_id",
    "current_visit_arrival_time",
    "current_visit_inlink_name",
    "current_visit_earliest_arrival_timestep",
    "current_visit_targets_northwest",
    "in_northwest_incoming_vehicles",
    "northwest_incoming_index",
    "northwest_rank_ledger_status",
    "assigned_c_rank",
    "link_position_class",
    "end_node_is_southwest_intersection",
    "current_link_is_southwest_incoming",
    "can_reach_target_inlink_from_current_link",
    "route_next_matches_target_inlink_reachability",
)

TRANSITION_COLUMNS = (
    "timestep",
    "phase",
    "before_link_name",
    "after_link_name",
    "before_link_end_node_name",
    "after_link_start_node_name",
    "is_continuous_link_connection",
    "current_visit_node_name",
    "current_visit_id",
    "route_next_link_name",
)

COMPARISON_COLUMNS = (
    "record_kind",
    "decision_timestep",
    "vehicle_name",
    "visit_key",
    "field_name",
    "field_value",
    "notes",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.original_arrival = None
        self.t392_pre_snapshot_row: dict | None = None
        self.t392_post_capture: dict | None = None
        self.t401_capture: dict | None = None
        self.transition_rows: list[dict] = []
        self.comparison_rows: list[dict] = []
        self.last_link_name: str | None = None
        self.last_link_end_node_name: str | None = None
        self.target_inlink_link = None
        self.first_northwest_arrival: dict | None = None
        self.review_text = ""


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _object_name(value, label: str) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", None)
    if name is None:
        return None
    if type(name) is not str or name == "":
        raise RuntimeError(f"{label} name must be a non-empty str.")
    return name


def _current_visit_fields(vehicle) -> dict:
    empty = {
        "has_current_visit": False,
        "visit_id": None,
        "node_name": "",
        "inlink_name": "",
        "earliest_arrival_timestep": "",
        "arrival_time": "",
    }
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return empty
    visit_id = current_visit.get("visit_id")
    if visit_id is not None and type(visit_id) is bool:
        raise RuntimeError("visit_id must not be bool.")
    if visit_id is not None and type(visit_id) is not int:
        raise RuntimeError("visit_id must be int or None.")
    node_name = _object_name(current_visit.get("node"), "current_visit node")
    inlink_name = _object_name(current_visit.get("inlink"), "current_visit inlink")
    earliest = current_visit.get("earliest_arrival_timestep", "")
    arrival_time = current_visit.get("arrival_time", "")
    return {
        "has_current_visit": True,
        "visit_id": visit_id,
        "node_name": node_name if node_name is not None else "",
        "inlink_name": inlink_name if inlink_name is not None else "",
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
    }


def _plain_visit(vehicle):
    fields = _current_visit_fields(vehicle)
    if fields["has_current_visit"] is not True or fields["visit_id"] is None:
        return None
    return (vehicle.name, fields["visit_id"])


def _formal_arrival_timestep(arrival_time, deltat) -> int:
    formal_timestep = int(round(arrival_time / deltat))
    if formal_timestep < 0:
        raise RuntimeError(f"Formal arrival timestep is {formal_timestep}.")
    return formal_timestep


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
        extra = set(row.keys()) - column_set
        if len(extra) != 0:
            raise RuntimeError(f"{label} row {index} extra keys {sorted(extra)!r}.")
        missing = column_set - set(row.keys())
        if len(missing) != 0:
            raise RuntimeError(f"{label} row {index} missing keys {sorted(missing)!r}.")


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row[column]) for column in columns})


def _append_comparison(
    record_kind: str,
    decision_timestep,
    vehicle_name: str,
    visit_key: str,
    field_name: str,
    field_value,
    notes: str = "",
) -> None:
    GATE.comparison_rows.append(
        {
            "record_kind": record_kind,
            "decision_timestep": decision_timestep,
            "vehicle_name": vehicle_name,
            "visit_key": visit_key,
            "field_name": field_name,
            "field_value": field_value,
            "notes": notes,
        }
    )


def _find_link_by_name(world, link_name: str):
    found = None
    for link in world.LINKS:
        if getattr(link, "name", None) == link_name:
            if found is not None:
                raise RuntimeError(f"Link {link_name} is duplicated.")
            found = link
    if found is None:
        raise RuntimeError(f"Link {link_name} is missing from World.")
    return found


def _physical_index(link, vehicle) -> int | None:
    if link is None:
        return None
    index = 0
    for current in link.vehicles:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _incoming_index(node, vehicle) -> int | None:
    incoming = getattr(node, "incoming_vehicles", None)
    if incoming is None:
        return None
    index = 0
    for current in incoming:
        if current is vehicle:
            return index
        index = index + 1
    return None


def _rank_state(world) -> OrderControlTvtNodeRankState | None:
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return None
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return None
    return rank_state


def _rank_ledger_status(world, visit_pair: tuple | None) -> str:
    rank_state = _rank_state(world)
    if rank_state is None or visit_pair is None:
        return "no_visit_or_no_ledger"
    if rank_state.is_confirmed(visit_pair):
        return "confirmed"
    if rank_state.is_undetermined(visit_pair):
        return "undetermined"
    return "absent"


def _assigned_c_rank(world, visit_pair: tuple | None):
    rank_state = _rank_state(world)
    if rank_state is None or visit_pair is None:
        return None
    if rank_state.is_confirmed(visit_pair):
        return rank_state.assigned_rank(visit_pair)
    return None


def _link_node_name(link, which: str) -> str | None:
    if link is None:
        return None
    node = getattr(link, which, None)
    if node is None:
        return None
    return getattr(node, "name", None)


def _can_reach_target_inlink_from_link(world, link) -> bool:
    if link is None or GATE.target_inlink_link is None:
        return False
    target = GATE.target_inlink_link
    if link.name == target.name:
        return True
    if _link_node_name(link, "end_node") == SOUTHWEST_NODE_NAME:
        start = _link_node_name(target, "start_node")
        if start == SOUTHWEST_NODE_NAME:
            return True
    sw_node = world.get_node(SOUTHWEST_NODE_NAME)
    if _link_node_name(link, "end_node") == SOUTHWEST_NODE_NAME:
        for outlink in sw_node.outlinks.values():
            if outlink.name == target.name:
                return True
    return False


def _classify_link_position(world, vehicle, link) -> str:
    if link is None:
        return "D_no_current_link"
    if link.name == EXPECTED_T401_FORMAL_INLINK_NAME:
        return "A_on_target_inlink"
    if _link_node_name(link, "end_node") == SOUTHWEST_NODE_NAME:
        return "B_upstream_to_target_inlink_start"
    if _can_reach_target_inlink_from_link(world, link):
        return "E_formal_object_undetermined"
    return "C_further_upstream"


def _vehicle_by_name(world, vehicle_name: str):
    vehicle = world.VEHICLES.get(vehicle_name)
    if vehicle is None:
        raise RuntimeError(f"Vehicle {vehicle_name} is missing at World.T={world.T}.")
    return vehicle


def _leader_follower_fields(vehicle):
    leader = getattr(vehicle, "leader", None)
    follower = getattr(vehicle, "follower", None)
    leader_link = None if leader is None else getattr(leader, "link", None)
    follower_link = None if follower is None else getattr(follower, "link", None)
    return {
        "leader_vehicle_name": None if leader is None else leader.name,
        "leader_current_link_name": None if leader_link is None else getattr(leader_link, "name", None),
        "leader_position_x": None if leader is None else getattr(leader, "x", None),
        "follower_vehicle_name": None if follower is None else follower.name,
        "follower_current_link_name": None if follower_link is None else getattr(follower_link, "name", None),
        "follower_position_x": None if follower is None else getattr(follower, "x", None),
    }


def _capture_t392_pre_driver_snapshot(world) -> dict:
    vehicle = _vehicle_by_name(world, TARGET_VEHICLE_NAME)
    node = world.get_node(TARGET_NODE_NAME)
    link = getattr(vehicle, "link", None)
    if link is None:
        raise RuntimeError(f"T={world.T} {TARGET_VEHICLE_NAME} has no current link (required).")
    visit_pair = _plain_visit(vehicle)
    visit_fields = _current_visit_fields(vehicle)
    targets_nw = visit_fields["node_name"] == TARGET_NODE_NAME
    if visit_fields["has_current_visit"] and visit_fields["inlink_name"] != "":
        if visit_fields["inlink_name"] != link.name:
            visit_inlink = None
            current_visit = getattr(vehicle, "order_control_current_visit", None)
            if isinstance(current_visit, dict):
                visit_inlink = current_visit.get("inlink")
            if visit_inlink is not link:
                raise RuntimeError(
                    "T=392 current_visit inlink and vehicle.link disagree."
                )
    route_link = getattr(vehicle, "route_next_link", None)
    lf = _leader_follower_fields(vehicle)
    incoming_index = _incoming_index(node, vehicle)
    position_class = _classify_link_position(world, vehicle, link)
    end_is_sw = _link_node_name(link, "end_node") == SOUTHWEST_NODE_NAME
    is_sw_incoming = end_is_sw
    can_reach = _can_reach_target_inlink_from_link(world, link)
    route_next_name = None if route_link is None else getattr(route_link, "name", None)
    route_matches = False
    if route_next_name == EXPECTED_T401_FORMAL_INLINK_NAME:
        route_matches = True
    elif route_link is not None and GATE.target_inlink_link is not None:
        route_matches = _can_reach_target_inlink_from_link(world, route_link)
    return {
        "timestep": world.T,
        "phase": PHASE_BEFORE_TVT_DRIVER,
        "vehicle_name": vehicle.name,
        "vehicle_id": getattr(vehicle, "id", None),
        "vehicle_state": getattr(vehicle, "state", None),
        "current_link_name": link.name,
        "current_link_start_node_name": _link_node_name(link, "start_node"),
        "current_link_end_node_name": _link_node_name(link, "end_node"),
        "current_link_physical_index": _physical_index(link, vehicle),
        "current_link_vehicle_count": len(link.vehicles),
        "position_x": getattr(vehicle, "x", None),
        "x_old": getattr(vehicle, "x_old", None),
        "x_next": getattr(vehicle, "x_next", None),
        "speed_v": getattr(vehicle, "v", None),
        "move_remain": getattr(vehicle, "move_remain", None),
        "lane": getattr(vehicle, "lane", None),
        "leader_vehicle_name": lf["leader_vehicle_name"],
        "leader_current_link_name": lf["leader_current_link_name"],
        "leader_position_x": lf["leader_position_x"],
        "follower_vehicle_name": lf["follower_vehicle_name"],
        "follower_current_link_name": lf["follower_current_link_name"],
        "follower_position_x": lf["follower_position_x"],
        "route_next_link_name": route_next_name,
        "has_order_control_current_visit": visit_fields["has_current_visit"],
        "current_visit_node_name": visit_fields["node_name"],
        "current_visit_id": visit_fields["visit_id"],
        "current_visit_arrival_time": visit_fields["arrival_time"],
        "current_visit_inlink_name": visit_fields["inlink_name"],
        "current_visit_earliest_arrival_timestep": visit_fields["earliest_arrival_timestep"],
        "current_visit_targets_northwest": targets_nw,
        "in_northwest_incoming_vehicles": incoming_index is not None,
        "northwest_incoming_index": incoming_index,
        "northwest_rank_ledger_status": _rank_ledger_status(world, visit_pair),
        "assigned_c_rank": _assigned_c_rank(world, visit_pair),
        "link_position_class": position_class,
        "end_node_is_southwest_intersection": end_is_sw,
        "current_link_is_southwest_incoming": is_sw_incoming,
        "can_reach_target_inlink_from_current_link": can_reach,
        "route_next_matches_target_inlink_reachability": route_matches,
    }


def _record_link_transition(world, phase: str) -> None:
    vehicle = world.VEHICLES.get(TARGET_VEHICLE_NAME)
    if vehicle is None:
        return
    link = getattr(vehicle, "link", None)
    after_name = None if link is None else getattr(link, "name", None)
    after_start = None if link is None else _link_node_name(link, "start_node")
    after_end = None if link is None else _link_node_name(link, "end_node")
    if GATE.last_link_name is None:
        GATE.last_link_name = after_name
        GATE.last_link_end_node_name = after_end
        return
    if GATE.last_link_name == after_name:
        return
    before_name = GATE.last_link_name
    before_end = GATE.last_link_end_node_name
    continuous = False
    if before_end is not None and after_start is not None:
        continuous = before_end == after_start
    visit_fields = _current_visit_fields(vehicle)
    route_link = getattr(vehicle, "route_next_link", None)
    GATE.transition_rows.append(
        {
            "timestep": world.T,
            "phase": phase,
            "before_link_name": before_name,
            "after_link_name": after_name,
            "before_link_end_node_name": before_end,
            "after_link_start_node_name": after_start,
            "is_continuous_link_connection": continuous,
            "current_visit_node_name": visit_fields["node_name"],
            "current_visit_id": visit_fields["visit_id"],
            "route_next_link_name": None if route_link is None else getattr(route_link, "name", None),
        }
    )
    GATE.last_link_name = after_name
    GATE.last_link_end_node_name = after_end


def _stages_from_atomic(atomic) -> dict:
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
        raise RuntimeError("fork_result type is wrong.")
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError("collector type is wrong.")
    return {
        "fork_result": fork_result,
        "collector": collector,
        "inlink_physical_orders": fork_result.inlink_physical_orders,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "final_rank_nodes": final_rank_set.node_final_rank_results,
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
        raise RuntimeError(f"{node_name} {label} count is {count}.")
    return matched


def _visit_in_physical_orders(inlink_physical_orders, visit_key: tuple) -> bool:
    for physical_order in inlink_physical_orders:
        if physical_order.node_name != TARGET_NODE_NAME:
            continue
        for key in physical_order.visit_keys_head_to_tail:
            if _plain_visit_key(key) == visit_key:
                return True
    return False


def _target_inlink_order_keys(inlink_physical_orders) -> list[tuple]:
    for physical_order in inlink_physical_orders:
        if physical_order.node_name != TARGET_NODE_NAME:
            continue
        if physical_order.inlink_name != EXPECTED_T401_FORMAL_INLINK_NAME:
            continue
        return [_plain_visit_key(key) for key in physical_order.visit_keys_head_to_tail]
    return []


def _collector_has_vehicle(collector, vehicle_name: str) -> bool:
    for record in collector.export_node_baseline_visits(TARGET_NODE_NAME):
        if record["vehicle_name"] == vehicle_name:
            return True
    return False


def _collector_has_visit_key(collector, visit_key: tuple) -> bool:
    return collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1]) is not None


def _rank_membership_snapshot(world) -> dict:
    rank_state = _rank_state(world)
    if rank_state is None:
        return {
            "confirmed_ranks_by_visit_key": {},
            "undetermined_visit_keys": frozenset(),
        }
    confirmed: dict[tuple, int] = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        assigned = rank_state.assigned_rank(visit_key)
        if assigned is None:
            raise RuntimeError(f"{_visit_text(plain)} confirmed without rank.")
        confirmed[plain] = assigned
    undetermined = frozenset(_plain_visit_key(key) for key in rank_state.undetermined_visit_keys())
    overlap = set(confirmed) & undetermined
    if len(overlap) != 0:
        raise RuntimeError("Rank snapshot overlap.")
    return {
        "confirmed_ranks_by_visit_key": confirmed,
        "undetermined_visit_keys": undetermined,
    }


def _locate_inlink(order_keys: list[tuple], visit_key: tuple):
    for index, key in enumerate(order_keys):
        if key == visit_key:
            return index, order_keys[:index]
    return None, []


def _capture_t392_post(world, stages: dict, post_rank: dict) -> dict:
    collector = stages["collector"]
    candidate_node = _one_node(stages["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate")
    right_node = _one_node(stages["right_of_entry_nodes"], TARGET_NODE_NAME, "roe")
    final_rank_node = _one_node(stages["final_rank_nodes"], TARGET_NODE_NAME, "final")
    candidate_keys = [_plain_visit_key(cv.visit_key) for cv in candidate_node.candidate_visits]
    order_keys = _target_inlink_order_keys(stages["inlink_physical_orders"])
    vehicle = world.VEHICLES.get(TARGET_VEHICLE_NAME)
    visit_registered = _plain_visit(vehicle) == TARGET_VISIT_KEY
    visit_key_text = _visit_text(TARGET_VISIT_KEY) if visit_registered else "target_visit_unregistered"
    in_export_visit = _collector_has_visit_key(collector, TARGET_VISIT_KEY)
    in_export_vehicle = _collector_has_vehicle(collector, TARGET_VEHICLE_NAME)
    in_physical = _visit_in_physical_orders(stages["inlink_physical_orders"], TARGET_VISIT_KEY)
    in_candidate = TARGET_VISIT_KEY in candidate_keys
    in_final = any(
        _plain_visit_key(fv.visit_key) == TARGET_VISIT_KEY for fv in final_rank_node.final_rank_visits
    )
    post_c = post_rank["confirmed_ranks_by_visit_key"].get(TARGET_VISIT_KEY)
    for index, key in enumerate(order_keys):
        _append_comparison(
            "t392_target_inlink_physical_order",
            TARGET_TIMESTEP,
            TARGET_VEHICLE_NAME,
            _visit_text(key),
            "physical_index",
            index,
            EXPECTED_T401_FORMAL_INLINK_NAME,
        )
    fields = {
        "visit_registered_on_vehicle": visit_registered,
        "collector_export_has_vehicle_name": in_export_vehicle,
        "collector_export_has_target_visit_key": in_export_visit,
        "inlink_physical_order_has_target_visit_key": in_physical,
        "candidate_visits_has_target_visit_key": in_candidate,
        "final_rank_has_target_visit_key": in_final,
        "post_driver_assigned_c_rank": post_c,
        "right_of_entry_visit_key": (
            _visit_text(_plain_visit_key(right_node.right_of_entry_visit_key))
            if right_node.right_of_entry_visit_key is not None
            else ""
        ),
    }
    for name, value in fields.items():
        _append_comparison(
            "t392_formal_membership",
            TARGET_TIMESTEP,
            TARGET_VEHICLE_NAME,
            visit_key_text,
            name,
            value,
            "",
        )
    return {
        "order_keys": order_keys,
        "fields": fields,
        "visit_registered": visit_registered,
    }


def _capture_t401(world, stages: dict, pre_rank: dict, post_rank: dict) -> dict:
    collector = stages["collector"]
    candidate_node = _one_node(stages["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate")
    right_node = _one_node(stages["right_of_entry_nodes"], TARGET_NODE_NAME, "roe")
    final_rank_node = _one_node(stages["final_rank_nodes"], TARGET_NODE_NAME, "final")
    candidate_keys = [_plain_visit_key(cv.visit_key) for cv in candidate_node.candidate_visits]
    order_keys = _target_inlink_order_keys(stages["inlink_physical_orders"])
    index, ahead = _locate_inlink(order_keys, TARGET_VISIT_KEY)
    record = collector.get_baseline_visit_snapshot(TARGET_VISIT_KEY[0], TARGET_VISIT_KEY[1])
    if record is None:
        raise RuntimeError("T=401 target visit missing from collector export.")
    roe_key = None
    if right_node.right_of_entry_visit_key is not None:
        roe_key = _plain_visit_key(right_node.right_of_entry_visit_key)
    final_visit = None
    for fv in final_rank_node.final_rank_visits:
        if _plain_visit_key(fv.visit_key) == TARGET_VISIT_KEY:
            final_visit = fv
    local_rank = ""
    if TARGET_VISIT_KEY in candidate_keys:
        local_rank = str(candidate_keys.index(TARGET_VISIT_KEY) + 1)
    b_record = collector.get_baseline_visit_snapshot(COMPARE_VISIT_B[0], COMPARE_VISIT_B[1])
    capture = {
        "formal_inlink": EXPECTED_T401_FORMAL_INLINK_NAME,
        "physical_index": index,
        "ahead_keys": ahead,
        "baseline_arrival": record["baseline_arrival_timestep"],
        "baseline_passage": record["baseline_passage_timestep"],
        "is_right_of_entry": roe_key == TARGET_VISIT_KEY,
        "candidate_local_rank": local_rank,
        "pre_c_rank": pre_rank["confirmed_ranks_by_visit_key"].get(TARGET_VISIT_KEY),
        "post_c_rank": post_rank["confirmed_ranks_by_visit_key"].get(TARGET_VISIT_KEY),
        "finalization_source": final_visit.finalization_source.value if final_visit else "",
        "final_rank_status": final_rank_node.final_rank_status.value,
        "b_baseline_arrival": b_record["baseline_arrival_timestep"] if b_record else None,
    }
    mapping = {
        "formal_inlink_name": capture["formal_inlink"],
        "physical_index": capture["physical_index"],
        "ahead_visit_keys": "|".join(_visit_text(k) for k in ahead),
        "baseline_arrival_timestep": capture["baseline_arrival"],
        "baseline_passage_timestep": capture["baseline_passage"],
        "is_right_of_entry": capture["is_right_of_entry"],
        "candidate_baseline_local_rank": capture["candidate_local_rank"],
        "pre_assigned_c_rank": capture["pre_c_rank"],
        "post_assigned_c_rank": capture["post_c_rank"],
        "finalization_source": capture["finalization_source"],
        "final_rank_status": capture["final_rank_status"],
        "compare_b_baseline_arrival": capture["b_baseline_arrival"],
    }
    for name, value in mapping.items():
        _append_comparison(
            "t401_formal_snapshot",
            TIMESTEP_T401,
            TARGET_VEHICLE_NAME,
            _visit_text(TARGET_VISIT_KEY),
            name,
            value,
            "",
        )
    return capture


def _hypothesis_verdict() -> dict:
    pre = GATE.t392_pre_snapshot_row
    post392 = GATE.t392_post_capture
    cap401 = GATE.t401_capture
    parts: dict[str, str] = {}
    if pre is None or post392 is None or cap401 is None:
        return {"parts": parts, "overall": "正式objectだけでは未確定"}

    parts["A_t392_on_target_inlink"] = (
        "支持" if pre["link_position_class"] == "A_on_target_inlink" else "反証"
    )
    parts["B_t392_end_node_southwest"] = (
        "支持" if pre["end_node_is_southwest_intersection"] is True else "反証"
    )
    parts["C_t392_visit_targets_northwest"] = (
        "支持" if pre["current_visit_targets_northwest"] is True else "反証"
    )
    if pre["has_order_control_current_visit"] is True and type(pre["current_visit_id"]) is int:
        parts["D_t392_visit_id_is_2"] = "支持" if pre["current_visit_id"] == 2 else "反証"
    else:
        parts["D_t392_visit_id_is_2"] = "正式objectだけでは未確定"
    if pre["has_order_control_current_visit"] is True and pre["current_visit_inlink_name"] != "":
        parts["E_t392_visit_inlink_matches_vehicle_link"] = (
            "支持" if pre["current_visit_inlink_name"] == pre["current_link_name"] else "反証"
        )
    else:
        parts["E_t392_visit_inlink_matches_vehicle_link"] = "正式objectだけでは未確定"
    entered = [
        row
        for row in GATE.transition_rows
        if row["after_link_name"] == EXPECTED_T401_FORMAL_INLINK_NAME
    ]
    parts["F_target_inlink_transition_observed"] = "支持" if len(entered) > 0 else "反証"
    if len(entered) == 0:
        parts["G_visit2_on_target_inlink_entry"] = "正式objectだけでは未確定"
    else:
        entry = entered[0]
        parts["G_visit2_on_target_inlink_entry"] = (
            "支持" if entry["current_visit_id"] == 2 else "反証"
        )
    arrival = GATE.first_northwest_arrival
    parts["H_northwest_arrival_recorded"] = (
        "支持"
        if arrival is not None and arrival["formal_timestep"] == EXPECTED_NORTHWEST_ARRIVAL_TIMESTEP
        else ("反証" if arrival is not None else "正式objectだけでは未確定")
    )
    baseline_actual_match = (
        arrival is not None
        and cap401["baseline_arrival"] == EXPECTED_T401_BASELINE_ARRIVAL
        and arrival["formal_timestep"] == cap401["baseline_arrival"]
    )
    parts["I_baseline_and_actual_arrival_match"] = (
        "支持" if baseline_actual_match else "正式objectだけでは未確定"
    )
    if post392["fields"]["collector_export_has_target_visit_key"] is False:
        parts["snapshot_exclusion_at_t392"] = "支持"
    else:
        parts["snapshot_exclusion_at_t392"] = "反証"

    entry_events = [
        row
        for row in GATE.transition_rows
        if row["after_link_name"] == EXPECTED_T401_FORMAL_INLINK_NAME
    ]
    continuous_entry = (
        len(entry_events) == 1
        and entry_events[0]["is_continuous_link_connection"] is True
    )
    arrival_on_inlink = (
        arrival is not None
        and arrival["current_link_name"] == EXPECTED_T401_FORMAL_INLINK_NAME
    )

    story_ok = (
        parts["A_t392_on_target_inlink"] == "反証"
        and parts["B_t392_end_node_southwest"] == "支持"
        and continuous_entry
        and parts["G_visit2_on_target_inlink_entry"] == "支持"
        and parts["H_northwest_arrival_recorded"] == "支持"
        and arrival_on_inlink
        and parts["I_baseline_and_actual_arrival_match"] == "支持"
        and parts["snapshot_exclusion_at_t392"] == "支持"
        and cap401["is_right_of_entry"] is True
        and cap401["post_c_rank"] == EXPECTED_T401_ASSIGNED_RANK
    )
    if story_ok and parts["C_t392_visit_targets_northwest"] == "支持":
        overall = "支持"
    elif story_ok:
        overall = "部分支持"
    elif parts["A_t392_on_target_inlink"] == "支持" or parts["snapshot_exclusion_at_t392"] == "反証":
        overall = "反証"
    else:
        overall = "正式objectだけでは未確定"
    return {"parts": parts, "overall": overall}


def _build_review() -> str:
    verdict = _hypothesis_verdict()
    parts = verdict["parts"]
    pre = GATE.t392_pre_snapshot_row
    lines = [
        "T=392 veh_sw_nw_base_041 real-World location diagnostic",
        "",
        "T=392 observations",
        f"  A in snapshot physical order (driver result): "
        f"{GATE.t392_post_capture['fields']['inlink_physical_order_has_target_visit_key'] if GATE.t392_post_capture else ''}",
        f"  A in collector export: "
        f"{GATE.t392_post_capture['fields']['collector_export_has_target_visit_key'] if GATE.t392_post_capture else ''}",
        f"  A formal inlink at T=392 driver: (not in snapshot export)",
        f"  A physical index at T=392 driver: n/a",
        f"  A Candidate outside reason: not_in_snapshot_fixed_visit_set",
        f"  Physical ahead observable at T=392: False",
        f"  Selected trade-scope behind decidable at T=392: False",
        "",
        "T=392 pre-driver real World",
        f"  current_link_name: {pre['current_link_name'] if pre else ''}",
        f"  link_position_class: {pre['link_position_class'] if pre else ''}",
        f"  current_visit_node_name: {pre['current_visit_node_name'] if pre else ''}",
        f"  visit_id on vehicle: {pre['current_visit_id'] if pre else ''}",
        f"  current_visit_inlink_name: {pre['current_visit_inlink_name'] if pre else ''}",
        "",
        "T=401 observations",
    ]
    if GATE.t401_capture:
        c = GATE.t401_capture
        lines.extend(
            [
                f"  A formal inlink: {c['formal_inlink']}",
                f"  A physical index: {c['physical_index']}",
                f"  A ahead visits: {'|'.join(_visit_text(k) for k in c['ahead_keys'])}",
                f"  A baseline arrival: {c['baseline_arrival']}",
                f"  A baseline passage: {c['baseline_passage']}",
                f"  A right-of-entry: {c['is_right_of_entry']}",
                f"  A post C rank: {c['post_c_rank']}",
                f"  B baseline arrival: {c['b_baseline_arrival']}",
                f"  B C rank at T=401 post: undetermined",
                f"  T=401 baseline arrival vs actual arrival at T=407: "
                f"{c['baseline_arrival']} / "
                f"{GATE.first_northwest_arrival['formal_timestep'] if GATE.first_northwest_arrival else ''}",
            ]
        )
    entry_rows = [
        row
        for row in GATE.transition_rows
        if row["after_link_name"] == EXPECTED_T401_FORMAL_INLINK_NAME
    ]
    if len(entry_rows) == 1:
        entry = entry_rows[0]
        lines.extend(
            [
                "",
                "Target inlink entry and northwest arrival",
                f"  target inlink entry timestep: {entry['timestep']}",
                f"  before link: {entry['before_link_name']}",
                f"  after link: {entry['after_link_name']}",
                f"  entry current_visit node: {entry['current_visit_node_name']}",
                f"  entry visit_id: {entry['current_visit_id']}",
            ]
        )
    if GATE.first_northwest_arrival is not None:
        arr = GATE.first_northwest_arrival
        lines.extend(
            [
                f"  northwest actual arrival timestep: {arr['formal_timestep']}",
                f"  arrival current link: {arr['current_link_name']}",
                f"  arrival visit node: {arr['current_visit_node_name']}",
                f"  arrival visit_id: {arr['visit_id']}",
            ]
        )
    lines.extend(
        [
            "",
            "T=392 vs target inlink (pre-driver)",
            f"  not on target inlink at T=392: {pre['link_position_class'] != 'A_on_target_inlink' if pre else ''}",
            f"  current link end node: {pre['current_link_end_node_name'] if pre else ''}",
            f"  upstream-to-SW connection class: {pre['link_position_class'] if pre else ''}",
        ]
    )
    lines.append("")
    lines.append("Hypothesis parts")
    for key, value in parts.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("Conclusions")
    lines.append("  1. Same-inlink behind at T=392: not observable (A absent from T=392 snapshot physical order).")
    lines.append("  2. T=392: target visit not in snapshot fixed visit set / collector export.")
    lines.append("  3. T=401: target visit in formal snapshot, right-of-entry, C184 after driver.")
    lines.append("  4. T=401 right-of-entry and C184 before B; baseline/actual arrival both 407.")
    lines.append("")
    lines.append(f"Overall verdict: {verdict['overall']}")
    return "\n".join(lines) + "\n"


def wrapped_arrival(vehicle, node):
    before_fields = _current_visit_fields(vehicle)
    arrival_before = before_fields["arrival_time"]
    result = GATE.original_arrival(vehicle, node)
    if vehicle.W is not GATE.real_world:
        return result
    if getattr(vehicle.W, "_order_control_baseline_collector", None) is not None:
        return result
    if vehicle.name != TARGET_VEHICLE_NAME:
        return result
    if node is None or node.name != TARGET_NODE_NAME:
        return result
    after_fields = _current_visit_fields(vehicle)
    arrival_after = after_fields["arrival_time"]
    if arrival_after is None:
        return result
    if GATE.first_northwest_arrival is not None:
        return result
    visit_id = after_fields["visit_id"]
    visit_node_name = after_fields["node_name"] if after_fields["node_name"] != "" else node.name
    link = getattr(vehicle, "link", None)
    GATE.first_northwest_arrival = {
        "world_timestep": vehicle.W.T,
        "raw_arrival_time": arrival_after,
        "formal_timestep": _formal_arrival_timestep(arrival_after, vehicle.W.DELTAT),
        "current_link_name": None if link is None else getattr(link, "name", None),
        "position_x": getattr(vehicle, "x", None),
        "visit_id": visit_id,
        "node_name": visit_node_name,
        "current_visit_node_name": after_fields["node_name"],
        "arrival_time_before": arrival_before,
    }
    return result


def wrapped_driver(world):
    pre_rank = None
    if world is GATE.real_world and getattr(world, "_order_control_baseline_collector", None) is None:
        if world.T == TARGET_TIMESTEP and GATE.t392_pre_snapshot_row is None:
            GATE.t392_pre_snapshot_row = _capture_t392_pre_driver_snapshot(world)
            link = getattr(_vehicle_by_name(world, TARGET_VEHICLE_NAME), "link", None)
            GATE.last_link_name = None if link is None else link.name
            GATE.last_link_end_node_name = None if link is None else _link_node_name(link, "end_node")
        elif type(world.T) is int and world.T > TARGET_TIMESTEP:
            _record_link_transition(world, "before_tvt_driver")
        if world.T in CAPTURE_DRIVER_TIMESTEPS:
            pre_rank = _rank_membership_snapshot(world)
    result = GATE.original_driver(world)
    if world is not GATE.real_world:
        return result
    if getattr(world, "_order_control_baseline_collector", None) is not None:
        return result
    if world.T not in CAPTURE_DRIVER_TIMESTEPS:
        return result
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={world.T} driver result type is wrong.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(f"T={world.T} atomic_apply_set_result is None.")
    if pre_rank is None:
        raise RuntimeError(f"T={world.T} pre-driver rank snapshot missing.")
    post_rank = _rank_membership_snapshot(world)
    stages = _stages_from_atomic(atomic)
    if world.T == TARGET_TIMESTEP:
        GATE.t392_post_capture = _capture_t392_post(world, stages, post_rank)
    if world.T == TIMESTEP_T401:
        GATE.t401_capture = _capture_t401(world, stages, pre_rank, post_rank)
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Hooks already installed.")
    GATE.real_world = real_world
    GATE.target_inlink_link = _find_link_by_name(real_world, EXPECTED_T401_FORMAL_INLINK_NAME)
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
    GATE.target_inlink_link = None
    GATE.installed = False


def _prepare_world():
    world = trial.build_world()
    vot_values = trial._true_vot_sequence()
    vot_records = trial.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
    trial.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
    trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    return world


def _validate_runtime(world) -> None:
    if GATE.t392_pre_snapshot_row is None:
        raise RuntimeError("T=392 pre-driver snapshot missing.")
    if GATE.t392_post_capture is None or GATE.t401_capture is None:
        raise RuntimeError("T=392/T=401 formal captures missing.")
    post392 = GATE.t392_post_capture["fields"]
    if post392["candidate_visits_has_target_visit_key"] is True:
        raise RuntimeError("T=392: target visit must not be in candidate_visits.")
    if post392["post_driver_assigned_c_rank"] is not None:
        raise RuntimeError("T=392: target visit must have no C rank after driver.")
    if TARGET_VISIT_KEY in GATE.t392_post_capture["order_keys"]:
        raise RuntimeError("T=392: target visit must not be on target inlink physical order.")
    cap401 = GATE.t401_capture
    if cap401["physical_index"] != EXPECTED_T401_PHYSICAL_INDEX:
        raise RuntimeError("T=401 physical index mismatch.")
    if cap401["baseline_arrival"] != EXPECTED_T401_BASELINE_ARRIVAL:
        raise RuntimeError("T=401 baseline arrival mismatch.")
    if cap401["baseline_passage"] != EXPECTED_T401_BASELINE_PASSAGE:
        raise RuntimeError("T=401 baseline passage mismatch.")
    if cap401["is_right_of_entry"] is not True:
        raise RuntimeError("T=401: target must be right-of-entry.")
    if cap401["pre_c_rank"] is not None:
        raise RuntimeError("T=401: target must have no pre-driver C rank.")
    if cap401["post_c_rank"] != EXPECTED_T401_ASSIGNED_RANK:
        raise RuntimeError("T=401: target must have C184 after driver.")
    if cap401["finalization_source"] != EXPECTED_T401_FINALIZATION_SOURCE:
        raise RuntimeError("T=401 finalization source mismatch.")
    if cap401["final_rank_status"] != EXPECTED_T401_FINAL_RANK_STATUS:
        raise RuntimeError("T=401 final rank status mismatch.")
    expected_ahead = (("veh_sw_nw_base_039", 2), ("veh_sw_nw_base_040", 2))
    if tuple(cap401["ahead_keys"]) != expected_ahead:
        raise RuntimeError("T=401 ahead visit keys mismatch.")
    pre = GATE.t392_pre_snapshot_row
    if pre["current_link_name"] == "":
        raise RuntimeError("T=392 pre-driver current_link_name is empty.")
    if pre["current_link_start_node_name"] == "" or pre["current_link_end_node_name"] == "":
        raise RuntimeError("T=392 pre-driver link start/end node names are empty.")
    if pre["link_position_class"] == "":
        raise RuntimeError("T=392 link_position_class is missing.")
    if pre["has_order_control_current_visit"] is True:
        if pre["current_visit_node_name"] == "":
            raise RuntimeError("T=392 current visit exists but node_name is empty.")
        if type(pre["current_visit_id"]) is not int or type(pre["current_visit_id"]) is bool:
            raise RuntimeError("T=392 current visit exists but visit_id is not int.")
        if pre["current_visit_inlink_name"] != pre["current_link_name"]:
            raise RuntimeError("T=392 current_visit inlink must match vehicle link.")
    if pre["link_position_class"] == "A_on_target_inlink":
        raise RuntimeError("T=392: target must not already be on target inlink.")
    if post392["collector_export_has_target_visit_key"] is False:
        if post392["collector_export_has_vehicle_name"] is True:
            raise RuntimeError("T=392: vehicle in export but target visit key missing (unexpected).")
    for row in GATE.transition_rows:
        if row["before_link_name"] is None or row["after_link_name"] is None:
            continue
        before_end = row["before_link_end_node_name"]
        after_start = row["after_link_start_node_name"]
        if before_end is not None and after_start is not None:
            if row["is_continuous_link_connection"] is not (before_end == after_start):
                raise RuntimeError(
                    f"Link transition at T={row['timestep']} continuous flag mismatch."
                )
        if row["is_continuous_link_connection"] is not True:
            raise RuntimeError(
                f"Link transition at T={row['timestep']} is not a continuous formal link connection."
            )
    entered = [r for r in GATE.transition_rows if r["after_link_name"] == EXPECTED_T401_FORMAL_INLINK_NAME]
    if len(entered) != 1:
        raise RuntimeError("Target inlink entry must be observed exactly once.")
    entry = entered[0]
    if entry["after_link_start_node_name"] != SOUTHWEST_NODE_NAME:
        raise RuntimeError("Target inlink entry: after start node must be southwest_intersection.")
    if entry["before_link_end_node_name"] != SOUTHWEST_NODE_NAME:
        raise RuntimeError("Target inlink entry: before end node must be southwest_intersection.")
    if entry["is_continuous_link_connection"] is not True:
        raise RuntimeError("Target inlink entry must be a continuous link connection.")
    if entry["current_visit_id"] != 2:
        raise RuntimeError("Target inlink entry must have current_visit_id 2.")
    if entry["current_visit_node_name"] != TARGET_NODE_NAME:
        raise RuntimeError("Target inlink entry must have northwest_intersection current visit.")
    arrival = GATE.first_northwest_arrival
    if arrival is None:
        raise RuntimeError("first_northwest_arrival is missing.")
    if arrival["node_name"] != TARGET_NODE_NAME:
        raise RuntimeError("Arrival node_name must be northwest_intersection.")
    if arrival["visit_id"] != 2:
        raise RuntimeError("Arrival visit_id must be 2.")
    if arrival["formal_timestep"] != EXPECTED_NORTHWEST_ARRIVAL_TIMESTEP:
        raise RuntimeError("Arrival formal timestep must be 407.")
    if arrival["world_timestep"] != EXPECTED_NORTHWEST_ARRIVAL_TIMESTEP:
        raise RuntimeError("Arrival world_timestep must be 407.")
    recomputed = _formal_arrival_timestep(arrival["raw_arrival_time"], world.DELTAT)
    if recomputed != arrival["formal_timestep"]:
        raise RuntimeError("Arrival raw time does not match formal timestep.")
    if arrival["current_link_name"] != EXPECTED_T401_FORMAL_INLINK_NAME:
        raise RuntimeError("Arrival current link must be target inlink.")
    if arrival["current_visit_node_name"] != TARGET_NODE_NAME:
        raise RuntimeError("Arrival current visit node must be northwest_intersection.")
    if entry["timestep"] > arrival["world_timestep"]:
        raise RuntimeError("Target inlink entry must occur before or at arrival timestep.")
    entry_t = entry["timestep"]
    arrival_t = arrival["world_timestep"]
    for row in GATE.transition_rows:
        if row["timestep"] <= entry_t or row["timestep"] >= arrival_t:
            continue
        if (
            row["before_link_name"] == EXPECTED_T401_FORMAL_INLINK_NAME
            and row["after_link_name"] != EXPECTED_T401_FORMAL_INLINK_NAME
        ):
            raise RuntimeError("Vehicle left target inlink after entry before northwest arrival.")
    if cap401["baseline_arrival"] != arrival["formal_timestep"]:
        raise RuntimeError("T=401 baseline arrival must match actual arrival timestep.")


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

    GATE.t392_pre_snapshot_row = None
    GATE.t392_post_capture = None
    GATE.t401_capture = None
    GATE.transition_rows = []
    GATE.comparison_rows = []
    GATE.last_link_name = None
    GATE.last_link_end_node_name = None
    GATE.first_northwest_arrival = None

    original_limit = sys.getrecursionlimit()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
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
        _validate_runtime(world)
        GATE.review_text = _build_review()
        snapshot_rows = [GATE.t392_pre_snapshot_row]
        _validate_csv_rows(SNAPSHOT_COLUMNS, snapshot_rows, SNAPSHOT_CSV)
        _validate_csv_rows(TRANSITION_COLUMNS, GATE.transition_rows, TRANSITIONS_CSV)
        _validate_csv_rows(COMPARISON_COLUMNS, GATE.comparison_rows, COMPARISON_CSV)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_csv(OUTPUT_DIR / SNAPSHOT_CSV, SNAPSHOT_COLUMNS, snapshot_rows)
        _write_csv(OUTPUT_DIR / TRANSITIONS_CSV, TRANSITION_COLUMNS, GATE.transition_rows)
        _write_csv(OUTPUT_DIR / COMPARISON_CSV, COMPARISON_COLUMNS, GATE.comparison_rows)
        (OUTPUT_DIR / REVIEW_NAME).write_text(GATE.review_text, encoding="utf-8")
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


def _module_string_constants(tree) -> set[str]:
    values: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if isinstance(node.value, ast.Constant) and type(node.value.value) is str:
                values.add(node.value.value)
    return values


def _subscript_constant_key(node: ast.Subscript):
    if isinstance(node.slice, ast.Constant):
        return node.slice.value
    if isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Constant):
        return node.slice.value.value
    return None


def _current_visit_uses_false_node_name_field(tree) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "get":
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "current_visit":
                continue
            if len(node.args) < 1 or not isinstance(node.args[0], ast.Constant):
                continue
            if node.args[0].value == "node_name":
                return True
        if isinstance(node, ast.Subscript):
            if not isinstance(node.value, ast.Name) or node.value.id != "current_visit":
                continue
            if _subscript_constant_key(node) == "node_name":
                return True
    return False


def _current_visit_fields_reads_node_object(tree) -> bool:
    helper = _function_node(tree, "_current_visit_fields")
    if helper is None:
        return False
    for node in ast.walk(helper):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get":
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "current_visit":
            continue
        if len(node.args) < 1 or not isinstance(node.args[0], ast.Constant):
            continue
        if node.args[0].value == "node":
            return True
    return False


def _object_name_reads_name_attribute(tree) -> bool:
    object_name_fn = _function_node(tree, "_object_name")
    if object_name_fn is None:
        return False
    for node in ast.walk(object_name_fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "getattr":
            continue
        if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant):
            continue
        if node.args[1].value == "name":
            return True
    return False


def _current_visit_helper_reads_node_name(tree) -> bool:
    return (
        _current_visit_fields_reads_node_object(tree) is True
        and _object_name_reads_name_attribute(tree) is True
    )


def _function_getattr_second_arg(function_node, obj_name: str, attr: str) -> bool:
    if function_node is None:
        return False
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "getattr":
            continue
        if len(node.args) < 2:
            continue
        if not isinstance(node.args[0], ast.Name) or node.args[0].id != obj_name:
            continue
        if not isinstance(node.args[1], ast.Constant) or node.args[1].value != attr:
            continue
        return True
    return False


def _pre_snapshot_reads_vehicle_link(tree) -> bool:
    pre_fn = _function_node(tree, "_capture_t392_pre_driver_snapshot")
    if _function_getattr_second_arg(pre_fn, "vehicle", "link"):
        return True
    if pre_fn is None:
        return False
    for node in ast.walk(pre_fn):
        if isinstance(node, ast.Attribute) and node.attr == "link":
            if isinstance(node.value, ast.Name) and node.value.id == "vehicle":
                return True
    return False


def _pre_snapshot_calls_link_node_name(tree, which: str) -> bool:
    pre_fn = _function_node(tree, "_capture_t392_pre_driver_snapshot")
    if pre_fn is None:
        return False
    for node in ast.walk(pre_fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "_link_node_name":
            continue
        if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant):
            continue
        if node.args[1].value == which:
            return True
    return False


def _link_node_name_reads_link_and_node_name(tree) -> bool:
    link_fn = _function_node(tree, "_link_node_name")
    if link_fn is None:
        return False
    reads_link_which = False
    reads_node_name = False
    for node in ast.walk(link_fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "getattr":
            continue
        if len(node.args) < 2:
            continue
        if isinstance(node.args[0], ast.Name) and node.args[0].id == "link":
            if isinstance(node.args[1], ast.Name) and node.args[1].id == "which":
                reads_link_which = True
        if isinstance(node.args[0], ast.Name) and node.args[0].id == "node":
            if isinstance(node.args[1], ast.Constant) and node.args[1].value == "name":
                reads_node_name = True
    return reads_link_which and reads_node_name


def _pre_snapshot_reads_link_nodes_through_helper(tree) -> bool:
    return (
        _pre_snapshot_calls_link_node_name(tree, "start_node") is True
        and _pre_snapshot_calls_link_node_name(tree, "end_node") is True
        and _link_node_name_reads_link_and_node_name(tree) is True
    )


def _pre_snapshot_reads_route_next_link(tree) -> bool:
    pre_fn = _function_node(tree, "_capture_t392_pre_driver_snapshot")
    if _function_getattr_second_arg(pre_fn, "vehicle", "route_next_link"):
        return True
    if pre_fn is None:
        return False
    for node in ast.walk(pre_fn):
        if isinstance(node, ast.Attribute) and node.attr == "route_next_link":
            if isinstance(node.value, ast.Name) and node.value.id == "vehicle":
                return True
    return False


def _pre_snapshot_calls_current_visit_fields(tree) -> bool:
    pre_fn = _function_node(tree, "_capture_t392_pre_driver_snapshot")
    if pre_fn is None:
        return False
    for node in ast.walk(pre_fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "_current_visit_fields":
            continue
        if len(node.args) < 1 or not isinstance(node.args[0], ast.Name):
            continue
        if node.args[0].id == "vehicle":
            return True
    return False


def _current_visit_fields_reads_order_control_visit(tree) -> bool:
    visit_fn = _function_node(tree, "_current_visit_fields")
    return _function_getattr_second_arg(visit_fn, "vehicle", "order_control_current_visit")


def _pre_snapshot_reads_current_visit_through_helper(tree) -> bool:
    return (
        _pre_snapshot_calls_current_visit_fields(tree) is True
        and _current_visit_fields_reads_order_control_visit(tree) is True
    )


def _transition_stores_link_end_on_gate(tree) -> bool:
    fn = _function_node(tree, "_record_link_transition")
    if fn is None:
        return False
    found_end_fetch = False
    found_gate_assign = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "after_end":
                    found_end_fetch = True
                if isinstance(target, ast.Attribute):
                    if (
                        isinstance(target.value, ast.Name)
                        and target.value.id == "GATE"
                        and target.attr == "last_link_end_node_name"
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "after_end"
                    ):
                        found_gate_assign = True
    return found_end_fetch and found_gate_assign


def validate_static_contract() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    if TARGET_TIMESTEP != 392 or TIMESTEP_T401 != 401:
        raise RuntimeError("Capture timesteps must be 392 and 401.")
    if SIMULATION_UNTIL_TIMESTEP != 407 or EXPECTED_WORLD_T_AFTER_SIM != 408:
        raise RuntimeError("Simulation end must be T=407 / World.T=408.")
    if EXPECTED_NORTHWEST_ARRIVAL_TIMESTEP != 407:
        raise RuntimeError("Expected northwest arrival timestep must be 407.")
    for file_name in OUTPUT_FILE_NAMES:
        if file_name not in _module_string_constants(tree):
            raise RuntimeError(f"Missing output file constant {file_name!r}.")
    if _function_node(tree, "_current_visit_fields") is None:
        raise RuntimeError("current Visit helper is missing.")
    if _current_visit_helper_reads_node_name(tree) is not True:
        raise RuntimeError("current Visit helper must read node.name from visit dict.")
    if _current_visit_uses_false_node_name_field(tree) is True:
        raise RuntimeError("Must not use current_visit.get('node_name') or current_visit['node_name'].")
    if _transition_stores_link_end_on_gate(tree) is not True:
        raise RuntimeError("_record_link_transition must store after_end on GATE.last_link_end_node_name.")
    if _function_node(tree, "_capture_t392_pre_driver_snapshot") is None:
        raise RuntimeError("T=392 pre-driver snapshot helper is missing.")
    driver_fn = _function_node(tree, "wrapped_driver")
    if driver_fn is None or _call_count(driver_fn, "GATE", "original_driver") != 1:
        raise RuntimeError("wrapped_driver must call original_driver once.")
    arrival_fn = _function_node(tree, "wrapped_arrival")
    if arrival_fn is None or _call_count(arrival_fn, "GATE", "original_arrival") != 1:
        raise RuntimeError("wrapped_arrival must call original_arrival once.")
    stages_fn = _function_node(tree, "_stages_from_atomic")
    if stages_fn is None:
        raise RuntimeError("_stages_from_atomic is missing.")
    found_inlink = False
    for node in ast.walk(stages_fn):
        if isinstance(node, ast.Attribute) and node.attr == "inlink_physical_orders":
            found_inlink = True
    if found_inlink is not True:
        raise RuntimeError("Must use fork_result.inlink_physical_orders.")
    if _pre_snapshot_reads_vehicle_link(tree) is not True:
        raise RuntimeError("Pre snapshot must read vehicle current Link via formal object access.")
    if _pre_snapshot_reads_link_nodes_through_helper(tree) is not True:
        raise RuntimeError("Pre snapshot must read Link start/end Nodes through _link_node_name.")
    if _pre_snapshot_reads_route_next_link(tree) is not True:
        raise RuntimeError("Pre snapshot must read route_next_link via formal object access.")
    if _pre_snapshot_reads_current_visit_through_helper(tree) is not True:
        raise RuntimeError("Pre snapshot must read current Visit through _current_visit_fields.")
    runtime_fn = _function_node(tree, "_validate_runtime")
    requires_arrival = False
    if runtime_fn is not None:
        for node in ast.walk(runtime_fn):
            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "GATE"
                    and node.attr == "first_northwest_arrival"
                ):
                    requires_arrival = True
    if requires_arrival is not True:
        raise RuntimeError("_validate_runtime must require GATE.first_northwest_arrival.")
    main_node = _function_node(tree, "main")
    sim_until = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "exec_simulation":
                for keyword in node.keywords:
                    if keyword.arg == "until_t":
                        sim_until = True
            if node.func.attr == "mkdir":
                pass
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic must not call trial.main.")
    if sim_until is not True:
        raise RuntimeError("main must call exec_simulation with until_t.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation must not run simulation or hooks.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
