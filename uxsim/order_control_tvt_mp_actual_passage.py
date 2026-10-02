from __future__ import annotations

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
