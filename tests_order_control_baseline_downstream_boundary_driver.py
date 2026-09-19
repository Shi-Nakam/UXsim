# Integration tests connecting the downstream boundary observer to the
# all-World baseline driver.
#
# Run from the repository root:
#   python tests_order_control_baseline_downstream_boundary_driver.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import patch

from uxsim import World
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryObserver,
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
    OrderControlBaselineDownstreamBoundaryResult,
)
from uxsim.order_control_baseline_driver import (
    OrderControlBaselineForkResult,
    run_snapshot_fixed_baseline_fork,
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import World as UxsimWorld


_REAL_EXEC_SIMULATION = UxsimWorld.__dict__["exec_simulation"]


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_world(name, *, tmax=300):
    return World(
        name=name,
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )


def _build_junction_world(*, name="driver_boundary_junction", tmax=300):
    W = _build_world(name, tmax=tmax)
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


def _build_through_world(
    *,
    name="driver_boundary_through",
    tmax=300,
    last_capacity_in=None,
):
    W = _build_world(name, tmax=tmax)
    W.addNode("orig", 0, 0)
    W.addNode(
        "junction",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("mid", 2, 0)
    W.addNode("dest", 3, 0)
    W.addLink("in", "orig", "junction", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink(
        "through",
        "junction",
        "mid",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    W.addLink(
        "last",
        "mid",
        "dest",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
        capacity_in=last_capacity_in,
    )
    _prepare_network(W)
    return W


def _build_shared_terminal_world(*, name="driver_boundary_shared", tmax=300):
    W = _build_world(name, tmax=tmax)
    W.addNode("orig_a", 0, 1)
    W.addNode("orig_a2", 0, 2)
    W.addNode(
        "node_a",
        1,
        1,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("orig_d", 0, -1)
    W.addNode("orig_d2", 0, -2)
    W.addNode(
        "node_d",
        1,
        -1,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    W.addNode("shared_b", 2, 0)
    W.addNode("dest", 3, 0)
    W.addLink("in_a1", "orig_a", "node_a", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("in_a2", "orig_a2", "node_a", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out_ab", "node_a", "shared_b", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("in_d1", "orig_d", "node_d", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("in_d2", "orig_d2", "node_d", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out_db", "node_d", "shared_b", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("last", "shared_b", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
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


def _place_arrived_at_junction(
    W,
    *,
    vehicle_name,
    snapshot_timestep=20,
    dest_name="dest",
):
    W.T = snapshot_timestep
    vehicle = W.addVehicle("orig", dest_name, 0, name=vehicle_name)
    _advance_until_on_inlink(vehicle, "in")
    junction = W.get_node("junction")
    outlink_name = next(iter(junction.outlinks))
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name=outlink_name,
        arrival_timestep=10,
        snapshot_timestep=snapshot_timestep,
    )
    return vehicle


def _place_waiting_through_vehicle_at_mid(
    W,
    *,
    vehicle_name,
    snapshot_timestep=20,
):
    through = W.get_link("through")
    last = W.get_link("last")
    mid = W.get_node("mid")
    vehicle = W.addVehicle("orig", "dest", 0, name=vehicle_name)
    vehicle.link = through
    vehicle.state = "run"
    vehicle.x = through.length
    vehicle.route_next_link = last
    vehicle.link_arrival_time = float((snapshot_timestep - 1) * W.DELTAT)
    if vehicle not in through.vehicles:
        through.vehicles.append(vehicle)
    if vehicle not in mid.incoming_vehicles:
        mid.incoming_vehicles.append(vehicle)
    W.T = snapshot_timestep
    return vehicle


def _place_arrived_at_named_node(
    W,
    *,
    vehicle_name,
    orig_name,
    inlink_name,
    target_node_name,
    outlink_name,
    snapshot_timestep=20,
):
    W.T = snapshot_timestep
    vehicle = W.addVehicle(orig_name, "dest", 0, name=vehicle_name)
    _advance_until_on_inlink(vehicle, inlink_name)
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name=inlink_name,
        target_node_name=target_node_name,
        outlink_name=outlink_name,
        arrival_timestep=10,
        snapshot_timestep=snapshot_timestep,
    )
    return vehicle


def _real_world_snapshot(W):
    return {
        "T": W.T,
        "TIME": W.TIME,
        "collector": W._order_control_baseline_collector,
        "downstream_boundary_observer": (
            W._order_control_baseline_downstream_boundary_observer
        ),
    }


def _assert_real_world_unchanged(W, before):
    after = _real_world_snapshot(W)
    assert after == before


def _rank_states_for_nodes(node_names):
    return {
        node_name: OrderControlTvtNodeRankState(node_name)
        for node_name in node_names
    }


def _capturing_copy_patch():
    captured_forks = []
    original_copy = UxsimWorld.copy

    def capturing_copy(self):
        fork_W = original_copy(self)
        captured_forks.append(fork_W)
        return fork_W

    return patch.object(UxsimWorld, "copy", capturing_copy), captured_forks


def _assert_three_level_frozen_boundary(boundary):
    assert isinstance(boundary, OrderControlBaselineDownstreamBoundaryResult)
    assert boundary.__dataclass_params__.frozen is True
    try:
        boundary.node_results = ()
        raise AssertionError("expected FrozenInstanceError on overall result")
    except FrozenInstanceError:
        pass
    for node_result in boundary.node_results:
        assert isinstance(
            node_result,
            OrderControlBaselineDownstreamBoundaryNodeResult,
        )
        assert node_result.__dataclass_params__.frozen is True
        for outlink_result in node_result.outlink_results:
            assert isinstance(
                outlink_result,
                OrderControlBaselineDownstreamBoundaryOutlinkResult,
            )
            assert outlink_result.__dataclass_params__.frozen is True
            assert type(outlink_result.active_timestep_count) is int
            assert type(outlink_result.transferred_vehicle_count) is int
            assert outlink_result.active_timestep_count >= 0
            assert outlink_result.transferred_vehicle_count >= 0


def _outlink_counts(boundary, node_name, outlink_name):
    for node_result in boundary.node_results:
        if node_result.node_name != node_name:
            continue
        for outlink_result in node_result.outlink_results:
            if outlink_result.outlink_name == outlink_name:
                return outlink_result
    raise AssertionError(
        f"Missing outlink {outlink_name!r} under node {node_name!r}"
    )


# --- empty baseline ---


def test_empty_baseline_returns_none_boundary_without_observer_or_forward():
    W = _build_junction_world()
    W.T = 15
    before = _real_world_snapshot(W)
    copy_patch, captured_forks = _capturing_copy_patch()
    with copy_patch:
        with patch(
            "uxsim.order_control_baseline_driver."
            "OrderControlBaselineDownstreamBoundaryObserver"
        ) as mock_observer_cls:
            with patch.object(UxsimWorld, "exec_simulation") as mock_exec:
                result = run_snapshot_fixed_baseline_fork(
                    W,
                    target_node_names=["junction"],
                    baseline_horizon_steps=10,
                )
    mock_observer_cls.assert_not_called()
    mock_exec.assert_not_called()
    assert result.registered_visit_count == 0
    assert result.fork_steps_executed == 0
    assert result.downstream_boundary_result is None
    assert result.collector.export_node_baseline_visits("junction") == []
    assert W._order_control_baseline_downstream_boundary_observer is None
    assert len(captured_forks) == 1
    assert captured_forks[0]._order_control_baseline_downstream_boundary_observer is None
    _assert_real_world_unchanged(W, before)


# --- non-empty completed baseline ---


def test_nonempty_baseline_connects_observer_to_fork_only_and_returns_frozen_result():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(W, vehicle_name="through_vehicle", snapshot_timestep=snapshot_T)
    before = _real_world_snapshot(W)
    copy_patch, captured_forks = _capturing_copy_patch()
    horizon = 8
    with copy_patch:
        result = run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=["junction"],
            baseline_horizon_steps=horizon,
        )
    assert result.registered_visit_count == 1
    assert result.fork_steps_executed == horizon
    assert result.downstream_boundary_result is not None
    _assert_three_level_frozen_boundary(result.downstream_boundary_result)
    node_results = result.downstream_boundary_result.node_results
    assert [node_result.node_name for node_result in node_results] == ["junction"]
    outlink_results = node_results[0].outlink_results
    assert [outlink_result.outlink_name for outlink_result in outlink_results] == [
        "through"
    ]
    assert outlink_results[0].terminal_node_name == "mid"
    assert not hasattr(result, "fork_W")
    assert not hasattr(result.downstream_boundary_result, "configured_horizon_steps")
    assert not hasattr(result.downstream_boundary_result, "horizon")
    assert W._order_control_baseline_downstream_boundary_observer is None
    assert len(captured_forks) == 1
    fork_observer = captured_forks[0]._order_control_baseline_downstream_boundary_observer
    assert isinstance(fork_observer, OrderControlBaselineDownstreamBoundaryObserver)
    assert result.downstream_boundary_result is not fork_observer
    _assert_real_world_unchanged(W, before)


# --- observed counts ---


def test_active_and_transfer_counts_when_passing_vehicle_leaves_outlink():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="registered_junction_vehicle",
        snapshot_timestep=snapshot_T,
        dest_name="mid",
    )
    _place_waiting_through_vehicle_at_mid(
        W,
        vehicle_name="passing_vehicle",
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=5,
    )
    boundary = result.downstream_boundary_result
    assert boundary is not None
    through_result = _outlink_counts(boundary, "junction", "through")
    assert through_result.active_timestep_count >= 1
    assert through_result.transferred_vehicle_count >= 1


def test_active_without_transfer_when_downstream_inflow_is_closed():
    W = _build_through_world(last_capacity_in=0)
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="registered_junction_vehicle",
        snapshot_timestep=snapshot_T,
        dest_name="mid",
    )
    _place_waiting_through_vehicle_at_mid(
        W,
        vehicle_name="blocked_vehicle",
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=5,
    )
    boundary = result.downstream_boundary_result
    assert boundary is not None
    through_result = _outlink_counts(boundary, "junction", "through")
    assert through_result.active_timestep_count >= 1
    assert through_result.transferred_vehicle_count == 0


def test_completed_baseline_with_zero_counts_is_not_none():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="short_horizon_vehicle",
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=1,
    )
    assert result.fork_steps_executed == 1
    boundary = result.downstream_boundary_result
    assert boundary is not None
    through_result = _outlink_counts(boundary, "junction", "through")
    assert through_result.active_timestep_count == 0
    assert through_result.transferred_vehicle_count == 0


def test_destination_arrival_is_excluded_from_active_and_transfer():
    W = _build_junction_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="trip_end_vehicle",
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=40,
    )
    boundary = result.downstream_boundary_result
    assert boundary is not None
    out_result = _outlink_counts(boundary, "junction", "out")
    assert out_result.terminal_node_name == "dest"
    assert out_result.active_timestep_count == 0
    assert out_result.transferred_vehicle_count == 0


# --- shared terminal ---


def test_shared_terminal_keeps_separate_origin_node_results():
    W = _build_shared_terminal_world()
    snapshot_T = 20
    _place_arrived_at_named_node(
        W,
        vehicle_name="node_a_vehicle",
        orig_name="orig_a",
        inlink_name="in_a1",
        target_node_name="node_a",
        outlink_name="out_ab",
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["node_a", "node_d"],
        baseline_horizon_steps=5,
    )
    boundary = result.downstream_boundary_result
    assert boundary is not None
    node_names = [node_result.node_name for node_result in boundary.node_results]
    assert node_names == ["node_a", "node_d"]
    node_a = boundary.node_results[0]
    node_d = boundary.node_results[1]
    assert [out.outlink_name for out in node_a.outlink_results] == ["out_ab"]
    assert [out.outlink_name for out in node_d.outlink_results] == ["out_db"]
    assert node_a.outlink_results[0].terminal_node_name == "shared_b"
    assert node_d.outlink_results[0].terminal_node_name == "shared_b"
    assert node_a.outlink_results[0] is not node_d.outlink_results[0]


# --- ordinary path and rank-ledger path ---


def test_ordinary_and_rank_ledger_paths_return_the_same_boundary_result():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="same_state_vehicle",
        snapshot_timestep=snapshot_T,
    )
    target_node_names = ["junction"]
    horizon = 8
    ordinary = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=target_node_names,
        baseline_horizon_steps=horizon,
    )
    rank_ledger = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=target_node_names,
        baseline_horizon_steps=horizon,
        rank_states_by_node_name=_rank_states_for_nodes(target_node_names),
    )
    assert ordinary.downstream_boundary_result is not None
    assert rank_ledger.downstream_boundary_result is not None
    assert ordinary.downstream_boundary_result == rank_ledger.downstream_boundary_result


