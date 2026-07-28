# Verify N=1 BATCH vs FCFS full equivalence with same-node revisit and clearance=1.
#
# Run from the repository root:
#   python tests_order_control_n1_batch_vs_fcfs_revisit_equivalence.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

RANDOM_SEED = 0
TMAX = 400
MAX_STEPS = TMAX + 50
CLEARANCE_TIMESTEPS = 1
LINK_LENGTH = 200
FREE_FLOW_SPEED = 20
LINK_TRAVEL_TIMESTEPS = LINK_LENGTH // FREE_FLOW_SPEED  # 10 with DELTAT=1

LOOP_ROUTE_NAMES = ["link1", "out", "mid_orig2", "link2", "out2"]
SHORT_ROUTE_NAMES = ["link2", "out2"]
LINK1_OUT2_ROUTE_NAMES = ["link1", "out2"]

MERGE_INLINK_NAMES = frozenset({"link1", "link2"})
MERGE_OUTLINK_NAMES = frozenset({"out", "out2"})

# Link travel is 10 timesteps per 200 m link at 20 m/s.
# Loop vehicle second merge arrival: departure + 4 * LINK_TRAVEL_TIMESTEPS.
# Link1-side competitor for revisit: departure + LINK_TRAVEL_TIMESTEPS.
VEHICLE_PLANS = [
    {
        "name": "L0",
        "origin": "orig1",
        "destination": "dest",
        "departure_time": 0,
        "route_names": LOOP_ROUTE_NAMES,
        "role": "loop",
    },
    {
        "name": "C0",
        "origin": "orig2",
        "destination": "dest",
        "departure_time": 0,
        "route_names": SHORT_ROUTE_NAMES,
        "role": "short",
    },
    {
        "name": "L1",
        "origin": "orig1",
        "destination": "dest",
        "departure_time": 20,
        "route_names": LOOP_ROUTE_NAMES,
        "role": "loop",
    },
    {
        "name": "C1",
        "origin": "orig2",
        "destination": "dest",
        "departure_time": 20,
        "route_names": SHORT_ROUTE_NAMES,
        "role": "short",
    },
    {
        "name": "R0",
        "origin": "orig1",
        "destination": "dest",
        "departure_time": 30,
        "route_names": LINK1_OUT2_ROUTE_NAMES,
        "role": "link1_revisit_competitor",
    },
    {
        "name": "R1",
        "origin": "orig1",
        "destination": "dest",
        "departure_time": 51,
        "route_names": LINK1_OUT2_ROUTE_NAMES,
        "role": "link1_revisit_competitor",
    },
]


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_world(order_control_type):
    W = World(
        name=f"n1_revisit_equiv_{order_control_type}",
        deltan=1,
        tmax=TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type=order_control_type,
        batch_size=1,
        order_control_batch_t_trigger_level=1,
    )
    W.addNode("mid", 2, 1)
    W.addNode("dest", 3, 1)
    W.addLink(
        "link1", "orig1", "merge", length=LINK_LENGTH, free_flow_speed=FREE_FLOW_SPEED, number_of_lanes=1
    )
    W.addLink(
        "link2", "orig2", "merge", length=LINK_LENGTH, free_flow_speed=FREE_FLOW_SPEED, number_of_lanes=1
    )
    W.addLink(
        "out", "merge", "mid", length=LINK_LENGTH, free_flow_speed=FREE_FLOW_SPEED, number_of_lanes=1
    )
    W.addLink(
        "mid_orig2",
        "mid",
        "orig2",
        length=LINK_LENGTH,
        free_flow_speed=FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out2", "merge", "dest", length=LINK_LENGTH, free_flow_speed=FREE_FLOW_SPEED, number_of_lanes=1
    )
    W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    if order_control_type == "batch":
        merge = W.get_node("merge")
        if merge.batch_size != 1:
            raise AssertionError(f"merge.batch_size={merge.batch_size}, expected 1")
        if merge.order_control_batch_t_trigger_level != 1:
            raise AssertionError(
                "merge.order_control_batch_t_trigger_level="
                f"{merge.order_control_batch_t_trigger_level}, expected 1"
            )
    elif order_control_type != "fcfs":
        raise AssertionError(f"Unsupported order_control_type={order_control_type!r}")
    _prepare_network(W)
    return W


