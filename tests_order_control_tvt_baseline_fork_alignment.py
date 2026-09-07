# Unit tests for TVT baseline fork and per-Node alignment connection
# (design memo §25.25.34.36).
#
# Run from the repository root:
#   python tests_order_control_tvt_baseline_fork_alignment.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import patch

from uxsim import World
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
    align_snapshot_undetermined_visits_with_node_baseline,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
    run_snapshot_fixed_baseline_fork_and_align_undetermined_visits,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


# --- shared helpers ---


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_time_value_junction_world(
    *,
    name="tvt_fork_align_time_value_junction",
    tmax=300,
):
    W = World(
        name=name,
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode(
        "junction",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("dest", 2, 0)
    W.addLink("in", "orig", "junction", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "junction", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _build_two_time_value_nodes_world(
    *,
    name="tvt_fork_align_two_time_value_nodes",
    tmax=300,
):
    W = World(
        name=name,
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig_a", 0, 0)
    W.addNode(
        "junction_a",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("mid", 2, 0)
    W.addNode(
        "junction_b",
        3,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("dest", 4, 0)
    W.addLink("in_a", "orig_a", "junction_a", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("mid_link", "junction_a", "mid", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("in_b", "mid", "junction_b", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out_b", "junction_b", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _advance_until_on_inlink(vehicle, inlink_name):
    while vehicle.link is None or vehicle.link.name != inlink_name:
        if not vehicle.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {inlink_name}")
        vehicle.W.exec_simulation(duration_t2=vehicle.W.DELTAT)


def _place_arrived_vehicle_at_snapshot(
    W,
    vehicle,
    *,
    inlink_name,
    target_node_name,
    outlink_name,
    arrival_timestep,
    arrival_tiebreaker=0.25,
    snapshot_timestep,
):
    inlink = W.get_link(inlink_name)
    outlink = W.get_link(outlink_name)
    target_node = W.get_node(target_node_name)
    W.T = snapshot_timestep
    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = inlink.length
    vehicle.route_next_link = outlink
    vehicle.link_arrival_time = float(arrival_timestep * W.DELTAT)
    if vehicle not in inlink.vehicles:
        inlink.vehicles.append(vehicle)
    if vehicle not in target_node.incoming_vehicles:
        target_node.incoming_vehicles.append(vehicle)
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise AssertionError("Expected current visit before arrived placement")
    current_visit["arrival_time"] = arrival_timestep * W.DELTAT
    current_visit["arrival_tiebreaker"] = arrival_tiebreaker


def _place_not_yet_arrived_vehicle_at_snapshot(
    W,
    vehicle,
    *,
    inlink_name,
    snapshot_timestep,
    x_position=180.0,
):
    inlink = W.get_link(inlink_name)
    W.T = snapshot_timestep
    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = x_position
    vehicle.link_arrival_time = float((snapshot_timestep - 1) * W.DELTAT)
    if vehicle not in inlink.vehicles:
        inlink.vehicles.append(vehicle)
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise AssertionError("Expected current visit before not-yet-arrived placement")
    current_visit["arrival_time"] = None
    current_visit["arrival_tiebreaker"] = None


def _real_world_snapshot(W):
    return {
        "T": W.T,
        "TIME": W.TIME,
        "collector": W._order_control_baseline_collector,
    }


def _assert_real_world_unchanged(W, before):
    assert _real_world_snapshot(W) == before


def _junction_target_nodes():
    return ["junction"]


def _two_node_target_names():
    return ["junction_a", "junction_b"]


def _rank_states_for_nodes(node_names):
    return {node_name: OrderControlTvtNodeRankState(node_name) for node_name in node_names}


def _build_arrived_junction_world():
    W = _build_time_value_junction_world()
    snapshot_T = 25
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    return W, vehicle


def _build_two_node_snapshot_world_with_visits_on_both_nodes():
    W = _build_two_time_value_nodes_world()
    snapshot_T = 25
    W.T = snapshot_T
    vehicle_b = W.addVehicle("orig_a", "dest", 0, name="veh_b")
    _advance_until_on_inlink(vehicle_b, "in_b")
    vehicle_a = W.addVehicle("orig_a", "dest", 0, name="veh_a")
    _advance_until_on_inlink(vehicle_a, "in_a")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W,
        vehicle_b,
        inlink_name="in_b",
        snapshot_timestep=snapshot_T,
    )
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle_a,
        inlink_name="in_a",
        target_node_name="junction_a",
        outlink_name="mid_link",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    return W, vehicle_a, vehicle_b


def _zero_visit_two_node_world():
    W = _build_two_time_value_nodes_world()
    W.T = 15
    return W


def _single_node_run_kwargs(rank_states):
    return {
        "target_node_names": _junction_target_nodes(),
        "baseline_horizon_steps": 3,
        "rank_states_by_node_name": rank_states,
    }


def _two_node_run_kwargs(rank_states):
    return {
        "target_node_names": _two_node_target_names(),
        "baseline_horizon_steps": 3,
        "rank_states_by_node_name": rank_states,
    }


def _expect_value_error(test_callable, expected_substring: str) -> None:
    try:
        test_callable()
    except ValueError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected ValueError")


def _expect_runtime_error(test_callable, expected_substring: str) -> None:
    try:
        test_callable()
    except RuntimeError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected RuntimeError")


# --- tests ---


def test_returns_baseline_fork_alignment_result_with_two_fields():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        W,
        **_single_node_run_kwargs({"junction": rank_state}),
    )
    assert isinstance(result, OrderControlTvtBaselineForkAlignmentResult)
    assert isinstance(result.fork_result, OrderControlBaselineForkResult)
    assert len(result.alignment_results) == 1
    assert result.alignment_results[0].node_name == "junction"
    assert rank_state.is_undetermined(visit_key)
    assert result.alignment_results[0].unregistered_collector_visit_keys == ()


def test_calls_baseline_driver_once():
    W, _vehicle = _build_arrived_junction_world()
    driver_count = 0
    original_driver = (
        __import__(
            "uxsim.order_control_baseline_driver",
            fromlist=["run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration"],
        ).run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration
    )

    def counting_driver(*args, **kwargs):
        nonlocal driver_count
        driver_count += 1
        return original_driver(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
        side_effect=counting_driver,
    ):
        run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
        )
    assert driver_count == 1


def test_skips_alignment_when_baseline_driver_fails():
    W, _vehicle = _build_arrived_junction_world()
    align_count = 0
    original_align = align_snapshot_undetermined_visits_with_node_baseline

    def counting_align(*args, **kwargs):
        nonlocal align_count
        align_count += 1
        return original_align(*args, **kwargs)

    def fail_driver(*args, **kwargs):
        raise ValueError("baseline driver failed")

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
        side_effect=fail_driver,
    ), patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=counting_align,
    ):
        _expect_value_error(
            lambda: run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
            ),
            "baseline driver failed",
        )
    assert align_count == 0


def test_calls_alignment_once_for_single_node():
    W, _vehicle = _build_arrived_junction_world()
    align_count = 0
    original_align = align_snapshot_undetermined_visits_with_node_baseline

    def counting_align(*args, **kwargs):
        nonlocal align_count
        align_count += 1
        return original_align(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=counting_align,
    ):
        run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
        )
    assert align_count == 1


def test_calls_alignment_once_per_node_in_target_node_order():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    events: list[str] = []
    original_align = align_snapshot_undetermined_visits_with_node_baseline

    def tracking_align(*args, **kwargs):
        events.append(kwargs["node_name"])
        return original_align(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=tracking_align,
    ):
        result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_two_node_run_kwargs(_rank_states_for_nodes(_two_node_target_names())),
        )
    assert events == ["junction_a", "junction_b"]
    assert [item.node_name for item in result.alignment_results] == [
        "junction_a",
        "junction_b",
    ]
    assert result.alignment_results[0].node_name == result.fork_result.target_node_names[0]
    assert result.alignment_results[1].node_name == result.fork_result.target_node_names[1]


def test_calls_collector_export_once_per_node():
    W, _vehicle = _build_arrived_junction_world()
    export_events: list[str] = []
    original_driver = (
        __import__(
            "uxsim.order_control_baseline_driver",
            fromlist=["run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration"],
        ).run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration
    )

    def driver_with_counting_export(*args, **kwargs):
        fork_result = original_driver(*args, **kwargs)
        collector = fork_result.collector
        original_export = collector.export_node_baseline_visits

        def counting_export(node_name):
            export_events.append(node_name)
            return original_export(node_name)

        collector.export_node_baseline_visits = counting_export
        return fork_result

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
        side_effect=driver_with_counting_export,
    ):
        run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
        )
    assert export_events == ["junction"]


