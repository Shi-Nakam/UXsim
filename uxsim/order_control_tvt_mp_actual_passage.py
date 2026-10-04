from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey

if TYPE_CHECKING:
    from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
        OrderControlTvtMpCandidatePassageObservationStatus,
    )


class OrderControlTvtMpActualPassageRole(Enum):
    BUYER = "buyer"
    SELLER = "seller"
    NONPARTICIPATING = "nonparticipating"


class OrderControlTvtMpActualPassageObservationStatus(Enum):
    ACTUAL_PASSAGE_OBSERVED = "actual_passage_observed"
    ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END = (
        "actual_passage_unobserved_at_evaluation_end"
    )


class OrderControlTvtMpActualPassageWaitStatus(Enum):
    WAITING_FOR_ACTUAL_PASSAGE = "waiting_for_actual_passage"
    ACTUAL_PASSAGE_OBSERVED = "actual_passage_observed"
    ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END = (
        "actual_passage_unobserved_at_evaluation_end"
    )


@dataclass(frozen=True)
class OrderControlTvtMpActualPassageObservationRecord:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    role: OrderControlTvtMpActualPassageRole
    observation_status: OrderControlTvtMpActualPassageObservationStatus
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    true_vot_per_second: float
    predicted_observation_status: OrderControlTvtMpCandidatePassageObservationStatus
    predicted_route_next_link_name: str
    baseline_minus_candidate_passage_timesteps: int | None
    baseline_minus_candidate_passage_seconds: int | float | None
    baseline_minus_candidate_time_value: int | float | None
    baseline_minus_actual_passage_timesteps: int | None
    baseline_minus_actual_passage_seconds: int | float | None
    baseline_minus_actual_time_value: int | float | None
    candidate_minus_actual_passage_timesteps: int | None
    candidate_minus_actual_passage_seconds: int | float | None
    candidate_minus_actual_time_value: int | float | None
    actual_passage_timestep: int | None
    actual_route_next_link_name: str | None


@dataclass(frozen=True)
class OrderControlTvtMpActualPassageCommonFrozenInput:
    """Establishment ranks and route origin copied for later evaluation.

    Identity fields that already live on the wait entry are not repeated
    here. The formal route and the Node rank stay on the rank ledger.
    """

    baseline_local_rank: int
    post_trade_local_rank: int
    rank_change: int
    route_origin: OrderControlTvtMpLocalBindingRouteOrigin

    def __post_init__(self) -> None:
        # Imported here because uxsim.py loads this module while World is
        # still being defined. The binding module reaches World.
        from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
            OrderControlTvtMpLocalBindingRouteOrigin,
        )
        if type(self.baseline_local_rank) is not int:
            raise RuntimeError(
                "baseline_local_rank must be a Python int, not bool; got "
                f"{self.baseline_local_rank!r}."
            )
        if type(self.post_trade_local_rank) is not int:
            raise RuntimeError(
                "post_trade_local_rank must be a Python int, not bool; got "
                f"{self.post_trade_local_rank!r}."
            )
        if type(self.rank_change) is not int:
            raise RuntimeError(
                "rank_change must be a Python int, not bool; got "
                f"{self.rank_change!r}."
            )
        expected_rank_change = (
            self.baseline_local_rank - self.post_trade_local_rank
        )
        if self.rank_change != expected_rank_change:
            raise RuntimeError(
                "rank_change must equal baseline_local_rank minus "
                "post_trade_local_rank; got "
                f"{self.rank_change!r}, expected {expected_rank_change!r}."
            )
        if not isinstance(
            self.route_origin,
            OrderControlTvtMpLocalBindingRouteOrigin,
        ):
            raise RuntimeError(
                "route_origin must be "
                "OrderControlTvtMpLocalBindingRouteOrigin; got type "
                f"{type(self.route_origin).__name__} with value "
                f"{self.route_origin!r}."
            )


