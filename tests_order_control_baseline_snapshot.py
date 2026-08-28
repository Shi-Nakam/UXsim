# Unit tests for snapshot-fixed baseline visit registration (design memo §25.22).
#
# Run from the repository root:
#   python tests_order_control_baseline_snapshot.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_snapshot import register_snapshot_fixed_visits


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _new_collector() -> OrderControlBaselineCollector:
    return OrderControlBaselineCollector()


def _build_time_value_junction_world(name="snapshot_time_value_junction"):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode(
        "junction",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("dest", 2, 0)
    W.addLink("in", "orig", "junction", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "junction", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_time_value_merge_world(name="snapshot_time_value_merge"):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_two_time_value_nodes_world(name="snapshot_two_time_value_nodes"):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig_a", 0, 0)
    W.addNode(
        "junction_a",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("mid", 2, 0)
    W.addNode(
        "junction_b",
        3,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("dest", 4, 0)
    W.addLink("in_a", "orig_a", "junction_a", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("mid_link", "junction_a", "mid", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("in_b", "mid", "junction_b", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out_b", "junction_b", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_node_type_world(order_control_type, *, eligible=True, node_name="junction"):
    W = World(
        name=f"snapshot_node_type_{order_control_type}",
        deltan=1,
        tmax=50,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode(
        node_name,
        1,
        0,
        order_control_eligible=eligible,
        order_control_type=order_control_type,
    )
    W.addNode("dest", 2, 0)
    W.addLink("in", "orig", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", node_name, "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _advance_until_on_inlink(vehicle, inlink_name):
    while vehicle.link is None or vehicle.link.name != inlink_name:
        if not vehicle.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {inlink_name}")
        vehicle.W.exec_simulation(duration_t2=vehicle.W.DELTAT)


def _place_arrived_vehicle_at_snapshot(
    W,
    vehicle,
    *,
    inlink_name,
    target_node_name,
    outlink_name,
    arrival_timestep,
    arrival_tiebreaker=0.25,
    snapshot_timestep,
):
    inlink = W.get_link(inlink_name)
    outlink = W.get_link(outlink_name)
    target_node = W.get_node(target_node_name)
    W.T = snapshot_timestep
    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = inlink.length
    vehicle.route_next_link = outlink
    vehicle.link_arrival_time = float(arrival_timestep * W.DELTAT)
    if vehicle not in inlink.vehicles:
        inlink.vehicles.append(vehicle)
    if vehicle not in target_node.incoming_vehicles:
        target_node.incoming_vehicles.append(vehicle)
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise AssertionError("Expected current visit before arrived placement")
    current_visit["arrival_time"] = arrival_timestep * W.DELTAT
    current_visit["arrival_tiebreaker"] = arrival_tiebreaker


def _place_not_yet_arrived_vehicle_at_snapshot(
    W,
    vehicle,
    *,
    inlink_name,
    snapshot_timestep,
    x_position=180.0,
):
    inlink = W.get_link(inlink_name)
    W.T = snapshot_timestep
    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = x_position
    vehicle.link_arrival_time = float((snapshot_timestep - 1) * W.DELTAT)
    if vehicle not in inlink.vehicles:
        inlink.vehicles.append(vehicle)
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise AssertionError("Expected current visit before not-yet-arrived placement")
    current_visit["arrival_time"] = None
    current_visit["arrival_tiebreaker"] = None


def _collector_is_empty(collector):
    return (
        collector.export_node_baseline_visits("junction") == []
        and collector.export_node_baseline_visits("merge") == []
        and collector.export_node_baseline_visits("junction_a") == []
        and collector.export_node_baseline_visits("junction_b") == []
        and collector.get_baseline_visit_snapshot("unused", 1) is None
    )


def _expect_value_error(test_callable, expected_substring):
    try:
        test_callable()
    except ValueError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected ValueError")


# --- target node input validation ---


def test_rejects_empty_target_node_names():
    W = _build_time_value_junction_world()
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(W, collector, target_node_names=[]),
        "must not be empty",
    )
    assert _collector_is_empty(collector)


def test_rejects_duplicate_target_node_names():
    W = _build_time_value_junction_world()
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction", "junction"]
        ),
        "Duplicate target node name",
    )
    assert _collector_is_empty(collector)


def test_rejects_target_node_names_as_single_string():
    W = _build_time_value_junction_world()
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names="junction"
        ),
        "not a single string",
    )
    assert _collector_is_empty(collector)


def test_rejects_non_string_target_node_name():
    W = _build_time_value_junction_world()
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction", 123]
        ),
        "non-empty str",
    )
    assert _collector_is_empty(collector)


def test_rejects_empty_string_target_node_name():
    W = _build_time_value_junction_world()
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(W, collector, target_node_names=[""]),
        "non-empty str",
    )
    assert _collector_is_empty(collector)


def test_rejects_missing_target_node_name():
    W = _build_time_value_junction_world()
    collector = _new_collector()
    try:
        register_snapshot_fixed_visits(
            W, collector, target_node_names=["missing_node"]
        )
    except ValueError as exc:
        if "does not exist" not in str(exc):
            raise AssertionError(
                f"Expected missing-node message in error: {exc}"
            ) from exc
        if "missing_node" not in str(exc):
            raise AssertionError(
                f"Expected target node name in error: {exc}"
            ) from exc
        if exc.__cause__ is None:
            raise AssertionError("Expected ValueError.__cause__ to be set")
        if not isinstance(exc.__cause__, Exception):
            raise AssertionError(
                f"Expected Exception as __cause__, got {type(exc.__cause__)}"
            )
        if "missing_node" not in str(exc.__cause__):
            raise AssertionError(
                f"Expected original exception to mention missing_node: {exc.__cause__}"
            )
    else:
        raise AssertionError("Expected ValueError")
    assert _collector_is_empty(collector)


def test_rejects_non_eligible_target_node():
    W = _build_node_type_world("none")
    junction = W.get_node("junction")
    junction.order_control_eligible = False
    junction.order_control_type = "time_value"
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "not order-control eligible",
    )
    assert _collector_is_empty(collector)


