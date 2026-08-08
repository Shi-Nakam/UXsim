# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Phase 4-6Y: BATCH Level 1 vs Level 2 comparison on high-demand 6x6 grid.
# Reuses Phase 4-6U Case U2 (clearance=1, batch_size=10, unsignaled internal
# grid, free routing) input conditions. Does NOT run signalized, FCFS, or N=1.
#
# Run from repository root:
#   python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 5000 --virtual-horizon 30
#   python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 5000 --virtual-horizon 50
#   python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 10000 --virtual-horizon 30
#   python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 10000 --virtual-horizon 50
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
BATCH_SIZE = 10
LEVEL_2_VIRTUAL_HORIZON = 30

DEPARTURE_START = 0
DEPARTURE_END = 500

VEHICLE_CASES = {
    5000: {"tmax": 30000},
    10000: {"tmax": 50000},
}


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
    """Unsignaled 6x6 grid — same as Case U2 BATCH/FCFS path (no internal signals)."""
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


def _assert_pre_simulation_identity(vehicle_plans, W_l1, eligible_l1, W_l2, eligible_l2):
    plan_specs = _collect_vehicle_specs_from_plans(vehicle_plans)
    world_specs_l1 = _collect_vehicle_specs_from_world(W_l1)
    world_specs_l2 = _collect_vehicle_specs_from_world(W_l2)

    if len(vehicle_plans) != len(plan_specs):
        raise ValueError("vehicle plan count mismatch within plan list")

    if set(plan_specs) != set(world_specs_l1) or set(plan_specs) != set(world_specs_l2):
        raise ValueError(
            "vehicle name set mismatch between plans and built worlds"
        )

    for name in sorted(plan_specs):
        if world_specs_l1[name] != plan_specs[name]:
            raise ValueError(
                f"vehicle {name} spec mismatch between plan and L1 world: "
                f"plan={plan_specs[name]!r}, L1={world_specs_l1[name]!r}"
            )
        if world_specs_l2[name] != plan_specs[name]:
            raise ValueError(
                f"vehicle {name} spec mismatch between plan and L2 world: "
                f"plan={plan_specs[name]!r}, L2={world_specs_l2[name]!r}"
            )

    if eligible_l1 != eligible_l2:
        raise ValueError(
            f"eligible node name sets differ: L1={eligible_l1!r}, L2={eligible_l2!r}"
        )

    link_specs_l1 = _collect_link_specs(W_l1)
    link_specs_l2 = _collect_link_specs(W_l2)
    if link_specs_l1 != link_specs_l2:
        only_l1 = set(link_specs_l1) - set(link_specs_l2)
        only_l2 = set(link_specs_l2) - set(link_specs_l1)
        raise ValueError(
            f"link specs differ between L1 and L2 pre-build worlds; "
            f"only in L1={sorted(only_l1)!r}, only in L2={sorted(only_l2)!r}"
        )


def _verify_batch_node_settings(W, eligible_node_names, trigger_level, virtual_horizon):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "batch":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, "
                "expected 'batch'"
            )
        if node.batch_size != BATCH_SIZE:
            raise AssertionError(
                f"node {name}: batch_size={node.batch_size}, expected {BATCH_SIZE}"
            )
        if node.order_control_batch_t_trigger_level != trigger_level:
            raise AssertionError(
                f"node {name}: order_control_batch_t_trigger_level="
                f"{node.order_control_batch_t_trigger_level}, expected {trigger_level}"
            )
        if node.order_control_clearance_timesteps != CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, expected {CLEARANCE_TIMESTEPS}"
            )
        if trigger_level == 2 and node.order_control_batch_virtual_horizon != virtual_horizon:
            raise AssertionError(
                f"node {name}: order_control_batch_virtual_horizon="
                f"{node.order_control_batch_virtual_horizon}, expected {virtual_horizon}"
            )


