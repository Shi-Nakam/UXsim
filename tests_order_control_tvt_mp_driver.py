"""
Tests for the TVT-MP upper driver.

Run from the repository root:
    python tests_order_control_tvt_mp_driver.py
"""

from __future__ import annotations

import dataclasses
import inspect
from contextlib import ExitStack
from unittest.mock import patch

from uxsim.order_control_tvt_mp_atomic_apply import (
    OrderControlTvtMpAtomicApplySetResult,
)
from uxsim.order_control_tvt_mp_final_rank import OrderControlTvtMpFinalRankStatus
from uxsim.order_control_tvt_mp_driver import (
    OrderControlTvtMpDriverResult,
    run_tvt_mp_driver,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import Node, Vehicle, World


STAGE_NAMES = (
    "run_snapshot_fixed_baseline_fork_and_align_undetermined_visits",
    "confirm_already_arrived_undetermined_visits",
    "confirm_leading_nonparticipating_decision_window_visits",
    "select_right_of_entry_decision_window_visits",
    "build_tvt_candidate_visit_set",
    "build_tvt_inlink_candidate_physical_orders",
    "build_tvt_mp_concrete_buyer_candidate_sets",
    "build_tvt_mp_general_trade_ranks",
    "build_tvt_mp_fifo_inspection_results",
    "evaluate_tvt_mp_candidate_local_virtual_calculations",
    "evaluate_tvt_mp_candidate_economics",
    "select_tvt_mp_candidates",
    "calculate_tvt_mp_payments_and_compensations",
    "build_tvt_mp_final_ranks",
    "validate_tvt_mp_final_consistency",
    "apply_tvt_mp_validated_result",
)


class _StageToken:
    def __init__(self, stage_name):
        self.stage_name = stage_name
        self.label = None


class _ResolvedVisit:
    def __init__(self, visit_key, baseline_arrival_timestep):
        self.visit_key = visit_key
        self.baseline_arrival_timestep = baseline_arrival_timestep


class _AlignmentResult:
    def __init__(self, resolved_visits):
        self.resolved_undetermined_visits = tuple(resolved_visits)


class _ForkResult:
    def __init__(self, baseline_timestep_T):
        self.baseline_timestep_T = baseline_timestep_T


class _AlignmentForkResult:
    def __init__(self, baseline_timestep_T, alignment_results):
        self.fork_result = _ForkResult(baseline_timestep_T)
        self.alignment_results = tuple(alignment_results)


class _ArrivedConfirmationResult:
    def __init__(self, alignment_fork_result):
        self.alignment_fork_result = alignment_fork_result


def _new_world(name):
    world = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    world.T = 4
    return world


def _add_plain_node(world, name):
    world.addNode(name, 0, 0)


def _add_tvt_node(world, name, eligible=True):
    node = world.addNode(
        name,
        1,
        0,
        order_control_type="time_value",
        order_control_eligible=True,
    )
    node.order_control_eligible = eligible
    return node


def _tvt_world(node_names):
    world = _new_world("tvt_mp_driver_" + "_".join(node_names))
    _add_plain_node(world, "orig")
    for node_name in node_names:
        _add_tvt_node(world, node_name)
    _add_plain_node(world, "dest")
    world.order_control_tvt_max_candidate_visit_count = 2
    return world


def _enable_route(world):
    if not world.finalized:
        world.finalize_scenario()


def _ensure_trip_route(world):
    if "trip_orig" in world.NODES_NAME_DICT:
        return
    world.addNode("trip_orig", 0, 2)
    world.addNode("trip_dest", 1, 2)
    world.addLink(
        "trip_link",
        "trip_orig",
        "trip_dest",
        length=100,
        free_flow_speed=10,
    )


def _add_vehicle(world, name, participates, vot_declared=0):
    saved_timestep = world.T
    _ensure_trip_route(world)
    _enable_route(world)
    vehicle = Vehicle(
        world,
        "trip_orig",
        "trip_dest",
        0,
        name=name,
        vot_declared=vot_declared,
        vot_true=9,
        participates_in_order_exchange=participates,
    )
    world.T = saved_timestep
    return vehicle


def _patched_stages(calls, fail_at=None, fail_error=None):
    tokens = []
    for index, stage_name in enumerate(STAGE_NAMES):
        if index == 1:
            tokens.append(
                _ArrivedConfirmationResult(_AlignmentForkResult(0, []))
            )
        else:
            tokens.append(_StageToken(stage_name))

    def make_fake(index, stage_name):
        def fake(*args, **kwargs):
            calls.append((stage_name, args, kwargs))
            if fail_at == index:
                raise fail_error
            return tokens[index]
        return fake

    stack = ExitStack()
    for index, stage_name in enumerate(STAGE_NAMES):
        stack.enter_context(
            patch(
                "uxsim.order_control_tvt_mp_driver." + stage_name,
                make_fake(index, stage_name),
            )
        )
    stack.tokens = tokens
    return stack


def _assert_raises(error_type, function):
    try:
        function()
    except error_type as error:
        return error
    except Exception as error:
        raise AssertionError(
            f"expected {error_type.__name__}, got {type(error).__name__}: {error}"
        ) from error
    raise AssertionError(f"expected {error_type.__name__}")


def _call_names(calls):
    names = []
    for stage_name, args, kwargs in calls:
        names.append(stage_name)
    return names


def test_public_function_and_frozen_result_have_one_field():
    signature = inspect.signature(run_tvt_mp_driver)
    assert list(signature.parameters) == ["real_W"]
    parameter = signature.parameters["real_W"]
    assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameter.default is inspect.Parameter.empty
    assert dataclasses.is_dataclass(OrderControlTvtMpDriverResult)
    assert OrderControlTvtMpDriverResult.__dataclass_params__.frozen is True
    field_names = []
    for field in dataclasses.fields(OrderControlTvtMpDriverResult):
        field_names.append(field.name)
    assert field_names == ["atomic_apply_set_result"]
    result = OrderControlTvtMpDriverResult(atomic_apply_set_result=None)
    try:
        result.atomic_apply_set_result = None
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("driver result must be frozen")


def test_driver_source_calls_sixteen_stages_explicitly():
    source = inspect.getsource(run_tvt_mp_driver)
    previous_position = -1
    for stage_name in STAGE_NAMES:
        position = source.find(stage_name + "(")
        assert position > previous_position
        previous_position = position
    assert "getattr" not in source
    assert "decorator" not in source


def test_world_init_sets_tvt_driver_attributes():
    world = _new_world("tvt_attribute_defaults")
    assert world.order_control_tvt_rank_states_by_node_name == {}
    assert world.order_control_tvt_driver_started_timestep is None
    assert world.order_control_tvt_baseline_horizon_steps == 6
    assert world.order_control_tvt_max_candidate_visit_count is None


def test_rejects_non_world_and_invalid_timestep_before_changes():
    error = _assert_raises(ValueError, lambda: run_tvt_mp_driver("not a world"))
    assert "World" in str(error)

    world = _tvt_world(("junction",))
    world.T = True
    error = _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    assert world.order_control_tvt_driver_started_timestep is None

    world.T = 1.5
    error = _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    assert world.order_control_tvt_driver_started_timestep is None


def test_zero_target_nodes_are_a_complete_no_op_even_when_repeated():
    world = _new_world("tvt_zero_targets")
    _add_plain_node(world, "plain")
    world.addNode(
        "batch_node",
        0,
        1,
        order_control_type="batch",
        order_control_eligible=True,
    )
    _add_tvt_node(world, "ineligible", eligible=False)
    world.order_control_tvt_baseline_horizon_steps = 1
    world.order_control_tvt_max_candidate_visit_count = None
    world.order_control_tvt_driver_started_timestep = world.T
    rank_states = world.order_control_tvt_rank_states_by_node_name
    calls = []
    with _patched_stages(calls):
        first = run_tvt_mp_driver(world)
        second = run_tvt_mp_driver(world)
    assert calls == []
    assert first.atomic_apply_set_result is None
    assert second.atomic_apply_set_result is None
    assert world.order_control_tvt_driver_started_timestep == world.T
    assert world.order_control_tvt_rank_states_by_node_name is rank_states
    assert rank_states == {}
    assert world.order_control_tvt_baseline_horizon_steps == 1


def test_target_nodes_keep_registration_order_and_empty_nodes():
    world = _new_world("tvt_registration_order")
    _add_plain_node(world, "orig")
    _add_tvt_node(world, "junction_b")
    world.addNode(
        "fcfs_node",
        2,
        0,
        order_control_type="fcfs",
        order_control_eligible=True,
    )
    _add_tvt_node(world, "junction_a", eligible=False)
    _add_tvt_node(world, "junction_c")
    world.order_control_tvt_max_candidate_visit_count = 3
    calls = []
    with _patched_stages(calls):
        run_tvt_mp_driver(world)
    stage_name, args, kwargs = calls[0]
    assert stage_name == STAGE_NAMES[0]
    assert args == (world,)
    assert kwargs["target_node_names"] == ("junction_b", "junction_c")
    assert kwargs["baseline_horizon_steps"] == 6
    assert kwargs["rank_states_by_node_name"] is (
        world.order_control_tvt_rank_states_by_node_name
    )


def test_duplicate_target_node_name_is_runtime_error_before_start():
    world = _tvt_world(("junction",))
    world.NODES.append(world.NODES[1])
    started_before = world.order_control_tvt_driver_started_timestep
    error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "Duplicate" in str(error)
    assert world.order_control_tvt_driver_started_timestep is started_before


def test_invalid_common_settings_do_not_record_start_and_can_be_retried():
    world = _tvt_world(("junction",))
    world.order_control_tvt_max_candidate_visit_count = None
    error = _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    assert "max_candidate_visit_count" in str(error)
    assert world.order_control_tvt_driver_started_timestep is None

    world.order_control_tvt_max_candidate_visit_count = True
    _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    world.order_control_tvt_max_candidate_visit_count = 0
    _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    world.order_control_tvt_max_candidate_visit_count = 2
    world.order_control_tvt_baseline_horizon_steps = True
    _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    world.order_control_tvt_baseline_horizon_steps = 5
    _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    assert world.order_control_tvt_driver_started_timestep is None

    world.order_control_tvt_baseline_horizon_steps = 6
    calls = []
    with _patched_stages(calls) as stack:
        result = run_tvt_mp_driver(world)
        apply_result = stack.tokens[-1]
    assert result.atomic_apply_set_result is apply_result
    assert world.order_control_tvt_driver_started_timestep == world.T
    assert len(calls) == 16


def test_same_timestep_restart_prefers_runtime_error_over_bad_settings():
    world = _tvt_world(("junction",))
    world.order_control_tvt_driver_started_timestep = world.T
    world.order_control_tvt_max_candidate_visit_count = None
    world.order_control_tvt_baseline_horizon_steps = 1
    error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "already started" in str(error)
    assert world.order_control_tvt_driver_started_timestep == world.T


def test_backward_timestep_is_runtime_error_and_does_not_update_start():
    world = _tvt_world(("junction",))
    world.order_control_tvt_driver_started_timestep = 9
    world.T = 8
    error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "backward" in str(error)
    assert world.order_control_tvt_driver_started_timestep == 9


def test_bad_started_timestep_type_is_runtime_error():
    world = _tvt_world(("junction",))
    world.order_control_tvt_driver_started_timestep = True
    error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "started_timestep" in str(error)
    assert world.order_control_tvt_driver_started_timestep is True


def test_rank_ledger_is_reused_and_not_rebuilt_each_run():
    world = _tvt_world(("junction", "later"))
    existing = OrderControlTvtNodeRankState("junction")
    outside = OrderControlTvtNodeRankState("old_node")
    world.order_control_tvt_rank_states_by_node_name["junction"] = existing
    world.order_control_tvt_rank_states_by_node_name["old_node"] = outside
    rank_states = world.order_control_tvt_rank_states_by_node_name
    calls = []
    with _patched_stages(calls):
        run_tvt_mp_driver(world)
    assert world.order_control_tvt_rank_states_by_node_name is rank_states
    assert rank_states["junction"] is existing
    assert rank_states["old_node"] is outside
    assert isinstance(rank_states["later"], OrderControlTvtNodeRankState)
    assert rank_states["later"].node_name == "later"
    assert calls[0][2]["rank_states_by_node_name"] is rank_states


def test_bad_rank_ledger_is_runtime_error_after_start_is_recorded():
    world = _tvt_world(("junction",))
    world.order_control_tvt_rank_states_by_node_name["junction"] = "not a ledger"
    error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "OrderControlTvtNodeRankState" in str(error)
    assert world.order_control_tvt_driver_started_timestep == world.T

    world.T = world.T + 1
    world.order_control_tvt_rank_states_by_node_name["junction"] = (
        OrderControlTvtNodeRankState("other")
    )
    error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "does not match" in str(error)
    assert world.order_control_tvt_driver_started_timestep == world.T


def test_participation_mapping_uses_vehicle_flag_not_declared_vot():
    world = _tvt_world(("junction",))
    participant = _add_vehicle(world, "participant", True, vot_declared=0)
    outsider = _add_vehicle(world, "outsider", False, vot_declared=0)
    arrived = _ArrivedConfirmationResult(
        _AlignmentForkResult(
            world.T,
            [
                _AlignmentResult(
                    [
                        _ResolvedVisit(("participant", 1), world.T),
                        _ResolvedVisit(("participant", 2), world.T + 1),
                        _ResolvedVisit(("outsider", 1), world.T + 6),
                        _ResolvedVisit(("outsider", 2), world.T + 7),
                    ]
                )
            ],
        )
    )
    captured = {}

    def stage_1(*args, **kwargs):
        return object()

    def stage_2(*args, **kwargs):
        return arrived

    def stage_3(*args, **kwargs):
        captured["mapping"] = kwargs["participates_by_visit_key"]
        captured["args"] = args
        raise RuntimeError("stop after participation")

    with patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[0],
        stage_1,
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[1],
        stage_2,
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[2],
        stage_3,
    ):
        error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "stop after participation" in str(error)
    assert captured["args"][0] is arrived
    assert captured["mapping"] == {
        ("participant", 2): True,
        ("outsider", 1): False,
    }
    assert participant.vot_declared == 0
    assert outsider.participates_in_order_exchange is False
    assert participant.participates_in_order_exchange is True


