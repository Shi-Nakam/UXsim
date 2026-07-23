# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Phase 4-6N: high-demand grid comparison — signalized UXsim all-red vs
# FCFS(clearance=1) vs Level 1 BATCH(clearance=1, batch_size=10) on 6x6 grid.
# Extends the existing signalized all-red vs FCFS high-demand sanity check
# by adding BATCH as a third mode. Compares 5,000- and 10,000-vehicle cases.
# Records pre–node-revisit-fix state. Performance ordering is NOT pass/fail.
#
# - Not part of the normal test suite; do not add to automated regression runs.
# - BATCH may exit with a known prefix violation (e.g. g_5_4, veh_1952 at
#   5,000 vehicles); that is intentional reproduction, not a test failure.
# - Level 1 BATCH is provisional before Level 2 (research design: Level 2,
#   then Level 1 fallback, then Level 0 if needed).
# - Formal record: ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md §1G
#
# Run from the repository root:
#   python diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import random

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = GRID_SIZE * GRID_SIZE
EXTERNAL_OD_NODE_COUNT = 4 * GRID_SIZE
MIN_ELIGIBLE_NODES = 32
MIN_OD_MANHATTAN_DISTANCE = 5
GREEN_TIME = 60
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
FCFS_CLEARANCE_TIMESTEPS = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
BATCH_SIZE = 10
BATCH_T_TRIGGER_LEVEL = 1

HIGH_DEMAND_CASES = [
    {
        "case_name": "5000 vehicles, departure 0-500, tmax=30000",
        "num_vehicles": 5000,
        "departure_start": 0,
        "departure_end": 500,
        "tmax": 30000,
    },
    {
        "case_name": "10000 vehicles, departure 0-500, tmax=50000",
        "num_vehicles": 10000,
        "departure_start": 0,
        "departure_end": 500,
        "tmax": 50000,
    },
]

COMPLETED_RATIO_MIN = 0.5
FCFS_COMPLETED_RATIO_FACTOR = 0.5
TRAVEL_TIME_RATIO_MIN = 0.25
TRAVEL_TIME_RATIO_MAX = 4.0
TOTAL_TRAVEL_TIME_RATIO_MIN = 0.25
TOTAL_TRAVEL_TIME_RATIO_MAX = 4.0
DISTANCE_RATIO_MIN = 0.4
DISTANCE_RATIO_MAX = 1.6

APPROX_EQUAL_AVG_TRAVEL_TIME_TOLERANCE = 0.05

