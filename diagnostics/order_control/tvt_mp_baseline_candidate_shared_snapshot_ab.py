# DIAGNOSTIC SCRIPT — NOT production, a regression test, or a research trial.
#
# A/B check of one idea: in the same real timestep, create the World snapshot
# bytes once during baseline preparation and reuse those same bytes for the
# Candidate set. Each FIFO-true Candidate still pickle.loads its own World.
#
# Mode A is current production:
#   baseline preparation calls World.copy (one dumps and one loads)
#   the Candidate set calls serialize once when any FIFO-true Candidate exists
#   each FIFO-true Candidate loads its own World
#
# Mode B changes only the number of serializations inside one driver call:
#   baseline preparation dumps the real World once and loads the fork from it
#   the Candidate set returns those same bytes and does not dump again
#   each FIFO-true Candidate still loads its own World
#   the bytes are dropped when that driver call returns
#
# This does not replace the existing Candidate-set sharing (one dumps per set,
# one loads per Candidate). It only asks whether the baseline dumps and the
# Candidate-set dumps can be the same bytes.
#
# Conditions match
# research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_shared_serialization_validation.py
# including all vehicles participating. That script is not imported.
#
# Run from the repository root:
#   python diagnostics/order_control/tvt_mp_baseline_candidate_shared_snapshot_ab.py --static-validate-only
#   python diagnostics/order_control/tvt_mp_baseline_candidate_shared_snapshot_ab.py

from __future__ import annotations

import ast
import csv
import gc
import hashlib
import json
import math
import random
import sys
import time
import weakref
from pathlib import Path

import dill
import numpy as np

import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.order_control_tvt_mp_local_virtual_calculation_set as candidate_set_module
import uxsim.uxsim as uxsim_module
from uxsim import World
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

# ---------------------------------------------------------------------------
# Conditions. Same research conditions as the T=0..299 validation script.
# ---------------------------------------------------------------------------

DIAGNOSTIC_NAME = (
    "tvt_mp_baseline_candidate_shared_snapshot_ab_seed_0_vot_seed_1_eval_300"
)
OUTPUT_DIR_NAME = DIAGNOSTIC_NAME
DIAGNOSTIC_ONLY = True

NUM_VEHICLES = 3000
GRID_SIZE = 6
DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5

EVALUATION_START_TIMESTEP = 0
EVALUATION_END_TIMESTEP = 299
EXPECTED_WORLD_T_AFTER_SIM = 300
SIMULATED_EVALUATION_TIMESTEPS = 300
BASELINE_HORIZON_STEPS = 30
MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1
INTERNAL_TSIZE = 330

TRAFFIC_SEED = 0
DEMAND_GEN_SEED = 42
VOT_SEED = 1
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

ALL_VEHICLES_PARTICIPATE = True
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
REACTION_TIME = 1
LINK_LENGTH = 200
FREE_FLOW_SPEED = 60 / 3.6
JAM_DENSITY = 0.2
SHOW_PROGRESS_DELTAT = 600
WORLD_COPY_RECURSION_LIMIT = 50000

EXPECTED_VEHICLE_PLAN_SHA256 = (
    "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
)

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)
VEHICLE_VOT_CSV_NAME = "vehicle_vot.csv"
CSV_COLUMNS_IGNORED_IN_COMPARISON = ("scenario_name",)

