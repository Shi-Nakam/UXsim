# Verify BATCH t_trigger estimation at Level 0 and Level 1.
#
# Run from the repository root:
#   python tests_order_control_batch_t_trigger_estimation.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy

from uxsim import World


def _build_merge_network(name="batch_t_trigger"):
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
    )
    W.addNode("other_node", 1, 2)
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _make_trigger_vehicle(
    W=None,
    name="trigger",
    inlink_name="link1",
    arrival_time=10.0,
    tiebreaker=0.2,
    earliest_arrival_timestep=12,
    batch_assignments=None,
):
    if W is None:
        W = _build_merge_network()
    veh = W.addVehicle("orig1", "dest", 0, name=name)
    veh.link = W.get_link(inlink_name)
    veh.route_next_link = W.get_link("out")
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest_arrival_timestep
    if batch_assignments is not None:
        veh.order_control_batch_assignments.update(batch_assignments)
    merge = W.get_node("merge")
    merge.incoming_vehicles = [veh]
    return veh, merge


def _snapshot_state(merge, trigger_vehicle):
    return {
        "incoming_vehicles": list(merge.incoming_vehicles),
        "service_queue": list(merge.order_control_batch_service_queue),
        "next_id": merge.order_control_batch_next_id,
        "last_inlink": merge.last_order_control_inlink,
        "last_entry_timestep": merge.last_order_control_entry_timestep,
        "clearance_timesteps": merge.order_control_clearance_timesteps,
        "W_T": getattr(merge.W, "T", 0),
        "vehicle": {
            "batch_assignments": copy.copy(trigger_vehicle.order_control_batch_assignments),
            "arrival_times": copy.copy(trigger_vehicle.order_control_node_arrival_times),
            "tiebreakers": copy.copy(trigger_vehicle.order_control_node_arrival_tiebreakers),
            "earliest": copy.copy(trigger_vehicle.order_control_earliest_arrival_timesteps),
            "route_next_link": trigger_vehicle.route_next_link,
            "link": trigger_vehicle.link,
        },
    }


def test_level_0_basic_earliest_arrival_is_maximum():
    veh, merge = _make_trigger_vehicle(
        arrival_time=10.0,
        earliest_arrival_timestep=12,
    )
    assert merge.estimate_order_control_batch_t_trigger_level_0(veh) == 12


def test_level_0_first_transfer_timestep_is_maximum():
    veh, merge = _make_trigger_vehicle(
        arrival_time=10.0,
        earliest_arrival_timestep=10,
    )
    assert merge.estimate_order_control_batch_t_trigger_level_0(veh) == 11


def test_level_0_independent_of_W_T():
    veh, merge = _make_trigger_vehicle(
        arrival_time=10.0,
        earliest_arrival_timestep=12,
    )
    setattr(merge.W, "T", 11)
    result_1 = merge.estimate_order_control_batch_t_trigger_level_0(veh)
    setattr(merge.W, "T", 50)
    result_2 = merge.estimate_order_control_batch_t_trigger_level_0(veh)
    assert result_1 == result_2 == 12


def test_level_1_no_previous_vehicle():
    veh, merge = _make_trigger_vehicle(
        arrival_time=10.0,
        earliest_arrival_timestep=12,
    )
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    assert merge.estimate_order_control_batch_t_trigger_level_1(veh) == 12


def test_level_1_same_inlink_no_additional_clearance():
    W = _build_merge_network("batch_t_trigger_same_inlink")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(
        W,
        inlink_name="link1",
        arrival_time=10.0,
        earliest_arrival_timestep=12,
    )
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 1
    assert merge.estimate_order_control_batch_t_trigger_level_1(veh) == 12


def test_level_1_different_inlink_clearance_is_maximum():
    W = _build_merge_network("batch_t_trigger_diff_inlink")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(
        W,
        inlink_name="link2",
        arrival_time=10.0,
        earliest_arrival_timestep=10,
    )
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 1
    assert merge.estimate_order_control_batch_t_trigger_level_1(veh) == 12


def test_level_1_base_trigger_timestep_larger_than_clearance():
    W = _build_merge_network("batch_t_trigger_base_larger")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(
        W,
        inlink_name="link2",
        arrival_time=14.0,
        earliest_arrival_timestep=15,
    )
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 1
    assert merge.estimate_order_control_batch_t_trigger_level_1(veh) == 15


def test_level_1_clearance_timesteps_zero():
    W = _build_merge_network("batch_t_trigger_clearance_zero")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(
        W,
        inlink_name="link2",
        arrival_time=10.0,
        earliest_arrival_timestep=10,
    )
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 0
    assert merge.estimate_order_control_batch_t_trigger_level_1(veh) == 11


