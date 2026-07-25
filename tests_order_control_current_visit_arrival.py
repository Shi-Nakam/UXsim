# Verify Phase 4-6P current-visit arrival recording at order-control nodes.
#
# Run from the repository root:
#   python tests_order_control_current_visit_arrival.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy

import numpy as np
import pytest

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_merge_world(name="current_visit_arrival_merge", *, order_control_type="fcfs"):
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


def _build_revisit_world(name="current_visit_arrival_revisit"):
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


def _build_corridor_world(name="current_visit_arrival_corridor"):
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


def _advance_until_on_link(veh, link_name):
    while veh.link is None or veh.link.name != link_name:
        if not veh.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {link_name}")
        veh.W.exec_simulation(duration_t2=1)


def _sync_vehicle_on_link_end(W, veh, link, out_link, *, timestep):
    W.T = timestep
    veh.link = link
    veh.state = "run"
    veh.x = link.length
    veh.v = 20.0
    veh.link_arrival_time = float(timestep * W.DELTAT)
    veh.route_next_link = out_link
    if veh not in link.vehicles:
        link.vehicles.append(veh)


def _assert_rng_streams_match(W_a, W_b):
    np.testing.assert_allclose(W_a.rng.random(), W_b.rng.random())
    np.testing.assert_allclose(
        W_a.order_control_rng.random(),
        W_b.order_control_rng.random(),
    )


def _setup_first_visit_ready(W, veh):
    link1 = W.get_link("link1")
    out = W.get_link("out")
    _advance_until_on_link(veh, "link1")
    _sync_vehicle_on_link_end(W, veh, link1, out, timestep=10)
    return W.get_node("merge"), link1, out


def test_ineligible_node_does_nothing():
    W = _build_corridor_world("arrival_ineligible")
    W_ref = _build_corridor_world("arrival_ineligible_ref")
    node_m = W.get_node("m")
    veh = W.addVehicle("o", "d", 0, name="veh_ineligible")
    veh_ref = W_ref.addVehicle("o", "d", 0, name="veh_ineligible_ref")
    visit_before = copy.deepcopy(veh.order_control_current_visit)
    times_before = copy.copy(veh.order_control_node_arrival_times)
    tie_before = copy.copy(veh.order_control_node_arrival_tiebreakers)

    veh.record_order_control_node_arrival(node_m)

    assert veh.order_control_current_visit == visit_before
    assert veh.order_control_node_arrival_times == times_before
    assert veh.order_control_node_arrival_tiebreakers == tie_before
    _assert_rng_streams_match(W, W_ref)


def test_none_type_node_does_nothing():
    W = _build_merge_world("arrival_none_type", order_control_type="none")
    W_ref = _build_merge_world("arrival_none_type_ref", order_control_type="none")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_none_type")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_none_type_ref")
    _advance_until_on_link(veh, "link1")
    _advance_until_on_link(veh_ref, "link1")
    visit_snapshot = copy.deepcopy(veh.order_control_current_visit)

    veh.record_order_control_node_arrival(merge)

    assert veh.order_control_current_visit == visit_snapshot
    assert veh.order_control_node_arrival_times == {}
    _assert_rng_streams_match(W, W_ref)


def test_missing_current_visit_raises():
    W = _build_merge_world("arrival_no_current_visit")
    W_ref = _build_merge_world("arrival_no_current_visit_ref")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_no_visit")
    W_ref.addVehicle("orig1", "dest", 0, name="veh_no_visit_ref")
    assert veh.order_control_current_visit is None

    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        veh.record_order_control_node_arrival(merge)

    assert veh.order_control_node_arrival_times == {}
    assert veh.order_control_node_arrival_tiebreakers == {}
    _assert_rng_streams_match(W, W_ref)


def test_mismatched_current_visit_node_raises():
    W = _build_merge_world("arrival_node_mismatch")
    W_ref = _build_merge_world("arrival_node_mismatch_ref")
    merge = W.get_node("merge")
    dest = W.get_node("dest")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_node_mismatch")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_node_mismatch_ref")
    _setup_first_visit_ready(W, veh)
    _setup_first_visit_ready(W_ref, veh_ref)
    visit_arrival_time = veh.order_control_current_visit["arrival_time"]
    visit_arrival_tiebreaker = veh.order_control_current_visit["arrival_tiebreaker"]
    times_before = copy.copy(veh.order_control_node_arrival_times)
    tie_before = copy.copy(veh.order_control_node_arrival_tiebreakers)
    veh.order_control_current_visit["node"] = dest

    with pytest.raises(ValueError, match="does not match arrival node"):
        veh.record_order_control_node_arrival(merge)

    assert veh.order_control_current_visit["arrival_time"] == visit_arrival_time
    assert veh.order_control_current_visit["arrival_tiebreaker"] == visit_arrival_tiebreaker
    assert veh.order_control_node_arrival_times == times_before
    assert veh.order_control_node_arrival_tiebreakers == tie_before
    _assert_rng_streams_match(W, W_ref)


