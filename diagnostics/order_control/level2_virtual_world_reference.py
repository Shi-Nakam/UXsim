# Phase 4-6W: mimic-World Level 2 t_trigger reference model (not connected to UXsim body).
#
# Run via tests_order_control_batch_t_trigger_level_2_reference.py from repository root.

from __future__ import annotations

from collections import deque

from uxsim import World


def estimate_order_control_batch_t_trigger_level_2_reference(
    real_node,
    real_trigger_vehicle,
    t_level_1,
    virtual_horizon,
    *,
    mimic_random_seed=0,
):
    """
    Reference-only Level 2 estimator using a small mimic World built from a snapshot.

    Does not mutate the real World. Returns a dict with resolved, t_level_1,
    t_virtual_trigger, t_level_2_candidate, reason, snapshot_timestep,
    simulated_timestep_count, trigger_vehicle_name, vehicle_transfer_timesteps,
    and sink_end_trip_trace.
    """
    _validate_reference_inputs(real_node, real_trigger_vehicle, t_level_1, virtual_horizon)
    snapshot_timestep = int(real_node.W.T)
    _validate_service_queue_invariants(real_node, real_trigger_vehicle)

    mimic_bundle = _build_mimic_world(
        real_node,
        real_trigger_vehicle,
        mimic_random_seed=mimic_random_seed,
    )
    mimic_W = mimic_bundle["mimic_W"]
    mimic_node = mimic_bundle["mimic_node"]
    mimic_trigger = mimic_bundle["mimic_trigger"]
    mimic_W.T = snapshot_timestep
    _ensure_link_cum_arrays(mimic_W, snapshot_timestep)

    loop_result = _run_limited_virtual_loop(
        mimic_W,
        mimic_node,
        mimic_trigger,
        virtual_horizon,
    )
    t_virtual_trigger = loop_result["t_virtual_trigger"]
    simulated_timestep_count = loop_result["simulated_timestep_count"]
    vehicle_transfer_timesteps = loop_result["vehicle_transfer_timesteps"]
    sink_end_trip_trace = loop_result["sink_end_trip_trace"]

    base_result = {
        "t_level_1": int(t_level_1),
        "snapshot_timestep": snapshot_timestep,
        "simulated_timestep_count": int(simulated_timestep_count),
        "trigger_vehicle_name": real_trigger_vehicle.name,
        "vehicle_transfer_timesteps": vehicle_transfer_timesteps,
        "sink_end_trip_trace": sink_end_trip_trace,
    }

    if t_virtual_trigger is not None:
        return {
            **base_result,
            "resolved": True,
            "t_virtual_trigger": int(t_virtual_trigger),
            "t_level_2_candidate": int(max(t_level_1, t_virtual_trigger)),
            "reason": None,
        }

    return {
        **base_result,
        "resolved": False,
        "t_virtual_trigger": None,
        "t_level_2_candidate": int(t_level_1),
        "reason": "virtual_horizon_exceeded",
    }


def _validate_reference_inputs(real_node, real_trigger_vehicle, t_level_1, virtual_horizon):
    if not real_node.order_control_eligible or real_node.order_control_type != "batch":
        raise ValueError(
            f"Node {real_node.name} is not a BATCH order-control node."
        )
    if real_trigger_vehicle not in real_node.incoming_vehicles:
        raise ValueError(
            f"Vehicle {real_trigger_vehicle.name} is not in incoming_vehicles of node "
            f"{real_node.name}."
        )
    if real_trigger_vehicle.route_next_link is None:
        raise ValueError(
            f"Vehicle {real_trigger_vehicle.name} has no route_next_link at node "
            f"{real_node.name}."
        )
    if real_trigger_vehicle.get_order_control_batch_assignment(real_node) is not None:
        raise ValueError(
            f"Vehicle {real_trigger_vehicle.name} is already batch-assigned at node "
            f"{real_node.name}."
        )
    if not isinstance(t_level_1, int) or isinstance(t_level_1, bool):
        raise ValueError(f"Invalid t_level_1={t_level_1!r}; expected int.")
    if t_level_1 < 0:
        raise ValueError(f"Invalid t_level_1={t_level_1}; expected non-negative int.")
    if not isinstance(virtual_horizon, int) or isinstance(virtual_horizon, bool):
        raise ValueError(f"Invalid virtual_horizon={virtual_horizon!r}; expected int.")
    if virtual_horizon < 0:
        raise ValueError(
            f"Invalid virtual_horizon={virtual_horizon}; expected non-negative int."
        )


