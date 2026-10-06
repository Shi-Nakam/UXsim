"""Contract tests for TVT-MP nonparticipating external effects (observation record fields)."""

import dataclasses
import inspect

import pytest

import uxsim.order_control_tvt_mp_actual_passage as actual_passage_module
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageCommonFrozenInput,
    OrderControlTvtMpActualPassageMonetaryFrozenInput,
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitRegistry,
    OrderControlTvtMpActualPassageWaitStatus,
    OrderControlTvtMpActualNodePassageRecord,
    OrderControlTvtMpTradeExPostEvaluationStatus,
    commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization,
    prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization,
    prepare_tvt_mp_trade_ex_post_evaluation,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRouteOrigin,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.uxsim import World

_ROUTE_ORIGIN = OrderControlTvtMpLocalBindingRouteOrigin.RANK_LEDGER_FORMAL_ROUTE
_DELTAT_SECONDS = 60
_TEST_TRUE_VOT = 0.5
_NODE_NAME = "node_a"
_PREPARE_DECISION_TIMESTEP = 10
_PREPARE_ACTUAL_TIMESTEP = 12
_PREPARE_BASELINE = 10
_PREPARE_CANDIDATE = 8
_COPIED_BASELINE_MINUS_CANDIDATE = (41, 42, 43)
_EVALUATION_END_TIMESTEP = 9
_EVALUATION_END_WORLD_T = 10
_EVALUATION_END_TSIZE = 40

_PASSAGE_TRIPLE_FIELD_NAMES = (
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_candidate_passage_seconds",
    "baseline_minus_candidate_time_value",
    "baseline_minus_actual_passage_timesteps",
    "baseline_minus_actual_passage_seconds",
    "baseline_minus_actual_time_value",
    "candidate_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_seconds",
    "candidate_minus_actual_time_value",
)


def _visit_key(vehicle_name: str, visit_index: int = 1) -> OrderControlTvtVisitKey:
    return (vehicle_name, visit_index)


def _common_frozen():
    return OrderControlTvtMpActualPassageCommonFrozenInput(
        baseline_local_rank=2,
        post_trade_local_rank=1,
        rank_change=1,
        route_origin=_ROUTE_ORIGIN,
    )


def _monetary_frozen(*, declared_vot_per_second=1.0):
    return OrderControlTvtMpActualPassageMonetaryFrozenInput(
        declared_vot_per_second=declared_vot_per_second,
        payment_paid_in_this_transaction=3.0,
        payment_received_in_this_transaction=0,
    )


def _frozen_fields(role, **monetary_changes):
    if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        return {
            "common_frozen_input": _common_frozen(),
            "monetary_frozen_input": None,
        }
    return {
        "common_frozen_input": _common_frozen(),
        "monetary_frozen_input": _monetary_frozen(**monetary_changes),
    }


def _evaluation_end_world():
    world = World(
        name="np_external_effect",
        deltan=1,
        tmax=_EVALUATION_END_TSIZE,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=0,
    )
    world.finalize_scenario()
    world.order_control_tvt_evaluation_end_timestep = _EVALUATION_END_TIMESTEP
    world.T = _EVALUATION_END_WORLD_T
    return world


def _register_formal_trade_wait(
    world,
    *,
    buyer_visit_keys,
    seller_visit_keys,
    nonparticipating_visit_keys=(),
    buyers_sorted=None,
):
    if buyers_sorted is None:
        buyers_sorted = (_visit_key("buyer_a"),)
    all_visit_keys = tuple(
        list(buyer_visit_keys)
        + list(seller_visit_keys)
        + list(nonparticipating_visit_keys)
    )
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=_PREPARE_DECISION_TIMESTEP,
        node_name=_NODE_NAME,
        buyers_sorted=buyers_sorted,
        all_visit_keys=all_visit_keys,
        buyer_visit_keys=buyer_visit_keys,
        seller_visit_keys=seller_visit_keys,
        nonparticipating_visit_keys=nonparticipating_visit_keys,
    )
    transaction_key = (_PREPARE_DECISION_TIMESTEP, _NODE_NAME, buyers_sorted)
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.trades_by_transaction_key[transaction_key] = trade
    return trade, transaction_key


