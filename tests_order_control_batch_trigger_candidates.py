# Verify BATCH trigger candidate identification on order-control nodes.
#
# Run from the repository root:
#   python tests_order_control_batch_trigger_candidates.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy

import pytest

from uxsim import World


def _build_merge_world(name, merge_order_control_type="batch", merge_eligible=True):
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
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=merge_eligible,
        order_control_type=merge_order_control_type,
    )
    W.addNode("other_node", 1, 2)
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _sync_arrived_trigger_current_visit(
    veh, merge, link, arrival_time, tiebreaker, earliest_arrival_timestep=0, batch_assignment=None
):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    visit = veh.order_control_current_visit
    if visit is None or visit.get("node") is not merge or visit.get("inlink") is not link:
        veh.order_control_current_visit = {
            "visit_id": veh.order_control_visit_id,
            "node": merge,
            "inlink": link,
            "earliest_arrival_timestep": earliest_arrival_timestep,
            "arrival_time": arrival_time,
            "arrival_tiebreaker": tiebreaker,
            "batch_assignment": batch_assignment,
        }
    else:
        visit["visit_id"] = veh.order_control_visit_id
        visit["node"] = merge
        visit["inlink"] = link
        visit["earliest_arrival_timestep"] = earliest_arrival_timestep
        visit["arrival_time"] = arrival_time
        visit["arrival_tiebreaker"] = tiebreaker
        visit["batch_assignment"] = batch_assignment


def _make_candidate_vehicle(W, name, departure_time, arrival_time, tiebreaker):
    merge = W.get_node("merge")
    link = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", departure_time, name=name)
    veh.link = link
    veh.route_next_link = W.get_link("out")
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    _sync_arrived_trigger_current_visit(veh, merge, link, arrival_time, tiebreaker)
    return veh


def _expected_order(vehicles, node_name):
    return sorted(
        vehicles,
        key=lambda veh: (
            veh.order_control_node_arrival_times[node_name],
            veh.order_control_node_arrival_tiebreakers[node_name],
            veh.id,
        ),
    )


def _snapshot_state(merge, vehicles):
    return {
        "incoming_vehicles": list(merge.incoming_vehicles),
        "service_queue": list(merge.order_control_batch_service_queue),
        "next_id": merge.order_control_batch_next_id,
        "vehicles": {
            veh.name: {
                "batch_assignments": copy.copy(veh.order_control_batch_assignments),
                "arrival_times": copy.copy(veh.order_control_node_arrival_times),
                "tiebreakers": copy.copy(veh.order_control_node_arrival_tiebreakers),
                "earliest": copy.copy(veh.order_control_earliest_arrival_timesteps),
            }
            for veh in vehicles
        },
    }


