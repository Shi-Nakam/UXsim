# Tests for the read-only local binding rank sequence.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_local_binding_rank_sequence.py

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryResult,
)
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
)
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
    OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtMpFifoInspectionSetResult,
    OrderControlTvtNodeMpFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtMpGeneralTradeRankSetResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
    OrderControlTvtMpLocalBindingTradeRole,
    build_tvt_mp_local_binding_rank_sequence,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionStatus,
)


class _Collector:
    def __init__(self, records: dict[tuple[str, int], dict]) -> None:
        self.records = records

    def get_baseline_visit_snapshot(self, vehicle_name: str, visit_id: int):
        record = self.records.get((vehicle_name, visit_id))
        if record is None:
            return None
        return dict(record)


def _record(
    vehicle_name: str,
    visit_id: int,
    *,
    vehicle_id: int,
    route: str | None,
    arrived: bool,
) -> dict:
    return {
        "vehicle_name": vehicle_name,
        "vehicle_id": vehicle_id,
        "node_name": "merge",
        "inlink_name": "in_a",
        "visit_id": visit_id,
        "was_arrived_at_snapshot": arrived,
        "baseline_arrival_timestep": 10,
        "arrival_tiebreaker": 0.2,
        "route_next_link_name": route,
        "baseline_passage_timestep": None,
    }


def _confirm_formal(state: OrderControlTvtNodeRankState, visit_key, route: str) -> None:
    state.register_undetermined_visit(visit_key)
    state.confirm_visits_and_formal_target_node_routes_atomically(
        [(visit_key, route)],
        frozenset({"out", "side", "snap", "ledger_out"}),
    )


def _build_chain(
    *,
    rank_state: OrderControlTvtNodeRankState,
    collector: _Collector,
    arrived_keys: tuple,
    leading_keys: tuple,
    remaining_keys: tuple,
    trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
    k_confirmed_before: int,
    preserves_fifo: bool = True,
    baseline_timestep_T: int = 10,
):
    alignment = OrderControlTvtSnapshotUndeterminedAlignmentResult(
        node_name="merge",
        resolved_undetermined_visits=(),
        unresolved_undetermined_visits=(),
        unregistered_collector_visit_keys=(),
    )
    fork_result = OrderControlBaselineForkResult(
        collector=collector,  # type: ignore[arg-type]
        target_node_names=("merge",),
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=6,
        fork_steps_executed=6,
        final_fork_timestep=baseline_timestep_T + 6,
        registered_visit_count=1,
        inlink_physical_orders=(),
        downstream_boundary_result=OrderControlBaselineDownstreamBoundaryResult(
            node_results=(),
        ),
    )
    alignment_fork = OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=(alignment,),
    )
    arrived = OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment_fork,
        node_confirmation_results=(
            OrderControlTvtNodeArrivedUndeterminedConfirmationResult(
                node_name="merge",
                confirmed_arrived_visit_keys=arrived_keys,
                confirm_result=OrderControlTvtConfirmResult(
                    k_confirmed_before=k_confirmed_before,
                    k_confirmed_after=k_confirmed_before + len(arrived_keys),
                    newly_confirmed_count=len(arrived_keys),
                ),
            ),
        ),
    )
    leading = OrderControlTvtLeadingNonparticipatingConfirmationResult(
        arrived_confirmation_result=arrived,
        node_confirmation_results=(
            OrderControlTvtNodeLeadingNonparticipatingConfirmationResult(
                node_name="merge",
                decision_window_visit_keys=leading_keys + remaining_keys,
                confirmed_leading_nonparticipating_visit_keys=leading_keys,
                remaining_decision_window_visit_keys=remaining_keys,
                confirm_result=OrderControlTvtConfirmResult(
                    k_confirmed_before=k_confirmed_before + len(arrived_keys),
                    k_confirmed_after=(
                        k_confirmed_before + len(arrived_keys) + len(leading_keys)
                    ),
                    newly_confirmed_count=len(leading_keys),
                ),
            ),
        ),
    )
    right_of_entry = OrderControlTvtRightOfEntrySelectionResult(
        leading_confirmation_result=leading,
        node_selection_results=(
            OrderControlTvtNodeRightOfEntrySelectionResult(
                node_name="merge",
                selection_status=OrderControlTvtRightOfEntrySelectionStatus.SELECTED,
                right_of_entry_visit_key=("buy", 1),
                k_confirmed_before=k_confirmed_before,
            ),
        ),
    )
    candidate_visit_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=right_of_entry,
        max_tvt_candidate_visit_count=2,
        node_candidate_set_results=(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name="merge",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                right_of_entry_visit_key=("buy", 1),
                right_of_entry_baseline_passage_timestep=12,
                k_confirmed_before=k_confirmed_before,
                p_minus_one_eligible_visit_count_before_limit=2,
                candidate_visits=(),
            ),
        ),
    )
    inlink_result = OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=candidate_visit_set,
        node_inlink_candidate_physical_order_results=(
            OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
                node_name="merge",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                inlink_candidate_physical_orders=(),
            ),
        ),
    )
    concrete_node = OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
        node_name="merge",
        build_status=OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE,
        buyer_candidate_inlink_prefix_results=(),
        concrete_buyer_candidate_sets=(trade_rank_result.concrete_buyer_candidate_set,),
    )
    concrete_set_result = OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=inlink_result,
        node_concrete_buyer_candidate_set_results=(concrete_node,),
    )
    trade_set = OrderControlTvtMpGeneralTradeRankSetResult(
        concrete_buyer_candidate_set_result=concrete_set_result,
        node_trade_rank_results=(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name="merge",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                candidate_trade_rank_results=(trade_rank_result,),
            ),
        ),
    )
    candidate = OrderControlTvtMpCandidateFifoInspectionResult(
        general_trade_rank_result=trade_rank_result,
        preserves_inlink_fifo=preserves_fifo,
    )
    fifo_set = OrderControlTvtMpFifoInspectionSetResult(
        general_trade_rank_set_result=trade_set,
        node_fifo_inspection_results=(
            OrderControlTvtNodeMpFifoInspectionResult(
                node_name="merge",
                build_status=(
                    OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
                ),
                candidate_fifo_inspection_results=(candidate,),
            ),
        ),
    )
    return fifo_set, candidate, rank_state


