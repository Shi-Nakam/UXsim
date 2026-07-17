# Verify BATCH service-unit registration at order-control nodes.
#
# Run from the repository root:
#   python tests_order_control_batch_service_unit_registration.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy
from collections import deque

from uxsim import World


def _build_network(name="batch_service_registration", node_name="merge"):
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
        node_name,
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", node_name, length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", node_name, "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _make_vehicle(W, orig_name, name, dest="dest"):
    return W.addVehicle(orig_name, dest, 0, name=name)


def _vehicles(names, W, orig="orig1"):
    return [_make_vehicle(W, orig, name) for name in names]


def _place_on_inlink(veh, link, x=100.0):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    link.vehicles.append(veh)


def _snapshot_service_queue(queue):
    if not isinstance(queue, deque):
        return queue
    return [
        {
            "batch_id": unit["batch_id"],
            "inlink": unit["inlink"],
            "vehicles": list(unit["vehicles"]),
        }
        for unit in queue
    ]


def _snapshot_registration_state(node, selected_groups, vehicles):
    return {
        "selected_groups": [(inlink, list(veh_list)) for inlink, veh_list in selected_groups],
        "service_queue": _snapshot_service_queue(node.order_control_batch_service_queue),
        "next_id": node.order_control_batch_next_id,
        "incoming_vehicles": list(node.incoming_vehicles),
        "last_inlink": node.last_order_control_inlink,
        "last_entry_timestep": node.last_order_control_entry_timestep,
        "clearance_timesteps": node.order_control_clearance_timesteps,
        "W_T": getattr(node.W, "T", 0),
        "inlink_vehicles": {
            link.name: list(link.vehicles) for link in node.inlinks.values()
        },
        "links": {link.name: {"length": link.length, "u": link.u} for link in node.inlinks.values()},
        "vehicles": {
            veh.name: {
                "batch_assignments": copy.copy(veh.order_control_batch_assignments),
                "earliest": copy.copy(veh.order_control_earliest_arrival_timesteps),
                "arrival_times": copy.copy(veh.order_control_node_arrival_times),
                "tiebreakers": copy.copy(veh.order_control_node_arrival_tiebreakers),
                "state": veh.state,
                "v": veh.v,
                "x": veh.x,
                "link": veh.link,
            }
            for veh in vehicles
        },
    }


def _expect_value_error(callable_obj, message_substrings=()):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError as exc:
        message = str(exc)
        for substring in message_substrings:
            assert substring in message, f"expected {substring!r} in {message!r}"


class _FailOnNthAppendDeque(deque):
    def __init__(self, iterable=(), fail_on_append_n=2):
        super().__init__(iterable)
        self._append_count = 0
        self._fail_on_append_n = fail_on_append_n

    def append(self, item):
        self._append_count += 1
        if self._append_count >= self._fail_on_append_n:
            raise RuntimeError("simulated service queue append failure")
        super().append(item)


def test_basic_registration():
    W = _build_network("service_reg_basic")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    a1, a2 = _vehicles(["A1", "A2"], W)
    _place_on_inlink(b1, link2, x=180.0)
    _place_on_inlink(a1, link1, x=120.0)
    _place_on_inlink(a2, link1, x=60.0)

    selected = [(link2, [b1]), (link1, [a1, a2])]
    assert merge.order_control_batch_next_id == 0
    assert len(merge.order_control_batch_service_queue) == 0

    result = merge.register_order_control_batch_service_units(selected)
    assert result is None
    assert b1.order_control_batch_assignments["merge"] == 0
    assert a1.order_control_batch_assignments["merge"] == 1
    assert a2.order_control_batch_assignments["merge"] == 1
    assert merge.order_control_batch_next_id == 2

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == 2
    assert queue[0]["batch_id"] == 0
    assert queue[0]["inlink"] is link2
    assert queue[0]["vehicles"] == [b1]
    assert queue[1]["batch_id"] == 1
    assert queue[1]["inlink"] is link1
    assert queue[1]["vehicles"] == [a1, a2]


