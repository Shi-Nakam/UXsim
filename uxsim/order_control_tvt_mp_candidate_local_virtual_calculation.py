"""
One-candidate TVT-MP local virtual calculation orchestrating loop.

This module runs the already implemented local parts in the adopted order
for one concrete buyer candidate. It does not enumerate candidates, score
economics, write the rank ledger, or change the real World.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferScanResult,
    OrderControlTvtMpBindingTransferStopReason,
    OrderControlTvtMpBindingVisitTemporarySkipReason,
    OrderControlTvtMpCandidateBindingTransferState,
    initialize_tvt_mp_candidate_binding_transfer_state,
    scan_and_transfer_tvt_mp_binding_visits_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    OrderControlTvtMpCandidateLocalState,
)
from uxsim.order_control_tvt_mp_candidate_local_vehicle_advance import (
    OrderControlTvtMpCandidateLocalVehicleAdvanceState,
    OrderControlTvtMpLocalVehicleAdvanceResult,
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals,
    initialize_tvt_mp_candidate_local_vehicle_advance_state,
)
from uxsim.order_control_tvt_mp_candidate_outlink_boundary import (
    OrderControlTvtMpCandidateOutlinkBoundaryState,
    OrderControlTvtMpOutlinkBoundaryMode,
    OrderControlTvtMpOutlinkBoundaryProcessResult,
    initialize_tvt_mp_candidate_outlink_boundary_state,
    process_tvt_mp_candidate_outlink_boundaries_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_unbound_fcfs_transfer import (
    OrderControlTvtMpCandidateUnboundFcfsTransferState,
    OrderControlTvtMpUnboundFcfsTransferResult,
    OrderControlTvtMpUnboundTemporarySkipReason,
    initialize_tvt_mp_candidate_unbound_fcfs_transfer_state,
    scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep,
)
from uxsim.order_control_tvt_mp_candidate_virtual_time import (
    OrderControlTvtMpCandidateVirtualTimeState,
    advance_tvt_mp_candidate_virtual_time_one_step,
    initialize_tvt_mp_candidate_virtual_time_state,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingPartition,
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
    OrderControlTvtMpLocalBindingRouteOrigin,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


class OrderControlTvtMpCandidateLocalVirtualCalculationStopReason(Enum):
    """Why one candidate's local virtual calculation stopped."""

    RESOLVED = "resolved"
    HORIZON_EXHAUSTED_UNRESOLVED = "horizon_exhausted_unresolved"


class OrderControlTvtMpCandidateUnresolvedReason(Enum):
    """Observed facts recorded when the horizon ends without required passages."""

    REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON = (
        "required_buyer_or_seller_did_not_pass_within_horizon"
    )
    DOWNSTREAM_BOUNDARY_REMAINED_BLOCKED_WITHIN_HORIZON = (
        "downstream_boundary_remained_blocked_within_horizon"
    )
    DOWNSTREAM_BOUNDARY_HAD_WAITING_VEHICLES_BUT_NO_TRANSFER = (
        "downstream_boundary_had_waiting_vehicles_but_no_transfer"
    )
    CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON = (
        "clearance_or_capacity_blocked_through_horizon"
    )
    NO_ACCEPTABLE_OUTLINK_FOR_ROUTE_UNDETERMINED_VEHICLE_WITHIN_HORIZON = (
        "no_acceptable_outlink_for_route_undetermined_vehicle_within_horizon"
    )
    DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION = (
        "downstream_boundary_prevented_required_passage_information"
    )


class OrderControlTvtMpCandidateFinalLinkRole(Enum):
    """Whether a saved link is a target inlink or a target outlink."""

    TARGET_INLINK = "target_inlink"
    TARGET_OUTLINK = "target_outlink"


class OrderControlTvtMpCandidatePassageObservationStatus(Enum):
    """Whether one trade-scope visit's candidate passage was observed.

    Initialization leaves the record status as None. A later final-result
    build chooses OBSERVED or UNOBSERVED_AT_HORIZON. This slice does not
    choose it.
    """

    OBSERVED = "observed"
    UNOBSERVED_AT_HORIZON = "unobserved_at_horizon"


@dataclass(frozen=True)
class OrderControlTvtMpCandidateClearanceScanStopContext:
    """One binding scan that stopped for unmet clearance.

    Clearance is not a per-visit temporary skip. This record is the type a
    later timestep update will store. This slice only defines it.
    """

    virtual_timestep: int
    offset: int
    stopped_binding_visit_key: OrderControlTvtVisitKey


@dataclass(frozen=True)
class OrderControlTvtMpCandidateTrafficObservationRecord:
    """One trade-scope visit prepared for later candidate-passage observation.

    Buyer, seller, and nonparticipating visits use this same frozen record.
    Partition 1, partition 2, and outside-trade-scope visits are not stored.
    """

    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    vehicle_id: int
    trade_role: OrderControlTvtMpLocalBindingTradeRole
    binding_partition: OrderControlTvtMpLocalBindingPartition
    binding_rank: int
    trade_scope_rank: int
    inlink_name: str
    route_next_link_name: str
    true_vot_per_second: float
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    passage_observation_status: (
        OrderControlTvtMpCandidatePassageObservationStatus | None
    )
    observed_offset: int | None
    observed_virtual_timestep: int | None
    predicted_time_difference_timesteps: int | None
    predicted_time_difference_seconds: int | float | None
    predicted_signed_time_value_change: int | float | None
    last_checked_offset: int | None
    last_checked_virtual_timestep: int | None
    last_temporary_skip_reason: OrderControlTvtMpBindingVisitTemporarySkipReason | None
    last_temporary_skip_offset: int | None
    latest_clearance_stop_context: (
        OrderControlTvtMpCandidateClearanceScanStopContext | None
    )
    horizon_exhausted: bool | None
    observation_complete: bool | None


# Binding skips that count as ordinary capacity or physical inability.
_CAPACITY_OR_PHYSICAL_SKIP_REASONS = (
    OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD,
    OrderControlTvtMpBindingVisitTemporarySkipReason.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE,
    OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE,
    OrderControlTvtMpBindingVisitTemporarySkipReason.NODE_FLOW_CAPACITY_UNAVAILABLE,
    OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE,
)


@dataclass(frozen=True)
class OrderControlTvtMpCandidatePassageRecord:
    """One required buyer or seller visit and its baseline/candidate passage times."""

    visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    trade_role: OrderControlTvtMpLocalBindingTradeRole
    binding_partition: OrderControlTvtMpLocalBindingPartition
    binding_rank: int
    baseline_passage_timestep: int | None
    candidate_passage_timestep: int | None
    route_next_link_name: str
    route_origin: OrderControlTvtMpLocalBindingRouteOrigin
    inlink_name: str


@dataclass(frozen=True)
class OrderControlTvtMpCandidateVirtualTimestepResult:
    """What one virtual traffic timestep did, after all seven steps."""

    node_name: str
    virtual_timestep: int
    offset: int
    binding_transfer_result: OrderControlTvtMpBindingTransferScanResult
    unbound_fcfs_result: OrderControlTvtMpUnboundFcfsTransferResult
    newly_recorded_required_passage_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    local_vehicle_advance_result: OrderControlTvtMpLocalVehicleAdvanceResult
    outlink_boundary_result: OrderControlTvtMpOutlinkBoundaryProcessResult
    required_passages_complete_after_node_passage: bool
    calculation_finished_after_timestep_end: bool
    resolved_after_timestep_end: bool


@dataclass(frozen=True)
class OrderControlTvtMpCandidateFinalVehicleRecord:
    """One vehicle still on a target inlink, outlink, or the target incoming list."""

    vehicle_name: str
    current_link_name: str | None
    position_x: int | float | None
    state: str
    current_visit_key: OrderControlTvtVisitKey | None
    current_visit_node_name: str | None


@dataclass(frozen=True)
class OrderControlTvtMpCandidateFinalLinkRecord:
    """One target inlink or outlink at the last processed timestep end."""

    link_name: str
    start_node_name: str
    end_node_name: str
    link_role: OrderControlTvtMpCandidateFinalLinkRole
    vehicle_names_in_physical_order: tuple[str, ...]
    capacity_out_remain: int | float
    capacity_in_remain: int | float


@dataclass(frozen=True)
class OrderControlTvtMpCandidateFinalNodeRecord:
    """The target Node at the last processed timestep end."""

    node_name: str
    incoming_vehicle_names: tuple[str, ...]
    flow_capacity_remain: int | float
    last_order_control_inlink_name: str | None
    last_order_control_entry_timestep: int | None
    order_control_clearance_timesteps: int


