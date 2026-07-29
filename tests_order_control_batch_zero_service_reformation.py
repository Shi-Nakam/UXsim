# BATCH zero-service reformation regression tests.
#
# Run from the repository root:
#   python tests_order_control_batch_zero_service_reformation.py

from uxsim import World

RANDOM_SEED = 0
LINK_LENGTH = 200
FREE_FLOW_SPEED = 20
CLEARANCE_TIMESTEPS = 1
TARGET_TIMESTEP = 11


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_merge_network(batch_size, t_trigger_level=1):
    W = World(
        name=f"zero_service_reform_n{batch_size}",
        deltan=1,
        tmax=200,
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
        order_control_type="batch",
        batch_size=batch_size,
        order_control_batch_t_trigger_level=t_trigger_level,
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


def _can_transfer(veh, merge):
    inlink = veh.link
    outlink = veh.route_next_link
    if outlink is None or inlink is None:
        return False
    return (
        len(inlink.vehicles) > 0
        and veh == inlink.vehicles[0]
        and (
            len(outlink.vehicles) < outlink.number_of_lanes
            or outlink.vehicles[-outlink.number_of_lanes].x
            > outlink.delta_per_lane * merge.W.DELTAN
        )
        and outlink.capacity_in_remain >= merge.W.DELTAN
        and inlink.capacity_out_remain >= merge.W.DELTAN
        and merge.flow_capacity_remain >= merge.W.DELTAN
    )


def _register_service_unit(merge, batch_id, inlink, vehicles):
    visit_ids = []
    for veh in vehicles:
        visit = veh.order_control_current_visit
        assert visit is not None
        assert visit["node"] is merge
        assert visit["inlink"] is inlink
        visit["batch_assignment"] = batch_id
        if merge.name not in veh.order_control_batch_assignments:
            veh.order_control_batch_assignments[merge.name] = batch_id
        visit_ids.append(visit["visit_id"])
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": batch_id,
            "inlink": inlink,
            "vehicles": list(vehicles),
            "visit_ids": visit_ids,
        }
    )


def _install_form_counter(merge):
    state = {"form_calls": 0, "orig_form": merge.form_order_control_batch}

    def wrap_form(t_trigger_level, max_batch_size, **kwargs):
        state["form_calls"] += 1
        return state["orig_form"](
            t_trigger_level,
            max_batch_size,
            blocked_inlinks=kwargs.get("blocked_inlinks"),
            trigger_snapshot_keys=kwargs.get("trigger_snapshot_keys"),
        )

    merge.form_order_control_batch = wrap_form
    return state


def test_batch_reforms_after_zero_service_on_blocked_first_inlink():
    W = _build_merge_network(batch_size=2, t_trigger_level=0)
    merge = W.get_node("merge")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    out_a = W.get_link("out_a")
    out_b = W.get_link("out_b")

    a1 = _make_vehicle(W, "orig_a", "A1", "mid_a")
    a2 = _make_vehicle(W, "orig_a", "A2", "mid_a")
    b1 = _make_vehicle(W, "orig_b", "B1", "dest_b")
    a1.enforce_route([link_a, out_a], set_avoid=True)
    a2.enforce_route([link_a, out_a], set_avoid=True)
    b1.enforce_route([link_b, out_b], set_avoid=True)

    _setup_arrived_candidate(merge, a1, link_a, out_a, 10.0, 0.1, LINK_LENGTH)
    _setup_arrived_candidate(merge, a2, link_a, out_a, 10.1, 0.11, LINK_LENGTH - 20)
    _setup_arrived_candidate(merge, b1, link_b, out_b, 10.0, 0.2, LINK_LENGTH)

    out_a.capacity_in_remain = 0
    merge.W.T = TARGET_TIMESTEP
    merge.W.TIME = TARGET_TIMESTEP * merge.W.DELTAT

    assert not _can_transfer(a1, merge)
    assert not _can_transfer(a2, merge)
    assert _can_transfer(b1, merge)

    form_state = _install_form_counter(merge)
    result = merge.transfer_batch()

    assert result["transferred_vehicle_count"] == 1
    assert form_state["form_calls"] == 2
    assert a1.has_order_control_batch_assignment(merge)
    assert a2.has_order_control_batch_assignment(merge)
    assert a1.link.name == "link_a"
    assert a2.link.name == "link_a"
    assert b1.link.name == "out_b"
    assert b1.link_arrival_time == TARGET_TIMESTEP

    assert len(merge.order_control_batch_service_queue) == 1
    head_unit = merge.order_control_batch_service_queue[0]
    assert head_unit["inlink"].name == "link_a"
    assert [veh.name for veh in head_unit["vehicles"]] == ["A1", "A2"]
    assert head_unit["visit_ids"] == [
        a1.order_control_current_visit["visit_id"],
        a2.order_control_current_visit["visit_id"],
    ]

    batch_ids = {
        unit["batch_id"] for unit in merge.order_control_batch_service_queue
    }
    assert len(batch_ids) == 1