def test_rejects_none_order_control_type_target_node():
    W = _build_node_type_world("none")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "only 'time_value'",
    )
    assert _collector_is_empty(collector)


def test_rejects_fcfs_order_control_type_target_node():
    W = _build_node_type_world("fcfs")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "only 'time_value'",
    )
    assert _collector_is_empty(collector)


def test_rejects_batch_order_control_type_target_node():
    W = _build_node_type_world("batch")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "only 'time_value'",
    )
    assert _collector_is_empty(collector)


def test_accepts_multiple_valid_time_value_nodes():
    W = _build_two_time_value_nodes_world()
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W,
        collector,
        target_node_names=["junction_a", "junction_b"],
    )
    assert count == 0
    assert collector.export_node_baseline_visits("junction_a") == []
    assert collector.export_node_baseline_visits("junction_b") == []


# --- arrived vehicle registration ---


def test_registers_arrived_vehicle_only():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_only")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1
    snapshot = collector.get_baseline_visit_snapshot(vehicle.name, vehicle.order_control_visit_id)
    assert snapshot["was_arrived_at_snapshot"] is True
    assert snapshot["baseline_arrival_timestep"] == 10
    assert snapshot["arrival_tiebreaker"] == 0.25
    assert snapshot["route_next_link_name"] == "out"
    assert snapshot["baseline_passage_timestep"] is None
    assert snapshot["node_name"] == "junction"
    assert snapshot["inlink_name"] == "in"
    assert snapshot["vehicle_id"] == vehicle.id


def test_arrived_vehicle_in_incoming_and_inlink_registers_once():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="dual_container")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    junction = W.get_node("junction")
    inlink = W.get_link("in")
    assert vehicle in junction.incoming_vehicles
    assert vehicle in inlink.vehicles
    # Same node, visit, and inlink: normal arrived-vehicle reappearance on inlink scan.
    assert vehicle.order_control_current_visit["node"] is junction
    assert vehicle.order_control_current_visit["inlink"] is inlink
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1


