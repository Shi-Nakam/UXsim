import dataclasses
import copy
import inspect
from pathlib import Path

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
    OrderControlTvtMpBuyerIndividualExPostEvaluationRecord,
    OrderControlTvtMpBuyerSatisfactionReason,
    OrderControlTvtMpIndividualExPostEvaluationResult,
    OrderControlTvtMpIndividualSatisfactionStatus,
    OrderControlTvtMpSellerIndividualExPostEvaluationRecord,
    OrderControlTvtMpSellerSatisfactionReason,
    OrderControlTvtMpTradeExPostEvaluationStatus,
    commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization,
    commit_tvt_mp_trade_ex_post_evaluation,
    prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization,
    prepare_tvt_mp_individual_ex_post_evaluation,
    prepare_tvt_mp_trade_ex_post_evaluation,
    commit_tvt_mp_individual_ex_post_evaluation,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRouteOrigin,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.uxsim import World

_REPO_ROOT = Path(__file__).resolve().parent

_EVALUATION_END_TIMESTEP = 9
_EVALUATION_END_WORLD_T = 10
_EVALUATION_END_TSIZE = 40
_PREPARE_DECISION_TIMESTEP = 10
_PREPARE_ACTUAL_TIMESTEP = 12
_PREPARE_BASELINE_PASSAGE_TIMESTEP = 10
_PREPARE_CANDIDATE_PASSAGE_TIMESTEP = 8
_COPIED_BASELINE_MINUS_CANDIDATE = (41, 42, 43)
_TEST_TRUE_VOT_PER_SECOND = 0.5
_NODE_NAME = "node_a"
_DELTAT_SECONDS = 60
_ROUTE_ORIGIN = OrderControlTvtMpLocalBindingRouteOrigin.RANK_LEDGER_FORMAL_ROUTE


def _field_names(cls):
    names = []
    for field in dataclasses.fields(cls):
        names.append(field.name)
    return names


def _visit_key(vehicle_name: str, visit_id: int = 1) -> OrderControlTvtVisitKey:
    return (vehicle_name, visit_id)


def _buyer_record(
    vehicle_name: str,
    *,
    visit_id: int = 1,
    realized_time_value: int | float,
    official_payment: int | float,
    satisfaction_status: OrderControlTvtMpIndividualSatisfactionStatus,
    satisfaction_reason: OrderControlTvtMpBuyerSatisfactionReason,
    official_payment_per_saved_second: int | float | None,
) -> OrderControlTvtMpBuyerIndividualExPostEvaluationRecord:
    visit_key = _visit_key(vehicle_name, visit_id)
    realized_gain = realized_time_value - official_payment
    return OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
        visit_key=visit_key,
        vehicle_name=vehicle_name,
        realized_time_value=realized_time_value,
        official_payment=official_payment,
        realized_gain=realized_gain,
        satisfaction_status=satisfaction_status,
        satisfaction_reason=satisfaction_reason,
        official_payment_per_saved_second=official_payment_per_saved_second,
    )


def _seller_record(
    vehicle_name: str,
    *,
    visit_id: int = 1,
    realized_delay_loss: int | float,
    official_compensation: int | float,
    satisfaction_status: OrderControlTvtMpIndividualSatisfactionStatus,
    satisfaction_reason: OrderControlTvtMpSellerSatisfactionReason,
    official_compensation_per_delayed_second: int | float | None,
) -> OrderControlTvtMpSellerIndividualExPostEvaluationRecord:
    visit_key = _visit_key(vehicle_name, visit_id)
    realized_gain = official_compensation - realized_delay_loss
    return OrderControlTvtMpSellerIndividualExPostEvaluationRecord(
        visit_key=visit_key,
        vehicle_name=vehicle_name,
        realized_delay_loss=realized_delay_loss,
        official_compensation=official_compensation,
        realized_gain=realized_gain,
        satisfaction_status=satisfaction_status,
        satisfaction_reason=satisfaction_reason,
        official_compensation_per_delayed_second=(
            official_compensation_per_delayed_second
        ),
    )


def _individual_result_kwargs(
    *,
    status: OrderControlTvtMpTradeExPostEvaluationStatus,
    buyer_records,
    seller_records,
    buyers_sorted=None,
):
    if buyers_sorted is None:
        buyers_sorted = (_visit_key("buyer_a"),)
    return {
        "tvt_decision_timestep": 5,
        "node_name": "junction_a",
        "buyers_sorted": buyers_sorted,
        "trade_ex_post_evaluation_status": status,
        "buyer_evaluation_records": buyer_records,
        "seller_evaluation_records": seller_records,
    }


def test_individual_satisfaction_status_enum_members_and_values():
    status = OrderControlTvtMpIndividualSatisfactionStatus
    assert status.SATISFIED.value == "satisfied"
    assert status.UNSATISFIED.value == "unsatisfied"
    names = []
    values = []
    for member in status:
        names.append(member.name)
        values.append(member.value)
    assert names == ["SATISFIED", "UNSATISFIED"]
    assert values == ["satisfied", "unsatisfied"]
    assert len(names) == 2


def test_buyer_satisfaction_reason_enum_members_and_values():
    reason = OrderControlTvtMpBuyerSatisfactionReason
    assert (
        reason.TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE.value
        == "trivially_unsatisfied_nonpositive_realized_time_value"
    )
    assert (
        reason.UNSATISFIED_BY_HIGH_PAYMENT_RATE.value
        == "unsatisfied_by_high_payment_rate"
    )
    assert (
        reason.SATISFIED_APPROPRIATE_PAYMENT_RATE.value
        == "satisfied_appropriate_payment_rate"
    )
    names = []
    values = []
    for member in reason:
        names.append(member.name)
        values.append(member.value)
    assert names == [
        "TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE",
        "UNSATISFIED_BY_HIGH_PAYMENT_RATE",
        "SATISFIED_APPROPRIATE_PAYMENT_RATE",
    ]
    assert values == [
        "trivially_unsatisfied_nonpositive_realized_time_value",
        "unsatisfied_by_high_payment_rate",
        "satisfied_appropriate_payment_rate",
    ]
    assert len(names) == 3


def test_seller_satisfaction_reason_enum_members_and_values():
    reason = OrderControlTvtMpSellerSatisfactionReason
    assert (
        reason.TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY.value
        == "trivially_satisfied_nonpositive_actual_delay"
    )
    assert (
        reason.UNSATISFIED_INSUFFICIENT_COMPENSATION_RATE.value
        == "unsatisfied_insufficient_compensation_rate"
    )
    assert (
        reason.SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE.value
        == "satisfied_by_sufficient_compensation_rate"
    )
    names = []
    values = []
    for member in reason:
        names.append(member.name)
        values.append(member.value)
    assert names == [
        "TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY",
        "UNSATISFIED_INSUFFICIENT_COMPENSATION_RATE",
        "SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE",
    ]
    assert values == [
        "trivially_satisfied_nonpositive_actual_delay",
        "unsatisfied_insufficient_compensation_rate",
        "satisfied_by_sufficient_compensation_rate",
    ]
    assert len(names) == 3


def test_buyer_individual_record_is_frozen_with_expected_field_order():
    fields = dataclasses.fields(OrderControlTvtMpBuyerIndividualExPostEvaluationRecord)
    assert _field_names(OrderControlTvtMpBuyerIndividualExPostEvaluationRecord) == [
        "visit_key",
        "vehicle_name",
        "realized_time_value",
        "official_payment",
        "realized_gain",
        "satisfaction_status",
        "satisfaction_reason",
        "official_payment_per_saved_second",
    ]
    for field in fields:
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
    record = _buyer_record(
        "buyer_a",
        realized_time_value=10.0,
        official_payment=3.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.5,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.realized_gain = 0.0


@pytest.mark.parametrize("realized_time_value", [-2.0, 0.0, 4.0])
def test_buyer_record_allows_negative_zero_and_positive_realized_time_value(
    realized_time_value,
):
    if realized_time_value <= 0:
        record = _buyer_record(
            "buyer_a",
            realized_time_value=realized_time_value,
            official_payment=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )
    else:
        record = _buyer_record(
            "buyer_a",
            realized_time_value=realized_time_value,
            official_payment=1.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .SATISFIED_APPROPRIATE_PAYMENT_RATE
            ),
            official_payment_per_saved_second=0.25,
        )
    assert record.realized_time_value == realized_time_value


