# Verify BATCH service-queue vehicle transfer at order-control nodes.
#
# Run from the repository root:
#   python tests_order_control_batch_service_queue_transfer.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy
from collections import deque

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _boost_transfer_capacity(merge, *links):
    for link in links:
        link.capacity_in_remain = 1e6
        link.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6


def _build_network(name="batch_service_queue_transfer", node_name="merge"):
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
    W.addNode("orig3", 0, 4)
    W.addNode(
        node_name,
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", node_name, "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _make_vehicle(W, orig_name, name, dest="dest"):
    return W.addVehicle(orig_name, dest, 0, name=name)


def _setup_arrived_vehicle(
    merge,
    veh,
    link,
    out_link,
    earliest,
    arrival_time,
    tiebreaker,
    x,
    *,
    move_remain=0.0,
    link_arrival_time=0.0,
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.move_remain = move_remain
    veh.link_arrival_time = link_arrival_time
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _register_service_unit(merge, batch_id, inlink, vehicles):
    for veh in vehicles:
        veh.order_control_batch_assignments["merge"] = batch_id
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": batch_id,
            "inlink": inlink,
            "vehicles": list(vehicles),
        }
    )


def _queue_snapshot(merge):
    return [
        {
            "batch_id": unit["batch_id"],
            "inlink": unit["inlink"],
            "vehicles": list(unit["vehicles"]),
        }
        for unit in merge.order_control_batch_service_queue
    ]


def _expect_value_error(callable_obj, message_substrings=()):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError as exc:
        message = str(exc)
        for substring in message_substrings:
            assert substring in message, f"expected {substring!r} in {message!r}"


def test_empty_queue_returns_zero():
    W = _build_network("sq_empty")
    merge = W.get_node("merge")
    assert merge.serve_order_control_batch_service_queue() == 0
    assert len(merge.order_control_batch_service_queue) == 0


def test_single_vehicle_transfer():
    W = _build_network("sq_single")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    _register_service_unit(merge, 0, link1, [veh])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert veh not in merge.incoming_vehicles
    assert veh.link is out
    assert len(merge.order_control_batch_service_queue) == 0
    assert veh.order_control_batch_assignments["merge"] == 0


def test_multiple_vehicles_same_unit():
    W = _build_network("sq_multi_same")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    a1, a2 = [_make_vehicle(W, "orig1", name) for name in ("A1", "A2")]
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=20.0)
    _setup_arrived_vehicle(merge, a2, link1, out, 0, 11.0, 0.2, 150.0, move_remain=20.0)
    _register_service_unit(merge, 0, link1, [a1, a2])
    _boost_transfer_capacity(merge, link1, out)

    count = merge.serve_order_control_batch_service_queue()
    assert count == 2
    assert a1.link is out and a2.link is out
    assert len(merge.order_control_batch_service_queue) == 0


def test_not_arrived_waits():
    W = _build_network("sq_not_arrived")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    a1.link = link1
    a1.state = "run"
    a1.x = 200.0
    a1.route_next_link = out
    a1.order_control_batch_assignments["merge"] = 0
    link1.vehicles.append(a1)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])
    before = _queue_snapshot(merge)
    out_cum = out.cum_arrival[-1]

    count = merge.serve_order_control_batch_service_queue()
    assert count == 0
    assert _queue_snapshot(merge) == before
    assert b1 in merge.incoming_vehicles
    assert b1.link is link2
    assert b1 in link2.vehicles
    assert b1.link is not out
    assert out.cum_arrival[-1] == out_cum
    assert merge.last_order_control_inlink is None


