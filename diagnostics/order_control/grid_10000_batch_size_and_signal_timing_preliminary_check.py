# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Exploratory 10,000-vehicle 6x6 grid diagnostics before Level 2 design.
# NOT a formal sensitivity analysis or general theoretical proof.
#
# Modes include:
#   - default: P1–P4 (BATCH N=20 and signal timing exploration)
#   - size-one BATCH vs FCFS pre-fix bug investigation (legacy modes)
#   - strict post-fix size-one BATCH vs FCFS equivalence (commit 2b10b08+)
#   - post-fix BATCH N=10 / N=20 recheck with historical pre-fix comparison
#
# Signal phase mapping (same as Phase 4-6U clearance=1 diagnostic):
#   phase 0 / signal_group 0: east-west links
#   phase 1: no links assigned — all-red equivalent
#   phase 2 / signal_group 2: north-south links
#   phase 3: no links assigned — all-red equivalent
#
# Staggered offset uses existing cycle-length-based formula (no asymmetric offset tuning).
#
# Run from repository root:
#   python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py

import argparse
import random
import time

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = GRID_SIZE * GRID_SIZE
NUM_VEHICLES = 10000
DEPARTURE_START = 0
DEPARTURE_END = 500
TMAX = 50000
MIN_OD_MANHATTAN_DISTANCE = 5
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
FCFS_CLEARANCE_TIMESTEPS = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
BATCH_T_TRIGGER_LEVEL = 1
COMPLETED_RATIO_MIN = 0.5

# Phase 4-6U signal reference — comparison display only; not re-run by default.
REFERENCE_SIGNAL_60_1_60_1 = {
    "label": "reference signal [60,1,60,1]",
    "completed": 10000,
    "completed_ratio": 1.000,
    "total_travel_time": 26989929.0,
    "average_travel_time": 2699.0,
    "average_delay": 2534.1,
    "total_distance_traveled": 50367200.0,
    "unfinished": 0,
    "last_completed_trip_time": 5703.0,
}

REFERENCE_FCFS_CLEARANCE_1 = {
    "label": "reference FCFS clearance=1",
    "completed": 10000,
    "completed_ratio": 1.000,
    "total_travel_time": 33293441.0,
    "average_travel_time": 3329.3,
    "average_delay": 3164.4,
    "total_distance_traveled": 39892000.0,
    "unfinished": 0,
    "last_completed_trip_time": 6492.0,
}

# BATCH N=10 results before commit 2b10b08 (zero-service reformation fix).
# Pre-fix implementation without same-timestep additional formation after zero service.
# Historical comparison only — do NOT use as the current N=10 baseline.
REFERENCE_BATCH_N10_PRE_ZERO_SERVICE_FIX = {
    "label": "reference BATCH N=10 clearance=1 (pre zero-service fix)",
    "completed": 10000,
    "completed_ratio": 1.000,
    "total_travel_time": 30119206.0,
    "average_travel_time": 3011.9,
    "average_delay": 2847.0,
    "total_distance_traveled": 40996000.0,
    "unfinished": 0,
    "last_completed_trip_time": 5382.0,
}

# BATCH N=10 results after commit 2b10b08 (zero-service reformation fix).
# Current N=10 baseline for P1 comparison on post-fix code.
# average_travel_time is derived exactly from saved total_travel_time / NUM_VEHICLES.
# average_delay is omitted because the saved recheck stdout only had display precision.
REFERENCE_BATCH_N10_POST_ZERO_SERVICE_FIX = {
    "label": "reference BATCH N=10 clearance=1 (post zero-service fix)",
    "completed": 10000,
    "completed_ratio": 1.000,
    "total_travel_time": 27782978.0,
    "average_travel_time": 27782978.0 / NUM_VEHICLES,
    "total_distance_traveled": 39962400.0,
    "unfinished": 0,
    "last_completed_trip_time": 4971.0,
}

# P1 (BATCH N=20) results from the preliminary check run before zero-service
# reformation fix. Post-fix code reproduces the same aggregates (historical record).
REFERENCE_BATCH_N20_P1_PRE_FIX = {
    "label": "reference BATCH N=20 clearance=1 (P1 pre-fix)",
    "completed": 10000,
    "completed_ratio": 1.000,
    "total_travel_time": 35221107.0,
    "average_travel_time": 3522.1,
    "average_delay": 3357.2,
    "total_distance_traveled": 46560000.0,
    "unfinished": 0,
    "last_completed_trip_time": 6258.0,
}

EXPECTED_E0_N1_FIRST_LINK_DIFF = {
    "total_vehicles": 10000,
    "completed_trips": 10000,
    "total_travel_time": 33293441.0,
    "average_travel_time": 3329.3441,
    "average_delay": 3164.4481,
    "total_distance_traveled": 39892000.0,
    "unfinished_vehicle_count": 0,
    "last_completed_trip_time": 6492,
}

EXPECTED_E1_N1_FIRST_LINK_DIFF = {
    "total_vehicles": 10000,
    "completed_trips": 10000,
    "total_travel_time": 31915802.0,
    "average_travel_time": 3191.5802,
    "average_delay": 3026.6842,
    "total_distance_traveled": 38900000.0,
    "unfinished_vehicle_count": 0,
    "last_completed_trip_time": 6234,
}

N1_LOCAL_DIFF_TARGET_VEHICLE = "veh_3573"
N1_LOCAL_DIFF_TARGET_NODE = "g_3_4"
N1_LOCAL_DIFF_TARGET_INLINK = "h_3_3_4"
N1_LOCAL_DIFF_TARGET_OUTLINK = "h_3_4_5"
N1_LOCAL_DIFF_WINDOW_START = 1098
N1_LOCAL_DIFF_WINDOW_END = 1105
N1_LOCAL_DIFF_DETAIL_TIMESTEPS = (1102, 1103, 1104)

SIGNAL_OFFSET_STRATEGY = (
    "signal_offset = ((row + column) % 4) * (cycle_length / 4); "
    "cycle-length-based staggered offsets (not tuned for asymmetric green times)"
)