def test_buyer_record_allows_zero_and_positive_official_payment():
    zero_payment = _buyer_record(
        "buyer_a",
        realized_time_value=0.0,
        official_payment=0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason
            .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
        ),
        official_payment_per_saved_second=None,
    )
    assert zero_payment.official_payment == 0
    positive_payment = _buyer_record(
        "buyer_a",
        realized_time_value=5.0,
        official_payment=2.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.4,
    )
    assert positive_payment.official_payment == 2.0


def test_buyer_record_realized_gain_formula_exact_match():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=100.0,
        official_payment=40.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=2.0,
    )
    assert record.realized_gain == 60.0


def test_buyer_positive_realized_gain_requires_satisfied():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=10.0,
        official_payment=2.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.5,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )


def test_buyer_zero_realized_gain_requires_unsatisfied():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=5.0,
        official_payment=5.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.UNSATISFIED_BY_HIGH_PAYMENT_RATE
        ),
        official_payment_per_saved_second=1.0,
    )
    assert record.realized_gain == 0
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
    )


def test_buyer_negative_realized_gain_requires_unsatisfied():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=3.0,
        official_payment=8.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.UNSATISFIED_BY_HIGH_PAYMENT_RATE
        ),
        official_payment_per_saved_second=4.0,
    )
    assert record.realized_gain == -5.0


def test_buyer_trivial_reason_contract():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=0.0,
        official_payment=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason
            .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
        ),
        official_payment_per_saved_second=None,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
    )
    assert record.realized_time_value <= 0
    assert record.official_payment_per_saved_second is None


def test_buyer_high_payment_reason_contract():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=8.0,
        official_payment=8.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.UNSATISFIED_BY_HIGH_PAYMENT_RATE
        ),
        official_payment_per_saved_second=2.0,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
    )
    assert record.realized_time_value > 0
    assert record.official_payment_per_saved_second == 2.0


def test_buyer_appropriate_payment_reason_contract():
    record = _buyer_record(
        "buyer_a",
        realized_time_value=10.0,
        official_payment=4.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.5,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )
    assert record.realized_time_value > 0
    assert record.official_payment_per_saved_second == 0.5


def test_buyer_record_rejects_status_reason_mismatch():
    with pytest.raises(RuntimeError, match="TRIVIALLY_UNSATISFIED"):
        _buyer_record(
            "buyer_a",
            realized_time_value=10.0,
            official_payment=2.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )


def test_buyer_record_rejects_trivial_reason_with_numeric_rate():
    with pytest.raises(RuntimeError, match="official_payment_per_saved_second"):
        _buyer_record(
            "buyer_a",
            realized_time_value=-1.0,
            official_payment=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=1.0,
        )


def test_buyer_record_rejects_high_payment_reason_with_none_rate():
    with pytest.raises(RuntimeError, match="official_payment_per_saved_second"):
        _buyer_record(
            "buyer_a",
            realized_time_value=5.0,
            official_payment=5.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason.UNSATISFIED_BY_HIGH_PAYMENT_RATE
            ),
            official_payment_per_saved_second=None,
        )


@pytest.mark.parametrize(
    "bad_value",
    [True, float("nan"), float("inf"), float("-inf")],
)
def test_buyer_record_rejects_non_finite_or_bool_numeric_fields(bad_value):
    with pytest.raises(RuntimeError):
        _buyer_record(
            "buyer_a",
            realized_time_value=bad_value,
            official_payment=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )


def test_buyer_record_rejects_negative_official_payment():
    with pytest.raises(RuntimeError, match="official_payment"):
        _buyer_record(
            "buyer_a",
            realized_time_value=1.0,
            official_payment=-0.01,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )


def test_buyer_record_rejects_inconsistent_realized_gain():
    visit_key = _visit_key("buyer_a")
    with pytest.raises(RuntimeError, match="realized_gain must equal"):
        OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="buyer_a",
            realized_time_value=10.0,
            official_payment=2.0,
            realized_gain=999.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .SATISFIED_APPROPRIATE_PAYMENT_RATE
            ),
            official_payment_per_saved_second=0.5,
        )


def test_buyer_record_rejects_visit_key_vehicle_name_mismatch():
    visit_key = _visit_key("buyer_a")
    with pytest.raises(RuntimeError, match="does not match"):
        OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="other_name",
            realized_time_value=0.0,
            official_payment=0.0,
            realized_gain=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )


def test_buyer_record_rejects_empty_vehicle_name():
    visit_key = _visit_key("buyer_a")
    with pytest.raises(RuntimeError, match="vehicle_name"):
        OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="",
            realized_time_value=0.0,
            official_payment=0.0,
            realized_gain=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )


def test_buyer_record_rejects_invalid_satisfaction_status_type():
    visit_key = _visit_key("buyer_a")
    with pytest.raises(RuntimeError, match="satisfaction_status"):
        OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="buyer_a",
            realized_time_value=0.0,
            official_payment=0.0,
            realized_gain=0.0,
            satisfaction_status="SATISFIED",
            satisfaction_reason=(
                OrderControlTvtMpBuyerSatisfactionReason
                .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
            ),
            official_payment_per_saved_second=None,
        )


def test_buyer_record_rejects_invalid_satisfaction_reason_type():
    visit_key = _visit_key("buyer_a")
    with pytest.raises(RuntimeError, match="satisfaction_reason"):
        OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="buyer_a",
            realized_time_value=0.0,
            official_payment=0.0,
            realized_gain=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
            ),
            satisfaction_reason="trivial",
            official_payment_per_saved_second=None,
        )


def test_seller_individual_record_is_frozen_with_expected_field_order():
    assert _field_names(OrderControlTvtMpSellerIndividualExPostEvaluationRecord) == [
        "visit_key",
        "vehicle_name",
        "realized_delay_loss",
        "official_compensation",
        "realized_gain",
        "satisfaction_status",
        "satisfaction_reason",
        "official_compensation_per_delayed_second",
    ]
    for field in dataclasses.fields(
        OrderControlTvtMpSellerIndividualExPostEvaluationRecord
    ):
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


@pytest.mark.parametrize("realized_delay_loss", [-3.0, 0.0, 6.0])
def test_seller_record_allows_negative_zero_and_positive_delay_loss(
    realized_delay_loss,
):
    if realized_delay_loss <= 0:
        record = _seller_record(
            "seller_a",
            realized_delay_loss=realized_delay_loss,
            official_compensation=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
            ),
            official_compensation_per_delayed_second=None,
        )
    else:
        record = _seller_record(
            "seller_a",
            realized_delay_loss=realized_delay_loss,
            official_compensation=10.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
            ),
            official_compensation_per_delayed_second=2.0,
        )
    assert record.realized_delay_loss == realized_delay_loss


def test_seller_record_allows_zero_and_positive_official_compensation():
    zero_comp = _seller_record(
        "seller_a",
        realized_delay_loss=0.0,
        official_compensation=0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
        ),
        official_compensation_per_delayed_second=None,
    )
    assert zero_comp.official_compensation == 0
    positive_comp = _seller_record(
        "seller_a",
        realized_delay_loss=2.0,
        official_compensation=5.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=2.5,
    )
    assert positive_comp.official_compensation == 5.0


def test_seller_record_realized_gain_formula_exact_match():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=30.0,
        official_compensation=50.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=1.0,
    )
    assert record.realized_gain == 20.0


