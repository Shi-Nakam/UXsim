# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Phase 4-6N: batch ID 318 lifecycle at node g_4_1 for veh_1619.
# Records pre–node-revisit-fix BATCH state under clearance=0, 5000-vehicle
# high-demand conditions. Hypothesis A (stale assignment) vs B (service-unit
# deletion bug) investigation only.
#
# - Not part of the normal test suite; do not add to automated regression runs.
# - Some diagnostics in this directory exit with a known prefix violation;
#   that is intentional reproduction, not a test failure.
# - Formal record: ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md §1G
#
# Run from the repository root:
#   python diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import random
import types

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
MIN_ELIGIBLE_NODES = 32
MIN_OD_MANHATTAN_DISTANCE = 5
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
BATCH_SIZE = 10
BATCH_T_TRIGGER_LEVEL = 1
CLEARANCE_TIMESTEPS = 0

NUM_VEHICLES = 5000
DEPARTURE_START = 0
DEPARTURE_END = 500
TMAX = 30000

TARGET_NODE = "g_4_1"
TARGET_INLINK = "v_5_4_1"
TARGET_VEHICLE = "veh_1619"
TARGET_BATCH_ID = 318

lifecycle_events = []


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


OD_TO_GRID_COORD = {}
for column in range(GRID_SIZE):
    OD_TO_GRID_COORD[f"top_{column}"] = (0, column)
    OD_TO_GRID_COORD[f"bottom_{column}"] = (GRID_SIZE - 1, column)
for row in range(GRID_SIZE):
    OD_TO_GRID_COORD[f"left_{row}"] = (row, 0)
    OD_TO_GRID_COORD[f"right_{row}"] = (row, GRID_SIZE - 1)
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
            }
        )
        vehicle_index += 1
    return plans


