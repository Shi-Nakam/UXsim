"""
Read-only trace of route_next_link_choice for the T=600 baseline fork and the
real World.

The traced vehicle is veh_ne_wn_base_032:1 at northeast_intersection.
Candidate local worlds are ignored. This script does not fix a route and
does not rerun the baseline fork.
"""

from __future__ import annotations

import ast
import copy
import csv
import datetime
import hashlib
import json
import numbers
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import uxsim.order_control_baseline_driver as baseline_driver_module
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module

import run_tvt_mp_four_cross_intersections_grid_medium_all_participating_trial as four_cross_trial


SCENARIO_NAME = four_cross_trial.SCENARIO_NAME
DIAGNOSTIC_SCRIPT_NAME = SCRIPT_PATH.name
OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900_timestep_seed_1_t600_baseline_actual_route_choice_trace"
    )
)
EARLY_STOP_OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900_timestep_seed_1_t600_baseline_route_choice_early_stop"
    )
)

COMMON_ORIGIN_CSV = "baseline_actual_common_origin_rng.csv"
ROUTE_CHOICE_CSV = "baseline_actual_route_choice_calls.csv"
TARGET_ROUTE_CHOICE_CSV = "target_vehicle_route_choice_calls.csv"
RNG_TRANSITION_CSV = "baseline_actual_rng_transitions.csv"
PASSAGE_CONTEXT_CSV = "target_vehicle_passage_context.csv"
SUMMARY_NAME = "first_route_choice_divergence_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    COMMON_ORIGIN_CSV,
    ROUTE_CHOICE_CSV,
    TARGET_ROUTE_CHOICE_CSV,
    RNG_TRANSITION_CSV,
    PASSAGE_CONTEXT_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)
EARLY_STOP_SNAPSHOT_JSON = "t600_baseline_target_snapshot.json"
EARLY_STOP_TARGET_ROUTE_CHOICE_CSV = "t600_baseline_target_route_choice_calls.csv"
EARLY_STOP_ALL_ROUTE_CHOICE_CSV = "t600_baseline_all_route_choice_calls.csv"
EARLY_STOP_OUTPUT_FILE_NAMES = (
    EARLY_STOP_SNAPSHOT_JSON,
    EARLY_STOP_TARGET_ROUTE_CHOICE_CSV,
    EARLY_STOP_ALL_ROUTE_CHOICE_CSV,
    MANIFEST_NAME,
)
CLI_STOP_AFTER_T600_BASELINE = "--stop-after-t600-baseline"
CLI_STATIC_VALIDATE_ONLY = "--static-validate-only"

TARGET_NODE_NAME = "northeast_intersection"
TARGET_VEHICLE_NAME = "veh_ne_wn_base_032"
TARGET_VISIT_ID = 1
TARGET_VISIT_KEY = "veh_ne_wn_base_032:1"
TARGET_INLINK_NAME = "north_east_od_to_northeast_intersection"
SOUTHEAST_OUTLINK_NAME = "northeast_intersection_to_southeast_intersection"
NORTHWEST_OUTLINK_NAME = "northeast_intersection_to_northwest_intersection"
DECISION_TIMESTEP = 600
TRACE_START = 600
TRACE_END = 602
ROUTE_CHANGE_TIMESTEP = 601
BASELINE_PHYSICAL_PASSAGE_TIMESTEP = 602
ACTUAL_PHYSICAL_PASSAGE_TIMESTEP = 602
PASSAGE_CONTEXT_TIMESTEPS = (
    ROUTE_CHANGE_TIMESTEP,
    BASELINE_PHYSICAL_PASSAGE_TIMESTEP,
)
EXPECTED_WORLD_T = 900
WORLD_BASELINE = "baseline"
WORLD_ACTUAL = "actual"
UNTRACED_RNG = "untraced_rng_consumption_between_route_choices"
OBSERVED_HOOK_RNG = "observed_hook_rng_consumption_between_route_choices"
EXPLAINING_HOOKS = ("node_transfer", "record_order_control_node_arrival", "route_pref_update")


class _StopAfterT600Baseline(Exception):
    pass


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.baseline_world = None
        self.baseline_collector = None
        self.baseline_identity_confirmed = False
        self.baseline_timestep_T = None
        self.baseline_target_node_names = None
        self.original_prepare = None
        self.original_align = None
        self.original_driver = None
        self.original_route_choice = None
        self.original_update = None
        self.original_arrival = None
        self.original_route_pref = None
        self.original_transfer = None
        self.original_move = None
        self.driver_entry_rng = None
        self.driver_entry_saved = False
        self.common_origin_rows = []
        self.common_origin_saved = False
        self.rng_read_stable = True
        self.route_calls = []
        self.rng_events = []
        self.passage_context_rows = []
        self.passage_moves = []
        self.next_global_sequence = 1
        self.next_world_sequence = {WORLD_BASELINE: 1, WORLD_ACTUAL: 1}
        self.next_event_index = {WORLD_BASELINE: 1, WORLD_ACTUAL: 1}
        self.analysis = None
        self.stop_after_t600_baseline = False
        self.t600_driver_completed = False


GATE = _Gate()


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        if value is True:
            return "True"
        return "False"
    return str(value)


def _jsonable(value):
    if value is None or type(value) is str or type(value) is bool:
        return value
    if isinstance(value, numbers.Integral) and type(value) is not bool:
        return int(value)
    if isinstance(value, numbers.Real) and type(value) is not bool:
        return float(value)
    if isinstance(value, dict):
        converted = {}
        for key in value:
            converted[str(key)] = _jsonable(value[key])
        return converted
    if isinstance(value, (list, tuple)):
        converted = []
        for item in value:
            converted.append(_jsonable(item))
        return converted
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return _jsonable(tolist())
    raise RuntimeError(
        "RNG state contains a value that cannot be stored as JSON: "
        f"{type(value).__name__}."
    )


def _stable_json(value) -> str:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rng_record(generator):
    bit_generator = generator.bit_generator
    state_copy = copy.deepcopy(bit_generator.state)
    text = _stable_json(state_copy)
    return type(bit_generator).__name__, text, _sha256_text(text)


def _read_rng_pair(world):
    traffic_type, traffic_json, traffic_hash = _rng_record(world.rng)
    order_type, order_json, order_hash = _rng_record(world.order_control_rng)
    return {
        "rng_bit_generator_type": traffic_type,
        "rng_state_json": traffic_json,
        "rng_state_hash": traffic_hash,
        "order_control_rng_bit_generator_type": order_type,
        "order_control_rng_state_json": order_json,
        "order_control_rng_state_hash": order_hash,
    }


def _read_rng_pair_twice(world):
    first = _read_rng_pair(world)
    second = _read_rng_pair(world)
    if first["rng_state_hash"] != second["rng_state_hash"]:
        GATE.rng_read_stable = False
        raise RuntimeError("Reading W.rng state changed its hash.")
    if first["order_control_rng_state_hash"] != second["order_control_rng_state_hash"]:
        GATE.rng_read_stable = False
        raise RuntimeError("Reading W.order_control_rng state changed its hash.")
    return first


def _tracked_kind(world):
    if world is None:
        return None
    if world is GATE.real_world:
        return WORLD_ACTUAL
    if GATE.baseline_world is not None and world is GATE.baseline_world:
        return WORLD_BASELINE
    return None


def _in_trace_window(world) -> bool:
    timestep = getattr(world, "T", None)
    if type(timestep) is not int:
        return False
    if timestep < TRACE_START or timestep > TRACE_END:
        return False
    return True


def _link_name(link):
    if link is None:
        return None
    name = getattr(link, "name", None)
    if name is None:
        return None
    return str(name)


def _node_name(node):
    if node is None:
        return None
    name = getattr(node, "name", None)
    if name is None:
        return None
    return str(name)


def _visit_key(vehicle):
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return None
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return None
    vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        return None
    return f"{vehicle_name}:{visit_id}"


def _link_sort_name(link) -> str:
    return str(getattr(link, "name", ""))


def _join_names(links) -> str:
    names = []
    for link in links:
        names.append(str(getattr(link, "name", "")))
    return "|".join(names)


def _iter_links(world):
    links = getattr(world, "LINKS", None)
    if isinstance(links, dict):
        ordered = []
        for link in links.values():
            ordered.append(link)
        return ordered
    if links is None:
        return []
    ordered = []
    for link in links:
        ordered.append(link)
    return ordered


