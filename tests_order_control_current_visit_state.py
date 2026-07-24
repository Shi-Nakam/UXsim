# Verify Phase 4-6O current visit state at link entry for order-control vehicles.
#
# Run from the repository root:
#   python tests_order_control_current_visit_state.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import math

from uxsim import World


def expected_earliest_arrival_timestep(link_entry_timestep, link, W, tau_timesteps):
    free_flow_travel_timesteps = math.ceil((link.length / link.u) / W.DELTAT)
    return link_entry_timestep + free_flow_travel_timesteps + tau_timesteps


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_corridor_world(name="current_visit_corridor"):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("o", 0, 0)
    W.addNode("m", 1, 0)
    W.addNode("d", 2, 0)
    W.addLink("o_m", "o", "m", length=105, free_flow_speed=20, number_of_lanes=1)
    W.addLink("m_d", "m", "d", length=130, free_flow_speed=30, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_merge_world(name="current_visit_merge", *, order_control_type="fcfs"):
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
        order_control_type=order_control_type,
        batch_size=1,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(0)
    _prepare_network(W)
    return W


def _assert_current_visit_matches(
    veh,
    *,
    visit_id,
    node_name,
    inlink_name,
    earliest,
):
    visit = veh.order_control_current_visit
    assert visit is not None
    assert visit["visit_id"] == visit_id
    assert visit["node"].name == node_name
    assert visit["inlink"].name == inlink_name
    assert visit["earliest_arrival_timestep"] == earliest
    assert visit["arrival_time"] is None
    assert visit["arrival_tiebreaker"] is None
    assert visit["batch_assignment"] is None


def _assert_eligible_visit_after_link_entry(veh, W, outlink, visit_id_before):
    end_node = outlink.end_node
    assert veh.link is outlink
    assert veh.order_control_visit_id == visit_id_before + 1
    assert veh.order_control_current_visit is not None
    visit = veh.order_control_current_visit
    assert visit["visit_id"] == veh.order_control_visit_id
    assert visit["node"] is end_node
    assert visit["inlink"] is outlink
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, outlink, W, W.order_control_batch_tau_timesteps
    )
    assert visit["earliest_arrival_timestep"] == expected
    assert visit["arrival_time"] is None
    assert visit["arrival_tiebreaker"] is None
    assert visit["batch_assignment"] is None
    assert veh.order_control_earliest_arrival_timesteps[end_node.name] == expected