def _trade_rank(
    *,
    last_buyer_rank: int = 2,
    buyers_sorted: tuple = (("buy", 1),),
    sellers_sorted: tuple = (("sell", 1),),
    nonparticipating_visits_sorted: tuple = (),
    trade_scope: tuple = (("buy", 1), ("sell", 1)),
    trade_order: tuple = (("buy", 1), ("sell", 1)),
    trade_rank_by_visit_key: dict | None = None,
) -> OrderControlTvtMpGeneralTradeRankResult:
    concrete = OrderControlTvtMpConcreteBuyerCandidateSet(
        buyers_sorted=buyers_sorted,
    )
    if trade_rank_by_visit_key is None:
        trade_rank_by_visit_key = {}
        for rank_number, visit_key in enumerate(trade_order, start=1):
            trade_rank_by_visit_key[visit_key] = rank_number
    return OrderControlTvtMpGeneralTradeRankResult(
        concrete_buyer_candidate_set=concrete,
        buyers_sorted=buyers_sorted,
        sellers_sorted=sellers_sorted,
        nonparticipating_visits_sorted=nonparticipating_visits_sorted,
        last_buyer_rank=last_buyer_rank,
        trade_scope=trade_scope,
        trade_order=trade_order,
        trade_rank_by_visit_key=trade_rank_by_visit_key,
    )


def _ready_case():
    rank_state = OrderControlTvtNodeRankState("merge")
    _confirm_formal(rank_state, ("gone", 1), "out")
    _confirm_formal(rank_state, ("old", 1), "ledger_out")
    _confirm_formal(rank_state, ("arr", 1), "out")
    _confirm_formal(rank_state, ("lead", 1), "side")
    records = {
        ("old", 1): _record("old", 1, vehicle_id=1, route="snap", arrived=True),
        ("arr", 1): _record("arr", 1, vehicle_id=2, route="out", arrived=True),
        ("lead", 1): _record("lead", 1, vehicle_id=3, route="side", arrived=False),
        ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
        ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=True),
        ("late", 1): _record("late", 1, vehicle_id=6, route="out", arrived=False),
    }
    # The already-passed visit has no collector record, so partition 1 omits it.
    collector = _Collector(records)
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=collector,
        arrived_keys=(("arr", 1),),
        leading_keys=(("lead", 1),),
        remaining_keys=(("buy", 1), ("sell", 1), ("late", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=2,
    )
    return fifo_set, candidate, rank_state, collector


def _leading_confirmation(fifo_set):
    return (
        fifo_set.general_trade_rank_set_result
        .concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .right_of_entry_selection_result
        .leading_confirmation_result
    )


def _leading_node(fifo_set):
    return _leading_confirmation(fifo_set).node_confirmation_results[0]


def _arrived_node(fifo_set):
    arrived = _leading_confirmation(fifo_set).arrived_confirmation_result
    return arrived.node_confirmation_results[0]


def _rebuild_with_fork_result(fifo_set, **fork_fields):
    """Copy one valid chain and replace only fork_result fields."""
    leading = _leading_confirmation(fifo_set)
    arrived = leading.arrived_confirmation_result
    alignment_fork = arrived.alignment_fork_result
    fork = alignment_fork.fork_result
    new_fork = dataclasses.replace(fork, **fork_fields)
    new_alignment_fork = dataclasses.replace(alignment_fork, fork_result=new_fork)
    new_arrived = dataclasses.replace(
        arrived,
        alignment_fork_result=new_alignment_fork,
    )
    return _rebuild_with_confirmation(
        fifo_set,
        arrived_confirmation_result=new_arrived,
    )


def _rebuild_with_confirmation(
    fifo_set,
    *,
    arrived_node=None,
    leading_node=None,
    arrived_confirmation_result=None,
):
    """Copy one valid chain and replace only the named confirmation node."""
    trade_set = fifo_set.general_trade_rank_set_result
    concrete = trade_set.concrete_buyer_candidate_set_result
    inlink = concrete.inlink_candidate_physical_order_result
    visit_set = inlink.candidate_visit_set_result
    right = visit_set.right_of_entry_selection_result
    leading = right.leading_confirmation_result
    arrived = leading.arrived_confirmation_result
    if arrived_confirmation_result is not None:
        arrived = arrived_confirmation_result
    elif arrived_node is not None:
        arrived = dataclasses.replace(
            arrived,
            node_confirmation_results=(arrived_node,),
        )
    if leading_node is not None:
        leading = dataclasses.replace(
            leading,
            arrived_confirmation_result=arrived,
            node_confirmation_results=(leading_node,),
        )
    else:
        leading = dataclasses.replace(
            leading,
            arrived_confirmation_result=arrived,
        )
    right = dataclasses.replace(right, leading_confirmation_result=leading)
    visit_set = dataclasses.replace(
        visit_set,
        right_of_entry_selection_result=right,
    )
    inlink = dataclasses.replace(inlink, candidate_visit_set_result=visit_set)
    concrete = dataclasses.replace(
        concrete,
        inlink_candidate_physical_order_result=inlink,
    )
    trade_set = dataclasses.replace(
        trade_set,
        concrete_buyer_candidate_set_result=concrete,
    )
    return dataclasses.replace(
        fifo_set,
        general_trade_rank_set_result=trade_set,
    )


def _rebuild_with_trade_rank(fifo_set, new_trade_rank, *, preserves_fifo=True):
    """Copy one valid chain and replace only the trade-rank result."""
    new_candidate = OrderControlTvtMpCandidateFifoInspectionResult(
        general_trade_rank_result=new_trade_rank,
        preserves_inlink_fifo=preserves_fifo,
    )
    trade_set = fifo_set.general_trade_rank_set_result
    trade_node = dataclasses.replace(
        trade_set.node_trade_rank_results[0],
        candidate_trade_rank_results=(new_trade_rank,),
    )
    trade_set = dataclasses.replace(
        trade_set,
        node_trade_rank_results=(trade_node,),
    )
    fifo_node = dataclasses.replace(
        fifo_set.node_fifo_inspection_results[0],
        candidate_fifo_inspection_results=(new_candidate,),
    )
    fifo_set = dataclasses.replace(
        fifo_set,
        general_trade_rank_set_result=trade_set,
        node_fifo_inspection_results=(fifo_node,),
    )
    return fifo_set, new_candidate


def _empty_ledger_case(trade_rank_result, records, remaining_keys):
    rank_state = OrderControlTvtNodeRankState("merge")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(records),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=remaining_keys,
        trade_rank_result=trade_rank_result,
        k_confirmed_before=0,
    )
    return fifo_set, candidate, rank_state