# --- real_W unchanged ---


def test_real_world_observer_and_time_remain_none_and_unchanged():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="unchanged_real_world_vehicle",
        snapshot_timestep=snapshot_T,
    )
    before = _real_world_snapshot(W)
    assert before["downstream_boundary_observer"] is None
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=5,
    )
    assert result.downstream_boundary_result is not None
    _assert_real_world_unchanged(W, before)


def test_runtime_error_when_real_world_observer_changes_before_success_return():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="mutated_observer_vehicle",
        snapshot_timestep=snapshot_T,
    )
    mutated_observer = object()

    def exec_mutating_real_world_observer_only(fork_W, **kwargs):
        W._order_control_baseline_downstream_boundary_observer = mutated_observer
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    try:
        with patch.object(
            UxsimWorld,
            "exec_simulation",
            exec_mutating_real_world_observer_only,
        ):
            try:
                run_snapshot_fixed_baseline_fork(
                    W,
                    target_node_names=["junction"],
                    baseline_horizon_steps=3,
                )
            except RuntimeError as exc:
                message = str(exc)
                assert (
                    "real_W._order_control_baseline_downstream_boundary_observer changed"
                    in message
                )
                assert "before=None" in message
                assert f"after={mutated_observer!r}" in message
            else:
                raise AssertionError("Expected RuntimeError")
    finally:
        W._order_control_baseline_downstream_boundary_observer = None


