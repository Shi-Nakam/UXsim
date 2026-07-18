# Verify integrated BATCH formation through formal registration.
#
# Run from the repository root:
#   python tests_order_control_batch_formation_integration.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy
from collections import deque
from unittest.mock import patch

from uxsim import World


def _build_network(name="batch_formation_integration"):
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
    W.addNode("other_node", 1, 3)
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _make_vehicle(W, orig_name, name):
    return W.addVehicle(orig_name, "dest", 0, name=name)


def _setup_arrived_vehicle(
    merge,
    veh,
    link,
    out_link,
    earliest,
    arrival_time,
    tiebreaker,
    x,
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _snapshot_state(merge, vehicles):
    return {
        "incoming_vehicles": list(merge.incoming_vehicles),
        "service_queue": [
            {
                "batch_id": unit["batch_id"],
                "inlink": unit["inlink"],
                "vehicles": list(unit["vehicles"]),
            }
            for unit in merge.order_control_batch_service_queue
        ],
        "next_id": merge.order_control_batch_next_id,
        "last_inlink": merge.last_order_control_inlink,
        "last_entry_timestep": merge.last_order_control_entry_timestep,
        "clearance_timesteps": merge.order_control_clearance_timesteps,
        "W_T": getattr(merge.W, "T", 0),
        "inlink_vehicles": {
            link.name: list(link.vehicles) for link in merge.inlinks.values()
        },
        "links": {
            link.name: {"length": link.length, "u": link.u}
            for link in merge.inlinks.values()
        },
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


def test_no_trigger_candidate():
    W = _build_network("integration_no_trigger")
    merge = W.get_node("merge")
    vehicles = []
    before = _snapshot_state(merge, vehicles)

    result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2)

    assert result == "no_trigger_candidate"
    assert before == _snapshot_state(merge, vehicles)


def test_level_0_basic_integration():
    W = _build_network("integration_level_0")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "A1")
    follow = _make_vehicle(W, "orig1", "A2")
    other = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_arrived_vehicle(merge, follow, link1, out, 12, 11.0, 0.2, 60.0)
    _setup_arrived_vehicle(merge, other, link2, out, 10, 15.0, 0.3, 100.0)

    expected_order = merge.get_ordered_order_control_batch_candidates_by_inlink(
        merge.get_order_control_batch_candidates_by_inlink(
            merge.estimate_order_control_batch_t_trigger_level_0(trigger)
        ),
        trigger,
    )

    result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    assert result == "batch_formed"

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == len(expected_order)
    for idx, (expected_inlink, expected_vehicles) in enumerate(expected_order):
        unit = queue[idx]
        assert unit["batch_id"] == idx
        assert unit["inlink"] is expected_inlink
        assert unit["vehicles"] == expected_vehicles
        batch_id = unit["batch_id"]
        for veh in unit["vehicles"]:
            assert veh.order_control_batch_assignments["merge"] == batch_id

    assert trigger.order_control_batch_assignments["merge"] == 0
    assert follow.order_control_batch_assignments["merge"] == 0
    assert other.order_control_batch_assignments["merge"] == 1
    assert merge.order_control_batch_next_id == 2


def test_level_1_basic_integration():
    W = _build_network("integration_level_1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig2", "B_trigger")
    included = _make_vehicle(W, "orig2", "B_included")
    _setup_arrived_vehicle(merge, trigger, link2, out, 10, 10.0, 0.1, 120.0)
    _setup_arrived_vehicle(merge, included, link2, out, 12, 11.0, 0.2, 60.0)

    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 1

    t_trigger = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    expected_selected = merge.apply_order_control_batch_max_size(
        merge.get_ordered_order_control_batch_candidates_by_inlink(
            merge.get_order_control_batch_candidates_by_inlink(t_trigger),
            trigger,
        ),
        5,
    )

    result = merge.form_order_control_batch(t_trigger_level=1, max_batch_size=5)
    assert result == "batch_formed"

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == len(expected_selected)
    for idx, (expected_inlink, expected_vehicles) in enumerate(expected_selected):
        assert queue[idx]["inlink"] is expected_inlink
        assert queue[idx]["vehicles"] == expected_vehicles
    assert trigger.order_control_batch_assignments["merge"] == 0
    assert included.order_control_batch_assignments["merge"] == 0
    assert merge.order_control_batch_next_id == 1