@dataclass(frozen=True)
class OrderControlTvtMpActualPassageMonetaryFrozenInput:
    """Buyer or seller transaction amounts copied at establishment.

    Zero is a real computed amount. None is not used in these fields.
    Buyer and seller share this one type.
    """

    declared_vot_per_second: float
    payment_paid_in_this_transaction: int | float
    payment_received_in_this_transaction: int | float

    def __post_init__(self) -> None:
        _require_non_negative_money_number(
            self.declared_vot_per_second,
            "declared_vot_per_second",
        )
        _require_non_negative_money_number(
            self.payment_paid_in_this_transaction,
            "payment_paid_in_this_transaction",
        )
        _require_non_negative_money_number(
            self.payment_received_in_this_transaction,
            "payment_received_in_this_transaction",
        )


def _require_non_negative_money_number(value: object, field_name: str) -> None:
    """Reject None, bool, and non-finite numbers. Zero is allowed."""
    if value is None:
        raise RuntimeError(
            f"{field_name} must be a formal number, not None."
        )
    if isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"{field_name} must be a Python int or float, not bool; got "
            f"{value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"{field_name} must be finite and >= 0; got {value!r}."
        )


@dataclass
class OrderControlTvtMpActualPassageWaitEntry:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    role: OrderControlTvtMpActualPassageRole
    wait_status: OrderControlTvtMpActualPassageWaitStatus
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    true_vot_per_second: float
    baseline_minus_candidate_passage_timesteps: int | None
    baseline_minus_candidate_passage_seconds: int | float | None
    baseline_minus_candidate_time_value: int | float | None
    predicted_observation_status: OrderControlTvtMpCandidatePassageObservationStatus
    predicted_route_next_link_name: str
    common_frozen_input: OrderControlTvtMpActualPassageCommonFrozenInput
    monetary_frozen_input: OrderControlTvtMpActualPassageMonetaryFrozenInput | None
    actual_passage_observation_record: (
        OrderControlTvtMpActualPassageObservationRecord | None
    ) = None

    def __post_init__(self) -> None:
        """Check this object's shape only. Do not search logs or ledgers."""
        if not isinstance(
            self.common_frozen_input,
            OrderControlTvtMpActualPassageCommonFrozenInput,
        ):
            raise RuntimeError(
                "common_frozen_input must be "
                "OrderControlTvtMpActualPassageCommonFrozenInput; got type "
                f"{type(self.common_frozen_input).__name__}."
            )
        if (
            self.role is OrderControlTvtMpActualPassageRole.BUYER
            or self.role is OrderControlTvtMpActualPassageRole.SELLER
        ):
            if not isinstance(
                self.monetary_frozen_input,
                OrderControlTvtMpActualPassageMonetaryFrozenInput,
            ):
                raise RuntimeError(
                    f"{self.role.value} wait entry requires "
                    "OrderControlTvtMpActualPassageMonetaryFrozenInput; got "
                    f"{self.monetary_frozen_input!r}."
                )
            return
        if self.role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
            if self.monetary_frozen_input is not None:
                raise RuntimeError(
                    "nonparticipating wait entry must not carry a monetary "
                    "frozen input; None means no monetary contract."
                )
            return
        raise RuntimeError(
            "wait entry role must be buyer, seller, or nonparticipating; "
            f"got {self.role!r}."
        )


@dataclass
class OrderControlTvtMpActualPassageTradeWait:
    tvt_decision_timestep: int
    node_name: str
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...]
    all_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    buyer_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    seller_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    nonparticipating_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    buyer_seller_actual_passage_completion_notified: bool = False


