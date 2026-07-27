# Verify BATCH transfer orchestration at order-control nodes.
#
# Run from the repository root:
#   python tests_order_control_batch_transfer.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_network(name="batch_transfer", batch_size=1, t_trigger_level=0):
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
        order_control_eligible=True,
        order_control_type="batch",
        batch_size=batch_size,
        order_control_batch_t_trigger_level=t_trigger_level,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _make_vehicle(W, orig_name, name, dest="dest"):
    return W.addVehicle(orig_name, dest, 0, name=name)


def _sync_arrived_current_visit(veh, merge, link, earliest, arrival_time, tiebreaker):
    assert veh.link is link
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    visit = veh.order_control_current_visit
    if visit is None:
        veh.order_control_current_visit = {
            "visit_id": veh.order_control_visit_id,
            "node": merge,
            "inlink": link,
            "earliest_arrival_timestep": earliest,
            "arrival_time": arrival_time,
            "arrival_tiebreaker": tiebreaker,
            "batch_assignment": None,
        }
    else:
        assert visit.get("node") is merge
        assert visit.get("inlink") is link
        visit["visit_id"] = veh.order_control_visit_id
        visit["node"] = merge
        visit["inlink"] = link
        visit["earliest_arrival_timestep"] = earliest
        visit["arrival_time"] = arrival_time
        visit["arrival_tiebreaker"] = tiebreaker
        visit["batch_assignment"] = None


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
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    _sync_arrived_current_visit(
        veh,
        merge,
        link,
        earliest,
        arrival_time,
        tiebreaker,
    )
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


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


def _queue_unit_names(merge):
    return [
        (unit["batch_id"], [veh.name for veh in unit["vehicles"]])
        for unit in merge.order_control_batch_service_queue
    ]


def _install_wrappers(merge):
    state = {
        "calls": [],
        "orig_form": merge.form_order_control_batch,
        "orig_serve": merge.serve_order_control_batch_service_queue,
    }

    def wrap_form(t_trigger_level, max_batch_size):
        state["calls"].append(
            ("form", t_trigger_level, max_batch_size)
        )
        return state["orig_form"](t_trigger_level, max_batch_size)

    def wrap_serve():
        state["calls"].append(("serve",))
        return state["orig_serve"]()

    merge.form_order_control_batch = wrap_form
    merge.serve_order_control_batch_service_queue = wrap_serve
    return state


def _restore_wrappers(merge, state):
    merge.form_order_control_batch = state["orig_form"]
    merge.serve_order_control_batch_service_queue = state["orig_serve"]


def test_call_order_count_and_arguments():
    W = _build_network("bt_order", batch_size=3, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)

    state = _install_wrappers(merge)
    try:
        result = merge.transfer_batch()
    finally:
        _restore_wrappers(merge, state)

    assert state["calls"] == [("form", 0, 3), ("serve",)]
    assert result["formation_result"] == "batch_formed"
    assert result["transferred_vehicle_count"] == 1


def test_serve_called_once_even_when_zero_transfers():
    W = _build_network("bt_serve_once")
    merge = W.get_node("merge")
    serve_calls = []
    orig_serve = merge.serve_order_control_batch_service_queue

    def wrap_serve():
        serve_calls.append(True)
        return 0

    merge.serve_order_control_batch_service_queue = wrap_serve
    try:
        result = merge.transfer_batch()
    finally:
        merge.serve_order_control_batch_service_queue = orig_serve

    assert len(serve_calls) == 1
    assert result == {
        "formation_result": "no_trigger_candidate",
        "transferred_vehicle_count": 0,
    }


def test_return_no_trigger_zero_transfer():
    W = _build_network("bt_ret_nt0")
    merge = W.get_node("merge")
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue
    merge.form_order_control_batch = (
        lambda t_trigger_level, max_batch_size: "no_trigger_candidate"
    )
    merge.serve_order_control_batch_service_queue = lambda: 0
    try:
        result = merge.transfer_batch()
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert result == {
        "formation_result": "no_trigger_candidate",
        "transferred_vehicle_count": 0,
    }


