# DIAGNOSTIC SCRIPT — NOT a regression test, research trial, or production change.
#
# A/B wall-clock comparison of Candidate local-world construction at one
# timestep (T=96) on the 3000-vehicle TVT-MP scenario.
#
# A: production build_tvt_mp_candidate_local_state (one World.copy per FIFO
#    True candidate; copy is pickle.loads(pickle.dumps(real_W))).
# B: dill dumps of real_W once, then pickle.loads per candidate.
#
# The real World is advanced only through T=95. TVT-MP stages run once up to
# the saved FIFO inspection set. Baseline, economics, atomic apply, and the
# real World's physical update are outside the measured A/B section.
# A function profiler is not used.
#
# Run from the repository root:
#   python diagnostics/order_control/tvt_mp_candidate_shared_serialization_ab.py --static-validate-only
#   python diagnostics/order_control/tvt_mp_candidate_shared_serialization_ab.py

from __future__ import annotations

import ast
import gc
import json
import math
import random
import sys
import time
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType

import dill as pickle
import numpy as np

from uxsim import World
from uxsim.order_control_tvt_baseline_fork_alignment import (
    run_snapshot_fixed_baseline_fork_and_align_undetermined_visits,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    build_tvt_candidate_visit_set,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    build_tvt_inlink_candidate_physical_orders,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    confirm_leading_nonparticipating_decision_window_visits,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    OrderControlTvtMpCandidateLocalState,
    _collect_local_vehicles,
    _copied_target_node,
    _incoming_local_vehicles,
    _link_states_in_registration_order,
    _pair_binding_visits_with_local_vehicles,
    _real_and_local_vehicle_name_maps,
    _require_binding_rank_sequence,
    _require_link_map,
    _require_real_world,
    _require_timestep_matches_baseline,
    _verify_local_reference_stays_in_copy,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    initialize_tvt_mp_candidate_local_virtual_calculation_state,
    run_tvt_mp_candidate_local_virtual_calculation,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    build_tvt_mp_concrete_buyer_candidate_sets,
)
from uxsim.order_control_tvt_mp_driver import (
    _build_participation_mapping,
    _collect_target_node_names,
    _ensure_target_rank_states,
    _reject_same_timestep_restart,
    _reject_timestep_moved_backward,
    _require_common_settings,
    _require_started_timestep_type,
    _require_timestep,
    _require_world,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    build_tvt_mp_fifo_inspection_results,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    build_tvt_mp_general_trade_ranks,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    build_tvt_mp_local_binding_rank_sequence,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    _candidate_is_fifo_true,
    _downstream_boundary_node_result_for_evaluated_node,
    _fork_result_from_fifo_set,
    _rank_state_for_evaluated_node,
    evaluate_tvt_mp_candidate_local_virtual_calculations,
)
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    confirm_already_arrived_undetermined_visits,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    select_right_of_entry_decision_window_visits,
)
from uxsim.uxsim import World as _WorldForTypeCheck

# ---------------------------------------------------------------------------
# Constants (same demand and road as the T=96 profile diagnostic)
# ---------------------------------------------------------------------------

DIAGNOSTIC_NAME = (
    "tvt_mp_candidate_shared_serialization_ab_seed_0_vot_seed_1_t96"
)
OUTPUT_DIR_NAME = DIAGNOSTIC_NAME

NUM_VEHICLES = 3000
DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5

PROFILE_TIMESTEP = 96
UNPROFILED_END_TIMESTEP = 95
EVALUATION_END_TIMESTEP = 96
BASELINE_HORIZON_STEPS = 30
INTERNAL_TSIZE = 127
WORLD_T_AT_AB = 96

TRAFFIC_SEED = 0
DEMAND_GEN_SEED = 42
VOT_SEED = 1
VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1
WORLD_COPY_RECURSION_LIMIT = 50000

GRID_SIZE = 6
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
REACTION_TIME = 1
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2
SHOW_PROGRESS_DELTAT = 100
ALL_VEHICLES_PARTICIPATE = True
SPECIFIED_ROUTE_USED = False

ROUND_ORDER_FIRST = ("A", "B")
ROUND_ORDER_SECOND = ("B", "A")

DECISION_PROMISING = "promising_for_production_design_review"
DECISION_RESULT_DIFFERENCE = "rejected_due_to_result_difference"
DECISION_INDEPENDENCE = "rejected_due_to_independence_failure"
DECISION_NO_SPEEDUP = "rejected_due_to_no_speedup"
DECISION_INCONCLUSIVE = "inconclusive"

_LIVE_CLASS_NAMES = frozenset({"World", "Node", "Link", "Vehicle"})

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "research_outputs" / "diagnostic" / OUTPUT_DIR_NAME
SCRIPT_PATH = Path(__file__).resolve()


@dataclass
class VehicleVotRecord:
    vehicle_name: str
    origin: str
    destination: str
    departure_time: float
    true_vot_per_second: float
    declared_vot_per_second: float


@dataclass
class PreparedCandidateInputs:
    """Frozen inputs for both A and B. Built once. Not a second driver run."""

    fifo_inspection_set_result: object
    rank_states_by_node_name: dict
    fifo_true_candidate_count: int
    target_node_names: tuple


# ---------------------------------------------------------------------------
# Network and demand (explicit; not imported from another diagnostic)
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


