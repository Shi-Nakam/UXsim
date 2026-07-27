# Phase 4-6T: small-scale BATCH revisit end-to-end integration via Node.transfer().
#
# Verifies that one vehicle visits the same BATCH node twice through the normal
# simulation path (formation, registration, and service) without assignment
# prefix violations.
#
# Run from the repository root:
#   python tests_order_control_batch_revisit_integration.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_batch_revisit_world(name="batch_revisit_integration"):
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
        order_control_type="batch",
        batch_size=1,
        order_control_batch_t_trigger_level=0,
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


def _exec_one_timestep(W):
    W.exec_simulation(duration_t2=1)


def _boost_transfer_capacity(merge, inlink, outlink):
    merge.flow_capacity_remain = 1e9
    inlink.capacity_out_remain = 1e9
    outlink.capacity_in_remain = 1e9


def _block_outlink_capacity(merge, inlink, outlink):
    merge.flow_capacity_remain = 1e9
    inlink.capacity_out_remain = 1e9
    outlink.capacity_in_remain = 0


def _advance_until(W, predicate, *, max_steps=500, error_message="condition not met"):
    for _ in range(max_steps):
        if predicate():
            return
        if not W.check_simulation_ongoing():
            break
        _exec_one_timestep(W)
    raise AssertionError(error_message)


def _ready_for_merge_batch_transfer(veh, merge, inlink):
    return (
        veh.link is inlink
        and merge.name in veh.order_control_node_arrival_times
        and veh in merge.incoming_vehicles
        and veh.order_control_current_visit is not None
        and veh.order_control_current_visit["node"] is merge
        and veh.order_control_current_visit["inlink"] is inlink
    )


def _complete_blocked_merge_pass(merge, veh, inlink, outlink):
    veh.carfollow()
    veh.update()
    _boost_transfer_capacity(merge, inlink, outlink)
    merge.transfer()


def test_same_vehicle_revisits_batch_node_and_completes_both_service_units():
    W = _build_batch_revisit_world()
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    out2 = W.get_link("out2")
    revisit_route = ["link1", "out", "mid_orig2", "link2", "out2"]

    veh = W.addVehicle("orig1", "dest", 0, name="veh_revisit_batch")
    veh.enforce_route(revisit_route, set_avoid=True)

    # --- First current visit on link1 ---
    _advance_until(
        W,
        lambda: (
            veh.link is link1
            and veh.order_control_current_visit is not None
            and veh.order_control_current_visit["node"] is merge
            and veh.order_control_current_visit["inlink"] is link1
        ),
        error_message="Vehicle did not begin first current visit on link1",
    )

    first_visit_id = veh.order_control_current_visit["visit_id"]
    assert first_visit_id == veh.order_control_visit_id
    assert veh.order_control_current_visit["batch_assignment"] is None

    # --- First merge arrival: register via Node.transfer(), then pass ---
    _advance_until(
        W,
        lambda: _ready_for_merge_batch_transfer(veh, merge, link1),
        error_message="Vehicle did not reach first merge arrival on link1",
    )

    _block_outlink_capacity(merge, link1, out)
    merge.transfer()

    first_batch_id = veh.order_control_current_visit["batch_assignment"]
    first_legacy_batch_id = veh.order_control_batch_assignments["merge"]
    first_service_unit = merge.order_control_batch_service_queue[0]
    first_service_unit_visit_ids = list(first_service_unit["visit_ids"])

    assert first_batch_id == 0
    assert first_legacy_batch_id == first_batch_id
    assert first_service_unit["batch_id"] == first_batch_id
    assert veh in first_service_unit["vehicles"]
    assert first_service_unit_visit_ids == [first_visit_id]
    assert veh.link is link1
    assert len(merge.order_control_batch_service_queue) == 1

    _complete_blocked_merge_pass(merge, veh, link1, out)
    assert veh.link is out
    assert len(merge.order_control_batch_service_queue) == 0
    assert veh.order_control_current_visit is None

    # --- Loop to second approach on link2 ---
    _advance_until(
        W,
        lambda: veh.link is link2,
        error_message="Vehicle did not return to link2 for revisit",
    )

    revisit_visit_id = veh.order_control_current_visit["visit_id"]
    assert veh.order_control_current_visit["node"] is merge
    assert veh.order_control_current_visit["inlink"] is link2
    assert revisit_visit_id != first_visit_id
    assert revisit_visit_id > first_visit_id
    assert veh.order_control_current_visit["batch_assignment"] is None
    assert veh.order_control_batch_assignments["merge"] == first_legacy_batch_id

    # --- Second merge arrival: register via Node.transfer(), then pass ---
    _advance_until(
        W,
        lambda: _ready_for_merge_batch_transfer(veh, merge, link2),
        error_message="Vehicle did not reach second merge arrival on link2",
    )

    _block_outlink_capacity(merge, link2, out2)
    merge.transfer()

    revisit_batch_id = veh.order_control_current_visit["batch_assignment"]
    revisit_service_unit = merge.order_control_batch_service_queue[0]
    revisit_service_unit_visit_ids = list(revisit_service_unit["visit_ids"])

    assert revisit_batch_id == 1
    assert revisit_batch_id != first_batch_id
    assert revisit_batch_id == revisit_service_unit["batch_id"]
    assert revisit_service_unit_visit_ids == [revisit_visit_id]
    assert revisit_service_unit_visit_ids != first_service_unit_visit_ids
    assert veh.order_control_batch_assignments["merge"] == first_legacy_batch_id
    assert veh.link is link2
    assert len(merge.order_control_batch_service_queue) == 1

    _complete_blocked_merge_pass(merge, veh, link2, out2)
    assert veh.link is out2
    assert len(merge.order_control_batch_service_queue) == 0
    assert veh.order_control_current_visit is None

    # --- Finish trip to dest ---
    _advance_until(
        W,
        lambda: veh.state == "end",
        error_message="Vehicle did not reach final destination",
    )

    assert len(merge.order_control_batch_service_queue) == 0
    assert veh.order_control_batch_assignments["merge"] == first_legacy_batch_id
    assert veh.dest.name == "dest"
    assert merge.name == "merge"


TESTS = [
    test_same_vehicle_revisits_batch_node_and_completes_both_service_units,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control batch revisit integration tests passed.")