def test_missing_or_invalid_vehicle_participation_is_runtime_error():
    world = _tvt_world(("junction",))
    arrived = _ArrivedConfirmationResult(
        _AlignmentForkResult(
            world.T,
            [_AlignmentResult([_ResolvedVisit(("missing", 1), world.T + 1)])],
        )
    )

    def stage_2(*args, **kwargs):
        return arrived

    with patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[0],
        lambda *args, **kwargs: object(),
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[1],
        stage_2,
    ):
        error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "not in real_W.VEHICLES" in str(error)

    world.T = world.T + 1
    world.VEHICLES["missing"] = object()
    with patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[0],
        lambda *args, **kwargs: object(),
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[1],
        stage_2,
    ):
        error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "must be a Vehicle" in str(error)

    world.T = world.T + 1
    vehicle = _add_vehicle(world, "present", True)
    del vehicle.participates_in_order_exchange
    arrived_present = _ArrivedConfirmationResult(
        _AlignmentForkResult(
            world.T,
            [_AlignmentResult([_ResolvedVisit(("present", 1), world.T + 2)])],
        )
    )

    def stage_2_present(*args, **kwargs):
        return arrived_present

    world.T = world.T + 1
    with patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[0],
        lambda *args, **kwargs: object(),
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[1],
        stage_2_present,
    ):
        error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "no participates_in_order_exchange" in str(error)

    vehicle.participates_in_order_exchange = 1
    world.T = world.T + 1
    with patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[0],
        lambda *args, **kwargs: object(),
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[1],
        stage_2_present,
    ):
        error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "Python bool" in str(error)