def test_return_no_trigger_nonzero_transfer():
    W = _build_network("bt_ret_nt2")
    merge = W.get_node("merge")
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue
    merge.form_order_control_batch = (
        lambda t_trigger_level, max_batch_size: "no_trigger_candidate"
    )
    merge.serve_order_control_batch_service_queue = lambda: 2
    try:
        result = merge.transfer_batch()
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert result == {
        "formation_result": "no_trigger_candidate",
        "transferred_vehicle_count": 2,
    }


def test_return_batch_formed_zero_transfer():
    W = _build_network("bt_ret_bf0")
    merge = W.get_node("merge")
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue
    merge.form_order_control_batch = (
        lambda t_trigger_level, max_batch_size: "batch_formed"
    )
    merge.serve_order_control_batch_service_queue = lambda: 0
    try:
        result = merge.transfer_batch()
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert result == {
        "formation_result": "batch_formed",
        "transferred_vehicle_count": 0,
    }


def test_return_batch_formed_nonzero_transfer():
    W = _build_network("bt_ret_bf3")
    merge = W.get_node("merge")
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue
    merge.form_order_control_batch = (
        lambda t_trigger_level, max_batch_size: "batch_formed"
    )
    merge.serve_order_control_batch_service_queue = lambda: 3
    try:
        result = merge.transfer_batch()
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert result == {
        "formation_result": "batch_formed",
        "transferred_vehicle_count": 3,
    }


def test_serve_called_when_no_trigger_candidate():
    W = _build_network("bt_serve_nt")
    merge = W.get_node("merge")
    serve_calls = []
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue

    def wrap_form(t_trigger_level, max_batch_size):
        return "no_trigger_candidate"

    def wrap_serve():
        serve_calls.append(True)
        return 0

    merge.form_order_control_batch = wrap_form
    merge.serve_order_control_batch_service_queue = wrap_serve
    try:
        merge.transfer_batch()
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert len(serve_calls) == 1


def test_serve_called_when_batch_formed():
    W = _build_network("bt_serve_bf")
    merge = W.get_node("merge")
    serve_calls = []
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue

    def wrap_form(t_trigger_level, max_batch_size):
        return "batch_formed"

    def wrap_serve():
        serve_calls.append(True)
        return 0

    merge.form_order_control_batch = wrap_form
    merge.serve_order_control_batch_service_queue = wrap_serve
    try:
        merge.transfer_batch()
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert len(serve_calls) == 1


def test_no_trigger_transfers_from_existing_queue():
    W = _build_network("bt_existing_queue")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    batched = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, batched, link1, out, 0, 10.0, 0.1, 200.0, move_remain=5.0)
    _register_service_unit(merge, 0, link1, [batched])

    result = merge.transfer_batch()
    assert result["formation_result"] == "no_trigger_candidate"
    assert result["transferred_vehicle_count"] == 1
    assert batched.link is out


