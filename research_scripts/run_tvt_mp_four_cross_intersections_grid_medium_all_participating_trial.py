"""
TVT-MP trial: four cross intersections on a 2x2 grid with eight perimeter OD nodes.

All 600 vehicles participate in order exchange. Routes are chosen by UXsim from
fixed origin-destination pairs (no specified_route). This script does not modify
production code or existing trials.
"""

from __future__ import annotations

import ast
import csv
import json
import math
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
# 1. Scenario and evaluation constants
# ---------------------------------------------------------------------------

SCENARIO_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
    "600_vehicle_eval_900_timestep_trial"
)
WORLD_DISPLAY_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
    "600_vehicle_eval_900"
)

LEGACY_500_VEHICLE_SCENARIO_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_all_participating_trial"
)
LEGACY_500_VEHICLE_TRIAL_OUTPUT_DIR_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_all_participating_seed_1_initial"
)

TRAFFIC_SEED = 0
VOT_SEED = 1

VOT_ARITHMETIC_MEAN = 1.0
VOT_ARITHMETIC_STDDEV = 3.0
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

EVALUATION_START_TIMESTEP = 0
EVALUATION_END_TIMESTEP = 899
INTERNAL_TSIZE = 930
EXPECTED_WORLD_T_AFTER_SIM = EVALUATION_END_TIMESTEP + 1
EXPECTED_DRIVER_CALL_COUNT = (
    EVALUATION_END_TIMESTEP - EVALUATION_START_TIMESTEP + 1
)

BASELINE_HORIZON_STEPS = 30
MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1
WORLD_COPY_RECURSION_LIMIT = 3000

FREE_FLOW_SPEED_M_PER_S = 60000 / 3600
LINK_LENGTH_M = 200
NUMBER_OF_LANES = 1
CAPACITY_SETTINGS_UNIFORM = True
ROUTE_ASSIGNMENT_MODE = "uxsim_dynamic_route_choice_from_od"
SPECIFIED_ROUTE_USED = False

DECISION_WINDOW_CONTRACT = (
    "0 < baseline_arrival_timestep - T <= 6 "
    "(code constant; not set in script)"
)

# ---------------------------------------------------------------------------
# 2. Network nodes and links (12 nodes, 24 directed links)
# ---------------------------------------------------------------------------

NORTHWEST_INTERSECTION = "northwest_intersection"
NORTHEAST_INTERSECTION = "northeast_intersection"
SOUTHWEST_INTERSECTION = "southwest_intersection"
SOUTHEAST_INTERSECTION = "southeast_intersection"

TVT_MP_NODE_NAMES: tuple[str, ...] = (
    NORTHWEST_INTERSECTION,
    NORTHEAST_INTERSECTION,
    SOUTHWEST_INTERSECTION,
    SOUTHEAST_INTERSECTION,
)

PERIMETER_OD_NODE_NAMES: tuple[str, ...] = (
    "north_west_od",
    "north_east_od",
    "west_north_od",
    "west_south_od",
    "east_north_od",
    "east_south_od",
    "south_west_od",
    "south_east_od",
)

NODE_NAMES: tuple[str, ...] = TVT_MP_NODE_NAMES + PERIMETER_OD_NODE_NAMES
NODE_COUNT = len(NODE_NAMES)

NODE_COORDINATES: dict[str, tuple[float, float]] = {
    NORTHWEST_INTERSECTION: (0.0, 1.0),
    NORTHEAST_INTERSECTION: (1.0, 1.0),
    SOUTHWEST_INTERSECTION: (0.0, 0.0),
    SOUTHEAST_INTERSECTION: (1.0, 0.0),
    "north_west_od": (0.0, 2.0),
    "north_east_od": (1.0, 2.0),
    "west_north_od": (-1.0, 1.0),
    "west_south_od": (-1.0, 0.0),
    "east_north_od": (2.0, 1.0),
    "east_south_od": (2.0, 0.0),
    "south_west_od": (0.0, -1.0),
    "south_east_od": (1.0, -1.0),
}

INTERNAL_LINK_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "northwest_intersection_to_northeast_intersection",
        NORTHWEST_INTERSECTION,
        NORTHEAST_INTERSECTION,
    ),
    (
        "northeast_intersection_to_northwest_intersection",
        NORTHEAST_INTERSECTION,
        NORTHWEST_INTERSECTION,
    ),
    (
        "northwest_intersection_to_southwest_intersection",
        NORTHWEST_INTERSECTION,
        SOUTHWEST_INTERSECTION,
    ),
    (
        "southwest_intersection_to_northwest_intersection",
        SOUTHWEST_INTERSECTION,
        NORTHWEST_INTERSECTION,
    ),
    (
        "northeast_intersection_to_southeast_intersection",
        NORTHEAST_INTERSECTION,
        SOUTHEAST_INTERSECTION,
    ),
    (
        "southeast_intersection_to_northeast_intersection",
        SOUTHEAST_INTERSECTION,
        NORTHEAST_INTERSECTION,
    ),
    (
        "southwest_intersection_to_southeast_intersection",
        SOUTHWEST_INTERSECTION,
        SOUTHEAST_INTERSECTION,
    ),
    (
        "southeast_intersection_to_southwest_intersection",
        SOUTHEAST_INTERSECTION,
        SOUTHWEST_INTERSECTION,
    ),
)

PERIMETER_LINK_SPECS: tuple[tuple[str, str, str], ...] = (
    ("north_west_od_to_northwest_intersection", "north_west_od", NORTHWEST_INTERSECTION),
    ("northwest_intersection_to_north_west_od", NORTHWEST_INTERSECTION, "north_west_od"),
    ("north_east_od_to_northeast_intersection", "north_east_od", NORTHEAST_INTERSECTION),
    ("northeast_intersection_to_north_east_od", NORTHEAST_INTERSECTION, "north_east_od"),
    ("west_north_od_to_northwest_intersection", "west_north_od", NORTHWEST_INTERSECTION),
    ("northwest_intersection_to_west_north_od", NORTHWEST_INTERSECTION, "west_north_od"),
    ("west_south_od_to_southwest_intersection", "west_south_od", SOUTHWEST_INTERSECTION),
    ("southwest_intersection_to_west_south_od", SOUTHWEST_INTERSECTION, "west_south_od"),
    ("east_north_od_to_northeast_intersection", "east_north_od", NORTHEAST_INTERSECTION),
    ("northeast_intersection_to_east_north_od", NORTHEAST_INTERSECTION, "east_north_od"),
    ("east_south_od_to_southeast_intersection", "east_south_od", SOUTHEAST_INTERSECTION),
    ("southeast_intersection_to_east_south_od", SOUTHEAST_INTERSECTION, "east_south_od"),
    ("south_west_od_to_southwest_intersection", "south_west_od", SOUTHWEST_INTERSECTION),
    ("southwest_intersection_to_south_west_od", SOUTHWEST_INTERSECTION, "south_west_od"),
    ("south_east_od_to_southeast_intersection", "south_east_od", SOUTHEAST_INTERSECTION),
    ("southeast_intersection_to_south_east_od", SOUTHEAST_INTERSECTION, "south_east_od"),
)