ROUND_ORDERS = (
    ("round_1", ("A", "B")),
    ("round_2", ("B", "A")),
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "research_outputs" / "diagnostic" / OUTPUT_DIR_NAME

ORIGINAL_WORLD_COPY = uxsim_module.World.copy
ORIGINAL_DRIVER = driver_module.run_tvt_mp_driver
ORIGINAL_SERIALIZE = candidate_set_module.serialize_tvt_mp_candidate_real_world_snapshot
ORIGINAL_BUILD = (
    candidate_set_module.build_tvt_mp_candidate_local_state_from_serialized_world
)
ORIGINAL_DILL_LOADS = dill.loads
ORIGINAL_DILL_DUMPS = dill.dumps


# ---------------------------------------------------------------------------
# One driver call. Bytes live here and are dropped in the driver finally.
# ---------------------------------------------------------------------------

class RestoredWorldLedgerRead(RuntimeError):
    """The restored Candidate World rank ledger was read. Stop the diagnosis."""


class ActiveDriverSnapshot:
    """Bytes for the driver call that is running now. Not a cross-timestep cache."""

    def __init__(self):
        self.token = 0
        self.real_world = None
        self.world_id = None
        self.timestep = None
        self.bytes_for_this_driver = None
        self.snapshot_token = None
        self.baseline_fork_ref = None
        self.candidate_local_world_refs = []
        self.guard_candidate_load = False
        self.driver_finished_with_bytes_cleared = 0


class RunCounters:
    def __init__(self):
        self.baseline_dumps_count = 0
        self.baseline_dumps_seconds = 0.0
        self.baseline_loads_count = 0
        self.baseline_loads_seconds = 0.0
        self.candidate_serialize_count = 0
        self.candidate_serialize_seconds = 0.0
        self.candidate_loads_count = 0
        self.candidate_loads_seconds = 0.0
        self.shared_bytes_reuse_count = 0
        self.serialized_bytes_total = 0
        self.serialized_bytes_maximum = 0
        self.serialized_bytes_samples = 0
        self.candidate_fingerprints = []
        self.candidate_start_real_traffic_rng = []
        self.candidate_start_real_order_rng = []
        self.candidate_start_loaded_traffic_rng = []
        self.candidate_start_loaded_order_rng = []


ACTIVE = ActiveDriverSnapshot()
COUNTERS = RunCounters()
MODE = None
PATCHES = []


def _reset_active_and_counters():
    global ACTIVE, COUNTERS
    ACTIVE = ActiveDriverSnapshot()
    COUNTERS = RunCounters()


class RestoredRankLedgerGuard(dict):
    """Raises if Candidate code reads the restored World's rank ledger."""

    def _refuse(self, action):
        raise RestoredWorldLedgerRead(
            "Candidate local calculation read the restored World's rank ledger "
            f"({action}) at restored World.T={self.diagnostic_timestep!r}. "
            "The diagnosis stopped. Production was not changed, and mode B was "
            "not given a fallback serialize."
        )

    def __getitem__(self, key):
        self._refuse(f"read key {key!r}")

    def __contains__(self, key):
        self._refuse("membership test")

    def __iter__(self):
        self._refuse("iteration")

    def __len__(self):
        self._refuse("len")

    def get(self, key, default=None):
        self._refuse("get")

    def keys(self):
        self._refuse("keys")

    def values(self):
        self._refuse("values")

    def items(self):
        self._refuse("items")

    def copy(self):
        self._refuse("copy")

    def pop(self, key, default=None):
        self._refuse("pop")

    def setdefault(self, key, default=None):
        self._refuse("setdefault")

    def update(self, *args, **kwargs):
        self._refuse("update")


def _install_rank_ledger_guard(local_world):
    guard = RestoredRankLedgerGuard()
    guard.diagnostic_timestep = local_world.T
    local_world.order_control_tvt_rank_states_by_node_name = guard


def _alive_baseline_fork_world():
    ref = ACTIVE.baseline_fork_ref
    if ref is None:
        return None
    return ref()


def _check_local_world_independence(local_world):
    baseline_world = _alive_baseline_fork_world()
    if baseline_world is not None and local_world is baseline_world:
        raise RuntimeError("A Candidate local World is the baseline fork World.")
    for prior_ref in ACTIVE.candidate_local_world_refs:
        prior_world = prior_ref()
        if prior_world is not None and local_world is prior_world:
            raise RuntimeError(
                "A Candidate local World was reused for another Candidate."
            )
    ACTIVE.candidate_local_world_refs.append(weakref.ref(local_world))


def _note_serialized_bytes(data):
    size = len(data)
    COUNTERS.serialized_bytes_total += size
    COUNTERS.serialized_bytes_samples += 1
    if size > COUNTERS.serialized_bytes_maximum:
        COUNTERS.serialized_bytes_maximum = size


def _require_shared_snapshot(real_world, snapshot):
    if ACTIVE.real_world is None:
        raise RuntimeError(
            "Mode B Candidate serialize ran outside a driver call. "
            "Refusing to serialize again."
        )
    if real_world is not ACTIVE.real_world or id(real_world) != ACTIVE.world_id:
        raise RuntimeError(
            "Mode B snapshot is not for this real World object. "
            "Refusing to serialize again."
        )
    if real_world.T != ACTIVE.timestep:
        raise RuntimeError(
            "Mode B snapshot timestep "
            f"{ACTIVE.timestep!r} does not match real World.T {real_world.T!r}. "
            "Refusing to serialize again."
        )
    if ACTIVE.snapshot_token != ACTIVE.token:
        raise RuntimeError(
            "Mode B snapshot belongs to a previous driver call. "
            "Refusing to serialize again."
        )
    if type(snapshot) is not bytes or len(snapshot) == 0:
        raise RuntimeError(
            "Mode B snapshot is not a non-empty bytes object. "
            "Refusing to serialize again."
        )


def _baseline_copy(world, share_bytes):
    if ACTIVE.real_world is None or world is not ACTIVE.real_world:
        return ORIGINAL_WORLD_COPY(world)
    if ACTIVE.bytes_for_this_driver is not None:
        raise RuntimeError(
            "Baseline snapshot bytes were already created in this driver call."
        )
    started = time.perf_counter()
    data = ORIGINAL_DILL_DUMPS(world)
    COUNTERS.baseline_dumps_count += 1
    COUNTERS.baseline_dumps_seconds += time.perf_counter() - started
    _note_serialized_bytes(data)
    if share_bytes:
        ACTIVE.bytes_for_this_driver = data
        ACTIVE.world_id = id(world)
        ACTIVE.timestep = world.T
        ACTIVE.snapshot_token = ACTIVE.token
    started = time.perf_counter()
    loaded = ORIGINAL_DILL_LOADS(data)
    COUNTERS.baseline_loads_count += 1
    COUNTERS.baseline_loads_seconds += time.perf_counter() - started
    ACTIVE.baseline_fork_ref = weakref.ref(loaded)
    return loaded


def baseline_copy_mode_a(world):
    return _baseline_copy(world, share_bytes=False)


def baseline_copy_mode_b(world):
    return _baseline_copy(world, share_bytes=True)


def candidate_serialize_mode_a(real_world):
    started = time.perf_counter()
    data = ORIGINAL_SERIALIZE(real_world)
    COUNTERS.candidate_serialize_count += 1
    COUNTERS.candidate_serialize_seconds += time.perf_counter() - started
    _note_serialized_bytes(data)
    return data


def candidate_serialize_mode_b(real_world):
    snapshot = ACTIVE.bytes_for_this_driver
    _require_shared_snapshot(real_world, snapshot)
    COUNTERS.shared_bytes_reuse_count += 1
    return snapshot


def _binding_fingerprint(sequence):
    rows = []
    for visit in sequence.visits_in_binding_order:
        vehicle_name, visit_id = visit.visit_key
        rows.append(
            (
                vehicle_name,
                int(visit_id),
                int(visit.binding_rank),
                visit.route_next_link_name,
                visit.inlink_name,
                visit.trade_role.value,
            )
        )
    return rows


def _candidate_fingerprint(state):
    return {
        "node": state.target_node_name,
        "timestep": int(state.real_world_timestep_T),
        "inlinks": [link.name for link in state.inlinks],
        "outlinks": [link.name for link in state.outlinks],
        "vehicles": [vehicle.name for vehicle in state.local_vehicles],
        "binding": _binding_fingerprint(state.binding_rank_sequence),
    }


def guarded_candidate_loads(data):
    started = time.perf_counter()
    loaded = ORIGINAL_DILL_LOADS(data)
    elapsed = time.perf_counter() - started
    if ACTIVE.guard_candidate_load:
        COUNTERS.candidate_loads_count += 1
        COUNTERS.candidate_loads_seconds += elapsed
        _install_rank_ledger_guard(loaded)
        COUNTERS.candidate_start_loaded_traffic_rng.append(_rng_state(loaded.rng))
        COUNTERS.candidate_start_loaded_order_rng.append(
            _rng_state(loaded.order_control_rng)
        )
    return loaded


def build_candidate_local_state_counting(real_world, sequence, serialized):
    loads_before = COUNTERS.candidate_loads_count
    COUNTERS.candidate_start_real_traffic_rng.append(_rng_state(real_world.rng))
    COUNTERS.candidate_start_real_order_rng.append(
        _rng_state(real_world.order_control_rng)
    )
    ACTIVE.guard_candidate_load = True
    try:
        state = ORIGINAL_BUILD(real_world, sequence, serialized)
    finally:
        ACTIVE.guard_candidate_load = False
    if COUNTERS.candidate_loads_count != loads_before + 1:
        raise RuntimeError(
            "One Candidate build did not pickle.loads exactly one World."
        )
    _check_local_world_independence(state.local_world)
    COUNTERS.candidate_fingerprints.append(_candidate_fingerprint(state))
    return state


def wrapped_driver(real_world):
    ACTIVE.token += 1
    ACTIVE.real_world = real_world
    ACTIVE.world_id = None
    ACTIVE.timestep = None
    ACTIVE.bytes_for_this_driver = None
    ACTIVE.snapshot_token = None
    ACTIVE.baseline_fork_ref = None
    ACTIVE.candidate_local_world_refs = []
    try:
        return ORIGINAL_DRIVER(real_world)
    finally:
        ACTIVE.bytes_for_this_driver = None
        ACTIVE.snapshot_token = None
        ACTIVE.real_world = None
        ACTIVE.world_id = None
        ACTIVE.timestep = None
        ACTIVE.baseline_fork_ref = None
        ACTIVE.candidate_local_world_refs = []
        ACTIVE.guard_candidate_load = False
        ACTIVE.driver_finished_with_bytes_cleared += 1


def install_wrappers(mode):
    global MODE
    if PATCHES:
        raise RuntimeError("Wrappers are already installed.")
    if mode == "A":
        copy_function = baseline_copy_mode_a
        serialize_function = candidate_serialize_mode_a
    elif mode == "B":
        copy_function = baseline_copy_mode_b
        serialize_function = candidate_serialize_mode_b
    else:
        raise RuntimeError(f"Unknown mode {mode!r}.")
    MODE = mode
    _assign_patch(uxsim_module.World, "copy", copy_function)
    _assign_patch(driver_module, "run_tvt_mp_driver", wrapped_driver)
    _assign_patch(
        candidate_set_module,
        "serialize_tvt_mp_candidate_real_world_snapshot",
        serialize_function,
    )
    _assign_patch(
        candidate_set_module,
        "build_tvt_mp_candidate_local_state_from_serialized_world",
        build_candidate_local_state_counting,
    )
    _assign_patch(dill, "loads", guarded_candidate_loads)


def _assign_patch(owner, name, wrapper):
    PATCHES.append((owner, name, getattr(owner, name)))
    setattr(owner, name, wrapper)


def restore_wrappers():
    global MODE
    while PATCHES:
        owner, name, original = PATCHES.pop()
        setattr(owner, name, original)
    MODE = None


def _wrappers_are_original():
    return (
        uxsim_module.World.copy is ORIGINAL_WORLD_COPY
        and driver_module.run_tvt_mp_driver is ORIGINAL_DRIVER
        and candidate_set_module.serialize_tvt_mp_candidate_real_world_snapshot
        is ORIGINAL_SERIALIZE
        and candidate_set_module.build_tvt_mp_candidate_local_state_from_serialized_world
        is ORIGINAL_BUILD
        and dill.loads is ORIGINAL_DILL_LOADS
        and not PATCHES
    )


# ---------------------------------------------------------------------------
# Network and vehicles. Copied from the T=0..299 validation conditions.
# All vehicles participate. There is no nonparticipation sample.
# ---------------------------------------------------------------------------

def _grid_node_name(row, column):
    return f"g_{row}_{column}"


def _external_od_node_names():
    names = []
    for column in range(GRID_SIZE):
        names.append(f"top_{column}")
        names.append(f"bottom_{column}")
    for row in range(GRID_SIZE):
        names.append(f"left_{row}")
        names.append(f"right_{row}")
    return tuple(names)


def _internal_grid_node_names():
    names = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            names.append(_grid_node_name(row, column))
    return tuple(names)


def _od_to_grid_coord_map():
    mapping = {}
    for column in range(GRID_SIZE):
        mapping[f"top_{column}"] = (0, column)
        mapping[f"bottom_{column}"] = (GRID_SIZE - 1, column)
    for row in range(GRID_SIZE):
        mapping[f"left_{row}"] = (row, 0)
        mapping[f"right_{row}"] = (row, GRID_SIZE - 1)
    return mapping


def _build_link_specs():
    internal = []
    connectors = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            internal.append((f"h_{row}_{column}_{column + 1}", left_node, right_node, 0))
            internal.append((f"h_{row}_{column + 1}_{column}", right_node, left_node, 0))
    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            internal.append((f"v_{row}_{row + 1}_{column}", upper_node, lower_node, 1))
            internal.append((f"v_{row + 1}_{row}_{column}", lower_node, upper_node, 1))
    for column in range(GRID_SIZE):
        top_node = f"top_{column}"
        bottom_node = f"bottom_{column}"
        north_grid = _grid_node_name(0, column)
        south_grid = _grid_node_name(GRID_SIZE - 1, column)
        connectors.append((f"top_{column}_to_g_0_{column}", top_node, north_grid, 1))
        connectors.append((f"g_0_{column}_to_top_{column}", north_grid, top_node, 1))
        connectors.append((f"bottom_{column}_to_g_5_{column}", bottom_node, south_grid, 1))
        connectors.append((f"g_5_{column}_to_bottom_{column}", south_grid, bottom_node, 1))
    for row in range(GRID_SIZE):
        left_node = f"left_{row}"
        right_node = f"right_{row}"
        west_grid = _grid_node_name(row, 0)
        east_grid = _grid_node_name(row, GRID_SIZE - 1)
        connectors.append((f"left_{row}_to_g_{row}_0", left_node, west_grid, 0))
        connectors.append((f"g_{row}_0_to_left_{row}", west_grid, left_node, 0))
        connectors.append((f"right_{row}_to_g_{row}_5", right_node, east_grid, 0))
        connectors.append((f"g_{row}_5_to_right_{row}", east_grid, right_node, 0))
    return tuple(internal), tuple(connectors)


INTERNAL_GRID_NODES = _internal_grid_node_names()
EXTERNAL_OD_NODES = _external_od_node_names()
OD_TO_GRID_COORD = _od_to_grid_coord_map()
INTERNAL_LINK_SPECS, OD_CONNECTOR_LINK_SPECS = _build_link_specs()
ALL_LINK_SPECS = INTERNAL_LINK_SPECS + OD_CONNECTOR_LINK_SPECS


def generate_vehicle_plans():
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    vehicle_index = 0
    while len(plans) < NUM_VEHICLES:
        origin = rng.choice(EXTERNAL_OD_NODES)
        destination = rng.choice(EXTERNAL_OD_NODES)
        if origin == destination:
            continue
        origin_coord = OD_TO_GRID_COORD[origin]
        destination_coord = OD_TO_GRID_COORD[destination]
        manhattan_distance = abs(origin_coord[0] - destination_coord[0]) + abs(
            origin_coord[1] - destination_coord[1]
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


def _vehicle_plan_digest(plans):
    hasher = hashlib.sha256()
    for plan in plans:
        line = (
            f"{plan['name']}|{plan['origin']}|{plan['destination']}|"
            f"{plan['departure_time']!r}\n"
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def generate_vehicle_vots(count):
    rng = np.random.default_rng(VOT_SEED)
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    values = []
    for value in samples:
        number = float(value)
        if math.isfinite(number) is not True or number <= 0.0:
            raise RuntimeError(f"VOT sample is not a positive finite float: {number!r}.")
        values.append(number)
    return values


def build_world(plans, vot_values):
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
            world.addNode(_grid_node_name(row, column), column * spacing, -row * spacing)
    for column in range(GRID_SIZE):
        world.addNode(f"top_{column}", column * spacing, spacing)
        world.addNode(f"bottom_{column}", column * spacing, -GRID_SIZE * spacing)
    for row in range(GRID_SIZE):
        world.addNode(f"left_{row}", -spacing, -row * spacing)
        world.addNode(f"right_{row}", GRID_SIZE * spacing, -row * spacing)
    for link_name, start_node, end_node, signal_group in ALL_LINK_SPECS:
        world.addLink(
            link_name,
            start_node,
            end_node,
            length=LINK_LENGTH,
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
    world.order_control_tvt_evaluation_end_timestep = EVALUATION_END_TIMESTEP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    for plan, vot in zip(plans, vot_values):
        world.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
            vot_true=vot,
            vot_declared=vot,
            participates_in_order_exchange=True,
        )
    return world


# ---------------------------------------------------------------------------
# One fresh World, one mode, T=0..299.
# ---------------------------------------------------------------------------

def _freeze(value):
    if isinstance(value, dict):
        return {str(key): _freeze(value[key]) for key in value}
    if isinstance(value, (list, tuple)):
        return [_freeze(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _rng_state(rng):
    return _freeze(rng.bit_generator.state)


def _route_names(vehicle):
    rows = []
    for entry in vehicle.log_t_link:
        point = entry[1]
        if hasattr(point, "name"):
            point_name = point.name
        else:
            point_name = point
        rows.append([entry[0], point_name])
    return rows


def _vehicle_states(world):
    rows = []
    for vehicle in world.VEHICLES.values():
        link_name = None if vehicle.link is None else vehicle.link.name
        rows.append(
            {
                "name": vehicle.name,
                "state": vehicle.state,
                "departure_time": vehicle.departure_time,
                "departure_time_in_second": vehicle.departure_time_in_second,
                "arrival_time": vehicle.arrival_time,
                "travel_time": vehicle.travel_time,
                "link": link_name,
                "x": vehicle.x,
                "route": _route_names(vehicle),
            }
        )
    return rows


def _state_counts(world):
    counts = {}
    for vehicle in world.VEHICLES.values():
        counts[vehicle.state] = counts.get(vehicle.state, 0) + 1
    return counts


def _rank_ledgers(world):
    ledgers = {}
    for node_name in INTERNAL_GRID_NODES:
        state = world.order_control_tvt_rank_states_by_node_name[node_name]
        ledgers[node_name] = _freeze(state.export_state())
    return ledgers


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames), list(reader)


def _write_vehicle_vot_csv(path, plans, vot_values):
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
        for plan, vot in zip(plans, vot_values):
            writer.writerow(
                {
                    "vehicle_name": plan["name"],
                    "origin": plan["origin"],
                    "destination": plan["destination"],
                    "departure_timestep": plan["departure_time"],
                    "participates_in_order_exchange": True,
                    "true_vot_per_second": vot,
                    "declared_vot_per_second": vot,
                    "traffic_seed": TRAFFIC_SEED,
                    "vot_seed": VOT_SEED,
                    "demand_gen_seed": DEMAND_GEN_SEED,
                }
            )


def _performance_row(round_name, mode, exec_simulation_seconds, script_seconds, world, transaction_count):
    if COUNTERS.serialized_bytes_samples == 0:
        average_bytes = None
    else:
        average_bytes = COUNTERS.serialized_bytes_total / COUNTERS.serialized_bytes_samples
    return {
        "round": round_name,
        "mode": mode,
        "exec_simulation_seconds": exec_simulation_seconds,
        "script_total_seconds": script_seconds,
        "baseline_snapshot_dumps_count": COUNTERS.baseline_dumps_count,
        "baseline_snapshot_dumps_seconds": COUNTERS.baseline_dumps_seconds,
        "baseline_loads_count": COUNTERS.baseline_loads_count,
        "baseline_loads_seconds": COUNTERS.baseline_loads_seconds,
        "candidate_serialize_count": COUNTERS.candidate_serialize_count,
        "candidate_serialize_seconds": COUNTERS.candidate_serialize_seconds,
        "candidate_loads_count": COUNTERS.candidate_loads_count,
        "candidate_loads_seconds": COUNTERS.candidate_loads_seconds,
        "shared_bytes_reuse_count": COUNTERS.shared_bytes_reuse_count,
        "serialized_bytes_average": average_bytes,
        "serialized_bytes_maximum": COUNTERS.serialized_bytes_maximum,
        "transaction_count": transaction_count,
        "final_world_T": world.T,
        "vehicle_state_counts": _state_counts(world),
        "driver_calls_cleared": ACTIVE.driver_finished_with_bytes_cleared,
        "shared_bytes_remaining": ACTIVE.bytes_for_this_driver is not None,
    }


def _capture_result(round_name, mode, exec_simulation_seconds, script_seconds, world, plans, vot_values):
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"{round_name} {mode} finished at World.T={world.T!r}, "
            f"expected {EXPECTED_WORLD_T_AFTER_SIM}."
        )
    if ACTIVE.bytes_for_this_driver is not None:
        raise RuntimeError(f"{round_name} {mode} still holds snapshot bytes after the run.")
    bundle = build_tvt_mp_research_output(world, DIAGNOSTIC_NAME)
    run_dir = OUTPUT_DIR / f"{round_name}_{mode}"
    run_dir.mkdir(parents=False, exist_ok=False)
    write_tvt_mp_research_output_csv(bundle, run_dir, overwrite=False)
    _write_vehicle_vot_csv(run_dir / VEHICLE_VOT_CSV_NAME, plans, vot_values)
    transaction_count = bundle.scenario[0].transaction_count
    return {
        "performance": _performance_row(
            round_name,
            mode,
            exec_simulation_seconds,
            script_seconds,
            world,
            transaction_count,
        ),
        "world_T": world.T,
        "vehicle_states": _vehicle_states(world),
        "vehicle_state_counts": _state_counts(world),
        "traffic_rng": _rng_state(world.rng),
        "order_control_rng": _rng_state(world.order_control_rng),
        "rank_ledgers": _rank_ledgers(world),
        "transaction_count": transaction_count,
        "candidate_fingerprints": COUNTERS.candidate_fingerprints,
        "candidate_start_real_traffic_rng": COUNTERS.candidate_start_real_traffic_rng,
        "candidate_start_real_order_rng": COUNTERS.candidate_start_real_order_rng,
        "candidate_start_loaded_traffic_rng": COUNTERS.candidate_start_loaded_traffic_rng,
        "candidate_start_loaded_order_rng": COUNTERS.candidate_start_loaded_order_rng,
        "csv_dir": run_dir,
    }


def run_mode_a(round_name, plans, vot_values):
    return _run_one("A", round_name, plans, vot_values)


def run_mode_b(round_name, plans, vot_values):
    return _run_one("B", round_name, plans, vot_values)


def _run_one(mode, round_name, plans, vot_values):
    _reset_active_and_counters()
    gc.collect()
    started_script = time.perf_counter()
    world = build_world(plans, vot_values)
    install_wrappers(mode)
    try:
        started_exec = time.perf_counter()
        world.exec_simulation()
        exec_simulation_seconds = time.perf_counter() - started_exec
    finally:
        restore_wrappers()
    if not _wrappers_are_original():
        raise RuntimeError(f"{round_name} {mode} did not restore production functions.")
    script_seconds = time.perf_counter() - started_script
    return _capture_result(
        round_name,
        mode,
        exec_simulation_seconds,
        script_seconds,
        world,
        plans,
        vot_values,
    )


# ---------------------------------------------------------------------------
# Equality.
# ---------------------------------------------------------------------------

def _preview(value):
    text = repr(value)
    if len(text) > 300:
        return text[:300] + "..."
    return text


def _first_difference(left, right, path):
    if type(left) is not type(right) and not (
        isinstance(left, (int, float)) and isinstance(right, (int, float)) and type(left) is type(right)
    ):
        if type(left) is not type(right):
            return {
                "path": path,
                "left_type": type(left).__name__,
                "right_type": type(right).__name__,
                "left": _preview(left),
                "right": _preview(right),
            }
    if isinstance(left, dict):
        left_keys = list(left.keys())
        right_keys = list(right.keys())
        if left_keys != right_keys:
            return {
                "path": path,
                "reason": "dict keys differ",
                "left_keys": left_keys[:20],
                "right_keys": right_keys[:20],
            }
        for key in left_keys:
            found = _first_difference(left[key], right[key], path + [key])
            if found is not None:
                return found
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return {
                "path": path,
                "reason": "length differs",
                "left_length": len(left),
                "right_length": len(right),
            }
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            found = _first_difference(left_item, right_item, path + [index])
            if found is not None:
                return found
        return None
    if left != right:
        return {"path": path, "left": _preview(left), "right": _preview(right)}
    return None


def _csv_difference(left_dir, right_dir, filename):
    left_header, left_rows = _read_csv(left_dir / filename)
    right_header, right_rows = _read_csv(right_dir / filename)
    if left_header != right_header:
        return {
            "file": filename,
            "reason": "headers differ",
            "left_header": left_header,
            "right_header": right_header,
        }
    if len(left_rows) != len(right_rows):
        return {
            "file": filename,
            "reason": "row count differs",
            "left_rows": len(left_rows),
            "right_rows": len(right_rows),
        }
    compared_columns = [
        name for name in left_header if name not in CSV_COLUMNS_IGNORED_IN_COMPARISON
    ]
    for row_index, (left_row, right_row) in enumerate(zip(left_rows, right_rows)):
        for column in compared_columns:
            if left_row[column] != right_row[column]:
                return {
                    "file": filename,
                    "row_index": row_index,
                    "column": column,
                    "left": left_row[column],
                    "right": right_row[column],
                    "tvt_decision_timestep": left_row.get("tvt_decision_timestep"),
                    "node_name": left_row.get("node_name"),
                    "vehicle_name": left_row.get("vehicle_name"),
                    "visit_id": left_row.get("visit_id"),
                }
    return None


def _attach_difference_context(section, left_value, found):
    path = found.get("path")
    if not isinstance(path, list) or len(path) < 3 or not isinstance(path[2], int):
        return
    index = path[2]
    if not isinstance(left_value, list) or index >= len(left_value):
        return
    row = left_value[index]
    if section == "vehicle_states" and isinstance(row, dict):
        found["vehicle_name"] = row.get("name")
        found["link"] = row.get("link")
        found["state"] = row.get("state")
    if section == "candidate_fingerprints" and isinstance(row, dict):
        found["node"] = row.get("node")
        found["timestep"] = row.get("timestep")
        binding = row.get("binding")
        if len(path) >= 5 and path[3] == "binding" and isinstance(path[4], int):
            visit_index = path[4]
            if isinstance(binding, list) and visit_index < len(binding):
                found["visit"] = binding[visit_index]


def _compare_pair(left, right, label):
    sections = {
        "world_T": (left["world_T"], right["world_T"]),
        "vehicle_state_counts": (
            left["vehicle_state_counts"],
            right["vehicle_state_counts"],
        ),
        "vehicle_states": (left["vehicle_states"], right["vehicle_states"]),
        "traffic_rng": (left["traffic_rng"], right["traffic_rng"]),
        "order_control_rng": (left["order_control_rng"], right["order_control_rng"]),
        "rank_ledgers": (left["rank_ledgers"], right["rank_ledgers"]),
        "transaction_count": (left["transaction_count"], right["transaction_count"]),
        "candidate_fingerprints": (
            left["candidate_fingerprints"],
            right["candidate_fingerprints"],
        ),
        "candidate_start_real_traffic_rng": (
            left["candidate_start_real_traffic_rng"],
            right["candidate_start_real_traffic_rng"],
        ),
        "candidate_start_real_order_rng": (
            left["candidate_start_real_order_rng"],
            right["candidate_start_real_order_rng"],
        ),
        "candidate_start_loaded_traffic_rng": (
            left["candidate_start_loaded_traffic_rng"],
            right["candidate_start_loaded_traffic_rng"],
        ),
        "candidate_start_loaded_order_rng": (
            left["candidate_start_loaded_order_rng"],
            right["candidate_start_loaded_order_rng"],
        ),
    }
    differences = []
    for name, (left_value, right_value) in sections.items():
        found = _first_difference(left_value, right_value, [label, name])
        if found is not None:
            _attach_difference_context(name, left_value, found)
            differences.append(found)
            break
    csv_names = list(RESEARCH_CSV_NAMES) + [VEHICLE_VOT_CSV_NAME]
    if differences:
        csv_names = []
    for filename in csv_names:
        found = _csv_difference(left["csv_dir"], right["csv_dir"], filename)
        if found is not None:
            found["pair"] = label
            differences.append(found)
            break
    return {"pair": label, "equal": len(differences) == 0, "first_difference": differences[:1]}


def _performance_checks(results):
    reasons = []
    round_pairs = (
        ("round_1", "A", "B"),
        ("round_2", "B", "A"),
    )
    for round_name, _first_mode, _second_mode in round_pairs:
        mode_a = results[f"{round_name}_A"]["performance"]
        mode_b = results[f"{round_name}_B"]["performance"]
        if mode_b["candidate_serialize_count"] != 0:
            reasons.append(
                f"{round_name} mode B candidate serialize count is "
                f"{mode_b['candidate_serialize_count']}, expected 0."
            )
        if mode_b["shared_bytes_reuse_count"] <= 0:
            reasons.append(f"{round_name} mode B did not reuse shared snapshot bytes.")
        if mode_a["candidate_loads_count"] != mode_b["candidate_loads_count"]:
            reasons.append(
                f"{round_name} candidate loads differ: "
                f"A={mode_a['candidate_loads_count']} B={mode_b['candidate_loads_count']}."
            )
        if mode_a["baseline_loads_count"] != mode_b["baseline_loads_count"]:
            reasons.append(
                f"{round_name} baseline loads differ: "
                f"A={mode_a['baseline_loads_count']} B={mode_b['baseline_loads_count']}."
            )
        if mode_b["baseline_snapshot_dumps_count"] != mode_a["baseline_snapshot_dumps_count"]:
            reasons.append(
                f"{round_name} baseline dumps differ: "
                f"A={mode_a['baseline_snapshot_dumps_count']} "
                f"B={mode_b['baseline_snapshot_dumps_count']}."
            )
        if mode_b["exec_simulation_seconds"] >= mode_a["exec_simulation_seconds"]:
            reasons.append(
                f"{round_name} mode B exec_simulation_seconds "
                f"{mode_b['exec_simulation_seconds']} is not faster than mode A "
                f"{mode_a['exec_simulation_seconds']}."
            )
        if mode_b["shared_bytes_remaining"] is not False:
            reasons.append(f"{round_name} mode B kept snapshot bytes after the run.")
        if mode_a["final_world_T"] != EXPECTED_WORLD_T_AFTER_SIM:
            reasons.append(f"{round_name} mode A final World.T is not 300.")
        if mode_b["final_world_T"] != EXPECTED_WORLD_T_AFTER_SIM:
            reasons.append(f"{round_name} mode B final World.T is not 300.")
    return reasons


def _decide(results, pair_reports):
    reasons = []
    for report in pair_reports:
        if report["equal"] is not True:
            first = report["first_difference"]
            reasons.append(
                f"{report['pair']} is not equal. First difference: {first!r}."
            )
    reasons.extend(_performance_checks(results))
    return {
        "shared_baseline_candidate_snapshot_is_promising": len(reasons) == 0,
        "reasons_not_to_change_production": reasons,
    }


# ---------------------------------------------------------------------------
# Output.
# ---------------------------------------------------------------------------

def _write_json(path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_performance_csv(path, rows):
    fieldnames = [
        "round",
        "mode",
        "exec_simulation_seconds",
        "script_total_seconds",
        "baseline_snapshot_dumps_count",
        "baseline_snapshot_dumps_seconds",
        "baseline_loads_count",
        "baseline_loads_seconds",
        "candidate_serialize_count",
        "candidate_serialize_seconds",
        "candidate_loads_count",
        "candidate_loads_seconds",
        "shared_bytes_reuse_count",
        "serialized_bytes_average",
        "serialized_bytes_maximum",
        "transaction_count",
        "final_world_T",
        "vehicle_state_counts",
        "driver_calls_cleared",
        "shared_bytes_remaining",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            outgoing = dict(row)
            outgoing["vehicle_state_counts"] = json.dumps(
                outgoing["vehicle_state_counts"], sort_keys=True
            )
            writer.writerow(outgoing)


def _write_run_summary(path, decision, rows):
    lines = [
        "diagnostic_only: true",
        "shared_baseline_candidate_snapshot_is_promising: "
        f"{decision['shared_baseline_candidate_snapshot_is_promising']}",
        "all_vehicles_participate: true",
        "evaluation: T=0..299",
        "baseline_horizon_steps: 30",
        "max_candidate_visit_count: 10",
        "rounds: round_1 A then B; round_2 B then A",
        "",
    ]
    if decision["reasons_not_to_change_production"]:
        lines.append("Do not change production.")
        for reason in decision["reasons_not_to_change_production"]:
            lines.append(f"- {reason}")
        lines.append("")
    for row in rows:
        lines.append(
            f"{row['round']} {row['mode']}: "
            f"exec_simulation_seconds={row['exec_simulation_seconds']} "
            f"baseline_dumps={row['baseline_snapshot_dumps_count']} "
            f"candidate_serialize={row['candidate_serialize_count']} "
            f"candidate_loads={row['candidate_loads_count']} "
            f"shared_bytes_reuse={row['shared_bytes_reuse_count']} "
            f"transactions={row['transaction_count']} "
            f"World.T={row['final_world_T']}"
        )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def _write_outputs(decision, pair_reports, results, stopped_reason):
    rows = [results[key]["performance"] for key in results]
    summary = {
        "diagnostic_only": True,
        "diagnostic_name": DIAGNOSTIC_NAME,
        "all_vehicles_participate": ALL_VEHICLES_PARTICIPATE,
        "evaluation_start_timestep": EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "traffic_seed": TRAFFIC_SEED,
        "demand_gen_seed": DEMAND_GEN_SEED,
        "vot_seed": VOT_SEED,
        "vehicle_plan_sha256": EXPECTED_VEHICLE_PLAN_SHA256,
        "round_orders": [["round_1", ["A", "B"]], ["round_2", ["B", "A"]]],
        "shared_baseline_candidate_snapshot_is_promising": decision[
            "shared_baseline_candidate_snapshot_is_promising"
        ],
        "reasons_not_to_change_production": decision["reasons_not_to_change_production"],
        "stopped_reason": stopped_reason,
        "production_changed": False,
    }
    equality = {
        "diagnostic_only": True,
        "pairs": pair_reports,
        "all_equal": all(report["equal"] for report in pair_reports) if pair_reports else False,
    }
    _write_json(OUTPUT_DIR / "ab_summary.json", summary)
    _write_json(OUTPUT_DIR / "ab_equality.json", equality)
    _write_performance_csv(OUTPUT_DIR / "ab_performance.csv", rows)
    _write_run_summary(OUTPUT_DIR / "run_summary.txt", decision, rows)


def run_diagnostic():
    if OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {OUTPUT_DIR}. "
            "Rename or remove it manually before re-running."
        )
    plans = generate_vehicle_plans()
    plan_digest = _vehicle_plan_digest(plans)
    if plan_digest != EXPECTED_VEHICLE_PLAN_SHA256:
        raise RuntimeError(
            f"Vehicle plan sha256 is {plan_digest}, expected {EXPECTED_VEHICLE_PLAN_SHA256}."
        )
    vot_values = generate_vehicle_vots(NUM_VEHICLES)
    if len(vot_values) != len(plans):
        raise RuntimeError("VOT count does not match the vehicle plan count.")
    original_recursion_limit = sys.getrecursionlimit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    results = {}
    stopped_reason = None
    try:
        if original_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)
        for round_name, modes in ROUND_ORDERS:
            for mode in modes:
                print(f"starting {round_name} mode {mode}", flush=True)
                if mode == "A":
                    results[f"{round_name}_{mode}"] = run_mode_a(round_name, plans, vot_values)
                else:
                    results[f"{round_name}_{mode}"] = run_mode_b(round_name, plans, vot_values)
                print(f"finished {round_name} mode {mode}", flush=True)
    except RestoredWorldLedgerRead as error:
        stopped_reason = str(error)
    finally:
        restore_wrappers()
        sys.setrecursionlimit(original_recursion_limit)
    pair_reports = []
    if stopped_reason is None and len(results) == 4:
        pair_reports.append(
            _compare_pair(results["round_1_A"], results["round_1_B"], "round_1 A vs B")
        )
        pair_reports.append(
            _compare_pair(results["round_2_B"], results["round_2_A"], "round_2 B vs A")
        )
        pair_reports.append(
            _compare_pair(results["round_1_A"], results["round_2_A"], "round_1 A vs round_2 A")
        )
        pair_reports.append(
            _compare_pair(results["round_1_B"], results["round_2_B"], "round_1 B vs round_2 B")
        )
        decision = _decide(results, pair_reports)
    else:
        reason = stopped_reason or "The diagnosis did not finish all four runs."
        decision = {
            "shared_baseline_candidate_snapshot_is_promising": False,
            "reasons_not_to_change_production": [reason],
        }
    _write_outputs(decision, pair_reports, results, stopped_reason)
    print(
        "shared_baseline_candidate_snapshot_is_promising:",
        decision["shared_baseline_candidate_snapshot_is_promising"],
    )
    print("output directory:", OUTPUT_DIR)
    if decision["shared_baseline_candidate_snapshot_is_promising"]:
        return 0
    return 1


# ---------------------------------------------------------------------------
# Static validation. No World and no simulation.
# ---------------------------------------------------------------------------

def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _assigned_literal(tree, name):
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise RuntimeError(f"Missing literal assignment {name}.")


def _calls_name(function_node, name):
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == name:
            return True
    return False


def _has_try_finally_calling(function_node, callee_name):
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Try) or not node.finalbody:
            continue
        for final_node in node.finalbody:
            if _calls_name(final_node, callee_name):
                return True
    return False


def static_validate():
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    if _assigned_literal(tree, "DIAGNOSTIC_ONLY") is not True:
        raise RuntimeError("DIAGNOSTIC_ONLY must be True.")
    if _assigned_literal(tree, "ALL_VEHICLES_PARTICIPATE") is not True:
        raise RuntimeError("ALL_VEHICLES_PARTICIPATE must be True.")
    if _assigned_literal(tree, "EVALUATION_END_TIMESTEP") != 299:
        raise RuntimeError("Evaluation end must be 299.")
    if _assigned_literal(tree, "EXPECTED_WORLD_T_AFTER_SIM") != 300:
        raise RuntimeError("Expected World.T after the run must be 300.")
    if _assigned_literal(tree, "BASELINE_HORIZON_STEPS") != 30:
        raise RuntimeError("Baseline horizon must be 30.")
    if _assigned_literal(tree, "MAX_CANDIDATE_VISIT_COUNT") != 10:
        raise RuntimeError("Candidate visit limit must be 10.")
    if _assigned_literal(tree, "NUM_VEHICLES") != 3000:
        raise RuntimeError("Vehicle count must be 3000.")
    if _assigned_literal(tree, "TRAFFIC_SEED") != 0:
        raise RuntimeError("Traffic seed must be 0.")
    if _assigned_literal(tree, "VOT_SEED") != 1:
        raise RuntimeError("VOT seed must be 1.")
    if _assigned_literal(tree, "DEMAND_GEN_SEED") != 42:
        raise RuntimeError("Demand generation seed must be 42.")
    if _assigned_literal(tree, "ROUND_ORDERS") != (
        ("round_1", ("A", "B")),
        ("round_2", ("B", "A")),
    ):
        raise RuntimeError("Round order must be A then B, then B then A.")
    required_functions = (
        "run_mode_a",
        "run_mode_b",
        "baseline_copy_mode_a",
        "baseline_copy_mode_b",
        "candidate_serialize_mode_a",
        "candidate_serialize_mode_b",
        "install_wrappers",
        "restore_wrappers",
        "build_world",
        "_compare_pair",
        "static_validate",
    )
    for name in required_functions:
        if _function_node(tree, name) is None:
            raise RuntimeError(f"Missing function {name}.")
    run_one = _function_node(tree, "_run_one")
    if not _has_try_finally_calling(run_one, "restore_wrappers"):
        raise RuntimeError("_run_one must restore wrappers in finally.")
    if not _calls_name(run_one, "build_world"):
        raise RuntimeError("_run_one must build a new World.")
    if not _calls_name(run_one, "install_wrappers"):
        raise RuntimeError("_run_one must install wrappers.")
    if _calls_name(_function_node(tree, "candidate_serialize_mode_b"), "ORIGINAL_SERIALIZE"):
        raise RuntimeError("Mode B must not call the production Candidate serialize.")
    if _calls_name(_function_node(tree, "candidate_serialize_mode_b"), "ORIGINAL_DILL_DUMPS"):
        raise RuntimeError("Mode B Candidate serialize must not dump.")
    if not _calls_name(_function_node(tree, "static_validate"), "read_text"):
        raise RuntimeError("static_validate must read this source file.")
    forbidden_modules = (
        "run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_shared_serialization_validation",
        "diagnose_tvt_mp_6x6_grid_3000_vehicle_performance_first_200_timesteps",
        "tvt_mp_candidate_shared_serialization_ab",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module_names = [node.module or ""]
        else:
            continue
        for module_name in module_names:
            for forbidden in forbidden_modules:
                if forbidden in module_name:
                    raise RuntimeError(f"This script must not import {module_name}.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "git":
                raise RuntimeError("This script must not call git.")
    static_function = _function_node(tree, "static_validate")
    if _calls_name(static_function, "exec_simulation"):
        raise RuntimeError("static_validate must not run exec_simulation.")
    if _calls_name(static_function, "run_diagnostic"):
        raise RuntimeError("static_validate must not run the diagnosis.")
    print("static validation passed")
    return 0


def main():
    if "--static-validate-only" in sys.argv:
        return static_validate()
    return run_diagnostic()


if __name__ == "__main__":
    sys.exit(main())
