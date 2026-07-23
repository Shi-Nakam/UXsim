# Grid-network comparison: UXsim standard vs FCFS(clearance=0) vs
# Level 1 BATCH(clearance=0, batch_size=10) on a 6x6 grid.
#
# Extends the existing FCFS vs UXsim standard grid-network sanity check by
# adding BATCH as a third control mode on the same network, demand, and seeds.
# Uses 1,000 vehicles with multiple routes and turns. Reports traffic results
# for all three modes and compares BATCH with FCFS, especially average travel
# time. BATCH <= FCFS is NOT an assertion pass/fail condition; performance
# is left for human review.
#
# Level 1 BATCH here is a provisional comparison before Level 2 is implemented.
# The research design target is Level 2, with fallback to Level 1 and then
# Level 0 when needed. This test does not claim Level 1 as the final setting.
#
# Run from the repository root:
#   python tests_order_control_batch_vs_fcfs_vs_uxsim_standard_grid_network.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import random

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
MIN_ELIGIBLE_NODES = 25
NUM_VEHICLES = 1000
DEPARTURE_START = 0
DEPARTURE_END = 500
MIN_OD_MANHATTAN_DISTANCE = 5
TMAX = 5000
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
BATCH_SIZE = 10
BATCH_T_TRIGGER_LEVEL = 1

COMPLETED_RATIO_MIN = 0.5
FCFS_COMPLETED_RATIO_FACTOR = 0.5
TRAVEL_TIME_RATIO_MIN = 0.25
TRAVEL_TIME_RATIO_MAX = 4.0
TOTAL_TRAVEL_TIME_RATIO_MIN = 0.25
TOTAL_TRAVEL_TIME_RATIO_MAX = 4.0
DISTANCE_RATIO_MIN = 0.4
DISTANCE_RATIO_MAX = 1.6

APPROX_EQUAL_AVG_TRAVEL_TIME_TOLERANCE = 0.05


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


def _generate_vehicle_plans():
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    vehicle_index = 0
    while len(plans) < NUM_VEHICLES:
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

        departure_time = DEPARTURE_START + (DEPARTURE_END - DEPARTURE_START) * len(
            plans
        ) / max(NUM_VEHICLES - 1, 1)
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


def _demand_summary(vehicle_plans):
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


