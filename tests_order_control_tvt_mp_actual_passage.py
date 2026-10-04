import dataclasses
import inspect

import pytest

from tests_order_control_tvt_mp_physical_transfer import (
    _as_fork,
    _confirm,
    _junction,
    _place,
    _register_only,
    _world,
)
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualNodePassageHistoryRegistry,
    OrderControlTvtMpActualNodePassageRecord,
    OrderControlTvtMpActualPassageCommonFrozenInput,
    OrderControlTvtMpActualPassageMonetaryFrozenInput,
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitRegistry,
    OrderControlTvtMpActualPassageWaitStatus,
    _PreparedTvtMpActualNodePassageHistoryUpdate,
    commit_tvt_mp_actual_node_passage_history,
    commit_tvt_mp_actual_passage_observation,
    prepare_tvt_mp_actual_node_passage_history,
    prepare_tvt_mp_actual_passage_observation,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRouteOrigin,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)
from uxsim.uxsim import World

_ROUTE_ORIGIN = OrderControlTvtMpLocalBindingRouteOrigin.RANK_LEDGER_FORMAL_ROUTE
_TEST_DELTAT_SECONDS = 60
_TEST_TRUE_VOT_PER_SECOND = 0.5
_TEST_BASELINE_PASSAGE_TIMESTEP = 10
_TEST_CANDIDATE_PASSAGE_TIMESTEP = 8
_TEST_ACTUAL_PASSAGE_TIMESTEP_OBSERVED = 7

_BASELINE_MINUS_CANDIDATE_PASSAGE_TIMESTEPS = (
    _TEST_BASELINE_PASSAGE_TIMESTEP - _TEST_CANDIDATE_PASSAGE_TIMESTEP
)
_BASELINE_MINUS_CANDIDATE_PASSAGE_SECONDS = (
    _BASELINE_MINUS_CANDIDATE_PASSAGE_TIMESTEPS * _TEST_DELTAT_SECONDS
)
_BASELINE_MINUS_CANDIDATE_TIME_VALUE = (
    _BASELINE_MINUS_CANDIDATE_PASSAGE_SECONDS * _TEST_TRUE_VOT_PER_SECOND
)

_BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS = (
    _TEST_BASELINE_PASSAGE_TIMESTEP - _TEST_ACTUAL_PASSAGE_TIMESTEP_OBSERVED
)
_BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS = (
    _BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS * _TEST_DELTAT_SECONDS
)
_BASELINE_MINUS_ACTUAL_TIME_VALUE = (
    _BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS * _TEST_TRUE_VOT_PER_SECOND
)

_CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS = (
    _TEST_CANDIDATE_PASSAGE_TIMESTEP - _TEST_ACTUAL_PASSAGE_TIMESTEP_OBSERVED
)
_CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS = (
    _CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS * _TEST_DELTAT_SECONDS
)
_CANDIDATE_MINUS_ACTUAL_TIME_VALUE = (
    _CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS * _TEST_TRUE_VOT_PER_SECOND
)

_TEST_ACTUAL_PASSAGE_TIMESTEP_FROZEN = 1

_FROZEN_BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS = (
    _TEST_BASELINE_PASSAGE_TIMESTEP - _TEST_ACTUAL_PASSAGE_TIMESTEP_FROZEN
)
_FROZEN_BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS = (
    _FROZEN_BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS * _TEST_DELTAT_SECONDS
)
_FROZEN_BASELINE_MINUS_ACTUAL_TIME_VALUE = (
    _FROZEN_BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS * _TEST_TRUE_VOT_PER_SECOND
)

_FROZEN_CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS = (
    _TEST_CANDIDATE_PASSAGE_TIMESTEP - _TEST_ACTUAL_PASSAGE_TIMESTEP_FROZEN
)
_FROZEN_CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS = (
    _FROZEN_CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS * _TEST_DELTAT_SECONDS
)
_FROZEN_CANDIDATE_MINUS_ACTUAL_TIME_VALUE = (
    _FROZEN_CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS * _TEST_TRUE_VOT_PER_SECOND
)


def _sample_visit_key(vehicle_name: str, visit_index: int) -> OrderControlTvtVisitKey:
    return (vehicle_name, visit_index)


def _wait_entry_baseline_minus_candidate_kwargs() -> dict:
    return {
        "baseline_minus_candidate_passage_timesteps": None,
        "baseline_minus_candidate_passage_seconds": None,
        "baseline_minus_candidate_time_value": None,
    }


