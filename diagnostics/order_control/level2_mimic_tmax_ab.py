# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# A/B comparison of Level 2 mimic World TMAX selection:
#   A (official): uxsim/order_control_batch_level_2_reference.py
#   B (short_tmax): diagnostics/order_control/order_control_batch_level_2_short_tmax_reference.py
#
# Only mimic World tmax differs between conditions. Both keep
# finalize_scenario(create_analyzer=False) on the mimic path.
#
# Run from repository root:
#   python diagnostics/order_control/level2_mimic_tmax_ab.py
#
# Default: RUN_BOUNDARY_SMALL_CASES=True, RUN_GRID5000_MATRIX=False

from __future__ import annotations

import copy
import difflib
import importlib.util
import pickle
import statistics
import sys
import time
from pathlib import Path

from uxsim import World
from uxsim.order_control_batch_level_2_reference import (
    estimate_order_control_batch_t_trigger_level_2_reference as official_estimate,
)

FORWARD_STEPS = 50
RECURSION_LIMIT = 50000

CONDITION_OFFICIAL = "official"
CONDITION_SHORT_TMAX = "short_tmax"
CONDITION_EXECUTION_ORDER = (
    CONDITION_SHORT_TMAX,
    CONDITION_OFFICIAL,
)

GRID_BRANCH_TIMESTEPS = (50, 300, 550)
LEVEL2_VIRTUAL_HORIZONS = (30, 199, 200)
BOUNDARY_VIRTUAL_HORIZONS = (199, 200)
BOUNDARY_LARGE_REAL_TMAX = 30000
BOUNDARY_LARGE_REAL_TMAX_VIRTUAL_HORIZON = 200
BOUNDARY_LARGE_REAL_TMAX_SHORT_TMAX_BOUNDARY_CASE_NAME = (
    "large_real_tmax_virtual_horizon_200_short_tmax_boundary"
)

RUN_BOUNDARY_SMALL_CASES = True
RUN_GRID5000_MATRIX = False

# Verified in uxsim.py Node._resolve_order_control_batch_t_trigger (level 2 path):
# s.order_control_batch_virtual_horizon is passed to Level 2 reference estimator.
NODE_LEVEL2_VIRTUAL_HORIZON_ATTR = "order_control_batch_virtual_horizon"

LEVEL2_RESULT_KEYS = (
    "resolved",
    "reason",
    "t_virtual_trigger",
    "t_level_2_candidate",
    "t_level_1",
    "snapshot_timestep",
    "simulated_timestep_count",
    "trigger_vehicle_name",
    "vehicle_transfer_timesteps",
    "virtual_node_arrival_timesteps",
    "virtual_outlink_choices",
    "service_stop_trace",
    "sink_end_trip_trace",
)

LEVEL2_CALL_INPUT_KEYS = (
    "call_index",
    "snapshot_timestep",
    "node_name",
    "trigger_vehicle_name",
    "t_level_1",
    "virtual_horizon",
)

LEVEL2_TIMING_KEYS = (
    "total_seconds",
    "mimic_build_seconds",
    "finalize_seconds",
    "virtual_loop_seconds",
    "mimic_tmax",
    "mimic_tsize",
    "mimic_link_count",
    "traveltime_actual_length",
    "k_mat_shape",
)

_DIAGNOSTICS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DIAGNOSTICS_DIR.parent.parent
_CANONICAL_REFERENCE_PATH = _REPO_ROOT / "uxsim" / "order_control_batch_level_2_reference.py"
_SHORT_TMAX_REFERENCE_PATH = (
    _DIAGNOSTICS_DIR / "order_control_batch_level_2_short_tmax_reference.py"
)


def _load_module(module_name: str, filename: str):
    module_path = _DIAGNOSTICS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Failed to load {filename}")
    spec.loader.exec_module(module)
    return module


def _load_short_tmax_reference_module():
    return _load_module(
        "order_control_batch_level_2_short_tmax_reference",
        "order_control_batch_level_2_short_tmax_reference.py",
    )


def _load_world_state_branching_module():
    return _load_module(
        "world_state_branching_investigation",
        "world_state_branching_investigation.py",
    )


def _load_grid_module():
    return _load_module(
        "grid_level_1_vs_level_2_check",
        "grid_level_1_vs_level_2_check.py",
    )


def _get_short_tmax_estimate():
    short_mod = _load_short_tmax_reference_module()
    return short_mod.estimate_order_control_batch_t_trigger_level_2_reference


def _rng_state_bytes(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_three_inlink_network(name="l2_tmax_ab", clearance=0, *, tmax=200):
    W = World(
        name=name,
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.set_order_control_clearance_timesteps(clearance)
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("orig3", 0, 4)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _make_vehicle(W, orig_name, name):
    return W.addVehicle(orig_name, "dest", 0, name=name)


def _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker, batch_assignment=None):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    veh.order_control_current_visit = {
        "visit_id": veh.order_control_visit_id,
        "node": merge,
        "inlink": link,
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
        "arrival_tiebreaker": tiebreaker,
        "batch_assignment": batch_assignment,
    }


def _setup_arrived(merge, veh, link, out_link, earliest, arrival_time, tiebreaker, x=200.0):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.move_remain = 0.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker)
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _setup_unarrived(merge, veh, link, earliest, *, x=150.0):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.move_remain = 0.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = link
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    _sync_visit(veh, merge, link, earliest, None, None)
    if veh not in link.vehicles:
        link.vehicles.append(veh)


def _register_unit(merge, batch_id, inlink, vehicles):
    visit_ids = []
    for veh in vehicles:
        visit = veh.order_control_current_visit
        visit["batch_assignment"] = batch_id
        veh.order_control_batch_assignments[merge.name] = batch_id
        visit_ids.append(visit["visit_id"])
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": batch_id,
            "inlink": inlink,
            "vehicles": list(vehicles),
            "visit_ids": visit_ids,
        }
    )


def _boost_capacity(merge, *links):
    for link in links:
        link.capacity_in_remain = 10**10
        link.capacity_out_remain = 10**10
    merge.flow_capacity_remain = 10**10


def _snapshot_world_state(merge, vehicles):
    return {
        "W_T": merge.W.T,
        "rng_state": _rng_state_bytes(merge.W.rng),
        "order_control_rng_state": _rng_state_bytes(merge.W.order_control_rng),
        "service_queue": [
            {
                "batch_id": unit["batch_id"],
                "inlink": unit["inlink"].name,
                "vehicles": [veh.name for veh in unit["vehicles"]],
                "visit_ids": list(unit["visit_ids"]),
            }
            for unit in merge.order_control_batch_service_queue
        ],
        "last_inlink": (
            None
            if merge.last_order_control_inlink is None
            else merge.last_order_control_inlink.name
        ),
        "last_entry": merge.last_order_control_entry_timestep,
        "next_id": merge.order_control_batch_next_id,
        "flow_capacity_remain": merge.flow_capacity_remain,
        "vehicles": {
            veh.name: {
                "x": veh.x,
                "state": veh.state,
                "assignment": copy.copy(veh.order_control_batch_assignments),
                "visit": (
                    None
                    if veh.order_control_current_visit is None
                    else {
                        "visit_id": veh.order_control_current_visit["visit_id"],
                        "node": veh.order_control_current_visit["node"].name,
                        "inlink": veh.order_control_current_visit["inlink"].name,
                        "earliest_arrival_timestep": veh.order_control_current_visit[
                            "earliest_arrival_timestep"
                        ],
                        "arrival_time": veh.order_control_current_visit.get(
                            "arrival_time"
                        ),
                        "arrival_tiebreaker": veh.order_control_current_visit.get(
                            "arrival_tiebreaker"
                        ),
                        "batch_assignment": veh.order_control_current_visit.get(
                            "batch_assignment"
                        ),
                    }
                ),
            }
            for veh in vehicles
        },
        "link_vehicles": {
            link.name: [veh.name for veh in link.vehicles]
            for link in list(merge.inlinks.values()) + list(merge.outlinks.values())
        },
        "capacity": {
            link.name: {
                "capacity_in_remain": link.capacity_in_remain,
                "capacity_out_remain": link.capacity_out_remain,
            }
            for link in list(merge.inlinks.values()) + list(merge.outlinks.values())
        },
    }


def _assert_world_unchanged(before, after):
    for key in before:
        if before[key] != after[key]:
            raise RuntimeError(f"real World changed at key={key!r}")


def _project_level2_result(result):
    return {key: result[key] for key in LEVEL2_RESULT_KEYS if key in result}


def _adopted_t_trigger(result):
    if result["resolved"]:
        return int(result["t_level_2_candidate"])
    return int(result["t_level_1"])


def _build_level2_call_record(
    call_index,
    real_node,
    real_trigger_vehicle,
    t_level_1,
    virtual_horizon,
    result,
    *,
    wall_seconds,
    timing_collector=None,
):
    record = {
        "call_index": int(call_index),
        "snapshot_timestep": int(real_node.W.T),
        "node_name": real_node.name,
        "trigger_vehicle_name": real_trigger_vehicle.name,
        "t_level_1": int(t_level_1),
        "virtual_horizon": int(virtual_horizon),
        **_project_level2_result(result),
        "adopted_t_trigger": _adopted_t_trigger(result),
        "total_seconds": float(wall_seconds),
    }
    if timing_collector is not None:
        for key in LEVEL2_TIMING_KEYS:
            if key == "total_seconds":
                continue
            if key in timing_collector:
                record[key] = timing_collector[key]
    return record


