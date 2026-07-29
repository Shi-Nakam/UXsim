# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Small-scale fixed-route diagnostic before Level 2 design.
# Compares FCFS clearance=1 vs BATCH N=1 Level 1 clearance=1 on a 6x6 grid
# with deterministic Manhattan routes (no dynamic route choice).
#
# Purpose:
#   - Isolate local order-control differences from route-choice / DUO / RNG feedback
#   - Pre-Level-2 baseline check only; NOT formal performance evaluation
#   - NOT a proof of equivalence for all networks or all demand patterns
#
# Run from repository root:
#   python diagnostics/order_control/grid_n1_fcfs_route_fixed_small_check.py

import random
import time

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = GRID_SIZE * GRID_SIZE
NUM_VEHICLES = 200
DEPARTURE_START = 0
DEPARTURE_END = 40
# Longest fixed Manhattan route: 1 entry + up to 10 internal + 1 exit links.
# Free-flow time ~250 s; last departure 40 s; 200 vehicles with clearance=1 at 36 nodes.
# 5000 s gives ~20x free-flow headroom for intersection queuing without matching the
# 10,000-vehicle TMAX=50000 scale (unnecessary for 200 vehicles).
TMAX = 5000
MIN_OD_MANHATTAN_DISTANCE = 5
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
FCFS_CLEARANCE_TIMESTEPS = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
BATCH_T_TRIGGER_LEVEL = 1

# All vehicles use the same Manhattan rule: horizontal grid moves first, then vertical.
FIXED_ROUTE_RULE = (
    "horizontal-first Manhattan route: OD connector entry, "
    "all horizontal internal grid links (column change), "
    "all vertical internal grid links (row change), "
    "OD connector exit"
)


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


def _origin_entry_link_name(origin):
    if origin.startswith("top_"):
        column = int(origin.split("_")[1])
        return f"top_{column}_to_g_0_{column}"
    if origin.startswith("bottom_"):
        column = int(origin.split("_")[1])
        last_row = GRID_SIZE - 1
        return f"bottom_{column}_to_g_{last_row}_{column}"
    if origin.startswith("left_"):
        row = int(origin.split("_")[1])
        return f"left_{row}_to_g_{row}_0"
    if origin.startswith("right_"):
        row = int(origin.split("_")[1])
        last_col = GRID_SIZE - 1
        return f"right_{row}_to_g_{row}_{last_col}"
    raise ValueError(f"Unknown origin node name: {origin!r}")


def _destination_exit_link_name(destination):
    if destination.startswith("top_"):
        column = int(destination.split("_")[1])
        return f"g_0_{column}_to_top_{column}"
    if destination.startswith("bottom_"):
        column = int(destination.split("_")[1])
        last_row = GRID_SIZE - 1
        return f"g_{last_row}_{column}_to_bottom_{column}"
    if destination.startswith("left_"):
        row = int(destination.split("_")[1])
        return f"g_{row}_0_to_left_{row}"
    if destination.startswith("right_"):
        row = int(destination.split("_")[1])
        last_col = GRID_SIZE - 1
        return f"g_{row}_{last_col}_to_right_{row}"
    raise ValueError(f"Unknown destination node name: {destination!r}")


def _horizontal_link_names(row, from_column, to_column):
    links = []
    column = from_column
    while column < to_column:
        links.append(f"h_{row}_{column}_{column + 1}")
        column += 1
    while column > to_column:
        links.append(f"h_{row}_{column}_{column - 1}")
        column -= 1
    return links


def _vertical_link_names(from_row, to_row, column):
    links = []
    row = from_row
    while row < to_row:
        links.append(f"v_{row}_{row + 1}_{column}")
        row += 1
    while row > to_row:
        links.append(f"v_{row}_{row - 1}_{column}")
        row -= 1
    return links


def _build_fixed_route_link_names(plan):
    origin_row, origin_column = plan["origin_grid_coord"]
    destination_row, destination_column = plan["destination_grid_coord"]
    link_names = [_origin_entry_link_name(plan["origin"])]
    link_names.extend(
        _horizontal_link_names(origin_row, origin_column, destination_column)
    )
    link_names.extend(
        _vertical_link_names(origin_row, destination_row, destination_column)
    )
    link_names.append(_destination_exit_link_name(plan["destination"]))
    return link_names


