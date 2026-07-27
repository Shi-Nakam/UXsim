# Verify BATCH inlink-group ordering for Phase 4-6F.
#
# Run from the repository root:
#   python tests_order_control_batch_candidate_group_ordering.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy
import math

from uxsim import World


def _build_network(name="batch_group_ordering"):
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


def _sync_pre_arrival_current_visit(veh, merge, link, earliest, batch_assignment=None):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    visit = veh.order_control_current_visit
    if visit is None or visit.get("node") is not merge or visit.get("inlink") is not link:
        veh.order_control_current_visit = {
            "visit_id": veh.order_control_visit_id,
            "node": merge,
            "inlink": link,
            "earliest_arrival_timestep": earliest,
            "arrival_time": None,
            "arrival_tiebreaker": None,
            "batch_assignment": batch_assignment,
        }
    else:
        visit["visit_id"] = veh.order_control_visit_id
        visit["node"] = merge
        visit["inlink"] = link
        visit["earliest_arrival_timestep"] = earliest
        visit["arrival_time"] = None
        visit["arrival_tiebreaker"] = None
        visit["batch_assignment"] = batch_assignment


def _sync_arrived_trigger_current_visit(
    veh, merge, link, earliest, arrival_time, tiebreaker, batch_assignment=None
):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    visit = veh.order_control_current_visit
    if visit is None or visit.get("node") is not merge or visit.get("inlink") is not link:
        veh.order_control_current_visit = {
            "visit_id": veh.order_control_visit_id,
            "node": merge,
            "inlink": link,
            "earliest_arrival_timestep": earliest,
            "arrival_time": arrival_time,
            "arrival_tiebreaker": tiebreaker,
            "batch_assignment": batch_assignment,
        }
    else:
        visit["visit_id"] = veh.order_control_visit_id
        visit["node"] = merge
        visit["inlink"] = link
        visit["earliest_arrival_timestep"] = earliest
        visit["arrival_time"] = arrival_time
        visit["arrival_tiebreaker"] = tiebreaker
        visit["batch_assignment"] = batch_assignment


def _place_on_inlink(veh, link, earliest, x, v=20.0, batch_assignment=None):
    merge = link.end_node
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = v
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    _sync_pre_arrival_current_visit(veh, merge, link, earliest, batch_assignment=batch_assignment)
    link.vehicles.append(veh)


def _setup_trigger(merge, trigger_veh, arrival_time=10.0, tiebreaker=0.5):
    trigger_veh.order_control_node_arrival_times["merge"] = arrival_time
    trigger_veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    earliest = trigger_veh.order_control_earliest_arrival_timesteps["merge"]
    _sync_arrived_trigger_current_visit(
        trigger_veh,
        merge,
        trigger_veh.link,
        earliest,
        arrival_time,
        tiebreaker,
    )
    if trigger_veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(trigger_veh)


def _snapshot_state(merge, candidates_by_inlink, vehicles):
    return {
        "candidates_by_inlink": {
            inlink: list(candidates)
            for inlink, candidates in candidates_by_inlink.items()
        },
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
                "current_batch_assignment": (
                    None
                    if veh.order_control_current_visit is None
                    else veh.order_control_current_visit.get("batch_assignment")
                ),
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
        "links": {
            link.name: {"length": link.length, "u": link.u}
            for link in merge.inlinks.values()
        },
    }


def _expect_value_error(callable_obj):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_basic_processing_order():
    W = _build_network("group_order_basic")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }

    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )

    assert isinstance(ordered, list)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in ordered)
    assert [inlink for inlink, _ in ordered] == [link2, link1, link3]


def test_trigger_inlink_first_regardless_of_input_dict_order():
    W = _build_network("group_order_dict_order")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    candidates_by_inlink = {}
    candidates_by_inlink[link1] = [head1]
    candidates_by_inlink[link3] = [head3]
    candidates_by_inlink[link2] = [trigger]

    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    assert ordered[0][0] is link2


def test_snapshot_estimated_arrival_basic_calculation():
    W = _build_network("group_order_snapshot_basic")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }
    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    other_links = [inlink for inlink, _ in ordered[1:]]
    assert other_links == [link1, link3]


def test_snapshot_uses_per_link_free_flow_speed():
    W = _build_network("group_order_speed")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    link1.u = 10.0
    link3.u = 40.0

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=100.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }
    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    other_links = [inlink for inlink, _ in ordered[1:]]
    assert other_links == [link3, link1]


def test_current_speed_not_used():
    W = _build_network("group_order_speed_unused")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0, v=0.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0, v=50.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0, v=0.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }
    ordered_zero = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )

    head1.v = 0.0
    head3.v = 99.0
    ordered_changed = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    assert ordered_zero == ordered_changed