def build_batch_world(
    vehicle_plans,
    tmax,
    trigger_level,
    *,
    virtual_horizon=LEVEL_2_VIRTUAL_HORIZON,
    run_simulation=True,
):
    """
    Timing scope (perf_counter):
      - world_build_seconds: World() through _add_grid_network (network only)
      - vehicle_apply_seconds: _add_vehicles through order-control setup
      - exec_simulation_seconds: W.exec_simulation() only (0 if not run)
      - case_total_seconds: entire build_batch_world call
    Result collection and printing are NOT included in exec_simulation_seconds.
    """
    case_started = time.perf_counter()

    world_build_started = time.perf_counter()
    W = World(
        name=f"grid_batch_level_{trigger_level}",
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

    set_kwargs = {
        "order_control_type": "batch",
        "batch_size": BATCH_SIZE,
        "order_control_batch_t_trigger_level": trigger_level,
    }
    if trigger_level == 2:
        set_kwargs["order_control_batch_virtual_horizon"] = virtual_horizon

    W.set_order_control_for_nodes(eligible_node_names, **set_kwargs)
    _verify_batch_node_settings(
        W, eligible_node_names, trigger_level, virtual_horizon
    )
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
                    f"{case_label}: expected {key}=0 for Level 1 case, got {value}"
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

    if not math.isfinite(results["completed_ratio"]):
        raise AssertionError(
            f"{case_label}: completed_ratio is not finite: {results['completed_ratio']}"
        )

    for field in (
        "total_travel_time",
        "average_travel_time",
        "average_delay",
        "total_distance_traveled",
    ):
        value = results[field]
        if not math.isfinite(value):
            raise AssertionError(f"{case_label}: {field} is not finite: {value}")

    if results["delay_ratio"] is not None and not math.isfinite(results["delay_ratio"]):
        raise AssertionError(
            f"{case_label}: delay_ratio is not finite: {results['delay_ratio']}"
        )

    if last_completed_trip_time is not None and not math.isfinite(
        last_completed_trip_time
    ):
        raise AssertionError(
            f"{case_label}: last_completed_trip_time is not finite: "
            f"{last_completed_trip_time}"
        )


def _safe_diff(l2_value, l1_value):
    if isinstance(l2_value, (int, float)) and isinstance(l1_value, (int, float)):
        if math.isfinite(l2_value) and math.isfinite(l1_value):
            return l2_value - l1_value
    return None


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


def _format_optional_float(value, precision=4):
    if value is None:
        return "None"
    if isinstance(value, (int, float)):
        return f"{value:.{precision}f}"
    return str(value)


def _print_section(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_case_settings(case_label, trigger_level, virtual_horizon):
    print(f"  case label: {case_label}")
    print('  order_control_type: "batch"')
    print(f"  batch_size: {BATCH_SIZE}")
    print(f"  order_control_batch_t_trigger_level: {trigger_level}")
    print(f"  clearance_timesteps: {CLEARANCE_TIMESTEPS}")
    if trigger_level == 2:
        print(f"  order_control_batch_virtual_horizon: {virtual_horizon}")


def _print_traffic_results(results, last_completed_trip_time):
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
    if last_completed_trip_time is not None:
        print(f"  last_completed_trip_time: {last_completed_trip_time:.1f} s")
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


def _run_case(case_label, vehicle_plans, tmax, trigger_level, *, virtual_horizon):
    W = None
    timing = None
    try:
        W, eligible_node_names, timing, simulation_error = build_batch_world(
            vehicle_plans,
            tmax,
            trigger_level,
            virtual_horizon=virtual_horizon,
            run_simulation=True,
        )
        if simulation_error is not None:
            counters = _collect_level_2_counters(W)
            rates = _counter_rates(counters)
            raise simulation_error
        results = _collect_traffic_results(W)
        last_completed_trip_time = _collect_last_completed_trip_time(W)
        counters = _collect_level_2_counters(W)
        rates = _counter_rates(counters)

        _verify_case_normality(case_label, results, last_completed_trip_time)
        _assert_level_2_counters(
            case_label,
            counters,
            expect_calls=(trigger_level == 2),
        )

        return {
            "case_label": case_label,
            "trigger_level": trigger_level,
            "eligible_node_names": eligible_node_names,
            "results": results,
            "last_completed_trip_time": last_completed_trip_time,
            "timing": timing,
            "counters": counters,
            "rates": rates,
            "success": True,
            "error": None,
        }
    except Exception as exc:
        counters = _collect_level_2_counters(W) if W is not None else None
        rates = _counter_rates(counters) if counters is not None else None
        partial_timing = timing
        return {
            "case_label": case_label,
            "trigger_level": trigger_level,
            "eligible_node_names": None,
            "results": None,
            "last_completed_trip_time": None,
            "timing": timing,
            "counters": counters,
            "rates": rates,
            "success": False,
            "error": exc,
        }


def _non_negative_int(value):
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError(
            f"virtual horizon must be a non-negative integer, got {parsed}"
        )
    return parsed


def _parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "BATCH Level 1 vs Level 2 grid diagnostic "
            "(Phase 4-6U Case U2 input conditions)"
        )
    )
    parser.add_argument(
        "--num-vehicles",
        type=int,
        default=5000,
        choices=[5000, 10000],
        help="number of vehicles (default: 5000)",
    )
    parser.add_argument(
        "--virtual-horizon",
        type=_non_negative_int,
        default=LEVEL_2_VIRTUAL_HORIZON,
        metavar="VIRTUAL_HORIZON",
        help=(
            "Level 2 virtual horizon (default: "
            f"{LEVEL_2_VIRTUAL_HORIZON})"
        ),
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    num_vehicles = args.num_vehicles
    virtual_horizon = args.virtual_horizon
    tmax = VEHICLE_CASES[num_vehicles]["tmax"]

    _print_section("Trial conditions")
    print(f"  grid_size: {GRID_SIZE}")
    print(f"  internal_grid_nodes: {INTERNAL_GRID_NODE_COUNT}")
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
    print(f"  number_of_lanes: {NUMBER_OF_LANES}")
    print(f"  merge_priority: {MERGE_PRIORITY}")
    print("  jam_density: 0.2 (UXsim addLink default, same as Case U2)")
    print("  reaction_time: 1 (World default, same as Case U2)")
    print("  deltan: 1")
    print("  deltat: 1")
    print(f"  clearance_timesteps: {CLEARANCE_TIMESTEPS}")
    print(f"  batch_size: {BATCH_SIZE}")
    print("  internal_grid_signals: none (unsignaled, same as Case U2 BATCH)")
    print("  route_choice: free (dynamic, no enforce_route)")
    print(
        "  comparison: Case L1 (Level 1) vs Case L2 "
        f"(Level 2, virtual_horizon={virtual_horizon})"
    )
    print("  excluded: signalized_all_red, FCFS, N=1")

    plan_gen_started = time.perf_counter()
    vehicle_plans = _generate_vehicle_plans(
        num_vehicles, DEPARTURE_START, DEPARTURE_END
    )
    vehicle_plan_generation_seconds = time.perf_counter() - plan_gen_started

    _print_section("Common vehicle plan")
    print(f"  vehicle_count: {len(vehicle_plans)}")
    print(f"  demand_gen_seed: {DEMAND_GEN_SEED}")
    print(f"  first_vehicle: {vehicle_plans[0]['name']}")
    print(f"  last_vehicle: {vehicle_plans[-1]['name']}")
    print(f"  first_departure_time: {vehicle_plans[0]['departure_time']}")
    print(f"  last_departure_time: {vehicle_plans[-1]['departure_time']}")
    print(
        f"  vehicle_plan_generation_seconds: "
        f"{vehicle_plan_generation_seconds:.3f}"
    )
    print("  same plan object passed to Case L1 and Case L2")

    _print_section("Common network conditions")
    print(f"  grid_size: {GRID_SIZE} x {GRID_SIZE}")
    print(f"  internal_grid_node_count: {INTERNAL_GRID_NODE_COUNT}")
    print(f"  external_od_node_count: {EXTERNAL_OD_NODE_COUNT}")
    print(f"  internal_link_length: {INTERNAL_LINK_LENGTH} m")
    print(f"  od_connector_length: {OD_CONNECTOR_LENGTH} m")
    print(f"  free_flow_speed: {FREE_FLOW_SPEED} m/s")
    print(f"  number_of_lanes: {NUMBER_OF_LANES}")
    print("  internal_grid_node_signals: none")
    print("  od_nodes_as_origin_or_destination_only: yes")

    _print_section("Pre-simulation input identity check")
    W_l1_pre, eligible_l1, _, _ = build_batch_world(
        vehicle_plans, tmax, 1, run_simulation=False
    )
    W_l2_pre, eligible_l2, _, _ = build_batch_world(
        vehicle_plans,
        tmax,
        2,
        virtual_horizon=virtual_horizon,
        run_simulation=False,
    )
    _assert_pre_simulation_identity(
        vehicle_plans, W_l1_pre, eligible_l1, W_l2_pre, eligible_l2
    )
    print("  vehicle count: match")
    print("  vehicle name set: match")
    print("  per-vehicle origin, destination, departure_time: match")
    print(f"  eligible_node_count: {len(eligible_l1)}")
    print("  eligible_node_names: match")
    print(f"  link_count: {len(W_l1_pre.LINKS)}")
    print("  link names and specs (start/end, length, speed, lanes): match")
    print("  pre-simulation identity check: PASS")

    case_l1 = None
    case_l2 = None
    comparison_done = False

    _print_section("Case L1 settings")
    _print_case_settings("L1", trigger_level=1, virtual_horizon=virtual_horizon)

    case_l1 = _run_case(
        "L1", vehicle_plans, tmax, trigger_level=1, virtual_horizon=virtual_horizon
    )
    if not case_l1["success"]:
        exc = case_l1["error"]
        _print_section("Case L1 failure")
        print(f"  exception_type: {type(exc).__name__}")
        print(f"  exception_message: {exc}")
        if case_l1["timing"] is not None:
            _print_section("Case L1 partial timing")
            _print_timing(case_l1["timing"])
        print()
        print("Case L2 was NOT executed because Case L1 failed.")
        sys.exit(1)

    _print_section("Case L1 results")
    _print_traffic_results(case_l1["results"], case_l1["last_completed_trip_time"])

    _print_section("Case L1 timing")
    _print_timing(case_l1["timing"])

    _print_section("Case L1 Level 2 counters")
    _print_level_2_counters(case_l1["counters"], case_l1["rates"])

    _print_section("Case L2 settings")
    _print_case_settings("L2", trigger_level=2, virtual_horizon=virtual_horizon)

    case_l2 = _run_case(
        "L2", vehicle_plans, tmax, trigger_level=2, virtual_horizon=virtual_horizon
    )
    if not case_l2["success"]:
        exc = case_l2["error"]
        _print_section("Case L2 failure")
        print(f"  exception_type: {type(exc).__name__}")
        print(f"  exception_message: {exc}")
        _print_section("Case L1 results preserved after L2 failure")
        _print_traffic_results(
            case_l1["results"], case_l1["last_completed_trip_time"]
        )
        _print_section("Case L1 timing preserved")
        _print_timing(case_l1["timing"])
        _print_section("Case L2 partial timing")
        if case_l2["timing"] is not None:
            _print_timing(case_l2["timing"])
        else:
            print("  (timing not available)")
        _print_section("Case L2 Level 2 counters at failure")
        if case_l2["counters"] is not None:
            _print_level_2_counters(
                case_l2["counters"],
                case_l2["rates"] or _counter_rates(case_l2["counters"]),
            )
        else:
            print("  (counters not available — World was not created)")
        print()
        print("L1 vs L2 full comparison was NOT performed.")
        sys.exit(1)

    _print_section("Case L2 results")
    _print_traffic_results(case_l2["results"], case_l2["last_completed_trip_time"])

    _print_section("Case L2 timing")
    _print_timing(case_l2["timing"])

    _print_section("Case L2 Level 2 counters")
    _print_level_2_counters(case_l2["counters"], case_l2["rates"])

    r1 = case_l1["results"]
    r2 = case_l2["results"]
    t1 = case_l1["timing"]
    t2 = case_l2["timing"]

    _print_section("L1 vs L2 differences (L2 - L1) and ratios")
    print(
        "  completed_trips difference: "
        f"{_safe_diff(r2['completed_trips'], r1['completed_trips'])}"
    )
    print(
        "  unfinished_trips difference: "
        f"{_safe_diff(r2['unfinished_trips'], r1['unfinished_trips'])}"
    )
    print(
        "  total_travel_time difference: "
        f"{_format_optional_float(_safe_diff(r2['total_travel_time'], r1['total_travel_time']), 1)} s"
    )
    print(
        "  average_travel_time difference: "
        f"{_format_optional_float(_safe_diff(r2['average_travel_time'], r1['average_travel_time']), 1)} s"
    )
    print(
        "  average_delay difference: "
        f"{_format_optional_float(_safe_diff(r2['average_delay'], r1['average_delay']), 1)} s"
    )
    dr_diff = _safe_diff(r2["delay_ratio"], r1["delay_ratio"])
    print(f"  delay_ratio difference: {_format_optional_float(dr_diff, 6)}")
    print(
        "  total_distance_traveled difference: "
        f"{_format_optional_float(_safe_diff(r2['total_distance_traveled'], r1['total_distance_traveled']), 1)} m"
    )
    print(
        "  last_completed_trip_time difference: "
        f"{_format_optional_float(_safe_diff(case_l2['last_completed_trip_time'], case_l1['last_completed_trip_time']), 1)} s"
    )
    print(
        "  exec_simulation_seconds difference: "
        f"{_format_optional_float(_safe_diff(t2['exec_simulation_seconds'], t1['exec_simulation_seconds']), 3)} s"
    )
    exec_ratio = _safe_ratio(
        t2["exec_simulation_seconds"], t1["exec_simulation_seconds"]
    )
    print(f"  exec_simulation_seconds ratio (L2/L1): {_format_optional_float(exec_ratio, 4)}")
    print(
        "  case_total_seconds difference: "
        f"{_format_optional_float(_safe_diff(t2['case_total_seconds'], t1['case_total_seconds']), 3)} s"
    )
    total_ratio = _safe_ratio(t2["case_total_seconds"], t1["case_total_seconds"])
    print(f"  case_total_seconds ratio (L2/L1): {_format_optional_float(total_ratio, 4)}")
    print(f"  Level 2 call_count: {case_l2['counters']['call_count']}")
    print(f"  resolved_rate: {_format_optional_float(case_l2['rates']['resolved_rate'])}")
    print(
        f"  unresolved_rate: {_format_optional_float(case_l2['rates']['unresolved_rate'])}"
    )
    print(
        f"  level_1_fallback_rate: "
        f"{_format_optional_float(case_l2['rates']['level_1_fallback_rate'])}"
    )
    comparison_done = True

    _print_section(
        f"Virtual horizon {virtual_horizon} — directly observed facts (this run)"
    )
    print(f"  virtual_horizon setting (L2 only): {virtual_horizon}")
    print(f"  L2 completed without exception: yes")
    print(f"  L2 Level 2 call_count: {case_l2['counters']['call_count']}")
    print(f"  L2 resolved_count: {case_l2['counters']['resolved_count']}")
    print(f"  L2 unresolved_count: {case_l2['counters']['unresolved_count']}")
    print(
        f"  L2 level_1_fallback_count: "
        f"{case_l2['counters']['level_1_fallback_count']}"
    )
    print(f"  L2 resolved_rate: {_format_optional_float(case_l2['rates']['resolved_rate'])}")
    print(
        f"  L2 unresolved_rate: "
        f"{_format_optional_float(case_l2['rates']['unresolved_rate'])}"
    )
    print(
        f"  L2 level_1_fallback_rate: "
        f"{_format_optional_float(case_l2['rates']['level_1_fallback_rate'])}"
    )
    print(
        f"  L2 exec_simulation_seconds: "
        f"{case_l2['timing']['exec_simulation_seconds']:.3f}"
    )
    print(
        f"  L1 exec_simulation_seconds: "
        f"{case_l1['timing']['exec_simulation_seconds']:.3f}"
    )
    print(
        f"  exec_simulation ratio (L2/L1): "
        f"{_format_optional_float(exec_ratio, 4)}"
    )

    all_l1_complete = r1["unfinished_trips"] == 0
    all_l2_complete = r2["unfinished_trips"] == 0

    _print_section("Final verdict")
    print("  Case L1: completed without exception")
    print("  Case L2: completed without exception")
    print(f"  L1 all vehicles completed: {all_l1_complete}")
    print(f"  L2 all vehicles completed: {all_l2_complete}")
    print(f"  L1 completed_trips: {r1['completed_trips']} / {r1['total_vehicles']}")
    print(f"  L2 completed_trips: {r2['completed_trips']} / {r2['total_vehicles']}")
    print("  assignment prefix violation: none observed (simulation completed)")
    print("  visit_id / batch_assignment / service unit mismatch: none observed")
    print(f"  L1 vs L2 comparison performed: {comparison_done}")

    _print_section("Remaining uncertainties")
    print(
        f"  - Whether virtual_horizon={virtual_horizon} is optimal cannot be determined from "
        f"this single {num_vehicles:,}-vehicle run."
    )
    print(
        "  - Observed unresolved_count="
        f"{case_l2['counters']['unresolved_count']} and unresolved_rate="
        f"{_format_optional_float(case_l2['rates']['unresolved_rate'])}. "
        "These observed values do not by themselves determine whether "
        f"virtual_horizon={virtual_horizon} should be increased or decreased. "
        "The unresolved rate, Level 1 fallback rate, computation time, "
        "and traffic results must be assessed together."
    )
    print(
        "  - Traffic result differences between L1 and L2 are observational only; "
        "no general superiority claim is made."
    )
    print(
        "  - N=1 BATCH Level 2 vs FCFS equivalence is outside this diagnostic; "
        "use grid_n1_level_2_vs_fcfs_check.py for that comparison."
    )

    print()
    print("grid_level_1_vs_level_2_check completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print(f"FATAL: {type(exc).__name__}: {exc}")
        sys.exit(1)
