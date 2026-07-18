# Verify World.set_order_control_for_nodes().
#
# Run from the repository root:
#   python tests_world_order_control_setters.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="world_order_control_setters",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
node_b = W.addNode("node_b", 1, 0, order_control_eligible=True)
node_c = W.addNode("node_c", 2, 0, order_control_eligible=True)
node_d = W.addNode("node_d", 3, 0, order_control_eligible=True)
node_ineligible = W.addNode("node_ineligible", 4, 0)

for node in (node_a, node_b, node_c, node_d):
    assert node.order_control_type == "none"
    assert node.batch_size == 1
    assert node.transaction_case is None

configured = W.set_order_control_for_nodes(
    ["node_a", "node_b"],
    order_control_type="batch",
    batch_size=10,
)
assert configured == [node_a, node_b]

for node in (node_a, node_b):
    assert node.order_control_type == "batch"
    assert node.batch_size == 10
    assert node.transaction_case is None
    assert node.order_control_batch_t_trigger_level == 1

for node in (node_c, node_d):
    assert node.order_control_type == "none"
    assert node.batch_size == 1
    assert node.transaction_case is None
    assert node.order_control_batch_t_trigger_level == 1

W.set_order_control_for_nodes(["node_c"], order_control_type="time_value", transaction_case="I")
assert node_c.order_control_type == "time_value"
assert node_c.batch_size == 1
assert node_c.transaction_case == "I"

W.set_order_control_for_nodes(["node_d"], order_control_type="fcfs")
assert node_d.order_control_type == "fcfs"
assert node_d.batch_size == 1
assert node_d.transaction_case is None

for kwargs in (
    {"order_control_type": "invalid"},
    {"batch_size": 0},
    {"transaction_case": "IV"},
):
    try:
        W.set_order_control_for_nodes(["node_a"], **kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected ValueError for {kwargs}")

for order_control_type in ("batch", "time_value", "fcfs"):
    try:
        W.set_order_control_for_nodes(
            ["node_ineligible"],
            order_control_type=order_control_type,
            batch_size=10,
            transaction_case="I",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            f"Expected ValueError for ineligible node with order_control_type={order_control_type!r}"
        )

W.set_order_control_for_nodes(["node_ineligible"], order_control_type="none")
assert node_ineligible.order_control_type == "none"

print("World order control setters test passed.")
