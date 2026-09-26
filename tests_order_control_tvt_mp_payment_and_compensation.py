# Tests for TVT-MP payment and compensation calculation.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_payment_and_compensation.py

from __future__ import annotations

import ast
import copy
import dataclasses
import inspect
import math
from pathlib import Path

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateFinalNodeRecord,
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionSetResult,
    OrderControlTvtMpCandidateSelectionStatus,
    OrderControlTvtNodeMpCandidateSelectionResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpCandidateEconomicInfeasibilityReason,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtMpSellerEconomicRecord,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpBuyerPaymentRecord,
    OrderControlTvtMpPaymentAndCompensationSetResult,
    OrderControlTvtMpPaymentAndCompensationStatus,
    OrderControlTvtMpSellerCompensationRecord,
    OrderControlTvtNodeMpPaymentAndCompensationResult,
    calculate_tvt_mp_payments_and_compensations,
)
from uxsim.uxsim import World


PRODUCTION_PATH = Path("uxsim/order_control_tvt_mp_payment_and_compensation.py")
BASELINE_T = 10
FIFO_SENTINEL = object()
RANK_STATE_SENTINEL = object()
COLLECTOR_SENTINEL = object()

_FORBIDDEN_RESULT_FIELD_NAMES = {
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "payment_share",
    "expected_net_benefit",
    "utility",
    "realized_utility",
    "early_passage",
    "early_passage_flag",
    "experienced_early_passage_benefit",
    "total_buyer_payment",
    "total_seller_compensation",
    "institutional_balance",
    "actual_compensation",
    "final_rank",
    "actual",
    "actual_passage",
    "payment_paid",
    "payment_received",
    "order_exchange_log",
    "tolerance",
    "decimal",
    "rng",
    "seed",
}


# ---------------------------------------------------------------------------
# Small explicit fixtures
# ---------------------------------------------------------------------------


def _visit_key(vehicle_name: str, visit_id: int = 1):
    return (vehicle_name, visit_id)


def _new_world(*, name: str = "tvt_mp_payment", random_seed=0):
    world = World(
        name=name,
        deltan=1,
        reaction_time=1.0,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=random_seed,
    )
    world.addNode("orig", 0, 0)
    world.addNode("merge", 1, 0)
    world.addNode("dest", 2, 0)
    world.addLink("in_a", "orig", "merge", length=200, free_flow_speed=20)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20)
    return world


def _add_vehicle(world, name: str, *, vot_declared=1.0, payment_paid=0, payment_received=0):
    world.addVehicle(
        "orig",
        "dest",
        0,
        name=name,
        vot_declared=vot_declared,
        vot_true=vot_declared,
        participates_in_order_exchange=True,
        payment_paid=payment_paid,
        payment_received=payment_received,
    )
    return world.VEHICLES[name]


def _world_with_vehicles(vehicle_names, *, random_seed=0):
    world = _new_world(random_seed=random_seed)
    for name in vehicle_names:
        _add_vehicle(world, name)
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    world.T = BASELINE_T
    return world


def _standard_world():
    return _world_with_vehicles(
        ["buyer_a", "buyer_b", "buyer_c", "seller_a", "seller_b", "seller_zero"]
    )


def _binding_visit(
    vehicle_name: str,
    *,
    rank: int,
    role: OrderControlTvtMpLocalBindingTradeRole,
    visit_id: int = 1,
    vehicle_id: int = 0,
):
    return OrderControlTvtMpLocalBindingRankVisit(
        visit_key=_visit_key(vehicle_name, visit_id),
        vehicle_id=vehicle_id,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        binding_rank=rank,
        route_next_link_name="out",
        route_origin=(
            OrderControlTvtMpLocalBindingRouteOrigin.SNAPSHOT_ROUTE_ALREADY_DECIDED
        ),
        inlink_name="in_a",
        baseline_arrival_timestep=BASELINE_T,
        arrival_tiebreaker=0.1,
        trade_role=role,
    )


def _final_node_record(node_name: str):
    return OrderControlTvtMpCandidateFinalNodeRecord(
        node_name=node_name,
        incoming_vehicle_names=(),
        flow_capacity_remain=1.0,
        last_order_control_inlink_name=None,
        last_order_control_entry_timestep=None,
        order_control_clearance_timesteps=0,
    )


def _candidate_local_result(
    *,
    node_name: str = "merge",
    buyer_keys=None,
    seller_names=(),
):
    if buyer_keys is None:
        buyer_keys = (_visit_key("buyer_a"),)
    visits = []
    rank = 1
    for visit_key in buyer_keys:
        visits.append(
            _binding_visit(
                visit_key[0],
                rank=rank,
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                visit_id=visit_key[1],
            )
        )
        rank = rank + 1
    for name in seller_names:
        visits.append(
            _binding_visit(
                name,
                rank=rank,
                role=OrderControlTvtMpLocalBindingTradeRole.SELLER,
            )
        )
        rank = rank + 1
    visits = tuple(visits)
    buyer_set = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=tuple(buyer_keys),
    )
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=BASELINE_T,
        concrete_buyer_candidate_set=buyer_set,
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=visits,
        k_last_buyer=len(buyer_keys),
        k_decision_window=len(visits),
        k_fixed=len(visits),
    )
    return OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name=node_name,
        concrete_buyer_candidate_set=buyer_set,
        binding_rank_sequence=sequence,
        baseline_timestep_T=BASELINE_T,
        configured_horizon_steps=6,
        final_virtual_timestep=BASELINE_T,
        final_offset=0,
        simulated_timestep_count=1,
        stop_reason=(
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
        ),
        resolved=True,
        required_passage_records=(),
        unresolved_reasons=(),
        timestep_results=(),
        final_vehicle_records=(),
        final_inlink_records=(),
        final_outlink_records=(),
        final_node_record=_final_node_record(node_name),
        final_boundary_records=(),
    )