def test_seller_positive_realized_gain_requires_satisfied():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=1.0,
        official_compensation=5.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=5.0,
    )
    assert record.realized_gain > 0


def test_seller_zero_realized_gain_requires_satisfied():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=4.0,
        official_compensation=4.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=1.0,
    )
    assert record.realized_gain == 0


def test_seller_negative_realized_gain_requires_unsatisfied():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=10.0,
        official_compensation=3.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .UNSATISFIED_INSUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=0.3,
    )
    assert record.realized_gain < 0


def test_seller_trivial_reason_contract():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=-2.0,
        official_compensation=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
        ),
        official_compensation_per_delayed_second=None,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )
    assert record.official_compensation_per_delayed_second is None


def test_seller_insufficient_reason_contract():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=20.0,
        official_compensation=5.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .UNSATISFIED_INSUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=0.25,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
    )
    assert record.official_compensation_per_delayed_second == 0.25


def test_seller_sufficient_reason_contract():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=10.0,
        official_compensation=15.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=1.5,
    )
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )
    assert record.official_compensation_per_delayed_second == 1.5


def test_seller_true_vot_zero_equivalent_shape():
    record = _seller_record(
        "seller_a",
        realized_delay_loss=0.0,
        official_compensation=3.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=0.0,
    )
    assert record.realized_delay_loss == 0.0
    assert record.official_compensation >= 0
    assert record.realized_gain == record.official_compensation
    assert record.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )
    assert record.satisfaction_reason is (
        OrderControlTvtMpSellerSatisfactionReason
        .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
    )
    assert record.official_compensation_per_delayed_second == 0.0


def test_seller_record_rejects_status_reason_mismatch():
    with pytest.raises(RuntimeError, match="UNSATISFIED_INSUFFICIENT"):
        _seller_record(
            "seller_a",
            realized_delay_loss=5.0,
            official_compensation=10.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .UNSATISFIED_INSUFFICIENT_COMPENSATION_RATE
            ),
            official_compensation_per_delayed_second=2.0,
        )


def test_seller_record_rejects_trivial_reason_with_numeric_rate():
    with pytest.raises(RuntimeError, match="official_compensation_per_delayed_second"):
        _seller_record(
            "seller_a",
            realized_delay_loss=0.0,
            official_compensation=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
            ),
            official_compensation_per_delayed_second=0.0,
        )


@pytest.mark.parametrize(
    "bad_value",
    [True, float("nan"), float("inf")],
)
def test_seller_record_rejects_non_finite_or_bool_numeric_fields(bad_value):
    with pytest.raises(RuntimeError):
        _seller_record(
            "seller_a",
            realized_delay_loss=bad_value,
            official_compensation=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
            ),
            official_compensation_per_delayed_second=None,
        )


def test_seller_record_rejects_negative_official_compensation():
    with pytest.raises(RuntimeError, match="official_compensation"):
        _seller_record(
            "seller_a",
            realized_delay_loss=0.0,
            official_compensation=-1.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
            ),
            official_compensation_per_delayed_second=None,
        )


def test_seller_record_rejects_inconsistent_realized_gain():
    visit_key = _visit_key("seller_a")
    with pytest.raises(RuntimeError, match="realized_gain must equal"):
        OrderControlTvtMpSellerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="seller_a",
            realized_delay_loss=5.0,
            official_compensation=10.0,
            realized_gain=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
            ),
            official_compensation_per_delayed_second=2.0,
        )


def test_seller_record_rejects_visit_key_vehicle_name_mismatch():
    visit_key = _visit_key("seller_a")
    with pytest.raises(RuntimeError, match="does not match"):
        OrderControlTvtMpSellerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="other",
            realized_delay_loss=0.0,
            official_compensation=0.0,
            realized_gain=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
            ),
            official_compensation_per_delayed_second=None,
        )


def test_seller_record_rejects_invalid_satisfaction_status_type():
    visit_key = _visit_key("seller_a")
    with pytest.raises(RuntimeError, match="satisfaction_status"):
        OrderControlTvtMpSellerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="seller_a",
            realized_delay_loss=0.0,
            official_compensation=0.0,
            realized_gain=0.0,
            satisfaction_status="SATISFIED",
            satisfaction_reason=(
                OrderControlTvtMpSellerSatisfactionReason
                .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
            ),
            official_compensation_per_delayed_second=None,
        )


def test_seller_record_rejects_invalid_satisfaction_reason_type():
    visit_key = _visit_key("seller_a")
    with pytest.raises(RuntimeError, match="satisfaction_reason"):
        OrderControlTvtMpSellerIndividualExPostEvaluationRecord(
            visit_key=visit_key,
            vehicle_name="seller_a",
            realized_delay_loss=0.0,
            official_compensation=0.0,
            realized_gain=0.0,
            satisfaction_status=(
                OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
            ),
            satisfaction_reason="sufficient",
            official_compensation_per_delayed_second=None,
        )


def test_individual_result_is_frozen_with_expected_field_order():
    assert _field_names(OrderControlTvtMpIndividualExPostEvaluationResult) == [
        "tvt_decision_timestep",
        "node_name",
        "buyers_sorted",
        "trade_ex_post_evaluation_status",
        "buyer_evaluation_records",
        "seller_evaluation_records",
    ]
    for field in dataclasses.fields(OrderControlTvtMpIndividualExPostEvaluationResult):
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


def test_individual_unavailable_result_requires_both_record_columns_none():
    result = OrderControlTvtMpIndividualExPostEvaluationResult(
        **_individual_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE,
            buyer_records=None,
            seller_records=None,
        )
    )
    assert result.buyer_evaluation_records is None
    assert result.seller_evaluation_records is None


def test_individual_unavailable_rejects_buyer_tuple():
    buyer = _buyer_record(
        "buyer_a",
        realized_time_value=0.0,
        official_payment=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason
            .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
        ),
        official_payment_per_saved_second=None,
    )
    with pytest.raises(RuntimeError, match="buyer_evaluation_records"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=(
                    OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
                ),
                buyer_records=(buyer,),
                seller_records=None,
            )
        )


def test_individual_unavailable_rejects_seller_tuple():
    seller = _seller_record(
        "seller_a",
        realized_delay_loss=0.0,
        official_compensation=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
        ),
        official_compensation_per_delayed_second=None,
    )
    with pytest.raises(RuntimeError, match="seller_evaluation_records"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=(
                    OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
                ),
                buyer_records=None,
                seller_records=(seller,),
            )
        )


def _evaluated_buyer_and_seller_records():
    buyer = _buyer_record(
        "buyer_a",
        realized_time_value=10.0,
        official_payment=4.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.4,
    )
    seller = _seller_record(
        "seller_a",
        realized_delay_loss=5.0,
        official_compensation=8.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=1.6,
    )
    return (buyer,), (seller,)


def test_individual_infeasible_evaluated_shape():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    result = OrderControlTvtMpIndividualExPostEvaluationResult(
        **_individual_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
            buyer_records=buyer_records,
            seller_records=seller_records,
        )
    )
    assert isinstance(result.buyer_evaluation_records, tuple)
    assert isinstance(result.seller_evaluation_records, tuple)


def test_individual_feasible_evaluated_shape():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    result = OrderControlTvtMpIndividualExPostEvaluationResult(
        **_individual_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
            buyer_records=buyer_records,
            seller_records=seller_records,
        )
    )
    assert isinstance(result.buyer_evaluation_records, tuple)
    assert isinstance(result.seller_evaluation_records, tuple)


def test_individual_evaluated_rejects_none_buyer_column():
    _, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="buyer_evaluation_records"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_records=None,
                seller_records=seller_records,
            )
        )


def test_individual_evaluated_rejects_none_seller_column():
    buyer_records, _ = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="seller_evaluation_records"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_records=buyer_records,
                seller_records=None,
            )
        )


