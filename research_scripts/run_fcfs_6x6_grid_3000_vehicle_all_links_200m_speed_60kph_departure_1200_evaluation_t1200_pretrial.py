"""
FCFS pretrial: 3000 vehicles, all 168 links 200 m, free-flow 60 km/h, departure T=0..1200.

Measures FCFS traffic state at evaluation end T=1200 under research candidate road
conditions (unified 200 m links, 60 km/h free flow, jam density 0.2 veh/m). Same
demand and 6x6 topology as the prior 3000-vehicle departure-1200 FCFS pretrial.
Full trip completion is not required; all-vehicle completion time is not measured.

Network and vehicle-plan generation follow
research_scripts/run_fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial.py
by explicit duplication. That script and TVT-MP trial modules are not imported at
runtime.

Run from the repository root:

    python research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial.py --static-validate-only
    python research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial.py
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from uxsim import World

# ---------------------------------------------------------------------------
# 1. Pretrial constants
# ---------------------------------------------------------------------------

SCENARIO_NAME = (
    "fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_"
    "evaluation_t1200_pretrial_seed_0_demand_seed_42"
)
TRIAL_OUTPUT_DIR_NAME = SCENARIO_NAME

LINK_OCCUPANCY_CSV_NAME = "link_occupancy_at_t1200.csv"

PRETRIAL_PURPOSE = (
    "FCFS pretrial under research candidate road conditions: all 168 links 200 m, "
    "free-flow speed 60 km/h (~16.667 m/s), jam density 0.2 veh/m, with the same "
    "3000-vehicle departure T=0..1200 demand and 6x6 topology as the prior "
    "departure-1200 FCFS pretrial. Observes traffic state at T=1200 after one "
    "exec_simulation. Independent pretrial for before/after road-condition comparison. "
    "Prior information for a future 3000-vehicle TVT-MP trial. Not a TVT-MP benchmark "
    "comparison."
)

NUM_VEHICLES = 3000
VEHICLE_STATE_NAME_SAMPLE_LIMIT = 50
TOP_HIGH_OCCUPANCY_LINK_LIMIT = 25

GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = 36
EXTERNAL_OD_NODE_COUNT = 24
TOTAL_NODE_COUNT = 60
INTERNAL_DIRECTED_LINK_COUNT = 120
OD_CONNECTOR_DIRECTED_LINK_COUNT = 48
TOTAL_LINK_COUNT = 168

DEPARTURE_START = 0
DEPARTURE_END = 1200
MIN_OD_MANHATTAN_DISTANCE = 5

EVALUATION_END_TIMESTEP = 1200
TMAX = 1201
EXPECTED_WORLD_T_AFTER_SIM = 1201
SIMULATED_EVALUATION_TIMESTEPS = 1201

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
FCFS_CLEARANCE_TIMESTEPS = 1
REACTION_TIME = 1

INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2

INTERNAL_LINK_THEORETICAL_CAPACITY = INTERNAL_LINK_LENGTH * JAM_DENSITY
OD_CONNECTOR_THEORETICAL_CAPACITY = OD_CONNECTOR_LENGTH * JAM_DENSITY
INTERNAL_LINKS_TOTAL_THEORETICAL_CAPACITY = (
    INTERNAL_DIRECTED_LINK_COUNT * INTERNAL_LINK_THEORETICAL_CAPACITY
)
EXTERNAL_TO_INTERNAL_CONNECTOR_TOTAL_THEORETICAL_CAPACITY = (
    (OD_CONNECTOR_DIRECTED_LINK_COUNT // 2) * OD_CONNECTOR_THEORETICAL_CAPACITY
)
INTERNAL_TO_EXTERNAL_CONNECTOR_TOTAL_THEORETICAL_CAPACITY = (
    EXTERNAL_TO_INTERNAL_CONNECTOR_TOTAL_THEORETICAL_CAPACITY
)
TOTAL_THEORETICAL_VEHICLE_CAPACITY = (
    INTERNAL_LINKS_TOTAL_THEORETICAL_CAPACITY
    + OD_CONNECTOR_DIRECTED_LINK_COUNT * OD_CONNECTOR_THEORETICAL_CAPACITY
)

# Fundamental diagram (homogeneous link, REACTION_TIME=1, single lane)
BACKWARD_WAVE_SPEED_MPS = 1.0 / (REACTION_TIME * JAM_DENSITY)
FD_CAPACITY_VEH_PER_S = (
    FREE_FLOW_SPEED
    * BACKWARD_WAVE_SPEED_MPS
    * JAM_DENSITY
    / (FREE_FLOW_SPEED + BACKWARD_WAVE_SPEED_MPS)
)
FD_CAPACITY_VEH_PER_H = FD_CAPACITY_VEH_PER_S * 3600.0
CRITICAL_DENSITY_VEH_PER_M = FD_CAPACITY_VEH_PER_S / FREE_FLOW_SPEED
CRITICAL_DENSITY_VEH_PER_KM = CRITICAL_DENSITY_VEH_PER_M * 1000.0
CRITICAL_DENSITY_VEHICLE_COUNT_PER_200M_LINK = CRITICAL_DENSITY_VEH_PER_M * 200.0
CRITICAL_DENSITY_OCCUPANCY_RATIO = CRITICAL_DENSITY_VEH_PER_M / JAM_DENSITY
UXSIM_DEFAULT_CAPACITY_IN_OUT_DIAGNOSTIC_VEH_PER_S = 2.0 * FD_CAPACITY_VEH_PER_S

SPECIFIED_ROUTE_USED = False
ROUTE_ASSIGNMENT_MODE = "uxsim_free_route_choice"

SCHEDULED_DEPARTURE_REACHED_COUNT_DEFINITION = (
    "Count of vehicles whose planned departure_time is less than or equal to "
    f"evaluation_end_timestep ({EVALUATION_END_TIMESTEP}). "
    f"Uses departure_time <= {EVALUATION_END_TIMESTEP} only; it does not "
    "directly mean the vehicle entered the network."
)
SCHEDULED_DEPARTURE_COUNT_ACTUAL_STATE_NOTE = (
    "For actual evaluation-end state, use vehicle_state_counts, "
    "vehicles_on_network_count, completed_count, and link occupancy aggregates."
)

SHORT_HORIZON_TRAVEL_METRICS_NOTE = (
    f"Evaluation ends at T={EVALUATION_END_TIMESTEP} with many vehicles still "
    "not completed. Analyzer travel-time and delay metrics including unfinished "
    "vehicles are not formal performance measures for this pretrial."
)

FULL_TRIP_COMPLETION_NOTE = (
    "This pretrial stops at T=1200. Full trip completion for all vehicles is "
    "not required. The timestep when "
    "all vehicles would complete is not measured."
)

DEPARTURE_END_OBSERVATION_NOTE = (
    "This pretrial observes FCFS traffic state at the departure-end evaluation "
    "timestep T=1200 after a single exec_simulation. No segmented execution or "
    "extension to full completion."
)

DEMAND_INTENSITY_CLASSIFICATION_NOTE = (
    "This pretrial alone does not classify the 3000-vehicle departure 0..1200 "
    "condition as normal demand, quasi-high demand, or high demand."
)

ROAD_CONDITION_NOTE = (
    "All 168 directed links are 200 m. Free-flow speed is 60 km/h (~16.667 m/s). "
    "Jam density is 0.2 veh/m. capacity_in and capacity_out are not passed to "
    "addLink; UXsim default automatic values apply. No additional 1500 veh/h "
    "(0.4167 veh/s) boundary capacity is configured."
)

FD_THEORY_NOTE = (
    "FD capacity q_max ≈ 0.7692 veh/s (~2769 veh/h). Critical density k* ≈ "
    "0.04615 veh/m (~46.15 veh/km). On a 200 m link, k* corresponds to ~9.23 "
    "vehicles; vehicle_count >= critical_density_vehicle_count marks at-or-above "
    "critical density (typically integer counts ≥ 10). Jam-density occupancy ratio "
    "at k* is ~23.08%. UXsim unset capacity_in/out diagnostic expectation: "
    "~2× q_max veh/s (~1.538 veh/s); this script does not set those parameters."
)

OCCUPANCY_RATIO_JAM_DENSITY_NOTE = (
    "occupancy_ratio uses jam-density theoretical capacity (length × 0.2 veh/m, "
    "40 vehicles per 200 m link). "
    "It is not FD critical-density occupancy."
)

CRITICAL_DENSITY_SNAPSHOT_NOTE = (
    "Links can satisfy vehicle_count >= critical_density_vehicle_count (~9.23) "
    "while jam-density occupancy remains below 90%. Snapshot vehicle counts alone "
    "do not fully identify dynamic traffic regime on each link."
)

ROAD_CONDITION_COMPARISON_NOTE = (
    "Independent FCFS pretrial for comparing road-condition changes against the "
    "prior 3000-vehicle departure-1200 pretrial (400 m / 300 m links, 20 m/s)."
)

VEHICLE_PLAN_DEMAND_MATCH_NOTE = (
    "Vehicle plan generation uses the same NUM_VEHICLES, departure window, OD "
    "rules, and DEMAND_GEN_SEED as the prior departure-1200 pretrial. "
    "vehicle_plan_sha256 in output can be compared after execution; this script "
    "does not assert equality before run."
)

MANIFEST_TIMING_SCOPE_NOTE = (
    f"pre_manifest_script_total_seconds ends after {LINK_OCCUPANCY_CSV_NAME}, "
    "vehicle_state_summary.csv, and vehicle_plan_audit.json are written. "
    "manifest.json write time and run_summary.txt write time are not included "
    "in manifest timing fields."
)

RUN_SUMMARY_TIMING_SCOPE_NOTE = (
    "run_summary.txt write time is not included in the timing lines above. "
    "run_summary_write_seconds is appended on the last line after the file is closed."
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME
SCRIPT_PATH = Path(__file__).resolve()

FORBIDDEN_RUNTIME_IMPORT_SUBSTRINGS = (
    "run_tvt_mp_6x6_grid_high_demand_5000_vehicle_early_scaling_benchmark",
    "run_tvt_mp_6x6_grid_high_demand_1000_vehicle_short_benchmark",
    "run_fcfs_6x6_grid_high_demand_5000_vehicle_eval_600_comparison_trial",
    "run_fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial",
    "tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand",
)


@dataclass
class TimingRecord:
    vehicle_plan_generation_s: float = 0.0
    world_build_s: float = 0.0
    vehicle_add_s: float = 0.0
    finalize_s: float = 0.0
    exec_simulation_s: float = 0.0
    result_collection_s: float = 0.0
    pre_manifest_output_write_s: float = 0.0
    pre_manifest_script_total_s: float = 0.0
    manifest_write_s: float = 0.0
    run_summary_write_s: float = 0.0


# ---------------------------------------------------------------------------
# 2. Network names and link specs (same 6x6 structure as base FCFS scaling scripts)
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
                (
                    f"h_{row}_{column}_{column + 1}",
                    left_node,
                    right_node,
                    INTERNAL_LINK_LENGTH,
                    0,
                )
            )
            internal.append(
                (
                    f"h_{row}_{column + 1}_{column}",
                    right_node,
                    left_node,
                    INTERNAL_LINK_LENGTH,
                    0,
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
                    1,
                )
            )
            internal.append(
                (
                    f"v_{row + 1}_{row}_{column}",
                    lower_node,
                    upper_node,
                    INTERNAL_LINK_LENGTH,
                    1,
                )
            )

    for column in range(GRID_SIZE):
        top_node = f"top_{column}"
        bottom_node = f"bottom_{column}"
        north_grid = _grid_node_name(0, column)
        south_grid = _grid_node_name(GRID_SIZE - 1, column)
        connectors.append(
            (f"top_{column}_to_g_0_{column}", top_node, north_grid, OD_CONNECTOR_LENGTH, 1)
        )
        connectors.append(
            (f"g_0_{column}_to_top_{column}", north_grid, top_node, OD_CONNECTOR_LENGTH, 1)
        )
        connectors.append(
            (
                f"bottom_{column}_to_g_5_{column}",
                bottom_node,
                south_grid,
                OD_CONNECTOR_LENGTH,
                1,
            )
        )
        connectors.append(
            (
                f"g_5_{column}_to_bottom_{column}",
                south_grid,
                bottom_node,
                OD_CONNECTOR_LENGTH,
                1,
            )
        )

    for row in range(GRID_SIZE):
        left_node = f"left_{row}"
        right_node = f"right_{row}"
        west_grid = _grid_node_name(row, 0)
        east_grid = _grid_node_name(row, GRID_SIZE - 1)
        connectors.append(
            (f"left_{row}_to_g_{row}_0", left_node, west_grid, OD_CONNECTOR_LENGTH, 0)
        )
        connectors.append(
            (f"g_{row}_0_to_left_{row}", west_grid, left_node, OD_CONNECTOR_LENGTH, 0)
        )
        connectors.append(
            (f"right_{row}_to_g_{row}_5", right_node, east_grid, OD_CONNECTOR_LENGTH, 0)
        )
        connectors.append(
            (f"g_{row}_5_to_right_{row}", east_grid, right_node, OD_CONNECTOR_LENGTH, 0)
        )

    return tuple(internal), tuple(connectors)


INTERNAL_GRID_NODES = _internal_grid_node_names()
EXTERNAL_OD_NODES = _external_od_node_names()
OD_TO_GRID_COORD = _od_to_grid_coord_map()
INTERNAL_LINK_SPECS, OD_CONNECTOR_LINK_SPECS = _build_link_specs()
ALL_LINK_SPECS = INTERNAL_LINK_SPECS + OD_CONNECTOR_LINK_SPECS

EXTERNAL_OD_NODE_SET = set(EXTERNAL_OD_NODES)
INTERNAL_GRID_NODE_SET = set(INTERNAL_GRID_NODES)

INTERNAL_LINK_NAME_SET = {spec[0] for spec in INTERNAL_LINK_SPECS}
OD_CONNECTOR_LINK_NAME_SET = {spec[0] for spec in OD_CONNECTOR_LINK_SPECS}

def _manhattan_distance(origin_coord, destination_coord) -> int:
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


def _classify_link(start_node: str, end_node: str) -> tuple[str, str]:
    start_external = start_node in EXTERNAL_OD_NODE_SET
    end_external = end_node in EXTERNAL_OD_NODE_SET
    if start_external and not end_external:
        return "connector", "external_to_internal"
    if not start_external and end_external:
        return "connector", "internal_to_external"
    if not start_external and not end_external:
        return "internal", "internal"
    raise RuntimeError(
        f"Unexpected link endpoints {start_node!r} -> {end_node!r}."
    )


def _critical_density_vehicle_count_for_length(length: float) -> float:
    return CRITICAL_DENSITY_VEH_PER_M * length


def _theoretical_vehicle_capacity(length: float) -> float:
    return length * JAM_DENSITY


def _fundamental_diagram_manifest_payload() -> dict:
    return {
        "reaction_time_s": REACTION_TIME,
        "backward_wave_speed_mps": BACKWARD_WAVE_SPEED_MPS,
        "fd_capacity_veh_per_s": FD_CAPACITY_VEH_PER_S,
        "fd_capacity_veh_per_h": FD_CAPACITY_VEH_PER_H,
        "critical_density_veh_per_m": CRITICAL_DENSITY_VEH_PER_M,
        "critical_density_veh_per_km": CRITICAL_DENSITY_VEH_PER_KM,
        "critical_density_vehicle_count_per_200m_link": (
            CRITICAL_DENSITY_VEHICLE_COUNT_PER_200M_LINK
        ),
        "critical_density_occupancy_ratio_vs_jam_density": (
            CRITICAL_DENSITY_OCCUPANCY_RATIO
        ),
        "uxsim_default_capacity_in_out_diagnostic_veh_per_s": (
            UXSIM_DEFAULT_CAPACITY_IN_OUT_DIAGNOSTIC_VEH_PER_S
        ),
        "capacity_in_out_explicitly_set_by_script": False,
        "fd_theory_note": FD_THEORY_NOTE,
        "occupancy_ratio_jam_density_note": OCCUPANCY_RATIO_JAM_DENSITY_NOTE,
        "critical_density_snapshot_note": CRITICAL_DENSITY_SNAPSHOT_NOTE,
    }


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
        manhattan_distance = _manhattan_distance(
            origin_grid_coord,
            destination_grid_coord,
        )
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
        vehicle_index += 1
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
    external = set(EXTERNAL_OD_NODES)
    names = []
    origins = []
    destinations = []
    departures = []
    distances = []
    previous_departure = None
    for index, plan in enumerate(plans):
        expected_name = f"veh_{index}"
        if plan["name"] != expected_name:
            raise RuntimeError(
                f"Vehicle plan {index} name is {plan['name']!r}, expected {expected_name!r}."
            )
        names.append(plan["name"])
        if plan["origin"] == plan["destination"]:
            raise RuntimeError(f"{plan['name']} origin equals destination.")
        if plan["origin"] not in external or plan["destination"] not in external:
            raise RuntimeError(f"{plan['name']} OD is not an external OD node.")
        if plan["manhattan_distance"] < MIN_OD_MANHATTAN_DISTANCE:
            raise RuntimeError(
                f"{plan['name']} Manhattan distance is {plan['manhattan_distance']}."
            )
        departure_time = plan["departure_time"]
        if previous_departure is not None and departure_time < previous_departure:
            raise RuntimeError(f"{plan['name']} departure decreased.")
        previous_departure = departure_time
        origins.append(plan["origin"])
        destinations.append(plan["destination"])
        departures.append(departure_time)
        distances.append(plan["manhattan_distance"])
    if len(set(names)) != NUM_VEHICLES:
        raise RuntimeError("Vehicle names are not unique.")
    if departures[0] != DEPARTURE_START:
        raise RuntimeError(f"First departure is {departures[0]!r}, expected {DEPARTURE_START}.")
    if departures[-1] != DEPARTURE_END:
        raise RuntimeError(f"Last departure is {departures[-1]!r}, expected {DEPARTURE_END}.")
    digest = _vehicle_plan_digest(plans)
    return {
        "plan_count": len(plans),
        "first_departure": departures[0],
        "last_departure": departures[-1],
        "minimum_manhattan_distance": min(distances),
        "average_manhattan_distance": sum(distances) / len(distances),
        "maximum_manhattan_distance": max(distances),
        "origin_count": len(set(origins)),
        "destination_count": len(set(destinations)),
        "vehicle_plan_sha256": digest,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "min_od_manhattan_distance": MIN_OD_MANHATTAN_DISTANCE,
        "departure_window": f"T={DEPARTURE_START}..{DEPARTURE_END}",
        "specified_route": False,
        "route_assignment_mode": ROUTE_ASSIGNMENT_MODE,
    }


# ---------------------------------------------------------------------------
# 4. World, FCFS setup, simulation checks
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
    eligible_names = {node.name for node in eligible_nodes}
    internal_set = set(INTERNAL_GRID_NODES)
    if eligible_names != internal_set:
        missing = internal_set - eligible_names
        extra = eligible_names - internal_set
        raise RuntimeError(
            "Eligible node set must equal internal 36 grid nodes. "
            f"missing={sorted(missing)!r}, extra={sorted(extra)!r}."
        )
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

    fcfs_nodes = []
    for node_name in INTERNAL_GRID_NODES:
        node = world.get_node(node_name)
        if node.order_control_type != "fcfs":
            raise RuntimeError(f"{node_name} order_control_type is not fcfs.")
        if node.order_control_clearance_timesteps != FCFS_CLEARANCE_TIMESTEPS:
            raise RuntimeError(f"{node_name} clearance is not {FCFS_CLEARANCE_TIMESTEPS}.")
        fcfs_nodes.append(node_name)
    if sorted(fcfs_nodes) != sorted(INTERNAL_GRID_NODES):
        raise RuntimeError("FCFS node list does not match internal grid nodes.")
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

    eligible_names = {
        node.name for node in world.NODES if node.order_control_eligible is True
    }
    if eligible_names != set(INTERNAL_GRID_NODES):
        raise RuntimeError("Runtime eligible set is not internal 36 nodes.")

    for link_name, start_node, end_node, length, _signal_group in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        if link.start_node.name != start_node or link.end_node.name != end_node:
            raise RuntimeError(f"Link {link_name} endpoints do not match spec.")
        if link.length != length:
            raise RuntimeError(f"Link {link_name} length is {link.length!r}.")
        if link.number_of_lanes != NUMBER_OF_LANES:
            raise RuntimeError(f"Link {link_name} lane count is not 1.")
        if link.merge_priority != MERGE_PRIORITY:
            raise RuntimeError(f"Link {link_name} merge priority is not 1.")
        if link.free_flow_speed != FREE_FLOW_SPEED or link.u != FREE_FLOW_SPEED:
            raise RuntimeError(
                f"Link {link_name} free-flow speed is not {FREE_FLOW_SPEED!r} m/s."
            )
        if abs(link.u - FREE_FLOW_SPEED_KMH / 3.6) > 1e-9:
            raise RuntimeError(f"Link {link_name} free-flow speed is not 60 km/h equivalent.")
        if link.jam_density != JAM_DENSITY or link.kappa != JAM_DENSITY:
            raise RuntimeError(f"Link {link_name} jam density is not 0.2.")
        if length != 200:
            raise RuntimeError(f"Link {link_name} length is not 200 m.")
        expected_capacity = _theoretical_vehicle_capacity(length)
        if expected_capacity != 40:
            raise RuntimeError(f"Link {link_name} theoretical jam-density capacity is not 40.")

    if TOTAL_THEORETICAL_VEHICLE_CAPACITY != 6720:
        raise RuntimeError("Total theoretical vehicle capacity is not 6720.")
    if INTERNAL_LINK_THEORETICAL_CAPACITY != 40:
        raise RuntimeError("Internal link theoretical capacity is not 40.")
    if OD_CONNECTOR_THEORETICAL_CAPACITY != 40:
        raise RuntimeError("Connector theoretical capacity is not 40.")
    if INTERNAL_LINKS_TOTAL_THEORETICAL_CAPACITY != 4800:
        raise RuntimeError("Internal links total theoretical capacity is not 4800.")
    if EXTERNAL_TO_INTERNAL_CONNECTOR_TOTAL_THEORETICAL_CAPACITY != 960:
        raise RuntimeError("External-to-internal connector total capacity is not 960.")


def add_vehicles_to_world(world: World, plans: list[dict]) -> None:
    for plan in plans:
        world.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )


def verify_world_time_after_simulation(world: World) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )


def _sample_vehicle_names(names: list[str]) -> dict:
    sorted_names = sorted(names)
    total_count = len(sorted_names)
    if total_count <= VEHICLE_STATE_NAME_SAMPLE_LIMIT:
        return {
            "total_count": total_count,
            "sampled_vehicle_names": sorted_names,
            "sample_limit": VEHICLE_STATE_NAME_SAMPLE_LIMIT,
            "names_truncated": False,
        }
    return {
        "total_count": total_count,
        "sampled_vehicle_names": sorted_names[:VEHICLE_STATE_NAME_SAMPLE_LIMIT],
        "sample_limit": VEHICLE_STATE_NAME_SAMPLE_LIMIT,
        "names_truncated": True,
    }


def collect_evaluation_end_vehicle_summary(world: World, plans: list[dict]) -> dict:
    state_names: dict[str, list[str]] = {}
    state_counts: dict[str, int] = {}
    scheduled_departure_reached_names = []
    scheduled_departure_not_reached_names = []
    on_network_names = []
    completed_names = []
    not_completed_names = []

    departure_by_name = {plan["name"]: plan["departure_time"] for plan in plans}

    for vehicle in world.VEHICLES.values():
        state_value = vehicle.state
        if type(state_value) is not str:
            raise RuntimeError(
                f"Vehicle {vehicle.name!r} state is not a str: {state_value!r}."
            )
        state_counts[state_value] = state_counts.get(state_value, 0) + 1
        state_names.setdefault(state_value, []).append(vehicle.name)

        departure_time = departure_by_name.get(vehicle.name)
        if departure_time is None:
            raise RuntimeError(f"Vehicle {vehicle.name!r} is missing from vehicle plans.")
        if float(departure_time) <= float(EVALUATION_END_TIMESTEP):
            scheduled_departure_reached_names.append(vehicle.name)
        else:
            scheduled_departure_not_reached_names.append(vehicle.name)

        if state_value == "end":
            completed_names.append(vehicle.name)
        else:
            not_completed_names.append(vehicle.name)

        if state_value in ("run", "wait"):
            on_network_names.append(vehicle.name)

    if len(world.VEHICLES) != NUM_VEHICLES:
        raise RuntimeError(
            f"World vehicle count is {len(world.VEHICLES)}, expected {NUM_VEHICLES}."
        )
    if sum(state_counts.values()) != NUM_VEHICLES:
        raise RuntimeError("Vehicle state counts do not sum to NUM_VEHICLES.")

    end_count = state_counts.get("end", 0)
    if len(completed_names) != end_count:
        raise RuntimeError(
            f"completed count {len(completed_names)} does not match state end count {end_count}."
        )

    state_name_samples = {
        state_value: _sample_vehicle_names(names)
        for state_value, names in sorted(state_names.items())
    }

    return {
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "vehicle_total_count": NUM_VEHICLES,
        "vehicle_state_counts": dict(sorted(state_counts.items())),
        "vehicle_state_name_samples": state_name_samples,
        "completed_count": len(completed_names),
        "not_completed_count": len(not_completed_names),
        "scheduled_departure_reached_count": len(scheduled_departure_reached_names),
        "scheduled_departure_not_reached_count": len(
            scheduled_departure_not_reached_names
        ),
        "scheduled_departure_reached_count_definition": (
            SCHEDULED_DEPARTURE_REACHED_COUNT_DEFINITION
        ),
        "scheduled_departure_count_actual_state_note": (
            SCHEDULED_DEPARTURE_COUNT_ACTUAL_STATE_NOTE
        ),
        "vehicles_on_network_count": len(on_network_names),
        "run_count": state_counts.get("run", 0),
        "wait_count": state_counts.get("wait", 0),
    }


def _occupancy_threshold_counts(rows: list[dict]) -> dict:
    thresholds = {
        "links_at_or_above_100_percent": 0,
        "links_at_or_above_90_percent": 0,
        "links_at_or_above_75_percent": 0,
        "links_at_or_above_50_percent": 0,
    }
    for row in rows:
        ratio = row["occupancy_ratio"]
        if ratio >= 1.0:
            thresholds["links_at_or_above_100_percent"] += 1
        if ratio >= 0.9:
            thresholds["links_at_or_above_90_percent"] += 1
        if ratio >= 0.75:
            thresholds["links_at_or_above_75_percent"] += 1
        if ratio >= 0.5:
            thresholds["links_at_or_above_50_percent"] += 1
    return thresholds


def _aggregate_link_group(rows: list[dict]) -> dict:
    empty_critical = {
        "links_at_or_above_critical_density": 0,
        "critical_density_vehicle_count_per_link": (
            CRITICAL_DENSITY_VEHICLE_COUNT_PER_200M_LINK
        ),
        "critical_density_occupancy_ratio": CRITICAL_DENSITY_OCCUPANCY_RATIO,
    }
    if not rows:
        return {
            "link_count": 0,
            "total_theoretical_vehicle_capacity": 0.0,
            "vehicle_count": 0,
            "aggregate_occupancy_ratio": 0.0,
            "links_at_or_above_100_percent": 0,
            "links_at_or_above_90_percent": 0,
            "links_at_or_above_75_percent": 0,
            "links_at_or_above_50_percent": 0,
            **empty_critical,
        }
    total_capacity = sum(row["theoretical_vehicle_capacity"] for row in rows)
    vehicle_count = sum(row["vehicle_count"] for row in rows)
    aggregate_ratio = vehicle_count / total_capacity if total_capacity > 0 else 0.0
    thresholds = _occupancy_threshold_counts(rows)
    links_at_or_above_critical = sum(
        1 for row in rows if row["at_or_above_critical_density"] is True
    )
    return {
        "link_count": len(rows),
        "total_theoretical_vehicle_capacity": total_capacity,
        "vehicle_count": vehicle_count,
        "aggregate_occupancy_ratio": aggregate_ratio,
        **thresholds,
        "links_at_or_above_critical_density": links_at_or_above_critical,
        "critical_density_vehicle_count_per_link": (
            CRITICAL_DENSITY_VEHICLE_COUNT_PER_200M_LINK
        ),
        "critical_density_occupancy_ratio": CRITICAL_DENSITY_OCCUPANCY_RATIO,
    }


def collect_link_occupancy_at_evaluation_end(world: World) -> dict:
    per_link_rows = []
    capacity_exceeded_links = []

    for link_name, start_node, end_node, length, _signal_group in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        link_type, direction_type = _classify_link(start_node, end_node)
        theoretical_capacity = _theoretical_vehicle_capacity(length)
        critical_density_vehicle_count = _critical_density_vehicle_count_for_length(length)
        vehicle_count = len(link.vehicles)
        at_or_above_critical_density = (
            vehicle_count >= critical_density_vehicle_count
        )
        occupancy_ratio = (
            vehicle_count / theoretical_capacity if theoretical_capacity > 0 else 0.0
        )
        if vehicle_count > theoretical_capacity:
            capacity_exceeded_links.append(
                {
                    "link_name": link_name,
                    "vehicle_count": vehicle_count,
                    "theoretical_vehicle_capacity": theoretical_capacity,
                    "excess_vehicles": vehicle_count - theoretical_capacity,
                }
            )
        per_link_rows.append(
            {
                "link_name": link_name,
                "link_type": link_type,
                "direction_type": direction_type,
                "length": length,
                "theoretical_vehicle_capacity": theoretical_capacity,
                "critical_density_vehicle_count": critical_density_vehicle_count,
                "vehicle_count": vehicle_count,
                "at_or_above_critical_density": at_or_above_critical_density,
                "occupancy_ratio": occupancy_ratio,
            }
        )

    per_link_rows.sort(key=lambda row: row["link_name"])

    internal_rows = [row for row in per_link_rows if row["link_type"] == "internal"]
    external_to_internal_rows = [
        row
        for row in per_link_rows
        if row["direction_type"] == "external_to_internal"
    ]
    internal_to_external_rows = [
        row
        for row in per_link_rows
        if row["direction_type"] == "internal_to_external"
    ]

    top_high_occupancy = sorted(
        per_link_rows,
        key=lambda row: (-row["occupancy_ratio"], row["link_name"]),
    )[:TOP_HIGH_OCCUPANCY_LINK_LIMIT]

    return {
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "per_link_rows": per_link_rows,
        "capacity_exceeded_links": capacity_exceeded_links,
        "capacity_exceeded_link_count": len(capacity_exceeded_links),
        "aggregates": {
            "internal_links": _aggregate_link_group(internal_rows),
            "external_to_internal_connectors": _aggregate_link_group(
                external_to_internal_rows
            ),
            "internal_to_external_connectors": _aggregate_link_group(
                internal_to_external_rows
            ),
            "all_links": _aggregate_link_group(per_link_rows),
        },
        "top_high_occupancy_links": top_high_occupancy,
    }


def collect_traffic_analyzer_summary(world: World) -> dict:
    analyzer = world.analyzer
    completed_trips = int(analyzer.trip_completed)
    total_trips = int(analyzer.trip_all)
    completed_ratio = completed_trips / total_trips if total_trips else 0.0
    total_travel_time = float(analyzer.total_travel_time)
    average_travel_time = float(analyzer.average_travel_time)
    average_delay = float(analyzer.average_delay)
    delay_ratio = (
        average_delay / average_travel_time
        if completed_trips > 0 and average_travel_time > 0
        else None
    )
    total_distance_traveled = float(analyzer.total_distance_traveled)
    average_speed = None
    average_speed_source = "not available"
    if hasattr(analyzer, "average_speed"):
        speed_value = analyzer.average_speed
        if isinstance(speed_value, (int, float)) and speed_value == speed_value:
            average_speed = float(speed_value)
            average_speed_source = (
                "world.analyzer.average_speed (simulator aggregate over recorded samples)"
            )
    return {
        "total_vehicles": total_trips,
        "completed_trips": completed_trips,
        "completed_ratio": completed_ratio,
        "total_travel_time": total_travel_time,
        "average_travel_time": average_travel_time,
        "average_delay": average_delay,
        "delay_ratio": delay_ratio,
        "total_distance_traveled": total_distance_traveled,
        "average_speed": average_speed,
        "average_speed_source": average_speed_source,
        "short_horizon_travel_metrics_note": SHORT_HORIZON_TRAVEL_METRICS_NOTE,
    }


def _seconds_per_evaluation_timestep(exec_simulation_s: float) -> float:
    return exec_simulation_s / SIMULATED_EVALUATION_TIMESTEPS


def _manifest_timing_payload(timing: TimingRecord) -> dict:
    return {
        "vehicle_plan_generation_seconds": timing.vehicle_plan_generation_s,
        "world_build_seconds": timing.world_build_s,
        "vehicle_add_seconds": timing.vehicle_add_s,
        "finalize_seconds": timing.finalize_s,
        "exec_simulation_seconds": timing.exec_simulation_s,
        "result_collection_seconds": timing.result_collection_s,
        "pre_manifest_output_write_seconds": timing.pre_manifest_output_write_s,
        "pre_manifest_script_total_seconds": timing.pre_manifest_script_total_s,
        "seconds_per_simulated_timestep": _seconds_per_evaluation_timestep(
            timing.exec_simulation_s
        ),
        "timing_scope_note": MANIFEST_TIMING_SCOPE_NOTE,
    }


def _run_summary_timing_lines(timing: TimingRecord) -> list[str]:
    payload = _manifest_timing_payload(timing)
    lines = [
        f"vehicle_plan_generation seconds: {payload['vehicle_plan_generation_seconds']}",
        f"world_build seconds: {payload['world_build_seconds']}",
        f"vehicle_add seconds: {payload['vehicle_add_seconds']}",
        f"finalize seconds: {payload['finalize_seconds']}",
        f"exec_simulation seconds: {payload['exec_simulation_seconds']}",
        f"result_collection seconds: {payload['result_collection_seconds']}",
        (
            "pre_manifest_output_write seconds: "
            f"{payload['pre_manifest_output_write_seconds']}"
        ),
        f"pre_manifest_script_total seconds: {payload['pre_manifest_script_total_seconds']}",
        f"seconds per simulated timestep: {payload['seconds_per_simulated_timestep']}",
        f"timing scope note: {payload['timing_scope_note']}",
        f"manifest_write seconds: {timing.manifest_write_s}",
        f"run_summary timing scope note: {RUN_SUMMARY_TIMING_SCOPE_NOTE}",
    ]
    return lines


# ---------------------------------------------------------------------------
# 5. Output writers
# ---------------------------------------------------------------------------

def write_link_occupancy_csv(path: Path, link_summary: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    fieldnames = [
        "link_name",
        "link_type",
        "direction_type",
        "length",
        "theoretical_vehicle_capacity",
        "critical_density_vehicle_count",
        "vehicle_count",
        "at_or_above_critical_density",
        "occupancy_ratio",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in link_summary["per_link_rows"]:
            writer.writerow(row)


def write_vehicle_state_summary_csv(path: Path, vehicle_summary: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerow(["evaluation_end_timestep", vehicle_summary["evaluation_end_timestep"]])
        writer.writerow(["vehicle_total_count", vehicle_summary["vehicle_total_count"]])
        for state_value, count in vehicle_summary["vehicle_state_counts"].items():
            writer.writerow([f"state_count_{state_value}", count])
        writer.writerow(["completed_count", vehicle_summary["completed_count"]])
        writer.writerow(["not_completed_count", vehicle_summary["not_completed_count"]])
        writer.writerow(
            ["vehicles_on_network_count", vehicle_summary["vehicles_on_network_count"]]
        )
        writer.writerow(["run_count", vehicle_summary["run_count"]])
        writer.writerow(["wait_count", vehicle_summary["wait_count"]])
        writer.writerow(
            [
                "scheduled_departure_reached_count",
                vehicle_summary["scheduled_departure_reached_count"],
            ]
        )
        writer.writerow(
            [
                "scheduled_departure_not_reached_count",
                vehicle_summary["scheduled_departure_not_reached_count"],
            ]
        )


def write_vehicle_plan_audit_json(path: Path, plan_audit: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(plan_audit, handle, indent=2)
        handle.write("\n")


def write_manifest_json(
    path: Path,
    timing: TimingRecord,
    plan_audit: dict,
    vehicle_summary: dict,
    link_summary: dict,
    traffic_summary: dict,
) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    manifest = {
        "scenario": SCENARIO_NAME,
        "pretrial_purpose": PRETRIAL_PURPOSE,
        "formal_performance_comparison": False,
        "future_3000_vehicle_tvt_mp_pretrial": True,
        "departure_end_observation_pretrial": True,
        "full_trip_completion_not_required": True,
        "all_vehicle_completion_time_not_measured": True,
        "full_trip_completion_note": FULL_TRIP_COMPLETION_NOTE,
        "departure_end_observation_note": DEPARTURE_END_OBSERVATION_NOTE,
        "demand_intensity_classification_note": DEMAND_INTENSITY_CLASSIFICATION_NOTE,
        "vehicle_plan_demand_match_note": VEHICLE_PLAN_DEMAND_MATCH_NOTE,
        "road_condition_note": ROAD_CONDITION_NOTE,
        "road_condition_comparison_note": ROAD_CONDITION_COMPARISON_NOTE,
        "fundamental_diagram": _fundamental_diagram_manifest_payload(),
        "order_control": {
            "type": "fcfs",
            "clearance_timesteps": FCFS_CLEARANCE_TIMESTEPS,
            "fcfs_node_count": INTERNAL_GRID_NODE_COUNT,
            "fcfs_node_names": list(INTERNAL_GRID_NODES),
        },
        "network_conditions": {
            "grid_size": GRID_SIZE,
            "internal_node_count": INTERNAL_GRID_NODE_COUNT,
            "external_od_node_count": EXTERNAL_OD_NODE_COUNT,
            "total_node_count": TOTAL_NODE_COUNT,
            "internal_directed_link_count": INTERNAL_DIRECTED_LINK_COUNT,
            "od_connector_directed_link_count": OD_CONNECTOR_DIRECTED_LINK_COUNT,
            "total_link_count": TOTAL_LINK_COUNT,
            "merge_priority": MERGE_PRIORITY,
            "number_of_lanes": NUMBER_OF_LANES,
            "reaction_time": REACTION_TIME,
            "all_links_length_m": 200,
            "internal_link_length": INTERNAL_LINK_LENGTH,
            "od_connector_length": OD_CONNECTOR_LENGTH,
            "free_flow_speed_mps": FREE_FLOW_SPEED,
            "free_flow_speed_kmh": FREE_FLOW_SPEED_KMH,
            "jam_density": JAM_DENSITY,
            "capacity_in_out_passed_to_add_link": False,
            "internal_link_theoretical_capacity": INTERNAL_LINK_THEORETICAL_CAPACITY,
            "connector_theoretical_capacity": OD_CONNECTOR_THEORETICAL_CAPACITY,
            "internal_links_total_theoretical_capacity": (
                INTERNAL_LINKS_TOTAL_THEORETICAL_CAPACITY
            ),
            "external_to_internal_connector_total_theoretical_capacity": (
                EXTERNAL_TO_INTERNAL_CONNECTOR_TOTAL_THEORETICAL_CAPACITY
            ),
            "total_theoretical_vehicle_capacity": TOTAL_THEORETICAL_VEHICLE_CAPACITY,
        },
        "demand_conditions": {
            "num_vehicles": NUM_VEHICLES,
            "departure_start": DEPARTURE_START,
            "departure_end": DEPARTURE_END,
            "departure_window": f"T={DEPARTURE_START}..{DEPARTURE_END}",
            "min_od_manhattan_distance": MIN_OD_MANHATTAN_DISTANCE,
        },
        "seeds": {
            "random_seed": RANDOM_SEED,
            "demand_gen_seed": DEMAND_GEN_SEED,
        },
        "routing": {
            "free_route_choice": True,
            "specified_route": False,
            "route_assignment_mode": ROUTE_ASSIGNMENT_MODE,
        },
        "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
        "vehicle_plan_audit": plan_audit,
        "evaluation": {
            "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
            "tmax": TMAX,
            "expected_world_t_after_simulation": EXPECTED_WORLD_T_AFTER_SIM,
            "simulated_evaluation_timesteps": SIMULATED_EVALUATION_TIMESTEPS,
        },
        "world_t_after_simulation": EXPECTED_WORLD_T_AFTER_SIM,
        "vehicle_state_summary": vehicle_summary,
        "completion": {
            "completed_count": vehicle_summary["completed_count"],
            "not_completed_count": vehicle_summary["not_completed_count"],
            "full_trip_completion_not_required": True,
        },
        "analyzer_aggregates": traffic_summary,
        "link_occupancy_at_evaluation_end": {
            "aggregates": link_summary["aggregates"],
            "capacity_exceeded_links": link_summary["capacity_exceeded_links"],
            "capacity_exceeded_link_count": link_summary["capacity_exceeded_link_count"],
            "top_high_occupancy_links": link_summary["top_high_occupancy_links"],
        },
        "timing": _manifest_timing_payload(timing),
        "production_unchanged": True,
        "existing_files_unchanged": True,
        "output_directory": str(TRIAL_OUTPUT_DIR),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def _fd_summary_lines(link_summary: dict) -> list[str]:
    fd = _fundamental_diagram_manifest_payload()
    aggregates = link_summary["aggregates"]
    lines = [
        f"FD capacity: {fd['fd_capacity_veh_per_s']} veh/s, "
        f"{fd['fd_capacity_veh_per_h']} veh/h",
        f"critical density: {fd['critical_density_veh_per_m']} veh/m, "
        f"{fd['critical_density_veh_per_km']} veh/km",
        (
            f"critical-density vehicles per 200 m link: "
            f"{fd['critical_density_vehicle_count_per_200m_link']}"
        ),
        (
            f"critical-density occupancy ratio (vs jam-density capacity): "
            f"{fd['critical_density_occupancy_ratio_vs_jam_density']}"
        ),
        (
            "links at or above critical density — internal: "
            f"{aggregates['internal_links']['links_at_or_above_critical_density']}, "
            "external->internal: "
            f"{aggregates['external_to_internal_connectors']['links_at_or_above_critical_density']}, "
            "internal->external: "
            f"{aggregates['internal_to_external_connectors']['links_at_or_above_critical_density']}, "
            "all: "
            f"{aggregates['all_links']['links_at_or_above_critical_density']}"
        ),
        OCCUPANCY_RATIO_JAM_DENSITY_NOTE,
        CRITICAL_DENSITY_SNAPSHOT_NOTE,
    ]
    return lines


def write_run_summary_txt(
    path: Path,
    vehicle_summary: dict,
    link_summary: dict,
    timing: TimingRecord,
) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    internal = link_summary["aggregates"]["internal_links"]
    ext_in = link_summary["aggregates"]["external_to_internal_connectors"]
    ext_out = link_summary["aggregates"]["internal_to_external_connectors"]
    seconds_per_timestep = _seconds_per_evaluation_timestep(timing.exec_simulation_s)
    capacity_note = ""
    if link_summary["capacity_exceeded_link_count"] > 0:
        capacity_note = (
            f"WARNING: {link_summary['capacity_exceeded_link_count']} link(s) "
            "exceeded theoretical vehicle capacity at evaluation end."
        )
    lines = [
        "FCFS 6x6 grid 3000-vehicle all-links-200m 60km/h departure-1200 pretrial",
        "Not a TVT-MP benchmark comparison.",
        f"scenario: {SCENARIO_NAME}",
        f"purpose: {PRETRIAL_PURPOSE}",
        ROAD_CONDITION_NOTE,
        ROAD_CONDITION_COMPARISON_NOTE,
        FULL_TRIP_COMPLETION_NOTE,
        DEPARTURE_END_OBSERVATION_NOTE,
        DEMAND_INTENSITY_CLASSIFICATION_NOTE,
        f"vehicles: {NUM_VEHICLES}",
        f"departure: T={DEPARTURE_START}..{DEPARTURE_END}",
        f"simulation: T=0..{EVALUATION_END_TIMESTEP} (World.T after sim={EXPECTED_WORLD_T_AFTER_SIM})",
        f"FCFS internal nodes: {INTERNAL_GRID_NODE_COUNT}",
        f"FCFS clearance timesteps: {FCFS_CLEARANCE_TIMESTEPS}",
        f"vehicle state counts: {vehicle_summary['vehicle_state_counts']}",
        f"completed: {vehicle_summary['completed_count']}",
        f"not completed: {vehicle_summary['not_completed_count']}",
        (
            f"internal link vehicles: {internal['vehicle_count']} "
            f"(aggregate occupancy {internal['aggregate_occupancy_ratio']:.6f})"
        ),
        (
            f"external->internal connector vehicles: {ext_in['vehicle_count']} "
            f"(aggregate occupancy {ext_in['aggregate_occupancy_ratio']:.6f})"
        ),
        (
            f"internal->external connector vehicles: {ext_out['vehicle_count']} "
            f"(aggregate occupancy {ext_out['aggregate_occupancy_ratio']:.6f})"
        ),
        f"links at or above 90% occupancy (all links): "
        f"{link_summary['aggregates']['all_links']['links_at_or_above_90_percent']}",
        *_fd_summary_lines(link_summary),
        f"exec_simulation seconds: {timing.exec_simulation_s}",
        f"seconds per simulated timestep: {seconds_per_timestep}",
        *_run_summary_timing_lines(timing),
        capacity_note,
        f"output directory: {TRIAL_OUTPUT_DIR}",
        "Production code and existing reference files were not modified.",
    ]
    lines = [line for line in lines if line]
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def print_console_summary(
    vehicle_summary: dict,
    link_summary: dict,
    timing: TimingRecord,
    final_script_total_s: float,
) -> None:
    internal = link_summary["aggregates"]["internal_links"]
    ext_in = link_summary["aggregates"]["external_to_internal_connectors"]
    ext_out = link_summary["aggregates"]["internal_to_external_connectors"]
    seconds_per_timestep = _seconds_per_evaluation_timestep(timing.exec_simulation_s)
    print()
    print(f"Vehicles: {NUM_VEHICLES}")
    print(f"departure T={DEPARTURE_START}..{DEPARTURE_END}; simulation T=0..{EVALUATION_END_TIMESTEP}")
    print(f"FCFS nodes: {INTERNAL_GRID_NODE_COUNT}; clearance: {FCFS_CLEARANCE_TIMESTEPS}")
    print("vehicle state counts:", vehicle_summary["vehicle_state_counts"])
    print(
        "completed / not completed:",
        vehicle_summary["completed_count"],
        "/",
        vehicle_summary["not_completed_count"],
    )
    print(
        f"internal links: {internal['vehicle_count']} vehicles, "
        f"occupancy {internal['aggregate_occupancy_ratio']:.4f}"
    )
    print(
        f"external->internal connectors: {ext_in['vehicle_count']} vehicles, "
        f"occupancy {ext_in['aggregate_occupancy_ratio']:.4f}"
    )
    print(
        f"internal->external connectors: {ext_out['vehicle_count']} vehicles, "
        f"occupancy {ext_out['aggregate_occupancy_ratio']:.4f}"
    )
    print(
        "links >= 90% occupancy (jam-density basis):",
        link_summary["aggregates"]["all_links"]["links_at_or_above_90_percent"],
    )
    for line in _fd_summary_lines(link_summary):
        print(line)
    print("exec_simulation seconds:", timing.exec_simulation_s)
    print("seconds per simulated timestep:", seconds_per_timestep)
    print("final_script_total seconds:", final_script_total_s)
    print("output directory:", TRIAL_OUTPUT_DIR)
    if link_summary["capacity_exceeded_link_count"] > 0:
        print(
            "WARNING: links exceeding theoretical capacity:",
            link_summary["capacity_exceeded_link_count"],
        )
    print("(FCFS pretrial; 200 m links, 60 km/h; full completion not required.)")
    print()


# ---------------------------------------------------------------------------
# 6. Static validation (no World, vehicles, simulation, or file writes)
# ---------------------------------------------------------------------------

def _function_node(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _module_assigned_constants(tree: ast.Module) -> dict:
    values = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value.value
    return values


def _call_names(function_node: ast.AST) -> list[str]:
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


def _assert_static_function_does_not_run(function_node: ast.AST) -> None:
    forbidden = {
        "exec_simulation",
        "mkdir",
        "addVehicle",
        "World",
        "generate_vehicle_plans",
        "build_world_and_network",
        "_run_pretrial",
        "main",
        "open",
    }
    for name in _call_names(function_node):
        if name in forbidden:
            raise RuntimeError(f"Static validation must not call {name}.")


def _assert_fcfs_targets_and_free_routing(tree: ast.Module) -> None:
    build_function = _function_node(tree, "build_world_and_network")
    if build_function is None:
        raise RuntimeError("build_world_and_network is missing.")
    saw_infer = False
    saw_set_fcfs = False
    for node in ast.walk(build_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "infer_order_control_eligible_nodes":
            saw_infer = True
        if node.func.attr == "set_order_control_for_nodes":
            saw_set_fcfs = True
            if len(node.args) < 1 or not isinstance(node.args[0], ast.Name):
                raise RuntimeError("set_order_control_for_nodes must take INTERNAL_GRID_NODES.")
            if node.args[0].id != "INTERNAL_GRID_NODES":
                raise RuntimeError("FCFS must target INTERNAL_GRID_NODES only.")
            fcfs_kw = False
            for keyword in node.keywords:
                if keyword.arg == "order_control_type":
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value == "fcfs":
                        fcfs_kw = True
            if fcfs_kw is not True:
                raise RuntimeError("Internal nodes must use order_control_type='fcfs'.")
    if saw_infer is not True:
        raise RuntimeError("build_world_and_network must infer order-control eligibility.")
    if saw_set_fcfs is not True:
        raise RuntimeError("build_world_and_network must set FCFS on internal nodes.")

    add_function = _function_node(tree, "add_vehicles_to_world")
    if add_function is None:
        raise RuntimeError("add_vehicles_to_world is missing.")
    saw_add_vehicle = False
    for node in ast.walk(add_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "addVehicle":
            continue
        saw_add_vehicle = True
        for keyword in node.keywords:
            if keyword.arg in ("specified_route", "route"):
                raise RuntimeError("specified_route must not be passed to addVehicle.")
    if saw_add_vehicle is not True:
        raise RuntimeError("add_vehicles_to_world must call addVehicle.")


def _assert_does_not_import_forbidden_modules(tree: ast.Module) -> None:
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in FORBIDDEN_RUNTIME_IMPORT_SUBSTRINGS:
                    if forbidden in alias.name:
                        raise RuntimeError(
                            f"This script must not import forbidden module {alias.name!r}."
                        )
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for forbidden in FORBIDDEN_RUNTIME_IMPORT_SUBSTRINGS:
                if forbidden in module:
                    raise RuntimeError(
                        f"This script must not import forbidden module {module!r}."
                    )


def _assert_addlink_no_capacity_in_out_keywords(tree: ast.Module) -> None:
    build_function = _function_node(tree, "build_world_and_network")
    if build_function is None:
        raise RuntimeError("build_world_and_network is missing.")
    for node in ast.walk(build_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "addLink":
            continue
        for keyword in node.keywords:
            if keyword.arg in ("capacity_in", "capacity_out"):
                raise RuntimeError(
                    f"addLink must not pass {keyword.arg!r}; use UXsim defaults."
                )


def _assert_main_static_branch(tree: ast.Module) -> None:
    main_function = _function_node(tree, "main")
    if main_function is None:
        raise RuntimeError("main is missing.")
    static_calls = _call_names(main_function)
    if "exec_simulation" in static_calls or "mkdir" in static_calls:
        raise RuntimeError("main must not simulate or create directories itself.")
    if "_run_pretrial" not in static_calls:
        raise RuntimeError("main must call _run_pretrial on the normal path.")
    if "validate_static_contract" not in static_calls:
        raise RuntimeError("main must call validate_static_contract for --static-validate-only.")


def validate_static_contract() -> None:
    if NUM_VEHICLES != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if GRID_SIZE != 6:
        raise RuntimeError("GRID_SIZE must be 6.")
    if TMAX != 1201:
        raise RuntimeError("TMAX must be 1201.")
    if EXPECTED_WORLD_T_AFTER_SIM != 1201:
        raise RuntimeError("EXPECTED_WORLD_T_AFTER_SIM must be 1201.")
    if EVALUATION_END_TIMESTEP != 1200:
        raise RuntimeError("EVALUATION_END_TIMESTEP must be 1200.")
    if SIMULATED_EVALUATION_TIMESTEPS != 1201:
        raise RuntimeError("SIMULATED_EVALUATION_TIMESTEPS must be 1201.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 1200:
        raise RuntimeError("Departure window must be 0..1200.")
    if RANDOM_SEED != 0:
        raise RuntimeError("Random seed must be 0.")
    if DEMAND_GEN_SEED != 42:
        raise RuntimeError("Demand seed must be 42.")
    if FCFS_CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Clearance must be 1.")
    if INTERNAL_LINK_LENGTH != 200:
        raise RuntimeError("Internal link length must be 200.")
    if OD_CONNECTOR_LENGTH != 200:
        raise RuntimeError("OD connector length must be 200.")
    if JAM_DENSITY != 0.2:
        raise RuntimeError("Jam density must be 0.2.")
    if TOTAL_THEORETICAL_VEHICLE_CAPACITY != 6720:
        raise RuntimeError("Theoretical total capacity must be 6720.")
    if INTERNAL_LINK_THEORETICAL_CAPACITY != 40:
        raise RuntimeError("Each link jam-density theoretical capacity must be 40.")
    if INTERNAL_LINKS_TOTAL_THEORETICAL_CAPACITY != 4800:
        raise RuntimeError("Internal links total theoretical capacity must be 4800.")
    if EXTERNAL_TO_INTERNAL_CONNECTOR_TOTAL_THEORETICAL_CAPACITY != 960:
        raise RuntimeError("External-to-internal connector total capacity must be 960.")
    if FREE_FLOW_SPEED_KMH != 60:
        raise RuntimeError("FREE_FLOW_SPEED_KMH must be 60.")
    if abs(FREE_FLOW_SPEED - FREE_FLOW_SPEED_KMH / 3.6) > 1e-12:
        raise RuntimeError("FREE_FLOW_SPEED must equal FREE_FLOW_SPEED_KMH / 3.6.")
    if SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("specified_route must not be used.")
    if len(INTERNAL_GRID_NODES) != 36:
        raise RuntimeError("Internal grid node list length is not 36.")
    if len(EXTERNAL_OD_NODES) != 24:
        raise RuntimeError("External OD node list length is not 24.")
    if set(INTERNAL_GRID_NODES) & set(EXTERNAL_OD_NODES):
        raise RuntimeError("Internal grid nodes and external OD nodes overlap.")
    for node_name in EXTERNAL_OD_NODES:
        if node_name in INTERNAL_GRID_NODE_SET:
            raise RuntimeError(f"External OD node {node_name} is in internal set.")
    if TRIAL_OUTPUT_DIR_NAME != SCENARIO_NAME:
        raise RuntimeError("Output directory name must match scenario name.")
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Static validation refuses non-unique output path."
        )

    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    assigned = _module_assigned_constants(tree)
    expected_numbers = {
        "NUM_VEHICLES": 3000,
        "GRID_SIZE": 6,
        "TMAX": 1201,
        "EXPECTED_WORLD_T_AFTER_SIM": 1201,
        "EVALUATION_END_TIMESTEP": 1200,
        "SIMULATED_EVALUATION_TIMESTEPS": 1201,
        "DEPARTURE_START": 0,
        "DEPARTURE_END": 1200,
        "RANDOM_SEED": 0,
        "DEMAND_GEN_SEED": 42,
        "FCFS_CLEARANCE_TIMESTEPS": 1,
        "INTERNAL_LINK_LENGTH": 200,
        "OD_CONNECTOR_LENGTH": 200,
        "FREE_FLOW_SPEED_KMH": 60,
        "JAM_DENSITY": 0.2,
        "REACTION_TIME": 1,
    }
    for name, expected in expected_numbers.items():
        if assigned.get(name) != expected:
            raise RuntimeError(f"Module constant {name} must be {expected}.")
    if assigned.get("SPECIFIED_ROUTE_USED") is not False:
        raise RuntimeError("SPECIFIED_ROUTE_USED must be False.")

    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    _assert_static_function_does_not_run(validator)
    _assert_does_not_import_forbidden_modules(tree)
    _assert_fcfs_targets_and_free_routing(tree)
    _assert_addlink_no_capacity_in_out_keywords(tree)
    _assert_main_static_branch(tree)


# ---------------------------------------------------------------------------
# 7. Main trial runner
# ---------------------------------------------------------------------------

def _refuse_existing_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Rename or remove it manually before re-running."
        )


def _run_pretrial() -> int:
    script_start = time.perf_counter()
    timing = TimingRecord()

    _refuse_existing_output_directory()

    started = time.perf_counter()
    plans = generate_vehicle_plans()
    plan_audit = verify_vehicle_plans(plans)
    timing.vehicle_plan_generation_s = time.perf_counter() - started

    started = time.perf_counter()
    world = build_world_and_network()
    timing.world_build_s = time.perf_counter() - started

    started = time.perf_counter()
    add_vehicles_to_world(world, plans)
    timing.vehicle_add_s = time.perf_counter() - started
    verify_network_runtime(world)

    started = time.perf_counter()
    world.finalize_scenario()
    timing.finalize_s = time.perf_counter() - started
    if world.TSIZE != TMAX:
        raise RuntimeError(f"World.TSIZE is {world.TSIZE!r}, expected {TMAX}.")

    started = time.perf_counter()
    world.exec_simulation()
    timing.exec_simulation_s = time.perf_counter() - started

    verify_world_time_after_simulation(world)

    started = time.perf_counter()
    vehicle_summary = collect_evaluation_end_vehicle_summary(world, plans)
    link_summary = collect_link_occupancy_at_evaluation_end(world)
    traffic_summary = collect_traffic_analyzer_summary(world)
    timing.result_collection_s = time.perf_counter() - started

    _refuse_existing_output_directory()
    TRIAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    pre_manifest_output_started = time.perf_counter()
    write_link_occupancy_csv(
        TRIAL_OUTPUT_DIR / LINK_OCCUPANCY_CSV_NAME,
        link_summary,
    )
    write_vehicle_state_summary_csv(
        TRIAL_OUTPUT_DIR / "vehicle_state_summary.csv",
        vehicle_summary,
    )
    write_vehicle_plan_audit_json(
        TRIAL_OUTPUT_DIR / "vehicle_plan_audit.json",
        plan_audit,
    )
    timing.pre_manifest_output_write_s = (
        time.perf_counter() - pre_manifest_output_started
    )
    timing.pre_manifest_script_total_s = time.perf_counter() - script_start

    manifest_started = time.perf_counter()
    write_manifest_json(
        TRIAL_OUTPUT_DIR / "manifest.json",
        timing,
        plan_audit,
        vehicle_summary,
        link_summary,
        traffic_summary,
    )
    timing.manifest_write_s = time.perf_counter() - manifest_started

    summary_path = TRIAL_OUTPUT_DIR / "run_summary.txt"
    summary_started = time.perf_counter()
    write_run_summary_txt(
        summary_path,
        vehicle_summary,
        link_summary,
        timing,
    )
    timing.run_summary_write_s = time.perf_counter() - summary_started
    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write(f"run_summary_write seconds: {timing.run_summary_write_s}\n")

    final_script_total_s = time.perf_counter() - script_start

    print_console_summary(
        vehicle_summary,
        link_summary,
        timing,
        final_script_total_s,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) == 1 and arguments[0] == "--static-validate-only":
        validate_static_contract()
        print("Static validation passed.")
        return 0
    if arguments:
        raise RuntimeError(f"Unknown arguments: {arguments!r}.")
    return _run_pretrial()


if __name__ == "__main__":
    raise SystemExit(main())