def _base_observation_record_kwargs(
    visit_key: OrderControlTvtVisitKey,
    role: OrderControlTvtMpActualPassageRole,
    observation_status: OrderControlTvtMpActualPassageObservationStatus,
    *,
    actual_passage_timestep: int | None,
    actual_route_next_link_name: str | None,
    baseline_minus_actual_passage_timesteps: int | None,
    baseline_minus_actual_passage_seconds: int | float | None,
    baseline_minus_actual_time_value: int | float | None,
    candidate_minus_actual_passage_timesteps: int | None,
    candidate_minus_actual_passage_seconds: int | float | None,
    candidate_minus_actual_time_value: int | float | None,
) -> dict:
    return {
        "tvt_decision_timestep": 10,
        "node_name": "node_a",
        "buyers_sorted": (_sample_visit_key("buyer_1", 1),),
        "visit_key": visit_key,
        "vehicle_name": visit_key[0],
        "role": role,
        "observation_status": observation_status,
        "baseline_passage_timestep": _TEST_BASELINE_PASSAGE_TIMESTEP,
        "candidate_passage_timestep": _TEST_CANDIDATE_PASSAGE_TIMESTEP,
        "true_vot_per_second": _TEST_TRUE_VOT_PER_SECOND,
        "predicted_observation_status": (
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        "predicted_route_next_link_name": "link_pred",
        "baseline_minus_candidate_passage_timesteps": (
            _BASELINE_MINUS_CANDIDATE_PASSAGE_TIMESTEPS
        ),
        "baseline_minus_candidate_passage_seconds": (
            _BASELINE_MINUS_CANDIDATE_PASSAGE_SECONDS
        ),
        "baseline_minus_candidate_time_value": _BASELINE_MINUS_CANDIDATE_TIME_VALUE,
        "baseline_minus_actual_passage_timesteps": (
            baseline_minus_actual_passage_timesteps
        ),
        "baseline_minus_actual_passage_seconds": baseline_minus_actual_passage_seconds,
        "baseline_minus_actual_time_value": baseline_minus_actual_time_value,
        "candidate_minus_actual_passage_timesteps": (
            candidate_minus_actual_passage_timesteps
        ),
        "candidate_minus_actual_passage_seconds": (
            candidate_minus_actual_passage_seconds
        ),
        "candidate_minus_actual_time_value": candidate_minus_actual_time_value,
        "actual_passage_timestep": actual_passage_timestep,
        "actual_route_next_link_name": actual_route_next_link_name,
    }


def test_actual_passage_role_has_three_values():
    values = {member.value for member in OrderControlTvtMpActualPassageRole}
    assert values == {"buyer", "seller", "nonparticipating"}


def test_observation_status_has_two_values():
    values = {member.value for member in OrderControlTvtMpActualPassageObservationStatus}
    assert values == {
        "actual_passage_observed",
        "actual_passage_unobserved_at_evaluation_end",
    }


def test_observation_status_has_no_waiting_value():
    names = {member.name for member in OrderControlTvtMpActualPassageObservationStatus}
    assert "WAITING_FOR_ACTUAL_PASSAGE" not in names
    values = {member.value for member in OrderControlTvtMpActualPassageObservationStatus}
    assert "waiting_for_actual_passage" not in values


def test_wait_status_has_three_values():
    values = {member.value for member in OrderControlTvtMpActualPassageWaitStatus}
    assert values == {
        "waiting_for_actual_passage",
        "actual_passage_observed",
        "actual_passage_unobserved_at_evaluation_end",
    }


def test_observation_record_observed_with_actual_values():
    visit_key = _sample_visit_key("veh_observed", 0)
    record = OrderControlTvtMpActualPassageObservationRecord(
        **_base_observation_record_kwargs(
            visit_key,
            OrderControlTvtMpActualPassageRole.BUYER,
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED,
            actual_passage_timestep=_TEST_ACTUAL_PASSAGE_TIMESTEP_OBSERVED,
            actual_route_next_link_name="link_actual",
            baseline_minus_actual_passage_timesteps=(
                _BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS
            ),
            baseline_minus_actual_passage_seconds=_BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS,
            baseline_minus_actual_time_value=_BASELINE_MINUS_ACTUAL_TIME_VALUE,
            candidate_minus_actual_passage_timesteps=(
                _CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS
            ),
            candidate_minus_actual_passage_seconds=(
                _CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS
            ),
            candidate_minus_actual_time_value=_CANDIDATE_MINUS_ACTUAL_TIME_VALUE,
        )
    )
    assert record.buyers_sorted == (_sample_visit_key("buyer_1", 1),)
    assert record.actual_passage_timestep == _TEST_ACTUAL_PASSAGE_TIMESTEP_OBSERVED
    assert record.actual_route_next_link_name == "link_actual"
    assert (
        record.baseline_minus_candidate_passage_timesteps
        == _BASELINE_MINUS_CANDIDATE_PASSAGE_TIMESTEPS
    )
    assert (
        record.baseline_minus_candidate_passage_seconds
        == _BASELINE_MINUS_CANDIDATE_PASSAGE_SECONDS
    )
    assert record.baseline_minus_candidate_time_value == _BASELINE_MINUS_CANDIDATE_TIME_VALUE
    assert (
        record.baseline_minus_actual_passage_timesteps
        == _BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS
    )
    assert (
        record.baseline_minus_actual_passage_seconds
        == _BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS
    )
    assert record.baseline_minus_actual_time_value == _BASELINE_MINUS_ACTUAL_TIME_VALUE
    assert (
        record.candidate_minus_actual_passage_timesteps
        == _CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS
    )
    assert (
        record.candidate_minus_actual_passage_seconds
        == _CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS
    )
    assert record.candidate_minus_actual_time_value == _CANDIDATE_MINUS_ACTUAL_TIME_VALUE


def test_observation_record_unobserved_with_none_actual_values():
    visit_key = _sample_visit_key("veh_unobserved", 1)
    record = OrderControlTvtMpActualPassageObservationRecord(
        **_base_observation_record_kwargs(
            visit_key,
            OrderControlTvtMpActualPassageRole.SELLER,
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END,
            actual_passage_timestep=None,
            actual_route_next_link_name=None,
            baseline_minus_actual_passage_timesteps=None,
            baseline_minus_actual_passage_seconds=None,
            baseline_minus_actual_time_value=None,
            candidate_minus_actual_passage_timesteps=None,
            candidate_minus_actual_passage_seconds=None,
            candidate_minus_actual_time_value=None,
        )
    )
    assert record.actual_passage_timestep is None
    assert record.actual_route_next_link_name is None
    assert (
        record.baseline_minus_candidate_passage_timesteps
        == _BASELINE_MINUS_CANDIDATE_PASSAGE_TIMESTEPS
    )
    assert (
        record.baseline_minus_candidate_passage_seconds
        == _BASELINE_MINUS_CANDIDATE_PASSAGE_SECONDS
    )
    assert record.baseline_minus_candidate_time_value == _BASELINE_MINUS_CANDIDATE_TIME_VALUE
    assert record.baseline_minus_actual_passage_timesteps is None
    assert record.baseline_minus_actual_passage_seconds is None
    assert record.baseline_minus_actual_time_value is None
    assert record.candidate_minus_actual_passage_timesteps is None
    assert record.candidate_minus_actual_passage_seconds is None
    assert record.candidate_minus_actual_time_value is None


def test_observation_record_is_frozen():
    visit_key = _sample_visit_key("veh_frozen", 0)
    record = OrderControlTvtMpActualPassageObservationRecord(
        **_base_observation_record_kwargs(
            visit_key,
            OrderControlTvtMpActualPassageRole.BUYER,
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED,
            actual_passage_timestep=_TEST_ACTUAL_PASSAGE_TIMESTEP_FROZEN,
            actual_route_next_link_name="l",
            baseline_minus_actual_passage_timesteps=(
                _FROZEN_BASELINE_MINUS_ACTUAL_PASSAGE_TIMESTEPS
            ),
            baseline_minus_actual_passage_seconds=(
                _FROZEN_BASELINE_MINUS_ACTUAL_PASSAGE_SECONDS
            ),
            baseline_minus_actual_time_value=_FROZEN_BASELINE_MINUS_ACTUAL_TIME_VALUE,
            candidate_minus_actual_passage_timesteps=(
                _FROZEN_CANDIDATE_MINUS_ACTUAL_PASSAGE_TIMESTEPS
            ),
            candidate_minus_actual_passage_seconds=(
                _FROZEN_CANDIDATE_MINUS_ACTUAL_PASSAGE_SECONDS
            ),
            candidate_minus_actual_time_value=_FROZEN_CANDIDATE_MINUS_ACTUAL_TIME_VALUE,
        )
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.actual_passage_timestep = 99


def _common_frozen(
    *,
    baseline_local_rank=2,
    post_trade_local_rank=1,
    route_origin=_ROUTE_ORIGIN,
):
    return OrderControlTvtMpActualPassageCommonFrozenInput(
        baseline_local_rank=baseline_local_rank,
        post_trade_local_rank=post_trade_local_rank,
        rank_change=baseline_local_rank - post_trade_local_rank,
        route_origin=route_origin,
    )


def _monetary_frozen(
    *,
    declared_vot_per_second=1.0,
    payment_paid_in_this_transaction=3.0,
    payment_received_in_this_transaction=0,
):
    return OrderControlTvtMpActualPassageMonetaryFrozenInput(
        declared_vot_per_second=declared_vot_per_second,
        payment_paid_in_this_transaction=payment_paid_in_this_transaction,
        payment_received_in_this_transaction=payment_received_in_this_transaction,
    )


def _frozen_fields(role, **monetary_changes):
    if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        monetary = None
    else:
        monetary = _monetary_frozen(**monetary_changes)
    return {
        "common_frozen_input": _common_frozen(),
        "monetary_frozen_input": monetary,
    }


def test_wait_entry_wait_status_is_mutable():
    visit_key = _sample_visit_key("veh_wait", 0)
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=1,
        node_name="n",
        buyers_sorted=(_sample_visit_key("b", 1),),
        visit_key=visit_key,
        vehicle_name=visit_key[0],
        role=OrderControlTvtMpActualPassageRole.BUYER,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=None,
        candidate_passage_timestep=None,
        true_vot_per_second=1.0,
        **_wait_entry_baseline_minus_candidate_kwargs(),
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link",
        **_frozen_fields(OrderControlTvtMpActualPassageRole.BUYER),
    )
    entry.wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    assert (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )


def test_common_and_monetary_frozen_inputs_keep_establishment_values():
    common = _common_frozen(baseline_local_rank=4, post_trade_local_rank=1)
    assert dataclasses.is_dataclass(common)
    assert common.__dataclass_params__.frozen is True
    assert common.rank_change == 3
    assert common.route_origin is _ROUTE_ORIGIN
    with pytest.raises(dataclasses.FrozenInstanceError):
        common.rank_change = 0
    monetary = _monetary_frozen(
        declared_vot_per_second=0.0,
        payment_paid_in_this_transaction=0,
        payment_received_in_this_transaction=0.0,
    )
    assert monetary.__dataclass_params__.frozen is True
    assert monetary.declared_vot_per_second == 0.0
    assert monetary.payment_paid_in_this_transaction == 0
    assert monetary.payment_received_in_this_transaction == 0.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        monetary.declared_vot_per_second = 1.0


def test_common_frozen_input_rejects_a_rank_change_that_is_not_the_difference():
    with pytest.raises(RuntimeError, match="rank_change"):
        OrderControlTvtMpActualPassageCommonFrozenInput(
            baseline_local_rank=4,
            post_trade_local_rank=1,
            rank_change=0,
            route_origin=_ROUTE_ORIGIN,
        )


def test_monetary_frozen_input_rejects_none_amounts():
    with pytest.raises(RuntimeError, match="not None"):
        OrderControlTvtMpActualPassageMonetaryFrozenInput(
            declared_vot_per_second=1.0,
            payment_paid_in_this_transaction=None,
            payment_received_in_this_transaction=0,
        )


def test_wait_entry_requires_common_frozen_input():
    visit_key = _sample_visit_key("veh_required", 1)
    with pytest.raises(TypeError):
        OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=1,
            node_name="n",
            buyers_sorted=(visit_key,),
            visit_key=visit_key,
            vehicle_name=visit_key[0],
            role=OrderControlTvtMpActualPassageRole.BUYER,
            wait_status=(
                OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
            ),
            baseline_passage_timestep=None,
            candidate_passage_timestep=None,
            true_vot_per_second=0.0,
            **_wait_entry_baseline_minus_candidate_kwargs(),
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="link",
            monetary_frozen_input=_monetary_frozen(),
        )


def test_buyer_and_seller_require_monetary_frozen_input():
    for role in (
        OrderControlTvtMpActualPassageRole.BUYER,
        OrderControlTvtMpActualPassageRole.SELLER,
    ):
        visit_key = _sample_visit_key(role.value, 1)
        with pytest.raises(RuntimeError, match="requires"):
            OrderControlTvtMpActualPassageWaitEntry(
                tvt_decision_timestep=1,
                node_name="n",
                buyers_sorted=(visit_key,),
                visit_key=visit_key,
                vehicle_name=visit_key[0],
                role=role,
                wait_status=(
                    OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
                ),
                baseline_passage_timestep=None,
                candidate_passage_timestep=None,
                true_vot_per_second=0.0,
                **_wait_entry_baseline_minus_candidate_kwargs(),
                predicted_observation_status=(
                    OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
                ),
                predicted_route_next_link_name="link",
                common_frozen_input=_common_frozen(),
                monetary_frozen_input=None,
            )


