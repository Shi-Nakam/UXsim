# Verify clearance-aware FCFS behavior with clearance_timesteps=0.
#
# Run from the repository root:
#   python tests_fcfs_order_control_clearance_0.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import numpy as np

from uxsim import World


def _passage_order_on_link(link, vehicle_names=None):
    names = [veh.name for _, veh in sorted(link.vehicles_enter_log.items())]
    if vehicle_names is not None:
        name_set = set(vehicle_names)
        names = [name for name in names if name in name_set]
    return names


def _passage_times_on_link(link, vehicle_names):
    name_set = set(vehicle_names)
    return {
        veh.name: enter_time
        for enter_time, veh in sorted(link.vehicles_enter_log.items())
        if veh.name in name_set
    }


def _expected_fcfs_order(vehicles, node_name):
    return [
        veh.name
        for veh in sorted(
            vehicles,
            key=lambda veh: (
                veh.order_control_node_arrival_times[node_name],
                veh.order_control_node_arrival_tiebreakers[node_name],
                veh.id,
            ),
        )
    ]


def _failure_message(
    *,
    expected_order,
    actual_order,
    actual_enter_times,
    veh_clr_1,
    veh_clr_2,
    merge,
):
    return (
        f"expected_order: {expected_order}\n"
        f"actual_order: {actual_order}\n"
        f"actual_enter_times: {actual_enter_times}\n"
        f"veh_clr_1 arrival_time: {veh_clr_1.order_control_node_arrival_times['merge']}\n"
        f"veh_clr_2 arrival_time: {veh_clr_2.order_control_node_arrival_times['merge']}\n"
        f"veh_clr_1 tiebreaker: {veh_clr_1.order_control_node_arrival_tiebreakers['merge']}\n"
        f"veh_clr_2 tiebreaker: {veh_clr_2.order_control_node_arrival_tiebreakers['merge']}\n"
        f"veh_clr_1 id: {veh_clr_1.id}\n"
        f"veh_clr_2 id: {veh_clr_2.id}\n"
        f"clearance_timesteps: {merge.order_control_clearance_timesteps}\n"
        f"veh_clr_1 state: {veh_clr_1.state}\n"
        f"veh_clr_2 state: {veh_clr_2.state}"
    )


def test_clearance_zero_blocks_same_timestep_direction_change():
    W = World(
        name="fcfs_clearance_zero_basic",
        deltan=1,
        tmax=400,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )

    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("merge", 1, 1)
    W.addNode("dest", 2, 1)

    link_length = 400
    link_speed = 20
    W.addLink(
        "link1", "orig1", "merge", length=link_length, free_flow_speed=link_speed, number_of_lanes=1
    )
    W.addLink(
        "link2", "orig2", "merge", length=link_length, free_flow_speed=link_speed, number_of_lanes=1
    )
    W.addLink(
        "out", "merge", "dest", length=500, free_flow_speed=link_speed, number_of_lanes=1
    )

    W.infer_order_control_eligible_nodes()
    merge = W.get_node("merge")
    assert merge.order_control_eligible is True

    W.set_order_control_clearance_timesteps(0)
    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")

    assert merge.order_control_type == "fcfs"
    assert merge.order_control_clearance_timesteps == 0

    veh_clr_1 = W.addVehicle("orig1", "dest", 0, name="veh_clr_1")
    veh_clr_2 = W.addVehicle("orig2", "dest", 0, name="veh_clr_2")

    W.exec_simulation()

    assert "merge" in veh_clr_1.order_control_node_arrival_times
    assert "merge" in veh_clr_2.order_control_node_arrival_times
    assert "merge" in veh_clr_1.order_control_node_arrival_tiebreakers
    assert "merge" in veh_clr_2.order_control_node_arrival_tiebreakers

    arrival1 = veh_clr_1.order_control_node_arrival_times["merge"]
    arrival2 = veh_clr_2.order_control_node_arrival_times["merge"]
    assert arrival1 == arrival2, (
        "同時到着せず\n"
        f"veh_clr_1 arrival_time: {arrival1}\n"
        f"veh_clr_2 arrival_time: {arrival2}"
    )

    expected_order = _expected_fcfs_order([veh_clr_1, veh_clr_2], "merge")

    outlink = W.get_link("out")
    vehicle_names = ["veh_clr_1", "veh_clr_2"]
    actual_order = _passage_order_on_link(outlink, vehicle_names=vehicle_names)
    actual_enter_times = _passage_times_on_link(outlink, vehicle_names)

    msg = _failure_message(
        expected_order=expected_order,
        actual_order=actual_order,
        actual_enter_times=actual_enter_times,
        veh_clr_1=veh_clr_1,
        veh_clr_2=veh_clr_2,
        merge=merge,
    )

    assert actual_order == expected_order, f"通過順が期待と一致しない\n{msg}"

    assert len(actual_enter_times) == 2, f"out進入記録が2台分ない\n{msg}"

    first_name = expected_order[0]
    second_name = expected_order[1]
    first_enter_time = actual_enter_times[first_name]
    second_enter_time = actual_enter_times[second_name]

    assert first_enter_time != second_enter_time, (
        f"同一タイムステップ内に異方向Vehicleが連続してoutに入った可能性\n{msg}"
    )
    assert second_enter_time > first_enter_time, (
        f"2台目のout進入時刻が1台目より後でない\n{msg}"
    )

    assert veh_clr_1.state == "end", msg
    assert veh_clr_2.state == "end", msg

    print("FCFS clearance=0 test passed.")