@dataclass
class OrderControlTvtMpActualPassageWaitRegistry:
    entries_by_node_name_and_visit_key: dict[
        tuple[str, OrderControlTvtVisitKey],
        OrderControlTvtMpActualPassageWaitEntry,
    ] = field(default_factory=dict)
    trades_by_transaction_key: dict[
        tuple[int, str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpActualPassageTradeWait,
    ] = field(default_factory=dict)


@dataclass(frozen=True)
class _PreparedTvtMpActualPassageObservationUpdate:
    """One actual passage observation ready to assign. Not yet assigned."""

    vehicle: object
    updated_order_exchange_log: list
    wait_entry: OrderControlTvtMpActualPassageWaitEntry
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus
    target_trade_wait: OrderControlTvtMpActualPassageTradeWait
    should_emit_buyer_seller_completion_notification: bool


def prepare_tvt_mp_actual_passage_observation(
    *,
    node,
    vehicle,
    visit_key,
    actual_outlink,
    actual_passage_timestep,
):
    """
    Build one actual passage observation, or return None when no entry waits.

    This does not move the vehicle, append the live log, or change the wait
    entry. A missing registry entry is a normal confirmed visit outside the
    selected trade scope.
    """
    registry = node.W.order_control_tvt_mp_actual_passage_wait_registry
    if not isinstance(registry, OrderControlTvtMpActualPassageWaitRegistry):
        raise RuntimeError(
            f"Node {node.name!r}: actual passage wait registry must be "
            "OrderControlTvtMpActualPassageWaitRegistry; got type "
            f"{type(registry).__name__}."
        )
    entry_key = (node.name, visit_key)
    wait_entry = registry.entries_by_node_name_and_visit_key.get(entry_key)
    if wait_entry is None:
        return None

    _require_waiting_entry_identity(
        wait_entry,
        node_name=node.name,
        visit_key=visit_key,
        vehicle=vehicle,
    )
    checked_actual_timestep = _require_actual_passage_timestep(
        actual_passage_timestep,
        wait_entry.tvt_decision_timestep,
        node.name,
        visit_key,
    )
    baseline_passage_timestep = _require_baseline_passage_timestep(
        wait_entry.baseline_passage_timestep,
        node.name,
        visit_key,
    )
    candidate_passage_timestep = _require_candidate_passage_timestep(
        wait_entry.candidate_passage_timestep,
        node.name,
        visit_key,
    )
    deltat = _require_positive_deltat(node.W.DELTAT, node.name)
    true_vot_per_second = _require_frozen_true_vot(
        wait_entry.true_vot_per_second,
        node.name,
        visit_key,
    )
    actual_route_next_link_name = _require_actual_route_name(
        actual_outlink,
        node.name,
        visit_key,
    )
    (
        baseline_minus_actual_passage_timesteps,
        baseline_minus_actual_passage_seconds,
        baseline_minus_actual_time_value,
    ) = _passage_difference_from_saved_timestep(
        baseline_passage_timestep,
        checked_actual_timestep,
        deltat,
        true_vot_per_second,
    )
    if candidate_passage_timestep is None:
        candidate_minus_actual_passage_timesteps = None
        candidate_minus_actual_passage_seconds = None
        candidate_minus_actual_time_value = None
    else:
        (
            candidate_minus_actual_passage_timesteps,
            candidate_minus_actual_passage_seconds,
            candidate_minus_actual_time_value,
        ) = _passage_difference_from_saved_timestep(
            candidate_passage_timestep,
            checked_actual_timestep,
            deltat,
            true_vot_per_second,
        )

    # baseline_minus_candidate is already stored. Do not recompute it.
    actual_observation_record = OrderControlTvtMpActualPassageObservationRecord(
        tvt_decision_timestep=wait_entry.tvt_decision_timestep,
        node_name=wait_entry.node_name,
        buyers_sorted=wait_entry.buyers_sorted,
        visit_key=wait_entry.visit_key,
        vehicle_name=wait_entry.vehicle_name,
        role=wait_entry.role,
        observation_status=(
            OrderControlTvtMpActualPassageObservationStatus.ACTUAL_PASSAGE_OBSERVED
        ),
        baseline_passage_timestep=baseline_passage_timestep,
        candidate_passage_timestep=candidate_passage_timestep,
        true_vot_per_second=true_vot_per_second,
        predicted_observation_status=wait_entry.predicted_observation_status,
        predicted_route_next_link_name=wait_entry.predicted_route_next_link_name,
        baseline_minus_candidate_passage_timesteps=(
            wait_entry.baseline_minus_candidate_passage_timesteps
        ),
        baseline_minus_candidate_passage_seconds=(
            wait_entry.baseline_minus_candidate_passage_seconds
        ),
        baseline_minus_candidate_time_value=(
            wait_entry.baseline_minus_candidate_time_value
        ),
        baseline_minus_actual_passage_timesteps=(
            baseline_minus_actual_passage_timesteps
        ),
        baseline_minus_actual_passage_seconds=baseline_minus_actual_passage_seconds,
        baseline_minus_actual_time_value=baseline_minus_actual_time_value,
        candidate_minus_actual_passage_timesteps=(
            candidate_minus_actual_passage_timesteps
        ),
        candidate_minus_actual_passage_seconds=(
            candidate_minus_actual_passage_seconds
        ),
        candidate_minus_actual_time_value=candidate_minus_actual_time_value,
        actual_passage_timestep=checked_actual_timestep,
        actual_route_next_link_name=actual_route_next_link_name,
    )
    if not isinstance(vehicle.order_exchange_log, list):
        raise RuntimeError(
            f"Node {node.name!r}: Vehicle {vehicle.name!r} "
            "order_exchange_log must be a list; got type "
            f"{type(vehicle.order_exchange_log).__name__}."
        )
    updated_order_exchange_log = list(vehicle.order_exchange_log)
    updated_order_exchange_log.append(actual_observation_record)
    committed_wait_status = (
        OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    trade_wait, should_emit_notification = (
        _prepare_buyer_seller_completion_notification(
            registry=registry,
            node_name=node.name,
            visit_key=visit_key,
            wait_entry=wait_entry,
            actual_passage_observation_record=actual_observation_record,
            committed_wait_status=committed_wait_status,
        )
    )
    return _PreparedTvtMpActualPassageObservationUpdate(
        vehicle=vehicle,
        updated_order_exchange_log=updated_order_exchange_log,
        wait_entry=wait_entry,
        actual_passage_observation_record=actual_observation_record,
        committed_wait_status=committed_wait_status,
        target_trade_wait=trade_wait,
        should_emit_buyer_seller_completion_notification=should_emit_notification,
    )


def commit_tvt_mp_actual_passage_observation(
    prepared_update,
) -> OrderControlTvtMpActualPassageTradeWait | None:
    """Assign one prepared observation. No search, check, or recalculation."""
    prepared_update.vehicle.order_exchange_log = (
        prepared_update.updated_order_exchange_log
    )
    prepared_update.wait_entry.actual_passage_observation_record = (
        prepared_update.actual_passage_observation_record
    )
    prepared_update.wait_entry.wait_status = prepared_update.committed_wait_status
    if not prepared_update.should_emit_buyer_seller_completion_notification:
        return None
    prepared_update.target_trade_wait.buyer_seller_actual_passage_completion_notified = (
        True
    )
    return prepared_update.target_trade_wait


def _require_waiting_entry_identity(
    wait_entry,
    *,
    node_name,
    visit_key,
    vehicle,
) -> None:
    if wait_entry.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: wait entry node_name "
            f"{wait_entry.node_name!r} does not match."
        )
    if wait_entry.visit_key != visit_key:
        raise RuntimeError(
            f"Node {node_name!r}: wait entry VisitKey {wait_entry.visit_key!r} "
            f"does not match {visit_key!r}."
        )
    if wait_entry.vehicle_name != vehicle.name:
        raise RuntimeError(
            f"Node {node_name!r}: wait entry vehicle_name "
            f"{wait_entry.vehicle_name!r} does not match {vehicle.name!r}."
        )
    if (
        wait_entry.wait_status
        is not OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    ):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} wait_status is "
            f"{wait_entry.wait_status!r}, not WAITING_FOR_ACTUAL_PASSAGE."
        )
    if wait_entry.actual_passage_observation_record is not None:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} already has an "
            "actual passage observation record."
        )