def test_nonparticipating_rejects_a_monetary_frozen_input():
    visit_key = _sample_visit_key("watcher", 1)
    with pytest.raises(RuntimeError, match="must not carry"):
        OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=1,
            node_name="n",
            buyers_sorted=(visit_key,),
            visit_key=visit_key,
            vehicle_name=visit_key[0],
            role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            wait_status=(
                OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
            ),
            baseline_passage_timestep=None,
            candidate_passage_timestep=None,
            true_vot_per_second=0.0,
            **_wait_entry_baseline_minus_candidate_kwargs(),
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="link",
            common_frozen_input=_common_frozen(),
            monetary_frozen_input=_monetary_frozen(),
        )


def test_wait_entry_keeps_zero_true_vot_with_positive_declared_vot():
    visit_key = _sample_visit_key("zero_true", 2)
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=1,
        node_name="n",
        buyers_sorted=(visit_key,),
        visit_key=visit_key,
        vehicle_name=visit_key[0],
        role=OrderControlTvtMpActualPassageRole.BUYER,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=None,
        candidate_passage_timestep=None,
        true_vot_per_second=0.0,
        **_wait_entry_baseline_minus_candidate_kwargs(),
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link",
        **_frozen_fields(
            OrderControlTvtMpActualPassageRole.BUYER,
            declared_vot_per_second=4.0,
            payment_paid_in_this_transaction=0,
            payment_received_in_this_transaction=0,
        ),
    )
    assert entry.true_vot_per_second == 0.0
    assert entry.monetary_frozen_input.declared_vot_per_second == 4.0
    assert entry.monetary_frozen_input.payment_paid_in_this_transaction == 0
    assert entry.common_frozen_input.rank_change == 1
    revisit_key = _sample_visit_key("zero_true", 3)
    revisit = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=1,
        node_name="n",
        buyers_sorted=(visit_key,),
        visit_key=revisit_key,
        vehicle_name=visit_key[0],
        role=OrderControlTvtMpActualPassageRole.SELLER,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=None,
        candidate_passage_timestep=None,
        true_vot_per_second=0.0,
        **_wait_entry_baseline_minus_candidate_kwargs(),
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link",
        **_frozen_fields(
            OrderControlTvtMpActualPassageRole.SELLER,
            declared_vot_per_second=0.0,
            payment_paid_in_this_transaction=0,
            payment_received_in_this_transaction=0,
        ),
    )
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    registry.entries_by_node_name_and_visit_key[("n", visit_key)] = entry
    registry.entries_by_node_name_and_visit_key[("n", revisit_key)] = revisit
    assert registry.entries_by_node_name_and_visit_key[("n", visit_key)] is entry
    assert registry.entries_by_node_name_and_visit_key[("n", revisit_key)] is revisit
    assert entry.vehicle_name == revisit.vehicle_name
    assert entry.visit_key != revisit.visit_key


def test_trade_wait_notification_flag_is_mutable():
    buyer_key = _sample_visit_key("buyer_v", 0)
    seller_key = _sample_visit_key("seller_v", 0)
    nonpart_key = _sample_visit_key("other_v", 0)
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=3,
        node_name="node_trade",
        buyers_sorted=(_sample_visit_key("buyer_a", 1),),
        all_visit_keys=(buyer_key, seller_key, nonpart_key),
        buyer_visit_keys=(buyer_key,),
        seller_visit_keys=(seller_key,),
        nonparticipating_visit_keys=(nonpart_key,),
    )
    assert trade.buyer_seller_actual_passage_completion_notified is False
    trade.buyer_seller_actual_passage_completion_notified = True
    assert trade.buyer_seller_actual_passage_completion_notified is True


def test_registry_dicts_start_empty():
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    assert registry.entries_by_node_name_and_visit_key == {}
    assert registry.trades_by_transaction_key == {}


def test_two_registry_instances_do_not_share_dicts():
    registry_a = OrderControlTvtMpActualPassageWaitRegistry()
    registry_b = OrderControlTvtMpActualPassageWaitRegistry()
    visit_key = _sample_visit_key("v", 0)
    registry_a.entries_by_node_name_and_visit_key[("n", visit_key)] = (
        OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=1,
            node_name="n",
            buyers_sorted=(),
            visit_key=visit_key,
            vehicle_name="v",
            role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
            baseline_passage_timestep=None,
            candidate_passage_timestep=None,
            true_vot_per_second=0.0,
            **_wait_entry_baseline_minus_candidate_kwargs(),
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="",
            **_frozen_fields(OrderControlTvtMpActualPassageRole.NONPARTICIPATING),
        )
    )
    assert registry_b.entries_by_node_name_and_visit_key == {}


def test_two_world_instances_do_not_share_registry_or_dicts():
    world_a = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    world_b = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    registry_a = world_a.order_control_tvt_mp_actual_passage_wait_registry
    registry_b = world_b.order_control_tvt_mp_actual_passage_wait_registry
    assert registry_a is not registry_b
    visit_key = _sample_visit_key("w", 0)
    registry_a.entries_by_node_name_and_visit_key[("w_node", visit_key)] = (
        OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=1,
            node_name="w_node",
            buyers_sorted=(),
            visit_key=visit_key,
            vehicle_name="w",
            role=OrderControlTvtMpActualPassageRole.BUYER,
            wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
            baseline_passage_timestep=None,
            candidate_passage_timestep=None,
            true_vot_per_second=0.0,
            **_wait_entry_baseline_minus_candidate_kwargs(),
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="",
            **_frozen_fields(OrderControlTvtMpActualPassageRole.BUYER),
        )
    )
    assert registry_b.entries_by_node_name_and_visit_key == {}


def test_trade_wait_holds_distinct_visit_keys_by_role():
    buyer_key = _sample_visit_key("buyer_vehicle", 0)
    seller_key = _sample_visit_key("seller_vehicle", 1)
    nonpart_key = _sample_visit_key("other_vehicle", 2)
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=5,
        node_name="role_node",
        buyers_sorted=(_sample_visit_key("b1", 1),),
        all_visit_keys=(buyer_key, seller_key, nonpart_key),
        buyer_visit_keys=(buyer_key,),
        seller_visit_keys=(seller_key,),
        nonparticipating_visit_keys=(nonpart_key,),
    )
    assert trade.buyer_visit_keys == (buyer_key,)
    assert trade.seller_visit_keys == (seller_key,)
    assert trade.nonparticipating_visit_keys == (nonpart_key,)
    assert buyer_key != seller_key != nonpart_key


def test_registry_entry_mapping_uses_node_name_and_visit_key():
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    visit_key = _sample_visit_key("map_v", 3)
    node_name = "map_node"
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=2,
        node_name=node_name,
        buyers_sorted=(_sample_visit_key("x", 1),),
        visit_key=visit_key,
        vehicle_name="map_v",
        role=OrderControlTvtMpActualPassageRole.SELLER,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=None,
        candidate_passage_timestep=None,
        true_vot_per_second=1.0,
        **_wait_entry_baseline_minus_candidate_kwargs(),
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="lnk",
        **_frozen_fields(OrderControlTvtMpActualPassageRole.SELLER),
    )
    key = (node_name, visit_key)
    registry.entries_by_node_name_and_visit_key[key] = entry
    assert registry.entries_by_node_name_and_visit_key[key] is entry


def test_registry_trade_mapping_uses_transaction_key():
    # Type-only mapping check: empty buyer/seller keys are not a formal trade.
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    buyers_sorted = (
        _sample_visit_key("buyer_z", 1),
        _sample_visit_key("buyer_y", 2),
    )
    transaction_key = (20, "trade_node", buyers_sorted)
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=20,
        node_name="trade_node",
        buyers_sorted=buyers_sorted,
        all_visit_keys=(),
        buyer_visit_keys=(),
        seller_visit_keys=(),
        nonparticipating_visit_keys=(),
    )
    registry.trades_by_transaction_key[transaction_key] = trade
    assert registry.trades_by_transaction_key[transaction_key] is trade
    assert trade.buyers_sorted == (
        ("buyer_z", 1),
        ("buyer_y", 2),
    )
    assert transaction_key[2] == trade.buyers_sorted


def test_buyers_sorted_and_transaction_key_annotations_use_visit_keys():
    expected = "tuple[OrderControlTvtVisitKey, ...]"
    assert (
        OrderControlTvtMpActualPassageObservationRecord.__annotations__[
            "buyers_sorted"
        ]
        == expected
    )
    assert (
        OrderControlTvtMpActualPassageWaitEntry.__annotations__["buyers_sorted"]
        == expected
    )
    assert (
        OrderControlTvtMpActualPassageTradeWait.__annotations__["buyers_sorted"]
        == expected
    )
    trade_annotation = OrderControlTvtMpActualPassageWaitRegistry.__annotations__[
        "trades_by_transaction_key"
    ]
    assert "tuple[OrderControlTvtVisitKey, ...]" in trade_annotation
    assert "tuple[str, ...]" not in trade_annotation