def test_rejects_real_world_with_observer_configured():
    W = _build_junction_world()
    W.T = 10
    existing_observer = object()
    W._order_control_baseline_downstream_boundary_observer = existing_observer
    try:
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=["junction"],
            baseline_horizon_steps=1,
        )
    except ValueError as exc:
        message = str(exc)
        assert "real_W._order_control_baseline_downstream_boundary_observer" in message
        assert "must be None before baseline fork" in message
        assert repr(existing_observer) in message
    else:
        raise AssertionError("Expected ValueError")


# --- copy-time inconsistency ---


def test_runtime_error_when_fork_observer_non_none_after_copy():
    W = _build_junction_world()
    W.T = 10
    bad_fork = W.copy()
    leftover_observer = object()
    bad_fork._order_control_baseline_downstream_boundary_observer = leftover_observer
    try:
        with patch.object(UxsimWorld, "copy", return_value=bad_fork):
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=["junction"],
                baseline_horizon_steps=1,
            )
    except RuntimeError as exc:
        message = str(exc)
        assert "fork_W._order_control_baseline_downstream_boundary_observer" in message
        assert "must be None immediately after copy" in message
        assert repr(leftover_observer) in message
    else:
        raise AssertionError("Expected RuntimeError")


# --- registration failure ---


def test_registration_failure_does_not_start_forward_or_connect_observer():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="register_fail_vehicle",
        snapshot_timestep=snapshot_T,
    )
    before = _real_world_snapshot(W)
    copy_patch, captured_forks = _capturing_copy_patch()
    with copy_patch:
        with patch.object(
            OrderControlBaselineDownstreamBoundaryObserver,
            "register_target_node_outlinks",
            side_effect=ValueError("register failed"),
        ):
            with patch.object(UxsimWorld, "exec_simulation") as mock_exec:
                try:
                    run_snapshot_fixed_baseline_fork(
                        W,
                        target_node_names=["junction"],
                        baseline_horizon_steps=5,
                    )
                except ValueError as exc:
                    assert "register failed" in str(exc)
                else:
                    raise AssertionError("Expected ValueError")
                mock_exec.assert_not_called()
    assert len(captured_forks) == 1
    assert captured_forks[0]._order_control_baseline_downstream_boundary_observer is None
    assert W._order_control_baseline_downstream_boundary_observer is None
    _assert_real_world_unchanged(W, before)


