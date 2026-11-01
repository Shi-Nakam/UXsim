# DIAGNOSTIC SCRIPT — NOT a regression test or research evaluation trial.
#
# cProfile probe for a single TVT-MP timestep (T=96) on the 3000-vehicle 6x6 grid
# scenario matching the short runtime benchmark (same vehicle plan, VOT, network).
# T=0..95 run without profiling; only world.exec_simulation(duration_t2=DELTAT)
# at T=96 is profiled.
#
# cProfile wall-clock is not a formal performance value. Do not compare profile
# totals directly to the normal benchmark exec_simulation_seconds.
#
# Does not import the research benchmark script or other profiling diagnostics at
# runtime. Production code is not modified.
#
# Run from repository root:
#   python diagnostics/order_control/tvt_mp_3000_vehicle_t96_single_timestep_profile.py --static-validate-only
#   python diagnostics/order_control/tvt_mp_3000_vehicle_t96_single_timestep_profile.py

from __future__ import annotations

import ast
import cProfile
import gc
import hashlib
import io
import json
import math
import pstats
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from uxsim import World
from uxsim.order_control_tvt_mp_research_output import build_tvt_mp_research_output

# ---------------------------------------------------------------------------
# Diagnostic constants
# ---------------------------------------------------------------------------

DIAGNOSTIC_NAME = (
    "tvt_mp_3000_vehicle_t96_single_timestep_profile_seed_0_vot_seed_1"
)
OUTPUT_DIR_NAME = DIAGNOSTIC_NAME

NUM_VEHICLES = 3000
DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5

PROFILE_TIMESTEP = 96
UNPROFILED_START_TIMESTEP = 0
UNPROFILED_END_TIMESTEP = 95
PROFILED_TIMESTEP_COUNT = 1
WORLD_T_BEFORE_PROFILE = 96
WORLD_T_AFTER_PROFILE = 97

EVALUATION_END_TIMESTEP = 96
BASELINE_HORIZON_STEPS = 30
INTERNAL_TSIZE = 127
EXPECTED_WORLD_T_AFTER_PROFILE = WORLD_T_AFTER_PROFILE

TRAFFIC_SEED = 0
DEMAND_GEN_SEED = 42
VOT_SEED = 1

VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1
WORLD_COPY_RECURSION_LIMIT = 50000

GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = 36
EXTERNAL_OD_NODE_COUNT = 24
TOTAL_NODE_COUNT = 60
INTERNAL_DIRECTED_LINK_COUNT = 120
OD_CONNECTOR_DIRECTED_LINK_COUNT = 48
TOTAL_LINK_COUNT = 168

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
REACTION_TIME = 1
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2

SHOW_PROGRESS_DELTAT = 100
SPECIFIED_ROUTE_USED = False
ALL_VEHICLES_PARTICIPATE = True

PROFILE_TOP_N = 80
SAVE_PROFILE_FILES = False

BENCHMARK_REFERENCE_EXEC_SIMULATION_SECONDS = 6295.571890000021
BENCHMARK_REFERENCE_SECONDS_PER_TIMESTEP = 20.985239633333403
BENCHMARK_REFERENCE_TRANSACTION_COUNT = 816
BENCHMARK_REFERENCE_T96_TRANSACTION_COUNT = 8
EXPECTED_TRANSACTIONS_ESTABLISHED_AT_T96 = 8