def test_sixteen_stages_are_called_once_in_order_and_apply_is_last():
    world = _tvt_world(("junction_b", "junction_a"))
    calls = []
    with _patched_stages(calls) as stack:
        result = run_tvt_mp_driver(world)
        tokens = stack.tokens
    assert _call_names(calls) == list(STAGE_NAMES)
    assert calls[-1][0] == "apply_tvt_mp_validated_result"
    assert calls[-1][1] == (tokens[14], world, world.order_control_tvt_rank_states_by_node_name)
    assert calls[9][1][0] is world
    assert calls[9][1][1] is tokens[8]
    assert calls[10][1] == (tokens[9], world)
    assert calls[11][1] == (tokens[10], world)
    assert result.atomic_apply_set_result is tokens[15]
    assert type(result.atomic_apply_set_result) is not World
    assert not isinstance(result.atomic_apply_set_result, dict)
    assert not isinstance(result.atomic_apply_set_result, list)


def _assert_labeled_success(label):
    world = _tvt_world(("junction",))
    calls = []
    with _patched_stages(calls) as stack:
        stack.tokens[13].label = label
        result = run_tvt_mp_driver(world)
        tokens = stack.tokens
    assert len(calls) == 16
    assert calls[14][1][0] is tokens[13]
    assert tokens[13].label == label
    assert result.atomic_apply_set_result is tokens[15]


