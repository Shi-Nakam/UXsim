# Verify earliest_arrival_timestep recording at link entry for BATCH preparation.
#
# Run from the repository root:
#   python tests_order_control_batch_earliest_arrival_timestep.py
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


def build_merge_world(name, tau_timesteps=1):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    assert W.order_control_batch_tau_timesteps == 1
    if tau_timesteps != 1:
        W.set_order_control_batch_tau_timesteps(tau_timesteps)

    W.addNode("orig1", 0, 0)
    W.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 0)
    W.addLink("link1", "orig1", "merge", length=105, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=130, free_flow_speed=30, number_of_lanes=1)
    _prepare_network(W)
    return W


def build_corridor_world(name, tau_timesteps=1):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    assert W.order_control_batch_tau_timesteps == 1
    if tau_timesteps != 1:
        W.set_order_control_batch_tau_timesteps(tau_timesteps)

    W.addNode("o", 0, 0)
    W.addNode("m", 1, 0)
    W.addNode("d", 2, 0)
    W.addLink("o_m", "o", "m", length=105, free_flow_speed=20, number_of_lanes=1)
    W.addLink("m_d", "m", "d", length=130, free_flow_speed=30, number_of_lanes=1)
    _prepare_network(W)
    return W


def test_tau_timesteps_setter():
    W = World(
        name="batch_tau_setter",
        deltan=1,
        tmax=10,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    assert W.order_control_batch_tau_timesteps == 1

    W.set_order_control_batch_tau_timesteps(0)
    assert W.order_control_batch_tau_timesteps == 0

    W.set_order_control_batch_tau_timesteps(2)
    assert W.order_control_batch_tau_timesteps == 2

    for invalid in (-1, 1.5, "1", True):
        try:
            W.set_order_control_batch_tau_timesteps(invalid)
            raise AssertionError(f"Expected ValueError for tau_timesteps={invalid!r}")
        except ValueError:
            pass


def test_earliest_arrival_timestep_recording_default_tau():
    W = build_merge_world("batch_earliest_arrival_default_tau")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    tau = W.order_control_batch_tau_timesteps

    veh = W.addVehicle("orig1", "dest", 0, name="veh_batch_earliest")
    assert veh.order_control_earliest_arrival_timesteps == {}
    assert veh.state == "home"
    assert veh.link is None

    W.exec_simulation(duration_t2=1)
    assert veh.state == "wait"
    assert veh.order_control_earliest_arrival_timesteps == {}
    assert veh.link is None

    while veh.link is None or veh.link.name != "link1":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link link1")
        W.exec_simulation(duration_t2=1)

    assert veh.state == "run"
    assert veh.link.name == "link1"
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected_merge = expected_earliest_arrival_timestep(link_entry, link1, W, tau)
    assert veh.order_control_earliest_arrival_timesteps["merge"] == expected_merge
    assert veh.order_control_current_visit["earliest_arrival_timestep"] == expected_merge
    assert isinstance(veh.order_control_earliest_arrival_timesteps["merge"], int)
    assert math.ceil((105 / 20) / W.DELTAT) == 6

    while veh.link.name != "out":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link out")
        W.exec_simulation(duration_t2=1)

    assert veh.order_control_visit_id == 1
    assert veh.order_control_current_visit is None
    assert set(veh.order_control_earliest_arrival_timesteps.keys()) == {"merge"}

    while veh.state != "end":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not complete trip")
        W.exec_simulation(duration_t2=1)

    assert veh.arrival_time >= 0
    assert veh.travel_time >= 0
    assert set(veh.order_control_earliest_arrival_timesteps.keys()) == {"merge"}


def test_earliest_arrival_timestep_with_tau_two():
    W = build_merge_world("batch_earliest_arrival_tau_two", tau_timesteps=2)
    link1 = W.get_link("link1")
    tau = W.order_control_batch_tau_timesteps
    assert tau == 2

    veh = W.addVehicle("orig1", "dest", 0, name="veh_batch_tau_two")

    while veh.link is None or veh.link.name != "link1":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link link1")
        W.exec_simulation(duration_t2=1)

    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected_merge = expected_earliest_arrival_timestep(link_entry, link1, W, tau)
    assert veh.order_control_earliest_arrival_timesteps["merge"] == expected_merge
    assert veh.order_control_current_visit["earliest_arrival_timestep"] == expected_merge
    assert expected_merge == link_entry + 6 + 2


def test_revisit_preserves_legacy_earliest_and_updates_current_visit():
    W = build_merge_world("batch_earliest_revisit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_revisit_earliest")

    while veh.link is None or veh.link.name != "link1":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link link1")
        W.exec_simulation(duration_t2=1)

    first_legacy = veh.order_control_earliest_arrival_timesteps["merge"]
    first_visit_id = veh.order_control_visit_id

    W.T = 40
    veh.link = link1
    veh.link_arrival_time = W.T * W.DELTAT
    veh.begin_order_control_visit_on_link_entry()

    assert veh.order_control_visit_id == first_visit_id + 1
    assert veh.order_control_earliest_arrival_timesteps["merge"] == first_legacy
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected_revisit = expected_earliest_arrival_timestep(
        link_entry, link1, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_current_visit["earliest_arrival_timestep"] == expected_revisit
    assert expected_revisit != first_legacy
    assert veh.get_order_control_batch_earliest_arrival_timestep(merge) == expected_revisit


def test_ineligible_nodes_do_not_record_legacy_earliest():
    W = build_corridor_world("batch_earliest_ineligible")
    veh = W.addVehicle("o", "d", 0, name="veh_ineligible_corridor")

    while veh.link is None or veh.link.name != "o_m":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link o_m")
        W.exec_simulation(duration_t2=1)

    assert veh.order_control_current_visit is None
    assert veh.order_control_earliest_arrival_timesteps == {}


def test_incoming_reregistration_does_not_change_earliest_values():
    W = build_merge_world("batch_earliest_reregister")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_reregister")

    while veh.link is None or veh.link.name != "link1":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link link1")
        W.exec_simulation(duration_t2=1)

    legacy_before = dict(veh.order_control_earliest_arrival_timesteps)
    visit_before = veh.order_control_current_visit.copy()
    visit_id_before = veh.order_control_visit_id

    veh.x = link1.length
    veh.route_next_link = out
    link1.vehicles.clear()
    link1.vehicles.append(veh)
    merge.incoming_vehicles = []

    for _ in range(3):
        W.T += 1
        veh.carfollow()
        veh.update()

        assert merge.incoming_vehicles.count(veh) == 1
        assert veh.order_control_visit_id == visit_id_before
        assert veh.order_control_earliest_arrival_timesteps == legacy_before
        assert (
            veh.order_control_current_visit["earliest_arrival_timestep"]
            == visit_before["earliest_arrival_timestep"]
        )

        merge.incoming_vehicles = []


def test_legacy_record_method_does_not_overwrite_existing_entry():
    W = build_merge_world("batch_earliest_legacy_record")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_legacy_record")
    veh.link = link1
    veh.link_arrival_time = 0.0

    veh.record_order_control_earliest_arrival_timestep_for_current_link()
    expected = expected_earliest_arrival_timestep(
        0, link1, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_earliest_arrival_timesteps["merge"] == expected
    assert veh.order_control_current_visit is None

    veh.order_control_earliest_arrival_timesteps["merge"] = 999
    veh.record_order_control_earliest_arrival_timestep_for_current_link()
    assert veh.order_control_earliest_arrival_timesteps["merge"] == 999
    assert veh.order_control_current_visit is None


if __name__ == "__main__":
    test_tau_timesteps_setter()
    test_earliest_arrival_timestep_recording_default_tau()
    test_earliest_arrival_timestep_with_tau_two()
    test_revisit_preserves_legacy_earliest_and_updates_current_visit()
    test_ineligible_nodes_do_not_record_legacy_earliest()
    test_incoming_reregistration_does_not_change_earliest_values()
    test_legacy_record_method_does_not_overwrite_existing_entry()
    print("Order-control batch earliest arrival timestep test passed.")
