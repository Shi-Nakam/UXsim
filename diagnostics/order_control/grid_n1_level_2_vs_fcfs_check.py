# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# N=1 BATCH Level 2 vs FCFS equivalence check on high-demand 6x6 grid with free
# routing. Reuses Phase 4-6U Case U2 input conditions (unsignaled internal
# grid, clearance=1, same vehicle plans). N=1 uses batch_size=1 and actually
# invokes Level 2 (order_control_batch_t_trigger_level=2); it does NOT bypass
# Level 2 because batch_size=1.
#
# Run from repository root:
#   python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py
#   python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 200
#   python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 5000
#   python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 10000
#
# Requires uxsim to be importable (e.g. pip install -e .).

import argparse
import math
import random
import sys
import time

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = GRID_SIZE * GRID_SIZE
EXTERNAL_OD_NODE_COUNT = 4 * GRID_SIZE
MIN_ELIGIBLE_NODES = 32
MIN_OD_MANHATTAN_DISTANCE = 5
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
CLEARANCE_TIMESTEPS = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
N1_BATCH_SIZE = 1
N1_TRIGGER_LEVEL = 2
LEVEL_2_VIRTUAL_HORIZON = 30

DEPARTURE_START = 0
DEPARTURE_END = 500

# TMAX rationale:
# - 5000 vehicles: 30000 (same as grid_level_1_vs_level_2_check / Case U2)
# - 10000 vehicles: 50000 (same as grid_level_1_vs_level_2_check)
# - 200 vehicles: 5000 — same absolute cap as grid_n1_fcfs_route_fixed_small_check
#   for 200 vehicles on this grid; last departure is 500 s, leaving ~4500 s for
#   trips under lighter congestion (well above free-flow upper bound for OD paths)
VEHICLE_CASES = {
    200: {"tmax": 5000},
    5000: {"tmax": 30000},
    10000: {"tmax": 50000},
}

AGGREGATE_COMPARE_FIELDS = [
    "total_vehicles",
    "completed_trips",
    "unfinished_trips",
    "completed_ratio",
    "total_travel_time",
    "average_travel_time",
    "average_delay",
    "delay_ratio",
    "total_distance_traveled",
    "last_completed_trip_time",
    "analyzer_reference_average_speed",
]

VEHICLE_COMPARE_FIELDS = [
    "state",
    "departure_time",
    "arrival_time",
    "travel_time",
    "destination_name",
    "traveled_route_link_names",
    "log_t_link_history",
]


def _grid_node_name(row, column):
    return f"g_{row}_{column}"


def _external_od_node_names():
    names = []
    for column in range(GRID_SIZE):
        names.append(f"top_{column}")
        names.append(f"bottom_{column}")
    for row in range(GRID_SIZE):
        names.append(f"left_{row}")
        names.append(f"right_{row}")
    return names


def _internal_grid_node_names():
    return [
        _grid_node_name(row, column)
        for row in range(GRID_SIZE)
        for column in range(GRID_SIZE)
    ]


def _od_to_grid_coord_map():
    mapping = {}
    for column in range(GRID_SIZE):
        mapping[f"top_{column}"] = (0, column)
        mapping[f"bottom_{column}"] = (GRID_SIZE - 1, column)
    for row in range(GRID_SIZE):
        mapping[f"left_{row}"] = (row, 0)
        mapping[f"right_{row}"] = (row, GRID_SIZE - 1)
    return mapping


OD_TO_GRID_COORD = _od_to_grid_coord_map()
EXTERNAL_OD_NODES = _external_od_node_names()


def _manhattan_distance(origin_coord, destination_coord):
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


def _generate_vehicle_plans(num_vehicles, departure_start, departure_end):
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    vehicle_index = 0
    while len(plans) < num_vehicles:
        origin = rng.choice(EXTERNAL_OD_NODES)
        destination = rng.choice(EXTERNAL_OD_NODES)
        if origin == destination:
            continue

        origin_grid_coord = OD_TO_GRID_COORD[origin]
        destination_grid_coord = OD_TO_GRID_COORD[destination]
        manhattan_distance = _manhattan_distance(
            origin_grid_coord, destination_grid_coord
        )
        if manhattan_distance < MIN_OD_MANHATTAN_DISTANCE:
            continue

        departure_time = departure_start + (departure_end - departure_start) * len(
            plans
        ) / max(num_vehicles - 1, 1)
        plans.append(
            {
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time,
                "name": f"veh_{vehicle_index}",
                "origin_grid_coord": origin_grid_coord,
                "destination_grid_coord": destination_grid_coord,
                "manhattan_distance": manhattan_distance,
            }
        )
        vehicle_index += 1
    return plans


