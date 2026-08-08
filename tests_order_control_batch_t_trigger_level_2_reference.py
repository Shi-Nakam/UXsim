# Phase 4-6W: mimic-World Level 2 t_trigger reference model tests.
#
# Run from the repository root:
#   python tests_order_control_batch_t_trigger_level_2_reference.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import ast
import copy
import importlib.util
import pickle
import time
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


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_three_inlink_network(name="l2_ref", clearance=0):
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


def _make_vehicle(W, orig_name, name):
    return W.addVehicle(orig_name, "dest", 0, name=name)


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


def _register_unit(merge, batch_id, inlink, vehicles):
    visit_ids = []
    for veh in vehicles:
        visit = veh.order_control_current_visit
        visit["batch_assignment"] = batch_id
        merge_name = merge.name
        veh.order_control_batch_assignments[merge_name] = batch_id
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


def _snapshot_world_state(merge, vehicles):
    return {
        "W_T": merge.W.T,
        "service_queue": [
            {
                "batch_id": unit["batch_id"],
                "inlink": unit["inlink"].name,
                "vehicles": [veh.name for veh in unit["vehicles"]],
                "visit_ids": list(unit["visit_ids"]),
            }
            for unit in merge.order_control_batch_service_queue
        ],
        "last_inlink": (
            merge.last_order_control_inlink.name
            if merge.last_order_control_inlink is not None
            else None
        ),
        "last_entry": merge.last_order_control_entry_timestep,
        "next_id": merge.order_control_batch_next_id,
        "flow_capacity_remain": merge.flow_capacity_remain,
        "rng_state": copy.deepcopy(merge.W.rng.bit_generator.state),
        "vehicles": {
            veh.name: {
                "state": veh.state,
                "link": veh.link.name if veh.link is not None else None,
                "x": veh.x,
                "v": veh.v,
                "route_next_link": (
                    veh.route_next_link.name
                    if veh.route_next_link is not None
                    else None
                ),
                "assignment": copy.copy(veh.order_control_batch_assignments),
                "visit": (
                    None
                    if veh.order_control_current_visit is None
                    else {
                        "visit_id": veh.order_control_current_visit["visit_id"],
                        "node": veh.order_control_current_visit["node"].name,
                        "inlink": veh.order_control_current_visit["inlink"].name,
                        "earliest_arrival_timestep": veh.order_control_current_visit[
                            "earliest_arrival_timestep"
                        ],
                        "arrival_time": veh.order_control_current_visit.get("arrival_time"),
                        "arrival_tiebreaker": veh.order_control_current_visit.get(
                            "arrival_tiebreaker"
                        ),
                        "batch_assignment": veh.order_control_current_visit.get(
                            "batch_assignment"
                        ),
                    }
                ),
            }
            for veh in vehicles
        },
        "link_vehicles": {
            link.name: [veh.name for veh in link.vehicles]
            for link in list(merge.inlinks.values()) + list(merge.outlinks.values())
        },
        "capacity": {
            link.name: {
                "capacity_in_remain": link.capacity_in_remain,
                "capacity_out_remain": link.capacity_out_remain,
            }
            for link in list(merge.inlinks.values()) + list(merge.outlinks.values())
        },
    }


def _assert_world_unchanged(before, after):
    assert before["W_T"] == after["W_T"]
    assert before["service_queue"] == after["service_queue"]
    assert before["last_inlink"] == after["last_inlink"]
    assert before["last_entry"] == after["last_entry"]
    assert before["next_id"] == after["next_id"]
    assert before["flow_capacity_remain"] == after["flow_capacity_remain"]
    assert before["rng_state"] == after["rng_state"]
    assert before["vehicles"] == after["vehicles"]
    assert before["link_vehicles"] == after["link_vehicles"]
    assert before["capacity"] == after["capacity"]


