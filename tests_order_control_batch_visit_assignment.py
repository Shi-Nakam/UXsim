# Verify Phase 4-6S Step 1 BATCH current-visit assignment control.
#
# - service unit vehicles and visit_ids correspond by the same index
# - legacy order_control_batch_assignments is a compatibility first-visit record only
# - full assignment visit history, trip-end handling, and stale-unit auto-removal are
#   out of scope for this step
#
# Run from the repository root:
#   python tests_order_control_batch_visit_assignment.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy
from collections import deque

import pytest

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_merge_world(name="batch_visit_assignment"):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addNode("other", 3, 1, order_control_eligible=False, order_control_type="none")
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("plain", "merge", "other", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _make_vehicle(W, name, orig="orig1", dest="dest"):
    return W.addVehicle(orig, dest, 0, name=name)


def _set_current_visit(
    veh,
    merge,
    link,
    *,
    visit_id,
    earliest=10,
    arrival_time=None,
    arrival_tiebreaker=None,
    batch_assignment=None,
):
    veh.order_control_visit_id = visit_id
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": merge,
        "inlink": link,
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
        "arrival_tiebreaker": arrival_tiebreaker,
        "batch_assignment": batch_assignment,
    }


def _place_arrived(merge, veh, link, out, *, visit_id, earliest=10, arrival_time=10.0, tiebreaker=0.1, x=200.0):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.route_next_link = out
    _set_current_visit(
        veh,
        merge,
        link,
        visit_id=visit_id,
        earliest=earliest,
        arrival_time=arrival_time,
        arrival_tiebreaker=tiebreaker,
    )
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _place_on_inlink(veh, merge, link, *, visit_id, earliest=10, x=100.0, batch_assignment=None):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    _set_current_visit(
        veh,
        merge,
        link,
        visit_id=visit_id,
        earliest=earliest,
        arrival_time=None,
        arrival_tiebreaker=None,
        batch_assignment=batch_assignment,
    )
    link.vehicles.append(veh)


def _boost_transfer_capacity(merge, *links):
    for link in links:
        link.capacity_in_remain = 1e6
        link.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6


def _expect_value_error(callable_obj, message_substrings=()):
    with pytest.raises(ValueError) as exc_info:
        callable_obj()
    message = str(exc_info.value)
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


def _snapshot_vehicle_state(veh):
    visit = veh.order_control_current_visit
    return {
        "link": veh.link,
        "x": veh.x,
        "move_remain": veh.move_remain,
        "visit_id": None if visit is None else visit["visit_id"],
        "batch_assignment": None if visit is None else visit["batch_assignment"],
        "node": None if visit is None else visit["node"],
        "inlink": None if visit is None else visit["inlink"],
        "legacy": copy.copy(veh.order_control_batch_assignments),
    }


def _snapshot_node_transfer_state(merge):
    return {
        "incoming": list(merge.incoming_vehicles),
        "last_inlink": merge.last_order_control_inlink,
        "last_entry": merge.last_order_control_entry_timestep,
        "inlink_vehicles": {
            link.name: list(link.vehicles) for link in merge.inlinks.values()
        },
        "outlink_vehicles": {
            link.name: list(link.vehicles) for link in merge.outlinks.values()
        },
        "cum_in": {link.name: link.cum_arrival[-1] for link in merge.inlinks.values()},
        "cum_out": {link.name: link.cum_departure[-1] for link in merge.inlinks.values()},
    }


