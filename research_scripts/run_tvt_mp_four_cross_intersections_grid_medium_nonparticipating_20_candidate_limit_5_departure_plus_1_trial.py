"""
TVT-MP trial: N=5 candidate-limit nonparticipating 20% with uniform departure +1 timestep.

Independent trial derived from the completed existing N=5 candidate-limit trial
(run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial).

The only intentional traffic-condition difference is:

    departure_timestep_new = departure_timestep_existing_n5 + 1

for all 600 vehicles. Candidate Visit count upper bound remains N=5.

Purpose: investigate even arrival/passage timestep clustering around T=392 in the
existing N=5 trial (departure phase vs 2-timestep dynamics). This trial is the
prerequisite run before comparing old T=392 vs new T=393.

Does not modify production, the N=10 nonparticipating trial, the existing N=5 trial,
or existing trial output directories.
"""

from __future__ import annotations

import ast
import csv
import json
import sys
import time
from dataclasses import fields, replace
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
import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial as nonparticipating_20_reference
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

DEPARTURE_SHIFT_TIMESTEPS = 1

SCENARIO_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
    "departure_plus_1_600_vehicle_eval_900_timestep_trial"
)
WORLD_DISPLAY_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
    "departure_plus_1_600_vehicle_eval_900"
)
TRIAL_OUTPUT_DIR_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
    "departure_plus_1_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_initial"
)
TRIAL_OUTPUT_DIR = reference.TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME

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


def _build_vehicle_specs() -> tuple[reference.VehicleSpec, ...]:
    specs: list[reference.VehicleSpec] = []
    for spec in base_n5.VEHICLE_SPECS:
        specs.append(
            replace(
                spec,
                departure_timestep=spec.departure_timestep + DEPARTURE_SHIFT_TIMESTEPS,
            )
        )
    return tuple(specs)


VEHICLE_SPECS = _build_vehicle_specs()


def _true_vot_sequence() -> list[float]:
    """True VOT column matches the completed base N=5 trial (no re-seed or re-sample)."""
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


def _assert_departure_shift_against_base_n5() -> None:
    if len(VEHICLE_SPECS) != len(base_n5.VEHICLE_SPECS):
        raise RuntimeError("VEHICLE_SPECS length differs from base N=5 trial.")
    base_departures: list[int] = []
    new_departures: list[int] = []
    for new_spec, base_spec in zip(VEHICLE_SPECS, base_n5.VEHICLE_SPECS):
        if new_spec.vehicle_name != base_spec.vehicle_name:
            raise RuntimeError(
                f"Vehicle order/name mismatch at index: {new_spec.vehicle_name!r} "
                f"vs {base_spec.vehicle_name!r}."
            )
        if new_spec.departure_timestep != base_spec.departure_timestep + DEPARTURE_SHIFT_TIMESTEPS:
            raise RuntimeError(
                f"{new_spec.vehicle_name}: departure shift is not exactly "
                f"+{DEPARTURE_SHIFT_TIMESTEPS} "
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
                        f"base N=5 VehicleSpec aside from departure_timestep."
                    )
            raise RuntimeError(
                f"{new_spec.vehicle_name}: VehicleSpec differs from base N=5 aside from "
                "departure_timestep."
            )
        base_departures.append(base_spec.departure_timestep)
        new_departures.append(new_spec.departure_timestep)
    if min(new_departures) != min(base_departures) + DEPARTURE_SHIFT_TIMESTEPS:
        raise RuntimeError("Minimum departure is not base minimum + shift.")
    if max(new_departures) != max(base_departures) + DEPARTURE_SHIFT_TIMESTEPS:
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

    _assert_traffic_group_departure_structure()


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