LINK_SPECS: tuple[tuple[str, str, str], ...] = (
    INTERNAL_LINK_SPECS + PERIMETER_LINK_SPECS
)
LINK_COUNT = len(LINK_SPECS)

SPILLBACK_LINK_NAMES: tuple[str, ...] = tuple(
    name for name, _upstream, _downstream in INTERNAL_LINK_SPECS
)
SPILLBACK_LINK_NAME_SET = frozenset(SPILLBACK_LINK_NAMES)

SPILLBACK_SUMMARY_CSV_NAME = "internal_spillback_link_summary.csv"
SPILLBACK_SUMMARY_FIELDS = (
    "link_name",
    "maximum_vehicle_count",
    "entrance_blocked_timestep_count",
    "first_entrance_blocked_timestep",
    "last_entrance_blocked_timestep",
    "vehicle_count_at_evaluation_end",
)

# ---------------------------------------------------------------------------
# 3. Demand: ten primary ODs, base 500 + pulse 100
# ---------------------------------------------------------------------------

BASE_DEPARTURE_START_TIMESTEP = 20
BASE_DEPARTURE_END_TIMESTEP = 118
BASE_DEPARTURE_INTERVAL_TIMESTEPS = 2
BASE_VEHICLES_PER_OD = 50

PULSE_DEPARTURE_START_TIMESTEP = 160
PULSE_DEPARTURE_END_TIMESTEP = 258
PULSE_DEPARTURE_INTERVAL_TIMESTEPS = 2
PULSE_VEHICLES_PER_OD = 50

# (origin, destination, short abbrev for vehicle names)
ORIGINAL_PRIMARY_OD_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("west_north_od", "east_north_od", "wn_en"),
    ("east_south_od", "west_south_od", "es_ws"),
    ("north_west_od", "south_west_od", "nw_sw"),
    ("south_east_od", "north_east_od", "se_ne"),
    ("west_north_od", "south_east_od", "wn_se"),
    ("north_east_od", "west_south_od", "ne_ws"),
    ("east_north_od", "south_west_od", "en_sw"),
    ("south_west_od", "east_south_od", "sw_es"),
)

ADDED_PRIMARY_OD_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("north_east_od", "west_north_od", "ne_wn"),
    ("south_west_od", "north_west_od", "sw_nw"),
)

ADDED_PRIMARY_OD_INTERNAL_LINK_BY_ABBREV: dict[str, str] = {
    "ne_wn": "northeast_intersection_to_northwest_intersection",
    "sw_nw": "southwest_intersection_to_northwest_intersection",
}

PRIMARY_OD_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ORIGINAL_PRIMARY_OD_DEFINITIONS + ADDED_PRIMARY_OD_DEFINITIONS
)

PULSE_OD_ABBREVS: frozenset[str] = frozenset({"wn_en", "nw_sw"})

BASE_OD_VEHICLE_COUNT = BASE_VEHICLES_PER_OD * len(PRIMARY_OD_DEFINITIONS)
PULSE_OD_VEHICLE_COUNT = PULSE_VEHICLES_PER_OD * len(PULSE_OD_ABBREVS)
EXPECTED_TOTAL_VEHICLE_COUNT = BASE_OD_VEHICLE_COUNT + PULSE_OD_VEHICLE_COUNT

# ---------------------------------------------------------------------------
# 4. Paths and auxiliary file names
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
    "600_vehicle_eval_900_timestep_seed_1_initial"
)
TRIAL_OUTPUT_DIR = TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)

COLLIDING_TRIAL_OUTPUT_DIR_NAMES: tuple[str, ...] = (
    LEGACY_500_VEHICLE_TRIAL_OUTPUT_DIR_NAME,
    "tvt_mp_two_cross_intersections_downstream_spillback_seed_1_initial",
    "tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_initial",
    "tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_nonparticipation_seed_3_initial",
    "tvt_mp_two_cross_intersections_downstream_spillback_late_pulse_seed_1_initial",
)

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Filled only during simulation when spillback observation is installed.
SPILLBACK_TIMESTEP_ROWS: list[dict] = []


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool
    traffic_group: str
    od_abbrev: str
    demand_kind: str


@dataclass(frozen=True)
class VehicleGenerationStats:
    total_vehicle_count: int
    participating_count: int
    base_vehicle_count: int
    pulse_vehicle_count: int
    od_counts: dict[str, int]
    od_base_counts: dict[str, int]
    od_pulse_counts: dict[str, int]
    departure_count_by_timestep: dict[int, int]
    vehicle_name_duplicate_count: int


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


class _SpillbackObservationGate:
    real_world: World | None = None
    enabled: bool = False
    original_link_update: object = None
    original_run_tvt_mp_driver: object = None


_SPILLBACK_OBSERVATION_GATE = _SpillbackObservationGate()


def _od_key(origin: str, destination: str) -> str:
    return f"{origin}->{destination}"


def _has_directed_link(upstream: str, downstream: str) -> bool:
    for _link_name, link_upstream, link_downstream in LINK_SPECS:
        if link_upstream == upstream and link_downstream == downstream:
            return True
    return False


def _internal_link_endpoints(link_name: str) -> tuple[str, str]:
    for name, upstream, downstream in INTERNAL_LINK_SPECS:
        if name == link_name:
            return upstream, downstream
    raise RuntimeError(f"Unknown internal link name: {link_name}")


