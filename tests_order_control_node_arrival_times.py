# Verify first arrival-time recording at order-control nodes.
#
# Run from the repository root:
#   python tests_order_control_node_arrival_times.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="order_control_node_arrival_times",
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

W.addLink("link1", "orig1", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W.addLink("link2", "orig2", "merge", length=500, free_flow_speed=16.67, number_of_lanes=1)
W.addLink(
    "link3",
    "merge",
    "dest",
    length=500,
    free_flow_speed=16.67,
    number_of_lanes=1,
    capacity_in=0,
)

W.infer_order_control_eligible_nodes()
assert W.get_node("merge").order_control_eligible is True

W.set_order_control_for_nodes(
    ["merge"],
    order_control_type="fcfs",
)

veh = W.addVehicle("orig1", "dest", 0, name="veh_arrival_test")

while "merge" not in veh.order_control_node_arrival_times:
    if not W.check_simulation_ongoing():
        raise AssertionError("Vehicle did not reach merge before simulation end")
    W.exec_simulation(duration_t2=1)

first_time = veh.order_control_node_arrival_times["merge"]
assert isinstance(first_time, (int, float))
assert first_time > 0
assert first_time % W.DELTAT == 0

for _ in range(5):
    if not W.check_simulation_ongoing():
        break
    W.exec_simulation(duration_t2=1)

assert veh.order_control_node_arrival_times["merge"] == first_time

W_none = World(
    name="order_control_node_arrival_times_none",
    deltan=1,
    tmax=100,
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
assert W_none.get_node("merge").order_control_eligible is True
assert W_none.get_node("merge").order_control_type == "none"

veh_none = W_none.addVehicle("orig1", "dest", 0, name="veh_none_control")

while veh_none.link is None or not (
    veh_none.link.end_node.name == "merge" and veh_none.x == veh_none.link.length
):
    if not W_none.check_simulation_ongoing():
        raise AssertionError("Vehicle did not reach merge end before simulation end")
    W_none.exec_simulation(duration_t2=1)

assert "merge" not in veh_none.order_control_node_arrival_times

print("Order-control node arrival time test passed.")