def _assert_builder_error(exception_type, fifo_set, candidate, rank_state, message_part):
    before_export = rank_state.export_state()
    try:
        build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
    except exception_type as exc:
        assert message_part in str(exc)
    else:
        raise AssertionError(f"expected {exception_type.__name__}")
    assert rank_state.export_state() == before_export


class _TradeRankWithDuplicateScope(OrderControlTvtMpGeneralTradeRankResult):
    """The public constructor rejects a duplicate trade_scope key.

    Only the column read by the builder is inconsistent. Private fields stay
    as the constructor stored them.
    """

    @property
    def trade_scope(self):
        return (("buy", 1), ("buy", 1))


class _TradeRankWithDuplicateOrderPrefix(OrderControlTvtMpGeneralTradeRankResult):
    """The public constructor rejects a duplicate trade_order key."""

    @property
    def trade_order(self):
        return (("buy", 1), ("buy", 1))


def test_public_types_are_frozen_and_importable():
    assert OrderControlTvtMpLocalBindingRankVisit is not None
    assert OrderControlTvtMpLocalBindingRankSequence is not None
    assert build_tvt_mp_local_binding_rank_sequence is not None
    assert dataclasses.is_dataclass(OrderControlTvtMpLocalBindingRankVisit)
    assert dataclasses.is_dataclass(OrderControlTvtMpLocalBindingRankSequence)
    remaining_list = [("buy", 1), ("sell", 1), ("late", 1)]
    rank_state = OrderControlTvtNodeRankState("merge")
    _confirm_formal(rank_state, ("gone", 1), "out")
    _confirm_formal(rank_state, ("old", 1), "ledger_out")
    _confirm_formal(rank_state, ("arr", 1), "out")
    _confirm_formal(rank_state, ("lead", 1), "side")
    collector = _Collector(
        {
            ("old", 1): _record("old", 1, vehicle_id=1, route="snap", arrived=True),
            ("arr", 1): _record("arr", 1, vehicle_id=2, route="out", arrived=True),
            ("lead", 1): _record("lead", 1, vehicle_id=3, route="side", arrived=False),
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=True),
            ("late", 1): _record("late", 1, vehicle_id=6, route="out", arrived=False),
        }
    )
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=collector,
        arrived_keys=(("arr", 1),),
        leading_keys=(("lead", 1),),
        remaining_keys=tuple(remaining_list),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=2,
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert isinstance(result.confirmed_before_this_baseline_visits, tuple)
    assert isinstance(result.preconfirmed_by_this_baseline_visits, tuple)
    assert isinstance(result.trade_scope_of_this_candidate_visits, tuple)
    assert isinstance(result.outside_trade_scope_inside_k_fixed_visits, tuple)
    assert isinstance(result.visits_in_binding_order, tuple)
    remaining_list.append(("mutated", 1))
    collector.records[("buy", 1)]["route_next_link_name"] = "changed"
    assert [visit.visit_key for visit in result.visits_in_binding_order] == [
        ("old", 1),
        ("arr", 1),
        ("lead", 1),
        ("buy", 1),
        ("sell", 1),
        ("late", 1),
    ]
    assert result.trade_scope_of_this_candidate_visits[0].route_next_link_name == "out"
    try:
        result.k_fixed = 99  # type: ignore[misc]
        raise AssertionError("expected frozen sequence")
    except dataclasses.FrozenInstanceError:
        pass
    try:
        result.visits_in_binding_order[0].binding_rank = 99  # type: ignore[misc]
        raise AssertionError("expected frozen visit")
    except dataclasses.FrozenInstanceError:
        pass


