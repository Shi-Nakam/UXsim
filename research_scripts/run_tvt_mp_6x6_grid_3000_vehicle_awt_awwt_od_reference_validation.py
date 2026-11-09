"""
TVT-MP 3000-vehicle full completion, then one OD-based waiting-time evaluation.

Traffic, participation, seeds, and the shared-snapshot TVT-MP driver match the
saved 20% nonparticipating full-completion audit. This file does not import
that trial or the FCFS waiting-time script. It writes the same ten TVT-MP
formal files, then compares the research CSVs, audit CSVs, vehicle_vot.csv,
and manifest research keys with the saved reference.

After every vehicle is in state "end" and traffic clearance has passed, it
calls evaluate_network_wide_waiting_time once. That call does not run the
simulation again and does not store its result on the World. The saved
reference has no OD AWT or AWWT files, so those new files are not part of the
reference comparison.

Run from the repository root:

    python research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py --static-validate-only
    python research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py
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
from uxsim.network_wide_waiting_time_evaluation import (
    evaluate_network_wide_waiting_time,
)
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tvt_mp_full_run_audit_helper import (  # noqa: E402
    TRANSACTION_AUDIT_CSV_NAME,
    VISIT_AUDIT_CSV_NAME,
    finalize_tvt_mp_full_run_audit,
    install_tvt_mp_full_run_audit,
    write_tvt_mp_full_run_audit_csv,
)

# ---------------------------------------------------------------------------
# 1. Scenario constants (copied from the T=0..999 departure-end trial)
# ---------------------------------------------------------------------------

SCENARIO_NAME = (
    "tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation_"
    "departure_999_seed_0_demand_seed_42_vot_seed_1_nonparticipation_seed_3"
)
TRIAL_OUTPUT_DIR_NAME = SCENARIO_NAME
REFERENCE_DIR_NAME = (
    "tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_"
    "candidate_limit_10_seed_0_vot_seed_1_nonparticipation_seed_3"
)
PREVIOUS_EXEC_SIMULATION_SECONDS = 65093.892005
# Production driver constant _DECISION_WINDOW_STEPS. This script does not
# write it onto the World, matching the saved full-completion trial.
PRODUCTION_DECISION_WINDOW_STEPS = 6
OD_AWT_AWWT_COMPARED_TO_REFERENCE = False
BASELINE_CANDIDATE_SHARED_SNAPSHOT_PRODUCTION_IS_ACTIVE = True
AWT_AWWT_REFERENCE_COMPARISON_NOTE = (
    "This run computes OD-based AWT and AWWT after full completion. "
    "The saved full-completion reference has no formal OD AWT or AWWT files. "
    "Those new files are not compared. This comparison does not claim "
    "AWT or AWWT equality with the reference."
)
METHOD_NAME = "tvt_mp"
PARTICIPATING_COHORT = "tvt_participating_cohort"
NONPARTICIPATING_COHORT = "tvt_nonparticipating_cohort"
PARTICIPATING_STATUS = "participating"
NONPARTICIPATING_STATUS = "nonparticipating"
WAITING_TIME_VEHICLES_CSV_NAME = "network_wide_waiting_time_vehicles.csv"
WAITING_TIME_COHORTS_CSV_NAME = "network_wide_waiting_time_cohorts.csv"
WAITING_TIME_SUMMARY_JSON_NAME = "network_wide_waiting_time_summary.json"
WAITING_TIME_OUTPUT_FILE_NAMES = (
    WAITING_TIME_VEHICLES_CSV_NAME,
    WAITING_TIME_COHORTS_CSV_NAME,
    WAITING_TIME_SUMMARY_JSON_NAME,
)
AUDIT_ABS_TOL = 1e-9
WEIGHTED_IDENTITY_ABS_TOL = 1e-6
SECONDS_MATCH_ABS_TOL = 1e-6

FULL_COMPLETION_TRIAL = True
TRAFFIC_CLEARANCE_REQUIRED = True
FULL_TRIP_COMPLETION_REQUIRED = True
FULL_RUN_AUDIT_ENABLED = True
PROFILING_RUN = False
PRODUCTION_UNCHANGED_BY_SCRIPT = True
SHARED_SERIALIZATION_PRODUCTION_IS_ACTIVE = True

EXPECTED_VEHICLE_PLAN_SHA256 = (
    "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
)

NUM_VEHICLES = 3000
NONPARTICIPATING_VEHICLE_COUNT = 600
PARTICIPATING_VEHICLE_COUNT = 2400
NONPARTICIPATION_SEED = 3

DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5

TRAFFIC_SEED = 0
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

# Safe cap for the last real-World TVT decision. Not an assumed completion time.
# FCFS pretrial completion near T=2296 is not used as this trial's end.
LAST_TVT_DECISION_TIMESTEP_CAP = 5000
BASELINE_HORIZON_STEPS = 30
INTERNAL_TSIZE = LAST_TVT_DECISION_TIMESTEP_CAP + BASELINE_HORIZON_STEPS + 1
MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1
WORLD_COPY_RECURSION_LIMIT = 50000

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
REACTION_TIME = 1
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2
SHOW_PROGRESS_DELTAT = 600

CAPACITY_IN_OUT_EXPLICITLY_SET_BY_SCRIPT = False
SPECIFIED_ROUTE_USED = False
ROUTE_ASSIGNMENT_MODE = "uxsim_free_route_choice"

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)
AUDIT_CSV_NAMES = (
    TRANSACTION_AUDIT_CSV_NAME,
    VISIT_AUDIT_CSV_NAME,
)
AUXILIARY_FILE_NAMES = (
    "vehicle_vot.csv",
    "manifest.json",
    "run_summary.txt",
)
FORMAL_OUTPUT_FILE_NAMES = RESEARCH_CSV_NAMES + AUDIT_CSV_NAMES + AUXILIARY_FILE_NAMES

REPO_ROOT = SCRIPT_PATH.parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME
REFERENCE_OUTPUT_DIR = TRIAL_PARENT / REFERENCE_DIR_NAME
COMPARISON_JSON_NAME = "full_completion_reference_comparison.json"
COMPARISON_TXT_NAME = "full_completion_reference_comparison.txt"
RESEARCH_CSV_SCENARIO_COLUMN = "scenario_name"
EXPECTED_CSV_DATA_ROW_COUNTS = {
    "tvt_mp_transactions.csv": 4298,
    "tvt_mp_visits.csv": 11871,
    "tvt_mp_vehicles.csv": 3000,
    "tvt_mp_nodes.csv": 36,
    "tvt_mp_scenario.csv": 1,
    "tvt_mp_transaction_audit.csv": 4298,
    "tvt_mp_visit_audit.csv": 11871,
    "vehicle_vot.csv": 3000,
}
MANIFEST_RESEARCH_RESULT_KEYS = (
    "full_completion_trial",
    "traffic_clearance_required",
    "full_trip_completion_required",
    "full_run_audit_enabled",
    "nonparticipating_fraction",
    "participating_vehicle_count",
    "nonparticipating_vehicle_count",
    "nonparticipation_seed",
    "NUM_VEHICLES",
    "departure_start",
    "departure_end",
    "candidate_visit_limit",
    "baseline_horizon",
    "clearance",
    "final_world_t",
    "final_actual_passage_timestep",
    "evaluation_end_timestep",
    "final_vehicle_state_counts",
    "final_internal_link_vehicle_count",
    "final_od_connector_vehicle_count",
    "final_all_link_vehicle_count",
    "scheduled_departure_reached_count",
    "scheduled_departure_not_reached_count",
    "traffic_clearance_completed",
    "full_trip_completion",
    "transaction_count",
    "transactions_by_node",
    "full_run_audit_transaction_row_count",
    "full_run_audit_visit_row_count",
    "full_run_audit_buyer_row_count",
    "full_run_audit_seller_row_count",
    "full_run_audit_nonparticipating_row_count",
    "full_run_audit_actual_arrival_row_count",
    "full_run_audit_fifo_violation_total",
    "full_run_audit_max_same_inlink_party_count",
    "full_run_audit_max_same_inlink_buyer_count",
    "full_run_audit_max_same_inlink_seller_count",
    "full_run_audit_max_same_inlink_nonparticipating_count",
    "vehicle_plan_sha256",
    "participation_assignment_sha256",
    "nonparticipating_name_sha256",
    "participating_name_sha256",
    "nonparticipating_vehicle_names",
    "profiling_run",
    "jam_density",
    "free_flow_speed_mps",
    "link_length_m",
    "traffic_seed",
    "demand_gen_seed",
    "vot_seed",
    "safe_last_tvt_decision_timestep_cap",
    "internal_tsize",
    "node_rank_ledger_summary",
    "visit_id_summary",
    "production_unchanged_by_script",
    "fcfs_pretrial_completion_timestep_not_assumed",
    "formal_output_file_names",
)
MANIFEST_KEYS_EXCLUDED_FROM_REFERENCE = (
    "scenario_name",
    "timing_seconds",
    "output_directory_bytes_before_manifest",
    "output_directory",
    "tvt_mp_transaction_audit_csv_sha256",
    "tvt_mp_visit_audit_csv_sha256",
    "research_csv_sha256",
    "shared_serialization_production_is_active",
    "baseline_candidate_shared_snapshot_production_is_active",
    "od_awt_awwt_compared_to_reference",
    "awt_awwt_reference_comparison_note",
)


@dataclass
class TimingRecord:
    world_build_s: float = 0.0
    finalize_s: float = 0.0
    audit_install_s: float = 0.0
    exec_simulation_s: float = 0.0
    research_build_s: float = 0.0
    audit_finalize_s: float = 0.0
    research_csv_write_s: float = 0.0
    audit_csv_write_s: float = 0.0
    vehicle_vot_csv_write_s: float = 0.0
    network_wide_waiting_time_evaluation_s: float = 0.0
    awt_awwt_output_write_s: float = 0.0
    manifest_write_s: float = 0.0
    run_summary_write_s: float = 0.0
    script_total_s: float = 0.0


@dataclass
class VehicleVotRecord:
    vehicle_name: str
    origin: str
    destination: str
    departure_time: float
    participates_in_order_exchange: bool
    true_vot_per_second: float
    declared_vot_per_second: float | None


@dataclass(frozen=True)
class FullRunAuditSummary:
    transaction_row_count: int
    visit_row_count: int
    buyer_row_count: int
    seller_row_count: int
    nonparticipating_row_count: int
    actual_arrival_row_count: int
    fifo_violation_total: int
    max_same_inlink_party_count: int
    max_same_inlink_buyer_count: int
    max_same_inlink_seller_count: int
    max_same_inlink_nonparticipating_count: int
    transaction_csv_sha256: str
    visit_csv_sha256: str


# ---------------------------------------------------------------------------
# 2. Network names (same 6x6 construction as the departure-end trial)
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
        connectors.append(
            (f"bottom_{column}_to_g_5_{column}", bottom_node, south_grid, OD_CONNECTOR_LENGTH, 1)
        )
        connectors.append(
            (f"g_5_{column}_to_bottom_{column}", south_grid, bottom_node, OD_CONNECTOR_LENGTH, 1)
        )
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
# 3. Vehicle plans and 20% nonparticipation
# ---------------------------------------------------------------------------

def generate_vehicle_plans() -> list[dict]:
    """Same formula as the 3000-vehicle departure-end trial."""
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
    external = set(EXTERNAL_OD_NODES)
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
            raise RuntimeError(f"{plan['name']} Manhattan distance is too small.")
        departure_time = plan["departure_time"]
        if previous_departure is not None and departure_time < previous_departure:
            raise RuntimeError(f"{plan['name']} departure decreased.")
        previous_departure = departure_time
        departures.append(departure_time)
    if departures[0] != DEPARTURE_START:
        raise RuntimeError(f"First departure is {departures[0]!r}.")
    if departures[-1] != DEPARTURE_END:
        raise RuntimeError(f"Last departure is {departures[-1]!r}.")
    digest = _vehicle_plan_digest(plans)
    if digest != EXPECTED_VEHICLE_PLAN_SHA256:
        raise RuntimeError(
            f"vehicle_plan_sha256 expected {EXPECTED_VEHICLE_PLAN_SHA256}, got {digest}."
        )
    return {
        "plan_count": len(plans),
        "first_departure": departures[0],
        "last_departure": departures[-1],
        "vehicle_plan_sha256": digest,
    }


def select_nonparticipating_names(plans: list[dict]) -> tuple[str, ...]:
    """Same selector as the 4-cross 20% trial: random.Random(seed).sample.

    The population is the locked plan order. The returned tuple keeps that
    order. Participation is not used as an arrival tie-break.
    """
    population = []
    for plan in plans:
        population.append(plan["name"])
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
        raise RuntimeError("Nonparticipating selection did not return 600 names.")
    again = select_nonparticipating_names_once(population)
    if again != tuple(selected):
        raise RuntimeError("Nonparticipating selection is not repeatable.")
    return tuple(selected)


def select_nonparticipating_names_once(population: list[str]) -> tuple[str, ...]:
    sampled = set(
        random.Random(NONPARTICIPATION_SEED).sample(
            list(population),
            NONPARTICIPATING_VEHICLE_COUNT,
        )
    )
    selected = []
    for name in population:
        if name in sampled:
            selected.append(name)
    return tuple(selected)


def _hash_names(names: tuple[str, ...] | list[str]) -> str:
    payload = "\n".join(names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def participation_assignment_digest(plans: list[dict], nonparticipating_names: tuple[str, ...]) -> str:
    selected = set(nonparticipating_names)
    hasher = hashlib.sha256()
    for plan in plans:
        if plan["name"] in selected:
            flag = "nonparticipating"
        else:
            flag = "participating"
        line = f"{plan['name']}|{flag}\n"
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


def build_vehicle_vot_records(
    plans: list[dict],
    vot_values: list[float],
    nonparticipating_names: tuple[str, ...],
) -> list[VehicleVotRecord]:
    if len(plans) != len(vot_values):
        raise RuntimeError("Vehicle plan count and VOT count differ.")
    selected = set(nonparticipating_names)
    records = []
    participating_count = 0
    nonparticipating_count = 0
    for plan, vot in zip(plans, vot_values):
        if plan["name"] in selected:
            records.append(
                VehicleVotRecord(
                    vehicle_name=plan["name"],
                    origin=plan["origin"],
                    destination=plan["destination"],
                    departure_time=plan["departure_time"],
                    participates_in_order_exchange=False,
                    true_vot_per_second=vot,
                    declared_vot_per_second=None,
                )
            )
            nonparticipating_count = nonparticipating_count + 1
        else:
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
            participating_count = participating_count + 1
    if participating_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Participating count is {participating_count}, expected 2400.")
    if nonparticipating_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Nonparticipating count is {nonparticipating_count}, expected 600.")
    return records


# ---------------------------------------------------------------------------
# 4. World
# ---------------------------------------------------------------------------

def build_world_and_network() -> World:
    world = World(
        name=SCENARIO_NAME,
        deltan=1,
        reaction_time=REACTION_TIME,
        tmax=INTERNAL_TSIZE,
        random_seed=TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
        show_progress_deltat=SHOW_PROGRESS_DELTAT,
    )
    spacing = 1.0
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            world.addNode(_grid_node_name(row, column), column * spacing, -row * spacing)
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
    for node_name in INTERNAL_GRID_NODES:
        if node_name not in eligible_names:
            raise RuntimeError(f"{node_name} is not order-control eligible.")
    world.set_order_control_for_nodes(
        INTERNAL_GRID_NODES,
        order_control_type="time_value",
        transaction_case=None,
    )
    world.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    # Cap stays above every decision until closure. The real end is chosen
    # only after the network is empty. TSIZE already includes horizon 30.
    world.order_control_tvt_evaluation_end_timestep = LAST_TVT_DECISION_TIMESTEP_CAP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    return world


def add_vehicles_to_world(world: World, vot_records: list[VehicleVotRecord]) -> None:
    for record in vot_records:
        if record.participates_in_order_exchange is True:
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
        elif record.participates_in_order_exchange is False:
            if record.declared_vot_per_second is not None:
                raise RuntimeError(f"{record.vehicle_name} nonparticipating declared VOT is not empty.")
            world.addVehicle(
                record.origin,
                record.destination,
                record.departure_time,
                name=record.vehicle_name,
                vot_true=record.true_vot_per_second,
                vot_declared=None,
                participates_in_order_exchange=False,
            )
        else:
            raise RuntimeError(f"{record.vehicle_name} has an invalid participation flag.")


def verify_network_runtime(world: World) -> None:
    if world.DELTAT != 1:
        raise RuntimeError(f"DELTAT is {world.DELTAT!r}; this trial requires 1.")
    if len(world.NODES) != TOTAL_NODE_COUNT:
        raise RuntimeError(f"Node count is {len(world.NODES)}, expected {TOTAL_NODE_COUNT}.")
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
    for link_name, start_node, end_node, length, _signal_group in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        if link.start_node.name != start_node or link.end_node.name != end_node:
            raise RuntimeError(f"Link {link_name} endpoints do not match the 6x6 spec.")
        if link.length != length or length != 200:
            raise RuntimeError(f"Link {link_name} length is {link.length!r}, expected 200.")
        if link.number_of_lanes != NUMBER_OF_LANES:
            raise RuntimeError(f"Link {link_name} lane count is not 1.")
        if link.merge_priority != MERGE_PRIORITY:
            raise RuntimeError(f"Link {link_name} merge priority is not 1.")
        if not math.isclose(link.free_flow_speed, FREE_FLOW_SPEED, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"Link {link_name} free-flow speed is not 60/3.6 m/s.")
        if not math.isclose(link.jam_density, JAM_DENSITY, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"Link {link_name} jam density is not 0.2.")
    for node_name in INTERNAL_GRID_NODES:
        node = world.get_node(node_name)
        if node.order_control_clearance_timesteps != CLEARANCE_TIMESTEPS:
            raise RuntimeError(f"{node_name} clearance is not 1.")
    if world.order_control_tvt_baseline_horizon_steps != BASELINE_HORIZON_STEPS:
        raise RuntimeError("Baseline horizon is not 30.")
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("Candidate visit limit is not 10.")
    if world.order_control_tvt_evaluation_end_timestep != LAST_TVT_DECISION_TIMESTEP_CAP:
        raise RuntimeError("Evaluation cap was not installed.")
    required_tsize = LAST_TVT_DECISION_TIMESTEP_CAP + BASELINE_HORIZON_STEPS + 1
    if world.TSIZE < required_tsize:
        raise RuntimeError(
            f"TSIZE {world.TSIZE} does not leave baseline horizon {BASELINE_HORIZON_STEPS} "
            f"after decision cap {LAST_TVT_DECISION_TIMESTEP_CAP}."
        )


# ---------------------------------------------------------------------------
# 5. Continue until the network is empty, then close evaluation
# ---------------------------------------------------------------------------

def _state_counts(world: World) -> dict[str, int]:
    counts = {"home": 0, "wait": 0, "run": 0, "end": 0}
    for vehicle in world.VEHICLES.values():
        state_value = vehicle.state
        if state_value not in counts:
            raise RuntimeError(f"Vehicle {vehicle.name} has unexpected state {state_value!r}.")
        counts[state_value] = counts[state_value] + 1
    return counts


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
    if counts["run"] != 0 or counts["wait"] != 0 or counts["home"] != 0:
        return False
    _internal_count, _connector_count, total_count = _link_vehicle_counts(world)
    if total_count != 0:
        return False
    return True


def _ready_to_close(world: World) -> bool:
    """True when every trip has already ended before this timestep is simulated."""
    if type(world.T) is not int:
        raise RuntimeError(f"World.T is {world.T!r}.")
    if world.T <= DEPARTURE_END:
        return False
    return _traffic_is_clear(world)


def _close_evaluation_at_current_timestep(world: World) -> None:
    """Make the current timestep the last TVT decision, then let production finalize.

    World.T is not written. exec_simulation runs this one timestep and then
    performs the normal evaluation-end finalization because T becomes
    evaluation_end + 1. TSIZE was allocated so this decision still has
    baseline horizon 30.
    """
    closing_timestep = world.T
    if type(closing_timestep) is not int:
        raise RuntimeError(f"Closing timestep is {closing_timestep!r}.")
    if closing_timestep > LAST_TVT_DECISION_TIMESTEP_CAP:
        raise RuntimeError(
            f"Closing timestep {closing_timestep} is above the safe cap "
            f"{LAST_TVT_DECISION_TIMESTEP_CAP}."
        )
    required_tsize = closing_timestep + BASELINE_HORIZON_STEPS + 1
    if world.TSIZE < required_tsize:
        raise RuntimeError(
            f"TSIZE {world.TSIZE} cannot hold baseline horizon {BASELINE_HORIZON_STEPS} "
            f"after closing decision {closing_timestep}."
        )
    world.order_control_tvt_evaluation_end_timestep = closing_timestep
    finished = world.exec_simulation()
    if finished != 1:
        raise RuntimeError("Closing exec_simulation did not finish evaluation.")
    if world.T != closing_timestep + 1:
        raise RuntimeError(
            f"After closure, World.T is {world.T}, expected {closing_timestep + 1}."
        )


def run_until_full_completion(world: World) -> None:
    """Step with until_t so an empty network is not simulated out to the cap.

    until_t is the documented UXsim continuation argument. This function does
    not assign World.T. The initial evaluation cap stays in place until the
    network is already clear, so every earlier decision keeps horizon 30.
    """
    if world.DELTAT != 1:
        raise RuntimeError(f"Continuation requires DELTAT=1, got {world.DELTAT!r}.")
    while world.T <= LAST_TVT_DECISION_TIMESTEP_CAP:
        if _ready_to_close(world):
            _close_evaluation_at_current_timestep(world)
            return
        before = world.T
        until_t = float(before) * float(world.DELTAT)
        world.exec_simulation(until_t=until_t)
        if world.T <= before:
            raise RuntimeError("exec_simulation did not advance World.T.")
        if world.T > world.order_control_tvt_evaluation_end_timestep:
            return
    raise RuntimeError(
        "Simulation left the safe timestep cap without a production evaluation end."
    )


def verify_full_completion(world: World, plans: list[dict]) -> dict:
    counts = _state_counts(world)
    if len(world.VEHICLES) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle count is {len(world.VEHICLES)}, expected 3000.")
    if sum(counts.values()) != NUM_VEHICLES:
        raise RuntimeError("Vehicle state counts do not sum to 3000.")
    if counts["end"] != NUM_VEHICLES:
        raise RuntimeError(f"end count is {counts['end']}, expected 3000. counts={counts}.")
    if counts["run"] != 0 or counts["wait"] != 0 or counts["home"] != 0:
        raise RuntimeError(f"Network is not clear. counts={counts}.")
    internal_count, connector_count, total_count = _link_vehicle_counts(world)
    if internal_count != 0 or connector_count != 0 or total_count != 0:
        raise RuntimeError(
            "Links still hold vehicles: "
            f"internal={internal_count}, connector={connector_count}, total={total_count}."
        )
    evaluation_end = world.order_control_tvt_evaluation_end_timestep
    if type(evaluation_end) is not int:
        raise RuntimeError(f"Evaluation end is {evaluation_end!r}.")
    if world.T != evaluation_end + 1:
        raise RuntimeError(
            f"World.T {world.T} is not one step after evaluation end {evaluation_end}."
        )
    if evaluation_end <= DEPARTURE_END:
        raise RuntimeError(
            f"Evaluation end {evaluation_end} does not cover the last planned departure."
        )
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
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    for field_name in (
        "evaluation_end_unobserved_finalized_timestep",
        "trade_ex_post_evaluation_finalized_timestep",
        "individual_ex_post_evaluation_finalized_timestep",
    ):
        actual = getattr(registry, field_name)
        if actual != evaluation_end:
            raise RuntimeError(
                f"Registry {field_name} is {actual!r}, expected evaluation end {evaluation_end}."
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
        "traffic_clearance_completed": True,
        "full_trip_completion": True,
    }


# ---------------------------------------------------------------------------
# 6. Research summaries and audit verification
# ---------------------------------------------------------------------------

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
    ordered = {}
    for visit_id in sorted(visit_id_counts):
        ordered[visit_id] = visit_id_counts[visit_id]
    return {
        "visit_id_counts": ordered,
        "maximum_visit_id": max_visit_id,
    }


def collect_transaction_counts_by_node(bundle) -> dict[str, int]:
    counts = {}
    for name in INTERNAL_GRID_NODES:
        counts[name] = 0
    for transaction in bundle.transactions:
        node_name = transaction.node_name
        if node_name not in counts:
            raise RuntimeError(f"Transaction node {node_name!r} is not an internal TVT-MP node.")
        counts[node_name] = counts[node_name] + 1
    return counts


def _max_actual_passage_timestep(bundle, final_world_t: int) -> int:
    maximum = None
    for visit in bundle.visits:
        if visit.actual_passage_timestep is None:
            raise RuntimeError(
                "Trade-scope visit has no actual_passage_timestep after full completion: "
                f"{visit.vehicle_name}:{visit.visit_id} at {visit.node_name}."
            )
        value = visit.actual_passage_timestep
        if type(value) is not int:
            raise RuntimeError(f"actual_passage_timestep is {value!r}.")
        if maximum is None or value > maximum:
            maximum = value
    if maximum is None:
        raise RuntimeError("Research output has no visits, so full-completion audit cannot be checked.")
    if final_world_t <= maximum:
        raise RuntimeError(
            f"Final World.T {final_world_t} is not after final actual passage {maximum}."
        )
    return maximum


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def count_csv_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        count = 0
        for _row in reader:
            count = count + 1
        return count


def read_csv_dict_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(dict(row))
        return rows


def _parse_int_cell(value: str, label: str, row_index: int) -> int:
    if value == "":
        raise RuntimeError(f"{label} row {row_index}: expected an integer, got a blank.")
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"{label} row {row_index}: {value!r} is not an integer.") from error


def verify_full_run_audit_output(directory: Path, bundle, audit_result) -> FullRunAuditSummary:
    transaction_path = directory / TRANSACTION_AUDIT_CSV_NAME
    visit_path = directory / VISIT_AUDIT_CSV_NAME
    if not transaction_path.is_file() or not visit_path.is_file():
        raise RuntimeError("Audit CSV files were not created.")
    research_transaction_rows = count_csv_data_rows(directory / "tvt_mp_transactions.csv")
    research_visit_rows = count_csv_data_rows(directory / "tvt_mp_visits.csv")
    transaction_rows = read_csv_dict_rows(transaction_path)
    visit_rows = read_csv_dict_rows(visit_path)
    if len(transaction_rows) != research_transaction_rows:
        raise RuntimeError(
            f"Transaction audit rows {len(transaction_rows)} != "
            f"tvt_mp_transactions.csv rows {research_transaction_rows}."
        )
    if len(visit_rows) != research_visit_rows:
        raise RuntimeError(
            f"Visit audit rows {len(visit_rows)} != tvt_mp_visits.csv rows {research_visit_rows}."
        )
    if len(audit_result.transaction_rows) != len(transaction_rows):
        raise RuntimeError("Frozen transaction audit count disagrees with the CSV.")
    if len(audit_result.visit_rows) != len(visit_rows):
        raise RuntimeError("Frozen visit audit count disagrees with the CSV.")

    buyer_row_count = 0
    seller_row_count = 0
    nonparticipating_row_count = 0
    actual_arrival_row_count = 0
    fifo_violation_total = 0
    max_party = 0
    max_buyer = 0
    max_seller = 0
    max_nonparticipating = 0

    for index, row in enumerate(transaction_rows, start=1):
        buyer_count = _parse_int_cell(row["buyer_count"], "transaction", index)
        seller_count = _parse_int_cell(row["seller_count"], "transaction", index)
        nonparticipating_count = _parse_int_cell(row["nonparticipating_count"], "transaction", index)
        trade_scope_count = _parse_int_cell(row["trade_scope_count"], "transaction", index)
        if buyer_count + seller_count + nonparticipating_count != trade_scope_count:
            raise RuntimeError(f"Transaction row {index}: role counts do not equal trade_scope_count.")
        fifo_violation_count = _parse_int_cell(row["fifo_violation_count"], "transaction", index)
        if fifo_violation_count != 0:
            raise RuntimeError(f"Transaction row {index}: fifo_violation_count is {fifo_violation_count}.")
        fifo_violation_total = fifo_violation_total + fifo_violation_count
        party_count = _parse_int_cell(row["max_same_inlink_party_count"], "transaction", index)
        buyer_max = _parse_int_cell(row["max_same_inlink_buyer_count"], "transaction", index)
        seller_max = _parse_int_cell(row["max_same_inlink_seller_count"], "transaction", index)
        nonparticipating_max = _parse_int_cell(
            row["max_same_inlink_nonparticipating_count"], "transaction", index
        )
        for count_value, count_label in (
            (party_count, "max_same_inlink_party_count"),
            (buyer_max, "max_same_inlink_buyer_count"),
            (seller_max, "max_same_inlink_seller_count"),
            (nonparticipating_max, "max_same_inlink_nonparticipating_count"),
        ):
            if count_value < 0:
                raise RuntimeError(f"Transaction row {index}: {count_label} is negative.")
        if party_count > max_party:
            max_party = party_count
        if buyer_max > max_buyer:
            max_buyer = buyer_max
        if seller_max > max_seller:
            max_seller = seller_max
        if nonparticipating_max > max_nonparticipating:
            max_nonparticipating = nonparticipating_max

    required_visit_fields = (
        "inlink_name",
        "baseline_arrival_timestep",
        "actual_node_arrival_timestep",
        "baseline_local_rank",
        "post_trade_local_rank",
        "assigned_rank",
        "actual_node_passage_rank",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "actual_passage_timestep",
    )
    for index, row in enumerate(visit_rows, start=1):
        for field_name in required_visit_fields:
            if row[field_name] == "":
                raise RuntimeError(
                    f"Visit row {index} ({row['role']}) is missing {field_name} after full completion."
                )
        actual_arrival = _parse_int_cell(row["actual_node_arrival_timestep"], "visit", index)
        actual_passage = _parse_int_cell(row["actual_passage_timestep"], "visit", index)
        if actual_passage < actual_arrival + 1:
            raise RuntimeError(
                f"Visit row {index}: actual passage {actual_passage} is before "
                f"actual arrival {actual_arrival} + 1."
            )
        actual_arrival_row_count = actual_arrival_row_count + 1
        if row["same_inlink_fifo_preserved"] != "True":
            raise RuntimeError(f"Visit row {index}: same_inlink_fifo_preserved is not True.")
        role = row["role"]
        if role == "buyer":
            buyer_row_count = buyer_row_count + 1
            if row["buyer_value_G_b"] == "" or row["payment_P_b"] == "":
                raise RuntimeError(f"Buyer row {index} is missing G_b or P_b.")
        elif role == "seller":
            seller_row_count = seller_row_count + 1
            if row["seller_required_compensation_R_s"] == "" or row["compensation_C_s"] == "":
                raise RuntimeError(f"Seller row {index} is missing R_s or C_s.")
        elif role == "nonparticipating":
            nonparticipating_row_count = nonparticipating_row_count + 1
            for blank_name in (
                "buyer_value_G_b",
                "seller_required_compensation_R_s",
                "payment_P_b",
                "compensation_C_s",
            ):
                if row[blank_name] != "":
                    raise RuntimeError(
                        f"Nonparticipating row {index}: {blank_name} must be blank."
                    )
        else:
            raise RuntimeError(f"Visit row {index} has unknown role {role!r}.")

    if buyer_row_count < 1 or seller_row_count < 1 or nonparticipating_row_count < 1:
        raise RuntimeError(
            "Audit visits must include buyer, seller, and nonparticipating rows. "
            f"Counts: buyer={buyer_row_count}, seller={seller_row_count}, "
            f"nonparticipating={nonparticipating_row_count}."
        )
    if bundle.scenario[0].transaction_count != len(transaction_rows):
        raise RuntimeError("Scenario transaction_count disagrees with the audit CSV.")
    return FullRunAuditSummary(
        transaction_row_count=len(transaction_rows),
        visit_row_count=len(visit_rows),
        buyer_row_count=buyer_row_count,
        seller_row_count=seller_row_count,
        nonparticipating_row_count=nonparticipating_row_count,
        actual_arrival_row_count=actual_arrival_row_count,
        fifo_violation_total=fifo_violation_total,
        max_same_inlink_party_count=max_party,
        max_same_inlink_buyer_count=max_buyer,
        max_same_inlink_seller_count=max_seller,
        max_same_inlink_nonparticipating_count=max_nonparticipating,
        transaction_csv_sha256=_sha256_file(transaction_path),
        visit_csv_sha256=_sha256_file(visit_path),
    )


# ---------------------------------------------------------------------------
# 7. Output writers
# ---------------------------------------------------------------------------

def _refuse_existing_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "This script does not delete or overwrite it."
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
        "demand_gen_seed",
        "nonparticipation_seed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in vot_records:
            declared = record.declared_vot_per_second
            if declared is None:
                declared_cell = ""
            else:
                declared_cell = declared
            writer.writerow(
                {
                    "vehicle_name": record.vehicle_name,
                    "origin": record.origin,
                    "destination": record.destination,
                    "departure_timestep": record.departure_time,
                    "participates_in_order_exchange": record.participates_in_order_exchange,
                    "true_vot_per_second": record.true_vot_per_second,
                    "declared_vot_per_second": declared_cell,
                    "traffic_seed": TRAFFIC_SEED,
                    "vot_seed": VOT_SEED,
                    "demand_gen_seed": DEMAND_GEN_SEED,
                    "nonparticipation_seed": NONPARTICIPATION_SEED,
                }
            )


def _directory_bytes(directory: Path) -> int:
    total = 0
    for path in directory.iterdir():
        if path.is_file():
            total = total + path.stat().st_size
    return total


def write_manifest_json(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(path: Path, lines: list[str]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _research_csv_sha256(directory: Path) -> dict[str, str]:
    digests = {}
    for name in RESEARCH_CSV_NAMES:
        digests[name] = _sha256_file(directory / name)
    return digests


# ---------------------------------------------------------------------------
# 8. Static contract
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


def _assert_static_function_does_not_run(function_node: ast.FunctionDef) -> None:
    forbidden = {
        "exec_simulation",
        "mkdir",
        "generate_vehicle_plans",
        "build_world_and_network",
        "addVehicle",
        "World",
        "build_tvt_mp_research_output",
        "write_tvt_mp_research_output_csv",
        "write_tvt_mp_full_run_audit_csv",
        "install_tvt_mp_full_run_audit",
        "finalize_tvt_mp_full_run_audit",
        "evaluate_network_wide_waiting_time",
        "evaluate_tvt_mp_network_wide_waiting_time",
        "_run_trial",
    }
    for name in _call_names(function_node):
        if name in forbidden:
            raise RuntimeError(f"Static validation must not call {name}.")


def _assert_no_trial_script_import(tree: ast.Module) -> None:
    for node in tree.body:
        modules = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                modules.append(node.module)
        for module_name in modules:
            if module_name.startswith("run_tvt_mp_") or module_name.startswith("run_fcfs_"):
                raise RuntimeError(f"This script must not import trial module {module_name!r}.")


def _assert_no_cprofile_import(tree: ast.Module) -> None:
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "cProfile" or alias.name.endswith(".cProfile"):
                    raise RuntimeError("cProfile import is not allowed.")
        if isinstance(node, ast.ImportFrom) and node.module == "cProfile":
            raise RuntimeError("cProfile import is not allowed.")


def _assert_no_production_hook_assignment(tree: ast.Module) -> None:
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
        for target in targets:
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr in (
                "run_tvt_mp_driver",
                "record_order_control_node_arrival",
            ):
                raise RuntimeError(
                    "This script must not install its own driver or arrival hook."
                )


def _assert_run_order(tree: ast.Module) -> None:
    run_function = _function_node(tree, "_run_trial")
    if run_function is None:
        raise RuntimeError("_run_trial is missing.")
    interesting = []
    for node in ast.walk(run_function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        else:
            continue
        if name in (
            "install_tvt_mp_full_run_audit",
            "run_until_full_completion",
            "verify_full_completion",
            "evaluate_tvt_mp_network_wide_waiting_time",
            "build_tvt_mp_research_output",
            "finalize_tvt_mp_full_run_audit",
            "write_tvt_mp_research_output_csv",
            "write_tvt_mp_full_run_audit_csv",
        ):
            interesting.append((node.lineno, name))
    interesting.sort(key=lambda item: item[0])
    names = []
    for _line, name in interesting:
        names.append(name)
    expected = [
        "install_tvt_mp_full_run_audit",
        "run_until_full_completion",
        "verify_full_completion",
        "evaluate_tvt_mp_network_wide_waiting_time",
        "build_tvt_mp_research_output",
        "finalize_tvt_mp_full_run_audit",
        "write_tvt_mp_research_output_csv",
        "write_tvt_mp_full_run_audit_csv",
    ]
    if names != expected:
        raise RuntimeError(f"Trial call order is {names}, expected {expected}.")
    for node in ast.walk(run_function):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "T":
                raise RuntimeError("_run_trial must not assign World.T.")


def _assert_continuation_uses_until_t(tree: ast.Module) -> None:
    function_node = _function_node(tree, "run_until_full_completion")
    if function_node is None:
        raise RuntimeError("run_until_full_completion is missing.")
    saw_until = False
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "exec_simulation":
            continue
        for keyword in node.keywords:
            if keyword.arg == "until_t":
                saw_until = True
    if saw_until is not True:
        raise RuntimeError("Full completion must continue with exec_simulation(until_t=...).")
    close_function = _function_node(tree, "_close_evaluation_at_current_timestep")
    if close_function is None:
        raise RuntimeError("Closing evaluation function is missing.")
    saw_horizon_name = False
    for node in ast.walk(close_function):
        if isinstance(node, ast.Name) and node.id == "BASELINE_HORIZON_STEPS":
            saw_horizon_name = True
    if saw_horizon_name is not True:
        raise RuntimeError("Closing evaluation must check the baseline horizon.")


def _assert_addlink_has_no_capacity_keywords(tree: ast.Module) -> None:
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
                raise RuntimeError(f"addLink must not pass {keyword.arg}.")
            if keyword.arg in ("specified_route", "route"):
                raise RuntimeError("addLink must not set a route.")


def _assert_no_destructive_delete_calls(tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            attr = func.attr
            if attr in ("unlink", "rmdir"):
                raise RuntimeError(
                    f"Destructive path call .{attr}() is not allowed at line {node.lineno}."
                )
            if attr == "rmtree" and isinstance(func.value, ast.Name):
                if func.value.id == "shutil":
                    raise RuntimeError(
                        "shutil.rmtree() is not allowed at "
                        f"line {node.lineno}."
                    )
            if attr in ("remove", "unlink") and isinstance(func.value, ast.Name):
                if func.value.id == "os":
                    raise RuntimeError(
                        f"os.{attr}() is not allowed at line {node.lineno}."
                    )
        elif isinstance(func, ast.Name) and func.id == "rmtree":
            raise RuntimeError(
                f"rmtree() is not allowed at line {node.lineno}."
            )


def _assert_free_route_and_participation(tree: ast.Module) -> None:
    add_function = _function_node(tree, "add_vehicles_to_world")
    if add_function is None:
        raise RuntimeError("add_vehicles_to_world is missing.")
    for node in ast.walk(add_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "addVehicle":
            continue
        for keyword in node.keywords:
            if keyword.arg in ("specified_route", "route"):
                raise RuntimeError("addVehicle must not set specified_route.")


def validate_static_contract() -> None:
    if SCENARIO_NAME != TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Scenario name and output directory name must match.")
    if "awt_awwt_od_reference_validation" not in SCENARIO_NAME:
        raise RuntimeError("Scenario name must identify the OD AWT and AWWT validation.")
    if "departure_999" not in SCENARIO_NAME:
        raise RuntimeError("Scenario name must identify departure through T=999.")
    if "nonparticipation_seed_3" not in SCENARIO_NAME:
        raise RuntimeError("Scenario name must identify nonparticipation seed 3.")
    if SCENARIO_NAME == REFERENCE_DIR_NAME:
        raise RuntimeError("New scenario name must differ from the reference directory name.")
    if TRIAL_OUTPUT_DIR.resolve() == REFERENCE_OUTPUT_DIR.resolve():
        raise RuntimeError("Output directory must differ from the reference directory.")
    if PRODUCTION_DECISION_WINDOW_STEPS != 6:
        raise RuntimeError("Production decision window recorded here must be 6.")
    if OD_AWT_AWWT_COMPARED_TO_REFERENCE is not False:
        raise RuntimeError("This script must not claim OD AWT or AWWT equality.")
    if BASELINE_CANDIDATE_SHARED_SNAPSHOT_PRODUCTION_IS_ACTIVE is not True:
        raise RuntimeError("Shared-snapshot acceptance flag must be true.")
    if EXPECTED_CSV_DATA_ROW_COUNTS != {
        "tvt_mp_transactions.csv": 4298,
        "tvt_mp_visits.csv": 11871,
        "tvt_mp_vehicles.csv": 3000,
        "tvt_mp_nodes.csv": 36,
        "tvt_mp_scenario.csv": 1,
        "tvt_mp_transaction_audit.csv": 4298,
        "tvt_mp_visit_audit.csv": 11871,
        "vehicle_vot.csv": 3000,
    }:
        raise RuntimeError("Expected CSV row counts changed.")
    if PREVIOUS_EXEC_SIMULATION_SECONDS != 65093.892005:
        raise RuntimeError("Previous exec_simulation seconds must stay 65093.892005.")
    if NUM_VEHICLES != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if NONPARTICIPATING_VEHICLE_COUNT != 600:
        raise RuntimeError("Nonparticipating count must be 600.")
    if PARTICIPATING_VEHICLE_COUNT != 2400:
        raise RuntimeError("Participating count must be 2400.")
    if PARTICIPATING_VEHICLE_COUNT + NONPARTICIPATING_VEHICLE_COUNT != NUM_VEHICLES:
        raise RuntimeError("Participation counts must sum to 3000.")
    if NONPARTICIPATING_VEHICLE_COUNT / NUM_VEHICLES != 0.2:
        raise RuntimeError("600/3000 must be 20%.")
    if NONPARTICIPATION_SEED != 3:
        raise RuntimeError("Nonparticipation seed must be 3.")
    if TRAFFIC_SEED != 0 or DEMAND_GEN_SEED != 42 or VOT_SEED != 1:
        raise RuntimeError("Seeds must be traffic 0, demand 42, VOT 1.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 999:
        raise RuntimeError("Departure window must be 0..999.")
    if EXPECTED_VEHICLE_PLAN_SHA256 != (
        "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
    ):
        raise RuntimeError("Vehicle plan SHA-256 contract changed.")
    if INTERNAL_LINK_LENGTH != 200 or OD_CONNECTOR_LENGTH != 200:
        raise RuntimeError("All links must be 200 m.")
    if FREE_FLOW_SPEED_KMH != 60:
        raise RuntimeError("Free-flow speed must be 60 km/h.")
    if not math.isclose(FREE_FLOW_SPEED, 60 / 3.6, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("FREE_FLOW_SPEED must be 60/3.6.")
    if JAM_DENSITY != 0.2:
        raise RuntimeError("Jam density must be 0.2.")
    if MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Candidate limit must be 10.")
    if BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("Baseline horizon must be 30.")
    if CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Clearance must be 1.")
    if WORLD_COPY_RECURSION_LIMIT != 50000:
        raise RuntimeError("Recursion limit must be 50000.")
    if LAST_TVT_DECISION_TIMESTEP_CAP < 5000:
        raise RuntimeError("The safe decision cap must be at least 5000.")
    if INTERNAL_TSIZE != LAST_TVT_DECISION_TIMESTEP_CAP + BASELINE_HORIZON_STEPS + 1:
        raise RuntimeError("INTERNAL_TSIZE must be cap + horizon + 1.")
    if INTERNAL_TSIZE == 1030:
        raise RuntimeError("This trial must not keep the fixed T=999 internal size.")
    if SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("specified_route must stay unused.")
    if ROUTE_ASSIGNMENT_MODE != "uxsim_free_route_choice":
        raise RuntimeError("Route mode must be free route choice.")
    if PROFILING_RUN is not False:
        raise RuntimeError("PROFILING_RUN must be False.")
    if SHOW_PROGRESS_DELTAT != 600:
        raise RuntimeError("SHOW_PROGRESS_DELTAT must be 600.")
    if len(FORMAL_OUTPUT_FILE_NAMES) != 10:
        raise RuntimeError("Formal output must be the 10 named files.")
    if len(INTERNAL_GRID_NODES) != 36 or len(EXTERNAL_OD_NODES) != 24:
        raise RuntimeError("Node lists must be 36 internal and 24 external.")
    if len(INTERNAL_LINK_SPECS) != 120 or len(OD_CONNECTOR_LINK_SPECS) != 48:
        raise RuntimeError("Link specs must be 120 internal and 48 connectors.")
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {TRIAL_OUTPUT_DIR}.")
    for required_manifest_key in (
        "production_unchanged_by_script",
        "fcfs_pretrial_completion_timestep_not_assumed",
        "formal_output_file_names",
    ):
        if required_manifest_key not in MANIFEST_RESEARCH_RESULT_KEYS:
            raise RuntimeError(
                f"{required_manifest_key} must be in MANIFEST_RESEARCH_RESULT_KEYS."
            )
        if required_manifest_key in MANIFEST_KEYS_EXCLUDED_FROM_REFERENCE:
            raise RuntimeError(
                f"{required_manifest_key} must not be excluded from reference comparison."
            )

    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    _assert_static_function_does_not_run(validator)
    _assert_no_trial_script_import(tree)
    _assert_no_cprofile_import(tree)
    _assert_no_production_hook_assignment(tree)
    _assert_run_order(tree)
    _assert_continuation_uses_until_t(tree)
    _assert_addlink_has_no_capacity_keywords(tree)
    _assert_free_route_and_participation(tree)
    if _function_node(tree, "verify_full_run_audit_output") is None:
        raise RuntimeError("Audit verification function is missing.")
    if _function_node(tree, "verify_full_completion") is None:
        raise RuntimeError("Full-completion verification function is missing.")
    if _function_node(tree, "compare_full_completion_reference") is None:
        raise RuntimeError("Reference comparison function is missing.")
    if _function_node(tree, "_require_reference_directory") is None:
        raise RuntimeError("Reference directory guard is missing.")
    build_function = _function_node(tree, "build_world_and_network")
    if build_function is None:
        raise RuntimeError("build_world_and_network is missing.")
    for node in ast.walk(build_function):
        if isinstance(node, ast.Attribute) and "decision_window" in node.attr:
            raise RuntimeError("This script must not override the production decision window.")
    _assert_no_destructive_delete_calls(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "git":
            raise RuntimeError("This script must not call git.")
    run_function = _function_node(tree, "_run_trial")
    if run_function is None:
        raise RuntimeError("_run_trial is missing.")
    ordered_calls = []
    for node in ast.walk(run_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id in (
            "write_manifest_json",
            "compare_full_completion_reference",
        ):
            ordered_calls.append((node.lineno, node.func.id))
    ordered_calls.sort(key=lambda item: item[0])
    ordered_names = []
    for _line, name in ordered_calls:
        ordered_names.append(name)
    if "write_manifest_json" not in ordered_names or "compare_full_completion_reference" not in ordered_names:
        raise RuntimeError("_run_trial must write the manifest and then compare the reference.")
    if ordered_names.index("compare_full_completion_reference") < ordered_names.index(
        "write_manifest_json"
    ):
        raise RuntimeError("Reference comparison must run after the manifest is written.")
    _require_reference_directory()
    if METHOD_NAME != "tvt_mp":
        raise RuntimeError("method_name must be tvt_mp.")
    if PARTICIPATING_COHORT != "tvt_participating_cohort":
        raise RuntimeError("Participating evaluation cohort name changed.")
    if NONPARTICIPATING_COHORT != "tvt_nonparticipating_cohort":
        raise RuntimeError("Nonparticipating evaluation cohort name changed.")
    if PARTICIPATING_STATUS != "participating" or NONPARTICIPATING_STATUS != "nonparticipating":
        raise RuntimeError("Method-specific participation status labels changed.")
    if WAITING_TIME_SUMMARY_JSON_NAME != "network_wide_waiting_time_summary.json":
        raise RuntimeError("Waiting-time summary must use the FCFS json file name.")
    formal_names = set(FORMAL_OUTPUT_FILE_NAMES)
    for extra_name in WAITING_TIME_OUTPUT_FILE_NAMES:
        if extra_name in formal_names:
            raise RuntimeError(f"{extra_name} must stay outside the ten TVT-MP formal files.")
    _assert_waiting_time_call_contract(tree)
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "EVALUATION_END_TIMESTEP":
            raise RuntimeError(
                "This trial must not stop at a fixed EVALUATION_END_TIMESTEP."
            )


def _assert_waiting_time_call_contract(tree: ast.Module) -> None:
    """Check the evaluation call by AST, not by searching the source text."""
    evaluate_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "evaluate_network_wide_waiting_time":
            evaluate_calls.append(node)
    if len(evaluate_calls) != 1:
        raise RuntimeError(
            "evaluate_network_wide_waiting_time must be called once. "
            f"found {len(evaluate_calls)}."
        )
    call = evaluate_calls[0]
    method_keyword = None
    for keyword in call.keywords:
        if keyword.arg == "method_name":
            method_keyword = keyword
    if method_keyword is None or not isinstance(method_keyword.value, ast.Name):
        raise RuntimeError("The evaluation call must pass method_name=METHOD_NAME.")
    if method_keyword.value.id != "METHOD_NAME":
        raise RuntimeError("The evaluation call must pass method_name=METHOD_NAME.")
    helper = _function_node(tree, "evaluate_tvt_mp_network_wide_waiting_time")
    if helper is None:
        raise RuntimeError("evaluate_tvt_mp_network_wide_waiting_time is missing.")
    helper_calls = _call_names(helper)
    if helper_calls.count("evaluate_network_wide_waiting_time") != 1:
        raise RuntimeError("The waiting-time helper must call the evaluator once.")
    if "exec_simulation" in helper_calls or "run_until_full_completion" in helper_calls:
        raise RuntimeError("The waiting-time helper must not run the simulation.")
    run_function = _function_node(tree, "_run_trial")
    if run_function is None:
        raise RuntimeError("_run_trial is missing.")
    run_calls = []
    for node in ast.walk(run_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            run_calls.append((node.lineno, node.func.id))
    run_calls.sort(key=lambda item: item[0])
    run_names = []
    for _line, name in run_calls:
        run_names.append(name)
    if run_names.count("evaluate_tvt_mp_network_wide_waiting_time") != 1:
        raise RuntimeError("_run_trial must call the waiting-time helper once.")
    if run_names.count("verify_full_completion") != 1:
        raise RuntimeError("_run_trial must call verify_full_completion once.")
    if run_names.count("exec_simulation") != 0:
        raise RuntimeError("_run_trial must not call exec_simulation itself.")
    if run_names.index("verify_full_completion") > run_names.index(
        "evaluate_tvt_mp_network_wide_waiting_time"
    ):
        raise RuntimeError("Waiting-time evaluation must follow full-completion verification.")
    if "verify_network_wide_waiting_time_result" not in run_names:
        raise RuntimeError("_run_trial must audit the waiting-time result.")
    if run_names.index("evaluate_tvt_mp_network_wide_waiting_time") > run_names.index(
        "verify_network_wide_waiting_time_result"
    ):
        raise RuntimeError("Waiting-time audit must follow the evaluation call.")
    ledger_function = _function_node(tree, "build_waiting_time_ledgers")
    if ledger_function is None:
        raise RuntimeError("build_waiting_time_ledgers is missing.")
    if _function_node(tree, "write_network_wide_waiting_time_outputs") is None:
        raise RuntimeError("Waiting-time CSV writer is missing.")


# ---------------------------------------------------------------------------
# 9. Reference comparison after the ten formal files exist
# ---------------------------------------------------------------------------

def _require_reference_directory() -> None:
    if REFERENCE_OUTPUT_DIR.resolve() == TRIAL_OUTPUT_DIR.resolve():
        raise RuntimeError("Reference directory and new output directory are the same.")
    if not REFERENCE_OUTPUT_DIR.is_dir():
        raise RuntimeError(f"Reference directory is missing: {REFERENCE_OUTPUT_DIR}")
    for name in FORMAL_OUTPUT_FILE_NAMES:
        path = REFERENCE_OUTPUT_DIR / name
        if not path.is_file():
            raise RuntimeError(f"Reference file is missing: {path}")


def _read_csv_table(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = []
        for row in reader:
            rows.append(list(row))
    if len(rows) == 0:
        raise RuntimeError(f"CSV is empty: {path}")
    return rows[0], rows[1:]


def _csv_first_difference(filename: str, *, ignore_scenario_name: bool) -> dict | None:
    reference_header, reference_rows = _read_csv_table(REFERENCE_OUTPUT_DIR / filename)
    new_header, new_rows = _read_csv_table(TRIAL_OUTPUT_DIR / filename)
    expected_rows = EXPECTED_CSV_DATA_ROW_COUNTS[filename]
    if reference_header != new_header:
        return {
            "file": filename,
            "row": 0,
            "column": "<header>",
            "reference": reference_header,
            "new": new_header,
        }
    if RESEARCH_CSV_SCENARIO_COLUMN in reference_header:
        if ignore_scenario_name is not True:
            raise RuntimeError(
                f"{filename} contains {RESEARCH_CSV_SCENARIO_COLUMN} "
                "but this comparison was not told to ignore that column."
            )
    elif ignore_scenario_name is True:
        raise RuntimeError(
            f"{filename} has no {RESEARCH_CSV_SCENARIO_COLUMN} column to exclude."
        )
    if (
        len(reference_rows) != expected_rows
        or len(new_rows) != expected_rows
    ):
        return {
            "file": filename,
            "row": None,
            "column": "<data_row_count>",
            "reference": len(reference_rows),
            "new": len(new_rows),
            "expected": expected_rows,
        }
    for row_number, (reference_row, new_row) in enumerate(
        zip(reference_rows, new_rows),
        start=1,
    ):
        if len(reference_row) != len(reference_header) or len(new_row) != len(new_header):
            return {
                "file": filename,
                "row": row_number,
                "column": "<column_count>",
                "reference": len(reference_row),
                "new": len(new_row),
            }
        for column_index, column_name in enumerate(reference_header):
            if ignore_scenario_name and column_name == RESEARCH_CSV_SCENARIO_COLUMN:
                continue
            if reference_row[column_index] != new_row[column_index]:
                return {
                    "file": filename,
                    "row": row_number,
                    "column": column_name,
                    "reference": reference_row[column_index],
                    "new": new_row[column_index],
                }
    return None


def _first_nested_difference(path: str, reference_value, new_value):
    if type(reference_value) is not type(new_value):
        return {
            "key": path,
            "reference": reference_value,
            "new": new_value,
        }
    if type(reference_value) is dict:
        reference_keys = list(reference_value)
        new_keys = list(new_value)
        if reference_keys != new_keys:
            return {
                "key": path,
                "reference": reference_keys,
                "new": new_keys,
            }
        for key in reference_keys:
            nested = _first_nested_difference(
                f"{path}.{key}",
                reference_value[key],
                new_value[key],
            )
            if nested is not None:
                return nested
        return None
    if type(reference_value) is list:
        if len(reference_value) != len(new_value):
            return {
                "key": path,
                "reference": reference_value,
                "new": new_value,
            }
        for index, (reference_item, new_item) in enumerate(
            zip(reference_value, new_value)
        ):
            nested = _first_nested_difference(
                f"{path}[{index}]",
                reference_item,
                new_item,
            )
            if nested is not None:
                return nested
        return None
    if reference_value != new_value:
        return {
            "key": path,
            "reference": reference_value,
            "new": new_value,
        }
    return None


def _manifest_research_difference(reference_manifest: dict, new_manifest: dict) -> dict | None:
    for key in MANIFEST_RESEARCH_RESULT_KEYS:
        if key not in reference_manifest or key not in new_manifest:
            return {
                "key": key,
                "reference": reference_manifest.get(key, "<missing>"),
                "new": new_manifest.get(key, "<missing>"),
            }
        nested = _first_nested_difference(
            key,
            reference_manifest[key],
            new_manifest[key],
        )
        if nested is not None:
            return nested
    if "shared_serialization_production_is_active" in reference_manifest:
        nested = _first_nested_difference(
            "shared_serialization_production_is_active",
            reference_manifest["shared_serialization_production_is_active"],
            new_manifest["shared_serialization_production_is_active"],
        )
        if nested is not None:
            return nested
    return None


def compare_full_completion_reference(exec_simulation_seconds: float) -> dict:
    """Read finished files only. Does not change World, ledgers, or the reference."""
    _require_reference_directory()
    if OD_AWT_AWWT_COMPARED_TO_REFERENCE is not False:
        raise RuntimeError("This script must not claim OD AWT or AWWT equality.")
    if BASELINE_CANDIDATE_SHARED_SNAPSHOT_PRODUCTION_IS_ACTIVE is not True:
        raise RuntimeError(
            "baseline_candidate_shared_snapshot_production_is_active must be true."
        )
    reference_manifest = json.loads(
        (REFERENCE_OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    new_manifest = json.loads(
        (TRIAL_OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    if new_manifest.get("baseline_candidate_shared_snapshot_production_is_active") is not True:
        raise RuntimeError(
            "New manifest must record baseline_candidate_shared_snapshot_production_is_active true."
        )
    if new_manifest.get("od_awt_awwt_compared_to_reference") is not False:
        raise RuntimeError("New manifest must not claim an AWT or AWWT comparison.")
    if new_manifest.get("shared_serialization_production_is_active") is not True:
        raise RuntimeError(
            "New manifest shared_serialization_production_is_active must be true."
        )

    csv_reports = {}
    research_equal = True
    audit_equal = True
    vot_equal = True
    first_difference = None
    for filename in RESEARCH_CSV_NAMES:
        difference = _csv_first_difference(filename, ignore_scenario_name=True)
        equal = difference is None
        csv_reports[filename] = {
            "equal": equal,
            "reference_data_rows": EXPECTED_CSV_DATA_ROW_COUNTS[filename] if equal else None,
            "new_data_rows": EXPECTED_CSV_DATA_ROW_COUNTS[filename] if equal else None,
            "scenario_name_column_excluded": True,
            "first_difference": difference,
        }
        if equal is not True:
            research_equal = False
            if first_difference is None:
                first_difference = difference
    for filename in AUDIT_CSV_NAMES:
        difference = _csv_first_difference(filename, ignore_scenario_name=False)
        equal = difference is None
        csv_reports[filename] = {
            "equal": equal,
            "reference_data_rows": EXPECTED_CSV_DATA_ROW_COUNTS[filename] if equal else None,
            "new_data_rows": EXPECTED_CSV_DATA_ROW_COUNTS[filename] if equal else None,
            "scenario_name_column_excluded": False,
            "first_difference": difference,
        }
        if equal is not True:
            audit_equal = False
            if first_difference is None:
                first_difference = difference
    vot_difference = _csv_first_difference("vehicle_vot.csv", ignore_scenario_name=False)
    vot_equal = vot_difference is None
    csv_reports["vehicle_vot.csv"] = {
        "equal": vot_equal,
        "reference_data_rows": EXPECTED_CSV_DATA_ROW_COUNTS["vehicle_vot.csv"] if vot_equal else None,
        "new_data_rows": EXPECTED_CSV_DATA_ROW_COUNTS["vehicle_vot.csv"] if vot_equal else None,
        "scenario_name_column_excluded": False,
        "first_difference": vot_difference,
    }
    if vot_equal is not True and first_difference is None:
        first_difference = vot_difference

    for filename, report in csv_reports.items():
        if report["equal"] is True:
            continue
        reference_header, reference_rows = _read_csv_table(REFERENCE_OUTPUT_DIR / filename)
        _new_header, new_rows = _read_csv_table(TRIAL_OUTPUT_DIR / filename)
        report["reference_data_rows"] = len(reference_rows)
        report["new_data_rows"] = len(new_rows)
        del reference_header

    manifest_difference = _manifest_research_difference(reference_manifest, new_manifest)
    manifest_equal = manifest_difference is None
    if manifest_equal is not True and first_difference is None:
        first_difference = manifest_difference

    if exec_simulation_seconds <= 0.0:
        raise RuntimeError("exec_simulation seconds must be positive before speedup is reported.")
    speedup = PREVIOUS_EXEC_SIMULATION_SECONDS / exec_simulation_seconds
    reduction_percent = (
        (PREVIOUS_EXEC_SIMULATION_SECONDS - exec_simulation_seconds)
        / PREVIOUS_EXEC_SIMULATION_SECONDS
        * 100.0
    )
    full_match = (
        research_equal is True
        and audit_equal is True
        and vot_equal is True
        and manifest_equal is True
    )
    hash_keys = (
        "participation_assignment_sha256",
        "nonparticipating_name_sha256",
        "participating_name_sha256",
    )
    participation_hashes_equal = True
    for key in hash_keys:
        if reference_manifest.get(key) != new_manifest.get(key):
            participation_hashes_equal = False
    reference_has_shared_flag = (
        "shared_serialization_production_is_active" in reference_manifest
    )
    return {
        "diagnostic_only": False,
        "validation_only": True,
        "reference_directory": str(REFERENCE_OUTPUT_DIR),
        "new_directory": str(TRIAL_OUTPUT_DIR),
        "csv_reports": csv_reports,
        "manifest_research_result_keys": list(MANIFEST_RESEARCH_RESULT_KEYS),
        "manifest_keys_excluded_from_reference": list(MANIFEST_KEYS_EXCLUDED_FROM_REFERENCE),
        "manifest_exclusion_note": (
            "scenario_name, timing_seconds, output_directory_bytes_before_manifest, "
            "output_directory, CSV SHA-256 digests, "
            "baseline_candidate_shared_snapshot_production_is_active, "
            "od_awt_awwt_compared_to_reference, and awt_awwt_reference_comparison_note "
            "differ by design between the saved reference run and this validation run. "
            "shared_serialization_production_is_active is compared only when the "
            "reference manifest contains that key. "
            "AWT and AWWT are not compared."
        ),
        "shared_serialization_production_is_active_reference_key_present": (
            reference_has_shared_flag
        ),
        "shared_serialization_production_is_active_new": True,
        "baseline_candidate_shared_snapshot_production_is_active": True,
        "manifest_research_results_equal": manifest_equal,
        "participation_hashes_equal": participation_hashes_equal,
        "all_research_csv_equal": research_equal,
        "all_audit_csv_equal": audit_equal,
        "vehicle_vot_equal": vot_equal,
        "first_difference": first_difference,
        "previous_exec_simulation_seconds": PREVIOUS_EXEC_SIMULATION_SECONDS,
        "exec_simulation_seconds": exec_simulation_seconds,
        "speedup": speedup,
        "runtime_reduction_percentage": reduction_percent,
        "od_awt_awwt_compared_to_reference": False,
        "awt_awwt_reference_comparison_note": AWT_AWWT_REFERENCE_COMPARISON_NOTE,
        "full_completion_reference_match": full_match,
        "formal_production_acceptance_ready": full_match,
    }


def _comparison_text_lines(comparison: dict) -> list[str]:
    lines = [
        "full-completion reference comparison",
        f"diagnostic_only: {comparison['diagnostic_only']}",
        f"validation_only: {comparison['validation_only']}",
        f"reference directory: {comparison['reference_directory']}",
        f"new directory: {comparison['new_directory']}",
        f"all research CSV equal: {comparison['all_research_csv_equal']}",
        f"all audit CSV equal: {comparison['all_audit_csv_equal']}",
        f"vehicle VOT equal: {comparison['vehicle_vot_equal']}",
        "manifest research results equal: "
        f"{comparison['manifest_research_results_equal']}",
        "full-completion reference match: "
        f"{comparison['full_completion_reference_match']}",
        "formal production acceptance ready: "
        f"{comparison['formal_production_acceptance_ready']}",
        "OD AWT/AWWT compared: false",
        comparison["awt_awwt_reference_comparison_note"],
        "performance is informational and is not the acceptance condition",
        f"previous exec_simulation seconds: {PREVIOUS_EXEC_SIMULATION_SECONDS}",
        f"exec_simulation seconds: {comparison['exec_simulation_seconds']}",
        f"speedup: {comparison['speedup']}",
        f"runtime reduction percentage: {comparison['runtime_reduction_percentage']}",
        f"first difference: {comparison['first_difference']!r}",
    ]
    for filename, report in comparison["csv_reports"].items():
        lines.append(
            f"{filename}: equal={report['equal']} "
            f"reference_rows={report['reference_data_rows']} "
            f"new_rows={report['new_data_rows']} "
            f"scenario_name_excluded={report['scenario_name_column_excluded']}"
        )
    return lines


def write_reference_comparison(comparison: dict) -> None:
    json_path = TRIAL_OUTPUT_DIR / COMPARISON_JSON_NAME
    text_path = TRIAL_OUTPUT_DIR / COMPARISON_TXT_NAME
    if json_path.exists() or text_path.exists():
        raise FileExistsError("Refusing to overwrite the reference comparison files.")
    write_manifest_json(json_path, comparison)
    write_run_summary_txt(text_path, _comparison_text_lines(comparison))


# ---------------------------------------------------------------------------
# 10. OD-based waiting time after the finished real World is unchanged
# ---------------------------------------------------------------------------

def _ordered_vehicle_names(plans: list[dict]) -> list[str]:
    names = []
    for plan in plans:
        names.append(plan["name"])
    return names


def _cohort_assignment_digest(
    plans: list[dict],
    cohort_by_name: dict[str, str],
) -> str:
    hasher = hashlib.sha256()
    for plan in plans:
        vehicle_name = plan["name"]
        line = f"{vehicle_name}|{cohort_by_name[vehicle_name]}\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def _participation_status_digest(
    plans: list[dict],
    status_by_name: dict[str, str],
) -> str:
    hasher = hashlib.sha256()
    for plan in plans:
        vehicle_name = plan["name"]
        line = f"{vehicle_name}|{status_by_name[vehicle_name]}\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def build_waiting_time_ledgers(
    vot_records: list[VehicleVotRecord],
) -> tuple[list[str], dict[str, float], dict[str, str], dict[str, str]]:
    """Plan order, true VOT, evaluation cohort, and TVT-MP participation status.

    Cohort labels and participation labels describe the same 2400/600 split.
    They stay in separate mappings because a later FCFS run does not pass a
    method-specific participation status.
    """
    ordered_names = []
    true_vot_by_name = {}
    cohort_by_name = {}
    status_by_name = {}
    participating_count = 0
    nonparticipating_count = 0
    for record in vot_records:
        vehicle_name = record.vehicle_name
        ordered_names.append(vehicle_name)
        true_vot_by_name[vehicle_name] = record.true_vot_per_second
        if record.participates_in_order_exchange is True:
            cohort_by_name[vehicle_name] = PARTICIPATING_COHORT
            status_by_name[vehicle_name] = PARTICIPATING_STATUS
            participating_count = participating_count + 1
        elif record.participates_in_order_exchange is False:
            cohort_by_name[vehicle_name] = NONPARTICIPATING_COHORT
            status_by_name[vehicle_name] = NONPARTICIPATING_STATUS
            nonparticipating_count = nonparticipating_count + 1
        else:
            raise RuntimeError(
                f"{vehicle_name} participation flag is not True or False."
            )
    if len(ordered_names) != NUM_VEHICLES:
        raise RuntimeError(f"Ledger vehicle count is {len(ordered_names)}, expected 3000.")
    if participating_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Participating ledger count is {participating_count}, expected 2400.")
    if nonparticipating_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Nonparticipating ledger count is {nonparticipating_count}, expected 600."
        )
    return ordered_names, true_vot_by_name, cohort_by_name, status_by_name


def build_waiting_time_comparison_metadata(
    plan_audit: dict,
    participation_digest: str,
    nonparticipating_digest: str,
    participating_digest: str,
    completion: dict,
) -> dict:
    return {
        "method_name": METHOD_NAME,
        "scenario_name": SCENARIO_NAME,
        "traffic_seed": TRAFFIC_SEED,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "vot_seed": VOT_SEED,
        "nonparticipation_seed": NONPARTICIPATION_SEED,
        "candidate_visit_limit": MAX_CANDIDATE_VISIT_COUNT,
        "baseline_horizon": BASELINE_HORIZON_STEPS,
        "departure_start": DEPARTURE_START,
        "departure_end": DEPARTURE_END,
        "participating_vehicle_count": PARTICIPATING_VEHICLE_COUNT,
        "nonparticipating_vehicle_count": NONPARTICIPATING_VEHICLE_COUNT,
        "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
        "participation_assignment_sha256": participation_digest,
        "nonparticipating_name_sha256": nonparticipating_digest,
        "participating_name_sha256": participating_digest,
        "final_world_t": completion["final_world_t"],
        "evaluation_end_timestep": completion["evaluation_end_timestep"],
        "full_completion": True,
        "traffic_clearance": True,
    }


def _finished_world_observation(world: World, ordered_names: list[str]) -> tuple:
    """Small read-only snapshot used only to show the evaluator did not move traffic."""
    states = []
    for vehicle_name in ordered_names:
        vehicle = world.VEHICLES[vehicle_name]
        states.append((vehicle_name, vehicle.state))
    link_counts = _link_vehicle_counts(world)
    return (world.T, tuple(states), link_counts)


def evaluate_tvt_mp_network_wide_waiting_time(
    world: World,
    ordered_names: list[str],
    true_vot_by_name: dict[str, float],
    cohort_by_name: dict[str, str],
    status_by_name: dict[str, str],
    vehicle_plan_digest: str,
    comparison_metadata: dict,
):
    """The only call to the production waiting-time evaluator."""
    return evaluate_network_wide_waiting_time(
        real_world=world,
        method_name=METHOD_NAME,
        evaluated_vehicle_names=ordered_names,
        true_vot_per_second_by_vehicle_name=true_vot_by_name,
        evaluation_cohort_by_vehicle_name=cohort_by_name,
        method_specific_participation_status_by_vehicle_name=status_by_name,
        vehicle_plan_digest=vehicle_plan_digest,
        comparison_metadata=comparison_metadata,
    )


def _require_close(left: float, right: float, label: str, abs_tol: float) -> None:
    if left == right:
        return
    if math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=abs_tol):
        return
    raise RuntimeError(
        f"{label} mismatch. left={left!r} right={right!r} abs_tol={abs_tol}."
    )


def _check_one_waiting_time_record(record, deltat: float) -> None:
    od_steps = record.od_based_waiting_time_timesteps
    route_steps = record.route_conditional_waiting_time_timesteps
    detour_steps = record.detour_time_timesteps
    if od_steps < 0 or route_steps < 0 or detour_steps < 0:
        raise RuntimeError(
            f"{record.vehicle_name} has a negative waiting or detour timestep."
        )
    if record.od_based_waiting_time_s < 0.0 or record.route_conditional_waiting_time_s < 0.0:
        raise RuntimeError(f"{record.vehicle_name} has a negative waiting time in seconds.")
    if record.detour_time_s < 0.0:
        raise RuntimeError(f"{record.vehicle_name} has a negative detour time.")
    if od_steps != route_steps + detour_steps:
        raise RuntimeError(
            f"{record.vehicle_name} timestep identity failed. "
            f"od={od_steps} route_conditional={route_steps} detour={detour_steps}."
        )
    if record.actual_trip_timesteps != (
        record.actual_arrival_timestep - record.actual_departure_timestep
    ):
        raise RuntimeError(f"{record.vehicle_name} trip timesteps are not arrival minus departure.")
    if record.actual_arrival_timestep < record.actual_departure_timestep:
        raise RuntimeError(f"{record.vehicle_name} arrives before it departs.")
    _require_close(
        record.actual_travel_time_s,
        record.actual_trip_timesteps * deltat,
        f"{record.vehicle_name} actual travel time versus timestep * DELTAT",
        SECONDS_MATCH_ABS_TOL,
    )
    _require_close(
        record.od_based_waiting_time_s,
        od_steps * deltat,
        f"{record.vehicle_name} OD waiting seconds",
        SECONDS_MATCH_ABS_TOL,
    )
    _require_close(
        record.route_conditional_waiting_time_s,
        route_steps * deltat,
        f"{record.vehicle_name} Route-Conditional waiting seconds",
        SECONDS_MATCH_ABS_TOL,
    )
    _require_close(
        record.detour_time_s,
        detour_steps * deltat,
        f"{record.vehicle_name} detour seconds",
        SECONDS_MATCH_ABS_TOL,
    )
    _require_close(
        record.weighted_od_based_waiting_time,
        record.weighted_route_conditional_waiting_time + record.weighted_detour_time,
        f"{record.vehicle_name} weighted identity",
        WEIGHTED_IDENTITY_ABS_TOL,
    )


def verify_network_wide_waiting_time_result(
    result,
    plans: list[dict],
    ordered_names: list[str],
    true_vot_by_name: dict[str, float],
    cohort_by_name: dict[str, str],
    status_by_name: dict[str, str],
    plan_digest: str,
    participation_digest: str,
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
        raise RuntimeError(f"summary.method_name is {summary.method_name!r}, expected 'tvt_mp'.")
    if result.vehicle_plan_digest != plan_digest:
        raise RuntimeError("Waiting-time result plan digest does not match the vehicle plan.")
    signature = result.network_free_flow_signature_digest
    if not isinstance(signature, str) or signature == "":
        raise RuntimeError("network_free_flow_signature_digest is empty.")
    if counters.negative_od_based_waiting_time_count != 0:
        raise RuntimeError("negative_od_based_waiting_time_count is not 0.")
    if counters.negative_cumulative_waiting_time_count != 0:
        raise RuntimeError("negative_cumulative_waiting_time_count is not 0.")
    if counters.negative_detour_time_count != 0:
        raise RuntimeError("negative_detour_time_count is not 0.")

    record_names = []
    participating_cohort_count = 0
    nonparticipating_cohort_count = 0
    participating_status_count = 0
    nonparticipating_status_count = 0
    total_od_steps = 0
    total_route_steps = 0
    total_detour_steps = 0
    total_weighted_od = 0.0
    total_weighted_route = 0.0
    total_weighted_detour = 0.0
    cohort_buckets = {}
    plans_by_name = {}
    for plan in plans:
        plans_by_name[plan["name"]] = plan
    for record in records:
        record_names.append(record.vehicle_name)
        if record.method_name != METHOD_NAME:
            raise RuntimeError(f"{record.vehicle_name} method_name is not tvt_mp.")
        if record.true_vot_per_second != true_vot_by_name[record.vehicle_name]:
            raise RuntimeError(f"{record.vehicle_name} true VOT does not match the ledger.")
        if record.evaluation_cohort != cohort_by_name[record.vehicle_name]:
            raise RuntimeError(f"{record.vehicle_name} evaluation cohort does not match the ledger.")
        if record.method_specific_participation_status != status_by_name[record.vehicle_name]:
            raise RuntimeError(
                f"{record.vehicle_name} participation status does not match the ledger."
            )
        if record.evaluation_cohort == PARTICIPATING_COHORT:
            participating_cohort_count = participating_cohort_count + 1
        elif record.evaluation_cohort == NONPARTICIPATING_COHORT:
            nonparticipating_cohort_count = nonparticipating_cohort_count + 1
        else:
            raise RuntimeError(f"{record.vehicle_name} has an unknown evaluation cohort.")
        if record.method_specific_participation_status == PARTICIPATING_STATUS:
            participating_status_count = participating_status_count + 1
        elif record.method_specific_participation_status == NONPARTICIPATING_STATUS:
            nonparticipating_status_count = nonparticipating_status_count + 1
        else:
            raise RuntimeError(f"{record.vehicle_name} has an unknown participation status.")
        plan = plans_by_name[record.vehicle_name]
        planned_departure_seconds = plan["departure_time"]
        expected_departure_timestep = int(planned_departure_seconds / deltat)
        if record.actual_departure_timestep != expected_departure_timestep:
            raise RuntimeError(
                f"{record.vehicle_name} actual departure timestep "
                f"{record.actual_departure_timestep} does not match "
                f"int(plan departure seconds / DELTAT)={expected_departure_timestep}."
            )
        if record.route_audit_identity is None or len(record.route_audit_identity) == 0:
            raise RuntimeError(f"{record.vehicle_name} actual route audit identity is empty.")
        _check_one_waiting_time_record(record, deltat)
        total_od_steps = total_od_steps + record.od_based_waiting_time_timesteps
        total_route_steps = total_route_steps + record.route_conditional_waiting_time_timesteps
        total_detour_steps = total_detour_steps + record.detour_time_timesteps
        total_weighted_od = total_weighted_od + record.weighted_od_based_waiting_time
        total_weighted_route = (
            total_weighted_route + record.weighted_route_conditional_waiting_time
        )
        total_weighted_detour = total_weighted_detour + record.weighted_detour_time
        bucket = cohort_buckets.get(record.evaluation_cohort)
        if bucket is None:
            bucket = {
                "vehicle_count": 0,
                "od_s": 0.0,
                "route_s": 0.0,
                "detour_s": 0.0,
                "weighted_od": 0.0,
                "weighted_route": 0.0,
                "weighted_detour": 0.0,
            }
            cohort_buckets[record.evaluation_cohort] = bucket
        bucket["vehicle_count"] = bucket["vehicle_count"] + 1
        bucket["od_s"] = bucket["od_s"] + record.od_based_waiting_time_s
        bucket["route_s"] = bucket["route_s"] + record.route_conditional_waiting_time_s
        bucket["detour_s"] = bucket["detour_s"] + record.detour_time_s
        bucket["weighted_od"] = bucket["weighted_od"] + record.weighted_od_based_waiting_time
        bucket["weighted_route"] = (
            bucket["weighted_route"] + record.weighted_route_conditional_waiting_time
        )
        bucket["weighted_detour"] = bucket["weighted_detour"] + record.weighted_detour_time

    if record_names != ordered_names:
        raise RuntimeError("Waiting-time vehicle order does not match the vehicle plan order.")
    if participating_cohort_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Participating cohort count is not 2400.")
    if nonparticipating_cohort_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Nonparticipating cohort count is not 600.")
    if participating_status_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Method-specific participating count is not 2400.")
    if nonparticipating_status_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Method-specific nonparticipating count is not 600.")
    if _cohort_assignment_digest(plans, cohort_by_name) != _cohort_assignment_digest_from_records(
        records
    ):
        raise RuntimeError("Cohort hash from records does not match the cohort ledger.")
    status_from_records = {}
    for record in records:
        status_from_records[record.vehicle_name] = record.method_specific_participation_status
    if _participation_status_digest(plans, status_from_records) != participation_digest:
        raise RuntimeError(
            "Participation-status hash does not match participation_assignment_sha256."
        )
    if _participation_status_digest(plans, status_by_name) != participation_digest:
        raise RuntimeError("Participation-status ledger hash does not match the assignment digest.")
    if total_od_steps != total_route_steps + total_detour_steps:
        raise RuntimeError("Overall timestep identity failed.")

    _require_close(
        summary.total_od_based_waiting_time_s,
        total_od_steps * deltat,
        "AWT numerator versus timestep sum",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.average_waiting_time_s,
        summary.total_od_based_waiting_time_s / NUM_VEHICLES,
        "AWT average identity",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.total_route_conditional_waiting_time_s,
        total_route_steps * deltat,
        "Route-Conditional AWT numerator",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.route_conditional_average_waiting_time_s,
        summary.total_route_conditional_waiting_time_s / NUM_VEHICLES,
        "Route-Conditional AWT average identity",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.total_detour_time_s,
        total_detour_steps * deltat,
        "detour numerator",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.average_detour_time_s,
        summary.total_detour_time_s / NUM_VEHICLES,
        "average detour identity",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.average_waiting_time_s,
        summary.route_conditional_average_waiting_time_s + summary.average_detour_time_s,
        "AWT equals Route-Conditional AWT plus average detour",
        AUDIT_ABS_TOL,
    )
    _require_close(
        summary.total_weighted_od_based_waiting_time,
        total_weighted_od,
        "AWWT numerator versus records",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.average_weighted_waiting_time,
        summary.total_weighted_od_based_waiting_time / NUM_VEHICLES,
        "AWWT average identity",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.total_weighted_route_conditional_waiting_time,
        total_weighted_route,
        "weighted Route-Conditional numerator",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.route_conditional_average_weighted_waiting_time,
        summary.total_weighted_route_conditional_waiting_time / NUM_VEHICLES,
        "Route-Conditional AWWT average identity",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.total_weighted_detour_time,
        total_weighted_detour,
        "weighted detour numerator",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.average_weighted_detour_time,
        summary.total_weighted_detour_time / NUM_VEHICLES,
        "weighted average detour identity",
        WEIGHTED_IDENTITY_ABS_TOL,
    )
    _require_close(
        summary.average_weighted_waiting_time,
        summary.route_conditional_average_weighted_waiting_time
        + summary.average_weighted_detour_time,
        "AWWT equals Route-Conditional AWWT plus weighted detour",
        WEIGHTED_IDENTITY_ABS_TOL,
    )

    found_cohorts = {}
    for cohort in summary.cohort_summaries:
        found_cohorts[cohort.evaluation_cohort] = cohort
        bucket = cohort_buckets[cohort.evaluation_cohort]
        if cohort.vehicle_count != bucket["vehicle_count"]:
            raise RuntimeError(f"{cohort.evaluation_cohort} vehicle count does not match records.")
        _require_close(
            cohort.total_od_based_waiting_time_s,
            bucket["od_s"],
            f"{cohort.evaluation_cohort} OD total",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
        _require_close(
            cohort.total_route_conditional_waiting_time_s,
            bucket["route_s"],
            f"{cohort.evaluation_cohort} Route-Conditional total",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
        _require_close(
            cohort.total_detour_time_s,
            bucket["detour_s"],
            f"{cohort.evaluation_cohort} detour total",
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
            f"{cohort.evaluation_cohort} AWT identity",
            AUDIT_ABS_TOL,
        )
        _require_close(
            cohort.average_weighted_waiting_time,
            cohort.total_weighted_od_based_waiting_time / cohort.vehicle_count,
            f"{cohort.evaluation_cohort} AWWT identity",
            WEIGHTED_IDENTITY_ABS_TOL,
        )
    if found_cohorts[PARTICIPATING_COHORT].vehicle_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Participating cohort summary is not 2400 vehicles.")
    if found_cohorts[NONPARTICIPATING_COHORT].vehicle_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Nonparticipating cohort summary is not 600 vehicles.")

    return {
        "awt_s": summary.average_waiting_time_s,
        "awwt": summary.average_weighted_waiting_time,
        "route_conditional_awt_s": summary.route_conditional_average_waiting_time_s,
        "route_conditional_awwt": summary.route_conditional_average_weighted_waiting_time,
        "average_detour_time_s": summary.average_detour_time_s,
        "average_weighted_detour_time": summary.average_weighted_detour_time,
        "participating_awt_s": found_cohorts[PARTICIPATING_COHORT].average_waiting_time_s,
        "participating_awwt": found_cohorts[PARTICIPATING_COHORT].average_weighted_waiting_time,
        "nonparticipating_awt_s": found_cohorts[NONPARTICIPATING_COHORT].average_waiting_time_s,
        "nonparticipating_awwt": (
            found_cohorts[NONPARTICIPATING_COHORT].average_weighted_waiting_time
        ),
        "network_free_flow_signature_digest": signature,
    }


def _cohort_assignment_digest_from_records(records) -> str:
    hasher = hashlib.sha256()
    for record in records:
        line = f"{record.vehicle_name}|{record.evaluation_cohort}\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def _json_number_list(values) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _json_text_list(values) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _waiting_time_vehicle_field_names() -> list[str]:
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


def _waiting_time_cohort_field_names() -> list[str]:
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


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_waiting_time_vehicle_rows(result) -> list[dict]:
    rows = []
    for record in result.vehicle_records:
        physical_key = record.physical_route_key
        lengths = []
        speeds = []
        for pair in physical_key[1]:
            lengths.append(pair[0])
            speeds.append(pair[1])
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "method_name": record.method_name,
                "vehicle_name": record.vehicle_name,
                "origin_name": record.origin_name,
                "destination_name": record.destination_name,
                "evaluation_cohort": record.evaluation_cohort,
                "method_specific_participation_status": (
                    record.method_specific_participation_status
                ),
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
                "od_minimum_free_flow_trip_timesteps": (
                    record.od_minimum_free_flow_trip_timesteps
                ),
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


def build_waiting_time_cohort_rows(result) -> list[dict]:
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
                "total_weighted_od_based_waiting_time": (
                    cohort.total_weighted_od_based_waiting_time
                ),
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


def build_waiting_time_summary_payload(result, evaluation_facts: dict) -> dict:
    summary = result.summary
    counters = result.counters
    return {
        "scenario_name": SCENARIO_NAME,
        "method_name": summary.method_name,
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
        "total_od_based_waiting_time_s": summary.total_od_based_waiting_time_s,
        "total_weighted_od_based_waiting_time": summary.total_weighted_od_based_waiting_time,
        "total_route_conditional_waiting_time_s": summary.total_route_conditional_waiting_time_s,
        "total_weighted_route_conditional_waiting_time": (
            summary.total_weighted_route_conditional_waiting_time
        ),
        "total_detour_time_s": summary.total_detour_time_s,
        "total_weighted_detour_time": summary.total_weighted_detour_time,
        "network_free_flow_signature_digest": (
            evaluation_facts["network_free_flow_signature_digest"]
        ),
        "evaluated_vehicle_count": counters.evaluated_vehicle_count,
        "incomplete_vehicle_count": counters.incomplete_vehicle_count,
        "unique_od_reference_count": counters.unique_od_reference_count,
        "od_reference_replay_run_count": counters.od_reference_replay_run_count,
        "od_reference_reuse_count": counters.od_reference_reuse_count,
        "unique_physical_route_count": counters.unique_physical_route_count,
        "reference_replay_run_count": counters.reference_replay_run_count,
        "reference_reuse_count": counters.reference_reuse_count,
        "cohorts": build_waiting_time_cohort_rows(result),
        "comparison_metadata": dict(result.comparison_metadata),
        "reference_comparison_includes_these_files": False,
    }


def write_network_wide_waiting_time_outputs(result, evaluation_facts: dict) -> None:
    vehicle_rows = build_waiting_time_vehicle_rows(result)
    cohort_rows = build_waiting_time_cohort_rows(result)
    summary_payload = build_waiting_time_summary_payload(result, evaluation_facts)
    _write_dict_csv(
        TRIAL_OUTPUT_DIR / WAITING_TIME_VEHICLES_CSV_NAME,
        _waiting_time_vehicle_field_names(),
        vehicle_rows,
    )
    _write_dict_csv(
        TRIAL_OUTPUT_DIR / WAITING_TIME_COHORTS_CSV_NAME,
        _waiting_time_cohort_field_names(),
        cohort_rows,
    )
    summary_path = TRIAL_OUTPUT_DIR / WAITING_TIME_SUMMARY_JSON_NAME
    if summary_path.exists():
        raise FileExistsError(f"Refusing to overwrite {summary_path}.")
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 11. Main
# ---------------------------------------------------------------------------

def _run_trial() -> int:
    script_start = time.perf_counter()
    timing = TimingRecord()
    original_recursion_limit = sys.getrecursionlimit()
    try:
        if original_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)

        _refuse_existing_output_directory()
        _require_reference_directory()

        plans = generate_vehicle_plans()
        plan_audit = verify_vehicle_plans(plans)
        nonparticipating_names = select_nonparticipating_names(plans)
        participating_names = []
        selected = set(nonparticipating_names)
        for plan in plans:
            if plan["name"] not in selected:
                participating_names.append(plan["name"])
        participation_digest = participation_assignment_digest(plans, nonparticipating_names)
        nonparticipating_digest = _hash_names(nonparticipating_names)
        participating_digest = _hash_names(participating_names)

        vot_values = generate_vehicle_vots(len(plans))
        vot_records = build_vehicle_vot_records(plans, vot_values, nonparticipating_names)

        started = time.perf_counter()
        world = build_world_and_network()
        add_vehicles_to_world(world, vot_records)
        timing.world_build_s = time.perf_counter() - started

        started = time.perf_counter()
        world.finalize_scenario()
        timing.finalize_s = time.perf_counter() - started
        if world.TSIZE != INTERNAL_TSIZE:
            raise RuntimeError(f"World.TSIZE is {world.TSIZE!r}, expected {INTERNAL_TSIZE}.")
        verify_network_runtime(world)

        started = time.perf_counter()
        install_tvt_mp_full_run_audit(world)
        timing.audit_install_s = time.perf_counter() - started

        started = time.perf_counter()
        run_until_full_completion(world)
        timing.exec_simulation_s = time.perf_counter() - started

        completion = verify_full_completion(world, plans)
        if completion["traffic_clearance_completed"] is not True:
            raise RuntimeError("Traffic clearance flag was not set.")
        if completion["full_trip_completion"] is not True:
            raise RuntimeError("Full trip completion flag was not set.")
        if not _traffic_is_clear(world):
            raise RuntimeError(
                "The safe timestep cap was reached before every vehicle finished "
                f"and the network emptied. World.T={world.T}. "
                "T=2296 is not assumed to be this trial's completion time."
            )

        ordered_names, true_vot_by_name, cohort_by_name, status_by_name = (
            build_waiting_time_ledgers(vot_records)
        )
        if ordered_names != _ordered_vehicle_names(plans):
            raise RuntimeError("Waiting-time vehicle order does not match the vehicle plan.")
        comparison_metadata = build_waiting_time_comparison_metadata(
            plan_audit,
            participation_digest,
            nonparticipating_digest,
            participating_digest,
            completion,
        )
        world_before_waiting_time = _finished_world_observation(world, ordered_names)
        started = time.perf_counter()
        waiting_time_result = evaluate_tvt_mp_network_wide_waiting_time(
            world,
            ordered_names,
            true_vot_by_name,
            cohort_by_name,
            status_by_name,
            plan_audit["vehicle_plan_sha256"],
            comparison_metadata,
        )
        timing.network_wide_waiting_time_evaluation_s = time.perf_counter() - started
        waiting_time_facts = verify_network_wide_waiting_time_result(
            waiting_time_result,
            plans,
            ordered_names,
            true_vot_by_name,
            cohort_by_name,
            status_by_name,
            plan_audit["vehicle_plan_sha256"],
            participation_digest,
            world,
        )
        world_after_waiting_time = _finished_world_observation(world, ordered_names)
        if world_after_waiting_time != world_before_waiting_time:
            raise RuntimeError(
                "Network-wide waiting-time evaluation changed the finished World."
            )
        if hasattr(world, "network_wide_waiting_time_result"):
            raise RuntimeError("The evaluation result must not be stored on the World.")

        ledger_summary = collect_node_rank_ledger_summary(world)
        visit_id_summary = collect_visit_id_summary(world)

        started = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        timing.research_build_s = time.perf_counter() - started
        final_actual_passage_timestep = _max_actual_passage_timestep(
            bundle,
            completion["final_world_t"],
        )
        transactions_by_node = collect_transaction_counts_by_node(bundle)
        transaction_count = bundle.scenario[0].transaction_count
        if sum(transactions_by_node.values()) != transaction_count:
            raise RuntimeError("Transaction node counts do not match the scenario total.")

        started = time.perf_counter()
        audit_result = finalize_tvt_mp_full_run_audit(world, bundle)
        timing.audit_finalize_s = time.perf_counter() - started

        _refuse_existing_output_directory()
        TRIAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

        started = time.perf_counter()
        write_tvt_mp_research_output_csv(bundle, TRIAL_OUTPUT_DIR, overwrite=False)
        timing.research_csv_write_s = time.perf_counter() - started

        started = time.perf_counter()
        write_tvt_mp_full_run_audit_csv(audit_result, TRIAL_OUTPUT_DIR)
        timing.audit_csv_write_s = time.perf_counter() - started

        audit_summary = verify_full_run_audit_output(TRIAL_OUTPUT_DIR, bundle, audit_result)
        research_sha256 = _research_csv_sha256(TRIAL_OUTPUT_DIR)

        vot_path = TRIAL_OUTPUT_DIR / "vehicle_vot.csv"
        started = time.perf_counter()
        write_vehicle_vot_csv(vot_path, vot_records)
        timing.vehicle_vot_csv_write_s = time.perf_counter() - started

        started = time.perf_counter()
        write_network_wide_waiting_time_outputs(waiting_time_result, waiting_time_facts)
        timing.awt_awwt_output_write_s = time.perf_counter() - started

        simulated_timesteps = completion["final_world_t"]
        if simulated_timesteps <= 0:
            raise RuntimeError("Simulated timestep count is not positive.")
        seconds_per_timestep = timing.exec_simulation_s / simulated_timesteps

        summary_lines = [
            "TVT-MP 6x6 3000-vehicle 20% nonparticipating full-completion audit trial",
            f"scenario: {SCENARIO_NAME}",
            f"vehicles: {NUM_VEHICLES}",
            f"participating: {PARTICIPATING_VEHICLE_COUNT}",
            f"nonparticipating: {NONPARTICIPATING_VEHICLE_COUNT}",
            f"departure: T={DEPARTURE_START}..{DEPARTURE_END}",
            f"final World.T: {completion['final_world_t']}",
            f"evaluation end timestep: {completion['evaluation_end_timestep']}",
            f"final actual passage timestep: {final_actual_passage_timestep}",
            "full trip completion: True",
            "traffic clearance: True",
            f"transaction count: {transaction_count}",
            f"transaction audit rows: {audit_summary.transaction_row_count}",
            f"visit audit rows: {audit_summary.visit_row_count}",
            f"buyer audit rows: {audit_summary.buyer_row_count}",
            f"seller audit rows: {audit_summary.seller_row_count}",
            f"nonparticipating audit rows: {audit_summary.nonparticipating_row_count}",
            f"actual arrival saved rows: {audit_summary.actual_arrival_row_count}",
            f"same-inlink max party: {audit_summary.max_same_inlink_party_count}",
            f"same-inlink max buyer: {audit_summary.max_same_inlink_buyer_count}",
            f"same-inlink max seller: {audit_summary.max_same_inlink_seller_count}",
            "same-inlink max nonparticipating: "
            f"{audit_summary.max_same_inlink_nonparticipating_count}",
            f"FIFO violation total: {audit_summary.fifo_violation_total}",
            "audit CSV validation: passed",
            f"method_name: {METHOD_NAME}",
            f"evaluated vehicles: {NUM_VEHICLES}",
            f"AWT: {waiting_time_facts['awt_s']}",
            f"AWWT: {waiting_time_facts['awwt']}",
            f"Route-Conditional AWT: {waiting_time_facts['route_conditional_awt_s']}",
            f"Route-Conditional AWWT: {waiting_time_facts['route_conditional_awwt']}",
            f"Average Detour Time: {waiting_time_facts['average_detour_time_s']}",
            "VOT-weighted Average Detour Time: "
            f"{waiting_time_facts['average_weighted_detour_time']}",
            "participating cohort AWT: "
            f"{waiting_time_facts['participating_awt_s']}",
            "participating cohort AWWT: "
            f"{waiting_time_facts['participating_awwt']}",
            "nonparticipating cohort AWT: "
            f"{waiting_time_facts['nonparticipating_awt_s']}",
            "nonparticipating cohort AWWT: "
            f"{waiting_time_facts['nonparticipating_awwt']}",
            "full completion: True",
            "traffic clearance: True",
            f"transaction count: {transaction_count}",
            f"final World.T: {completion['final_world_t']}",
            "network-wide evaluation seconds: "
            f"{timing.network_wide_waiting_time_evaluation_s:.6f}",
            f"AWT AWWT output write seconds: {timing.awt_awwt_output_write_s:.6f}",
            f"exec_simulation seconds: {timing.exec_simulation_s:.6f}",
            AWT_AWWT_REFERENCE_COMPARISON_NOTE,
            f"seconds per real-world timestep: {seconds_per_timestep:.6f}",
        ]
        summary_path = TRIAL_OUTPUT_DIR / "run_summary.txt"
        started = time.perf_counter()
        write_run_summary_txt(summary_path, summary_lines)
        timing.run_summary_write_s = time.perf_counter() - started

        bytes_before_manifest = _directory_bytes(TRIAL_OUTPUT_DIR)
        timing.script_total_s = time.perf_counter() - script_start
        manifest = {
            "scenario_name": SCENARIO_NAME,
            "full_completion_trial": FULL_COMPLETION_TRIAL,
            "traffic_clearance_required": TRAFFIC_CLEARANCE_REQUIRED,
            "full_trip_completion_required": FULL_TRIP_COMPLETION_REQUIRED,
            "full_run_audit_enabled": FULL_RUN_AUDIT_ENABLED,
            "nonparticipating_fraction": NONPARTICIPATING_VEHICLE_COUNT / NUM_VEHICLES,
            "participating_vehicle_count": PARTICIPATING_VEHICLE_COUNT,
            "nonparticipating_vehicle_count": NONPARTICIPATING_VEHICLE_COUNT,
            "nonparticipation_seed": NONPARTICIPATION_SEED,
            "NUM_VEHICLES": NUM_VEHICLES,
            "departure_start": DEPARTURE_START,
            "departure_end": DEPARTURE_END,
            "candidate_visit_limit": MAX_CANDIDATE_VISIT_COUNT,
            "baseline_horizon": BASELINE_HORIZON_STEPS,
            "clearance": CLEARANCE_TIMESTEPS,
            "final_world_t": completion["final_world_t"],
            "final_actual_passage_timestep": final_actual_passage_timestep,
            "evaluation_end_timestep": completion["evaluation_end_timestep"],
            "final_vehicle_state_counts": completion["vehicle_state_counts"],
            "final_internal_link_vehicle_count": completion["internal_link_vehicle_count"],
            "final_od_connector_vehicle_count": completion["od_connector_vehicle_count"],
            "final_all_link_vehicle_count": completion["all_link_vehicle_count"],
            "scheduled_departure_reached_count": completion["scheduled_departure_reached_count"],
            "scheduled_departure_not_reached_count": completion[
                "scheduled_departure_not_reached_count"
            ],
            "traffic_clearance_completed": True,
            "full_trip_completion": True,
            "transaction_count": transaction_count,
            "transactions_by_node": transactions_by_node,
            "full_run_audit_transaction_row_count": audit_summary.transaction_row_count,
            "full_run_audit_visit_row_count": audit_summary.visit_row_count,
            "full_run_audit_buyer_row_count": audit_summary.buyer_row_count,
            "full_run_audit_seller_row_count": audit_summary.seller_row_count,
            "full_run_audit_nonparticipating_row_count": audit_summary.nonparticipating_row_count,
            "full_run_audit_actual_arrival_row_count": audit_summary.actual_arrival_row_count,
            "full_run_audit_fifo_violation_total": audit_summary.fifo_violation_total,
            "full_run_audit_max_same_inlink_party_count": audit_summary.max_same_inlink_party_count,
            "full_run_audit_max_same_inlink_buyer_count": audit_summary.max_same_inlink_buyer_count,
            "full_run_audit_max_same_inlink_seller_count": audit_summary.max_same_inlink_seller_count,
            "full_run_audit_max_same_inlink_nonparticipating_count": (
                audit_summary.max_same_inlink_nonparticipating_count
            ),
            "tvt_mp_transaction_audit_csv_sha256": audit_summary.transaction_csv_sha256,
            "tvt_mp_visit_audit_csv_sha256": audit_summary.visit_csv_sha256,
            "research_csv_sha256": research_sha256,
            "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
            "participation_assignment_sha256": participation_digest,
            "nonparticipating_name_sha256": nonparticipating_digest,
            "participating_name_sha256": participating_digest,
            "nonparticipating_vehicle_names": list(nonparticipating_names),
            "shared_serialization_production_is_active": SHARED_SERIALIZATION_PRODUCTION_IS_ACTIVE,
            "baseline_candidate_shared_snapshot_production_is_active": (
                BASELINE_CANDIDATE_SHARED_SNAPSHOT_PRODUCTION_IS_ACTIVE
            ),
            "od_awt_awwt_compared_to_reference": OD_AWT_AWWT_COMPARED_TO_REFERENCE,
            "awt_awwt_reference_comparison_note": AWT_AWWT_REFERENCE_COMPARISON_NOTE,
            "profiling_run": PROFILING_RUN,
            "production_unchanged_by_script": PRODUCTION_UNCHANGED_BY_SCRIPT,
            "jam_density": JAM_DENSITY,
            "free_flow_speed_mps": FREE_FLOW_SPEED,
            "link_length_m": INTERNAL_LINK_LENGTH,
            "traffic_seed": TRAFFIC_SEED,
            "demand_gen_seed": DEMAND_GEN_SEED,
            "vot_seed": VOT_SEED,
            "safe_last_tvt_decision_timestep_cap": LAST_TVT_DECISION_TIMESTEP_CAP,
            "internal_tsize": INTERNAL_TSIZE,
            "fcfs_pretrial_completion_timestep_not_assumed": 2296,
            "node_rank_ledger_summary": ledger_summary,
            "visit_id_summary": visit_id_summary,
            "timing_seconds": {
                "world_build_seconds": timing.world_build_s,
                "finalize_seconds": timing.finalize_s,
                "audit_install_seconds": timing.audit_install_s,
                "exec_simulation_seconds": timing.exec_simulation_s,
                "research_output_build_seconds": timing.research_build_s,
                "audit_finalize_seconds": timing.audit_finalize_s,
                "research_csv_write_seconds": timing.research_csv_write_s,
                "audit_csv_write_seconds": timing.audit_csv_write_s,
                "vehicle_vot_csv_write_seconds": timing.vehicle_vot_csv_write_s,
                "network_wide_waiting_time_evaluation_seconds": (
                    timing.network_wide_waiting_time_evaluation_s
                ),
                "awt_awwt_output_write_seconds": timing.awt_awwt_output_write_s,
                "run_summary_write_seconds": timing.run_summary_write_s,
                "final_script_total_seconds_before_manifest_write": timing.script_total_s,
                "simulated_real_world_timestep_count": simulated_timesteps,
                "seconds_per_real_world_timestep": seconds_per_timestep,
            },
            "output_directory_bytes_before_manifest": bytes_before_manifest,
            "output_directory": str(TRIAL_OUTPUT_DIR),
            "formal_output_file_names": list(FORMAL_OUTPUT_FILE_NAMES),
        }
        manifest_path = TRIAL_OUTPUT_DIR / "manifest.json"
        started = time.perf_counter()
        write_manifest_json(manifest_path, manifest)
        timing.manifest_write_s = time.perf_counter() - started
        output_directory_total_bytes = _directory_bytes(TRIAL_OUTPUT_DIR)
        timing.script_total_s = time.perf_counter() - script_start

        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(f"manifest_write seconds: {timing.manifest_write_s:.6f}\n")
            handle.write(f"final script total seconds: {timing.script_total_s:.6f}\n")
            handle.write(f"output directory bytes: {output_directory_total_bytes}\n")

        print()
        print("=== 3000-vehicle 20% nonparticipating full-completion audit ===")
        print(f"scenario: {SCENARIO_NAME}")
        print(f"vehicles: {NUM_VEHICLES}")
        print(f"participating / nonparticipating: {PARTICIPATING_VEHICLE_COUNT} / {NONPARTICIPATING_VEHICLE_COUNT}")
        print(f"departure: T={DEPARTURE_START}..{DEPARTURE_END}")
        print(f"final World.T: {completion['final_world_t']}")
        print("full trip completion: True")
        print("traffic clearance: True")
        print(f"transaction count: {transaction_count}")
        print(f"audit transaction / visit rows: {audit_summary.transaction_row_count} / {audit_summary.visit_row_count}")
        print(
            "buyer / seller / nonparticipating audit rows: "
            f"{audit_summary.buyer_row_count} / {audit_summary.seller_row_count} / "
            f"{audit_summary.nonparticipating_row_count}"
        )
        print(f"actual arrival saved rows: {audit_summary.actual_arrival_row_count}")
        print(f"same-inlink max party: {audit_summary.max_same_inlink_party_count}")
        print(f"FIFO violation total: {audit_summary.fifo_violation_total}")
        print(f"method_name: {METHOD_NAME}")
        print(f"evaluated vehicles: {NUM_VEHICLES}")
        print(f"AWT: {waiting_time_facts['awt_s']}")
        print(f"AWWT: {waiting_time_facts['awwt']}")
        print(f"Route-Conditional AWT: {waiting_time_facts['route_conditional_awt_s']}")
        print(f"Route-Conditional AWWT: {waiting_time_facts['route_conditional_awwt']}")
        print(f"Average Detour Time: {waiting_time_facts['average_detour_time_s']}")
        print(
            "VOT-weighted Average Detour Time: "
            f"{waiting_time_facts['average_weighted_detour_time']}"
        )
        print(f"participating cohort AWT: {waiting_time_facts['participating_awt_s']}")
        print(f"participating cohort AWWT: {waiting_time_facts['participating_awwt']}")
        print(f"nonparticipating cohort AWT: {waiting_time_facts['nonparticipating_awt_s']}")
        print(
            "nonparticipating cohort AWWT: "
            f"{waiting_time_facts['nonparticipating_awwt']}"
        )
        print("full completion: True")
        print("traffic clearance: True")
        print(f"transaction count: {transaction_count}")
        print(f"final World.T: {completion['final_world_t']}")
        print(
            "network-wide evaluation seconds: "
            f"{timing.network_wide_waiting_time_evaluation_s:.6f}"
        )
        print(f"AWT AWWT output write seconds: {timing.awt_awwt_output_write_s:.6f}")
        print(f"exec_simulation seconds: {timing.exec_simulation_s:.3f}")
        print(f"final script total seconds: {timing.script_total_s:.3f}")
        print(f"output directory bytes: {output_directory_total_bytes}")
        print(f"output directory: {TRIAL_OUTPUT_DIR}")
        print()

        comparison = compare_full_completion_reference(timing.exec_simulation_s)
        write_reference_comparison(comparison)
        timing.script_total_s = time.perf_counter() - script_start
        acceptance_lines = [
            "3000 vehicles completed: True",
            "traffic clearance completed: True",
            "participating/nonparticipating hashes matched: "
            f"{comparison['participation_hashes_equal']}",
            f"transaction count: {transaction_count}",
            f"Visit count: {audit_summary.visit_row_count}",
            f"final World.T: {completion['final_world_t']}",
            f"evaluation end timestep: {completion['evaluation_end_timestep']}",
            f"CSV equality: {comparison['all_research_csv_equal']}",
            f"audit equality: {comparison['all_audit_csv_equal']}",
            f"VOT equality: {comparison['vehicle_vot_equal']}",
            "manifest research-result equality: "
            f"{comparison['manifest_research_results_equal']}",
            "full-completion Reference match: "
            f"{comparison['full_completion_reference_match']}",
            f"exec_simulation seconds: {timing.exec_simulation_s:.6f}",
            f"previous exec_simulation seconds: {PREVIOUS_EXEC_SIMULATION_SECONDS}",
            f"speedup: {comparison['speedup']:.6f}",
            "runtime reduction percentage: "
            f"{comparison['runtime_reduction_percentage']:.6f}",
            f"script total seconds: {timing.script_total_s:.6f}",
            "network-wide evaluation seconds: "
            f"{timing.network_wide_waiting_time_evaluation_s:.6f}",
            f"AWT AWWT output write seconds: {timing.awt_awwt_output_write_s:.6f}",
            f"output directory: {TRIAL_OUTPUT_DIR}",
            f"Reference directory: {REFERENCE_OUTPUT_DIR}",
            AWT_AWWT_REFERENCE_COMPARISON_NOTE,
            "performance is informational; acceptance requires a full reference match",
        ]
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(acceptance_lines))
            handle.write("\n")
        print("=== full-completion reference comparison ===")
        for line in acceptance_lines:
            print(line)
        if comparison["first_difference"] is not None:
            print(f"first difference: {comparison['first_difference']!r}")
        print()
        if comparison["full_completion_reference_match"] is not True:
            return 1
        return 0
    finally:
        sys.setrecursionlimit(original_recursion_limit)


def main() -> int:
    if len(sys.argv) > 2:
        raise SystemExit("Use no arguments, or --static-validate-only.")
    if len(sys.argv) == 2:
        if sys.argv[1] != "--static-validate-only":
            raise SystemExit(f"Unknown option {sys.argv[1]!r}.")
        validate_static_contract()
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        ast.parse(source)
        compile(source, str(SCRIPT_PATH), "exec")
        print("Static contract validation passed.", file=sys.stderr)
        return 0
    return _run_trial()


if __name__ == "__main__":
    raise SystemExit(main())