def _add_grid_network(W):
    spacing = 1.0
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            W.addNode(_grid_node_name(row, column), column * spacing, -row * spacing)

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
                signal_group=1,
            )
            add_link(
                f"v_{row + 1}_{row}_{column}",
                lower_node,
                upper_node,
                INTERNAL_LINK_LENGTH,
                signal_group=1,
            )

    for column in range(GRID_SIZE):
        add_link(
            f"top_{column}_to_g_0_{column}",
            f"top_{column}",
            _grid_node_name(0, column),
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )
        add_link(
            f"g_0_{column}_to_top_{column}",
            _grid_node_name(0, column),
            f"top_{column}",
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )
        add_link(
            f"bottom_{column}_to_g_5_{column}",
            f"bottom_{column}",
            _grid_node_name(GRID_SIZE - 1, column),
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )
        add_link(
            f"g_5_{column}_to_bottom_{column}",
            _grid_node_name(GRID_SIZE - 1, column),
            f"bottom_{column}",
            OD_CONNECTOR_LENGTH,
            signal_group=1,
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


def _assignment_at_node(veh, node_name):
    return veh.order_control_batch_assignments.get(node_name, None)


def _snapshot_service_queue(node):
    return [
        {
            "batch_id": unit["batch_id"],
            "inlink": unit["inlink"].name,
            "vehicles": [veh.name for veh in unit["vehicles"]],
        }
        for unit in node.order_control_batch_service_queue
    ]


def _find_service_unit(snapshot, batch_id):
    for unit in snapshot:
        if unit["batch_id"] == batch_id:
            return unit
    return None


def _record_event(event_type, W, node, veh, extra=None):
    payload = {
        "T": W.T,
        "event_type": event_type,
        "node": node.name,
        "vehicle": veh.name if veh is not None else None,
        "vehicle_link": veh.link.name if veh is not None and veh.link is not None else None,
        "vehicle_x": veh.x if veh is not None else None,
        "in_incoming": veh in node.incoming_vehicles if veh is not None else None,
        "assignment": _assignment_at_node(veh, node.name) if veh is not None else None,
        "service_queue": _snapshot_service_queue(node),
    }
    if extra:
        payload.update(extra)
    lifecycle_events.append(payload)


class LifecycleTracker:
    def __init__(self, W, node):
        self.W = W
        self.node = node
        self.target_veh = W.VEHICLES[TARGET_VEHICLE]
        self.prev_incoming = False
        self.prev_link = None
        self.prev_link_obj = None
        self.prev_assignment = None
        self.prev_batch_in_queue = False
        self.arrival_count = 0
        self.pass_count = 0
        self.batch_created_T = None
        self.batch_removed_T = None

    def observe_timestep(self):
        veh = self.target_veh
        node = self.node
        incoming = veh in node.incoming_vehicles
        assignment = _assignment_at_node(veh, node.name)
        link = veh.link
        link_name = link.name if link is not None else None
        queue_snapshot = _snapshot_service_queue(node)
        batch_in_queue = _find_service_unit(queue_snapshot, TARGET_BATCH_ID) is not None

        if incoming and not self.prev_incoming:
            self.arrival_count += 1
            _record_event(
                "arrived_at_node_incoming",
                self.W,
                node,
                veh,
                {
                    "arrival_number": self.arrival_count,
                    "inlink": link_name,
                    "route_next_link": getattr(veh.route_next_link, "name", None),
                    "batch_318_in_queue": batch_in_queue,
                },
            )

        if (
            self.prev_link_obj is not None
            and self.prev_link_obj.end_node is node
            and link is not None
            and link.start_node is node
            and link_name != self.prev_link
        ):
            self.pass_count += 1
            _record_event(
                "passed_node_transfer",
                self.W,
                node,
                veh,
                {
                    "pass_number": self.pass_count,
                    "from_inlink": self.prev_link,
                    "to_outlink": link_name,
                    "assignment": assignment,
                    "batch_318_in_queue": batch_in_queue,
                    "assignment_retained_after_pass": assignment == TARGET_BATCH_ID,
                },
            )

        if batch_in_queue and not self.prev_batch_in_queue:
            pass
        if not batch_in_queue and self.prev_batch_in_queue:
            self.batch_removed_T = self.W.T
            _record_event(
                "service_unit_318_absent_from_queue",
                self.W,
                node,
                veh,
                {
                    "queue_snapshot": queue_snapshot,
                    "target_in_unit_before": None,
                    "target_link": link_name,
                    "target_in_incoming": incoming,
                    "target_assignment": assignment,
                },
            )

        self.prev_incoming = incoming
        self.prev_link = link_name
        self.prev_link_obj = link
        self.prev_assignment = assignment
        self.prev_batch_in_queue = batch_in_queue


def _install_node_wrappers(W, node, tracker):
    orig_form = node.form_order_control_batch
    orig_serve = node.serve_order_control_batch_service_queue

    def wrapped_form(s, t_trigger_level, max_batch_size):
        trigger_candidates = node.get_order_control_batch_trigger_candidates()
        trigger_vehicle = trigger_candidates[0] if trigger_candidates else None
        t_trigger = None
        if trigger_vehicle is not None:
            if t_trigger_level == 0:
                t_trigger = node.estimate_order_control_batch_t_trigger_level_0(
                    trigger_vehicle
                )
            else:
                t_trigger = node.estimate_order_control_batch_t_trigger_level_1(
                    trigger_vehicle
                )

        queue_before = _snapshot_service_queue(node)
        target_before = _assignment_at_node(tracker.target_veh, node.name)
        try:
            result = orig_form(t_trigger_level, max_batch_size)
        except ValueError as exc:
            _record_prefix_violation(W, node, tracker, exc)
            raise

        queue_after = _snapshot_service_queue(node)
        target_after = _assignment_at_node(tracker.target_veh, node.name)
        new_batch_ids = {
            unit["batch_id"] for unit in queue_after
        } - {unit["batch_id"] for unit in queue_before}

        for unit in queue_after:
            if unit["batch_id"] not in new_batch_ids:
                continue
            if unit["batch_id"] == TARGET_BATCH_ID:
                tracker.batch_created_T = W.T
                position = (
                    unit["vehicles"].index(TARGET_VEHICLE)
                    if TARGET_VEHICLE in unit["vehicles"]
                    else None
                )
                _record_event(
                    "assignment_created_and_service_unit_added",
                    W,
                    node,
                    tracker.target_veh,
                    {
                        "batch_id": unit["batch_id"],
                        "inlink": unit["inlink"],
                        "batch_vehicle_names": unit["vehicles"],
                        "target_position_in_batch": position,
                        "trigger_vehicle": trigger_vehicle.name
                        if trigger_vehicle is not None
                        else None,
                        "t_trigger": t_trigger,
                        "assignment_before": target_before,
                        "assignment_after": target_after,
                        "earliest_arrival_timestep": tracker.target_veh.order_control_earliest_arrival_timesteps.get(
                            node.name
                        ),
                        "same_timestep_as_queue_add": True,
                    },
                )

        return result

    def wrapped_serve(s):
        queue_before = _snapshot_service_queue(node)
        unit_before = _find_service_unit(queue_before, TARGET_BATCH_ID)
        veh = tracker.target_veh
        link_before = veh.link.name if veh.link is not None else None
        x_before = veh.x
        incoming_before = veh in node.incoming_vehicles
        assignment_before = _assignment_at_node(veh, node.name)
        in_unit_before = (
            TARGET_VEHICLE in unit_before["vehicles"] if unit_before is not None else False
        )
        unit_before_vehicles = list(unit_before["vehicles"]) if unit_before else []

        count = orig_serve()

        queue_after = _snapshot_service_queue(node)
        unit_after = _find_service_unit(queue_after, TARGET_BATCH_ID)
        link_after = veh.link.name if veh.link is not None else None
        x_after = veh.x
        incoming_after = veh in node.incoming_vehicles
        assignment_after = _assignment_at_node(veh, node.name)
        in_unit_after = (
            TARGET_VEHICLE in unit_after["vehicles"] if unit_after is not None else False
        )

        if in_unit_before and not in_unit_after:
            transferred = (
                link_before != link_after
                and link_before is not None
                and W.get_link(link_before).end_node is node
                and link_after is not None
                and W.get_link(link_after).start_node is node
            )
            _record_event(
                "removed_from_service_unit",
                W,
                node,
                veh,
                {
                    "batch_id": TARGET_BATCH_ID,
                    "unit_vehicles_before": unit_before_vehicles,
                    "link_before": link_before,
                    "link_after": link_after,
                    "x_before": x_before,
                    "x_after": x_after,
                    "incoming_before": incoming_before,
                    "incoming_after": incoming_after,
                    "assignment_before": assignment_before,
                    "assignment_after": assignment_after,
                    "link_transfer_occurred": transferred,
                    "service_unit_still_in_queue": unit_after is not None,
                    "transferred_vehicle_count_this_call": count,
                },
            )

        if unit_before is not None and unit_after is None:
            tracker.batch_removed_T = W.T
            _record_event(
                "service_unit_removed_from_formal_queue",
                W,
                node,
                veh,
                {
                    "batch_id": TARGET_BATCH_ID,
                    "unit_before_vehicles": unit_before_vehicles,
                    "unit_was_empty": len(unit_before_vehicles) == 0,
                    "target_still_in_unit_before_removal": in_unit_before,
                    "target_link": link_after,
                    "target_in_incoming": incoming_after,
                    "target_assignment": assignment_after,
                    "link_transfer_occurred_this_call": link_before != link_after,
                    "transferred_vehicle_count_this_call": count,
                    "queue_after": queue_after,
                },
            )

        return count

    node.form_order_control_batch = types.MethodType(wrapped_form, node)
    node.serve_order_control_batch_service_queue = types.MethodType(wrapped_serve, node)

    return orig_form, orig_serve


def _restore_node_wrappers(node, orig_form, orig_serve):
    node.form_order_control_batch = orig_form
    node.serve_order_control_batch_service_queue = orig_serve


def _record_prefix_violation(W, node, tracker, exc):
    inlink = W.get_link(TARGET_INLINK)
    veh = tracker.target_veh
    inlink_state = []
    for index, link_veh in enumerate(inlink.vehicles):
        inlink_state.append(
            {
                "index": index,
                "name": link_veh.name,
                "x": link_veh.x,
                "assignment": _assignment_at_node(link_veh, TARGET_NODE),
                "in_incoming": link_veh in node.incoming_vehicles,
            }
        )
    _record_event(
        "prefix_violation_detected",
        W,
        node,
        veh,
        {
            "exception_message": str(exc),
            "service_queue_full": _snapshot_service_queue(node),
            "inlink_vehicles": inlink_state,
            "link_history_tail": list(tracker.target_veh.log_t_link[-30:]),
            "arrival_count": tracker.arrival_count,
            "pass_count": tracker.pass_count,
            "batch_created_T": tracker.batch_created_T,
            "batch_removed_T": tracker.batch_removed_T,
        },
    )


def _build_batch_world(vehicle_plans, tmax):
    W = World(
        name="batch_assignment_318_lifecycle",
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
    W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    eligible_node_names = [node.name for node in W.NODES if node.order_control_eligible]
    assert len(eligible_node_names) >= MIN_ELIGIBLE_NODES
    W.set_order_control_for_nodes(
        eligible_node_names,
        order_control_type="batch",
        batch_size=BATCH_SIZE,
        order_control_batch_t_trigger_level=BATCH_T_TRIGGER_LEVEL,
    )
    return W


def _print_lifecycle_timeline():
    print("\n" + "=" * 72)
    print("Lifecycle event timeline (target-related only)")
    print("=" * 72)
    for event in lifecycle_events:
        print(f"\nW.T = {event['T']}: {event['event_type']}")
        for key, value in event.items():
            if key in {"T", "event_type"}:
                continue
            print(f"  {key}: {value}")


def run_batch_assignment_318_lifecycle_diagnostic():
    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )
    W = _build_batch_world(vehicle_plans, TMAX)
    node = W.get_node(TARGET_NODE)
    tracker = LifecycleTracker(W, node)
    orig_form, orig_serve = _install_node_wrappers(W, node, tracker)

    W.finalize_scenario()
    try:
        while W.T < TMAX:
            W.exec_simulation(duration_t2=W.DELTAT)
            tracker.observe_timestep()
            if W.T >= W.TSIZE:
                break
    except ValueError:
        tracker.observe_timestep()
        _print_lifecycle_timeline()
        raise
    finally:
        _restore_node_wrappers(node, orig_form, orig_serve)

    _print_lifecycle_timeline()
    print("\nSimulation completed without prefix violation (unexpected for this case).")


if __name__ == "__main__":
    run_batch_assignment_318_lifecycle_diagnostic()