def _require_actual_passage_timestep(
    value,
    decision_timestep,
    node_name,
    visit_key,
) -> int:
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "actual_passage_timestep must be a Python int, not bool; got "
            f"{value!r}."
        )
    if type(decision_timestep) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "tvt_decision_timestep must be a Python int, not bool; got "
            f"{decision_timestep!r}."
        )
    if value < decision_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            f"actual_passage_timestep {value!r} is before "
            f"tvt_decision_timestep {decision_timestep!r}."
        )
    return value


def _require_baseline_passage_timestep(value, node_name, visit_key) -> int:
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "baseline_passage_timestep must be a Python int, not bool; got "
            f"{value!r}."
        )
    return value


def _require_candidate_passage_timestep(value, node_name, visit_key):
    if value is None:
        return None
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} "
            "candidate_passage_timestep must be a Python int or None; got "
            f"{value!r}."
        )
    return value


def _require_positive_deltat(value, node_name):
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: DELTAT must be a Python int or float, not "
            f"bool or None; got {value!r}."
        )
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(
            f"Node {node_name!r}: DELTAT must be finite and > 0; got {value!r}."
        )
    return value


def _require_frozen_true_vot(value, node_name, visit_key):
    """Use the value stored on the wait entry. Do not read Vehicle.vot_true."""
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} true_vot_per_second "
            f"must be a Python int or float, not bool or None; got {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} true_vot_per_second "
            f"must be finite and >= 0; got {value!r}."
        )
    return value


