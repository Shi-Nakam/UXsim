# Verify Level 2 BATCH t_trigger body connection in UXsim.
#
# Run from the repository root:
#   python tests_order_control_batch_t_trigger_level_2_body.py

import copy
from unittest.mock import patch

from uxsim import World


def _build_network(name="level2_body"):
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
        order_control_batch_t_trigger_level=2,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker):
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


def _setup_vehicle(merge, veh, link, out, earliest, arrival_time, tiebreaker, x):
    veh.link = link
    veh.route_next_link = out
    veh.x = x
    veh.v = 5.0
    veh.state = "run"
    veh.order_control_node_arrival_times[merge.name] = arrival_time
    veh.order_control_node_arrival_tiebreakers[merge.name] = tiebreaker
    veh.order_control_earliest_arrival_timesteps[merge.name] = earliest
    _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)
    if veh not in link.vehicles:
        link.vehicles.append(veh)


def _world_counter_snapshot(W):
    return {
        "call": W.order_control_batch_level_2_call_count,
        "resolved": W.order_control_batch_level_2_resolved_count,
        "unresolved": W.order_control_batch_level_2_unresolved_count,
        "fallback": W.order_control_batch_level_2_level_1_fallback_count,
    }


def test_world_counters_initial_zero():
    W = _build_network("counters_zero")
    assert _world_counter_snapshot(W) == {
        "call": 0,
        "resolved": 0,
        "unresolved": 0,
        "fallback": 0,
    }


def test_node_virtual_horizon_default():
    W = _build_network("vh_default")
    merge = W.get_node("merge")
    assert merge.order_control_batch_virtual_horizon == 30


def test_level_0_does_not_call_level_2():
    W = _build_network("level0_no_l2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="T0")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _world_counter_snapshot(W)
    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference"
    ) as mock_l2:
        t_trigger = merge._resolve_order_control_batch_t_trigger(trigger, 0)
        mock_l2.assert_not_called()
    assert t_trigger == merge.estimate_order_control_batch_t_trigger_level_0(trigger)
    assert _world_counter_snapshot(W) == before


def test_level_1_does_not_call_level_2():
    W = _build_network("level1_no_l2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="T1")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    before = _world_counter_snapshot(W)
    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference"
    ) as mock_l2:
        t_trigger = merge._resolve_order_control_batch_t_trigger(trigger, 1)
        mock_l2.assert_not_called()
    assert t_trigger == merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    assert _world_counter_snapshot(W) == before


def test_level_0_and_1_form_batch_counters_unchanged():
    W = _build_network("form_level01")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="A")
    other = W.addVehicle("orig2", "dest", 0, name="B")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_vehicle(merge, other, link2, out, 10, 15.0, 0.2, 100.0)
    before = _world_counter_snapshot(W)
    merge.form_order_control_batch(t_trigger_level=0, max_batch_size=5)
    assert _world_counter_snapshot(W) == before
    merge.form_order_control_batch(t_trigger_level=1, max_batch_size=5)
    assert _world_counter_snapshot(W) == before


def test_level_2_calls_level_1_once():
    W = _build_network("l2_l1_once")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="L1")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    l1_calls = 0
    original_l1 = merge.estimate_order_control_batch_t_trigger_level_1

    def counting_l1(veh):
        nonlocal l1_calls
        l1_calls += 1
        return original_l1(veh)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": False, "t_level_2_candidate": t_level_1}

    merge.estimate_order_control_batch_t_trigger_level_1 = counting_l1
    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert l1_calls == 1


def test_level_2_calls_reference_once():
    W = _build_network("l2_ref_once")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="R1")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    calls = 0

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        nonlocal calls
        calls += 1
        return {"resolved": True, "t_level_2_candidate": t_level_1 + 3}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        result = merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert calls == 1
    assert result == merge.estimate_order_control_batch_t_trigger_level_1(trigger) + 3


def test_level_2_receives_node_virtual_horizon():
    W = _build_network("l2_virtual_horizon_pass")
    merge = W.get_node("merge")
    merge.order_control_batch_virtual_horizon = 47
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="VH")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    calls = 0
    seen_horizon = None

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        nonlocal calls, seen_horizon
        calls += 1
        seen_horizon = virtual_horizon
        return {"resolved": True, "t_level_2_candidate": t_level_1}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert calls == 1
    assert seen_horizon == 47


