# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Investigate whether a mid-simulation World can be branched safely for virtual
# forward execution without mutating the original World.
#
# Phase 1: small BATCH merge network (legacy probe constants below).
# Phase 2: 5,000-vehicle high-demand 6x6 grid network (BATCH Level 2 baseline).
#
# Run from repository root:
#   python diagnostics/order_control/world_state_branching_investigation.py
#   python diagnostics/order_control/world_state_branching_investigation.py --mode grid5000

from __future__ import annotations

import argparse
import gc
import importlib.util
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

from uxsim import World

# Legacy small-network constants (mode=small only).
SNAPSHOT_TIMESTEP = 25
FORWARD_STEPS = (1, 10, 50)
SMALL_RANDOM_SEED = 7
SMALL_DEMAND_GEN_SEED = 42
SMALL_NUM_VEHICLES = 40

GRID_NUM_VEHICLES = 5000
GRID_TMAX = 30000
GRID_TRIGGER_LEVEL = 2
GRID_VIRTUAL_HORIZON = 30
GRID_CHECK_INTERVAL = 50
GRID_MAX_SEARCH_T = 2500
GRID_MIN_LINKS_WITH_VEHICLES = 10
GRID_MIN_RUNNING_VEHICLES = 50
GRID_MIN_CURRENT_VISIT_VEHICLES = 1
GRID_MIN_VEHICLES_TOWARD_ELIGIBLE_NODES = 5


def _load_grid_level_1_vs_level_2_module():
    module_path = Path(__file__).resolve().parent / "grid_level_1_vs_level_2_check.py"
    spec = importlib.util.spec_from_file_location(
        "grid_level_1_vs_level_2_check", module_path
    )
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("Failed to load grid_level_1_vs_level_2_check.py")
    spec.loader.exec_module(module)
    return module