def _require_actual_route_name(actual_outlink, node_name, visit_key) -> str:
    route_name = getattr(actual_outlink, "name", None)
    if not isinstance(route_name, str) or route_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} actual outlink name "
            f"must be a non-empty str; got {route_name!r}."
        )
    return route_name


def _passage_difference_from_saved_timestep(
    earlier_saved_timestep,
    actual_passage_timestep,
    deltat,
    true_vot_per_second,
):
    """saved timestep minus actual timestep, then seconds and time value."""
    passage_timesteps = earlier_saved_timestep - actual_passage_timestep
    passage_seconds = passage_timesteps * deltat
    time_value = passage_seconds * true_vot_per_second
    return passage_timesteps, passage_seconds, time_value


def _transaction_key_from_wait_entry(
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
) -> tuple[int, str, tuple[OrderControlTvtVisitKey, ...]]:
    return (
        wait_entry.tvt_decision_timestep,
        wait_entry.node_name,
        wait_entry.buyers_sorted,
    )


def _prepare_buyer_seller_completion_notification(
    *,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord,
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus,
) -> tuple[OrderControlTvtMpActualPassageTradeWait, bool]:
    transaction_key = _transaction_key_from_wait_entry(wait_entry)
    trade_wait = registry.trades_by_transaction_key.get(transaction_key)
    if trade_wait is None:
        raise RuntimeError(
            f"Node {node_name!r}: no TradeWait for transaction key "
            f"{transaction_key!r}."
        )
    _validate_trade_wait_matches_wait_entry(trade_wait, wait_entry, node_name)
    _validate_trade_wait_buyer_seller_visit_keys(trade_wait, node_name)
    _validate_current_visit_trade_membership(
        trade_wait,
        wait_entry,
        node_name,
        visit_key,
    )
    _validate_role_visit_keys_for_trade(
        registry,
        trade_wait,
        node_name,
    )
    _validate_saved_wait_entries_for_trade(
        registry,
        trade_wait,
        node_name,
        current_visit_key=visit_key,
    )
    all_buyer_seller_complete_after_commit = (
        _all_buyer_seller_visits_complete_after_commit(
            trade_wait,
            registry,
            node_name,
            current_visit_key=visit_key,
            actual_passage_observation_record=actual_passage_observation_record,
            committed_wait_status=committed_wait_status,
        )
    )
    _validate_completion_flag_consistency(
        trade_wait,
        registry,
        node_name,
        wait_entry,
    )
    should_emit = (
        all_buyer_seller_complete_after_commit
        and not trade_wait.buyer_seller_actual_passage_completion_notified
    )
    return trade_wait, should_emit