@dataclass(frozen=True)
class OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord:
    """One outlink terminal after the last processed boundary step."""

    outlink_name: str
    terminal_node_name: str
    boundary_mode: OrderControlTvtMpOutlinkBoundaryMode
    observed_average_outflow_rate: int | float | None
    flow_allowance_after: int | float
    waiting_vehicle_names_after: tuple[str, ...]
    capacity_out_remain_after: int | float
    terminal_node_flow_capacity_remain_after: int | float
    cumulative_observed_outflow_exit_vehicle_names: tuple[str, ...]
    cumulative_constrained_sink_end_trip_vehicle_names: tuple[str, ...]


@dataclass(frozen=True)
class OrderControlTvtMpCandidateLocalVirtualCalculationResult:
    """Frozen one-candidate result. It does not keep live traffic objects."""

    node_name: str
    concrete_buyer_candidate_set: OrderControlTvtMpConcreteBuyerCandidateSet
    binding_rank_sequence: OrderControlTvtMpLocalBindingRankSequence
    baseline_timestep_T: int
    configured_horizon_steps: int
    final_virtual_timestep: int
    final_offset: int
    simulated_timestep_count: int
    stop_reason: OrderControlTvtMpCandidateLocalVirtualCalculationStopReason
    resolved: bool
    required_passage_records: tuple[OrderControlTvtMpCandidatePassageRecord, ...]
    unresolved_reasons: tuple[OrderControlTvtMpCandidateUnresolvedReason, ...]
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...]
    final_vehicle_records: tuple[OrderControlTvtMpCandidateFinalVehicleRecord, ...]
    final_inlink_records: tuple[OrderControlTvtMpCandidateFinalLinkRecord, ...]
    final_outlink_records: tuple[OrderControlTvtMpCandidateFinalLinkRecord, ...]
    final_node_record: OrderControlTvtMpCandidateFinalNodeRecord
    final_boundary_records: tuple[
        OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord,
        ...,
    ]