def _build_link_specs() -> tuple:
    internal = []
    connectors = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            internal.append((f"h_{row}_{column}_{column + 1}", left_node, right_node, INTERNAL_LINK_LENGTH, 0))
            internal.append((f"h_{row}_{column + 1}_{column}", right_node, left_node, INTERNAL_LINK_LENGTH, 0))
    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            internal.append((f"v_{row}_{row + 1}_{column}", upper_node, lower_node, INTERNAL_LINK_LENGTH, 1))
            internal.append((f"v_{row + 1}_{row}_{column}", lower_node, upper_node, INTERNAL_LINK_LENGTH, 1))
    for column in range(GRID_SIZE):
        north_grid = _grid_node_name(0, column)
        south_grid = _grid_node_name(GRID_SIZE - 1, column)
        connectors.append((f"top_{column}_to_g_0_{column}", f"top_{column}", north_grid, OD_CONNECTOR_LENGTH, 1))
        connectors.append((f"g_0_{column}_to_top_{column}", north_grid, f"top_{column}", OD_CONNECTOR_LENGTH, 1))
        connectors.append((f"bottom_{column}_to_g_5_{column}", f"bottom_{column}", south_grid, OD_CONNECTOR_LENGTH, 1))
        connectors.append((f"g_5_{column}_to_bottom_{column}", south_grid, f"bottom_{column}", OD_CONNECTOR_LENGTH, 1))
    for row in range(GRID_SIZE):
        west_grid = _grid_node_name(row, 0)
        east_grid = _grid_node_name(row, GRID_SIZE - 1)
        connectors.append((f"left_{row}_to_g_{row}_0", f"left_{row}", west_grid, OD_CONNECTOR_LENGTH, 0))
        connectors.append((f"g_{row}_0_to_left_{row}", west_grid, f"left_{row}", OD_CONNECTOR_LENGTH, 0))
        connectors.append((f"right_{row}_to_g_{row}_5", f"right_{row}", east_grid, OD_CONNECTOR_LENGTH, 0))
        connectors.append((f"g_{row}_5_to_right_{row}", east_grid, f"right_{row}", OD_CONNECTOR_LENGTH, 0))
    return tuple(internal), tuple(connectors)


INTERNAL_GRID_NODES = _internal_grid_node_names()
EXTERNAL_OD_NODES = _external_od_node_names()
OD_TO_GRID_COORD = _od_to_grid_coord_map()
INTERNAL_LINK_SPECS, OD_CONNECTOR_LINK_SPECS = _build_link_specs()
ALL_LINK_SPECS = INTERNAL_LINK_SPECS + OD_CONNECTOR_LINK_SPECS


def generate_vehicle_plans() -> list[dict]:
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
        manhattan = abs(origin_coord[0] - destination_coord[0]) + abs(
            origin_coord[1] - destination_coord[1]
        )
        if manhattan < MIN_OD_MANHATTAN_DISTANCE:
            continue
        departure_time = DEPARTURE_START + (
            (DEPARTURE_END - DEPARTURE_START) * len(plans) / max(NUM_VEHICLES - 1, 1)
        )
        plans.append(
            {
                "name": f"veh_{vehicle_index}",
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time,
            }
        )
        vehicle_index += 1
    return plans


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


def build_world() -> World:
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


def verify_network(world: World) -> None:
    tvt_names = [
        node.name for node in world.NODES if node.order_control_type == "time_value"
    ]
    if sorted(tvt_names) != sorted(INTERNAL_GRID_NODES):
        raise RuntimeError("TVT-MP targets are not the 36 internal nodes.")
    for node_name in EXTERNAL_OD_NODES:
        node = world.get_node(node_name)
        if node.order_control_type == "time_value":
            raise RuntimeError(f"External node {node_name} is a TVT-MP target.")
        if node.order_control_eligible is not False:
            raise RuntimeError(
                f"External OD node {node_name} is order-control eligible."
            )
    for link_name, _s, _e, _length, _sg in ALL_LINK_SPECS:
        link = world.get_link(link_name)
        if link.length != 200:
            raise RuntimeError(f"{link_name} length is not 200.")
        if not math.isclose(link.free_flow_speed, FREE_FLOW_SPEED, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"{link_name} free-flow speed mismatch.")
        if not math.isclose(link.jam_density, JAM_DENSITY, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"{link_name} jam density mismatch.")


# ---------------------------------------------------------------------------
# Prepare one T=96 input (driver stages through FIFO inspection only)
# ---------------------------------------------------------------------------

def prepare_candidate_inputs(real_W: World) -> PreparedCandidateInputs:
    """Same public stage order as run_tvt_mp_driver, stopping before local calc."""
    _require_world(real_W)
    _require_timestep(real_W.T)
    if real_W.T != WORLD_T_AT_AB:
        raise RuntimeError(f"Prepared World.T must be {WORLD_T_AT_AB}, got {real_W.T!r}.")
    target_node_names = tuple(_collect_target_node_names(real_W))
    _require_started_timestep_type(real_W.order_control_tvt_driver_started_timestep)
    _reject_same_timestep_restart(real_W)
    _reject_timestep_moved_backward(real_W)
    _require_common_settings(real_W)
    real_W.order_control_tvt_driver_started_timestep = real_W.T
    rank_states = real_W.order_control_tvt_rank_states_by_node_name
    _ensure_target_rank_states(rank_states, target_node_names)

    alignment_result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=real_W.order_control_tvt_baseline_horizon_steps,
        rank_states_by_node_name=rank_states,
    )
    arrived = confirm_already_arrived_undetermined_visits(
        alignment_result,
        rank_states_by_node_name=rank_states,
        real_W=real_W,
    )
    participation = _build_participation_mapping(real_W, arrived)
    leading = confirm_leading_nonparticipating_decision_window_visits(
        arrived,
        rank_states_by_node_name=rank_states,
        participates_by_visit_key=participation,
        real_W=real_W,
    )
    right_of_entry = select_right_of_entry_decision_window_visits(
        leading,
        rank_states_by_node_name=rank_states,
        participates_by_visit_key=participation,
    )
    candidate_visits = build_tvt_candidate_visit_set(
        right_of_entry,
        rank_states_by_node_name=rank_states,
        max_tvt_candidate_visit_count=real_W.order_control_tvt_max_candidate_visit_count,
    )
    physical = build_tvt_inlink_candidate_physical_orders(candidate_visits)
    concrete = build_tvt_mp_concrete_buyer_candidate_sets(
        physical,
        participates_by_visit_key=participation,
    )
    general = build_tvt_mp_general_trade_ranks(
        concrete,
        participates_by_visit_key=participation,
    )
    fifo_set = build_tvt_mp_fifo_inspection_results(general)
    fifo_true_count = _count_fifo_true_candidates(fifo_set)
    return PreparedCandidateInputs(
        fifo_inspection_set_result=fifo_set,
        rank_states_by_node_name=rank_states,
        fifo_true_candidate_count=fifo_true_count,
        target_node_names=target_node_names,
    )


