# Tests for TVT-MP economically feasible candidate selection.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_candidate_selection.py

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
    OrderControlTvtMpCandidatePassageRecord,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionSetResult,
    OrderControlTvtMpCandidateSelectionStatus,
    OrderControlTvtNodeMpCandidateSelectionResult,
    _build_node_candidate_selection_result,
    _require_rng_index_in_range,
    select_tvt_mp_candidates,
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
from uxsim.uxsim import World


PRODUCTION_PATH = Path("uxsim/order_control_tvt_mp_candidate_selection.py")
BASELINE_T = 10
FIFO_SENTINEL = object()

_FORBIDDEN_RESULT_FIELD_NAMES = {
    "payment",
    "compensation",
    "selected",
    "selected_flag",
    "candidate_id",
    "seed",
    "rng",
    "random_index",
    "final_rank",
    "actual",
    "actual_passage",
    "actual_result",
    "feasible_candidate_count",
    "maximum_surplus",
    "maximum_surplus_candidate_count",
    "maximum_buyer_count",
    "final_tied_candidate_count",
}


# ---------------------------------------------------------------------------
# Small explicit fixtures
# ---------------------------------------------------------------------------


def _visit_key(vehicle_name: str, visit_id: int = 1):
    return (vehicle_name, visit_id)


def _new_world(*, name: str = "tvt_mp_selection", random_seed=0):
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


def _add_vehicle(world, name: str, *, vot_declared=1.0):
    world.addVehicle(
        "orig",
        "dest",
        0,
        name=name,
        vot_declared=vot_declared,
        vot_true=vot_declared,
        participates_in_order_exchange=True,
    )
    return world.VEHICLES[name]


def _world_with_vehicles(vehicle_names, *, random_seed=0, timestep_T=BASELINE_T):
    world = _new_world(random_seed=random_seed)
    for name in vehicle_names:
        _add_vehicle(world, name)
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    world.T = timestep_T
    return world


def _standard_world(*, random_seed=0, timestep_T=BASELINE_T):
    return _world_with_vehicles(
        ["buyer_a", "buyer_b", "buyer_c", "seller_a", "seller_b"],
        random_seed=random_seed,
        timestep_T=timestep_T,
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


def _buyer_record(vehicle_name: str, *, visit_id: int = 1, G_b: float = 4.0):
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


def _seller_record(vehicle_name: str, *, R_s: float = 1.0):
    return OrderControlTvtMpSellerEconomicRecord(
        visit_key=_visit_key(vehicle_name),
        vehicle_name=vehicle_name,
        declared_vot_per_second=1.0,
        baseline_passage_timestep=10,
        candidate_passage_timestep=12,
        raw_passage_difference_timesteps=2,
        expected_waiting_increase_timesteps=2,
        raw_passage_difference_seconds=2.0,
        expected_waiting_increase_seconds=2.0,
        required_compensation_R_s=R_s,
    )


def _candidate_economic_result(
    *,
    node_name: str = "merge",
    buyer_keys=None,
    seller_names=(),
    surplus=3.0,
    total_buyer_value_G=None,
    total_required_compensation_R=1.0,
    economically_feasible=True,
    infeasibility_reasons=(),
    buyer_G_b_values=None,
    extra_seller_records=(),
    local_result=None,
):
    if buyer_keys is None:
        buyer_keys = (_visit_key("buyer_a"),)
    if local_result is None:
        local_result = _candidate_local_result(
            node_name=node_name,
            buyer_keys=buyer_keys,
            seller_names=seller_names,
        )
    if buyer_G_b_values is None:
        remaining = surplus + total_required_compensation_R
        buyer_G_b_values = []
        remaining_buyers = len(buyer_keys)
        for _buyer_key in buyer_keys:
            remaining_buyers = remaining_buyers - 1
            if remaining_buyers == 0:
                buyer_G_b_values.append(remaining)
            else:
                buyer_G_b_values.append(1.0)
                remaining = remaining - 1.0
    buyer_records = []
    buyer_index = 0
    for visit_key in buyer_keys:
        buyer_records.append(
            _buyer_record(
                visit_key[0],
                visit_id=visit_key[1],
                G_b=buyer_G_b_values[buyer_index],
            )
        )
        buyer_index = buyer_index + 1
    seller_records = []
    for name in seller_names:
        seller_records.append(_seller_record(name, R_s=1.0))
    for extra_seller in extra_seller_records:
        seller_records.append(extra_seller)
    if total_buyer_value_G is None:
        total_buyer_value_G = 0.0
        for buyer_record in buyer_records:
            total_buyer_value_G = total_buyer_value_G + buyer_record.gross_time_value_G_b
    if economically_feasible is True and infeasibility_reasons == ():
        reasons = ()
    else:
        reasons = infeasibility_reasons
    return OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=local_result,
        buyer_economic_records=tuple(buyer_records),
        seller_economic_records=tuple(seller_records),
        total_buyer_value_G=total_buyer_value_G,
        total_required_compensation_R=total_required_compensation_R,
        surplus=surplus,
        economically_feasible=economically_feasible,
        infeasibility_reasons=reasons,
    )


