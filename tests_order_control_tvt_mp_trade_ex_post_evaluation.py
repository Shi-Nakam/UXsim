import copy
import dataclasses
import inspect

import pytest

from tests_order_control_tvt_mp_actual_passage import (
    _COPIED_BASELINE_MINUS_CANDIDATE,
    _PREPARE_ACTUAL_TIMESTEP,
    _PREPARE_BASELINE_PASSAGE_TIMESTEP,
    _PREPARE_CANDIDATE_PASSAGE_TIMESTEP,
    _PREPARE_DECISION_TIMESTEP,
    _TEST_TRUE_VOT_PER_SECOND,
    _append_node_passage_history,
    _evaluation_end_world,
    _frozen_fields,
    _prepare_and_commit_evaluation_end,
    _register_formal_trade_wait,
    _sample_visit_key,
    _wait_entry_baseline_minus_candidate_kwargs,
)
from tests_order_control_tvt_mp_physical_transfer import _as_fork
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageObservationRecord,
    OrderControlTvtMpActualPassageObservationStatus,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitRegistry,
    OrderControlTvtMpActualPassageWaitStatus,
    OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord,
    OrderControlTvtMpTradeExPostEvaluationResult,
    OrderControlTvtMpTradeExPostEvaluationStatus,
    OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord,
    commit_tvt_mp_trade_ex_post_evaluation,
    prepare_tvt_mp_trade_ex_post_evaluation,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.uxsim import World


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
    buyer_value: int | float,
    reference_payment: int | float,
) -> OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord:
    visit_key = _visit_key(vehicle_name, visit_id)
    return OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord(
        visit_key,
        vehicle_name,
        buyer_value,
        reference_payment,
    )


def _seller_record(
    vehicle_name: str,
    *,
    visit_id: int = 1,
    seller_actual_required_compensation: int | float,
    reference_compensation: int | float,
) -> OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord:
    visit_key = _visit_key(vehicle_name, visit_id)
    return OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord(
        visit_key,
        vehicle_name,
        seller_actual_required_compensation,
        reference_compensation,
    )


def _base_result_kwargs(
    *,
    status: OrderControlTvtMpTradeExPostEvaluationStatus,
    buyer_total: int | float | None,
    seller_total: int | float | None,
    buyer_records: tuple | None,
    seller_records: tuple | None,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...] | None = None,
):
    if buyers_sorted is None:
        buyers_sorted = (_visit_key("buyer_a"),)
    return {
        "tvt_decision_timestep": 5,
        "node_name": "junction_a",
        "buyers_sorted": buyers_sorted,
        "ex_post_evaluation_status": status,
        "buyer_actual_declared_time_saving_value_total": buyer_total,
        "seller_actual_required_compensation_total": seller_total,
        "buyer_reference_payment_records": buyer_records,
        "seller_reference_compensation_records": seller_records,
    }


def test_ex_post_evaluation_status_enum_members_and_values():
    status = OrderControlTvtMpTradeExPostEvaluationStatus
    assert status.EVALUATION_UNAVAILABLE.value == "evaluation_unavailable"
    assert status.EX_POST_INFEASIBLE.value == "ex_post_infeasible"
    assert status.EX_POST_FEASIBLE.value == "ex_post_feasible"
    names = []
    values = []
    for member in status:
        names.append(member.name)
        values.append(member.value)
    assert names == [
        "EVALUATION_UNAVAILABLE",
        "EX_POST_INFEASIBLE",
        "EX_POST_FEASIBLE",
    ]
    assert values == [
        "evaluation_unavailable",
        "ex_post_infeasible",
        "ex_post_feasible",
    ]
    assert len(names) == 3


