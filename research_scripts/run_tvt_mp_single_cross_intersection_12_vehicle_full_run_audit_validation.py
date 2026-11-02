"""
12-vehicle single cross intersection trial with full-run audit helper attached.

Same network, vehicle plan, seeds, VOT, and evaluation window as
run_tvt_mp_single_cross_intersection_12_vehicle_trial.py. Adds the
research_scripts/tvt_mp_full_run_audit_helper.py hooks and writes two audit
CSVs into a separate output directory. All vehicles remain participating;
nonparticipating 20% is not part of this validation script.

Run from the repository root:

    python research_scripts/run_tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation.py --static-validate-only
    python research_scripts/run_tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation.py
"""

from __future__ import annotations

import ast
import csv
import hashlib
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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tvt_mp_full_run_audit_helper import (  # noqa: E402
    TRANSACTION_AUDIT_CSV_NAME,
    VISIT_AUDIT_CSV_NAME,
    finalize_tvt_mp_full_run_audit,
    install_tvt_mp_full_run_audit,
    write_tvt_mp_full_run_audit_csv,
)

# ---------------------------------------------------------------------------
# 1. Constants (same experiment as the base 12-vehicle trial)
# ---------------------------------------------------------------------------

SCENARIO_NAME = (
    "tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation_seed_1"
)
WORLD_DISPLAY_NAME = "tvt_mp_single_cross_intersection_12_vehicle"

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

CENTRAL_INTERSECTION_NODE = "intersection"
PERIPHERAL_NODE_NAMES: tuple[str, ...] = ("north", "east", "south", "west")
NODE_NAMES: tuple[str, ...] = (CENTRAL_INTERSECTION_NODE,) + PERIPHERAL_NODE_NAMES

ORIGIN_DEPARTURE_ORDER: tuple[str, ...] = PERIPHERAL_NODE_NAMES

DEPARTURE_TIMESTEPS: tuple[int, ...] = (5, 9, 13)
VEHICLES_PER_DEPARTURE_TIMESTEP = 4

ROUTE_ASSIGNMENT_MODE = "uxsim_dynamic_route_choice_from_od"
SPECIFIED_ROUTE_USED = False

LINK_SPECS: tuple[tuple[str, str, str], ...] = (
    ("north_to_intersection", "north", "intersection"),
    ("intersection_to_north", "intersection", "north"),
    ("east_to_intersection", "east", "intersection"),
    ("intersection_to_east", "intersection", "east"),
    ("south_to_intersection", "south", "intersection"),
    ("intersection_to_south", "intersection", "south"),
    ("west_to_intersection", "west", "intersection"),
    ("intersection_to_west", "intersection", "west"),
)

INLINK_COUNT = sum(1 for _name, _u, down in LINK_SPECS if down == CENTRAL_INTERSECTION_NODE)
OUTLINK_COUNT = sum(
    1 for _name, up, _down in LINK_SPECS if up == CENTRAL_INTERSECTION_NODE
)
LINK_COUNT = len(LINK_SPECS)

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAL_PARENT = REPO_ROOT / "research_outputs" / "trial"
TRIAL_OUTPUT_DIR = TRIAL_PARENT / SCENARIO_NAME

RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
)

FULL_RUN_AUDIT_CSV_NAMES = (
    TRANSACTION_AUDIT_CSV_NAME,
    VISIT_AUDIT_CSV_NAME,
)

SCRIPT_PATH = Path(__file__).resolve()

BASE_TRIAL_SCRIPT_BASENAME = "run_tvt_mp_single_cross_intersection_12_vehicle_trial.py"
BASE_TRIAL_OUTPUT_DIR_NAME = (
    "tvt_mp_single_cross_intersection_12_vehicle_seed_1_initial"
)

