"""
Current-FCFS validation: 3000-vehicle network-wide ACWT and ACWWT.

validation_scope:
current_fcfs_3000_vehicle_network_wide_waiting_time_connection

future_compatibility_note:
This validation script does not automatically adopt future changes to BATCH,
TVT-MP, demand generation, or seed contracts.

This file is a one-condition validation script. It is not a four-method trial
framework. It connects the current FCFS 3000-vehicle completion conditions to
evaluate_network_wide_waiting_time. If vehicle-plan generation, seeds, OD,
departure, true VOT, cohort assignment, FCFS node setup, routing, the finish
rule, or World/Vehicle time contracts change, this script must be checked
again or rewritten.

The 2400/600 split is an evaluation cohort copied from the current TVT-MP
vehicle-name assignment. It is not an FCFS participating status.

Run from the repository root:

    python research_scripts/run_fcfs_6x6_grid_3000_vehicle_network_wide_acwt_acwwt_validation.py --static-validate-only
    python research_scripts/run_fcfs_6x6_grid_3000_vehicle_network_wide_acwt_acwwt_validation.py

Timing audit: manifest.json stores only durations fixed before manifest write starts.
run_summary.txt stores durations fixed before run_summary write starts.
run_summary_write_seconds and script_total_seconds are printed to the console only.
Neither manifest.json nor run_summary.txt is rewritten to update those final times.
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
from uxsim.analyzer import Analyzer
from uxsim.network_wide_waiting_time_evaluation import (
    evaluate_network_wide_waiting_time,
)
from uxsim.uxsim import Link, Node, Vehicle

# ---------------------------------------------------------------------------
# 1. Current FCFS validation constants
# ---------------------------------------------------------------------------

VALIDATION_SCOPE = "current_fcfs_3000_vehicle_network_wide_waiting_time_connection"
FUTURE_COMPATIBILITY_NOTE = (
    "This validation script does not automatically adopt future changes to BATCH, "
    "TVT-MP, demand generation, or seed contracts."
)
CURRENT_SEED_CONTRACT_NOTE = (
    "Current contract only: traffic seed 0, demand generation seed 42, "
    "true VOT seed 1, cohort assignment seed 3. "
    "These seeds are not a promise about future BATCH or TVT-MP trials."
)

SCENARIO_NAME = (
    "fcfs_6x6_grid_3000_vehicle_network_wide_acwt_acwwt_"
    "validation_departure_999_seed_0_demand_seed_42_"
    "vot_seed_1_cohort_seed_3"
)
SOURCE_FCFS_SCRIPT = (
    "research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_"
    "speed_60kph_departure_999_tmax_5000_completion_check.py"
)
PRODUCTION_MODULE_NAME = "uxsim.network_wide_waiting_time_evaluation"
PRODUCTION_ENTRY_POINT = "evaluate_network_wide_waiting_time"
PRODUCTION_COMMIT = "89145c6"
METHOD_NAME = "fcfs"
NODE_CONTROL_METHOD = "fcfs"
REPLICATION_IDENTIFIER = SCENARIO_NAME

PARTICIPATING_COHORT = "tvt_participating_cohort"
NONPARTICIPATING_COHORT = "tvt_nonparticipating_cohort"

EXPECTED_VEHICLE_PLAN_SHA256 = (
    "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
)
EXPECTED_PARTICIPATION_ASSIGNMENT_SHA256 = (
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
NONPARTICIPATION_SEED = 3

DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5
FINAL_OBSERVATION_TIMESTEP = 4999
TMAX = 5000
EXPECTED_WORLD_T_AFTER_SIM = 5000

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
VOT_SEED = 1
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = 36
EXTERNAL_OD_NODE_COUNT = 24
TOTAL_NODE_COUNT = 60
INTERNAL_DIRECTED_LINK_COUNT = 120
OD_CONNECTOR_DIRECTED_LINK_COUNT = 48
TOTAL_LINK_COUNT = 168

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
FCFS_CLEARANCE_TIMESTEPS = 1
REACTION_TIME = 1
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2

VEHICLES_CSV_NAME = "network_wide_waiting_time_vehicles.csv"
COHORTS_CSV_NAME = "network_wide_waiting_time_cohorts.csv"
SUMMARY_JSON_NAME = "network_wide_waiting_time_summary.json"
VOT_COHORT_CSV_NAME = "vehicle_vot_and_cohort.csv"
PLAN_AUDIT_JSON_NAME = "vehicle_plan_audit.json"
MANIFEST_JSON_NAME = "manifest.json"
RUN_SUMMARY_TXT_NAME = "run_summary.txt"

DATA_FILE_NAMES = (
    VEHICLES_CSV_NAME,
    COHORTS_CSV_NAME,
    SUMMARY_JSON_NAME,
    VOT_COHORT_CSV_NAME,
    PLAN_AUDIT_JSON_NAME,
)

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
TRIAL_OUTPUT_DIR = REPO_ROOT / "research_outputs" / "trial" / SCENARIO_NAME


# ---------------------------------------------------------------------------
# 2. Network names. Same construction as the current FCFS completion script.
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


def _build_link_specs() -> tuple[tuple, tuple]:
    internal = []
    connectors = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            internal.append(
                (f"h_{row}_{column}_{column + 1}", left_node, right_node, INTERNAL_LINK_LENGTH, 0)
            )
            internal.append(
                (f"h_{row}_{column + 1}_{column}", right_node, left_node, INTERNAL_LINK_LENGTH, 0)
            )
    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            internal.append(
                (f"v_{row}_{row + 1}_{column}", upper_node, lower_node, INTERNAL_LINK_LENGTH, 1)
            )
            internal.append(
                (f"v_{row + 1}_{row}_{column}", lower_node, upper_node, INTERNAL_LINK_LENGTH, 1)
            )
    for column in range(GRID_SIZE):
        top_node = f"top_{column}"
        bottom_node = f"bottom_{column}"
        north_grid = _grid_node_name(0, column)
        south_grid = _grid_node_name(GRID_SIZE - 1, column)
        connectors.append((f"top_{column}_to_g_0_{column}", top_node, north_grid, OD_CONNECTOR_LENGTH, 1))
        connectors.append((f"g_0_{column}_to_top_{column}", north_grid, top_node, OD_CONNECTOR_LENGTH, 1))
        connectors.append((f"bottom_{column}_to_g_5_{column}", bottom_node, south_grid, OD_CONNECTOR_LENGTH, 1))
        connectors.append((f"g_5_{column}_to_bottom_{column}", south_grid, bottom_node, OD_CONNECTOR_LENGTH, 1))
    for row in range(GRID_SIZE):
        left_node = f"left_{row}"
        right_node = f"right_{row}"
        west_grid = _grid_node_name(row, 0)
        east_grid = _grid_node_name(row, GRID_SIZE - 1)
        connectors.append((f"left_{row}_to_g_{row}_0", left_node, west_grid, OD_CONNECTOR_LENGTH, 0))
        connectors.append((f"g_{row}_0_to_left_{row}", west_grid, left_node, OD_CONNECTOR_LENGTH, 0))
        connectors.append((f"right_{row}_to_g_{row}_5", right_node, east_grid, OD_CONNECTOR_LENGTH, 0))
        connectors.append((f"g_{row}_5_to_right_{row}", east_grid, right_node, OD_CONNECTOR_LENGTH, 0))
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
    """Same OD, departure, and seed order as the current FCFS completion script."""
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
        raise RuntimeError(f"Vehicle plan count is {len(plans)}, expected {NUM_VEHICLES}.")
    external = []
    for name in EXTERNAL_OD_NODES:
        external.append(name)
    departures = []
    previous_departure = None
    for index, plan in enumerate(plans):
        expected_name = f"veh_{index}"
        if plan["name"] != expected_name:
            raise RuntimeError(
                f"Vehicle plan {index} name is {plan['name']!r}, expected {expected_name!r}."
            )
        if plan["origin"] == plan["destination"]:
            raise RuntimeError(f"{plan['name']} origin equals destination.")
        if plan["origin"] not in external or plan["destination"] not in external:
            raise RuntimeError(f"{plan['name']} OD is not an external OD node.")
        if plan["manhattan_distance"] < MIN_OD_MANHATTAN_DISTANCE:
            raise RuntimeError(
                f"{plan['name']} Manhattan distance is {plan['manhattan_distance']}."
            )
        departure_time = plan["departure_time"]
        if departure_time < DEPARTURE_START or departure_time > DEPARTURE_END:
            raise RuntimeError(
                f"{plan['name']} departure {departure_time!r} is outside "
                f"T={DEPARTURE_START}..{DEPARTURE_END}."
            )
        if previous_departure is not None and departure_time < previous_departure:
            raise RuntimeError(f"{plan['name']} departure decreased.")
        previous_departure = departure_time
        departures.append(departure_time)
    if departures[0] != DEPARTURE_START:
        raise RuntimeError(f"First departure is {departures[0]!r}, expected {DEPARTURE_START}.")
    if departures[-1] != DEPARTURE_END:
        raise RuntimeError(f"Last departure is {departures[-1]!r}, expected {DEPARTURE_END}.")
    digest = _vehicle_plan_digest(plans)
    if digest != EXPECTED_VEHICLE_PLAN_SHA256:
        raise RuntimeError(
            "vehicle_plan_sha256 mismatch. "
            f"expected {EXPECTED_VEHICLE_PLAN_SHA256}, got {digest}."
        )
    return {
        "plan_count": len(plans),
        "first_departure": departures[0],
        "last_departure": departures[-1],
        "vehicle_plan_sha256": digest,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "traffic_seed": RANDOM_SEED,
    }


def _ordered_vehicle_names(plans: list[dict]) -> list[str]:
    names = []
    for plan in plans:
        names.append(plan["name"])
    return names


def select_nonparticipating_names(population: list[str]) -> tuple[str, ...]:
    """Same selector as the current TVT-MP 3000-vehicle script.

    random.Random(seed).sample draws 600 names. The returned tuple keeps the
    vehicle-plan order. The set is only the sample membership test from that
    script. Saved files keep tuples and lists, not sets.
    """
    sampled = set(
        random.Random(NONPARTICIPATION_SEED).sample(
            population,
            NONPARTICIPATING_VEHICLE_COUNT,
        )
    )
    selected = []
    for name in population:
        if name in sampled:
            selected.append(name)
    if len(selected) != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            "Nonparticipating selection count is "
            f"{len(selected)}, expected {NONPARTICIPATING_VEHICLE_COUNT}."
        )
    return tuple(selected)


def _participating_names(population: list[str], nonparticipating_names: tuple[str, ...]) -> tuple[str, ...]:
    selected = []
    for name in nonparticipating_names:
        selected.append(name)
    names = []
    for name in population:
        if name not in selected:
            names.append(name)
    if len(names) != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Participating name count is {len(names)}, expected {PARTICIPATING_VEHICLE_COUNT}."
        )
    return tuple(names)


def _hash_names(names: tuple[str, ...] | list[str]) -> str:
    payload = "\n".join(names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def participation_assignment_digest(plans: list[dict], nonparticipating_names: tuple[str, ...]) -> str:
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
    participation_digest = participation_assignment_digest(plans, nonparticipating_names)
    nonparticipating_digest = _hash_names(nonparticipating_names)
    participating_digest = _hash_names(participating_names)
    if participation_digest != EXPECTED_PARTICIPATION_ASSIGNMENT_SHA256:
        raise RuntimeError(
            "participation_assignment_sha256 mismatch. "
            f"expected {EXPECTED_PARTICIPATION_ASSIGNMENT_SHA256}, got {participation_digest}."
        )
    if nonparticipating_digest != EXPECTED_NONPARTICIPATING_NAME_SHA256:
        raise RuntimeError(
            "nonparticipating_name_sha256 mismatch. "
            f"expected {EXPECTED_NONPARTICIPATING_NAME_SHA256}, got {nonparticipating_digest}."
        )
    if participating_digest != EXPECTED_PARTICIPATING_NAME_SHA256:
        raise RuntimeError(
            "participating_name_sha256 mismatch. "
            f"expected {EXPECTED_PARTICIPATING_NAME_SHA256}, got {participating_digest}."
        )
    if len(nonparticipating_names) != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Nonparticipating count is {len(nonparticipating_names)}, expected 600."
        )
    if len(participating_names) != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Participating count is {len(participating_names)}, expected 2400."
        )
    return {
        "participation_assignment_sha256": participation_digest,
        "nonparticipating_name_sha256": nonparticipating_digest,
        "participating_name_sha256": participating_digest,
    }


def generate_true_vot_per_second(count: int) -> list[float]:
    """Same lognormal draw as the current TVT-MP 3000-vehicle trial. Not divided by 3600."""
    rng = np.random.default_rng(VOT_SEED)
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    values = []
    for value in samples:
        if isinstance(value, bool):
            raise RuntimeError(f"true VOT sample is bool: {value!r}.")
        number = float(value)
        if math.isfinite(number) is not True or number <= 0.0:
            raise RuntimeError(f"true VOT sample is not a positive finite float: {number!r}.")
        values.append(number)
    if len(values) != count:
        raise RuntimeError(f"true VOT count is {len(values)}, expected {count}.")
    return values


def build_vot_and_cohort_ledgers(
    plans: list[dict],
    vot_values: list[float],
    nonparticipating_names: tuple[str, ...],
) -> tuple[dict[str, float], dict[str, str]]:
    if len(plans) != len(vot_values):
        raise RuntimeError(
            f"Plan count {len(plans)} and true VOT count {len(vot_values)} differ."
        )
    nonparticipating = []
    for name in nonparticipating_names:
        nonparticipating.append(name)
    vot_by_name = {}
    cohort_by_name = {}
    participating_count = 0
    nonparticipating_count = 0
    for plan, vot in zip(plans, vot_values):
        vehicle_name = plan["name"]
        if isinstance(vot, bool) or not isinstance(vot, float):
            raise RuntimeError(
                f"true_vot_per_second for {vehicle_name} is not a float: {vot!r}."
            )
        if math.isfinite(vot) is not True or vot <= 0.0:
            raise RuntimeError(
                f"true_vot_per_second for {vehicle_name} is not positive and finite: {vot!r}."
            )
        vot_by_name[vehicle_name] = vot
        if vehicle_name in nonparticipating:
            cohort_by_name[vehicle_name] = NONPARTICIPATING_COHORT
            nonparticipating_count = nonparticipating_count + 1
        else:
            cohort_by_name[vehicle_name] = PARTICIPATING_COHORT
            participating_count = participating_count + 1
    if participating_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Participating cohort count is {participating_count}, expected 2400."
        )
    if nonparticipating_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Nonparticipating cohort count is {nonparticipating_count}, expected 600."
        )
    return vot_by_name, cohort_by_name


# ---------------------------------------------------------------------------
# 4. FCFS world
# ---------------------------------------------------------------------------

def build_world_and_network() -> World:
    world = World(
        name=SCENARIO_NAME,
        deltan=1,
        reaction_time=REACTION_TIME,
        tmax=TMAX,
        random_seed=RANDOM_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
    )
    spacing = 1.0
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            world.addNode(
                _grid_node_name(row, column),
                column * spacing,
                -row * spacing,
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

    eligible_nodes = world.infer_order_control_eligible_nodes()
    eligible_names = []
    for node in eligible_nodes:
        eligible_names.append(node.name)
    for node_name in INTERNAL_GRID_NODES:
        if node_name not in eligible_names:
            raise RuntimeError(f"Internal node {node_name} was not inferred eligible.")
    for node_name in eligible_names:
        if node_name not in INTERNAL_GRID_NODES:
            raise RuntimeError(f"Non-internal node {node_name} was inferred eligible.")
    for node_name in INTERNAL_GRID_NODES:
        node = world.get_node(node_name)
        if node.order_control_eligible is not True:
            raise RuntimeError(f"{node_name} order_control_eligible is not True.")
    for node_name in EXTERNAL_OD_NODES:
        node = world.get_node(node_name)
        if node.order_control_eligible is not False:
            raise RuntimeError(f"External OD node {node_name} must not be eligible.")

    world.set_order_control_clearance_timesteps(FCFS_CLEARANCE_TIMESTEPS)
    world.set_order_control_for_nodes(
        INTERNAL_GRID_NODES,
        order_control_type="fcfs",
    )
    for node_name in INTERNAL_GRID_NODES:
        node = world.get_node(node_name)
        if node.order_control_type != "fcfs":
            raise RuntimeError(f"{node_name} order_control_type is {node.order_control_type!r}.")
        if node.order_control_clearance_timesteps != FCFS_CLEARANCE_TIMESTEPS:
            raise RuntimeError(f"{node_name} clearance is not {FCFS_CLEARANCE_TIMESTEPS}.")
    for node_name in EXTERNAL_OD_NODES:
        node = world.get_node(node_name)
        if node.order_control_type == "fcfs":
            raise RuntimeError(f"External OD node {node_name} must not use FCFS.")
    return world


def verify_network_runtime(world: World) -> None:
    if len(world.NODES) != TOTAL_NODE_COUNT:
        raise RuntimeError(f"Node count is {len(world.NODES)}, expected {TOTAL_NODE_COUNT}.")
    if len(world.LINKS) != TOTAL_LINK_COUNT:
        raise RuntimeError(f"Link count is {len(world.LINKS)}, expected {TOTAL_LINK_COUNT}.")
    if len(INTERNAL_LINK_SPECS) != INTERNAL_DIRECTED_LINK_COUNT:
        raise RuntimeError("Internal directed link count is not 120.")
    if len(OD_CONNECTOR_LINK_SPECS) != OD_CONNECTOR_DIRECTED_LINK_COUNT:
        raise RuntimeError("OD connector directed link count is not 48.")
    for link_name, start_node, end_node, length, _signal_group in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        if link.start_node.name != start_node or link.end_node.name != end_node:
            raise RuntimeError(f"Link {link_name} endpoints do not match the spec.")
        if link.length != length or length != 200:
            raise RuntimeError(f"Link {link_name} length is {link.length!r}.")
        if link.number_of_lanes != NUMBER_OF_LANES:
            raise RuntimeError(f"Link {link_name} lane count is not 1.")
        if link.free_flow_speed != FREE_FLOW_SPEED or link.u != FREE_FLOW_SPEED:
            raise RuntimeError(f"Link {link_name} free-flow speed is not 60 km/h.")
        if link.jam_density != JAM_DENSITY:
            raise RuntimeError(f"Link {link_name} jam density is {link.jam_density!r}.")


def add_vehicles_to_world(world: World, plans: list[dict]) -> None:
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
            raise RuntimeError(f"Vehicle {vehicle.name} has unexpected state {state_value!r}.")
        counts[state_value] = counts[state_value] + 1
    return counts


def _all_link_vehicle_count(world: World) -> int:
    total = 0
    for link in world.LINKS:
        total = total + len(link.vehicles)
    return total


def verify_fcfs_full_completion(world: World, plans: list[dict]) -> dict:
    """Require the same full-completion facts as the current FCFS completion check.

    A failed check raises before any formal output directory is created.
    """
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )
    if len(world.VEHICLES) != NUM_VEHICLES:
        raise RuntimeError(f"World vehicle count is {len(world.VEHICLES)}, expected 3000.")
    if len(plans) != NUM_VEHICLES:
        raise RuntimeError(f"Plan count is {len(plans)}, expected 3000.")

    plan_names = _ordered_vehicle_names(plans)
    world_names = []
    for vehicle_name in world.VEHICLES.keys():
        world_names.append(vehicle_name)
    if sorted(world_names) != sorted(plan_names):
        raise RuntimeError("World vehicle names do not match the vehicle plan.")

    counts = _state_counts(world)
    if counts["home"] != 0 or counts["wait"] != 0 or counts["run"] != 0:
        raise RuntimeError(
            "FCFS completion left non-end vehicles. "
            f"home={counts['home']} wait={counts['wait']} run={counts['run']} end={counts['end']}."
        )
    if counts["end"] != NUM_VEHICLES:
        raise RuntimeError(f"end count is {counts['end']}, expected 3000.")

    link_vehicle_count = _all_link_vehicle_count(world)
    if link_vehicle_count != 0:
        raise RuntimeError(
            "Full completion requires every link, including OD connectors, to have "
            f"0 vehicles. got {link_vehicle_count}."
        )

    for plan in plans:
        vehicle = world.VEHICLES[plan["name"]]
        if type(vehicle.departure_time) is not int:
            raise RuntimeError(
                f"{vehicle.name} departure_time is not a Python int: {vehicle.departure_time!r}."
            )
        if vehicle.departure_time < DEPARTURE_START or vehicle.departure_time > DEPARTURE_END:
            raise RuntimeError(
                f"{vehicle.name} departure timestep {vehicle.departure_time} is outside "
                f"T={DEPARTURE_START}..{DEPARTURE_END}."
            )
        if type(vehicle.arrival_time) is not int:
            raise RuntimeError(
                f"{vehicle.name} arrival_time is not a Python int: {vehicle.arrival_time!r}."
            )
        if vehicle.arrival_time < 0 or vehicle.arrival_time > FINAL_OBSERVATION_TIMESTEP:
            raise RuntimeError(
                f"{vehicle.name} arrival_time {vehicle.arrival_time} is not a valid "
                f"timestep through T={FINAL_OBSERVATION_TIMESTEP}."
            )
        if vehicle.state != "end":
            raise RuntimeError(f"{vehicle.name} state is {vehicle.state!r}, expected 'end'.")

    return {
        "final_world_t": world.T,
        "final_vehicle_state_counts": counts,
        "all_link_vehicle_count": link_vehicle_count,
        "full_trip_completion": True,
        "traffic_clearance_completed": True,
    }


# ---------------------------------------------------------------------------
# 5. Evaluation metadata and result checks
# ---------------------------------------------------------------------------

def build_comparison_metadata(plan_audit: dict, cohort_hashes: dict[str, str]) -> dict:
    metadata = {
        "replication_identifier": REPLICATION_IDENTIFIER,
        "method_name": METHOD_NAME,
        "node_control_method": NODE_CONTROL_METHOD,
        "traffic_seed": RANDOM_SEED,
        "demand_generation_seed": DEMAND_GEN_SEED,
        "true_vot_generation_seed": VOT_SEED,
        "cohort_assignment_seed": NONPARTICIPATION_SEED,
        "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
        "participation_assignment_sha256": cohort_hashes["participation_assignment_sha256"],
        "nonparticipating_name_sha256": cohort_hashes["nonparticipating_name_sha256"],
        "participating_name_sha256": cohort_hashes["participating_name_sha256"],
        "vehicle_count": NUM_VEHICLES,
        "departure_start": DEPARTURE_START,
        "departure_end": DEPARTURE_END,
        "grid_size": GRID_SIZE,
        "link_length_m": INTERNAL_LINK_LENGTH,
        "free_flow_speed_mps": FREE_FLOW_SPEED,
        "validation_scope": VALIDATION_SCOPE,
        "source_fcfs_script": SOURCE_FCFS_SCRIPT,
        "network_wide_waiting_time_production_commit": PRODUCTION_COMMIT,
        "current_seed_contract_note": CURRENT_SEED_CONTRACT_NOTE,
        "future_compatibility_note": FUTURE_COMPATIBILITY_NOTE,
    }
    for key, value in metadata.items():
        if isinstance(value, (World, Vehicle, Node, Link, Analyzer)):
            raise RuntimeError(f"comparison_metadata[{key!r}] contains a simulation object.")
        if not isinstance(value, (str, int, float, bool)):
            raise RuntimeError(
                f"comparison_metadata[{key!r}] is not a scalar. got {value!r}."
            )
        if isinstance(value, bool):
            continue
        if isinstance(value, float) and math.isfinite(value) is not True:
            raise RuntimeError(f"comparison_metadata[{key!r}] is not finite: {value!r}.")
    return metadata


def _values_close(left: float, right: float, label: str) -> None:
    if left == right:
        return
    if math.isclose(left, right, rel_tol=0.0, abs_tol=1e-6):
        return
    raise RuntimeError(f"{label} mismatch. left={left!r} right={right!r}.")


def _cohort_by_name(result) -> dict:
    found = {}
    for cohort in result.summary.cohort_summaries:
        found[cohort.evaluation_cohort] = cohort
    return found


def verify_evaluation_result(result, plans, vot_by_name, cohort_by_name, world) -> dict:
    records = result.vehicle_records
    summary = result.summary
    counters = result.counters
    if len(records) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle record count is {len(records)}, expected 3000.")
    if summary.vehicle_count != NUM_VEHICLES:
        raise RuntimeError(f"summary.vehicle_count is {summary.vehicle_count}, expected 3000.")
    if summary.method_name != METHOD_NAME:
        raise RuntimeError(f"summary.method_name is {summary.method_name!r}, expected 'fcfs'.")
    if counters.evaluated_vehicle_count != NUM_VEHICLES:
        raise RuntimeError(
            f"evaluated_vehicle_count is {counters.evaluated_vehicle_count}, expected 3000."
        )
    if counters.reference_replay_run_count != counters.unique_physical_route_count:
        raise RuntimeError(
            "reference_replay_run_count "
            f"{counters.reference_replay_run_count} does not match unique physical routes "
            f"{counters.unique_physical_route_count}."
        )
    expected_reuse = NUM_VEHICLES - counters.unique_physical_route_count
    if counters.reference_reuse_count != expected_reuse:
        raise RuntimeError(
            f"reference_reuse_count is {counters.reference_reuse_count}, expected {expected_reuse}."
        )
    if counters.negative_cumulative_waiting_time_count != 0:
        raise RuntimeError("negative_cumulative_waiting_time_count is not 0.")
    if counters.validation_failure_count != 0:
        raise RuntimeError("validation_failure_count is not 0.")
    if counters.incomplete_vehicle_count != 0:
        raise RuntimeError("incomplete_vehicle_count is not 0.")

    plan_names = _ordered_vehicle_names(plans)
    record_names = []
    total_cw = 0.0
    total_weighted = 0.0
    for record in records:
        record_names.append(record.vehicle_name)
        if record.method_name != METHOD_NAME:
            raise RuntimeError(
                f"{record.vehicle_name} method_name is {record.method_name!r}, expected 'fcfs'."
            )
        if record.cumulative_waiting_time_timesteps < 0:
            raise RuntimeError(
                f"{record.vehicle_name} cumulative waiting timesteps are "
                f"{record.cumulative_waiting_time_timesteps}."
            )
        if record.method_specific_participation_status is not None:
            raise RuntimeError(
                f"{record.vehicle_name} has method_specific_participation_status "
                f"{record.method_specific_participation_status!r}. FCFS must leave it unset."
            )
        total_cw = total_cw + record.cumulative_waiting_time_s
        total_weighted = total_weighted + record.weighted_cumulative_waiting_time
    if record_names != plan_names:
        raise RuntimeError("Vehicle record order does not match the vehicle plan order.")

    world_names = []
    for vehicle_name in world.VEHICLES.keys():
        world_names.append(vehicle_name)
    if sorted(world_names) != sorted(plan_names):
        raise RuntimeError("World names and vehicle plan names differ after evaluation.")
    if sorted(vot_by_name.keys()) != sorted(plan_names):
        raise RuntimeError("true VOT ledger names do not match the vehicle plan.")
    if sorted(cohort_by_name.keys()) != sorted(plan_names):
        raise RuntimeError("evaluation cohort ledger names do not match the vehicle plan.")

    cohorts = _cohort_by_name(result)
    if PARTICIPATING_COHORT not in cohorts or NONPARTICIPATING_COHORT not in cohorts:
        raise RuntimeError(f"Cohort summaries are {list(cohorts.keys())!r}.")
    participating = cohorts[PARTICIPATING_COHORT]
    nonparticipating = cohorts[NONPARTICIPATING_COHORT]
    if participating.vehicle_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Participating cohort count is {participating.vehicle_count}, expected 2400."
        )
    if nonparticipating.vehicle_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Nonparticipating cohort count is {nonparticipating.vehicle_count}, expected 600."
        )
    if participating.vehicle_count + nonparticipating.vehicle_count != NUM_VEHICLES:
        raise RuntimeError("Cohort counts do not add up to 3000.")

    _values_close(
        summary.total_cumulative_waiting_time_s,
        participating.total_cumulative_waiting_time_s
        + nonparticipating.total_cumulative_waiting_time_s,
        "total CW versus cohort CW",
    )
    _values_close(
        summary.total_weighted_cumulative_waiting_time,
        participating.total_weighted_cumulative_waiting_time
        + nonparticipating.total_weighted_cumulative_waiting_time,
        "total weighted versus cohort weighted",
    )
    _values_close(summary.total_cumulative_waiting_time_s, total_cw, "summary CW versus records")
    _values_close(
        summary.total_weighted_cumulative_waiting_time,
        total_weighted,
        "summary weighted versus records",
    )
    _values_close(
        summary.average_cumulative_waiting_time_s,
        summary.total_cumulative_waiting_time_s / NUM_VEHICLES,
        "ACWT",
    )
    _values_close(
        summary.average_weighted_cumulative_waiting_time,
        summary.total_weighted_cumulative_waiting_time / NUM_VEHICLES,
        "ACWWT",
    )
    _values_close(
        participating.average_cumulative_waiting_time_s,
        participating.total_cumulative_waiting_time_s / participating.vehicle_count,
        "participating ACWT",
    )
    _values_close(
        participating.average_weighted_cumulative_waiting_time,
        participating.total_weighted_cumulative_waiting_time / participating.vehicle_count,
        "participating ACWWT",
    )
    _values_close(
        nonparticipating.average_cumulative_waiting_time_s,
        nonparticipating.total_cumulative_waiting_time_s / nonparticipating.vehicle_count,
        "nonparticipating ACWT",
    )
    _values_close(
        nonparticipating.average_weighted_cumulative_waiting_time,
        nonparticipating.total_weighted_cumulative_waiting_time / nonparticipating.vehicle_count,
        "nonparticipating ACWWT",
    )

    for stored in result.reference_results_by_physical_key.values():
        if stored.validation_passed is not True:
            raise RuntimeError("A reference result in the formal result is not validated.")
    _reject_simulation_objects(result)
    return {
        "acwt_s": summary.average_cumulative_waiting_time_s,
        "acwwt": summary.average_weighted_cumulative_waiting_time,
        "total_cw_s": summary.total_cumulative_waiting_time_s,
        "total_weighted": summary.total_weighted_cumulative_waiting_time,
        "participating_acwt_s": participating.average_cumulative_waiting_time_s,
        "participating_acwwt": participating.average_weighted_cumulative_waiting_time,
        "nonparticipating_acwt_s": nonparticipating.average_cumulative_waiting_time_s,
        "nonparticipating_acwwt": nonparticipating.average_weighted_cumulative_waiting_time,
        "unique_physical_route_count": counters.unique_physical_route_count,
        "reference_replay_run_count": counters.reference_replay_run_count,
        "reference_reuse_count": counters.reference_reuse_count,
    }


def _reject_simulation_objects(value, seen=None) -> None:
    if seen is None:
        seen = []
    if id(value) in seen:
        return
    seen.append(id(value))
    if isinstance(value, (World, Vehicle, Node, Link, Analyzer)):
        raise RuntimeError(
            "Evaluation result contains a simulation object "
            f"({type(value).__name__})."
        )
    if isinstance(value, (str, bytes, int, float, bool, type(None))):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_simulation_objects(key, seen)
            _reject_simulation_objects(item, seen)
        return
    items = getattr(value, "items", None)
    if callable(items):
        for key, item in value.items():
            _reject_simulation_objects(key, seen)
            _reject_simulation_objects(item, seen)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _reject_simulation_objects(item, seen)
        return
    fields = getattr(value, "__dataclass_fields__", None)
    if fields is not None:
        for field_name in fields:
            _reject_simulation_objects(getattr(value, field_name), seen)


# ---------------------------------------------------------------------------
# 6. Formal output. The directory is created only after the checks above pass.
# ---------------------------------------------------------------------------

def _refuse_existing_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "This script does not overwrite it."
        )


def _json_number_list(values) -> str:
    numbers = []
    for value in values:
        numbers.append(value)
    return json.dumps(numbers)


def _json_text_list(values) -> str:
    texts = []
    for value in values:
        texts.append(str(value))
    return json.dumps(texts)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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
                "evaluation_cohort": record.evaluation_cohort,
                "method_specific_participation_status": status_cell,
                "actual_departure_timestep": record.actual_departure_timestep,
                "actual_arrival_timestep": record.actual_arrival_timestep,
                "actual_trip_timesteps": record.actual_trip_timesteps,
                "reference_departure_timestep": record.reference_departure_timestep,
                "reference_arrival_timestep": record.reference_arrival_timestep,
                "reference_minimum_trip_timesteps": record.reference_minimum_trip_timesteps,
                "cumulative_waiting_time_timesteps": record.cumulative_waiting_time_timesteps,
                "actual_travel_time_s": record.actual_travel_time_s,
                "minimum_trip_time_s": record.minimum_trip_time_s,
                "cumulative_waiting_time_s": record.cumulative_waiting_time_s,
                "true_vot_per_second": record.true_vot_per_second,
                "weighted_cumulative_waiting_time": record.weighted_cumulative_waiting_time,
                "route_audit_identity": _json_text_list(record.route_audit_identity),
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
                "traffic_seed": RANDOM_SEED,
                "demand_gen_seed": DEMAND_GEN_SEED,
                "vot_seed": VOT_SEED,
                "cohort_assignment_seed": NONPARTICIPATION_SEED,
            }
        )
    return rows


def build_summary_payload(result, evaluation_facts: dict) -> dict:
    counters = result.counters
    return {
        "scenario_name": SCENARIO_NAME,
        "method_name": result.summary.method_name,
        "validation_scope": VALIDATION_SCOPE,
        "future_compatibility_note": FUTURE_COMPATIBILITY_NOTE,
        "vehicle_count": result.summary.vehicle_count,
        "total_cumulative_waiting_time_s": result.summary.total_cumulative_waiting_time_s,
        "average_cumulative_waiting_time_s": result.summary.average_cumulative_waiting_time_s,
        "total_weighted_cumulative_waiting_time": (
            result.summary.total_weighted_cumulative_waiting_time
        ),
        "average_weighted_cumulative_waiting_time": (
            result.summary.average_weighted_cumulative_waiting_time
        ),
        "cohorts": build_cohort_rows(result),
        "evaluation_facts": evaluation_facts,
        "counters": {
            "evaluated_vehicle_count": counters.evaluated_vehicle_count,
            "unique_physical_route_count": counters.unique_physical_route_count,
            "reference_replay_run_count": counters.reference_replay_run_count,
            "reference_reuse_count": counters.reference_reuse_count,
            "unique_audit_identity_count": counters.unique_audit_identity_count,
            "duplicate_audit_identity_observation_count": (
                counters.duplicate_audit_identity_observation_count
            ),
            "incomplete_vehicle_count": counters.incomplete_vehicle_count,
            "validation_failure_count": counters.validation_failure_count,
            "negative_cumulative_waiting_time_count": (
                counters.negative_cumulative_waiting_time_count
            ),
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if block == b"":
                break
            hasher.update(block)
    return hasher.hexdigest()


def _manifest_timing_payload(timing: dict) -> dict:
    """Durations fixed before manifest.json write starts.

    manifest_write_seconds, run_summary_write_seconds, and script_total_seconds
    are excluded because they are not known yet.
    """
    return {
        "vehicle_plan_generation_seconds": timing["vehicle_plan_generation_seconds"],
        "true_vot_and_cohort_build_seconds": timing["true_vot_and_cohort_build_seconds"],
        "world_build_seconds": timing["world_build_seconds"],
        "vehicle_add_seconds": timing["vehicle_add_seconds"],
        "finalize_seconds": timing["finalize_seconds"],
        "exec_simulation_seconds": timing["exec_simulation_seconds"],
        "completion_validation_seconds": timing["completion_validation_seconds"],
        "network_wide_waiting_time_evaluation_seconds": (
            timing["network_wide_waiting_time_evaluation_seconds"]
        ),
        "output_build_seconds": timing["output_build_seconds"],
        "output_write_seconds": timing["output_write_seconds"],
        "elapsed_before_manifest_write_seconds": (
            timing["elapsed_before_manifest_write_seconds"]
        ),
    }


def _create_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory appeared before creation: {TRIAL_OUTPUT_DIR}.")
    TRIAL_OUTPUT_DIR.mkdir(parents=True)


# ---------------------------------------------------------------------------
# 7. Static validation. No simulation and no production evaluation.
# ---------------------------------------------------------------------------

def _function_node(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _collect_call_names_in_order(node, found: list[str]) -> None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            found.append(func.id)
        elif isinstance(func, ast.Attribute):
            found.append(func.attr)
    for child in ast.iter_child_nodes(node):
        _collect_call_names_in_order(child, found)


def _assert_explicit_production_import(tree: ast.Module) -> None:
    found = False
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if module == "uxsim":
            for alias in node.names:
                if alias.name == PRODUCTION_ENTRY_POINT:
                    raise RuntimeError(
                        "evaluate_network_wide_waiting_time must not be imported from uxsim."
                    )
        if module == PRODUCTION_MODULE_NAME:
            for alias in node.names:
                if alias.name == PRODUCTION_ENTRY_POINT:
                    found = True
        if "run_fcfs_6x6_grid" in module or "run_tvt_mp_6x6_grid" in module:
            raise RuntimeError(f"This script must not import {module}.")
    if found is not True:
        raise RuntimeError(
            "The script must import evaluate_network_wide_waiting_time from "
            "uxsim.network_wide_waiting_time_evaluation."
        )


def _assert_run_path_order(tree: ast.Module) -> None:
    run_function = _function_node(tree, "_run_fcfs_network_wide_validation")
    if run_function is None:
        raise RuntimeError("_run_fcfs_network_wide_validation is missing.")
    calls = []
    _collect_call_names_in_order(run_function, calls)
    exec_count = 0
    evaluate_count = 0
    mkdir_count = 0
    for name in calls:
        if name == "exec_simulation":
            exec_count = exec_count + 1
        if name == PRODUCTION_ENTRY_POINT:
            evaluate_count = evaluate_count + 1
        if name == "mkdir":
            mkdir_count = mkdir_count + 1
    directory_function = _function_node(tree, "_create_output_directory")
    if directory_function is None:
        raise RuntimeError("_create_output_directory is missing.")
    directory_calls = []
    _collect_call_names_in_order(directory_function, directory_calls)
    if directory_calls.count("mkdir") != 1:
        raise RuntimeError("The formal output directory must be created in one mkdir call.")
    if exec_count != 1:
        raise RuntimeError(f"exec_simulation call count is {exec_count}, expected 1.")
    if evaluate_count != 1:
        raise RuntimeError(
            f"evaluate_network_wide_waiting_time call count is {evaluate_count}, expected 1."
        )
    if mkdir_count != 0:
        raise RuntimeError("The run function must create the output directory through one helper.")
    if calls.index("exec_simulation") > calls.index(PRODUCTION_ENTRY_POINT):
        raise RuntimeError("exec_simulation must run before the production evaluation.")
    if calls.index(PRODUCTION_ENTRY_POINT) > calls.index("_create_output_directory"):
        raise RuntimeError("The formal output directory must be created after evaluation.")
    if calls.index("verify_evaluation_result") > calls.index("_create_output_directory"):
        raise RuntimeError("Result checks must finish before the output directory is created.")


def _assert_no_other_method_control(tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "set_order_control_for_nodes":
            continue
        for keyword in node.keywords:
            if keyword.arg != "order_control_type":
                continue
            if not isinstance(keyword.value, ast.Constant) or keyword.value.value != "fcfs":
                raise RuntimeError("The only order_control_type in this script must be fcfs.")


def _assert_timing_recording_contract(tree: ast.Module) -> None:
    payload_function = _function_node(tree, "_manifest_timing_payload")
    if payload_function is None:
        raise RuntimeError("_manifest_timing_payload is missing.")
    payload_source = ast.get_source_segment(
        SCRIPT_PATH.read_text(encoding="utf-8"),
        payload_function,
    )
    if payload_source is None:
        raise RuntimeError("Could not read _manifest_timing_payload source.")
    for forbidden_key in (
        "manifest_write_seconds",
        "run_summary_write_seconds",
        "script_total_seconds",
    ):
        if f'"{forbidden_key}"' in payload_source:
            raise RuntimeError(
                f"_manifest_timing_payload must not include {forbidden_key!r}."
            )

    run_function = _function_node(tree, "_run_fcfs_network_wide_validation")
    if run_function is None:
        raise RuntimeError("_run_fcfs_network_wide_validation is missing.")
    calls = []
    _collect_call_names_in_order(run_function, calls)
    if "_manifest_timing_payload" not in calls:
        raise RuntimeError("Run path must build a manifest timing payload.")
    payload_index = calls.index("_manifest_timing_payload")
    write_json_indices = [index for index, name in enumerate(calls) if name == "_write_json"]
    if len(write_json_indices) < 2:
        raise RuntimeError("Run path must write data files and then manifest.json.")
    first_data_json_index = write_json_indices[0]
    manifest_json_index = write_json_indices[-1]
    if payload_index <= first_data_json_index:
        raise RuntimeError(
            "Manifest timing payload must be built after formal data files are written."
        )
    if payload_index >= manifest_json_index:
        raise RuntimeError(
            "Manifest timing payload must be built before manifest.json is written."
        )
    sha256_indices = [index for index, name in enumerate(calls) if name == "_sha256_file"]
    if len(sha256_indices) < 2:
        raise RuntimeError(
            "Run path must hash formal data files and then hash manifest.json once."
        )
    if sha256_indices[-1] <= manifest_json_index:
        raise RuntimeError("Manifest hash must be computed after manifest.json is written.")
    run_source = ast.get_source_segment(
        SCRIPT_PATH.read_text(encoding="utf-8"),
        run_function,
    )
    if run_source is None:
        raise RuntimeError("Could not read run function source.")
    manifest_pos = run_source.find("_write_json(TRIAL_OUTPUT_DIR / MANIFEST_JSON_NAME")
    summary_pos = run_source.find("summary_path.write_text")
    if manifest_pos < 0 or summary_pos < 0 or manifest_pos > summary_pos:
        raise RuntimeError(
            "manifest.json must be written before run_summary.txt is written."
        )
    if "timing_seconds\": _timing_dict(timing)" in run_source:
        raise RuntimeError("manifest.json must not copy the full internal timing dict.")


def _literal_command_strings(node: ast.expr) -> list[str] | None:
    """Return command string parts when the AST node is a literal argv or shell string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        parts: list[str] = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                parts.append(elt.value)
            else:
                return None
        return parts
    return None


