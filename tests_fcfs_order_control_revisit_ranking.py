# Verify Phase 4-6Q FCFS ordering from current visit (not first-visit history).
#
# Run from the repository root:
#   python tests_fcfs_order_control_revisit_ranking.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import pytest

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_merge_world(name="fcfs_revisit_ranking", *, out_lanes=1):
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
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="fcfs",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink(
        "out",
        "merge",
        "dest",
        length=500,
        free_flow_speed=20,
        number_of_lanes=out_lanes,
    )
    W.set_order_control_clearance_timesteps(0)
    _prepare_network(W)
    return W


def _advance_until_on_link(veh, link_name):
    while veh.link is None or veh.link.name != link_name:
        if not veh.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {link_name}")
        veh.W.exec_simulation(duration_t2=1)


def _ensure_current_visit_on_link(veh, merge, link):
    visit = veh.order_control_current_visit
    if visit is None or visit["node"] is not merge or visit["inlink"] is not link:
        veh.link = link
        veh.begin_order_control_visit_on_link_entry()
    visit = veh.order_control_current_visit
    assert visit is not None
    assert visit["node"] is merge
    assert visit["inlink"] is link
    return visit


def _set_current_visit_arrival(visit, *, arrival_time, tiebreaker):
    visit["arrival_time"] = arrival_time
    visit["arrival_tiebreaker"] = tiebreaker


def _place_at_link_head(merge, veh, link, out_link):
    veh.link = link
    veh.state = "run"
    veh.x = link.length
    veh.v = 20.0
    veh.route_next_link = out_link
    link.vehicles.clear()
    link.vehicles.append(veh)
    link.capacity_out_remain = veh.W.DELTAN
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _prepare_transfer_capacity(merge, out_link):
    out_link.capacity_in_remain = 1e6
    out_link.vehicles.clear()
    for inlink in merge.inlinks.values():
        inlink.capacity_out_remain = 1e6
    if merge.flow_capacity is not None:
        merge.flow_capacity_remain = 1e6


def test_rank_key_returns_current_visit_values():
    W = _build_merge_world("rank_key_normal")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_rank_key")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    _set_current_visit_arrival(visit, arrival_time=30.0, tiebreaker=0.42)
    veh.order_control_node_arrival_times["merge"] = 10.0
    veh.order_control_node_arrival_tiebreakers["merge"] = 0.99

    key = veh.get_order_control_fcfs_rank_key(merge)
    assert key == (30.0, 0.42, veh.id)
    assert key != (
        veh.order_control_node_arrival_times["merge"],
        veh.order_control_node_arrival_tiebreakers["merge"],
        veh.id,
    )


def test_rank_key_raises_when_current_visit_missing():
    W = _build_merge_world("rank_key_no_visit")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_no_visit")
    veh.order_control_current_visit = None
    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        veh.get_order_control_fcfs_rank_key(merge)


def test_rank_key_raises_when_node_mismatch():
    W = _build_merge_world("rank_key_node_mismatch")
    merge = W.get_node("merge")
    dest = W.get_node("dest")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_node_mismatch")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    _set_current_visit_arrival(visit, arrival_time=10.0, tiebreaker=0.1)
    visit["node"] = dest
    with pytest.raises(ValueError, match="does not match FCFS node"):
        veh.get_order_control_fcfs_rank_key(merge)