def test_four_partitions_orders_roles_and_k_values():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    before_export = rank_state.export_state()
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert [visit.visit_key for visit in result.confirmed_before_this_baseline_visits] == [
        ("old", 1)
    ]
    assert result.confirmed_before_this_baseline_visits[0].route_next_link_name == "snap"
    assert (
        result.confirmed_before_this_baseline_visits[0].route_origin
        is OrderControlTvtMpLocalBindingRouteOrigin.SNAPSHOT_ROUTE_ALREADY_DECIDED
    )
    assert rank_state.formal_route_next_link_name(("old", 1)) == "ledger_out"
    assert [
        visit.visit_key for visit in result.preconfirmed_by_this_baseline_visits
    ] == [("arr", 1), ("lead", 1)]
    assert result.preconfirmed_by_this_baseline_visits[0].route_next_link_name == "out"
    assert result.preconfirmed_by_this_baseline_visits[1].route_next_link_name == "side"
    assert [
        visit.visit_key for visit in result.trade_scope_of_this_candidate_visits
    ] == [("buy", 1), ("sell", 1)]
    assert (
        result.trade_scope_of_this_candidate_visits[0].trade_role
        is OrderControlTvtMpLocalBindingTradeRole.BUYER
    )
    assert (
        result.trade_scope_of_this_candidate_visits[1].trade_role
        is OrderControlTvtMpLocalBindingTradeRole.SELLER
    )
    assert (
        result.trade_scope_of_this_candidate_visits[0].route_origin
        is OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
    )
    assert [visit.visit_key for visit in result.outside_trade_scope_inside_k_fixed_visits] == [
        ("late", 1)
    ]
    assert (
        result.outside_trade_scope_inside_k_fixed_visits[0].trade_role
        is OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE
    )
    assert result.k_last_buyer == 2
    # k_decision_window counts the remaining suffix, not the full window.
    # The full window is the leading prefix plus that suffix (4 visits).
    leading_node = _leading_node(fifo_set)
    assert len(leading_node.decision_window_visit_keys) == 4
    assert len(leading_node.remaining_decision_window_visit_keys) == 3
    assert result.k_decision_window == 3
    assert result.k_fixed == 3
    assert [visit.binding_rank for visit in result.visits_in_binding_order] == [1, 2, 3, 4, 5, 6]
    assert rank_state.export_state() == before_export


def test_partition_4_is_empty_when_last_buyer_covers_the_window():
    rank_state = OrderControlTvtNodeRankState("merge")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=0,
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert result.outside_trade_scope_inside_k_fixed_visits == ()
    assert result.k_last_buyer == 2
    assert result.k_decision_window == 2
    assert result.k_fixed == 2


def test_duplicate_visit_across_partitions_is_runtime_error():
    rank_state = OrderControlTvtNodeRankState("merge")
    _confirm_formal(rank_state, ("buy", 1), "out")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(("buy", 1),),
        leading_keys=(),
        remaining_keys=(("sell", 1),),
        trade_rank_result=_trade_rank(
            last_buyer_rank=1,
            sellers_sorted=(),
            trade_scope=(("buy", 1),),
            trade_order=(("buy", 1),),
            trade_rank_by_visit_key={("buy", 1): 1},
        ),
        k_confirmed_before=0,
    )
    try:
        build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
        raise AssertionError("expected duplicate VisitKey RuntimeError")
    except RuntimeError as exc:
        assert "('buy', 1)" in str(exc)


def test_missing_partition_3_route_is_value_error_without_ledger_write():
    rank_state = OrderControlTvtNodeRankState("merge")
    before = rank_state.export_state()
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("buy", 1): _record("buy", 1, vehicle_id=4, route=None, arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=0,
    )
    try:
        build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
        raise AssertionError("expected missing route ValueError")
    except ValueError as exc:
        assert "('buy', 1)" in str(exc)
    assert rank_state.export_state() == before


def test_old_none_formal_route_outside_partition_1_does_not_stop_build():
    rank_state = OrderControlTvtNodeRankState("merge")
    rank_state.register_undetermined_visit(("ancient", 1))
    rank_state.confirm_visits_in_order([("ancient", 1)])
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=1,
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert result.confirmed_before_this_baseline_visits == ()
    assert rank_state.formal_route_next_link_name(("ancient", 1)) is None


def test_missing_partition_2_formal_route_is_value_error():
    rank_state = OrderControlTvtNodeRankState("merge")
    rank_state.register_undetermined_visit(("arr", 1))
    rank_state.confirm_visits_in_order([("arr", 1)])
    before = rank_state.export_state()
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("arr", 1): _record("arr", 1, vehicle_id=2, route="out", arrived=True),
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(("arr", 1),),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=0,
    )
    try:
        build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
        raise AssertionError("expected missing formal route ValueError")
    except ValueError as exc:
        assert "formal_route_next_link_name" in str(exc)
        assert "('arr', 1)" in str(exc)
    assert rank_state.export_state() == before


def test_rank_state_node_name_mismatch_is_value_error():
    fifo_set, candidate, _rank_state, _collector = _ready_case()
    other_state = OrderControlTvtNodeRankState("other")
    try:
        build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, other_state)
        raise AssertionError("expected node name ValueError")
    except ValueError as exc:
        assert "other" in str(exc)
        assert "merge" in str(exc)


def test_builder_does_not_call_confirmation_apis():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    rank_state.confirm_visits_in_order = MagicMock(  # type: ignore[method-assign]
        side_effect=AssertionError("old confirm API")
    )
    rank_state.confirm_visits_and_formal_target_node_routes_atomically = MagicMock(  # type: ignore[method-assign]
        side_effect=AssertionError("atomic confirm API")
    )
    build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
    rank_state.confirm_visits_in_order.assert_not_called()
    rank_state.confirm_visits_and_formal_target_node_routes_atomically.assert_not_called()


def test_partition_1_missing_both_routes_is_runtime_error():
    rank_state = OrderControlTvtNodeRankState("merge")
    rank_state.register_undetermined_visit(("old", 1))
    rank_state.confirm_visits_in_order([("old", 1)])
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("old", 1): _record("old", 1, vehicle_id=1, route=None, arrived=False),
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=1,
    )
    _assert_builder_error(RuntimeError, fifo_set, candidate, rank_state, "('old', 1)")
    assert rank_state.formal_route_next_link_name(("old", 1)) is None