def test_trigger_earliest_arrival_lower_bound_level_0_and_1():
    W = _build_merge_network("batch_t_trigger_lower_bound")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(
        W,
        inlink_name="link2",
        arrival_time=10.0,
        earliest_arrival_timestep=18,
    )
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 1

    t0 = merge.estimate_order_control_batch_t_trigger_level_0(veh)
    t1 = merge.estimate_order_control_batch_t_trigger_level_1(veh)
    earliest = veh.order_control_earliest_arrival_timesteps["merge"]
    assert earliest <= t0
    assert earliest <= t1
    assert t0 == 18
    assert t1 == 18


def _expect_value_error(callable_obj):
    try:
        callable_obj()
        raise AssertionError("Expected ValueError was not raised.")
    except ValueError:
        pass


def test_value_error_not_order_control_eligible():
    W = _build_merge_network("batch_t_trigger_ineligible")
    merge = W.get_node("merge")
    merge.order_control_eligible = False
    veh, _ = _make_trigger_vehicle(W)
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_not_batch_type():
    W = _build_merge_network("batch_t_trigger_not_batch")
    merge = W.get_node("merge")
    merge.order_control_type = "fcfs"
    veh, _ = _make_trigger_vehicle(W)
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_not_in_incoming_vehicles():
    veh, merge = _make_trigger_vehicle()
    merge.incoming_vehicles = []
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_no_route_next_link():
    veh, merge = _make_trigger_vehicle()
    veh.route_next_link = None
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_missing_arrival_time():
    veh, merge = _make_trigger_vehicle()
    del veh.order_control_node_arrival_times["merge"]
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_missing_tiebreaker():
    veh, merge = _make_trigger_vehicle()
    del veh.order_control_node_arrival_tiebreakers["merge"]
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_missing_earliest_arrival_timestep():
    veh, merge = _make_trigger_vehicle()
    del veh.order_control_earliest_arrival_timesteps["merge"]
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_value_error_already_batched_at_target_node():
    veh, merge = _make_trigger_vehicle(
        batch_assignments={"merge": 0},
    )
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_0(veh))


def test_other_node_batch_assignment_allowed():
    veh, merge = _make_trigger_vehicle(
        batch_assignments={"other_node": 0},
    )
    assert merge.estimate_order_control_batch_t_trigger_level_0(veh) == 12
    assert merge.estimate_order_control_batch_t_trigger_level_1(veh) == 12


def test_value_error_level_1_no_current_link():
    veh, merge = _make_trigger_vehicle()
    veh.link = None
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_1(veh))


def test_value_error_level_1_inconsistent_clearance_state():
    W = _build_merge_network("batch_t_trigger_inconsistent_clearance")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(W, inlink_name="link2")
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = None
    _expect_value_error(lambda: merge.estimate_order_control_batch_t_trigger_level_1(veh))


def test_no_side_effects_level_0_and_level_1():
    W = _build_merge_network("batch_t_trigger_no_side_effects")
    link1 = W.get_link("link1")
    veh, merge = _make_trigger_vehicle(
        W,
        inlink_name="link2",
        arrival_time=10.0,
        earliest_arrival_timestep=12,
    )
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 10
    merge.order_control_clearance_timesteps = 1

    before_0 = _snapshot_state(merge, veh)
    merge.estimate_order_control_batch_t_trigger_level_0(veh)
    after_0 = _snapshot_state(merge, veh)
    assert before_0 == after_0

    before_1 = _snapshot_state(merge, veh)
    merge.estimate_order_control_batch_t_trigger_level_1(veh)
    after_1 = _snapshot_state(merge, veh)
    assert before_1 == after_1


if __name__ == "__main__":
    test_level_0_basic_earliest_arrival_is_maximum()
    test_level_0_first_transfer_timestep_is_maximum()
    test_level_0_independent_of_W_T()
    test_level_1_no_previous_vehicle()
    test_level_1_same_inlink_no_additional_clearance()
    test_level_1_different_inlink_clearance_is_maximum()
    test_level_1_base_trigger_timestep_larger_than_clearance()
    test_level_1_clearance_timesteps_zero()
    test_trigger_earliest_arrival_lower_bound_level_0_and_1()
    test_value_error_not_order_control_eligible()
    test_value_error_not_batch_type()
    test_value_error_not_in_incoming_vehicles()
    test_value_error_no_route_next_link()
    test_value_error_missing_arrival_time()
    test_value_error_missing_tiebreaker()
    test_value_error_missing_earliest_arrival_timestep()
    test_value_error_already_batched_at_target_node()
    test_other_node_batch_assignment_allowed()
    test_value_error_level_1_no_current_link()
    test_value_error_level_1_inconsistent_clearance_state()
    test_no_side_effects_level_0_and_level_1()
    print("Order-control batch t_trigger estimation test passed.")
