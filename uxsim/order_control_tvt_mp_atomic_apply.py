"""
TVT-MP atomic apply.

One validated final-consistency result is one apply. Prepare every target
Node ledger and every buyer or seller Vehicle update before the first live
assignment. Commit only if that prepare finishes. A failure leaves every
rank ledger, cumulative amount, and order-exchange log unchanged.

This module does not rerun validation, ranks, payments, or virtual
calculations, and it does not build an actual-outcome record.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionSetResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtMpSellerEconomicRecord,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpFifoInspectionSetResult,
)
from uxsim.order_control_tvt_mp_final_consistency_validation import (
    OrderControlTvtMpFinalConsistencyValidationSetResult,
)
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankSetResult,
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalRankVisitRecord,
    OrderControlTvtNodeMpFinalRankResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtMpGeneralTradeRankSetResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpBuyerPaymentRecord,
    OrderControlTvtMpPaymentAndCompensationSetResult,
    OrderControlTvtMpSellerCompensationRecord,
    OrderControlTvtNodeMpPaymentAndCompensationResult,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)
from uxsim.uxsim import Vehicle, World


class OrderControlTvtMpTradeEstablishmentRole(Enum):
    """Role stored on one establishment record. Buyer or seller only."""

    BUYER = "buyer"
    SELLER = "seller"


@dataclass(frozen=True)
class OrderControlTvtMpTradeEstablishmentLogRecord:
    """
    One buyer or seller row written when a TVT trade is established.

    The row is the state at the decision, not an actual passage. It does not
    keep a live Vehicle, Node, World, Link, or rank ledger.
    """

    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    trade_role: OrderControlTvtMpTradeEstablishmentRole
    baseline_local_rank: int
    post_trade_local_rank: int
    ledger_assigned_rank: int
    rank_change: int
    formal_route_next_link_name: str
    baseline_passage_timestep: int
    candidate_passage_timestep: int
    payment_paid_in_this_transaction: int | float
    payment_received_in_this_transaction: int | float
    declared_vot_per_second: float
    true_vot_per_second: float


@dataclass(frozen=True)
class OrderControlTvtMpAtomicApplySetResult:
    """Successful apply of one validation result. The result is not copied."""

    final_consistency_validation_set_result: (
        OrderControlTvtMpFinalConsistencyValidationSetResult
    )


@dataclass
class _SavedApplyColumns:
    """Aligned saved columns reached from one validation result. Same objects."""

    validation_result: OrderControlTvtMpFinalConsistencyValidationSetResult
    final_rank_nodes: tuple[OrderControlTvtNodeMpFinalRankResult, ...]
    payment_nodes: tuple[OrderControlTvtNodeMpPaymentAndCompensationResult, ...]
    trade_rank_nodes: tuple
    candidate_visit_nodes: tuple[OrderControlTvtNodeCandidateVisitSetResult, ...]
    fork_result: OrderControlBaselineForkResult


@dataclass
class _PreparedVehicleUpdate:
    """New cumulative amounts and a new log list. Not yet assigned."""

    vehicle: Vehicle
    updated_payment_paid: int | float
    updated_payment_received: int | float
    updated_order_exchange_log: list


@dataclass
class _PreparedNodeLedgerCommit:
    """One Node whose prepared ledger should be assigned during commit."""

    rank_state: OrderControlTvtNodeRankState
    prepared: object


def apply_tvt_mp_validated_result(
    final_consistency_validation_set_result,
    real_W,
    rank_states_by_node_name,
) -> OrderControlTvtMpAtomicApplySetResult:
    """
    Apply one validated all-Node result, or change nothing.

    Positional arguments only. There is no per-Node or per-Vehicle public
    apply. Prepare builds every ledger replacement and every Vehicle update
    first. Commit assigns those prepared values and does not inspect them.
    """
    validation_result = _require_validation_result(
        final_consistency_validation_set_result,
    )
    real_world = _require_real_world(real_W)
    rank_states = _require_rank_state_mapping(rank_states_by_node_name)
    saved_columns = _saved_columns_from_validation_result(validation_result)
    decision_timestep = _require_decision_timestep(saved_columns, real_world)

    _reject_duplicate_money_vehicle_names(saved_columns)

    node_commits: list[_PreparedNodeLedgerCommit] = []
    vehicle_updates: list[_PreparedVehicleUpdate] = []
    node_index = 0
    for final_rank_node in saved_columns.final_rank_nodes:
        node_commit, node_vehicle_updates = _prepare_one_node(
            saved_columns=saved_columns,
            node_index=node_index,
            final_rank_node=final_rank_node,
            real_world=real_world,
            rank_states=rank_states,
            decision_timestep=decision_timestep,
        )
        if node_commit is not None:
            node_commits.append(node_commit)
        for vehicle_update in node_vehicle_updates:
            vehicle_updates.append(vehicle_update)
        node_index = node_index + 1

    # The success object only points at the input validation result.
    # It is built before commit and returned only after commit finishes.
    apply_result = OrderControlTvtMpAtomicApplySetResult(
        final_consistency_validation_set_result=validation_result,
    )

    # Commit assigns prepared state only. It does not search, check, or add.
    for node_commit in node_commits:
        node_commit.rank_state._commit_prepared_formal_route_confirmation(
            node_commit.prepared,
        )
    for vehicle_update in vehicle_updates:
        vehicle_update.vehicle.payment_paid = vehicle_update.updated_payment_paid
    for vehicle_update in vehicle_updates:
        vehicle_update.vehicle.payment_received = (
            vehicle_update.updated_payment_received
        )
    for vehicle_update in vehicle_updates:
        vehicle_update.vehicle.order_exchange_log = (
            vehicle_update.updated_order_exchange_log
        )
    return apply_result


def _require_validation_result(
    value: object,
) -> OrderControlTvtMpFinalConsistencyValidationSetResult:
    if not isinstance(value, OrderControlTvtMpFinalConsistencyValidationSetResult):
        raise ValueError(
            "final_consistency_validation_set_result must be "
            "OrderControlTvtMpFinalConsistencyValidationSetResult; got "
            f"type {type(value).__name__}."
        )
    return value


def _require_real_world(value: object) -> World:
    if not isinstance(value, World):
        raise ValueError(
            "real_W must be a World; got type "
            f"{type(value).__name__}."
        )
    return value


def _require_rank_state_mapping(
    value: object,
) -> Mapping[str, OrderControlTvtNodeRankState]:
    if not isinstance(value, Mapping):
        raise ValueError(
            "rank_states_by_node_name must be a mapping from node name to "
            "OrderControlTvtNodeRankState; got type "
            f"{type(value).__name__}."
        )
    for node_name in value:
        rank_state = value[node_name]
        if not isinstance(rank_state, OrderControlTvtNodeRankState):
            raise ValueError(
                "rank_states_by_node_name values must be "
                "OrderControlTvtNodeRankState; got type "
                f"{type(rank_state).__name__} for key {node_name!r}."
            )
    return value


def _saved_columns_from_validation_result(
    validation_result: OrderControlTvtMpFinalConsistencyValidationSetResult,
) -> _SavedApplyColumns:
    final_rank_set = validation_result.final_rank_set_result
    if not isinstance(final_rank_set, OrderControlTvtMpFinalRankSetResult):
        raise RuntimeError(
            "final_rank_set_result must be OrderControlTvtMpFinalRankSetResult; "
            f"got type {type(final_rank_set).__name__}."
        )
    final_rank_nodes = _require_tuple_column(
        final_rank_set.node_final_rank_results,
        "node_final_rank_results",
    )
    payment_set = final_rank_set.payment_and_compensation_set_result
    if not isinstance(payment_set, OrderControlTvtMpPaymentAndCompensationSetResult):
        raise RuntimeError(
            "payment_and_compensation_set_result must be "
            "OrderControlTvtMpPaymentAndCompensationSetResult; got "
            f"type {type(payment_set).__name__}."
        )
    payment_nodes = _require_tuple_column(
        payment_set.node_payment_and_compensation_results,
        "node_payment_and_compensation_results",
    )
    selection_set = payment_set.candidate_selection_set_result
    if not isinstance(selection_set, OrderControlTvtMpCandidateSelectionSetResult):
        raise RuntimeError(
            "candidate_selection_set_result must be "
            "OrderControlTvtMpCandidateSelectionSetResult; got "
            f"type {type(selection_set).__name__}."
        )
    economic_set = selection_set.economic_evaluation_set_result
    if not isinstance(economic_set, OrderControlTvtMpEconomicEvaluationSetResult):
        raise RuntimeError(
            "economic_evaluation_set_result must be "
            "OrderControlTvtMpEconomicEvaluationSetResult; got "
            f"type {type(economic_set).__name__}."
        )
    local_set = economic_set.local_virtual_calculation_set_result
    if not isinstance(local_set, OrderControlTvtMpLocalVirtualCalculationSetResult):
        raise RuntimeError(
            "local_virtual_calculation_set_result must be "
            "OrderControlTvtMpLocalVirtualCalculationSetResult; got "
            f"type {type(local_set).__name__}."
        )
    fifo_set = local_set.fifo_inspection_set_result
    if not isinstance(fifo_set, OrderControlTvtMpFifoInspectionSetResult):
        raise RuntimeError(
            "fifo_inspection_set_result must be "
            "OrderControlTvtMpFifoInspectionSetResult; got "
            f"type {type(fifo_set).__name__}."
        )
    trade_rank_set = fifo_set.general_trade_rank_set_result
    if not isinstance(trade_rank_set, OrderControlTvtMpGeneralTradeRankSetResult):
        raise RuntimeError(
            "general_trade_rank_set_result must be "
            "OrderControlTvtMpGeneralTradeRankSetResult; got "
            f"type {type(trade_rank_set).__name__}."
        )
    trade_rank_nodes = _require_tuple_column(
        trade_rank_set.node_trade_rank_results,
        "node_trade_rank_results",
    )
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    if not isinstance(concrete_set, OrderControlTvtMpConcreteBuyerCandidateSetResult):
        raise RuntimeError(
            "concrete_buyer_candidate_set_result must be "
            "OrderControlTvtMpConcreteBuyerCandidateSetResult; got "
            f"type {type(concrete_set).__name__}."
        )
    inlink_set = concrete_set.inlink_candidate_physical_order_result
    if not isinstance(
        inlink_set,
        OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    ):
        raise RuntimeError(
            "inlink_candidate_physical_order_result must be "
            "OrderControlTvtInlinkCandidatePhysicalOrderSetResult; got "
            f"type {type(inlink_set).__name__}."
        )
    candidate_visit_set = inlink_set.candidate_visit_set_result
    if not isinstance(candidate_visit_set, OrderControlTvtCandidateVisitSetResult):
        raise RuntimeError(
            "candidate_visit_set_result must be "
            "OrderControlTvtCandidateVisitSetResult; got "
            f"type {type(candidate_visit_set).__name__}."
        )
    candidate_visit_nodes = _require_tuple_column(
        candidate_visit_set.node_candidate_set_results,
        "node_candidate_set_results",
    )
    fork_result = _fork_result_from_candidate_visit_set(candidate_visit_set)

    expected_count = len(final_rank_nodes)
    named_columns = (
        ("payment", payment_nodes),
        ("trade rank", trade_rank_nodes),
        ("candidate visit", candidate_visit_nodes),
    )
    for column_label, column in named_columns:
        if len(column) != expected_count:
            raise RuntimeError(
                f"{column_label} Node count {len(column)} does not match "
                f"final rank Node count {expected_count}."
            )

    seen_node_names: list[str] = []
    node_index = 0
    for final_rank_node in final_rank_nodes:
        node_name = _require_node_name(
            final_rank_node.node_name,
            "final rank node_name",
        )
        if node_name in seen_node_names:
            raise RuntimeError(
                f"Node name {node_name!r} is duplicated in the final rank column."
            )
        seen_node_names.append(node_name)
        _require_same_node_name(
            node_name,
            payment_nodes[node_index].node_name,
            "payment",
            node_index,
        )
        _require_same_node_name(
            node_name,
            trade_rank_nodes[node_index].node_name,
            "trade rank",
            node_index,
        )
        _require_same_node_name(
            node_name,
            candidate_visit_nodes[node_index].node_name,
            "candidate visit",
            node_index,
        )
        node_index = node_index + 1

    return _SavedApplyColumns(
        validation_result=validation_result,
        final_rank_nodes=final_rank_nodes,
        payment_nodes=payment_nodes,
        trade_rank_nodes=trade_rank_nodes,
        candidate_visit_nodes=candidate_visit_nodes,
        fork_result=fork_result,
    )


def _fork_result_from_candidate_visit_set(
    candidate_visit_set: OrderControlTvtCandidateVisitSetResult,
) -> OrderControlBaselineForkResult:
    right_of_entry_set = candidate_visit_set.right_of_entry_selection_result
    leading_set = right_of_entry_set.leading_confirmation_result
    arrived_set = leading_set.arrived_confirmation_result
    alignment_fork = arrived_set.alignment_fork_result
    if not isinstance(alignment_fork, OrderControlTvtBaselineForkAlignmentResult):
        raise RuntimeError(
            "alignment_fork_result must be "
            "OrderControlTvtBaselineForkAlignmentResult; got "
            f"type {type(alignment_fork).__name__}."
        )
    fork_result = alignment_fork.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError(
            "fork_result must be OrderControlBaselineForkResult; got "
            f"type {type(fork_result).__name__}."
        )
    return fork_result


def _require_decision_timestep(
    saved_columns: _SavedApplyColumns,
    real_world: World,
) -> int:
    """
    The decision timestep is the saved baseline start T.

    It is the real World time at which baseline calculation started and at
    which this TVT decision is established. It is not a virtual passage time.
    Empty-Node results still require this match.
    """
    baseline_timestep_T = saved_columns.fork_result.baseline_timestep_T
    if type(baseline_timestep_T) is not int:
        raise RuntimeError(
            "fork_result.baseline_timestep_T must be a Python int, not bool; "
            f"got type {type(baseline_timestep_T).__name__} "
            f"with value {baseline_timestep_T!r}."
        )
    if real_world.T != baseline_timestep_T:
        raise RuntimeError(
            "real_W.T must equal the saved baseline_timestep_T before any "
            f"ledger write; real_W.T={real_world.T!r}, "
            f"baseline_timestep_T={baseline_timestep_T!r}."
        )

    node_index = 0
    for final_rank_node in saved_columns.final_rank_nodes:
        if (
            final_rank_node.final_rank_status
            is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS
        ):
            _require_selected_baseline_timestep(
                final_rank_node,
                baseline_timestep_T,
            )
        node_index = node_index + 1
    return baseline_timestep_T


def _require_selected_baseline_timestep(
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    baseline_timestep_T: int,
) -> None:
    selected = _require_selected_candidate(final_rank_node)
    local_result = _require_local_result(selected, final_rank_node.node_name)
    local_timestep = local_result.baseline_timestep_T
    binding_timestep = local_result.binding_rank_sequence.baseline_timestep_T
    if type(local_timestep) is not int or local_timestep != baseline_timestep_T:
        raise RuntimeError(
            f"Node {final_rank_node.node_name!r}: selected local "
            f"baseline_timestep_T {local_timestep!r} does not match fork "
            f"baseline_timestep_T {baseline_timestep_T!r}."
        )
    if type(binding_timestep) is not int or binding_timestep != baseline_timestep_T:
        raise RuntimeError(
            f"Node {final_rank_node.node_name!r}: selected binding "
            f"baseline_timestep_T {binding_timestep!r} does not match fork "
            f"baseline_timestep_T {baseline_timestep_T!r}."
        )


def _reject_duplicate_money_vehicle_names(saved_columns: _SavedApplyColumns) -> None:
    """One validation result may mention each vehicle in at most one money row."""
    seen_vehicle_names: list[str] = []
    node_index = 0
    for final_rank_node in saved_columns.final_rank_nodes:
        payment_node = saved_columns.payment_nodes[node_index]
        if (
            final_rank_node.final_rank_status
            is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS
        ):
            for buyer_record in payment_node.buyer_payment_records:
                _note_money_vehicle_name(
                    seen_vehicle_names,
                    buyer_record.vehicle_name,
                    final_rank_node.node_name,
                )
            for seller_record in payment_node.seller_compensation_records:
                _note_money_vehicle_name(
                    seen_vehicle_names,
                    seller_record.vehicle_name,
                    final_rank_node.node_name,
                )
        node_index = node_index + 1


def _note_money_vehicle_name(
    seen_vehicle_names: list[str],
    vehicle_name: object,
    node_name: str,
) -> None:
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: money record vehicle_name must be a "
            f"non-empty str; got {vehicle_name!r}."
        )
    if vehicle_name in seen_vehicle_names:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r} appears in more than one buyer or "
            "seller money record in this validation result. Current atomic "
            "apply does not combine those records."
        )
    seen_vehicle_names.append(vehicle_name)


def _prepare_one_node(
    *,
    saved_columns: _SavedApplyColumns,
    node_index: int,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    real_world: World,
    rank_states: Mapping[str, OrderControlTvtNodeRankState],
    decision_timestep: int,
) -> tuple[_PreparedNodeLedgerCommit | None, list[_PreparedVehicleUpdate]]:
    node_name = final_rank_node.node_name
    rank_state = _require_rank_state_for_node(rank_states, node_name)
    # Existence is required even when this Node confirms no visits.
    _outlink_names_at_target_node(real_world, node_name)

    status = final_rank_node.final_rank_status
    payment_node = saved_columns.payment_nodes[node_index]
    _require_status_and_money_agree(final_rank_node, payment_node)

    if status is OrderControlTvtMpFinalRankStatus.NO_VISITS_TO_CONFIRM:
        if len(final_rank_node.final_rank_visits) != 0:
            raise RuntimeError(
                f"Node {node_name!r}: NO_VISITS_TO_CONFIRM has a non-empty "
                "final rank column."
            )
        return None, []

    visit_pairs, k_confirmed_before = _require_final_rank_column_for_ledger(
        final_rank_node,
        rank_state,
        real_world,
    )
    if len(visit_pairs) == 0:
        # A selected Node with money rows must still be checked. An empty
        # fallback or no-visit column has nothing to commit.
        if status is not OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
            return None, []
        return None, _prepare_selected_vehicle_updates(
            saved_columns=saved_columns,
            node_index=node_index,
            final_rank_node=final_rank_node,
            payment_node=payment_node,
            real_world=real_world,
            decision_timestep=decision_timestep,
            k_confirmed_before=k_confirmed_before,
        )

    outlink_names = _outlink_names_at_target_node(real_world, node_name)
    try:
        prepared_ledger = rank_state._prepare_formal_route_confirmation(
            visit_pairs,
            outlink_names,
        )
    except ValueError as error:
        raise RuntimeError(
            f"Node {node_name!r}: rank-ledger prepare rejected the final "
            f"rank column. {error}"
        ) from error

    vehicle_updates: list[_PreparedVehicleUpdate] = []
    if status is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
        vehicle_updates = _prepare_selected_vehicle_updates(
            saved_columns=saved_columns,
            node_index=node_index,
            final_rank_node=final_rank_node,
            payment_node=payment_node,
            real_world=real_world,
            decision_timestep=decision_timestep,
            k_confirmed_before=k_confirmed_before,
        )

    node_commit = _PreparedNodeLedgerCommit(
        rank_state=rank_state,
        prepared=prepared_ledger,
    )
    return node_commit, vehicle_updates


def _require_status_and_money_agree(
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
) -> None:
    node_name = final_rank_node.node_name
    status = final_rank_node.final_rank_status
    selected = final_rank_node.selected_candidate_economic_result
    buyer_count = len(payment_node.buyer_payment_records)
    seller_count = len(payment_node.seller_compensation_records)
    if status is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
        if selected is None:
            raise RuntimeError(
                f"Node {node_name!r}: SELECTED_CANDIDATE_RANKS requires a "
                "selected candidate."
            )
        if payment_node.selected_candidate_economic_result is not selected:
            raise RuntimeError(
                f"Node {node_name!r}: payment selected candidate is not the "
                "same object as the final rank selected candidate."
            )
        return
    if selected is not None or buyer_count != 0 or seller_count != 0:
        raise RuntimeError(
            f"Node {node_name!r}: status {status!r} must not carry a selected "
            "candidate or money records."
        )


def _require_rank_state_for_node(
    rank_states: Mapping[str, OrderControlTvtNodeRankState],
    node_name: str,
) -> OrderControlTvtNodeRankState:
    if node_name not in rank_states:
        raise RuntimeError(
            f"Node {node_name!r} is missing from rank_states_by_node_name. "
            "An empty Node is not an absent rank ledger."
        )
    rank_state = rank_states[node_name]
    if rank_state.node_name != node_name:
        raise RuntimeError(
            f"rank_states_by_node_name[{node_name!r}] belongs to Node "
            f"{rank_state.node_name!r}."
        )
    return rank_state


def _outlink_names_at_target_node(real_world: World, node_name: str) -> frozenset[str]:
    """Link.name values on node.outlinks.values(), not the mapping keys."""
    try:
        target_node = real_world.get_node(node_name)
    except Exception as error:
        raise RuntimeError(
            f"Node {node_name!r} is not registered in the real World."
        ) from error
    if target_node is None:
        raise RuntimeError(
            f"Node {node_name!r} is not registered in the real World."
        )
    outlink_names: list[str] = []
    for outlink in target_node.outlinks.values():
        outlink_name = outlink.name
        if not isinstance(outlink_name, str) or outlink_name == "":
            raise RuntimeError(
                f"Node {node_name!r} has an outlink without a non-empty name."
            )
        outlink_names.append(outlink_name)
    return frozenset(outlink_names)


def _require_final_rank_column_for_ledger(
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    rank_state: OrderControlTvtNodeRankState,
    real_world: World,
) -> tuple[list[tuple[OrderControlTvtVisitKey, str]], int]:
    node_name = final_rank_node.node_name
    outlink_names = _outlink_names_at_target_node(real_world, node_name)
    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    visit_pairs: list[tuple[OrderControlTvtVisitKey, str]] = []
    position = 0
    for visit_record in final_rank_node.final_rank_visits:
        position = position + 1
        visit_key = _require_saved_visit_key(
            visit_record.visit_key,
            f"Node {node_name!r} final rank position {position}",
        )
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: final rank VisitKey {visit_key!r} "
                "is duplicated."
            )
        seen_visit_keys.append(visit_key)
        if type(visit_record.final_local_rank) is not int:
            raise RuntimeError(
                f"Node {node_name!r}: final_local_rank for {visit_key!r} "
                "must be a Python int, not bool."
            )
        if visit_record.final_local_rank != position:
            raise RuntimeError(
                f"Node {node_name!r}: final_local_rank "
                f"{visit_record.final_local_rank!r} at position {position} "
                "is not the 1-based index in the final rank column. "
                "final_local_rank is not an absolute ledger rank."
            )
        route_name = visit_record.formal_route_next_link_name
        if not isinstance(route_name, str) or route_name == "":
            raise RuntimeError(
                f"Node {node_name!r}: formal route for {visit_key!r} must be "
                f"a non-empty str; got {route_name!r}."
            )
        if route_name not in outlink_names:
            raise RuntimeError(
                f"Node {node_name!r}: formal route {route_name!r} for "
                f"{visit_key!r} is not a current outlink name."
            )
        if rank_state.is_confirmed(visit_key):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is already "
                "confirmed."
            )
        if not rank_state.is_undetermined(visit_key):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is not "
                "registered as undetermined."
            )
        visit_pairs.append((visit_key, route_name))
    k_confirmed_before = rank_state.k_confirmed()
    return visit_pairs, k_confirmed_before


def _prepare_selected_vehicle_updates(
    *,
    saved_columns: _SavedApplyColumns,
    node_index: int,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    real_world: World,
    decision_timestep: int,
    k_confirmed_before: int,
) -> list[_PreparedVehicleUpdate]:
    node_name = final_rank_node.node_name
    selected = _require_selected_candidate(final_rank_node)
    local_result = _require_local_result(selected, node_name)
    buyers_sorted = _require_buyers_sorted(local_result, node_name)
    trade_rank_result = _matching_trade_rank_result(
        saved_columns.trade_rank_nodes[node_index],
        buyers_sorted,
        node_name,
    )
    candidate_visit_node = saved_columns.candidate_visit_nodes[node_index]
    vehicle_updates: list[_PreparedVehicleUpdate] = []

    for buyer_record in payment_node.buyer_payment_records:
        vehicle_updates.append(
            _prepare_one_money_record(
                real_world=real_world,
                node_name=node_name,
                decision_timestep=decision_timestep,
                buyers_sorted=buyers_sorted,
                trade_role=OrderControlTvtMpTradeEstablishmentRole.BUYER,
                binding_role=OrderControlTvtMpLocalBindingTradeRole.BUYER,
                visit_key=buyer_record.visit_key,
                vehicle_name=buyer_record.vehicle_name,
                paid_amount=buyer_record.payment_P_b,
                received_amount=0,
                add_to_paid=True,
                economic_records=selected.buyer_economic_records,
                final_rank_visits=final_rank_node.final_rank_visits,
                candidate_visits=candidate_visit_node.candidate_visits,
                trade_rank_result=trade_rank_result,
                binding_visits=(
                    local_result.binding_rank_sequence
                    .trade_scope_of_this_candidate_visits
                ),
                k_confirmed_before=k_confirmed_before,
            )
        )
    for seller_record in payment_node.seller_compensation_records:
        vehicle_updates.append(
            _prepare_one_money_record(
                real_world=real_world,
                node_name=node_name,
                decision_timestep=decision_timestep,
                buyers_sorted=buyers_sorted,
                trade_role=OrderControlTvtMpTradeEstablishmentRole.SELLER,
                binding_role=OrderControlTvtMpLocalBindingTradeRole.SELLER,
                visit_key=seller_record.visit_key,
                vehicle_name=seller_record.vehicle_name,
                paid_amount=0,
                received_amount=seller_record.compensation_amount,
                add_to_paid=False,
                economic_records=selected.seller_economic_records,
                final_rank_visits=final_rank_node.final_rank_visits,
                candidate_visits=candidate_visit_node.candidate_visits,
                trade_rank_result=trade_rank_result,
                binding_visits=(
                    local_result.binding_rank_sequence
                    .trade_scope_of_this_candidate_visits
                ),
                k_confirmed_before=k_confirmed_before,
            )
        )
    return vehicle_updates


def _prepare_one_money_record(
    *,
    real_world: World,
    node_name: str,
    decision_timestep: int,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    trade_role: OrderControlTvtMpTradeEstablishmentRole,
    binding_role: OrderControlTvtMpLocalBindingTradeRole,
    visit_key: object,
    vehicle_name: object,
    paid_amount: object,
    received_amount: object,
    add_to_paid: bool,
    economic_records: tuple,
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...],
    candidate_visits: tuple,
    trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
    binding_visits: tuple,
    k_confirmed_before: int,
) -> _PreparedVehicleUpdate:
    saved_visit_key = _require_saved_visit_key(
        visit_key,
        f"Node {node_name!r} money record",
    )
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: money record vehicle_name must be a "
            f"non-empty str; got {vehicle_name!r}."
        )
    if saved_visit_key[0] != vehicle_name:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {saved_visit_key!r} does not "
            f"start with vehicle_name {vehicle_name!r}."
        )
    _require_binding_role(
        binding_visits,
        saved_visit_key,
        binding_role,
        node_name,
    )
    economic_record = _matching_economic_record(
        economic_records,
        saved_visit_key,
        vehicle_name,
        node_name,
    )
    final_rank_visit = _matching_final_rank_visit(
        final_rank_visits,
        saved_visit_key,
        node_name,
    )
    baseline_local_rank = _baseline_local_rank(
        candidate_visits,
        saved_visit_key,
        node_name,
    )
    post_trade_local_rank = _post_trade_local_rank(
        trade_rank_result,
        saved_visit_key,
        node_name,
    )
    # Absolute ledger rank uses the confirmed count from before this apply.
    # final_local_rank is only the 1-based index in this final rank column.
    ledger_assigned_rank = k_confirmed_before + final_rank_visit.final_local_rank
    rank_change = baseline_local_rank - post_trade_local_rank
    checked_paid_amount = _require_non_negative_finite_number(
        paid_amount,
        f"Node {node_name!r} payment amount for {saved_visit_key!r}",
    )
    checked_received_amount = _require_non_negative_finite_number(
        received_amount,
        f"Node {node_name!r} compensation amount for {saved_visit_key!r}",
    )
    vehicle = _require_live_vehicle(real_world, vehicle_name)
    current_paid = _require_live_money(
        vehicle.payment_paid,
        vehicle_name,
        "payment_paid",
    )
    current_received = _require_live_money(
        vehicle.payment_received,
        vehicle_name,
        "payment_received",
    )
    if add_to_paid:
        updated_paid = current_paid + checked_paid_amount
        updated_received = current_received
    else:
        updated_paid = current_paid
        updated_received = current_received + checked_received_amount
    _require_updated_money(updated_paid, vehicle_name, "payment_paid")
    _require_updated_money(updated_received, vehicle_name, "payment_received")
    if not isinstance(vehicle.order_exchange_log, list):
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: order_exchange_log must be a list; "
            f"got type {type(vehicle.order_exchange_log).__name__}."
        )
    true_vot_per_second = _require_true_vot(vehicle.vot_true, vehicle_name)
    declared_vot_per_second = _require_declared_vot(
        economic_record.declared_vot_per_second,
        vehicle_name,
    )
    baseline_passage_timestep = _require_passage_timestep(
        economic_record.baseline_passage_timestep,
        vehicle_name,
        "baseline_passage_timestep",
    )
    candidate_passage_timestep = _require_passage_timestep(
        economic_record.candidate_passage_timestep,
        vehicle_name,
        "candidate_passage_timestep",
    )
    establishment_record = OrderControlTvtMpTradeEstablishmentLogRecord(
        tvt_decision_timestep=decision_timestep,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        visit_key=saved_visit_key,
        vehicle_name=vehicle_name,
        trade_role=trade_role,
        baseline_local_rank=baseline_local_rank,
        post_trade_local_rank=post_trade_local_rank,
        ledger_assigned_rank=ledger_assigned_rank,
        rank_change=rank_change,
        formal_route_next_link_name=final_rank_visit.formal_route_next_link_name,
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        payment_paid_in_this_transaction=checked_paid_amount,
        payment_received_in_this_transaction=checked_received_amount,
        declared_vot_per_second=declared_vot_per_second,
        true_vot_per_second=true_vot_per_second,
    )
    # Copy first. The live list is not appended to, during prepare or commit.
    updated_log = list(vehicle.order_exchange_log)
    updated_log.append(establishment_record)
    return _PreparedVehicleUpdate(
        vehicle=vehicle,
        updated_payment_paid=updated_paid,
        updated_payment_received=updated_received,
        updated_order_exchange_log=updated_log,
    )


def _require_selected_candidate(
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
) -> OrderControlTvtMpCandidateEconomicEvaluationResult:
    selected = final_rank_node.selected_candidate_economic_result
    if not isinstance(selected, OrderControlTvtMpCandidateEconomicEvaluationResult):
        raise RuntimeError(
            f"Node {final_rank_node.node_name!r}: selected candidate must be "
            "OrderControlTvtMpCandidateEconomicEvaluationResult; got "
            f"type {type(selected).__name__}."
        )
    return selected


def _require_local_result(
    selected: OrderControlTvtMpCandidateEconomicEvaluationResult,
    node_name: str,
) -> OrderControlTvtMpCandidateLocalVirtualCalculationResult:
    local_result = selected.candidate_local_virtual_calculation_result
    if not isinstance(
        local_result,
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: selected local result must be "
            "OrderControlTvtMpCandidateLocalVirtualCalculationResult; got "
            f"type {type(local_result).__name__}."
        )
    return local_result


def _require_buyers_sorted(
    local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    node_name: str,
) -> tuple[OrderControlTvtVisitKey, ...]:
    buyers_sorted = local_result.concrete_buyer_candidate_set.buyers_sorted
    if not isinstance(buyers_sorted, tuple) or len(buyers_sorted) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: buyers_sorted must be a non-empty tuple."
        )
    validated_buyers: list[OrderControlTvtVisitKey] = []
    for visit_key in buyers_sorted:
        validated_buyers.append(
            _require_saved_visit_key(
                visit_key,
                f"Node {node_name!r} buyers_sorted",
            )
        )
    return tuple(validated_buyers)


def _matching_trade_rank_result(
    trade_rank_node: object,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    node_name: str,
) -> OrderControlTvtMpGeneralTradeRankResult:
    matches: list[OrderControlTvtMpGeneralTradeRankResult] = []
    for trade_rank_result in trade_rank_node.candidate_trade_rank_results:
        if not isinstance(
            trade_rank_result,
            OrderControlTvtMpGeneralTradeRankResult,
        ):
            raise RuntimeError(
                f"Node {node_name!r}: candidate trade rank result has type "
                f"{type(trade_rank_result).__name__}."
            )
        if trade_rank_result.buyers_sorted == buyers_sorted:
            matches.append(trade_rank_result)
    if len(matches) != 1:
        raise RuntimeError(
            f"Node {node_name!r}: post-trade rank is not uniquely available "
            f"for buyers_sorted {buyers_sorted!r}; match count {len(matches)}."
        )
    return matches[0]


def _require_binding_role(
    binding_visits: tuple,
    visit_key: OrderControlTvtVisitKey,
    expected_role: OrderControlTvtMpLocalBindingTradeRole,
    node_name: str,
) -> None:
    match_count = 0
    for binding_visit in binding_visits:
        if binding_visit.visit_key == visit_key:
            match_count = match_count + 1
            if binding_visit.trade_role is not expected_role:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {visit_key!r} has binding "
                    f"role {binding_visit.trade_role!r}, not {expected_role!r}."
                )
    if match_count != 1:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} does not have exactly "
            f"one binding role; found {match_count}."
        )


def _matching_economic_record(
    economic_records: tuple,
    visit_key: OrderControlTvtVisitKey,
    vehicle_name: str,
    node_name: str,
):
    matched = None
    match_count = 0
    for economic_record in economic_records:
        if economic_record.visit_key == visit_key:
            match_count = match_count + 1
            matched = economic_record
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} does not match "
            f"exactly one economic record; found {match_count}."
        )
    if matched.vehicle_name != vehicle_name:
        raise RuntimeError(
            f"Node {node_name!r}: economic record vehicle_name "
            f"{matched.vehicle_name!r} does not match {vehicle_name!r}."
        )
    return matched


def _matching_final_rank_visit(
    final_rank_visits: tuple[OrderControlTvtMpFinalRankVisitRecord, ...],
    visit_key: OrderControlTvtVisitKey,
    node_name: str,
) -> OrderControlTvtMpFinalRankVisitRecord:
    matched = None
    match_count = 0
    for final_rank_visit in final_rank_visits:
        if final_rank_visit.visit_key == visit_key:
            match_count = match_count + 1
            matched = final_rank_visit
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} does not match "
            f"exactly one final rank record; found {match_count}."
        )
    return matched


def _baseline_local_rank(
    candidate_visits: tuple,
    visit_key: OrderControlTvtVisitKey,
    node_name: str,
) -> int:
    """1-based index in the saved candidate_visits order. No resorting."""
    match_count = 0
    found_rank = 0
    position = 0
    for candidate_visit in candidate_visits:
        position = position + 1
        if candidate_visit.visit_key == visit_key:
            match_count = match_count + 1
            found_rank = position
    if match_count != 1:
        raise RuntimeError(
            f"Node {node_name!r}: baseline local rank for {visit_key!r} is "
            f"not unique in candidate_visits; found {match_count}."
        )
    return found_rank


def _post_trade_local_rank(
    trade_rank_result: OrderControlTvtMpGeneralTradeRankResult,
    visit_key: OrderControlTvtVisitKey,
    node_name: str,
) -> int:
    try:
        assigned_rank = trade_rank_result.assigned_rank(visit_key)
    except ValueError as error:
        raise RuntimeError(
            f"Node {node_name!r}: post-trade local rank for {visit_key!r} "
            f"is not available. {error}"
        ) from error
    if type(assigned_rank) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: post-trade local rank for {visit_key!r} "
            "must be a Python int, not bool."
        )
    return assigned_rank


def _require_live_vehicle(real_world: World, vehicle_name: str) -> Vehicle:
    if vehicle_name not in real_world.VEHICLES:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r} is not in real_W.VEHICLES."
        )
    vehicle = real_world.VEHICLES[vehicle_name]
    if not isinstance(vehicle, Vehicle):
        raise RuntimeError(
            f"real_W.VEHICLES[{vehicle_name!r}] must be a Vehicle; got "
            f"type {type(vehicle).__name__}."
        )
    return vehicle


def _require_live_money(
    value: object,
    vehicle_name: str,
    field_name: str,
) -> int | float:
    return _require_non_negative_finite_number(
        value,
        f"Vehicle {vehicle_name!r} {field_name}",
    )


def _require_updated_money(
    value: object,
    vehicle_name: str,
    field_name: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: updated {field_name} must be a "
            f"finite non-negative number; got {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: updated {field_name} must be finite "
            f"and >= 0; got {value!r}."
        )


def _require_non_negative_finite_number(
    value: object,
    description: str,
) -> int | float:
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"{description} must be a Python int or float, not bool; "
            f"got type {type(value).__name__} with value {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"{description} must be finite and >= 0; got {value!r}."
        )
    return value


def _require_true_vot(value: object, vehicle_name: str) -> float:
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: vot_true must be a Python int or "
            f"float, not bool or None; got {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: vot_true must be finite and >= 0; "
            f"got {value!r}."
        )
    return float(value)


def _require_declared_vot(value: object, vehicle_name: str) -> float:
    """Copy the saved economic-record value. Do not read Vehicle.vot_declared."""
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: saved declared_vot_per_second must be "
            f"a Python int or float, not bool; got {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: saved declared_vot_per_second must be "
            f"finite and >= 0; got {value!r}."
        )
    return float(value)


def _require_passage_timestep(
    value: object,
    vehicle_name: str,
    field_name: str,
) -> int:
    if type(value) is not int:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r}: saved {field_name} must be a Python "
            f"int; got type {type(value).__name__} with value {value!r}."
        )
    return value


def _require_saved_visit_key(
    value: object,
    description: str,
) -> OrderControlTvtVisitKey:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not isinstance(value[0], str)
        or value[0] == ""
        or type(value[1]) is not int
        or value[1] < 1
    ):
        raise RuntimeError(
            f"{description} must be a VisitKey (vehicle_name, visit_id); "
            f"got {value!r}."
        )
    return value


def _require_tuple_column(column: object, column_name: str) -> tuple:
    if not isinstance(column, tuple):
        raise RuntimeError(
            f"{column_name} must be a tuple; got type {type(column).__name__}."
        )
    return column


def _require_node_name(node_name: object, field_name: str) -> str:
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"{field_name} must be a non-empty str; got {node_name!r}."
        )
    return node_name


def _require_same_node_name(
    expected_node_name: str,
    actual_node_name: object,
    column_label: str,
    node_index: int,
) -> None:
    if actual_node_name != expected_node_name:
        raise RuntimeError(
            f"{column_label} node index {node_index} has node_name "
            f"{actual_node_name!r}; expected {expected_node_name!r}."
        )