def _buyer_record(vehicle_name: str, *, visit_id: int = 1, G_b: float = 6.0):
    return OrderControlTvtMpBuyerEconomicRecord(
        visit_key=_visit_key(vehicle_name, visit_id),
        vehicle_name=vehicle_name,
        declared_vot_per_second=2.0,
        baseline_passage_timestep=12,
        candidate_passage_timestep=10,
        expected_time_saving_timesteps=2,
        expected_time_saving_seconds=2.0,
        gross_time_value_G_b=G_b,
        passes_positive_buyer_value_condition=G_b > 0,
    )


def _seller_record(
    vehicle_name: str,
    *,
    R_s: float = 2.0,
    declared_vot_per_second: float = 1.0,
    baseline_passage_timestep: int = 10,
    candidate_passage_timestep: int = 12,
):
    raw_difference = candidate_passage_timestep - baseline_passage_timestep
    if raw_difference > 0:
        waiting_increase = raw_difference
    else:
        waiting_increase = 0
    return OrderControlTvtMpSellerEconomicRecord(
        visit_key=_visit_key(vehicle_name),
        vehicle_name=vehicle_name,
        declared_vot_per_second=declared_vot_per_second,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        raw_passage_difference_timesteps=raw_difference,
        expected_waiting_increase_timesteps=waiting_increase,
        raw_passage_difference_seconds=float(raw_difference),
        expected_waiting_increase_seconds=float(waiting_increase),
        required_compensation_R_s=R_s,
    )


def _candidate_economic_result(
    *,
    node_name: str = "merge",
    buyer_records=None,
    seller_records=None,
    economically_feasible=True,
    infeasibility_reasons=(),
    total_buyer_value_G=None,
    total_required_compensation_R=None,
    surplus=None,
    local_result=None,
):
    if buyer_records is None:
        buyer_records = (_buyer_record("buyer_a", G_b=6.0),)
    if seller_records is None:
        seller_records = (_seller_record("seller_a", R_s=2.0),)
    buyer_records = tuple(buyer_records)
    seller_records = tuple(seller_records)
    if local_result is None:
        buyer_keys = []
        for buyer_record in buyer_records:
            buyer_keys.append(buyer_record.visit_key)
        seller_names = []
        for seller_record in seller_records:
            seller_names.append(seller_record.vehicle_name)
        local_result = _candidate_local_result(
            node_name=node_name,
            buyer_keys=tuple(buyer_keys),
            seller_names=tuple(seller_names),
        )
    if total_buyer_value_G is None:
        total_buyer_value_G = 0.0
        for buyer_record in buyer_records:
            total_buyer_value_G = (
                total_buyer_value_G + buyer_record.gross_time_value_G_b
            )
    if total_required_compensation_R is None:
        total_required_compensation_R = 0.0
        for seller_record in seller_records:
            total_required_compensation_R = (
                total_required_compensation_R
                + seller_record.required_compensation_R_s
            )
    if surplus is None:
        surplus = total_buyer_value_G - total_required_compensation_R
    return OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=local_result,
        buyer_economic_records=buyer_records,
        seller_economic_records=seller_records,
        total_buyer_value_G=total_buyer_value_G,
        total_required_compensation_R=total_required_compensation_R,
        surplus=surplus,
        economically_feasible=economically_feasible,
        infeasibility_reasons=infeasibility_reasons,
    )


def _infeasible_candidate(*, node_name: str = "merge"):
    return _candidate_economic_result(
        node_name=node_name,
        buyer_records=(_buyer_record("buyer_a", G_b=0.0),),
        seller_records=(_seller_record("seller_a", R_s=1.0),),
        economically_feasible=False,
        infeasibility_reasons=(
            OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
            OrderControlTvtMpCandidateEconomicInfeasibilityReason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION,
        ),
        total_buyer_value_G=0.0,
        total_required_compensation_R=1.0,
        surplus=-1.0,
    )


def _node_economic_result(node_name: str, candidates):
    return OrderControlTvtNodeMpEconomicEvaluationResult(
        node_name=node_name,
        candidate_economic_evaluation_results=tuple(candidates),
    )


def _node_local_result(node_name: str, candidate_economic_results):
    local_candidates = []
    for candidate in candidate_economic_results:
        local_candidates.append(
            candidate.candidate_local_virtual_calculation_result
        )
    return OrderControlTvtNodeMpLocalVirtualCalculationResult(
        node_name=node_name,
        build_status=OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE,
        candidate_local_virtual_calculation_results=tuple(local_candidates),
    )


def _economic_set(node_items):
    node_economic_results = []
    node_local_results = []
    for node_name, candidates in node_items:
        node_economic_results.append(_node_economic_result(node_name, candidates))
        node_local_results.append(_node_local_result(node_name, candidates))
    local_set = OrderControlTvtMpLocalVirtualCalculationSetResult(
        fifo_inspection_set_result=FIFO_SENTINEL,
        node_local_virtual_calculation_results=tuple(node_local_results),
    )
    return OrderControlTvtMpEconomicEvaluationSetResult(
        local_virtual_calculation_set_result=local_set,
        node_economic_evaluation_results=tuple(node_economic_results),
    )


