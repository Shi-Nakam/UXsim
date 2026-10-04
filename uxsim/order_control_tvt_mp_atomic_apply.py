"""
TVT-MP atomic apply.

One validated final-consistency result is one apply. Prepare every target
Node ledger, every buyer or seller Vehicle update, and every actual-passage
wait proposal before the first live assignment. Commit only if that prepare
finishes. A failure leaves every rank ledger, cumulative amount,
order-exchange log, and actual-passage wait registry unchanged.

This module does not rerun validation, ranks, payments, or virtual
calculations. It does not build an actual-passage observation record, and
it does not read DELTAT again when it copies saved candidate differences.
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
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageCommonFrozenInput,
    OrderControlTvtMpActualPassageMonetaryFrozenInput,
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpActualPassageTradeWait,
    OrderControlTvtMpActualPassageWaitEntry,
    OrderControlTvtMpActualPassageWaitRegistry,
    OrderControlTvtMpActualPassageWaitStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidatePassageObservationStatus,
    OrderControlTvtMpCandidateTrafficObservationRecord,
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
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
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
    establishment_record: OrderControlTvtMpTradeEstablishmentLogRecord


@dataclass
class _PreparedNodeLedgerCommit:
    """One Node whose prepared ledger should be assigned during commit."""

    rank_state: OrderControlTvtNodeRankState
    prepared: object


@dataclass
class _PreparedActualPassageProposal:
    """One selected Node's wait entries and trade wait. Not yet assigned."""

    entries: tuple[OrderControlTvtMpActualPassageWaitEntry, ...]
    trade: OrderControlTvtMpActualPassageTradeWait


@dataclass
class _PreparedActualPassageRegistryReplacement:
    """Copied registry dicts with every proposal already inserted."""

    registry: OrderControlTvtMpActualPassageWaitRegistry
    entries: dict[
        tuple[str, OrderControlTvtVisitKey],
        OrderControlTvtMpActualPassageWaitEntry,
    ]
    trades: dict[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpActualPassageTradeWait,
    ]


