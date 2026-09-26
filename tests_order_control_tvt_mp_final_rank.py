"""
Tests for TVT-MP final rank construction.

Run from the repository root:
    python tests_order_control_tvt_mp_final_rank.py
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
    OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
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
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtMpSellerEconomicRecord,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpFifoInspectionSetResult,
    OrderControlTvtNodeMpFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankSetResult,
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalRankVisitRecord,
    OrderControlTvtMpFinalizationSource,
    OrderControlTvtNodeMpFinalRankResult,
    build_tvt_mp_final_ranks,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankSetResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
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
    OrderControlTvtNodeMpPaymentAndCompensationResult,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionStatus,
    OrderControlTvtNodeRightOfEntrySelectionResult,
)
from uxsim.uxsim import Vehicle, World


PRODUCTION_PATH = Path("uxsim/order_control_tvt_mp_final_rank.py")
COMPLETE = OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
NO_ENTRY = OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY
UNRESOLVED_ARRIVALS = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS
)
UNRESOLVED_RIGHT = (
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE
)
UNRESOLVED_PASSAGES = (
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES
)
SELECTED = OrderControlTvtMpCandidateSelectionStatus.SELECTED
NO_FEASIBLE = (
    OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
)
CALCULATED = OrderControlTvtMpPaymentAndCompensationStatus.CALCULATED
NO_SELECTED = OrderControlTvtMpPaymentAndCompensationStatus.NO_SELECTED_CANDIDATE
PARTITION_1 = OrderControlTvtMpLocalBindingPartition.CONFIRMED_BEFORE_THIS_BASELINE
PARTITION_2 = OrderControlTvtMpLocalBindingPartition.PRECONFIRMED_BY_THIS_BASELINE
PARTITION_3 = OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
PARTITION_4 = (
    OrderControlTvtMpLocalBindingPartition.OUTSIDE_TRADE_SCOPE_INSIDE_K_FIXED
)
ROUTE_ORIGIN = (
    OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
)

_FORBIDDEN_RESULT_FIELD_NAMES = {
    "vehicle_name",
    "vehicle_id",
    "payment_P_b",
    "compensation_amount",
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "surplus",
    "trade_role",
    "actual",
    "realized_utility",
}


class _RouteCollector:
    """Saved baseline routes only. Tests do not ask production to search."""

    def __init__(self, routes):
        self.routes = dict(routes)

    def get_baseline_visit_snapshot(self, vehicle_name, visit_id):
        key = (vehicle_name, visit_id)
        if key not in self.routes:
            return None
        return {"route_next_link_name": self.routes[key]}


def _visit(name, visit_id=1):
    return (name, visit_id)


def _binding_visit(
    name,
    *,
    visit_id=1,
    rank,
    partition,
    route,
    role=OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
):
    return OrderControlTvtMpLocalBindingRankVisit(
        visit_key=_visit(name, visit_id),
        vehicle_id=visit_id,
        binding_partition=partition,
        binding_rank=rank,
        route_next_link_name=route,
        route_origin=ROUTE_ORIGIN,
        inlink_name="in",
        baseline_arrival_timestep=11,
        arrival_tiebreaker=0,
        trade_role=role,
    )


def _final_node(node_name):
    return OrderControlTvtMpCandidateFinalNodeRecord(
        node_name=node_name,
        incoming_vehicle_names=(),
        flow_capacity_remain=1,
        last_order_control_inlink_name=None,
        last_order_control_entry_timestep=None,
        order_control_clearance_timesteps=0,
    )


def _local_result(node_name, binding_sequence):
    buyer_set = binding_sequence.concrete_buyer_candidate_set
    return OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name=node_name,
        concrete_buyer_candidate_set=buyer_set,
        binding_rank_sequence=binding_sequence,
        baseline_timestep_T=10,
        configured_horizon_steps=6,
        final_virtual_timestep=10,
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
        final_node_record=_final_node(node_name),
        final_boundary_records=(),
    )


def _buyer_record(name, visit_id=1):
    return OrderControlTvtMpBuyerEconomicRecord(
        visit_key=_visit(name, visit_id),
        vehicle_name=name,
        declared_vot_per_second=1.0,
        baseline_passage_timestep=12,
        candidate_passage_timestep=11,
        expected_time_saving_timesteps=1,
        expected_time_saving_seconds=1.0,
        gross_time_value_G_b=4.0,
        passes_positive_buyer_value_condition=True,
    )


def _seller_record(name):
    return OrderControlTvtMpSellerEconomicRecord(
        visit_key=_visit(name),
        vehicle_name=name,
        declared_vot_per_second=1.0,
        baseline_passage_timestep=11,
        candidate_passage_timestep=12,
        raw_passage_difference_timesteps=1,
        expected_waiting_increase_timesteps=1,
        raw_passage_difference_seconds=1.0,
        expected_waiting_increase_seconds=1.0,
        required_compensation_R_s=1.0,
    )


def _economic_candidate(node_name, binding_sequence, *, feasible=True):
    local_result = _local_result(node_name, binding_sequence)
    return OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=local_result,
        buyer_economic_records=(_buyer_record("buyer"),),
        seller_economic_records=(_seller_record("seller"),),
        total_buyer_value_G=4.0,
        total_required_compensation_R=1.0,
        surplus=3.0,
        economically_feasible=feasible,
        infeasibility_reasons=(),
    )


def _sequence(
    node_name,
    *,
    partition_1=(),
    partition_2=(),
    partition_3,
    partition_4=(),
    remaining,
):
    visits = tuple(partition_1) + tuple(partition_2) + tuple(partition_3) + tuple(
        partition_4
    )
    k_last_buyer = len(partition_3)
    k_decision_window = len(remaining)
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=(_visit("buyer"),),
        ),
        confirmed_before_this_baseline_visits=tuple(partition_1),
        preconfirmed_by_this_baseline_visits=tuple(partition_2),
        trade_scope_of_this_candidate_visits=tuple(partition_3),
        outside_trade_scope_inside_k_fixed_visits=tuple(partition_4),
        visits_in_binding_order=visits,
        k_last_buyer=k_last_buyer,
        k_decision_window=k_decision_window,
        k_fixed=max(k_last_buyer, k_decision_window),
    )


def _payment_set_from_nodes(node_specs, *, collector_routes=None, extra_routes=None):
    """Build one payment set. Each spec is a dict of saved upstream facts."""
    if collector_routes is None:
        collector_routes = {}
    if extra_routes is not None:
        for key, route in extra_routes.items():
            collector_routes[key] = route
    collector = _RouteCollector(collector_routes)

    payment_nodes = []
    selection_nodes = []
    economic_nodes = []
    local_nodes = []
    fifo_nodes = []
    trade_nodes = []
    concrete_nodes = []
    inlink_nodes = []
    candidate_nodes = []
    right_nodes = []
    leading_nodes = []
    arrived_nodes = []
    alignment_nodes = []
    target_names = []

    for spec in node_specs:
        node_name = spec["node_name"]
        decision = tuple(spec.get("decision", ()))
        leading = tuple(spec.get("leading", ()))
        remaining = tuple(spec.get("remaining", ()))
        if "decision" not in spec:
            decision = leading + remaining
        build_status = spec["build_status"]
        selected = spec.get("selected")
        economic_candidates = spec.get("economic_candidates")
        if economic_candidates is None:
            if selected is None:
                economic_candidates = ()
            else:
                economic_candidates = (selected,)
        local_candidates = []
        for candidate in economic_candidates:
            local_candidates.append(
                candidate.candidate_local_virtual_calculation_result
            )
        for extra_local in spec.get("extra_local_results", ()):
            local_candidates.append(extra_local)
        if spec.get("payment_status") is None:
            if selected is None:
                payment_status = NO_SELECTED
                selection_status = NO_FEASIBLE
            else:
                payment_status = CALCULATED
                selection_status = SELECTED
        else:
            payment_status = spec["payment_status"]
            selection_status = spec["selection_status"]
        buyer_records = tuple(spec.get("buyer_records", ()))
        seller_records = tuple(spec.get("seller_records", ()))
        payment_nodes.append(
            OrderControlTvtNodeMpPaymentAndCompensationResult(
                node_name=node_name,
                payment_and_compensation_status=payment_status,
                selected_candidate_economic_result=selected,
                buyer_payment_records=buyer_records,
                seller_compensation_records=seller_records,
            )
        )
        selection_nodes.append(
            OrderControlTvtNodeMpCandidateSelectionResult(
                node_name=node_name,
                selection_status=selection_status,
                selected_candidate_economic_result=selected,
                rng_was_used=False,
            )
        )
        economic_nodes.append(
            OrderControlTvtNodeMpEconomicEvaluationResult(
                node_name=node_name,
                candidate_economic_evaluation_results=tuple(economic_candidates),
            )
        )
        local_nodes.append(
            OrderControlTvtNodeMpLocalVirtualCalculationResult(
                node_name=node_name,
                build_status=build_status,
                candidate_local_virtual_calculation_results=tuple(local_candidates),
            )
        )
        fifo_nodes.append(
            OrderControlTvtNodeMpFifoInspectionResult(
                node_name=node_name,
                build_status=build_status,
                candidate_fifo_inspection_results=(),
            )
        )
        trade_nodes.append(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name=node_name,
                build_status=build_status,
                candidate_trade_rank_results=(),
            )
        )
        concrete_nodes.append(
            OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
                node_name=node_name,
                build_status=build_status,
                buyer_candidate_inlink_prefix_results=(),
                concrete_buyer_candidate_sets=(),
            )
        )
        inlink_nodes.append(
            OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
                node_name=node_name,
                build_status=build_status,
                inlink_candidate_physical_orders=(),
            )
        )
        candidate_nodes.append(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name=node_name,
                build_status=build_status,
                right_of_entry_visit_key=spec.get("right_of_entry_visit_key"),
                right_of_entry_baseline_passage_timestep=None,
                k_confirmed_before=len(leading),
                p_minus_one_eligible_visit_count_before_limit=spec.get(
                    "eligible_before_limit"
                ),
                candidate_visits=(),
            )
        )
        if len(remaining) == 0:
            right_status = OrderControlTvtRightOfEntrySelectionStatus.NO_RIGHT_OF_ENTRY
            right_key = None
        else:
            right_status = OrderControlTvtRightOfEntrySelectionStatus.SELECTED
            right_key = remaining[0]
        right_nodes.append(
            OrderControlTvtNodeRightOfEntrySelectionResult(
                node_name=node_name,
                selection_status=right_status,
                right_of_entry_visit_key=right_key,
                k_confirmed_before=len(leading),
            )
        )
        leading_nodes.append(
            OrderControlTvtNodeLeadingNonparticipatingConfirmationResult(
                node_name=node_name,
                decision_window_visit_keys=decision,
                confirmed_leading_nonparticipating_visit_keys=leading,
                remaining_decision_window_visit_keys=remaining,
                confirm_result=OrderControlTvtConfirmResult(
                    k_confirmed_before=0,
                    k_confirmed_after=len(leading),
                    newly_confirmed_count=len(leading),
                ),
            )
        )
        arrived_nodes.append(
            OrderControlTvtNodeArrivedUndeterminedConfirmationResult(
                node_name=node_name,
                confirmed_arrived_visit_keys=tuple(spec.get("arrived", ())),
                confirm_result=OrderControlTvtConfirmResult(0, 0, 0),
            )
        )
        alignment_nodes.append(
            OrderControlTvtSnapshotUndeterminedAlignmentResult(
                node_name=node_name,
                resolved_undetermined_visits=(),
                unresolved_undetermined_visits=(),
                unregistered_collector_visit_keys=(),
            )
        )
        target_names.append(node_name)

    fork_result = OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=tuple(target_names),
        baseline_timestep_T=10,
        configured_horizon_steps=30,
        fork_steps_executed=30,
        final_fork_timestep=40,
        registered_visit_count=len(collector.routes),
        inlink_physical_orders=(),
        downstream_boundary_result=None,
    )
    alignment = OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=tuple(alignment_nodes),
    )
    arrived = OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment,
        node_confirmation_results=tuple(arrived_nodes),
    )
    leading = OrderControlTvtLeadingNonparticipatingConfirmationResult(
        arrived_confirmation_result=arrived,
        node_confirmation_results=tuple(leading_nodes),
    )
    right = OrderControlTvtRightOfEntrySelectionResult(
        leading_confirmation_result=leading,
        node_selection_results=tuple(right_nodes),
    )
    candidate_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=right,
        max_tvt_candidate_visit_count=1,
        node_candidate_set_results=tuple(candidate_nodes),
    )
    inlink_set = OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=candidate_set,
        node_inlink_candidate_physical_order_results=tuple(inlink_nodes),
    )
    concrete_set = OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=inlink_set,
        node_concrete_buyer_candidate_set_results=tuple(concrete_nodes),
    )
    trade_set = OrderControlTvtMpGeneralTradeRankSetResult(
        concrete_buyer_candidate_set_result=concrete_set,
        node_trade_rank_results=tuple(trade_nodes),
    )
    fifo_set = OrderControlTvtMpFifoInspectionSetResult(
        general_trade_rank_set_result=trade_set,
        node_fifo_inspection_results=tuple(fifo_nodes),
    )
    local_set = OrderControlTvtMpLocalVirtualCalculationSetResult(
        fifo_inspection_set_result=fifo_set,
        node_local_virtual_calculation_results=tuple(local_nodes),
    )
    economic_set = OrderControlTvtMpEconomicEvaluationSetResult(
        local_virtual_calculation_set_result=local_set,
        node_economic_evaluation_results=tuple(economic_nodes),
    )
    selection_set = OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=economic_set,
        node_candidate_selection_results=tuple(selection_nodes),
    )
    return OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=selection_set,
        node_payment_and_compensation_results=tuple(payment_nodes),
    )


def _selected_spec(
    node_name,
    *,
    partition_3,
    partition_4=(),
    partition_1=(),
    partition_2=(),
    remaining,
    leading=(),
    buyer_records=(),
):
    sequence = _sequence(
        node_name,
        partition_1=partition_1,
        partition_2=partition_2,
        partition_3=partition_3,
        partition_4=partition_4,
        remaining=remaining,
    )
    selected = _economic_candidate(node_name, sequence)
    routes = {}
    for visit_key in remaining:
        routes[visit_key] = "collector-" + visit_key[0]
    return {
        "node_name": node_name,
        "build_status": COMPLETE,
        "selected": selected,
        "remaining": remaining,
        "leading": leading,
        "buyer_records": buyer_records,
        "routes": routes,
    }


def _fallback_spec(node_name, *, remaining, build_status, leading=(), arrived=()):
    routes = {}
    for visit_key in remaining:
        routes[visit_key] = "base-" + visit_key[0]
    return {
        "node_name": node_name,
        "build_status": build_status,
        "selected": None,
        "remaining": remaining,
        "leading": leading,
        "arrived": arrived,
        "routes": routes,
        "eligible_before_limit": len(remaining) + 2,
    }


def _empty_window_spec(node_name):
    return {
        "node_name": node_name,
        "build_status": NO_ENTRY,
        "selected": None,
        "decision": (),
        "leading": (),
        "remaining": (),
        "routes": {},
    }


def _fully_preconfirmed_spec(node_name):
    first = _visit("old_a")
    second = _visit("old_b")
    return {
        "node_name": node_name,
        "build_status": NO_ENTRY,
        "selected": None,
        "decision": (first, second),
        "leading": (first, second),
        "remaining": (),
        "routes": {first: "kept-a", second: "kept-b"},
    }


def _merge_routes(specs):
    routes = {}
    for spec in specs:
        for key, route in spec.get("routes", {}).items():
            routes[key] = route
    return routes


def _build(specs):
    cleaned = []
    for spec in specs:
        copied = dict(spec)
        copied.pop("routes", None)
        cleaned.append(copied)
    return _payment_set_from_nodes(cleaned, collector_routes=_merge_routes(specs))


def _ranks(result, node_index=0):
    records = result.node_final_rank_results[node_index].final_rank_visits
    pairs = []
    for record in records:
        pairs.append(
            (
                record.visit_key,
                record.final_local_rank,
                record.formal_route_next_link_name,
                record.finalization_source,
            )
        )
    return pairs


# ---------------------------------------------------------------------------
# Public types and API
# ---------------------------------------------------------------------------


def test_final_rank_status_enum_members_and_values():
    status = OrderControlTvtMpFinalRankStatus
    assert status.SELECTED_CANDIDATE_RANKS.value == "selected_candidate_ranks"
    assert status.BASELINE_FALLBACK_RANKS.value == "baseline_fallback_ranks"
    assert status.NO_VISITS_TO_CONFIRM.value == "no_visits_to_confirm"
    assert [member.name for member in status] == [
        "SELECTED_CANDIDATE_RANKS",
        "BASELINE_FALLBACK_RANKS",
        "NO_VISITS_TO_CONFIRM",
    ]


def test_finalization_source_enum_members_and_values():
    source = OrderControlTvtMpFinalizationSource
    assert source.SELECTED_CANDIDATE.value == "selected_candidate"
    assert source.BASELINE.value == "baseline"
    assert [member.name for member in source] == [
        "SELECTED_CANDIDATE",
        "BASELINE",
    ]


def test_public_results_are_frozen_with_field_order():
    assert OrderControlTvtMpFinalRankVisitRecord.__dataclass_fields__
    assert OrderControlTvtNodeMpFinalRankResult.__dataclass_fields__
    assert OrderControlTvtMpFinalRankSetResult.__dataclass_fields__
    visit_fields = [
        field.name for field in OrderControlTvtMpFinalRankVisitRecord.__dataclass_fields__.values()
    ]
    # dataclass field order follows definition order on the class.
    assert tuple(OrderControlTvtMpFinalRankVisitRecord.__dataclass_fields__) == (
        "visit_key",
        "final_local_rank",
        "formal_route_next_link_name",
        "finalization_source",
    )
    assert tuple(OrderControlTvtNodeMpFinalRankResult.__dataclass_fields__) == (
        "node_name",
        "final_rank_status",
        "selected_candidate_economic_result",
        "final_rank_visits",
    )
    assert tuple(OrderControlTvtMpFinalRankSetResult.__dataclass_fields__) == (
        "payment_and_compensation_set_result",
        "node_final_rank_results",
    )
    assert visit_fields == list(
        tuple(OrderControlTvtMpFinalRankVisitRecord.__dataclass_fields__)
    )
    record = OrderControlTvtMpFinalRankVisitRecord(
        visit_key=_visit("a"),
        final_local_rank=1,
        formal_route_next_link_name="out",
        finalization_source=OrderControlTvtMpFinalizationSource.BASELINE,
    )
    try:
        record.final_local_rank = 2
        frozen_rejected = False
    except Exception:
        frozen_rejected = True
    assert frozen_rejected is True


def test_public_columns_are_tuples_and_keep_same_objects():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="trade-out")
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    payment_set = _build([spec])
    selected = spec["selected"]
    result = build_tvt_mp_final_ranks(payment_set)
    assert result.payment_and_compensation_set_result is payment_set
    assert isinstance(result.node_final_rank_results, tuple)
    node_result = result.node_final_rank_results[0]
    assert isinstance(node_result.final_rank_visits, tuple)
    assert node_result.selected_candidate_economic_result is selected


def test_result_does_not_keep_live_world_vehicle_rank_state_or_rng():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="trade-out")
    result = build_tvt_mp_final_ranks(
        _build([
            _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
        ])
    )
    world = World(
        name="final-rank-live",
        deltan=1,
        reaction_time=1.0,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    rank_state = OrderControlTvtNodeRankState("merge")
    forbidden_types = (World, Vehicle, OrderControlTvtNodeRankState)
    seen = [result, world, rank_state]
    assert type(world.rng).__name__
    stack = [result]
    while len(stack) > 0:
        current = stack.pop()
        assert not isinstance(current, forbidden_types)
        if isinstance(current, tuple):
            for item in current:
                stack.append(item)
            continue
        if hasattr(current, "__dataclass_fields__"):
            for field_name in current.__dataclass_fields__:
                stack.append(getattr(current, field_name))
    assert seen[0] is result


def test_forbidden_fields_are_absent():
    for cls in (
        OrderControlTvtMpFinalRankVisitRecord,
        OrderControlTvtNodeMpFinalRankResult,
        OrderControlTvtMpFinalRankSetResult,
    ):
        for field_name in cls.__dataclass_fields__:
            assert field_name not in _FORBIDDEN_RESULT_FIELD_NAMES


def test_public_api_is_one_positional_function():
    signature = inspect.signature(build_tvt_mp_final_ranks)
    parameters = list(signature.parameters.values())
    assert len(parameters) == 1
    assert parameters[0].name == "payment_and_compensation_set_result"
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[0].default is inspect.Parameter.empty
    source = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    public_names = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            public_names.append(node.name)
    assert public_names == ["build_tvt_mp_final_ranks"]


def test_rejects_input_that_is_not_a_payment_set():
    try:
        build_tvt_mp_final_ranks("not-a-payment-set")
        raised = False
    except ValueError:
        raised = True
    assert raised is True


# ---------------------------------------------------------------------------
# Branch 1
# ---------------------------------------------------------------------------


def test_branch1_partition_3_only_uses_selected_source_and_saved_route():
    visit = _binding_visit(
        "scope",
        rank=1,
        partition=PARTITION_3,
        route="trade-out",
        role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
    )
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    # Collector route differs. Selected ranks must keep the binding route.
    spec["routes"][_visit("scope")] = "collector-should-not-win"
    result = build_tvt_mp_final_ranks(_build([spec]))
    node_result = result.node_final_rank_results[0]
    assert node_result.final_rank_status is (
        OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS
    )
    assert _ranks(result) == [
        (
            _visit("scope"),
            1,
            "trade-out",
            OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE,
        )
    ]


def test_branch1_partition_3_then_partition_4_keeps_saved_order():
    first = _binding_visit("buyer", rank=2, partition=PARTITION_3, route="buy-out")
    second = _binding_visit("tail_z", rank=3, partition=PARTITION_4, route="z-out")
    third = _binding_visit("tail_a", rank=4, partition=PARTITION_4, route="a-out")
    confirmed = _binding_visit("old", rank=1, partition=PARTITION_1, route="old-out")
    remaining = (_visit("buyer"), _visit("tail_z"), _visit("tail_a"))
    spec = _selected_spec(
        "merge",
        partition_1=(confirmed,),
        partition_3=(first,),
        partition_4=(second, third),
        remaining=remaining,
    )
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert _ranks(result) == [
        (_visit("buyer"), 1, "buy-out", OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE),
        (_visit("tail_z"), 2, "z-out", OrderControlTvtMpFinalizationSource.BASELINE),
        (_visit("tail_a"), 3, "a-out", OrderControlTvtMpFinalizationSource.BASELINE),
    ]
    keys = []
    for record in result.node_final_rank_results[0].final_rank_visits:
        keys.append(record.visit_key)
    assert _visit("old") not in keys


def test_branch1_partition_4_may_be_empty_when_trade_scope_covers_window():
    first = _binding_visit("buyer", rank=1, partition=PARTITION_3, route="buy-out")
    second = _binding_visit("later", rank=2, partition=PARTITION_3, route="later-out")
    # k_last_buyer 2 is above the remaining window length 1, so partition 4 is empty.
    spec = _selected_spec(
        "merge",
        partition_3=(first, second),
        remaining=(_visit("buyer"),),
    )
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert len(result.node_final_rank_results[0].final_rank_visits) == 2
    assert result.node_final_rank_results[0].final_rank_visits[1].finalization_source is (
        OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE
    )


def test_branch1_does_not_use_payment_record_order_as_rank_order():
    first = _binding_visit("buyer_b", rank=1, partition=PARTITION_3, route="b-out")
    second = _binding_visit("buyer_a", rank=2, partition=PARTITION_3, route="a-out")
    buyer_records = (
        OrderControlTvtMpBuyerPaymentRecord(
            visit_key=_visit("buyer_a"),
            vehicle_name="buyer_a",
            payment_P_b=9.0,
        ),
        OrderControlTvtMpBuyerPaymentRecord(
            visit_key=_visit("buyer_b"),
            vehicle_name="buyer_b",
            payment_P_b=1.0,
        ),
    )
    spec = _selected_spec(
        "merge",
        partition_3=(first, second),
        remaining=(_visit("buyer_b"), _visit("buyer_a")),
        buyer_records=buyer_records,
    )
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert _ranks(result)[0][0] == _visit("buyer_b")
    assert _ranks(result)[1][0] == _visit("buyer_a")


def test_branch1_does_not_repeat_partition_2():
    preconfirmed = _binding_visit("lead", rank=1, partition=PARTITION_2, route="lead-out")
    scope = _binding_visit("scope", rank=2, partition=PARTITION_3, route="scope-out")
    spec = _selected_spec(
        "merge",
        partition_2=(preconfirmed,),
        partition_3=(scope,),
        remaining=(_visit("scope"),),
        leading=(_visit("lead"),),
    )
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert len(result.node_final_rank_results[0].final_rank_visits) == 1
    assert result.node_final_rank_results[0].final_rank_visits[0].visit_key == _visit(
        "scope"
    )


# ---------------------------------------------------------------------------
# Branch 2 and branch 3
# ---------------------------------------------------------------------------


def test_branch2_complete_review_with_no_adopted_candidate_uses_whole_remaining_window():
    # Names are not alphabetical. Saved remaining order must be kept.
    remaining = (_visit("zeta"), _visit("alpha"), _visit("mid"))
    spec = _fallback_spec("merge", remaining=remaining, build_status=COMPLETE)
    result = build_tvt_mp_final_ranks(_build([spec]))
    node_result = result.node_final_rank_results[0]
    assert node_result.final_rank_status is (
        OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS
    )
    assert node_result.selected_candidate_economic_result is None
    assert _ranks(result) == [
        (_visit("zeta"), 1, "base-zeta", OrderControlTvtMpFinalizationSource.BASELINE),
        (_visit("alpha"), 2, "base-alpha", OrderControlTvtMpFinalizationSource.BASELINE),
        (_visit("mid"), 3, "base-mid", OrderControlTvtMpFinalizationSource.BASELINE),
    ]


def test_branch2_keeps_visits_beyond_candidate_count_limit():
    remaining = (_visit("one"), _visit("two"), _visit("three"))
    spec = _fallback_spec("merge", remaining=remaining, build_status=COMPLETE)
    spec["eligible_before_limit"] = 5
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert len(result.node_final_rank_results[0].final_rank_visits) == 3


def test_branch2_infeasible_and_unresolved_candidates_still_fall_back():
    unresolved = _local_result(
        "merge",
        _sequence(
            "merge",
            partition_3=(
                _binding_visit("unresolved", rank=1, partition=PARTITION_3, route="u"),
            ),
            remaining=(_visit("zeta"),),
        ),
    )
    # Mark the extra local result unresolved without making it selected.
    unresolved = OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name="merge",
        concrete_buyer_candidate_set=unresolved.concrete_buyer_candidate_set,
        binding_rank_sequence=unresolved.binding_rank_sequence,
        baseline_timestep_T=10,
        configured_horizon_steps=6,
        final_virtual_timestep=10,
        final_offset=0,
        simulated_timestep_count=1,
        stop_reason=(
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
        ),
        resolved=False,
        required_passage_records=(),
        unresolved_reasons=(),
        timestep_results=(),
        final_vehicle_records=(),
        final_inlink_records=(),
        final_outlink_records=(),
        final_node_record=unresolved.final_node_record,
        final_boundary_records=(),
    )
    infeasible_sequence = _sequence(
        "merge",
        partition_3=(
            _binding_visit("infeasible", rank=1, partition=PARTITION_3, route="i"),
        ),
        remaining=(_visit("zeta"), _visit("alpha")),
    )
    infeasible = _economic_candidate("merge", infeasible_sequence, feasible=False)
    spec = _fallback_spec(
        "merge",
        remaining=(_visit("zeta"), _visit("alpha")),
        build_status=COMPLETE,
    )
    spec["economic_candidates"] = (infeasible,)
    spec["extra_local_results"] = (unresolved,)
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert result.node_final_rank_results[0].final_rank_status is (
        OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS
    )
    assert len(result.node_final_rank_results[0].final_rank_visits) == 2


def test_branch3_information_shortage_is_fallback_not_economic_failure():
    remaining = (_visit("stay"), _visit("next"))
    for build_status in (UNRESOLVED_ARRIVALS, UNRESOLVED_RIGHT, UNRESOLVED_PASSAGES):
        spec = _fallback_spec("merge", remaining=remaining, build_status=build_status)
        result = build_tvt_mp_final_ranks(_build([spec]))
        node_result = result.node_final_rank_results[0]
        assert node_result.final_rank_status is (
            OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS
        )
        assert node_result.selected_candidate_economic_result is None
        assert node_result.final_rank_visits[0].formal_route_next_link_name == "base-stay"
        assert node_result.final_rank_visits[1].visit_key == _visit("next")


def test_fallback_does_not_include_preconfirmed_leading_visits():
    remaining = (_visit("rest"),)
    spec = _fallback_spec(
        "merge",
        remaining=remaining,
        build_status=COMPLETE,
        leading=(_visit("lead"),),
    )
    spec["routes"][_visit("lead")] = "lead-out"
    result = build_tvt_mp_final_ranks(_build([spec]))
    assert result.node_final_rank_results[0].final_rank_visits[0].visit_key == _visit(
        "rest"
    )


# ---------------------------------------------------------------------------
# Branch 4 and branch 5
# ---------------------------------------------------------------------------


def test_branch4_empty_decision_window_is_no_visits_without_fallback():
    spec = _empty_window_spec("quiet")
    payment_set = _build([spec])
    result = build_tvt_mp_final_ranks(payment_set)
    node_result = result.node_final_rank_results[0]
    assert node_result.final_rank_status is (
        OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM
    )
    assert node_result.selected_candidate_economic_result is None
    assert node_result.final_rank_visits == ()
    payment_node = payment_set.node_payment_and_compensation_results[0]
    assert payment_node.payment_and_compensation_status is NO_SELECTED
    assert payment_node.buyer_payment_records == ()
    assert payment_node.seller_compensation_records == ()
    economic_node = (
        payment_set.candidate_selection_set_result
        .economic_evaluation_set_result
        .node_economic_evaluation_results[0]
    )
    assert economic_node.candidate_economic_evaluation_results == ()


def test_branch5_fully_preconfirmed_window_is_no_visits_and_does_not_repeat_visits():
    spec = _fully_preconfirmed_spec("merge")
    result = build_tvt_mp_final_ranks(_build([spec]))
    node_result = result.node_final_rank_results[0]
    assert node_result.final_rank_status is (
        OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM
    )
    assert node_result.final_rank_visits == ()
    assert node_result.selected_candidate_economic_result is None


def test_branch4_and_branch5_share_status_but_not_decision_window_cause():
    result = build_tvt_mp_final_ranks(
        _build([_empty_window_spec("empty"), _fully_preconfirmed_spec("full")])
    )
    assert result.node_final_rank_results[0].node_name == "empty"
    assert result.node_final_rank_results[1].node_name == "full"
    assert result.node_final_rank_results[0].final_rank_status is (
        result.node_final_rank_results[1].final_rank_status
    )
    leading_nodes = (
        result.payment_and_compensation_set_result
        .candidate_selection_set_result
        .economic_evaluation_set_result
        .local_virtual_calculation_set_result
        .fifo_inspection_set_result
        .general_trade_rank_set_result
        .concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .right_of_entry_selection_result
        .leading_confirmation_result
        .node_confirmation_results
    )
    assert leading_nodes[0].decision_window_visit_keys == ()
    assert len(leading_nodes[1].decision_window_visit_keys) == 2
    assert leading_nodes[1].remaining_decision_window_visit_keys == ()


def test_node_order_follows_payment_set_order():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="out")
    result = build_tvt_mp_final_ranks(
        _build([
            _empty_window_spec("first"),
            _selected_spec("second", partition_3=(visit,), remaining=(_visit("scope"),)),
            _fallback_spec(
                "third",
                remaining=(_visit("rest"),),
                build_status=UNRESOLVED_ARRIVALS,
            ),
        ])
    )
    names = []
    statuses = []
    for node_result in result.node_final_rank_results:
        names.append(node_result.node_name)
        statuses.append(node_result.final_rank_status)
    assert names == ["first", "second", "third"]
    assert statuses == [
        OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM,
        OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS,
        OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS,
    ]


# ---------------------------------------------------------------------------
# Inconsistencies
# ---------------------------------------------------------------------------


def test_rejects_non_tuple_payment_column():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="out")
    payment_set = _build([
        _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    ])
    broken = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=payment_set.candidate_selection_set_result,
        node_payment_and_compensation_results=list(
            payment_set.node_payment_and_compensation_results
        ),
    )
    try:
        build_tvt_mp_final_ranks(broken)
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True


def test_rejects_node_name_mismatch():
    spec = _empty_window_spec("merge")
    payment_set = _build([spec])
    selection_nodes = (
        payment_set.candidate_selection_set_result.node_candidate_selection_results
    )
    replaced = (
        OrderControlTvtNodeMpCandidateSelectionResult(
            node_name="other",
            selection_status=selection_nodes[0].selection_status,
            selected_candidate_economic_result=None,
            rng_was_used=False,
        ),
    )
    broken_selection = OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=(
            payment_set.candidate_selection_set_result.economic_evaluation_set_result
        ),
        node_candidate_selection_results=replaced,
    )
    broken = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=broken_selection,
        node_payment_and_compensation_results=(
            payment_set.node_payment_and_compensation_results
        ),
    )
    try:
        build_tvt_mp_final_ranks(broken)
        raised = False
    except RuntimeError as error:
        raised = True
        assert "Node name mismatch" in str(error)
    assert raised is True


def test_rejects_payment_status_that_disagrees_with_selection():
    spec = _empty_window_spec("merge")
    payment_set = _build([spec])
    payment_node = payment_set.node_payment_and_compensation_results[0]
    replaced_payment = OrderControlTvtNodeMpPaymentAndCompensationResult(
        node_name="merge",
        payment_and_compensation_status=CALCULATED,
        selected_candidate_economic_result=None,
        buyer_payment_records=(),
        seller_compensation_records=(),
    )
    broken = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=payment_set.candidate_selection_set_result,
        node_payment_and_compensation_results=(replaced_payment,),
    )
    assert payment_node.payment_and_compensation_status is NO_SELECTED
    try:
        build_tvt_mp_final_ranks(broken)
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True


def test_rejects_no_selected_status_with_payment_records():
    spec = _fallback_spec(
        "merge",
        remaining=(_visit("rest"),),
        build_status=COMPLETE,
    )
    spec["buyer_records"] = (
        OrderControlTvtMpBuyerPaymentRecord(
            visit_key=_visit("rest"),
            vehicle_name="rest",
            payment_P_b=1.0,
        ),
    )
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "empty payment" in str(error)
    assert raised is True


def test_rejects_selected_candidate_that_is_not_the_same_object():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="out")
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    original = spec["selected"]
    copied = OrderControlTvtMpCandidateEconomicEvaluationResult(
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
    spec["selected"] = copied
    spec["economic_candidates"] = (original,)
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "same object" in str(error)
        assert "not converted" in str(error)
    assert raised is True


def test_rejects_selected_candidate_when_remaining_window_is_empty():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="out")
    sequence = _sequence(
        "merge",
        partition_3=(visit,),
        remaining=(),
    )
    # k_decision_window 0 with a selected candidate is a saved contradiction.
    sequence = OrderControlTvtMpLocalBindingRankSequence(
        node_name="merge",
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=sequence.concrete_buyer_candidate_set,
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=(visit,),
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=(visit,),
        k_last_buyer=1,
        k_decision_window=0,
        k_fixed=1,
    )
    selected = _economic_candidate("merge", sequence)
    spec = _fully_preconfirmed_spec("merge")
    spec["build_status"] = NO_ENTRY
    spec["selected"] = selected
    spec["payment_status"] = CALCULATED
    spec["selection_status"] = SELECTED
    spec["economic_candidates"] = (selected,)
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "not converted into" in str(error) or "remaining decision window is empty" in str(error)
    assert raised is True


def test_rejects_information_shortage_status_when_remaining_window_is_empty():
    spec = _empty_window_spec("merge")
    spec["build_status"] = UNRESOLVED_ARRIVALS
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "NOT_BUILT_NO_RIGHT_OF_ENTRY" in str(error)
    assert raised is True


def test_rejects_no_entry_status_when_remaining_window_is_non_empty():
    spec = _fallback_spec(
        "merge",
        remaining=(_visit("rest"),),
        build_status=NO_ENTRY,
    )
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "does not match" in str(error)
    assert raised is True


def test_rejects_missing_binding_sequence_without_fallback():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="out")
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    selected = spec["selected"]
    local_result = selected.candidate_local_virtual_calculation_result
    broken_local = OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name=local_result.node_name,
        concrete_buyer_candidate_set=local_result.concrete_buyer_candidate_set,
        binding_rank_sequence=None,
        baseline_timestep_T=local_result.baseline_timestep_T,
        configured_horizon_steps=local_result.configured_horizon_steps,
        final_virtual_timestep=local_result.final_virtual_timestep,
        final_offset=local_result.final_offset,
        simulated_timestep_count=local_result.simulated_timestep_count,
        stop_reason=local_result.stop_reason,
        resolved=local_result.resolved,
        required_passage_records=local_result.required_passage_records,
        unresolved_reasons=local_result.unresolved_reasons,
        timestep_results=local_result.timestep_results,
        final_vehicle_records=local_result.final_vehicle_records,
        final_inlink_records=local_result.final_inlink_records,
        final_outlink_records=local_result.final_outlink_records,
        final_node_record=local_result.final_node_record,
        final_boundary_records=local_result.final_boundary_records,
    )
    broken_selected = OrderControlTvtMpCandidateEconomicEvaluationResult(
        candidate_local_virtual_calculation_result=broken_local,
        buyer_economic_records=selected.buyer_economic_records,
        seller_economic_records=selected.seller_economic_records,
        total_buyer_value_G=selected.total_buyer_value_G,
        total_required_compensation_R=selected.total_required_compensation_R,
        surplus=selected.surplus,
        economically_feasible=selected.economically_feasible,
        infeasibility_reasons=selected.infeasibility_reasons,
    )
    spec["selected"] = broken_selected
    spec["economic_candidates"] = (broken_selected,)
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "not converted into baseline fallback" in str(error)
    assert raised is True


def test_rejects_partition_1_visit_inside_partition_3():
    old = _binding_visit("old", rank=1, partition=PARTITION_1, route="old-out")
    repeated = _binding_visit("old", rank=2, partition=PARTITION_3, route="old-again")
    spec = _selected_spec(
        "merge",
        partition_1=(old,),
        partition_3=(repeated,),
        remaining=(_visit("old"),),
    )
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "already confirmed" in str(error)
    assert raised is True


def test_rejects_duplicate_visit_across_partition_3_and_4():
    first = _binding_visit("same", rank=1, partition=PARTITION_3, route="a")
    second = _binding_visit("same", rank=2, partition=PARTITION_4, route="b")
    spec = _selected_spec(
        "merge",
        partition_3=(first,),
        partition_4=(second,),
        remaining=(_visit("same"), _visit("same")),
    )
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True


def test_rejects_binding_rank_that_is_not_consecutive():
    visit = _binding_visit("scope", rank=4, partition=PARTITION_3, route="out")
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "consecutive rank" in str(error)
    assert raised is True


def test_rejects_k_fixed_that_disagrees_with_saved_counts():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="out")
    sequence = _sequence(
        "merge",
        partition_3=(visit,),
        remaining=(_visit("scope"),),
    )
    broken = OrderControlTvtMpLocalBindingRankSequence(
        node_name=sequence.node_name,
        baseline_timestep_T=sequence.baseline_timestep_T,
        concrete_buyer_candidate_set=sequence.concrete_buyer_candidate_set,
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=sequence.trade_scope_of_this_candidate_visits,
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=sequence.visits_in_binding_order,
        k_last_buyer=1,
        k_decision_window=1,
        k_fixed=9,
    )
    selected = _economic_candidate("merge", broken)
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    spec["selected"] = selected
    spec["economic_candidates"] = (selected,)
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "k_fixed" in str(error)
    assert raised is True


def test_rejects_wrong_binding_partition_on_partition_3():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_4, route="out")
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "binding partition" in str(error)
    assert raised is True


def test_rejects_missing_collector_route_on_fallback():
    spec = _fallback_spec(
        "merge",
        remaining=(_visit("rest"),),
        build_status=COMPLETE,
    )
    spec["routes"] = {}
    try:
        build_tvt_mp_final_ranks(_build([spec]))
        raised = False
    except RuntimeError as error:
        raised = True
        assert "not guessed" in str(error)
    assert raised is True


def test_rejects_none_and_empty_formal_routes():
    none_spec = _fallback_spec(
        "merge",
        remaining=(_visit("rest"),),
        build_status=COMPLETE,
    )
    none_spec["routes"][_visit("rest")] = None
    empty_spec = _fallback_spec(
        "merge",
        remaining=(_visit("rest"),),
        build_status=COMPLETE,
    )
    empty_spec["routes"][_visit("rest")] = ""
    for spec in (none_spec, empty_spec):
        try:
            build_tvt_mp_final_ranks(_build([spec]))
            raised = False
        except RuntimeError as error:
            raised = True
            assert "not guessed" in str(error)
        assert raised is True


def test_one_node_inconsistency_stops_without_a_partial_result():
    bad = _fallback_spec(
        "bad",
        remaining=(_visit("rest"),),
        build_status=COMPLETE,
    )
    bad["routes"] = {}
    good = _empty_window_spec("good")
    try:
        build_tvt_mp_final_ranks(_build([bad, good]))
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True


# ---------------------------------------------------------------------------
# Immutability and source shape
# ---------------------------------------------------------------------------


def test_inputs_collector_rank_state_and_vehicle_are_unchanged():
    visit = _binding_visit("scope", rank=1, partition=PARTITION_3, route="trade-out")
    spec = _selected_spec("merge", partition_3=(visit,), remaining=(_visit("scope"),))
    payment_set = _build([spec])
    collector = (
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
        .arrived_confirmation_result
        .alignment_fork_result
        .fork_result
        .collector
    )
    routes_before = dict(collector.routes)
    decision_before = (
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
        .decision_window_visit_keys
    )
    rank_state = OrderControlTvtNodeRankState("merge")
    rank_state.register_undetermined_visit(_visit("scope"))
    confirmed_before = rank_state.k_confirmed()
    world = World(
        name="unchanged",
        deltan=1,
        reaction_time=1.0,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=3,
    )
    world.addNode("orig", 0, 0)
    world.addNode("dest", 1, 0)
    world.addLink("in", "orig", "dest", length=200, free_flow_speed=20)
    world.addVehicle("orig", "dest", 0, name="scope")
    vehicle = world.VEHICLES["scope"]
    paid_before = vehicle.payment_paid
    received_before = vehicle.payment_received
    log_before = list(vehicle.order_exchange_log)
    seed_before = world.random_seed
    build_tvt_mp_final_ranks(payment_set)
    assert collector.routes == routes_before
    assert (
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
        .decision_window_visit_keys
    ) == decision_before
    assert rank_state.k_confirmed() == confirmed_before
    assert vehicle.payment_paid == paid_before
    assert vehicle.payment_received == received_before
    assert list(vehicle.order_exchange_log) == log_before
    assert world.random_seed == seed_before


def test_production_source_keeps_explicit_loops_and_forbids_out_of_scope_work():
    source = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    public_names = []
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            public_names.append(node.name)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    assert public_names == ["build_tvt_mp_final_ranks"]
    assert "for payment_node_result in saved_columns.payment_nodes:" in source
    assert "for binding_visit in trade_scope_visits:" in source
    assert "for binding_visit in outside_visits:" in source
    assert "for visit_key in remaining_decision_window_visit_keys:" in source
    assert "dataclass(frozen=True)" in source
    assert "get_baseline_visit_snapshot" in source
    forbidden_calls = {
        "calculate_tvt_mp_payments_and_compensations",
        "select_tvt_mp_candidates",
        "evaluate_tvt_mp_candidate_economics",
        "evaluate_tvt_mp_candidate_local_virtual_calculations",
        "build_tvt_mp_fifo_inspection_results",
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


def test_rejects_a_missing_upstream_node_result():
    spec = _empty_window_spec("merge")
    payment_set = _build([spec])
    selection = payment_set.candidate_selection_set_result
    broken_selection = OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=selection.economic_evaluation_set_result,
        node_candidate_selection_results=(),
    )
    broken = OrderControlTvtMpPaymentAndCompensationSetResult(
        candidate_selection_set_result=broken_selection,
        node_payment_and_compensation_results=(
            payment_set.node_payment_and_compensation_results
        ),
    )
    try:
        build_tvt_mp_final_ranks(broken)
        raised = False
    except RuntimeError as error:
        raised = True
        assert "not a normal empty-Node outcome" in str(error)
    assert raised is True


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