def _count_fifo_true_candidates(fifo_set) -> int:
    count = 0
    for fifo_node_result in fifo_set.node_fifo_inspection_results:
        for candidate_result in fifo_node_result.candidate_fifo_inspection_results:
            if _candidate_is_fifo_true(candidate_result):
                count += 1
    return count


# ---------------------------------------------------------------------------
# Condition A: production local-virtual-calculation entry
# ---------------------------------------------------------------------------

def run_condition_a(real_W: World, prepared: PreparedCandidateInputs) -> dict:
    gc.collect()
    started = time.perf_counter()
    result = evaluate_tvt_mp_candidate_local_virtual_calculations(
        real_W,
        prepared.fifo_inspection_set_result,
        rank_states_by_node_name=prepared.rank_states_by_node_name,
    )
    elapsed = time.perf_counter() - started
    fifo_true_count = prepared.fifo_true_candidate_count
    return {
        "label": "A",
        "total_seconds": elapsed,
        "seconds_per_fifo_true_candidate": (
            elapsed / fifo_true_count if fifo_true_count else None
        ),
        "fifo_true_candidate_count": fifo_true_count,
        "expected_world_copy_calls": fifo_true_count,
        "expected_dumps_calls": fifo_true_count,
        "expected_loads_calls": fifo_true_count,
        "result": result,
        "fingerprint": _fingerprint_local_calculation_set(result),
    }


# ---------------------------------------------------------------------------
# Condition B: one dumps, then loads per FIFO True candidate
# ---------------------------------------------------------------------------

def build_candidate_local_state_from_loaded_world(
    real_W: World,
    binding_rank_sequence,
    local_world: World,
) -> OrderControlTvtMpCandidateLocalState:
    """Same post-copy checks as build_tvt_mp_candidate_local_state.

    Caller supplies a World already restored by pickle.loads. This function
    does not call World.copy and does not dumps again.
    """
    real_world = _require_real_world(real_W)
    sequence = _require_binding_rank_sequence(binding_rank_sequence)
    real_world_timestep_T = _require_timestep_matches_baseline(real_world, sequence)
    if not isinstance(sequence.node_name, str) or sequence.node_name == "":
        raise ValueError(
            "binding_rank_sequence.node_name must be a non-empty str; "
            f"got {sequence.node_name!r}."
        )
    if local_world is real_world:
        raise RuntimeError("Restored World is the real World object.")
    if not isinstance(local_world, _WorldForTypeCheck):
        raise RuntimeError(
            "Restored World must be a World; got "
            f"type {type(local_world).__name__}."
        )
    target_node_name = sequence.node_name
    target_node = _copied_target_node(local_world, target_node_name)
    inlink_map = _require_link_map(
        target_node.inlinks,
        node_name=target_node_name,
        field_name="inlinks",
    )
    outlink_map = _require_link_map(
        target_node.outlinks,
        node_name=target_node_name,
        field_name="outlinks",
    )
    inlink_states = _link_states_in_registration_order(
        inlink_map,
        node_name=target_node_name,
    )
    outlink_states = _link_states_in_registration_order(
        outlink_map,
        node_name=target_node_name,
    )
    incoming_vehicles = _incoming_local_vehicles(
        target_node,
        node_name=target_node_name,
    )
    local_vehicles = _collect_local_vehicles(
        inlink_states,
        outlink_states,
        incoming_vehicles,
    )
    _verify_local_reference_stays_in_copy(
        node_name=target_node_name,
        real_W=real_world,
        local_world=local_world,
        target_node=target_node,
        inlink_states=inlink_states,
        outlink_states=outlink_states,
        incoming_local_vehicles=incoming_vehicles,
        local_vehicles=local_vehicles,
    )
    binding_pairs = _pair_binding_visits_with_local_vehicles(
        node_name=target_node_name,
        local_world=local_world,
        target_node=target_node,
        binding_visits=sequence.visits_in_binding_order,
        local_vehicles=local_vehicles,
    )
    (
        local_vehicle_by_real_vehicle_name,
        real_vehicle_name_by_local_vehicle_name,
        real_vehicle_id_by_real_vehicle_name,
    ) = _real_and_local_vehicle_name_maps(
        node_name=target_node_name,
        real_W=real_world,
        local_vehicles=local_vehicles,
    )
    inlinks = tuple(link_state.link for link_state in inlink_states)
    outlinks = tuple(link_state.link for link_state in outlink_states)
    return OrderControlTvtMpCandidateLocalState(
        binding_rank_sequence=sequence,
        real_world_timestep_T=real_world_timestep_T,
        local_world=local_world,
        target_node_name=target_node_name,
        target_node=target_node,
        inlinks=inlinks,
        outlinks=outlinks,
        local_vehicles=local_vehicles,
        inlink_local_vehicle_states=inlink_states,
        outlink_local_vehicle_states=outlink_states,
        incoming_local_vehicles=incoming_vehicles,
        binding_visit_local_vehicle_pairs=binding_pairs,
        local_vehicle_by_real_vehicle_name=MappingProxyType(
            local_vehicle_by_real_vehicle_name
        ),
        real_vehicle_name_by_local_vehicle_name=MappingProxyType(
            real_vehicle_name_by_local_vehicle_name
        ),
        _real_vehicle_id_by_real_vehicle_name=MappingProxyType(
            real_vehicle_id_by_real_vehicle_name
        ),
    )