def apply_tvt_mp_validated_result(
    final_consistency_validation_set_result,
    real_W,
    rank_states_by_node_name,
) -> OrderControlTvtMpAtomicApplySetResult:
    """
    Apply one validated all-Node result through a fully checked prepare phase.

    Positional arguments only. There is no per-Node or per-Vehicle public
    apply. Prepare builds every ledger replacement, every Vehicle update,
    and every actual-passage wait proposal first. Commit assigns those
    prepared values and does not inspect them.
    """
    validation_result = _require_validation_result(
        final_consistency_validation_set_result,
    )
    real_world = _require_real_world(real_W)
    rank_states = _require_rank_state_mapping(rank_states_by_node_name)
    saved_columns = _saved_columns_from_validation_result(validation_result)
    decision_timestep = _require_decision_timestep(saved_columns, real_world)

    _reject_duplicate_money_vehicle_names(saved_columns)

    # Prepare does not assign rank ledgers, money, logs, or the wait registry.
    node_commits: list[_PreparedNodeLedgerCommit] = []
    vehicle_updates: list[_PreparedVehicleUpdate] = []
    passage_proposals: list[_PreparedActualPassageProposal] = []
    node_index = 0
    for final_rank_node in saved_columns.final_rank_nodes:
        node_commit, node_vehicle_updates, passage_proposal = _prepare_one_node(
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
        if passage_proposal is not None:
            passage_proposals.append(passage_proposal)
        node_index = node_index + 1

    # Zero selected Nodes keep the registry's current dict objects.
    prepared_registry = None
    if len(passage_proposals) > 0:
        prepared_registry = _prepare_actual_passage_registry_replacement(
            real_world,
            passage_proposals,
        )

    # The success object only points at the input validation result.
    # It is built before commit and returned only after commit finishes.
    apply_result = OrderControlTvtMpAtomicApplySetResult(
        final_consistency_validation_set_result=validation_result,
    )

    # Commit assigns prepared state only. It does not search, check, sort,
    # recalculate, or build frozen inputs. Frozen inputs are already inside
    # the prepared WaitEntry objects. This commit is still several live
    # assignments, so an exception in this existing window can remain.
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
    if prepared_registry is not None:
        prepared_registry.registry.entries_by_node_name_and_visit_key = (
            prepared_registry.entries
        )
        prepared_registry.registry.trades_by_transaction_key = (
            prepared_registry.trades
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
) -> tuple[
    _PreparedNodeLedgerCommit | None,
    list[_PreparedVehicleUpdate],
    _PreparedActualPassageProposal | None,
]:
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
        return None, [], None

    visit_pairs, k_confirmed_before = _require_final_rank_column_for_ledger(
        final_rank_node,
        rank_state,
        real_world,
    )
    node_commit = None
    if len(visit_pairs) != 0:
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
        node_commit = _PreparedNodeLedgerCommit(
            rank_state=rank_state,
            prepared=prepared_ledger,
        )

    if status is not OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
        # Fallback confirms ranks only. It does not open an evaluation WaitEntry.
        return node_commit, [], None

    # A selected Node with money rows must still be checked. An empty
    # final-rank column has no ledger commit, but it can still have waits.
    vehicle_updates = _prepare_selected_vehicle_updates(
        saved_columns=saved_columns,
        node_index=node_index,
        final_rank_node=final_rank_node,
        payment_node=payment_node,
        real_world=real_world,
        decision_timestep=decision_timestep,
        k_confirmed_before=k_confirmed_before,
    )
    passage_proposal = _prepare_actual_passage_proposal(
        saved_columns=saved_columns,
        node_index=node_index,
        final_rank_node=final_rank_node,
        payment_node=payment_node,
        decision_timestep=decision_timestep,
        vehicle_updates=vehicle_updates,
    )
    return node_commit, vehicle_updates, passage_proposal


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


def _prepare_actual_passage_proposal(
    *,
    saved_columns: _SavedApplyColumns,
    node_index: int,
    final_rank_node: OrderControlTvtNodeMpFinalRankResult,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    decision_timestep: int,
    vehicle_updates: list[_PreparedVehicleUpdate],
) -> _PreparedActualPassageProposal:
    """
    Build wait entries and one trade wait for one selected Node.

    The live registry is not changed here. Buyer and seller true VOT is the
    value already checked for the establishment row. It is not read from the
    live Vehicle again. A nonparticipating true VOT comes from the saved
    traffic observation. The exchange log is not searched.
    Monetary frozen inputs copy the same saved amounts that were written on
    the establishment row. They do not keep that row object.
    """
    node_name = final_rank_node.node_name
    selected = _require_selected_candidate(final_rank_node)
    local_result = _require_local_result(selected, node_name)
    if local_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: selected local result belongs to "
            f"{local_result.node_name!r}."
        )
    buyers_sorted = _require_buyers_sorted(local_result, node_name)
    traffic_records = local_result.traffic_observation_records
    trade_scope = (
        local_result.binding_rank_sequence.trade_scope_of_this_candidate_visits
    )
    _require_traffic_observations_match_trade_scope(
        node_name,
        traffic_records,
        trade_scope,
    )
    establishment_records = _establishment_records_from_vehicle_updates(
        vehicle_updates,
        node_name,
    )
    candidate_visits = saved_columns.candidate_visit_nodes[node_index].candidate_visits
    trade_rank_result = _matching_trade_rank_result(
        saved_columns.trade_rank_nodes[node_index],
        buyers_sorted,
        node_name,
    )
    outside_visits = (
        local_result.binding_rank_sequence
        .outside_trade_scope_inside_k_fixed_visits
    )

    entries: list[OrderControlTvtMpActualPassageWaitEntry] = []
    all_visit_keys: list[OrderControlTvtVisitKey] = []
    buyer_visit_keys: list[OrderControlTvtVisitKey] = []
    seller_visit_keys: list[OrderControlTvtVisitKey] = []
    nonparticipating_visit_keys: list[OrderControlTvtVisitKey] = []
    matched_establishment_visit_keys: list[OrderControlTvtVisitKey] = []

    traffic_index = 0
    for traffic_record in traffic_records:
        binding_visit = trade_scope[traffic_index]
        traffic_index = traffic_index + 1
        visit_key = traffic_record.visit_key
        actual_role = _actual_passage_role(
            traffic_record.trade_role,
            node_name,
            visit_key,
        )
        _require_role_status(
            actual_role,
            traffic_record.passage_observation_status,
            node_name,
            visit_key,
        )
        final_rank_visit = _matching_final_rank_visit(
            final_rank_node.final_rank_visits,
            visit_key,
            node_name,
        )
        route_origin = _require_saved_route_origin(
            final_rank_visit.route_origin,
            node_name,
            visit_key,
        )
        _require_binding_route_matches_final_rank(
            binding_visit,
            final_rank_visit,
            route_origin,
            node_name,
        )
        baseline_local_rank = _baseline_local_rank(
            candidate_visits,
            visit_key,
            node_name,
        )
        post_trade_local_rank = _post_trade_local_rank(
            trade_rank_result,
            visit_key,
            node_name,
        )
        rank_change = baseline_local_rank - post_trade_local_rank
        common_frozen_input = OrderControlTvtMpActualPassageCommonFrozenInput(
            baseline_local_rank=baseline_local_rank,
            post_trade_local_rank=post_trade_local_rank,
            rank_change=rank_change,
            route_origin=route_origin,
        )
        if (
            actual_role is OrderControlTvtMpActualPassageRole.BUYER
            or actual_role is OrderControlTvtMpActualPassageRole.SELLER
        ):
            establishment = _require_matching_establishment(
                establishment_records,
                traffic_record,
                node_name=node_name,
                buyers_sorted=buyers_sorted,
                expected_trade_role=_establishment_role_for_actual_role(actual_role),
            )
            if visit_key in matched_establishment_visit_keys:
                raise RuntimeError(
                    f"Node {node_name!r}: VisitKey {visit_key!r} was matched "
                    "to more than one establishment record."
                )
            matched_establishment_visit_keys.append(visit_key)
            # Same checked value that was stored on the establishment record.
            # Do not read Vehicle.vot_true again.
            true_vot_per_second = establishment.true_vot_per_second
            paid_amount, received_amount, declared_vot_per_second = (
                _trade_money_inputs_for_visit(
                    payment_node=payment_node,
                    selected=selected,
                    actual_role=actual_role,
                    visit_key=visit_key,
                    vehicle_name=traffic_record.vehicle_name,
                    node_name=node_name,
                )
            )
            _require_establishment_matches_frozen_money(
                establishment,
                baseline_local_rank=baseline_local_rank,
                post_trade_local_rank=post_trade_local_rank,
                rank_change=rank_change,
                declared_vot_per_second=declared_vot_per_second,
                payment_paid_in_this_transaction=paid_amount,
                payment_received_in_this_transaction=received_amount,
                node_name=node_name,
            )
            monetary_frozen_input = (
                OrderControlTvtMpActualPassageMonetaryFrozenInput(
                    declared_vot_per_second=declared_vot_per_second,
                    payment_paid_in_this_transaction=paid_amount,
                    payment_received_in_this_transaction=received_amount,
                )
            )
        else:
            _require_no_establishment_for_visit(
                establishment_records,
                visit_key,
                node_name,
            )
            # Saved on the traffic observation. Do not read Vehicle.vot_true.
            true_vot_per_second = traffic_record.true_vot_per_second
            monetary_frozen_input = None

        # Copy the saved candidate differences. Do not recompute them.
        entry = OrderControlTvtMpActualPassageWaitEntry(
            tvt_decision_timestep=decision_timestep,
            node_name=node_name,
            buyers_sorted=buyers_sorted,
            visit_key=visit_key,
            vehicle_name=traffic_record.vehicle_name,
            role=actual_role,
            wait_status=(
                OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
            ),
            baseline_passage_timestep=traffic_record.baseline_passage_timestep,
            candidate_passage_timestep=traffic_record.candidate_passage_timestep,
            true_vot_per_second=true_vot_per_second,
            baseline_minus_candidate_passage_timesteps=(
                traffic_record.predicted_time_difference_timesteps
            ),
            baseline_minus_candidate_passage_seconds=(
                traffic_record.predicted_time_difference_seconds
            ),
            baseline_minus_candidate_time_value=(
                traffic_record.predicted_signed_time_value_change
            ),
            predicted_observation_status=traffic_record.passage_observation_status,
            predicted_route_next_link_name=traffic_record.route_next_link_name,
            common_frozen_input=common_frozen_input,
            monetary_frozen_input=monetary_frozen_input,
            actual_passage_observation_record=None,
        )
        entries.append(entry)
        all_visit_keys.append(visit_key)
        if actual_role is OrderControlTvtMpActualPassageRole.BUYER:
            buyer_visit_keys.append(visit_key)
        elif actual_role is OrderControlTvtMpActualPassageRole.SELLER:
            seller_visit_keys.append(visit_key)
        else:
            nonparticipating_visit_keys.append(visit_key)

    _require_partition_4_has_no_wait_entry(
        outside_visits,
        all_visit_keys,
        node_name,
    )
    _require_establishments_match_buyer_and_seller_observations(
        establishment_records,
        matched_establishment_visit_keys,
        node_name,
    )
    trade = OrderControlTvtMpActualPassageTradeWait(
        tvt_decision_timestep=decision_timestep,
        node_name=node_name,
        buyers_sorted=buyers_sorted,
        all_visit_keys=tuple(all_visit_keys),
        buyer_visit_keys=tuple(buyer_visit_keys),
        seller_visit_keys=tuple(seller_visit_keys),
        nonparticipating_visit_keys=tuple(nonparticipating_visit_keys),
    )
    return _PreparedActualPassageProposal(
        entries=tuple(entries),
        trade=trade,
    )