class _ObservationNode:
    def __init__(self, world, name):
        self.W = world
        self.name = name


class _ObservationVehicle:
    def __init__(self, name, log):
        self.name = name
        self.order_exchange_log = log
        self.vot_true = 999.0


class _ObservationOutlink:
    def __init__(self, name):
        self.name = name


_PREPARE_DECISION_TIMESTEP = 10
_PREPARE_ACTUAL_TIMESTEP = 12
_PREPARE_BASELINE_PASSAGE_TIMESTEP = 10
_PREPARE_CANDIDATE_PASSAGE_TIMESTEP = 8
_COPIED_BASELINE_MINUS_CANDIDATE = (41, 42, 43)


def _observation_world():
    world = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    world.DELTAT = _TEST_DELTAT_SECONDS
    return world


def _register_peer_waiting_entry(
    world,
    *,
    node_name,
    vehicle_name,
    role,
    visit_index,
    decision_timestep,
    buyers_sorted,
):
    visit_key = _sample_visit_key(vehicle_name, visit_index)
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=decision_timestep,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        visit_key=visit_key,
        vehicle_name=vehicle_name,
        role=role,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=_PREPARE_BASELINE_PASSAGE_TIMESTEP,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        true_vot_per_second=_TEST_TRUE_VOT_PER_SECOND,
        baseline_minus_candidate_passage_timesteps=_COPIED_BASELINE_MINUS_CANDIDATE[0],
        baseline_minus_candidate_passage_seconds=_COPIED_BASELINE_MINUS_CANDIDATE[1],
        baseline_minus_candidate_time_value=_COPIED_BASELINE_MINUS_CANDIDATE[2],
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link_pred",
        **_frozen_fields(role),
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.entries_by_node_name_and_visit_key[(node_name, visit_key)] = entry
    return visit_key, entry


def _register_formal_trade_wait(
    world,
    *,
    decision_timestep,
    node_name,
    buyers_sorted,
    buyer_visit_keys,
    seller_visit_keys,
    nonparticipating_visit_keys=(),
    completion_notified=False,
):
    all_visit_keys = tuple(
        list(buyer_visit_keys)
        + list(seller_visit_keys)
        + list(nonparticipating_visit_keys)
    )
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=decision_timestep,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        all_visit_keys=all_visit_keys,
        buyer_visit_keys=buyer_visit_keys,
        seller_visit_keys=seller_visit_keys,
        nonparticipating_visit_keys=nonparticipating_visit_keys,
        buyer_seller_actual_passage_completion_notified=completion_notified,
    )
    transaction_key = (decision_timestep, node_name, buyers_sorted)
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.trades_by_transaction_key[transaction_key] = trade
    return trade, transaction_key


def _attach_minimal_formal_trade_for_entry(world, node_name, entry, visit_key, role):
    decision_timestep = entry.tvt_decision_timestep
    buyers_sorted = entry.buyers_sorted
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        buyer_visit_keys = (visit_key,)
        seller_visit_key, _ = _register_peer_waiting_entry(
            world,
            node_name=node_name,
            vehicle_name="formal_peer_seller",
            role=OrderControlTvtMpActualPassageRole.SELLER,
            visit_index=50,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
        seller_visit_keys = (seller_visit_key,)
        nonparticipating_visit_keys = ()
    elif role is OrderControlTvtMpActualPassageRole.SELLER:
        seller_visit_keys = (visit_key,)
        buyer_visit_key, _ = _register_peer_waiting_entry(
            world,
            node_name=node_name,
            vehicle_name="formal_peer_buyer",
            role=OrderControlTvtMpActualPassageRole.BUYER,
            visit_index=51,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
        buyer_visit_keys = (buyer_visit_key,)
        nonparticipating_visit_keys = ()
    else:
        nonparticipating_visit_keys = (visit_key,)
        buyer_visit_key, _ = _register_peer_waiting_entry(
            world,
            node_name=node_name,
            vehicle_name="formal_peer_buyer",
            role=OrderControlTvtMpActualPassageRole.BUYER,
            visit_index=52,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
        seller_visit_key, _ = _register_peer_waiting_entry(
            world,
            node_name=node_name,
            vehicle_name="formal_peer_seller",
            role=OrderControlTvtMpActualPassageRole.SELLER,
            visit_index=53,
            decision_timestep=decision_timestep,
            buyers_sorted=buyers_sorted,
        )
        buyer_visit_keys = (buyer_visit_key,)
        seller_visit_keys = (seller_visit_key,)
    trade, _transaction_key = _register_formal_trade_wait(
        world,
        decision_timestep=decision_timestep,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        buyer_visit_keys=buyer_visit_keys,
        seller_visit_keys=seller_visit_keys,
        nonparticipating_visit_keys=nonparticipating_visit_keys,
    )
    return trade


def _register_waiting_entry(
    world,
    *,
    node_name,
    vehicle_name,
    role,
    candidate_passage_timestep,
    predicted_observation_status,
    baseline_minus_candidate,
    log,
    true_vot_per_second=_TEST_TRUE_VOT_PER_SECOND,
    baseline_passage_timestep=_PREPARE_BASELINE_PASSAGE_TIMESTEP,
    decision_timestep=_PREPARE_DECISION_TIMESTEP,
    entry_visit_key=None,
    entry_node_name=None,
    entry_vehicle_name=None,
    attach_minimal_formal_trade=True,
):
    visit_key = _sample_visit_key(vehicle_name, 1)
    if entry_visit_key is None:
        entry_visit_key = visit_key
    if entry_node_name is None:
        entry_node_name = node_name
    if entry_vehicle_name is None:
        entry_vehicle_name = vehicle_name
    if baseline_minus_candidate is None:
        copied_timesteps = None
        copied_seconds = None
        copied_value = None
    else:
        copied_timesteps, copied_seconds, copied_value = baseline_minus_candidate
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=decision_timestep,
        node_name=entry_node_name,
        buyers_sorted=(_sample_visit_key("buyer_1", 1),),
        visit_key=entry_visit_key,
        vehicle_name=entry_vehicle_name,
        role=role,
        wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        true_vot_per_second=true_vot_per_second,
        baseline_minus_candidate_passage_timesteps=copied_timesteps,
        baseline_minus_candidate_passage_seconds=copied_seconds,
        baseline_minus_candidate_time_value=copied_value,
        predicted_observation_status=predicted_observation_status,
        predicted_route_next_link_name="link_pred",
        **_frozen_fields(role),
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.entries_by_node_name_and_visit_key[(node_name, visit_key)] = entry
    trade = None
    if attach_minimal_formal_trade:
        trade = _attach_minimal_formal_trade_for_entry(
            world,
            node_name,
            entry,
            visit_key,
            role,
        )
    node = _ObservationNode(world, node_name)
    vehicle = _ObservationVehicle(vehicle_name, log)
    outlink = _ObservationOutlink("link_actual")
    return node, vehicle, visit_key, outlink, entry, trade


def _commit_prepared(node, vehicle, visit_key, outlink, actual_timestep):
    prepared = prepare_tvt_mp_actual_passage_observation(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=actual_timestep,
    )
    assert prepared is not None
    notified_trade = commit_tvt_mp_actual_passage_observation(prepared)
    return prepared, notified_trade


def _assert_prepare_rejects(node, vehicle, visit_key, outlink, actual_timestep, entry):
    log_before = vehicle.order_exchange_log
    status_before = entry.wait_status
    record_before = entry.actual_passage_observation_record
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    entries_before = registry.entries_by_node_name_and_visit_key
    trades_before = registry.trades_by_transaction_key
    trade_flags_before = {
        key: trade.buyer_seller_actual_passage_completion_notified
        for key, trade in trades_before.items()
    }
    try:
        prepare_tvt_mp_actual_passage_observation(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=actual_timestep,
        )
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True
    assert vehicle.order_exchange_log is log_before
    assert entry.wait_status is status_before
    assert entry.actual_passage_observation_record is record_before
    assert registry.entries_by_node_name_and_visit_key is entries_before
    assert registry.trades_by_transaction_key is trades_before
    for key, trade in trades_before.items():
        assert (
            trade.buyer_seller_actual_passage_completion_notified
            == trade_flags_before[key]
        )
    assert entries_before[(node.name, visit_key)] is entry


def test_prepare_returns_none_when_wait_entry_is_missing():
    world = _observation_world()
    node = _ObservationNode(world, "node_a")
    vehicle = _ObservationVehicle("buyer", ["old"])
    visit_key = _sample_visit_key("buyer", 1)
    prepared = prepare_tvt_mp_actual_passage_observation(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=_ObservationOutlink("link_actual"),
        actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
    )
    assert prepared is None
    assert vehicle.order_exchange_log == ["old"]
    assert world.order_control_tvt_mp_actual_passage_wait_registry.entries_by_node_name_and_visit_key == {}


def _assert_observed_actual_record(role, vehicle_name):
    world = _observation_world()
    old_log = ["establishment"]
    node, vehicle, visit_key, outlink, entry, trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name=vehicle_name,
        role=role,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=old_log,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    transaction_key = (
        _PREPARE_DECISION_TIMESTEP,
        "node_a",
        (_sample_visit_key("buyer_1", 1),),
    )
    vehicle.vot_true = 999.0
    prepared, notified_trade = _commit_prepared(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
    )
    record = entry.actual_passage_observation_record
    assert record is prepared.actual_passage_observation_record
    assert vehicle.order_exchange_log[-1] is record
    assert vehicle.order_exchange_log is not old_log
    assert old_log == ["establishment"]
    assert record.role is role
    assert record.observation_status is (
        OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
    )
    assert record.actual_passage_timestep == _PREPARE_ACTUAL_TIMESTEP
    assert record.actual_route_next_link_name == "link_actual"
    assert record.true_vot_per_second == _TEST_TRUE_VOT_PER_SECOND
    assert vehicle.vot_true == 999.0
    vehicle.vot_true = 0.0
    assert record.true_vot_per_second == _TEST_TRUE_VOT_PER_SECOND
    assert record.baseline_minus_candidate_passage_timesteps == 41
    assert record.baseline_minus_candidate_passage_seconds == 42
    assert record.baseline_minus_candidate_time_value == 43
    assert record.baseline_minus_actual_passage_timesteps == -2
    assert record.baseline_minus_actual_passage_seconds == -120
    assert record.baseline_minus_actual_time_value == -60.0
    assert record.candidate_minus_actual_passage_timesteps == -4
    assert record.candidate_minus_actual_passage_seconds == -240
    assert record.candidate_minus_actual_time_value == -120.0
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    assert registry.entries_by_node_name_and_visit_key[(node.name, visit_key)] is entry
    assert registry.trades_by_transaction_key[transaction_key] is trade
    assert trade.buyer_seller_actual_passage_completion_notified is False
    assert notified_trade is None
    return node, vehicle, visit_key, outlink, entry, trade


def test_buyer_actual_record_is_stored_on_log_and_wait_entry():
    _assert_observed_actual_record(
        OrderControlTvtMpActualPassageRole.BUYER,
        "buyer",
    )


def test_seller_actual_record_is_stored_on_log_and_wait_entry():
    _assert_observed_actual_record(
        OrderControlTvtMpActualPassageRole.SELLER,
        "seller",
    )


def test_nonparticipating_observed_actual_record_is_stored():
    _assert_observed_actual_record(
        OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        "watcher",
    )


def test_unobserved_candidate_nonparticipating_keeps_candidate_difference_none():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="watcher",
        role=OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
        candidate_passage_timestep=None,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON
        ),
        baseline_minus_candidate=None,
        log=["old"],
    )
    vehicle.vot_true = None
    _commit_prepared(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
    )
    record = entry.actual_passage_observation_record
    assert record.predicted_observation_status is (
        OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON
    )
    assert record.candidate_passage_timestep is None
    assert record.baseline_minus_candidate_passage_timesteps is None
    assert record.baseline_minus_candidate_passage_seconds is None
    assert record.baseline_minus_candidate_time_value is None
    assert record.baseline_minus_actual_passage_timesteps == -2
    assert record.baseline_minus_actual_passage_seconds == -120
    assert record.baseline_minus_actual_time_value == -60.0
    assert record.candidate_minus_actual_passage_timesteps is None
    assert record.candidate_minus_actual_passage_seconds is None
    assert record.candidate_minus_actual_time_value is None
    assert record.true_vot_per_second == _TEST_TRUE_VOT_PER_SECOND
    assert vehicle.vot_true is None
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )


