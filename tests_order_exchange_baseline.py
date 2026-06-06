# Baseline scenario for order-exchange intersection algorithm development.
#
# Run from the repository root:
#   python tests_order_exchange_baseline.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

W = World(
    name="order_exchange_baseline",
    deltan=1,
    tmax=600,
    print_mode=1,
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

W.adddemand("orig1", "dest", 0, 120, 0.2)
W.adddemand("orig2", "dest", 0, 120, 0.2)

W.exec_simulation()
W.analyzer.print_simple_stats()