def test_snapshot_route_does_not_overwrite_ledger_formal_route():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    old_visit = result.confirmed_before_this_baseline_visits[0]
    assert old_visit.route_next_link_name == "snap"
    assert (
        old_visit.route_origin
        is OrderControlTvtMpLocalBindingRouteOrigin.SNAPSHOT_ROUTE_ALREADY_DECIDED
    )
    assert rank_state.formal_route_next_link_name(("old", 1)) == "ledger_out"


def test_partition_1_prefix_longer_than_ledger_is_runtime_error():
    # Public confirm counts claim two ranks before this baseline, but the
    # ledger prefix is empty. The rank ledger itself is not altered.
    rank_state = OrderControlTvtNodeRankState("merge")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=2,
    )
    _assert_builder_error(RuntimeError, fifo_set, candidate, rank_state, "rank ledger")


def test_partition_2_arrived_then_leading_matches_ledger_order():
    rank_state = OrderControlTvtNodeRankState("merge")
    _confirm_formal(rank_state, ("arr", 1), "out")
    _confirm_formal(rank_state, ("lead", 1), "side")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("arr", 1): _record("arr", 1, vehicle_id=2, route="out", arrived=True),
                ("lead", 1): _record("lead", 1, vehicle_id=3, route="side", arrived=False),
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(("arr", 1),),
        leading_keys=(("lead", 1),),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=0,
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert [
        visit.visit_key for visit in result.preconfirmed_by_this_baseline_visits
    ] == [("arr", 1), ("lead", 1)]
    assert rank_state.assigned_rank(("arr", 1)) == 1
    assert rank_state.assigned_rank(("lead", 1)) == 2


def _break_arrived_confirm(fifo_set, **confirm_fields):
    arrived_node = _arrived_node(fifo_set)
    confirm_result = dataclasses.replace(arrived_node.confirm_result, **confirm_fields)
    broken_node = dataclasses.replace(arrived_node, confirm_result=confirm_result)
    return _rebuild_with_confirmation(fifo_set, arrived_node=broken_node)


def _break_leading_node(fifo_set, **node_fields):
    leading_node = _leading_node(fifo_set)
    if "confirm_result" in node_fields and isinstance(node_fields["confirm_result"], dict):
        node_fields["confirm_result"] = dataclasses.replace(
            leading_node.confirm_result,
            **node_fields["confirm_result"],
        )
    broken_node = dataclasses.replace(leading_node, **node_fields)
    return _rebuild_with_confirmation(fifo_set, leading_node=broken_node)


def test_arrived_newly_confirmed_count_mismatch_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_arrived_confirm(fifo_set, newly_confirmed_count=0)
    _assert_builder_error(
        RuntimeError,
        broken,
        candidate,
        rank_state,
        "newly_confirmed_count",
    )


def test_arrived_k_confirmed_after_mismatch_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_arrived_confirm(fifo_set, k_confirmed_after=9)
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "k_confirmed_after")


def test_arrived_confirm_count_rejects_bool():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_arrived_confirm(fifo_set, newly_confirmed_count=True)
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "Python int")


def test_leading_newly_confirmed_count_mismatch_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_leading_node(
        fifo_set,
        confirm_result={"newly_confirmed_count": 0},
    )
    _assert_builder_error(
        RuntimeError,
        broken,
        candidate,
        rank_state,
        "newly_confirmed_count",
    )


def test_leading_k_confirmed_before_does_not_continue_arrived_end():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    # Internal leading counts stay consistent: 0 + 1 = 1.
    # They no longer start at the arrived confirmation end.
    broken = _break_leading_node(
        fifo_set,
        confirm_result={
            "k_confirmed_before": 0,
            "k_confirmed_after": 1,
            "newly_confirmed_count": 1,
        },
    )
    _assert_builder_error(
        RuntimeError,
        broken,
        candidate,
        rank_state,
        "does not continue",
    )


def test_leading_k_confirmed_after_mismatch_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_leading_node(
        fifo_set,
        confirm_result={"k_confirmed_after": 9},
    )
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "k_confirmed_after")


def test_arrived_key_order_disagrees_with_ledger_slice():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    arrived_node = _arrived_node(fifo_set)
    # Only the arrived visit column changes. Counts stay length 1.
    broken_node = dataclasses.replace(
        arrived_node,
        confirmed_arrived_visit_keys=(("lead", 1),),
    )
    broken = _rebuild_with_confirmation(fifo_set, arrived_node=broken_node)
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "confirmed_arrived")


def test_leading_key_order_disagrees_with_ledger_slice():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_leading_node(
        fifo_set,
        confirmed_leading_nonparticipating_visit_keys=(("arr", 1),),
    )
    _assert_builder_error(
        RuntimeError,
        broken,
        candidate,
        rank_state,
        "confirmed_leading_nonparticipating",
    )


def test_decision_window_must_be_leading_prefix_plus_remaining_suffix():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_leading_node(
        fifo_set,
        decision_window_visit_keys=(("buy", 1), ("sell", 1), ("late", 1)),
    )
    _assert_builder_error(
        RuntimeError,
        broken,
        candidate,
        rank_state,
        "decision_window_visit_keys",
    )


def test_partition_3_uses_post_trade_order_not_baseline_scope_order():
    # Baseline trade_scope is seller then buyer.
    # trade_order[:last_buyer_rank] is buyer then seller.
    trade_rank = _trade_rank(
        trade_scope=(("sell", 1), ("buy", 1)),
        trade_order=(("buy", 1), ("sell", 1), ("tail", 1)),
        trade_rank_by_visit_key={
            ("buy", 1): 1,
            ("sell", 1): 2,
            ("tail", 1): 3,
        },
    )
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
        },
        (("buy", 1), ("sell", 1)),
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert [
        visit.visit_key for visit in result.trade_scope_of_this_candidate_visits
    ] == [("buy", 1), ("sell", 1)]
    completed_keys = [visit.visit_key for visit in result.visits_in_binding_order]
    assert ("tail", 1) not in completed_keys


