"""
Early scaling TVT-MP benchmark: 6x6 internal grid, 24 external OD nodes, 5000 vehicles.

This is not a formal method-performance trial or a completion benchmark. It checks
that a 5000-vehicle World can finalize, run TVT-MP through evaluation T=0..599
(including departure T=0..500 and post-demand observation), produce research
output, and report runtime versus the 1000-vehicle short benchmark reference.

Network and vehicle-plan structure follow
tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py.
That module and the 1000-vehicle benchmark script are not imported at runtime.
Production code is not modified.

Run from the repository root:

    python research_scripts/run_tvt_mp_6x6_grid_high_demand_5000_vehicle_early_scaling_benchmark.py --static-validate-only
    python research_scripts/run_tvt_mp_6x6_grid_high_demand_5000_vehicle_early_scaling_benchmark.py
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
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from uxsim import World
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

# ---------------------------------------------------------------------------
# 1. Benchmark constants
# ---------------------------------------------------------------------------

SCENARIO_NAME = (
    "tvt_mp_6x6_grid_5000_vehicle_eval_600_timestep_early_scaling_benchmark_"
    "candidate_limit_10_seed_0_vot_seed_1"
)
TRIAL_OUTPUT_DIR_NAME = SCENARIO_NAME

BENCHMARK_PURPOSE = (
    "Early scaling benchmark before a future 5000-vehicle formal 6x6 TVT-MP trial. "
    "Confirms 5000-vehicle World build, dill World copy at recursion limit 50000, "
    "TVT-MP on 36 internal nodes through T=599 (departure T=0..500 plus "
    "post-demand observation), research output, and runtime versus the "
    "1000-vehicle short benchmark reference. Not a formal performance comparison."
)

NUM_VEHICLES = 5000
VEHICLE_STATE_NAME_SAMPLE_LIMIT = 50

REFERENCE_1000_VEHICLE_BENCHMARK = {
    "vehicle_count": 1000,
    "evaluation_timesteps": 1000,
    "exec_simulation_seconds": 7620.127332167001,
    "seconds_per_evaluation_timestep": 7.6201273321670016,
    "completed_count": 1000,
    "transaction_count": 1078,
}

INTERVAL_TIMING_AVAILABLE = False
INTERVAL_TIMING_UNAVAILABLE_REASON = "safe segmented execution was not assumed"

GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = 36
EXTERNAL_OD_NODE_COUNT = 24
TOTAL_NODE_COUNT = 60
INTERNAL_DIRECTED_LINK_COUNT = 120
OD_CONNECTOR_DIRECTED_LINK_COUNT = 48
TOTAL_LINK_COUNT = 168

DEPARTURE_START = 0
DEPARTURE_END = 500
MIN_OD_MANHATTAN_DISTANCE = 5

EVALUATION_START_TIMESTEP = 0
EVALUATION_END_TIMESTEP = 599
BASELINE_HORIZON_STEPS = 30
INTERNAL_TSIZE = 630
EXPECTED_WORLD_T_AFTER_SIM = 600
SIMULATED_EVALUATION_TIMESTEPS = 600

LAST_DEPARTURE_TIMESTEP = DEPARTURE_END
POST_DEMAND_OBSERVATION_DEFINITION = (
    "Integer timesteps strictly after the last departure timestep (500): "
    "timesteps 501 through 599 inclusive, count = 99."
)
POST_DEMAND_OBSERVATION_TIMESTEP_COUNT = EVALUATION_END_TIMESTEP - LAST_DEPARTURE_TIMESTEP

SCHEDULED_DEPARTURE_REACHED_COUNT_DEFINITION = (
    "Count of vehicles whose planned departure_time (vehicle plan) is less than or "
    f"equal to evaluation_end_timestep ({EVALUATION_END_TIMESTEP}). "
    "Classification uses departure_time <= EVALUATION_END_TIMESTEP only; it does "
    "not directly mean the vehicle entered the network."
)
SCHEDULED_DEPARTURE_COUNT_ACTUAL_STATE_NOTE = (
    "For actual evaluation-end state, use vehicle_state_counts, "
    "vehicles_on_network_count, completed_count, and "
    "link_vehicle_counts_at_evaluation_end."
)

MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1

TRAFFIC_SEED = 0
DEMAND_GEN_SEED = 42
VOT_SEED = 1

VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20

WORLD_COPY_RECURSION_LIMIT = 50000
SPECIFIED_ROUTE_USED = False
ROUTE_ASSIGNMENT_MODE = "uxsim_free_route_choice"
ALL_VEHICLES_PARTICIPATE = True

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME
SCRIPT_PATH = Path(__file__).resolve()


@dataclass
class TimingRecord:
    world_build_s: float = 0.0
    finalize_s: float = 0.0
    exec_simulation_s: float = 0.0
    research_build_s: float = 0.0
    research_csv_write_s: float = 0.0
    vehicle_vot_csv_write_s: float = 0.0
    pre_manifest_script_total_s: float = 0.0
    manifest_write_s: float = 0.0
    run_summary_write_s: float = 0.0


@dataclass
class VehicleVotRecord:
    vehicle_name: str
    origin: str
    destination: str
    departure_time: float
    participates_in_order_exchange: bool
    true_vot_per_second: float
    declared_vot_per_second: float


# ---------------------------------------------------------------------------
# 2. Network names and link specs (same structure as the 6x6 high-demand test)
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
    """Return (internal_links, od_connector_links).

    Each item is (link_name, start_node, end_node, length, signal_group).
    Names match the 6x6 high-demand test, including bidirectional pairs.
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


def _manhattan_distance(origin_coord, destination_coord) -> int:
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


# ---------------------------------------------------------------------------
# 3. Vehicle plans (random.Random(DEMAND_GEN_SEED); not built at import)
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
    }