def _validate_fixed_route(W, vehicle, route_names):
    if not route_names:
        raise AssertionError(
            f"{vehicle.name}: fixed route is empty for origin={vehicle.orig.name!r} "
            f"destination={vehicle.dest.name!r}"
        )

    route_links = []
    for link_name in route_names:
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


def _add_vehicles_with_fixed_routes(W, vehicle_plans):
    vehicles = {}
    for plan in vehicle_plans:
        vehicle = W.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )
        route_links = _validate_fixed_route(W, vehicle, plan["route_names"])
        vehicle.enforce_route(route_links, set_avoid=True)
        vehicles[plan["name"]] = vehicle
    return vehicles


def _link_name(link):
    if link is None:
        return None
    return link.name


def _current_visit_snapshot(visit):
    if visit is None:
        return None
    return {
        "node": visit["node"].name,
        "inlink": visit["inlink"].name,
        "visit_id": visit["visit_id"],
        "arrival_time": visit["arrival_time"],
        "arrival_tiebreaker": visit["arrival_tiebreaker"],
    }


def _incoming_vehicle_pre_transfer_entry(veh, merge):
    visit = veh.order_control_current_visit
    inlink_name = veh.link.name if veh.link is not None else None
    is_inlink_head = (
        veh.link is not None
        and len(veh.link.vehicles) > 0
        and veh.link.vehicles[0] is veh
    )
    clearance_required = (
        merge.last_order_control_inlink is not None
        and veh.link is not None
        and veh.link is not merge.last_order_control_inlink
    )
    clearance_satisfied = True
    if clearance_required and merge.last_order_control_entry_timestep is not None:
        clearance_satisfied = (
            merge.W.T - merge.last_order_control_entry_timestep
            > merge.order_control_clearance_timesteps
        )
    return {
        "name": veh.name,
        "inlink_name": inlink_name,
        "has_current_visit": visit is not None,
        "current_visit_node": visit["node"].name if visit is not None else None,
        "current_visit_inlink": visit["inlink"].name if visit is not None else None,
        "current_visit_visit_id": visit["visit_id"] if visit is not None else None,
        "has_route_next_link": veh.route_next_link is not None,
        "is_inlink_head": is_inlink_head,
        "clearance_required": clearance_required,
        "clearance_satisfied": clearance_satisfied,
    }


def _merge_pre_transfer_snapshot(merge):
    incoming_names = [veh.name for veh in merge.incoming_vehicles]
    incoming_inlinks = [
        veh.link.name if veh.link is not None else None for veh in merge.incoming_vehicles
    ]
    last_inlink = merge.last_order_control_inlink
    return {
        "timestep": merge.W.T,
        "incoming_vehicle_names": incoming_names,
        "incoming_inlink_names": incoming_inlinks,
        "incoming_vehicles": [
            _incoming_vehicle_pre_transfer_entry(veh, merge)
            for veh in merge.incoming_vehicles
        ],
        "last_order_control_inlink": last_inlink.name if last_inlink is not None else None,
        "last_order_control_entry_timestep": merge.last_order_control_entry_timestep,
    }


def _vehicle_timestep_snapshot(veh):
    visit = veh.order_control_current_visit
    return {
        "name": veh.name,
        "timestep": veh.W.T,
        "state": veh.state,
        "link_name": _link_name(veh.link),
        "link_arrival_time": veh.link_arrival_time,
        "has_current_visit": visit is not None,
        "current_visit": _current_visit_snapshot(visit),
    }


def _batch_diagnostic_snapshot(merge):
    trigger_candidates = merge.get_order_control_batch_trigger_candidates()
    service_queue = []
    for unit in merge.order_control_batch_service_queue:
        service_queue.append(
            {
                "batch_id": unit["batch_id"],
                "inlink": unit["inlink"].name,
                "vehicles": [veh.name for veh in unit["vehicles"]],
                "visit_ids": list(unit["visit_ids"]),
            }
        )
    return {
        "timestep": merge.W.T,
        "trigger_candidate_names": [veh.name for veh in trigger_candidates],
        "service_queue": service_queue,
    }