SIGNAL_OFFSET_STRATEGY = (
    "signal_offset = ((row + column) % 4) * (cycle_length / 4); "
    "staggered offsets to avoid fully synchronized grid-wide phase switching"
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
INTERNAL_GRID_NODES = _internal_grid_node_names()


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


def _demand_summary(vehicle_plans, case_name, tmax):
    origins = [plan["origin"] for plan in vehicle_plans]
    destinations = [plan["destination"] for plan in vehicle_plans]
    departure_times = [plan["departure_time"] for plan in vehicle_plans]
    origin_grid_coords = [plan["origin_grid_coord"] for plan in vehicle_plans]
    destination_grid_coords = [
        plan["destination_grid_coord"] for plan in vehicle_plans
    ]
    manhattan_distances = [plan["manhattan_distance"] for plan in vehicle_plans]
    first_departure = departure_times[0]
    last_departure = departure_times[-1]
    demand_duration = last_departure - first_departure
    average_interval = demand_duration / max(len(departure_times) - 1, 1)
    vehicles_per_timestep = len(departure_times) / max(demand_duration, 1)
    return {
        "case_name": case_name,
        "tmax": tmax,
        "total_vehicles": len(vehicle_plans),
        "first_departure_time": first_departure,
        "last_departure_time": last_departure,
        "demand_duration": demand_duration,
        "average_departure_interval": average_interval,
        "vehicles_per_timestep": vehicles_per_timestep,
        "minimum_od_manhattan_distance": min(manhattan_distances),
        "average_od_manhattan_distance": sum(manhattan_distances) / len(
            manhattan_distances
        ),
        "maximum_od_manhattan_distance": max(manhattan_distances),
        "origin_sequence": origins,
        "destination_sequence": destinations,
        "departure_time_sequence": departure_times,
        "origin_grid_coord_sequence": origin_grid_coords,
        "destination_grid_coord_sequence": destination_grid_coords,
        "manhattan_distance_sequence": manhattan_distances,
    }


def _compute_signal_params(W):
    signal_clearance_duration = W.DELTAT
    signal_setting = [
        GREEN_TIME,
        signal_clearance_duration,
        GREEN_TIME,
        signal_clearance_duration,
    ]
    cycle_length = sum(signal_setting)
    return {
        "deltat": W.DELTAT,
        "signal_clearance_duration": signal_clearance_duration,
        "signal_setting": signal_setting,
        "cycle_length": cycle_length,
    }


def _signal_offset_for_node(row, column, cycle_length):
    return ((row + column) % 4) * (cycle_length / 4)


def _count_links_by_signal_group(W):
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for link in W.LINKS:
        groups = link.signal_group
        if not isinstance(groups, list):
            groups = [groups]
        for group in groups:
            if group in counts:
                counts[group] += 1
            else:
                counts[group] = counts.get(group, 0) + 1
    return counts


def _add_grid_network(W, control_mode, signal_params=None):
    spacing = 1.0
    signalize_internal = control_mode == "signalized_all_red"

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            node_name = _grid_node_name(row, column)
            if signalize_internal:
                signal_setting = signal_params["signal_setting"]
                cycle_length = signal_params["cycle_length"]
                signal_offset = _signal_offset_for_node(row, column, cycle_length)
                W.addNode(
                    node_name,
                    column * spacing,
                    -row * spacing,
                    signal=signal_setting,
                    signal_offset=signal_offset,
                )
            else:
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


def _grid_network_summary(W):
    return {
        "grid_size": GRID_SIZE,
        "internal_grid_node_count": INTERNAL_GRID_NODE_COUNT,
        "external_od_node_count": EXTERNAL_OD_NODE_COUNT,
        "total_node_count": len(W.NODES),
        "total_link_count": len(W.LINKS),
        "bidirectional_internal_links": True,
        "bidirectional_od_connector_links": True,
        "merge_priority": MERGE_PRIORITY,
        "number_of_lanes": NUMBER_OF_LANES,
    }


def _collect_signalized_all_red_control_summary(W, signal_params):
    signalized_internal_nodes = []
    signalized_od_nodes = []
    signal_offsets = {}
    for node in W.NODES:
        signal = getattr(node, "signal", None)
        if signal is None:
            continue
        if node.name in INTERNAL_GRID_NODES and signal != [0]:
            signalized_internal_nodes.append(node.name)
            signal_offsets[node.name] = getattr(node, "signal_offset", None)
        elif node.name in EXTERNAL_OD_NODES and signal != [0]:
            signalized_od_nodes.append(node.name)

    signal_group_counts = _count_links_by_signal_group(W)
    unique_offsets = sorted(set(signal_offsets.values()))

    return {
        "standard_control_type_used": (
            "UXsim standard Node.transfer with 4-phase all-red clearance signals "
            "on internal grid nodes (order_control_type='none', "
            "set_order_control_for_nodes not called)"
        ),
        "deltat": signal_params["deltat"],
        "signal_clearance_duration": signal_params["signal_clearance_duration"],
        "signal_setting": signal_params["signal_setting"],
        "signal_cycle_length": signal_params["cycle_length"],
        "internal_grid_signal_setting": signal_params["signal_setting"],
        "signalized_internal_grid_node_count": len(signalized_internal_nodes),
        "signalized_od_node_count": len(signalized_od_nodes),
        "signal_groups": {
            "0": "east-west links (phase 0 green; horizontal internal and left/right connectors)",
            "1": "unused (all-red phase 1; no links assigned)",
            "2": "north-south links (phase 2 green; vertical internal and top/bottom connectors)",
            "3": "unused (all-red phase 3; no links assigned)",
        },
        "signal_group_1_link_count": signal_group_counts.get(1, 0),
        "signal_group_3_link_count": signal_group_counts.get(3, 0),
        "signal_offset_strategy": SIGNAL_OFFSET_STRATEGY,
        "signal_offset_unique_values": unique_offsets,
        "signal_offsets": signal_offsets if signal_offsets else "default (0)",
        "note": (
            "4-phase signal [60, W.DELTAT, 60, W.DELTAT] on internal grid nodes only; "
            "phases 1 and 3 are all-red with no assigned signal_group links; "
            "external OD nodes remain unsignalized (signal=[0])"
        ),
    }


def _add_vehicles(W, vehicle_plans):
    for plan in vehicle_plans:
        W.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )


def _collect_traffic_results(W):
    analyzer = W.analyzer
    completed_trips = int(analyzer.trip_completed)
    total_trips = int(analyzer.trip_all)
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
    return {
        "completed_trips": completed_trips,
        "total_vehicles": total_trips,
        "completed_ratio": completed_ratio,
        "total_travel_time": total_travel_time,
        "average_travel_time": average_travel_time,
        "average_delay": average_delay,
        "delay_ratio": delay_ratio,
        "total_distance_traveled": total_distance_traveled,
    }


def _collect_unfinished_summary(W, traffic_results):
    unfinished_count = (
        traffic_results["total_vehicles"] - traffic_results["completed_trips"]
    )
    total_vehicles = traffic_results["total_vehicles"]
    unfinished_ratio = unfinished_count / total_vehicles if total_vehicles else 0.0
    return {
        "unfinished_vehicle_count": unfinished_count,
        "unfinished_vehicle_ratio": unfinished_ratio,
    }


def _collect_completion_time_summary(W, tmax):
    completed_arrival_times_seconds = []
    completed_travel_times = []
    for veh in W.VEHICLES.values():
        if veh.arrival_time >= 0 and veh.travel_time >= 0:
            completed_arrival_times_seconds.append(veh.arrival_time * W.DELTAT)
            completed_travel_times.append(float(veh.travel_time))

    if not completed_arrival_times_seconds:
        return {
            "last_completed_trip_time": "not available",
            "max_completed_travel_time": "not available",
            "last_completed_trip_time_over_tmax": "not available",
        }

    last_completed_trip_time = max(completed_arrival_times_seconds)
    max_completed_travel_time = max(completed_travel_times)
    return {
        "last_completed_trip_time": last_completed_trip_time,
        "max_completed_travel_time": max_completed_travel_time,
        "last_completed_trip_time_over_tmax": last_completed_trip_time / tmax,
    }


def _eligible_node_names(W):
    return [node.name for node in W.NODES if node.order_control_eligible]