def test_selected_status_still_completes_the_driver():
    _assert_labeled_success("selected")


def test_normal_non_establishment_still_completes_the_driver():
    _assert_labeled_success("normal_non_establishment")


def test_fallback_still_completes_the_driver():
    _assert_labeled_success("fallback")


def test_no_visits_to_confirm_still_completes_the_driver():
    _assert_labeled_success("NO_VISITS_TO_CONFIRM")


def test_seller_zero_still_completes_the_driver():
    _assert_labeled_success("seller_zero")


def test_nonparticipating_visit_still_completes_the_driver():
    _assert_labeled_success("nonparticipating_visit")


def test_multiple_nodes_are_passed_together_to_atomic_apply():
    world = _tvt_world(("north", "south"))
    calls = []
    with _patched_stages(calls):
        run_tvt_mp_driver(world)
    assert calls[0][2]["target_node_names"] == ("north", "south")
    assert calls[-1][1][2] is world.order_control_tvt_rank_states_by_node_name
    assert set(world.order_control_tvt_rank_states_by_node_name) == {"north", "south"}


def test_middle_exception_does_not_call_later_stages_or_roll_back_start():
    world = _tvt_world(("junction",))
    calls = []
    error = RuntimeError("stage five failed")
    with _patched_stages(calls, fail_at=4, fail_error=error):
        caught = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert caught is error
    assert _call_names(calls) == list(STAGE_NAMES[:5])
    assert world.order_control_tvt_driver_started_timestep == world.T
    caught_again = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "already started" in str(caught_again)


