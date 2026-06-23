# Verify intersection order control attributes on Node via World.addNode().
#
# Run from the repository root:
#   python tests_node_order_control_attributes.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="node_order_control_attributes",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

node_default = W.addNode("node_default", 0, 0)
assert node_default.order_control_type == "none"
assert node_default.batch_size == 1
assert node_default.transaction_case is None
assert node_default.order_control_eligible is False

node_eligible = W.addNode("node_eligible", 4, 0, order_control_eligible=True)
assert node_eligible.order_control_eligible is True

node_fcfs = W.addNode(
    "node_fcfs", 1, 0, order_control_eligible=True, order_control_type="fcfs"
)
assert node_fcfs.order_control_type == "fcfs"
assert node_fcfs.batch_size == 1
assert node_fcfs.transaction_case is None
assert node_fcfs.order_control_eligible is True

node_batch = W.addNode(
    "node_batch", 2, 0, order_control_eligible=True, order_control_type="batch", batch_size=10
)
assert node_batch.order_control_type == "batch"
assert node_batch.batch_size == 10
assert node_batch.transaction_case is None

node_tv = W.addNode(
    "node_tv",
    3,
    0,
    order_control_eligible=True,
    order_control_type="time_value",
    transaction_case="I",
)
assert node_tv.order_control_type == "time_value"
assert node_tv.batch_size == 1
assert node_tv.transaction_case == "I"

for kwargs in (
    {"order_control_type": "invalid"},
    {"batch_size": 0},
    {"transaction_case": "IV"},
):
    try:
        W.addNode("bad_node", 9, 9, **kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected ValueError for {kwargs}")

try:
    W.addNode("bad_fcfs", 0, 0, order_control_type="fcfs")
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for fcfs node without order_control_eligible=True")

try:
    W.addNode("bad_batch", 0, 0, order_control_type="batch")
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for batch node without order_control_eligible=True")

try:
    W.addNode("bad_time_value", 0, 0, order_control_type="time_value")
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for time_value node without order_control_eligible=True")

node_none = W.addNode("node_none_allowed", 0, 0, order_control_type="none")
assert node_none.order_control_type == "none"
assert node_none.order_control_eligible is False

node_fcfs_allowed = W.addNode(
    "node_fcfs_allowed",
    0,
    0,
    order_control_eligible=True,
    order_control_type="fcfs",
)
assert node_fcfs_allowed.order_control_type == "fcfs"
assert node_fcfs_allowed.order_control_eligible is True

try:
    W.addNode("bad_eligible_type", 0, 0, order_control_eligible="yes")
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for non-bool order_control_eligible")

try:
    W.addNode("bad_eligible_int", 0, 0, order_control_eligible=1)
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for int order_control_eligible")

print("Node order control attributes test passed.")
