# Tests for TVT-MP resolved-candidate economic evaluation.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_economic_evaluation.py

from __future__ import annotations

import ast
import copy
import dataclasses
import inspect
import math
from pathlib import Path
import numpy as np

from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateFinalNodeRecord,
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
    OrderControlTvtMpCandidatePassageRecord,
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
    evaluate_tvt_mp_candidate_economics,
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
from uxsim.uxsim import World


PRODUCTION_PATH = Path("uxsim/order_control_tvt_mp_economic_evaluation.py")
BASELINE_T = 10
FIFO_SENTINEL = object()

_FORBIDDEN_RESULT_FIELD_NAMES = {
    "true_vot",
    "payment",
    "compensation",
    "selected",
    "selected_candidate",
    "candidate_id",
    "actual_passage_timestep",
    "actual_time_saving",
    "actual_waiting_increase",
    "prediction_error",
    "realized_utility",
    "ex_post_welfare",
    "final_rank",
}


# ---------------------------------------------------------------------------
# Small explicit fixtures
# ---------------------------------------------------------------------------


def _visit_key(vehicle_name: str, visit_id: int = 1):
    return (vehicle_name, visit_id)


def _new_world(*, name: str = "tvt_mp_economics", reaction_time: float = 1.0):
    world = World(
        name=name,
        deltan=1,
        reaction_time=reaction_time,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig", 0, 0)
    world.addNode("merge", 1, 0)
    world.addNode("dest", 2, 0)
    world.addLink("in_a", "orig", "merge", length=200, free_flow_speed=20)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20)
    return world


def _add_vehicle(
    world,
    name: str,
    *,
    vot_declared,
    vot_true=None,
    participates_in_order_exchange=True,
):
    if vot_true is None:
        vot_true = vot_declared
    world.addVehicle(
        "orig",
        "dest",
        0,
        name=name,
        vot_declared=vot_declared,
        vot_true=vot_true,
        participates_in_order_exchange=participates_in_order_exchange,
    )
    return world.VEHICLES[name]


def _world_with_vehicles(vehicle_specs, *, reaction_time: float = 1.0):
    world = _new_world(reaction_time=reaction_time)
    for spec in vehicle_specs:
        _add_vehicle(
            world,
            spec["name"],
            vot_declared=spec.get("vot_declared", 1.0),
            vot_true=spec.get("vot_true", spec.get("vot_declared", 1.0)),
            participates_in_order_exchange=spec.get(
                "participates_in_order_exchange",
                True,
            ),
        )
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    world.T = BASELINE_T
    return world


def _binding_visit(
    vehicle_name: str,
    *,
    rank: int,
    role: OrderControlTvtMpLocalBindingTradeRole,
    visit_id: int = 1,
    vehicle_id: int = 0,
    inlink_name: str = "in_a",
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
        inlink_name=inlink_name,
        baseline_arrival_timestep=BASELINE_T,
        arrival_tiebreaker=0.1,
        trade_role=role,
    )


def _passage(
    vehicle_name: str,
    *,
    role: OrderControlTvtMpLocalBindingTradeRole,
    baseline_passage_timestep,
    candidate_passage_timestep,
    rank: int = 1,
    visit_id: int = 1,
):
    return OrderControlTvtMpCandidatePassageRecord(
        visit_key=_visit_key(vehicle_name, visit_id),
        vehicle_name=vehicle_name,
        trade_role=role,
        binding_partition=(
            OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ),
        binding_rank=rank,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        route_next_link_name="out",
        route_origin=(
            OrderControlTvtMpLocalBindingRouteOrigin.SNAPSHOT_ROUTE_ALREADY_DECIDED
        ),
        inlink_name="in_a",
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
    buyer_names: tuple[str, ...] = ("buyer_a",),
    seller_names: tuple[str, ...] = ("seller_a",),
    buyer_passages: dict | None = None,
    seller_passages: dict | None = None,
    resolved: bool = True,
    stop_reason=None,
    extra_passages=(),
    buyers_sorted=None,
    binding_visits=None,
    baseline_timestep_T: int = BASELINE_T,
    configured_horizon_steps: int = 6,
    force_passages=None,
    sequence_buyer_set=None,
):
    if buyer_passages is None:
        buyer_passages = {}
    if seller_passages is None:
        seller_passages = {}
    visits = []
    rank = 1
    for name in buyer_names:
        visits.append(
            _binding_visit(
                name,
                rank=rank,
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
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
    if binding_visits is not None:
        visits = list(binding_visits)
    visits = tuple(visits)
    if buyers_sorted is None:
        buyers_sorted = tuple(_visit_key(name) for name in buyer_names)
    buyer_set = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=buyers_sorted,
    )
    if sequence_buyer_set is None:
        sequence_buyer_set = buyer_set
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=baseline_timestep_T,
        concrete_buyer_candidate_set=sequence_buyer_set,
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=visits,
        k_last_buyer=len(buyer_names),
        k_decision_window=len(visits),
        k_fixed=len(visits),
    )
    if force_passages is not None:
        passages = tuple(force_passages)
    else:
        passages = []
        rank = 1
        for name in buyer_names:
            times = buyer_passages.get(name, {"baseline": 12, "candidate": 10})
            passages.append(
                _passage(
                    name,
                    role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                    baseline_passage_timestep=times["baseline"],
                    candidate_passage_timestep=times["candidate"],
                    rank=rank,
                )
            )
            rank = rank + 1
        for name in seller_names:
            times = seller_passages.get(name, {"baseline": 10, "candidate": 12})
            passages.append(
                _passage(
                    name,
                    role=OrderControlTvtMpLocalBindingTradeRole.SELLER,
                    baseline_passage_timestep=times["baseline"],
                    candidate_passage_timestep=times["candidate"],
                    rank=rank,
                )
            )
            rank = rank + 1
        for extra in extra_passages:
            passages.append(extra)
        passages = tuple(passages)
    if resolved is True:
        default_stop = (
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
        )
    else:
        default_stop = (
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
        )
    if stop_reason is None:
        stop_reason = default_stop
    return OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name=node_name,
        concrete_buyer_candidate_set=buyer_set,
        binding_rank_sequence=sequence,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=configured_horizon_steps,
        final_virtual_timestep=baseline_timestep_T,
        final_offset=0,
        simulated_timestep_count=1,
        stop_reason=stop_reason,
        resolved=resolved,
        required_passage_records=passages,
        unresolved_reasons=(),
        timestep_results=(),
        final_vehicle_records=(),
        final_inlink_records=(),
        final_outlink_records=(),
        final_node_record=_final_node_record(node_name),
        final_boundary_records=(),
    )


