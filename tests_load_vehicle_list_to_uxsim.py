# Load a CSV vehicle list into UXsim and verify attributes are preserved.
#
# Run from the repository root:
#   python tests_load_vehicle_list_to_uxsim.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import tempfile
from pathlib import Path

from generate_vehicle_list_for_order_exchange import generate_vehicle_list, load_vehicle_list_to_world
from uxsim import World

W = World(
    name="load_vehicle_list_test",
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

with tempfile.TemporaryDirectory() as tmpdir:
    csv_path = Path(tmpdir) / "vehicle_list_seed0.csv"
    generate_vehicle_list(seed=0, output_csv=str(csv_path))
    rows = load_vehicle_list_to_world(W, csv_path)

assert len(rows) == len(W.VEHICLES)

first = rows[0]
veh = W.VEHICLES[first["vehicle_id"]]
assert veh.name == first["vehicle_id"]
assert veh.vot_true == float(first["vot_true"])
assert veh.vot_declared == (
    float(first["vot_declared"]) if first["vot_declared"] != "" else None
)
assert veh.participates_in_order_exchange == (first["participates_in_order_exchange"] == "True")
assert veh.payment_paid == 0
assert veh.payment_received == 0
assert veh.order_exchange_log == []

W.exec_simulation()

for veh in W.VEHICLES.values():
    assert veh.state == "end"

print(f"Loaded vehicles: {len(rows)}")
print("Vehicle list loading test passed.")