def assert_added_primary_od_network_paths() -> None:
    """Static contract: added ODs can reach destination via the target internal link."""
    for origin, destination, abbrev in ADDED_PRIMARY_OD_DEFINITIONS:
        internal_link_name = ADDED_PRIMARY_OD_INTERNAL_LINK_BY_ABBREV[abbrev]
        internal_upstream, internal_downstream = _internal_link_endpoints(
            internal_link_name
        )
        if abbrev == "ne_wn":
            perimeter_upstream = NORTHEAST_INTERSECTION
            perimeter_downstream = NORTHWEST_INTERSECTION
        elif abbrev == "sw_nw":
            perimeter_upstream = SOUTHWEST_INTERSECTION
            perimeter_downstream = NORTHWEST_INTERSECTION
        else:
            raise RuntimeError(f"Unhandled added OD abbrev: {abbrev}")
        if internal_upstream != perimeter_upstream or internal_downstream != perimeter_downstream:
            raise RuntimeError(
                f"Internal link {internal_link_name} does not match expected "
                f"{perimeter_upstream}->{perimeter_downstream} for {abbrev}."
            )
        if not _has_directed_link(origin, perimeter_upstream):
            raise RuntimeError(
                f"Added OD {abbrev} lacks perimeter link {origin}->{perimeter_upstream}."
            )
        if not _has_directed_link(perimeter_downstream, destination):
            raise RuntimeError(
                f"Added OD {abbrev} lacks perimeter link "
                f"{perimeter_downstream}->{destination}."
            )


def _departure_timesteps(start: int, end: int, interval: int) -> list[int]:
    timesteps = list(range(start, end + 1, interval))
    if len(timesteps) == 0:
        raise RuntimeError("Departure timestep list is empty.")
    return timesteps


BASE_DEPARTURE_TIMESTEPS = _departure_timesteps(
    BASE_DEPARTURE_START_TIMESTEP,
    BASE_DEPARTURE_END_TIMESTEP,
    BASE_DEPARTURE_INTERVAL_TIMESTEPS,
)
PULSE_DEPARTURE_TIMESTEPS = _departure_timesteps(
    PULSE_DEPARTURE_START_TIMESTEP,
    PULSE_DEPARTURE_END_TIMESTEP,
    PULSE_DEPARTURE_INTERVAL_TIMESTEPS,
)


def _build_vehicle_specs_and_stats() -> tuple[tuple[VehicleSpec, ...], VehicleGenerationStats]:
    specs: list[VehicleSpec] = []
    for origin, destination, abbrev in PRIMARY_OD_DEFINITIONS:
        base_seq = 0
        for departure_timestep in BASE_DEPARTURE_TIMESTEPS:
            base_seq += 1
            vehicle_name = f"veh_{abbrev}_base_{base_seq:03d}"
            specs.append(
                VehicleSpec(
                    vehicle_name=vehicle_name,
                    orig=origin,
                    dest=destination,
                    departure_timestep=departure_timestep,
                    participating=True,
                    traffic_group=f"{abbrev}_base",
                    od_abbrev=abbrev,
                    demand_kind="base",
                )
            )
        if abbrev in PULSE_OD_ABBREVS:
            pulse_seq = 0
            for departure_timestep in PULSE_DEPARTURE_TIMESTEPS:
                pulse_seq += 1
                vehicle_name = f"veh_{abbrev}_pulse_{pulse_seq:03d}"
                specs.append(
                    VehicleSpec(
                        vehicle_name=vehicle_name,
                        orig=origin,
                        dest=destination,
                        departure_timestep=departure_timestep,
                        participating=True,
                        traffic_group=f"{abbrev}_pulse",
                        od_abbrev=abbrev,
                        demand_kind="pulse",
                    )
                )

    specs.sort(key=lambda item: (item.departure_timestep, item.od_abbrev, item.demand_kind))
    specs_tuple = tuple(specs)

    names = [spec.vehicle_name for spec in specs_tuple]
    duplicate_count = len(names) - len(set(names))

    od_counts: dict[str, int] = {}
    od_base_counts: dict[str, int] = {}
    od_pulse_counts: dict[str, int] = {}
    departure_count_by_timestep: dict[int, int] = {}
    base_count = 0
    pulse_count = 0
    for spec in specs_tuple:
        od_key = _od_key(spec.orig, spec.dest)
        od_counts[od_key] = od_counts.get(od_key, 0) + 1
        if spec.demand_kind == "base":
            base_count += 1
            od_base_counts[od_key] = od_base_counts.get(od_key, 0) + 1
        else:
            pulse_count += 1
            od_pulse_counts[od_key] = od_pulse_counts.get(od_key, 0) + 1
        departure_count_by_timestep[spec.departure_timestep] = (
            departure_count_by_timestep.get(spec.departure_timestep, 0) + 1
        )

    stats = VehicleGenerationStats(
        total_vehicle_count=len(specs_tuple),
        participating_count=len(specs_tuple),
        base_vehicle_count=base_count,
        pulse_vehicle_count=pulse_count,
        od_counts=dict(sorted(od_counts.items())),
        od_base_counts=dict(sorted(od_base_counts.items())),
        od_pulse_counts=dict(sorted(od_pulse_counts.items())),
        departure_count_by_timestep=dict(sorted(departure_count_by_timestep.items())),
        vehicle_name_duplicate_count=duplicate_count,
    )
    return specs_tuple, stats


VEHICLE_SPECS, GENERATION_STATS = _build_vehicle_specs_and_stats()


def generate_vehicle_vots(rng: np.random.Generator, count: int) -> list[float]:
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    return [float(value) for value in samples]


def build_vehicle_vot_records(
    specs: tuple[VehicleSpec, ...],
    vot_values: list[float],
) -> list[VehicleVotRecord]:
    if len(specs) != len(vot_values):
        raise RuntimeError("VehicleSpec count and VOT count differ.")
    records: list[VehicleVotRecord] = []
    for spec, vot in zip(specs, vot_values):
        records.append(
            VehicleVotRecord(
                vehicle_name=spec.vehicle_name,
                origin=spec.orig,
                destination=spec.dest,
                departure_timestep=spec.departure_timestep,
                participates_in_order_exchange=True,
                true_vot_per_second=vot,
                declared_vot_per_second=vot,
            )
        )
    return records