def _validate_trade_wait_matches_wait_entry(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
) -> None:
    if trade_wait.tvt_decision_timestep != wait_entry.tvt_decision_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait tvt_decision_timestep "
            f"{trade_wait.tvt_decision_timestep!r} does not match wait entry "
            f"{wait_entry.tvt_decision_timestep!r}."
        )
    if trade_wait.node_name != wait_entry.node_name:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait node_name {trade_wait.node_name!r} "
            f"does not match wait entry {wait_entry.node_name!r}."
        )
    if trade_wait.buyers_sorted != wait_entry.buyers_sorted:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait buyers_sorted does not match "
            "wait entry buyers_sorted."
        )


def _validate_trade_wait_buyer_seller_visit_keys(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    node_name: str,
) -> None:
    if len(trade_wait.buyer_visit_keys) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait buyer_visit_keys must not be empty."
        )
    if len(trade_wait.seller_visit_keys) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait seller_visit_keys must not be empty."
        )
    duplicate_buyer_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.buyer_visit_keys,
    )
    if duplicate_buyer_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait buyer_visit_keys contains duplicate "
            f"VisitKey {duplicate_buyer_visit_key!r}."
        )
    duplicate_seller_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.seller_visit_keys,
    )
    if duplicate_seller_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait seller_visit_keys contains duplicate "
            f"VisitKey {duplicate_seller_visit_key!r}."
        )
    duplicate_nonparticipating_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.nonparticipating_visit_keys,
    )
    if duplicate_nonparticipating_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait nonparticipating_visit_keys contains "
            f"duplicate VisitKey {duplicate_nonparticipating_visit_key!r}."
        )
    duplicate_all_visit_key = _find_duplicate_visit_key_in_sequence(
        trade_wait.all_visit_keys,
    )
    if duplicate_all_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait all_visit_keys contains duplicate "
            f"VisitKey {duplicate_all_visit_key!r}."
        )
    shared_buyer_seller_visit_key = _find_shared_visit_key_between_sequences(
        trade_wait.buyer_visit_keys,
        trade_wait.seller_visit_keys,
    )
    if shared_buyer_seller_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait has VisitKey shared by buyer and "
            f"seller role lists: {shared_buyer_seller_visit_key!r}."
        )
    shared_buyer_nonparticipating_visit_key = _find_shared_visit_key_between_sequences(
        trade_wait.buyer_visit_keys,
        trade_wait.nonparticipating_visit_keys,
    )
    if shared_buyer_nonparticipating_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait has VisitKey shared by buyer and "
            "nonparticipating role lists: "
            f"{shared_buyer_nonparticipating_visit_key!r}."
        )
    shared_seller_nonparticipating_visit_key = _find_shared_visit_key_between_sequences(
        trade_wait.seller_visit_keys,
        trade_wait.nonparticipating_visit_keys,
    )
    if shared_seller_nonparticipating_visit_key is not None:
        raise RuntimeError(
            f"Node {node_name!r}: TradeWait has VisitKey shared by seller and "
            "nonparticipating role lists: "
            f"{shared_seller_nonparticipating_visit_key!r}."
        )
    for visit_key in trade_wait.buyer_visit_keys:
        if not _visit_key_listed_in_sequence(visit_key, trade_wait.all_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait buyer VisitKey {visit_key!r} is "
                "not listed in all_visit_keys."
            )
    for visit_key in trade_wait.seller_visit_keys:
        if not _visit_key_listed_in_sequence(visit_key, trade_wait.all_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait seller VisitKey {visit_key!r} is "
                "not listed in all_visit_keys."
            )
    for visit_key in trade_wait.nonparticipating_visit_keys:
        if not _visit_key_listed_in_sequence(visit_key, trade_wait.all_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait nonparticipating VisitKey "
                f"{visit_key!r} is not listed in all_visit_keys."
            )
    for visit_key in trade_wait.all_visit_keys:
        in_buyer_visit_keys = _visit_key_listed_in_sequence(
            visit_key,
            trade_wait.buyer_visit_keys,
        )
        in_seller_visit_keys = _visit_key_listed_in_sequence(
            visit_key,
            trade_wait.seller_visit_keys,
        )
        in_nonparticipating_visit_keys = _visit_key_listed_in_sequence(
            visit_key,
            trade_wait.nonparticipating_visit_keys,
        )
        role_list_count = 0
        if in_buyer_visit_keys:
            role_list_count += 1
        if in_seller_visit_keys:
            role_list_count += 1
        if in_nonparticipating_visit_keys:
            role_list_count += 1
        if role_list_count == 0:
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait all_visit_keys contains VisitKey "
                f"{visit_key!r} that is not listed in buyer_visit_keys, "
                "seller_visit_keys, or nonparticipating_visit_keys."
            )