def _infeasible_candidate(*, node_name: str = "merge", buyer_name: str = "buyer_a"):
    return _candidate_economic_result(
        node_name=node_name,
        buyer_keys=(_visit_key(buyer_name),),
        surplus=-1.0,
        total_buyer_value_G=0.0,
        total_required_compensation_R=1.0,
        economically_feasible=False,
        infeasibility_reasons=(
            OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
            OrderControlTvtMpCandidateEconomicInfeasibilityReason.TOTAL_BUYER_VALUE_BELOW_REQUIRED_COMPENSATION,
        ),
        buyer_G_b_values=[0.0],
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


def _select(economic_set_result, world):
    return select_tvt_mp_candidates(economic_set_result, world)


def _selected_identity(node_result):
    selected = node_result.selected_candidate_economic_result
    buyers_sorted = (
        selected.candidate_local_virtual_calculation_result.concrete_buyer_candidate_set.buyers_sorted
    )
    return (node_result.node_name, buyers_sorted)


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


def _replace_candidate(candidate, **changes):
    return dataclasses.replace(candidate, **changes)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


def test_selection_status_enum_members_and_values():
    status = OrderControlTvtMpCandidateSelectionStatus
    assert status.SELECTED.value == "selected"
    assert (
        status.NO_ECONOMICALLY_FEASIBLE_CANDIDATE.value
        == "no_economically_feasible_candidate"
    )
    names = []
    values = []
    for member in status:
        names.append(member.name)
        values.append(member.value)
    assert names == ["SELECTED", "NO_ECONOMICALLY_FEASIBLE_CANDIDATE"]
    assert values == ["selected", "no_economically_feasible_candidate"]


def test_node_and_set_results_are_frozen():
    for cls in (
        OrderControlTvtNodeMpCandidateSelectionResult,
        OrderControlTvtMpCandidateSelectionSetResult,
    ):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True


def test_public_result_field_order_and_forbidden_fields():
    assert _field_names(OrderControlTvtNodeMpCandidateSelectionResult) == [
        "node_name",
        "selection_status",
        "selected_candidate_economic_result",
        "rng_was_used",
    ]
    assert _field_names(OrderControlTvtMpCandidateSelectionSetResult) == [
        "economic_evaluation_set_result",
        "node_candidate_selection_results",
    ]
    for cls in (
        OrderControlTvtNodeMpCandidateSelectionResult,
        OrderControlTvtMpCandidateSelectionSetResult,
    ):
        names = set(_field_names(cls))
        assert names.isdisjoint(_FORBIDDEN_RESULT_FIELD_NAMES)
        for name in names:
            assert "count" not in name
            assert "payment" not in name
            assert "compensation" not in name
            assert "rank" not in name
            assert "actual" not in name
            assert "seed" not in name


def test_public_columns_are_tuples_and_keep_input_objects():
    world = _standard_world()
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    result = _select(economic_set, world)
    assert result.economic_evaluation_set_result is economic_set
    assert isinstance(result.node_candidate_selection_results, tuple)
    node_result = result.node_candidate_selection_results[0]
    assert type(node_result.rng_was_used) is bool
    assert node_result.selected_candidate_economic_result is candidate
    assert (
        economic_set.node_economic_evaluation_results[0]
        .candidate_economic_evaluation_results[0]
        is candidate
    )


def test_result_does_not_keep_live_world_vehicle_node_link_rng_or_seed():
    world = _standard_world()
    candidate = _candidate_economic_result()
    result = _select(_economic_set([("merge", [candidate])]), world)
    dumped = str(result)
    assert "World(" not in dumped
    node_result = result.node_candidate_selection_results[0]
    for field in dataclasses.fields(node_result):
        value = getattr(node_result, field.name)
        assert not isinstance(value, World)
    assert not hasattr(result, "seed")
    assert not hasattr(node_result, "seed")
    assert not hasattr(result, "rng")
    assert not hasattr(node_result, "rng")
    assert "Generator" not in dumped
    assert "SeedSequence" not in dumped
    assert not hasattr(result, "selected_count")
    assert not hasattr(node_result, "feasible_candidate_count")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def test_public_api_is_one_positional_function_without_extra_helpers():
    import uxsim.order_control_tvt_mp_candidate_selection as module

    signature = inspect.signature(select_tvt_mp_candidates)
    parameter_names = list(signature.parameters)
    assert parameter_names == [
        "economic_evaluation_set_result",
        "real_W",
    ]
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert parameter.default is inspect.Parameter.empty
    assert not hasattr(module, "select_tvt_mp_node_candidates")
    assert not hasattr(module, "select_tvt_mp_one_candidate")
    assert not hasattr(module, "initialize_tvt_mp_candidate_selection")
    assert "external_rng" not in parameter_names
    assert "random_seed" not in parameter_names
    assert "tolerance" not in parameter_names
    assert "payment_rule" not in parameter_names
    assert "compensation_rule" not in parameter_names
    source = inspect.getsource(select_tvt_mp_candidates)
    assert "payment_rule" not in source
    assert "compensation_rule" not in source


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_rejects_non_world_and_non_economic_set_result():
    world = _standard_world()
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    try:
        select_tvt_mp_candidates(economic_set, "not-a-world")
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "World" in str(error)
    try:
        select_tvt_mp_candidates("not-a-set", world)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "EconomicEvaluationSetResult" in str(error)


def test_rejects_invalid_random_seed_and_world_t():
    world = _standard_world()
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    original_seed = world.random_seed
    original_t = world.T
    invalid_seeds = (True, False, "0", 1.5, -1)
    for invalid in invalid_seeds:
        world.random_seed = invalid
        try:
            select_tvt_mp_candidates(economic_set, world)
            raise AssertionError(f"expected ValueError for random_seed={invalid!r}")
        except ValueError:
            pass
    world.random_seed = original_seed
    invalid_t_values = (True, False, None, "10", 1.5, -1)
    for invalid in invalid_t_values:
        world.T = invalid
        try:
            select_tvt_mp_candidates(economic_set, world)
            raise AssertionError(f"expected ValueError for T={invalid!r}")
        except ValueError:
            pass
    world.T = original_t
    world.random_seed = None
    result = select_tvt_mp_candidates(economic_set, world)
    assert (
        result.node_candidate_selection_results[0].selection_status
        is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    )
    world.random_seed = original_seed


def test_rejects_invalid_node_and_candidate_result_types():
    world = _standard_world()
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    bad_nodes = dataclasses.replace(
        economic_set,
        node_economic_evaluation_results=["not-a-node"],
    )
    try:
        select_tvt_mp_candidates(bad_nodes, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    bad_node_tuple = dataclasses.replace(
        economic_set,
        node_economic_evaluation_results=[
            economic_set.node_economic_evaluation_results[0]
        ],
    )
    try:
        select_tvt_mp_candidates(bad_node_tuple, world)
        raise AssertionError("expected RuntimeError for Node list")
    except RuntimeError:
        pass
    bad_candidates = _node_economic_result("merge", [])
    bad_candidates = dataclasses.replace(
        economic_set.node_economic_evaluation_results[0],
        candidate_economic_evaluation_results=["not-a-candidate"],
    )
    bad_set = _economic_set([("merge", [candidate])])
    bad_set = dataclasses.replace(
        bad_set,
        node_economic_evaluation_results=(bad_candidates,),
        local_virtual_calculation_set_result=dataclasses.replace(
            bad_set.local_virtual_calculation_set_result,
            node_local_virtual_calculation_results=(
                _node_local_result("merge", [candidate]),
            ),
        ),
    )
    try:
        select_tvt_mp_candidates(bad_set, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_rejects_node_name_mismatch():
    world = _standard_world()
    candidate = _candidate_economic_result(node_name="merge")
    economic_set = _economic_set([("merge", [candidate])])
    mismatched_local = dataclasses.replace(
        economic_set.local_virtual_calculation_set_result.node_local_virtual_calculation_results[0],
        node_name="other",
    )
    mismatched = dataclasses.replace(
        economic_set,
        local_virtual_calculation_set_result=dataclasses.replace(
            economic_set.local_virtual_calculation_set_result,
            node_local_virtual_calculation_results=(mismatched_local,),
        ),
    )
    try:
        select_tvt_mp_candidates(mismatched, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "does not match" in str(error)


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def test_no_feasible_candidate_is_normal_empty_status():
    world = _standard_world()
    empty_set = _economic_set([("merge", [])])
    empty_result = _select(empty_set, world)
    empty_node = empty_result.node_candidate_selection_results[0]
    assert (
        empty_node.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    )
    assert empty_node.selected_candidate_economic_result is None
    assert empty_node.rng_was_used is False

    infeasible = _infeasible_candidate()
    infeasible_result = _select(_economic_set([("merge", [infeasible])]), world)
    infeasible_node = infeasible_result.node_candidate_selection_results[0]
    assert (
        infeasible_node.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    )
    assert infeasible_node.selected_candidate_economic_result is None
    assert infeasible_node.rng_was_used is False

    no_node_set = _economic_set([])
    no_node_result = _select(no_node_set, world)
    assert no_node_result.node_candidate_selection_results == ()
    assert no_node_result.economic_evaluation_set_result is no_node_set


def test_one_feasible_candidate_is_selected_without_rng():
    world = _standard_world()
    candidate = _candidate_economic_result(surplus=3.0)
    infeasible = _infeasible_candidate(buyer_name="buyer_b")
    result = _select(_economic_set([("merge", [infeasible, candidate])]), world)
    node_result = result.node_candidate_selection_results[0]
    assert (
        node_result.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    )
    assert node_result.selected_candidate_economic_result is candidate
    assert node_result.rng_was_used is False


def test_multiple_feasible_selects_maximum_surplus():
    world = _standard_world()
    low = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=2.0,
        total_required_compensation_R=1.0,
    )
    high = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=5.0,
        total_required_compensation_R=1.0,
    )
    mid = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_c"),),
        surplus=4.0,
        total_required_compensation_R=1.0,
    )
    result = _select(_economic_set([("merge", [low, high, mid])]), world)
    node_result = result.node_candidate_selection_results[0]
    assert node_result.selected_candidate_economic_result is high
    assert node_result.rng_was_used is False


def test_near_but_unequal_surplus_is_not_a_tie():
    world = _standard_world()
    almost = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=1.0,
        total_required_compensation_R=1.0,
    )
    slightly_higher = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=1.0 + 1e-12,
        total_required_compensation_R=1.0,
    )
    assert almost.surplus != slightly_higher.surplus
    result = _select(
        _economic_set([("merge", [almost, slightly_higher])]),
        world,
    )
    node_result = result.node_candidate_selection_results[0]
    assert node_result.selected_candidate_economic_result is slightly_higher
    assert node_result.rng_was_used is False