def test_individual_result_rejects_buyer_order_mismatch():
    buyer_a = _buyer_record(
        "buyer_a",
        realized_time_value=10.0,
        official_payment=4.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.4,
    )
    buyer_b = _buyer_record(
        "buyer_b",
        visit_id=2,
        realized_time_value=8.0,
        official_payment=2.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.25,
    )
    seller_records = _evaluated_buyer_and_seller_records()[1]
    buyers_sorted = (_visit_key("buyer_b", 2), _visit_key("buyer_a"))
    with pytest.raises(RuntimeError, match="buyers_sorted order"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_records=(buyer_a, buyer_b),
                seller_records=seller_records,
                buyers_sorted=buyers_sorted,
            )
        )


def test_individual_result_rejects_duplicate_buyer_visit_keys():
    buyer_one = _buyer_record(
        "buyer_a",
        realized_time_value=1.0,
        official_payment=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.1,
    )
    buyer_two = _buyer_record(
        "buyer_a",
        realized_time_value=2.0,
        official_payment=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.2,
    )
    seller = _seller_record(
        "seller_a",
        realized_delay_loss=0.0,
        official_compensation=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
        ),
        official_compensation_per_delayed_second=None,
    )
    with pytest.raises(RuntimeError, match="duplicate VisitKey"):
        actual_passage_module._validate_individual_record_visit_keys_no_duplicates_or_overlap(
            (buyer_one, buyer_two),
            (seller,),
        )


def test_individual_result_rejects_duplicate_seller_visit_keys():
    buyer = _buyer_record(
        "buyer_a",
        realized_time_value=1.0,
        official_payment=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.1,
    )
    seller_one = _seller_record(
        "seller_a",
        realized_delay_loss=0.0,
        official_compensation=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
        ),
        official_compensation_per_delayed_second=None,
    )
    seller_two = _seller_record(
        "seller_a",
        realized_delay_loss=1.0,
        official_compensation=2.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
        ),
        official_compensation_per_delayed_second=2.0,
    )
    with pytest.raises(RuntimeError, match="duplicate VisitKey"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_records=(buyer,),
                seller_records=(seller_one, seller_two),
            )
        )


def test_individual_result_rejects_shared_visit_key_between_buyer_and_seller():
    shared_key = _visit_key("shared_vehicle")
    buyer = OrderControlTvtMpBuyerIndividualExPostEvaluationRecord(
        visit_key=shared_key,
        vehicle_name="shared_vehicle",
        realized_time_value=1.0,
        official_payment=0.0,
        realized_gain=1.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpBuyerSatisfactionReason.SATISFIED_APPROPRIATE_PAYMENT_RATE
        ),
        official_payment_per_saved_second=0.1,
    )
    seller = OrderControlTvtMpSellerIndividualExPostEvaluationRecord(
        visit_key=shared_key,
        vehicle_name="shared_vehicle",
        realized_delay_loss=0.0,
        official_compensation=0.0,
        realized_gain=0.0,
        satisfaction_status=OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED,
        satisfaction_reason=(
            OrderControlTvtMpSellerSatisfactionReason
            .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
        ),
        official_compensation_per_delayed_second=None,
    )
    with pytest.raises(RuntimeError, match="must not share"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=1,
            node_name="node_a",
            buyers_sorted=(shared_key,),
            trade_ex_post_evaluation_status=(
                OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
            ),
            buyer_evaluation_records=(buyer,),
            seller_evaluation_records=(seller,),
        )


def test_individual_result_rejects_wrong_buyer_element_type():
    seller_records = _evaluated_buyer_and_seller_records()[1]
    with pytest.raises(RuntimeError, match="OrderControlTvtMpBuyerIndividual"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_records=("not_a_record",),
                seller_records=seller_records,
            )
        )


def test_individual_result_rejects_wrong_seller_element_type():
    buyer_records = _evaluated_buyer_and_seller_records()[0]
    with pytest.raises(RuntimeError, match="OrderControlTvtMpSellerIndividual"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            **_individual_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_records=buyer_records,
                seller_records=("not_a_record",),
            )
        )


def test_individual_result_rejects_bool_decision_timestep():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="tvt_decision_timestep"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=True,
            node_name="junction_a",
            buyers_sorted=(_visit_key("buyer_a"),),
            trade_ex_post_evaluation_status=(
                OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
            ),
            buyer_evaluation_records=buyer_records,
            seller_evaluation_records=seller_records,
        )


def test_individual_result_rejects_negative_decision_timestep():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="tvt_decision_timestep"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=-1,
            node_name="junction_a",
            buyers_sorted=(_visit_key("buyer_a"),),
            trade_ex_post_evaluation_status=(
                OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
            ),
            buyer_evaluation_records=buyer_records,
            seller_evaluation_records=seller_records,
        )


def test_individual_result_rejects_empty_node_name():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="node_name"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=0,
            node_name="",
            buyers_sorted=(_visit_key("buyer_a"),),
            trade_ex_post_evaluation_status=(
                OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
            ),
            buyer_evaluation_records=buyer_records,
            seller_evaluation_records=seller_records,
        )


def test_individual_result_rejects_non_tuple_buyers_sorted():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="buyers_sorted must be a tuple"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=0,
            node_name="junction_a",
            buyers_sorted=[_visit_key("buyer_a")],
            trade_ex_post_evaluation_status=(
                OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
            ),
            buyer_evaluation_records=buyer_records,
            seller_evaluation_records=seller_records,
        )


def test_individual_result_rejects_duplicate_buyers_sorted_entries():
    duplicate_key = _visit_key("buyer_a")
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="duplicate VisitKey"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=0,
            node_name="junction_a",
            buyers_sorted=(duplicate_key, duplicate_key),
            trade_ex_post_evaluation_status=(
                OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
            ),
            buyer_evaluation_records=buyer_records,
            seller_evaluation_records=seller_records,
        )


def test_individual_result_rejects_invalid_trade_status_type():
    buyer_records, seller_records = _evaluated_buyer_and_seller_records()
    with pytest.raises(RuntimeError, match="trade_ex_post_evaluation_status"):
        OrderControlTvtMpIndividualExPostEvaluationResult(
            tvt_decision_timestep=0,
            node_name="junction_a",
            buyers_sorted=(_visit_key("buyer_a"),),
            trade_ex_post_evaluation_status="feasible",
            buyer_evaluation_records=buyer_records,
            seller_evaluation_records=seller_records,
        )


def test_registry_individual_result_dict_starts_empty():
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    assert registry.individual_ex_post_evaluation_results_by_transaction_key == {}


def test_registry_individual_finalized_timestep_starts_none():
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    assert registry.individual_ex_post_evaluation_finalized_timestep is None


def test_registry_instances_do_not_share_individual_result_dict():
    registry_a = OrderControlTvtMpActualPassageWaitRegistry()
    registry_b = OrderControlTvtMpActualPassageWaitRegistry()
    registry_a.individual_ex_post_evaluation_results_by_transaction_key[(1, "n", ())] = (
        None
    )
    assert registry_b.individual_ex_post_evaluation_results_by_transaction_key == {}


def test_world_instances_do_not_share_individual_result_dict():
    world_a = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    world_b = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    registry_a = world_a.order_control_tvt_mp_actual_passage_wait_registry
    registry_b = world_b.order_control_tvt_mp_actual_passage_wait_registry
    registry_a.individual_ex_post_evaluation_results_by_transaction_key[(2, "n", ())] = (
        None
    )
    assert registry_b.individual_ex_post_evaluation_results_by_transaction_key == {}


def test_trade_wait_has_no_individual_evaluation_fields():
    field_names = _field_names(OrderControlTvtMpActualPassageTradeWait)
    for name in field_names:
        assert "individual" not in name


def test_wait_entry_has_no_individual_evaluation_fields():
    field_names = _field_names(OrderControlTvtMpActualPassageWaitEntry)
    for name in field_names:
        assert "individual" not in name