def _assert_traffic_group_departure_structure() -> None:
    base_by_group = _vehicle_specs_by_traffic_group_preserving_order(base_n5.VEHICLE_SPECS)
    new_by_group = _vehicle_specs_by_traffic_group_preserving_order(VEHICLE_SPECS)
    base_group_names = [name for name, _ in base_by_group]
    new_group_names = [name for name, _ in new_by_group]
    if base_group_names != new_group_names:
        raise RuntimeError(
            "Traffic group set or first-appearance order differs between departure plus 1 trial "
            f"and base N=5 trial: {new_group_names!r} vs {base_group_names!r}."
        )
    for (base_group_name, base_group_specs), (new_group_name, new_group_specs) in zip(
        base_by_group, new_by_group
    ):
        if base_group_name != new_group_name:
            raise RuntimeError(
                "Traffic group name mismatch while comparing departure structure: "
                f"{new_group_name!r} vs {base_group_name!r}."
            )
        if len(new_group_specs) != len(base_group_specs):
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: vehicle count differs from base N=5 trial "
                f"({len(new_group_specs)} vs {len(base_group_specs)})."
            )
        base_names = [spec.vehicle_name for spec in base_group_specs]
        new_names = [spec.vehicle_name for spec in new_group_specs]
        if new_names != base_names:
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: vehicle name order differs from base N=5 trial."
            )
        base_group_departures = [spec.departure_timestep for spec in base_group_specs]
        new_group_departures = [spec.departure_timestep for spec in new_group_specs]
        for vehicle_name, base_dep, new_dep in zip(
            base_names, base_group_departures, new_group_departures
        ):
            if new_dep != base_dep + DEPARTURE_SHIFT_TIMESTEPS:
                raise RuntimeError(
                    f"Traffic group {base_group_name!r}, vehicle {vehicle_name!r}: departure is not "
                    f"base N=5 + {DEPARTURE_SHIFT_TIMESTEPS} ({base_dep} -> {new_dep})."
                )
        if new_group_departures[0] != base_group_departures[0] + DEPARTURE_SHIFT_TIMESTEPS:
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: first departure is not base N=5 first + shift."
            )
        if new_group_departures[-1] != base_group_departures[-1] + DEPARTURE_SHIFT_TIMESTEPS:
            raise RuntimeError(
                f"Traffic group {base_group_name!r}: last departure is not base N=5 last + shift."
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
                    f"Traffic group {base_group_name!r}: within-group adjacent departure differences "
                    "differ from base N=5 trial."
                )