def _literal_argv_invokes_forbidden_git(parts: list[str]) -> bool:
    if not parts:
        return False
    tokens = parts[0].split() if len(parts) == 1 else list(parts)
    for index, token in enumerate(tokens):
        if token != "git" and not token.endswith("/git"):
            continue
        if index + 1 >= len(tokens):
            continue
        if tokens[index + 1] in {"add", "commit", "push"}:
            return True
    return False


def _assert_no_git_command_execution(tree: ast.Module) -> None:
    """Reject subprocess/os.system calls whose literal argv runs git add, commit, or push."""
    subprocess_exec_methods = frozenset({"run", "call", "check_call", "check_output"})
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
            continue
        module_name = func.value.id
        method_name = func.attr
        if module_name == "os" and method_name == "system":
            if not node.args:
                continue
            literal = _literal_command_strings(node.args[0])
            if literal is not None and _literal_argv_invokes_forbidden_git(literal):
                raise RuntimeError(
                    "This validation script must not execute Git commands via os.system."
                )
            continue
        if module_name != "subprocess" or method_name not in subprocess_exec_methods:
            continue
        if not node.args:
            continue
        literal = _literal_command_strings(node.args[0])
        if literal is not None and _literal_argv_invokes_forbidden_git(literal):
            raise RuntimeError(
                "This validation script must not execute Git commands via subprocess."
            )


