"""
TVT-MP trial: four-cross grid medium network with 120 nonparticipating vehicles.

Traffic, OD, departures, routes, true VOT, and evaluation match the all-participating
600-vehicle reference trial. Only participation attributes of a fixed 120-vehicle subset
change. This script does not modify production code or the reference trial.
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

import run_tvt_mp_four_cross_intersections_grid_medium_all_participating_trial as reference
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)


SCENARIO_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
    "600_vehicle_eval_900_timestep_trial"
)
WORLD_DISPLAY_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
    "600_vehicle_eval_900"
)
TRIAL_OUTPUT_DIR_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
    "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_initial"
)
TRIAL_OUTPUT_DIR = reference.TRIAL_PARENT / TRIAL_OUTPUT_DIR_NAME

NONPARTICIPATION_SEED = 3
NONPARTICIPATING_VEHICLE_COUNT = 120
EXPECTED_TOTAL_VEHICLE_COUNT = 600
EXPECTED_PARTICIPATING_COUNT = 480
EXPECTED_NONPARTICIPATING_COUNT = 120
NONPARTICIPATING_NAME_HASH = (
    "3377404c888b45a5000ac08224f8da4830d9e4fa4889e9455871ecb2d3ef7602"
)

# Population order of reference.VEHICLE_SPECS. Do not regenerate this tuple at runtime.
NONPARTICIPATING_VEHICLE_NAMES: tuple[str, ...] = (
    "veh_sw_nw_base_001",
    "veh_ne_ws_base_002",
    "veh_se_ne_base_002",
    "veh_en_sw_base_003",
    "veh_es_ws_base_003",
    "veh_wn_se_base_003",
    "veh_es_ws_base_004",
    "veh_ne_wn_base_004",
    "veh_sw_es_base_004",
    "veh_ne_ws_base_005",
    "veh_se_ne_base_005",
    "veh_sw_es_base_005",
    "veh_ne_wn_base_006",
    "veh_nw_sw_base_007",
    "veh_se_ne_base_007",
    "veh_sw_nw_base_007",
    "veh_wn_en_base_007",
    "veh_en_sw_base_008",
    "veh_wn_en_base_008",
    "veh_wn_se_base_008",
    "veh_en_sw_base_010",
    "veh_wn_se_base_010",
    "veh_sw_es_base_011",
    "veh_en_sw_base_012",
    "veh_es_ws_base_013",
    "veh_sw_nw_base_013",
    "veh_ne_ws_base_014",
    "veh_nw_sw_base_014",
    "veh_sw_nw_base_014",
    "veh_wn_se_base_014",
    "veh_wn_se_base_015",
    "veh_nw_sw_base_016",
    "veh_se_ne_base_016",
    "veh_en_sw_base_017",
    "veh_ne_ws_base_017",
    "veh_sw_nw_base_017",
    "veh_ne_ws_base_018",
    "veh_nw_sw_base_019",
    "veh_ne_wn_base_020",
    "veh_ne_ws_base_020",
    "veh_sw_es_base_020",
    "veh_sw_nw_base_020",
    "veh_ne_wn_base_021",
    "veh_wn_en_base_021",
    "veh_sw_es_base_022",
    "veh_ne_wn_base_023",
    "veh_se_ne_base_024",
    "veh_sw_nw_base_024",
    "veh_wn_se_base_024",
    "veh_es_ws_base_025",
    "veh_ne_ws_base_025",
    "veh_nw_sw_base_027",
    "veh_se_ne_base_027",
    "veh_sw_es_base_027",
    "veh_ne_ws_base_028",
    "veh_se_ne_base_028",
    "veh_se_ne_base_029",
    "veh_sw_es_base_029",
    "veh_es_ws_base_030",
    "veh_en_sw_base_031",
    "veh_nw_sw_base_031",
    "veh_wn_en_base_031",
    "veh_ne_wn_base_032",
    "veh_sw_nw_base_032",
    "veh_wn_se_base_033",
    "veh_nw_sw_base_034",
    "veh_wn_en_base_034",
    "veh_nw_sw_base_035",
    "veh_wn_en_base_035",
    "veh_ne_wn_base_036",
    "veh_ne_ws_base_036",
    "veh_wn_se_base_036",
    "veh_nw_sw_base_038",
    "veh_wn_en_base_038",
    "veh_sw_es_base_039",
    "veh_se_ne_base_040",
    "veh_sw_es_base_040",
    "veh_wn_se_base_040",
    "veh_nw_sw_base_041",
    "veh_sw_es_base_041",
    "veh_se_ne_base_042",
    "veh_sw_nw_base_042",
    "veh_en_sw_base_043",
    "veh_se_ne_base_043",
    "veh_es_ws_base_044",
    "veh_sw_nw_base_044",
    "veh_es_ws_base_045",
    "veh_ne_ws_base_045",
    "veh_nw_sw_base_045",
    "veh_se_ne_base_045",
    "veh_sw_es_base_045",
    "veh_se_ne_base_046",
    "veh_wn_se_base_046",
    "veh_en_sw_base_049",
    "veh_es_ws_base_049",
    "veh_nw_sw_base_049",
    "veh_se_ne_base_049",
    "veh_sw_nw_base_049",
    "veh_en_sw_base_050",
    "veh_ne_ws_base_050",
    "veh_se_ne_base_050",
    "veh_sw_nw_base_050",
    "veh_wn_en_pulse_001",
    "veh_nw_sw_pulse_004",
    "veh_nw_sw_pulse_009",
    "veh_wn_en_pulse_009",
    "veh_wn_en_pulse_010",
    "veh_wn_en_pulse_018",
    "veh_wn_en_pulse_023",
    "veh_nw_sw_pulse_024",
    "veh_wn_en_pulse_027",
    "veh_wn_en_pulse_029",
    "veh_wn_en_pulse_031",
    "veh_nw_sw_pulse_032",
    "veh_nw_sw_pulse_033",
    "veh_wn_en_pulse_034",
    "veh_nw_sw_pulse_037",
    "veh_nw_sw_pulse_041",
    "veh_wn_en_pulse_041",
    "veh_nw_sw_pulse_048",
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
    "vot_seed",
    "nonparticipation_seed",
    "nonparticipation_selected",
)

AUXILIARY_FILE_NAMES = (
    "vehicle_vot.csv",
    reference.SPILLBACK_SUMMARY_CSV_NAME,
    "manifest.json",
    "run_summary.txt",
)


def _population_names() -> tuple[str, ...]:
    return tuple(spec.vehicle_name for spec in reference.VEHICLE_SPECS)


def _hash_names(names: tuple[str, ...]) -> str:
    payload = "\n".join(names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sample_nonparticipating_names() -> tuple[str, ...]:
    population = list(_population_names())
    sampled = set(
        random.Random(NONPARTICIPATION_SEED).sample(
            population,
            NONPARTICIPATING_VEHICLE_COUNT,
        )
    )
    return tuple(name for name in population if name in sampled)


def _build_vehicle_specs() -> tuple[reference.VehicleSpec, ...]:
    selected = set(NONPARTICIPATING_VEHICLE_NAMES)
    specs: list[reference.VehicleSpec] = []
    for spec in reference.VEHICLE_SPECS:
        if spec.vehicle_name in selected:
            specs.append(replace(spec, participating=False))
        else:
            specs.append(spec)
    return tuple(specs)


VEHICLE_SPECS = _build_vehicle_specs()


def _identity_tuple(spec: reference.VehicleSpec) -> tuple:
    return (
        spec.vehicle_name,
        spec.orig,
        spec.dest,
        spec.departure_timestep,
        spec.traffic_group,
        spec.od_abbrev,
        spec.demand_kind,
    )


def _true_vot_sequence() -> list[float]:
    return reference.generate_vehicle_vots(
        np.random.default_rng(reference.VOT_SEED),
        EXPECTED_TOTAL_VEHICLE_COUNT,
    )


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


def validate_static_contract() -> None:
    if reference.SCENARIO_NAME != (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900_timestep_trial"
    ):
        raise RuntimeError("Reference scenario name is not the expected all-participating trial.")
    if reference.WORLD_DISPLAY_NAME != (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900"
    ):
        raise RuntimeError("Reference world display name is not the expected all-participating trial.")
    if reference.TRIAL_OUTPUT_DIR_NAME != (
        "tvt_mp_four_cross_intersections_grid_medium_all_participating_"
        "600_vehicle_eval_900_timestep_seed_1_initial"
    ):
        raise RuntimeError("Reference trial output directory name is not the expected value.")
    if reference.TRAFFIC_SEED != 0:
        raise RuntimeError("Reference traffic seed is not 0.")
    if reference.VOT_SEED != 1:
        raise RuntimeError("Reference VOT seed is not 1.")
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
    if reference.MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Reference candidate visit limit is not 10.")
    if reference.NODE_COUNT != 12:
        raise RuntimeError("Reference node count is not 12.")
    if reference.LINK_COUNT != 24:
        raise RuntimeError("Reference link count is not 24.")
    if len(reference.TVT_MP_NODE_NAMES) != 4:
        raise RuntimeError("Reference TVT-MP node count is not 4.")
    if reference.EXPECTED_TOTAL_VEHICLE_COUNT != 600:
        raise RuntimeError("Reference vehicle total is not 600.")
    ref_stats = reference.GENERATION_STATS
    if ref_stats.base_vehicle_count != 500 or ref_stats.pulse_vehicle_count != 100:
        raise RuntimeError("Reference generation stats base/pulse counts are not 500/100.")
    if len(reference.VEHICLE_SPECS) != 600:
        raise RuntimeError("Reference VEHICLE_SPECS length is not 600.")
    ref_names = [spec.vehicle_name for spec in reference.VEHICLE_SPECS]
    if len(set(ref_names)) != len(ref_names):
        raise RuntimeError("Reference vehicle names are not unique.")
    for spec in reference.VEHICLE_SPECS:
        if spec.participating is not True:
            raise RuntimeError("Reference vehicles must all be participating.")

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

    population = _population_names()
    if len(NONPARTICIPATING_VEHICLE_NAMES) != NONPARTICIPATING_VEHICLE_COUNT:
        raise RuntimeError("Embedded nonparticipating list is not 120 names.")
    if len(set(NONPARTICIPATING_VEHICLE_NAMES)) != len(NONPARTICIPATING_VEHICLE_NAMES):
        raise RuntimeError("Embedded nonparticipating list has duplicates.")
    unknown = set(NONPARTICIPATING_VEHICLE_NAMES) - set(population)
    if len(unknown) != 0:
        raise RuntimeError(f"Embedded names are outside the reference population: {unknown!r}.")
    if _hash_names(NONPARTICIPATING_VEHICLE_NAMES) != NONPARTICIPATING_NAME_HASH:
        raise RuntimeError("Embedded nonparticipating name hash does not match.")
    if _sample_nonparticipating_names() != NONPARTICIPATING_VEHICLE_NAMES:
        raise RuntimeError(
            "random.Random(3).sample does not match the embedded 120 names. "
            "The embedded list is not updated automatically."
        )

    if len(VEHICLE_SPECS) != 600:
        raise RuntimeError("New trial VEHICLE_SPECS length is not 600.")
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
    if participating_count != EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError("Built participating count is not 480.")
    if nonparticipating_count != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError("Built nonparticipating count is not 120.")

    true_vot = _true_vot_sequence()
    reference_true_vot = _true_vot_sequence()
    if true_vot != reference_true_vot:
        raise RuntimeError("True VOT sequence is not deterministic or differs from reference.")
    if len(true_vot) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("True VOT sequence length is not 600.")
    records = build_vehicle_vot_records(VEHICLE_SPECS, true_vot)
    if len(records) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VOT record count is not 600.")
    for record, spec, vot in zip(records, VEHICLE_SPECS, true_vot):
        if record.true_vot_per_second != vot:
            raise RuntimeError(f"True VOT differs for {record.vehicle_name}.")
        if record.participates_in_order_exchange != spec.participating:
            raise RuntimeError(
                f"VOT record participation flag differs from spec for {record.vehicle_name}."
            )
        if spec.participating:
            if record.declared_vot_per_second != record.true_vot_per_second:
                raise RuntimeError(
                    f"Participating declared VOT differs from true VOT for {record.vehicle_name}."
                )
        else:
            if record.declared_vot_per_second is not None:
                raise RuntimeError(
                    f"Nonparticipating declared VOT is not None for {record.vehicle_name}."
                )

    world = reference.build_world_and_network()
    reference._assert_world_network_contract(world)

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
            if node.func.attr == "install_real_world_spillback_observation":
                raise RuntimeError("Static validation must not install spillback hooks.")
            if node.func.attr == "build_tvt_mp_research_output":
                raise RuntimeError("Static validation must not build research output.")


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
        raise RuntimeError("World nonparticipating names differ from the embedded set.")


def passage_comparison(bundle) -> dict:
    both_observed = 0
    equal_count = 0
    unequal_count = 0
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
            if visit.candidate_passage_timestep == visit.actual_passage_timestep:
                equal_count += 1
            else:
                unequal_count += 1
    scenario = bundle.scenario[0]
    predicted_available = 0
    actual_available = 0
    for vehicle_row in bundle.vehicles:
        if vehicle_row.nonparticipating_predicted_external_effect_total is not None:
            predicted_available += 1
        if vehicle_row.nonparticipating_actual_external_effect_total is not None:
            actual_available += 1
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
            "Four-cross grid medium nonparticipating 120/600 variant. "
            "Not a formal experiment schema."
        ),
        "run_type": "trial",
        "scenario_name": SCENARIO_NAME,
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
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
        "max_candidate_visit_count": reference.MAX_CANDIDATE_VISIT_COUNT,
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
        "TVT-MP four-cross grid medium nonparticipating 20 percent trial",
        "=" * 55,
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"Reference scenario: {reference.SCENARIO_NAME}",
        f"Reference output directory: {reference.TRIAL_OUTPUT_DIR.name}",
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
        f"candidate limit {reference.MAX_CANDIDATE_VISIT_COUNT}, "
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
    print("=== TVT-MP four-cross grid medium nonparticipating 20% trial ===")
    print()
    print(f"Scenario: {SCENARIO_NAME}")
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
        TRIAL_OUTPUT_DIR.mkdir(parents=False, exist_ok=False)

        vot_values = _true_vot_sequence()
        vot_records = build_vehicle_vot_records(VEHICLE_SPECS, vot_values)

        t0 = time.perf_counter()
        world = build_world()
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