KNOWN_OTHER_TRIAL_DIR_NAMES: tuple[str, ...] = (
    BASE_TRIAL_OUTPUT_DIR_NAME,
    "tvt_mp_50_vehicle_medium_demand_seed_1_initial",
    "tvt_mp_50_vehicle_medium_demand_seed_1_passage_resolution_v2",
    "tvt_mp_50_vehicle_medium_demand_seed_1_capacity_refill_v3",
    "tvt_mp_50_vehicle_asymmetric_demand_seed_1_initial",
    "tvt_mp_small_scale_initial_seed_1_baseline_arrival_order",
    "tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2",
)

MOVEMENT_BY_ORIGIN_DESTINATION: dict[tuple[str, str], str] = {
    ("north", "south"): "straight",
    ("north", "east"): "left",
    ("north", "west"): "right",
    ("north", "north"): "u_turn",
    ("east", "west"): "straight",
    ("east", "south"): "left",
    ("east", "north"): "right",
    ("east", "east"): "u_turn",
    ("south", "north"): "straight",
    ("south", "west"): "left",
    ("south", "east"): "right",
    ("south", "south"): "u_turn",
    ("west", "east"): "straight",
    ("west", "north"): "left",
    ("west", "south"): "right",
    ("west", "west"): "u_turn",
}


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool


def planned_movement_label(origin: str, destination: str) -> str:
    key = (origin, destination)
    if key not in MOVEMENT_BY_ORIGIN_DESTINATION:
        raise KeyError(f"No movement label for OD {origin} -> {destination}.")
    return MOVEMENT_BY_ORIGIN_DESTINATION[key]


def _build_vehicle_specs() -> tuple[VehicleSpec, ...]:
    raw_rows: list[tuple[str, str, str, int]] = [
        ("veh_n1", "north", "south", 5),
        ("veh_e1", "east", "west", 5),
        ("veh_s1", "south", "north", 5),
        ("veh_w1", "west", "east", 5),
        ("veh_n2", "north", "east", 9),
        ("veh_e2", "east", "south", 9),
        ("veh_s2", "south", "west", 9),
        ("veh_w2", "west", "north", 9),
        ("veh_n3", "north", "west", 13),
        ("veh_e3", "east", "north", 13),
        ("veh_s3", "south", "east", 13),
        ("veh_w3", "west", "south", 13),
    ]

    specs = [
        VehicleSpec(
            vehicle_name=name,
            orig=orig,
            dest=dest,
            departure_timestep=departure,
            participating=True,
        )
        for name, orig, dest, departure in raw_rows
    ]

    def sort_key(spec: VehicleSpec) -> tuple[int, int]:
        origin_order = ORIGIN_DEPARTURE_ORDER.index(spec.orig)
        return (spec.departure_timestep, origin_order)

    specs.sort(key=sort_key)
    return tuple(specs)


VEHICLE_SPECS: tuple[VehicleSpec, ...] = _build_vehicle_specs()


@dataclass
class TimingRecord:
    world_build_s: float = 0.0
    finalize_s: float = 0.0
    exec_simulation_s: float = 0.0
    research_build_s: float = 0.0
    audit_finalize_s: float = 0.0
    csv_write_s: float = 0.0
    audit_csv_write_s: float = 0.0
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


@dataclass(frozen=True)
class FullRunAuditSummary:
    transaction_row_count: int
    visit_row_count: int
    buyer_row_count: int
    seller_row_count: int
    nonparticipating_row_count: int
    actual_arrival_saved_row_count: int
    validation_passed: bool
    transaction_csv_sha256: str
    visit_csv_sha256: str


# ---------------------------------------------------------------------------
# Static contract validation (no World build, simulation, mkdir, or writes)
# ---------------------------------------------------------------------------