def test_buyer_reference_payment_record_is_frozen_with_expected_field_order():
    fields = dataclasses.fields(OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord)
    assert [field.name for field in fields] == [
        "visit_key",
        "vehicle_name",
        "buyer_actual_declared_time_saving_value",
        "reference_payment",
    ]
    for field in fields:
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
    record = _buyer_record("buyer_a", buyer_value=10.0, reference_payment=0.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.reference_payment = 1.0


@pytest.mark.parametrize(
    "buyer_value",
    [-3.0, 0.0, 7.5],
)
def test_buyer_record_allows_negative_zero_and_positive_actual_values(buyer_value):
    record = _buyer_record(
        "buyer_a",
        buyer_value=buyer_value,
        reference_payment=0.0,
    )
    assert record.buyer_actual_declared_time_saving_value == buyer_value


def test_buyer_record_allows_zero_reference_payment():
    record = _buyer_record("buyer_a", buyer_value=1.0, reference_payment=0)
    assert record.reference_payment == 0


def test_buyer_record_rejects_negative_reference_payment():
    with pytest.raises(RuntimeError, match="reference_payment"):
        _buyer_record("buyer_a", buyer_value=1.0, reference_payment=-0.01)


@pytest.mark.parametrize(
    "bad_value",
    [True, float("nan"), float("inf"), float("-inf")],
)
def test_buyer_record_rejects_non_finite_or_bool_values(bad_value):
    with pytest.raises(RuntimeError):
        _buyer_record("buyer_a", buyer_value=bad_value, reference_payment=0.0)
    with pytest.raises(RuntimeError):
        _buyer_record("buyer_a", buyer_value=1.0, reference_payment=bad_value)


def test_buyer_record_rejects_visit_key_vehicle_name_mismatch():
    visit_key = _visit_key("buyer_a")
    with pytest.raises(RuntimeError, match="does not match"):
        OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord(
            visit_key,
            "other_name",
            1.0,
            0.0,
        )


def test_seller_reference_compensation_record_is_frozen_with_expected_field_order():
    fields = dataclasses.fields(
        OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord
    )
    assert [field.name for field in fields] == [
        "visit_key",
        "vehicle_name",
        "seller_actual_required_compensation",
        "reference_compensation",
    ]
    for field in fields:
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


def test_seller_record_allows_zero_actual_and_reference_compensation():
    record = _seller_record(
        "seller_a",
        seller_actual_required_compensation=0,
        reference_compensation=0,
    )
    assert record.seller_actual_required_compensation == 0
    assert record.reference_compensation == 0


def test_seller_record_keeps_actual_500_and_reference_0():
    record = _seller_record(
        "seller_a",
        seller_actual_required_compensation=500,
        reference_compensation=0,
    )
    assert record.seller_actual_required_compensation == 500
    assert record.reference_compensation == 0


def test_seller_record_rejects_negative_actual_required_compensation():
    with pytest.raises(RuntimeError):
        _seller_record(
            "seller_a",
            seller_actual_required_compensation=-1.0,
            reference_compensation=0.0,
        )


def test_seller_record_rejects_negative_reference_compensation():
    with pytest.raises(RuntimeError):
        _seller_record(
            "seller_a",
            seller_actual_required_compensation=0.0,
            reference_compensation=-1.0,
        )


@pytest.mark.parametrize(
    "bad_value",
    [True, float("nan"), float("inf")],
)
def test_seller_record_rejects_non_finite_or_bool_values(bad_value):
    with pytest.raises(RuntimeError):
        _seller_record(
            "seller_a",
            seller_actual_required_compensation=bad_value,
            reference_compensation=0.0,
        )


def test_ex_post_evaluation_result_is_frozen_with_expected_field_order():
    fields = dataclasses.fields(OrderControlTvtMpTradeExPostEvaluationResult)
    assert _field_names(OrderControlTvtMpTradeExPostEvaluationResult) == [
        "tvt_decision_timestep",
        "node_name",
        "buyers_sorted",
        "ex_post_evaluation_status",
        "buyer_actual_declared_time_saving_value_total",
        "seller_actual_required_compensation_total",
        "buyer_reference_payment_records",
        "seller_reference_compensation_records",
    ]
    for field in fields:
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


def test_evaluation_unavailable_result_requires_all_none_fields():
    result = OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE,
            buyer_total=None,
            seller_total=None,
            buyer_records=None,
            seller_records=None,
        )
    )
    assert result.buyer_actual_declared_time_saving_value_total is None
    assert result.seller_actual_required_compensation_total is None
    assert result.buyer_reference_payment_records is None
    assert result.seller_reference_compensation_records is None


@pytest.mark.parametrize(
    "buyer_total,seller_total,buyer_records,seller_records",
    [
        (1.0, None, None, None),
        (None, 1.0, None, None),
        (None, None, (), None),
        (None, None, None, ()),
    ],
)
def test_evaluation_unavailable_rejects_numeric_or_tuple_payloads(
    buyer_total,
    seller_total,
    buyer_records,
    seller_records,
):
    with pytest.raises(RuntimeError):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=(
                    OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
                ),
                buyer_total=buyer_total,
                seller_total=seller_total,
                buyer_records=buyer_records,
                seller_records=seller_records,
            )
        )


def test_ex_post_infeasible_keeps_actual_values_and_zero_reference_amounts():
    buyers_sorted = (_visit_key("buyer_a"),)
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=0.0, reference_payment=0.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=500,
            reference_compensation=0,
        ),
    )
    result = OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
            buyer_total=0.0,
            seller_total=500.0,
            buyer_records=buyer_records,
            seller_records=seller_records,
            buyers_sorted=buyers_sorted,
        )
    )
    assert result.buyer_reference_payment_records[0].reference_payment == 0
    assert (
        result.seller_reference_compensation_records[0]
        .seller_actual_required_compensation
        == 500
    )
    assert (
        result.seller_reference_compensation_records[0].reference_compensation
        == 0
    )