def test_level_2_planned_but_not_implemented():
    W = _build_network("integration_level_2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _snapshot_state(merge, [trigger])

    _expect_value_error(
        lambda: merge.form_order_control_batch(t_trigger_level=2, max_batch_size=2),
        message_substrings=(
            "merge",
            "t_trigger_level=2",
            "Level 2 is planned",
            "virtual-service estimation is not yet implemented",
        ),
    )
    assert before == _snapshot_state(merge, [trigger])


def test_invalid_t_trigger_level_values():
    W = _build_network("integration_invalid_level")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _snapshot_state(merge, [trigger])

    for invalid in (-1, 3, 1.5, "1", True, False, None):
        _expect_value_error(
            lambda invalid=invalid: merge.form_order_control_batch(
                t_trigger_level=invalid,
                max_batch_size=2,
            ),
            message_substrings=("merge",),
        )
        assert before == _snapshot_state(merge, [trigger])


def test_max_batch_size_reflected():
    W = _build_network("integration_max_size")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "V1")
    second = _make_vehicle(W, "orig1", "V2")
    third = _make_vehicle(W, "orig1", "V3")
    _setup_arrived_vehicle(merge, trigger, link1, out, 10, 10.0, 0.1, 180.0)
    _setup_arrived_vehicle(merge, second, link1, out, 11, 11.0, 0.2, 120.0)
    _setup_arrived_vehicle(merge, third, link1, out, 12, 12.0, 0.3, 60.0)

    result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2)
    assert result == "batch_formed"

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == 1
    assert queue[0]["vehicles"] == [trigger, second]
    assert "merge" not in third.order_control_batch_assignments


def test_multiple_formations_on_same_node():
    W = _build_network("integration_multiple")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")

    first_trigger = _make_vehicle(W, "orig1", "A1")
    first_other = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, first_trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_arrived_vehicle(merge, first_other, link2, out, 10, 15.0, 0.2, 100.0)

    first_result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    assert first_result == "batch_formed"
    first_queue = list(merge.order_control_batch_service_queue)
    first_assignments = {
        veh.name: veh.order_control_batch_assignments["merge"]
        for veh in (first_trigger, first_other)
    }

    second_trigger = _make_vehicle(W, "orig3", "C1")
    _setup_arrived_vehicle(merge, second_trigger, link3, out, 10, 20.0, 0.3, 100.0)

    trigger_candidates = merge.get_order_control_batch_trigger_candidates()
    assert first_trigger not in trigger_candidates
    assert first_other not in trigger_candidates
    assert trigger_candidates[0] is second_trigger

    second_result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    assert second_result == "batch_formed"

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) == 3
    assert queue[0] is first_queue[0]
    assert queue[1] is first_queue[1]
    assert queue[2]["batch_id"] == 2
    assert queue[2]["vehicles"] == [second_trigger]
    assert first_trigger.order_control_batch_assignments["merge"] == first_assignments["A1"]
    assert first_other.order_control_batch_assignments["merge"] == first_assignments["B1"]
    assert second_trigger.order_control_batch_assignments["merge"] == 2
    assert merge.order_control_batch_next_id == 3


def test_empty_candidates_by_inlink_internal_inconsistency():
    W = _build_network("integration_empty_candidates")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _snapshot_state(merge, [trigger])

    with patch.object(
        merge,
        "get_order_control_batch_candidates_by_inlink",
        return_value={},
    ) as mocked_extract:
        _expect_value_error(
            lambda: merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2),
            message_substrings=(
                "merge",
                "A1",
                "empty dict",
            ),
        )
        assert mocked_extract.called

    assert before == _snapshot_state(merge, [trigger])


def test_empty_selected_groups_internal_inconsistency():
    W = _build_network("integration_empty_selected")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _snapshot_state(merge, [trigger])

    with patch.object(
        merge,
        "apply_order_control_batch_max_size",
        return_value=[],
    ) as mocked_apply:
        _expect_value_error(
            lambda: merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2),
            message_substrings=(
                "merge",
                "A1",
                "max_batch_size=2",
                "empty list",
            ),
        )
        assert mocked_apply.called

    assert before == _snapshot_state(merge, [trigger])


def test_upstream_error_does_not_mutate_state():
    W = _build_network("integration_upstream_error")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "A1")
    missing_earliest = _make_vehicle(W, "orig1", "A2")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    missing_earliest.link = link1
    missing_earliest.state = "run"
    missing_earliest.x = 60.0
    missing_earliest.v = 20.0
    link1.vehicles.append(missing_earliest)

    vehicles = [trigger, missing_earliest]
    before = _snapshot_state(merge, vehicles)

    try:
        merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "A2" in str(exc)
        assert "earliest arrival timestep" in str(exc)

    assert before == _snapshot_state(merge, vehicles)


def test_registration_rollback_through_integration():
    W = _build_network("integration_rollback")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "A1")
    other = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_arrived_vehicle(merge, other, link2, out, 10, 15.0, 0.2, 100.0)

    existing_unit = {
        "batch_id": 0,
        "inlink": link1,
        "vehicles": [_make_vehicle(W, "orig1", "OLD")],
    }
    merge.order_control_batch_service_queue = _FailOnNthAppendDeque(
        [existing_unit],
        fail_on_append_n=2,
    )
    merge.order_control_batch_next_id = 1
    vehicles = [trigger, other]
    before = _snapshot_state(merge, vehicles)

    try:
        merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "simulated service queue append failure" in str(exc)

    after = _snapshot_state(merge, vehicles)
    assert after == before
    assert "merge" not in trigger.order_control_batch_assignments
    assert "merge" not in other.order_control_batch_assignments
    assert list(merge.order_control_batch_service_queue) == [existing_unit]


