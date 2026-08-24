# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Manual cProfile probe for TVT global-World baseline virtual computation timing
# breakdown. Profiles World.copy() and a 50-timestep exec_simulation() separately
# on the Analyzer-attached normal path.
#
# cProfile adds overhead. Do NOT use profile-run wall-clock totals as baseline
# performance values. Do NOT compare them against already-measured non-profile
# timings (e.g. copy ~1.52 s, 50-step forward ~5.86 s). The goal is to identify
# top functions by cumulative time and internal time (tottime).
#
# - cumulative time includes callees
# - tottime (internal time) is time spent in the function itself
#
# Does NOT reproduce TVT institutional logic, confirmed-rank blocks, baseline
# predicted arrival/passage recording, or unresolved-rate measurement.
# Vehicle logging is stopped on the fork only (vehicle_logging_timestep_interval
# = -1) after copy profiling, because the logging A/B diagnostic confirmed
# traffic-state and fork RNG equivalence for that setting.
#
# Keeps tvt_global_baseline_performance.py and tvt_global_baseline_logging_ab.py
# unchanged. Global-World baseline predictions may later be reused for BATCH
# candidate selection improvement, but BATCH candidate-selection logic is out
# of scope.
#
# Run from repository root:
#   python diagnostics/order_control/tvt_global_baseline_profile.py

from __future__ import annotations

import cProfile
import importlib.util
import io
import math
import pickle
import pstats
import sys
from pathlib import Path

FORWARD_STEPS = 50
RECURSION_LIMIT = 50000
PROFILE_TOP_N = 50
SAVE_PROFILE_FILES = False

# Matching rules verified against uxsim.py and related modules (funcname / lineno).
INTERESTED_FUNCTION_SPECS = (
    ("World.copy", {"funcname": "copy", "lineno": 5253, "filename_contains": "uxsim.py"}),
    ("pickle/dill dumps", {"funcname_contains": "dumps"}),
    ("pickle/dill loads", {"funcname_contains": "loads"}),
    ("exec_simulation", {"funcname": "exec_simulation", "lineno": 4796, "filename_contains": "uxsim.py"}),
    ("Link.update", {"funcname": "update", "lineno": 2397, "filename_contains": "uxsim.py"}),
    ("Node.generate", {"funcname": "generate", "lineno": 340, "filename_contains": "uxsim.py"}),
    ("Node.update", {"funcname": "update", "lineno": 2170, "filename_contains": "uxsim.py"}),
    ("Node.transfer", {"funcname": "transfer", "lineno": 2050, "filename_contains": "uxsim.py"}),
    ("Node.transfer_batch", {"funcname": "transfer_batch", "lineno": 1722, "filename_contains": "uxsim.py"}),
    ("form_order_control_batch", {"funcname": "form_order_control_batch", "lineno": 1303, "filename_contains": "uxsim.py"}),
    ("serve_order_control_batch_service_queue", {
        "funcname": "serve_order_control_batch_service_queue",
        "lineno": 1679,
        "filename_contains": "uxsim.py",
    }),
    ("estimate_order_control_batch_t_trigger_level_2_reference", {
        "funcname": "estimate_order_control_batch_t_trigger_level_2_reference",
        "lineno": 19,
        "filename_contains": "order_control_batch_level_2_reference.py",
    }),
    ("_build_mimic_world", {
        "funcname": "_build_mimic_world",
        "lineno": 304,
        "filename_contains": "order_control_batch_level_2_reference.py",
    }),
    ("_run_limited_virtual_loop", {
        "funcname": "_run_limited_virtual_loop",
        "lineno": 1180,
        "filename_contains": "order_control_batch_level_2_reference.py",
    }),
    ("Vehicle.carfollow", {"funcname": "carfollow", "lineno": 3009, "filename_contains": "uxsim.py"}),
    ("Vehicle.update", {"funcname": "update", "lineno": 2899, "filename_contains": "uxsim.py"}),
    ("Vehicle.record_log", {"funcname": "record_log", "lineno": 3648, "filename_contains": "uxsim.py"}),
    ("route_next_link_choice", {"funcname": "route_next_link_choice", "lineno": 3473, "filename_contains": "uxsim.py"}),
    ("record_order_control_node_arrival", {
        "funcname": "record_order_control_node_arrival",
        "lineno": 3318,
        "filename_contains": "uxsim.py",
    }),
    ("route_search_all", {"funcname": "route_search_all", "lineno": 3730, "filename_contains": "uxsim.py"}),
    ("homogeneous_DUO_update", {"funcname": "homogeneous_DUO_update", "lineno": 3768, "filename_contains": "uxsim.py"}),
    ("route_pref_update", {"funcname": "route_pref_update", "lineno": 3045, "filename_contains": "uxsim.py"}),
    ("Analyzer / analyzer", {"filename_contains": "analyzer.py"}),
    ("show_simulation_progress", {"funcname": "show_simulation_progress", "lineno": 1131, "filename_contains": "analyzer.py"}),
    ("basic_analysis", {"funcname": "basic_analysis", "lineno": 80, "filename_contains": "analyzer.py"}),
)


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


