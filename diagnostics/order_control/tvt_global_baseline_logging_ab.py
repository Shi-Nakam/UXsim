# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Vehicle-logging A/B performance probe for TVT global-World baseline virtual
# computation research.
#
# Condition A (logging_on): keeps the normal Vehicle logging interval copied from
# the real World (vehicle_logging_timestep_interval=1 by default).
#
# Condition B (logging_off): after World.copy(), sets fork-only
# vehicle_logging_timestep_interval=-1 before exec_simulation().
#
# Both conditions use Analyzer-attached normal exec_simulation(). This script
# does NOT reproduce TVT institutional logic, confirmed-rank blocks, baseline
# predicted arrival/passage recording, or unresolved-rate measurement.
#
# The prior baseline probe (tvt_global_baseline_performance.py) is left unchanged.
# The primary A/B comparison target is forward time, not copy time, because the
# logging interval is changed only after World.copy() completes. Copy-time
# medians are recorded for measurement-noise inspection but must not be
# interpreted as a direct effect of Vehicle-log suppression.
#
# Total-time improvement is expected mainly from forward-time reduction.
# Global-World baseline predictions may later be reused for BATCH candidate
# selection improvement, but BATCH candidate-selection logic is out of scope.
#
# Run from repository root:
#   python diagnostics/order_control/tvt_global_baseline_logging_ab.py

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

CONDITION_LOGGING_ON = "logging_on"
CONDITION_LOGGING_OFF = "logging_off"


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