def test_surplus_zero_and_g_equals_r_is_feasible_and_selectable():
    world = _standard_world()
    zero_surplus = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=0.0,
        total_buyer_value_G=2.0,
        total_required_compensation_R=2.0,
        buyer_G_b_values=[2.0],
    )
    negative = _infeasible_candidate(buyer_name="buyer_b")
    result = _select(_economic_set([("merge", [negative, zero_surplus])]), world)
    node_result = result.node_candidate_selection_results[0]
    assert node_result.selected_candidate_economic_result is zero_surplus
    assert node_result.selected_candidate_economic_result.surplus == 0.0
    assert node_result.rng_was_used is False


def test_buyer_count_is_the_second_criterion():
    world = _standard_world()
    one_buyer = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
        total_required_compensation_R=1.0,
        seller_names=("seller_a", "seller_b"),
    )
    two_buyers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"), _visit_key("buyer_c")),
        surplus=4.0,
        total_required_compensation_R=1.0,
        seller_names=(),
    )
    result = _select(_economic_set([("merge", [one_buyer, two_buyers])]), world)
    node_result = result.node_candidate_selection_results[0]
    assert node_result.selected_candidate_economic_result is two_buyers
    assert node_result.rng_was_used is False
    assert len(two_buyers.buyer_economic_records) == 2
    assert len(one_buyer.buyer_economic_records) == 1