def _fcfs_candidate_order(merge):
    candidates = [
        veh
        for veh in merge.incoming_vehicles
        if veh.route_next_link is not None
    ]
    candidates.sort(key=lambda veh: veh.get_order_control_fcfs_rank_key(merge))
    return [veh.name for veh in candidates]


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


def _run_traced_simulation(order_control_type):
    W = _build_world(order_control_type)
    merge = W.get_node("merge")
    vehicles = _add_vehicles_with_fixed_routes(W, VEHICLE_PLANS)
    vehicle_names = sorted(vehicles)

    vehicle_traces = {name: [] for name in vehicle_names}
    merge_pre_transfer_traces = []
    merge_post_transfer_traces = []
    batch_diagnostic_traces = []
    pass_events = []
    trip_end_timesteps = {}
    pending_visit_ids = {name: None for name in vehicle_names}

    link_before = {name: None for name in vehicle_names}
    steps = 0

    while W.check_simulation_ongoing():
        if steps >= MAX_STEPS:
            raise AssertionError(
                f"{order_control_type}: exceeded max_steps={MAX_STEPS} before completion"
            )

        pre_merge = _merge_pre_transfer_snapshot(merge)
        merge_pre_transfer_traces.append(pre_merge)

        if order_control_type == "batch":
            batch_diagnostic_traces.append(
                {
                    "pre_transfer": _batch_diagnostic_snapshot(merge),
                    "fcfs_candidate_order_for_diagnostic": _fcfs_candidate_order(merge),
                }
            )
        else:
            batch_diagnostic_traces.append(
                {
                    "pre_transfer": None,
                    "fcfs_candidate_order_for_diagnostic": _fcfs_candidate_order(merge),
                }
            )

        W.exec_simulation(duration_t2=1)
        steps += 1

        merge_post_transfer_traces.append(
            {
                "timestep": W.T,
                "last_order_control_inlink": _link_name(merge.last_order_control_inlink),
                "last_order_control_entry_timestep": merge.last_order_control_entry_timestep,
            }
        )

        for name in vehicle_names:
            veh = vehicles[name]
            previous_link = link_before[name]
            previous_name = _link_name(previous_link)
            current_name = _link_name(veh.link)

            if (
                current_name in MERGE_INLINK_NAMES
                and veh.order_control_current_visit is not None
            ):
                pending_visit_ids[name] = veh.order_control_current_visit["visit_id"]

            if (
                previous_name in MERGE_INLINK_NAMES
                and current_name in MERGE_OUTLINK_NAMES
            ):
                visit_id = pending_visit_ids[name]
                pass_events.append(
                    {
                        "vehicle_name": name,
                        "timestep": W.T,
                        "inlink_name": previous_name,
                        "outlink_name": current_name,
                        "visit_id": visit_id,
                        "is_revisit": visit_id == 2,
                    }
                )

            if name not in trip_end_timesteps and veh.state == "end":
                trip_end_timesteps[name] = W.T

            vehicle_traces[name].append(_vehicle_timestep_snapshot(veh))
            link_before[name] = veh.link

    completed = sum(1 for veh in vehicles.values() if veh.state == "end")
    analyzer = W.analyzer
    completed_arrival_times = [
        veh.arrival_time * W.DELTAT
        for veh in vehicles.values()
        if veh.arrival_time >= 0 and veh.travel_time >= 0
    ]
    last_completed_trip_time = (
        max(completed_arrival_times) if completed_arrival_times else None
    )

    per_vehicle_final = {}
    for name in vehicle_names:
        veh = vehicles[name]
        per_vehicle_final[name] = {
            "state": veh.state,
            "arrival_time": veh.arrival_time,
            "travel_time": veh.travel_time,
            "traveled_route_link_names": _traveled_route_link_names(veh),
            "log_t_link_history": _normalize_log_t_link(veh),
        }

    return {
        "order_control_type": order_control_type,
        "vehicle_names": vehicle_names,
        "vehicles": vehicles,
        "vehicle_traces": vehicle_traces,
        "merge_pre_transfer_traces": merge_pre_transfer_traces,
        "merge_post_transfer_traces": merge_post_transfer_traces,
        "batch_diagnostic_traces": batch_diagnostic_traces,
        "pass_events": pass_events,
        "trip_end_timesteps": trip_end_timesteps,
        "completed_trips": completed,
        "unfinished_vehicle_count": len(vehicle_names) - completed,
        "total_travel_time": float(analyzer.total_travel_time),
        "average_travel_time": float(analyzer.average_travel_time),
        "average_delay": float(analyzer.average_delay),
        "total_distance_traveled": float(analyzer.total_distance_traveled),
        "last_completed_trip_time": last_completed_trip_time,
        "per_vehicle_final": per_vehicle_final,
        "steps": steps,
    }