def _validate_service_queue_invariants(real_node, real_trigger_vehicle):
    if (real_node.last_order_control_inlink is None) != (
        real_node.last_order_control_entry_timestep is None
    ):
        raise ValueError(
            f"Node {real_node.name} has inconsistent order-control clearance history."
        )

    seen_vehicles = set()
    for unit_index, unit in enumerate(real_node.order_control_batch_service_queue):
        for required_key in ("batch_id", "inlink", "vehicles", "visit_ids"):
            if required_key not in unit:
                raise ValueError(
                    f"Node {real_node.name}: service unit at queue index {unit_index} "
                    f"is missing required key {required_key!r}."
                )
        batch_id = unit["batch_id"]
        inlink = unit["inlink"]
        vehicles = unit["vehicles"]
        visit_ids = unit["visit_ids"]
        if len(vehicles) != len(visit_ids):
            raise ValueError(
                f"Node {real_node.name}: service unit batch_id={batch_id} has mismatched "
                "vehicles and visit_ids lengths."
            )
        if not vehicles:
            raise ValueError(
                f"Node {real_node.name}: service unit batch_id={batch_id} is empty."
            )
        for veh, registered_visit_id in zip(vehicles, visit_ids):
            if veh in seen_vehicles:
                raise ValueError(
                    f"Vehicle {veh.name} appears in multiple service units at node "
                    f"{real_node.name}."
                )
            seen_vehicles.add(veh)
            if veh.link is not inlink:
                raise ValueError(
                    f"Vehicle {veh.name} inlink mismatch for service unit batch_id={batch_id}."
                )
            current_visit = veh.order_control_current_visit
            if current_visit is None:
                raise ValueError(
                    f"Vehicle {veh.name} has no current visit for service unit "
                    f"batch_id={batch_id}."
                )
            if current_visit["visit_id"] != registered_visit_id:
                raise ValueError(
                    f"Vehicle {veh.name} visit_id mismatch for service unit batch_id={batch_id}."
                )
            assignment = veh.get_order_control_batch_assignment(real_node)
            if assignment is None or assignment != batch_id:
                raise ValueError(
                    f"Vehicle {veh.name} batch_assignment mismatch for service unit "
                    f"batch_id={batch_id}."
                )

    _validate_service_unit_inlink_assignment_prefixes(
        real_node, seen_vehicles
    )

    trigger_inlink = real_trigger_vehicle.link
    if trigger_inlink is None:
        raise ValueError(
            f"Vehicle {real_trigger_vehicle.name} has no link at node {real_node.name}."
        )
    for veh in trigger_inlink.vehicles:
        if veh is real_trigger_vehicle:
            break
        if not veh.has_order_control_batch_assignment(real_node):
            raise ValueError(
                f"Vehicle {veh.name} ahead of trigger {real_trigger_vehicle.name} on "
                f"inlink {trigger_inlink.name} is not batch-assigned."
            )
        if veh not in seen_vehicles:
            raise ValueError(
                f"Vehicle {veh.name} ahead of trigger {real_trigger_vehicle.name} is "
                "not registered in the service queue."
            )