def _add_grid_network(W):
    spacing = 1.0

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            node_name = _grid_node_name(row, column)
            W.addNode(node_name, column * spacing, -row * spacing)

    for column in range(GRID_SIZE):
        W.addNode(f"top_{column}", column * spacing, spacing)
        W.addNode(
            f"bottom_{column}",
            column * spacing,
            -GRID_SIZE * spacing,
        )

    for row in range(GRID_SIZE):
        W.addNode(f"left_{row}", -spacing, -row * spacing)
        W.addNode(
            f"right_{row}",
            GRID_SIZE * spacing,
            -row * spacing,
        )

    def add_link(link_name, start_node, end_node, length, signal_group):
        W.addLink(
            link_name,
            start_node,
            end_node,
            length=length,
            free_flow_speed=FREE_FLOW_SPEED,
            number_of_lanes=NUMBER_OF_LANES,
            merge_priority=MERGE_PRIORITY,
            signal_group=signal_group,
        )

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            add_link(
                f"h_{row}_{column}_{column + 1}",
                left_node,
                right_node,
                INTERNAL_LINK_LENGTH,
                signal_group=0,
            )
            add_link(
                f"h_{row}_{column + 1}_{column}",
                right_node,
                left_node,
                INTERNAL_LINK_LENGTH,
                signal_group=0,
            )

    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            add_link(
                f"v_{row}_{row + 1}_{column}",
                upper_node,
                lower_node,
                INTERNAL_LINK_LENGTH,
                signal_group=2,
            )
            add_link(
                f"v_{row + 1}_{row}_{column}",
                lower_node,
                upper_node,
                INTERNAL_LINK_LENGTH,
                signal_group=2,
            )

    for column in range(GRID_SIZE):
        add_link(
            f"top_{column}_to_g_0_{column}",
            f"top_{column}",
            _grid_node_name(0, column),
            OD_CONNECTOR_LENGTH,
            signal_group=2,
        )
        add_link(
            f"g_0_{column}_to_top_{column}",
            _grid_node_name(0, column),
            f"top_{column}",
            OD_CONNECTOR_LENGTH,
            signal_group=2,
        )
        add_link(
            f"bottom_{column}_to_g_5_{column}",
            f"bottom_{column}",
            _grid_node_name(GRID_SIZE - 1, column),
            OD_CONNECTOR_LENGTH,
            signal_group=2,
        )
        add_link(
            f"g_5_{column}_to_bottom_{column}",
            _grid_node_name(GRID_SIZE - 1, column),
            f"bottom_{column}",
            OD_CONNECTOR_LENGTH,
            signal_group=2,
        )

    for row in range(GRID_SIZE):
        add_link(
            f"left_{row}_to_g_{row}_0",
            f"left_{row}",
            _grid_node_name(row, 0),
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )
        add_link(
            f"g_{row}_0_to_left_{row}",
            _grid_node_name(row, 0),
            f"left_{row}",
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )
        add_link(
            f"right_{row}_to_g_{row}_5",
            f"right_{row}",
            _grid_node_name(row, GRID_SIZE - 1),
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )
        add_link(
            f"g_{row}_5_to_right_{row}",
            _grid_node_name(row, GRID_SIZE - 1),
            f"right_{row}",
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )


def _add_vehicles(W, vehicle_plans):
    for plan in vehicle_plans:
        W.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )


def _eligible_node_names(W):
    return sorted(node.name for node in W.NODES if node.order_control_eligible)


def _collect_link_specs(W):
    specs = {}
    for link in W.LINKS:
        specs[link.name] = {
            "start_node": link.start_node.name,
            "end_node": link.end_node.name,
            "length": link.length,
            "free_flow_speed": link.u,
            "number_of_lanes": link.number_of_lanes,
        }
    return specs


def _collect_vehicle_specs_from_world(W):
    specs = {}
    for name in sorted(W.VEHICLES):
        veh = W.VEHICLES[name]
        specs[name] = {
            "origin": veh.orig.name,
            "destination": veh.dest.name,
            "departure_time": veh.departure_time_in_second,
        }
    return specs


def _collect_vehicle_specs_from_plans(vehicle_plans):
    specs = {}
    for plan in vehicle_plans:
        specs[plan["name"]] = {
            "origin": plan["origin"],
            "destination": plan["destination"],
            "departure_time": plan["departure_time"],
        }
    return specs