def test_actual_timestep_equal_to_decision_timestep_is_allowed():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=[],
    )
    _commit_prepared(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_DECISION_TIMESTEP,
    )
    record = entry.actual_passage_observation_record
    assert record.actual_passage_timestep == _PREPARE_DECISION_TIMESTEP
    assert record.baseline_minus_actual_passage_timesteps == 0
    assert record.baseline_minus_actual_passage_seconds == 0
    assert record.baseline_minus_actual_time_value == 0.0


def test_prepare_rejects_non_list_log_without_writing():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=("old",),
    )
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_identity_mismatch_without_writing():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
        entry_vehicle_name="other",
    )
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
        entry_node_name="other_node",
    )
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
        entry_visit_key=_sample_visit_key("buyer", 2),
    )
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_bad_wait_state_without_writing():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
    )
    entry.wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_second_observation_of_the_same_visit_is_rejected():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
    )
    _commit_prepared(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
    )
    log_after_commit = vehicle.order_exchange_log
    record = entry.actual_passage_observation_record
    try:
        prepare_tvt_mp_actual_passage_observation(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
        )
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True
    assert vehicle.order_exchange_log is log_after_commit
    assert entry.actual_passage_observation_record is record
    assert entry.wait_status is (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )


def test_prepare_rejects_actual_timestep_before_decision_without_writing():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
    )
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_DECISION_TIMESTEP - 1,
        entry,
    )


def test_prepare_rejects_bad_passage_deltat_vot_and_route_without_writing():
    def one_case(**entry_changes):
        world = _observation_world()
        if "deltat" in entry_changes:
            world.DELTAT = entry_changes.pop("deltat")
        route_name = entry_changes.pop("route_name", "link_actual")
        actual_timestep = entry_changes.pop(
            "actual_timestep",
            _PREPARE_ACTUAL_TIMESTEP,
        )
        node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
            world,
            node_name="node_a",
            vehicle_name="buyer",
            role=OrderControlTvtMpActualPassageRole.BUYER,
            candidate_passage_timestep=entry_changes.pop(
                "candidate_passage_timestep",
                _PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
            ),
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
            log=["old"],
            true_vot_per_second=entry_changes.pop(
                "true_vot_per_second",
                _TEST_TRUE_VOT_PER_SECOND,
            ),
            baseline_passage_timestep=entry_changes.pop(
                "baseline_passage_timestep",
                _PREPARE_BASELINE_PASSAGE_TIMESTEP,
            ),
        )
        assert entry_changes == {}
        outlink.name = route_name
        _assert_prepare_rejects(
            node,
            vehicle,
            visit_key,
            outlink,
            actual_timestep,
            entry,
        )

    one_case(baseline_passage_timestep=10.0)
    one_case(baseline_passage_timestep=True)
    one_case(baseline_passage_timestep=None)
    one_case(candidate_passage_timestep=8.0)
    one_case(candidate_passage_timestep=True)
    one_case(candidate_passage_timestep="8")
    one_case(deltat=0)
    one_case(deltat=-1)
    one_case(deltat=True)
    one_case(deltat=None)
    one_case(deltat=float("nan"))
    one_case(deltat=float("inf"))
    one_case(true_vot_per_second=-0.1)
    one_case(true_vot_per_second=True)
    one_case(true_vot_per_second=None)
    one_case(true_vot_per_second=float("nan"))
    one_case(route_name="")
    one_case(actual_timestep=True)
    one_case(actual_timestep=12.0)


def _create_formal_trade_with_entries(
    *,
    buyer_vehicle_names,
    seller_vehicle_names,
    nonpart_vehicle_name=None,
    completion_notified=False,
):
    world = _observation_world()
    node_name = "node_a"
    buyers_sorted = (_sample_visit_key("buyer_1", 1),)
    decision_timestep = _PREPARE_DECISION_TIMESTEP
    outlink = _ObservationOutlink("link_actual")
    node = _ObservationNode(world, node_name)
    buyer_keys = []
    seller_keys = []
    vehicles = {}
    entries = {}

    def add_role(vehicle_name, role):
        visit_key = _sample_visit_key(vehicle_name, 1)
        entry = OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=decision_timestep,
            node_name=node_name,
            buyers_sorted=buyers_sorted,
            visit_key=visit_key,
            vehicle_name=vehicle_name,
            role=role,
            wait_status=OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE,
            baseline_passage_timestep=_PREPARE_BASELINE_PASSAGE_TIMESTEP,
            candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
            true_vot_per_second=_TEST_TRUE_VOT_PER_SECOND,
            baseline_minus_candidate_passage_timesteps=_COPIED_BASELINE_MINUS_CANDIDATE[0],
            baseline_minus_candidate_passage_seconds=_COPIED_BASELINE_MINUS_CANDIDATE[1],
            baseline_minus_candidate_time_value=_COPIED_BASELINE_MINUS_CANDIDATE[2],
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="link_pred",
            **_frozen_fields(role),
        )
        registry = world.order_control_tvt_mp_actual_passage_wait_registry
        registry.entries_by_node_name_and_visit_key[(node_name, visit_key)] = entry
        vehicles[visit_key] = _ObservationVehicle(vehicle_name, [])
        entries[visit_key] = entry
        return visit_key

    for name in buyer_vehicle_names:
        buyer_keys.append(
            add_role(name, OrderControlTvtMpActualPassageRole.BUYER)
        )
    for name in seller_vehicle_names:
        seller_keys.append(
            add_role(name, OrderControlTvtMpActualPassageRole.SELLER)
        )
    nonpart_keys = ()
    if nonpart_vehicle_name is not None:
        nonpart_keys = (
            add_role(
                nonpart_vehicle_name,
                OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            ),
        )
    trade, _transaction_key = _register_formal_trade_wait(
        world,
        decision_timestep=decision_timestep,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        buyer_visit_keys=tuple(buyer_keys),
        seller_visit_keys=tuple(seller_keys),
        nonparticipating_visit_keys=nonpart_keys,
        completion_notified=completion_notified,
    )
    return world, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, entries


