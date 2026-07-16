# Verify per-inlink maximum batch size application.
#
# Run from the repository root:
#   python tests_order_control_batch_max_size_application.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy

from uxsim import World


def _build_network(name="batch_max_size"):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("orig3", 0, 4)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _make_vehicle(W, orig_name, name):
    return W.addVehicle(orig_name, "dest", 0, name=name)


def _vehicles(names, W, orig="orig1"):
    return [_make_vehicle(W, orig, name) for name in names]


def _expect_value_error(callable_obj):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError:
        pass


def _snapshot_state(merge, ordered_input, vehicles):
    return {
        "ordered_input": [(inlink, list(candidates)) for inlink, candidates in ordered_input],
        "inlink_vehicles": {
            link.name: list(link.vehicles) for link in merge.inlinks.values()
        },
        "incoming_vehicles": list(merge.incoming_vehicles),
        "service_queue": list(merge.order_control_batch_service_queue),
        "next_id": merge.order_control_batch_next_id,
        "last_inlink": merge.last_order_control_inlink,
        "last_entry_timestep": merge.last_order_control_entry_timestep,
        "clearance_timesteps": merge.order_control_clearance_timesteps,
        "W_T": getattr(merge.W, "T", 0),
        "vehicles": {
            veh.name: {
                "batch_assignments": copy.copy(veh.order_control_batch_assignments),
                "state": veh.state,
                "v": veh.v,
                "x": veh.x,
                "link": veh.link,
            }
            for veh in vehicles
        },
        "links": {
            link.name: {"length": link.length, "u": link.u}
            for link in merge.inlinks.values()
        },
    }


