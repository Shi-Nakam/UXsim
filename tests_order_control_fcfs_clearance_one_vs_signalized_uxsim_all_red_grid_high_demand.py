# Sanity check: signalized UXsim standard with all-red clearance vs FCFS(clearance=1)
# on a grid/mesh network under high demand (5000 and 10000 vehicles).
#
# This is NOT a research performance comparison. It checks that FCFS(clearance=1)
# does not break down under high demand and compares periodic signal control with
# all-red clearance against arrival-order FCFS with clearance_timesteps=1.
#
# Run from the repository root:
#   python tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand.py
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
            # In the current uxsim.py implementation, veh.arrival_time is stored as a
            # timestep index, while veh.travel_time is already in seconds. Convert
            # arrival_time to seconds here for the completion-time summary.
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


def build_world(control_mode, vehicle_plans, tmax):
    W = World(
        name=f"fcfs_clearance_one_vs_signalized_all_red_{control_mode}",
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
        eligible_node_names = [
            node.name for node in W.NODES if node.order_control_eligible
        ]
        assert len(eligible_node_names) >= MIN_ELIGIBLE_NODES
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="fcfs",
        )

    W.exec_simulation()
    return W, eligible_node_names, signal_params


def _safe_ratio(numerator, denominator):
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


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


def _build_report_context(
    *,
    case_name,
    signalized_control_summary,
    grid_network_summary,
    demand_summary,
    signalized_results,
    fcfs_results,
    signalized_unfinished,
    fcfs_unfinished,
    signalized_completion,
    fcfs_completion,
    eligible_node_names,
    fcfs_clearance_timesteps,
    comparison_ratios,
    sanity_checks,
):
    return (
        f"Case summary: {case_name}\n\n"
        f"{_format_signalized_all_red_control_summary(signalized_control_summary)}\n\n"
        f"{_format_grid_network_summary(grid_network_summary)}\n\n"
        f"{_format_demand_summary(demand_summary)}\n\n"
        f"{_format_results('Signalized UXsim standard with all-red clearance results', signalized_results)}\n\n"
        f"{_format_results('FCFS clearance=1 results', fcfs_results)}\n\n"
        f"{_format_unfinished_summary('Signalized UXsim standard with all-red unfinished vehicle summary', signalized_unfinished)}\n\n"
        f"{_format_unfinished_summary('FCFS clearance=1 unfinished vehicle summary', fcfs_unfinished)}\n\n"
        f"{_format_completion_time_summary('Signalized UXsim standard with all-red completion time summary', signalized_completion)}\n\n"
        f"{_format_completion_time_summary('FCFS clearance=1 completion time summary', fcfs_completion)}\n\n"
        "Comparison ratios:\n"
        f"- completed ratio difference: {comparison_ratios['completed_ratio_difference']:.3f}\n"
        f"- average travel time ratio (fcfs / signalized all-red): {comparison_ratios['average_travel_time_ratio']}\n"
        f"- total travel time ratio (fcfs / signalized all-red): {comparison_ratios['total_travel_time_ratio']}\n"
        f"- total distance traveled ratio (fcfs / signalized all-red): {comparison_ratios['total_distance_traveled_ratio']}\n\n"
        "Eligible FCFS nodes:\n"
        f"- count: {len(eligible_node_names)}\n"
        f"- names: {eligible_node_names}\n\n"
        f"FCFS clearance_timesteps: {fcfs_clearance_timesteps}\n\n"
        "Sanity checks:\n"
        + "\n".join(f"- {name}: {status}" for name, status in sanity_checks.items())
    )


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
    fcfs_clearance_timesteps = fcfs_W.order_control_clearance_timesteps

    comparison_ratios = {
        "completed_ratio_difference": (
            fcfs_results["completed_ratio"] - signalized_results["completed_ratio"]
        ),
        "average_travel_time_ratio": _safe_ratio(
            fcfs_results["average_travel_time"],
            signalized_results["average_travel_time"],
        ),
        "total_travel_time_ratio": _safe_ratio(
            fcfs_results["total_travel_time"],
            signalized_results["total_travel_time"],
        ),
        "total_distance_traveled_ratio": _safe_ratio(
            fcfs_results["total_distance_traveled"],
            signalized_results["total_distance_traveled"],
        ),
    }

    sanity_checks = {}

    sanity_checks["total vehicles equal"] = (
        "pass"
        if signalized_results["total_vehicles"] == fcfs_results["total_vehicles"]
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
    sanity_checks["eligible node count >= 32"] = (
        "pass" if len(fcfs_eligible) >= MIN_ELIGIBLE_NODES else "fail"
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
    sanity_checks["completed ratio not extremely worse"] = (
        "pass"
        if fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * signalized_results["completed_ratio"]
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
    sanity_checks["fcfs clearance_timesteps == 1"] = (
        "pass" if fcfs_clearance_timesteps == FCFS_CLEARANCE_TIMESTEPS else "fail"
    )

    report = _build_report_context(
        case_name=case_name,
        signalized_control_summary=signalized_control_summary,
        grid_network_summary=grid_network_summary,
        demand_summary=demand_summary,
        signalized_results=signalized_results,
        fcfs_results=fcfs_results,
        signalized_unfinished=signalized_unfinished,
        fcfs_unfinished=fcfs_unfinished,
        signalized_completion=signalized_completion,
        fcfs_completion=fcfs_completion,
        eligible_node_names=fcfs_eligible,
        fcfs_clearance_timesteps=fcfs_clearance_timesteps,
        comparison_ratios=comparison_ratios,
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
    assert signalized_results["total_vehicles"] == fcfs_results["total_vehicles"], (
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
        f"eligible node count too small\n{report}"
    )
    assert signalized_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"signalized all-red completed ratio too low\n{report}"
    )
    assert fcfs_results["completed_ratio"] >= COMPLETED_RATIO_MIN, (
        f"fcfs completed ratio too low\n{report}"
    )
    assert (
        fcfs_results["completed_ratio"]
        >= FCFS_COMPLETED_RATIO_FACTOR * signalized_results["completed_ratio"]
    ), f"fcfs completed ratio extremely worse than signalized all-red\n{report}"
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
    assert fcfs_clearance_timesteps == FCFS_CLEARANCE_TIMESTEPS, (
        f"fcfs clearance_timesteps is not 1\n{report}"
    )

    return {
        "case_name": case_name,
        "demand_summary": demand_summary,
        "signalized_control_summary": signalized_control_summary,
        "grid_network_summary": grid_network_summary,
        "signalized_results": signalized_results,
        "fcfs_results": fcfs_results,
        "signalized_unfinished": signalized_unfinished,
        "fcfs_unfinished": fcfs_unfinished,
        "signalized_completion": signalized_completion,
        "fcfs_completion": fcfs_completion,
        "comparison_ratios": comparison_ratios,
        "eligible_node_names": fcfs_eligible,
        "fcfs_clearance_timesteps": fcfs_clearance_timesteps,
        "sanity_checks": sanity_checks,
    }


def test_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand():
    for case in HIGH_DEMAND_CASES:
        _run_high_demand_case(case)

    print(
        "FCFS clearance=1 vs signalized UXsim all-red grid high-demand test passed."
    )


if __name__ == "__main__":
    test_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand()
