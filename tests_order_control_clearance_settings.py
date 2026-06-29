# Verify order-control clearance settings on World and Node.
#
# Run from the repository root:
#   python tests_order_control_clearance_settings.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def test_order_control_clearance_default_and_setter():
    W = World(
        name="order_control_clearance_default",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )

    assert W.order_control_clearance_timesteps == 1

    node_a = W.addNode("node_a", 0, 0)
    node_b = W.addNode("node_b", 1, 0)

    for node in (node_a, node_b):
        assert hasattr(node, "order_control_clearance_timesteps")
        assert node.order_control_clearance_timesteps == 1
        assert node.last_order_control_inlink is None
        assert node.last_order_control_entry_timestep is None

    W.set_order_control_clearance_timesteps(0)
    assert W.order_control_clearance_timesteps == 0
    for node in W.NODES:
        assert node.order_control_clearance_timesteps == 0

    W.set_order_control_clearance_timesteps(2)
    assert W.order_control_clearance_timesteps == 2
    for node in W.NODES:
        assert node.order_control_clearance_timesteps == 2


def test_new_node_inherits_current_world_clearance_setting():
    W = World(
        name="order_control_clearance_new_node",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )

    W.addNode("node_a", 0, 0)
    W.set_order_control_clearance_timesteps(2)

    new_node = W.addNode("node_b", 1, 0)
    assert new_node.order_control_clearance_timesteps == 2
    assert new_node.last_order_control_inlink is None
    assert new_node.last_order_control_entry_timestep is None


def test_order_control_clearance_setting_independent_of_set_order_control_for_nodes():
    W = World(
        name="order_control_clearance_with_fcfs",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )

    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("merge", 1, 1)
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)

    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(2)
    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")

    merge = W.get_node("merge")
    assert merge.order_control_type == "fcfs"
    assert merge.order_control_clearance_timesteps == 2


def test_order_control_clearance_rejects_invalid_values():
    W = World(
        name="order_control_clearance_validation",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )

    invalid_values = (-1, 1.5, "1", True, False)
    for value in invalid_values:
        try:
            W.set_order_control_clearance_timesteps(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for clearance_timesteps={value!r}")


if __name__ == "__main__":
    test_order_control_clearance_default_and_setter()
    test_new_node_inherits_current_world_clearance_setting()
    test_order_control_clearance_setting_independent_of_set_order_control_for_nodes()
    test_order_control_clearance_rejects_invalid_values()
    print("Order-control clearance settings test passed.")
