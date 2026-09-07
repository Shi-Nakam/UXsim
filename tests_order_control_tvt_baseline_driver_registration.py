# Unit tests for TVT rank-ledger registration baseline driver path
# (design memo §25.25.34.34).
#
# Run from the repository root:
#   python tests_order_control_tvt_baseline_driver_registration.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import patch

from uxsim import World
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import (
    OrderControlBaselineForkResult,
    run_snapshot_fixed_baseline_fork,
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration,
)
from uxsim.order_control_baseline_snapshot import (
    apply_snapshot_fixed_visit_registration_plan,
    prepare_snapshot_fixed_visit_registration_plan,
    register_snapshot_fixed_visits,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.order_control_tvt_snapshot_undetermined_registration import (
    register_undetermined_visits_from_snapshot_plan,
)
from uxsim.uxsim import World as UxsimWorld


# --- shared helpers ---


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_time_value_junction_world(
    *,
    name="tvt_driver_time_value_junction",
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
    name="tvt_driver_two_time_value_nodes",
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


def _zero_visit_two_node_world():
    W = _build_two_time_value_nodes_world()
    W.T = 15
    return W


def _zero_visit_run_kwargs():
    return {
        "target_node_names": _two_node_target_names(),
        "baseline_horizon_steps": 5,
        "rank_states_by_node_name": _rank_states_for_nodes(
            ["junction_a", "junction_b"]
        ),
    }


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


def _collector_visit_keys(collector, node_name):
    return [
        (record["vehicle_name"], record["visit_id"])
        for record in collector.export_node_baseline_visits(node_name)
    ]


_REAL_EXEC_SIMULATION = UxsimWorld.__dict__["exec_simulation"]


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


def test_returns_order_control_baseline_fork_result():
    W, _vehicle = _build_arrived_junction_world()
    result = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
    )
    assert isinstance(result, OrderControlBaselineForkResult)


def test_prepare_called_once():
    W, _vehicle = _build_arrived_junction_world()
    prepare_count = 0
    original_prepare = prepare_snapshot_fixed_visit_registration_plan

    def counting_prepare(*args, **kwargs):
        nonlocal prepare_count
        prepare_count += 1
        return original_prepare(*args, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.prepare_snapshot_fixed_visit_registration_plan",
        side_effect=counting_prepare,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
        )
    assert prepare_count == 1


def test_same_plan_passed_to_helper_and_apply():
    W, _vehicle = _build_arrived_junction_world()
    plan_ids: list[int] = []
    original_prepare = prepare_snapshot_fixed_visit_registration_plan
    original_helper = register_undetermined_visits_from_snapshot_plan
    original_apply = apply_snapshot_fixed_visit_registration_plan

    def tracking_prepare(*args, **kwargs):
        plan = original_prepare(*args, **kwargs)
        plan_ids.append(id(plan))
        return plan

    def tracking_helper(plan, rank_states):
        plan_ids.append(id(plan))
        return original_helper(plan, rank_states)

    def tracking_apply(plan, collector):
        plan_ids.append(id(plan))
        return original_apply(plan, collector)

    with patch(
        "uxsim.order_control_baseline_driver.prepare_snapshot_fixed_visit_registration_plan",
        side_effect=tracking_prepare,
    ), patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=tracking_helper,
    ), patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=tracking_apply,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
        )
    assert len(plan_ids) == 3
    assert plan_ids[0] == plan_ids[1] == plan_ids[2]


def test_does_not_call_register_snapshot_fixed_visits():
    W, _vehicle = _build_arrived_junction_world()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("register_snapshot_fixed_visits must not be called")

    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=fail_if_called,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
        )