def validate_static_contract() -> None:
    if DEPARTURE_SHIFT_TIMESTEPS != 1:
        raise RuntimeError("This trial requires DEPARTURE_SHIFT_TIMESTEPS == 1.")
    if len(base_n5.VEHICLE_SPECS) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("Base N=5 VEHICLE_SPECS length is not 600.")
    if base_n5.MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("Base N=5 trial candidate visit limit is not 5.")

    if reference.EVALUATION_START_TIMESTEP != 0:
        raise RuntimeError("Reference evaluation start is not T=0.")
    if reference.EVALUATION_END_TIMESTEP != 899:
        raise RuntimeError("Reference evaluation end is not T=899.")
    if reference.INTERNAL_TSIZE != 930:
        raise RuntimeError("Reference INTERNAL_TSIZE is not 930.")
    if reference.EXPECTED_WORLD_T_AFTER_SIM != 900:
        raise RuntimeError("Reference expected World.T after simulation is not 900.")
    if reference.BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("Reference baseline horizon is not 30.")
    if reference.CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Reference clearance is not 1.")

    if MAX_CANDIDATE_VISIT_COUNT != 5:
        raise RuntimeError("This trial MAX_CANDIDATE_VISIT_COUNT must be 5.")

    expected_scenario = (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "departure_plus_1_600_vehicle_eval_900_timestep_trial"
    )
    if SCENARIO_NAME != expected_scenario:
        raise RuntimeError("SCENARIO_NAME does not match the expected departure+1 trial string.")
    expected_world = (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "departure_plus_1_600_vehicle_eval_900"
    )
    if WORLD_DISPLAY_NAME != expected_world:
        raise RuntimeError("WORLD_DISPLAY_NAME does not match the expected departure+1 string.")
    expected_output_dir = (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "departure_plus_1_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_initial"
    )
    if TRIAL_OUTPUT_DIR_NAME != expected_output_dir:
        raise RuntimeError("TRIAL_OUTPUT_DIR_NAME does not match the expected departure+1 string.")

    _collision_checks()

    if len(VEHICLE_SPECS) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("New trial VEHICLE_SPECS length is not 600.")
    names = [spec.vehicle_name for spec in VEHICLE_SPECS]
    if len(set(names)) != len(names):
        raise RuntimeError("Vehicle names are not unique.")
    participating_count = sum(1 for spec in VEHICLE_SPECS if spec.participating)
    nonparticipating_count = sum(1 for spec in VEHICLE_SPECS if not spec.participating)
    if participating_count != EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError("Participating count is not 480.")
    if nonparticipating_count != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("Nonparticipating count is not 120.")

    _assert_departure_shift_against_base_n5()

    true_vot = _true_vot_sequence()
    base_true_vot = base_n5._true_vot_sequence()
    if len(true_vot) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(
            f"Departure plus 1 trial VOT column length is {len(true_vot)}, expected 600."
        )
    if len(base_true_vot) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(
            f"Base N=5 trial VOT column length is {len(base_true_vot)}, expected 600."
        )
    if true_vot != base_true_vot:
        for index, (trial_vot, base_vot) in enumerate(zip(true_vot, base_true_vot)):
            if trial_vot != base_vot:
                trial_vehicle = VEHICLE_SPECS[index].vehicle_name
                base_vehicle = base_n5.VEHICLE_SPECS[index].vehicle_name
                raise RuntimeError(
                    "Departure plus 1 trial true VOT column differs from base N=5 trial at "
                    f"index {index} (trial vehicle {trial_vehicle!r}, base vehicle "
                    f"{base_vehicle!r}): trial VOT {trial_vot!r}, base N=5 VOT {base_vot!r}."
                )
        raise RuntimeError(
            "Departure plus 1 trial true VOT column differs from the base N=5 trial."
        )
    for index, (new_spec, base_spec, trial_vot, base_vot) in enumerate(
        zip(VEHICLE_SPECS, base_n5.VEHICLE_SPECS, true_vot, base_true_vot)
    ):
        if new_spec.vehicle_name != base_spec.vehicle_name:
            raise RuntimeError(
                "VehicleSpec order differs from base N=5 at VOT index "
                f"{index}: {new_spec.vehicle_name!r} vs {base_spec.vehicle_name!r}."
            )
        if trial_vot != base_vot:
            raise RuntimeError(
                "Departure plus 1 trial VOT value differs from base N=5 at index "
                f"{index} for {new_spec.vehicle_name!r}."
            )
    records = build_vehicle_vot_records(VEHICLE_SPECS, true_vot)
    if len(records) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VOT record count is not 600.")
    for record, new_spec, base_spec, vot in zip(
        records, VEHICLE_SPECS, base_n5.VEHICLE_SPECS, true_vot
    ):
        if record.departure_timestep != new_spec.departure_timestep:
            raise RuntimeError(
                f"VOT record departure differs from VehicleSpec for {record.vehicle_name}."
            )
        if record.departure_timestep != base_spec.departure_timestep + DEPARTURE_SHIFT_TIMESTEPS:
            raise RuntimeError(
                f"VOT record departure is not base+{DEPARTURE_SHIFT_TIMESTEPS} for "
                f"{record.vehicle_name}."
            )
        if record.true_vot_per_second != vot:
            raise RuntimeError(f"True VOT differs for {record.vehicle_name}.")
        if record.participates_in_order_exchange != new_spec.participating:
            raise RuntimeError(
                f"VOT record participation flag differs from spec for {record.vehicle_name}."
            )
        if new_spec.participating:
            if record.declared_vot_per_second != record.true_vot_per_second:
                raise RuntimeError(
                    f"Participating declared VOT differs from true VOT for {record.vehicle_name}."
                )
        else:
            if record.declared_vot_per_second is not None:
                raise RuntimeError(
                    f"Nonparticipating declared VOT is not None for {record.vehicle_name}."
                )

    world = build_world()
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError(
            "Static contract: world.order_control_tvt_max_candidate_visit_count is not 5."
        )
    if world.name != WORLD_DISPLAY_NAME:
        raise RuntimeError("Static contract: world.name does not match WORLD_DISPLAY_NAME.")
    reference._assert_world_network_contract(world)

    _assert_static_validation_has_no_side_effects()