def test_not_arrived_without_route_next_link_attribute():
    W = _build_network("sq_not_arrived_no_route_attr")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    a1.link = link1
    a1.state = "run"
    a1.x = 200.0
    if hasattr(a1, "route_next_link"):
        delattr(a1, "route_next_link")
    assert not hasattr(a1, "route_next_link")
    a1.order_control_batch_assignments["merge"] = 0
    link1.vehicles.append(a1)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])
    before = _queue_snapshot(merge)
    out_cum = out.cum_arrival[-1]

    count = merge.serve_order_control_batch_service_queue()
    assert count == 0
    assert _queue_snapshot(merge) == before
    assert a1 not in merge.incoming_vehicles
    assert a1.order_control_batch_assignments.get("merge") == 0
    assert not hasattr(a1, "route_next_link")
    assert b1 in merge.incoming_vehicles
    assert b1.link is link2
    assert b1.link is not out
    assert out.cum_arrival[-1] == out_cum
    assert merge.last_order_control_inlink is None


def test_clearance_no_history():
    W = _build_network("sq_clr_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    _register_service_unit(merge, 0, link1, [veh])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None

    assert merge.serve_order_control_batch_service_queue() == 1


def test_clearance_same_inlink_not_required():
    W = _build_network("sq_clr_same")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = merge.W.T
    a1, a2 = [_make_vehicle(W, "orig1", name) for name in ("A1", "A2")]
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=20.0)
    _setup_arrived_vehicle(merge, a2, link1, out, 0, 11.0, 0.2, 150.0, move_remain=20.0)
    _register_service_unit(merge, 0, link1, [a1, a2])
    _boost_transfer_capacity(merge, link1, out)

    assert merge.serve_order_control_batch_service_queue() == 2


def test_clearance_blocks_and_stops():
    W = _build_network("sq_clr_block")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = merge.W.T
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    _register_service_unit(merge, 0, link2, [b1])
    _register_service_unit(merge, 1, link1, [a1])
    before = _queue_snapshot(merge)

    count = merge.serve_order_control_batch_service_queue()
    assert count == 0
    assert _queue_snapshot(merge) == before
    assert merge.last_order_control_inlink is link1


def test_clearance_satisfied_after_wait():
    W = _build_network("sq_clr_ok")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.W.T = 10
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 8
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    _register_service_unit(merge, 0, link2, [b1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert merge.last_order_control_inlink is link2


def test_clearance_history_mismatch_value_error():
    W = _build_network("sq_clr_mismatch")
    merge = W.get_node("merge")
    merge.last_order_control_inlink = W.get_link("link1")
    merge.last_order_control_entry_timestep = None
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["inconsistent", "merge"],
    )


def test_clearance_history_reverse_mismatch_value_error():
    W = _build_network("sq_clr_reverse_mismatch")
    merge = W.get_node("merge")
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = 0
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["inconsistent", "merge"],
    )