def test_arrived_vehicle_includes_participates_false():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle(
        "orig",
        "dest",
        0,
        name="arrived_non_participant",
        participates_in_order_exchange=False,
    )
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1


def test_rejects_arrived_vehicle_missing_current_visit():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_no_visit")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.order_control_current_visit = None
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "order_control_current_visit=None",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_missing_required_current_visit_key():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_missing_key")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    del vehicle.order_control_current_visit["arrival_tiebreaker"]
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "missing current visit key 'arrival_tiebreaker'",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_visit_id_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_visit_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.order_control_visit_id += 1
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "order_control_visit_id",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_current_visit_node_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_node_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.order_control_current_visit["node"] = W.get_node("dest")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "does not match target node",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_current_visit_inlink_mismatch():
    W = _build_time_value_merge_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig1", "dest", 0, name="arrived_inlink_mismatch")
    _advance_until_on_inlink(vehicle, "link1")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="link1",
        target_node_name="merge",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.order_control_current_visit["inlink"] = W.get_link("link2")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["merge"]
        ),
        "does not match current visit inlink",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_link_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_link_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.link = W.get_link("out")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "does not match current visit inlink",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_missing_from_inlink_vehicles():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_not_on_inlink")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    W.get_link("in").vehicles.remove(vehicle)
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "not in inlink",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_partial_arrival_information():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_partial_arrival")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.order_control_current_visit["arrival_tiebreaker"] = None
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "inconsistent arrival state",
    )
    assert _collector_is_empty(collector)


def test_rejects_incoming_vehicle_without_arrival_information():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="incoming_without_arrival")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.order_control_current_visit["arrival_time"] = None
    vehicle.order_control_current_visit["arrival_tiebreaker"] = None
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "does not have arrival information",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_missing_route_next_link():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_no_route_next")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.route_next_link = None
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "route_next_link=None",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_route_next_link_start_node_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_route_start_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.route_next_link = W.get_link("in")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "does not start at target node",
    )
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_with_arrival_timestep_at_or_after_snapshot_T():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_too_late")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "must have arrived before T",
    )
    assert _collector_is_empty(collector)


# --- not-yet-arrived vehicle registration ---


def test_registers_not_yet_arrived_vehicle_only():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_only")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1
    snapshot = collector.get_baseline_visit_snapshot(vehicle.name, vehicle.order_control_visit_id)
    assert snapshot["was_arrived_at_snapshot"] is False
    assert snapshot["baseline_arrival_timestep"] is None
    assert snapshot["arrival_tiebreaker"] is None
    assert snapshot["route_next_link_name"] is None
    assert snapshot["baseline_passage_timestep"] is None
    assert snapshot["node_name"] == "junction"
    assert snapshot["inlink_name"] == "in"


def test_not_yet_arrived_vehicle_ignores_snapshot_route_next_link_value():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_route_next")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.route_next_link = W.get_link("out")
    collector = _new_collector()
    register_snapshot_fixed_visits(W, collector, target_node_names=["junction"])
    snapshot = collector.get_baseline_visit_snapshot(vehicle.name, vehicle.order_control_visit_id)
    assert snapshot["route_next_link_name"] is None


def test_not_yet_arrived_vehicle_includes_participates_false():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle(
        "orig",
        "dest",
        0,
        name="not_yet_arrived_non_participant",
        participates_in_order_exchange=False,
    )
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1


def test_rejects_not_yet_arrived_vehicle_missing_current_visit():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_no_visit")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.order_control_current_visit = None
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "order_control_current_visit=None",
    )
    assert _collector_is_empty(collector)


def test_rejects_not_yet_arrived_vehicle_visit_id_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_visit_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.order_control_visit_id += 1
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "order_control_visit_id",
    )
    assert _collector_is_empty(collector)


def test_rejects_not_yet_arrived_vehicle_current_visit_node_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_node_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.order_control_current_visit["node"] = W.get_node("dest")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "does not match target node",
    )
    assert _collector_is_empty(collector)


