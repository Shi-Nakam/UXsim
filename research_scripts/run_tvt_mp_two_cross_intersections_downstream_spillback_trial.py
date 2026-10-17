"""
TVT-MP trial: two cross intersections in a row, with downstream spillback.

East intersection receives heavy OD-only demand. West intersection then sends
north-approach traffic toward that downstream queue and south-approach traffic
toward the west outer node. Routes are chosen by UXsim. This script does not
force a movement, a route, or a spillback event.

The spillback CSV records the real World's connector link once per timestep,
immediately after that link's Link.update returns. Link.update refills
capacity before it returns, and Node.transfer has not run yet.
exec_simulation calls the TVT-MP driver before Link.update, so the driver
wrapper only forwards that one call and arms this post-update record.
Baseline forks and candidate Worlds are not recorded.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from uxsim import Link, World
from uxsim import order_control_tvt_mp_driver as tvt_mp_driver_module
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

SCENARIO_NAME = "tvt_mp_two_cross_intersections_downstream_spillback_trial"
WORLD_DISPLAY_NAME = "tvt_mp_two_cross_intersections_downstream_spillback"

EAST_DESTINATION_SEED = 1
WEST_NORTH_DESTINATION_SEED = 2
VOT_SEED = 1
TRAFFIC_SEED = 0

VOT_ARITHMETIC_MEAN = 1.0
VOT_ARITHMETIC_STDDEV = 3.0
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

EVALUATION_START_TIMESTEP = 0
EVALUATION_END_TIMESTEP = 599
INTERNAL_TSIZE = 630
EXPECTED_WORLD_T_AFTER_SIM = EVALUATION_END_TIMESTEP + 1

BASELINE_HORIZON_STEPS = 30
MAX_CANDIDATE_VISIT_COUNT = 10
EXPECTED_DRIVER_CALL_COUNT = EVALUATION_END_TIMESTEP - EVALUATION_START_TIMESTEP + 1
CLEARANCE_TIMESTEPS = 1
WORLD_COPY_RECURSION_LIMIT = 3000

DECISION_WINDOW_CONTRACT = (
    "0 < baseline_arrival_timestep - T <= 6 "
    "(code constant; not set in script)"
)

FREE_FLOW_SPEED_M_PER_S = 60000 / 3600
LINK_LENGTH_M = 200
NUMBER_OF_LANES = 1
CAPACITY_SETTINGS_UNIFORM = True
ROUTE_ASSIGNMENT_MODE = "uxsim_dynamic_route_choice_from_od"
SPECIFIED_ROUTE_USED = False

WEST_INTERSECTION_NODE = "west_intersection"
EAST_INTERSECTION_NODE = "east_intersection"
TVT_MP_NODE_NAMES: tuple[str, ...] = (
    WEST_INTERSECTION_NODE,
    EAST_INTERSECTION_NODE,
)

NODE_NAMES: tuple[str, ...] = (
    WEST_INTERSECTION_NODE,
    EAST_INTERSECTION_NODE,
    "west_outer",
    "west_north",
    "west_south",
    "east_outer",
    "east_north",
    "east_south",
)

NODE_COORDINATES: dict[str, tuple[float, float]] = {
    "west_intersection": (0.0, 0.0),
    "east_intersection": (1.0, 0.0),
    "west_outer": (-1.0, 0.0),
    "west_north": (0.0, 1.0),
    "west_south": (0.0, -1.0),
    "east_outer": (2.0, 0.0),
    "east_north": (1.0, 1.0),
    "east_south": (1.0, -1.0),
}

# Seven road segments, each with two opposite links. 14 links total.
LINK_SPECS: tuple[tuple[str, str, str], ...] = (
    ("west_outer_to_west_intersection", "west_outer", "west_intersection"),
    ("west_intersection_to_west_outer", "west_intersection", "west_outer"),
    ("west_north_to_west_intersection", "west_north", "west_intersection"),
    ("west_intersection_to_west_north", "west_intersection", "west_north"),
    ("west_south_to_west_intersection", "west_south", "west_intersection"),
    ("west_intersection_to_west_south", "west_intersection", "west_south"),
    ("west_intersection_to_east_intersection", "west_intersection", "east_intersection"),
    ("east_intersection_to_west_intersection", "east_intersection", "west_intersection"),
    ("east_north_to_east_intersection", "east_north", "east_intersection"),
    ("east_intersection_to_east_north", "east_intersection", "east_north"),
    ("east_south_to_east_intersection", "east_south", "east_intersection"),
    ("east_intersection_to_east_south", "east_intersection", "east_south"),
    ("east_outer_to_east_intersection", "east_outer", "east_intersection"),
    ("east_intersection_to_east_outer", "east_intersection", "east_outer"),
)

SPILLBACK_LINK_NAME = "west_intersection_to_east_intersection"
SPILLBACK_REVERSE_LINK_NAME = "east_intersection_to_west_intersection"

LINK_COUNT = len(LINK_SPECS)
NODE_COUNT = len(NODE_NAMES)

EAST_DEPARTURE_START_TIMESTEP = 5
EAST_DEPARTURE_END_TIMESTEP = 104
WEST_NORTH_DEPARTURE_START_TIMESTEP = 15
WEST_NORTH_DEPARTURE_END_TIMESTEP = 114
WEST_SOUTH_DEPARTURE_START_TIMESTEP = 15
WEST_SOUTH_DEPARTURE_END_TIMESTEP = 113
WEST_SOUTH_DEPARTURE_INTERVAL_TIMESTEPS = 2

EAST_CONGESTION_VEHICLE_COUNT = 300
WEST_NORTH_VEHICLE_COUNT = 100
WEST_SOUTH_VEHICLE_COUNT = 50
EXPECTED_TOTAL_VEHICLE_COUNT = 450

WEST_NORTH_EASTBOUND_PROBABILITY = 0.7
WEST_NORTH_SOUTHBOUND_PROBABILITY = 0.3

# Same-timestep creation order. Names stay attached to each spec after sorting.
ORIGIN_CREATION_ORDER: tuple[str, ...] = (
    "east_north",
    "east_south",
    "east_outer",
    "west_north",
    "west_south",
)

ORIGIN_NAME_PREFIX = {
    "east_north": "en",
    "east_south": "es",
    "east_outer": "ee",
    "west_north": "wn",
    "west_south": "ws",
}

EAST_ORIGINS: tuple[str, ...] = ("east_north", "east_south", "east_outer")
WEST_NODES_FORBIDDEN_AS_EAST_DESTINATION: tuple[str, ...] = (
    "west_intersection",
    "west_outer",
    "west_north",
    "west_south",
)

# Two non-west destinations, equal probability via Random.choice.
EAST_DESTINATIONS_BY_ORIGIN: dict[str, tuple[str, ...]] = {
    "east_north": ("east_south", "east_outer"),
    "east_south": ("east_north", "east_outer"),
    "east_outer": ("east_north", "east_south"),
}

WEST_NORTH_EASTBOUND_DESTINATION = "east_outer"
WEST_NORTH_SOUTHBOUND_DESTINATION = "west_south"
WEST_SOUTH_DESTINATION = "west_outer"

# Local compass at one cross intersection. North-to-east is a left turn.
CROSS_MOVEMENT_BY_LOCAL_OD: dict[tuple[str, str], str] = {
    ("north", "south"): "straight",
    ("north", "east"): "left",
    ("north", "west"): "right",
    ("east", "west"): "straight",
    ("east", "south"): "left",
    ("east", "north"): "right",
    ("south", "north"): "straight",
    ("south", "west"): "left",
    ("south", "east"): "right",
    ("west", "east"): "straight",
    ("west", "north"): "left",
    ("west", "south"): "right",
}

EAST_LOCAL_DIRECTION = {
    "east_north": "north",
    "east_south": "south",
    "east_outer": "east",
}

SPILLBACK_CSV_NAME = "spillback_link_summary.csv"
SPILLBACK_CSV_FIELDS = (
    "timestep",
    "vehicle_count_on_link",
    "vehicle_names_on_link",
    "minimum_vehicle_x",
    "maximum_vehicle_x",
    "entrance_space_available",
    "entrance_blocked",
    "capacity_in_remain",
    "capacity_out_remain",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = (
    TRIAL_PARENT
    / "tvt_mp_two_cross_intersections_downstream_spillback_seed_1_initial"
)

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)

SCRIPT_PATH = Path(__file__).resolve()

KNOWN_OTHER_TRIAL_DIR_NAMES: tuple[str, ...] = (
    "tvt_mp_single_cross_intersection_12_vehicle_seed_1_initial",
    "tvt_mp_single_cross_intersection_high_demand_seed_1_initial",
    "tvt_mp_50_vehicle_medium_demand_seed_1_initial",
    "tvt_mp_50_vehicle_medium_demand_seed_1_passage_resolution_v2",
    "tvt_mp_50_vehicle_medium_demand_seed_1_capacity_refill_v3",
    "tvt_mp_50_vehicle_asymmetric_demand_seed_1_initial",
    "tvt_mp_small_scale_initial_seed_1_baseline_arrival_order",
    "tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2",
)

# Filled only while the simulation calls Link.update. Static validation does not run it.
SPILLBACK_TIMESTEP_ROWS: list[dict] = []


class _SpillbackObservationGate:
    """Process-local gate. It is not stored on a Link or a World."""

    real_world: World | None = None
    enabled: bool = False
    original_link_update: object = None
    original_run_tvt_mp_driver: object = None


_SPILLBACK_OBSERVATION_GATE = _SpillbackObservationGate()


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool
    traffic_group: str
    planned_movement: str


@dataclass(frozen=True)
class VehicleGenerationStats:
    total_vehicle_count: int
    participating_count: int
    nonparticipating_count: int
    departure_count_by_timestep: dict[int, int]
    origin_counts: dict[str, int]
    destination_counts: dict[str, int]
    od_counts: dict[str, int]
    vehicle_name_duplicate_count: int
    same_od_pair_count: int
    same_od_vehicle_count: int
    east_origin_counts: dict[str, int]
    east_destination_counts: dict[str, int]
    east_od_counts: dict[str, int]
    east_planned_movement_counts: dict[str, int]
    west_north_eastbound_count: int
    west_north_southbound_count: int
    west_north_eastbound_share: float
    west_north_southbound_share: float


def _od_key(origin: str, destination: str) -> str:
    return f"{origin}->{destination}"


def east_planned_movement(origin: str, destination: str) -> str:
    local_origin = EAST_LOCAL_DIRECTION[origin]
    local_destination = EAST_LOCAL_DIRECTION[destination]
    key = (local_origin, local_destination)
    if key not in CROSS_MOVEMENT_BY_LOCAL_OD:
        raise KeyError(f"No east-intersection movement for {origin} -> {destination}.")
    return CROSS_MOVEMENT_BY_LOCAL_OD[key]


def west_planned_movement(origin: str, destination: str) -> str:
    if origin == "west_north" and destination == WEST_NORTH_EASTBOUND_DESTINATION:
        return "left"
    if origin == "west_north" and destination == WEST_NORTH_SOUTHBOUND_DESTINATION:
        return "straight"
    if origin == "west_south" and destination == WEST_SOUTH_DESTINATION:
        return "left"
    raise KeyError(f"No west-intersection planned movement for {origin} -> {destination}.")


def _append_spec(
    specs_list: list[VehicleSpec],
    origin_counters: dict[str, int],
    origin: str,
    destination: str,
    departure_timestep: int,
    traffic_group: str,
    planned_movement: str,
) -> None:
    origin_counters[origin] += 1
    prefix = ORIGIN_NAME_PREFIX[origin]
    vehicle_name = f"veh_{prefix}_{origin_counters[origin]}"
    specs_list.append(
        VehicleSpec(
            vehicle_name=vehicle_name,
            orig=origin,
            dest=destination,
            departure_timestep=departure_timestep,
            participating=True,
            traffic_group=traffic_group,
            planned_movement=planned_movement,
        )
    )


def _build_vehicle_specs_and_stats() -> tuple[tuple[VehicleSpec, ...], VehicleGenerationStats]:
    """
    East destinations and west-north destinations use separate Random instances.
    VOT is not drawn here.
    """
    east_destination_rng = random.Random(EAST_DESTINATION_SEED)
    west_north_destination_rng = random.Random(WEST_NORTH_DESTINATION_SEED)

    origin_counters = {origin: 0 for origin in ORIGIN_CREATION_ORDER}
    specs_list: list[VehicleSpec] = []

    for departure_timestep in range(
        EAST_DEPARTURE_START_TIMESTEP,
        EAST_DEPARTURE_END_TIMESTEP + 1,
    ):
        for origin in EAST_ORIGINS:
            destinations = EAST_DESTINATIONS_BY_ORIGIN[origin]
            destination = east_destination_rng.choice(destinations)
            _append_spec(
                specs_list,
                origin_counters,
                origin,
                destination,
                departure_timestep,
                "east_congestion",
                east_planned_movement(origin, destination),
            )

    for departure_timestep in range(
        WEST_NORTH_DEPARTURE_START_TIMESTEP,
        WEST_NORTH_DEPARTURE_END_TIMESTEP + 1,
    ):
        draw = west_north_destination_rng.random()
        if draw < WEST_NORTH_EASTBOUND_PROBABILITY:
            destination = WEST_NORTH_EASTBOUND_DESTINATION
        else:
            destination = WEST_NORTH_SOUTHBOUND_DESTINATION
        _append_spec(
            specs_list,
            origin_counters,
            "west_north",
            destination,
            departure_timestep,
            "west_north",
            west_planned_movement("west_north", destination),
        )

    west_south_timestep = WEST_SOUTH_DEPARTURE_START_TIMESTEP
    while west_south_timestep <= WEST_SOUTH_DEPARTURE_END_TIMESTEP:
        _append_spec(
            specs_list,
            origin_counters,
            "west_south",
            WEST_SOUTH_DESTINATION,
            west_south_timestep,
            "west_south",
            west_planned_movement("west_south", WEST_SOUTH_DESTINATION),
        )
        west_south_timestep += WEST_SOUTH_DEPARTURE_INTERVAL_TIMESTEPS

    def sort_key(spec: VehicleSpec) -> tuple[int, int]:
        return (spec.departure_timestep, ORIGIN_CREATION_ORDER.index(spec.orig))

    specs_list.sort(key=sort_key)
    specs = tuple(specs_list)
    stats = _stats_from_specs(specs)
    return specs, stats


def _stats_from_specs(specs: tuple[VehicleSpec, ...]) -> VehicleGenerationStats:
    origin_counts = {origin: 0 for origin in ORIGIN_CREATION_ORDER}
    destination_counts: dict[str, int] = {}
    od_counts: dict[str, int] = {}
    departure_count_by_timestep: dict[int, int] = {}

    east_origin_counts = {origin: 0 for origin in EAST_ORIGINS}
    east_destination_counts: dict[str, int] = {}
    east_od_counts: dict[str, int] = {}
    east_planned_movement_counts = {"straight": 0, "left": 0, "right": 0, "u_turn": 0}

    west_north_eastbound_count = 0
    west_north_southbound_count = 0

    names = [spec.vehicle_name for spec in specs]
    duplicate_count = len(names) - len(set(names))

    for spec in specs:
        origin_counts[spec.orig] += 1
        destination_counts[spec.dest] = destination_counts.get(spec.dest, 0) + 1
        od_key = _od_key(spec.orig, spec.dest)
        od_counts[od_key] = od_counts.get(od_key, 0) + 1
        departure_count_by_timestep[spec.departure_timestep] = (
            departure_count_by_timestep.get(spec.departure_timestep, 0) + 1
        )
        if spec.traffic_group == "east_congestion":
            east_origin_counts[spec.orig] += 1
            east_destination_counts[spec.dest] = (
                east_destination_counts.get(spec.dest, 0) + 1
            )
            east_od_counts[od_key] = east_od_counts.get(od_key, 0) + 1
            east_planned_movement_counts[spec.planned_movement] += 1
        if spec.traffic_group == "west_north":
            if spec.dest == WEST_NORTH_EASTBOUND_DESTINATION:
                west_north_eastbound_count += 1
            elif spec.dest == WEST_NORTH_SOUTHBOUND_DESTINATION:
                west_north_southbound_count += 1

    same_od_pair_count = 0
    same_od_vehicle_count = 0
    for count in od_counts.values():
        if count >= 2:
            same_od_pair_count += 1
            same_od_vehicle_count += count

    west_north_total = west_north_eastbound_count + west_north_southbound_count
    if west_north_total == 0:
        eastbound_share = 0.0
        southbound_share = 0.0
    else:
        eastbound_share = west_north_eastbound_count / west_north_total
        southbound_share = west_north_southbound_count / west_north_total

    participating_count = sum(1 for spec in specs if spec.participating)
    return VehicleGenerationStats(
        total_vehicle_count=len(specs),
        participating_count=participating_count,
        nonparticipating_count=len(specs) - participating_count,
        departure_count_by_timestep=dict(sorted(departure_count_by_timestep.items())),
        origin_counts=origin_counts,
        destination_counts=dict(sorted(destination_counts.items())),
        od_counts=dict(sorted(od_counts.items())),
        vehicle_name_duplicate_count=duplicate_count,
        same_od_pair_count=same_od_pair_count,
        same_od_vehicle_count=same_od_vehicle_count,
        east_origin_counts=east_origin_counts,
        east_destination_counts=dict(sorted(east_destination_counts.items())),
        east_od_counts=dict(sorted(east_od_counts.items())),
        east_planned_movement_counts=east_planned_movement_counts,
        west_north_eastbound_count=west_north_eastbound_count,
        west_north_southbound_count=west_north_southbound_count,
        west_north_eastbound_share=eastbound_share,
        west_north_southbound_share=southbound_share,
    )


VEHICLE_SPECS, GENERATION_STATS = _build_vehicle_specs_and_stats()


@dataclass
class TimingRecord:
    world_build_s: float = 0.0
    finalize_s: float = 0.0
    exec_simulation_s: float = 0.0
    research_build_s: float = 0.0
    csv_write_s: float = 0.0
    trial_aux_write_s: float = 0.0
    script_total_s: float = 0.0


@dataclass
class VehicleVotRecord:
    vehicle_name: str
    origin: str
    destination: str
    departure_timestep: int
    participates_in_order_exchange: bool
    true_vot_per_second: float
    declared_vot_per_second: float | None


def manifest_counts_from_specs(stats: VehicleGenerationStats) -> dict:
    return {
        "scenario_name": SCENARIO_NAME,
        "actual_vehicle_count": stats.total_vehicle_count,
        "participating_count": stats.participating_count,
        "nonparticipating_count": stats.nonparticipating_count,
        "east_congestion_vehicle_count": stats.origin_counts["east_north"]
        + stats.origin_counts["east_south"]
        + stats.origin_counts["east_outer"],
        "west_north_vehicle_count": stats.origin_counts["west_north"],
        "west_south_vehicle_count": stats.origin_counts["west_south"],
        "east_destination_seed": EAST_DESTINATION_SEED,
        "west_north_destination_seed": WEST_NORTH_DESTINATION_SEED,
        "vot_seed": VOT_SEED,
        "traffic_seed": TRAFFIC_SEED,
        "west_north_eastbound_probability": WEST_NORTH_EASTBOUND_PROBABILITY,
        "west_north_southbound_probability": WEST_NORTH_SOUTHBOUND_PROBABILITY,
        "actual_west_north_eastbound_count": stats.west_north_eastbound_count,
        "actual_west_north_southbound_count": stats.west_north_southbound_count,
        "actual_west_north_eastbound_share": stats.west_north_eastbound_share,
        "actual_west_north_southbound_share": stats.west_north_southbound_share,
        "west_south_departure_interval_timesteps": WEST_SOUTH_DEPARTURE_INTERVAL_TIMESTEPS,
        "west_south_all_destination": WEST_SOUTH_DESTINATION,
        "node_count": NODE_COUNT,
        "link_count": LINK_COUNT,
        "tvt_mp_node_count": len(TVT_MP_NODE_NAMES),
        "tvt_mp_node_names": list(TVT_MP_NODE_NAMES),
        "link_length_m": LINK_LENGTH_M,
        "lane_count_per_link": NUMBER_OF_LANES,
        "capacity_settings_uniform": CAPACITY_SETTINGS_UNIFORM,
        "route_assignment_mode": ROUTE_ASSIGNMENT_MODE,
        "specified_route_used": SPECIFIED_ROUTE_USED,
        "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "clearance_timesteps": CLEARANCE_TIMESTEPS,
        "evaluation_start_timestep": EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "internal_tsize": INTERNAL_TSIZE,
        "expected_driver_call_count": EXPECTED_DRIVER_CALL_COUNT,
        "spillback_link_name": SPILLBACK_LINK_NAME,
        "origin_counts": stats.origin_counts,
        "destination_counts": stats.destination_counts,
        "od_counts": stats.od_counts,
        "departure_count_by_timestep": stats.departure_count_by_timestep,
        "vehicle_name_duplicate_count": stats.vehicle_name_duplicate_count,
        "same_od_pair_count": stats.same_od_pair_count,
        "same_od_vehicle_count": stats.same_od_vehicle_count,
        "east_origin_counts": stats.east_origin_counts,
        "east_destination_counts": stats.east_destination_counts,
        "east_od_counts": stats.east_od_counts,
        "east_planned_movement_counts": stats.east_planned_movement_counts,
    }


def entrance_space_available_from_link_state(link) -> bool:
    """
    Same entrance test as UXsim Node transfer.

    Room exists when the link holds fewer vehicles than its lane count, or when
    the latest entered vehicle on the entrance side has x greater than
    delta_per_lane * DELTAN. This reads link attributes only.
    """
    if len(link.vehicles) < link.number_of_lanes:
        return True
    entrance_vehicle = link.vehicles[-link.number_of_lanes]
    entry_gap = link.delta_per_lane * link.W.DELTAN
    return entrance_vehicle.x > entry_gap


def record_spillback_link_before_real_world_transfer(world) -> None:
    """
    Record the real World's spillback link after its Link.update capacity refill.

    exec_simulation order for one timestep is: TVT-MP driver, then every
    Link.update (capacity refill inside that call), then Node.generate and
    Node.update, then Node.transfer. This function runs when the spillback
    link's Link.update has returned and before any Node.transfer.
    """
    timestep = world.T
    for row in SPILLBACK_TIMESTEP_ROWS:
        if row["timestep"] == timestep:
            raise RuntimeError(
                f"Spillback timestep {timestep} is already recorded."
            )
    link = world.get_link(SPILLBACK_LINK_NAME)
    vehicles = list(link.vehicles)
    vehicle_count = len(vehicles)
    if vehicle_count == 0:
        minimum_x = ""
        maximum_x = ""
    else:
        positions = [vehicle.x for vehicle in vehicles]
        minimum_x = min(positions)
        maximum_x = max(positions)
    entrance_open = entrance_space_available_from_link_state(link)
    names = [vehicle.name for vehicle in vehicles]
    SPILLBACK_TIMESTEP_ROWS.append(
        {
            "timestep": timestep,
            "vehicle_count_on_link": vehicle_count,
            "vehicle_names_on_link": "|".join(names),
            "minimum_vehicle_x": minimum_x,
            "maximum_vehicle_x": maximum_x,
            "entrance_space_available": entrance_open,
            "entrance_blocked": (not entrance_open),
            "capacity_in_remain": link.capacity_in_remain,
            "capacity_out_remain": link.capacity_out_remain,
        }
    )


def run_real_world_tvt_mp_driver_once(world):
    """
    Forward one TVT-MP driver call.

    uxsim.World.exec_simulation calls this before Link.update. Spillback state
    is therefore not read here. Observation is armed only after this call
    returns, which is still before the real World's Link.update and Node.transfer.
    While the original driver runs, Link.update and the driver module
    attribute are the UXsim originals, so baseline and candidate copies do
    not see this script's functions and do not re-enter this wrapper.
    """
    gate = _SPILLBACK_OBSERVATION_GATE
    original_run_tvt_mp_driver = gate.original_run_tvt_mp_driver
    original_link_update = gate.original_link_update
    observe_after_return = world is gate.real_world
    if observe_after_return:
        gate.enabled = False
        tvt_mp_driver_module.run_tvt_mp_driver = original_run_tvt_mp_driver
        Link.update = original_link_update
    try:
        result = original_run_tvt_mp_driver(world)
    finally:
        if observe_after_return:
            tvt_mp_driver_module.run_tvt_mp_driver = (
                run_real_world_tvt_mp_driver_once
            )
            Link.update = update_link_and_record_real_world_spillback
            gate.enabled = True
    return result


def update_link_and_record_real_world_spillback(link) -> None:
    """
    Run the simulator's one Link.update, then record the real spillback link.

    The original update is the call exec_simulation already made. This hook
    does not call Node.transfer and does not update any other link.
    """
    gate = _SPILLBACK_OBSERVATION_GATE
    original_link_update = gate.original_link_update
    original_link_update(link)
    if gate.enabled is not True:
        return
    if link.W is not gate.real_world:
        return
    if link.name != SPILLBACK_LINK_NAME:
        return
    record_spillback_link_before_real_world_transfer(gate.real_world)


def install_real_world_spillback_observation(real_world) -> None:
    gate = _SPILLBACK_OBSERVATION_GATE
    if gate.original_run_tvt_mp_driver is not None:
        raise RuntimeError("Spillback observation is already installed.")
    gate.real_world = real_world
    gate.enabled = False
    gate.original_run_tvt_mp_driver = tvt_mp_driver_module.run_tvt_mp_driver
    gate.original_link_update = Link.update
    tvt_mp_driver_module.run_tvt_mp_driver = run_real_world_tvt_mp_driver_once
    Link.update = update_link_and_record_real_world_spillback


def restore_real_world_spillback_observation() -> None:
    gate = _SPILLBACK_OBSERVATION_GATE
    if gate.original_run_tvt_mp_driver is not None:
        tvt_mp_driver_module.run_tvt_mp_driver = gate.original_run_tvt_mp_driver
    if gate.original_link_update is not None:
        Link.update = gate.original_link_update
    gate.real_world = None
    gate.enabled = False
    gate.original_run_tvt_mp_driver = None
    gate.original_link_update = None


def _assert_link_user_functions_are_none(world, label: str) -> None:
    for link in world.LINKS:
        if link.user_function is not None:
            raise RuntimeError(
                f"{label}: {link.name} user_function is {link.user_function!r}."
            )


def _assert_spillback_observer_is_not_a_world_callback(world) -> None:
    observer = record_spillback_link_before_real_world_transfer
    if world.user_function is observer:
        raise RuntimeError("World holds the spillback observer as user_function.")
    for link in world.LINKS:
        if link.user_function is observer:
            raise RuntimeError(
                f"{link.name} holds the spillback observer as user_function."
            )
    for node in world.NODES:
        if node.user_function is observer:
            raise RuntimeError(
                f"{node.name} holds the spillback observer as user_function."
            )


def _module_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Missing function {name}.")


def _called_names(function: ast.FunctionDef) -> list[str]:
    names: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def _assert_observation_wrapper_calls_driver_once() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    driver_wrapper = _module_function(tree, "run_real_world_tvt_mp_driver_once")
    called = _called_names(driver_wrapper)
    original_calls = called.count("original_run_tvt_mp_driver")
    if original_calls != 1:
        raise RuntimeError(
            "TVT-MP driver wrapper must call the original driver once, "
            f"found {original_calls}."
        )
    if "record_spillback_link_before_real_world_transfer" in called:
        raise RuntimeError(
            "Driver wrapper must not record spillback before Link.update."
        )
    link_hook = _module_function(
        tree,
        "update_link_and_record_real_world_spillback",
    )
    link_called = _called_names(link_hook)
    if link_called.count("original_link_update") != 1:
        raise RuntimeError("Link hook must delegate the simulator Link.update once.")
    if link_called.count("record_spillback_link_before_real_world_transfer") != 1:
        raise RuntimeError("Link hook must record the real spillback link once.")
    if "transfer" in link_called or "run_tvt_mp_driver" in link_called:
        raise RuntimeError("Link hook must not transfer or call the TVT-MP driver.")
    recorder = _module_function(
        tree,
        "record_spillback_link_before_real_world_transfer",
    )
    recorder_called = _called_names(recorder)
    for forbidden in (
        "update",
        "transfer",
        "run_tvt_mp_driver",
        "original_link_update",
        "original_run_tvt_mp_driver",
    ):
        if forbidden in recorder_called:
            raise RuntimeError(f"Spillback recorder must not call {forbidden}.")


def _assert_main_recursion_limit_try_finally() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    main_func = _module_function(tree, "main")
    has_get_recursion_limit = False
    raises_for_world_copy = False
    has_finally_restore = False
    for node in ast.walk(main_func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "getrecursionlimit":
                has_get_recursion_limit = True
            if node.func.attr == "setrecursionlimit":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id == (
                        "original_python_recursion_limit"
                    ):
                        has_finally_restore = True
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if (
                    isinstance(comparator, ast.Name)
                    and comparator.id == "WORLD_COPY_RECURSION_LIMIT"
                ):
                    raises_for_world_copy = True
    if has_get_recursion_limit is not True:
        raise RuntimeError("main must save sys.getrecursionlimit().")
    if raises_for_world_copy is not True:
        raise RuntimeError(
            "main must compare the saved limit against WORLD_COPY_RECURSION_LIMIT."
        )
    try_nodes = [node for node in main_func.body if isinstance(node, ast.Try)]
    if len(try_nodes) != 1:
        raise RuntimeError("main must use one try/finally for recursion restore.")
    try_node = try_nodes[0]
    if len(try_node.finalbody) == 0:
        raise RuntimeError("main must restore the recursion limit in finally.")
    if has_finally_restore is not True:
        raise RuntimeError(
            "main finally must call sys.setrecursionlimit("
            "original_python_recursion_limit)."
        )


def _occupied_length_of_row(row: dict) -> float:
    if row["vehicle_count_on_link"] == 0:
        return 0.0
    return float(row["maximum_vehicle_x"]) - float(row["minimum_vehicle_x"])


def summarize_spillback_rows(rows: list[dict]) -> dict:
    """
    maximum_occupied_length_estimate is the largest (maximum_x - minimum_x)
    across timesteps. A single vehicle on the link contributes 0.
    """
    maximum_vehicle_count = 0
    maximum_occupied_length = 0.0
    blocked_timesteps: list[int] = []
    for row in rows:
        vehicle_count = int(row["vehicle_count_on_link"])
        if vehicle_count > maximum_vehicle_count:
            maximum_vehicle_count = vehicle_count
        occupied_length = _occupied_length_of_row(row)
        if occupied_length > maximum_occupied_length:
            maximum_occupied_length = occupied_length
        if row["entrance_blocked"] is True:
            blocked_timesteps.append(int(row["timestep"]))
    if len(blocked_timesteps) == 0:
        first_blocked = None
        last_blocked = None
    else:
        first_blocked = blocked_timesteps[0]
        last_blocked = blocked_timesteps[-1]
    return {
        "maximum_vehicle_count_on_spillback_link": maximum_vehicle_count,
        "maximum_occupied_length_estimate": maximum_occupied_length,
        "entrance_blocked_timestep_count": len(blocked_timesteps),
        "first_entrance_blocked_timestep": first_blocked,
        "last_entrance_blocked_timestep": last_blocked,
    }


def _origin_order_key(spec: VehicleSpec) -> tuple[int, int]:
    return (spec.departure_timestep, ORIGIN_CREATION_ORDER.index(spec.orig))


def validate_static_contract() -> None:
    specs = VEHICLE_SPECS
    stats = GENERATION_STATS
    counts = manifest_counts_from_specs(stats)

    if NODE_COUNT != 8 or len(NODE_NAMES) != 8:
        raise RuntimeError(f"Expected 8 nodes, got {NODE_COUNT}.")
    if set(NODE_NAMES) != set(NODE_COORDINATES):
        raise RuntimeError("NODE_NAMES and NODE_COORDINATES do not match.")
    if len(TVT_MP_NODE_NAMES) != 2:
        raise RuntimeError("Expected 2 TVT-MP intersection nodes.")
    if LINK_COUNT != 14 or len(LINK_SPECS) != 14:
        raise RuntimeError(f"Expected 14 links, got {LINK_COUNT}.")
    link_names = [name for name, _up, _down in LINK_SPECS]
    if len(set(link_names)) != len(link_names):
        raise RuntimeError("Duplicate link name in LINK_SPECS.")
    if SPILLBACK_LINK_NAME not in link_names:
        raise RuntimeError("Spillback link is missing from LINK_SPECS.")
    if SPILLBACK_REVERSE_LINK_NAME not in link_names:
        raise RuntimeError("Reverse connector link is missing from LINK_SPECS.")
    connector_pairs = {
        (up, down) for _name, up, down in LINK_SPECS
    }
    if (WEST_INTERSECTION_NODE, EAST_INTERSECTION_NODE) not in connector_pairs:
        raise RuntimeError("Missing west_intersection -> east_intersection link.")
    if (EAST_INTERSECTION_NODE, WEST_INTERSECTION_NODE) not in connector_pairs:
        raise RuntimeError("Missing east_intersection -> west_intersection link.")
    if LINK_LENGTH_M != 200:
        raise RuntimeError("Link length must be 200 m.")
    if NUMBER_OF_LANES != 1:
        raise RuntimeError("Each link must have 1 lane.")
    if CAPACITY_SETTINGS_UNIFORM is not True:
        raise RuntimeError("Capacity settings must stay uniform.")
    if CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Clearance must be 1 timestep.")
    if EVALUATION_START_TIMESTEP != 0 or EVALUATION_END_TIMESTEP != 599:
        raise RuntimeError("Evaluation must be T=0..599.")
    if INTERNAL_TSIZE != 630:
        raise RuntimeError("INTERNAL_TSIZE must be 630.")
    if BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("Baseline horizon must be 30.")
    if MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Candidate visit limit must be 10.")
    if EXPECTED_DRIVER_CALL_COUNT != 600:
        raise RuntimeError(
            f"Expected 600 driver calls, got {EXPECTED_DRIVER_CALL_COUNT}."
        )
    if EXPECTED_WORLD_T_AFTER_SIM != 600:
        raise RuntimeError("Expected World.T after simulation is 600.")
    if SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("specified_route must stay unused.")
    if ROUTE_ASSIGNMENT_MODE != "uxsim_dynamic_route_choice_from_od":
        raise RuntimeError("Route assignment mode is not OD dynamic choice.")

    if len(specs) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_VEHICLE_COUNT} VehicleSpecs, got {len(specs)}."
        )
    if counts["actual_vehicle_count"] != len(specs):
        raise RuntimeError("Manifest vehicle count does not match VehicleSpec.")
    if counts["node_count"] != NODE_COUNT or counts["link_count"] != LINK_COUNT:
        raise RuntimeError("Manifest network counts do not match definitions.")
    if counts["east_congestion_vehicle_count"] != EAST_CONGESTION_VEHICLE_COUNT:
        raise RuntimeError("East congestion count is not 300.")
    if counts["west_north_vehicle_count"] != WEST_NORTH_VEHICLE_COUNT:
        raise RuntimeError("West-north count is not 100.")
    if counts["west_south_vehicle_count"] != WEST_SOUTH_VEHICLE_COUNT:
        raise RuntimeError("West-south count is not 50.")
    if (
        counts["east_congestion_vehicle_count"]
        + counts["west_north_vehicle_count"]
        + counts["west_south_vehicle_count"]
        != EXPECTED_TOTAL_VEHICLE_COUNT
    ):
        raise RuntimeError("Traffic group counts do not sum to 450.")

    east_timesteps = range(
        EAST_DEPARTURE_START_TIMESTEP,
        EAST_DEPARTURE_END_TIMESTEP + 1,
    )
    if len(list(east_timesteps)) != 100:
        raise RuntimeError("East departure window is not 100 timesteps.")
    for timestep in east_timesteps:
        at_t = [
            spec for spec in specs
            if spec.departure_timestep == timestep and spec.traffic_group == "east_congestion"
        ]
        if len(at_t) != 3:
            raise RuntimeError(
                f"T={timestep}: expected 3 east vehicles, got {len(at_t)}."
            )
        origins = [spec.orig for spec in at_t]
        if origins != list(EAST_ORIGINS):
            raise RuntimeError(
                f"T={timestep}: east vehicles are not in "
                "east_north, east_south, east_outer order."
            )
    west_north_timesteps = range(
        WEST_NORTH_DEPARTURE_START_TIMESTEP,
        WEST_NORTH_DEPARTURE_END_TIMESTEP + 1,
    )
    if len(list(west_north_timesteps)) != 100:
        raise RuntimeError("West-north departure window is not 100 timesteps.")
    for timestep in west_north_timesteps:
        at_t = [
            spec for spec in specs
            if spec.departure_timestep == timestep and spec.traffic_group == "west_north"
        ]
        if len(at_t) != 1:
            raise RuntimeError(
                f"T={timestep}: expected 1 west-north vehicle, got {len(at_t)}."
            )
    west_south_timesteps = list(
        range(
            WEST_SOUTH_DEPARTURE_START_TIMESTEP,
            WEST_SOUTH_DEPARTURE_END_TIMESTEP + 1,
            WEST_SOUTH_DEPARTURE_INTERVAL_TIMESTEPS,
        )
    )
    if west_south_timesteps[0] != 15 or west_south_timesteps[-1] != 113:
        raise RuntimeError("West-south departures must run from T=15 to T=113.")
    if len(west_south_timesteps) != WEST_SOUTH_VEHICLE_COUNT:
        raise RuntimeError("West-south departure count is not 50.")
    for timestep in west_south_timesteps:
        if timestep % 2 == 0:
            raise RuntimeError(f"West-south timestep T={timestep} is not odd.")
        at_t = [
            spec for spec in specs
            if spec.departure_timestep == timestep and spec.traffic_group == "west_south"
        ]
        if len(at_t) != 1:
            raise RuntimeError(
                f"T={timestep}: expected 1 west-south vehicle, got {len(at_t)}."
            )
    for spec in specs:
        if spec.traffic_group == "east_congestion":
            if spec.departure_timestep < 5 or spec.departure_timestep > 104:
                raise RuntimeError(f"{spec.vehicle_name} is outside T=5..104.")
            if spec.dest in WEST_NODES_FORBIDDEN_AS_EAST_DESTINATION:
                raise RuntimeError(
                    f"{spec.vehicle_name} has a west destination {spec.dest}."
                )
            allowed = EAST_DESTINATIONS_BY_ORIGIN[spec.orig]
            if spec.dest not in allowed:
                raise RuntimeError(
                    f"{spec.vehicle_name} destination {spec.dest} is not allowed."
                )
        elif spec.traffic_group == "west_north":
            if spec.dest not in (
                WEST_NORTH_EASTBOUND_DESTINATION,
                WEST_NORTH_SOUTHBOUND_DESTINATION,
            ):
                raise RuntimeError(
                    f"{spec.vehicle_name} destination {spec.dest} is not "
                    "east_outer or west_south."
                )
        elif spec.traffic_group == "west_south":
            if spec.dest != WEST_SOUTH_DESTINATION:
                raise RuntimeError(
                    f"{spec.vehicle_name} destination is not west_outer."
                )
        else:
            raise RuntimeError(f"Unknown traffic group {spec.traffic_group!r}.")
        if spec.orig == spec.dest:
            raise RuntimeError(f"{spec.vehicle_name} has origin equal to destination.")

    if stats.vehicle_name_duplicate_count != 0:
        raise RuntimeError("Duplicate vehicle names.")
    if stats.participating_count != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("Not every vehicle is participating.")
    if stats.nonparticipating_count != 0:
        raise RuntimeError("Expected 0 nonparticipating vehicles.")
    if sum(stats.departure_count_by_timestep.values()) != len(specs):
        raise RuntimeError("Departure counts do not sum to the vehicle total.")
    if sum(stats.east_origin_counts.values()) != EAST_CONGESTION_VEHICLE_COUNT:
        raise RuntimeError("East origin counts do not sum to 300.")
    if sum(stats.east_od_counts.values()) != EAST_CONGESTION_VEHICLE_COUNT:
        raise RuntimeError("East OD counts do not sum to 300.")
    if sum(stats.east_planned_movement_counts.values()) != EAST_CONGESTION_VEHICLE_COUNT:
        raise RuntimeError("East planned movement counts do not sum to 300.")
    if (
        stats.west_north_eastbound_count + stats.west_north_southbound_count
        != WEST_NORTH_VEHICLE_COUNT
    ):
        raise RuntimeError("West-north destination split does not sum to 100.")
    if stats.west_north_eastbound_count != 62 or stats.west_north_southbound_count != 38:
        raise RuntimeError(
            "West-north seed-2 split changed: "
            f"eastbound={stats.west_north_eastbound_count}, "
            f"southbound={stats.west_north_southbound_count}."
        )
    # 0.7 and 0.3 are draw probabilities. The seed-2 counts are recorded as drawn.
    if abs(
        stats.west_north_eastbound_share
        - stats.west_north_eastbound_count / WEST_NORTH_VEHICLE_COUNT
    ) > 0:
        raise RuntimeError("West-north eastbound share does not match the count.")

    for index in range(1, len(specs)):
        if _origin_order_key(specs[index]) < _origin_order_key(specs[index - 1]):
            raise RuntimeError("VEHICLE_SPECS is not in departure then origin order.")

    specs_repeat, stats_repeat = _build_vehicle_specs_and_stats()
    if specs_repeat != specs or stats_repeat != stats:
        raise RuntimeError("VehicleSpec generation is not deterministic.")

    vot_first = generate_vehicle_vots(
        np.random.default_rng(VOT_SEED),
        len(specs),
    )
    unrelated_destination_rng = random.Random(EAST_DESTINATION_SEED)
    for _draw_index in range(1000):
        unrelated_destination_rng.random()
    vot_second = generate_vehicle_vots(
        np.random.default_rng(VOT_SEED),
        len(specs),
    )
    if vot_first != vot_second:
        raise RuntimeError("VOT sequence changed after a separate destination RNG was used.")
    vot_records = build_vehicle_vot_records(specs, vot_first)
    for record in vot_records:
        if record.declared_vot_per_second != record.true_vot_per_second:
            raise RuntimeError(
                f"declared VOT must equal true VOT for {record.vehicle_name}."
            )
        if record.participates_in_order_exchange is not True:
            raise RuntimeError(f"{record.vehicle_name} is not participating.")

    if EAST_DESTINATION_SEED == WEST_NORTH_DESTINATION_SEED:
        raise RuntimeError("The two destination seeds must differ.")
    if TRIAL_OUTPUT_DIR.name in KNOWN_OTHER_TRIAL_DIR_NAMES:
        raise RuntimeError("Output directory collides with an existing trial.")

    open_link = _FakeLink(vehicles=[], lanes=1, delta_per_lane=5.0, deltan=1.0)
    if entrance_space_available_from_link_state(open_link) is not True:
        raise RuntimeError("Empty link should have entrance space.")
    blocked_vehicle = _FakeVehicle(x=0.0)
    blocked_link = _FakeLink(
        vehicles=[blocked_vehicle],
        lanes=1,
        delta_per_lane=5.0,
        deltan=1.0,
    )
    if entrance_space_available_from_link_state(blocked_link) is not False:
        raise RuntimeError("Vehicle at x=0 should block the entrance.")
    clear_vehicle = _FakeVehicle(x=5.1)
    clear_link = _FakeLink(
        vehicles=[clear_vehicle],
        lanes=1,
        delta_per_lane=5.0,
        deltan=1.0,
    )
    if entrance_space_available_from_link_state(clear_link) is not True:
        raise RuntimeError("Vehicle beyond the entry gap should leave the entrance open.")

    sample_rows = [
        {
            "timestep": 0,
            "vehicle_count_on_link": 1,
            "minimum_vehicle_x": 10.0,
            "maximum_vehicle_x": 10.0,
            "entrance_blocked": False,
        },
        {
            "timestep": 4,
            "vehicle_count_on_link": 3,
            "minimum_vehicle_x": 0.0,
            "maximum_vehicle_x": 40.0,
            "entrance_blocked": True,
        },
    ]
    sample_summary = summarize_spillback_rows(sample_rows)
    if sample_summary["maximum_vehicle_count_on_spillback_link"] != 3:
        raise RuntimeError("Spillback summary max vehicle count is wrong.")
    if sample_summary["maximum_occupied_length_estimate"] != 40.0:
        raise RuntimeError("Spillback occupied-length summary is wrong.")
    if sample_summary["entrance_blocked_timestep_count"] != 1:
        raise RuntimeError("Spillback blocked-count summary is wrong.")
    if sample_summary["first_entrance_blocked_timestep"] != 4:
        raise RuntimeError("Spillback first blocked timestep is wrong.")
    if sample_summary["last_entrance_blocked_timestep"] != 4:
        raise RuntimeError("Spillback last blocked timestep is wrong.")

    world = build_world_and_network()
    if len(world.NODES) != 8:
        raise RuntimeError(f"Built world has {len(world.NODES)} nodes.")
    if len(world.LINKS) != 14:
        raise RuntimeError(f"Built world has {len(world.LINKS)} links.")
    capacity_out_values = []
    capacity_in_values = []
    for link in world.LINKS:
        if link.length != LINK_LENGTH_M:
            raise RuntimeError(f"{link.name} length is {link.length}, expected 200.")
        if link.number_of_lanes != 1:
            raise RuntimeError(f"{link.name} is not single-lane.")
        capacity_out_values.append(link.capacity_out)
        capacity_in_values.append(link.capacity_in)
    if len(set(capacity_out_values)) != 1 or len(set(capacity_in_values)) != 1:
        raise RuntimeError("Links do not share one capacity setting.")
    spillback_link = world.get_link(SPILLBACK_LINK_NAME)
    reverse_link = world.get_link(SPILLBACK_REVERSE_LINK_NAME)
    if spillback_link.start_node.name != WEST_INTERSECTION_NODE:
        raise RuntimeError("Spillback link does not start at west_intersection.")
    if spillback_link.end_node.name != EAST_INTERSECTION_NODE:
        raise RuntimeError("Spillback link does not end at east_intersection.")
    if reverse_link.start_node.name != EAST_INTERSECTION_NODE:
        raise RuntimeError("Reverse connector does not start at east_intersection.")
    _assert_link_user_functions_are_none(world, "built world")
    if world.user_function is not None:
        raise RuntimeError("World.user_function must stay unset.")
    copied_world = world.copy()
    if len(copied_world.NODES) != 8 or len(copied_world.LINKS) != 14:
        raise RuntimeError("Copied world does not keep 8 nodes and 14 links.")
    _assert_link_user_functions_are_none(copied_world, "copied world")
    if copied_world.user_function is not None:
        raise RuntimeError("Copied World.user_function must stay unset.")
    _assert_spillback_observer_is_not_a_world_callback(world)
    _assert_spillback_observer_is_not_a_world_callback(copied_world)
    _assert_observation_wrapper_calls_driver_once()
    try:
        install_real_world_spillback_observation(world)
        if Link.update is not update_link_and_record_real_world_spillback:
            raise RuntimeError("Spillback observation is not on Link.update.")
        _assert_link_user_functions_are_none(
            world,
            "built world after installing the class hook",
        )
        _assert_spillback_observer_is_not_a_world_callback(world)
    finally:
        restore_real_world_spillback_observation()
    if Link.update is update_link_and_record_real_world_spillback:
        raise RuntimeError("Spillback Link.update hook was left installed.")
    if tvt_mp_driver_module.run_tvt_mp_driver is run_real_world_tvt_mp_driver_once:
        raise RuntimeError("Spillback driver wrapper was left installed.")
    for node_name in TVT_MP_NODE_NAMES:
        node = world.get_node(node_name)
        if node.order_control_type != "time_value":
            raise RuntimeError(f"{node_name} is not TVT-MP.")
        if node.order_control_clearance_timesteps != 1:
            raise RuntimeError(f"{node_name} clearance is not 1.")
        if node.order_control_eligible is not True:
            raise RuntimeError(f"{node_name} is not order-control eligible.")
    for node in world.NODES:
        if node.name in TVT_MP_NODE_NAMES:
            continue
        if node.order_control_type != "none":
            raise RuntimeError(f"{node.name} should stay on standard control.")
    if len(SPILLBACK_TIMESTEP_ROWS) != 0:
        raise RuntimeError("Static validation must not record spillback timesteps.")
    if WORLD_COPY_RECURSION_LIMIT != 3000:
        raise RuntimeError("WORLD_COPY_RECURSION_LIMIT must be 3000.")
    if isinstance(WORLD_COPY_RECURSION_LIMIT, bool) or not isinstance(
        WORLD_COPY_RECURSION_LIMIT, int
    ):
        raise RuntimeError("WORLD_COPY_RECURSION_LIMIT must be a non-bool int.")
    _assert_main_recursion_limit_try_finally()


class _FakeVehicle:
    def __init__(self, x: float) -> None:
        self.x = x
        self.name = "fake"


class _FakeWorld:
    def __init__(self, deltan: float) -> None:
        self.DELTAN = deltan


class _FakeLink:
    def __init__(self, vehicles, lanes: int, delta_per_lane: float, deltan: float) -> None:
        self.vehicles = vehicles
        self.number_of_lanes = lanes
        self.delta_per_lane = delta_per_lane
        self.W = _FakeWorld(deltan)


def generate_vehicle_vots(rng: np.random.Generator, count: int) -> list[float]:
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    return [float(value) for value in samples]


def build_vehicle_vot_records(
    specs: tuple[VehicleSpec, ...],
    vot_values: list[float],
) -> list[VehicleVotRecord]:
    records: list[VehicleVotRecord] = []
    for spec, vot in zip(specs, vot_values):
        if spec.participating:
            declared = vot
        else:
            declared = None
        records.append(
            VehicleVotRecord(
                vehicle_name=spec.vehicle_name,
                origin=spec.orig,
                destination=spec.dest,
                departure_timestep=spec.departure_timestep,
                participates_in_order_exchange=spec.participating,
                true_vot_per_second=vot,
                declared_vot_per_second=declared,
            )
        )
    return records


def ensure_trial_parent_directories() -> None:
    TRIAL_PARENT.mkdir(parents=True, exist_ok=True)


def refuse_existing_trial_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Remove or rename it manually before re-running; this script does "
            "not delete or overwrite existing trial output."
        )


def build_world_and_network() -> World:
    world = World(
        name=WORLD_DISPLAY_NAME,
        deltan=1,
        reaction_time=1,
        tmax=INTERNAL_TSIZE,
        random_seed=TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
    )
    for node_name in NODE_NAMES:
        x_coord, y_coord = NODE_COORDINATES[node_name]
        world.addNode(node_name, x_coord, y_coord)

    for link_name, upstream, downstream in LINK_SPECS:
        world.addLink(
            link_name,
            upstream,
            downstream,
            length=LINK_LENGTH_M,
            free_flow_speed=FREE_FLOW_SPEED_M_PER_S,
            number_of_lanes=NUMBER_OF_LANES,
        )

    world.infer_order_control_eligible_nodes()
    world.set_order_control_for_nodes(
        list(TVT_MP_NODE_NAMES),
        order_control_type="time_value",
        transaction_case=None,
    )
    world.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)

    for node_name in TVT_MP_NODE_NAMES:
        node = world.get_node(node_name)
        if node.order_control_type != "time_value":
            raise RuntimeError(f"{node_name} was not set to time_value.")
        if node.order_control_clearance_timesteps != CLEARANCE_TIMESTEPS:
            raise RuntimeError(
                f"{node_name} clearance is {node.order_control_clearance_timesteps!r}."
            )

    world.order_control_tvt_evaluation_end_timestep = EVALUATION_END_TIMESTEP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    return world


def add_vehicles_to_world(
    world: World,
    specs: tuple[VehicleSpec, ...],
    vot_records: list[VehicleVotRecord],
) -> None:
    for spec, vot_record in zip(specs, vot_records):
        kwargs = {
            "name": spec.vehicle_name,
            "departure_time_is_time_step": 1,
            "vot_true": vot_record.true_vot_per_second,
            "participates_in_order_exchange": spec.participating,
        }
        if spec.participating:
            kwargs["vot_declared"] = vot_record.declared_vot_per_second
        else:
            kwargs["vot_declared"] = None
        world.addVehicle(
            spec.orig,
            spec.dest,
            spec.departure_timestep,
            **kwargs,
        )


def verify_evaluation_end(world: World) -> dict:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )
    if EXPECTED_DRIVER_CALL_COUNT != 600:
        raise RuntimeError("Driver-call expectation is not 600.")

    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    for field_name in (
        "evaluation_end_unobserved_finalized_timestep",
        "trade_ex_post_evaluation_finalized_timestep",
        "individual_ex_post_evaluation_finalized_timestep",
    ):
        actual = getattr(registry, field_name)
        if actual != EVALUATION_END_TIMESTEP:
            raise RuntimeError(
                f"Registry {field_name} expected {EVALUATION_END_TIMESTEP}, "
                f"got {actual!r}."
            )
    return {
        "world_t": world.T,
        "world_t_ok": True,
    }


def collect_trip_completion(world: World) -> dict:
    """
    Record unfinished trips. This trial does not require all 450 vehicles to
    finish before T=599.
    """
    completed_names = []
    incomplete_names = []
    for vehicle in world.VEHICLES.values():
        if vehicle.state == "end":
            completed_names.append(vehicle.name)
        else:
            incomplete_names.append(vehicle.name)
    completed_names.sort()
    incomplete_names.sort()

    analyzer_completed = int(world.analyzer.trip_completed)
    if analyzer_completed != len(completed_names):
        raise RuntimeError(
            "analyzer.trip_completed "
            f"{analyzer_completed} does not match vehicles in state 'end' "
            f"({len(completed_names)})."
        )

    link_vehicle_counts = {}
    for link in world.LINKS:
        link_vehicle_counts[link.name] = len(link.vehicles)
    spillback_link = world.get_link(SPILLBACK_LINK_NAME)
    return {
        "completed_trip_count": len(completed_names),
        "incomplete_vehicle_count": len(incomplete_names),
        "incomplete_vehicle_names": incomplete_names,
        "link_vehicle_counts_at_evaluation_end": dict(sorted(link_vehicle_counts.items())),
        "spillback_link_vehicle_count_at_evaluation_end": len(spillback_link.vehicles),
    }


def verify_spillback_observation(rows: list[dict], summary: dict) -> None:
    if len(rows) != EXPECTED_DRIVER_CALL_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_DRIVER_CALL_COUNT} spillback rows, got {len(rows)}."
        )
    for index, row in enumerate(rows):
        if row["timestep"] != index:
            raise RuntimeError(
                f"Spillback row {index} has timestep {row['timestep']!r}."
            )
        if row["entrance_blocked"] is not (not row["entrance_space_available"]):
            raise RuntimeError(
                f"T={row['timestep']}: entrance flags contradict each other."
            )
        for field_name in SPILLBACK_CSV_FIELDS:
            if field_name not in row:
                raise RuntimeError(f"Spillback row is missing {field_name}.")
    recomputed = summarize_spillback_rows(rows)
    if recomputed != summary:
        raise RuntimeError(
            "Spillback summary does not match the timestep rows: "
            f"{summary!r} vs {recomputed!r}."
        )


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
        "east_destination_seed",
        "west_north_destination_seed",
        "vot_seed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in vot_records:
            declared = record.declared_vot_per_second
            writer.writerow(
                {
                    "vehicle_name": record.vehicle_name,
                    "origin": record.origin,
                    "destination": record.destination,
                    "departure_timestep": record.departure_timestep,
                    "participates_in_order_exchange": record.participates_in_order_exchange,
                    "true_vot_per_second": record.true_vot_per_second,
                    "declared_vot_per_second": "" if declared is None else declared,
                    "traffic_seed": TRAFFIC_SEED,
                    "east_destination_seed": EAST_DESTINATION_SEED,
                    "west_north_destination_seed": WEST_NORTH_DESTINATION_SEED,
                    "vot_seed": VOT_SEED,
                }
            )


def write_spillback_csv(path: Path, rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SPILLBACK_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_manifest_json(
    path: Path,
    timing: TimingRecord,
    world: World,
    generated_files: list[str],
    spillback_summary: dict,
    completion: dict,
    original_python_recursion_limit: int,
) -> None:
    trial_fields = manifest_counts_from_specs(GENERATION_STATS)
    manifest = {
        "schema_note": (
            "Two-cross downstream spillback trial manifest only; "
            "not a formal experiment schema."
        ),
        "run_type": "trial",
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
        "vot_arithmetic_mean_per_second": VOT_ARITHMETIC_MEAN,
        "vot_arithmetic_stddev_per_second": VOT_ARITHMETIC_STDDEV,
        "vot_log_space_mu": VOT_LOG_MU,
        "vot_log_space_sigma": VOT_LOG_SIGMA,
        "decision_window_contract": DECISION_WINDOW_CONTRACT,
        "free_flow_speed_m_per_s": FREE_FLOW_SPEED_M_PER_S,
        "node_names": list(NODE_NAMES),
        "link_specs": [
            {"name": name, "upstream": upstream, "downstream": downstream}
            for name, upstream, downstream in LINK_SPECS
        ],
        "capacity_settings": (
            "UXsim defaults (capacity_in/out and Node flow_capacity not set); "
            "same setting on every link"
        ),
        "timing_seconds": {
            "world_build": timing.world_build_s,
            "finalize_scenario": timing.finalize_s,
            "exec_simulation": timing.exec_simulation_s,
            "research_output_build": timing.research_build_s,
            "csv_write": timing.csv_write_s,
            "trial_auxiliary_write": timing.trial_aux_write_s,
            "script_total": timing.script_total_s,
        },
        "world_t_after_execution": world.T,
        "expected_tvt_mp_driver_calls": EXPECTED_DRIVER_CALL_COUNT,
        "completed_trip_count": completion["completed_trip_count"],
        "incomplete_vehicle_count": completion["incomplete_vehicle_count"],
        "incomplete_vehicle_names": completion["incomplete_vehicle_names"],
        "link_vehicle_counts_at_evaluation_end": completion[
            "link_vehicle_counts_at_evaluation_end"
        ],
        "spillback_link_vehicle_count_at_evaluation_end": completion[
            "spillback_link_vehicle_count_at_evaluation_end"
        ],
        "spillback_summary": spillback_summary,
        "generated_files": generated_files,
        "world_copy_recursion_limit_during_trial": WORLD_COPY_RECURSION_LIMIT,
        "original_python_recursion_limit": original_python_recursion_limit,
        "recursion_limit_restored_after_trial": True,
        "world_copy_recursion_limit_note": (
            "Execution environment setting for World.copy with long "
            "single-lane queues; not a traffic-model parameter."
        ),
    }
    manifest.update(trial_fields)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(
    path: Path,
    timing: TimingRecord,
    world: World,
    bundle,
    completion: dict,
    spillback_summary: dict,
    generated_files: list[str],
    original_python_recursion_limit: int,
) -> None:
    stats = GENERATION_STATS
    scenario_row = bundle.scenario[0]
    lines = [
        "TVT-MP two-cross downstream spillback trial",
        "=" * 50,
        "Completed run: yes",
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Network:",
        "  8 Node / 14 Link",
        "  2 TVT-MP cross intersections: west_intersection, east_intersection",
        "  both intersections use TVT-MP and clearance 1 timestep",
        "  all links are 200 m, single lane, and the same UXsim capacity setting",
        f"  connector: {SPILLBACK_LINK_NAME}",
        f"  reverse connector: {SPILLBACK_REVERSE_LINK_NAME}",
        "",
        "Vehicles:",
        "  total 450",
        "  east congestion traffic 300",
        "  west-north inflow 100",
        "  west-south inflow 50",
        "  participating 450, nonparticipating 0",
        "  declared VOT equals true VOT",
        f"  west-north eastbound (destination east_outer): "
        f"{stats.west_north_eastbound_count} "
        f"(share {stats.west_north_eastbound_share})",
        f"  west-north southbound (destination west_south): "
        f"{stats.west_north_southbound_count} "
        f"(share {stats.west_north_southbound_share})",
        "  west-north split is the seed-2 draw, not a fixed 70/30 quota",
        "  west-south destination is west_outer for every vehicle",
        f"  east OD counts: {stats.east_od_counts}",
        f"  east destination counts: {stats.east_destination_counts}",
        f"  east planned movements: {stats.east_planned_movement_counts}",
        f"  all OD counts: {stats.od_counts}",
        f"  same-OD pairs: {stats.same_od_pair_count}",
        f"  vehicles sharing an OD with at least one other vehicle: "
        f"{stats.same_od_vehicle_count}",
        "",
        "Routing:",
        "  no fixed route",
        "  OD only",
        "  UXsim dynamic route choice",
        "  realized movements and right-of-entry temporary skips are left to a later diagnostic",
        "",
        "Time:",
        "  evaluation T=0..599",
        "  baseline horizon 30",
        "  candidate visit limit 10",
        "  internal TSIZE 630",
        "  configured driver calls 600",
        "  a short baseline horizon may leave some baseline information unresolved;",
        "  this script records that through the existing TVT-MP outputs and does not abort for it",
        "",
        "Spillback link observation (real World only; after that link's "
        "Link.update capacity refill, before Node.transfer):",
        f"  link: {SPILLBACK_LINK_NAME}",
        f"  maximum vehicle count: "
        f"{spillback_summary['maximum_vehicle_count_on_spillback_link']}",
        f"  maximum occupied length estimate (max_x - min_x): "
        f"{spillback_summary['maximum_occupied_length_estimate']}",
        f"  entrance-blocked timestep count: "
        f"{spillback_summary['entrance_blocked_timestep_count']}",
        f"  first entrance-blocked timestep: "
        f"{spillback_summary['first_entrance_blocked_timestep']}",
        f"  last entrance-blocked timestep: "
        f"{spillback_summary['last_entrance_blocked_timestep']}",
        f"  vehicles still on the spillback link after evaluation: "
        f"{completion['spillback_link_vehicle_count_at_evaluation_end']}",
        "",
        "Execution environment (World.copy only; not traffic-model parameters):",
        f"  world_copy_recursion_limit_during_trial: {WORLD_COPY_RECURSION_LIMIT}",
        f"  original_python_recursion_limit: {original_python_recursion_limit}",
        "  recursion_limit_restored_after_trial: true",
        "",
        "Trips:",
        f"  completed trip count: {completion['completed_trip_count']} / {stats.total_vehicle_count}",
        f"  incomplete vehicle count: {completion['incomplete_vehicle_count']}",
        "  all 450 vehicles are not required to finish",
        "  incomplete vehicle names:",
    ]
    if len(completion["incomplete_vehicle_names"]) == 0:
        lines.append("    (none)")
    else:
        for vehicle_name in completion["incomplete_vehicle_names"]:
            lines.append(f"    {vehicle_name}")
    lines.extend(
        [
            "  vehicles on each link at evaluation end:",
        ]
    )
    for link_name, vehicle_count in completion[
        "link_vehicle_counts_at_evaluation_end"
    ].items():
        lines.append(f"    {link_name}: {vehicle_count}")
    lines.extend(
        [
            "",
            "Timing (seconds):",
            f"  world_build: {timing.world_build_s:.4f}",
            f"  finalize_scenario: {timing.finalize_s:.4f}",
            f"  exec_simulation: {timing.exec_simulation_s:.4f}",
            f"  research_output_build: {timing.research_build_s:.4f}",
            f"  csv_write: {timing.csv_write_s:.4f}",
            f"  trial_auxiliary_write: {timing.trial_aux_write_s:.4f}",
            f"  script_total: {timing.script_total_s:.4f}",
            "",
            f"Transaction count: {scenario_row.transaction_count}",
            f"Scenario name in research output: {scenario_row.scenario_name}",
            "",
            "Generated files:",
        ]
    )
    for name in generated_files:
        lines.append(f"  - {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_research_output(bundle, output_dir: Path) -> None:
    if bundle.scenario[0].scenario_name != SCENARIO_NAME:
        raise RuntimeError(
            "Research output scenario name "
            f"{bundle.scenario[0].scenario_name!r} does not match {SCENARIO_NAME!r}."
        )
    if output_dir != TRIAL_OUTPUT_DIR:
        raise RuntimeError("Research output directory is not this trial directory.")
    for name in RESEARCH_CSV_NAMES:
        path = output_dir / name
        if not path.is_file():
            raise RuntimeError(f"Expected research CSV missing: {path}")


def print_console_summary(
    completion: dict,
    spillback_summary: dict,
    timing: TimingRecord,
    bundle,
    output_dir: Path,
) -> None:
    stats = GENERATION_STATS
    print()
    print("=== TVT-MP two-cross downstream spillback trial ===")
    print()
    print("Network: 8 nodes, 14 links, 2 TVT-MP intersections")
    print(
        f"Vehicles: {stats.total_vehicle_count} "
        f"(east {EAST_CONGESTION_VEHICLE_COUNT}, "
        f"west-north {WEST_NORTH_VEHICLE_COUNT}, "
        f"west-south {WEST_SOUTH_VEHICLE_COUNT})"
    )
    print(
        "West-north draw: "
        f"eastbound {stats.west_north_eastbound_count}, "
        f"southbound {stats.west_north_southbound_count}"
    )
    print(f"East OD: {stats.east_od_counts}")
    print(f"World.T = {EXPECTED_WORLD_T_AFTER_SIM}")
    print(
        f"Completed trips: {completion['completed_trip_count']} / "
        f"{stats.total_vehicle_count}"
    )
    print(
        "Spillback max vehicles: "
        f"{spillback_summary['maximum_vehicle_count_on_spillback_link']}; "
        "entrance blocked timesteps: "
        f"{spillback_summary['entrance_blocked_timestep_count']}"
    )
    print(f"Transactions: {bundle.scenario[0].transaction_count}")
    print(f"Timing total (s): {timing.script_total_s:.3f}")
    print(f"Output directory: {output_dir}")
    print()


def main() -> int:
    script_start = time.perf_counter()
    timing = TimingRecord()
    SPILLBACK_TIMESTEP_ROWS.clear()
    original_python_recursion_limit = sys.getrecursionlimit()
    try:
        if original_python_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)

        validate_static_contract()
        ensure_trial_parent_directories()
        refuse_existing_trial_output_directory()

        vot_rng = np.random.default_rng(VOT_SEED)
        vot_values = generate_vehicle_vots(vot_rng, len(VEHICLE_SPECS))
        vot_records = build_vehicle_vot_records(VEHICLE_SPECS, vot_values)

        t0 = time.perf_counter()
        world = build_world_and_network()
        add_vehicles_to_world(world, VEHICLE_SPECS, vot_records)
        timing.world_build_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        world.finalize_scenario()
        timing.finalize_s = time.perf_counter() - t0
        if world.TSIZE != INTERNAL_TSIZE:
            raise RuntimeError(
                f"Expected TSIZE=={INTERNAL_TSIZE} after finalize, got {world.TSIZE}."
            )

        t0 = time.perf_counter()
        install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            restore_real_world_spillback_observation()
        timing.exec_simulation_s = time.perf_counter() - t0

        eval_ok = verify_evaluation_end(world)
        if eval_ok["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")

        completion = collect_trip_completion(world)
        spillback_summary = summarize_spillback_rows(SPILLBACK_TIMESTEP_ROWS)
        verify_spillback_observation(SPILLBACK_TIMESTEP_ROWS, spillback_summary)

        t0 = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        timing.research_build_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        try:
            write_tvt_mp_research_output_csv(
                bundle,
                TRIAL_OUTPUT_DIR,
                overwrite=False,
            )
        except FileExistsError:
            raise
        timing.csv_write_s = time.perf_counter() - t0
        verify_research_output(bundle, TRIAL_OUTPUT_DIR)

        generated_files = list(RESEARCH_CSV_NAMES) + [
            "vehicle_vot.csv",
            SPILLBACK_CSV_NAME,
            "manifest.json",
            "run_summary.txt",
        ]

        t0 = time.perf_counter()
        write_vehicle_vot_csv(TRIAL_OUTPUT_DIR / "vehicle_vot.csv", vot_records)
        write_spillback_csv(
            TRIAL_OUTPUT_DIR / SPILLBACK_CSV_NAME,
            SPILLBACK_TIMESTEP_ROWS,
        )
        timing.trial_aux_write_s = time.perf_counter() - t0
        timing.script_total_s = time.perf_counter() - script_start

        write_manifest_json(
            TRIAL_OUTPUT_DIR / "manifest.json",
            timing,
            world,
            generated_files,
            spillback_summary,
            completion,
            original_python_recursion_limit,
        )
        write_run_summary_txt(
            TRIAL_OUTPUT_DIR / "run_summary.txt",
            timing,
            world,
            bundle,
            completion,
            spillback_summary,
            generated_files,
            original_python_recursion_limit,
        )
        print_console_summary(
            completion,
            spillback_summary,
            timing,
            bundle,
            TRIAL_OUTPUT_DIR,
        )
        return 0
    finally:
        sys.setrecursionlimit(original_python_recursion_limit)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
            recursion_limit_before = sys.getrecursionlimit()
            validate_static_contract()
            if sys.getrecursionlimit() != recursion_limit_before:
                raise RuntimeError(
                    "Static validation changed sys.getrecursionlimit(): "
                    f"before={recursion_limit_before}, "
                    f"after={sys.getrecursionlimit()}."
                )
            source = SCRIPT_PATH.read_text(encoding="utf-8")
            ast.parse(source)
            compile(source, str(SCRIPT_PATH), "exec")
            print("Static contract validation passed.", file=sys.stderr)
            print(
                "west_north_eastbound="
                f"{GENERATION_STATS.west_north_eastbound_count} "
                "west_north_southbound="
                f"{GENERATION_STATS.west_north_southbound_count}",
                file=sys.stderr,
            )
            print(
                f"east_od_counts={GENERATION_STATS.east_od_counts}",
                file=sys.stderr,
            )
            print(
                "east_movements="
                f"{GENERATION_STATS.east_planned_movement_counts}",
                file=sys.stderr,
            )
            raise SystemExit(0)
        raise SystemExit(main())
    except FileExistsError as exc:
        print(f"FileExistsError: {exc}", file=sys.stderr)
        raise SystemExit(1)