def _attach_fixed_routes(vehicle_plans):
    for plan in vehicle_plans:
        plan["route_link_names"] = _build_fixed_route_link_names(plan)


def _validate_fixed_route(W, vehicle, route_link_names):
    if not route_link_names:
        raise AssertionError(
            f"{vehicle.name}: fixed route is empty for origin={vehicle.orig.name!r} "
            f"destination={vehicle.dest.name!r}"
        )

    route_links = []
    for link_name in route_link_names:
        link = W.get_link(link_name)
        if link is None:
            raise AssertionError(
                f"{vehicle.name}: link {link_name!r} does not exist in World"
            )
        route_links.append(link)

    first_link = route_links[0]
    if first_link.start_node is not vehicle.orig:
        raise AssertionError(
            f"{vehicle.name}: first link {first_link.name!r} start_node="
            f"{first_link.start_node.name!r}, expected origin {vehicle.orig.name!r}"
        )

    for index in range(len(route_links) - 1):
        current_link = route_links[index]
        next_link = route_links[index + 1]
        if current_link.end_node is not next_link.start_node:
            raise AssertionError(
                f"{vehicle.name}: route discontinuity between "
                f"{current_link.name!r} (end {current_link.end_node.name!r}) and "
                f"{next_link.name!r} (start {next_link.start_node.name!r})"
            )

    last_link = route_links[-1]
    if last_link.end_node is not vehicle.dest:
        raise AssertionError(
            f"{vehicle.name}: last link {last_link.name!r} end_node="
            f"{last_link.end_node.name!r}, expected destination {vehicle.dest.name!r}"
        )

    return route_links


def _add_grid_network(W):
    spacing = 1.0

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            W.addNode(
                _grid_node_name(row, column),
                column * spacing,
                -row * spacing,
            )

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


def _eligible_node_names(W):
    return [node.name for node in W.NODES if node.order_control_eligible]


def _verify_fcfs_node_settings(W, eligible_node_names):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "fcfs":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, "
                "expected 'fcfs'"
            )
        if node.order_control_clearance_timesteps != FCFS_CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, "
                f"expected {FCFS_CLEARANCE_TIMESTEPS}"
            )


def _verify_batch_node_settings(W, eligible_node_names):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "batch":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, "
                "expected 'batch'"
            )
        if node.batch_size != 1:
            raise AssertionError(
                f"node {name}: batch_size={node.batch_size}, expected 1"
            )
        if node.order_control_batch_t_trigger_level != BATCH_T_TRIGGER_LEVEL:
            raise AssertionError(
                f"node {name}: order_control_batch_t_trigger_level="
                f"{node.order_control_batch_t_trigger_level}, "
                f"expected {BATCH_T_TRIGGER_LEVEL}"
            )
        if node.order_control_clearance_timesteps != FCFS_CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, "
                f"expected {FCFS_CLEARANCE_TIMESTEPS}"
            )


def _create_world(mode):
    if mode == "fcfs":
        world_name = "fixed_route_fcfs_clearance_1"
    elif mode == "batch":
        world_name = "fixed_route_batch_n1_clearance_1"
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    return World(
        name=world_name,
        deltan=1,
        tmax=TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )


def _configure_order_control(W, mode, eligible_node_names):
    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(FCFS_CLEARANCE_TIMESTEPS)
    eligible_node_names[:] = _eligible_node_names(W)
    if len(eligible_node_names) != INTERNAL_GRID_NODE_COUNT:
        raise AssertionError(
            f"eligible node count={len(eligible_node_names)}, "
            f"expected {INTERNAL_GRID_NODE_COUNT}"
        )

    if mode == "fcfs":
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="fcfs",
        )
        _verify_fcfs_node_settings(W, eligible_node_names)
    else:
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="batch",
            batch_size=1,
            order_control_batch_t_trigger_level=BATCH_T_TRIGGER_LEVEL,
        )
        _verify_batch_node_settings(W, eligible_node_names)


def _add_vehicles_with_fixed_routes(W, vehicle_plans):
    vehicles = {}
    for plan in vehicle_plans:
        vehicle = W.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )
        route_links = _validate_fixed_route(W, vehicle, plan["route_link_names"])
        vehicle.enforce_route(route_links, set_avoid=True)
        vehicles[plan["name"]] = vehicle
    return vehicles