def _prepare_link_logs(world):
    for link in world.LINKS:
        if len(link.cum_arrival) == 0:
            link.cum_arrival.append(0)
            link.cum_departure.append(0)
        link.traveltime_actual = np.zeros(world.T + 5)
        link.capacity_out_remain = 10
        link.capacity_in_remain = 10


def _fcfs_world(name):
    world = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig_a", 0, 1)
    world.addNode("orig_b", 0, -1)
    world.addNode(
        "junction",
        1,
        0,
        order_control_type="fcfs",
        order_control_eligible=True,
        flow_capacity=2,
    )
    world.addNode("dest", 2, 0)
    world.addLink(
        "in_a", "orig_a", "junction", length=100, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "in_b", "orig_b", "junction", length=100, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "out", "junction", "dest", length=100, free_flow_speed=20, number_of_lanes=1
    )
    world.addLink(
        "out_b", "junction", "dest", length=100, free_flow_speed=20, number_of_lanes=1
    )
    world.T = 10
    _prepare_link_logs(world)
    junction = world.get_node("junction")
    junction.flow_capacity_remain = 10
    junction.order_control_clearance_timesteps = 0
    return world


def _place_fcfs(world, vehicle_name, inlink_name, outlink_name, arrival_time, *, incoming=True):
    inlink = world.get_link(inlink_name)
    junction = world.get_node("junction")
    vehicle = world.addVehicle(inlink.start_node.name, "dest", 0, name=vehicle_name)
    vehicle.state = "run"
    vehicle.link = inlink
    vehicle.x = inlink.length
    vehicle.x_old = inlink.length
    vehicle.link_arrival_time = 0
    vehicle.move_remain = 0
    vehicle.v = 0
    vehicle.route_next_link = world.get_link(outlink_name)
    vehicle.begin_order_control_visit_on_link_entry()
    vehicle.order_control_current_visit["arrival_time"] = arrival_time
    vehicle.order_control_current_visit["arrival_tiebreaker"] = 0.1
    inlink.vehicles.append(vehicle)
    if incoming:
        junction.incoming_vehicles.append(vehicle)
    return vehicle


def _park_at_entrance(world, link_name, vehicle_name):
    link = world.get_link(link_name)
    parked = world.addVehicle("orig_a", "dest", 0, name=vehicle_name)
    parked.state = "run"
    parked.link = link
    parked.x = 0
    parked.x_old = 0
    link.vehicles.append(parked)
    return parked


def _watch_fcfs_judgments(junction):
    seen = []
    original = junction._fcfs_clearance_passage_judgment

    def wrapped(vehicle):
        judgment = original(vehicle)
        seen.append((vehicle.name, judgment))
        return judgment

    junction._fcfs_clearance_passage_judgment = wrapped
    return seen


def _history(junction):
    inlink_name = None
    if junction.last_order_control_inlink is not None:
        inlink_name = junction.last_order_control_inlink.name
    return (inlink_name, junction.last_order_control_entry_timestep)