def test_a1_unassigned_get_returns_none():
    W = _build_merge_world("accessor_a1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _set_current_visit(veh, merge, link1, visit_id=1)
    assert veh.get_order_control_batch_assignment(merge) is None
    assert veh.has_order_control_batch_assignment(merge) is False


def test_a2_assigned_get_returns_batch_id():
    W = _build_merge_world("accessor_a2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _set_current_visit(veh, merge, link1, visit_id=1, batch_assignment=12)
    assert veh.get_order_control_batch_assignment(merge) == 12
    assert veh.has_order_control_batch_assignment(merge) is True


def test_a3_missing_current_visit_raises():
    W = _build_merge_world("accessor_a3")
    merge = W.get_node("merge")
    veh = _make_vehicle(W, "A1")
    veh.order_control_current_visit = None
    _expect_value_error(lambda: veh.get_order_control_batch_assignment(merge), ["None"])
    _expect_value_error(lambda: veh.has_order_control_batch_assignment(merge), ["None"])


def test_a4_node_mismatch_raises():
    W = _build_merge_world("accessor_a4")
    merge = W.get_node("merge")
    other = W.get_node("other")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _set_current_visit(veh, other, link1, visit_id=1)
    _expect_value_error(lambda: veh.get_order_control_batch_assignment(merge), ["does not match"])


def test_a5_invalid_assignment_type_raises():
    W = _build_merge_world("accessor_a5")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    for invalid in (True, -1, 1.5, "1"):
        _set_current_visit(veh, merge, link1, visit_id=1, batch_assignment=invalid)
        _expect_value_error(lambda: veh.get_order_control_batch_assignment(merge), ["invalid batch_assignment"])


def test_b1_assign_to_current_visit():
    W = _build_merge_world("assign_b1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _set_current_visit(veh, merge, link1, visit_id=1)
    veh.assign_order_control_batch_to_current_visit(merge, 8)
    assert veh.order_control_current_visit["batch_assignment"] == 8
    assert veh.order_control_batch_assignments == {}


def test_b2_double_assign_raises():
    W = _build_merge_world("assign_b2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _set_current_visit(veh, merge, link1, visit_id=1, batch_assignment=8)
    _expect_value_error(
        lambda: veh.assign_order_control_batch_to_current_visit(merge, 9),
        ["batch_assignment=8", "batch_id=9"],
    )
    assert veh.order_control_current_visit["batch_assignment"] == 8


def test_b3_invalid_batch_id_raises():
    W = _build_merge_world("assign_b3")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _set_current_visit(veh, merge, link1, visit_id=1)
    for invalid in (True, -1, 1.5, "1"):
        _expect_value_error(
            lambda: veh.assign_order_control_batch_to_current_visit(merge, invalid),
            ["invalid batch_id"],
        )
        assert veh.order_control_current_visit["batch_assignment"] is None


def test_c1_revisit_trigger_with_legacy_assignment():
    W = _build_merge_world("cand_c1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(
        merge,
        veh,
        link1,
        out,
        visit_id=2,
        arrival_time=10.0,
        tiebreaker=0.1,
    )
    veh.order_control_batch_assignments["merge"] = 10
    candidates = merge.get_order_control_batch_trigger_candidates()
    assert veh in candidates


def test_c2_assigned_current_visit_excluded_from_trigger():
    W = _build_merge_world("cand_c2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(
        merge,
        veh,
        link1,
        out,
        visit_id=2,
        arrival_time=10.0,
        tiebreaker=0.1,
    )
    veh.order_control_current_visit["batch_assignment"] = 25
    candidates = merge.get_order_control_batch_trigger_candidates()
    assert veh not in candidates


def test_c3_assigned_trigger_direct_to_t_trigger_raises():
    W = _build_merge_world("cand_c3")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(
        merge,
        veh,
        link1,
        out,
        visit_id=2,
        arrival_time=10.0,
        tiebreaker=0.1,
    )
    veh.order_control_current_visit["batch_assignment"] = 25
    _expect_value_error(
        lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh),
        ["batch_assignment=25"],
    )


def test_d1_legacy_assignment_does_not_affect_prefix():
    W = _build_merge_world("prefix_d1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh_a = _make_vehicle(W, "A")
    veh_b = _make_vehicle(W, "B")
    _place_on_inlink(veh_a, merge, link1, visit_id=1, x=180.0)
    _place_on_inlink(veh_b, merge, link1, visit_id=2, x=120.0)
    veh_b.order_control_batch_assignments["merge"] = 99
    result = merge.get_order_control_batch_candidates_by_inlink(t_trigger=100)
    assert result[link1] == [veh_a, veh_b]


def test_d2_current_visit_prefix_violation_raises():
    W = _build_merge_world("prefix_d2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh_a = _make_vehicle(W, "A")
    veh_b = _make_vehicle(W, "B")
    veh_c = _make_vehicle(W, "C")
    _place_on_inlink(veh_a, merge, link1, visit_id=1, x=180.0, batch_assignment=1)
    _place_on_inlink(veh_b, merge, link1, visit_id=2, x=120.0)
    _place_on_inlink(veh_c, merge, link1, visit_id=3, x=60.0, batch_assignment=2)
    _expect_value_error(
        lambda: merge.get_order_control_batch_candidates_by_inlink(t_trigger=100),
        ["prefix violation", "C"],
    )


def test_e1_first_register_writes_current_visit_and_visit_ids():
    W = _build_merge_world("reg_e1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _place_on_inlink(veh, merge, link1, visit_id=4)
    merge.register_order_control_batch_service_units([(link1, [veh])])
    unit = merge.order_control_batch_service_queue[0]
    assert veh.order_control_current_visit["batch_assignment"] == 0
    assert unit["batch_id"] == 0
    assert unit["visit_ids"] == [4]
    assert len(unit["vehicles"]) == len(unit["visit_ids"])
    assert veh.order_control_batch_assignments["merge"] == 0


def test_e2_revisit_register_preserves_legacy_first_value():
    W = _build_merge_world("reg_e2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    veh.order_control_batch_assignments["merge"] = 10
    _place_on_inlink(veh, merge, link1, visit_id=2)
    merge.register_order_control_batch_service_units([(link1, [veh])])
    assert veh.order_control_batch_assignments["merge"] == 10
    assert veh.order_control_current_visit["batch_assignment"] == 0
    assert merge.order_control_batch_service_queue[0]["visit_ids"] == [2]


def test_e3_multiple_vehicle_visit_ids():
    W = _build_merge_world("reg_e3")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh_a = _make_vehicle(W, "A")
    veh_b = _make_vehicle(W, "B", orig="orig2")
    _place_on_inlink(veh_a, merge, link1, visit_id=3, x=120.0)
    _place_on_inlink(veh_b, merge, link1, visit_id=7, x=60.0)
    merge.register_order_control_batch_service_units([(link1, [veh_a, veh_b])])
    unit = merge.order_control_batch_service_queue[0]
    assert unit["vehicles"] == [veh_a, veh_b]
    assert unit["visit_ids"] == [3, 7]


def test_e4_register_rejects_existing_current_assignment():
    W = _build_merge_world("reg_e4")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = _make_vehicle(W, "A1")
    _place_on_inlink(veh, merge, link1, visit_id=1, batch_assignment=5)
    before_queue = list(merge.order_control_batch_service_queue)
    before_next = merge.order_control_batch_next_id
    _expect_value_error(
        lambda: merge.register_order_control_batch_service_units([(link1, [veh])]),
        ["batch_assignment=5"],
    )
    assert veh.order_control_current_visit["batch_assignment"] == 5
    assert list(merge.order_control_batch_service_queue) == before_queue
    assert merge.order_control_batch_next_id == before_next


def test_e5_register_rollback_restores_state():
    W = _build_merge_world("reg_e5")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh_a = _make_vehicle(W, "A")
    veh_b = _make_vehicle(W, "B", orig="orig2")
    veh_revisit = _make_vehicle(W, "R", orig="orig2")
    _place_on_inlink(veh_a, merge, link2, visit_id=1, x=180.0)
    _place_on_inlink(veh_b, merge, link1, visit_id=2, x=120.0)
    _place_on_inlink(veh_revisit, merge, link1, visit_id=5, x=60.0)
    veh_revisit.order_control_batch_assignments["merge"] = 77
    merge.order_control_batch_service_queue = _FailOnNthAppendDeque([], fail_on_append_n=2)
    before = {
        "a_assignment": veh_a.order_control_current_visit["batch_assignment"],
        "b_assignment": veh_b.order_control_current_visit["batch_assignment"],
        "revisit_assignment": veh_revisit.order_control_current_visit["batch_assignment"],
        "revisit_legacy": copy.copy(veh_revisit.order_control_batch_assignments),
        "queue": list(merge.order_control_batch_service_queue),
        "next_id": merge.order_control_batch_next_id,
    }
    with pytest.raises(RuntimeError):
        merge.register_order_control_batch_service_units(
            [(link2, [veh_a]), (link1, [veh_b, veh_revisit])]
        )
    assert veh_a.order_control_current_visit["batch_assignment"] == before["a_assignment"]
    assert veh_b.order_control_current_visit["batch_assignment"] == before["b_assignment"]
    assert veh_revisit.order_control_current_visit["batch_assignment"] == before["revisit_assignment"]
    assert veh_revisit.order_control_batch_assignments == before["revisit_legacy"]
    assert "merge" not in veh_a.order_control_batch_assignments
    assert "merge" not in veh_b.order_control_batch_assignments
    assert list(merge.order_control_batch_service_queue) == before["queue"]
    assert merge.order_control_batch_next_id == before["next_id"]


def _make_registered_service_unit(merge, veh, link, out, *, visit_id, batch_id=0, move_remain=5.0):
    _place_arrived(
        merge,
        veh,
        link,
        out,
        visit_id=visit_id,
        arrival_time=10.0,
        tiebreaker=0.1,
        x=200.0,
    )
    veh.move_remain = move_remain
    merge.register_order_control_batch_service_units([(link, [veh])])
    return merge.order_control_batch_service_queue[0]


def test_f1_normal_service_transfer():
    W = _build_merge_world("serve_f1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    unit = _make_registered_service_unit(merge, veh, link1, out, visit_id=3)
    _boost_transfer_capacity(merge, link1, out)
    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert veh.link is out
    assert len(merge.order_control_batch_service_queue) == 0
    assert veh.order_control_current_visit is None


def test_f2_normal_service_to_non_order_control_outlink():
    W = _build_merge_world("serve_f2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    plain = W.get_link("plain")
    veh = _make_vehicle(W, "A1")
    _place_arrived(
        merge,
        veh,
        link1,
        plain,
        visit_id=2,
        arrival_time=10.0,
        tiebreaker=0.1,
    )
    veh.move_remain = 5.0
    merge.register_order_control_batch_service_units([(link1, [veh])])
    _boost_transfer_capacity(merge, link1, plain)
    count = merge.serve_order_control_batch_service_queue()
    assert count == 1
    assert veh.link is plain
    assert veh.order_control_current_visit is None


def test_g1_missing_current_visit_raises():
    W = _build_merge_world("serve_g1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    veh.order_control_current_visit = None
    before = _snapshot_vehicle_state(veh)
    before_node = _snapshot_node_transfer_state(merge)
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["order_control_current_visit is None"])
    assert _snapshot_vehicle_state(veh) == before
    assert _snapshot_node_transfer_state(merge) == before_node


def test_g2_node_mismatch_raises():
    W = _build_merge_world("serve_g2")
    merge = W.get_node("merge")
    other = W.get_node("other")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    veh.order_control_current_visit["batch_assignment"] = 0
    veh.order_control_current_visit["node"] = other
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    before = _snapshot_vehicle_state(veh)
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["does not match service node"])


def test_g3_visit_id_mismatch_raises():
    W = _build_merge_world("serve_g3")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=3)
    veh.order_control_current_visit["batch_assignment"] = 0
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    before = _snapshot_vehicle_state(veh)
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["visit_id mismatch"])


def test_g4_missing_batch_assignment_raises():
    W = _build_merge_world("serve_g4")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["batch_assignment is None"])


def test_g5_batch_id_mismatch_raises():
    W = _build_merge_world("serve_g5")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    veh.order_control_current_visit["batch_assignment"] = 11
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 10,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["batch_assignment mismatch"])


def test_g6_vehicle_visit_id_length_mismatch_raises():
    W = _build_merge_world("serve_g6")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    veh.order_control_current_visit["batch_assignment"] = 0
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2, 99],
        }
    )
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["len(vehicles)=1"])