def test_ex_post_infeasible_keeps_seller_actual_when_buyer_value_is_negative():
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=-2.0, reference_payment=0.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=12.0,
            reference_compensation=0.0,
        ),
    )
    result = OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
            buyer_total=-2.0,
            seller_total=12.0,
            buyer_records=buyer_records,
            seller_records=seller_records,
        )
    )
    assert result.seller_actual_required_compensation_total == 12.0
    assert (
        result.seller_reference_compensation_records[0]
        .seller_actual_required_compensation
        == 12.0
    )


def test_ex_post_infeasible_rejects_none_record_columns():
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=1.0, reference_payment=0.0),
    )
    with pytest.raises(RuntimeError, match="seller_reference_compensation_records"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
                buyer_total=1.0,
                seller_total=0.0,
                buyer_records=buyer_records,
                seller_records=None,
            )
        )


def test_ex_post_infeasible_rejects_non_zero_reference_payment():
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=1.0, reference_payment=0.01),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=0.0,
            reference_compensation=0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="reference_payment"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
                buyer_total=1.0,
                seller_total=0.0,
                buyer_records=buyer_records,
                seller_records=seller_records,
            )
        )


def test_ex_post_infeasible_rejects_buyer_total_mismatch():
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=3.0, reference_payment=0.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=0.0,
            reference_compensation=0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="buyer_actual_declared_time_saving_value_total"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
                buyer_total=99.0,
                seller_total=0.0,
                buyer_records=buyer_records,
                seller_records=seller_records,
            )
        )


def test_ex_post_infeasible_rejects_seller_total_mismatch():
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=1.0, reference_payment=0.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=500.0,
            reference_compensation=0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="seller_actual_required_compensation_total"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
                buyer_total=1.0,
                seller_total=999.0,
                buyer_records=buyer_records,
                seller_records=seller_records,
            )
        )


def test_ex_post_infeasible_accepts_negative_and_zero_buyer_values_when_total_matches():
    buyers_sorted = (_visit_key("buyer_a"), _visit_key("buyer_b", 2))
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=-2.0, reference_payment=0.0),
        _buyer_record("buyer_b", visit_id=2, buyer_value=0.0, reference_payment=0.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=3,
            seller_actual_required_compensation=500.0,
            reference_compensation=0.0,
        ),
    )
    result = OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
            buyer_total=-2.0,
            seller_total=500.0,
            buyer_records=buyer_records,
            seller_records=seller_records,
            buyers_sorted=buyers_sorted,
        )
    )
    assert result.buyer_actual_declared_time_saving_value_total == -2.0
    assert result.seller_actual_required_compensation_total == 500.0
    assert (
        result.seller_reference_compensation_records[0]
        .seller_actual_required_compensation
        == 500.0
    )
    assert (
        result.seller_reference_compensation_records[0].reference_compensation
        == 0.0
    )


def _feasible_result(
    *,
    buyer_value: float = 100.0,
    seller_compensation: float = 40.0,
    reference_payment: float = 40.0,
):
    buyers_sorted = (_visit_key("buyer_a"),)
    buyer_records = (
        _buyer_record(
            "buyer_a",
            buyer_value=buyer_value,
            reference_payment=reference_payment,
        ),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=seller_compensation,
            reference_compensation=seller_compensation,
        ),
    )
    return OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
            buyer_total=buyer_value,
            seller_total=seller_compensation,
            buyer_records=buyer_records,
            seller_records=seller_records,
            buyers_sorted=buyers_sorted,
        )
    )


def test_ex_post_feasible_accepts_consistent_proportional_shape():
    result = _feasible_result()
    assert result.ex_post_evaluation_status is (
        OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )
    assert result.buyer_reference_payment_records[0].reference_payment == 40.0
    assert (
        result.seller_reference_compensation_records[0].reference_compensation
        == 40.0
    )


def test_ex_post_feasible_rejects_non_positive_buyer_actual_value():
    buyer_records = (
        _buyer_record("buyer_a", buyer_value=0.0, reference_payment=0.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=2,
            seller_actual_required_compensation=0.0,
            reference_compensation=0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="buyer_actual_declared_time_saving_value"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_total=1.0,
                seller_total=0.0,
                buyer_records=buyer_records,
                seller_records=seller_records,
            )
        )


