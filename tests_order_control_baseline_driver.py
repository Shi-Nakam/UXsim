# Unit tests for the fixed-horizon full-World baseline driver (design memo §25.25.28).
#
# Run from the repository root:
#   python tests_order_control_baseline_driver.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

from unittest.mock import patch

from uxsim import World
from uxsim.analyzer import Analyzer
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import (
    OrderControlBaselineForkResult,
    run_snapshot_fixed_baseline_fork,
)
from uxsim.order_control_baseline_snapshot import register_snapshot_fixed_visits
from uxsim.uxsim import World as UxsimWorld


# --- shared helpers ---


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_time_value_junction_world(
    *,
    name="driver_time_value_junction",
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
    name="driver_two_time_value_nodes",
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
    after = _real_world_snapshot(W)
    assert after == before


def _expect_value_error(test_callable, expected_substring):
    try:
        test_callable()
    except ValueError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected ValueError")


def _expect_runtime_error(test_callable, expected_substring):
    try:
        test_callable()
    except RuntimeError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"Expected substring {expected_substring!r} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected RuntimeError")


def _expect_invalid_baseline_horizon(
    test_callable,
    *,
    expected_value_substring: str,
    expected_type_name: str,
):
    try:
        test_callable()
    except ValueError as exc:
        message = str(exc)
        if "must not be bool" not in message:
            raise AssertionError(
                f"Expected bool rejection in error: {exc}"
            ) from exc
        if "Python int greater than or equal to 1" not in message:
            raise AssertionError(
                f"Expected int range requirement in error: {exc}"
            ) from exc
        if expected_value_substring not in message:
            raise AssertionError(
                f"Expected value substring {expected_value_substring!r} in error: {exc}"
            ) from exc
        if f"type={expected_type_name}" not in message:
            raise AssertionError(
                f"Expected type={expected_type_name} in error: {exc}"
            ) from exc
        return
    raise AssertionError("Expected ValueError")


def _junction_target_nodes():
    return ["junction"]


def _two_node_target_names():
    return ["junction_a", "junction_b"]


_REAL_EXEC_SIMULATION = UxsimWorld.__dict__["exec_simulation"]
_REAL_SIMULATION_TERMINATED = UxsimWorld.__dict__["simulation_terminated"]
_REAL_BASIC_ANALYSIS = Analyzer.__dict__["basic_analysis"]


def _patch_exec_simulation_with_counter():
    """Return (context_manager, counter_list) for one exec_simulation call count."""
    counter = [0]
    original_exec = UxsimWorld.__dict__["exec_simulation"]

    def counting_exec(W, **kwargs):
        counter[0] += 1
        return original_exec(W, **kwargs)

    return patch.object(UxsimWorld, "exec_simulation", counting_exec), counter


# --- input validation ---


def test_accepts_list_target_node_names():
    W = _build_time_value_junction_world()
    W.T = 10
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=1,
    )
    assert isinstance(result.target_node_names, tuple)


def test_accepts_tuple_target_node_names():
    W = _build_time_value_junction_world()
    W.T = 10
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=("junction",),
        baseline_horizon_steps=1,
    )
    assert result.target_node_names == ("junction",)


def test_result_freezes_target_node_names_as_tuple():
    W = _build_time_value_junction_world()
    W.T = 10
    input_names = ["junction"]
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=input_names,
        baseline_horizon_steps=1,
    )
    assert result.target_node_names == ("junction",)
    assert result.target_node_names is not input_names


def test_rejects_str_target_node_names():
    W = _build_time_value_junction_world()
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names="junction",
            baseline_horizon_steps=1,
        ),
        "list or tuple",
    )


def test_rejects_bytes_target_node_names():
    W = _build_time_value_junction_world()
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=b"junction",
            baseline_horizon_steps=1,
        ),
        "list or tuple",
    )


def test_rejects_set_target_node_names():
    W = _build_time_value_junction_world()
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names={"junction"},
            baseline_horizon_steps=1,
        ),
        "list or tuple",
    )


def test_rejects_generator_target_node_names():
    W = _build_time_value_junction_world()

    def _node_names():
        yield "junction"

    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_node_names(),
            baseline_horizon_steps=1,
        ),
        "list or tuple",
    )