def test_multiple_registrations_on_same_node():
    W = _build_network("service_reg_multi")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    a1, a2 = _vehicles(["A1", "A2"], W)
    c1 = _vehicles(["C1"], W, orig="orig3")[0]
    for veh, link, x in ((b1, link2, 180.0), (a1, link1, 120.0), (a2, link1, 60.0), (c1, link3, 100.0)):
        _place_on_inlink(veh, link, x=x)

    first = [(link2, [b1]), (link1, [a1, a2])]
    merge.register_order_control_batch_service_units(first)

    second = [(link3, [c1])]
    merge.register_order_control_batch_service_units(second)

    assert c1.order_control_batch_assignments["merge"] == 2
    assert b1.order_control_batch_assignments["merge"] == 0
    assert a1.order_control_batch_assignments["merge"] == 1
    assert merge.order_control_batch_next_id == 3

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == 3
    assert queue[0]["batch_id"] == 0
    assert queue[0]["inlink"] is link2
    assert queue[0]["vehicles"] == [b1]
    assert queue[1]["batch_id"] == 1
    assert queue[1]["inlink"] is link1
    assert queue[1]["vehicles"] == [a1, a2]
    batch_ids = [unit["batch_id"] for unit in queue]
    assert batch_ids == [0, 1, 2]


def test_node_local_batch_id_independence():
    W_a = _build_network("service_reg_node_a", node_name="merge_a")
    W_b = _build_network("service_reg_node_b", node_name="merge_b")
    merge_a = W_a.get_node("merge_a")
    merge_b = W_b.get_node("merge_b")
    link_a = W_a.get_link("link1")
    link_b = W_b.get_link("link1")
    veh_a = _vehicles(["VA1"], W_a)[0]
    veh_b = _vehicles(["VB1"], W_b)[0]
    _place_on_inlink(veh_a, link_a)
    _place_on_inlink(veh_b, link_b)

    merge_a.register_order_control_batch_service_units([(link_a, [veh_a])])
    merge_b.register_order_control_batch_service_units([(link_b, [veh_b])])

    assert veh_a.order_control_batch_assignments["merge_a"] == 0
    assert veh_b.order_control_batch_assignments["merge_b"] == 0
    assert merge_a.order_control_batch_next_id == 1
    assert merge_b.order_control_batch_next_id == 1


def test_append_to_existing_service_queue():
    W = _build_network("service_reg_existing_queue")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    old_vehicle = _vehicles(["OLD"], W)[0]
    existing_unit = {
        "batch_id": 0,
        "inlink": link1,
        "vehicles": [old_vehicle],
    }
    merge.order_control_batch_service_queue.append(existing_unit)
    merge.order_control_batch_next_id = 1
    existing_snapshot = {
        "batch_id": existing_unit["batch_id"],
        "inlink": existing_unit["inlink"],
        "vehicles": list(existing_unit["vehicles"]),
    }

    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    _place_on_inlink(b1, link2)
    merge.register_order_control_batch_service_units([(link2, [b1])])

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == 2

    assert queue[0] is existing_unit
    assert queue[0]["batch_id"] == 0
    assert queue[0]["inlink"] is link1
    assert queue[0]["vehicles"] == [old_vehicle]

    assert queue[1]["batch_id"] == 1
    assert queue[1]["inlink"] is link2
    assert queue[1]["vehicles"] == [b1]

    assert b1.order_control_batch_assignments["merge"] == 1
    assert merge.order_control_batch_next_id == 2

    assert existing_unit["batch_id"] == existing_snapshot["batch_id"]
    assert existing_unit["inlink"] is existing_snapshot["inlink"]
    assert existing_unit["vehicles"] == existing_snapshot["vehicles"]


def test_same_batch_id_within_group_different_across_groups():
    W = _build_network("service_reg_batch_ids")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    a1, a2 = _vehicles(["A1", "A2"], W)
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    _place_on_inlink(a1, link1, x=120.0)
    _place_on_inlink(a2, link1, x=60.0)
    _place_on_inlink(b1, link2)

    merge.register_order_control_batch_service_units([(link2, [b1]), (link1, [a1, a2])])
    assert a1.order_control_batch_assignments["merge"] == 1
    assert a2.order_control_batch_assignments["merge"] == 1
    assert b1.order_control_batch_assignments["merge"] == 0
    assert a1.order_control_batch_assignments["merge"] != b1.order_control_batch_assignments["merge"]