# --- forward failure ---


def test_forward_exception_does_not_return_fork_result_or_export():
    W = _build_through_world()
    snapshot_T = 20
    _place_arrived_at_junction(
        W,
        vehicle_name="exec_fail_vehicle",
        snapshot_timestep=snapshot_T,
    )
    before = _real_world_snapshot(W)
    exec_calls = []

    def failing_exec(fork_W, **kwargs):
        exec_calls.append(1)
        raise RuntimeError("exec failed")

    with patch.object(
        OrderControlBaselineDownstreamBoundaryObserver,
        "export_result",
    ) as mock_export:
        with patch.object(UxsimWorld, "exec_simulation", failing_exec):
            try:
                run_snapshot_fixed_baseline_fork(
                    W,
                    target_node_names=["junction"],
                    baseline_horizon_steps=5,
                )
            except RuntimeError as exc:
                assert "exec failed" in str(exc)
                assert type(exc) is RuntimeError
            else:
                raise AssertionError("Expected RuntimeError")
        mock_export.assert_not_called()
    assert exec_calls == [1]
    _assert_real_world_unchanged(W, before)


# --- ForkResult required field ---


def test_completed_and_empty_fork_result_field_contract():
    empty_world = _build_junction_world()
    empty_world.T = 12
    empty_result = run_snapshot_fixed_baseline_fork(
        empty_world,
        target_node_names=["junction"],
        baseline_horizon_steps=4,
    )
    assert empty_result.downstream_boundary_result is None

    completed_world = _build_through_world()
    _place_arrived_at_junction(
        completed_world,
        vehicle_name="field_contract_vehicle",
        snapshot_timestep=20,
    )
    completed = run_snapshot_fixed_baseline_fork(
        completed_world,
        target_node_names=["junction"],
        baseline_horizon_steps=4,
    )
    assert isinstance(
        completed.downstream_boundary_result,
        OrderControlBaselineDownstreamBoundaryResult,
    )
    assert not isinstance(
        completed.downstream_boundary_result,
        OrderControlBaselineDownstreamBoundaryObserver,
    )
    assert not hasattr(completed, "fork_W")

    try:
        OrderControlBaselineForkResult(
            collector=OrderControlBaselineCollector(),
            target_node_names=("junction",),
            baseline_timestep_T=10,
            configured_horizon_steps=3,
            fork_steps_executed=3,
            final_fork_timestep=13,
            registered_visit_count=1,
            inlink_physical_orders=(),
        )
    except TypeError:
        pass
    else:
        raise AssertionError(
            "Expected TypeError when downstream_boundary_result is omitted"
        )