def _node_local_result(
    node_name: str,
    candidates,
    *,
    build_status=OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE,
):
    return OrderControlTvtNodeMpLocalVirtualCalculationResult(
        node_name=node_name,
        build_status=build_status,
        candidate_local_virtual_calculation_results=tuple(candidates),
    )


def _set_result(node_results, *, fifo_inspection_set_result=FIFO_SENTINEL):
    return OrderControlTvtMpLocalVirtualCalculationSetResult(
        fifo_inspection_set_result=fifo_inspection_set_result,
        node_local_virtual_calculation_results=tuple(node_results),
    )


def _standard_buyer_seller_world():
    return _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 2.0},
            {"name": "seller_a", "vot_declared": 1.0},
        ]
    )


def _standard_feasible_candidate(*, node_name: str = "merge"):
    return _candidate_local_result(
        node_name=node_name,
        buyer_names=("buyer_a",),
        seller_names=("seller_a",),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
        seller_passages={"seller_a": {"baseline": 10, "candidate": 12}},
    )


def _evaluate(local_set_result, world):
    return evaluate_tvt_mp_candidate_economics(local_set_result, world)


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


def test_infeasibility_reason_enum_members_and_values():
    reason = OrderControlTvtMpCandidateEconomicInfeasibilityReason
    assert reason.BUYER_NONPOSITIVE_VALUE.value == "buyer_nonpositive_value"
    assert (
        reason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION.value
        == "total_buyer_value_below_required_compensation"
    )
    names = []
    for member in reason:
        names.append(member.name)
    assert names == [
        "BUYER_NONPOSITIVE_VALUE",
        "TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION",
    ]


def test_buyer_seller_candidate_node_and_set_results_are_frozen():
    for cls in (
        OrderControlTvtMpBuyerEconomicRecord,
        OrderControlTvtMpSellerEconomicRecord,
        OrderControlTvtMpCandidateEconomicEvaluationResult,
        OrderControlTvtNodeMpEconomicEvaluationResult,
        OrderControlTvtMpEconomicEvaluationSetResult,
    ):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True


def test_public_result_field_order_and_forbidden_fields():
    assert _field_names(OrderControlTvtMpBuyerEconomicRecord) == [
        "visit_key",
        "vehicle_name",
        "declared_vot_per_second",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "expected_time_saving_timesteps",
        "expected_time_saving_seconds",
        "gross_time_value_G_b",
        "passes_positive_buyer_value_condition",
    ]
    assert _field_names(OrderControlTvtMpSellerEconomicRecord) == [
        "visit_key",
        "vehicle_name",
        "declared_vot_per_second",
        "baseline_passage_timestep",
        "candidate_passage_timestep",
        "raw_passage_difference_timesteps",
        "expected_waiting_increase_timesteps",
        "raw_passage_difference_seconds",
        "expected_waiting_increase_seconds",
        "required_compensation_R_s",
    ]
    assert _field_names(OrderControlTvtMpCandidateEconomicEvaluationResult) == [
        "candidate_local_virtual_calculation_result",
        "buyer_economic_records",
        "seller_economic_records",
        "total_buyer_value_G",
        "total_required_compensation_R",
        "surplus",
        "economically_feasible",
        "infeasibility_reasons",
    ]
    assert _field_names(OrderControlTvtNodeMpEconomicEvaluationResult) == [
        "node_name",
        "candidate_economic_evaluation_results",
    ]
    assert _field_names(OrderControlTvtMpEconomicEvaluationSetResult) == [
        "local_virtual_calculation_set_result",
        "node_economic_evaluation_results",
    ]
    for cls in (
        OrderControlTvtMpBuyerEconomicRecord,
        OrderControlTvtMpSellerEconomicRecord,
        OrderControlTvtMpCandidateEconomicEvaluationResult,
        OrderControlTvtNodeMpEconomicEvaluationResult,
        OrderControlTvtMpEconomicEvaluationSetResult,
    ):
        names = set(_field_names(cls))
        assert names.isdisjoint(_FORBIDDEN_RESULT_FIELD_NAMES)
        assert "count" not in names
        assert "n_candidates" not in names
        assert "n_buyers" not in names
        assert "n_sellers" not in names
        assert "true_vot" not in names