def _pass_events_for_vehicle(pass_events, vehicle_name):
    return [event for event in pass_events if event["vehicle_name"] == vehicle_name]


def _is_first_visit_merge_candidate(entry, inlink_name):
    return (
        entry["inlink_name"] == inlink_name
        and entry["has_current_visit"]
        and entry["current_visit_node"] == "merge"
        and entry["current_visit_inlink"] == inlink_name
        and entry["current_visit_visit_id"] == 1
    )


def _is_revisit_link2_loop_candidate(entry, loop_name):
    return (
        entry["name"] == loop_name
        and entry["inlink_name"] == "link2"
        and entry["has_current_visit"]
        and entry["current_visit_node"] == "merge"
        and entry["current_visit_inlink"] == "link2"
        and entry["current_visit_visit_id"] == 2
    )


def _is_revisit_link1_competitor_candidate(entry):
    return (
        entry["inlink_name"] == "link1"
        and entry["has_current_visit"]
        and entry["current_visit_node"] == "merge"
        and entry["current_visit_inlink"] == "link1"
    )


def _collect_first_visit_conflicts(merge_pre_transfer_traces):
    conflicts = []
    for snapshot in merge_pre_transfer_traces:
        incoming = snapshot["incoming_vehicles"]
        if len(incoming) < 2:
            continue
        link1_candidates = [
            entry for entry in incoming if _is_first_visit_merge_candidate(entry, "link1")
        ]
        link2_candidates = [
            entry for entry in incoming if _is_first_visit_merge_candidate(entry, "link2")
        ]
        if not link1_candidates or not link2_candidates:
            continue
        conflicts.append(
            {
                "timestep": snapshot["timestep"],
                "link1_vehicle": link1_candidates[0]["name"],
                "link1_inlink": link1_candidates[0]["inlink_name"],
                "link1_visit_id": link1_candidates[0]["current_visit_visit_id"],
                "link2_vehicle": link2_candidates[0]["name"],
                "link2_inlink": link2_candidates[0]["inlink_name"],
                "link2_visit_id": link2_candidates[0]["current_visit_visit_id"],
                "incoming_vehicle_names": list(snapshot["incoming_vehicle_names"]),
            }
        )
    return conflicts


def _collect_revisit_conflicts(merge_pre_transfer_traces, loop_names):
    conflicts = []
    for snapshot in merge_pre_transfer_traces:
        incoming = snapshot["incoming_vehicles"]
        if len(incoming) < 2:
            continue
        for loop_name in sorted(loop_names):
            loop_candidates = [
                entry for entry in incoming if _is_revisit_link2_loop_candidate(entry, loop_name)
            ]
            if not loop_candidates:
                continue
            link1_competitors = [
                entry
                for entry in incoming
                if entry["name"] != loop_name and _is_revisit_link1_competitor_candidate(entry)
            ]
            if not link1_competitors:
                continue
            loop_entry = loop_candidates[0]
            link1_entry = link1_competitors[0]
            conflicts.append(
                {
                    "timestep": snapshot["timestep"],
                    "loop_vehicle": loop_name,
                    "loop_inlink": loop_entry["inlink_name"],
                    "loop_visit_id": loop_entry["current_visit_visit_id"],
                    "link1_vehicle": link1_entry["name"],
                    "link1_inlink": link1_entry["inlink_name"],
                    "link1_visit_id": link1_entry["current_visit_visit_id"],
                    "incoming_vehicle_names": list(snapshot["incoming_vehicle_names"]),
                }
            )
    return conflicts


def _vehicle_pass_timesteps(pass_events):
    passes_by_vehicle = {}
    for event in pass_events:
        passes_by_vehicle.setdefault(event["vehicle_name"], []).append(event["timestep"])
    return passes_by_vehicle