def test_batch_does_not_reform_after_any_vehicle_transfers():
    W = _build_merge_network(batch_size=2, t_trigger_level=0)
    merge = W.get_node("merge")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    out_a = W.get_link("out_a")
    out_b = W.get_link("out_b")

    a1 = _make_vehicle(W, "orig_a", "A1", "mid_a")
    a2 = _make_vehicle(W, "orig_a", "A2", "mid_a")
    b1 = _make_vehicle(W, "orig_b", "B1", "dest_b")
    a1.enforce_route([link_a, out_a], set_avoid=True)
    a2.enforce_route([link_a, out_a], set_avoid=True)
    b1.enforce_route([link_b, out_b], set_avoid=True)

    _setup_arrived_candidate(merge, a1, link_a, out_a, 10.0, 0.1, LINK_LENGTH)
    _setup_arrived_candidate(merge, a2, link_a, out_a, 10.1, 0.11, LINK_LENGTH - 20)
    _setup_arrived_candidate(merge, b1, link_b, out_b, 10.0, 0.2, LINK_LENGTH)
    merge.W.T = TARGET_TIMESTEP
    merge.W.TIME = TARGET_TIMESTEP * merge.W.DELTAT

    assert _can_transfer(a1, merge)
    assert _can_transfer(b1, merge)

    form_state = _install_form_counter(merge)
    result = merge.transfer_batch()

    assert result["transferred_vehicle_count"] >= 1
    assert form_state["form_calls"] == 1
    assert a1.link.name == "out_a"
    assert b1.link.name == "link_b"
    assert not b1.has_order_control_batch_assignment(merge)
    assert a2.has_order_control_batch_assignment(merge)
    assert a2.link.name == "link_a"
    assert len(merge.order_control_batch_service_queue) == 1
    assert merge.order_control_batch_service_queue[0]["inlink"].name == "link_a"
    assert merge.order_control_batch_service_queue[0]["vehicles"][0].name == "A2"