def test_rank_key_raises_when_both_arrival_fields_none():
    W = _build_merge_world("rank_key_both_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_both_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = None
    visit["arrival_tiebreaker"] = None
    with pytest.raises(ValueError, match="incomplete arrival state"):
        veh.get_order_control_fcfs_rank_key(merge)


def test_rank_key_raises_when_arrival_time_none_only():
    W = _build_merge_world("rank_key_time_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_time_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = None
    visit["arrival_tiebreaker"] = 0.2
    with pytest.raises(ValueError, match="incomplete arrival state"):
        veh.get_order_control_fcfs_rank_key(merge)


def test_rank_key_raises_when_arrival_tiebreaker_none_only():
    W = _build_merge_world("rank_key_tie_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_tie_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = 10.0
    visit["arrival_tiebreaker"] = None
    with pytest.raises(ValueError, match="incomplete arrival state"):
        veh.get_order_control_fcfs_rank_key(merge)


def test_revisit_vehicle_loses_priority_to_first_visit_vehicle():
    W = _build_merge_world("revisit_vs_first_visit", out_lanes=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    veh_a = W.addVehicle("orig1", "dest", 0, name="veh_revisit_a")
    veh_b = W.addVehicle("orig2", "dest", 0, name="veh_first_b")
    _advance_until_on_link(veh_a, "link1")
    _advance_until_on_link(veh_b, "link2")

    visit_a = _ensure_current_visit_on_link(veh_a, merge, link1)
    visit_b = _ensure_current_visit_on_link(veh_b, merge, link2)
    veh_a.order_control_node_arrival_times["merge"] = 10.0
    veh_a.order_control_node_arrival_tiebreakers["merge"] = 0.01
    _set_current_visit_arrival(visit_a, arrival_time=30.0, tiebreaker=0.5)
    veh_b.order_control_node_arrival_times["merge"] = 20.0
    veh_b.order_control_node_arrival_tiebreakers["merge"] = 0.99
    _set_current_visit_arrival(visit_b, arrival_time=20.0, tiebreaker=0.3)

    _prepare_transfer_capacity(merge, out)
    _place_at_link_head(merge, veh_a, link1, out)
    _place_at_link_head(merge, veh_b, link2, out)
    merge.incoming_vehicles = [veh_a, veh_b]

    merge.transfer_fcfs_no_clearance()

    assert veh_b.link is out
    assert veh_a.link is link1
    assert veh_a in link1.vehicles


def test_revisit_vehicles_tiebroken_by_current_visit_tiebreaker():
    W = _build_merge_world("revisit_tiebreaker", out_lanes=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    veh_a = W.addVehicle("orig1", "dest", 0, name="veh_tie_a")
    veh_b = W.addVehicle("orig2", "dest", 0, name="veh_tie_b")
    _advance_until_on_link(veh_a, "link1")
    _advance_until_on_link(veh_b, "link2")

    visit_a = _ensure_current_visit_on_link(veh_a, merge, link1)
    visit_b = _ensure_current_visit_on_link(veh_b, merge, link2)
    same_arrival = 25.0
    veh_a.order_control_node_arrival_times["merge"] = same_arrival
    veh_a.order_control_node_arrival_tiebreakers["merge"] = 0.99
    veh_b.order_control_node_arrival_times["merge"] = same_arrival
    veh_b.order_control_node_arrival_tiebreakers["merge"] = 0.01
    _set_current_visit_arrival(visit_a, arrival_time=same_arrival, tiebreaker=0.8)
    _set_current_visit_arrival(visit_b, arrival_time=same_arrival, tiebreaker=0.2)

    _prepare_transfer_capacity(merge, out)
    _place_at_link_head(merge, veh_a, link1, out)
    _place_at_link_head(merge, veh_b, link2, out)
    merge.incoming_vehicles = [veh_a, veh_b]

    merge.transfer_fcfs_no_clearance()

    assert veh_b.link is out
    assert veh_a.link is link1
    assert veh_a in link1.vehicles


def test_same_arrival_and_tiebreaker_uses_vehicle_id():
    W = _build_merge_world("veh_id_fallback", out_lanes=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    veh_a = W.addVehicle("orig1", "dest", 0, name="veh_id_a")
    veh_b = W.addVehicle("orig2", "dest", 0, name="veh_id_b")
    _advance_until_on_link(veh_a, "link1")
    _advance_until_on_link(veh_b, "link2")

    visit_a = _ensure_current_visit_on_link(veh_a, merge, link1)
    visit_b = _ensure_current_visit_on_link(veh_b, merge, link2)
    same_arrival = 15.0
    same_tie = 0.55
    _set_current_visit_arrival(visit_a, arrival_time=same_arrival, tiebreaker=same_tie)
    _set_current_visit_arrival(visit_b, arrival_time=same_arrival, tiebreaker=same_tie)
    veh_a.order_control_node_arrival_times["merge"] = 1.0
    veh_a.order_control_node_arrival_tiebreakers["merge"] = 0.1
    veh_b.order_control_node_arrival_times["merge"] = 2.0
    veh_b.order_control_node_arrival_tiebreakers["merge"] = 0.9

    _prepare_transfer_capacity(merge, out)
    _place_at_link_head(merge, veh_a, link1, out)
    _place_at_link_head(merge, veh_b, link2, out)
    merge.incoming_vehicles = [veh_a, veh_b]

    merge.transfer_fcfs_no_clearance()

    first_id, second_id = sorted([veh_a.id, veh_b.id])
    first_veh = veh_a if veh_a.id == first_id else veh_b
    second_veh = veh_b if veh_b.id == second_id else veh_a
    assert first_veh.link is out
    assert second_veh.link is not out
    assert second_veh in second_veh.link.vehicles


def test_same_visit_reregistration_preserves_rank_key():
    W = _build_merge_world("same_visit_reregister")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_reregister_rank")
    _advance_until_on_link(veh, "link1")

    blocker = W.addVehicle("orig2", "dest", 100, name="blocker")
    blocker.state = "run"
    blocker.link = out
    blocker.x = 0
    blocker.lane = 0
    blocker.leader = None
    blocker.follower = None
    out.vehicles.append(blocker)
    out.capacity_in_remain = 0

    veh.x = link1.length
    veh.route_next_link = out
    link1.vehicles.clear()
    link1.vehicles.append(veh)
    merge.incoming_vehicles = [veh]
    W.T = 10
    veh.record_order_control_node_arrival(merge)

    visit_id_before = veh.order_control_visit_id
    key_before = veh.get_order_control_fcfs_rank_key(merge)

    merge.transfer_fcfs_clearance()
    assert veh.link is link1

    for _ in range(2):
        W.T += 1
        veh.carfollow()
        veh.update()

        assert merge.incoming_vehicles.count(veh) == 1
        assert veh.get_order_control_fcfs_rank_key(merge) == key_before
        assert veh.order_control_visit_id == visit_id_before
        assert veh.order_control_current_visit["visit_id"] == visit_id_before
        assert veh.order_control_current_visit["arrival_time"] == key_before[0]
        assert veh.order_control_current_visit["arrival_tiebreaker"] == key_before[1]

        merge.incoming_vehicles = []


def _setup_transfer_vehicle(merge, link, out_link, *, name):
    W = merge.W
    veh = W.addVehicle(link.start_node.name, "dest", 0, name=name)
    veh.link = link
    veh.state = "run"
    veh.x = link.length
    veh.v = 20.0
    veh.route_next_link = out_link
    link.vehicles.clear()
    link.vehicles.append(veh)
    link.capacity_out_remain = W.DELTAN
    merge.incoming_vehicles = [veh]
    out_link.capacity_in_remain = 1e6
    if merge.flow_capacity is not None:
        merge.flow_capacity_remain = 1e6
    return veh


def test_transfer_raises_when_current_visit_missing():
    W = _build_merge_world("transfer_no_visit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _setup_transfer_vehicle(merge, link1, out, name="veh_transfer_no_visit")
    veh.order_control_current_visit = None
    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        merge.transfer_fcfs_clearance()


def test_transfer_raises_when_current_visit_node_mismatch():
    W = _build_merge_world("transfer_node_mismatch")
    merge = W.get_node("merge")
    dest = W.get_node("dest")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _setup_transfer_vehicle(merge, link1, out, name="veh_transfer_node_mismatch")
    veh.order_control_current_visit = {
        "visit_id": 1,
        "node": dest,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": 10.0,
        "arrival_tiebreaker": 0.1,
        "batch_assignment": None,
    }
    with pytest.raises(ValueError, match="does not match FCFS node"):
        merge.transfer_fcfs_no_clearance()


def test_transfer_raises_when_arrival_fields_both_none():
    W = _build_merge_world("transfer_arrival_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _setup_transfer_vehicle(merge, link1, out, name="veh_transfer_arrival_none")
    veh.order_control_current_visit = {
        "visit_id": 1,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": None,
        "arrival_tiebreaker": None,
        "batch_assignment": None,
    }
    with pytest.raises(ValueError, match="incomplete arrival state"):
        merge.transfer_fcfs_clearance()


TESTS = [
    test_rank_key_returns_current_visit_values,
    test_rank_key_raises_when_current_visit_missing,
    test_rank_key_raises_when_node_mismatch,
    test_rank_key_raises_when_both_arrival_fields_none,
    test_rank_key_raises_when_arrival_time_none_only,
    test_rank_key_raises_when_arrival_tiebreaker_none_only,
    test_revisit_vehicle_loses_priority_to_first_visit_vehicle,
    test_revisit_vehicles_tiebroken_by_current_visit_tiebreaker,
    test_same_arrival_and_tiebreaker_uses_vehicle_id,
    test_same_visit_reregistration_preserves_rank_key,
    test_transfer_raises_when_current_visit_missing,
    test_transfer_raises_when_current_visit_node_mismatch,
    test_transfer_raises_when_arrival_fields_both_none,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("FCFS revisit ranking tests passed.")