def test_seller_count_party_total_and_trade_scope_are_not_used():
    world = _standard_world()
    few_sellers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=3.0,
        total_required_compensation_R=1.0,
        seller_names=(),
    )
    many_sellers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=5.0,
        total_required_compensation_R=1.0,
        seller_names=("seller_a", "seller_b"),
    )
    result = _select(
        _economic_set([("merge", [few_sellers, many_sellers])]),
        world,
    )
    node_result = result.node_candidate_selection_results[0]
    assert node_result.selected_candidate_economic_result is many_sellers
    tied_few_sellers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
        total_required_compensation_R=1.0,
        seller_names=(),
    )
    tied_many_sellers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
        total_required_compensation_R=1.0,
        seller_names=("seller_a", "seller_b"),
    )
    tied_result = _select(
        _economic_set([("merge", [tied_few_sellers, tied_many_sellers])]),
        world,
    )
    tied_node = tied_result.node_candidate_selection_results[0]
    assert tied_node.rng_was_used is True
    selected = tied_node.selected_candidate_economic_result
    assert selected is tied_few_sellers or selected is tied_many_sellers
    assert len(tied_few_sellers.buyer_economic_records) == 1
    assert len(tied_many_sellers.buyer_economic_records) == 1
    few_party_total = len(tied_few_sellers.buyer_economic_records) + len(
        tied_few_sellers.seller_economic_records
    )
    many_party_total = len(tied_many_sellers.buyer_economic_records) + len(
        tied_many_sellers.seller_economic_records
    )
    assert many_party_total > few_party_total
    few_scope = len(
        tied_few_sellers.candidate_local_virtual_calculation_result.binding_rank_sequence.trade_scope_of_this_candidate_visits
    )
    many_scope = len(
        tied_many_sellers.candidate_local_virtual_calculation_result.binding_rank_sequence.trade_scope_of_this_candidate_visits
    )
    assert many_scope > few_scope