def _require_traffic_observations_match_trade_scope(
    node_name: str,
    traffic_records: object,
    trade_scope: object,
) -> None:
    """Saved traffic observations and trade scope must name the same visits."""
    if not isinstance(traffic_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: traffic_observation_records must be a "
            f"tuple; got type {type(traffic_records).__name__}."
        )
    if not isinstance(trade_scope, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: trade_scope_of_this_candidate_visits must "
            f"be a tuple; got type {type(trade_scope).__name__}."
        )
    if len(traffic_records) != len(trade_scope):
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation count "
            f"{len(traffic_records)} does not match trade scope count "
            f"{len(trade_scope)}."
        )

    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    index = 0
    for traffic_record in traffic_records:
        trade_scope_visit = trade_scope[index]
        position = index + 1
        index = index + 1
        if not isinstance(
            traffic_record,
            OrderControlTvtMpCandidateTrafficObservationRecord,
        ):
            raise RuntimeError(
                f"Node {node_name!r}: traffic observation position {position} "
                "must be OrderControlTvtMpCandidateTrafficObservationRecord; "
                f"got type {type(traffic_record).__name__}."
            )
        if not isinstance(trade_scope_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"Node {node_name!r}: trade scope position {position} must be "
                "OrderControlTvtMpLocalBindingRankVisit; got type "
                f"{type(trade_scope_visit).__name__}."
            )
        visit_key = _require_saved_visit_key(
            traffic_record.visit_key,
            f"Node {node_name!r} traffic observation position {position}",
        )
        scope_visit_key = _require_saved_visit_key(
            trade_scope_visit.visit_key,
            f"Node {node_name!r} trade scope position {position}",
        )
        if visit_key != scope_visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: traffic observation position {position} "
                f"has VisitKey {visit_key!r}, but trade scope has "
                f"{scope_visit_key!r}."
            )
        if traffic_record.trade_role is not trade_scope_visit.trade_role:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} has traffic "
                f"observation role {traffic_record.trade_role!r}, but trade "
                f"scope role {trade_scope_visit.trade_role!r}."
            )
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is duplicated "
                "in traffic observations and trade scope."
            )
        seen_visit_keys.append(visit_key)
        if traffic_record.vehicle_name != visit_key[0]:
            raise RuntimeError(
                f"Node {node_name!r}: traffic observation vehicle_name "
                f"{traffic_record.vehicle_name!r} does not match VisitKey "
                f"{visit_key!r}."
            )
        _actual_passage_role(traffic_record.trade_role, node_name, visit_key)
        _require_status_and_candidate_values(traffic_record, node_name)