def test_calls_collector_export_once_per_node_for_multiple_nodes():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    export_events: list[str] = []
    original_driver = (
        __import__(
            "uxsim.order_control_baseline_driver",
            fromlist=["run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration"],
        ).run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration
    )

    def driver_with_counting_export(*args, **kwargs):
        fork_result = original_driver(*args, **kwargs)
        collector = fork_result.collector
        original_export = collector.export_node_baseline_visits

        def counting_export(node_name):
            export_events.append(node_name)
            return original_export(node_name)

        collector.export_node_baseline_visits = counting_export
        return fork_result

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration",
        side_effect=driver_with_counting_export,
    ):
        run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_two_node_run_kwargs(_rank_states_for_nodes(_two_node_target_names())),
        )
    assert export_events == ["junction_a", "junction_b"]


def test_passes_same_rank_state_objects_to_alignment():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    seen_states: list[OrderControlTvtNodeRankState] = []
    original_align = align_snapshot_undetermined_visits_with_node_baseline

    def capture_state(*args, **kwargs):
        seen_states.append(kwargs["node_rank_state"])
        return original_align(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=capture_state,
    ):
        run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_single_node_run_kwargs({"junction": rank_state}),
        )
    assert seen_states == [rank_state]
    assert rank_state.is_undetermined((vehicle.name, vehicle.order_control_visit_id))