class OrderControlTvtMpCandidateLocalVirtualCalculationState:
    """Mutable orchestrating state for one candidate local virtual calculation.

    Public sequences are returned as tuples. The internal passage map is not
    published as a dict.
    """

    def __init__(
        self,
        *,
        candidate_local_state: OrderControlTvtMpCandidateLocalState,
        virtual_time_state: OrderControlTvtMpCandidateVirtualTimeState,
        binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
        unbound_fcfs_transfer_state: OrderControlTvtMpCandidateUnboundFcfsTransferState,
        local_vehicle_advance_state: OrderControlTvtMpCandidateLocalVehicleAdvanceState,
        outlink_boundary_state: OrderControlTvtMpCandidateOutlinkBoundaryState,
        configured_horizon_steps: int,
        required_buyer_visit_keys: tuple[OrderControlTvtVisitKey, ...],
        required_seller_visit_keys: tuple[OrderControlTvtVisitKey, ...],
        passage_records_in_public_order: list[OrderControlTvtMpCandidatePassageRecord],
        traffic_observation_records_in_public_order: list[
            OrderControlTvtMpCandidateTrafficObservationRecord
        ],
    ) -> None:
        self._candidate_local_state = candidate_local_state
        self._virtual_time_state = virtual_time_state
        self._binding_transfer_state = binding_transfer_state
        self._unbound_fcfs_transfer_state = unbound_fcfs_transfer_state
        self._local_vehicle_advance_state = local_vehicle_advance_state
        self._outlink_boundary_state = outlink_boundary_state
        self._configured_horizon_steps = configured_horizon_steps
        self._required_buyer_visit_keys = required_buyer_visit_keys
        self._required_seller_visit_keys = required_seller_visit_keys
        self._passage_records_in_public_order = passage_records_in_public_order
        self._passage_record_by_visit_key: dict[
            OrderControlTvtVisitKey,
            OrderControlTvtMpCandidatePassageRecord,
        ] = {}
        for record in passage_records_in_public_order:
            self._passage_record_by_visit_key[record.visit_key] = record
        self._traffic_observation_records_in_public_order = (
            traffic_observation_records_in_public_order
        )
        self._traffic_observation_record_by_visit_key: dict[
            OrderControlTvtVisitKey,
            OrderControlTvtMpCandidateTrafficObservationRecord,
        ] = {}
        for record in traffic_observation_records_in_public_order:
            self._traffic_observation_record_by_visit_key[record.visit_key] = record
        self._economic_required_passages_complete_offset: int | None = None
        self._economic_required_passages_complete_virtual_timestep: int | None = None
        self._all_trade_scope_passages_complete_offset: int | None = None
        self._all_trade_scope_passages_complete_virtual_timestep: int | None = None
        self._completed_virtual_timesteps: list[int] = []
        self._timestep_results: list[OrderControlTvtMpCandidateVirtualTimestepResult] = []
        self._finished = False
        self._final_result: (
            OrderControlTvtMpCandidateLocalVirtualCalculationResult | None
        ) = None

    @property
    def candidate_local_state(self) -> OrderControlTvtMpCandidateLocalState:
        return self._candidate_local_state

    @property
    def virtual_time_state(self) -> OrderControlTvtMpCandidateVirtualTimeState:
        return self._virtual_time_state

    @property
    def binding_transfer_state(self) -> OrderControlTvtMpCandidateBindingTransferState:
        return self._binding_transfer_state

    @property
    def unbound_fcfs_transfer_state(
        self,
    ) -> OrderControlTvtMpCandidateUnboundFcfsTransferState:
        return self._unbound_fcfs_transfer_state

    @property
    def local_vehicle_advance_state(
        self,
    ) -> OrderControlTvtMpCandidateLocalVehicleAdvanceState:
        return self._local_vehicle_advance_state

    @property
    def outlink_boundary_state(self) -> OrderControlTvtMpCandidateOutlinkBoundaryState:
        return self._outlink_boundary_state

    @property
    def configured_horizon_steps(self) -> int:
        return self._configured_horizon_steps

    @property
    def required_buyer_visit_keys(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._required_buyer_visit_keys

    @property
    def required_seller_visit_keys(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._required_seller_visit_keys

    @property
    def required_passage_records(
        self,
    ) -> tuple[OrderControlTvtMpCandidatePassageRecord, ...]:
        return tuple(self._passage_records_in_public_order)

    @property
    def completed_virtual_timesteps(self) -> tuple[int, ...]:
        return tuple(self._completed_virtual_timesteps)

    @property
    def timestep_results(
        self,
    ) -> tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...]:
        return tuple(self._timestep_results)

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def final_result(
        self,
    ) -> OrderControlTvtMpCandidateLocalVirtualCalculationResult | None:
        return self._final_result

    @property
    def traffic_observation_records_in_public_order(
        self,
    ) -> tuple[OrderControlTvtMpCandidateTrafficObservationRecord, ...]:
        return tuple(self._traffic_observation_records_in_public_order)

    @property
    def traffic_observation_record_by_visit_key(
        self,
    ) -> tuple[
        tuple[OrderControlTvtVisitKey, OrderControlTvtMpCandidateTrafficObservationRecord],
        ...,
    ]:
        """VisitKey pairs in public order. The internal dict is not returned."""
        pairs: list[
            tuple[OrderControlTvtVisitKey, OrderControlTvtMpCandidateTrafficObservationRecord]
        ] = []
        for record in self._traffic_observation_records_in_public_order:
            pairs.append((record.visit_key, record))
        return tuple(pairs)

    def traffic_observation_record_for_visit_key(
        self,
        visit_key: OrderControlTvtVisitKey,
    ) -> OrderControlTvtMpCandidateTrafficObservationRecord:
        record = self._traffic_observation_record_by_visit_key.get(visit_key)
        if record is None:
            raise RuntimeError(
                f"Node {self.candidate_local_state.target_node_name!r}: "
                f"VisitKey {visit_key!r} has no traffic observation record."
            )
        return record

    @property
    def economic_required_passages_complete_offset(self) -> int | None:
        return self._economic_required_passages_complete_offset

    @property
    def economic_required_passages_complete_virtual_timestep(self) -> int | None:
        return self._economic_required_passages_complete_virtual_timestep

    @property
    def all_trade_scope_passages_complete_offset(self) -> int | None:
        return self._all_trade_scope_passages_complete_offset

    @property
    def all_trade_scope_passages_complete_virtual_timestep(self) -> int | None:
        return self._all_trade_scope_passages_complete_virtual_timestep


def initialize_tvt_mp_candidate_local_virtual_calculation_state(
    candidate_local_state,
    baseline_collector,
    downstream_boundary_node_result,
    configured_horizon_steps,
) -> OrderControlTvtMpCandidateLocalVirtualCalculationState:
    """Create orchestrating state at T without moving traffic."""
    _require_candidate_local_state(candidate_local_state)
    _require_baseline_collector(baseline_collector)
    configured_horizon = _require_configured_horizon_steps(configured_horizon_steps)
    if downstream_boundary_node_result is None:
        raise RuntimeError(
            "downstream boundary result is missing. An empty baseline is "
            "not an observed active count of zero."
        )
    if not isinstance(
        downstream_boundary_node_result,
        OrderControlBaselineDownstreamBoundaryNodeResult,
    ):
        raise ValueError(
            "downstream_boundary_node_result must be "
            "OrderControlBaselineDownstreamBoundaryNodeResult; got "
            f"type {type(downstream_boundary_node_result).__name__}."
        )

    sequence = candidate_local_state.binding_rank_sequence
    node_name = candidate_local_state.target_node_name
    _require_node_names_match(
        candidate_local_state=candidate_local_state,
        downstream_boundary_node_result=downstream_boundary_node_result,
    )
    _require_timesteps_match(candidate_local_state)
    _require_downstream_outlinks_match(
        candidate_local_state,
        downstream_boundary_node_result,
    )
    visit_by_key = _visit_map_in_binding_order(sequence)
    _require_buyer_and_seller_roles_only_in_trade_scope(sequence)
    required_buyer_visit_keys = _required_buyer_visit_keys(sequence, visit_by_key)
    required_seller_visit_keys = _required_seller_visit_keys(sequence, visit_by_key)
    _require_no_buyer_seller_overlap(
        required_buyer_visit_keys,
        required_seller_visit_keys,
        node_name=node_name,
    )
    _require_required_visits_have_collector_snapshots(
        baseline_collector,
        node_name,
        required_buyer_visit_keys,
        required_seller_visit_keys,
        visit_by_key,
    )
    passage_records = _initial_passage_records(
        baseline_collector=baseline_collector,
        node_name=node_name,
        required_buyer_visit_keys=required_buyer_visit_keys,
        required_seller_visit_keys=required_seller_visit_keys,
        visit_by_key=visit_by_key,
    )
    traffic_observation_records = _initial_traffic_observation_records(
        candidate_local_state=candidate_local_state,
        baseline_collector=baseline_collector,
        node_name=node_name,
    )

    virtual_time_state = initialize_tvt_mp_candidate_virtual_time_state(
        candidate_local_state
    )
    binding_transfer_state = initialize_tvt_mp_candidate_binding_transfer_state(
        virtual_time_state
    )
    unbound_fcfs_transfer_state = (
        initialize_tvt_mp_candidate_unbound_fcfs_transfer_state(
            binding_transfer_state,
            baseline_collector,
        )
    )
    local_vehicle_advance_state = (
        initialize_tvt_mp_candidate_local_vehicle_advance_state(
            binding_transfer_state
        )
    )
    outlink_boundary_state = initialize_tvt_mp_candidate_outlink_boundary_state(
        local_vehicle_advance_state,
        downstream_boundary_node_result,
    )
    return OrderControlTvtMpCandidateLocalVirtualCalculationState(
        candidate_local_state=candidate_local_state,
        virtual_time_state=virtual_time_state,
        binding_transfer_state=binding_transfer_state,
        unbound_fcfs_transfer_state=unbound_fcfs_transfer_state,
        local_vehicle_advance_state=local_vehicle_advance_state,
        outlink_boundary_state=outlink_boundary_state,
        configured_horizon_steps=configured_horizon,
        required_buyer_visit_keys=required_buyer_visit_keys,
        required_seller_visit_keys=required_seller_visit_keys,
        passage_records_in_public_order=passage_records,
        traffic_observation_records_in_public_order=traffic_observation_records,
    )


def run_tvt_mp_candidate_local_virtual_calculation_one_timestep(
    calculation_state,
) -> OrderControlTvtMpCandidateVirtualTimestepResult:
    """Run the seven traffic steps of one allowed virtual timestep."""
    state = _require_calculation_state(calculation_state)
    _raise_if_finished(state)
    _raise_if_final_result_without_finished(state)

    virtual_time_state = state.virtual_time_state
    horizon_steps = state.configured_horizon_steps
    current_virtual_timestep = virtual_time_state.current_virtual_timestep
    if current_virtual_timestep in state.completed_virtual_timesteps:
        next_offset = virtual_time_state.current_offset + 1
        if next_offset >= horizon_steps:
            raise RuntimeError(
                f"Node {state.candidate_local_state.target_node_name!r}: "
                "the next processing offset would be "
                f"{next_offset}, which is outside 0 .. {horizon_steps - 1}. "
                "Offset H is not processed and virtual time one-step is not "
                "used as a terminal clock move."
            )
        advance_tvt_mp_candidate_virtual_time_one_step(virtual_time_state)

    offset = virtual_time_state.current_offset
    virtual_timestep = virtual_time_state.current_virtual_timestep
    if offset < 0 or offset >= horizon_steps:
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            f"processing offset {offset} is outside 0 .. {horizon_steps - 1}."
        )
    if virtual_timestep in state.completed_virtual_timesteps:
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            f"virtual timestep {virtual_timestep} is already completed in "
            "the orchestrating loop."
        )

    binding_transfer_result = (
        scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
            state.binding_transfer_state
        )
    )
    unbound_fcfs_result = (
        scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep(
            state.unbound_fcfs_transfer_state,
            binding_transfer_result,
        )
    )
    newly_recorded_keys = _record_required_passages_from_binding(
        state,
        binding_transfer_result,
        virtual_timestep,
    )
    _raise_if_unpassed_required_vehicle_passed_unbound(
        state,
        unbound_fcfs_result,
    )
    required_passages_complete_after_node_passage = (
        _required_passages_are_complete(state)
    )
    local_vehicle_advance_result = (
        advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
            state.local_vehicle_advance_state,
            binding_transfer_result,
        )
    )
    outlink_boundary_result = (
        process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
            state.outlink_boundary_state,
            local_vehicle_advance_result,
        )
    )

    resolved_after_timestep_end = required_passages_complete_after_node_passage
    last_allowed_offset = horizon_steps - 1
    calculation_finished_after_timestep_end = (
        resolved_after_timestep_end or offset == last_allowed_offset
    )
    timestep_result = OrderControlTvtMpCandidateVirtualTimestepResult(
        node_name=state.candidate_local_state.target_node_name,
        virtual_timestep=virtual_timestep,
        offset=offset,
        binding_transfer_result=binding_transfer_result,
        unbound_fcfs_result=unbound_fcfs_result,
        newly_recorded_required_passage_visit_keys=newly_recorded_keys,
        local_vehicle_advance_result=local_vehicle_advance_result,
        outlink_boundary_result=outlink_boundary_result,
        required_passages_complete_after_node_passage=(
            required_passages_complete_after_node_passage
        ),
        calculation_finished_after_timestep_end=(
            calculation_finished_after_timestep_end
        ),
        resolved_after_timestep_end=resolved_after_timestep_end,
    )
    if calculation_finished_after_timestep_end:
        final_result = _build_final_result(state, timestep_result)
        state._timestep_results.append(timestep_result)
        state._completed_virtual_timesteps.append(virtual_timestep)
        state._finished = True
        state._final_result = final_result
    else:
        state._timestep_results.append(timestep_result)
        state._completed_virtual_timesteps.append(virtual_timestep)
    return timestep_result


def run_tvt_mp_candidate_local_virtual_calculation(
    calculation_state,
) -> OrderControlTvtMpCandidateLocalVirtualCalculationResult:
    """Repeat the one-timestep API until resolved or the last allowed offset."""
    state = _require_calculation_state(calculation_state)
    if state.finished:
        if state.final_result is None:
            raise RuntimeError(
                f"Node {state.candidate_local_state.target_node_name!r}: "
                "the calculation is finished but no final result was stored."
            )
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            "the one-candidate local virtual calculation has already finished."
        )
    _raise_if_final_result_without_finished(state)
    while not state.finished:
        run_tvt_mp_candidate_local_virtual_calculation_one_timestep(state)
    if state.final_result is None:
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            "the calculation finished without storing a final result."
        )
    return state.final_result


def _require_candidate_local_state(candidate_local_state) -> None:
    if not isinstance(candidate_local_state, OrderControlTvtMpCandidateLocalState):
        raise ValueError(
            "candidate_local_state must be "
            "OrderControlTvtMpCandidateLocalState; got "
            f"type {type(candidate_local_state).__name__}."
        )


def _require_baseline_collector(baseline_collector) -> None:
    if not isinstance(baseline_collector, OrderControlBaselineCollector):
        raise ValueError(
            "baseline_collector must be OrderControlBaselineCollector; got "
            f"type {type(baseline_collector).__name__}."
        )