def _evaluate_one_fifo_true_candidate_shared_bytes(
    *,
    real_world: World,
    fifo_set,
    candidate_fifo_inspection_result,
    rank_state,
    fork_result,
    downstream_boundary_node_result,
    serialized_real_world: bytes,
    loads_seconds_box: list,
    local_worlds: list,
) -> object:
    binding_rank_sequence = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate_fifo_inspection_result,
        rank_state,
    )
    load_started = time.perf_counter()
    local_world = pickle.loads(serialized_real_world)
    loads_seconds_box[0] += time.perf_counter() - load_started
    candidate_local_state = build_candidate_local_state_from_loaded_world(
        real_world,
        binding_rank_sequence,
        local_world,
    )
    local_worlds.append(candidate_local_state.local_world)
    calculation_state = initialize_tvt_mp_candidate_local_virtual_calculation_state(
        candidate_local_state,
        fork_result.collector,
        downstream_boundary_node_result,
        fork_result.configured_horizon_steps,
    )
    return run_tvt_mp_candidate_local_virtual_calculation(calculation_state)


def run_condition_b(real_W: World, prepared: PreparedCandidateInputs) -> dict:
    """One dumps, then an independent loads plus local calculation per candidate.

    loads time is inside candidate-evaluation seconds. dumps is also reported
    alone. B total is dumps plus candidate evaluation.
    """
    from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
        OrderControlTvtMpLocalVirtualCalculationSetResult,
        OrderControlTvtNodeMpLocalVirtualCalculationResult,
        _build_status_is_complete,
        _build_status_is_normal_not_generated,
        _empty_node_result,
        _node_has_fifo_true_candidate,
    )

    fifo_set = prepared.fifo_inspection_set_result
    fork_result = _fork_result_from_fifo_set(fifo_set)
    gc.collect()
    dump_started = time.perf_counter()
    serialized_real_world = pickle.dumps(real_W)
    dumps_seconds = time.perf_counter() - dump_started
    if not isinstance(serialized_real_world, bytes):
        raise RuntimeError("pickle.dumps(real_W) did not return bytes.")
    serialized_snapshot = serialized_real_world

    gc.collect()
    eval_started = time.perf_counter()
    loads_seconds_box = [0.0]
    local_worlds: list = []
    node_results = []
    fifo_node_results = fifo_set.node_fifo_inspection_results
    for node_index, fifo_node_result in enumerate(fifo_node_results):
        build_status = fifo_node_result.build_status
        if _build_status_is_normal_not_generated(build_status):
            node_results.append(_empty_node_result(fifo_node_result))
            continue
        if not _build_status_is_complete(build_status):
            raise RuntimeError(
                f"Node {fifo_node_result.node_name!r}: unexpected build status "
                f"{build_status!r}."
            )
        if not _node_has_fifo_true_candidate(fifo_node_result):
            node_results.append(_empty_node_result(fifo_node_result))
            continue
        rank_state = _rank_state_for_evaluated_node(
            node_name=fifo_node_result.node_name,
            rank_states_by_node_name=prepared.rank_states_by_node_name,
        )
        boundary = _downstream_boundary_node_result_for_evaluated_node(
            node_name=fifo_node_result.node_name,
            node_index=node_index,
            fork_result=fork_result,
        )
        candidate_results = []
        for candidate_fifo in fifo_node_result.candidate_fifo_inspection_results:
            if not _candidate_is_fifo_true(candidate_fifo):
                continue
            candidate_results.append(
                _evaluate_one_fifo_true_candidate_shared_bytes(
                    real_world=real_W,
                    fifo_set=fifo_set,
                    candidate_fifo_inspection_result=candidate_fifo,
                    rank_state=rank_state,
                    fork_result=fork_result,
                    downstream_boundary_node_result=boundary,
                    serialized_real_world=serialized_real_world,
                    loads_seconds_box=loads_seconds_box,
                    local_worlds=local_worlds,
                )
            )
        node_results.append(
            OrderControlTvtNodeMpLocalVirtualCalculationResult(
                node_name=fifo_node_result.node_name,
                build_status=fifo_node_result.build_status,
                candidate_local_virtual_calculation_results=tuple(candidate_results),
            )
        )
    result = OrderControlTvtMpLocalVirtualCalculationSetResult(
        fifo_inspection_set_result=fifo_set,
        node_local_virtual_calculation_results=tuple(node_results),
    )
    eval_seconds = time.perf_counter() - eval_started
    total_seconds = dumps_seconds + eval_seconds
    fifo_true_count = prepared.fifo_true_candidate_count
    if len(local_worlds) != fifo_true_count:
        raise RuntimeError(
            f"B restored {len(local_worlds)} worlds, expected {fifo_true_count}."
        )
    if serialized_real_world != serialized_snapshot:
        raise RuntimeError("Shared serialized bytes changed during B.")
    independence = _check_local_world_independence(real_W, local_worlds)
    return {
        "label": "B",
        "dumps_seconds": dumps_seconds,
        "loads_seconds": loads_seconds_box[0],
        "candidate_evaluation_seconds": eval_seconds,
        "total_seconds": total_seconds,
        "seconds_per_fifo_true_candidate": (
            total_seconds / fifo_true_count if fifo_true_count else None
        ),
        "fifo_true_candidate_count": fifo_true_count,
        "expected_dumps_calls": 1,
        "expected_loads_calls": fifo_true_count,
        "shared_bytes_unchanged": serialized_real_world == serialized_snapshot,
        "shared_bytes_length": len(serialized_real_world),
        "independence": independence,
        "result": result,
        "fingerprint": _fingerprint_local_calculation_set(result),
    }