def test_public_columns_are_tuples_and_keep_input_objects():
    world = _standard_buyer_seller_world()
    candidate = _standard_feasible_candidate()
    local_set = _set_result([_node_local_result("merge", [candidate])])
    result = _evaluate(local_set, world)
    assert result.local_virtual_calculation_set_result is local_set
    assert isinstance(result.node_economic_evaluation_results, tuple)
    node_result = result.node_economic_evaluation_results[0]
    assert isinstance(node_result.candidate_economic_evaluation_results, tuple)
    candidate_result = node_result.candidate_economic_evaluation_results[0]
    assert candidate_result.candidate_local_virtual_calculation_result is candidate
    assert isinstance(candidate_result.buyer_economic_records, tuple)
    assert isinstance(candidate_result.seller_economic_records, tuple)
    assert isinstance(candidate_result.infeasibility_reasons, tuple)
    assert type(candidate_result.economically_feasible) is bool
    assert type(candidate_result.buyer_economic_records[0].passes_positive_buyer_value_condition) is bool


def test_result_does_not_keep_live_world_vehicle_node_or_link():
    world = _standard_buyer_seller_world()
    candidate = _standard_feasible_candidate()
    local_set = _set_result([_node_local_result("merge", [candidate])])
    result = _evaluate(local_set, world)
    dumped = str(result)
    assert "World(" not in dumped
    candidate_result = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results[0]
    for field in dataclasses.fields(candidate_result):
        value = getattr(candidate_result, field.name)
        assert not isinstance(value, World)
    buyer = candidate_result.buyer_economic_records[0]
    assert buyer.vehicle_name == "buyer_a"
    assert not hasattr(buyer, "vehicle")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def test_public_api_is_one_positional_function_without_mapping_or_node_helpers():
    import uxsim.order_control_tvt_mp_economic_evaluation as module

    signature = inspect.signature(evaluate_tvt_mp_candidate_economics)
    parameter_names = list(signature.parameters)
    assert parameter_names == [
        "local_virtual_calculation_set_result",
        "real_W",
    ]
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert parameter.default is inspect.Parameter.empty
    assert not hasattr(module, "initialize_tvt_mp_economic_evaluation")
    assert not hasattr(module, "evaluate_tvt_mp_node_economics")
    assert not hasattr(module, "evaluate_tvt_mp_one_candidate_economics")
    source = inspect.getsource(evaluate_tvt_mp_candidate_economics)
    assert "vot_mapping" not in source
    assert "payment_rule" not in source
    assert "compensation_rule" not in source


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_rejects_non_world_and_non_local_set_result():
    world = _standard_buyer_seller_world()
    candidate = _standard_feasible_candidate()
    local_set = _set_result([_node_local_result("merge", [candidate])])
    try:
        evaluate_tvt_mp_candidate_economics(local_set, "not-a-world")
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "World" in str(error)
    try:
        evaluate_tvt_mp_candidate_economics("not-a-set", world)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "LocalVirtualCalculationSetResult" in str(error)


def test_rejects_invalid_deltat_values():
    world = _standard_buyer_seller_world()
    candidate = _standard_feasible_candidate()
    local_set = _set_result([_node_local_result("merge", [candidate])])
    invalid_values = (
        0,
        -1,
        True,
        False,
        None,
        "1",
        math.nan,
        math.inf,
        -math.inf,
    )
    original = world.DELTAT
    for invalid in invalid_values:
        world.DELTAT = invalid
        try:
            evaluate_tvt_mp_candidate_economics(local_set, world)
            raise AssertionError(f"expected ValueError for DELTAT={invalid!r}")
        except ValueError:
            pass
    world.DELTAT = original


# ---------------------------------------------------------------------------
# VOT legal and illegal
# ---------------------------------------------------------------------------


def test_accepts_positive_int_positive_float_zero_and_zero_float_vot():
    world = _world_with_vehicles(
        [
            {"name": "buyer_int", "vot_declared": 3},
            {"name": "buyer_float", "vot_declared": 2.5},
            {"name": "buyer_zero", "vot_declared": 0},
            {"name": "buyer_zero_float", "vot_declared": 0.0},
        ]
    )
    cases = (
        ("buyer_int", 3.0, True),
        ("buyer_float", 2.5, True),
        ("buyer_zero", 0.0, False),
        ("buyer_zero_float", 0.0, False),
    )
    candidates = []
    for name, _declared, _feasible in cases:
        candidates.append(
            _candidate_local_result(
                buyer_names=(name,),
                seller_names=(),
                buyer_passages={name: {"baseline": 12, "candidate": 10}},
            )
        )
    local_set = _set_result([_node_local_result("merge", candidates)])
    result = _evaluate(local_set, world)
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    assert len(evaluated) == 4
    for index, (name, declared, feasible) in enumerate(cases):
        buyer = evaluated[index].buyer_economic_records[0]
        assert buyer.vehicle_name == name
        assert buyer.declared_vot_per_second == declared
        assert type(buyer.declared_vot_per_second) is float
        assert buyer.expected_time_saving_timesteps == 2
        assert evaluated[index].economically_feasible is feasible


def test_rejects_illegal_declared_vot_values():
    illegal_values = (
        -1,
        -0.5,
        True,
        False,
        None,
        "1.0",
        math.nan,
        math.inf,
        -math.inf,
        np.bool_(True),
        np.int64(2),
    )
    for illegal in illegal_values:
        world = _world_with_vehicles([{"name": "buyer_a", "vot_declared": 1.0}])
        world.VEHICLES["buyer_a"].vot_declared = illegal
        candidate = _candidate_local_result(
            buyer_names=("buyer_a",),
            seller_names=(),
        )
        local_set = _set_result([_node_local_result("merge", [candidate])])
        try:
            evaluate_tvt_mp_candidate_economics(local_set, world)
            raise AssertionError(f"expected ValueError for vot={illegal!r}")
        except ValueError:
            pass