def test_snapshot_tiebreak_by_head_vehicle_id():
    W = _build_network("group_order_id_tiebreak")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _place_on_inlink(head3, link3, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    if head1.id > head3.id:
        head1, head3 = head3, head1
        link1, link3 = link3, link1
        candidates_by_inlink = {
            link1: [head1],
            link2: [trigger],
            link3: [head3],
        }
    else:
        candidates_by_inlink = {
            link1: [head1],
            link2: [trigger],
            link3: [head3],
        }

    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    other_links = [inlink for inlink, _ in ordered[1:]]
    smaller_id_link = link1 if head1.id < head3.id else link3
    larger_id_link = link3 if smaller_id_link is link1 else link1
    assert other_links == [smaller_id_link, larger_id_link]


def test_ceil_for_remaining_free_flow_timesteps():
    W = _build_network("group_order_ceil")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    link1.u = 10.0
    link3.u = 10.0

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=179.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    remaining_distance = 21.0
    remaining_free_flow_timesteps = math.ceil((remaining_distance / 10.0) / 1.0)
    assert remaining_free_flow_timesteps == 3

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }
    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    other_links = [inlink for inlink, _ in ordered[1:]]
    assert other_links[0] is link1


def test_head_x_beyond_link_length_uses_zero_remaining_distance():
    W = _build_network("group_order_x_overflow")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    head3 = _make_vehicle(W, "orig3", "head3")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=201.0)
    _place_on_inlink(head3, link3, earliest=10, x=100.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }
    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    other_links = [inlink for inlink, _ in ordered[1:]]
    assert other_links[0] is link1


def test_trigger_vehicle_validation_errors():
    W = _build_network("group_order_trigger_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")

    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    base_candidates = {link1: [head1], link2: [trigger]}

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, None
        )
    )

    trigger.link = None
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, trigger
        )
    )
    trigger.link = link2

    trigger.state = "end"
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, trigger
        )
    )
    trigger.state = "run"

    merge.incoming_vehicles = []
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, trigger
        )
    )
    _setup_trigger(merge, trigger)

    del trigger.order_control_node_arrival_times["merge"]
    trigger.order_control_current_visit["arrival_time"] = None
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, trigger
        )
    )
    trigger.order_control_node_arrival_times["merge"] = 10.0
    trigger.order_control_current_visit["arrival_time"] = 10.0

    del trigger.order_control_node_arrival_tiebreakers["merge"]
    trigger.order_control_current_visit["arrival_tiebreaker"] = None
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, trigger
        )
    )
    trigger.order_control_node_arrival_tiebreakers["merge"] = 0.5
    trigger.order_control_current_visit["arrival_tiebreaker"] = 0.5

    trigger.order_control_current_visit["batch_assignment"] = 0
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            base_candidates, trigger
        )
    )


def test_trigger_inlink_candidate_consistency_errors():
    W = _build_network("group_order_trigger_inlink")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")

    trigger = _make_vehicle(W, "orig2", "trigger")
    other = _make_vehicle(W, "orig2", "other")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(other, link2, earliest=11, x=150.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1]}, trigger
        )
    )

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: [other]}, trigger
        )
    )

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: [other, trigger]}, trigger
        )
    )

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: []}, trigger
        )
    )


def test_candidates_by_inlink_input_validation():
    W = _build_network("group_order_input_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    valid = {link1: [head1], link2: [trigger]}

    for invalid in (None, [], (), "invalid", 1, {}):
        _expect_value_error(
            lambda invalid=invalid: merge.get_ordered_order_control_batch_candidates_by_inlink(
                invalid, trigger
            )
        )

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: "bad", link2: [trigger]}, trigger
        )
    )
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [], link2: [trigger]}, trigger
        )
    )
    merge.get_ordered_order_control_batch_candidates_by_inlink(valid, trigger)


def test_inlink_key_validation():
    W = _build_network("group_order_inlink_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {out: [head1], link2: [trigger]}, trigger
        )
    )

    original_end_node = link1.end_node
    link1.end_node = W.get_node("dest")
    try:
        _expect_value_error(
            lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
                {link1: [head1], link2: [trigger]}, trigger
            )
        )
    finally:
        link1.end_node = original_end_node


def test_candidate_vehicle_duplication_errors():
    W = _build_network("group_order_duplicate")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1, head1], link2: [trigger]}, trigger
        )
    )
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: [trigger, head1]}, trigger
        )
    )


