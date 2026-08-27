# UXsim connection tests for OrderControlBaselineCollector (design memo §25.15 phase 2).
#
# Run from the repository root:
#   python tests_order_control_baseline_collector_uxsim.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy
import pickle

import numpy as np

from uxsim import World
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _rng_state_bytes(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


def _build_fcfs_clearance_world(name="baseline_collector_fcfs"):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
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
        order_control_type="fcfs",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(0)
    _prepare_network(W)
    return W


def _build_batch_world(name="baseline_collector_batch"):
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
        order_control_type="batch",
        batch_size=1,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_time_value_transfer_world(name="baseline_collector_time_value"):
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


def _build_normal_transfer_world(name="baseline_collector_normal_transfer"):
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
    W.addNode("junction", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink("in", "orig", "junction", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "junction", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _boost_transfer_capacity(node, *links):
    for link in links:
        link.capacity_in_remain = 1e6
        link.capacity_out_remain = 1e6
    node.flow_capacity_remain = 1e6


def _advance_until_on_link(veh, link_name):
    while veh.link is None or veh.link.name != link_name:
        if not veh.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {link_name}")
        veh.W.exec_simulation(duration_t2=1)


def _vehicle_traffic_snapshot(W, vehicle_names):
    snapshot = {}
    for name in vehicle_names:
        veh = W.VEHICLES[name]
        snapshot[name] = {
            "state": veh.state,
            "arrival_time": veh.arrival_time,
            "travel_time": veh.travel_time,
            "link_name": None if veh.link is None else veh.link.name,
        }
    return snapshot


def _register_b_snapshot(collector, veh, *, node_name, inlink_name, visit_id):
    collector.register_snapshot_visit(
        vehicle_name=veh.name,
        vehicle_id=veh.id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )


def _register_arrived_a_snapshot(
    collector,
    veh,
    *,
    node_name,
    inlink_name,
    visit_id,
    arrival_timestep,
    tiebreaker,
    route_next_link_name,
):
    collector.register_snapshot_visit(
        vehicle_name=veh.name,
        vehicle_id=veh.id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=arrival_timestep,
        arrival_tiebreaker=tiebreaker,
        route_next_link_name=route_next_link_name,
        baseline_passage_timestep=None,
    )


def test_collector_disabled_traffic_and_rng_unchanged():
    W_default = _build_fcfs_clearance_world("collector_disabled_default")
    W_explicit = _build_fcfs_clearance_world("collector_disabled_explicit")
    W_explicit._order_control_baseline_collector = None

    for W in (W_default, W_explicit):
        W.addVehicle("orig1", "dest", 0, name="veh1")
        W.addVehicle("orig2", "dest", 0, name="veh2")

    rng_before_default = _rng_state_bytes(W_default.rng)
    oc_rng_before_default = _rng_state_bytes(W_default.order_control_rng)
    rng_before_explicit = _rng_state_bytes(W_explicit.rng)
    oc_rng_before_explicit = _rng_state_bytes(W_explicit.order_control_rng)

    W_default.exec_simulation()
    W_explicit.exec_simulation()

    assert _vehicle_traffic_snapshot(W_default, ["veh1", "veh2"]) == (
        _vehicle_traffic_snapshot(W_explicit, ["veh1", "veh2"])
    )
    assert _rng_state_bytes(W_default.rng) == _rng_state_bytes(W_explicit.rng)
    assert _rng_state_bytes(W_default.order_control_rng) == (
        _rng_state_bytes(W_explicit.order_control_rng)
    )
    assert W_default._order_control_baseline_collector is None
    assert W_explicit._order_control_baseline_collector is None
    assert rng_before_default != _rng_state_bytes(W_default.rng)
    assert oc_rng_before_default == _rng_state_bytes(W_default.order_control_rng)


def test_b_arrival_notification_records_baseline_facts():
    W = _build_fcfs_clearance_world("collector_b_arrival")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector

    veh = W.addVehicle("orig1", "dest", 0, name="veh_b")
    _advance_until_on_link(veh, "link1")

    visit_id = veh.order_control_visit_id
    assert visit_id >= 1
    _register_b_snapshot(
        collector,
        veh,
        node_name="merge",
        inlink_name="link1",
        visit_id=visit_id,
    )

    link1 = W.get_link("link1")
    out = W.get_link("out")
    merge = W.get_node("merge")
    W.T = 10
    veh.link = link1
    veh.state = "run"
    veh.x = link1.length
    veh.route_next_link = out
    veh.route_next_link_choice()
    merge.incoming_vehicles.append(veh)
    veh.record_order_control_node_arrival(merge)

    snapshot = collector.get_baseline_visit_snapshot(veh.name, visit_id)
    assert snapshot is not None
    assert snapshot["baseline_arrival_timestep"] == 10
    assert snapshot["arrival_tiebreaker"] == (
        veh.order_control_current_visit["arrival_tiebreaker"]
    )
    assert snapshot["route_next_link_name"] == "out"


def test_b_arrival_notification_ignores_duplicate_and_outside_fixed_set():
    W = _build_fcfs_clearance_world("collector_b_arrival_ignore")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector

    veh_fixed = W.addVehicle("orig1", "dest", 0, name="veh_fixed")
    veh_outside = W.addVehicle("orig2", "dest", 0, name="veh_outside")
    _advance_until_on_link(veh_fixed, "link1")

    visit_id = veh_fixed.order_control_visit_id
    _register_b_snapshot(
        collector,
        veh_fixed,
        node_name="merge",
        inlink_name="link1",
        visit_id=visit_id,
    )

    link1 = W.get_link("link1")
    out = W.get_link("out")
    merge = W.get_node("merge")

    def _arrive(veh):
        W.T = 12
        veh.link = link1
        veh.state = "run"
        veh.x = link1.length
        veh.route_next_link = out
        veh.route_next_link_choice()
        merge.incoming_vehicles.append(veh)
        veh.record_order_control_node_arrival(merge)

    _arrive(veh_fixed)
    first_snapshot = copy.deepcopy(
        collector.get_baseline_visit_snapshot(veh_fixed.name, visit_id)
    )

    veh_fixed.record_order_control_node_arrival(merge)
    after_duplicate = collector.get_baseline_visit_snapshot(veh_fixed.name, visit_id)
    assert after_duplicate == first_snapshot

    _advance_until_on_link(veh_outside, "link2")
    link2 = W.get_link("link2")
    W.T = 13
    veh_outside.link = link2
    veh_outside.state = "run"
    veh_outside.x = link2.length
    veh_outside.route_next_link = out
    veh_outside.route_next_link_choice()
    merge.incoming_vehicles.append(veh_outside)
    veh_outside.record_order_control_node_arrival(merge)
    assert collector.get_baseline_visit_snapshot(veh_outside.name, 999) is None


def test_batch_passage_records_after_service_queue_finalize():
    W = _build_batch_world("collector_batch_passage")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="batch_veh")

    visit_id = 1
    veh.order_control_visit_id = visit_id
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": 10.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": 0,
    }
    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    link1.vehicles.append(veh)
    merge.incoming_vehicles.append(veh)
    veh.order_control_batch_assignments["merge"] = 0

    _register_arrived_a_snapshot(
        collector,
        veh,
        node_name="merge",
        inlink_name="link1",
        visit_id=visit_id,
        arrival_timestep=10,
        tiebreaker=0.1,
        route_next_link_name="out",
    )

    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [visit_id],
        }
    )
    _boost_transfer_capacity(merge, link1, out)

    apply_calls = []

    def _recording_apply(record, timestep):
        apply_calls.append(
            {
                "timestep": timestep,
                "queue_len": len(merge.order_control_batch_service_queue),
            }
        )
        OrderControlBaselineCollector.apply_baseline_passage_timestep(
            collector, record, timestep
        )

    collector.apply_baseline_passage_timestep = _recording_apply

    W.T = 15
    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert len(apply_calls) == 1
    assert apply_calls[0]["timestep"] == 15
    assert apply_calls[0]["queue_len"] == 0

    snapshot = collector.get_baseline_visit_snapshot(veh.name, visit_id)
    assert snapshot["baseline_passage_timestep"] == 15
    assert veh.link is out


