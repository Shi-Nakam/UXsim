# Regression test for N=1 BATCH vs FCFS when rank-0 candidate is blocked but rank-1
# can pass in the same timestep.
#
# Run from the repository root:
#   python tests_order_control_n1_batch_blocked_candidate_equivalence.py
#
# Expected before fix: FAIL on candidate B same-timestep pass for BATCH.

from uxsim import World

RANDOM_SEED = 0
TMAX = 200
LINK_LENGTH = 200
FREE_FLOW_SPEED = 20
CLEARANCE_TIMESTEPS = 1
TARGET_TIMESTEP = 11
CANDIDATE_A_NAME = "A"
CANDIDATE_B_NAME = "B"


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_world(order_control_type):
    W = World(
        name=f"n1_blocked_candidate_{order_control_type}",
        deltan=1,
        tmax=TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    W.addNode("orig_a", 0, 0)
    W.addNode("orig_b", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type=order_control_type,
        batch_size=1,
        order_control_batch_t_trigger_level=1,
    )
    W.addNode("mid_a", 2, 0)
    W.addNode("dest_b", 2, 2)
    W.addLink(
        "link_a",
        "orig_a",
        "merge",
        length=LINK_LENGTH,
        free_flow_speed=FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "link_b",
        "orig_b",
        "merge",
        length=LINK_LENGTH,
        free_flow_speed=FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out_a",
        "merge",
        "mid_a",
        length=LINK_LENGTH,
        free_flow_speed=FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out_b",
        "merge",
        "dest_b",
        length=LINK_LENGTH,
        free_flow_speed=FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
    _prepare_network(W)
    return W


def _make_vehicle(W, orig_name, name, dest_name):
    return W.addVehicle(orig_name, dest_name, 0, name=name)


def _sync_current_visit(veh, merge, link, earliest, arrival_time, tiebreaker):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    veh.order_control_current_visit = {
        "visit_id": veh.order_control_visit_id,
        "node": merge,
        "inlink": link,
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
        "arrival_tiebreaker": tiebreaker,
        "batch_assignment": None,
    }


def _setup_arrived_candidate(merge, veh, inlink, outlink, arrival_time, tiebreaker, x):
    veh.link = inlink
    veh.state = "run"
    veh.x = x
    veh.v = FREE_FLOW_SPEED
    veh.move_remain = 0.0
    veh.route_next_link = outlink
    veh.order_control_earliest_arrival_timesteps[merge.name] = 0
    veh.order_control_node_arrival_times[merge.name] = arrival_time
    veh.order_control_node_arrival_tiebreakers[merge.name] = tiebreaker
    _sync_current_visit(veh, merge, inlink, 0, arrival_time, tiebreaker)
    if veh not in inlink.vehicles:
        inlink.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _clearance_satisfied(merge, veh):
    clearance_required = (
        merge.last_order_control_inlink is not None
        and veh.link is not None
        and veh.link != merge.last_order_control_inlink
    )
    if not clearance_required:
        return True
    if merge.last_order_control_entry_timestep is None:
        return False
    return (
        merge.W.T - merge.last_order_control_entry_timestep
        > merge.order_control_clearance_timesteps
    )


def _outlink_space_ok(outlink, W):
    if outlink is None:
        return False
    return (
        len(outlink.vehicles) < outlink.number_of_lanes
        or outlink.vehicles[-outlink.number_of_lanes].x
        > outlink.delta_per_lane * W.DELTAN
    )


def _can_transfer(veh, merge):
    inlink = veh.link
    outlink = veh.route_next_link
    if outlink is None or inlink is None:
        return False
    return (
        len(inlink.vehicles) > 0
        and veh == inlink.vehicles[0]
        and _outlink_space_ok(outlink, merge.W)
        and outlink.capacity_in_remain >= merge.W.DELTAN
        and inlink.capacity_out_remain >= merge.W.DELTAN
        and merge.flow_capacity_remain >= merge.W.DELTAN
    )


def _fcfs_candidate_names(merge):
    candidates = [
        veh
        for veh in merge.incoming_vehicles
        if veh.route_next_link is not None
    ]
    candidates.sort(key=lambda veh: veh.get_order_control_fcfs_rank_key(merge))
    return [veh.name for veh in candidates]


def _batch_trigger_names(merge):
    return [veh.name for veh in merge.get_order_control_batch_trigger_candidates()]


def _batch_selected_groups(merge):
    trigger_candidates = merge.get_order_control_batch_trigger_candidates()
    trigger_vehicle = trigger_candidates[0]
    t_trigger = merge.estimate_order_control_batch_t_trigger_level_1(trigger_vehicle)
    candidates_by_inlink = merge.get_order_control_batch_candidates_by_inlink(t_trigger)
    ordered_groups = merge.get_ordered_order_control_batch_candidates_by_inlink(
        candidates_by_inlink,
        trigger_vehicle,
    )
    selected_groups = merge.apply_order_control_batch_max_size(
        ordered_groups,
        merge.batch_size,
    )
    return candidates_by_inlink, ordered_groups, selected_groups


def _setup_scenario(order_control_type):
    W = _build_world(order_control_type)
    merge = W.get_node("merge")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    out_a = W.get_link("out_a")
    out_b = W.get_link("out_b")

    candidate_a = _make_vehicle(W, "orig_a", CANDIDATE_A_NAME, "mid_a")
    candidate_b = _make_vehicle(W, "orig_b", CANDIDATE_B_NAME, "dest_b")
    candidate_a.enforce_route([link_a, out_a], set_avoid=True)
    candidate_b.enforce_route([link_b, out_b], set_avoid=True)

    _setup_arrived_candidate(
        merge,
        candidate_a,
        link_a,
        out_a,
        arrival_time=10.0,
        tiebreaker=0.1,
        x=LINK_LENGTH,
    )
    _setup_arrived_candidate(
        merge,
        candidate_b,
        link_b,
        out_b,
        arrival_time=10.0,
        tiebreaker=0.2,
        x=LINK_LENGTH,
    )

    out_a.capacity_in_remain = 0

    merge.W.T = TARGET_TIMESTEP
    merge.W.TIME = TARGET_TIMESTEP * merge.W.DELTAT
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None

    return {
        "W": W,
        "merge": merge,
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "link_a": link_a,
        "link_b": link_b,
        "out_a": out_a,
        "out_b": out_b,
    }


def _assert_pre_transfer_preconditions(scenario):
    merge = scenario["merge"]
    candidate_a = scenario["candidate_a"]
    candidate_b = scenario["candidate_b"]
    out_a = scenario["out_a"]
    out_b = scenario["out_b"]

    fcfs_names = _fcfs_candidate_names(merge)
    assert fcfs_names == [CANDIDATE_A_NAME, CANDIDATE_B_NAME]
    if merge.order_control_type == "batch":
        batch_names = _batch_trigger_names(merge)
        assert batch_names == fcfs_names

    assert candidate_a == merge.incoming_vehicles[0]
    assert candidate_b == merge.incoming_vehicles[1]
    assert candidate_a.link.vehicles[0] is candidate_a
    assert candidate_b.link.vehicles[0] is candidate_b

    assert not _can_transfer(candidate_a, merge)
    assert _can_transfer(candidate_b, merge)
    assert _clearance_satisfied(merge, candidate_a)
    assert _clearance_satisfied(merge, candidate_b)
    assert out_a.capacity_in_remain < merge.W.DELTAN

    if merge.order_control_type == "batch":
        candidates_by_inlink, ordered_groups, selected_groups = _batch_selected_groups(
            merge
        )
        total_candidates = sum(
            len(vehicles) for vehicles in candidates_by_inlink.values()
        )
        assert total_candidates >= 2
        assert len(ordered_groups) >= 2
        assert len(selected_groups) == 1
        assert [veh.name for veh in selected_groups[0][1]] == [CANDIDATE_A_NAME]
        assert not candidate_b.has_order_control_batch_assignment(merge)


def _run_single_transfer(scenario):
    merge = scenario["merge"]
    candidate_b = scenario["candidate_b"]
    candidate_a = scenario["candidate_a"]

    _assert_pre_transfer_preconditions(scenario)

    candidate_a_visit_id = candidate_a.order_control_current_visit["visit_id"]
    pre_queue_len = 0
    if merge.order_control_type == "batch":
        pre_queue_len = len(merge.order_control_batch_service_queue)

    if merge.order_control_type == "fcfs":
        merge.transfer_fcfs_clearance()
    else:
        merge.transfer_batch()

    return {
        "candidate_a_visit_id": candidate_a_visit_id,
        "pre_queue_len": pre_queue_len if merge.order_control_type == "batch" else None,
    }


def test_batch_size_one_processes_next_candidate_like_fcfs_when_first_is_blocked():
    fcfs_scenario = _setup_scenario("fcfs")
    batch_scenario = _setup_scenario("batch")

    fcfs_result = _run_single_transfer(fcfs_scenario)
    batch_result = _run_single_transfer(batch_scenario)

    fcfs_b = fcfs_scenario["candidate_b"]
    fcfs_a = fcfs_scenario["candidate_a"]
    batch_b = batch_scenario["candidate_b"]
    batch_a = batch_scenario["candidate_a"]
    batch_merge = batch_scenario["merge"]
    out_b = batch_scenario["out_b"]

    assert fcfs_a.link.name == "link_a"
    assert fcfs_b.link.name == "out_b"
    assert fcfs_b.link_arrival_time == TARGET_TIMESTEP

    assert batch_a.link.name == "link_a"
    assert batch_a.has_order_control_batch_assignment(batch_merge)
    assert len(batch_merge.order_control_batch_service_queue) == batch_result["pre_queue_len"] + 1
    head_unit = batch_merge.order_control_batch_service_queue[0]
    assert head_unit["vehicles"][0].name == CANDIDATE_A_NAME
    assert head_unit["visit_ids"][0] == batch_result["candidate_a_visit_id"]
    assert batch_a.get_order_control_batch_assignment(batch_merge) == head_unit["batch_id"]
    assert batch_a.order_control_current_visit["batch_assignment"] == head_unit["batch_id"]

    # Desired post-fix behavior: BATCH should match FCFS on the same timestep.
    assert batch_b.link.name == "out_b"
    assert batch_b.link_arrival_time == TARGET_TIMESTEP


if __name__ == "__main__":
    test_batch_size_one_processes_next_candidate_like_fcfs_when_first_is_blocked()
    print("N=1 blocked-candidate equivalence test passed.")