def _collect_traffic_results(W):
    analyzer = W.analyzer
    completed_trips = int(analyzer.trip_completed)
    total_trips = int(analyzer.trip_all)
    completed_ratio = completed_trips / total_trips if total_trips else 0.0
    return {
        "total_vehicles": total_trips,
        "completed_trips": completed_trips,
        "completed_ratio": completed_ratio,
        "total_travel_time": float(analyzer.total_travel_time),
        "average_travel_time": float(analyzer.average_travel_time),
        "average_delay": float(analyzer.average_delay),
        "total_distance_traveled": float(analyzer.total_distance_traveled),
    }


def _collect_completion_time_summary(W):
    completed_arrival_times_seconds = []
    for veh in W.VEHICLES.values():
        if veh.arrival_time >= 0 and veh.travel_time >= 0:
            completed_arrival_times_seconds.append(veh.arrival_time * W.DELTAT)

    if not completed_arrival_times_seconds:
        return {
            "last_completed_trip_time": None,
            "unfinished_vehicle_count": len(W.VEHICLES),
        }

    return {
        "last_completed_trip_time": max(completed_arrival_times_seconds),
        "unfinished_vehicle_count": len(W.VEHICLES) - len(completed_arrival_times_seconds),
    }


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
        snapshots[name] = {
            "name": name,
            "state": veh.state,
            "arrival_time": veh.arrival_time,
            "travel_time": veh.travel_time,
            "traveled_route_link_names": _traveled_route_link_names(veh),
            "log_t_link_history": _normalize_log_t_link(veh),
        }
    return snapshots


def _run_case(case_name, mode, vehicle_plans):
    started = time.perf_counter()
    W = _create_world(mode)
    _add_grid_network(W)
    eligible_node_names = []
    _configure_order_control(W, mode, eligible_node_names)
    _add_vehicles_with_fixed_routes(W, vehicle_plans)
    W.exec_simulation()
    elapsed_seconds = time.perf_counter() - started

    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W)
    vehicle_snapshots = _collect_vehicle_snapshots(W)

    return {
        "case_name": case_name,
        "mode": mode,
        "results": results,
        "completion": completion,
        "elapsed_seconds": elapsed_seconds,
        "eligible_node_names": sorted(eligible_node_names),
        "vehicle_snapshots": vehicle_snapshots,
    }


def _first_sequence_diff(left, right):
    limit = max(len(left), len(right))
    for index in range(limit):
        left_value = left[index] if index < len(left) else "<missing>"
        right_value = right[index] if index < len(right) else "<missing>"
        if left_value != right_value:
            return index, left_value, right_value
    return None


def _link_endpoints(W, link_name):
    if link_name in ("<missing>", "home", "end"):
        return None, None
    link = W.get_link(link_name)
    return link.start_node.name, link.end_node.name