def test_call_order_prepare_helper_apply_exec_simulation():
    W, _vehicle = _build_arrived_junction_world()
    events: list[str] = []
    original_prepare = prepare_snapshot_fixed_visit_registration_plan
    original_helper = register_undetermined_visits_from_snapshot_plan
    original_apply = apply_snapshot_fixed_visit_registration_plan

    def tracking_prepare(*args, **kwargs):
        events.append("prepare")
        return original_prepare(*args, **kwargs)

    def tracking_helper(*args, **kwargs):
        events.append("helper")
        return original_helper(*args, **kwargs)

    def tracking_apply(*args, **kwargs):
        events.append("apply")
        return original_apply(*args, **kwargs)

    def tracking_exec(W, **kwargs):
        events.append("exec")
        return _REAL_EXEC_SIMULATION(W, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.prepare_snapshot_fixed_visit_registration_plan",
        side_effect=tracking_prepare,
    ), patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=tracking_helper,
    ), patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=tracking_apply,
    ), patch.object(UxsimWorld, "exec_simulation", tracking_exec):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
        )
    assert events == ["prepare", "helper", "apply", "exec"]


def test_registers_unregistered_visit_before_simulation():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    assert not rank_state.is_undetermined(visit_key)
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name={"junction": rank_state},
    )
    assert rank_state.is_undetermined(visit_key)
    assert not rank_state.is_confirmed(visit_key)


def test_does_not_reregister_already_undetermined_visit():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    rank_state.register_undetermined_visits((visit_key,))
    helper_count = 0
    original_helper = register_undetermined_visits_from_snapshot_plan

    def counting_helper(plan, rank_states):
        nonlocal helper_count
        helper_count += 1
        return original_helper(plan, rank_states)

    with patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=counting_helper,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name={"junction": rank_state},
        )
    assert helper_count == 1
    assert rank_state.is_undetermined(visit_key)
    assert rank_state.undetermined_visit_keys() == frozenset({visit_key})


def test_does_not_reregister_already_confirmed_visit():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    rank_state.register_undetermined_visits((visit_key,))
    rank_state.confirm_visits_in_order((visit_key,))
    assert rank_state.is_confirmed(visit_key)
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name={"junction": rank_state},
    )
    assert rank_state.is_confirmed(visit_key)
    assert not rank_state.is_undetermined(visit_key)


def test_collector_matches_legacy_snapshot_registration():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    tvt_result = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name={"junction": rank_state},
    )
    W_legacy = _build_time_value_junction_world()
    W_legacy.T = W.T
    legacy_vehicle = W_legacy.addVehicle("orig", "dest", 0, name=vehicle.name)
    _advance_until_on_inlink(legacy_vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W_legacy,
        legacy_vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=W.T,
    )
    legacy_result = run_snapshot_fixed_baseline_fork(
        W_legacy,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
    )
    assert _collector_visit_keys(tvt_result.collector, "junction") == _collector_visit_keys(
        legacy_result.collector, "junction"
    )
    assert tvt_result.registered_visit_count == legacy_result.registered_visit_count


def test_helper_value_error_skips_apply_and_exec():
    W, _vehicle = _build_arrived_junction_world()
    apply_called = False
    exec_called = False
    original_apply = apply_snapshot_fixed_visit_registration_plan

    def fail_apply(*args, **kwargs):
        nonlocal apply_called
        apply_called = True
        return original_apply(*args, **kwargs)

    def fail_exec(W, **kwargs):
        nonlocal exec_called
        exec_called = True
        return _REAL_EXEC_SIMULATION(W, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=ValueError("helper failed"),
    ), patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=fail_apply,
    ), patch.object(UxsimWorld, "exec_simulation", fail_exec):
        _expect_value_error(
            lambda: run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
                rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
            ),
            "helper failed",
        )
    assert apply_called is False
    assert exec_called is False


def test_helper_failure_leaves_real_world_unchanged():
    W, _vehicle = _build_arrived_junction_world()
    before = _real_world_snapshot(W)
    with patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=ValueError("helper failed"),
    ):
        try:
            run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
                rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    _assert_real_world_unchanged(W, before)


def test_apply_failure_skips_exec_preserves_real_world_and_undetermined_registrations():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    before = _real_world_snapshot(W)
    exec_called = False

    def fail_exec(W, **kwargs):
        nonlocal exec_called
        exec_called = True
        return _REAL_EXEC_SIMULATION(W, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=ValueError("apply failed"),
    ), patch.object(UxsimWorld, "exec_simulation", fail_exec):
        _expect_value_error(
            lambda: run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
                rank_states_by_node_name={"junction": rank_state},
            ),
            "apply failed",
        )
    assert exec_called is False
    assert rank_state.is_undetermined(visit_key)
    _assert_real_world_unchanged(W, before)