def test_non_batch_nodes_return_empty_list():
    W = World(
        name="batch_trigger_non_batch",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    node_ineligible = W.addNode("ineligible", 0, 0, order_control_eligible=False, order_control_type="none")
    node_eligible_none = W.addNode("eligible_none", 1, 0, order_control_eligible=True, order_control_type="none")
    W.addNode("dest", 2, 0)
    W.addLink("link1", "ineligible", "dest", length=200, free_flow_speed=20, number_of_lanes=1)

    veh = W.addVehicle("ineligible", "dest", 0, name="veh_non_batch")
    veh.route_next_link = W.get_link("link1")
    node_ineligible.incoming_vehicles.append(veh)
    node_eligible_none.incoming_vehicles.append(veh)

    assert node_ineligible.get_order_control_batch_trigger_candidates() == []
    assert node_eligible_none.get_order_control_batch_trigger_candidates() == []


def test_fcfs_node_returns_empty_list():
    W = _build_merge_world("batch_trigger_fcfs", merge_order_control_type="fcfs")
    merge = W.get_node("merge")
    veh = _make_candidate_vehicle(W, "veh_fcfs", 0, 10.0, 0.5)
    merge.incoming_vehicles.append(veh)

    assert merge.get_order_control_batch_trigger_candidates() == []


def test_unbatched_arrived_vehicles_become_candidates():
    W = _build_merge_world("batch_trigger_unbatched")
    merge = W.get_node("merge")
    veh = _make_candidate_vehicle(W, "veh_candidate", 0, 10.0, 0.5)
    merge.incoming_vehicles.append(veh)

    candidates = merge.get_order_control_batch_trigger_candidates()
    assert isinstance(candidates, list)
    assert candidates == [veh]
    assert candidates[0] is veh


def test_candidates_sorted_by_arrival_time():
    W = _build_merge_world("batch_trigger_arrival_order")
    merge = W.get_node("merge")
    veh_late = _make_candidate_vehicle(W, "veh_late", 0, 20.0, 0.9)
    veh_early = _make_candidate_vehicle(W, "veh_early", 1, 10.0, 0.1)

    merge.incoming_vehicles = [veh_late, veh_early]
    candidates = merge.get_order_control_batch_trigger_candidates()

    assert candidates == [veh_early, veh_late]
    assert candidates == _expected_order([veh_early, veh_late], "merge")


def test_candidates_sorted_by_tiebreaker_for_simultaneous_arrivals():
    W = _build_merge_world("batch_trigger_tiebreaker")
    merge = W.get_node("merge")
    veh_b = _make_candidate_vehicle(W, "veh_b", 0, 15.0, 0.8)
    veh_a = _make_candidate_vehicle(W, "veh_a", 1, 15.0, 0.2)

    merge.incoming_vehicles = [veh_b, veh_a]
    tiebreakers_before = {
        veh_b.name: veh_b.order_control_node_arrival_tiebreakers["merge"],
        veh_a.name: veh_a.order_control_node_arrival_tiebreakers["merge"],
    }

    first_call = merge.get_order_control_batch_trigger_candidates()
    second_call = merge.get_order_control_batch_trigger_candidates()

    assert first_call == [veh_a, veh_b]
    assert second_call == first_call
    assert veh_b.order_control_node_arrival_tiebreakers["merge"] == tiebreakers_before[veh_b.name]
    assert veh_a.order_control_node_arrival_tiebreakers["merge"] == tiebreakers_before[veh_a.name]


def test_node_specific_batch_assignment_exclusion():
    W = _build_merge_world("batch_trigger_assignment_exclusion")
    merge = W.get_node("merge")

    veh1 = _make_candidate_vehicle(W, "veh1", 0, 10.0, 0.1)
    veh1.order_control_current_visit["batch_assignment"] = 0

    veh2 = _make_candidate_vehicle(W, "veh2", 1, 11.0, 0.2)

    veh3 = _make_candidate_vehicle(W, "veh3", 2, 12.0, 0.3)
    veh3.order_control_batch_assignments["other_node"] = 0

    merge.incoming_vehicles = [veh1, veh2, veh3]
    candidates = merge.get_order_control_batch_trigger_candidates()

    assert candidates == [veh2, veh3]
    assert veh1 not in candidates
    assert veh3 in candidates


def test_no_side_effects():
    W = _build_merge_world("batch_trigger_no_side_effects")
    merge = W.get_node("merge")
    veh_a = _make_candidate_vehicle(W, "veh_a", 0, 10.0, 0.1)
    veh_b = _make_candidate_vehicle(W, "veh_b", 1, 12.0, 0.2)
    merge.incoming_vehicles = [veh_b, veh_a]
    vehicles = [veh_a, veh_b]

    before = _snapshot_state(merge, vehicles)
    candidates = merge.get_order_control_batch_trigger_candidates()
    after = _snapshot_state(merge, vehicles)

    assert candidates == [veh_a, veh_b]
    assert before == after


def test_incoming_vehicle_storage_order_independence():
    W = _build_merge_world("batch_trigger_storage_order")
    merge = W.get_node("merge")
    vehicle_a = _make_candidate_vehicle(W, "vehicle_a", 0, 10.0, 0.1)
    vehicle_b = _make_candidate_vehicle(W, "vehicle_b", 1, 20.0, 0.2)

    merge.incoming_vehicles = [vehicle_b, vehicle_a]
    candidates = merge.get_order_control_batch_trigger_candidates()

    assert candidates == [vehicle_a, vehicle_b]
    assert merge.incoming_vehicles == [vehicle_b, vehicle_a]


def test_vehicle_without_route_next_link_is_excluded():
    W = _build_merge_world("batch_trigger_no_route")
    merge = W.get_node("merge")

    veh_no_route = W.addVehicle("orig1", "dest", 0, name="veh_no_route")
    veh_no_route.route_next_link = None
    veh_no_route.order_control_node_arrival_times["merge"] = 10.0
    veh_no_route.order_control_node_arrival_tiebreakers["merge"] = 0.1

    veh_valid = _make_candidate_vehicle(W, "veh_valid", 3, 11.0, 0.3)

    merge.incoming_vehicles = [veh_no_route, veh_valid]
    assert merge.get_order_control_batch_trigger_candidates() == [veh_valid]


def test_candidate_with_missing_arrival_time_raises():
    W = _build_merge_world("batch_trigger_missing_arrival_time")
    merge = W.get_node("merge")
    outlink = W.get_link("out")
    link1 = W.get_link("link1")

    veh_no_arrival = W.addVehicle("orig1", "dest", 1, name="veh_no_arrival")
    veh_no_arrival.route_next_link = outlink
    veh_no_arrival.order_control_node_arrival_tiebreakers["merge"] = 0.2
    veh_no_arrival.order_control_visit_id = 1
    veh_no_arrival.order_control_current_visit = {
        "visit_id": 1,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": None,
        "arrival_tiebreaker": 0.2,
        "batch_assignment": None,
    }
    merge.incoming_vehicles = [veh_no_arrival]
    with pytest.raises(ValueError, match="incomplete arrival state") as exc_info:
        merge.get_order_control_batch_trigger_candidates()
    message = str(exc_info.value)
    assert veh_no_arrival.name in message
    assert "arrival_time=None" in message


def test_candidate_with_missing_arrival_tiebreaker_raises():
    W = _build_merge_world("batch_trigger_missing_arrival_tiebreaker")
    merge = W.get_node("merge")
    outlink = W.get_link("out")
    link1 = W.get_link("link1")

    veh_no_tiebreaker = W.addVehicle("orig1", "dest", 2, name="veh_no_tiebreaker")
    veh_no_tiebreaker.route_next_link = outlink
    veh_no_tiebreaker.order_control_node_arrival_times["merge"] = 12.0
    veh_no_tiebreaker.order_control_visit_id = 1
    veh_no_tiebreaker.order_control_current_visit = {
        "visit_id": 1,
        "node": merge,
        "inlink": link1,
        "earliest_arrival_timestep": 0,
        "arrival_time": 12.0,
        "arrival_tiebreaker": None,
        "batch_assignment": None,
    }
    merge.incoming_vehicles = [veh_no_tiebreaker]
    with pytest.raises(ValueError, match="incomplete arrival state") as exc_info:
        merge.get_order_control_batch_trigger_candidates()
    message = str(exc_info.value)
    assert veh_no_tiebreaker.name in message
    assert "arrival_tiebreaker=None" in message


if __name__ == "__main__":
    test_non_batch_nodes_return_empty_list()
    test_fcfs_node_returns_empty_list()
    test_unbatched_arrived_vehicles_become_candidates()
    test_candidates_sorted_by_arrival_time()
    test_candidates_sorted_by_tiebreaker_for_simultaneous_arrivals()
    test_node_specific_batch_assignment_exclusion()
    test_no_side_effects()
    test_incoming_vehicle_storage_order_independence()
    test_vehicle_without_route_next_link_is_excluded()
    test_candidate_with_missing_arrival_time_raises()
    test_candidate_with_missing_arrival_tiebreaker_raises()
    print("Order-control batch trigger candidates test passed.")