def test_clearance_history_updated_only_on_success():
    W = _build_network("sq_clr_no_update_fail")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = merge.W.T
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    out.capacity_in_remain = 0
    _register_service_unit(merge, 0, link2, [b1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 0
    assert merge.last_order_control_inlink is link1
    assert merge.last_order_control_entry_timestep == merge.W.T


def test_downstream_space_insufficient():
    W = _build_network("sq_downstream")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    blocker = _make_vehicle(W, "orig1", "BLOCK")
    blocker.link = out
    blocker.state = "run"
    blocker.x = 0.0
    blocker.lane = 0
    out.vehicles.append(blocker)
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    _register_service_unit(merge, 0, link1, [veh])
    in_cum = link1.cum_departure[-1]

    assert merge.serve_order_control_batch_service_queue() == 0
    assert link1.cum_departure[-1] == in_cum
    assert veh in merge.incoming_vehicles


def test_outlink_capacity_insufficient():
    W = _build_network("sq_out_cap")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    out.capacity_in_remain = 0
    _register_service_unit(merge, 0, link1, [veh])
    assert merge.serve_order_control_batch_service_queue() == 0


def test_inlink_capacity_insufficient():
    W = _build_network("sq_in_cap")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    link1.capacity_out_remain = 0
    _register_service_unit(merge, 0, link1, [veh])
    assert merge.serve_order_control_batch_service_queue() == 0


def test_node_flow_capacity_insufficient():
    W = _build_network("sq_node_cap")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    merge.flow_capacity_remain = 0
    _register_service_unit(merge, 0, link1, [veh])
    assert merge.serve_order_control_batch_service_queue() == 0


def test_node_flow_capacity_decreases_on_transfer():
    W = World(
        name="sq_node_cap_decrease",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
        flow_capacity=10,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    link1.capacity_in_remain = 1e6
    link1.capacity_out_remain = 1e6
    out.capacity_in_remain = 1e6
    out.capacity_out_remain = 1e6
    flow_cap_before = merge.flow_capacity_remain
    _register_service_unit(merge, 0, link1, [veh])

    assert merge.serve_order_control_batch_service_queue() == 1
    assert merge.flow_capacity_remain == flow_cap_before - merge.W.DELTAN


def test_not_physical_head():
    W = _build_network("sq_not_head")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    lead = _make_vehicle(W, "orig1", "LEAD")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, lead, link1, out, 0, 9.0, 0.0, 200.0)
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 150.0)
    _register_service_unit(merge, 0, link1, [veh])
    assert merge.serve_order_control_batch_service_queue() == 0


def test_consecutive_same_inlink_units():
    W = _build_network("sq_consecutive")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    out.number_of_lanes = 4
    vehicles = []
    for idx in range(4):
        veh = _make_vehicle(W, "orig1", f"A{idx}")
        _setup_arrived_vehicle(
            merge, veh, link1, out, 0, 10.0 + idx, 0.1 + idx, 200.0 - idx * 10,
            move_remain=20.0,
        )
        vehicles.append(veh)
    _register_service_unit(merge, 0, link1, [vehicles[0]])
    _register_service_unit(merge, 1, link1, [vehicles[1]])
    _register_service_unit(merge, 2, link1, [vehicles[2]])
    _register_service_unit(merge, 3, link1, [vehicles[3]])
    merge.batch_size = 2
    _boost_transfer_capacity(merge, link1, out)

    count = merge.serve_order_control_batch_service_queue()
    assert count == 4
    assert len(merge.order_control_batch_service_queue) == 0
    assert all(veh.link is out for veh in vehicles)


def test_capacity_stop_after_first_transfer_same_unit():
    W = _build_network("sq_stop_mid_unit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    a1, a2 = [_make_vehicle(W, "orig1", name) for name in ("A1", "A2")]
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=20.0)
    _setup_arrived_vehicle(merge, a2, link1, out, 0, 11.0, 0.2, 150.0, move_remain=20.0)
    _register_service_unit(merge, 0, link1, [a1, a2])

    out.capacity_in_remain = merge.W.DELTAN
    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert len(merge.order_control_batch_service_queue) == 1
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [a2]


def test_zero_transfer_checks_different_inlink():
    W = _build_network("sq_zero_diff")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert b1.link is out
    queue = _queue_snapshot(merge)
    assert len(queue) == 1
    assert queue[0]["inlink"] is link1
    assert queue[0]["vehicles"] == [a1]


def test_zero_transfer_skips_same_inlink_follower():
    W = _build_network("sq_zero_skip_same")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    a1, a2 = [_make_vehicle(W, "orig1", name) for name in ("A1", "A2")]
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=20.0)
    _setup_arrived_vehicle(merge, a2, link1, out, 0, 11.0, 0.2, 150.0, move_remain=20.0)
    out.capacity_in_remain = 0
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link1, [a2])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 0
    assert len(merge.order_control_batch_service_queue) == 2