# Partial funcname/filename match only (no fixed line numbers).
INTERESTED_PARTIAL_MATCH_SPECS = (
    ("World.copy", {"funcname": "copy", "filename_contains": "uxsim.py"}),
    ("dill/pickle dumps", {"funcname_contains": "dumps"}),
    ("dill/pickle loads", {"funcname_contains": "loads"}),
    ("run_tvt_mp_driver", {"funcname_contains": "run_tvt_mp_driver"}),
    ("baseline (funcname)", {"funcname_contains": "baseline"}),
    ("candidate (funcname)", {"funcname_contains": "candidate"}),
    ("local virtual (funcname)", {"funcname_contains": "local"}),
    ("decision (funcname)", {"funcname_contains": "decision"}),
    ("transaction (funcname)", {"funcname_contains": "transaction"}),
    ("rank (funcname)", {"funcname_contains": "rank"}),
    ("passage (funcname)", {"funcname_contains": "passage"}),
    ("build_tvt_mp (funcname)", {"funcname_contains": "build_tvt_mp"}),
    ("Node.transfer", {"funcname": "transfer", "filename_contains": "uxsim.py"}),
    ("Vehicle.update", {"funcname": "update", "filename_contains": "uxsim.py"}),
    ("route search", {"funcname_contains": "route_search"}),
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "research_outputs" / "diagnostic" / OUTPUT_DIR_NAME
SCRIPT_PATH = Path(__file__).resolve()


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
# Network (same 6x6 high-demand structure as the 3000-vehicle benchmark)
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


def _manhattan_distance(origin_coord, destination_coord) -> int:
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


# ---------------------------------------------------------------------------
# Vehicle plans and VOT (same as benchmark)
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
                "manhattan_distance": manhattan_distance,
            }
        )
        vehicle_index += 1
    return plans