def test_batch_passage_ignores_outside_fixed_set_vehicle():
    W = _build_batch_world("collector_batch_outside")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="outside_batch")

    visit_id = 1
    veh.order_control_visit_id = visit_id
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": 10.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": 0,
    }
    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    link1.vehicles.append(veh)
    merge.incoming_vehicles.append(veh)
    veh.order_control_batch_assignments["merge"] = 0
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [visit_id],
        }
    )
    _boost_transfer_capacity(merge, link1, out)

    W.T = 20
    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert collector.get_baseline_visit_snapshot(veh.name, visit_id) is None
    assert veh.link is out


def test_fcfs_clearance_passage_records_original_visit():
    W = _build_fcfs_clearance_world("collector_fcfs_passage")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="fcfs_veh")

    visit_id = 1
    veh.order_control_visit_id = visit_id
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": 10.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": None,
    }
    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    link1.vehicles.append(veh)
    merge.incoming_vehicles.append(veh)

    _register_arrived_a_snapshot(
        collector,
        veh,
        node_name="merge",
        inlink_name="link1",
        visit_id=visit_id,
        arrival_timestep=10,
        tiebreaker=0.1,
        route_next_link_name="out",
    )
    _boost_transfer_capacity(merge, link1, out)

    W.T = 25
    merge.transfer_fcfs_clearance()

    snapshot = collector.get_baseline_visit_snapshot(veh.name, visit_id)
    assert snapshot["baseline_passage_timestep"] == 25
    assert veh.link is out
    assert (
        veh.order_control_current_visit is None
        or veh.order_control_current_visit["visit_id"] != visit_id
    )