def _append_node_passage_history(world, visit_key, rank):
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    record = OrderControlTvtMpActualNodePassageRecord(
        visit_key=visit_key,
        actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
        actual_route_next_link_name="link_actual",
        actual_node_passage_rank=rank,
    )
    existing = registry.records_by_node_name.get(_NODE_NAME, ())
    registry.records_by_node_name[_NODE_NAME] = existing + (record,)


def _observation_record(
    visit_key,
    role,
    *,
    buyers_sorted,
    predicted_status=OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED,
    candidate_timestep=_PREPARE_CANDIDATE,
    baseline_minus_candidate=(2, 120.0, 60.0),
    observation_status=OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED,
    actual_timestep=_PREPARE_ACTUAL_TIMESTEP,
    actual_route="link_actual",
    baseline_minus_actual=(3, 180.0, 90.0),
    candidate_minus_actual=(1, 60.0, 30.0),
    true_vot=_TEST_TRUE_VOT,
    predicted_route="link_pred",
):
    bmc_t, bmc_s, bmc_v = baseline_minus_candidate
    bma_t, bma_s, bma_v = baseline_minus_actual
    cma_t, cma_s, cma_v = candidate_minus_actual
    if predicted_status is (
        OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON
    ):
        candidate_timestep = None
        bmc_t, bmc_s, bmc_v = None, None, None
        cma_t, cma_s, cma_v = None, None, None
    if observation_status is (
        OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
    ):
        actual_timestep = None
        actual_route = None
        bma_t, bma_s, bma_v = None, None, None
        cma_t, cma_s, cma_v = None, None, None
    return OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=_PREPARE_DECISION_TIMESTEP,
        node_name=_NODE_NAME,
        buyers_sorted=buyers_sorted,
        visit_key=visit_key,
        vehicle_name=visit_key[0],
        role=role,
        observation_status=observation_status,
        baseline_passage_timestep=_PREPARE_BASELINE,
        candidate_passage_timestep=candidate_timestep,
        true_vot_per_second=true_vot,
        predicted_observation_status=predicted_status,
        predicted_route_next_link_name=predicted_route,
        baseline_minus_candidate_passage_timesteps=bmc_t,
        baseline_minus_candidate_passage_seconds=bmc_s,
        baseline_minus_candidate_time_value=bmc_v,
        baseline_minus_actual_passage_timesteps=bma_t,
        baseline_minus_actual_passage_seconds=bma_s,
        baseline_minus_actual_time_value=bma_v,
        candidate_minus_actual_passage_timesteps=cma_t,
        candidate_minus_actual_passage_seconds=cma_s,
        candidate_minus_actual_time_value=cma_v,
        actual_passage_timestep=actual_timestep,
        actual_route_next_link_name=actual_route,
    )


def _register_wait_entry(
    world,
    *,
    visit_key,
    role,
    buyers_sorted,
    observation_record=None,
    wait_status=None,
    candidate_timestep=_PREPARE_CANDIDATE,
    predicted_status=OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED,
):
    if wait_status is None:
        if observation_record is None:
            wait_status = (
                OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
            )
        else:
            wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=_PREPARE_DECISION_TIMESTEP,
        node_name=_NODE_NAME,
        buyers_sorted=buyers_sorted,
        visit_key=visit_key,
        vehicle_name=visit_key[0],
        role=role,
        wait_status=wait_status,
        baseline_passage_timestep=_PREPARE_BASELINE,
        candidate_passage_timestep=candidate_timestep,
        true_vot_per_second=_TEST_TRUE_VOT,
        baseline_minus_candidate_passage_timesteps=_COPIED_BASELINE_MINUS_CANDIDATE[0],
        baseline_minus_candidate_passage_seconds=_COPIED_BASELINE_MINUS_CANDIDATE[1],
        baseline_minus_candidate_time_value=_COPIED_BASELINE_MINUS_CANDIDATE[2],
        predicted_observation_status=predicted_status,
        predicted_route_next_link_name="link_pred",
        actual_passage_observation_record=observation_record,
        **_frozen_fields(role),
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.entries_by_node_name_and_visit_key[(_NODE_NAME, visit_key)] = entry
    return entry