def _require_configured_horizon_steps(configured_horizon_steps) -> int:
    if type(configured_horizon_steps) is not int:
        raise ValueError(
            "configured_horizon_steps must be a Python int, not bool; got "
            f"type {type(configured_horizon_steps).__name__} with value "
            f"{configured_horizon_steps!r}."
        )
    if configured_horizon_steps < 1:
        raise ValueError(
            "configured_horizon_steps must be >= 1; got "
            f"{configured_horizon_steps!r}."
        )
    return configured_horizon_steps


def _require_calculation_state(
    calculation_state,
) -> OrderControlTvtMpCandidateLocalVirtualCalculationState:
    if not isinstance(
        calculation_state,
        OrderControlTvtMpCandidateLocalVirtualCalculationState,
    ):
        raise ValueError(
            "calculation_state must be "
            "OrderControlTvtMpCandidateLocalVirtualCalculationState; got "
            f"type {type(calculation_state).__name__}."
        )
    return calculation_state


def _raise_if_finished(state: OrderControlTvtMpCandidateLocalVirtualCalculationState) -> None:
    if state.finished:
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            "the one-candidate local virtual calculation has already finished."
        )


def _raise_if_final_result_without_finished(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> None:
    if state.final_result is not None and not state.finished:
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            "a final result is stored but the calculation is not finished."
        )


def _require_node_names_match(
    *,
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
    downstream_boundary_node_result: OrderControlBaselineDownstreamBoundaryNodeResult,
) -> None:
    node_name = candidate_local_state.target_node_name
    sequence = candidate_local_state.binding_rank_sequence
    if sequence.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: binding sequence node "
            f"{sequence.node_name!r} does not match the candidate target Node."
        )
    if downstream_boundary_node_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: downstream boundary node is "
            f"{downstream_boundary_node_result.node_name!r}."
        )
    copied_node = candidate_local_state.local_world.get_node(node_name)
    if copied_node is not candidate_local_state.target_node:
        raise RuntimeError(
            f"Node {node_name!r} in the copied World is not the candidate "
            "target Node."
        )


def _require_timesteps_match(
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
) -> None:
    sequence = candidate_local_state.binding_rank_sequence
    local_world = candidate_local_state.local_world
    node_name = candidate_local_state.target_node_name
    if candidate_local_state.real_world_timestep_T != sequence.baseline_timestep_T:
        raise RuntimeError(
            f"Node {node_name!r}: copied baseline timestep "
            f"{candidate_local_state.real_world_timestep_T} does not match "
            f"binding baseline {sequence.baseline_timestep_T}."
        )
    if local_world.T != sequence.baseline_timestep_T:
        raise RuntimeError(
            f"Node {node_name!r}: copied World time {local_world.T!r} does "
            f"not match binding baseline {sequence.baseline_timestep_T}."
        )


def _require_downstream_outlinks_match(
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
    downstream_boundary_node_result: OrderControlBaselineDownstreamBoundaryNodeResult,
) -> None:
    outlinks = tuple(candidate_local_state.outlinks)
    observed = downstream_boundary_node_result.outlink_results
    node_name = candidate_local_state.target_node_name
    if len(observed) != len(outlinks):
        raise RuntimeError(
            f"Node {node_name!r}: downstream boundary has {len(observed)} "
            f"outlinks and the candidate has {len(outlinks)}."
        )
    for outlink, observed_outlink in zip(outlinks, observed):
        if observed_outlink.outlink_name != outlink.name:
            raise RuntimeError(
                f"Node {node_name!r}: outlink order does not match. "
                f"Candidate outlink is {outlink.name!r} and downstream "
                f"boundary outlink is {observed_outlink.outlink_name!r}."
            )


def _visit_map_in_binding_order(
    sequence: OrderControlTvtMpLocalBindingRankSequence,
) -> dict[OrderControlTvtVisitKey, OrderControlTvtMpLocalBindingRankVisit]:
    visit_by_key: dict[
        OrderControlTvtVisitKey,
        OrderControlTvtMpLocalBindingRankVisit,
    ] = {}
    for visit in sequence.visits_in_binding_order:
        visit_key = visit.visit_key
        if visit_key in visit_by_key:
            raise RuntimeError(
                f"Node {sequence.node_name!r}: VisitKey {visit_key!r} is "
                "duplicated in visits_in_binding_order."
            )
        visit_by_key[visit_key] = visit
    return visit_by_key


def _require_buyer_and_seller_roles_only_in_trade_scope(
    sequence: OrderControlTvtMpLocalBindingRankSequence,
) -> None:
    for visit in sequence.visits_in_binding_order:
        if visit.trade_role in (
            OrderControlTvtMpLocalBindingTradeRole.BUYER,
            OrderControlTvtMpLocalBindingTradeRole.SELLER,
        ):
            if (
                visit.binding_partition
                is not OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
            ):
                raise RuntimeError(
                    f"Node {sequence.node_name!r}: VisitKey {visit.visit_key!r} "
                    f"has trade role {visit.trade_role} outside "
                    "trade_scope_of_this_candidate."
                )


def _required_buyer_visit_keys(
    sequence: OrderControlTvtMpLocalBindingRankSequence,
    visit_by_key: dict[OrderControlTvtVisitKey, OrderControlTvtMpLocalBindingRankVisit],
) -> tuple[OrderControlTvtVisitKey, ...]:
    buyers_sorted = sequence.concrete_buyer_candidate_set.buyers_sorted
    if not isinstance(buyers_sorted, tuple):
        raise RuntimeError(
            f"Node {sequence.node_name!r}: buyers_sorted must be a tuple."
        )
    if len(buyers_sorted) == 0:
        raise ValueError(
            f"Node {sequence.node_name!r}: required buyers are empty."
        )
    seen: set[OrderControlTvtVisitKey] = set()
    buyer_keys: list[OrderControlTvtVisitKey] = []
    for visit_key in buyers_sorted:
        if visit_key in seen:
            raise RuntimeError(
                f"Node {sequence.node_name!r}: required buyer VisitKey "
                f"{visit_key!r} is duplicated."
            )
        seen.add(visit_key)
        visit = visit_by_key.get(visit_key)
        if visit is None:
            raise RuntimeError(
                f"Node {sequence.node_name!r}: required buyer VisitKey "
                f"{visit_key!r} is not in the binding sequence."
            )
        if visit.trade_role is not OrderControlTvtMpLocalBindingTradeRole.BUYER:
            raise RuntimeError(
                f"Node {sequence.node_name!r}: required buyer VisitKey "
                f"{visit_key!r} has trade role {visit.trade_role}."
            )
        buyer_keys.append(visit_key)

    buyer_keys_from_trade_scope: set[OrderControlTvtVisitKey] = set()
    for visit in sequence.trade_scope_of_this_candidate_visits:
        if visit.trade_role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
            buyer_keys_from_trade_scope.add(visit.visit_key)
    if buyer_keys_from_trade_scope != set(buyer_keys):
        raise RuntimeError(
            f"Node {sequence.node_name!r}: BUYER visits in trade scope "
            "do not match concrete_buyer_candidate_set.buyers_sorted."
        )
    return tuple(buyer_keys)


def _required_seller_visit_keys(
    sequence: OrderControlTvtMpLocalBindingRankSequence,
    visit_by_key: dict[OrderControlTvtVisitKey, OrderControlTvtMpLocalBindingRankVisit],
) -> tuple[OrderControlTvtVisitKey, ...]:
    seller_keys: list[OrderControlTvtVisitKey] = []
    seen: set[OrderControlTvtVisitKey] = set()
    for visit in sequence.trade_scope_of_this_candidate_visits:
        if visit.trade_role is not OrderControlTvtMpLocalBindingTradeRole.SELLER:
            continue
        visit_key = visit.visit_key
        if visit_key in seen:
            raise RuntimeError(
                f"Node {sequence.node_name!r}: required seller VisitKey "
                f"{visit_key!r} is duplicated."
            )
        seen.add(visit_key)
        stored = visit_by_key.get(visit_key)
        if stored is None:
            raise RuntimeError(
                f"Node {sequence.node_name!r}: required seller VisitKey "
                f"{visit_key!r} is not in the binding sequence."
            )
        seller_keys.append(visit_key)
    return tuple(seller_keys)


def _require_no_buyer_seller_overlap(
    required_buyer_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    required_seller_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    *,
    node_name: str,
) -> None:
    buyer_set = set(required_buyer_visit_keys)
    for visit_key in required_seller_visit_keys:
        if visit_key in buyer_set:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is required as "
                "both buyer and seller."
            )