def test_fcfs_clearance_passage_ignores_outside_fixed_set_vehicle():
    W = _build_fcfs_clearance_world("collector_fcfs_outside_passage")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="fcfs_outside")

    # FCFS clearance経路ではcurrent_visitを持つが、collector固定集合には登録しない。
    visit_id = 1
    veh.order_control_visit_id = visit_id
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": 10.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": None,
    }
    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    link1.vehicles.append(veh)
    merge.incoming_vehicles.append(veh)
    _boost_transfer_capacity(merge, link1, out)

    # collector未登録でも、FCFS clearance通過前にはcurrent_visitを持つ。
    assert veh.order_control_current_visit is not None
    assert veh.order_control_current_visit["visit_id"] == visit_id

    W.T = 25
    merge.transfer_fcfs_clearance()

    assert veh.link is out
    assert collector.get_baseline_visit_snapshot(veh.name, visit_id) is None


def test_normal_transfer_passage_on_time_value_node():
    W = _build_time_value_transfer_world("collector_time_value_transfer")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    junction = W.get_node("junction")
    inlink = W.get_link("in")
    out = W.get_link("out")
    veh = W.addVehicle("orig", "dest", 0, name="tv_veh")

    visit_id = 1
    veh.order_control_visit_id = visit_id
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": junction,
        "inlink": inlink,
        "earliest_arrival_timestep": 0,
        "arrival_time": 10.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": None,
    }
    veh.link = inlink
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    inlink.vehicles.append(veh)
    junction.incoming_vehicles.append(veh)

    _register_arrived_a_snapshot(
        collector,
        veh,
        node_name="junction",
        inlink_name="in",
        visit_id=visit_id,
        arrival_timestep=10,
        tiebreaker=0.1,
        route_next_link_name="out",
    )
    _boost_transfer_capacity(junction, inlink, out)

    W.T = 30
    junction.transfer()

    snapshot = collector.get_baseline_visit_snapshot(veh.name, visit_id)
    assert snapshot["baseline_passage_timestep"] == 30
    assert veh.link is out