def _rng_states_unchanged(before: bytes, after: bytes) -> bool:
    return before == after


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


def _select_branch_timestep(grid_mod, branch_mod):
    W, eligible_node_names, _vehicle_plans = branch_mod._build_grid5000_world(
        grid_mod
    )
    selection = branch_mod._select_branch_timestep(W, eligible_node_names)
    return selection


def _profile_stats_to_text(profiler, sort_key: str, top_n: int) -> str:
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats(sort_key)
    stats.print_stats(top_n)
    return stream.getvalue()


def _print_profile_both_sorts(cumulative_title: str, internal_title: str, profiler):
    print(cumulative_title)
    print("-" * len(cumulative_title))
    print(_profile_stats_to_text(profiler, "cumulative", PROFILE_TOP_N), end="")
    print()
    print(internal_title)
    print("-" * len(internal_title))
    print(_profile_stats_to_text(profiler, "tottime", PROFILE_TOP_N), end="")


def _iter_profile_entries(profiler):
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    for key, value in stats.stats.items():
        filename, lineno, funcname = key
        cc, nc, tt, ct, _callers = value
        yield {
            "filename": filename,
            "lineno": lineno,
            "funcname": funcname,
            "ncalls": nc,
            "tottime": tt,
            "percall_tottime": tt / nc if nc else 0.0,
            "cumtime": ct,
            "percall_cumtime": ct / nc if nc else 0.0,
        }


def _entry_matches_spec(entry, spec):
    filename = entry["filename"]
    funcname = entry["funcname"]
    lineno = entry["lineno"]

    filename_contains = spec.get("filename_contains")
    if filename_contains and filename_contains not in filename:
        return False

    if "funcname" in spec and funcname != spec["funcname"]:
        return False

    funcname_contains = spec.get("funcname_contains")
    if funcname_contains and funcname_contains not in funcname:
        return False

    if "lineno" in spec and lineno != spec["lineno"]:
        return False

    return True


def _find_interested_entries(profiler, spec):
    return [
        entry
        for entry in _iter_profile_entries(profiler)
        if _entry_matches_spec(entry, spec)
    ]


def _format_entry_summary(entry):
    return (
        f"ncalls={entry['ncalls']} "
        f"tottime={entry['tottime']:.6f} "
        f"percall_tottime={entry['percall_tottime']:.6f} "
        f"cumtime={entry['cumtime']:.6f} "
        f"percall_cumtime={entry['percall_cumtime']:.6f} "
        f"{entry['filename']}:{entry['lineno']}({entry['funcname']})"
    )


def _entry_in_profile_top_n(profiler, spec):
    entries = sorted(
        _iter_profile_entries(profiler),
        key=lambda item: item["cumtime"],
        reverse=True,
    )
    top_entries = entries[:PROFILE_TOP_N]
    return any(_entry_matches_spec(entry, spec) for entry in top_entries)


def _summarize_interested_functions(copy_profiler, forward_profiler):
    print("Interested-function summary")
    print("-" * 28)
    for label, spec in INTERESTED_FUNCTION_SPECS:
        print(f"\n{label}:")
        copy_matches = _find_interested_entries(copy_profiler, spec)
        forward_matches = _find_interested_entries(forward_profiler, spec)
        if copy_matches:
            print("  World.copy profile:")
            for entry in copy_matches:
                print(f"    {_format_entry_summary(entry)}")
        if forward_matches:
            print("  50-timestep forward profile:")
            for entry in forward_matches:
                print(f"    {_format_entry_summary(entry)}")
        if not copy_matches and not forward_matches:
            in_copy_top = _entry_in_profile_top_n(copy_profiler, spec)
            in_forward_top = _entry_in_profile_top_n(forward_profiler, spec)
            if in_copy_top or in_forward_top:
                print(
                    "  status: present in cumulative top "
                    f"{PROFILE_TOP_N} but not matched by lineno/name rules"
                )
            else:
                print(
                    "  status: not found in profile statistics "
                    "(not called in this profile scope, below top "
                    f"{PROFILE_TOP_N} by cumulative time, or name differs)"
                )


