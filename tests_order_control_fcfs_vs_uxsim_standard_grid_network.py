# Sanity check: UXsim standard vs FCFS(clearance=0) on a grid/mesh network.
#
# This is NOT a research performance comparison. It checks that FCFS(clearance=0)
# does not cause extreme divergence from standard UXsim behavior on a 6x6 grid with
# ~1000 vehicles, where multiple routes and UXsim route choice may apply.
#
# Run from the repository root:
#   python tests_order_control_fcfs_vs_uxsim_standard_grid_network.py
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

COMPLETED_RATIO_MIN = 0.5
FCFS_COMPLETED_RATIO_FACTOR = 0.5
TRAVEL_TIME_RATIO_MIN = 0.25
TRAVEL_TIME_RATIO_MAX = 4.0
TOTAL_TRAVEL_TIME_RATIO_MIN = 0.25
TOTAL_TRAVEL_TIME_RATIO_MAX = 4.0
DISTANCE_RATIO_MIN = 0.4
DISTANCE_RATIO_MAX = 1.6


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


def build_world(control_mode, vehicle_plans):
    W = World(
        name=f"fcfs_vs_standard_grid_{control_mode}",
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
        eligible_node_names = [
            node.name for node in W.NODES if node.order_control_eligible
        ]
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="fcfs",
        )

    W.exec_simulation()
    return W, eligible_node_names


def _safe_ratio(numerator, denominator):
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


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


def _build_report_context(
    *,
    standard_control_summary,
    grid_network_summary,
    demand_summary,
    standard_results,
    fcfs_results,
    eligible_node_names,
    comparison_ratios,
    sanity_checks,
):
    return (
        f"{_format_standard_control_summary(standard_control_summary)}\n\n"
        f"{_format_grid_network_summary(grid_network_summary)}\n\n"
        f"{_format_demand_summary(demand_summary)}\n\n"
        f"{_format_results('UXsim standard results', standard_results)}\n\n"
        f"{_format_results('FCFS clearance=0 results', fcfs_results)}\n\n"
        "Comparison ratios:\n"
        f"- completed ratio difference: {comparison_ratios['completed_ratio_difference']:.3f}\n"
        f"- average travel time ratio (fcfs / standard): {comparison_ratios['average_travel_time_ratio']}\n"
        f"- total travel time ratio (fcfs / standard): {comparison_ratios['total_travel_time_ratio']}\n"
        f"- total distance traveled ratio (fcfs / standard): {comparison_ratios['total_distance_traveled_ratio']}\n\n"
        "Eligible FCFS nodes:\n"
        f"- count: {len(eligible_node_names)}\n"
        f"- names: {eligible_node_names}\n\n"
        "Sanity checks:\n"
        + "\n".join(f"- {name}: {status}" for name, status in sanity_checks.items())
    )


def test_fcfs_clearance_zero_vs_uxsim_standard_grid_network():
    vehicle_plans = _generate_vehicle_plans()
    demand_summary = _demand_summary(vehicle_plans)

    standard_W, _ = build_world("standard", vehicle_plans)
    standard_control_summary = _collect_standard_control_summary(standard_W)
    grid_network_summary = _grid_network_summary(standard_W)
    standard_results = _collect_traffic_results(standard_W)

    fcfs_W, fcfs_eligible = build_world("fcfs", vehicle_plans)
    fcfs_results = _collect_traffic_results(fcfs_W)

    comparison_ratios = {
        "completed_ratio_difference": (
            fcfs_results["completed_ratio"] - standard_results["completed_ratio"]
        ),
        "average_travel_time_ratio": _safe_ratio(
            fcfs_results["average_travel_time"],
            standard_results["average_travel_time"],
        ),
        "total_travel_time_ratio": _safe_ratio(
            fcfs_results["total_travel_time"],
            standard_results["total_travel_time"],
        ),
        "total_distance_traveled_ratio": _safe_ratio(
            fcfs_results["total_distance_traveled"],
            standard_results["total_distance_traveled"],
        ),
    }

    sanity_checks = {}

    sanity_checks["total vehicles equal"] = (
        "pass"
        if standard_results["total_vehicles"] == fcfs_results["total_vehicles"]
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
    sanity_checks["eligible node count >= 25"] = (
        "pass" if len(fcfs_eligible) >= MIN_ELIGIBLE_NODES else "fail"
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
    sanity_checks["completed ratio not extremely worse"] = (
        "pass"
        if fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * standard_results["completed_ratio"]
        else "fail"
    )

    avg_tt_ratio = comparison_ratios["average_travel_time_ratio"]
    sanity_checks["average travel time ratio within range"] = (
        "pass"
        if avg_tt_ratio is not None
        and TRAVEL_TIME_RATIO_MIN <= avg_tt_ratio <= TRAVEL_TIME_RATIO_MAX
        else "fail"
    )

    total_tt_ratio = comparison_ratios["total_travel_time_ratio"]
    sanity_checks["total travel time ratio within range"] = (
        "pass"
        if total_tt_ratio is not None
        and TOTAL_TRAVEL_TIME_RATIO_MIN <= total_tt_ratio <= TOTAL_TRAVEL_TIME_RATIO_MAX
        else "fail"
    )

    dist_ratio = comparison_ratios["total_distance_traveled_ratio"]
    sanity_checks["total distance traveled ratio within range"] = (
        "pass"
        if dist_ratio is not None
        and DISTANCE_RATIO_MIN <= dist_ratio <= DISTANCE_RATIO_MAX
        else "fail"
    )

    report = _build_report_context(
        standard_control_summary=standard_control_summary,
        grid_network_summary=grid_network_summary,
        demand_summary=demand_summary,
        standard_results=standard_results,
        fcfs_results=fcfs_results,
        eligible_node_names=fcfs_eligible,
        comparison_ratios=comparison_ratios,
        sanity_checks=sanity_checks,
    )
    print(report)

    assert standard_results["total_vehicles"] == fcfs_results["total_vehicles"], (
        f"total vehicles differ\n{report}"
    )
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
    assert len(fcfs_eligible) >= MIN_ELIGIBLE_NODES, (
        f"eligible node count too small\n{report}"
    )
    assert standard_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"standard completed ratio too low\n{report}"
    )
    assert fcfs_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"fcfs completed ratio too low\n{report}"
    )
    assert (
        fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * standard_results["completed_ratio"]
    ), f"fcfs completed ratio extremely worse than standard\n{report}"
    assert avg_tt_ratio is not None, f"average travel time ratio unavailable\n{report}"
    assert TRAVEL_TIME_RATIO_MIN <= avg_tt_ratio <= TRAVEL_TIME_RATIO_MAX, (
        f"average travel time ratio out of range\n{report}"
    )
    assert total_tt_ratio is not None, f"total travel time ratio unavailable\n{report}"
    assert (
        TOTAL_TRAVEL_TIME_RATIO_MIN <= total_tt_ratio <= TOTAL_TRAVEL_TIME_RATIO_MAX
    ), f"total travel time ratio out of range\n{report}"
    assert dist_ratio is not None, (
        f"total distance traveled ratio unavailable\n{report}"
    )
    assert DISTANCE_RATIO_MIN <= dist_ratio <= DISTANCE_RATIO_MAX, (
        f"total distance traveled ratio out of range\n{report}"
    )

    print("FCFS clearance=0 vs UXsim standard grid network test passed.")


if __name__ == "__main__":
    test_fcfs_clearance_zero_vs_uxsim_standard_grid_network()