def _make_trade_world(role_specs, *, finalize_unobserved=True):
    world = _evaluation_end_world()
    buyer_names = [
        spec["vehicle_name"]
        for spec in role_specs
        if spec["role"] is OrderControlTvtMpActualPassageRole.BUYER
    ]
    buyers_sorted = tuple(_visit_key(name) for name in buyer_names)
    buyer_keys = []
    seller_keys = []
    nonpart_keys = []
    entries = {}
    history_rank = 1
    for spec in role_specs:
        role = spec["role"]
        vehicle_name = spec["vehicle_name"]
        visit_key = _visit_key(vehicle_name)
        observed = spec.get("observed", True)
        seconds = spec.get("baseline_minus_actual_passage_seconds", 120)
        if observed:
            observation_record = _observation_record(
                visit_key,
                role,
                buyers_sorted=buyers_sorted,
                baseline_minus_actual=(
                    seconds // _DELTAT_SECONDS,
                    float(seconds),
                    float(seconds) * _TEST_TRUE_VOT,
                ),
                candidate_minus_actual=(
                    (seconds - 120) // _DELTAT_SECONDS,
                    float(seconds - 120),
                    float(seconds - 120) * _TEST_TRUE_VOT,
                ),
            )
            _append_node_passage_history(world, visit_key, history_rank)
            history_rank = history_rank + 1
        else:
            observation_record = None
        entry = _register_wait_entry(
            world,
            visit_key=visit_key,
            role=role,
            buyers_sorted=buyers_sorted,
            observation_record=observation_record,
        )
        entries[visit_key] = entry
        if role is OrderControlTvtMpActualPassageRole.BUYER:
            buyer_keys.append(visit_key)
        elif role is OrderControlTvtMpActualPassageRole.SELLER:
            seller_keys.append(visit_key)
        else:
            nonpart_keys.append(visit_key)
    trade, transaction_key = _register_formal_trade_wait(
        world,
        buyer_visit_keys=tuple(buyer_keys),
        seller_visit_keys=tuple(seller_keys),
        nonparticipating_visit_keys=tuple(nonpart_keys),
        buyers_sorted=buyers_sorted,
    )
    if finalize_unobserved:
        prepared = prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization(
            world,
        )
        commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization(prepared)
    return world, trade, transaction_key, entries


def _np_records_in_trade_order(trade, entries):
    records = []
    for visit_key in trade.nonparticipating_visit_keys:
        entry = entries[visit_key]
        assert entry.role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING
        records.append(entry.actual_passage_observation_record)
    return records


# --- target set ---


def test_trade_wait_allows_zero_nonparticipating_visit_keys():
    world = _evaluation_end_world()
    trade, _key = _register_formal_trade_wait(
        world,
        buyer_visit_keys=(_visit_key("buyer_a"),),
        seller_visit_keys=(_visit_key("seller_a"),),
        nonparticipating_visit_keys=(),
    )
    assert trade.nonparticipating_visit_keys == ()


def test_trade_wait_preserves_multiple_nonparticipating_keys_in_order():
    keys = (_visit_key("w1"), _visit_key("w2"), _visit_key("w3"))
    world = _evaluation_end_world()
    trade, _key = _register_formal_trade_wait(
        world,
        buyer_visit_keys=(_visit_key("buyer_a"),),
        seller_visit_keys=(_visit_key("seller_a"),),
        nonparticipating_visit_keys=keys,
    )
    assert trade.nonparticipating_visit_keys == keys


def test_buyer_and_seller_keys_are_not_listed_as_nonparticipating():
    buyer_key = _visit_key("buyer_a")
    seller_key = _visit_key("seller_a")
    np_key = _visit_key("watcher_a")
    world = _evaluation_end_world()
    trade, _key = _register_formal_trade_wait(
        world,
        buyer_visit_keys=(buyer_key,),
        seller_visit_keys=(seller_key,),
        nonparticipating_visit_keys=(np_key,),
    )
    assert buyer_key not in trade.nonparticipating_visit_keys
    assert seller_key not in trade.nonparticipating_visit_keys
    assert np_key in trade.nonparticipating_visit_keys