def _selected_node_result(node_name: str, candidate, *, rng_was_used=False):
    return OrderControlTvtNodeMpCandidateSelectionResult(
        node_name=node_name,
        selection_status=OrderControlTvtMpCandidateSelectionStatus.SELECTED,
        selected_candidate_economic_result=candidate,
        rng_was_used=rng_was_used,
    )


def _no_candidate_node_result(node_name: str):
    return OrderControlTvtNodeMpCandidateSelectionResult(
        node_name=node_name,
        selection_status=(
            OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
        ),
        selected_candidate_economic_result=None,
        rng_was_used=False,
    )


def _selection_set(economic_set, node_selection_results):
    return OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=economic_set,
        node_candidate_selection_results=tuple(node_selection_results),
    )


def _standard_selected_set():
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    selection_set = _selection_set(
        economic_set,
        [_selected_node_result("merge", candidate)],
    )
    return candidate, economic_set, selection_set


def _calculate(selection_set):
    return calculate_tvt_mp_payments_and_compensations(selection_set)


def _world_fingerprint(world):
    vehicle_rows = []
    for name, vehicle in world.VEHICLES.items():
        vehicle_rows.append(
            (
                name,
                vehicle.vot_declared,
                vehicle.vot_true,
                vehicle.participates_in_order_exchange,
                vehicle.payment_paid,
                vehicle.payment_received,
                list(vehicle.order_exchange_log),
                vehicle.x,
                vehicle.state,
            )
        )
    return {
        "T": world.T,
        "TIME": world.TIME,
        "DELTAT": world.DELTAT,
        "random_seed": world.random_seed,
        "rng": copy.deepcopy(world.rng.bit_generator.state),
        "order_control_rng": copy.deepcopy(
            world.order_control_rng.bit_generator.state
        ),
        "vehicles": tuple(vehicle_rows),
    }


def _field_names(cls):
    names = []
    for field in dataclasses.fields(cls):
        names.append(field.name)
    return names


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


def test_payment_and_compensation_status_enum_members_and_values():
    status = OrderControlTvtMpPaymentAndCompensationStatus
    assert status.CALCULATED.value == "calculated"
    assert status.NO_SELECTED_CANDIDATE.value == "no_selected_candidate"
    names = []
    values = []
    for member in status:
        names.append(member.name)
        values.append(member.value)
    assert names == ["CALCULATED", "NO_SELECTED_CANDIDATE"]
    assert values == ["calculated", "no_selected_candidate"]


def test_buyer_seller_node_and_set_results_are_frozen():
    for cls in (
        OrderControlTvtMpBuyerPaymentRecord,
        OrderControlTvtMpSellerCompensationRecord,
        OrderControlTvtNodeMpPaymentAndCompensationResult,
        OrderControlTvtMpPaymentAndCompensationSetResult,
    ):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True


def test_public_result_field_order_and_forbidden_fields():
    assert _field_names(OrderControlTvtMpBuyerPaymentRecord) == [
        "visit_key",
        "vehicle_name",
        "payment_P_b",
    ]
    assert _field_names(OrderControlTvtMpSellerCompensationRecord) == [
        "visit_key",
        "vehicle_name",
        "compensation_amount",
    ]
    assert _field_names(OrderControlTvtNodeMpPaymentAndCompensationResult) == [
        "node_name",
        "payment_and_compensation_status",
        "selected_candidate_economic_result",
        "buyer_payment_records",
        "seller_compensation_records",
    ]
    assert _field_names(OrderControlTvtMpPaymentAndCompensationSetResult) == [
        "candidate_selection_set_result",
        "node_payment_and_compensation_results",
    ]
    for cls in (
        OrderControlTvtMpBuyerPaymentRecord,
        OrderControlTvtMpSellerCompensationRecord,
        OrderControlTvtNodeMpPaymentAndCompensationResult,
        OrderControlTvtMpPaymentAndCompensationSetResult,
    ):
        names = set(_field_names(cls))
        assert names.isdisjoint(_FORBIDDEN_RESULT_FIELD_NAMES)
        for name in names:
            assert "share" not in name
            assert "utility" not in name
            assert "actual" not in name
            assert "rank" not in name
            assert "balance" not in name


def test_public_columns_are_tuples_and_keep_input_objects():
    candidate, economic_set, selection_set = _standard_selected_set()
    result = _calculate(selection_set)
    assert result.candidate_selection_set_result is selection_set
    assert isinstance(result.node_payment_and_compensation_results, tuple)
    node_result = result.node_payment_and_compensation_results[0]
    assert node_result.selected_candidate_economic_result is candidate
    assert (
        economic_set.node_economic_evaluation_results[0]
        .candidate_economic_evaluation_results[0]
        is candidate
    )
    assert isinstance(node_result.buyer_payment_records, tuple)
    assert isinstance(node_result.seller_compensation_records, tuple)