def test_level_2_resolved_uses_candidate():
    W = _build_network("l2_resolved")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="RS")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    t_l1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": True, "t_level_2_candidate": t_level_1 + 5}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        assert merge._resolve_order_control_batch_t_trigger(trigger, 2) == t_l1 + 5


def test_level_2_resolved_counters():
    W = _build_network("l2_resolved_counters")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="RC")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": True, "t_level_2_candidate": t_level_1}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert _world_counter_snapshot(W) == {
        "call": 1,
        "resolved": 1,
        "unresolved": 0,
        "fallback": 0,
    }


def test_level_2_unresolved_uses_level_1():
    W = _build_network("l2_unresolved")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="UN")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    t_l1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": False, "t_level_2_candidate": 999}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        assert merge._resolve_order_control_batch_t_trigger(trigger, 2) == t_l1


def test_level_2_unresolved_level_1_called_once():
    W = _build_network("l2_unresolved_l1")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="UO")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    l1_calls = 0
    original_l1 = merge.estimate_order_control_batch_t_trigger_level_1

    def counting_l1(veh):
        nonlocal l1_calls
        l1_calls += 1
        return original_l1(veh)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": False, "t_level_2_candidate": 50}

    merge.estimate_order_control_batch_t_trigger_level_1 = counting_l1
    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert l1_calls == 1


def test_level_2_unresolved_counters():
    W = _build_network("l2_unresolved_counters")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="UC")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": False, "t_level_2_candidate": t_level_1}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert _world_counter_snapshot(W) == {
        "call": 1,
        "resolved": 0,
        "unresolved": 1,
        "fallback": 1,
    }


def test_level_2_value_error_propagates():
    W = _build_network("l2_value_error")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="VE")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)

    def raising_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        raise ValueError("synthetic level 2 failure")

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        raising_l2,
    ):
        try:
            merge._resolve_order_control_batch_t_trigger(trigger, 2)
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "synthetic level 2 failure" in str(exc)
    assert _world_counter_snapshot(W) == {
        "call": 1,
        "resolved": 0,
        "unresolved": 0,
        "fallback": 0,
    }


def test_level_2_invalid_return_value_raises():
    W = _build_network("l2_invalid_return")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="IR")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        lambda *args, **kwargs: {"resolved": True, "t_level_2_candidate": True},
    ):
        try:
            merge._resolve_order_control_batch_t_trigger(trigger, 2)
            assert False, "expected ValueError"
        except ValueError:
            pass
    assert W.order_control_batch_level_2_call_count == 1
    assert W.order_control_batch_level_2_resolved_count == 0


def test_level_2_resolved_batch_formation():
    W = _build_network("l2_form_resolved")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="FR")
    other = W.addVehicle("orig2", "dest", 0, name="FO")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_vehicle(merge, other, link2, out, 10, 15.0, 0.2, 100.0)
    t_l1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": True, "t_level_2_candidate": t_level_1 + 2}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        result = merge.form_order_control_batch(t_trigger_level=2, max_batch_size=5)
    assert result == "batch_formed"
    assert trigger.order_control_batch_assignments["merge"] == 0
    assert len(merge.order_control_batch_service_queue) >= 1


def test_level_2_unresolved_batch_formation():
    W = _build_network("l2_form_unresolved")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="FU")
    other = W.addVehicle("orig2", "dest", 0, name="FO2")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)
    _setup_vehicle(merge, other, link2, out, 10, 15.0, 0.2, 100.0)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": False, "t_level_2_candidate": 999}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        result = merge.form_order_control_batch(t_trigger_level=2, max_batch_size=5)
    assert result == "batch_formed"
    assert trigger.order_control_batch_assignments["merge"] == 0


def test_assigned_visit_excluded_from_next_formation():
    W = _build_network("l2_exclude")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="EX")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 120.0)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": True, "t_level_2_candidate": t_level_1}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge.form_order_control_batch(t_trigger_level=2, max_batch_size=5)
    assert trigger not in merge.get_order_control_batch_trigger_candidates()