def test_does_not_replace_rank_states_mapping():
    W, _vehicle = _build_arrived_junction_world()
    rank_states = _rank_states_for_nodes(["junction"])
    before_keys = set(rank_states.keys())
    before_values = {node_name: rank_states[node_name] for node_name in rank_states}
    run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        W,
        **_single_node_run_kwargs(rank_states),
    )
    assert set(rank_states.keys()) == before_keys
    assert {
        node_name: rank_states[node_name] for node_name in rank_states
    } == before_values


def test_succeeds_when_unregistered_collector_visit_keys_empty():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        W,
        **_single_node_run_kwargs({"junction": rank_state}),
    )
    alignment = result.alignment_results[0]
    assert alignment.unregistered_collector_visit_keys == ()
    assert not alignment.has_unregistered_collector_visits
    assert rank_state.is_undetermined(visit_key)


def test_raises_runtime_error_when_unregistered_collector_visit_keys_nonempty():
    W, vehicle_a, vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(_two_node_target_names())
    visit_key_b = (vehicle_b.name, vehicle_b.order_control_visit_id)
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def skip_registration_on_junction_b(self, visit_keys):
        if self.node_name == "junction_b":
            return None
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        skip_registration_on_junction_b,
    ):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(rank_states),
            ),
            "junction_b",
        )
    assert rank_states["junction_a"].is_undetermined(
        (vehicle_a.name, vehicle_a.order_control_visit_id)
    )
    assert not rank_states["junction_b"].is_undetermined(visit_key_b)


def test_runtime_error_includes_node_name_and_unregistered_visit_keys():
    W, _vehicle_a, vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(_two_node_target_names())
    visit_key_b = (vehicle_b.name, vehicle_b.order_control_visit_id)
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def skip_registration_on_junction_b(self, visit_keys):
        if self.node_name == "junction_b":
            return None
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        skip_registration_on_junction_b,
    ):
        try:
            run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(rank_states),
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "junction_b" in message
            assert repr(visit_key_b) in message or str(visit_key_b) in message
            return
        raise AssertionError("Expected RuntimeError")


def test_stops_after_unregistered_node_without_processing_later_nodes():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(_two_node_target_names())
    align_events: list[str] = []
    original_align = align_snapshot_undetermined_visits_with_node_baseline
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def skip_registration_on_junction_a(self, visit_keys):
        if self.node_name == "junction_a":
            return None
        return original_register(self, visit_keys)

    def tracking_align(*args, **kwargs):
        align_events.append(kwargs["node_name"])
        return original_align(*args, **kwargs)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        skip_registration_on_junction_a,
    ), patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=tracking_align,
    ):
        try:
            run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(rank_states),
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected RuntimeError")
    assert align_events == ["junction_a"]
    assert "junction_b" not in align_events


