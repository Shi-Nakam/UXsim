# Verify BATCH node settings for t_trigger level and batch_size.
#
# Run from the repository root:
#   python tests_order_control_batch_node_settings.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy

from uxsim import World


def _build_world(name="batch_node_settings"):
    return World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )


def _snapshot_nodes(nodes):
    return {
        node.name: {
            "order_control_type": node.order_control_type,
            "batch_size": node.batch_size,
            "transaction_case": node.transaction_case,
            "order_control_batch_t_trigger_level": node.order_control_batch_t_trigger_level,
        }
        for node in nodes
    }


def _expect_value_error(callable_obj, message_substrings=()):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError as exc:
        message = str(exc)
        for substring in message_substrings:
            assert substring in message, f"expected {substring!r} in {message!r}"


def test_node_attribute_defaults():
    W = _build_world("batch_settings_defaults")
    node_default = W.addNode("node_default", 0, 0)
    node_fcfs = W.addNode(
        "node_fcfs", 1, 0, order_control_eligible=True, order_control_type="fcfs"
    )
    node_batch = W.addNode(
        "node_batch", 2, 0, order_control_eligible=True, order_control_type="batch"
    )
    node_tv = W.addNode(
        "node_tv",
        3,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
        transaction_case="I",
    )

    for node in (node_default, node_fcfs, node_batch, node_tv):
        assert node.batch_size == 1
        assert node.order_control_batch_t_trigger_level == 1


def test_world_addnode_individual_specification():
    W = _build_world("batch_settings_addnode")
    merge_a = W.addNode(
        "merge_a",
        0,
        0,
        order_control_eligible=True,
        order_control_type="batch",
        batch_size=10,
        order_control_batch_t_trigger_level=1,
    )
    merge_b = W.addNode(
        "merge_b",
        1,
        0,
        order_control_eligible=True,
        order_control_type="batch",
        batch_size=5,
        order_control_batch_t_trigger_level=0,
    )

    assert merge_a.batch_size == 10
    assert merge_a.order_control_batch_t_trigger_level == 1
    assert merge_b.batch_size == 5
    assert merge_b.order_control_batch_t_trigger_level == 0


def test_set_order_control_for_nodes_bulk():
    W = _build_world("batch_settings_bulk")
    node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
    node_b = W.addNode("node_b", 1, 0, order_control_eligible=True)
    node_outside = W.addNode("node_outside", 2, 0)
    before_outside = _snapshot_nodes([node_outside])

    W.set_order_control_for_nodes(
        ["node_a", "node_b"],
        order_control_type="batch",
        batch_size=10,
        transaction_case=None,
        order_control_batch_t_trigger_level=1,
    )

    for node in (node_a, node_b):
        assert node.order_control_type == "batch"
        assert node.batch_size == 10
        assert node.order_control_batch_t_trigger_level == 1

    assert _snapshot_nodes([node_outside]) == before_outside


def test_sensitivity_analysis_batch_size_bulk_change():
    W = _build_world("batch_settings_sensitivity")
    node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
    node_b = W.addNode("node_b", 1, 0, order_control_eligible=True)
    target_names = ["node_a", "node_b"]

    W.set_order_control_for_nodes(
        target_names,
        order_control_type="batch",
        batch_size=10,
        transaction_case=None,
        order_control_batch_t_trigger_level=1,
    )
    W.set_order_control_for_nodes(
        target_names,
        order_control_type="batch",
        batch_size=5,
        transaction_case=None,
        order_control_batch_t_trigger_level=1,
    )

    for node in (node_a, node_b):
        assert node.batch_size == 5
        assert node.order_control_batch_t_trigger_level == 1

    W.set_order_control_for_nodes(
        target_names,
        order_control_type="batch",
        batch_size=20,
        transaction_case=None,
        order_control_batch_t_trigger_level=1,
    )

    for node in (node_a, node_b):
        assert node.batch_size == 20
        assert node.order_control_batch_t_trigger_level == 1


def test_partial_node_override():
    W = _build_world("batch_settings_override")
    node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
    node_b = W.addNode("node_b", 1, 0, order_control_eligible=True)
    special = W.addNode("special_node", 2, 0, order_control_eligible=True)

    W.set_order_control_for_nodes(
        ["node_a", "node_b", "special_node"],
        order_control_type="batch",
        batch_size=10,
        transaction_case=None,
        order_control_batch_t_trigger_level=1,
    )

    W.set_order_control_for_nodes(
        ["special_node"],
        order_control_type="batch",
        batch_size=3,
        transaction_case=None,
        order_control_batch_t_trigger_level=0,
    )

    assert special.batch_size == 3
    assert special.order_control_batch_t_trigger_level == 0
    for node in (node_a, node_b):
        assert node.batch_size == 10
        assert node.order_control_batch_t_trigger_level == 1


def test_random_selected_nodes():
    W = _build_world("batch_settings_random")
    merges = []
    for i in range(1, 5):
        orig_a = W.addNode(f"orig{i}a", 0, i)
        orig_b = W.addNode(f"orig{i}b", 1, i)
        merge = W.addNode(f"merge{i}", 2, i)
        dest = W.addNode(f"dest{i}", 3, i)
        W.addLink(f"link{i}a", orig_a.name, merge.name, length=200, free_flow_speed=20, number_of_lanes=1)
        W.addLink(f"link{i}b", orig_b.name, merge.name, length=200, free_flow_speed=20, number_of_lanes=1)
        W.addLink(f"link{i}c", merge.name, dest.name, length=200, free_flow_speed=20, number_of_lanes=1)
        merges.append(merge)

    W.infer_order_control_eligible_nodes()
    before = _snapshot_nodes(merges)

    selected = W.set_order_control_for_randomly_selected_eligible_nodes(
        fraction=0.5,
        order_control_type="batch",
        batch_size=10,
        transaction_case=None,
        random_seed=0,
        order_control_batch_t_trigger_level=1,
    )

    selected_names = {node.name for node in selected}
    for node in selected:
        assert node.order_control_type == "batch"
        assert node.batch_size == 10
        assert node.order_control_batch_t_trigger_level == 1

    for node in merges:
        if node.name in selected_names:
            continue
        assert _snapshot_nodes([node])[node.name] == before[node.name]