def test_ex_post_feasible_rejects_buyer_total_mismatch():
    result_kwargs = _base_result_kwargs(
        status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
        buyer_total=999.0,
        seller_total=40.0,
        buyer_records=(
            _buyer_record("buyer_a", buyer_value=100.0, reference_payment=40.0),
        ),
        seller_records=(
            _seller_record(
                "seller_a",
                visit_id=2,
                seller_actual_required_compensation=40.0,
                reference_compensation=40.0,
            ),
        ),
    )
    with pytest.raises(RuntimeError, match="buyer_actual_declared_time_saving_value_total"):
        OrderControlTvtMpTradeExPostEvaluationResult(**result_kwargs)


def test_ex_post_feasible_rejects_seller_total_mismatch():
    with pytest.raises(RuntimeError, match="seller_actual_required_compensation_total"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_total=100.0,
                seller_total=999.0,
                buyer_records=(
                    _buyer_record(
                        "buyer_a",
                        buyer_value=100.0,
                        reference_payment=40.0,
                    ),
                ),
                seller_records=(
                    _seller_record(
                        "seller_a",
                        visit_id=2,
                        seller_actual_required_compensation=40.0,
                        reference_compensation=40.0,
                    ),
                ),
            )
        )


def test_ex_post_feasible_rejects_reference_compensation_mismatch():
    with pytest.raises(RuntimeError, match="reference_compensation"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_total=100.0,
                seller_total=40.0,
                buyer_records=(
                    _buyer_record(
                        "buyer_a",
                        buyer_value=100.0,
                        reference_payment=40.0,
                    ),
                ),
                seller_records=(
                    _seller_record(
                        "seller_a",
                        visit_id=2,
                        seller_actual_required_compensation=40.0,
                        reference_compensation=39.0,
                    ),
                ),
            )
        )


def test_ex_post_feasible_rejects_buyer_record_order_mismatch():
    buyers_sorted = (_visit_key("buyer_a"), _visit_key("buyer_b", 2))
    buyer_records = (
        _buyer_record("buyer_b", visit_id=2, buyer_value=50.0, reference_payment=20.0),
        _buyer_record("buyer_a", buyer_value=50.0, reference_payment=20.0),
    )
    seller_records = (
        _seller_record(
            "seller_a",
            visit_id=3,
            seller_actual_required_compensation=40.0,
            reference_compensation=40.0,
        ),
    )
    with pytest.raises(RuntimeError, match="buyers_sorted order"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE,
                buyer_total=100.0,
                seller_total=40.0,
                buyer_records=buyer_records,
                seller_records=seller_records,
                buyers_sorted=buyers_sorted,
            )
        )


def test_ex_post_result_rejects_shared_visit_key_between_buyer_and_seller():
    shared_key = _visit_key("shared_vehicle")
    buyer_records = (
        OrderControlTvtMpTradeExPostBuyerReferencePaymentRecord(
            shared_key,
            "shared_vehicle",
            1.0,
            0.0,
        ),
    )
    seller_records = (
        OrderControlTvtMpTradeExPostSellerReferenceCompensationRecord(
            shared_key,
            "shared_vehicle",
            0.0,
            0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="must not share VisitKey"):
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE,
                buyer_total=1.0,
                seller_total=0.0,
                buyer_records=buyer_records,
                seller_records=seller_records,
                buyers_sorted=(shared_key,),
            )
        )


def test_registry_ex_post_fields_default_to_empty_dict_and_none():
    registry = OrderControlTvtMpActualPassageWaitRegistry()
    assert registry.trade_ex_post_evaluation_results_by_transaction_key == {}
    assert registry.trade_ex_post_evaluation_finalized_timestep is None


def test_two_registry_instances_do_not_share_ex_post_result_dict():
    registry_a = OrderControlTvtMpActualPassageWaitRegistry()
    registry_b = OrderControlTvtMpActualPassageWaitRegistry()
    transaction_key = (1, "node_a", (_visit_key("buyer_a"),))
    registry_a.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ] = OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE,
            buyer_total=None,
            seller_total=None,
            buyer_records=None,
            seller_records=None,
        )
    )
    assert registry_b.trade_ex_post_evaluation_results_by_transaction_key == {}


def test_two_world_instances_do_not_share_ex_post_registry_dict():
    world_a = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    world_b = World(print_mode=0, save_mode=0, show_mode=0, show_progress=0)
    registry_a = world_a.order_control_tvt_mp_actual_passage_wait_registry
    registry_b = world_b.order_control_tvt_mp_actual_passage_wait_registry
    transaction_key = (2, "node_b", (_visit_key("buyer_b"),))
    registry_a.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ] = OrderControlTvtMpTradeExPostEvaluationResult(
        **_base_result_kwargs(
            status=OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE,
            buyer_total=None,
            seller_total=None,
            buyer_records=None,
            seller_records=None,
            buyers_sorted=(_visit_key("buyer_b"),),
        )
    )
    assert registry_b.trade_ex_post_evaluation_results_by_transaction_key == {}