def _compare_cases(f0_case, f1_case):
    aggregate_keys = [
        "total_vehicles",
        "completed_trips",
        "completed_ratio",
        "total_travel_time",
        "average_travel_time",
        "average_delay",
        "total_distance_traveled",
    ]
    aggregate_mismatches = []
    for key in aggregate_keys:
        f0_value = f0_case["results"][key]
        f1_value = f1_case["results"][key]
        if f0_value != f1_value:
            aggregate_mismatches.append(
                {"key": key, "f0": f0_value, "f1": f1_value}
            )

    f0_completion = f0_case["completion"]
    f1_completion = f1_case["completion"]
    if (
        f0_completion["unfinished_vehicle_count"]
        != f1_completion["unfinished_vehicle_count"]
    ):
        aggregate_mismatches.append(
            {
                "key": "unfinished_vehicle_count",
                "f0": f0_completion["unfinished_vehicle_count"],
                "f1": f1_completion["unfinished_vehicle_count"],
            }
        )
    if (
        f0_completion["last_completed_trip_time"]
        != f1_completion["last_completed_trip_time"]
    ):
        aggregate_mismatches.append(
            {
                "key": "last_completed_trip_time",
                "f0": f0_completion["last_completed_trip_time"],
                "f1": f1_completion["last_completed_trip_time"],
            }
        )

    f0_nodes = set(f0_case["eligible_node_names"])
    f1_nodes = set(f1_case["eligible_node_names"])
    eligible_node_mismatch = f0_nodes != f1_nodes

    f0_names = set(f0_case["vehicle_snapshots"])
    f1_names = set(f1_case["vehicle_snapshots"])
    vehicle_name_mismatch = f0_names != f1_names

    first_vehicle_mismatch = None
    traveled_route_first_diff = None
    log_t_link_first_diff = None
    diff_link_name = None

    for name in sorted(f0_names | f1_names):
        f0_snapshot = f0_case["vehicle_snapshots"].get(name)
        f1_snapshot = f1_case["vehicle_snapshots"].get(name)
        if f0_snapshot is None or f1_snapshot is None:
            first_vehicle_mismatch = name
            break

        for field in ("state", "arrival_time", "travel_time"):
            if f0_snapshot[field] != f1_snapshot[field]:
                first_vehicle_mismatch = name
                break

        if first_vehicle_mismatch is not None:
            break

        if (
            f0_snapshot["traveled_route_link_names"]
            != f1_snapshot["traveled_route_link_names"]
        ):
            first_vehicle_mismatch = name
            traveled_route_first_diff = _first_sequence_diff(
                f0_snapshot["traveled_route_link_names"],
                f1_snapshot["traveled_route_link_names"],
            )
            break

        if f0_snapshot["log_t_link_history"] != f1_snapshot["log_t_link_history"]:
            first_vehicle_mismatch = name
            log_t_link_first_diff = _first_sequence_diff(
                f0_snapshot["log_t_link_history"],
                f1_snapshot["log_t_link_history"],
            )
            if log_t_link_first_diff is not None:
                _, f0_entry, _f1_entry = log_t_link_first_diff
                if isinstance(f0_entry, tuple):
                    diff_link_name = f0_entry[1]
                else:
                    diff_link_name = f0_entry
            break

    return {
        "aggregate_mismatches": aggregate_mismatches,
        "eligible_node_mismatch": eligible_node_mismatch,
        "f0_nodes": f0_nodes,
        "f1_nodes": f1_nodes,
        "vehicle_name_mismatch": vehicle_name_mismatch,
        "first_vehicle_mismatch": first_vehicle_mismatch,
        "traveled_route_first_diff": traveled_route_first_diff,
        "log_t_link_first_diff": log_t_link_first_diff,
        "diff_link_name": diff_link_name,
    }


def _print_pass_summary(f0_case, f1_case):
    print("N=1 fixed-route grid equivalence result: PASS")
    print()
    print("Compared items:")
    print("  - aggregate metrics (strict equality)")
    print("  - eligible node set")
    print("  - vehicle name set")
    print("  - per-vehicle state, arrival_time, travel_time")
    print("  - traveled route link-name sequence")
    print("  - normalized log_t_link entry history")
    print()
    print(f"Vehicle count: {NUM_VEHICLES}")
    print(f"Fixed-route rule: {FIXED_ROUTE_RULE}")
    print(f"Eligible node count: {len(f0_case['eligible_node_names'])}")
    print(f"F0 elapsed seconds: {f0_case['elapsed_seconds']:.1f}")
    print(f"F1 elapsed seconds: {f1_case['elapsed_seconds']:.1f}")
    print()
    print("F0 (FCFS clearance=1) aggregate values:")
    for key, value in f0_case["results"].items():
        print(f"  {key}: {value}")
    print(
        f"  unfinished_vehicle_count: "
        f"{f0_case['completion']['unfinished_vehicle_count']}"
    )
    print(
        f"  last_completed_trip_time: "
        f"{f0_case['completion']['last_completed_trip_time']}"
    )
    print()
    print("F1 (BATCH N=1 clearance=1 Level 1) aggregate values:")
    for key, value in f1_case["results"].items():
        print(f"  {key}: {value}")
    print(
        f"  unfinished_vehicle_count: "
        f"{f1_case['completion']['unfinished_vehicle_count']}"
    )
    print(
        f"  last_completed_trip_time: "
        f"{f1_case['completion']['last_completed_trip_time']}"
    )
    print()
    print("Interpretation:")
    print(
        "  - On this small fixed-route 6x6 grid, FCFS clearance=1 and "
        "BATCH N=1 Level 1 clearance=1 matched exactly."
    )
    print(
        "  - Same-node revisit formal tests also match FCFS and size-one BATCH."
    )
    print(
        "  - After commit 2b10b08 (zero-service reformation fix), the "
        "10,000-vehicle free-route grid also matches FCFS and size-one BATCH "
        "exactly on all compared vehicle fields."
    )
    print(
        "  - This is not a general proof of equivalence for all networks, "
        "demand patterns, or control settings."
    )
    print(
        "  - This diagnostic is an independent fixed-route small-grid "
        "regression check before Level 2 design."
    )