def _make_collecting_estimate(estimate_fn, *, include_timing_collector):
    def collecting_estimate(
        real_node,
        real_trigger_vehicle,
        t_level_1,
        virtual_horizon,
        **kwargs,
    ):
        timing_collector = {} if include_timing_collector else None
        started = time.perf_counter()
        if include_timing_collector:
            result = estimate_fn(
                real_node,
                real_trigger_vehicle,
                t_level_1,
                virtual_horizon,
                timing_collector=timing_collector,
                **kwargs,
            )
        else:
            result = estimate_fn(
                real_node,
                real_trigger_vehicle,
                t_level_1,
                virtual_horizon,
                **kwargs,
            )
        wall_seconds = time.perf_counter() - started
        record = _build_level2_call_record(
            len(collecting_estimate.records) + 1,
            real_node,
            real_trigger_vehicle,
            t_level_1,
            virtual_horizon,
            result,
            wall_seconds=wall_seconds,
            timing_collector=timing_collector,
        )
        collecting_estimate.records.append(record)
        return result

    collecting_estimate.records = []
    return collecting_estimate


def _patch_level2_reference(estimate_fn):
    import uxsim.order_control_batch_level_2_reference as l2_module

    original = l2_module.estimate_order_control_batch_t_trigger_level_2_reference
    l2_module.estimate_order_control_batch_t_trigger_level_2_reference = estimate_fn
    return l2_module, original


def _restore_level2_reference(l2_module, original):
    l2_module.estimate_order_control_batch_t_trigger_level_2_reference = original


def _run_official_estimate(merge, trigger, t_level_1, virtual_horizon):
    vehicles = list(
        {
            veh
            for unit in merge.order_control_batch_service_queue
            for veh in unit["vehicles"]
        }
    ) + [trigger]
    before = _snapshot_world_state(merge, vehicles)
    before_rng = _rng_state_bytes(merge.W.rng)
    before_order_control_rng = _rng_state_bytes(merge.W.order_control_rng)

    started = time.perf_counter()
    result = official_estimate(
        merge,
        trigger,
        t_level_1,
        virtual_horizon,
        mimic_random_seed=0,
    )
    wall_seconds = time.perf_counter() - started

    after = _snapshot_world_state(merge, vehicles)
    _assert_world_unchanged(before, after)
    if _rng_state_bytes(merge.W.rng) != before_rng:
        raise RuntimeError("real W.rng changed after official Level 2 estimate")
    if _rng_state_bytes(merge.W.order_control_rng) != before_order_control_rng:
        raise RuntimeError(
            "real W.order_control_rng changed after official Level 2 estimate"
        )

    return {
        "condition": CONDITION_OFFICIAL,
        "result": _project_level2_result(result),
        "adopted_t_trigger": _adopted_t_trigger(result),
        "total_seconds": wall_seconds,
    }


def _run_short_tmax_estimate(merge, trigger, t_level_1, virtual_horizon, short_tmax_estimate):
    vehicles = list(
        {
            veh
            for unit in merge.order_control_batch_service_queue
            for veh in unit["vehicles"]
        }
    ) + [trigger]
    before = _snapshot_world_state(merge, vehicles)
    before_rng = _rng_state_bytes(merge.W.rng)
    before_order_control_rng = _rng_state_bytes(merge.W.order_control_rng)

    timing_collector = {}
    started = time.perf_counter()
    result = short_tmax_estimate(
        merge,
        trigger,
        t_level_1,
        virtual_horizon,
        mimic_random_seed=0,
        timing_collector=timing_collector,
    )
    wall_seconds = time.perf_counter() - started

    after = _snapshot_world_state(merge, vehicles)
    _assert_world_unchanged(before, after)
    if _rng_state_bytes(merge.W.rng) != before_rng:
        raise RuntimeError("real W.rng changed after short_tmax Level 2 estimate")
    if _rng_state_bytes(merge.W.order_control_rng) != before_order_control_rng:
        raise RuntimeError(
            "real W.order_control_rng changed after short_tmax Level 2 estimate"
        )

    return {
        "condition": CONDITION_SHORT_TMAX,
        "result": _project_level2_result(result),
        "adopted_t_trigger": _adopted_t_trigger(result),
        "total_seconds": wall_seconds,
        "timing": dict(timing_collector),
    }


def _compare_ab_results(label, result_a, result_b):
    if result_a["result"] != result_b["result"]:
        raise RuntimeError(
            f"{label}: Level 2 result mismatch between conditions\n"
            f"  A={result_a['result']}\n"
            f"  B={result_b['result']}"
        )
    if result_a["adopted_t_trigger"] != result_b["adopted_t_trigger"]:
        raise RuntimeError(
            f"{label}: adopted t_trigger mismatch "
            f"A={result_a['adopted_t_trigger']} B={result_b['adopted_t_trigger']}"
        )


def _compare_level2_call_inputs(label, records_a, records_b):
    if len(records_a) != len(records_b):
        raise RuntimeError(
            f"{label}: Level 2 call count mismatch "
            f"A={len(records_a)} B={len(records_b)}"
        )
    for index, (record_a, record_b) in enumerate(
        zip(records_a, records_b), start=1
    ):
        for key in LEVEL2_CALL_INPUT_KEYS:
            if record_a.get(key) != record_b.get(key):
                raise RuntimeError(
                    f"{label}: Level 2 call input mismatch at call {index}, "
                    f"key={key!r}, A={record_a.get(key)!r}, B={record_b.get(key)!r}"
                )


def _compare_level2_call_results(label, records_a, records_b):
    compare_keys = LEVEL2_RESULT_KEYS + ("adopted_t_trigger",)
    for index, (record_a, record_b) in enumerate(
        zip(records_a, records_b), start=1
    ):
        for key in compare_keys:
            if record_a.get(key) != record_b.get(key):
                raise RuntimeError(
                    f"{label}: Level 2 result mismatch at call {index}, "
                    f"key={key!r}, A={record_a.get(key)!r}, B={record_b.get(key)!r}"
                )


def _record_condition(item):
    return item.get("condition", "grid_call")


def _record_resolved(item):
    if "result" in item:
        return item["result"]["resolved"]
    return item["resolved"]


def _print_timing_summary(label, runs, *, include_phase_timing=False):
    totals = [item["total_seconds"] for item in runs]
    print(f"\n{label} timing summary:")
    print(f"  condition: {_record_condition(runs[0])}")
    print(f"  call_count: {len(runs)}")
    print(f"  resolved_count: {sum(1 for item in runs if _record_resolved(item))}")
    print(
        "  unresolved_count: "
        f"{sum(1 for item in runs if not _record_resolved(item))}"
    )
    print(f"  total_seconds (sum): {sum(totals):.6f}")
    print(f"  median_seconds: {statistics.median(totals):.6f}")
    print(f"  min_seconds: {min(totals):.6f}")
    print(f"  max_seconds: {max(totals):.6f}")

    if include_phase_timing:
        for phase in (
            "mimic_build_seconds",
            "finalize_seconds",
            "virtual_loop_seconds",
        ):
            samples = [
                item.get(phase)
                for item in runs
                if item.get(phase) is not None
            ]
            if samples:
                print(f"  {phase} median: {statistics.median(samples):.6f}")


def _print_reference_array_shapes(label, merge, result_b, real_tmax):
    local_tmax = (merge.W.T + 200) * merge.W.DELTAT
    print(f"\n{label} array-shape sample:")
    print(f"  snapshot_timestep: {merge.W.T}")
    print(f"  expected A mimic_tmax: {max(real_tmax, local_tmax)}")
    print(f"  expected B mimic_tmax: {local_tmax}")
    timing = result_b.get("timing", {})
    print(f"  B measured mimic_tmax: {timing.get('mimic_tmax')}")
    print(f"  B measured mimic_tsize: {timing.get('mimic_tsize')}")
    print(f"  B measured mimic_link_count: {timing.get('mimic_link_count')}")
    print(
        "  B measured traveltime_actual_length: "
        f"{timing.get('traveltime_actual_length')}"
    )
    print(f"  B measured k_mat_shape: {timing.get('k_mat_shape')}")


