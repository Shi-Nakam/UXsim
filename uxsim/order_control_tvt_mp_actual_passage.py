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
    actual_passage_observation_record: (
        OrderControlTvtMpActualPassageObservationRecord | None
    ) = None


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
    return _PreparedTvtMpActualPassageObservationUpdate(
        vehicle=vehicle,
        updated_order_exchange_log=updated_order_exchange_log,
        wait_entry=wait_entry,
        actual_passage_observation_record=actual_observation_record,
        committed_wait_status=(
            OrderControlTvtMpActualPassageWaitStatus.ACTUAL_PASSAGE_OBSERVED
        ),
    )


def commit_tvt_mp_actual_passage_observation(prepared_update) -> None:
    """Assign one prepared observation. No search, check, or recalculation."""
    prepared_update.vehicle.order_exchange_log = (
        prepared_update.updated_order_exchange_log
    )
    prepared_update.wait_entry.actual_passage_observation_record = (
        prepared_update.actual_passage_observation_record
    )
    prepared_update.wait_entry.wait_status = prepared_update.committed_wait_status


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