def _require_required_visits_have_collector_snapshots(
    baseline_collector: OrderControlBaselineCollector,
    node_name: str,
    required_buyer_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    required_seller_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    visit_by_key: dict[OrderControlTvtVisitKey, OrderControlTvtMpLocalBindingRankVisit],
) -> None:
    required_keys = list(required_buyer_visit_keys) + list(required_seller_visit_keys)
    for visit_key in required_keys:
        visit = visit_by_key[visit_key]
        vehicle_name, visit_id = visit_key
        if vehicle_name != visit.visit_key[0]:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} does not match "
                "the binding visit."
            )
        snapshot = baseline_collector.get_baseline_visit_snapshot(
            vehicle_name,
            visit_id,
        )
        if snapshot is None:
            raise RuntimeError(
                f"Node {node_name!r}: required VisitKey {visit_key!r} has no "
                "collector snapshot."
            )
        if snapshot.get("node_name") != node_name:
            raise RuntimeError(
                f"Node {node_name!r}: collector snapshot node "
                f"{snapshot.get('node_name')!r} does not match."
            )


def _initial_passage_records(
    *,
    baseline_collector: OrderControlBaselineCollector,
    node_name: str,
    required_buyer_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    required_seller_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    visit_by_key: dict[OrderControlTvtVisitKey, OrderControlTvtMpLocalBindingRankVisit],
) -> list[OrderControlTvtMpCandidatePassageRecord]:
    records: list[OrderControlTvtMpCandidatePassageRecord] = []
    required_keys = list(required_buyer_visit_keys) + list(required_seller_visit_keys)
    for visit_key in required_keys:
        visit = visit_by_key[visit_key]
        vehicle_name, visit_id = visit_key
        if vehicle_name != visit.visit_key[0]:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey vehicle name "
                f"{vehicle_name!r} does not match the visit."
            )
        if visit.trade_role not in (
            OrderControlTvtMpLocalBindingTradeRole.BUYER,
            OrderControlTvtMpLocalBindingTradeRole.SELLER,
        ):
            raise RuntimeError(
                f"Node {node_name!r}: required VisitKey {visit_key!r} has "
                f"trade role {visit.trade_role}."
            )
        snapshot = baseline_collector.get_baseline_visit_snapshot(
            vehicle_name,
            visit_id,
        )
        if snapshot is None:
            raise RuntimeError(
                f"Node {node_name!r}: required VisitKey {visit_key!r} has no "
                "collector snapshot."
            )
        baseline_passage_timestep = snapshot.get("baseline_passage_timestep")
        records.append(
            OrderControlTvtMpCandidatePassageRecord(
                visit_key=visit_key,
                vehicle_name=vehicle_name,
                trade_role=visit.trade_role,
                binding_partition=visit.binding_partition,
                binding_rank=visit.binding_rank,
                baseline_passage_timestep=baseline_passage_timestep,
                candidate_passage_timestep=None,
                route_next_link_name=visit.route_next_link_name,
                route_origin=visit.route_origin,
                inlink_name=visit.inlink_name,
            )
        )
    return records


_TRAFFIC_OBSERVATION_TRADE_ROLES = (
    OrderControlTvtMpLocalBindingTradeRole.BUYER,
    OrderControlTvtMpLocalBindingTradeRole.SELLER,
    OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING,
)


def _require_true_vot_for_traffic_observation(
    value: object,
    *,
    node_name: str,
    vehicle_name: str,
) -> float:
    """Freeze decision-time vot_true. Reject missing, bool, non-finite, and negative."""
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} vot_true must be "
            "a Python int or float, not bool or None; got "
            f"type {type(value).__name__} with value {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} vot_true must be "
            f"finite and >= 0; got {value!r}."
        )
    return float(value)


def _baseline_passage_for_traffic_observation(
    baseline_collector: OrderControlBaselineCollector,
    *,
    node_name: str,
    visit_key: OrderControlTvtVisitKey,
) -> int:
    """Read the candidate-visit baseline passage stored on the collector snapshot.

    Candidate visit construction copies this same collector field. The formal
    initialization path requires an int. The frozen record type still allows
    None for a later unobserved or incomplete representation.
    """
    vehicle_name, visit_id = visit_key
    snapshot = baseline_collector.get_baseline_visit_snapshot(vehicle_name, visit_id)
    if snapshot is None:
        raise RuntimeError(
            f"Node {node_name!r}: trade-scope VisitKey {visit_key!r} has no "
            "collector snapshot for baseline passage."
        )
    baseline_passage_timestep = snapshot.get("baseline_passage_timestep")
    if (
        isinstance(baseline_passage_timestep, bool)
        or type(baseline_passage_timestep) is not int
        or baseline_passage_timestep < 0
    ):
        raise RuntimeError(
            f"Node {node_name!r}: trade-scope VisitKey {visit_key!r} baseline "
            "passage must be a Python int >= 0; got "
            f"{baseline_passage_timestep!r}."
        )
    return baseline_passage_timestep


def _require_non_empty_text(value: object, *, node_name: str, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation {field_name} must be a "
            f"non-empty str; got {value!r}."
        )
    return value


def _initial_traffic_observation_records(
    *,
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
    baseline_collector: OrderControlBaselineCollector,
    node_name: str,
) -> list[OrderControlTvtMpCandidateTrafficObservationRecord]:
    """One initial record per trade_scope visit, in that tuple's order."""
    sequence = candidate_local_state.binding_rank_sequence
    trade_scope_visits = sequence.trade_scope_of_this_candidate_visits
    records: list[OrderControlTvtMpCandidateTrafficObservationRecord] = []
    seen_visit_keys: set[OrderControlTvtVisitKey] = set()
    for index, visit in enumerate(trade_scope_visits):
        trade_scope_rank = index + 1
        visit_key = visit.visit_key
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: trade-scope VisitKey {visit_key!r} is "
                "duplicated."
            )
        seen_visit_keys.add(visit_key)
        if (
            visit.binding_partition
            is not OrderControlTvtMpLocalBindingPartition.TRADE_SCOPE_OF_THIS_CANDIDATE
        ):
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} is in "
                "trade_scope_of_this_candidate_visits but binding partition "
                f"is {visit.binding_partition!r}."
            )
        if visit.trade_role not in _TRAFFIC_OBSERVATION_TRADE_ROLES:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} has trade role "
                f"{visit.trade_role!r}. Traffic observation accepts only "
                "buyer, seller, and nonparticipating."
            )
        if type(visit.binding_rank) is not int or visit.binding_rank < 1:
            raise RuntimeError(
                f"Node {node_name!r}: VisitKey {visit_key!r} binding_rank "
                f"must be a Python int >= 1; got {visit.binding_rank!r}."
            )
        vehicle_name = _require_non_empty_text(
            visit_key[0],
            node_name=node_name,
            field_name="vehicle_name",
        )
        inlink_name = _require_non_empty_text(
            visit.inlink_name,
            node_name=node_name,
            field_name="inlink_name",
        )
        route_next_link_name = _require_non_empty_text(
            visit.route_next_link_name,
            node_name=node_name,
            field_name="route_next_link_name",
        )
        local_vehicle = candidate_local_state.local_vehicle_by_real_vehicle_name.get(
            vehicle_name
        )
        if local_vehicle is None:
            raise RuntimeError(
                f"Node {node_name!r}: trade-scope Vehicle {vehicle_name!r} "
                "has no local Vehicle."
            )
        if local_vehicle.name != vehicle_name:
            raise RuntimeError(
                f"Node {node_name!r}: local Vehicle name {local_vehicle.name!r} "
                f"does not match VisitKey {visit_key!r}."
            )
        vehicle_id = local_vehicle.id
        if isinstance(vehicle_id, bool) or type(vehicle_id) is not int:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {vehicle_name!r} id must be a "
                f"Python int; got {vehicle_id!r}."
            )
        if vehicle_id != visit.vehicle_id:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {vehicle_name!r} id {vehicle_id!r} "
                f"does not match binding vehicle_id {visit.vehicle_id!r}."
            )
        true_vot_per_second = _require_true_vot_for_traffic_observation(
            local_vehicle.vot_true,
            node_name=node_name,
            vehicle_name=vehicle_name,
        )
        baseline_passage_timestep = _baseline_passage_for_traffic_observation(
            baseline_collector,
            node_name=node_name,
            visit_key=visit_key,
        )
        records.append(
            OrderControlTvtMpCandidateTrafficObservationRecord(
                visit_key=visit_key,
                vehicle_name=vehicle_name,
                vehicle_id=vehicle_id,
                trade_role=visit.trade_role,
                binding_partition=visit.binding_partition,
                binding_rank=visit.binding_rank,
                trade_scope_rank=trade_scope_rank,
                inlink_name=inlink_name,
                route_next_link_name=route_next_link_name,
                true_vot_per_second=true_vot_per_second,
                baseline_passage_timestep=baseline_passage_timestep,
                candidate_passage_timestep=None,
                passage_observation_status=None,
                observed_offset=None,
                observed_virtual_timestep=None,
                predicted_time_difference_timesteps=None,
                predicted_time_difference_seconds=None,
                predicted_signed_time_value_change=None,
                last_checked_offset=None,
                last_checked_virtual_timestep=None,
                last_temporary_skip_reason=None,
                last_temporary_skip_offset=None,
                latest_clearance_stop_context=None,
                horizon_exhausted=None,
                observation_complete=None,
            )
        )
    return records