def manifest_counts_from_specs(
    specs: tuple[VehicleSpec, ...],
) -> dict[str, int | str | bool | list[int]]:
    movement_counts = {"straight": 0, "left": 0, "right": 0, "u_turn": 0}
    for spec in specs:
        label = planned_movement_label(spec.orig, spec.dest)
        movement_counts[label] += 1

    unique_origins = {spec.orig for spec in specs}
    unique_dests = {spec.dest for spec in specs}

    return {
        "vehicle_count": len(specs),
        "participating_count": sum(1 for s in specs if s.participating),
        "nonparticipating_count": sum(1 for s in specs if not s.participating),
        "central_intersection_node": CENTRAL_INTERSECTION_NODE,
        "inlink_count": INLINK_COUNT,
        "outlink_count": OUTLINK_COUNT,
        "link_count": LINK_COUNT,
        "link_length_m": LINK_LENGTH_M,
        "lane_count_per_link": NUMBER_OF_LANES,
        "route_assignment_mode": ROUTE_ASSIGNMENT_MODE,
        "specified_route_used": SPECIFIED_ROUTE_USED,
        "origin_count": len(unique_origins),
        "destination_count": len(unique_dests),
        "planned_straight_od_count": movement_counts["straight"],
        "planned_left_turn_od_count": movement_counts["left"],
        "planned_right_turn_od_count": movement_counts["right"],
        "planned_u_turn_od_count": movement_counts["u_turn"],
        "departure_timesteps": list(DEPARTURE_TIMESTEPS),
        "vehicles_per_departure_timestep": VEHICLES_PER_DEPARTURE_TIMESTEP,
        "baseline_horizon_steps": BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": MAX_CANDIDATE_VISIT_COUNT,
        "clearance_timesteps": 1,
    }


def _origin_order_key(spec: VehicleSpec) -> tuple[int, int]:
    return (spec.departure_timestep, ORIGIN_DEPARTURE_ORDER.index(spec.orig))


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _function_body_calls(function_def: ast.FunctionDef) -> list[tuple[int, str]]:
    calls: list[tuple[int, str]] = []
    for node in ast.walk(function_def):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name is None:
            continue
        calls.append((node.lineno, name))
    calls.sort(key=lambda item: item[0])
    return calls


def _require_call_before(calls: list[tuple[int, str]], first: str, second: str) -> None:
    first_line = None
    second_line = None
    for line_number, name in calls:
        if name == first and first_line is None:
            first_line = line_number
        if name == second and second_line is None:
            second_line = line_number
    if first_line is None:
        raise RuntimeError(f"Static contract: main() never calls {first}.")
    if second_line is None:
        raise RuntimeError(f"Static contract: main() never calls {second}.")
    if first_line >= second_line:
        raise RuntimeError(
            f"Static contract: {first} must appear before {second} in main()."
        )


def _count_calls_named(calls: list[tuple[int, str]], name: str) -> int:
    count = 0
    for _line_number, call_name in calls:
        if call_name == name:
            count = count + 1
    return count


def _assert_static_source_contract(source_text: str) -> None:
    if BASE_TRIAL_SCRIPT_BASENAME.replace(".py", "") in source_text:
        forbidden_import = (
            "import run_tvt_mp_single_cross_"
            + "intersection_12_vehicle_trial"
        )
        if forbidden_import in source_text:
            raise RuntimeError(
                "Static contract: must not runtime-import the base 12-vehicle trial."
            )

    if BASE_TRIAL_OUTPUT_DIR_NAME in source_text:
        read_existing = (
            'Path("research_outputs") / "trial" / '
            + f'"{BASE_TRIAL_OUTPUT_DIR_NAME}"'
        )
        if read_existing in source_text:
            raise RuntimeError(
                "Static contract: must not read the existing base trial output "
                "directory at runtime."
            )

    tree = ast.parse(source_text)
    main_function = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_function = node
            break
    if main_function is None:
        raise RuntimeError("Static contract: main() is missing.")

    calls = _function_body_calls(main_function)
    _require_call_before(
        calls,
        "install_tvt_mp_full_run_audit",
        "exec_simulation",
    )
    _require_call_before(
        calls,
        "build_tvt_mp_research_output",
        "finalize_tvt_mp_full_run_audit",
    )
    _require_call_before(
        calls,
        "write_tvt_mp_research_output_csv",
        "write_tvt_mp_full_run_audit_csv",
    )

    exec_count = _count_calls_named(calls, "exec_simulation")
    if exec_count != 1:
        raise RuntimeError(
            f"Static contract: main() must call exec_simulation exactly once; "
            f"found {exec_count}."
        )

    for required_name in (
        "install_tvt_mp_full_run_audit",
        "finalize_tvt_mp_full_run_audit",
        "write_tvt_mp_full_run_audit_csv",
    ):
        if _count_calls_named(calls, required_name) != 1:
            raise RuntimeError(
                f"Static contract: main() must call {required_name} exactly once."
            )

    forbidden_profiling_fragments = (
        "cPro" + "file",
        "profile" + ".run",
    )
    for fragment in forbidden_profiling_fragments:
        if fragment in source_text:
            raise RuntimeError(
                f"Static contract: forbidden profiling fragment {fragment!r} "
                "in script source."
            )