def verify_vehicle_plans(plans: list[dict]) -> dict:
    if len(plans) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle plan count is {len(plans)}, expected {NUM_VEHICLES}.")
    external = set(EXTERNAL_OD_NODES)
    departures = []
    for index, plan in enumerate(plans):
        if plan["name"] != f"veh_{index}":
            raise RuntimeError(f"Vehicle plan {index} name mismatch.")
        if plan["origin"] not in external or plan["destination"] not in external:
            raise RuntimeError(f"{plan['name']} OD is not external.")
        if plan["manhattan_distance"] < MIN_OD_MANHATTAN_DISTANCE:
            raise RuntimeError(f"{plan['name']} Manhattan distance too small.")
        departures.append(plan["departure_time"])
    if departures[0] != DEPARTURE_START or departures[-1] != DEPARTURE_END:
        raise RuntimeError("Departure window is not 0..999.")
    digest = _vehicle_plan_digest(plans)
    return {
        "vehicle_plan_sha256": digest,
        "first_departure": departures[0],
        "last_departure": departures[-1],
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
            raise RuntimeError(f"VOT sample is not positive finite: {number!r}.")
        values.append(number)
    return values


def build_vehicle_vot_records(plans: list[dict], vot_values: list[float]) -> list[VehicleVotRecord]:
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
# World build and checks
# ---------------------------------------------------------------------------

def build_world_and_network() -> World:
    world = World(
        name=DIAGNOSTIC_NAME,
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

    eligible_names = {node.name for node in world.infer_order_control_eligible_nodes()}
    for node_name in INTERNAL_GRID_NODES:
        if node_name not in eligible_names:
            raise RuntimeError(f"{node_name} is not order-control eligible.")
        if world.get_node(node_name).order_control_eligible is not True:
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


def add_vehicles_to_world(world: World, vot_records: list[VehicleVotRecord]) -> None:
    for record in vot_records:
        world.addVehicle(
            record.origin,
            record.destination,
            record.departure_time,
            name=record.vehicle_name,
            vot_true=record.true_vot_per_second,
            vot_declared=record.declared_vot_per_second,
            participates_in_order_exchange=True,
        )


def verify_network_runtime(world: World) -> None:
    tvt_nodes = [
        node.name for node in world.NODES if node.order_control_type == "time_value"
    ]
    if sorted(tvt_nodes) != sorted(INTERNAL_GRID_NODES):
        raise RuntimeError("TVT-MP nodes are not exactly the 36 internal grid nodes.")
    for node_name in EXTERNAL_OD_NODES:
        node = world.get_node(node_name)
        if node.order_control_type == "time_value":
            raise RuntimeError(f"External OD node {node_name} is TVT-MP target.")
    for link_name, _start, _end, length, _sg in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        if link.length != 200:
            raise RuntimeError(f"Link {link_name} length is not 200 m.")
        if not math.isclose(link.free_flow_speed, FREE_FLOW_SPEED, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"Link {link_name} free-flow speed mismatch.")
        if not math.isclose(link.jam_density, JAM_DENSITY, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"Link {link_name} jam density is not 0.2.")
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("Candidate visit limit is not N=10.")


def count_established_transactions(world: World) -> int:
    """Same source as TVT-MP research output transaction rows (wait registry trades)."""
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    trades = registry.trades_by_transaction_key
    if not isinstance(trades, dict):
        raise RuntimeError("trades_by_transaction_key is not a dict.")
    return len(trades)


def verify_research_output_transaction_count(world: World, expected_count: int) -> None:
    bundle = build_tvt_mp_research_output(world, DIAGNOSTIC_NAME)
    actual = bundle.scenario[0].transaction_count
    if actual != expected_count:
        raise RuntimeError(
            f"Research output transaction_count {actual} != registry count {expected_count}."
        )


def verify_evaluation_end_registry(world: World) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_PROFILE:
        raise RuntimeError(
            f"Expected World.T=={EXPECTED_WORLD_T_AFTER_PROFILE}, got {world.T!r}."
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


def collect_vehicle_state_counts(world: World) -> dict[str, int]:
    counts: dict[str, int] = {}
    for vehicle in world.VEHICLES.values():
        state_value = vehicle.state
        if type(state_value) is not str:
            raise RuntimeError(f"Vehicle {vehicle.name!r} state is not str.")
        counts[state_value] = counts.get(state_value, 0) + 1
    if len(world.VEHICLES) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle count is {len(world.VEHICLES)}, expected {NUM_VEHICLES}.")
    if sum(counts.values()) != NUM_VEHICLES:
        raise RuntimeError("Vehicle state counts do not sum to NUM_VEHICLES.")
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Profiling helpers
# ---------------------------------------------------------------------------

def _profile_stats_to_text(profiler: cProfile.Profile, sort_key: str, top_n: int) -> str:
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats(sort_key)
    stats.print_stats(top_n)
    return stream.getvalue()


def _iter_profile_entries(profiler: cProfile.Profile):
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    for key, value in stats.stats.items():
        filename, lineno, funcname = key
        _cc, nc, tt, ct, _callers = value
        yield {
            "filename": filename,
            "lineno": lineno,
            "funcname": funcname,
            "ncalls": nc,
            "tottime": tt,
            "cumtime": ct,
        }


def _entry_matches_spec(entry: dict, spec: dict) -> bool:
    filename = entry["filename"]
    funcname = entry["funcname"]
    filename_contains = spec.get("filename_contains")
    if filename_contains and filename_contains not in filename:
        return False
    if "funcname" in spec and funcname != spec["funcname"]:
        return False
    funcname_contains = spec.get("funcname_contains")
    if funcname_contains and funcname_contains not in funcname:
        return False
    return True


def _summarize_interested_functions(profiler: cProfile.Profile) -> list[str]:
    lines = ["Interested-function partial-match summary", "-" * 40]
    for label, spec in INTERESTED_PARTIAL_MATCH_SPECS:
        matches = [
            entry
            for entry in _iter_profile_entries(profiler)
            if _entry_matches_spec(entry, spec)
        ]
        lines.append(f"\n{label}:")
        if not matches:
            lines.append("  (no matching entries in this profile scope)")
            continue
        matches.sort(key=lambda item: item["cumtime"], reverse=True)
        for entry in matches[:5]:
            lines.append(
                f"  ncalls={entry['ncalls']} tottime={entry['tottime']:.6f} "
                f"cumtime={entry['cumtime']:.6f} "
                f"{entry['filename']}:{entry['lineno']}({entry['funcname']})"
            )
    return lines


def _refuse_existing_output_directory() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {OUTPUT_DIR}. "
            "Rename or remove it manually before re-running."
        )


def _run_diagnostic() -> int:
    _refuse_existing_output_directory()
    original_recursion_limit = sys.getrecursionlimit()
    try:
        if original_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)
        effective_recursion_limit = sys.getrecursionlimit()

        plans = generate_vehicle_plans()
        plan_audit = verify_vehicle_plans(plans)
        vot_values = generate_vehicle_vots(len(plans))
        if len(vot_values) != NUM_VEHICLES:
            raise RuntimeError("VOT count is not 3000.")
        vot_records = build_vehicle_vot_records(plans, vot_values)

        world = build_world_and_network()
        add_vehicles_to_world(world, vot_records)
        verify_network_runtime(world)
        world.finalize_scenario()
        if world.TSIZE != INTERNAL_TSIZE:
            raise RuntimeError(f"World.TSIZE is {world.TSIZE!r}, expected {INTERNAL_TSIZE}.")
        if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError("N=10 was not kept after finalize.")

        prefix_started = time.perf_counter()
        world.exec_simulation(until_t=UNPROFILED_END_TIMESTEP * world.DELTAT)
        normal_prefix_wall_seconds = time.perf_counter() - prefix_started

        if world.T != WORLD_T_BEFORE_PROFILE:
            raise RuntimeError(
                f"After prefix run expected World.T=={WORLD_T_BEFORE_PROFILE}, "
                f"got {world.T!r}."
            )
        if world._tvt_evaluation_has_ended(EVALUATION_END_TIMESTEP):
            raise RuntimeError("TVT evaluation ended before the profile timestep.")
        if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError("N=10 changed after prefix run.")

        transaction_count_before = count_established_transactions(world)

        gc.collect()
        profiler = cProfile.Profile()
        profile_started = time.perf_counter()
        profiler.enable()
        world.exec_simulation(duration_t2=world.DELTAT)
        profiler.disable()
        profiled_single_timestep_wall_seconds = time.perf_counter() - profile_started

        if world.T != WORLD_T_AFTER_PROFILE:
            raise RuntimeError(
                f"After profile step expected World.T=={WORLD_T_AFTER_PROFILE}, "
                f"got {world.T!r}."
            )
        verify_evaluation_end_registry(world)
        if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError("N=10 changed after profile step.")

        transaction_count_after = count_established_transactions(world)
        transactions_established_at_t96 = (
            transaction_count_after - transaction_count_before
        )
        verify_research_output_transaction_count(world, transaction_count_after)
        if transactions_established_at_t96 != EXPECTED_TRANSACTIONS_ESTABLISHED_AT_T96:
            raise RuntimeError(
                f"transactions_established_at_t96 is {transactions_established_at_t96}, "
                f"expected {EXPECTED_TRANSACTIONS_ESTABLISHED_AT_T96}."
            )

        vehicle_state_counts = collect_vehicle_state_counts(world)
        stats = pstats.Stats(profiler)
        total_function_calls = stats.total_calls

        cumulative_text = _profile_stats_to_text(profiler, "cumulative", PROFILE_TOP_N)
        tottime_text = _profile_stats_to_text(profiler, "tottime", PROFILE_TOP_N)
        interested_lines = _summarize_interested_functions(profiler)

        print("=" * 72)
        print("TVT-MP T=96 single-timestep cProfile diagnostic")
        print("=" * 72)
        print("\nCumulative time top", PROFILE_TOP_N)
        print(cumulative_text, end="")
        print("\nInternal time (tottime) top", PROFILE_TOP_N)
        print(tottime_text, end="")
        print()
        for line in interested_lines:
            print(line)

        _refuse_existing_output_directory()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
        report_path = OUTPUT_DIR / "profile_report.txt"
        summary_path = OUTPUT_DIR / "summary.json"

        report_lines = [
            "TVT-MP 3000-vehicle T=96 single-timestep cProfile diagnostic",
            "Purpose: identify dominant functions for wall-clock at the busiest single timestep.",
            "This is not a research evaluation trial.",
            "Profiling wall-clock must not be used as normal benchmark performance.",
            "",
            "Reference normal benchmark (evaluation T=0..299):",
            f"  exec_simulation_seconds = {BENCHMARK_REFERENCE_EXEC_SIMULATION_SECONDS}",
            f"  seconds_per_evaluation_timestep = {BENCHMARK_REFERENCE_SECONDS_PER_TIMESTEP}",
            f"  transaction_count = {BENCHMARK_REFERENCE_TRANSACTION_COUNT}",
            "",
            "Profile scope:",
            f"  profile_timestep = {PROFILE_TIMESTEP} (one timestep only)",
            f"  unprofiled prefix = T={UNPROFILED_START_TIMESTEP}..{UNPROFILED_END_TIMESTEP}",
            f"  benchmark busiest single timestep T=96 transaction_count = "
            f"{BENCHMARK_REFERENCE_T96_TRANSACTION_COUNT}",
            "",
            f"World.T before profile = {WORLD_T_BEFORE_PROFILE}",
            f"World.T after profile = {WORLD_T_AFTER_PROFILE}",
            f"normal_prefix_wall_seconds = {normal_prefix_wall_seconds}",
            f"profiled_single_timestep_wall_seconds = {profiled_single_timestep_wall_seconds}",
            f"cProfile total function calls = {total_function_calls}",
            f"vehicle_plan_sha256 = {plan_audit['vehicle_plan_sha256']}",
            f"transaction_count_before_t96_step = {transaction_count_before}",
            f"transaction_count_after_t96_step = {transaction_count_after}",
            f"transactions_established_at_t96 = {transactions_established_at_t96}",
            f"vehicle_state_counts = {vehicle_state_counts}",
            f"recursion_limit_before = {original_recursion_limit}",
            f"recursion_limit_effective = {effective_recursion_limit}",
            "production_unchanged = True",
            "",
            "Cumulative time (top by cumulative):",
            cumulative_text.rstrip(),
            "",
            "Internal time / tottime (top by tottime):",
            tottime_text.rstrip(),
            "",
        ]
        report_lines.extend(interested_lines)
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

        summary = {
            "diagnostic_name": DIAGNOSTIC_NAME,
            "profiling_run": True,
            "formal_performance_comparison": False,
            "research_evaluation_trial": False,
            "production_unchanged": True,
            "vehicle_count": NUM_VEHICLES,
            "departure_start": DEPARTURE_START,
            "departure_end": DEPARTURE_END,
            "traffic_seed": TRAFFIC_SEED,
            "demand_gen_seed": DEMAND_GEN_SEED,
            "vot_seed": VOT_SEED,
            "vehicle_plan_sha256": plan_audit["vehicle_plan_sha256"],
            "profile_timestep": PROFILE_TIMESTEP,
            "unprofiled_start_timestep": UNPROFILED_START_TIMESTEP,
            "unprofiled_end_timestep": UNPROFILED_END_TIMESTEP,
            "world_t_before_profile": WORLD_T_BEFORE_PROFILE,
            "world_t_after_profile": WORLD_T_AFTER_PROFILE,
            "profiled_timestep_count": PROFILED_TIMESTEP_COUNT,
            "normal_prefix_wall_seconds": normal_prefix_wall_seconds,
            "profiled_single_timestep_wall_seconds": profiled_single_timestep_wall_seconds,
            "benchmark_reference_exec_simulation_seconds": (
                BENCHMARK_REFERENCE_EXEC_SIMULATION_SECONDS
            ),
            "benchmark_reference_seconds_per_timestep": (
                BENCHMARK_REFERENCE_SECONDS_PER_TIMESTEP
            ),
            "benchmark_reference_transactions": BENCHMARK_REFERENCE_TRANSACTION_COUNT,
            "benchmark_reference_t96_transaction_count": (
                BENCHMARK_REFERENCE_T96_TRANSACTION_COUNT
            ),
            "transaction_count_before_t96_step": transaction_count_before,
            "total_transactions_after_t96": transaction_count_after,
            "transactions_established_at_t96": transactions_established_at_t96,
            "vehicle_state_counts_after_t96": vehicle_state_counts,
            "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
            "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
            "clearance_timesteps": CLEARANCE_TIMESTEPS,
            "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
            "internal_tsize": INTERNAL_TSIZE,
            "original_python_recursion_limit": original_recursion_limit,
            "effective_python_recursion_limit": effective_recursion_limit,
            "profile_top_n": PROFILE_TOP_N,
            "cprofile_total_function_calls": total_function_calls,
            "profile_report_path": str(report_path),
            "output_directory": str(OUTPUT_DIR),
        }
        summary_path.write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0
    finally:
        sys.setrecursionlimit(original_recursion_limit)


# ---------------------------------------------------------------------------
# Static validation
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
        "World",
        "generate_vehicle_plans",
        "generate_vehicle_vots",
        "build_world_and_network",
        "_run_diagnostic",
        "main",
        "Profile",
        "open",
        "cProfile",
    }
    for name in _call_names(function_node):
        if name in forbidden:
            raise RuntimeError(f"Static validation must not call {name}.")


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