def _add_grid_network(W):
    spacing = 1.0
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            W.addNode(
                f"g_{row}_{column}",
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

    def add_link(link_name, start_node, end_node, length):
        W.addLink(
            link_name,
            start_node,
            end_node,
            length=length,
            free_flow_speed=FREE_FLOW_SPEED,
            number_of_lanes=NUMBER_OF_LANES,
            merge_priority=MERGE_PRIORITY,
        )

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = f"g_{row}_{column}"
            right_node = f"g_{row}_{column + 1}"
            add_link(
                f"h_{row}_{column}_{column + 1}",
                left_node,
                right_node,
                INTERNAL_LINK_LENGTH,
            )
            add_link(
                f"h_{row}_{column + 1}_{column}",
                right_node,
                left_node,
                INTERNAL_LINK_LENGTH,
            )

    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = f"g_{row}_{column}"
            lower_node = f"g_{row + 1}_{column}"
            add_link(
                f"v_{row}_{row + 1}_{column}",
                upper_node,
                lower_node,
                INTERNAL_LINK_LENGTH,
            )
            add_link(
                f"v_{row + 1}_{row}_{column}",
                lower_node,
                upper_node,
                INTERNAL_LINK_LENGTH,
            )

    for column in range(GRID_SIZE):
        add_link(
            f"top_{column}_to_g_0_{column}",
            f"top_{column}",
            f"g_0_{column}",
            OD_CONNECTOR_LENGTH,
        )
        add_link(
            f"g_0_{column}_to_top_{column}",
            f"g_0_{column}",
            f"top_{column}",
            OD_CONNECTOR_LENGTH,
        )
        add_link(
            f"bottom_{column}_to_g_5_{column}",
            f"bottom_{column}",
            f"g_{GRID_SIZE - 1}_{column}",
            OD_CONNECTOR_LENGTH,
        )
        add_link(
            f"g_5_{column}_to_bottom_{column}",
            f"g_{GRID_SIZE - 1}_{column}",
            f"bottom_{column}",
            OD_CONNECTOR_LENGTH,
        )

    for row in range(GRID_SIZE):
        add_link(
            f"left_{row}_to_g_{row}_0",
            f"left_{row}",
            f"g_{row}_0",
            OD_CONNECTOR_LENGTH,
        )
        add_link(
            f"g_{row}_0_to_left_{row}",
            f"g_{row}_0",
            f"left_{row}",
            OD_CONNECTOR_LENGTH,
        )
        add_link(
            f"right_{row}_to_g_{row}_5",
            f"right_{row}",
            f"g_{row}_{GRID_SIZE - 1}",
            OD_CONNECTOR_LENGTH,
        )
        add_link(
            f"g_{row}_5_to_right_{row}",
            f"g_{row}_{GRID_SIZE - 1}",
            f"right_{row}",
            OD_CONNECTOR_LENGTH,
        )


def _grid_network_summary(W):
    internal_grid_node_count = GRID_SIZE * GRID_SIZE
    external_od_node_count = len(EXTERNAL_OD_NODES)
    return {
        "grid_size": GRID_SIZE,
        "internal_grid_node_count": internal_grid_node_count,
        "external_od_node_count": external_od_node_count,
        "total_node_count": len(W.NODES),
        "total_link_count": len(W.LINKS),
        "bidirectional_internal_links": True,
        "bidirectional_od_connector_links": True,
        "merge_priority": MERGE_PRIORITY,
        "number_of_lanes": NUMBER_OF_LANES,
    }


def _collect_standard_control_summary(W):
    signalized_nodes = []
    signal_parameters = {}
    for node in W.NODES:
        signal = getattr(node, "signal", None)
        if signal is None:
            continue
        if signal != [0]:
            signalized_nodes.append(node.name)
            signal_parameters[node.name] = {
                "signal": list(signal),
                "signal_offset": getattr(node, "signal_offset", None),
                "cycle_length": getattr(node, "cycle_length", None),
            }

    if signalized_nodes:
        default_signal_detected = "partial (some nodes have non-default signal)"
        note = (
            "UXsim standard transfer with existing default or API-based signal "
            "configuration detected on one or more nodes"
        )
    else:
        default_signal_detected = "yes (all nodes use signal=[0], no signal control)"
        note = "UXsim standard transfer without explicit signal configuration"

    return {
        "standard_control_type_used": (
            "UXsim standard Node.transfer "
            "(order_control_type='none', set_order_control_for_nodes not called)"
        ),
        "explicit_signal_settings_used": "no",
        "default_signal_settings_detected": default_signal_detected,
        "signalized_node_count": len(signalized_nodes),
        "signalized_node_names": signalized_nodes,
        "signal_parameters": signal_parameters if signal_parameters else "not available",
        "note": note,
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
        if node.order_control_clearance_timesteps != 0:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, expected 0"
            )


def build_world(control_mode, vehicle_plans):
    W = World(
        name=f"batch_fcfs_standard_grid_{control_mode}",
        deltan=1,
        tmax=TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_grid_network(W)
    _add_vehicles(W, vehicle_plans)

    eligible_node_names = []
    if control_mode == "fcfs":
        W.infer_order_control_eligible_nodes()
        W.set_order_control_clearance_timesteps(0)
        eligible_node_names = _eligible_node_names(W)
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="fcfs",
        )
    elif control_mode == "batch":
        W.infer_order_control_eligible_nodes()
        W.set_order_control_clearance_timesteps(0)
        eligible_node_names = _eligible_node_names(W)
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="batch",
            batch_size=BATCH_SIZE,
            order_control_batch_t_trigger_level=BATCH_T_TRIGGER_LEVEL,
        )
        _verify_batch_node_settings(W, eligible_node_names)
    elif control_mode == "standard":
        pass
    else:
        raise ValueError(f"unsupported control_mode: {control_mode!r}")

    W.exec_simulation()
    return W, eligible_node_names


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