def test_rejects_not_yet_arrived_vehicle_current_visit_inlink_mismatch():
    W = _build_time_value_merge_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig1", "dest", 0, name="not_yet_arrived_inlink_mismatch")
    _advance_until_on_inlink(vehicle, "link1")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="link1", snapshot_timestep=snapshot_T
    )
    vehicle.order_control_current_visit["inlink"] = W.get_link("link2")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["merge"]
        ),
        "does not match scanned inlink",
    )
    assert _collector_is_empty(collector)


def test_rejects_not_yet_arrived_vehicle_link_mismatch():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_link_mismatch")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.link = W.get_link("out")
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "does not match scanned inlink",
    )
    assert _collector_is_empty(collector)


def test_rejects_not_yet_arrived_vehicle_partial_arrival_information():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_partial_arrival")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.order_control_current_visit["arrival_time"] = 5.0
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "inconsistent arrival state",
    )
    assert _collector_is_empty(collector)


def test_rejects_not_yet_arrived_vehicle_also_in_incoming_vehicles():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="not_yet_arrived_in_incoming")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    W.get_node("junction").incoming_vehicles.append(vehicle)
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "incoming_vehicles",
    )
    assert _collector_is_empty(collector)


# --- arrived and not-yet-arrived combinations ---


def test_registers_arrived_and_not_yet_arrived_on_same_node():
    W = _build_time_value_merge_world()
    snapshot_T = 20
    W.T = snapshot_T
    arrived_vehicle = W.addVehicle("orig1", "dest", 0, name="arrived_on_merge")
    not_yet_arrived_vehicle = W.addVehicle("orig2", "dest", 0, name="not_yet_arrived_on_merge")
    _advance_until_on_inlink(arrived_vehicle, "link1")
    _advance_until_on_inlink(not_yet_arrived_vehicle, "link2")
    _place_arrived_vehicle_at_snapshot(
        W,
        arrived_vehicle,
        inlink_name="link1",
        target_node_name="merge",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    _place_not_yet_arrived_vehicle_at_snapshot(
        W,
        not_yet_arrived_vehicle,
        inlink_name="link2",
        snapshot_timestep=snapshot_T,
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(W, collector, target_node_names=["merge"])
    assert count == 2
    exports = collector.export_node_baseline_visits("merge")
    assert len(exports) == 2


def test_registers_multiple_inlinks_on_same_node():
    W = _build_time_value_merge_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle1 = W.addVehicle("orig1", "dest", 0, name="merge_inlink1")
    vehicle2 = W.addVehicle("orig2", "dest", 0, name="merge_inlink2")
    _advance_until_on_inlink(vehicle1, "link1")
    _advance_until_on_inlink(vehicle2, "link2")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle1, inlink_name="link1", snapshot_timestep=snapshot_T
    )
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle2, inlink_name="link2", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(W, collector, target_node_names=["merge"])
    assert count == 2


def test_registers_multiple_time_value_nodes():
    W = _build_two_time_value_nodes_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle_a = W.addVehicle("orig_a", "dest", 0, name="node_a_vehicle")
    _advance_until_on_inlink(vehicle_a, "in_a")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle_a, inlink_name="in_a", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction_a", "junction_b"]
    )
    assert count == 1
    assert len(collector.export_node_baseline_visits("junction_a")) == 1
    assert collector.export_node_baseline_visits("junction_b") == []


def test_does_not_register_arrived_vehicle_twice_from_inlink_scan():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_no_double_b")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    junction = W.get_node("junction")
    inlink = W.get_link("in")
    assert vehicle in junction.incoming_vehicles
    assert vehicle in inlink.vehicles
    assert vehicle.order_control_current_visit["node"] is junction
    assert vehicle.order_control_current_visit["inlink"] is inlink
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1


def test_rejects_undetected_arrived_vehicle_on_inlink_only():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="inlink_only_arrived")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    W.get_node("junction").incoming_vehicles.remove(vehicle)
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "already has arrival information at snapshot time",
    )
    assert _collector_is_empty(collector)


def test_rejects_duplicate_arrived_vehicle_in_incoming_vehicles():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="duplicate_incoming_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    junction = W.get_node("junction")
    junction.incoming_vehicles.append(vehicle)
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "multiple snapshot-fixed visits",
    )
    assert _collector_is_empty(collector)