def test_rejects_empty_list_target_node_names():
    W = _build_time_value_junction_world()
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=[],
            baseline_horizon_steps=1,
        ),
        "at least one target node name",
    )
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=[],
            baseline_horizon_steps=1,
        ),
        "empty node list is an input error",
    )


def test_rejects_empty_tuple_target_node_names():
    W = _build_time_value_junction_world()
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=(),
            baseline_horizon_steps=1,
        ),
        "at least one target node name",
    )
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=(),
            baseline_horizon_steps=1,
        ),
        "zero registered snapshot-fixed visits",
    )


def test_rejects_true_baseline_horizon_steps():
    W = _build_time_value_junction_world()
    _expect_invalid_baseline_horizon(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=True,
        ),
        expected_value_substring="value=True",
        expected_type_name="bool",
    )


def test_rejects_false_baseline_horizon_steps():
    W = _build_time_value_junction_world()
    _expect_invalid_baseline_horizon(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=False,
        ),
        expected_value_substring="value=False",
        expected_type_name="bool",
    )


def test_rejects_zero_baseline_horizon_steps():
    W = _build_time_value_junction_world()
    _expect_invalid_baseline_horizon(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=0,
        ),
        expected_value_substring="value=0",
        expected_type_name="int",
    )


def test_rejects_negative_baseline_horizon_steps():
    W = _build_time_value_junction_world()
    _expect_invalid_baseline_horizon(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=-3,
        ),
        expected_value_substring="value=-3",
        expected_type_name="int",
    )


def test_rejects_float_baseline_horizon_steps():
    W = _build_time_value_junction_world()
    _expect_invalid_baseline_horizon(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=1.5,
        ),
        expected_value_substring="value=1.5",
        expected_type_name="float",
    )


def test_rejects_numpy_int_baseline_horizon_steps():
    np = __import__("numpy")
    W = _build_time_value_junction_world()
    _expect_invalid_baseline_horizon(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=np.int64(5),
        ),
        expected_value_substring="np.int64(5)",
        expected_type_name="int64",
    )


def test_accepts_positive_python_int_baseline_horizon_steps():
    W = _build_time_value_junction_world(tmax=300)
    W.T = 100
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=50,
    )
    assert result.configured_horizon_steps == 50


def test_rejects_real_world_with_collector_configured():
    W = _build_time_value_junction_world()
    W._order_control_baseline_collector = OrderControlBaselineCollector()
    _expect_value_error(
        lambda: run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=1,
        ),
        "real_W._order_control_baseline_collector must be None",
    )


# --- copy and collector ---


def test_zero_visit_run_leaves_real_world_unchanged():
    W = _build_time_value_junction_world()
    W.T = 10
    before = _real_world_snapshot(W)
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    _assert_real_world_unchanged(W, before)
    assert result.registered_visit_count == 0


def test_fork_timestep_matches_real_world_after_copy():
    W = _build_time_value_junction_world(tmax=300)
    W.T = 100
    snapshot_T = W.T
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=5,
    )
    assert result.baseline_timestep_T == snapshot_T
    assert result.final_fork_timestep == snapshot_T + 5


def test_collector_set_only_on_fork_world():
    W = _build_time_value_junction_world()
    W.T = 10
    run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    assert W._order_control_baseline_collector is None


def test_multiple_calls_use_distinct_collectors():
    W = _build_time_value_junction_world()
    W.T = 10
    result1 = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    result2 = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    assert result1.collector is not result2.collector


def test_previous_collector_results_do_not_leak_to_next_call():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="leak_test_vehicle")
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
    first = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
    )
    assert first.registered_visit_count == 1
    second = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    assert second.registered_visit_count == 1
    assert second.collector is not first.collector
    assert (
        second.collector.get_baseline_visit_snapshot(
            vehicle.name, vehicle.order_control_visit_id
        ) is not None
    )


# --- snapshot registration ---


def test_register_snapshot_fixed_visits_called_once_before_exec_simulation():
    W = _build_time_value_junction_world(tmax=300)
    W.T = 100
    vehicle = W.addVehicle("orig", "dest", 0, name="once_call_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=W.T,
    )
    events: list[str] = []
    original_register = register_snapshot_fixed_visits

    def tracking_register(fork_W, collector, *, target_node_names):
        events.append("register")
        return original_register(
            fork_W, collector, target_node_names=target_node_names
        )

    def tracking_exec(W, **kwargs):
        events.append("exec")
        return _REAL_EXEC_SIMULATION(W, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=tracking_register,
    ), patch.object(UxsimWorld, "exec_simulation", tracking_exec):
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=5,
        )
    assert events == ["register", "exec"]


