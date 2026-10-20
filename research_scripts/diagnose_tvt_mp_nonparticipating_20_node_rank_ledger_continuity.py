"""
Replay the nonparticipating-20 two-cross trial once and audit Node rank ledgers.

This diagnostic inspects C-order ranks (assigned_rank) in
OrderControlTvtNodeRankState at simulation end. It does not audit
actual_node_passage_rank continuity across all visits.

No research CSV files are written. Existing trial output directories are
not modified. The trial script main() is not called.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState

import run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_nonparticipating_20_trial as trial


SCENARIO_NAME = trial.SCENARIO_NAME
TRIAL_SCRIPT_NAME = (
    "run_tvt_mp_two_cross_intersections_downstream_spillback_"
    "extended_south_pulse_nonparticipating_20_trial.py"
)

WEST_NODE_NAME = "west_intersection"
EAST_NODE_NAME = "east_intersection"
TARGET_NODE_NAMES = (WEST_NODE_NAME, EAST_NODE_NAME)

WEST_ORIGINS = ("west_north", "west_south")
EAST_VISIT_ONE_ORIGINS = ("east_north", "east_outer", "east_south")

EAST_VISIT_TWO_ORIGIN = "west_north"
EAST_VISIT_TWO_DEST = "east_outer"
EAST_VISIT_TWO_PLANNED_MOVEMENT = "left"

EXPECTED_WEST_NORTH_COUNT = 150
EXPECTED_WEST_SOUTH_COUNT = 101
EXPECTED_WEST_TOTAL = 251

EXPECTED_EAST_VISIT_ONE_COUNT = 300
EXPECTED_EAST_VISIT_TWO_COUNT = 99
EXPECTED_EAST_TOTAL = 399

EXPECTED_WEST_CONFIRMED = 251
EXPECTED_WEST_UNDETERMINED = 0

EXPECTED_EAST_VISIT_ONE_CONFIRMED = 240
EXPECTED_EAST_VISIT_ONE_UNDETERMINED = 60
EXPECTED_EAST_VISIT_TWO_CONFIRMED = 76
EXPECTED_EAST_VISIT_TWO_UNDETERMINED = 23
EXPECTED_EAST_CONFIRMED_TOTAL = 316
EXPECTED_EAST_UNDETERMINED_TOTAL = 83

EXPECTED_EAST_K_CONFIRMED = 316
EXPECTED_EAST_RANK_MAX = 316

VisitKey = tuple[str, int]


def visit_key_from_row(row: dict[str, Any]) -> VisitKey:
    vehicle_name = row["vehicle_name"]
    visit_id = row["visit_id"]
    if not isinstance(vehicle_name, str):
        raise RuntimeError("vehicle_name must be a string.")
    if not isinstance(visit_id, int):
        raise RuntimeError("visit_id must be an int.")
    return (vehicle_name, visit_id)


def build_west_expected_visit_keys(vehicle_specs) -> set[VisitKey]:
    expected: set[VisitKey] = set()
    for spec in vehicle_specs:
        if spec.orig in WEST_ORIGINS:
            expected.add((spec.vehicle_name, 1))
    return expected


def build_east_visit_one_expected_visit_keys(vehicle_specs) -> set[VisitKey]:
    expected: set[VisitKey] = set()
    for spec in vehicle_specs:
        if spec.orig in EAST_VISIT_ONE_ORIGINS:
            expected.add((spec.vehicle_name, 1))
    return expected


def build_east_visit_two_expected_visit_keys(vehicle_specs) -> set[VisitKey]:
    expected: set[VisitKey] = set()
    for spec in vehicle_specs:
        if spec.orig != EAST_VISIT_TWO_ORIGIN:
            continue
        if spec.dest != EAST_VISIT_TWO_DEST:
            continue
        if spec.planned_movement != EAST_VISIT_TWO_PLANNED_MOVEMENT:
            continue
        expected.add((spec.vehicle_name, 2))
    return expected


def count_west_origins(vehicle_specs) -> tuple[int, int]:
    west_north_count = 0
    west_south_count = 0
    for spec in vehicle_specs:
        if spec.orig == "west_north":
            west_north_count += 1
        elif spec.orig == "west_south":
            west_south_count += 1
    return west_north_count, west_south_count


def function_by_name(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Function {name} is missing.")


def call_names(function_node: ast.FunctionDef) -> list[str]:
    names: list[str] = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def diagnostic_must_not_write_research_output(tree: ast.Module) -> None:
    forbidden_call_attrs = (
        "write_tvt_mp_research_output_csv",
        "build_tvt_mp_research_output",
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in forbidden_call_attrs:
                raise RuntimeError(
                    f"Diagnostic must not call research output writer {func.attr}."
                )
            if func.attr == "main" and isinstance(func.value, ast.Name):
                if func.value.id == "trial":
                    raise RuntimeError("Diagnostic must not call trial.main().")
            if func.attr == "mkdir":
                raise RuntimeError("Diagnostic must not create output directories.")


def validate_static_contract() -> None:
    if SCENARIO_NAME != (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20_trial"
    ):
        raise RuntimeError("Scenario name does not match the nonparticipating trial.")
    if not (SCRIPT_DIR / TRIAL_SCRIPT_NAME).is_file():
        raise RuntimeError(f"Trial script is missing: {TRIAL_SCRIPT_NAME}.")

    if not callable(trial.validate_static_contract):
        raise RuntimeError("trial.validate_static_contract is not callable.")
    if not callable(trial._true_vot_sequence):
        raise RuntimeError("trial._true_vot_sequence is not callable.")
    if not callable(trial.build_world):
        raise RuntimeError("trial.build_world is not callable.")

    reference = trial.reference
    if not callable(reference.build_vehicle_vot_records):
        raise RuntimeError("reference.build_vehicle_vot_records is not callable.")
    if not callable(reference.add_vehicles_to_world):
        raise RuntimeError("reference.add_vehicles_to_world is not callable.")
    if not callable(reference.install_real_world_spillback_observation):
        raise RuntimeError("install_real_world_spillback_observation is not callable.")
    if not callable(reference.restore_real_world_spillback_observation):
        raise RuntimeError("restore_real_world_spillback_observation is not callable.")

    if len(trial.VEHICLE_SPECS) == 0:
        raise RuntimeError("trial.VEHICLE_SPECS is empty.")

    west_north_count, west_south_count = count_west_origins(trial.VEHICLE_SPECS)
    if west_north_count != EXPECTED_WEST_NORTH_COUNT:
        raise RuntimeError(
            f"west_north count is {west_north_count}, expected "
            f"{EXPECTED_WEST_NORTH_COUNT}."
        )
    if west_south_count != EXPECTED_WEST_SOUTH_COUNT:
        raise RuntimeError(
            f"west_south count is {west_south_count}, expected "
            f"{EXPECTED_WEST_SOUTH_COUNT}."
        )
    if west_north_count + west_south_count != EXPECTED_WEST_TOTAL:
        raise RuntimeError("West origin counts do not sum to 251.")

    west_expected = build_west_expected_visit_keys(trial.VEHICLE_SPECS)
    east_one_expected = build_east_visit_one_expected_visit_keys(trial.VEHICLE_SPECS)
    east_two_expected = build_east_visit_two_expected_visit_keys(trial.VEHICLE_SPECS)

    if len(west_expected) != EXPECTED_WEST_TOTAL:
        raise RuntimeError("West expected VisitKey count is not 251.")
    if len(east_one_expected) != EXPECTED_EAST_VISIT_ONE_COUNT:
        raise RuntimeError("East Visit ID=1 expected count is not 300.")
    if len(east_two_expected) != EXPECTED_EAST_VISIT_TWO_COUNT:
        raise RuntimeError("East Visit ID=2 expected count is not 99.")
    if len(east_one_expected) + len(east_two_expected) != EXPECTED_EAST_TOTAL:
        raise RuntimeError("East expected VisitKey total is not 399.")

    if not hasattr(OrderControlTvtNodeRankState, "export_state"):
        raise RuntimeError("OrderControlTvtNodeRankState.export_state is missing.")
    if not callable(OrderControlTvtNodeRankState.export_state):
        raise RuntimeError("OrderControlTvtNodeRankState.export_state is not callable.")

    if WEST_NODE_NAME not in TARGET_NODE_NAMES:
        raise RuntimeError("West node name is not in the target list.")
    if EAST_NODE_NAME not in TARGET_NODE_NAMES:
        raise RuntimeError("East node name is not in the target list.")

    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    validator = function_by_name(tree, "validate_static_contract")
    validator_calls = call_names(validator)
    if "exec_simulation" in validator_calls:
        raise RuntimeError("validate_static_contract must not call exec_simulation.")
    if "run_simulation_once" in validator_calls:
        raise RuntimeError("validate_static_contract must not run the simulation.")

    main_function = function_by_name(tree, "main")
    main_calls = call_names(main_function)
    if main_calls.count("run_simulation_once") != 1:
        raise RuntimeError("main must call run_simulation_once exactly once.")

    diagnostic_must_not_write_research_output(tree)

    for node_name in TARGET_NODE_NAMES:
        if node_name not in source:
            raise RuntimeError(f"Target node name {node_name} is not recorded.")


def prepare_world():
    reference = trial.reference
    reference.SPILLBACK_TIMESTEP_ROWS.clear()
    vot_values = trial._true_vot_sequence()
    vot_records = reference.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
    world = trial.build_world()
    reference.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
    world.finalize_scenario()
    return world


def run_simulation_once(world) -> None:
    reference = trial.reference
    reference.install_real_world_spillback_observation(world)
    try:
        world.exec_simulation()
    finally:
        reference.restore_real_world_spillback_observation()


def export_node_rank_ledger(world, node_name: str) -> dict[str, Any]:
    ledgers = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(ledgers, dict):
        raise RuntimeError(
            "world.order_control_tvt_rank_states_by_node_name must be a dict."
        )
    if node_name not in ledgers:
        raise RuntimeError(f"Missing rank ledger for node {node_name}.")
    state = ledgers[node_name]
    if not isinstance(state, OrderControlTvtNodeRankState):
        raise RuntimeError(
            f"Rank state for {node_name} is not OrderControlTvtNodeRankState."
        )
    exported = state.export_state()
    if not isinstance(exported, dict):
        raise RuntimeError(f"export_state for {node_name} did not return a dict.")
    return exported


def split_visit_keys_by_visit_id(visit_keys: set[VisitKey]) -> tuple[set[VisitKey], set[VisitKey]]:
    visit_one: set[VisitKey] = set()
    visit_two: set[VisitKey] = set()
    for vehicle_name, visit_id in visit_keys:
        if visit_id == 1:
            visit_one.add((vehicle_name, visit_id))
        elif visit_id == 2:
            visit_two.add((vehicle_name, visit_id))
        else:
            raise RuntimeError(f"Unexpected visit_id {visit_id} for {vehicle_name}.")
    return visit_one, visit_two


def collect_registered_visit_keys(export_state: dict[str, Any]) -> tuple[
    set[VisitKey],
    set[VisitKey],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    confirmed_rows = export_state["confirmed_visits"]
    undetermined_rows = export_state["undetermined_visits"]
    if not isinstance(confirmed_rows, list):
        raise RuntimeError("confirmed_visits must be a list.")
    if not isinstance(undetermined_rows, list):
        raise RuntimeError("undetermined_visits must be a list.")

    confirmed_keys: set[VisitKey] = set()
    undetermined_keys: set[VisitKey] = set()
    for row in confirmed_rows:
        key = visit_key_from_row(row)
        if key in confirmed_keys:
            raise RuntimeError(f"Duplicate confirmed VisitKey {key}.")
        confirmed_keys.add(key)
    for row in undetermined_rows:
        key = visit_key_from_row(row)
        if key in undetermined_keys:
            raise RuntimeError(f"Duplicate undetermined VisitKey {key}.")
        if key in confirmed_keys:
            raise RuntimeError(f"VisitKey {key} is both confirmed and undetermined.")
        undetermined_keys.add(key)
    return confirmed_keys, undetermined_keys, confirmed_rows, undetermined_rows


def analyze_confirmed_assigned_ranks(
    confirmed_rows: list[dict[str, Any]],
    k_confirmed_from_export: int,
) -> dict[str, Any]:
    assigned_ranks: list[int] = []
    visit_keys: list[VisitKey] = []
    duplicate_visit_keys: list[VisitKey] = []
    seen_visit_keys: set[VisitKey] = set()

    for row in confirmed_rows:
        key = visit_key_from_row(row)
        assigned_rank = row["assigned_rank"]
        if not isinstance(assigned_rank, int):
            raise RuntimeError("assigned_rank must be an int.")
        visit_keys.append(key)
        assigned_ranks.append(assigned_rank)
        if key in seen_visit_keys:
            duplicate_visit_keys.append(key)
        seen_visit_keys.add(key)

    duplicate_ranks: list[int] = []
    seen_ranks: set[int] = set()
    for rank in assigned_ranks:
        if rank in seen_ranks:
            duplicate_ranks.append(rank)
        seen_ranks.add(rank)

    export_order_matches_assigned_rank_order = True
    previous_rank = 0
    for rank in assigned_ranks:
        if rank <= previous_rank:
            export_order_matches_assigned_rank_order = False
            break
        previous_rank = rank

    if assigned_ranks:
        minimum_rank = min(assigned_ranks)
        maximum_rank = max(assigned_ranks)
        expected_range = set(range(minimum_rank, maximum_rank + 1))
        missing_ranks = sorted(expected_range - set(assigned_ranks))
    else:
        minimum_rank = 0
        maximum_rank = 0
        missing_ranks = []

    unexpected_ranks: list[int] = []
    if k_confirmed_from_export > 0:
        allowed = set(range(1, k_confirmed_from_export + 1))
        for rank in assigned_ranks:
            if rank not in allowed:
                unexpected_ranks.append(rank)

    unique_assigned_rank_count = len(set(assigned_ranks))
    assigned_rank_sequence_is_continuous = (
        k_confirmed_from_export == len(confirmed_rows)
        and k_confirmed_from_export == unique_assigned_rank_count
        and len(duplicate_ranks) == 0
        and len(duplicate_visit_keys) == 0
        and len(missing_ranks) == 0
        and len(unexpected_ranks) == 0
        and export_order_matches_assigned_rank_order is True
        and (k_confirmed_from_export == 0 or minimum_rank == 1)
        and (k_confirmed_from_export == 0 or maximum_rank == k_confirmed_from_export)
    )

    return {
        "minimum_assigned_rank": minimum_rank,
        "maximum_assigned_rank": maximum_rank,
        "unique_assigned_rank_count": unique_assigned_rank_count,
        "missing_assigned_ranks": missing_ranks,
        "duplicate_assigned_ranks": sorted(set(duplicate_ranks)),
        "duplicate_visit_keys": duplicate_visit_keys,
        "unexpected_assigned_ranks": sorted(set(unexpected_ranks)),
        "export_order_matches_assigned_rank_order": export_order_matches_assigned_rank_order,
        "assigned_rank_sequence_is_continuous": assigned_rank_sequence_is_continuous,
        "k_confirmed_matches_confirmed_rows": k_confirmed_from_export == len(confirmed_rows),
    }


def reconcile_expected_visit_keys(
    expected_keys: set[VisitKey],
    confirmed_keys: set[VisitKey],
    undetermined_keys: set[VisitKey],
) -> dict[str, Any]:
    registered_keys = confirmed_keys | undetermined_keys
    missing_unregistered = sorted(expected_keys - registered_keys)
    unexpected_confirmed = sorted(confirmed_keys - expected_keys)
    unexpected_undetermined = sorted(undetermined_keys - expected_keys)
    return {
        "expected_count": len(expected_keys),
        "confirmed_count": len(confirmed_keys),
        "undetermined_count": len(undetermined_keys),
        "missing_unregistered_count": len(missing_unregistered),
        "missing_unregistered": missing_unregistered,
        "unexpected_confirmed_count": len(unexpected_confirmed),
        "unexpected_confirmed": unexpected_confirmed,
        "unexpected_undetermined_count": len(unexpected_undetermined),
        "unexpected_undetermined": unexpected_undetermined,
    }


def require_zero_mismatch(label: str, field_name: str, actual: int, expected: int = 0) -> None:
    if actual != expected:
        raise RuntimeError(
            f"{label}: {field_name} is {actual}, expected {expected}."
        )


def audit_west_ledger(export_state: dict[str, Any], expected_keys: set[VisitKey]) -> dict[str, Any]:
    k_confirmed = export_state["k_confirmed"]
    if not isinstance(k_confirmed, int):
        raise RuntimeError("k_confirmed must be an int.")

    confirmed_keys, undetermined_keys, confirmed_rows, _ = collect_registered_visit_keys(
        export_state
    )
    reconciliation = reconcile_expected_visit_keys(
        expected_keys,
        confirmed_keys,
        undetermined_keys,
    )
    rank_analysis = analyze_confirmed_assigned_ranks(confirmed_rows, k_confirmed)

    require_zero_mismatch("west", "missing_unregistered", reconciliation["missing_unregistered_count"])
    require_zero_mismatch("west", "unexpected_confirmed", reconciliation["unexpected_confirmed_count"])
    require_zero_mismatch(
        "west",
        "unexpected_undetermined",
        reconciliation["unexpected_undetermined_count"],
    )
    require_zero_mismatch("west", "duplicate_assigned_ranks", len(rank_analysis["duplicate_assigned_ranks"]))
    require_zero_mismatch("west", "missing_assigned_ranks", len(rank_analysis["missing_assigned_ranks"]))
    require_zero_mismatch("west", "duplicate_visit_keys", len(rank_analysis["duplicate_visit_keys"]))
    require_zero_mismatch("west", "unexpected_assigned_ranks", len(rank_analysis["unexpected_assigned_ranks"]))

    if reconciliation["expected_count"] != EXPECTED_WEST_TOTAL:
        raise RuntimeError("West expected count is not 251.")
    if reconciliation["confirmed_count"] != EXPECTED_WEST_CONFIRMED:
        raise RuntimeError(
            f"West confirmed count is {reconciliation['confirmed_count']}, "
            f"expected {EXPECTED_WEST_CONFIRMED}."
        )
    if reconciliation["undetermined_count"] != EXPECTED_WEST_UNDETERMINED:
        raise RuntimeError(
            f"West undetermined count is {reconciliation['undetermined_count']}, "
            f"expected {EXPECTED_WEST_UNDETERMINED}."
        )
    if rank_analysis["minimum_assigned_rank"] != 1:
        raise RuntimeError("West minimum assigned rank is not 1.")
    if rank_analysis["maximum_assigned_rank"] != EXPECTED_WEST_TOTAL:
        raise RuntimeError("West maximum assigned rank is not 251.")
    if rank_analysis["assigned_rank_sequence_is_continuous"] is not True:
        raise RuntimeError("West assigned_rank_sequence_is_continuous is not True.")
    if rank_analysis["k_confirmed_matches_confirmed_rows"] is not True:
        raise RuntimeError("West k_confirmed does not match confirmed row count.")

    return {
        "reconciliation": reconciliation,
        "rank_analysis": rank_analysis,
        "k_confirmed": k_confirmed,
    }


def audit_east_ledger(
    export_state: dict[str, Any],
    expected_visit_one: set[VisitKey],
    expected_visit_two: set[VisitKey],
) -> dict[str, Any]:
    k_confirmed = export_state["k_confirmed"]
    if not isinstance(k_confirmed, int):
        raise RuntimeError("k_confirmed must be an int.")

    confirmed_keys, undetermined_keys, confirmed_rows, _ = collect_registered_visit_keys(
        export_state
    )
    expected_all = expected_visit_one | expected_visit_two
    reconciliation_all = reconcile_expected_visit_keys(
        expected_all,
        confirmed_keys,
        undetermined_keys,
    )

    confirmed_one, confirmed_two = split_visit_keys_by_visit_id(confirmed_keys)
    undetermined_one, undetermined_two = split_visit_keys_by_visit_id(undetermined_keys)

    reconciliation_visit_one = reconcile_expected_visit_keys(
        expected_visit_one,
        confirmed_one,
        undetermined_one,
    )
    reconciliation_visit_two = reconcile_expected_visit_keys(
        expected_visit_two,
        confirmed_two,
        undetermined_two,
    )

    rank_analysis = analyze_confirmed_assigned_ranks(confirmed_rows, k_confirmed)

    require_zero_mismatch("east", "missing_unregistered", reconciliation_all["missing_unregistered_count"])
    require_zero_mismatch("east", "unexpected_confirmed", reconciliation_all["unexpected_confirmed_count"])
    require_zero_mismatch(
        "east",
        "unexpected_undetermined",
        reconciliation_all["unexpected_undetermined_count"],
    )
    require_zero_mismatch("east", "duplicate_assigned_ranks", len(rank_analysis["duplicate_assigned_ranks"]))
    require_zero_mismatch("east", "missing_assigned_ranks", len(rank_analysis["missing_assigned_ranks"]))
    require_zero_mismatch("east", "duplicate_visit_keys", len(rank_analysis["duplicate_visit_keys"]))
    require_zero_mismatch("east", "unexpected_assigned_ranks", len(rank_analysis["unexpected_assigned_ranks"]))

    if reconciliation_visit_one["expected_count"] != EXPECTED_EAST_VISIT_ONE_COUNT:
        raise RuntimeError("East Visit ID=1 expected count is not 300.")
    if reconciliation_visit_one["confirmed_count"] != EXPECTED_EAST_VISIT_ONE_CONFIRMED:
        raise RuntimeError("East Visit ID=1 confirmed count is not 240.")
    if reconciliation_visit_one["undetermined_count"] != EXPECTED_EAST_VISIT_ONE_UNDETERMINED:
        raise RuntimeError("East Visit ID=1 undetermined count is not 60.")
    if reconciliation_visit_one["missing_unregistered_count"] != 0:
        raise RuntimeError("East Visit ID=1 has missing or unregistered visits.")

    if reconciliation_visit_two["expected_count"] != EXPECTED_EAST_VISIT_TWO_COUNT:
        raise RuntimeError("East Visit ID=2 expected count is not 99.")
    if reconciliation_visit_two["confirmed_count"] != EXPECTED_EAST_VISIT_TWO_CONFIRMED:
        raise RuntimeError("East Visit ID=2 confirmed count is not 76.")
    if reconciliation_visit_two["undetermined_count"] != EXPECTED_EAST_VISIT_TWO_UNDETERMINED:
        raise RuntimeError("East Visit ID=2 undetermined count is not 23.")
    if reconciliation_visit_two["missing_unregistered_count"] != 0:
        raise RuntimeError("East Visit ID=2 has missing or unregistered visits.")

    if reconciliation_all["expected_count"] != EXPECTED_EAST_TOTAL:
        raise RuntimeError("East expected total is not 399.")
    if reconciliation_all["confirmed_count"] != EXPECTED_EAST_CONFIRMED_TOTAL:
        raise RuntimeError("East confirmed total is not 316.")
    if reconciliation_all["undetermined_count"] != EXPECTED_EAST_UNDETERMINED_TOTAL:
        raise RuntimeError("East undetermined total is not 83.")

    if k_confirmed != EXPECTED_EAST_K_CONFIRMED:
        raise RuntimeError(f"East k_confirmed is {k_confirmed}, expected 316.")
    if rank_analysis["minimum_assigned_rank"] != 1:
        raise RuntimeError("East minimum assigned rank is not 1.")
    if rank_analysis["maximum_assigned_rank"] != EXPECTED_EAST_RANK_MAX:
        raise RuntimeError("East maximum assigned rank is not 316.")
    if rank_analysis["assigned_rank_sequence_is_continuous"] is not True:
        raise RuntimeError("East assigned_rank_sequence_is_continuous is not True.")
    if rank_analysis["k_confirmed_matches_confirmed_rows"] is not True:
        raise RuntimeError("East k_confirmed does not match confirmed row count.")

    return {
        "reconciliation_all": reconciliation_all,
        "reconciliation_visit_one": reconciliation_visit_one,
        "reconciliation_visit_two": reconciliation_visit_two,
        "rank_analysis": rank_analysis,
        "k_confirmed": k_confirmed,
    }


def print_report(
    world_t: int,
    west_report: dict[str, Any],
    east_report: dict[str, Any],
) -> None:
    west_rec = west_report["reconciliation"]
    west_rank = west_report["rank_analysis"]
    east_one = east_report["reconciliation_visit_one"]
    east_two = east_report["reconciliation_visit_two"]
    east_all = east_report["reconciliation_all"]
    east_rank = east_report["rank_analysis"]

    print(f"scenario={SCENARIO_NAME}")
    print(f"world_T={world_t}")
    print(
        "west expected="
        f"{west_rec['expected_count']} "
        f"confirmed={west_rec['confirmed_count']} "
        f"undetermined={west_rec['undetermined_count']}"
    )
    print(
        "west missing_unregistered="
        f"{west_rec['missing_unregistered_count']} "
        f"unexpected_confirmed={west_rec['unexpected_confirmed_count']} "
        f"unexpected_undetermined={west_rec['unexpected_undetermined_count']}"
    )
    print(
        "west rank min="
        f"{west_rank['minimum_assigned_rank']} "
        f"max={west_rank['maximum_assigned_rank']}"
    )
    print(
        "west missing_ranks="
        f"{len(west_rank['missing_assigned_ranks'])} "
        f"duplicate_ranks={len(west_rank['duplicate_assigned_ranks'])}"
    )
    print(f"west duplicate_VisitKeys={len(west_rank['duplicate_visit_keys'])}")
    print(
        "west continuity="
        f"{west_rank['assigned_rank_sequence_is_continuous']}"
    )

    print(
        "east VisitID=1 expected="
        f"{east_one['expected_count']} "
        f"confirmed={east_one['confirmed_count']} "
        f"undetermined={east_one['undetermined_count']} "
        f"missing={east_one['missing_unregistered_count']}"
    )
    print(
        "east VisitID=2 expected="
        f"{east_two['expected_count']} "
        f"confirmed={east_two['confirmed_count']} "
        f"undetermined={east_two['undetermined_count']} "
        f"missing={east_two['missing_unregistered_count']}"
    )
    print(
        "east total expected="
        f"{east_all['expected_count']} "
        f"confirmed={east_all['confirmed_count']} "
        f"undetermined={east_all['undetermined_count']}"
    )
    print(
        "east unexpected_confirmed="
        f"{east_all['unexpected_confirmed_count']} "
        f"unexpected_undetermined={east_all['unexpected_undetermined_count']}"
    )
    print(
        "east rank min="
        f"{east_rank['minimum_assigned_rank']} "
        f"max={east_rank['maximum_assigned_rank']}"
    )
    print(
        "east missing_ranks="
        f"{len(east_rank['missing_assigned_ranks'])} "
        f"duplicate_ranks={len(east_rank['duplicate_assigned_ranks'])}"
    )
    print(f"east duplicate_VisitKeys={len(east_rank['duplicate_visit_keys'])}")
    print(
        "east continuity="
        f"{east_rank['assigned_rank_sequence_is_continuous']}"
    )
    print("final_overall_status=passed")


def audit_world_rank_ledgers(world) -> None:
    west_expected = build_west_expected_visit_keys(trial.VEHICLE_SPECS)
    east_visit_one_expected = build_east_visit_one_expected_visit_keys(trial.VEHICLE_SPECS)
    east_visit_two_expected = build_east_visit_two_expected_visit_keys(trial.VEHICLE_SPECS)

    west_export = export_node_rank_ledger(world, WEST_NODE_NAME)
    east_export = export_node_rank_ledger(world, EAST_NODE_NAME)

    west_report = audit_west_ledger(west_export, west_expected)
    east_report = audit_east_ledger(
        east_export,
        east_visit_one_expected,
        east_visit_two_expected,
    )

    world_t = world.T
    print_report(world_t, west_report, east_report)
    print("Node rank ledger continuity diagnostic passed.")


def main() -> int:
    reference = trial.reference
    original_recursion_limit = sys.getrecursionlimit()
    try:
        if original_recursion_limit < reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(reference.WORLD_COPY_RECURSION_LIMIT)
        validate_static_contract()
        trial.validate_static_contract()
        world = prepare_world()
        run_simulation_once(world)
        audit_world_rank_ledgers(world)
        return 0
    finally:
        sys.setrecursionlimit(original_recursion_limit)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
        print("Static contract validation passed.")
    else:
        raise SystemExit(main())