def _verify_batch_node_settings(W, eligible_node_names):
    for name in eligible_node_names:
        node = W.get_node(name)
        if not node.order_control_eligible:
            raise AssertionError(
                f"node {name}: order_control_eligible={node.order_control_eligible}, "
                "expected True"
            )
        if node.order_control_type != "batch":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, expected 'batch'"
            )
        if node.batch_size != BATCH_SIZE:
            raise AssertionError(
                f"node {name}: batch_size={node.batch_size}, expected {BATCH_SIZE}"
            )
        if node.order_control_batch_t_trigger_level != BATCH_T_TRIGGER_LEVEL:
            raise AssertionError(
                f"node {name}: order_control_batch_t_trigger_level="
                f"{node.order_control_batch_t_trigger_level}, expected {BATCH_T_TRIGGER_LEVEL}"
            )
        if node.order_control_clearance_timesteps != FCFS_CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, expected {FCFS_CLEARANCE_TIMESTEPS}"
            )


def build_world(control_mode, vehicle_plans, tmax):
    W = World(
        name=f"batch_fcfs_signalized_all_red_{control_mode}",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    signal_params = _compute_signal_params(W)

    if control_mode == "signalized_all_red":
        _add_grid_network(W, control_mode, signal_params=signal_params)
    else:
        _add_grid_network(W, control_mode)

    _add_vehicles(W, vehicle_plans)

    eligible_node_names = []
    if control_mode == "fcfs":
        W.infer_order_control_eligible_nodes()
        W.set_order_control_clearance_timesteps(FCFS_CLEARANCE_TIMESTEPS)
        eligible_node_names = _eligible_node_names(W)
        assert len(eligible_node_names) >= MIN_ELIGIBLE_NODES
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="fcfs",
        )
    elif control_mode == "batch":
        W.infer_order_control_eligible_nodes()
        W.set_order_control_clearance_timesteps(FCFS_CLEARANCE_TIMESTEPS)
        eligible_node_names = _eligible_node_names(W)
        assert len(eligible_node_names) >= MIN_ELIGIBLE_NODES
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="batch",
            batch_size=BATCH_SIZE,
            order_control_batch_t_trigger_level=BATCH_T_TRIGGER_LEVEL,
        )
        _verify_batch_node_settings(W, eligible_node_names)
    elif control_mode != "signalized_all_red":
        raise ValueError(f"unsupported control_mode: {control_mode!r}")

    W.exec_simulation()
    return W, eligible_node_names, signal_params


def _safe_ratio(numerator, denominator):
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _comparison_ratios(numerator_results, denominator_results):
    return {
        "completed_ratio_difference": (
            numerator_results["completed_ratio"] - denominator_results["completed_ratio"]
        ),
        "average_travel_time_ratio": _safe_ratio(
            numerator_results["average_travel_time"],
            denominator_results["average_travel_time"],
        ),
        "total_travel_time_ratio": _safe_ratio(
            numerator_results["total_travel_time"],
            denominator_results["total_travel_time"],
        ),
        "total_distance_traveled_ratio": _safe_ratio(
            numerator_results["total_distance_traveled"],
            denominator_results["total_distance_traveled"],
        ),
    }


def _numeric_difference(batch_value, fcfs_value):
    if isinstance(batch_value, (int, float)) and isinstance(fcfs_value, (int, float)):
        return batch_value - fcfs_value
    return "not available"


def _batch_vs_fcfs_differences(
    batch_results,
    fcfs_results,
    batch_unfinished,
    fcfs_unfinished,
    batch_completion,
    fcfs_completion,
):
    return {
        "completed_trips_difference": (
            batch_results["completed_trips"] - fcfs_results["completed_trips"]
        ),
        "completed_ratio_difference": (
            batch_results["completed_ratio"] - fcfs_results["completed_ratio"]
        ),
        "total_travel_time_difference": (
            batch_results["total_travel_time"] - fcfs_results["total_travel_time"]
        ),
        "average_travel_time_difference": (
            batch_results["average_travel_time"] - fcfs_results["average_travel_time"]
        ),
        "average_delay_difference": (
            batch_results["average_delay"] - fcfs_results["average_delay"]
        ),
        "total_distance_traveled_difference": (
            batch_results["total_distance_traveled"]
            - fcfs_results["total_distance_traveled"]
        ),
        "unfinished_vehicle_difference": (
            batch_unfinished["unfinished_vehicle_count"]
            - fcfs_unfinished["unfinished_vehicle_count"]
        ),
        "last_completed_trip_time_difference": _numeric_difference(
            batch_completion["last_completed_trip_time"],
            fcfs_completion["last_completed_trip_time"],
        ),
        "max_completed_travel_time_difference": _numeric_difference(
            batch_completion["max_completed_travel_time"],
            fcfs_completion["max_completed_travel_time"],
        ),
    }


def _batch_vs_fcfs_travel_time_interpretation(batch_results, fcfs_results):
    batch_avg = batch_results["average_travel_time"]
    fcfs_avg = fcfs_results["average_travel_time"]
    if abs(batch_avg - fcfs_avg) <= APPROX_EQUAL_AVG_TRAVEL_TIME_TOLERANCE:
        return "approximately equal"
    if batch_avg < fcfs_avg:
        return "lower"
    return "higher"