def test_snapshot_exception_propagates_without_result():
    W = _build_time_value_junction_world()
    W.T = 10
    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=ValueError("snapshot registration failed"),
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            )
        except ValueError as exc:
            assert "snapshot registration failed" in str(exc)
        else:
            raise AssertionError("Expected ValueError")


def test_registration_failure_returns_no_result():
    W = _build_time_value_junction_world()
    W.T = 10
    before = _real_world_snapshot(W)
    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=ValueError("snapshot registration failed"),
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    _assert_real_world_unchanged(W, before)


# --- zero total registered visits ---


def test_zero_total_registered_visits_returns_zero_step_result():
    W = _build_two_time_value_nodes_world()
    W.T = 15
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_two_node_target_names(),
        baseline_horizon_steps=50,
    )
    assert result.registered_visit_count == 0
    assert result.fork_steps_executed == 0


def test_zero_total_skips_exec_simulation():
    W = _build_two_time_value_nodes_world()
    W.T = 15
    with patch.object(UxsimWorld, "exec_simulation") as mock_exec:
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_two_node_target_names(),
            baseline_horizon_steps=50,
        )
    mock_exec.assert_not_called()


def test_zero_total_result_fields():
    W = _build_two_time_value_nodes_world()
    W.T = 42
    horizon = 50
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_two_node_target_names(),
        baseline_horizon_steps=horizon,
    )
    assert isinstance(result, OrderControlBaselineForkResult)
    assert result.target_node_names == ("junction_a", "junction_b")
    assert result.baseline_timestep_T == 42
    assert result.configured_horizon_steps == horizon
    assert result.fork_steps_executed == 0
    assert result.final_fork_timestep == 42
    assert result.registered_visit_count == 0
    assert isinstance(result.collector, OrderControlBaselineCollector)
    assert result.collector.export_node_baseline_visits("junction_a") == []
    assert result.collector.export_node_baseline_visits("junction_b") == []


def test_zero_total_registered_visits_skips_insufficient_margin_validation():
    W = _build_time_value_junction_world(tmax=250)
    snapshot_T = 200
    horizon = 50
    W.T = snapshot_T
    remaining_steps = W.TSIZE - W.T
    required_steps = horizon + 1
    assert remaining_steps < required_steps
    before = _real_world_snapshot(W)
    with patch.object(UxsimWorld, "exec_simulation") as mock_exec:
        result = run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=horizon,
        )
    mock_exec.assert_not_called()
    _assert_real_world_unchanged(W, before)
    assert result.registered_visit_count == 0
    assert result.fork_steps_executed == 0
    assert result.final_fork_timestep == snapshot_T
    assert result.baseline_timestep_T == snapshot_T
    assert result.configured_horizon_steps == horizon


def test_partial_node_zero_still_forwards_when_other_node_has_visits():
    W = _build_two_time_value_nodes_world(tmax=300)
    snapshot_T = 30
    W.T = snapshot_T
    vehicle = W.addVehicle("orig_a", "dest", 0, name="node_a_vehicle")
    _advance_until_on_inlink(vehicle, "in_a")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in_a",
        target_node_name="junction_a",
        outlink_name="mid_link",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_two_node_target_names(),
        baseline_horizon_steps=5,
    )
    assert result.registered_visit_count == 1
    assert result.fork_steps_executed == 5
    assert result.final_fork_timestep == snapshot_T + 5
    assert len(result.collector.export_node_baseline_visits("junction_a")) == 1
    assert result.collector.export_node_baseline_visits("junction_b") == []


# --- one timestep margin ---


def test_succeeds_when_remaining_steps_equals_horizon_plus_one():
    W = _build_time_value_junction_world(tmax=251)
    snapshot_T = 200
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="margin_ok_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=50,
    )
    assert result.final_fork_timestep == snapshot_T + 50
    assert result.final_fork_timestep < W.TSIZE


def test_rejects_when_remaining_steps_equals_horizon_only():
    W = _build_time_value_junction_world(tmax=250)
    snapshot_T = 200
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="margin_short_vehicle")
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
    try:
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=50,
        )
    except ValueError as exc:
        message = str(exc)
        assert "Insufficient remaining fork timesteps" in message
        assert "baseline_horizon_steps=50" in message
        assert "remaining_steps=50" in message
        assert "required_steps=51" in message
        assert "fork_W.T=200" in message
        assert "fork_W.TSIZE=250" in message
        assert "at least one timestep before World termination" in message
    else:
        raise AssertionError("Expected ValueError")