def test_new_visit_at_different_node():
    W = _build_network("l2_other_node")
    merge = W.get_node("merge")
    other_merge = W.addNode(
        "merge2",
        3,
        1,
        order_control_eligible=True,
        order_control_type="batch",
        order_control_batch_t_trigger_level=2,
    )
    W.addLink("link3", "orig1", "merge2", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out2", "merge2", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    link1 = W.get_link("link1")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    out2 = W.get_link("out2")
    veh = W.addVehicle("orig1", "dest", 0, name="DN")
    _setup_vehicle(merge, veh, link1, out, 12, 10.0, 0.1, 120.0)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": True, "t_level_2_candidate": t_level_1}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge.form_order_control_batch(t_trigger_level=2, max_batch_size=5)
    veh.order_control_visit_id += 1
    veh.order_control_current_visit = None
    _setup_vehicle(other_merge, veh, link3, out2, 10, 20.0, 0.3, 100.0)
    assert veh in other_merge.get_order_control_batch_trigger_candidates()


def test_revisit_same_node_new_visit():
    W = _build_network("l2_revisit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="RV")
    _setup_vehicle(merge, veh, link1, out, 12, 10.0, 0.1, 120.0)

    def fake_l2(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, **kwargs):
        return {"resolved": True, "t_level_2_candidate": t_level_1}

    with patch(
        "uxsim.order_control_batch_level_2_reference.estimate_order_control_batch_t_trigger_level_2_reference",
        fake_l2,
    ):
        merge.form_order_control_batch(t_trigger_level=2, max_batch_size=5)
    veh.order_control_visit_id += 1
    veh.order_control_current_visit = None
    veh.order_control_batch_assignments.pop("merge", None)
    _setup_vehicle(merge, veh, link1, out, 10, 25.0, 0.4, 100.0)
    assert veh in merge.get_order_control_batch_trigger_candidates()


def test_real_level_2_small_integration():
    W = _build_network("l2_real")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="REAL")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    W.T = 0
    rng_state = copy.deepcopy(W.rng.bit_generator.state)
    world_t = getattr(W, "T", 0)
    result = merge.form_order_control_batch(t_trigger_level=2, max_batch_size=5)
    assert result == "batch_formed"
    assert trigger.has_order_control_batch_assignment(merge) is True
    assert W.rng.bit_generator.state == rng_state
    assert getattr(W, "T", 0) == world_t
    assert W.order_control_batch_level_2_call_count >= 1


def test_real_level_2_does_not_mutate_real_state():
    W = _build_network("l2_real_mut")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    trigger = W.addVehicle("orig1", "dest", 0, name="MUT")
    _setup_vehicle(merge, trigger, link1, out, 12, 10.0, 0.1, 100.0)
    W.T = 0
    before = {
        "queue": list(merge.order_control_batch_service_queue),
        "incoming": list(merge.incoming_vehicles),
        "x": trigger.x,
        "v": trigger.v,
        "link": trigger.link,
        "rng": copy.deepcopy(W.rng.bit_generator.state),
    }
    merge._resolve_order_control_batch_t_trigger(trigger, 2)
    assert list(merge.order_control_batch_service_queue) == before["queue"]
    assert merge.incoming_vehicles == before["incoming"]
    assert trigger.x == before["x"]
    assert trigger.v == before["v"]
    assert trigger.link is before["link"]
    assert W.rng.bit_generator.state == before["rng"]


def main():
    test_world_counters_initial_zero()
    test_node_virtual_horizon_default()
    test_level_0_does_not_call_level_2()
    test_level_1_does_not_call_level_2()
    test_level_0_and_1_form_batch_counters_unchanged()
    test_level_2_calls_level_1_once()
    test_level_2_calls_reference_once()
    test_level_2_receives_node_virtual_horizon()
    test_level_2_resolved_uses_candidate()
    test_level_2_resolved_counters()
    test_level_2_unresolved_uses_level_1()
    test_level_2_unresolved_level_1_called_once()
    test_level_2_unresolved_counters()
    test_level_2_value_error_propagates()
    test_level_2_invalid_return_value_raises()
    test_level_2_resolved_batch_formation()
    test_level_2_unresolved_batch_formation()
    test_assigned_visit_excluded_from_next_formation()
    test_new_visit_at_different_node()
    test_revisit_same_node_new_visit()
    test_real_level_2_small_integration()
    test_real_level_2_does_not_mutate_real_state()
    print("Level 2 body connection tests passed (22 tests).")


if __name__ == "__main__":
    main()
