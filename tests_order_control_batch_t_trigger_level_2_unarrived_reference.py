# Phase 4-6X: unarrived service-unit Vehicle and reference-only BATCH serve tests.
#
# Run from the repository root:
#   python tests_order_control_batch_t_trigger_level_2_unarrived_reference.py

import ast
import copy
import importlib.util
import pickle
from collections import deque
from pathlib import Path

from uxsim import World

_REPO_ROOT = Path(__file__).resolve().parent
_REFERENCE_MODULE_PATH = (
    _REPO_ROOT / "diagnostics" / "order_control" / "level2_virtual_world_reference.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "level2_virtual_world_reference",
    _REFERENCE_MODULE_PATH,
)
_L2_REFERENCE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_L2_REFERENCE)
estimate_level2_reference = (
    _L2_REFERENCE.estimate_order_control_batch_t_trigger_level_2_reference
)
STOP_QUEUE = _L2_REFERENCE.STOP_QUEUE
BLOCK_INLINK = _L2_REFERENCE.BLOCK_INLINK
STOP_AFTER_TRANSFER = _L2_REFERENCE.STOP_AFTER_TRANSFER
SKIP_INLINK = _L2_REFERENCE.SKIP_INLINK


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_three_inlink_network(name="l2_unarr", clearance=0):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.set_order_control_clearance_timesteps(clearance)
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("orig3", 0, 4)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_multi_outlink_network(name="l2_multi_out", clearance=0):
    W = World(
        name=name,
        deltan=1,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.set_order_control_clearance_timesteps(clearance)
    W.addNode("orig1", 0, 0)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest1", 2, 0)
    W.addNode("dest2", 2, 2)
    W.addNode("dest3", 2, 4)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out1", "merge", "dest1", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out2", "merge", "dest2", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out3", "merge", "dest3", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _make_vehicle(W, orig_name, name, dest="dest"):
    return W.addVehicle(orig_name, dest, 0, name=name)


def _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker, batch_assignment=None):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    veh.order_control_current_visit = {
        "visit_id": veh.order_control_visit_id,
        "node": merge,
        "inlink": link,
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
        "arrival_tiebreaker": tiebreaker,
        "batch_assignment": batch_assignment,
    }


def _setup_arrived(merge, veh, link, out_link, earliest, arrival_time, tiebreaker, x=200.0):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.move_remain = 0.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    veh.order_control_node_arrival_times["merge"] = arrival_time
    veh.order_control_node_arrival_tiebreakers["merge"] = tiebreaker
    _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker)
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _setup_unarrived(
    merge,
    veh,
    link,
    earliest,
    *,
    x=150.0,
    route_next_link=None,
    use_link_as_route=True,
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = 20.0
    veh.move_remain = 20.0
    veh.x_old = x
    veh.x_next = x
    veh.link_arrival_time = 0.0
    if route_next_link is None and use_link_as_route:
        veh.route_next_link = link
    else:
        veh.route_next_link = route_next_link
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    _sync_visit(veh, merge, link, earliest, None, None)
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    assert veh not in merge.incoming_vehicles


def _register_unit(merge, batch_id, inlink, vehicles):
    visit_ids = []
    for veh in vehicles:
        visit = veh.order_control_current_visit
        visit["batch_assignment"] = batch_id
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


def _boost_capacity(merge, *links):
    for link in links:
        link.capacity_in_remain = 1e6
        link.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6


def _snapshot_vehicle(veh):
    visit = veh.order_control_current_visit
    return {
        "x": veh.x,
        "state": veh.state,
        "route_next_link": (
            veh.route_next_link.name if veh.route_next_link is not None else None
        ),
        "arrival_time": visit.get("arrival_time") if visit else None,
        "arrival_tiebreaker": visit.get("arrival_tiebreaker") if visit else None,
    }


def _expect_value_error(callable_obj):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_offset0_no_advance_before_service():
    W = _build_three_inlink_network("off0_before")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=150.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    x_before = a1.x
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    assert a1.x == x_before
    assert "A1" not in result["virtual_node_arrival_timesteps"]


def test_offset0_single_advance_after_service():
    W = _build_three_inlink_network("off0_after")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    x_before = a1.x
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"]
    assert trace[0]["timestep"] == 10
    assert a1.x == x_before
    assert result["virtual_node_arrival_timesteps"].get("A1") == 10


def test_unarrived_served_on_next_timestep_not_same():
    W = _build_three_inlink_network("next_t_serve")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=5
    )
    assert result["virtual_node_arrival_timesteps"]["A1"] == 10
    assert result["vehicle_transfer_timesteps"].get("A1", 99) >= 11