def test_succeeds_with_sufficient_margin_example():
    W = _build_time_value_junction_world(tmax=250)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="ample_margin_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=50,
    )
    assert result.final_fork_timestep == 150
    assert result.final_fork_timestep < W.TSIZE


def test_does_not_automatically_shorten_horizon():
    W = _build_time_value_junction_world(tmax=250)
    snapshot_T = 200
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="no_shorten_vehicle")
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
    try:
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=50,
        )
    except ValueError as exc:
        assert "baseline_horizon_steps=50" in str(exc)
    else:
        raise AssertionError("Expected ValueError for insufficient margin")


# --- batch forward ---


def test_calls_exec_simulation_once():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="batch_once_vehicle")
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
    patch_ctx, call_counter = _patch_exec_simulation_with_counter()
    with patch_ctx:
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=50,
        )
    assert call_counter[0] == 1


def test_exec_simulation_duration_matches_horizon():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="duration_vehicle")
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
    captured = {}

    def capturing_exec(W, **kwargs):
        captured.update(kwargs)
        return _REAL_EXEC_SIMULATION(W, **kwargs)

    with patch.object(UxsimWorld, "exec_simulation", capturing_exec):
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=50,
        )
    assert captured["duration_t2"] == 50 * W.DELTAT


def test_advances_timestep_by_configured_horizon():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="advance_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=50,
    )
    assert result.fork_steps_executed == 50
    assert result.final_fork_timestep == snapshot_T + 50


def test_final_timestep_remains_below_tsize():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="below_tsize_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=50,
    )
    assert result.final_fork_timestep < W.TSIZE


def test_simulation_terminated_not_called():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="no_term_vehicle")
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
    termination_calls = []

    def tracking_simulation_terminated(W):
        termination_calls.append(1)
        return _REAL_SIMULATION_TERMINATED(W)

    with patch.object(
        UxsimWorld, "simulation_terminated", tracking_simulation_terminated
    ):
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=50,
        )
    assert termination_calls == []


def test_analyzer_basic_analysis_not_called():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="no_analysis_vehicle")
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
    analysis_calls = []

    def tracking_basic_analysis(analyzer_self):
        analysis_calls.append(1)
        return _REAL_BASIC_ANALYSIS(analyzer_self)

    with patch.object(Analyzer, "basic_analysis", tracking_basic_analysis):
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=50,
        )
    assert analysis_calls == []


# --- collector results ---


def test_preserves_arrived_vehicle_snapshot_information():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 25
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_info_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        arrival_tiebreaker=0.25,
        snapshot_timestep=snapshot_T,
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
    )
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot["was_arrived_at_snapshot"] is True
    assert snapshot["baseline_arrival_timestep"] == 10
    assert snapshot["arrival_tiebreaker"] == 0.25


def test_records_arrival_for_not_yet_arrived_vehicle_after_forward():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 5
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="future_arrival_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=30,
    )
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot["was_arrived_at_snapshot"] is False
    assert snapshot["baseline_arrival_timestep"] is not None


def test_leaves_none_for_non_arriving_vehicle():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 5
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="no_arrival_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T, x_position=5.0
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot["baseline_arrival_timestep"] is None
    assert snapshot["baseline_passage_timestep"] is None


def test_leaves_passage_none_for_arrived_not_passed():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 25
    W.T = snapshot_T
    outlink = W.get_link("out")
    blocker = W.addVehicle("orig", "dest", 0, name="outlink_blocker_vehicle")
    blocker.link = outlink
    blocker.state = "run"
    blocker.x = 0.0
    blocker.link_arrival_time = 0.0
    if blocker not in outlink.vehicles:
        outlink.vehicles.append(blocker)

    vehicle = W.addVehicle("orig", "dest", 0, name="arrived_not_passed_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=3,
    )
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot["baseline_arrival_timestep"] == 10
    assert snapshot["baseline_passage_timestep"] is None


def test_records_passage_when_vehicle_passes():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="passing_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=15,
    )
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot["baseline_passage_timestep"] is not None