def test_atomic_apply_exception_is_not_converted_to_success():
    world = _tvt_world(("junction",))
    calls = []
    error = RuntimeError("apply failed")
    with _patched_stages(calls, fail_at=15, fail_error=error):
        caught = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert caught is error
    assert len(calls) == 16
    assert world.order_control_tvt_driver_started_timestep == world.T


def test_completed_early_ledger_change_remains_after_later_failure():
    world = _tvt_world(("junction",))
    calls = []

    def stage_2(*args, **kwargs):
        calls.append(STAGE_NAMES[1])
        rank_states = kwargs["rank_states_by_node_name"]
        rank_states["junction"].test_early_confirmation = "kept"
        return _ArrivedConfirmationResult(_AlignmentForkResult(world.T, []))

    def stage_3(*args, **kwargs):
        calls.append(STAGE_NAMES[2])
        raise RuntimeError("leading failed")

    with patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[0],
        lambda *args, **kwargs: object(),
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[1],
        stage_2,
    ), patch(
        "uxsim.order_control_tvt_mp_driver." + STAGE_NAMES[2],
        stage_3,
    ):
        error = _assert_raises(RuntimeError, lambda: run_tvt_mp_driver(world))
    assert "leading failed" in str(error)
    ledger = world.order_control_tvt_rank_states_by_node_name["junction"]
    assert ledger.test_early_confirmation == "kept"
    assert world.order_control_tvt_driver_started_timestep == world.T