def test_orphan_nonparticipating_entry_not_in_trade_target_set():
    buyers_sorted = (_visit_key("buyer_a"),)
    selected_np = _visit_key("selected_watcher")
    orphan_np = _visit_key("orphan_watcher")
    world = _evaluation_end_world()
    _register_wait_entry(
        world,
        visit_key=orphan_np,
        role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=buyers_sorted,
    )
    trade, _key = _register_formal_trade_wait(
        world,
        buyer_visit_keys=(buyers_sorted[0],),
        seller_visit_keys=(_visit_key("seller_a"),),
        nonparticipating_visit_keys=(selected_np,),
        buyers_sorted=buyers_sorted,
    )
    target_keys = set(trade.nonparticipating_visit_keys)
    assert orphan_np not in target_keys
    assert selected_np in target_keys


# --- canonical observation record ---


def test_observation_record_exposes_nine_passage_difference_fields():
    names = {field.name for field in dataclasses.fields(
        OrderControlTvtMpActualPassageObservationRecord
    )}
    for name in _PASSAGE_TRIPLE_FIELD_NAMES:
        assert name in names


def test_observation_record_has_no_ambiguous_prediction_error_field():
    names = {field.name for field in dataclasses.fields(
        OrderControlTvtMpActualPassageObservationRecord
    )}
    for forbidden in (
        "prediction_error",
        "predicted_external_effect",
        "actual_external_effect",
        "predicted_minus_actual_external_effect",
    ):
        assert forbidden not in names


def test_wait_entry_holds_observation_record_reference_and_copied_candidate_values():
    visit_key = _visit_key("watcher")
    buyers_sorted = (_visit_key("buyer_a"),)
    record = _observation_record(visit_key, OrderControlTvtMpActualPassageRole.NONPARTICIPATING, buyers_sorted=buyers_sorted)
    world = _evaluation_end_world()
    entry = _register_wait_entry(
        world,
        visit_key=visit_key,
        role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=buyers_sorted,
        observation_record=record,
    )
    assert entry.actual_passage_observation_record is record
    assert entry.baseline_minus_candidate_passage_timesteps == 41


# --- predicted external effect ---


@pytest.mark.parametrize(
    "bmc_seconds,expected_value",
    [(120.0, 60.0), (0.0, 0.0), (-60.0, -30.0)],
)
def test_predicted_external_effect_signs_when_candidate_observed(bmc_seconds, expected_value):
    timesteps = int(bmc_seconds // _DELTAT_SECONDS)
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        baseline_minus_candidate=(timesteps, bmc_seconds, expected_value),
    )
    assert record.baseline_minus_candidate_passage_seconds == bmc_seconds
    assert record.baseline_minus_candidate_time_value == expected_value


def test_predicted_external_effect_zero_true_vot_yields_zero_amount_with_nonzero_seconds():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        true_vot=0.0,
        baseline_minus_candidate=(2, 120.0, 0.0),
    )
    assert record.baseline_minus_candidate_passage_seconds == 120.0
    assert record.baseline_minus_candidate_time_value == 0.0


def test_unobserved_at_horizon_makes_candidate_and_baseline_minus_candidate_none():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_status=OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON,
    )
    assert record.candidate_passage_timestep is None
    assert record.baseline_minus_candidate_passage_timesteps is None
    assert record.baseline_minus_candidate_passage_seconds is None
    assert record.baseline_minus_candidate_time_value is None
    assert record.candidate_minus_actual_passage_timesteps is None


def test_candidate_unpredictable_is_not_zero_predicted_effect():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_status=OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON,
        baseline_minus_actual=(3, 180.0, 90.0),
        candidate_minus_actual=(1, 60.0, 30.0),
    )
    assert record.baseline_minus_candidate_time_value is None
    assert record.baseline_minus_candidate_time_value != 0


# --- actual external effect ---


@pytest.mark.parametrize(
    "bma_seconds,expected_value",
    [(180.0, 90.0), (0.0, 0.0), (-120.0, -60.0)],
)
def test_actual_external_effect_signs_when_observed(bma_seconds, expected_value):
    timesteps = int(bma_seconds // _DELTAT_SECONDS)
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        baseline_minus_actual=(timesteps, bma_seconds, expected_value),
    )
    assert record.baseline_minus_actual_passage_seconds == bma_seconds
    assert record.baseline_minus_actual_time_value == expected_value


def test_actual_external_effect_zero_true_vot_is_numeric_zero_not_none():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        true_vot=0.0,
        baseline_minus_actual=(3, 180.0, 0.0),
    )
    assert record.baseline_minus_actual_time_value == 0.0
    assert record.baseline_minus_actual_time_value is not None