def test_exec_failure_skips_result_preserves_real_world_and_undetermined_registrations():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    before = _real_world_snapshot(W)

    def fail_exec(W, **kwargs):
        raise RuntimeError("exec failed")

    with patch.object(UxsimWorld, "exec_simulation", fail_exec):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
                rank_states_by_node_name={"junction": rank_state},
            ),
            "exec failed",
        )
    assert rank_state.is_undetermined(visit_key)
    _assert_real_world_unchanged(W, before)


def test_post_forward_validation_failure_keeps_undetermined_registrations():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)

    with patch(
        "uxsim.order_control_baseline_driver._validate_completed_fork_forward",
        side_effect=RuntimeError("post-forward validation failed"),
    ):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
                rank_states_by_node_name={"junction": rank_state},
            ),
            "post-forward validation failed",
        )
    assert rank_state.is_undetermined(visit_key)


def test_exceptions_do_not_return_partial_fork_result():
    scenarios = (
        (
            patch(
                "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
                side_effect=ValueError("helper failed"),
            ),
            ValueError,
        ),
        (
            patch(
                "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
                side_effect=ValueError("apply failed"),
            ),
            ValueError,
        ),
        (
            patch.object(
                UxsimWorld,
                "exec_simulation",
                side_effect=RuntimeError("exec failed"),
            ),
            RuntimeError,
        ),
    )
    for side_effect, expected_type in scenarios:
        W, _vehicle = _build_arrived_junction_world()
        with side_effect:
            try:
                result = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                    W,
                    target_node_names=_junction_target_nodes(),
                    baseline_horizon_steps=3,
                    rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
                )
            except expected_type:
                continue
            else:
                raise AssertionError(
                    f"Expected {expected_type.__name__}, got result {result!r}"
                )


def test_zero_visits_still_calls_helper():
    W = _zero_visit_two_node_world()
    helper_count = 0
    original_helper = register_undetermined_visits_from_snapshot_plan

    def counting_helper(*args, **kwargs):
        nonlocal helper_count
        helper_count += 1
        return original_helper(*args, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=counting_helper,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            **_zero_visit_run_kwargs(),
        )
    assert helper_count == 1


def test_zero_visits_calls_apply_snapshot_fixed_visit_registration_plan_once():
    W = _zero_visit_two_node_world()
    apply_count = 0
    original_apply = apply_snapshot_fixed_visit_registration_plan

    def counting_apply(*args, **kwargs):
        nonlocal apply_count
        apply_count += 1
        return original_apply(*args, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=counting_apply,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            **_zero_visit_run_kwargs(),
        )
    assert apply_count == 1


def test_zero_visits_call_order_is_prepare_helper_apply_without_exec():
    W = _zero_visit_two_node_world()
    events: list[str] = []
    original_prepare = prepare_snapshot_fixed_visit_registration_plan
    original_helper = register_undetermined_visits_from_snapshot_plan
    original_apply = apply_snapshot_fixed_visit_registration_plan

    def tracking_prepare(*args, **kwargs):
        events.append("prepare")
        return original_prepare(*args, **kwargs)

    def tracking_helper(*args, **kwargs):
        events.append("helper")
        return original_helper(*args, **kwargs)

    def tracking_apply(*args, **kwargs):
        events.append("apply")
        return original_apply(*args, **kwargs)

    def tracking_exec(W, **kwargs):
        events.append("exec")
        return _REAL_EXEC_SIMULATION(W, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.prepare_snapshot_fixed_visit_registration_plan",
        side_effect=tracking_prepare,
    ), patch(
        "uxsim.order_control_baseline_driver.register_undetermined_visits_from_snapshot_plan",
        side_effect=tracking_helper,
    ), patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=tracking_apply,
    ), patch.object(UxsimWorld, "exec_simulation", tracking_exec):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            **_zero_visit_run_kwargs(),
        )
    assert events == ["prepare", "helper", "apply"]