def test_node_settings_validation():
    W = _build_network("integration_node_settings")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _snapshot_state(merge, [trigger])

    merge.order_control_eligible = False
    _expect_value_error(
        lambda: merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2),
        message_substrings=("merge", "not order-control eligible"),
    )
    assert before == _snapshot_state(merge, [trigger])

    merge.order_control_eligible = True
    merge.order_control_type = "none"
    _expect_value_error(
        lambda: merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2),
        message_substrings=("merge", "order_control_type='none'"),
    )
    assert before == _snapshot_state(merge, [trigger])

    merge.order_control_type = "fcfs"
    _expect_value_error(
        lambda: merge.form_order_control_batch(t_trigger_level=0, max_batch_size=2),
        message_substrings=("merge", "order_control_type='fcfs'"),
    )
    assert before == _snapshot_state(merge, [trigger])


def test_uses_existing_helper_methods():
    W = _build_network("integration_helper_calls")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "A1")
    other = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_arrived_vehicle(merge, other, link2, out, 10, 15.0, 0.2, 100.0)

    call_order = []
    method_names = [
        "get_order_control_batch_trigger_candidates",
        "estimate_order_control_batch_t_trigger_level_0",
        "get_order_control_batch_candidates_by_inlink",
        "get_ordered_order_control_batch_candidates_by_inlink",
        "apply_order_control_batch_max_size",
        "register_order_control_batch_service_units",
    ]
    originals = {name: getattr(merge, name) for name in method_names}

    def _make_wrapper(name):
        original = originals[name]

        def wrapper(*args, **kwargs):
            call_order.append(name)
            return original(*args, **kwargs)

        return wrapper

    for name in method_names:
        setattr(merge, name, _make_wrapper(name))

    try:
        result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    finally:
        for name in method_names:
            setattr(merge, name, originals[name])

    assert result == "batch_formed"
    assert call_order == [
        "get_order_control_batch_trigger_candidates",
        "estimate_order_control_batch_t_trigger_level_0",
        "get_order_control_batch_candidates_by_inlink",
        "get_ordered_order_control_batch_candidates_by_inlink",
        "apply_order_control_batch_max_size",
        "register_order_control_batch_service_units",
    ]


def test_side_effect_scope():
    W = _build_network("integration_side_effects")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "A1")
    other = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_arrived_vehicle(merge, other, link2, out, 10, 15.0, 0.2, 100.0)
    vehicles = [trigger, other]
    before = _snapshot_state(merge, vehicles)

    result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    assert result == "batch_formed"

    after_assignments = {
        name: copy.copy(data["batch_assignments"])
        for name, data in before["vehicles"].items()
    }
    after_assignments["A1"]["merge"] = 0
    after_assignments["B1"]["merge"] = 1
    assert {
        veh.name: copy.copy(veh.order_control_batch_assignments) for veh in vehicles
    } == after_assignments

    assert list(merge.incoming_vehicles) == before["incoming_vehicles"]
    assert merge.last_order_control_inlink == before["last_inlink"]
    assert merge.last_order_control_entry_timestep == before["last_entry_timestep"]
    assert merge.order_control_clearance_timesteps == before["clearance_timesteps"]
    assert getattr(merge.W, "T", 0) == before["W_T"]
    assert {
        link.name: list(link.vehicles) for link in merge.inlinks.values()
    } == before["inlink_vehicles"]
    assert {
        link.name: {"length": link.length, "u": link.u}
        for link in merge.inlinks.values()
    } == before["links"]
    for veh in vehicles:
        assert veh.order_control_earliest_arrival_timesteps == before["vehicles"][veh.name]["earliest"]
        assert veh.order_control_node_arrival_times == before["vehicles"][veh.name]["arrival_times"]
        assert veh.order_control_node_arrival_tiebreakers == before["vehicles"][veh.name]["tiebreakers"]
        assert veh.state == before["vehicles"][veh.name]["state"]
        assert veh.v == before["vehicles"][veh.name]["v"]
        assert veh.x == before["vehicles"][veh.name]["x"]
        assert veh.link is before["vehicles"][veh.name]["link"]


def main():
    test_no_trigger_candidate()
    test_level_0_basic_integration()
    test_level_1_basic_integration()
    test_level_2_planned_but_not_implemented()
    test_invalid_t_trigger_level_values()
    test_max_batch_size_reflected()
    test_multiple_formations_on_same_node()
    test_empty_candidates_by_inlink_internal_inconsistency()
    test_empty_selected_groups_internal_inconsistency()
    test_upstream_error_does_not_mutate_state()
    test_registration_rollback_through_integration()
    test_node_settings_validation()
    test_uses_existing_helper_methods()
    test_side_effect_scope()
    print("Order-control batch formation integration tests passed.")


if __name__ == "__main__":
    main()