def validate_static_contract() -> None:
    specs = VEHICLE_SPECS
    counts = manifest_counts_from_specs(specs)

    if SCENARIO_NAME != (
        "tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation_seed_1"
    ):
        raise RuntimeError("Unexpected SCENARIO_NAME for full-run audit validation.")
    if TRIAL_OUTPUT_DIR.name != SCENARIO_NAME:
        raise RuntimeError("TRIAL_OUTPUT_DIR name must match SCENARIO_NAME.")

    if len(NODE_NAMES) != 5:
        raise RuntimeError(f"Expected 5 nodes, got {len(NODE_NAMES)}.")
    if LINK_COUNT != 8:
        raise RuntimeError(f"Expected 8 links, got {LINK_COUNT}.")
    if counts["vehicle_count"] != 12:
        raise RuntimeError(f"Expected 12 VehicleSpec, got {counts['vehicle_count']}.")
    if counts["participating_count"] != 12:
        raise RuntimeError(
            f"Expected 12 participating, got {counts['participating_count']}."
        )
    if counts["nonparticipating_count"] != 0:
        raise RuntimeError(
            f"Expected 0 nonparticipating, got {counts['nonparticipating_count']}."
        )

    for departure in DEPARTURE_TIMESTEPS:
        at_t = [s for s in specs if s.departure_timestep == departure]
        if len(at_t) != VEHICLES_PER_DEPARTURE_TIMESTEP:
            raise RuntimeError(
                f"Expected {VEHICLES_PER_DEPARTURE_TIMESTEP} vehicles at T={departure}, "
                f"got {len(at_t)}."
            )

    for index in range(1, len(specs)):
        if _origin_order_key(specs[index]) < _origin_order_key(specs[index - 1]):
            raise RuntimeError("VEHICLE_SPECS sort order is wrong.")

    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "Remove or rename it manually before re-running."
        )

    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    _assert_static_source_contract(source_text)


# ---------------------------------------------------------------------------
# VOT, World, vehicles (same as base trial)
# ---------------------------------------------------------------------------


def generate_vehicle_vots(rng: np.random.Generator, count: int) -> list[float]:
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
        name=WORLD_DISPLAY_NAME,
        deltan=1,
        reaction_time=1,
        tmax=INTERNAL_TSIZE,
        random_seed=TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
    )

    world.addNode("intersection", 0, 0)
    world.addNode("north", 0, 1)
    world.addNode("east", 1, 0)
    world.addNode("south", 0, -1)
    world.addNode("west", -1, 0)

    for link_name, upstream, downstream in LINK_SPECS:
        world.addLink(
            link_name,
            upstream,
            downstream,
            length=LINK_LENGTH_M,
            free_flow_speed=FREE_FLOW_SPEED_M_PER_S,
            number_of_lanes=NUMBER_OF_LANES,
        )

    world.infer_order_control_eligible_nodes()
    world.set_order_control_for_nodes(
        [CENTRAL_INTERSECTION_NODE],
        order_control_type="time_value",
        transaction_case=None,
    )

    if world.order_control_clearance_timesteps != 1:
        raise RuntimeError(
            "Expected order_control_clearance_timesteps=1, "
            f"got {world.order_control_clearance_timesteps!r}."
        )

    world.order_control_tvt_evaluation_end_timestep = EVALUATION_END_TIMESTEP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT

    return world


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