def test_succeeds_when_baseline_information_remains_unresolved():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 5
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="partial_none_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_not_yet_arrived_vehicle_at_snapshot(
        W, vehicle, inlink_name="in", snapshot_timestep=snapshot_T, x_position=5.0
    )
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=1,
    )
    snapshot = result.collector.get_baseline_visit_snapshot(
        vehicle.name, vehicle.order_control_visit_id
    )
    assert snapshot is not None
    assert snapshot["was_arrived_at_snapshot"] is False
    assert snapshot["baseline_arrival_timestep"] is None
    assert snapshot["baseline_passage_timestep"] is None


def test_outside_fixed_set_vehicle_does_not_increase_count():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    fixed_vehicle = W.addVehicle("orig", "dest", 0, name="fixed_vehicle")
    _advance_until_on_inlink(fixed_vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        W,
        fixed_vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=10,
        snapshot_timestep=snapshot_T,
    )
    before = _real_world_snapshot(W)

    def exec_with_outside_fixed_set_notification(fork_W, **kwargs):
        collector = fork_W._order_control_baseline_collector
        collector.record_baseline_arrival(
            vehicle_name="outside_fixed_vehicle",
            visit_id=99,
            node_name="junction",
            baseline_arrival_timestep=fork_W.T + 1,
            arrival_tiebreaker=0.5,
            route_next_link_name="out",
        )
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    with patch.object(
        UxsimWorld, "exec_simulation", exec_with_outside_fixed_set_notification
    ):
        result = run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=_junction_target_nodes(),
            baseline_horizon_steps=3,
        )

    _assert_real_world_unchanged(W, before)
    exported_names = {
        record["vehicle_name"]
        for record in result.collector.export_node_baseline_visits("junction")
    }
    assert exported_names == {"fixed_vehicle"}
    assert "outside_fixed_vehicle" not in exported_names
    assert result.registered_visit_count == 1
    assert (
        len(result.collector.export_node_baseline_visits("junction"))
        == result.registered_visit_count
    )


def test_registration_count_unchanged_after_forward():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="count_stable_vehicle")
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
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=_junction_target_nodes(),
        baseline_horizon_steps=4,
    )
    exported = sum(
        len(result.collector.export_node_baseline_visits(node_name))
        for node_name in result.target_node_names
    )
    assert exported == result.registered_visit_count == 1


def test_runtime_error_when_registration_count_mismatch_after_snapshot_registration():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="mismatch_register_vehicle")
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
    before = _real_world_snapshot(W)
    exec_calls = [0]

    def wrong_count_register(fork_W, collector, *, target_node_names):
        actual_count = register_snapshot_fixed_visits(
            fork_W, collector, target_node_names=target_node_names
        )
        return actual_count + 1

    def tracking_exec(fork_W, **kwargs):
        exec_calls[0] += 1
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=wrong_count_register,
    ), patch.object(UxsimWorld, "exec_simulation", tracking_exec):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "registered_visit_count=2" in message
            assert "exported_visit_count=1" in message
            assert "after snapshot registration" in message
            assert "('junction',)" in message
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)
    assert exec_calls[0] == 0


def test_runtime_error_when_registration_count_mismatch_after_baseline_forward():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="mismatch_forward_vehicle")
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
    before = _real_world_snapshot(W)

    def exec_adding_extra_fixed_visit(fork_W, **kwargs):
        collector = fork_W._order_control_baseline_collector
        collector.register_snapshot_visit(
            vehicle_name="extra_fixed_vehicle",
            vehicle_id=99,
            node_name="junction",
            inlink_name="in",
            visit_id=99,
            was_arrived_at_snapshot=False,
            baseline_arrival_timestep=None,
            arrival_tiebreaker=None,
            route_next_link_name=None,
            baseline_passage_timestep=None,
        )
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    with patch.object(
        UxsimWorld, "exec_simulation", exec_adding_extra_fixed_visit
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=3,
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "registered_visit_count=1" in message
            assert "exported_visit_count=2" in message
            assert "after baseline forward" in message
            assert "('junction',)" in message
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)