def _collect_direction_change_pass_pairs(pass_events):
    if len(pass_events) < 2:
        return []
    pairs = []
    for index in range(1, len(pass_events)):
        previous = pass_events[index - 1]
        current = pass_events[index]
        if previous["inlink_name"] != current["inlink_name"]:
            pairs.append((previous, current))
    return pairs


def _assert_clearance_wait_from_pass_events(pass_events):
    # Same meaning as tests_order_control_batch_node_transfer_integration.py
    # _assert_clearance_wait_occurred(): consecutive global merge passes that switch
    # inlink must be separated by more than clearance_timesteps. This does not by
    # itself prove a specific vehicle was blocked only by clearance (capacity blocks
    # are indistinguishable here); snapshot-based checks below add blocked-candidate
    # evidence where possible.
    clearance_waits = []
    for index in range(1, len(pass_events)):
        previous = pass_events[index - 1]
        current = pass_events[index]
        if previous["inlink_name"] == current["inlink_name"]:
            continue
        gap = current["timestep"] - previous["timestep"]
        clearance_waits.append(
            {
                "previous_vehicle": previous["vehicle_name"],
                "current_vehicle": current["vehicle_name"],
                "previous_timestep": previous["timestep"],
                "current_timestep": current["timestep"],
                "previous_inlink": previous["inlink_name"],
                "current_inlink": current["inlink_name"],
                "gap": gap,
            }
        )
        if gap <= CLEARANCE_TIMESTEPS:
            raise AssertionError(
                "Direction-change clearance wait violated for "
                f"{current['vehicle_name']}: previous pass {previous['vehicle_name']} "
                f"at timestep {previous['timestep']} from {previous['inlink_name']}, "
                f"current pass at {current['timestep']} from {current['inlink_name']}, "
                f"gap={gap}, clearance_timesteps={CLEARANCE_TIMESTEPS}"
            )
    if not clearance_waits:
        raise AssertionError(
            "Expected at least one direction-change clearance wait in global pass order, "
            f"but pass_events={pass_events!r}"
        )
    return clearance_waits


def _collect_clearance_blocked_candidates(merge_pre_transfer_traces, pass_events):
    # Identify incoming vehicles blocked by unsatisfied clearance at transfer time,
    # then verify they pass on a later timestep. Capacity-only blocks are not always
    # distinguishable from clearance blocks without additional probes.
    passes_by_vehicle = _vehicle_pass_timesteps(pass_events)
    blocked_events = []
    for snapshot in merge_pre_transfer_traces:
        timestep = snapshot["timestep"]
        for entry in snapshot["incoming_vehicles"]:
            if not entry["clearance_required"]:
                continue
            if entry["clearance_satisfied"]:
                continue
            if not entry["has_route_next_link"]:
                continue
            vehicle_name = entry["name"]
            if timestep in passes_by_vehicle.get(vehicle_name, []):
                continue
            later_passes = [
                pass_timestep
                for pass_timestep in passes_by_vehicle.get(vehicle_name, [])
                if pass_timestep > timestep
            ]
            if not later_passes:
                continue
            blocked_events.append(
                {
                    "timestep": timestep,
                    "vehicle_name": vehicle_name,
                    "candidate_inlink": entry["inlink_name"],
                    "last_order_control_inlink": snapshot["last_order_control_inlink"],
                    "last_order_control_entry_timestep": (
                        snapshot["last_order_control_entry_timestep"]
                    ),
                    "later_pass_timestep": min(later_passes),
                }
            )
    return blocked_events