def test_observation_record_has_no_individual_evaluation_fields():
    field_names = _field_names(OrderControlTvtMpActualPassageObservationRecord)
    for name in field_names:
        assert "individual" not in name


def test_production_public_types_match_specified_field_order_and_enum_values():
    assert _field_names(OrderControlTvtMpBuyerIndividualExPostEvaluationRecord) == [
        "visit_key",
        "vehicle_name",
        "realized_time_value",
        "official_payment",
        "realized_gain",
        "satisfaction_status",
        "satisfaction_reason",
        "official_payment_per_saved_second",
    ]
    assert _field_names(OrderControlTvtMpSellerIndividualExPostEvaluationRecord) == [
        "visit_key",
        "vehicle_name",
        "realized_delay_loss",
        "official_compensation",
        "realized_gain",
        "satisfaction_status",
        "satisfaction_reason",
        "official_compensation_per_delayed_second",
    ]
    assert _field_names(OrderControlTvtMpIndividualExPostEvaluationResult) == [
        "tvt_decision_timestep",
        "node_name",
        "buyers_sorted",
        "trade_ex_post_evaluation_status",
        "buyer_evaluation_records",
        "seller_evaluation_records",
    ]
    assert (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED.value == "satisfied"
    )
    assert (
        OrderControlTvtMpBuyerSatisfactionReason.UNSATISFIED_BY_HIGH_PAYMENT_RATE.value
        == "unsatisfied_by_high_payment_rate"
    )
    assert (
        OrderControlTvtMpSellerSatisfactionReason.SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE.value
        == "satisfied_by_sufficient_compensation_rate"
    )


def test_world_init_source_unchanged_for_individual_registry_fields():
    world_init_source = inspect.getsource(World.__init__)
    assert "individual_ex_post_evaluation" not in world_init_source


def test_individual_prepare_does_not_assign_to_live_registry():
    source = inspect.getsource(prepare_tvt_mp_individual_ex_post_evaluation)
    assert (
        "wait_registry.individual_ex_post_evaluation_results_by_transaction_key ="
        not in source
    )
    assert "wait_registry.individual_ex_post_evaluation_finalized_timestep =" not in source


def test_individual_commit_api_is_present():
    assert "commit_tvt_mp_individual_ex_post_evaluation" in dir(actual_passage_module)


def _minimal_world_for_individual_commit():
    world, trade, transaction_key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    return world, trade, transaction_key, registry


def _snapshot_commit_protected_live_state(world, trade, transaction_key):
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    trade_ex_post_result = (
        registry.trade_ex_post_evaluation_results_by_transaction_key[transaction_key]
    )
    return {
        "entries": copy.deepcopy(registry.entries_by_node_name_and_visit_key),
        "trades": copy.deepcopy(registry.trades_by_transaction_key),
        "trade_completion_flag": trade.buyer_seller_actual_passage_completion_notified,
        "history": copy.deepcopy(
            world.order_control_tvt_mp_actual_node_passage_history_registry.records_by_node_name
        ),
        "evaluation_end_unobserved_finalized_timestep": (
            registry.evaluation_end_unobserved_finalized_timestep
        ),
        "trade_ex_post_dict_id": id(
            registry.trade_ex_post_evaluation_results_by_transaction_key
        ),
        "trade_ex_post_result_id": id(trade_ex_post_result),
        "trade_ex_post_finalized": registry.trade_ex_post_evaluation_finalized_timestep,
    }


def test_commit_rejects_non_prepared_input():
    with pytest.raises(RuntimeError, match="_PreparedTvtMpIndividualExPostEvaluation"):
        commit_tvt_mp_individual_ex_post_evaluation(None)
    with pytest.raises(RuntimeError, match="_PreparedTvtMpIndividualExPostEvaluation"):
        commit_tvt_mp_individual_ex_post_evaluation({"wait_registry": None})
    with pytest.raises(RuntimeError, match="_PreparedTvtMpIndividualExPostEvaluation"):
        commit_tvt_mp_individual_ex_post_evaluation(object())


def test_commit_stores_prepared_results_and_finalized_timestep():
    world, _trade, transaction_key, registry = _minimal_world_for_individual_commit()
    assert registry.individual_ex_post_evaluation_results_by_transaction_key == {}
    assert registry.individual_ex_post_evaluation_finalized_timestep is None
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    prepared_result = (
        prepared.individual_ex_post_evaluation_results_by_transaction_key[
            transaction_key
        ]
    )
    commit_tvt_mp_individual_ex_post_evaluation(prepared)
    saved_result = registry.individual_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert saved_result is prepared_result
    assert (
        registry.individual_ex_post_evaluation_results_by_transaction_key
        is prepared.individual_ex_post_evaluation_results_by_transaction_key
    )
    assert registry.individual_ex_post_evaluation_finalized_timestep == (
        _EVALUATION_END_TIMESTEP
    )


def test_commit_assigns_result_dict_before_finalized_timestep(monkeypatch):
    world, _trade, _transaction_key, _registry = _minimal_world_for_individual_commit()
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    assignment_order = []

    original_setattr = OrderControlTvtMpActualPassageWaitRegistry.__setattr__

    def tracking_setattr(self, name, value):
        if name == "individual_ex_post_evaluation_results_by_transaction_key":
            assignment_order.append("results_dict")
        if name == "individual_ex_post_evaluation_finalized_timestep":
            assignment_order.append("finalized_timestep")
        return original_setattr(self, name, value)

    monkeypatch.setattr(
        OrderControlTvtMpActualPassageWaitRegistry,
        "__setattr__",
        tracking_setattr,
    )
    commit_tvt_mp_individual_ex_post_evaluation(prepared)
    assert assignment_order == ["results_dict", "finalized_timestep"]


def test_commit_does_not_mutate_other_live_state():
    world, trade, transaction_key, registry = _minimal_world_for_individual_commit()
    before = _snapshot_commit_protected_live_state(world, trade, transaction_key)
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    commit_tvt_mp_individual_ex_post_evaluation(prepared)
    after = _snapshot_commit_protected_live_state(world, trade, transaction_key)
    assert after == before


def test_commit_preserves_unavailable_infeasible_and_feasible_result_objects():
    unavailable_world, _t1, key1, _r1 = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": False,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
    )
    _prepare_and_commit_trade_ex_post(unavailable_world)
    unavailable_prepared = prepare_tvt_mp_individual_ex_post_evaluation(
        unavailable_world,
    )
    commit_tvt_mp_individual_ex_post_evaluation(unavailable_prepared)
    unavailable_saved = (
        unavailable_world.order_control_tvt_mp_actual_passage_wait_registry
        .individual_ex_post_evaluation_results_by_transaction_key[key1]
    )
    assert unavailable_saved is (
        unavailable_prepared.individual_ex_post_evaluation_results_by_transaction_key[
            key1
        ]
    )
    assert (
        unavailable_saved.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    )

    infeasible_world, _t2, key2, reg2 = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_b",
                "baseline_minus_actual_passage_seconds": 0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_b",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
        buyers_sorted=(_visit_key("buyer_b"),),
    )
    infeasible_prepared = prepare_tvt_mp_individual_ex_post_evaluation(
        infeasible_world,
    )
    commit_tvt_mp_individual_ex_post_evaluation(infeasible_prepared)
    infeasible_saved = reg2.individual_ex_post_evaluation_results_by_transaction_key[
        key2
    ]
    assert infeasible_saved is (
        infeasible_prepared.individual_ex_post_evaluation_results_by_transaction_key[
            key2
        ]
    )
    assert (
        infeasible_saved.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    )

    feasible_world, _t3, key3, reg3 = _minimal_world_for_individual_commit()
    feasible_prepared = prepare_tvt_mp_individual_ex_post_evaluation(feasible_world)
    commit_tvt_mp_individual_ex_post_evaluation(feasible_prepared)
    feasible_saved = reg3.individual_ex_post_evaluation_results_by_transaction_key[key3]
    assert feasible_saved is (
        feasible_prepared.individual_ex_post_evaluation_results_by_transaction_key[
            key3
        ]
    )
    assert (
        feasible_saved.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )


def test_commit_stores_all_transactions_from_prepared_dict():
    world = _evaluation_end_world()
    _add_trade_to_world(
        world,
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
        finalize_unobserved=True,
    )
    _add_trade_to_world(
        world,
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_b"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_b"},
        ],
        decision_timestep=_PREPARE_DECISION_TIMESTEP + 1,
        buyers_sorted=(_visit_key("buyer_b"),),
        finalize_unobserved=False,
    )
    _prepare_and_commit_trade_ex_post(world)
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    commit_tvt_mp_individual_ex_post_evaluation(prepared)
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    assert (
        registry.individual_ex_post_evaluation_results_by_transaction_key
        is prepared.individual_ex_post_evaluation_results_by_transaction_key
    )
    assert len(registry.individual_ex_post_evaluation_results_by_transaction_key) == 2


def test_commit_then_prepare_is_rejected_as_rerun():
    world, _trade, _transaction_key, _registry = _minimal_world_for_individual_commit()
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    commit_tvt_mp_individual_ex_post_evaluation(prepared)
    with pytest.raises(RuntimeError, match="already completed"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_partial_state_after_result_dict_only_assignment():
    world, _trade, transaction_key, registry = _minimal_world_for_individual_commit()
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    registry.individual_ex_post_evaluation_results_by_transaction_key = (
        prepared.individual_ex_post_evaluation_results_by_transaction_key
    )
    assert registry.individual_ex_post_evaluation_finalized_timestep is None
    with pytest.raises(RuntimeError, match="partial saved results"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_commit_source_assigns_prepared_values_only():
    source = inspect.getsource(commit_tvt_mp_individual_ex_post_evaluation)
    lowered = source.lower()
    assert "_PreparedTvtMpIndividualExPostEvaluation" in source
    assert "individual_ex_post_evaluation_results_by_transaction_key" in source
    assert "individual_ex_post_evaluation_finalized_timestep" in source
    results_index = source.index(
        "individual_ex_post_evaluation_results_by_transaction_key"
    )
    finalized_index = source.index(
        "individual_ex_post_evaluation_finalized_timestep"
    )
    assert results_index < finalized_index
    assert "order_exchange_log" not in lowered
    assert "waitentry" not in lowered.replace("_", "")
    assert "tradewait" not in lowered.replace("_", "")
    assert "observation_record" not in source
    assert "monetary_frozen" not in source
    assert "sort" not in source
    assert "realized_gain" not in source
    assert "satisfaction" not in lowered
    assert "OrderControlTvtMpIndividualExPostEvaluationResult(" not in source


def _common_frozen():
    return OrderControlTvtMpActualPassageCommonFrozenInput(
        baseline_local_rank=2,
        post_trade_local_rank=1,
        rank_change=1,
        route_origin=_ROUTE_ORIGIN,
    )


def _monetary_frozen(**changes):
    defaults = {
        "declared_vot_per_second": 1.0,
        "payment_paid_in_this_transaction": 3.0,
        "payment_received_in_this_transaction": 0.0,
    }
    for key, value in changes.items():
        defaults[key] = value
    return OrderControlTvtMpActualPassageMonetaryFrozenInput(**defaults)


def _frozen_fields(role, **monetary_changes):
    if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        monetary = None
    else:
        monetary = _monetary_frozen(**monetary_changes)
    return {
        "common_frozen_input": _common_frozen(),
        "monetary_frozen_input": monetary,
    }


def _evaluation_end_world():
    world = World(
        name="individual_prepare",
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


def _append_node_passage_history(world, node_name, visit_key, rank):
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    record = OrderControlTvtMpActualNodePassageRecord(
        visit_key=visit_key,
        actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
        actual_route_next_link_name="link_actual",
        actual_node_passage_rank=rank,
    )
    existing = registry.records_by_node_name.get(node_name, ())
    registry.records_by_node_name[node_name] = existing + (record,)


def _register_formal_trade_wait(
    world,
    *,
    decision_timestep,
    node_name,
    buyers_sorted,
    buyer_visit_keys,
    seller_visit_keys,
    nonparticipating_visit_keys=(),
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
    )
    transaction_key = (decision_timestep, node_name, buyers_sorted)
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.trades_by_transaction_key[transaction_key] = trade
    return trade, transaction_key


def _visit_key_for_role_spec(spec, buyers_sorted):
    vehicle_name = spec["vehicle_name"]
    visit_id = spec.get("visit_id", 1)
    role = spec["role"]
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        for visit_key in buyers_sorted:
            if visit_key[0] == vehicle_name:
                return visit_key
    return _visit_key(vehicle_name, visit_id)


def _observed_passage_record(
    *,
    visit_key,
    role,
    buyers_sorted,
    baseline_minus_actual_passage_seconds,
    true_vot_per_second=_TEST_TRUE_VOT_PER_SECOND,
    decision_timestep=_PREPARE_DECISION_TIMESTEP,
):
    timesteps = baseline_minus_actual_passage_seconds // _DELTAT_SECONDS
    time_value = baseline_minus_actual_passage_seconds * true_vot_per_second
    return OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=decision_timestep,
        node_name=_NODE_NAME,
        buyers_sorted=buyers_sorted,
        visit_key=visit_key,
        vehicle_name=visit_key[0],
        role=role,
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
        ),
        baseline_passage_timestep=_PREPARE_BASELINE_PASSAGE_TIMESTEP,
        candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
        true_vot_per_second=true_vot_per_second,
        predicted_observation_status=(
            OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
        ),
        predicted_route_next_link_name="link_pred",
        baseline_minus_candidate_passage_timesteps=_COPIED_BASELINE_MINUS_CANDIDATE[0],
        baseline_minus_candidate_passage_seconds=_COPIED_BASELINE_MINUS_CANDIDATE[1],
        baseline_minus_candidate_time_value=_COPIED_BASELINE_MINUS_CANDIDATE[2],
        baseline_minus_actual_passage_timesteps=timesteps,
        baseline_minus_actual_passage_seconds=baseline_minus_actual_passage_seconds,
        baseline_minus_actual_time_value=time_value,
        candidate_minus_actual_passage_timesteps=timesteps - 2,
        candidate_minus_actual_passage_seconds=(
            baseline_minus_actual_passage_seconds - 120
        ),
        candidate_minus_actual_time_value=time_value - 60.0,
        actual_passage_timestep=_PREPARE_ACTUAL_TIMESTEP,
        actual_route_next_link_name="link_actual",
    )


def _add_trade_to_world(
    world,
    role_specs,
    *,
    decision_timestep=_PREPARE_DECISION_TIMESTEP,
    buyers_sorted=None,
    finalize_unobserved=False,
):
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    if buyers_sorted is None:
        buyer_names = []
        for spec in role_specs:
            if spec["role"] is OrderControlTvtMpActualPassageRole.BUYER:
                buyer_names.append(spec["vehicle_name"])
        buyers_sorted = tuple(_visit_key(name) for name in buyer_names)
    buyer_keys = []
    seller_keys = []
    nonpart_keys = []
    history_registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    history_rank = 1
    for node_records in history_registry.records_by_node_name.values():
        history_rank = history_rank + len(node_records)
    for spec in role_specs:
        role = spec["role"]
        vehicle_name = spec["vehicle_name"]
        visit_key = _visit_key_for_role_spec(spec, buyers_sorted)
        observed = spec.get("observed", True)
        monetary_kwargs = {}
        if "declared_vot_per_second" in spec:
            monetary_kwargs["declared_vot_per_second"] = spec["declared_vot_per_second"]
        if "payment_paid_in_this_transaction" in spec:
            monetary_kwargs["payment_paid_in_this_transaction"] = spec[
                "payment_paid_in_this_transaction"
            ]
        if "payment_received_in_this_transaction" in spec:
            monetary_kwargs["payment_received_in_this_transaction"] = spec[
                "payment_received_in_this_transaction"
            ]
        true_vot = spec.get("true_vot_per_second", _TEST_TRUE_VOT_PER_SECOND)
        if observed:
            seconds = spec.get("baseline_minus_actual_passage_seconds", 120)
            wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
            observation_record = _observed_passage_record(
                visit_key=visit_key,
                role=role,
                buyers_sorted=buyers_sorted,
                baseline_minus_actual_passage_seconds=seconds,
                true_vot_per_second=true_vot,
                decision_timestep=decision_timestep,
            )
            _append_node_passage_history(
                world,
                _NODE_NAME,
                visit_key,
                history_rank,
            )
            history_rank = history_rank + 1
        else:
            wait_status = (
                OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
            )
            observation_record = None
        entry = OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=decision_timestep,
            node_name=_NODE_NAME,
            buyers_sorted=buyers_sorted,
            visit_key=visit_key,
            vehicle_name=vehicle_name,
            role=role,
            wait_status=wait_status,
            baseline_passage_timestep=_PREPARE_BASELINE_PASSAGE_TIMESTEP,
            candidate_passage_timestep=_PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
            true_vot_per_second=true_vot,
            baseline_minus_candidate_passage_timesteps=_COPIED_BASELINE_MINUS_CANDIDATE[0],
            baseline_minus_candidate_passage_seconds=_COPIED_BASELINE_MINUS_CANDIDATE[1],
            baseline_minus_candidate_time_value=_COPIED_BASELINE_MINUS_CANDIDATE[2],
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="link_pred",
            actual_passage_observation_record=observation_record,
            **_frozen_fields(role, **monetary_kwargs),
        )
        registry.entries_by_node_name_and_visit_key[(_NODE_NAME, visit_key)] = entry
        if role is OrderControlTvtMpActualPassageRole.BUYER:
            buyer_keys.append(visit_key)
        elif role is OrderControlTvtMpActualPassageRole.SELLER:
            seller_keys.append(visit_key)
        else:
            nonpart_keys.append(visit_key)
    trade, transaction_key = _register_formal_trade_wait(
        world,
        decision_timestep=decision_timestep,
        node_name=_NODE_NAME,
        buyers_sorted=buyers_sorted,
        buyer_visit_keys=tuple(buyer_keys),
        seller_visit_keys=tuple(seller_keys),
        nonparticipating_visit_keys=tuple(nonpart_keys),
    )
    if finalize_unobserved:
        _prepare_and_commit_evaluation_end(world)
    return trade, transaction_key