def test_result_does_not_keep_live_world_vehicle_node_link_or_rng():
    candidate, _economic_set, selection_set = _standard_selected_set()
    result = _calculate(selection_set)
    node_result = result.node_payment_and_compensation_results[0]
    for obj in (
        result,
        node_result,
        node_result.buyer_payment_records[0],
        node_result.seller_compensation_records[0],
    ):
        names = _field_names(type(obj))
        assert "world" not in names
        assert "vehicle" not in names
        assert "rng" not in names
        assert "seed" not in names
        assert "real_W" not in names
    assert not isinstance(result.candidate_selection_set_result, World)
    assert candidate is node_result.selected_candidate_economic_result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def test_public_api_is_one_positional_function_without_extra_helpers():
    import uxsim.order_control_tvt_mp_payment_and_compensation as module

    signature = inspect.signature(calculate_tvt_mp_payments_and_compensations)
    parameter_names = list(signature.parameters)
    assert parameter_names == ["candidate_selection_set_result"]
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert parameter.default is inspect.Parameter.empty
    assert not hasattr(module, "calculate_tvt_mp_node_payments_and_compensations")
    assert not hasattr(module, "calculate_tvt_mp_one_buyer_payment")
    assert not hasattr(module, "calculate_tvt_mp_one_seller_compensation")
    assert not hasattr(module, "settle_tvt_mp_selected_candidates")
    assert "real_W" not in parameter_names
    assert "tolerance" not in parameter_names
    assert "rounding" not in parameter_names
    assert "payment_rule" not in parameter_names
    source = inspect.getsource(calculate_tvt_mp_payments_and_compensations)
    assert "real_W" not in source
    assert "tolerance" not in source
    assert "Decimal" not in source


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_rejects_non_selection_set_result():
    try:
        calculate_tvt_mp_payments_and_compensations("not-a-set")
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "CandidateSelectionSetResult" in str(error)
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    try:
        calculate_tvt_mp_payments_and_compensations(economic_set)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "CandidateSelectionSetResult" in str(error)


def test_rejects_non_tuple_or_mismatched_node_columns():
    candidate, economic_set, selection_set = _standard_selected_set()
    bad_list = dataclasses.replace(
        selection_set,
        node_candidate_selection_results=[
            selection_set.node_candidate_selection_results[0]
        ],
    )
    try:
        _calculate(bad_list)
        raise AssertionError("expected RuntimeError for selection list")
    except RuntimeError:
        pass
    extra_economic = dataclasses.replace(
        economic_set,
        node_economic_evaluation_results=(
            economic_set.node_economic_evaluation_results[0],
            _node_economic_result("other", [candidate]),
        ),
    )
    mismatched_count = dataclasses.replace(
        selection_set,
        economic_evaluation_set_result=extra_economic,
    )
    try:
        _calculate(mismatched_count)
        raise AssertionError("expected RuntimeError for Node count")
    except RuntimeError as error:
        assert "same length" in str(error)


def test_rejects_node_name_mismatch():
    candidate = _candidate_economic_result(node_name="merge")
    economic_set = _economic_set([("merge", [candidate])])
    selection_set = _selection_set(
        economic_set,
        [_selected_node_result("other", candidate)],
    )
    try:
        _calculate(selection_set)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "does not match" in str(error)


# ---------------------------------------------------------------------------
# Basic calculation
# ---------------------------------------------------------------------------


def test_one_buyer_one_seller_payment_and_compensation():
    candidate, _economic_set, selection_set = _standard_selected_set()
    result = _calculate(selection_set)
    node_result = result.node_payment_and_compensation_results[0]
    assert (
        node_result.payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    )
    assert node_result.selected_candidate_economic_result is candidate
    assert len(node_result.buyer_payment_records) == 1
    buyer_payment = node_result.buyer_payment_records[0]
    assert buyer_payment.visit_key == _visit_key("buyer_a")
    assert buyer_payment.vehicle_name == "buyer_a"
    # P_b = R * G_b / G = 2.0 * 6.0 / 6.0 = 2.0
    assert buyer_payment.payment_P_b == 2.0
    assert len(node_result.seller_compensation_records) == 1
    seller_compensation = node_result.seller_compensation_records[0]
    assert seller_compensation.visit_key == _visit_key("seller_a")
    assert seller_compensation.vehicle_name == "seller_a"
    assert seller_compensation.compensation_amount == 2.0


def test_multiple_buyers_keep_saved_order_and_formula():
    buyer_a = _buyer_record("buyer_a", G_b=6.0)
    buyer_b = _buyer_record("buyer_b", G_b=4.0)
    seller = _seller_record("seller_a", R_s=5.0)
    candidate = _candidate_economic_result(
        buyer_records=(buyer_a, buyer_b),
        seller_records=(seller,),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    payments = result.node_payment_and_compensation_results[0].buyer_payment_records
    assert payments[0].visit_key == _visit_key("buyer_a")
    assert payments[1].visit_key == _visit_key("buyer_b")
    # P_a = 5.0 * 6.0 / 10.0 = 3.0
    # P_b = 5.0 * 4.0 / 10.0 = 2.0
    assert payments[0].payment_P_b == 3.0
    assert payments[1].payment_P_b == 2.0


def test_zero_sellers_gives_zero_payments():
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=5.0),),
        seller_records=(),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    node_result = result.node_payment_and_compensation_results[0]
    assert node_result.seller_compensation_records == ()
    assert candidate.total_required_compensation_R == 0.0
    assert node_result.buyer_payment_records[0].payment_P_b == 0.0


def test_multiple_sellers_keep_saved_order():
    sellers = (
        _seller_record("seller_a", R_s=1.0),
        _seller_record("seller_b", R_s=2.0),
    )
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=sellers,
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    compensations = result.node_payment_and_compensation_results[0].seller_compensation_records
    assert compensations[0].vehicle_name == "seller_a"
    assert compensations[1].vehicle_name == "seller_b"
    assert compensations[0].compensation_amount == 1.0
    assert compensations[1].compensation_amount == 2.0
    assert result.node_payment_and_compensation_results[0].buyer_payment_records[0].payment_P_b == 3.0