def test_nonparticipating_visit_keeps_a_fixed_trade_scope_slot():
    trade_rank = _trade_rank(
        last_buyer_rank=3,
        nonparticipating_visits_sorted=(("hold", 1),),
        trade_scope=(("sell", 1), ("hold", 1), ("buy", 1)),
        trade_order=(("buy", 1), ("hold", 1), ("sell", 1)),
    )
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("hold", 1): _record("hold", 1, vehicle_id=7, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
        },
        (("sell", 1), ("hold", 1), ("buy", 1)),
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    hold_visit = result.trade_scope_of_this_candidate_visits[1]
    assert hold_visit.visit_key == ("hold", 1)
    assert hold_visit.trade_role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING


def test_trade_scope_set_mismatch_is_runtime_error():
    trade_rank = _trade_rank(
        trade_scope=(("buy", 1), ("other", 1)),
        trade_order=(("buy", 1), ("sell", 1)),
        trade_rank_by_visit_key={
            ("buy", 1): 1,
            ("sell", 1): 2,
            ("other", 1): 3,
        },
    )
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {},
        (("buy", 1), ("sell", 1)),
    )
    _assert_builder_error(RuntimeError, fifo_set, candidate, rank_state, "trade_scope")


def test_trade_scope_duplicate_is_runtime_error():
    fifo_set, candidate, rank_state = _empty_ledger_case(
        _trade_rank(),
        {},
        (("buy", 1), ("sell", 1)),
    )
    broken_rank = _TradeRankWithDuplicateScope(
        concrete_buyer_candidate_set=candidate.general_trade_rank_result.concrete_buyer_candidate_set,
        buyers_sorted=(("buy", 1),),
        sellers_sorted=(("sell", 1),),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(("buy", 1), ("sell", 1)),
        trade_order=(("buy", 1), ("sell", 1)),
        trade_rank_by_visit_key={("buy", 1): 1, ("sell", 1): 2},
    )
    broken_set, broken_candidate = _rebuild_with_trade_rank(fifo_set, broken_rank)
    _assert_builder_error(
        RuntimeError,
        broken_set,
        broken_candidate,
        rank_state,
        "trade_scope",
    )


def test_trade_order_prefix_duplicate_is_runtime_error():
    fifo_set, candidate, rank_state = _empty_ledger_case(
        _trade_rank(),
        {},
        (("buy", 1), ("sell", 1)),
    )
    broken_rank = _TradeRankWithDuplicateOrderPrefix(
        concrete_buyer_candidate_set=candidate.general_trade_rank_result.concrete_buyer_candidate_set,
        buyers_sorted=(("buy", 1),),
        sellers_sorted=(("sell", 1),),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=2,
        trade_scope=(("buy", 1), ("sell", 1)),
        trade_order=(("buy", 1), ("sell", 1)),
        trade_rank_by_visit_key={("buy", 1): 1, ("sell", 1): 2},
    )
    broken_set, broken_candidate = _rebuild_with_trade_rank(fifo_set, broken_rank)
    _assert_builder_error(
        RuntimeError,
        broken_set,
        broken_candidate,
        rank_state,
        "trade_order[:last_buyer_rank]",
    )


def test_trade_role_overlap_is_runtime_error():
    trade_rank = _trade_rank(
        last_buyer_rank=1,
        sellers_sorted=(("buy", 1),),
        trade_scope=(("buy", 1),),
        trade_order=(("buy", 1),),
        trade_rank_by_visit_key={("buy", 1): 1},
    )
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False)},
        (("buy", 1),),
    )
    _assert_builder_error(RuntimeError, fifo_set, candidate, rank_state, "exactly one")


def test_trade_role_missing_is_runtime_error():
    trade_rank = _trade_rank(
        sellers_sorted=(),
        trade_scope=(("buy", 1), ("gap", 1)),
        trade_order=(("buy", 1), ("gap", 1)),
        trade_rank_by_visit_key={("buy", 1): 1, ("gap", 1): 2},
    )
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("gap", 1): _record("gap", 1, vehicle_id=8, route="out", arrived=False),
        },
        (("buy", 1), ("gap", 1)),
    )
    _assert_builder_error(RuntimeError, fifo_set, candidate, rank_state, "('gap', 1)")


def test_partition_4_keeps_n_plus_one_suffix_visit_in_baseline_order():
    # N+1 is not a flag on the current result types. This visit is absent
    # from candidate_visits and from trade_order, and exists only on the
    # remaining decision-window suffix.
    trade_rank = _trade_rank()
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            ("n_plus_one", 1): _record(
                "n_plus_one",
                1,
                vehicle_id=9,
                route="out",
                arrived=False,
            ),
        },
        (("buy", 1), ("sell", 1), ("n_plus_one", 1)),
    )
    candidate_visits = (
        fifo_set.general_trade_rank_set_result
        .concrete_buyer_candidate_set_result
        .inlink_candidate_physical_order_result
        .candidate_visit_set_result
        .node_candidate_set_results[0]
        .candidate_visits
    )
    assert candidate_visits == ()
    assert ("n_plus_one", 1) not in trade_rank.trade_order
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert [
        visit.visit_key for visit in result.outside_trade_scope_inside_k_fixed_visits
    ] == [("n_plus_one", 1)]