def _check_local_world_independence(real_W: World, local_worlds: list) -> dict:
    """Identity and leak checks. Does not change real_W."""
    report = {
        "local_world_count": len(local_worlds),
        "all_distinct_from_real": True,
        "pairwise_worlds_distinct": True,
        "pairwise_nodes_distinct": True,
        "pairwise_links_distinct": True,
        "pairwise_vehicles_distinct": True,
        "registries_distinct": True,
        "mutation_does_not_leak": True,
        "checked_pair": False,
    }
    for local_world in local_worlds:
        if local_world is real_W:
            report["all_distinct_from_real"] = False
        if local_world.VEHICLES is real_W.VEHICLES:
            report["registries_distinct"] = False
    if len(local_worlds) < 2:
        return report
    report["checked_pair"] = True
    first = local_worlds[0]
    second = local_worlds[1]
    if first is second:
        report["pairwise_worlds_distinct"] = False
    if first.VEHICLES is second.VEHICLES:
        report["registries_distinct"] = False
    first_node = first.NODES[0]
    second_node = second.get_node(first_node.name)
    real_node = real_W.get_node(first_node.name)
    if first_node is second_node or first_node is real_node:
        report["pairwise_nodes_distinct"] = False
    first_link = first.LINKS[0]
    second_link = second.get_link(first_link.name)
    real_link = real_W.get_link(first_link.name)
    if first_link is second_link or first_link is real_link:
        report["pairwise_links_distinct"] = False
    vehicle_name = sorted(first.VEHICLES)[0]
    first_vehicle = first.VEHICLES[vehicle_name]
    second_vehicle = second.VEHICLES[vehicle_name]
    real_vehicle = real_W.VEHICLES[vehicle_name]
    if (
        first_vehicle is second_vehicle
        or first_vehicle is real_vehicle
    ):
        report["pairwise_vehicles_distinct"] = False
    saved_second_x = second_vehicle.x
    saved_real_x = real_vehicle.x
    first_vehicle.x = float(saved_second_x) + 100000.0
    if second_vehicle.x != saved_second_x:
        report["mutation_does_not_leak"] = False
    if real_vehicle.x != saved_real_x:
        report["mutation_does_not_leak"] = False
    if real_W.VEHICLES[vehicle_name] is not real_vehicle:
        report["mutation_does_not_leak"] = False
    return report


def _independence_ok(report: dict) -> bool:
    if report["all_distinct_from_real"] is not True:
        return False
    if report["registries_distinct"] is not True:
        return False
    if report["local_world_count"] < 2:
        return False
    return (
        report["pairwise_worlds_distinct"]
        and report["pairwise_nodes_distinct"]
        and report["pairwise_links_distinct"]
        and report["pairwise_vehicles_distinct"]
        and report["mutation_does_not_leak"]
    )


# ---------------------------------------------------------------------------
# Fingerprints (no asdict of live Worlds)
# ---------------------------------------------------------------------------

def _fingerprint_value(value, seen: set):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Enum):
        return {"enum": type(value).__name__, "value": value.value}
    if isinstance(value, tuple):
        return [_fingerprint_value(item, seen) for item in value]
    if isinstance(value, list):
        return [_fingerprint_value(item, seen) for item in value]
    class_name = type(value).__name__
    if class_name in _LIVE_CLASS_NAMES:
        return {"live_object_omitted": class_name, "name": getattr(value, "name", None)}
    if is_dataclass(value):
        object_id = id(value)
        if object_id in seen:
            return {"cycle": class_name}
        seen.add(object_id)
        payload = {"dataclass": class_name}
        for field in fields(value):
            payload[field.name] = _fingerprint_value(getattr(value, field.name), seen)
        return payload
    if isinstance(value, dict):
        payload = {}
        for key in sorted(value, key=repr):
            payload[repr(key)] = _fingerprint_value(value[key], seen)
        return payload
    return {"opaque": class_name, "repr": repr(value)}


def _fingerprint_local_calculation_set(result) -> list:
    rows = []
    for node_result in result.node_local_virtual_calculation_results:
        candidate_rows = []
        for candidate_result in node_result.candidate_local_virtual_calculation_results:
            candidate_rows.append(_fingerprint_value(candidate_result, set()))
        rows.append(
            {
                "node_name": node_result.node_name,
                "build_status": _fingerprint_value(node_result.build_status, set()),
                "candidate_count": len(candidate_rows),
                "candidates": candidate_rows,
            }
        )
    return rows