def _assert_scenario_conditions(result):
    vehicle_names = set(result["vehicle_names"])
    loop_names = {plan["name"] for plan in VEHICLE_PLANS if plan["role"] == "loop"}
    if len(loop_names) < 2:
        raise AssertionError("Expected at least two loop vehicles")

    for loop_name in sorted(loop_names):
        events = _pass_events_for_vehicle(result["pass_events"], loop_name)
        if len(events) != 2:
            raise AssertionError(
                f"Loop vehicle {loop_name} expected 2 merge passes, got {events!r}"
            )
        visit_ids = [event["visit_id"] for event in events]
        if visit_ids != [1, 2]:
            raise AssertionError(
                f"Loop vehicle {loop_name} expected visit_id sequence [1, 2], got {visit_ids!r}"
            )

    first_visit_conflicts = _collect_first_visit_conflicts(result["merge_pre_transfer_traces"])
    if not first_visit_conflicts:
        raise AssertionError(
            "Scenario condition not met: no first-visit conflict with link1/link2 "
            "candidates whose current visit at merge has visit_id=1"
        )

    revisit_conflicts = _collect_revisit_conflicts(
        result["merge_pre_transfer_traces"], loop_names
    )
    if not revisit_conflicts:
        raise AssertionError(
            "Scenario condition not met: no revisit conflict snapshot with loop vehicle "
            "visit_id=2 on link2 and a link1-side merge candidate in incoming_vehicles"
        )

    direction_change_pairs = _collect_direction_change_pass_pairs(result["pass_events"])
    if not direction_change_pairs:
        raise AssertionError(
            "Scenario condition not met: no direction change in global pass_events order"
        )

    clearance_waits = _assert_clearance_wait_from_pass_events(result["pass_events"])

    clearance_blocked_candidates = _collect_clearance_blocked_candidates(
        result["merge_pre_transfer_traces"], result["pass_events"]
    )
    if not clearance_blocked_candidates:
        raise AssertionError(
            "Scenario condition not met: no clearance-blocked incoming candidate that "
            "passed on a later timestep; clearance_waits_from_pass_events="
            f"{clearance_waits!r}"
        )

    result["scenario_evidence"] = {
        "first_visit_conflicts": first_visit_conflicts,
        "revisit_conflicts": revisit_conflicts,
        "direction_change_pairs": direction_change_pairs,
        "clearance_waits": clearance_waits,
        "clearance_blocked_candidates": clearance_blocked_candidates,
    }

    if result["completed_trips"] != len(vehicle_names):
        raise AssertionError(
            f"Not all vehicles completed: {result['completed_trips']} / {len(vehicle_names)}"
        )
    if set(result["trip_end_timesteps"]) != vehicle_names:
        missing = sorted(vehicle_names - set(result["trip_end_timesteps"]))
        raise AssertionError(f"Trip-end timesteps missing vehicles: {missing!r}")


def _aggregate_payload(result):
    return {
        "completed_trips": result["completed_trips"],
        "total_travel_time": result["total_travel_time"],
        "average_travel_time": result["average_travel_time"],
        "average_delay": result["average_delay"],
        "total_distance_traveled": result["total_distance_traveled"],
        "unfinished_vehicle_count": result["unfinished_vehicle_count"],
        "last_completed_trip_time": result["last_completed_trip_time"],
    }


