# Verify detailed behavior of the clearance-free FCFS transfer implemented in phase 4-3.
#
# This file is not a phase 4-4 implementation; it exercises the initial FCFS transfer
# from phase 4-3. Coverage includes:
#   - arrival-order behavior (passing order matches merge arrival order)
#   - blocked-outlink skip behavior (skip an infeasible first-arrival vehicle)
#
# Run from the repository root:
#   python tests_fcfs_order_control_behavior.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def _passage_order_on_link(link):
    return [veh.name for _, veh in sorted(link.vehicles_enter_log.items())]


def test_fcfs_arrival_order_matches_passing_order():
    W = World(
        name="fcfs_arrival_order_behavior",
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

    W.addLink(
        "link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1
    )
    W.addLink(
        "link2", "orig2", "merge", length=600, free_flow_speed=20, number_of_lanes=1
    )
    W.addLink(
        "out", "merge", "dest", length=500, free_flow_speed=20, number_of_lanes=1
    )

    W.infer_order_control_eligible_nodes()
    merge = W.get_node("merge")
    assert merge.order_control_eligible is True

    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")
    assert merge.order_control_type == "fcfs"

    veh_early = W.addVehicle("orig1", "dest", 0, name="veh_early")
    veh_late = W.addVehicle("orig2", "dest", 0, name="veh_late")

    W.exec_simulation()

    assert "merge" in veh_early.order_control_node_arrival_times
    assert "merge" in veh_late.order_control_node_arrival_times
    assert (
        veh_early.order_control_node_arrival_times["merge"]
        < veh_late.order_control_node_arrival_times["merge"]
    )

    outlink = W.get_link("out")
    passage_names = _passage_order_on_link(outlink)
    assert passage_names.index("veh_early") < passage_names.index("veh_late")

    assert veh_early.state == "end"
    assert veh_late.state == "end"

    print("FCFS arrival-order behavior test passed.")


def test_fcfs_skips_blocked_first_arrival_and_serves_next_feasible_vehicle():
    W = World(
        name="fcfs_blocked_first_skip_behavior",
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
    W.addNode("dest1", 2, 0)
    W.addNode("dest2", 2, 2)

    W.addLink(
        "link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1
    )
    W.addLink(
        "link2", "orig2", "merge", length=600, free_flow_speed=20, number_of_lanes=1
    )
    W.addLink(
        "out1",
        "merge",
        "dest1",
        length=500,
        free_flow_speed=20,
        number_of_lanes=1,
        capacity_in=0,
    )
    W.addLink(
        "out2", "merge", "dest2", length=500, free_flow_speed=20, number_of_lanes=1
    )

    W.infer_order_control_eligible_nodes()
    merge = W.get_node("merge")
    assert merge.order_control_eligible is True

    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")
    assert merge.order_control_type == "fcfs"

    veh_early_blocked = W.addVehicle("orig1", "dest1", 0, name="veh_early_blocked")
    veh_late_feasible = W.addVehicle("orig2", "dest2", 0, name="veh_late_feasible")

    W.exec_simulation()

    assert "merge" in veh_early_blocked.order_control_node_arrival_times
    assert "merge" in veh_late_feasible.order_control_node_arrival_times
    assert (
        veh_early_blocked.order_control_node_arrival_times["merge"]
        < veh_late_feasible.order_control_node_arrival_times["merge"]
    )

    out1 = W.get_link("out1")
    out2 = W.get_link("out2")

    assert all(
        veh.name != "veh_early_blocked" for veh in out1.vehicles_enter_log.values()
    )
    assert any(
        veh.name == "veh_late_feasible" for veh in out2.vehicles_enter_log.values()
    )

    assert veh_late_feasible.state == "end"

    print("FCFS blocked-first-vehicle skip behavior test passed.")


if __name__ == "__main__":
    test_fcfs_arrival_order_matches_passing_order()
    test_fcfs_skips_blocked_first_arrival_and_serves_next_feasible_vehicle()
    print("FCFS order control behavior tests all passed.")