def _print_fail_summary(f0_case, f1_case, comparison):
    print("N=1 fixed-route grid equivalence result: FAIL")
    print()
    print("Aggregate mismatches:")
    if comparison["aggregate_mismatches"]:
        for item in comparison["aggregate_mismatches"]:
            print(f"  - {item['key']}: F0={item['f0']!r}, F1={item['f1']!r}")
    else:
        print("  - none")
    print()

    first_name = comparison["first_vehicle_mismatch"]
    print(f"First mismatched vehicle (name order): {first_name!r}")
    if first_name is not None:
        print(f"  F0 snapshot: {f0_case['vehicle_snapshots'].get(first_name)!r}")
        print(f"  F1 snapshot: {f1_case['vehicle_snapshots'].get(first_name)!r}")

    if comparison["traveled_route_first_diff"] is not None:
        index, f0_value, f1_value = comparison["traveled_route_first_diff"]
        print(
            f"First traveled-route difference at index {index}: "
            f"F0={f0_value!r}, F1={f1_value!r}"
        )

    if comparison["log_t_link_first_diff"] is not None:
        index, f0_value, f1_value = comparison["log_t_link_first_diff"]
        print(
            f"First log_t_link difference at index {index}: "
            f"F0={f0_value!r}, F1={f1_value!r}"
        )
        link_name = comparison["diff_link_name"]
        if link_name is not None:
            start_node, end_node = _link_endpoints(f0_case["W_ref"], link_name)
            print(
                f"Corresponding link: {link_name!r} "
                f"(start_node={start_node!r}, end_node={end_node!r})"
            )

    if comparison["eligible_node_mismatch"]:
        only_f0 = sorted(comparison["f0_nodes"] - comparison["f1_nodes"])
        only_f1 = sorted(comparison["f1_nodes"] - comparison["f0_nodes"])
        print(f"Eligible node set difference: only in F0={only_f0!r}")
        print(f"Eligible node set difference: only in F1={only_f1!r}")

    print()
    print("Interpretation:")
    print(
        "  - Even with dynamic route choice removed, FCFS and N=1 BATCH diverged."
    )
    print(
        "  - A structural local order-control difference likely remains in "
        "multi-node environments."
    )
    print(
        "  - Level 2 design should not proceed until the N=1 vs FCFS specification "
        "is clarified; do not modify core code in this diagnostic step."
    )


def main():
    print("Small-scale fixed-route FCFS vs N=1 BATCH diagnostic")
    print(f"NUM_VEHICLES={NUM_VEHICLES}, TMAX={TMAX}, RANDOM_SEED={RANDOM_SEED}")
    print(f"DEMAND_GEN_SEED={DEMAND_GEN_SEED}")
    print(f"Fixed-route rule: {FIXED_ROUTE_RULE}")
    print()

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    _attach_fixed_routes(vehicle_plans)

    f0_case = _run_case("F0", "fcfs", vehicle_plans)
    print(
        f"Case F0 completed in {f0_case['elapsed_seconds']:.1f} s "
        f"(mode=FCFS clearance=1)"
    )

    f1_case = _run_case("F1", "batch", vehicle_plans)
    print(
        f"Case F1 completed in {f1_case['elapsed_seconds']:.1f} s "
        f"(mode=BATCH N=1 Level 1 clearance=1)"
    )
    print()

    comparison = _compare_cases(f0_case, f1_case)
    f0_case["W_ref"] = None

    has_fail = (
        comparison["aggregate_mismatches"]
        or comparison["eligible_node_mismatch"]
        or comparison["vehicle_name_mismatch"]
        or comparison["first_vehicle_mismatch"] is not None
    )

    if has_fail:
        # Keep a World reference only for fail diagnostics on link endpoints.
        W_for_links = _create_world("fcfs")
        _add_grid_network(W_for_links)
        f0_case["W_ref"] = W_for_links
        _print_fail_summary(f0_case, f1_case, comparison)
        raise AssertionError("F0/F1 fixed-route equivalence check failed")

    _print_pass_summary(f0_case, f1_case)


if __name__ == "__main__":
    main()