def _vehicle_plan_digest(plans: list[dict]) -> str:
    hasher = hashlib.sha256()
    for plan in plans:
        line = (
            f"{plan['name']}|{plan['origin']}|{plan['destination']}|"
            f"{plan['departure_time']!r}\n"
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def generate_vehicle_vots(count: int) -> list[float]:
    rng = np.random.default_rng(VOT_SEED)
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    values = []
    for value in samples:
        number = float(value)
        if math.isfinite(number) is not True or number <= 0.0:
            raise RuntimeError(f"VOT sample is not a positive finite float: {number!r}.")
        values.append(number)
    return values


def build_vehicle_vot_records(plans: list[dict], vot_values: list[float]) -> list[VehicleVotRecord]:
    if len(plans) != len(vot_values):
        raise RuntimeError("Vehicle plan count and VOT count differ.")
    records = []
    for plan, vot in zip(plans, vot_values):
        records.append(
            VehicleVotRecord(
                vehicle_name=plan["name"],
                origin=plan["origin"],
                destination=plan["destination"],
                departure_time=plan["departure_time"],
                participates_in_order_exchange=True,
                true_vot_per_second=vot,
                declared_vot_per_second=vot,
            )
        )
    return records


# ---------------------------------------------------------------------------
# 4. World, simulation, and runtime checks
# ---------------------------------------------------------------------------

def build_world_and_network() -> World:
    world = World(
        name=SCENARIO_NAME,
        deltan=1,
        reaction_time=1,
        tmax=INTERNAL_TSIZE,
        random_seed=TRAFFIC_SEED,
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
            number_of_lanes=NUMBER_OF_LANES,
            merge_priority=MERGE_PRIORITY,
            signal_group=signal_group,
        )

    eligible_nodes = world.infer_order_control_eligible_nodes()
    eligible_names = {node.name for node in eligible_nodes}
    for node_name in INTERNAL_GRID_NODES:
        if node_name not in eligible_names:
            raise RuntimeError(f"{node_name} is not order-control eligible.")
        node = world.get_node(node_name)
        if node.order_control_eligible is not True:
            raise RuntimeError(f"{node_name} order_control_eligible is not True.")

    world.set_order_control_for_nodes(
        INTERNAL_GRID_NODES,
        order_control_type="time_value",
        transaction_case=None,
    )
    world.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    world.order_control_tvt_evaluation_end_timestep = EVALUATION_END_TIMESTEP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    return world


def verify_network_runtime(world: World) -> None:
    if GRID_SIZE != 6:
        raise RuntimeError("GRID_SIZE is not 6.")
    if len(world.NODES) != TOTAL_NODE_COUNT:
        raise RuntimeError(f"Node count is {len(world.NODES)}, expected {TOTAL_NODE_COUNT}.")
    if len(INTERNAL_GRID_NODES) != INTERNAL_GRID_NODE_COUNT:
        raise RuntimeError("Internal node name count is not 36.")
    if len(EXTERNAL_OD_NODES) != EXTERNAL_OD_NODE_COUNT:
        raise RuntimeError("External OD node name count is not 24.")
    if len(INTERNAL_LINK_SPECS) != INTERNAL_DIRECTED_LINK_COUNT:
        raise RuntimeError("Internal directed link count is not 120.")
    if len(OD_CONNECTOR_LINK_SPECS) != OD_CONNECTOR_DIRECTED_LINK_COUNT:
        raise RuntimeError("OD connector directed link count is not 48.")
    if len(world.LINKS) != TOTAL_LINK_COUNT:
        raise RuntimeError(f"Link count is {len(world.LINKS)}, expected {TOTAL_LINK_COUNT}.")

    tvt_nodes = []
    for node in world.NODES:
        if node.order_control_type == "time_value":
            tvt_nodes.append(node.name)
    if sorted(tvt_nodes) != sorted(INTERNAL_GRID_NODES):
        raise RuntimeError("TVT-MP nodes are not exactly the 36 internal grid nodes.")
    for node_name in EXTERNAL_OD_NODES:
        node = world.get_node(node_name)
        if node.order_control_type == "time_value":
            raise RuntimeError(f"External OD node {node_name} is a TVT-MP target.")
        if node.order_control_eligible is not False:
            raise RuntimeError(f"External OD node {node_name} is order-control eligible.")

    for link_name, start_node, end_node, length, _signal_group in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        if link.start_node.name != start_node or link.end_node.name != end_node:
            raise RuntimeError(f"Link {link_name} endpoints do not match the 6x6 spec.")
        if link.length != length:
            raise RuntimeError(f"Link {link_name} length is {link.length!r}.")
        if link.number_of_lanes != NUMBER_OF_LANES:
            raise RuntimeError(f"Link {link_name} lane count is not 1.")
        if link.merge_priority != MERGE_PRIORITY:
            raise RuntimeError(f"Link {link_name} merge priority is not 1.")
        if link.free_flow_speed != FREE_FLOW_SPEED or link.u != FREE_FLOW_SPEED:
            raise RuntimeError(f"Link {link_name} free-flow speed is not 20.")

    for node_name in INTERNAL_GRID_NODES:
        node = world.get_node(node_name)
        if node.order_control_clearance_timesteps != CLEARANCE_TIMESTEPS:
            raise RuntimeError(f"{node_name} clearance is not 1.")
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("Candidate visit limit is not the explicit N=10.")
    if world.order_control_tvt_baseline_horizon_steps != BASELINE_HORIZON_STEPS:
        raise RuntimeError("Baseline horizon is not 30.")
    if world.order_control_tvt_evaluation_end_timestep != EVALUATION_END_TIMESTEP:
        raise RuntimeError("Evaluation end timestep is not 599.")


def add_vehicles_to_world(world: World, vot_records: list[VehicleVotRecord]) -> None:
    for record in vot_records:
        if record.participates_in_order_exchange is not True:
            raise RuntimeError(f"{record.vehicle_name} is not participating.")
        if record.declared_vot_per_second != record.true_vot_per_second:
            raise RuntimeError(f"{record.vehicle_name} declared VOT differs from true VOT.")
        world.addVehicle(
            record.origin,
            record.destination,
            record.departure_time,
            name=record.vehicle_name,
            vot_true=record.true_vot_per_second,
            vot_declared=record.declared_vot_per_second,
            participates_in_order_exchange=True,
        )


def verify_evaluation_end(world: World) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    for field_name in (
        "evaluation_end_unobserved_finalized_timestep",
        "trade_ex_post_evaluation_finalized_timestep",
        "individual_ex_post_evaluation_finalized_timestep",
    ):
        actual = getattr(registry, field_name)
        if actual != EVALUATION_END_TIMESTEP:
            raise RuntimeError(
                f"Registry {field_name} expected {EVALUATION_END_TIMESTEP}, got {actual!r}."
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

    internal_names = {spec[0] for spec in INTERNAL_LINK_SPECS}
    connector_names = {spec[0] for spec in OD_CONNECTOR_LINK_SPECS}
    link_vehicle_counts = {}
    internal_remaining = 0
    connector_remaining = 0
    for link in world.LINKS:
        count = len(link.vehicles)
        link_vehicle_counts[link.name] = count
        if link.name in internal_names:
            internal_remaining += count
        elif link.name in connector_names:
            connector_remaining += count
        else:
            raise RuntimeError(f"Unexpected link at evaluation end: {link.name}.")

    state_name_samples = {
        state_value: _sample_vehicle_names(names)
        for state_value, names in sorted(state_names.items())
    }

    return {
        "vehicle_total_count": NUM_VEHICLES,
        "vehicle_state_counts": dict(sorted(state_counts.items())),
        "vehicle_state_name_samples": state_name_samples,
        "completed_count": len(completed_names),
        "not_completed_count": len(not_completed_names),
        "scheduled_departure_reached_count": len(scheduled_departure_reached_names),
        "scheduled_departure_not_reached_count": len(
            scheduled_departure_not_reached_names
        ),
        "vehicles_on_network_count": len(on_network_names),
        "internal_grid_link_vehicle_count_at_evaluation_end": internal_remaining,
        "od_connector_vehicle_count_at_evaluation_end": connector_remaining,
        "link_vehicle_counts_at_evaluation_end": dict(sorted(link_vehicle_counts.items())),
    }


def _runtime_scaling_metrics(timing: TimingRecord) -> dict:
    reference = REFERENCE_1000_VEHICLE_BENCHMARK
    current_spt = _seconds_per_evaluation_timestep(timing.exec_simulation_s)
    reference_spt = reference["seconds_per_evaluation_timestep"]
    return {
        "reference_1000_vehicle_benchmark": reference,
        "current_seconds_per_evaluation_timestep": current_spt,
        "reference_seconds_per_evaluation_timestep": reference_spt,
        "per_timestep_runtime_ratio": current_spt / reference_spt,
        "vehicle_count_ratio": NUM_VEHICLES / reference["vehicle_count"],
        "evaluation_timestep_ratio": (
            SIMULATED_EVALUATION_TIMESTEPS / reference["evaluation_timesteps"]
        ),
        "runtime_ratio_interpretation_note": (
            "Evaluation range and traffic state differ between benchmarks. "
            "per_timestep_runtime_ratio is an approximate comparison, not a strict "
            "vehicle-count scaling law. Do not extrapolate total runtime for a "
            "future 5000-vehicle formal trial by simple proportion."
        ),
    }


def collect_node_rank_ledger_summary(world: World) -> dict:
    ledgers = world.order_control_tvt_rank_states_by_node_name
    summary = {}
    for node_name in INTERNAL_GRID_NODES:
        state = ledgers[node_name]
        exported = state.export_state()
        summary[node_name] = {
            "k_confirmed": exported["k_confirmed"],
            "confirmed_visit_count": len(exported["confirmed_visits"]),
            "undetermined_visit_count": len(exported["undetermined_visits"]),
        }
    return summary


def collect_visit_id_summary(world: World) -> dict:
    visit_id_counts = {}
    max_visit_id = 0
    ledgers = world.order_control_tvt_rank_states_by_node_name
    for node_name in INTERNAL_GRID_NODES:
        exported = ledgers[node_name].export_state()
        for bucket_name in ("confirmed_visits", "undetermined_visits"):
            for row in exported[bucket_name]:
                visit_id = int(row["visit_id"])
                visit_id_counts[visit_id] = visit_id_counts.get(visit_id, 0) + 1
                if visit_id > max_visit_id:
                    max_visit_id = visit_id
    return {
        "visit_id_counts": dict(sorted(visit_id_counts.items())),
        "maximum_visit_id": max_visit_id,
    }


def collect_transaction_counts_by_node(bundle) -> dict[str, int]:
    counts = {name: 0 for name in INTERNAL_GRID_NODES}
    for transaction in bundle.transactions:
        node_name = transaction.node_name
        if node_name not in counts:
            raise RuntimeError(f"Transaction node {node_name!r} is not an internal TVT-MP node.")
        counts[node_name] += 1
    return counts


# ---------------------------------------------------------------------------
# 5. Output writers
# ---------------------------------------------------------------------------

def verify_transaction_totals(transaction_count: int, transactions_by_node: dict[str, int]) -> None:
    node_total = sum(transactions_by_node.values())
    if node_total != transaction_count:
        raise RuntimeError(
            f"Transaction count {transaction_count} does not match "
            f"node sum {node_total}."
        )


def _file_sizes(paths: list[Path]) -> dict[str, int]:
    sizes = {}
    for path in paths:
        sizes[path.name] = path.stat().st_size
    return sizes


def write_vehicle_vot_csv(path: Path, vot_records: list[VehicleVotRecord]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    fieldnames = [
        "vehicle_name",
        "origin",
        "destination",
        "departure_timestep",
        "participates_in_order_exchange",
        "true_vot_per_second",
        "declared_vot_per_second",
        "traffic_seed",
        "vot_seed",
        "demand_gen_seed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in vot_records:
            writer.writerow(
                {
                    "vehicle_name": record.vehicle_name,
                    "origin": record.origin,
                    "destination": record.destination,
                    "departure_timestep": record.departure_time,
                    "participates_in_order_exchange": record.participates_in_order_exchange,
                    "true_vot_per_second": record.true_vot_per_second,
                    "declared_vot_per_second": record.declared_vot_per_second,
                    "traffic_seed": TRAFFIC_SEED,
                    "vot_seed": VOT_SEED,
                    "demand_gen_seed": DEMAND_GEN_SEED,
                }
            )


def _seconds_per_evaluation_timestep(exec_simulation_s: float) -> float:
    return exec_simulation_s / SIMULATED_EVALUATION_TIMESTEPS


def _manifest_timing_payload(timing: TimingRecord) -> dict:
    return {
        "world_build_seconds": timing.world_build_s,
        "finalize_seconds": timing.finalize_s,
        "exec_simulation_seconds": timing.exec_simulation_s,
        "research_output_build_seconds": timing.research_build_s,
        "research_csv_write_seconds": timing.research_csv_write_s,
        "vehicle_vot_csv_write_seconds": timing.vehicle_vot_csv_write_s,
        "pre_manifest_script_total_seconds": timing.pre_manifest_script_total_s,
        "simulated_evaluation_timesteps": SIMULATED_EVALUATION_TIMESTEPS,
        "seconds_per_evaluation_timestep": _seconds_per_evaluation_timestep(
            timing.exec_simulation_s
        ),
        "timing_scope_note": (
            "pre_manifest_script_total_seconds ends after vehicle_vot.csv is written. "
            "manifest.json write time and run_summary.txt write time are not included."
        ),
    }


def write_manifest_json(
    path: Path,
    timing: TimingRecord,
    plan_audit: dict,
    vehicle_summary: dict,
    ledger_summary: dict,
    visit_id_summary: dict,
    transactions_by_node: dict[str, int],
    transaction_count: int,
    runtime_scaling: dict,
    file_sizes: dict[str, int],
    original_recursion_limit: int,
    effective_recursion_limit: int,
) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    timing_payload = _manifest_timing_payload(timing)
    output_bytes_before_manifest = sum(file_sizes.values())
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "benchmark_purpose": BENCHMARK_PURPOSE,
        "formal_performance_comparison": False,
        "early_scaling_benchmark": True,
        "not_formal_5000_vehicle_trial": True,
        "not_10000_vehicle_trial": True,
        "full_trip_completion_not_required": True,
        "production_unchanged": True,
        "demand_injection_completed_before_evaluation_end": True,
        "departure_window_timesteps": f"T={DEPARTURE_START}..{DEPARTURE_END}",
        "post_demand_observation_definition": POST_DEMAND_OBSERVATION_DEFINITION,
        "post_demand_observation_timestep_count": POST_DEMAND_OBSERVATION_TIMESTEP_COUNT,
        "simulated_evaluation_timestep_count": SIMULATED_EVALUATION_TIMESTEPS,
        "interval_timing_available": INTERVAL_TIMING_AVAILABLE,
        "interval_timing_unavailable_reason": INTERVAL_TIMING_UNAVAILABLE_REASON,
        "runtime_scaling_vs_1000_vehicle_benchmark": runtime_scaling,
        "vehicle_count": NUM_VEHICLES,
        "participating_count": NUM_VEHICLES,
        "nonparticipating_count": 0,
        "traffic_seed": TRAFFIC_SEED,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "vot_seed": VOT_SEED,
        "grid_size": GRID_SIZE,
        "internal_node_count": INTERNAL_GRID_NODE_COUNT,
        "external_od_node_count": EXTERNAL_OD_NODE_COUNT,
        "total_node_count": TOTAL_NODE_COUNT,
        "internal_tvt_mp_node_count": INTERNAL_GRID_NODE_COUNT,
        "internal_tvt_mp_node_names": list(INTERNAL_GRID_NODES),
        "external_od_node_names": list(EXTERNAL_OD_NODES),
        "link_count": TOTAL_LINK_COUNT,
        "internal_directed_link_count": INTERNAL_DIRECTED_LINK_COUNT,
        "od_connector_directed_link_count": OD_CONNECTOR_DIRECTED_LINK_COUNT,
        "departure_start": DEPARTURE_START,
        "departure_end": DEPARTURE_END,
        "departure_time_definition": (
            "Continuous departure time in seconds, evenly spaced from 0 to 500 "
            "by the 6x6 high-demand formula. Stored in vehicle_vot.csv as "
            "departure_timestep. Not rounded to an integer timestep."
        ),
        "evaluation_start_timestep": EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "internal_tsize": INTERNAL_TSIZE,
        "expected_world_t_after_simulation": EXPECTED_WORLD_T_AFTER_SIM,
        "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "clearance_timesteps": CLEARANCE_TIMESTEPS,
        "free_route_choice": True,
        "specified_route": False,
        "vot_distribution": "lognormal",
        "vot_log_mu": VOT_LOG_MU,
        "vot_log_sigma": VOT_LOG_SIGMA,
        "true_vot_equals_declared_vot": True,
        "vehicle_plan_audit": plan_audit,
        "vehicle_state_summary": {
            "vehicle_total_count": vehicle_summary["vehicle_total_count"],
            "vehicle_state_counts": vehicle_summary["vehicle_state_counts"],
            "vehicle_state_name_samples": vehicle_summary["vehicle_state_name_samples"],
            "completed_count": vehicle_summary["completed_count"],
            "not_completed_count": vehicle_summary["not_completed_count"],
            "scheduled_departure_reached_count": vehicle_summary[
                "scheduled_departure_reached_count"
            ],
            "scheduled_departure_not_reached_count": vehicle_summary[
                "scheduled_departure_not_reached_count"
            ],
            "scheduled_departure_reached_count_definition": (
                SCHEDULED_DEPARTURE_REACHED_COUNT_DEFINITION
            ),
            "scheduled_departure_count_actual_state_note": (
                SCHEDULED_DEPARTURE_COUNT_ACTUAL_STATE_NOTE
            ),
            "vehicles_on_network_count": vehicle_summary["vehicles_on_network_count"],
        },
        "completed_count": vehicle_summary["completed_count"],
        "not_completed_count": vehicle_summary["not_completed_count"],
        "scheduled_departure_reached_count": vehicle_summary[
            "scheduled_departure_reached_count"
        ],
        "scheduled_departure_not_reached_count": vehicle_summary[
            "scheduled_departure_not_reached_count"
        ],
        "scheduled_departure_reached_count_definition": (
            SCHEDULED_DEPARTURE_REACHED_COUNT_DEFINITION
        ),
        "scheduled_departure_count_actual_state_note": (
            SCHEDULED_DEPARTURE_COUNT_ACTUAL_STATE_NOTE
        ),
        "vehicles_on_network_count": vehicle_summary["vehicles_on_network_count"],
        "link_vehicle_counts_at_evaluation_end": vehicle_summary[
            "link_vehicle_counts_at_evaluation_end"
        ],
        "internal_grid_link_vehicle_count_at_evaluation_end": vehicle_summary[
            "internal_grid_link_vehicle_count_at_evaluation_end"
        ],
        "od_connector_vehicle_count_at_evaluation_end": vehicle_summary[
            "od_connector_vehicle_count_at_evaluation_end"
        ],
        "transactions_count": transaction_count,
        "transaction_count_minimum_not_enforced": True,
        "transactions_by_node": transactions_by_node,
        "transactions_per_simulated_evaluation_timestep": (
            transaction_count / SIMULATED_EVALUATION_TIMESTEPS
        ),
        "transactions_per_tvt_node": transaction_count / INTERNAL_GRID_NODE_COUNT,
        "node_rank_ledger_summary": ledger_summary,
        "visit_id_summary": visit_id_summary,
        "timing": timing_payload,
        "tvt_node_count": INTERNAL_GRID_NODE_COUNT,
        "output_file_sizes_before_manifest": file_sizes,
        "output_bytes_before_manifest": output_bytes_before_manifest,
        "output_size_scope_note": (
            "output_file_sizes_before_manifest lists the five formal research CSV files "
            "and vehicle_vot.csv only. output_bytes_before_manifest is their sum. "
            "manifest.json and run_summary.txt are excluded."
        ),
        "spillback_timestep_rows_saved": False,
        "spillback_note": (
            "Per-link per-timestep spillback rows are not saved. "
            "Evaluation-end vehicle counts by link are in this manifest."
        ),
        "original_python_recursion_limit": original_recursion_limit,
        "effective_python_recursion_limit": effective_recursion_limit,
        "world_copy_recursion_limit": WORLD_COPY_RECURSION_LIMIT,
        "partial_output_directory_note": (
            "The output directory is created only after simulation, research-output "
            "construction, and runtime checks. A failure while writing can leave a "
            "partial directory. Rename or remove it before re-running."
        ),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(
    path: Path,
    timing: TimingRecord,
    plan_audit: dict,
    vehicle_summary: dict,
    transaction_count: int,
    transactions_by_node: dict[str, int],
    runtime_scaling: dict,
    directory_bytes_after_manifest: int,
) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    seconds_per_timestep = _seconds_per_evaluation_timestep(timing.exec_simulation_s)
    lines = [
        "TVT-MP 6x6 grid 5000-vehicle early scaling benchmark",
        "This is not a formal performance comparison.",
        f"scenario: {SCENARIO_NAME}",
        f"purpose: {BENCHMARK_PURPOSE}",
        f"internal grid nodes: {INTERNAL_GRID_NODE_COUNT} (g_0_0..g_5_5)",
        f"external OD nodes: {EXTERNAL_OD_NODE_COUNT}",
        f"TVT-MP nodes: {INTERNAL_GRID_NODE_COUNT}",
        f"vehicles: {NUM_VEHICLES}",
        f"departure: T={DEPARTURE_START}..{DEPARTURE_END}",
        f"evaluation: T={EVALUATION_START_TIMESTEP}..{EVALUATION_END_TIMESTEP}",
        f"post-demand observation: {POST_DEMAND_OBSERVATION_DEFINITION}",
        f"TSIZE: {INTERNAL_TSIZE}",
        f"World.T after simulation: {EXPECTED_WORLD_T_AFTER_SIM}",
        f"candidate visit limit N: {MAX_CANDIDATE_VISIT_COUNT}",
        f"vehicle state counts: {vehicle_summary['vehicle_state_counts']}",
        f"completed: {vehicle_summary['completed_count']}",
        f"not completed: {vehicle_summary['not_completed_count']}",
        f"scheduled_departure_reached_count: "
        f"{vehicle_summary['scheduled_departure_reached_count']}",
        f"scheduled_departure_not_reached_count: "
        f"{vehicle_summary['scheduled_departure_not_reached_count']}",
        f"scheduled_departure_reached_count meaning: "
        f"{SCHEDULED_DEPARTURE_REACHED_COUNT_DEFINITION}",
        f"scheduled_departure counts vs actual state: "
        f"{SCHEDULED_DEPARTURE_COUNT_ACTUAL_STATE_NOTE}",
        f"vehicles on network (run/wait): {vehicle_summary['vehicles_on_network_count']}",
        "Full trip completion is not required for this benchmark.",
        f"exec_simulation seconds: {timing.exec_simulation_s}",
        f"seconds per evaluation timestep: {seconds_per_timestep}",
        f"reference seconds per evaluation timestep: "
        f"{runtime_scaling['reference_seconds_per_evaluation_timestep']}",
        f"per-timestep runtime ratio vs 1000-vehicle benchmark: "
        f"{runtime_scaling['per_timestep_runtime_ratio']}",
        f"runtime ratio note: {runtime_scaling['runtime_ratio_interpretation_note']}",
        f"interval timing available: {INTERVAL_TIMING_AVAILABLE}",
        f"transactions: {transaction_count}",
        f"transactions by node: {transactions_by_node}",
        f"internal grid link vehicles at evaluation end: "
        f"{vehicle_summary['internal_grid_link_vehicle_count_at_evaluation_end']}",
        f"OD connector vehicles at evaluation end: "
        f"{vehicle_summary['od_connector_vehicle_count_at_evaluation_end']}",
        f"world_build seconds: {timing.world_build_s}",
        f"finalize seconds: {timing.finalize_s}",
        f"research_output_build seconds: {timing.research_build_s}",
        f"research_csv_write seconds: {timing.research_csv_write_s}",
        f"vehicle_vot_csv_write seconds: {timing.vehicle_vot_csv_write_s}",
        f"pre_manifest_script_total seconds: {timing.pre_manifest_script_total_s}",
        f"manifest_write seconds: {timing.manifest_write_s}",
        (
            "run_summary_write seconds: appended on the last line after this file "
            "is closed; not included in pre_manifest_script_total."
        ),
        f"output directory bytes after manifest.json: {directory_bytes_after_manifest}",
        f"output directory: {TRIAL_OUTPUT_DIR}",
        (
            "Directory byte total excludes run_summary.txt itself. "
            "The console prints the final directory total after run_summary.txt."
        ),
        "Per-timestep spillback rows are not saved.",
        "Production code was not modified.",
        "A write failure can leave a partial output directory.",
    ]
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def print_console_summary(
    timing: TimingRecord,
    vehicle_summary: dict,
    transaction_count: int,
    runtime_scaling: dict,
    final_script_total_s: float,
    output_total_bytes: int,
) -> None:
    seconds_per_timestep = _seconds_per_evaluation_timestep(timing.exec_simulation_s)
    print()
    print("scenario:", SCENARIO_NAME)
    print("vehicles:", NUM_VEHICLES)
    print(
        f"departure: T={DEPARTURE_START}..{DEPARTURE_END}; "
        f"evaluation: T={EVALUATION_START_TIMESTEP}..{EVALUATION_END_TIMESTEP}"
    )
    print("transactions:", transaction_count)
    print("vehicle state counts:", vehicle_summary["vehicle_state_counts"])
    print("exec simulation seconds:", timing.exec_simulation_s)
    print("seconds per evaluation timestep:", seconds_per_timestep)
    print(
        "per-timestep runtime ratio vs 1000-vehicle benchmark:",
        runtime_scaling["per_timestep_runtime_ratio"],
    )
    print("final_script_total seconds:", final_script_total_s)
    print("output directory total bytes:", output_total_bytes)
    print("output directory:", TRIAL_OUTPUT_DIR)
    print("(Not a formal performance comparison.)")
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
        "build_tvt_mp_research_output",
        "write_tvt_mp_research_output_csv",
        "addVehicle",
        "World",
        "generate_vehicle_plans",
        "generate_vehicle_vots",
        "build_world_and_network",
        "_run_benchmark",
        "main",
        "open",
    }
    for name in _call_names(function_node):
        if name in forbidden:
            raise RuntimeError(f"Static validation must not call {name}.")


def _assert_tvt_targets_and_free_routing(tree: ast.Module) -> None:
    build_function = _function_node(tree, "build_world_and_network")
    if build_function is None:
        raise RuntimeError("build_world_and_network is missing.")
    saw_infer = False
    saw_set_order_control = False
    for node in ast.walk(build_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "infer_order_control_eligible_nodes":
            saw_infer = True
        if node.func.attr == "set_order_control_for_nodes":
            saw_set_order_control = True
            if len(node.args) < 1 or not isinstance(node.args[0], ast.Name):
                raise RuntimeError("set_order_control_for_nodes must take INTERNAL_GRID_NODES.")
            if node.args[0].id != "INTERNAL_GRID_NODES":
                raise RuntimeError(
                    "TVT-MP targets must be the internal grid nodes, not external OD nodes."
                )
            if node.args[0].id == "EXTERNAL_OD_NODES":
                raise RuntimeError("External OD nodes must not be TVT-MP targets.")
    if saw_infer is not True:
        raise RuntimeError("build_world_and_network must infer order-control eligibility.")
    if saw_set_order_control is not True:
        raise RuntimeError("build_world_and_network must set order control on internal nodes.")

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


def _assert_does_not_import_1000_vehicle_benchmark(tree: ast.Module) -> None:
    forbidden_substring = "run_tvt_mp_6x6_grid_high_demand_1000_vehicle_short_benchmark"
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if forbidden_substring in alias.name:
                    raise RuntimeError(
                        "This script must not import the 1000-vehicle short benchmark module."
                    )
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if forbidden_substring in module:
                raise RuntimeError(
                    "This script must not import the 1000-vehicle short benchmark module."
                )


def _assert_run_benchmark_does_not_require_transactions_or_full_completion(
    tree: ast.Module,
) -> None:
    run_function = _function_node(tree, "_run_benchmark")
    if run_function is None:
        raise RuntimeError("_run_benchmark is missing.")
    for node in ast.walk(run_function):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], (ast.Lt, ast.LtE)):
            continue
        left = test.left
        if not isinstance(left, ast.Name) or left.id != "transaction_count":
            continue
        if len(test.comparators) != 1 or not isinstance(test.comparators[0], ast.Constant):
            continue
        if test.comparators[0].value != 1:
            continue
        if any(isinstance(child, ast.Raise) for child in node.body):
            raise RuntimeError(
                "_run_benchmark must not require transaction_count >= 1."
            )


def _assert_main_static_branch(tree: ast.Module) -> None:
    main_function = _function_node(tree, "main")
    if main_function is None:
        raise RuntimeError("main is missing.")
    static_calls = _call_names(main_function)
    if "exec_simulation" in static_calls or "mkdir" in static_calls:
        raise RuntimeError("main must not simulate or create directories itself.")
    if "_run_benchmark" not in static_calls:
        raise RuntimeError("main must be able to start the benchmark on the normal path.")
    if "validate_static_contract" not in static_calls:
        raise RuntimeError("main must call validate_static_contract for --static-validate-only.")


def validate_static_contract() -> None:
    if NUM_VEHICLES != 5000:
        raise RuntimeError("NUM_VEHICLES must be 5000.")
    if GRID_SIZE != 6:
        raise RuntimeError("GRID_SIZE must be 6.")
    if INTERNAL_GRID_NODE_COUNT != 36 or INTERNAL_GRID_NODE_COUNT != GRID_SIZE * GRID_SIZE:
        raise RuntimeError("Internal grid node count must be 36.")
    if EXTERNAL_OD_NODE_COUNT != 24 or EXTERNAL_OD_NODE_COUNT != 4 * GRID_SIZE:
        raise RuntimeError("External OD node count must be 24.")
    if TOTAL_NODE_COUNT != 60:
        raise RuntimeError("Total node count must be 60.")
    if INTERNAL_DIRECTED_LINK_COUNT != 120:
        raise RuntimeError("Internal directed link count must be 120.")
    if OD_CONNECTOR_DIRECTED_LINK_COUNT != 48:
        raise RuntimeError("OD connector directed link count must be 48.")
    if TOTAL_LINK_COUNT != 168:
        raise RuntimeError("Total link count must be 168.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 500:
        raise RuntimeError("Departure window must be 0..500.")
    if EVALUATION_END_TIMESTEP != 599:
        raise RuntimeError("Evaluation end must be 599.")
    if BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("Baseline horizon must be 30.")
    if INTERNAL_TSIZE != 630:
        raise RuntimeError("INTERNAL_TSIZE must be 630.")
    if INTERNAL_TSIZE != EVALUATION_END_TIMESTEP + BASELINE_HORIZON_STEPS + 1:
        raise RuntimeError("INTERNAL_TSIZE must be evaluation end + horizon + 1.")
    if EXPECTED_WORLD_T_AFTER_SIM != 600:
        raise RuntimeError("Expected World.T after simulation must be 600.")
    if EXPECTED_WORLD_T_AFTER_SIM != EVALUATION_END_TIMESTEP + 1:
        raise RuntimeError("Expected World.T must be evaluation end + 1.")
    if SIMULATED_EVALUATION_TIMESTEPS != 600:
        raise RuntimeError("Simulated evaluation timestep count must be 600.")
    if MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Candidate visit limit must be explicit N=10.")
    if WORLD_COPY_RECURSION_LIMIT != 50000:
        raise RuntimeError("World copy recursion limit must be 50000.")
    if CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Clearance must be 1.")
    if TRAFFIC_SEED != 0:
        raise RuntimeError("Traffic seed must be 0.")
    if DEMAND_GEN_SEED != 42:
        raise RuntimeError("Demand seed must be 42.")
    if VOT_SEED != 1:
        raise RuntimeError("VOT seed must be 1.")
    if SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("specified_route must not be used.")
    if ALL_VEHICLES_PARTICIPATE is not True:
        raise RuntimeError("All vehicles must participate.")
    if len(INTERNAL_GRID_NODES) != 36:
        raise RuntimeError("Internal grid node list length is not 36.")
    if len(EXTERNAL_OD_NODES) != 24:
        raise RuntimeError("External OD node list length is not 24.")
    if set(INTERNAL_GRID_NODES) & set(EXTERNAL_OD_NODES):
        raise RuntimeError("Internal grid nodes and external OD nodes overlap.")
    if len(INTERNAL_LINK_SPECS) != 120 or len(OD_CONNECTOR_LINK_SPECS) != 48:
        raise RuntimeError("Built link spec counts do not match 120 and 48.")
    required_name_parts = (
        "tvt_mp",
        "6x6_grid",
        "5000_vehicle",
        "eval_600_timestep",
        "early_scaling_benchmark",
        "candidate_limit_10",
        "seed_0",
        "vot_seed_1",
    )
    for part in required_name_parts:
        if part not in SCENARIO_NAME or part not in TRIAL_OUTPUT_DIR_NAME:
            raise RuntimeError(f"Scenario or output name is missing {part!r}.")

    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    assigned = _module_assigned_constants(tree)
    expected_ints = {
        "NUM_VEHICLES": 5000,
        "GRID_SIZE": 6,
        "INTERNAL_GRID_NODE_COUNT": 36,
        "EXTERNAL_OD_NODE_COUNT": 24,
        "TOTAL_NODE_COUNT": 60,
        "INTERNAL_DIRECTED_LINK_COUNT": 120,
        "OD_CONNECTOR_DIRECTED_LINK_COUNT": 48,
        "TOTAL_LINK_COUNT": 168,
        "DEPARTURE_START": 0,
        "DEPARTURE_END": 500,
        "EVALUATION_END_TIMESTEP": 599,
        "BASELINE_HORIZON_STEPS": 30,
        "INTERNAL_TSIZE": 630,
        "EXPECTED_WORLD_T_AFTER_SIM": 600,
        "SIMULATED_EVALUATION_TIMESTEPS": 600,
        "MAX_CANDIDATE_VISIT_COUNT": 10,
        "CLEARANCE_TIMESTEPS": 1,
        "TRAFFIC_SEED": 0,
        "DEMAND_GEN_SEED": 42,
        "VOT_SEED": 1,
        "MIN_OD_MANHATTAN_DISTANCE": 5,
        "MERGE_PRIORITY": 1,
        "NUMBER_OF_LANES": 1,
        "INTERNAL_LINK_LENGTH": 400,
        "OD_CONNECTOR_LENGTH": 300,
        "FREE_FLOW_SPEED": 20,
        "WORLD_COPY_RECURSION_LIMIT": 50000,
    }
    for name, expected in expected_ints.items():
        if assigned.get(name) != expected:
            raise RuntimeError(f"Module constant {name} must be {expected}.")
    if assigned.get("SPECIFIED_ROUTE_USED") is not False:
        raise RuntimeError("SPECIFIED_ROUTE_USED must be False.")
    if assigned.get("ROUTE_ASSIGNMENT_MODE") != "uxsim_free_route_choice":
        raise RuntimeError("Route assignment must be free route choice.")

    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    _assert_static_function_does_not_run(validator)
    _assert_does_not_import_1000_vehicle_benchmark(tree)
    _assert_run_benchmark_does_not_require_transactions_or_full_completion(tree)
    _assert_tvt_targets_and_free_routing(tree)
    _assert_main_static_branch(tree)


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------

def _refuse_existing_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Rename or remove it manually before re-running."
        )


def _run_benchmark() -> int:
    script_start = time.perf_counter()
    timing = TimingRecord()
    original_recursion_limit = sys.getrecursionlimit()
    try:
        if original_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)
        effective_recursion_limit = sys.getrecursionlimit()

        _refuse_existing_output_directory()

        plans = generate_vehicle_plans()
        plan_audit = verify_vehicle_plans(plans)
        vot_values = generate_vehicle_vots(len(plans))
        vot_records = build_vehicle_vot_records(plans, vot_values)

        started = time.perf_counter()
        world = build_world_and_network()
        add_vehicles_to_world(world, vot_records)
        timing.world_build_s = time.perf_counter() - started
        verify_network_runtime(world)

        started = time.perf_counter()
        world.finalize_scenario()
        timing.finalize_s = time.perf_counter() - started
        if world.TSIZE != INTERNAL_TSIZE:
            raise RuntimeError(f"World.TSIZE is {world.TSIZE!r}, expected {INTERNAL_TSIZE}.")
        if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError("N=10 was not kept after finalize.")

        started = time.perf_counter()
        world.exec_simulation()
        timing.exec_simulation_s = time.perf_counter() - started

        verify_evaluation_end(world)
        if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError("N=10 changed during simulation.")
        vehicle_summary = collect_evaluation_end_vehicle_summary(world, plans)
        ledger_summary = collect_node_rank_ledger_summary(world)
        visit_id_summary = collect_visit_id_summary(world)

        started = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        timing.research_build_s = time.perf_counter() - started
        if bundle.scenario[0].scenario_name != SCENARIO_NAME:
            raise RuntimeError("Research output scenario name does not match.")
        transaction_count = bundle.scenario[0].transaction_count
        transactions_by_node = collect_transaction_counts_by_node(bundle)
        verify_transaction_totals(transaction_count, transactions_by_node)
        runtime_scaling = _runtime_scaling_metrics(timing)

        _refuse_existing_output_directory()
        TRIAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

        started = time.perf_counter()
        write_tvt_mp_research_output_csv(bundle, TRIAL_OUTPUT_DIR, overwrite=False)
        timing.research_csv_write_s = time.perf_counter() - started
        for name in RESEARCH_CSV_NAMES:
            path = TRIAL_OUTPUT_DIR / name
            if not path.is_file():
                raise RuntimeError(f"Expected research CSV missing: {path}.")

        research_paths = [TRIAL_OUTPUT_DIR / name for name in RESEARCH_CSV_NAMES]
        vot_path = TRIAL_OUTPUT_DIR / "vehicle_vot.csv"
        started = time.perf_counter()
        write_vehicle_vot_csv(vot_path, vot_records)
        timing.vehicle_vot_csv_write_s = time.perf_counter() - started
        file_sizes = _file_sizes(research_paths + [vot_path])
        timing.pre_manifest_script_total_s = time.perf_counter() - script_start

        manifest_path = TRIAL_OUTPUT_DIR / "manifest.json"
        started = time.perf_counter()
        write_manifest_json(
            manifest_path,
            timing,
            plan_audit,
            vehicle_summary,
            ledger_summary,
            visit_id_summary,
            transactions_by_node,
            transaction_count,
            runtime_scaling,
            file_sizes,
            original_recursion_limit,
            effective_recursion_limit,
        )
        timing.manifest_write_s = time.perf_counter() - started

        directory_bytes_after_manifest = 0
        for path in TRIAL_OUTPUT_DIR.iterdir():
            if path.is_file():
                directory_bytes_after_manifest += path.stat().st_size

        summary_path = TRIAL_OUTPUT_DIR / "run_summary.txt"
        started = time.perf_counter()
        write_run_summary_txt(
            summary_path,
            timing,
            plan_audit,
            vehicle_summary,
            transaction_count,
            transactions_by_node,
            runtime_scaling,
            directory_bytes_after_manifest,
        )
        timing.run_summary_write_s = time.perf_counter() - started
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(f"run_summary_write seconds: {timing.run_summary_write_s}\n")
        final_script_total_s = time.perf_counter() - script_start

        output_total_bytes = 0
        for path in TRIAL_OUTPUT_DIR.iterdir():
            if path.is_file():
                output_total_bytes += path.stat().st_size
        print_console_summary(
            timing,
            vehicle_summary,
            transaction_count,
            runtime_scaling,
            final_script_total_s,
            output_total_bytes,
        )
        return 0
    finally:
        sys.setrecursionlimit(original_recursion_limit)


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
        print("Static contract validation passed.", file=sys.stderr)
        return 0
    return _run_benchmark()


if __name__ == "__main__":
    raise SystemExit(main())