def _route_pref_by_link_name(vehicle) -> str:
    pref = getattr(vehicle, "route_pref", None)
    pairs = []
    for link in _iter_links(vehicle.W):
        value = None
        if isinstance(pref, dict) and link.id in pref:
            value = _jsonable(pref[link.id])
        pairs.append([str(link.name), value])
    pairs.sort()
    return json.dumps(pairs, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _outlink_registration(node):
    if node is None:
        return []
    outlinks = getattr(node, "outlinks", None)
    if not isinstance(outlinks, dict):
        return []
    ordered = []
    for link in outlinks.values():
        ordered.append(link)
    return ordered


def _preference_value(vehicle, link):
    pref = getattr(vehicle, "route_pref", None)
    if not isinstance(pref, dict):
        return None
    if link.id not in pref:
        return None
    return _jsonable(pref[link.id])


def _candidate_stages(vehicle):
    link = getattr(vehicle, "link", None)
    if link is None:
        return [], [], [], "no_current_link"
    end_node = link.end_node
    registered = _outlink_registration(end_node)
    specified = getattr(vehicle, "specified_route", None)
    if specified is not None:
        return registered, list(registered), list(registered), "specified_route"
    destination = getattr(vehicle, "dest", None)
    if destination == end_node:
        return registered, [], [], "already_at_destination"
    if len(registered) == 0:
        return registered, [], [], "no_outlink"
    after_prefer = list(registered)
    links_prefer = getattr(vehicle, "links_prefer", None)
    if links_prefer is None:
        links_prefer = []
    if set(registered) & set(links_prefer):
        after_prefer = sorted(set(registered) & set(links_prefer), key=_link_sort_name)
    after_avoid = list(after_prefer)
    links_avoid = getattr(vehicle, "links_avoid", None)
    if links_avoid is None:
        links_avoid = []
    if set(after_prefer) & set(links_avoid):
        after_avoid = sorted(set(after_prefer) - set(links_avoid), key=_link_sort_name)
    return registered, after_prefer, after_avoid, "filtered_outlinks"


def _numbers_text(values) -> str:
    parts = []
    for value in values:
        if value is None:
            parts.append("")
        else:
            parts.append(str(value))
    return "|".join(parts)


def _selection_numbers(vehicle, final_links, selection_mode):
    prefs = []
    for link in final_links:
        prefs.append(_preference_value(vehicle, link))
    total = 0.0
    has_number = False
    for value in prefs:
        if isinstance(value, numbers.Real) and type(value) is not bool:
            total = total + float(value)
            has_number = True
    probabilities = []
    if selection_mode == "hard_deterministic" or selection_mode == "specified_route":
        probabilities = []
    elif selection_mode == "weighted_rng" and has_number is True and total > 0:
        for value in prefs:
            probabilities.append(float(value) / total)
    elif selection_mode == "uniform_rng" and len(final_links) > 0:
        share = 1.0 / float(len(final_links))
        index = 0
        while index < len(final_links):
            probabilities.append(share)
            index = index + 1
    return prefs, total if has_number else None, probabilities


def _selection_mode(vehicle, final_links, stage_name) -> str:
    if stage_name == "specified_route":
        return "specified_route"
    if stage_name != "filtered_outlinks":
        return stage_name
    if len(final_links) == 0:
        return "no_outlink"
    if vehicle.W.hard_deterministic_mode == False:
        prefs, total, _probabilities = _selection_numbers(vehicle, final_links, "weighted_rng")
        if total is not None and total > 0:
            return "weighted_rng"
        return "uniform_rng"
    return "hard_deterministic"


def _entry_open(link, world):
    if link is None or world is None:
        return None
    vehicles = getattr(link, "vehicles", None)
    if vehicles is None:
        return None
    lane_count = getattr(link, "number_of_lanes", None)
    if type(lane_count) is not int or type(lane_count) is bool:
        return None
    if len(vehicles) < lane_count:
        return True
    entrance_vehicle = vehicles[-lane_count]
    delta = getattr(link, "delta_per_lane", None)
    deltan = getattr(world, "DELTAN", None)
    if delta is None or deltan is None:
        return None
    if entrance_vehicle.x <= delta * deltan:
        return False
    return True


def _entrance_names(link) -> str:
    vehicles = getattr(link, "vehicles", None)
    if vehicles is None:
        return ""
    lane_count = getattr(link, "number_of_lanes", None)
    if type(lane_count) is not int or type(lane_count) is bool or lane_count < 1:
        return ""
    if len(vehicles) < lane_count:
        return ""
    names = []
    index = len(vehicles) - lane_count
    while index < len(vehicles):
        names.append(str(getattr(vehicles[index], "name", "")))
        index = index + 1
    return "|".join(names)


def _clearance_satisfied(node, inlink):
    if node is None or inlink is None:
        return None
    last_inlink = node.last_order_control_inlink
    last_timestep = node.last_order_control_entry_timestep
    if (last_inlink is None) != (last_timestep is None):
        return None
    if last_inlink is None:
        return True
    if inlink is last_inlink:
        return True
    if type(node.W.T) is not int or type(last_timestep) is not int:
        return None
    gap = node.W.T - last_timestep
    return gap > node.order_control_clearance_timesteps


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


def _specified_route_names(vehicle) -> str:
    specified = getattr(vehicle, "specified_route", None)
    if specified is None:
        return ""
    return _join_names(specified)


def _same_value(left, right) -> bool:
    if type(left) is bool or type(right) is bool:
        return left == right
    if isinstance(left, numbers.Real) and isinstance(right, numbers.Real):
        return float(left) == float(right)
    return left == right


def _target_vehicle(world):
    vehicles = getattr(world, "VEHICLES", None)
    if not isinstance(vehicles, dict):
        return None
    return vehicles.get(TARGET_VEHICLE_NAME)


def _common_origin_row(world, world_kind, rng_record):
    node = world.get_node(TARGET_NODE_NAME)
    vehicle = _target_vehicle(world)
    if vehicle is None:
        raise RuntimeError(f"{world_kind} common origin has no {TARGET_VEHICLE_NAME}.")
    return {
        "world_kind": world_kind,
        "world_object_id": id(world),
        "world_timestep": world.T,
        "rng_bit_generator_type": rng_record["rng_bit_generator_type"],
        "rng_state_json": rng_record["rng_state_json"],
        "rng_state_hash": rng_record["rng_state_hash"],
        "order_control_rng_bit_generator_type": rng_record["order_control_rng_bit_generator_type"],
        "order_control_rng_state_json": rng_record["order_control_rng_state_json"],
        "order_control_rng_state_hash": rng_record["order_control_rng_state_hash"],
        "driver_entry_rng_state_hash": None,
        "vehicle_name": vehicle.name,
        "vehicle_id": getattr(vehicle, "id", None),
        "visit_key": _visit_key(vehicle),
        "current_link_name": _link_name(getattr(vehicle, "link", None)),
        "position_x": getattr(vehicle, "x", None),
        "route_pref_by_link_name_json": _route_pref_by_link_name(vehicle),
        "route_next_link_name": _link_name(getattr(vehicle, "route_next_link", None)),
        "outlink_registration_order": _join_names(_outlink_registration(node)),
    }


def _capture_common_origin(real_world, baseline_world) -> None:
    if GATE.common_origin_saved is True:
        raise RuntimeError("T=600 common origin was captured more than once.")
    if baseline_world is real_world:
        raise RuntimeError("Baseline fork World is the real World object.")
    actual_rng = _read_rng_pair_twice(real_world)
    baseline_rng = _read_rng_pair_twice(baseline_world)
    actual_row = _common_origin_row(real_world, WORLD_ACTUAL, actual_rng)
    baseline_row = _common_origin_row(baseline_world, WORLD_BASELINE, baseline_rng)
    if GATE.driver_entry_rng is not None:
        actual_row["driver_entry_rng_state_hash"] = GATE.driver_entry_rng["rng_state_hash"]
        baseline_row["driver_entry_rng_state_hash"] = GATE.driver_entry_rng["rng_state_hash"]
    GATE.common_origin_rows = [baseline_row, actual_row]
    GATE.common_origin_saved = True


def _note_rng_event(world, kind, before_record, after_record, vehicle_name):
    world_kind = _tracked_kind(world)
    if world_kind is None or _in_trace_window(world) is not True:
        return None
    event_index = GATE.next_event_index[world_kind]
    GATE.next_event_index[world_kind] = event_index + 1
    GATE.rng_events.append(
        {
            "world_kind": world_kind,
            "event_index": event_index,
            "kind": kind,
            "world_timestep": world.T,
            "vehicle_name": vehicle_name,
            "rng_before_hash": before_record["rng_state_hash"],
            "rng_after_hash": after_record["rng_state_hash"],
        }
    )
    return event_index


def _append_route_call(world, world_kind, before_record, after_record, vehicle, stages, before_route, event_index) -> None:
    registered, after_prefer, after_avoid, stage_name = stages
    final_links = after_avoid
    selection_mode = _selection_mode(vehicle, final_links, stage_name)
    prefs, total, probabilities = _selection_numbers(vehicle, final_links, selection_mode)
    after_route = _link_name(getattr(vehicle, "route_next_link", None))
    global_sequence = GATE.next_global_sequence
    GATE.next_global_sequence = global_sequence + 1
    world_sequence = GATE.next_world_sequence[world_kind]
    GATE.next_world_sequence[world_kind] = world_sequence + 1
    capacity_values = []
    entry_values = []
    entrance_values = []
    pref_defined = []
    ids = []
    for link in final_links:
        ids.append(str(getattr(link, "id", "")))
        capacity_values.append(getattr(link, "capacity_in_remain", None))
        entry_values.append(_entry_open(link, world))
        entrance_values.append(_entrance_names(link))
        pref_defined.append(_preference_value(vehicle, link))
    full_pref = ""
    if getattr(vehicle, "name", None) == TARGET_VEHICLE_NAME:
        full_pref = _route_pref_by_link_name(vehicle)
    GATE.route_calls.append(
        {
            "world_kind": world_kind,
            "world_object_id": id(world),
            "world_timestep": world.T,
            "global_sequence": global_sequence,
            "world_sequence": world_sequence,
            "event_index": event_index,
            "vehicle_name": getattr(vehicle, "name", None),
            "vehicle_id": getattr(vehicle, "id", None),
            "visit_key": _visit_key(vehicle),
            "current_link_name": _link_name(getattr(vehicle, "link", None)),
            "current_link_end_node": _node_name(None if vehicle.link is None else vehicle.link.end_node),
            "destination_node": _node_name(getattr(vehicle, "dest", None)),
            "state": getattr(vehicle, "state", None),
            "mode": getattr(vehicle, "mode", None),
            "specified_route_present": getattr(vehicle, "specified_route", None) is not None,
            "specified_route_names": _specified_route_names(vehicle),
            "route_choice_principle": getattr(vehicle, "route_choice_principle", None),
            "hard_deterministic_mode": world.hard_deterministic_mode,
            "links_prefer_names": _join_names(getattr(vehicle, "links_prefer", []) or []),
            "links_avoid_names": _join_names(getattr(vehicle, "links_avoid", []) or []),
            "outlink_registration_order": _join_names(registered),
            "outlinks_after_prefer": _join_names(after_prefer),
            "outlinks_after_avoid": _join_names(after_avoid),
            "final_outlink_names": _join_names(final_links),
            "outlink_ids": "|".join(ids),
            "outlink_route_pref": _numbers_text(pref_defined),
            "route_pref_sum": total,
            "normalized_probabilities": _numbers_text(probabilities),
            "selection_mode": selection_mode,
            "outlink_capacity_in_remain": _numbers_text(capacity_values),
            "outlink_entry_open": _numbers_text(entry_values),
            "outlink_entrance_vehicle_names": "|".join(entrance_values),
            "route_pref_by_link_name_json": full_pref,
            "rng_bit_generator_type": before_record["rng_bit_generator_type"],
            "rng_state_json_before": before_record["rng_state_json"],
            "rng_state_hash_before": before_record["rng_state_hash"],
            "rng_state_json_after": after_record["rng_state_json"],
            "rng_state_hash_after": after_record["rng_state_hash"],
            "rng_state_changed": before_record["rng_state_hash"] != after_record["rng_state_hash"],
            "order_control_rng_state_json_before": before_record["order_control_rng_state_json"],
            "order_control_rng_state_hash_before": before_record["order_control_rng_state_hash"],
            "order_control_rng_state_json_after": after_record["order_control_rng_state_json"],
            "order_control_rng_state_hash_after": after_record["order_control_rng_state_hash"],
            "route_next_link_before": before_route,
            "route_next_link_after": after_route,
            "chosen_outlink_name": after_route,
            "route_changed": before_route != after_route,
        }
    )


def _capture_passage_context(node, world_kind, phase) -> None:
    world = node.W
    vehicle = _target_vehicle(world)
    if vehicle is None:
        return
    inlink = getattr(vehicle, "link", None)
    outlinks = _outlink_registration(node)
    names = []
    capacities = []
    entries = []
    entrances = []
    for link in outlinks:
        names.append(str(link.name))
        capacities.append(getattr(link, "capacity_in_remain", None))
        entries.append(_entry_open(link, world))
        entrances.append(_entrance_names(link))
    incoming_index = _incoming_index(node, vehicle)
    GATE.passage_context_rows.append(
        {
            "world_kind": world_kind,
            "world_object_id": id(world),
            "world_timestep": world.T,
            "phase": phase,
            "vehicle_name": vehicle.name,
            "visit_key": _visit_key(vehicle),
            "current_link_name": _link_name(inlink),
            "position_x": getattr(vehicle, "x", None),
            "route_next_link_name": _link_name(getattr(vehicle, "route_next_link", None)),
            "in_incoming": incoming_index is not None,
            "incoming_index": incoming_index,
            "state": getattr(vehicle, "state", None),
            "node_flow_capacity_remain": getattr(node, "flow_capacity_remain", None),
            "clearance_satisfied": _clearance_satisfied(node, inlink),
            "last_order_control_inlink_name": _link_name(getattr(node, "last_order_control_inlink", None)),
            "last_order_control_entry_timestep": getattr(node, "last_order_control_entry_timestep", None),
            "clearance_timesteps": getattr(node, "order_control_clearance_timesteps", None),
            "inlink_capacity_out_remain": None if inlink is None else getattr(inlink, "capacity_out_remain", None),
            "outlink_registration_order": "|".join(names),
            "outlink_capacity_in_remain": _numbers_text(capacities),
            "outlink_entry_open": _numbers_text(entries),
            "outlink_entrance_vehicle_names": "|".join(entrances),
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
        and real_W.T == DECISION_TIMESTEP
        and apply_copied_tvt_confirmed_ranks is True
    ):
        if GATE.baseline_world is not None:
            raise RuntimeError("T=600 baseline fork was prepared more than once.")
        if prepared.fork_W is real_W:
            raise RuntimeError("Prepared baseline fork is the real World.")
        if prepared.baseline_timestep_T != DECISION_TIMESTEP:
            raise RuntimeError("Prepared baseline timestep is not T=600.")
        GATE.baseline_world = prepared.fork_W
        GATE.baseline_collector = prepared.collector
        _capture_common_origin(real_W, prepared.fork_W)
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
    if real_W is GATE.real_world and real_W.T == DECISION_TIMESTEP:
        fork_result = result.fork_result
        if fork_result.baseline_timestep_T != DECISION_TIMESTEP:
            raise RuntimeError("Aligned baseline fork is not the T=600 fork.")
        if TARGET_NODE_NAME not in fork_result.target_node_names:
            raise RuntimeError("T=600 baseline fork does not include northeast_intersection.")
        if fork_result.collector is not GATE.baseline_collector:
            raise RuntimeError("Aligned baseline collector is not the prepared T=600 collector.")
        GATE.baseline_timestep_T = fork_result.baseline_timestep_T
        GATE.baseline_target_node_names = tuple(fork_result.target_node_names)
        GATE.baseline_identity_confirmed = True
    return result


def wrapped_driver(world):
    if world is GATE.real_world and world.T == DECISION_TIMESTEP:
        if GATE.driver_entry_saved is True:
            raise RuntimeError("T=600 real World driver entry was saved more than once.")
        GATE.driver_entry_rng = _read_rng_pair_twice(world)
        GATE.driver_entry_saved = True
    result = GATE.original_driver(world)
    if world is GATE.real_world and world.T == DECISION_TIMESTEP:
        GATE.t600_driver_completed = True
    if (
        GATE.stop_after_t600_baseline is True
        and world is GATE.real_world
        and world.T == DECISION_TIMESTEP
    ):
        raise _StopAfterT600Baseline()
    return result


def wrapped_route_choice(vehicle):
    world = vehicle.W
    world_kind = _tracked_kind(world)
    tracing = world_kind is not None and _in_trace_window(world) is True
    before_record = None
    stages = None
    before_route = None
    if tracing is True:
        before_record = _read_rng_pair(world)
        before_route = _link_name(getattr(vehicle, "route_next_link", None))
        stages = _candidate_stages(vehicle)
    result = GATE.original_route_choice(vehicle)
    if tracing is True:
        after_record = _read_rng_pair(world)
        event_index = _note_rng_event(
            world,
            "route_next_link_choice",
            before_record,
            after_record,
            getattr(vehicle, "name", None),
        )
        _append_route_call(
            world,
            world_kind,
            before_record,
            after_record,
            vehicle,
            stages,
            before_route,
            event_index,
        )
    return result


def wrapped_vehicle_update(vehicle):
    world = vehicle.W
    world_kind = _tracked_kind(world)
    tracing = world_kind is not None and _in_trace_window(world) is True
    before_record = None
    if tracing is True:
        before_record = _read_rng_pair(world)
    result = GATE.original_update(vehicle)
    if tracing is True:
        after_record = _read_rng_pair(world)
        _note_rng_event(world, "vehicle_update", before_record, after_record, getattr(vehicle, "name", None))
    return result


def wrapped_arrival(vehicle, node):
    world = vehicle.W
    world_kind = _tracked_kind(world)
    tracing = world_kind is not None and _in_trace_window(world) is True
    before_record = None
    if tracing is True:
        before_record = _read_rng_pair(world)
    result = GATE.original_arrival(vehicle, node)
    if tracing is True:
        after_record = _read_rng_pair(world)
        _note_rng_event(
            world,
            "record_order_control_node_arrival",
            before_record,
            after_record,
            getattr(vehicle, "name", None),
        )
    return result


def wrapped_route_pref_update(vehicle, weight=1):
    world = vehicle.W
    world_kind = _tracked_kind(world)
    tracing = world_kind is not None and _in_trace_window(world) is True
    before_record = None
    if tracing is True:
        before_record = _read_rng_pair(world)
    result = GATE.original_route_pref(vehicle, weight)
    if tracing is True:
        after_record = _read_rng_pair(world)
        _note_rng_event(world, "route_pref_update", before_record, after_record, getattr(vehicle, "name", None))
    return result


def wrapped_transfer(node):
    world = node.W
    world_kind = _tracked_kind(world)
    tracing = world_kind is not None and _in_trace_window(world) is True
    passage = (
        tracing is True
        and node.name == TARGET_NODE_NAME
        and world.T in PASSAGE_CONTEXT_TIMESTEPS
    )
    before_record = None
    if tracing is True:
        before_record = _read_rng_pair(world)
    if passage is True:
        _capture_passage_context(node, world_kind, "before_node_passage")
    result = GATE.original_transfer(node)
    if passage is True:
        _capture_passage_context(node, world_kind, "after_node_passage")
    if tracing is True:
        after_record = _read_rng_pair(world)
        _note_rng_event(world, "node_transfer", before_record, after_record, node.name)
    return result


def wrapped_move(node, vehicle, inlink, outlink):
    world_kind = _tracked_kind(node.W)
    tracing = (
        world_kind is not None
        and _in_trace_window(node.W) is True
        and node.name == TARGET_NODE_NAME
        and getattr(vehicle, "name", None) == TARGET_VEHICLE_NAME
    )
    vehicle_name = None
    visit_key = None
    timestep = None
    world_object_id = None
    if tracing is True:
        vehicle_name = vehicle.name
        visit_key = _visit_key(vehicle)
        timestep = node.W.T
        world_object_id = id(node.W)
    result = GATE.original_move(node, vehicle, inlink, outlink)
    if tracing is True:
        GATE.passage_moves.append(
            {
                "world_kind": world_kind,
                "world_object_id": world_object_id,
                "world_timestep": timestep,
                "vehicle_name": vehicle_name,
                "visit_key": visit_key,
                "inlink_name": _link_name(inlink),
                "outlink_name": _link_name(outlink),
            }
        )
    return result


def install_route_choice_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Route choice trace hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_prepare = baseline_driver_module._prepare_baseline_fork
    GATE.original_align = driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_route_choice = uxsim_module.Vehicle.route_next_link_choice
    GATE.original_update = uxsim_module.Vehicle.update
    GATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    GATE.original_route_pref = uxsim_module.Vehicle.route_pref_update
    GATE.original_transfer = uxsim_module.Node.transfer
    GATE.original_move = uxsim_module.Node._transfer_one_vehicle_between_links
    GATE.installed = True
    baseline_driver_module._prepare_baseline_fork = wrapped_prepare_baseline_fork
    driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits = wrapped_align_baseline
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Vehicle.route_next_link_choice = wrapped_route_choice
    uxsim_module.Vehicle.update = wrapped_vehicle_update
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival
    uxsim_module.Vehicle.route_pref_update = wrapped_route_pref_update
    uxsim_module.Node.transfer = wrapped_transfer
    uxsim_module.Node._transfer_one_vehicle_between_links = wrapped_move


def restore_route_choice_hooks() -> None:
    if GATE.installed is not True:
        return
    baseline_driver_module._prepare_baseline_fork = GATE.original_prepare
    driver_module.run_snapshot_fixed_baseline_fork_and_align_undetermined_visits = GATE.original_align
    driver_module.run_tvt_mp_driver = GATE.original_driver
    uxsim_module.Vehicle.route_next_link_choice = GATE.original_route_choice
    uxsim_module.Vehicle.update = GATE.original_update
    uxsim_module.Vehicle.record_order_control_node_arrival = GATE.original_arrival
    uxsim_module.Vehicle.route_pref_update = GATE.original_route_pref
    uxsim_module.Node.transfer = GATE.original_transfer
    uxsim_module.Node._transfer_one_vehicle_between_links = GATE.original_move
    GATE.original_prepare = None
    GATE.original_align = None
    GATE.original_driver = None
    GATE.original_route_choice = None
    GATE.original_update = None
    GATE.original_arrival = None
    GATE.original_route_pref = None
    GATE.original_transfer = None
    GATE.original_move = None
    GATE.real_world = None
    GATE.installed = False


def _prepare_trial_world():
    four_cross_trial.SPILLBACK_TIMESTEP_ROWS.clear()
    vot_rng = four_cross_trial.np.random.default_rng(four_cross_trial.VOT_SEED)
    vot_values = four_cross_trial.generate_vehicle_vots(
        vot_rng,
        len(four_cross_trial.VEHICLE_SPECS),
    )
    vot_records = four_cross_trial.build_vehicle_vot_records(
        four_cross_trial.VEHICLE_SPECS,
        vot_values,
    )
    world = four_cross_trial.build_world_and_network()
    four_cross_trial.add_vehicles_to_world(world, four_cross_trial.VEHICLE_SPECS, vot_records)
    world.finalize_scenario()
    if world.TSIZE != four_cross_trial.INTERNAL_TSIZE:
        raise RuntimeError(f"Expected TSIZE=={four_cross_trial.INTERNAL_TSIZE}, got {world.TSIZE}.")
    if world.name != four_cross_trial.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name was not kept.")
    return world


def _calls_for(world_kind):
    rows = []
    for row in GATE.route_calls:
        if row["world_kind"] == world_kind:
            rows.append(row)
    return rows


def _events_for(world_kind):
    rows = []
    for row in GATE.rng_events:
        if row["world_kind"] == world_kind:
            rows.append(row)
    return rows


def _context_row(world_kind, timestep, phase):
    for row in GATE.passage_context_rows:
        if row["world_kind"] != world_kind:
            continue
        if row["world_timestep"] != timestep or row["phase"] != phase:
            continue
        return row
    return None


def _parallel_value(text, name_text, wanted_name):
    if text is None or name_text is None:
        return None
    names = name_text.split("|") if name_text != "" else []
    values = text.split("|") if text != "" else []
    index = 0
    while index < len(names) and index < len(values):
        if names[index] == wanted_name:
            return values[index]
        index = index + 1
    return None


def _require_contiguous_calls() -> None:
    seen_global = set()
    for world_kind in (WORLD_BASELINE, WORLD_ACTUAL):
        rows = _calls_for(world_kind)
        expected = 1
        seen_world = set()
        for row in rows:
            if row["world_sequence"] != expected:
                raise RuntimeError(
                    f"{world_kind} route choice sequence is not contiguous at {row['world_sequence']}."
                )
            if row["world_sequence"] in seen_world:
                raise RuntimeError(f"Duplicate {world_kind} route choice sequence {row['world_sequence']}.")
            if row["global_sequence"] in seen_global:
                raise RuntimeError(f"Duplicate global route choice sequence {row['global_sequence']}.")
            seen_world.add(row["world_sequence"])
            seen_global.add(row["global_sequence"])
            expected = expected + 1
            if row["world_object_id"] == id(GATE.real_world) and world_kind != WORLD_ACTUAL:
                raise RuntimeError("A real World route choice was stored as baseline.")
            if GATE.baseline_world is not None and row["world_object_id"] == id(GATE.baseline_world) and world_kind != WORLD_BASELINE:
                raise RuntimeError("A baseline route choice was stored as actual.")


def _require_common_origin() -> None:
    if GATE.common_origin_saved is not True or len(GATE.common_origin_rows) != 2:
        raise RuntimeError("T=600 common origin RNG snapshot is missing.")
    baseline_row = None
    actual_row = None
    for row in GATE.common_origin_rows:
        if row["world_kind"] == WORLD_BASELINE:
            baseline_row = row
        elif row["world_kind"] == WORLD_ACTUAL:
            actual_row = row
    if baseline_row is None or actual_row is None:
        raise RuntimeError("Common origin rows are not the baseline and actual pair.")
    if baseline_row["world_object_id"] == actual_row["world_object_id"]:
        raise RuntimeError("Baseline and actual common origin share one World object.")
    if baseline_row["rng_state_hash"] != actual_row["rng_state_hash"]:
        raise RuntimeError("Baseline and actual W.rng hashes differ immediately after copy. Output was not written.")
    if baseline_row["rng_state_json"] != actual_row["rng_state_json"]:
        raise RuntimeError("Baseline and actual W.rng JSON differ immediately after copy. Output was not written.")
    if baseline_row["order_control_rng_state_hash"] != actual_row["order_control_rng_state_hash"]:
        raise RuntimeError(
            "Baseline and actual order_control_rng hashes differ immediately after copy. Output was not written."
        )
    if baseline_row["route_pref_by_link_name_json"] != actual_row["route_pref_by_link_name_json"]:
        raise RuntimeError("Target vehicle route_pref differs immediately after copy. Output was not written.")
    if baseline_row["current_link_name"] != actual_row["current_link_name"]:
        raise RuntimeError("Target vehicle current link differs immediately after copy. Output was not written.")
    if baseline_row["current_link_name"] != TARGET_INLINK_NAME:
        raise RuntimeError(
            "Target vehicle is not on north_east_od_to_northeast_intersection immediately after copy. "
            "Output was not written."
        )
    if baseline_row["visit_key"] != TARGET_VISIT_KEY or actual_row["visit_key"] != TARGET_VISIT_KEY:
        raise RuntimeError("Target VisitKey differs from veh_ne_wn_base_032:1 immediately after copy. Output was not written.")
    if _same_value(baseline_row["position_x"], actual_row["position_x"]) is not True:
        raise RuntimeError("Target vehicle position differs immediately after copy. Output was not written.")
    if baseline_row["outlink_registration_order"] != actual_row["outlink_registration_order"]:
        raise RuntimeError("Northeast outlink registration order differs immediately after copy. Output was not written.")
    if baseline_row["route_next_link_name"] != actual_row["route_next_link_name"]:
        raise RuntimeError("Target route_next_link differs immediately after copy. Output was not written.")
    if baseline_row["vehicle_id"] != actual_row["vehicle_id"]:
        raise RuntimeError("Target vehicle id differs immediately after copy. Output was not written.")


def _baseline_snapshot():
    if GATE.baseline_collector is None:
        raise RuntimeError("T=600 baseline collector is missing.")
    snapshot = GATE.baseline_collector.get_baseline_visit_snapshot(
        TARGET_VEHICLE_NAME,
        TARGET_VISIT_ID,
    )
    if snapshot is None:
        raise RuntimeError("T=600 baseline collector has no veh_ne_wn_base_032:1.")
    return snapshot


def _require_passages() -> None:
    snapshot = _baseline_snapshot()
    if snapshot["baseline_passage_timestep"] != BASELINE_PHYSICAL_PASSAGE_TIMESTEP:
        raise RuntimeError(
            "T=600 baseline snapshot mismatch for veh_ne_wn_base_032:1: "
            f"baseline_passage_timestep={snapshot['baseline_passage_timestep']!r}, "
            f"expected_baseline_physical_passage={BASELINE_PHYSICAL_PASSAGE_TIMESTEP!r}; "
            f"baseline_passage_route_next_link_name="
            f"{snapshot['baseline_passage_route_next_link_name']!r}; "
            f"route_next_link_name={snapshot['route_next_link_name']!r}; "
            f"baseline_arrival_timestep={snapshot['baseline_arrival_timestep']!r}; "
            f"arrival_tiebreaker={snapshot['arrival_tiebreaker']!r}."
        )
    if snapshot["baseline_passage_route_next_link_name"] != SOUTHEAST_OUTLINK_NAME:
        raise RuntimeError("Baseline physical passage route is not southeast.")
    before_actual = _context_row(WORLD_ACTUAL, ROUTE_CHANGE_TIMESTEP, "before_node_passage")
    if before_actual is None:
        raise RuntimeError("Actual T=601 before-transfer snapshot is missing.")
    if before_actual["route_next_link_name"] != NORTHWEST_OUTLINK_NAME:
        raise RuntimeError("Actual T=601 pre-scan route is not northwest.")
    actual_move = None
    for row in GATE.passage_moves:
        if row["world_kind"] != WORLD_ACTUAL:
            continue
        if row["world_timestep"] != ACTUAL_PHYSICAL_PASSAGE_TIMESTEP:
            continue
        if actual_move is not None:
            raise RuntimeError("Actual target vehicle passed more than once at T=602.")
        actual_move = row
    if actual_move is None:
        raise RuntimeError("Actual target vehicle did not pass at T=602.")
    if actual_move["outlink_name"] != SOUTHEAST_OUTLINK_NAME:
        raise RuntimeError("Actual T=602 passage route is not southeast.")


def _input_signature(row):
    return (
        row["vehicle_name"],
        row["visit_key"],
        row["current_link_name"],
        row["final_outlink_names"],
        row["outlink_route_pref"],
        row["outlink_registration_order"],
        row["outlinks_after_prefer"],
        row["outlinks_after_avoid"],
        row["hard_deterministic_mode"],
        row["specified_route_present"],
        row["specified_route_names"],
        row["links_prefer_names"],
        row["links_avoid_names"],
    )


def _explaining_events_between(world_kind, start_event_index, end_event_index):
    found = []
    for event in _events_for(world_kind):
        if event["event_index"] <= start_event_index or event["event_index"] >= end_event_index:
            continue
        if event["kind"] not in EXPLAINING_HOOKS:
            continue
        found.append(event)
    return found


def _chain_status(start_hash, end_hash, events):
    if start_hash == end_hash and len(events) == 0:
        return False, []
    cursor = start_hash
    unexplained = False
    changed_names = []
    for event in events:
        if event["rng_before_hash"] != cursor:
            unexplained = True
        if event["rng_before_hash"] != event["rng_after_hash"]:
            changed_names.append(event["kind"])
        cursor = event["rng_after_hash"]
    if cursor != end_hash:
        unexplained = True
    return unexplained, changed_names


def _route_event_index(world_kind, world_sequence):
    for row in _calls_for(world_kind):
        if row["world_sequence"] == world_sequence:
            return row["event_index"]
    return None


def _build_rng_transitions():
    transitions = []
    for world_kind in (WORLD_BASELINE, WORLD_ACTUAL):
        calls = _calls_for(world_kind)
        if len(calls) == 0:
            continue
        origin = None
        for row in GATE.common_origin_rows:
            if row["world_kind"] == world_kind:
                origin = row
        if origin is not None:
            first_event = _route_event_index(world_kind, calls[0]["world_sequence"])
            preceding = []
            if first_event is not None:
                preceding = _explaining_events_between(world_kind, 0, first_event)
            unexplained, names = _chain_status(
                origin["rng_state_hash"],
                calls[0]["rng_state_hash_before"],
                preceding,
            )
            if origin["rng_state_hash"] != calls[0]["rng_state_hash_before"]:
                classification = OBSERVED_HOOK_RNG
                if unexplained is True:
                    classification = UNTRACED_RNG
                transitions.append(
                    {
                        "world_kind": world_kind,
                        "from_label": "common_origin",
                        "to_world_sequence": calls[0]["world_sequence"],
                        "from_timestep": origin["world_timestep"],
                        "to_timestep": calls[0]["world_timestep"],
                        "from_vehicle_name": "",
                        "to_vehicle_name": calls[0]["vehicle_name"],
                        "rng_hash_before_gap": origin["rng_state_hash"],
                        "rng_hash_after_gap": calls[0]["rng_state_hash_before"],
                        "intervening_hook_names": "|".join(names),
                        "classification": classification,
                    }
                )
        index = 0
        while index < len(calls) - 1:
            current = calls[index]
            nxt = calls[index + 1]
            if current["rng_state_hash_after"] != nxt["rng_state_hash_before"]:
                current_event = _route_event_index(world_kind, current["world_sequence"])
                next_event = _route_event_index(world_kind, nxt["world_sequence"])
                events = []
                if current_event is not None and next_event is not None:
                    events = _explaining_events_between(world_kind, current_event, next_event)
                unexplained, names = _chain_status(
                    current["rng_state_hash_after"],
                    nxt["rng_state_hash_before"],
                    events,
                )
                classification = OBSERVED_HOOK_RNG
                if unexplained is True:
                    classification = UNTRACED_RNG
                transitions.append(
                    {
                        "world_kind": world_kind,
                        "from_label": str(current["world_sequence"]),
                        "to_world_sequence": nxt["world_sequence"],
                        "from_timestep": current["world_timestep"],
                        "to_timestep": nxt["world_timestep"],
                        "from_vehicle_name": current["vehicle_name"],
                        "to_vehicle_name": nxt["vehicle_name"],
                        "rng_hash_before_gap": current["rng_state_hash_after"],
                        "rng_hash_after_gap": nxt["rng_state_hash_before"],
                        "intervening_hook_names": "|".join(names),
                        "classification": classification,
                    }
                )
            index = index + 1
    return transitions


def _first_order_difference(baseline_calls, actual_calls):
    limit = len(baseline_calls)
    if len(actual_calls) < limit:
        limit = len(actual_calls)
    index = 0
    while index < limit:
        if baseline_calls[index]["vehicle_name"] != actual_calls[index]["vehicle_name"]:
            return {
                "world_sequence": baseline_calls[index]["world_sequence"],
                "baseline_vehicle": baseline_calls[index]["vehicle_name"],
                "actual_vehicle": actual_calls[index]["vehicle_name"],
                "baseline_timestep": baseline_calls[index]["world_timestep"],
                "actual_timestep": actual_calls[index]["world_timestep"],
            }
        index = index + 1
    if len(baseline_calls) != len(actual_calls):
        sequence = limit + 1
        baseline_vehicle = None
        actual_vehicle = None
        baseline_timestep = None
        actual_timestep = None
        if len(baseline_calls) > limit:
            baseline_vehicle = baseline_calls[limit]["vehicle_name"]
            baseline_timestep = baseline_calls[limit]["world_timestep"]
        if len(actual_calls) > limit:
            actual_vehicle = actual_calls[limit]["vehicle_name"]
            actual_timestep = actual_calls[limit]["world_timestep"]
        return {
            "world_sequence": sequence,
            "baseline_vehicle": baseline_vehicle,
            "actual_vehicle": actual_vehicle,
            "baseline_timestep": baseline_timestep,
            "actual_timestep": actual_timestep,
        }
    return None


def _first_aligned_difference(baseline_calls, actual_calls, mode):
    limit = len(baseline_calls)
    if len(actual_calls) < limit:
        limit = len(actual_calls)
    index = 0
    while index < limit:
        baseline_row = baseline_calls[index]
        actual_row = actual_calls[index]
        if baseline_row["vehicle_name"] != actual_row["vehicle_name"]:
            return None
        same_input = _input_signature(baseline_row) == _input_signature(actual_row)
        same_rng = baseline_row["rng_state_hash_before"] == actual_row["rng_state_hash_before"]
        same_choice = baseline_row["chosen_outlink_name"] == actual_row["chosen_outlink_name"]
        same_candidates = (
            baseline_row["final_outlink_names"] == actual_row["final_outlink_names"]
            and baseline_row["outlink_route_pref"] == actual_row["outlink_route_pref"]
        )
        matched = False
        if mode == "same_input_different_rng" and same_input is True and same_rng is not True:
            matched = True
        if mode == "same_rng_different_candidates" and same_rng is True and same_candidates is not True:
            matched = True
        if mode == "same_input_same_rng_different_choice" and same_input is True and same_rng is True and same_choice is not True:
            matched = True
        if matched is True:
            return {
                "world_sequence": baseline_row["world_sequence"],
                "vehicle_name": baseline_row["vehicle_name"],
                "baseline_choice": baseline_row["chosen_outlink_name"],
                "actual_choice": actual_row["chosen_outlink_name"],
                "baseline_rng_before": baseline_row["rng_state_hash_before"],
                "actual_rng_before": actual_row["rng_state_hash_before"],
            }
        index = index + 1
    return None


def _target_calls(world_kind):
    rows = []
    for row in _calls_for(world_kind):
        if row["vehicle_name"] == TARGET_VEHICLE_NAME and row["visit_key"] == TARGET_VISIT_KEY:
            rows.append(row)
    return rows


def _call_brief(row):
    return (
        f"T={row['world_timestep']} world_sequence={row['world_sequence']} "
        f"before={row['route_next_link_before']} after={row['chosen_outlink_name']} "
        f"mode={row['selection_mode']} pref={row['outlink_route_pref']} "
        f"prob={row['normalized_probabilities']} "
        f"rng_before={row['rng_state_hash_before']}"
    )


def _cause_for_target(order_difference, same_input_rng, same_rng_candidates, same_input_choice, transitions):
    if same_input_choice is not None:
        return "未確定", "同じ入力と同じRNG beforeなのに選択結果が異なる呼出しがある。"
    if order_difference is not None and (
        same_input_rng is None or order_difference["world_sequence"] <= same_input_rng["world_sequence"]
    ):
        return (
            "route choice呼出し順差",
            f"world sequence {order_difference['world_sequence']} で呼出しVehicleが最初に異なる。",
        )
    if same_rng_candidates is not None and (
        same_input_rng is None or same_rng_candidates["world_sequence"] <= same_input_rng["world_sequence"]
    ):
        return (
            "outlink候補順差",
            f"world sequence {same_rng_candidates['world_sequence']} で同じRNG beforeに対し候補またはroute_prefが異なる。",
        )
    if same_input_rng is not None:
        untraced_before = False
        for row in transitions:
            if row["classification"] != UNTRACED_RNG:
                continue
            to_sequence = row["to_world_sequence"]
            if type(to_sequence) is int and to_sequence <= same_input_rng["world_sequence"]:
                untraced_before = True
        if untraced_before is True:
            return (
                "route choice以前の未追跡RNG消費",
                "対象のRNG beforeが分かれるまでに、route choice以外のhookでは説明できないRNG hash変化がある。",
            )
        return (
            "RNG状態差",
            f"world sequence {same_input_rng['world_sequence']} で同じVehicleと同じ入力なのにRNG beforeが異なる。",
        )
    return "未確定", "観測したroute choice列からは、一意の分岐原因を特定できない。"


def _target_pair_cause(baseline_call, actual_call):
    if baseline_call is None or actual_call is None:
        return "未確定"
    if baseline_call["specified_route_present"] != actual_call["specified_route_present"]:
        return "specified_route差"
    if baseline_call["specified_route_names"] != actual_call["specified_route_names"]:
        return "specified_route差"
    if baseline_call["hard_deterministic_mode"] != actual_call["hard_deterministic_mode"]:
        return "hard deterministic mode差"
    if (
        baseline_call["links_prefer_names"] != actual_call["links_prefer_names"]
        or baseline_call["links_avoid_names"] != actual_call["links_avoid_names"]
    ):
        return "links_prefer／avoid差"
    if baseline_call["final_outlink_names"] != actual_call["final_outlink_names"]:
        return "outlink候補順差"
    if baseline_call["outlink_route_pref"] != actual_call["outlink_route_pref"]:
        return "route_pref差"
    if baseline_call["rng_state_hash_before"] != actual_call["rng_state_hash_before"]:
        return "RNG状態差"
    if baseline_call["chosen_outlink_name"] != actual_call["chosen_outlink_name"]:
        return "未確定"
    return "未確定"


def _choice_reason(row):
    if row is None:
        return "呼出しが記録されていない。"
    chosen = row["chosen_outlink_name"]
    if row["selection_mode"] == "specified_route":
        return f"specified_routeにより {chosen} が選ばれた。"
    if row["selection_mode"] == "hard_deterministic":
        return (
            f"hard_deterministic_modeのため、保存route_prefの最大outlink {chosen} が選ばれた。"
            f" route_pref={row['outlink_route_pref']}。"
        )
    if row["selection_mode"] == "weighted_rng":
        return (
            f"productionのrng.choiceが、outlink順 {row['final_outlink_names']} と"
            f"確率 {row['normalized_probabilities']} で {chosen} を選んだ。"
            "確率の再抽選はしていない。"
        )
    if row["selection_mode"] == "uniform_rng":
        return (
            f"route_pref合計が0以下のため、productionのrng.choiceが等確率で {chosen} を選んだ。"
            "再抽選はしていない。"
        )
    return f"selection_mode={row['selection_mode']} で {chosen} が記録された。理由は未確定。"


def _find_choice(rows, chosen_name, previous_name):
    for row in rows:
        if previous_name is None and row["chosen_outlink_name"] == chosen_name:
            return row
        if previous_name is not None and row["route_next_link_before"] == previous_name and row["chosen_outlink_name"] == chosen_name:
            return row
    return None


def _analyze():
    baseline_calls = _calls_for(WORLD_BASELINE)
    actual_calls = _calls_for(WORLD_ACTUAL)
    transitions = _build_rng_transitions()
    order_difference = _first_order_difference(baseline_calls, actual_calls)
    same_input_rng = _first_aligned_difference(baseline_calls, actual_calls, "same_input_different_rng")
    same_rng_candidates = _first_aligned_difference(baseline_calls, actual_calls, "same_rng_different_candidates")
    same_input_choice = _first_aligned_difference(
        baseline_calls,
        actual_calls,
        "same_input_same_rng_different_choice",
    )
    cause, cause_detail = _cause_for_target(
        order_difference,
        same_input_rng,
        same_rng_candidates,
        same_input_choice,
        transitions,
    )
    baseline_target = _target_calls(WORLD_BASELINE)
    actual_target = _target_calls(WORLD_ACTUAL)
    baseline_southeast = _find_choice(baseline_target, SOUTHEAST_OUTLINK_NAME, None)
    actual_northwest = _find_choice(actual_target, NORTHWEST_OUTLINK_NAME, None)
    actual_southeast = _find_choice(actual_target, SOUTHEAST_OUTLINK_NAME, NORTHWEST_OUTLINK_NAME)
    pair_cause = _target_pair_cause(baseline_southeast, actual_northwest)
    if cause == "未確定" and pair_cause != "未確定":
        cause = pair_cause
        cause_detail = "対象Vehicleのsoutheast選択と呼出しとnorthwest選択と呼出しを比べた結果。"
    GATE.analysis = {
        "transitions": transitions,
        "order_difference": order_difference,
        "same_input_rng": same_input_rng,
        "same_rng_candidates": same_rng_candidates,
        "same_input_choice": same_input_choice,
        "cause": cause,
        "cause_detail": cause_detail,
        "pair_cause": pair_cause,
        "baseline_target": baseline_target,
        "actual_target": actual_target,
        "baseline_southeast": baseline_southeast,
        "actual_northwest": actual_northwest,
        "actual_southeast": actual_southeast,
    }
    return GATE.analysis


def _entrance_sentence(row, outlink_name):
    if row is None:
        return f"{outlink_name} の走査前記録がない。"
    entry = _parallel_value(row["outlink_entry_open"], row["outlink_registration_order"], outlink_name)
    entrance = _parallel_value(
        row["outlink_entrance_vehicle_names"],
        row["outlink_registration_order"],
        outlink_name,
    )
    capacity = _parallel_value(
        row["outlink_capacity_in_remain"],
        row["outlink_registration_order"],
        outlink_name,
    )
    return (
        f"{outlink_name}: entry_open={entry}, entrance_vehicles={entrance}, "
        f"capacity_in_remain={capacity}"
    )


def _summary_text() -> str:
    analysis = GATE.analysis
    baseline_origin = None
    actual_origin = None
    for row in GATE.common_origin_rows:
        if row["world_kind"] == WORLD_BASELINE:
            baseline_origin = row
        if row["world_kind"] == WORLD_ACTUAL:
            actual_origin = row
    snapshot = _baseline_snapshot()
    before_baseline = _context_row(WORLD_BASELINE, ROUTE_CHANGE_TIMESTEP, "before_node_passage")
    before_actual = _context_row(WORLD_ACTUAL, ROUTE_CHANGE_TIMESTEP, "before_node_passage")
    order_difference = analysis["order_difference"]
    if order_difference is None:
        order_text = "T=600〜602の記録範囲では、route choice呼出し順のVehicle名は一致した。"
    else:
        order_text = (
            f"最初の呼出し順差は world sequence {order_difference['world_sequence']}: "
            f"baseline={order_difference['baseline_vehicle']} T={order_difference['baseline_timestep']}, "
            f"actual={order_difference['actual_vehicle']} T={order_difference['actual_timestep']}。"
        )
    driver_entry_text = "driver入口のRNG hashは保存されていない。"
    if actual_origin is not None and actual_origin["driver_entry_rng_state_hash"] is not None:
        if actual_origin["driver_entry_rng_state_hash"] == actual_origin["rng_state_hash"]:
            driver_entry_text = "T=600 driver入口のW.rng hashは、copy直後の実World hashと一致した。"
        else:
            driver_entry_text = "T=600 driver入口のW.rng hashは、copy直後の実World hashと異なる。公式比較はcopy直後の一致を使う。"
    baseline_lines = []
    for row in analysis["baseline_target"]:
        baseline_lines.append("  " + _call_brief(row))
    if len(baseline_lines) == 0:
        baseline_lines.append("  記録なし。")
    actual_lines = []
    for row in analysis["actual_target"]:
        actual_lines.append("  " + _call_brief(row))
    if len(actual_lines) == 0:
        actual_lines.append("  記録なし。")
    southeast_call = analysis["baseline_southeast"]
    northwest_call = analysis["actual_northwest"]
    changed_call = analysis["actual_southeast"]
    if changed_call is None:
        changed_text = "実Worldの記録したroute_next_link_choiceの中に、northwestからsoutheastへ変わる呼出しは無い。"
    else:
        changed_text = "実Worldでnorthwestからsoutheastへ変わった呼出し: " + _call_brief(changed_call)
    entrance_text = (
        "T=601走査前の入口: "
        + _entrance_sentence(before_actual, NORTHWEST_OUTLINK_NAME)
        + "。 "
        + _entrance_sentence(before_actual, SOUTHEAST_OUTLINK_NAME)
        + "。 baseline側: "
        + _entrance_sentence(before_baseline, SOUTHEAST_OUTLINK_NAME)
        + "。"
    )
    if before_actual is not None and before_actual["route_next_link_name"] == NORTHWEST_OUTLINK_NAME:
        entrance_relation = (
            "実WorldはT=601走査前にnorthwestを向いていた。"
            "その入口が閉じていれば、このtimestepの通過できないことと一致する。"
            "入口の開閉は上の観測値で読み、閉じていない場合は入口空間不足をこの分岐の説明に使わない。"
        )
    else:
        entrance_relation = "T=601走査前の実World進路がnorthwestではないため、入口空間との関係は未確定。"
    lines = [
        "T=600 baseline fork と実Worldの route choice trace",
        "反実仮想比較は実装していない。",
        "",
        "copy直後のW.rng状態: 一致。",
        "copy直後のorder_control_rng状態: 一致。",
        "copy直後の対象Vehicle route_pref: 一致。",
        "copy直後のnortheast outlink登録順: 一致。",
        driver_entry_text,
        "baselineと実Worldのroute choice呼出しは、各Worldのworld_sequence順にCSVへ保存した。",
        order_text,
        "対象Vehicleのbaseline route choice:",
    ]
    lines.extend(baseline_lines)
    lines.append("対象Vehicleの実World route choice:")
    lines.extend(actual_lines)
    if southeast_call is None:
        lines.append("baselineがsoutheastを選んだroute choice呼出し: 記録なし。")
    else:
        lines.append("baselineがsoutheastを選んだ理由: " + _choice_reason(southeast_call))
    if northwest_call is None:
        lines.append("実Worldがnorthwestを選んだroute choice呼出し: 記録なし。")
    else:
        lines.append("実Worldがnorthwestを選んだ理由: " + _choice_reason(northwest_call))
    lines.append(changed_text)
    lines.append(f"分岐原因の分類: {analysis['cause']}。")
    lines.append(analysis["cause_detail"])
    lines.append(f"対象のsoutheast呼出しとnorthwest呼出しを直接比べた分類: {analysis['pair_cause']}。")
    lines.append(
        "baseline到着時進路: "
        f"{snapshot['route_next_link_name']}。"
        "baseline物理通過時進路: "
        f"{snapshot['baseline_passage_route_next_link_name']}。"
        "T=601 baseline走査直前live進路: "
        f"{None if before_baseline is None else before_baseline['route_next_link_name']}。"
    )
    lines.append(
        "Candidateのbinding進路は、このbaseline物理通過時進路から後段が得る値である。"
        "この診断はCandidate局所Worldのroute choiceを比較していない。"
    )
    lines.append(entrance_text)
    lines.append(entrance_relation)
    lines.append(
        f"baselineのT={ROUTE_CHANGE_TIMESTEP} route choice: northwestからsoutheastへ変更。"
        f"baseline physical passage: T={BASELINE_PHYSICAL_PASSAGE_TIMESTEP}、southeast方向。"
        f"Actual physical passage: T={ACTUAL_PHYSICAL_PASSAGE_TIMESTEP}、southeast方向。"
    )
    lines.append(
        "後続buyerとsellerへの波及: この診断はbuyerとsellerの通過を再計測していない。"
        "対象Vehicleのbaseline仮想計算と実Worldの物理通過時刻はいずれもT=602である。"
        "後続buyerとsellerの通過差をこのroute choice記録だけで一意に説明できるかは未確定。"
    )
    lines.append("反実仮想比較がなお必要か: 必要。反実仮想比較は実装していない。")
    if analysis["cause"] == "未確定" or analysis["pair_cause"] == "未確定":
        lines.append("一意に説明できない箇所は未確定のまま残す。")
    return "\n".join(lines) + "\n"


COMMON_ORIGIN_COLUMNS = (
    "world_kind",
    "world_object_id",
    "world_timestep",
    "rng_bit_generator_type",
    "rng_state_json",
    "rng_state_hash",
    "order_control_rng_bit_generator_type",
    "order_control_rng_state_json",
    "order_control_rng_state_hash",
    "driver_entry_rng_state_hash",
    "vehicle_name",
    "vehicle_id",
    "visit_key",
    "current_link_name",
    "position_x",
    "route_pref_by_link_name_json",
    "route_next_link_name",
    "outlink_registration_order",
)

ROUTE_CHOICE_COLUMNS = (
    "world_kind",
    "world_object_id",
    "world_timestep",
    "global_sequence",
    "world_sequence",
    "vehicle_name",
    "vehicle_id",
    "visit_key",
    "current_link_name",
    "current_link_end_node",
    "destination_node",
    "state",
    "mode",
    "specified_route_present",
    "specified_route_names",
    "route_choice_principle",
    "hard_deterministic_mode",
    "links_prefer_names",
    "links_avoid_names",
    "outlink_registration_order",
    "outlinks_after_prefer",
    "outlinks_after_avoid",
    "final_outlink_names",
    "outlink_ids",
    "outlink_route_pref",
    "route_pref_sum",
    "normalized_probabilities",
    "selection_mode",
    "outlink_capacity_in_remain",
    "outlink_entry_open",
    "outlink_entrance_vehicle_names",
    "route_pref_by_link_name_json",
    "rng_bit_generator_type",
    "rng_state_json_before",
    "rng_state_hash_before",
    "rng_state_json_after",
    "rng_state_hash_after",
    "rng_state_changed",
    "order_control_rng_state_json_before",
    "order_control_rng_state_hash_before",
    "order_control_rng_state_json_after",
    "order_control_rng_state_hash_after",
    "route_next_link_before",
    "route_next_link_after",
    "chosen_outlink_name",
    "route_changed",
)

TRANSITION_COLUMNS = (
    "world_kind",
    "from_label",
    "to_world_sequence",
    "from_timestep",
    "to_timestep",
    "from_vehicle_name",
    "to_vehicle_name",
    "rng_hash_before_gap",
    "rng_hash_after_gap",
    "intervening_hook_names",
    "classification",
)

PASSAGE_COLUMNS = (
    "world_kind",
    "world_object_id",
    "world_timestep",
    "phase",
    "vehicle_name",
    "visit_key",
    "current_link_name",
    "position_x",
    "route_next_link_name",
    "in_incoming",
    "incoming_index",
    "state",
    "node_flow_capacity_remain",
    "clearance_satisfied",
    "last_order_control_inlink_name",
    "last_order_control_entry_timestep",
    "clearance_timesteps",
    "inlink_capacity_out_remain",
    "outlink_registration_order",
    "outlink_capacity_in_remain",
    "outlink_entry_open",
    "outlink_entrance_vehicle_names",
)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cells = {}
            for column in columns:
                cells[column] = _csv_cell(row.get(column))
            writer.writerow(cells)


def _early_stop_snapshot_document(snapshot: dict) -> dict:
    visit_key = f"{snapshot['vehicle_name']}:{snapshot['visit_id']}"
    return {
        "vehicle_name": snapshot["vehicle_name"],
        "visit_id": snapshot["visit_id"],
        "visit_key": visit_key,
        "baseline_arrival_timestep": snapshot["baseline_arrival_timestep"],
        "arrival_tiebreaker": snapshot["arrival_tiebreaker"],
        "route_next_link_name": snapshot["route_next_link_name"],
        "baseline_passage_timestep": snapshot["baseline_passage_timestep"],
        "baseline_passage_route_next_link_name": snapshot["baseline_passage_route_next_link_name"],
    }


def _require_baseline_fork_route_choice_sequence() -> None:
    rows = _calls_for(WORLD_BASELINE)
    expected = 1
    seen_world = set()
    for row in rows:
        if row["world_sequence"] in seen_world:
            raise RuntimeError(
                f"Duplicate baseline route choice sequence {row['world_sequence']} in the T=600 fork."
            )
        if row["world_sequence"] != expected:
            raise RuntimeError(
                f"Baseline route choice sequence is not contiguous at {row['world_sequence']}."
            )
        seen_world.add(row["world_sequence"])
        expected = expected + 1
        if GATE.baseline_world is not None and row["world_object_id"] != id(GATE.baseline_world):
            raise RuntimeError("A baseline route choice is not from the prepared T=600 fork.")


def _validate_early_stop_runtime(world) -> None:
    if GATE.t600_driver_completed is not True:
        raise RuntimeError("Real World T=600 driver did not complete.")
    if world.T != DECISION_TIMESTEP:
        raise RuntimeError(f"Early stop World.T is {world.T}, expected T=600 after driver.")
    if GATE.driver_entry_saved is not True:
        raise RuntimeError("T=600 driver entry was not recorded.")
    if GATE.baseline_identity_confirmed is not True:
        raise RuntimeError("T=600 baseline fork was not uniquely identified.")
    if GATE.baseline_world is None or GATE.baseline_world is world:
        raise RuntimeError("Baseline World identity is missing or is the real World.")
    if GATE.baseline_collector is None:
        raise RuntimeError("T=600 baseline collector is missing.")
    snapshot = _baseline_snapshot()
    visit_key = f"{snapshot['vehicle_name']}:{snapshot['visit_id']}"
    if visit_key != TARGET_VISIT_KEY:
        raise RuntimeError(f"Snapshot VisitKey is {visit_key!r}, expected {TARGET_VISIT_KEY!r}.")
    passage_timestep = snapshot["baseline_passage_timestep"]
    if type(passage_timestep) is not int or type(passage_timestep) is bool or passage_timestep < 1:
        raise RuntimeError(f"baseline_passage_timestep is not a positive int: {passage_timestep!r}.")
    passage_route = snapshot["baseline_passage_route_next_link_name"]
    if not isinstance(passage_route, str) or passage_route == "":
        raise RuntimeError("baseline_passage_route_next_link_name is empty.")
    arrival_timestep = snapshot["baseline_arrival_timestep"]
    if type(arrival_timestep) is not int or type(arrival_timestep) is bool:
        raise RuntimeError(f"baseline_arrival_timestep is not an int: {arrival_timestep!r}.")
    route_next_link_name = snapshot["route_next_link_name"]
    if not isinstance(route_next_link_name, str) or route_next_link_name == "":
        raise RuntimeError("route_next_link_name is empty.")
    if len(_target_calls(WORLD_BASELINE)) == 0:
        raise RuntimeError("Target vehicle baseline route choice calls are missing in the T=600 fork.")
    _require_baseline_fork_route_choice_sequence()


def _write_early_stop_outputs(world) -> None:
    if EARLY_STOP_OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {EARLY_STOP_OUTPUT_DIR}.")
    if EARLY_STOP_OUTPUT_DIR == four_cross_trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Early-stop output directory is the trial output directory.")
    snapshot = _baseline_snapshot()
    document = _early_stop_snapshot_document(snapshot)
    EARLY_STOP_OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    (EARLY_STOP_OUTPUT_DIR / EARLY_STOP_SNAPSHOT_JSON).write_text(
        json.dumps(_jsonable(document), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        EARLY_STOP_OUTPUT_DIR / EARLY_STOP_TARGET_ROUTE_CHOICE_CSV,
        ROUTE_CHOICE_COLUMNS,
        _target_calls(WORLD_BASELINE),
    )
    _write_csv(
        EARLY_STOP_OUTPUT_DIR / EARLY_STOP_ALL_ROUTE_CHOICE_CSV,
        ROUTE_CHOICE_COLUMNS,
        _calls_for(WORLD_BASELINE),
    )
    manifest = {
        "mode": CLI_STOP_AFTER_T600_BASELINE,
        "stopped_after_t600_baseline": True,
        "full_simulation_completed": False,
        "final_real_world_timestep": world.T,
        "baseline_timestep": DECISION_TIMESTEP,
        "target_node": TARGET_NODE_NAME,
        "target_visit_key": TARGET_VISIT_KEY,
        "output_filenames": list(EARLY_STOP_OUTPUT_FILE_NAMES),
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "generated_at_meaning": "file write time, not a simulation timestep",
    }
    (EARLY_STOP_OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected_names = set(EARLY_STOP_OUTPUT_FILE_NAMES)
    for path in EARLY_STOP_OUTPUT_DIR.iterdir():
        if path.name not in expected_names:
            raise RuntimeError(f"Unexpected early-stop output file {path.name}.")


def _parse_cli_execution_mode() -> str:
    args = sys.argv[1:]
    if len(args) == 0:
        return "full"
    if len(args) != 1:
        raise RuntimeError("CLI modes are mutually exclusive; pass at most one option.")
    option = args[0]
    if option == CLI_STATIC_VALIDATE_ONLY:
        return "static"
    if option == CLI_STOP_AFTER_T600_BASELINE:
        return "early_stop"
    raise RuntimeError(f"Unknown CLI option: {option!r}.")


def _write_outputs(summary_text: str) -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    if OUTPUT_DIR == four_cross_trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory is the trial output directory.")
    target_rows = _target_calls(WORLD_BASELINE)
    for row in _target_calls(WORLD_ACTUAL):
        target_rows.append(row)
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    _write_csv(OUTPUT_DIR / COMMON_ORIGIN_CSV, COMMON_ORIGIN_COLUMNS, GATE.common_origin_rows)
    _write_csv(OUTPUT_DIR / ROUTE_CHOICE_CSV, ROUTE_CHOICE_COLUMNS, GATE.route_calls)
    _write_csv(OUTPUT_DIR / TARGET_ROUTE_CHOICE_CSV, ROUTE_CHOICE_COLUMNS, target_rows)
    _write_csv(OUTPUT_DIR / RNG_TRANSITION_CSV, TRANSITION_COLUMNS, GATE.analysis["transitions"])
    _write_csv(OUTPUT_DIR / PASSAGE_CONTEXT_CSV, PASSAGE_COLUMNS, GATE.passage_context_rows)
    (OUTPUT_DIR / SUMMARY_NAME).write_text(summary_text, encoding="utf-8")
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "diagnostic_script_name": DIAGNOSTIC_SCRIPT_NAME,
        "target_node_name": TARGET_NODE_NAME,
        "target_visit_key": TARGET_VISIT_KEY,
        "decision_timestep": DECISION_TIMESTEP,
        "trace_start": TRACE_START,
        "trace_end": TRACE_END,
        "baseline_world_object_id": None if GATE.baseline_world is None else id(GATE.baseline_world),
        "actual_world_object_id": None if GATE.real_world is None else id(GATE.real_world),
        "output_filenames": list(OUTPUT_FILE_NAMES),
        "counterfactual_route_comparison": "not_implemented",
        "candidate_local_world_comparison": "not_implemented",
        "cause_classification": GATE.analysis["cause"],
        "completion_status": "completed",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "generated_at_meaning": "file write time, not a simulation timestep",
    }
    (OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected_names = set(OUTPUT_FILE_NAMES)
    for path in OUTPUT_DIR.iterdir():
        if path.name not in expected_names:
            raise RuntimeError(f"Unexpected output file {path.name}.")


def _validate_runtime(world) -> None:
    if world.T != EXPECTED_WORLD_T:
        raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T}.")
    evaluation = four_cross_trial.verify_evaluation_end(world)
    if evaluation["world_t_ok"] is not True:
        raise RuntimeError("Evaluation-end check did not pass.")
    if GATE.baseline_identity_confirmed is not True:
        raise RuntimeError("T=600 baseline fork was not uniquely identified.")
    if GATE.baseline_world is None or GATE.baseline_world is world:
        raise RuntimeError("Baseline World identity is missing or is the real World.")
    if GATE.rng_read_stable is not True:
        raise RuntimeError("Diagnostic changed an RNG state while reading it.")
    _require_common_origin()
    _require_contiguous_calls()
    if len(_target_calls(WORLD_BASELINE)) == 0 or len(_target_calls(WORLD_ACTUAL)) == 0:
        raise RuntimeError("Target vehicle route choice calls are missing on one World.")
    _require_passages()
    _analyze()


def _reset_gate() -> None:
    GATE.baseline_world = None
    GATE.baseline_collector = None
    GATE.baseline_identity_confirmed = False
    GATE.baseline_timestep_T = None
    GATE.baseline_target_node_names = None
    GATE.driver_entry_rng = None
    GATE.driver_entry_saved = False
    GATE.common_origin_rows = []
    GATE.common_origin_saved = False
    GATE.rng_read_stable = True
    GATE.route_calls = []
    GATE.rng_events = []
    GATE.passage_context_rows = []
    GATE.passage_moves = []
    GATE.next_global_sequence = 1
    GATE.next_world_sequence = {WORLD_BASELINE: 1, WORLD_ACTUAL: 1}
    GATE.next_event_index = {WORLD_BASELINE: 1, WORLD_ACTUAL: 1}
    GATE.analysis = None
    GATE.stop_after_t600_baseline = False
    GATE.t600_driver_completed = False


def main(mode: str = "full") -> int:
    if mode not in ("full", "early_stop"):
        raise RuntimeError(f"Unsupported execution mode: {mode!r}.")
    stop_after_t600_baseline = mode == "early_stop"
    output_dir = EARLY_STOP_OUTPUT_DIR if stop_after_t600_baseline is True else OUTPUT_DIR
    original_python_recursion_limit = sys.getrecursionlimit()
    _reset_gate()
    GATE.stop_after_t600_baseline = stop_after_t600_baseline
    try:
        if output_dir.exists():
            raise RuntimeError(f"Output directory already exists: {output_dir}.")
        if original_python_recursion_limit < four_cross_trial.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(four_cross_trial.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_trial_world()
        install_route_choice_hooks(world)
        four_cross_trial.install_real_world_spillback_observation(world)
        try:
            try:
                world.exec_simulation()
            except _StopAfterT600Baseline:
                if stop_after_t600_baseline is not True:
                    raise
        finally:
            four_cross_trial.restore_real_world_spillback_observation()
            restore_route_choice_hooks()
        if stop_after_t600_baseline is True:
            _validate_early_stop_runtime(world)
            _write_early_stop_outputs(world)
            print(f"Wrote {EARLY_STOP_OUTPUT_DIR}")
            return 0
        _validate_runtime(world)
        _write_outputs(_summary_text())
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        four_cross_trial.restore_real_world_spillback_observation()
        restore_route_choice_hooks()
        sys.setrecursionlimit(original_python_recursion_limit)


def _function_by_name(tree, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Function {name} is missing.")


def _call_names(function_node) -> list[str]:
    names = []
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                names.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                names.append(node.func.id)
    return names


def _module_level_int_constants(tree: ast.Module) -> dict[str, int]:
    constants: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant):
            continue
        value = node.value.value
        if type(value) is not int or type(value) is bool:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = value
    return constants


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    for module_name in imported:
        if module_name in ("subprocess", "shutil", "git", "os"):
            raise RuntimeError(f"Diagnostic imports {module_name}.")
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
            if node.func.attr == "main":
                raise RuntimeError("Diagnostic calls a main function.")
            if node.func.attr in ("choice", "random", "uniform", "shuffle", "hash"):
                raise RuntimeError(f"Diagnostic calls {node.func.attr}.")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
            if node.func.id in ("eval", "exec", "hash"):
                raise RuntimeError(f"Diagnostic calls {node.func.id}.")
    for name in ("system", "rmtree", "unlink", "rmdir", "eval", "exec"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr in (
                "route_next_link",
                "route_pref",
                "flow_capacity_remain",
                "capacity_out_remain",
                "capacity_in_remain",
                "assigned_rank",
                "state",
                "rng",
                "x",
                "v",
            ):
                raise RuntimeError(f"Diagnostic assigns {target.attr}.")
    if tuple(OUTPUT_FILE_NAMES) != (
        "baseline_actual_common_origin_rng.csv",
        "baseline_actual_route_choice_calls.csv",
        "target_vehicle_route_choice_calls.csv",
        "baseline_actual_rng_transitions.csv",
        "target_vehicle_passage_context.csv",
        "first_route_choice_divergence_summary.txt",
        "manifest.json",
    ):
        raise RuntimeError("Output filenames are not the fixed seven files.")
    if "反実仮想比較は実装していない" not in source:
        raise RuntimeError("Counterfactual comparison is not marked unimplemented.")
    if "candidate_local_world_comparison" not in source:
        raise RuntimeError("Candidate local world comparison is not marked unimplemented.")
    if "world is GATE.real_world" not in source or "world is GATE.baseline_world" not in source:
        raise RuntimeError("Baseline and real World are not identified by object identity.")
    if "sha256" not in source:
        raise RuntimeError("RNG state hash does not use SHA-256.")
    if CLI_STOP_AFTER_T600_BASELINE not in source:
        raise RuntimeError("Early-stop CLI option is missing.")
    if "_StopAfterT600Baseline" not in source:
        raise RuntimeError("Early-stop private exception is missing.")
    if tuple(EARLY_STOP_OUTPUT_FILE_NAMES) != (
        "t600_baseline_target_snapshot.json",
        "t600_baseline_target_route_choice_calls.csv",
        "t600_baseline_all_route_choice_calls.csv",
        "manifest.json",
    ):
        raise RuntimeError("Early-stop output filenames are not the fixed four files.")
    early_stop_validate = _function_by_name(tree, "_validate_early_stop_runtime")
    early_stop_source = ast.get_source_segment(source, early_stop_validate)
    module_constants = _module_level_int_constants(tree)
    for forbidden_name in ("BASELINE_PASSAGE_TIMESTEP", "ACTUAL_PASSAGE_TIMESTEP"):
        if forbidden_name in module_constants:
            raise RuntimeError(f"Ambiguous module constant {forbidden_name} must not exist.")
    expected_constants = {
        "ROUTE_CHANGE_TIMESTEP": 601,
        "BASELINE_PHYSICAL_PASSAGE_TIMESTEP": 602,
        "ACTUAL_PHYSICAL_PASSAGE_TIMESTEP": 602,
    }
    for constant_name, expected_value in expected_constants.items():
        if module_constants.get(constant_name) != expected_value:
            raise RuntimeError(
                f"Module constant {constant_name} must be {expected_value}, "
                f"found {module_constants.get(constant_name)!r}."
            )
    if early_stop_source is None or "BASELINE_PHYSICAL_PASSAGE_TIMESTEP" in early_stop_source:
        raise RuntimeError("Early-stop runtime validation uses fixed baseline physical passage timestep.")
    require_passages = _function_by_name(tree, "_require_passages")
    require_passages_source = ast.get_source_segment(source, require_passages)
    if require_passages_source is None or "BASELINE_PHYSICAL_PASSAGE_TIMESTEP" not in require_passages_source:
        raise RuntimeError("_require_passages does not compare baseline collector to BASELINE_PHYSICAL_PASSAGE_TIMESTEP.")
    transfer_wrapper = _function_by_name(tree, "wrapped_transfer")
    transfer_source = ast.get_source_segment(source, transfer_wrapper)
    if transfer_source is None or "PASSAGE_CONTEXT_TIMESTEPS" not in transfer_source:
        raise RuntimeError("wrapped_transfer does not use PASSAGE_CONTEXT_TIMESTEPS.")
    driver_wrapper = _function_by_name(tree, "wrapped_driver")
    driver_source = ast.get_source_segment(source, driver_wrapper)
    if driver_source is None:
        raise RuntimeError("wrapped_driver source is missing.")
    if "GATE.original_driver(world)" not in driver_source:
        raise RuntimeError("wrapped_driver does not call original_driver.")
    if "_StopAfterT600Baseline" not in driver_source:
        raise RuntimeError("wrapped_driver does not raise the early-stop private exception.")
    original_index = driver_source.index("GATE.original_driver(world)")
    stop_index = driver_source.index("_StopAfterT600Baseline")
    if stop_index < original_index:
        raise RuntimeError("wrapped_driver stops before original_driver completes.")
    main_function = _function_by_name(tree, "main")
    stop_handlers = 0
    for node in ast.walk(main_function):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            continue
        if isinstance(node.type, ast.Name) and node.type.id == "_StopAfterT600Baseline":
            stop_handlers = stop_handlers + 1
    if stop_handlers != 1:
        raise RuntimeError("main() must catch _StopAfterT600Baseline exactly once.")
    main_source = ast.get_source_segment(source, main_function)
    if main_source is None or "_write_early_stop_outputs" not in main_source:
        raise RuntimeError("main() does not write early-stop outputs.")
    if "_require_passages" in early_stop_source:
        raise RuntimeError("Early-stop runtime validation calls full passage checks.")
    main_function = _function_by_name(tree, "main")
    finally_count = 0
    for node in ast.walk(main_function):
        if isinstance(node, ast.Try) and len(node.finalbody) > 0:
            finally_count = finally_count + 1
    if finally_count < 2:
        raise RuntimeError("main() does not restore hooks in finally.")
    main_called = _call_names(main_function)
    if "restore_route_choice_hooks" not in main_called:
        raise RuntimeError("main() does not restore route choice hooks.")
    if "restore_real_world_spillback_observation" not in main_called:
        raise RuntimeError("main() does not restore spillback observation.")
    for wrapper_name in (
        "wrapped_prepare_baseline_fork",
        "wrapped_align_baseline",
        "wrapped_driver",
        "wrapped_route_choice",
        "wrapped_vehicle_update",
        "wrapped_arrival",
        "wrapped_route_pref_update",
        "wrapped_transfer",
        "wrapped_move",
    ):
        wrapper = _function_by_name(tree, wrapper_name)
        original_calls = 0
        for node in ast.walk(wrapper):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("original_"):
                    original_calls = original_calls + 1
        if original_calls != 1:
            raise RuntimeError(f"{wrapper_name} does not call the original once.")
    route_wrapper = _function_by_name(tree, "wrapped_route_choice")
    route_source = ast.get_source_segment(source, route_wrapper)
    if route_source is None or "GATE.original_route_choice(vehicle)" not in route_source:
        raise RuntimeError("route_next_link_choice wrapper does not call the original once.")
    if "route_next_link_choice(" in route_source.replace("GATE.original_route_choice(vehicle)", ""):
        raise RuntimeError("route choice wrapper reruns route_next_link_choice.")
    print("static contract ok")


if __name__ == "__main__":
    mode = _parse_cli_execution_mode()
    if mode == "static":
        validate_static_contract()
    else:
        raise SystemExit(main(mode))