def test_r_equals_zero_gives_zero_payments():
    candidate = _candidate_economic_result(
        buyer_records=(
            _buyer_record("buyer_a", G_b=3.0),
            _buyer_record("buyer_b", G_b=2.0),
        ),
        seller_records=(_seller_record("seller_a", R_s=0.0),),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    payments = result.node_payment_and_compensation_results[0].buyer_payment_records
    assert payments[0].payment_P_b == 0.0
    assert payments[1].payment_P_b == 0.0
    assert result.node_payment_and_compensation_results[0].seller_compensation_records[0].compensation_amount == 0.0


def test_g_equals_r_uses_formula_without_residual():
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=4.0),),
        seller_records=(_seller_record("seller_a", R_s=4.0),),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    payment = result.node_payment_and_compensation_results[0].buyer_payment_records[0]
    # P_b = 4.0 * 4.0 / 4.0 = 4.0. No leftover is added afterwards.
    assert payment.payment_P_b == 4.0


def test_g_greater_than_r_uses_formula_without_taking_surplus():
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=10.0),),
        seller_records=(_seller_record("seller_a", R_s=4.0),),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    payment = result.node_payment_and_compensation_results[0].buyer_payment_records[0]
    # P_b = 4.0 * 10.0 / 10.0 = 4.0. Surplus 6.0 is not collected from the buyer.
    assert payment.payment_P_b == 4.0
    assert payment.payment_P_b != 10.0


def test_node_order_is_preserved():
    first = _candidate_economic_result(
        node_name="merge",
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(_seller_record("seller_a", R_s=2.0),),
    )
    second = _candidate_economic_result(
        node_name="other",
        buyer_records=(_buyer_record("buyer_b", G_b=8.0),),
        seller_records=(),
    )
    economic_set = _economic_set([("merge", [first]), ("other", [second])])
    result = _calculate(
        _selection_set(
            economic_set,
            [
                _selected_node_result("merge", first),
                _selected_node_result("other", second),
            ],
        )
    )
    names = []
    for node_result in result.node_payment_and_compensation_results:
        names.append(node_result.node_name)
    assert names == ["merge", "other"]


# ---------------------------------------------------------------------------
# Seller cases
# ---------------------------------------------------------------------------


def test_delayed_seller_compensation_equals_saved_r_s():
    seller = _seller_record(
        "seller_a",
        R_s=12.0,
        declared_vot_per_second=3.0,
        baseline_passage_timestep=10,
        candidate_passage_timestep=14,
    )
    assert seller.raw_passage_difference_timesteps == 4
    assert seller.expected_waiting_increase_timesteps == 4
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=20.0),),
        seller_records=(seller,),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    compensation = result.node_payment_and_compensation_results[0].seller_compensation_records[0]
    assert compensation.compensation_amount == 12.0
    assert compensation.vehicle_name == "seller_a"


def test_same_time_seller_compensation_is_zero():
    seller = _seller_record(
        "seller_a",
        R_s=0.0,
        baseline_passage_timestep=10,
        candidate_passage_timestep=10,
    )
    assert seller.raw_passage_difference_timesteps == 0
    assert seller.expected_waiting_increase_timesteps == 0
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(seller,),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    node_result = result.node_payment_and_compensation_results[0]
    assert node_result.seller_compensation_records[0].compensation_amount == 0.0
    assert node_result.buyer_payment_records[0].payment_P_b == 0.0
    assert candidate.seller_economic_records[0] is seller


def test_early_passage_seller_compensation_is_zero_and_role_stays_seller():
    seller = _seller_record(
        "seller_a",
        R_s=0.0,
        baseline_passage_timestep=14,
        candidate_passage_timestep=10,
    )
    assert seller.raw_passage_difference_timesteps == -4
    assert seller.expected_waiting_increase_timesteps == 0
    buyer = _buyer_record("buyer_a", G_b=6.0)
    candidate = _candidate_economic_result(
        buyer_records=(buyer,),
        seller_records=(seller,),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    node_result = result.node_payment_and_compensation_results[0]
    assert node_result.seller_compensation_records[0].compensation_amount == 0.0
    assert node_result.seller_compensation_records[0].visit_key == _visit_key("seller_a")
    buyer_keys = []
    for payment in node_result.buyer_payment_records:
        buyer_keys.append(payment.visit_key)
    assert _visit_key("seller_a") not in buyer_keys
    assert candidate.seller_economic_records[0] is seller
    assert candidate.total_buyer_value_G == 6.0
    assert not hasattr(node_result.seller_compensation_records[0], "early_passage_flag")


def test_declared_vot_zero_delayed_seller_keeps_zero_compensation():
    # Declared VOT is 0, so even a delayed seller has saved R_s = 0 from
    # the upstream economic evaluation. This module copies that R_s.
    seller = _seller_record(
        "seller_zero",
        R_s=0.0,
        declared_vot_per_second=0.0,
        baseline_passage_timestep=10,
        candidate_passage_timestep=14,
    )
    assert seller.raw_passage_difference_timesteps == 4
    assert seller.expected_waiting_increase_timesteps == 4
    assert seller.declared_vot_per_second == 0.0
    assert seller.required_compensation_R_s == 0.0
    candidate = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(seller,),
    )
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    compensation = result.node_payment_and_compensation_results[0].seller_compensation_records[0]
    assert compensation.compensation_amount == 0.0
    assert compensation.vehicle_name == "seller_zero"
    assert candidate.seller_economic_records[0] is seller
    assert candidate.seller_economic_records[0].declared_vot_per_second == 0.0