def _collision_checks() -> None:
    if SCENARIO_NAME == reference.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with the all-participating reference trial.")
    if WORLD_DISPLAY_NAME == reference.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with the all-participating reference trial.")
    if TRIAL_OUTPUT_DIR == reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with the all-participating reference trial.")
    if TRIAL_OUTPUT_DIR.name == reference.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with the all-participating reference trial.")
    if TRIAL_OUTPUT_DIR.name in reference.COLLIDING_TRIAL_OUTPUT_DIR_NAMES:
        raise RuntimeError("Output directory name collides with a known trial output directory.")

    if SCENARIO_NAME == nonparticipating_20_reference.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with the N=10 nonparticipating trial.")
    if WORLD_DISPLAY_NAME == nonparticipating_20_reference.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with the N=10 nonparticipating trial.")
    if TRIAL_OUTPUT_DIR == nonparticipating_20_reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with the N=10 nonparticipating trial.")
    if TRIAL_OUTPUT_DIR.name == nonparticipating_20_reference.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with the N=10 nonparticipating trial.")

    if SCENARIO_NAME == base_n5.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with the existing N=5 trial.")
    if WORLD_DISPLAY_NAME == base_n5.WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name collides with the existing N=5 trial.")
    if TRIAL_OUTPUT_DIR == base_n5.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with the existing N=5 trial.")
    if TRIAL_OUTPUT_DIR.name == base_n5.TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory name collides with the existing N=5 trial.")


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


def refuse_existing_trial_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "This script does not delete or overwrite existing trial output."
        )
    if TRIAL_OUTPUT_DIR == nonparticipating_20_reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError(
            "Trial output directory path equals the N=10 nonparticipating trial output."
        )
    if TRIAL_OUTPUT_DIR == base_n5.TRIAL_OUTPUT_DIR:
        raise RuntimeError(
            "Trial output directory path equals the existing N=5 trial output."
        )


def build_world():
    world = reference.build_world_and_network()
    world.name = WORLD_DISPLAY_NAME
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    if world.order_control_tvt_max_candidate_visit_count != 5:
        raise RuntimeError(
            "order_control_tvt_max_candidate_visit_count must be 5 after assignment."
        )
    return world


def verify_world_candidate_limit_and_identity(world) -> None:
    if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
        raise RuntimeError(
            f"Expected max candidate visit count {MAX_CANDIDATE_VISIT_COUNT}, "
            f"got {world.order_control_tvt_max_candidate_visit_count!r}."
        )
    if world.name != WORLD_DISPLAY_NAME:
        raise RuntimeError("World display name does not match this trial.")
    if TRIAL_OUTPUT_DIR == nonparticipating_20_reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory must differ from the N=10 nonparticipating trial.")
    if TRIAL_OUTPUT_DIR == base_n5.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory must differ from the existing N=5 trial.")


def verify_departure_shift_before_simulation() -> None:
    _assert_departure_shift_against_base_n5()