def test_rejects_same_vehicle_as_arrived_on_one_node_and_candidate_on_another():
    """
    Defensive abnormal-state test.

    One physical Vehicle object cannot normally occupy two links at once. This
    test places the same object on a second target node's inlink after it was
    registered as arrived (A) on the first node. The vehicle name is in
    arrived_vehicle_names, but the second appearance is on a different node, so
    _handle_arrived_vehicle_name_seen_on_inlink() raises instead of skipping.
    """
    W = _build_two_time_value_nodes_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig_a", "dest", 0, name="cross_node_duplicate_vehicle")
    _advance_until_on_inlink(vehicle, "in_a")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in_a",
        target_node_name="junction_a",
        outlink_name="mid_link",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    planned_visit_id = vehicle.order_control_visit_id

    # Abnormal: same Vehicle object also listed on junction_b inlink. Keep the
    # current visit pointing at junction_a so junction_a incoming registration
    # succeeds first; junction_b inlink scan must then reject the cross-node
    # reappearance.
    in_b = W.get_link("in_b")
    in_b.vehicles.append(vehicle)

    collector = _new_collector()
    try:
        register_snapshot_fixed_visits(
            W,
            collector,
            target_node_names=["junction_a", "junction_b"],
        )
        raise AssertionError("Expected ValueError for cross-node duplicate vehicle")
    except ValueError as exc:
        message = str(exc)
        assert "cross_node_duplicate_vehicle" in message
        assert "junction_a" in message
        assert "junction_b" in message
        assert str(planned_visit_id) in message
        assert "multiple snapshot-fixed visits" in message
    assert _collector_is_empty(collector)


def test_rejects_arrived_vehicle_abnormal_reappearance_on_different_inlink():
    """
    Defensive abnormal-state test.

    The same vehicle name is registered as arrived (A) from link1, then also
    appears on link2 of the same node during inlink scan. This is not the
    normal dual-container reappearance and must raise ValueError.
    """
    W = _build_time_value_merge_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig1", "dest", 0, name="different_inlink_reappearance")
    _advance_until_on_inlink(vehicle, "link1")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="link1",
        target_node_name="merge",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    planned_visit_id = vehicle.order_control_visit_id
    planned_inlink_name = "link1"
    abnormal_inlink_name = "link2"

    # Abnormal: same Vehicle object also listed on a different inlink deque.
    W.get_link(abnormal_inlink_name).vehicles.append(vehicle)

    collector = _new_collector()
    try:
        register_snapshot_fixed_visits(W, collector, target_node_names=["merge"])
        raise AssertionError(
            "Expected ValueError for abnormal arrived reappearance on different inlink"
        )
    except ValueError as exc:
        message = str(exc)
        assert "different_inlink_reappearance" in message
        assert "merge" in message
        assert planned_inlink_name in message
        assert f"scanning inlink {abnormal_inlink_name!r}" in message
        assert str(planned_visit_id) in message
    assert _collector_is_empty(collector)


def test_validation_failure_leaves_collector_empty():
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="validation_failure")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    vehicle.route_next_link = None
    collector = _new_collector()
    _expect_value_error(
        lambda: register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        ),
        "route_next_link=None",
    )
    assert collector.export_node_baseline_visits("junction") == []


def test_returns_total_registration_count():
    W = _build_time_value_merge_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle1 = W.addVehicle("orig1", "dest", 0, name="count_vehicle1")
    vehicle2 = W.addVehicle("orig2", "dest", 0, name="count_vehicle2")
    _advance_until_on_inlink(vehicle1, "link1")
    _advance_until_on_inlink(vehicle2, "link2")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle1, inlink_name="link1", snapshot_timestep=snapshot_T
    )
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle2, inlink_name="link2", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(W, collector, target_node_names=["merge"])
    assert count == 2


def test_node_export_contents_match_registration():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="export_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    register_snapshot_fixed_visits(W, collector, target_node_names=["junction"])
    exports = collector.export_node_baseline_visits("junction")
    assert len(exports) == 1
    assert exports[0]["vehicle_name"] == "export_vehicle"
    assert exports[0]["was_arrived_at_snapshot"] is False