def _assert_pre_simulation_identity(
    vehicle_plans, W_fcfs, eligible_fcfs, W_n1, eligible_n1
):
    plan_specs = _collect_vehicle_specs_from_plans(vehicle_plans)
    world_specs_fcfs = _collect_vehicle_specs_from_world(W_fcfs)
    world_specs_n1 = _collect_vehicle_specs_from_world(W_n1)

    if set(plan_specs) != set(world_specs_fcfs) or set(plan_specs) != set(
        world_specs_n1
    ):
        raise ValueError(
            "vehicle name set mismatch between plans and built worlds"
        )

    for name in sorted(plan_specs):
        if world_specs_fcfs[name] != plan_specs[name]:
            raise ValueError(
                f"vehicle {name} spec mismatch between plan and FCFS world"
            )
        if world_specs_n1[name] != plan_specs[name]:
            raise ValueError(
                f"vehicle {name} spec mismatch between plan and N1-L2 world"
            )

    if eligible_fcfs != eligible_n1:
        raise ValueError(
            f"eligible node name sets differ: FCFS={eligible_fcfs!r}, "
            f"N1-L2={eligible_n1!r}"
        )

    link_specs_fcfs = _collect_link_specs(W_fcfs)
    link_specs_n1 = _collect_link_specs(W_n1)
    if link_specs_fcfs != link_specs_n1:
        raise ValueError("link specs differ between FCFS and N1-L2 pre-build worlds")


def _verify_fcfs_node_settings(W, eligible_node_names):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "fcfs":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, "
                "expected 'fcfs'"
            )
        if node.order_control_clearance_timesteps != CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, "
                f"expected {CLEARANCE_TIMESTEPS}"
            )


def _verify_n1_l2_node_settings(W, eligible_node_names):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "batch":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, "
                "expected 'batch'"
            )
        if node.batch_size != N1_BATCH_SIZE:
            raise AssertionError(
                f"node {name}: batch_size={node.batch_size}, "
                f"expected {N1_BATCH_SIZE}"
            )
        if node.order_control_batch_t_trigger_level != N1_TRIGGER_LEVEL:
            raise AssertionError(
                f"node {name}: order_control_batch_t_trigger_level="
                f"{node.order_control_batch_t_trigger_level}, "
                f"expected {N1_TRIGGER_LEVEL}"
            )
        if node.order_control_clearance_timesteps != CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, "
                f"expected {CLEARANCE_TIMESTEPS}"
            )
        if node.order_control_batch_virtual_horizon != LEVEL_2_VIRTUAL_HORIZON:
            raise AssertionError(
                f"node {name}: order_control_batch_virtual_horizon="
                f"{node.order_control_batch_virtual_horizon}, "
                f"expected {LEVEL_2_VIRTUAL_HORIZON}"
            )