def test_actual_unobserved_at_evaluation_end_clears_actual_triple_and_route():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
        ),
    )
    assert record.actual_passage_timestep is None
    assert record.actual_route_next_link_name is None
    assert record.baseline_minus_actual_passage_timesteps is None
    assert record.baseline_minus_actual_passage_seconds is None
    assert record.baseline_minus_actual_time_value is None


def test_actual_unobserved_is_not_zero_external_effect():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
        ),
    )
    assert record.baseline_minus_actual_time_value is None
    assert record.baseline_minus_actual_time_value != 0


# --- candidate minus actual ---


def test_candidate_minus_actual_definition_when_both_timesteps_known():
    baseline = 10
    candidate = 8
    actual = 7
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        candidate_timestep=candidate,
        actual_timestep=actual,
        baseline_minus_candidate=(baseline - candidate, 120.0, 60.0),
        baseline_minus_actual=(baseline - actual, 180.0, 90.0),
        candidate_minus_actual=(candidate - actual, 60.0, 30.0),
    )
    assert (
        record.candidate_minus_actual_passage_timesteps
        == record.candidate_passage_timestep - record.actual_passage_timestep
    )


@pytest.mark.parametrize("delta_seconds", [60.0, 0.0, -60.0])
def test_candidate_minus_actual_signs(delta_seconds):
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        candidate_minus_actual=(
            int(delta_seconds // _DELTAT_SECONDS),
            delta_seconds,
            delta_seconds * _TEST_TRUE_VOT,
        ),
    )
    assert record.candidate_minus_actual_passage_seconds == delta_seconds


def test_candidate_minus_actual_none_when_candidate_unpredictable():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_status=OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON,
        baseline_minus_actual=(3, 180.0, 90.0),
    )
    assert record.candidate_minus_actual_passage_timesteps is None


def test_candidate_minus_actual_none_when_actual_unobserved():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END
        ),
    )
    assert record.candidate_minus_actual_passage_seconds is None


# --- route ---


def test_predicted_and_actual_routes_are_separate_fields():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_route="pred_link",
        actual_route="actual_link",
    )
    assert record.predicted_route_next_link_name == "pred_link"
    assert record.actual_route_next_link_name == "actual_link"


def test_route_match_and_mismatch_are_distinguishable():
    matched = _observation_record(
        _visit_key("w1"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_route="same",
        actual_route="same",
    )
    mismatched = _observation_record(
        _visit_key("w2"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_route="pred",
        actual_route="actual",
    )
    assert (
        matched.predicted_route_next_link_name
        == matched.actual_route_next_link_name
    )
    assert (
        mismatched.predicted_route_next_link_name
        != mismatched.actual_route_next_link_name
    )


def test_time_value_fields_do_not_embed_route_difference():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        predicted_route="pred",
        actual_route="different",
        baseline_minus_actual=(3, 180.0, 90.0),
    )
    assert record.baseline_minus_actual_time_value == 90.0


# --- nonparticipating entry inputs ---


def test_nonparticipating_wait_entry_rejects_monetary_frozen_input():
    visit_key = _visit_key("w")
    with pytest.raises(RuntimeError, match="must not carry"):
        OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=1,
            node_name="n",
            buyers_sorted=(_visit_key("b"),),
            visit_key=visit_key,
            vehicle_name=visit_key[0],
            role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
            baseline_passage_timestep=1,
            candidate_passage_timestep=1,
            true_vot_per_second=_TEST_TRUE_VOT,
            baseline_minus_candidate_passage_timesteps=None,
            baseline_minus_candidate_passage_seconds=None,
            baseline_minus_candidate_time_value=None,
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="link",
            common_frozen_input=_common_frozen(),
            monetary_frozen_input=_monetary_frozen(),
        )


def test_nonparticipating_observation_record_uses_true_vot_not_declared():
    record = _observation_record(
        _visit_key("w"),
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        buyers_sorted=(_visit_key("b"),),
        true_vot=_TEST_TRUE_VOT,
    )
    assert record.true_vot_per_second == _TEST_TRUE_VOT
    monetary_fields = {
        field.name
        for field in dataclasses.fields(OrderControlTvtMpActualPassageObservationRecord)
        if "declared" in field.name or "payment" in field.name or "compensation" in field.name
    }
    assert monetary_fields == set()