def _expect_value_error(callable_obj):
    try:
        callable_obj()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_case1_one_unit_clearance_zero():
    # Expected timeline (W.T starts at 10):
    # T=10: service unit A on link1 transfers; trigger on link2 blocked by same-call inlink change.
    # T=11: clearance satisfied (11-10>0); trigger transfers.
    W = _build_three_inlink_network("case1", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    before = _snapshot_world_state(merge, [a1, trigger])
    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    after = _snapshot_world_state(merge, [a1, trigger])

    assert result["resolved"] is True
    assert result["t_virtual_trigger"] == 11
    assert result["t_level_2_candidate"] == max(t_level_1, 11)
    assert result["snapshot_timestep"] == 10
    _assert_world_unchanged(before, after)


def test_case2_one_unit_clearance_one():
    # Expected timeline:
    # T=10: A transfers from link1.
    # T=12: trigger on link2 transfers (needs W.T-last_entry>1 with clearance=1).
    W = _build_three_inlink_network("case2", clearance=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["t_virtual_trigger"] == 12
    assert result["t_level_2_candidate"] == max(t_level_1, 12)


def test_case3_two_units_clearance_zero():
    # Expected timeline:
    # T=10: unit on link1 transfers.
    # T=11: unit on link2 transfers.
    # T=12: trigger on link3 transfers.
    W = _build_three_inlink_network("case3", clearance=0)
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
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, link3, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["t_virtual_trigger"] == 12
    assert result["t_level_2_candidate"] == max(t_level_1, 12)


def test_case4_two_units_clearance_one():
    # Expected timeline:
    # T=10: link1 unit transfers.
    # T=12: link2 unit transfers (clearance=1 after link1 at T=10).
    # T=14: trigger on link3 transfers.
    W = _build_three_inlink_network("case4", clearance=1)
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
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, link3, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["t_virtual_trigger"] == 14
    assert result["t_level_2_candidate"] == max(t_level_1, 14)


def test_capacity_refill_after_depletion():
    # Expected timeline (snapshot W.T=10, capacity_out_remain=0 on inlinks):
    # T=10 (offset=0): no capacity refill; A1 does not transfer.
    # T=11 (offset=1): capacity refills; A1 transfers; trigger later.
    W = _build_three_inlink_network("cap_refill", clearance=0)
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
    link2.capacity_out_remain = 0.0
    out.capacity_in_remain = 1e6
    merge.flow_capacity_remain = 1e6
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result_horizon_zero = estimate_level2_reference(
        merge, trigger, t_level_1, virtual_horizon=0
    )
    assert result_horizon_zero["resolved"] is False
    assert "A1" not in result_horizon_zero["vehicle_transfer_timesteps"]

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["vehicle_transfer_timesteps"]["A1"] == 11
    assert result["vehicle_transfer_timesteps"]["A1"] > result["snapshot_timestep"]


def test_same_timestep_same_inlink_multi_pass():
    W = _build_three_inlink_network("same_t_multi", clearance=0)
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

    # Expected timeline:
    # T=10: A1 and A2 transfer from the same service unit at the same W.T.
    # T=11: trigger transfers after outlink space recovers from two entering vehicles.
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["vehicle_transfer_timesteps"]["A1"] == 10
    assert result["vehicle_transfer_timesteps"]["A2"] == 10
    assert (
        result["vehicle_transfer_timesteps"]["A1"]
        == result["vehicle_transfer_timesteps"]["A2"]
    )
    assert result["t_virtual_trigger"] == 11


def test_outlink_entrance_recovery_by_vehicle_advance():
    # Expected timeline:
    # T=10: blocker at x=0 occupies outlink entrance; trigger cannot enter.
    # T=11: blocker advances; entrance space recovers; trigger transfers.
    # Blocker remains on outlink (no sink end-trip yet).
    W = _build_three_inlink_network("outlink_advance", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    blocker = _make_vehicle(W, "orig1", "BLOCK")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    blocker.link = out
    blocker.state = "run"
    blocker.x = 0.0
    blocker.v = 0.0
    blocker.x_old = 0.0
    blocker.x_next = 0.0
    blocker.link_arrival_time = 0.0
    blocker.route_next_link = None
    out.vehicles.append(blocker)
    W.VEHICLES_RUNNING[blocker.name] = blocker
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    out.capacity_in_remain = 1e6
    link2.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result_horizon_zero = estimate_level2_reference(
        merge, trigger, t_level_1, virtual_horizon=0
    )
    assert result_horizon_zero["resolved"] is False
    assert "TRIG" not in result_horizon_zero["vehicle_transfer_timesteps"]

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=30)
    assert result["resolved"] is True
    assert result["t_virtual_trigger"] == 11
    assert result["vehicle_transfer_timesteps"]["TRIG"] == 11
    assert "BLOCK" not in result["sink_end_trip_trace"]


def test_sink_standard_end_trip_trace():
    # Expected timeline (blocker near outlink end, independent of trigger passage):
    # T=10: blocker reaches sink end; flag_waiting_for_trip_end; end_trip removes it.
    W = _build_three_inlink_network("sink_end_trip", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    blocker = _make_vehicle(W, "orig1", "BLOCK")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    blocker.link = out
    blocker.state = "run"
    blocker.x = 199.0
    blocker.v = 20.0
    blocker.x_old = 199.0
    blocker.x_next = 199.0
    blocker.link_arrival_time = 0.0
    blocker.route_next_link = None
    out.vehicles.append(blocker)
    W.VEHICLES_RUNNING[blocker.name] = blocker
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    out.capacity_in_remain = 0.0
    link2.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=0)
    trace = result["sink_end_trip_trace"]["BLOCK"]
    # outlink_removal_timestep is recorded only after end_trip() and a post-call
    # check that BLOCK is no longer in outlink.vehicles (see _observe_sink_end_trip).
    assert trace["sink_arrival_timestep"] == 10
    assert trace["flag_waiting_for_trip_end_timestep"] == 10
    assert trace["end_trip_timestep"] == 10
    assert trace["outlink_removal_timestep"] == 10
    assert trace["end_trip_timestep"] == trace["outlink_removal_timestep"]


def test_trigger_rear_vehicle_excluded():
    W = _build_three_inlink_network("rear_excluded", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    rear = _make_vehicle(W, "orig2", "REAR")
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    rear.link = link2
    rear.state = "run"
    rear.x = 150.0
    rear.route_next_link = out
    link2.vehicles = deque([trigger, rear])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["t_virtual_trigger"] == 10
    assert rear.link is link2


def test_simultaneous_arrival_trigger_rank_key():
    W = _build_three_inlink_network("simul_trigger", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    cand_low = _make_vehicle(W, "orig2", "CAND_LOW")
    cand_high = _make_vehicle(W, "orig3", "CAND_HIGH")
    _setup_arrived(merge, cand_low, link2, out, 0, 12.0, 0.5)
    _setup_arrived(merge, cand_high, link3, out, 0, 12.0, 0.1)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link2, link3, out)
    candidates = merge.get_order_control_batch_trigger_candidates()
    selected = candidates[0]
    assert selected.name == "CAND_HIGH"
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(selected)
    result = estimate_level2_reference(merge, selected, t_level_1, virtual_horizon=20)
    assert result["resolved"] is True
    assert result["trigger_vehicle_name"] == "CAND_HIGH"


def test_virtual_horizon_exceeded():
    W = _build_three_inlink_network("horizon", clearance=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    result = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=0)
    assert result["resolved"] is False
    assert result["t_virtual_trigger"] is None
    assert result["t_level_2_candidate"] == t_level_1
    assert result["reason"] == "virtual_horizon_exceeded"


def test_visit_id_mismatch_raises():
    W = _build_three_inlink_network("visit_mismatch", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig2", "A1")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link2, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link2, [a1])
    merge.order_control_batch_service_queue[0]["visit_ids"] = [999]
    W.T = 10
    _boost_capacity(merge, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    _expect_value_error(
        lambda: estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=5)
    )


def test_assignment_mismatch_raises():
    W = _build_three_inlink_network("assign_mismatch", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig2", "A1")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link2, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link2, [a1])
    a1.order_control_batch_assignments[merge.name] = 99
    a1.order_control_current_visit["batch_assignment"] = 99
    W.T = 10
    _boost_capacity(merge, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    _expect_value_error(
        lambda: estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=5)
    )


def test_inlink_mismatch_raises():
    W = _build_three_inlink_network("inlink_mismatch", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.order_control_batch_service_queue[0]["inlink"] = link2
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    _expect_value_error(
        lambda: estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=5)
    )


def test_unassigned_vehicle_ahead_of_service_unit_raises():
    # Physical FIFO: [UNASSIGNED, A1 assigned in service unit]
    W = _build_three_inlink_network("prefix_inconsistency", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    blocker = _make_vehicle(W, "orig1", "UNASSIGNED")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    blocker.link = link1
    blocker.state = "run"
    blocker.x = 150.0
    blocker.v = 20.0
    blocker.route_next_link = out
    _sync_visit(blocker, merge, link1, 0, 9.0, 0.05)
    link1.vehicles = deque([blocker, a1])
    merge.incoming_vehicles = [a1, trigger]
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    _expect_value_error(
        lambda: estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=5)
    )


def test_real_world_unchanged():
    W = _build_three_inlink_network("unchanged", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    before = _snapshot_world_state(merge, [a1, trigger])
    estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    after = _snapshot_world_state(merge, [a1, trigger])
    _assert_world_unchanged(before, after)


def test_rng_unchanged():
    W = _build_three_inlink_network("rng", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = 10
    _boost_capacity(merge, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    before = pickle.dumps(W.rng.bit_generator.state)
    estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=10, mimic_random_seed=0)
    estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=10, mimic_random_seed=99)
    after = pickle.dumps(W.rng.bit_generator.state)
    assert before == after


def test_determinism():
    W = _build_three_inlink_network("determinism", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)

    r1 = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20, mimic_random_seed=0)
    r2 = estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20, mimic_random_seed=12345)
    assert r1 == r2


def _build_minimal_unfinalized_world(name="mini_finalize"):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.addNode("orig", 0, 0)
    W.addNode("dest", 1, 0)
    W.addLink(
        "link",
        "orig",
        "dest",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    return W


def test_finalize_scenario_create_analyzer_flag():
    from unittest.mock import patch

    import uxsim.uxsim as uxsim_module

    with patch.object(uxsim_module, "Analyzer") as mock_analyzer:
        W_default = _build_minimal_unfinalized_world("default_analyzer")
        W_default.finalize_scenario()
        assert mock_analyzer.call_count == 1
        assert hasattr(W_default, "analyzer")

        W_true = _build_minimal_unfinalized_world("explicit_true_analyzer")
        W_true.finalize_scenario(create_analyzer=True)
        assert mock_analyzer.call_count == 2
        assert hasattr(W_true, "analyzer")

        W_false = _build_minimal_unfinalized_world("skip_analyzer")
        W_false.finalize_scenario(create_analyzer=False)
        assert mock_analyzer.call_count == 2
        assert not hasattr(W_false, "analyzer")
        assert W_false.finalized == 1


def test_level2_reference_skips_mimic_analyzer():
    from unittest.mock import patch

    import uxsim.uxsim as uxsim_module

    W = _build_three_inlink_network("skip_mimic_analyzer", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    before = _snapshot_world_state(merge, [a1, trigger])

    with patch.object(uxsim_module, "Analyzer") as mock_analyzer:
        with patch(
            "matplotlib.font_manager.findSystemFonts", return_value=[]
        ) as mock_find_fonts:
            result = estimate_level2_reference(
                merge, trigger, t_level_1, virtual_horizon=20
            )
        assert mock_analyzer.call_count == 0
        assert mock_find_fonts.call_count == 0

    assert isinstance(result, dict)
    assert isinstance(result["resolved"], bool)
    if result["resolved"]:
        assert isinstance(result["t_level_2_candidate"], int)
        assert result["t_level_2_candidate"] >= t_level_1
    after = _snapshot_world_state(merge, [a1, trigger])
    _assert_world_unchanged(before, after)


def _measure_reference_runtime():
    W = _build_three_inlink_network("timing", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = 10
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    start = time.perf_counter()
    estimate_level2_reference(merge, trigger, t_level_1, virtual_horizon=20)
    return time.perf_counter() - start


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
        test_case1_one_unit_clearance_zero,
        test_case2_one_unit_clearance_one,
        test_case3_two_units_clearance_zero,
        test_case4_two_units_clearance_one,
        test_capacity_refill_after_depletion,
        test_same_timestep_same_inlink_multi_pass,
        test_outlink_entrance_recovery_by_vehicle_advance,
        test_sink_standard_end_trip_trace,
        test_trigger_rear_vehicle_excluded,
        test_simultaneous_arrival_trigger_rank_key,
        test_virtual_horizon_exceeded,
        test_visit_id_mismatch_raises,
        test_assignment_mismatch_raises,
        test_inlink_mismatch_raises,
        test_unassigned_vehicle_ahead_of_service_unit_raises,
        test_real_world_unchanged,
        test_rng_unchanged,
        test_determinism,
        test_finalize_scenario_create_analyzer_flag,
        test_level2_reference_skips_mimic_analyzer,
    ]
    for test in tests:
        test()
    runtime = _measure_reference_runtime()
    print(f"All {len(tests)} Level 2 reference tests passed.")
    print(
        "Single Level 2 reference-call time including mimic-World build "
        "but excluding real-World fixture setup: "
        f"{runtime * 1000:.2f} ms"
    )
    return runtime


if __name__ == "__main__":
    main()
