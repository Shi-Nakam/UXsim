# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Short-TMAX global-World baseline performance probe for TVT research.
# Measures World.copy() plus exec_simulation() on a copied World while the
# BATCH Level 2 estimator is temporarily replaced with the diagnostic-only
# short-TMAX reference model:
#   diagnostics/order_control/order_control_batch_level_2_short_tmax_reference.py
#
# The canonical Level 2 reference (uxsim/order_control_batch_level_2_reference.py)
# is NOT modified. During each fork forward only, the module attribute
# uxsim.order_control_batch_level_2_reference
#     .estimate_order_control_batch_t_trigger_level_2_reference
# is swapped to the short-TMAX diagnostic function and restored in finally.
#
# Measures forward horizons 6, 30, and 50 timesteps on the Analyzer-attached
# normal exec_simulation() path. Vehicle logging is stopped on the fork only
# (vehicle_logging_timestep_interval=-1) after copy and before forward.
#
# Does NOT reproduce TVT institutional logic, baseline predicted arrival/passage
# recording, or unresolved-rate measurement. Global-World baseline predictions
# may later be reused for both TVT and BATCH candidate selection, but those
# changes are out of scope here.
#
# Keeps tvt_global_baseline_performance.py unchanged as the official-baseline
# performance probe.
#
# Run from repository root:
#   python diagnostics/order_control/tvt_global_baseline_short_tmax_performance.py

from __future__ import annotations

import gc
import importlib.util
import math
import pickle
import statistics
import sys
import time
from pathlib import Path

N_REPEATS = 3
FORWARD_STEPS = (
    6,
    30,
    50,
)
RECURSION_LIMIT = 50000

LEVEL2_MODE = "short_tmax_diagnostic"


def _load_module(module_name: str, filename: str):
    module_path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Failed to load {filename}")
    spec.loader.exec_module(module)
    return module


def _load_grid_level_1_vs_level_2_module():
    return _load_module(
        "grid_level_1_vs_level_2_check",
        "grid_level_1_vs_level_2_check.py",
    )


def _load_world_state_branching_module():
    return _load_module(
        "world_state_branching_investigation",
        "world_state_branching_investigation.py",
    )


def _load_short_tmax_reference_module():
    return _load_module(
        "order_control_batch_level_2_short_tmax_reference",
        "order_control_batch_level_2_short_tmax_reference.py",
    )


def _get_short_tmax_estimate():
    short_mod = _load_short_tmax_reference_module()
    return short_mod.estimate_order_control_batch_t_trigger_level_2_reference


def _patch_level2_reference(estimate_fn):
    import uxsim.order_control_batch_level_2_reference as l2_module

    original = l2_module.estimate_order_control_batch_t_trigger_level_2_reference
    l2_module.estimate_order_control_batch_t_trigger_level_2_reference = estimate_fn
    return l2_module, original


def _restore_level2_reference(l2_module, original):
    l2_module.estimate_order_control_batch_t_trigger_level_2_reference = original


