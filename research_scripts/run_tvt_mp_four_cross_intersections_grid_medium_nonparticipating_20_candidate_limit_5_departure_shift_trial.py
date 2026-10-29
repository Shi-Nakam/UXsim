"""
TVT-MP trial: N=5 candidate-limit with aligned uniform departure shift (1, 2, or 3).

Independent trials derived from the completed base N=5 candidate-limit trial
(run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial).

Shift 0 is the existing base N=5 trial. This script runs shift 1, 2, or 3 only.

For each shift, the only intentional traffic-condition change is:

    departure_timestep_new = departure_timestep_base_n5 + shift

Evaluation end, internal TSIZE, and expected World.T shift in parallel so the same
base-aligned observation window (old trial T=0..899) is covered:

    evaluation_end = 899 + shift
    internal TSIZE = 930 + shift
    expected World.T = 900 + shift

Candidate Visit count upper bound remains N=5.

Purpose: efficient phase comparison of departure shifts 0/1/2/3 (even arrival clustering).

Does not modify production, base N=5, N=10, all-participating, or the legacy
departure_plus_1 (non-aligned) trial or existing outputs.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import sys
import time
from dataclasses import dataclass, fields, replace
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_all_participating_trial as reference
import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial as base_n5
import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_plus_1_trial as departure_plus_1_reference
import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial as nonparticipating_20_reference
from uxsim import World
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

ALLOWED_DEPARTURE_SHIFTS = (1, 2, 3)
ALIGNED_BASE_EVALUATION_END_TIMESTEP = 899
ALIGNED_BASE_INTERNAL_TSIZE = 930
ALIGNED_BASE_EXPECTED_WORLD_T = 900
EVALUATION_START_TIMESTEP = 0

MAX_CANDIDATE_VISIT_COUNT = 5

NONPARTICIPATION_SEED = base_n5.NONPARTICIPATION_SEED
NONPARTICIPATING_VEHICLE_COUNT = base_n5.NONPARTICIPATING_VEHICLE_COUNT
EXPECTED_TOTAL_VEHICLE_COUNT = base_n5.EXPECTED_TOTAL_VEHICLE_COUNT
EXPECTED_PARTICIPATING_COUNT = base_n5.EXPECTED_PARTICIPATING_COUNT
EXPECTED_NONPARTICIPATING_COUNT = base_n5.EXPECTED_NONPARTICIPATING_COUNT
NONPARTICIPATING_VEHICLE_NAMES = base_n5.NONPARTICIPATING_VEHICLE_NAMES
NONPARTICIPATING_NAME_HASH = base_n5.NONPARTICIPATING_NAME_HASH

VEHICLE_VOT_FIELDS = base_n5.VEHICLE_VOT_FIELDS
AUXILIARY_FILE_NAMES = base_n5.AUXILIARY_FILE_NAMES


@dataclass(frozen=True)
class ShiftTrialConfig:
    shift: int
    evaluation_end_timestep: int
    internal_tsize: int
    expected_world_t_after_sim: int
    scenario_name: str
    world_display_name: str
    trial_output_dir_name: str
    trial_output_dir: Path


def shift_trial_config(shift: int) -> ShiftTrialConfig:
    if shift not in ALLOWED_DEPARTURE_SHIFTS:
        raise ValueError(
            f"departure shift must be one of {ALLOWED_DEPARTURE_SHIFTS}; got {shift!r}."
        )
    evaluation_end = ALIGNED_BASE_EVALUATION_END_TIMESTEP + shift
    internal_tsize = ALIGNED_BASE_INTERNAL_TSIZE + shift
    expected_world_t = ALIGNED_BASE_EXPECTED_WORLD_T + shift
    horizon = reference.BASELINE_HORIZON_STEPS
    if internal_tsize != evaluation_end + horizon + 1:
        raise RuntimeError(
            f"INTERNAL_TSIZE {internal_tsize} != evaluation_end {evaluation_end} + "
            f"horizon {horizon} + 1."
        )
    prefix = (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "candidate_limit_5_departure_plus_"
    )
    scenario_name = (
        f"{prefix}{shift}_600_vehicle_eval_900_aligned_timestep_trial"
    )
    world_display_name = (
        f"{prefix}{shift}_600_vehicle_eval_900_aligned"
    )
    trial_output_dir_name = (
        f"{prefix}{shift}_600_vehicle_eval_900_aligned_timestep_seed_1_"
        "nonparticipation_seed_3_initial"
    )
    trial_output_dir = reference.TRIAL_PARENT / trial_output_dir_name
    return ShiftTrialConfig(
        shift=shift,
        evaluation_end_timestep=evaluation_end,
        internal_tsize=internal_tsize,
        expected_world_t_after_sim=expected_world_t,
        scenario_name=scenario_name,
        world_display_name=world_display_name,
        trial_output_dir_name=trial_output_dir_name,
        trial_output_dir=trial_output_dir,
    )


def parse_command_line(argv: list[str]) -> tuple[int, bool]:
    parser = argparse.ArgumentParser(
        description=(
            "N=5 candidate-limit trial with aligned departure shift 1, 2, or 3 "
            "(shift 0 uses the existing base N=5 trial)."
        ),
    )
    parser.add_argument(
        "--shift",
        type=int,
        required=True,
        help="Uniform departure shift in timesteps (allowed: 1, 2, 3).",
    )
    parser.add_argument(
        "--static-validate-only",
        action="store_true",
        help="Run static contract validation without simulation or output creation.",
    )
    args = parser.parse_args(argv)
    if args.shift == 0:
        raise SystemExit(
            "Shift 0 is the existing base N=5 trial; use "
            "run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
            "candidate_limit_5_trial.py instead of this script."
        )
    if args.shift not in ALLOWED_DEPARTURE_SHIFTS:
        raise SystemExit(
            f"Shift must be 1, 2, or 3; got {args.shift!r}."
        )
    return args.shift, args.static_validate_only


def build_vehicle_specs(shift: int) -> tuple[reference.VehicleSpec, ...]:
    specs: list[reference.VehicleSpec] = []
    for spec in base_n5.VEHICLE_SPECS:
        specs.append(
            replace(
                spec,
                departure_timestep=spec.departure_timestep + shift,
            )
        )
    return tuple(specs)


def _true_vot_sequence() -> list[float]:
    return base_n5._true_vot_sequence()


def build_vehicle_vot_records(
    specs: tuple[reference.VehicleSpec, ...],
    vot_values: list[float],
) -> list[reference.VehicleVotRecord]:
    if len(specs) != len(vot_values):
        raise RuntimeError("VehicleSpec count and VOT count differ.")
    records: list[reference.VehicleVotRecord] = []
    for spec, vot in zip(specs, vot_values):
        if spec.participating:
            records.append(
                reference.VehicleVotRecord(
                    vehicle_name=spec.vehicle_name,
                    origin=spec.orig,
                    destination=spec.dest,
                    departure_timestep=spec.departure_timestep,
                    participates_in_order_exchange=True,
                    true_vot_per_second=vot,
                    declared_vot_per_second=vot,
                )
            )
        else:
            records.append(
                reference.VehicleVotRecord(
                    vehicle_name=spec.vehicle_name,
                    origin=spec.orig,
                    destination=spec.dest,
                    departure_timestep=spec.departure_timestep,
                    participates_in_order_exchange=False,
                    true_vot_per_second=vot,
                    declared_vot_per_second=None,
                )
            )
    return records


def add_vehicles_to_world(
    world,
    specs: tuple[reference.VehicleSpec, ...],
    vot_records: list[reference.VehicleVotRecord],
) -> None:
    for spec, vot_record in zip(specs, vot_records):
        if spec.participating:
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
        else:
            world.addVehicle(
                spec.orig,
                spec.dest,
                spec.departure_timestep,
                name=spec.vehicle_name,
                departure_time_is_time_step=1,
                vot_true=vot_record.true_vot_per_second,
                vot_declared=None,
                participates_in_order_exchange=False,
            )


def _vehicle_specs_by_traffic_group_preserving_order(
    specs: tuple[reference.VehicleSpec, ...],
) -> list[tuple[str, list[reference.VehicleSpec]]]:
    grouped: dict[str, list[reference.VehicleSpec]] = {}
    group_order: list[str] = []
    for spec in specs:
        traffic_group = spec.traffic_group
        if traffic_group not in grouped:
            grouped[traffic_group] = []
            group_order.append(traffic_group)
        grouped[traffic_group].append(spec)
    return [(traffic_group, grouped[traffic_group]) for traffic_group in group_order]


def _assert_traffic_group_departure_structure(
    shift: int,
    vehicle_specs: tuple[reference.VehicleSpec, ...],
) -> None:
    base_by_group = _vehicle_specs_by_traffic_group_preserving_order(base_n5.VEHICLE_SPECS)
    new_by_group = _vehicle_specs_by_traffic_group_preserving_order(vehicle_specs)
    base_group_names = [name for name, _ in base_by_group]
    new_group_names = [name for name, _ in new_by_group]
    if base_group_names != new_group_names:
        raise RuntimeError(
            "Traffic group set or first-appearance order differs from base N=5 trial."
        )
    for (base_group_name, base_group_specs), (new_group_name, new_group_specs) in zip(
        base_by_group, new_by_group
    ):
        if base_group_name != new_group_name:
            raise RuntimeError("Traffic group name mismatch during departure structure check.")
        if len(new_group_specs) != len(base_group_specs):
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: vehicle count differs from base N=5."
            )
        base_names = [spec.vehicle_name for spec in base_group_specs]
        new_names = [spec.vehicle_name for spec in new_group_specs]
        if new_names != base_names:
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: vehicle name order differs from base N=5."
            )
        base_group_departures = [spec.departure_timestep for spec in base_group_specs]
        new_group_departures = [spec.departure_timestep for spec in new_group_specs]
        for vehicle_name, base_dep, new_dep in zip(
            base_names, base_group_departures, new_group_departures
        ):
            if new_dep != base_dep + shift:
                raise RuntimeError(
                    f"Traffic group {base_group_name!r}, {vehicle_name!r}: departure not "
                    f"base+{shift} ({base_dep} -> {new_dep})."
                )
        if new_group_departures[0] != base_group_departures[0] + shift:
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: first departure not base+{shift}."
            )
        if new_group_departures[-1] != base_group_departures[-1] + shift:
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: last departure not base+{shift}."
            )
        if len(base_group_departures) >= 2:
            base_in_group_diffs = [
                base_group_departures[index + 1] - base_group_departures[index]
                for index in range(len(base_group_departures) - 1)
            ]
            new_in_group_diffs = [
                new_group_departures[index + 1] - new_group_departures[index]
                for index in range(len(new_group_departures) - 1)
            ]
            if base_in_group_diffs != new_in_group_diffs:
                raise RuntimeError(
                    f"Traffic group {base_group_name!r}: within-group adjacent departure "
                    "differences differ from base N=5."
                )


def _assert_departure_shift_against_base_n5(
    shift: int,
    vehicle_specs: tuple[reference.VehicleSpec, ...],
) -> None:
    if len(vehicle_specs) != len(base_n5.VEHICLE_SPECS):
        raise RuntimeError("VEHICLE_SPECS length differs from base N=5 trial.")
    base_departures: list[int] = []
    new_departures: list[int] = []
    for new_spec, base_spec in zip(vehicle_specs, base_n5.VEHICLE_SPECS):
        if new_spec.vehicle_name != base_spec.vehicle_name:
            raise RuntimeError(
                f"Vehicle order/name mismatch: {new_spec.vehicle_name!r} vs "
                f"{base_spec.vehicle_name!r}."
            )
        if new_spec.departure_timestep != base_spec.departure_timestep + shift:
            raise RuntimeError(
                f"{new_spec.vehicle_name}: departure shift is not exactly +{shift} "
                f"({base_spec.departure_timestep} -> {new_spec.departure_timestep})."
            )
        reverted = replace(new_spec, departure_timestep=base_spec.departure_timestep)
        if reverted != base_spec:
            for field in fields(reference.VehicleSpec):
                if field.name == "departure_timestep":
                    continue
                if getattr(reverted, field.name) != getattr(base_spec, field.name):
                    raise RuntimeError(
                        f"{new_spec.vehicle_name}: field {field.name!r} differs from "
                        "base N=5 aside from departure_timestep."
                    )
            raise RuntimeError(
                f"{new_spec.vehicle_name}: VehicleSpec differs from base N=5 aside from "
                "departure_timestep."
            )
        base_departures.append(base_spec.departure_timestep)
        new_departures.append(new_spec.departure_timestep)
    if min(new_departures) != min(base_departures) + shift:
        raise RuntimeError("Minimum departure is not base minimum + shift.")
    if max(new_departures) != max(base_departures) + shift:
        raise RuntimeError("Maximum departure is not base maximum + shift.")
    base_adjacent_diffs = [
        base_departures[index + 1] - base_departures[index]
        for index in range(len(base_departures) - 1)
    ]
    new_adjacent_diffs = [
        new_departures[index + 1] - new_departures[index]
        for index in range(len(new_departures) - 1)
    ]
    if base_adjacent_diffs != new_adjacent_diffs:
        raise RuntimeError("Adjacent departure differences differ from base N=5 trial.")
    _assert_traffic_group_departure_structure(shift, vehicle_specs)


def _assert_vot_column_matches_base_n5(
    shift: int,
    vehicle_specs: tuple[reference.VehicleSpec, ...],
) -> None:
    true_vot = _true_vot_sequence()
    base_true_vot = base_n5._true_vot_sequence()
    if len(true_vot) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(
            f"Shift {shift} trial VOT column length is {len(true_vot)}, expected 600."
        )
    if len(base_true_vot) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("Base N=5 VOT column length is not 600.")
    if true_vot != base_true_vot:
        for index, (trial_vot, base_vot) in enumerate(zip(true_vot, base_true_vot)):
            if trial_vot != base_vot:
                trial_vehicle = vehicle_specs[index].vehicle_name
                base_vehicle = base_n5.VEHICLE_SPECS[index].vehicle_name
                raise RuntimeError(
                    f"Shift {shift} trial true VOT differs from base N=5 at index {index} "
                    f"({trial_vehicle!r} vs {base_vehicle!r})."
                )
        raise RuntimeError(
            f"Shift {shift} trial true VOT column differs from the base N=5 trial."
        )
    records = build_vehicle_vot_records(vehicle_specs, true_vot)
    for record, new_spec, base_spec, vot in zip(
        records, vehicle_specs, base_n5.VEHICLE_SPECS, true_vot
    ):
        if new_spec.vehicle_name != base_spec.vehicle_name:
            raise RuntimeError("VehicleSpec order differs from base N=5 at VOT alignment.")
        if record.departure_timestep != new_spec.departure_timestep:
            raise RuntimeError(
                f"VOT record departure differs from VehicleSpec for {record.vehicle_name}."
            )
        if record.departure_timestep != base_spec.departure_timestep + shift:
            raise RuntimeError(
                f"VOT record departure is not base+{shift} for {record.vehicle_name}."
            )
        if record.true_vot_per_second != vot:
            raise RuntimeError(f"True VOT differs for {record.vehicle_name}.")
        if record.participates_in_order_exchange != new_spec.participating:
            raise RuntimeError(
                f"VOT record participation differs from spec for {record.vehicle_name}."
            )
        if new_spec.participating:
            if record.declared_vot_per_second != record.true_vot_per_second:
                raise RuntimeError(
                    f"Participating declared VOT differs from true VOT for "
                    f"{record.vehicle_name}."
                )
        else:
            if record.declared_vot_per_second is not None:
                raise RuntimeError(
                    f"Nonparticipating declared VOT is not None for {record.vehicle_name}."
                )


def _collision_checks(config: ShiftTrialConfig) -> None:
    if config.scenario_name == reference.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with all-participating reference.")
    if config.world_display_name == reference.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with all-participating reference.")
    if config.trial_output_dir == reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with all-participating reference.")
    if config.trial_output_dir.name == reference.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with all-participating reference.")
    if config.trial_output_dir.name in reference.COLLIDING_TRIAL_OUTPUT_DIR_NAMES:
        raise RuntimeError("Output directory name collides with a known trial directory.")

    if config.scenario_name == nonparticipating_20_reference.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with N=10 nonparticipating trial.")
    if config.world_display_name == nonparticipating_20_reference.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with N=10 nonparticipating trial.")
    if config.trial_output_dir == nonparticipating_20_reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with N=10 nonparticipating trial.")
    if config.trial_output_dir.name == nonparticipating_20_reference.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with N=10 nonparticipating trial.")

    if config.scenario_name == base_n5.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with base N=5 trial.")
    if config.world_display_name == base_n5.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with base N=5 trial.")
    if config.trial_output_dir == base_n5.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with base N=5 trial.")
    if config.trial_output_dir.name == base_n5.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with base N=5 trial.")

    if config.scenario_name == departure_plus_1_reference.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with legacy departure_plus_1 trial.")
    if config.world_display_name == departure_plus_1_reference.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with legacy departure_plus_1 trial.")
    if config.trial_output_dir == departure_plus_1_reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with legacy departure_plus_1 trial.")
    if config.trial_output_dir.name == departure_plus_1_reference.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with legacy departure_plus_1 trial.")

    for other_shift in ALLOWED_DEPARTURE_SHIFTS:
        if other_shift == config.shift:
            continue
        other = shift_trial_config(other_shift)
        if config.scenario_name == other.scenario_name:
            raise RuntimeError(f"Scenario name collides with shift {other_shift} trial.")
        if config.world_display_name == other.world_display_name:
            raise RuntimeError(f"World display name collides with shift {other_shift} trial.")
        if config.trial_output_dir == other.trial_output_dir:
            raise RuntimeError(f"Output directory collides with shift {other_shift} trial.")
        if config.trial_output_dir_name == other.trial_output_dir_name:
            raise RuntimeError(
                f"Output directory name collides with shift {other_shift} trial."
            )


def _assert_static_validation_has_no_side_effects() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    static_function = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "validate_static_contract":
            static_function = node
    if static_function is None:
        raise RuntimeError("validate_static_contract is missing.")
    for node in ast.walk(static_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "exec_simulation":
                raise RuntimeError("Static validation must not call exec_simulation.")
            if node.func.attr == "install_real_world_spillback_observation":
                raise RuntimeError("Static validation must not install spillback hooks.")
            if node.func.attr == "build_tvt_mp_research_output":
                raise RuntimeError("Static validation must not build research output.")
            if node.func.attr == "mkdir":
                raise RuntimeError("Static validation must not create output directories.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "main":
                raise RuntimeError("Static validation must not call main().")


def _assert_spillback_verification_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    spillback_function = None
    main_function = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "verify_spillback_observation":
            spillback_function = node
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_function = node
    if spillback_function is None:
        raise RuntimeError(
            "Shift-specific verify_spillback_observation helper is missing."
        )
    if main_function is None:
        raise RuntimeError("main is missing.")

    uses_shift_expected_rows = False
    for node in ast.walk(spillback_function):
        if isinstance(node, ast.Attribute) and node.attr == "expected_world_t_after_sim":
            if isinstance(node.value, ast.Name) and node.value.id == "config":
                uses_shift_expected_rows = True
    if not uses_shift_expected_rows:
        raise RuntimeError(
            "verify_spillback_observation must use config.expected_world_t_after_sim "
            "as expected_rows_per_link."
        )

    calls_local_spillback_verify = False
    for node in ast.walk(main_function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "reference"
                and node.func.attr == "verify_spillback_observation"
            ):
                raise RuntimeError(
                    "main must not call reference.verify_spillback_observation."
                )
        if isinstance(node.func, ast.Name) and node.func.id == "verify_spillback_observation":
            calls_local_spillback_verify = True
    if not calls_local_spillback_verify:
        raise RuntimeError(
            "main must call verify_spillback_observation(rows, config)."
        )


def validate_static_contract(config: ShiftTrialConfig) -> None:
    shift = config.shift
    if shift not in ALLOWED_DEPARTURE_SHIFTS:
        raise RuntimeError(f"Shift must be in {ALLOWED_DEPARTURE_SHIFTS}; got {shift}.")
    if config.evaluation_end_timestep != ALIGNED_BASE_EVALUATION_END_TIMESTEP + shift:
        raise RuntimeError("EVALUATION_END_TIMESTEP is not 899 + shift.")
    if config.internal_tsize != ALIGNED_BASE_INTERNAL_TSIZE + shift:
        raise RuntimeError("INTERNAL_TSIZE is not 930 + shift.")
    if config.expected_world_t_after_sim != ALIGNED_BASE_EXPECTED_WORLD_T + shift:
        raise RuntimeError("EXPECTED_WORLD_T_AFTER_SIM is not 900 + shift.")
    if config.internal_tsize != (
        config.evaluation_end_timestep + reference.BASELINE_HORIZON_STEPS + 1
    ):
        raise RuntimeError("INTERNAL_TSIZE != evaluation_end + horizon + 1.")
    if base_n5.MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("Base N=5 candidate visit limit is not 5.")
    if MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("This trial MAX_CANDIDATE_VISIT_COUNT must be 5.")

    _collision_checks(config)

    vehicle_specs = build_vehicle_specs(shift)
    if len(vehicle_specs) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VEHICLE_SPECS length is not 600.")
    names = [spec.vehicle_name for spec in vehicle_specs]
    if len(set(names)) != len(names):
        raise RuntimeError("Vehicle names are not unique.")
    participating_count = sum(1 for spec in vehicle_specs if spec.participating)
    nonparticipating_count = sum(1 for spec in vehicle_specs if not spec.participating)
    if participating_count != EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError("Participating count is not 480.")
    if nonparticipating_count != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("Nonparticipating count is not 120.")

    _assert_departure_shift_against_base_n5(shift, vehicle_specs)
    _assert_vot_column_matches_base_n5(shift, vehicle_specs)

    world = build_world(config)
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("world.order_control_tvt_max_candidate_visit_count is not 5.")
    if world.name != config.world_display_name:
        raise RuntimeError("world.name does not match WORLD_DISPLAY_NAME.")
    if world.order_control_tvt_evaluation_end_timestep != config.evaluation_end_timestep:
        raise RuntimeError("world.order_control_tvt_evaluation_end_timestep mismatch.")
    if world.order_control_tvt_baseline_horizon_steps != reference.BASELINE_HORIZON_STEPS:
        raise RuntimeError("world.order_control_tvt_baseline_horizon_steps is not 30.")
    reference._assert_world_network_contract(world)

    _assert_spillback_verification_contract()
    _assert_static_validation_has_no_side_effects()


def refuse_existing_trial_output_directory(config: ShiftTrialConfig) -> None:
    if config.trial_output_dir.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {config.trial_output_dir}. "
            "This script does not delete or overwrite existing trial output."
        )
    if config.trial_output_dir == base_n5.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory equals base N=5 trial output.")
    if config.trial_output_dir == departure_plus_1_reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory equals legacy departure_plus_1 trial output.")


def build_world(config: ShiftTrialConfig) -> World:
    world = World(
        name=config.world_display_name,
        deltan=1,
        reaction_time=1,
        tmax=config.internal_tsize,
        random_seed=reference.TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
    )
    for node_name in reference.NODE_NAMES:
        x_coord, y_coord = reference.NODE_COORDINATES[node_name]
        world.addNode(node_name, x_coord, y_coord)

    for link_name, upstream, downstream in reference.LINK_SPECS:
        world.addLink(
            link_name,
            upstream,
            downstream,
            length=reference.LINK_LENGTH_M,
            free_flow_speed=reference.FREE_FLOW_SPEED_M_PER_S,
            number_of_lanes=reference.NUMBER_OF_LANES,
        )

    world.infer_order_control_eligible_nodes()
    world.set_order_control_for_nodes(
        list(reference.TVT_MP_NODE_NAMES),
        order_control_type="time_value",
        transaction_case=None,
    )
    world.set_order_control_clearance_timesteps(reference.CLEARANCE_TIMESTEPS)

    for node_name in reference.TVT_MP_NODE_NAMES:
        node = world.get_node(node_name)
        if node.order_control_clearance_timesteps != reference.CLEARANCE_TIMESTEPS:
            raise RuntimeError(
                f"{node_name} clearance is {node.order_control_clearance_timesteps!r}."
            )

    world.order_control_tvt_evaluation_end_timestep = config.evaluation_end_timestep
    world.order_control_tvt_baseline_horizon_steps = reference.BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    if world.order_control_tvt_max_candidate_visit_count != 5:
        raise RuntimeError("order_control_tvt_max_candidate_visit_count must be 5.")
    return world


def verify_evaluation_end(world: World, config: ShiftTrialConfig) -> dict:
    if world.T != config.expected_world_t_after_sim:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={config.expected_world_t_after_sim}, "
            f"got {world.T!r}."
        )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    for field_name in (
        "evaluation_end_unobserved_finalized_timestep",
        "trade_ex_post_evaluation_finalized_timestep",
        "individual_ex_post_evaluation_finalized_timestep",
    ):
        actual = getattr(registry, field_name)
        if actual != config.evaluation_end_timestep:
            raise RuntimeError(
                f"Registry {field_name} expected {config.evaluation_end_timestep}, "
                f"got {actual!r}."
            )
    return {"world_t": world.T, "world_t_ok": True}


def verify_world_candidate_limit_and_identity(
    world: World,
    config: ShiftTrialConfig,
) -> None:
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError("Max candidate visit count mismatch.")
    if world.name != config.world_display_name:
        raise RuntimeError("World display name does not match this shift trial.")
    if world.order_control_tvt_evaluation_end_timestep != config.evaluation_end_timestep:
        raise RuntimeError("Evaluation end on world does not match shift config.")


def verify_before_simulation(
    config: ShiftTrialConfig,
    vehicle_specs: tuple[reference.VehicleSpec, ...],
    vot_records: list[reference.VehicleVotRecord],
) -> None:
    _assert_departure_shift_against_base_n5(config.shift, vehicle_specs)
    _assert_vot_column_matches_base_n5(config.shift, vehicle_specs)
    true_vot = _true_vot_sequence()
    base_true_vot = base_n5._true_vot_sequence()
    if true_vot != base_true_vot:
        raise RuntimeError("VOT column differs from base N=5 before simulation.")


def verify_world_participation(
    world,
    vot_records: list[reference.VehicleVotRecord],
) -> None:
    vehicles = list(world.VEHICLES.values())
    if len(vehicles) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(f"World has {len(vehicles)} vehicles, expected 600.")
    record_by_name = {record.vehicle_name: record for record in vot_records}
    selected = set(NONPARTICIPATING_VEHICLE_NAMES)
    participating_names: list[str] = []
    nonparticipating_names: list[str] = []
    for vehicle in vehicles:
        record = record_by_name.get(vehicle.name)
        if record is None:
            raise RuntimeError(f"Missing VOT record for {vehicle.name}.")
        if vehicle.vot_true != record.true_vot_per_second:
            raise RuntimeError(f"{vehicle.name} true VOT does not match the VOT record.")
        if vehicle.participates_in_order_exchange is True:
            participating_names.append(vehicle.name)
            if vehicle.vot_declared != vehicle.vot_true:
                raise RuntimeError(f"{vehicle.name} declared VOT does not equal true VOT.")
        elif vehicle.participates_in_order_exchange is False:
            nonparticipating_names.append(vehicle.name)
            if vehicle.vot_declared is not None:
                raise RuntimeError(f"{vehicle.name} declared VOT is not None.")
        else:
            raise RuntimeError(
                f"{vehicle.name} participates_in_order_exchange is "
                f"{vehicle.participates_in_order_exchange!r}."
            )
    if len(participating_names) != EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError("World participating count is not 480.")
    if len(nonparticipating_names) != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("World nonparticipating count is not 120.")
    if set(nonparticipating_names) != selected:
        raise RuntimeError("World nonparticipating names differ from base N=5 set.")


def verify_spillback_observation(
    rows: list[dict],
    config: ShiftTrialConfig,
) -> None:
    expected_rows_per_link = config.expected_world_t_after_sim
    shift = config.shift
    grouped: dict[str, list[dict]] = {
        name: [] for name in reference.SPILLBACK_LINK_NAMES
    }
    for row in rows:
        link_name = row["link_name"]
        if link_name not in grouped:
            raise RuntimeError(
                f"shift {shift}: unknown spillback link {link_name!r}."
            )
        grouped[link_name].append(row)
    for link_name in reference.SPILLBACK_LINK_NAMES:
        link_rows = grouped[link_name]
        if len(link_rows) != expected_rows_per_link:
            raise RuntimeError(
                f"shift {shift}, Link {link_name}: expected {expected_rows_per_link} rows, "
                f"got {len(link_rows)}."
            )
        for index, row in enumerate(link_rows):
            if row["timestep"] != index:
                raise RuntimeError(
                    f"shift {shift}, Link {link_name} row index {index}: "
                    f"expected timestep {index}, got {row['timestep']!r}."
                )


def passage_comparison(bundle) -> dict:
    return base_n5.passage_comparison(bundle)


def write_vehicle_vot_csv(path: Path, vot_records: list[reference.VehicleVotRecord]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}.")
    selected = set(NONPARTICIPATING_VEHICLE_NAMES)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(VEHICLE_VOT_FIELDS))
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
                    "traffic_seed": reference.TRAFFIC_SEED,
                    "vot_seed": reference.VOT_SEED,
                    "nonparticipation_seed": NONPARTICIPATION_SEED,
                    "nonparticipation_selected": record.vehicle_name in selected,
                }
            )


def write_manifest_json(
    path: Path,
    config: ShiftTrialConfig,
    timing: reference.TimingRecord,
    world,
    generated_files: list[str],
    spillback_summary_by_link: dict[str, dict],
    completion: dict,
    ledger_summary: dict,
    visit_id_summary: dict,
    transactions_by_node: dict[str, int],
    passage_stats: dict,
    original_python_recursion_limit: int,
) -> None:
    ref_stats = reference.GENERATION_STATS
    manifest = {
        "schema_note": (
            "Four-cross grid medium nonparticipating 120/600, N=5 candidate limit, "
            f"aligned departure shift {config.shift}. Not a formal experiment schema."
        ),
        "run_type": "trial",
        "scenario_name": config.scenario_name,
        "world_display_name": config.world_display_name,
        "script_path": str(SCRIPT_PATH),
        "base_trial": "existing N=5 candidate-limit trial",
        "base_trial_scenario_name": base_n5.SCENARIO_NAME,
        "departure_shift_timesteps": config.shift,
        "aligned_base_evaluation_end_timestep": ALIGNED_BASE_EVALUATION_END_TIMESTEP,
        "actual_evaluation_end_timestep": config.evaluation_end_timestep,
        "evaluation_start_timestep": EVALUATION_START_TIMESTEP,
        "internal_tsize": config.internal_tsize,
        "expected_world_t_after_simulation": config.expected_world_t_after_sim,
        "comparison_alignment_note": "aligned old T = actual T - departure_shift_timesteps",
        "comparison_target": f"old T=392 vs shifted T={392 + config.shift}",
        "traffic_seed": reference.TRAFFIC_SEED,
        "vot_seed": reference.VOT_SEED,
        "nonparticipation_seed": NONPARTICIPATION_SEED,
        "vehicle_count": EXPECTED_TOTAL_VEHICLE_COUNT,
        "participating_count": EXPECTED_PARTICIPATING_COUNT,
        "nonparticipating_count": EXPECTED_NONPARTICIPATING_COUNT,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "baseline_horizon_steps": reference.BASELINE_HORIZON_STEPS,
        "clearance_timesteps": reference.CLEARANCE_TIMESTEPS,
        "base_vehicle_count": ref_stats.base_vehicle_count,
        "pulse_vehicle_count": ref_stats.pulse_vehicle_count,
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
        "world_copy_recursion_limit_during_trial": reference.WORLD_COPY_RECURSION_LIMIT,
        "original_python_recursion_limit": original_python_recursion_limit,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(
    path: Path,
    config: ShiftTrialConfig,
    world,
    bundle,
    completion: dict,
    spillback_summary_by_link: dict[str, dict],
    ledger_summary: dict,
    visit_id_summary: dict,
    transactions_by_node: dict[str, int],
    passage_stats: dict,
    generated_files: list[str],
) -> None:
    ref_stats = reference.GENERATION_STATS
    scenario_row = bundle.scenario[0]
    lines = [
        "TVT-MP four-cross nonparticipating 20% trial (N=5, aligned departure shift)",
        "=" * 55,
        f"Scenario name: {config.scenario_name}",
        f"World display name: {config.world_display_name}",
        f"Base trial: existing N=5 candidate-limit trial ({base_n5.SCENARIO_NAME})",
        f"Departure shift timesteps: {config.shift}",
        f"Aligned base evaluation end: T={ALIGNED_BASE_EVALUATION_END_TIMESTEP}",
        f"Actual evaluation end: T={config.evaluation_end_timestep}",
        f"Internal TSIZE: {config.internal_tsize}",
        f"Expected World.T after simulation: {config.expected_world_t_after_sim}",
        "Comparison alignment: aligned old T = actual T - departure_shift_timesteps",
        f"Comparison target: old T=392 vs shifted T={392 + config.shift}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Vehicles:",
        f"  total {EXPECTED_TOTAL_VEHICLE_COUNT}",
        f"  participating {EXPECTED_PARTICIPATING_COUNT}",
        f"  nonparticipating {EXPECTED_NONPARTICIPATING_COUNT}",
        f"  candidate limit {MAX_CANDIDATE_VISIT_COUNT}",
        f"  base demand {ref_stats.base_vehicle_count}, pulse {ref_stats.pulse_vehicle_count}",
        "",
        "Evaluation:",
        f"  start T={EVALUATION_START_TIMESTEP}",
        f"  end T={config.evaluation_end_timestep}",
        f"  baseline horizon {reference.BASELINE_HORIZON_STEPS}, "
        f"clearance {reference.CLEARANCE_TIMESTEPS}",
        "",
        "Established transactions:",
        f"  total {scenario_row.transaction_count}",
        f"  by node: {transactions_by_node}",
        "",
        "Trips:",
        f"  completed {completion['completed_trip_count']} / {EXPECTED_TOTAL_VEHICLE_COUNT}",
        f"  incomplete {completion['incomplete_vehicle_count']}",
        "",
        "Generated files:",
    ]
    for name in generated_files:
        lines.append(f"  {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_console_summary(
    config: ShiftTrialConfig,
    bundle,
    passage_stats: dict,
    transactions_by_node: dict[str, int],
    spillback_summary_by_link: dict[str, dict],
    timing: reference.TimingRecord,
    completion: dict,
) -> None:
    max_internal = 0
    for link_name in reference.SPILLBACK_LINK_NAMES:
        count = spillback_summary_by_link[link_name]["maximum_vehicle_count"]
        if count > max_internal:
            max_internal = count
    print()
    print(
        f"=== TVT-MP N=5 aligned departure shift {config.shift} trial ==="
    )
    print()
    print(f"Scenario: {config.scenario_name}")
    print(f"Departure shift: +{config.shift}")
    print(
        f"Evaluation: T={EVALUATION_START_TIMESTEP}..{config.evaluation_end_timestep}, "
        f"TSIZE {config.internal_tsize}, World ends T={config.expected_world_t_after_sim}"
    )
    print(f"Comparison target: old T=392 vs shifted T={392 + config.shift}")
    print(f"Transactions: {bundle.scenario[0].transaction_count}")
    print(
        f"Trips completed: {completion['completed_trip_count']} / "
        f"{EXPECTED_TOTAL_VEHICLE_COUNT}, incomplete "
        f"{completion['incomplete_vehicle_count']}"
    )
    print(f"Output directory: {config.trial_output_dir}")
    print(f"Timing total (s): {timing.script_total_s:.3f}")
    print()


def main(config: ShiftTrialConfig) -> int:
    script_start = time.perf_counter()
    timing = reference.TimingRecord()
    reference.SPILLBACK_TIMESTEP_ROWS.clear()
    original_python_recursion_limit = sys.getrecursionlimit()
    vehicle_specs = build_vehicle_specs(config.shift)
    try:
        if original_python_recursion_limit < reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(reference.WORLD_COPY_RECURSION_LIMIT)

        validate_static_contract(config)
        reference.ensure_trial_parent_directories()
        refuse_existing_trial_output_directory(config)

        vot_values = _true_vot_sequence()
        vot_records = build_vehicle_vot_records(vehicle_specs, vot_values)
        verify_before_simulation(config, vehicle_specs, vot_records)

        config.trial_output_dir.mkdir(parents=False, exist_ok=False)

        t0 = time.perf_counter()
        world = build_world(config)
        verify_world_candidate_limit_and_identity(world, config)
        reference._assert_world_network_contract(world)
        add_vehicles_to_world(world, vehicle_specs, vot_records)
        verify_world_participation(world, vot_records)
        timing.world_build_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        world.finalize_scenario()
        timing.finalize_s = time.perf_counter() - t0
        if world.TSIZE != config.internal_tsize:
            raise RuntimeError(
                f"Expected TSIZE=={config.internal_tsize}, got {world.TSIZE}."
            )
        if world.order_control_tvt_evaluation_end_timestep != config.evaluation_end_timestep:
            raise RuntimeError("Evaluation end was not kept before simulation.")

        t0 = time.perf_counter()
        reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            reference.restore_real_world_spillback_observation()
        timing.exec_simulation_s = time.perf_counter() - t0

        evaluation = verify_evaluation_end(world, config)
        if evaluation["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")

        completion = reference.collect_trip_completion(world)
        verify_spillback_observation(reference.SPILLBACK_TIMESTEP_ROWS, config)
        spillback_summary_by_link = reference.summarize_spillback_by_link(
            reference.SPILLBACK_TIMESTEP_ROWS,
            world,
        )
        ledger_summary = reference.collect_node_rank_ledger_summary(world)
        visit_id_summary = reference.collect_visit_id_summary(world)

        t0 = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, config.scenario_name)
        timing.research_build_s = time.perf_counter() - t0
        if bundle.scenario[0].scenario_name != config.scenario_name:
            raise RuntimeError("Research output scenario name does not match.")

        passage_stats = passage_comparison(bundle)
        transactions_by_node = reference.collect_transaction_counts_by_node(bundle)

        t0 = time.perf_counter()
        write_tvt_mp_research_output_csv(
            bundle, config.trial_output_dir, overwrite=False
        )
        timing.csv_write_s = time.perf_counter() - t0
        for name in reference.RESEARCH_CSV_NAMES:
            if not (config.trial_output_dir / name).is_file():
                raise RuntimeError(f"Missing research CSV {name}.")

        generated_files = list(reference.RESEARCH_CSV_NAMES) + list(AUXILIARY_FILE_NAMES)

        t0 = time.perf_counter()
        write_vehicle_vot_csv(config.trial_output_dir / "vehicle_vot.csv", vot_records)
        reference.write_spillback_summary_csv(
            config.trial_output_dir / reference.SPILLBACK_SUMMARY_CSV_NAME,
            spillback_summary_by_link,
        )
        timing.trial_aux_write_s = time.perf_counter() - t0
        timing.script_total_s = time.perf_counter() - script_start

        write_manifest_json(
            config.trial_output_dir / "manifest.json",
            config,
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
            config.trial_output_dir / "run_summary.txt",
            config,
            world,
            bundle,
            completion,
            spillback_summary_by_link,
            ledger_summary,
            visit_id_summary,
            transactions_by_node,
            passage_stats,
            generated_files,
        )
        expected_names = set(generated_files)
        for path in config.trial_output_dir.iterdir():
            if path.name not in expected_names:
                raise RuntimeError(f"Unexpected file in output directory: {path.name}.")

        print_console_summary(
            config,
            bundle,
            passage_stats,
            transactions_by_node,
            spillback_summary_by_link,
            timing,
            completion,
        )
        return 0
    finally:
        reference.restore_real_world_spillback_observation()
        sys.setrecursionlimit(original_python_recursion_limit)


if __name__ == "__main__":
    shift, static_only = parse_command_line(sys.argv[1:])
    trial_config = shift_trial_config(shift)
    if static_only:
        validate_static_contract(trial_config)
        print(
            f"Static contract validation passed (shift={shift}).",
            file=sys.stderr,
        )
        raise SystemExit(0)
    raise SystemExit(main(trial_config))