def _prepare_and_commit_evaluation_end(world):
    prepared = prepare_tvt_mp_actual_passage_evaluation_end_unobserved_finalization(
        world,
    )
    commit_tvt_mp_actual_passage_evaluation_end_unobserved_finalization(prepared)
    return prepared


def _prepare_and_commit_trade_ex_post(world):
    prepared = prepare_tvt_mp_trade_ex_post_evaluation(world)
    commit_tvt_mp_trade_ex_post_evaluation(prepared)
    return prepared


def _make_world_with_trade(
    role_specs,
    *,
    buyers_sorted=None,
    finalize_unobserved=True,
    decision_timestep=_PREPARE_DECISION_TIMESTEP,
):
    world = _evaluation_end_world()
    if buyers_sorted is None:
        buyer_names = []
        for spec in role_specs:
            if spec["role"] is OrderControlTvtMpActualPassageRole.BUYER:
                buyer_names.append(spec["vehicle_name"])
        buyers_sorted = tuple(_visit_key(name) for name in buyer_names)
    trade, transaction_key = _add_trade_to_world(
        world,
        role_specs,
        decision_timestep=decision_timestep,
        buyers_sorted=buyers_sorted,
        finalize_unobserved=finalize_unobserved,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    return world, trade, transaction_key, registry


def _ready_world_for_individual_prepare(role_specs, **kwargs):
    world, trade, transaction_key, registry = _make_world_with_trade(
        role_specs,
        **kwargs,
    )
    _prepare_and_commit_trade_ex_post(world)
    return world, trade, transaction_key, registry


def _individual_prepared_for_only_trade(world):
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    results = prepared.individual_ex_post_evaluation_results_by_transaction_key
    assert len(results) == 1
    return prepared, next(iter(results.values()))


def _snapshot_live_state(world, transaction_key):
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    trade = registry.trades_by_transaction_key[transaction_key]
    entry_snapshots = {}
    for entry_key, entry in registry.entries_by_node_name_and_visit_key.items():
        entry_snapshots[entry_key] = {
            "wait_status": entry.wait_status,
            "observation_record_id": id(entry.actual_passage_observation_record),
            "monetary_id": id(entry.monetary_frozen_input),
        }
    trade_ex_post_result = (
        registry.trade_ex_post_evaluation_results_by_transaction_key[transaction_key]
    )
    history = world.order_control_tvt_mp_actual_node_passage_history_registry
    return {
        "individual_dict_id": id(
            registry.individual_ex_post_evaluation_results_by_transaction_key
        ),
        "individual_dict": copy.deepcopy(
            registry.individual_ex_post_evaluation_results_by_transaction_key
        ),
        "individual_finalized": registry.individual_ex_post_evaluation_finalized_timestep,
        "trade_ex_post_result_id": id(trade_ex_post_result),
        "trade_ex_post_dict_id": id(
            registry.trade_ex_post_evaluation_results_by_transaction_key
        ),
        "notification_flag": trade.buyer_seller_actual_passage_completion_notified,
        "entry_snapshots": entry_snapshots,
        "history": copy.deepcopy(history.records_by_node_name),
    }


def test_prepare_rejects_when_unobserved_finalization_not_done():
    world, _trade, _key, _registry = _make_world_with_trade(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
        finalize_unobserved=False,
    )
    with pytest.raises(RuntimeError, match="evaluation_end_unobserved_finalized"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_when_trade_ex_post_not_completed():
    world, _trade, _key, _registry = _make_world_with_trade(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    with pytest.raises(RuntimeError, match="trade_ex_post_evaluation_finalized"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_trade_ex_post_finalized_timestep_mismatch():
    world, _trade, _key, registry = _make_world_with_trade(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    _prepare_and_commit_trade_ex_post(world)
    registry.trade_ex_post_evaluation_finalized_timestep = (
        _EVALUATION_END_TIMESTEP - 1
    )
    with pytest.raises(RuntimeError, match="trade_ex_post_evaluation_finalized"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_when_individual_finalized_already_set():
    world, _trade, _key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    registry.individual_ex_post_evaluation_finalized_timestep = (
        _EVALUATION_END_TIMESTEP
    )
    with pytest.raises(RuntimeError, match="already completed"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_partial_individual_result_dict():
    world, _trade, transaction_key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    registry.individual_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ] = OrderControlTvtMpIndividualExPostEvaluationResult(
        tvt_decision_timestep=_PREPARE_DECISION_TIMESTEP,
        node_name=_NODE_NAME,
        buyers_sorted=(_visit_key("buyer_a"),),
        trade_ex_post_evaluation_status=(
            OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
        ),
        buyer_evaluation_records=None,
        seller_evaluation_records=None,
    )
    with pytest.raises(RuntimeError, match="partial saved results"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_evaluation_end_timestep_mismatch_on_world_t():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    world.T = _EVALUATION_END_WORLD_T + 1
    with pytest.raises(RuntimeError, match="World.T"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_baseline_fork_world():
    from tests_order_control_tvt_mp_physical_transfer import _as_fork

    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    _as_fork(world)
    with pytest.raises(RuntimeError, match="real world only"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_waiting_entry():
    world, trade, _key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    seller_key = trade.seller_visit_keys[0]
    entry = registry.entries_by_node_name_and_visit_key[(_NODE_NAME, seller_key)]
    entry.wait_status = (
        OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    with pytest.raises(RuntimeError, match="WAITING_FOR_ACTUAL_PASSAGE"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_missing_trade_ex_post_result():
    world, _trade, transaction_key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    del registry.trade_ex_post_evaluation_results_by_transaction_key[transaction_key]
    with pytest.raises(RuntimeError, match="no saved trade ex-post"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_extra_trade_ex_post_result_key():
    world, _trade, transaction_key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    extra_key = (99, "orphan", (_visit_key("orphan_buyer"),))
    registry.trade_ex_post_evaluation_results_by_transaction_key[extra_key] = (
        registry.trade_ex_post_evaluation_results_by_transaction_key[transaction_key]
    )
    with pytest.raises(RuntimeError, match="unexpected transaction key"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_trade_ex_post_result_identity_mismatch():
    world, _trade, transaction_key, registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    trade_result = registry.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    registry.trade_ex_post_evaluation_results_by_transaction_key[transaction_key] = (
        dataclasses.replace(trade_result, node_name="other_node")
    )
    with pytest.raises(RuntimeError, match="node_name must match"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_rejects_stored_trade_status_inconsistent_with_unobserved_seller():
    world, _trade, transaction_key, registry = _make_world_with_trade(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": False,
            },
        ],
    )
    _prepare_and_commit_trade_ex_post(world)
    trade_result = registry.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    object.__setattr__(
        trade_result,
        "ex_post_evaluation_status",
        OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
    )
    with pytest.raises(RuntimeError, match="stored trade ex-post evaluation status"):
        prepare_tvt_mp_individual_ex_post_evaluation(world)


def test_prepare_unavailable_when_buyer_unobserved():
    world, _trade, transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": False,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
    )
    _prepare_and_commit_trade_ex_post(world)
    prepared, result = _individual_prepared_for_only_trade(world)
    assert (
        result.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    )
    assert result.buyer_evaluation_records is None
    assert result.seller_evaluation_records is None
    assert prepared.individual_ex_post_evaluation_finalized_timestep == (
        _EVALUATION_END_TIMESTEP
    )


def test_prepare_unavailable_when_seller_unobserved():
    world, _trade, _key, _registry = _make_world_with_trade(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": False,
            },
        ],
    )
    _prepare_and_commit_trade_ex_post(world)
    _prepared, result = _individual_prepared_for_only_trade(world)
    assert result.buyer_evaluation_records is None
    assert result.seller_evaluation_records is None


def test_prepare_buyer_positive_gain_is_satisfied():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
                "payment_paid_in_this_transaction": 30.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
                "payment_received_in_this_transaction": 0.0,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    buyer = result.buyer_evaluation_records[0]
    assert buyer.realized_time_value == 60.0
    assert buyer.realized_gain == 30.0
    assert buyer.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )


def test_prepare_buyer_zero_gain_is_unsatisfied():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
                "payment_paid_in_this_transaction": 60.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    buyer = result.buyer_evaluation_records[0]
    assert buyer.realized_gain == 0
    assert buyer.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.UNSATISFIED
    )


def test_prepare_buyer_high_payment_rate_equality_is_unsatisfied():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
                "payment_paid_in_this_transaction": 60.0,
                "true_vot_per_second": 0.5,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    buyer = result.buyer_evaluation_records[0]
    assert buyer.official_payment_per_saved_second == 0.5
    assert buyer.satisfaction_reason is (
        OrderControlTvtMpBuyerSatisfactionReason.UNSATISFIED_BY_HIGH_PAYMENT_RATE
    )


def test_prepare_buyer_true_vot_zero_with_positive_saving_is_trivial_unsatisfied():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
                "true_vot_per_second": 0.0,
                "payment_paid_in_this_transaction": 0.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    buyer = result.buyer_evaluation_records[0]
    assert buyer.realized_time_value == 0.0
    assert buyer.satisfaction_reason is (
        OrderControlTvtMpBuyerSatisfactionReason
        .TRIVIALLY_UNSATISFIED_NONPOSITIVE_REALIZED_TIME_VALUE
    )
    assert buyer.official_payment_per_saved_second is None


def test_prepare_seller_zero_gain_is_satisfied():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
                "payment_received_in_this_transaction": 60.0,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    seller = result.seller_evaluation_records[0]
    assert seller.realized_gain == 0
    assert seller.satisfaction_status is (
        OrderControlTvtMpIndividualSatisfactionStatus.SATISFIED
    )


def test_prepare_seller_early_passage_keeps_negative_delay_loss():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": 60,
                "payment_received_in_this_transaction": 0.0,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    seller = result.seller_evaluation_records[0]
    assert seller.realized_delay_loss == -30.0
    assert seller.satisfaction_reason is (
        OrderControlTvtMpSellerSatisfactionReason
        .TRIVIALLY_SATISFIED_NONPOSITIVE_ACTUAL_DELAY
    )


def test_prepare_seller_true_vot_zero_positive_delay_zero_compensation():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
                "true_vot_per_second": 0.0,
                "payment_received_in_this_transaction": 0.0,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    seller = result.seller_evaluation_records[0]
    assert seller.realized_delay_loss == 0.0
    assert seller.official_compensation_per_delayed_second == 0.0
    assert seller.satisfaction_reason is (
        OrderControlTvtMpSellerSatisfactionReason
        .SATISFIED_BY_SUFFICIENT_COMPENSATION_RATE
    )


def test_prepare_evaluates_all_roles_when_ex_post_infeasible():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 0,
                "payment_paid_in_this_transaction": 0.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
                "payment_received_in_this_transaction": 0.0,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    assert (
        result.trade_ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    )
    assert len(result.buyer_evaluation_records) == 1
    assert len(result.seller_evaluation_records) == 1


def test_prepare_does_not_use_declared_vot_for_buyer_time_value():
    world, _trade, _key, _registry = _ready_world_for_individual_prepare(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
                "declared_vot_per_second": 99.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
    )
    _prepared, result = _individual_prepared_for_only_trade(world)
    buyer = result.buyer_evaluation_records[0]
    assert buyer.realized_time_value == 60.0


def test_prepare_keeps_multiple_trades_separate_in_prepared_dict():
    world = _evaluation_end_world()
    specs_a = [
        {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
        {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
    ]
    specs_b = [
        {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_b"},
        {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_b"},
    ]
    _add_trade_to_world(world, specs_a, finalize_unobserved=True)
    _add_trade_to_world(
        world,
        specs_b,
        decision_timestep=_PREPARE_DECISION_TIMESTEP + 1,
        buyers_sorted=(_visit_key("buyer_b"),),
        finalize_unobserved=False,
    )
    _prepare_and_commit_trade_ex_post(world)
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    assert len(prepared.individual_ex_post_evaluation_results_by_transaction_key) == 2


def test_prepare_does_not_mutate_live_registry_individual_fields():
    world, _trade, transaction_key, _registry = _ready_world_for_individual_prepare(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
    )
    before = _snapshot_live_state(world, transaction_key)
    prepare_tvt_mp_individual_ex_post_evaluation(world)
    after = _snapshot_live_state(world, transaction_key)
    assert after["individual_dict"] == before["individual_dict"]
    assert after["individual_finalized"] == before["individual_finalized"]
    assert after["individual_dict_id"] == before["individual_dict_id"]
    assert after["trade_ex_post_result_id"] == before["trade_ex_post_result_id"]
    assert after["notification_flag"] == before["notification_flag"]
    assert after["entry_snapshots"] == before["entry_snapshots"]
    assert after["history"] == before["history"]


def test_prepare_source_does_not_reference_vehicle_or_order_exchange_log():
    source = inspect.getsource(prepare_tvt_mp_individual_ex_post_evaluation)
    lowered = source.lower()
    assert "order_exchange_log" not in lowered
    assert ".veh" not in lowered
    assert "vehicle." not in lowered
    assert "reference_payment" not in lowered
    assert "reference_compensation" not in lowered
