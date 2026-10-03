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
    commit_tvt_mp_actual_passage_observation,
    prepare_tvt_mp_actual_passage_observation,
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
