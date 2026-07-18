# Verify automatic and manual setting of order_control_eligible.
#
# Run from the repository root:
#   python tests_order_control_eligibility.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="order_control_eligibility",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

orig1 = W.addNode("orig1", 0, 0)
orig2 = W.addNode("orig2", 0, 2)
merge = W.addNode("merge", 1, 1)
dest = W.addNode("dest", 2, 1)

W.addLink("link1", "orig1", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W.addLink("link2", "orig2", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W.addLink("link3", "merge", "dest", length=500, free_flow_speed=16.67, number_of_lanes=1)

eligible_nodes = W.infer_order_control_eligible_nodes()
assert merge.order_control_eligible is True
assert orig1.order_control_eligible is False
assert orig2.order_control_eligible is False
assert dest.order_control_eligible is False
assert eligible_nodes == [merge]

W.set_order_control_eligible_flag_for_nodes(["orig1"], True)
assert orig1.order_control_eligible is True

W.set_order_control_eligible_flag_for_nodes(["merge"], False)
assert merge.order_control_eligible is False

try:
    W.set_order_control_eligible_flag_for_nodes(["merge"], "yes")
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for non-bool is_eligible")

try:
    W.set_order_control_for_nodes(["merge"], order_control_type="batch", batch_size=10)
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError for ineligible merge node")

W.set_order_control_eligible_flag_for_nodes(["merge"], True)
configured = W.set_order_control_for_nodes(
    ["merge"],
    order_control_type="batch",
    batch_size=10,
    order_control_batch_t_trigger_level=1,
)
assert configured == [merge]
assert merge.order_control_type == "batch"
assert merge.batch_size == 10
assert merge.order_control_batch_t_trigger_level == 1

W.set_order_control_eligible_flag_for_nodes(["merge"], False)
W.set_order_control_for_nodes(["merge"], order_control_type="none")
assert merge.order_control_type == "none"
assert merge.batch_size == 1
assert merge.transaction_case is None

W_single = World(
    name="order_control_eligibility_single",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

W_single.addNode("orig_single", 0, 0)
mid_single = W_single.addNode("mid_single", 1, 0)
W_single.addNode("dest_single", 2, 0)
W_single.addLink("link_single1", "orig_single", "mid_single", length=500, free_flow_speed=16.67, number_of_lanes=1)
W_single.addLink("link_single2", "mid_single", "dest_single", length=500, free_flow_speed=16.67, number_of_lanes=1)

eligible_nodes_single = W_single.infer_order_control_eligible_nodes()
assert mid_single.order_control_eligible is False
assert eligible_nodes_single == []

print("Order control eligibility test passed.")