def _require_status_and_candidate_values(
    traffic_record: OrderControlTvtMpCandidateTrafficObservationRecord,
    node_name: str,
) -> None:
    """OBSERVED keeps candidate numbers. UNOBSERVED_AT_HORIZON keeps None."""
    status = traffic_record.passage_observation_status
    visit_key = traffic_record.visit_key
    candidate_passage_timestep = traffic_record.candidate_passage_timestep
    predicted_timesteps = traffic_record.predicted_time_difference_timesteps
    predicted_seconds = traffic_record.predicted_time_difference_seconds
    predicted_value = traffic_record.predicted_signed_time_value_change
    if status is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} passage observation "
            "status is None."
        )
    if status is OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED:
        baseline_passage_timestep = traffic_record.baseline_passage_timestep
        if type(baseline_passage_timestep) is not int:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is OBSERVED but "
                "baseline_passage_timestep is not a Python int; got "
                f"{baseline_passage_timestep!r}."
            )
        if type(candidate_passage_timestep) is not int:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is OBSERVED but "
                "candidate_passage_timestep is not a Python int; got "
                f"{candidate_passage_timestep!r}."
            )
        _require_saved_predicted_number(
            predicted_timesteps,
            node_name,
            visit_key,
            "predicted_time_difference_timesteps",
        )
        _require_saved_predicted_number(
            predicted_seconds,
            node_name,
            visit_key,
            "predicted_time_difference_seconds",
        )
        _require_saved_predicted_number(
            predicted_value,
            node_name,
            visit_key,
            "predicted_signed_time_value_change",
        )
        expected_predicted_time_difference_timesteps = (
            baseline_passage_timestep - candidate_passage_timestep
        )
        if predicted_timesteps != expected_predicted_time_difference_timesteps:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} "
                "predicted_time_difference_timesteps "
                f"{predicted_timesteps!r} does not equal baseline minus "
                "candidate passage timesteps "
                f"{expected_predicted_time_difference_timesteps!r}."
            )
        return
    if (
        status
        is OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON
    ):
        if (
            candidate_passage_timestep is not None
            or predicted_timesteps is not None
            or predicted_seconds is not None
            or predicted_value is not None
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is "
                "UNOBSERVED_AT_HORIZON, so candidate passage and predicted "
                "candidate differences must all be None."
            )
        return
    raise RuntimeError(
        f"Node {node_name!r}: VisitKey {visit_key!r} has passage observation "
        f"status {status!r}."
    )