def _rng_state_bytes(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


def _rng_states_equal(left: bytes, right: bytes) -> bool:
    return left == right


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


def _vehicle_traffic_snapshot(veh, branch_mod):
    snapshot = branch_mod._vehicle_state_snapshot(veh)
    snapshot["v"] = float(veh.v)
    return snapshot


def _node_traffic_snapshot(node, branch_mod):
    return {
        "incoming_vehicle_names": [veh.name for veh in node.incoming_vehicles],
        "last_order_control_inlink_name": branch_mod._obj_name(
            node.last_order_control_inlink
        ),
        "last_order_control_entry_timestep": node.last_order_control_entry_timestep,
        "order_control_clearance_timesteps": node.order_control_clearance_timesteps,
        "signal_phase": node.signal_phase,
        "signal_t": float(node.signal_t),
        "flow_capacity_remain": float(node.flow_capacity_remain),
        "service_queue": branch_mod._service_queue_snapshot(node),
    }


def _traffic_state_ab_snapshot(W, branch_mod):
    """
    Traffic-state snapshot for A/B fork comparison.

    Excludes Vehicle trajectory logs (log_t, log_state, log_link, log_x, log_v,
    log_s, log_lane) and Analyzer-derived statistics. Reuses existing branching
    snapshot helpers for traffic fields only.
    """
    return {
        "world": {
            "T": W.T,
            "TIME": W.TIME,
            "level2_counters": branch_mod._level2_counters(W),
        },
        "vehicles": {
            name: _vehicle_traffic_snapshot(veh, branch_mod)
            for name, veh in sorted(W.VEHICLES.items())
        },
        "links": {
            link.name: {
                "vehicle_names": [veh.name for veh in link.vehicles],
                "capacity_in_remain": float(link.capacity_in_remain),
                "capacity_out_remain": float(link.capacity_out_remain),
                "vehicles_enter_log": branch_mod._vehicles_enter_log_snapshot(link),
                "cum_series": branch_mod._cum_series_snapshot(link, W),
            }
            for link in sorted(W.LINKS, key=lambda item: item.name)
        },
        "nodes": {
            node.name: _node_traffic_snapshot(node, branch_mod)
            for node in sorted(W.NODES, key=lambda item: item.name)
        },
    }


def _compare_traffic_states(snapshot_a, snapshot_b, branch_mod):
    return branch_mod._compare_world_snapshots(snapshot_a, snapshot_b)


def _condition_order_for_repeat(repeat_index):
    if repeat_index % 2 == 1:
        return (CONDITION_LOGGING_ON, CONDITION_LOGGING_OFF)
    return (CONDITION_LOGGING_OFF, CONDITION_LOGGING_ON)


def _apply_vehicle_logging_condition(fork_W, condition):
    if condition == CONDITION_LOGGING_ON:
        return
    if condition == CONDITION_LOGGING_OFF:
        fork_W.vehicle_logging_timestep_interval = -1
        return
    raise ValueError(f"unknown condition: {condition!r}")


def _run_condition_measurement(
    real_W,
    branch_mod,
    *,
    condition,
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

    _apply_vehicle_logging_condition(fork_W, condition)
    branch_mod._configure_fork(fork_W)
    fork_t_before = fork_W.T

    exec_started = time.perf_counter()
    exception_text = None
    return_code = None
    try:
        return_code = fork_W.exec_simulation(
            duration_t2=forward_steps * fork_W.DELTAT
        )
    except Exception as exc:
        exception_text = repr(exc)
    forward_seconds = time.perf_counter() - exec_started

    advanced_steps = fork_W.T - fork_t_before
    fork_advanced_as_expected = (
        exception_text is None
        and advanced_steps == forward_steps
        and return_code is not None
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

    traffic_snapshot = _traffic_state_ab_snapshot(fork_W, branch_mod)
    fork_rng_state = _rng_state_bytes(fork_W.rng)
    fork_order_control_rng_state = _rng_state_bytes(fork_W.order_control_rng)

    result = {
        "scenario": "grid5000_batch_level2",
        "condition": condition,
        "vehicle_count": branch_mod.GRID_NUM_VEHICLES,
        "branch_timestep": real_W.T,
        "forward_steps": forward_steps,
        "repeat_index": repeat_index,
        "copy_seconds": copy_seconds,
        "forward_seconds": forward_seconds,
        "total_seconds": copy_seconds + forward_seconds,
        "vehicle_logging_timestep_interval": fork_W.vehicle_logging_timestep_interval,
        "real_world_unchanged": real_world_unchanged and real_t_unchanged,
        "real_rng_unchanged": real_rng_unchanged,
        "real_order_control_rng_unchanged": real_order_control_rng_unchanged,
        "references_independent": reference_report["references_independent"],
        "fork_advanced_as_expected": fork_advanced_as_expected,
        "return_code": return_code,
        "exception": exception_text,
        "advanced_steps": advanced_steps,
        "damage_message": damage_message,
        "comparison_results": comparison_results,
        "reference_report": reference_report,
        "traffic_snapshot": traffic_snapshot,
        "fork_rng_state": fork_rng_state,
        "fork_order_control_rng_state": fork_order_control_rng_state,
    }

    del fork_W
    gc.collect()
    return result


def _print_measurement_row(result):
    fields = [
        "scenario",
        "condition",
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
    ]
    for field in fields:
        print(f"{field}: {result[field]}")


def _print_ab_repeat_summary(ab_summary):
    print("traffic_state_equal:", ab_summary["traffic_state_equal"])
    print("fork_rng_equal:", ab_summary["fork_rng_equal"])
    print("fork_order_control_rng_equal:", ab_summary["fork_order_control_rng_equal"])
    print(
        "logging_on_advanced_as_expected:",
        ab_summary["logging_on_advanced_as_expected"],
    )
    print(
        "logging_off_advanced_as_expected:",
        ab_summary["logging_off_advanced_as_expected"],
    )


_AB_COMPARISON_TEMP_RESULT_KEYS = (
    "traffic_snapshot",
    "fork_rng_state",
    "fork_order_control_rng_state",
)


def _drop_ab_comparison_temp_data(result):
    for key in _AB_COMPARISON_TEMP_RESULT_KEYS:
        result.pop(key, None)
    return result


def _assert_condition_measurement_success(result):
    context = (
        f"condition={result['condition']}, "
        f"horizon={result['forward_steps']}, "
        f"repeat={result['repeat_index']}"
    )
    if not result["fork_advanced_as_expected"]:
        raise RuntimeError(
            "fork advance failed "
            f"({context}): exception={result['exception']}, "
            f"return_code={result['return_code']}, "
            f"advanced_steps={result['advanced_steps']}, "
            f"damage={result['damage_message']}"
        )
    if not result["real_world_unchanged"]:
        lines = _format_comparison_mismatches(result["comparison_results"])
        raise RuntimeError(
            "real World changed after fork execution "
            f"({context}): " + "; ".join(lines)
        )
    if not result["real_rng_unchanged"]:
        raise RuntimeError(f"real W.rng changed ({context})")
    if not result["real_order_control_rng_unchanged"]:
        raise RuntimeError(f"real W.order_control_rng changed ({context})")
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
            f"({context}): explicit={failed_explicit}; " + "; ".join(lines)
        )


def _compare_ab_pair(logging_on_result, logging_off_result, branch_mod):
    traffic_comparison = _compare_traffic_states(
        logging_on_result["traffic_snapshot"],
        logging_off_result["traffic_snapshot"],
        branch_mod,
    )
    traffic_state_equal = _snapshot_all_match(traffic_comparison)
    fork_rng_equal = _rng_states_equal(
        logging_on_result["fork_rng_state"],
        logging_off_result["fork_rng_state"],
    )
    fork_order_control_rng_equal = _rng_states_equal(
        logging_on_result["fork_order_control_rng_state"],
        logging_off_result["fork_order_control_rng_state"],
    )
    return {
        "forward_steps": logging_on_result["forward_steps"],
        "repeat_index": logging_on_result["repeat_index"],
        "traffic_state_equal": traffic_state_equal,
        "fork_rng_equal": fork_rng_equal,
        "fork_order_control_rng_equal": fork_order_control_rng_equal,
        "logging_on_advanced_as_expected": logging_on_result[
            "fork_advanced_as_expected"
        ],
        "logging_off_advanced_as_expected": logging_off_result[
            "fork_advanced_as_expected"
        ],
        "traffic_comparison": traffic_comparison,
    }


def _compute_speedup_metrics(on_summary, off_summary):
    forward_on = on_summary["forward_seconds"]["median"]
    forward_off = off_summary["forward_seconds"]["median"]
    total_on = on_summary["total_seconds"]["median"]
    total_off = off_summary["total_seconds"]["median"]
    copy_on = on_summary["copy_seconds"]["median"]
    copy_off = off_summary["copy_seconds"]["median"]

    return {
        "copy_median_difference": copy_on - copy_off,
        "forward_time_reduction_percent": (
            (forward_on - forward_off) / forward_on * 100.0
        ),
        "total_time_reduction_percent": (
            (total_on - total_off) / total_on * 100.0
        ),
        "forward_speedup_ratio": forward_on / forward_off,
        "total_speedup_ratio": total_on / total_off,
    }


def _summarize_condition_results(condition_results):
    return {
        "copy_seconds": _summarize_times(
            [item["copy_seconds"] for item in condition_results]
        ),
        "forward_seconds": _summarize_times(
            [item["forward_seconds"] for item in condition_results]
        ),
        "total_seconds": _summarize_times(
            [item["total_seconds"] for item in condition_results]
        ),
    }


def _select_branch_timestep(grid_mod, branch_mod):
    W, eligible_node_names, _vehicle_plans = branch_mod._build_grid5000_world(
        grid_mod
    )
    selection = branch_mod._select_branch_timestep(W, eligible_node_names)
    return selection


def _collect_failures(all_results, ab_summaries):
    failures = []
    for result in all_results:
        try:
            _assert_condition_measurement_success(result)
        except RuntimeError as exc:
            failures.append(str(exc))

    for ab_summary in ab_summaries:
        if not ab_summary["traffic_state_equal"]:
            lines = _format_comparison_mismatches(
                ab_summary["traffic_comparison"]
            )
            failures.append(
                "A/B traffic state mismatch "
                f"(horizon={ab_summary['forward_steps']}, "
                f"repeat={ab_summary['repeat_index']}): "
                + "; ".join(lines)
            )
        if not ab_summary["fork_rng_equal"]:
            failures.append(
                "A/B fork W.rng mismatch "
                f"(horizon={ab_summary['forward_steps']}, "
                f"repeat={ab_summary['repeat_index']})"
            )
        if not ab_summary["fork_order_control_rng_equal"]:
            failures.append(
                "A/B fork W.order_control_rng mismatch "
                f"(horizon={ab_summary['forward_steps']}, "
                f"repeat={ab_summary['repeat_index']})"
            )
    return failures


def main():
    previous_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(previous_limit, RECURSION_LIMIT))
    print(
        f"Python recursion limit: {previous_limit} -> {sys.getrecursionlimit()}"
    )

    try:
        grid_mod = _load_grid_level_1_vs_level_2_module()
        branch_mod = _load_world_state_branching_module()

        print("=" * 72)
        print("TVT global-World baseline Vehicle-logging A/B probe")
        print("=" * 72)
        print(
            "Scenario builder: grid_level_1_vs_level_2_check.build_batch_world "
            "(run_simulation=False)"
        )
        print(
            "Branch selection: "
            "world_state_branching_investigation._select_branch_timestep"
        )
        print(f"N_REPEATS: {N_REPEATS}")
        print(f"FORWARD_STEPS: {FORWARD_STEPS}")
        print(
            "Measurement path: finalized real World -> independent World.copy() "
            "per condition -> exec_simulation() on fork only"
        )
        print(
            "Copy-time note: logging interval is changed only after copy(), so "
            "copy_seconds A/B medians are not expected to differ much. The "
            "primary comparison target is forward_seconds."
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
        ab_summaries = []
        horizon_summaries = {}

        for forward_steps in FORWARD_STEPS:
            print("\n" + "-" * 72)
            print(f"Forward horizon: {forward_steps} timestep(s)")
            print("-" * 72)

            horizon_results = {
                CONDITION_LOGGING_ON: [],
                CONDITION_LOGGING_OFF: [],
            }
            horizon_ab_summaries = []

            for repeat_index in range(1, N_REPEATS + 1):
                print(f"\nRepeat {repeat_index}/{N_REPEATS}")
                condition_order = _condition_order_for_repeat(repeat_index)
                print(f"  execution order: {', '.join(condition_order)}")

                repeat_results = {}
                for condition in condition_order:
                    print(f"\n  Condition: {condition}")
                    result = _run_condition_measurement(
                        real_W,
                        branch_mod,
                        condition=condition,
                        forward_steps=forward_steps,
                        repeat_index=repeat_index,
                    )
                    _print_measurement_row(result)
                    repeat_results[condition] = result

                ab_summary = _compare_ab_pair(
                    repeat_results[CONDITION_LOGGING_ON],
                    repeat_results[CONDITION_LOGGING_OFF],
                    branch_mod,
                )
                _print_ab_repeat_summary(ab_summary)
                ab_summaries.append(ab_summary)
                horizon_ab_summaries.append(ab_summary)

                for condition in (
                    CONDITION_LOGGING_ON,
                    CONDITION_LOGGING_OFF,
                ):
                    _assert_condition_measurement_success(
                        repeat_results[condition]
                    )

                for condition in (
                    CONDITION_LOGGING_ON,
                    CONDITION_LOGGING_OFF,
                ):
                    lightweight_result = _drop_ab_comparison_temp_data(
                        repeat_results[condition]
                    )
                    all_results.append(lightweight_result)
                    horizon_results[condition].append(lightweight_result)

                repeat_results.clear()
                gc.collect()

            on_summary = _summarize_condition_results(
                horizon_results[CONDITION_LOGGING_ON]
            )
            off_summary = _summarize_condition_results(
                horizon_results[CONDITION_LOGGING_OFF]
            )
            comparison = _compute_speedup_metrics(on_summary, off_summary)

            horizon_summaries[forward_steps] = {
                CONDITION_LOGGING_ON: on_summary,
                CONDITION_LOGGING_OFF: off_summary,
                "comparison": comparison,
                "all_traffic_states_equal": all(
                    item["traffic_state_equal"] for item in horizon_ab_summaries
                ),
                "all_fork_rng_states_equal": all(
                    item["fork_rng_equal"] and item["fork_order_control_rng_equal"]
                    for item in horizon_ab_summaries
                ),
                "all_real_world_checks_passed": all(
                    result["real_world_unchanged"]
                    and result["real_rng_unchanged"]
                    and result["real_order_control_rng_unchanged"]
                    and result["references_independent"]
                    and result["fork_advanced_as_expected"]
                    for result in (
                        horizon_results[CONDITION_LOGGING_ON]
                        + horizon_results[CONDITION_LOGGING_OFF]
                    )
                ),
            }

        print("\n" + "=" * 72)
        print("Horizon-specific aggregates")
        print("=" * 72)

        for forward_steps in FORWARD_STEPS:
            summary = horizon_summaries[forward_steps]
            print(f"\nhorizon={forward_steps}")

            for condition in (CONDITION_LOGGING_ON, CONDITION_LOGGING_OFF):
                condition_summary = summary[condition]
                print(f"\n{condition}:")
                _print_time_summary("copy_seconds", condition_summary["copy_seconds"])
                _print_time_summary(
                    "forward_seconds", condition_summary["forward_seconds"]
                )
                _print_time_summary("total_seconds", condition_summary["total_seconds"])

            comparison = summary["comparison"]
            print("\ncomparison:")
            print(
                "  copy_median_difference: "
                f"{comparison['copy_median_difference']:.6f} s "
                "(not interpreted as direct logging-off effect)"
            )
            print(
                "  forward_time_reduction_percent: "
                f"{comparison['forward_time_reduction_percent']:.2f}"
            )
            print(
                "  total_time_reduction_percent: "
                f"{comparison['total_time_reduction_percent']:.2f}"
            )
            print(
                "  forward_speedup_ratio: "
                f"{comparison['forward_speedup_ratio']:.4f}"
            )
            print(
                "  total_speedup_ratio: "
                f"{comparison['total_speedup_ratio']:.4f}"
            )
            print(
                "  all_traffic_states_equal: "
                f"{summary['all_traffic_states_equal']}"
            )
            print(
                "  all_fork_rng_states_equal: "
                f"{summary['all_fork_rng_states_equal']}"
            )
            print(
                "  all_real_world_checks_passed: "
                f"{summary['all_real_world_checks_passed']}"
            )

        failures = _collect_failures(all_results, ab_summaries)
        if failures:
            print("\n" + "=" * 72)
            print("Diagnostic failures")
            print("=" * 72)
            for failure in failures:
                print(f"- {failure}")
            raise RuntimeError(
                f"logging A/B diagnostic failed with {len(failures)} issue(s)"
            )

        print("\nAll measurements completed successfully.")
        return 0
    finally:
        sys.setrecursionlimit(previous_limit)
        print(
            f"Python recursion limit restored: "
            f"{sys.getrecursionlimit()} (was {previous_limit})"
        )


if __name__ == "__main__":
    sys.exit(main())