def manifest_counts_from_stats(stats: VehicleGenerationStats) -> dict:
    return {
        "scenario_name": SCENARIO_NAME,
        "actual_vehicle_count": stats.total_vehicle_count,
        "participating_count": stats.participating_count,
        "nonparticipating_count": 0,
        "base_vehicle_count": stats.base_vehicle_count,
        "pulse_vehicle_count": stats.pulse_vehicle_count,
        "traffic_seed": TRAFFIC_SEED,
        "vot_seed": VOT_SEED,
        "node_count": NODE_COUNT,
        "link_count": LINK_COUNT,
        "tvt_mp_node_count": len(TVT_MP_NODE_NAMES),
        "tvt_mp_node_names": list(TVT_MP_NODE_NAMES),
        "perimeter_od_node_names": list(PERIMETER_OD_NODE_NAMES),
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
        "spillback_link_names": list(SPILLBACK_LINK_NAMES),
        "od_counts": stats.od_counts,
        "od_base_counts": stats.od_base_counts,
        "od_pulse_counts": stats.od_pulse_counts,
        "departure_count_by_timestep": stats.departure_count_by_timestep,
        "vehicle_name_duplicate_count": stats.vehicle_name_duplicate_count,
        "primary_od_count": len(PRIMARY_OD_DEFINITIONS),
        "pulse_od_abbrevs": sorted(PULSE_OD_ABBREVS),
        "expected_world_t_after_simulation": EXPECTED_WORLD_T_AFTER_SIM,
        "legacy_500_vehicle_scenario_name": LEGACY_500_VEHICLE_SCENARIO_NAME,
        "legacy_500_vehicle_trial_output_dir_name": (
            LEGACY_500_VEHICLE_TRIAL_OUTPUT_DIR_NAME
        ),
        "added_primary_od_abbrevs": [abbrev for _o, _d, abbrev in ADDED_PRIMARY_OD_DEFINITIONS],
        "added_primary_od_base_counts": {
            abbrev: stats.od_base_counts[_od_key(origin, destination)]
            for origin, destination, abbrev in ADDED_PRIMARY_OD_DEFINITIONS
        },
        "added_primary_od_internal_links": ADDED_PRIMARY_OD_INTERNAL_LINK_BY_ABBREV,
    }


def entrance_space_available_from_link_state(link) -> bool:
    if len(link.vehicles) < link.number_of_lanes:
        return True
    entrance_vehicle = link.vehicles[-link.number_of_lanes]
    entry_gap = link.delta_per_lane * link.W.DELTAN
    return entrance_vehicle.x > entry_gap


def record_spillback_link_row(world, link_name: str, link) -> None:
    timestep = world.T
    for row in SPILLBACK_TIMESTEP_ROWS:
        if row["timestep"] == timestep and row["link_name"] == link_name:
            raise RuntimeError(
                f"Spillback row already recorded for T={timestep} link={link_name}."
            )
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
            "link_name": link_name,
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
            tvt_mp_driver_module.run_tvt_mp_driver = run_real_world_tvt_mp_driver_once
            Link.update = update_link_and_record_real_world_spillback
            gate.enabled = True
    return result


def update_link_and_record_real_world_spillback(link) -> None:
    gate = _SPILLBACK_OBSERVATION_GATE
    original_link_update = gate.original_link_update
    original_link_update(link)
    if gate.enabled is not True:
        return
    if link.W is not gate.real_world:
        return
    if link.name not in SPILLBACK_LINK_NAME_SET:
        return
    record_spillback_link_row(gate.real_world, link.name, link)


def install_real_world_spillback_observation(real_world: World) -> None:
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


def _occupied_length_of_row(row: dict) -> float:
    if row["vehicle_count_on_link"] == 0:
        return 0.0
    return float(row["maximum_vehicle_x"]) - float(row["minimum_vehicle_x"])


def summarize_spillback_rows_for_one_link(rows: list[dict]) -> dict:
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
        "maximum_vehicle_count": maximum_vehicle_count,
        "maximum_occupied_length_estimate": maximum_occupied_length,
        "entrance_blocked_timestep_count": len(blocked_timesteps),
        "first_entrance_blocked_timestep": first_blocked,
        "last_entrance_blocked_timestep": last_blocked,
    }


def summarize_spillback_by_link(rows: list[dict], world: World) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {name: [] for name in SPILLBACK_LINK_NAMES}
    for row in rows:
        link_name = row["link_name"]
        if link_name not in grouped:
            raise RuntimeError(f"Unexpected spillback link name {link_name}.")
        grouped[link_name].append(row)
    summary_by_link: dict[str, dict] = {}
    for link_name in SPILLBACK_LINK_NAMES:
        link_rows = grouped[link_name]
        link_summary = summarize_spillback_rows_for_one_link(link_rows)
        link = world.get_link(link_name)
        link_summary["vehicle_count_at_evaluation_end"] = len(link.vehicles)
        summary_by_link[link_name] = link_summary
    return summary_by_link