# ---------------------------------------------------------------------------
# RNG use and non-use
# ---------------------------------------------------------------------------


def test_rng_not_used_when_feasible_zero_one_or_unique_max():
    world = _standard_world()
    cases = []
    cases.append(_economic_set([("merge", [])]))
    cases.append(_economic_set([("merge", [_infeasible_candidate()])]))
    cases.append(
        _economic_set([("merge", [_candidate_economic_result(surplus=3.0)])])
    )
    high = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=9.0,
    )
    low = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=1.0,
    )
    cases.append(_economic_set([("merge", [high, low])]))
    more_buyers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"), _visit_key("buyer_b")),
        surplus=4.0,
    )
    fewer_buyers = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_c"),),
        surplus=4.0,
    )
    cases.append(_economic_set([("merge", [fewer_buyers, more_buyers])]))
    for economic_set in cases:
        result = _select(economic_set, world)
        node_result = result.node_candidate_selection_results[0]
        assert node_result.rng_was_used is False


def test_rng_used_for_two_or_more_final_ties_and_selects_only_tied_candidate():
    world = _standard_world()
    first = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    second = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
    )
    two_result = _select(_economic_set([("merge", [first, second])]), world)
    two_node = two_result.node_candidate_selection_results[0]
    assert two_node.rng_was_used is True
    assert two_node.selection_status is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    assert two_node.selected_candidate_economic_result in (first, second)

    third = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_c"),),
        surplus=4.0,
    )
    lower = _candidate_economic_result(
        buyer_keys=(_visit_key("seller_a"),),
        surplus=1.0,
    )
    three_result = _select(
        _economic_set([("merge", [lower, third, first, second])]),
        world,
    )
    three_node = three_result.node_candidate_selection_results[0]
    assert three_node.rng_was_used is True
    assert three_node.selected_candidate_economic_result in (first, second, third)
    assert three_node.selected_candidate_economic_result is not lower


# ---------------------------------------------------------------------------
# Reproducibility and order independence
# ---------------------------------------------------------------------------