def test_other_node_assignment_preserved():
    W = _build_network("service_reg_other_node")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    a1.order_control_batch_assignments["other_node"] = 7
    _place_on_inlink(a1, link1)

    merge.register_order_control_batch_service_units([(link1, [a1])])
    assert a1.order_control_batch_assignments["other_node"] == 7
    assert a1.order_control_batch_assignments["merge"] == 0


def test_already_assigned_at_current_node_raises():
    W = _build_network("service_reg_already_assigned")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    a1.order_control_batch_assignments["merge"] = 99
    _place_on_inlink(a1, link1)
    vehicles = [a1]
    before = _snapshot_registration_state(merge, [(link1, [a1])], vehicles)

    try:
        merge.register_order_control_batch_service_units([(link1, [a1])])
        assert False, "expected ValueError"
    except ValueError as exc:
        message = str(exc)
        assert "A1" in message
        assert "merge" in message
        assert "99" in message

    after = _snapshot_registration_state(merge, [(link1, [a1])], vehicles)
    assert before == after


def test_duplicate_vehicle_across_groups_raises():
    W = _build_network("service_reg_dup_vehicle")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    a1 = _vehicles(["A1"], W)[0]
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    _place_on_inlink(a1, link1)
    _place_on_inlink(b1, link2)
    vehicles = [a1, b1]
    before = _snapshot_registration_state(merge, [(link1, [a1]), (link2, [b1, a1])], vehicles)

    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units(
            [(link1, [a1]), (link2, [b1, a1])]
        ),
        message_substrings=("A1", "merge"),
    )
    assert before == _snapshot_registration_state(
        merge, [(link1, [a1]), (link2, [b1, a1])], vehicles
    )


def test_duplicate_inlink_raises():
    W = _build_network("service_reg_dup_inlink")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1, a2 = _vehicles(["A1", "A2"], W)
    _place_on_inlink(a1, link1, x=120.0)
    _place_on_inlink(a2, link1, x=60.0)
    vehicles = [a1, a2]
    before = _snapshot_registration_state(merge, [(link1, [a1]), (link1, [a2])], vehicles)

    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units(
            [(link1, [a1]), (link1, [a2])]
        ),
        message_substrings=("link1", "merge"),
    )
    assert before == _snapshot_registration_state(
        merge, [(link1, [a1]), (link1, [a2])], vehicles
    )


def test_input_format_validation():
    W = _build_network("service_reg_input_format")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _vehicles(["A1"], W)[0]
    _place_on_inlink(a1, link1)
    valid = [(link1, [a1])]

    for invalid in (None, {}, (), "bad", 1, []):
        _expect_value_error(
            lambda invalid=invalid: merge.register_order_control_batch_service_units(invalid),
            message_substrings=("merge",),
        )

    _expect_value_error(lambda: merge.register_order_control_batch_service_units([(link1,)]))
    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units([(link1, [a1], "extra")])
    )
    _expect_value_error(lambda: merge.register_order_control_batch_service_units([(link1, [])]))
    _expect_value_error(lambda: merge.register_order_control_batch_service_units([(link1, "bad")]))
    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units([(out, [a1])])
    )

    original_end_node = link1.end_node
    link1.end_node = W.get_node("dest")
    try:
        _expect_value_error(lambda: merge.register_order_control_batch_service_units(valid))
    finally:
        link1.end_node = original_end_node

    a1.link = link2
    _expect_value_error(lambda: merge.register_order_control_batch_service_units([(link1, [a1])]))
    a1.link = link1

    a1.state = "end"
    _expect_value_error(lambda: merge.register_order_control_batch_service_units([(link1, [a1])]))