def test_partial_arrival_time_only_raises():
    W = _build_merge_world("arrival_time_only")
    W_ref = _build_merge_world("arrival_time_only_ref")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_time_only")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_time_only_ref")
    _setup_first_visit_ready(W, veh)
    _setup_first_visit_ready(W_ref, veh_ref)
    veh.order_control_current_visit["arrival_time"] = 5.0
    arrival_tiebreaker_before = veh.order_control_current_visit["arrival_tiebreaker"]

    with pytest.raises(ValueError, match="inconsistent arrival state"):
        veh.record_order_control_node_arrival(merge)

    assert veh.order_control_current_visit["arrival_time"] == 5.0
    assert veh.order_control_current_visit["arrival_tiebreaker"] == arrival_tiebreaker_before
    assert veh.order_control_node_arrival_times == {}
    _assert_rng_streams_match(W, W_ref)


def test_partial_tiebreaker_only_raises():
    W = _build_merge_world("arrival_tie_only")
    W_ref = _build_merge_world("arrival_tie_only_ref")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_tie_only")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_tie_only_ref")
    _setup_first_visit_ready(W, veh)
    _setup_first_visit_ready(W_ref, veh_ref)
    veh.order_control_current_visit["arrival_tiebreaker"] = 0.5
    arrival_time_before = veh.order_control_current_visit["arrival_time"]

    with pytest.raises(ValueError, match="inconsistent arrival state"):
        veh.record_order_control_node_arrival(merge)

    assert veh.order_control_current_visit["arrival_time"] == arrival_time_before
    assert veh.order_control_current_visit["arrival_tiebreaker"] == 0.5
    assert veh.order_control_node_arrival_times == {}
    _assert_rng_streams_match(W, W_ref)


def test_first_visit_records_matching_values():
    W = _build_merge_world("arrival_first_visit")
    W_ref = _build_merge_world("arrival_first_visit_ref")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_first")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_first_ref")
    merge, _, _ = _setup_first_visit_ready(W, veh)
    _setup_first_visit_ready(W_ref, veh_ref)

    veh.record_order_control_node_arrival(merge)

    visit = veh.order_control_current_visit
    assert visit["arrival_time"] == W.T * W.DELTAT
    assert visit["arrival_tiebreaker"] is not None
    assert veh.order_control_node_arrival_times["merge"] == visit["arrival_time"]
    assert veh.order_control_node_arrival_tiebreakers["merge"] == visit["arrival_tiebreaker"]
    assert visit["arrival_tiebreaker"] == W_ref.rng.random()
    _assert_rng_streams_match(W, W_ref)


def test_first_visit_tiebreaker_uses_existing_rng_stream():
    W = _build_merge_world("arrival_rng_stream")
    W_ref = _build_merge_world("arrival_rng_stream_ref")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_rng")
    W_ref.addVehicle("orig1", "dest", 0, name="veh_rng_ref")
    merge, _, _ = _setup_first_visit_ready(W, veh)
    _setup_first_visit_ready(W_ref, W_ref.VEHICLES["veh_rng_ref"])

    veh.record_order_control_node_arrival(merge)

    expected_tiebreaker = W_ref.rng.random()
    assert veh.order_control_current_visit["arrival_tiebreaker"] == expected_tiebreaker
    np.testing.assert_allclose(W.rng.random(), W_ref.rng.random())


def test_same_visit_reregistration_is_noop():
    W = _build_merge_world("arrival_reregister")
    W_ref = _build_merge_world("arrival_reregister_ref")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_reregister")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_reregister_ref")
    merge, _, _ = _setup_first_visit_ready(W, veh)
    merge_ref, _, _ = _setup_first_visit_ready(W_ref, veh_ref)
    veh.record_order_control_node_arrival(merge)
    veh_ref.record_order_control_node_arrival(merge_ref)
    first_time = veh.order_control_current_visit["arrival_time"]
    first_tie = veh.order_control_current_visit["arrival_tiebreaker"]
    first_hist_time = veh.order_control_node_arrival_times["merge"]
    first_hist_tie = veh.order_control_node_arrival_tiebreakers["merge"]

    W.T = 15
    veh.record_order_control_node_arrival(merge)

    assert veh.order_control_current_visit["arrival_time"] == first_time
    assert veh.order_control_current_visit["arrival_tiebreaker"] == first_tie
    assert veh.order_control_node_arrival_times["merge"] == first_hist_time
    assert veh.order_control_node_arrival_tiebreakers["merge"] == first_hist_tie
    _assert_rng_streams_match(W, W_ref)


def _complete_first_visit_and_loop_back(W, veh):
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    mid_orig2 = W.get_link("mid_orig2")
    merge, _, _ = _setup_first_visit_ready(W, veh)
    veh.record_order_control_node_arrival(merge)
    first_hist_time = veh.order_control_node_arrival_times["merge"]
    first_hist_tie = veh.order_control_node_arrival_tiebreakers["merge"]

    _sync_vehicle_on_link_end(W, veh, link1, out, timestep=W.T)
    merge.incoming_vehicles = [veh]
    merge.transfer_fcfs_clearance()

    while veh.link.name != "mid_orig2":
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not loop back to mid_orig2")
        W.exec_simulation(duration_t2=1)

    orig2 = W.get_node("orig2")
    veh.x = mid_orig2.length
    veh.route_next_link = link2
    orig2.incoming_vehicles = [veh]
    orig2.transfer()

    return merge, first_hist_time, first_hist_tie


