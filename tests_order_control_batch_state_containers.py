# Verify BATCH Processing state containers on Vehicle and Node.
#
# Run from the repository root:
#   python tests_order_control_batch_state_containers.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from collections import deque

from uxsim import World


def test_vehicle_initial_batch_assignments():
    W = World(
        name="batch_state_vehicle_initial",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode("dest", 1, 0)
    W.addLink("link1", "orig", "dest", length=500, free_flow_speed=16.67, number_of_lanes=1)

    veh = W.addVehicle("orig", "dest", 0, name="veh_batch_state")
    assert veh.order_control_batch_assignments == {}
    assert isinstance(veh.order_control_batch_assignments, dict)


def test_node_initial_batch_state():
    W = World(
        name="batch_state_node_initial",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    node = W.addNode("merge", 0, 0)

    assert isinstance(node.order_control_batch_service_queue, deque)
    assert len(node.order_control_batch_service_queue) == 0
    assert node.order_control_batch_next_id == 0


def test_node_batch_state_independence():
    W = World(
        name="batch_state_node_independence",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    node_a = W.addNode("node_a", 0, 0)
    node_b = W.addNode("node_b", 1, 0)

    assert node_a.order_control_batch_service_queue is not node_b.order_control_batch_service_queue
    node_a.order_control_batch_service_queue.append("test_service_unit")
    assert len(node_a.order_control_batch_service_queue) == 1
    assert len(node_b.order_control_batch_service_queue) == 0
    node_a.order_control_batch_service_queue.clear()


def test_vehicle_batch_assignments_independence():
    W = World(
        name="batch_state_vehicle_independence",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode("dest", 1, 0)
    W.addLink("link1", "orig", "dest", length=500, free_flow_speed=16.67, number_of_lanes=1)

    veh1 = W.addVehicle("orig", "dest", 0, name="veh_batch_state_1")
    veh2 = W.addVehicle("orig", "dest", 10, name="veh_batch_state_2")

    assert veh1.order_control_batch_assignments is not veh2.order_control_batch_assignments
    veh1.order_control_batch_assignments["merge"] = 0
    assert veh1.order_control_batch_assignments == {"merge": 0}
    assert veh2.order_control_batch_assignments == {}


def test_simulation_leaves_batch_containers_untouched():
    W = World(
        name="batch_state_simulation_unchanged",
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    orig = W.addNode("orig", 0, 0)
    dest = W.addNode("dest", 1, 0)
    W.addLink("link1", "orig", "dest", length=500, free_flow_speed=16.67, number_of_lanes=1)

    veh = W.addVehicle("orig", "dest", 0, name="veh_batch_sim")
    assert orig.order_control_type == "none"

    W.exec_simulation()

    assert veh.state == "end"
    assert veh.order_control_batch_assignments == {}
    assert len(orig.order_control_batch_service_queue) == 0
    assert len(dest.order_control_batch_service_queue) == 0
    assert orig.order_control_batch_next_id == 0
    assert dest.order_control_batch_next_id == 0


if __name__ == "__main__":
    test_vehicle_initial_batch_assignments()
    test_node_initial_batch_state()
    test_node_batch_state_independence()
    test_vehicle_batch_assignments_independence()
    test_simulation_leaves_batch_containers_untouched()
    print("Order-control batch state containers test passed.")
