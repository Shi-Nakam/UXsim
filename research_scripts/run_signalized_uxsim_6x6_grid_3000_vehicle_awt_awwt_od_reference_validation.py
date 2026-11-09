"""
Signalized UXsim 3000-vehicle full completion and OD-based waiting time.

Same vehicle plan, seeds, true VOT, and 2400/600 evaluation cohorts as the
FCFS and TVT-MP formal runs. Internal intersections use signal_setting
[59, 0, 59, 0]. External OD nodes stay unsignalized. Order control is not used.

The script does not import those trial scripts. After full completion it calls
evaluate_network_wide_waiting_time once. AWWT is a VOT-weighted average, not
a value in seconds.

Run from the repository root:

    python research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py --static-validate-only
    python research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py --validate-signal-timing-only
    python research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

from uxsim import World
from uxsim.network_wide_waiting_time_evaluation import (
    evaluate_network_wide_waiting_time,
)

# ---------------------------------------------------------------------------
# 1. Constants. Demand and hashes match the FCFS and TVT-MP formal runs.
# ---------------------------------------------------------------------------

SCENARIO_NAME = (
    "signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_"
    "validation_departure_999_seed_0_demand_seed_42_vot_seed_1_"
    "cohort_seed_3_signal_59_0_59_0"
)
METHOD_NAME = "signalized_uxsim"
PRODUCTION_MODULE_NAME = "uxsim.network_wide_waiting_time_evaluation"
PRODUCTION_ENTRY_POINT = "evaluate_network_wide_waiting_time"

PARTICIPATING_COHORT = "tvt_participating_cohort"
NONPARTICIPATING_COHORT = "tvt_nonparticipating_cohort"

EXPECTED_VEHICLE_PLAN_SHA256 = (
    "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
)
EXPECTED_COHORT_ASSIGNMENT_SHA256 = (
    "240948f02de649c69963f54ae6be0cfc387295517a0c01ea5c0a616cf1fe727c"
)
EXPECTED_NONPARTICIPATING_NAME_SHA256 = (
    "d03652284a7e07af117c0c60b77b627a52d2185c4cd316a7506710f0680d2529"
)
EXPECTED_PARTICIPATING_NAME_SHA256 = (
    "79866a40a53f065634d7766b6c944a3083e19cad5558f0b1c4a1306bbabb9481"
)

NUM_VEHICLES = 3000
NONPARTICIPATING_VEHICLE_COUNT = 600
PARTICIPATING_VEHICLE_COUNT = 2400
COHORT_SEED = 3

DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5

# Safety ceiling only. FCFS formal script allocates tmax=5000 and always
# runs that far. Historical signalized trials with 5000 vehicles used
# tmax=30000 and finished much earlier. This 3000-vehicle demand is lighter
# than those trials. 12000 is not an assumed completion time.
SAFE_LAST_TIMESTEP_CAP = 12000

TRAFFIC_SEED = 0
DEMAND_GEN_SEED = 42
VOT_SEED = 1
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = 36
EXTERNAL_OD_NODE_COUNT = 24

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
REACTION_TIME = 1
DELTAN = 1
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2

# API setting. Effective transfer durations are one timestep longer than a
# positive setting, and a 0 setting lasts one all-red timestep, because
# UXsim advances the phase only when signal_t > signal[phase] and then adds
# DELTAT. Offset uses sum(signal_setting)=118, not the effective 122.
SIGNAL_SETTING = (59, 0, 59, 0)
API_CYCLE_LENGTH = 118
OFFSET_INTERVAL = 29.5
OFFSET_VALUES = (0.0, 29.5, 59.0, 88.5)
INTENDED_EFFECTIVE_PHASE_DURATIONS = (60, 1, 60, 1)
SIGNAL_GROUP_EAST_WEST = 0
SIGNAL_GROUP_NORTH_SOUTH = 2
OFFSET_FORMULA = (
    "((row + column) % 4) * (sum(signal_setting) / 4)"
)

AUDIT_ABS_TOL = 1e-9
WEIGHTED_IDENTITY_ABS_TOL = 1e-6
SECONDS_MATCH_ABS_TOL = 1e-6

VEHICLES_CSV_NAME = "network_wide_waiting_time_vehicles.csv"
COHORTS_CSV_NAME = "network_wide_waiting_time_cohorts.csv"
SUMMARY_JSON_NAME = "network_wide_waiting_time_summary.json"
VOT_COHORT_CSV_NAME = "vehicle_vot_and_cohort.csv"
PLAN_AUDIT_JSON_NAME = "vehicle_plan_audit.json"
SIGNAL_SUMMARY_JSON_NAME = "signal_control_summary.json"
MANIFEST_JSON_NAME = "manifest.json"
RUN_SUMMARY_TXT_NAME = "run_summary.txt"

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
TRIAL_OUTPUT_DIR = REPO_ROOT / "research_outputs" / "trial" / SCENARIO_NAME


# ---------------------------------------------------------------------------
# 2. Network names. Same construction order as the FCFS formal script.
# ---------------------------------------------------------------------------

def _grid_node_name(row: int, column: int) -> str:
    return f"g_{row}_{column}"


def _external_od_node_names() -> tuple[str, ...]:
    names = []
    for column in range(GRID_SIZE):
        names.append(f"top_{column}")
        names.append(f"bottom_{column}")
    for row in range(GRID_SIZE):
        names.append(f"left_{row}")
        names.append(f"right_{row}")
    return tuple(names)


def _internal_grid_node_names() -> tuple[str, ...]:
    names = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            names.append(_grid_node_name(row, column))
    return tuple(names)


def _od_to_grid_coord_map() -> dict[str, tuple[int, int]]:
    mapping = {}
    for column in range(GRID_SIZE):
        mapping[f"top_{column}"] = (0, column)
        mapping[f"bottom_{column}"] = (GRID_SIZE - 1, column)
    for row in range(GRID_SIZE):
        mapping[f"left_{row}"] = (row, 0)
        mapping[f"right_{row}"] = (row, GRID_SIZE - 1)
    return mapping


def signal_offset_for_intersection(row: int, column: int) -> float:
    """Stagger by the API cycle, not by the effective 122-timestep series."""
    return ((row + column) % 4) * (sum(SIGNAL_SETTING) / 4)


def _build_link_specs() -> tuple[tuple, tuple]:
    """East-west entry is group 0. North-south entry is group 2.

    The group is the entry direction at the link end node. Outbound
    connectors use the same direction number so no link receives group 1
    or 3. Their end nodes are unsignalized, so the group does not control
    transfer there.
    """
    internal = []
    connectors = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            internal.append(
                (
                    f"h_{row}_{column}_{column + 1}",
                    left_node,
                    right_node,
                    INTERNAL_LINK_LENGTH,
                    SIGNAL_GROUP_EAST_WEST,
                )
            )
            internal.append(
                (
                    f"h_{row}_{column + 1}_{column}",
                    right_node,
                    left_node,
                    INTERNAL_LINK_LENGTH,
                    SIGNAL_GROUP_EAST_WEST,
                )
            )
    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            internal.append(
                (
                    f"v_{row}_{row + 1}_{column}",
                    upper_node,
                    lower_node,
                    INTERNAL_LINK_LENGTH,
                    SIGNAL_GROUP_NORTH_SOUTH,
                )
            )
            internal.append(
                (
                    f"v_{row + 1}_{row}_{column}",
                    lower_node,
                    upper_node,
                    INTERNAL_LINK_LENGTH,
                    SIGNAL_GROUP_NORTH_SOUTH,
                )
            )
    for column in range(GRID_SIZE):
        top_node = f"top_{column}"
        bottom_node = f"bottom_{column}"
        north_grid = _grid_node_name(0, column)
        south_grid = _grid_node_name(GRID_SIZE - 1, column)
        connectors.append(
            (
                f"top_{column}_to_g_0_{column}",
                top_node,
                north_grid,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_NORTH_SOUTH,
            )
        )
        connectors.append(
            (
                f"g_0_{column}_to_top_{column}",
                north_grid,
                top_node,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_NORTH_SOUTH,
            )
        )
        connectors.append(
            (
                f"bottom_{column}_to_g_5_{column}",
                bottom_node,
                south_grid,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_NORTH_SOUTH,
            )
        )
        connectors.append(
            (
                f"g_5_{column}_to_bottom_{column}",
                south_grid,
                bottom_node,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_NORTH_SOUTH,
            )
        )
    for row in range(GRID_SIZE):
        left_node = f"left_{row}"
        right_node = f"right_{row}"
        west_grid = _grid_node_name(row, 0)
        east_grid = _grid_node_name(row, GRID_SIZE - 1)
        connectors.append(
            (
                f"left_{row}_to_g_{row}_0",
                left_node,
                west_grid,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_EAST_WEST,
            )
        )
        connectors.append(
            (
                f"g_{row}_0_to_left_{row}",
                west_grid,
                left_node,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_EAST_WEST,
            )
        )
        connectors.append(
            (
                f"right_{row}_to_g_{row}_5",
                right_node,
                east_grid,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_EAST_WEST,
            )
        )
        connectors.append(
            (
                f"g_{row}_5_to_right_{row}",
                east_grid,
                right_node,
                OD_CONNECTOR_LENGTH,
                SIGNAL_GROUP_EAST_WEST,
            )
        )
    return tuple(internal), tuple(connectors)


def _manhattan_distance(origin_coord, destination_coord) -> int:
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


INTERNAL_GRID_NODES = _internal_grid_node_names()
EXTERNAL_OD_NODES = _external_od_node_names()
OD_TO_GRID_COORD = _od_to_grid_coord_map()
INTERNAL_LINK_SPECS, OD_CONNECTOR_LINK_SPECS = _build_link_specs()
ALL_LINK_SPECS = INTERNAL_LINK_SPECS + OD_CONNECTOR_LINK_SPECS


# ---------------------------------------------------------------------------
# 3. Vehicle plan, true VOT, and evaluation cohort
# ---------------------------------------------------------------------------

def generate_vehicle_plans() -> list[dict]:
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    vehicle_index = 0
    while len(plans) < NUM_VEHICLES:
        origin = rng.choice(EXTERNAL_OD_NODES)
        destination = rng.choice(EXTERNAL_OD_NODES)
        if origin == destination:
            continue
        origin_grid_coord = OD_TO_GRID_COORD[origin]
        destination_grid_coord = OD_TO_GRID_COORD[destination]
        manhattan_distance = _manhattan_distance(origin_grid_coord, destination_grid_coord)
        if manhattan_distance < MIN_OD_MANHATTAN_DISTANCE:
            continue
        departure_time = DEPARTURE_START + (
            (DEPARTURE_END - DEPARTURE_START) * len(plans) / max(NUM_VEHICLES - 1, 1)
        )
        plans.append(
            {
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time,
                "name": f"veh_{vehicle_index}",
                "origin_grid_coord": origin_grid_coord,
                "destination_grid_coord": destination_grid_coord,
                "manhattan_distance": manhattan_distance,
            }
        )
        vehicle_index = vehicle_index + 1
    return plans


def _vehicle_plan_digest(plans: list[dict]) -> str:
    hasher = hashlib.sha256()
    for plan in plans:
        line = (
            f"{plan['name']}|{plan['origin']}|{plan['destination']}|"
            f"{plan['departure_time']!r}\n"
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def verify_vehicle_plans(plans: list[dict]) -> dict:
    if len(plans) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle plan count is {len(plans)}, expected 3000.")
    external = set(EXTERNAL_OD_NODES)
    departures = []
    previous_departure = None
    for index, plan in enumerate(plans):
        if plan["name"] != f"veh_{index}":
            raise RuntimeError(f"Vehicle plan {index} name is {plan['name']!r}.")
        if plan["origin"] == plan["destination"]:
            raise RuntimeError(f"{plan['name']} origin equals destination.")
        if plan["origin"] not in external or plan["destination"] not in external:
            raise RuntimeError(f"{plan['name']} OD is not external.")
        if plan["manhattan_distance"] < MIN_OD_MANHATTAN_DISTANCE:
            raise RuntimeError(f"{plan['name']} Manhattan distance is too small.")
        departure_time = plan["departure_time"]
        if previous_departure is not None and departure_time < previous_departure:
            raise RuntimeError(f"{plan['name']} departure decreased.")
        previous_departure = departure_time
        departures.append(departure_time)
    if departures[0] != DEPARTURE_START or departures[-1] != DEPARTURE_END:
        raise RuntimeError("Departure window is not 0..999.")
    digest = _vehicle_plan_digest(plans)
    if digest != EXPECTED_VEHICLE_PLAN_SHA256:
        raise RuntimeError(
            f"vehicle_plan_sha256 expected {EXPECTED_VEHICLE_PLAN_SHA256}, got {digest}."
        )
    return {
        "vehicle_plan_sha256": digest,
        "first_departure": departures[0],
        "last_departure": departures[-1],
    }


def _ordered_vehicle_names(plans: list[dict]) -> list[str]:
    names = []
    for plan in plans:
        names.append(plan["name"])
    return names


def select_nonparticipating_names(population: list[str]) -> tuple[str, ...]:
    sampled = set(
        random.Random(COHORT_SEED).sample(
            population,
            NONPARTICIPATING_VEHICLE_COUNT,
        )
    )
    selected = []
    for name in population:
        if name in sampled:
            selected.append(name)
    if len(selected) != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Cohort selection count is {len(selected)}, expected 600.")
    return tuple(selected)


def _participating_names(
    population: list[str],
    nonparticipating_names: tuple[str, ...],
) -> tuple[str, ...]:
    selected = []
    for name in nonparticipating_names:
        selected.append(name)
    names = []
    for name in population:
        if name not in selected:
            names.append(name)
    if len(names) != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Participating cohort count is {len(names)}, expected 2400.")
    return tuple(names)


def _hash_names(names: tuple[str, ...] | list[str]) -> str:
    payload = "\n".join(names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cohort_assignment_digest(plans: list[dict], nonparticipating_names: tuple[str, ...]) -> str:
    """Same bytes as the FCFS participation_assignment_sha256."""
    selected = []
    for name in nonparticipating_names:
        selected.append(name)
    hasher = hashlib.sha256()
    for plan in plans:
        if plan["name"] in selected:
            flag = "nonparticipating"
        else:
            flag = "participating"
        line = f"{plan['name']}|{flag}\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def verify_cohort_hashes(
    plans: list[dict],
    nonparticipating_names: tuple[str, ...],
    participating_names: tuple[str, ...],
) -> dict[str, str]:
    cohort_digest = cohort_assignment_digest(plans, nonparticipating_names)
    nonparticipating_digest = _hash_names(nonparticipating_names)
    participating_digest = _hash_names(participating_names)
    if cohort_digest != EXPECTED_COHORT_ASSIGNMENT_SHA256:
        raise RuntimeError(
            "cohort_assignment_sha256 does not match the FCFS and TVT-MP value. "
            f"got {cohort_digest}."
        )
    if nonparticipating_digest != EXPECTED_NONPARTICIPATING_NAME_SHA256:
        raise RuntimeError("nonparticipating_name_sha256 does not match.")
    if participating_digest != EXPECTED_PARTICIPATING_NAME_SHA256:
        raise RuntimeError("participating_name_sha256 does not match.")
    return {
        "cohort_assignment_sha256": cohort_digest,
        "nonparticipating_name_sha256": nonparticipating_digest,
        "participating_name_sha256": participating_digest,
    }


def generate_true_vot_per_second(count: int) -> list[float]:
    rng = np.random.default_rng(VOT_SEED)
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    values = []
    for value in samples:
        number = float(value)
        if math.isfinite(number) is not True or number <= 0.0:
            raise RuntimeError(f"true VOT sample is not positive and finite: {number!r}.")
        values.append(number)
    if len(values) != count:
        raise RuntimeError(f"true VOT count is {len(values)}, expected {count}.")
    return values


def build_vot_and_cohort_ledgers(
    plans: list[dict],
    vot_values: list[float],
    nonparticipating_names: tuple[str, ...],
) -> tuple[dict[str, float], dict[str, str]]:
    nonparticipating = []
    for name in nonparticipating_names:
        nonparticipating.append(name)
    vot_by_name = {}
    cohort_by_name = {}
    participating_count = 0
    nonparticipating_count = 0
    for plan, vot in zip(plans, vot_values):
        vehicle_name = plan["name"]
        vot_by_name[vehicle_name] = vot
        if vehicle_name in nonparticipating:
            cohort_by_name[vehicle_name] = NONPARTICIPATING_COHORT
            nonparticipating_count = nonparticipating_count + 1
        else:
            cohort_by_name[vehicle_name] = PARTICIPATING_COHORT
            participating_count = participating_count + 1
    if participating_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Participating cohort count is {participating_count}.")
    if nonparticipating_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Nonparticipating cohort count is {nonparticipating_count}.")
    return vot_by_name, cohort_by_name


# ---------------------------------------------------------------------------
# 4. Signalized world. No order control.
# ---------------------------------------------------------------------------

def build_world_and_network() -> World:
    world = World(
        name=SCENARIO_NAME,
        deltan=DELTAN,
        reaction_time=REACTION_TIME,
        tmax=SAFE_LAST_TIMESTEP_CAP,
        random_seed=TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
        show_progress_deltat=600,
    )
    spacing = 1.0
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            offset = signal_offset_for_intersection(row, column)
            world.addNode(
                _grid_node_name(row, column),
                column * spacing,
                -row * spacing,
                signal=list(SIGNAL_SETTING),
                signal_offset=offset,
            )
    for column in range(GRID_SIZE):
        world.addNode(f"top_{column}", column * spacing, spacing)
        world.addNode(f"bottom_{column}", column * spacing, -GRID_SIZE * spacing)
    for row in range(GRID_SIZE):
        world.addNode(f"left_{row}", -spacing, -row * spacing)
        world.addNode(f"right_{row}", GRID_SIZE * spacing, -row * spacing)

    for link_name, start_node, end_node, length, signal_group in ALL_LINK_SPECS:
        world.addLink(
            link_name,
            start_node,
            end_node,
            length=length,
            free_flow_speed=FREE_FLOW_SPEED,
            jam_density=JAM_DENSITY,
            number_of_lanes=NUMBER_OF_LANES,
            merge_priority=MERGE_PRIORITY,
            signal_group=signal_group,
        )
    return world


def verify_signal_and_network(world: World) -> dict:
    if world.DELTAN != 1 or world.DELTAT != 1:
        raise RuntimeError(
            f"DELTAN={world.DELTAN!r} DELTAT={world.DELTAT!r}, expected 1 and 1."
        )
    if len(world.NODES) != INTERNAL_GRID_NODE_COUNT + EXTERNAL_OD_NODE_COUNT:
        raise RuntimeError(f"Node count is {len(world.NODES)}.")
    internal_signalized = 0
    external_unsignalized = 0
    seen_offsets = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            node = world.get_node(_grid_node_name(row, column))
            if list(node.signal) != list(SIGNAL_SETTING):
                raise RuntimeError(f"{node.name} signal is {node.signal!r}.")
            expected_offset = signal_offset_for_intersection(row, column)
            if node.signal_offset != expected_offset:
                raise RuntimeError(
                    f"{node.name} offset is {node.signal_offset!r}, "
                    f"expected {expected_offset!r}."
                )
            if node.order_control_type != "none":
                raise RuntimeError(f"{node.name} order_control_type is not none.")
            seen_offsets.append(node.signal_offset)
            internal_signalized = internal_signalized + 1
    for node_name in EXTERNAL_OD_NODES:
        node = world.get_node(node_name)
        if list(node.signal) != [0]:
            raise RuntimeError(f"External node {node_name} is signalized: {node.signal!r}.")
        if node.order_control_type != "none":
            raise RuntimeError(f"{node_name} order_control_type is not none.")
        external_unsignalized = external_unsignalized + 1
    if internal_signalized != 36 or external_unsignalized != 24:
        raise RuntimeError("Signalized and external node counts are not 36 and 24.")
    unique_offsets = []
    for offset in seen_offsets:
        if offset not in unique_offsets:
            unique_offsets.append(offset)
    unique_offsets.sort()
    if unique_offsets != [0.0, 29.5, 59.0, 88.5]:
        raise RuntimeError(f"Offset values are {unique_offsets!r}.")

    group_counts = {0: 0, 2: 0}
    entering_group_counts = {0: 0, 2: 0}
    internal_names = set(INTERNAL_GRID_NODES)
    for link in world.LINKS:
        group = _single_signal_group(link)
        if group not in (SIGNAL_GROUP_EAST_WEST, SIGNAL_GROUP_NORTH_SOUTH):
            raise RuntimeError(f"Link {link.name} signal_group is {link.signal_group!r}.")
        group_counts[group] = group_counts[group] + 1
        if link.end_node.name in internal_names:
            entering_group_counts[group] = entering_group_counts[group] + 1
        if link.length != 200:
            raise RuntimeError(f"Link {link.name} length is {link.length!r}.")
    return {
        "internal_signalized_node_count": internal_signalized,
        "external_unsignalized_node_count": external_unsignalized,
        "signal_group_0_link_count": group_counts[0],
        "signal_group_2_link_count": group_counts[2],
        "entering_signal_group_0_count": entering_group_counts[0],
        "entering_signal_group_2_count": entering_group_counts[2],
        "signal_group_1_link_count": 0,
        "signal_group_3_link_count": 0,
        "offset_values": unique_offsets,
    }


def add_vehicles_to_world(world: World, plans: list[dict]) -> None:
    """Same addVehicle arguments as the FCFS formal script. No declared VOT."""
    for plan in plans:
        world.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )


def _state_counts(world: World) -> dict[str, int]:
    counts = {"home": 0, "wait": 0, "run": 0, "end": 0}
    for vehicle in world.VEHICLES.values():
        state_value = vehicle.state
        if state_value not in counts:
            raise RuntimeError(f"Vehicle {vehicle.name} state is {state_value!r}.")
        counts[state_value] = counts[state_value] + 1
    return counts


def _single_signal_group(link) -> int:
    group = link.signal_group
    if type(group) is int:
        return group
    if type(group) is list and len(group) == 1 and type(group[0]) is int:
        return group[0]
    raise RuntimeError(f"Link {link.name} signal_group is {group!r}.")


def _link_vehicle_counts(world: World) -> tuple[int, int, int]:
    internal_names = set()
    for spec in INTERNAL_LINK_SPECS:
        internal_names.add(spec[0])
    connector_names = set()
    for spec in OD_CONNECTOR_LINK_SPECS:
        connector_names.add(spec[0])
    internal_count = 0
    connector_count = 0
    total_count = 0
    for link in world.LINKS:
        count = len(link.vehicles)
        total_count = total_count + count
        if link.name in internal_names:
            internal_count = internal_count + count
        elif link.name in connector_names:
            connector_count = connector_count + count
        else:
            raise RuntimeError(f"Unexpected link {link.name}.")
    return internal_count, connector_count, total_count


def _traffic_is_clear(world: World) -> bool:
    if len(world.VEHICLES) != NUM_VEHICLES:
        return False
    counts = _state_counts(world)
    if counts["end"] != NUM_VEHICLES:
        return False
    if counts["home"] != 0 or counts["wait"] != 0 or counts["run"] != 0:
        return False
    _internal, _connector, total = _link_vehicle_counts(world)
    return total == 0


def run_until_full_completion(world: World) -> None:
    """Advance one timestep at a time and stop when the network is empty."""
    if world.DELTAT != 1:
        raise RuntimeError(f"Continuation requires DELTAT=1, got {world.DELTAT!r}.")
    while world.T < SAFE_LAST_TIMESTEP_CAP:
        if _traffic_is_clear(world):
            return
        before = world.T
        until_t = float(before) * float(world.DELTAT)
        world.exec_simulation(until_t=until_t)
        if world.T <= before:
            raise RuntimeError("exec_simulation did not advance World.T.")
    raise RuntimeError(
        "Signalized simulation reached the safe timestep cap "
        f"{SAFE_LAST_TIMESTEP_CAP} before every vehicle finished and the "
        "network emptied. This cap is not an assumed completion time."
    )


def verify_full_completion(world: World, plans: list[dict]) -> dict:
    counts = _state_counts(world)
    if counts["end"] != NUM_VEHICLES:
        raise RuntimeError(f"end count is {counts['end']}, expected 3000.")
    if counts["home"] != 0 or counts["wait"] != 0 or counts["run"] != 0:
        raise RuntimeError(f"Network is not clear. counts={counts}.")
    internal_count, connector_count, total_count = _link_vehicle_counts(world)
    if internal_count != 0 or connector_count != 0 or total_count != 0:
        raise RuntimeError(
            "Links still hold vehicles: "
            f"internal={internal_count}, connector={connector_count}, total={total_count}."
        )
    if world.T < 1:
        raise RuntimeError(f"World.T is {world.T} after completion.")
    evaluation_end = world.T - 1
    reached = 0
    not_reached = 0
    for plan in plans:
        if float(plan["departure_time"]) <= float(evaluation_end):
            reached = reached + 1
        else:
            not_reached = not_reached + 1
    if reached != NUM_VEHICLES or not_reached != 0:
        raise RuntimeError(
            f"Scheduled departure reached {reached}, not reached {not_reached}."
        )
    return {
        "final_world_t": world.T,
        "evaluation_end_timestep": evaluation_end,
        "vehicle_state_counts": counts,
        "internal_link_vehicle_count": internal_count,
        "od_connector_vehicle_count": connector_count,
        "all_link_vehicle_count": total_count,
        "scheduled_departure_reached_count": reached,
        "scheduled_departure_not_reached_count": not_reached,
        "full_trip_completion": True,
        "traffic_clearance_completed": True,
    }


# ---------------------------------------------------------------------------
# 5. Waiting-time evaluation
# ---------------------------------------------------------------------------

def build_comparison_metadata(plan_audit: dict, cohort_hashes: dict, completion: dict) -> dict:
    return {
        "method_name": METHOD_NAME,
        "scenario_name": SCENARIO_NAME,
        "traffic_seed": TRAFFIC_SEED,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "vot_seed": VOT_SEED,
        "cohort_seed": COHORT_SEED,
        "departure_start": DEPARTURE_START,
        "departure_end": DEPARTURE_END,
        "participating_cohort_count": PARTICIPATING_VEHICLE_COUNT,
        "nonparticipating_cohort_count": NONPARTICIPATING_VEHICLE_COUNT,
        "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
        "cohort_assignment_sha256": cohort_hashes["cohort_assignment_sha256"],
        "nonparticipating_name_sha256": cohort_hashes["nonparticipating_name_sha256"],
        "participating_name_sha256": cohort_hashes["participating_name_sha256"],
        "final_world_t": completion["final_world_t"],
        "evaluation_end_timestep": completion["evaluation_end_timestep"],
        "full_completion": True,
        "traffic_clearance": True,
        "signal_setting": list(SIGNAL_SETTING),
        "api_cycle_length": API_CYCLE_LENGTH,
        "effective_phase_durations": list(INTENDED_EFFECTIVE_PHASE_DURATIONS),
        "offset_formula": OFFSET_FORMULA,
        "offset_interval": OFFSET_INTERVAL,
        "offset_values": list(OFFSET_VALUES),
    }


def _finished_world_observation(world: World, ordered_names: list[str]) -> tuple:
    states = []
    for vehicle_name in ordered_names:
        vehicle = world.VEHICLES[vehicle_name]
        states.append((vehicle_name, vehicle.state))
    return (world.T, tuple(states), _link_vehicle_counts(world))


def evaluate_signalized_network_wide_waiting_time(
    world: World,
    ordered_names: list[str],
    true_vot_by_name: dict[str, float],
    cohort_by_name: dict[str, str],
    vehicle_plan_digest: str,
    comparison_metadata: dict,
):
    """The only production waiting-time call. No participation-status ledger."""
    return evaluate_network_wide_waiting_time(
        real_world=world,
        method_name=METHOD_NAME,
        evaluated_vehicle_names=ordered_names,
        true_vot_per_second_by_vehicle_name=true_vot_by_name,
        evaluation_cohort_by_vehicle_name=cohort_by_name,
        vehicle_plan_digest=vehicle_plan_digest,
        comparison_metadata=comparison_metadata,
    )


def _require_close(left: float, right: float, label: str, abs_tol: float) -> None:
    if left == right:
        return
    if math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=abs_tol):
        return
    raise RuntimeError(f"{label} mismatch. left={left!r} right={right!r}.")


def verify_waiting_time_result(
    result,
    plans: list[dict],
    ordered_names: list[str],
    true_vot_by_name: dict[str, float],
    cohort_by_name: dict[str, str],
    plan_digest: str,
    cohort_digest: str,
    world: World,
) -> dict:
    records = result.vehicle_records
    summary = result.summary
    counters = result.counters
    deltat = float(world.DELTAT)
    if len(records) != NUM_VEHICLES or counters.evaluated_vehicle_count != NUM_VEHICLES:
        raise RuntimeError("Evaluated vehicle count is not 3000.")
    if counters.incomplete_vehicle_count != 0:
        raise RuntimeError("The evaluator reported an unfinished vehicle.")
    if summary.method_name != METHOD_NAME:
        raise RuntimeError(f"summary.method_name is {summary.method_name!r}.")
    if result.vehicle_plan_digest != plan_digest:
        raise RuntimeError("Plan digest on the waiting-time result does not match.")
    signature = result.network_free_flow_signature_digest
    if not isinstance(signature, str) or signature == "":
        raise RuntimeError("network_free_flow_signature_digest is empty.")

    plans_by_name = {}
    for plan in plans:
        plans_by_name[plan["name"]] = plan
    record_names = []
    total_od_steps = 0
    total_route_steps = 0
    total_detour_steps = 0
    total_weighted_od = 0.0
    total_weighted_route = 0.0
    total_weighted_detour = 0.0
    cohort_buckets = {}
    cohort_counts = {}
    for record in records:
        record_names.append(record.vehicle_name)
        if record.method_name != METHOD_NAME:
            raise RuntimeError(f"{record.vehicle_name} method_name is not signalized_uxsim.")
        if record.method_specific_participation_status is not None:
            raise RuntimeError(
                f"{record.vehicle_name} has a method-specific participation status."
            )
        if record.true_vot_per_second != true_vot_by_name[record.vehicle_name]:
            raise RuntimeError(f"{record.vehicle_name} true VOT does not match the ledger.")
        if record.evaluation_cohort != cohort_by_name[record.vehicle_name]:
            raise RuntimeError(f"{record.vehicle_name} cohort does not match the ledger.")
        cohort_counts[record.evaluation_cohort] = cohort_counts.get(record.evaluation_cohort, 0) + 1
        plan = plans_by_name[record.vehicle_name]
        expected_departure = int(plan["departure_time"] / deltat)
        if record.actual_departure_timestep != expected_departure:
            raise RuntimeError(
                f"{record.vehicle_name} departure timestep does not match the plan."
            )
        if record.actual_arrival_timestep < record.actual_departure_timestep:
            raise RuntimeError(f"{record.vehicle_name} arrives before departure.")
        trip = record.actual_arrival_timestep - record.actual_departure_timestep
        if record.actual_trip_timesteps != trip:
            raise RuntimeError(f"{record.vehicle_name} trip timesteps are not arrival minus departure.")
        _require_close(
            record.actual_travel_time_s,
            trip * deltat,
            f"{record.vehicle_name} travel time",
            SECONDS_MATCH_ABS_TOL,
        )
        od_steps = record.od_based_waiting_time_timesteps
        route_steps = record.route_conditional_waiting_time_timesteps
        detour_steps = record.detour_time_timesteps
        if od_steps < 0 or route_steps < 0 or detour_steps < 0:
            raise RuntimeError(f"{record.vehicle_name} has a negative wait or detour.")
        if od_steps != route_steps + detour_steps:
            raise RuntimeError(f"{record.vehicle_name} timestep identity failed.")
        _require_close(
            record.weighted_od_based_waiting_time,
            record.weighted_route_conditional_waiting_time + record.weighted_detour_time,
            f"{record.vehicle_name} weighted identity",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
        total_od_steps = total_od_steps + od_steps
        total_route_steps = total_route_steps + route_steps
        total_detour_steps = total_detour_steps + detour_steps
        total_weighted_od = total_weighted_od + record.weighted_od_based_waiting_time
        total_weighted_route = (
            total_weighted_route + record.weighted_route_conditional_waiting_time
        )
        total_weighted_detour = total_weighted_detour + record.weighted_detour_time
        bucket = cohort_buckets.get(record.evaluation_cohort)
        if bucket is None:
            bucket = {"count": 0, "od_s": 0.0, "weighted_od": 0.0}
            cohort_buckets[record.evaluation_cohort] = bucket
        bucket["count"] = bucket["count"] + 1
        bucket["od_s"] = bucket["od_s"] + record.od_based_waiting_time_s
        bucket["weighted_od"] = bucket["weighted_od"] + record.weighted_od_based_waiting_time

    if record_names != ordered_names:
        raise RuntimeError("Waiting-time vehicle order does not match the plan.")
    if cohort_counts[PARTICIPATING_COHORT] != 2400:
        raise RuntimeError("Participating cohort count is not 2400.")
    if cohort_counts[NONPARTICIPATING_COHORT] != 600:
        raise RuntimeError("Nonparticipating cohort count is not 600.")
    rebuilt = []
    for record in records:
        if record.evaluation_cohort == NONPARTICIPATING_COHORT:
            flag = "nonparticipating"
        else:
            flag = "participating"
        rebuilt.append(f"{record.vehicle_name}|{flag}")
    hasher = hashlib.sha256()
    for plan in plans:
        vehicle_name = plan["name"]
        if cohort_by_name[vehicle_name] == NONPARTICIPATING_COHORT:
            flag = "nonparticipating"
        else:
            flag = "participating"
        hasher.update(f"{vehicle_name}|{flag}\n".encode("utf-8"))
    if hasher.hexdigest() != cohort_digest:
        raise RuntimeError("Cohort hash does not match the FCFS and TVT-MP assignment.")

    _require_close(
        summary.average_waiting_time_s,
        summary.total_od_based_waiting_time_s / NUM_VEHICLES,
        "AWT average identity",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.total_od_based_waiting_time_s,
        total_od_steps * deltat,
        "AWT numerator",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.average_weighted_waiting_time,
        summary.total_weighted_od_based_waiting_time / NUM_VEHICLES,
        "AWWT average identity",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.total_weighted_od_based_waiting_time,
        total_weighted_od,
        "AWWT numerator",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.average_waiting_time_s,
        summary.route_conditional_average_waiting_time_s + summary.average_detour_time_s,
        "AWT equals Route-Conditional AWT plus detour",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.average_weighted_waiting_time,
        summary.route_conditional_average_weighted_waiting_time
        + summary.average_weighted_detour_time,
        "AWWT equals Route-Conditional AWWT plus weighted detour",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.total_route_conditional_waiting_time_s,
        total_route_steps * deltat,
        "Route-Conditional numerator",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.total_detour_time_s,
        total_detour_steps * deltat,
        "detour numerator",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.total_weighted_route_conditional_waiting_time,
        total_weighted_route,
        "weighted Route-Conditional numerator",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.total_weighted_detour_time,
        total_weighted_detour,
        "weighted detour numerator",
        WEIGHTED_IDENTITY_ABS_TOL,
    )

    found = {}
    for cohort in summary.cohort_summaries:
        found[cohort.evaluation_cohort] = cohort
        bucket = cohort_buckets[cohort.evaluation_cohort]
        if cohort.vehicle_count != bucket["count"]:
            raise RuntimeError(f"{cohort.evaluation_cohort} count does not match records.")
        _require_close(
            cohort.total_od_based_waiting_time_s,
            bucket["od_s"],
            f"{cohort.evaluation_cohort} OD total",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
        _require_close(
            cohort.total_weighted_od_based_waiting_time,
            bucket["weighted_od"],
            f"{cohort.evaluation_cohort} weighted OD total",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
        _require_close(
            cohort.average_waiting_time_s,
            cohort.total_od_based_waiting_time_s / cohort.vehicle_count,
            f"{cohort.evaluation_cohort} AWT",
            AUDIT_ABS_TOL,
        )
        _require_close(
            cohort.average_weighted_waiting_time,
            cohort.total_weighted_od_based_waiting_time / cohort.vehicle_count,
            f"{cohort.evaluation_cohort} AWWT",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
    return {
        "awt_s": summary.average_waiting_time_s,
        "awwt": summary.average_weighted_waiting_time,
        "route_conditional_awt_s": summary.route_conditional_average_waiting_time_s,
        "route_conditional_awwt": summary.route_conditional_average_weighted_waiting_time,
        "average_detour_time_s": summary.average_detour_time_s,
        "average_weighted_detour_time": summary.average_weighted_detour_time,
        "participating_awt_s": found[PARTICIPATING_COHORT].average_waiting_time_s,
        "participating_awwt": found[PARTICIPATING_COHORT].average_weighted_waiting_time,
        "nonparticipating_awt_s": found[NONPARTICIPATING_COHORT].average_waiting_time_s,
        "nonparticipating_awwt": found[NONPARTICIPATING_COHORT].average_weighted_waiting_time,
        "network_free_flow_signature_digest": signature,
    }


# ---------------------------------------------------------------------------
# 6. Signal timing probe. No 3000-vehicle simulation.
# ---------------------------------------------------------------------------

def _expected_initial_signal_state(signal_setting: tuple[int, ...], signal_offset: float) -> tuple[int, float]:
    """Same initial-phase walk as Node.__init__ in uxsim.py."""
    cycle_length = sum(signal_setting)
    offset = cycle_length - signal_offset
    phase_index = 0
    while True:
        if offset < signal_setting[phase_index]:
            return phase_index, offset
        offset = offset - signal_setting[phase_index]
        phase_index = phase_index + 1
        if phase_index >= len(signal_setting):
            phase_index = 0


def _phase_run_lengths(phases: list[int]) -> list[tuple[int, int]]:
    runs = []
    if len(phases) == 0:
        return runs
    current = phases[0]
    length = 0
    for phase in phases:
        if phase == current:
            length = length + 1
        else:
            runs.append((current, length))
            current = phase
            length = 1
    runs.append((current, length))
    return runs


def _build_signal_probe_world(signal_offset: float) -> World:
    world = World(
        name="signal_timing_probe",
        deltan=1,
        reaction_time=1,
        tmax=400,
        random_seed=0,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
    )
    world.addNode("west", 0, 0)
    world.addNode("north", 1, 1)
    world.addNode(
        "junction",
        1,
        0,
        signal=list(SIGNAL_SETTING),
        signal_offset=signal_offset,
    )
    world.addLink(
        "ew_in",
        "west",
        "junction",
        length=200,
        free_flow_speed=FREE_FLOW_SPEED,
        jam_density=JAM_DENSITY,
        signal_group=SIGNAL_GROUP_EAST_WEST,
    )
    world.addLink(
        "ns_in",
        "north",
        "junction",
        length=200,
        free_flow_speed=FREE_FLOW_SPEED,
        jam_density=JAM_DENSITY,
        signal_group=SIGNAL_GROUP_NORTH_SOUTH,
    )
    return world


def validate_signal_timing_only() -> dict:
    """Measure one cycle of signal_control. Does not build the 3000-vehicle demand."""
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            "Signal timing validation must not use the formal output directory, "
            f"and it already exists: {TRIAL_OUTPUT_DIR}."
        )
    probe = _build_signal_probe_world(0.0)
    junction = probe.get_node("junction")
    if list(junction.signal) != list(SIGNAL_SETTING):
        raise RuntimeError(f"Probe signal is {junction.signal!r}.")
    if junction.signal_phase != 0 or junction.signal_t != 0:
        raise RuntimeError(
            "Offset 0 did not start at phase 0, signal_t 0. "
            f"phase={junction.signal_phase} signal_t={junction.signal_t}."
        )
    groups = []
    for link in probe.LINKS:
        groups.append(_single_signal_group(link))
    if groups != [SIGNAL_GROUP_EAST_WEST, SIGNAL_GROUP_NORTH_SOUTH]:
        raise RuntimeError(f"Probe signal groups are {groups!r}.")
    measured_steps = sum(INTENDED_EFFECTIVE_PHASE_DURATIONS)
    for _step in range(measured_steps):
        junction.signal_control()
    runs = _phase_run_lengths(list(junction.signal_log))
    expected_runs = []
    for phase_index, duration in enumerate(INTENDED_EFFECTIVE_PHASE_DURATIONS):
        expected_runs.append((phase_index, duration))
    if runs != expected_runs:
        raise RuntimeError(
            "Effective phase durations are "
            f"{runs!r}, expected {expected_runs!r}."
        )

    offset_probe = _build_signal_probe_world(OFFSET_INTERVAL)
    offset_node = offset_probe.get_node("junction")
    expected_phase, expected_t = _expected_initial_signal_state(
        SIGNAL_SETTING,
        OFFSET_INTERVAL,
    )
    if expected_phase != 2 or expected_t != 29.5:
        raise RuntimeError(
            "Offset 29.5 was expected to start in phase 2 at signal_t 29.5. "
            f"formula returned phase={expected_phase} signal_t={expected_t}."
        )
    if offset_node.signal_phase != expected_phase or offset_node.signal_t != expected_t:
        raise RuntimeError(
            "Offset 29.5 initial state does not match UXsim's offset walk. "
            f"node phase={offset_node.signal_phase} signal_t={offset_node.signal_t}."
        )
    print("Signal timing validation passed.")
    print("signal_setting: [59, 0, 59, 0]")
    print("effective phase durations: 60, 1, 60, 1")
    print("offset 29.5 initial phase: 2")
    print("offset 29.5 initial signal_t: 29.5")
    return {
        "phase_runs": runs,
        "offset_29_5_initial_phase": offset_node.signal_phase,
        "offset_29_5_initial_signal_t": offset_node.signal_t,
    }


# ---------------------------------------------------------------------------
# 7. Output writers
# ---------------------------------------------------------------------------

def _refuse_existing_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Refusing to overwrite."
        )


def _json_number_list(values) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _json_text_list(values) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _vehicle_field_names() -> list[str]:
    return [
        "scenario_name",
        "method_name",
        "vehicle_name",
        "origin_name",
        "destination_name",
        "evaluation_cohort",
        "method_specific_participation_status",
        "true_vot_per_second",
        "actual_departure_timestep",
        "actual_arrival_timestep",
        "actual_trip_timesteps",
        "actual_travel_time_s",
        "od_reference_signature_digest",
        "od_reference_route_audit_identity",
        "od_reference_departure_timestep",
        "od_reference_arrival_timestep",
        "od_minimum_free_flow_trip_timesteps",
        "od_minimum_free_flow_trip_time_s",
        "route_audit_identity",
        "reference_departure_timestep",
        "reference_arrival_timestep",
        "route_conditional_minimum_trip_timesteps",
        "route_conditional_minimum_trip_time_s",
        "od_based_waiting_time_timesteps",
        "od_based_waiting_time_s",
        "weighted_od_based_waiting_time",
        "route_conditional_waiting_time_timesteps",
        "route_conditional_waiting_time_s",
        "weighted_route_conditional_waiting_time",
        "detour_time_timesteps",
        "detour_time_s",
        "weighted_detour_time",
        "cumulative_waiting_time_timesteps",
        "cumulative_waiting_time_s",
        "weighted_cumulative_waiting_time",
        "physical_route_deltat",
        "physical_route_link_lengths",
        "physical_route_link_free_flow_speeds",
    ]


def _cohort_field_names() -> list[str]:
    return [
        "scenario_name",
        "method_name",
        "evaluation_cohort",
        "vehicle_count",
        "total_od_based_waiting_time_s",
        "average_waiting_time_s",
        "total_weighted_od_based_waiting_time",
        "average_weighted_waiting_time",
        "total_route_conditional_waiting_time_s",
        "route_conditional_average_waiting_time_s",
        "total_weighted_route_conditional_waiting_time",
        "route_conditional_average_weighted_waiting_time",
        "total_detour_time_s",
        "average_detour_time_s",
        "total_weighted_detour_time",
        "average_weighted_detour_time",
        "total_cumulative_waiting_time_s",
        "average_cumulative_waiting_time_s",
        "total_weighted_cumulative_waiting_time",
        "average_weighted_cumulative_waiting_time",
    ]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_vehicle_rows(result) -> list[dict]:
    rows = []
    for record in result.vehicle_records:
        physical_key = record.physical_route_key
        lengths = []
        speeds = []
        for pair in physical_key[1]:
            lengths.append(pair[0])
            speeds.append(pair[1])
        status = record.method_specific_participation_status
        if status is None:
            status_cell = ""
        else:
            status_cell = status
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "method_name": record.method_name,
                "vehicle_name": record.vehicle_name,
                "origin_name": record.origin_name,
                "destination_name": record.destination_name,
                "evaluation_cohort": record.evaluation_cohort,
                "method_specific_participation_status": status_cell,
                "true_vot_per_second": record.true_vot_per_second,
                "actual_departure_timestep": record.actual_departure_timestep,
                "actual_arrival_timestep": record.actual_arrival_timestep,
                "actual_trip_timesteps": record.actual_trip_timesteps,
                "actual_travel_time_s": record.actual_travel_time_s,
                "od_reference_signature_digest": record.od_reference_signature_digest,
                "od_reference_route_audit_identity": _json_text_list(
                    record.od_reference_route_audit_identity
                ),
                "od_reference_departure_timestep": record.od_reference_departure_timestep,
                "od_reference_arrival_timestep": record.od_reference_arrival_timestep,
                "od_minimum_free_flow_trip_timesteps": record.od_minimum_free_flow_trip_timesteps,
                "od_minimum_free_flow_trip_time_s": record.od_minimum_free_flow_trip_time_s,
                "route_audit_identity": _json_text_list(record.route_audit_identity),
                "reference_departure_timestep": record.reference_departure_timestep,
                "reference_arrival_timestep": record.reference_arrival_timestep,
                "route_conditional_minimum_trip_timesteps": (
                    record.route_conditional_minimum_trip_timesteps
                ),
                "route_conditional_minimum_trip_time_s": (
                    record.route_conditional_minimum_trip_time_s
                ),
                "od_based_waiting_time_timesteps": record.od_based_waiting_time_timesteps,
                "od_based_waiting_time_s": record.od_based_waiting_time_s,
                "weighted_od_based_waiting_time": record.weighted_od_based_waiting_time,
                "route_conditional_waiting_time_timesteps": (
                    record.route_conditional_waiting_time_timesteps
                ),
                "route_conditional_waiting_time_s": record.route_conditional_waiting_time_s,
                "weighted_route_conditional_waiting_time": (
                    record.weighted_route_conditional_waiting_time
                ),
                "detour_time_timesteps": record.detour_time_timesteps,
                "detour_time_s": record.detour_time_s,
                "weighted_detour_time": record.weighted_detour_time,
                "cumulative_waiting_time_timesteps": record.cumulative_waiting_time_timesteps,
                "cumulative_waiting_time_s": record.cumulative_waiting_time_s,
                "weighted_cumulative_waiting_time": record.weighted_cumulative_waiting_time,
                "physical_route_deltat": physical_key[0],
                "physical_route_link_lengths": _json_number_list(lengths),
                "physical_route_link_free_flow_speeds": _json_number_list(speeds),
            }
        )
    return rows


def build_cohort_rows(result) -> list[dict]:
    rows = []
    for cohort in result.summary.cohort_summaries:
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "method_name": result.summary.method_name,
                "evaluation_cohort": cohort.evaluation_cohort,
                "vehicle_count": cohort.vehicle_count,
                "total_od_based_waiting_time_s": cohort.total_od_based_waiting_time_s,
                "average_waiting_time_s": cohort.average_waiting_time_s,
                "total_weighted_od_based_waiting_time": cohort.total_weighted_od_based_waiting_time,
                "average_weighted_waiting_time": cohort.average_weighted_waiting_time,
                "total_route_conditional_waiting_time_s": (
                    cohort.total_route_conditional_waiting_time_s
                ),
                "route_conditional_average_waiting_time_s": (
                    cohort.route_conditional_average_waiting_time_s
                ),
                "total_weighted_route_conditional_waiting_time": (
                    cohort.total_weighted_route_conditional_waiting_time
                ),
                "route_conditional_average_weighted_waiting_time": (
                    cohort.route_conditional_average_weighted_waiting_time
                ),
                "total_detour_time_s": cohort.total_detour_time_s,
                "average_detour_time_s": cohort.average_detour_time_s,
                "total_weighted_detour_time": cohort.total_weighted_detour_time,
                "average_weighted_detour_time": cohort.average_weighted_detour_time,
                "total_cumulative_waiting_time_s": cohort.total_cumulative_waiting_time_s,
                "average_cumulative_waiting_time_s": cohort.average_cumulative_waiting_time_s,
                "total_weighted_cumulative_waiting_time": (
                    cohort.total_weighted_cumulative_waiting_time
                ),
                "average_weighted_cumulative_waiting_time": (
                    cohort.average_weighted_cumulative_waiting_time
                ),
            }
        )
    return rows


def build_vot_cohort_rows(plans, vot_by_name, cohort_by_name) -> list[dict]:
    rows = []
    for plan in plans:
        vehicle_name = plan["name"]
        rows.append(
            {
                "vehicle_name": vehicle_name,
                "origin": plan["origin"],
                "destination": plan["destination"],
                "departure_timestep": plan["departure_time"],
                "evaluation_cohort": cohort_by_name[vehicle_name],
                "true_vot_per_second": vot_by_name[vehicle_name],
                "traffic_seed": TRAFFIC_SEED,
                "demand_gen_seed": DEMAND_GEN_SEED,
                "vot_seed": VOT_SEED,
                "cohort_assignment_seed": COHORT_SEED,
            }
        )
    return rows


def build_signal_control_summary(signal_audit: dict) -> dict:
    return {
        "method_name": METHOD_NAME,
        "signal_setting": list(SIGNAL_SETTING),
        "api_cycle_length": API_CYCLE_LENGTH,
        "deltat": 1,
        "intended_effective_phase_durations": list(INTENDED_EFFECTIVE_PHASE_DURATIONS),
        "offset_formula": OFFSET_FORMULA,
        "offset_interval": OFFSET_INTERVAL,
        "offset_values": list(OFFSET_VALUES),
        "internal_signalized_node_count": signal_audit["internal_signalized_node_count"],
        "external_unsignalized_node_count": signal_audit["external_unsignalized_node_count"],
        "signal_group_0_entering_link_count": signal_audit["entering_signal_group_0_count"],
        "signal_group_2_entering_link_count": signal_audit["entering_signal_group_2_count"],
        "signal_group_0_link_count": signal_audit["signal_group_0_link_count"],
        "signal_group_2_link_count": signal_audit["signal_group_2_link_count"],
        "signal_group_1_link_count": 0,
        "signal_group_3_link_count": 0,
        "phase_0": "east-west green, signal_group 0",
        "phase_1": "no link assigned, all-red equivalent",
        "phase_2": "north-south green, signal_group 2",
        "phase_3": "no link assigned, all-red equivalent",
        "order_control_used": False,
    }


def build_summary_payload(result, evaluation_facts: dict, comparison_metadata: dict) -> dict:
    summary = result.summary
    return {
        "scenario_name": SCENARIO_NAME,
        "method_name": METHOD_NAME,
        "vehicle_count": summary.vehicle_count,
        "AWT_s": evaluation_facts["awt_s"],
        "AWWT": evaluation_facts["awwt"],
        "route_conditional_AWT_s": evaluation_facts["route_conditional_awt_s"],
        "route_conditional_AWWT": evaluation_facts["route_conditional_awwt"],
        "average_detour_time_s": evaluation_facts["average_detour_time_s"],
        "average_weighted_detour_time": evaluation_facts["average_weighted_detour_time"],
        "participating_cohort_AWT_s": evaluation_facts["participating_awt_s"],
        "participating_cohort_AWWT": evaluation_facts["participating_awwt"],
        "nonparticipating_cohort_AWT_s": evaluation_facts["nonparticipating_awt_s"],
        "nonparticipating_cohort_AWWT": evaluation_facts["nonparticipating_awwt"],
        "network_free_flow_signature_digest": (
            evaluation_facts["network_free_flow_signature_digest"]
        ),
        "cohorts": build_cohort_rows(result),
        "comparison_metadata": comparison_metadata,
        "awwt_unit_note": (
            "AWWT, Route-Conditional AWWT, and VOT-weighted Average Detour Time "
            "are per-vehicle averages of waiting seconds times true_vot_per_second. "
            "They are not seconds."
        ),
    }


# ---------------------------------------------------------------------------
# 8. Static validation
# ---------------------------------------------------------------------------

def _function_node(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_names(function_node: ast.FunctionDef) -> list[str]:
    names = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def _assert_formal_signal_constants() -> None:
    if SIGNAL_SETTING != (59, 0, 59, 0):
        raise RuntimeError("Formal signal_setting must be [59, 0, 59, 0].")
    if sum(SIGNAL_SETTING) != 118 or API_CYCLE_LENGTH != 118:
        raise RuntimeError("API cycle length must be 118.")
    if OFFSET_INTERVAL != 29.5:
        raise RuntimeError("Offset interval must be 29.5.")
    if OFFSET_VALUES != (0.0, 29.5, 59.0, 88.5):
        raise RuntimeError("Offset values must be 0, 29.5, 59, 88.5.")
    if INTENDED_EFFECTIVE_PHASE_DURATIONS != (60, 1, 60, 1):
        raise RuntimeError("Effective phase durations must be 60, 1, 60, 1.")
    if SIGNAL_SETTING == (60, 60) or SIGNAL_SETTING == (60, 1, 60, 1):
        raise RuntimeError("Formal signal_setting must not be a historical setting.")
    if SIGNAL_SETTING == (59, 1, 59, 1):
        raise RuntimeError("Formal signal_setting must not use a 1-timestep all-red API value.")


def _assert_single_evaluation_call(tree: ast.Module) -> None:
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == PRODUCTION_ENTRY_POINT:
            calls.append(node)
    if len(calls) != 1:
        raise RuntimeError(
            f"evaluate_network_wide_waiting_time call count is {len(calls)}, expected 1."
        )
    keyword_names = []
    for keyword in calls[0].keywords:
        keyword_names.append(keyword.arg)
    if "method_specific_participation_status_by_vehicle_name" in keyword_names:
        raise RuntimeError(
            "signalized UXsim must not pass method_specific_participation_status."
        )
    if "method_name" not in keyword_names:
        raise RuntimeError("The evaluation call must pass method_name.")


def _assert_run_order(tree: ast.Module) -> None:
    run_function = _function_node(tree, "_run_signalized_validation")
    if run_function is None:
        raise RuntimeError("_run_signalized_validation is missing.")
    names = _call_names(run_function)
    required = [
        "run_until_full_completion",
        "verify_full_completion",
        "evaluate_signalized_network_wide_waiting_time",
        "verify_waiting_time_result",
    ]
    positions = []
    for name in required:
        if names.count(name) != 1:
            raise RuntimeError(f"_run_signalized_validation must call {name} once.")
        positions.append(names.index(name))
    if positions != sorted(positions):
        raise RuntimeError("Completion, evaluation, and audit are out of order.")
    if "exec_simulation" in names:
        raise RuntimeError("The run function must not call exec_simulation itself.")
    if "set_order_control_for_nodes" in names or "set_order_control_clearance_timesteps" in names:
        raise RuntimeError("The run function must not install order control.")
    stepper = _function_node(tree, "run_until_full_completion")
    if stepper is None or "exec_simulation" not in _call_names(stepper):
        raise RuntimeError("Full completion must advance with exec_simulation.")
    helper = _function_node(tree, "evaluate_signalized_network_wide_waiting_time")
    if helper is None:
        raise RuntimeError("Waiting-time helper is missing.")
    helper_names = _call_names(helper)
    if helper_names.count(PRODUCTION_ENTRY_POINT) != 1:
        raise RuntimeError("The helper must call the evaluator once.")
    if "exec_simulation" in helper_names:
        raise RuntimeError("The waiting-time helper must not run the simulation.")


def _assert_no_trial_import(tree: ast.Module) -> None:
    for node in tree.body:
        modules = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
        for module_name in modules:
            if module_name.startswith("run_fcfs_") or module_name.startswith("run_tvt_mp_"):
                raise RuntimeError(f"This script must not import {module_name}.")
            if module_name.startswith("run_signalized_"):
                raise RuntimeError(f"This script must not import {module_name}.")


def _assert_no_git(tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "git":
            raise RuntimeError("This script must not call git.")


def validate_static_contract() -> None:
    if METHOD_NAME != "signalized_uxsim":
        raise RuntimeError("method_name must be signalized_uxsim.")
    if NUM_VEHICLES != 3000 or PARTICIPATING_VEHICLE_COUNT != 2400:
        raise RuntimeError("Vehicle and cohort counts must be 3000 and 2400.")
    if NONPARTICIPATING_VEHICLE_COUNT != 600 or COHORT_SEED != 3:
        raise RuntimeError("Nonparticipating count must be 600 and cohort seed 3.")
    if TRAFFIC_SEED != 0 or DEMAND_GEN_SEED != 42 or VOT_SEED != 1:
        raise RuntimeError("Seeds must be traffic 0, demand 42, VOT 1.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 999:
        raise RuntimeError("Departure window must be 0..999.")
    if len(INTERNAL_GRID_NODES) != 36 or len(EXTERNAL_OD_NODES) != 24:
        raise RuntimeError("Node lists must be 36 internal and 24 external.")
    if SIGNAL_GROUP_EAST_WEST != 0 or SIGNAL_GROUP_NORTH_SOUTH != 2:
        raise RuntimeError("Signal groups must be 0 and 2.")
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {TRIAL_OUTPUT_DIR}.")
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    _assert_formal_signal_constants()
    _assert_single_evaluation_call(tree)
    _assert_run_order(tree)
    _assert_no_trial_import(tree)
    _assert_no_git(tree)
    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    forbidden_in_static = {
        "exec_simulation",
        "generate_vehicle_plans",
        "build_world_and_network",
        "evaluate_network_wide_waiting_time",
        "validate_signal_timing_only",
        "mkdir",
    }
    for name in _call_names(validator):
        if name in forbidden_in_static:
            raise RuntimeError(f"Static validation must not call {name}.")


# ---------------------------------------------------------------------------
# 9. Run
# ---------------------------------------------------------------------------

def _run_signalized_validation() -> int:
    script_start = time.perf_counter()
    timing = {
        "exec_simulation_seconds": 0.0,
        "network_wide_waiting_time_evaluation_seconds": 0.0,
        "output_write_seconds": 0.0,
        "script_total_seconds": 0.0,
    }
    _refuse_existing_output_directory()

    plans = generate_vehicle_plans()
    plan_audit = verify_vehicle_plans(plans)
    ordered_names = _ordered_vehicle_names(plans)
    nonparticipating_names = select_nonparticipating_names(ordered_names)
    participating_names = _participating_names(ordered_names, nonparticipating_names)
    cohort_hashes = verify_cohort_hashes(plans, nonparticipating_names, participating_names)
    vot_values = generate_true_vot_per_second(len(plans))
    true_vot_by_name, cohort_by_name = build_vot_and_cohort_ledgers(
        plans,
        vot_values,
        nonparticipating_names,
    )

    world = build_world_and_network()
    signal_audit = verify_signal_and_network(world)
    add_vehicles_to_world(world, plans)
    world.finalize_scenario()
    if world.TSIZE != SAFE_LAST_TIMESTEP_CAP:
        raise RuntimeError(
            f"World.TSIZE is {world.TSIZE}, expected the safe cap {SAFE_LAST_TIMESTEP_CAP}."
        )

    started = time.perf_counter()
    run_until_full_completion(world)
    timing["exec_simulation_seconds"] = time.perf_counter() - started
    completion = verify_full_completion(world, plans)
    if completion["full_trip_completion"] is not True:
        raise RuntimeError("Full completion flag was not set.")
    if completion["traffic_clearance_completed"] is not True:
        raise RuntimeError("Traffic clearance flag was not set.")

    comparison_metadata = build_comparison_metadata(plan_audit, cohort_hashes, completion)
    before = _finished_world_observation(world, ordered_names)
    started = time.perf_counter()
    result = evaluate_signalized_network_wide_waiting_time(
        world,
        ordered_names,
        true_vot_by_name,
        cohort_by_name,
        plan_audit["vehicle_plan_sha256"],
        comparison_metadata,
    )
    timing["network_wide_waiting_time_evaluation_seconds"] = time.perf_counter() - started
    evaluation_facts = verify_waiting_time_result(
        result,
        plans,
        ordered_names,
        true_vot_by_name,
        cohort_by_name,
        plan_audit["vehicle_plan_sha256"],
        cohort_hashes["cohort_assignment_sha256"],
        world,
    )
    after = _finished_world_observation(world, ordered_names)
    if after != before:
        raise RuntimeError("Waiting-time evaluation changed the finished World.")
    if _traffic_is_clear(world) is not True:
        raise RuntimeError("Traffic clearance changed after evaluation.")

    _refuse_existing_output_directory()
    TRIAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    _write_csv(
        TRIAL_OUTPUT_DIR / VEHICLES_CSV_NAME,
        _vehicle_field_names(),
        build_vehicle_rows(result),
    )
    _write_csv(
        TRIAL_OUTPUT_DIR / COHORTS_CSV_NAME,
        _cohort_field_names(),
        build_cohort_rows(result),
    )
    _write_json(
        TRIAL_OUTPUT_DIR / SUMMARY_JSON_NAME,
        build_summary_payload(result, evaluation_facts, comparison_metadata),
    )
    vot_fields = [
        "vehicle_name",
        "origin",
        "destination",
        "departure_timestep",
        "evaluation_cohort",
        "true_vot_per_second",
        "traffic_seed",
        "demand_gen_seed",
        "vot_seed",
        "cohort_assignment_seed",
    ]
    _write_csv(
        TRIAL_OUTPUT_DIR / VOT_COHORT_CSV_NAME,
        vot_fields,
        build_vot_cohort_rows(plans, true_vot_by_name, cohort_by_name),
    )
    _write_json(
        TRIAL_OUTPUT_DIR / PLAN_AUDIT_JSON_NAME,
        {
            "scenario_name": SCENARIO_NAME,
            "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
            "cohort_assignment_sha256": cohort_hashes["cohort_assignment_sha256"],
            "nonparticipating_name_sha256": cohort_hashes["nonparticipating_name_sha256"],
            "participating_name_sha256": cohort_hashes["participating_name_sha256"],
            "first_departure": plan_audit["first_departure"],
            "last_departure": plan_audit["last_departure"],
        },
    )
    _write_json(
        TRIAL_OUTPUT_DIR / SIGNAL_SUMMARY_JSON_NAME,
        build_signal_control_summary(signal_audit),
    )
    timing["output_write_seconds"] = time.perf_counter() - started
    timing["script_total_seconds"] = time.perf_counter() - script_start

    manifest = {
        "scenario_name": SCENARIO_NAME,
        "method_name": METHOD_NAME,
        "NUM_VEHICLES": NUM_VEHICLES,
        "comparison_metadata": comparison_metadata,
        "full_trip_completion": True,
        "traffic_clearance_completed": True,
        "final_world_t": completion["final_world_t"],
        "evaluation_end_timestep": completion["evaluation_end_timestep"],
        "AWT_s": evaluation_facts["awt_s"],
        "AWWT": evaluation_facts["awwt"],
        "route_conditional_AWT_s": evaluation_facts["route_conditional_awt_s"],
        "route_conditional_AWWT": evaluation_facts["route_conditional_awwt"],
        "average_detour_time_s": evaluation_facts["average_detour_time_s"],
        "average_weighted_detour_time": evaluation_facts["average_weighted_detour_time"],
        "timing_seconds": timing,
        "safe_last_timestep_cap": SAFE_LAST_TIMESTEP_CAP,
        "safe_cap_is_not_an_assumed_completion_time": True,
    }
    _write_json(TRIAL_OUTPUT_DIR / MANIFEST_JSON_NAME, manifest)

    summary_lines = [
        f"method_name: {METHOD_NAME}",
        f"vehicles: {NUM_VEHICLES}",
        "full completion: True",
        "traffic clearance: True",
        f"final World.T: {completion['final_world_t']}",
        f"evaluation end timestep: {completion['evaluation_end_timestep']}",
        "signal_setting: [59, 0, 59, 0]",
        f"API cycle length: {API_CYCLE_LENGTH}",
        "effective phase durations: [60, 1, 60, 1]",
        f"offset interval: {OFFSET_INTERVAL}",
        "offset values: [0, 29.5, 59, 88.5]",
        f"AWT seconds: {evaluation_facts['awt_s']}",
        f"AWWT: {evaluation_facts['awwt']}",
        f"Route-Conditional AWT seconds: {evaluation_facts['route_conditional_awt_s']}",
        f"Route-Conditional AWWT: {evaluation_facts['route_conditional_awwt']}",
        f"Average Detour Time seconds: {evaluation_facts['average_detour_time_s']}",
        "VOT-weighted Average Detour Time: "
        f"{evaluation_facts['average_weighted_detour_time']}",
        f"participating cohort AWT seconds: {evaluation_facts['participating_awt_s']}",
        f"participating cohort AWWT: {evaluation_facts['participating_awwt']}",
        f"nonparticipating cohort AWT seconds: {evaluation_facts['nonparticipating_awt_s']}",
        f"nonparticipating cohort AWWT: {evaluation_facts['nonparticipating_awwt']}",
        f"exec_simulation seconds: {timing['exec_simulation_seconds']}",
        "network-wide evaluation seconds: "
        f"{timing['network_wide_waiting_time_evaluation_seconds']}",
        f"output write seconds: {timing['output_write_seconds']}",
        f"script total seconds: {timing['script_total_seconds']}",
        f"output directory: {TRIAL_OUTPUT_DIR}",
    ]
    summary_path = TRIAL_OUTPUT_DIR / RUN_SUMMARY_TXT_NAME
    if summary_path.exists():
        raise FileExistsError(f"Refusing to overwrite {summary_path}.")
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    for line in summary_lines:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) > 1:
        raise SystemExit("Pass at most one option.")
    if len(argv) == 1:
        option = argv[0]
        if option == "--static-validate-only":
            validate_static_contract()
            print("Static contract validation passed.")
            return 0
        if option == "--validate-signal-timing-only":
            validate_signal_timing_only()
            return 0
        raise SystemExit(f"Unknown option {option!r}.")
    return _run_signalized_validation()


if __name__ == "__main__":
    raise SystemExit(main())
