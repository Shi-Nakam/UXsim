"""
T=0..299 validation after sharing one real-World snapshot between the
baseline fork and the Candidate set.

Conditions match the existing shared-serialization validation. That script
and its saved output are not modified. This script reads the saved CSV
files only to compare them, excluding the scenario_name column.

Full-completion acceptance is a later Terminal run. Do not treat a passing
result here as permission to commit.

Run from the repository root:

    python research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_baseline_candidate_shared_snapshot_validation.py --static-validate-only
    python research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_baseline_candidate_shared_snapshot_validation.py
"""

from __future__ import annotations

import ast
import csv
import importlib.util
import json
import sys
import time
from pathlib import Path

from uxsim.order_control_tvt_mp_research_output import (
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)

SCENARIO_NAME = (
    "tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_"
    "baseline_candidate_shared_snapshot_validation_"
    "candidate_limit_10_seed_0_vot_seed_1"
)
REFERENCE_SCRIPT_NAME = (
    "run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_"
    "shared_serialization_validation.py"
)
REFERENCE_MODULE_NAME = "tvt_mp_eval_300_shared_serialization_reference"
RESEARCH_CSV_NAMES = (
    "tvt_mp_transactions.csv",
    "tvt_mp_visits.csv",
    "tvt_mp_vehicles.csv",
    "tvt_mp_nodes.csv",
    "tvt_mp_scenario.csv",
    "vehicle_vot.csv",
)
CSV_COLUMNS_IGNORED = ("scenario_name",)
EXPECTED_TRANSACTION_COUNT = 816
EXPECTED_WORLD_T = 300
WORLD_COPY_RECURSION_LIMIT = 50000

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "research_outputs" / "trial" / SCENARIO_NAME


def _load_reference_module():
    path = Path(__file__).resolve().parent / REFERENCE_SCRIPT_NAME
    module_name = REFERENCE_MODULE_NAME
    resolved_path = path.resolve()
    if module_name in sys.modules:
        existing = sys.modules[module_name]
        existing_file = getattr(existing, "__file__", None)
        if existing_file is None:
            raise RuntimeError(
                f"sys.modules[{module_name!r}] is already registered without __file__."
            )
        if Path(existing_file).resolve() != resolved_path:
            raise RuntimeError(
                "sys.modules contains a different module under "
                f"{module_name!r}: {existing_file!r}."
            )
        return existing
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load reference script: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames), list(reader)


def _compare_csv(reference_dir: Path, current_dir: Path, filename: str) -> None:
    reference_path = reference_dir / filename
    current_path = current_dir / filename
    if not reference_path.is_file():
        raise RuntimeError(f"Reference CSV is missing: {reference_path}")
    if not current_path.is_file():
        raise RuntimeError(f"Current CSV is missing: {current_path}")
    reference_header, reference_rows = _read_csv(reference_path)
    current_header, current_rows = _read_csv(current_path)
    if reference_header != current_header:
        raise RuntimeError(
            f"{filename} headers differ. reference={reference_header!r} "
            f"current={current_header!r}"
        )
    if len(reference_rows) != len(current_rows):
        raise RuntimeError(
            f"{filename} row count differs. reference={len(reference_rows)} "
            f"current={len(current_rows)}"
        )
    compared = [
        name for name in reference_header if name not in CSV_COLUMNS_IGNORED
    ]
    for row_index, (reference_row, current_row) in enumerate(
        zip(reference_rows, current_rows)
    ):
        for column in compared:
            if reference_row[column] != current_row[column]:
                raise RuntimeError(
                    f"{filename} differs at row {row_index}, column {column!r}. "
                    f"reference={reference_row[column]!r} current={current_row[column]!r} "
                    f"timestep={current_row.get('tvt_decision_timestep')!r} "
                    f"node={current_row.get('node_name')!r} "
                    f"vehicle={current_row.get('vehicle_name')!r} "
                    f"visit={current_row.get('visit_id')!r}"
                )