def _pass_visit(node, vehicles, visit_key, outlink, actual_timestep=_PREPARE_ACTUAL_TIMESTEP):
    vehicle = vehicles[visit_key]
    log_before = vehicle.order_exchange_log
    entry = node.W.order_control_tvt_mp_actual_passage_wait_registry.entries_by_node_name_and_visit_key[
        (node.name, visit_key)
    ]
    status_before = entry.wait_status
    record_before = entry.actual_passage_observation_record
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    trades_before = registry.trades_by_transaction_key
    trade_flag_before = {
        key: trade.buyer_seller_actual_passage_completion_notified
        for key, trade in trades_before.items()
    }
    prepared = prepare_tvt_mp_actual_passage_observation(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=actual_timestep,
    )
    assert prepared is not None
    notified_trade = commit_tvt_mp_actual_passage_observation(prepared)
    return prepared, notified_trade, log_before, status_before, record_before, trade_flag_before


def test_buyer_then_seller_emits_completion_once():
    world, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    _, notified_first, _, _, _, _ = _pass_visit(
        node, vehicles, buyer_keys[0], outlink
    )
    assert notified_first is None
    assert trade.buyer_seller_actual_passage_completion_notified is False
    _, notified_second, _, _, _, _ = _pass_visit(
        node, vehicles, seller_keys[0], outlink
    )
    assert notified_second is trade
    assert trade.buyer_seller_actual_passage_completion_notified is True
    assert entries[buyer_keys[0]].actual_passage_observation_record is not None
    assert entries[seller_keys[0]].actual_passage_observation_record is not None


def test_seller_then_buyer_emits_completion_on_last_buyer():
    world, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    _, notified_first = _pass_visit(node, vehicles, seller_keys[0], outlink)[:2]
    assert notified_first is None
    _, notified_second = _pass_visit(node, vehicles, buyer_keys[0], outlink)[:2]
    assert notified_second is trade
    assert trade.buyer_seller_actual_passage_completion_notified is True


def test_multiple_buyers_notify_only_after_last_buyer_or_seller():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a", "buyer_b"),
            seller_vehicle_names=("seller_a",),
        )
    )
    for buyer_key in buyer_keys:
        _, notified = _pass_visit(node, vehicles, buyer_key, outlink)[:2]
        assert notified is None
    _, notified = _pass_visit(node, vehicles, seller_keys[0], outlink)[:2]
    assert notified is trade


def test_multiple_sellers_notify_only_after_all_complete():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a", "seller_b"),
        )
    )
    _, notified = _pass_visit(node, vehicles, buyer_keys[0], outlink)[:2]
    assert notified is None
    _, notified = _pass_visit(node, vehicles, seller_keys[0], outlink)[:2]
    assert notified is None
    _, notified = _pass_visit(node, vehicles, seller_keys[1], outlink)[:2]
    assert notified is trade


def test_multiple_buyers_and_sellers_notify_when_all_complete():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a", "buyer_b"),
            seller_vehicle_names=("seller_a", "seller_b"),
        )
    )
    visit_order = (
        buyer_keys[0],
        seller_keys[0],
        buyer_keys[1],
        seller_keys[1],
    )
    for visit_key in visit_order[:-1]:
        _, notified = _pass_visit(node, vehicles, visit_key, outlink)[:2]
        assert notified is None
    _, notified = _pass_visit(node, vehicles, visit_order[-1], outlink)[:2]
    assert notified is trade


def test_nonparticipating_unobserved_still_notifies_when_buyer_seller_complete():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    _, notified = _pass_visit(node, vehicles, buyer_keys[0], outlink)[:2]
    assert notified is None
    _, notified = _pass_visit(node, vehicles, seller_keys[0], outlink)[:2]
    assert notified is trade
    assert (
        node.W.order_control_tvt_mp_actual_passage_wait_registry.entries_by_node_name_and_visit_key[
            (node.name, nonpart_keys[0])
        ].wait_status
        is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )


def test_nonparticipating_observed_first_still_notifies_on_last_buyer_or_seller():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    _, notified = _pass_visit(node, vehicles, nonpart_keys[0], outlink)[:2]
    assert notified is None
    _, notified = _pass_visit(node, vehicles, buyer_keys[0], outlink)[:2]
    assert notified is None
    _, notified = _pass_visit(node, vehicles, seller_keys[0], outlink)[:2]
    assert notified is trade


def test_nonparticipating_after_notification_does_not_renotify():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, _ = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    _pass_visit(node, vehicles, buyer_keys[0], outlink)
    _pass_visit(node, vehicles, seller_keys[0], outlink)
    assert trade.buyer_seller_actual_passage_completion_notified is True
    _, notified = _pass_visit(node, vehicles, nonpart_keys[0], outlink)[:2]
    assert notified is None
    assert trade.buyer_seller_actual_passage_completion_notified is True


def test_prepare_leaves_live_state_unchanged_before_commit():
    _, node, outlink, trade, buyer_keys, _, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    visit_key = buyer_keys[0]
    vehicle = vehicles[visit_key]
    entry = entries[visit_key]
    log_before = vehicle.order_exchange_log
    status_before = entry.wait_status
    record_before = entry.actual_passage_observation_record
    flag_before = trade.buyer_seller_actual_passage_completion_notified
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    entries_before = registry.entries_by_node_name_and_visit_key
    trades_before = registry.trades_by_transaction_key
    prepared = prepare_tvt_mp_actual_passage_observation(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
    )
    assert prepared is not None
    assert vehicle.order_exchange_log is log_before
    assert entry.wait_status is status_before
    assert entry.actual_passage_observation_record is record_before
    assert trade.buyer_seller_actual_passage_completion_notified is flag_before
    assert registry.entries_by_node_name_and_visit_key is entries_before
    assert registry.trades_by_transaction_key is trades_before


def test_commit_applies_record_and_flag_in_same_successful_commit():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    _pass_visit(node, vehicles, buyer_keys[0], outlink)
    prepared, notified = _pass_visit(node, vehicles, seller_keys[0], outlink)[:2]
    assert notified is trade
    seller_entry = entries[seller_keys[0]]
    assert seller_entry.actual_passage_observation_record is (
        prepared.actual_passage_observation_record
    )
    assert trade.buyer_seller_actual_passage_completion_notified is True