def _maybe_save_profile(profiler, filename: str):
    if not SAVE_PROFILE_FILES:
        return
    output_path = Path(__file__).resolve().parent / filename
    profiler.dump_stats(str(output_path))
    print(f"Saved profile: {output_path}")


def _run_forward_checks(
    fork_W,
    real_W,
    branch_mod,
    *,
    real_snapshot_before,
    real_rng_before,
    real_order_control_rng_before,
    real_t_before,
    fork_t_before,
    return_code,
    exception_text,
):
    advanced_steps = fork_W.T - fork_t_before
    fork_advanced_as_expected = (
        exception_text is None
        and advanced_steps == FORWARD_STEPS
        and return_code is not None
    )
    damage_detected, damage_message = _fork_has_obvious_state_damage(fork_W)
    if damage_detected:
        fork_advanced_as_expected = False

    comparison_results = branch_mod._compare_world_snapshots(
        real_snapshot_before,
        branch_mod._world_comparison_snapshot(real_W),
    )
    real_world_unchanged = _snapshot_all_match(comparison_results)

    real_rng_unchanged = _rng_states_unchanged(
        real_rng_before,
        _rng_state_bytes(real_W.rng),
    )
    real_order_control_rng_unchanged = _rng_states_unchanged(
        real_order_control_rng_before,
        _rng_state_bytes(real_W.order_control_rng),
    )
    real_t_unchanged = real_W.T == real_t_before

    reference_report = _check_explicit_reference_independence(
        real_W, fork_W, branch_mod
    )

    return {
        "fork_advanced_as_expected": fork_advanced_as_expected,
        "advanced_steps": advanced_steps,
        "return_code": return_code,
        "exception": exception_text,
        "damage_detected": damage_detected,
        "damage_message": damage_message,
        "real_world_unchanged": real_world_unchanged and real_t_unchanged,
        "real_rng_unchanged": real_rng_unchanged,
        "real_order_control_rng_unchanged": real_order_control_rng_unchanged,
        "references_independent": reference_report["references_independent"],
        "comparison_results": comparison_results,
        "reference_report": reference_report,
    }


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
        print("TVT global-World baseline cProfile probe")
        print("=" * 72)

        selection = _select_branch_timestep(grid_mod, branch_mod)
        branch_T = selection["selected_T"]

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

        real_snapshot_before = branch_mod._world_comparison_snapshot(real_W)
        real_rng_before = _rng_state_bytes(real_W.rng)
        real_order_control_rng_before = _rng_state_bytes(
            real_W.order_control_rng
        )
        real_t_before = real_W.T

        print("\nScenario information")
        print("-" * 20)
        print(
            "Scenario builder: grid_level_1_vs_level_2_check.build_batch_world "
            "(run_simulation=False)"
        )
        print(
            "Branch selection: "
            "world_state_branching_investigation._select_branch_timestep"
        )
        print(f"vehicle_count: {branch_mod.GRID_NUM_VEHICLES}")
        print(f"branch_timestep: {real_W.T}")
        print(f"FORWARD_STEPS: {FORWARD_STEPS}")
        print(
            "Vehicle logging on fork: stopped "
            "(vehicle_logging_timestep_interval=-1 after copy profile)"
        )
        print(
            "Vehicle logging on real_W: unchanged "
            f"(vehicle_logging_timestep_interval="
            f"{real_W.vehicle_logging_timestep_interval})"
        )

        print("\ncProfile overhead note")
        print("-" * 22)
        print(
            "- cProfile adds measurement overhead; profile-run totals are not "
            "baseline performance values."
        )
        print(
            "- Do not replace already-measured non-profile timings with these "
            "results."
        )
        print(
            "- Use cumulative time to see inclusive cost including callees."
        )
        print(
            "- Use internal time (tottime) to see time spent inside each "
            "function."
        )

        print("\nProfiling World.copy() ...")
        copy_profiler = cProfile.Profile()
        fork_W = None
        try:
            copy_profiler.enable()
            fork_W = real_W.copy()
            copy_profiler.disable()
        except Exception as exc:
            copy_profiler.disable()
            raise RuntimeError(f"World.copy() failed during profiling: {exc!r}")

        if fork_W is None:
            raise RuntimeError("World.copy() returned None")

        _maybe_save_profile(copy_profiler, "tvt_global_baseline_profile_copy.prof")

        print()
        _print_profile_both_sorts(
            "World.copy profile sorted by cumulative time",
            "World.copy profile sorted by internal time",
            copy_profiler,
        )

        branch_mod._configure_fork(fork_W)
        fork_W.vehicle_logging_timestep_interval = -1

        fork_t_before = fork_W.T
        forward_profiler = cProfile.Profile()
        return_code = None
        exception_text = None
        print("\nProfiling 50-timestep exec_simulation() ...")
        try:
            forward_profiler.enable()
            return_code = fork_W.exec_simulation(
                duration_t2=FORWARD_STEPS * fork_W.DELTAT
            )
            forward_profiler.disable()
        except Exception as exc:
            forward_profiler.disable()
            raise RuntimeError(
                f"exec_simulation() failed during profiling: {exc!r}"
            ) from exc

        _maybe_save_profile(
            forward_profiler,
            "tvt_global_baseline_profile_forward50.prof",
        )

        print()
        _print_profile_both_sorts(
            "50-timestep forward profile sorted by cumulative time",
            "50-timestep forward profile sorted by internal time",
            forward_profiler,
        )

        print()
        _summarize_interested_functions(copy_profiler, forward_profiler)

        checks = _run_forward_checks(
            fork_W,
            real_W,
            branch_mod,
            real_snapshot_before=real_snapshot_before,
            real_rng_before=real_rng_before,
            real_order_control_rng_before=real_order_control_rng_before,
            real_t_before=real_t_before,
            fork_t_before=fork_t_before,
            return_code=return_code,
            exception_text=exception_text,
        )

        print("\nSanity-check results")
        print("-" * 20)
        print(f"fork_advanced_as_expected: {checks['fork_advanced_as_expected']}")
        print(f"advanced_steps: {checks['advanced_steps']}")
        print(f"return_code: {checks['return_code']}")
        print(f"exception: {checks['exception']}")
        print(f"damage_detected: {checks['damage_detected']}")
        print(f"damage_message: {checks['damage_message']}")

        print("\nreal_W immutability")
        print("-" * 18)
        print(f"real_world_unchanged: {checks['real_world_unchanged']}")
        if not checks["real_world_unchanged"]:
            for line in _format_comparison_mismatches(
                checks["comparison_results"]
            ):
                print(f"  {line}")

        print("\nreal_W RNG immutability")
        print("-" * 22)
        print(f"real_rng_unchanged: {checks['real_rng_unchanged']}")
        print(
            "real_order_control_rng_unchanged: "
            f"{checks['real_order_control_rng_unchanged']}"
        )

        print("\nReference independence")
        print("-" * 23)
        print(
            "references_independent: "
            f"{checks['references_independent']}"
        )
        if not checks["references_independent"]:
            for item in checks["reference_report"]["explicit_results"]:
                if not item["independent"]:
                    print(f"  explicit failure: {item['label']}")
            for line in _format_integrity_failures(
                checks["reference_report"]["integrity_checks"]
            ):
                print(f"  {line}")

        if not checks["fork_advanced_as_expected"]:
            raise RuntimeError("forward sanity check failed after profiling")
        if not checks["real_world_unchanged"]:
            raise RuntimeError("real_W changed after profiling")
        if not checks["real_rng_unchanged"]:
            raise RuntimeError("real_W.rng changed after profiling")
        if not checks["real_order_control_rng_unchanged"]:
            raise RuntimeError("real_W.order_control_rng changed after profiling")
        if not checks["references_independent"]:
            raise RuntimeError("reference independence failed after profiling")

        print("\nProfiling diagnostic completed successfully.")
        return 0
    finally:
        sys.setrecursionlimit(previous_limit)
        print(
            f"Python recursion limit restored: "
            f"{sys.getrecursionlimit()} (was {previous_limit})"
        )


if __name__ == "__main__":
    sys.exit(main())