def _function_by_name(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Function {name} is missing in this script.")


def _call_names(function_node: ast.FunctionDef) -> list[str]:
    names: list[str] = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def _assert_world_network_contract(world: World) -> None:
    if len(world.NODES) != NODE_COUNT:
        raise RuntimeError(f"World has {len(world.NODES)} nodes, expected {NODE_COUNT}.")
    if len(world.LINKS) != LINK_COUNT:
        raise RuntimeError(f"World has {len(world.LINKS)} links, expected {LINK_COUNT}.")
    for node_name in NODE_NAMES:
        node = world.get_node(node_name)
        if node.name != node_name:
            raise RuntimeError(f"Node name mismatch for {node_name}.")
    for link_name, upstream, downstream in LINK_SPECS:
        link = world.get_link(link_name)
        if link.name != link_name:
            raise RuntimeError(f"Link name mismatch for {link_name}.")
        if link.length != LINK_LENGTH_M:
            raise RuntimeError(f"Link {link_name} length is not 200 m.")
        if link.number_of_lanes != NUMBER_OF_LANES:
            raise RuntimeError(f"Link {link_name} lane count is not 1.")
        if abs(link.u - FREE_FLOW_SPEED_M_PER_S) > 1e-9:
            raise RuntimeError(f"Link {link_name} free-flow speed is unexpected.")
        if link.start_node.name != upstream or link.end_node.name != downstream:
            raise RuntimeError(f"Link {link_name} endpoints do not match LINK_SPECS.")
    for node_name in TVT_MP_NODE_NAMES:
        node = world.get_node(node_name)
        if node.order_control_type != "time_value":
            raise RuntimeError(f"{node_name} is not time_value order control.")
    for node_name in PERIMETER_OD_NODE_NAMES:
        node = world.get_node(node_name)
        if node.order_control_type == "time_value":
            raise RuntimeError(f"{node_name} must not be a TVT-MP node.")


def validate_static_contract() -> None:
    if SCENARIO_NAME == LEGACY_500_VEHICLE_SCENARIO_NAME:
        raise RuntimeError(
            "SCENARIO_NAME must not match the legacy 500-vehicle trial."
        )
    if TRIAL_OUTPUT_DIR_NAME == LEGACY_500_VEHICLE_TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError(
            "TRIAL_OUTPUT_DIR_NAME must not match the legacy 500-vehicle trial output."
        )
    if TRIAL_OUTPUT_DIR.name != TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("TRIAL_OUTPUT_DIR name does not match.")
    if TRIAL_OUTPUT_DIR.name in COLLIDING_TRIAL_OUTPUT_DIR_NAMES:
        raise RuntimeError("Output directory name collides with an existing trial.")
    if NODE_COUNT != 12:
        raise RuntimeError("Node count must be 12.")
    if LINK_COUNT != 24:
        raise RuntimeError("Link count must be 24.")
    if len(TVT_MP_NODE_NAMES) != 4:
        raise RuntimeError("TVT-MP node count must be 4.")
    if len(set(NODE_NAMES)) != len(NODE_NAMES):
        raise RuntimeError("NODE_NAMES are not unique.")
    link_names = [name for name, _up, _down in LINK_SPECS]
    if len(set(link_names)) != len(link_names):
        raise RuntimeError("LINK_SPECS contain duplicate link names.")
    if len(INTERNAL_LINK_SPECS) != 8:
        raise RuntimeError("Internal directed link count must be 8.")
    if len(PERIMETER_LINK_SPECS) != 16:
        raise RuntimeError("Perimeter directed link count must be 16.")
    if len(SPILLBACK_LINK_NAMES) != 8:
        raise RuntimeError("Spillback link count must be 8.")
    if LINK_LENGTH_M != 200 or NUMBER_OF_LANES != 1:
        raise RuntimeError("Link geometry constants are wrong.")
    if CAPACITY_SETTINGS_UNIFORM is not True:
        raise RuntimeError("Capacity settings must stay at UXsim defaults.")
    if SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("specified_route must not be used.")
    if len(ORIGINAL_PRIMARY_OD_DEFINITIONS) != 8:
        raise RuntimeError("Original primary OD count must be 8.")
    for od_def in ORIGINAL_PRIMARY_OD_DEFINITIONS:
        if od_def not in PRIMARY_OD_DEFINITIONS:
            raise RuntimeError(f"Original primary OD missing from definitions: {od_def}.")
    if len(ADDED_PRIMARY_OD_DEFINITIONS) != 2:
        raise RuntimeError("Added primary OD count must be 2.")
    for od_def in ADDED_PRIMARY_OD_DEFINITIONS:
        if od_def not in PRIMARY_OD_DEFINITIONS:
            raise RuntimeError(f"Added primary OD missing from definitions: {od_def}.")
    expected_added = (
        ("north_east_od", "west_north_od", "ne_wn"),
        ("south_west_od", "north_west_od", "sw_nw"),
    )
    for od_def in expected_added:
        if od_def not in ADDED_PRIMARY_OD_DEFINITIONS:
            raise RuntimeError(f"Expected added OD not defined: {od_def}.")
    assert_added_primary_od_network_paths()
    if len(PRIMARY_OD_DEFINITIONS) != 10:
        raise RuntimeError("Primary OD count must be 10.")
    if BASE_VEHICLES_PER_OD != 50:
        raise RuntimeError("Base vehicles per OD must be 50.")
    if BASE_OD_VEHICLE_COUNT != 500:
        raise RuntimeError("Base OD vehicle total must be 500.")
    if PULSE_VEHICLES_PER_OD != 50:
        raise RuntimeError("Pulse vehicles per OD must be 50.")
    if PULSE_OD_VEHICLE_COUNT != 100:
        raise RuntimeError("Pulse vehicle total must be 100.")
    if EXPECTED_TOTAL_VEHICLE_COUNT != 600:
        raise RuntimeError("Vehicle total must be 600.")
    if len(BASE_DEPARTURE_TIMESTEPS) != 50:
        raise RuntimeError("Base departure count per OD must be 50 timesteps.")
    if BASE_DEPARTURE_TIMESTEPS[0] != 20 or BASE_DEPARTURE_TIMESTEPS[-1] != 118:
        raise RuntimeError("Base departure window must be T=20..118 step 2.")
    if len(PULSE_DEPARTURE_TIMESTEPS) != 50:
        raise RuntimeError("Pulse departure count per OD must be 50 timesteps.")
    if PULSE_DEPARTURE_TIMESTEPS[0] != 160 or PULSE_DEPARTURE_TIMESTEPS[-1] != 258:
        raise RuntimeError("Pulse departure window must be T=160..258 step 2.")
    if PULSE_OD_ABBREVS != frozenset({"wn_en", "nw_sw"}):
        raise RuntimeError("Pulse OD abbrev set is wrong.")
    if EVALUATION_START_TIMESTEP != 0:
        raise RuntimeError("Evaluation start must be T=0.")
    if EVALUATION_END_TIMESTEP != 899 or INTERNAL_TSIZE != 930:
        raise RuntimeError("Evaluation or TSIZE constants are wrong.")
    if EXPECTED_WORLD_T_AFTER_SIM != 900:
        raise RuntimeError("World must end at T=900 after simulation.")
    if INTERNAL_TSIZE != EVALUATION_END_TIMESTEP + BASELINE_HORIZON_STEPS + 1:
        raise RuntimeError("INTERNAL_TSIZE must exceed evaluation by horizon+1.")
    if EXPECTED_DRIVER_CALL_COUNT != 900:
        raise RuntimeError("Driver call count must be 900.")
    if BASELINE_HORIZON_STEPS != 30 or CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Horizon or clearance constants are wrong.")
    if MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Candidate visit limit must match existing trials (10).")

    specs = VEHICLE_SPECS
    stats = GENERATION_STATS
    if len(specs) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VEHICLE_SPECS length is not 600.")
    if stats.total_vehicle_count != 600:
        raise RuntimeError("Generation stats vehicle total is not 600.")
    if stats.participating_count != 600:
        raise RuntimeError("All vehicles must be participating.")
    if stats.base_vehicle_count != 500 or stats.pulse_vehicle_count != 100:
        raise RuntimeError("Base/pulse totals in stats are wrong.")
    for origin, destination, abbrev in ADDED_PRIMARY_OD_DEFINITIONS:
        od_key = _od_key(origin, destination)
        if stats.od_base_counts.get(od_key, 0) != 50:
            raise RuntimeError(f"Added OD {abbrev} base count is not 50.")
    if stats.vehicle_name_duplicate_count != 0:
        raise RuntimeError("Vehicle names must be unique.")
    for spec in specs:
        if spec.participating is not True:
            raise RuntimeError(f"{spec.vehicle_name} must be participating.")
    sample_vot_records = build_vehicle_vot_records(
        VEHICLE_SPECS[:2],
        [1.0, 2.0],
    )
    for record in sample_vot_records:
        if record.participates_in_order_exchange is not True:
            raise RuntimeError("Vehicles must participate in order exchange.")
        if record.declared_vot_per_second != record.true_vot_per_second:
            raise RuntimeError("Declared VOT must equal true VOT.")
    for od_key, count in stats.od_base_counts.items():
        if count != 50:
            raise RuntimeError(f"Base count for {od_key} is not 50.")
    for abbrev in PULSE_OD_ABBREVS:
        matching = [item for item in PRIMARY_OD_DEFINITIONS if item[2] == abbrev]
        if len(matching) != 1:
            raise RuntimeError(f"Pulse abbrev {abbrev} is ambiguous.")
        origin, destination, _abbrev = matching[0]
        od_key = _od_key(origin, destination)
        if stats.od_pulse_counts.get(od_key, 0) != 50:
            raise RuntimeError(f"Pulse count for {od_key} is not 50.")
    for od_key, count in stats.od_counts.items():
        abbrev_match = None
        for origin, destination, abbrev in PRIMARY_OD_DEFINITIONS:
            if _od_key(origin, destination) == od_key:
                abbrev_match = abbrev
        if abbrev_match is None:
            raise RuntimeError(f"Unknown OD key {od_key}.")
        expected = 50
        if abbrev_match in PULSE_OD_ABBREVS:
            expected = 100
        if count != expected:
            raise RuntimeError(f"OD total for {od_key} is {count}, expected {expected}.")

    world = build_world_and_network()
    _assert_world_network_contract(world)

    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    validator = _function_by_name(tree, "validate_static_contract")
    validator_calls = _call_names(validator)
    if "exec_simulation" in validator_calls:
        raise RuntimeError("validate_static_contract must not call exec_simulation.")
    if "install_real_world_spillback_observation" in validator_calls:
        raise RuntimeError("Static validation must not install spillback hooks.")
    if "build_tvt_mp_research_output" in validator_calls:
        raise RuntimeError("Static validation must not build research output.")


def ensure_trial_parent_directories() -> None:
    TRIAL_PARENT.mkdir(parents=True, exist_ok=True)


def refuse_existing_trial_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Remove or rename it manually before re-running."
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
        world.addVehicle(
            spec.orig,
            spec.dest,
            spec.departure_timestep,
            name=spec.vehicle_name,
            departure_time_is_time_step=1,
            vot_true=vot_record.true_vot_per_second,
            vot_declared=vot_record.declared_vot_per_second,
            participates_in_order_exchange=True,
        )


def verify_evaluation_end(world: World) -> dict:
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
                f"Registry {field_name} expected {EVALUATION_END_TIMESTEP}, "
                f"got {actual!r}."
            )
    return {"world_t": world.T, "world_t_ok": True}