def verify_world_participation(
    world,
    vot_records: list[reference.VehicleVotRecord],
) -> None:
    vehicles = list(world.VEHICLES.values())
    if len(vehicles) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(f"World has {len(vehicles)} vehicles, expected 600.")
    record_by_name = {record.vehicle_name: record for record in vot_records}
    if len(record_by_name) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VOT record name map is not 600 entries.")
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
                raise RuntimeError(
                    f"{vehicle.name} declared VOT does not equal true VOT."
                )
            if record.participates_in_order_exchange is not True:
                raise RuntimeError(f"{vehicle.name} VOT record is not participating.")
        elif vehicle.participates_in_order_exchange is False:
            nonparticipating_names.append(vehicle.name)
            if vehicle.vot_declared is not None:
                raise RuntimeError(f"{vehicle.name} declared VOT is not None.")
            if record.participates_in_order_exchange is not False:
                raise RuntimeError(f"{vehicle.name} VOT record is not nonparticipating.")
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
        raise RuntimeError("World nonparticipating names differ from the base N=5 set.")


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
            "Four-cross grid medium nonparticipating 120/600 variant, "
            f"max_candidate_visit_count={MAX_CANDIDATE_VISIT_COUNT}, "
            f"departure_shift_timesteps={DEPARTURE_SHIFT_TIMESTEPS}. "
            "Not a formal experiment schema."
        ),
        "run_type": "trial",
        "scenario_name": SCENARIO_NAME,
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
        "base_trial": "existing N=5 candidate-limit trial",
        "base_trial_scenario_name": base_n5.SCENARIO_NAME,
        "base_trial_output_directory_name": base_n5.TRIAL_OUTPUT_DIR_NAME,
        "departure_shift_timesteps": DEPARTURE_SHIFT_TIMESTEPS,
        "comparison_target": "old T=392 vs new T=393",
        "reference_scenario_name": reference.SCENARIO_NAME,
        "reference_output_directory_name": reference.TRIAL_OUTPUT_DIR.name,
        "traffic_seed": reference.TRAFFIC_SEED,
        "vot_seed": reference.VOT_SEED,
        "nonparticipation_seed": NONPARTICIPATION_SEED,
        "vehicle_count": EXPECTED_TOTAL_VEHICLE_COUNT,
        "extraction_population_count": EXPECTED_TOTAL_VEHICLE_COUNT,
        "nonparticipating_extraction_count": NONPARTICIPATING_VEHICLE_COUNT,
        "participating_count": EXPECTED_PARTICIPATING_COUNT,
        "nonparticipating_count": EXPECTED_NONPARTICIPATING_COUNT,
        "nonparticipating_rate": "120/600",
        "nonparticipating_vehicle_names": list(NONPARTICIPATING_VEHICLE_NAMES),
        "nonparticipating_vehicle_name_hash": NONPARTICIPATING_NAME_HASH,
        "evaluation_start_timestep": reference.EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": reference.EVALUATION_END_TIMESTEP,
        "internal_tsize": reference.INTERNAL_TSIZE,
        "expected_world_t_after_simulation": reference.EXPECTED_WORLD_T_AFTER_SIM,
        "baseline_horizon_steps": reference.BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
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
        "expected_tvt_mp_driver_calls": reference.EXPECTED_DRIVER_CALL_COUNT,
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
        "TVT-MP four-cross grid medium nonparticipating 20 percent trial "
        "(candidate limit 5, departure +1 timestep)",
        "=" * 55,
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"Base trial: existing N=5 candidate-limit trial ({base_n5.SCENARIO_NAME})",
        f"Departure shift timesteps: {DEPARTURE_SHIFT_TIMESTEPS}",
        f"Comparison target: old T=392 vs new T=393",
        f"Reference scenario: {reference.SCENARIO_NAME}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Seeds:",
        f"  traffic seed: {reference.TRAFFIC_SEED}",
        f"  VOT seed: {reference.VOT_SEED}",
        f"  nonparticipation seed: {NONPARTICIPATION_SEED}",
        "",
        "Vehicles:",
        f"  total {EXPECTED_TOTAL_VEHICLE_COUNT}",
        f"  participating {EXPECTED_PARTICIPATING_COUNT}",
        f"  nonparticipating {EXPECTED_NONPARTICIPATING_COUNT}",
        f"  nonparticipating rate: 120/600",
        f"  nonparticipating name hash: {NONPARTICIPATING_NAME_HASH}",
        f"  base demand {ref_stats.base_vehicle_count}, pulse {ref_stats.pulse_vehicle_count}",
        "",
        "Evaluation:",
        f"  T={reference.EVALUATION_START_TIMESTEP}..{reference.EVALUATION_END_TIMESTEP}",
        f"  internal TSIZE {reference.INTERNAL_TSIZE}",
        f"  World ends T={reference.EXPECTED_WORLD_T_AFTER_SIM}",
        f"  baseline horizon {reference.BASELINE_HORIZON_STEPS}, "
        f"candidate limit {MAX_CANDIDATE_VISIT_COUNT}, "
        f"clearance {reference.CLEARANCE_TIMESTEPS}",
        "",
        "Established transactions:",
        f"  total {scenario_row.transaction_count}",
        f"  by node: {transactions_by_node}",
        f"  buyer visits (recount) {passage_stats['buyer_visit_count']}",
        f"  seller visits (recount) {passage_stats['seller_visit_count']}",
        f"  nonparticipating visits (recount) {passage_stats['nonparticipating_visit_count']}",
        "",
        "Candidate P vs Actual P (trade-scope parties):",
        f"  both observed {passage_stats['both_passage_observed_count']}",
        f"  candidate equals actual {passage_stats['candidate_equals_actual_count']}",
        f"  candidate differs {passage_stats['candidate_differs_from_actual_count']}",
        f"  actual unobserved {passage_stats['actual_unobserved_count']}",
        "",
        "Node rank ledger (assigned_rank, end of evaluation):",
    ]
    for node_name in reference.TVT_MP_NODE_NAMES:
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
    for link_name in reference.SPILLBACK_LINK_NAMES:
        summary = spillback_summary_by_link[link_name]
        lines.append(
            f"  {link_name}: max vehicles {summary['maximum_vehicle_count']}, "
            f"entrance blocked timesteps {summary['entrance_blocked_timestep_count']}, "
            f"vehicles at evaluation end {summary['vehicle_count_at_evaluation_end']}"
        )
    lines.extend(
        [
            "",
            "Trips:",
            f"  completed {completion['completed_trip_count']} / {EXPECTED_TOTAL_VEHICLE_COUNT}",
            f"  incomplete {completion['incomplete_vehicle_count']}",
            "",
            "Nonparticipating vehicle names:",
        ]
    )
    for name in NONPARTICIPATING_VEHICLE_NAMES:
        lines.append(f"  {name}")
    lines.append("")
    lines.append("Generated files:")
    for name in generated_files:
        lines.append(f"  {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_console_summary(
    bundle,
    passage_stats: dict,
    transactions_by_node: dict[str, int],
    spillback_summary_by_link: dict[str, dict],
    timing: reference.TimingRecord,
    output_dir: Path,
) -> None:
    ref_stats = reference.GENERATION_STATS
    max_internal = 0
    for link_name in reference.SPILLBACK_LINK_NAMES:
        count = spillback_summary_by_link[link_name]["maximum_vehicle_count"]
        if count > max_internal:
            max_internal = count
    print()
    print(
        "=== TVT-MP four-cross grid medium nonparticipating 20% trial "
        "(N=5, departure +1) ==="
    )
    print()
    print(f"Scenario: {SCENARIO_NAME}")
    print(f"Base trial: {base_n5.SCENARIO_NAME}")
    print(f"Departure shift: +{DEPARTURE_SHIFT_TIMESTEPS} timestep")
    print(f"Comparison target: old T=392 vs new T=393")
    print(f"Participating: {EXPECTED_PARTICIPATING_COUNT}")
    print(f"Nonparticipating: {EXPECTED_NONPARTICIPATING_COUNT}")
    print(
        f"Network: {reference.NODE_COUNT} nodes, {reference.LINK_COUNT} links, "
        f"4 TVT-MP intersections"
    )
    print(
        f"Vehicles: base {ref_stats.base_vehicle_count}, pulse {ref_stats.pulse_vehicle_count}, "
        f"total {EXPECTED_TOTAL_VEHICLE_COUNT}"
    )
    print(
        f"Evaluation: T={reference.EVALUATION_START_TIMESTEP}.."
        f"{reference.EVALUATION_END_TIMESTEP}, TSIZE {reference.INTERNAL_TSIZE}"
    )
    print(f"Max candidate visit count (trade_scope): {MAX_CANDIDATE_VISIT_COUNT}")
    print(f"Transactions: {bundle.scenario[0].transaction_count}")
    print(f"Transactions by node: {transactions_by_node}")
    print(
        "Passage CP=AP: "
        f"{passage_stats['candidate_equals_actual_count']} / "
        f"{passage_stats['both_passage_observed_count']} observed"
    )
    print(f"Nonparticipating visits: {passage_stats['nonparticipating_visit_count']}")
    print(f"Internal link max vehicles (peak): {max_internal}")
    print(f"Timing total (s): {timing.script_total_s:.3f}")
    print(f"Output directory: {output_dir}")
    print()