def _propose_tvt_mp_candidate_traffic_observation_updates_from_binding_transfer(
    calculation_state,
    binding_transfer_result,
    offset,
    virtual_timestep,
) -> tuple[OrderControlTvtMpCandidateTrafficObservationRecord, ...]:
    """Build updated traffic observation records for binding transfers.

    Does not modify calculation_state. Only trade-scope visits with an
    existing observation record are updated. Keys outside that set are ignored.
    """
    state = _require_calculation_state(calculation_state)
    if not isinstance(
        binding_transfer_result,
        OrderControlTvtMpBindingTransferScanResult,
    ):
        raise ValueError(
            "binding_transfer_result must be "
            "OrderControlTvtMpBindingTransferScanResult; got "
            f"type {type(binding_transfer_result).__name__}."
        )
    node_name = state.candidate_local_state.target_node_name
    offset_value = _require_traffic_observation_update_offset(offset, node_name=node_name)
    virtual_timestep_value = _require_traffic_observation_update_virtual_timestep(
        virtual_timestep,
        node_name=node_name,
    )
    deltat = _require_traffic_observation_update_deltat(
        state.candidate_local_state.local_world.DELTAT,
        node_name=node_name,
    )
    proposed_records: list[OrderControlTvtMpCandidateTrafficObservationRecord] = []
    seen_trade_scope_visit_keys: set[OrderControlTvtVisitKey] = set()
    for visit_key in binding_transfer_result.transferred_binding_visit_keys:
        existing_record = state._traffic_observation_record_by_visit_key.get(visit_key)
        if existing_record is None:
            continue
        if visit_key in seen_trade_scope_visit_keys:
            raise RuntimeError(
                f"Node {node_name!r}: trade-scope VisitKey {visit_key!r} was "
                "transferred twice in one binding transfer result."
            )
        seen_trade_scope_visit_keys.add(visit_key)
        if existing_record.candidate_passage_timestep is not None:
            raise RuntimeError(
                f"Node {node_name!r}: trade-scope VisitKey {visit_key!r} already "
                "has candidate passage timestep "
                f"{existing_record.candidate_passage_timestep}."
            )
        baseline_passage_timestep = existing_record.baseline_passage_timestep
        if (
            isinstance(baseline_passage_timestep, bool)
            or type(baseline_passage_timestep) is not int
        ):
            raise RuntimeError(
                f"Node {node_name!r}: trade-scope VisitKey {visit_key!r} baseline "
                "passage must be a Python int; got "
                f"{baseline_passage_timestep!r}."
            )
        true_vot_per_second = _require_frozen_true_vot_per_second_on_observation_record(
            existing_record.true_vot_per_second,
            node_name=node_name,
            vehicle_name=existing_record.vehicle_name,
        )
        predicted_time_difference_timesteps = (
            baseline_passage_timestep - virtual_timestep_value
        )
        predicted_time_difference_seconds = (
            predicted_time_difference_timesteps * deltat
        )
        predicted_signed_time_value_change = (
            predicted_time_difference_seconds * true_vot_per_second
        )
        proposed_records.append(
            OrderControlTvtMpCandidateTrafficObservationRecord(
                visit_key=existing_record.visit_key,
                vehicle_name=existing_record.vehicle_name,
                vehicle_id=existing_record.vehicle_id,
                trade_role=existing_record.trade_role,
                binding_partition=existing_record.binding_partition,
                binding_rank=existing_record.binding_rank,
                trade_scope_rank=existing_record.trade_scope_rank,
                inlink_name=existing_record.inlink_name,
                route_next_link_name=existing_record.route_next_link_name,
                true_vot_per_second=existing_record.true_vot_per_second,
                baseline_passage_timestep=existing_record.baseline_passage_timestep,
                candidate_passage_timestep=virtual_timestep_value,
                passage_observation_status=existing_record.passage_observation_status,
                observed_offset=offset_value,
                observed_virtual_timestep=virtual_timestep_value,
                predicted_time_difference_timesteps=predicted_time_difference_timesteps,
                predicted_time_difference_seconds=predicted_time_difference_seconds,
                predicted_signed_time_value_change=predicted_signed_time_value_change,
                last_checked_offset=offset_value,
                last_checked_virtual_timestep=virtual_timestep_value,
                last_temporary_skip_reason=existing_record.last_temporary_skip_reason,
                last_temporary_skip_offset=existing_record.last_temporary_skip_offset,
                latest_clearance_stop_context=(
                    existing_record.latest_clearance_stop_context
                ),
                horizon_exhausted=existing_record.horizon_exhausted,
                observation_complete=existing_record.observation_complete,
            )
        )
    return tuple(proposed_records)


def _require_traffic_observation_update_offset(value: object, *, node_name: str) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation update offset must be a "
            f"Python int >= 0; got type {type(value).__name__} with value "
            f"{value!r}."
        )
    if value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation update offset must be >= 0; "
            f"got {value!r}."
        )
    return value


def _require_traffic_observation_update_virtual_timestep(
    value: object,
    *,
    node_name: str,
) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation update virtual_timestep "
            f"must be a Python int >= 0; got type {type(value).__name__} with "
            f"value {value!r}."
        )
    if value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation update virtual_timestep "
            f"must be >= 0; got {value!r}."
        )
    return value


def _require_traffic_observation_update_deltat(
    value: object,
    *,
    node_name: str,
) -> int | float:
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: local World DELTAT must be a Python int or "
            f"float; got type {type(value).__name__} with value {value!r}."
        )
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(
            f"Node {node_name!r}: local World DELTAT must be finite and > 0; "
            f"got {value!r}."
        )
    return value


def _require_frozen_true_vot_per_second_on_observation_record(
    value: object,
    *,
    node_name: str,
    vehicle_name: str,
) -> float:
    if value is None or isinstance(value, bool) or type(value) not in (int, float):
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation record for Vehicle "
            f"{vehicle_name!r} true_vot_per_second must be a Python int or "
            f"float; got type {type(value).__name__} with value {value!r}."
        )
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: traffic observation record for Vehicle "
            f"{vehicle_name!r} true_vot_per_second must be finite and >= 0; "
            f"got {value!r}."
        )
    return float(value)


def _record_required_passages_from_binding(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    binding_transfer_result: OrderControlTvtMpBindingTransferScanResult,
    virtual_timestep: int,
) -> tuple[OrderControlTvtVisitKey, ...]:
    required_keys = set(state.required_buyer_visit_keys)
    required_keys.update(state.required_seller_visit_keys)
    newly_recorded: list[OrderControlTvtVisitKey] = []
    seen_in_this_timestep: set[OrderControlTvtVisitKey] = set()
    for visit_key in binding_transfer_result.transferred_binding_visit_keys:
        if visit_key not in required_keys:
            continue
        if visit_key in seen_in_this_timestep:
            raise RuntimeError(
                f"Node {state.candidate_local_state.target_node_name!r}: "
                f"required VisitKey {visit_key!r} was transferred twice in "
                f"virtual timestep {virtual_timestep}."
            )
        seen_in_this_timestep.add(visit_key)
        current_record = state._passage_record_by_visit_key[visit_key]
        if current_record.candidate_passage_timestep is not None:
            raise RuntimeError(
                f"Node {state.candidate_local_state.target_node_name!r}: "
                f"required VisitKey {visit_key!r} already has candidate "
                f"passage timestep {current_record.candidate_passage_timestep}."
            )
        updated_record = OrderControlTvtMpCandidatePassageRecord(
            visit_key=current_record.visit_key,
            vehicle_name=current_record.vehicle_name,
            trade_role=current_record.trade_role,
            binding_partition=current_record.binding_partition,
            binding_rank=current_record.binding_rank,
            baseline_passage_timestep=current_record.baseline_passage_timestep,
            candidate_passage_timestep=virtual_timestep,
            route_next_link_name=current_record.route_next_link_name,
            route_origin=current_record.route_origin,
            inlink_name=current_record.inlink_name,
        )
        state._passage_record_by_visit_key[visit_key] = updated_record
        _replace_passage_record_in_public_order(state, updated_record)
        newly_recorded.append(visit_key)
    return tuple(newly_recorded)