def test_revisit_updates_current_visit_only():
    W = _build_revisit_world("arrival_revisit")
    W_ref = _build_revisit_world("arrival_revisit_ref")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_revisit")
    W_ref.addVehicle("orig1", "dest", 0, name="veh_revisit_ref")
    merge, first_hist_time, first_hist_tie = _complete_first_visit_and_loop_back(W, veh)
    _complete_first_visit_and_loop_back(W_ref, W_ref.VEHICLES["veh_revisit_ref"])

    W.T = 40
    veh.record_order_control_node_arrival(merge)

    visit = veh.order_control_current_visit
    assert visit["arrival_time"] == W.T * W.DELTAT
    assert visit["arrival_tiebreaker"] is not None
    assert visit["arrival_tiebreaker"] == W_ref.order_control_rng.random()
    assert veh.order_control_node_arrival_times["merge"] == first_hist_time
    assert veh.order_control_node_arrival_tiebreakers["merge"] == first_hist_tie
    _assert_rng_streams_match(W, W_ref)


def test_revisit_reregistration_is_noop():
    W = _build_revisit_world("arrival_revisit_reregister")
    W_ref = _build_revisit_world("arrival_revisit_reregister_ref")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_revisit_reregister")
    veh_ref = W_ref.addVehicle("orig1", "dest", 0, name="veh_revisit_reregister_ref")
    merge, first_hist_time, first_hist_tie = _complete_first_visit_and_loop_back(W, veh)
    merge_ref, _, _ = _complete_first_visit_and_loop_back(W_ref, veh_ref)
    W.T = 40
    W_ref.T = 40
    veh.record_order_control_node_arrival(merge)
    veh_ref.record_order_control_node_arrival(merge_ref)
    revisit_time = veh.order_control_current_visit["arrival_time"]
    revisit_tie = veh.order_control_current_visit["arrival_tiebreaker"]

    W.T = 45
    W_ref.T = 45
    veh.record_order_control_node_arrival(merge)

    assert veh.order_control_current_visit["arrival_time"] == revisit_time
    assert veh.order_control_current_visit["arrival_tiebreaker"] == revisit_tie
    assert veh.order_control_node_arrival_times["merge"] == first_hist_time
    assert veh.order_control_node_arrival_tiebreakers["merge"] == first_hist_tie
    _assert_rng_streams_match(W, W_ref)


def _run_first_visit_and_revisit(W, veh):
    merge, first_hist_time, first_hist_tie = _complete_first_visit_and_loop_back(W, veh)
    W.T = 40
    veh.record_order_control_node_arrival(merge)
    return veh.order_control_current_visit["arrival_tiebreaker"]


def test_revisit_tiebreaker_reproducible_for_same_seed():
    W1 = _build_revisit_world("arrival_repro_1")
    W2 = _build_revisit_world("arrival_repro_2")
    veh1 = W1.addVehicle("orig1", "dest", 0, name="veh_repro_1")
    veh2 = W2.addVehicle("orig1", "dest", 0, name="veh_repro_2")
    tie1 = _run_first_visit_and_revisit(W1, veh1)
    tie2 = _run_first_visit_and_revisit(W2, veh2)
    np.testing.assert_allclose(tie1, tie2)


def test_vehicle_update_records_arrival_on_first_visit():
    W = _build_merge_world("arrival_update_integration")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_update")
    link1 = W.get_link("link1")
    _advance_until_on_link(veh, "link1")

    while (
        veh.order_control_current_visit is None
        or veh.order_control_current_visit["arrival_time"] is None
    ):
        if not W.check_simulation_ongoing():
            raise AssertionError("Vehicle did not record arrival via update()")
        W.exec_simulation(duration_t2=1)

    visit = veh.order_control_current_visit
    assert visit["arrival_time"] is not None
    assert visit["arrival_time"] > 0
    assert visit["arrival_time"] % W.DELTAT == 0
    assert visit["arrival_time"] <= W.T * W.DELTAT
    assert visit["arrival_tiebreaker"] is not None
    assert veh.order_control_node_arrival_times["merge"] == visit["arrival_time"]
    assert veh.order_control_node_arrival_tiebreakers["merge"] == visit["arrival_tiebreaker"]
    assert veh.link is link1
    assert veh.x == link1.length


TESTS = [
    test_ineligible_node_does_nothing,
    test_none_type_node_does_nothing,
    test_missing_current_visit_raises,
    test_mismatched_current_visit_node_raises,
    test_partial_arrival_time_only_raises,
    test_partial_tiebreaker_only_raises,
    test_first_visit_records_matching_values,
    test_first_visit_tiebreaker_uses_existing_rng_stream,
    test_same_visit_reregistration_is_noop,
    test_revisit_updates_current_visit_only,
    test_revisit_reregistration_is_noop,
    test_revisit_tiebreaker_reproducible_for_same_seed,
    test_vehicle_update_records_arrival_on_first_visit,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control current visit arrival tests passed.")