def _run_validation() -> int:
    if OUTPUT_DIR.exists():
        raise RuntimeError(
            f"Output directory already exists: {OUTPUT_DIR}. "
            "Rename or remove it manually before re-running."
        )
    reference = _load_reference_module()
    reference_output_dir = reference.TRIAL_OUTPUT_DIR
    if reference_output_dir == OUTPUT_DIR:
        raise RuntimeError("This script must not write the reference output directory.")
    reference.SCENARIO_NAME = SCENARIO_NAME

    original_recursion_limit = sys.getrecursionlimit()
    script_started = time.perf_counter()
    try:
        if original_recursion_limit < WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(WORLD_COPY_RECURSION_LIMIT)
        plans = reference.generate_vehicle_plans()
        plan_audit = reference.verify_vehicle_plans(plans)
        vot_values = reference.generate_vehicle_vots(reference.NUM_VEHICLES)
        vot_records = reference.build_vehicle_vot_records(plans, vot_values)
        world = reference.build_world_and_network()
        reference.verify_network_runtime(world)
        reference.add_vehicles_to_world(world, vot_records)
        started = time.perf_counter()
        world.exec_simulation()
        exec_simulation_seconds = time.perf_counter() - started
        reference.verify_evaluation_end(world)
        if world.T != EXPECTED_WORLD_T:
            raise RuntimeError(f"World.T is {world.T!r}, expected {EXPECTED_WORLD_T}.")
        vehicle_summary = reference.collect_evaluation_end_vehicle_summary(world, plans)
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        transaction_count = bundle.scenario[0].transaction_count
        transactions_by_node = reference.collect_transaction_counts_by_node(bundle)
        reference.verify_research_results_match_reference(
            plan_audit,
            vehicle_summary,
            transaction_count,
            transactions_by_node,
        )
        if transaction_count != EXPECTED_TRANSACTION_COUNT:
            raise RuntimeError(
                f"transaction_count is {transaction_count}, "
                f"expected {EXPECTED_TRANSACTION_COUNT}."
            )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
        write_tvt_mp_research_output_csv(bundle, OUTPUT_DIR, overwrite=False)
        reference.write_vehicle_vot_csv(OUTPUT_DIR / "vehicle_vot.csv", vot_records)
        for filename in RESEARCH_CSV_NAMES:
            _compare_csv(reference_output_dir, OUTPUT_DIR, filename)
    finally:
        sys.setrecursionlimit(original_recursion_limit)

    script_seconds = time.perf_counter() - script_started
    seconds_per_timestep = exec_simulation_seconds / reference.SIMULATED_EVALUATION_TIMESTEPS
    manifest = {
        "scenario_name": SCENARIO_NAME,
        "reference_output_directory": str(reference_output_dir),
        "exec_simulation_seconds": exec_simulation_seconds,
        "script_total_seconds": script_seconds,
        "seconds_per_evaluation_timestep": seconds_per_timestep,
        "transaction_count": transaction_count,
        "final_world_T": world.T,
        "vehicle_state_counts": vehicle_summary["vehicle_state_counts"],
        "csv_equality_excluding_scenario_name": True,
        "research_result_equality_checks_passed": True,
        "profiling": False,
        "full_completion": False,
        "formal_acceptance": False,
        "formal_acceptance_note": (
            "Passing this T=0..299 validation does not accept the production "
            "change. Commit only after the existing 3000-vehicle, 20 percent "
            "nonparticipating, full-completion trial matches the saved result "
            "on transactions, visits, ranks, candidates, payments, passages, "
            "vehicles, final time, research CSV, and audit CSV. Execution time, "
            "scenario name, manifest timestamps, and file hashes may differ."
        ),
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    summary_path = OUTPUT_DIR / "run_summary.txt"
    summary_lines = [
        f"scenario: {SCENARIO_NAME}",
        f"exec_simulation seconds: {exec_simulation_seconds}",
        f"script total seconds: {script_seconds}",
        f"seconds per evaluation timestep: {seconds_per_timestep}",
        f"transactions: {transaction_count}",
        f"final World.T: {world.T}",
        f"vehicle state counts: {vehicle_summary['vehicle_state_counts']}",
        "csv equality excluding scenario_name: true",
        "formal acceptance: false until the 20 percent nonparticipating full-completion trial matches",
    ]
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines))
        handle.write("\n")
    print("exec_simulation seconds:", exec_simulation_seconds)
    print("transactions:", transaction_count)
    print("final World.T:", world.T)
    print("csv equality excluding scenario_name: true")
    print("output directory:", OUTPUT_DIR)
    return 0


def static_validate() -> int:
    expected_reference_script_name = (
        "run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_"
        "shared_serialization_validation.py"
    )
    if not isinstance(REFERENCE_SCRIPT_NAME, str):
        raise RuntimeError("REFERENCE_SCRIPT_NAME must be a str.")
    if not REFERENCE_SCRIPT_NAME:
        raise RuntimeError("REFERENCE_SCRIPT_NAME must not be empty.")
    if REFERENCE_SCRIPT_NAME != expected_reference_script_name:
        raise RuntimeError(
            "REFERENCE_SCRIPT_NAME must equal "
            f"{expected_reference_script_name!r}; got {REFERENCE_SCRIPT_NAME!r}."
        )
    if REFERENCE_SCRIPT_NAME == Path(__file__).name:
        raise RuntimeError("REFERENCE_SCRIPT_NAME must not point to this script.")
    reference_script_path = Path(__file__).resolve().parent / REFERENCE_SCRIPT_NAME
    if not reference_script_path.is_file():
        raise RuntimeError(
            f"Reference validation script is missing: {reference_script_path}"
        )

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    if str(EXPECTED_TRANSACTION_COUNT) not in source:
        raise RuntimeError("Expected transaction count 816 is missing.")
    if "exec_simulation" not in source:
        raise RuntimeError("exec_simulation is missing.")
    if SCENARIO_NAME in REFERENCE_SCRIPT_NAME:
        raise RuntimeError("This scenario name must differ from the reference script.")
    load_marker = "def _load_reference_module"
    load_start = source.index(load_marker)
    load_end = source.index("\ndef _read_csv", load_start)
    load_source = source[load_start:load_end]
    if "sys.modules[" not in load_source:
        raise RuntimeError("sys.modules registration is missing in _load_reference_module.")
    if "sys.modules.pop" not in load_source:
        raise RuntimeError(
            "sys.modules cleanup on load failure is missing in _load_reference_module."
        )
    modules_idx = load_source.index("sys.modules[")
    exec_idx = load_source.index("exec_module")
    if modules_idx > exec_idx:
        raise RuntimeError(
            "sys.modules must be registered before exec_module in _load_reference_module."
        )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "git":
                raise RuntimeError("This script must not call git.")
    print("static validation passed")
    return 0


def main() -> int:
    if "--static-validate-only" in sys.argv:
        return static_validate()
    return _run_validation()


if __name__ == "__main__":
    sys.exit(main())