# --- normal exclusions ---


def test_skips_state_end_vehicle_on_inlink():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="ended_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.state = "end"
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 0


def test_skips_state_abort_vehicle_on_inlink():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="aborted_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.state = "abort"
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 0


def test_skips_flag_waiting_for_trip_end_vehicle_on_inlink():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="trip_end_wait_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.flag_waiting_for_trip_end = 1
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 0


def test_skips_taxi_mode_vehicle_on_inlink():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="taxi_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.mode = "taxi"
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 0


def test_skips_specified_route_vehicle_on_inlink():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="specified_route_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    vehicle.specified_route = [W.get_link("in"), W.get_link("out")]
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 0


def test_does_not_skip_participates_false_vehicle_on_inlink():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    vehicle = W.addVehicle(
        "orig",
        "dest",
        0,
        name="participant_false_vehicle",
        participates_in_order_exchange=False,
    )
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1


# --- timestep T boundary via exec_simulation ---


def test_timestep_T_not_yet_arrived_vehicle_registers_then_arrives_on_exec():
    W = _build_time_value_junction_world()
    outlink = W.get_link("out")
    outlink.capacity_in_remain = 0.0
    W.get_node("junction").flow_capacity_remain = 0.0

    baseline_T = 10
    vehicle = W.addVehicle("orig", "dest", 0, name="timestep_T_vehicle")
    W.exec_simulation(duration_t2=baseline_T * W.DELTAT)
    assert W.T == baseline_T

    visit = vehicle.order_control_current_visit
    assert visit is not None
    assert visit["node"].name == "junction"
    assert visit["inlink"].name == "in"
    assert visit["arrival_time"] is None
    assert visit["arrival_tiebreaker"] is None
    assert vehicle not in W.get_node("junction").incoming_vehicles

    collector = _new_collector()
    W._order_control_baseline_collector = collector
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1
    snapshot_before_exec = collector.get_baseline_visit_snapshot(
        vehicle.name, visit["visit_id"]
    )
    assert snapshot_before_exec["was_arrived_at_snapshot"] is False
    assert snapshot_before_exec["baseline_arrival_timestep"] is None

    W.exec_simulation(duration_t2=W.DELTAT)
    assert W.T == baseline_T + 1

    snapshot_after_exec = collector.get_baseline_visit_snapshot(
        vehicle.name, visit["visit_id"]
    )
    assert snapshot_after_exec["baseline_arrival_timestep"] == baseline_T
    assert snapshot_after_exec["was_arrived_at_snapshot"] is False