def test_batch_does_not_reform_while_head_service_vehicle_has_not_arrived():
    W = _build_merge_network(batch_size=1, t_trigger_level=0)
    merge = W.get_node("merge")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    out_a = W.get_link("out_a")
    out_b = W.get_link("out_b")

    a1 = _make_vehicle(W, "orig_a", "A1", "mid_a")
    b1 = _make_vehicle(W, "orig_b", "B1", "dest_b")
    a1.enforce_route([link_a, out_a], set_avoid=True)
    b1.enforce_route([link_b, out_b], set_avoid=True)

    a1.link = link_a
    a1.state = "run"
    a1.x = LINK_LENGTH - 20.0
    a1.v = FREE_FLOW_SPEED
    a1.route_next_link = out_a
    a1.order_control_earliest_arrival_timesteps[merge.name] = 0
    a1.order_control_node_arrival_times[merge.name] = 10.0
    a1.order_control_node_arrival_tiebreakers[merge.name] = 0.1
    _sync_current_visit(a1, merge, link_a, 0, 10.0, 0.1)
    if a1 not in link_a.vehicles:
        link_a.vehicles.append(a1)
    assert a1 not in merge.incoming_vehicles

    _setup_arrived_candidate(merge, b1, link_b, out_b, 10.0, 0.2, LINK_LENGTH)
    merge.W.T = TARGET_TIMESTEP
    merge.W.TIME = TARGET_TIMESTEP * merge.W.DELTAT

    _register_service_unit(merge, 0, link_a, [a1])
    before_batch_id = merge.order_control_batch_service_queue[0]["batch_id"]
    before_visit_id = a1.order_control_current_visit["visit_id"]
    before_assignment = a1.order_control_batch_assignments[merge.name]
    before_queue_len = len(merge.order_control_batch_service_queue)

    assert _can_transfer(b1, merge)
    assert not merge.last_order_control_inlink

    form_state = _install_form_counter(merge)
    result = merge.transfer_batch()

    assert result["transferred_vehicle_count"] == 0
    assert form_state["form_calls"] == 0
    assert len(merge.order_control_batch_service_queue) == before_queue_len
    head_unit = merge.order_control_batch_service_queue[0]
    assert head_unit["inlink"].name == "link_a"
    assert head_unit["vehicles"] == [a1]
    assert head_unit["batch_id"] == before_batch_id
    assert head_unit["visit_ids"] == [before_visit_id]
    assert a1.order_control_batch_assignments[merge.name] == before_assignment
    assert a1.order_control_current_visit["batch_assignment"] == before_batch_id
    assert not b1.has_order_control_batch_assignment(merge)
    assert b1.link.name == "link_b"
    assert b1 in link_b.vehicles
    assert b1.link is not out_b
    assert a1.link.name == "link_a"
    assert a1 not in merge.incoming_vehicles
    assert len(merge.order_control_batch_service_queue) == 1


def test_batch_does_not_reform_when_clearance_blocks_current_priority():
    W = _build_merge_network(batch_size=1, t_trigger_level=0)
    merge = W.get_node("merge")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    out_a = W.get_link("out_a")
    out_b = W.get_link("out_b")

    a1 = _make_vehicle(W, "orig_a", "A1", "mid_a")
    b1 = _make_vehicle(W, "orig_b", "B1", "dest_b")
    a1.enforce_route([link_a, out_a], set_avoid=True)
    b1.enforce_route([link_b, out_b], set_avoid=True)

    _setup_arrived_candidate(merge, a1, link_a, out_a, 10.0, 0.1, LINK_LENGTH)
    _setup_arrived_candidate(merge, b1, link_b, out_b, 10.0, 0.2, LINK_LENGTH)
    merge.last_order_control_inlink = link_b
    merge.last_order_control_entry_timestep = TARGET_TIMESTEP
    merge.W.T = TARGET_TIMESTEP
    merge.W.TIME = TARGET_TIMESTEP * merge.W.DELTAT

    assert _can_transfer(b1, merge)
    assert not (
        merge.W.T - merge.last_order_control_entry_timestep
        > merge.order_control_clearance_timesteps
    )

    form_state = _install_form_counter(merge)
    result = merge.transfer_batch()

    assert result["transferred_vehicle_count"] == 0
    assert form_state["form_calls"] == 1
    assert a1.has_order_control_batch_assignment(merge)
    assert not b1.has_order_control_batch_assignment(merge)
    assert a1.link.name == "link_a"
    assert b1.link.name == "link_b"
    assert len(merge.order_control_batch_service_queue) == 1
    assert merge.order_control_batch_service_queue[0]["vehicles"][0].name == "A1"


TESTS = [
    test_batch_reforms_after_zero_service_on_blocked_first_inlink,
    test_batch_does_not_reform_after_any_vehicle_transfers,
    test_batch_does_not_reform_while_head_service_vehicle_has_not_arrived,
    test_batch_does_not_reform_when_clearance_blocks_current_priority,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("BATCH zero-service reformation tests passed.")
