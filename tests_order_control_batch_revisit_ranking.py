# Verify Phase 4-6R Step 2 BATCH formation reads revisit arrival/earliest from current visit.
#
# - Revisit vehicle arrival and earliest information used by Node-side BATCH formation
#   must come from order_control_current_visit, not legacy first-visit dictionaries.
# - Past-assignment visit handling is Phase 4-6S; normal-case tests here leave no
#   stale order_control_batch_assignments on target vehicles.
#
# Run from the repository root:
#   python tests_order_control_batch_revisit_ranking.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import math

import pytest

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_merge_world(name="batch_revisit_ranking", *, num_inlinks=2):
    W = World(
        name=name,
        deltan=1,
        tmax=400,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    if num_inlinks >= 3:
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
    if num_inlinks >= 3:
        W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _advance_until_on_link(veh, link_name):
    while veh.link is None or veh.link.name != link_name:
        if not veh.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {link_name}")
        veh.W.exec_simulation(duration_t2=1)


def _set_current_visit(
    veh,
    merge,
    link,
    *,
    earliest,
    arrival_time=None,
    arrival_tiebreaker=None,
    visit_id=1,
):
    veh.order_control_current_visit = {
        "visit_id": visit_id,
        "node": merge,
        "inlink": link,
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
        "arrival_tiebreaker": arrival_tiebreaker,
        "batch_assignment": None,
    }


def _place_arrived_trigger(merge, veh, link, out_link, *, earliest, arrival_time, tiebreaker, x):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.route_next_link = out_link
    _set_current_visit(
        veh,
        merge,
        link,
        earliest=earliest,
        arrival_time=arrival_time,
        arrival_tiebreaker=tiebreaker,
    )
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _place_pre_arrival_on_inlink(veh, merge, link, *, earliest, x=100.0):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    _set_current_visit(
        veh,
        merge,
        link,
        earliest=earliest,
        arrival_time=None,
        arrival_tiebreaker=None,
    )
    link.vehicles.append(veh)


def test_trigger_candidates_ranked_by_current_visit_arrival_time():
    W = _build_merge_world("trigger_arrival_time")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    veh_late_legacy = W.addVehicle("orig1", "dest", 0, name="veh_late_legacy")
    veh_early_current = W.addVehicle("orig2", "dest", 0, name="veh_early_current")
    _place_arrived_trigger(
        merge,
        veh_late_legacy,
        link1,
        out,
        earliest=10,
        arrival_time=100.0,
        tiebreaker=0.1,
        x=200.0,
    )
    _place_arrived_trigger(
        merge,
        veh_early_current,
        link2,
        out,
        earliest=10,
        arrival_time=10.0,
        tiebreaker=0.9,
        x=200.0,
    )
    veh_late_legacy.order_control_node_arrival_times["merge"] = 10.0
    veh_late_legacy.order_control_node_arrival_tiebreakers["merge"] = 0.01
    veh_early_current.order_control_node_arrival_times["merge"] = 100.0
    veh_early_current.order_control_node_arrival_tiebreakers["merge"] = 0.99

    candidates = merge.get_order_control_batch_trigger_candidates()
    assert candidates == [veh_early_current, veh_late_legacy]


def test_trigger_candidates_ranked_by_current_visit_tiebreaker():
    W = _build_merge_world("trigger_tiebreaker")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    same_arrival = 25.0

    veh_b = W.addVehicle("orig1", "dest", 0, name="veh_b")
    veh_a = W.addVehicle("orig2", "dest", 0, name="veh_a")
    _place_arrived_trigger(
        merge,
        veh_b,
        link1,
        out,
        earliest=10,
        arrival_time=same_arrival,
        tiebreaker=0.8,
        x=200.0,
    )
    _place_arrived_trigger(
        merge,
        veh_a,
        link2,
        out,
        earliest=10,
        arrival_time=same_arrival,
        tiebreaker=0.2,
        x=200.0,
    )
    veh_b.order_control_node_arrival_tiebreakers["merge"] = 0.01
    veh_a.order_control_node_arrival_tiebreakers["merge"] = 0.99

    candidates = merge.get_order_control_batch_trigger_candidates()
    assert candidates == [veh_a, veh_b]


def test_trigger_candidates_use_vehicle_id_fallback():
    W = _build_merge_world("trigger_veh_id")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    same_arrival = 15.0
    same_tie = 0.55

    veh_a = W.addVehicle("orig1", "dest", 0, name="veh_a")
    veh_b = W.addVehicle("orig2", "dest", 0, name="veh_b")
    _place_arrived_trigger(
        merge,
        veh_a,
        link1,
        out,
        earliest=10,
        arrival_time=same_arrival,
        tiebreaker=same_tie,
        x=200.0,
    )
    _place_arrived_trigger(
        merge,
        veh_b,
        link2,
        out,
        earliest=10,
        arrival_time=same_arrival,
        tiebreaker=same_tie,
        x=200.0,
    )

    candidates = merge.get_order_control_batch_trigger_candidates()
    first_id, second_id = sorted([veh_a.id, veh_b.id])
    first_veh = veh_a if veh_a.id == first_id else veh_b
    second_veh = veh_b if veh_b.id == second_id else veh_a
    assert candidates == [first_veh, second_veh]


def test_trigger_candidates_raise_when_current_visit_missing():
    W = _build_merge_world("trigger_no_visit")
    merge = W.get_node("merge")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_no_visit")
    veh.route_next_link = out
    veh.order_control_current_visit = None
    merge.incoming_vehicles.append(veh)

    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        merge.get_order_control_batch_trigger_candidates()


def test_trigger_candidates_raise_when_arrival_incomplete():
    W = _build_merge_world("trigger_incomplete_arrival")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_incomplete")
    veh.route_next_link = out
    _set_current_visit(veh, merge, link1, earliest=10, arrival_time=None, arrival_tiebreaker=None)
    merge.incoming_vehicles.append(veh)

    with pytest.raises(ValueError, match="incomplete arrival state"):
        merge.get_order_control_batch_trigger_candidates()


def test_level_0_uses_current_visit_for_t_trigger():
    W = _build_merge_world("level_0_current_visit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    current_arrival_time = 50.0
    current_earliest = 60

    trigger = W.addVehicle("orig1", "dest", 0, name="trigger_l0")
    _place_arrived_trigger(
        merge,
        trigger,
        link1,
        out,
        earliest=current_earliest,
        arrival_time=current_arrival_time,
        tiebreaker=0.1,
        x=200.0,
    )
    trigger.order_control_node_arrival_times["merge"] = 10.0
    trigger.order_control_earliest_arrival_timesteps["merge"] = 15

    arrival_timestep = int(round(current_arrival_time / W.DELTAT))
    first_transfer_timestep = arrival_timestep + 1
    expected = max(first_transfer_timestep, current_earliest)
    legacy_expected = max(int(round(10.0 / W.DELTAT)) + 1, 15)

    result = merge.estimate_order_control_batch_t_trigger_level_0(trigger)
    assert result == expected
    assert result != legacy_expected


def test_level_1_uses_current_visit_for_t_trigger():
    W = _build_merge_world("level_1_current_visit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    current_arrival_time = 40.0
    current_earliest = 55

    trigger = W.addVehicle("orig2", "dest", 0, name="trigger_l1")
    _place_arrived_trigger(
        merge,
        trigger,
        link2,
        out,
        earliest=current_earliest,
        arrival_time=current_arrival_time,
        tiebreaker=0.2,
        x=200.0,
    )
    trigger.order_control_node_arrival_times["merge"] = 5.0
    trigger.order_control_earliest_arrival_timesteps["merge"] = 8

    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 5

    base = max(int(round(current_arrival_time / W.DELTAT)) + 1, current_earliest)
    clearance_satisfied_timestep = (
        merge.last_order_control_entry_timestep
        + merge.order_control_clearance_timesteps
        + 1
    )
    expected = max(base, clearance_satisfied_timestep)

    result = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    assert result == expected


def test_inlink_candidate_included_by_current_visit_earliest():
    W = _build_merge_world("inlink_included")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    t_trigger = 20

    veh = W.addVehicle("orig1", "dest", 0, name="veh_included")
    _place_pre_arrival_on_inlink(veh, merge, link1, earliest=15)
    veh.order_control_earliest_arrival_timesteps["merge"] = 25

    result = merge.get_order_control_batch_candidates_by_inlink(t_trigger)
    assert result[link1] == [veh]


def test_inlink_candidate_excluded_by_current_visit_earliest():
    W = _build_merge_world("inlink_excluded")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    t_trigger = 20

    veh = W.addVehicle("orig1", "dest", 0, name="veh_excluded")
    _place_pre_arrival_on_inlink(veh, merge, link1, earliest=25)
    veh.order_control_earliest_arrival_timesteps["merge"] = 15

    result = merge.get_order_control_batch_candidates_by_inlink(t_trigger)
    assert link1 not in result


def test_inlink_candidates_raise_when_current_visit_missing():
    W = _build_merge_world("inlink_no_visit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = W.addVehicle("orig1", "dest", 0, name="veh_no_visit")
    veh.link = link1
    veh.state = "run"
    veh.x = 100.0
    veh.v = 20.0
    veh.order_control_current_visit = None
    veh.order_control_earliest_arrival_timesteps["merge"] = 10
    link1.vehicles.append(veh)

    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        merge.get_order_control_batch_candidates_by_inlink(20)


def test_pre_arrival_vehicle_with_none_arrival_fields_is_valid_candidate():
    W = _build_merge_world("inlink_pre_arrival_ok")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    t_trigger = 20

    veh = W.addVehicle("orig1", "dest", 0, name="veh_pre_arrival_ok")
    _place_pre_arrival_on_inlink(veh, merge, link1, earliest=18)
    visit = veh.order_control_current_visit
    assert visit["arrival_time"] is None
    assert visit["arrival_tiebreaker"] is None

    result = merge.get_order_control_batch_candidates_by_inlink(t_trigger)
    assert result[link1] == [veh]


def test_candidate_group_ordering_without_legacy_arrival_key():
    W = _build_merge_world("group_order_no_legacy", num_inlinks=3)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")

    trigger = W.addVehicle("orig2", "dest", 0, name="trigger")
    head1 = W.addVehicle("orig1", "dest", 0, name="head1")
    head3 = W.addVehicle("orig3", "dest", 0, name="head3")
    _place_arrived_trigger(
        merge,
        trigger,
        link2,
        out,
        earliest=10,
        arrival_time=10.0,
        tiebreaker=0.5,
        x=200.0,
    )
    _place_pre_arrival_on_inlink(head1, merge, link1, earliest=10, x=140.0)
    _place_pre_arrival_on_inlink(head3, merge, link3, earliest=10, x=100.0)
    trigger.order_control_node_arrival_times.pop("merge", None)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }
    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink,
        trigger,
    )
    assert [inlink for inlink, _ in ordered] == [link2, link1, link3]


def test_candidate_group_ordering_snapshot_order_matches_expected_keys():
    W = _build_merge_world("group_order_snapshot", num_inlinks=3)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    arrival_seconds = 10.0

    trigger = W.addVehicle("orig2", "dest", 0, name="trigger")
    head1 = W.addVehicle("orig1", "dest", 0, name="head1")
    head3 = W.addVehicle("orig3", "dest", 0, name="head3")
    _place_arrived_trigger(
        merge,
        trigger,
        link2,
        out,
        earliest=10,
        arrival_time=arrival_seconds,
        tiebreaker=0.5,
        x=200.0,
    )
    _place_pre_arrival_on_inlink(head1, merge, link1, earliest=10, x=140.0)
    _place_pre_arrival_on_inlink(head3, merge, link3, earliest=10, x=100.0)

    candidates_by_inlink = {
        link1: [head1],
        link2: [trigger],
        link3: [head3],
    }

    trigger_arrival_timestep = int(round(arrival_seconds / W.DELTAT))
    expected_other_order = []
    for inlink, head_vehicle in ((link1, head1), (link3, head3)):
        remaining_distance = max(0, inlink.length - head_vehicle.x)
        remaining_free_flow_timesteps = math.ceil(
            (remaining_distance / inlink.u) / W.DELTAT
        )
        snapshot_estimated_arrival_timestep = (
            trigger_arrival_timestep + remaining_free_flow_timesteps
        )
        expected_other_order.append(
            (
                snapshot_estimated_arrival_timestep,
                head_vehicle.id,
                inlink,
            )
        )
    expected_other_order.sort(key=lambda item: (item[0], item[1]))
    expected_inlink_order = [link2] + [item[2] for item in expected_other_order]

    ordered = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink,
        trigger,
    )
    assert [inlink for inlink, _ in ordered] == expected_inlink_order


def test_same_visit_reregistration_preserves_trigger_rank_key():
    W = _build_merge_world("same_visit_reregister")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_reregister")
    _advance_until_on_link(veh, "link1")

    veh.x = link1.length
    veh.route_next_link = out
    link1.vehicles.clear()
    link1.vehicles.append(veh)
    W.T = 10
    veh.record_order_control_node_arrival(merge)

    visit_id_before = veh.order_control_visit_id
    key_before = (
        veh.order_control_current_visit["arrival_time"],
        veh.order_control_current_visit["arrival_tiebreaker"],
        veh.id,
    )
    legacy_arrival_before = dict(veh.order_control_node_arrival_times)
    legacy_tie_before = dict(veh.order_control_node_arrival_tiebreakers)

    for _ in range(2):
        W.T += 1
        veh.carfollow()
        veh.update()

        assert merge.incoming_vehicles.count(veh) == 1
        assert (
            veh.order_control_current_visit["arrival_time"],
            veh.order_control_current_visit["arrival_tiebreaker"],
            veh.id,
        ) == key_before
        assert veh.order_control_visit_id == visit_id_before
        assert veh.order_control_current_visit["visit_id"] == visit_id_before
        assert veh.order_control_node_arrival_times == legacy_arrival_before
        assert veh.order_control_node_arrival_tiebreakers == legacy_tie_before

        merge.incoming_vehicles = []


def test_form_order_control_batch_uses_current_visit_trigger_order():
    W = _build_merge_world("formation_current_trigger", num_inlinks=2)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    veh_legacy_first = W.addVehicle("orig1", "dest", 0, name="veh_legacy_first")
    veh_current_first = W.addVehicle("orig2", "dest", 0, name="veh_current_first")
    follow_current = W.addVehicle("orig2", "dest", 0, name="follow_current")

    _place_arrived_trigger(
        merge,
        veh_legacy_first,
        link1,
        out,
        earliest=10,
        arrival_time=30.0,
        tiebreaker=0.1,
        x=200.0,
    )
    _place_arrived_trigger(
        merge,
        veh_current_first,
        link2,
        out,
        earliest=10,
        arrival_time=10.0,
        tiebreaker=0.2,
        x=200.0,
    )
    _place_pre_arrival_on_inlink(follow_current, merge, link2, earliest=10, x=120.0)

    veh_legacy_first.order_control_node_arrival_times["merge"] = 5.0
    veh_legacy_first.order_control_node_arrival_tiebreakers["merge"] = 0.01
    veh_current_first.order_control_node_arrival_times["merge"] = 50.0
    veh_current_first.order_control_node_arrival_tiebreakers["merge"] = 0.99

    merge.incoming_vehicles = [veh_legacy_first, veh_current_first]

    result = merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    assert result == "batch_formed"

    queue = list(merge.order_control_batch_service_queue)
    assert len(queue) >= 1
    assert queue[0]["inlink"] is link2
    assert queue[0]["vehicles"][0] is veh_current_first
    assert veh_current_first.order_control_batch_assignments["merge"] == 0
    if len(queue) > 1:
        assert queue[1]["inlink"] is link1
        assert queue[1]["vehicles"][0] is veh_legacy_first


if __name__ == "__main__":
    test_trigger_candidates_ranked_by_current_visit_arrival_time()
    test_trigger_candidates_ranked_by_current_visit_tiebreaker()
    test_trigger_candidates_use_vehicle_id_fallback()
    test_trigger_candidates_raise_when_current_visit_missing()
    test_trigger_candidates_raise_when_arrival_incomplete()
    test_level_0_uses_current_visit_for_t_trigger()
    test_level_1_uses_current_visit_for_t_trigger()
    test_inlink_candidate_included_by_current_visit_earliest()
    test_inlink_candidate_excluded_by_current_visit_earliest()
    test_inlink_candidates_raise_when_current_visit_missing()
    test_pre_arrival_vehicle_with_none_arrival_fields_is_valid_candidate()
    test_candidate_group_ordering_without_legacy_arrival_key()
    test_candidate_group_ordering_snapshot_order_matches_expected_keys()
    test_same_visit_reregistration_preserves_trigger_rank_key()
    test_form_order_control_batch_uses_current_visit_trigger_order()
    print("Order-control batch revisit ranking test passed.")
