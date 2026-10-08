"""
TVT-MP initial small-scale trial run (not a formal experiment).

See TVT_MP_EXPERIMENT_DESIGN_NOTES.md for experiment conditions.
"""

from __future__ import annotations

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

SCENARIO_NAME = "tvt_mp_small_scale_initial_run"

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

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = TRIAL_PARENT / "tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2"

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)

SCRIPT_PATH = Path(__file__).resolve()


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool


VEHICLE_SPECS: tuple[VehicleSpec, ...] = (
    VehicleSpec("veh_a1", "orig_a", "dest", 5, False),
    VehicleSpec("veh_b1", "orig_b", "dest", 6, True),
    VehicleSpec("veh_a2", "orig_a", "dest", 7, True),
    VehicleSpec("veh_b2", "orig_b", "dest", 8, True),
    VehicleSpec("veh_a3", "orig_a", "dest", 9, True),
    VehicleSpec("veh_b3", "orig_b", "dest", 10, False),
    VehicleSpec("veh_a4", "orig_a", "dest", 11, True),
    VehicleSpec("veh_b4", "orig_b", "dest", 12, True),
    VehicleSpec("veh_a5", "orig_a", "dest", 13, True),
    VehicleSpec("veh_b5", "orig_b", "dest", 14, True),
)


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
# 2. VOT generation
# ---------------------------------------------------------------------------


def generate_vehicle_vots(rng: np.random.Generator, count: int) -> list[float]:
    """One lognormal draw per vehicle, in definition order."""
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
        name="tvt_mp_small_scale_initial",
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
    manifest = {
        "schema_note": "Initial trial manifest only; not a formal experiment schema.",
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
        "vehicle_count": len(VEHICLE_SPECS),
        "participating_count": sum(1 for s in VEHICLE_SPECS if s.participating),
        "nonparticipating_count": sum(
            1 for s in VEHICLE_SPECS if not s.participating
        ),
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
    scenario_row = bundle.scenario[0]
    lines = [
        "TVT-MP initial small-scale trial run summary",
        "=" * 50,
        f"Completed run: yes",
        f"Scenario name: {SCENARIO_NAME}",
        f"World.T after exec_simulation: {world.T}",
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
    print()
    print("=== TVT-MP small-scale initial trial ===")
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
        raise SystemExit(main())
    except FileExistsError as exc:
        print(f"FileExistsError: {exc}", file=sys.stderr)
        raise SystemExit(1)