def main() -> int:
    script_start = time.perf_counter()
    timing = reference.TimingRecord()
    reference.SPILLBACK_TIMESTEP_ROWS.clear()
    original_python_recursion_limit = sys.getrecursionlimit()
    try:
        if original_python_recursion_limit < reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(reference.WORLD_COPY_RECURSION_LIMIT)

        validate_static_contract()
        reference.ensure_trial_parent_directories()
        refuse_existing_trial_output_directory()
        verify_departure_shift_before_simulation()
        TRIAL_OUTPUT_DIR.mkdir(parents=False, exist_ok=False)

        vot_values = _true_vot_sequence()
        vot_records = build_vehicle_vot_records(VEHICLE_SPECS, vot_values)

        t0 = time.perf_counter()
        world = build_world()
        verify_world_candidate_limit_and_identity(world)
        reference._assert_world_network_contract(world)
        add_vehicles_to_world(world, VEHICLE_SPECS, vot_records)
        verify_world_participation(world, vot_records)
        timing.world_build_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        world.finalize_scenario()
        timing.finalize_s = time.perf_counter() - t0
        if world.TSIZE != reference.INTERNAL_TSIZE:
            raise RuntimeError(
                f"Expected TSIZE=={reference.INTERNAL_TSIZE}, got {world.TSIZE}."
            )
        if world.name != WORLD_DISPLAY_NAME:
            raise RuntimeError("World display name was not kept.")
        if world.order_control_tvt_max_candidate_visit_count != MAX_CANDIDATE_VISIT_COUNT:
            raise RuntimeError("Max candidate visit count was not kept before simulation.")

        t0 = time.perf_counter()
        reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            reference.restore_real_world_spillback_observation()
        timing.exec_simulation_s = time.perf_counter() - t0

        if world.T != reference.EXPECTED_WORLD_T_AFTER_SIM:
            raise RuntimeError(
                f"Expected World.T=={reference.EXPECTED_WORLD_T_AFTER_SIM} after simulation, "
                f"got {world.T}."
            )

        evaluation = reference.verify_evaluation_end(world)
        if evaluation["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")

        completion = reference.collect_trip_completion(world)
        reference.verify_spillback_observation(reference.SPILLBACK_TIMESTEP_ROWS)
        spillback_summary_by_link = reference.summarize_spillback_by_link(
            reference.SPILLBACK_TIMESTEP_ROWS,
            world,
        )
        ledger_summary = reference.collect_node_rank_ledger_summary(world)
        visit_id_summary = reference.collect_visit_id_summary(world)

        t0 = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        timing.research_build_s = time.perf_counter() - t0
        if bundle.scenario[0].scenario_name != SCENARIO_NAME:
            raise RuntimeError("Research output scenario name does not match.")

        passage_stats = passage_comparison(bundle)
        transactions_by_node = reference.collect_transaction_counts_by_node(bundle)
        if passage_stats["buyer_visit_count"] != passage_stats["scenario_buyer_visit_count"]:
            raise RuntimeError("Buyer visit recount does not match the scenario row.")
        if passage_stats["seller_visit_count"] != passage_stats["scenario_seller_visit_count"]:
            raise RuntimeError("Seller visit recount does not match the scenario row.")
        if (
            passage_stats["nonparticipating_visit_count"]
            != passage_stats["scenario_nonparticipating_visit_count"]
        ):
            raise RuntimeError(
                "Nonparticipating visit recount does not match the scenario row."
            )

        t0 = time.perf_counter()
        write_tvt_mp_research_output_csv(bundle, TRIAL_OUTPUT_DIR, overwrite=False)
        timing.csv_write_s = time.perf_counter() - t0
        for name in reference.RESEARCH_CSV_NAMES:
            if not (TRIAL_OUTPUT_DIR / name).is_file():
                raise RuntimeError(f"Missing research CSV {name}.")

        generated_files = list(reference.RESEARCH_CSV_NAMES) + list(AUXILIARY_FILE_NAMES)

        t0 = time.perf_counter()
        write_vehicle_vot_csv(TRIAL_OUTPUT_DIR / "vehicle_vot.csv", vot_records)
        reference.write_spillback_summary_csv(
            TRIAL_OUTPUT_DIR / reference.SPILLBACK_SUMMARY_CSV_NAME,
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
            generated_files,
        )
        expected_names = set(generated_files)
        for path in TRIAL_OUTPUT_DIR.iterdir():
            if path.name not in expected_names:
                raise RuntimeError(f"Unexpected file in output directory: {path.name}.")

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
        reference.restore_real_world_spillback_observation()
        sys.setrecursionlimit(original_python_recursion_limit)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("Unexpected CLI arguments; use no arguments or --static-validate-only.")
    if len(sys.argv) == 2:
        if sys.argv[1] == "--static-validate-only":
            validate_static_contract()
            print("Static contract validation passed.", file=sys.stderr)
            raise SystemExit(0)
        raise SystemExit(f"Unknown CLI option: {sys.argv[1]!r}")
    raise SystemExit(main())