# ---------------------------------------------------------------------------
# Float contract
# ---------------------------------------------------------------------------


def test_buyer_order_reversal_does_not_change_visit_key_payments():
    buyer_a = _buyer_record("buyer_a", G_b=6.0)
    buyer_b = _buyer_record("buyer_b", G_b=4.0)
    seller = _seller_record("seller_a", R_s=5.0)
    first = _candidate_economic_result(
        buyer_records=(buyer_a, buyer_b),
        seller_records=(seller,),
    )
    reversed_buyers = _candidate_economic_result(
        buyer_records=(buyer_b, buyer_a),
        seller_records=(seller,),
    )
    first_result = _calculate(
        _selection_set(
            _economic_set([("merge", [first])]),
            [_selected_node_result("merge", first)],
        )
    )
    reversed_result = _calculate(
        _selection_set(
            _economic_set([("other", [reversed_buyers])]),
            [_selected_node_result("other", reversed_buyers)],
        )
    )
    first_by_key = {}
    for payment in first_result.node_payment_and_compensation_results[0].buyer_payment_records:
        first_by_key[payment.visit_key] = payment.payment_P_b
    reversed_by_key = {}
    for payment in reversed_result.node_payment_and_compensation_results[0].buyer_payment_records:
        reversed_by_key[payment.visit_key] = payment.payment_P_b
    assert first_by_key[_visit_key("buyer_a")] == reversed_by_key[_visit_key("buyer_a")]
    assert first_by_key[_visit_key("buyer_b")] == reversed_by_key[_visit_key("buyer_b")]
    assert first_by_key[_visit_key("buyer_a")] == 3.0
    assert first_by_key[_visit_key("buyer_b")] == 2.0


def test_three_equal_buyers_each_use_formula_without_residual_or_sum_bit_check():
    buyers = (
        _buyer_record("buyer_a", G_b=1.0),
        _buyer_record("buyer_b", G_b=1.0),
        _buyer_record("buyer_c", G_b=1.0),
    )
    candidate = _candidate_economic_result(
        buyer_records=buyers,
        seller_records=(_seller_record("seller_a", R_s=1.0),),
    )
    R = 1.0
    G = 3.0
    economic_set = _economic_set([("merge", [candidate])])
    result = _calculate(
        _selection_set(economic_set, [_selected_node_result("merge", candidate)])
    )
    node_result = result.node_payment_and_compensation_results[0]
    assert (
        node_result.payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
    )
    payments = node_result.buyer_payment_records
    assert len(payments) == 3
    buyer_index = 0
    for buyer_economic_record in buyers:
        G_b = buyer_economic_record.gross_time_value_G_b
        expected_payment = R * G_b / G
        assert payments[buyer_index].payment_P_b == expected_payment
        assert payments[buyer_index].payment_P_b == 1.0 / 3.0
        buyer_index = buyer_index + 1
    # The last buyer uses the same per-buyer formula, not R minus earlier
    # payments. With equal G_b, that means the third payment is 1/3, not a
    # leftover residual assigned only to the final buyer.
    assert payments[2].payment_P_b == R * buyers[2].gross_time_value_G_b / G
    assert payments[2].payment_P_b == payments[0].payment_P_b
    production_source = PRODUCTION_PATH.read_text(encoding="utf-8")
    assert "payment_P_b <=" not in production_source
    assert "total_buyer_payment" not in production_source
    assert "summed_payments" not in production_source
    assert "sum(P_b)" not in production_source


def test_production_does_not_use_tolerance_decimal_rounding_or_residual():
    source_text = PRODUCTION_PATH.read_text(encoding="utf-8")
    assert "Decimal" not in source_text
    assert "tolerance" not in source_text
    assert "epsilon" not in source_text
    assert "round(" not in source_text
    assert "residual allocation" not in source_text
    assert "does not receive a leftover" in source_text
    assert "payment_P_b <=" not in source_text
    assert "payment_P_b >" not in source_text


# ---------------------------------------------------------------------------
# No selected candidate
# ---------------------------------------------------------------------------


def test_no_selected_candidate_is_normal_empty_status():
    infeasible = _infeasible_candidate()
    economic_set = _economic_set([("merge", [infeasible])])
    selection_set = _selection_set(
        economic_set,
        [_no_candidate_node_result("merge")],
    )
    result = _calculate(selection_set)
    node_result = result.node_payment_and_compensation_results[0]
    assert (
        node_result.payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
    )
    assert node_result.selected_candidate_economic_result is None
    assert node_result.buyer_payment_records == ()
    assert node_result.seller_compensation_records == ()

    empty_set = _economic_set([("merge", [])])
    empty_result = _calculate(
        _selection_set(empty_set, [_no_candidate_node_result("merge")])
    )
    empty_node = empty_result.node_payment_and_compensation_results[0]
    assert (
        empty_node.payment_and_compensation_status
        is OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
    )
    assert empty_node.buyer_payment_records == ()
    assert empty_node.seller_compensation_records == ()

    no_node_set = _economic_set([])
    no_node_result = _calculate(_selection_set(no_node_set, []))
    assert no_node_result.node_payment_and_compensation_results == ()
    assert no_node_result.candidate_selection_set_result.economic_evaluation_set_result is no_node_set