def _validate_service_unit_inlink_assignment_prefixes(real_node, seen_vehicles):
    inlinks_with_units = {}
    for unit in real_node.order_control_batch_service_queue:
        inlink = unit["inlink"]
        inlinks_with_units.setdefault(inlink, []).extend(unit["vehicles"])

    for inlink, unit_vehicles in inlinks_with_units.items():
        unit_vehicle_set = set(unit_vehicles)
        if not inlink.vehicles:
            raise ValueError(
                f"Inlink {inlink.name} at node {real_node.name} has service units but "
                "an empty vehicles deque."
            )

        min_unit_index = None
        for index, veh in enumerate(inlink.vehicles):
            if veh in unit_vehicle_set:
                min_unit_index = index
                break

        if min_unit_index is None:
            raise ValueError(
                f"Inlink {inlink.name} at node {real_node.name}: service unit vehicles "
                "are not present in the physical FIFO queue."
            )

        for index in range(min_unit_index):
            ahead_vehicle = inlink.vehicles[index]
            if not ahead_vehicle.has_order_control_batch_assignment(real_node):
                raise ValueError(
                    f"Vehicle {ahead_vehicle.name} ahead of service unit vehicles on "
                    f"inlink {inlink.name} at node {real_node.name} is not "
                    "batch-assigned."
                )
            if ahead_vehicle not in seen_vehicles:
                raise ValueError(
                    f"Vehicle {ahead_vehicle.name} ahead of service unit vehicles on "
                    f"inlink {inlink.name} at node {real_node.name} is not registered "
                    "in the service queue."
                )

        saw_unassigned = False
        for veh in inlink.vehicles:
            if veh.has_order_control_batch_assignment(real_node):
                if saw_unassigned:
                    raise ValueError(
                        f"Inlink {inlink.name} at node {real_node.name}: assigned "
                        "vehicles do not form a contiguous FIFO prefix."
                    )
                if veh not in seen_vehicles:
                    raise ValueError(
                        f"Vehicle {veh.name} is batch-assigned on inlink {inlink.name} "
                        f"at node {real_node.name} but is not registered in the service "
                        "queue."
                    )
            else:
                saw_unassigned = True
                if veh in unit_vehicle_set:
                    raise ValueError(
                        f"Vehicle {veh.name} appears in a service unit on inlink "
                        f"{inlink.name} at node {real_node.name} without batch assignment."
                    )


def _collect_real_vehicles(real_node, real_trigger_vehicle):
    vehicles = set()
    for unit in real_node.order_control_batch_service_queue:
        for veh in unit["vehicles"]:
            vehicles.add(veh)
    vehicles.add(real_trigger_vehicle)

    for outlink in real_node.outlinks.values():
        for veh in outlink.vehicles:
            vehicles.add(veh)

    trigger_inlink = real_trigger_vehicle.link
    for veh in trigger_inlink.vehicles:
        if veh is real_trigger_vehicle:
            break
        vehicles.add(veh)

    return vehicles