def test_unarrived_advances_and_registers_incoming():
    W = _build_three_inlink_network("unarrived_adv")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=150.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    before = _snapshot_vehicle(a1)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=2
    )
    after = _snapshot_vehicle(a1)
    assert after == before
    assert "A1" in result["virtual_node_arrival_timesteps"]
    assert result["virtual_node_arrival_timesteps"]["A1"] >= 10


def test_leader_follower_maintained_on_inlink():
    W = _build_three_inlink_network("leader_follower")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    a2 = _make_vehicle(W, "orig1", "A2")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_unarrived(merge, a2, link1, 0, x=198.0)
    link1.vehicles = deque([a1, a2])
    a1.leader = None
    a1.follower = a2
    a2.leader = a1
    a2.follower = None
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1, a2])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=1
    )
    assert result["virtual_node_arrival_timesteps"]["A1"] == 10
    assert result["virtual_node_arrival_timesteps"]["A2"] == 11


def test_simultaneous_virtual_arrival_same_timestep():
    W = _build_three_inlink_network("simul_arrival")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    a2 = _make_vehicle(W, "orig2", "A2")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_unarrived(merge, a2, link2, 0, x=199.0)
    link3 = W.get_link("link3")
    _setup_arrived(merge, trigger, link3, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link2, [a2])
    W.T = 10
    _boost_capacity(merge, link1, link2, link3, out)
    before_a1 = copy.deepcopy(a1.order_control_current_visit)
    before_a2 = copy.deepcopy(a2.order_control_current_visit)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=2
    )
    assert result["virtual_node_arrival_timesteps"]["A1"] == 10
    assert result["virtual_node_arrival_timesteps"]["A2"] == 10
    assert a1.order_control_current_visit["arrival_time"] == before_a1["arrival_time"]
    assert a2.order_control_current_visit["arrival_tiebreaker"] == before_a2["arrival_tiebreaker"]


def test_real_world_unchanged_with_unarrived():
    W = _build_three_inlink_network("real_unchanged")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=150.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    before = _snapshot_vehicle(a1)
    before_trigger = _snapshot_vehicle(trigger)
    estimate_level2_reference(merge, trigger, t_level_1=10, virtual_horizon=5)
    assert _snapshot_vehicle(a1) == before
    assert _snapshot_vehicle(trigger) == before_trigger


def test_type_a_fixed_outlink_maintained():
    W = _build_three_inlink_network("type_a")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=199.0, route_next_link=out, use_link_as_route=False)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=5
    )
    assert "A1" not in result["virtual_outlink_choices"]
    assert result["vehicle_transfer_timesteps"]["A1"] >= 11


def test_type_a_fixed_outlink_blocked_other_available():
    W = _build_multi_outlink_network("type_a_block")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_arrived(merge, a1, link1, out1, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, trigger])
    merge.incoming_vehicles = [a1, trigger]
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    out1.capacity_in_remain = 0.0
    _boost_capacity(merge, link1, out2, out3)
    out2.capacity_in_remain = 1e6
    out3.capacity_in_remain = 1e6
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert trace["stop_reason"] == BLOCK_INLINK
    assert "link1" in trace["blocked_inlinks"]


def test_block_inlink_then_different_inlink_transfer_clears_stop_reason():
    # A1 on inlink A is blocked; B1 on inlink B transfers in the same serve call.
    # stop_reason must not remain BLOCK_INLINK (that is recorded in blocked_inlinks).
    # Trigger sits on link3 so active_inlink ends the scan after B1 transfers; stop_reason
    # None means the queue scan finished without STOP_QUEUE or STOP_AFTER_TRANSFER.
    W = _build_three_inlink_network("block_then_transfer", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, b1, link2, out, 0, 11.0, 0.2)
    _setup_arrived(merge, trigger, link3, out, 0, 12.0, 0.3)
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link2, [b1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    link1.capacity_out_remain = 0.0
    _boost_capacity(merge, link2, link3, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert "A1" not in result["vehicle_transfer_timesteps"]
    assert result["vehicle_transfer_timesteps"]["B1"] == 10
    assert "link1" in trace["blocked_inlinks"]
    assert 0 in trace["evaluated_unit_batch_ids"]
    assert 1 in trace["evaluated_unit_batch_ids"]
    assert trace["stop_reason"] is None
    assert trace["stop_reason"] != BLOCK_INLINK


def test_type_b_route_next_link_none():
    W = _build_multi_outlink_network("type_b_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_unarrived(
        merge, a1, link1, 0, x=199.0, route_next_link=None, use_link_as_route=False
    )
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, trigger])
    merge.incoming_vehicles = [trigger]
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, out1, out2, out3)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=3
    )
    assert "A1" in result["virtual_outlink_choices"]
    assert result["vehicle_transfer_timesteps"]["A1"] >= 11