def _batch_vs_fcfs_differences(batch_results, fcfs_results):
    return {
        "average_travel_time_difference": (
            batch_results["average_travel_time"] - fcfs_results["average_travel_time"]
        ),
        "total_travel_time_difference": (
            batch_results["total_travel_time"] - fcfs_results["total_travel_time"]
        ),
        "average_delay_difference": (
            batch_results["average_delay"] - fcfs_results["average_delay"]
        ),
        "completed_trips_difference": (
            batch_results["completed_trips"] - fcfs_results["completed_trips"]
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


def _format_standard_control_summary(summary):
    signal_names_text = (
        summary["signalized_node_names"]
        if summary["signalized_node_names"]
        else "none"
    )
    return (
        "Standard control summary:\n"
        f"- standard control type used: {summary['standard_control_type_used']}\n"
        f"- explicit signal settings used: {summary['explicit_signal_settings_used']}\n"
        f"- default signal settings detected: {summary['default_signal_settings_detected']}\n"
        f"- signalized node count: {summary['signalized_node_count']}\n"
        f"- signalized node names: {signal_names_text}\n"
        f"- signal parameters: {summary['signal_parameters']}\n"
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
        f"- total vehicles: {summary['total_vehicles']}\n"
        f"- first departure time: {summary['first_departure_time']}\n"
        f"- last departure time: {summary['last_departure_time']}\n"
        f"- demand duration: {summary['demand_duration']}\n"
        f"- average departure interval: {summary['average_departure_interval']}\n"
        f"- vehicles per timestep: {summary['vehicles_per_timestep']}\n"
        f"- minimum OD manhattan distance: {summary['minimum_od_manhattan_distance']}\n"
        f"- average OD manhattan distance: {summary['average_od_manhattan_distance']}\n"
        f"- maximum OD manhattan distance: {summary['maximum_od_manhattan_distance']}"
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


def _format_ratio_block(title, ratios):
    return (
        f"{title}:\n"
        f"- completed ratio difference: {ratios['completed_ratio_difference']:.3f}\n"
        f"- average travel time ratio: {ratios['average_travel_time_ratio']}\n"
        f"- total travel time ratio: {ratios['total_travel_time_ratio']}\n"
        f"- total distance traveled ratio: {ratios['total_distance_traveled_ratio']}"
    )


def _format_difference_block(title, differences):
    return (
        f"{title}:\n"
        f"- average travel time difference (batch - fcfs): "
        f"{differences['average_travel_time_difference']:.3f} s\n"
        f"- total travel time difference (batch - fcfs): "
        f"{differences['total_travel_time_difference']:.1f} s\n"
        f"- average delay difference (batch - fcfs): "
        f"{differences['average_delay_difference']:.3f} s\n"
        f"- completed trips difference (batch - fcfs): "
        f"{differences['completed_trips_difference']}"
    )


def _build_report_context(
    *,
    standard_control_summary,
    grid_network_summary,
    demand_summary,
    standard_results,
    fcfs_results,
    batch_results,
    fcfs_eligible_node_names,
    batch_eligible_node_names,
    fcfs_vs_standard_ratios,
    batch_vs_standard_ratios,
    batch_vs_fcfs_ratios,
    batch_vs_fcfs_differences,
    batch_vs_fcfs_travel_time_interpretation,
    sanity_checks,
):
    eligible_match = fcfs_eligible_node_names == batch_eligible_node_names
    return (
        f"{_format_standard_control_summary(standard_control_summary)}\n\n"
        f"{_format_grid_network_summary(grid_network_summary)}\n\n"
        f"{_format_demand_summary(demand_summary)}\n\n"
        f"{_format_results('UXsim standard results', standard_results)}\n\n"
        f"{_format_results('FCFS clearance=0 results', fcfs_results)}\n\n"
        f"{_format_results('BATCH Level 1, clearance=0, batch_size=10 results', batch_results)}\n\n"
        f"{_format_ratio_block('Comparison ratios (FCFS / UXsim standard)', fcfs_vs_standard_ratios)}\n\n"
        f"{_format_ratio_block('Comparison ratios (BATCH / UXsim standard)', batch_vs_standard_ratios)}\n\n"
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
        "Sanity checks:\n"
        + "\n".join(f"- {name}: {status}" for name, status in sanity_checks.items())
    )


def _ratio_within_range(ratio, minimum, maximum):
    return ratio is not None and minimum <= ratio <= maximum


def test_batch_level1_clearance_zero_vs_fcfs_vs_uxsim_standard_grid_network():
    vehicle_plans = _generate_vehicle_plans()
    demand_summary = _demand_summary(vehicle_plans)

    standard_W, _ = build_world("standard", vehicle_plans)
    standard_control_summary = _collect_standard_control_summary(standard_W)
    grid_network_summary = _grid_network_summary(standard_W)
    standard_results = _collect_traffic_results(standard_W)

    fcfs_W, fcfs_eligible = build_world("fcfs", vehicle_plans)
    fcfs_results = _collect_traffic_results(fcfs_W)

    batch_W, batch_eligible = build_world("batch", vehicle_plans)
    batch_results = _collect_traffic_results(batch_W)

    fcfs_vs_standard_ratios = _comparison_ratios(fcfs_results, standard_results)
    batch_vs_standard_ratios = _comparison_ratios(batch_results, standard_results)
    batch_vs_fcfs_ratios = _comparison_ratios(batch_results, fcfs_results)
    batch_vs_fcfs_differences = _batch_vs_fcfs_differences(batch_results, fcfs_results)
    batch_vs_fcfs_travel_time_interpretation = _batch_vs_fcfs_travel_time_interpretation(
        batch_results,
        fcfs_results,
    )

    sanity_checks = {}

    sanity_checks["total vehicles equal (standard/fcfs/batch)"] = (
        "pass"
        if standard_results["total_vehicles"]
        == fcfs_results["total_vehicles"]
        == batch_results["total_vehicles"]
        else "fail"
    )
    sanity_checks["demand summary equal"] = (
        "pass"
        if demand_summary["total_vehicles"] == NUM_VEHICLES
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
    sanity_checks["first departure time matches DEPARTURE_START"] = (
        "pass"
        if demand_summary["first_departure_time"] == DEPARTURE_START
        else "fail"
    )
    sanity_checks["last departure time matches DEPARTURE_END"] = (
        "pass"
        if demand_summary["last_departure_time"] == DEPARTURE_END
        else "fail"
    )
    sanity_checks["demand duration matches existing value"] = (
        "pass"
        if demand_summary["demand_duration"] == DEPARTURE_END - DEPARTURE_START
        else "fail"
    )
    sanity_checks["minimum OD manhattan distance >= threshold"] = (
        "pass"
        if demand_summary["minimum_od_manhattan_distance"] >= MIN_OD_MANHATTAN_DISTANCE
        else "fail"
    )
    sanity_checks["fcfs eligible node count >= 25"] = (
        "pass" if len(fcfs_eligible) >= MIN_ELIGIBLE_NODES else "fail"
    )
    sanity_checks["batch eligible node count >= 25"] = (
        "pass" if len(batch_eligible) >= MIN_ELIGIBLE_NODES else "fail"
    )
    sanity_checks["fcfs and batch eligible node sets match"] = (
        "pass" if fcfs_eligible == batch_eligible else "fail"
    )
    sanity_checks["standard completed ratio >= threshold"] = (
        "pass"
        if standard_results["completed_ratio"] >= COMPLETED_RATIO_MIN
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
    sanity_checks["fcfs completed ratio not extremely worse than standard"] = (
        "pass"
        if fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * standard_results["completed_ratio"]
        else "fail"
    )
    sanity_checks["batch completed ratio not extremely worse than standard"] = (
        "pass"
        if batch_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * standard_results["completed_ratio"]
        else "fail"
    )

    fcfs_avg_tt_ratio = fcfs_vs_standard_ratios["average_travel_time_ratio"]
    sanity_checks["fcfs average travel time ratio (fcfs/standard) within range"] = (
        "pass"
        if _ratio_within_range(fcfs_avg_tt_ratio, TRAVEL_TIME_RATIO_MIN, TRAVEL_TIME_RATIO_MAX)
        else "fail"
    )

    batch_avg_tt_ratio = batch_vs_standard_ratios["average_travel_time_ratio"]
    sanity_checks["batch average travel time ratio (batch/standard) within range"] = (
        "pass"
        if _ratio_within_range(batch_avg_tt_ratio, TRAVEL_TIME_RATIO_MIN, TRAVEL_TIME_RATIO_MAX)
        else "fail"
    )

    fcfs_total_tt_ratio = fcfs_vs_standard_ratios["total_travel_time_ratio"]
    sanity_checks["fcfs total travel time ratio (fcfs/standard) within range"] = (
        "pass"
        if _ratio_within_range(
            fcfs_total_tt_ratio,
            TOTAL_TRAVEL_TIME_RATIO_MIN,
            TOTAL_TRAVEL_TIME_RATIO_MAX,
        )
        else "fail"
    )

    batch_total_tt_ratio = batch_vs_standard_ratios["total_travel_time_ratio"]
    sanity_checks["batch total travel time ratio (batch/standard) within range"] = (
        "pass"
        if _ratio_within_range(
            batch_total_tt_ratio,
            TOTAL_TRAVEL_TIME_RATIO_MIN,
            TOTAL_TRAVEL_TIME_RATIO_MAX,
        )
        else "fail"
    )

    fcfs_dist_ratio = fcfs_vs_standard_ratios["total_distance_traveled_ratio"]
    sanity_checks["fcfs total distance traveled ratio (fcfs/standard) within range"] = (
        "pass"
        if _ratio_within_range(fcfs_dist_ratio, DISTANCE_RATIO_MIN, DISTANCE_RATIO_MAX)
        else "fail"
    )

    batch_dist_ratio = batch_vs_standard_ratios["total_distance_traveled_ratio"]
    sanity_checks["batch total distance traveled ratio (batch/standard) within range"] = (
        "pass"
        if _ratio_within_range(batch_dist_ratio, DISTANCE_RATIO_MIN, DISTANCE_RATIO_MAX)
        else "fail"
    )

    report = _build_report_context(
        standard_control_summary=standard_control_summary,
        grid_network_summary=grid_network_summary,
        demand_summary=demand_summary,
        standard_results=standard_results,
        fcfs_results=fcfs_results,
        batch_results=batch_results,
        fcfs_eligible_node_names=fcfs_eligible,
        batch_eligible_node_names=batch_eligible,
        fcfs_vs_standard_ratios=fcfs_vs_standard_ratios,
        batch_vs_standard_ratios=batch_vs_standard_ratios,
        batch_vs_fcfs_ratios=batch_vs_fcfs_ratios,
        batch_vs_fcfs_differences=batch_vs_fcfs_differences,
        batch_vs_fcfs_travel_time_interpretation=batch_vs_fcfs_travel_time_interpretation,
        sanity_checks=sanity_checks,
    )
    print(report)

    assert (
        standard_results["total_vehicles"]
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
    assert demand_summary["first_departure_time"] == DEPARTURE_START, (
        f"first departure time mismatch\n{report}"
    )
    assert demand_summary["last_departure_time"] == DEPARTURE_END, (
        f"last departure time mismatch\n{report}"
    )
    assert demand_summary["demand_duration"] == DEPARTURE_END - DEPARTURE_START, (
        f"demand duration mismatch\n{report}"
    )
    assert (
        demand_summary["minimum_od_manhattan_distance"] >= MIN_OD_MANHATTAN_DISTANCE
    ), f"minimum OD manhattan distance too small\n{report}"
    assert len(fcfs_eligible) >= MIN_ELIGIBLE_NODES, (
        f"fcfs eligible node count too small\n{report}"
    )
    assert len(batch_eligible) >= MIN_ELIGIBLE_NODES, (
        f"batch eligible node count too small\n{report}"
    )
    assert fcfs_eligible == batch_eligible, (
        f"fcfs and batch eligible node sets differ\n{report}"
    )
    assert standard_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"standard completed ratio too low\n{report}"
    )
    assert fcfs_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"fcfs completed ratio too low\n{report}"
    )
    assert batch_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"batch completed ratio too low\n{report}"
    )
    assert (
        fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * standard_results["completed_ratio"]
    ), f"fcfs completed ratio extremely worse than standard\n{report}"
    assert (
        batch_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * standard_results["completed_ratio"]
    ), f"batch completed ratio extremely worse than standard\n{report}"

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

    print(
        "BATCH Level 1 vs FCFS clearance=0 vs UXsim standard grid network test passed."
    )


if __name__ == "__main__":
    test_batch_level1_clearance_zero_vs_fcfs_vs_uxsim_standard_grid_network()