def test_trade_wait_and_wait_entry_have_no_ex_post_fields():
    for cls in (
        OrderControlTvtMpActualPassageTradeWait,
        OrderControlTvtMpActualPassageWaitEntry,
    ):
        for field in dataclasses.fields(cls):
            lowered = field.name.lower()
            assert "ex_post" not in lowered
            assert "trade_ex_post" not in lowered


_NODE_NAME = "node_a"
_DELTAT_SECONDS = 60


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
    visit_key: OrderControlTvtVisitKey,
    role: OrderControlTvtMpActualPassageRole,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    baseline_minus_actual_passage_seconds: int | float,
) -> OrderControlTvtMpActualPassageObservationRecord:
    timesteps = baseline_minus_actual_passage_seconds // _DELTAT_SECONDS
    time_value = baseline_minus_actual_passage_seconds * _TEST_TRUE_VOT_PER_SECOND
    return OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=_PREPARE_DECISION_TIMESTEP,
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
        true_vot_per_second=_TEST_TRUE_VOT_PER_SECOND,
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


def _add_trade_to_existing_world(
    world,
    role_specs,
    *,
    decision_timestep,
    buyers_sorted,
    finalize_unobserved=False,
):
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
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
        declared_vot = spec.get("declared_vot_per_second", 1.0)
        monetary_overrides = {"declared_vot_per_second": declared_vot}
        if observed:
            seconds = spec.get("baseline_minus_actual_passage_seconds", 120)
            wait_status = OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
            observation_record = _observed_passage_record(
                visit_key=visit_key,
                role=role,
                buyers_sorted=buyers_sorted,
                baseline_minus_actual_passage_seconds=seconds,
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
            true_vot_per_second=_TEST_TRUE_VOT_PER_SECOND,
            baseline_minus_candidate_passage_timesteps=_COPIED_BASELINE_MINUS_CANDIDATE[0],
            baseline_minus_candidate_passage_seconds=_COPIED_BASELINE_MINUS_CANDIDATE[1],
            baseline_minus_candidate_time_value=_COPIED_BASELINE_MINUS_CANDIDATE[2],
            predicted_observation_status=(
                OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
            ),
            predicted_route_next_link_name="link_pred",
            actual_passage_observation_record=observation_record,
            **_frozen_fields(role, **monetary_overrides),
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
    trade, transaction_key = _add_trade_to_existing_world(
        world,
        role_specs,
        decision_timestep=decision_timestep,
        buyers_sorted=buyers_sorted,
        finalize_unobserved=finalize_unobserved,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    return world, trade, transaction_key, registry


def _prepare_ex_post(world):
    return prepare_tvt_mp_trade_ex_post_evaluation(world)


def _result_for_only_trade(prepared):
    results = prepared.trade_ex_post_evaluation_results_by_transaction_key
    assert len(results) == 1
    return next(iter(results.values()))


def test_prepare_marks_buyer_unobserved_trade_as_evaluation_unavailable():
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
                "observed": True,
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    prepared = _prepare_ex_post(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    )
    assert result.buyer_actual_declared_time_saving_value_total is None


def test_prepare_marks_seller_unobserved_trade_as_evaluation_unavailable():
    world, _trade, transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": True,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": False,
            },
        ]
    )
    prepared = _prepare_ex_post(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE
    )


def test_prepare_still_evaluates_when_only_nonparticipating_is_unobserved():
    world, _trade, transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": True,
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": True,
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "watcher_a",
                "observed": False,
            },
        ]
    )
    prepared = _prepare_ex_post(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )


def test_prepare_marks_zero_buyer_value_as_ex_post_infeasible():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
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
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    )
    assert result.buyer_reference_payment_records[0].reference_payment == 0


def test_prepare_marks_negative_buyer_value_as_ex_post_infeasible():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": -60,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    )
    assert result.buyer_actual_declared_time_saving_value_total == -60.0


def test_prepare_marks_buyer_total_below_seller_total_as_infeasible():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 60,
                "declared_vot_per_second": 1.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
                "declared_vot_per_second": 1.0,
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert result.buyer_actual_declared_time_saving_value_total == 60.0
    assert result.seller_actual_required_compensation_total == 120.0
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE
    )


def test_prepare_marks_equal_totals_as_ex_post_feasible():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
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
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert result.buyer_actual_declared_time_saving_value_total == 120.0
    assert result.seller_actual_required_compensation_total == 120.0
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )


def test_prepare_computes_zero_seller_compensation_for_zero_delay():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": 0,
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert (
        result.seller_reference_compensation_records[0]
        .seller_actual_required_compensation
        == 0
    )
    assert result.seller_reference_compensation_records[0].reference_compensation == 0


def test_prepare_computes_zero_seller_compensation_for_negative_delay():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
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
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert result.seller_actual_required_compensation_total == 0


def test_prepare_computes_positive_seller_compensation_for_positive_delay():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 300,
                "declared_vot_per_second": 1.0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
                "declared_vot_per_second": 1.0,
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert result.seller_actual_required_compensation_total == 120.0


def test_prepare_infeasible_keeps_seller_actual_500_and_zero_reference():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 0,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -100,
                "declared_vot_per_second": 5.0,
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    seller_record = result.seller_reference_compensation_records[0]
    assert seller_record.seller_actual_required_compensation == 500.0
    assert seller_record.reference_compensation == 0.0


def test_prepare_feasible_uses_proportional_buyer_reference_payments():
    buyers_sorted = (_visit_key("buyer_a"), _visit_key("buyer_b", 2))
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_b",
                "visit_id": 2,
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
        buyers_sorted=buyers_sorted,
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert result.buyer_reference_payment_records[0].reference_payment == 60.0
    assert result.buyer_reference_payment_records[1].reference_payment == 60.0


def test_prepare_feasible_sets_zero_buyer_reference_payments_when_seller_total_is_zero():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": 0,
            },
        ]
    )
    result = _result_for_only_trade(_prepare_ex_post(world))
    assert (
        result.ex_post_evaluation_status
        is OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE
    )
    assert result.buyer_reference_payment_records[0].reference_payment == 0


def test_prepare_handles_multiple_buyers_and_sellers():
    buyers_sorted = (_visit_key("buyer_a"), _visit_key("buyer_b", 2))
    world, _trade, transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "baseline_minus_actual_passage_seconds": 120,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_b",
                "visit_id": 2,
                "baseline_minus_actual_passage_seconds": 60,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -60,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_b",
                "visit_id": 2,
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
        buyers_sorted=buyers_sorted,
    )
    prepared = _prepare_ex_post(world)
    result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert result.buyer_actual_declared_time_saving_value_total == 180.0
    assert result.seller_actual_required_compensation_total == 180.0
    assert len(result.buyer_reference_payment_records) == 2
    assert len(result.seller_reference_compensation_records) == 2


def test_prepare_does_not_mutate_registry_entries_trades_or_records():
    world, _trade, _transaction_key, registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    registry_before = copy.deepcopy(registry)
    prepared = _prepare_ex_post(world)
    assert registry == registry_before
    assert registry.trade_ex_post_evaluation_results_by_transaction_key == {}
    assert registry.trade_ex_post_evaluation_finalized_timestep is None
    assert prepared.trade_ex_post_evaluation_finalized_timestep == 9


