"""
TVT-MP trial: the extended-south-pulse network with 110 nonparticipating vehicles.

Traffic, OD, departure, route generation, and true VOT match the all-participating
reference trial. Only the participation attribute of a fixed 110-vehicle subset
changes. This script does not modify production code or the reference trial.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import random
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_trial as reference
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)


SCENARIO_NAME = (
    "tvt_mp_two_cross_intersections_downstream_spillback_"
    "extended_south_pulse_nonparticipating_20_trial"
)
WORLD_DISPLAY_NAME = (
    "tvt_mp_two_cross_intersections_downstream_spillback_"
    "extended_south_pulse_nonparticipating_20"
)
TRIAL_OUTPUT_DIR_NAME = (
    "tvt_mp_two_cross_intersections_downstream_spillback_"
    "extended_south_pulse_seed_1_nonparticipation_seed_3_initial"
)
TRIAL_OUTPUT_DIR = reference.TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME

NONPARTICIPATION_SEED = 3
NONPARTICIPATING_VEHICLE_COUNT = 110
EXPECTED_TOTAL_VEHICLE_COUNT = 551
EXPECTED_PARTICIPATING_COUNT = 441
EXPECTED_NONPARTICIPATING_COUNT = 110
NONPARTICIPATING_NAME_HASH = (
    "f91065b60888f0c2d9a8bf1a60efad5d40828546445bd0909dde25897c1ca111"
)

# Population order of reference.VEHICLE_SPECS. Do not regenerate this tuple.
NONPARTICIPATING_VEHICLE_NAMES: tuple[str, ...] = (
    "veh_es_4",
    "veh_es_5",
    "veh_ee_5",
    "veh_en_6",
    "veh_es_8",
    "veh_ee_8",
    "veh_es_11",
    "veh_ee_11",
    "veh_ws_1",
    "veh_es_12",
    "veh_ws_2",
    "veh_es_14",
    "veh_en_16",
    "veh_wn_7",
    "veh_es_18",
    "veh_wn_8",
    "veh_es_19",
    "veh_ee_21",
    "veh_wn_12",
    "veh_es_26",
    "veh_es_28",
    "veh_ee_30",
    "veh_ws_12",
    "veh_ee_34",
    "veh_wn_24",
    "veh_es_35",
    "veh_ws_13",
    "veh_en_36",
    "veh_ee_36",
    "veh_wn_27",
    "veh_ee_38",
    "veh_wn_28",
    "veh_ee_40",
    "veh_ee_41",
    "veh_ws_16",
    "veh_ee_42",
    "veh_ee_43",
    "veh_en_44",
    "veh_es_47",
    "veh_ws_19",
    "veh_en_48",
    "veh_ee_50",
    "veh_en_51",
    "veh_ee_51",
    "veh_wn_42",
    "veh_wn_43",
    "veh_en_57",
    "veh_ee_57",
    "veh_es_58",
    "veh_en_59",
    "veh_es_59",
    "veh_wn_51",
    "veh_ws_26",
    "veh_en_63",
    "veh_es_63",
    "veh_en_65",
    "veh_ee_65",
    "veh_ws_28",
    "veh_en_67",
    "veh_en_69",
    "veh_es_69",
    "veh_ee_69",
    "veh_wn_60",
    "veh_en_71",
    "veh_wn_62",
    "veh_en_73",
    "veh_es_73",
    "veh_en_74",
    "veh_es_76",
    "veh_en_77",
    "veh_wn_68",
    "veh_ee_80",
    "veh_ws_36",
    "veh_ee_83",
    "veh_wn_73",
    "veh_ee_85",
    "veh_ws_38",
    "veh_ee_87",
    "veh_es_88",
    "veh_wn_80",
    "veh_wn_81",
    "veh_es_92",
    "veh_en_93",
    "veh_en_94",
    "veh_ee_94",
    "veh_es_95",
    "veh_wn_88",
    "veh_en_99",
    "veh_en_100",
    "veh_wn_92",
    "veh_wn_93",
    "veh_wn_94",
    "veh_wn_98",
    "veh_wn_104",
    "veh_wn_107",
    "veh_wn_109",
    "veh_ws_55",
    "veh_wn_113",
    "veh_ws_59",
    "veh_wn_121",
    "veh_ws_61",
    "veh_ws_62",
    "veh_wn_124",
    "veh_ws_63",
    "veh_wn_137",
    "veh_wn_138",
    "veh_wn_139",
    "veh_wn_143",
    "veh_wn_150",
    "veh_ws_80",
)

VEHICLE_VOT_FIELDS = (
    "vehicle_name",
    "origin",
    "destination",
    "departure_timestep",
    "participates_in_order_exchange",
    "true_vot_per_second",
    "declared_vot_per_second",
    "traffic_seed",
    "east_destination_seed",
    "west_north_destination_seed",
    "vot_seed",
    "nonparticipation_seed",
    "nonparticipation_selected",
)

AUXILIARY_FILE_NAMES = (
    "vehicle_vot.csv",
    reference.SPILLBACK_CSV_NAME,
    "manifest.json",
    "run_summary.txt",
)


def _population_names() -> tuple[str, ...]:
    return tuple(spec.vehicle_name for spec in reference.VEHICLE_SPECS)


def _hash_names(names: tuple[str, ...]) -> str:
    payload = "\n".join(names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sample_nonparticipating_names() -> tuple[str, ...]:
    population = _population_names()
    sampled = set(
        random.Random(NONPARTICIPATION_SEED).sample(
            list(population),
            NONPARTICIPATING_VEHICLE_COUNT,
        )
    )
    return tuple(name for name in population if name in sampled)


def _build_vehicle_specs():
    selected = set(NONPARTICIPATING_VEHICLE_NAMES)
    specs = []
    for spec in reference.VEHICLE_SPECS:
        if spec.vehicle_name in selected:
            specs.append(replace(spec, participating=False))
        else:
            specs.append(spec)
    return tuple(specs)


VEHICLE_SPECS = _build_vehicle_specs()


def _identity_tuple(spec) -> tuple:
    return (
        spec.vehicle_name,
        spec.orig,
        spec.dest,
        spec.departure_timestep,
        spec.traffic_group,
        spec.planned_movement,
    )


def _true_vot_sequence() -> list[float]:
    return reference.generate_vehicle_vots(
        np.random.default_rng(reference.VOT_SEED),
        EXPECTED_TOTAL_VEHICLE_COUNT,
    )


def validate_static_contract() -> None:
    if SCRIPT_PATH.name != (
        "run_tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20_trial.py"
    ):
        raise RuntimeError("Unexpected script name.")
    if SCENARIO_NAME != (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20_trial"
    ):
        raise RuntimeError("Unexpected scenario name.")
    if WORLD_DISPLAY_NAME != (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20"
    ):
        raise RuntimeError("Unexpected world display name.")
    if TRIAL_OUTPUT_DIR.name != TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Unexpected output directory name.")
    if TRIAL_OUTPUT_DIR == reference.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory collides with the reference trial.")
    if TRIAL_OUTPUT_DIR.name == reference.TRIAL_OUTPUT_DIR.name:
        raise RuntimeError("Output directory name collides with the reference trial.")
    if TRIAL_OUTPUT_DIR.name in reference.KNOWN_OTHER_TRIAL_DIR_NAMES:
        raise RuntimeError("Output directory collides with a known trial.")
    if NONPARTICIPATION_SEED != 3:
        raise RuntimeError("NONPARTICIPATION_SEED must be 3.")
    if EXPECTED_TOTAL_VEHICLE_COUNT != 551:
        raise RuntimeError("Vehicle total must be 551.")
    if EXPECTED_PARTICIPATING_COUNT != 441:
        raise RuntimeError("Participating count must be 441.")
    if EXPECTED_NONPARTICIPATING_COUNT != 110:
        raise RuntimeError("Nonparticipating count must be 110.")
    if (
        EXPECTED_PARTICIPATING_COUNT + EXPECTED_NONPARTICIPATING_COUNT
        != EXPECTED_TOTAL_VEHICLE_COUNT
    ):
        raise RuntimeError("Participation counts do not sum to 551.")
    if NONPARTICIPATING_VEHICLE_COUNT != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("Extraction count must be 110.")
    rate = EXPECTED_NONPARTICIPATING_COUNT / EXPECTED_TOTAL_VEHICLE_COUNT
    if rate != 110 / 551:
        raise RuntimeError("Nonparticipation rate must be 110/551.")

    population = _population_names()
    if len(population) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("Reference population is not 551 vehicles.")
    if len(set(population)) != len(population):
        raise RuntimeError("Reference population has duplicate vehicle names.")
    if len(NONPARTICIPATING_VEHICLE_NAMES) != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Embedded nonparticipating list is not 110 names.")
    if len(set(NONPARTICIPATING_VEHICLE_NAMES)) != len(NONPARTICIPATING_VEHICLE_NAMES):
        raise RuntimeError("Embedded nonparticipating list has duplicates.")
    unknown = set(NONPARTICIPATING_VEHICLE_NAMES) - set(population)
    if len(unknown) != 0:
        raise RuntimeError(f"Embedded names are outside the reference population: {unknown!r}.")
    if _hash_names(NONPARTICIPATING_VEHICLE_NAMES) != NONPARTICIPATING_NAME_HASH:
        raise RuntimeError("Embedded nonparticipating name hash does not match.")
    resampled = _sample_nonparticipating_names()
    if resampled != NONPARTICIPATING_VEHICLE_NAMES:
        raise RuntimeError(
            "random.Random(3).sample does not match the embedded 110 names. "
            "The embedded list is not updated automatically."
        )

    if len(VEHICLE_SPECS) != len(reference.VEHICLE_SPECS):
        raise RuntimeError("VEHICLE_SPECS length differs from the reference.")
    selected = set(NONPARTICIPATING_VEHICLE_NAMES)
    participating_count = 0
    nonparticipating_count = 0
    for spec, reference_spec in zip(VEHICLE_SPECS, reference.VEHICLE_SPECS):
        if _identity_tuple(spec) != _identity_tuple(reference_spec):
            raise RuntimeError(
                f"{spec.vehicle_name} identity differs from the reference VehicleSpec."
            )
        if spec.vehicle_name in selected:
            if spec.participating is not False:
                raise RuntimeError(f"{spec.vehicle_name} must be nonparticipating.")
            nonparticipating_count += 1
        else:
            if spec.participating is not True:
                raise RuntimeError(f"{spec.vehicle_name} must stay participating.")
            participating_count += 1
        if spec.participating != reference_spec.participating and spec.vehicle_name not in selected:
            raise RuntimeError(
                f"{spec.vehicle_name} participation differs outside the selected set."
            )
    if participating_count != EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError("Built participating count is not 441.")
    if nonparticipating_count != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("Built nonparticipating count is not 110.")

    if reference.TRAFFIC_SEED != 0:
        raise RuntimeError("Reference traffic seed is not 0.")
    if reference.EAST_DESTINATION_SEED != 1:
        raise RuntimeError("Reference east destination seed is not 1.")
    if reference.WEST_NORTH_DESTINATION_SEED != 2:
        raise RuntimeError("Reference west-north destination seed is not 2.")
    if reference.VOT_SEED != 1:
        raise RuntimeError("Reference VOT seed is not 1.")
    if reference.EVALUATION_START_TIMESTEP != 0 or reference.EVALUATION_END_TIMESTEP != 599:
        raise RuntimeError("Reference evaluation window is not T=0..599.")
    if reference.INTERNAL_TSIZE != 630:
        raise RuntimeError("Reference INTERNAL_TSIZE is not 630.")
    if reference.BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("Reference baseline horizon is not 30.")
    if reference.MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Reference candidate visit limit is not 10.")
    if reference.CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Reference clearance is not 1.")
    if reference.NODE_COUNT != 8 or reference.LINK_COUNT != 14:
        raise RuntimeError("Reference network size changed.")
    if reference.EXPECTED_TOTAL_VEHICLE_COUNT != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("Reference vehicle total is not 551.")

    true_vot = _true_vot_sequence()
    reference_true_vot = _true_vot_sequence()
    if true_vot != reference_true_vot:
        raise RuntimeError("True VOT sequence is not deterministic.")
    if len(true_vot) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("True VOT sequence length is not 551.")
    records = reference.build_vehicle_vot_records(VEHICLE_SPECS, true_vot)
    reference_records = reference.build_vehicle_vot_records(
        reference.VEHICLE_SPECS,
        reference_true_vot,
    )
    if len(records) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VOT record count is not 551.")
    for record, reference_record, spec in zip(records, reference_records, VEHICLE_SPECS):
        if record.vehicle_name != reference_record.vehicle_name:
            raise RuntimeError("VOT record order differs from the reference.")
        if record.true_vot_per_second != reference_record.true_vot_per_second:
            raise RuntimeError(f"True VOT differs for {record.vehicle_name}.")
        if spec.participating:
            if record.declared_vot_per_second != record.true_vot_per_second:
                raise RuntimeError(
                    f"Participating declared VOT differs from true VOT for {record.vehicle_name}."
                )
            if record.participates_in_order_exchange is not True:
                raise RuntimeError(f"{record.vehicle_name} is not marked participating.")
        else:
            if record.declared_vot_per_second is not None:
                raise RuntimeError(
                    f"Nonparticipating declared VOT is not None for {record.vehicle_name}."
                )
            if record.participates_in_order_exchange is not False:
                raise RuntimeError(f"{record.vehicle_name} is not marked nonparticipating.")

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
            if node.func.attr == "validate_static_contract" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "reference":
                    raise RuntimeError(
                        "This trial must not call reference.validate_static_contract."
                    )


def refuse_existing_trial_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "This script does not delete or overwrite existing trial output."
        )


def build_world():
    world = reference.build_world_and_network()
    world.name = WORLD_DISPLAY_NAME
    return world


def verify_world_participation(world) -> None:
    vehicles = list(world.VEHICLES.values())
    if len(vehicles) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError(f"World has {len(vehicles)} vehicles, expected 551.")
    selected = set(NONPARTICIPATING_VEHICLE_NAMES)
    participating_names = []
    nonparticipating_names = []
    for vehicle in vehicles:
        if vehicle.participates_in_order_exchange is True:
            participating_names.append(vehicle.name)
            if vehicle.vot_declared != vehicle.vot_true:
                raise RuntimeError(
                    f"{vehicle.name} declared VOT does not equal true VOT."
                )
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
        raise RuntimeError("World participating count is not 441.")
    if len(nonparticipating_names) != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("World nonparticipating count is not 110.")
    if set(nonparticipating_names) != selected:
        raise RuntimeError("World nonparticipating names differ from the embedded set.")


def _passage_comparison(bundle) -> dict:
    both_observed = 0
    equal_count = 0
    unequal_count = 0
    differences = []
    actual_unobserved = 0
    buyer_count = 0
    seller_count = 0
    nonparticipating_count = 0
    for visit in bundle.visits:
        if visit.role == "buyer":
            buyer_count += 1
        elif visit.role == "seller":
            seller_count += 1
        elif visit.role == "nonparticipating":
            nonparticipating_count += 1
        if visit.actual_passage_timestep is None:
            actual_unobserved += 1
        if (
            visit.candidate_passage_timestep is not None
            and visit.actual_passage_timestep is not None
        ):
            both_observed += 1
            difference = visit.candidate_passage_timestep - visit.actual_passage_timestep
            differences.append(difference)
            if difference == 0:
                equal_count += 1
            else:
                unequal_count += 1
    if len(differences) == 0:
        minimum_difference = None
        maximum_difference = None
    else:
        minimum_difference = min(differences)
        maximum_difference = max(differences)
    predicted_available = 0
    actual_available = 0
    for vehicle_row in bundle.vehicles:
        if vehicle_row.nonparticipating_predicted_external_effect_total is not None:
            predicted_available += 1
        if vehicle_row.nonparticipating_actual_external_effect_total is not None:
            actual_available += 1
    scenario = bundle.scenario[0]
    return {
        "transaction_count": scenario.transaction_count,
        "buyer_visit_count": buyer_count,
        "seller_visit_count": seller_count,
        "nonparticipating_visit_count": nonparticipating_count,
        "scenario_buyer_visit_count": scenario.buyer_visit_count,
        "scenario_seller_visit_count": scenario.seller_visit_count,
        "scenario_nonparticipating_visit_count": scenario.nonparticipating_visit_count,
        "both_passage_observed_count": both_observed,
        "candidate_equals_actual_count": equal_count,
        "candidate_differs_from_actual_count": unequal_count,
        "candidate_minus_actual_minimum": minimum_difference,
        "candidate_minus_actual_maximum": maximum_difference,
        "actual_unobserved_count": actual_unobserved,
        "scenario_actual_unobserved_count": scenario.actual_unobserved_count,
        "nonparticipating_predicted_external_effect_available_vehicle_count": (
            predicted_available
        ),
        "nonparticipating_actual_external_effect_available_vehicle_count": (
            actual_available
        ),
        "scenario_nonparticipating_predicted_external_effect_total": (
            scenario.nonparticipating_predicted_external_effect_total
        ),
        "scenario_nonparticipating_actual_external_effect_total": (
            scenario.nonparticipating_actual_external_effect_total
        ),
    }


def write_vehicle_vot_csv(path: Path, vot_records) -> None:
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
                    "east_destination_seed": reference.EAST_DESTINATION_SEED,
                    "west_north_destination_seed": reference.WEST_NORTH_DESTINATION_SEED,
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
    spillback_summary: dict,
    completion: dict,
    comparison: dict,
    original_python_recursion_limit: int,
) -> None:
    manifest = {
        "schema_note": (
            "Nonparticipating 110/551 variant of the extended-south-pulse trial. "
            "Not a formal experiment schema."
        ),
        "run_type": "trial",
        "scenario_name": SCENARIO_NAME,
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
        "reference_scenario_name": reference.SCENARIO_NAME,
        "reference_output_directory_name": reference.TRIAL_OUTPUT_DIR.name,
        "traffic_seed": reference.TRAFFIC_SEED,
        "east_destination_seed": reference.EAST_DESTINATION_SEED,
        "west_north_destination_seed": reference.WEST_NORTH_DESTINATION_SEED,
        "vot_seed": reference.VOT_SEED,
        "nonparticipation_seed": NONPARTICIPATION_SEED,
        "vehicle_count": EXPECTED_TOTAL_VEHICLE_COUNT,
        "extraction_population_count": EXPECTED_TOTAL_VEHICLE_COUNT,
        "nonparticipating_extraction_count": NONPARTICIPATING_VEHICLE_COUNT,
        "participating_count": EXPECTED_PARTICIPATING_COUNT,
        "nonparticipating_count": EXPECTED_NONPARTICIPATING_COUNT,
        "nonparticipating_rate": "110/551",
        "nonparticipating_vehicle_names": list(NONPARTICIPATING_VEHICLE_NAMES),
        "nonparticipating_vehicle_name_hash": NONPARTICIPATING_NAME_HASH,
        "evaluation_start_timestep": reference.EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": reference.EVALUATION_END_TIMESTEP,
        "internal_tsize": reference.INTERNAL_TSIZE,
        "baseline_horizon_steps": reference.BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": reference.MAX_CANDIDATE_VISIT_COUNT,
        "clearance_timesteps": reference.CLEARANCE_TIMESTEPS,
        "generated_files": generated_files,
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
        "spillback_summary": spillback_summary,
        "comparison": comparison,
        "world_copy_recursion_limit_during_trial": reference.WORLD_COPY_RECURSION_LIMIT,
        "original_python_recursion_limit": original_python_recursion_limit,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def write_run_summary_txt(
    path: Path,
    world,
    comparison: dict,
    completion: dict,
    spillback_summary: dict,
    generated_files: list[str],
) -> None:
    lines = [
        "TVT-MP extended-south-pulse nonparticipating 20 percent trial",
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"Reference scenario: {reference.SCENARIO_NAME}",
        f"Reference output directory: {reference.TRIAL_OUTPUT_DIR.name}",
        f"World.T after exec_simulation: {world.T}",
        f"traffic seed: {reference.TRAFFIC_SEED}",
        f"east destination seed: {reference.EAST_DESTINATION_SEED}",
        f"west-north destination seed: {reference.WEST_NORTH_DESTINATION_SEED}",
        f"VOT seed: {reference.VOT_SEED}",
        f"nonparticipation seed: {NONPARTICIPATION_SEED}",
        f"vehicles: {EXPECTED_TOTAL_VEHICLE_COUNT}",
        f"extraction population: {EXPECTED_TOTAL_VEHICLE_COUNT}",
        f"participating: {EXPECTED_PARTICIPATING_COUNT}",
        f"nonparticipating: {EXPECTED_NONPARTICIPATING_COUNT}",
        "nonparticipating rate: 110/551",
        f"nonparticipating name hash: {NONPARTICIPATING_NAME_HASH}",
        "evaluation T=0..599",
        "internal TSIZE 630",
        "baseline horizon 30",
        "candidate visit limit 10",
        "clearance 1",
        f"completed trips: {completion['completed_trip_count']}",
        f"incomplete vehicles: {completion['incomplete_vehicle_count']}",
        "spillback maximum vehicle count: "
        f"{spillback_summary['maximum_vehicle_count_on_spillback_link']}",
        "spillback entrance-blocked timesteps: "
        f"{spillback_summary['entrance_blocked_timestep_count']}",
        f"transaction count: {comparison['transaction_count']}",
        f"buyer visits: {comparison['buyer_visit_count']}",
        f"seller visits: {comparison['seller_visit_count']}",
        f"nonparticipating visits: {comparison['nonparticipating_visit_count']}",
        "both passage observed: "
        f"{comparison['both_passage_observed_count']}",
        "candidate equals actual: "
        f"{comparison['candidate_equals_actual_count']}",
        "candidate differs from actual: "
        f"{comparison['candidate_differs_from_actual_count']}",
        "candidate minus actual minimum: "
        f"{comparison['candidate_minus_actual_minimum']}",
        "candidate minus actual maximum: "
        f"{comparison['candidate_minus_actual_maximum']}",
        f"actual unobserved visits: {comparison['actual_unobserved_count']}",
        "nonparticipating predicted external effect available vehicles: "
        f"{comparison['nonparticipating_predicted_external_effect_available_vehicle_count']}",
        "nonparticipating actual external effect available vehicles: "
        f"{comparison['nonparticipating_actual_external_effect_available_vehicle_count']}",
        "nonparticipating vehicle names:",
    ]
    for name in NONPARTICIPATING_VEHICLE_NAMES:
        lines.append(f"  {name}")
    lines.append("generated files:")
    for name in generated_files:
        lines.append(f"  {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_console_summary(comparison: dict, spillback_summary: dict, output_dir: Path) -> None:
    print(f"scenario={SCENARIO_NAME}")
    print(f"participating={EXPECTED_PARTICIPATING_COUNT}")
    print(f"nonparticipating={EXPECTED_NONPARTICIPATING_COUNT}")
    print(f"transactions={comparison['transaction_count']}")
    print(f"buyer_visits={comparison['buyer_visit_count']}")
    print(f"seller_visits={comparison['seller_visit_count']}")
    print(f"nonparticipating_visits={comparison['nonparticipating_visit_count']}")
    print(f"both_observed={comparison['both_passage_observed_count']}")
    print(f"candidate_equals_actual={comparison['candidate_equals_actual_count']}")
    print(f"candidate_differs_from_actual={comparison['candidate_differs_from_actual_count']}")
    print(f"candidate_minus_actual_min={comparison['candidate_minus_actual_minimum']}")
    print(f"candidate_minus_actual_max={comparison['candidate_minus_actual_maximum']}")
    print(f"actual_unobserved={comparison['actual_unobserved_count']}")
    print(
        "nonparticipating_predicted_external_effect_available_vehicles="
        f"{comparison['nonparticipating_predicted_external_effect_available_vehicle_count']}"
    )
    print(
        "nonparticipating_actual_external_effect_available_vehicles="
        f"{comparison['nonparticipating_actual_external_effect_available_vehicle_count']}"
    )
    print(
        "spillback_max_vehicles="
        f"{spillback_summary['maximum_vehicle_count_on_spillback_link']}"
    )
    print(
        "entrance_blocked_timesteps="
        f"{spillback_summary['entrance_blocked_timestep_count']}"
    )
    print(f"output_directory={output_dir}")


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
        TRIAL_OUTPUT_DIR.mkdir(parents=False, exist_ok=False)

        vot_values = _true_vot_sequence()
        vot_records = reference.build_vehicle_vot_records(VEHICLE_SPECS, vot_values)

        t0 = time.perf_counter()
        world = build_world()
        reference.add_vehicles_to_world(world, VEHICLE_SPECS, vot_records)
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

        t0 = time.perf_counter()
        reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            reference.restore_real_world_spillback_observation()
        timing.exec_simulation_s = time.perf_counter() - t0

        evaluation = reference.verify_evaluation_end(world)
        if evaluation["world_t_ok"] is not True:
            raise RuntimeError("Evaluation-end check did not pass.")
        verify_world_participation(world)

        completion = reference.collect_trip_completion(world)
        spillback_rows = list(reference.SPILLBACK_TIMESTEP_ROWS)
        spillback_summary = reference.summarize_spillback_rows(spillback_rows)
        reference.verify_spillback_observation(spillback_rows, spillback_summary)

        t0 = time.perf_counter()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        timing.research_build_s = time.perf_counter() - t0
        if bundle.scenario[0].scenario_name != SCENARIO_NAME:
            raise RuntimeError("Research output scenario name does not match.")

        t0 = time.perf_counter()
        write_tvt_mp_research_output_csv(bundle, TRIAL_OUTPUT_DIR, overwrite=False)
        timing.csv_write_s = time.perf_counter() - t0
        for name in reference.RESEARCH_CSV_NAMES:
            if not (TRIAL_OUTPUT_DIR / name).is_file():
                raise RuntimeError(f"Missing research CSV {name}.")

        comparison = _passage_comparison(bundle)
        if comparison["buyer_visit_count"] != comparison["scenario_buyer_visit_count"]:
            raise RuntimeError("Buyer visit recount does not match the scenario row.")
        if comparison["seller_visit_count"] != comparison["scenario_seller_visit_count"]:
            raise RuntimeError("Seller visit recount does not match the scenario row.")
        if (
            comparison["nonparticipating_visit_count"]
            != comparison["scenario_nonparticipating_visit_count"]
        ):
            raise RuntimeError(
                "Nonparticipating visit recount does not match the scenario row."
            )

        generated_files = list(reference.RESEARCH_CSV_NAMES) + list(AUXILIARY_FILE_NAMES)
        t0 = time.perf_counter()
        write_vehicle_vot_csv(TRIAL_OUTPUT_DIR / "vehicle_vot.csv", vot_records)
        reference.write_spillback_csv(
            TRIAL_OUTPUT_DIR / reference.SPILLBACK_CSV_NAME,
            spillback_rows,
        )
        timing.trial_aux_write_s = time.perf_counter() - t0
        timing.script_total_s = time.perf_counter() - script_start
        write_manifest_json(
            TRIAL_OUTPUT_DIR / "manifest.json",
            timing,
            world,
            generated_files,
            spillback_summary,
            completion,
            comparison,
            original_python_recursion_limit,
        )
        write_run_summary_txt(
            TRIAL_OUTPUT_DIR / "run_summary.txt",
            world,
            comparison,
            completion,
            spillback_summary,
            generated_files,
        )
        expected_names = set(generated_files)
        for path in TRIAL_OUTPUT_DIR.iterdir():
            if path.name not in expected_names:
                raise RuntimeError(f"Unexpected file in output directory: {path.name}.")
        print_console_summary(comparison, spillback_summary, TRIAL_OUTPUT_DIR)
        return 0
    finally:
        reference.restore_real_world_spillback_observation()
        sys.setrecursionlimit(original_python_recursion_limit)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
        print("Static contract validation passed.")
    else:
        raise SystemExit(main())