def test_normal_transfer_passage_ignores_outside_fixed_set_vehicle():
    W = _build_normal_transfer_world("collector_normal_transfer_outside")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    junction = W.get_node("junction")
    inlink = W.get_link("in")
    out = W.get_link("out")
    veh = W.addVehicle("orig", "dest", 0, name="normal_outside")

    # order_control対象外Nodeではcurrent_visitが作られない前提を通過前に確認する。
    assert veh.order_control_current_visit is None

    veh.link = inlink
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    inlink.vehicles.append(veh)
    junction.incoming_vehicles.append(veh)
    _boost_transfer_capacity(junction, inlink, out)

    W.T = 30
    junction.transfer()

    assert veh.link is out
    assert veh.order_control_current_visit is None
    assert collector.get_baseline_visit_snapshot(veh.name, 1) is None


def test_batch_passage_stops_before_physical_transfer_on_inconsistency():
    W = _build_batch_world("collector_batch_inconsistency")
    collector = OrderControlBaselineCollector()
    W._order_control_baseline_collector = collector
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="bad_batch")

    registered_visit_id = 1
    collector_visit_id = 2
    veh.order_control_visit_id = registered_visit_id
    veh.order_control_current_visit = {
        "visit_id": registered_visit_id,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": None,
        "arrival_tiebreaker": None,
        "batch_assignment": 0,
    }
    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out
    link1.vehicles.append(veh)
    merge.incoming_vehicles.append(veh)
    veh.order_control_batch_assignments["merge"] = 0

    _register_b_snapshot(
        collector,
        veh,
        node_name="merge",
        inlink_name="link1",
        visit_id=collector_visit_id,
    )

    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [registered_visit_id],
        }
    )
    _boost_transfer_capacity(merge, link1, out)

    try:
        merge.serve_order_control_batch_service_queue()
        raise AssertionError("Expected ValueError before physical BATCH transfer")
    except ValueError as exc:
        assert "visit_id mismatch" in str(exc)

    assert veh.link is link1
    assert veh in link1.vehicles
    assert veh in merge.incoming_vehicles
    assert veh.link is not out
    assert collector.get_baseline_visit_snapshot(veh.name, collector_visit_id) is not None
    assert (
        collector.get_baseline_visit_snapshot(veh.name, collector_visit_id)[
            "baseline_passage_timestep"
        ]
        is None
    )


def test_real_world_and_fork_collector_are_separated():
    real_W = _build_fcfs_clearance_world("collector_real_world")
    assert real_W._order_control_baseline_collector is None

    fork_W = real_W.copy()
    fork_collector = OrderControlBaselineCollector()
    fork_W._order_control_baseline_collector = fork_collector

    assert real_W._order_control_baseline_collector is None
    assert fork_W._order_control_baseline_collector is fork_collector
    assert not hasattr(fork_collector, "W")

    fork_collector.register_snapshot_visit(
        vehicle_name="probe",
        vehicle_id=0,
        node_name="merge",
        inlink_name="link1",
        visit_id=1,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )

    assert fork_collector.get_baseline_visit_snapshot("probe", 1) is not None
    assert real_W._order_control_baseline_collector is None


TESTS = [
    test_collector_disabled_traffic_and_rng_unchanged,
    test_b_arrival_notification_records_baseline_facts,
    test_b_arrival_notification_ignores_duplicate_and_outside_fixed_set,
    test_batch_passage_records_after_service_queue_finalize,
    test_batch_passage_ignores_outside_fixed_set_vehicle,
    test_fcfs_clearance_passage_records_original_visit,
    test_fcfs_clearance_passage_ignores_outside_fixed_set_vehicle,
    test_normal_transfer_passage_on_time_value_node,
    test_normal_transfer_passage_ignores_outside_fixed_set_vehicle,
    test_batch_passage_stops_before_physical_transfer_on_inconsistency,
    test_real_world_and_fork_collector_are_separated,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control baseline collector UXsim connection tests passed.")
