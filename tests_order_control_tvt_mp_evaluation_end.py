"""
Tests for TVT-MP auto-start, evaluation-end control, and fork release.

Run from the repository root:
    python tests_order_control_tvt_mp_evaluation_end.py
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

from uxsim.analyzer import Analyzer
from uxsim.order_control_baseline_driver import run_snapshot_fixed_baseline_fork
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageCommonFrozenInput,
    OrderControlTvtMpActualPassageMonetaryFrozenInput,
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitStatus,
    OrderControlTvtMpActualNodePassageRecord,
    commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization,
    prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization,
    commit_tvt_mp_trade_ex_post_evaluation,
    prepare_tvt_mp_trade_ex_post_evaluation,
    OrderControlTvtMpTradeExPostEvaluationStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_mp_driver import (
    OrderControlTvtMpDriverResult,
    run_tvt_mp_driver,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRouteOrigin,
)
from uxsim.uxsim import Link, Node, World
from tests_order_control_baseline_driver import (
    _advance_until_on_inlink,
    _build_time_value_junction_world,
    _place_arrived_vehicle_at_snapshot,
)


def _plain_world(name, tmax):
    world = World(
        name=name,
        deltan=1,
        tmax=tmax,
        reaction_time=1,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig", 0, 0)
    world.addNode("dest", 1, 0)
    world.addLink(
        "link",
        "orig",
        "dest",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    return world


def _add_tvt_node(world, name, x):
    world.addNode(
        name,
        x,
        1,
        order_control_type="time_value",
        order_control_eligible=True,
    )


def _recording_driver(calls):
    def fake(world):
        calls.append(world.T)
        return OrderControlTvtMpDriverResult(atomic_apply_set_result=None)
    return fake


def _assert_raises(error_type, function):
    try:
        function()
    except error_type as error:
        return error
    raise AssertionError(f"Expected {error_type.__name__}")


def _assert_raises(error_type, function):
    try:
        function()
    except error_type as error:
        return error
    raise AssertionError(f"Expected {error_type.__name__}")


_ROUTE_ORIGIN = OrderControlTvtMpLocalBindingRouteOrigin.RANK_LEDGER_FORMAL_ROUTE
_HOOK_DECISION_TIMESTEP = 10
_HOOK_BASELINE_TIMESTEP = 10
_HOOK_CANDIDATE_TIMESTEP = 8
_HOOK_ACTUAL_TIMESTEP = 7


def _hook_visit_key(vehicle_name, visit_index=1):
    return (vehicle_name, visit_index)


def _hook_common_frozen():
    return OrderControlTvtMpActualPassageCommonFrozenInput(
        baseline_local_rank=2,
        post_trade_local_rank=1,
        rank_change=1,
        route_origin=_ROUTE_ORIGIN,
    )


def _hook_monetary_frozen():
    return OrderControlTvtMpActualPassageMonetaryFrozenInput(
        declared_vot_per_second=1.0,
        payment_paid_in_this_transaction=0,
        payment_received_in_this_transaction=0,
    )


def _hook_observed_record(visit_key, role):
    return OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=_HOOK_DECISION_TIMESTEP,
        node_name="node_a",
        buyers_sorted=(_hook_visit_key("buyer_1", 1),),
        visit_key=visit_key,
        vehicle_name=visit_key[0],
        role=role,
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
        ),
        baseline_passage_timestep=_HOOK_BASELINE_TIMESTEP,
        candidate_passage_timestep=_HOOK_CANDIDATE_TIMESTEP,
        true_vot_per_second=0.5,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link_pred",
        baseline_minus_candidate_passage_timesteps=2,
        baseline_minus_candidate_passage_seconds=120,
        baseline_minus_candidate_time_value=60.0,
        baseline_minus_actual_passage_timesteps=3,
        baseline_minus_actual_passage_seconds=180,
        baseline_minus_actual_time_value=90.0,
        candidate_minus_actual_passage_timesteps=1,
        candidate_minus_actual_passage_seconds=60,
        candidate_minus_actual_time_value=30.0,
        actual_passage_timestep=_HOOK_ACTUAL_TIMESTEP,
        actual_route_next_link_name="link_actual",
    )


def _append_hook_node_history(world, node_name, visit_key):
    history_registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    existing = history_registry.records_by_node_name.get(node_name, ())
    record = OrderControlTvtMpActualNodePassageRecord(
        visit_key=visit_key,
        actual_passage_timestep=_HOOK_ACTUAL_TIMESTEP,
        actual_route_next_link_name="link_actual",
        actual_node_passage_rank=len(existing) + 1,
    )
    history_registry.records_by_node_name[node_name] = existing + (record,)


def _register_hook_trade(
    world,
    *,
    node_name="node_a",
    observed_buyer=False,
):
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    buyers_sorted = (_hook_visit_key("buyer_1", 1),)
    buyer_key = _hook_visit_key("buyer_a", 1)
    seller_key = _hook_visit_key("seller_a", 1)
    buyer_status = (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
        if observed_buyer
        else OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    buyer_record = None
    if observed_buyer:
        buyer_record = _hook_observed_record(
            buyer_key,
            OrderControlTvtMpActualPassageRole.BUYER,
        )
        _append_hook_node_history(world, node_name, buyer_key)
    buyer_entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=_HOOK_DECISION_TIMESTEP,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        visit_key=buyer_key,
        vehicle_name="buyer_a",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        wait_status=buyer_status,
        baseline_passage_timestep=_HOOK_BASELINE_TIMESTEP,
        candidate_passage_timestep=_HOOK_CANDIDATE_TIMESTEP,
        true_vot_per_second=0.5,
        baseline_minus_candidate_passage_timesteps=2,
        baseline_minus_candidate_passage_seconds=120,
        baseline_minus_candidate_time_value=60.0,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link_pred",
        common_frozen_input=_hook_common_frozen(),
        monetary_frozen_input=_hook_monetary_frozen(),
        actual_passage_observation_record=buyer_record,
    )
    seller_entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=_HOOK_DECISION_TIMESTEP,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        visit_key=seller_key,
        vehicle_name="seller_a",
        role=OrderControlTvtMpActualPassageRole.SELLER,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=_HOOK_BASELINE_TIMESTEP,
        candidate_passage_timestep=_HOOK_CANDIDATE_TIMESTEP,
        true_vot_per_second=0.5,
        baseline_minus_candidate_passage_timesteps=2,
        baseline_minus_candidate_passage_seconds=120,
        baseline_minus_candidate_time_value=60.0,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link_pred",
        common_frozen_input=_hook_common_frozen(),
        monetary_frozen_input=_hook_monetary_frozen(),
        actual_passage_observation_record=None,
    )
    registry.entries_by_node_name_and_visit_key[(node_name, buyer_key)] = buyer_entry
    registry.entries_by_node_name_and_visit_key[(node_name, seller_key)] = seller_entry
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=_HOOK_DECISION_TIMESTEP,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        all_visit_keys=(buyer_key, seller_key),
        buyer_visit_keys=(buyer_key,),
        seller_visit_keys=(seller_key,),
        nonparticipating_visit_keys=(),
        buyer_seller_actual_passage_completion_notified=False,
    )
    transaction_key = (_HOOK_DECISION_TIMESTEP, node_name, buyers_sorted)
    registry.trades_by_transaction_key[transaction_key] = trade
    return buyer_entry, seller_entry, trade


def _run_exec_with_driver_patched(world, **exec_kwargs):
    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver([]),
    ):
        return world.exec_simulation(**exec_kwargs)


def test_exec_simulation_unobserved_finalize_order_before_termination_and_analysis():
    world = _plain_world("unobserved_hook_order", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    events = []
    original_unobserved_prepare = (
        prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_unobserved_commit = (
        commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation
    original_ex_post_commit = commit_tvt_mp_trade_ex_post_evaluation
    original_terminated = World.simulation_terminated
    original_analysis = Analyzer.basic_analysis

    def tracking_unobserved_prepare(current_world):
        events.append("unobserved_prepare")
        return original_unobserved_prepare(current_world)

    def tracking_unobserved_commit(prepared_update):
        events.append("unobserved_commit")
        return original_unobserved_commit(prepared_update)

    def tracking_ex_post_prepare(current_world):
        events.append("ex_post_prepare")
        return original_ex_post_prepare(current_world)

    def tracking_ex_post_commit(prepared_update):
        events.append("ex_post_commit")
        return original_ex_post_commit(prepared_update)

    def tracking_terminated(current_world):
        events.append("terminated")
        return original_terminated(current_world)

    def tracking_analysis(analyzer):
        events.append("analysis")
        return original_analysis(analyzer)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
        tracking_unobserved_prepare,
    ):
        with patch(
            "uxsim.order_control_tvt_mp_actual_passage.commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
            tracking_unobserved_commit,
        ):
            with patch(
                "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
                tracking_ex_post_prepare,
            ):
                with patch(
                    "uxsim.order_control_tvt_mp_actual_passage.commit_tvt_mp_trade_ex_post_evaluation",
                    tracking_ex_post_commit,
                ):
                    with patch.object(
                        World,
                        "simulation_terminated",
                        tracking_terminated,
                    ):
                        with patch.object(
                            Analyzer,
                            "basic_analysis",
                            tracking_analysis,
                        ):
                            _run_exec_with_driver_patched(world)
    assert events == [
        "unobserved_prepare",
        "unobserved_commit",
        "ex_post_prepare",
        "ex_post_commit",
        "terminated",
        "analysis",
    ]
    assert world.T == 10


def test_exec_simulation_unobserved_finalize_sets_waiting_entries_after_last_traffic():
    world = _plain_world("unobserved_hook_waiting", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    buyer_entry, seller_entry, trade = _register_hook_trade(
        world,
        observed_buyer=True,
    )
    buyer_record_before = buyer_entry.actual_passage_observation_record
    flag_before = trade.buyer_seller_actual_passage_completion_notified
    _run_exec_with_driver_patched(world)
    assert world.T == 10
    assert buyer_entry.actual_passage_observation_record is buyer_record_before
    assert (
        buyer_entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    assert (
        seller_entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    )
    assert seller_entry.actual_passage_observation_record is not None
    assert trade.buyer_seller_actual_passage_completion_notified is flag_before
    assert (
        world.order_control_tvt_mp_actual_passage_wait_registry.evaluation_end_unobserved_finalized_timestep
        == 9
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    assert registry.trade_ex_post_evaluation_finalized_timestep == 9
    assert len(registry.trade_ex_post_evaluation_results_by_transaction_key) == 1
    ex_post_result = next(
        iter(registry.trade_ex_post_evaluation_results_by_transaction_key.values())
    )
    assert (
        ex_post_result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    )


def test_exec_simulation_ex_post_prepare_reads_seller_after_unobserved_commit():
    world = _plain_world("ex_post_after_unobserved", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    _buyer_entry, seller_entry, _trade = _register_hook_trade(
        world,
        observed_buyer=True,
    )
    seller_status_at_ex_post_prepare = []
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation

    def tracking_ex_post_prepare(current_world):
        seller_status_at_ex_post_prepare.append(seller_entry.wait_status)
        return original_ex_post_prepare(current_world)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
        tracking_ex_post_prepare,
    ):
        _run_exec_with_driver_patched(world)
    assert seller_status_at_ex_post_prepare == [
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    ]


def test_simulation_terminated_does_not_call_trade_ex_post_hooks():
    source = inspect.getsource(World.simulation_terminated)
    assert "trade_ex_post" not in source
    assert "unobserved" not in source


def test_exec_simulation_unobserved_finalize_does_not_run_traffic_after_evaluation_end():
    world = _plain_world("unobserved_hook_no_traffic", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    link_timesteps = []
    original_update = Link.update

    def tracking_update(link):
        link_timesteps.append(link.W.T)
        return original_update(link)

    with patch.object(Link, "update", tracking_update):
        _run_exec_with_driver_patched(world)
    assert max(link_timesteps) == 9
    assert 10 not in link_timesteps
    assert world.T == 10


def test_exec_simulation_unobserved_finalize_not_called_on_mid_stop():
    world = _plain_world("unobserved_hook_mid_stop", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    unobserved_prepare_calls = []
    ex_post_prepare_calls = []
    original_unobserved_prepare = (
        prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation

    def tracking_unobserved_prepare(current_world):
        unobserved_prepare_calls.append(current_world.T)
        return original_unobserved_prepare(current_world)

    def tracking_ex_post_prepare(current_world):
        ex_post_prepare_calls.append(current_world.T)
        return original_ex_post_prepare(current_world)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
        tracking_unobserved_prepare,
    ):
        with patch(
            "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
            tracking_ex_post_prepare,
        ):
            code = _run_exec_with_driver_patched(world, duration_t2=5)
    assert code == 0
    assert world.T == 5
    assert unobserved_prepare_calls == []
    assert ex_post_prepare_calls == []


def test_exec_simulation_unobserved_finalize_runs_once_on_split_resume():
    world = _plain_world("unobserved_hook_split", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    unobserved_prepare_calls = []
    ex_post_prepare_calls = []
    original_unobserved_prepare = (
        prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation

    def tracking_unobserved_prepare(current_world):
        unobserved_prepare_calls.append(current_world.T)
        return original_unobserved_prepare(current_world)

    def tracking_ex_post_prepare(current_world):
        ex_post_prepare_calls.append(current_world.T)
        return original_ex_post_prepare(current_world)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
        tracking_unobserved_prepare,
    ):
        with patch(
            "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
            tracking_ex_post_prepare,
        ):
            first = _run_exec_with_driver_patched(world, duration_t2=5)
            second = _run_exec_with_driver_patched(world)
    assert first == 0
    assert second == 1
    assert unobserved_prepare_calls == [10]
    assert ex_post_prepare_calls == [10]


def test_exec_simulation_unobserved_finalize_not_called_on_rerun_after_finish():
    world = _plain_world("unobserved_hook_rerun", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    unobserved_prepare_calls = []
    ex_post_prepare_calls = []
    original_unobserved_prepare = (
        prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation

    def tracking_unobserved_prepare(current_world):
        unobserved_prepare_calls.append(current_world.T)
        return original_unobserved_prepare(current_world)

    def tracking_ex_post_prepare(current_world):
        ex_post_prepare_calls.append(current_world.T)
        return original_ex_post_prepare(current_world)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
        tracking_unobserved_prepare,
    ):
        with patch(
            "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
            tracking_ex_post_prepare,
        ):
            first = _run_exec_with_driver_patched(world)
            second = _run_exec_with_driver_patched(world)
    assert first == 1
    assert second == 1
    assert unobserved_prepare_calls == [10]
    assert ex_post_prepare_calls == [10]


def test_exec_simulation_unobserved_finalize_not_called_when_evaluation_end_is_none():
    world = _plain_world("unobserved_hook_none", 5)
    unobserved_prepare_calls = []
    ex_post_prepare_calls = []
    original_unobserved_prepare = (
        prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation

    def tracking_unobserved_prepare(current_world):
        unobserved_prepare_calls.append(current_world.T)
        return original_unobserved_prepare(current_world)

    def tracking_ex_post_prepare(current_world):
        ex_post_prepare_calls.append(current_world.T)
        return original_ex_post_prepare(current_world)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
        tracking_unobserved_prepare,
    ):
        with patch(
            "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
            tracking_ex_post_prepare,
        ):
            world.exec_simulation()
    assert unobserved_prepare_calls == []
    assert ex_post_prepare_calls == []


def test_exec_simulation_unobserved_finalize_on_tsize_equals_evaluation_end_plus_one():
    world = _plain_world("unobserved_hook_tsize_path", 10)
    world.order_control_tvt_evaluation_end_timestep = 9
    unobserved_prepare_calls = []
    ex_post_prepare_calls = []
    original_unobserved_prepare = (
        prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization
    )
    original_ex_post_prepare = prepare_tvt_mp_trade_ex_post_evaluation

    def tracking_unobserved_prepare(current_world):
        unobserved_prepare_calls.append(current_world.T)
        return original_unobserved_prepare(current_world)

    def tracking_ex_post_prepare(current_world):
        ex_post_prepare_calls.append(current_world.T)
        return original_ex_post_prepare(current_world)

    with patch(
        "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization",
        tracking_unobserved_prepare,
    ):
        with patch(
            "uxsim.order_control_tvt_mp_actual_passage.prepare_tvt_mp_trade_ex_post_evaluation",
            tracking_ex_post_prepare,
        ):
            code = _run_exec_with_driver_patched(world)
    assert code == 1
    assert world.T == world.TSIZE == 10
    assert unobserved_prepare_calls == [10]
    assert ex_post_prepare_calls == [10]
    assert (
        world.order_control_tvt_mp_actual_passage_wait_registry.evaluation_end_unobserved_finalized_timestep
        == 9
    )
    assert (
        world.order_control_tvt_mp_actual_passage_wait_registry.trade_ex_post_evaluation_finalized_timestep
        == 9
    )


def test_evaluation_end_timestep_initial_value_is_none():
    world = _plain_world("eval_end_initial", 10)
    assert world.order_control_tvt_evaluation_end_timestep is None


def test_none_does_not_auto_start_driver():
    world = _plain_world("eval_end_none_no_driver", 5)
    calls = []
    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver(calls),
    ):
        code = world.exec_simulation()
    assert calls == []
    assert code == 1
    assert world.T == world.TSIZE


def test_none_uses_ordinary_tsize_termination():
    world = _plain_world("eval_end_none_tsize", 5)
    termination_calls = []
    original = World.simulation_terminated

    def tracking(world):
        termination_calls.append(world.T)
        return original(world)

    with patch.object(World, "simulation_terminated", tracking):
        first = world.exec_simulation()
        second = world.exec_simulation()
    assert first == 1
    assert second == 1
    assert world.T == 5
    assert termination_calls == [5, 5]


def test_bool_evaluation_end_is_value_error():
    world = _plain_world("eval_end_bool", 10)
    world.finalize_scenario()
    world.order_control_tvt_evaluation_end_timestep = True
    error = _assert_raises(ValueError, world.exec_simulation)
    assert "order_control_tvt_evaluation_end_timestep" in str(error)
    assert world.T == 0


def test_negative_evaluation_end_is_value_error():
    world = _plain_world("eval_end_negative", 10)
    world.finalize_scenario()
    world.order_control_tvt_evaluation_end_timestep = -1
    error = _assert_raises(ValueError, world.exec_simulation)
    assert "order_control_tvt_evaluation_end_timestep" in str(error)


def test_evaluation_end_at_or_above_tsize_is_value_error():
    world = _plain_world("eval_end_tsize", 10)
    world.finalize_scenario()
    world.order_control_tvt_evaluation_end_timestep = world.TSIZE
    error = _assert_raises(ValueError, world.exec_simulation)
    assert "TSIZE" in str(error)
    world.order_control_tvt_evaluation_end_timestep = world.TSIZE + 1
    _assert_raises(ValueError, world.check_simulation_ongoing)


def test_invalid_evaluation_end_starts_neither_traffic_nor_driver():
    world = _plain_world("eval_end_invalid_quiet", 10)
    world.finalize_scenario()
    world.order_control_tvt_evaluation_end_timestep = True
    calls = []
    link_updates = []
    original_update = Link.update

    def tracking_update(link):
        link_updates.append(link.W.T)
        return original_update(link)

    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver(calls),
    ):
        with patch.object(Link, "update", tracking_update):
            _assert_raises(ValueError, world.exec_simulation)
    assert calls == []
    assert link_updates == []
    assert world.T == 0


def test_ten_timestep_evaluation_processes_through_final_timestep():
    world = _plain_world("eval_end_ten", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    calls = []
    termination_calls = []
    analysis_calls = []
    original_terminated = World.simulation_terminated
    original_analysis = Analyzer.basic_analysis

    def tracking_terminated(world):
        termination_calls.append(world.T)
        return original_terminated(world)

    def tracking_analysis(analyzer):
        analysis_calls.append(analyzer.W.T)
        return original_analysis(analyzer)

    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver(calls),
    ):
        with patch.object(World, "simulation_terminated", tracking_terminated):
            with patch.object(Analyzer, "basic_analysis", tracking_analysis):
                code = world.exec_simulation()
                rerun = world.exec_simulation()
    assert calls == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert world.T == 10
    assert code == 1
    assert rerun == 1
    assert world.T == 10
    assert termination_calls == [10]
    assert analysis_calls == [10]
    assert world.check_simulation_ongoing() is False


def test_until_t_past_evaluation_end_is_clamped():
    world = _plain_world("eval_end_until_clamp", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    calls = []
    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver(calls),
    ):
        code = world.exec_simulation(until_t=100)
    assert code == 1
    assert world.T == 10
    assert calls[-1] == 9


def test_check_ongoing_true_on_final_evaluation_timestep():
    world = _plain_world("eval_end_ongoing_true", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    calls = []
    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver(calls),
    ):
        code = world.exec_simulation(duration_t2=9)
    assert code == 0
    assert world.T == 9
    assert world.check_simulation_ongoing() is True
    assert 9 not in calls


def test_mid_stop_does_not_terminate_and_can_resume():
    world = _plain_world("eval_end_resume", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    termination_calls = []
    original = World.simulation_terminated

    def tracking(world):
        termination_calls.append(world.T)
        return original(world)

    with patch.object(World, "simulation_terminated", tracking):
        with patch(
            "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
            _recording_driver([]),
        ):
            first = world.exec_simulation(duration_t2=5)
            assert first == 0
            assert world.T == 5
            assert termination_calls == []
            assert world.check_simulation_ongoing() is True
            second = world.exec_simulation()
    assert second == 1
    assert world.T == 10
    assert termination_calls == [10]


def test_driver_called_once_per_timestep_for_several_nodes():
    world = _plain_world("eval_end_several_nodes", 40)
    _add_tvt_node(world, "junction_a", 0)
    _add_tvt_node(world, "junction_b", 2)
    world.order_control_tvt_evaluation_end_timestep = 9
    calls = []
    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        _recording_driver(calls),
    ):
        world.exec_simulation(duration_t2=3)
    assert calls == [0, 1, 2]


def test_driver_runs_before_link_update_and_node_transfer():
    world = _plain_world("eval_end_order", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    events = []
    original_update = Link.update
    original_transfer = Node.transfer

    def fake_driver(world):
        events.append(("driver", world.T))
        return OrderControlTvtMpDriverResult(atomic_apply_set_result=None)

    def tracking_update(link):
        events.append(("link", link.W.T))
        return original_update(link)

    def tracking_transfer(node):
        events.append(("transfer", node.W.T))
        return original_transfer(node)

    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        fake_driver,
    ):
        with patch.object(Link, "update", tracking_update):
            with patch.object(Node, "transfer", tracking_transfer):
                world.exec_simulation(duration_t2=1)
    driver_at = events.index(("driver", 0))
    link_at = events.index(("link", 0))
    transfer_at = events.index(("transfer", 0))
    assert driver_at < link_at
    assert driver_at < transfer_at


def test_driver_exception_skips_traffic_and_propagates():
    world = _plain_world("eval_end_driver_error", 40)
    world.order_control_tvt_evaluation_end_timestep = 9
    link_updates = []
    original_update = Link.update

    def boom(world):
        raise RuntimeError("tvt driver failed")

    def tracking_update(link):
        link_updates.append(link.W.T)
        return original_update(link)

    with patch(
        "uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver",
        boom,
    ):
        with patch.object(Link, "update", tracking_update):
            error = _assert_raises(RuntimeError, world.exec_simulation)
    assert str(error) == "tvt driver failed"
    assert link_updates == []


def test_zero_target_nodes_do_not_require_margin_but_still_stop():
    world = _plain_world("eval_end_zero_nodes", 10)
    world.order_control_tvt_baseline_horizon_steps = 50
    world.order_control_tvt_evaluation_end_timestep = 9
    code = world.exec_simulation()
    assert code == 1
    assert world.T == 10
    assert world.order_control_tvt_driver_started_timestep is None
    assert world.check_simulation_ongoing() is False


def test_margin_one_below_minimum_is_value_error_before_start():
    world = _plain_world("eval_end_margin_short", 39)
    _add_tvt_node(world, "junction", 0)
    world.finalize_scenario()
    world.order_control_tvt_baseline_horizon_steps = 30
    world.order_control_tvt_max_candidate_visit_count = 1
    world.order_control_tvt_evaluation_end_timestep = 9
    world.T = 9
    error = _assert_raises(ValueError, lambda: run_tvt_mp_driver(world))
    assert "required_steps=31" in str(error)
    assert "baseline_horizon_steps=30" in str(error)
    assert world.order_control_tvt_driver_started_timestep is None


def test_exact_margin_allows_driver_and_is_independent_of_window_six():
    world = _plain_world("eval_end_margin_exact", 40)
    _add_tvt_node(world, "junction", 0)
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
    world.finalize_scenario()
    world.order_control_tvt_baseline_horizon_steps = 30
    world.order_control_tvt_max_candidate_visit_count = 1
    world.order_control_tvt_evaluation_end_timestep = 9
    world.T = 9
    result = run_tvt_mp_driver(world)
    assert result.atomic_apply_set_result is not None
    assert world.order_control_tvt_driver_started_timestep == 9
    assert world.order_control_tvt_baseline_horizon_steps == 30


def test_fork_clears_evaluation_end_and_runs_full_horizon():
    world = _build_time_value_junction_world(
        name="eval_end_fork_horizon",
        tmax=300,
    )
    world.order_control_tvt_baseline_horizon_steps = 50
    vehicle = world.addVehicle("orig", "dest", 0, name="fork_vehicle")
    _advance_until_on_inlink(vehicle, "in")
    _place_arrived_vehicle_at_snapshot(
        world,
        vehicle,
        inlink_name="in",
        target_node_name="junction",
        outlink_name="out",
        arrival_timestep=5,
        snapshot_timestep=9,
    )
    world.order_control_tvt_evaluation_end_timestep = 9
    copied = []
    original_copy = World.copy
    termination_calls = []
    analysis_calls = []
    original_terminated = World.simulation_terminated
    original_analysis = Analyzer.basic_analysis

    def capture_copy(world):
        fork = original_copy(world)
        copied.append(fork)
        return fork

    def tracking_terminated(world):
        termination_calls.append(world.T)
        return original_terminated(world)

    def tracking_analysis(analyzer):
        analysis_calls.append(1)
        return original_analysis(analyzer)

    with patch.object(World, "copy", capture_copy):
        with patch.object(World, "simulation_terminated", tracking_terminated):
            with patch.object(Analyzer, "basic_analysis", tracking_analysis):
                result = run_snapshot_fixed_baseline_fork(
                    world,
                    target_node_names=["junction"],
                    baseline_horizon_steps=50,
                )
    assert world.order_control_tvt_evaluation_end_timestep == 9
    assert len(copied) == 1
    assert copied[0].order_control_tvt_evaluation_end_timestep is None
    assert result.fork_steps_executed == 50
    assert result.final_fork_timestep == 59
    assert result.final_fork_timestep > 9
    assert termination_calls == []
    assert analysis_calls == []


def test_zero_visits_still_skip_forward_after_fork_release():
    world = _build_time_value_junction_world(
        name="eval_end_fork_zero_visits",
        tmax=300,
    )
    world.T = 9
    world.order_control_tvt_evaluation_end_timestep = 9
    copied = []
    original_copy = World.copy

    def capture_copy(world):
        fork = original_copy(world)
        copied.append(fork)
        return fork

    with patch.object(World, "copy", capture_copy):
        result = run_snapshot_fixed_baseline_fork(
            world,
            target_node_names=["junction"],
            baseline_horizon_steps=50,
        )
    assert result.fork_steps_executed == 0
    assert result.final_fork_timestep == 9
    assert copied[0].order_control_tvt_evaluation_end_timestep is None
    assert world.order_control_tvt_evaluation_end_timestep == 9


def test_completed_and_incomplete_vehicles_keep_existing_basic_counts():
    world = _plain_world("eval_end_trips", 40)
    early = world.addVehicle("orig", "dest", 0, name="early")
    late = world.addVehicle("orig", "dest", 9, name="late")
    world.order_control_tvt_evaluation_end_timestep = 9
    world.exec_simulation()
    assert world.T == 10
    assert early.travel_time != -1
    assert early.state == "end"
    assert late.travel_time == -1
    assert late.state != "end"
    assert world.analyzer.trip_completed == 1
    assert world.analyzer.trip_all == 2


def test_node_transfer_does_not_use_tvt_rank():
    source = inspect.getsource(Node.transfer)
    assert "run_tvt_mp_driver" not in source
    assert "time_value" in source
    assert "transfer_tvt_mp_passage_attempts" in source


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