def _find_first_trace_mismatch(fcfs_result, batch_result):
    if fcfs_result["vehicle_names"] != batch_result["vehicle_names"]:
        return {
            "kind": "vehicle_names",
            "index": 0,
            "vehicle_name": None,
            "fcfs": fcfs_result["vehicle_names"],
            "batch": batch_result["vehicle_names"],
        }

    for name in fcfs_result["vehicle_names"]:
        if fcfs_result["vehicle_traces"][name] != batch_result["vehicle_traces"][name]:
            fcfs_trace = fcfs_result["vehicle_traces"][name]
            batch_trace = batch_result["vehicle_traces"][name]
            limit = max(len(fcfs_trace), len(batch_trace))
            for index in range(limit):
                fcfs_item = fcfs_trace[index] if index < len(fcfs_trace) else "<missing>"
                batch_item = batch_trace[index] if index < len(batch_trace) else "<missing>"
                if fcfs_item != batch_item:
                    return {
                        "kind": "vehicle_trace",
                        "index": index,
                        "vehicle_name": name,
                        "fcfs": fcfs_item,
                        "batch": batch_item,
                    }

    if fcfs_result["merge_pre_transfer_traces"] != batch_result["merge_pre_transfer_traces"]:
        for index, (fcfs_item, batch_item) in enumerate(
            zip(
                fcfs_result["merge_pre_transfer_traces"],
                batch_result["merge_pre_transfer_traces"],
            )
        ):
            if fcfs_item != batch_item:
                return {
                    "kind": "merge_pre_transfer_trace",
                    "index": index,
                    "vehicle_name": None,
                    "fcfs": fcfs_item,
                    "batch": batch_item,
                }
        return {
            "kind": "merge_pre_transfer_trace_length",
            "index": min(
                len(fcfs_result["merge_pre_transfer_traces"]),
                len(batch_result["merge_pre_transfer_traces"]),
            ),
            "vehicle_name": None,
            "fcfs": len(fcfs_result["merge_pre_transfer_traces"]),
            "batch": len(batch_result["merge_pre_transfer_traces"]),
        }

    if fcfs_result["merge_post_transfer_traces"] != batch_result["merge_post_transfer_traces"]:
        for index, (fcfs_item, batch_item) in enumerate(
            zip(
                fcfs_result["merge_post_transfer_traces"],
                batch_result["merge_post_transfer_traces"],
            )
        ):
            if fcfs_item != batch_item:
                return {
                    "kind": "merge_post_transfer_trace",
                    "index": index,
                    "vehicle_name": None,
                    "fcfs": fcfs_item,
                    "batch": batch_item,
                }

    if fcfs_result["pass_events"] != batch_result["pass_events"]:
        for index, (fcfs_item, batch_item) in enumerate(
            zip(fcfs_result["pass_events"], batch_result["pass_events"])
        ):
            if fcfs_item != batch_item:
                return {
                    "kind": "pass_events",
                    "index": index,
                    "vehicle_name": fcfs_item.get("vehicle_name"),
                    "fcfs": fcfs_item,
                    "batch": batch_item,
                }
        return {
            "kind": "pass_events_length",
            "index": min(len(fcfs_result["pass_events"]), len(batch_result["pass_events"])),
            "vehicle_name": None,
            "fcfs": len(fcfs_result["pass_events"]),
            "batch": len(batch_result["pass_events"]),
        }

    if fcfs_result["trip_end_timesteps"] != batch_result["trip_end_timesteps"]:
        for name in fcfs_result["vehicle_names"]:
            if fcfs_result["trip_end_timesteps"].get(name) != batch_result["trip_end_timesteps"].get(
                name
            ):
                return {
                    "kind": "trip_end_timesteps",
                    "index": fcfs_result["trip_end_timesteps"].get(name),
                    "vehicle_name": name,
                    "fcfs": fcfs_result["trip_end_timesteps"].get(name),
                    "batch": batch_result["trip_end_timesteps"].get(name),
                }

    if _aggregate_payload(fcfs_result) != _aggregate_payload(batch_result):
        for key, fcfs_value in _aggregate_payload(fcfs_result).items():
            batch_value = _aggregate_payload(batch_result)[key]
            if fcfs_value != batch_value:
                return {
                    "kind": "aggregate",
                    "index": key,
                    "vehicle_name": None,
                    "fcfs": fcfs_value,
                    "batch": batch_value,
                }

    for name in fcfs_result["vehicle_names"]:
        fcfs_final = fcfs_result["per_vehicle_final"][name]
        batch_final = batch_result["per_vehicle_final"][name]
        if fcfs_final != batch_final:
            for key in fcfs_final:
                if fcfs_final[key] != batch_final[key]:
                    return {
                        "kind": f"per_vehicle_final.{key}",
                        "index": key,
                        "vehicle_name": name,
                        "fcfs": fcfs_final[key],
                        "batch": batch_final[key],
                    }

    return None