def test_partition_4_keeps_p_minus_one_outside_suffix_visit():
    # P-1 outside is also not a flag. This is a different visit from the
    # N+1 example: it stands for a decision-window visit that was not in
    # the P-1 eligible set, and it appears only on the remaining suffix.
    trade_rank = _trade_rank()
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            ("p1_outside", 1): _record(
                "p1_outside",
                1,
                vehicle_id=10,
                route="side",
                arrived=False,
            ),
        },
        (("buy", 1), ("sell", 1), ("p1_outside", 1)),
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    outside_visit = result.outside_trade_scope_inside_k_fixed_visits[0]
    assert outside_visit.visit_key == ("p1_outside", 1)
    assert (
        outside_visit.route_origin
        is OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_TARGET_NODE_ARRIVAL_ROUTE
    )


def test_partition_4_suffix_preserves_baseline_order():
    trade_rank = _trade_rank()
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            ("n_plus_one", 1): _record(
                "n_plus_one",
                1,
                vehicle_id=9,
                route="out",
                arrived=False,
            ),
            ("p1_outside", 1): _record(
                "p1_outside",
                1,
                vehicle_id=10,
                route="side",
                arrived=False,
            ),
        },
        (("buy", 1), ("sell", 1), ("n_plus_one", 1), ("p1_outside", 1)),
    )
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert [
        visit.visit_key for visit in result.outside_trade_scope_inside_k_fixed_visits
    ] == [("n_plus_one", 1), ("p1_outside", 1)]


def test_partition_4_missing_route_is_value_error():
    trade_rank = _trade_rank()
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            ("late", 1): _record("late", 1, vehicle_id=6, route=None, arrived=False),
        },
        (("buy", 1), ("sell", 1), ("late", 1)),
    )
    _assert_builder_error(ValueError, fifo_set, candidate, rank_state, "('late', 1)")


def test_route_origin_enum_has_no_vehicle_id_mode():
    assert [item.value for item in OrderControlTvtMpLocalBindingRouteOrigin] == [
        "rank_ledger_formal_route",
        "snapshot_route_already_decided",
        "baseline_target_node_arrival_route",
    ]


def test_duplicate_visit_inside_partition_4_is_runtime_error():
    trade_rank = _trade_rank()
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {
            ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
            ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            ("late", 1): _record("late", 1, vehicle_id=6, route="out", arrived=False),
        },
        (("buy", 1), ("sell", 1), ("late", 1), ("late", 1)),
    )
    _assert_builder_error(RuntimeError, fifo_set, candidate, rank_state, "('late', 1)")


def test_fifo_failure_is_value_error():
    rank_state = OrderControlTvtNodeRankState("merge")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector({}),
        arrived_keys=(),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=0,
        preserves_fifo=False,
    )
    _assert_builder_error(ValueError, fifo_set, candidate, rank_state, "preserves_inlink_fifo")


def test_candidate_missing_from_fifo_set_is_value_error():
    fifo_set, _candidate, rank_state, _collector = _ready_case()
    outsider = OrderControlTvtMpCandidateFifoInspectionResult(
        general_trade_rank_result=_candidate.general_trade_rank_result,
        preserves_inlink_fifo=True,
    )
    _assert_builder_error(ValueError, fifo_set, outsider, rank_state, "not one of the candidates")


def test_upstream_leading_node_name_mismatch_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _break_leading_node(fifo_set, node_name="other")
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "other")


def test_builder_does_not_touch_another_nodes_rank_ledger():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    other_state = OrderControlTvtNodeRankState("side")
    _confirm_formal(other_state, ("side_visit", 1), "out")
    before_other = other_state.export_state()
    before_target = rank_state.export_state()
    build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
    assert other_state.export_state() == before_other
    assert rank_state.export_state() == before_target


def test_completed_sequence_is_the_four_partitions_with_contiguous_ranks():
    fifo_set, candidate, rank_state, collector = _ready_case()
    before_records = {
        visit_key: dict(record) for visit_key, record in collector.records.items()
    }
    before_window = _leading_node(fifo_set).decision_window_visit_keys
    before_export = rank_state.export_state()
    first = build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
    second = build_tvt_mp_local_binding_rank_sequence(fifo_set, candidate, rank_state)
    assert first == second
    concatenated = (
        first.confirmed_before_this_baseline_visits
        + first.preconfirmed_by_this_baseline_visits
        + first.trade_scope_of_this_candidate_visits
        + first.outside_trade_scope_inside_k_fixed_visits
    )
    assert first.visits_in_binding_order == concatenated
    assert [visit.binding_rank for visit in first.visits_in_binding_order] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert collector.records == before_records
    assert _leading_node(fifo_set).decision_window_visit_keys == before_window
    assert rank_state.export_state() == before_export


def test_last_buyer_rank_past_trade_order_is_value_error():
    trade_rank = _trade_rank(last_buyer_rank=3)
    fifo_set, candidate, rank_state = _empty_ledger_case(
        trade_rank,
        {},
        (("buy", 1), ("sell", 1)),
    )
    _assert_builder_error(ValueError, fifo_set, candidate, rank_state, "last_buyer_rank")


def _fork_result_from_fifo_set(fifo_set):
    leading = _leading_confirmation(fifo_set)
    return leading.arrived_confirmation_result.alignment_fork_result.fork_result


def test_baseline_timestep_T_matches_fork_result():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    fork_result = _fork_result_from_fifo_set(fifo_set)
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert result.baseline_timestep_T == fork_result.baseline_timestep_T
    assert result.baseline_timestep_T == 10
    assert result.baseline_timestep_T != fork_result.final_fork_timestep
    assert "baseline_timestep_T" in {
        field.name for field in dataclasses.fields(OrderControlTvtMpLocalBindingRankSequence)
    }
    second = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert second.baseline_timestep_T == result.baseline_timestep_T
    try:
        result.baseline_timestep_T = 99  # type: ignore[misc]
        raise AssertionError("expected frozen baseline_timestep_T")
    except dataclasses.FrozenInstanceError:
        pass