def _find_duplicate_visit_key_in_sequence(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    for visit_key in visit_keys:
        if visit_key in seen_visit_keys:
            return visit_key
        seen_visit_keys.add(visit_key)
    return None


def _find_shared_visit_key_between_sequences(
    left_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    right_visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtVisitKey | None:
    for left_visit_key in left_visit_keys:
        if _visit_key_listed_in_sequence(left_visit_key, right_visit_keys):
            return left_visit_key
    return None


def _visit_key_listed_in_sequence(
    visit_key: OrderControlTvtVisitKey,
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> bool:
    for listed_visit_key in visit_keys:
        if listed_visit_key == visit_key:
            return True
    return False


def _validate_current_visit_trade_membership(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    if visit_key not in trade_wait.all_visit_keys:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is not listed in "
            "TradeWait all_visit_keys."
        )
    role = wait_entry.role
    if role is OrderControlTvtMpActualPassageRole.BUYER:
        if visit_key not in trade_wait.buyer_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {visit_key!r} is not in "
                "TradeWait buyer_visit_keys."
            )
        return
    if role is OrderControlTvtMpActualPassageRole.SELLER:
        if visit_key not in trade_wait.seller_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: seller VisitKey {visit_key!r} is not in "
                "TradeWait seller_visit_keys."
            )
        return
    if role is OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        if visit_key not in trade_wait.nonparticipating_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: nonparticipating VisitKey {visit_key!r} "
                "is not in TradeWait nonparticipating_visit_keys."
            )
        return
    raise RuntimeError(
        f"Node {node_name!r}: VisitKey {visit_key!r} has unknown role "
        f"{role!r}."
    )


def _validate_role_visit_keys_for_trade(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    node_name: str,
) -> None:
    for visit_key in trade_wait.buyer_visit_keys:
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="buyer",
        )
        if entry.role is not OrderControlTvtMpActualPassageRole.BUYER:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is listed as "
                "buyer but wait entry role is not BUYER."
            )
    for visit_key in trade_wait.seller_visit_keys:
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="seller",
        )
        if entry.role is not OrderControlTvtMpActualPassageRole.SELLER:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is listed as "
                "seller but wait entry role is not SELLER."
            )


def _require_wait_entry_for_visit_key(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
    *,
    role_label: str,
) -> OrderControlTvtMpActualPassageWaitEntry:
    entry = registry.entries_by_node_name_and_visit_key.get((node_name, visit_key))
    if entry is None:
        raise RuntimeError(
            f"Node {node_name!r}: no WaitEntry for {role_label} VisitKey "
            f"{visit_key!r}."
        )
    return entry


def _validate_saved_wait_entries_for_trade(
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    node_name: str,
    *,
    current_visit_key: OrderControlTvtVisitKey,
) -> None:
    for visit_key in trade_wait.buyer_visit_keys + trade_wait.seller_visit_keys:
        if visit_key == current_visit_key:
            continue
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="buyer or seller",
        )
        _validate_wait_entry_identity_matches_trade(trade_wait, entry, node_name)
        _validate_saved_wait_entry_observation_consistency(
            entry,
            node_name,
            visit_key,
        )


def _validate_wait_entry_identity_matches_trade(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
) -> None:
    if entry.tvt_decision_timestep != trade_wait.tvt_decision_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: WaitEntry transaction identity "
            "tvt_decision_timestep does not match TradeWait."
        )
    if entry.node_name != trade_wait.node_name:
        raise RuntimeError(
            f"Node {node_name!r}: WaitEntry transaction identity node_name "
            "does not match TradeWait."
        )
    if entry.buyers_sorted != trade_wait.buyers_sorted:
        raise RuntimeError(
            f"Node {node_name!r}: WaitEntry transaction identity buyers_sorted "
            "does not match TradeWait."
        )