def _diagnostic_context(result, mismatch):
    merge = result["vehicles"]["L0"].W.get_node("merge")
    timestep = None
    vehicle_name = mismatch.get("vehicle_name")

    if mismatch["kind"] == "vehicle_trace" and vehicle_name is not None:
        index = mismatch["index"]
        timestep = result["vehicle_traces"][vehicle_name][index]["timestep"]
    elif mismatch["kind"] in (
        "merge_pre_transfer_trace",
        "merge_post_transfer_trace",
    ):
        index = mismatch["index"]
        if mismatch["kind"] == "merge_pre_transfer_trace":
            timestep = result["merge_pre_transfer_traces"][index]["timestep"]
        else:
            timestep = result["merge_post_transfer_traces"][index]["timestep"]
    elif mismatch["kind"] == "pass_events":
        timestep = mismatch["fcfs"].get("timestep")

    pre_merge = None
    batch_diag = None
    fcfs_candidates = None
    if timestep is not None:
        for snapshot in result["merge_pre_transfer_traces"]:
            if snapshot["timestep"] == timestep:
                pre_merge = snapshot
                break
        for diag in result["batch_diagnostic_traces"]:
            if diag["pre_transfer"] is not None and diag["pre_transfer"]["timestep"] == timestep:
                batch_diag = diag
                fcfs_candidates = diag["fcfs_candidate_order_for_diagnostic"]
                break

    recent_passes = [
        event
        for event in result["pass_events"]
        if timestep is None or event["timestep"] <= timestep
    ][-5:]

    vehicle_snapshot = None
    if vehicle_name is not None and mismatch["kind"] == "vehicle_trace":
        vehicle_snapshot = mismatch.get("batch") if result["order_control_type"] == "batch" else mismatch.get("fcfs")

    return {
        "timestep": timestep,
        "vehicle_name": vehicle_name,
        "vehicle_snapshot": vehicle_snapshot,
        "merge_pre_transfer": pre_merge,
        "last_order_control_inlink": pre_merge["last_order_control_inlink"] if pre_merge else None,
        "last_order_control_entry_timestep": (
            pre_merge["last_order_control_entry_timestep"] if pre_merge else None
        ),
        "fcfs_candidate_order": fcfs_candidates,
        "batch_trigger_candidates": (
            batch_diag["pre_transfer"]["trigger_candidate_names"] if batch_diag else None
        ),
        "batch_service_queue": (
            batch_diag["pre_transfer"]["service_queue"] if batch_diag else None
        ),
        "recent_pass_events": recent_passes,
    }


def _raise_equivalence_failure(fcfs_result, batch_result):
    mismatch = _find_first_trace_mismatch(fcfs_result, batch_result)
    if mismatch is None:
        raise AssertionError("Equivalence failure reported but no mismatch found")

    fcfs_context = _diagnostic_context(fcfs_result, mismatch)
    batch_context = _diagnostic_context(batch_result, mismatch)

    message_lines = [
        "FCFS vs N=1 BATCH revisit equivalence mismatch",
        f"first_difference_kind={mismatch['kind']!r}",
        f"first_difference_index={mismatch['index']!r}",
        f"first_difference_vehicle={mismatch.get('vehicle_name')!r}",
        f"fcfs_value={mismatch['fcfs']!r}",
        f"batch_value={mismatch['batch']!r}",
        f"fcfs_vehicle_snapshot={fcfs_context['vehicle_snapshot']!r}",
        f"batch_vehicle_snapshot={batch_context['vehicle_snapshot']!r}",
        f"fcfs_merge_pre_transfer={fcfs_context['merge_pre_transfer']!r}",
        f"batch_merge_pre_transfer={batch_context['merge_pre_transfer']!r}",
        f"fcfs_last_order_control_inlink={fcfs_context['last_order_control_inlink']!r}",
        f"batch_last_order_control_inlink={batch_context['last_order_control_inlink']!r}",
        f"fcfs_last_order_control_entry_timestep={fcfs_context['last_order_control_entry_timestep']!r}",
        f"batch_last_order_control_entry_timestep={batch_context['last_order_control_entry_timestep']!r}",
        f"fcfs_candidate_order={fcfs_context['fcfs_candidate_order']!r}",
        f"batch_trigger_candidates={batch_context['batch_trigger_candidates']!r}",
        f"batch_service_queue={batch_context['batch_service_queue']!r}",
        f"fcfs_recent_pass_events={fcfs_context['recent_pass_events']!r}",
        f"batch_recent_pass_events={batch_context['recent_pass_events']!r}",
    ]
    raise AssertionError("\n".join(message_lines))


def _assert_full_equivalence(fcfs_result, batch_result):
    mismatch = _find_first_trace_mismatch(fcfs_result, batch_result)
    if mismatch is not None:
        _raise_equivalence_failure(fcfs_result, batch_result)


def test_n1_batch_matches_fcfs_with_same_node_revisit_and_clearance():
    fcfs_result = _run_traced_simulation("fcfs")
    batch_result = _run_traced_simulation("batch")

    _assert_scenario_conditions(fcfs_result)
    _assert_scenario_conditions(batch_result)
    _assert_full_equivalence(fcfs_result, batch_result)


TESTS = [
    test_n1_batch_matches_fcfs_with_same_node_revisit_and_clearance,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("N=1 BATCH vs FCFS same-node revisit equivalence tests passed.")