def _build_small_batch_world():
    import random

    W = World(
        name="world_branch_probe",
        deltan=1,
        tmax=600,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=SMALL_RANDOM_SEED,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
        batch_size=5,
        order_control_batch_t_trigger_level=1,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=300, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=300, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=300, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(1)

    rng = random.Random(SMALL_DEMAND_GEN_SEED)
    for index in range(SMALL_NUM_VEHICLES):
        departure_time = index * 3
        origin = rng.choice(["orig1", "orig2"])
        W.addVehicle(origin, "dest", departure_time, name=f"veh_{index}")

    W.finalize_scenario()
    return W


def _build_grid5000_world(grid_diag):
    vehicle_plans = grid_diag._generate_vehicle_plans(
        GRID_NUM_VEHICLES,
        grid_diag.DEPARTURE_START,
        grid_diag.DEPARTURE_END,
    )
    W, eligible_node_names, _, _ = grid_diag.build_batch_world(
        vehicle_plans,
        GRID_TMAX,
        GRID_TRIGGER_LEVEL,
        virtual_horizon=GRID_VIRTUAL_HORIZON,
        run_simulation=False,
    )
    if W.finalized == 0:
        W.finalize_scenario()
    return W, eligible_node_names, vehicle_plans


def _level2_counters(W):
    return {
        "call": int(W.order_control_batch_level_2_call_count),
        "resolved": int(W.order_control_batch_level_2_resolved_count),
        "unresolved": int(W.order_control_batch_level_2_unresolved_count),
        "fallback": int(W.order_control_batch_level_2_level_1_fallback_count),
    }


def _configure_fork(fork):
    fork.print_mode = 0
    fork.save_mode = 0
    fork.show_mode = 0
    fork.show_progress = 0


def _advance_exact(W, n_steps):
    start_t = W.T
    W.exec_simulation(duration_t2=n_steps * W.DELTAT)
    return W.T - start_t


def _obj_name(obj):
    return obj.name if obj is not None else None


def _vehicles_enter_log_snapshot(link):
    return {
        float(time_key): vehicle.name
        for time_key, vehicle in sorted(link.vehicles_enter_log.items())
    }


def _cum_series_snapshot(link, W):
    t_index = int(W.T)
    arrival = list(link.cum_arrival[: t_index + 1])
    departure = list(link.cum_departure[: t_index + 1])
    return {
        "length": len(link.cum_arrival),
        "prefix_arrival": arrival,
        "prefix_departure": departure,
    }


def _service_queue_snapshot(node):
    queue = []
    for unit in node.order_control_batch_service_queue:
        queue.append(
            {
                "batch_id": unit["batch_id"],
                "inlink_name": unit["inlink"].name,
                "vehicle_names": [veh.name for veh in unit["vehicles"]],
                "visit_ids": list(unit["visit_ids"]),
            }
        )
    return queue


def _current_visit_snapshot(veh):
    visit = veh.order_control_current_visit
    if visit is None:
        return None
    return {
        "visit_id": visit.get("visit_id"),
        "node_name": _obj_name(visit.get("node")),
        "inlink_name": _obj_name(visit.get("inlink")),
        "earliest_arrival_timestep": visit.get("earliest_arrival_timestep"),
        "arrival_time": visit.get("arrival_time"),
        "arrival_tiebreaker": visit.get("arrival_tiebreaker"),
        "batch_assignment": visit.get("batch_assignment"),
    }


def _batch_assignments_snapshot(veh):
    return dict(getattr(veh, "order_control_batch_assignments", {}))


def _vehicle_state_snapshot(veh):
    has_route_next_link = hasattr(veh, "route_next_link")
    route_next_link = getattr(veh, "route_next_link", None)
    return {
        "state": veh.state,
        "link_name": _obj_name(veh.link),
        "x": float(veh.x),
        "has_route_next_link": has_route_next_link,
        "route_next_link_name": _obj_name(route_next_link),
        "leader_name": _obj_name(veh.leader),
        "follower_name": _obj_name(veh.follower),
        "order_control_current_visit": _current_visit_snapshot(veh),
        "order_control_batch_assignments": _batch_assignments_snapshot(veh),
    }


def _world_comparison_snapshot(W):
    return {
        "world": {
            "T": W.T,
            "TIME": W.TIME,
            "rng_state": W.rng.bit_generator.state,
            "order_control_rng_state": W.order_control_rng.bit_generator.state,
            "level2_counters": _level2_counters(W),
        },
        "vehicles": {
            name: _vehicle_state_snapshot(veh)
            for name, veh in sorted(W.VEHICLES.items())
        },
        "links": {
            link.name: {
                "vehicle_names": [veh.name for veh in link.vehicles],
                "capacity_in_remain": float(link.capacity_in_remain),
                "capacity_out_remain": float(link.capacity_out_remain),
                "vehicles_enter_log": _vehicles_enter_log_snapshot(link),
                "cum_series": _cum_series_snapshot(link, W),
            }
            for link in sorted(W.LINKS, key=lambda item: item.name)
        },
        "nodes": {
            node.name: {
                "incoming_vehicle_names": [veh.name for veh in node.incoming_vehicles],
                "last_order_control_inlink_name": _obj_name(node.last_order_control_inlink),
                "last_order_control_entry_timestep": node.last_order_control_entry_timestep,
                "service_queue": _service_queue_snapshot(node),
            }
            for node in sorted(W.NODES, key=lambda item: item.name)
        },
    }


def _compare_category_snapshots(before, after, category):
    if category == "world":
        keys = sorted(set(before) | set(after))
        mismatches = []
        for key in keys:
            if before.get(key) != after.get(key):
                mismatches.append(
                    {
                        "key": key,
                        "before": before.get(key),
                        "after": after.get(key),
                    }
                )
        return {
            "category": category,
            "compared": len(keys),
            "mismatches": len(mismatches),
            "match": len(mismatches) == 0,
            "examples": mismatches[:3],
        }

    mismatches = []
    all_keys = sorted(set(before) | set(after))
    for key in all_keys:
        if before.get(key) != after.get(key):
            mismatches.append(
                {
                    "key": key,
                    "before": before.get(key),
                    "after": after.get(key),
                }
            )
    return {
        "category": category,
        "compared": len(all_keys),
        "mismatches": len(mismatches),
        "match": len(mismatches) == 0,
        "examples": mismatches[:3],
    }


def _compare_world_snapshots(snapshot_a, snapshot_b):
    results = []
    for category in ("world", "vehicles", "links", "nodes"):
        results.append(
            _compare_category_snapshots(
                snapshot_a[category], snapshot_b[category], category
            )
        )
    return results


def _collect_traffic_state(W, eligible_node_names):
    eligible_set = set(eligible_node_names)
    state_counts = {}
    for veh in W.VEHICLES.values():
        state_counts[veh.state] = state_counts.get(veh.state, 0) + 1

    links_with_vehicles = 0
    link_vehicle_refs = 0
    for link in W.LINKS:
        if link.vehicles:
            links_with_vehicles += 1
            link_vehicle_refs += len(link.vehicles)

    nodes_with_incoming = 0
    incoming_vehicle_refs = 0
    nodes_with_service_queue = 0
    service_units = 0
    service_unit_vehicles = 0
    for node in W.NODES:
        if node.incoming_vehicles:
            nodes_with_incoming += 1
            incoming_vehicle_refs += len(node.incoming_vehicles)
        if node.order_control_batch_service_queue:
            nodes_with_service_queue += 1
            for unit in node.order_control_batch_service_queue:
                service_units += 1
                service_unit_vehicles += len(unit["vehicles"])

    current_visit_count = 0
    batch_assignment_current_visit_count = 0
    for veh in W.VEHICLES.values():
        visit = veh.order_control_current_visit
        if visit is not None:
            current_visit_count += 1
            if visit.get("batch_assignment") is not None:
                batch_assignment_current_visit_count += 1

    vehicles_toward_eligible = 0
    for veh in W.VEHICLES_RUNNING.values():
        if veh.link is not None and veh.link.end_node.name in eligible_set:
            vehicles_toward_eligible += 1

    return {
        "T": W.T,
        "TIME": W.TIME,
        "total_vehicles": len(W.VEHICLES),
        "state_counts": state_counts,
        "running_vehicles": len(W.VEHICLES_RUNNING),
        "wait_vehicles": state_counts.get("wait", 0),
        "end_vehicles": state_counts.get("end", 0),
        "links_with_vehicles": links_with_vehicles,
        "link_vehicle_refs": link_vehicle_refs,
        "nodes_with_incoming": nodes_with_incoming,
        "incoming_vehicle_refs": incoming_vehicle_refs,
        "nodes_with_service_queue": nodes_with_service_queue,
        "service_units": service_units,
        "service_unit_vehicles": service_unit_vehicles,
        "current_visit_count": current_visit_count,
        "batch_assignment_current_visit_count": batch_assignment_current_visit_count,
        "vehicles_toward_eligible_nodes": vehicles_toward_eligible,
        "level2_counters": _level2_counters(W),
    }


def _branch_candidate_score(metrics):
    score = 0
    score += metrics["links_with_vehicles"]
    score += metrics["running_vehicles"]
    score += metrics["current_visit_count"] * 10
    score += metrics["batch_assignment_current_visit_count"] * 20
    score += metrics["vehicles_toward_eligible_nodes"] * 5
    score += metrics["level2_counters"]["call"] * 50
    if metrics["nodes_with_service_queue"] > 0:
        score += 1000
    return score


def _candidate_is_sufficient(metrics):
    return (
        metrics["links_with_vehicles"] >= GRID_MIN_LINKS_WITH_VEHICLES
        and metrics["running_vehicles"] >= GRID_MIN_RUNNING_VEHICLES
        and metrics["current_visit_count"] >= GRID_MIN_CURRENT_VISIT_VEHICLES
        and metrics["vehicles_toward_eligible_nodes"]
        >= GRID_MIN_VEHICLES_TOWARD_ELIGIBLE_NODES
        and metrics["level2_counters"]["call"] >= 1
    )


def _candidate_is_complete_branch_point(metrics):
    return (
        _candidate_is_sufficient(metrics)
        and metrics["level2_counters"]["call"] >= 1
        and metrics["nodes_with_service_queue"] >= 1
    )


def _select_branch_timestep(W, eligible_node_names):
    search_log = []
    best_metrics = None
    best_T = None
    first_service_queue_metrics = None
    first_service_queue_T = None
    selected_T = None
    selected_metrics = None
    selection_reason = None

    while W.T < GRID_MAX_SEARCH_T:
        advanced = _advance_exact(W, GRID_CHECK_INTERVAL)
        if advanced <= 0:
            break
        metrics = _collect_traffic_state(W, eligible_node_names)
        metrics["advanced_this_chunk"] = advanced
        search_log.append(metrics)
        score = _branch_candidate_score(metrics)
        metrics["score"] = score

        if (
            first_service_queue_metrics is None
            and metrics["nodes_with_service_queue"] > 0
        ):
            first_service_queue_metrics = metrics
            first_service_queue_T = W.T

        if best_metrics is None or score > best_metrics["score"]:
            best_metrics = metrics
            best_T = W.T

        if _candidate_is_complete_branch_point(metrics):
            selected_T = W.T
            selected_metrics = metrics
            selection_reason = (
                "First timestep boundary where minimum traffic-state criteria, "
                "at least one Level 2 call, and at least one non-empty BATCH "
                "service queue were all observed."
            )
            break

    if selected_T is None:
        if best_T is not None:
            selected_T = best_T
            selected_metrics = best_metrics
            selection_reason = (
                "No timestep satisfied all minimum criteria plus a non-empty "
                "BATCH service queue within the search limit; selected the "
                "highest-scoring timestep observed during search."
            )
        else:
            selected_T = W.T
            selected_metrics = _collect_traffic_state(W, eligible_node_names)
            selection_reason = (
                "No timestep satisfied the minimum criteria within the search "
                "limit; used the final searched timestep."
            )

    service_queue_note = (
        "A non-empty BATCH service queue at a timestep boundary was observed "
        f"at T={first_service_queue_T}."
        if first_service_queue_T is not None
        else (
            "No non-empty BATCH service queue was observed at any timestep boundary "
            f"up to T={W.T} within the search limit."
        )
    )

    return {
        "selected_T": selected_T,
        "selected_metrics": selected_metrics,
        "selection_reason": selection_reason,
        "service_queue_note": service_queue_note,
        "search_log_tail": search_log[-3:],
        "first_service_queue_T": first_service_queue_T,
    }


def _rebuild_world_to_timestep(grid_diag, target_T):
    W, eligible_node_names, vehicle_plans = _build_grid5000_world(grid_diag)
    if target_T > 0:
        _advance_exact(W, target_T)
    return W, eligible_node_names, vehicle_plans


def _assert_tracemalloc_inactive():
    if tracemalloc.is_tracing():
        raise RuntimeError(
            "tracemalloc must not be active during normal World.copy() timing"
        )


def _copy_world_normal(W, *, release_fork=True):
    """Measure World.copy() with tracemalloc disabled."""
    _assert_tracemalloc_inactive()
    copy_started = time.perf_counter()
    fork = W.copy()
    copy_seconds = time.perf_counter() - copy_started
    result = {"copy_seconds": copy_seconds, "fork": fork}
    if release_fork:
        del fork
        result["fork"] = None
    return result


def _benchmark_normal_world_copy(W, runs=3):
    samples = []
    for _run_index in range(runs):
        gc.collect()
        _assert_tracemalloc_inactive()
        copy_started = time.perf_counter()
        fork = W.copy()
        copy_seconds = time.perf_counter() - copy_started
        if fork is None:
            raise RuntimeError("World.copy() returned None")
        del fork
        gc.collect()
        samples.append(copy_seconds)
    return {
        "samples": samples,
        "min": min(samples),
        "max": max(samples),
        "mean": statistics.mean(samples),
        "median": statistics.median(samples),
    }


def _measure_world_copy_memory(W):
    gc.collect()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    fork = None
    try:
        before_current, _ = tracemalloc.get_traced_memory()
        copy_started = time.perf_counter()
        fork = W.copy()
        copy_seconds_with_tracemalloc = time.perf_counter() - copy_started
        after_current, peak = tracemalloc.get_traced_memory()
        return {
            "copy_seconds_with_tracemalloc": copy_seconds_with_tracemalloc,
            "before_current_bytes": before_current,
            "after_current_bytes": after_current,
            "peak_bytes": peak,
            "current_delta_bytes": after_current - before_current,
            "peak_increase_bytes": peak - before_current,
        }
    finally:
        tracemalloc.stop()
        if fork is not None:
            del fork
        gc.collect()


def _run_forward_case(W, n_steps):
    counters_before = _level2_counters(W)
    t_before = W.T
    gc.collect()
    _assert_tracemalloc_inactive()
    copy_started = time.perf_counter()
    fork = W.copy()
    copy_seconds = time.perf_counter() - copy_started
    _configure_fork(fork)
    exec_started = time.perf_counter()
    return_code = None
    exception_text = None
    try:
        return_code = fork.exec_simulation(duration_t2=n_steps * fork.DELTAT)
    except Exception as exc:
        exception_text = repr(exc)
    exec_seconds = time.perf_counter() - exec_started
    advanced = fork.T - t_before
    counters_after = _level2_counters(fork)
    result = {
        "requested_steps": n_steps,
        "advanced_steps": advanced,
        "steps_match": advanced == n_steps,
        "fork_T_before": t_before,
        "fork_T_after": fork.T,
        "exec_seconds": exec_seconds,
        "copy_seconds": copy_seconds,
        "total_seconds": copy_seconds + exec_seconds,
        "per_step_ms": (exec_seconds / advanced * 1000) if advanced else None,
        "return_code": return_code,
        "success": exception_text is None and advanced == n_steps,
        "exception": exception_text,
        "level2_delta": {
            key: counters_after[key] - counters_before[key]
            for key in counters_before
        },
        "fork": fork,
    }
    return result


def _check_fork_reference_integrity(fork, original_W):
    fork_vehicle_set = set(fork.VEHICLES.values())
    fork_link_set = set(fork.LINKS)
    fork_node_set = set(fork.NODES)
    checks = []

    def add_check(category, inspected, bad_examples):
        checks.append(
            {
                "category": category,
                "inspected": inspected,
                "bad_count": len(bad_examples),
                "examples": bad_examples[:3],
            }
        )

    bad = []
    inspected = 0
    for veh in fork.VEHICLES.values():
        inspected += 1
        if veh.W is not fork:
            bad.append(f"{veh.name}: Vehicle.W is not fork")
        if veh.link is not None and veh.link not in fork_link_set:
            bad.append(f"{veh.name}: link not in fork.LINKS")
        if veh.leader is not None and veh.leader not in fork_vehicle_set:
            bad.append(f"{veh.name}: leader not in fork.VEHICLES")
        if veh.follower is not None and veh.follower not in fork_vehicle_set:
            bad.append(f"{veh.name}: follower not in fork.VEHICLES")
        if hasattr(veh, "route_next_link"):
            route_next_link = veh.route_next_link
            if route_next_link is not None and route_next_link not in fork_link_set:
                bad.append(f"{veh.name}: route_next_link not in fork.LINKS")
        visit = veh.order_control_current_visit
        if visit is not None:
            node = visit.get("node")
            inlink = visit.get("inlink")
            if node is not None and node not in fork_node_set:
                bad.append(f"{veh.name}: current_visit.node not in fork.NODES")
            if inlink is not None and inlink not in fork_link_set:
                bad.append(f"{veh.name}: current_visit.inlink not in fork.LINKS")
    add_check("vehicle", inspected, bad)

    bad = []
    inspected = 0
    for link in fork.LINKS:
        inspected += 1
        if link.W is not fork:
            bad.append(f"{link.name}: Link.W is not fork")
        if link.start_node not in fork_node_set:
            bad.append(f"{link.name}: start_node not in fork.NODES")
        if link.end_node not in fork_node_set:
            bad.append(f"{link.name}: end_node not in fork.NODES")
        for veh in link.vehicles:
            if veh not in fork_vehicle_set:
                bad.append(f"{link.name}: vehicle {veh.name} not in fork.VEHICLES")
    add_check("link", inspected, bad)

    bad = []
    inspected = 0
    for node in fork.NODES:
        inspected += 1
        if node.W is not fork:
            bad.append(f"{node.name}: Node.W is not fork")
        for inlink in node.inlinks.values():
            if inlink not in fork_link_set:
                bad.append(f"{node.name}: inlink {inlink.name} not in fork.LINKS")
        for outlink in node.outlinks.values():
            if outlink not in fork_link_set:
                bad.append(f"{node.name}: outlink {outlink.name} not in fork.LINKS")
        for veh in node.incoming_vehicles:
            if veh not in fork_vehicle_set:
                bad.append(
                    f"{node.name}: incoming vehicle {veh.name} not in fork.VEHICLES"
                )
        if (
            node.last_order_control_inlink is not None
            and node.last_order_control_inlink not in fork_link_set
        ):
            bad.append(f"{node.name}: last_order_control_inlink not in fork.LINKS")
        for unit in node.order_control_batch_service_queue:
            inlink = unit["inlink"]
            if inlink not in fork_link_set:
                bad.append(f"{node.name}: service unit inlink not in fork.LINKS")
            for veh in unit["vehicles"]:
                if veh not in fork_vehicle_set:
                    bad.append(
                        f"{node.name}: service unit vehicle {veh.name} not in fork.VEHICLES"
                    )
    add_check("node", inspected, bad)

    orig_vehicle_set = set(original_W.VEHICLES.values())
    orig_link_set = set(original_W.LINKS)
    orig_node_set = set(original_W.NODES)
    cross_bad = []
    inspected = 0
    for veh in fork.VEHICLES.values():
        inspected += 1
        if veh in orig_vehicle_set:
            cross_bad.append(f"{veh.name}: fork Vehicle object is identical to original")
        if veh.link is not None and veh.link in orig_link_set:
            cross_bad.append(f"{veh.name}: fork Vehicle.link references original Link")
        visit = veh.order_control_current_visit
        if visit is not None:
            node = visit.get("node")
            inlink = visit.get("inlink")
            if node is not None and node in orig_node_set:
                cross_bad.append(
                    f"{veh.name}: current_visit.node references original Node"
                )
            if inlink is not None and inlink in orig_link_set:
                cross_bad.append(
                    f"{veh.name}: current_visit.inlink references original Link"
                )
    add_check("cross_world_identity", inspected, cross_bad)

    return checks


def _print_comparison_results(title, results):
    print(title)
    all_match = True
    for item in results:
        print(
            f"  {item['category']:10s} compared={item['compared']:5d} "
            f"mismatches={item['mismatches']:5d} match={item['match']}"
        )
        if not item["match"]:
            all_match = False
            for example in item["examples"]:
                print(f"    example: {example}")
    return all_match


def _print_integrity_results(title, checks):
    print(title)
    all_ok = True
    for item in checks:
        print(
            f"  {item['category']:22s} inspected={item['inspected']:5d} "
            f"bad={item['bad_count']:5d}"
        )
        if item["bad_count"]:
            all_ok = False
            for example in item["examples"]:
                print(f"    example: {example}")
    return all_ok


def _bytes_to_mib(value):
    return value / (1024 * 1024)


def run_grid5000_investigation():
    # dill pickling of the full 5,000-vehicle World exceeds the default recursion
    # limit on this platform; raise it so World.copy() can complete.
    previous_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(previous_limit, 50000))
    print(
        f"Python recursion limit for grid5000 run: "
        f"{previous_limit} -> {sys.getrecursionlimit()}"
    )

    try:
        grid_diag = _load_grid_level_1_vs_level_2_module()
        print("=" * 72)
        print("World state branching investigation — 5,000-vehicle grid network")
        print("=" * 72)
        print(
            "Reference diagnostic: "
            "diagnostics/order_control/grid_level_1_vs_level_2_check.py"
        )
        print(
            "Reused functions: _generate_vehicle_plans, build_batch_world "
            "(run_simulation=False)"
        )
        print(
            "Scenario constants from reference: "
            f"RANDOM_SEED={grid_diag.RANDOM_SEED}, "
            f"DEMAND_GEN_SEED={grid_diag.DEMAND_GEN_SEED}, "
            f"BATCH_SIZE={grid_diag.BATCH_SIZE}, "
            f"CLEARANCE_TIMESTEPS={grid_diag.CLEARANCE_TIMESTEPS}, "
            f"LEVEL_2_VIRTUAL_HORIZON={grid_diag.LEVEL_2_VIRTUAL_HORIZON}, "
            f"NUM_VEHICLES={GRID_NUM_VEHICLES}, TMAX={GRID_TMAX}, "
            f"trigger_level={GRID_TRIGGER_LEVEL}"
        )
        print(
            "Difference from reference diagnostic: this script stops at a "
            "mid-simulation timestep boundary for branching; it does not run the "
            "full diagnostic comparison workflow."
        )

        W, eligible_node_names, _vehicle_plans = _build_grid5000_world(grid_diag)
        print(f"Eligible order-control nodes: {len(eligible_node_names)}")

        selection = _select_branch_timestep(W, eligible_node_names)
        branch_T = selection["selected_T"]
        print("\nBranch timestep selection:")
        print(f"  selected T: {branch_T}")
        print(f"  reason: {selection['selection_reason']}")
        print(f"  service queue note: {selection['service_queue_note']}")

        branch_state = selection["selected_metrics"]
        print("\nTraffic state at branch timestep:")
        for key, value in branch_state.items():
            print(f"  {key}: {value}")

        W_branch, eligible_node_names, _ = _rebuild_world_to_timestep(
            grid_diag, branch_T
        )

        print("\nNormal World.copy() timing (tracemalloc disabled, 3 runs):")
        normal_copy_benchmark = _benchmark_normal_world_copy(W_branch, runs=3)
        for index, sample in enumerate(normal_copy_benchmark["samples"], start=1):
            print(f"  run {index}: {sample:.6f} s")
        print(f"  min: {normal_copy_benchmark['min']:.6f} s")
        print(f"  max: {normal_copy_benchmark['max']:.6f} s")
        print(f"  mean: {normal_copy_benchmark['mean']:.6f} s")
        print(f"  median (representative): {normal_copy_benchmark['median']:.6f} s")

        print("\nWorld.copy() memory measurement (tracemalloc enabled, 1 run):")
        memory_measurement = _measure_world_copy_memory(W_branch)
        print(
            "  copy_seconds_with_tracemalloc (reference only, not performance): "
            f"{memory_measurement['copy_seconds_with_tracemalloc']:.6f}"
        )
        print(
            "  before_current: "
            f"{_bytes_to_mib(memory_measurement['before_current_bytes']):.2f} MiB"
        )
        print(
            "  after_current: "
            f"{_bytes_to_mib(memory_measurement['after_current_bytes']):.2f} MiB"
        )
        print(f"  peak: {_bytes_to_mib(memory_measurement['peak_bytes']):.2f} MiB")
        print(
            "  current_delta: "
            f"{_bytes_to_mib(memory_measurement['current_delta_bytes']):.2f} MiB"
        )
        print(
            "  peak_increase_from_before: "
            f"{_bytes_to_mib(memory_measurement['peak_increase_bytes']):.2f} MiB"
        )
        print(
            "  memory note: tracemalloc tracks Python allocations only; "
            "NumPy/SciPy/OS memory may be under-reported."
        )

        print("\nForward execution cases (normal copy without tracemalloc):")
        forward_results = {}
        for steps in FORWARD_STEPS:
            W_case, _, _ = _rebuild_world_to_timestep(grid_diag, branch_T)
            case_result = _run_forward_case(W_case, steps)
            forward_results[steps] = case_result
            print(f"  steps={steps}:")
            print(f"    copy_seconds: {case_result['copy_seconds']:.6f}")
            print(f"    exec_seconds: {case_result['exec_seconds']:.6f}")
            print(f"    total_seconds: {case_result['total_seconds']:.6f}")
            print(f"    per_step_ms: {case_result['per_step_ms']}")
            print(f"    fork_T_before: {case_result['fork_T_before']}")
            print(f"    fork_T_after: {case_result['fork_T_after']}")
            print(f"    advanced_steps: {case_result['advanced_steps']}")
            print(f"    steps_match: {case_result['steps_match']}")
            print(f"    return_code: {case_result['return_code']}")
            print(f"    success: {case_result['success']}")
            print(f"    exception: {case_result['exception']}")
            print(f"    level2_delta: {case_result['level2_delta']}")
            del case_result["fork"]
            gc.collect()

        print("\nOriginal-world independence after separate 50-step fork:")
        W_orig, _, _ = _rebuild_world_to_timestep(grid_diag, branch_T)
        before_snapshot = _world_comparison_snapshot(W_orig)
        fifty_case = _run_forward_case(W_orig, 50)
        independence_ok = _print_comparison_results(
            "  category results:",
            _compare_world_snapshots(
                before_snapshot, _world_comparison_snapshot(W_orig)
            ),
        )
        del fifty_case["fork"]
        gc.collect()

        print("\nFork reference integrity (from a fresh copy at branch timestep):")
        W_integrity, _, _ = _rebuild_world_to_timestep(grid_diag, branch_T)
        gc.collect()
        _assert_tracemalloc_inactive()
        fork = W_integrity.copy()
        _configure_fork(fork)
        integrity_ok = _print_integrity_results(
            "  integrity checks:",
            _check_fork_reference_integrity(fork, W_integrity),
        )
        del fork, W_integrity
        gc.collect()

        print("\nReproducibility: two independent forks, 50 steps each:")
        W_repro, _, _ = _rebuild_world_to_timestep(grid_diag, branch_T)
        gc.collect()
        _assert_tracemalloc_inactive()
        fork_a = W_repro.copy()
        fork_b = W_repro.copy()
        _configure_fork(fork_a)
        _configure_fork(fork_b)
        _advance_exact(fork_a, 50)
        _advance_exact(fork_b, 50)
        reproducibility_ok = _print_comparison_results(
            "  category results:",
            _compare_world_snapshots(
                _world_comparison_snapshot(fork_a),
                _world_comparison_snapshot(fork_b),
            ),
        )
        del fork_a, fork_b, W_repro
        gc.collect()

        all_forward_ok = all(item["success"] for item in forward_results.values())
        return {
            "branch_T": branch_T,
            "branch_state": branch_state,
            "normal_copy_benchmark": normal_copy_benchmark,
            "memory_measurement": memory_measurement,
            "forward_results": forward_results,
            "independence_ok": independence_ok,
            "integrity_ok": integrity_ok,
            "reproducibility_ok": reproducibility_ok,
            "all_forward_ok": all_forward_ok,
        }
    finally:
        sys.setrecursionlimit(previous_limit)
        print(
            f"Python recursion limit restored: "
            f"{sys.getrecursionlimit()} (was {previous_limit})"
        )


def run_small_investigation():
    print("=" * 72)
    print("World state branching investigation — small network (legacy probe)")
    print("=" * 72)
    base_W = _build_small_batch_world()
    base_W.exec_simulation(until_t=SNAPSHOT_TIMESTEP * base_W.DELTAT)
    print(f"Base world advanced to T={base_W.T}, vehicles={len(base_W.VEHICLES)}")
    fork = base_W.copy()
    _configure_fork(fork)
    _advance_exact(fork, 50)
    print("Small-network probe complete.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("grid5000", "small"),
        default="grid5000",
        help="grid5000 runs the 5,000-vehicle investigation (default).",
    )
    args = parser.parse_args()
    if args.mode == "grid5000":
        result = run_grid5000_investigation()
        if not (
            result["all_forward_ok"]
            and result["independence_ok"]
            and result["integrity_ok"]
            and result["reproducibility_ok"]
        ):
            return 2
        return 0
    run_small_investigation()
    return 0


if __name__ == "__main__":
    sys.exit(main())