def test_same_seed_t_node_and_set_selects_same_identity():
    first = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    second = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
    )
    economic_set = _economic_set([("merge", [first, second])])
    world = _standard_world(random_seed=7, timestep_T=10)
    first_result = _select(economic_set, world)
    second_result = _select(economic_set, world)
    first_identity = _selected_identity(first_result.node_candidate_selection_results[0])
    second_identity = _selected_identity(
        second_result.node_candidate_selection_results[0]
    )
    assert first_identity == second_identity
    world_again = _standard_world(random_seed=7, timestep_T=10)
    again_result = _select(economic_set, world_again)
    assert (
        _selected_identity(again_result.node_candidate_selection_results[0])
        == first_identity
    )


def test_candidate_order_and_node_order_do_not_change_selected_identity():
    merge_a = _candidate_economic_result(
        node_name="merge",
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    merge_b = _candidate_economic_result(
        node_name="merge",
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
    )
    dest_a = _candidate_economic_result(
        node_name="dest",
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    dest_b = _candidate_economic_result(
        node_name="dest",
        buyer_keys=(_visit_key("buyer_c"),),
        surplus=4.0,
    )
    world = _standard_world(random_seed=11, timestep_T=10)
    first_set = _economic_set(
        [
            ("merge", [merge_a, merge_b]),
            ("dest", [dest_a, dest_b]),
        ]
    )
    reversed_candidates = _economic_set(
        [
            ("merge", [merge_b, merge_a]),
            ("dest", [dest_b, dest_a]),
        ]
    )
    reversed_nodes = _economic_set(
        [
            ("dest", [dest_a, dest_b]),
            ("merge", [merge_a, merge_b]),
        ]
    )
    first_result = _select(first_set, world)
    reversed_candidate_result = _select(reversed_candidates, world)
    reversed_node_result = _select(reversed_nodes, world)

    def identities_by_node(result):
        mapping = {}
        for node_result in result.node_candidate_selection_results:
            mapping[node_result.node_name] = _selected_identity(node_result)
        return mapping

    first_identities = identities_by_node(first_result)
    assert identities_by_node(reversed_candidate_result) == first_identities
    assert identities_by_node(reversed_node_result) == first_identities
    assert first_identities["merge"][0] == "merge"
    assert first_identities["dest"][0] == "dest"


def test_different_seeds_can_select_different_tied_identities():
    first = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    second = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
    )
    economic_set = _economic_set([("merge", [first, second])])
    seen_identities = []
    for seed in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15):
        world = _standard_world(random_seed=seed, timestep_T=10)
        result = _select(economic_set, world)
        identity = _selected_identity(result.node_candidate_selection_results[0])
        already_seen = False
        for seen in seen_identities:
            if seen == identity:
                already_seen = True
                break
        if already_seen is False:
            seen_identities.append(identity)
    assert len(seen_identities) >= 2


def test_production_does_not_use_hash_or_object_id():
    source_text = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    assert "hash" not in called_names
    assert "id" not in called_names
    assert "prefix" not in source_text or "prefix index" not in source_text.lower()


# ---------------------------------------------------------------------------
# RNG invariance
# ---------------------------------------------------------------------------


def test_world_rng_states_seed_t_and_traffic_are_unchanged():
    world = _standard_world(random_seed=3, timestep_T=10)
    first = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    second = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
    )
    economic_set = _economic_set([("merge", [first, second])])
    before = _world_fingerprint(world)
    result = _select(economic_set, world)
    assert result.node_candidate_selection_results[0].rng_was_used is True
    assert _world_fingerprint(world) == before
    assert world.random_seed == 3
    assert world.T == 10


# ---------------------------------------------------------------------------
# candidate identity
# ---------------------------------------------------------------------------


def test_identity_uses_node_name_and_buyers_sorted_and_distinguishes_revisit():
    world = _standard_world(random_seed=4, timestep_T=10)
    first_visit = _candidate_economic_result(
        node_name="merge",
        buyer_keys=(_visit_key("buyer_a", 1),),
        surplus=4.0,
    )
    second_visit = _candidate_economic_result(
        node_name="merge",
        buyer_keys=(_visit_key("buyer_a", 2),),
        surplus=4.0,
    )
    result = _select(_economic_set([("merge", [first_visit, second_visit])]), world)
    selected = result.node_candidate_selection_results[0].selected_candidate_economic_result
    selected_buyers = (
        selected.candidate_local_virtual_calculation_result.concrete_buyer_candidate_set.buyers_sorted
    )
    assert selected_buyers in (
        (_visit_key("buyer_a", 1),),
        (_visit_key("buyer_a", 2),),
    )
    assert selected is first_visit or selected is second_visit