# Corrected signal setting for intended effective green 60 s / all-red 1 timestep.
# Under current UXsim discrete signal_control() (> comparison, update before transfer),
# setting [59,0,59,0] yields steady transfer phase lengths 60/1/60/1 (cycle 122 timesteps).
CORRECTED_SIGNAL_SETTING = [59, 0, 59, 0]
CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS = [60, 1, 60, 1]
CORRECTED_SIGNAL_EFFECTIVE_TRANSFER_CYCLE = 122
CORRECTED_SIGNAL_CASE_NAME = "S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1"
BATCH_N10_POST_FIX_AVG_DELAY_DISPLAY = 2613.4
OLD_SIGNAL_PRECISE_AVERAGE_TRAVEL_TIME = (
    REFERENCE_SIGNAL_60_1_60_1["total_travel_time"] / NUM_VEHICLES
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


def _compute_signal_params(W, green_ew, green_ns):
    signal_clearance_duration = W.DELTAT
    signal_setting = [
        green_ew,
        signal_clearance_duration,
        green_ns,
        signal_clearance_duration,
    ]
    cycle_length = sum(signal_setting)
    return {
        "deltat": W.DELTAT,
        "signal_clearance_duration": signal_clearance_duration,
        "signal_setting": signal_setting,
        "cycle_length": cycle_length,
        "green_ew": green_ew,
        "green_ns": green_ns,
    }


def _compute_explicit_signal_params(W, signal_setting):
    signal_setting = list(signal_setting)
    cycle_length = sum(signal_setting)
    return {
        "deltat": W.DELTAT,
        "signal_setting": signal_setting,
        "cycle_length": cycle_length,
        "green_ew": signal_setting[0],
        "green_ns": signal_setting[2],
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


def _add_grid_network(W, signal_params=None):
    spacing = 1.0
    signalize_internal = signal_params is not None

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
    total_distance_traveled = float(analyzer.total_distance_traveled)
    return {
        "completed_trips": completed_trips,
        "total_vehicles": total_trips,
        "completed_ratio": completed_ratio,
        "total_travel_time": total_travel_time,
        "average_travel_time": average_travel_time,
        "average_delay": average_delay,
        "total_distance_traveled": total_distance_traveled,
    }


def _collect_completion_time_summary(W, tmax):
    completed_arrival_times_seconds = []
    for veh in W.VEHICLES.values():
        if veh.arrival_time >= 0 and veh.travel_time >= 0:
            completed_arrival_times_seconds.append(veh.arrival_time * W.DELTAT)

    if not completed_arrival_times_seconds:
        return {
            "last_completed_trip_time": "not available",
            "unfinished_vehicle_count": len(W.VEHICLES),
        }

    last_completed_trip_time = max(completed_arrival_times_seconds)
    unfinished_vehicle_count = len(W.VEHICLES) - len(completed_arrival_times_seconds)
    return {
        "last_completed_trip_time": last_completed_trip_time,
        "unfinished_vehicle_count": unfinished_vehicle_count,
    }


def _eligible_node_names(W):
    return [node.name for node in W.NODES if node.order_control_eligible]


def _verify_batch_node_settings(W, eligible_node_names, batch_size):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "batch":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, expected 'batch'"
            )
        if node.batch_size != batch_size:
            raise AssertionError(
                f"node {name}: batch_size={node.batch_size}, expected {batch_size}"
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


def _verify_fcfs_node_settings(W, eligible_node_names):
    for name in eligible_node_names:
        node = W.get_node(name)
        if node.order_control_type != "fcfs":
            raise AssertionError(
                f"node {name}: order_control_type={node.order_control_type!r}, expected 'fcfs'"
            )
        if node.order_control_clearance_timesteps != FCFS_CLEARANCE_TIMESTEPS:
            raise AssertionError(
                f"node {name}: order_control_clearance_timesteps="
                f"{node.order_control_clearance_timesteps}, expected {FCFS_CLEARANCE_TIMESTEPS}"
            )


def _collect_signalized_control_summary(W, signal_params):
    signalized_internal_nodes = []
    signalized_od_nodes = []
    signal_offsets = {}
    expected_signal = signal_params["signal_setting"]
    for node in W.NODES:
        signal = getattr(node, "signal", None)
        if signal is None:
            continue
        if node.name in INTERNAL_GRID_NODES and signal != [0]:
            signalized_internal_nodes.append(node.name)
            signal_offsets[node.name] = getattr(node, "signal_offset", None)
            if signal != expected_signal:
                raise AssertionError(
                    f"node {node.name}: signal={signal}, expected {expected_signal}"
                )
        elif node.name in EXTERNAL_OD_NODES and signal != [0]:
            signalized_od_nodes.append(node.name)

    signal_group_counts = _count_links_by_signal_group(W)
    return {
        "signal_setting": expected_signal,
        "cycle_length": signal_params["cycle_length"],
        "signalized_internal_grid_node_count": len(signalized_internal_nodes),
        "signalized_od_node_count": len(signalized_od_nodes),
        "signal_group_1_link_count": signal_group_counts.get(1, 0),
        "signal_group_3_link_count": signal_group_counts.get(3, 0),
        "signal_offsets": signal_offsets,
    }


def build_batch_world(vehicle_plans, tmax, batch_size, run_simulation=True):
    W = World(
        name=f"preliminary_batch_n{batch_size}",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_grid_network(W)
    _add_vehicles(W, vehicle_plans)

    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(FCFS_CLEARANCE_TIMESTEPS)
    eligible_node_names = _eligible_node_names(W)
    W.set_order_control_for_nodes(
        eligible_node_names,
        order_control_type="batch",
        batch_size=batch_size,
        order_control_batch_t_trigger_level=BATCH_T_TRIGGER_LEVEL,
    )
    _verify_batch_node_settings(W, eligible_node_names, batch_size)

    if run_simulation:
        W.exec_simulation()
    return W, eligible_node_names


def build_fcfs_world(vehicle_plans, tmax, run_simulation=True):
    W = World(
        name="preliminary_fcfs_clearance_1",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_grid_network(W)
    _add_vehicles(W, vehicle_plans)

    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(FCFS_CLEARANCE_TIMESTEPS)
    eligible_node_names = _eligible_node_names(W)
    W.set_order_control_for_nodes(
        eligible_node_names,
        order_control_type="fcfs",
    )
    _verify_fcfs_node_settings(W, eligible_node_names)

    if run_simulation:
        W.exec_simulation()
    return W, eligible_node_names


def build_signalized_world(vehicle_plans, tmax, green_ew, green_ns):
    W = World(
        name=f"preliminary_signal_ew{green_ew}_ns{green_ns}",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    signal_params = _compute_signal_params(W, green_ew, green_ns)
    _add_grid_network(W, signal_params=signal_params)
    _add_vehicles(W, vehicle_plans)

    W.exec_simulation()
    return W, signal_params


def build_corrected_signalized_world(vehicle_plans, tmax, signal_setting):
    W = World(
        name="preliminary_corrected_signal",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    signal_params = _compute_explicit_signal_params(W, signal_setting)
    _add_grid_network(W, signal_params=signal_params)
    _add_vehicles(W, vehicle_plans)
    W.exec_simulation()
    return W, signal_params


def _build_signalized_network_only(signal_setting):
    W = World(
        name="signal_network_sanity",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    signal_params = _compute_explicit_signal_params(W, signal_setting)
    _add_grid_network(W, signal_params=signal_params)
    return W, signal_params


def _build_single_signal_node_world(signal_setting, signal_offset):
    W = World(
        name="signal_timing_sanity",
        deltan=1,
        tmax=500,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    node = W.addNode(
        "g_timing",
        0.0,
        0.0,
        signal=list(signal_setting),
        signal_offset=signal_offset,
    )
    return W, node


def _measure_real_node_transfer_phase_runs(node, max_steps=500):
    runs = []
    timeline = []
    current_phase = None
    current_length = 0
    for w_t in range(max_steps):
        pre_phase = node.signal_phase
        pre_t = node.signal_t
        node.update()
        post_phase = node.signal_phase
        post_t = node.signal_t
        transfer_phase = post_phase
        timeline.append((w_t, pre_phase, pre_t, post_phase, post_t, transfer_phase))
        if transfer_phase != current_phase:
            if current_phase is not None:
                runs.append((current_phase, current_length))
            current_phase = transfer_phase
            current_length = 1
        else:
            current_length += 1
    if current_phase is not None:
        runs.append((current_phase, current_length))
    return runs, timeline


def _steady_real_node_phase_run_lengths(signal_setting, signal_offset=0.0, max_steps=500):
    _world, node = _build_single_signal_node_world(signal_setting, signal_offset)
    runs, _timeline = _measure_real_node_transfer_phase_runs(node, max_steps=max_steps)
    start_index = None
    for index in range(len(runs) - 3):
        window = runs[index : index + 4]
        lengths = [length for _phase, length in window]
        phases = [phase for phase, _length in window]
        if (
            phases == [0, 1, 2, 3]
            and lengths == CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS
        ):
            start_index = index
            break
    if start_index is None:
        raise AssertionError(
            f"real Node: could not find steady 60/1/60/1 transfer cycle for "
            f"signal={signal_setting}, offset={signal_offset}; observed runs={runs[:12]}"
        )
    return runs[start_index : start_index + 4]


def _direction_change_timeline_from_transfer_history(timeline):
    last_green = None
    first_all_red = None
    first_new_green = None
    for w_t, _pre_p, _pre_t, _post_p, _post_t, xfer in timeline:
        if xfer == 0:
            last_green = w_t
        if last_green is not None and xfer == 1 and first_all_red is None:
            first_all_red = w_t
        if first_all_red is not None and xfer == 2 and first_new_green is None:
            first_new_green = w_t
    if last_green is None or first_all_red is None or first_new_green is None:
        raise AssertionError("could not derive direction-change timeline")
    if first_all_red != last_green + 1:
        raise AssertionError(
            f"expected all-red at T+1 after last green; "
            f"last_green={last_green}, first_all_red={first_all_red}"
        )
    if first_new_green != last_green + 2:
        raise AssertionError(
            f"expected new green at T+2 after last green; "
            f"last_green={last_green}, first_new_green={first_new_green}"
        )
    return {
        "last_old_direction_green_transfer": last_green,
        "first_all_red_transfer": first_all_red,
        "first_new_direction_green_transfer": first_new_green,
    }


def _verify_vehicle_plan_invariants(vehicle_plans):
    if len(vehicle_plans) != NUM_VEHICLES:
        raise AssertionError(
            f"expected {NUM_VEHICLES} vehicle plans, got {len(vehicle_plans)}"
        )

    expected_names = [f"veh_{index}" for index in range(NUM_VEHICLES)]
    actual_names = [plan["name"] for plan in vehicle_plans]
    if actual_names != expected_names:
        raise AssertionError("vehicle names are not veh_0..veh_9999 without gaps")
    if len(set(actual_names)) != NUM_VEHICLES:
        raise AssertionError("duplicate vehicle names in generated plans")

    departure_times = []
    manhattan_distances = []
    for index, plan in enumerate(vehicle_plans):
        if plan["origin"] == plan["destination"]:
            raise AssertionError(f"{plan['name']}: origin equals destination")
        if plan["manhattan_distance"] < MIN_OD_MANHATTAN_DISTANCE:
            raise AssertionError(
                f"{plan['name']}: manhattan distance {plan['manhattan_distance']} "
                f"< {MIN_OD_MANHATTAN_DISTANCE}"
            )
        expected_departure = DEPARTURE_START + (
            (DEPARTURE_END - DEPARTURE_START) * index / max(NUM_VEHICLES - 1, 1)
        )
        if plan["departure_time"] != expected_departure:
            raise AssertionError(
                f"{plan['name']}: departure_time {plan['departure_time']} "
                f"!= expected {expected_departure}"
            )
        departure_times.append(plan["departure_time"])
        manhattan_distances.append(plan["manhattan_distance"])

    if departure_times[0] != float(DEPARTURE_START):
        raise AssertionError(f"first departure must be {DEPARTURE_START}")
    if departure_times[-1] != float(DEPARTURE_END):
        raise AssertionError(f"last departure must be {DEPARTURE_END}")

    minimum_distance = min(manhattan_distances)
    if minimum_distance != MIN_OD_MANHATTAN_DISTANCE:
        raise AssertionError(
            f"minimum OD Manhattan distance must be {MIN_OD_MANHATTAN_DISTANCE}, "
            f"got {minimum_distance}"
        )

    return {
        "total_vehicles": len(vehicle_plans),
        "first_departure_time": departure_times[0],
        "last_departure_time": departure_times[-1],
        "minimum_od_manhattan_distance": minimum_distance,
        "average_od_manhattan_distance": sum(manhattan_distances) / len(
            manhattan_distances
        ),
    }


def _init_signal_probe_state(signal_setting, signal_offset, deltat):
    cycle_length = sum(signal_setting)
    signal_phase = 0
    signal_t = 0
    offset = cycle_length - signal_offset
    if signal_setting != [0]:
        phase_index = 0
        while True:
            if offset < signal_setting[phase_index]:
                signal_phase = phase_index
                signal_t = offset
                break
            offset -= signal_setting[phase_index]
            phase_index += 1
            if phase_index >= len(signal_setting):
                phase_index = 0
    return {
        "signal": list(signal_setting),
        "deltat": deltat,
        "signal_phase": signal_phase,
        "signal_t": signal_t,
    }


def _signal_control_probe_step(probe):
    pre_phase = probe["signal_phase"]
    pre_t = probe["signal_t"]
    signal = probe["signal"]
    deltat = probe["deltat"]
    if probe["signal_t"] > signal[probe["signal_phase"]]:
        probe["signal_phase"] += 1
        probe["signal_t"] = 0
        if probe["signal_phase"] >= len(signal):
            probe["signal_phase"] = 0
    probe["signal_t"] += deltat
    return pre_phase, pre_t, probe["signal_phase"], probe["signal_t"], probe["signal_phase"]


def _verify_corrected_signal_timing_sanity():
    signal_setting = CORRECTED_SIGNAL_SETTING
    deltat = 1.0
    signal_offset = 0.0

    real_runs = _steady_real_node_phase_run_lengths(
        signal_setting, signal_offset=signal_offset
    )
    lengths = [length for _phase, length in real_runs]
    phases = [phase for phase, _length in real_runs]
    if phases != [0, 1, 2, 3]:
        raise AssertionError(f"real Node: unexpected steady phases: {phases}")
    if lengths != CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS:
        raise AssertionError(
            f"real Node: unexpected steady transfer lengths: {lengths}, "
            f"expected {CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS}"
        )
    cycle_length = sum(lengths)
    if cycle_length != CORRECTED_SIGNAL_EFFECTIVE_TRANSFER_CYCLE:
        raise AssertionError(
            f"real Node: unexpected effective transfer cycle: {cycle_length}, "
            f"expected {CORRECTED_SIGNAL_EFFECTIVE_TRANSFER_CYCLE}"
        )

    _world, node = _build_single_signal_node_world(signal_setting, signal_offset)
    _runs, real_timeline = _measure_real_node_transfer_phase_runs(node, max_steps=70)
    direction_timeline = _direction_change_timeline_from_transfer_history(real_timeline)

    probe = _init_signal_probe_state(signal_setting, signal_offset, deltat)
    probe_timeline = []
    for w_t in range(70):
        pre_p, pre_t, post_p, post_t, xfer = _signal_control_probe_step(probe)
        probe_timeline.append((w_t, pre_p, pre_t, post_p, post_t, xfer))

    return {
        "signal_setting": signal_setting,
        "signal_offset": signal_offset,
        "deltat": deltat,
        "steady_phase_lengths": lengths,
        "effective_transfer_cycle": cycle_length,
        "direction_change_timeline": direction_timeline,
        "timeline_sample": real_timeline[55:64],
        "probe_timeline_sample": probe_timeline[55:64],
        "verification_source": "real Node.update()",
    }


def _expected_offset_values(cycle_length):
    step = cycle_length / 4
    return {round(group * step, 1) for group in range(4)}


def _verify_corrected_signal_offset_sanity():
    signal_setting = CORRECTED_SIGNAL_SETTING
    W, signal_params = _build_signalized_network_only(signal_setting)
    cycle_length = signal_params["cycle_length"]
    offset_step = cycle_length / 4
    expected_offsets = _expected_offset_values(cycle_length)

    offsets_by_node = {}
    group_mismatches = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            node_name = _grid_node_name(row, column)
            node = W.NODES_NAME_DICT[node_name]
            offset = getattr(node, "signal_offset", None)
            offsets_by_node[node_name] = offset
            expected_group = (row + column) % 4
            expected_offset = round(expected_group * offset_step, 1)
            if offset != expected_offset:
                group_mismatches.append(
                    (node_name, row, column, expected_group, expected_offset, offset)
                )

    control_summary = _collect_signalized_control_summary(W, signal_params)
    signal_group_counts = _count_links_by_signal_group(W)

    if len(offsets_by_node) != INTERNAL_GRID_NODE_COUNT:
        raise AssertionError("internal node offset map incomplete")
    observed_offsets = {round(value, 1) for value in offsets_by_node.values()}
    if observed_offsets != expected_offsets:
        raise AssertionError(
            f"unexpected offset set: {sorted(observed_offsets)}, "
            f"expected {sorted(expected_offsets)}"
        )
    if group_mismatches:
        raise AssertionError(f"offset group mismatches: {group_mismatches[:5]}")
    if control_summary["signal_group_1_link_count"] != 0:
        raise AssertionError("phase 1 links must be zero")
    if control_summary["signal_group_3_link_count"] != 0:
        raise AssertionError("phase 3 links must be zero")
    if signal_group_counts.get(0, 0) == 0 or signal_group_counts.get(2, 0) == 0:
        raise AssertionError("east-west / north-south signal groups must be non-zero")

    steady_lengths_by_offset = {}
    for offset_value in sorted(expected_offsets):
        steady_runs = _steady_real_node_phase_run_lengths(
            signal_setting, signal_offset=offset_value
        )
        steady_lengths = [length for _phase, length in steady_runs]
        if steady_lengths != CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS:
            raise AssertionError(
                f"real Node offset={offset_value}: steady lengths {steady_lengths}, "
                f"expected {CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS}"
            )
        steady_lengths_by_offset[offset_value] = steady_lengths

    return {
        "cycle_length": cycle_length,
        "offset_step": offset_step,
        "expected_offsets": sorted(expected_offsets),
        "signal_group_counts": signal_group_counts,
        "control_summary": control_summary,
        "steady_lengths_by_offset": steady_lengths_by_offset,
        "steady_lengths_offset_zero": steady_lengths_by_offset[0.0],
        "steady_lengths_offset_nonzero": steady_lengths_by_offset[29.5],
        "non_zero_offset_checked": 29.5,
    }


def _run_corrected_signal_case(case_name, vehicle_plans):
    started = time.perf_counter()
    W, signal_params = build_corrected_signalized_world(
        vehicle_plans, TMAX, CORRECTED_SIGNAL_SETTING
    )
    elapsed = time.perf_counter() - started

    control_summary = _collect_signalized_control_summary(W, signal_params)
    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W, TMAX)
    demand_summary = _demand_summary(vehicle_plans, case_name, TMAX)

    sanity = {}
    sanity["total vehicles == 10000"] = (
        "pass" if results["total_vehicles"] == NUM_VEHICLES else "fail"
    )
    sanity["completed trips == 10000"] = (
        "pass" if results["completed_trips"] == NUM_VEHICLES else "fail"
    )
    sanity["completed ratio == 1.0"] = (
        "pass" if results["completed_ratio"] == 1.0 else "fail"
    )
    sanity["unfinished == 0"] = (
        "pass"
        if results["total_vehicles"] - results["completed_trips"] == 0
        else "fail"
    )
    sanity["signalized internal node count == 36"] = (
        "pass"
        if control_summary["signalized_internal_grid_node_count"]
        == INTERNAL_GRID_NODE_COUNT
        else "fail"
    )
    sanity["signal_group 1 link count == 0"] = (
        "pass" if control_summary["signal_group_1_link_count"] == 0 else "fail"
    )
    sanity["signal_group 3 link count == 0"] = (
        "pass" if control_summary["signal_group_3_link_count"] == 0 else "fail"
    )
    sanity["signal setting == [59,0,59,0]"] = (
        "pass" if signal_params["signal_setting"] == CORRECTED_SIGNAL_SETTING else "fail"
    )
    sanity["configured cycle length == 118"] = (
        "pass" if signal_params["cycle_length"] == 118 else "fail"
    )
    try:
        _verify_vehicle_plan_invariants(vehicle_plans)
        sanity["demand plan invariant checks"] = "pass"
    except AssertionError:
        sanity["demand plan invariant checks"] = "fail"
    expected_offsets = _expected_offset_values(signal_params["cycle_length"])
    observed_offsets = {
        round(value, 1) for value in control_summary["signal_offsets"].values()
    }
    sanity["offset set == {0.0,29.5,59.0,88.5}"] = (
        "pass" if observed_offsets == expected_offsets else "fail"
    )

    for label, status in sanity.items():
        if status != "pass":
            raise AssertionError(f"{case_name}: sanity check failed: {label} = {status}")

    return {
        "case_name": case_name,
        "mode": "signalized UXsim (corrected setting)",
        "batch_size": None,
        "signal_setting": signal_params["signal_setting"],
        "cycle_length": signal_params["cycle_length"],
        "effective_phase_lengths": CORRECTED_SIGNAL_EFFECTIVE_PHASE_LENGTHS,
        "effective_transfer_cycle": CORRECTED_SIGNAL_EFFECTIVE_TRANSFER_CYCLE,
        "green_ew": signal_params["green_ew"],
        "green_ns": signal_params["green_ns"],
        "results": results,
        "completion": completion,
        "elapsed_seconds": elapsed,
        "sanity_checks": sanity,
        "control_summary": control_summary,
        "demand_summary": demand_summary,
        "offset_step": signal_params["cycle_length"] / 4,
        "offset_values": sorted(expected_offsets),
    }


def _format_metric_delta(label, corrected_value, reference_value):
    difference = corrected_value - reference_value
    ratio = _safe_ratio(corrected_value, reference_value)
    percent_change = None
    if reference_value not in (None, 0):
        percent_change = 100.0 * difference / reference_value
    return {
        "label": label,
        "corrected": corrected_value,
        "reference": reference_value,
        "difference": difference,
        "ratio": ratio,
        "percent_change": percent_change,
    }


def _print_metric_delta_block(title, metric):
    print(f"\n{title}")
    print(f"  corrected: {metric['corrected']}")
    print(f"  reference: {metric['reference']}")
    print(f"  difference: {metric['difference']}")
    if metric["ratio"] is not None:
        print(f"  ratio (corrected / reference): {metric['ratio']:.6f}")
    if metric["percent_change"] is not None:
        print(f"  percent change: {metric['percent_change']:.4f}%")


def _compare_average_travel_time_gap(batch_avg_tt, signal_avg_tt):
    difference = batch_avg_tt - signal_avg_tt
    ratio = _safe_ratio(batch_avg_tt, signal_avg_tt)
    percent_difference = None
    if signal_avg_tt not in (None, 0):
        percent_difference = 100.0 * difference / signal_avg_tt
    return {
        "difference_seconds": difference,
        "ratio": ratio,
        "percent_difference": percent_difference,
    }


def main_corrected_signal_baseline_only():
    print("=" * 72)
    print("Corrected signal baseline only: S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1")
    print("=" * 72)
    print(
        "\nDoes NOT run FCFS, BATCH, P1–P4, or other simulations.\n"
        f"Corrected signal setting: {CORRECTED_SIGNAL_SETTING}\n"
        f"Offset strategy: {SIGNAL_OFFSET_STRATEGY}\n"
    )

    print("Running corrected-signal timing sanity check (offset=0, real Node)...")
    timing_sanity = _verify_corrected_signal_timing_sanity()
    print(f"  PASS ({timing_sanity['verification_source']})")
    print(
        f"  steady transfer phase lengths: {timing_sanity['steady_phase_lengths']}"
    )
    print(
        f"  effective transfer cycle: {timing_sanity['effective_transfer_cycle']} timesteps"
    )
    direction_timeline = timing_sanity["direction_change_timeline"]
    print(
        "  direction-change timeline (real Node, offset=0): "
        f"T={direction_timeline['last_old_direction_green_transfer']} old green, "
        f"T+1={direction_timeline['first_all_red_transfer']} all-red, "
        f"T+2={direction_timeline['first_new_direction_green_transfer']} new green"
    )
    print("  sample timeline W.T=55..63 (real Node):")
    for row in timing_sanity["timeline_sample"]:
        print(
            f"    W.T={row[0]} pre_phase={row[1]} pre_t={row[2]} "
            f"post_phase={row[3]} post_t={row[4]} transfer_phase={row[5]}"
        )

    print("\nRunning corrected-signal offset sanity check...")
    offset_sanity = _verify_corrected_signal_offset_sanity()
    print("  PASS")
    print(f"  configured cycle length: {offset_sanity['cycle_length']} s")
    print(f"  offset step: {offset_sanity['offset_step']} s")
    print(f"  offset values: {offset_sanity['expected_offsets']}")
    print(f"  signal group link counts: {offset_sanity['signal_group_counts']}")
    print(
        f"  steady lengths offset=0: {offset_sanity['steady_lengths_offset_zero']}"
    )
    print(
        f"  steady lengths offset={offset_sanity['non_zero_offset_checked']}: "
        f"{offset_sanity['steady_lengths_offset_nonzero']}"
    )
    print("  steady lengths by offset (real Node):")
    for offset_value, lengths in offset_sanity["steady_lengths_by_offset"].items():
        print(f"    offset={offset_value}: {lengths}")

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    demand_invariants = _verify_vehicle_plan_invariants(vehicle_plans)
    print("\nDemand plan invariant checks: PASS")
    print(f"  total plans: {demand_invariants['total_vehicles']}")
    print(
        f"  first departure: {demand_invariants['first_departure_time']}, "
        f"last departure: {demand_invariants['last_departure_time']}"
    )
    print(
        f"  minimum OD Manhattan distance: "
        f"{demand_invariants['minimum_od_manhattan_distance']}"
    )
    print(
        f"  average OD Manhattan distance (generator full precision): "
        f"{demand_invariants['average_od_manhattan_distance']}"
    )

    case_result = _run_corrected_signal_case(
        CORRECTED_SIGNAL_CASE_NAME,
        vehicle_plans,
    )
    print("\n" + _format_case_report(case_result))
    print(
        f"  effective transfer phase lengths: "
        f"{case_result['effective_phase_lengths']}"
    )
    print(
        f"  effective transfer cycle: "
        f"{case_result['effective_transfer_cycle']} timesteps"
    )
    print(f"  offset step: {case_result['offset_step']} s")
    print(f"  offset values: {case_result['offset_values']}")
    print(
        "  signalized internal nodes: "
        f"{sorted(case_result['control_summary']['signal_offsets'].keys())}"
    )

    corrected_results = case_result["results"]
    corrected_completion = case_result["completion"]
    batch_ref = REFERENCE_BATCH_N10_POST_ZERO_SERVICE_FIX
    old_signal_ref = REFERENCE_SIGNAL_60_1_60_1

    batch_vs_corrected = {
        "total_travel_time": _format_metric_delta(
            "total travel time",
            corrected_results["total_travel_time"],
            batch_ref["total_travel_time"],
        ),
        "average_travel_time": _format_metric_delta(
            "average travel time",
            corrected_results["average_travel_time"],
            batch_ref["average_travel_time"],
        ),
        "total_distance_traveled": _format_metric_delta(
            "total distance traveled",
            corrected_results["total_distance_traveled"],
            batch_ref["total_distance_traveled"],
        ),
        "last_completed_trip_time": _format_metric_delta(
            "last completed trip time",
            corrected_completion["last_completed_trip_time"],
            batch_ref["last_completed_trip_time"],
        ),
    }

    print("\nCorrected signal vs post-fix BATCH N=10:")
    for key, metric in batch_vs_corrected.items():
        _print_metric_delta_block(key, metric)

    avg_tt_gap = _compare_average_travel_time_gap(
        batch_ref["average_travel_time"], corrected_results["average_travel_time"]
    )
    print("\nBATCH N=10 vs corrected signal (average travel time):")
    print(f"  BATCH - corrected difference: {avg_tt_gap['difference_seconds']:.4f} s")
    print(f"  BATCH / corrected ratio: {avg_tt_gap['ratio']:.6f}")
    print(
        f"  BATCH excess percent over corrected signal: "
        f"{avg_tt_gap['percent_difference']:.4f}%"
    )

    print(
        "\nAverage delay reference comparison (display-precision approximation only):"
    )
    print(
        f"  corrected signal average delay (full precision): "
        f"{corrected_results['average_delay']}"
    )
    print(
        f"  BATCH N=10 average delay display value: {BATCH_N10_POST_FIX_AVG_DELAY_DISPLAY}"
    )
    delay_display_ratio = _safe_ratio(
        BATCH_N10_POST_FIX_AVG_DELAY_DISPLAY, corrected_results["average_delay"]
    )
    if delay_display_ratio is not None:
        print(
            f"  BATCH display / corrected full ratio "
            f"(display-precision approximation): {delay_display_ratio:.6f}"
        )

    print("\nRanking (lower is better for time metrics):")
    rankings = {
        "average_travel_time": (
            "BATCH N=10"
            if batch_ref["average_travel_time"]
            < corrected_results["average_travel_time"]
            else "corrected signal"
        ),
        "average_delay": (
            "BATCH N=10"
            if BATCH_N10_POST_FIX_AVG_DELAY_DISPLAY
            < corrected_results["average_delay"]
            else "corrected signal"
        ),
        "total_distance_traveled": (
            "BATCH N=10"
            if batch_ref["total_distance_traveled"]
            < corrected_results["total_distance_traveled"]
            else "corrected signal"
        ),
        "last_completed_trip_time": (
            "BATCH N=10"
            if batch_ref["last_completed_trip_time"]
            < corrected_completion["last_completed_trip_time"]
            else "corrected signal"
        ),
    }
    for metric_name, winner in rankings.items():
        print(f"  {metric_name}: {winner}")

    old_vs_corrected = {
        "total_travel_time": _format_metric_delta(
            "total travel time",
            corrected_results["total_travel_time"],
            old_signal_ref["total_travel_time"],
        ),
        "average_travel_time": _format_metric_delta(
            "average travel time",
            corrected_results["average_travel_time"],
            OLD_SIGNAL_PRECISE_AVERAGE_TRAVEL_TIME,
        ),
        "average_delay": _format_metric_delta(
            "average delay",
            corrected_results["average_delay"],
            old_signal_ref["average_delay"],
        ),
        "total_distance_traveled": _format_metric_delta(
            "total distance traveled",
            corrected_results["total_distance_traveled"],
            old_signal_ref["total_distance_traveled"],
        ),
        "last_completed_trip_time": _format_metric_delta(
            "last completed trip time",
            corrected_completion["last_completed_trip_time"],
            old_signal_ref["last_completed_trip_time"],
        ),
    }

    print(
        "\nHistorical old signal [60,1,60,1] vs corrected signal "
        "(old signal is NOT a fair clearance baseline):"
    )
    for metric in old_vs_corrected.values():
        _print_metric_delta_block(metric["label"], metric)

    old_batch_gap = _compare_average_travel_time_gap(
        batch_ref["average_travel_time"], OLD_SIGNAL_PRECISE_AVERAGE_TRAVEL_TIME
    )
    corrected_batch_gap = _compare_average_travel_time_gap(
        batch_ref["average_travel_time"], corrected_results["average_travel_time"]
    )
    old_excess_pp = old_batch_gap["percent_difference"]
    corrected_excess_pp = corrected_batch_gap["percent_difference"]
    pp_change = None
    if old_excess_pp is not None and corrected_excess_pp is not None:
        pp_change = corrected_excess_pp - old_excess_pp

    print("\nBATCH vs signal average travel time gap comparison:")
    print(
        f"  old signal precise average travel time: "
        f"{OLD_SIGNAL_PRECISE_AVERAGE_TRAVEL_TIME}"
    )
    print(
        f"  old signal gap (BATCH - old signal): "
        f"{old_batch_gap['difference_seconds']:.4f} s "
        f"({old_excess_pp:.4f}% over old signal)"
    )
    print(
        f"  corrected signal gap (BATCH - corrected signal): "
        f"{corrected_batch_gap['difference_seconds']:.4f} s "
        f"({corrected_excess_pp:.4f}% over corrected signal)"
    )
    if pp_change is not None:
        if abs(pp_change) < 0.05:
            change_label = "approximately unchanged"
        elif pp_change > 0:
            change_label = "expanded"
        else:
            change_label = "shrunk"
        print(
            f"  BATCH relative lag vs signal: {change_label} "
            f"({pp_change:+.4f} percentage points vs old-signal comparison)"
        )

    print(
        "\nInterpretation notes:\n"
        "  - same offset formula as before; cycle length and offset values changed only "
        "because the corrected signal setting changed\n"
        "  - corrected setting targets effective green 60 timesteps / all-red 1 timestep\n"
        "  - old signal [60,1,60,1] is a historical condition, not a fair clearance baseline\n"
        "  - exploratory result for fixed demand, one seed, free routing\n"
        "  - do not attribute network-wide differences to a single factor\n"
    )
    print(
        "\nGrid 10000 corrected signal baseline check passed "
        f"({CORRECTED_SIGNAL_CASE_NAME})."
    )


def _safe_ratio(numerator, denominator):
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _demand_matches_reference(demand_summary, reference_demand_summary):
    return (
        demand_summary["total_vehicles"] == reference_demand_summary["total_vehicles"]
        and demand_summary["first_departure_time"]
        == reference_demand_summary["first_departure_time"]
        and demand_summary["last_departure_time"]
        == reference_demand_summary["last_departure_time"]
        and demand_summary["demand_duration"]
        == reference_demand_summary["demand_duration"]
        and demand_summary["minimum_od_manhattan_distance"]
        == reference_demand_summary["minimum_od_manhattan_distance"]
        and demand_summary["average_od_manhattan_distance"]
        == reference_demand_summary["average_od_manhattan_distance"]
        and demand_summary["maximum_od_manhattan_distance"]
        == reference_demand_summary["maximum_od_manhattan_distance"]
        and demand_summary["origin_sequence"]
        == reference_demand_summary["origin_sequence"]
        and demand_summary["destination_sequence"]
        == reference_demand_summary["destination_sequence"]
        and demand_summary["departure_time_sequence"]
        == reference_demand_summary["departure_time_sequence"]
        and demand_summary["origin_grid_coord_sequence"]
        == reference_demand_summary["origin_grid_coord_sequence"]
        and demand_summary["destination_grid_coord_sequence"]
        == reference_demand_summary["destination_grid_coord_sequence"]
        and demand_summary["manhattan_distance_sequence"]
        == reference_demand_summary["manhattan_distance_sequence"]
        and demand_summary["tmax"] == reference_demand_summary["tmax"]
    )


def _check_completed_ratio(results, case_name):
    ratio = results["completed_ratio"]
    if ratio < COMPLETED_RATIO_MIN:
        raise AssertionError(
            f"{case_name}: completed_ratio={ratio:.3f} < {COMPLETED_RATIO_MIN}"
        )
    if ratio < 1.0:
        print(
            f"\n*** WARNING ({case_name}): completed_ratio={ratio:.3f} < 1.000 ***"
        )
        print(
            f"    completed trips: {results['completed_trips']} / "
            f"{results['total_vehicles']}"
        )
        print(
            f"    unfinished vehicles: "
            f"{results['total_vehicles'] - results['completed_trips']}"
        )
        print(
            "    Travel-time comparisons include unfinished vehicles; interpret with care."
        )


def _collect_vehicle_snapshots(W):
    snapshots = {}
    for name in sorted(W.VEHICLES):
        veh = W.VEHICLES[name]
        snapshots[name] = {
            "name": name,
            "state": veh.state,
            "arrival_time": veh.arrival_time,
            "travel_time": veh.travel_time,
        }
    return snapshots


def _normalize_log_t_link_entry(event_index, time_value, link_value):
    entry = {
        "index": event_index,
        "time": time_value,
        "link_name": None,
        "start_node": None,
        "end_node": None,
    }
    if link_value == "home":
        entry["link_name"] = "home"
    elif link_value == "end":
        entry["link_name"] = "end"
    elif link_value is None:
        entry["link_name"] = None
    elif hasattr(link_value, "name"):
        entry["link_name"] = link_value.name
        entry["start_node"] = link_value.start_node.name
        entry["end_node"] = link_value.end_node.name
    else:
        entry["link_name"] = str(link_value)
    return entry


def _normalize_log_t_link_history(veh):
    return [
        _normalize_log_t_link_entry(event_index, time_value, link_value)
        for event_index, (time_value, link_value) in enumerate(veh.log_t_link)
    ]


def _traveled_route_link_names(veh):
    route, _timestamps = veh.traveled_route()
    return [link.name for link in route]


def _collect_vehicle_link_histories(W):
    histories = {}
    for name in sorted(W.VEHICLES):
        veh = W.VEHICLES[name]
        histories[name] = {
            "name": name,
            "state": veh.state,
            "arrival_time": veh.arrival_time,
            "travel_time": veh.travel_time,
            "traveled_route_link_names": _traveled_route_link_names(veh),
            "log_t_link_events": _normalize_log_t_link_history(veh),
        }
    if not histories:
        raise AssertionError("no vehicle link histories collected")
    return histories


def _build_link_node_metadata(W, eligible_node_names):
    eligible_set = set(eligible_node_names)
    metadata = {}
    for link in W.LINKS:
        start_name = link.start_node.name
        metadata[link.name] = {
            "start_node": start_name,
            "end_node": link.end_node.name,
            "start_node_order_control_eligible": start_name in eligible_set,
            "start_node_order_control_type": link.start_node.order_control_type,
        }
    return metadata


def _vehicle_numeric_id(vehicle_name):
    if vehicle_name.startswith("veh_"):
        return int(vehicle_name[4:])
    return 10**18


def _first_route_diff_index(left_route, right_route):
    limit = max(len(left_route), len(right_route))
    for index in range(limit):
        left_value = left_route[index] if index < len(left_route) else None
        right_value = right_route[index] if index < len(right_route) else None
        if left_value != right_value:
            return index
    return None


def _classify_link_history_difference(
    fcfs_event, batch_event, mismatch_index, fcfs_event_count, batch_event_count
):
    if fcfs_event is None and batch_event is None:
        return None
    if fcfs_event is None and batch_event is not None:
        if mismatch_index == fcfs_event_count:
            return "history length differs after a common prefix"
        return "event only on BATCH"
    if batch_event is None and fcfs_event is not None:
        if mismatch_index == batch_event_count:
            return "history length differs after a common prefix"
        return "event only on FCFS"

    f_link = fcfs_event["link_name"]
    b_link = batch_event["link_name"]
    f_time = fcfs_event["time"]
    b_time = batch_event["time"]
    if f_link == b_link and f_time != b_time:
        return "same link, different entry time"
    if f_time == b_time and f_link != b_link:
        return "same time, different link"
    if f_time != b_time and f_link != b_link:
        return "different time and different link"
    if fcfs_event != batch_event:
        return "other"
    return None


def _provisional_route_timing_judgment(comparison):
    classification = comparison["classification"]
    routes_match = comparison["routes_match"]
    route_first_diff_index = comparison["route_first_diff_index"]
    mismatch_index = comparison["first_mismatch_index"]

    if classification == "same link, different entry time":
        if routes_match:
            return "local timing divergence before route divergence"
        if (
            route_first_diff_index is not None
            and route_first_diff_index > mismatch_index
        ):
            return "timing divergence followed by later route divergence"
        return "local timing divergence before route divergence"

    if classification in (
        "same time, different link",
        "different time and different link",
    ):
        if comparison["prefix_length"] == mismatch_index:
            return "route-choice divergence"
        return "route divergence without earlier observed timing difference"

    return "other / unresolved"


def _compare_vehicle_link_histories(fcfs_snap, batch_snap):
    fcfs_events = fcfs_snap["log_t_link_events"]
    batch_events = batch_snap["log_t_link_events"]
    fcfs_route = fcfs_snap["traveled_route_link_names"]
    batch_route = batch_snap["traveled_route_link_names"]
    routes_match = fcfs_route == batch_route
    route_first_diff_index = (
        None if routes_match else _first_route_diff_index(fcfs_route, batch_route)
    )

    prefix_length = 0
    first_mismatch_index = None
    fcfs_event = None
    batch_event = None
    prev_common_event = None

    max_len = max(len(fcfs_events), len(batch_events))
    for index in range(max_len):
        fcfs_at_index = fcfs_events[index] if index < len(fcfs_events) else None
        batch_at_index = batch_events[index] if index < len(batch_events) else None
        if fcfs_at_index == batch_at_index:
            prefix_length = index + 1
            continue
        first_mismatch_index = index
        fcfs_event = fcfs_at_index
        batch_event = batch_at_index
        prev_common_event = fcfs_events[index - 1] if index > 0 else None
        break

    history_match = first_mismatch_index is None
    earliest_time = None
    if not history_match:
        candidate_times = []
        if fcfs_event is not None:
            candidate_times.append(fcfs_event["time"])
        if batch_event is not None:
            candidate_times.append(batch_event["time"])
        earliest_time = min(candidate_times)

    classification = None
    if not history_match:
        classification = _classify_link_history_difference(
            fcfs_event,
            batch_event,
            first_mismatch_index,
            len(fcfs_events),
            len(batch_events),
        )

    return {
        "vehicle_name": fcfs_snap["name"],
        "vehicle_numeric_id": _vehicle_numeric_id(fcfs_snap["name"]),
        "state": fcfs_snap["state"],
        "arrival_time": fcfs_snap["arrival_time"],
        "travel_time": fcfs_snap["travel_time"],
        "history_match": history_match,
        "prefix_length": prefix_length,
        "first_mismatch_index": first_mismatch_index,
        "fcfs_event": fcfs_event,
        "batch_event": batch_event,
        "prev_common_event": prev_common_event,
        "routes_match": routes_match,
        "route_first_diff_index": route_first_diff_index,
        "fcfs_traveled_route": fcfs_route,
        "batch_traveled_route": batch_route,
        "earliest_time": earliest_time,
        "classification": classification,
    }


def _assert_known_n1_first_link_difference_aggregates(case, expected, case_label):
    results = case["results"]
    completion = case["completion"]
    checks = [
        ("total_vehicles", results["total_vehicles"], expected["total_vehicles"]),
        ("completed_trips", results["completed_trips"], expected["completed_trips"]),
        (
            "total_travel_time",
            results["total_travel_time"],
            expected["total_travel_time"],
        ),
        (
            "average_travel_time",
            results["average_travel_time"],
            expected["average_travel_time"],
        ),
        ("average_delay", results["average_delay"], expected["average_delay"]),
        (
            "total_distance_traveled",
            results["total_distance_traveled"],
            expected["total_distance_traveled"],
        ),
        (
            "unfinished_vehicle_count",
            completion["unfinished_vehicle_count"],
            expected["unfinished_vehicle_count"],
        ),
        (
            "last_completed_trip_time",
            completion["last_completed_trip_time"],
            expected["last_completed_trip_time"],
        ),
    ]
    for field_name, actual, exp_value in checks:
        if actual != exp_value:
            raise AssertionError(
                f"{case_label}: {field_name}={actual!r}, expected {exp_value!r}"
            )


def _run_fcfs_case(case_name, vehicle_plans, reference_demand_summary, collect_link_histories=False):
    started = time.perf_counter()
    W, eligible_node_names = build_fcfs_world(vehicle_plans, TMAX)
    elapsed = time.perf_counter() - started

    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W, TMAX)
    demand_summary = _demand_summary(vehicle_plans, case_name, TMAX)
    vehicle_snapshots = _collect_vehicle_snapshots(W)

    sanity = {}
    sanity["total vehicles == 10000"] = (
        "pass" if results["total_vehicles"] == NUM_VEHICLES else "fail"
    )
    sanity["fcfs eligible node count == 36"] = (
        "pass" if len(eligible_node_names) == INTERNAL_GRID_NODE_COUNT else "fail"
    )
    sanity["demand summary matches reference demand"] = (
        "pass" if _demand_matches_reference(demand_summary, reference_demand_summary) else "fail"
    )
    sanity["completed ratio >= 0.5"] = (
        "pass" if results["completed_ratio"] >= COMPLETED_RATIO_MIN else "fail"
    )
    sanity["non-negative travel metrics"] = (
        "pass"
        if results["total_travel_time"] >= 0
        and results["average_travel_time"] >= 0
        and results["average_delay"] >= 0
        and results["total_distance_traveled"] >= 0
        else "fail"
    )
    sanity["simulation completed without exception"] = "pass"

    for label, status in sanity.items():
        if status != "pass":
            raise AssertionError(f"{case_name}: sanity check failed: {label} = {status}")

    _check_completed_ratio(results, case_name)

    case_result = {
        "case_name": case_name,
        "mode": "FCFS",
        "batch_size": None,
        "results": results,
        "completion": completion,
        "elapsed_seconds": elapsed,
        "sanity_checks": sanity,
        "eligible_node_names": sorted(eligible_node_names),
        "vehicle_snapshots": vehicle_snapshots,
    }
    if collect_link_histories:
        case_result["vehicle_link_histories"] = _collect_vehicle_link_histories(W)
        case_result["link_node_metadata"] = _build_link_node_metadata(
            W, eligible_node_names
        )
    return case_result


def _run_n1_batch_equivalence_case(
    case_name, vehicle_plans, reference_demand_summary, collect_link_histories=False
):
    started = time.perf_counter()
    W, eligible_node_names = build_batch_world(vehicle_plans, TMAX, batch_size=1)
    elapsed = time.perf_counter() - started

    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W, TMAX)
    demand_summary = _demand_summary(vehicle_plans, case_name, TMAX)
    vehicle_snapshots = _collect_vehicle_snapshots(W)

    sanity = {}
    sanity["total vehicles == 10000"] = (
        "pass" if results["total_vehicles"] == NUM_VEHICLES else "fail"
    )
    sanity["batch eligible node count == 36"] = (
        "pass" if len(eligible_node_names) == INTERNAL_GRID_NODE_COUNT else "fail"
    )
    sanity["demand summary matches reference demand"] = (
        "pass" if _demand_matches_reference(demand_summary, reference_demand_summary) else "fail"
    )
    sanity["completed ratio >= 0.5"] = (
        "pass" if results["completed_ratio"] >= COMPLETED_RATIO_MIN else "fail"
    )
    sanity["non-negative travel metrics"] = (
        "pass"
        if results["total_travel_time"] >= 0
        and results["average_travel_time"] >= 0
        and results["average_delay"] >= 0
        and results["total_distance_traveled"] >= 0
        else "fail"
    )
    sanity["simulation completed without assignment/state exception"] = "pass"

    for label, status in sanity.items():
        if status != "pass":
            raise AssertionError(f"{case_name}: sanity check failed: {label} = {status}")

    _check_completed_ratio(results, case_name)

    case_result = {
        "case_name": case_name,
        "mode": "BATCH",
        "batch_size": 1,
        "results": results,
        "completion": completion,
        "elapsed_seconds": elapsed,
        "sanity_checks": sanity,
        "eligible_node_names": sorted(eligible_node_names),
        "vehicle_snapshots": vehicle_snapshots,
    }
    if collect_link_histories:
        case_result["vehicle_link_histories"] = _collect_vehicle_link_histories(W)
        case_result["link_node_metadata"] = _build_link_node_metadata(
            W, eligible_node_names
        )
    return case_result


N1_EQUIVALENCE_AGGREGATE_FIELDS = [
    "total_vehicles",
    "completed_trips",
    "completed_ratio",
    "total_travel_time",
    "average_travel_time",
    "average_delay",
    "total_distance_traveled",
]

N1_EQUIVALENCE_COMPLETION_FIELDS = [
    "unfinished_vehicle_count",
    "last_completed_trip_time",
]

N1_EQUIVALENCE_VEHICLE_FIELDS = [
    "state",
    "arrival_time",
    "travel_time",
]


def _print_n1_equivalence_fail(
    mismatches,
    e0_case,
    e1_case,
    first_vehicle_mismatch=None,
):
    print("\nN=1 equivalence result: FAIL")
    print("Mismatched items:")
    for item in mismatches:
        print(f"  - {item['label']}")
        print(f"    E0: {item['e0']!r}")
        print(f"    E1: {item['e1']!r}")

    if first_vehicle_mismatch is not None:
        veh_name = first_vehicle_mismatch["name"]
        print(f"\nFirst mismatched vehicle: {veh_name}")
        print(f"  E0 snapshot: {first_vehicle_mismatch['e0']!r}")
        print(f"  E1 snapshot: {first_vehicle_mismatch['e1']!r}")

    e0_nodes = set(e0_case["eligible_node_names"])
    e1_nodes = set(e1_case["eligible_node_names"])
    if e0_nodes != e1_nodes:
        print("\nEligible node set difference:")
        print(f"  only in E0: {sorted(e0_nodes - e1_nodes)!r}")
        print(f"  only in E1: {sorted(e1_nodes - e0_nodes)!r}")


def _assert_n1_equivalence(e0_case, e1_case):
    mismatches = []
    e0_results = e0_case["results"]
    e1_results = e1_case["results"]
    e0_completion = e0_case["completion"]
    e1_completion = e1_case["completion"]

    for field in N1_EQUIVALENCE_AGGREGATE_FIELDS:
        e0_value = e0_results[field]
        e1_value = e1_results[field]
        if e0_value != e1_value:
            mismatches.append(
                {"label": field, "e0": e0_value, "e1": e1_value}
            )

    for field in N1_EQUIVALENCE_COMPLETION_FIELDS:
        e0_value = e0_completion[field]
        e1_value = e1_completion[field]
        if e0_value != e1_value:
            mismatches.append(
                {"label": field, "e0": e0_value, "e1": e1_value}
            )

    e0_nodes = e0_case["eligible_node_names"]
    e1_nodes = e1_case["eligible_node_names"]
    if len(e0_nodes) != len(e1_nodes):
        mismatches.append(
            {
                "label": "eligible_node_count",
                "e0": len(e0_nodes),
                "e1": len(e1_nodes),
            }
        )
    if e0_nodes != e1_nodes:
        mismatches.append(
            {
                "label": "eligible_node_names",
                "e0": e0_nodes,
                "e1": e1_nodes,
            }
        )

    e0_snapshots = e0_case["vehicle_snapshots"]
    e1_snapshots = e1_case["vehicle_snapshots"]
    first_vehicle_mismatch = None

    if set(e0_snapshots) != set(e1_snapshots):
        mismatches.append(
            {
                "label": "vehicle_name_set",
                "e0": sorted(e0_snapshots),
                "e1": sorted(e1_snapshots),
            }
        )
    else:
        for name in sorted(e0_snapshots):
            for field in N1_EQUIVALENCE_VEHICLE_FIELDS:
                e0_value = e0_snapshots[name][field]
                e1_value = e1_snapshots[name][field]
                if e0_value != e1_value:
                    mismatches.append(
                        {
                            "label": f"vehicle {name} {field}",
                            "e0": e0_value,
                            "e1": e1_value,
                        }
                    )
                    if first_vehicle_mismatch is None:
                        first_vehicle_mismatch = {
                            "name": name,
                            "field": field,
                            "e0": e0_snapshots[name],
                            "e1": e1_snapshots[name],
                        }
                    break
            if first_vehicle_mismatch is not None:
                break

    compared_items = (
        list(N1_EQUIVALENCE_AGGREGATE_FIELDS)
        + list(N1_EQUIVALENCE_COMPLETION_FIELDS)
        + ["eligible_node_count", "eligible_node_names", "vehicle_name_set"]
        + [
            f"vehicle {name} {field}"
            for name in sorted(e0_snapshots)
            for field in N1_EQUIVALENCE_VEHICLE_FIELDS
        ]
    )

    if mismatches:
        _print_n1_equivalence_fail(mismatches, e0_case, e1_case, first_vehicle_mismatch)
        raise AssertionError(
            f"N=1 equivalence failed with {len(mismatches)} mismatched item(s)"
        )

    print("\nN=1 equivalence result: PASS")
    print("E0 (FCFS clearance=1) aggregate values:")
    for field in N1_EQUIVALENCE_AGGREGATE_FIELDS:
        print(f"  {field}: {e0_results[field]!r}")
    print("E1 (BATCH N=1 clearance=1 Level 1) aggregate values:")
    for field in N1_EQUIVALENCE_AGGREGATE_FIELDS:
        print(f"  {field}: {e1_results[field]!r}")
    print(f"  eligible node count: {len(e0_nodes)} (E0 and E1 match)")
    print(f"  eligible node names match: {e0_nodes == e1_nodes}")
    print(f"  vehicle snapshots match: {len(e0_snapshots)} vehicles")
    print("Compared items:")
    for item in compared_items:
        print(f"  - {item}")
    print(f"E0 elapsed seconds: {e0_case['elapsed_seconds']:.1f}")
    print(f"E1 elapsed seconds: {e1_case['elapsed_seconds']:.1f}")
    print(
        "\nScope notes:\n"
        "  - 10,000-vehicle 6x6 grid\n"
        "  - fixed demand and fixed seeds\n"
        "  - clearance=1\n"
        "  - BATCH Level 1\n"
        "  - this is not a general proof for all networks and demands"
    )

    return compared_items


def _run_batch_case(case_name, vehicle_plans, reference_demand_summary, batch_size):
    started = time.perf_counter()
    W, eligible_node_names = build_batch_world(vehicle_plans, TMAX, batch_size)
    elapsed = time.perf_counter() - started

    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W, TMAX)
    demand_summary = _demand_summary(vehicle_plans, case_name, TMAX)

    sanity = {}
    sanity["total vehicles == 10000"] = (
        "pass" if results["total_vehicles"] == NUM_VEHICLES else "fail"
    )
    sanity["batch eligible node count == 36"] = (
        "pass" if len(eligible_node_names) == INTERNAL_GRID_NODE_COUNT else "fail"
    )
    sanity["demand summary matches reference vehicle_plans"] = (
        "pass" if _demand_matches_reference(demand_summary, reference_demand_summary) else "fail"
    )
    sanity["completed ratio >= 0.5"] = (
        "pass" if results["completed_ratio"] >= COMPLETED_RATIO_MIN else "fail"
    )
    sanity["non-negative travel metrics"] = (
        "pass"
        if results["total_travel_time"] >= 0
        and results["average_travel_time"] >= 0
        and results["average_delay"] >= 0
        and results["total_distance_traveled"] >= 0
        else "fail"
    )
    sanity["simulation completed without assignment/state exception"] = "pass"

    for label, status in sanity.items():
        if status != "pass":
            raise AssertionError(f"{case_name}: sanity check failed: {label} = {status}")

    _check_completed_ratio(results, case_name)

    return {
        "case_name": case_name,
        "mode": "BATCH",
        "batch_size": batch_size,
        "signal_setting": None,
        "cycle_length": None,
        "results": results,
        "completion": completion,
        "elapsed_seconds": elapsed,
        "sanity_checks": sanity,
        "eligible_node_count": len(eligible_node_names),
        "eligible_node_names": sorted(eligible_node_names),
    }


def _run_signalized_case(
    case_name, vehicle_plans, reference_demand_summary, green_ew, green_ns
):
    started = time.perf_counter()
    W, signal_params = build_signalized_world(
        vehicle_plans, TMAX, green_ew, green_ns
    )
    elapsed = time.perf_counter() - started

    control_summary = _collect_signalized_control_summary(W, signal_params)
    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W, TMAX)
    demand_summary = _demand_summary(vehicle_plans, case_name, TMAX)

    sanity = {}
    sanity["total vehicles == 10000"] = (
        "pass" if results["total_vehicles"] == NUM_VEHICLES else "fail"
    )
    sanity["signalized internal node count == 36"] = (
        "pass"
        if control_summary["signalized_internal_grid_node_count"]
        == INTERNAL_GRID_NODE_COUNT
        else "fail"
    )
    sanity["external OD nodes not signalized"] = (
        "pass" if control_summary["signalized_od_node_count"] == 0 else "fail"
    )
    sanity["signal_group 1 link count == 0"] = (
        "pass" if control_summary["signal_group_1_link_count"] == 0 else "fail"
    )
    sanity["signal_group 3 link count == 0"] = (
        "pass" if control_summary["signal_group_3_link_count"] == 0 else "fail"
    )
    sanity["internal nodes use expected signal setting"] = "pass"
    sanity["demand summary matches reference vehicle_plans"] = (
        "pass" if _demand_matches_reference(demand_summary, reference_demand_summary) else "fail"
    )
    sanity["completed ratio >= 0.5"] = (
        "pass" if results["completed_ratio"] >= COMPLETED_RATIO_MIN else "fail"
    )
    sanity["non-negative travel metrics"] = (
        "pass"
        if results["total_travel_time"] >= 0
        and results["average_travel_time"] >= 0
        and results["average_delay"] >= 0
        and results["total_distance_traveled"] >= 0
        else "fail"
    )

    for label, status in sanity.items():
        if status != "pass":
            raise AssertionError(f"{case_name}: sanity check failed: {label} = {status}")

    _check_completed_ratio(results, case_name)

    return {
        "case_name": case_name,
        "mode": "signalized UXsim",
        "batch_size": None,
        "signal_setting": signal_params["signal_setting"],
        "cycle_length": signal_params["cycle_length"],
        "green_ew": green_ew,
        "green_ns": green_ns,
        "results": results,
        "completion": completion,
        "elapsed_seconds": elapsed,
        "sanity_checks": sanity,
        "control_summary": control_summary,
    }


def _format_case_report(case_result):
    results = case_result["results"]
    completion = case_result["completion"]
    unfinished = results["total_vehicles"] - results["completed_trips"]
    lines = [
        f"Case: {case_result['case_name']}",
        f"  mode: {case_result['mode']}",
    ]
    if case_result["batch_size"] is not None:
        lines.append(f"  batch size: {case_result['batch_size']}")
    if case_result["signal_setting"] is not None:
        lines.append(f"  signal setting: {case_result['signal_setting']}")
        lines.append(
            f"  east-west green (phase 0): {case_result['green_ew']} s; "
            f"north-south green (phase 2): {case_result['green_ns']} s"
        )
    if case_result["cycle_length"] is not None:
        lines.append(f"  cycle length: {case_result['cycle_length']} s")
    lines.extend(
        [
            f"  total vehicles: {results['total_vehicles']}",
            f"  completed trips: {results['completed_trips']}",
            f"  completed ratio: {results['completed_ratio']:.3f}",
            f"  total travel time: {results['total_travel_time']:.1f} s",
            f"  average travel time: {results['average_travel_time']:.1f} s",
            f"  average delay: {results['average_delay']:.1f} s",
            f"  total distance traveled: {results['total_distance_traveled']:.1f} m",
            f"  unfinished vehicles: {unfinished}",
            f"  last completed trip time: {completion['last_completed_trip_time']}",
            f"  elapsed seconds: {case_result['elapsed_seconds']:.1f}",
            "  sanity checks:",
        ]
    )
    for name, status in case_result["sanity_checks"].items():
        lines.append(f"    - {name}: {status}")
    return "\n".join(lines)


def _reference_row(ref):
    return {
        "label": ref["label"],
        "average_travel_time": ref.get("average_travel_time"),
        "average_delay": ref.get("average_delay"),
        "total_distance": ref.get("total_distance_traveled"),
        "completed_ratio": ref["completed_ratio"],
        "last_completed_trip_time": ref.get("last_completed_trip_time"),
    }


def _case_row(case_result):
    results = case_result["results"]
    completion = case_result["completion"]
    label = case_result["case_name"]
    if case_result["batch_size"] is not None:
        label += f" (BATCH N={case_result['batch_size']})"
    elif case_result["signal_setting"] is not None:
        label += f" (signal {case_result['signal_setting']})"
    return {
        "label": label,
        "average_travel_time": results["average_travel_time"],
        "average_delay": results["average_delay"],
        "total_distance": results["total_distance_traveled"],
        "completed_ratio": results["completed_ratio"],
        "last_completed_trip_time": completion["last_completed_trip_time"],
    }


def _comparison_table_metric_text(value):
    if value is None:
        return "not available"
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)


def _print_comparison_table(rows):
    print("\nComparison table (average travel time, delay, distance, completion):")
    print(
        f"{'label':<45} {'avg TT':>10} {'avg delay':>13} "
        f"{'total dist':>14} {'compl ratio':>12} {'last compl':>12}"
    )
    for row in rows:
        last_compl = row["last_completed_trip_time"]
        if isinstance(last_compl, (int, float)):
            last_compl_text = f"{last_compl:.1f}"
        else:
            last_compl_text = (
                "not available" if last_compl is None else str(last_compl)
            )
        print(
            f"{row['label']:<45} "
            f"{_comparison_table_metric_text(row['average_travel_time']):>10} "
            f"{_comparison_table_metric_text(row['average_delay']):>13} "
            f"{_comparison_table_metric_text(row['total_distance']):>14} "
            f"{row['completed_ratio']:>12.3f} "
            f"{last_compl_text:>12}"
        )


def _observed_change_label(new_value, reference_value):
    if reference_value <= 0:
        return "not available"
    ratio = new_value / reference_value
    if ratio < 1.0:
        return f"improved by {(1 - ratio) * 100:.1f}% (lower average travel time)"
    if ratio > 1.0:
        return f"worsened by {(ratio - 1) * 100:.1f}% (higher average travel time)"
    return "approximately unchanged"


def _local_diff_link_name(link):
    if link is None:
        return None
    if isinstance(link, str):
        return link
    return link.name


def _local_diff_visit_fields(veh):
    visit = veh.order_control_current_visit
    if visit is None:
        return {
            "has_current_visit": False,
            "current_visit_node": None,
            "current_visit_inlink": None,
            "visit_id": None,
            "arrival_time": None,
            "arrival_tiebreaker": None,
            "batch_assignment": None,
            "earliest_arrival_timestep": None,
        }
    earliest = visit.get("earliest_arrival_timestep")
    return {
        "has_current_visit": True,
        "current_visit_node": visit["node"].name,
        "current_visit_inlink": visit["inlink"].name,
        "visit_id": visit["visit_id"],
        "arrival_time": visit["arrival_time"],
        "arrival_tiebreaker": visit["arrival_tiebreaker"],
        "batch_assignment": visit.get("batch_assignment"),
        "earliest_arrival_timestep": earliest,
    }


def _local_diff_clearance_for_vehicle(node, veh):
    clearance_required = (
        node.last_order_control_inlink is not None
        and veh.link is not None
        and veh.link != node.last_order_control_inlink
    )
    if not clearance_required:
        return False, True
    if node.last_order_control_entry_timestep is None:
        return True, False
    clearance_satisfied = (
        node.W.T - node.last_order_control_entry_timestep
        > node.order_control_clearance_timesteps
    )
    return True, clearance_satisfied


def _local_diff_can_transfer_vehicle(veh, inlink, outlink, node):
    if outlink is None or inlink is None:
        return False
    return (
        len(inlink.vehicles) > 0
        and veh == inlink.vehicles[0]
        and (
            len(outlink.vehicles) < outlink.number_of_lanes
            or outlink.vehicles[-outlink.number_of_lanes].x
            > outlink.delta_per_lane * node.W.DELTAN
        )
        and outlink.capacity_in_remain >= node.W.DELTAN
        and inlink.capacity_out_remain >= node.W.DELTAN
        and node.flow_capacity_remain >= node.W.DELTAN
    )


def _local_diff_transfer_conditions(veh, node):
    inlink = veh.link
    outlink = veh.route_next_link
    clearance_required, clearance_satisfied = _local_diff_clearance_for_vehicle(
        node, veh
    )
    is_inlink_head = (
        inlink is not None
        and len(inlink.vehicles) > 0
        and inlink.vehicles[0] is veh
    )
    outlink_space_ok = False
    if outlink is not None:
        outlink_space_ok = (
            len(outlink.vehicles) < outlink.number_of_lanes
            or outlink.vehicles[-outlink.number_of_lanes].x
            > outlink.delta_per_lane * node.W.DELTAN
        )
    return {
        "clearance_required": clearance_required,
        "clearance_satisfied": clearance_satisfied,
        "is_inlink_head": is_inlink_head,
        "outlink_space_ok": outlink_space_ok,
        "outlink_capacity_in_remain_ok": (
            outlink is not None and outlink.capacity_in_remain >= node.W.DELTAN
        ),
        "inlink_capacity_out_remain_ok": (
            inlink is not None and inlink.capacity_out_remain >= node.W.DELTAN
        ),
        "node_flow_capacity_remain_ok": node.flow_capacity_remain >= node.W.DELTAN,
        "can_transfer": _local_diff_can_transfer_vehicle(veh, inlink, outlink, node),
    }


def _local_diff_target_vehicle_snapshot(veh, node):
    inlink = veh.link
    inlink_index = None
    is_inlink_head = False
    if inlink is not None and inlink.name == N1_LOCAL_DIFF_TARGET_INLINK:
        for index, queued in enumerate(inlink.vehicles):
            if queued.name == veh.name:
                inlink_index = index
                break
        is_inlink_head = inlink_index == 0
    visit_fields = _local_diff_visit_fields(veh)
    legacy_assignment = veh.order_control_batch_assignments.get(node.name)
    try:
        batch_assignment = veh.get_order_control_batch_assignment(node)
    except (ValueError, AttributeError):
        batch_assignment = visit_fields["batch_assignment"]
    at_node_end = veh.name in [v.name for v in node.incoming_vehicles]
    return {
        "W_T": veh.W.T,
        "state": veh.state,
        "link_name": _local_diff_link_name(veh.link),
        "x": veh.x,
        "v": veh.v,
        "link_arrival_time": veh.link_arrival_time,
        "route_next_link_name": _local_diff_link_name(veh.route_next_link),
        "inlink_index": inlink_index,
        "is_inlink_head": is_inlink_head,
        "at_node_end_arrived": at_node_end,
        "in_incoming_vehicles": at_node_end,
        **visit_fields,
        "batch_assignment": batch_assignment,
        "legacy_batch_assignment": legacy_assignment,
    }


def _local_diff_inlink_snapshot(link, target_vehicle_name):
    if link is None:
        return None
    vehicle_entries = []
    target_index = None
    for index, veh in enumerate(link.vehicles):
        if veh.name == target_vehicle_name:
            target_index = index
        vehicle_entries.append(
            {
                "name": veh.name,
                "x": veh.x,
                "v": veh.v,
                "state": veh.state,
            }
        )
    snapshot = {
        "link_name": link.name,
        "vehicle_names": [entry["name"] for entry in vehicle_entries],
        "vehicles": vehicle_entries,
        "target_index": target_index,
        "target_is_head": target_index == 0,
        "num_vehicles": len(link.vehicles),
    }
    for attr in (
        "capacity_out_remain",
        "capacity_in_remain",
        "outflow_capacity",
        "capacity_in",
        "capacity_out",
        "flow_capacity",
        "flow_capacity_remain",
    ):
        if hasattr(link, attr):
            snapshot[attr] = getattr(link, attr)
    if hasattr(link, "vehicles") and link.vehicles:
        tail = link.vehicles[-1]
        if tail.x == link.length:
            snapshot["tail_at_link_end"] = tail.name
    return snapshot


def _local_diff_outlink_snapshot(outlink, target_vehicle, node):
    if outlink is None:
        return None
    vehicle_names = [veh.name for veh in outlink.vehicles]
    snapshot = {
        "link_name": outlink.name,
        "vehicle_names": vehicle_names,
        "num_vehicles": len(outlink.vehicles),
        "head_vehicle": vehicle_names[0] if vehicle_names else None,
        "tail_vehicle": vehicle_names[-1] if vehicle_names else None,
        "tail_x": outlink.vehicles[-1].x if vehicle_names else None,
    }
    for attr in (
        "capacity_in_remain",
        "capacity_out_remain",
        "inflow_capacity",
        "capacity_in",
        "capacity_out",
        "flow_capacity",
        "flow_capacity_remain",
        "number_of_lanes",
        "delta_per_lane",
    ):
        if hasattr(outlink, attr):
            snapshot[attr] = getattr(outlink, attr)
    if target_vehicle is not None:
        snapshot["target_acceptance_conditions"] = _local_diff_transfer_conditions(
            target_vehicle, node
        )
    return snapshot


def _local_diff_fcfs_evaluations(node):
    candidates = [
        veh
        for veh in node.incoming_vehicles
        if veh.route_next_link is not None
    ]
    candidates.sort(key=lambda veh: veh.get_order_control_fcfs_rank_key(node))
    evaluations = []
    stopped_by_clearance = False
    for veh in candidates:
        rank_key = veh.get_order_control_fcfs_rank_key(node)
        conditions = _local_diff_transfer_conditions(veh, node)
        entry = {
            "vehicle_name": veh.name,
            "rank_key": rank_key,
            "inlink_name": _local_diff_link_name(veh.link),
            "outlink_name": _local_diff_link_name(veh.route_next_link),
            **conditions,
        }
        evaluations.append(entry)
        if conditions["clearance_required"] and not conditions["clearance_satisfied"]:
            stopped_by_clearance = True
            break
    return {
        "candidate_names": [entry["vehicle_name"] for entry in evaluations],
        "evaluations": evaluations,
        "stopped_by_clearance": stopped_by_clearance,
    }


def _local_diff_target_service_unit(node, target_vehicle_name):
    for queue_index, unit in enumerate(node.order_control_batch_service_queue):
        vehicle_names = [veh.name for veh in unit["vehicles"]]
        if target_vehicle_name not in vehicle_names:
            continue
        head_vehicle = unit["vehicles"][0]
        head_conditions = _local_diff_transfer_conditions(head_vehicle, node)
        return {
            "queue_index": queue_index,
            "is_head_service_unit": queue_index == 0,
            "is_head_vehicle_in_unit": head_vehicle.name == target_vehicle_name,
            "batch_id": unit["batch_id"],
            "inlink_name": unit["inlink"].name,
            "vehicle_names": vehicle_names,
            "visit_ids": list(unit["visit_ids"]),
            "head_vehicle_name": head_vehicle.name,
            "head_in_incoming": head_vehicle in node.incoming_vehicles,
            "head_transfer_conditions": head_conditions,
        }
    return None


def _local_diff_serialize_inlink_groups(groups):
    return [
        {
            "inlink": inlink.name,
            "vehicles": [veh.name for veh in vehicles],
        }
        for inlink, vehicles in (groups or [])
    ]


def _local_diff_batch_evaluations(node, target_vehicle):
    trigger_candidates = node.get_order_control_batch_trigger_candidates()
    trigger_names = [veh.name for veh in trigger_candidates]
    target_trigger_index = None
    target_t_trigger = None
    if target_vehicle in trigger_candidates:
        target_trigger_index = trigger_names.index(target_vehicle.name)
        target_t_trigger = node.estimate_order_control_batch_t_trigger_level_1(
            target_vehicle
        )

    batch_candidates_by_inlink = None
    ordered_groups = None
    selected_groups = None
    if trigger_candidates:
        trigger_vehicle = trigger_candidates[0]
        t_trigger = node.estimate_order_control_batch_t_trigger_level_1(
            trigger_vehicle
        )
        candidates_by_inlink = node.get_order_control_batch_candidates_by_inlink(
            t_trigger
        )
        ordered_groups = node.get_ordered_order_control_batch_candidates_by_inlink(
            candidates_by_inlink,
            trigger_vehicle,
        )
        selected_groups = node.apply_order_control_batch_max_size(
            ordered_groups,
            node.batch_size,
        )
        batch_candidates_by_inlink = {
            inlink.name: [veh.name for veh in vehicles]
            for inlink, vehicles in candidates_by_inlink.items()
        }

    service_queue = []
    for unit in node.order_control_batch_service_queue:
        service_queue.append(
            {
                "batch_id": unit["batch_id"],
                "inlink": unit["inlink"].name,
                "vehicles": [veh.name for veh in unit["vehicles"]],
                "visit_ids": list(unit["visit_ids"]),
            }
        )

    return {
        "trigger_candidate_names": trigger_names,
        "trigger_rank_keys": [
            veh.get_order_control_batch_trigger_rank_key(node)
            for veh in trigger_candidates
        ],
        "target_is_trigger_candidate": target_vehicle.name in trigger_names,
        "target_trigger_index": target_trigger_index,
        "target_t_trigger_level_1": target_t_trigger,
        "batch_candidates_by_inlink": batch_candidates_by_inlink,
        "ordered_candidate_groups": _local_diff_serialize_inlink_groups(ordered_groups),
        "selected_candidate_groups": _local_diff_serialize_inlink_groups(
            selected_groups
        ),
        "service_queue": service_queue,
        "target_service_unit": _local_diff_target_service_unit(
            node, target_vehicle.name
        ),
    }


def _local_diff_node_pre_transfer_snapshot(node, target_vehicle, mode):
    clearance_required, clearance_satisfied = _local_diff_clearance_for_vehicle(
        node, target_vehicle
    )
    same_last_inlink = (
        node.last_order_control_inlink is not None
        and target_vehicle.link is not None
        and target_vehicle.link == node.last_order_control_inlink
    )
    snapshot = {
        "W_T": node.W.T,
        "snapshot_phase": "pre-transfer at W.T (before node.transfer in exec_simulation)",
        "incoming_vehicle_names": [veh.name for veh in node.incoming_vehicles],
        "incoming_inlink_names": [
            _local_diff_link_name(veh.link) for veh in node.incoming_vehicles
        ],
        "incoming_route_next_links": [
            _local_diff_link_name(veh.route_next_link)
            for veh in node.incoming_vehicles
        ],
        "last_order_control_inlink": _local_diff_link_name(
            node.last_order_control_inlink
        ),
        "last_order_control_entry_timestep": node.last_order_control_entry_timestep,
        "clearance_timesteps": node.order_control_clearance_timesteps,
        "target_same_last_inlink": same_last_inlink,
        "target_clearance_required": clearance_required,
        "target_clearance_satisfied": clearance_satisfied,
        "flow_capacity": node.flow_capacity,
        "flow_capacity_remain": node.flow_capacity_remain,
        "target_vehicle": _local_diff_target_vehicle_snapshot(target_vehicle, node),
    }
    if mode == "FCFS":
        snapshot["fcfs"] = _local_diff_fcfs_evaluations(node)
        snapshot["fcfs_candidate_names"] = snapshot["fcfs"]["candidate_names"]
        target_name = target_vehicle.name
        fcfs_names = snapshot["fcfs_candidate_names"]
        snapshot["target_fcfs_candidate_index"] = (
            fcfs_names.index(target_name) if target_name in fcfs_names else None
        )
    else:
        snapshot["batch"] = _local_diff_batch_evaluations(node, target_vehicle)
        snapshot["batch_trigger_candidate_names"] = snapshot["batch"][
            "trigger_candidate_names"
        ]
    return snapshot


def _local_diff_vehicles_near_node(node):
    names = set()
    for veh in node.incoming_vehicles:
        names.add(veh.name)
    for inlink in node.inlinks.values():
        for veh in inlink.vehicles:
            names.add(veh.name)
    return names


def _local_diff_detect_pass_events(
    node, link_before, inlink_names, outlink_names, mode, timestep
):
    events = []
    order = 0
    for name, previous_link_name in sorted(link_before.items()):
        veh = node.W.VEHICLES.get(name)
        if veh is None:
            continue
        current_link_name = _local_diff_link_name(veh.link)
        if (
            previous_link_name in inlink_names
            and current_link_name in outlink_names
        ):
            order += 1
            visit_id = None
            visit = veh.order_control_current_visit
            if visit is not None:
                visit_id = visit["visit_id"]
            events.append(
                {
                    "timestep": timestep,
                    "vehicle_name": name,
                    "inlink": previous_link_name,
                    "outlink": current_link_name,
                    "order_in_timestep": order,
                    "visit_id": visit_id,
                    "mode": mode,
                }
            )
    return events


def _run_stepwise_local_difference_trace(build_world_fn, mode_label):
    started = time.perf_counter()
    W, eligible_node_names = build_world_fn(run_simulation=False)
    if W.finalized == 0:
        W.finalize_scenario()
    node = W.get_node(N1_LOCAL_DIFF_TARGET_NODE)
    inlink = W.get_link(N1_LOCAL_DIFF_TARGET_INLINK)
    outlink = W.get_link(N1_LOCAL_DIFF_TARGET_OUTLINK)
    target_vehicle = W.VEHICLES[N1_LOCAL_DIFF_TARGET_VEHICLE]
    inlink_names = {link.name for link in node.inlinks.values()}
    outlink_names = {link.name for link in node.outlinks.values()}

    window_snapshots = {}
    pass_events = []
    milestones = {
        "first_incoming_timestep": None,
        "first_fcfs_candidate_timestep": None,
        "first_trigger_candidate_timestep": None,
        "first_service_queue_timestep": None,
        "first_batch_assignment_timestep": None,
        "pass_timestep": None,
    }

    steps = 0
    max_steps = TMAX + 2
    while W.check_simulation_ongoing():
        if steps >= max_steps:
            raise AssertionError(
                f"{mode_label}: exceeded max_steps={max_steps} before completion"
            )

        timestep = W.T
        in_window = (
            N1_LOCAL_DIFF_WINDOW_START
            <= timestep
            <= N1_LOCAL_DIFF_WINDOW_END
        )

        link_before = None
        pre_snapshot = None
        if in_window:
            link_before = {
                name: _local_diff_link_name(W.VEHICLES[name].link)
                for name in _local_diff_vehicles_near_node(node)
                if name in W.VEHICLES
            }
            pre_snapshot = _local_diff_node_pre_transfer_snapshot(
                node, target_vehicle, mode_label
            )
            pre_snapshot["inlink_h_3_3_4"] = _local_diff_inlink_snapshot(
                inlink, N1_LOCAL_DIFF_TARGET_VEHICLE
            )
            pre_snapshot["outlink_h_3_4_5"] = _local_diff_outlink_snapshot(
                outlink, target_vehicle, node
            )

        W.exec_simulation(duration_t2=1)
        steps += 1

        if in_window:
            step_pass_events = _local_diff_detect_pass_events(
                node,
                link_before,
                inlink_names,
                outlink_names,
                mode_label,
                timestep,
            )
            pass_events.extend(step_pass_events)
            for event in step_pass_events:
                if (
                    event["vehicle_name"] == N1_LOCAL_DIFF_TARGET_VEHICLE
                    and milestones["pass_timestep"] is None
                ):
                    milestones["pass_timestep"] = timestep

            if pre_snapshot is not None:
                if (
                    milestones["first_incoming_timestep"] is None
                    and pre_snapshot["target_vehicle"]["in_incoming_vehicles"]
                ):
                    milestones["first_incoming_timestep"] = timestep
                if mode_label == "FCFS":
                    fcfs_index = pre_snapshot.get("target_fcfs_candidate_index")
                    if (
                        milestones["first_fcfs_candidate_timestep"] is None
                        and fcfs_index is not None
                    ):
                        milestones["first_fcfs_candidate_timestep"] = timestep
                else:
                    batch_info = pre_snapshot.get("batch", {})
                    if (
                        milestones["first_trigger_candidate_timestep"] is None
                        and batch_info.get("target_is_trigger_candidate")
                    ):
                        milestones["first_trigger_candidate_timestep"] = timestep
                    if (
                        milestones["first_service_queue_timestep"] is None
                        and batch_info.get("target_service_unit") is not None
                    ):
                        milestones["first_service_queue_timestep"] = timestep
                    if (
                        milestones["first_batch_assignment_timestep"] is None
                        and pre_snapshot["target_vehicle"].get("batch_assignment")
                        is not None
                    ):
                        milestones["first_batch_assignment_timestep"] = timestep

            record = {
                "pre_transfer_timestep": timestep,
                "post_transfer_timestep": W.T,
                "pre_transfer": pre_snapshot,
                "post_transfer_target": _local_diff_target_vehicle_snapshot(
                    target_vehicle, node
                ),
                "pass_events": step_pass_events,
            }
            window_snapshots[timestep] = record

    elapsed = time.perf_counter() - started
    results = _collect_traffic_results(W)
    completion = _collect_completion_time_summary(W, TMAX)
    return {
        "mode": mode_label,
        "elapsed_seconds": elapsed,
        "window_snapshots": window_snapshots,
        "pass_events": pass_events,
        "target_milestones": milestones,
        "results": results,
        "completion": completion,
        "eligible_node_names": sorted(eligible_node_names),
        "steps": steps,
    }


def _local_diff_comparison_row(timestep, e0_snap, e1_snap):
    e0_pre = e0_snap["pre_transfer"]
    e1_pre = e1_snap["pre_transfer"]
    e0_target = e0_pre["target_vehicle"]
    e1_target = e1_pre["target_vehicle"]
    e0_fcfs_index = e0_pre.get("target_fcfs_candidate_index")
    e1_batch = e1_pre.get("batch", {})
    e1_trigger_index = e1_batch.get("target_trigger_index")
    e1_service = e1_batch.get("target_service_unit") or {}
    e1_queue_index = e1_service.get("queue_index")
    e0_passed = any(
        event["vehicle_name"] == N1_LOCAL_DIFF_TARGET_VEHICLE
        for event in e0_snap["pass_events"]
    )
    e1_passed = any(
        event["vehicle_name"] == N1_LOCAL_DIFF_TARGET_VEHICLE
        for event in e1_snap["pass_events"]
    )
    main_diff = []
    if e0_target["link_name"] != e1_target["link_name"]:
        main_diff.append("link")
    if e0_target["in_incoming_vehicles"] != e1_target["in_incoming_vehicles"]:
        main_diff.append("incoming")
    if e0_fcfs_index != e1_trigger_index:
        main_diff.append("candidate_index")
    if e0_pre["target_clearance_satisfied"] != e1_pre["target_clearance_satisfied"]:
        main_diff.append("clearance")
    if e0_passed != e1_passed:
        main_diff.append("pass")
    return {
        "timestep": timestep,
        "fcfs_link": e0_target["link_name"],
        "batch_link": e1_target["link_name"],
        "fcfs_incoming": e0_target["in_incoming_vehicles"],
        "batch_incoming": e1_target["in_incoming_vehicles"],
        "fcfs_candidate_index": e0_fcfs_index,
        "batch_trigger_index": e1_trigger_index,
        "batch_queue_index": e1_queue_index,
        "fcfs_clearance": e0_pre["target_clearance_satisfied"],
        "batch_clearance": e1_pre["target_clearance_satisfied"],
        "fcfs_passed": e0_passed,
        "batch_passed": e1_passed,
        "main_diff": ",".join(main_diff) if main_diff else "-",
    }


def _local_diff_print_comparison_table(rows):
    print(
        "\nComparison table T=1098-1105 "
        "(pre-transfer at W.T; pass flag is transfer during that W.T):"
    )
    print(
        f"{'T':>4} {'FCFS link':>12} {'BATCH link':>12} {'FCFS inc':>8} "
        f"{'B inc':>5} {'FCFS idx':>8} {'B trg':>5} {'B que':>5} "
        f"{'FCFS clr':>8} {'B clr':>5} {'FCFS pass':>9} {'B pass':>6} "
        f"{'diff':>20}"
    )
    for row in rows:
        print(
            f"{row['timestep']:4d} "
            f"{str(row['fcfs_link']):>12} "
            f"{str(row['batch_link']):>12} "
            f"{str(row['fcfs_incoming']):>8} "
            f"{str(row['batch_incoming']):>5} "
            f"{str(row['fcfs_candidate_index']):>8} "
            f"{str(row['batch_trigger_index']):>5} "
            f"{str(row['batch_queue_index']):>5} "
            f"{str(row['fcfs_clearance']):>8} "
            f"{str(row['batch_clearance']):>5} "
            f"{str(row['fcfs_passed']):>9} "
            f"{str(row['batch_passed']):>6} "
            f"{row['main_diff']:>20}"
        )


def _local_diff_print_detail_snapshot(label, record):
    print(f"\n{label} (pre-transfer W.T={record['pre_transfer_timestep']}):")
    pre = record["pre_transfer"]
    print(f"  incoming: {pre['incoming_vehicle_names']}")
    print(f"  target: {pre['target_vehicle']}")
    if "fcfs" in pre:
        print(f"  FCFS candidates: {pre['fcfs']['candidate_names']}")
        for evaluation in pre["fcfs"]["evaluations"]:
            print(f"    FCFS eval: {evaluation}")
    if "batch" in pre:
        batch = pre["batch"]
        print(f"  BATCH trigger candidates: {batch['trigger_candidate_names']}")
        print(f"  BATCH service queue: {batch['service_queue']}")
        print(f"  BATCH target service unit: {batch['target_service_unit']}")
        print(f"  BATCH selected groups: {batch['selected_candidate_groups']}")
    print(f"  inlink h_3_3_4: {pre['inlink_h_3_3_4']}")
    print(f"  outlink h_3_4_5: {pre['outlink_h_3_4_5']}")
    print(f"  pass events this timestep: {record['pass_events']}")


def _local_diff_classify_cause(e0_trace, e1_trace):
    fcfs_pass = e0_trace["target_milestones"]["pass_timestep"]
    batch_pass = e1_trace["target_milestones"]["pass_timestep"]
    if fcfs_pass != 1103 or batch_pass != 1104:
        raise AssertionError(
            f"unexpected pass timesteps: FCFS={fcfs_pass}, BATCH={batch_pass}"
        )

    fcfs_1103 = e0_trace["window_snapshots"][1103]
    batch_1103 = e1_trace["window_snapshots"][1103]
    batch_1104 = e1_trace["window_snapshots"][1104]

    fcfs_pre = fcfs_1103["pre_transfer"]
    batch_pre = batch_1103["pre_transfer"]
    fcfs_eval = None
    for evaluation in fcfs_pre["fcfs"]["evaluations"]:
        if evaluation["vehicle_name"] == N1_LOCAL_DIFF_TARGET_VEHICLE:
            fcfs_eval = evaluation
            break
    if fcfs_eval is None:
        raise AssertionError("veh_3573 not in FCFS evaluations at T=1103")

    batch_pre_batch = batch_pre["batch"]
    batch_service = batch_pre_batch.get("target_service_unit")
    batch_1104_pre = batch_1104["pre_transfer"]
    batch_1104_service = batch_1104_pre["batch"].get("target_service_unit")

    fcfs_pass_events = fcfs_1103["pass_events"]
    batch_1103_pass_events = batch_1103["pass_events"]
    batch_1104_pass_events = batch_1104["pass_events"]

    fcfs_before_target = []
    target_order = None
    for event in fcfs_pass_events:
        if event["vehicle_name"] == N1_LOCAL_DIFF_TARGET_VEHICLE:
            target_order = event["order_in_timestep"]
            break
    if target_order is not None:
        fcfs_before_target = [
            event
            for event in fcfs_pass_events
            if event["order_in_timestep"] < target_order
        ]

    direct_fcfs_condition = (
        f"At W.T=1103 pre-transfer, veh_3573 was FCFS candidate "
        f"index {fcfs_pre.get('target_fcfs_candidate_index')} with can_transfer="
        f"{fcfs_eval['can_transfer']}; it transferred during node.transfer at "
        f"W.T=1103 (log_t_link event time 1103)."
    )

    if batch_service is None:
        direct_batch_block = (
            "At W.T=1103 pre-transfer, veh_3573 was not in the BATCH service queue; "
            f"trigger_candidate={batch_pre_batch['target_is_trigger_candidate']}, "
            f"trigger_index={batch_pre_batch.get('target_trigger_index')}, "
            f"selected_groups={batch_pre_batch.get('selected_candidate_groups')}."
        )
        if batch_pre_batch["target_is_trigger_candidate"]:
            cause = "E"
            cause_name = (
                "N=1 formation timing difference"
            )
        elif (
            batch_pre["target_vehicle"]["in_incoming_vehicles"]
            != fcfs_pre["target_vehicle"]["in_incoming_vehicles"]
        ):
            cause = "B"
            cause_name = "incoming registration difference"
        else:
            cause = "C"
            cause_name = "FCFS/BATCH candidate inclusion difference"
    else:
        head_conditions = batch_service["head_transfer_conditions"]
        if not batch_service["is_head_service_unit"]:
            direct_batch_block = (
                f"At W.T=1103 pre-transfer, veh_3573 was in service queue index "
                f"{batch_service['queue_index']} but head unit was batch_id="
                f"{batch_1103_pre['batch']['service_queue'][0]['batch_id']}."
            )
            cause = "F"
            cause_name = "service queue ordering or persistence difference"
        elif not batch_service["is_head_vehicle_in_unit"]:
            direct_batch_block = (
                "At W.T=1103 pre-transfer, veh_3573 was in head service unit but "
                f"not head vehicle; head={batch_service['head_vehicle_name']}."
            )
            cause = "F"
            cause_name = "service queue ordering or persistence difference"
        elif not batch_service["head_in_incoming"]:
            direct_batch_block = (
                "At W.T=1103 pre-transfer, head service-unit vehicle was not in "
                "incoming_vehicles (BATCH serve waits for arrival)."
            )
            cause = "E"
            cause_name = "N=1 formation timing difference"
        elif (
            head_conditions["clearance_required"]
            and not head_conditions["clearance_satisfied"]
        ):
            direct_batch_block = (
                "At W.T=1103 pre-transfer, head service unit clearance was not "
                "satisfied."
            )
            cause = "G"
            cause_name = "clearance evaluation difference"
        elif not head_conditions["can_transfer"]:
            direct_batch_block = (
                "At W.T=1103 pre-transfer, head service unit could not transfer due "
                f"to capacity/head/space checks: {head_conditions}."
            )
            if (
                head_conditions["is_inlink_head"]
                and head_conditions["outlink_space_ok"]
                and head_conditions["clearance_satisfied"]
            ):
                cause = "H"
                cause_name = "inlink/outlink/node capacity difference"
            else:
                cause = "G"
                cause_name = "clearance evaluation difference"
        else:
            direct_batch_block = (
                "At W.T=1103 pre-transfer, head service unit appeared transferable "
                "but veh_3573 did not pass in this timestep."
            )
            cause = "I"
            cause_name = "same-timestep repeated processing difference"

    batch_1104_service = batch_1104_pre["batch"].get("target_service_unit")
    direct_batch_pass = (
        f"At W.T=1104 pre-transfer, target service unit="
        f"{batch_1104_service}; veh_3573 passed during node.transfer at W.T=1104."
    )

    if (
        fcfs_pre["target_vehicle"]["in_incoming_vehicles"]
        == batch_pre["target_vehicle"]["in_incoming_vehicles"]
        and fcfs_eval["can_transfer"]
        and batch_service is None
        and batch_pre_batch["target_is_trigger_candidate"]
    ):
        cause = "E"
        cause_name = "N=1 formation timing difference"

    evidence = {
        "cause_code": cause,
        "cause_name": cause_name,
        "direct_fcfs_condition": direct_fcfs_condition,
        "direct_batch_block_at_1103": direct_batch_block,
        "direct_batch_pass_at_1104": direct_batch_pass,
        "fcfs_pass_events_T1103": fcfs_pass_events,
        "batch_pass_events_T1103": batch_1103_pass_events,
        "batch_pass_events_T1104": batch_1104_pass_events,
        "fcfs_before_target_T1103": fcfs_before_target,
    }
    return evidence


def main_n1_first_local_difference_only():
    """
    Legacy pre-fix diagnostic for commit 2b10b08 and earlier.

    Investigates the first local size-one BATCH vs FCFS timing difference
    (veh_3573 at g_3_4). Expects pre-fix E1 aggregate values and reproduces the
    T=1104 BATCH entry that was resolved to T=1103 after the zero-service fix.

    Not a normal post-fix regression mode. Re-run on post-fix code will fail the
    pre-fix aggregate assertions. Keep for historical reproduction; checkout the
    pre-fix commit to reproduce the original mismatch.
    """
    print("=" * 72)
    print("N=1 first local difference stepwise diagnostic")
    print(
        f"Target vehicle {N1_LOCAL_DIFF_TARGET_VEHICLE}, node "
        f"{N1_LOCAL_DIFF_TARGET_NODE}, window T="
        f"{N1_LOCAL_DIFF_WINDOW_START}-{N1_LOCAL_DIFF_WINDOW_END}"
    )
    print("=" * 72)
    print(
        "Timing note: snapshots labeled pre-transfer at W.T are captured immediately "
        "before W.exec_simulation(duration_t2=1) when World.T equals that value. "
        "node.transfer() runs inside that step; log_t_link event times use W.T*DELTAT "
        "at transfer time, so a transfer during the W.T=1103 iteration records event "
        "time 1103."
    )

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    reference_demand_summary = _demand_summary(
        vehicle_plans, "reference demand", TMAX
    )
    demand_ok = _demand_matches_reference(
        reference_demand_summary, reference_demand_summary
    )
    if not demand_ok:
        raise AssertionError("reference demand summary self-check failed")

    def build_fcfs_stepwise(run_simulation=False):
        return build_fcfs_world(
            vehicle_plans,
            TMAX,
            run_simulation=run_simulation,
        )

    def build_batch_stepwise(run_simulation=False):
        return build_batch_world(
            vehicle_plans,
            TMAX,
            batch_size=1,
            run_simulation=run_simulation,
        )

    e0_trace = _run_stepwise_local_difference_trace(build_fcfs_stepwise, "FCFS")
    print(f"\nE0 FCFS stepwise completed in {e0_trace['elapsed_seconds']:.1f} s")

    e1_trace = _run_stepwise_local_difference_trace(build_batch_stepwise, "BATCH")
    print(f"E1 BATCH stepwise completed in {e1_trace['elapsed_seconds']:.1f} s")

    e0_case = {
        "results": e0_trace["results"],
        "completion": e0_trace["completion"],
    }
    e1_case = {
        "results": e1_trace["results"],
        "completion": e1_trace["completion"],
    }
    _assert_known_n1_first_link_difference_aggregates(
        e0_case, EXPECTED_E0_N1_FIRST_LINK_DIFF, "E0"
    )
    _assert_known_n1_first_link_difference_aggregates(
        e1_case, EXPECTED_E1_N1_FIRST_LINK_DIFF, "E1"
    )
    print("\nKnown aggregate values reproduced exactly for E0 and E1.")

    comparison_rows = []
    for timestep in range(
        N1_LOCAL_DIFF_WINDOW_START, N1_LOCAL_DIFF_WINDOW_END + 1
    ):
        if (
            timestep not in e0_trace["window_snapshots"]
            or timestep not in e1_trace["window_snapshots"]
        ):
            raise AssertionError(f"missing window snapshot at T={timestep}")
        comparison_rows.append(
            _local_diff_comparison_row(
                timestep,
                e0_trace["window_snapshots"][timestep],
                e1_trace["window_snapshots"][timestep],
            )
        )
    _local_diff_print_comparison_table(comparison_rows)

    for detail_timestep in N1_LOCAL_DIFF_DETAIL_TIMESTEPS:
        _local_diff_print_detail_snapshot(
            f"FCFS detail T={detail_timestep}",
            e0_trace["window_snapshots"][detail_timestep],
        )
        _local_diff_print_detail_snapshot(
            f"BATCH detail T={detail_timestep}",
            e1_trace["window_snapshots"][detail_timestep],
        )

    cause = _local_diff_classify_cause(e0_trace, e1_trace)
    print("\nCause classification:")
    print(f"  code: {cause['cause_code']}")
    print(f"  name: {cause['cause_name']}")
    print(f"  FCFS direct pass condition: {cause['direct_fcfs_condition']}")
    print(
        f"  BATCH direct block at T=1103: {cause['direct_batch_block_at_1103']}"
    )
    print(f"  BATCH direct pass at T=1104: {cause['direct_batch_pass_at_1104']}")
    print(f"  FCFS pass events at T=1103: {cause['fcfs_pass_events_T1103']}")
    print(f"  BATCH pass events at T=1103: {cause['batch_pass_events_T1103']}")
    print(f"  BATCH pass events at T=1104: {cause['batch_pass_events_T1104']}")
    print(
        f"  FCFS vehicles before veh_3573 at T=1103: "
        f"{cause['fcfs_before_target_T1103']}"
    )

    print("\nTarget milestones:")
    print(f"  FCFS: {e0_trace['target_milestones']}")
    print(f"  BATCH: {e1_trace['target_milestones']}")

    print(
        "\nN=1 first local difference stepwise diagnostic completed (E0–E1)."
    )


def main_n1_first_link_difference_only():
    """
    Legacy pre-fix diagnostic for commit 2b10b08 and earlier.

    Finds the temporally earliest log_t_link difference between FCFS (E0) and
    pre-fix size-one BATCH (E1). Expects pre-fix E1 aggregates and requires at
    least one vehicle history mismatch.

    Not a normal post-fix regression mode. Post-fix code matches E0/E1 and will
    fail the mismatch requirement. Keep for historical investigation; checkout
    the pre-fix commit to reproduce the original behavior.
    """
    print("=" * 72)
    print("N=1 first link-history difference: 10,000-vehicle 6x6 grid")
    print("FCFS clearance=1 (E0) vs BATCH N=1 clearance=1 Level 1 (E1)")
    print("=" * 72)

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    reference_demand_summary = _demand_summary(
        vehicle_plans, "reference demand", TMAX
    )
    plans_by_name = {plan["name"]: plan for plan in vehicle_plans}
    print(
        f"Generated {len(vehicle_plans)} vehicle plans once "
        f"(DEMAND_GEN_SEED={DEMAND_GEN_SEED}, RANDOM_SEED={RANDOM_SEED})"
    )

    e0 = _run_fcfs_case(
        "E0",
        vehicle_plans,
        reference_demand_summary,
        collect_link_histories=True,
    )
    print(f"\nE0 FCFS completed in {e0['elapsed_seconds']:.1f} s")

    e1 = _run_n1_batch_equivalence_case(
        "E1",
        vehicle_plans,
        reference_demand_summary,
        collect_link_histories=True,
    )
    print(f"E1 BATCH N=1 completed in {e1['elapsed_seconds']:.1f} s")

    _assert_known_n1_first_link_difference_aggregates(
        e0, EXPECTED_E0_N1_FIRST_LINK_DIFF, "E0"
    )
    _assert_known_n1_first_link_difference_aggregates(
        e1, EXPECTED_E1_N1_FIRST_LINK_DIFF, "E1"
    )
    print("\nKnown aggregate values reproduced exactly for E0 and E1.")

    if e0["eligible_node_names"] != e1["eligible_node_names"]:
        raise AssertionError("eligible node names differ between E0 and E1")

    e0_histories = e0["vehicle_link_histories"]
    e1_histories = e1["vehicle_link_histories"]
    e0_names = set(e0_histories)
    e1_names = set(e1_histories)
    if e0_names != e1_names:
        raise AssertionError(
            f"vehicle name set mismatch: only E0={sorted(e0_names - e1_names)!r}, "
            f"only E1={sorted(e1_names - e0_names)!r}"
        )
    print(f"Vehicle name sets match ({len(e0_names)} vehicles).")

    comparisons = []
    link_history_match_count = 0
    route_match_count = 0
    for name in sorted(e0_names, key=_vehicle_numeric_id):
        comparison = _compare_vehicle_link_histories(
            e0_histories[name], e1_histories[name]
        )
        comparisons.append(comparison)
        if comparison["history_match"]:
            link_history_match_count += 1
        if comparison["routes_match"]:
            route_match_count += 1

    link_history_mismatch_count = len(comparisons) - link_history_match_count
    route_mismatch_count = len(comparisons) - route_match_count

    if link_history_mismatch_count == 0:
        raise AssertionError(
            "all vehicle link histories match; expected known E0/E1 mismatch"
        )

    mismatch_comparisons = [
        c for c in comparisons if not c["history_match"]
    ]
    mismatch_comparisons.sort(
        key=lambda c: (
            c["earliest_time"],
            c["vehicle_numeric_id"],
            c["first_mismatch_index"],
        )
    )
    representative = mismatch_comparisons[0]
    earliest_time = representative["earliest_time"]
    same_time_mismatches = [
        c
        for c in mismatch_comparisons
        if c["earliest_time"] == earliest_time
    ]
    same_time_mismatches.sort(
        key=lambda c: (c["vehicle_numeric_id"], c["first_mismatch_index"])
    )
    representative = same_time_mismatches[0]
    representative_name = representative["vehicle_name"]
    representative_plan = plans_by_name[representative_name]
    representative["provisional_judgment"] = _provisional_route_timing_judgment(
        representative
    )

    print("\nE0 aggregate values:")
    for field in N1_EQUIVALENCE_AGGREGATE_FIELDS:
        print(f"  {field}: {e0['results'][field]!r}")
    print("E0 completion:")
    for field in N1_EQUIVALENCE_COMPLETION_FIELDS:
        print(f"  {field}: {e0['completion'][field]!r}")

    print("\nE1 aggregate values:")
    for field in N1_EQUIVALENCE_AGGREGATE_FIELDS:
        print(f"  {field}: {e1['results'][field]!r}")
    print("E1 completion:")
    for field in N1_EQUIVALENCE_COMPLETION_FIELDS:
        print(f"  {field}: {e1['completion'][field]!r}")

    print("\nLink history comparison summary:")
    print(f"  vehicles compared: {len(comparisons)}")
    print(f"  link histories fully matching: {link_history_match_count}")
    print(f"  link histories with differences: {link_history_mismatch_count}")
    print(f"  traveled routes fully matching: {route_match_count}")
    print(f"  traveled routes with differences: {route_mismatch_count}")
    print(f"  earliest difference time: {earliest_time}")
    print(
        f"  vehicles with difference at earliest time: {len(same_time_mismatches)}"
    )
    if len(same_time_mismatches) > 1:
        preview_names = [c["vehicle_name"] for c in same_time_mismatches[:20]]
        print(f"  earliest-time vehicle preview (max 20): {preview_names}")

    print(f"\nRepresentative vehicle: {representative_name}")
    print(f"  origin: {representative_plan['origin']!r}")
    print(f"  destination: {representative_plan['destination']!r}")
    print(f"  departure time: {representative_plan['departure_time']!r}")
    print(f"  event index: {representative['first_mismatch_index']}")
    print(f"  common prefix length: {representative['prefix_length']}")
    print(f"  previous common event: {representative['prev_common_event']!r}")
    print(f"  FCFS difference event: {representative['fcfs_event']!r}")
    print(f"  BATCH difference event: {representative['batch_event']!r}")
    print(f"  difference classification: {representative['classification']}")
    print(
        "  provisional route/timing judgment "
        f"(not a root-cause conclusion): {representative['provisional_judgment']}"
    )
    print(f"  FCFS traveled route: {representative['fcfs_traveled_route']!r}")
    print(f"  BATCH traveled route: {representative['batch_traveled_route']!r}")
    print(
        f"  first traveled-route difference index: "
        f"{representative['route_first_diff_index']!r}"
    )
    print(
        f"  FCFS arrival_time / travel_time: "
        f"{e0_histories[representative_name]['arrival_time']!r} / "
        f"{e0_histories[representative_name]['travel_time']!r}"
    )
    print(
        f"  BATCH arrival_time / travel_time: "
        f"{e1_histories[representative_name]['arrival_time']!r} / "
        f"{e1_histories[representative_name]['travel_time']!r}"
    )

    link_metadata = e0["link_node_metadata"]
    for side_label, event in (
        ("FCFS", representative["fcfs_event"]),
        ("BATCH", representative["batch_event"]),
    ):
        if event is None:
            print(f"  {side_label} difference link metadata: <no event>")
            continue
        link_name = event["link_name"]
        if link_name in ("home", "end", None) or link_name not in link_metadata:
            print(
                f"  {side_label} difference link metadata: "
                f"link_name={link_name!r} (non-real link or unknown)"
            )
            continue
        meta = link_metadata[link_name]
        print(f"  {side_label} difference link: {link_name!r}")
        print(f"    start node: {meta['start_node']!r}")
        print(f"    end node: {meta['end_node']!r}")
        print(
            "    start node order-control eligible: "
            f"{meta['start_node_order_control_eligible']}"
        )
        print(
            f"    start node order_control_type: "
            f"{meta['start_node_order_control_type']!r}"
        )

    fcfs_start = (
        representative["fcfs_event"]["start_node"]
        if representative["fcfs_event"] is not None
        else None
    )
    batch_start = (
        representative["batch_event"]["start_node"]
        if representative["batch_event"] is not None
        else None
    )
    print(
        f"  FCFS/BATCH difference-event start nodes match by name: "
        f"{fcfs_start == batch_start}"
    )

    prev_common = representative["prev_common_event"]
    if prev_common is not None:
        same_link_before_diff = (
            representative["fcfs_event"] is not None
            and representative["batch_event"] is not None
            and representative["fcfs_event"]["link_name"]
            == representative["batch_event"]["link_name"]
        )
        print(
            "  before first difference, log_t_link prefix was identical: "
            f"{representative['prefix_length'] == representative['first_mismatch_index']}"
        )
        print(
            "  difference events share the same link name: "
            f"{same_link_before_diff}"
        )
        print(
            "  previous common event implies same prior link entry: "
            f"link={prev_common['link_name']!r}, time={prev_common['time']!r}"
        )
    else:
        print("  before first difference, log_t_link prefix was identical: False")
        print("  previous common event: none (difference at index 0)")

    print(
        "\nInterpretation notes (provisional, not causal):\n"
        "  - This mode identifies the temporally earliest log_t_link divergence.\n"
        "  - It does not prove whether Node.transfer ordering, route choice, or RNG "
        "caused the divergence.\n"
        "  - Whether the difference event was produced by Node.transfer cannot be "
        "determined from log_t_link alone."
    )
    print(
        f"\nE0 elapsed seconds: {e0['elapsed_seconds']:.1f}\n"
        f"E1 elapsed seconds: {e1['elapsed_seconds']:.1f}"
    )
    print("\nN=1 first link-history difference diagnostic completed (E0–E1).")


def _find_first_log_t_link_entry(history, link_name):
    for event in history["log_t_link_events"]:
        if event["link_name"] == link_name:
            return event
    return None


def _assert_n1_link_history_equivalence(e0_case, e1_case):
    e0_histories = e0_case["vehicle_link_histories"]
    e1_histories = e1_case["vehicle_link_histories"]
    if set(e0_histories) != set(e1_histories):
        raise AssertionError(
            "vehicle link-history name sets differ between E0 and E1: "
            f"E0-only={sorted(set(e0_histories) - set(e1_histories))!r}, "
            f"E1-only={sorted(set(e1_histories) - set(e0_histories))!r}"
        )

    first_mismatch = None
    for name in sorted(e0_histories):
        comparison = _compare_vehicle_link_histories(
            e0_histories[name], e1_histories[name]
        )
        if not comparison["history_match"] or not comparison["routes_match"]:
            if first_mismatch is None:
                first_mismatch = comparison
            continue

    if first_mismatch is not None:
        veh_name = first_mismatch["vehicle_name"]
        raise AssertionError(
            "vehicle link-history mismatch between E0 and E1: "
            f"vehicle={veh_name!r}, history_match={first_mismatch['history_match']!r}, "
            f"routes_match={first_mismatch['routes_match']!r}, "
            f"first_mismatch_index={first_mismatch['first_mismatch_index']!r}, "
            f"fcfs_event={first_mismatch['fcfs_event']!r}, "
            f"batch_event={first_mismatch['batch_event']!r}"
        )

    return len(e0_histories)


def _assert_veh_3573_reformation_fix_resolved(e0_case, e1_case):
    veh_name = N1_LOCAL_DIFF_TARGET_VEHICLE
    outlink = N1_LOCAL_DIFF_TARGET_OUTLINK
    expected_entry_time = 1103

    e0_hist = e0_case["vehicle_link_histories"][veh_name]
    e1_hist = e1_case["vehicle_link_histories"][veh_name]
    comparison = _compare_vehicle_link_histories(e0_hist, e1_hist)
    if not comparison["history_match"]:
        raise AssertionError(
            f"{veh_name}: log_t_link histories still differ after reformation fix: "
            f"first_mismatch_index={comparison['first_mismatch_index']!r}, "
            f"fcfs_event={comparison['fcfs_event']!r}, "
            f"batch_event={comparison['batch_event']!r}"
        )
    if not comparison["routes_match"]:
        raise AssertionError(
            f"{veh_name}: traveled routes still differ after reformation fix: "
            f"E0={comparison['fcfs_traveled_route']!r}, "
            f"E1={comparison['batch_traveled_route']!r}"
        )

    e0_entry = _find_first_log_t_link_entry(e0_hist, outlink)
    e1_entry = _find_first_log_t_link_entry(e1_hist, outlink)
    if e0_entry is None or e1_entry is None:
        raise AssertionError(
            f"{veh_name}: missing {outlink!r} entry in log_t_link "
            f"(E0={e0_entry!r}, E1={e1_entry!r})"
        )
    if e0_entry["time"] != expected_entry_time:
        raise AssertionError(
            f"{veh_name}: E0 {outlink!r} entry time={e0_entry['time']!r}, "
            f"expected {expected_entry_time!r}"
        )
    if e1_entry["time"] != expected_entry_time:
        raise AssertionError(
            f"{veh_name}: E1 {outlink!r} entry time={e1_entry['time']!r}, "
            f"expected {expected_entry_time!r} (pre-fix BATCH was T=1104)"
        )
    if e0_entry != e1_entry:
        raise AssertionError(
            f"{veh_name}: {outlink!r} entry events differ: "
            f"E0={e0_entry!r}, E1={e1_entry!r}"
        )

    print(
        f"\nKnown first-difference vehicle resolved: {veh_name}\n"
        f"  node: {N1_LOCAL_DIFF_TARGET_NODE}\n"
        f"  inlink: {N1_LOCAL_DIFF_TARGET_INLINK}\n"
        f"  outlink: {outlink}\n"
        f"  E0 entry time: {e0_entry['time']}\n"
        f"  E1 entry time: {e1_entry['time']}\n"
        f"  log_t_link events match: True\n"
        f"  traveled route match: True"
    )


def _format_recheck_metric_value(value):
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _recheck_comparison_metrics(results, completion):
    return {
        "total_travel_time": results["total_travel_time"],
        "average_travel_time": results["average_travel_time"],
        "average_delay": results["average_delay"],
        "total_distance_traveled": results["total_distance_traveled"],
        "last_completed_trip_time": completion["last_completed_trip_time"],
    }


def _print_recheck_before_after(case_label, before_ref, after_metrics):
    metric_labels = [
        ("total_travel_time", "total travel time"),
        ("average_travel_time", "average travel time"),
        ("average_delay", "average delay"),
        ("total_distance_traveled", "total distance traveled"),
        ("last_completed_trip_time", "last completed trip time"),
    ]
    print(f"\n{case_label} before/after comparison:")
    for key, label in metric_labels:
        before_value = None if before_ref is None else before_ref.get(key)
        after_value = after_metrics[key]
        print(f"  {label}:")
        if before_value is None:
            print("    before: 修正前値未保存")
        else:
            print(f"    before: {_format_recheck_metric_value(before_value)}")
        print(f"    after:  {_format_recheck_metric_value(after_value)}")
        if before_value is None:
            print("    diff:   修正前値未保存")
            print("    ratio:  修正前値未保存")
        else:
            diff = after_value - before_value
            ratio = _safe_ratio(after_value, before_value)
            print(f"    diff:   {_format_recheck_metric_value(diff)}")
            if ratio is None:
                print("    ratio:  not available")
            else:
                print(f"    ratio:  {ratio:.6f}")


def _assert_recheck_case_sanity(case_result):
    results = case_result["results"]
    case_name = case_result["case_name"]
    unfinished = results["total_vehicles"] - results["completed_trips"]

    checks = {
        "total vehicles == 10000": results["total_vehicles"] == NUM_VEHICLES,
        "completed trips == 10000": results["completed_trips"] == NUM_VEHICLES,
        "completed ratio == 1.0": results["completed_ratio"] == 1.0,
        "unfinished == 0": unfinished == 0,
        "eligible node count == 36": case_result["eligible_node_count"]
        == INTERNAL_GRID_NODE_COUNT,
    }
    for label, ok in checks.items():
        if not ok:
            raise AssertionError(f"{case_name}: sanity check failed: {label}")


def _print_recheck_case_summary(case_result):
    results = case_result["results"]
    completion = case_result["completion"]
    unfinished = results["total_vehicles"] - results["completed_trips"]
    print(f"\nCase: {case_result['case_name']}")
    print(f"  batch size: {case_result['batch_size']}")
    print(f"  elapsed seconds: {case_result['elapsed_seconds']:.1f}")
    print(f"  total vehicles: {results['total_vehicles']}")
    print(f"  completed trips: {results['completed_trips']}")
    print(f"  completed ratio: {results['completed_ratio']:.3f}")
    print(f"  unfinished vehicles: {unfinished}")
    print(f"  total travel time: {results['total_travel_time']:.1f} s")
    print(f"  average travel time: {results['average_travel_time']:.1f} s")
    print(f"  average delay: {results['average_delay']:.1f} s")
    print(f"  total distance traveled: {results['total_distance_traveled']:.1f} m")
    print(
        f"  last completed trip time: {completion['last_completed_trip_time']}"
    )
    print(f"  eligible node count: {case_result['eligible_node_count']}")


def _rank_label_smaller_is_better(value_a, label_a, value_b, label_b):
    if value_a < value_b:
        return label_a
    if value_b < value_a:
        return label_b
    return "tie"


def main_batch_size_recheck_after_zero_service_fix_only():
    """
    Post-fix diagnostic (commit 2b10b08+).

    Re-runs BATCH N=10 (R10) and N=20 (R20) on the fixed codebase, compares
    post-fix results against pre-fix historical references, and reports post-fix
    R20/R10 ratios. Does not run FCFS, size-one BATCH, or signal P2–P4.
    """
    print("=" * 72)
    print("BATCH N=10 / N=20 recheck after zero-service reformation fix")
    print("10,000-vehicle 6x6 grid, free route, clearance=1, t_trigger Level 1")
    print("=" * 72)
    print("\nNot run in this mode:")
    print("  - FCFS (E0)")
    print("  - N=1 BATCH (E1)")
    print("  - signal P2, P3, P4")
    print("  - 200-vehicle fixed-route diagnostic")

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    reference_demand_summary = _demand_summary(
        vehicle_plans, "reference demand", TMAX
    )
    print(
        f"\nGenerated {len(vehicle_plans)} vehicle plans once "
        f"(DEMAND_GEN_SEED={DEMAND_GEN_SEED}, RANDOM_SEED={RANDOM_SEED})"
    )
    print(
        f"  first departure: {reference_demand_summary['first_departure_time']}, "
        f"last departure: {reference_demand_summary['last_departure_time']}"
    )
    print(
        f"  minimum OD Manhattan distance: "
        f"{reference_demand_summary['minimum_od_manhattan_distance']}"
    )
    print(
        f"  average OD Manhattan distance: "
        f"{reference_demand_summary['average_od_manhattan_distance']:.3f}"
    )

    if not _demand_matches_reference(
        reference_demand_summary, reference_demand_summary
    ):
        raise AssertionError("demand summary self-check failed")

    r10 = _run_batch_case(
        "R10", vehicle_plans, reference_demand_summary, batch_size=10
    )
    _print_recheck_case_summary(r10)

    r20 = _run_batch_case(
        "R20", vehicle_plans, reference_demand_summary, batch_size=20
    )
    _print_recheck_case_summary(r20)

    _assert_recheck_case_sanity(r10)
    _assert_recheck_case_sanity(r20)
    if r10["eligible_node_names"] != r20["eligible_node_names"]:
        raise AssertionError(
            "R10 and R20 eligible node name sets do not match"
        )

    print("\nEligible node names (R10 and R20 identical):")
    print(f"  count: {len(r10['eligible_node_names'])}")
    print(f"  names: {', '.join(r10['eligible_node_names'])}")

    r10_after = _recheck_comparison_metrics(r10["results"], r10["completion"])
    r20_after = _recheck_comparison_metrics(r20["results"], r20["completion"])

    _print_recheck_before_after(
        "R10", REFERENCE_BATCH_N10_PRE_ZERO_SERVICE_FIX, r10_after
    )
    _print_recheck_before_after(
        "R20", REFERENCE_BATCH_N20_P1_PRE_FIX, r20_after
    )

    print("\nPost-fix R20 / R10 ratios:")
    post_fix_metrics = [
        ("total_travel_time", "total travel time"),
        ("average_travel_time", "average travel time"),
        ("average_delay", "average delay"),
        ("total_distance_traveled", "total distance traveled"),
        ("last_completed_trip_time", "last completed trip time"),
    ]
    for key, label in post_fix_metrics:
        ratio = _safe_ratio(r20_after[key], r10_after[key])
        if ratio is None:
            print(f"  {label} ratio: not available")
        else:
            print(f"  {label} ratio: {ratio:.6f}")

    print("\nPost-fix ranking (smaller is better):")
    avg_tt_winner = _rank_label_smaller_is_better(
        r10_after["average_travel_time"],
        "R10",
        r20_after["average_travel_time"],
        "R20",
    )
    avg_delay_winner = _rank_label_smaller_is_better(
        r10_after["average_delay"],
        "R10",
        r20_after["average_delay"],
        "R20",
    )
    total_dist_winner = _rank_label_smaller_is_better(
        r10_after["total_distance_traveled"],
        "R10",
        r20_after["total_distance_traveled"],
        "R20",
    )
    print(f"  average travel time: {avg_tt_winner}")
    print(f"  average delay: {avg_delay_winner}")
    print(f"  total distance traveled: {total_dist_winner}")

    pre_fix_n20_worse_avg_tt = (
        REFERENCE_BATCH_N20_P1_PRE_FIX["average_travel_time"]
        > REFERENCE_BATCH_N10_PRE_ZERO_SERVICE_FIX["average_travel_time"]
    )
    post_fix_n20_worse_avg_tt = (
        r20_after["average_travel_time"] > r10_after["average_travel_time"]
    )
    pre_fix_n20_worse_dist = (
        REFERENCE_BATCH_N20_P1_PRE_FIX["total_distance_traveled"]
        > REFERENCE_BATCH_N10_PRE_ZERO_SERVICE_FIX["total_distance_traveled"]
    )
    post_fix_n20_worse_dist = (
        r20_after["total_distance_traveled"]
        > r10_after["total_distance_traveled"]
    )
    if pre_fix_n20_worse_avg_tt == post_fix_n20_worse_avg_tt:
        print(
            "\nPre-fix N=20 worsening tendency (higher average travel time than "
            "N=10) is maintained after the fix."
        )
    else:
        print(
            "\nPre-fix N=20 worsening tendency on average travel time is NOT "
            "maintained after the fix (ranking reversed or tied)."
        )
    if pre_fix_n20_worse_dist == post_fix_n20_worse_dist:
        print(
            "Pre-fix N=20 higher total distance than N=10 is maintained after "
            "the fix."
        )
    else:
        print(
            "Pre-fix N=20 higher total distance than N=10 is NOT maintained "
            "after the fix (ranking reversed or tied)."
        )

    print(
        "\nInterpretation notes (exploratory, single seed / single demand):\n"
        "  - Before the fix, a formed batch that served zero vehicles in the "
        "same timestep did not trigger additional formation on other inlinks.\n"
        "  - After the fix, additional formation can occur when clearance stop "
        "and arrival-wait stop do not apply and unassigned trigger candidates "
        "remain on non-blocked inlinks.\n"
        "  - Aggregate changes may reflect idle timesteps, queue state, route "
        "choice, total distance, and travel time feedback — not only direct "
        "zero-service reformation counts.\n"
        "  - This run does not count additional-formation events and does not "
        "identify dominant nodes.\n"
        "  - This is not a formal sensitivity analysis, causal estimate, or "
        "general optimality result for N=10 or N=20."
    )
    print(
        "\nGrid 10000 BATCH N=10/N=20 recheck after zero-service fix passed "
        "(R10–R20)."
    )


def main_n1_equivalence_after_reformation_fix_only():
    """
    Post-fix strict regression (commit 2b10b08+).

    Confirms size-one BATCH vs FCFS equivalence on 10,000 vehicles including
    per-vehicle routes, log_t_link histories, and veh_3573 h_3_4_5 entry at
    T=1103. Does not run P1–P4.
    """
    print("=" * 72)
    print("N=1 equivalence after zero-service reformation fix")
    print("10,000-vehicle 6x6 grid, free route")
    print("FCFS clearance=1 (E0) vs BATCH N=1 clearance=1 Level 1 (E1)")
    print("=" * 72)

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    reference_demand_summary = _demand_summary(
        vehicle_plans, "reference demand", TMAX
    )
    print(
        f"Generated {len(vehicle_plans)} vehicle plans once "
        f"(DEMAND_GEN_SEED={DEMAND_GEN_SEED}, RANDOM_SEED={RANDOM_SEED})"
    )
    print(
        f"  first departure: {reference_demand_summary['first_departure_time']}, "
        f"last departure: {reference_demand_summary['last_departure_time']}"
    )

    e0 = _run_fcfs_case(
        "E0", vehicle_plans, reference_demand_summary, collect_link_histories=True
    )
    print(
        f"\nCase E0 completed in {e0['elapsed_seconds']:.1f} s "
        f"(FCFS clearance=1, eligible nodes={len(e0['eligible_node_names'])})"
    )

    e1 = _run_n1_batch_equivalence_case(
        "E1", vehicle_plans, reference_demand_summary, collect_link_histories=True
    )
    print(
        f"Case E1 completed in {e1['elapsed_seconds']:.1f} s "
        f"(BATCH N=1 clearance=1 Level 1, eligible nodes={len(e1['eligible_node_names'])})"
    )

    _assert_known_n1_first_link_difference_aggregates(
        e0, EXPECTED_E0_N1_FIRST_LINK_DIFF, "E0"
    )
    print("E0 aggregate values match pre-fix FCFS reference values.")

    _assert_n1_equivalence(e0, e1)
    matched_vehicle_count = _assert_n1_link_history_equivalence(e0, e1)
    print(
        f"Per-vehicle traveled route and normalized log_t_link equivalence: "
        f"{matched_vehicle_count} vehicles"
    )
    _assert_veh_3573_reformation_fix_resolved(e0, e1)
    print("\nGrid 10000 N=1 equivalence after reformation fix passed (E0–E1).")


def main_n1_equivalence_only():
    """
    Lightweight post-fix size-one BATCH vs FCFS check on 10,000 vehicles.

    Compares aggregate metrics and per-vehicle state snapshots only. For the
    stronger post-fix regression that also checks routes, log_t_link, and
    veh_3573 resolution, use --n1-equivalence-after-reformation-fix-only.
    """
    print("=" * 72)
    print("N=1 equivalence check: 10,000-vehicle 6x6 grid")
    print("FCFS clearance=1 (E0) vs BATCH N=1 clearance=1 Level 1 (E1)")
    print("=" * 72)

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    reference_demand_summary = _demand_summary(
        vehicle_plans, "reference demand", TMAX
    )
    print(
        f"Generated {len(vehicle_plans)} vehicle plans once "
        f"(DEMAND_GEN_SEED={DEMAND_GEN_SEED}, RANDOM_SEED={RANDOM_SEED})"
    )
    print(
        f"  first departure: {reference_demand_summary['first_departure_time']}, "
        f"last departure: {reference_demand_summary['last_departure_time']}"
    )

    e0 = _run_fcfs_case("E0", vehicle_plans, reference_demand_summary)
    print(
        f"\nCase E0 completed in {e0['elapsed_seconds']:.1f} s "
        f"(FCFS clearance=1, eligible nodes={len(e0['eligible_node_names'])})"
    )

    e1 = _run_n1_batch_equivalence_case("E1", vehicle_plans, reference_demand_summary)
    print(
        f"Case E1 completed in {e1['elapsed_seconds']:.1f} s "
        f"(BATCH N=1 clearance=1 Level 1, eligible nodes={len(e1['eligible_node_names'])})"
    )

    _assert_n1_equivalence(e0, e1)
    print("\nGrid 10000 N=1 equivalence check passed (E0–E1).")


def main():
    print("=" * 72)
    print("Preliminary exploratory check: 10,000-vehicle grid")
    print("Default run: BATCH size and signal timing P1–P4")
    print("=" * 72)
    print(
        "\nSignal phase mapping:\n"
        "  phase 0 / signal_group 0: east-west\n"
        "  phase 1: no links — all-red equivalent\n"
        "  phase 2 / signal_group 2: north-south\n"
        "  phase 3: no links — all-red equivalent\n"
    )
    print(f"Staggered offset strategy: {SIGNAL_OFFSET_STRATEGY}\n")

    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    reference_demand_summary = _demand_summary(
        vehicle_plans, "reference demand", TMAX
    )
    print(
        f"Generated {len(vehicle_plans)} vehicle plans once "
        f"(DEMAND_GEN_SEED={DEMAND_GEN_SEED}, RANDOM_SEED={RANDOM_SEED})"
    )
    print(
        f"  first departure: {reference_demand_summary['first_departure_time']}, "
        f"last departure: {reference_demand_summary['last_departure_time']}"
    )

    case_results = []

    p1 = _run_batch_case(
        "P1", vehicle_plans, reference_demand_summary, batch_size=20
    )
    case_results.append(p1)
    print("\n" + _format_case_report(p1))

    p2 = _run_signalized_case(
        "P2", vehicle_plans, reference_demand_summary, green_ew=30, green_ns=30
    )
    case_results.append(p2)
    print("\n" + _format_case_report(p2))

    p3 = _run_signalized_case(
        "P3", vehicle_plans, reference_demand_summary, green_ew=60, green_ns=30
    )
    case_results.append(p3)
    print("\n" + _format_case_report(p3))

    p4 = _run_signalized_case(
        "P4", vehicle_plans, reference_demand_summary, green_ew=30, green_ns=60
    )
    case_results.append(p4)
    print("\n" + _format_case_report(p4))

    ref_batch_post = REFERENCE_BATCH_N10_POST_ZERO_SERVICE_FIX
    ref_batch_pre = REFERENCE_BATCH_N10_PRE_ZERO_SERVICE_FIX
    ref_signal = REFERENCE_SIGNAL_60_1_60_1
    p1_results = p1["results"]

    print("\nComparison ratios:")
    print(
        "P1 (BATCH N=20) vs current BATCH N=10 baseline "
        "(post zero-service fix, commit 2b10b08+):"
    )
    print(
        f"  total travel time ratio: "
        f"{_safe_ratio(p1_results['total_travel_time'], ref_batch_post['total_travel_time'])}"
    )
    print(
        f"  average travel time ratio: "
        f"{_safe_ratio(p1_results['average_travel_time'], ref_batch_post['average_travel_time'])}"
    )
    delay_ratio_post = _safe_ratio(
        p1_results["average_delay"], ref_batch_post.get("average_delay")
    )
    if delay_ratio_post is None:
        print(
            "  average delay ratio: not available "
            "(post-fix N=10 average_delay not stored at full precision)"
        )
    else:
        print(f"  average delay ratio: {delay_ratio_post}")
    print(
        f"  total distance traveled ratio: "
        f"{_safe_ratio(p1_results['total_distance_traveled'], ref_batch_post['total_distance_traveled'])}"
    )
    p1_completion = p1["completion"]
    print(
        f"  last completed trip time ratio: "
        f"{_safe_ratio(p1_completion['last_completed_trip_time'], ref_batch_post['last_completed_trip_time'])}"
    )
    print(
        "\nHistorical comparison vs pre-zero-service-fix BATCH N=10 "
        "(commit 2b10b08 before):"
    )
    print(
        f"  total travel time ratio: "
        f"{_safe_ratio(p1_results['total_travel_time'], ref_batch_pre['total_travel_time'])}"
    )
    print(
        f"  average travel time ratio: "
        f"{_safe_ratio(p1_results['average_travel_time'], ref_batch_pre['average_travel_time'])}"
    )
    print("P1 (BATCH N=20) vs reference signal [60,1,60,1]:")
    print(
        f"  average travel time ratio: "
        f"{_safe_ratio(p1_results['average_travel_time'], ref_signal['average_travel_time'])}"
    )

    for case in case_results[1:]:
        results = case["results"]
        print(f"\n{case['case_name']} vs reference signal [60,1,60,1]:")
        print(
            f"  average travel time ratio: "
            f"{_safe_ratio(results['average_travel_time'], ref_signal['average_travel_time'])}"
        )
        print(
            f"  total travel time ratio: "
            f"{_safe_ratio(results['total_travel_time'], ref_signal['total_travel_time'])}"
        )
        print(
            f"  distance ratio: "
            f"{_safe_ratio(results['total_distance_traveled'], ref_signal['total_distance_traveled'])}"
        )
        print(
            f"  current BATCH N=10 (post-fix) / {case['case_name']} "
            f"average travel time ratio: "
            f"{_safe_ratio(ref_batch_post['average_travel_time'], results['average_travel_time'])}"
        )
        print(f"  P1 BATCH N=20 / {case['case_name']} average travel time ratio: "
              f"{_safe_ratio(p1_results['average_travel_time'], results['average_travel_time'])}")

    comparison_rows = [
        _reference_row(REFERENCE_FCFS_CLEARANCE_1),
        _reference_row(REFERENCE_BATCH_N10_POST_ZERO_SERVICE_FIX),
        _reference_row(REFERENCE_BATCH_N10_PRE_ZERO_SERVICE_FIX),
        _case_row(p1),
        _reference_row(REFERENCE_SIGNAL_60_1_60_1),
        _case_row(p2),
        _case_row(p3),
        _case_row(p4),
    ]
    _print_comparison_table(comparison_rows)

    signal_cases = [p2, p3, p4]
    best_signal_case = min(
        signal_cases, key=lambda c: c["results"]["average_travel_time"]
    )
    p3_avg = p3["results"]["average_travel_time"]
    p4_avg = p4["results"]["average_travel_time"]

    print("\nObserved preliminary interpretation (not causal conclusions):")
    print(
        "On this fixed 10,000-vehicle free-route grid with one seed, post-fix "
        "BATCH N=20 shows higher average travel time and total distance than "
        "post-fix BATCH N=10:"
    )
    print(
        f"  average travel time: "
        f"{_observed_change_label(p1_results['average_travel_time'], ref_batch_post['average_travel_time'])}"
    )
    dist_ratio_p1 = _safe_ratio(
        p1_results["total_distance_traveled"],
        ref_batch_post["total_distance_traveled"],
    )
    if dist_ratio_p1 is not None:
        if dist_ratio_p1 > 1.0:
            print(
                f"  total distance: N=20 is higher than post-fix N=10 "
                f"(ratio {dist_ratio_p1:.6f})"
            )
        elif dist_ratio_p1 < 1.0:
            print(
                f"  total distance: N=20 is lower than post-fix N=10 "
                f"(ratio {dist_ratio_p1:.6f})"
            )
        else:
            print("  total distance: N=20 is approximately equal to post-fix N=10")
    print(
        "  - network-wide comparison including route choice, distance, and "
        "feedback; not a pure intersection-waiting effect"
    )
    print(
        "  - not a formal sensitivity analysis and does not identify an "
        "optimal batch size"
    )
    print(
        "\nHistorical note (pre-zero-service-fix N=10 only): "
        f"average travel time ratio N=20/N=10 was "
        f"{_safe_ratio(p1_results['average_travel_time'], ref_batch_pre['average_travel_time'])} "
        f"under the old implementation"
    )

    print(
        f"Signal cases: lowest average travel time among P2–P4 is "
        f"{best_signal_case['case_name']} "
        f"(signal {best_signal_case['signal_setting']}, "
        f"avg TT {best_signal_case['results']['average_travel_time']:.1f} s)"
    )
    improved_signals = [
        c
        for c in signal_cases
        if c["results"]["average_travel_time"] < ref_signal["average_travel_time"]
    ]
    if improved_signals:
        names = ", ".join(c["case_name"] for c in improved_signals)
        print(
            f"Signal settings with lower average travel time than reference "
            f"[60,1,60,1]: {names}"
        )
    else:
        print(
            "No P2–P4 signal setting showed lower average travel time than "
            "reference [60,1,60,1]"
        )
    print(
        f"P3 vs P4 average travel time difference (P3 - P4): "
        f"{p3_avg - p4_avg:.1f} s "
        f"(P3 EW60/NS30 vs P4 EW30/NS60)"
    )
    if p3_avg != p4_avg:
        print(
            "East-west and north-south green extension produced different "
            "observed average travel times under this fixed demand."
        )

    print(
        "\nNotes:\n"
        "  - preliminary exploratory result\n"
        "  - fixed 10,000-vehicle demand and fixed seeds\n"
        "  - not a formal sensitivity analysis\n"
        "  - not an optimization result\n"
        "  - route and total-distance differences may affect travel-time comparisons\n"
        "  - no additional parameter search is implied\n"
        "  - cycle-length-based staggered offset used (not tuned for asymmetric greens)\n"
    )

    print(
        "\nGrid 10000 batch size and signal timing preliminary check passed (P1–P4)."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="10,000-vehicle grid preliminary checks"
    )
    parser.add_argument(
        "--corrected-signal-baseline-only",
        action="store_true",
        help=(
            "Run only S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1 with signal=[59,0,59,0] "
            "and cycle-length-based staggered offsets. Does not run FCFS, BATCH, "
            "or P1–P4."
        ),
    )
    parser.add_argument(
        "--batch-size-recheck-after-zero-service-fix-only",
        action="store_true",
        help=(
            "Post-fix (commit 2b10b08+): re-run BATCH N=10 and N=20, compare "
            "against pre-fix historical references, report post-fix R20/R10 "
            "ratios. Does not run FCFS, size-one BATCH, or signal P2–P4."
        ),
    )
    parser.add_argument(
        "--n1-equivalence-after-reformation-fix-only",
        action="store_true",
        help=(
            "Post-fix (commit 2b10b08+): strict E0/E1 equivalence including "
            "routes, log_t_link, and veh_3573 T=1103 resolution. No P1–P4."
        ),
    )
    parser.add_argument(
        "--n1-equivalence-only",
        action="store_true",
        help=(
            "Lightweight post-fix E0/E1 check (aggregates and vehicle state "
            "only). Stronger check: --n1-equivalence-after-reformation-fix-only. "
            "No P1–P4."
        ),
    )
    parser.add_argument(
        "--n1-first-link-difference-only",
        action="store_true",
        help=(
            "Legacy pre-fix diagnostic (commit 2b10b08 and earlier): earliest "
            "log_t_link difference investigation. Fails on post-fix code. "
            "Checkout pre-fix commit to reproduce. No P1–P4."
        ),
    )
    parser.add_argument(
        "--n1-first-local-difference-only",
        action="store_true",
        help=(
            "Legacy pre-fix diagnostic (commit 2b10b08 and earlier): stepwise "
            "veh_3573 local difference investigation. Fails on post-fix code. "
            "Checkout pre-fix commit to reproduce. No P1–P4."
        ),
    )
    args = parser.parse_args()
    if args.corrected_signal_baseline_only:
        main_corrected_signal_baseline_only()
    elif args.batch_size_recheck_after_zero_service_fix_only:
        main_batch_size_recheck_after_zero_service_fix_only()
    elif args.n1_first_local_difference_only:
        main_n1_first_local_difference_only()
    elif args.n1_first_link_difference_only:
        main_n1_first_link_difference_only()
    elif args.n1_equivalence_after_reformation_fix_only:
        main_n1_equivalence_after_reformation_fix_only()
    elif args.n1_equivalence_only:
        main_n1_equivalence_only()
    else:
        main()