def _replace_passage_record_in_public_order(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    updated_record: OrderControlTvtMpCandidatePassageRecord,
) -> None:
    public_order = state._passage_records_in_public_order
    for index, existing in enumerate(public_order):
        if existing.visit_key == updated_record.visit_key:
            public_order[index] = updated_record
            return
    raise RuntimeError(
        f"Node {state.candidate_local_state.target_node_name!r}: "
        f"required VisitKey {updated_record.visit_key!r} is missing from "
        "the public passage-record order."
    )


def _raise_if_unpassed_required_vehicle_passed_unbound(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    unbound_fcfs_result: OrderControlTvtMpUnboundFcfsTransferResult,
) -> None:
    unpassed_vehicle_names: set[str] = set()
    for record in state._passage_records_in_public_order:
        if record.candidate_passage_timestep is None:
            unpassed_vehicle_names.add(record.vehicle_name)
    for transferred in unbound_fcfs_result.transferred_vehicle_records:
        if transferred.vehicle_name in unpassed_vehicle_names:
            raise RuntimeError(
                f"Node {state.candidate_local_state.target_node_name!r}: "
                f"unpassed required vehicle {transferred.vehicle_name!r} "
                "passed as an unbound vehicle."
            )


def _required_passages_are_complete(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> bool:
    for record in state._passage_records_in_public_order:
        if type(record.candidate_passage_timestep) is not int:
            return False
    return True


def _build_final_result(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    last_timestep_result: OrderControlTvtMpCandidateVirtualTimestepResult,
) -> OrderControlTvtMpCandidateLocalVirtualCalculationResult:
    resolved = last_timestep_result.resolved_after_timestep_end
    if resolved:
        stop_reason = (
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
        )
        unresolved_reasons: tuple[OrderControlTvtMpCandidateUnresolvedReason, ...] = ()
    else:
        stop_reason = (
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
        )
        completed_timestep_results = tuple(state._timestep_results) + (
            last_timestep_result,
        )
        unresolved_reasons = _collect_unresolved_reasons(
            state,
            completed_timestep_results,
        )
    sequence = state.candidate_local_state.binding_rank_sequence
    virtual_time_state = state.virtual_time_state
    final_vehicle_records = _build_final_vehicle_records(state)
    final_inlink_records, final_outlink_records = _build_final_link_records(state)
    final_node_record = _build_final_node_record(state)
    final_boundary_records = _build_final_boundary_records(
        state,
        last_timestep_result.outlink_boundary_result,
    )
    return OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name=state.candidate_local_state.target_node_name,
        concrete_buyer_candidate_set=sequence.concrete_buyer_candidate_set,
        binding_rank_sequence=sequence,
        baseline_timestep_T=virtual_time_state.baseline_timestep_T,
        configured_horizon_steps=state.configured_horizon_steps,
        final_virtual_timestep=last_timestep_result.virtual_timestep,
        final_offset=last_timestep_result.offset,
        simulated_timestep_count=virtual_time_state.simulated_timestep_count,
        stop_reason=stop_reason,
        resolved=resolved,
        required_passage_records=tuple(state._passage_records_in_public_order),
        unresolved_reasons=unresolved_reasons,
        timestep_results=tuple(state._timestep_results) + (last_timestep_result,),
        final_vehicle_records=final_vehicle_records,
        final_inlink_records=final_inlink_records,
        final_outlink_records=final_outlink_records,
        final_node_record=final_node_record,
        final_boundary_records=final_boundary_records,
    )


def _collect_unresolved_reasons(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...],
) -> tuple[OrderControlTvtMpCandidateUnresolvedReason, ...]:
    reasons: list[OrderControlTvtMpCandidateUnresolvedReason] = []
    if _required_visit_did_not_pass(state):
        reasons.append(
            OrderControlTvtMpCandidateUnresolvedReason.REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON
        )
    if _downstream_boundary_remained_blocked(timestep_results):
        reasons.append(
            OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_REMAINED_BLOCKED_WITHIN_HORIZON
        )
    if _downstream_boundary_had_waiting_without_transfer(state):
        reasons.append(
            OrderControlTvtMpCandidateUnresolvedReason.DOWNSTREAM_BOUNDARY_HAD_WAITING_VEHICLES_BUT_NO_TRANSFER
        )
    if _clearance_or_capacity_blocked_through_horizon(state, timestep_results):
        reasons.append(
            OrderControlTvtMpCandidateUnresolvedReason.CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON
        )
    if _acceptable_outlinks_empty_was_observed(timestep_results):
        reasons.append(
            OrderControlTvtMpCandidateUnresolvedReason.NO_ACCEPTABLE_OUTLINK_FOR_ROUTE_UNDETERMINED_VEHICLE_WITHIN_HORIZON
        )
    if not reasons:
        raise RuntimeError(
            f"Node {state.candidate_local_state.target_node_name!r}: "
            "horizon exhausted unresolved has no observed reason."
        )
    return tuple(reasons)


def _required_visit_did_not_pass(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> bool:
    for record in state._passage_records_in_public_order:
        if record.candidate_passage_timestep is None:
            return True
    return False


def _downstream_boundary_had_waiting_without_transfer(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> bool:
    for link_state in state.outlink_boundary_state.outlink_states:
        if (
            link_state.boundary_mode
            is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
        ):
            return True
    return False


def _downstream_boundary_remained_blocked(
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...],
) -> bool:
    if len(timestep_results) == 0:
        return False
    last_boundary_result = timestep_results[-1].outlink_boundary_result
    for outlink_result in last_boundary_result.outlink_results:
        if (
            outlink_result.boundary_mode
            is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
            and len(outlink_result.waiting_vehicle_names_after) > 0
        ):
            return True
    return False


def _clearance_or_capacity_blocked_through_horizon(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...],
) -> bool:
    unpassed_visit_keys: list[OrderControlTvtVisitKey] = []
    for record in state._passage_records_in_public_order:
        if record.candidate_passage_timestep is None:
            unpassed_visit_keys.append(record.visit_key)
    for visit_key in unpassed_visit_keys:
        if _one_unpassed_visit_was_blocked_through_horizon(
            visit_key,
            timestep_results,
        ):
            return True
    return False


def _one_unpassed_visit_was_blocked_through_horizon(
    visit_key: OrderControlTvtVisitKey,
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...],
) -> bool:
    first_observed_index = _first_timestep_with_direct_arrival_observation_for_visit(
        visit_key,
        timestep_results,
    )
    if first_observed_index is None:
        return False
    last_processed_index = len(timestep_results) - 1
    observation_span_length = last_processed_index - first_observed_index + 1
    if observation_span_length < 2:
        return False
    for index in range(first_observed_index, last_processed_index + 1):
        binding_result = timestep_results[index].binding_transfer_result
        if not _required_visit_has_direct_capacity_or_clearance_block_on_self(
            visit_key,
            binding_result,
        ):
            return False
    return True


def _first_timestep_with_direct_arrival_observation_for_visit(
    visit_key: OrderControlTvtVisitKey,
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...],
) -> int | None:
    """First timestep where this required Visit itself is visible on the binding scan.

    A forward Visit's clearance stop does not count. Missing skip records do not
    prove that this Visit has arrived.
    """
    for index, timestep_result in enumerate(timestep_results):
        binding_result = timestep_result.binding_transfer_result
        if _required_visit_has_direct_arrival_observation_on_binding(
            visit_key,
            binding_result,
        ):
            return index
    return None


def _required_visit_has_direct_arrival_observation_on_binding(
    visit_key: OrderControlTvtVisitKey,
    binding_transfer_result: OrderControlTvtMpBindingTransferScanResult,
) -> bool:
    if visit_key in binding_transfer_result.transferred_binding_visit_keys:
        return False
    skip_reason = _binding_skip_reason_for_visit(visit_key, binding_transfer_result)
    if (
        skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
    ):
        return False
    if skip_reason in _CAPACITY_OR_PHYSICAL_SKIP_REASONS:
        return True
    if (
        binding_transfer_result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
        and binding_transfer_result.stopped_binding_visit_key == visit_key
    ):
        return True
    return False


def _required_visit_has_direct_capacity_or_clearance_block_on_self(
    visit_key: OrderControlTvtVisitKey,
    binding_transfer_result: OrderControlTvtMpBindingTransferScanResult,
) -> bool:
    """True only when this Visit's own binding record shows a capacity or clearance block."""
    if visit_key in binding_transfer_result.transferred_binding_visit_keys:
        return False
    skip_reason = _binding_skip_reason_for_visit(visit_key, binding_transfer_result)
    if (
        skip_reason
        is OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
    ):
        return False
    if skip_reason in _CAPACITY_OR_PHYSICAL_SKIP_REASONS:
        return True
    if (
        binding_transfer_result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
        and binding_transfer_result.stopped_binding_visit_key == visit_key
    ):
        return True
    return False


