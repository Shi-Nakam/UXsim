import dataclasses

import pytest

from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitRegistry,
    OrderControlTvtMpActualPassageWaitStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.uxsim import World

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
        "buyers_sorted": ("buyer_1",),
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


def test_wait_entry_wait_status_is_mutable():
    visit_key = _sample_visit_key("veh_wait", 0)
    entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=1,
        node_name="n",
        buyers_sorted=("b",),
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
    )
    entry.wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    assert (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )


def test_trade_wait_notification_flag_is_mutable():
    buyer_key = _sample_visit_key("buyer_v", 0)
    seller_key = _sample_visit_key("seller_v", 0)
    nonpart_key = _sample_visit_key("other_v", 0)
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=3,
        node_name="node_trade",
        buyers_sorted=("buyer_a",),
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
        buyers_sorted=("b1",),
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
        buyers_sorted=("x",),
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
    )
    key = (node_name, visit_key)
    registry.entries_by_node_name_and_visit_key[key] = entry
    assert registry.entries_by_node_name_and_visit_key[key] is entry


def test_registry_trade_mapping_uses_transaction_key():
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    transaction_key = (20, "trade_node", ("buyer_z", "buyer_y"))
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=20,
        node_name="trade_node",
        buyers_sorted=("buyer_z", "buyer_y"),
        all_visit_keys=(),
        buyer_visit_keys=(),
        seller_visit_keys=(),
        nonparticipating_visit_keys=(),
    )
    registry.trades_by_transaction_key[transaction_key] = trade
    assert registry.trades_by_transaction_key[transaction_key] is trade