def test_first_group_below_max_size():
    W = _build_network("max_size_first_below")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    a1 = _vehicles(["A1"], W)[0]
    b1 = _vehicles(["B1"], W, orig="orig2")[0]

    ordered = [(link1, [a1]), (link2, [b1])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result == [(link1, [a1]), (link2, [b1])]


def test_middle_group_reaches_max_size():
    W = _build_network("max_size_middle_equal")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    a1 = _vehicles(["A1"], W)[0]
    b1, b2 = _vehicles(["B1", "B2"], W, orig="orig2")
    c1 = _vehicles(["C1"], W, orig="orig3")[0]

    ordered = [(link1, [a1]), (link2, [b1, b2]), (link3, [c1])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result == [(link1, [a1]), (link2, [b1, b2])]
    assert link3 not in [inlink for inlink, _ in result]


def test_first_group_exceeds_max_size():
    W = _build_network("max_size_first_exceeds")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    a1, a2, a3 = _vehicles(["A1", "A2", "A3"], W)
    b1 = _vehicles(["B1"], W, orig="orig2")[0]

    ordered = [(link1, [a1, a2, a3]), (link2, [b1])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result == [(link1, [a1, a2])]


def test_middle_group_exceeds_max_size():
    W = _build_network("max_size_middle_exceeds")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    a1 = _vehicles(["A1"], W)[0]
    b1, b2, b3 = _vehicles(["B1", "B2", "B3"], W, orig="orig2")
    c1 = _vehicles(["C1"], W, orig="orig3")[0]

    ordered = [(link1, [a1]), (link2, [b1, b2, b3]), (link3, [c1])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result == [(link1, [a1]), (link2, [b1, b2])]


def test_all_groups_below_max_size():
    W = _build_network("max_size_all_below")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    a1 = _vehicles(["A1"], W)[0]
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    c1 = _vehicles(["C1"], W, orig="orig3")[0]

    ordered = [(link1, [a1]), (link2, [b1]), (link3, [c1])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result == ordered


def test_max_batch_size_one():
    W = _build_network("max_size_one")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    a1, a2 = _vehicles(["A1", "A2"], W)
    b1 = _vehicles(["B1"], W, orig="orig2")[0]

    ordered = [(link1, [a1, a2]), (link2, [b1])]
    result = merge.apply_order_control_batch_max_size(ordered, 1)
    assert result == [(link1, [a1])]
    assert result[0][1][0] is a1


def test_fifo_head_selection():
    W = _build_network("max_size_fifo")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1, a2, a3, a4 = _vehicles(["A1", "A2", "A3", "A4"], W)
    a4.x = 10.0
    a3.x = 20.0
    a2.x = 30.0
    a1.x = 40.0

    ordered = [(link1, [a1, a2, a3, a4])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result == [(link1, [a1, a2])]


def test_input_order_preserved():
    W = _build_network("max_size_order")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    a1 = _vehicles(["A1"], W)[0]
    c1 = _vehicles(["C1"], W, orig="orig3")[0]

    ordered = [(link2, [b1]), (link1, [a1]), (link3, [c1])]
    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert [inlink for inlink, _ in result] == [link2, link1, link3]


def test_max_batch_size_validation():
    W = _build_network("max_size_param_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    ordered = [(link1, [a1])]

    for valid in (1, 2, 10):
        assert merge.apply_order_control_batch_max_size(ordered, valid) == [(link1, [a1])]

    for invalid in (0, -1, 1.5, "2", True, False, None):
        _expect_value_error(
            lambda invalid=invalid: merge.apply_order_control_batch_max_size(
                ordered, invalid
            )
        )


def test_ordered_input_validation():
    W = _build_network("max_size_input_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1, a2 = _vehicles(["A1", "A2"], W)
    valid = [(link1, [a1])]

    for invalid in (None, {}, (), "bad", 1, []):
        _expect_value_error(
            lambda invalid=invalid: merge.apply_order_control_batch_max_size(
                invalid, 2
            )
        )

    _expect_value_error(
        lambda: merge.apply_order_control_batch_max_size([(link1,)], 2)
    )
    _expect_value_error(
        lambda: merge.apply_order_control_batch_max_size(
            [(link1, [a1], "extra")], 2
        )
    )
    _expect_value_error(
        lambda: merge.apply_order_control_batch_max_size([(link1, [])], 2)
    )
    _expect_value_error(
        lambda: merge.apply_order_control_batch_max_size([(link1, "bad")], 2)
    )
    _expect_value_error(
        lambda: merge.apply_order_control_batch_max_size([(out, [a1])], 2)
    )

    original_end_node = link1.end_node
    link1.end_node = W.get_node("dest")
    try:
        _expect_value_error(
            lambda: merge.apply_order_control_batch_max_size(valid, 2)
        )
    finally:
        link1.end_node = original_end_node

    _expect_value_error(
        lambda: merge.apply_order_control_batch_max_size(
            [(link1, [a1]), (link1, [a2])], 2
        )
    )

    merge.apply_order_control_batch_max_size(valid, 2)


def test_returns_new_lists():
    W = _build_network("max_size_new_lists")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1, a2, a3 = _vehicles(["A1", "A2", "A3"], W)
    input_list = [a1, a2, a3]
    ordered = [(link1, input_list)]

    result = merge.apply_order_control_batch_max_size(ordered, 2)
    assert result is not ordered
    assert result[0][1] is not input_list
    assert result[0][1] == [a1, a2]
    assert result[0][1][0] is a1
    assert result[0][1][1] is a2

    result[0][1].append("mutated")
    assert input_list == [a1, a2, a3]
    assert ordered[0][1] == [a1, a2, a3]


def test_no_side_effects():
    W = _build_network("max_size_no_side_effects")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    a1, a2 = _vehicles(["A1", "A2"], W)
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    ordered = [(link1, [a1, a2]), (link2, [b1])]
    vehicles = [a1, a2, b1]

    before = _snapshot_state(merge, ordered, vehicles)
    merge.apply_order_control_batch_max_size(ordered, 1)
    after = _snapshot_state(merge, ordered, vehicles)
    assert before == after


def main():
    test_first_group_below_max_size()
    test_middle_group_reaches_max_size()
    test_first_group_exceeds_max_size()
    test_middle_group_exceeds_max_size()
    test_all_groups_below_max_size()
    test_max_batch_size_one()
    test_fifo_head_selection()
    test_input_order_preserved()
    test_max_batch_size_validation()
    test_ordered_input_validation()
    test_returns_new_lists()
    test_no_side_effects()
    print("Order-control batch max-size application tests passed.")


if __name__ == "__main__":
    main()