def test_fcfs_inlink_outflow_precedes_node_flow_when_both_are_short():
    """
    The earlier FCFS vehicle is short of inlink outflow and node flow.

    The judgment is inlink outflow. The later vehicle is still judged, and
    its first shortage is node flow. Neither passes, and clearance history
    stays unchanged.
    """
    world = _fcfs_world("fcfs_outflow_before_node_flow")
    junction = world.get_node("junction")
    earlier = _place_fcfs(world, "fcfs_earlier", "in_a", "out", 1.0)
    later = _place_fcfs(world, "fcfs_later", "in_b", "out_b", 2.0)
    in_a = world.get_link("in_a")
    in_b = world.get_link("in_b")
    in_a.capacity_out_remain = 0
    in_b.capacity_out_remain = 10
    junction.flow_capacity_remain = 0
    history_before = _history(junction)
    seen = _watch_fcfs_judgments(junction)
    junction.transfer_fcfs_clearance()
    assert seen == [
        ("fcfs_earlier", "inlink_outflow_capacity_unavailable"),
        ("fcfs_later", "node_flow_capacity_unavailable"),
    ]
    assert earlier.link.name == "in_a"
    assert later.link.name == "in_b"
    assert junction.incoming_vehicles == []
    assert earlier is in_a.vehicles[0]
    assert later is in_b.vehicles[0]
    assert in_a.capacity_out_remain == 0
    assert junction.flow_capacity_remain == 0
    assert _history(junction) == history_before


def test_fcfs_clearance_precedes_inlink_outflow_and_blocks_later_vehicle():
    """
    Unmet clearance stops FCFS before an inlink-outflow skip.

    The earlier vehicle is the physical head, clearance is unmet, and its
    inlink outflow is also short. The later vehicle could pass. It is not
    judged and does not pass.
    """
    world = _fcfs_world("fcfs_clearance_before_outflow")
    junction = world.get_node("junction")
    earlier = _place_fcfs(world, "fcfs_clearance_earlier", "in_a", "out", 1.0)
    later = _place_fcfs(world, "fcfs_clearance_later", "in_b", "out_b", 2.0)
    world.get_link("in_a").capacity_out_remain = 0
    junction.order_control_clearance_timesteps = 5
    junction.last_order_control_inlink = world.get_link("in_b")
    junction.last_order_control_entry_timestep = world.T
    history_before = _history(junction)
    flow_before = junction.flow_capacity_remain
    seen = _watch_fcfs_judgments(junction)
    junction.transfer_fcfs_clearance()
    assert seen == [("fcfs_clearance_earlier", "clearance_not_satisfied")]
    assert earlier.link.name == "in_a"
    assert later.link.name == "in_b"
    assert junction.incoming_vehicles == []
    assert world.get_link("in_a").capacity_out_remain == 0
    assert junction.flow_capacity_remain == flow_before
    assert _history(junction) == history_before


def test_fcfs_clearance_precedes_node_flow_and_blocks_later_vehicle():
    """
    Unmet clearance stops FCFS before a node-flow skip.

    Node flow is also short. The later vehicle is not judged.
    """
    world = _fcfs_world("fcfs_clearance_before_node_flow")
    junction = world.get_node("junction")
    earlier = _place_fcfs(world, "fcfs_flow_earlier", "in_a", "out", 1.0)
    later = _place_fcfs(world, "fcfs_flow_later", "in_b", "out_b", 2.0)
    world.get_link("in_a").capacity_out_remain = 10
    junction.flow_capacity_remain = 0
    junction.order_control_clearance_timesteps = 5
    junction.last_order_control_inlink = world.get_link("in_b")
    junction.last_order_control_entry_timestep = world.T
    history_before = _history(junction)
    seen = _watch_fcfs_judgments(junction)
    junction.transfer_fcfs_clearance()
    assert seen == [("fcfs_flow_earlier", "clearance_not_satisfied")]
    assert earlier.link.name == "in_a"
    assert later.link.name == "in_b"
    assert junction.flow_capacity_remain == 0
    assert world.get_link("in_a").capacity_out_remain == 10
    assert _history(junction) == history_before