def test_baseline_timestep_T_is_distinct_from_visit_arrival_and_final_fork():
    rank_state = OrderControlTvtNodeRankState("merge")
    _confirm_formal(rank_state, ("arr", 1), "out")
    fifo_set, candidate, rank_state = _build_chain(
        rank_state=rank_state,
        collector=_Collector(
            {
                ("arr", 1): _record(
                    "arr",
                    1,
                    vehicle_id=2,
                    route="out",
                    arrived=True,
                ),
                ("buy", 1): _record("buy", 1, vehicle_id=4, route="out", arrived=False),
                ("sell", 1): _record("sell", 1, vehicle_id=5, route="side", arrived=False),
            }
        ),
        arrived_keys=(("arr", 1),),
        leading_keys=(),
        remaining_keys=(("buy", 1), ("sell", 1)),
        trade_rank_result=_trade_rank(),
        k_confirmed_before=0,
        baseline_timestep_T=7,
    )
    fork_result = _fork_result_from_fifo_set(fifo_set)
    result = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate,
        rank_state,
    )
    assert result.baseline_timestep_T == 7
    assert fork_result.final_fork_timestep == 13
    assert result.baseline_timestep_T != fork_result.final_fork_timestep
    assert result.preconfirmed_by_this_baseline_visits[0].baseline_arrival_timestep == 10


def test_fork_baseline_timestep_T_bool_is_runtime_error():
    fifo_set, candidate, rank_state, collector = _ready_case()
    broken = _rebuild_with_fork_result(fifo_set, baseline_timestep_T=True)
    before_records = dict(collector.records)
    before_window = _leading_node(fifo_set).decision_window_visit_keys
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "baseline_timestep_T")
    assert collector.records == before_records
    assert _leading_node(fifo_set).decision_window_visit_keys == before_window


def test_fork_baseline_timestep_T_non_int_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _rebuild_with_fork_result(fifo_set, baseline_timestep_T=10.0)
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "baseline_timestep_T")


def test_fork_baseline_timestep_T_negative_is_runtime_error():
    fifo_set, candidate, rank_state, _collector = _ready_case()
    broken = _rebuild_with_fork_result(fifo_set, baseline_timestep_T=-1)
    _assert_builder_error(RuntimeError, broken, candidate, rank_state, "baseline_timestep_T")


TESTS = (
    test_public_types_are_frozen_and_importable,
    test_four_partitions_orders_roles_and_k_values,
    test_partition_4_is_empty_when_last_buyer_covers_the_window,
    test_duplicate_visit_across_partitions_is_runtime_error,
    test_missing_partition_3_route_is_value_error_without_ledger_write,
    test_old_none_formal_route_outside_partition_1_does_not_stop_build,
    test_missing_partition_2_formal_route_is_value_error,
    test_rank_state_node_name_mismatch_is_value_error,
    test_builder_does_not_call_confirmation_apis,
    test_partition_1_missing_both_routes_is_runtime_error,
    test_snapshot_route_does_not_overwrite_ledger_formal_route,
    test_partition_1_prefix_longer_than_ledger_is_runtime_error,
    test_partition_2_arrived_then_leading_matches_ledger_order,
    test_arrived_newly_confirmed_count_mismatch_is_runtime_error,
    test_arrived_k_confirmed_after_mismatch_is_runtime_error,
    test_arrived_confirm_count_rejects_bool,
    test_leading_newly_confirmed_count_mismatch_is_runtime_error,
    test_leading_k_confirmed_before_does_not_continue_arrived_end,
    test_leading_k_confirmed_after_mismatch_is_runtime_error,
    test_arrived_key_order_disagrees_with_ledger_slice,
    test_leading_key_order_disagrees_with_ledger_slice,
    test_decision_window_must_be_leading_prefix_plus_remaining_suffix,
    test_partition_3_uses_post_trade_order_not_baseline_scope_order,
    test_nonparticipating_visit_keeps_a_fixed_trade_scope_slot,
    test_trade_scope_set_mismatch_is_runtime_error,
    test_trade_scope_duplicate_is_runtime_error,
    test_trade_order_prefix_duplicate_is_runtime_error,
    test_trade_role_overlap_is_runtime_error,
    test_trade_role_missing_is_runtime_error,
    test_partition_4_keeps_n_plus_one_suffix_visit_in_baseline_order,
    test_partition_4_keeps_p_minus_one_outside_suffix_visit,
    test_partition_4_suffix_preserves_baseline_order,
    test_partition_4_missing_route_is_value_error,
    test_route_origin_enum_has_no_vehicle_id_mode,
    test_duplicate_visit_inside_partition_4_is_runtime_error,
    test_fifo_failure_is_value_error,
    test_candidate_missing_from_fifo_set_is_value_error,
    test_upstream_leading_node_name_mismatch_is_runtime_error,
    test_builder_does_not_touch_another_nodes_rank_ledger,
    test_completed_sequence_is_the_four_partitions_with_contiguous_ranks,
    test_last_buyer_rank_past_trade_order_is_value_error,
    test_baseline_timestep_T_matches_fork_result,
    test_baseline_timestep_T_is_distinct_from_visit_arrival_and_final_fork,
    test_fork_baseline_timestep_T_bool_is_runtime_error,
    test_fork_baseline_timestep_T_non_int_is_runtime_error,
    test_fork_baseline_timestep_T_negative_is_runtime_error,
)


if __name__ == "__main__":
    for test_function in TESTS:
        test_function()
    print(
        "local binding rank sequence tests passed "
        f"({len(TESTS)} tests)."
    )