def validate_static_contract() -> None:
    if NUM_VEHICLES != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 999:
        raise RuntimeError("Departure window must be T=0..999.")
    if RANDOM_SEED != 0:
        raise RuntimeError("traffic seed must be 0.")
    if DEMAND_GEN_SEED != 42:
        raise RuntimeError("demand seed must be 42.")
    if VOT_SEED != 1:
        raise RuntimeError("VOT seed must be 1.")
    if NONPARTICIPATION_SEED != 3:
        raise RuntimeError("cohort seed must be 3.")
    if METHOD_NAME != "fcfs":
        raise RuntimeError("method_name must be fcfs.")
    if EXPECTED_VEHICLE_PLAN_SHA256 != (
        "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
    ):
        raise RuntimeError("Vehicle plan hash constant changed.")
    if EXPECTED_PARTICIPATION_ASSIGNMENT_SHA256 != (
        "240948f02de649c69963f54ae6be0cfc387295517a0c01ea5c0a616cf1fe727c"
    ):
        raise RuntimeError("Participation assignment hash constant changed.")
    if EXPECTED_NONPARTICIPATING_NAME_SHA256 != (
        "d03652284a7e07af117c0c60b77b627a52d2185c4cd316a7506710f0680d2529"
    ):
        raise RuntimeError("Nonparticipating name hash constant changed.")
    if EXPECTED_PARTICIPATING_NAME_SHA256 != (
        "79866a40a53f065634d7766b6c944a3083e19cad5558f0b1c4a1306bbabb9481"
    ):
        raise RuntimeError("Participating name hash constant changed.")
    if TMAX != 5000 or EXPECTED_WORLD_T_AFTER_SIM != 5000:
        raise RuntimeError("TMAX and World.T after simulation must be 5000.")
    if INTERNAL_LINK_LENGTH != 200 or OD_CONNECTOR_LENGTH != 200:
        raise RuntimeError("Every link length must be 200 m.")
    if FREE_FLOW_SPEED_KMH != 60:
        raise RuntimeError("Free-flow speed must be 60 km/h.")
    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    _assert_no_git_command_execution(tree)
    _assert_explicit_production_import(tree)
    _assert_run_path_order(tree)
    _assert_no_other_method_control(tree)
    _assert_timing_recording_contract(tree)
    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    validator_calls = []
    _collect_call_names_in_order(validator, validator_calls)
    if "exec_simulation" in validator_calls or PRODUCTION_ENTRY_POINT in validator_calls:
        raise RuntimeError("Static validation must not simulate or evaluate.")
    if "_run_fcfs_network_wide_validation" in validator_calls:
        raise RuntimeError("Static validation must not start the trial.")