def collect_trip_completion(world: World) -> dict:
    completed_names = []
    incomplete_names = []
    for vehicle in world.VEHICLES.values():
        if vehicle.state == "end":
            completed_names.append(vehicle.name)
        else:
            incomplete_names.append(vehicle.name)
    completed_names.sort()
    incomplete_names.sort()
    link_vehicle_counts = {}
    for link in world.LINKS:
        link_vehicle_counts[link.name] = len(link.vehicles)
    internal_end_counts = {
        link_name: link_vehicle_counts[link_name] for link_name in SPILLBACK_LINK_NAMES
    }
    return {
        "completed_trip_count": len(completed_names),
        "incomplete_vehicle_count": len(incomplete_names),
        "incomplete_vehicle_names": incomplete_names,
        "link_vehicle_counts_at_evaluation_end": dict(sorted(link_vehicle_counts.items())),
        "internal_link_vehicle_counts_at_evaluation_end": internal_end_counts,
    }


def collect_node_rank_ledger_summary(world: World) -> dict:
    ledgers = world.order_control_tvt_rank_states_by_node_name
    summary: dict[str, dict] = {}
    for node_name in TVT_MP_NODE_NAMES:
        state = ledgers[node_name]
        exported = state.export_state()
        summary[node_name] = {
            "k_confirmed": exported["k_confirmed"],
            "confirmed_visit_count": len(exported["confirmed_visits"]),
            "undetermined_visit_count": len(exported["undetermined_visits"]),
        }
    return summary


def collect_visit_id_summary(world: World) -> dict:
    visit_id_counts: dict[int, int] = {}
    max_visit_id = 0
    ledgers = world.order_control_tvt_rank_states_by_node_name
    for node_name in TVT_MP_NODE_NAMES:
        exported = ledgers[node_name].export_state()
        for row in exported["confirmed_visits"]:
            visit_id = int(row["visit_id"])
            visit_id_counts[visit_id] = visit_id_counts.get(visit_id, 0) + 1
            if visit_id > max_visit_id:
                max_visit_id = visit_id
        for row in exported["undetermined_visits"]:
            visit_id = int(row["visit_id"])
            visit_id_counts[visit_id] = visit_id_counts.get(visit_id, 0) + 1
            if visit_id > max_visit_id:
                max_visit_id = visit_id
    return {
        "visit_id_counts": dict(sorted(visit_id_counts.items())),
        "maximum_visit_id": max_visit_id,
    }


def collect_transaction_counts_by_node(bundle) -> dict[str, int]:
    counts: dict[str, int] = {name: 0 for name in TVT_MP_NODE_NAMES}
    for transaction in bundle.transactions:
        node_name = transaction.node_name
        if node_name in counts:
            counts[node_name] += 1
    return counts


def passage_comparison(bundle) -> dict:
    both_observed = 0
    equal_count = 0
    unequal_count = 0
    actual_unobserved = 0
    buyer_count = 0
    seller_count = 0
    for visit in bundle.visits:
        if visit.role == "buyer":
            buyer_count += 1
        elif visit.role == "seller":
            seller_count += 1
        if visit.actual_passage_timestep is None:
            actual_unobserved += 1
        if (
            visit.candidate_passage_timestep is not None
            and visit.actual_passage_timestep is not None
        ):
            both_observed += 1
            difference = visit.candidate_passage_timestep - visit.actual_passage_timestep
            if difference == 0:
                equal_count += 1
            else:
                unequal_count += 1
    scenario = bundle.scenario[0]
    return {
        "transaction_count": scenario.transaction_count,
        "buyer_visit_count": buyer_count,
        "seller_visit_count": seller_count,
        "scenario_buyer_visit_count": scenario.buyer_visit_count,
        "scenario_seller_visit_count": scenario.seller_visit_count,
        "both_passage_observed_count": both_observed,
        "candidate_equals_actual_count": equal_count,
        "candidate_differs_from_actual_count": unequal_count,
        "actual_unobserved_count": actual_unobserved,
        "scenario_actual_unobserved_count": scenario.actual_unobserved_count,
    }


