# Medium-network comparison: UXsim standard vs FCFS(clearance=0) vs
# Level 1 BATCH(clearance=0, batch_size=10).
#
# Extends the existing FCFS vs UXsim standard medium-network sanity check by
# adding BATCH as a third control mode on the same network, demand, and seeds.
# Reports traffic results for all three modes and compares BATCH with FCFS,
# especially average travel time. BATCH <= FCFS is NOT an assertion pass/fail
# condition; performance is left for human review.
#
# Level 1 BATCH here is a provisional comparison before Level 2 is implemented.
# The research design target is Level 2, with fallback to Level 1 and then
# Level 0 when needed. This test does not claim Level 1 as the final setting.
#
# Run from the repository root:
#   python tests_order_control_batch_vs_fcfs_vs_uxsim_standard_medium_network.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import random

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
NUM_VEHICLES = 500
DEPARTURE_START = 0
DEPARTURE_END = 300
TMAX = 2500
LINK_LENGTH = 400
SIDE_LINK_LENGTH = 350
UPSTREAM_LINK_LENGTH = 300
BRANCH_LINK_LENGTH = 500
FREE_FLOW_SPEED = 20
MERGE_PRIORITY = 1
MIN_ELIGIBLE_NODES = 10
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

ORIGIN_NODES = ["u1", "u2", "s1", "s1b", "s2", "s3", "s4a", "s5", "s6", "s7", "s8"]
DESTINATION_NODES = ["d3", "d5", "d7", "d_main"]


def _generate_vehicle_plans():
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    for index in range(NUM_VEHICLES):
        departure_time = DEPARTURE_START + (DEPARTURE_END - DEPARTURE_START) * index / max(
            NUM_VEHICLES - 1, 1
        )
        plans.append(
            {
                "origin": rng.choice(ORIGIN_NODES),
                "destination": rng.choice(DESTINATION_NODES),
                "departure_time": departure_time,
                "name": f"veh_{index}",
            }
        )
    return plans


def _demand_summary(vehicle_plans):
    origins = [plan["origin"] for plan in vehicle_plans]
    destinations = [plan["destination"] for plan in vehicle_plans]
    departure_times = [plan["departure_time"] for plan in vehicle_plans]
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
        "origin_sequence": origins,
        "destination_sequence": destinations,
        "departure_time_sequence": departure_times,
    }


def _add_medium_network(W):
    node_coords = {
        "u1": (0, 0),
        "u2": (0, 2),
        "m0": (1, 1),
        "s1": (1, 3),
        "m1": (2, 1),
        "s1b": (2, 3),
        "j2": (3, 1),
        "s2": (3, 3),
        "m2": (4, 1),
        "s3": (4, 3),
        "m3": (5, 1),
        "j4": (6, 1),
        "s4a": (6, 3),
        "m5": (7, 1),
        "s5": (7, 3),
        "m6": (8, 1),
        "s6": (8, 3),
        "m7": (9, 1),
        "s7": (9, 3),
        "m8": (10, 1),
        "s8": (10, 3),
        "m9": (11, 1),
        "d3": (5, 5),
        "d5": (7, 5),
        "d7": (9, 5),
        "d_main": (12, 1),
    }
    for name, (x, y) in node_coords.items():
        W.addNode(name, x, y)

    def add_link(link_name, start_node, end_node, length):
        W.addLink(
            link_name,
            start_node,
            end_node,
            length=length,
            free_flow_speed=FREE_FLOW_SPEED,
            number_of_lanes=1,
            merge_priority=MERGE_PRIORITY,
        )

    add_link("l_u1_m0", "u1", "m0", UPSTREAM_LINK_LENGTH)
    add_link("l_u2_m0", "u2", "m0", UPSTREAM_LINK_LENGTH)

    corridor_pairs = [
        ("m0", "m1"),
        ("m1", "j2"),
        ("j2", "m2"),
        ("m2", "m3"),
        ("m3", "j4"),
        ("j4", "m5"),
        ("m5", "m6"),
        ("m6", "m7"),
        ("m7", "m8"),
        ("m8", "m9"),
    ]
    for start_node, end_node in corridor_pairs:
        add_link(f"l_{start_node}_{end_node}", start_node, end_node, LINK_LENGTH)

    side_pairs = [
        ("s1", "m1"),
        ("s1b", "j2"),
        ("s2", "m2"),
        ("s3", "m3"),
        ("s4a", "j4"),
        ("s5", "m5"),
        ("s6", "m6"),
        ("s7", "m7"),
        ("s8", "m8"),
    ]
    for start_node, end_node in side_pairs:
        add_link(f"l_{start_node}_{end_node}", start_node, end_node, SIDE_LINK_LENGTH)

    add_link("l_m3_d3", "m3", "d3", BRANCH_LINK_LENGTH)
    add_link("l_m5_d5", "m5", "d5", BRANCH_LINK_LENGTH)
    add_link("l_m7_d7", "m7", "d7", BRANCH_LINK_LENGTH)
    add_link("l_m9_dmain", "m9", "d_main", BRANCH_LINK_LENGTH)


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
        name=f"batch_fcfs_standard_{control_mode}",
        deltan=1,
        tmax=TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_medium_network(W)
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