def _build_mimic_world(real_node, real_trigger_vehicle, *, mimic_random_seed):
    real_W = real_node.W
    mimic_W = World(
        name=f"{real_W.name}_l2_mimic",
        deltan=1,
        tmax=max(real_W.TMAX, (real_W.T + 200) * real_W.DELTAT),
        reaction_time=real_W.REACTION_TIME,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=mimic_random_seed,
        hard_deterministic_mode=True,
    )
    mimic_W.set_order_control_clearance_timesteps(real_W.order_control_clearance_timesteps)

    node_maps = {
        "real_node": real_node,
        "real_to_mimic_node": {},
        "real_to_mimic_link": {},
        "real_to_mimic_vehicle": {},
    }

    for real_inlink in real_node.inlinks.values():
        upstream_name = f"_mimic_up_{real_inlink.name}"
        mimic_W.addNode(upstream_name, 0, 0)

    mimic_node = mimic_W.addNode(
        real_node.name,
        real_node.x,
        real_node.y,
        order_control_eligible=True,
        order_control_type="batch",
        batch_size=real_node.batch_size,
        order_control_batch_t_trigger_level=real_node.order_control_batch_t_trigger_level,
        flow_capacity=real_node.flow_capacity,
        number_of_lanes=real_node.number_of_lanes,
    )
    mimic_node.order_control_clearance_timesteps = real_node.order_control_clearance_timesteps
    node_maps["real_to_mimic_node"][real_node] = mimic_node

    for real_inlink in real_node.inlinks.values():
        upstream_name = f"_mimic_up_{real_inlink.name}"
        mimic_inlink = mimic_W.addLink(
            real_inlink.name,
            upstream_name,
            real_node.name,
            length=real_inlink.length,
            free_flow_speed=real_inlink.u,
            jam_density=real_inlink.jam_density,
            number_of_lanes=real_inlink.number_of_lanes,
            merge_priority=real_inlink.merge_priority,
            capacity_out=real_inlink.capacity_out,
            capacity_in=real_inlink.capacity_in,
        )
        node_maps["real_to_mimic_link"][real_inlink] = mimic_inlink

    for real_outlink in real_node.outlinks.values():
        sink_name = f"_mimic_sink_{real_outlink.name}"
        mimic_sink = mimic_W.addNode(sink_name, 0, 0)
        node_maps["real_to_mimic_node"][real_outlink.end_node] = mimic_sink
        mimic_outlink = mimic_W.addLink(
            real_outlink.name,
            real_node.name,
            sink_name,
            length=real_outlink.length,
            free_flow_speed=real_outlink.u,
            jam_density=real_outlink.jam_density,
            number_of_lanes=real_outlink.number_of_lanes,
            merge_priority=real_outlink.merge_priority,
            capacity_out=real_outlink.capacity_out,
            capacity_in=real_outlink.capacity_in,
        )
        node_maps["real_to_mimic_link"][real_outlink] = mimic_outlink

    mimic_W.finalize_scenario()

    mimic_node = mimic_W.get_node(real_node.name)
    _copy_node_capacity_state(real_node, mimic_node)
    _copy_clearance_state(real_node, mimic_node, node_maps["real_to_mimic_link"])

    for real_link in list(real_node.inlinks.values()) + list(real_node.outlinks.values()):
        mimic_link = node_maps["real_to_mimic_link"][real_link]
        _copy_link_capacity_state(real_link, mimic_link)

    real_vehicles = _collect_real_vehicles(real_node, real_trigger_vehicle)
    for real_veh in _ordered_real_vehicles(real_node, real_trigger_vehicle, real_vehicles):
        mimic_veh = _create_mimic_vehicle(
            mimic_W,
            real_veh,
            real_node,
            mimic_node,
            node_maps,
        )
        node_maps["real_to_mimic_vehicle"][real_veh] = mimic_veh

    _rebuild_outlink_leader_followers_after_build(mimic_W, mimic_node)
    _rebuild_link_vehicle_deques(real_node, node_maps)
    mimic_node.incoming_vehicles = [
        node_maps["real_to_mimic_vehicle"][veh]
        for veh in real_node.incoming_vehicles
        if veh in node_maps["real_to_mimic_vehicle"]
    ]

    mimic_trigger = node_maps["real_to_mimic_vehicle"][real_trigger_vehicle]
    _rebuild_mimic_service_queue(real_node, mimic_node, node_maps)
    _append_trigger_pseudo_service_unit(mimic_node, mimic_trigger)

    mimic_node.order_control_batch_next_id = max(
        (
            unit["batch_id"]
            for unit in mimic_node.order_control_batch_service_queue
        ),
        default=0,
    ) + 1

    return {
        "mimic_W": mimic_W,
        "mimic_node": mimic_node,
        "mimic_trigger": mimic_trigger,
        "node_maps": node_maps,
    }


def _copy_clearance_state(real_node, mimic_node, real_to_mimic_link):
    if real_node.last_order_control_inlink is None:
        mimic_node.last_order_control_inlink = None
        mimic_node.last_order_control_entry_timestep = None
        return
    mimic_node.last_order_control_inlink = real_to_mimic_link[
        real_node.last_order_control_inlink
    ]
    mimic_node.last_order_control_entry_timestep = (
        real_node.last_order_control_entry_timestep
    )


def _copy_node_capacity_state(real_node, mimic_node):
    mimic_node.flow_capacity = real_node.flow_capacity
    mimic_node.flow_capacity_remain = real_node.flow_capacity_remain
    mimic_node.number_of_lanes = real_node.number_of_lanes