def test_working_list_removes_completed_middle_unit():
    W = _build_network("sq_working_list")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.W.T = 10
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 8
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    c1 = _make_vehicle(W, "orig3", "C1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    c1.link = link2
    c1.state = "run"
    c1.x = 200.0
    c1.route_next_link = out
    c1.order_control_batch_assignments["merge"] = 2
    link2.vehicles.append(c1)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])
    _register_service_unit(merge, 2, link2, [c1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert b1.link is out
    queue = _queue_snapshot(merge)
    assert len(queue) == 2
    assert queue[0]["inlink"] is link1 and queue[0]["vehicles"] == [a1]
    assert queue[1]["inlink"] is link2 and queue[1]["vehicles"] == [c1]


def test_early_stop_removes_completed_unit():
    W = _build_network("sq_early_stop")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.W.T = 10
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 8
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    c1 = _make_vehicle(W, "orig3", "C1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    c1.link = link2
    c1.state = "run"
    c1.x = 200.0
    c1.route_next_link = out
    c1.order_control_batch_assignments["merge"] = 2
    link2.vehicles.append(c1)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])
    _register_service_unit(merge, 2, link2, [c1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    queue = _queue_snapshot(merge)
    assert len(queue) == 2
    assert queue[0]["vehicles"] == [a1]
    assert queue[1]["vehicles"] == [c1]
    assert all(unit["vehicles"] for unit in queue)


def test_cannot_complete_d_after_stop_at_c():
    W = _build_network("sq_no_d_after_c")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.W.T = 10
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 8
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    c1 = _make_vehicle(W, "orig3", "C1")
    d1 = _make_vehicle(W, "orig1", "D1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    _setup_arrived_vehicle(merge, c1, link2, out, 0, 11.0, 0.3, 150.0)
    _setup_arrived_vehicle(merge, d1, link1, out, 0, 12.0, 0.4, 100.0)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])
    _register_service_unit(merge, 2, link2, [c1])
    _register_service_unit(merge, 3, link1, [d1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    queue = _queue_snapshot(merge)
    assert len(queue) == 3
    assert queue[0]["vehicles"] == [a1]
    assert queue[1]["vehicles"] == [c1]
    assert queue[2]["vehicles"] == [d1]


def test_link_transition_updates():
    W = _build_network("sq_link_updates")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(
        merge, veh, link1, out, 3, 10.0, 0.1, 200.0, move_remain=4.0, link_arrival_time=5.0
    )
    old_link_arrival_time = veh.link_arrival_time
    travel_time_index = int(old_link_arrival_time / merge.W.DELTAT)
    v_before = veh.v
    move_remain_before = veh.move_remain
    in_dep_before = link1.cum_departure[-1]
    out_arr_before = out.cum_arrival[-1]
    in_cap_before = link1.capacity_out_remain
    out_cap_before = out.capacity_in_remain
    _register_service_unit(merge, 0, link1, [veh])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert link1.cum_departure[-1] == in_dep_before + merge.W.DELTAN
    assert out.cum_arrival[-1] == out_arr_before + merge.W.DELTAN
    assert link1.capacity_out_remain == in_cap_before - merge.W.DELTAN
    assert out.capacity_in_remain == out_cap_before - merge.W.DELTAN
    assert link1.traveltime_actual[travel_time_index] == (
        merge.W.T * merge.W.DELTAT - old_link_arrival_time
    )
    assert veh.link_arrival_time == merge.W.T * merge.W.DELTAT
    entry_time = merge.W.T * merge.W.DELTAT
    assert out.vehicles_enter_log[entry_time] is veh
    expected_x = move_remain_before * out.u / link1.u
    if expected_x >= out.length:
        expected_x = out.length
    assert veh.x == expected_x
    assert veh.v == v_before + veh.x / merge.W.DELTAT
    assert veh.lane == 0
    assert veh.link is out
    assert veh in out.vehicles
    assert veh not in link1.vehicles
    assert veh not in merge.incoming_vehicles
    assert veh.move_remain == 0
    assert out.end_node.name not in veh.order_control_earliest_arrival_timesteps
    assert veh.order_control_current_visit is None
    assert merge.last_order_control_inlink is link1
    assert merge.last_order_control_entry_timestep == merge.W.T


def test_n1_clearance_blocks_later_unit():
    W = _build_network("sq_n1_clearance")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    W.set_order_control_clearance_timesteps(1)
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = merge.W.T
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    _register_service_unit(merge, 0, link2, [b1])
    _register_service_unit(merge, 1, link1, [a1])

    assert merge.serve_order_control_batch_service_queue() == 0
    assert len(merge.order_control_batch_service_queue) == 2


def test_n1_capacity_fail_checks_different_inlink():
    W = _build_network("sq_n1_capacity")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    link1.capacity_out_remain = 0
    _boost_transfer_capacity(merge, link2, out)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert b1.link is out
    assert _queue_snapshot(merge)[0]["vehicles"] == [a1]


def test_missing_assignment_value_error():
    W = _build_network("sq_missing_assign")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    merge.order_control_batch_service_queue.append(
        {"batch_id": 0, "inlink": link1, "vehicles": [veh]}
    )
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["no batch assignment", "A1"],
    )


def test_mismatched_batch_id_value_error():
    W = _build_network("sq_bad_batch")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    veh.order_control_batch_assignments["merge"] = 9
    merge.order_control_batch_service_queue.append(
        {"batch_id": 0, "inlink": link1, "vehicles": [veh]}
    )
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["batch assignment", "A1"],
    )


def test_vehicle_link_mismatch_value_error():
    W = _build_network("sq_link_mismatch")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    veh.order_control_batch_assignments["merge"] = 0
    merge.order_control_batch_service_queue.append(
        {"batch_id": 0, "inlink": link2, "vehicles": [veh]}
    )
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["veh.link", "A1", "merge"],
    )


def test_route_next_link_none_value_error():
    W = _build_network("sq_no_route")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "orig1", "A1")
    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.route_next_link = None
    veh.order_control_batch_assignments["merge"] = 0
    link1.vehicles.append(veh)
    merge.incoming_vehicles.append(veh)
    merge.order_control_batch_service_queue.append(
        {"batch_id": 0, "inlink": link1, "vehicles": [veh]}
    )
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["route_next_link=None", "A1"],
    )