def test_does_not_return_partial_result_on_unregistered_nonempty():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(_two_node_target_names())
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def skip_registration_on_junction_a(self, visit_keys):
        if self.node_name == "junction_a":
            return None
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        skip_registration_on_junction_a,
    ):
        try:
            result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(rank_states),
            )
        except RuntimeError:
            return
        else:
            raise AssertionError(
                f"Expected RuntimeError, got result {result!r}"
            )


def test_propagates_alignment_exception_without_processing_later_nodes():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    align_events: list[str] = []
    original_align = align_snapshot_undetermined_visits_with_node_baseline

    def fail_on_junction_a(*args, **kwargs):
        align_events.append(kwargs["node_name"])
        if kwargs["node_name"] == "junction_a":
            raise ValueError("alignment failed on junction_a")
        return original_align(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=fail_on_junction_a,
    ):
        _expect_value_error(
            lambda: run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(_rank_states_for_nodes(_two_node_target_names())),
            ),
            "alignment failed on junction_a",
        )
    assert align_events == ["junction_a"]


def test_zero_visits_calls_alignment_once_per_node():
    W = _zero_visit_two_node_world()
    align_events: list[str] = []
    original_align = align_snapshot_undetermined_visits_with_node_baseline

    def tracking_align(*args, **kwargs):
        align_events.append(kwargs["node_name"])
        return original_align(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=tracking_align,
    ):
        result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            target_node_names=_two_node_target_names(),
            baseline_horizon_steps=5,
            rank_states_by_node_name=_rank_states_for_nodes(_two_node_target_names()),
        )
    assert align_events == ["junction_a", "junction_b"]
    assert result.fork_result.registered_visit_count == 0
    assert result.fork_result.fork_steps_executed == 0


def test_zero_visits_returns_empty_alignment_results_in_target_node_order():
    W = _zero_visit_two_node_world()
    result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        W,
        target_node_names=_two_node_target_names(),
        baseline_horizon_steps=5,
        rank_states_by_node_name=_rank_states_for_nodes(_two_node_target_names()),
    )
    assert [item.node_name for item in result.alignment_results] == [
        "junction_a",
        "junction_b",
    ]
    for alignment in result.alignment_results:
        assert alignment.resolved_undetermined_visits == ()
        assert alignment.unresolved_undetermined_visits == ()
        assert alignment.unregistered_collector_visit_keys == ()


def test_leaves_real_world_unchanged_on_success():
    W, _vehicle = _build_arrived_junction_world()
    before = _real_world_snapshot(W)
    run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        W,
        **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
    )
    _assert_real_world_unchanged(W, before)


def test_leaves_real_world_unchanged_on_alignment_failure():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    before = _real_world_snapshot(W)

    def fail_on_junction_a(*args, **kwargs):
        if kwargs["node_name"] == "junction_a":
            raise ValueError("alignment failed")
        return align_snapshot_undetermined_visits_with_node_baseline(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=fail_on_junction_a,
    ):
        try:
            run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(_rank_states_for_nodes(_two_node_target_names())),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    _assert_real_world_unchanged(W, before)


def test_leaves_real_world_unchanged_on_unregistered_nonempty():
    W, _vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    before = _real_world_snapshot(W)
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def skip_registration_on_junction_b(self, visit_keys):
        if self.node_name == "junction_b":
            return None
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        skip_registration_on_junction_b,
    ):
        try:
            run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(_rank_states_for_nodes(_two_node_target_names())),
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)


def test_preserves_undetermined_registrations_after_alignment_failure():
    W, vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(_two_node_target_names())
    visit_key_a = (vehicle_a.name, vehicle_a.order_control_visit_id)

    def fail_on_junction_b(*args, **kwargs):
        if kwargs["node_name"] == "junction_b":
            raise ValueError("alignment failed on junction_b")
        return align_snapshot_undetermined_visits_with_node_baseline(*args, **kwargs)

    with patch(
        "uxsim.order_control_tvt_baseline_fork_alignment."
        "align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=fail_on_junction_b,
    ):
        try:
            run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(rank_states),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    assert rank_states["junction_a"].is_undetermined(visit_key_a)