def verify_spillback_observation(rows: list[dict]) -> None:
    expected_rows_per_link = EXPECTED_DRIVER_CALL_COUNT
    grouped: dict[str, list[dict]] = {name: [] for name in SPILLBACK_LINK_NAMES}
    for row in rows:
        grouped[row["link_name"]].append(row)
    for link_name in SPILLBACK_LINK_NAMES:
        link_rows = grouped[link_name]
        if len(link_rows) != expected_rows_per_link:
            raise RuntimeError(
                f"Link {link_name}: expected {expected_rows_per_link} rows, "
                f"got {len(link_rows)}."
            )
        for index, row in enumerate(link_rows):
            if row["timestep"] != index:
                raise RuntimeError(
                    f"Link {link_name} row {index} has timestep {row['timestep']!r}."
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
        "vot_seed",
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
                    "departure_timestep": record.departure_timestep,
                    "participates_in_order_exchange": record.participates_in_order_exchange,
                    "true_vot_per_second": record.true_vot_per_second,
                    "declared_vot_per_second": record.declared_vot_per_second,
                    "traffic_seed": TRAFFIC_SEED,
                    "vot_seed": VOT_SEED,
                }
            )


def write_spillback_summary_csv(path: Path, summary_by_link: dict[str, dict]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SPILLBACK_SUMMARY_FIELDS)
        writer.writeheader()
        for link_name in SPILLBACK_LINK_NAMES:
            summary = summary_by_link[link_name]
            writer.writerow(
                {
                    "link_name": link_name,
                    "maximum_vehicle_count": summary["maximum_vehicle_count"],
                    "entrance_blocked_timestep_count": summary[
                        "entrance_blocked_timestep_count"
                    ],
                    "first_entrance_blocked_timestep": summary[
                        "first_entrance_blocked_timestep"
                    ],
                    "last_entrance_blocked_timestep": summary[
                        "last_entrance_blocked_timestep"
                    ],
                    "vehicle_count_at_evaluation_end": summary[
                        "vehicle_count_at_evaluation_end"
                    ],
                }
            )