def _rng_state_bytes(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


def _rng_states_unchanged(before: bytes, after: bytes) -> bool:
    return before == after


def _summarize_times(samples):
    return {
        "samples": list(samples),
        "median": statistics.median(samples),
        "min": min(samples),
        "max": max(samples),
    }


def _print_time_summary(label, summary):
    print(f"{label}:")
    for index, sample in enumerate(summary["samples"], start=1):
        print(f"  run {index}: {sample:.6f} s")
    print(f"  median: {summary['median']:.6f} s")
    print(f"  min: {summary['min']:.6f} s")
    print(f"  max: {summary['max']:.6f} s")


def _snapshot_all_match(comparison_results):
    return all(item["match"] for item in comparison_results)


def _format_comparison_mismatches(comparison_results):
    lines = []
    for item in comparison_results:
        if item["match"]:
            continue
        lines.append(
            f"category={item['category']} mismatches={item['mismatches']}"
        )
        for example in item["examples"]:
            lines.append(f"  example: {example}")
    return lines


def _format_integrity_failures(checks):
    lines = []
    for item in checks:
        if item["bad_count"] == 0:
            continue
        lines.append(
            f"category={item['category']} bad_count={item['bad_count']}"
        )
        for example in item["examples"]:
            lines.append(f"  example: {example}")
    return lines


def _pick_representatives(W):
    node = sorted(W.NODES, key=lambda item: item.name)[0]
    link = sorted(W.LINKS, key=lambda item: item.name)[0]
    vehicle = sorted(W.VEHICLES.values(), key=lambda item: item.name)[0]
    return node, link, vehicle


def _check_explicit_reference_independence(original_W, fork_W, branch_mod):
    rep_node, rep_link, rep_vehicle = _pick_representatives(original_W)
    fork_rep_node = fork_W.get_node(rep_node.name)
    fork_rep_link = fork_W.get_link(rep_link.name)
    fork_rep_vehicle = fork_W.VEHICLES[rep_vehicle.name]

    checks = [
        ("World", original_W is not fork_W),
        ("representative Node", rep_node is not fork_rep_node),
        ("representative Link", rep_link is not fork_rep_link),
        ("representative Vehicle", rep_vehicle is not fork_rep_vehicle),
        (
            "Analyzer",
            hasattr(original_W, "analyzer")
            and hasattr(fork_W, "analyzer")
            and original_W.analyzer is not fork_W.analyzer,
        ),
        ("W.rng", original_W.rng is not fork_W.rng),
        (
            "W.order_control_rng",
            original_W.order_control_rng is not fork_W.order_control_rng,
        ),
    ]

    integrity_checks = branch_mod._check_fork_reference_integrity(
        fork_W, original_W
    )
    integrity_ok = all(item["bad_count"] == 0 for item in integrity_checks)

    explicit_results = []
    explicit_ok = True
    for label, passed in checks:
        explicit_results.append({"label": label, "independent": passed})
        if not passed:
            explicit_ok = False

    return {
        "explicit_results": explicit_results,
        "explicit_ok": explicit_ok,
        "integrity_checks": integrity_checks,
        "integrity_ok": integrity_ok,
        "references_independent": explicit_ok and integrity_ok,
    }


def _fork_has_obvious_state_damage(fork_W):
    for veh in fork_W.VEHICLES.values():
        if math.isnan(float(veh.x)) or math.isnan(float(veh.v)):
            return True, f"Vehicle {veh.name} has NaN state"
    return False, None


def _run_single_measurement(
    real_W,
    branch_mod,
    short_tmax_estimate,
    forward_steps,
    repeat_index,
):
    before_snapshot = branch_mod._world_comparison_snapshot(real_W)
    before_rng = _rng_state_bytes(real_W.rng)
    before_order_control_rng = _rng_state_bytes(real_W.order_control_rng)
    real_t_before = real_W.T

    gc.collect()
    copy_started = time.perf_counter()
    fork_W = real_W.copy()
    copy_seconds = time.perf_counter() - copy_started
    if fork_W is None:
        raise RuntimeError("World.copy() returned None")

    fork_W.vehicle_logging_timestep_interval = -1
    branch_mod._configure_fork(fork_W)
    fork_t_before = fork_W.T
    level2_calls_before = int(fork_W.order_control_batch_level_2_call_count)

    l2_module, original_estimate = _patch_level2_reference(short_tmax_estimate)
    exception_text = None
    return_code = None
    try:
        exec_started = time.perf_counter()
        try:
            return_code = fork_W.exec_simulation(
                duration_t2=forward_steps * fork_W.DELTAT
            )
        except Exception as exc:
            exception_text = repr(exc)
        forward_seconds = time.perf_counter() - exec_started
    finally:
        _restore_level2_reference(l2_module, original_estimate)

    level2_reference_restored = (
        l2_module.estimate_order_control_batch_t_trigger_level_2_reference
        is original_estimate
    )
    level2_calls_after = int(fork_W.order_control_batch_level_2_call_count)
    level2_calls_during_forward = level2_calls_after - level2_calls_before

    advanced_steps = fork_W.T - fork_t_before
    fork_advanced_as_expected = (
        exception_text is None
        and advanced_steps == forward_steps
        and return_code is not None
        and fork_W.T < fork_W.TSIZE
    )

    damage_detected, damage_message = _fork_has_obvious_state_damage(fork_W)
    if damage_detected:
        fork_advanced_as_expected = False

    comparison_results = branch_mod._compare_world_snapshots(
        before_snapshot,
        branch_mod._world_comparison_snapshot(real_W),
    )
    real_world_unchanged = _snapshot_all_match(comparison_results)

    after_rng = _rng_state_bytes(real_W.rng)
    after_order_control_rng = _rng_state_bytes(real_W.order_control_rng)
    real_rng_unchanged = _rng_states_unchanged(before_rng, after_rng)
    real_order_control_rng_unchanged = _rng_states_unchanged(
        before_order_control_rng,
        after_order_control_rng,
    )
    real_t_unchanged = real_W.T == real_t_before

    reference_report = _check_explicit_reference_independence(
        real_W, fork_W, branch_mod
    )

    result = {
        "scenario": "grid5000_batch_level2",
        "level2_mode": LEVEL2_MODE,
        "vehicle_count": branch_mod.GRID_NUM_VEHICLES,
        "branch_timestep": real_W.T,
        "forward_steps": forward_steps,
        "repeat_index": repeat_index,
        "copy_seconds": copy_seconds,
        "forward_seconds": forward_seconds,
        "total_seconds": copy_seconds + forward_seconds,
        "real_world_unchanged": real_world_unchanged and real_t_unchanged,
        "real_rng_unchanged": real_rng_unchanged,
        "real_order_control_rng_unchanged": real_order_control_rng_unchanged,
        "references_independent": reference_report["references_independent"],
        "fork_advanced_as_expected": fork_advanced_as_expected,
        "level2_reference_restored": level2_reference_restored,
        "level2_calls_before": level2_calls_before,
        "level2_calls_after": level2_calls_after,
        "level2_calls_during_forward": level2_calls_during_forward,
        "return_code": return_code,
        "exception": exception_text,
        "advanced_steps": advanced_steps,
        "damage_message": damage_message,
        "comparison_results": comparison_results,
        "reference_report": reference_report,
    }

    del fork_W
    gc.collect()
    return result


def _print_measurement_row(result):
    fields = [
        "scenario",
        "level2_mode",
        "vehicle_count",
        "branch_timestep",
        "forward_steps",
        "repeat_index",
        "copy_seconds",
        "forward_seconds",
        "total_seconds",
        "real_world_unchanged",
        "real_rng_unchanged",
        "real_order_control_rng_unchanged",
        "references_independent",
        "fork_advanced_as_expected",
        "level2_reference_restored",
        "level2_calls_before",
        "level2_calls_after",
        "level2_calls_during_forward",
    ]
    for field in fields:
        print(f"{field}: {result[field]}")


def _assert_measurement_success(result):
    if result["level2_calls_during_forward"] <= 0:
        raise RuntimeError(
            "no Level 2 calls during forward "
            f"(horizon={result['forward_steps']}, "
            f"repeat={result['repeat_index']}): "
            f"before={result['level2_calls_before']}, "
            f"after={result['level2_calls_after']}"
        )
    if not result["level2_reference_restored"]:
        raise RuntimeError(
            "Level 2 reference was not restored to canonical function "
            f"(horizon={result['forward_steps']}, "
            f"repeat={result['repeat_index']})"
        )
    if not result["fork_advanced_as_expected"]:
        raise RuntimeError(
            "fork advance failed "
            f"(horizon={result['forward_steps']}, "
            f"repeat={result['repeat_index']}): "
            f"exception={result['exception']}, "
            f"return_code={result['return_code']}, "
            f"advanced_steps={result['advanced_steps']}, "
            f"damage={result['damage_message']}"
        )
    if not result["real_world_unchanged"]:
        lines = _format_comparison_mismatches(result["comparison_results"])
        raise RuntimeError(
            "real World changed after fork execution "
            f"(horizon={result['forward_steps']}, "
            f"repeat={result['repeat_index']}): "
            + "; ".join(lines)
        )
    if not result["real_rng_unchanged"]:
        raise RuntimeError(
            "real W.rng changed "
            f"(horizon={result['forward_steps']}, repeat={result['repeat_index']})"
        )
    if not result["real_order_control_rng_unchanged"]:
        raise RuntimeError(
            "real W.order_control_rng changed "
            f"(horizon={result['forward_steps']}, repeat={result['repeat_index']})"
        )
    if not result["references_independent"]:
        lines = _format_integrity_failures(
            result["reference_report"]["integrity_checks"]
        )
        failed_explicit = [
            item["label"]
            for item in result["reference_report"]["explicit_results"]
            if not item["independent"]
        ]
        raise RuntimeError(
            "reference independence failed "
            f"(horizon={result['forward_steps']}, "
            f"repeat={result['repeat_index']}): "
            f"explicit={failed_explicit}; "
            + "; ".join(lines)
        )


def _select_branch_timestep(grid_mod, branch_mod):
    W, eligible_node_names, _vehicle_plans = branch_mod._build_grid5000_world(
        grid_mod
    )
    selection = branch_mod._select_branch_timestep(W, eligible_node_names)
    return selection


def _print_official_baseline_reference_medians():
    print("\n" + "-" * 72)
    print("official baseline reference medians (informational only):")
    print("  copy: ~1.52 s")
    print("  6-step forward: ~0.80 s")
    print("  30-step forward: ~3.78 s")
    print("  50-step forward: ~5.86 s")
    print("  50-step total (copy + forward): ~7.39 s")
    print(
        "These values are NOT used for pass/fail judgment in this diagnostic."
    )


def main():
    previous_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(previous_limit, RECURSION_LIMIT))
    print(
        f"Python recursion limit: {previous_limit} -> {sys.getrecursionlimit()}"
    )

    try:
        grid_mod = _load_grid_level_1_vs_level_2_module()
        branch_mod = _load_world_state_branching_module()
        short_tmax_estimate = _get_short_tmax_estimate()

        print("=" * 72)
        print("TVT global-World baseline short-TMAX performance probe")
        print("=" * 72)
        print(
            "Scenario builder: grid_level_1_vs_level_2_check.build_batch_world "
            "(run_simulation=False)"
        )
        print(
            "Branch selection: world_state_branching_investigation._select_branch_timestep"
        )
        print(f"level2_mode: {LEVEL2_MODE}")
        print(f"N_REPEATS: {N_REPEATS}")
        print(f"FORWARD_STEPS: {FORWARD_STEPS}")
        print(
            "Measurement path: finalized real World -> World.copy() -> "
            "short-TMAX Level 2 patch -> exec_simulation() on fork only -> "
            "restore canonical Level 2 reference"
        )
        print(
            "Vehicle logging: fork-only vehicle_logging_timestep_interval=-1 "
            "after copy, before forward"
        )

        selection = _select_branch_timestep(grid_mod, branch_mod)
        branch_T = selection["selected_T"]
        print("\nBranch timestep selection:")
        print(f"  selected T: {branch_T}")
        print(f"  reason: {selection['selection_reason']}")
        print(f"  service queue note: {selection['service_queue_note']}")

        real_W, _eligible_node_names, _vehicle_plans = (
            branch_mod._rebuild_world_to_timestep(
                grid_mod,
                branch_T,
            )
        )
        if real_W.T != branch_T:
            raise RuntimeError(
                f"branch rebuild T mismatch: expected {branch_T}, got {real_W.T}"
            )
        if real_W.T >= real_W.TSIZE:
            raise RuntimeError(
                f"branch timestep {branch_T} is not before simulation end "
                f"TSIZE={real_W.TSIZE}"
            )

        all_results = []
        horizon_summaries = {}

        for forward_steps in FORWARD_STEPS:
            print("\n" + "-" * 72)
            print(f"Forward horizon: {forward_steps} timestep(s)")
            print("-" * 72)

            copy_samples = []
            forward_samples = []
            total_samples = []
            level2_call_samples = []

            for repeat_index in range(1, N_REPEATS + 1):
                print(f"\nRepeat {repeat_index}/{N_REPEATS}")
                result = _run_single_measurement(
                    real_W,
                    branch_mod,
                    short_tmax_estimate,
                    forward_steps,
                    repeat_index,
                )
                _assert_measurement_success(result)
                _print_measurement_row(result)
                all_results.append(result)
                copy_samples.append(result["copy_seconds"])
                forward_samples.append(result["forward_seconds"])
                total_samples.append(result["total_seconds"])
                level2_call_samples.append(result["level2_calls_during_forward"])

            horizon_summaries[forward_steps] = {
                "copy_seconds": _summarize_times(copy_samples),
                "forward_seconds": _summarize_times(forward_samples),
                "total_seconds": _summarize_times(total_samples),
                "level2_calls_during_forward": _summarize_times(
                    level2_call_samples
                ),
            }

        print("\n" + "=" * 72)
        print("Horizon-specific aggregates (short-TMAX measured values)")
        print("=" * 72)

        copy_only_samples = []
        for forward_steps in FORWARD_STEPS:
            summary = horizon_summaries[forward_steps]
            print(f"\nhorizon={forward_steps}")
            _print_time_summary("copy_seconds", summary["copy_seconds"])
            _print_time_summary("forward_seconds", summary["forward_seconds"])
            _print_time_summary("total_seconds", summary["total_seconds"])
            _print_time_summary(
                "level2_calls_during_forward",
                summary["level2_calls_during_forward"],
            )
            copy_only_samples.extend(summary["copy_seconds"]["samples"])

        print("\n" + "-" * 72)
        print("copy_seconds across all horizons:")
        _print_time_summary("copy_seconds", _summarize_times(copy_only_samples))

        _print_official_baseline_reference_medians()

        print("\nAll short-TMAX measurements completed successfully.")
        return 0
    finally:
        sys.setrecursionlimit(previous_limit)
        print(
            f"Python recursion limit restored: "
            f"{sys.getrecursionlimit()} (was {previous_limit})"
        )


if __name__ == "__main__":
    sys.exit(main())