def _format_demand_summary(summary):
    return (
        "Demand summary:\n"
        f"- total vehicles: {summary['total_vehicles']}\n"
        f"- first departure time: {summary['first_departure_time']}\n"
        f"- last departure time: {summary['last_departure_time']}\n"
        f"- demand duration: {summary['demand_duration']}\n"
        f"- average departure interval: {summary['average_departure_interval']}\n"
        f"- vehicles per timestep: {summary['vehicles_per_timestep']}"
    )


def _format_ratio_block(title, ratios):
    return (
        f"{title}:\n"
        f"- completed ratio difference: {ratios['completed_ratio_difference']:.3f}\n"
        f"- average travel time ratio: {ratios['average_travel_time_ratio']}\n"
        f"- total travel time ratio: {ratios['total_travel_time_ratio']}\n"
        f"- total distance traveled ratio: {ratios['total_distance_traveled_ratio']}"
    )


def _batch_vs_fcfs_travel_time_interpretation(batch_results, fcfs_results):
    batch_avg = batch_results["average_travel_time"]
    fcfs_avg = fcfs_results["average_travel_time"]
    if batch_avg < fcfs_avg:
        return "lower"
    if batch_avg > fcfs_avg:
        return "higher"
    return "equal"


def _build_report_context(
    *,
    demand_summary,
    standard_results,
    fcfs_results,
    batch_results,
    fcfs_eligible_node_names,
    batch_eligible_node_names,
    fcfs_vs_standard_ratios,
    batch_vs_standard_ratios,
    batch_vs_fcfs_ratios,
    batch_vs_fcfs_travel_time_interpretation,
    sanity_checks,
):
    eligible_match = fcfs_eligible_node_names == batch_eligible_node_names
    return (
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


def test_batch_level1_clearance_zero_vs_fcfs_vs_uxsim_standard_medium_network():
    vehicle_plans = _generate_vehicle_plans()
    demand_summary = _demand_summary(vehicle_plans)

    standard_W, _ = build_world("standard", vehicle_plans)
    standard_results = _collect_traffic_results(standard_W)

    fcfs_W, fcfs_eligible = build_world("fcfs", vehicle_plans)
    fcfs_results = _collect_traffic_results(fcfs_W)

    batch_W, batch_eligible = build_world("batch", vehicle_plans)
    batch_results = _collect_traffic_results(batch_W)

    fcfs_vs_standard_ratios = _comparison_ratios(fcfs_results, standard_results)
    batch_vs_standard_ratios = _comparison_ratios(batch_results, standard_results)
    batch_vs_fcfs_ratios = _comparison_ratios(batch_results, fcfs_results)
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
        else "fail"
    )
    sanity_checks["fcfs eligible node count >= 10"] = (
        "pass" if len(fcfs_eligible) >= MIN_ELIGIBLE_NODES else "fail"
    )
    sanity_checks["batch eligible node count >= 10"] = (
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
        demand_summary=demand_summary,
        standard_results=standard_results,
        fcfs_results=fcfs_results,
        batch_results=batch_results,
        fcfs_eligible_node_names=fcfs_eligible,
        batch_eligible_node_names=batch_eligible,
        fcfs_vs_standard_ratios=fcfs_vs_standard_ratios,
        batch_vs_standard_ratios=batch_vs_standard_ratios,
        batch_vs_fcfs_ratios=batch_vs_fcfs_ratios,
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
        "BATCH Level 1 vs FCFS clearance=0 vs UXsim standard medium network test passed."
    )


if __name__ == "__main__":
    test_batch_level1_clearance_zero_vs_fcfs_vs_uxsim_standard_medium_network()