def test_accepts_numpy_float64_declared_vot():
    world = _world_with_vehicles([{"name": "buyer_a", "vot_declared": 1.0}])
    world.VEHICLES["buyer_a"].vot_declared = np.float64(2.0)
    candidate = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
    )
    local_set = _set_result([_node_local_result("merge", [candidate])])
    result = _evaluate(local_set, world)
    buyer = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results[0].buyer_economic_records[0]
    assert buyer.declared_vot_per_second == 2.0
    assert type(buyer.declared_vot_per_second) is float
    assert buyer.gross_time_value_G_b == 4.0


def test_missing_vehicle_and_missing_vot_declared_are_value_error():
    world = _world_with_vehicles([{"name": "other", "vot_declared": 1.0}])
    candidate = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
    )
    local_set = _set_result([_node_local_result("merge", [candidate])])
    try:
        evaluate_tvt_mp_candidate_economics(local_set, world)
        raise AssertionError("expected ValueError for missing vehicle")
    except ValueError as error:
        assert "buyer_a" in str(error)

    world = _world_with_vehicles([{"name": "buyer_a", "vot_declared": 1.0}])
    delattr(world.VEHICLES["buyer_a"], "vot_declared")
    candidate = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
    )
    local_set = _set_result([_node_local_result("merge", [candidate])])
    try:
        evaluate_tvt_mp_candidate_economics(local_set, world)
        raise AssertionError("expected ValueError for missing vot_declared")
    except ValueError as error:
        assert "vot_declared" in str(error)


# ---------------------------------------------------------------------------
# VOT=0 buyer and seller
# ---------------------------------------------------------------------------


def test_vot_zero_buyer_is_normal_economic_infeasibility_and_later_candidate_is_evaluated():
    world = _world_with_vehicles(
        [
            {"name": "buyer_zero", "vot_declared": 0, "vot_true": 0},
            {"name": "buyer_later", "vot_declared": 2.0},
        ]
    )
    first = _candidate_local_result(
        buyer_names=("buyer_zero",),
        seller_names=(),
        buyer_passages={"buyer_zero": {"baseline": 14, "candidate": 11}},
    )
    second = _candidate_local_result(
        buyer_names=("buyer_later",),
        seller_names=(),
        buyer_passages={"buyer_later": {"baseline": 12, "candidate": 10}},
    )
    local_set = _set_result([_node_local_result("merge", [first, second])])
    result = _evaluate(local_set, world)
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    assert len(evaluated) == 2
    zero_buyer = evaluated[0].buyer_economic_records[0]
    assert zero_buyer.declared_vot_per_second == 0.0
    assert zero_buyer.expected_time_saving_timesteps == 3
    assert zero_buyer.expected_time_saving_seconds == 3.0
    assert zero_buyer.gross_time_value_G_b == 0.0
    assert zero_buyer.passes_positive_buyer_value_condition is False
    assert evaluated[0].economically_feasible is False
    assert evaluated[0].infeasibility_reasons == (
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
    )
    assert evaluated[1].economically_feasible is True
    assert world.VEHICLES["buyer_zero"].participates_in_order_exchange is True
    assert evaluated[0].buyer_economic_records[0].vehicle_name == "buyer_zero"


def test_vot_zero_seller_keeps_waiting_increase_and_zero_reservation():
    world = _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 2.0},
            {"name": "seller_zero", "vot_declared": 0.0, "vot_true": 0.0},
            {"name": "buyer_later", "vot_declared": 1.0},
        ]
    )
    first = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_zero",),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
        seller_passages={"seller_zero": {"baseline": 10, "candidate": 15}},
    )
    second = _candidate_local_result(
        buyer_names=("buyer_later",),
        seller_names=(),
        buyer_passages={"buyer_later": {"baseline": 11, "candidate": 10}},
    )
    local_set = _set_result([_node_local_result("merge", [first, second])])
    result = _evaluate(local_set, world)
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    seller = evaluated[0].seller_economic_records[0]
    assert seller.declared_vot_per_second == 0.0
    assert seller.raw_passage_difference_timesteps == 5
    assert seller.expected_waiting_increase_timesteps == 5
    assert seller.expected_waiting_increase_seconds == 5.0
    assert seller.required_compensation_R_s == 0.0
    assert evaluated[0].total_required_compensation_R == 0.0
    assert evaluated[0].total_buyer_value_G == 4.0
    assert evaluated[0].economically_feasible is True
    assert evaluated[1].economically_feasible is True
    assert world.VEHICLES["seller_zero"].participates_in_order_exchange is True
    assert seller.vehicle_name == "seller_zero"
    assert evaluated[0].buyer_economic_records[0].gross_time_value_G_b == 4.0


# ---------------------------------------------------------------------------
# Non-participation distinction
# ---------------------------------------------------------------------------


def test_nonparticipating_vehicle_is_not_evaluated_and_vot_zero_participant_is():
    world = _world_with_vehicles(
        [
            {"name": "buyer_zero", "vot_declared": 0.0},
            {
                "name": "outsider",
                "vot_declared": None,
                "vot_true": None,
                "participates_in_order_exchange": False,
            },
        ]
    )
    candidate = _candidate_local_result(
        buyer_names=("buyer_zero",),
        seller_names=(),
        buyer_passages={"buyer_zero": {"baseline": 12, "candidate": 10}},
    )
    local_set = _set_result([_node_local_result("merge", [candidate])])
    result = _evaluate(local_set, world)
    candidate_result = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results[0]
    assert len(candidate_result.buyer_economic_records) == 1
    assert candidate_result.buyer_economic_records[0].vehicle_name == "buyer_zero"
    assert candidate_result.seller_economic_records == ()
    assert world.VEHICLES["outsider"].participates_in_order_exchange is False
    assert world.VEHICLES["buyer_zero"].participates_in_order_exchange is True
    assert world.VEHICLES["outsider"].vot_declared is None