def _format_signalized_all_red_control_summary(summary):
    return (
        "Signalized all-red control summary:\n"
        f"- standard control type used: {summary['standard_control_type_used']}\n"
        f"- W.DELTAT: {summary['deltat']}\n"
        f"- signal_clearance_duration: {summary['signal_clearance_duration']}\n"
        f"- signal_setting: {summary['signal_setting']}\n"
        f"- signal cycle length: {summary['signal_cycle_length']}\n"
        f"- internal grid signal setting: {summary['internal_grid_signal_setting']}\n"
        f"- signalized internal grid node count: {summary['signalized_internal_grid_node_count']}\n"
        f"- signalized OD node count: {summary['signalized_od_node_count']}\n"
        f"- signal groups: {summary['signal_groups']}\n"
        f"- signal_group=1 link count: {summary['signal_group_1_link_count']}\n"
        f"- signal_group=3 link count: {summary['signal_group_3_link_count']}\n"
        f"- signal_offset strategy: {summary['signal_offset_strategy']}\n"
        f"- signal offset unique values: {summary['signal_offset_unique_values']}\n"
        f"- signal offsets for internal grid nodes: {summary['signal_offsets']}\n"
        f"- note: {summary['note']}"
    )


def _format_grid_network_summary(summary):
    return (
        "Grid network summary:\n"
        f"- grid size: {summary['grid_size']}\n"
        f"- internal grid node count: {summary['internal_grid_node_count']}\n"
        f"- external OD node count: {summary['external_od_node_count']}\n"
        f"- total node count: {summary['total_node_count']}\n"
        f"- total link count: {summary['total_link_count']}\n"
        f"- bidirectional internal links: {summary['bidirectional_internal_links']}\n"
        f"- bidirectional OD connector links: {summary['bidirectional_od_connector_links']}\n"
        f"- merge_priority: {summary['merge_priority']}\n"
        f"- number_of_lanes: {summary['number_of_lanes']}"
    )


def _format_demand_summary(summary):
    return (
        "Demand summary:\n"
        f"- case name: {summary['case_name']}\n"
        f"- total vehicles: {summary['total_vehicles']}\n"
        f"- first departure time: {summary['first_departure_time']}\n"
        f"- last departure time: {summary['last_departure_time']}\n"
        f"- demand duration: {summary['demand_duration']}\n"
        f"- average departure interval: {summary['average_departure_interval']}\n"
        f"- vehicles per timestep: {summary['vehicles_per_timestep']}\n"
        f"- minimum OD manhattan distance: {summary['minimum_od_manhattan_distance']}\n"
        f"- average OD manhattan distance: {summary['average_od_manhattan_distance']}\n"
        f"- maximum OD manhattan distance: {summary['maximum_od_manhattan_distance']}\n"
        f"- tmax: {summary['tmax']}"
    )


def _format_results(label, results):
    delay_ratio_text = (
        f"{results['delay_ratio']:.3f}"
        if results["delay_ratio"] is not None
        else "not available"
    )
    return (
        f"{label}:\n"
        f"- completed trips: {results['completed_trips']}\n"
        f"- total vehicles: {results['total_vehicles']}\n"
        f"- completed ratio: {results['completed_ratio']:.3f}\n"
        f"- total travel time: {results['total_travel_time']:.1f} s\n"
        f"- average travel time: {results['average_travel_time']:.1f} s\n"
        f"- average delay: {results['average_delay']:.1f} s\n"
        f"- delay ratio: {delay_ratio_text}\n"
        f"- total distance traveled: {results['total_distance_traveled']:.1f} m"
    )


def _format_unfinished_summary(label, summary):
    return (
        f"{label}:\n"
        f"- unfinished vehicle count: {summary['unfinished_vehicle_count']}\n"
        f"- unfinished vehicle ratio: {summary['unfinished_vehicle_ratio']:.3f}"
    )


def _format_completion_time_summary(label, summary):
    last_time = summary["last_completed_trip_time"]
    max_travel = summary["max_completed_travel_time"]
    last_over_tmax = summary["last_completed_trip_time_over_tmax"]

    if isinstance(last_time, (int, float)):
        last_time_text = f"{last_time:.1f} s"
    else:
        last_time_text = last_time

    if isinstance(max_travel, (int, float)):
        max_travel_text = f"{max_travel:.1f} s"
    else:
        max_travel_text = max_travel

    if isinstance(last_over_tmax, (int, float)):
        last_over_tmax_text = f"{last_over_tmax:.3f}"
    else:
        last_over_tmax_text = last_over_tmax

    return (
        f"{label}:\n"
        f"- last completed trip time: {last_time_text}\n"
        f"- max completed travel time: {max_travel_text}\n"
        f"- last completed trip time / tmax: {last_over_tmax_text}"
    )


def _format_ratio_block(title, ratios):
    return (
        f"{title}:\n"
        f"- completed ratio difference: {ratios['completed_ratio_difference']:.3f}\n"
        f"- average travel time ratio: {ratios['average_travel_time_ratio']}\n"
        f"- total travel time ratio: {ratios['total_travel_time_ratio']}\n"
        f"- total distance traveled ratio: {ratios['total_distance_traveled_ratio']}"
    )


def _format_numeric_difference(value, unit=""):
    if isinstance(value, (int, float)):
        if unit == "s":
            return f"{value:.3f} s"
        if unit == "m":
            return f"{value:.1f} m"
        return f"{value}"
    return value


