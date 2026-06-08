# Verify research attributes on Vehicle via World.addVehicle().
#
# Run from the repository root:
#   python tests_vehicle_research_attributes.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="vehicle_research_attributes",
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

W.addVehicle(
    "orig",
    "dest",
    0,
    name="veh_attr_test",
    vot_true=10.0,
    vot_declared=8.0,
    payment_paid=1.5,
    payment_received=0.25,
    order_exchange_log=[{"event": "test"}],
)

veh = W.VEHICLES["veh_attr_test"]
assert veh.vot_true == 10.0
assert veh.vot_declared == 8.0
assert veh.payment_paid == 1.5
assert veh.payment_received == 0.25
assert veh.order_exchange_log == [{"event": "test"}]

W.addVehicle("orig", "dest", 10, name="veh_default_log")

veh_default = W.VEHICLES["veh_default_log"]
assert veh_default.order_exchange_log == []

print("Vehicle research attributes test passed.")