def test_zero_visits_fork_result_matches_existing_contract():
    W = _zero_visit_two_node_world()
    result = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        **_zero_visit_run_kwargs(),
    )
    assert result.registered_visit_count == 0
    assert result.fork_steps_executed == 0
    assert result.final_fork_timestep == W.T
    assert result.configured_horizon_steps == 5
    assert result.collector.export_node_baseline_visits("junction_a") == []
    assert result.collector.export_node_baseline_visits("junction_b") == []


def test_raises_when_target_node_rank_state_is_missing():
    W = _build_two_time_value_nodes_world()
    W.T = 15
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_two_node_target_names(),
            baseline_horizon_steps=5,
            rank_states_by_node_name={"junction_a": OrderControlTvtNodeRankState("junction_a")},
        ),
        "Missing rank state for target node 'junction_b'",
    )


def test_ignores_non_target_mapping_nodes():
    W = _build_two_time_value_nodes_world()
    W.T = 15
    unused_state = OrderControlTvtNodeRankState("unused_node")
    before = unused_state.undetermined_visit_keys()
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_two_node_target_names(),
        baseline_horizon_steps=5,
        rank_states_by_node_name={
            "junction_a": OrderControlTvtNodeRankState("junction_a"),
            "junction_b": OrderControlTvtNodeRankState("junction_b"),
            "unused_node": unused_state,
        },
    )
    assert unused_state.undetermined_visit_keys() == before


def test_multi_node_helper_internal_failure_preserves_front_registration_without_apply_or_exec():
    W, vehicle_a, vehicle_b = _build_two_node_snapshot_world_with_visits_on_both_nodes()
    rank_states = _rank_states_for_nodes(["junction_a", "junction_b"])
    rank_a = rank_states["junction_a"]
    rank_b = rank_states["junction_b"]
    visit_key_a = (vehicle_a.name, vehicle_a.order_control_visit_id)
    visit_key_b = (vehicle_b.name, vehicle_b.order_control_visit_id)
    before = _real_world_snapshot(W)
    apply_called = False
    exec_called = False
    original_register = OrderControlTvtNodeRankState.register_undetermined_visits

    def failing_register_on_junction_b(self, visit_keys):
        if self.node_name == "junction_b":
            raise ValueError("junction_b registration failed")
        return original_register(self, visit_keys)

    def fail_apply(*args, **kwargs):
        nonlocal apply_called
        apply_called = True
        raise AssertionError("apply must not be called")

    def fail_exec(W, **kwargs):
        nonlocal exec_called
        exec_called = True
        raise AssertionError("exec must not be called")

    with patch.object(
        OrderControlTvtNodeRankState,
        "register_undetermined_visits",
        failing_register_on_junction_b,
    ), patch(
        "uxsim.order_control_baseline_driver.apply_snapshot_fixed_visit_registration_plan",
        side_effect=fail_apply,
    ), patch.object(UxsimWorld, "exec_simulation", fail_exec):
        _expect_value_error(
            lambda: run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
                W,
                target_node_names=_two_node_target_names(),
                baseline_horizon_steps=3,
                rank_states_by_node_name=rank_states,
            ),
            "junction_b registration failed",
        )

    assert rank_a.is_undetermined(visit_key_a)
    assert not rank_b.is_undetermined(visit_key_b)
    assert apply_called is False
    assert exec_called is False
    _assert_real_world_unchanged(W, before)


def test_leaves_real_world_t_time_collector_unchanged():
    W, _vehicle = _build_arrived_junction_world()
    before = _real_world_snapshot(W)
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
    )
    _assert_real_world_unchanged(W, before)


def test_sets_collector_only_on_fork_world():
    W, _vehicle = _build_arrived_junction_world()
    before_collector = W._order_control_baseline_collector
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
    )
    assert W._order_control_baseline_collector is before_collector


def test_legacy_driver_behavior_unchanged():
    W, vehicle = _build_arrived_junction_world()
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
    )
    assert result.registered_visit_count == 1
    assert result.fork_steps_executed == 3
    assert result.final_fork_timestep == W.T + 3
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot["was_arrived_at_snapshot"] is True


def test_legacy_driver_calls_register_snapshot_fixed_visits_once():
    W, _vehicle = _build_arrived_junction_world()
    call_count = 0
    original_register = register_snapshot_fixed_visits

    def counting_register(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_register(*args, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=counting_register,
    ):
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
        )
    assert call_count == 1