def test_prepare_rejects_missing_trade_wait():
    world = _observation_world()
    node, vehicle, visit_key, outlink, entry, _trade = _register_waiting_entry(
        world,
        node_name="node_a",
        vehicle_name="buyer",
        role=OrderControlTvtMpActualPassageRole.BUYER,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        baseline_minus_candidate=_COPIED_BASELINE_MINUS_CANDIDATE,
        log=["old"],
        attach_minimal_formal_trade=False,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.trades_by_transaction_key.clear()
    _assert_prepare_rejects(
        node,
        vehicle,
        visit_key,
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_empty_buyer_visit_keys():
    world, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.buyer_visit_keys = ()
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_empty_seller_visit_keys():
    world, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.seller_visit_keys = ()
    vehicle = vehicles[seller_keys[0]]
    entry = entries[seller_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        seller_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_missing_buyer_wait_entry():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    del registry.entries_by_node_name_and_visit_key[(node.name, buyer_keys[0])]
    vehicle = vehicles[seller_keys[0]]
    entry = entries[seller_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        seller_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_missing_seller_wait_entry():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    del registry.entries_by_node_name_and_visit_key[(node.name, seller_keys[0])]
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_buyer_role_mismatch():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    entries[buyer_keys[0]].role = OrderControlTvtMpActualPassageRole.SELLER
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_seller_role_mismatch():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    entries[seller_keys[0]].role = OrderControlTvtMpActualPassageRole.BUYER
    vehicle = vehicles[seller_keys[0]]
    entry = entries[seller_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        seller_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_duplicate_visit_key_across_buyer_and_seller():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.seller_visit_keys = (buyer_keys[0],)
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def _assert_prepare_rejects_for_buyer_passage(
    node,
    outlink,
    buyer_keys,
    vehicles,
    entries,
):
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_duplicate_visit_key_within_buyer_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.buyer_visit_keys = (buyer_keys[0], buyer_keys[0])
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_duplicate_visit_key_within_seller_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.seller_visit_keys = (seller_keys[0], seller_keys[0])
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_duplicate_visit_key_within_nonparticipating_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    trade.nonparticipating_visit_keys = (nonpart_keys[0], nonpart_keys[0])
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_duplicate_visit_key_across_buyer_and_nonparticipating():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    trade.nonparticipating_visit_keys = (buyer_keys[0],)
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_duplicate_visit_key_across_seller_and_nonparticipating():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    trade.nonparticipating_visit_keys = (seller_keys[0],)
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_duplicate_visit_key_within_all_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.all_visit_keys = (
        buyer_keys[0],
        seller_keys[0],
        buyer_keys[0],
    )
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_buyer_visit_key_missing_from_all_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.all_visit_keys = (seller_keys[0],)
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_seller_visit_key_missing_from_all_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.all_visit_keys = (buyer_keys[0],)
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_nonparticipating_visit_key_missing_from_all_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    trade.all_visit_keys = (buyer_keys[0], seller_keys[0])
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_unclassified_visit_key_in_all_visit_keys():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    orphan_visit_key = _sample_visit_key("orphan_vehicle", 99)
    trade.all_visit_keys = (
        buyer_keys[0],
        seller_keys[0],
        orphan_visit_key,
    )
    _assert_prepare_rejects_for_buyer_passage(
        node, outlink, buyer_keys, vehicles, entries
    )


def test_prepare_rejects_transaction_identity_mismatch():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.tvt_decision_timestep = trade.tvt_decision_timestep + 1
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_observed_status_without_record():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    peer_entry = entries[seller_keys[0]]
    peer_entry.wait_status = (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_waiting_status_with_existing_record():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    peer_entry = entries[seller_keys[0]]
    peer_entry.actual_passage_observation_record = (
        OrderControlTvtMpActualPassageObservationRecord(
            **_base_observation_record_kwargs(
                seller_keys[0],
                OrderControlTvtMpActualPassageRole.SELLER,
                OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED,
                actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
                actual_route_next_link_name="link_actual",
                baseline_minus_actual_passage_timesteps=-2,
                baseline_minus_actual_passage_seconds=-120,
                baseline_minus_actual_time_value=-60.0,
                candidate_minus_actual_passage_timesteps=-4,
                candidate_minus_actual_passage_seconds=-240,
                candidate_minus_actual_time_value=-120.0,
            )
        )
    )
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_completion_flag_true_when_passing_buyer_still_incomplete_on_live():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    trade.buyer_seller_actual_passage_completion_notified = True
    vehicle = vehicles[buyer_keys[0]]
    entry = entries[buyer_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        buyer_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_completion_flag_true_when_passing_seller_would_complete_all():
    _, node, outlink, trade, buyer_keys, seller_keys, _, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
        )
    )
    _pass_visit(node, vehicles, buyer_keys[0], outlink)
    trade.buyer_seller_actual_passage_completion_notified = True
    vehicle = vehicles[seller_keys[0]]
    entry = entries[seller_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        seller_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def test_prepare_rejects_nonparticipating_when_flag_false_but_buyer_seller_complete():
    _, node, outlink, trade, buyer_keys, seller_keys, nonpart_keys, vehicles, entries = (
        _create_formal_trade_with_entries(
            buyer_vehicle_names=("buyer_a",),
            seller_vehicle_names=("seller_a",),
            nonpart_vehicle_name="watcher",
        )
    )
    _pass_visit(node, vehicles, buyer_keys[0], outlink)
    _pass_visit(node, vehicles, seller_keys[0], outlink)
    trade.buyer_seller_actual_passage_completion_notified = False
    vehicle = vehicles[nonpart_keys[0]]
    entry = entries[nonpart_keys[0]]
    _assert_prepare_rejects(
        node,
        vehicle,
        nonpart_keys[0],
        outlink,
        _PREPARE_ACTUAL_TIMESTEP,
        entry,
    )


def _history_record_kwargs(**changes):
    values = {
        "visit_key": ("history_car", 1),
        "actual_passage_timestep": 10,
        "actual_route_next_link_name": "out",
        "actual_node_passage_rank": 1,
    }
    values.update(changes)
    return values


def _confirmed_history_world(name, vehicle_name="history_car", visit_id=1):
    world = _world(name)
    vehicle = _place(world, vehicle_name, "in_a", visit_id=visit_id)
    _confirm(world, [vehicle])
    node = _junction(world)
    outlink = world.get_link("out")
    visit_key = (vehicle_name, visit_id)
    return world, node, vehicle, outlink, visit_key


def test_node_passage_record_is_frozen_and_has_four_required_fields():
    fields = dataclasses.fields(OrderControlTvtMpActualNodePassageRecord)
    assert [field.name for field in fields] == [
        "visit_key",
        "actual_passage_timestep",
        "actual_route_next_link_name",
        "actual_node_passage_rank",
    ]
    for field in fields:
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
    record = OrderControlTvtMpActualNodePassageRecord(
        ("history_car", 1),
        10,
        "out",
        1,
    )
    assert record.visit_key == ("history_car", 1)
    assert record.actual_passage_timestep == 10
    assert record.actual_route_next_link_name == "out"
    assert record.actual_node_passage_rank == 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.actual_node_passage_rank = 2
    same_timestep = OrderControlTvtMpActualNodePassageRecord(
        ("other_car", 1),
        10,
        "out_b",
        2,
    )
    assert record.actual_passage_timestep == same_timestep.actual_passage_timestep
    assert "node_name" not in record.__dataclass_fields__
    assert "vehicle_name" not in record.__dataclass_fields__
    assert "role" not in record.__dataclass_fields__
    saved = dataclasses.asdict(record)
    assert set(saved) == {
        "visit_key",
        "actual_passage_timestep",
        "actual_route_next_link_name",
        "actual_node_passage_rank",
    }


def test_node_passage_record_rejects_a_bad_shape():
    rejected = []
    cases = [
        ("empty vehicle name", _history_record_kwargs(visit_key=("", 1))),
        ("visit id zero", _history_record_kwargs(visit_key=("history_car", 0))),
        ("visit id bool", _history_record_kwargs(visit_key=("history_car", True))),
        ("visit key not a tuple", _history_record_kwargs(visit_key="history_car")),
        ("short visit key", _history_record_kwargs(visit_key=("history_car",))),
        ("bool timestep", _history_record_kwargs(actual_passage_timestep=True)),
        ("negative timestep", _history_record_kwargs(actual_passage_timestep=-1)),
        ("empty route", _history_record_kwargs(actual_route_next_link_name="")),
        ("non-string route", _history_record_kwargs(actual_route_next_link_name=1)),
        ("bool rank", _history_record_kwargs(actual_node_passage_rank=True)),
        ("zero rank", _history_record_kwargs(actual_node_passage_rank=0)),
        ("negative rank", _history_record_kwargs(actual_node_passage_rank=-1)),
    ]
    for label, kwargs in cases:
        try:
            OrderControlTvtMpActualNodePassageRecord(**kwargs)
        except RuntimeError:
            continue
        rejected.append(label)
    assert rejected == []
    rank_one = OrderControlTvtMpActualNodePassageRecord(
        **_history_record_kwargs(actual_node_passage_rank=1)
    )
    assert rank_one.actual_node_passage_rank == 1


def test_node_passage_history_registry_keeps_per_node_tuples():
    registry = OrderControlTvtMpActualNodePassageHistoryRegistry()
    assert registry.records_by_node_name == {}
    assert registry.records_by_node_name.get("missing", ()) == ()
    assert [
        field.name
        for field in dataclasses.fields(OrderControlTvtMpActualNodePassageHistoryRegistry)
    ] == ["records_by_node_name"]
    other = OrderControlTvtMpActualNodePassageHistoryRegistry()
    assert other.records_by_node_name is not registry.records_by_node_name
    wait_registry = OrderControlTvtMpActualPassageWaitRegistry()
    assert type(registry) is not type(wait_registry)
    assert registry is not wait_registry


def test_world_initializes_independent_node_passage_history_registries():
    world_a = World(
        name="history_world_a",
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=0,
    )
    world_b = World(
        name="history_world_b",
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=1,
    )
    history_a = world_a.order_control_tvt_mp_actual_node_passage_history_registry
    history_b = world_b.order_control_tvt_mp_actual_node_passage_history_registry
    assert isinstance(history_a, OrderControlTvtMpActualNodePassageHistoryRegistry)
    assert isinstance(history_b, OrderControlTvtMpActualNodePassageHistoryRegistry)
    assert history_a.records_by_node_name == {}
    assert history_b.records_by_node_name == {}
    assert history_a is not history_b
    assert history_a is not world_a.order_control_tvt_mp_actual_passage_wait_registry
    assert type(history_a) is not type(
        world_a.order_control_tvt_mp_actual_passage_wait_registry
    )
    history_a.records_by_node_name["junction"] = ()
    assert history_b.records_by_node_name == {}
    fork = world_a.copy()
    fork_history = fork.order_control_tvt_mp_actual_node_passage_history_registry
    assert isinstance(fork_history, OrderControlTvtMpActualNodePassageHistoryRegistry)
    assert fork_history is not history_a
    assert fork_history.records_by_node_name == {"junction": ()}


def test_prepare_node_passage_history_keeps_live_state_until_commit():
    world, node, vehicle, outlink, visit_key = _confirmed_history_world(
        "history_prepare_ok",
    )
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    rank_state = world.order_control_tvt_rank_states_by_node_name["junction"]
    link_before = vehicle.link
    prepared = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    assert prepared.node_name == "junction"
    assert prepared.record.visit_key == visit_key
    assert prepared.record.actual_passage_timestep == world.T
    assert prepared.record.actual_route_next_link_name == "out"
    assert prepared.record.actual_node_passage_rank == 1
    assert prepared.updated_node_records == (prepared.record,)
    assert registry.records_by_node_name == {}
    assert vehicle.link is link_before
    assert rank_state.assigned_rank(visit_key) == 1
    assert rank_state.formal_route_next_link_name(visit_key) is None
    by_name = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle.name,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    assert by_name.record.actual_node_passage_rank == 1
    assert registry.records_by_node_name == {}


def test_prepare_node_passage_history_uses_existing_length_plus_one():
    world, node, vehicle, outlink, visit_key = _confirmed_history_world(
        "history_rank_two",
    )
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    first = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    commit_tvt_mp_actual_node_passage_history(first)
    rank_state = world.order_control_tvt_rank_states_by_node_name["junction"]
    second_vehicle = _place(world, "second_car", "in_b", visit_id=2)
    rank_state.register_undetermined_visit(("second_car", 2))
    rank_state.confirm_visits_in_order([("second_car", 2)])
    second_outlink = world.get_link("out")
    prepared = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=second_vehicle,
        visit_key=("second_car", 2),
        actual_outlink=second_outlink,
        actual_passage_timestep=world.T,
    )
    assert prepared.record.actual_node_passage_rank == 2
    assert len(registry.records_by_node_name["junction"]) == 1
    commit_tvt_mp_actual_node_passage_history(prepared)
    records = registry.records_by_node_name["junction"]
    assert isinstance(records, tuple)
    assert [record.actual_node_passage_rank for record in records] == [1, 2]
    assert records[0].visit_key == ("history_car", 1)
    assert records[1].visit_key == ("second_car", 2)


def test_prepare_node_passage_history_separates_nodes_and_visit_keys():
    world, node, vehicle, outlink, visit_key = _confirmed_history_world(
        "history_separate",
    )
    world.addNode("dest_b", 4, 0)
    world.addNode(
        "junction_b",
        3,
        0,
        order_control_type="time_value",
        order_control_eligible=True,
    )
    world.addLink(
        "out_b",
        "junction_b",
        "dest_b",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    node_b = world.get_node("junction_b")
    rank_state_b = OrderControlTvtNodeRankState("junction_b")
    rank_state_b.register_undetermined_visit(visit_key)
    rank_state_b.confirm_visits_in_order([visit_key])
    world.order_control_tvt_rank_states_by_node_name["junction_b"] = rank_state_b
    first = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    commit_tvt_mp_actual_node_passage_history(first)
    second = prepare_tvt_mp_actual_node_passage_history(
        node=node_b,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=world.get_link("out_b"),
        actual_passage_timestep=world.T,
    )
    assert second.record.actual_node_passage_rank == 1
    assert second.record.visit_key == visit_key
    commit_tvt_mp_actual_node_passage_history(second)
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    assert registry.records_by_node_name["junction"][0].actual_node_passage_rank == 1
    assert registry.records_by_node_name["junction_b"][0].actual_node_passage_rank == 1

    rank_state = world.order_control_tvt_rank_states_by_node_name["junction"]
    revisit_key = ("history_car", 2)
    rank_state.register_undetermined_visit(revisit_key)
    rank_state.confirm_visits_in_order([revisit_key])
    revisit = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle,
        visit_key=revisit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    assert revisit.record.actual_node_passage_rank == 2
    assert revisit.record.visit_key[0] == visit_key[0]
    assert revisit.record.visit_key != visit_key


def test_prepare_node_passage_history_rejects_bad_live_inputs():
    world, node, vehicle, outlink, visit_key = _confirmed_history_world(
        "history_prepare_reject",
    )
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    loose_world = _world("history_unconfirmed")
    loose = _place(loose_world, "loose_car", "in_a", visit_id=1)
    _register_only(loose_world, [loose])
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=_junction(loose_world),
            vehicle=loose,
            visit_key=("loose_car", 1),
            actual_outlink=loose_world.get_link("out"),
            actual_passage_timestep=loose_world.T,
        )
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=("other_car", 1),
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T - 1,
        )
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=world.get_link("side"),
            actual_passage_timestep=world.T,
        )
    world.order_control_tvt_mp_actual_node_passage_history_registry = (
        world.order_control_tvt_mp_actual_passage_wait_registry
    )
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )
    world.order_control_tvt_mp_actual_node_passage_history_registry = registry
    registry.records_by_node_name["junction"] = []
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )
    broken_rank = OrderControlTvtMpActualNodePassageRecord(
        ("earlier_car", 1),
        0,
        "out",
        2,
    )
    registry.records_by_node_name["junction"] = (broken_rank,)
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )
    duplicate_a = OrderControlTvtMpActualNodePassageRecord(
        ("earlier_car", 1),
        0,
        "out",
        1,
    )
    duplicate_b = OrderControlTvtMpActualNodePassageRecord(
        ("earlier_car", 1),
        1,
        "out",
        2,
    )
    registry.records_by_node_name["junction"] = (duplicate_a, duplicate_b)
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )
    registry.records_by_node_name["junction"] = (
        OrderControlTvtMpActualNodePassageRecord(visit_key, 0, "out", 1),
    )
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )
    assert vehicle.link.name == "in_a"
    assert registry.records_by_node_name["junction"][0].visit_key == visit_key
    _as_fork(world)
    with pytest.raises(RuntimeError):
        prepare_tvt_mp_actual_node_passage_history(
            node=node,
            vehicle=vehicle,
            visit_key=visit_key,
            actual_outlink=outlink,
            actual_passage_timestep=world.T,
        )