def test_success_does_not_change_vehicle_participation_vot_or_rng():
    world = _tvt_world(("junction",))
    vehicle = _add_vehicle(world, "car", True, vot_declared=0)
    vehicle.payment_paid = 3
    vehicle.payment_received = 4
    rng_state = world.rng.bit_generator.state
    order_rng_state = world.order_control_rng.bit_generator.state
    link_names = []
    for link in world.LINKS:
        link_names.append(link.name)
    calls = []
    with _patched_stages(calls):
        run_tvt_mp_driver(world)
    assert vehicle.participates_in_order_exchange is True
    assert vehicle.vot_declared == 0
    assert vehicle.vot_true == 9
    assert vehicle.payment_paid == 3
    assert vehicle.payment_received == 4
    assert world.rng.bit_generator.state == rng_state
    assert world.order_control_rng.bit_generator.state == order_rng_state
    after_names = []
    for link in world.LINKS:
        after_names.append(link.name)
    assert after_names == link_names


def test_exec_simulation_and_node_transfer_do_not_call_the_driver():
    simulation_source = inspect.getsource(World.exec_simulation)
    transfer_source = inspect.getsource(Node.transfer)
    assert "run_tvt_mp_driver" not in simulation_source
    assert "order_control_tvt_mp_driver" not in simulation_source
    assert "run_tvt_mp_driver" not in transfer_source
    assert "time_value" not in transfer_source


def _prepare_links(world):
    if not world.finalized:
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()


def _build_quiet_single_junction_world():
    """
    One single-lane time-value junction.

    The only vehicle departs after the decision window, so this run checks
    that the real 16 stages connect. It does not establish a trade.
    """
    world = World(
        name="tvt_mp_driver_quiet_junction",
        deltan=1,
        tmax=300,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig", 0, 0)
    world.addNode(
        "junction",
        1,
        0,
        order_control_type="time_value",
        order_control_eligible=True,
    )
    world.addNode("dest", 2, 0)
    world.addLink(
        "in",
        "orig",
        "junction",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    world.addLink(
        "out",
        "junction",
        "dest",
        length=200,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    late_vehicle = world.addVehicle(
        "orig",
        "dest",
        200,
        name="late_car",
        vot_declared=1.0,
        vot_true=2.0,
        participates_in_order_exchange=True,
    )
    _prepare_links(world)
    world.T = 15
    world.order_control_tvt_baseline_horizon_steps = 6
    world.order_control_tvt_max_candidate_visit_count = 1
    return world, late_vehicle


def test_real_sixteen_stages_reach_atomic_apply_on_quiet_junction():
    world, late_vehicle = _build_quiet_single_junction_world()

    result = run_tvt_mp_driver(world)

    apply_result = result.atomic_apply_set_result
    assert isinstance(apply_result, OrderControlTvtMpAtomicApplySetResult)
    validation_result = apply_result.final_consistency_validation_set_result
    final_rank_set = validation_result.final_rank_set_result
    assert len(final_rank_set.node_final_rank_results) == 1
    node_result = final_rank_set.node_final_rank_results[0]
    assert node_result.node_name == "junction"
    assert node_result.final_rank_status is (
        OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM
    )
    assert node_result.final_rank_visits == ()
    assert world.order_control_tvt_driver_started_timestep == world.T
    rank_state = world.order_control_tvt_rank_states_by_node_name["junction"]
    assert isinstance(rank_state, OrderControlTvtNodeRankState)
    assert rank_state.node_name == "junction"
    assert late_vehicle.participates_in_order_exchange is True
    assert late_vehicle.vot_declared == 1.0
    assert late_vehicle.vot_true == 2.0
    assert late_vehicle.link is None


def test_apply_result_annotation_matches_the_sixteenth_stage():
    field = dataclasses.fields(OrderControlTvtMpDriverResult)[0]
    assert field.type == "OrderControlTvtMpAtomicApplySetResult | None"
    assert OrderControlTvtMpAtomicApplySetResult.__dataclass_params__.frozen is True


def test_tests_registry_matches_defined_functions():
    defined_names = []
    defined_functions = []
    for name, value in list(globals().items()):
        if name.startswith("test_") and callable(value):
            defined_names.append(name)
            defined_functions.append(value)
    tests_names = []
    for function in TESTS:
        tests_names.append(function.__name__)
    assert tests_names == defined_names
    assert list(TESTS) == defined_functions


TESTS = tuple(
    value
    for name, value in list(globals().items())
    if name.startswith("test_") and callable(value)
)


if __name__ == "__main__":
    for current_case in TESTS:
        current_case()
        print("PASS", current_case.__name__)
    print(len(TESTS), "tests passed")
