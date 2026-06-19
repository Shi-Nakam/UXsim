# Verify random selection from order_control_eligible nodes.
#
# Run from the repository root:
#   python tests_random_eligible_order_control.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def build_four_merge_network(W):
    merges = []
    for i in range(1, 5):
        orig_a = W.addNode(f"orig{i*2-1}", 0, i)
        orig_b = W.addNode(f"orig{i*2}", 1, i)
        merge = W.addNode(f"merge{i}", 2, i)
        dest = W.addNode(f"dest{i}", 3, i)
        W.addLink(f"link{i}a", f"orig{i*2-1}", f"merge{i}", length=500, free_flow_speed=16.67, number_of_lanes=1)
        W.addLink(f"link{i}b", f"orig{i*2}", f"merge{i}", length=500, free_flow_speed=16.67, number_of_lanes=1)
        W.addLink(f"link{i}c", f"merge{i}", f"dest{i}", length=500, free_flow_speed=16.67, number_of_lanes=1)
        merges.append(merge)
    return merges


W = World(
    name="random_eligible_order_control",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)

merges = build_four_merge_network(W)

try:
    W.set_order_control_for_randomly_selected_eligible_nodes(
        fraction=0.5,
        order_control_type="batch",
        batch_size=10,
        random_seed=0,
    )
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError before infer_order_control_eligible_nodes()")

eligible_nodes = W.infer_order_control_eligible_nodes()
assert eligible_nodes == merges

selected = W.set_order_control_for_randomly_selected_eligible_nodes(
    fraction=0.5,
    order_control_type="batch",
    batch_size=10,
    random_seed=0,
)
assert len(selected) == 2

selected_names = {node.name for node in selected}
for node in selected:
    assert node.order_control_type == "batch"
    assert node.batch_size == 10
    assert node.transaction_case is None
    assert node.order_control_eligible is True

for merge in merges:
    if merge.name in selected_names:
        continue
    assert merge.order_control_type == "none"

W2 = World(
    name="random_eligible_order_control_repro",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)
build_four_merge_network(W2)
W2.infer_order_control_eligible_nodes()
selected2 = W2.set_order_control_for_randomly_selected_eligible_nodes(
    fraction=0.5,
    order_control_type="batch",
    batch_size=10,
    random_seed=0,
)
assert [node.name for node in selected2] == [node.name for node in selected]

assert W.set_order_control_for_randomly_selected_eligible_nodes(fraction=0, random_seed=0) == []

for bad_fraction in (-0.1, 1.1, True, "0.5"):
    try:
        W.set_order_control_for_randomly_selected_eligible_nodes(
            fraction=bad_fraction,
            order_control_type="batch",
            random_seed=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected ValueError for fraction={bad_fraction!r}")

W_empty_candidates = World(
    name="random_eligible_order_control_empty",
    deltan=1,
    tmax=100,
    print_mode=0,
    save_mode=0,
    show_mode=0,
    random_seed=0,
)
W_empty_candidates.addNode("orig_single", 0, 0)
W_empty_candidates.addNode("mid_single", 1, 0)
W_empty_candidates.addNode("dest_single", 2, 0)
W_empty_candidates.addLink("link_single1", "orig_single", "mid_single", length=500, free_flow_speed=16.67, number_of_lanes=1)
W_empty_candidates.addLink("link_single2", "mid_single", "dest_single", length=500, free_flow_speed=16.67, number_of_lanes=1)
W_empty_candidates.infer_order_control_eligible_nodes()

try:
    W_empty_candidates.set_order_control_for_randomly_selected_eligible_nodes(
        fraction=0.5,
        order_control_type="batch",
        random_seed=0,
    )
except ValueError:
    pass
else:
    raise AssertionError("Expected ValueError when no eligible nodes are available")

print("Random eligible order control test passed.")