def test_commit_node_passage_history_assigns_prepared_values_only():
    world, node, vehicle, outlink, visit_key = _confirmed_history_world(
        "history_commit",
    )
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    other = OrderControlTvtMpActualNodePassageRecord(
        ("other_node_car", 1),
        3,
        "side",
        1,
    )
    registry.records_by_node_name["other_node"] = (other,)
    prepared = prepare_tvt_mp_actual_node_passage_history(
        node=node,
        vehicle=vehicle,
        visit_key=visit_key,
        actual_outlink=outlink,
        actual_passage_timestep=world.T,
    )
    rank_state = world.order_control_tvt_rank_states_by_node_name["junction"]

    def fail_if_called(*args, **kwargs):
        raise AssertionError("commit searched the rank ledger")

    rank_state.is_confirmed = fail_if_called
    world.T = 99
    commit_source = inspect.getsource(commit_tvt_mp_actual_node_passage_history)
    assert "sort(" not in commit_source
    assert "is_confirmed" not in commit_source
    assert "assigned_rank" not in commit_source
    assert "OrderControlTvtMpActualNodePassageRecord(" not in commit_source
    commit_tvt_mp_actual_node_passage_history(prepared)
    stored = registry.records_by_node_name["junction"]
    assert isinstance(stored, tuple)
    assert stored[0] is prepared.record
    assert stored[0].actual_passage_timestep == 10
    assert stored[0].actual_node_passage_rank == 1
    assert registry.records_by_node_name["other_node"] == (other,)
    late = OrderControlTvtMpActualNodePassageRecord(("z_car", 1), 20, "out", 1)
    early = OrderControlTvtMpActualNodePassageRecord(("a_car", 1), 5, "out", 2)
    unsorted = _PreparedTvtMpActualNodePassageHistoryUpdate(
        registry=registry,
        node_name="unsorted_node",
        record=early,
        updated_node_records=(late, early),
    )
    commit_tvt_mp_actual_node_passage_history(unsorted)
    assert registry.records_by_node_name["unsorted_node"] == (late, early)
    assert registry.records_by_node_name["unsorted_node"][0] is late
    with pytest.raises(RuntimeError):
        commit_tvt_mp_actual_node_passage_history(prepared.record)