def test_addnode_t_trigger_level_validation():
    W = _build_world("batch_settings_addnode_validation")
    before_count = len(W.NODES)

    for invalid in (-1, 3, 1.5, "1", True, False, None):
        try:
            W.addNode(
                f"bad_{invalid}",
                0,
                0,
                order_control_eligible=True,
                order_control_type="batch",
                order_control_batch_t_trigger_level=invalid,
            )
            assert False, f"expected ValueError for {invalid!r}"
        except ValueError as exc:
            assert "expected 0 or 1" in str(exc) or "non-bool int" in str(exc)
        assert len(W.NODES) == before_count

    try:
        W.addNode(
            "bad_level_2",
            0,
            0,
            order_control_eligible=True,
            order_control_type="batch",
            order_control_batch_t_trigger_level=2,
        )
        assert False, "expected ValueError for level 2"
    except ValueError as exc:
        message = str(exc)
        assert "bad_level_2" in message
        assert "order_control_batch_t_trigger_level=2" in message
        assert "Level 2 is planned" in message
        assert "virtual-service estimation is not yet implemented" in message
    assert len(W.NODES) == before_count


def test_setter_t_trigger_level_validation():
    W = _build_world("batch_settings_setter_validation")
    node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
    node_b = W.addNode("node_b", 1, 0, order_control_eligible=True)
    nodes = [node_a, node_b]
    before = _snapshot_nodes(nodes)

    for invalid in (-1, 3, 1.5, "1", True, False, None):
        _expect_value_error(
            lambda invalid=invalid: W.set_order_control_for_nodes(
                ["node_a", "node_b"],
                order_control_type="batch",
                batch_size=10,
                order_control_batch_t_trigger_level=invalid,
            ),
            message_substrings=("expected 0 or 1",),
        )
        assert _snapshot_nodes(nodes) == before

    _expect_value_error(
        lambda: W.set_order_control_for_nodes(
            ["node_a", "node_b"],
            order_control_type="batch",
            batch_size=10,
            order_control_batch_t_trigger_level=2,
        ),
        message_substrings=(
            "order_control_batch_t_trigger_level=2",
            "Level 2",
            "virtual-service estimation is not yet implemented",
        ),
    )
    assert _snapshot_nodes(nodes) == before


def test_random_setter_t_trigger_level_validation():
    W = _build_world("batch_settings_random_validation")
    orig_a = W.addNode("orig_a", 0, 0)
    orig_b = W.addNode("orig_b", 0, 1)
    merge = W.addNode("merge", 1, 0)
    dest = W.addNode("dest", 2, 0)
    W.addLink("link1", "orig_a", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig_b", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.infer_order_control_eligible_nodes()
    before = _snapshot_nodes([merge])

    _expect_value_error(
        lambda: W.set_order_control_for_randomly_selected_eligible_nodes(
            fraction=1.0,
            order_control_type="batch",
            batch_size=10,
            random_seed=0,
            order_control_batch_t_trigger_level=2,
        ),
        message_substrings=(
            "order_control_batch_t_trigger_level=2",
            "Level 2",
            "virtual-service estimation is not yet implemented",
        ),
    )
    assert _snapshot_nodes([merge]) == before


def test_batch_size_existing_validation():
    W = _build_world("batch_settings_batch_size_validation")
    node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
    before = _snapshot_nodes([node_a])

    for invalid in (0, -1, 1.5, "10", True, False, None):
        _expect_value_error(
            lambda invalid=invalid: W.set_order_control_for_nodes(
                ["node_a"],
                order_control_type="batch",
                batch_size=invalid,
            ),
            message_substrings=("batch_size",),
        )
        assert _snapshot_nodes([node_a]) == before


def test_partial_update_prevention():
    W = _build_world("batch_settings_partial_update")
    node_a = W.addNode("node_a", 0, 0, order_control_eligible=True)
    node_b = W.addNode("node_b", 1, 0, order_control_eligible=True)
    node_ineligible = W.addNode("node_ineligible", 2, 0)
    nodes = [node_a, node_b, node_ineligible]
    before = _snapshot_nodes(nodes)

    _expect_value_error(
        lambda: W.set_order_control_for_nodes(
            ["node_a", "node_b", "node_ineligible"],
            order_control_type="batch",
            batch_size=10,
            order_control_batch_t_trigger_level=1,
        )
    )
    assert _snapshot_nodes(nodes) == before

    _expect_value_error(
        lambda: W.set_order_control_for_nodes(
            ["node_a", "node_b"],
            order_control_type="batch",
            batch_size=10,
            order_control_batch_t_trigger_level=3,
        ),
        message_substrings=("expected 0 or 1",),
    )
    assert _snapshot_nodes(nodes) == before


def main():
    test_node_attribute_defaults()
    test_world_addnode_individual_specification()
    test_set_order_control_for_nodes_bulk()
    test_sensitivity_analysis_batch_size_bulk_change()
    test_partial_node_override()
    test_random_selected_nodes()
    test_addnode_t_trigger_level_validation()
    test_setter_t_trigger_level_validation()
    test_random_setter_t_trigger_level_validation()
    test_batch_size_existing_validation()
    test_partial_update_prevention()
    print("Order-control batch node-setting tests passed.")


if __name__ == "__main__":
    main()