def test_type_b_route_next_link_is_veh_link():
    W = _build_multi_outlink_network("type_b_link")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, trigger])
    merge.incoming_vehicles = [trigger]
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, out1, out2, out3)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=3
    )
    assert a1.route_next_link is link1
    assert "A1" in result["virtual_outlink_choices"]


def test_type_b_modulo_two_outlinks():
    W = _build_multi_outlink_network("mod2")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, trigger])
    merge.incoming_vehicles = [trigger]
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, out1, out2, out3)
    out3.capacity_in_remain = 0.0
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=3
    )
    acceptable = sorted([out1, out2], key=lambda link: link.id)
    expected = acceptable[a1.id % 2].name
    assert result["virtual_outlink_choices"]["A1"] == expected


def test_type_b_modulo_three_outlinks():
    W = _build_multi_outlink_network("mod3")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_unarrived(merge, a1, link1, 0, x=199.0)
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, trigger])
    merge.incoming_vehicles = [trigger]
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, out1, out2, out3)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=3
    )
    acceptable = sorted([out1, out2, out3], key=lambda link: link.id)
    expected = acceptable[a1.id % 3].name
    assert result["virtual_outlink_choices"]["A1"] == expected


def test_stop_queue_arrival_wait():
    W = _build_three_inlink_network("stop_arrival")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=50.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    assert result["service_stop_trace"][0]["stop_reason"] == STOP_QUEUE


def test_stop_queue_clearance():
    W = _build_three_inlink_network("stop_clearance", clearance=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    b1 = _make_vehicle(W, "orig2", "B1")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, b1, link2, out, 0, 11.0, 0.2)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.3)
    _register_unit(merge, 0, link2, [b1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    assert result["service_stop_trace"][0]["stop_reason"] == STOP_QUEUE


def test_stop_queue_node_flow_capacity():
    W = _build_three_inlink_network("stop_node_flow")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    merge.flow_capacity_remain = 0.0
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    assert result["service_stop_trace"][0]["stop_reason"] == STOP_QUEUE


def test_stop_queue_no_acceptable_outlinks():
    W = _build_three_inlink_network("stop_outlinks")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2)
    out.capacity_in_remain = 0.0
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    assert result["service_stop_trace"][0]["stop_reason"] == STOP_QUEUE


def test_block_inlink_capacity_out():
    W = _build_three_inlink_network("block_cap_out")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    link1.capacity_out_remain = 0.0
    _boost_capacity(merge, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert trace["stop_reason"] is None
    assert "link1" in trace["blocked_inlinks"]


def test_a1_b1_a2_skip_inlink():
    W = _build_three_inlink_network("a1b1a2_skip", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    a2 = _make_vehicle(W, "orig1", "A2")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, b1, link2, out, 0, 11.0, 0.2)
    _setup_arrived(merge, a2, link1, out, 0, 11.5, 0.25)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.3)
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link2, [b1])
    _register_unit(merge, 2, link1, [a2])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    link1.capacity_out_remain = 0.0
    link2.capacity_out_remain = 0.0
    _boost_capacity(merge, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert trace["stop_reason"] == BLOCK_INLINK
    skipped = trace["skipped_units"]
    assert any(item["batch_id"] == 2 and item["reason"] == SKIP_INLINK for item in skipped)
    assert 2 not in trace["evaluated_unit_batch_ids"]


def test_a1_b1_a2_clearance_stop_before_a2():
    W = _build_three_inlink_network("a1b1a2_clear", clearance=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    a2 = _make_vehicle(W, "orig1", "A2")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, b1, link2, out, 0, 11.0, 0.2)
    _setup_arrived(merge, a2, link1, out, 0, 11.5, 0.25)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.3)
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link2, [b1])
    _register_unit(merge, 2, link1, [a2])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    link1.capacity_out_remain = 0.0
    _boost_capacity(merge, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert trace["stop_reason"] == STOP_QUEUE
    assert 2 not in trace["evaluated_unit_batch_ids"]


def test_same_unit_sequential_transfer_same_timestep():
    W = _build_three_inlink_network("seq_same_unit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    a2 = _make_vehicle(W, "orig1", "A2")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, a2, link1, out, 0, 10.5, 0.15, x=200.0)
    a1.move_remain = 20.0
    a2.move_remain = 20.0
    link1.vehicles = deque([a1, a2])
    merge.incoming_vehicles = [a1, a2, trigger]
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1, a2])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    assert result["vehicle_transfer_timesteps"]["A1"] == 10
    assert result["vehicle_transfer_timesteps"]["A2"] == 10