def _copy_link_capacity_state(real_link, mimic_link):
    mimic_link.capacity_out = real_link.capacity_out
    mimic_link.capacity_out_remain = real_link.capacity_out_remain
    mimic_link.capacity_in = real_link.capacity_in
    mimic_link.capacity_in_remain = real_link.capacity_in_remain


def _ordered_real_vehicles(real_node, real_trigger_vehicle, real_vehicles):
    ordered = []
    seen = set()

    def _append(veh):
        if veh in real_vehicles and veh not in seen:
            ordered.append(veh)
            seen.add(veh)

    for unit in real_node.order_control_batch_service_queue:
        for veh in unit["vehicles"]:
            _append(veh)
    _append(real_trigger_vehicle)
    for real_inlink in real_node.inlinks.values():
        for veh in real_inlink.vehicles:
            _append(veh)
    for real_outlink in real_node.outlinks.values():
        for veh in real_outlink.vehicles:
            _append(veh)
    return ordered


def _create_mimic_vehicle(mimic_W, real_veh, real_node, mimic_node, node_maps):
    real_to_mimic_link = node_maps["real_to_mimic_link"]
    real_link = real_veh.link
    if real_link not in real_to_mimic_link:
        raise ValueError(
            f"Vehicle {real_veh.name} link {real_link.name} is not mapped in mimic world."
        )
    mimic_link = real_to_mimic_link[real_link]

    if real_link.end_node is real_node:
        orig_name = f"_mimic_up_{real_link.name}"
        dest_name = real_node.name
        mimic_route_next = real_to_mimic_link[real_veh.route_next_link]
        on_inlink = True
    elif real_link.start_node is real_node:
        orig_name = real_node.name
        dest_name = f"_mimic_sink_{real_link.name}"
        mimic_route_next = (
            real_to_mimic_link[real_veh.route_next_link]
            if real_veh.route_next_link is not None
            else None
        )
        on_inlink = False
    else:
        raise ValueError(
            f"Vehicle {real_veh.name} link {real_link.name} is not connected to node "
            f"{real_node.name}."
        )

    mimic_veh = mimic_W.addVehicle(orig_name, dest_name, 0, name=real_veh.name)
    mimic_veh.state = real_veh.state
    mimic_veh.link = mimic_link
    mimic_veh.route_next_link = mimic_route_next
    mimic_veh.x = real_veh.x
    mimic_veh.x_old = getattr(real_veh, "x_old", real_veh.x)
    mimic_veh.x_next = getattr(real_veh, "x_next", real_veh.x)
    mimic_veh.v = real_veh.v
    mimic_veh.lane = real_veh.lane
    mimic_veh.move_remain = real_veh.move_remain
    mimic_veh.link_arrival_time = real_veh.link_arrival_time
    mimic_veh.flag_waiting_for_trip_end = real_veh.flag_waiting_for_trip_end
    mimic_veh.order_control_visit_id = real_veh.order_control_visit_id
    mimic_veh.order_control_batch_assignments = dict(
        real_veh.order_control_batch_assignments
    )
    mimic_veh.order_control_node_arrival_times = dict(
        real_veh.order_control_node_arrival_times
    )
    mimic_veh.order_control_node_arrival_tiebreakers = dict(
        real_veh.order_control_node_arrival_tiebreakers
    )
    mimic_veh.order_control_earliest_arrival_timesteps = dict(
        real_veh.order_control_earliest_arrival_timesteps
    )

    if real_veh.order_control_current_visit is not None:
        real_visit = real_veh.order_control_current_visit
        mimic_inlink = None
        if real_visit.get("inlink") is not None:
            mimic_inlink = real_to_mimic_link[real_visit["inlink"]]
        mimic_veh.order_control_current_visit = {
            "visit_id": real_visit["visit_id"],
            "node": mimic_node,
            "inlink": mimic_inlink,
            "earliest_arrival_timestep": real_visit["earliest_arrival_timestep"],
            "arrival_time": real_visit.get("arrival_time"),
            "arrival_tiebreaker": real_visit.get("arrival_tiebreaker"),
            "batch_assignment": real_visit.get("batch_assignment"),
        }

    if mimic_veh.state == "run":
        mimic_W.VEHICLES_RUNNING[mimic_veh.name] = mimic_veh

    mimic_link.vehicles.append(mimic_veh)
    if on_inlink and real_veh in real_node.incoming_vehicles:
        if mimic_veh not in mimic_node.incoming_vehicles:
            mimic_node.incoming_vehicles.append(mimic_veh)

    return mimic_veh