def test_prepare_failure_leaves_registry_result_dict_empty():
    world, _trade_a, _key_a, registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
        decision_timestep=10,
    )
    buyers_sorted_b = (_visit_key("buyer_b"),)
    _add_trade_to_existing_world(
        world,
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_b",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_b",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
        decision_timestep=11,
        buyers_sorted=buyers_sorted_b,
    )
    bad_visit_key = _visit_key("buyer_b")
    bad_entry = registry.entries_by_node_name_and_visit_key[(_NODE_NAME, bad_visit_key)]
    broken_record = _observed_passage_record(
        visit_key=bad_visit_key,
        role=OrderControlTvtMpActualPassageRole.BUYER,
        buyers_sorted=buyers_sorted_b,
        baseline_minus_actual_passage_seconds=120,
    )
    broken_record = OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=broken_record.tvt_decision_timestep,
        node_name=broken_record.node_name,
        buyers_sorted=broken_record.buyers_sorted,
        visit_key=broken_record.visit_key,
        vehicle_name=broken_record.vehicle_name,
        role=broken_record.role,
        observation_status=broken_record.observation_status,
        baseline_passage_timestep=broken_record.baseline_passage_timestep,
        candidate_passage_timestep=broken_record.candidate_passage_timestep,
        true_vot_per_second=broken_record.true_vot_per_second,
        predicted_observation_status=broken_record.predicted_observation_status,
        predicted_route_next_link_name=broken_record.predicted_route_next_link_name,
        baseline_minus_candidate_passage_timesteps=(
            broken_record.baseline_minus_candidate_passage_timesteps
        ),
        baseline_minus_candidate_passage_seconds=(
            broken_record.baseline_minus_candidate_passage_seconds
        ),
        baseline_minus_candidate_time_value=broken_record.baseline_minus_candidate_time_value,
        baseline_minus_actual_passage_timesteps=None,
        baseline_minus_actual_passage_seconds=None,
        baseline_minus_actual_time_value=None,
        candidate_minus_actual_passage_timesteps=(
            broken_record.candidate_minus_actual_passage_timesteps
        ),
        candidate_minus_actual_passage_seconds=(
            broken_record.candidate_minus_actual_passage_seconds
        ),
        candidate_minus_actual_time_value=broken_record.candidate_minus_actual_time_value,
        actual_passage_timestep=broken_record.actual_passage_timestep,
        actual_route_next_link_name=broken_record.actual_route_next_link_name,
    )
    broken_entry = OrderControlTvtMpActualPassageWaitEntry(
        tvt_decision_timestep=bad_entry.tvt_decision_timestep,
        node_name=bad_entry.node_name,
        buyers_sorted=bad_entry.buyers_sorted,
        visit_key=bad_entry.visit_key,
        vehicle_name=bad_entry.vehicle_name,
        role=bad_entry.role,
        wait_status=bad_entry.wait_status,
        baseline_passage_timestep=bad_entry.baseline_passage_timestep,
        candidate_passage_timestep=bad_entry.candidate_passage_timestep,
        true_vot_per_second=bad_entry.true_vot_per_second,
        baseline_minus_candidate_passage_timesteps=(
            bad_entry.baseline_minus_candidate_passage_timesteps
        ),
        baseline_minus_candidate_passage_seconds=(
            bad_entry.baseline_minus_candidate_passage_seconds
        ),
        baseline_minus_candidate_time_value=bad_entry.baseline_minus_candidate_time_value,
        predicted_observation_status=bad_entry.predicted_observation_status,
        predicted_route_next_link_name=bad_entry.predicted_route_next_link_name,
        common_frozen_input=bad_entry.common_frozen_input,
        monetary_frozen_input=bad_entry.monetary_frozen_input,
        actual_passage_observation_record=broken_record,
    )
    registry.entries_by_node_name_and_visit_key[(_NODE_NAME, bad_visit_key)] = (
        broken_entry
    )
    with pytest.raises(RuntimeError, match="baseline_minus_actual_passage_seconds"):
        _prepare_ex_post(world)
    assert registry.trade_ex_post_evaluation_results_by_transaction_key == {}


def test_prepare_rejects_unfinalized_evaluation_end():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ],
        finalize_unobserved=False,
    )
    with pytest.raises(RuntimeError, match="evaluation_end_unobserved_finalized_timestep"):
        _prepare_ex_post(world)


def test_prepare_rejects_already_finalized_ex_post_field():
    world, _trade, _transaction_key, registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    registry.trade_ex_post_evaluation_finalized_timestep = 9
    with pytest.raises(RuntimeError, match="already completed"):
        _prepare_ex_post(world)


def test_prepare_rejects_partial_saved_results():
    world, _trade, transaction_key, registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    registry.trade_ex_post_evaluation_results_by_transaction_key[transaction_key] = (
        OrderControlTvtMpTradeExPostEvaluationResult(
            **_base_result_kwargs(
                status=OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE,
                buyer_total=None,
                seller_total=None,
                buyer_records=None,
                seller_records=None,
            )
        )
    )
    with pytest.raises(RuntimeError, match="partial saved results"):
        _prepare_ex_post(world)


def test_prepare_rejects_evaluation_end_timestep_mismatch():
    world, _trade, _transaction_key, registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    registry.evaluation_end_unobserved_finalized_timestep = 8
    with pytest.raises(RuntimeError, match="evaluation_end_unobserved_finalized_timestep"):
        _prepare_ex_post(world)


def test_prepare_rejects_baseline_fork_world():
    world, _trade, _transaction_key, _registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "baseline_minus_actual_passage_seconds": -120,
            },
        ]
    )
    _as_fork(world)
    with pytest.raises(RuntimeError, match="real world only"):
        _prepare_ex_post(world)


def test_prepare_rejects_waiting_entry():
    world, _trade, _transaction_key, registry = _make_world_with_trade(
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "observed": False,
            },
            {
                "role": OrderControlTvtMpActualPassageRole.SELLER,
                "vehicle_name": "seller_a",
                "observed": False,
            },
        ],
        finalize_unobserved=False,
    )
    registry.evaluation_end_unobserved_finalized_timestep = 9
    with pytest.raises(RuntimeError, match="WAITING_FOR_ACTUAL_PASSAGE"):
        _prepare_ex_post(world)