def test_after_transfer_does_not_check_different_inlink():
    W = _build_network("sq_after_no_diff")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert a1.link is out
    assert b1 in merge.incoming_vehicles
    queue = _queue_snapshot(merge)
    assert len(queue) == 1 and queue[0]["vehicles"] == [b1]


def test_residual_keeps_order_in_unit():
    W = _build_network("sq_residual")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    a1, a2, a3 = [_make_vehicle(W, "orig1", f"A{i}") for i in (1, 2, 3)]
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, a2, link1, out, 0, 11.0, 0.2, 150.0)
    _setup_arrived_vehicle(merge, a3, link1, out, 0, 12.0, 0.3, 100.0)
    _register_service_unit(merge, 0, link1, [a1, a2, a3])
    out.capacity_in_remain = merge.W.DELTAN

    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [a2, a3]


TESTS = [
    test_empty_queue_returns_zero,
    test_single_vehicle_transfer,
    test_multiple_vehicles_same_unit,
    test_not_arrived_waits,
    test_not_arrived_without_route_next_link_attribute,
    test_clearance_no_history,
    test_clearance_same_inlink_not_required,
    test_clearance_blocks_and_stops,
    test_clearance_satisfied_after_wait,
    test_clearance_history_mismatch_value_error,
    test_clearance_history_reverse_mismatch_value_error,
    test_clearance_history_updated_only_on_success,
    test_downstream_space_insufficient,
    test_outlink_capacity_insufficient,
    test_inlink_capacity_insufficient,
    test_node_flow_capacity_insufficient,
    test_node_flow_capacity_decreases_on_transfer,
    test_not_physical_head,
    test_consecutive_same_inlink_units,
    test_capacity_stop_after_first_transfer_same_unit,
    test_zero_transfer_checks_different_inlink,
    test_zero_transfer_skips_same_inlink_follower,
    test_working_list_removes_completed_middle_unit,
    test_early_stop_removes_completed_unit,
    test_cannot_complete_d_after_stop_at_c,
    test_link_transition_updates,
    test_n1_clearance_blocks_later_unit,
    test_n1_capacity_fail_checks_different_inlink,
    test_missing_assignment_value_error,
    test_mismatched_batch_id_value_error,
    test_vehicle_link_mismatch_value_error,
    test_route_next_link_none_value_error,
    test_after_transfer_does_not_check_different_inlink,
    test_residual_keeps_order_in_unit,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control batch service-queue transfer tests passed.")