def _require_saved_predicted_number(
    value: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    field_name: str,
) -> None:
    """Presence check only. The stored number is copied unchanged."""
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} field {field_name} "
            "must be a Python int or float when the visit is OBSERVED; "
            f"got {value!r}."
        )


def _require_role_status(
    actual_role: OrderControlTvtMpActualPassageRole,
    status: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    if status is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} passage observation "
            "status is None."
        )
    observed = OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
    unobserved = (
        OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON
    )
    if (
        actual_role is OrderControlTvtMpActualPassageRole.BUYER
        or actual_role is OrderControlTvtMpActualPassageRole.SELLER
    ):
        if status is not observed:
            raise RuntimeError(
                f"Node {node_name!r}: {actual_role.value} VisitKey "
                f"{visit_key!r} must be OBSERVED; got {status!r}."
            )
        return
    if actual_role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        if status is not observed and status is not unobserved:
            raise RuntimeError(
                f"Node {node_name!r}: nonparticipating VisitKey {visit_key!r} "
                "must be OBSERVED or UNOBSERVED_AT_HORIZON; got "
                f"{status!r}."
            )
        return
    raise RuntimeError(
        f"Node {node_name!r}: VisitKey {visit_key!r} has actual passage role "
        f"{actual_role!r}."
    )


def _actual_passage_role(
    binding_role: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> OrderControlTvtMpActualPassageRole:
    if binding_role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return OrderControlTvtMpActualPassageRole.BUYER
    if binding_role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return OrderControlTvtMpActualPassageRole.SELLER
    if binding_role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return OrderControlTvtMpActualPassageRole.NONPARTICIPATING
    raise RuntimeError(
        f"Node {node_name!r}: VisitKey {visit_key!r} has trade role "
        f"{binding_role!r}. Actual passage wait accepts only buyer, seller, "
        "and nonparticipating."
    )


def _establishment_role_for_actual_role(
    actual_role: OrderControlTvtMpActualPassageRole,
) -> OrderControlTvtMpTradeEstablishmentRole:
    if actual_role is OrderControlTvtMpActualPassageRole.BUYER:
        return OrderControlTvtMpTradeEstablishmentRole.BUYER
    if actual_role is OrderControlTvtMpActualPassageRole.SELLER:
        return OrderControlTvtMpTradeEstablishmentRole.SELLER
    raise RuntimeError(
        f"Actual passage role {actual_role!r} has no establishment role."
    )


def _establishment_records_from_vehicle_updates(
    vehicle_updates: list[_PreparedVehicleUpdate],
    node_name: str,
) -> list[OrderControlTvtMpTradeEstablishmentLogRecord]:
    """Each prepared Vehicle update carries its establishment row directly."""
    establishment_records: list[OrderControlTvtMpTradeEstablishmentLogRecord] = []
    seen_visit_keys: list[OrderControlTvtVisitKey] = []
    for vehicle_update in vehicle_updates:
        establishment = vehicle_update.establishment_record
        if not isinstance(establishment, OrderControlTvtMpTradeEstablishmentLogRecord):
            raise RuntimeError(
                f"Node {node_name!r}: prepared Vehicle update "
                "establishment_record must be "
                "OrderControlTvtMpTradeEstablishmentLogRecord; got "
                f"type {type(establishment).__name__}."
            )
        if establishment.visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: establishment VisitKey "
                f"{establishment.visit_key!r} is duplicated."
            )
        seen_visit_keys.append(establishment.visit_key)
        establishment_records.append(establishment)
    return establishment_records