def test_duplicate_identity_is_runtime_error():
    world = _standard_world()
    first = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    second = _candidate_economic_result(
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=5.0,
    )
    try:
        select_tvt_mp_candidates(
            _economic_set([("merge", [first, second])]),
            world,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "duplicated" in str(error)


def test_same_buyers_sorted_on_different_nodes_are_different_identities():
    world = _standard_world(random_seed=5, timestep_T=10)
    merge_candidate = _candidate_economic_result(
        node_name="merge",
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    dest_candidate = _candidate_economic_result(
        node_name="dest",
        buyer_keys=(_visit_key("buyer_a"),),
        surplus=4.0,
    )
    result = _select(
        _economic_set(
            [
                ("merge", [merge_candidate]),
                ("dest", [dest_candidate]),
            ]
        ),
        world,
    )
    merge_node = result.node_candidate_selection_results[0]
    dest_node = result.node_candidate_selection_results[1]
    assert merge_node.selected_candidate_economic_result is merge_candidate
    assert dest_node.selected_candidate_economic_result is dest_candidate
    merge_identity = _selected_identity(merge_node)
    dest_identity = _selected_identity(dest_node)
    assert merge_identity != dest_identity
    assert merge_identity[1] == dest_identity[1]


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_selected_and_no_candidate_status_contracts():
    world = _standard_world()
    candidate = _candidate_economic_result()
    selected_result = _select(_economic_set([("merge", [candidate])]), world)
    selected_node = selected_result.node_candidate_selection_results[0]
    assert (
        selected_node.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    )
    assert selected_node.selected_candidate_economic_result is not None
    empty_result = _select(_economic_set([("merge", [])]), world)
    empty_node = empty_result.node_candidate_selection_results[0]
    assert (
        empty_node.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    )
    assert empty_node.selected_candidate_economic_result is None
    assert empty_node.rng_was_used is False


def test_status_contradiction_is_runtime_error():
    candidate = _candidate_economic_result()
    try:
        _build_node_candidate_selection_result(
            node_name="merge",
            selection_status=OrderControlTvtMpCandidateSelectionStatus.SELECTED,
            selected_candidate_economic_result=None,
            rng_was_used=False,
            input_candidate_results=(candidate,),
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    try:
        _build_node_candidate_selection_result(
            node_name="merge",
            selection_status=(
                OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
            ),
            selected_candidate_economic_result=candidate,
            rng_was_used=False,
            input_candidate_results=(candidate,),
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    try:
        _build_node_candidate_selection_result(
            node_name="merge",
            selection_status=(
                OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
            ),
            selected_candidate_economic_result=None,
            rng_was_used=True,
            input_candidate_results=(candidate,),
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    try:
        _require_rng_index_in_range(-1, 2, node_name="merge")
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    try:
        _require_rng_index_in_range(2, 2, node_name="merge")
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# Serious inconsistency
# ---------------------------------------------------------------------------


def test_feasible_flag_reason_and_value_inconsistencies_are_runtime_error():
    world = _standard_world()
    cases = []
    cases.append(
        _replace_candidate(
            _candidate_economic_result(),
            economically_feasible=True,
            infeasibility_reasons=(
                OrderControlTvtMpCandidateEconomicInfeasibilityReason.BUYER_NONPOSITIVE_VALUE,
            ),
        )
    )
    cases.append(
        _replace_candidate(
            _infeasible_candidate(),
            economically_feasible=False,
            infeasibility_reasons=(),
        )
    )
    cases.append(
        _replace_candidate(
            _candidate_economic_result(surplus=3.0, total_required_compensation_R=1.0),
            surplus=math.inf,
        )
    )
    cases.append(
        _replace_candidate(
            _candidate_economic_result(surplus=3.0, total_required_compensation_R=1.0),
            surplus=2.0,
        )
    )
    cases.append(
        _replace_candidate(
            _candidate_economic_result(),
            buyer_economic_records=(),
        )
    )
    negative_buyer = _candidate_economic_result(
        surplus=3.0,
        total_required_compensation_R=1.0,
        buyer_G_b_values=[-1.0],
        total_buyer_value_G=4.0,
    )
    cases.append(negative_buyer)
    low_g = _candidate_economic_result(
        surplus=-1.0,
        total_buyer_value_G=1.0,
        total_required_compensation_R=2.0,
        buyer_G_b_values=[1.0],
        economically_feasible=True,
        infeasibility_reasons=(),
    )
    cases.append(low_g)
    for candidate in cases:
        try:
            select_tvt_mp_candidates(_economic_set([("merge", [candidate])]), world)
            raise AssertionError(
                f"expected RuntimeError for candidate surplus={candidate.surplus!r}"
            )
        except RuntimeError:
            pass


def test_one_node_inconsistency_stops_later_nodes_without_partial_result():
    world = _standard_world()
    bad = _replace_candidate(
        _candidate_economic_result(node_name="merge", surplus=3.0),
        surplus=99.0,
    )
    later = _candidate_economic_result(
        node_name="dest",
        buyer_keys=(_visit_key("buyer_b"),),
        surplus=4.0,
    )
    economic_set = _economic_set(
        [
            ("merge", [bad]),
            ("dest", [later]),
        ]
    )
    try:
        select_tvt_mp_candidates(economic_set, world)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "merge" in str(error)
        assert "dest" not in str(error) or "surplus" in str(error)


# ---------------------------------------------------------------------------
# Invariance and out of scope
# ---------------------------------------------------------------------------


def test_economic_local_and_vehicle_state_are_unchanged():
    world = _standard_world()
    candidate = _candidate_economic_result()
    economic_set = _economic_set([("merge", [candidate])])
    before = _world_fingerprint(world)
    local_before = economic_set.local_virtual_calculation_set_result
    fifo_before = local_before.fifo_inspection_set_result
    result = _select(economic_set, world)
    assert _world_fingerprint(world) == before
    assert result.economic_evaluation_set_result is economic_set
    assert economic_set.local_virtual_calculation_set_result is local_before
    assert local_before.fifo_inspection_set_result is fifo_before
    assert candidate.surplus == 3.0
    assert not hasattr(candidate, "selected")
    assert world.VEHICLES["buyer_a"].payment_paid == 0
    assert world.VEHICLES["seller_a"].payment_received == 0
    assert world.VEHICLES["buyer_a"].order_exchange_log == []


def test_does_not_write_payment_compensation_or_selected_flag():
    world = _standard_world()
    candidate = _candidate_economic_result()
    result = _select(_economic_set([("merge", [candidate])]), world)
    node_result = result.node_candidate_selection_results[0]
    for obj in (result, node_result, candidate):
        names = []
        if dataclasses.is_dataclass(obj):
            names = _field_names(type(obj))
        else:
            names = list(vars(obj))
        assert "payment" not in names
        assert "compensation" not in names
        assert "final_rank" not in names
        assert "actual" not in names
        assert "selected_flag" not in names
    assert not hasattr(candidate, "selected")
    assert world.VEHICLES["buyer_a"].payment_paid == 0
    assert world.VEHICLES["seller_a"].payment_received == 0


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
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
        "run_tvt_mp_candidate_local_virtual_calculation",
        "build_tvt_mp_fifo_inspection_results",
        "build_tvt_mp_general_trade_ranks",
        "build_tvt_mp_concrete_buyer_candidate_sets",
        "run_snapshot_fixed_baseline_fork",
        "ThreadPoolExecutor",
        "Pool",
        "hash",
        "id",
        "deepcopy",
    }
    assert called_names.isdisjoint(forbidden_calls)
    assert public_function_names == ["select_tvt_mp_candidates"]
    assert "dataclass(frozen=True)" in source_text
    assert "for node_economic_result in node_economic_results:" in source_text
    assert "for candidate_economic_result in candidate_economic_results:" in source_text
    assert "SeedSequence" in source_text
    assert "default_rng" in source_text
    assert "P_b" not in source_text
    assert "payment_paid" not in source_text
    assert "payment_received" not in source_text
    assert "actual_passage" not in source_text
    assert "final_rank" not in source_text
    assert "bit_generator" not in source_text
    attribute_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            attribute_names.add(node.attr)
    assert "rng" not in attribute_names
    assert "order_control_rng" not in attribute_names
    assert "economically_feasible is True" in source_text
    assert "does not compute payment" in source_text.lower() or "does not" in source_text


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