def _rebuild_link_vehicle_deques(real_node, node_maps):
    real_to_mimic_vehicle = node_maps["real_to_mimic_vehicle"]
    real_to_mimic_link = node_maps["real_to_mimic_link"]
    for real_inlink in real_node.inlinks.values():
        mimic_inlink = real_to_mimic_link[real_inlink]
        mimic_inlink.vehicles = deque(
            real_to_mimic_vehicle[veh]
            for veh in real_inlink.vehicles
            if veh in real_to_mimic_vehicle
        )
    for real_outlink in real_node.outlinks.values():
        mimic_outlink = real_to_mimic_link[real_outlink]
        mimic_outlink.vehicles = deque(
            real_to_mimic_vehicle[veh]
            for veh in real_outlink.vehicles
            if veh in real_to_mimic_vehicle
        )


def _rebuild_mimic_service_queue(real_node, mimic_node, node_maps):
    real_to_mimic_link = node_maps["real_to_mimic_link"]
    real_to_mimic_vehicle = node_maps["real_to_mimic_vehicle"]
    mimic_node.order_control_batch_service_queue = deque()
    for real_unit in real_node.order_control_batch_service_queue:
        mimic_vehicles = [real_to_mimic_vehicle[v] for v in real_unit["vehicles"]]
        mimic_unit = {
            "batch_id": real_unit["batch_id"],
            "inlink": real_to_mimic_link[real_unit["inlink"]],
            "vehicles": list(mimic_vehicles),
            "visit_ids": list(real_unit["visit_ids"]),
        }
        mimic_node.order_control_batch_service_queue.append(mimic_unit)
        for mimic_veh in mimic_vehicles:
            batch_id = real_unit["batch_id"]
            mimic_veh.order_control_batch_assignments[mimic_node.name] = batch_id
            if mimic_veh.order_control_current_visit is not None:
                mimic_veh.order_control_current_visit["batch_assignment"] = batch_id


def _append_trigger_pseudo_service_unit(mimic_node, mimic_trigger):
    existing_ids = [
        unit["batch_id"] for unit in mimic_node.order_control_batch_service_queue
    ]
    pseudo_batch_id = max(existing_ids) + 1 if existing_ids else 0
    visit = mimic_trigger.order_control_current_visit
    if visit is None:
        raise ValueError(
            f"Mimic trigger {mimic_trigger.name} has no current visit."
        )
    mimic_node.order_control_batch_service_queue.append(
        {
            "batch_id": pseudo_batch_id,
            "inlink": mimic_trigger.link,
            "vehicles": [mimic_trigger],
            "visit_ids": [visit["visit_id"]],
        }
    )
    mimic_trigger.order_control_batch_assignments[mimic_node.name] = pseudo_batch_id
    visit["batch_assignment"] = pseudo_batch_id


def _ensure_link_cum_arrays(mimic_W, timestep):
    for link in mimic_W.LINKS:
        while len(link.cum_arrival) <= timestep:
            link.cum_arrival.append(0)
            link.cum_departure.append(0)
            if len(link.cum_arrival) > 1:
                link.cum_arrival[-1] = link.cum_arrival[-2]
                link.cum_departure[-1] = link.cum_departure[-2]