# ---------------------------------------------------------------------------
# Time differences
# ---------------------------------------------------------------------------


def test_buyer_positive_zero_and_negative_time_saving():
    world = _world_with_vehicles(
        [
            {"name": "buyer_pos", "vot_declared": 2.0},
            {"name": "buyer_zero", "vot_declared": 2.0},
            {"name": "buyer_neg", "vot_declared": 2.0},
        ]
    )
    cases = (
        ("buyer_pos", 12, 10, 2, 4.0, True),
        ("buyer_zero", 10, 10, 0, 0.0, False),
        ("buyer_neg", 10, 13, -3, -6.0, False),
    )
    candidates = []
    for name, baseline, candidate_time, _saving, _g, _ok in cases:
        candidates.append(
            _candidate_local_result(
                buyer_names=(name,),
                seller_names=(),
                buyer_passages={
                    name: {"baseline": baseline, "candidate": candidate_time}
                },
            )
        )
    result = _evaluate(_set_result([_node_local_result("merge", candidates)]), world)
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    for index, (name, baseline, candidate_time, saving, g_b, ok) in enumerate(cases):
        buyer = evaluated[index].buyer_economic_records[0]
        assert buyer.expected_time_saving_timesteps == saving
        assert buyer.expected_time_saving_seconds == saving * 1.0
        assert buyer.gross_time_value_G_b == g_b
        assert buyer.passes_positive_buyer_value_condition is ok
        assert evaluated[index].economically_feasible is ok


def test_seller_delay_same_time_and_early_passage():
    world = _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 2.0},
            {"name": "seller_delay", "vot_declared": 3.0},
            {"name": "seller_same", "vot_declared": 3.0},
            {"name": "seller_early", "vot_declared": 3.0},
        ]
    )
    cases = (
        ("seller_delay", 10, 14, 4, 4, 12.0, False),
        ("seller_same", 10, 10, 0, 0, 0.0, True),
        ("seller_early", 14, 10, -4, 0, 0.0, True),
    )
    candidates = []
    for name, baseline, candidate_time, raw, waiting, r_s, _feasible in cases:
        candidates.append(
            _candidate_local_result(
                buyer_names=("buyer_a",),
                seller_names=(name,),
                buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
                seller_passages={
                    name: {"baseline": baseline, "candidate": candidate_time}
                },
            )
        )
    result = _evaluate(_set_result([_node_local_result("merge", candidates)]), world)
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    for index, (name, baseline, candidate_time, raw, waiting, r_s, feasible) in enumerate(cases):
        seller = evaluated[index].seller_economic_records[0]
        assert seller.raw_passage_difference_timesteps == raw
        assert seller.expected_waiting_increase_timesteps == waiting
        assert seller.raw_passage_difference_seconds == raw * 1.0
        assert seller.expected_waiting_increase_seconds == waiting * 1.0
        assert seller.required_compensation_R_s == r_s
        assert evaluated[index].buyer_economic_records[0].gross_time_value_G_b == 4.0
        assert evaluated[index].economically_feasible is feasible


def test_seconds_use_deltat_other_than_one_and_horizon_endpoint():
    world = _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 2.0},
            {"name": "seller_a", "vot_declared": 1.0},
        ],
        reaction_time=2.0,
    )
    assert world.DELTAT == 2.0
    candidate = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a",),
        buyer_passages={"buyer_a": {"baseline": 15, "candidate": 10}},
        seller_passages={"seller_a": {"baseline": 10, "candidate": 15}},
        configured_horizon_steps=6,
    )
    result = _evaluate(_set_result([_node_local_result("merge", [candidate])]), world)
    candidate_result = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results[0]
    buyer = candidate_result.buyer_economic_records[0]
    seller = candidate_result.seller_economic_records[0]
    assert buyer.expected_time_saving_timesteps == 5
    assert buyer.expected_time_saving_seconds == 10.0
    assert buyer.gross_time_value_G_b == 20.0
    assert seller.raw_passage_difference_timesteps == 5
    assert seller.expected_waiting_increase_seconds == 10.0
    assert seller.required_compensation_R_s == 10.0
    assert candidate_result.surplus == 10.0
    assert candidate_result.economically_feasible is True


# ---------------------------------------------------------------------------
# Economic conditions
# ---------------------------------------------------------------------------


def test_all_buyers_positive_g_greater_equal_and_less_than_r():
    world = _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 2.0},
            {"name": "buyer_b", "vot_declared": 1.0},
            {"name": "seller_a", "vot_declared": 2.0},
            {"name": "seller_b", "vot_declared": 1.0},
        ]
    )
    greater = _candidate_local_result(
        buyer_names=("buyer_a", "buyer_b"),
        seller_names=("seller_a",),
        buyer_passages={
            "buyer_a": {"baseline": 12, "candidate": 10},
            "buyer_b": {"baseline": 13, "candidate": 10},
        },
        seller_passages={"seller_a": {"baseline": 10, "candidate": 11}},
    )
    equal = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a",),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
        seller_passages={"seller_a": {"baseline": 10, "candidate": 12}},
    )
    below = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a", "seller_b"),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
        seller_passages={
            "seller_a": {"baseline": 10, "candidate": 12}},
    )
    # Rebuild below with both sellers delayed enough that R > G.
    below = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a", "seller_b"),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
        seller_passages={
            "seller_a": {"baseline": 10, "candidate": 12},
            "seller_b": {"baseline": 10, "candidate": 13},
        },
    )
    result = _evaluate(
        _set_result([_node_local_result("merge", [greater, equal, below])]),
        world,
    )
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    # G = 2*2 + 1*3 = 7, R = 2*1 = 2, surplus = 5
    assert evaluated[0].total_buyer_value_G == 7.0
    assert evaluated[0].total_required_compensation_R == 2.0
    assert evaluated[0].surplus == 5.0
    assert evaluated[0].economically_feasible is True
    assert evaluated[0].infeasibility_reasons == ()
    # G = 2*2 = 4, R = 2*2 = 4
    assert evaluated[1].total_buyer_value_G == 4.0
    assert evaluated[1].total_required_compensation_R == 4.0
    assert evaluated[1].surplus == 0.0
    assert evaluated[1].economically_feasible is True
    # G = 4, R = 2*2 + 1*3 = 7
    assert evaluated[2].total_buyer_value_G == 4.0
    assert evaluated[2].total_required_compensation_R == 7.0
    assert evaluated[2].surplus == -3.0
    assert evaluated[2].economically_feasible is False
    assert evaluated[2].infeasibility_reasons == (
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION,
    )


