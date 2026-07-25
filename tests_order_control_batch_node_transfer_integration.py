# Verify Node.transfer() BATCH branch integration and N=1 BATCH vs FCFS equivalence.
#
# Run from the repository root:
#   python tests_order_control_batch_node_transfer_integration.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_merge_network(
    name="batch_node_transfer",
    *,
    merge_type="batch",
    batch_size=1,
    t_trigger_level=1,
    clearance_timesteps=1,
    three_inlinks=False,
):
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
    if three_inlinks:
        W.addNode("orig3", 0, 4)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type=merge_type,
        batch_size=batch_size,
        order_control_batch_t_trigger_level=t_trigger_level,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    if three_inlinks:
        W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(clearance_timesteps)
    _prepare_network(W)
    return W


def _make_vehicle(W, orig_name, name, dest="dest", departure_time=0):
    return W.addVehicle(orig_name, dest, departure_time, name=name)


def _setup_arrived_vehicle(
    merge,
    veh,
    link,
    out_link,
    earliest,
    arrival_time,
    tiebreaker,
    x,
    *,
    move_remain=0.0,
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.move_remain = move_remain
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps[merge.name] = earliest
    veh.order_control_node_arrival_times[merge.name] = arrival_time
    veh.order_control_node_arrival_tiebreakers[merge.name] = tiebreaker
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _begin_arrived_current_visit_for_test(
    veh,
    merge,
    link,
    earliest,
    arrival_time,
    tiebreaker,
):
    assert veh.link is link
    assert link.end_node is merge
    assert merge.order_control_eligible is True
    assert merge.order_control_type != "none"
    assert veh.order_control_node_arrival_times[merge.name] == arrival_time
    assert veh.order_control_node_arrival_tiebreakers[merge.name] == tiebreaker
    assert veh.order_control_earliest_arrival_timesteps[merge.name] == earliest

    veh.begin_order_control_visit_on_link_entry()

    veh.order_control_earliest_arrival_timesteps[merge.name] = earliest
    veh.order_control_current_visit["earliest_arrival_timestep"] = earliest
    veh.order_control_current_visit["arrival_time"] = arrival_time
    veh.order_control_current_visit["arrival_tiebreaker"] = tiebreaker

    current_visit = veh.order_control_current_visit
    assert current_visit is not None
    assert current_visit["node"] is merge
    assert current_visit["inlink"] is link
    assert current_visit["visit_id"] == veh.order_control_visit_id
    assert current_visit["earliest_arrival_timestep"] == earliest
    assert current_visit["arrival_time"] == arrival_time
    assert current_visit["arrival_tiebreaker"] == tiebreaker
    assert current_visit["batch_assignment"] is None
    assert veh.order_control_node_arrival_times[merge.name] == arrival_time
    assert veh.order_control_node_arrival_tiebreakers[merge.name] == tiebreaker


def _install_call_wrappers(merge):
    state = {
        "transfer_batch_calls": [],
        "fcfs_calls": [],
        "standard_transfer_markers": [],
        "orig_transfer_batch": merge.transfer_batch,
        "orig_transfer_fcfs": merge.transfer_fcfs_clearance,
        "orig_transfer": merge.transfer,
    }

    def wrap_transfer_batch():
        state["transfer_batch_calls"].append(merge.W.T)
        return state["orig_transfer_batch"]()

    def wrap_transfer_fcfs():
        state["fcfs_calls"].append(merge.W.T)
        return state["orig_transfer_fcfs"]()

    def wrap_transfer():
        before_incoming = list(merge.incoming_vehicles)
        uses_order_control_branch = (
            merge.order_control_eligible
            and merge.order_control_type in ("fcfs", "batch")
        )
        result = state["orig_transfer"]()
        if not uses_order_control_branch and before_incoming:
            for veh in before_incoming:
                if veh not in merge.incoming_vehicles and veh.link is not None:
                    if veh.link.name == "out":
                        state["standard_transfer_markers"].append(
                            (merge.W.T, veh.name)
                        )
        return result

    merge.transfer_batch = wrap_transfer_batch
    merge.transfer_fcfs_clearance = wrap_transfer_fcfs
    merge.transfer = wrap_transfer
    return state


def _restore_call_wrappers(merge, state):
    merge.transfer_batch = state["orig_transfer_batch"]
    merge.transfer_fcfs_clearance = state["orig_transfer_fcfs"]
    merge.transfer = state["orig_transfer"]


def _exec_one_timestep(W):
    W.exec_simulation(duration_t2=1)


def _run_one_timestep(W):
    _exec_one_timestep(W)


def test_batch_node_calls_transfer_batch_once():
    W = _build_merge_network("int_batch_branch", merge_type="batch")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    state = _install_call_wrappers(merge)
    try:
        result = merge.transfer()
        assert result is None
        assert state["transfer_batch_calls"] == [merge.W.T]
        assert state["fcfs_calls"] == []
        assert state["standard_transfer_markers"] == []
        assert veh.order_control_batch_assignments.get("merge") == 0
        assert veh.link is out
    finally:
        _restore_call_wrappers(merge, state)


def test_fcfs_node_calls_fcfs_once():
    W = _build_merge_network("int_fcfs_branch", merge_type="fcfs")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    _begin_arrived_current_visit_for_test(veh, merge, link1, 0, 10.0, 0.1)
    state = _install_call_wrappers(merge)
    try:
        result = merge.transfer()
        assert result is None
        assert state["fcfs_calls"] == [merge.W.T]
        assert state["transfer_batch_calls"] == []
        assert "merge" not in veh.order_control_batch_assignments
        assert veh.link is out
    finally:
        _restore_call_wrappers(merge, state)


def test_standard_node_eligible_false():
    W = _build_merge_network("int_std_ineligible", merge_type="batch")
    merge = W.get_node("merge")
    merge.order_control_eligible = False
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    state = _install_call_wrappers(merge)
    try:
        merge.transfer()
        assert state["transfer_batch_calls"] == []
        assert state["fcfs_calls"] == []
        assert state["standard_transfer_markers"] == [(merge.W.T, "A1")]
        assert veh.link is out
    finally:
        _restore_call_wrappers(merge, state)


def test_standard_node_type_none():
    W = _build_merge_network("int_std_none", merge_type="none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    state = _install_call_wrappers(merge)
    try:
        merge.transfer()
        assert state["transfer_batch_calls"] == []
        assert state["fcfs_calls"] == []
        assert state["standard_transfer_markers"] == [(merge.W.T, "A1")]
        assert veh.link is out
    finally:
        _restore_call_wrappers(merge, state)


def test_simulation_timeline_arrival_formation_transfer():
    W = _build_merge_network(
        "int_timeline",
        merge_type="batch",
        batch_size=1,
        t_trigger_level=0,
    )
    merge = W.get_node("merge")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1", departure_time=0)

    events = []
    orig_transfer = merge.transfer
    orig_transfer_batch = merge.transfer_batch

    def wrap_transfer():
        events.append(
            ("transfer", W.T, veh in merge.incoming_vehicles)
        )
        return orig_transfer()

    def wrap_transfer_batch():
        events.append(("transfer_batch", W.T))
        return orig_transfer_batch()

    merge.transfer = wrap_transfer
    merge.transfer_batch = wrap_transfer_batch

    try:
        while W.check_simulation_ongoing() and veh.link is not out:
            _exec_one_timestep(W)

        assert "merge" in veh.order_control_node_arrival_times
        arrival_timestep = int(
            round(veh.order_control_node_arrival_times["merge"] / W.DELTAT)
        )
        first_transfer_timestep = arrival_timestep + 1
        transfer_events = [event for event in events if event[0] == "transfer"]
        batch_events = [event for event in events if event[0] == "transfer_batch"]

        assert any(
            timestep == arrival_timestep and in_incoming is False
            for timestep, in_incoming in (
                (item[1], item[2]) for item in transfer_events
            )
        )
        assert ("transfer_batch", first_transfer_timestep) in batch_events
        assert veh.order_control_batch_assignments.get("merge") == 0
        assert veh.link is out
        assert veh not in merge.incoming_vehicles
        assert not any(
            event[1] > first_transfer_timestep for event in batch_events
        )
    finally:
        merge.transfer = orig_transfer
        merge.transfer_batch = orig_transfer_batch


def test_capacity_blocked_batch_vehicle_reregistration():
    W = _build_merge_network(
        "int_capacity_rereg",
        merge_type="batch",
        batch_size=1,
        t_trigger_level=0,
    )
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(
        merge,
        veh,
        link1,
        out,
        0,
        10.0,
        0.1,
        200.0,
        move_remain=5.0,
    )
    _begin_arrived_current_visit_for_test(veh, merge, link1, 0, 10.0, 0.1)
    out.capacity_in_remain = 0

    merge.transfer()
    assert veh.order_control_batch_assignments.get("merge") == 0
    assert veh.link is link1
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [veh]
    assert veh not in merge.incoming_vehicles

    visit_id_before = veh.order_control_current_visit["visit_id"]
    arrival_time_before = veh.order_control_current_visit["arrival_time"]
    arrival_tiebreaker_before = veh.order_control_current_visit["arrival_tiebreaker"]
    first_hist_time_before = veh.order_control_node_arrival_times["merge"]
    first_hist_tiebreaker_before = veh.order_control_node_arrival_tiebreakers["merge"]
    veh.carfollow()
    veh.update()
    assert veh.order_control_current_visit["visit_id"] == visit_id_before
    assert veh.order_control_current_visit["arrival_time"] == arrival_time_before
    assert veh.order_control_current_visit["arrival_tiebreaker"] == arrival_tiebreaker_before
    assert veh.order_control_node_arrival_times["merge"] == first_hist_time_before
    assert veh.order_control_node_arrival_tiebreakers["merge"] == first_hist_tiebreaker_before
    assert veh in merge.incoming_vehicles

    out.capacity_in_remain = 1e6
    merge.flow_capacity_remain = 1e6
    link1.capacity_out_remain = 1e6
    merge.transfer()
    assert veh.link is out
    assert len(merge.order_control_batch_service_queue) == 0


def test_service_queue_stop_reregistration():
    W = _build_merge_network(
        "int_queue_stop",
        merge_type="batch",
        batch_size=1,
        t_trigger_level=0,
        clearance_timesteps=1,
    )
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    merge.W.T = 10
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10

    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0, move_remain=5.0)
    _begin_arrived_current_visit_for_test(b1, merge, link2, 0, 10.0, 0.2)
    a1.order_control_batch_assignments["merge"] = 0
    b1.order_control_batch_assignments["merge"] = 1
    merge.order_control_batch_service_queue.append(
        {"batch_id": 0, "inlink": link1, "vehicles": []}
    )
    merge.order_control_batch_service_queue.append(
        {"batch_id": 1, "inlink": link2, "vehicles": [b1]}
    )
    merge.incoming_vehicles = [b1]

    merge.transfer()
    assert b1.link.name == "link2"
    assert b1.order_control_batch_assignments.get("merge") == 1
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [b1]
    assert b1 not in merge.incoming_vehicles

    b1.carfollow()
    b1.update()
    assert b1 in merge.incoming_vehicles

    merge.W.T = 12
    merge.transfer()
    assert b1.link is out
    assert len(merge.order_control_batch_service_queue) == 0


def test_t_trigger_out_of_range_unbatched_carryover():
    W = _build_merge_network("int_ttrigger_out", batch_size=3, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")

    trigger = _make_vehicle(W, "orig1", "A1")
    late = _make_vehicle(W, "orig1", "A_late")
    _setup_arrived_vehicle(merge, trigger, link1, out, 5, 10.0, 0.1, 200.0, move_remain=5.0)
    _setup_arrived_vehicle(merge, late, link1, out, 20, 11.0, 0.2, 180.0)
    _begin_arrived_current_visit_for_test(late, merge, link1, 20, 11.0, 0.2)

    t_trigger = merge.estimate_order_control_batch_t_trigger_level_0(trigger)
    assert late.order_control_earliest_arrival_timesteps["merge"] > t_trigger

    merge.transfer()
    assert trigger.order_control_batch_assignments.get("merge") == 0
    assert "merge" not in late.order_control_batch_assignments
    assert late.link.name == "link1"
    assert late not in merge.incoming_vehicles

    late.x = 200.0
    late.move_remain = 5.0
    late.carfollow()
    late.update()
    assert late in merge.incoming_vehicles
    assert "merge" not in late.order_control_batch_assignments


def test_n_exceeded_unbatched_carryover():
    W = _build_merge_network("int_n_exceeded", batch_size=2, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")

    vehicles = []
    for index in range(4):
        veh = _make_vehicle(W, "orig1", f"B{index + 1}")
        _setup_arrived_vehicle(
            merge,
            veh,
            link1,
            out,
            0,
            float(index),
            0.1 + index * 0.01,
            200.0,
        )
        vehicles.append(veh)

    _begin_arrived_current_visit_for_test(
        vehicles[2],
        merge,
        link1,
        0,
        vehicles[2].order_control_node_arrival_times["merge"],
        vehicles[2].order_control_node_arrival_tiebreakers["merge"],
    )

    out.capacity_in_remain = 0
    merge.transfer()
    registered = merge.order_control_batch_service_queue[0]["vehicles"]
    assert [veh.name for veh in registered] == ["B1", "B2"]
    assert vehicles[2].name not in [veh.name for veh in registered]
    assert "merge" not in vehicles[2].order_control_batch_assignments
    assert vehicles[2].link.name == "link1"
    assert vehicles[2] not in merge.incoming_vehicles

    vehicles[2].x = 200.0
    vehicles[2].move_remain = 5.0
    vehicles[2].carfollow()
    vehicles[2].update()
    assert vehicles[2] in merge.incoming_vehicles
    assert "merge" not in vehicles[2].order_control_batch_assignments


def test_formation_cutoff_other_direction_unbatched():
    W = _build_merge_network("int_cutoff", batch_size=2, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    a1 = _make_vehicle(W, "orig1", "A1")
    a2 = _make_vehicle(W, "orig1", "A2")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    _setup_arrived_vehicle(merge, a2, link1, out, 0, 10.1, 0.11, 180.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0, move_remain=5.0)
    _begin_arrived_current_visit_for_test(b1, merge, link2, 0, 10.0, 0.2)

    out.capacity_in_remain = 0
    merge.transfer()
    assert len(merge.order_control_batch_service_queue) == 1
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [a1, a2]
    assert "merge" not in b1.order_control_batch_assignments
    assert b1.link.name == "link2"
    assert b1 not in merge.incoming_vehicles

    b1.carfollow()
    b1.update()
    assert b1 in merge.incoming_vehicles
    assert "merge" not in b1.order_control_batch_assignments


def test_three_direction_simultaneous_arrival():
    W = _build_merge_network(
        "int_three_dir",
        batch_size=1,
        t_trigger_level=0,
        three_inlinks=True,
    )
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")

    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    c1 = _make_vehicle(W, "orig3", "C1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0, move_remain=5.0)
    _setup_arrived_vehicle(merge, c1, link3, out, 0, 10.0, 0.3, 200.0, move_remain=5.0)

    form_calls = []
    orig_form = merge.form_order_control_batch

    def wrap_form(t_trigger_level, max_batch_size):
        form_calls.append(1)
        return orig_form(t_trigger_level, max_batch_size)

    merge.form_order_control_batch = wrap_form
    try:
        assert merge.get_order_control_batch_trigger_candidates()[0] is a1
        out.capacity_in_remain = 0
        merge.transfer()
    finally:
        merge.form_order_control_batch = orig_form

    assert form_calls == [1]
    assert a1.order_control_batch_assignments.get("merge") == 0
    assert "merge" not in b1.order_control_batch_assignments
    assert "merge" not in c1.order_control_batch_assignments
    assert c1.link.name == "link3"
    assert c1 not in merge.incoming_vehicles


def test_a1_b1_two_direction_level0_level1_trigger():
    W = _build_merge_network(
        "int_a1_b1",
        batch_size=1,
        t_trigger_level=1,
        clearance_timesteps=1,
    )
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    merge.W.T = 11

    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 10.0, 0.2, 200.0, move_remain=5.0)
    _begin_arrived_current_visit_for_test(b1, merge, link2, 0, 10.0, 0.2)

    merge.transfer()
    assert a1.link is out
    assert b1.link.name == "link2"
    assert merge.last_order_control_inlink is link1
    assert merge.last_order_control_entry_timestep == 11
    assert "merge" not in b1.order_control_batch_assignments

    b1.carfollow()
    b1.update()
    assert b1 in merge.incoming_vehicles

    # Timeline: A1/B1 Node初回到着timestep=10, A1形成・実通過timestep=11.
    # A1通過後 last_order_control_inlink=link1, last_order_control_entry_timestep=11.
    # B1はlink2所属のため異方向切替clearanceが必要.
    # clearance_timesteps=1 なので最早切替可能timestep=13.
    b1_level0 = merge.estimate_order_control_batch_t_trigger_level_0(b1)
    clearance_floor = (
        merge.last_order_control_entry_timestep
        + merge.order_control_clearance_timesteps
        + 1
    )
    b1_level1 = merge.estimate_order_control_batch_t_trigger_level_1(b1)

    assert b1_level0 == 11
    assert clearance_floor == 13
    assert b1_level1 == 13
    assert b1_level1 == max(b1_level0, clearance_floor)
    assert b1_level1 > b1_level0
    assert merge.get_order_control_batch_trigger_candidates()[0] is b1


def _build_comparison_world(order_control_type):
    W = World(
        name=f"n1_compare_{order_control_type}",
        deltan=1,
        tmax=300,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("merge", 1, 1)
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=400, free_flow_speed=20, number_of_lanes=1)
    W.infer_order_control_eligible_nodes()
    W.set_order_control_clearance_timesteps(1)
    if order_control_type == "batch":
        W.set_order_control_for_nodes(
            ["merge"],
            order_control_type="batch",
            batch_size=1,
            order_control_batch_t_trigger_level=1,
        )
    else:
        W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")
    return W


def _vehicle_plans():
    return [
        ("orig1", "A1", 0.0),
        ("orig2", "B1", 0.0),
        ("orig1", "A2", 20.0),
        ("orig2", "B2", 20.0),
        ("orig1", "A3", 40.0),
        ("orig2", "B3", 40.0),
    ]


def _count_direction_changes(pass_inlink_order):
    direction_changes = 0
    prev_inlink = None
    for inlink_name in pass_inlink_order:
        if prev_inlink is not None and inlink_name != prev_inlink:
            direction_changes += 1
        prev_inlink = inlink_name
    return direction_changes


def _run_comparison_simulation(order_control_type):
    W = _build_comparison_world(order_control_type)
    merge = W.get_node("merge")
    out = W.get_link("out")
    vehicles = {}
    for orig, name, departure in _vehicle_plans():
        vehicles[name] = W.addVehicle(orig, "dest", departure, name=name)

    vehicle_names = set(vehicles)
    pass_timesteps = {}
    pass_vehicle_order = []
    pass_inlink_order = []
    trip_end_timesteps = {}
    node_history = []

    while W.check_simulation_ongoing():
        link_before = {
            name: vehicles[name].link for name in vehicles
        }
        W.exec_simulation(duration_t2=1)
        for name, veh in vehicles.items():
            previous_link = link_before[name]
            if (
                name not in pass_timesteps
                and veh.link is out
                and previous_link is not out
            ):
                pass_timesteps[name] = W.T
                pass_vehicle_order.append(name)
                pass_inlink_order.append(previous_link.name)
            if name not in trip_end_timesteps and veh.state == "end":
                trip_end_timesteps[name] = W.T

        inlink = merge.last_order_control_inlink
        inlink_name = inlink.name if inlink is not None else None
        node_history.append(
            (
                W.T,
                inlink_name,
                merge.last_order_control_entry_timestep,
            )
        )

    merge_arrivals = {
        name: vehicles[name].order_control_node_arrival_times.get("merge")
        for name in vehicles
    }

    completed = sum(1 for veh in vehicles.values() if veh.state == "end")
    travel_times = [
        veh.travel_time for veh in vehicles.values() if veh.state == "end"
    ]
    total_travel_time = sum(travel_times)
    avg_travel_time = total_travel_time / max(len(travel_times), 1)
    direction_changes = _count_direction_changes(pass_inlink_order)

    return {
        "vehicle_names": vehicle_names,
        "pass_timesteps": pass_timesteps,
        "pass_vehicle_order": pass_vehicle_order,
        "pass_inlink_order": pass_inlink_order,
        "merge_arrivals": merge_arrivals,
        "trip_end_timesteps": trip_end_timesteps,
        "node_history": node_history,
        "completed": completed,
        "total_travel_time": total_travel_time,
        "avg_travel_time": avg_travel_time,
        "direction_changes": direction_changes,
        "clearance_timesteps": merge.order_control_clearance_timesteps,
        "vehicles": vehicles,
    }


def _assert_clearance_wait_occurred(result):
    pass_events = list(
        zip(
            result["pass_vehicle_order"],
            [result["pass_timesteps"][name] for name in result["pass_vehicle_order"]],
            result["pass_inlink_order"],
        )
    )
    clearance_timesteps = result["clearance_timesteps"]
    clearance_waits = []
    for index in range(1, len(pass_events)):
        prev_name, prev_timestep, prev_inlink = pass_events[index - 1]
        curr_name, curr_timestep, curr_inlink = pass_events[index]
        if prev_inlink != curr_inlink:
            gap = curr_timestep - prev_timestep
            clearance_waits.append(
                (prev_name, curr_name, prev_timestep, curr_timestep, gap)
            )
            assert gap > clearance_timesteps, (
                "Direction-change clearance wait violated for "
                f"{curr_name}: previous pass {prev_name} at timestep "
                f"{prev_timestep} from {prev_inlink}, current pass at "
                f"{curr_timestep} from {curr_inlink}, gap={gap}, "
                f"clearance_timesteps={clearance_timesteps}"
            )
    assert clearance_waits, (
        "Expected at least one direction-change clearance wait, "
        f"but pass_inlink_order={result['pass_inlink_order']!r}"
    )


def _assert_n1_batch_fcfs_equivalence(batch_result, fcfs_result):
    batch_names = batch_result["vehicle_names"]
    fcfs_names = fcfs_result["vehicle_names"]
    if batch_names != fcfs_names:
        raise AssertionError(
            "Vehicle-name set mismatch: "
            f"batch={sorted(batch_names)!r} fcfs={sorted(fcfs_names)!r}"
        )

    for name in sorted(batch_names):
        batch_arrival = batch_result["merge_arrivals"].get(name)
        fcfs_arrival = fcfs_result["merge_arrivals"].get(name)
        if batch_arrival != fcfs_arrival:
            raise AssertionError(
                "First merge-arrival mismatch at vehicle "
                f"{name}: batch={batch_arrival!r} fcfs={fcfs_arrival!r}"
            )

    batch_pass_names = set(batch_result["pass_timesteps"])
    fcfs_pass_names = set(fcfs_result["pass_timesteps"])
    if batch_pass_names != batch_names:
        missing = sorted(batch_names - batch_pass_names)
        raise AssertionError(
            "BATCH pass_timesteps missing vehicles: "
            f"{missing!r}; recorded={sorted(batch_pass_names)!r}"
        )
    if fcfs_pass_names != fcfs_names:
        missing = sorted(fcfs_names - fcfs_pass_names)
        raise AssertionError(
            "FCFS pass_timesteps missing vehicles: "
            f"{missing!r}; recorded={sorted(fcfs_pass_names)!r}"
        )
    if batch_pass_names != fcfs_pass_names:
        raise AssertionError(
            "Outlink-entry vehicle-set mismatch: "
            f"batch={sorted(batch_pass_names)!r} "
            f"fcfs={sorted(fcfs_pass_names)!r}"
        )

    for name in sorted(batch_names):
        batch_pass = batch_result["pass_timesteps"][name]
        fcfs_pass = fcfs_result["pass_timesteps"][name]
        if batch_pass != fcfs_pass:
            raise AssertionError(
                "First outlink-entry timestep mismatch at vehicle "
                f"{name}: batch={batch_pass} fcfs={fcfs_pass}"
            )

    if batch_result["pass_vehicle_order"] != fcfs_result["pass_vehicle_order"]:
        raise AssertionError(
            "Outlink-entry vehicle-order mismatch: "
            f"batch={batch_result['pass_vehicle_order']!r} "
            f"fcfs={fcfs_result['pass_vehicle_order']!r}"
        )

    if batch_result["pass_inlink_order"] != fcfs_result["pass_inlink_order"]:
        raise AssertionError(
            "Pass-inlink-order mismatch: "
            f"batch={batch_result['pass_inlink_order']!r} "
            f"fcfs={fcfs_result['pass_inlink_order']!r}"
        )

    batch_trip_end_names = set(batch_result["trip_end_timesteps"])
    fcfs_trip_end_names = set(fcfs_result["trip_end_timesteps"])
    if batch_trip_end_names != batch_names:
        missing = sorted(batch_names - batch_trip_end_names)
        raise AssertionError(
            "BATCH trip-end timesteps missing vehicles: "
            f"{missing!r}"
        )
    if fcfs_trip_end_names != fcfs_names:
        missing = sorted(fcfs_names - fcfs_trip_end_names)
        raise AssertionError(
            "FCFS trip-end timesteps missing vehicles: "
            f"{missing!r}"
        )

    for name in sorted(batch_names):
        batch_end = batch_result["trip_end_timesteps"].get(name)
        fcfs_end = fcfs_result["trip_end_timesteps"].get(name)
        if batch_end != fcfs_end:
            raise AssertionError(
                "First trip-end timestep mismatch at vehicle "
                f"{name}: batch={batch_end} fcfs={fcfs_end}"
            )

    if batch_result["node_history"] != fcfs_result["node_history"]:
        for index, (batch_entry, fcfs_entry) in enumerate(
            zip(batch_result["node_history"], fcfs_result["node_history"])
        ):
            if batch_entry != fcfs_entry:
                raise AssertionError(
                    "First node-history mismatch at index "
                    f"{index}: batch={batch_entry!r} fcfs={fcfs_entry!r}"
                )
        raise AssertionError(
            "Node-history length mismatch: "
            f"batch={len(batch_result['node_history'])} "
            f"fcfs={len(fcfs_result['node_history'])}"
        )

    if batch_result["direction_changes"] != fcfs_result["direction_changes"]:
        raise AssertionError(
            "Direction-change count mismatch: "
            f"batch={batch_result['direction_changes']} "
            f"fcfs={fcfs_result['direction_changes']}; "
            f"batch_inlinks={batch_result['pass_inlink_order']!r} "
            f"fcfs_inlinks={fcfs_result['pass_inlink_order']!r}"
        )

    if batch_result["completed"] != len(batch_names):
        raise AssertionError(
            "BATCH did not complete all vehicles: "
            f"completed={batch_result['completed']} "
            f"expected={len(batch_names)}"
        )
    if fcfs_result["completed"] != len(fcfs_names):
        raise AssertionError(
            "FCFS did not complete all vehicles: "
            f"completed={fcfs_result['completed']} "
            f"expected={len(fcfs_names)}"
        )

    if batch_result["completed"] != fcfs_result["completed"]:
        raise AssertionError(
            "Completed-trip count mismatch: "
            f"batch={batch_result['completed']} fcfs={fcfs_result['completed']}"
        )
    if batch_result["total_travel_time"] != fcfs_result["total_travel_time"]:
        raise AssertionError(
            "Total travel time mismatch: "
            f"batch={batch_result['total_travel_time']} "
            f"fcfs={fcfs_result['total_travel_time']}"
        )
    if batch_result["avg_travel_time"] != fcfs_result["avg_travel_time"]:
        raise AssertionError(
            "Average travel time mismatch: "
            f"batch={batch_result['avg_travel_time']} "
            f"fcfs={fcfs_result['avg_travel_time']}"
        )


def test_n1_batch_vs_fcfs_equivalence():
    batch_result = _run_comparison_simulation("batch")
    fcfs_result = _run_comparison_simulation("fcfs")

    _assert_clearance_wait_occurred(batch_result)
    _assert_clearance_wait_occurred(fcfs_result)
    _assert_n1_batch_fcfs_equivalence(batch_result, fcfs_result)


TESTS = [
    test_batch_node_calls_transfer_batch_once,
    test_fcfs_node_calls_fcfs_once,
    test_standard_node_eligible_false,
    test_standard_node_type_none,
    test_simulation_timeline_arrival_formation_transfer,
    test_capacity_blocked_batch_vehicle_reregistration,
    test_service_queue_stop_reregistration,
    test_t_trigger_out_of_range_unbatched_carryover,
    test_n_exceeded_unbatched_carryover,
    test_formation_cutoff_other_direction_unbatched,
    test_three_direction_simultaneous_arrival,
    test_a1_b1_two_direction_level0_level1_trigger,
    test_n1_batch_vs_fcfs_equivalence,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control batch Node.transfer integration tests passed.")