def _format_difference_block(title, differences):
    return (
        f"{title}:\n"
        f"- completed trips difference (batch - fcfs): "
        f"{differences['completed_trips_difference']}\n"
        f"- completed ratio difference (batch - fcfs): "
        f"{differences['completed_ratio_difference']:.3f}\n"
        f"- total travel time difference (batch - fcfs): "
        f"{_format_numeric_difference(differences['total_travel_time_difference'], 's')}\n"
        f"- average travel time difference (batch - fcfs): "
        f"{_format_numeric_difference(differences['average_travel_time_difference'], 's')}\n"
        f"- average delay difference (batch - fcfs): "
        f"{_format_numeric_difference(differences['average_delay_difference'], 's')}\n"
        f"- total distance traveled difference (batch - fcfs): "
        f"{_format_numeric_difference(differences['total_distance_traveled_difference'], 'm')}\n"
        f"- unfinished vehicle difference (batch - fcfs): "
        f"{differences['unfinished_vehicle_difference']}\n"
        f"- last completed trip time difference (batch - fcfs): "
        f"{_format_numeric_difference(differences['last_completed_trip_time_difference'], 's')}\n"
        f"- max completed travel time difference (batch - fcfs): "
        f"{_format_numeric_difference(differences['max_completed_travel_time_difference'], 's')}"
    )


def _build_report_context(
    *,
    case_name,
    signalized_control_summary,
    grid_network_summary,
    demand_summary,
    signalized_results,
    fcfs_results,
    batch_results,
    signalized_unfinished,
    fcfs_unfinished,
    batch_unfinished,
    signalized_completion,
    fcfs_completion,
    batch_completion,
    fcfs_eligible_node_names,
    batch_eligible_node_names,
    order_control_clearance_timesteps,
    fcfs_vs_signalized_ratios,
    batch_vs_signalized_ratios,
    batch_vs_fcfs_ratios,
    batch_vs_fcfs_differences,
    batch_vs_fcfs_travel_time_interpretation,
    sanity_checks,
):
    eligible_match = fcfs_eligible_node_names == batch_eligible_node_names
    return (
        f"Case summary: {case_name}\n\n"
        f"{_format_signalized_all_red_control_summary(signalized_control_summary)}\n\n"
        f"{_format_grid_network_summary(grid_network_summary)}\n\n"
        f"{_format_demand_summary(demand_summary)}\n\n"
        f"{_format_results('Signalized UXsim standard with all-red clearance results', signalized_results)}\n\n"
        f"{_format_results('FCFS clearance=1 results', fcfs_results)}\n\n"
        f"{_format_results('BATCH Level 1, clearance=1, batch_size=10 results', batch_results)}\n\n"
        f"{_format_unfinished_summary('Signalized UXsim standard with all-red unfinished vehicle summary', signalized_unfinished)}\n\n"
        f"{_format_unfinished_summary('FCFS clearance=1 unfinished vehicle summary', fcfs_unfinished)}\n\n"
        f"{_format_unfinished_summary('BATCH Level 1, clearance=1 unfinished vehicle summary', batch_unfinished)}\n\n"
        f"{_format_completion_time_summary('Signalized UXsim standard with all-red completion time summary', signalized_completion)}\n\n"
        f"{_format_completion_time_summary('FCFS clearance=1 completion time summary', fcfs_completion)}\n\n"
        f"{_format_completion_time_summary('BATCH Level 1, clearance=1 completion time summary', batch_completion)}\n\n"
        f"{_format_ratio_block('Comparison ratios (FCFS / signalized all-red)', fcfs_vs_signalized_ratios)}\n\n"
        f"{_format_ratio_block('Comparison ratios (BATCH / signalized all-red)', batch_vs_signalized_ratios)}\n\n"
        f"{_format_ratio_block('Comparison ratios (BATCH / FCFS)', batch_vs_fcfs_ratios)}\n\n"
        "BATCH vs FCFS average travel time:\n"
        f"- average travel time ratio (batch / fcfs): "
        f"{batch_vs_fcfs_ratios['average_travel_time_ratio']}\n"
        f"- batch average travel time compared with fcfs: "
        f"{batch_vs_fcfs_travel_time_interpretation}\n\n"
        f"{_format_difference_block('BATCH vs FCFS differences', batch_vs_fcfs_differences)}\n\n"
        "Eligible order-control nodes:\n"
        f"- FCFS count: {len(fcfs_eligible_node_names)}\n"
        f"- FCFS names: {fcfs_eligible_node_names}\n"
        f"- BATCH count: {len(batch_eligible_node_names)}\n"
        f"- BATCH names: {batch_eligible_node_names}\n"
        f"- FCFS and BATCH eligible node sets match: {eligible_match}\n\n"
        f"Order-control clearance_timesteps: {order_control_clearance_timesteps}\n\n"
        "Sanity checks:\n"
        + "\n".join(f"- {name}: {status}" for name, status in sanity_checks.items())
    )


def _ratio_within_range(ratio, minimum, maximum):
    return ratio is not None and minimum <= ratio <= maximum