def test_registration_does_not_add_later_inlink_vehicle_to_collector():
    W = _build_time_value_junction_world()
    snapshot_T = 10
    W.T = snapshot_T
    first_vehicle = W.addVehicle("orig", "dest", 0, name="first_registered")
    _advance_until_on_inlink(first_vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, first_vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    collector = _new_collector()
    register_snapshot_fixed_visits(W, collector, target_node_names=["junction"])

    second_vehicle = W.addVehicle("orig", "dest", 0, name="later_vehicle")
    _advance_until_on_inlink(second_vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, second_vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    assert collector.get_baseline_visit_snapshot(
        second_vehicle.name, second_vehicle.order_control_visit_id
    ) is None


def test_collector_validation_failure_leaves_real_collector_empty():
    """
    When registration_plan contains a value that passes snapshot-side checks but
    fails collector.register_snapshot_visit(), the real collector must remain
    empty because validation runs on a temporary collector first.
    """
    W = _build_time_value_junction_world()
    snapshot_T = 20
    W.T = snapshot_T
    first_vehicle = W.addVehicle("orig", "dest", 0, name="valid_arrived_vehicle")
    _advance_until_on_inlink(first_vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        first_vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    second_vehicle = W.addVehicle("orig", "dest", 0, name="invalid_tiebreaker_vehicle")
    _advance_until_on_inlink(second_vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        second_vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=11,
        arrival_tiebreaker=True,
        snapshot_timestep=snapshot_T,
    )
    collector = _new_collector()
    try:
        register_snapshot_fixed_visits(
            W, collector, target_node_names=["junction"]
        )
        raise AssertionError("Expected ValueError for collector validation failure")
    except ValueError as exc:
        if "arrival_tiebreaker must be an int or float (not bool)" not in str(exc):
            raise AssertionError(
                f"Expected arrival_tiebreaker validation error: {exc}"
            ) from exc
    assert _collector_is_empty(collector)


class _BrokenForkWorld:
    def get_node(self, node_name):
        raise RuntimeError("unexpected get_node failure")


def test_propagates_unexpected_get_node_exception_without_node_missing_conversion():
    collector = _new_collector()
    fork_W = _BrokenForkWorld()
    try:
        register_snapshot_fixed_visits(
            fork_W, collector, target_node_names=["junction"]
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as exc:
        if str(exc) != "unexpected get_node failure":
            raise AssertionError(
                f"Expected original RuntimeError message: {exc}"
            ) from exc
    except ValueError as exc:
        raise AssertionError(
            f"Expected RuntimeError, not ValueError: {exc}"
        ) from exc
    assert _collector_is_empty(collector)


def test_exec_simulation_arrived_vehicle_registers_as_arrived_at_snapshot():
    W = _build_time_value_junction_world()
    outlink = W.get_link("out")
    blocker = W.addVehicle(
        "orig", "dest", 0, name="outlink_blocker_vehicle"
    )
    blocker.link = outlink
    blocker.state = "run"
    blocker.x = 0.0
    blocker.link_arrival_time = 0.0
    if blocker not in outlink.vehicles:
        outlink.vehicles.append(blocker)

    snapshot_T = 20
    vehicle = W.addVehicle("orig", "dest", 0, name="exec_arrived_vehicle")
    W.exec_simulation(duration_t2=snapshot_T * W.DELTAT)
    assert W.T == snapshot_T

    junction = W.get_node("junction")
    inlink = W.get_link("in")
    visit = vehicle.order_control_current_visit
    assert visit is not None
    assert visit["arrival_time"] is not None
    assert visit["arrival_tiebreaker"] is not None
    assert vehicle in junction.incoming_vehicles
    assert vehicle in inlink.vehicles
    assert vehicle.route_next_link is not None
    assert vehicle.route_next_link.name == "out"

    collector = _new_collector()
    count = register_snapshot_fixed_visits(
        W, collector, target_node_names=["junction"]
    )
    assert count == 1
    expected_arrival_timestep = int(round(visit["arrival_time"] / W.DELTAT))
    assert expected_arrival_timestep < snapshot_T
    snapshot = collector.get_baseline_visit_snapshot(
        vehicle.name, visit["visit_id"]
    )
    assert snapshot["was_arrived_at_snapshot"] is True
    assert snapshot["baseline_arrival_timestep"] == expected_arrival_timestep
    assert snapshot["arrival_tiebreaker"] == visit["arrival_tiebreaker"]
    assert snapshot["route_next_link_name"] == "out"


def test_rejects_not_yet_arrived_vehicle_reappearing_on_different_node():
    """
    Defensive abnormal-state test for B on junction_a with the same Vehicle object
    also listed on junction_b inlink.

    B vehicles are not added to arrived_vehicle_names, so this reappearance must
    not be silently skipped. With veh.link still on in_a while scanning in_b, the
    junction_b inlink scan raises link mismatch before _record_planned_vehicle_name()
    duplicate detection.
    """
    W = _build_two_time_value_nodes_world()
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig_a", "dest", 0, name="cross_node_b_vehicle")
    _advance_until_on_inlink(vehicle, "in_a")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in_a", snapshot_timestep=snapshot_T
    )
    in_b = W.get_link("in_b")
    in_b.vehicles.append(vehicle)

    collector = _new_collector()
    try:
        register_snapshot_fixed_visits(
            W,
            collector,
            target_node_names=["junction_a", "junction_b"],
        )
        raise AssertionError(
            "Expected ValueError for cross-node B vehicle reappearance"
        )
    except ValueError as exc:
        message = str(exc)
        assert "cross_node_b_vehicle" in message
        assert "in_b" in message
        assert "does not match scanned inlink" in message
    assert _collector_is_empty(collector)


TESTS = [
    test_rejects_empty_target_node_names,
    test_rejects_duplicate_target_node_names,
    test_rejects_target_node_names_as_single_string,
    test_rejects_non_string_target_node_name,
    test_rejects_empty_string_target_node_name,
    test_rejects_missing_target_node_name,
    test_propagates_unexpected_get_node_exception_without_node_missing_conversion,
    test_rejects_non_eligible_target_node,
    test_rejects_none_order_control_type_target_node,
    test_rejects_fcfs_order_control_type_target_node,
    test_rejects_batch_order_control_type_target_node,
    test_accepts_multiple_valid_time_value_nodes,
    test_registers_arrived_vehicle_only,
    test_exec_simulation_arrived_vehicle_registers_as_arrived_at_snapshot,
    test_arrived_vehicle_in_incoming_and_inlink_registers_once,
    test_arrived_vehicle_includes_participates_false,
    test_rejects_arrived_vehicle_missing_current_visit,
    test_rejects_arrived_vehicle_missing_required_current_visit_key,
    test_rejects_arrived_vehicle_visit_id_mismatch,
    test_rejects_arrived_vehicle_current_visit_node_mismatch,
    test_rejects_arrived_vehicle_current_visit_inlink_mismatch,
    test_rejects_arrived_vehicle_link_mismatch,
    test_rejects_arrived_vehicle_missing_from_inlink_vehicles,
    test_rejects_arrived_vehicle_partial_arrival_information,
    test_rejects_incoming_vehicle_without_arrival_information,
    test_rejects_arrived_vehicle_missing_route_next_link,
    test_rejects_arrived_vehicle_route_next_link_start_node_mismatch,
    test_rejects_arrived_vehicle_with_arrival_timestep_at_or_after_snapshot_T,
    test_registers_not_yet_arrived_vehicle_only,
    test_not_yet_arrived_vehicle_ignores_snapshot_route_next_link_value,
    test_not_yet_arrived_vehicle_includes_participates_false,
    test_rejects_not_yet_arrived_vehicle_missing_current_visit,
    test_rejects_not_yet_arrived_vehicle_visit_id_mismatch,
    test_rejects_not_yet_arrived_vehicle_current_visit_node_mismatch,
    test_rejects_not_yet_arrived_vehicle_current_visit_inlink_mismatch,
    test_rejects_not_yet_arrived_vehicle_link_mismatch,
    test_rejects_not_yet_arrived_vehicle_partial_arrival_information,
    test_rejects_not_yet_arrived_vehicle_also_in_incoming_vehicles,
    test_registers_arrived_and_not_yet_arrived_on_same_node,
    test_registers_multiple_inlinks_on_same_node,
    test_registers_multiple_time_value_nodes,
    test_does_not_register_arrived_vehicle_twice_from_inlink_scan,
    test_rejects_undetected_arrived_vehicle_on_inlink_only,
    test_rejects_duplicate_arrived_vehicle_in_incoming_vehicles,
    test_rejects_same_vehicle_as_arrived_on_one_node_and_candidate_on_another,
    test_rejects_not_yet_arrived_vehicle_reappearing_on_different_node,
    test_rejects_arrived_vehicle_abnormal_reappearance_on_different_inlink,
    test_validation_failure_leaves_collector_empty,
    test_collector_validation_failure_leaves_real_collector_empty,
    test_returns_total_registration_count,
    test_node_export_contents_match_registration,
    test_skips_state_end_vehicle_on_inlink,
    test_skips_state_abort_vehicle_on_inlink,
    test_skips_flag_waiting_for_trip_end_vehicle_on_inlink,
    test_skips_taxi_mode_vehicle_on_inlink,
    test_skips_specified_route_vehicle_on_inlink,
    test_does_not_skip_participates_false_vehicle_on_inlink,
    test_timestep_T_not_yet_arrived_vehicle_registers_then_arrives_on_exec,
    test_registration_does_not_add_later_inlink_vehicle_to_collector,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control baseline snapshot tests passed.")