def test_stop_after_transfer_same_inlink():
    W = _build_multi_outlink_network("stop_after")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    a2 = _make_vehicle(W, "orig1", "A2", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_arrived(merge, a1, link1, out1, 0, 10.0, 0.1)
    _setup_arrived(merge, a2, link1, out1, 0, 10.5, 0.15, x=200.0)
    a1.move_remain = 20.0
    link1.vehicles = deque([a1, a2])
    merge.incoming_vehicles = [a1, a2, trigger]
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, a2, trigger])
    _register_unit(merge, 0, link1, [a1, a2])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, out2, out3)
    out1.capacity_in_remain = W.DELTAN
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert result["vehicle_transfer_timesteps"]["A1"] == 10
    assert trace["stop_reason"] == STOP_AFTER_TRANSFER


def test_no_switch_to_different_inlink_after_transfer():
    W = _build_three_inlink_network("no_switch")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, b1, link2, out, 0, 11.0, 0.2)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.3)
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link2, [b1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    result = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=0
    )
    trace = result["service_stop_trace"][0]
    assert result["vehicle_transfer_timesteps"]["A1"] == 10
    assert 1 not in trace["evaluated_unit_batch_ids"]


def test_invalid_route_raises():
    W = _build_three_inlink_network("invalid_route")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    a1.route_next_link = W.get_link("link2")
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    _expect_value_error(
        lambda: estimate_level2_reference(
            merge, trigger, t_level_1=10, virtual_horizon=0
        )
    )


def test_fifo_mismatch_raises():
    W = _build_three_inlink_network("fifo_err")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    a2 = _make_vehicle(W, "orig1", "A2")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, a2, link1, out, 0, 10.5, 0.15, x=200.0)
    link1.vehicles = deque([a2, a1])
    merge.incoming_vehicles = [a2, a1]
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    _expect_value_error(
        lambda: estimate_level2_reference(
            merge, trigger, t_level_1=10, virtual_horizon=0
        )
    )


def test_determinism_unarrived():
    W = _build_three_inlink_network("det_unarr")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=150.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    r1 = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=5, mimic_random_seed=0
    )
    r2 = estimate_level2_reference(
        merge, trigger, t_level_1=10, virtual_horizon=5, mimic_random_seed=99
    )
    assert r1 == r2


def test_rng_unchanged_unarrived():
    W = _build_three_inlink_network("rng_unarr")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(merge, a1, link1, 0, x=150.0)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    before = pickle.dumps(W.rng.bit_generator.state)
    estimate_level2_reference(merge, trigger, t_level_1=10, virtual_horizon=5)
    after = pickle.dumps(W.rng.bit_generator.state)
    assert before == after


def _run_ast_parse():
    for path in (
        _REFERENCE_MODULE_PATH,
        Path(__file__).resolve(),
    ):
        with open(path, encoding="utf-8") as handle:
            ast.parse(handle.read(), filename=str(path))


def main():
    _run_ast_parse()
    tests = [
        test_offset0_no_advance_before_service,
        test_offset0_single_advance_after_service,
        test_unarrived_served_on_next_timestep_not_same,
        test_unarrived_advances_and_registers_incoming,
        test_leader_follower_maintained_on_inlink,
        test_simultaneous_virtual_arrival_same_timestep,
        test_real_world_unchanged_with_unarrived,
        test_type_a_fixed_outlink_maintained,
        test_type_a_fixed_outlink_blocked_other_available,
        test_block_inlink_then_different_inlink_transfer_clears_stop_reason,
        test_type_b_route_next_link_none,
        test_type_b_route_next_link_is_veh_link,
        test_type_b_modulo_two_outlinks,
        test_type_b_modulo_three_outlinks,
        test_stop_queue_arrival_wait,
        test_stop_queue_clearance,
        test_stop_queue_node_flow_capacity,
        test_stop_queue_no_acceptable_outlinks,
        test_block_inlink_capacity_out,
        test_a1_b1_a2_skip_inlink,
        test_a1_b1_a2_clearance_stop_before_a2,
        test_same_unit_sequential_transfer_same_timestep,
        test_stop_after_transfer_same_inlink,
        test_no_switch_to_different_inlink_after_transfer,
        test_invalid_route_raises,
        test_fifo_mismatch_raises,
        test_determinism_unarrived,
        test_rng_unchanged_unarrived,
    ]
    for test in tests:
        test()
    print(f"All {len(tests)} Phase 4-6X unarrived reference tests passed.")


if __name__ == "__main__":
    main()