def test_runtime_error_when_real_world_changes_before_success_return():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="real_world_change_vehicle")
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
    saved_t = W.T
    saved_time = W.TIME

    def exec_mutating_real_world(fork_W, **kwargs):
        W.T = W.T + 1
        W.TIME = W.T * W.DELTAT
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    try:
        with patch.object(UxsimWorld, "exec_simulation", exec_mutating_real_world):
            try:
                run_snapshot_fixed_baseline_fork(
                    W,
                    target_node_names=_junction_target_nodes(),
                    baseline_horizon_steps=3,
                )
            except RuntimeError as exc:
                message = str(exc)
                assert "real_W.T changed" in message
                assert f"before={saved_t}" in message
                assert f"after={saved_t + 1}" in message
            else:
                raise AssertionError("Expected RuntimeError")
    finally:
        W.T = saved_t
        W.TIME = saved_time


def test_runtime_error_when_real_world_time_changes_before_success_return():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="real_world_time_change_vehicle")
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
    saved_t = W.T
    saved_time = W.TIME
    mutated_time = saved_time + 999.0

    def exec_mutating_real_world_time_only(fork_W, **kwargs):
        W.TIME = mutated_time
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    try:
        with patch.object(
            UxsimWorld, "exec_simulation", exec_mutating_real_world_time_only
        ):
            try:
                run_snapshot_fixed_baseline_fork(
                    W,
                    target_node_names=_junction_target_nodes(),
                    baseline_horizon_steps=3,
                )
            except RuntimeError as exc:
                message = str(exc)
                assert "real_W.TIME changed" in message
                assert f"before={saved_time}" in message
                assert f"after={mutated_time}" in message
            else:
                raise AssertionError("Expected RuntimeError")
    finally:
        W.T = saved_t
        W.TIME = saved_time
    assert W._order_control_baseline_collector is None


def test_runtime_error_when_real_world_collector_changes_before_success_return():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 20
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="real_world_collector_change_vehicle")
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
    saved_t = W.T
    saved_time = W.TIME
    mutated_collector = OrderControlBaselineCollector()

    def exec_mutating_real_world_collector_only(fork_W, **kwargs):
        W._order_control_baseline_collector = mutated_collector
        return _REAL_EXEC_SIMULATION(fork_W, **kwargs)

    try:
        with patch.object(
            UxsimWorld,
            "exec_simulation",
            exec_mutating_real_world_collector_only,
        ):
            try:
                run_snapshot_fixed_baseline_fork(
                    W,
                    target_node_names=_junction_target_nodes(),
                    baseline_horizon_steps=3,
                )
            except RuntimeError as exc:
                message = str(exc)
                assert "real_W._order_control_baseline_collector changed" in message
                assert "before=None" in message
                assert f"after={mutated_collector!r}" in message
            else:
                raise AssertionError("Expected RuntimeError")
    finally:
        W.T = saved_t
        W.TIME = saved_time
        W._order_control_baseline_collector = None
    assert W.T == saved_t
    assert W.TIME == saved_time


def test_world_copy_propagates_original_exception():
    W = _build_time_value_junction_world()
    W.T = 10
    before = _real_world_snapshot(W)
    with patch.object(
        UxsimWorld, "copy", side_effect=RuntimeError("copy failed for test")
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            )
        except RuntimeError as exc:
            assert str(exc) == "copy failed for test"
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)


# --- inconsistency and exceptions ---


def test_runtime_error_when_copy_returns_same_object():
    W = _build_time_value_junction_world()
    W.T = 10
    with patch.object(UxsimWorld, "copy", return_value=W):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            ),
            "distinct copy",
        )


def test_runtime_error_when_fork_timestep_mismatch_after_copy():
    W = _build_time_value_junction_world()
    W.T = 10
    bad_fork = W.copy()
    bad_fork.T = 99
    with patch.object(UxsimWorld, "copy", return_value=bad_fork):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            ),
            "baseline_timestep_T",
        )


def test_runtime_error_when_fork_collector_non_none_after_copy():
    W = _build_time_value_junction_world()
    W.T = 10
    bad_fork = W.copy()
    bad_fork._order_control_baseline_collector = OrderControlBaselineCollector()
    with patch.object(UxsimWorld, "copy", return_value=bad_fork):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            ),
            "must be None immediately after copy",
        )


def test_runtime_error_when_forward_does_not_advance_expected_steps():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="bad_advance_vehicle")
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

    def short_forward(W, **kwargs):
        return _REAL_EXEC_SIMULATION(W, duration_t2=W.DELTAT)

    with patch.object(UxsimWorld, "exec_simulation", short_forward):
        _expect_runtime_error(
            lambda: run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=50,
            ),
            "did not advance by baseline_horizon_steps",
        )


