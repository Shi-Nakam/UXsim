"""
TVT-MP single cross intersection 12-vehicle initial trial (not a formal experiment).

One central TVT-MP intersection with four peripheral nodes (north, east, south, west),
eight directional single-lane links (200 m each), and 12 vehicles with OD-only assignment.
UXsim dynamic route choice is used; routes are not fixed in this script.
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

from uxsim import World
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

SCENARIO_NAME = "tvt_mp_single_cross_intersection_12_vehicle_trial"
WORLD_DISPLAY_NAME = "tvt_mp_single_cross_intersection_12_vehicle"

TRAFFIC_SEED = 0
VOT_SEED = 1

VOT_ARITHMETIC_MEAN = 1.0
VOT_ARITHMETIC_STDDEV = 3.0
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

EVALUATION_START_TIMESTEP = 0
EVALUATION_END_TIMESTEP = 299
INTERNAL_TSIZE = 330
EXPECTED_WORLD_T_AFTER_SIM = EVALUATION_END_TIMESTEP + 1

BASELINE_HORIZON_STEPS = 30
MAX_CANDIDATE_VISIT_COUNT = 10
EXPECTED_DRIVER_CALL_COUNT = EVALUATION_END_TIMESTEP - EVALUATION_START_TIMESTEP + 1

DECISION_WINDOW_CONTRACT = (
    "0 < baseline_arrival_timestep - T <= 6 "
    "(code constant; not set in script)"
)

FREE_FLOW_SPEED_M_PER_S = 60000 / 3600
LINK_LENGTH_M = 200
NUMBER_OF_LANES = 1

CENTRAL_INTERSECTION_NODE = "intersection"
PERIPHERAL_NODE_NAMES: tuple[str, ...] = ("north", "east", "south", "west")
NODE_NAMES: tuple[str, ...] = (CENTRAL_INTERSECTION_NODE,) + PERIPHERAL_NODE_NAMES

# Same-timestep VehicleSpec order: north, east, south, west.
ORIGIN_DEPARTURE_ORDER: tuple[str, ...] = PERIPHERAL_NODE_NAMES

DEPARTURE_TIMESTEPS: tuple[int, ...] = (5, 9, 13)
VEHICLES_PER_DEPARTURE_TIMESTEP = 4

ROUTE_ASSIGNMENT_MODE = "uxsim_dynamic_route_choice_from_od"
SPECIFIED_ROUTE_USED = False

# Link name, upstream node, downstream node (for static checks and world build).
LINK_SPECS: tuple[tuple[str, str, str], ...] = (
    ("north_to_intersection", "north", "intersection"),
    ("intersection_to_north", "intersection", "north"),
    ("east_to_intersection", "east", "intersection"),
    ("intersection_to_east", "intersection", "east"),
    ("south_to_intersection", "south", "intersection"),
    ("intersection_to_south", "intersection", "south"),
    ("west_to_intersection", "west", "intersection"),
    ("intersection_to_west", "intersection", "west"),
)

INLINK_COUNT = sum(1 for _name, _u, down in LINK_SPECS if down == CENTRAL_INTERSECTION_NODE)
OUTLINK_COUNT = sum(
    1 for _name, up, _down in LINK_SPECS if up == CENTRAL_INTERSECTION_NODE
)
LINK_COUNT = len(LINK_SPECS)

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = (
    TRIAL_PARENT / "tvt_mp_single_cross_intersection_12_vehicle_seed_1_initial"
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
    "tvt_mp_50_vehicle_medium_demand_seed_1_initial",
    "tvt_mp_50_vehicle_medium_demand_seed_1_passage_resolution_v2",
    "tvt_mp_50_vehicle_medium_demand_seed_1_capacity_refill_v3",
    "tvt_mp_50_vehicle_asymmetric_demand_seed_1_initial",
    "tvt_mp_small_scale_initial_seed_1_baseline_arrival_order",
    "tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2",
)

# Planned movement labels from origin/destination (diagnosis helper only; not routes).
MOVEMENT_BY_ORIGIN_DESTINATION: dict[tuple[str, str], str] = {
    ("north", "south"): "straight",
    ("north", "east"): "left",
    ("north", "west"): "right",
    ("north", "north"): "u_turn",
    ("east", "west"): "straight",
    ("east", "south"): "left",
    ("east", "north"): "right",
    ("east", "east"): "u_turn",
    ("south", "north"): "straight",
    ("south", "west"): "left",
    ("south", "east"): "right",
    ("south", "south"): "u_turn",
    ("west", "east"): "straight",
    ("west", "north"): "left",
    ("west", "south"): "right",
    ("west", "west"): "u_turn",
}


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool


def planned_movement_label(origin: str, destination: str) -> str:
    """Return planned movement label for OD (for manifest/diagnosis; not a route)."""
    key = (origin, destination)
    if key not in MOVEMENT_BY_ORIGIN_DESTINATION:
        raise KeyError(f"No movement label for OD {origin} -> {destination}.")
    return MOVEMENT_BY_ORIGIN_DESTINATION[key]


def _build_vehicle_specs() -> tuple[VehicleSpec, ...]:
    """
    Twelve vehicles: T=5 straight-like OD, T=9 left-like OD, T=13 right-like OD.
    At equal T, order is north, east, south, west by origin.
    """
    raw_rows: list[tuple[str, str, str, int]] = [
        ("veh_n1", "north", "south", 5),
        ("veh_e1", "east", "west", 5),
        ("veh_s1", "south", "north", 5),
        ("veh_w1", "west", "east", 5),
        ("veh_n2", "north", "east", 9),
        ("veh_e2", "east", "south", 9),
        ("veh_s2", "south", "west", 9),
        ("veh_w2", "west", "north", 9),
        ("veh_n3", "north", "west", 13),
        ("veh_e3", "east", "north", 13),
        ("veh_s3", "south", "east", 13),
        ("veh_w3", "west", "south", 13),
    ]

    specs = [
        VehicleSpec(
            vehicle_name=name,
            orig=orig,
            dest=dest,
            departure_timestep=departure,
            participating=True,
        )
        for name, orig, dest, departure in raw_rows
    ]

    def sort_key(spec: VehicleSpec) -> tuple[int, int]:
        origin_order = ORIGIN_DEPARTURE_ORDER.index(spec.orig)
        return (spec.departure_timestep, origin_order)

    specs.sort(key=sort_key)
    return tuple(specs)


VEHICLE_SPECS: tuple[VehicleSpec, ...] = _build_vehicle_specs()


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


# ---------------------------------------------------------------------------
# 1b. Static contract validation (no simulation)
# ---------------------------------------------------------------------------


def manifest_counts_from_specs(
    specs: tuple[VehicleSpec, ...],
) -> dict[str, int | str | bool | list[int]]:
    """Manifest count fields derived from VEHICLE_SPECS and network constants."""
    movement_counts = {"straight": 0, "left": 0, "right": 0, "u_turn": 0}
    for spec in specs:
        label = planned_movement_label(spec.orig, spec.dest)
        movement_counts[label] += 1

    unique_origins = {spec.orig for spec in specs}
    unique_dests = {spec.dest for spec in specs}

    return {
        "vehicle_count": len(specs),
        "participating_count": sum(1 for s in specs if s.participating),
        "nonparticipating_count": sum(1 for s in specs if not s.participating),
        "central_intersection_node": CENTRAL_INTERSECTION_NODE,
        "inlink_count": INLINK_COUNT,
        "outlink_count": OUTLINK_COUNT,
        "link_count": LINK_COUNT,
        "link_length_m": LINK_LENGTH_M,
        "lane_count_per_link": NUMBER_OF_LANES,
        "route_assignment_mode": ROUTE_ASSIGNMENT_MODE,
        "specified_route_used": SPECIFIED_ROUTE_USED,
        "origin_count": len(unique_origins),
        "destination_count": len(unique_dests),
        "planned_straight_od_count": movement_counts["straight"],
        "planned_left_turn_od_count": movement_counts["left"],
        "planned_right_turn_od_count": movement_counts["right"],
        "planned_u_turn_od_count": movement_counts["u_turn"],
        "departure_timesteps": list(DEPARTURE_TIMESTEPS),
        "vehicles_per_departure_timestep": VEHICLES_PER_DEPARTURE_TIMESTEP,
        "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "clearance_timesteps": 1,
    }


def _origin_order_key(spec: VehicleSpec) -> tuple[int, int]:
    return (spec.departure_timestep, ORIGIN_DEPARTURE_ORDER.index(spec.orig))


def validate_static_contract() -> None:
    specs = VEHICLE_SPECS
    counts = manifest_counts_from_specs(specs)

    if len(NODE_NAMES) != 5:
        raise RuntimeError(f"Expected 5 nodes, got {len(NODE_NAMES)}.")
    if LINK_COUNT != 8:
        raise RuntimeError(f"Expected 8 links, got {LINK_COUNT}.")
    if INLINK_COUNT != 4:
        raise RuntimeError(f"Expected 4 intersection inlinks, got {INLINK_COUNT}.")
    if OUTLINK_COUNT != 4:
        raise RuntimeError(f"Expected 4 intersection outlinks, got {OUTLINK_COUNT}.")
    if LINK_LENGTH_M != 200:
        raise RuntimeError(f"Expected link length 200 m, got {LINK_LENGTH_M}.")
    if NUMBER_OF_LANES != 1:
        raise RuntimeError(f"Expected 1 lane per link, got {NUMBER_OF_LANES}.")

    if counts["vehicle_count"] != 12:
        raise RuntimeError(f"Expected 12 VehicleSpec, got {counts['vehicle_count']}.")
    if counts["participating_count"] != 12:
        raise RuntimeError(
            f"Expected 12 participating, got {counts['participating_count']}."
        )
    if counts["nonparticipating_count"] != 0:
        raise RuntimeError(
            f"Expected 0 nonparticipating, got {counts['nonparticipating_count']}."
        )

    for departure in DEPARTURE_TIMESTEPS:
        at_t = [s for s in specs if s.departure_timestep == departure]
        if len(at_t) != VEHICLES_PER_DEPARTURE_TIMESTEP:
            raise RuntimeError(
                f"Expected {VEHICLES_PER_DEPARTURE_TIMESTEP} vehicles at T={departure}, "
                f"got {len(at_t)}."
            )
        origins_at_t = [s.orig for s in at_t]
        if origins_at_t != list(ORIGIN_DEPARTURE_ORDER):
            raise RuntimeError(
                f"At T={departure}, expected origin order {list(ORIGIN_DEPARTURE_ORDER)}, "
                f"got {origins_at_t}."
            )

    for index in range(1, len(specs)):
        if _origin_order_key(specs[index]) < _origin_order_key(specs[index - 1]):
            raise RuntimeError(
                "VEHICLE_SPECS is not sorted by departure ascending, "
                "then north, east, south, west at equal T."
            )

    if any(spec.orig == spec.dest for spec in specs):
        raise RuntimeError("Origin equals destination for at least one vehicle.")
    if counts["planned_u_turn_od_count"] != 0:
        raise RuntimeError(
            f"Expected 0 planned U-turn OD, got {counts['planned_u_turn_od_count']}."
        )

    vehicle_names = [spec.vehicle_name for spec in specs]
    if len(set(vehicle_names)) != len(vehicle_names):
        raise RuntimeError("Duplicate vehicle_name in VEHICLE_SPECS.")

    od_departure_keys = [
        (spec.orig, spec.dest, spec.departure_timestep) for spec in specs
    ]
    if len(set(od_departure_keys)) != len(od_departure_keys):
        raise RuntimeError(
            "Duplicate (origin, destination, departure_timestep) in VEHICLE_SPECS."
        )

    if SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("specified_route_used must remain False for this trial.")
    if ROUTE_ASSIGNMENT_MODE != "uxsim_dynamic_route_choice_from_od":
        raise RuntimeError("Unexpected route_assignment_mode.")

    manifest_vehicle_count = counts["vehicle_count"]
    if manifest_vehicle_count != len(specs):
        raise RuntimeError("manifest vehicle_count inconsistent with VEHICLE_SPECS.")
    if counts["link_count"] != LINK_COUNT:
        raise RuntimeError("manifest link_count inconsistent with LINK_SPECS.")
    if counts["inlink_count"] != INLINK_COUNT:
        raise RuntimeError("manifest inlink_count inconsistent with LINK_SPECS.")
    if counts["outlink_count"] != OUTLINK_COUNT:
        raise RuntimeError("manifest outlink_count inconsistent with LINK_SPECS.")

    output_name = TRIAL_OUTPUT_DIR.name
    if output_name in KNOWN_OTHER_TRIAL_DIR_NAMES:
        raise RuntimeError(
            f"Output directory name collides with known trial: {output_name}."
        )
    for known in KNOWN_OTHER_TRIAL_DIR_NAMES:
        if TRIAL_OUTPUT_DIR == TRIAL_PARENT / known:
            raise RuntimeError(
                f"TRIAL_OUTPUT_DIR must differ from existing trial: {known}."
            )


# ---------------------------------------------------------------------------
# 2. VOT generation
# ---------------------------------------------------------------------------


def generate_vehicle_vots(rng: np.random.Generator, count: int) -> list[float]:
    """One lognormal draw per vehicle, in VEHICLE_SPECS order."""
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


# ---------------------------------------------------------------------------
# 3. World and network
# ---------------------------------------------------------------------------


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

    world.addNode("intersection", 0, 0)
    world.addNode("north", 0, 1)
    world.addNode("east", 1, 0)
    world.addNode("south", 0, -1)
    world.addNode("west", -1, 0)

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
        [CENTRAL_INTERSECTION_NODE],
        order_control_type="time_value",
        transaction_case=None,
    )

    clearance = world.order_control_clearance_timesteps
    if clearance != 1:
        raise RuntimeError(
            f"Expected order_control_clearance_timesteps=1, got {clearance!r}."
        )

    world.order_control_tvt_evaluation_end_timestep = EVALUATION_END_TIMESTEP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT

    return world


# ---------------------------------------------------------------------------
# 4. Vehicle addition (OD only; no specified_route)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 6. Evaluation end checks
# ---------------------------------------------------------------------------


def verify_evaluation_end(world: World) -> dict[str, int | bool]:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )

    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    checks = {
        "world_t": world.T,
        "evaluation_end_unobserved_finalized_timestep": (
            registry.evaluation_end_unobserved_finalized_timestep
        ),
        "trade_ex_post_evaluation_finalized_timestep": (
            registry.trade_ex_post_evaluation_finalized_timestep
        ),
        "individual_ex_post_evaluation_finalized_timestep": (
            registry.individual_ex_post_evaluation_finalized_timestep
        ),
    }

    for field_name, expected in (
        ("evaluation_end_unobserved_finalized_timestep", EVALUATION_END_TIMESTEP),
        ("trade_ex_post_evaluation_finalized_timestep", EVALUATION_END_TIMESTEP),
        ("individual_ex_post_evaluation_finalized_timestep", EVALUATION_END_TIMESTEP),
    ):
        actual = checks[field_name]
        if actual != expected:
            raise RuntimeError(
                f"Registry {field_name} expected {expected}, got {actual!r}."
            )

    return {
        "world_t": world.T,
        "world_t_ok": True,
        "unobserved_ok": True,
        "trade_ex_post_ok": True,
        "individual_ex_post_ok": True,
    }


# ---------------------------------------------------------------------------
# 8–9. Trial auxiliary files
# ---------------------------------------------------------------------------


def write_vehicle_vot_csv(
    path: Path,
    vot_records: list[VehicleVotRecord],
) -> None:
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
            declared = record.declared_vot_per_second
            writer.writerow(
                {
                    "vehicle_name": record.vehicle_name,
                    "origin": record.origin,
                    "destination": record.destination,
                    "departure_timestep": record.departure_timestep,
                    "participates_in_order_exchange": record.participates_in_order_exchange,
                    "true_vot_per_second": record.true_vot_per_second,
                    "declared_vot_per_second": (
                        "" if declared is None else declared
                    ),
                    "traffic_seed": TRAFFIC_SEED,
                    "vot_seed": VOT_SEED,
                }
            )


def write_manifest_json(
    path: Path,
    timing: TimingRecord,
    world: World,
    generated_files: list[str],
    clearance_timesteps: int,
) -> None:
    trial_fields = manifest_counts_from_specs(VEHICLE_SPECS)
    manifest = {
        "schema_note": (
            "12-vehicle single cross intersection trial manifest only; "
            "not a formal experiment schema."
        ),
        "run_type": "trial",
        "scenario_name": SCENARIO_NAME,
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
        "traffic_seed": TRAFFIC_SEED,
        "vot_seed": VOT_SEED,
        "vot_arithmetic_mean_per_second": VOT_ARITHMETIC_MEAN,
        "vot_arithmetic_stddev_per_second": VOT_ARITHMETIC_STDDEV,
        "vot_log_space_mu": VOT_LOG_MU,
        "vot_log_space_sigma": VOT_LOG_SIGMA,
        "evaluation_start_timestep": EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "internal_tsize": INTERNAL_TSIZE,
        "baseline_horizon_steps": trial_fields["baseline_horizon_steps"],
        "decision_window_contract": DECISION_WINDOW_CONTRACT,
        "max_candidate_visit_count": trial_fields["max_candidate_visit_count"],
        "clearance_timesteps": clearance_timesteps,
        "free_flow_speed_m_per_s": FREE_FLOW_SPEED_M_PER_S,
        "link_length_m": trial_fields["link_length_m"],
        "lane_count_per_link": trial_fields["lane_count_per_link"],
        "vehicle_count": trial_fields["vehicle_count"],
        "participating_count": trial_fields["participating_count"],
        "nonparticipating_count": trial_fields["nonparticipating_count"],
        "central_intersection_node": trial_fields["central_intersection_node"],
        "inlink_count": trial_fields["inlink_count"],
        "outlink_count": trial_fields["outlink_count"],
        "link_count": trial_fields["link_count"],
        "route_assignment_mode": trial_fields["route_assignment_mode"],
        "specified_route_used": trial_fields["specified_route_used"],
        "origin_count": trial_fields["origin_count"],
        "destination_count": trial_fields["destination_count"],
        "planned_straight_od_count": trial_fields["planned_straight_od_count"],
        "planned_left_turn_od_count": trial_fields["planned_left_turn_od_count"],
        "planned_right_turn_od_count": trial_fields["planned_right_turn_od_count"],
        "planned_u_turn_od_count": trial_fields["planned_u_turn_od_count"],
        "departure_timesteps": trial_fields["departure_timesteps"],
        "vehicles_per_departure_timestep": trial_fields[
            "vehicles_per_departure_timestep"
        ],
        "node_names": list(NODE_NAMES),
        "link_specs": [
            {"name": name, "upstream": up, "downstream": down}
            for name, up, down in LINK_SPECS
        ],
        "capacity_settings": "UXsim defaults (capacity_in/out and Node flow_capacity not set)",
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
        "generated_files": generated_files,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(
    path: Path,
    timing: TimingRecord,
    world: World,
    bundle,
    completed_trips: int,
    decision_timesteps: list[int],
    generated_files: list[str],
) -> None:
    counts = manifest_counts_from_specs(VEHICLE_SPECS)
    scenario_row = bundle.scenario[0]
    lines = [
        "TVT-MP single cross intersection 12-vehicle trial run summary",
        "=" * 50,
        "Completed run: yes",
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Network:",
        "  5 nodes / 8 links",
        "  central intersection: 4 inlinks / 4 outlinks",
        f"  all links {LINK_LENGTH_M} m, single lane",
        f"  TVT-MP target node: {CENTRAL_INTERSECTION_NODE}",
        "",
        "Vehicles:",
        f"  12 vehicles, all participating (nonparticipating 0)",
        "  T=5: four straight-equivalent OD (one per peripheral origin)",
        "  T=9: four left-turn-equivalent OD",
        "  T=13: four right-turn-equivalent OD",
        "  no route fixing; OD only",
        "  UXsim dynamic route choice",
        "  realized movements at central node to be confirmed by future diagnosis",
        "",
        "Route assignment:",
        f"  mode: {ROUTE_ASSIGNMENT_MODE}",
        f"  specified_route_used: {SPECIFIED_ROUTE_USED}",
        "",
        "Timing (seconds):",
        f"  world_build: {timing.world_build_s:.4f}",
        f"  finalize_scenario: {timing.finalize_s:.4f}",
        f"  exec_simulation: {timing.exec_simulation_s:.4f}",
        f"  research_output_build: {timing.research_build_s:.4f}",
        f"  csv_write: {timing.csv_write_s:.4f}",
        f"  trial_auxiliary_write: {timing.trial_aux_write_s:.4f}",
        f"  script_total: {timing.script_total_s:.4f}",
        f"  (TVT-MP driver calls by configuration: {EXPECTED_DRIVER_CALL_COUNT})",
        "",
        f"Completed trips: {completed_trips} / {len(VEHICLE_SPECS)}",
        f"Transaction count: {scenario_row.transaction_count}",
        "",
        "Trade ex-post status counts (scenario aggregation):",
        f"  feasible: {scenario_row.feasible_count}",
        f"  infeasible: {scenario_row.infeasible_count}",
        f"  unavailable: {scenario_row.unavailable_count}",
        "",
        "Visit counts (research output scenario row):",
        f"  buyer visits: {scenario_row.buyer_visit_count}",
        f"  seller visits: {scenario_row.seller_visit_count}",
        f"  nonparticipating visits: {scenario_row.nonparticipating_visit_count}",
        "",
        "Planned OD movement counts (not guaranteed realized routes):",
        f"  straight: {counts['planned_straight_od_count']}",
        f"  left: {counts['planned_left_turn_od_count']}",
        f"  right: {counts['planned_right_turn_od_count']}",
        f"  u_turn: {counts['planned_u_turn_od_count']}",
        "",
        "Generated files:",
    ]
    for name in generated_files:
        lines.append(f"  - {name}")

    if scenario_row.transaction_count == 0:
        lines.extend(
            [
                "",
                "Note: transaction_count is 0.",
                "Whether this was due to no candidate formation, economic "
                "infeasibility, or unresolved evaluation cannot be determined "
                "from current research output alone.",
            ]
        )
    else:
        lines.append("")
        lines.append("tvt_decision_timestep per transaction:")
        for row in bundle.transactions:
            lines.append(
                f"  - {row.node_name}: T={row.tvt_decision_timestep}"
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_decision_timesteps(bundle) -> list[int]:
    return sorted({row.tvt_decision_timestep for row in bundle.transactions})


def verify_research_csv_files(directory: Path) -> None:
    for name in RESEARCH_CSV_NAMES:
        path = directory / name
        if not path.is_file():
            raise RuntimeError(f"Expected research CSV missing: {path}")


# ---------------------------------------------------------------------------
# 10. Console summary
# ---------------------------------------------------------------------------


def print_console_summary(
    vot_records: list[VehicleVotRecord],
    eval_ok: dict,
    timing: TimingRecord,
    completed_trips: int,
    bundle,
    output_dir: Path,
) -> None:
    scenario_row = bundle.scenario[0]
    counts = manifest_counts_from_specs(VEHICLE_SPECS)
    print()
    print("=== TVT-MP single cross intersection 12-vehicle trial ===")
    print()
    print(
        f"Network: 5 nodes, 8 links; TVT-MP node {CENTRAL_INTERSECTION_NODE}; "
        f"participating {counts['participating_count']} / "
        f"nonparticipating {counts['nonparticipating_count']}"
    )
    print(
        f"Route: {ROUTE_ASSIGNMENT_MODE}; "
        f"specified_route_used={SPECIFIED_ROUTE_USED}"
    )
    print()
    print("Vehicles (name, origin, dest, T, participating, true VOT, declared VOT):")
    for record in vot_records:
        part = "Y" if record.participates_in_order_exchange else "N"
        declared_display = (
            "None"
            if record.declared_vot_per_second is None
            else f"{record.declared_vot_per_second:.6g}"
        )
        print(
            f"  {record.vehicle_name}: {record.origin}->{record.destination} "
            f"T={record.departure_timestep} part={part}, "
            f"true={record.true_vot_per_second:.6g}, declared={declared_display}"
        )
    print()
    print("Evaluation end checks: all passed")
    print(f"  World.T = {eval_ok['world_t']}")
    print()
    print("Timing (s):")
    print(f"  build: {timing.world_build_s:.3f}")
    print(f"  finalize: {timing.finalize_s:.3f}")
    print(f"  exec_simulation: {timing.exec_simulation_s:.3f}")
    print(f"  research build: {timing.research_build_s:.3f}")
    print(f"  csv write: {timing.csv_write_s:.3f}")
    print(f"  trial aux: {timing.trial_aux_write_s:.3f}")
    print(f"  total: {timing.script_total_s:.3f}")
    print(f"  (driver calls by config: {EXPECTED_DRIVER_CALL_COUNT})")
    print()
    print(f"Completed trips: {completed_trips}")
    print(f"Transaction count: {scenario_row.transaction_count}")
    print(
        f"Feasible / infeasible / unavailable: "
        f"{scenario_row.feasible_count} / "
        f"{scenario_row.infeasible_count} / "
        f"{scenario_row.unavailable_count}"
    )
    print(
        f"Buyer / seller / NP visits: "
        f"{scenario_row.buyer_visit_count} / "
        f"{scenario_row.seller_visit_count} / "
        f"{scenario_row.nonparticipating_visit_count}"
    )
    print()
    print(f"Output directory: {output_dir}")
    if scenario_row.transaction_count == 0:
        print()
        print(
            "Note: transaction_count=0; cause (candidates / infeasible / "
            "unresolved) cannot be inferred from current output alone."
        )
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    script_start = time.perf_counter()
    timing = TimingRecord()

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
    world.exec_simulation()
    timing.exec_simulation_s = time.perf_counter() - t0

    eval_ok = verify_evaluation_end(world)

    t0 = time.perf_counter()
    bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
    timing.research_build_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        written = write_tvt_mp_research_output_csv(
            bundle,
            TRIAL_OUTPUT_DIR,
            overwrite=False,
        )
    except FileExistsError:
        raise
    timing.csv_write_s = time.perf_counter() - t0

    verify_research_csv_files(TRIAL_OUTPUT_DIR)

    generated_files = list(RESEARCH_CSV_NAMES) + [
        "vehicle_vot.csv",
        "manifest.json",
        "run_summary.txt",
    ]

    completed_trips = int(world.analyzer.trip_completed)
    decision_timesteps = collect_decision_timesteps(bundle)

    t0 = time.perf_counter()
    write_vehicle_vot_csv(TRIAL_OUTPUT_DIR / "vehicle_vot.csv", vot_records)
    write_manifest_json(
        TRIAL_OUTPUT_DIR / "manifest.json",
        timing,
        world,
        generated_files,
        world.order_control_clearance_timesteps,
    )
    write_run_summary_txt(
        TRIAL_OUTPUT_DIR / "run_summary.txt",
        timing,
        world,
        bundle,
        completed_trips,
        decision_timesteps,
        generated_files,
    )
    timing.trial_aux_write_s = time.perf_counter() - t0

    timing.script_total_s = time.perf_counter() - script_start

    write_manifest_json(
        TRIAL_OUTPUT_DIR / "manifest.json",
        timing,
        world,
        generated_files,
        world.order_control_clearance_timesteps,
    )
    write_run_summary_txt(
        TRIAL_OUTPUT_DIR / "run_summary.txt",
        timing,
        world,
        bundle,
        completed_trips,
        decision_timesteps,
        generated_files,
    )

    print_console_summary(
        vot_records,
        eval_ok,
        timing,
        completed_trips,
        bundle,
        TRIAL_OUTPUT_DIR,
    )

    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
            validate_static_contract()
            source = SCRIPT_PATH.read_text(encoding="utf-8")
            ast.parse(source)
            compile(source, str(SCRIPT_PATH), "exec")
            print("Static contract validation passed.", file=sys.stderr)
            raise SystemExit(0)
        raise SystemExit(main())
    except FileExistsError as exc:
        print(f"FileExistsError: {exc}", file=sys.stderr)
        raise SystemExit(1)