def _first_difference(left, right, path=""):
    if type(left) is not type(right):
        return f"{path}: type {type(left).__name__} != {type(right).__name__}"
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path}: length {len(left)} != {len(right)}"
        for index, (item_left, item_right) in enumerate(zip(left, right)):
            found = _first_difference(item_left, item_right, f"{path}[{index}]")
            if found is not None:
                return found
        return None
    if isinstance(left, dict):
        if set(left) != set(right):
            return f"{path}: keys differ"
        for key in left:
            found = _first_difference(left[key], right[key], f"{path}.{key}")
            if found is not None:
                return found
        return None
    if left != right:
        return f"{path}: {left!r} != {right!r}"
    return None


def _real_world_fingerprint(real_W: World) -> dict:
    vehicles = []
    for name in sorted(real_W.VEHICLES):
        vehicle = real_W.VEHICLES[name]
        link = getattr(vehicle, "link", None)
        link_name = None if link is None else getattr(link, "name", None)
        vehicles.append(
            (
                name,
                vehicle.state,
                vehicle.x,
                vehicle.v,
                link_name,
            )
        )
    links = []
    for link in sorted(real_W.LINKS, key=lambda item: item.name):
        links.append(
            (
                link.name,
                tuple(vehicle.name for vehicle in link.vehicles),
                link.capacity_in_remain,
                link.capacity_out_remain,
            )
        )
    nodes = []
    for node in sorted(real_W.NODES, key=lambda item: item.name):
        nodes.append(
            (
                node.name,
                tuple(vehicle.name for vehicle in node.incoming_vehicles),
            )
        )
    return {
        "T": real_W.T,
        "TIME": real_W.TIME,
        "vehicles": vehicles,
        "links": links,
        "nodes": nodes,
    }


def _rng_token(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


# ---------------------------------------------------------------------------
# Rounds, decision, output
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    mid = count // 2
    if count % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _run_one_round(real_W, prepared, order: tuple[str, str], fingerprint_before, rng_before) -> dict:
    results = {}
    for label in order:
        if _real_world_fingerprint(real_W) != fingerprint_before:
            raise RuntimeError(f"real_W changed before condition {label}.")
        if _rng_token(real_W.rng) != rng_before["traffic"]:
            raise RuntimeError(f"traffic RNG changed before condition {label}.")
        if _rng_token(real_W.order_control_rng) != rng_before["order_control"]:
            raise RuntimeError(f"order-control RNG changed before condition {label}.")
        if label == "A":
            results["A"] = run_condition_a(real_W, prepared)
        elif label == "B":
            results["B"] = run_condition_b(real_W, prepared)
        else:
            raise RuntimeError(f"Unknown condition label {label!r}.")
        if _real_world_fingerprint(real_W) != fingerprint_before:
            raise RuntimeError(f"real_W changed during condition {label}.")
        if _rng_token(real_W.rng) != rng_before["traffic"]:
            raise RuntimeError(f"traffic RNG changed during condition {label}.")
        if _rng_token(real_W.order_control_rng) != rng_before["order_control"]:
            raise RuntimeError(f"order-control RNG changed during condition {label}.")
    difference = _first_difference(results["A"]["fingerprint"], results["B"]["fingerprint"])
    a_total = results["A"]["total_seconds"]
    b_total = results["B"]["total_seconds"]
    return {
        "order": list(order),
        "A_total_seconds": a_total,
        "B_total_seconds": b_total,
        "A_seconds_per_fifo_true_candidate": results["A"]["seconds_per_fifo_true_candidate"],
        "B_seconds_per_fifo_true_candidate": results["B"]["seconds_per_fifo_true_candidate"],
        "B_dumps_seconds": results["B"]["dumps_seconds"],
        "B_loads_seconds": results["B"]["loads_seconds"],
        "B_candidate_evaluation_seconds": results["B"]["candidate_evaluation_seconds"],
        "speedup_ratio_a_over_b": (a_total / b_total) if b_total else None,
        "seconds_saved": a_total - b_total,
        "results_equal": difference is None,
        "first_difference": difference,
        "independence": results["B"]["independence"],
        "independence_ok": _independence_ok(results["B"]["independence"]),
        "shared_bytes_unchanged": results["B"]["shared_bytes_unchanged"],
        "expected_A_dumps_calls": results["A"]["expected_dumps_calls"],
        "expected_A_loads_calls": results["A"]["expected_loads_calls"],
        "expected_B_dumps_calls": results["B"]["expected_dumps_calls"],
        "expected_B_loads_calls": results["B"]["expected_loads_calls"],
        "real_world_unchanged": True,
        "traffic_rng_unchanged": True,
        "order_control_rng_unchanged": True,
    }


def _decide(rounds: list[dict], fifo_true_count: int, exception_text: str | None) -> tuple[str, bool]:
    if exception_text is not None:
        return DECISION_INCONCLUSIVE, False
    if fifo_true_count < 1:
        return DECISION_INCONCLUSIVE, False
    if any(item["results_equal"] is not True for item in rounds):
        return DECISION_RESULT_DIFFERENCE, False
    if any(item["independence_ok"] is not True for item in rounds):
        return DECISION_INDEPENDENCE, False
    if any(item["shared_bytes_unchanged"] is not True for item in rounds):
        return DECISION_INDEPENDENCE, False
    if any(item["real_world_unchanged"] is not True for item in rounds):
        return DECISION_INDEPENDENCE, False
    if any(item["B_total_seconds"] >= item["A_total_seconds"] for item in rounds):
        return DECISION_NO_SPEEDUP, False
    return DECISION_PROMISING, True


def _refuse_existing_output_directory() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {OUTPUT_DIR}. "
            "Rename or remove it manually before re-running."
        )