def _validate_saved_wait_entry_observation_consistency(
    entry: OrderControlTvtMpActualPassageWaitEntry,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    observed = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
    )
    has_record = entry.actual_passage_observation_record is not None
    waiting = (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.WAITING_FOR_ACTUAL_PASSAGE
    )
    if observed and not has_record:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is "
            "ACTUAL_PASSAGE_OBSERVED but has no actual passage observation "
            "record."
        )
    if waiting and has_record:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey {visit_key!r} is "
            "WAITING_FOR_ACTUAL_PASSAGE but already has an actual passage "
            "observation record."
        )


def _all_buyer_seller_visits_complete_after_commit(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    *,
    current_visit_key: OrderControlTvtVisitKey,
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord,
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus,
) -> bool:
    for visit_key in trade_wait.buyer_visit_keys:
        if not _visit_complete_after_commit(
            visit_key,
            registry,
            node_name,
            current_visit_key=current_visit_key,
            actual_passage_observation_record=actual_passage_observation_record,
            committed_wait_status=committed_wait_status,
        ):
            return False
    for visit_key in trade_wait.seller_visit_keys:
        if not _visit_complete_after_commit(
            visit_key,
            registry,
            node_name,
            current_visit_key=current_visit_key,
            actual_passage_observation_record=actual_passage_observation_record,
            committed_wait_status=committed_wait_status,
        ):
            return False
    return True


def _all_buyer_seller_visits_complete_on_live_state(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
) -> bool:
    for visit_key in trade_wait.buyer_visit_keys + trade_wait.seller_visit_keys:
        entry = _require_wait_entry_for_visit_key(
            registry,
            node_name,
            visit_key,
            role_label="buyer or seller",
        )
        if (
            entry.wait_status
            is not OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
            or entry.actual_passage_observation_record is None
        ):
            return False
    return True


def _visit_complete_after_commit(
    visit_key: OrderControlTvtVisitKey,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    *,
    current_visit_key: OrderControlTvtVisitKey,
    actual_passage_observation_record: OrderControlTvtMpActualPassageObservationRecord,
    committed_wait_status: OrderControlTvtMpActualPassageWaitStatus,
) -> bool:
    if visit_key == current_visit_key:
        return (
            committed_wait_status
            is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
            and actual_passage_observation_record is not None
        )
    entry = _require_wait_entry_for_visit_key(
        registry,
        node_name,
        visit_key,
        role_label="buyer or seller",
    )
    return (
        entry.wait_status
        is OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
        and entry.actual_passage_observation_record is not None
    )


def _validate_completion_flag_consistency(
    trade_wait: OrderControlTvtMpActualPassageTradeWait,
    registry: OrderControlTvtMpActualPassageWaitRegistry,
    node_name: str,
    wait_entry: OrderControlTvtMpActualPassageWaitEntry,
) -> None:
    if trade_wait.buyer_seller_actual_passage_completion_notified:
        all_buyer_seller_complete_on_live_state = (
            _all_buyer_seller_visits_complete_on_live_state(
                trade_wait,
                registry,
                node_name,
            )
        )
        if not all_buyer_seller_complete_on_live_state:
            raise RuntimeError(
                f"Node {node_name!r}: TradeWait completion flag is True but "
                "buyer and seller are not all complete on live saved state "
                "before this commit."
            )
    if wait_entry.role is not OrderControlTvtMpActualPassageRole.NONPARTICIPATING:
        return
    all_buyer_seller_already_complete = (
        _all_buyer_seller_visits_complete_on_live_state(
            trade_wait,
            registry,
            node_name,
        )
    )
    if (
        all_buyer_seller_already_complete
        and not trade_wait.buyer_seller_actual_passage_completion_notified
    ):
        raise RuntimeError(
            f"Node {node_name!r}: buyer and seller are already complete but "
            "TradeWait completion flag is still False during nonparticipating "
            "passage."
        )