# ---------------------------------------------------------------------------
# Inconsistencies
# ---------------------------------------------------------------------------


def test_rejects_status_and_selected_contradiction():
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    selected_none = OrderControlTvtNodeMpCandidateSelectionResult(
        node_name="merge",
        selection_status=OrderControlTvtMpCandidateSelectionStatus.SELECTED,
        selected_candidate_economic_result=None,
        rng_was_used=False,
    )
    try:
        _calculate(_selection_set(economic_set, [selected_none]))
        raise AssertionError("expected RuntimeError for SELECTED without candidate")
    except RuntimeError:
        pass
    no_status_with_candidate = OrderControlTvtNodeMpCandidateSelectionResult(
        node_name="merge",
        selection_status=(
            OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
        ),
        selected_candidate_economic_result=candidate,
        rng_was_used=False,
    )
    try:
        _calculate(_selection_set(economic_set, [no_status_with_candidate]))
        raise AssertionError("expected RuntimeError for no-candidate with object")
    except RuntimeError:
        pass


def test_rejects_selected_that_is_not_the_input_object():
    original = _candidate_economic_result()
    copied = dataclasses.replace(original)
    economic_set = _economic_set([("merge", [original])])
    selection_set = _selection_set(
        economic_set,
        [_selected_node_result("merge", copied)],
    )
    try:
        _calculate(selection_set)
        raise AssertionError("expected RuntimeError for copied selected object")
    except RuntimeError as error:
        assert "not an object from the input" in str(error)


def test_rejects_infeasible_selected_candidate():
    infeasible = _infeasible_candidate()
    # Force a SELECTED status onto an infeasible candidate.
    economic_set = _economic_set([("merge", [infeasible])])
    selection_set = _selection_set(
        economic_set,
        [_selected_node_result("merge", infeasible)],
    )
    try:
        _calculate(selection_set)
        raise AssertionError("expected RuntimeError for infeasible selected")
    except RuntimeError as error:
        assert "not economically feasible" in str(error)


def test_rejects_non_positive_or_non_finite_g_and_negative_or_non_finite_r():
    base = _candidate_economic_result()
    economic_set = _economic_set([("merge", [base])])
    cases = (
        {"total_buyer_value_G": 0.0},
        {"total_buyer_value_G": -1.0},
        {"total_buyer_value_G": math.inf},
        {"total_buyer_value_G": math.nan},
        {"total_required_compensation_R": -1.0},
        {"total_required_compensation_R": math.inf},
        {"total_required_compensation_R": math.nan},
        {"total_buyer_value_G": 1.0, "total_required_compensation_R": 2.0},
    )
    for changes in cases:
        bad = dataclasses.replace(base, **changes)
        bad_set = _economic_set([("merge", [bad])])
        try:
            _calculate(
                _selection_set(bad_set, [_selected_node_result("merge", bad)])
            )
            raise AssertionError(f"expected RuntimeError for {changes!r}")
        except RuntimeError:
            pass


def test_rejects_empty_buyers_and_bad_g_b_or_r_s():
    empty_buyers = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(_seller_record("seller_a", R_s=2.0),),
    )
    empty_buyers = dataclasses.replace(
        empty_buyers,
        buyer_economic_records=(),
        total_buyer_value_G=6.0,
    )
    try:
        _calculate(
            _selection_set(
                _economic_set([("merge", [empty_buyers])]),
                [_selected_node_result("merge", empty_buyers)],
            )
        )
        raise AssertionError("expected RuntimeError for empty buyers")
    except RuntimeError:
        pass

    nonpositive_g_b = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=0.0),),
        seller_records=(),
        economically_feasible=True,
        total_buyer_value_G=0.0,
        total_required_compensation_R=0.0,
        surplus=0.0,
    )
    nonpositive_g_b = dataclasses.replace(
        nonpositive_g_b,
        total_buyer_value_G=1.0,
        buyer_economic_records=(_buyer_record("buyer_a", G_b=-1.0),),
        economically_feasible=True,
        infeasibility_reasons=(),
    )
    try:
        _calculate(
            _selection_set(
                _economic_set([("merge", [nonpositive_g_b])]),
                [_selected_node_result("merge", nonpositive_g_b)],
            )
        )
        raise AssertionError("expected RuntimeError for G_b <= 0")
    except RuntimeError:
        pass

    negative_r_s = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(_seller_record("seller_a", R_s=-1.0),),
        total_required_compensation_R=2.0,
        surplus=4.0,
    )
    try:
        _calculate(
            _selection_set(
                _economic_set([("merge", [negative_r_s])]),
                [_selected_node_result("merge", negative_r_s)],
            )
        )
        raise AssertionError("expected RuntimeError for R_s < 0")
    except RuntimeError:
        pass


def test_rejects_saved_g_or_r_not_equal_to_explicit_sums():
    mismatched_g = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(_seller_record("seller_a", R_s=2.0),),
        total_buyer_value_G=9.0,
    )
    try:
        _calculate(
            _selection_set(
                _economic_set([("merge", [mismatched_g])]),
                [_selected_node_result("merge", mismatched_g)],
            )
        )
        raise AssertionError("expected RuntimeError for G mismatch")
    except RuntimeError as error:
        assert "G_b" in str(error)

    mismatched_r = _candidate_economic_result(
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(_seller_record("seller_a", R_s=2.0),),
        total_required_compensation_R=1.0,
        surplus=5.0,
    )
    try:
        _calculate(
            _selection_set(
                _economic_set([("merge", [mismatched_r])]),
                [_selected_node_result("merge", mismatched_r)],
            )
        )
        raise AssertionError("expected RuntimeError for R mismatch")
    except RuntimeError as error:
        assert "R_s" in str(error)