def _build_standard_to_eligible_world(name="current_visit_path_standard_eligible"):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0, signal=[30, 30])
    W.addNode("mid", 1, 0, signal=[30, 30])
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge2",
        2,
        0,
        order_control_eligible=True,
        order_control_type="fcfs",
    )
    W.addNode("dest", 3, 0)
    W.addLink(
        "in", "orig", "mid", length=200, free_flow_speed=20, number_of_lanes=1, signal_group=[0]
    )
    W.addLink(
        "out", "mid", "merge2", length=200, free_flow_speed=20, number_of_lanes=1, signal_group=[0]
    )
    W.addLink("link2", "orig2", "merge2", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out2", "merge2", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_two_merge_world(
    name="current_visit_two_merge",
    *,
    merge1_order_control_type="fcfs",
):
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
        "merge1",
        1,
        1,
        order_control_eligible=True,
        order_control_type=merge1_order_control_type,
        batch_size=1,
    )
    W.addNode("mid", 2, 1)
    W.addNode("orig3", 0, 4)
    W.addNode(
        "merge2",
        3,
        1,
        order_control_eligible=True,
        order_control_type="fcfs",
    )
    W.addNode("dest", 4, 1)
    W.addLink("link1", "orig1", "merge1", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge1", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("mid_link", "merge1", "mid", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", "merge2", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("mid_merge2", "mid", "merge2", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge2", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(0)
    _prepare_network(W)
    return W


def _build_revisit_world(name="current_visit_revisit"):
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
    W.addNode("mid", 2, 1)
    W.addNode("dest", 3, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "mid", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("mid_orig2", "mid", "orig2", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out2", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(0)
    _prepare_network(W)
    return W


def _advance_until_on_link(veh, link_name):
    while veh.link is None or veh.link.name != link_name:
        if not veh.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {link_name}")
        veh.W.exec_simulation(duration_t2=1)


def _setup_arrived_vehicle(
    merge,
    veh,
    link,
    out_link,
    *,
    x,
    earliest=0,
    arrival_time=10.0,
    tiebreaker=0.1,
    link_arrival_time=0.0,
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.link_arrival_time = link_arrival_time
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps[merge.name] = earliest
    veh.order_control_node_arrival_times[merge.name] = arrival_time
    veh.order_control_node_arrival_tiebreakers[merge.name] = tiebreaker
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _assert_current_visit_none(veh):
    assert veh.order_control_current_visit is None


def test_vehicle_initial_values():
    W = _build_corridor_world("current_visit_init")
    veh = W.addVehicle("o", "d", 0, name="veh_init")
    assert veh.order_control_visit_id == 0
    assert veh.order_control_current_visit is None
    assert veh.order_control_node_arrival_times == {}
    assert veh.order_control_node_arrival_tiebreakers == {}
    assert veh.order_control_earliest_arrival_timesteps == {}
    assert veh.order_control_batch_assignments == {}


def test_origin_to_ineligible_first_link():
    W = _build_corridor_world("current_visit_ineligible_first")
    link_o_m = W.get_link("o_m")
    veh = W.addVehicle("o", "d", 0, name="veh_ineligible_first")
    _advance_until_on_link(veh, "o_m")

    assert veh.order_control_visit_id == 0
    _assert_current_visit_none(veh)
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, link_o_m, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_earliest_arrival_timesteps["m"] == expected


def test_first_eligible_node_visit_via_generate():
    W = _build_merge_world("current_visit_first_eligible")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_first_eligible")
    _advance_until_on_link(veh, "link1")

    assert veh.order_control_visit_id == 1
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, link1, W, W.order_control_batch_tau_timesteps
    )
    _assert_current_visit_matches(
        veh,
        visit_id=1,
        node_name="merge",
        inlink_name="link1",
        earliest=expected,
    )


def test_eligible_to_ineligible_clears_current_visit():
    W = _build_merge_world("current_visit_eligible_to_ineligible")
    merge = W.get_node("merge")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_eligible_to_ineligible")

    _advance_until_on_link(veh, "link1")
    assert veh.order_control_visit_id == 1
    assert veh.order_control_current_visit is not None

    _setup_arrived_vehicle(
        merge,
        veh,
        W.get_link("link1"),
        out,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    merge.transfer_fcfs_clearance()

    assert veh.link.name == "out"
    assert veh.order_control_visit_id == 1
    _assert_current_visit_none(veh)
    assert "dest" in veh.order_control_earliest_arrival_timesteps


def test_next_eligible_visit_after_ineligible_link():
    W = _build_two_merge_world("current_visit_next_eligible")
    merge1 = W.get_node("merge1")
    mid_link = W.get_link("mid_link")
    mid_merge2 = W.get_link("mid_merge2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_next_eligible")

    _advance_until_on_link(veh, "link1")
    assert veh.order_control_visit_id == 1

    _setup_arrived_vehicle(
        merge1,
        veh,
        W.get_link("link1"),
        mid_link,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    merge1.transfer_fcfs_clearance()
    assert veh.link.name == "mid_link"
    assert veh.order_control_visit_id == 1
    _assert_current_visit_none(veh)

    veh.x = mid_link.length
    veh.route_next_link_choice()
    mid_merge2_entry_before = veh.order_control_visit_id
    veh.link = mid_merge2
    veh.link_arrival_time = W.T * W.DELTAT
    veh.begin_order_control_visit_on_link_entry()

    assert veh.order_control_visit_id == mid_merge2_entry_before + 1
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, mid_merge2, W, W.order_control_batch_tau_timesteps
    )
    _assert_current_visit_matches(
        veh,
        visit_id=2,
        node_name="merge2",
        inlink_name="mid_merge2",
        earliest=expected,
    )


def test_same_eligible_node_revisit_gets_new_visit_id():
    W = _build_revisit_world("current_visit_revisit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    mid_orig2 = W.get_link("mid_orig2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_revisit")

    _advance_until_on_link(veh, "link1")
    first_visit_id = veh.order_control_visit_id
    assert first_visit_id == 1

    _setup_arrived_vehicle(
        merge,
        veh,
        link1,
        out,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    merge.transfer_fcfs_clearance()
    assert veh.link.name == "out"
    _assert_current_visit_none(veh)

    while veh.link.name != "mid_orig2":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not reach mid_orig2")
        W.exec_simulation(duration_t2=1)

    orig2 = W.get_node("orig2")
    veh.x = mid_orig2.length
    veh.route_next_link = link2
    orig2.incoming_vehicles = [veh]
    orig2.transfer()

    assert veh.link.name == "link2"
    assert veh.order_control_visit_id == first_visit_id + 1
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, link2, W, W.order_control_batch_tau_timesteps
    )
    _assert_current_visit_matches(
        veh,
        visit_id=first_visit_id + 1,
        node_name="merge",
        inlink_name="link2",
        earliest=expected,
    )
    assert veh.order_control_current_visit["visit_id"] != first_visit_id
    assert veh.order_control_current_visit["inlink"].name == "link2"


def test_earliest_arrival_timestep_calculation():
    W = _build_merge_world("current_visit_earliest_calc", order_control_type="batch")
    W.set_order_control_batch_tau_timesteps(2)
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_earliest_calc")
    _advance_until_on_link(veh, "link1")

    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, link1, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_current_visit["earliest_arrival_timestep"] == expected
    computed = veh._compute_order_control_earliest_arrival_timestep_for_current_link()
    assert computed == expected


def test_legacy_earliest_dict_overwrites_on_revisit():
    W = _build_revisit_world("current_visit_legacy_overwrite")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    mid_orig2 = W.get_link("mid_orig2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_legacy_overwrite")

    _advance_until_on_link(veh, "link1")
    first_value = veh.order_control_earliest_arrival_timesteps["merge"]

    _setup_arrived_vehicle(
        merge,
        veh,
        link1,
        out,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    merge.transfer_fcfs_clearance()

    while veh.link.name != "mid_orig2":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not reach mid_orig2 for overwrite test")
        W.exec_simulation(duration_t2=1)

    orig2 = W.get_node("orig2")
    veh.x = mid_orig2.length
    veh.route_next_link = link2
    orig2.incoming_vehicles = [veh]
    orig2.transfer()

    second_value = veh.order_control_earliest_arrival_timesteps["merge"]
    assert second_value != first_value
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, link2, W, W.order_control_batch_tau_timesteps
    )
    assert second_value == expected


def test_legacy_record_method_does_not_touch_current_visit():
    W = _build_corridor_world("current_visit_legacy_record_only")
    link_o_m = W.get_link("o_m")
    veh = W.addVehicle("o", "d", 0, name="veh_legacy_record_only")
    veh.link = link_o_m
    veh.link_arrival_time = 0.0

    assert veh.order_control_visit_id == 0
    _assert_current_visit_none(veh)

    veh.record_order_control_earliest_arrival_timestep_for_current_link()

    assert veh.order_control_visit_id == 0
    _assert_current_visit_none(veh)
    expected = expected_earliest_arrival_timestep(
        0, link_o_m, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_earliest_arrival_timesteps["m"] == expected


def test_incoming_vehicles_reregistration_does_not_increment_visit_id():
    W = _build_merge_world("current_visit_incoming_reregister")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_incoming_reregister")

    _advance_until_on_link(veh, "link1")
    visit_id_after_entry = veh.order_control_visit_id
    assert visit_id_after_entry == 1

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
    merge.incoming_vehicles = [veh]

    visit_id_before_wait = veh.order_control_visit_id
    for _ in range(3):
        veh.route_next_link_choice()
        merge.incoming_vehicles.append(veh)
        W.T += 1
        veh.update()

    assert veh.order_control_visit_id == visit_id_before_wait
    assert veh.order_control_current_visit["visit_id"] == visit_id_after_entry


def test_link_entry_via_node_generate():
    W = _build_merge_world("current_visit_path_generate")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_path_generate")
    _advance_until_on_link(veh, "link1")
    assert veh.order_control_visit_id == 1
    assert veh.order_control_current_visit is not None


def test_link_entry_via_standard_transfer():
    W = _build_standard_to_eligible_world("current_visit_path_standard")
    mid = W.get_node("mid")
    in_link = W.get_link("in")
    out_link = W.get_link("out")
    merge2 = W.get_node("merge2")
    veh = W.addVehicle("orig", "dest", 0, name="veh_path_standard")
    veh.link = in_link
    veh.state = "run"
    veh.x = 200.0
    veh.v = 20.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out_link
    in_link.vehicles.append(veh)
    mid.incoming_vehicles = [veh]
    mid.signal_phase = 0

    visit_id_before = veh.order_control_visit_id
    mid.transfer()

    _assert_eligible_visit_after_link_entry(veh, W, out_link, visit_id_before)
    assert merge2.order_control_eligible is True
    assert merge2.order_control_type == "fcfs"


def test_link_entry_via_transfer_fcfs_no_clearance():
    W = _build_two_merge_world("current_visit_path_fcfs_no_clearance")
    merge1 = W.get_node("merge1")
    link1 = W.get_link("link1")
    mid_merge2 = W.get_link("mid_merge2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_path_fcfs_no_clearance")
    _advance_until_on_link(veh, "link1")
    visit_id_before = veh.order_control_visit_id
    _setup_arrived_vehicle(
        merge1,
        veh,
        link1,
        mid_merge2,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    merge1.transfer_fcfs_no_clearance()
    _assert_eligible_visit_after_link_entry(veh, W, mid_merge2, visit_id_before)


def test_link_entry_via_transfer_fcfs_clearance():
    W = _build_two_merge_world("current_visit_path_fcfs_clearance")
    merge1 = W.get_node("merge1")
    link1 = W.get_link("link1")
    mid_merge2 = W.get_link("mid_merge2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_path_fcfs_clearance")
    _advance_until_on_link(veh, "link1")
    visit_id_before = veh.order_control_visit_id
    _setup_arrived_vehicle(
        merge1,
        veh,
        link1,
        mid_merge2,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    merge1.transfer_fcfs_clearance()
    _assert_eligible_visit_after_link_entry(veh, W, mid_merge2, visit_id_before)


def test_link_entry_via_batch_transfer_vehicle():
    W = _build_two_merge_world(
        "current_visit_path_batch",
        merge1_order_control_type="batch",
    )
    merge1 = W.get_node("merge1")
    link1 = W.get_link("link1")
    mid_merge2 = W.get_link("mid_merge2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_path_batch")
    _advance_until_on_link(veh, "link1")
    visit_id_before = veh.order_control_visit_id
    _setup_arrived_vehicle(
        merge1,
        veh,
        link1,
        mid_merge2,
        x=200.0,
        earliest=veh.order_control_current_visit["earliest_arrival_timestep"],
    )
    veh.order_control_batch_assignments["merge1"] = 0
    merge1.order_control_batch_service_queue.append(
        {"batch_id": 0, "inlink": link1, "vehicles": [veh]}
    )
    mid_merge2.capacity_in_remain = 1e6
    link1.capacity_out_remain = 1e6
    merge1.flow_capacity_remain = 1e6
    count = merge1.serve_order_control_batch_service_queue()
    assert count == 1
    _assert_eligible_visit_after_link_entry(veh, W, mid_merge2, visit_id_before)


TESTS = [
    test_vehicle_initial_values,
    test_origin_to_ineligible_first_link,
    test_first_eligible_node_visit_via_generate,
    test_eligible_to_ineligible_clears_current_visit,
    test_next_eligible_visit_after_ineligible_link,
    test_same_eligible_node_revisit_gets_new_visit_id,
    test_earliest_arrival_timestep_calculation,
    test_legacy_earliest_dict_overwrites_on_revisit,
    test_legacy_record_method_does_not_touch_current_visit,
    test_incoming_vehicles_reregistration_does_not_increment_visit_id,
    test_link_entry_via_node_generate,
    test_link_entry_via_standard_transfer,
    test_link_entry_via_transfer_fcfs_no_clearance,
    test_link_entry_via_transfer_fcfs_clearance,
    test_link_entry_via_batch_transfer_vehicle,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control current visit state tests passed.")