def test_node_settings_validation():
    W = _build_network("service_reg_node_settings")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    _place_on_inlink(a1, link1)
    selected = [(link1, [a1])]
    vehicles = [a1]

    merge.order_control_eligible = False
    before = _snapshot_registration_state(merge, selected, vehicles)
    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units(selected),
        message_substrings=("merge",),
    )
    assert before == _snapshot_registration_state(merge, selected, vehicles)
    merge.order_control_eligible = True

    merge.order_control_type = "none"
    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units(selected),
        message_substrings=("merge", "none"),
    )
    merge.order_control_type = "batch"

    merge.order_control_type = "fcfs"
    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units(selected),
        message_substrings=("merge", "fcfs"),
    )
    merge.order_control_type = "batch"


def test_next_id_validation():
    W = _build_network("service_reg_next_id")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    _place_on_inlink(a1, link1)
    selected = [(link1, [a1])]
    vehicles = [a1]

    for invalid in (-1, 1.5, "0", True, None):
        merge.order_control_batch_next_id = invalid
        before = _snapshot_registration_state(merge, selected, vehicles)
        _expect_value_error(
            lambda: merge.register_order_control_batch_service_units(selected),
            message_substrings=("merge", "order_control_batch_next_id"),
        )
        assert before == _snapshot_registration_state(merge, selected, vehicles)

    merge.order_control_batch_next_id = 0
    merge.register_order_control_batch_service_units(selected)


def test_service_queue_type_validation():
    W = _build_network("service_reg_queue_type")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    _place_on_inlink(a1, link1)
    selected = [(link1, [a1])]
    vehicles = [a1]

    for invalid in ([], None):
        merge.order_control_batch_service_queue = invalid
        before = _snapshot_registration_state(merge, selected, vehicles)
        _expect_value_error(
            lambda: merge.register_order_control_batch_service_units(selected),
            message_substrings=("merge", "deque"),
        )
        assert before == _snapshot_registration_state(merge, selected, vehicles)

    merge.order_control_batch_service_queue = deque()


def test_service_unit_vehicle_list_is_new_list():
    W = _build_network("service_reg_new_lists")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1, a2 = _vehicles(["A1", "A2"], W)
    _place_on_inlink(a1, link1, x=120.0)
    _place_on_inlink(a2, link1, x=60.0)
    input_list = [a1, a2]
    selected = [(link1, input_list)]

    merge.register_order_control_batch_service_units(selected)
    queue_vehicles = merge.order_control_batch_service_queue[-1]["vehicles"]
    assert queue_vehicles is not input_list
    assert queue_vehicles == [a1, a2]
    assert queue_vehicles[0] is a1
    assert queue_vehicles[1] is a2

    queue_vehicles.append("mutated")
    assert input_list == [a1, a2]
    assert selected[0][1] == [a1, a2]


def test_input_lists_unchanged_after_registration():
    W = _build_network("service_reg_input_unchanged")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    a1, a2 = _vehicles(["A1", "A2"], W)
    _place_on_inlink(b1, link2)
    _place_on_inlink(a1, link1, x=120.0)
    _place_on_inlink(a2, link1, x=60.0)
    group1 = [b1]
    group2 = [a1, a2]
    selected = [(link2, group1), (link1, group2)]
    before_structure = [(inlink, list(vehicles)) for inlink, vehicles in selected]

    merge.register_order_control_batch_service_units(selected)

    assert [(inlink, list(vehicles)) for inlink, vehicles in selected] == before_structure
    assert selected[0][1] is group1
    assert selected[1][1] is group2


def test_pre_change_validation_blocks_partial_registration():
    W = _build_network("service_reg_pre_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    a1 = _vehicles(["A1"], W)[0]
    _place_on_inlink(b1, link2)
    _place_on_inlink(a1, link1)
    a1.order_control_batch_assignments["merge"] = 5
    vehicles = [b1, a1]
    before = _snapshot_registration_state(merge, [(link2, [b1]), (link1, [a1])], vehicles)

    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units(
            [(link2, [b1]), (link1, [a1])]
        )
    )
    after = _snapshot_registration_state(merge, [(link2, [b1]), (link1, [a1])], vehicles)
    assert before == after
    assert "merge" not in b1.order_control_batch_assignments