def test_fcfs_node_flow_shortage_after_available_outflow_tries_later_vehicle():
    """Node flow shortage skips only the current vehicle and still judges the next."""
    world = _fcfs_world("fcfs_node_flow_after_outflow")
    junction = world.get_node("junction")
    earlier = _place_fcfs(world, "fcfs_node_earlier", "in_a", "out", 1.0)
    later = _place_fcfs(world, "fcfs_node_later", "in_b", "out_b", 2.0)
    world.get_link("in_a").capacity_out_remain = 10
    world.get_link("in_b").capacity_out_remain = 10
    junction.flow_capacity_remain = 0
    history_before = _history(junction)
    seen = _watch_fcfs_judgments(junction)
    junction.transfer_fcfs_clearance()
    assert seen == [
        ("fcfs_node_earlier", "node_flow_capacity_unavailable"),
        ("fcfs_node_later", "node_flow_capacity_unavailable"),
    ]
    assert earlier.link.name == "in_a"
    assert later.link.name == "in_b"
    assert junction.flow_capacity_remain == 0
    assert _history(junction) == history_before


def test_fcfs_outlink_inflow_precedes_entry_space_when_both_are_short():
    """
    The earlier vehicle lacks outlink inflow and entry space.

    The judgment is outlink inflow. The later vehicle uses an open outlink
    and passes. Clearance history is updated only for that pass.
    """
    world = _fcfs_world("fcfs_inflow_before_entry_space")
    junction = world.get_node("junction")
    _park_at_entrance(world, "out", "fcfs_parked")
    earlier = _place_fcfs(world, "fcfs_inflow_earlier", "in_a", "out", 1.0)
    later = _place_fcfs(world, "fcfs_inflow_later", "in_b", "out_b", 2.0)
    outlink = world.get_link("out")
    out_b = world.get_link("out_b")
    outlink.capacity_in_remain = 0
    out_b.capacity_in_remain = 10
    world.get_link("in_a").capacity_out_remain = 10
    junction.flow_capacity_remain = 10
    seen = _watch_fcfs_judgments(junction)
    junction.transfer_fcfs_clearance()
    assert seen[0] == ("fcfs_inflow_earlier", "outlink_inflow_capacity_unavailable")
    assert seen[1] == ("fcfs_inflow_later", "pass")
    assert earlier.link.name == "in_a"
    assert later.link.name == "out_b"
    assert outlink.capacity_in_remain == 0
    assert world.get_link("in_a").capacity_out_remain == 10
    assert _history(junction) == ("in_b", world.T)


def test_fcfs_not_physical_head_precedes_clearance():
    """
    A vehicle that is not the physical head is skipped before clearance.

    Its unmet clearance does not stop the node scan. The later physical
    head, whose inlink matches the previous entry, can pass.
    """
    world = _fcfs_world("fcfs_head_before_clearance")
    junction = world.get_node("junction")
    _place_fcfs(world, "fcfs_blocker", "in_a", "out", 0.5, incoming=False)
    earlier = _place_fcfs(world, "fcfs_behind", "in_a", "out", 1.0)
    later = _place_fcfs(world, "fcfs_open_later", "in_b", "out_b", 2.0)
    junction.order_control_clearance_timesteps = 5
    junction.last_order_control_inlink = world.get_link("in_b")
    junction.last_order_control_entry_timestep = world.T
    seen = _watch_fcfs_judgments(junction)
    junction.transfer_fcfs_clearance()
    assert seen[0] == ("fcfs_behind", "not_physical_head")
    assert ("fcfs_open_later", "pass") in seen
    assert earlier.link.name == "in_a"
    assert later.link.name == "out_b"
    assert _history(junction) == ("in_b", world.T)


def _run_fcfs_physical_order_tests():
    tests = [
        test_fcfs_inlink_outflow_precedes_node_flow_when_both_are_short,
        test_fcfs_clearance_precedes_inlink_outflow_and_blocks_later_vehicle,
        test_fcfs_clearance_precedes_node_flow_and_blocks_later_vehicle,
        test_fcfs_node_flow_shortage_after_available_outflow_tries_later_vehicle,
        test_fcfs_outlink_inflow_precedes_entry_space_when_both_are_short,
        test_fcfs_not_physical_head_precedes_clearance,
    ]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print(len(tests), "FCFS physical-order tests passed")


if __name__ == "__main__":
    _run_fcfs_physical_order_tests()
    test_clearance_zero_blocks_same_timestep_direction_change()