def test_candidate_vehicle_state_errors():
    W = _build_network("group_order_candidate_state")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    head1.link = link2
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: [trigger]}, trigger
        )
    )
    head1.link = link1

    head1.state = "end"
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: [trigger]}, trigger
        )
    )
    head1.state = "run"

    head1.order_control_current_visit["batch_assignment"] = 0
    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [head1], link2: [trigger]}, trigger
        )
    )


def test_candidate_fifo_order_validation():
    W = _build_network("group_order_fifo")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    trigger = _make_vehicle(W, "orig2", "trigger")
    _place_on_inlink(veh_a, link1, earliest=8, x=180.0)
    _place_on_inlink(veh_b, link1, earliest=9, x=120.0)
    _place_on_inlink(veh_c, link1, earliest=10, x=60.0)
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    merge.get_ordered_order_control_batch_candidates_by_inlink(
        {link1: [veh_a, veh_b], link2: [trigger]}, trigger
    )
    veh_a.order_control_current_visit["batch_assignment"] = 0
    merge.get_ordered_order_control_batch_candidates_by_inlink(
        {link1: [veh_b, veh_c], link2: [trigger]}, trigger
    )
    veh_a.order_control_current_visit["batch_assignment"] = None

    for bad in ([veh_b, veh_a], [veh_c, veh_b]):
        _expect_value_error(
            lambda bad=bad: merge.get_ordered_order_control_batch_candidates_by_inlink(
                {link1: bad, link2: [trigger]}, trigger
            )
        )


def test_unassigned_suffix_continuity_validation():
    W = _build_network("group_order_suffix")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    veh_d = _make_vehicle(W, "orig1", "veh_d")
    veh_e = _make_vehicle(W, "orig1", "veh_e")
    trigger = _make_vehicle(W, "orig2", "trigger")
    _place_on_inlink(veh_a, link1, earliest=8, x=200.0, batch_assignment=0)
    _place_on_inlink(veh_b, link1, earliest=9, x=160.0, batch_assignment=1)
    _place_on_inlink(veh_c, link1, earliest=10, x=120.0)
    _place_on_inlink(veh_d, link1, earliest=11, x=80.0)
    _place_on_inlink(veh_e, link1, earliest=12, x=40.0)
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    for valid in ([veh_c], [veh_c, veh_d], [veh_c, veh_d, veh_e]):
        merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: valid, link2: [trigger]}, trigger
        )

    for bad in ([veh_d], [veh_d, veh_e], [veh_c, veh_e]):
        _expect_value_error(
            lambda bad=bad: merge.get_ordered_order_control_batch_candidates_by_inlink(
                {link1: bad, link2: [trigger]}, trigger
            )
        )


def test_assignment_layout_unassigned_assigned_unassigned_raises():
    W = _build_network("group_order_assignment_layout_a")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    trigger = _make_vehicle(W, "orig2", "trigger")
    _place_on_inlink(veh_a, link1, earliest=10, x=180.0)
    _place_on_inlink(veh_b, link1, earliest=11, x=120.0, batch_assignment=0)
    _place_on_inlink(veh_c, link1, earliest=12, x=60.0)
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [veh_a], link2: [trigger]}, trigger
        )
    )


def test_assignment_layout_assigned_unassigned_assigned_raises():
    W = _build_network("group_order_assignment_layout_b")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    trigger = _make_vehicle(W, "orig2", "trigger")
    _place_on_inlink(veh_a, link1, earliest=10, x=180.0, batch_assignment=0)
    _place_on_inlink(veh_b, link1, earliest=11, x=120.0)
    _place_on_inlink(veh_c, link1, earliest=12, x=60.0, batch_assignment=1)
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)

    _expect_value_error(
        lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
            {link1: [veh_b], link2: [trigger]}, trigger
        )
    )


def test_trigger_arrival_validation():
    W = _build_network("group_order_trigger_arrival")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    base = {link1: [head1], link2: [trigger]}

    for invalid in (-1, True, "10", None, float("nan"), float("inf")):
        trigger.order_control_node_arrival_times["merge"] = invalid
        trigger.order_control_current_visit["arrival_time"] = invalid
        _expect_value_error(
            lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
                base, trigger
            )
        )

    trigger.order_control_node_arrival_times["merge"] = 10.0
    trigger.order_control_current_visit["arrival_time"] = 10.0
    merge.get_ordered_order_control_batch_candidates_by_inlink(base, trigger)
    trigger.order_control_node_arrival_times["merge"] = 10.5
    trigger.order_control_current_visit["arrival_time"] = 10.5
    merge.get_ordered_order_control_batch_candidates_by_inlink(base, trigger)