def test_does_not_confirm_ranks():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key = (vehicle.name, vehicle.order_control_visit_id)
    original_confirm = OrderControlTvtNodeRankState.confirm_visits_in_order

    def fail_confirm(*args, **kwargs):
        raise AssertionError("confirm_visits_in_order must not be called")

    with patch.object(
        OrderControlTvtNodeRankState,
        "confirm_visits_in_order",
        fail_confirm,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name={"junction": rank_state},
        )
    assert rank_state.is_undetermined(visit_key)
    assert not rank_state.is_confirmed(visit_key)


def test_does_not_call_baseline_alignment():
    W, _vehicle = _build_arrived_junction_world()
    alignment_called = False

    def fail_alignment(*args, **kwargs):
        nonlocal alignment_called
        alignment_called = True
        raise AssertionError("baseline alignment must not be called")

    with patch(
        "uxsim.order_control_tvt_baseline_alignment.align_snapshot_undetermined_visits_with_node_baseline",
        side_effect=fail_alignment,
    ):
        run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
            rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
        )
    assert alignment_called is False


def test_fork_result_does_not_include_plan_or_rank_ledger_fields():
    W, _vehicle = _build_arrived_junction_world()
    result = run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name=_rank_states_for_nodes(["junction"]),
    )
    field_names = {field.name for field in dataclasses.fields(result)}
    assert field_names == {
        "collector",
        "target_node_names",
        "baseline_timestep_T",
        "configured_horizon_steps",
        "fork_steps_executed",
        "final_fork_timestep",
        "registered_visit_count",
    }


def test_preserves_distinct_visit_keys_for_node_revisit():
    W, vehicle = _build_arrived_junction_world()
    rank_state = OrderControlTvtNodeRankState("junction")
    visit_key_1 = (vehicle.name, 1)
    visit_key_2 = (vehicle.name, 2)
    rank_state.register_undetermined_visits((visit_key_1, visit_key_2))
    run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
        rank_states_by_node_name={"junction": rank_state},
    )
    assert rank_state.is_undetermined(visit_key_1)
    assert rank_state.is_undetermined(visit_key_2)
    assert vehicle.order_control_visit_id == 1


TESTS = [
    test_returns_order_control_baseline_fork_result,
    test_prepare_called_once,
    test_same_plan_passed_to_helper_and_apply,
    test_does_not_call_register_snapshot_fixed_visits,
    test_call_order_prepare_helper_apply_exec_simulation,
    test_registers_unregistered_visit_before_simulation,
    test_does_not_reregister_already_undetermined_visit,
    test_does_not_reregister_already_confirmed_visit,
    test_collector_matches_legacy_snapshot_registration,
    test_helper_value_error_skips_apply_and_exec,
    test_helper_failure_leaves_real_world_unchanged,
    test_apply_failure_skips_exec_preserves_real_world_and_undetermined_registrations,
    test_exec_failure_skips_result_preserves_real_world_and_undetermined_registrations,
    test_post_forward_validation_failure_keeps_undetermined_registrations,
    test_exceptions_do_not_return_partial_fork_result,
    test_zero_visits_still_calls_helper,
    test_zero_visits_calls_apply_snapshot_fixed_visit_registration_plan_once,
    test_zero_visits_call_order_is_prepare_helper_apply_without_exec,
    test_zero_visits_fork_result_matches_existing_contract,
    test_raises_when_target_node_rank_state_is_missing,
    test_ignores_non_target_mapping_nodes,
    test_multi_node_helper_internal_failure_preserves_front_registration_without_apply_or_exec,
    test_leaves_real_world_t_time_collector_unchanged,
    test_sets_collector_only_on_fork_world,
    test_legacy_driver_behavior_unchanged,
    test_legacy_driver_calls_register_snapshot_fixed_visits_once,
    test_does_not_confirm_ranks,
    test_does_not_call_baseline_alignment,
    test_fork_result_does_not_include_plan_or_rank_ledger_fields,
    test_preserves_distinct_visit_keys_for_node_revisit,
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
        "Order-control TVT baseline driver registration tests passed "
        f"({len(TESTS)} tests)."
    )
