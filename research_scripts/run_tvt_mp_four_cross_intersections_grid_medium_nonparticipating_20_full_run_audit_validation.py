"""
Four-cross 600-vehicle nonparticipating 20% trial with full-run audit helper attached.

Same network, vehicle plan, seeds, VOT, and evaluation as
run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial.py.
Adds research_scripts/tvt_mp_full_run_audit_helper.py and writes audit CSVs
for buyer, seller, and nonparticipating roles.

Run from the repository root:

    python research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_full_run_audit_validation.py --static-validate-only
    python research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_full_run_audit_validation.py
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import sys
import time
from dataclasses import dataclass
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
import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial as base_trial
from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

from tvt_mp_full_run_audit_helper import (  # noqa: E402
    TRANSACTION_AUDIT_CSV_NAME,
    VISIT_AUDIT_CSV_NAME,
    finalize_tvt_mp_full_run_audit,
    install_tvt_mp_full_run_audit,
    write_tvt_mp_full_run_audit_csv,
)

SCENARIO_NAME = (
    "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
    "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
    "full_run_audit_validation"
)
WORLD_DISPLAY_NAME = base_trial.WORLD_DISPLAY_NAME
TRIAL_OUTPUT_DIR = reference.TRIAL_PARENT / SCENARIO_NAME

BASE_NP_TRIAL_OUTPUT_DIR_NAME = base_trial.TRIAL_OUTPUT_DIR_NAME

NONPARTICIPATION_SEED = base_trial.NONPARTICIPATION_SEED
NONPARTICIPATING_VEHICLE_NAMES = base_trial.NONPARTICIPATING_VEHICLE_NAMES
VEHICLE_SPECS = base_trial.VEHICLE_SPECS
EXPECTED_TOTAL_VEHICLE_COUNT = base_trial.EXPECTED_TOTAL_VEHICLE_COUNT
EXPECTED_PARTICIPATING_COUNT = base_trial.EXPECTED_PARTICIPATING_COUNT
EXPECTED_NONPARTICIPATING_COUNT = base_trial.EXPECTED_NONPARTICIPATING_COUNT

FULL_RUN_AUDIT_CSV_NAMES = (
    TRANSACTION_AUDIT_CSV_NAME,
    VISIT_AUDIT_CSV_NAME,
)

AUXILIARY_FILE_NAMES = base_trial.AUXILIARY_FILE_NAMES


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


@dataclass(frozen=True)
class FullRunAuditSummary:
    transaction_row_count: int
    visit_row_count: int
    buyer_row_count: int
    seller_row_count: int
    nonparticipating_row_count: int
    actual_arrival_row_count: int
    fifo_violation_total: int
    max_same_inlink_party_count: int
    max_same_inlink_buyer_count: int
    max_same_inlink_seller_count: int
    max_same_inlink_nonparticipating_count: int
    validation_passed: bool
    transaction_csv_sha256: str
    visit_csv_sha256: str


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


def _assert_main_source_contract(source_text: str) -> None:
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


def _assert_validate_static_contract_body(source_text: str) -> None:
    tree = ast.parse(source_text)
    static_function = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "validate_static_contract":
            static_function = node
            break
    if static_function is None:
        raise RuntimeError("validate_static_contract is missing.")
    for node in ast.walk(static_function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "exec_simulation":
                raise RuntimeError("Static validation must not call exec_simulation.")
            if node.func.attr == "build_tvt_mp_research_output":
                raise RuntimeError("Static validation must not build research output.")
            if node.func.attr == "mkdir":
                raise RuntimeError("Static validation must not create directories.")
            if node.func.attr == "build_world_and_network":
                raise RuntimeError(
                    "Static validation must not build the World network."
                )


def validate_static_contract() -> None:
    expected_scenario = (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "full_run_audit_validation"
    )
    if SCENARIO_NAME != expected_scenario:
        raise RuntimeError("Unexpected SCENARIO_NAME for full-run audit validation.")
    if TRIAL_OUTPUT_DIR.name != SCENARIO_NAME:
        raise RuntimeError("TRIAL_OUTPUT_DIR name must match SCENARIO_NAME.")

    if NONPARTICIPATION_SEED != 3:
        raise RuntimeError("Nonparticipation seed must be 3.")
    if len(VEHICLE_SPECS) != 600:
        raise RuntimeError("VEHICLE_SPECS length must be 600.")
    participating_count = 0
    nonparticipating_count = 0
    for spec in VEHICLE_SPECS:
        if spec.participating is True:
            participating_count = participating_count + 1
        elif spec.participating is False:
            nonparticipating_count = nonparticipating_count + 1
        else:
            raise RuntimeError(
                f"{spec.vehicle_name} participating flag is {spec.participating!r}."
            )
    if participating_count != EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_PARTICIPATING_COUNT} participating vehicles, "
            f"got {participating_count}."
        )
    if nonparticipating_count != EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_NONPARTICIPATING_COUNT} nonparticipating vehicles, "
            f"got {nonparticipating_count}."
        )
    if participating_count + nonparticipating_count != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("Participating and nonparticipating counts do not sum to 600.")

    if reference.EVALUATION_END_TIMESTEP != 899:
        raise RuntimeError("Reference evaluation end must be T=899.")
    if reference.VOT_SEED != 1:
        raise RuntimeError("Reference VOT seed must be 1.")
    if reference.MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError("Reference candidate visit limit must be 10.")
    if reference.BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError("Reference baseline horizon must be 30.")
    if reference.CLEARANCE_TIMESTEPS != 1:
        raise RuntimeError("Reference clearance must be 1.")
    if len(reference.TVT_MP_NODE_NAMES) != 4:
        raise RuntimeError("Reference must use four TVT-MP intersections.")

    if SCENARIO_NAME == base_trial.SCENARIO_NAME:
        raise RuntimeError("Scenario name collides with the base nonparticipating trial.")
    if TRIAL_OUTPUT_DIR.name == BASE_NP_TRIAL_OUTPUT_DIR_NAME:
        raise RuntimeError("Output directory collides with the base nonparticipating trial.")
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}."
        )

    if base_trial._sample_nonparticipating_names() != NONPARTICIPATING_VEHICLE_NAMES:
        raise RuntimeError(
            "Embedded nonparticipating list does not match participation seed 3."
        )

    true_vot = base_trial._true_vot_sequence()
    records = base_trial.build_vehicle_vot_records(VEHICLE_SPECS, true_vot)
    if len(records) != EXPECTED_TOTAL_VEHICLE_COUNT:
        raise RuntimeError("VOT record count must be 600.")

    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    _assert_main_source_contract(source_text)
    _assert_validate_static_contract_body(source_text)

    if "verify_full_run_audit_output" not in source_text:
        raise RuntimeError("Missing post-run audit verification function.")
    if "nonparticipating_row_count" not in source_text:
        raise RuntimeError("Missing nonparticipating audit row validation.")


def refuse_existing_trial_output_directory() -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Trial output directory already exists: {TRIAL_OUTPUT_DIR}. "
            "This script does not delete or overwrite existing trial output."
        )


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

    transaction_path = directory / TRANSACTION_AUDIT_CSV_NAME
    visit_path = directory / VISIT_AUDIT_CSV_NAME
    transaction_rows = read_csv_dict_rows(transaction_path)
    visit_rows = read_csv_dict_rows(visit_path)

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

    required_transaction_columns = (
        "buyer_count",
        "seller_count",
        "nonparticipating_count",
        "trade_scope_count",
        "baseline_order_visit_keys",
        "candidate_order_visit_keys",
        "total_G",
        "total_R",
        "surplus",
        "fifo_violation_count",
        "max_same_inlink_party_count",
        "max_same_inlink_buyer_count",
        "max_same_inlink_seller_count",
        "max_same_inlink_nonparticipating_count",
    )
    if transaction_rows:
        header = set(transaction_rows[0].keys())
        for column_name in required_transaction_columns:
            if column_name not in header:
                raise RuntimeError(
                    f"Transaction audit CSV missing column {column_name!r}."
                )

    buyer_row_count = 0
    seller_row_count = 0
    nonparticipating_row_count = 0
    actual_arrival_row_count = 0
    fifo_violation_total = 0
    max_same_inlink_party_count = 0
    max_same_inlink_buyer_count = 0
    max_same_inlink_seller_count = 0
    max_same_inlink_nonparticipating_count = 0

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
        fifo_violation_count = _parse_int_cell(
            row["fifo_violation_count"], "transaction audit", index
        )
        if fifo_violation_count != 0:
            raise RuntimeError(
                f"Transaction audit row {index}: fifo_violation_count is "
                f"{fifo_violation_count}, not 0."
            )
        fifo_violation_total = fifo_violation_total + fifo_violation_count
        party_count = _parse_int_cell(
            row["max_same_inlink_party_count"], "transaction audit", index
        )
        buyer_max = _parse_int_cell(
            row["max_same_inlink_buyer_count"], "transaction audit", index
        )
        seller_max = _parse_int_cell(
            row["max_same_inlink_seller_count"], "transaction audit", index
        )
        nonparticipating_max = _parse_int_cell(
            row["max_same_inlink_nonparticipating_count"],
            "transaction audit",
            index,
        )
        for count_value, count_label in (
            (party_count, "max_same_inlink_party_count"),
            (buyer_max, "max_same_inlink_buyer_count"),
            (seller_max, "max_same_inlink_seller_count"),
            (nonparticipating_max, "max_same_inlink_nonparticipating_count"),
        ):
            if count_value < 0:
                raise RuntimeError(
                    f"Transaction audit row {index}: {count_label} is negative."
                )
        if party_count > max_same_inlink_party_count:
            max_same_inlink_party_count = party_count
        if buyer_max > max_same_inlink_buyer_count:
            max_same_inlink_buyer_count = buyer_max
        if seller_max > max_same_inlink_seller_count:
            max_same_inlink_seller_count = seller_max
        if nonparticipating_max > max_same_inlink_nonparticipating_count:
            max_same_inlink_nonparticipating_count = nonparticipating_max

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
            for blank_name in (
                "buyer_value_G_b",
                "seller_required_compensation_R_s",
                "payment_P_b",
                "compensation_C_s",
            ):
                if row[blank_name] != "":
                    raise RuntimeError(
                        f"Visit audit nonparticipating row {index}: "
                        f"{blank_name} must be blank."
                    )
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
            actual_arrival_row_count = actual_arrival_row_count + 1
        if actual_passage is not None:
            if actual_arrival is not None and actual_passage < actual_arrival + 1:
                raise RuntimeError(
                    f"Visit audit row {index}: actual_passage_timestep "
                    f"{actual_passage} is before actual_node_arrival_timestep "
                    f"{actual_arrival} + 1."
                )

    if buyer_row_count < 1:
        raise RuntimeError("Visit audit must contain at least one buyer row.")
    if seller_row_count < 1:
        raise RuntimeError("Visit audit must contain at least one seller row.")
    if nonparticipating_row_count < 1:
        raise RuntimeError("Visit audit must contain at least one nonparticipating row.")

    if bundle.scenario[0].transaction_count != len(transaction_rows):
        raise RuntimeError(
            "Research scenario transaction_count disagrees with audit CSV row count."
        )

    transaction_sha256 = sha256_file(transaction_path)
    visit_sha256 = sha256_file(visit_path)

    return FullRunAuditSummary(
        transaction_row_count=len(transaction_rows),
        visit_row_count=len(visit_rows),
        buyer_row_count=buyer_row_count,
        seller_row_count=seller_row_count,
        nonparticipating_row_count=nonparticipating_row_count,
        actual_arrival_row_count=actual_arrival_row_count,
        fifo_violation_total=fifo_violation_total,
        max_same_inlink_party_count=max_same_inlink_party_count,
        max_same_inlink_buyer_count=max_same_inlink_buyer_count,
        max_same_inlink_seller_count=max_same_inlink_seller_count,
        max_same_inlink_nonparticipating_count=max_same_inlink_nonparticipating_count,
        validation_passed=True,
        transaction_csv_sha256=transaction_sha256,
        visit_csv_sha256=visit_sha256,
    )


def write_manifest_json(
    path: Path,
    timing: TimingRecord,
    world,
    generated_files: list[str],
    spillback_summary_by_link: dict[str, dict],
    completion: dict,
    ledger_summary: dict,
    visit_id_summary: dict,
    transactions_by_node: dict[str, int],
    passage_stats: dict,
    original_python_recursion_limit: int,
    audit_summary: FullRunAuditSummary,
) -> None:
    ref_stats = reference.GENERATION_STATS
    manifest = {
        "schema_note": (
            "Four-cross grid medium nonparticipating 20% full-run audit validation."
        ),
        "run_type": "full_run_audit_validation",
        "scenario_name": SCENARIO_NAME,
        "world_display_name": WORLD_DISPLAY_NAME,
        "script_path": str(SCRIPT_PATH),
        "base_nonparticipating_trial_scenario_name": base_trial.SCENARIO_NAME,
        "traffic_seed": reference.TRAFFIC_SEED,
        "vot_seed": reference.VOT_SEED,
        "nonparticipation_seed": NONPARTICIPATION_SEED,
        "vehicle_count": EXPECTED_TOTAL_VEHICLE_COUNT,
        "participating_count": EXPECTED_PARTICIPATING_COUNT,
        "nonparticipating_count": EXPECTED_NONPARTICIPATING_COUNT,
        "evaluation_start_timestep": reference.EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": reference.EVALUATION_END_TIMESTEP,
        "full_run_audit_enabled": True,
        "full_run_audit_validation": True,
        "audit_validation_participation_mode": "nonparticipating_20_percent",
        "full_run_audit_transaction_row_count": audit_summary.transaction_row_count,
        "full_run_audit_visit_row_count": audit_summary.visit_row_count,
        "full_run_audit_buyer_row_count": audit_summary.buyer_row_count,
        "full_run_audit_seller_row_count": audit_summary.seller_row_count,
        "full_run_audit_nonparticipating_row_count": (
            audit_summary.nonparticipating_row_count
        ),
        "full_run_audit_actual_arrival_row_count": (
            audit_summary.actual_arrival_row_count
        ),
        "full_run_audit_fifo_violation_total": audit_summary.fifo_violation_total,
        "full_run_audit_max_same_inlink_party_count": (
            audit_summary.max_same_inlink_party_count
        ),
        "full_run_audit_max_same_inlink_buyer_count": (
            audit_summary.max_same_inlink_buyer_count
        ),
        "full_run_audit_max_same_inlink_seller_count": (
            audit_summary.max_same_inlink_seller_count
        ),
        "full_run_audit_max_same_inlink_nonparticipating_count": (
            audit_summary.max_same_inlink_nonparticipating_count
        ),
        "full_run_audit_transaction_csv_sha256": audit_summary.transaction_csv_sha256,
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
        "transaction_count": passage_stats["transaction_count"],
        "base_vehicle_count": ref_stats.base_vehicle_count,
        "pulse_vehicle_count": ref_stats.pulse_vehicle_count,
        "transactions_by_node": transactions_by_node,
        "completed_trip_count": completion["completed_trip_count"],
        "internal_spillback_summary_by_link": spillback_summary_by_link,
        "node_rank_ledger_summary": ledger_summary,
        "visit_id_summary": visit_id_summary,
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
    passage_stats: dict,
    audit_summary: FullRunAuditSummary,
    generated_files: list[str],
) -> None:
    lines = [
        "TVT-MP four-cross grid medium nonparticipating 20% full-run audit validation",
        "=" * 70,
        "Audit helper attached: yes (tvt_mp_full_run_audit_helper.py)",
        f"Scenario name: {SCENARIO_NAME}",
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
        f"{audit_summary.actual_arrival_row_count}",
        f"Same-inlink max party count: {audit_summary.max_same_inlink_party_count}",
        f"Same-inlink max buyer count: {audit_summary.max_same_inlink_buyer_count}",
        f"Same-inlink max seller count: {audit_summary.max_same_inlink_seller_count}",
        "Same-inlink max nonparticipating count: "
        f"{audit_summary.max_same_inlink_nonparticipating_count}",
        f"FIFO violation total: {audit_summary.fifo_violation_total}",
        "",
        f"Research transaction count: {bundle.scenario[0].transaction_count}",
        f"Research buyer visits: {passage_stats['buyer_visit_count']}",
        f"Research seller visits: {passage_stats['seller_visit_count']}",
        f"Research nonparticipating visits: "
        f"{passage_stats['nonparticipating_visit_count']}",
        "",
        "Generated files:",
    ]
    for name in generated_files:
        lines.append(f"  - {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_console_summary(
    bundle,
    passage_stats: dict,
    timing: TimingRecord,
    output_dir: Path,
    audit_summary: FullRunAuditSummary,
) -> None:
    print()
    print("=== Four-cross 600-vehicle full-run audit validation (20% NP) ===")
    print()
    print(f"Scenario: {SCENARIO_NAME}")
    print(f"Transactions (research): {bundle.scenario[0].transaction_count}")
    print(f"Transaction audit rows: {audit_summary.transaction_row_count}")
    print(f"Visit audit rows: {audit_summary.visit_row_count}")
    print(f"Buyer / seller / NP audit rows: "
          f"{audit_summary.buyer_row_count} / "
          f"{audit_summary.seller_row_count} / "
          f"{audit_summary.nonparticipating_row_count}")
    print(f"Actual arrival saved rows: {audit_summary.actual_arrival_row_count}")
    print(f"FIFO violation total: {audit_summary.fifo_violation_total}")
    print(f"Same-inlink max party: {audit_summary.max_same_inlink_party_count}")
    print("Audit CSV validation: passed")
    print(f"Timing total (s): {timing.script_total_s:.3f}")
    print(f"Output: {output_dir}")
    print()


def main() -> int:
    script_start = time.perf_counter()
    timing = TimingRecord()
    reference.SPILLBACK_TIMESTEP_ROWS.clear()
    original_python_recursion_limit = sys.getrecursionlimit()
    try:
        if original_python_recursion_limit < reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(reference.WORLD_COPY_RECURSION_LIMIT)

        validate_static_contract()
        reference.ensure_trial_parent_directories()
        refuse_existing_trial_output_directory()
        TRIAL_OUTPUT_DIR.mkdir(parents=False, exist_ok=False)

        vot_values = base_trial._true_vot_sequence()
        vot_records = base_trial.build_vehicle_vot_records(VEHICLE_SPECS, vot_values)

        t0 = time.perf_counter()
        world = base_trial.build_world()
        base_trial.add_vehicles_to_world(world, VEHICLE_SPECS, vot_records)
        base_trial.verify_world_participation(world, vot_records)
        timing.world_build_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        world.finalize_scenario()
        timing.finalize_s = time.perf_counter() - t0
        if world.TSIZE != reference.INTERNAL_TSIZE:
            raise RuntimeError(
                f"Expected TSIZE=={reference.INTERNAL_TSIZE}, got {world.TSIZE}."
            )

        install_tvt_mp_full_run_audit(world)

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

        t0 = time.perf_counter()
        audit_result = finalize_tvt_mp_full_run_audit(world, bundle)
        timing.audit_finalize_s = time.perf_counter() - t0

        passage_stats = base_trial.passage_comparison(bundle)
        transactions_by_node = reference.collect_transaction_counts_by_node(bundle)

        t0 = time.perf_counter()
        write_tvt_mp_research_output_csv(bundle, TRIAL_OUTPUT_DIR, overwrite=False)
        timing.csv_write_s = time.perf_counter() - t0
        for name in reference.RESEARCH_CSV_NAMES:
            if not (TRIAL_OUTPUT_DIR / name).is_file():
                raise RuntimeError(f"Missing research CSV {name}.")

        t0 = time.perf_counter()
        write_tvt_mp_full_run_audit_csv(audit_result, TRIAL_OUTPUT_DIR)
        timing.audit_csv_write_s = time.perf_counter() - t0

        verify_audit_csv_files_exist(TRIAL_OUTPUT_DIR)
        audit_summary = verify_full_run_audit_output(
            TRIAL_OUTPUT_DIR,
            bundle,
            audit_result,
        )

        generated_files = (
            list(reference.RESEARCH_CSV_NAMES)
            + list(FULL_RUN_AUDIT_CSV_NAMES)
            + list(AUXILIARY_FILE_NAMES)
        )

        t0 = time.perf_counter()
        base_trial.write_vehicle_vot_csv(
            TRIAL_OUTPUT_DIR / "vehicle_vot.csv",
            vot_records,
        )
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
            audit_summary,
        )
        write_run_summary_txt(
            TRIAL_OUTPUT_DIR / "run_summary.txt",
            world,
            bundle,
            passage_stats,
            audit_summary,
            generated_files,
        )

        expected_names = set(generated_files)
        for path in TRIAL_OUTPUT_DIR.iterdir():
            if path.name not in expected_names:
                raise RuntimeError(f"Unexpected file in output directory: {path.name}.")

        print_console_summary(
            bundle,
            passage_stats,
            timing,
            TRIAL_OUTPUT_DIR,
            audit_summary,
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
            source = SCRIPT_PATH.read_text(encoding="utf-8")
            ast.parse(source)
            compile(source, str(SCRIPT_PATH), "exec")
            print("Static contract validation passed.", file=sys.stderr)
            raise SystemExit(0)
        raise SystemExit(f"Unknown CLI option: {sys.argv[1]!r}")
    raise SystemExit(main())
