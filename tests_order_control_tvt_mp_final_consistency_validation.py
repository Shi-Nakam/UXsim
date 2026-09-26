"""
Tests for TVT-MP final consistency validation.

Run from the repository root:
    python tests_order_control_tvt_mp_final_consistency_validation.py
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import tests_order_control_tvt_mp_final_rank as fx
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionSetResult,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtMpSellerEconomicRecord,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_final_consistency_validation import (
    OrderControlTvtMpFinalConsistencyValidationSetResult,
    validate_tvt_mp_final_consistency,
)
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankSetResult,
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalRankVisitRecord,
    OrderControlTvtMpFinalizationSource,
    OrderControlTvtNodeMpFinalRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpBuyerPaymentRecord,
    OrderControlTvtMpPaymentAndCompensationSetResult,
    OrderControlTvtMpSellerCompensationRecord,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import World


PRODUCTION_PATH = Path("uxsim/order_control_tvt_mp_final_consistency_validation.py")
BUYER = OrderControlTvtMpLocalBindingTradeRole.BUYER
SELLER = OrderControlTvtMpLocalBindingTradeRole.SELLER
NONPARTICIPATING = OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING
OUTSIDE = OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE
SELECTED_SOURCE = OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE
BASELINE_SOURCE = OrderControlTvtMpFinalizationSource.BASELINE
SELECTED_RANKS = OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS
FALLBACK_RANKS = OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS
NO_VISITS = OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM


def _rank_record(visit_key, rank, route, source):
    return OrderControlTvtMpFinalRankVisitRecord(
        visit_key=visit_key,
        final_local_rank=rank,
        formal_route_next_link_name=route,
        finalization_source=source,
    )


def _seller(
    name,
    *,
    visit_id=1,
    declared_vot_per_second=1.0,
    baseline_passage_timestep=11,
    candidate_passage_timestep=12,
    raw_passage_difference_timesteps=1,
    expected_waiting_increase_timesteps=1,
    required_compensation_R_s=1.0,
):
    return OrderControlTvtMpSellerEconomicRecord(
        visit_key=fx._visit(name, visit_id),
        vehicle_name=name,
        declared_vot_per_second=declared_vot_per_second,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        raw_passage_difference_timesteps=raw_passage_difference_timesteps,
        expected_waiting_increase_timesteps=expected_waiting_increase_timesteps,
        raw_passage_difference_seconds=float(raw_passage_difference_timesteps),
        expected_waiting_increase_seconds=float(expected_waiting_increase_timesteps),
        required_compensation_R_s=required_compensation_R_s,
    )


def _binding(name, *, visit_id=1, rank, partition, route, role):
    return fx._binding_visit(
        name,
        visit_id=visit_id,
        rank=rank,
        partition=partition,
        route=route,
        role=role,
    )


def _economic(node_name, sequence, buyers, sellers):
    total_r = 0.0
    for seller in sellers:
        total_r = total_r + seller.required_compensation_R_s
    return OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=fx._local_result(
            node_name,
            sequence,
        ),
        buyer_economic_records=tuple(buyers),
        seller_economic_records=tuple(sellers),
        total_buyer_value_G=4.0,
        total_required_compensation_R=total_r,
        surplus=4.0 - total_r,
        economically_feasible=True,
        infeasibility_reasons=(),
    )


def _default_selected_parts(node_name="merge"):
    """Buyer, seller, nonparticipant, then one outside visit. Routes are explicit."""
    buyer = fx._buyer_record("buyer")
    seller = _seller("seller")
    partition_3 = (
        _binding(
            "buyer",
            rank=1,
            partition=fx.PARTITION_3,
            route="route-buyer",
            role=BUYER,
        ),
        _binding(
            "seller",
            rank=2,
            partition=fx.PARTITION_3,
            route="route-seller",
            role=SELLER,
        ),
        _binding(
            "watcher",
            rank=3,
            partition=fx.PARTITION_3,
            route="route-watcher",
            role=NONPARTICIPATING,
        ),
    )
    partition_4 = (
        _binding(
            "later",
            rank=4,
            partition=fx.PARTITION_4,
            route="route-later",
            role=OUTSIDE,
        ),
    )
    remaining = (
        fx._visit("buyer"),
        fx._visit("seller"),
        fx._visit("watcher"),
        fx._visit("later"),
    )
    return {
        "node_name": node_name,
        "buyers": (buyer,),
        "sellers": (seller,),
        "partition_1": (),
        "partition_2": (),
        "partition_3": partition_3,
        "partition_4": partition_4,
        "remaining": remaining,
        "leading": (),
        "arrived": (),
    }


def _visits_from_partitions(partition_3, partition_4):
    visits = []
    rank = 1
    for binding_visit in partition_3:
        visits.append(
            _rank_record(
                binding_visit.visit_key,
                rank,
                binding_visit.route_next_link_name,
                SELECTED_SOURCE,
            )
        )
        rank = rank + 1
    for binding_visit in partition_4:
        visits.append(
            _rank_record(
                binding_visit.visit_key,
                rank,
                binding_visit.route_next_link_name,
                BASELINE_SOURCE,
            )
        )
        rank = rank + 1
    return tuple(visits)


def _payment_records(buyers, sellers, *, payment_amount=99.0):
    buyer_records = []
    for buyer in buyers:
        buyer_records.append(
            OrderControlTvtMpBuyerPaymentRecord(
                visit_key=buyer.visit_key,
                vehicle_name=buyer.vehicle_name,
                payment_P_b=payment_amount,
            )
        )
    seller_records = []
    for seller in sellers:
        seller_records.append(
            OrderControlTvtMpSellerCompensationRecord(
                visit_key=seller.visit_key,
                vehicle_name=seller.vehicle_name,
                compensation_amount=seller.required_compensation_R_s,
            )
        )
    return tuple(buyer_records), tuple(seller_records)


def _selected_final_rank_set(
    *,
    node_name="merge",
    buyers=None,
    sellers=None,
    partition_3=None,
    partition_4=None,
    remaining=None,
    leading=None,
    arrived=None,
    partition_1=None,
    partition_2=None,
    buyer_records=None,
    seller_records=None,
    visits=None,
    payment_amount=99.0,
):
    parts = _default_selected_parts(node_name)
    if buyers is None:
        buyers = parts["buyers"]
    if sellers is None:
        sellers = parts["sellers"]
    if partition_3 is None:
        partition_3 = parts["partition_3"]
    if partition_4 is None:
        partition_4 = parts["partition_4"]
    if remaining is None:
        remaining = parts["remaining"]
    if leading is None:
        leading = parts["leading"]
    if arrived is None:
        arrived = parts["arrived"]
    if partition_1 is None:
        partition_1 = parts["partition_1"]
    if partition_2 is None:
        partition_2 = parts["partition_2"]
    sequence = fx._sequence(
        node_name,
        partition_1=partition_1,
        partition_2=partition_2,
        partition_3=partition_3,
        partition_4=partition_4,
        remaining=remaining,
    )
    selected = _economic(node_name, sequence, buyers, sellers)
    if buyer_records is None or seller_records is None:
        default_buyers, default_sellers = _payment_records(
            buyers,
            sellers,
            payment_amount=payment_amount,
        )
        if buyer_records is None:
            buyer_records = default_buyers
        if seller_records is None:
            seller_records = default_sellers
    spec = {
        "node_name": node_name,
        "build_status": fx.COMPLETE,
        "selected": selected,
        "remaining": remaining,
        "leading": leading,
        "arrived": arrived,
        "buyer_records": buyer_records,
        "seller_records": seller_records,
        "routes": {},
    }
    for visit_key in remaining:
        spec["routes"][visit_key] = "collector-" + visit_key[0]
    payment_set = fx._build([spec])
    if visits is None:
        visits = _visits_from_partitions(partition_3, partition_4)
    return _final_set(
        payment_set,
        (
            {
                "status": SELECTED_RANKS,
                "selected": selected,
                "visits": visits,
            },
        ),
    )


def _fallback_final_rank_set(node_name="merge", *, remaining=None, build_status=None, arrived=(), leading=(), visits=None):
    if remaining is None:
        remaining = (fx._visit("alpha"), fx._visit("beta"))
    if build_status is None:
        build_status = fx.COMPLETE
    spec = fx._fallback_spec(
        node_name,
        remaining=remaining,
        build_status=build_status,
        leading=leading,
        arrived=arrived,
    )
    payment_set = fx._build([spec])
    if visits is None:
        built_visits = []
        rank = 1
        for visit_key in remaining:
            built_visits.append(
                _rank_record(
                    visit_key,
                    rank,
                    "base-" + visit_key[0],
                    BASELINE_SOURCE,
                )
            )
            rank = rank + 1
        visits = tuple(built_visits)
    return _final_set(
        payment_set,
        (
            {
                "status": FALLBACK_RANKS,
                "selected": None,
                "visits": visits,
            },
        ),
    )


def _no_visits_final_rank_set(node_name="merge", *, preconfirmed=False):
    if preconfirmed:
        spec = fx._fully_preconfirmed_spec(node_name)
    else:
        spec = fx._empty_window_spec(node_name)
    payment_set = fx._build([spec])
    return _final_set(
        payment_set,
        (
            {
                "status": NO_VISITS,
                "selected": None,
                "visits": (),
            },
        ),
    )


def _final_set(payment_set, plans):
    nodes = []
    index = 0
    for plan in plans:
        payment_node = payment_set.node_payment_and_compensation_results[index]
        nodes.append(
            OrderControlTvtNodeMpFinalRankResult(
                node_name=plan.get("node_name", payment_node.node_name),
                final_rank_status=plan["status"],
                selected_candidate_economic_result=plan["selected"],
                final_rank_visits=plan["visits"],
            )
        )
        index = index + 1
    return OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=payment_set,
        node_final_rank_results=tuple(nodes),
    )


def _replace_final_rank_node(final_rank_set, node):
    return OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=(
            final_rank_set.payment_and_compensation_set_result
        ),
        node_final_rank_results=(node,),
    )


def _assert_runtime(final_rank_set, expected_text):
    try:
        validate_tvt_mp_final_consistency(final_rank_set)
        raised = False
        message = ""
    except RuntimeError as error:
        raised = True
        message = str(error)
    assert raised is True
    assert expected_text in message
    return message


# ---------------------------------------------------------------------------
# Public type and API
# ---------------------------------------------------------------------------


def test_validation_result_is_frozen_with_only_the_final_rank_set_field():
    result_fields = tuple(
        OrderControlTvtMpFinalConsistencyValidationSetResult.__dataclass_fields__
    )
    assert result_fields == ("final_rank_set_result",)
    final_rank_set = _no_visits_final_rank_set()
    result = validate_tvt_mp_final_consistency(final_rank_set)
    assert result.final_rank_set_result is final_rank_set
    try:
        result.final_rank_set_result = final_rank_set
        frozen = False
    except Exception:
        frozen = True
    assert frozen is True


def test_module_has_no_public_enum_and_no_public_node_result():
    source = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    public_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            public_classes.append(node.name)
    assert public_classes == [
        "OrderControlTvtMpFinalConsistencyValidationSetResult",
    ]
    assert "class OrderControlTvtMp" in source
    assert "Enum" not in source.split("class OrderControlTvtMpFinalConsistencyValidationSetResult", 1)[0][-80:]


def test_public_api_is_one_positional_function():
    signature = inspect.signature(validate_tvt_mp_final_consistency)
    parameters = list(signature.parameters.values())
    assert [parameter.name for parameter in parameters] == ["final_rank_set_result"]
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    source = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    public_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            public_names.append(node.name)
    assert public_names == ["validate_tvt_mp_final_consistency"]


def test_rejects_input_that_is_not_a_final_rank_set():
    try:
        validate_tvt_mp_final_consistency(None)
        raised = False
    except ValueError as error:
        raised = True
        assert "OrderControlTvtMpFinalRankSetResult" in str(error)
    assert raised is True


# ---------------------------------------------------------------------------
# Branch 1
# ---------------------------------------------------------------------------


def test_branch1_approves_buyer_seller_nonparticipant_and_partition_4():
    final_rank_set = _selected_final_rank_set()
    result = validate_tvt_mp_final_consistency(final_rank_set)
    assert result.final_rank_set_result is final_rank_set
    visits = final_rank_set.node_final_rank_results[0].final_rank_visits
    assert visits[0].visit_key == ("buyer", 1)
    assert visits[0].finalization_source is SELECTED_SOURCE
    assert visits[0].formal_route_next_link_name == "route-buyer"
    assert visits[1].visit_key == ("seller", 1)
    assert visits[1].finalization_source is SELECTED_SOURCE
    assert visits[2].visit_key == ("watcher", 1)
    assert visits[2].finalization_source is SELECTED_SOURCE
    assert visits[3].visit_key == ("later", 1)
    assert visits[3].finalization_source is BASELINE_SOURCE
    assert visits[3].formal_route_next_link_name == "route-later"
    assert [visit.final_local_rank for visit in visits] == [1, 2, 3, 4]
    payment_node = (
        final_rank_set.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    assert payment_node.buyer_payment_records[0].payment_P_b == 99.0
    assert payment_node.seller_compensation_records[0].compensation_amount == 1.0


def test_branch1_does_not_recompute_payment_amount():
    """99 is not R * G_b / G. Approval must not reject a saved amount."""
    final_rank_set = _selected_final_rank_set(payment_amount=99.0)
    result = validate_tvt_mp_final_consistency(final_rank_set)
    assert result.final_rank_set_result is final_rank_set


def test_branch1_partition_4_may_be_empty():
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding("seller", rank=2, partition=fx.PARTITION_3, route="route-seller", role=SELLER),
    )
    remaining = (fx._visit("buyer"), fx._visit("seller"))
    final_rank_set = _selected_final_rank_set(
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    result = validate_tvt_mp_final_consistency(final_rank_set)
    assert len(result.final_rank_set_result.node_final_rank_results[0].final_rank_visits) == 2


def test_branch1_zero_sellers_is_normal():
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
    )
    remaining = (fx._visit("buyer"),)
    final_rank_set = _selected_final_rank_set(
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    result = validate_tvt_mp_final_consistency(final_rank_set)
    payment_node = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    assert payment_node.seller_compensation_records == ()
    assert len(payment_node.buyer_payment_records) == 1


def test_buyer_record_order_must_match_economic_order():
    first = fx._buyer_record("buyer")
    second = fx._buyer_record("buyer_b", visit_id=2)
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding(
            "buyer_b",
            visit_id=2,
            rank=2,
            partition=fx.PARTITION_3,
            route="route-buyer-b",
            role=BUYER,
        ),
    )
    remaining = (fx._visit("buyer"), fx._visit("buyer_b", 2))
    buyer_records, seller_records = _payment_records((second, first), ())
    final_rank_set = _selected_final_rank_set(
        buyers=(first, second),
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
        buyer_records=buyer_records,
        seller_records=seller_records,
    )
    _assert_runtime(final_rank_set, "Saved order is not repaired")


def test_two_buyers_keep_saved_order_when_records_agree():
    first = fx._buyer_record("buyer")
    second = fx._buyer_record("buyer_b", visit_id=2)
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding(
            "buyer_b",
            visit_id=2,
            rank=2,
            partition=fx.PARTITION_3,
            route="route-buyer-b",
            role=BUYER,
        ),
    )
    remaining = (fx._visit("buyer"), fx._visit("buyer_b", 2))
    final_rank_set = _selected_final_rank_set(
        buyers=(first, second),
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    result = validate_tvt_mp_final_consistency(final_rank_set)
    records = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
        .buyer_payment_records
    )
    assert records[0].visit_key == ("buyer", 1)
    assert records[1].visit_key == ("buyer_b", 2)


def test_same_time_seller_keeps_zero_compensation_record():
    seller = _seller(
        "seller",
        baseline_passage_timestep=12,
        candidate_passage_timestep=12,
        raw_passage_difference_timesteps=0,
        expected_waiting_increase_timesteps=0,
        required_compensation_R_s=0.0,
    )
    final_rank_set = _selected_final_rank_set(sellers=(seller,))
    result = validate_tvt_mp_final_consistency(final_rank_set)
    compensation = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
        .seller_compensation_records[0]
    )
    assert compensation.compensation_amount == 0.0
    assert compensation.visit_key == ("seller", 1)


def test_early_seller_keeps_zero_compensation_record():
    seller = _seller(
        "seller",
        baseline_passage_timestep=14,
        candidate_passage_timestep=10,
        raw_passage_difference_timesteps=-4,
        expected_waiting_increase_timesteps=0,
        required_compensation_R_s=0.0,
    )
    final_rank_set = _selected_final_rank_set(sellers=(seller,))
    result = validate_tvt_mp_final_consistency(final_rank_set)
    compensation = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
        .seller_compensation_records[0]
    )
    assert compensation.compensation_amount == 0.0


def test_declared_vot_zero_delayed_seller_keeps_zero_compensation_record():
    seller = _seller(
        "seller",
        declared_vot_per_second=0.0,
        baseline_passage_timestep=10,
        candidate_passage_timestep=18,
        raw_passage_difference_timesteps=8,
        expected_waiting_increase_timesteps=8,
        required_compensation_R_s=0.0,
    )
    final_rank_set = _selected_final_rank_set(sellers=(seller,))
    result = validate_tvt_mp_final_consistency(final_rank_set)
    compensation = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
        .seller_compensation_records[0]
    )
    assert compensation.compensation_amount == 0.0
    assert seller.expected_waiting_increase_timesteps == 8


def test_saved_compensation_is_not_recomputed_from_passage_times():
    """Passage times would not produce 7 if a formula were rerun. 7 is the saved R_s."""
    seller = _seller(
        "seller",
        declared_vot_per_second=1.0,
        raw_passage_difference_timesteps=1,
        expected_waiting_increase_timesteps=1,
        required_compensation_R_s=7.0,
    )
    final_rank_set = _selected_final_rank_set(sellers=(seller,))
    result = validate_tvt_mp_final_consistency(final_rank_set)
    compensation = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
        .seller_compensation_records[0]
    )
    assert compensation.compensation_amount == 7.0


# ---------------------------------------------------------------------------
# Branches 2 to 5
# ---------------------------------------------------------------------------


def test_branch2_complete_review_fallback_has_empty_money_and_baseline_routes():
    final_rank_set = _fallback_final_rank_set(build_status=fx.COMPLETE)
    result = validate_tvt_mp_final_consistency(final_rank_set)
    node = result.final_rank_set_result.node_final_rank_results[0]
    assert node.final_rank_status is FALLBACK_RANKS
    assert node.final_rank_visits[0].formal_route_next_link_name == "base-alpha"
    assert node.final_rank_visits[1].finalization_source is BASELINE_SOURCE
    payment_node = (
        result.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    assert payment_node.buyer_payment_records == ()
    assert payment_node.seller_compensation_records == ()
    assert payment_node.selected_candidate_economic_result is None


def test_branch3_information_shortage_statuses_stay_fallback():
    for build_status in (
        fx.UNRESOLVED_ARRIVALS,
        fx.UNRESOLVED_RIGHT,
        fx.UNRESOLVED_PASSAGES,
    ):
        final_rank_set = _fallback_final_rank_set(build_status=build_status)
        result = validate_tvt_mp_final_consistency(final_rank_set)
        assert (
            result.final_rank_set_result.node_final_rank_results[0].final_rank_status
            is FALLBACK_RANKS
        )


def test_branch4_empty_window_is_no_visits():
    final_rank_set = _no_visits_final_rank_set(preconfirmed=False)
    result = validate_tvt_mp_final_consistency(final_rank_set)
    node = result.final_rank_set_result.node_final_rank_results[0]
    assert node.final_rank_status is NO_VISITS
    assert node.final_rank_visits == ()
    payment_set = result.final_rank_set_result.payment_and_compensation_set_result
    assert payment_set.node_payment_and_compensation_results[0].buyer_payment_records == ()
    leading = (
        payment_set.candidate_selection_set_result
        .economic_evaluation_set_result
        .local_virtual_calculation_set_result
        .fifo_inspection_set_result
        .general_trade_rank_set_result
        .concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .right_of_entry_selection_result
        .leading_confirmation_result
        .node_confirmation_results[0]
    )
    assert leading.decision_window_visit_keys == ()
    assert leading.remaining_decision_window_visit_keys == ()


def test_branch5_fully_preconfirmed_window_is_no_visits_without_repeating_visits():
    final_rank_set = _no_visits_final_rank_set(preconfirmed=True)
    result = validate_tvt_mp_final_consistency(final_rank_set)
    node = result.final_rank_set_result.node_final_rank_results[0]
    assert node.final_rank_visits == ()
    assert ("old_a", 1) not in [visit.visit_key for visit in node.final_rank_visits]


def test_branch4_and_branch5_share_status_but_not_decision_window_length():
    empty_window = _no_visits_final_rank_set("empty_node", preconfirmed=False)
    preconfirmed = _no_visits_final_rank_set("old_node", preconfirmed=True)
    validate_tvt_mp_final_consistency(empty_window)
    validate_tvt_mp_final_consistency(preconfirmed)
    empty_leading = _leading_node(empty_window)
    old_leading = _leading_node(preconfirmed)
    assert len(empty_leading.decision_window_visit_keys) == 0
    assert len(old_leading.decision_window_visit_keys) == 2
    assert empty_window.node_final_rank_results[0].final_rank_status is NO_VISITS
    assert preconfirmed.node_final_rank_results[0].final_rank_status is NO_VISITS


def _leading_node(final_rank_set):
    payment_set = final_rank_set.payment_and_compensation_set_result
    return (
        payment_set.candidate_selection_set_result
        .economic_evaluation_set_result
        .local_virtual_calculation_set_result
        .fifo_inspection_set_result
        .general_trade_rank_set_result
        .concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .right_of_entry_selection_result
        .leading_confirmation_result
        .node_confirmation_results[0]
    )


def test_mixed_node_order_is_approved_without_dropping_an_empty_node():
    empty_spec = fx._empty_window_spec("west")
    selected_set = _selected_final_rank_set(node_name="east")
    selected_payment = selected_set.payment_and_compensation_set_result
    # Rebuild a two-node payment set by concatenating the saved specs' results
    # is heavier than approving each. Here west is empty and east is selected,
    # built through the shared chain helper one node at a time above.
    # A combined set is built from the east selected spec plus an empty spec.
    east_node = selected_set.node_final_rank_results[0]
    selected_candidate = east_node.selected_candidate_economic_result
    east_spec = {
        "node_name": "east",
        "build_status": fx.COMPLETE,
        "selected": selected_candidate,
        "remaining": _leading_node(selected_set).remaining_decision_window_visit_keys,
        "buyer_records": (
            selected_payment.node_payment_and_compensation_results[0].buyer_payment_records
        ),
        "seller_records": (
            selected_payment.node_payment_and_compensation_results[0]
            .seller_compensation_records
        ),
        "routes": {},
    }
    for visit_key in east_spec["remaining"]:
        east_spec["routes"][visit_key] = "collector-" + visit_key[0]
    payment_set = fx._build([empty_spec, east_spec])
    final_rank_set = _final_set(
        payment_set,
        (
            {"status": NO_VISITS, "selected": None, "visits": ()},
            {
                "status": SELECTED_RANKS,
                "selected": selected_candidate,
                "visits": east_node.final_rank_visits,
            },
        ),
    )
    result = validate_tvt_mp_final_consistency(final_rank_set)
    names = []
    for node in result.final_rank_set_result.node_final_rank_results:
        names.append(node.node_name)
    assert names == ["west", "east"]


# ---------------------------------------------------------------------------
# Inconsistencies
# ---------------------------------------------------------------------------


def test_rejects_non_tuple_final_rank_column():
    final_rank_set = _no_visits_final_rank_set()
    broken = OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=(
            final_rank_set.payment_and_compensation_set_result
        ),
        node_final_rank_results=list(final_rank_set.node_final_rank_results),
    )
    _assert_runtime(broken, "must be a tuple")


def test_rejects_node_name_mismatch():
    final_rank_set = _no_visits_final_rank_set()
    node = final_rank_set.node_final_rank_results[0]
    renamed = OrderControlTvtNodeMpFinalRankResult(
        node_name="other",
        final_rank_status=node.final_rank_status,
        selected_candidate_economic_result=None,
        final_rank_visits=(),
    )
    broken = _replace_final_rank_node(final_rank_set, renamed)
    _assert_runtime(broken, "Node name mismatch")


def test_rejects_a_missing_upstream_node_result():
    final_rank_set = _no_visits_final_rank_set()
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection = payment_set.candidate_selection_set_result
    broken_selection = OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=selection.economic_evaluation_set_result,
        node_candidate_selection_results=(),
    )
    broken_payment = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=broken_selection,
        node_payment_and_compensation_results=(
            payment_set.node_payment_and_compensation_results
        ),
    )
    broken = OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=broken_payment,
        node_final_rank_results=final_rank_set.node_final_rank_results,
    )
    _assert_runtime(broken, "not a normal empty-Node outcome")


def test_rejects_selected_candidate_that_is_not_the_same_object():
    final_rank_set = _selected_final_rank_set()
    node = final_rank_set.node_final_rank_results[0]
    original = node.selected_candidate_economic_result
    clone = OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=(
            original.candidate_local_virtual_calculation_result
        ),
        buyer_economic_records=original.buyer_economic_records,
        seller_economic_records=original.seller_economic_records,
        total_buyer_value_G=original.total_buyer_value_G,
        total_required_compensation_R=original.total_required_compensation_R,
        surplus=original.surplus,
        economically_feasible=original.economically_feasible,
        infeasibility_reasons=original.infeasibility_reasons,
    )
    assert clone == original
    assert clone is not original
    replaced = OrderControlTvtNodeMpFinalRankResult(
        node_name=node.node_name,
        final_rank_status=node.final_rank_status,
        selected_candidate_economic_result=clone,
        final_rank_visits=node.final_rank_visits,
    )
    broken = _replace_final_rank_node(final_rank_set, replaced)
    _assert_runtime(broken, "not the same object")


def test_rejects_selected_candidate_missing_from_the_economic_tuple():
    final_rank_set = _selected_final_rank_set()
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection = payment_set.candidate_selection_set_result
    economic = selection.economic_evaluation_set_result
    original = final_rank_set.node_final_rank_results[0].selected_candidate_economic_result
    clone = OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=(
            original.candidate_local_virtual_calculation_result
        ),
        buyer_economic_records=original.buyer_economic_records,
        seller_economic_records=original.seller_economic_records,
        total_buyer_value_G=original.total_buyer_value_G,
        total_required_compensation_R=original.total_required_compensation_R,
        surplus=original.surplus,
        economically_feasible=original.economically_feasible,
        infeasibility_reasons=original.infeasibility_reasons,
    )
    payment_node = payment_set.node_payment_and_compensation_results[0]
    from uxsim.order_control_tvt_mp_payment_and_compensation import (
        OrderControlTvtNodeMpPaymentAndCompensationResult,
    )
    from uxsim.order_control_tvt_mp_candidate_selection import (
        OrderControlTvtNodeMpCandidateSelectionResult,
    )

    new_payment_node = OrderControlTvtNodeMpPaymentAndCompensationResult(
        node_name=payment_node.node_name,
        payment_and_compensation_status=payment_node.payment_and_compensation_status,
        selected_candidate_economic_result=clone,
        buyer_payment_records=payment_node.buyer_payment_records,
        seller_compensation_records=payment_node.seller_compensation_records,
    )
    selection_node = selection.node_candidate_selection_results[0]
    new_selection_node = OrderControlTvtNodeMpCandidateSelectionResult(
        node_name=selection_node.node_name,
        selection_status=selection_node.selection_status,
        selected_candidate_economic_result=clone,
        rng_was_used=False,
    )
    new_economic = OrderControlTvtMpEconomicEvaluationSetResult(
        local_virtual_calculation_set_result=economic.local_virtual_calculation_set_result,
        node_economic_evaluation_results=(
            OrderControlTvtNodeMpEconomicEvaluationResult(
                node_name="merge",
                candidate_economic_evaluation_results=(original,),
            ),
        ),
    )
    new_selection = OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=new_economic,
        node_candidate_selection_results=(new_selection_node,),
    )
    new_payment = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=new_selection,
        node_payment_and_compensation_results=(new_payment_node,),
    )
    new_final_node = OrderControlTvtNodeMpFinalRankResult(
        node_name="merge",
        final_rank_status=SELECTED_RANKS,
        selected_candidate_economic_result=clone,
        final_rank_visits=final_rank_set.node_final_rank_results[0].final_rank_visits,
    )
    broken = OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=new_payment,
        node_final_rank_results=(new_final_node,),
    )
    _assert_runtime(broken, "economic candidate tuple")


def test_rejects_buyer_vehicle_name_mismatch():
    buyer = fx._buyer_record("buyer")
    buyer_records = (
        OrderControlTvtMpBuyerPaymentRecord(
            visit_key=buyer.visit_key,
            vehicle_name="someone_else",
            payment_P_b=99.0,
        ),
    )
    final_rank_set = _selected_final_rank_set(
        buyers=(buyer,),
        buyer_records=buyer_records,
        seller_records=None,
    )
    _assert_runtime(final_rank_set, "vehicle_name")


def test_rejects_extra_buyer_payment_record():
    buyer = fx._buyer_record("buyer")
    extra = OrderControlTvtMpBuyerPaymentRecord(
        visit_key=fx._visit("buyer_b", 2),
        vehicle_name="buyer_b",
        payment_P_b=1.0,
    )
    matched, seller_records = _payment_records((buyer,), (_seller("seller"),))
    final_rank_set = _selected_final_rank_set(
        buyer_records=matched + (extra,),
        seller_records=seller_records,
    )
    _assert_runtime(final_rank_set, "buyer economic record count")


def test_rejects_buyer_role_that_is_not_buyer():
    watcher = fx._buyer_record("watcher")
    partition_3 = (
        _binding(
            "watcher",
            rank=1,
            partition=fx.PARTITION_3,
            route="route-watcher",
            role=NONPARTICIPATING,
        ),
    )
    final_rank_set = _selected_final_rank_set(
        buyers=(watcher,),
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=(fx._visit("watcher"),),
    )
    _assert_runtime(final_rank_set, "not BUYER")


def test_rejects_missing_payment_for_a_partition_3_buyer():
    first = fx._buyer_record("buyer")
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding(
            "buyer_b",
            visit_id=2,
            rank=2,
            partition=fx.PARTITION_3,
            route="route-buyer-b",
            role=BUYER,
        ),
    )
    remaining = (fx._visit("buyer"), fx._visit("buyer_b", 2))
    final_rank_set = _selected_final_rank_set(
        buyers=(first,),
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    _assert_runtime(final_rank_set, "has no buyer payment record")


def test_rejects_duplicate_buyer_visit_key():
    first = fx._buyer_record("buyer")
    duplicate = fx._buyer_record("buyer")
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
    )
    final_rank_set = _selected_final_rank_set(
        buyers=(first, duplicate),
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=(fx._visit("buyer"),),
    )
    _assert_runtime(final_rank_set, "duplicated")


def test_rejects_seller_vehicle_name_mismatch():
    seller = _seller("seller")
    buyer_records, _unused = _payment_records((fx._buyer_record("buyer"),), (seller,))
    seller_records = (
        OrderControlTvtMpSellerCompensationRecord(
            visit_key=seller.visit_key,
            vehicle_name="not_the_seller",
            compensation_amount=seller.required_compensation_R_s,
        ),
    )
    final_rank_set = _selected_final_rank_set(
        sellers=(seller,),
        buyer_records=buyer_records,
        seller_records=seller_records,
    )
    _assert_runtime(final_rank_set, "vehicle_name")


def test_rejects_compensation_amount_that_differs_from_saved_r_s():
    seller = _seller("seller", required_compensation_R_s=1.0)
    buyer_records, _unused = _payment_records((fx._buyer_record("buyer"),), (seller,))
    seller_records = (
        OrderControlTvtMpSellerCompensationRecord(
            visit_key=seller.visit_key,
            vehicle_name="seller",
            compensation_amount=0.0,
        ),
    )
    final_rank_set = _selected_final_rank_set(
        sellers=(seller,),
        buyer_records=buyer_records,
        seller_records=seller_records,
    )
    _assert_runtime(final_rank_set, "required_compensation_R_s")


def test_rejects_missing_zero_compensation_seller_record():
    seller = _seller("seller", required_compensation_R_s=0.0)
    buyer_records, _unused = _payment_records((fx._buyer_record("buyer"),), ())
    final_rank_set = _selected_final_rank_set(
        sellers=(seller,),
        buyer_records=buyer_records,
        seller_records=(),
    )
    message = _assert_runtime(final_rank_set, "zero compensation does not remove")
    assert "seller" in message


def test_rejects_seller_role_that_is_not_seller():
    seller = _seller("watcher", required_compensation_R_s=1.0)
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding(
            "watcher",
            rank=2,
            partition=fx.PARTITION_3,
            route="route-watcher",
            role=NONPARTICIPATING,
        ),
    )
    remaining = (fx._visit("buyer"), fx._visit("watcher"))
    final_rank_set = _selected_final_rank_set(
        sellers=(seller,),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    _assert_runtime(final_rank_set, "not SELLER")


def test_rejects_missing_compensation_for_a_partition_3_seller():
    seller = _seller("seller")
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding("seller", rank=2, partition=fx.PARTITION_3, route="route-seller", role=SELLER),
        _binding(
            "seller_b",
            visit_id=2,
            rank=3,
            partition=fx.PARTITION_3,
            route="route-seller-b",
            role=SELLER,
        ),
    )
    remaining = (
        fx._visit("buyer"),
        fx._visit("seller"),
        fx._visit("seller_b", 2),
    )
    final_rank_set = _selected_final_rank_set(
        sellers=(seller,),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    _assert_runtime(final_rank_set, "has no seller compensation record")


def test_rejects_duplicate_seller_visit_key():
    seller = _seller("seller")
    final_rank_set = _selected_final_rank_set(sellers=(seller, seller))
    _assert_runtime(final_rank_set, "duplicated")


def test_rejects_visit_key_used_as_both_buyer_and_seller():
    shared = fx._buyer_record("buyer")
    seller = _seller("buyer")
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
    )
    final_rank_set = _selected_final_rank_set(
        buyers=(shared,),
        sellers=(seller,),
        partition_3=partition_3,
        partition_4=(),
        remaining=(fx._visit("buyer"),),
    )
    _assert_runtime(final_rank_set, "both a buyer and a seller")


def test_rejects_money_record_on_a_nonparticipating_visit():
    """A payment whose visit is NONPARTICIPATING is rejected even if another buyer exists."""
    buyer = fx._buyer_record("buyer")
    watcher_as_buyer_record = OrderControlTvtMpBuyerPaymentRecord(
        visit_key=fx._visit("watcher"),
        vehicle_name="watcher",
        payment_P_b=1.0,
    )
    watcher_economic = fx._buyer_record("watcher")
    final_rank_set = _selected_final_rank_set(
        buyers=(buyer, watcher_economic),
        buyer_records=(
            OrderControlTvtMpBuyerPaymentRecord(
                visit_key=buyer.visit_key,
                vehicle_name="buyer",
                payment_P_b=99.0,
            ),
            watcher_as_buyer_record,
        ),
    )
    _assert_runtime(final_rank_set, "not BUYER")


def test_rejects_money_record_on_partition_4():
    later_seller = _seller("later")
    final_rank_set = _selected_final_rank_set(sellers=(_seller("seller"), later_seller))
    _assert_runtime(final_rank_set, "not in partition")


def test_rejects_fallback_with_a_buyer_payment_record():
    final_rank_set = _fallback_final_rank_set()
    payment_set = final_rank_set.payment_and_compensation_set_result
    payment_node = payment_set.node_payment_and_compensation_results[0]
    from uxsim.order_control_tvt_mp_payment_and_compensation import (
        OrderControlTvtNodeMpPaymentAndCompensationResult,
    )

    paid = OrderControlTvtNodeMpPaymentAndCompensationResult(
        node_name=payment_node.node_name,
        payment_and_compensation_status=payment_node.payment_and_compensation_status,
        selected_candidate_economic_result=None,
        buyer_payment_records=(
            OrderControlTvtMpBuyerPaymentRecord(
                visit_key=fx._visit("alpha"),
                vehicle_name="alpha",
                payment_P_b=1.0,
            ),
        ),
        seller_compensation_records=(),
    )
    selection = payment_set.candidate_selection_set_result
    broken_payment = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=selection,
        node_payment_and_compensation_results=(paid,),
    )
    broken = OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=broken_payment,
        node_final_rank_results=final_rank_set.node_final_rank_results,
    )
    _assert_runtime(broken, "empty buyer payment")


def test_rejects_no_visits_with_a_seller_compensation_record():
    final_rank_set = _no_visits_final_rank_set()
    payment_set = final_rank_set.payment_and_compensation_set_result
    payment_node = payment_set.node_payment_and_compensation_results[0]
    from uxsim.order_control_tvt_mp_payment_and_compensation import (
        OrderControlTvtNodeMpPaymentAndCompensationResult,
    )

    paid = OrderControlTvtNodeMpPaymentAndCompensationResult(
        node_name=payment_node.node_name,
        payment_and_compensation_status=payment_node.payment_and_compensation_status,
        selected_candidate_economic_result=None,
        buyer_payment_records=(),
        seller_compensation_records=(
            OrderControlTvtMpSellerCompensationRecord(
                visit_key=fx._visit("ghost"),
                vehicle_name="ghost",
                compensation_amount=0.0,
            ),
        ),
    )
    broken_payment = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=payment_set.candidate_selection_set_result,
        node_payment_and_compensation_results=(paid,),
    )
    broken = OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=broken_payment,
        node_final_rank_results=final_rank_set.node_final_rank_results,
    )
    _assert_runtime(broken, "empty seller compensation")


def test_rejects_final_local_rank_that_is_not_consecutive():
    final_rank_set = _selected_final_rank_set()
    visits = final_rank_set.node_final_rank_results[0].final_rank_visits
    first = visits[0]
    broken_first = _rank_record(first.visit_key, 2, first.formal_route_next_link_name, SELECTED_SOURCE)
    broken_visits = (broken_first,) + visits[1:]
    node = final_rank_set.node_final_rank_results[0]
    replaced = OrderControlTvtNodeMpFinalRankResult(
        node_name=node.node_name,
        final_rank_status=node.final_rank_status,
        selected_candidate_economic_result=node.selected_candidate_economic_result,
        final_rank_visits=broken_visits,
    )
    _assert_runtime(_replace_final_rank_node(final_rank_set, replaced), "final_local_rank")


def test_rejects_selected_source_on_a_partition_3_visit_that_is_marked_baseline():
    final_rank_set = _selected_final_rank_set()
    visits = final_rank_set.node_final_rank_results[0].final_rank_visits
    first = visits[0]
    broken_first = _rank_record(
        first.visit_key,
        1,
        first.formal_route_next_link_name,
        BASELINE_SOURCE,
    )
    broken_visits = (broken_first,) + visits[1:]
    node = final_rank_set.node_final_rank_results[0]
    replaced = OrderControlTvtNodeMpFinalRankResult(
        node_name=node.node_name,
        final_rank_status=node.final_rank_status,
        selected_candidate_economic_result=node.selected_candidate_economic_result,
        final_rank_visits=broken_visits,
    )
    _assert_runtime(
        _replace_final_rank_node(final_rank_set, replaced),
        "finalization source",
    )


def test_rejects_selected_route_that_differs_from_the_binding_route():
    final_rank_set = _selected_final_rank_set()
    visits = final_rank_set.node_final_rank_results[0].final_rank_visits
    first = visits[0]
    broken_first = _rank_record(first.visit_key, 1, "collector-buyer", SELECTED_SOURCE)
    broken_visits = (broken_first,) + visits[1:]
    node = final_rank_set.node_final_rank_results[0]
    replaced = OrderControlTvtNodeMpFinalRankResult(
        node_name=node.node_name,
        final_rank_status=node.final_rank_status,
        selected_candidate_economic_result=node.selected_candidate_economic_result,
        final_rank_visits=broken_visits,
    )
    message = _assert_runtime(
        _replace_final_rank_node(final_rank_set, replaced),
        "does not match saved binding route",
    )
    assert "not guessed" in message


def test_rejects_empty_binding_route():
    partition_3 = (
        _binding("buyer", rank=1, partition=fx.PARTITION_3, route="", role=BUYER),
        _binding("seller", rank=2, partition=fx.PARTITION_3, route="route-seller", role=SELLER),
        _binding(
            "watcher",
            rank=3,
            partition=fx.PARTITION_3,
            route="route-watcher",
            role=NONPARTICIPATING,
        ),
    )
    partition_4 = (
        _binding("later", rank=4, partition=fx.PARTITION_4, route="route-later", role=OUTSIDE),
    )
    visits = _visits_from_partitions(partition_3, partition_4)
    # The empty route is also copied into the hand-built final rank record.
    final_rank_set = _selected_final_rank_set(
        partition_3=partition_3,
        partition_4=partition_4,
        visits=visits,
    )
    _assert_runtime(final_rank_set, "empty")


def test_rejects_fallback_route_that_differs_from_the_collector():
    remaining = (fx._visit("alpha"),)
    visits = (
        _rank_record(fx._visit("alpha"), 1, "guessed-route", BASELINE_SOURCE),
    )
    final_rank_set = _fallback_final_rank_set(remaining=remaining, visits=visits)
    message = _assert_runtime(final_rank_set, "collector snapshot")
    assert "not guessed" in message


def test_rejects_missing_collector_route_on_fallback():
    remaining = (fx._visit("alpha"),)
    spec = fx._fallback_spec("merge", remaining=remaining, build_status=fx.COMPLETE)
    spec["routes"] = {}
    payment_set = fx._build([spec])
    visits = (_rank_record(fx._visit("alpha"), 1, "base-alpha", BASELINE_SOURCE),)
    final_rank_set = _final_set(
        payment_set,
        ({"status": FALLBACK_RANKS, "selected": None, "visits": visits},),
    )
    _assert_runtime(final_rank_set, "no snapshot")


def test_rejects_partition_1_visit_repeated_in_the_final_rank():
    repeated = _binding(
        "buyer",
        rank=1,
        partition=fx.PARTITION_1,
        route="old-route",
        role=NONPARTICIPATING,
    )
    partition_3 = (
        _binding("buyer", rank=2, partition=fx.PARTITION_3, route="route-buyer", role=BUYER),
        _binding("seller", rank=3, partition=fx.PARTITION_3, route="route-seller", role=SELLER),
    )
    remaining = (fx._visit("buyer"), fx._visit("seller"))
    final_rank_set = _selected_final_rank_set(
        partition_1=(repeated,),
        partition_3=partition_3,
        partition_4=(),
        remaining=remaining,
    )
    _assert_runtime(final_rank_set, "already confirmed")


def test_rejects_arrived_visit_repeated_in_fallback():
    remaining = (fx._visit("alpha"),)
    final_rank_set = _fallback_final_rank_set(
        remaining=remaining,
        arrived=(fx._visit("alpha"),),
    )
    _assert_runtime(final_rank_set, "arrived confirmed")


def test_rejects_preconfirmed_visit_repeated_in_the_remaining_window():
    leading = (fx._visit("alpha"),)
    remaining = (fx._visit("alpha"),)
    spec = fx._fallback_spec(
        "merge",
        remaining=remaining,
        build_status=fx.COMPLETE,
        leading=leading,
    )
    # The fixture builder sets decision from leading + remaining when decision
    # is omitted, which repeats alpha. Validation must not drop the repeat.
    payment_set = fx._build([spec])
    visits = (_rank_record(fx._visit("alpha"), 1, "base-alpha", BASELINE_SOURCE),)
    final_rank_set = _final_set(
        payment_set,
        ({"status": FALLBACK_RANKS, "selected": None, "visits": visits},),
    )
    _assert_runtime(final_rank_set, "repeats VisitKey")


def test_rejects_empty_window_status_used_as_fallback():
    final_rank_set = _fallback_final_rank_set(build_status=fx.NO_ENTRY)
    _assert_runtime(final_rank_set, "not fallback")


def test_rejects_completed_review_status_used_as_no_visits():
    spec = fx._empty_window_spec("merge")
    spec["build_status"] = fx.COMPLETE
    payment_set = fx._build([spec])
    final_rank_set = _final_set(
        payment_set,
        ({"status": NO_VISITS, "selected": None, "visits": ()},),
    )
    _assert_runtime(final_rank_set, "not recorded as no visits")


def test_rejects_no_visits_when_the_remaining_window_is_non_empty():
    final_rank_set = _fallback_final_rank_set()
    node = final_rank_set.node_final_rank_results[0]
    replaced = OrderControlTvtNodeMpFinalRankResult(
        node_name=node.node_name,
        final_rank_status=NO_VISITS,
        selected_candidate_economic_result=None,
        final_rank_visits=(),
    )
    _assert_runtime(
        _replace_final_rank_node(final_rank_set, replaced),
        "not an empty confirmation",
    )


def test_one_node_inconsistency_stops_before_the_next_node():
    bad = _selected_final_rank_set(node_name="first_node", seller_records=(), sellers=(_seller("seller", required_compensation_R_s=0.0),), buyer_records=_payment_records((fx._buyer_record("buyer"),), ())[0])
    good_spec = fx._fallback_spec(
        "second_node",
        remaining=(fx._visit("alpha"),),
        build_status=fx.COMPLETE,
    )
    good_spec["routes"] = {}
    first_payment = bad.payment_and_compensation_set_result
    # Rebuild by using the first node's saved spec pieces is unnecessary:
    # concatenate through a fresh build of first failure plus second missing route.
    first_selected = bad.node_final_rank_results[0].selected_candidate_economic_result
    first_payment_node = first_payment.node_payment_and_compensation_results[0]
    first_spec = {
        "node_name": "first_node",
        "build_status": fx.COMPLETE,
        "selected": first_selected,
        "remaining": _leading_node(bad).remaining_decision_window_visit_keys,
        "buyer_records": first_payment_node.buyer_payment_records,
        "seller_records": (),
        "routes": {},
    }
    for visit_key in first_spec["remaining"]:
        first_spec["routes"][visit_key] = "collector-" + visit_key[0]
    payment_set = fx._build([first_spec, good_spec])
    final_rank_set = _final_set(
        payment_set,
        (
            {
                "status": SELECTED_RANKS,
                "selected": first_selected,
                "visits": bad.node_final_rank_results[0].final_rank_visits,
            },
            {
                "status": FALLBACK_RANKS,
                "selected": None,
                "visits": (
                    _rank_record(fx._visit("alpha"), 1, "missing", BASELINE_SOURCE),
                ),
            },
        ),
    )
    message = _assert_runtime(final_rank_set, "first_node")
    assert "second_node" not in message


def test_inputs_rank_state_vehicle_and_world_seed_are_unchanged():
    final_rank_set = _selected_final_rank_set()
    rank_state = OrderControlTvtNodeRankState("merge")
    confirmed_before = rank_state.k_confirmed()
    world = World(
        name="validation-unchanged",
        deltan=1,
        reaction_time=1.0,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=4,
    )
    world.addNode("orig", 0, 0)
    world.addNode("dest", 1, 0)
    world.addLink("in", "orig", "dest", length=200, free_flow_speed=20)
    vehicle = world.addVehicle("orig", "dest", 0, name="scope")
    vehicle.payment_paid = 3.0
    vehicle.payment_received = 4.0
    vehicle.order_exchange_log = ["before"]
    validate_tvt_mp_final_consistency(final_rank_set)
    assert rank_state.k_confirmed() == confirmed_before
    assert vehicle.payment_paid == 3.0
    assert vehicle.payment_received == 4.0
    assert vehicle.order_exchange_log == ["before"]
    assert world.random_seed == 4


def test_rejects_none_formal_route():
    final_rank_set = _selected_final_rank_set()
    visits = final_rank_set.node_final_rank_results[0].final_rank_visits
    first = visits[0]
    broken_first = OrderControlTvtMpFinalRankVisitRecord(
        visit_key=first.visit_key,
        final_local_rank=1,
        formal_route_next_link_name=None,
        finalization_source=SELECTED_SOURCE,
    )
    broken_visits = (broken_first,) + visits[1:]
    node = final_rank_set.node_final_rank_results[0]
    replaced = OrderControlTvtNodeMpFinalRankResult(
        node_name=node.node_name,
        final_rank_status=node.final_rank_status,
        selected_candidate_economic_result=node.selected_candidate_economic_result,
        final_rank_visits=broken_visits,
    )
    message = _assert_runtime(
        _replace_final_rank_node(final_rank_set, replaced),
        "is None",
    )
    assert "not guessed" in message


def test_production_source_keeps_explicit_loops_and_forbids_out_of_scope_work():
    source = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    assert "for final_rank_node in saved_columns.final_rank_nodes:" in source
    assert "for buyer_economic_record in buyer_economic_records:" in source
    assert "for seller_economic_record in seller_economic_records:" in source
    assert "for binding_visit in trade_scope_visits:" in source
    assert "for binding_visit in outside_visits:" in source
    assert "dataclass(frozen=True)" in source
    assert "get_baseline_visit_snapshot" in source
    assert "_saved_node_columns_from_final_rank_set" in source
    forbidden_calls = {
        "calculate_tvt_mp_payments_and_compensations",
        "select_tvt_mp_candidates",
        "evaluate_tvt_mp_candidate_economics",
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
        "build_tvt_mp_fifo_inspection_results",
        "build_tvt_mp_final_ranks",
        "build_tvt_candidate_visit_set",
        "confirm_visits_and_formal_target_node_routes_atomically",
        "exec_simulation",
    }
    assert called_names.isdisjoint(forbidden_calls)
    for forbidden in (
        "real_W",
        "payment_paid",
        "payment_received",
        "order_exchange_log",
        "VEHICLES",
        "actual_passage",
    ):
        assert forbidden not in source
    assert "World" not in source


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