def _append_serve_unit_for_validation_tests(merge, veh, link1, *, batch_id=0, visit_ids=None):
    if visit_ids is None:
        visit_ids = [veh.order_control_current_visit["visit_id"]]
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": batch_id,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": list(visit_ids),
        }
    )


def _snapshot_serve_validation_state(merge, veh):
    return {
        "vehicle": _snapshot_vehicle_state(veh),
        "node": _snapshot_node_transfer_state(merge),
        "queue": [
            {
                "batch_id": unit.get("batch_id"),
                "inlink": unit.get("inlink"),
                "vehicles": list(unit.get("vehicles", [])),
                "visit_ids": list(unit.get("visit_ids", [])),
            }
            for unit in merge.order_control_batch_service_queue
        ],
    }


def test_g7_missing_batch_id_key_raises():
    W = _build_merge_world("serve_g7")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    veh.order_control_current_visit["batch_assignment"] = 0
    merge.order_control_batch_service_queue.append(
        {
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    before = _snapshot_serve_validation_state(merge, veh)
    _expect_value_error(
        merge.serve_order_control_batch_service_queue,
        ["merge", "missing required key", "batch_id"],
    )
    assert _snapshot_serve_validation_state(merge, veh) == before


def test_g8_invalid_service_unit_batch_id_raises():
    W = _build_merge_world("serve_g8")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    veh.order_control_current_visit["batch_assignment"] = 0
    for invalid_batch_id in (True, -1, 1.5, "1"):
        merge.order_control_batch_service_queue.clear()
        _append_serve_unit_for_validation_tests(
            merge, veh, link1, batch_id=invalid_batch_id
        )
        before = _snapshot_serve_validation_state(merge, veh)
        _expect_value_error(
            merge.serve_order_control_batch_service_queue,
            ["merge", f"batch_id={invalid_batch_id!r}", "non-negative int"],
        )
        assert _snapshot_serve_validation_state(merge, veh) == before


def test_g9_invalid_registered_visit_id_raises():
    W = _build_merge_world("serve_g9")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_arrived(merge, veh, link1, out, visit_id=2)
    veh.order_control_current_visit["batch_assignment"] = 0
    for invalid_visit_id in (True, 0, -1, 1.5, "1"):
        merge.order_control_batch_service_queue.clear()
        _append_serve_unit_for_validation_tests(
            merge, veh, link1, visit_ids=[invalid_visit_id]
        )
        before = _snapshot_serve_validation_state(merge, veh)
        _expect_value_error(
            merge.serve_order_control_batch_service_queue,
            [
                "merge",
                "batch_id=0",
                f"registered_visit_id={invalid_visit_id!r}",
                "positive int",
            ],
        )
        assert _snapshot_serve_validation_state(merge, veh) == before


def test_h1_not_arrived_waits_without_mutation():
    W = _build_merge_world("wait_h1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_on_inlink(veh, merge, link1, visit_id=2, x=200.0)
    veh.route_next_link = out
    veh.assign_order_control_batch_to_current_visit(merge, 0)
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    before_veh = _snapshot_vehicle_state(veh)
    before_node = _snapshot_node_transfer_state(merge)
    before_vehicle_names = [
        [v.name for v in unit["vehicles"]]
        for unit in merge.order_control_batch_service_queue
    ]
    before_visit_ids = [
        list(unit["visit_ids"]) for unit in merge.order_control_batch_service_queue
    ]
    count = merge.serve_order_control_batch_service_queue()
    assert count == 0
    assert _snapshot_vehicle_state(veh) == before_veh
    assert _snapshot_node_transfer_state(merge) == before_node
    assert [
        [v.name for v in unit["vehicles"]]
        for unit in merge.order_control_batch_service_queue
    ] == before_vehicle_names
    assert [
        list(unit["visit_ids"]) for unit in merge.order_control_batch_service_queue
    ] == before_visit_ids


def test_h2_visit_id_mismatch_not_treated_as_not_arrived():
    W = _build_merge_world("wait_h2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "A1")
    _place_on_inlink(veh, merge, link1, visit_id=3, x=200.0)
    veh.route_next_link = out
    veh.order_control_current_visit["batch_assignment"] = 0
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [2],
        }
    )
    _expect_value_error(merge.serve_order_control_batch_service_queue, ["visit_id mismatch"])


def test_i1_parallel_lists_stay_synchronized():
    W = _build_merge_world("parallel_i1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh_a = _make_vehicle(W, "A")
    veh_b = _make_vehicle(W, "B", orig="orig2")
    _place_arrived(merge, veh_a, link1, out, visit_id=3, x=200.0, tiebreaker=0.1)
    _place_arrived(merge, veh_b, link1, out, visit_id=7, x=150.0, tiebreaker=0.2)
    veh_a.move_remain = 20.0
    veh_b.move_remain = 20.0
    merge.register_order_control_batch_service_units([(link1, [veh_a, veh_b])])
    unit = merge.order_control_batch_service_queue[0]
    assert unit["vehicles"] == [veh_a, veh_b]
    assert unit["visit_ids"] == [3, 7]
    _boost_transfer_capacity(merge, link1, out)
    count = merge.serve_order_control_batch_service_queue()
    assert count == 2
    assert len(merge.order_control_batch_service_queue) == 0


def main():
    test_a1_unassigned_get_returns_none()
    test_a2_assigned_get_returns_batch_id()
    test_a3_missing_current_visit_raises()
    test_a4_node_mismatch_raises()
    test_a5_invalid_assignment_type_raises()
    test_b1_assign_to_current_visit()
    test_b2_double_assign_raises()
    test_b3_invalid_batch_id_raises()
    test_c1_revisit_trigger_with_legacy_assignment()
    test_c2_assigned_current_visit_excluded_from_trigger()
    test_c3_assigned_trigger_direct_to_t_trigger_raises()
    test_d1_legacy_assignment_does_not_affect_prefix()
    test_d2_current_visit_prefix_violation_raises()
    test_e1_first_register_writes_current_visit_and_visit_ids()
    test_e2_revisit_register_preserves_legacy_first_value()
    test_e3_multiple_vehicle_visit_ids()
    test_e4_register_rejects_existing_current_assignment()
    test_e5_register_rollback_restores_state()
    test_f1_normal_service_transfer()
    test_f2_normal_service_to_non_order_control_outlink()
    test_g1_missing_current_visit_raises()
    test_g2_node_mismatch_raises()
    test_g3_visit_id_mismatch_raises()
    test_g4_missing_batch_assignment_raises()
    test_g5_batch_id_mismatch_raises()
    test_g6_vehicle_visit_id_length_mismatch_raises()
    test_g7_missing_batch_id_key_raises()
    test_g8_invalid_service_unit_batch_id_raises()
    test_g9_invalid_registered_visit_id_raises()
    test_h1_not_arrived_waits_without_mutation()
    test_h2_visit_id_mismatch_not_treated_as_not_arrived()
    test_i1_parallel_lists_stay_synchronized()
    print("Order-control batch visit assignment tests passed.")


if __name__ == "__main__":
    main()