def test_one_buyer_zero_one_buyer_negative_empty_sellers_and_two_reasons():
    world = _world_with_vehicles(
        [
            {"name": "buyer_pos", "vot_declared": 2.0},
            {"name": "buyer_zero", "vot_declared": 2.0},
            {"name": "buyer_neg", "vot_declared": 2.0},
            {"name": "seller_a", "vot_declared": 5.0},
        ]
    )
    zero_buyer = _candidate_local_result(
        buyer_names=("buyer_pos", "buyer_zero"),
        seller_names=(),
        buyer_passages={
            "buyer_pos": {"baseline": 12, "candidate": 10},
            "buyer_zero": {"baseline": 10, "candidate": 10},
        },
    )
    negative_buyer = _candidate_local_result(
        buyer_names=("buyer_neg",),
        seller_names=(),
        buyer_passages={"buyer_neg": {"baseline": 10, "candidate": 12}},
    )
    empty_seller_ok = _candidate_local_result(
        buyer_names=("buyer_pos",),
        seller_names=(),
        buyer_passages={"buyer_pos": {"baseline": 12, "candidate": 10}},
    )
    two_reasons = _candidate_local_result(
        buyer_names=("buyer_zero",),
        seller_names=("seller_a",),
        buyer_passages={"buyer_zero": {"baseline": 10, "candidate": 10}},
        seller_passages={"seller_a": {"baseline": 10, "candidate": 12}},
    )
    result = _evaluate(
        _set_result(
            [
                _node_local_result(
                    "merge",
                    [zero_buyer, negative_buyer, empty_seller_ok, two_reasons],
                )
            ]
        ),
        world,
    )
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    assert evaluated[0].economically_feasible is False
    assert evaluated[0].infeasibility_reasons == (
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
    )
    assert evaluated[1].buyer_economic_records[0].gross_time_value_G_b == -4.0
    assert evaluated[1].infeasibility_reasons == (
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION,
    )
    assert evaluated[2].seller_economic_records == ()
    assert evaluated[2].total_required_compensation_R == 0.0
    assert evaluated[2].economically_feasible is True
    assert evaluated[3].infeasibility_reasons == (
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
        OrderControlTvtMpCandidateEconomicInfeasibilityReason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION,
    )
    assert len(evaluated[3].infeasibility_reasons) == 2
    assert evaluated[3].economically_feasible is False


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def test_node_candidate_buyer_and_seller_order_are_preserved():
    world = _world_with_vehicles(
        [
            {"name": "buyer_b", "vot_declared": 1.0},
            {"name": "buyer_a", "vot_declared": 1.0},
            {"name": "seller_b", "vot_declared": 1.0},
            {"name": "seller_a", "vot_declared": 1.0},
            {"name": "buyer_n2", "vot_declared": 1.0},
        ]
    )
    first_on_merge = _candidate_local_result(
        node_name="merge",
        buyer_names=("buyer_b", "buyer_a"),
        seller_names=("seller_b", "seller_a"),
        buyer_passages={
            "buyer_b": {"baseline": 12, "candidate": 10},
            "buyer_a": {"baseline": 13, "candidate": 10},
        },
        seller_passages={
            "seller_b": {"baseline": 10, "candidate": 11},
            "seller_a": {"baseline": 10, "candidate": 12},
        },
    )
    second_on_merge = _candidate_local_result(
        node_name="merge",
        buyer_names=("buyer_a",),
        seller_names=(),
        buyer_passages={"buyer_a": {"baseline": 11, "candidate": 10}},
    )
    other_node = _candidate_local_result(
        node_name="side",
        buyer_names=("buyer_n2",),
        seller_names=(),
        buyer_passages={"buyer_n2": {"baseline": 12, "candidate": 10}},
    )
    local_set = _set_result(
        [
            _node_local_result("merge", [first_on_merge, second_on_merge]),
            _node_local_result("side", [other_node]),
        ]
    )
    result = _evaluate(local_set, world)
    node_names = []
    for node_result in result.node_economic_evaluation_results:
        node_names.append(node_result.node_name)
    assert node_names == ["merge", "side"]
    merge_candidates = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    assert merge_candidates[0].candidate_local_virtual_calculation_result is first_on_merge
    assert merge_candidates[1].candidate_local_virtual_calculation_result is second_on_merge
    buyer_names = []
    for record in merge_candidates[0].buyer_economic_records:
        buyer_names.append(record.vehicle_name)
    seller_names = []
    for record in merge_candidates[0].seller_economic_records:
        seller_names.append(record.vehicle_name)
    assert buyer_names == ["buyer_b", "buyer_a"]
    assert seller_names == ["seller_b", "seller_a"]


# ---------------------------------------------------------------------------
# Out of evaluation scope
# ---------------------------------------------------------------------------