def test_one_node_inconsistency_stops_later_nodes_without_partial_result():
    bad = _candidate_economic_result(
        node_name="merge",
        buyer_records=(_buyer_record("buyer_a", G_b=6.0),),
        seller_records=(_seller_record("seller_a", R_s=2.0),),
        total_buyer_value_G=9.0,
    )
    later = _candidate_economic_result(
        node_name="other",
        buyer_records=(_buyer_record("buyer_b", G_b=8.0),),
        seller_records=(),
    )
    economic_set = _economic_set([("merge", [bad]), ("other", [later])])
    selection_set = _selection_set(
        economic_set,
        [
            _selected_node_result("merge", bad),
            _selected_node_result("other", later),
        ],
    )
    later_g_before = later.total_buyer_value_G
    try:
        result = _calculate(selection_set)
        raise AssertionError(f"expected RuntimeError, got {result!r}")
    except RuntimeError:
        pass
    assert later.total_buyer_value_G == later_g_before
    assert selection_set.node_candidate_selection_results[1].selected_candidate_economic_result is later


# ---------------------------------------------------------------------------
# Invariance and out-of-scope
# ---------------------------------------------------------------------------


def test_selection_economic_local_vehicle_and_world_are_unchanged():
    world = _standard_world()
    candidate, economic_set, selection_set = _standard_selected_set()
    before = _world_fingerprint(world)
    local_before = economic_set.local_virtual_calculation_set_result
    fifo_before = local_before.fifo_inspection_set_result
    result = _calculate(selection_set)
    assert _world_fingerprint(world) == before
    assert result.candidate_selection_set_result is selection_set
    assert selection_set.economic_evaluation_set_result is economic_set
    assert economic_set.local_virtual_calculation_set_result is local_before
    assert local_before.fifo_inspection_set_result is fifo_before
    assert candidate.total_buyer_value_G == 6.0
    assert candidate.total_required_compensation_R == 2.0
    assert world.VEHICLES["buyer_a"].payment_paid == 0
    assert world.VEHICLES["seller_a"].payment_received == 0
    assert world.VEHICLES["buyer_a"].order_exchange_log == []
    assert world.VEHICLES["buyer_a"].vot_declared == 1.0
    assert world.VEHICLES["buyer_a"].participates_in_order_exchange is True


def test_does_not_write_vehicle_ledgers_or_final_rank():
    world = _standard_world()
    candidate, _economic_set, selection_set = _standard_selected_set()
    result = _calculate(selection_set)
    node_result = result.node_payment_and_compensation_results[0]
    for obj in (result, node_result, candidate):
        names = _field_names(type(obj))
        assert "final_rank" not in names
        assert "actual" not in names
        assert "payment_paid" not in names
        assert "payment_received" not in names
        assert "order_exchange_log" not in names
    assert world.VEHICLES["buyer_a"].payment_paid == 0
    assert world.VEHICLES["seller_a"].payment_received == 0
    assert world.VEHICLES["buyer_a"].order_exchange_log == []
    assert not hasattr(candidate, "selected")
    assert RANK_STATE_SENTINEL is RANK_STATE_SENTINEL
    assert COLLECTOR_SENTINEL is COLLECTOR_SENTINEL


def test_production_source_keeps_required_shape_and_forbids_out_of_scope_work():
    source_text = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    called_names = set()
    imported_modules = set()
    public_function_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            else:
                imported_modules.add((node.module or "").split(".")[0])
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith("_"):
                public_function_names.append(node.name)
    forbidden_calls = {
        "exec_simulation",
        "evaluate_tvt_mp_candidate_economics",
        "select_tvt_mp_candidates",
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
        "run_tvt_mp_candidate_local_virtual_calculation",
        "build_tvt_mp_fifo_inspection_results",
        "build_tvt_mp_general_trade_ranks",
        "ThreadPoolExecutor",
        "Pool",
        "hash",
        "id",
        "deepcopy",
        "Decimal",
        "round",
    }
    assert called_names.isdisjoint(forbidden_calls)
    assert public_function_names == ["calculate_tvt_mp_payments_and_compensations"]
    assert "dataclass(frozen=True)" in source_text
    assert "for node_selection_result in node_selection_results:" in source_text
    assert "for buyer_economic_record in buyer_economic_records:" in source_text
    assert "for seller_economic_record in seller_economic_records:" in source_text
    assert "payment_P_b = R * G_b / G" in source_text
    assert "compensation_amount = required_compensation_R_s" in source_text
    assert "declared VOT = 0" in source_text
    assert "payment_paid" not in source_text
    assert "payment_received" not in source_text
    assert "order_exchange_log" not in source_text
    assert "actual_passage" not in source_text
    assert "final_rank" not in source_text
    assert "real_W" not in source_text
    assert "VEHICLES" not in source_text
    attribute_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            attribute_names.add(node.attr)
    assert "rng" not in attribute_names
    assert "order_control_rng" not in attribute_names
    assert "World" not in imported_modules
    assert "decimal" not in imported_modules
    assert "numpy" not in imported_modules


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


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
    assert len(TESTS) == len(defined_functions)
    assert len(set(TESTS)) == len(TESTS)


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