def test_batch_formed_zero_transfer_success():
    W = _build_network("bt_bf0_real", batch_size=2, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    lead = _make_vehicle(W, "orig1", "A1")
    follow = _make_vehicle(W, "orig1", "A2")
    _setup_arrived_vehicle(merge, lead, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, follow, link1, out, 0, 11.0, 0.2, 150.0)
    out.capacity_in_remain = 0
    assert merge.order_control_batch_next_id == 0

    result = merge.transfer_batch()
    assert result == {
        "formation_result": "batch_formed",
        "transferred_vehicle_count": 0,
    }
    assert lead.link is link1
    assert follow.link is link1
    assert lead not in out.vehicles
    assert follow not in out.vehicles
    assert len(merge.order_control_batch_service_queue) == 1
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [lead, follow]
    assert lead.order_control_batch_assignments["merge"] == 0
    assert follow.order_control_batch_assignments["merge"] == 0
    assert merge.incoming_vehicles == []


def test_incoming_vehicles_cleared_on_success():
    W = _build_network("bt_incoming_clear", batch_size=2, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    batched = _make_vehicle(W, "orig1", "A1")
    unbatched = _make_vehicle(W, "orig1", "U1")
    _setup_arrived_vehicle(merge, batched, link1, out, 0, 10.0, 0.1, 200.0)
    unbatched.link = link1
    unbatched.state = "run"
    unbatched.x = 150.0
    unbatched.v = 20.0
    # Keep U1 outside the trigger candidates; this test only verifies incoming cleanup.
    unbatched.route_next_link = None
    unbatched.order_control_earliest_arrival_timesteps["merge"] = 0
    link1.vehicles.append(unbatched)
    merge.incoming_vehicles.append(unbatched)
    out.capacity_in_remain = 0
    _register_service_unit(merge, 0, link1, [batched])

    assert len(merge.incoming_vehicles) == 2
    merge.transfer_batch()
    assert merge.incoming_vehicles == []
    assert batched.link is link1
    assert unbatched.link is link1
    assert batched in link1.vehicles
    assert unbatched in link1.vehicles
    assert batched.order_control_batch_assignments["merge"] == 0
    assert "merge" not in unbatched.order_control_batch_assignments
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [batched]


def test_formation_exception_no_serve_no_clear():
    W = _build_network("bt_form_exc")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    before_incoming = list(merge.incoming_vehicles)
    expected_error = ValueError("formation test")
    serve_calls = []
    orig_form = merge.form_order_control_batch
    orig_serve = merge.serve_order_control_batch_service_queue

    def wrap_form(t_trigger_level, max_batch_size):
        raise expected_error

    def wrap_serve():
        serve_calls.append(True)
        return 0

    merge.form_order_control_batch = wrap_form
    merge.serve_order_control_batch_service_queue = wrap_serve
    try:
        try:
            merge.transfer_batch()
            assert False, "expected ValueError"
        except ValueError as exc:
            assert exc is expected_error
    finally:
        merge.form_order_control_batch = orig_form
        merge.serve_order_control_batch_service_queue = orig_serve

    assert serve_calls == []
    assert merge.incoming_vehicles == before_incoming


def test_serve_exception_no_clear():
    W = _build_network("bt_serve_exc")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    _setup_arrived_vehicle(merge, veh, link1, out, 0, 10.0, 0.1, 200.0)
    before_incoming = list(merge.incoming_vehicles)
    expected_error = RuntimeError("serve test")
    orig_serve = merge.serve_order_control_batch_service_queue

    def wrap_serve():
        raise expected_error

    merge.serve_order_control_batch_service_queue = wrap_serve
    try:
        try:
            merge.transfer_batch()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert exc is expected_error
    finally:
        merge.serve_order_control_batch_service_queue = orig_serve

    assert merge.incoming_vehicles == before_incoming


def test_single_form_and_serve_call_with_multiple_unbatched():
    W = _build_network("bt_single_call", batch_size=5, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    vehicles = []
    for idx in range(3):
        veh = _make_vehicle(W, "orig1", f"A{idx}")
        _setup_arrived_vehicle(
            merge, veh, link1, out, idx, 10.0 + idx, 0.1 + idx, 200.0 - idx * 20
        )
        vehicles.append(veh)
    extra = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, extra, link2, out, 0, 20.0, 0.9, 200.0)

    state = _install_wrappers(merge)
    try:
        merge.transfer_batch()
    finally:
        _restore_wrappers(merge, state)

    form_calls = [call for call in state["calls"] if call[0] == "form"]
    serve_calls = [call for call in state["calls"] if call[0] == "serve"]
    assert len(form_calls) == 1
    assert len(serve_calls) == 1


def test_timeline_arrival_formation_transfer():
    W = _build_network("bt_timeline", batch_size=1, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    arrival_timestep = 10
    arrival_seconds = arrival_timestep * merge.W.DELTAT
    first_transfer_timestep = arrival_timestep + 1
    merge.W.T = arrival_timestep

    veh.link = link1
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.move_remain = 5.0
    veh.route_next_link = out
    veh.order_control_earliest_arrival_timesteps["merge"] = arrival_timestep
    link1.vehicles.append(veh)

    assert veh not in merge.incoming_vehicles
    result_t = merge.transfer_batch()
    assert result_t["formation_result"] == "no_trigger_candidate"
    assert result_t["transferred_vehicle_count"] == 0

    veh.order_control_node_arrival_times["merge"] = arrival_seconds
    veh.order_control_node_arrival_tiebreakers["merge"] = 0.1
    _sync_arrived_current_visit(
        veh,
        merge,
        link1,
        arrival_timestep,
        arrival_seconds,
        0.1,
    )
    merge.incoming_vehicles.append(veh)

    estimated_t_trigger = merge.estimate_order_control_batch_t_trigger_level_0(veh)
    assert estimated_t_trigger == first_transfer_timestep

    merge.W.T = first_transfer_timestep
    result_t1 = merge.transfer_batch()
    assert result_t1["formation_result"] == "batch_formed"
    assert result_t1["transferred_vehicle_count"] == 1
    assert veh.link is out
    assert merge.incoming_vehicles == []


def test_n1_same_call_formation_and_transfer():
    W = _build_network("bt_n1", batch_size=1, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = _make_vehicle(W, "orig1", "A1")
    arrival_timestep = 5
    merge.W.T = arrival_timestep + 1
    _setup_arrived_vehicle(
        merge,
        veh,
        link1,
        out,
        arrival_timestep,
        float(arrival_timestep),
        0.1,
        200.0,
        move_remain=5.0,
    )

    result = merge.transfer_batch()
    assert result["formation_result"] == "batch_formed"
    assert result["transferred_vehicle_count"] == 1
    assert veh.order_control_batch_assignments["merge"] == 0
    assert veh.link is out


def test_existing_queue_plus_new_formation():
    W = _build_network("bt_queue_append", batch_size=1, t_trigger_level=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")

    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    _setup_arrived_vehicle(merge, a1, link1, out, 0, 10.0, 0.1, 200.0)
    _setup_arrived_vehicle(merge, b1, link2, out, 0, 11.0, 0.2, 200.0)
    _register_service_unit(merge, 0, link1, [a1])
    _register_service_unit(merge, 1, link2, [b1])
    before_units = _queue_unit_names(merge)

    trigger = _make_vehicle(W, "orig1", "C1")
    _setup_arrived_vehicle(merge, trigger, link1, out, 0, 20.0, 0.9, 200.0)
    out.capacity_in_remain = 0

    result = merge.transfer_batch()
    assert result["formation_result"] == "batch_formed"
    assert result["transferred_vehicle_count"] == 0

    after_units = _queue_unit_names(merge)
    assert len(after_units) == 3
    assert after_units[:2] == before_units
    assert after_units[2][1] == ["C1"]
    assert merge.order_control_batch_service_queue[0]["vehicles"] == [a1]
    assert merge.order_control_batch_service_queue[1]["vehicles"] == [b1]


TESTS = [
    test_call_order_count_and_arguments,
    test_serve_called_once_even_when_zero_transfers,
    test_return_no_trigger_zero_transfer,
    test_return_no_trigger_nonzero_transfer,
    test_return_batch_formed_zero_transfer,
    test_return_batch_formed_nonzero_transfer,
    test_serve_called_when_no_trigger_candidate,
    test_serve_called_when_batch_formed,
    test_no_trigger_transfers_from_existing_queue,
    test_batch_formed_zero_transfer_success,
    test_incoming_vehicles_cleared_on_success,
    test_formation_exception_no_serve_no_clear,
    test_serve_exception_no_clear,
    test_single_form_and_serve_call_with_multiple_unbatched,
    test_timeline_arrival_formation_transfer,
    test_n1_same_call_formation_and_transfer,
    test_existing_queue_plus_new_formation,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control batch transfer tests passed.")
