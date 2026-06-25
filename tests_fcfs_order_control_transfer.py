# Verify FCFS order-control transfer at merge nodes.
#
# Run from the repository root:
#   python tests_fcfs_order_control_transfer.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="fcfs_order_control_transfer",
    deltan=1,
    tmax=600,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

W.addNode("orig1", 0, 0)
W.addNode("orig2", 0, 2)
W.addNode("merge", 1, 1)
W.addNode("dest", 2, 1)

W.addLink("link1", "orig1", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W.addLink("link2", "orig2", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W.addLink("link3", "merge", "dest", length=500, free_flow_speed=16.67, number_of_lanes=1)

W.infer_order_control_eligible_nodes()
merge = W.get_node("merge")
assert merge.order_control_eligible is True

W.set_order_control_for_nodes(
    ["merge"],
    order_control_type="fcfs",
)
assert merge.order_control_type == "fcfs"

W.adddemand("orig1", "dest", 0, 300, 0.15)
W.adddemand("orig2", "dest", 0, 300, 0.15)

W.exec_simulation()

completed = sum(1 for veh in W.VEHICLES.values() if veh.state == "end")
assert completed == len(W.VEHICLES)

arrival_recorded = sum(
    1 for veh in W.VEHICLES.values() if "merge" in veh.order_control_node_arrival_times
)
assert arrival_recorded == len(W.VEHICLES)

W_none = World(
    name="fcfs_none_control_baseline",
    deltan=1,
    tmax=200,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

W_none.addNode("orig1", 0, 0)
W_none.addNode("orig2", 0, 2)
W_none.addNode("merge", 1, 1)
W_none.addNode("dest", 2, 1)

W_none.addLink("link1", "orig1", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W_none.addLink("link2", "orig2", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W_none.addLink("link3", "merge", "dest", length=500, free_flow_speed=16.67, number_of_lanes=1)

W_none.infer_order_control_eligible_nodes()
assert W_none.get_node("merge").order_control_type == "none"

W_none.adddemand("orig1", "dest", 0, 120, 0.2)
W_none.adddemand("orig2", "dest", 0, 120, 0.2)
W_none.exec_simulation()

completed_none = sum(1 for veh in W_none.VEHICLES.values() if veh.state == "end")
assert completed_none == len(W_none.VEHICLES)

arrival_recorded_none = sum(
    1 for veh in W_none.VEHICLES.values() if "merge" in veh.order_control_node_arrival_times
)
assert arrival_recorded_none == 0

print("FCFS order control transfer test passed.")