# --- trade ex-post status independence ---


def test_trade_ex_post_feasible_when_only_nonparticipating_unobserved():
    world, trade, transaction_key, entries = _make_trade_world(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": True,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": True,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_a",
                "observed": False,
            },
        ]
    )
    prepared = prepare_tvt_mp_trade_ex_post_evaluation(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )
    np_entry = entries[trade.nonparticipating_visit_keys[0]]
    np_record = np_entry.actual_passage_observation_record
    assert np_record.baseline_minus_actual_time_value is None
    assert np_record.baseline_minus_candidate_time_value == 43


def test_trade_ex_post_unavailable_does_not_clear_observed_nonparticipating_record():
    world, trade, transaction_key, entries = _make_trade_world(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": False,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": True,
                "baseline_minus_actual_passage_seconds": -120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_a",
                "observed": True,
                "baseline_minus_actual_passage_seconds": 180,
            },
        ]
    )
    prepared = prepare_tvt_mp_trade_ex_post_evaluation(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    )
    np_record = entries[trade.nonparticipating_visit_keys[0]].actual_passage_observation_record
    assert np_record.baseline_minus_actual_time_value == 90.0
    assert "ex_post" not in {
        field.name for field in dataclasses.fields(
            OrderControlTvtMpActualPassageObservationRecord
        )
    }


def test_ex_post_infeasible_keeps_nonparticipating_external_effect_values():
    world, trade, transaction_key, entries = _make_trade_world(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_a",
                "baseline_minus_actual_passage_seconds": 180,
            },
        ],
        finalize_unobserved=True,
    )
    prepared = prepare_tvt_mp_trade_ex_post_evaluation(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    )
    np_record = entries[trade.nonparticipating_visit_keys[0]].actual_passage_observation_record
    assert np_record.baseline_minus_actual_time_value == 90.0


def test_ex_post_feasible_keeps_nonparticipating_external_effect_values():
    world, trade, transaction_key, entries = _make_trade_world(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_a",
                "baseline_minus_actual_passage_seconds": 60,
            },
        ],
        finalize_unobserved=True,
    )
    prepared = prepare_tvt_mp_trade_ex_post_evaluation(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )
    np_record = entries[trade.nonparticipating_visit_keys[0]].actual_passage_observation_record
    assert np_record.baseline_minus_actual_time_value == 30.0


# --- absence of new APIs / fields ---


def test_module_has_no_nonparticipating_external_effect_result_type():
    forbidden_names = (
        "OrderControlTvtMpNonparticipatingExternalEffectResult",
        "OrderControlTvtMpExternalEffectEvaluationResult",
        "OrderControlTvtMpExternalEffectEvaluationStatus",
        "OrderControlTvtMpExternalEffectEvaluationReason",
    )
    for name in forbidden_names:
        assert not hasattr(actual_passage_module, name)


def test_module_has_no_external_effect_prepare_or_commit_apis():
    source = inspect.getsource(actual_passage_module)
    for fragment in (
        "prepare_tvt_mp_nonparticipating_external_effect",
        "commit_tvt_mp_nonparticipating_external_effect",
        "prepare_tvt_mp_external_effect",
        "commit_tvt_mp_external_effect",
    ):
        assert fragment not in source


def test_registry_and_trade_wait_have_no_external_effect_registry_fields():
    for cls in (
        OrderControlTvtMpActualPassageWaitRegistry,
        OrderControlTvtMpActualPassageTradeWait,
        OrderControlTvtMpActualPassageWaitEntry,
    ):
        for field in dataclasses.fields(cls):
            lowered = field.name.lower()
            assert "external_effect" not in lowered


def test_aggregation_reads_nonparticipating_visit_keys_in_order():
    world, trade, _transaction_key, entries = _make_trade_world(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_first",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_second",
            },
        ],
        finalize_unobserved=False,
    )
    records = _np_records_in_trade_order(trade, entries)
    assert len(records) == 2
    assert records[0].vehicle_name == "watcher_first"
    assert records[1].vehicle_name == "watcher_second"
    assert all(record.role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING for record in records)