def _assert_does_not_monkey_patch_production() -> None:
    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden_unittest_mock = "unittest" + "." + "mock"
    forbidden_monkey_patch_combo = "monkey" + "patch"
    forbidden_setattr_uxsim = "setattr" + "(" + "uxsim"
    for fragment in (
        forbidden_unittest_mock,
        forbidden_monkey_patch_combo,
        forbidden_setattr_uxsim,
    ):
        if fragment in source_text:
            raise RuntimeError(
                f"This script must not monkey-patch production ({fragment!r} found)."
            )


def _assert_does_not_import_forbidden_modules(tree: ast.Module) -> None:
    forbidden_benchmark = (
        "run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_short_benchmark"
    )
    forbidden_profile = "tvt_global_baseline_profile"
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        for module in modules:
            if forbidden_benchmark in module:
                raise RuntimeError("Must not import the research benchmark module.")
            if forbidden_profile in module:
                raise RuntimeError("Must not import past profiling diagnostic modules.")


def _assert_exec_simulation_and_cprofile_contract(tree: ast.Module) -> None:
    run_function = _function_node(tree, "_run_diagnostic")
    if run_function is None:
        raise RuntimeError("_run_diagnostic is missing.")
    exec_calls = []
    for node in ast.walk(run_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "exec_simulation":
            continue
        exec_calls.append(node)
    if len(exec_calls) != 2:
        raise RuntimeError(
            f"_run_diagnostic must call exec_simulation exactly twice (found {len(exec_calls)})."
        )
    until_calls = [
        call
        for call in exec_calls
        if any(keyword.arg == "until_t" for keyword in call.keywords)
    ]
    duration_calls = [
        call
        for call in exec_calls
        if any(keyword.arg == "duration_t2" for keyword in call.keywords)
    ]
    if len(until_calls) != 1:
        raise RuntimeError("Prefix exec_simulation must use until_t once.")
    if len(duration_calls) != 1:
        raise RuntimeError("Profile exec_simulation must use duration_t2 once.")

    enable_lineno = None
    disable_lineno = None
    for node in ast.walk(run_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "enable":
            enable_lineno = node.lineno
        if node.func.attr == "disable":
            disable_lineno = node.lineno
    profile_lineno = duration_calls[0].lineno
    if enable_lineno is None or disable_lineno is None:
        raise RuntimeError("cProfile enable/disable must wrap the profile step.")
    if not (enable_lineno < profile_lineno < disable_lineno):
        raise RuntimeError(
            "duration_t2 exec_simulation must appear between enable and disable."
        )


def _assert_main_static_branch(tree: ast.Module) -> None:
    main_function = _function_node(tree, "main")
    if main_function is None:
        raise RuntimeError("main is missing.")
    static_calls = _call_names(main_function)
    if "exec_simulation" in static_calls or "mkdir" in static_calls:
        raise RuntimeError("main must not simulate or create directories itself.")
    if "_run_diagnostic" not in static_calls:
        raise RuntimeError("main must call _run_diagnostic on the normal path.")
    if "validate_static_contract" not in static_calls:
        raise RuntimeError("main must call validate_static_contract for --static-validate-only.")


def validate_static_contract() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory must not exist: {OUTPUT_DIR}.")
    if NUM_VEHICLES != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 999:
        raise RuntimeError("Departure window must be 0..999.")
    if PROFILE_TIMESTEP != 96:
        raise RuntimeError("PROFILE_TIMESTEP must be 96.")
    if EVALUATION_END_TIMESTEP != PROFILE_TIMESTEP:
        raise RuntimeError("EVALUATION_END_TIMESTEP must equal PROFILE_TIMESTEP.")
    if PROFILED_TIMESTEP_COUNT != 1:
        raise RuntimeError("PROFILED_TIMESTEP_COUNT must be 1.")
    if UNPROFILED_END_TIMESTEP != 95:
        raise RuntimeError("UNPROFILED_END_TIMESTEP must be 95.")
    if EVALUATION_END_TIMESTEP != 96:
        raise RuntimeError("EVALUATION_END_TIMESTEP must be 96.")
    if BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("BASELINE_HORIZON_STEPS must be 30.")
    if INTERNAL_TSIZE != 127:
        raise RuntimeError("INTERNAL_TSIZE must be 127.")
    if INTERNAL_TSIZE != EVALUATION_END_TIMESTEP + BASELINE_HORIZON_STEPS + 1:
        raise RuntimeError("INTERNAL_TSIZE relation must hold.")
    if MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("MAX_CANDIDATE_VISIT_COUNT must be 10.")
    if CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("CLEARANCE_TIMESTEPS must be 1.")
    if TRAFFIC_SEED != 0 or DEMAND_GEN_SEED != 42 or VOT_SEED != 1:
        raise RuntimeError("Seeds must match benchmark.")
    if INTERNAL_LINK_LENGTH != 200 or OD_CONNECTOR_LENGTH != 200:
        raise RuntimeError("All links must be 200 m.")
    if not math.isclose(FREE_FLOW_SPEED, FREE_FLOW_SPEED_KMH / 3.6, rel_tol=0.0, abs_tol=1e-9):
        raise RuntimeError("FREE_FLOW_SPEED must be 60/3.6.")
    if JAM_DENSITY != 0.2:
        raise RuntimeError("JAM_DENSITY must be 0.2.")
    if PROFILE_TOP_N != 80:
        raise RuntimeError("PROFILE_TOP_N must be 80.")
    if WORLD_COPY_RECURSION_LIMIT != 50000:
        raise RuntimeError("WORLD_COPY_RECURSION_LIMIT must be 50000.")
    if SPECIFIED_ROUTE_USED is not False or ALL_VEHICLES_PARTICIPATE is not True:
        raise RuntimeError("Route/participation flags mismatch.")
    if OUTPUT_DIR_NAME != DIAGNOSTIC_NAME:
        raise RuntimeError("Output directory name must match diagnostic name.")

    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    assigned = _module_assigned_constants(tree)
    expected = {
        "NUM_VEHICLES": 3000,
        "DEPARTURE_START": 0,
        "DEPARTURE_END": 999,
        "PROFILE_TIMESTEP": 96,
        "UNPROFILED_END_TIMESTEP": 95,
        "PROFILED_TIMESTEP_COUNT": 1,
        "EVALUATION_END_TIMESTEP": 96,
        "BASELINE_HORIZON_STEPS": 30,
        "INTERNAL_TSIZE": 127,
        "MAX_CANDIDATE_VISIT_COUNT": 10,
        "CLEARANCE_TIMESTEPS": 1,
        "TRAFFIC_SEED": 0,
        "DEMAND_GEN_SEED": 42,
        "VOT_SEED": 1,
        "PROFILE_TOP_N": 80,
        "WORLD_COPY_RECURSION_LIMIT": 50000,
    }
    for name, value in expected.items():
        if assigned.get(name) != value:
            raise RuntimeError(f"Module constant {name} must be {value}.")

    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    _assert_static_function_does_not_run(validator)
    _assert_does_not_monkey_patch_production()
    _assert_does_not_import_forbidden_modules(tree)
    _assert_addlink_no_capacity_in_out_keywords(tree)
    _assert_exec_simulation_and_cprofile_contract(tree)
    _assert_main_static_branch(tree)


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
    return _run_diagnostic()


if __name__ == "__main__":
    raise SystemExit(main())
