"""
TVT-MP 50-vehicle asymmetric-demand trial run (not a formal experiment).

Same 2-inflow single-lane merge network and TVT-MP settings as the 50-vehicle
medium-demand trial, with highly asymmetric inflow: 40 vehicles from orig_a
(every timestep T=5..44) and 10 vehicles from orig_b (every 4 timesteps).

See TVT_MP_EXPERIMENT_DESIGN_NOTES.md for broader experiment context.
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

SCENARIO_NAME = "tvt_mp_50_vehicle_asymmetric_demand_trial"

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

HIGH_DENSITY_ORIGIN = "orig_a"
LOW_DENSITY_ORIGIN = "orig_b"
HIGH_DENSITY_VEHICLE_COUNT = 40
LOW_DENSITY_VEHICLE_COUNT = 10
HIGH_DENSITY_DEPARTURE_START = 5
HIGH_DENSITY_DEPARTURE_END = 44
HIGH_DENSITY_DEPARTURE_INTERVAL = 1
LOW_DENSITY_DEPARTURE_TIMESTEPS: tuple[int, ...] = (
    5,
    9,
    13,
    17,
    21,
    25,
    29,
    33,
    37,
    41,
)
LOW_DENSITY_DEPARTURE_INTERVAL = 4

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = (
    TRIAL_PARENT / "tvt_mp_50_vehicle_asymmetric_demand_seed_1_initial"
)

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)

SCRIPT_PATH = Path(__file__).resolve()

# Existing 50-vehicle medium-demand trial directories (must not be reused).
KNOWN_MEDIUM_DEMAND_TRIAL_DIR_NAMES: tuple[str, ...] = (
    "tvt_mp_50_vehicle_medium_demand_seed_1_initial",
    "tvt_mp_50_vehicle_medium_demand_seed_1_passage_resolution_v2",
    "tvt_mp_50_vehicle_medium_demand_seed_1_capacity_refill_v3",
    "tvt_mp_50_vehicle_medium_demand_seed_1_initial_decision_trace",
    "tvt_mp_50_vehicle_medium_demand_seed_1_passage_resolution_v2_decision_trace",
    "tvt_mp_50_vehicle_medium_demand_seed_1_capacity_refill_v3_decision_trace",
)


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool


def _build_vehicle_specs() -> tuple[VehicleSpec, ...]:
    """
    Build 50 VehicleSpec entries.

    Departure timestep ascending; at equal T, orig_a before orig_b.
    All vehicles participate in order exchange.
    """
    specs: list[VehicleSpec] = []

    for index in range(1, HIGH_DENSITY_VEHICLE_COUNT + 1):
        departure = HIGH_DENSITY_DEPARTURE_START + (index - 1)
        specs.append(
            VehicleSpec(
                vehicle_name=f"veh_a{index}",
                orig=HIGH_DENSITY_ORIGIN,
                dest="dest",
                departure_timestep=departure,
                participating=True,
            )
        )

    for index, departure in enumerate(LOW_DENSITY_DEPARTURE_TIMESTEPS, start=1):
        specs.append(
            VehicleSpec(
                vehicle_name=f"veh_b{index}",
                orig=LOW_DENSITY_ORIGIN,
                dest="dest",
                departure_timestep=departure,
                participating=True,
            )
        )

    def sort_key(spec: VehicleSpec) -> tuple[int, int]:
        origin_order = 0 if spec.orig == HIGH_DENSITY_ORIGIN else 1
        return (spec.departure_timestep, origin_order)

    specs.sort(key=sort_key)
    return tuple(specs)


# Departure timestep ascending; at equal T, orig_a entries before orig_b.
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


def _orig_a_departure_timesteps(specs: tuple[VehicleSpec, ...]) -> list[int]:
    return [
        s.departure_timestep
        for s in specs
        if s.orig == HIGH_DENSITY_ORIGIN
    ]


def _orig_b_departure_timesteps(specs: tuple[VehicleSpec, ...]) -> list[int]:
    return [
        s.departure_timestep
        for s in specs
        if s.orig == LOW_DENSITY_ORIGIN
    ]


def manifest_counts_from_specs(
    specs: tuple[VehicleSpec, ...],
) -> dict[str, int | str | list[int]]:
    """Manifest count fields derived only from VEHICLE_SPECS."""
    return {
        "vehicle_count": len(specs),
        "orig_a_count": sum(1 for s in specs if s.orig == HIGH_DENSITY_ORIGIN),
        "orig_b_count": sum(1 for s in specs if s.orig == LOW_DENSITY_ORIGIN),
        "participating_count": sum(1 for s in specs if s.participating),
        "nonparticipating_count": sum(1 for s in specs if not s.participating),
        "high_density_origin": HIGH_DENSITY_ORIGIN,
        "low_density_origin": LOW_DENSITY_ORIGIN,
        "high_density_departure_start": HIGH_DENSITY_DEPARTURE_START,
        "high_density_departure_end": HIGH_DENSITY_DEPARTURE_END,
        "high_density_departure_interval": HIGH_DENSITY_DEPARTURE_INTERVAL,
        "low_density_departure_timesteps": list(LOW_DENSITY_DEPARTURE_TIMESTEPS),
        "low_density_departure_interval": LOW_DENSITY_DEPARTURE_INTERVAL,
    }


def validate_static_contract() -> None:
    specs = VEHICLE_SPECS
    counts = manifest_counts_from_specs(specs)

    if counts["vehicle_count"] != 50:
        raise RuntimeError(f"Expected 50 VehicleSpec, got {counts['vehicle_count']}.")
    if counts["orig_a_count"] != 40:
        raise RuntimeError(f"Expected 40 orig_a, got {counts['orig_a_count']}.")
    if counts["orig_b_count"] != 10:
        raise RuntimeError(f"Expected 10 orig_b, got {counts['orig_b_count']}.")
    if counts["participating_count"] != 50:
        raise RuntimeError(
            f"Expected 50 participating, got {counts['participating_count']}."
        )
    if counts["nonparticipating_count"] != 0:
        raise RuntimeError(
            f"Expected 0 nonparticipating, got {counts['nonparticipating_count']}."
        )

    orig_a_deps = _orig_a_departure_timesteps(specs)
    expected_a = list(
        range(HIGH_DENSITY_DEPARTURE_START, HIGH_DENSITY_DEPARTURE_END + 1)
    )
    if orig_a_deps != expected_a:
        raise RuntimeError(
            f"orig_a departures expected {expected_a}, got {orig_a_deps}."
        )

    orig_b_deps = _orig_b_departure_timesteps(specs)
    if orig_b_deps != list(LOW_DENSITY_DEPARTURE_TIMESTEPS):
        raise RuntimeError(
            f"orig_b departures expected {list(LOW_DENSITY_DEPARTURE_TIMESTEPS)}, "
            f"got {orig_b_deps}."
        )

    def spec_order_key(spec: VehicleSpec) -> tuple[int, int]:
        origin_order = 0 if spec.orig == HIGH_DENSITY_ORIGIN else 1
        return (spec.departure_timestep, origin_order)

    for index in range(1, len(specs)):
        prev_key = spec_order_key(specs[index - 1])
        curr_key = spec_order_key(specs[index])
        if curr_key < prev_key:
            raise RuntimeError(
                "VEHICLE_SPECS is not sorted by departure timestep ascending, "
                "then orig_a before orig_b at equal T."
            )

    departure_keys = [(s.orig, s.departure_timestep) for s in specs]
    if len(set(departure_keys)) != len(departure_keys):
        raise RuntimeError("Duplicate (origin, departure_timestep) in VEHICLE_SPECS.")

    manifest_vehicle_count = counts["vehicle_count"]
    if manifest_vehicle_count != len(specs):
        raise RuntimeError("manifest vehicle_count inconsistent with VEHICLE_SPECS.")

    output_name = TRIAL_OUTPUT_DIR.name
    if output_name in KNOWN_MEDIUM_DEMAND_TRIAL_DIR_NAMES:
        raise RuntimeError(
            f"Output directory name collides with known medium-demand trial: "
            f"{output_name}."
        )
    for known in KNOWN_MEDIUM_DEMAND_TRIAL_DIR_NAMES:
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
        name="tvt_mp_50_vehicle_asymmetric_demand",
        deltan=1,
        reaction_time=1,
        tmax=330,
        random_seed=TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
    )

    world.addNode("orig_a", 0, 1)
    world.addNode("orig_b", 0, -1)
    world.addNode("merge", 1, 0)
    world.addNode("dest", 2, 0)

    world.addLink(
        "in_a",
        "orig_a",
        "merge",
        length=LINK_LENGTH_M,
        free_flow_speed=FREE_FLOW_SPEED_M_PER_S,
        number_of_lanes=NUMBER_OF_LANES,
    )
    world.addLink(
        "in_b",
        "orig_b",
        "merge",
        length=LINK_LENGTH_M,
        free_flow_speed=FREE_FLOW_SPEED_M_PER_S,
        number_of_lanes=NUMBER_OF_LANES,
    )
    world.addLink(
        "out",
        "merge",
        "dest",
        length=LINK_LENGTH_M,
        free_flow_speed=FREE_FLOW_SPEED_M_PER_S,
        number_of_lanes=NUMBER_OF_LANES,
    )

    world.infer_order_control_eligible_nodes()
    world.set_order_control_for_nodes(
        ["merge"],
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
# 4. Vehicle addition
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
    asymmetric_fields = manifest_counts_from_specs(VEHICLE_SPECS)
    manifest = {
        "schema_note": (
            "50-vehicle asymmetric-demand trial manifest only; "
            "not a formal experiment schema."
        ),
        "run_type": "trial",
        "scenario_name": SCENARIO_NAME,
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
        "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
        "decision_window_contract": DECISION_WINDOW_CONTRACT,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "clearance_timesteps": clearance_timesteps,
        "free_flow_speed_m_per_s": FREE_FLOW_SPEED_M_PER_S,
        "link_length_m": LINK_LENGTH_M,
        "number_of_lanes": NUMBER_OF_LANES,
        "vehicle_count": asymmetric_fields["vehicle_count"],
        "orig_a_count": asymmetric_fields["orig_a_count"],
        "orig_b_count": asymmetric_fields["orig_b_count"],
        "participating_count": asymmetric_fields["participating_count"],
        "nonparticipating_count": asymmetric_fields["nonparticipating_count"],
        "high_density_origin": asymmetric_fields["high_density_origin"],
        "low_density_origin": asymmetric_fields["low_density_origin"],
        "high_density_departure_start": asymmetric_fields["high_density_departure_start"],
        "high_density_departure_end": asymmetric_fields["high_density_departure_end"],
        "high_density_departure_interval": asymmetric_fields[
            "high_density_departure_interval"
        ],
        "low_density_departure_timesteps": asymmetric_fields[
            "low_density_departure_timesteps"
        ],
        "low_density_departure_interval": asymmetric_fields[
            "low_density_departure_interval"
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
        "TVT-MP 50-vehicle asymmetric-demand trial run summary",
        "=" * 50,
        f"Completed run: yes",
        f"Scenario name: {SCENARIO_NAME}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Demand asymmetry:",
        f"  orig_a {counts['orig_a_count']} / orig_b {counts['orig_b_count']}",
        (
            f"  participating {counts['participating_count']} / "
            f"nonparticipating {counts['nonparticipating_count']}"
        ),
        (
            f"  high-density {HIGH_DENSITY_ORIGIN}: departures T="
            f"{HIGH_DENSITY_DEPARTURE_START}..{HIGH_DENSITY_DEPARTURE_END} "
            f"every {HIGH_DENSITY_DEPARTURE_INTERVAL} timestep"
        ),
        (
            f"  low-density {LOW_DENSITY_ORIGIN}: departures T="
            f"{list(LOW_DENSITY_DEPARTURE_TIMESTEPS)[0]}.."
            f"{list(LOW_DENSITY_DEPARTURE_TIMESTEPS)[-1]} "
            f"every {LOW_DENSITY_DEPARTURE_INTERVAL} timesteps "
            f"({list(LOW_DENSITY_DEPARTURE_TIMESTEPS)})"
        ),
        "  T=5: simultaneous departure veh_a1 (orig_a) and veh_b1 (orig_b)",
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
    print("=== TVT-MP 50-vehicle asymmetric-demand trial ===")
    print()
    print(
        f"Demand: orig_a {counts['orig_a_count']} / orig_b {counts['orig_b_count']}; "
        f"participating {counts['participating_count']} / "
        f"nonparticipating {counts['nonparticipating_count']}"
    )
    print()
    print("Vehicles (name, participating, true VOT, declared VOT):")
    for record in vot_records:
        part = "Y" if record.participates_in_order_exchange else "N"
        declared_display = (
            "None"
            if record.declared_vot_per_second is None
            else f"{record.declared_vot_per_second:.6g}"
        )
        print(
            f"  {record.vehicle_name}: part={part}, "
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
            ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
            print("Static contract validation passed.", file=sys.stderr)
            raise SystemExit(0)
        raise SystemExit(main())
    except FileExistsError as exc:
        print(f"FileExistsError: {exc}", file=sys.stderr)
        raise SystemExit(1)