def _build_arrived_reference_case():
    W = _build_three_inlink_network("ab_arrived", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    return merge, trigger, t_level_1, 20, W.TMAX


def _build_unarrived_reference_case():
    W = _build_three_inlink_network("ab_unarrived", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = 10
    return merge, trigger, t_level_1, 5, W.TMAX


def _run_reference_case_ab(label, merge, trigger, t_level_1, virtual_horizon, real_tmax):
    print(f"\n{'=' * 72}")
    print(label)
    print(f"  real_W.TMAX: {real_tmax}")
    print(f"  snapshot_timestep: {merge.W.T}")
    print(f"  virtual_horizon: {virtual_horizon}")

    short_tmax_estimate = _get_short_tmax_estimate()
    result_a = _run_official_estimate(merge, trigger, t_level_1, virtual_horizon)
    result_b = _run_short_tmax_estimate(
        merge,
        trigger,
        t_level_1,
        virtual_horizon,
        short_tmax_estimate,
    )
    _compare_ab_results(label, result_a, result_b)
    _print_reference_array_shapes(label, merge, result_b, real_tmax)
    return result_a, result_b


def _build_virtual_horizon_exceeded_boundary_case(virtual_horizon, *, real_world_tmax=200):
    """
    Based on tests_order_control_batch_t_trigger_level_2_reference.test_virtual_horizon_exceeded.

    Reuses the same Node/Link/Vehicle/service-queue layout, but raises clearance so the
    trigger on link2 cannot satisfy clearance before the virtual loop exhausts:

      clearance_satisfied when W.T >= last_entry + clearance + 1
      with last_entry=9 and snapshot W.T=10, that is W.T >= clearance + 10.

    The virtual loop ends at snapshot + virtual_horizon, so choosing
    clearance = virtual_horizon + 1 keeps trigger unresolved through the final offset.
    """
    clearance = virtual_horizon + 1
    W = _build_three_inlink_network(
        f"ab_boundary_h{virtual_horizon}",
        clearance=clearance,
        tmax=real_world_tmax,
    )
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    return merge, trigger, t_level_1, W.TMAX


def _assert_boundary_horizon_exceeded_result(result, virtual_horizon):
    if result["resolved"] is not False:
        raise RuntimeError(
            f"expected resolved=False for horizon={virtual_horizon}, "
            f"got {result['resolved']!r}"
        )
    if result["reason"] != "virtual_horizon_exceeded":
        raise RuntimeError(
            f"expected reason='virtual_horizon_exceeded' for horizon={virtual_horizon}, "
            f"got {result['reason']!r}"
        )
    if result["simulated_timestep_count"] != virtual_horizon:
        raise RuntimeError(
            f"expected simulated_timestep_count={virtual_horizon}, "
            f"got {result['simulated_timestep_count']!r}"
        )
    if result["t_virtual_trigger"] is not None:
        raise RuntimeError(
            f"expected t_virtual_trigger=None for horizon={virtual_horizon}, "
            f"got {result['t_virtual_trigger']!r}"
        )
    if result["t_level_2_candidate"] != result["t_level_1"]:
        raise RuntimeError(
            "expected unresolved Level 1 fallback "
            f"t_level_2_candidate={result['t_level_1']!r}, "
            f"got {result['t_level_2_candidate']!r}"
        )


def _print_boundary_case_summary(summary, result_b, real_tmax, merge):
    print(
        f"\nBoundary case horizon={summary['boundary_virtual_horizon']} "
        f"status={summary['status']}"
    )
    for key in (
        "boundary_virtual_horizon",
        "official_resolved",
        "short_tmax_resolved",
        "official_reason",
        "short_tmax_reason",
        "official_simulated_timestep_count",
        "short_tmax_simulated_timestep_count",
        "ab_result_equal",
        "real_world_unchanged",
        "real_rng_unchanged",
        "real_order_control_rng_unchanged",
        "measured_short_mimic_tmax",
        "measured_short_mimic_tsize",
        "measured_short_traveltime_actual_length",
        "status",
    ):
        print(f"  {key}: {summary.get(key)}")
    timing = result_b.get("timing", {})
    print(f"  snapshot_timestep: {merge.W.T}")
    print(f"  virtual_horizon: {summary['boundary_virtual_horizon']}")
    print(f"  expected_official_mimic_tmax: {max(real_tmax, (merge.W.T + 200) * merge.W.DELTAT)}")
    print(f"  expected_short_mimic_tmax: {(merge.W.T + 200) * merge.W.DELTAT}")
    print(f"  measured_short_mimic_tmax: {timing.get('mimic_tmax')}")
    print(f"  measured_short_mimic_tsize: {timing.get('mimic_tsize')}")
    print(
        "  measured_short_traveltime_actual_length: "
        f"{timing.get('traveltime_actual_length')}"
    )
    print(f"  measured_short_k_mat_shape: {timing.get('k_mat_shape')}")
    print(
        "  measured_short_simulated_timestep_count: "
        f"{summary.get('short_tmax_simulated_timestep_count')}"
    )
    if summary.get("exception_or_mismatch_summary"):
        print(
            "  exception_or_mismatch_summary: "
            f"{summary['exception_or_mismatch_summary']}"
        )


def _run_boundary_virtual_horizon_ab(virtual_horizon):
    label = f"Boundary virtual_horizon_exceeded horizon={virtual_horizon}"
    print(f"\n{'=' * 72}")
    print(label)
    print(
        "  base case: tests_order_control_batch_t_trigger_level_2_reference."
        "test_virtual_horizon_exceeded"
    )
    print(f"  clearance: {virtual_horizon + 1} (virtual_horizon + 1)")

    short_tmax_estimate = _get_short_tmax_estimate()
    merge, trigger, t_level_1, real_tmax = _build_virtual_horizon_exceeded_boundary_case(
        virtual_horizon
    )
    summary = {
        "boundary_virtual_horizon": virtual_horizon,
        "official_resolved": None,
        "short_tmax_resolved": None,
        "official_reason": None,
        "short_tmax_reason": None,
        "official_simulated_timestep_count": None,
        "short_tmax_simulated_timestep_count": None,
        "ab_result_equal": None,
        "real_world_unchanged": None,
        "real_rng_unchanged": None,
        "real_order_control_rng_unchanged": None,
        "measured_short_mimic_tmax": None,
        "measured_short_mimic_tsize": None,
        "measured_short_traveltime_actual_length": None,
        "status": "exception",
        "exception_or_mismatch_summary": None,
    }
    result_b = {"timing": {}}
    try:
        result_a = _run_official_estimate(merge, trigger, t_level_1, virtual_horizon)
        summary["official_resolved"] = result_a["result"]["resolved"]
        summary["official_reason"] = result_a["result"]["reason"]
        summary["official_simulated_timestep_count"] = result_a["result"][
            "simulated_timestep_count"
        ]
        _assert_boundary_horizon_exceeded_result(result_a["result"], virtual_horizon)

        result_b = _run_short_tmax_estimate(
            merge,
            trigger,
            t_level_1,
            virtual_horizon,
            short_tmax_estimate,
        )
        summary["short_tmax_resolved"] = result_b["result"]["resolved"]
        summary["short_tmax_reason"] = result_b["result"]["reason"]
        summary["short_tmax_simulated_timestep_count"] = result_b["result"][
            "simulated_timestep_count"
        ]
        summary["measured_short_mimic_tmax"] = result_b.get("timing", {}).get(
            "mimic_tmax"
        )
        summary["measured_short_mimic_tsize"] = result_b.get("timing", {}).get(
            "mimic_tsize"
        )
        summary["measured_short_traveltime_actual_length"] = result_b.get(
            "timing", {}
        ).get("traveltime_actual_length")
        _assert_boundary_horizon_exceeded_result(result_b["result"], virtual_horizon)

        _compare_ab_results(label, result_a, result_b)
        summary["ab_result_equal"] = True
        summary["real_world_unchanged"] = True
        summary["real_rng_unchanged"] = True
        summary["real_order_control_rng_unchanged"] = True
        summary["status"] = "passed"
        _print_boundary_case_summary(summary, result_b, real_tmax, merge)
        return summary
    except RuntimeError as exc:
        summary["status"] = "failed"
        summary["exception_or_mismatch_summary"] = str(exc)
        _print_boundary_case_summary(summary, result_b, real_tmax, merge)
        return summary
    except Exception as exc:
        summary["status"] = "exception"
        summary["exception_or_mismatch_summary"] = repr(exc)
        _print_boundary_case_summary(summary, result_b, real_tmax, merge)
        return summary


def _assert_large_real_tmax_mimic_expectations(
    merge,
    real_tmax,
    virtual_horizon,
    result_b,
):
    snapshot_timestep = merge.W.T
    expected_official_mimic_tmax = max(
        real_tmax,
        (snapshot_timestep + 200) * merge.W.DELTAT,
    )
    expected_short_mimic_tmax = (snapshot_timestep + 200) * merge.W.DELTAT
    timing = result_b.get("timing", {})

    if real_tmax != BOUNDARY_LARGE_REAL_TMAX:
        raise RuntimeError(
            f"expected real_W.TMAX={BOUNDARY_LARGE_REAL_TMAX}, got {real_tmax!r}"
        )
    if expected_official_mimic_tmax != BOUNDARY_LARGE_REAL_TMAX:
        raise RuntimeError(
            "expected official mimic TMAX "
            f"{BOUNDARY_LARGE_REAL_TMAX}, got {expected_official_mimic_tmax!r}"
        )
    if expected_short_mimic_tmax != 210:
        raise RuntimeError(
            f"expected short mimic TMAX 210, got {expected_short_mimic_tmax!r}"
        )
    if timing.get("mimic_tmax") != 210:
        raise RuntimeError(
            f"expected measured short mimic_tmax=210, got {timing.get('mimic_tmax')!r}"
        )
    if timing.get("mimic_tsize") != 210:
        raise RuntimeError(
            f"expected measured short mimic_tsize=210, got {timing.get('mimic_tsize')!r}"
        )
    if timing.get("traveltime_actual_length") != 210:
        raise RuntimeError(
            "expected measured short traveltime_actual_length=210, "
            f"got {timing.get('traveltime_actual_length')!r}"
        )
    virtual_loop_final_timestep = snapshot_timestep + virtual_horizon
    if virtual_loop_final_timestep != 210:
        raise RuntimeError(
            "expected virtual loop final timestep 210, "
            f"got {virtual_loop_final_timestep!r}"
        )


def _print_large_real_tmax_boundary_case_summary(summary, merge):
    print(
        f"\nBoundary case {summary['case_name']} "
        f"status={summary['status']}"
    )
    for key in (
        "case_name",
        "real_world_tmax",
        "snapshot_timestep",
        "virtual_horizon",
        "expected_official_mimic_tmax",
        "expected_short_mimic_tmax",
        "measured_short_mimic_tmax",
        "measured_short_mimic_tsize",
        "measured_short_traveltime_actual_length",
        "official_resolved",
        "short_tmax_resolved",
        "official_reason",
        "short_tmax_reason",
        "official_simulated_timestep_count",
        "short_tmax_simulated_timestep_count",
        "ab_result_equal",
        "real_world_unchanged",
        "real_rng_unchanged",
        "real_order_control_rng_unchanged",
        "status",
    ):
        print(f"  {key}: {summary.get(key)}")
    print(
        "  virtual_loop_final_timestep: "
        f"{summary['snapshot_timestep'] + summary['virtual_horizon']}"
    )
    print(
        "  boundary relation: "
        f"snapshot={summary['snapshot_timestep']}, "
        f"short mimic TSIZE={summary['measured_short_mimic_tsize']}, "
        f"virtual loop final={summary['snapshot_timestep'] + summary['virtual_horizon']}, "
        f"simulated_timestep_count={summary['official_simulated_timestep_count']}"
    )
    if summary.get("exception_or_mismatch_summary"):
        print(
            "  exception_or_mismatch_summary: "
            f"{summary['exception_or_mismatch_summary']}"
        )


def _run_large_real_tmax_virtual_horizon_200_short_tmax_boundary_ab():
    case_name = BOUNDARY_LARGE_REAL_TMAX_SHORT_TMAX_BOUNDARY_CASE_NAME
    virtual_horizon = BOUNDARY_LARGE_REAL_TMAX_VIRTUAL_HORIZON
    label = (
        "Boundary large real TMAX virtual_horizon_200 short TMAX divergence case"
    )
    print(f"\n{'=' * 72}")
    print(label)
    print(f"  case_name: {case_name}")
    print(
        "  base case: tests_order_control_batch_t_trigger_level_2_reference."
        "test_virtual_horizon_exceeded"
    )
    print(f"  real_world_tmax: {BOUNDARY_LARGE_REAL_TMAX}")
    print(f"  virtual_horizon: {virtual_horizon}")
    print(f"  clearance: {virtual_horizon + 1} (virtual_horizon + 1)")

    short_tmax_estimate = _get_short_tmax_estimate()
    merge, trigger, t_level_1, real_tmax = _build_virtual_horizon_exceeded_boundary_case(
        virtual_horizon,
        real_world_tmax=BOUNDARY_LARGE_REAL_TMAX,
    )
    snapshot_timestep = merge.W.T
    expected_official_mimic_tmax = max(
        real_tmax,
        (snapshot_timestep + 200) * merge.W.DELTAT,
    )
    expected_short_mimic_tmax = (snapshot_timestep + 200) * merge.W.DELTAT
    summary = {
        "case_name": case_name,
        "boundary_virtual_horizon": virtual_horizon,
        "real_world_tmax": real_tmax,
        "snapshot_timestep": snapshot_timestep,
        "virtual_horizon": virtual_horizon,
        "expected_official_mimic_tmax": expected_official_mimic_tmax,
        "expected_short_mimic_tmax": expected_short_mimic_tmax,
        "measured_short_mimic_tmax": None,
        "measured_short_mimic_tsize": None,
        "measured_short_traveltime_actual_length": None,
        "official_resolved": None,
        "short_tmax_resolved": None,
        "official_reason": None,
        "short_tmax_reason": None,
        "official_simulated_timestep_count": None,
        "short_tmax_simulated_timestep_count": None,
        "ab_result_equal": None,
        "real_world_unchanged": None,
        "real_rng_unchanged": None,
        "real_order_control_rng_unchanged": None,
        "status": "exception",
        "exception_or_mismatch_summary": None,
    }
    result_b = {"timing": {}}
    try:
        result_a = _run_official_estimate(merge, trigger, t_level_1, virtual_horizon)
        summary["official_resolved"] = result_a["result"]["resolved"]
        summary["official_reason"] = result_a["result"]["reason"]
        summary["official_simulated_timestep_count"] = result_a["result"][
            "simulated_timestep_count"
        ]
        _assert_boundary_horizon_exceeded_result(result_a["result"], virtual_horizon)

        result_b = _run_short_tmax_estimate(
            merge,
            trigger,
            t_level_1,
            virtual_horizon,
            short_tmax_estimate,
        )
        summary["short_tmax_resolved"] = result_b["result"]["resolved"]
        summary["short_tmax_reason"] = result_b["result"]["reason"]
        summary["short_tmax_simulated_timestep_count"] = result_b["result"][
            "simulated_timestep_count"
        ]
        summary["measured_short_mimic_tmax"] = result_b.get("timing", {}).get(
            "mimic_tmax"
        )
        summary["measured_short_mimic_tsize"] = result_b.get("timing", {}).get(
            "mimic_tsize"
        )
        summary["measured_short_traveltime_actual_length"] = result_b.get(
            "timing", {}
        ).get("traveltime_actual_length")
        _assert_boundary_horizon_exceeded_result(result_b["result"], virtual_horizon)
        _assert_large_real_tmax_mimic_expectations(
            merge,
            real_tmax,
            virtual_horizon,
            result_b,
        )

        _compare_ab_results(label, result_a, result_b)
        summary["ab_result_equal"] = True
        summary["real_world_unchanged"] = True
        summary["real_rng_unchanged"] = True
        summary["real_order_control_rng_unchanged"] = True
        summary["status"] = "passed"
        _print_large_real_tmax_boundary_case_summary(summary, merge)
        return summary
    except RuntimeError as exc:
        summary["status"] = "failed"
        summary["exception_or_mismatch_summary"] = str(exc)
        _print_large_real_tmax_boundary_case_summary(summary, merge)
        return summary
    except Exception as exc:
        summary["status"] = "exception"
        summary["exception_or_mismatch_summary"] = repr(exc)
        _print_large_real_tmax_boundary_case_summary(summary, merge)
        return summary


def _boundary_case_failure_label(item):
    if item.get("case_name"):
        return (
            f"case={item['case_name']} "
            f"horizon={item.get('virtual_horizon', item.get('boundary_virtual_horizon'))}"
        )
    return f"boundary horizon={item['boundary_virtual_horizon']}"


def _run_boundary_small_cases_diagnostic():
    print(f"\n{'=' * 72}")
    print("Small-scale boundary A/B cases (virtual_horizon_exceeded at horizon end)")
    print(f"  boundary horizons: {BOUNDARY_VIRTUAL_HORIZONS}")
    summaries = []
    for virtual_horizon in BOUNDARY_VIRTUAL_HORIZONS:
        summaries.append(_run_boundary_virtual_horizon_ab(virtual_horizon))
    summaries.append(_run_large_real_tmax_virtual_horizon_200_short_tmax_boundary_ab())

    print(f"\n{'-' * 72}")
    print("Boundary small-case overall summary")
    for item in summaries:
        label = _boundary_case_failure_label(item)
        print(
            f"  {label} "
            f"status={item['status']} "
            f"official_steps={item['official_simulated_timestep_count']} "
            f"short_steps={item['short_tmax_simulated_timestep_count']} "
            f"ab_equal={item['ab_result_equal']}"
        )

    passed = [item for item in summaries if item["status"] == "passed"]
    if len(passed) == len(summaries):
        print(
            "\nBoundary small-case confirmation succeeded: "
            "virtual_horizon 199/200 horizon-end cases and the large real TMAX "
            "virtual_horizon 200 short TMAX divergence case all passed."
        )
    else:
        print(
            "\nBoundary small-case confirmation did not succeed for all configured "
            f"cases ({len(passed)}/{len(summaries)} passed)."
        )
    return summaries


def _assert_real_world_unchanged(real_W, before_snapshot, branch_mod):
    after_snapshot = branch_mod._world_comparison_snapshot(real_W)
    comparison = branch_mod._compare_world_snapshots(before_snapshot, after_snapshot)
    if not all(item["match"] for item in comparison):
        raise RuntimeError("real_W changed during grid5000 A/B")


def _validate_branch_timestep_candidate(real_W, branch_T, eligible_node_names):
    reasons = []
    if branch_T >= real_W.TMAX:
        reasons.append(f"branch_T={branch_T} is not before TMAX={real_W.TMAX}")
    if branch_T + FORWARD_STEPS > real_W.TMAX:
        reasons.append(
            f"{FORWARD_STEPS}-step forward from T={branch_T} exceeds "
            f"TMAX={real_W.TMAX}"
        )
    if real_W.T != branch_T:
        reasons.append(f"real_W.T={real_W.T} != branch_T={branch_T}")
    level2_nodes = [
        node_name
        for node_name in eligible_node_names
        if real_W.get_node(node_name).order_control_batch_t_trigger_level == 2
    ]
    if not level2_nodes:
        reasons.append("no Level 2 BATCH nodes among eligible nodes")
    running_vehicle_count = sum(
        1 for veh in real_W.VEHICLES.values() if veh.state == "run"
    )
    if running_vehicle_count == 0:
        reasons.append(
            "no running vehicles at branch timestep (simulation may have ended)"
        )
    if reasons:
        return False, "; ".join(reasons)
    return True, None


def _configure_fork_virtual_horizon(fork_W, eligible_node_names, virtual_horizon):
    configured_node_names = []
    for node_name in eligible_node_names:
        node = fork_W.get_node(node_name)
        if (
            node.order_control_eligible
            and node.order_control_type == "batch"
            and node.order_control_batch_t_trigger_level == 2
        ):
            node.order_control_batch_virtual_horizon = virtual_horizon
            configured_node_names.append(node_name)
    if not configured_node_names:
        raise RuntimeError(
            "no Level 2 BATCH nodes configured with virtual horizon on fork"
        )
    return configured_node_names


def _min_or_none(values):
    cleaned = [value for value in values if value is not None]
    if not cleaned:
        return None
    return min(cleaned)


def _max_or_none(values):
    cleaned = [value for value in values if value is not None]
    if not cleaned:
        return None
    return max(cleaned)


def _empty_boundary_metrics():
    return {
        "official_simulated_steps_min": None,
        "official_simulated_steps_median": None,
        "official_simulated_steps_max": None,
        "short_tmax_simulated_steps_min": None,
        "short_tmax_simulated_steps_median": None,
        "short_tmax_simulated_steps_max": None,
        "official_horizon_end_call_count": 0,
        "short_tmax_horizon_end_call_count": 0,
        "horizon_end_flags_equal": None,
        "horizon_end_results_equal": None,
        "official_unresolved_call_count": 0,
        "short_tmax_unresolved_call_count": 0,
        "official_unresolved_simulated_steps": [],
        "short_tmax_unresolved_simulated_steps": [],
        "unresolved_details_equal": None,
    }


def _call_reached_horizon_end(record, configured_virtual_horizon):
    """
    True when the Level 2 virtual loop exhausted all advance steps.

    Reference: uxsim/order_control_batch_level_2_reference._run_limited_virtual_loop
    iterates offset in range(virtual_horizon + 1). offset == 0 is the snapshot
    timestep (no advance). Each offset > 0 increments simulated_timestep_count by
    1 after advancing mimic_W.T. Full loop exhaustion without early return yields
    simulated_timestep_count == virtual_horizon.
    """
    return (
        record.get("simulated_timestep_count") == configured_virtual_horizon
    )


def _simulated_step_values(records):
    return [
        record.get("simulated_timestep_count")
        for record in records
        if record.get("simulated_timestep_count") is not None
    ]


def _simulated_step_stats(records):
    values = _simulated_step_values(records)
    return {
        "min": _min_or_none(values),
        "median": _median_or_none(values),
        "max": _max_or_none(values),
    }


def _unresolved_call_details(records):
    unresolved_records = [
        record for record in records if record.get("resolved") is False
    ]
    return {
        "count": len(unresolved_records),
        "call_indexes": [record["call_index"] for record in unresolved_records],
        "simulated_steps": [
            record.get("simulated_timestep_count")
            for record in unresolved_records
        ],
    }


def _compare_horizon_end_flags(
    official_records,
    short_records,
    configured_virtual_horizon,
):
    if len(official_records) != len(short_records):
        return False, "Level 2 call count mismatch for horizon-end flag comparison"
    for official_record, short_record in zip(official_records, short_records):
        official_flag = _call_reached_horizon_end(
            official_record,
            configured_virtual_horizon,
        )
        short_flag = _call_reached_horizon_end(
            short_record,
            configured_virtual_horizon,
        )
        if official_flag != short_flag:
            return False, (
                f"call_index={official_record['call_index']} "
                f"snapshot_timestep={official_record['snapshot_timestep']} "
                f"node_name={official_record['node_name']} "
                f"trigger_vehicle_name={official_record['trigger_vehicle_name']} "
                f"configured_virtual_horizon={configured_virtual_horizon} "
                f"official_simulated_timestep_count="
                f"{official_record.get('simulated_timestep_count')} "
                f"short_tmax_simulated_timestep_count="
                f"{short_record.get('simulated_timestep_count')}"
            )
    return True, None


def _compare_horizon_end_results(
    official_records,
    short_records,
    configured_virtual_horizon,
):
    official_horizon_end_records = [
        record
        for record in official_records
        if _call_reached_horizon_end(record, configured_virtual_horizon)
    ]
    if not official_horizon_end_records:
        return None
    short_horizon_end_records = [
        record
        for record in short_records
        if _call_reached_horizon_end(record, configured_virtual_horizon)
    ]
    if len(official_horizon_end_records) != len(short_horizon_end_records):
        return False
    compare_keys = LEVEL2_RESULT_KEYS + ("adopted_t_trigger",)
    for official_record, short_record in zip(
        official_horizon_end_records,
        short_horizon_end_records,
    ):
        if official_record.get("call_index") != short_record.get("call_index"):
            return False
        for key in compare_keys:
            if official_record.get(key) != short_record.get(key):
                return False
    return True


def _compare_unresolved_details(official_records, short_records):
    official_details = _unresolved_call_details(official_records)
    short_details = _unresolved_call_details(short_records)
    return (
        official_details["count"] == short_details["count"]
        and official_details["call_indexes"] == short_details["call_indexes"]
        and official_details["simulated_steps"] == short_details["simulated_steps"]
    )


def _aggregate_simulated_step_boundary_metrics(
    official_records,
    short_records,
    configured_virtual_horizon,
):
    if not official_records and not short_records:
        return _empty_boundary_metrics()

    official_stats = _simulated_step_stats(official_records)
    short_stats = _simulated_step_stats(short_records)
    official_unresolved = _unresolved_call_details(official_records)
    short_unresolved = _unresolved_call_details(short_records)

    horizon_end_flags_equal = None
    horizon_end_mismatch_summary = None
    if official_records and short_records:
        horizon_end_flags_equal, horizon_end_mismatch_summary = (
            _compare_horizon_end_flags(
                official_records,
                short_records,
                configured_virtual_horizon,
            )
        )

    unresolved_details_equal = None
    if official_records or short_records:
        unresolved_details_equal = _compare_unresolved_details(
            official_records,
            short_records,
        )

    horizon_end_results_equal = None
    if official_records and short_records:
        horizon_end_results_equal = _compare_horizon_end_results(
            official_records,
            short_records,
            configured_virtual_horizon,
        )

    return {
        "official_simulated_steps_min": official_stats["min"],
        "official_simulated_steps_median": official_stats["median"],
        "official_simulated_steps_max": official_stats["max"],
        "short_tmax_simulated_steps_min": short_stats["min"],
        "short_tmax_simulated_steps_median": short_stats["median"],
        "short_tmax_simulated_steps_max": short_stats["max"],
        "official_horizon_end_call_count": sum(
            1
            for record in official_records
            if _call_reached_horizon_end(record, configured_virtual_horizon)
        ),
        "short_tmax_horizon_end_call_count": sum(
            1
            for record in short_records
            if _call_reached_horizon_end(record, configured_virtual_horizon)
        ),
        "horizon_end_flags_equal": horizon_end_flags_equal,
        "horizon_end_results_equal": horizon_end_results_equal,
        "official_unresolved_call_count": official_unresolved["count"],
        "short_tmax_unresolved_call_count": short_unresolved["count"],
        "official_unresolved_simulated_steps": official_unresolved["simulated_steps"],
        "short_tmax_unresolved_simulated_steps": short_unresolved["simulated_steps"],
        "unresolved_details_equal": unresolved_details_equal,
        "horizon_end_mismatch_summary": horizon_end_mismatch_summary,
    }


def _validate_simulated_step_boundary_metrics(boundary_metrics):
    issues = []
    if boundary_metrics.get("horizon_end_flags_equal") is False:
        issues.append(
            "horizon-end flag mismatch: "
            f"{boundary_metrics.get('horizon_end_mismatch_summary')}"
        )
    if boundary_metrics.get("horizon_end_results_equal") is False:
        issues.append(
            "horizon-end Level 2 result mismatch"
        )
    if boundary_metrics.get("unresolved_details_equal") is False:
        issues.append(
            "unresolved detail mismatch: "
            f"official_unresolved_call_count="
            f"{boundary_metrics.get('official_unresolved_call_count')}, "
            f"short_tmax_unresolved_call_count="
            f"{boundary_metrics.get('short_tmax_unresolved_call_count')}, "
            f"official_unresolved_simulated_steps="
            f"{boundary_metrics.get('official_unresolved_simulated_steps')}, "
            f"short_tmax_unresolved_simulated_steps="
            f"{boundary_metrics.get('short_tmax_unresolved_simulated_steps')}"
        )
    if issues:
        raise RuntimeError("; ".join(issues))


def _median_or_none(values):
    cleaned = [value for value in values if value is not None]
    if not cleaned:
        return None
    return statistics.median(cleaned)


def _sum_or_zero(values):
    return sum(value for value in values if value is not None)


def _build_matrix_cell_summary(
    *,
    snapshot_timestep,
    configured_virtual_horizon,
    configured_node_names,
    official_result,
    short_result,
    real_W,
    status,
    ab_result_equal=None,
    traffic_state_equal=None,
    fork_rng_equal=None,
    fork_order_control_rng_equal=None,
    real_world_unchanged=None,
    exception_or_mismatch_summary=None,
):
    official_records = official_result["records"]
    short_records = short_result["records"]
    expected_official_mimic_tmax = None
    measured_short_mimic_tmax = _first_record_value(short_records, "mimic_tmax")
    measured_short_mimic_tsize = _first_record_value(short_records, "mimic_tsize")
    if official_records:
        first_snapshot = official_records[0]["snapshot_timestep"]
        local_tmax = (first_snapshot + 200) * real_W.DELTAT
        expected_official_mimic_tmax = max(real_W.TMAX, local_tmax)
    elif short_records:
        first_snapshot = short_records[0]["snapshot_timestep"]
        local_tmax = (first_snapshot + 200) * real_W.DELTAT
        expected_official_mimic_tmax = max(real_W.TMAX, local_tmax)

    official_forward = official_result.get("forward_seconds")
    short_forward = short_result.get("forward_seconds")
    forward_speedup_ratio = None
    if (
        official_forward is not None
        and short_forward is not None
        and short_forward > 0
    ):
        forward_speedup_ratio = official_forward / short_forward

    boundary_metrics = _aggregate_simulated_step_boundary_metrics(
        official_records,
        short_records,
        configured_virtual_horizon,
    )

    summary = {
        "snapshot_timestep": snapshot_timestep,
        "configured_virtual_horizon": configured_virtual_horizon,
        "configured_node_count": len(configured_node_names),
        "configured_node_names": list(configured_node_names),
        "official_forward_seconds": official_forward,
        "short_tmax_forward_seconds": short_forward,
        "forward_speedup_ratio": forward_speedup_ratio,
        "official_level2_call_count": len(official_records),
        "short_tmax_level2_call_count": len(short_records),
        "official_level2_total_seconds": _sum_or_zero(
            record.get("total_seconds") for record in official_records
        ),
        "short_tmax_level2_total_seconds": _sum_or_zero(
            record.get("total_seconds") for record in short_records
        ),
        "official_level2_median_seconds": _median_or_none(
            [record.get("total_seconds") for record in official_records]
        ),
        "short_tmax_level2_median_seconds": _median_or_none(
            [record.get("total_seconds") for record in short_records]
        ),
        "short_tmax_finalize_median_seconds": _median_or_none(
            [record.get("finalize_seconds") for record in short_records]
        ),
        "short_tmax_mimic_build_median_seconds": _median_or_none(
            [record.get("mimic_build_seconds") for record in short_records]
        ),
        "short_tmax_virtual_loop_median_seconds": _median_or_none(
            [record.get("virtual_loop_seconds") for record in short_records]
        ),
        "expected_official_mimic_tmax": expected_official_mimic_tmax,
        "measured_short_mimic_tmax": measured_short_mimic_tmax,
        "measured_short_mimic_tsize": measured_short_mimic_tsize,
        "measured_short_traveltime_actual_length": _first_record_value(
            short_records, "traveltime_actual_length"
        ),
        "measured_short_k_mat_shape": _first_record_value(short_records, "k_mat_shape"),
        "ab_result_equal": ab_result_equal,
        "traffic_state_equal": traffic_state_equal,
        "fork_rng_equal": fork_rng_equal,
        "fork_order_control_rng_equal": fork_order_control_rng_equal,
        "real_world_unchanged": real_world_unchanged,
        "status": status,
        "exception_or_mismatch_summary": exception_or_mismatch_summary,
        **{
            key: boundary_metrics[key]
            for key in _empty_boundary_metrics()
            if key != "horizon_end_mismatch_summary"
        },
    }
    return summary


def _first_record_value(records, key):
    for record in records:
        if key in record:
            return record[key]
    return None


def _print_matrix_cell_summary(summary):
    print(
        f"\nMatrix cell T={summary['snapshot_timestep']} "
        f"horizon={summary['configured_virtual_horizon']} "
        f"status={summary['status']}"
    )
    print(
        f"  configured_node_count: {summary['configured_node_count']}"
    )
    print(f"  configured_node_names: {summary['configured_node_names']}")
    for key in (
        "official_forward_seconds",
        "short_tmax_forward_seconds",
        "forward_speedup_ratio",
        "official_level2_call_count",
        "short_tmax_level2_call_count",
        "official_level2_total_seconds",
        "short_tmax_level2_total_seconds",
        "official_level2_median_seconds",
        "short_tmax_level2_median_seconds",
        "short_tmax_finalize_median_seconds",
        "short_tmax_mimic_build_median_seconds",
        "short_tmax_virtual_loop_median_seconds",
        "expected_official_mimic_tmax",
        "measured_short_mimic_tmax",
        "measured_short_mimic_tsize",
        "measured_short_traveltime_actual_length",
        "measured_short_k_mat_shape",
        "official_simulated_steps_min",
        "official_simulated_steps_median",
        "official_simulated_steps_max",
        "short_tmax_simulated_steps_min",
        "short_tmax_simulated_steps_median",
        "short_tmax_simulated_steps_max",
        "official_horizon_end_call_count",
        "short_tmax_horizon_end_call_count",
        "horizon_end_flags_equal",
        "horizon_end_results_equal",
        "official_unresolved_call_count",
        "short_tmax_unresolved_call_count",
        "official_unresolved_simulated_steps",
        "short_tmax_unresolved_simulated_steps",
        "unresolved_details_equal",
        "traffic_state_equal",
        "fork_rng_equal",
        "fork_order_control_rng_equal",
        "real_world_unchanged",
    ):
        print(f"  {key}: {summary.get(key)}")
    if summary.get("exception_or_mismatch_summary"):
        print(f"  exception_or_mismatch_summary: {summary['exception_or_mismatch_summary']}")


def _print_matrix_summary_table(cell_summaries):
    print(f"\n{'=' * 72}")
    print("Grid matrix overall summary")
    print("=" * 72)
    header = (
        "snapshot_timestep",
        "virtual_horizon",
        "status",
        "Level 2 call count",
        "A/B result equality",
        "traffic state equality",
        "RNG equality",
        "exception or mismatch summary",
    )
    print("  " + " | ".join(header))
    for summary in cell_summaries:
        level2_call_count = (
            f"official={summary['official_level2_call_count']}, "
            f"short={summary['short_tmax_level2_call_count']}"
        )
        rng_equal = (
            summary.get("fork_rng_equal")
            if summary.get("fork_order_control_rng_equal") is None
            else (
                summary.get("fork_rng_equal")
                and summary.get("fork_order_control_rng_equal")
            )
        )
        print(
            "  "
            f"{summary['snapshot_timestep']} | "
            f"{summary['configured_virtual_horizon']} | "
            f"{summary['status']} | "
            f"{level2_call_count} | "
            f"{summary.get('ab_result_equal')} | "
            f"{summary.get('traffic_state_equal')} | "
            f"{rng_equal} | "
            f"{summary.get('exception_or_mismatch_summary')}"
        )

    passed_cells = [item for item in cell_summaries if item["status"] == "passed"]
    unverified_cells = [
        item for item in cell_summaries if item["status"] == "no_level2_calls"
    ]
    failed_cells = [item for item in cell_summaries if item["status"] == "failed"]
    exception_cells = [
        item for item in cell_summaries if item["status"] == "exception"
    ]
    if unverified_cells:
        print("\nUnverified cells (no_level2_calls):")
        for item in unverified_cells:
            print(
                f"  T={item['snapshot_timestep']} "
                f"horizon={item['configured_virtual_horizon']}"
            )
    if failed_cells or exception_cells:
        print("\nFailed or exceptional cells:")
        for item in failed_cells + exception_cells:
            print(
                f"  T={item['snapshot_timestep']} "
                f"horizon={item['configured_virtual_horizon']} "
                f"status={item['status']}: "
                f"{item.get('exception_or_mismatch_summary')}"
            )

    print(f"\n{'-' * 72}")
    print("Grid matrix boundary verification summary")
    boundary_header = (
        "snapshot_timestep",
        "virtual_horizon",
        "status",
        "official_max_simulated_steps",
        "short_max_simulated_steps",
        "horizon_end_call_count",
        "horizon_end_results_equal",
        "unresolved_call_count",
        "unresolved_simulated_steps",
    )
    print("  " + " | ".join(boundary_header))
    for summary in cell_summaries:
        horizon_end_call_count = (
            f"official={summary.get('official_horizon_end_call_count')}, "
            f"short={summary.get('short_tmax_horizon_end_call_count')}"
        )
        unresolved_call_count = (
            f"official={summary.get('official_unresolved_call_count')}, "
            f"short={summary.get('short_tmax_unresolved_call_count')}"
        )
        unresolved_simulated_steps = (
            f"official={summary.get('official_unresolved_simulated_steps')}, "
            f"short={summary.get('short_tmax_unresolved_simulated_steps')}"
        )
        print(
            "  "
            f"{summary['snapshot_timestep']} | "
            f"{summary['configured_virtual_horizon']} | "
            f"{summary['status']} | "
            f"{summary.get('official_simulated_steps_max')} | "
            f"{summary.get('short_tmax_simulated_steps_max')} | "
            f"{horizon_end_call_count} | "
            f"{summary.get('horizon_end_results_equal')} | "
            f"{unresolved_call_count} | "
            f"{unresolved_simulated_steps}"
        )

    cells_with_horizon_end_calls = [
        item
        for item in cell_summaries
        if (item.get("official_horizon_end_call_count") or 0) > 0
        or (item.get("short_tmax_horizon_end_call_count") or 0) > 0
    ]
    cells_without_horizon_end_calls = [
        item
        for item in cell_summaries
        if item not in cells_with_horizon_end_calls
    ]
    cells_199_200_with_horizon_end = [
        item
        for item in cells_with_horizon_end_calls
        if item.get("configured_virtual_horizon") in (199, 200)
        and (item.get("official_horizon_end_call_count") or 0) > 0
    ]
    strong_boundary_confirmed = any(
        item.get("status") == "passed"
        and item.get("configured_virtual_horizon") in (199, 200)
        and (item.get("official_horizon_end_call_count") or 0) > 0
        and item.get("horizon_end_results_equal") is True
        for item in cell_summaries
    )

    print("\nBoundary verification classification:")
    print(
        f"  1. basic A/B comparison passed cells: "
        f"{len(passed_cells)}/{len(cell_summaries)}"
    )
    print(
        f"  2. cells with horizon-end calls: {len(cells_with_horizon_end_calls)}"
    )
    print(
        "  3. cells without horizon-end calls: "
        f"{len(cells_without_horizon_end_calls)}"
    )
    print(
        "  4. horizon 199/200 cells with actual horizon-end progression: "
        f"{len(cells_199_200_with_horizon_end)}"
    )
    print(
        "  5. horizon 199/200 horizon-end calls with A/B result equality: "
        f"{sum(1 for item in cells_199_200_with_horizon_end if item.get('horizon_end_results_equal') is True)}"
    )

    if len(passed_cells) == len(cell_summaries) and cell_summaries:
        print(
            "\nShort TMAX basic A/B validation succeeded within current diagnostic scope."
        )
    if strong_boundary_confirmed:
        print(
            "\nStrong boundary confirmation: virtual horizon 199 or 200 reached "
            "the horizon end in at least one cell, and A/B results matched on "
            "those horizon-end calls."
        )
    elif len(passed_cells) == len(cell_summaries) and cell_summaries:
        print(
            "\nA/B basic comparison succeeded, but no horizon-end progression "
            "boundary case was confirmed for virtual horizon 199 or 200."
        )


def _run_grid_fork_condition(
    real_W,
    branch_mod,
    *,
    condition,
    estimate_fn,
    include_timing_collector,
    eligible_node_names,
    virtual_horizon,
):
    before_snapshot = branch_mod._world_comparison_snapshot(real_W)
    before_rng = _rng_state_bytes(real_W.rng)
    before_order_control_rng = _rng_state_bytes(real_W.order_control_rng)
    before_t = real_W.T

    fork_W = real_W.copy()
    if fork_W is None:
        raise RuntimeError("World.copy() returned None")
    branch_mod._configure_fork(fork_W)
    configured_node_names = _configure_fork_virtual_horizon(
        fork_W,
        eligible_node_names,
        virtual_horizon,
    )

    collecting_estimate = _make_collecting_estimate(
        estimate_fn,
        include_timing_collector=include_timing_collector,
    )
    l2_module, original_estimate = _patch_level2_reference(collecting_estimate)
    forward_started = time.perf_counter()
    try:
        fork_W.exec_simulation(duration_t2=FORWARD_STEPS * fork_W.DELTAT)
    finally:
        _restore_level2_reference(l2_module, original_estimate)
    forward_seconds = time.perf_counter() - forward_started

    _assert_real_world_unchanged(real_W, before_snapshot, branch_mod)
    if real_W.T != before_t:
        raise RuntimeError("real_W.T changed during grid5000 fork run")
    if _rng_state_bytes(real_W.rng) != before_rng:
        raise RuntimeError("real_W.rng changed during grid5000 fork run")
    if _rng_state_bytes(real_W.order_control_rng) != before_order_control_rng:
        raise RuntimeError("real_W.order_control_rng changed during grid5000 fork run")

    return {
        "condition": condition,
        "fork_W": fork_W,
        "records": list(collecting_estimate.records),
        "forward_seconds": forward_seconds,
        "configured_virtual_horizon": virtual_horizon,
        "configured_node_names": configured_node_names,
    }


def _compare_fork_traffic_states(official_W, short_tmax_W, branch_mod, label):
    snapshot_official = branch_mod._world_comparison_snapshot(official_W)
    snapshot_short = branch_mod._world_comparison_snapshot(short_tmax_W)
    comparison = branch_mod._compare_world_snapshots(snapshot_official, snapshot_short)
    if not all(item["match"] for item in comparison):
        mismatches = [item for item in comparison if not item["match"]]
        raise RuntimeError(
            f"{label}: traffic-state mismatch after {FORWARD_STEPS} steps: "
            f"{mismatches[:3]}"
        )


def _compare_fork_rng(official_W, short_tmax_W, label):
    if _rng_state_bytes(official_W.rng) != _rng_state_bytes(short_tmax_W.rng):
        raise RuntimeError(f"{label}: fork W.rng mismatch after forward")
    if _rng_state_bytes(official_W.order_control_rng) != _rng_state_bytes(
        short_tmax_W.order_control_rng
    ):
        raise RuntimeError(f"{label}: fork order_control_rng mismatch after forward")


def _run_grid_matrix_cell(
    real_W,
    branch_mod,
    *,
    branch_T,
    virtual_horizon,
    eligible_node_names,
    short_tmax_estimate,
    real_before_snapshot,
    real_before_rng,
    real_before_order_control_rng,
    real_before_t,
):
    label = f"grid5000 T={branch_T} horizon={virtual_horizon}"
    condition_results = {}
    official_result = {
        "records": [],
        "forward_seconds": None,
        "configured_virtual_horizon": virtual_horizon,
        "configured_node_names": [],
    }
    short_result = {
        "records": [],
        "forward_seconds": None,
        "configured_virtual_horizon": virtual_horizon,
        "configured_node_names": [],
    }
    try:
        for condition in CONDITION_EXECUTION_ORDER:
            if condition == CONDITION_OFFICIAL:
                result = _run_grid_fork_condition(
                    real_W,
                    branch_mod,
                    condition=condition,
                    estimate_fn=official_estimate,
                    include_timing_collector=False,
                    eligible_node_names=eligible_node_names,
                    virtual_horizon=virtual_horizon,
                )
                condition_results[condition] = result
                official_result = result
            elif condition == CONDITION_SHORT_TMAX:
                result = _run_grid_fork_condition(
                    real_W,
                    branch_mod,
                    condition=condition,
                    estimate_fn=short_tmax_estimate,
                    include_timing_collector=True,
                    eligible_node_names=eligible_node_names,
                    virtual_horizon=virtual_horizon,
                )
                condition_results[condition] = result
                short_result = result
            else:
                raise ValueError(f"unknown condition: {condition!r}")

        _assert_real_world_unchanged(real_W, real_before_snapshot, branch_mod)
        if real_W.T != real_before_t:
            raise RuntimeError("real_W.T changed after grid matrix cell")
        if _rng_state_bytes(real_W.rng) != real_before_rng:
            raise RuntimeError("real_W.rng changed after grid matrix cell")
        if _rng_state_bytes(real_W.order_control_rng) != real_before_order_control_rng:
            raise RuntimeError(
                "real_W.order_control_rng changed after grid matrix cell"
            )

        configured_node_names = official_result["configured_node_names"]

        if not official_result["records"]:
            summary = _build_matrix_cell_summary(
                snapshot_timestep=branch_T,
                configured_virtual_horizon=virtual_horizon,
                configured_node_names=configured_node_names,
                official_result=official_result,
                short_result=short_result,
                real_W=real_W,
                status="no_level2_calls",
                exception_or_mismatch_summary=(
                    "no Level 2 calls during 50-step forward; "
                    "short_tmax correctness not verified for this cell"
                ),
            )
            _print_matrix_cell_summary(summary)
            return summary

        _compare_level2_call_inputs(
            label,
            official_result["records"],
            short_result["records"],
        )
        _compare_level2_call_results(
            label,
            official_result["records"],
            short_result["records"],
        )
        _compare_fork_traffic_states(
            official_result["fork_W"],
            short_result["fork_W"],
            branch_mod,
            label,
        )
        _compare_fork_rng(
            official_result["fork_W"],
            short_result["fork_W"],
            label,
        )

        boundary_metrics = _aggregate_simulated_step_boundary_metrics(
            official_result["records"],
            short_result["records"],
            virtual_horizon,
        )
        _validate_simulated_step_boundary_metrics(boundary_metrics)

        summary = _build_matrix_cell_summary(
            snapshot_timestep=branch_T,
            configured_virtual_horizon=virtual_horizon,
            configured_node_names=configured_node_names,
            official_result=official_result,
            short_result=short_result,
            real_W=real_W,
            status="passed",
            ab_result_equal=True,
            traffic_state_equal=True,
            fork_rng_equal=True,
            fork_order_control_rng_equal=True,
            real_world_unchanged=True,
        )
        _print_matrix_cell_summary(summary)
        return summary
    except RuntimeError as exc:
        configured_node_names = official_result.get("configured_node_names", [])
        summary = _build_matrix_cell_summary(
            snapshot_timestep=branch_T,
            configured_virtual_horizon=virtual_horizon,
            configured_node_names=configured_node_names,
            official_result=official_result,
            short_result=short_result,
            real_W=real_W,
            status="failed",
            ab_result_equal=False,
            exception_or_mismatch_summary=str(exc),
        )
        _print_matrix_cell_summary(summary)
        return summary
    except Exception as exc:
        configured_node_names = official_result.get("configured_node_names", [])
        summary = _build_matrix_cell_summary(
            snapshot_timestep=branch_T,
            configured_virtual_horizon=virtual_horizon,
            configured_node_names=configured_node_names,
            official_result=official_result,
            short_result=short_result,
            real_W=real_W,
            status="exception",
            exception_or_mismatch_summary=repr(exc),
        )
        _print_matrix_cell_summary(summary)
        return summary
    finally:
        for result in condition_results.values():
            if "fork_W" in result:
                del result["fork_W"]


def _run_grid_matrix_diagnostic(branch_mod, grid_mod):
    print(f"\n{'=' * 72}")
    print("grid5000 Level 2 A/B matrix diagnostic")
    print(f"  branch timesteps: {GRID_BRANCH_TIMESTEPS}")
    print(f"  virtual horizons: {LEVEL2_VIRTUAL_HORIZONS}")
    print(f"  forward_steps: {FORWARD_STEPS}")
    print(f"  execution_order: {CONDITION_EXECUTION_ORDER}")
    print(
        f"  virtual horizon attribute: {NODE_LEVEL2_VIRTUAL_HORIZON_ATTR} "
        "(read in uxsim.py Node._resolve_order_control_batch_t_trigger level 2 path)"
    )

    short_tmax_estimate = _get_short_tmax_estimate()
    cell_summaries = []

    for branch_T in GRID_BRANCH_TIMESTEPS:
        print(f"\n{'-' * 72}")
        print(f"Preparing real_W at snapshot timestep T={branch_T}")
        real_W, eligible_node_names, _vehicle_plans = branch_mod._rebuild_world_to_timestep(
            grid_mod,
            branch_T,
        )
        branch_ok, branch_reason = _validate_branch_timestep_candidate(
            real_W,
            branch_T,
            eligible_node_names,
        )
        if not branch_ok:
            print(f"  branch timestep rejected: {branch_reason}")
            for virtual_horizon in LEVEL2_VIRTUAL_HORIZONS:
                rejected_summary = {
                    "snapshot_timestep": branch_T,
                    "configured_virtual_horizon": virtual_horizon,
                    "configured_node_count": 0,
                    "configured_node_names": [],
                    "official_forward_seconds": None,
                    "short_tmax_forward_seconds": None,
                    "forward_speedup_ratio": None,
                    "official_level2_call_count": 0,
                    "short_tmax_level2_call_count": 0,
                    "official_level2_total_seconds": 0.0,
                    "short_tmax_level2_total_seconds": 0.0,
                    "official_level2_median_seconds": None,
                    "short_tmax_level2_median_seconds": None,
                    "short_tmax_finalize_median_seconds": None,
                    "short_tmax_mimic_build_median_seconds": None,
                    "short_tmax_virtual_loop_median_seconds": None,
                    "expected_official_mimic_tmax": None,
                    "measured_short_mimic_tmax": None,
                    "measured_short_mimic_tsize": None,
                    "measured_short_traveltime_actual_length": None,
                    "measured_short_k_mat_shape": None,
                    "ab_result_equal": None,
                    "traffic_state_equal": None,
                    "fork_rng_equal": None,
                    "fork_order_control_rng_equal": None,
                    "real_world_unchanged": None,
                    "status": "exception",
                    "exception_or_mismatch_summary": branch_reason,
                    **_empty_boundary_metrics(),
                }
                cell_summaries.append(rejected_summary)
                _print_matrix_cell_summary(rejected_summary)
            continue

        print(f"  real_W.TMAX: {real_W.TMAX}")
        print(f"  eligible_node_count: {len(eligible_node_names)}")
        print(
            "  default virtual horizon on real_W nodes: "
            f"{real_W.get_node(eligible_node_names[0]).order_control_batch_virtual_horizon}"
        )

        real_before_snapshot = branch_mod._world_comparison_snapshot(real_W)
        real_before_rng = _rng_state_bytes(real_W.rng)
        real_before_order_control_rng = _rng_state_bytes(real_W.order_control_rng)
        real_before_t = real_W.T

        for virtual_horizon in LEVEL2_VIRTUAL_HORIZONS:
            summary = _run_grid_matrix_cell(
                real_W,
                branch_mod,
                branch_T=branch_T,
                virtual_horizon=virtual_horizon,
                eligible_node_names=eligible_node_names,
                short_tmax_estimate=short_tmax_estimate,
                real_before_snapshot=real_before_snapshot,
                real_before_rng=real_before_rng,
                real_before_order_control_rng=real_before_order_control_rng,
                real_before_t=real_before_t,
            )
            cell_summaries.append(summary)

        _assert_real_world_unchanged(real_W, real_before_snapshot, branch_mod)
        if real_W.T != real_before_t:
            raise RuntimeError(f"real_W.T changed after branch T={branch_T} matrix")
        if _rng_state_bytes(real_W.rng) != real_before_rng:
            raise RuntimeError(f"real_W.rng changed after branch T={branch_T} matrix")
        if _rng_state_bytes(real_W.order_control_rng) != real_before_order_control_rng:
            raise RuntimeError(
                f"real_W.order_control_rng changed after branch T={branch_T} matrix"
            )

    _print_matrix_summary_table(cell_summaries)
    return cell_summaries


def _summarize_canonical_vs_short_tmax_diff():
    canonical_lines = _CANONICAL_REFERENCE_PATH.read_text().splitlines()
    short_lines = _SHORT_TMAX_REFERENCE_PATH.read_text().splitlines()
    diff = list(
        difflib.unified_diff(
            canonical_lines,
            short_lines,
            fromfile=str(_CANONICAL_REFERENCE_PATH.relative_to(_REPO_ROOT)),
            tofile=str(_SHORT_TMAX_REFERENCE_PATH.relative_to(_REPO_ROOT)),
            lineterm="",
        )
    )
    print("\nCanonical vs short_tmax diagnostic copy diff summary")
    print("=" * 72)
    print("  basis: diagnostic copy derives from canonical reference")
    print("  expected differences:")
    print("    - diagnostic header comment block")
    print("    - import time")
    print("    - MIMIC_TMAX_MODE constants and default short_local_tmax")
    print("    - _resolve_mimic_tmax()")
    print("    - timing_collector instrumentation")
    print("    - mimic array-shape recording helpers")
    print(f"  unified diff line count: {len(diff)}")
    if diff:
        preview = diff[:40]
        print("  diff preview (first 40 lines):")
        for line in preview:
            print(f"    {line}")
        if len(diff) > 40:
            print(f"    ... ({len(diff) - 40} more diff lines)")


def main():
    previous_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(previous_limit, RECURSION_LIMIT))
    print("Level 2 mimic TMAX A/B diagnostic")
    print("=" * 72)
    print("A: uxsim.order_control_batch_level_2_reference (canonical, unchanged)")
    print("B: diagnostics.order_control.order_control_batch_level_2_short_tmax_reference")
    print(f"  RUN_BOUNDARY_SMALL_CASES: {RUN_BOUNDARY_SMALL_CASES}")
    print(f"  RUN_GRID5000_MATRIX: {RUN_GRID5000_MATRIX}")

    try:
        _summarize_canonical_vs_short_tmax_diff()

        reference_runs_official = []
        reference_runs_short = []

        merge, trigger, t_level_1, vh, real_tmax = _build_arrived_reference_case()
        result_a, result_b = _run_reference_case_ab(
            "Reference case: arrived trigger",
            merge,
            trigger,
            t_level_1,
            vh,
            real_tmax,
        )
        reference_runs_official.append(result_a)
        reference_runs_short.append(result_b)

        merge, trigger, t_level_1, vh, real_tmax = _build_unarrived_reference_case()
        result_a, result_b = _run_reference_case_ab(
            "Reference case: unarrived service unit",
            merge,
            trigger,
            t_level_1,
            vh,
            real_tmax,
        )
        reference_runs_official.append(result_a)
        reference_runs_short.append(result_b)

        boundary_summaries = []
        if RUN_BOUNDARY_SMALL_CASES:
            boundary_summaries = _run_boundary_small_cases_diagnostic()

        matrix_summaries = []
        if RUN_GRID5000_MATRIX:
            branch_mod = _load_world_state_branching_module()
            grid_mod = _load_grid_module()
            matrix_summaries = _run_grid_matrix_diagnostic(branch_mod, grid_mod)

        _print_timing_summary(
            "reference official Level 2 calls",
            reference_runs_official,
            include_phase_timing=False,
        )
        _print_timing_summary(
            "reference short_tmax Level 2 calls",
            [
                {
                    "condition": CONDITION_SHORT_TMAX,
                    "result": item["result"],
                    "total_seconds": item["total_seconds"],
                    **item.get("timing", {}),
                }
                for item in reference_runs_short
            ],
            include_phase_timing=True,
        )

        if matrix_summaries:
            passed_count = sum(
                1 for item in matrix_summaries if item["status"] == "passed"
            )
            print(
                f"\nGrid matrix cells passed: {passed_count}/{len(matrix_summaries)}"
            )

        if RUN_BOUNDARY_SMALL_CASES:
            print(
                f"\nBoundary small cases passed: "
                f"{sum(1 for item in boundary_summaries if item['status'] == 'passed')}"
                f"/{len(boundary_summaries)}"
            )
            failed_boundary_summaries = [
                item
                for item in boundary_summaries
                if item["status"] != "passed"
            ]
            if failed_boundary_summaries:
                failure_lines = [
                    (
                        f"{_boundary_case_failure_label(item)} "
                        f"status={item['status']}: "
                        f"{item.get('exception_or_mismatch_summary')}"
                    )
                    for item in failed_boundary_summaries
                ]
                raise RuntimeError(
                    "boundary small-case diagnostic failed:\n  "
                    + "\n  ".join(failure_lines)
                )
        if not RUN_GRID5000_MATRIX:
            print("\nGrid5000 9-cell matrix skipped (RUN_GRID5000_MATRIX=False).")

        print("\nDiagnostic completed successfully.")
        return 0
    finally:
        sys.setrecursionlimit(previous_limit)


if __name__ == "__main__":
    sys.exit(main())