def _public_round(round_result: dict) -> dict:
    copied = dict(round_result)
    return copied


def _run_diagnostic() -> int:
    _refuse_existing_output_directory()
    original_limit = sys.getrecursionlimit()
    exception_text = None
    rounds = []
    fifo_true_count = 0
    try:
        if original_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)

        plans = generate_vehicle_plans()
        if plans[0]["departure_time"] != 0 or plans[-1]["departure_time"] != 999:
            raise RuntimeError("Vehicle plan departure window is not 0..999.")
        if len(plans) != NUM_VEHICLES:
            raise RuntimeError("Vehicle plan count is not 3000.")
        vot_values = generate_vehicle_vots(len(plans))
        world = build_world()
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
        verify_network(world)
        world.finalize_scenario()
        if world.TSIZE != INTERNAL_TSIZE:
            raise RuntimeError(f"TSIZE is {world.TSIZE!r}, expected {INTERNAL_TSIZE}.")
        world.exec_simulation(until_t=UNPROFILED_END_TIMESTEP * world.DELTAT)
        if world.T != WORLD_T_AT_AB:
            raise RuntimeError(f"After prefix, World.T is {world.T!r}, expected {WORLD_T_AT_AB}.")

        prepared = prepare_candidate_inputs(world)
        fifo_true_count = prepared.fifo_true_candidate_count
        fingerprint_before = _real_world_fingerprint(world)
        rng_before = {
            "traffic": _rng_token(world.rng),
            "order_control": _rng_token(world.order_control_rng),
        }
        for order in (ROUND_ORDER_FIRST, ROUND_ORDER_SECOND):
            rounds.append(
                _run_one_round(world, prepared, order, fingerprint_before, rng_before)
            )
    except Exception as exc:
        exception_text = repr(exc)
    finally:
        sys.setrecursionlimit(original_limit)

    if rounds:
        a_totals = [item["A_total_seconds"] for item in rounds]
        b_totals = [item["B_total_seconds"] for item in rounds]
        a_mean = _mean(a_totals)
        b_mean = _mean(b_totals)
        a_median = _median(a_totals)
        b_median = _median(b_totals)
        mean_speedup = a_mean / b_mean if b_mean else None
    else:
        a_mean = None
        b_mean = None
        a_median = None
        b_median = None
        mean_speedup = None
    decision, promising = _decide(rounds, fifo_true_count, exception_text)
    summary = {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "production_unchanged": True,
        "profiling_run": False,
        "formal_performance_comparison": False,
        "research_evaluation_trial": False,
        "profile_timestep": PROFILE_TIMESTEP,
        "vehicle_count": NUM_VEHICLES,
        "fifo_true_candidate_count": fifo_true_count,
        "condition_A": "production World.copy per FIFO True candidate",
        "condition_B": "one dill dumps of real_W, then loads per candidate",
        "rounds": [_public_round(item) for item in rounds],
        "A_total_seconds_mean": a_mean,
        "A_total_seconds_median": a_median,
        "B_total_seconds_mean": b_mean,
        "B_total_seconds_median": b_median,
        "mean_speedup_ratio_a_over_b": mean_speedup,
        "decision": decision,
        "shared_serialization_candidate_is_promising": promising,
        "exception": exception_text,
        "output_directory": str(OUTPUT_DIR),
    }
    _refuse_existing_output_directory()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    report_lines = [
        "TVT-MP Candidate shared-serialization A/B diagnostic",
        "Purpose: check whether one dumps plus per-candidate loads matches production copies.",
        "Production code was not modified.",
        "This is not a research evaluation trial and not a function profiler run.",
        f"timestep: T={PROFILE_TIMESTEP}",
        f"fifo_true_candidate_count: {fifo_true_count}",
        "A: each FIFO True candidate calls production build via evaluate_tvt_mp_candidate_local_virtual_calculations (World.copy).",
        "B: pickle.dumps(real_W) once, then pickle.loads per candidate, then the same local-state helpers.",
        f"round 1 order: {ROUND_ORDER_FIRST}",
        f"round 2 order: {ROUND_ORDER_SECOND}",
    ]
    for index, item in enumerate(rounds, start=1):
        report_lines.append(f"round {index}: {json.dumps(item, default=str)}")
    report_lines.extend(
        [
            f"A total mean seconds: {summary['A_total_seconds_mean']}",
            f"A total median seconds: {summary['A_total_seconds_median']}",
            f"B total mean seconds: {summary['B_total_seconds_mean']}",
            f"B total median seconds: {summary['B_total_seconds_median']}",
            f"mean speedup A/B: {summary['mean_speedup_ratio_a_over_b']}",
            f"decision: {decision}",
            f"shared_serialization_candidate_is_promising: {promising}",
            "Production was not changed by this diagnostic.",
        ]
    )
    (OUTPUT_DIR / "report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(decision)
    print(OUTPUT_DIR)
    if exception_text is not None:
        raise RuntimeError(exception_text)
    return 0


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


def _assert_no_profiler_import(tree: ast.Module) -> None:
    forbidden = "c" + "Profile"
    for node in tree.body:
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        for module in modules:
            if module == forbidden or module.endswith("." + forbidden):
                raise RuntimeError("This diagnostic must not import a function profiler.")


def _assert_no_forbidden_runtime_imports(tree: ast.Module) -> None:
    forbidden_parts = (
        "run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_short_benchmark",
        "tvt_mp_3000_vehicle_t96_single_timestep_profile",
        "tvt_global_baseline_profile",
    )
    for node in tree.body:
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        for module in modules:
            for part in forbidden_parts:
                if part in module:
                    raise RuntimeError(f"Must not import {part}.")


def _assert_no_production_monkey_patch() -> None:
    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    fragments = (
        "unittest" + "." + "mock",
        "monkey" + "patch",
        "setattr" + "(" + "uxsim",
    )
    for fragment in fragments:
        if fragment in source_text:
            raise RuntimeError(
                f"This script must not monkey-patch production ({fragment!r} found)."
            )


def _assert_addlink_has_no_capacity_keywords(tree: ast.Module) -> None:
    build_function = _function_node(tree, "build_world")
    if build_function is None:
        raise RuntimeError("build_world is missing.")
    for node in ast.walk(build_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "addLink":
            continue
        for keyword in node.keywords:
            if keyword.arg in ("capacity_in", "capacity_out"):
                raise RuntimeError(f"addLink must not pass {keyword.arg}.")


def _assert_build_world_order_control_setup_order(tree: ast.Module) -> None:
    build_function = _function_node(tree, "build_world")
    if build_function is None:
        raise RuntimeError("build_world is missing.")
    addlink_lineno = None
    infer_lineno = None
    set_order_lineno = None
    for node in ast.walk(build_function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        attr = node.func.attr
        if attr == "addLink":
            if addlink_lineno is None or node.lineno > addlink_lineno:
                addlink_lineno = node.lineno
        if attr == "infer_order_control_eligible_nodes":
            infer_lineno = node.lineno
        if attr == "set_order_control_for_nodes":
            set_order_lineno = node.lineno
    if addlink_lineno is None:
        raise RuntimeError("build_world must call addLink.")
    if infer_lineno is None:
        raise RuntimeError("build_world must call infer_order_control_eligible_nodes.")
    if set_order_lineno is None:
        raise RuntimeError("build_world must call set_order_control_for_nodes.")
    if not (addlink_lineno < infer_lineno < set_order_lineno):
        raise RuntimeError(
            "build_world order must be: all addLink, then "
            "infer_order_control_eligible_nodes, then set_order_control_for_nodes."
        )


def _assert_static_function_does_not_run(function_node: ast.AST) -> None:
    forbidden = {
        "exec_simulation",
        "mkdir",
        "World",
        "dumps",
        "loads",
        "generate_vehicle_plans",
        "_run_diagnostic",
        "run_condition_a",
        "run_condition_b",
    }
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name in forbidden:
            raise RuntimeError(f"Static validation must not call {name}.")


def validate_static_contract() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory must not exist: {OUTPUT_DIR}.")
    if NUM_VEHICLES != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 999:
        raise RuntimeError("Departure window must be 0..999.")
    if PROFILE_TIMESTEP != 96 or EVALUATION_END_TIMESTEP != 96:
        raise RuntimeError("Timestep must be 96.")
    if EVALUATION_END_TIMESTEP != PROFILE_TIMESTEP:
        raise RuntimeError("EVALUATION_END_TIMESTEP must equal PROFILE_TIMESTEP.")
    if BASELINE_HORIZON_STEPS != 30 or INTERNAL_TSIZE != 127:
        raise RuntimeError("Horizon or TSIZE mismatch.")
    if INTERNAL_TSIZE != EVALUATION_END_TIMESTEP + BASELINE_HORIZON_STEPS + 1:
        raise RuntimeError("INTERNAL_TSIZE relation failed.")
    if MAX_CANDIDATE_VISIT_COUNT != 10 or CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("N or clearance mismatch.")
    if TRAFFIC_SEED != 0 or DEMAND_GEN_SEED != 42 or VOT_SEED != 1:
        raise RuntimeError("Seeds mismatch.")
    if WORLD_COPY_RECURSION_LIMIT != 50000:
        raise RuntimeError("Recursion limit must be 50000.")
    if INTERNAL_LINK_LENGTH != 200 or JAM_DENSITY != 0.2:
        raise RuntimeError("Road constants mismatch.")
    if not math.isclose(FREE_FLOW_SPEED, 60 / 3.6, rel_tol=0.0, abs_tol=1e-9):
        raise RuntimeError("Free-flow speed mismatch.")
    if ROUND_ORDER_FIRST != ("A", "B") or ROUND_ORDER_SECOND != ("B", "A"):
        raise RuntimeError("Round order must be A-then-B and B-then-A.")
    if ALL_VEHICLES_PARTICIPATE is not True or SPECIFIED_ROUTE_USED is not False:
        raise RuntimeError("Participation or route flag mismatch.")
    if OUTPUT_DIR_NAME != DIAGNOSTIC_NAME:
        raise RuntimeError("Output directory name mismatch.")

    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    assigned = _module_assigned_constants(tree)
    expected = {
        "NUM_VEHICLES": 3000,
        "DEPARTURE_END": 999,
        "PROFILE_TIMESTEP": 96,
        "EVALUATION_END_TIMESTEP": 96,
        "BASELINE_HORIZON_STEPS": 30,
        "INTERNAL_TSIZE": 127,
        "MAX_CANDIDATE_VISIT_COUNT": 10,
        "CLEARANCE_TIMESTEPS": 1,
        "WORLD_COPY_RECURSION_LIMIT": 50000,
    }
    for name, value in expected.items():
        if assigned.get(name) != value:
            raise RuntimeError(f"Module constant {name} must be {value}.")
    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    _assert_static_function_does_not_run(validator)
    _assert_no_profiler_import(tree)
    _assert_no_forbidden_runtime_imports(tree)
    _assert_no_production_monkey_patch()
    _assert_addlink_has_no_capacity_keywords(tree)
    _assert_build_world_order_control_setup_order(tree)


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