def test_unresolved_is_skipped_without_reading_vot_or_building_records():
    world = _world_with_vehicles(
        [
            {"name": "buyer_bad", "vot_declared": None},
            {"name": "buyer_ok", "vot_declared": 2.0},
        ]
    )
    unresolved = _candidate_local_result(
        buyer_names=("buyer_bad",),
        seller_names=(),
        resolved=False,
        force_passages=(
            _passage(
                "buyer_bad",
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                baseline_passage_timestep=None,
                candidate_passage_timestep=None,
            ),
        ),
    )
    resolved = _candidate_local_result(
        buyer_names=("buyer_ok",),
        seller_names=(),
        buyer_passages={"buyer_ok": {"baseline": 12, "candidate": 10}},
    )
    local_set = _set_result(
        [_node_local_result("merge", [unresolved, resolved])]
    )
    result = _evaluate(local_set, world)
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    assert len(evaluated) == 1
    assert evaluated[0].candidate_local_virtual_calculation_result is resolved
    assert world.VEHICLES["buyer_bad"].vot_declared is None


def test_empty_candidate_tuple_is_fifo_false_or_no_resolved_and_keeps_node():
    world = _standard_buyer_seller_world()
    local_set = _set_result([_node_local_result("merge", [])])
    result = _evaluate(local_set, world)
    assert len(result.node_economic_evaluation_results) == 1
    assert result.node_economic_evaluation_results[0].candidate_economic_evaluation_results == ()
    assert result.local_virtual_calculation_set_result is local_set


# ---------------------------------------------------------------------------
# Serious inconsistency
# ---------------------------------------------------------------------------


