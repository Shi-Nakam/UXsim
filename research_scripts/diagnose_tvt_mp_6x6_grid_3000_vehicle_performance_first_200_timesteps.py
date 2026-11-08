"""
Performance diagnosis for the first 200 real timesteps of the 3000-vehicle TVT-MP trial.

This script does not change production code. It temporarily replaces functions
the TVT-MP driver already calls, times those calls, and always restores the
original functions. It does not compute AWT or AWWT and it does not run the
18-hour full-completion trial.

Run from the repository root:

    python research_scripts/diagnose_tvt_mp_6x6_grid_3000_vehicle_performance_first_200_timesteps.py --static-validate-only
    python research_scripts/diagnose_tvt_mp_6x6_grid_3000_vehicle_performance_first_200_timesteps.py
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
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from uxsim import World
import uxsim.order_control_baseline_driver as baseline_driver_module
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.order_control_tvt_mp_local_virtual_calculation_set as candidate_set_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
)

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tvt_mp_full_run_audit_helper import (  # noqa: E402
    _clear_live_state,
    _restore_hooks,
    install_tvt_mp_full_run_audit,
)

# ---------------------------------------------------------------------------
# 1. Same scenario constants as the full-completion trial
# ---------------------------------------------------------------------------

DIAGNOSTIC_ONLY = True
DIAGNOSTIC_SCRIPT_NAME = (
    "diagnose_tvt_mp_6x6_grid_3000_vehicle_performance_first_200_timesteps.py"
)
FORMAL_TRIAL_MODULE_NAME = (
    "run_tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_trial"
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
TOTAL_NODE_COUNT = 60
TOTAL_LINK_COUNT = 168
LAST_TVT_DECISION_TIMESTEP_CAP = 5000
BASELINE_HORIZON_STEPS = 30
DECISION_WINDOW_STEPS = 6
MAX_CANDIDATE_VISIT_COUNT = 10
CLEARANCE_TIMESTEPS = 1
INTERNAL_TSIZE = LAST_TVT_DECISION_TIMESTEP_CAP + BASELINE_HORIZON_STEPS + 1
WORLD_COPY_RECURSION_LIMIT = 50000
NEAR_HORIZON_MINIMUM_TIMESTEPS = 28

DIAGNOSTIC_FIRST_TIMESTEP = 0
DIAGNOSTIC_LAST_TIMESTEP = 199
DIAGNOSTIC_TIMESTEP_COUNT = 200
TIMESTEP_BINS = (
    (0, 49),
    (50, 99),
    (100, 149),
    (150, 199),
)

MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
REACTION_TIME = 1
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2
SHOW_PROGRESS_DELTAT = 600

EXPECTED_VEHICLE_PLAN_SHA256 = (
    "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
)

OUTPUT_DIR_NAME = (
    "diagnose_tvt_mp_6x6_grid_3000_vehicle_performance_first_200_timesteps"
)
# Distinct from the formal trial name so Analyzer does not write into that
# trial's out directory. The name is not a traffic input.
DIAGNOSTIC_WORLD_NAME = OUTPUT_DIR_NAME

REPO_ROOT = SCRIPT_PATH.parents[1]
OUTPUT_DIR = REPO_ROOT / "research_outputs" / "trial" / OUTPUT_DIR_NAME

RESOLVED_STOP = OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
HORIZON_STOP = (
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
)

# Symbols patched on the module that actually looks them up at runtime.
# The driver calls the names imported into uxsim.order_control_tvt_mp_driver.
# Baseline internals are looked up inside uxsim.order_control_baseline_driver.
# Candidate serialize and load are looked up inside the local-calculation set
# module, which imported its own references.
GENERIC_DRIVER_STAGES = (
    ("arrived_confirmation", "confirm_already_arrived_undetermined_visits"),
    (
        "leading_nonparticipating_confirmation",
        "confirm_leading_nonparticipating_decision_window_visits",
    ),
    ("right_of_entry_selection", "select_right_of_entry_decision_window_visits"),
    ("candidate_visit_set", "build_tvt_candidate_visit_set"),
    ("inlink_physical_order", "build_tvt_inlink_candidate_physical_orders"),
    ("concrete_buyer_candidate_sets", "build_tvt_mp_concrete_buyer_candidate_sets"),
    ("general_trade_rank", "build_tvt_mp_general_trade_ranks"),
    ("fifo_inspection", "build_tvt_mp_fifo_inspection_results"),
    ("economic_evaluation", "evaluate_tvt_mp_candidate_economics"),
    ("candidate_selection", "select_tvt_mp_candidates"),
    ("payment_and_compensation", "calculate_tvt_mp_payments_and_compensations"),
    ("final_rank", "build_tvt_mp_final_ranks"),
    ("final_consistency_validation", "validate_tvt_mp_final_consistency"),
    ("atomic_apply", "apply_tvt_mp_validated_result"),
    ("participation_mapping", "_build_participation_mapping"),
)

STAGE_ORDER = (
    "baseline_fork_and_alignment",
    "arrived_confirmation",
    "participation_mapping",
    "leading_nonparticipating_confirmation",
    "right_of_entry_selection",
    "candidate_visit_set",
    "inlink_physical_order",
    "concrete_buyer_candidate_sets",
    "general_trade_rank",
    "fifo_inspection",
    "candidate_local_virtual_calculations",
    "economic_evaluation",
    "candidate_selection",
    "payment_and_compensation",
    "final_rank",
    "final_consistency_validation",
    "atomic_apply",
    "baseline_prepare",
    "baseline_complete",
    "baseline_forward",
    "world_copy",
    "candidate_serialize",
    "candidate_load",
)


# ---------------------------------------------------------------------------
# 2. Timing ledger. It lives in this script, not on the World.
# ---------------------------------------------------------------------------

@dataclass
class StageTotal:
    call_count: int = 0
    total_seconds: float = 0.0
    max_seconds: float = 0.0


@dataclass
class TimestepBin:
    label: str
    start_timestep: int
    end_timestep: int
    driver_call_count: int = 0
    driver_total_seconds: float = 0.0
    baseline_prepare_seconds: float = 0.0
    baseline_forward_seconds: float = 0.0
    candidate_serialize_seconds: float = 0.0
    candidate_load_seconds: float = 0.0
    candidate_local_seconds: float = 0.0
    registered_visit_zero_count: int = 0
    candidate_zero_count: int = 0
    serialized_bytes_total: int = 0
    serialize_call_count: int = 0
    serialized_bytes_maximum: int = 0


@dataclass
class TimingLedger:
    stages: dict[str, StageTotal] = field(default_factory=dict)
    timesteps: list[dict] = field(default_factory=list)
    bins: list[TimestepBin] = field(default_factory=list)
    current: dict | None = None
    driver_call_count: int = 0
    driver_total_seconds: float = 0.0
    driver_max_seconds: float = 0.0
    driver_min_seconds: float | None = None
    production_driver_total_seconds: float = 0.0
    audit_wrapper_call_count: int = 0
    audit_overhead_total_seconds: float = 0.0
    registered_visit_count_total: int = 0
    registered_visit_zero_count: int = 0
    registered_visit_positive_count: int = 0
    fork_steps_total: int = 0
    fork_steps_max: int = 0
    fork_full_horizon_count: int = 0
    serialized_bytes_total: int = 0
    serialized_bytes_maximum: int = 0
    candidate_execution_count: int = 0
    simulated_timestep_total: int = 0
    simulated_timestep_max: int = 0
    early_stop_candidate_count: int = 0
    near_horizon_candidate_count: int = 0
    other_stop_candidate_count: int = 0
    candidate_count_histogram: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for stage_name in STAGE_ORDER:
            self.stages[stage_name] = StageTotal()
        for start_timestep, end_timestep in TIMESTEP_BINS:
            self.bins.append(
                TimestepBin(
                    label=f"T={start_timestep}..{end_timestep}",
                    start_timestep=start_timestep,
                    end_timestep=end_timestep,
                )
            )

    @property
    def current_timestep(self) -> int | None:
        if self.current is None:
            return None
        return self.current["real_timestep"]

    def begin_timestep(self, timestep: int) -> None:
        if type(timestep) is not int:
            raise RuntimeError(
                "stage audit_driver_wrapper: real timestep "
                f"{timestep!r} is not a Python int."
            )
        if self.current is not None:
            raise RuntimeError(
                "stage audit_driver_wrapper at timestep "
                f"{timestep}: another driver timing record is still open "
                f"at timestep {self.current['real_timestep']}."
            )
        self.current = {
            "real_timestep": timestep,
            "baseline_stage_seconds": 0.0,
            "candidate_local_stage_seconds": 0.0,
            "prepare_seconds": 0.0,
            "forward_seconds": 0.0,
            "serialize_seconds": 0.0,
            "load_seconds": 0.0,
            "serialize_bytes": 0,
            "serialize_calls": 0,
            "candidate_count": None,
            "registered_visit_count": None,
            "fork_steps": None,
            "production_seconds": None,
        }

    def record_stage(self, stage_name: str, elapsed: float) -> None:
        stage = self.stages[stage_name]
        stage.call_count = stage.call_count + 1
        stage.total_seconds = stage.total_seconds + elapsed
        if elapsed > stage.max_seconds:
            stage.max_seconds = elapsed
        if self.current is None:
            return
        if stage_name == "baseline_prepare":
            self.current["prepare_seconds"] = self.current["prepare_seconds"] + elapsed
        elif stage_name == "baseline_fork_and_alignment":
            self.current["baseline_stage_seconds"] = (
                self.current["baseline_stage_seconds"] + elapsed
            )
        elif stage_name == "candidate_serialize":
            self.current["serialize_seconds"] = (
                self.current["serialize_seconds"] + elapsed
            )
        elif stage_name == "candidate_load":
            self.current["load_seconds"] = self.current["load_seconds"] + elapsed
        elif stage_name == "candidate_local_virtual_calculations":
            self.current["candidate_local_stage_seconds"] = (
                self.current["candidate_local_stage_seconds"] + elapsed
            )

    def add_baseline_forward_seconds(self, elapsed: float) -> None:
        stage = self.stages["baseline_forward"]
        stage.call_count = stage.call_count + 1
        stage.total_seconds = stage.total_seconds + elapsed
        if elapsed > stage.max_seconds:
            stage.max_seconds = elapsed
        if self.current is not None:
            self.current["forward_seconds"] = self.current["forward_seconds"] + elapsed

    def note_serialized_bytes(self, nbytes: int) -> None:
        self.serialized_bytes_total = self.serialized_bytes_total + nbytes
        if nbytes > self.serialized_bytes_maximum:
            self.serialized_bytes_maximum = nbytes
        if self.current is None:
            return
        self.current["serialize_bytes"] = self.current["serialize_bytes"] + nbytes
        self.current["serialize_calls"] = self.current["serialize_calls"] + 1
        bin_row = self._bin_for_current()
        if nbytes > bin_row.serialized_bytes_maximum:
            bin_row.serialized_bytes_maximum = nbytes

    def note_alignment_result(self, result) -> None:
        if self.current is None:
            raise RuntimeError(
                "stage baseline_fork_and_alignment ran outside a driver timing record."
            )
        if self.current["registered_visit_count"] is not None:
            raise RuntimeError(
                "stage baseline_fork_and_alignment at timestep "
                f"{self.current_timestep} ran more than once in one driver call."
            )
        fork_result = result.fork_result
        registered = fork_result.registered_visit_count
        fork_steps = fork_result.fork_steps_executed
        if type(registered) is not int or type(fork_steps) is not int:
            raise RuntimeError(
                "stage baseline_fork_and_alignment at timestep "
                f"{self.current_timestep}: visit or fork step count is not an int."
            )
        self.current["registered_visit_count"] = registered
        self.current["fork_steps"] = fork_steps
        self.registered_visit_count_total = self.registered_visit_count_total + registered
        if registered == 0:
            self.registered_visit_zero_count = self.registered_visit_zero_count + 1
        else:
            self.registered_visit_positive_count = (
                self.registered_visit_positive_count + 1
            )
        self.fork_steps_total = self.fork_steps_total + fork_steps
        if fork_steps > self.fork_steps_max:
            self.fork_steps_max = fork_steps
        if fork_steps == BASELINE_HORIZON_STEPS:
            self.fork_full_horizon_count = self.fork_full_horizon_count + 1

    def note_candidate_result(self, result) -> None:
        if self.current is None:
            raise RuntimeError(
                "stage candidate_local_virtual_calculations ran outside a driver "
                "timing record."
            )
        if self.current["candidate_count"] is not None:
            raise RuntimeError(
                "stage candidate_local_virtual_calculations at timestep "
                f"{self.current_timestep} ran more than once in one driver call."
            )
        candidate_count = 0
        node_results = result.node_local_virtual_calculation_results
        for node_result in node_results:
            for candidate in node_result.candidate_local_virtual_calculation_results:
                candidate_count = candidate_count + 1
                simulated = candidate.simulated_timestep_count
                if type(simulated) is not int:
                    raise RuntimeError(
                        "stage candidate_local_virtual_calculations at timestep "
                        f"{self.current_timestep}: simulated_timestep_count is "
                        f"{simulated!r}."
                    )
                self.candidate_execution_count = self.candidate_execution_count + 1
                self.simulated_timestep_total = self.simulated_timestep_total + simulated
                if simulated > self.simulated_timestep_max:
                    self.simulated_timestep_max = simulated
                stop_reason = candidate.stop_reason
                if stop_reason == RESOLVED_STOP and simulated < NEAR_HORIZON_MINIMUM_TIMESTEPS:
                    self.early_stop_candidate_count = self.early_stop_candidate_count + 1
                elif simulated >= NEAR_HORIZON_MINIMUM_TIMESTEPS or stop_reason == HORIZON_STOP:
                    self.near_horizon_candidate_count = self.near_horizon_candidate_count + 1
                else:
                    self.other_stop_candidate_count = self.other_stop_candidate_count + 1
        self.current["candidate_count"] = candidate_count
        previous = self.candidate_count_histogram.get(candidate_count, 0)
        self.candidate_count_histogram[candidate_count] = previous + 1

    def note_production_driver_seconds(self, elapsed: float) -> None:
        if self.current is None:
            raise RuntimeError(
                "stage production_driver ran outside a driver timing record."
            )
        if self.current["production_seconds"] is not None:
            raise RuntimeError(
                "stage production_driver at timestep "
                f"{self.current_timestep} was timed more than once."
            )
        self.current["production_seconds"] = elapsed
        self.production_driver_total_seconds = (
            self.production_driver_total_seconds + elapsed
        )

    def finish_timestep(self, driver_seconds: float) -> None:
        current = self.current
        if current is None:
            raise RuntimeError("stage audit_driver_wrapper finished without a start.")
        timestep = current["real_timestep"]
        if current["registered_visit_count"] is None:
            raise RuntimeError(
                "stage baseline_fork_and_alignment at timestep "
                f"{timestep} did not report a registered visit count."
            )
        if current["candidate_count"] is None:
            raise RuntimeError(
                "stage candidate_local_virtual_calculations at timestep "
                f"{timestep} did not report a candidate count."
            )
        if current["production_seconds"] is None:
            raise RuntimeError(
                f"stage production_driver at timestep {timestep} was not timed."
            )
        overhead = driver_seconds - current["production_seconds"]
        self.driver_call_count = self.driver_call_count + 1
        self.driver_total_seconds = self.driver_total_seconds + driver_seconds
        if driver_seconds > self.driver_max_seconds:
            self.driver_max_seconds = driver_seconds
        if self.driver_min_seconds is None or driver_seconds < self.driver_min_seconds:
            self.driver_min_seconds = driver_seconds
        self.audit_wrapper_call_count = self.audit_wrapper_call_count + 1
        self.audit_overhead_total_seconds = self.audit_overhead_total_seconds + overhead
        self.timesteps.append(
            {
                "real_timestep": timestep,
                "driver_seconds": driver_seconds,
                "baseline_stage_seconds": current["baseline_stage_seconds"],
                "candidate_local_stage_seconds": current["candidate_local_stage_seconds"],
                "candidate_count": current["candidate_count"],
                "registered_visit_count": current["registered_visit_count"],
                "baseline_fork_steps_executed": current["fork_steps"],
                "serialized_world_bytes": current["serialize_bytes"],
                "production_driver_seconds": current["production_seconds"],
                "audit_overhead_seconds": overhead,
            }
        )
        bin_row = self._bin_for_timestep(timestep)
        bin_row.driver_call_count = bin_row.driver_call_count + 1
        bin_row.driver_total_seconds = bin_row.driver_total_seconds + driver_seconds
        bin_row.baseline_prepare_seconds = (
            bin_row.baseline_prepare_seconds + current["prepare_seconds"]
        )
        bin_row.baseline_forward_seconds = (
            bin_row.baseline_forward_seconds + current["forward_seconds"]
        )
        bin_row.candidate_serialize_seconds = (
            bin_row.candidate_serialize_seconds + current["serialize_seconds"]
        )
        bin_row.candidate_load_seconds = (
            bin_row.candidate_load_seconds + current["load_seconds"]
        )
        bin_row.candidate_local_seconds = (
            bin_row.candidate_local_seconds + current["candidate_local_stage_seconds"]
        )
        if current["registered_visit_count"] == 0:
            bin_row.registered_visit_zero_count = bin_row.registered_visit_zero_count + 1
        if current["candidate_count"] == 0:
            bin_row.candidate_zero_count = bin_row.candidate_zero_count + 1
        bin_row.serialized_bytes_total = (
            bin_row.serialized_bytes_total + current["serialize_bytes"]
        )
        bin_row.serialize_call_count = (
            bin_row.serialize_call_count + current["serialize_calls"]
        )
        self.current = None

    def _bin_for_current(self) -> TimestepBin:
        if self.current is None:
            raise RuntimeError("No timestep is open for a bin update.")
        return self._bin_for_timestep(self.current["real_timestep"])

    def _bin_for_timestep(self, timestep: int) -> TimestepBin:
        for bin_row in self.bins:
            if bin_row.start_timestep <= timestep <= bin_row.end_timestep:
                return bin_row
        raise RuntimeError(
            f"timestep {timestep} is outside the diagnostic range "
            f"T={DIAGNOSTIC_FIRST_TIMESTEP}..{DIAGNOSTIC_LAST_TIMESTEP}."
        )


LEDGER = TimingLedger()
PATCHES: list[tuple[object, str, object]] = []
audit_hook_installed = False

original_prepare_baseline_fork = None
original_complete_baseline_fork = None
original_world_copy = None
original_serialize_real_world = None
original_load_candidate_world = None
original_align_baseline = None
original_candidate_local_calculations = None
ORIGINAL_RUN_TVT_MP_DRIVER = None
AUDIT_DRIVER_ENTRY = None
SAVED_WORLD_COPY = None
SAVED_RUN_TVT_MP_DRIVER = None


def _raise_unless_original_called_once(stage_name: str, called: int) -> None:
    if sys.exc_info()[0] is not None:
        return
    if called != 1:
        raise RuntimeError(
            f"stage {stage_name} at timestep {LEDGER.current_timestep} "
            f"called the original function {called} times; expected 1."
        )


def finish_timed_call(stage_name: str, started: float, called: int) -> float:
    elapsed = time.perf_counter() - started
    LEDGER.record_stage(stage_name, elapsed)
    _raise_unless_original_called_once(stage_name, called)
    return elapsed


def call_original_once(stage_name, original, args, kwargs):
    """Call one saved production function and time that single call."""
    started = time.perf_counter()
    called = 0
    try:
        result = original(*args, **kwargs)
        called = called + 1
        return result
    finally:
        finish_timed_call(stage_name, started, called)


def make_stage_wrapper(stage_name, original):
    def wrapper(*args, **kwargs):
        return call_original_once(stage_name, original, args, kwargs)

    return wrapper


def timed_prepare_baseline_fork(*args, **kwargs):
    started = time.perf_counter()
    called = 0
    try:
        result = original_prepare_baseline_fork(*args, **kwargs)
        called = called + 1
        return result
    finally:
        finish_timed_call("baseline_prepare", started, called)


def timed_complete_baseline_fork(*args, **kwargs):
    started = time.perf_counter()
    called = 0
    fork_steps_executed = None
    try:
        result = original_complete_baseline_fork(*args, **kwargs)
        called = called + 1
        fork_steps_executed = result.fork_steps_executed
        return result
    finally:
        elapsed = finish_timed_call("baseline_complete", started, called)
        if called == 1 and type(fork_steps_executed) is int and fork_steps_executed > 0:
            LEDGER.add_baseline_forward_seconds(elapsed)


def timed_world_copy(world):
    started = time.perf_counter()
    called = 0
    try:
        result = original_world_copy(world)
        called = called + 1
        return result
    finally:
        finish_timed_call("world_copy", started, called)


def timed_serialize_real_world(*args, **kwargs):
    started = time.perf_counter()
    called = 0
    try:
        result = original_serialize_real_world(*args, **kwargs)
        called = called + 1
        if type(result) is bytes:
            LEDGER.note_serialized_bytes(len(result))
        return result
    finally:
        finish_timed_call("candidate_serialize", started, called)


def timed_load_candidate_world(*args, **kwargs):
    started = time.perf_counter()
    called = 0
    try:
        result = original_load_candidate_world(*args, **kwargs)
        called = called + 1
        return result
    finally:
        finish_timed_call("candidate_load", started, called)


def timed_align_baseline(*args, **kwargs):
    started = time.perf_counter()
    called = 0
    try:
        result = original_align_baseline(*args, **kwargs)
        called = called + 1
        LEDGER.note_alignment_result(result)
        return result
    finally:
        finish_timed_call("baseline_fork_and_alignment", started, called)


def timed_candidate_local_calculations(*args, **kwargs):
    started = time.perf_counter()
    called = 0
    try:
        result = original_candidate_local_calculations(*args, **kwargs)
        called = called + 1
        LEDGER.note_candidate_result(result)
        return result
    finally:
        finish_timed_call("candidate_local_virtual_calculations", started, called)


def production_driver_timer(real_W):
    started = time.perf_counter()
    called = 0
    try:
        result = ORIGINAL_RUN_TVT_MP_DRIVER(real_W)
        called = called + 1
        return result
    finally:
        elapsed = time.perf_counter() - started
        if called == 1:
            LEDGER.note_production_driver_seconds(elapsed)
        _raise_unless_original_called_once("production_driver", called)


def audit_outer_timer(real_W):
    LEDGER.begin_timestep(real_W.T)
    started = time.perf_counter()
    called = 0
    try:
        result = AUDIT_DRIVER_ENTRY(real_W)
        called = called + 1
        return result
    finally:
        elapsed = time.perf_counter() - started
        _raise_unless_original_called_once("audit_driver_wrapper", called)
        if called == 1 and sys.exc_info()[0] is None:
            LEDGER.finish_timestep(elapsed)


def _replace(owner, attribute_name, wrapper) -> None:
    original = getattr(owner, attribute_name)
    PATCHES.append((owner, attribute_name, original))
    setattr(owner, attribute_name, wrapper)


def install_function_wrappers() -> None:
    """Patch the symbols the running driver and baseline actually look up."""
    global original_prepare_baseline_fork
    global original_complete_baseline_fork
    global original_world_copy
    global original_serialize_real_world
    global original_load_candidate_world
    global original_align_baseline
    global original_candidate_local_calculations
    global SAVED_WORLD_COPY

    for stage_name, attribute_name in GENERIC_DRIVER_STAGES:
        original = getattr(driver_module, attribute_name)
        _replace(driver_module, attribute_name, make_stage_wrapper(stage_name, original))

    original_align_baseline = getattr(
        driver_module,
        "run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
    )
    _replace(
        driver_module,
        "run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
        timed_align_baseline,
    )
    original_candidate_local_calculations = getattr(
        driver_module,
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
    )
    _replace(
        driver_module,
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
        timed_candidate_local_calculations,
    )

    original_prepare_baseline_fork = baseline_driver_module._prepare_baseline_fork
    _replace(
        baseline_driver_module,
        "_prepare_baseline_fork",
        timed_prepare_baseline_fork,
    )
    original_complete_baseline_fork = (
        baseline_driver_module._complete_baseline_fork_after_registration
    )
    _replace(
        baseline_driver_module,
        "_complete_baseline_fork_after_registration",
        timed_complete_baseline_fork,
    )

    original_world_copy = uxsim_module.World.copy
    SAVED_WORLD_COPY = original_world_copy
    _replace(uxsim_module.World, "copy", timed_world_copy)

    original_serialize_real_world = (
        candidate_set_module.serialize_tvt_mp_candidate_real_world_snapshot
    )
    _replace(
        candidate_set_module,
        "serialize_tvt_mp_candidate_real_world_snapshot",
        timed_serialize_real_world,
    )
    original_load_candidate_world = (
        candidate_set_module.build_tvt_mp_candidate_local_state_from_serialized_world
    )
    _replace(
        candidate_set_module,
        "build_tvt_mp_candidate_local_state_from_serialized_world",
        timed_load_candidate_world,
    )


def attach_audit_driver_wrapper(world) -> None:
    """Install the unchanged audit hook, then time its extra work."""
    global ORIGINAL_RUN_TVT_MP_DRIVER
    global AUDIT_DRIVER_ENTRY
    global audit_hook_installed
    global SAVED_RUN_TVT_MP_DRIVER

    SAVED_RUN_TVT_MP_DRIVER = driver_module.run_tvt_mp_driver
    ORIGINAL_RUN_TVT_MP_DRIVER = SAVED_RUN_TVT_MP_DRIVER
    _replace(driver_module, "run_tvt_mp_driver", production_driver_timer)
    install_tvt_mp_full_run_audit(world)
    audit_hook_installed = True
    AUDIT_DRIVER_ENTRY = driver_module.run_tvt_mp_driver
    driver_module.run_tvt_mp_driver = audit_outer_timer


def restore_measurement_wrappers() -> None:
    """Restore audit hooks and every patched production symbol."""
    global audit_hook_installed
    try:
        if audit_hook_installed:
            _restore_hooks()
            _clear_live_state()
            audit_hook_installed = False
    finally:
        while PATCHES:
            owner, attribute_name, original = PATCHES.pop()
            setattr(owner, attribute_name, original)


# ---------------------------------------------------------------------------
# 3. Network, plans, and World. Copied from the formal trial, not imported.
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


def verify_vehicle_plans(plans: list[dict]) -> str:
    if len(plans) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle plan count is {len(plans)}, expected {NUM_VEHICLES}.")
    digest = _vehicle_plan_digest(plans)
    if digest != EXPECTED_VEHICLE_PLAN_SHA256:
        raise RuntimeError(
            f"vehicle_plan_sha256 expected {EXPECTED_VEHICLE_PLAN_SHA256}, got {digest}."
        )
    return digest


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


def select_nonparticipating_names(plans: list[dict]) -> tuple[str, ...]:
    population = []
    for plan in plans:
        population.append(plan["name"])
    selected = select_nonparticipating_names_once(population)
    if len(selected) != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Nonparticipating selection did not return 600 names.")
    again = select_nonparticipating_names_once(population)
    if again != selected:
        raise RuntimeError("Nonparticipating selection is not repeatable.")
    return selected


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


def build_world_and_network() -> World:
    world = World(
        name=DIAGNOSTIC_WORLD_NAME,
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
    world.order_control_tvt_evaluation_end_timestep = LAST_TVT_DECISION_TIMESTEP_CAP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    return world


def add_vehicles_to_world(world: World, plans: list[dict], vot_values: list[float], nonparticipating_names: tuple[str, ...]) -> None:
    selected = set(nonparticipating_names)
    participating_count = 0
    nonparticipating_count = 0
    for plan, vot in zip(plans, vot_values):
        participates = plan["name"] not in selected
        if participates:
            world.addVehicle(
                plan["origin"],
                plan["destination"],
                plan["departure_time"],
                name=plan["name"],
                vot_true=vot,
                vot_declared=vot,
                participates_in_order_exchange=True,
            )
            participating_count = participating_count + 1
        else:
            world.addVehicle(
                plan["origin"],
                plan["destination"],
                plan["departure_time"],
                name=plan["name"],
                vot_true=vot,
                vot_declared=None,
                participates_in_order_exchange=False,
            )
            nonparticipating_count = nonparticipating_count + 1
    if participating_count != PARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(f"Participating count is {participating_count}, expected 2400.")
    if nonparticipating_count != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError(
            f"Nonparticipating count is {nonparticipating_count}, expected 600."
        )


def require_unchanged_driver_constants() -> None:
    if driver_module._DECISION_WINDOW_STEPS != DECISION_WINDOW_STEPS:
        raise RuntimeError(
            "TVT-MP decision window is "
            f"{driver_module._DECISION_WINDOW_STEPS}, expected {DECISION_WINDOW_STEPS}."
        )


def refuse_existing_output_directory() -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Diagnostic output directory already exists: {OUTPUT_DIR}. "
            "This script does not overwrite."
        )


def run_first_200_timesteps(world: World) -> None:
    executed = 0
    while world.T < DIAGNOSTIC_TIMESTEP_COUNT:
        before = world.T
        if before < DIAGNOSTIC_FIRST_TIMESTEP or before > DIAGNOSTIC_LAST_TIMESTEP:
            raise RuntimeError(
                f"Refusing to simulate timestep {before}. "
                f"This diagnosis stops after T={DIAGNOSTIC_LAST_TIMESTEP}."
            )
        world.exec_simulation(until_t=float(before) * float(world.DELTAT))
        if world.T != before + 1:
            raise RuntimeError(
                f"exec_simulation at timestep {before} left World.T at {world.T}."
            )
        executed = executed + 1
    if executed != DIAGNOSTIC_TIMESTEP_COUNT:
        raise RuntimeError(
            f"Executed {executed} real timesteps, expected {DIAGNOSTIC_TIMESTEP_COUNT}."
        )
    if world.T != DIAGNOSTIC_TIMESTEP_COUNT:
        raise RuntimeError(
            f"World.T is {world.T}, expected {DIAGNOSTIC_TIMESTEP_COUNT} "
            f"after T={DIAGNOSTIC_FIRST_TIMESTEP}..{DIAGNOSTIC_LAST_TIMESTEP}."
        )


def collect_vehicle_state_counts(world: World) -> dict[str, int]:
    counts = {"home": 0, "wait": 0, "run": 0, "end": 0}
    for vehicle in world.VEHICLES.values():
        state = vehicle.state
        if state not in counts:
            raise RuntimeError(f"Vehicle {vehicle.name} state {state!r} is unexpected.")
        counts[state] = counts[state] + 1
    if sum(counts.values()) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle state counts sum to {sum(counts.values())}, expected 3000.")
    return counts


def collect_node_rank_ledger_summary(world: World) -> dict:
    ledgers = world.order_control_tvt_rank_states_by_node_name
    summary = {}
    for node_name in INTERNAL_GRID_NODES:
        exported = ledgers[node_name].export_state()
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
        ordered[str(visit_id)] = visit_id_counts[visit_id]
    return {
        "visit_id_counts": ordered,
        "maximum_visit_id": max_visit_id,
    }


def collect_transaction_count(world: World) -> int:
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    return len(registry.trades_by_transaction_key)


def _average(total: float, count: int) -> float:
    if count == 0:
        return 0.0
    return total / count


def _histogram_rows() -> list[dict]:
    rows = []
    for candidate_count in sorted(LEDGER.candidate_count_histogram):
        rows.append(
            {
                "candidate_count": candidate_count,
                "driver_call_count": LEDGER.candidate_count_histogram[candidate_count],
            }
        )
    return rows


def _bin_payload(bin_row: TimestepBin) -> dict:
    return {
        "label": bin_row.label,
        "start_timestep": bin_row.start_timestep,
        "end_timestep": bin_row.end_timestep,
        "driver_call_count": bin_row.driver_call_count,
        "driver_total_seconds": bin_row.driver_total_seconds,
        "baseline_prepare_seconds": bin_row.baseline_prepare_seconds,
        "baseline_forward_seconds": bin_row.baseline_forward_seconds,
        "candidate_serialize_seconds": bin_row.candidate_serialize_seconds,
        "candidate_load_seconds": bin_row.candidate_load_seconds,
        "candidate_local_calculation_seconds": bin_row.candidate_local_seconds,
        "registered_visit_zero_count": bin_row.registered_visit_zero_count,
        "candidate_zero_count": bin_row.candidate_zero_count,
        "serialized_bytes_average": _average(
            bin_row.serialized_bytes_total,
            bin_row.serialize_call_count,
        ),
        "serialized_bytes_maximum": bin_row.serialized_bytes_maximum,
    }


def _top_stages(limit: int) -> list[dict]:
    ranked = []
    for stage_name in STAGE_ORDER:
        stage = LEDGER.stages[stage_name]
        ranked.append((stage.total_seconds, stage_name, stage))
    ranked.sort(key=lambda item: item[0], reverse=True)
    rows = []
    for _total, stage_name, stage in ranked[:limit]:
        rows.append(
            {
                "stage_name": stage_name,
                "call_count": stage.call_count,
                "total_seconds": stage.total_seconds,
                "maximum_seconds": stage.max_seconds,
            }
        )
    return rows


def build_summary(world: World, plans_digest: str, participation_digest: str, diagnostic_total_seconds: float, simulation_loop_seconds: float) -> dict:
    serialize_stage = LEDGER.stages["candidate_serialize"]
    load_stage = LEDGER.stages["candidate_load"]
    copy_stage = LEDGER.stages["world_copy"]
    prepare_stage = LEDGER.stages["baseline_prepare"]
    complete_stage = LEDGER.stages["baseline_complete"]
    local_stage = LEDGER.stages["candidate_local_virtual_calculations"]
    return {
        "diagnostic_only": DIAGNOSTIC_ONLY,
        "formal_evaluation": False,
        "awt_awwt_evaluated": False,
        "full_completion_required": False,
        "diagnostic_timestep_range": [
            DIAGNOSTIC_FIRST_TIMESTEP,
            DIAGNOSTIC_LAST_TIMESTEP,
        ],
        "real_timesteps_executed": DIAGNOSTIC_TIMESTEP_COUNT,
        "diagnostic_total_seconds": diagnostic_total_seconds,
        "simulation_loop_seconds": simulation_loop_seconds,
        "driver_call_count": LEDGER.driver_call_count,
        "driver_total_seconds": LEDGER.driver_total_seconds,
        "driver_max_seconds": LEDGER.driver_max_seconds,
        "driver_min_seconds": LEDGER.driver_min_seconds,
        "production_driver_total_seconds": LEDGER.production_driver_total_seconds,
        "audit_driver_wrapper_call_count": LEDGER.audit_wrapper_call_count,
        "audit_overhead_total_seconds": LEDGER.audit_overhead_total_seconds,
        "baseline_prepare_call_count": prepare_stage.call_count,
        "baseline_prepare_total_seconds": prepare_stage.total_seconds,
        "baseline_prepare_max_seconds": prepare_stage.max_seconds,
        "baseline_complete_call_count": complete_stage.call_count,
        "baseline_complete_total_seconds": complete_stage.total_seconds,
        "baseline_complete_max_seconds": complete_stage.max_seconds,
        "baseline_forward_call_count": LEDGER.stages["baseline_forward"].call_count,
        "baseline_forward_total_seconds": LEDGER.stages["baseline_forward"].total_seconds,
        "baseline_forward_max_seconds": LEDGER.stages["baseline_forward"].max_seconds,
        "world_copy_call_count": copy_stage.call_count,
        "world_copy_total_seconds": copy_stage.total_seconds,
        "world_copy_max_seconds": copy_stage.max_seconds,
        "registered_visit_count_total": LEDGER.registered_visit_count_total,
        "registered_visit_zero_count": LEDGER.registered_visit_zero_count,
        "registered_visit_positive_count": LEDGER.registered_visit_positive_count,
        "fork_steps_executed_total": LEDGER.fork_steps_total,
        "fork_steps_executed_max": LEDGER.fork_steps_max,
        "fork_full_horizon_30_count": LEDGER.fork_full_horizon_count,
        "candidate_serialize_call_count": serialize_stage.call_count,
        "candidate_serialize_total_seconds": serialize_stage.total_seconds,
        "candidate_serialize_max_seconds": serialize_stage.max_seconds,
        "serialized_world_bytes_total": LEDGER.serialized_bytes_total,
        "serialized_world_bytes_average": _average(
            LEDGER.serialized_bytes_total,
            serialize_stage.call_count,
        ),
        "serialized_world_bytes_maximum": LEDGER.serialized_bytes_maximum,
        "candidate_load_call_count": load_stage.call_count,
        "candidate_load_total_seconds": load_stage.total_seconds,
        "candidate_load_max_seconds": load_stage.max_seconds,
        "candidate_local_calculation_call_count": local_stage.call_count,
        "candidate_local_calculation_total_seconds": local_stage.total_seconds,
        "candidate_local_calculation_max_seconds": local_stage.max_seconds,
        "candidate_execution_count": LEDGER.candidate_execution_count,
        "candidate_simulated_timestep_total": LEDGER.simulated_timestep_total,
        "candidate_simulated_timestep_max": LEDGER.simulated_timestep_max,
        "early_stop_candidate_count": LEDGER.early_stop_candidate_count,
        "near_horizon_candidate_count": LEDGER.near_horizon_candidate_count,
        "near_horizon_minimum_timesteps": NEAR_HORIZON_MINIMUM_TIMESTEPS,
        "other_stop_candidate_count": LEDGER.other_stop_candidate_count,
        "candidate_count_histogram": _histogram_rows(),
        "candidate_execution_count_matches_load_count": (
            LEDGER.candidate_execution_count == load_stage.call_count
        ),
        "world_copy_count_matches_baseline_prepare_count": (
            copy_stage.call_count == prepare_stage.call_count
        ),
        "nested_stage_note": (
            "world_copy is inside baseline_prepare. "
            "baseline_prepare and baseline_forward are inside "
            "baseline_fork_and_alignment. "
            "candidate_serialize and candidate_load are inside "
            "candidate_local_virtual_calculations. "
            "Do not add these rows together."
        ),
        "timestep_bins": [_bin_payload(bin_row) for bin_row in LEDGER.bins],
        "timesteps": LEDGER.timesteps,
        "top_stages_by_total_seconds": _top_stages(5),
        "comparison_snapshot": {
            "world_T": world.T,
            "world_name": world.name,
            "hard_deterministic_mode": world.hard_deterministic_mode,
            "evaluation_end_timestep": world.order_control_tvt_evaluation_end_timestep,
            "baseline_horizon_steps": world.order_control_tvt_baseline_horizon_steps,
            "max_candidate_visit_count": world.order_control_tvt_max_candidate_visit_count,
            "driver_started_timestep": world.order_control_tvt_driver_started_timestep,
            "vehicle_state_counts": collect_vehicle_state_counts(world),
            "transaction_count": collect_transaction_count(world),
            "rank_ledger_summary": collect_node_rank_ledger_summary(world),
            "visit_id_summary": collect_visit_id_summary(world),
            "vehicle_plan_sha256": plans_digest,
            "participation_assignment_sha256": participation_digest,
        },
    }


def write_outputs(summary: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    summary_path = OUTPUT_DIR / "performance_summary.json"
    bins_path = OUTPUT_DIR / "performance_timestep_bins.csv"
    stages_path = OUTPUT_DIR / "performance_stage_totals.csv"
    text_path = OUTPUT_DIR / "run_summary.txt"
    for path in (summary_path, bins_path, stages_path, text_path):
        if path.exists():
            raise RuntimeError(f"Refusing to overwrite {path}.")
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    with bins_path.open("w", encoding="utf-8", newline="") as handle:
        field_names = [
            "label",
            "start_timestep",
            "end_timestep",
            "driver_call_count",
            "driver_total_seconds",
            "baseline_prepare_seconds",
            "baseline_forward_seconds",
            "candidate_serialize_seconds",
            "candidate_load_seconds",
            "candidate_local_calculation_seconds",
            "registered_visit_zero_count",
            "candidate_zero_count",
            "serialized_bytes_average",
            "serialized_bytes_maximum",
        ]
        writer = csv.DictWriter(handle, fieldnames=field_names)
        writer.writeheader()
        for row in summary["timestep_bins"]:
            writer.writerow(row)
    with stages_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("stage_name", "call_count", "total_seconds", "maximum_seconds"),
        )
        writer.writeheader()
        for stage_name in STAGE_ORDER:
            stage = LEDGER.stages[stage_name]
            writer.writerow(
                {
                    "stage_name": stage_name,
                    "call_count": stage.call_count,
                    "total_seconds": stage.total_seconds,
                    "maximum_seconds": stage.max_seconds,
                }
            )
    lines = [
        "TVT-MP 3000-vehicle performance diagnosis, first 200 real timesteps",
        "diagnostic_only: true",
        "formal AWT/AWWT evaluation: false",
        f"real timesteps executed: {summary['real_timesteps_executed']}",
        f"World.T: {summary['comparison_snapshot']['world_T']}",
        f"driver call count: {summary['driver_call_count']}",
        f"diagnostic total seconds: {summary['diagnostic_total_seconds']}",
        f"simulation loop seconds: {summary['simulation_loop_seconds']}",
        f"driver total seconds: {summary['driver_total_seconds']}",
        f"baseline prepare seconds: {summary['baseline_prepare_total_seconds']}",
        f"baseline completion seconds: {summary['baseline_complete_total_seconds']}",
        f"baseline forward seconds: {summary['baseline_forward_total_seconds']}",
        f"World.copy count: {summary['world_copy_call_count']}",
        f"World.copy seconds: {summary['world_copy_total_seconds']}",
        f"registered Visit 0 count: {summary['registered_visit_zero_count']}",
        f"candidate serialize count: {summary['candidate_serialize_call_count']}",
        f"candidate serialize seconds: {summary['candidate_serialize_total_seconds']}",
        f"candidate load count: {summary['candidate_load_call_count']}",
        f"candidate load seconds: {summary['candidate_load_total_seconds']}",
        f"serialized bytes average: {summary['serialized_world_bytes_average']}",
        f"serialized bytes maximum: {summary['serialized_world_bytes_maximum']}",
        f"candidate execution count: {summary['candidate_execution_count']}",
        f"candidate local calculation seconds: {summary['candidate_local_calculation_total_seconds']}",
        f"candidate simulated timestep total: {summary['candidate_simulated_timestep_total']}",
        f"audit wrapper overhead seconds: {summary['audit_overhead_total_seconds']}",
        f"transaction count: {summary['comparison_snapshot']['transaction_count']}",
        f"vehicle plan sha256: {summary['comparison_snapshot']['vehicle_plan_sha256']}",
        f"participation assignment sha256: {summary['comparison_snapshot']['participation_assignment_sha256']}",
        summary["nested_stage_note"],
        f"output directory: {OUTPUT_DIR}",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_console_summary(summary: dict) -> None:
    print()
    print("=== TVT-MP 3000-vehicle performance diagnosis, T=0..199 ===")
    print("diagnostic_only: true")
    print(f"real timesteps executed: {summary['real_timesteps_executed']}")
    print(f"driver call count: {summary['driver_call_count']}")
    print(f"total diagnostic runtime: {summary['diagnostic_total_seconds']}")
    print(f"simulation loop seconds: {summary['simulation_loop_seconds']}")
    print(f"driver total seconds: {summary['driver_total_seconds']}")
    print(f"baseline prepare seconds: {summary['baseline_prepare_total_seconds']}")
    print(f"baseline completion seconds: {summary['baseline_complete_total_seconds']}")
    print(f"baseline forward seconds: {summary['baseline_forward_total_seconds']}")
    print(
        "World.copy count and seconds: "
        f"{summary['world_copy_call_count']} {summary['world_copy_total_seconds']}"
    )
    print(f"registered Visit 0 count: {summary['registered_visit_zero_count']}")
    print(
        "candidate serialize count and seconds: "
        f"{summary['candidate_serialize_call_count']} "
        f"{summary['candidate_serialize_total_seconds']}"
    )
    print(
        "candidate loads count and seconds: "
        f"{summary['candidate_load_call_count']} {summary['candidate_load_total_seconds']}"
    )
    print(
        "serialized bytes average and maximum: "
        f"{summary['serialized_world_bytes_average']} "
        f"{summary['serialized_world_bytes_maximum']}"
    )
    print(
        "candidate local calculation count and seconds: "
        f"{summary['candidate_execution_count']} "
        f"{summary['candidate_local_calculation_total_seconds']}"
    )
    print(f"candidate simulated timestep total: {summary['candidate_simulated_timestep_total']}")
    print(f"audit wrapper overhead seconds: {summary['audit_overhead_total_seconds']}")
    print("top 5 stages by total seconds:")
    for row in summary["top_stages_by_total_seconds"]:
        print(
            f"  {row['stage_name']}: {row['total_seconds']} seconds "
            f"over {row['call_count']} calls"
        )
    print(f"output directory: {OUTPUT_DIR}")
    print(summary["nested_stage_note"])
    print()


def execute_first_200_timesteps() -> dict:
    refuse_existing_output_directory()
    require_unchanged_driver_constants()
    started = time.perf_counter()
    plans = generate_vehicle_plans()
    plans_digest = verify_vehicle_plans(plans)
    nonparticipating_names = select_nonparticipating_names(plans)
    participation_digest = participation_assignment_digest(plans, nonparticipating_names)
    vot_values = generate_vehicle_vots(NUM_VEHICLES)
    world = build_world_and_network()
    add_vehicles_to_world(world, plans, vot_values, nonparticipating_names)
    world.finalize_scenario()
    if world.DELTAT != 1:
        raise RuntimeError(f"DELTAT is {world.DELTAT!r}; this diagnosis requires 1.")
    if world.hard_deterministic_mode is not False:
        raise RuntimeError(
            "hard_deterministic_mode is "
            f"{world.hard_deterministic_mode!r}; this diagnosis must leave it False."
        )
    if hasattr(world, "performance_ledger"):
        raise RuntimeError("The World already has a performance ledger attribute.")
    attach_audit_driver_wrapper(world)
    loop_started = time.perf_counter()
    run_first_200_timesteps(world)
    simulation_loop_seconds = time.perf_counter() - loop_started
    if LEDGER.driver_call_count != DIAGNOSTIC_TIMESTEP_COUNT:
        raise RuntimeError(
            f"driver call count is {LEDGER.driver_call_count}, "
            f"expected {DIAGNOSTIC_TIMESTEP_COUNT}."
        )
    if hasattr(world, "performance_ledger"):
        raise RuntimeError("The diagnostic added a performance ledger to the World.")
    summary = build_summary(
        world,
        plans_digest,
        participation_digest,
        time.perf_counter() - started,
        simulation_loop_seconds,
    )
    write_outputs(summary)
    print_console_summary(summary)
    return summary


def run_diagnostic() -> int:
    original_recursion_limit = sys.getrecursionlimit()
    completed = False
    try:
        if original_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)
        try:
            install_function_wrappers()
            execute_first_200_timesteps()
            completed = True
        finally:
            restore_measurement_wrappers()
    finally:
        sys.setrecursionlimit(original_recursion_limit)
    if completed:
        if uxsim_module.World.copy is not SAVED_WORLD_COPY:
            raise RuntimeError("World.copy was not restored after the diagnostic.")
        if driver_module.run_tvt_mp_driver is not SAVED_RUN_TVT_MP_DRIVER:
            raise RuntimeError("run_tvt_mp_driver was not restored after the diagnostic.")
    return 0


# ---------------------------------------------------------------------------
# 4. Static validation. This does not simulate.
# ---------------------------------------------------------------------------

HAND_TIMED_ORIGINAL_NAMES = {
    "timed_prepare_baseline_fork": "original_prepare_baseline_fork",
    "timed_complete_baseline_fork": "original_complete_baseline_fork",
    "timed_world_copy": "original_world_copy",
    "timed_serialize_real_world": "original_serialize_real_world",
    "timed_load_candidate_world": "original_load_candidate_world",
    "timed_align_baseline": "original_align_baseline",
    "timed_candidate_local_calculations": "original_candidate_local_calculations",
    "production_driver_timer": "ORIGINAL_RUN_TVT_MP_DRIVER",
    "audit_outer_timer": "AUDIT_DRIVER_ENTRY",
}


def _function_node(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_count(function_node: ast.FunctionDef, called_name: str) -> int:
    count = 0
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == called_name:
                count = count + 1
    return count


def _imports_formal_trial(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == FORMAL_TRIAL_MODULE_NAME:
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == FORMAL_TRIAL_MODULE_NAME:
                    return True
    return False


def _has_restore_finally(function_node: ast.FunctionDef) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Try):
            continue
        for final_node in node.finalbody:
            if _call_count_in_statement(final_node, "restore_measurement_wrappers") > 0:
                return True
    return False


def _call_count_in_statement(statement, called_name: str) -> int:
    count = 0
    for node in ast.walk(statement):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == called_name:
                count = count + 1
    return count


def _assigned_constant(tree: ast.Module, name: str):
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                if isinstance(node.value, ast.Constant):
                    return node.value.value
    return None


def validate_diagnostic_script_statically() -> None:
    if SCRIPT_PATH.name != DIAGNOSTIC_SCRIPT_NAME:
        raise RuntimeError(f"Script name is {SCRIPT_PATH.name!r}.")
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if _imports_formal_trial(tree):
        raise RuntimeError("The diagnostic script imports the formal trial module.")
    if _assigned_constant(tree, "DIAGNOSTIC_ONLY") is not True:
        raise RuntimeError("DIAGNOSTIC_ONLY must be True.")
    if _assigned_constant(tree, "NUM_VEHICLES") != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if _assigned_constant(tree, "TRAFFIC_SEED") != 0:
        raise RuntimeError("TRAFFIC_SEED must be 0.")
    if _assigned_constant(tree, "DEMAND_GEN_SEED") != 42:
        raise RuntimeError("DEMAND_GEN_SEED must be 42.")
    if _assigned_constant(tree, "VOT_SEED") != 1:
        raise RuntimeError("VOT_SEED must be 1.")
    if _assigned_constant(tree, "NONPARTICIPATION_SEED") != 3:
        raise RuntimeError("NONPARTICIPATION_SEED must be 3.")
    if _assigned_constant(tree, "NONPARTICIPATING_VEHICLE_COUNT") != 600:
        raise RuntimeError("NONPARTICIPATING_VEHICLE_COUNT must be 600.")
    if _assigned_constant(tree, "BASELINE_HORIZON_STEPS") != 30:
        raise RuntimeError("BASELINE_HORIZON_STEPS must be 30.")
    if _assigned_constant(tree, "DECISION_WINDOW_STEPS") != 6:
        raise RuntimeError("DECISION_WINDOW_STEPS must be 6.")
    if _assigned_constant(tree, "MAX_CANDIDATE_VISIT_COUNT") != 10:
        raise RuntimeError("MAX_CANDIDATE_VISIT_COUNT must be 10.")
    if _assigned_constant(tree, "DIAGNOSTIC_FIRST_TIMESTEP") != 0:
        raise RuntimeError("DIAGNOSTIC_FIRST_TIMESTEP must be 0.")
    if _assigned_constant(tree, "DIAGNOSTIC_LAST_TIMESTEP") != 199:
        raise RuntimeError("DIAGNOSTIC_LAST_TIMESTEP must be 199.")
    if _function_node(tree, "install_function_wrappers") is None:
        raise RuntimeError("install_function_wrappers is missing.")
    if _function_node(tree, "restore_measurement_wrappers") is None:
        raise RuntimeError("restore_measurement_wrappers is missing.")
    if _function_node(tree, "refuse_existing_output_directory") is None:
        raise RuntimeError("refuse_existing_output_directory is missing.")
    run_diagnostic_node = _function_node(tree, "run_diagnostic")
    if run_diagnostic_node is None or not _has_restore_finally(run_diagnostic_node):
        raise RuntimeError("run_diagnostic must restore wrappers in a finally block.")
    call_once = _function_node(tree, "call_original_once")
    if call_once is None or _call_count(call_once, "original") != 1:
        raise RuntimeError("call_original_once must call original exactly once.")
    for function_name, original_name in HAND_TIMED_ORIGINAL_NAMES.items():
        function_node = _function_node(tree, function_name)
        if function_node is None:
            raise RuntimeError(f"{function_name} is missing.")
        if _call_count(function_node, original_name) != 1:
            raise RuntimeError(
                f"{function_name} must call {original_name} exactly once."
            )
    if _function_node(tree, "evaluate_network_wide_waiting_time") is not None:
        raise RuntimeError("This diagnosis must not define an AWT evaluation.")
    print("static validation passed")


def main() -> int:
    if len(sys.argv) > 2:
        raise SystemExit("Use no arguments, or --static-validate-only.")
    if len(sys.argv) == 2:
        if sys.argv[1] != "--static-validate-only":
            raise SystemExit(f"Unknown option {sys.argv[1]!r}.")
        validate_diagnostic_script_statically()
        return 0
    return run_diagnostic()


if __name__ == "__main__":
    raise SystemExit(main())