def test_link_and_world_numeric_validation():
    W = _build_network("group_order_numeric_validation")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    base = {link1: [head1], link2: [trigger]}

    cases = [
        ("link_u", link1, "u", 0),
        ("link_u_nan", link1, "u", float("nan")),
        ("link_u_inf", link1, "u", float("inf")),
        ("link_length", link1, "length", -1),
        ("link_length_nan", link1, "length", float("nan")),
        ("link_length_inf", link1, "length", float("inf")),
        ("head_x_nan", head1, "x", float("nan")),
        ("head_x_inf", head1, "x", float("inf")),
        ("deltat", merge.W, "DELTAT", 0),
        ("deltat_nan", merge.W, "DELTAT", float("nan")),
        ("deltat_inf", merge.W, "DELTAT", float("inf")),
    ]

    for _, obj, attr, value in cases:
        original = getattr(obj, attr)
        setattr(obj, attr, value)
        try:
            _expect_value_error(
                lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
                    base, trigger
                )
            )
        finally:
            setattr(obj, attr, original)


def test_head_vehicle_id_validation():
    W = _build_network("group_order_head_id")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    base = {link1: [head1], link2: [trigger]}

    for invalid in (-1, True, 1.5, "1", None):
        original = head1.id
        head1.id = invalid
        try:
            _expect_value_error(
                lambda: merge.get_ordered_order_control_batch_candidates_by_inlink(
                    base, trigger
                )
            )
        finally:
            head1.id = original


def test_intra_inlink_fifo_preserved_in_return_value():
    W = _build_network("group_order_fifo_preserved")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    trigger = _make_vehicle(W, "orig2", "trigger")
    _place_on_inlink(veh_a, link1, earliest=10, x=180.0)
    _place_on_inlink(veh_b, link1, earliest=11, x=120.0)
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    input_list = [veh_a, veh_b]

    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        {link1: input_list, link2: [trigger]}, trigger
    )
    link1_result = next(candidates for inlink, candidates in ordered if inlink is link1)
    assert link1_result == [veh_a, veh_b]


def test_returns_new_lists():
    W = _build_network("group_order_new_lists")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    input_dict = {link1: [head1], link2: [trigger]}
    input_list = input_dict[link1]

    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        input_dict, trigger
    )
    assert ordered is not input_dict
    link1_returned = next(candidates for inlink, candidates in ordered if inlink is link1)
    assert link1_returned is not input_list
    assert link1_returned == input_list
    assert link1_returned[0] is head1

    link1_returned.append("mutated")
    assert input_dict[link1] == [head1]
    assert input_list == [head1]


def test_no_side_effects():
    W = _build_network("group_order_no_side_effects")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    trigger = _make_vehicle(W, "orig2", "trigger")
    head1 = _make_vehicle(W, "orig1", "head1")
    _place_on_inlink(trigger, link2, earliest=10, x=200.0)
    _place_on_inlink(head1, link1, earliest=10, x=140.0)
    _setup_trigger(merge, trigger, arrival_time=10.0)
    candidates_by_inlink = {link1: [head1], link2: [trigger]}
    vehicles = [trigger, head1]

    before = _snapshot_state(merge, candidates_by_inlink, vehicles)
    merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink, trigger
    )
    after = _snapshot_state(merge, candidates_by_inlink, vehicles)
    assert before == after


def main():
    test_basic_processing_order()
    test_trigger_inlink_first_regardless_of_input_dict_order()
    test_snapshot_estimated_arrival_basic_calculation()
    test_snapshot_uses_per_link_free_flow_speed()
    test_current_speed_not_used()
    test_snapshot_tiebreak_by_head_vehicle_id()
    test_ceil_for_remaining_free_flow_timesteps()
    test_head_x_beyond_link_length_uses_zero_remaining_distance()
    test_trigger_vehicle_validation_errors()
    test_trigger_inlink_candidate_consistency_errors()
    test_candidates_by_inlink_input_validation()
    test_inlink_key_validation()
    test_candidate_vehicle_duplication_errors()
    test_candidate_vehicle_state_errors()
    test_candidate_fifo_order_validation()
    test_unassigned_suffix_continuity_validation()
    test_assignment_layout_unassigned_assigned_unassigned_raises()
    test_assignment_layout_assigned_unassigned_assigned_raises()
    test_trigger_arrival_validation()
    test_link_and_world_numeric_validation()
    test_head_vehicle_id_validation()
    test_intra_inlink_fifo_preserved_in_return_value()
    test_returns_new_lists()
    test_no_side_effects()
    print("Order-control batch candidate group ordering tests passed.")


if __name__ == "__main__":
    main()