TESTS = [
    test_empty_baseline_returns_none_boundary_without_observer_or_forward,
    test_nonempty_baseline_connects_observer_to_fork_only_and_returns_frozen_result,
    test_active_and_transfer_counts_when_passing_vehicle_leaves_outlink,
    test_active_without_transfer_when_downstream_inflow_is_closed,
    test_completed_baseline_with_zero_counts_is_not_none,
    test_destination_arrival_is_excluded_from_active_and_transfer,
    test_shared_terminal_keeps_separate_origin_node_results,
    test_ordinary_and_rank_ledger_paths_return_the_same_boundary_result,
    test_real_world_observer_and_time_remain_none_and_unchanged,
    test_runtime_error_when_real_world_observer_changes_before_success_return,
    test_rejects_real_world_with_observer_configured,
    test_runtime_error_when_fork_observer_non_none_after_copy,
    test_registration_failure_does_not_start_forward_or_connect_observer,
    test_forward_exception_does_not_return_fork_result_or_export,
    test_completed_and_empty_fork_result_field_contract,
]


if __name__ == "__main__":
    duplicate_names = [
        name
        for name in {test.__name__ for test in TESTS}
        if sum(1 for test in TESTS if test.__name__ == name) > 1
    ]
    if duplicate_names:
        raise SystemExit(f"Duplicate test names: {duplicate_names}")
    if len(TESTS) != len({test.__name__ for test in TESTS}):
        raise SystemExit("TESTS list length does not match unique test function count")
    for test_func in TESTS:
        test_func()
    print(
        "Order-control baseline downstream-boundary driver tests passed "
        f"({len(TESTS)} tests)."
    )
