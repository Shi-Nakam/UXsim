# Vehicle link-entry counts and the physical-entry helper.
#
# This file does not change route choice, arrival tiebreakers, or merge RNG.
# Run from the repository root:
#   python tests_vehicle_link_entry_state.py

import ast

from uxsim import World
from uxsim.order_control_batch_level_2_reference import (
    _create_mimic_vehicle,
    _transfer_vehicle_reference,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    _transfer_one_vehicle_like_uxsim,
    initialize_tvt_mp_candidate_binding_transfer_state,
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_local_vehicle_advance import (
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals,
    initialize_tvt_mp_candidate_local_vehicle_advance_state,
)
from uxsim.order_control_tvt_mp_candidate_virtual_time import (
    initialize_tvt_mp_candidate_virtual_time_state,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
    OrderControlTvtMpLocalBindingTradeRole,
)


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()
    for node in W.NODES:
        node.flow_capacity_update()


def _build_merge_world(name, order_control_type="fcfs"):
    W = World(
        name=name,
        deltan=1,
        tmax=50,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type=order_control_type,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    W.set_order_control_clearance_timesteps(0)
    _prepare_network(W)
    return W


def _build_level2_mimic_world_for_real_merge(real_W, name):
    """
    Build a Level 2-style mimic World around the real order-control Node merge.

    Level 2 does not copy the full real network. For each real inlink to merge
    it adds an upstream Node named _mimic_up_{link name}. For each real outlink
    it adds a sink Node named _mimic_sink_{link name}. _create_mimic_vehicle
    places a vehicle on real inlink link1 with origin _mimic_up_link1 and
    destination merge, so those Nodes must exist in the mimic World.
    """
    real_merge = real_W.get_node("merge")
    mimic_W = World(
        name=name,
        deltan=real_W.DELTAN,
        tmax=real_W.TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    mimic_W.set_order_control_clearance_timesteps(
        real_W.order_control_clearance_timesteps
    )

    real_to_mimic_link = {}

    for real_inlink_name in real_merge.inlinks:
        real_inlink = real_W.get_link(real_inlink_name)
        upstream_name = f"_mimic_up_{real_inlink_name}"
        mimic_W.addNode(upstream_name, 0, 0)

    mimic_W.addNode(
        "merge",
        real_merge.x,
        real_merge.y,
        order_control_eligible=True,
        order_control_type=real_merge.order_control_type,
        batch_size=real_merge.batch_size,
    )

    for real_inlink_name in real_merge.inlinks:
        real_inlink = real_W.get_link(real_inlink_name)
        upstream_name = f"_mimic_up_{real_inlink_name}"
        mimic_inlink = mimic_W.addLink(
            real_inlink_name,
            upstream_name,
            "merge",
            length=real_inlink.length,
            free_flow_speed=real_inlink.u,
            number_of_lanes=real_inlink.number_of_lanes,
        )
        real_to_mimic_link[real_inlink] = mimic_inlink

    for real_outlink_name in real_merge.outlinks:
        real_outlink = real_W.get_link(real_outlink_name)
        sink_name = f"_mimic_sink_{real_outlink_name}"
        mimic_W.addNode(sink_name, 0, 0)
        mimic_outlink = mimic_W.addLink(
            real_outlink_name,
            "merge",
            sink_name,
            length=real_outlink.length,
            free_flow_speed=real_outlink.u,
            number_of_lanes=real_outlink.number_of_lanes,
        )
        real_to_mimic_link[real_outlink] = mimic_outlink

    _prepare_network(mimic_W)
    node_maps = {"real_to_mimic_link": real_to_mimic_link}
    return mimic_W, node_maps


def _build_loop_world(name):
    W = World(
        name=name,
        deltan=1,
        tmax=50,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.addNode("n1", 0, 0)
    W.addNode("n2", 1, 0)
    W.addLink("link_a", "n1", "n2", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("link_b", "n2", "n1", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare_network(W)
    return W


def _assert_value_error(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError:
        return
    raise AssertionError(f"{function.__name__} did not raise ValueError")


def _set_attempts(veh, in_trip_attempt, origin_attempt):
    veh.current_link_route_choice_attempt_count = in_trip_attempt
    veh.origin_route_choice_attempt_count = origin_attempt


def _set_arrival_visit(veh, node, inlink):
    veh.order_control_visit_id = 1
    veh.order_control_current_visit = {
        "visit_id": 1,
        "node": node,
        "inlink": inlink,
        "earliest_arrival_timestep": 0,
        "arrival_time": 1.0,
        "arrival_tiebreaker": 0.25,
        "batch_assignment": None,
    }


def _ensure_transfer_head(veh, inlink, outlink):
    if veh not in inlink.vehicles:
        inlink.vehicles.appendleft(veh)
    veh.link = inlink
    veh.state = "run"
    veh.x = inlink.length
    veh.v = inlink.u
    veh.move_remain = 0
    veh.leader = None
    veh.follower = None
    veh.link_arrival_time = 0.0
    veh.route_next_link = outlink
    node = inlink.end_node
    if veh not in node.incoming_vehicles:
        node.incoming_vehicles.append(veh)
    inlink.capacity_out_remain = 100
    outlink.capacity_in_remain = 100
    node.flow_capacity_remain = 100
    _set_arrival_visit(veh, node, inlink)
    return node


def test_new_vehicle_link_entry_state_starts_empty_and_is_not_shared():
    W = _build_merge_world("link_entry_init")
    first = W.addVehicle("orig1", "dest", 0, name="veh_first")
    second = W.addVehicle("orig2", "dest", 0, name="veh_second")
    assert first.link_entry_count_by_link_name == {}
    assert second.link_entry_count_by_link_name == {}
    assert first.current_link_route_choice_attempt_count == 0
    assert first.origin_route_choice_attempt_count == 0
    assert first.link_entry_count_by_link_name is not second.link_entry_count_by_link_name
    first.link_entry_count_by_link_name["link1"] = 1
    assert second.link_entry_count_by_link_name == {}


def test_helper_records_link_name_and_resets_only_in_trip_attempt():
    W = _build_merge_world("link_entry_helper")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_helper")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh.link = link1
    veh.order_control_visit_id = 4
    _set_attempts(veh, 3, 2)

    veh.record_successful_physical_link_entry()
    assert veh.link_entry_count_by_link_name == {"link1": 1}
    assert veh.current_link_route_choice_attempt_count == 0
    assert veh.origin_route_choice_attempt_count == 2
    assert veh.order_control_visit_id == 4
    assert veh.order_control_current_visit is None

    _set_attempts(veh, 5, 2)
    veh.record_successful_physical_link_entry()
    assert veh.link_entry_count_by_link_name["link1"] == 2

    veh.link = out
    veh.record_successful_physical_link_entry()
    assert veh.link_entry_count_by_link_name == {"link1": 2, "out": 1}
    assert veh.origin_route_choice_attempt_count == 2


def test_helper_rejects_missing_link():
    W = _build_merge_world("link_entry_missing_link")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_missing_link")
    veh.link = None
    veh.order_control_visit_id = 1
    _assert_value_error(veh.record_successful_physical_link_entry)
    assert veh.link_entry_count_by_link_name == {}
    assert veh.order_control_visit_id == 1


def test_origin_entry_success_records_the_entered_link_once():
    W = _build_merge_world("link_entry_origin_success")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_origin_ok")
    orig = W.get_node("orig1")
    link1 = W.get_link("link1")
    veh.state = "wait"
    _set_attempts(veh, 4, 2)
    orig.generation_queue.append(veh)

    orig.generate()

    assert veh in link1.vehicles
    assert veh.link is link1
    assert veh.link_entry_count_by_link_name == {"link1": 1}
    assert veh.current_link_route_choice_attempt_count == 0
    assert veh.origin_route_choice_attempt_count == 2
    assert veh.order_control_visit_id == 1


def test_origin_entry_failure_does_not_record_a_link():
    W = _build_merge_world("link_entry_origin_fail")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_origin_fail")
    orig = W.get_node("orig1")
    link1 = W.get_link("link1")
    veh.state = "wait"
    _set_attempts(veh, 4, 2)
    orig.generation_queue.append(veh)
    link1.capacity_in_remain = 0

    orig.generate()

    assert veh.link is None
    assert veh not in link1.vehicles
    assert veh.link_entry_count_by_link_name == {}
    assert veh.current_link_route_choice_attempt_count == 4
    assert veh.origin_route_choice_attempt_count == 2


def test_batch_real_transfer_records_outlink_once():
    W = _build_merge_world("link_entry_batch", order_control_type="batch")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_batch")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    merge = _ensure_transfer_head(veh, link1, out)
    veh.order_control_current_visit["batch_assignment"] = 0
    _set_attempts(veh, 6, 3)
    merge.order_control_batch_service_queue = [
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [1],
        }
    ]

    transferred = merge.serve_order_control_batch_service_queue()

    assert transferred == 1
    assert veh.link is out
    assert veh in out.vehicles
    assert veh.link_entry_count_by_link_name == {"out": 1}
    assert veh.current_link_route_choice_attempt_count == 0
    assert veh.origin_route_choice_attempt_count == 3


def test_batch_real_transfer_failure_does_not_record_outlink():
    W = _build_merge_world("link_entry_batch_fail", order_control_type="batch")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_batch_fail")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    merge = _ensure_transfer_head(veh, link1, out)
    veh.order_control_current_visit["batch_assignment"] = 0
    _set_attempts(veh, 6, 3)
    out.capacity_in_remain = 0
    merge.order_control_batch_service_queue = [
        {
            "batch_id": 0,
            "inlink": link1,
            "vehicles": [veh],
            "visit_ids": [1],
        }
    ]

    transferred = merge.serve_order_control_batch_service_queue()

    assert transferred == 0
    assert veh.link is link1
    assert veh.link_entry_count_by_link_name == {}
    assert veh.current_link_route_choice_attempt_count == 6
    assert veh.origin_route_choice_attempt_count == 3


def test_fcfs_without_clearance_records_only_a_successful_pass():
    W_ok = _build_merge_world("link_entry_fcfs_plain_ok")
    veh_ok = W_ok.addVehicle("orig1", "dest", 0, name="veh_fcfs_plain_ok")
    link_ok = W_ok.get_link("link1")
    out_ok = W_ok.get_link("out")
    merge_ok = _ensure_transfer_head(veh_ok, link_ok, out_ok)
    _set_attempts(veh_ok, 5, 1)
    merge_ok.transfer_fcfs_no_clearance()
    assert veh_ok.link is out_ok
    assert veh_ok.link_entry_count_by_link_name == {"out": 1}
    assert veh_ok.current_link_route_choice_attempt_count == 0
    assert veh_ok.origin_route_choice_attempt_count == 1

    W_fail = _build_merge_world("link_entry_fcfs_plain_fail")
    veh_fail = W_fail.addVehicle("orig1", "dest", 0, name="veh_fcfs_plain_fail")
    link_fail = W_fail.get_link("link1")
    out_fail = W_fail.get_link("out")
    _ensure_transfer_head(veh_fail, link_fail, out_fail)
    _set_attempts(veh_fail, 5, 1)
    out_fail.capacity_in_remain = 0
    W_fail.get_node("merge").transfer_fcfs_no_clearance()
    assert veh_fail.link is link_fail
    assert veh_fail.link_entry_count_by_link_name == {}
    assert veh_fail.current_link_route_choice_attempt_count == 5


def test_fcfs_with_clearance_records_only_a_successful_pass():
    W_ok = _build_merge_world("link_entry_fcfs_clear_ok")
    veh_ok = W_ok.addVehicle("orig1", "dest", 0, name="veh_fcfs_clear_ok")
    link_ok = W_ok.get_link("link1")
    out_ok = W_ok.get_link("out")
    merge_ok = _ensure_transfer_head(veh_ok, link_ok, out_ok)
    _set_attempts(veh_ok, 5, 1)
    assert W_ok._order_control_baseline_collector is None
    merge_ok.transfer_fcfs_clearance()
    assert veh_ok.link is out_ok
    assert veh_ok.link_entry_count_by_link_name == {"out": 1}
    assert veh_ok.current_link_route_choice_attempt_count == 0
    assert veh_ok.origin_route_choice_attempt_count == 1
    assert merge_ok.last_order_control_inlink is link_ok
    assert W_ok._order_control_baseline_collector is None

    W_fail = _build_merge_world("link_entry_fcfs_clear_fail")
    veh_fail = W_fail.addVehicle("orig1", "dest", 0, name="veh_fcfs_clear_fail")
    link_fail = W_fail.get_link("link1")
    out_fail = W_fail.get_link("out")
    _ensure_transfer_head(veh_fail, link_fail, out_fail)
    _set_attempts(veh_fail, 5, 1)
    out_fail.capacity_in_remain = 0
    W_fail.get_node("merge").transfer_fcfs_clearance()
    assert veh_fail.link is link_fail
    assert veh_fail.link_entry_count_by_link_name == {}
    assert veh_fail.current_link_route_choice_attempt_count == 5


def test_common_physical_transfer_and_normal_merge_record_once():
    W_direct = _build_merge_world("link_entry_common_direct")
    veh_direct = W_direct.addVehicle("orig1", "dest", 0, name="veh_common_direct")
    link_direct = W_direct.get_link("link1")
    out_direct = W_direct.get_link("out")
    merge_direct = _ensure_transfer_head(veh_direct, link_direct, out_direct)
    _set_attempts(veh_direct, 7, 1)
    merge_direct._transfer_one_vehicle_between_links(
        veh_direct,
        link_direct,
        out_direct,
    )
    assert veh_direct.link_entry_count_by_link_name == {"out": 1}
    assert veh_direct.current_link_route_choice_attempt_count == 0
    assert veh_direct.origin_route_choice_attempt_count == 1

    W_merge = _build_merge_world("link_entry_normal_merge")
    veh_merge = W_merge.addVehicle("orig1", "dest", 0, name="veh_normal_merge")
    link_merge = W_merge.get_link("link1")
    out_merge = W_merge.get_link("out")
    merge = _ensure_transfer_head(veh_merge, link_merge, out_merge)
    _set_attempts(veh_merge, 7, 1)
    merge._transfer_normal_merge()
    assert veh_merge.link is out_merge
    assert veh_merge.link_entry_count_by_link_name == {"out": 1}
    assert veh_merge.current_link_route_choice_attempt_count == 0


def test_formal_reentry_keeps_cumulative_link_counts():
    W = _build_loop_world("link_entry_loop")
    veh = W.addVehicle("n1", "n2", 0, name="veh_loop")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    n2 = _ensure_transfer_head(veh, link_a, link_b)
    n2._transfer_one_vehicle_between_links(veh, link_a, link_b)
    assert veh.link_entry_count_by_link_name == {"link_b": 1}

    n1 = _ensure_transfer_head(veh, link_b, link_a)
    n1._transfer_one_vehicle_between_links(veh, link_b, link_a)
    assert veh.link_entry_count_by_link_name == {"link_b": 1, "link_a": 1}

    n2_again = _ensure_transfer_head(veh, link_a, link_b)
    n2_again._transfer_one_vehicle_between_links(veh, link_a, link_b)
    assert veh.link_entry_count_by_link_name == {"link_b": 2, "link_a": 1}
    assert veh.origin_route_choice_attempt_count == 0


def test_candidate_binding_updates_only_the_copied_vehicle():
    W = _build_merge_world("link_entry_binding_real")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_binding")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    _ensure_transfer_head(veh, link1, out)
    veh.link_entry_count_by_link_name = {"link1": 1}
    _set_attempts(veh, 8, 3)
    copied = W.copy()
    local_veh = copied.VEHICLES["veh_binding"]
    local_merge = copied.get_node("merge")
    local_link = copied.get_link("link1")
    local_out = copied.get_link("out")
    assert local_veh.link_entry_count_by_link_name is not veh.link_entry_count_by_link_name
    assert local_veh.link_entry_count_by_link_name == {"link1": 1}

    _transfer_one_vehicle_like_uxsim(
        target_node=local_merge,
        local_world=copied,
        local_vehicle=local_veh,
        inlink=local_link,
        outlink=local_out,
    )

    assert local_veh.link is local_out
    assert local_veh.link_entry_count_by_link_name == {"link1": 1, "out": 1}
    assert local_veh.current_link_route_choice_attempt_count == 0
    assert local_veh.origin_route_choice_attempt_count == 3
    assert veh.link_entry_count_by_link_name == {"link1": 1}
    assert veh.current_link_route_choice_attempt_count == 8
    assert veh.link is link1


def _candidate_local_advance_binding_visit(vehicle, *, route_name, inlink_name):
    current_visit = vehicle.order_control_current_visit
    return OrderControlTvtMpLocalBindingRankVisit(
        visit_key=(vehicle.name, current_visit["visit_id"]),
        vehicle_id=vehicle.id,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        binding_rank=1,
        route_next_link_name=route_name,
        route_origin=(
            OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
        ),
        inlink_name=inlink_name,
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.2,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
    )


def _candidate_local_advance_rank_sequence(visit):
    visit_key = visit.visit_key
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(visit_key,),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=(visit,),
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=(visit,),
        k_last_buyer=1,
        k_decision_window=1,
        k_fixed=1,
    )


def test_candidate_local_advance_does_not_record_a_new_link():
    # 1. World with a TVT-MP candidate target node (same shape as other local-advance tests).
    W = World(
        name="link_entry_candidate_advance",
        deltan=1,
        tmax=40,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.addNode("orig1", 0, 0)
    W.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
        flow_capacity=1.0,
        number_of_lanes=1,
    )
    W.addNode("dest", 2, 0)
    W.addLink(
        "link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1
    )
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    W.T = 10

    # 2. Vehicle on inlink, not yet at the node end (local advance moves along this link).
    link1 = W.get_link("link1")
    out = W.get_link("out")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_advance")
    veh.link = link1
    veh.state = "run"
    veh.x = 20.0
    veh.x_old = 20.0
    veh.x_next = 20.0
    veh.v = 4.0
    veh.lane = 0
    veh.leader = None
    veh.follower = None
    veh.route_next_link = out
    veh.link_arrival_time = 5.0
    veh.move_remain = 2.0
    veh.flag_waiting_for_trip_end = 0
    W.VEHICLES_RUNNING[veh.name] = veh
    link1.vehicles.append(veh)
    veh.begin_order_control_visit_on_link_entry()

    # 3. Existing link-entry counts and both route-choice attempt counters.
    veh.link_entry_count_by_link_name = {"link1": 1}
    _set_attempts(veh, 4, 2)

    visit = _candidate_local_advance_binding_visit(
        veh,
        route_name="out",
        inlink_name="link1",
    )
    local_state = build_tvt_mp_candidate_local_state(
        W,
        _candidate_local_advance_rank_sequence(visit),
    )
    local_state.target_node.flow_capacity_remain = 10.0
    for link in local_state.inlinks + local_state.outlinks:
        link.capacity_out_remain = 10.0
        link.capacity_in_remain = 10.0
    # Block binding outflow so this step only scans; local advance does the inlink motion.
    local_state.local_world.get_link("link1").capacity_out_remain = 0.0

    clock = initialize_tvt_mp_candidate_virtual_time_state(local_state)
    transfer_state = initialize_tvt_mp_candidate_binding_transfer_state(clock)
    scan_result = scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
        transfer_state
    )
    advance_state = initialize_tvt_mp_candidate_local_vehicle_advance_state(
        transfer_state
    )
    local_veh = local_state.local_vehicle_by_real_vehicle_name["veh_advance"]
    local_link1 = local_state.local_world.get_link("link1")

    # 4. Candidate local advance (not Level 2 _advance_inlink_vehicles).
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
        advance_state,
        scan_result,
    )

    # 5. Same inlink; counters unchanged (no physical link entry helper).
    assert local_veh.link is local_link1
    assert local_veh.link_entry_count_by_link_name == {"link1": 1}
    assert local_veh.current_link_route_choice_attempt_count == 4
    assert local_veh.origin_route_choice_attempt_count == 2
    assert veh.link_entry_count_by_link_name == {"link1": 1}
    assert veh.current_link_route_choice_attempt_count == 4


def test_level2_reference_transfer_does_not_record_link_entry():
    real_W = _build_merge_world("link_entry_level2_real", order_control_type="batch")
    mimic_W, node_maps = _build_level2_mimic_world_for_real_merge(
        real_W,
        "link_entry_level2_mimic",
    )
    real_veh = real_W.addVehicle("orig1", "dest", 0, name="veh_level2")
    real_link = real_W.get_link("link1")
    real_out = real_W.get_link("out")
    real_merge = _ensure_transfer_head(real_veh, real_link, real_out)
    real_veh.link_entry_count_by_link_name = {"link1": 4}
    _set_attempts(real_veh, 9, 5)
    mimic_veh = _create_mimic_vehicle(
        mimic_W,
        real_veh,
        real_merge,
        mimic_W.get_node("merge"),
        node_maps,
    )
    assert mimic_veh.link_entry_count_by_link_name == {}
    assert mimic_veh.current_link_route_choice_attempt_count == 0
    assert mimic_veh.origin_route_choice_attempt_count == 0
    assert mimic_veh.link_entry_count_by_link_name is not real_veh.link_entry_count_by_link_name

    mimic_in = mimic_W.get_link("link1")
    mimic_out = mimic_W.get_link("out")
    mimic_in.capacity_out_remain = 100
    mimic_out.capacity_in_remain = 100
    _transfer_vehicle_reference(
        mimic_W.get_node("merge"),
        mimic_W,
        mimic_veh,
        mimic_in,
        mimic_out,
    )

    assert mimic_veh.link is mimic_out
    assert mimic_veh.link_entry_count_by_link_name == {}
    assert mimic_veh.current_link_route_choice_attempt_count == 0
    assert real_veh.link_entry_count_by_link_name == {"link1": 4}


def test_begin_visit_and_level2_do_not_call_the_link_entry_helper():
    import uxsim.order_control_batch_level_2_reference as level2_module
    import uxsim.order_control_tvt_mp_candidate_local_vehicle_advance as advance_module
    import uxsim.uxsim as uxsim_module

    helper_name = "record_successful_physical_link_entry"
    with open(level2_module.__file__, encoding="utf-8") as level2_file:
        level2_tree = ast.parse(level2_file.read())
    with open(advance_module.__file__, encoding="utf-8") as advance_file:
        advance_tree = ast.parse(advance_file.read())
    with open(uxsim_module.__file__, encoding="utf-8") as uxsim_file:
        uxsim_tree = ast.parse(uxsim_file.read())

    def _calls_helper(tree):
        for node in ast.walk(tree):
            if type(node) is ast.Attribute and node.attr == helper_name:
                return True
        return False

    assert _calls_helper(level2_tree) is False
    assert _calls_helper(advance_tree) is False

    begin_function = None
    for node in ast.walk(uxsim_tree):
        if (
            type(node) is ast.FunctionDef
            and node.name == "begin_order_control_visit_on_link_entry"
        ):
            begin_function = node
            break
    assert begin_function is not None
    assert _calls_helper(begin_function) is False


def test_world_copy_keeps_link_entry_state_on_a_distinct_dict():
    W = _build_merge_world("link_entry_copy")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_copy")
    veh.link = W.get_link("link1")
    veh.record_successful_physical_link_entry()
    veh.current_link_route_choice_attempt_count = 4
    veh.origin_route_choice_attempt_count = 2
    copied = W.copy()
    copied_veh = copied.VEHICLES["veh_copy"]

    assert copied_veh is not veh
    assert copied_veh.link_entry_count_by_link_name == {"link1": 1}
    assert copied_veh.current_link_route_choice_attempt_count == 4
    assert copied_veh.origin_route_choice_attempt_count == 2
    assert copied_veh.link_entry_count_by_link_name is not veh.link_entry_count_by_link_name
    copied_veh.link_entry_count_by_link_name["link1"] = 9
    assert veh.link_entry_count_by_link_name == {"link1": 1}


def test_single_path_trip_still_uses_the_only_route():
    W = World(
        name="link_entry_single_path",
        deltan=1,
        tmax=80,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.addNode("orig", 0, 0)
    W.addNode("mid", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink("first", "orig", "mid", length=20, free_flow_speed=20, number_of_lanes=1)
    W.addLink("second", "mid", "dest", length=20, free_flow_speed=20, number_of_lanes=1)
    veh = W.addVehicle("orig", "dest", 0, name="veh_single_path")
    W.exec_simulation()

    assert veh.state == "end"
    assert veh.link_entry_count_by_link_name == {"first": 1, "second": 1}
    assert veh.origin_route_choice_attempt_count == 0
    assert veh.current_link_route_choice_attempt_count == 0


TESTS = [
    test_new_vehicle_link_entry_state_starts_empty_and_is_not_shared,
    test_helper_records_link_name_and_resets_only_in_trip_attempt,
    test_helper_rejects_missing_link,
    test_origin_entry_success_records_the_entered_link_once,
    test_origin_entry_failure_does_not_record_a_link,
    test_batch_real_transfer_records_outlink_once,
    test_batch_real_transfer_failure_does_not_record_outlink,
    test_fcfs_without_clearance_records_only_a_successful_pass,
    test_fcfs_with_clearance_records_only_a_successful_pass,
    test_common_physical_transfer_and_normal_merge_record_once,
    test_formal_reentry_keeps_cumulative_link_counts,
    test_candidate_binding_updates_only_the_copied_vehicle,
    test_candidate_local_advance_does_not_record_a_new_link,
    test_level2_reference_transfer_does_not_record_link_entry,
    test_begin_visit_and_level2_do_not_call_the_link_entry_helper,
    test_world_copy_keeps_link_entry_state_on_a_distinct_dict,
    test_single_path_trip_still_uses_the_only_route,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Vehicle link-entry state tests passed.")