def test_runtime_error_when_forward_advances_more_than_configured_horizon():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    horizon = 50
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="over_advance_vehicle")
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
    before = _real_world_snapshot(W)
    expected_fork_timestep_after = snapshot_T + horizon

    def exec_advancing_too_far(fork_W, **kwargs):
        _REAL_EXEC_SIMULATION(fork_W, **kwargs)
        fork_W.T = expected_fork_timestep_after + 1
        return 0

    with patch.object(UxsimWorld, "exec_simulation", exec_advancing_too_far):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=horizon,
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "did not advance by baseline_horizon_steps" in message
            assert f"fork_timestep_before={snapshot_T}" in message
            assert f"fork_W.T={expected_fork_timestep_after + 1}" in message
            assert f"baseline_horizon_steps={horizon}" in message
            assert (
                f"expected_fork_timestep_after={expected_fork_timestep_after}"
                in message
            )
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)


def test_runtime_error_when_public_driver_forward_reaches_world_termination():
    W = _build_time_value_junction_world(tmax=251)
    snapshot_T = 200
    horizon = 50
    W.T = snapshot_T
    remaining_steps = W.TSIZE - W.T
    required_steps = horizon + 1
    assert remaining_steps == required_steps
    vehicle = W.addVehicle("orig", "dest", 0, name="termination_safety_net_vehicle")
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
    before = _real_world_snapshot(W)
    expected_fork_timestep_after = snapshot_T + horizon
    assert expected_fork_timestep_after == W.TSIZE - 1

    def exec_reaching_world_termination(fork_W, **kwargs):
        _REAL_EXEC_SIMULATION(fork_W, **kwargs)
        fork_W.T = fork_W.TSIZE
        return 1

    with patch.object(
        UxsimWorld, "exec_simulation", exec_reaching_world_termination
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=horizon,
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "did not advance by baseline_horizon_steps" in message
            assert f"fork_timestep_before={snapshot_T}" in message
            assert f"fork_W.T={W.TSIZE}" in message
            assert f"baseline_horizon_steps={horizon}" in message
            assert (
                f"expected_fork_timestep_after={expected_fork_timestep_after}"
                in message
            )
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)


def test_runtime_error_when_world_reaches_termination_after_forward():
    from uxsim.order_control_baseline_driver import _validate_completed_fork_forward

    W = _build_time_value_junction_world(tmax=300)
    W.T = W.TSIZE
    _expect_runtime_error(
        lambda: _validate_completed_fork_forward(
            fork_W=W,
            fork_timestep_before=W.TSIZE - 50,
            baseline_horizon_steps=50,
        ),
        "reached or passed World termination",
    )