def _require_matching_establishment(
    establishment_records: list[OrderControlTvtMpTradeEstablishmentLogRecord],
    traffic_record: OrderControlTvtMpCandidateTrafficObservationRecord,
    *,
    node_name: str,
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    expected_trade_role: OrderControlTvtMpTradeEstablishmentRole,
) -> OrderControlTvtMpTradeEstablishmentLogRecord:
    visit_key = traffic_record.visit_key
    matched = None
    match_count = 0
    for establishment in establishment_records:
        if establishment.visit_key == visit_key:
            match_count = match_count + 1
            matched = establishment
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} does not match "
            f"exactly one establishment record; found {match_count}."
        )
    if matched.visit_key != traffic_record.visit_key:
        raise RuntimeError(
            f"Node {node_name!r}: establishment VisitKey {matched.visit_key!r} "
            f"does not match traffic observation VisitKey {visit_key!r}."
        )
    if matched.vehicle_name != traffic_record.vehicle_name:
        raise RuntimeError(
            f"Node {node_name!r}: establishment vehicle_name "
            f"{matched.vehicle_name!r} does not match traffic observation "
            f"vehicle_name {traffic_record.vehicle_name!r}."
        )
    if matched.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: establishment node_name "
            f"{matched.node_name!r} does not match."
        )
    if matched.buyers_sorted != buyers_sorted:
        raise RuntimeError(
            f"Node {node_name!r}: establishment buyers_sorted "
            f"{matched.buyers_sorted!r} does not match {buyers_sorted!r}."
        )
    if matched.trade_role is not expected_trade_role:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} has establishment "
            f"role {matched.trade_role!r}, not {expected_trade_role!r}."
        )
    if (
        matched.baseline_passage_timestep
        != traffic_record.baseline_passage_timestep
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} baseline passage "
            f"{traffic_record.baseline_passage_timestep!r} does not match "
            f"establishment baseline {matched.baseline_passage_timestep!r}."
        )
    if (
        matched.candidate_passage_timestep
        != traffic_record.candidate_passage_timestep
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} candidate passage "
            f"{traffic_record.candidate_passage_timestep!r} does not match "
            f"establishment candidate {matched.candidate_passage_timestep!r}."
        )
    return matched


def _require_establishments_match_buyer_and_seller_observations(
    establishment_records: list[OrderControlTvtMpTradeEstablishmentLogRecord],
    matched_establishment_visit_keys: list[OrderControlTvtVisitKey],
    node_name: str,
) -> None:
    if len(establishment_records) != len(matched_establishment_visit_keys):
        raise RuntimeError(
            f"Node {node_name!r}: buyer and seller traffic observations do "
            "not match establishment records one to one; observations "
            f"{len(matched_establishment_visit_keys)}, establishment records "
            f"{len(establishment_records)}."
        )
    for establishment in establishment_records:
        if establishment.visit_key not in matched_establishment_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: establishment VisitKey "
                f"{establishment.visit_key!r} has no buyer or seller traffic "
                "observation."
            )


def _require_saved_route_origin(
    value: object,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> OrderControlTvtMpLocalBindingRouteOrigin:
    """Accept the saved enum. Do not compare it with a route name."""
    if not isinstance(value, OrderControlTvtMpLocalBindingRouteOrigin):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} route_origin must be "
            "OrderControlTvtMpLocalBindingRouteOrigin; got type "
            f"{type(value).__name__} with value {value!r}."
        )
    return value


def _require_binding_route_matches_final_rank(
    binding_visit: OrderControlTvtMpLocalBindingRankVisit,
    final_rank_visit: OrderControlTvtMpFinalRankVisitRecord,
    route_origin: OrderControlTvtMpLocalBindingRouteOrigin,
    node_name: str,
) -> None:
    visit_key = binding_visit.visit_key
    if not isinstance(
        binding_visit.route_origin,
        OrderControlTvtMpLocalBindingRouteOrigin,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} binding route_origin "
            f"{binding_visit.route_origin!r} is not a saved route origin."
        )
    if route_origin is not binding_visit.route_origin:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} final rank "
            f"route_origin {route_origin!r} does not match binding "
            f"route_origin {binding_visit.route_origin!r}."
        )
    formal_route = final_rank_visit.formal_route_next_link_name
    binding_route = binding_visit.route_next_link_name
    if not isinstance(formal_route, str) or formal_route == "":
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} final rank formal "
            f"route must be a non-empty str; got {formal_route!r}."
        )
    if not isinstance(binding_route, str) or binding_route == "":
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} binding route must "
            f"be a non-empty str; got {binding_route!r}."
        )
    if formal_route != binding_route:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} final rank formal "
            f"route {formal_route!r} does not match binding route "
            f"{binding_route!r}."
        )