def test_resolved_with_none_or_bool_passage_is_runtime_error():
    world = _standard_buyer_seller_world()
    none_baseline = _candidate_local_result(
        force_passages=(
            _passage(
                "buyer_a",
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                baseline_passage_timestep=None,
                candidate_passage_timestep=10,
            ),
        ),
        seller_names=(),
    )
    local_set = _set_result([_node_local_result("merge", [none_baseline])])
    try:
        evaluate_tvt_mp_candidate_economics(local_set, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    none_candidate = _candidate_local_result(
        force_passages=(
            _passage(
                "buyer_a",
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                baseline_passage_timestep=12,
                candidate_passage_timestep=None,
            ),
        ),
        seller_names=(),
    )
    local_set = _set_result([_node_local_result("merge", [none_candidate])])
    try:
        evaluate_tvt_mp_candidate_economics(local_set, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    bool_timestep = _candidate_local_result(
        force_passages=(
            _passage(
                "buyer_a",
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                baseline_passage_timestep=True,
                candidate_passage_timestep=10,
            ),
        ),
        seller_names=(),
    )
    local_set = _set_result([_node_local_result("merge", [bool_timestep])])
    try:
        evaluate_tvt_mp_candidate_economics(local_set, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_empty_buyers_role_and_set_mismatches_are_runtime_error():
    world = _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 1.0},
            {"name": "seller_a", "vot_declared": 1.0},
        ]
    )
    empty_buyers = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a",),
        force_passages=(
            _passage(
                "seller_a",
                role=OrderControlTvtMpLocalBindingTradeRole.SELLER,
                baseline_passage_timestep=10,
                candidate_passage_timestep=12,
            ),
        ),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [empty_buyers])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "BUYER" in str(error)

    wrong_buyer_set = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
        buyers_sorted=(_visit_key("someone_else"),),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [wrong_buyer_set])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    extra_seller_passage = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
        extra_passages=(
            _passage(
                "seller_a",
                role=OrderControlTvtMpLocalBindingTradeRole.SELLER,
                baseline_passage_timestep=10,
                candidate_passage_timestep=12,
                rank=2,
            ),
        ),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [extra_seller_passage])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    nonparticipating_role = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
        extra_passages=(
            _passage(
                "buyer_a",
                role=OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
                baseline_passage_timestep=12,
                candidate_passage_timestep=10,
                visit_id=2,
            ),
        ),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [nonparticipating_role])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_node_name_visit_key_and_stop_reason_mismatches_are_runtime_error():
    world = _standard_buyer_seller_world()
    wrong_node = _candidate_local_result(node_name="other")
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [wrong_node])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    mismatched_name = _passage(
        "buyer_a",
        role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
        baseline_passage_timestep=12,
        candidate_passage_timestep=10,
    )
    mismatched_name = dataclasses.replace(mismatched_name, vehicle_name="other")
    bad_name = _candidate_local_result(
        seller_names=(),
        force_passages=(mismatched_name,),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [bad_name])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    bad_stop = _candidate_local_result(
        stop_reason=OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED,
        resolved=True,
        seller_names=(),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [bad_stop])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    unresolved_with_resolved_reason = _candidate_local_result(
        stop_reason=OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED,
        resolved=False,
        seller_names=(),
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result(
                [_node_local_result("merge", [unresolved_with_resolved_reason])]
            ),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    other_buyer_set = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=(_visit_key("buyer_a"),),
    )
    identity_mismatch = _candidate_local_result(
        seller_names=(),
        sequence_buyer_set=other_buyer_set,
    )
    try:
        evaluate_tvt_mp_candidate_economics(
            _set_result([_node_local_result("merge", [identity_mismatch])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_one_inconsistency_stops_later_candidates_and_later_nodes_without_partial_result():
    world = _world_with_vehicles(
        [
            {"name": "buyer_a", "vot_declared": 1.0},
            {"name": "buyer_later", "vot_declared": None},
            {"name": "buyer_node2", "vot_declared": None},
        ]
    )
    bad_first = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
        force_passages=(
            _passage(
                "buyer_a",
                role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                baseline_passage_timestep=None,
                candidate_passage_timestep=10,
            ),
        ),
    )
    later_candidate = _candidate_local_result(
        buyer_names=("buyer_later",),
        seller_names=(),
        buyer_passages={"buyer_later": {"baseline": 12, "candidate": 10}},
    )
    later_node = _candidate_local_result(
        node_name="side",
        buyer_names=("buyer_node2",),
        seller_names=(),
        buyer_passages={"buyer_node2": {"baseline": 12, "candidate": 10}},
    )
    local_set = _set_result(
        [
            _node_local_result("merge", [bad_first, later_candidate]),
            _node_local_result("side", [later_node]),
        ]
    )
    try:
        evaluate_tvt_mp_candidate_economics(local_set, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    except ValueError as error:
        raise AssertionError(
            "later candidate or later Node was processed; got ValueError: "
            f"{error}"
        )


# ---------------------------------------------------------------------------
# Immutability and out-of-scope work
# ---------------------------------------------------------------------------


def test_world_local_results_and_vehicle_attributes_are_unchanged():
    world = _standard_buyer_seller_world()
    candidate = _standard_feasible_candidate()
    local_set = _set_result([_node_local_result("merge", [candidate])])
    before = _world_fingerprint(world)
    fifo_before = local_set.fifo_inspection_set_result
    result = _evaluate(local_set, world)
    assert _world_fingerprint(world) == before
    assert local_set.fifo_inspection_set_result is fifo_before
    assert result.local_virtual_calculation_set_result is local_set
    assert candidate.required_passage_records[0].baseline_passage_timestep == 12
    assert world.VEHICLES["buyer_a"].participates_in_order_exchange is True
    assert world.VEHICLES["buyer_a"].vot_declared == 2.0


def test_does_not_select_candidates_or_write_payments():
    world = _standard_buyer_seller_world()
    low = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a",),
        buyer_passages={"buyer_a": {"baseline": 11, "candidate": 10}},
        seller_passages={"seller_a": {"baseline": 10, "candidate": 10}},
    )
    high = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=("seller_a",),
        buyer_passages={"buyer_a": {"baseline": 20, "candidate": 10}},
        seller_passages={"seller_a": {"baseline": 10, "candidate": 10}},
    )
    result = _evaluate(
        _set_result([_node_local_result("merge", [low, high])]),
        world,
    )
    evaluated = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results
    assert len(evaluated) == 2
    assert evaluated[0].surplus == 2.0
    assert evaluated[1].surplus == 20.0
    for candidate_result in evaluated:
        names = _field_names(type(candidate_result))
        assert "selected" not in names
        assert "payment" not in names
        assert "compensation" not in names
        assert "actual_passage_timestep" not in names
    assert world.VEHICLES["buyer_a"].payment_paid == 0
    assert world.VEHICLES["seller_a"].payment_received == 0
    assert world.VEHICLES["buyer_a"].order_exchange_log == []


def test_production_source_keeps_required_shape_and_forbids_out_of_scope_work():
    source_text = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    called_names = set()
    imported_modules = set()
    function_names = []
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
            function_names.append(node.name)
            if not node.name.startswith("_"):
                public_function_names.append(node.name)
    forbidden_calls = {
        "exec_simulation",
        "run_snapshot_fixed_baseline_fork",
        "build_tvt_mp_fifo_inspection_results",
        "build_tvt_mp_general_trade_ranks",
        "build_tvt_mp_concrete_buyer_candidate_sets",
        "run_tvt_mp_candidate_local_virtual_calculation",
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
        "ThreadPoolExecutor",
        "Pool",
    }
    assert called_names.isdisjoint(forbidden_calls)
    assert "random" not in imported_modules
    assert public_function_names == ["evaluate_tvt_mp_candidate_economics"]
    assert "dataclass(frozen=True)" in source_text
    assert "for node_local_result in node_local_results:" in source_text
    assert "for candidate_local_result in candidate_local_results:" in source_text
    assert "for buyer_passage_record in buyer_passage_records:" in source_text
    assert "for seller_passage_record in seller_passage_records:" in source_text
    assert "P_b" not in source_text
    assert "payment_paid" not in source_text
    assert "payment_received" not in source_text
    assert "actual_passage" not in source_text
    assert "selected_candidate" not in source_text
    assert "Decimal" not in source_text
    assert "vot_true" in source_text
    assert "does not compute payment" in source_text.lower() or "not the buyer's payment" in source_text
    assert "VOT=0 is legal" in source_text
    assert "if declared_vot == 0" not in source_text
    assert "if declared_vot_per_second == 0" not in source_text
    assert "partial" not in source_text.lower() or "does not" in source_text
    assert "economically_feasible" in source_text
    assert "BUYER_NONPOSITIVE_VALUE" in source_text
    assert "total_buyer_value_G < total_required_compensation_R" in source_text


def test_feasible_result_uses_declared_vot_not_true_vot():
    world = _world_with_vehicles(
        [
            {
                "name": "buyer_a",
                "vot_declared": 2.0,
                "vot_true": 99.0,
            }
        ]
    )
    candidate = _candidate_local_result(
        buyer_names=("buyer_a",),
        seller_names=(),
        buyer_passages={"buyer_a": {"baseline": 12, "candidate": 10}},
    )
    result = _evaluate(_set_result([_node_local_result("merge", [candidate])]), world)
    buyer = result.node_economic_evaluation_results[0].candidate_economic_evaluation_results[0].buyer_economic_records[0]
    assert buyer.declared_vot_per_second == 2.0
    assert buyer.gross_time_value_G_b == 4.0
    assert not hasattr(buyer, "true_vot")
    assert world.VEHICLES["buyer_a"].vot_true == 99.0


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