def write_manifest_json(
    path: Path,
    timing: TimingRecord,
    world: World,
    generated_files: list[str],
    spillback_summary_by_link: dict[str, dict],
    completion: dict,
    ledger_summary: dict,
    visit_id_summary: dict,
    transactions_by_node: dict[str, int],
    passage_stats: dict,
    original_python_recursion_limit: int,
) -> None:
    manifest = {
        "schema_note": (
            "Four-cross grid medium all-participating trial manifest; "
            "not a formal experiment schema."
        ),
        "run_type": "trial",
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
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
        "internal_link_vehicle_counts_at_evaluation_end": completion[
            "internal_link_vehicle_counts_at_evaluation_end"
        ],
        "node_rank_ledger_summary": ledger_summary,
        "visit_id_summary": visit_id_summary,
        "transactions_by_node": transactions_by_node,
        "passage_comparison": passage_stats,
        "internal_spillback_summary_by_link": spillback_summary_by_link,
        "generated_files": generated_files,
        "world_copy_recursion_limit_during_trial": WORLD_COPY_RECURSION_LIMIT,
        "original_python_recursion_limit": original_python_recursion_limit,
    }
    manifest.update(manifest_counts_from_stats(GENERATION_STATS))
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(
    path: Path,
    world: World,
    bundle,
    completion: dict,
    spillback_summary_by_link: dict[str, dict],
    ledger_summary: dict,
    visit_id_summary: dict,
    transactions_by_node: dict[str, int],
    passage_stats: dict,
) -> None:
    stats = GENERATION_STATS
    scenario_row = bundle.scenario[0]
    lines = [
        "TVT-MP four-cross grid medium all-participating trial",
        "=" * 55,
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Network:",
        "  12 nodes (4 TVT-MP intersections + 8 perimeter OD nodes)",
        "  24 directed links (8 internal + 16 perimeter), 200 m, single lane",
        f"  TVT-MP nodes: {', '.join(TVT_MP_NODE_NAMES)}",
        "",
        "Vehicles:",
        f"  primary OD count {len(PRIMARY_OD_DEFINITIONS)}",
        f"  total {stats.total_vehicle_count} (all participating)",
        f"  base demand {stats.base_vehicle_count} (10 OD x 50, T=20..118 step 2)",
        f"  pulse demand {stats.pulse_vehicle_count} (2 OD x 50, T=160..258 step 2)",
        f"  OD counts: {stats.od_counts}",
        "  added base ODs (ne_wn, sw_nw) base counts:",
        f"    ne_wn: {stats.od_base_counts.get(_od_key('north_east_od', 'west_north_od'), 0)}",
        f"    sw_nw: {stats.od_base_counts.get(_od_key('south_west_od', 'north_west_od'), 0)}",
        "",
        "Evaluation:",
        f"  T={EVALUATION_START_TIMESTEP}..{EVALUATION_END_TIMESTEP}",
        f"  internal TSIZE {INTERNAL_TSIZE}, horizon {BASELINE_HORIZON_STEPS}",
        f"  World.T after simulation (expected {EXPECTED_WORLD_T_AFTER_SIM}): {world.T}",
        f"  candidate visit limit {MAX_CANDIDATE_VISIT_COUNT}, clearance {CLEARANCE_TIMESTEPS}",
        "",
        "Established transactions:",
        f"  total {scenario_row.transaction_count}",
        f"  by node: {transactions_by_node}",
        f"  buyer visits (recount) {passage_stats['buyer_visit_count']}",
        f"  seller visits (recount) {passage_stats['seller_visit_count']}",
        "",
        "Candidate P vs Actual P (trade-scope parties):",
        f"  both observed {passage_stats['both_passage_observed_count']}",
        f"  candidate equals actual {passage_stats['candidate_equals_actual_count']}",
        f"  candidate differs {passage_stats['candidate_differs_from_actual_count']}",
        f"  actual unobserved {passage_stats['actual_unobserved_count']}",
        "",
        "Node rank ledger (assigned_rank, end of evaluation):",
    ]
    for node_name in TVT_MP_NODE_NAMES:
        row = ledger_summary[node_name]
        lines.append(
            f"  {node_name}: confirmed {row['confirmed_visit_count']}, "
            f"undetermined {row['undetermined_visit_count']}"
        )
    lines.extend(
        [
            "",
            "Visit ID counts (all TVT nodes, ledger visits):",
            f"  {visit_id_summary['visit_id_counts']}",
            f"  maximum visit id {visit_id_summary['maximum_visit_id']}",
            "",
            "Internal link spillback summary (8 directed internal links):",
        ]
    )
    for link_name in SPILLBACK_LINK_NAMES:
        summary = spillback_summary_by_link[link_name]
        lines.append(
            f"  {link_name}: max vehicles {summary['maximum_vehicle_count']}, "
            f"entrance blocked timesteps {summary['entrance_blocked_timestep_count']}, "
            f"vehicles at evaluation end "
            f"{summary['vehicle_count_at_evaluation_end']}"
        )
    lines.extend(
        [
            "",
            "Trips:",
            f"  completed {completion['completed_trip_count']} / {stats.total_vehicle_count}",
            f"  incomplete {completion['incomplete_vehicle_count']}",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def print_console_summary(
    bundle,
    passage_stats: dict,
    transactions_by_node: dict[str, int],
    spillback_summary_by_link: dict[str, dict],
    timing: TimingRecord,
    output_dir: Path,
) -> None:
    stats = GENERATION_STATS
    max_internal = 0
    for link_name in SPILLBACK_LINK_NAMES:
        count = spillback_summary_by_link[link_name]["maximum_vehicle_count"]
        if count > max_internal:
            max_internal = count
    print()
    print("=== TVT-MP four-cross grid medium all-participating trial ===")
    print()
    print(f"Scenario: {SCENARIO_NAME}")
    print(f"Network: {NODE_COUNT} nodes, {LINK_COUNT} links, 4 TVT-MP intersections")
    print(
        f"Primary ODs: {len(PRIMARY_OD_DEFINITIONS)} "
        f"(base {stats.base_vehicle_count}, pulse {stats.pulse_vehicle_count}, "
        f"total {stats.total_vehicle_count})"
    )
    print(
        f"Evaluation: T={EVALUATION_START_TIMESTEP}..{EVALUATION_END_TIMESTEP}, "
        f"TSIZE {INTERNAL_TSIZE}, World ends T={EXPECTED_WORLD_T_AFTER_SIM}"
    )
    print(f"Transactions: {bundle.scenario[0].transaction_count}")
    print(f"Transactions by node: {transactions_by_node}")
    print(
        "Passage CP=AP: "
        f"{passage_stats['candidate_equals_actual_count']} / "
        f"{passage_stats['both_passage_observed_count']} observed"
    )
    print(f"Internal link max vehicles (peak): {max_internal}")
    print(f"Timing total (s): {timing.script_total_s:.3f}")
    print(f"Output directory: {output_dir}")
    print()


def verify_research_output(bundle, output_dir: Path) -> None:
    if bundle.scenario[0].scenario_name != SCENARIO_NAME:
        raise RuntimeError("Research output scenario name does not match.")
    for name in RESEARCH_CSV_NAMES:
        path = output_dir / name
        if not path.is_file():
            raise RuntimeError(f"Expected research CSV missing: {path}")


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
        TRIAL_OUTPUT_DIR.mkdir(parents=False, exist_ok=False)

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
            raise RuntimeError(f"Expected TSIZE=={INTERNAL_TSIZE}, got {world.TSIZE}.")

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
        verify_spillback_observation(SPILLBACK_TIMESTEP_ROWS)
        spillback_summary_by_link = summarize_spillback_by_link(
            SPILLBACK_TIMESTEP_ROWS,
            world,
        )
        ledger_summary = collect_node_rank_ledger_summary(world)
        visit_id_summary = collect_visit_id_summary(world)

        t0 = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        timing.research_build_s = time.perf_counter() - t0
        passage_stats = passage_comparison(bundle)
        transactions_by_node = collect_transaction_counts_by_node(bundle)

        t0 = time.perf_counter()
        write_tvt_mp_research_output_csv(bundle, TRIAL_OUTPUT_DIR, overwrite=False)
        timing.csv_write_s = time.perf_counter() - t0
        verify_research_output(bundle, TRIAL_OUTPUT_DIR)

        generated_files = list(RESEARCH_CSV_NAMES) + [
            "vehicle_vot.csv",
            SPILLBACK_SUMMARY_CSV_NAME,
            "manifest.json",
            "run_summary.txt",
        ]

        t0 = time.perf_counter()
        write_vehicle_vot_csv(TRIAL_OUTPUT_DIR / "vehicle_vot.csv", vot_records)
        write_spillback_summary_csv(
            TRIAL_OUTPUT_DIR / SPILLBACK_SUMMARY_CSV_NAME,
            spillback_summary_by_link,
        )
        timing.trial_aux_write_s = time.perf_counter() - t0
        timing.script_total_s = time.perf_counter() - script_start

        write_manifest_json(
            TRIAL_OUTPUT_DIR / "manifest.json",
            timing,
            world,
            generated_files,
            spillback_summary_by_link,
            completion,
            ledger_summary,
            visit_id_summary,
            transactions_by_node,
            passage_stats,
            original_python_recursion_limit,
        )
        write_run_summary_txt(
            TRIAL_OUTPUT_DIR / "run_summary.txt",
            world,
            bundle,
            completion,
            spillback_summary_by_link,
            ledger_summary,
            visit_id_summary,
            transactions_by_node,
            passage_stats,
        )
        print_console_summary(
            bundle,
            passage_stats,
            transactions_by_node,
            spillback_summary_by_link,
            timing,
            TRIAL_OUTPUT_DIR,
        )
        return 0
    finally:
        sys.setrecursionlimit(original_python_recursion_limit)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        recursion_limit_before = sys.getrecursionlimit()
        validate_static_contract()
        if sys.getrecursionlimit() != recursion_limit_before:
            raise RuntimeError("Static validation changed sys.getrecursionlimit().")
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        ast.parse(source)
        compile(source, str(SCRIPT_PATH), "exec")
        print("Static contract validation passed.", file=sys.stderr)
        raise SystemExit(0)
    raise SystemExit(main())