def _run_high_demand_case(case):
    case_name = case["case_name"]
    num_vehicles = case["num_vehicles"]
    departure_start = case["departure_start"]
    departure_end = case["departure_end"]
    tmax = case["tmax"]

    vehicle_plans = _generate_vehicle_plans(
        num_vehicles, departure_start, departure_end
    )
    demand_summary = _demand_summary(vehicle_plans, case_name, tmax)

    signalized_W, _, signal_params = build_world(
        "signalized_all_red", vehicle_plans, tmax
    )
    signalized_control_summary = _collect_signalized_all_red_control_summary(
        signalized_W, signal_params
    )
    grid_network_summary = _grid_network_summary(signalized_W)
    signalized_results = _collect_traffic_results(signalized_W)
    signalized_unfinished = _collect_unfinished_summary(
        signalized_W, signalized_results
    )
    signalized_completion = _collect_completion_time_summary(signalized_W, tmax)

    fcfs_W, fcfs_eligible, _ = build_world("fcfs", vehicle_plans, tmax)
    fcfs_results = _collect_traffic_results(fcfs_W)
    fcfs_unfinished = _collect_unfinished_summary(fcfs_W, fcfs_results)
    fcfs_completion = _collect_completion_time_summary(fcfs_W, tmax)

    batch_W, batch_eligible, _ = build_world("batch", vehicle_plans, tmax)
    batch_results = _collect_traffic_results(batch_W)
    batch_unfinished = _collect_unfinished_summary(batch_W, batch_results)
    batch_completion = _collect_completion_time_summary(batch_W, tmax)
    order_control_clearance_timesteps = batch_W.order_control_clearance_timesteps

    fcfs_vs_signalized_ratios = _comparison_ratios(fcfs_results, signalized_results)
    batch_vs_signalized_ratios = _comparison_ratios(batch_results, signalized_results)
    batch_vs_fcfs_ratios = _comparison_ratios(batch_results, fcfs_results)
    batch_vs_fcfs_differences = _batch_vs_fcfs_differences(
        batch_results,
        fcfs_results,
        batch_unfinished,
        fcfs_unfinished,
        batch_completion,
        fcfs_completion,
    )
    batch_vs_fcfs_travel_time_interpretation = _batch_vs_fcfs_travel_time_interpretation(
        batch_results,
        fcfs_results,
    )

    sanity_checks = {}

    sanity_checks["total vehicles equal (signalized/fcfs/batch)"] = (
        "pass"
        if signalized_results["total_vehicles"]
        == fcfs_results["total_vehicles"]
        == batch_results["total_vehicles"]
        else "fail"
    )
    sanity_checks["demand summary equal"] = (
        "pass"
        if demand_summary["total_vehicles"] == num_vehicles
        and demand_summary["origin_sequence"]
        == [plan["origin"] for plan in vehicle_plans]
        and demand_summary["destination_sequence"]
        == [plan["destination"] for plan in vehicle_plans]
        and demand_summary["departure_time_sequence"]
        == [plan["departure_time"] for plan in vehicle_plans]
        and demand_summary["origin_grid_coord_sequence"]
        == [plan["origin_grid_coord"] for plan in vehicle_plans]
        and demand_summary["destination_grid_coord_sequence"]
        == [plan["destination_grid_coord"] for plan in vehicle_plans]
        and demand_summary["manhattan_distance_sequence"]
        == [plan["manhattan_distance"] for plan in vehicle_plans]
        else "fail"
    )
    sanity_checks["signalized internal grid node count == 36"] = (
        "pass"
        if signalized_control_summary["signalized_internal_grid_node_count"]
        == INTERNAL_GRID_NODE_COUNT
        else "fail"
    )
    sanity_checks["signalized OD node count == 0"] = (
        "pass"
        if signalized_control_summary["signalized_od_node_count"] == 0
        else "fail"
    )
    sanity_checks["signal_group=1 link count == 0"] = (
        "pass"
        if signalized_control_summary["signal_group_1_link_count"] == 0
        else "fail"
    )
    sanity_checks["signal_group=3 link count == 0"] = (
        "pass"
        if signalized_control_summary["signal_group_3_link_count"] == 0
        else "fail"
    )
    sanity_checks["signal setting matches existing value"] = (
        "pass"
        if signalized_control_summary["signal_setting"] == signal_params["signal_setting"]
        else "fail"
    )
    sanity_checks["signal clearance duration equals W.DELTAT"] = (
        "pass"
        if signalized_control_summary["signal_clearance_duration"]
        == signal_params["deltat"]
        else "fail"
    )
    sanity_checks["fcfs eligible node count >= 32"] = (
        "pass" if len(fcfs_eligible) >= MIN_ELIGIBLE_NODES else "fail"
    )
    sanity_checks["batch eligible node count >= 32"] = (
        "pass" if len(batch_eligible) >= MIN_ELIGIBLE_NODES else "fail"
    )
    sanity_checks["fcfs and batch eligible node sets match"] = (
        "pass" if fcfs_eligible == batch_eligible else "fail"
    )
    sanity_checks["fcfs clearance_timesteps == 1"] = (
        "pass"
        if fcfs_W.order_control_clearance_timesteps == FCFS_CLEARANCE_TIMESTEPS
        else "fail"
    )
    sanity_checks["batch clearance_timesteps == 1"] = (
        "pass"
        if order_control_clearance_timesteps == FCFS_CLEARANCE_TIMESTEPS
        else "fail"
    )
    sanity_checks["signalized all-red completed ratio >= threshold"] = (
        "pass"
        if signalized_results["completed_ratio"] >= COMPLETED_RATIO_MIN
        else "fail"
    )
    sanity_checks["fcfs completed ratio >= threshold"] = (
        "pass"
        if fcfs_results["completed_ratio"] >= COMPLETED_RATIO_MIN
        else "fail"
    )
    sanity_checks["batch completed ratio >= threshold"] = (
        "pass"
        if batch_results["completed_ratio"] >= COMPLETED_RATIO_MIN
        else "fail"
    )
    sanity_checks["fcfs completed ratio not extremely worse than signalized"] = (
        "pass"
        if fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * signalized_results["completed_ratio"]
        else "fail"
    )
    sanity_checks["batch completed ratio not extremely worse than signalized"] = (
        "pass"
        if batch_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * signalized_results["completed_ratio"]
        else "fail"
    )

    fcfs_avg_tt_ratio = fcfs_vs_signalized_ratios["average_travel_time_ratio"]
    sanity_checks["fcfs average travel time ratio (fcfs/signalized) within range"] = (
        "pass"
        if _ratio_within_range(fcfs_avg_tt_ratio, TRAVEL_TIME_RATIO_MIN, TRAVEL_TIME_RATIO_MAX)
        else "fail"
    )

    batch_avg_tt_ratio = batch_vs_signalized_ratios["average_travel_time_ratio"]
    sanity_checks["batch average travel time ratio (batch/signalized) within range"] = (
        "pass"
        if _ratio_within_range(batch_avg_tt_ratio, TRAVEL_TIME_RATIO_MIN, TRAVEL_TIME_RATIO_MAX)
        else "fail"
    )

    fcfs_total_tt_ratio = fcfs_vs_signalized_ratios["total_travel_time_ratio"]
    sanity_checks["fcfs total travel time ratio (fcfs/signalized) within range"] = (
        "pass"
        if _ratio_within_range(
            fcfs_total_tt_ratio,
            TOTAL_TRAVEL_TIME_RATIO_MIN,
            TOTAL_TRAVEL_TIME_RATIO_MAX,
        )
        else "fail"
    )

    batch_total_tt_ratio = batch_vs_signalized_ratios["total_travel_time_ratio"]
    sanity_checks["batch total travel time ratio (batch/signalized) within range"] = (
        "pass"
        if _ratio_within_range(
            batch_total_tt_ratio,
            TOTAL_TRAVEL_TIME_RATIO_MIN,
            TOTAL_TRAVEL_TIME_RATIO_MAX,
        )
        else "fail"
    )

    fcfs_dist_ratio = fcfs_vs_signalized_ratios["total_distance_traveled_ratio"]
    sanity_checks["fcfs total distance traveled ratio (fcfs/signalized) within range"] = (
        "pass"
        if _ratio_within_range(fcfs_dist_ratio, DISTANCE_RATIO_MIN, DISTANCE_RATIO_MAX)
        else "fail"
    )

    batch_dist_ratio = batch_vs_signalized_ratios["total_distance_traveled_ratio"]
    sanity_checks["batch total distance traveled ratio (batch/signalized) within range"] = (
        "pass"
        if _ratio_within_range(batch_dist_ratio, DISTANCE_RATIO_MIN, DISTANCE_RATIO_MAX)
        else "fail"
    )

    report = _build_report_context(
        case_name=case_name,
        signalized_control_summary=signalized_control_summary,
        grid_network_summary=grid_network_summary,
        demand_summary=demand_summary,
        signalized_results=signalized_results,
        fcfs_results=fcfs_results,
        batch_results=batch_results,
        signalized_unfinished=signalized_unfinished,
        fcfs_unfinished=fcfs_unfinished,
        batch_unfinished=batch_unfinished,
        signalized_completion=signalized_completion,
        fcfs_completion=fcfs_completion,
        batch_completion=batch_completion,
        fcfs_eligible_node_names=fcfs_eligible,
        batch_eligible_node_names=batch_eligible,
        order_control_clearance_timesteps=order_control_clearance_timesteps,
        fcfs_vs_signalized_ratios=fcfs_vs_signalized_ratios,
        batch_vs_signalized_ratios=batch_vs_signalized_ratios,
        batch_vs_fcfs_ratios=batch_vs_fcfs_ratios,
        batch_vs_fcfs_differences=batch_vs_fcfs_differences,
        batch_vs_fcfs_travel_time_interpretation=batch_vs_fcfs_travel_time_interpretation,
        sanity_checks=sanity_checks,
    )
    print(report)

    assert signalized_control_summary["signalized_internal_grid_node_count"] == (
        INTERNAL_GRID_NODE_COUNT
    ), f"internal grid nodes not all signalized\n{report}"
    assert signalized_control_summary["signalized_od_node_count"] == 0, (
        f"external OD nodes should remain unsignalized\n{report}"
    )
    assert signalized_control_summary["signal_group_1_link_count"] == 0, (
        f"signal_group=1 links should not exist\n{report}"
    )
    assert signalized_control_summary["signal_group_3_link_count"] == 0, (
        f"signal_group=3 links should not exist\n{report}"
    )
    assert signalized_control_summary["signal_setting"] == signal_params["signal_setting"], (
        f"signal setting mismatch\n{report}"
    )
    assert (
        signalized_control_summary["signal_clearance_duration"] == signal_params["deltat"]
    ), f"signal clearance duration mismatch\n{report}"
    assert (
        signalized_results["total_vehicles"]
        == fcfs_results["total_vehicles"]
        == batch_results["total_vehicles"]
    ), f"total vehicles differ\n{report}"
    assert demand_summary["origin_sequence"] == [
        plan["origin"] for plan in vehicle_plans
    ], f"origin sequence mismatch\n{report}"
    assert demand_summary["destination_sequence"] == [
        plan["destination"] for plan in vehicle_plans
    ], f"destination sequence mismatch\n{report}"
    assert demand_summary["departure_time_sequence"] == [
        plan["departure_time"] for plan in vehicle_plans
    ], f"departure_time sequence mismatch\n{report}"
    assert demand_summary["origin_grid_coord_sequence"] == [
        plan["origin_grid_coord"] for plan in vehicle_plans
    ], f"origin_grid_coord sequence mismatch\n{report}"
    assert demand_summary["destination_grid_coord_sequence"] == [
        plan["destination_grid_coord"] for plan in vehicle_plans
    ], f"destination_grid_coord sequence mismatch\n{report}"
    assert demand_summary["manhattan_distance_sequence"] == [
        plan["manhattan_distance"] for plan in vehicle_plans
    ], f"manhattan_distance sequence mismatch\n{report}"
    assert demand_summary["first_departure_time"] == departure_start, (
        f"first departure time mismatch\n{report}"
    )
    assert demand_summary["last_departure_time"] == departure_end, (
        f"last departure time mismatch\n{report}"
    )
    assert demand_summary["demand_duration"] == departure_end - departure_start, (
        f"demand duration mismatch\n{report}"
    )
    assert len(fcfs_eligible) >= MIN_ELIGIBLE_NODES, (
        f"fcfs eligible node count too small\n{report}"
    )
    assert len(batch_eligible) >= MIN_ELIGIBLE_NODES, (
        f"batch eligible node count too small\n{report}"
    )
    assert fcfs_eligible == batch_eligible, (
        f"fcfs and batch eligible node sets differ\n{report}"
    )
    assert signalized_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"signalized all-red completed ratio too low\n{report}"
    )
    assert fcfs_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"fcfs completed ratio too low\n{report}"
    )
    assert batch_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"batch completed ratio too low\n{report}"
    )
    assert (
        fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * signalized_results["completed_ratio"]
    ), f"fcfs completed ratio extremely worse than signalized all-red\n{report}"
    assert (
        batch_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * signalized_results["completed_ratio"]
    ), f"batch completed ratio extremely worse than signalized all-red\n{report}"
    assert fcfs_avg_tt_ratio is not None, (
        f"fcfs average travel time ratio unavailable\n{report}"
    )
    assert _ratio_within_range(
        fcfs_avg_tt_ratio, TRAVEL_TIME_RATIO_MIN, TRAVEL_TIME_RATIO_MAX
    ), f"fcfs average travel time ratio out of range\n{report}"
    assert batch_avg_tt_ratio is not None, (
        f"batch average travel time ratio unavailable\n{report}"
    )
    assert _ratio_within_range(
        batch_avg_tt_ratio, TRAVEL_TIME_RATIO_MIN, TRAVEL_TIME_RATIO_MAX
    ), f"batch average travel time ratio out of range\n{report}"
    assert fcfs_total_tt_ratio is not None, (
        f"fcfs total travel time ratio unavailable\n{report}"
    )
    assert _ratio_within_range(
        fcfs_total_tt_ratio,
        TOTAL_TRAVEL_TIME_RATIO_MIN,
        TOTAL_TRAVEL_TIME_RATIO_MAX,
    ), f"fcfs total travel time ratio out of range\n{report}"
    assert batch_total_tt_ratio is not None, (
        f"batch total travel time ratio unavailable\n{report}"
    )
    assert _ratio_within_range(
        batch_total_tt_ratio,
        TOTAL_TRAVEL_TIME_RATIO_MIN,
        TOTAL_TRAVEL_TIME_RATIO_MAX,
    ), f"batch total travel time ratio out of range\n{report}"
    assert fcfs_dist_ratio is not None, (
        f"fcfs total distance traveled ratio unavailable\n{report}"
    )
    assert _ratio_within_range(
        fcfs_dist_ratio, DISTANCE_RATIO_MIN, DISTANCE_RATIO_MAX
    ), f"fcfs total distance traveled ratio out of range\n{report}"
    assert batch_dist_ratio is not None, (
        f"batch total distance traveled ratio unavailable\n{report}"
    )
    assert _ratio_within_range(
        batch_dist_ratio, DISTANCE_RATIO_MIN, DISTANCE_RATIO_MAX
    ), f"batch total distance traveled ratio out of range\n{report}"
    assert fcfs_W.order_control_clearance_timesteps == FCFS_CLEARANCE_TIMESTEPS, (
        f"fcfs clearance_timesteps is not 1\n{report}"
    )
    assert order_control_clearance_timesteps == FCFS_CLEARANCE_TIMESTEPS, (
        f"batch clearance_timesteps is not 1\n{report}"
    )

    return {
        "case_name": case_name,
        "demand_summary": demand_summary,
        "signalized_control_summary": signalized_control_summary,
        "grid_network_summary": grid_network_summary,
        "signalized_results": signalized_results,
        "fcfs_results": fcfs_results,
        "batch_results": batch_results,
        "signalized_unfinished": signalized_unfinished,
        "fcfs_unfinished": fcfs_unfinished,
        "batch_unfinished": batch_unfinished,
        "signalized_completion": signalized_completion,
        "fcfs_completion": fcfs_completion,
        "batch_completion": batch_completion,
        "fcfs_vs_signalized_ratios": fcfs_vs_signalized_ratios,
        "batch_vs_signalized_ratios": batch_vs_signalized_ratios,
        "batch_vs_fcfs_ratios": batch_vs_fcfs_ratios,
        "batch_vs_fcfs_differences": batch_vs_fcfs_differences,
        "batch_vs_fcfs_travel_time_interpretation": batch_vs_fcfs_travel_time_interpretation,
        "fcfs_eligible_node_names": fcfs_eligible,
        "batch_eligible_node_names": batch_eligible,
        "order_control_clearance_timesteps": order_control_clearance_timesteps,
        "sanity_checks": sanity_checks,
    }


def test_batch_level1_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand():
    for case in HIGH_DEMAND_CASES:
        _run_high_demand_case(case)

    print(
        "BATCH Level 1 vs FCFS clearance=1 vs signalized UXsim all-red grid high-demand test passed."
    )


if __name__ == "__main__":
    test_batch_level1_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand()
