# Load a CSV vehicle list into UXsim and verify attributes are preserved.
#
# Run from the repository root:
#   python tests_load_vehicle_list_to_uxsim.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import csv
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

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    rows[0]["participates_in_order_exchange"] = "False"
    rows[0]["vot_declared"] = ""

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    rows = load_vehicle_list_to_world(W, csv_path)

assert len(rows) == len(W.VEHICLES)

non_participating = rows[0]
veh_np = W.VEHICLES[non_participating["vehicle_id"]]
assert veh_np.participates_in_order_exchange is False
assert veh_np.vot_declared is None
assert veh_np.vot_true == float(non_participating["vot_true"])
assert veh_np.payment_paid == 0
assert veh_np.payment_received == 0
assert veh_np.order_exchange_log == []

participating = rows[1]
veh = W.VEHICLES[participating["vehicle_id"]]
assert veh.name == participating["vehicle_id"]
assert veh.vot_true == float(participating["vot_true"])
assert veh.vot_declared == (
    float(participating["vot_declared"]) if participating["vot_declared"] != "" else None
)
assert veh.participates_in_order_exchange == (participating["participates_in_order_exchange"] == "True")
assert veh.payment_paid == 0
assert veh.payment_received == 0
assert veh.order_exchange_log == []

W.exec_simulation()

for veh in W.VEHICLES.values():
    assert veh.state == "end"

print(f"Loaded vehicles: {len(rows)}")
print("Vehicle list loading test passed.")