def _trade_money_inputs_for_visit(
    *,
    payment_node: OrderControlTvtNodeMpPaymentAndCompensationResult,
    selected: OrderControlTvtMpCandidateEconomicEvaluationResult,
    actual_role: OrderControlTvtMpActualPassageRole,
    visit_key: OrderControlTvtVisitKey,
    vehicle_name: str,
    node_name: str,
) -> tuple[int | float, int | float, float]:
    """Read this transaction's saved amounts. Do not use cumulative totals."""
    if actual_role is OrderControlTvtMpActualPassageRole.BUYER:
        payment_record = _matching_payment_record(
            payment_node.buyer_payment_records,
            visit_key,
            vehicle_name,
            node_name,
            "buyer payment",
        )
        economic_record = _matching_economic_record(
            selected.buyer_economic_records,
            visit_key,
            vehicle_name,
            node_name,
        )
        paid_amount = _require_non_negative_finite_number(
            payment_record.payment_P_b,
            f"Node {node_name!r} payment amount for {visit_key!r}",
        )
        received_amount = 0
    elif actual_role is OrderControlTvtMpActualPassageRole.SELLER:
        payment_record = _matching_payment_record(
            payment_node.seller_compensation_records,
            visit_key,
            vehicle_name,
            node_name,
            "seller compensation",
        )
        economic_record = _matching_economic_record(
            selected.seller_economic_records,
            visit_key,
            vehicle_name,
            node_name,
        )
        paid_amount = 0
        received_amount = _require_non_negative_finite_number(
            payment_record.compensation_amount,
            f"Node {node_name!r} compensation amount for {visit_key!r}",
        )
    else:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} role {actual_role!r} "
            "has no transaction amount."
        )
    declared_vot_per_second = _require_declared_vot(
        economic_record.declared_vot_per_second,
        vehicle_name,
    )
    return paid_amount, received_amount, declared_vot_per_second


def _matching_payment_record(
    payment_records: tuple,
    visit_key: OrderControlTvtVisitKey,
    vehicle_name: str,
    node_name: str,
    record_label: str,
):
    matched = None
    match_count = 0
    for payment_record in payment_records:
        if payment_record.visit_key == visit_key:
            match_count = match_count + 1
            matched = payment_record
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} does not match "
            f"exactly one {record_label} record; found {match_count}."
        )
    if matched.vehicle_name != vehicle_name:
        raise RuntimeError(
            f"Node {node_name!r}: {record_label} vehicle_name "
            f"{matched.vehicle_name!r} does not match {vehicle_name!r}."
        )
    return matched


def _require_establishment_matches_frozen_money(
    establishment: OrderControlTvtMpTradeEstablishmentLogRecord,
    *,
    baseline_local_rank: int,
    post_trade_local_rank: int,
    rank_change: int,
    declared_vot_per_second: float,
    payment_paid_in_this_transaction: int | float,
    payment_received_in_this_transaction: int | float,
    node_name: str,
) -> None:
    """Check the row. The frozen input is built from the saved inputs."""
    visit_key = establishment.visit_key
    if establishment.baseline_local_rank != baseline_local_rank:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} establishment "
            f"baseline_local_rank {establishment.baseline_local_rank!r} does "
            f"not match {baseline_local_rank!r}."
        )
    if establishment.post_trade_local_rank != post_trade_local_rank:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} establishment "
            f"post_trade_local_rank {establishment.post_trade_local_rank!r} "
            f"does not match {post_trade_local_rank!r}."
        )
    if establishment.rank_change != rank_change:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} establishment "
            f"rank_change {establishment.rank_change!r} does not match "
            f"{rank_change!r}."
        )
    if establishment.declared_vot_per_second != declared_vot_per_second:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} establishment "
            "declared_vot_per_second "
            f"{establishment.declared_vot_per_second!r} does not match "
            f"{declared_vot_per_second!r}."
        )
    if (
        establishment.payment_paid_in_this_transaction
        != payment_paid_in_this_transaction
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} establishment "
            "payment_paid_in_this_transaction "
            f"{establishment.payment_paid_in_this_transaction!r} does not "
            f"match {payment_paid_in_this_transaction!r}."
        )
    if (
        establishment.payment_received_in_this_transaction
        != payment_received_in_this_transaction
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} establishment "
            "payment_received_in_this_transaction "
            f"{establishment.payment_received_in_this_transaction!r} does "
            f"not match {payment_received_in_this_transaction!r}."
        )