def test_real_world_unchanged_on_value_error_before_copy():
    W = _build_time_value_junction_world()
    before = _real_world_snapshot(W)
    try:
        run_snapshot_fixed_baseline_fork(
            W,
            target_node_names=[],
            baseline_horizon_steps=1,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
    _assert_real_world_unchanged(W, before)


def test_real_world_unchanged_on_snapshot_registration_failure():
    W = _build_time_value_junction_world()
    W.T = 10
    before = _real_world_snapshot(W)
    with patch(
        "uxsim.order_control_baseline_driver.register_snapshot_fixed_visits",
        side_effect=ValueError("snapshot registration failed"),
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=1,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    _assert_real_world_unchanged(W, before)


def test_no_result_on_exec_simulation_exception():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 100
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="exec_fail_vehicle")
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
    before = _real_world_snapshot(W)
    with patch.object(
        UxsimWorld,
        "exec_simulation",
        side_effect=RuntimeError("exec failed"),
    ):
        try:
            run_snapshot_fixed_baseline_fork(
                W,
                target_node_names=_junction_target_nodes(),
                baseline_horizon_steps=50,
            )
        except RuntimeError as exc:
            assert "exec failed" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError")
    _assert_real_world_unchanged(W, before)


# --- result contract ---


def test_completed_result_fields():
    W = _build_time_value_junction_world(tmax=300)
    snapshot_T = 60
    W.T = snapshot_T
    vehicle = W.addVehicle("orig", "dest", 0, name="completed_result_vehicle")
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
    horizon = 7
    result = run_snapshot_fixed_baseline_fork(
        W,
        target_node_names=["junction"],
        baseline_horizon_steps=horizon,
    )
    assert isinstance(result.collector, OrderControlBaselineCollector)
    assert result.target_node_names == ("junction",)
    assert result.baseline_timestep_T == snapshot_T
    assert result.configured_horizon_steps == horizon
    assert result.fork_steps_executed == horizon
    assert result.final_fork_timestep == snapshot_T + horizon
    assert result.registered_visit_count == 1
    assert not hasattr(result, "return_code")
    assert not hasattr(result, "early_terminated")
    assert not hasattr(result, "fork_W")


TESTS = [
    test_accepts_list_target_node_names,
    test_accepts_tuple_target_node_names,
    test_result_freezes_target_node_names_as_tuple,
    test_rejects_str_target_node_names,
    test_rejects_bytes_target_node_names,
    test_rejects_set_target_node_names,
    test_rejects_generator_target_node_names,
    test_rejects_empty_list_target_node_names,
    test_rejects_empty_tuple_target_node_names,
    test_rejects_true_baseline_horizon_steps,
    test_rejects_false_baseline_horizon_steps,
    test_rejects_zero_baseline_horizon_steps,
    test_rejects_negative_baseline_horizon_steps,
    test_rejects_float_baseline_horizon_steps,
    test_rejects_numpy_int_baseline_horizon_steps,
    test_accepts_positive_python_int_baseline_horizon_steps,
    test_rejects_real_world_with_collector_configured,
    test_zero_visit_run_leaves_real_world_unchanged,
    test_fork_timestep_matches_real_world_after_copy,
    test_collector_set_only_on_fork_world,
    test_multiple_calls_use_distinct_collectors,
    test_previous_collector_results_do_not_leak_to_next_call,
    test_register_snapshot_fixed_visits_called_once_before_exec_simulation,
    test_snapshot_exception_propagates_without_result,
    test_registration_failure_returns_no_result,
    test_zero_total_registered_visits_returns_zero_step_result,
    test_zero_total_skips_exec_simulation,
    test_zero_total_result_fields,
    test_zero_total_registered_visits_skips_insufficient_margin_validation,
    test_partial_node_zero_still_forwards_when_other_node_has_visits,
    test_succeeds_when_remaining_steps_equals_horizon_plus_one,
    test_rejects_when_remaining_steps_equals_horizon_only,
    test_succeeds_with_sufficient_margin_example,
    test_does_not_automatically_shorten_horizon,
    test_calls_exec_simulation_once,
    test_exec_simulation_duration_matches_horizon,
    test_advances_timestep_by_configured_horizon,
    test_final_timestep_remains_below_tsize,
    test_simulation_terminated_not_called,
    test_analyzer_basic_analysis_not_called,
    test_preserves_arrived_vehicle_snapshot_information,
    test_records_arrival_for_not_yet_arrived_vehicle_after_forward,
    test_leaves_none_for_non_arriving_vehicle,
    test_leaves_passage_none_for_arrived_not_passed,
    test_records_passage_when_vehicle_passes,
    test_succeeds_when_baseline_information_remains_unresolved,
    test_outside_fixed_set_vehicle_does_not_increase_count,
    test_registration_count_unchanged_after_forward,
    test_runtime_error_when_registration_count_mismatch_after_snapshot_registration,
    test_runtime_error_when_registration_count_mismatch_after_baseline_forward,
    test_runtime_error_when_real_world_changes_before_success_return,
    test_runtime_error_when_real_world_time_changes_before_success_return,
    test_runtime_error_when_real_world_collector_changes_before_success_return,
    test_world_copy_propagates_original_exception,
    test_runtime_error_when_copy_returns_same_object,
    test_runtime_error_when_fork_timestep_mismatch_after_copy,
    test_runtime_error_when_fork_collector_non_none_after_copy,
    test_runtime_error_when_forward_does_not_advance_expected_steps,
    test_runtime_error_when_forward_advances_more_than_configured_horizon,
    test_runtime_error_when_public_driver_forward_reaches_world_termination,
    test_runtime_error_when_world_reaches_termination_after_forward,
    test_real_world_unchanged_on_value_error_before_copy,
    test_real_world_unchanged_on_snapshot_registration_failure,
    test_no_result_on_exec_simulation_exception,
    test_completed_result_fields,
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
        f"Order-control baseline driver tests passed ({len(TESTS)} tests)."
    )