def verify_evaluation_end(world: World) -> dict[str, int | bool]:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )

    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    for field_name, expected in (
        ("evaluation_end_unobserved_finalized_timestep", EVALUATION_END_TIMESTEP),
        ("trade_ex_post_evaluation_finalized_timestep", EVALUATION_END_TIMESTEP),
        ("individual_ex_post_evaluation_finalized_timestep", EVALUATION_END_TIMESTEP),
    ):
        actual = getattr(registry, field_name)
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
# Audit CSV verification
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def count_csv_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        count = 0
        for _row in reader:
            count = count + 1
        return count


def read_csv_dict_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(dict(row))
        return rows


def _parse_int_cell(value: str, label: str, row_index: int) -> int:
    if value == "":
        raise RuntimeError(f"{label} row {row_index}: expected integer, got blank.")
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(
            f"{label} row {row_index}: expected integer, got {value!r}."
        ) from error


def _parse_optional_int_cell(value: str) -> int | None:
    if value == "":
        return None
    return int(value)


def verify_audit_csv_files_exist(directory: Path) -> None:
    for name in FULL_RUN_AUDIT_CSV_NAMES:
        path = directory / name
        if not path.is_file():
            raise RuntimeError(f"Expected audit CSV missing: {path}")


def verify_full_run_audit_output(
    directory: Path,
    bundle,
    audit_result,
) -> FullRunAuditSummary:
    verify_audit_csv_files_exist(directory)

    research_transaction_rows = count_csv_data_rows(
        directory / "tvt_mp_transactions.csv"
    )
    research_visit_rows = count_csv_data_rows(directory / "tvt_mp_visits.csv")

    transaction_rows = read_csv_dict_rows(directory / TRANSACTION_AUDIT_CSV_NAME)
    visit_rows = read_csv_dict_rows(directory / VISIT_AUDIT_CSV_NAME)

    if len(transaction_rows) != research_transaction_rows:
        raise RuntimeError(
            "Transaction audit row count "
            f"{len(transaction_rows)} != research transactions "
            f"{research_transaction_rows}."
        )
    if len(visit_rows) != research_visit_rows:
        raise RuntimeError(
            f"Visit audit row count {len(visit_rows)} != research visits "
            f"{research_visit_rows}."
        )
    if len(audit_result.transaction_rows) != len(transaction_rows):
        raise RuntimeError("Frozen audit transaction count disagrees with CSV.")
    if len(audit_result.visit_rows) != len(visit_rows):
        raise RuntimeError("Frozen audit visit count disagrees with CSV.")

    buyer_row_count = 0
    seller_row_count = 0
    nonparticipating_row_count = 0
    actual_arrival_saved_row_count = 0

    for index, row in enumerate(transaction_rows, start=1):
        buyer_count = _parse_int_cell(row["buyer_count"], "transaction audit", index)
        seller_count = _parse_int_cell(row["seller_count"], "transaction audit", index)
        nonparticipating_count = _parse_int_cell(
            row["nonparticipating_count"], "transaction audit", index
        )
        trade_scope_count = _parse_int_cell(
            row["trade_scope_count"], "transaction audit", index
        )
        if buyer_count + seller_count + nonparticipating_count != trade_scope_count:
            raise RuntimeError(
                "Transaction audit row "
                f"{index}: buyer+seller+nonparticipating != trade_scope_count."
            )
        if row["fifo_inspection_passed"] != "True":
            raise RuntimeError(
                f"Transaction audit row {index}: fifo_inspection_passed is not True."
            )
        fifo_violation_count = _parse_int_cell(
            row["fifo_violation_count"], "transaction audit", index
        )
        if fifo_violation_count < 0:
            raise RuntimeError(
                f"Transaction audit row {index}: fifo_violation_count is negative."
            )
        for count_name in (
            "max_same_inlink_party_count",
            "max_same_inlink_buyer_count",
            "max_same_inlink_seller_count",
            "max_same_inlink_nonparticipating_count",
        ):
            count_value = _parse_int_cell(row[count_name], "transaction audit", index)
            if count_value < 0:
                raise RuntimeError(
                    f"Transaction audit row {index}: {count_name} is negative."
                )

    for index, row in enumerate(visit_rows, start=1):
        role = row["role"]
        if role == "buyer":
            buyer_row_count = buyer_row_count + 1
            if row["buyer_value_G_b"] == "" or row["payment_P_b"] == "":
                raise RuntimeError(
                    f"Visit audit buyer row {index} missing G_b or payment_P_b."
                )
        elif role == "seller":
            seller_row_count = seller_row_count + 1
            if (
                row["seller_required_compensation_R_s"] == ""
                or row["compensation_C_s"] == ""
            ):
                raise RuntimeError(
                    f"Visit audit seller row {index} missing R_s or compensation_C_s."
                )
        elif role == "nonparticipating":
            nonparticipating_row_count = nonparticipating_row_count + 1
        else:
            raise RuntimeError(f"Visit audit row {index}: unknown role {role!r}.")

        for required_name in (
            "inlink_name",
            "baseline_arrival_timestep",
            "baseline_local_rank",
            "post_trade_local_rank",
            "assigned_rank",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
        ):
            if row[required_name] == "":
                raise RuntimeError(
                    f"Visit audit row {index}: missing {required_name}."
                )

        if row["same_inlink_fifo_preserved"] != "True":
            raise RuntimeError(
                f"Visit audit row {index}: same_inlink_fifo_preserved is not True."
            )

        actual_arrival = _parse_optional_int_cell(row["actual_node_arrival_timestep"])
        actual_passage = _parse_optional_int_cell(row["actual_passage_timestep"])
        if actual_arrival is not None:
            actual_arrival_saved_row_count = actual_arrival_saved_row_count + 1
        if actual_passage is not None:
            if actual_arrival is not None and actual_passage < actual_arrival + 1:
                raise RuntimeError(
                    f"Visit audit row {index}: actual_passage_timestep "
                    f"{actual_passage} is before actual_node_arrival_timestep "
                    f"{actual_arrival} + 1."
                )

    if buyer_row_count < 1 or seller_row_count < 1:
        raise RuntimeError(
            "Visit audit must contain at least one buyer row and one seller row."
        )
    if nonparticipating_row_count != 0:
        raise RuntimeError(
            f"Expected 0 nonparticipating visit audit rows, got "
            f"{nonparticipating_row_count}."
        )

    transaction_sha256 = sha256_file(directory / TRANSACTION_AUDIT_CSV_NAME)
    visit_sha256 = sha256_file(directory / VISIT_AUDIT_CSV_NAME)

    return FullRunAuditSummary(
        transaction_row_count=len(transaction_rows),
        visit_row_count=len(visit_rows),
        buyer_row_count=buyer_row_count,
        seller_row_count=seller_row_count,
        nonparticipating_row_count=nonparticipating_row_count,
        actual_arrival_saved_row_count=actual_arrival_saved_row_count,
        validation_passed=True,
        transaction_csv_sha256=transaction_sha256,
        visit_csv_sha256=visit_sha256,
    )