def test_preserves_undetermined_registrations_after_unregistered_nonempty():
    W, vehicle_a, _vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(_two_node_target_names())
    visit_key_a = (vehicle_a.name, vehicle_a.order_control_visit_id)
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def skip_registration_on_junction_b(self, visit_keys):
        if self.node_name == "junction_b":
            return None
        return original_register(self, visit_keys)

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        skip_registration_on_junction_b,
    ):
        try:
            run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
                W,
                **_two_node_run_kwargs(rank_states),
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected RuntimeError")
    assert rank_states["junction_a"].is_undetermined(visit_key_a)


def test_does_not_call_confirm_visits_in_order():
    W, _vehicle = _build_arrived_junction_world()
    confirm_called = False
    original_confirm = OrderControlTvtNodeRankState.confirm_visits_in_order

    def fail_confirm(self, visit_keys_in_order):
        nonlocal confirm_called
        confirm_called = True
        return original_confirm(self, visit_keys_in_order)

    with patch.object(
        OrderControlTvtNodeRankState,
        "confirm_visits_in_order",
        fail_confirm,
    ):
        run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
            W,
            **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
        )
    assert confirm_called is False


def test_does_not_modify_existing_result_types():
    W, _vehicle = _build_arrived_junction_world()
    result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        W,
        **_single_node_run_kwargs(_rank_states_for_nodes(["junction"])),
    )
    fork_field_names = {field.name for field in dataclasses.fields(result.fork_result)}
    assert fork_field_names == {
        "collector",
        "target_node_names",
        "baseline_timestep_T",
        "configured_horizon_steps",
        "fork_steps_executed",
        "final_fork_timestep",
        "registered_visit_count",
    }
    alignment_field_names = {
        field.name for field in dataclasses.fields(result.alignment_results[0])
    }
    assert alignment_field_names == {
        "node_name",
        "resolved_undetermined_visits",
        "unresolved_undetermined_visits",
        "unregistered_collector_visit_keys",
    }
    assert dataclasses.is_dataclass(OrderControlTvtBaselineForkAlignmentResult)
    assert OrderControlTvtBaselineForkAlignmentResult.__dataclass_params__.frozen


TESTS = [
    test_returns_baseline_fork_alignment_result_with_two_fields,
    test_calls_baseline_driver_once,
    test_skips_alignment_when_baseline_driver_fails,
    test_calls_alignment_once_for_single_node,
    test_calls_alignment_once_per_node_in_target_node_order,
    test_calls_collector_export_once_per_node,
    test_calls_collector_export_once_per_node_for_multiple_nodes,
    test_passes_same_rank_state_objects_to_alignment,
    test_does_not_replace_rank_states_mapping,
    test_succeeds_when_unregistered_collector_visit_keys_empty,
    test_raises_runtime_error_when_unregistered_collector_visit_keys_nonempty,
    test_runtime_error_includes_node_name_and_unregistered_visit_keys,
    test_stops_after_unregistered_node_without_processing_later_nodes,
    test_does_not_return_partial_result_on_unregistered_nonempty,
    test_propagates_alignment_exception_without_processing_later_nodes,
    test_zero_visits_calls_alignment_once_per_node,
    test_zero_visits_returns_empty_alignment_results_in_target_node_order,
    test_leaves_real_world_unchanged_on_success,
    test_leaves_real_world_unchanged_on_alignment_failure,
    test_leaves_real_world_unchanged_on_unregistered_nonempty,
    test_preserves_undetermined_registrations_after_alignment_failure,
    test_preserves_undetermined_registrations_after_unregistered_nonempty,
    test_does_not_call_confirm_visits_in_order,
    test_does_not_modify_existing_result_types,
]


if __name__ == "__main__":
    duplicate_names = sorted(
        name
        for name in {test.__name__ for test in TESTS}
        if sum(1 for test in TESTS if test.__name__ == name) > 1
    )
    if duplicate_names:
        raise SystemExit(f"Duplicate test names: {duplicate_names}")
    if len(TESTS) != len({test.__name__ for test in TESTS}):
        raise SystemExit("TESTS list length does not match unique test function count")
    for test_func in TESTS:
        test_func()
    print(
        "Order-control TVT baseline fork alignment tests passed "
        f"({len(TESTS)} tests)."
    )