def _require_no_establishment_for_visit(
    establishment_records: list[OrderControlTvtMpTradeEstablishmentLogRecord],
    visit_key: OrderControlTvtVisitKey,
    node_name: str,
) -> None:
    for establishment in establishment_records:
        if establishment.visit_key == visit_key:
            raise RuntimeError(
                f"Node {node_name!r}: nonparticipating VisitKey {visit_key!r} "
                "must not have an establishment record."
            )


def _require_partition_4_has_no_wait_entry(
    outside_visits: object,
    wait_entry_visit_keys: list[OrderControlTvtVisitKey],
    node_name: str,
) -> None:
    if not isinstance(outside_visits, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: outside_trade_scope_inside_k_fixed_visits "
            f"must be a tuple; got type {type(outside_visits).__name__}."
        )
    for outside_visit in outside_visits:
        if not isinstance(outside_visit, OrderControlTvtMpLocalBindingRankVisit):
            raise RuntimeError(
                f"Node {node_name!r}: partition 4 visit must be "
                "OrderControlTvtMpLocalBindingRankVisit; got type "
                f"{type(outside_visit).__name__}."
            )
        if outside_visit.visit_key in wait_entry_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: partition 4 VisitKey "
                f"{outside_visit.visit_key!r} must not have an evaluation "
                "WaitEntry."
            )


def _prepare_actual_passage_registry_replacement(
    real_world: World,
    passage_proposals: list[_PreparedActualPassageProposal],
) -> _PreparedActualPassageRegistryReplacement:
    """
    Check keys, then copy the two registry dicts and insert every proposal.

    This still runs before commit. The live dict objects are not replaced
    and their contents are not changed.
    """
    registry = real_world.order_control_tvt_mp_actual_passage_wait_registry
    if not isinstance(registry, OrderControlTvtMpActualPassageWaitRegistry):
        raise RuntimeError(
            "real_W.order_control_tvt_mp_actual_passage_wait_registry must "
            "be OrderControlTvtMpActualPassageWaitRegistry; got type "
            f"{type(registry).__name__}."
        )
    current_entries = registry.entries_by_node_name_and_visit_key
    current_trades = registry.trades_by_transaction_key
    if not isinstance(current_entries, dict) or not isinstance(current_trades, dict):
        raise RuntimeError(
            "actual passage wait registry must hold two dicts; got "
            f"entries {type(current_entries).__name__} and trades "
            f"{type(current_trades).__name__}."
        )

    seen_entry_keys: list[tuple[str, OrderControlTvtVisitKey]] = []
    seen_transaction_keys: list[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]]
    ] = []
    for proposal in passage_proposals:
        trade = proposal.trade
        transaction_key = (
            trade.tvt_decision_timestep,
            trade.node_name,
            trade.buyers_sorted,
        )
        if transaction_key in seen_transaction_keys:
            raise RuntimeError(
                "actual passage transaction key "
                f"{transaction_key!r} is duplicated in this apply."
            )
        seen_transaction_keys.append(transaction_key)
        for entry in proposal.entries:
            entry_key = (entry.node_name, entry.visit_key)
            if entry_key in seen_entry_keys:
                raise RuntimeError(
                    f"actual passage entry key {entry_key!r} is duplicated "
                    "in this apply."
                )
            seen_entry_keys.append(entry_key)

    for entry_key in seen_entry_keys:
        if entry_key in current_entries:
            raise RuntimeError(
                f"actual passage entry key {entry_key!r} is already in the "
                "wait registry."
            )
    for transaction_key in seen_transaction_keys:
        if transaction_key in current_trades:
            raise RuntimeError(
                "actual passage transaction key "
                f"{transaction_key!r} is already in the wait registry."
            )

    replacement_entries = dict(current_entries)
    replacement_trades = dict(current_trades)
    for proposal in passage_proposals:
        trade = proposal.trade
        transaction_key = (
            trade.tvt_decision_timestep,
            trade.node_name,
            trade.buyers_sorted,
        )
        for entry in proposal.entries:
            entry_key = (entry.node_name, entry.visit_key)
            replacement_entries[entry_key] = entry
        replacement_trades[transaction_key] = trade
    return _PreparedActualPassageRegistryReplacement(
        registry=registry,
        entries=replacement_entries,
        trades=replacement_trades,
    )


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
        establishment_record=establishment_record,
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