def verify_research_csv_files(directory: Path) -> None:
    for name in RESEARCH_CSV_NAMES:
        path = directory / name
        if not path.is_file():
            raise RuntimeError(f"Expected research CSV missing: {path}")


# ---------------------------------------------------------------------------
# Auxiliary output files
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
    audit_summary: FullRunAuditSummary,
) -> None:
    trial_fields = manifest_counts_from_specs(VEHICLE_SPECS)
    manifest = {
        "schema_note": (
            "12-vehicle single cross intersection full-run audit validation "
            "manifest; same experiment as the base 12-vehicle trial with audit "
            "helper attached."
        ),
        "run_type": "full_run_audit_validation",
        "scenario_name": SCENARIO_NAME,
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
        "traffic_seed": TRAFFIC_SEED,
        "vot_seed": VOT_SEED,
        "evaluation_start_timestep": EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": EVALUATION_END_TIMESTEP,
        "internal_tsize": INTERNAL_TSIZE,
        "baseline_horizon_steps": trial_fields["baseline_horizon_steps"],
        "decision_window_contract": DECISION_WINDOW_CONTRACT,
        "max_candidate_visit_count": trial_fields["max_candidate_visit_count"],
        "clearance_timesteps": clearance_timesteps,
        "vehicle_count": trial_fields["vehicle_count"],
        "participating_count": trial_fields["participating_count"],
        "nonparticipating_count": trial_fields["nonparticipating_count"],
        "route_assignment_mode": trial_fields["route_assignment_mode"],
        "specified_route_used": trial_fields["specified_route_used"],
        "full_run_audit_enabled": True,
        "full_run_audit_validation": True,
        "full_run_audit_transaction_row_count": audit_summary.transaction_row_count,
        "full_run_audit_visit_row_count": audit_summary.visit_row_count,
        "full_run_audit_nonparticipating_row_count": (
            audit_summary.nonparticipating_row_count
        ),
        "full_run_audit_transaction_csv_sha256": (
            audit_summary.transaction_csv_sha256
        ),
        "full_run_audit_visit_csv_sha256": audit_summary.visit_csv_sha256,
        "timing_seconds": {
            "world_build": timing.world_build_s,
            "finalize_scenario": timing.finalize_s,
            "exec_simulation": timing.exec_simulation_s,
            "research_output_build": timing.research_build_s,
            "audit_finalize": timing.audit_finalize_s,
            "csv_write": timing.csv_write_s,
            "audit_csv_write": timing.audit_csv_write_s,
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
    generated_files: list[str],
    audit_summary: FullRunAuditSummary,
) -> None:
    scenario_row = bundle.scenario[0]
    lines = [
        "TVT-MP single cross intersection 12-vehicle full-run audit validation",
        "=" * 60,
        "Completed run: yes",
        "Audit helper attached: yes (tvt_mp_full_run_audit_helper.py)",
        f"Scenario name: {SCENARIO_NAME}",
        f"World display name: {WORLD_DISPLAY_NAME}",
        f"World.T after exec_simulation: {world.T}",
        "",
        "Full-run audit CSV validation: passed",
        f"Transaction audit rows: {audit_summary.transaction_row_count}",
        f"Visit audit rows: {audit_summary.visit_row_count}",
        f"Visit audit buyer rows: {audit_summary.buyer_row_count}",
        f"Visit audit seller rows: {audit_summary.seller_row_count}",
        f"Visit audit nonparticipating rows: "
        f"{audit_summary.nonparticipating_row_count}",
        f"Visit audit rows with actual_node_arrival_timestep saved: "
        f"{audit_summary.actual_arrival_saved_row_count}",
        "",
        f"Completed trips: {completed_trips} / {len(VEHICLE_SPECS)}",
        f"Transaction count (research): {scenario_row.transaction_count}",
        "",
        "Timing (seconds):",
        f"  world_build: {timing.world_build_s:.4f}",
        f"  finalize_scenario: {timing.finalize_s:.4f}",
        f"  exec_simulation: {timing.exec_simulation_s:.4f}",
        f"  research_output_build: {timing.research_build_s:.4f}",
        f"  audit_finalize: {timing.audit_finalize_s:.4f}",
        f"  csv_write: {timing.csv_write_s:.4f}",
        f"  audit_csv_write: {timing.audit_csv_write_s:.4f}",
        f"  script_total: {timing.script_total_s:.4f}",
        "",
        "Generated files:",
    ]
    for name in generated_files:
        lines.append(f"  - {name}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_console_summary(
    eval_ok: dict,
    timing: TimingRecord,
    completed_trips: int,
    bundle,
    output_dir: Path,
    audit_summary: FullRunAuditSummary,
) -> None:
    scenario_row = bundle.scenario[0]
    print()
    print("=== 12-vehicle full-run audit validation ===")
    print()
    print(f"Scenario: {SCENARIO_NAME}")
    print(f"World.T: {eval_ok['world_t']}")
    print(f"Transactions (research): {scenario_row.transaction_count}")
    print(f"Transaction audit rows: {audit_summary.transaction_row_count}")
    print(f"Visit audit rows: {audit_summary.visit_row_count}")
    print(f"Audit validation: passed")
    print(f"Completed trips: {completed_trips}")
    print(f"Output: {output_dir}")
    print(f"Total time (s): {timing.script_total_s:.3f}")
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

    install_tvt_mp_full_run_audit(world)

    t0 = time.perf_counter()
    world.exec_simulation()
    timing.exec_simulation_s = time.perf_counter() - t0

    eval_ok = verify_evaluation_end(world)

    t0 = time.perf_counter()
    bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
    timing.research_build_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    audit_result = finalize_tvt_mp_full_run_audit(world, bundle)
    timing.audit_finalize_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    write_tvt_mp_research_output_csv(
        bundle,
        TRIAL_OUTPUT_DIR,
        overwrite=False,
    )
    timing.csv_write_s = time.perf_counter() - t0

    verify_research_csv_files(TRIAL_OUTPUT_DIR)

    t0 = time.perf_counter()
    write_tvt_mp_full_run_audit_csv(audit_result, TRIAL_OUTPUT_DIR)
    timing.audit_csv_write_s = time.perf_counter() - t0

    verify_audit_csv_files_exist(TRIAL_OUTPUT_DIR)

    audit_summary = verify_full_run_audit_output(
        TRIAL_OUTPUT_DIR,
        bundle,
        audit_result,
    )

    generated_files = list(RESEARCH_CSV_NAMES) + list(FULL_RUN_AUDIT_CSV_NAMES) + [
        "vehicle_vot.csv",
        "manifest.json",
        "run_summary.txt",
    ]

    completed_trips = int(world.analyzer.trip_completed)

    t0 = time.perf_counter()
    write_vehicle_vot_csv(TRIAL_OUTPUT_DIR / "vehicle_vot.csv", vot_records)
    write_manifest_json(
        TRIAL_OUTPUT_DIR / "manifest.json",
        timing,
        world,
        generated_files,
        world.order_control_clearance_timesteps,
        audit_summary,
    )
    write_run_summary_txt(
        TRIAL_OUTPUT_DIR / "run_summary.txt",
        timing,
        world,
        bundle,
        completed_trips,
        generated_files,
        audit_summary,
    )
    timing.trial_aux_write_s = time.perf_counter() - t0

    timing.script_total_s = time.perf_counter() - script_start

    write_manifest_json(
        TRIAL_OUTPUT_DIR / "manifest.json",
        timing,
        world,
        generated_files,
        world.order_control_clearance_timesteps,
        audit_summary,
    )
    write_run_summary_txt(
        TRIAL_OUTPUT_DIR / "run_summary.txt",
        timing,
        world,
        bundle,
        completed_trips,
        generated_files,
        audit_summary,
    )

    print_console_summary(
        eval_ok,
        timing,
        completed_trips,
        bundle,
        TRIAL_OUTPUT_DIR,
        audit_summary,
    )

    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
            validate_static_contract()
            source = SCRIPT_PATH.read_text(encoding="utf-8")
            ast.parse(source)
            compile(source, str(SCRIPT_PATH), "exec")
            print("Static contract validation passed.", file=sys.stderr)
            raise SystemExit(0)
        raise SystemExit(main())
    except FileExistsError as exc:
        print(f"FileExistsError: {exc}", file=sys.stderr)
        raise SystemExit(1)