def _run_limited_virtual_loop(mimic_W, mimic_node, mimic_trigger, virtual_horizon):
    """
    Limited virtual timestep loop aligned with exec_simulation order for local scope.

    offset == 0 (snapshot W.T):
      Use post-Link.update / post-Node.update capacity remains copied from the real
      World without refilling. Serve, then advance outlink vehicles and sink end-trip.

    offset >= 1:
      Advance W.T, refill Link and Node flow capacity, serve, then outlink movement
      and sink end-trip.

    Inlink waiting vehicles do not call Vehicle.update() to keep route_next_link fixed.
    """
    simulated_timestep_count = 0
    vehicle_transfer_timesteps = {}
    sink_end_trip_trace = {}

    for offset in range(virtual_horizon + 1):
        if offset > 0:
            mimic_W.T += 1
            simulated_timestep_count += 1
            for link in mimic_W.LINKS:
                link.in_out_flow_constraint()
            mimic_node.flow_capacity_update()

        trigger_was_waiting = mimic_trigger in mimic_node.incoming_vehicles
        waiting_before_serve = list(mimic_node.incoming_vehicles)

        for link in mimic_W.LINKS:
            while len(link.cum_arrival) <= mimic_W.T:
                link.cum_arrival.append(link.cum_arrival[-1] if link.cum_arrival else 0)
                link.cum_departure.append(
                    link.cum_departure[-1] if link.cum_departure else 0
                )

        mimic_node._serve_order_control_batch_service_queue_internal(set())
        for veh in waiting_before_serve:
            if (
                veh not in mimic_node.incoming_vehicles
                and veh.name not in vehicle_transfer_timesteps
            ):
                vehicle_transfer_timesteps[veh.name] = mimic_W.T

        if trigger_was_waiting and mimic_trigger not in mimic_node.incoming_vehicles:
            return {
                "t_virtual_trigger": mimic_W.T,
                "simulated_timestep_count": simulated_timestep_count,
                "vehicle_transfer_timesteps": vehicle_transfer_timesteps,
                "sink_end_trip_trace": sink_end_trip_trace,
            }

        outlink_vehicles = _get_outlink_running_vehicles(mimic_W, mimic_node)
        for veh in outlink_vehicles:
            veh.carfollow()
        for veh in outlink_vehicles:
            veh.v = (veh.x_next - veh.x) / mimic_W.DELTAT
            veh.x_old = veh.x
            veh.x = veh.x_next
            if veh.x == veh.link.length and veh.link.end_node == veh.dest:
                trace = sink_end_trip_trace.setdefault(veh.name, {})
                trace.setdefault("sink_arrival_timestep", mimic_W.T)
                _observe_sink_end_trip(veh, mimic_W, trace)

    return {
        "t_virtual_trigger": None,
        "simulated_timestep_count": simulated_timestep_count,
        "vehicle_transfer_timesteps": vehicle_transfer_timesteps,
        "sink_end_trip_trace": sink_end_trip_trace,
    }


def _observe_sink_end_trip(veh, mimic_W, trace):
    if "flag_waiting_for_trip_end_timestep" not in trace:
        veh.flag_waiting_for_trip_end = 1
        trace["flag_waiting_for_trip_end_timestep"] = mimic_W.T
    if veh.link is not None and veh.link.vehicles and veh.link.vehicles[0] is veh:
        outlink_before_end_trip = veh.link
        trace.setdefault("end_trip_timestep", mimic_W.T)
        veh.end_trip()
        if veh in outlink_before_end_trip.vehicles:
            raise ValueError(
                f"Vehicle {veh.name} remained on outlink {outlink_before_end_trip.name} "
                "after end_trip() in the Level 2 reference model."
            )
        trace.setdefault("outlink_removal_timestep", mimic_W.T)


def _get_outlink_running_vehicles(mimic_W, mimic_node):
    outlinks = set(mimic_node.outlinks.values())
    return [
        veh
        for veh in mimic_W.VEHICLES_RUNNING.values()
        if veh.link in outlinks
    ]


def _rebuild_outlink_leader_followers_after_build(mimic_W, mimic_node):
    for outlink in mimic_node.outlinks.values():
        if not outlink.vehicles:
            continue
        for veh in outlink.vehicles:
            veh.leader = None
            veh.follower = None
        for index, veh in enumerate(outlink.vehicles):
            if index >= outlink.number_of_lanes:
                leader = outlink.vehicles[index - outlink.number_of_lanes]
                veh.leader = leader
                leader.follower = veh
                veh.lane = leader.lane