def build_fcfs_world(vehicle_plans, tmax, *, run_simulation=True):
    case_started = time.perf_counter()

    world_build_started = time.perf_counter()
    W = World(
        name="grid_n1_fcfs",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_grid_network(W)
    world_build_seconds = time.perf_counter() - world_build_started

    vehicle_apply_started = time.perf_counter()
    _add_vehicles(W, vehicle_plans)
    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    eligible_node_names = _eligible_node_names(W)
    if len(eligible_node_names) < MIN_ELIGIBLE_NODES:
        raise ValueError(
            f"eligible node count {len(eligible_node_names)} < {MIN_ELIGIBLE_NODES}"
        )
    W.set_order_control_for_nodes(
        eligible_node_names,
        order_control_type="fcfs",
    )
    _verify_fcfs_node_settings(W, eligible_node_names)
    vehicle_apply_seconds = time.perf_counter() - vehicle_apply_started

    exec_simulation_seconds = 0.0
    simulation_error = None
    if run_simulation:
        exec_started = time.perf_counter()
        try:
            W.exec_simulation()
        except Exception as exc:
            simulation_error = exc
        exec_simulation_seconds = time.perf_counter() - exec_started

    case_total_seconds = time.perf_counter() - case_started

    timing = {
        "world_build_seconds": world_build_seconds,
        "vehicle_apply_seconds": vehicle_apply_seconds,
        "exec_simulation_seconds": exec_simulation_seconds,
        "case_total_seconds": case_total_seconds,
    }
    return W, eligible_node_names, timing, simulation_error


def build_n1_l2_world(vehicle_plans, tmax, *, run_simulation=True):
    case_started = time.perf_counter()

    world_build_started = time.perf_counter()
    W = World(
        name="grid_n1_batch_level_2",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_grid_network(W)
    world_build_seconds = time.perf_counter() - world_build_started

    vehicle_apply_started = time.perf_counter()
    _add_vehicles(W, vehicle_plans)
    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    eligible_node_names = _eligible_node_names(W)
    if len(eligible_node_names) < MIN_ELIGIBLE_NODES:
        raise ValueError(
            f"eligible node count {len(eligible_node_names)} < {MIN_ELIGIBLE_NODES}"
        )
    W.set_order_control_for_nodes(
        eligible_node_names,
        order_control_type="batch",
        batch_size=N1_BATCH_SIZE,
        order_control_batch_t_trigger_level=N1_TRIGGER_LEVEL,
        order_control_batch_virtual_horizon=LEVEL_2_VIRTUAL_HORIZON,
    )
    _verify_n1_l2_node_settings(W, eligible_node_names)
    vehicle_apply_seconds = time.perf_counter() - vehicle_apply_started

    exec_simulation_seconds = 0.0
    simulation_error = None
    if run_simulation:
        exec_started = time.perf_counter()
        try:
            W.exec_simulation()
        except Exception as exc:
            simulation_error = exc
        exec_simulation_seconds = time.perf_counter() - exec_started

    case_total_seconds = time.perf_counter() - case_started

    timing = {
        "world_build_seconds": world_build_seconds,
        "vehicle_apply_seconds": vehicle_apply_seconds,
        "exec_simulation_seconds": exec_simulation_seconds,
        "case_total_seconds": case_total_seconds,
    }
    return W, eligible_node_names, timing, simulation_error


def _collect_traffic_results(W):
    analyzer = W.analyzer
    completed_trips = int(analyzer.trip_completed)
    total_trips = int(analyzer.trip_all)
    unfinished_trips = total_trips - completed_trips
    completed_ratio = completed_trips / total_trips if total_trips else 0.0
    total_travel_time = float(analyzer.total_travel_time)
    average_travel_time = float(analyzer.average_travel_time)
    average_delay = float(analyzer.average_delay)
    delay_ratio = (
        average_delay / average_travel_time
        if completed_trips > 0 and average_travel_time > 0
        else None
    )
    total_distance_traveled = float(analyzer.total_distance_traveled)

    analyzer_reference_average_speed = None
    if getattr(analyzer, "average_speed_count", 0) > 0:
        analyzer_reference_average_speed = float(analyzer.average_speed)

    return {
        "total_vehicles": total_trips,
        "completed_trips": completed_trips,
        "unfinished_trips": unfinished_trips,
        "completed_ratio": completed_ratio,
        "total_travel_time": total_travel_time,
        "average_travel_time": average_travel_time,
        "average_delay": average_delay,
        "delay_ratio": delay_ratio,
        "total_distance_traveled": total_distance_traveled,
        "analyzer_reference_average_speed": analyzer_reference_average_speed,
    }


def _collect_last_completed_trip_time(W):
    completed_arrival_times_seconds = []
    for veh in W.VEHICLES.values():
        if veh.arrival_time >= 0 and veh.travel_time >= 0:
            completed_arrival_times_seconds.append(veh.arrival_time * W.DELTAT)

    if not completed_arrival_times_seconds:
        return None
    return max(completed_arrival_times_seconds)


def _collect_level_2_counters(W):
    return {
        "call_count": int(W.order_control_batch_level_2_call_count),
        "resolved_count": int(W.order_control_batch_level_2_resolved_count),
        "unresolved_count": int(W.order_control_batch_level_2_unresolved_count),
        "level_1_fallback_count": int(
            W.order_control_batch_level_2_level_1_fallback_count
        ),
    }


def _counter_rates(counters):
    call_count = counters["call_count"]
    if call_count == 0:
        return {
            "resolved_rate": None,
            "unresolved_rate": None,
            "level_1_fallback_rate": None,
        }
    return {
        "resolved_rate": counters["resolved_count"] / call_count,
        "unresolved_rate": counters["unresolved_count"] / call_count,
        "level_1_fallback_rate": counters["level_1_fallback_count"] / call_count,
    }


def _assert_level_2_counters(case_label, counters, *, expect_calls):
    if expect_calls:
        if counters["call_count"] <= 0:
            raise AssertionError(
                f"{case_label}: expected call_count > 0, got {counters['call_count']}"
            )
        if (
            counters["resolved_count"] + counters["unresolved_count"]
            != counters["call_count"]
        ):
            raise AssertionError(
                f"{case_label}: resolved_count + unresolved_count != call_count "
                f"({counters['resolved_count']} + {counters['unresolved_count']} "
                f"!= {counters['call_count']})"
            )
        if counters["level_1_fallback_count"] != counters["unresolved_count"]:
            raise AssertionError(
                f"{case_label}: level_1_fallback_count != unresolved_count "
                f"({counters['level_1_fallback_count']} != "
                f"{counters['unresolved_count']})"
            )
    else:
        for key, value in counters.items():
            if value != 0:
                raise AssertionError(
                    f"{case_label}: expected {key}=0 for FCFS case, got {value}"
                )


def _verify_case_normality(case_label, results, last_completed_trip_time):
    total = results["total_vehicles"]
    completed = results["completed_trips"]
    unfinished = results["unfinished_trips"]

    if total != completed + unfinished:
        raise AssertionError(
            f"{case_label}: total_vehicles ({total}) != completed_trips ({completed}) "
            f"+ unfinished_trips ({unfinished})"
        )

    if unfinished != 0:
        raise AssertionError(
            f"{case_label}: expected all vehicles to complete, "
            f"unfinished_trips={unfinished}"
        )

    if not math.isfinite(results["completed_ratio"]):
        raise AssertionError(
            f"{case_label}: completed_ratio is not finite: {results['completed_ratio']}"
        )


def _normalize_log_t_link(veh):
    history = []
    for time_value, link_value in veh.log_t_link:
        if link_value == "home":
            history.append((time_value, "home"))
        elif link_value == "end":
            history.append((time_value, "end"))
        else:
            history.append((time_value, link_value.name))
    return history


def _traveled_route_link_names(veh):
    route, _timestamps = veh.traveled_route()
    return [link.name for link in route]


def _collect_vehicle_snapshots(W):
    snapshots = {}
    for name in sorted(W.VEHICLES):
        veh = W.VEHICLES[name]
        traveled_route = _traveled_route_link_names(veh)
        snapshots[name] = {
            "name": name,
            "state": veh.state,
            "departure_time": veh.departure_time_in_second,
            "arrival_time": veh.arrival_time,
            "travel_time": veh.travel_time,
            "destination_name": veh.dest.name,
            "traveled_route_link_names": traveled_route,
            "log_t_link_history": _normalize_log_t_link(veh),
            "final_link_name": traveled_route[-1] if traveled_route else None,
        }
    return snapshots


def _completion_order(vehicle_snapshots):
    completed = []
    for name, snap in vehicle_snapshots.items():
        if snap["state"] == "end" and snap["arrival_time"] >= 0:
            completed.append((snap["arrival_time"], name))
    completed.sort()
    return [name for _arrival, name in completed]


def _run_fcfs_case(vehicle_plans, tmax):
    W, eligible_node_names, timing, simulation_error = build_fcfs_world(
        vehicle_plans, tmax, run_simulation=True
    )
    if simulation_error is not None:
        counters = _collect_level_2_counters(W)
        raise simulation_error

    results = _collect_traffic_results(W)
    last_completed_trip_time = _collect_last_completed_trip_time(W)
    counters = _collect_level_2_counters(W)
    rates = _counter_rates(counters)

    _verify_case_normality("FCFS", results, last_completed_trip_time)
    _assert_level_2_counters("FCFS", counters, expect_calls=False)

    results_with_last = dict(results)
    results_with_last["last_completed_trip_time"] = last_completed_trip_time

    vehicle_snapshots = _collect_vehicle_snapshots(W)

    return {
        "case_label": "FCFS",
        "eligible_node_names": eligible_node_names,
        "results": results_with_last,
        "timing": timing,
        "counters": counters,
        "rates": rates,
        "vehicle_snapshots": vehicle_snapshots,
        "completion_order": _completion_order(vehicle_snapshots),
    }


def _run_n1_l2_case(vehicle_plans, tmax):
    W, eligible_node_names, timing, simulation_error = build_n1_l2_world(
        vehicle_plans, tmax, run_simulation=True
    )
    if simulation_error is not None:
        counters = _collect_level_2_counters(W)
        raise simulation_error

    results = _collect_traffic_results(W)
    last_completed_trip_time = _collect_last_completed_trip_time(W)
    counters = _collect_level_2_counters(W)
    rates = _counter_rates(counters)

    _verify_case_normality("N1-L2", results, last_completed_trip_time)
    _assert_level_2_counters("N1-L2", counters, expect_calls=True)

    results_with_last = dict(results)
    results_with_last["last_completed_trip_time"] = last_completed_trip_time

    vehicle_snapshots = _collect_vehicle_snapshots(W)

    return {
        "case_label": "N1-L2",
        "eligible_node_names": eligible_node_names,
        "results": results_with_last,
        "timing": timing,
        "counters": counters,
        "rates": rates,
        "vehicle_snapshots": vehicle_snapshots,
        "completion_order": _completion_order(vehicle_snapshots),
    }


def _compare_aggregate(fcfs_case, n1_case):
    mismatches = []
    for field in AGGREGATE_COMPARE_FIELDS:
        fcfs_value = fcfs_case["results"][field]
        n1_value = n1_case["results"][field]
        if fcfs_value != n1_value:
            mismatches.append(
                {"field": field, "fcfs": fcfs_value, "n1_l2": n1_value}
            )
    return mismatches


def _compare_vehicle_level(fcfs_case, n1_case):
    fcfs_snapshots = fcfs_case["vehicle_snapshots"]
    n1_snapshots = n1_case["vehicle_snapshots"]
    mismatches = []

    fcfs_names = set(fcfs_snapshots)
    n1_names = set(n1_snapshots)
    if fcfs_names != n1_names:
        mismatches.append(
            {
                "vehicle_name": "<vehicle_name_set>",
                "field": "vehicle_name_set",
                "fcfs": sorted(fcfs_names),
                "n1_l2": sorted(n1_names),
            }
        )
        return mismatches

    for name in sorted(fcfs_names):
        fcfs_snap = fcfs_snapshots[name]
        n1_snap = n1_snapshots[name]
        for field in VEHICLE_COMPARE_FIELDS:
            fcfs_value = fcfs_snap[field]
            n1_value = n1_snap[field]
            if fcfs_value != n1_value:
                mismatches.append(
                    {
                        "vehicle_name": name,
                        "field": field,
                        "fcfs": fcfs_value,
                        "n1_l2": n1_value,
                    }
                )

    if fcfs_case["completion_order"] != n1_case["completion_order"]:
        mismatches.append(
            {
                "vehicle_name": "<completion_order>",
                "field": "completion_order",
                "fcfs": fcfs_case["completion_order"],
                "n1_l2": n1_case["completion_order"],
            }
        )

    return mismatches


def _classify_comparison(aggregate_mismatches, vehicle_mismatches):
    if not aggregate_mismatches and not vehicle_mismatches:
        return "exact_match"
    if not aggregate_mismatches and vehicle_mismatches:
        return "aggregate_match_only"
    return "mismatch"


def _format_optional_float(value, precision=4):
    if value is None:
        return "None"
    if isinstance(value, (int, float)):
        return f"{value:.{precision}f}"
    return str(value)


def _safe_ratio(numerator, denominator):
    if (
        isinstance(numerator, (int, float))
        and isinstance(denominator, (int, float))
        and denominator > 0
        and math.isfinite(numerator)
        and math.isfinite(denominator)
    ):
        return numerator / denominator
    return None


def _print_section(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_traffic_results(results):
    print(f"  total_vehicles: {results['total_vehicles']}")
    print(f"  completed_trips: {results['completed_trips']}")
    print(f"  unfinished_trips: {results['unfinished_trips']}")
    print(f"  completed_ratio: {results['completed_ratio']:.6f}")
    print(f"  total_travel_time: {results['total_travel_time']:.1f} s")
    print(f"  average_travel_time: {results['average_travel_time']:.1f} s")
    print(f"  average_delay: {results['average_delay']:.1f} s")
    if results["delay_ratio"] is not None:
        print(f"  delay_ratio: {results['delay_ratio']:.6f}")
    else:
        print("  delay_ratio: None")
    print(f"  total_distance_traveled: {results['total_distance_traveled']:.1f} m")
    if results["last_completed_trip_time"] is not None:
        print(
            f"  last_completed_trip_time: "
            f"{results['last_completed_trip_time']:.1f} s"
        )
    else:
        print("  last_completed_trip_time: None")
    ref_speed = results["analyzer_reference_average_speed"]
    if ref_speed is not None:
        print(
            "  analyzer_reference_average_speed: "
            f"{ref_speed:.4f} m/s "
            "(running mean of vehicle speeds during simulation; not a primary metric)"
        )


def _print_timing(timing, vehicle_plan_generation_seconds=None):
    if vehicle_plan_generation_seconds is not None:
        print(
            f"  vehicle_plan_generation_seconds: "
            f"{vehicle_plan_generation_seconds:.3f}"
        )
    print(f"  world_build_seconds: {timing['world_build_seconds']:.3f}")
    print(f"  vehicle_apply_seconds: {timing['vehicle_apply_seconds']:.3f}")
    print(f"  exec_simulation_seconds: {timing['exec_simulation_seconds']:.3f}")
    print(f"  case_total_seconds: {timing['case_total_seconds']:.3f}")


def _print_level_2_counters(counters, rates):
    print(f"  order_control_batch_level_2_call_count: {counters['call_count']}")
    print(f"  order_control_batch_level_2_resolved_count: {counters['resolved_count']}")
    print(
        f"  order_control_batch_level_2_unresolved_count: "
        f"{counters['unresolved_count']}"
    )
    print(
        f"  order_control_batch_level_2_level_1_fallback_count: "
        f"{counters['level_1_fallback_count']}"
    )
    print(f"  resolved_rate: {_format_optional_float(rates['resolved_rate'])}")
    print(f"  unresolved_rate: {_format_optional_float(rates['unresolved_rate'])}")
    print(
        f"  level_1_fallback_rate: "
        f"{_format_optional_float(rates['level_1_fallback_rate'])}"
    )


def _print_vehicle_mismatch_summary(vehicle_mismatches, limit=20):
    print(f"  mismatched_vehicle_level_items: {len(vehicle_mismatches)}")
    if not vehicle_mismatches:
        print("  (none)")
        return

    first = vehicle_mismatches[0]
    print(f"  first_mismatch_vehicle_name: {first['vehicle_name']!r}")
    print(f"  first_mismatch_field: {first['field']!r}")
    print(f"  first_mismatch_fcfs_value: {first['fcfs']!r}")
    print(f"  first_mismatch_n1_l2_value: {first['n1_l2']!r}")

    print(f"  mismatch_overview (up to {limit} items):")
    for item in vehicle_mismatches[:limit]:
        print(
            f"    - vehicle={item['vehicle_name']!r} field={item['field']!r} "
            f"FCFS={item['fcfs']!r} N1-L2={item['n1_l2']!r}"
        )


def _parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "N=1 BATCH Level 2 vs FCFS grid diagnostic "
            "(Phase 4-6U Case U2 input conditions, free routing)"
        )
    )
    parser.add_argument(
        "--num-vehicles",
        type=int,
        default=200,
        choices=[200, 5000, 10000],
        help="number of vehicles (default: 200)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    num_vehicles = args.num_vehicles
    tmax = VEHICLE_CASES[num_vehicles]["tmax"]

    _print_section("Diagnostic settings")
    print(f"  grid_size: {GRID_SIZE}")
    print(f"  internal_grid_nodes: {INTERNAL_GRID_NODE_COUNT}")
    print(f"  external_od_nodes: {EXTERNAL_OD_NODE_COUNT}")
    print(f"  num_vehicles: {num_vehicles}")
    print(f"  departure_start: {DEPARTURE_START}")
    print(f"  departure_end: {DEPARTURE_END}")
    print(f"  tmax: {tmax}")
    print(f"  random_seed: {RANDOM_SEED}")
    print(f"  demand_gen_seed: {DEMAND_GEN_SEED}")
    print(f"  min_od_manhattan_distance: {MIN_OD_MANHATTAN_DISTANCE}")
    print(f"  internal_link_length: {INTERNAL_LINK_LENGTH}")
    print(f"  od_connector_length: {OD_CONNECTOR_LENGTH}")
    print(f"  free_flow_speed: {FREE_FLOW_SPEED}")
    print(f"  clearance_timesteps: {CLEARANCE_TIMESTEPS}")
    print("  internal_grid_signals: none (unsignaled, same as Case U2)")
    print("  route_choice: free (dynamic, no enforce_route)")
    print("  comparison: Case FCFS vs Case N1-L2 (batch_size=1, Level 2)")

    plan_gen_started = time.perf_counter()
    vehicle_plans = _generate_vehicle_plans(
        num_vehicles, DEPARTURE_START, DEPARTURE_END
    )
    vehicle_plan_generation_seconds = time.perf_counter() - plan_gen_started

    _print_section("Input identity verification")
    W_fcfs_pre, eligible_fcfs, _, _ = build_fcfs_world(
        vehicle_plans, tmax, run_simulation=False
    )
    W_n1_pre, eligible_n1, _, _ = build_n1_l2_world(
        vehicle_plans, tmax, run_simulation=False
    )
    _assert_pre_simulation_identity(
        vehicle_plans, W_fcfs_pre, eligible_fcfs, W_n1_pre, eligible_n1
    )
    print(f"  vehicle_count: {len(vehicle_plans)}")
    print(f"  vehicle_plan_generation_seconds: {vehicle_plan_generation_seconds:.3f}")
    print("  vehicle name set: match")
    print("  per-vehicle origin, destination, departure_time: match")
    print(f"  eligible_node_count: {len(eligible_fcfs)}")
    print("  eligible_node_names: match")
    print(f"  link_count: {len(W_fcfs_pre.LINKS)}")
    print("  link names and specs: match")
    print(f"  random_seed: {RANDOM_SEED}")
    print(f"  demand_gen_seed: {DEMAND_GEN_SEED}")
    print("  pre-simulation identity check: PASS")

    _print_section("Case FCFS settings")
    print('  order_control_type: "fcfs"')
    print(f"  clearance_timesteps: {CLEARANCE_TIMESTEPS}")
    print("  batch_size: (not used for traffic processing)")

    fcfs_case = _run_fcfs_case(vehicle_plans, tmax)

    _print_section("Case FCFS results")
    _print_traffic_results(fcfs_case["results"])

    _print_section("Case FCFS timing")
    _print_timing(fcfs_case["timing"], vehicle_plan_generation_seconds)

    _print_section("Case N1-L2 settings")
    print('  order_control_type: "batch"')
    print(f"  batch_size: {N1_BATCH_SIZE}")
    print(f"  order_control_batch_t_trigger_level: {N1_TRIGGER_LEVEL}")
    print(f"  order_control_batch_virtual_horizon: {LEVEL_2_VIRTUAL_HORIZON}")
    print(f"  clearance_timesteps: {CLEARANCE_TIMESTEPS}")

    n1_case = _run_n1_l2_case(vehicle_plans, tmax)

    _print_section("Case N1-L2 results")
    _print_traffic_results(n1_case["results"])

    _print_section("Case N1-L2 timing")
    _print_timing(n1_case["timing"])

    _print_section("Case N1-L2 Level 2 counters")
    _print_level_2_counters(n1_case["counters"], n1_case["rates"])

    aggregate_mismatches = _compare_aggregate(fcfs_case, n1_case)
    vehicle_mismatches = _compare_vehicle_level(fcfs_case, n1_case)
    comparison_class = _classify_comparison(aggregate_mismatches, vehicle_mismatches)

    _print_section("Aggregate comparison")
    if aggregate_mismatches:
        print(f"  aggregate_mismatch_count: {len(aggregate_mismatches)}")
        for item in aggregate_mismatches:
            print(
                f"    - {item['field']}: FCFS={item['fcfs']!r}, "
                f"N1-L2={item['n1_l2']!r}"
            )
    else:
        print("  aggregate_mismatch_count: 0")
        print("  all compared aggregate fields match exactly")

    _print_section("Vehicle-level comparison")
    _print_vehicle_mismatch_summary(vehicle_mismatches)

    exec_ratio = _safe_ratio(
        n1_case["timing"]["exec_simulation_seconds"],
        fcfs_case["timing"]["exec_simulation_seconds"],
    )

    _print_section("Final verdict")
    print("  FCFS completed without exception: yes")
    print("  N1-L2 completed without exception: yes")
    print(
        f"  FCFS all vehicles completed: "
        f"{fcfs_case['results']['unfinished_trips'] == 0}"
    )
    print(
        f"  N1-L2 all vehicles completed: "
        f"{n1_case['results']['unfinished_trips'] == 0}"
    )
    print(
        f"  FCFS completed_trips: "
        f"{fcfs_case['results']['completed_trips']} / "
        f"{fcfs_case['results']['total_vehicles']}"
    )
    print(
        f"  N1-L2 completed_trips: "
        f"{n1_case['results']['completed_trips']} / "
        f"{n1_case['results']['total_vehicles']}"
    )
    print(
        f"  Level 2 call_count > 0: {n1_case['counters']['call_count'] > 0}"
    )
    print("  Level 2 counters consistent: yes")
    print(
        f"  aggregate comparison result: "
        f"{'match' if not aggregate_mismatches else 'mismatch'}"
    )
    print(
        f"  vehicle-level comparison result: "
        f"{'match' if not vehicle_mismatches else 'mismatch'}"
    )
    print(f"  comparison_class: {comparison_class}")
    print(
        "  assignment prefix violation: none observed (simulation completed)"
    )
    print("  visit_id / batch_assignment / service unit mismatch: none observed")
    print("  comparison performed: yes")
    print(
        f"  N1-L2 / FCFS exec_simulation_seconds ratio: "
        f"{_format_optional_float(exec_ratio, 4)}"
    )

    _print_section("Remaining uncertainties")
    print(
        f"  - Results from this {num_vehicles:,}-vehicle run do not guarantee "
        "equivalence at 5,000 or 10,000 vehicles."
    )
    print(
        f"  - Execution time from this {num_vehicles:,}-vehicle run does not "
        "predict 5,000- or 10,000-vehicle runtime."
    )
    if num_vehicles == 200:
        print("  - 5,000-vehicle formal diagnostic: not executed in this run.")
        print("  - 10,000-vehicle formal diagnostic: not executed in this run.")
    elif num_vehicles == 5000:
        print("  - This run is the 5,000-vehicle formal diagnostic.")
        print("  - 10,000-vehicle formal diagnostic: not executed in this run.")
    else:
        print("  - This run is the 10,000-vehicle formal diagnostic.")
    print(
        "  - If vehicles do not match, investigate before modifying core code."
    )
    print(
        "  - N=1 still invokes Level 2 estimation; no batch_size=1 bypass was added."
    )
    print(
        "  - No N=1-specific Level 2 shortcut optimization was implemented."
    )

    if comparison_class != "exact_match":
        raise AssertionError(
            f"N=1 BATCH Level 2 vs FCFS comparison result: {comparison_class} "
            f"(aggregate_mismatches={len(aggregate_mismatches)}, "
            f"vehicle_mismatches={len(vehicle_mismatches)})"
        )

    print()
    print("grid_n1_level_2_vs_fcfs_check completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print(f"grid_n1_level_2_vs_fcfs_check failed: {type(exc).__name__}: {exc}")
        sys.exit(1)