def test_rollback_on_mid_update_exception():
    W = _build_network("service_reg_rollback")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    b1 = _vehicles(["B1"], W, orig="orig2")[0]
    a1, a2 = _vehicles(["A1", "A2"], W)
    _place_on_inlink(b1, link2)
    _place_on_inlink(a1, link1, x=120.0)
    _place_on_inlink(a2, link1, x=60.0)
    existing_unit = {
        "batch_id": 99,
        "inlink": link1,
        "vehicles": [_vehicles(["OLD"], W)[0]],
    }
    merge.order_control_batch_service_queue = _FailOnNthAppendDeque(
        [existing_unit], fail_on_append_n=2
    )
    merge.order_control_batch_next_id = 0
    vehicles = [b1, a1, a2]
    before = _snapshot_registration_state(
        merge, [(link2, [b1]), (link1, [a1, a2])], vehicles
    )

    try:
        merge.register_order_control_batch_service_units(
            [(link2, [b1]), (link1, [a1, a2])]
        )
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "simulated service queue append failure" in str(exc)

    after = _snapshot_registration_state(
        merge, [(link2, [b1]), (link1, [a1, a2])], vehicles
    )
    assert after == before
    assert "merge" not in b1.order_control_batch_assignments
    assert "merge" not in a1.order_control_batch_assignments
    assert list(merge.order_control_batch_service_queue) == [existing_unit]


def test_side_effect_scope():
    W = _build_network("service_reg_side_effects")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    a1 = _vehicles(["A1"], W)[0]
    a1.order_control_earliest_arrival_timesteps["merge"] = 10
    a1.order_control_node_arrival_times["merge"] = 5.0
    a1.order_control_node_arrival_tiebreakers["merge"] = 0.1
    _place_on_inlink(a1, link1, x=100.0)
    selected = [(link1, [a1])]
    vehicles = [a1]
    before = _snapshot_registration_state(merge, selected, vehicles)

    merge.register_order_control_batch_service_units(selected)

    after_assignments = copy.copy(a1.order_control_batch_assignments)
    assert after_assignments["merge"] == 0
    del after_assignments["merge"]
    expected = copy.copy(before["vehicles"]["A1"]["batch_assignments"])
    assert after_assignments == expected

    assert a1.order_control_earliest_arrival_timesteps == before["vehicles"]["A1"]["earliest"]
    assert a1.order_control_node_arrival_times == before["vehicles"]["A1"]["arrival_times"]
    assert a1.order_control_node_arrival_tiebreakers == before["vehicles"]["A1"]["tiebreakers"]
    assert a1.state == before["vehicles"]["A1"]["state"]
    assert a1.v == before["vehicles"]["A1"]["v"]
    assert a1.x == before["vehicles"]["A1"]["x"]
    assert a1.link is before["vehicles"]["A1"]["link"]
    assert list(merge.incoming_vehicles) == before["incoming_vehicles"]
    assert merge.last_order_control_inlink == before["last_inlink"]
    assert merge.last_order_control_entry_timestep == before["last_entry_timestep"]
    assert merge.order_control_clearance_timesteps == before["clearance_timesteps"]
    assert getattr(merge.W, "T", 0) == before["W_T"]
    assert {
        link.name: list(link.vehicles) for link in merge.inlinks.values()
    } == before["inlink_vehicles"]
    assert {
        link.name: {"length": link.length, "u": link.u} for link in merge.inlinks.values()
    } == before["links"]


def main():
    test_basic_registration()
    test_multiple_registrations_on_same_node()
    test_node_local_batch_id_independence()
    test_append_to_existing_service_queue()
    test_same_batch_id_within_group_different_across_groups()
    test_other_node_assignment_preserved()
    test_already_assigned_at_current_node_raises()
    test_duplicate_vehicle_across_groups_raises()
    test_duplicate_inlink_raises()
    test_input_format_validation()
    test_node_settings_validation()
    test_next_id_validation()
    test_service_queue_type_validation()
    test_service_unit_vehicle_list_is_new_list()
    test_input_lists_unchanged_after_registration()
    test_pre_change_validation_blocks_partial_registration()
    test_rollback_on_mid_update_exception()
    test_side_effect_scope()
    print("Order-control batch service-unit registration tests passed.")


if __name__ == "__main__":
    main()