# ---------------------------------------------------------------------------
# 8. Run
# ---------------------------------------------------------------------------

def _run_fcfs_network_wide_validation() -> int:
    script_start = time.perf_counter()
    timing = {
        "vehicle_plan_generation_seconds": 0.0,
        "true_vot_and_cohort_build_seconds": 0.0,
        "world_build_seconds": 0.0,
        "vehicle_add_seconds": 0.0,
        "finalize_seconds": 0.0,
        "exec_simulation_seconds": 0.0,
        "completion_validation_seconds": 0.0,
        "network_wide_waiting_time_evaluation_seconds": 0.0,
        "output_build_seconds": 0.0,
        "output_write_seconds": 0.0,
        "elapsed_before_manifest_write_seconds": 0.0,
        "elapsed_before_run_summary_write_seconds": 0.0,
        "manifest_write_seconds": 0.0,
        "run_summary_write_seconds": 0.0,
        "script_total_seconds": 0.0,
    }
    exec_simulation_call_count = 0
    evaluation_call_count = 0

    _refuse_existing_output_directory()

    started = time.perf_counter()
    plans = generate_vehicle_plans()
    plan_audit = verify_vehicle_plans(plans)
    timing["vehicle_plan_generation_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    ordered_names = _ordered_vehicle_names(plans)
    vot_values = generate_true_vot_per_second(len(plans))
    nonparticipating_names = select_nonparticipating_names(ordered_names)
    participating_names = _participating_names(ordered_names, nonparticipating_names)
    cohort_hashes = verify_cohort_hashes(plans, nonparticipating_names, participating_names)
    vot_by_name, cohort_by_name = build_vot_and_cohort_ledgers(
        plans,
        vot_values,
        nonparticipating_names,
    )
    comparison_metadata = build_comparison_metadata(plan_audit, cohort_hashes)
    timing["true_vot_and_cohort_build_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    world = build_world_and_network()
    verify_network_runtime(world)
    timing["world_build_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    add_vehicles_to_world(world, plans)
    timing["vehicle_add_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    world.finalize_scenario()
    timing["finalize_seconds"] = time.perf_counter() - started
    if world.TSIZE != TMAX:
        raise RuntimeError(f"World.TSIZE is {world.TSIZE!r}, expected {TMAX}.")

    started = time.perf_counter()
    world.exec_simulation()
    exec_simulation_call_count = exec_simulation_call_count + 1
    timing["exec_simulation_seconds"] = time.perf_counter() - started
    if exec_simulation_call_count != 1:
        raise RuntimeError(
            f"exec_simulation ran {exec_simulation_call_count} times, expected 1."
        )

    started = time.perf_counter()
    completion = verify_fcfs_full_completion(world, plans)
    timing["completion_validation_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    result = evaluate_network_wide_waiting_time(
        real_world=world,
        method_name=METHOD_NAME,
        evaluated_vehicle_names=ordered_names,
        true_vot_per_second_by_vehicle_name=vot_by_name,
        evaluation_cohort_by_vehicle_name=cohort_by_name,
        vehicle_plan_digest=plan_audit["vehicle_plan_sha256"],
        comparison_metadata=comparison_metadata,
    )
    evaluation_call_count = evaluation_call_count + 1
    timing["network_wide_waiting_time_evaluation_seconds"] = time.perf_counter() - started
    if evaluation_call_count != 1:
        raise RuntimeError(
            f"network-wide evaluation ran {evaluation_call_count} times, expected 1."
        )

    evaluation_facts = verify_evaluation_result(
        result,
        plans,
        vot_by_name,
        cohort_by_name,
        world,
    )

    started = time.perf_counter()
    vehicle_rows = build_vehicle_rows(result)
    cohort_rows = build_cohort_rows(result)
    vot_rows = build_vot_cohort_rows(plans, vot_by_name, cohort_by_name)
    summary_payload = build_summary_payload(result, evaluation_facts)
    plan_payload = {
        "scenario_name": SCENARIO_NAME,
        "validation_scope": VALIDATION_SCOPE,
        "future_compatibility_note": FUTURE_COMPATIBILITY_NOTE,
        "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
        "participation_assignment_sha256": cohort_hashes["participation_assignment_sha256"],
        "nonparticipating_name_sha256": cohort_hashes["nonparticipating_name_sha256"],
        "participating_name_sha256": cohort_hashes["participating_name_sha256"],
        "participating_vehicle_count": PARTICIPATING_VEHICLE_COUNT,
        "nonparticipating_vehicle_count": NONPARTICIPATING_VEHICLE_COUNT,
        "traffic_seed": RANDOM_SEED,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "vot_seed": VOT_SEED,
        "cohort_assignment_seed": NONPARTICIPATION_SEED,
        "first_departure": plan_audit["first_departure"],
        "last_departure": plan_audit["last_departure"],
    }
    timing["output_build_seconds"] = time.perf_counter() - started

    _create_output_directory()

    started = time.perf_counter()
    vehicle_fields = [
        "scenario_name",
        "method_name",
        "vehicle_name",
        "evaluation_cohort",
        "method_specific_participation_status",
        "actual_departure_timestep",
        "actual_arrival_timestep",
        "actual_trip_timesteps",
        "reference_departure_timestep",
        "reference_arrival_timestep",
        "reference_minimum_trip_timesteps",
        "cumulative_waiting_time_timesteps",
        "actual_travel_time_s",
        "minimum_trip_time_s",
        "cumulative_waiting_time_s",
        "true_vot_per_second",
        "weighted_cumulative_waiting_time",
        "route_audit_identity",
        "physical_route_deltat",
        "physical_route_link_lengths",
        "physical_route_link_free_flow_speeds",
    ]
    cohort_fields = [
        "scenario_name",
        "method_name",
        "evaluation_cohort",
        "vehicle_count",
        "total_cumulative_waiting_time_s",
        "average_cumulative_waiting_time_s",
        "total_weighted_cumulative_waiting_time",
        "average_weighted_cumulative_waiting_time",
    ]
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
    _write_csv(TRIAL_OUTPUT_DIR / VEHICLES_CSV_NAME, vehicle_fields, vehicle_rows)
    _write_csv(TRIAL_OUTPUT_DIR / COHORTS_CSV_NAME, cohort_fields, cohort_rows)
    _write_json(TRIAL_OUTPUT_DIR / SUMMARY_JSON_NAME, summary_payload)
    _write_csv(TRIAL_OUTPUT_DIR / VOT_COHORT_CSV_NAME, vot_fields, vot_rows)
    _write_json(TRIAL_OUTPUT_DIR / PLAN_AUDIT_JSON_NAME, plan_payload)
    timing["output_write_seconds"] = time.perf_counter() - started

    file_hashes = {}
    for file_name in DATA_FILE_NAMES:
        file_hashes[file_name] = _sha256_file(TRIAL_OUTPUT_DIR / file_name)

    timing["elapsed_before_manifest_write_seconds"] = time.perf_counter() - script_start
    manifest_timing = _manifest_timing_payload(timing)
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "method_name": METHOD_NAME,
        "node_control_method": NODE_CONTROL_METHOD,
        "validation_scope": VALIDATION_SCOPE,
        "future_compatibility_note": FUTURE_COMPATIBILITY_NOTE,
        "source_fcfs_script": SOURCE_FCFS_SCRIPT,
        "production_module_name": PRODUCTION_MODULE_NAME,
        "production_entry_point": PRODUCTION_ENTRY_POINT,
        "production_commit": PRODUCTION_COMMIT,
        "NUM_VEHICLES": NUM_VEHICLES,
        "departure_start": DEPARTURE_START,
        "departure_end": DEPARTURE_END,
        "traffic_seed": RANDOM_SEED,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "VOT_SEED": VOT_SEED,
        "NONPARTICIPATION_SEED": NONPARTICIPATION_SEED,
        "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
        "participation_assignment_sha256": cohort_hashes["participation_assignment_sha256"],
        "nonparticipating_name_sha256": cohort_hashes["nonparticipating_name_sha256"],
        "participating_name_sha256": cohort_hashes["participating_name_sha256"],
        "participating_vehicle_count": PARTICIPATING_VEHICLE_COUNT,
        "nonparticipating_vehicle_count": NONPARTICIPATING_VEHICLE_COUNT,
        "final_world_t": completion["final_world_t"],
        "final_vehicle_state_counts": completion["final_vehicle_state_counts"],
        "full_trip_completion": completion["full_trip_completion"],
        "traffic_clearance_completed": completion["traffic_clearance_completed"],
        "network_wide_waiting_time_evaluation_completed": True,
        "acwt_s": evaluation_facts["acwt_s"],
        "acwwt": evaluation_facts["acwwt"],
        "participating_cohort_acwt_s": evaluation_facts["participating_acwt_s"],
        "participating_cohort_acwwt": evaluation_facts["participating_acwwt"],
        "nonparticipating_cohort_acwt_s": evaluation_facts["nonparticipating_acwt_s"],
        "nonparticipating_cohort_acwwt": evaluation_facts["nonparticipating_acwwt"],
        "counter_summary": summary_payload["counters"],
        "timing_seconds": manifest_timing,
        "formal_output_file_names": [
            VEHICLES_CSV_NAME,
            COHORTS_CSV_NAME,
            SUMMARY_JSON_NAME,
            VOT_COHORT_CSV_NAME,
            PLAN_AUDIT_JSON_NAME,
            MANIFEST_JSON_NAME,
            RUN_SUMMARY_TXT_NAME,
        ],
        "formal_output_sha256": file_hashes,
    }
    started = time.perf_counter()
    _write_json(TRIAL_OUTPUT_DIR / MANIFEST_JSON_NAME, manifest)
    timing["manifest_write_seconds"] = time.perf_counter() - started
    manifest_sha256 = _sha256_file(TRIAL_OUTPUT_DIR / MANIFEST_JSON_NAME)

    timing["elapsed_before_run_summary_write_seconds"] = time.perf_counter() - script_start
    summary_lines = [
        "FCFS validation trial",
        f"validation_scope: {VALIDATION_SCOPE}",
        FUTURE_COMPATIBILITY_NOTE,
        "Vehicle plan hash: matched",
        "cohort hash: matched",
        "3000 vehicles completed",
        f"full_trip_completion: {completion['full_trip_completion']}",
        f"traffic_clearance_completed: {completion['traffic_clearance_completed']}",
        f"overall ACWT seconds: {evaluation_facts['acwt_s']}",
        f"overall ACWWT: {evaluation_facts['acwwt']}",
        f"participating cohort 2400 ACWT seconds: {evaluation_facts['participating_acwt_s']}",
        f"participating cohort 2400 ACWWT: {evaluation_facts['participating_acwwt']}",
        f"nonparticipating cohort 600 ACWT seconds: {evaluation_facts['nonparticipating_acwt_s']}",
        f"nonparticipating cohort 600 ACWWT: {evaluation_facts['nonparticipating_acwwt']}",
        f"unique physical route count: {evaluation_facts['unique_physical_route_count']}",
        f"Reference replay run count: {evaluation_facts['reference_replay_run_count']}",
        f"Reference reuse count: {evaluation_facts['reference_reuse_count']}",
        f"FCFS simulation seconds: {timing['exec_simulation_seconds']}",
        "network-wide evaluation seconds: "
        f"{timing['network_wide_waiting_time_evaluation_seconds']}",
        f"output build seconds: {timing['output_build_seconds']}",
        f"output write seconds: {timing['output_write_seconds']}",
        f"manifest write seconds: {timing['manifest_write_seconds']}",
        "elapsed before run summary write seconds: "
        f"{timing['elapsed_before_run_summary_write_seconds']}",
        f"manifest sha256: {manifest_sha256}",
        "formal output: success",
        "This script validates the current FCFS condition only.",
    ]
    started = time.perf_counter()
    summary_path = TRIAL_OUTPUT_DIR / RUN_SUMMARY_TXT_NAME
    if summary_path.exists():
        raise FileExistsError(f"Refusing to overwrite {summary_path}.")
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    timing["run_summary_write_seconds"] = time.perf_counter() - started
    timing["script_total_seconds"] = time.perf_counter() - script_start

    print("FCFS validation trial")
    print("Vehicle plan hash: matched")
    print("cohort hash: matched")
    print("3000 vehicles completed")
    print("overall ACWT seconds:", evaluation_facts["acwt_s"])
    print("overall ACWWT:", evaluation_facts["acwwt"])
    print("participating cohort 2400 ACWT seconds:", evaluation_facts["participating_acwt_s"])
    print("participating cohort 2400 ACWWT:", evaluation_facts["participating_acwwt"])
    print("nonparticipating cohort 600 ACWT seconds:", evaluation_facts["nonparticipating_acwt_s"])
    print("nonparticipating cohort 600 ACWWT:", evaluation_facts["nonparticipating_acwwt"])
    print("unique physical route count:", evaluation_facts["unique_physical_route_count"])
    print("Reference replay run count:", evaluation_facts["reference_replay_run_count"])
    print("Reference reuse count:", evaluation_facts["reference_reuse_count"])
    print("FCFS simulation seconds:", timing["exec_simulation_seconds"])
    print(
        "network-wide evaluation seconds:",
        timing["network_wide_waiting_time_evaluation_seconds"],
    )
    print("output build seconds:", timing["output_build_seconds"])
    print("output write seconds:", timing["output_write_seconds"])
    print("manifest write seconds:", timing["manifest_write_seconds"])
    print("run summary write seconds:", timing["run_summary_write_seconds"])
    print("total script seconds:", timing["script_total_seconds"])
    print("formal output: success")
    print("This script validates the current FCFS condition only.")
    print("output directory:", TRIAL_OUTPUT_DIR)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--static-validate-only"]:
        validate_static_contract()
        print("static validation passed")
        return 0
    if len(argv) != 0:
        raise RuntimeError(f"Unknown arguments: {argv!r}.")
    return _run_fcfs_network_wide_validation()


if __name__ == "__main__":
    raise SystemExit(main())