def _binding_skip_reason_for_visit(
    visit_key: OrderControlTvtVisitKey,
    binding_transfer_result: OrderControlTvtMpBindingTransferScanResult,
) -> OrderControlTvtMpBindingVisitTemporarySkipReason | None:
    for skip in binding_transfer_result.temporarily_skipped_visits:
        if skip.binding_visit_key == visit_key:
            return skip.skip_reason
    return None


def _acceptable_outlinks_empty_was_observed(
    timestep_results: tuple[OrderControlTvtMpCandidateVirtualTimestepResult, ...],
) -> bool:
    for timestep_result in timestep_results:
        unbound_result = timestep_result.unbound_fcfs_result
        for skip in unbound_result.temporary_skips:
            if (
                skip.skip_reason
                is OrderControlTvtMpUnboundTemporarySkipReason.ACCEPTABLE_OUTLINKS_EMPTY
            ):
                return True
    return False


def _build_final_vehicle_records(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> tuple[OrderControlTvtMpCandidateFinalVehicleRecord, ...]:
    candidate_local_state = state.candidate_local_state
    seen_vehicle_ids: set[int] = set()
    name_to_vehicle_id: dict[str, int] = {}
    records: list[OrderControlTvtMpCandidateFinalVehicleRecord] = []
    vehicles_in_union: list[object] = []
    for inlink in candidate_local_state.inlinks:
        for vehicle in list(inlink.vehicles):
            vehicles_in_union.append(vehicle)
    for outlink in candidate_local_state.outlinks:
        for vehicle in list(outlink.vehicles):
            vehicles_in_union.append(vehicle)
    for vehicle in list(candidate_local_state.target_node.incoming_vehicles):
        vehicles_in_union.append(vehicle)
    for vehicle in vehicles_in_union:
        vehicle_id = id(vehicle)
        vehicle_name = vehicle.name
        if vehicle_id in seen_vehicle_ids:
            continue
        if vehicle_name in name_to_vehicle_id:
            if name_to_vehicle_id[vehicle_name] != vehicle_id:
                raise RuntimeError(
                    f"Node {candidate_local_state.target_node_name!r}: "
                    f"vehicle name {vehicle_name!r} refers to different "
                    "Vehicle objects."
                )
            continue
        seen_vehicle_ids.add(vehicle_id)
        name_to_vehicle_id[vehicle_name] = vehicle_id
        records.append(_one_final_vehicle_record(vehicle))
    return tuple(records)


def _one_final_vehicle_record(vehicle) -> OrderControlTvtMpCandidateFinalVehicleRecord:
    current_link = getattr(vehicle, "link", None)
    if current_link is None:
        current_link_name = None
        position_x = None
    else:
        current_link_name = current_link.name
        position_x = vehicle.x
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if current_visit is None:
        current_visit_key = None
        current_visit_node_name = None
    else:
        visit_id = current_visit.get("visit_id")
        if isinstance(visit_id, bool) or not isinstance(visit_id, int):
            raise RuntimeError(
                f"Vehicle {vehicle.name!r}: current visit_id is not a "
                f"Python int; got {visit_id!r}."
            )
        current_visit_key = (vehicle.name, visit_id)
        visit_node = current_visit.get("node")
        if visit_node is None:
            current_visit_node_name = None
        else:
            current_visit_node_name = visit_node.name
    vehicle_state = vehicle.state
    if not isinstance(vehicle_state, str):
        raise RuntimeError(
            f"Vehicle {vehicle.name!r}: state is not a str; got "
            f"{vehicle_state!r}."
        )
    return OrderControlTvtMpCandidateFinalVehicleRecord(
        vehicle_name=vehicle.name,
        current_link_name=current_link_name,
        position_x=position_x,
        state=vehicle_state,
        current_visit_key=current_visit_key,
        current_visit_node_name=current_visit_node_name,
    )


def _build_final_link_records(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> tuple[
    tuple[OrderControlTvtMpCandidateFinalLinkRecord, ...],
    tuple[OrderControlTvtMpCandidateFinalLinkRecord, ...],
]:
    candidate_local_state = state.candidate_local_state
    inlink_records: list[OrderControlTvtMpCandidateFinalLinkRecord] = []
    for inlink in candidate_local_state.inlinks:
        inlink_records.append(
            _one_final_link_record(
                inlink,
                OrderControlTvtMpCandidateFinalLinkRole.TARGET_INLINK,
            )
        )
    outlink_records: list[OrderControlTvtMpCandidateFinalLinkRecord] = []
    for outlink in candidate_local_state.outlinks:
        outlink_records.append(
            _one_final_link_record(
                outlink,
                OrderControlTvtMpCandidateFinalLinkRole.TARGET_OUTLINK,
            )
        )
    return tuple(inlink_records), tuple(outlink_records)


def _one_final_link_record(
    link,
    link_role: OrderControlTvtMpCandidateFinalLinkRole,
) -> OrderControlTvtMpCandidateFinalLinkRecord:
    vehicle_names: list[str] = []
    for vehicle in list(link.vehicles):
        vehicle_names.append(vehicle.name)
    return OrderControlTvtMpCandidateFinalLinkRecord(
        link_name=link.name,
        start_node_name=link.start_node.name,
        end_node_name=link.end_node.name,
        link_role=link_role,
        vehicle_names_in_physical_order=tuple(vehicle_names),
        capacity_out_remain=link.capacity_out_remain,
        capacity_in_remain=link.capacity_in_remain,
    )


def _build_final_node_record(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
) -> OrderControlTvtMpCandidateFinalNodeRecord:
    target_node = state.candidate_local_state.target_node
    incoming_names: list[str] = []
    seen_vehicle_ids: set[int] = set()
    for vehicle in list(target_node.incoming_vehicles):
        vehicle_id = id(vehicle)
        if vehicle_id in seen_vehicle_ids:
            raise RuntimeError(
                f"Node {target_node.name!r}: incoming list contains the "
                f"same Vehicle object more than once ({vehicle.name!r})."
            )
        seen_vehicle_ids.add(vehicle_id)
        incoming_names.append(vehicle.name)
    last_inlink = target_node.last_order_control_inlink
    if last_inlink is None:
        last_inlink_name = None
    else:
        last_inlink_name = last_inlink.name
    return OrderControlTvtMpCandidateFinalNodeRecord(
        node_name=target_node.name,
        incoming_vehicle_names=tuple(incoming_names),
        flow_capacity_remain=target_node.flow_capacity_remain,
        last_order_control_inlink_name=last_inlink_name,
        last_order_control_entry_timestep=(
            target_node.last_order_control_entry_timestep
        ),
        order_control_clearance_timesteps=(
            target_node.order_control_clearance_timesteps
        ),
    )


def _build_final_boundary_records(
    state: OrderControlTvtMpCandidateLocalVirtualCalculationState,
    last_boundary_result: OrderControlTvtMpOutlinkBoundaryProcessResult,
) -> tuple[OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord, ...]:
    last_result_by_outlink_name: dict[str, object] = {}
    for outlink_result in last_boundary_result.outlink_results:
        last_result_by_outlink_name[outlink_result.outlink_name] = outlink_result
    records: list[OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord] = []
    for link_state in state.outlink_boundary_state.outlink_states:
        last_outlink_result = last_result_by_outlink_name.get(link_state.outlink_name)
        if last_outlink_result is None:
            raise RuntimeError(
                f"Node {state.candidate_local_state.target_node_name!r}: "
                f"outlink {link_state.outlink_name!r} is missing from the "
                "last boundary result."
            )
        records.append(
            OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord(
                outlink_name=link_state.outlink_name,
                terminal_node_name=link_state.terminal_node_name,
                boundary_mode=last_outlink_result.boundary_mode,
                observed_average_outflow_rate=link_state.observed_average_outflow_rate,
                flow_allowance_after=last_outlink_result.flow_allowance_after,
                waiting_vehicle_names_after=(
                    last_outlink_result.waiting_vehicle_names_after
                ),
                capacity_out_remain_after=last_outlink_result.capacity_out_remain_after,
                terminal_node_flow_capacity_remain_after=(
                    last_outlink_result.terminal_node_flow_capacity_remain_after
                ),
                cumulative_observed_outflow_exit_vehicle_names=(
                    link_state.cumulative_observed_outflow_exit_vehicle_names
                ),
                cumulative_constrained_sink_end_trip_vehicle_names=(
                    link_state.cumulative_constrained_sink_end_trip_vehicle_names
                ),
            )
        )
    return tuple(records)