def test_prepare_source_does_not_read_live_vehicle_or_exchange_log():
    import uxsim.order_control_tvt_mp_actual_passage as module

    names = [
        "prepare_tvt_mp_trade_ex_post_evaluation",
        "_build_trade_ex_post_evaluation_evaluated_result",
        "_build_trade_ex_post_evaluation_result_for_trade",
        "_buyer_actual_declared_time_saving_value_from_entry",
        "_seller_actual_required_compensation_from_entry",
    ]
    combined_source = ""
    for name in names:
        combined_source = combined_source + inspect.getsource(getattr(module, name))
    assert "order_exchange_log" not in combined_source
    assert "payment_paid" not in combined_source
    assert "payment_received" not in combined_source
    assert ".vehicles" not in combined_source


# ---------------------------------------------------------------------------
# commit_tvt_mp_trade_ex_post_evaluation
# ---------------------------------------------------------------------------


def _minimal_trade_world_for_commit():
    world, trade, transaction_key, registry = _make_world_with_trade(
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
            },
        ]
    )
    return world, trade, transaction_key, registry


def _snapshot_commit_protected_live_state(world, trade):
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
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
    }


def test_commit_rejects_non_prepared_input():
    with pytest.raises(RuntimeError, match="_PreparedTvtMpTradeExPostEvaluation"):
        commit_tvt_mp_trade_ex_post_evaluation(None)
    with pytest.raises(RuntimeError, match="_PreparedTvtMpTradeExPostEvaluation"):
        commit_tvt_mp_trade_ex_post_evaluation({"wait_registry": None})


def test_commit_stores_prepared_results_and_finalized_timestep():
    world, _trade, transaction_key, registry = _minimal_trade_world_for_commit()
    assert registry.trade_ex_post_evaluation_results_by_transaction_key == {}
    assert registry.trade_ex_post_evaluation_finalized_timestep is None
    prepared = _prepare_ex_post(world)
    prepared_result = prepared.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    commit_tvt_mp_trade_ex_post_evaluation(prepared)
    saved_result = registry.trade_ex_post_evaluation_results_by_transaction_key[
        transaction_key
    ]
    assert saved_result is prepared_result
    assert (
        registry.trade_ex_post_evaluation_results_by_transaction_key
        is prepared.trade_ex_post_evaluation_results_by_transaction_key
    )
    assert registry.trade_ex_post_evaluation_finalized_timestep == 9


def test_commit_assigns_result_dict_before_finalized_timestep(monkeypatch):
    world, _trade, _transaction_key, registry = _minimal_trade_world_for_commit()
    prepared = _prepare_ex_post(world)
    assignment_order = []

    original_setattr = OrderControlTvtMpActualPassageWaitRegistry.__setattr__

    def tracking_setattr(self, name, value):
        if name == "trade_ex_post_evaluation_results_by_transaction_key":
            assignment_order.append("results_dict")
        if name == "trade_ex_post_evaluation_finalized_timestep":
            assignment_order.append("finalized_timestep")
        return original_setattr(self, name, value)

    monkeypatch.setattr(
        OrderControlTvtMpActualPassageWaitRegistry,
        "__setattr__",
        tracking_setattr,
    )
    commit_tvt_mp_trade_ex_post_evaluation(prepared)
    assert assignment_order == ["results_dict", "finalized_timestep"]


def test_commit_does_not_mutate_other_live_state():
    world, trade, _transaction_key, registry = _minimal_trade_world_for_commit()
    before = _snapshot_commit_protected_live_state(world, trade)
    prepared = _prepare_ex_post(world)
    commit_tvt_mp_trade_ex_post_evaluation(prepared)
    after = _snapshot_commit_protected_live_state(world, trade)
    assert after == before


def test_commit_source_does_not_search_vehicle_or_exchange_log():
    import uxsim.order_control_tvt_mp_actual_passage as module

    source = inspect.getsource(module.commit_tvt_mp_trade_ex_post_evaluation)
    assert "order_exchange_log" not in source
    assert ".vehicles" not in source
    assert "prepare_tvt_mp" not in source
    assert "sort" not in source


def test_commit_then_prepare_is_rejected_as_rerun():
    world, _trade, _transaction_key, registry = _minimal_trade_world_for_commit()
    prepared = _prepare_ex_post(world)
    commit_tvt_mp_trade_ex_post_evaluation(prepared)
    with pytest.raises(RuntimeError, match="already completed"):
        _prepare_ex_post(world)


def test_prepare_rejects_partial_state_after_result_dict_only_assignment():
    world, _trade, transaction_key, registry = _minimal_trade_world_for_commit()
    prepared = _prepare_ex_post(world)
    registry.trade_ex_post_evaluation_results_by_transaction_key = (
        prepared.trade_ex_post_evaluation_results_by_transaction_key
    )
    assert registry.trade_ex_post_evaluation_finalized_timestep is None
    with pytest.raises(RuntimeError, match="partial saved results"):
        _prepare_ex_post(world)
