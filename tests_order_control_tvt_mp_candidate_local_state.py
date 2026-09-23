# Tests for one candidate's copied local state at baseline timestep T.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_local_state.py

from __future__ import annotations

import copy
import dataclasses

import numpy as np

from uxsim.order_control_tvt_mp_candidate_local_state import (
    OrderControlTvtMpBindingVisitLocalVehiclePair,
    OrderControlTvtMpCandidateLocalState,
    OrderControlTvtMpLocalLinkVehicleState,
    build_tvt_mp_candidate_local_state,
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
from uxsim.uxsim import World


def _new_world() -> World:
    world = World(
        name="tvt_mp_candidate_local_state",
        deltan=1,
        tmax=40,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig", 0, 0)
    world.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    world.addNode("dest", 2, 0)
    world.addNode("dest_b", 2, 1)
    world.addNode("west", 0, 1)
    world.addNode("sink", 0, 2)
    world.addLink("in", "orig", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("far", "west", "sink", length=200, free_flow_speed=20, number_of_lanes=1)
    return world


def _place_on_link(vehicle, link, *, x: float, route_link) -> None:
    vehicle.link = link
    vehicle.state = "run"
    vehicle.x = x
    vehicle.x_old = x - 1.0
    vehicle.x_next = x + 1.0
    vehicle.v = 4.0
    vehicle.lane = 0
    vehicle.link_arrival_time = 5.0
    vehicle.move_remain = 1.5
    vehicle.flag_waiting_for_trip_end = 0
    vehicle.route_next_link = route_link
    vehicle.leader = None
    vehicle.follower = None


def _begin_merge_visit(vehicle) -> None:
    vehicle.begin_order_control_visit_on_link_entry()


def _ready_case(*, revisit_in_front: bool = False):
    """A real merge at timestep 10, plus one outside link that must stay put."""
    world = _new_world()
    in_front = world.addVehicle("orig", "dest", 0, name="in_front")
    in_back = world.addVehicle("orig", "dest", 0, name="in_back")
    out_vehicle = world.addVehicle("orig", "dest", 0, name="out_veh")
    only_incoming = world.addVehicle("orig", "dest", 0, name="only_incoming")
    far_vehicle = world.addVehicle("west", "sink", 0, name="far_veh")
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = 10

    inlink = world.get_link("in")
    outlink = world.get_link("out")
    side_link = world.get_link("side")
    far_link = world.get_link("far")
    merge = world.get_node("merge")
    _place_on_link(in_front, inlink, x=200.0, route_link=outlink)
    _place_on_link(in_back, inlink, x=180.0, route_link=outlink)
    _place_on_link(only_incoming, inlink, x=200.0, route_link=outlink)
    _place_on_link(out_vehicle, outlink, x=20.0, route_link=None)
    _place_on_link(far_vehicle, far_link, x=30.0, route_link=None)
    in_back.leader = in_front
    in_front.follower = in_back
    inlink.vehicles.append(in_front)
    inlink.vehicles.append(in_back)
    outlink.vehicles.append(out_vehicle)
    far_link.vehicles.append(far_vehicle)
    _begin_merge_visit(in_front)
    if revisit_in_front:
        # The same vehicle is still on the inlink, but the current visit is
        # the second one. Visit id 1 is a past visit and must not be used.
        _begin_merge_visit(in_front)
    _begin_merge_visit(in_back)
    _begin_merge_visit(only_incoming)
    merge.incoming_vehicles.append(in_back)
    merge.incoming_vehicles.append(in_front)
    merge.incoming_vehicles.append(only_incoming)

    merge.flow_capacity_remain = 2.5
    merge.last_order_control_inlink = inlink
    merge.last_order_control_entry_timestep = 4
    merge.order_control_clearance_timesteps = 2
    inlink.capacity_out_remain = 3.0
    inlink.capacity_in_remain = 4.0
    outlink.capacity_out_remain = 5.0
    outlink.capacity_in_remain = 6.0
    inlink.cum_arrival.append(1)
    inlink.cum_departure.append(0)
    inlink.vehicles_enter_log[10] = in_front

    binding_visits = (
        _binding_visit(in_front, rank=1),
        _binding_visit(in_back, rank=2),
        _binding_visit(only_incoming, rank=3),
    )
    sequence = _sequence(binding_visits)
    return world, sequence


def _binding_visit(vehicle, *, rank: int, visit_id: int | None = None):
    if visit_id is None:
        visit_id = vehicle.order_control_current_visit["visit_id"]
    return OrderControlTvtMpLocalBindingRankVisit(
        visit_key=(vehicle.name, visit_id),
        vehicle_id=vehicle.id,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        binding_rank=rank,
        route_next_link_name="out",
        route_origin=(
            OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
        ),
        inlink_name="in",
        baseline_arrival_timestep=12,
        arrival_tiebreaker=0.2,
        trade_role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
    )


def _sequence(binding_visits, *, baseline_timestep_T: int = 10, node_name: str = "merge"):
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=baseline_timestep_T,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(("in_front", 1),),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=binding_visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=binding_visits,
        k_last_buyer=1,
        k_decision_window=1,
        k_fixed=1,
    )


def _rng_snapshot(world: World):
    return copy.deepcopy(
        (
            world.rng.bit_generator.state,
            world.order_control_rng.bit_generator.state,
        )
    )


def _real_snapshot(world: World) -> dict:
    merge = world.get_node("merge")
    inlink = world.get_link("in")
    return {
        "T": world.T,
        "x": {name: vehicle.x for name, vehicle in world.VEHICLES.items()},
        "incoming": [vehicle.name for vehicle in merge.incoming_vehicles],
        "flow_capacity_remain": merge.flow_capacity_remain,
        "capacity_out_remain": inlink.capacity_out_remain,
        "clearance_timestep": merge.last_order_control_entry_timestep,
        "clearance_count": merge.order_control_clearance_timesteps,
        "inlink_names": [vehicle.name for vehicle in inlink.vehicles],
        "rng": _rng_snapshot(world),
    }


def test_public_types_are_frozen_and_local_world_stays_mutable():
    assert build_tvt_mp_candidate_local_state is not None
    assert dataclasses.is_dataclass(OrderControlTvtMpCandidateLocalState)
    assert dataclasses.is_dataclass(OrderControlTvtMpBindingVisitLocalVehiclePair)
    assert dataclasses.is_dataclass(OrderControlTvtMpLocalLinkVehicleState)
    world, sequence = _ready_case()
    state = build_tvt_mp_candidate_local_state(world, sequence)
    assert isinstance(state.inlinks, tuple)
    assert isinstance(state.outlinks, tuple)
    assert isinstance(state.local_vehicles, tuple)
    assert isinstance(state.inlink_local_vehicle_states, tuple)
    assert isinstance(state.outlink_local_vehicle_states, tuple)
    assert isinstance(state.incoming_local_vehicles, tuple)
    assert isinstance(state.binding_visit_local_vehicle_pairs, tuple)
    try:
        state.local_vehicle_by_real_vehicle_name["extra"] = None  # type: ignore[index]
        raise AssertionError("expected read-only vehicle mapping")
    except TypeError:
        pass
    try:
        state.target_node_name = "other"  # type: ignore[misc]
        raise AssertionError("expected frozen local state")
    except dataclasses.FrozenInstanceError:
        pass
    state.local_vehicles[0].x = 111.0
    assert state.local_vehicles[0].x == 111.0
    assert world.VEHICLES["in_front"].x == 200.0


def test_copy_extracts_local_targets_and_keeps_initial_traffic_state():
    world, sequence = _ready_case()
    before = _real_snapshot(world)
    real_merge = world.get_node("merge")
    real_inlink = world.get_link("in")
    real_outlink = world.get_link("out")
    real_in_front = world.VEHICLES["in_front"]
    state = build_tvt_mp_candidate_local_state(world, sequence)

    assert state.local_world is not world
    assert state.real_world_timestep_T == 10
    assert state.binding_rank_sequence is sequence
    assert state.binding_rank_sequence.baseline_timestep_T == 10
    assert state.target_node_name == "merge"
    assert state.target_node is not real_merge
    assert state.target_node is state.local_world.get_node("merge")
    assert [link.name for link in state.inlinks] == ["in"]
    assert [link.name for link in state.outlinks] == ["out", "side"]
    assert state.inlinks[0] is not real_inlink
    assert state.outlinks[0] is not real_outlink
    assert state.inlinks[0] is state.local_world.get_link("in")
    assert state.outlinks[0] is state.local_world.get_link("out")

    local_in_front = state.local_vehicle_by_real_vehicle_name["in_front"]
    assert local_in_front is not real_in_front
    assert local_in_front.name == "in_front"
    assert local_in_front.id == real_in_front.id
    assert local_in_front.link is state.inlinks[0]
    assert local_in_front.follower is state.local_vehicle_by_real_vehicle_name["in_back"]
    assert state.local_vehicle_by_real_vehicle_name["in_back"].leader is local_in_front
    assert state.real_vehicle_name_by_local_vehicle_name["in_front"] == "in_front"
    assert state.local_world.VEHICLES["in_front"] is local_in_front
    assert state.local_world.LINKS_NAME_DICT["in"] is state.inlinks[0]
    assert state.local_world.NODES_NAME_DICT["merge"] is state.target_node

    assert state.inlink_local_vehicle_states[0].link is state.inlinks[0]
    assert [
        vehicle.name
        for vehicle in state.inlink_local_vehicle_states[0].vehicles_in_physical_order
    ] == ["in_front", "in_back"]
    assert [
        vehicle.name
        for vehicle in state.outlink_local_vehicle_states[0].vehicles_in_physical_order
    ] == ["out_veh"]
    assert state.outlink_local_vehicle_states[1].vehicles_in_physical_order == ()
    assert [vehicle.name for vehicle in state.incoming_local_vehicles] == [
        "in_back",
        "in_front",
        "only_incoming",
    ]
    assert [vehicle.name for vehicle in state.local_vehicles] == [
        "in_front",
        "in_back",
        "out_veh",
        "only_incoming",
    ]
    assert "far_veh" not in [vehicle.name for vehicle in state.local_vehicles]
    assert "far_veh" in state.local_world.VEHICLES
    assert state.local_world.get_link("far") is not world.get_link("far")
    assert state.local_world.get_node("west") is not world.get_node("west")

    for incoming_vehicle in state.incoming_local_vehicles:
        assert incoming_vehicle is state.local_world.VEHICLES[incoming_vehicle.name]
        assert incoming_vehicle is not world.VEHICLES[incoming_vehicle.name]
    for link_vehicle in state.inlinks[0].vehicles:
        assert link_vehicle is state.local_world.VEHICLES[link_vehicle.name]

    pair_names = [
        pair.local_vehicle_name for pair in state.binding_visit_local_vehicle_pairs
    ]
    assert pair_names == ["in_front", "in_back", "only_incoming"]
    assert [
        pair.binding_visit for pair in state.binding_visit_local_vehicle_pairs
    ] == list(sequence.visits_in_binding_order)
    for pair, binding_visit in zip(
        state.binding_visit_local_vehicle_pairs,
        sequence.visits_in_binding_order,
    ):
        assert pair.local_vehicle.name == binding_visit.visit_key[0]
        assert (
            pair.local_vehicle.order_control_current_visit["visit_id"]
            == binding_visit.visit_key[1]
        )
        assert pair.local_vehicle.order_control_current_visit["node"] is state.target_node
        assert pair.local_vehicle in state.local_vehicles

    local_merge = state.target_node
    local_inlink = state.inlinks[0]
    local_outlink = state.outlinks[0]
    assert state.local_world.T == world.T
    assert state.local_world.DELTAT == world.DELTAT
    assert state.local_world.DELTAN == world.DELTAN
    assert local_merge.flow_capacity == real_merge.flow_capacity
    assert local_merge.flow_capacity_remain == 2.5
    assert local_inlink.capacity_out_remain == 3.0
    assert local_inlink.capacity_in_remain == 4.0
    assert local_outlink.capacity_out_remain == 5.0
    assert local_outlink.capacity_in_remain == 6.0
    assert list(local_inlink.cum_arrival) == list(real_inlink.cum_arrival)
    assert local_inlink.cum_arrival is not real_inlink.cum_arrival
    assert list(local_inlink.cum_departure) == list(real_inlink.cum_departure)
    assert np.array_equal(local_inlink.traveltime_actual, real_inlink.traveltime_actual)
    assert local_inlink.traveltime_actual is not real_inlink.traveltime_actual
    assert list(local_inlink.vehicles_enter_log) == [10]
    assert local_inlink.vehicles_enter_log[10] is local_in_front
    assert local_inlink.vehicles_enter_log[10] is not real_in_front
    assert local_merge.last_order_control_inlink is local_inlink
    assert local_merge.last_order_control_inlink is not real_inlink
    assert local_merge.last_order_control_entry_timestep == 4
    assert local_merge.order_control_clearance_timesteps == 2
    assert local_in_front.x == 200.0
    assert local_in_front.v == 4.0
    assert local_in_front.lane == 0
    assert local_in_front.link_arrival_time == 5.0
    assert local_in_front.move_remain == 1.5
    assert local_in_front.route_next_link is local_outlink
    assert local_in_front.route_next_link is not world.get_link("out")
    assert local_in_front.route_next_link is state.local_world.get_link("out")
    local_out_veh = state.local_vehicle_by_real_vehicle_name["out_veh"]
    assert local_out_veh.route_next_link is None
    assert local_in_front.order_control_visit_id == real_in_front.order_control_visit_id
    assert state.local_world.rng is not world.rng
    assert state.local_world.order_control_rng is not world.order_control_rng
    assert _real_snapshot(world) == before


def test_two_local_states_do_not_share_copied_objects():
    world, sequence = _ready_case()
    first = build_tvt_mp_candidate_local_state(world, sequence)
    second = build_tvt_mp_candidate_local_state(world, sequence)
    assert first.local_world is not second.local_world
    assert first.target_node is not second.target_node
    assert first.inlinks is not second.inlinks
    assert first.inlinks[0] is not second.inlinks[0]
    assert first.local_vehicles is not second.local_vehicles
    assert first.local_vehicles[0] is not second.local_vehicles[0]
    assert (
        first.local_vehicle_by_real_vehicle_name
        is not second.local_vehicle_by_real_vehicle_name
    )
    real_x = world.VEHICLES["in_front"].x
    second_x = second.local_vehicles[0].x
    second_capacity = second.inlinks[0].capacity_out_remain
    second_incoming = [vehicle.name for vehicle in second.target_node.incoming_vehicles]
    first.local_vehicles[0].x = 50.0
    first.inlinks[0].capacity_out_remain = 0.0
    first.target_node.incoming_vehicles.append(first.local_vehicles[0])
    assert world.VEHICLES["in_front"].x == real_x
    assert second.local_vehicles[0].x == second_x
    assert second.inlinks[0].capacity_out_remain == second_capacity
    assert [vehicle.name for vehicle in second.target_node.incoming_vehicles] == (
        second_incoming
    )
    assert [vehicle.name for vehicle in world.get_node("merge").incoming_vehicles] == [
        "in_back",
        "in_front",
        "only_incoming",
    ]


def test_past_visit_id_is_not_used_for_the_same_vehicle():
    world, sequence = _ready_case(revisit_in_front=True)
    assert world.VEHICLES["in_front"].order_control_current_visit["visit_id"] == 2
    stale_visit = _binding_visit(world.VEHICLES["in_front"], rank=1, visit_id=1)
    stale_sequence = dataclasses.replace(
        sequence,
        visits_in_binding_order=(stale_visit,) + sequence.visits_in_binding_order[1:],
    )
    before = _real_snapshot(world)
    try:
        build_tvt_mp_candidate_local_state(world, stale_sequence)
        raise AssertionError("expected past visit RuntimeError")
    except RuntimeError as exc:
        assert "visit_id" in str(exc)
        assert "in_front" in str(exc)
    assert _real_snapshot(world) == before


def test_missing_binding_vehicle_is_value_error():
    world, sequence = _ready_case()
    missing_visit = dataclasses.replace(
        sequence.visits_in_binding_order[0],
        visit_key=("nobody", 1),
        vehicle_id=1,
    )
    broken = dataclasses.replace(
        sequence,
        visits_in_binding_order=(missing_visit,),
    )
    before = _real_snapshot(world)
    try:
        build_tvt_mp_candidate_local_state(world, broken)
        raise AssertionError("expected missing vehicle ValueError")
    except ValueError as exc:
        assert "nobody" in str(exc)
    assert _real_snapshot(world) == before


def test_visit_id_mismatch_is_runtime_error():
    world, sequence = _ready_case()
    mismatched = dataclasses.replace(
        sequence.visits_in_binding_order[0],
        visit_key=("in_front", 9),
    )
    broken = dataclasses.replace(
        sequence,
        visits_in_binding_order=(mismatched,),
    )
    before = _real_snapshot(world)
    try:
        build_tvt_mp_candidate_local_state(world, broken)
        raise AssertionError("expected visit id RuntimeError")
    except RuntimeError as exc:
        assert "visit_id" in str(exc)
    assert _real_snapshot(world) == before


def test_current_visit_node_mismatch_is_runtime_error():
    world, sequence = _ready_case()
    world.VEHICLES["in_front"].order_control_current_visit["node"] = world.get_node("dest")
    before_x = world.VEHICLES["in_front"].x
    try:
        build_tvt_mp_candidate_local_state(world, sequence)
        raise AssertionError("expected node mismatch RuntimeError")
    except RuntimeError as exc:
        assert "dest" in str(exc)
    assert world.VEHICLES["in_front"].x == before_x


def test_binding_vehicle_outside_local_set_is_runtime_error():
    world, sequence = _ready_case()
    far_vehicle = world.VEHICLES["far_veh"]
    far_vehicle.order_control_visit_id = 1
    far_vehicle.order_control_current_visit = {
        "visit_id": 1,
        "node": world.get_node("merge"),
        "inlink": world.get_link("far"),
        "earliest_arrival_timestep": 1,
        "arrival_time": None,
        "arrival_tiebreaker": None,
        "batch_assignment": None,
    }
    outside_visit = _binding_visit(far_vehicle, rank=1, visit_id=1)
    broken = dataclasses.replace(
        sequence,
        visits_in_binding_order=(outside_visit,),
    )
    before = _real_snapshot(world)
    try:
        build_tvt_mp_candidate_local_state(world, broken)
        raise AssertionError("expected outside-local RuntimeError")
    except RuntimeError as exc:
        assert "far_veh" in str(exc)
        assert "outside" in str(exc)
    assert _real_snapshot(world) == before


def test_timestep_mismatch_stops_before_copy():
    world, sequence = _ready_case()
    world.T = 11

    def _refuse_copy():
        raise AssertionError("copy was called")

    world.copy = _refuse_copy  # type: ignore[method-assign]
    before_x = world.VEHICLES["in_front"].x
    try:
        build_tvt_mp_candidate_local_state(world, sequence)
        raise AssertionError("expected timestep ValueError")
    except ValueError as exc:
        assert "11" in str(exc)
        assert "10" in str(exc)
    assert world.VEHICLES["in_front"].x == before_x


def test_bool_and_non_int_world_timestep_are_value_errors():
    world, sequence = _ready_case()

    def _refuse_copy():
        raise AssertionError("copy was called")

    world.copy = _refuse_copy  # type: ignore[method-assign]
    world.T = True
    try:
        build_tvt_mp_candidate_local_state(world, sequence)
        raise AssertionError("expected bool timestep ValueError")
    except ValueError as exc:
        assert "Python int" in str(exc)
    world.T = 10.0
    try:
        build_tvt_mp_candidate_local_state(world, sequence)
        raise AssertionError("expected float timestep ValueError")
    except ValueError as exc:
        assert "Python int" in str(exc)


def test_missing_copied_node_is_value_error_without_changing_real_world():
    world, sequence = _ready_case()
    broken = dataclasses.replace(sequence, node_name="absent")
    before = _real_snapshot(world)
    try:
        build_tvt_mp_candidate_local_state(world, broken)
        raise AssertionError("expected missing node ValueError")
    except ValueError as exc:
        assert "absent" in str(exc)
    assert _real_snapshot(world) == before


def test_binding_sequence_type_error_is_value_error():
    world, _sequence = _ready_case()
    try:
        build_tvt_mp_candidate_local_state(world, object())  # type: ignore[arg-type]
        raise AssertionError("expected type ValueError")
    except ValueError as exc:
        assert "binding_rank_sequence" in str(exc)


def test_frozen_auxiliary_types_reject_field_reassignment():
    world, sequence = _ready_case()
    state = build_tvt_mp_candidate_local_state(world, sequence)
    pair = state.binding_visit_local_vehicle_pairs[0]
    link_state = state.inlink_local_vehicle_states[0]
    before_vehicle_x = pair.local_vehicle.x
    before_capacity = link_state.link.capacity_out_remain
    try:
        pair.local_vehicle_name = "broken"  # type: ignore[misc]
        raise AssertionError("expected frozen binding visit pair")
    except dataclasses.FrozenInstanceError:
        pass
    try:
        link_state.link_name = "broken"  # type: ignore[misc]
        raise AssertionError("expected frozen link vehicle state")
    except dataclasses.FrozenInstanceError:
        pass
    pair.local_vehicle.x = before_vehicle_x + 1.0
    link_state.link.capacity_out_remain = before_capacity + 0.25
    assert pair.local_vehicle.x == before_vehicle_x + 1.0
    assert link_state.link.capacity_out_remain == before_capacity + 0.25


def test_route_next_link_real_world_link_leak_is_runtime_error():
    world, sequence = _ready_case()
    copied_world = world.copy()
    copied_world.VEHICLES["in_front"].route_next_link = world.get_link("out")
    before = _real_snapshot(world)

    def _return_broken_copy():
        return copied_world

    world.copy = _return_broken_copy  # type: ignore[method-assign]
    try:
        build_tvt_mp_candidate_local_state(world, sequence)
        raise AssertionError("expected route_next_link RuntimeError")
    except RuntimeError as exc:
        message = str(exc)
        assert "in_front" in message
        assert "route_next_link" in message
        assert "real World link" in message
    assert _real_snapshot(world) == before
    assert world.VEHICLES["in_front"].route_next_link is world.get_link("out")


TESTS = (
    test_public_types_are_frozen_and_local_world_stays_mutable,
    test_copy_extracts_local_targets_and_keeps_initial_traffic_state,
    test_two_local_states_do_not_share_copied_objects,
    test_past_visit_id_is_not_used_for_the_same_vehicle,
    test_missing_binding_vehicle_is_value_error,
    test_visit_id_mismatch_is_runtime_error,
    test_current_visit_node_mismatch_is_runtime_error,
    test_binding_vehicle_outside_local_set_is_runtime_error,
    test_timestep_mismatch_stops_before_copy,
    test_bool_and_non_int_world_timestep_are_value_errors,
    test_missing_copied_node_is_value_error_without_changing_real_world,
    test_binding_sequence_type_error_is_value_error,
    test_frozen_auxiliary_types_reject_field_reassignment,
    test_route_next_link_real_world_link_leak_is_runtime_error,
)


if __name__ == "__main__":
    for test_function in TESTS:
        test_function()
    print(
        "candidate local state tests passed "
        f"({len(TESTS)} tests)."
    )
