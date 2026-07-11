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
    W = build_corridor_world("batch_earliest_arrival_default_tau")
    link_o_m = W.get_link("o_m")
    link_m_d = W.get_link("m_d")
    tau = W.order_control_batch_tau_timesteps

    veh = W.addVehicle("o", "d", 0, name="veh_batch_earliest")
    assert veh.order_control_earliest_arrival_timesteps == {}
    assert veh.state == "home"
    assert veh.link is None

    W.exec_simulation(duration_t2=1)
    assert veh.state == "wait"
    assert veh.order_control_earliest_arrival_timesteps == {}
    assert veh.link is None

    while "m" not in veh.order_control_earliest_arrival_timesteps:
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link o_m")
        W.exec_simulation(duration_t2=1)

    assert veh.state == "run"
    assert veh.link.name == "o_m"
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected_m = expected_earliest_arrival_timestep(link_entry, link_o_m, W, tau)
    assert veh.order_control_earliest_arrival_timesteps["m"] == expected_m
    assert isinstance(veh.order_control_earliest_arrival_timesteps["m"], int)
    assert math.ceil((105 / 20) / W.DELTAT) == 6

    while "d" not in veh.order_control_earliest_arrival_timesteps:
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link m_d")
        W.exec_simulation(duration_t2=1)

    assert veh.link.name == "m_d"
    link_entry_m_d = int(round(veh.link_arrival_time / W.DELTAT))
    expected_d = expected_earliest_arrival_timestep(link_entry_m_d, link_m_d, W, tau)
    assert set(veh.order_control_earliest_arrival_timesteps.keys()) == {"m", "d"}
    assert veh.order_control_earliest_arrival_timesteps["d"] == expected_d
    assert isinstance(veh.order_control_earliest_arrival_timesteps["d"], int)
    assert math.ceil((130 / 30) / W.DELTAT) == 5

    while veh.state != "end":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not complete trip")
        W.exec_simulation(duration_t2=1)

    assert veh.arrival_time >= 0
    assert veh.travel_time >= 0
    assert set(veh.order_control_earliest_arrival_timesteps.keys()) == {"m", "d"}


def test_earliest_arrival_timestep_with_tau_two():
    W = build_corridor_world("batch_earliest_arrival_tau_two", tau_timesteps=2)
    link_o_m = W.get_link("o_m")
    tau = W.order_control_batch_tau_timesteps
    assert tau == 2

    veh = W.addVehicle("o", "d", 0, name="veh_batch_tau_two")

    while "m" not in veh.order_control_earliest_arrival_timesteps:
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not enter link o_m")
        W.exec_simulation(duration_t2=1)

    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected_m = expected_earliest_arrival_timestep(link_entry, link_o_m, W, tau)
    assert veh.order_control_earliest_arrival_timesteps["m"] == expected_m
    assert expected_m == link_entry + 6 + 2


if __name__ == "__main__":
    test_tau_timesteps_setter()
    test_earliest_arrival_timestep_recording_default_tau()
    test_earliest_arrival_timestep_with_tau_two()
    print("Order-control batch earliest arrival timestep test passed.")
