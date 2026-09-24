"""
Outlink-terminal boundary handling for one TVT-MP candidate copy.

This stage runs after local vehicle advance at the same virtual timestep.
It does not scan binding-rank passage again, does not advance vehicles,
and does not move the virtual clock.

Downstream boundary counts come from the baseline observation result for
this target Node. ``None`` means observation was not run. That is not the
same as an observed active count of zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
)
from uxsim.order_control_tvt_mp_candidate_local_vehicle_advance import (
    OrderControlTvtMpCandidateLocalVehicleAdvanceState,
    OrderControlTvtMpLocalVehicleAdvanceResult,
)


class OrderControlTvtMpOutlinkBoundaryMode(Enum):
    """How one outlink terminal is served inside the local horizon."""

    OBSERVED_WAIT_WITH_OUTFLOW = "observed_wait_with_outflow"
    OBSERVED_WAIT_WITHOUT_OUTFLOW = "observed_wait_without_outflow"
    NO_OBSERVED_WAIT_CONSTRAINED_SINK = "no_observed_wait_constrained_sink"


class OrderControlTvtMpOutlinkBoundaryRemovalKind(Enum):
    """Why a vehicle left the outlink terminal in the candidate copy."""

    OBSERVED_OUTFLOW_BOUNDARY_EXIT = "observed_outflow_boundary_exit"
    CONSTRAINED_SINK_END_TRIP = "constrained_sink_end_trip"


@dataclass(frozen=True)
class OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord:
    """One vehicle removed from an outlink terminal.

    ``vehicle_name`` is the identifier. The current order-control visit may
    be ``None`` when the terminal Node is not order-control eligible. This
    record does not store a VisitKey and does not infer one.
    """

    vehicle_name: str
    outlink_name: str
    terminal_node_name: str
    virtual_timestep: int
    boundary_exit_time_seconds: int | float
    removal_kind: OrderControlTvtMpOutlinkBoundaryRemovalKind

    def __post_init__(self) -> None:
        if not isinstance(self.vehicle_name, str) or self.vehicle_name == "":
            raise ValueError(
                "vehicle_name must be a non-empty str; "
                f"got {self.vehicle_name!r}."
            )
        if not isinstance(self.outlink_name, str) or self.outlink_name == "":
            raise ValueError(
                "outlink_name must be a non-empty str; "
                f"got {self.outlink_name!r}."
            )
        if (
            not isinstance(self.terminal_node_name, str)
            or self.terminal_node_name == ""
        ):
            raise ValueError(
                "terminal_node_name must be a non-empty str; "
                f"got {self.terminal_node_name!r}."
            )
        _require_non_negative_int(self.virtual_timestep, "virtual_timestep")
        _require_number(self.boundary_exit_time_seconds, "boundary_exit_time_seconds")
        if not isinstance(
            self.removal_kind,
            OrderControlTvtMpOutlinkBoundaryRemovalKind,
        ):
            raise ValueError(
                "removal_kind must be "
                "OrderControlTvtMpOutlinkBoundaryRemovalKind; got "
                f"{self.removal_kind!r}."
            )


@dataclass(frozen=True)
class OrderControlTvtMpOutlinkBoundaryLinkProcessResult:
    """What one outlink terminal did at one virtual timestep."""

    outlink_name: str
    terminal_node_name: str
    boundary_mode: OrderControlTvtMpOutlinkBoundaryMode
    flow_allowance_before: int | float
    flow_allowance_added: int | float
    flow_allowance_after: int | float
    vehicle_names_at_end_before: tuple[str, ...]
    observed_outflow_boundary_exit_vehicle_names: tuple[str, ...]
    constrained_sink_end_trip_vehicle_names: tuple[str, ...]
    waiting_vehicle_names_after: tuple[str, ...]
    capacity_out_remain_before: int | float
    capacity_out_remain_after: int | float
    terminal_node_flow_capacity_remain_before: int | float
    terminal_node_flow_capacity_remain_after: int | float


@dataclass(frozen=True)
class OrderControlTvtMpOutlinkBoundaryProcessResult:
    """Boundary results for every outlink of one Node, in registration order."""

    node_name: str
    virtual_timestep: int
    outlink_results: tuple[OrderControlTvtMpOutlinkBoundaryLinkProcessResult, ...]


class OrderControlTvtMpCandidateOutlinkBoundaryLinkState:
    """Per-outlink allowance and cumulative removal names for one candidate."""

    def __init__(
        self,
        *,
        outlink_name: str,
        terminal_node_name: str,
        boundary_mode: OrderControlTvtMpOutlinkBoundaryMode,
        active_timestep_count: int,
        transferred_vehicle_count: int,
        observed_average_outflow_rate: int | float | None,
    ) -> None:
        self._outlink_name = outlink_name
        self._terminal_node_name = terminal_node_name
        self._boundary_mode = boundary_mode
        self._active_timestep_count = active_timestep_count
        self._transferred_vehicle_count = transferred_vehicle_count
        self._observed_average_outflow_rate = observed_average_outflow_rate
        self._flow_allowance = 0.0
        self._cumulative_observed_outflow_exit_vehicle_names: list[str] = []
        self._cumulative_constrained_sink_end_trip_vehicle_names: list[str] = []
        self._completed_virtual_timesteps: list[int] = []
        self._completed_process_results_by_virtual_timestep: dict[
            int,
            OrderControlTvtMpOutlinkBoundaryLinkProcessResult,
        ] = {}

    @property
    def outlink_name(self) -> str:
        return self._outlink_name

    @property
    def terminal_node_name(self) -> str:
        return self._terminal_node_name

    @property
    def boundary_mode(self) -> OrderControlTvtMpOutlinkBoundaryMode:
        return self._boundary_mode

    @property
    def active_timestep_count(self) -> int:
        return self._active_timestep_count

    @property
    def transferred_vehicle_count(self) -> int:
        return self._transferred_vehicle_count

    @property
    def observed_average_outflow_rate(self) -> int | float | None:
        return self._observed_average_outflow_rate

    @property
    def flow_allowance(self) -> float:
        return self._flow_allowance

    @property
    def cumulative_observed_outflow_exit_vehicle_names(self) -> tuple[str, ...]:
        return tuple(self._cumulative_observed_outflow_exit_vehicle_names)

    @property
    def cumulative_constrained_sink_end_trip_vehicle_names(self) -> tuple[str, ...]:
        return tuple(self._cumulative_constrained_sink_end_trip_vehicle_names)

    @property
    def completed_virtual_timesteps(self) -> tuple[int, ...]:
        return tuple(self._completed_virtual_timesteps)

    def completed_process_result(
        self,
        virtual_timestep: int,
    ) -> OrderControlTvtMpOutlinkBoundaryLinkProcessResult | None:
        """Return the saved result for one finished virtual timestep, if any."""
        return self._completed_process_results_by_virtual_timestep.get(
            virtual_timestep
        )


class OrderControlTvtMpCandidateOutlinkBoundaryState:
    """Mutable boundary state for one candidate and one target Node."""

    def __init__(
        self,
        *,
        local_vehicle_advance_state: OrderControlTvtMpCandidateLocalVehicleAdvanceState,
        downstream_boundary_node_result: OrderControlBaselineDownstreamBoundaryNodeResult,
        outlink_states: tuple[OrderControlTvtMpCandidateOutlinkBoundaryLinkState, ...],
    ) -> None:
        self._local_vehicle_advance_state = local_vehicle_advance_state
        self._downstream_boundary_node_result = downstream_boundary_node_result
        self._outlink_states = outlink_states
        self._completed_virtual_timesteps: list[int] = []
        self._vehicle_removal_records: list[
            OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord
        ] = []

    @property
    def local_vehicle_advance_state(
        self,
    ) -> OrderControlTvtMpCandidateLocalVehicleAdvanceState:
        return self._local_vehicle_advance_state

    @property
    def downstream_boundary_node_result(
        self,
    ) -> OrderControlBaselineDownstreamBoundaryNodeResult:
        return self._downstream_boundary_node_result

    @property
    def outlink_states(
        self,
    ) -> tuple[OrderControlTvtMpCandidateOutlinkBoundaryLinkState, ...]:
        return self._outlink_states

    @property
    def completed_virtual_timesteps(self) -> tuple[int, ...]:
        return tuple(self._completed_virtual_timesteps)

    @property
    def vehicle_removal_records(
        self,
    ) -> tuple[OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord, ...]:
        return tuple(self._vehicle_removal_records)


def initialize_tvt_mp_candidate_outlink_boundary_state(
    local_vehicle_advance_state: OrderControlTvtMpCandidateLocalVehicleAdvanceState,
    downstream_boundary_node_result: OrderControlBaselineDownstreamBoundaryNodeResult,
) -> OrderControlTvtMpCandidateOutlinkBoundaryState:
    """Pair copied outlinks with one Node's baseline boundary counts.

    Does not move vehicles or change capacity. ``None`` is refused. An
    observed active count of zero stays a constrained sink and is not
    rewritten into a missing result.
    """
    if downstream_boundary_node_result is None:
        raise RuntimeError(
            "downstream boundary result is missing. An empty baseline is "
            "not an observed active count of zero."
        )
    if not isinstance(
        local_vehicle_advance_state,
        OrderControlTvtMpCandidateLocalVehicleAdvanceState,
    ):
        raise ValueError(
            "local_vehicle_advance_state must be "
            "OrderControlTvtMpCandidateLocalVehicleAdvanceState; got "
            f"type {type(local_vehicle_advance_state).__name__}."
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
    candidate_local_state = _candidate_local_state(local_vehicle_advance_state)
    node_name = candidate_local_state.target_node_name
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
    outlinks = tuple(candidate_local_state.outlinks)
    observed = downstream_boundary_node_result.outlink_results
    if len(observed) != len(outlinks):
        raise RuntimeError(
            f"Node {node_name!r}: downstream boundary has {len(observed)} "
            f"outlinks and the candidate has {len(outlinks)}."
        )
    link_states = []
    for outlink, observed_outlink in zip(outlinks, observed):
        link_states.append(
            _link_state_for_outlink(
                node_name=node_name,
                outlink=outlink,
                observed_outlink=observed_outlink,
            )
        )
    return OrderControlTvtMpCandidateOutlinkBoundaryState(
        local_vehicle_advance_state=local_vehicle_advance_state,
        downstream_boundary_node_result=downstream_boundary_node_result,
        outlink_states=tuple(link_states),
    )


def process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(
    outlink_boundary_state: OrderControlTvtMpCandidateOutlinkBoundaryState,
    local_vehicle_advance_result: OrderControlTvtMpLocalVehicleAdvanceResult,
) -> OrderControlTvtMpOutlinkBoundaryProcessResult:
    """Serve every outlink terminal once at the current virtual timestep.

    Outlinks are independent. A later outlink failure does not undo an
    earlier outlink that already finished. The timestep is marked complete
    only after every outlink returns.
    """
    if not isinstance(
        outlink_boundary_state,
        OrderControlTvtMpCandidateOutlinkBoundaryState,
    ):
        raise ValueError(
            "outlink_boundary_state must be "
            "OrderControlTvtMpCandidateOutlinkBoundaryState; got "
            f"type {type(outlink_boundary_state).__name__}."
        )
    if not isinstance(
        local_vehicle_advance_result,
        OrderControlTvtMpLocalVehicleAdvanceResult,
    ):
        raise ValueError(
            "local_vehicle_advance_result must be "
            "OrderControlTvtMpLocalVehicleAdvanceResult; got "
            f"type {type(local_vehicle_advance_result).__name__}."
        )
    advance_state = outlink_boundary_state.local_vehicle_advance_state
    candidate_local_state = _candidate_local_state(advance_state)
    node_name = candidate_local_state.target_node_name
    local_world = candidate_local_state.local_world
    virtual_timestep = _current_virtual_timestep(advance_state)
    if local_world.T != virtual_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: copied World time {local_world.T} does "
            f"not match virtual timestep {virtual_timestep}."
        )
    if local_vehicle_advance_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: local vehicle advance result node is "
            f"{local_vehicle_advance_result.node_name!r}."
        )
    if local_vehicle_advance_result.virtual_timestep != virtual_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: local vehicle advance result timestep "
            f"{local_vehicle_advance_result.virtual_timestep} does not "
            f"match virtual timestep {virtual_timestep}."
        )
    if virtual_timestep not in advance_state.completed_virtual_timesteps:
        raise RuntimeError(
            f"Node {node_name!r}: local vehicle advance has not finished "
            f"virtual timestep {virtual_timestep}."
        )
    if virtual_timestep in outlink_boundary_state.completed_virtual_timesteps:
        raise RuntimeError(
            f"Node {node_name!r}: outlink boundary processing already "
            f"finished virtual timestep {virtual_timestep}."
        )
    outlink_results = []
    for outlink, link_state in zip(
        candidate_local_state.outlinks,
        outlink_boundary_state.outlink_states,
    ):
        outlink_results.append(
            _process_one_outlink(
                outlink_boundary_state=outlink_boundary_state,
                link_state=link_state,
                outlink=outlink,
                local_world=local_world,
                virtual_timestep=virtual_timestep,
            )
        )
    every_outlink_finished = True
    for link_state in outlink_boundary_state.outlink_states:
        if virtual_timestep not in link_state.completed_virtual_timesteps:
            every_outlink_finished = False
    if (
        every_outlink_finished
        and virtual_timestep
        not in outlink_boundary_state._completed_virtual_timesteps
    ):
        outlink_boundary_state._completed_virtual_timesteps.append(virtual_timestep)
    return OrderControlTvtMpOutlinkBoundaryProcessResult(
        node_name=node_name,
        virtual_timestep=virtual_timestep,
        outlink_results=tuple(outlink_results),
    )


def _candidate_local_state(advance_state):
    return advance_state.binding_transfer_state.virtual_time_state.candidate_local_state


def _current_virtual_timestep(advance_state) -> int:
    return (
        advance_state.binding_transfer_state.virtual_time_state.current_virtual_timestep
    )


def _require_non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative int, not bool; got {value!r}."
        )
    return value


def _require_number(value: object, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a number, not bool; got {value!r}."
        )
    return value


def _boundary_mode(
    active_timestep_count: int,
    transferred_vehicle_count: int,
    *,
    outlink_name: str,
) -> OrderControlTvtMpOutlinkBoundaryMode:
    if active_timestep_count == 0:
        if transferred_vehicle_count != 0:
            raise RuntimeError(
                f"outlink {outlink_name!r}: active_timestep_count is 0 but "
                f"transferred_vehicle_count is {transferred_vehicle_count}. "
                "Observed outflow requires an observed wait."
            )
        return OrderControlTvtMpOutlinkBoundaryMode.NO_OBSERVED_WAIT_CONSTRAINED_SINK
    if transferred_vehicle_count > 0:
        return OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITH_OUTFLOW
    return OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW


def _link_state_for_outlink(
    *,
    node_name: str,
    outlink,
    observed_outlink: OrderControlBaselineDownstreamBoundaryOutlinkResult,
) -> OrderControlTvtMpCandidateOutlinkBoundaryLinkState:
    if not isinstance(
        observed_outlink,
        OrderControlBaselineDownstreamBoundaryOutlinkResult,
    ):
        raise ValueError(
            f"Node {node_name!r}: each downstream outlink result must be "
            "OrderControlBaselineDownstreamBoundaryOutlinkResult."
        )
    if observed_outlink.outlink_name != outlink.name:
        raise RuntimeError(
            f"Node {node_name!r}: outlink order does not match. Candidate "
            f"outlink is {outlink.name!r} and downstream boundary outlink "
            f"is {observed_outlink.outlink_name!r}."
        )
    terminal_node = outlink.end_node
    if terminal_node is None or terminal_node.name != observed_outlink.terminal_node_name:
        copied_name = None if terminal_node is None else terminal_node.name
        raise RuntimeError(
            f"outlink {outlink.name!r}: terminal Node is {copied_name!r}, "
            "not downstream boundary terminal "
            f"{observed_outlink.terminal_node_name!r}."
        )
    active_count = _require_non_negative_int(
        observed_outlink.active_timestep_count,
        f"outlink {outlink.name}.active_timestep_count",
    )
    transferred_count = _require_non_negative_int(
        observed_outlink.transferred_vehicle_count,
        f"outlink {outlink.name}.transferred_vehicle_count",
    )
    mode = _boundary_mode(
        active_count,
        transferred_count,
        outlink_name=outlink.name,
    )
    if mode is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITH_OUTFLOW:
        rate = transferred_count / active_count
    else:
        rate = None
    return OrderControlTvtMpCandidateOutlinkBoundaryLinkState(
        outlink_name=outlink.name,
        terminal_node_name=terminal_node.name,
        boundary_mode=mode,
        active_timestep_count=active_count,
        transferred_vehicle_count=transferred_count,
        observed_average_outflow_rate=rate,
    )


def _record_outlink_completion(link_state, virtual_timestep: int, link_result) -> None:
    """Save one outlink result and mark that virtual timestep complete.

    Both updates belong to the same success. A later failure still rolls
    this outlink back to the snapshot taken before them.
    """
    if virtual_timestep in link_state._completed_virtual_timesteps:
        raise RuntimeError(
            f"outlink {link_state.outlink_name!r}: virtual timestep "
            f"{virtual_timestep} is already complete."
        )
    link_state._completed_process_results_by_virtual_timestep[virtual_timestep] = (
        link_result
    )
    link_state._completed_virtual_timesteps.append(virtual_timestep)


def _process_one_outlink(
    *,
    outlink_boundary_state: OrderControlTvtMpCandidateOutlinkBoundaryState,
    link_state: OrderControlTvtMpCandidateOutlinkBoundaryLinkState,
    outlink,
    local_world,
    virtual_timestep: int,
) -> OrderControlTvtMpOutlinkBoundaryLinkProcessResult:
    if virtual_timestep in link_state._completed_virtual_timesteps:
        saved_result = link_state.completed_process_result(virtual_timestep)
        if saved_result is None:
            raise RuntimeError(
                f"outlink {outlink.name!r}: virtual timestep "
                f"{virtual_timestep} is marked complete but has no saved "
                "boundary result."
            )
        return saved_result
    terminal_node = outlink.end_node
    _prevalidate_outlink(
        link_state=link_state,
        outlink=outlink,
        terminal_node=terminal_node,
        local_world=local_world,
    )
    snapshot = _snapshot_outlink(
        outlink_boundary_state=outlink_boundary_state,
        link_state=link_state,
        outlink=outlink,
        terminal_node=terminal_node,
        local_world=local_world,
    )
    try:
        link_result = _apply_outlink_boundary(
            outlink_boundary_state=outlink_boundary_state,
            link_state=link_state,
            outlink=outlink,
            terminal_node=terminal_node,
            local_world=local_world,
            virtual_timestep=virtual_timestep,
        )
        _record_outlink_completion(
            link_state,
            virtual_timestep,
            link_result,
        )
        return link_result
    except Exception as original_error:
        try:
            _restore_outlink_snapshot(snapshot)
        except Exception as restore_error:
            raise RuntimeError(
                f"outlink {outlink.name!r}: rollback failed ({restore_error})."
            ) from original_error
        raise


def _prevalidate_outlink(*, link_state, outlink, terminal_node, local_world) -> None:
    """Reject corruption before this outlink is changed."""
    if terminal_node is None or terminal_node.name != link_state.terminal_node_name:
        raise RuntimeError(
            f"outlink {outlink.name!r}: terminal Node does not match "
            f"{link_state.terminal_node_name!r}."
        )
    if not isinstance(outlink.cum_departure, list):
        raise RuntimeError(
            f"outlink {outlink.name!r}: cum_departure must be a list."
        )
    if len(outlink.cum_departure) != local_world.T + 1:
        raise RuntimeError(
            f"outlink {outlink.name!r}: len(cum_departure) is "
            f"{len(outlink.cum_departure)}, expected {local_world.T + 1}."
        )
    traveltime_actual = outlink.traveltime_actual
    if not hasattr(traveltime_actual, "__len__") or not hasattr(
        traveltime_actual,
        "__setitem__",
    ):
        raise RuntimeError(
            f"outlink {outlink.name!r}: traveltime_actual cannot be updated."
        )
    _require_number(outlink.capacity_out_remain, f"outlink {outlink.name}.capacity_out_remain")
    if outlink.capacity_out_remain < 0:
        raise RuntimeError(
            f"outlink {outlink.name!r}: capacity_out_remain is negative."
        )
    _require_number(link_state.flow_allowance, f"outlink {outlink.name}.flow_allowance")
    if link_state.flow_allowance < 0:
        raise RuntimeError(
            f"outlink {outlink.name!r}: flow_allowance is negative."
        )
    if _terminal_node_capacity_is_finite(terminal_node):
        _require_number(
            terminal_node.flow_capacity_remain,
            f"terminal Node {terminal_node.name}.flow_capacity_remain",
        )
        if terminal_node.flow_capacity_remain < 0:
            raise RuntimeError(
                f"terminal Node {terminal_node.name!r}: flow_capacity_remain "
                "is negative."
            )
    vehicles = list(outlink.vehicles)
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for vehicle in vehicles:
        if id(vehicle) in seen_ids or vehicle.name in seen_names:
            raise RuntimeError(
                f"outlink {outlink.name!r}: vehicle {vehicle.name!r} is "
                "listed more than once."
            )
        seen_ids.add(id(vehicle))
        seen_names.add(vehicle.name)
    _terminal_prefix_or_raise(
        outlink=outlink,
        local_world=local_world,
        require_traveltime_index=(
            link_state.boundary_mode
            is not OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
        ),
    )


def _terminal_node_capacity_is_finite(terminal_node) -> bool:
    return terminal_node.flow_capacity is not None


def _terminal_prefix_or_raise(
    *,
    outlink,
    local_world,
    require_traveltime_index: bool,
) -> list:
    """Vehicles at the physical head that have already reached the outlink end.

    The first vehicle that has not reached the end stops the scan. Later
    vehicles are not boundary candidates. A broken head registration is an
    error. A head that is simply not at the end is a normal wait.
    """
    vehicles = list(outlink.vehicles)
    prefix = []
    for index, vehicle in enumerate(vehicles):
        _require_vehicle_registration(vehicle, outlink, local_world)
        if vehicle.link is not outlink:
            raise RuntimeError(
                f"outlink {outlink.name!r}: vehicle {vehicle.name!r} is in "
                "the physical queue but its link is different."
            )
        if vehicle.state != "run":
            raise RuntimeError(
                f"outlink {outlink.name!r}: vehicle {vehicle.name!r} state "
                f"is {vehicle.state!r}, expected 'run'."
            )
        if vehicle.x != outlink.length:
            break
        _require_leader_follower(outlink, vehicles, index, vehicle)
        if require_traveltime_index:
            _require_traveltime_start_index(vehicle, outlink, local_world)
        prefix.append(vehicle)
    return prefix


def _require_vehicle_registration(vehicle, outlink, local_world) -> None:
    registered = local_world.VEHICLES.get(vehicle.name)
    running = local_world.VEHICLES_RUNNING.get(vehicle.name)
    living = local_world.VEHICLES_LIVING.get(vehicle.name)
    if registered is not vehicle or running is not vehicle or living is not vehicle:
        raise RuntimeError(
            f"outlink {outlink.name!r}: vehicle {vehicle.name!r} is not "
            "registered consistently in VEHICLES, VEHICLES_RUNNING, and "
            "VEHICLES_LIVING."
        )


def _require_leader_follower(outlink, vehicles, index: int, vehicle) -> None:
    if index == 0:
        if vehicle.leader is not None:
            raise RuntimeError(
                f"outlink {outlink.name!r}: physical head {vehicle.name!r} "
                "has a leader."
            )
    else:
        if vehicle.leader is not vehicles[index - 1]:
            raise RuntimeError(
                f"outlink {outlink.name!r}: vehicle {vehicle.name!r} leader "
                "does not match the previous physical vehicle."
            )
    if index + 1 < len(vehicles):
        follower = vehicles[index + 1]
        if vehicle.follower is not follower:
            raise RuntimeError(
                f"outlink {outlink.name!r}: vehicle {vehicle.name!r} follower "
                "is not the next physical vehicle."
            )
        if follower.link is not outlink or follower.leader is not vehicle:
            raise RuntimeError(
                f"outlink {outlink.name!r}: follower of {vehicle.name!r} "
                "does not point back on this outlink."
            )
    elif vehicle.follower is not None:
        raise RuntimeError(
            f"outlink {outlink.name!r}: last vehicle {vehicle.name!r} has "
            "a follower."
        )


def _require_traveltime_start_index(vehicle, outlink, local_world) -> int:
    _require_number(vehicle.link_arrival_time, f"vehicle {vehicle.name}.link_arrival_time")
    _require_number(local_world.DELTAT, "DELTAT")
    if local_world.DELTAT <= 0:
        raise RuntimeError("DELTAT must be positive.")
    start_timestep = int(vehicle.link_arrival_time / local_world.DELTAT)
    traveltime_length = len(outlink.traveltime_actual)
    if start_timestep < 0 or start_timestep >= traveltime_length:
        raise RuntimeError(
            f"outlink {outlink.name!r}: traveltime_actual start index "
            f"{start_timestep} is outside length {traveltime_length} for "
            f"vehicle {vehicle.name!r}."
        )
    return start_timestep


def _apply_outlink_boundary(
    *,
    outlink_boundary_state,
    link_state,
    outlink,
    terminal_node,
    local_world,
    virtual_timestep: int,
) -> OrderControlTvtMpOutlinkBoundaryLinkProcessResult:
    allowance_before = link_state.flow_allowance
    capacity_before = outlink.capacity_out_remain
    node_capacity_before = terminal_node.flow_capacity_remain
    names_at_end_before = tuple(
        vehicle.name
        for vehicle in _terminal_prefix_or_raise(
            outlink=outlink,
            local_world=local_world,
            require_traveltime_index=(
                link_state.boundary_mode
                is not OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITHOUT_OUTFLOW
            ),
        )
    )
    observed_names: list[str] = []
    sink_names: list[str] = []
    added = 0.0
    mode = link_state.boundary_mode
    if mode is OrderControlTvtMpOutlinkBoundaryMode.OBSERVED_WAIT_WITH_OUTFLOW:
        added = link_state.observed_average_outflow_rate
        link_state._flow_allowance = allowance_before + added
        while _can_take_observed_outflow(link_state, outlink, terminal_node, local_world):
            vehicle = outlink.vehicles[0]
            _exit_by_dedicated_boundary(
                outlink_boundary_state=outlink_boundary_state,
                link_state=link_state,
                outlink=outlink,
                terminal_node=terminal_node,
                vehicle=vehicle,
                local_world=local_world,
                virtual_timestep=virtual_timestep,
            )
            observed_names.append(vehicle.name)
    elif mode is OrderControlTvtMpOutlinkBoundaryMode.NO_OBSERVED_WAIT_CONSTRAINED_SINK:
        while _can_take_constrained_sink(outlink, terminal_node, local_world):
            vehicle = outlink.vehicles[0]
            _exit_by_constrained_sink(
                outlink_boundary_state=outlink_boundary_state,
                link_state=link_state,
                outlink=outlink,
                terminal_node=terminal_node,
                vehicle=vehicle,
                local_world=local_world,
                virtual_timestep=virtual_timestep,
            )
            sink_names.append(vehicle.name)
    waiting_names = tuple(
        vehicle.name
        for vehicle in _terminal_prefix_or_raise(
            outlink=outlink,
            local_world=local_world,
            require_traveltime_index=False,
        )
    )
    return OrderControlTvtMpOutlinkBoundaryLinkProcessResult(
        outlink_name=outlink.name,
        terminal_node_name=terminal_node.name,
        boundary_mode=mode,
        flow_allowance_before=allowance_before,
        flow_allowance_added=added,
        flow_allowance_after=link_state.flow_allowance,
        vehicle_names_at_end_before=names_at_end_before,
        observed_outflow_boundary_exit_vehicle_names=tuple(observed_names),
        constrained_sink_end_trip_vehicle_names=tuple(sink_names),
        waiting_vehicle_names_after=waiting_names,
        capacity_out_remain_before=capacity_before,
        capacity_out_remain_after=outlink.capacity_out_remain,
        terminal_node_flow_capacity_remain_before=node_capacity_before,
        terminal_node_flow_capacity_remain_after=terminal_node.flow_capacity_remain,
    )


def _head_is_waiting_at_end(outlink) -> bool:
    if len(outlink.vehicles) == 0:
        return False
    vehicle = outlink.vehicles[0]
    return (
        vehicle.link is outlink
        and vehicle.state == "run"
        and vehicle.x == outlink.length
    )


def _capacity_allows_one_vehicle(outlink, terminal_node, local_world) -> bool:
    if outlink.capacity_out_remain < local_world.DELTAN:
        return False
    if not _terminal_node_capacity_is_finite(terminal_node):
        return True
    return terminal_node.flow_capacity_remain >= local_world.DELTAN


def _can_take_observed_outflow(link_state, outlink, terminal_node, local_world) -> bool:
    if not _head_is_waiting_at_end(outlink):
        return False
    if link_state.flow_allowance < 1:
        return False
    return _capacity_allows_one_vehicle(outlink, terminal_node, local_world)


def _can_take_constrained_sink(outlink, terminal_node, local_world) -> bool:
    if not _head_is_waiting_at_end(outlink):
        return False
    return _capacity_allows_one_vehicle(outlink, terminal_node, local_world)


def _boundary_exit_time_seconds(local_world):
    return (local_world.T + 1) * local_world.DELTAT


def _append_removal_record(
    *,
    outlink_boundary_state,
    vehicle_name: str,
    outlink_name: str,
    terminal_node_name: str,
    virtual_timestep: int,
    boundary_exit_time_seconds,
    removal_kind: OrderControlTvtMpOutlinkBoundaryRemovalKind,
) -> None:
    for existing in outlink_boundary_state._vehicle_removal_records:
        if existing.vehicle_name == vehicle_name:
            raise RuntimeError(
                f"vehicle {vehicle_name!r} is already in the boundary "
                "removal records."
            )
    outlink_boundary_state._vehicle_removal_records.append(
        OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord(
            vehicle_name=vehicle_name,
            outlink_name=outlink_name,
            terminal_node_name=terminal_node_name,
            virtual_timestep=virtual_timestep,
            boundary_exit_time_seconds=boundary_exit_time_seconds,
            removal_kind=removal_kind,
        )
    )


def _consume_exit_capacity(outlink, terminal_node, local_world) -> None:
    outlink.capacity_out_remain -= local_world.DELTAN
    if _terminal_node_capacity_is_finite(terminal_node):
        terminal_node.flow_capacity_remain -= local_world.DELTAN
    if outlink.capacity_out_remain < 0:
        raise RuntimeError(
            f"outlink {outlink.name!r}: capacity_out_remain became negative."
        )
    if (
        _terminal_node_capacity_is_finite(terminal_node)
        and terminal_node.flow_capacity_remain < 0
    ):
        raise RuntimeError(
            f"terminal Node {terminal_node.name!r}: flow_capacity_remain "
            "became negative."
        )


def _exit_by_dedicated_boundary(
    *,
    outlink_boundary_state,
    link_state,
    outlink,
    terminal_node,
    vehicle,
    local_world,
    virtual_timestep: int,
) -> None:
    """Remove one vehicle without calling ``Vehicle.end_trip``."""
    if len(outlink.vehicles) == 0 or outlink.vehicles[0] is not vehicle:
        raise RuntimeError(
            f"outlink {outlink.name!r}: dedicated boundary exit expected "
            f"{vehicle.name!r} at the physical head."
        )
    _require_vehicle_registration(vehicle, outlink, local_world)
    if vehicle.link is not outlink or vehicle.state != "run":
        raise RuntimeError(
            f"outlink {outlink.name!r}: vehicle {vehicle.name!r} is not "
            "running on this outlink."
        )
    if vehicle.leader is not None:
        raise RuntimeError(
            f"outlink {outlink.name!r}: vehicle {vehicle.name!r} still has "
            "a leader."
        )
    vehicles = list(outlink.vehicles)
    _require_leader_follower(outlink, vehicles, 0, vehicle)
    if len(outlink.cum_departure) != local_world.T + 1:
        raise RuntimeError(
            f"outlink {outlink.name!r}: len(cum_departure) is "
            f"{len(outlink.cum_departure)}, expected {local_world.T + 1}."
        )
    start_timestep = _require_traveltime_start_index(vehicle, outlink, local_world)
    if link_state.flow_allowance < 1:
        raise RuntimeError(
            f"outlink {outlink.name!r}: flow_allowance is below 1."
        )
    if not _capacity_allows_one_vehicle(outlink, terminal_node, local_world):
        raise RuntimeError(
            f"outlink {outlink.name!r}: capacity does not allow one vehicle."
        )
    exit_time = _boundary_exit_time_seconds(local_world)
    outlink.cum_departure[-1] += local_world.DELTAN
    outlink.traveltime_actual[start_timestep:] = (
        exit_time - vehicle.link_arrival_time
    )
    _consume_exit_capacity(outlink, terminal_node, local_world)
    link_state._flow_allowance -= 1
    if link_state.flow_allowance < 0:
        raise RuntimeError(
            f"outlink {outlink.name!r}: flow_allowance became negative."
        )
    follower = vehicle.follower
    if follower is not None:
        follower.leader = None
    vehicle.follower = None
    vehicle.leader = None
    removed = outlink.vehicles.popleft()
    if removed is not vehicle:
        raise RuntimeError(
            f"outlink {outlink.name!r}: popleft removed {removed.name!r}, "
            f"not {vehicle.name!r}."
        )
    del local_world.VEHICLES_RUNNING[vehicle.name]
    del local_world.VEHICLES_LIVING[vehicle.name]
    vehicle.link = None
    vehicle.state = "end"
    _append_removal_record(
        outlink_boundary_state=outlink_boundary_state,
        vehicle_name=vehicle.name,
        outlink_name=outlink.name,
        terminal_node_name=terminal_node.name,
        virtual_timestep=virtual_timestep,
        boundary_exit_time_seconds=exit_time,
        removal_kind=(
            OrderControlTvtMpOutlinkBoundaryRemovalKind.OBSERVED_OUTFLOW_BOUNDARY_EXIT
        ),
    )
    link_state._cumulative_observed_outflow_exit_vehicle_names.append(vehicle.name)


def _exit_by_constrained_sink(
    *,
    outlink_boundary_state,
    link_state,
    outlink,
    terminal_node,
    vehicle,
    local_world,
    virtual_timestep: int,
) -> None:
    """Consume terminal capacity, then let ``end_trip`` remove the vehicle."""
    if len(outlink.vehicles) == 0 or outlink.vehicles[0] is not vehicle:
        raise RuntimeError(
            f"outlink {outlink.name!r}: constrained sink expected "
            f"{vehicle.name!r} at the physical head."
        )
    if not _capacity_allows_one_vehicle(outlink, terminal_node, local_world):
        raise RuntimeError(
            f"outlink {outlink.name!r}: capacity does not allow one vehicle."
        )
    exit_time = _boundary_exit_time_seconds(local_world)
    vehicle_name = vehicle.name
    outlink_name = outlink.name
    terminal_node_name = terminal_node.name
    _consume_exit_capacity(outlink, terminal_node, local_world)
    vehicle.end_trip()
    _append_removal_record(
        outlink_boundary_state=outlink_boundary_state,
        vehicle_name=vehicle_name,
        outlink_name=outlink_name,
        terminal_node_name=terminal_node_name,
        virtual_timestep=virtual_timestep,
        boundary_exit_time_seconds=exit_time,
        removal_kind=(
            OrderControlTvtMpOutlinkBoundaryRemovalKind.CONSTRAINED_SINK_END_TRIP
        ),
    )
    link_state._cumulative_constrained_sink_end_trip_vehicle_names.append(vehicle_name)


def _copy_log_rows(rows) -> list:
    copied = []
    for row in rows:
        if isinstance(row, list):
            copied.append(row.copy())
        else:
            copied.append(row)
    return copied


def _snapshot_outlink(
    *,
    outlink_boundary_state,
    link_state,
    outlink,
    terminal_node,
    local_world,
) -> dict:
    vehicles = []
    for vehicle in list(outlink.vehicles):
        vehicles.append(
            {
                "vehicle": vehicle,
                "state": vehicle.state,
                "link": vehicle.link,
                "leader": vehicle.leader,
                "follower": vehicle.follower,
                "x": vehicle.x,
                "x_old": vehicle.x_old,
                "x_next": vehicle.x_next,
                "v": vehicle.v,
                "move_remain": vehicle.move_remain,
                "arrival_time": vehicle.arrival_time,
                "travel_time": vehicle.travel_time,
                "link_arrival_time": vehicle.link_arrival_time,
                "route_next_link": vehicle.route_next_link,
                "flag_waiting_for_trip_end": vehicle.flag_waiting_for_trip_end,
                "order_control_current_visit": vehicle.order_control_current_visit,
                "order_control_visit_id": vehicle.order_control_visit_id,
                "link_old": vehicle.link_old,
                "route_pref": vehicle.route_pref,
                "flag_trip_aborted": vehicle.flag_trip_aborted,
                "log_t": list(vehicle.log_t),
                "log_state": list(vehicle.log_state),
                "log_link": list(vehicle.log_link),
                "log_x": list(vehicle.log_x),
                "log_s": list(vehicle.log_s),
                "log_v": list(vehicle.log_v),
                "log_lane": list(vehicle.log_lane),
                "log_t_link": _copy_log_rows(vehicle.log_t_link),
                "in_running": vehicle.name in local_world.VEHICLES_RUNNING,
                "in_living": vehicle.name in local_world.VEHICLES_LIVING,
            }
        )
    return {
        "outlink": outlink,
        "terminal_node": terminal_node,
        "local_world": local_world,
        "link_state": link_state,
        "boundary_state": outlink_boundary_state,
        "vehicles_order": list(outlink.vehicles),
        "vehicle_fields": vehicles,
        "capacity_out_remain": outlink.capacity_out_remain,
        "cum_departure": list(outlink.cum_departure),
        "traveltime_actual": np.array(outlink.traveltime_actual, copy=True),
        "flow_capacity_remain": terminal_node.flow_capacity_remain,
        "flow_allowance": link_state.flow_allowance,
        "observed_names": list(
            link_state._cumulative_observed_outflow_exit_vehicle_names
        ),
        "sink_names": list(
            link_state._cumulative_constrained_sink_end_trip_vehicle_names
        ),
        "removal_records": list(outlink_boundary_state._vehicle_removal_records),
        "completed_virtual_timesteps": list(link_state._completed_virtual_timesteps),
        "completed_process_results": dict(
            link_state._completed_process_results_by_virtual_timestep
        ),
        "average_speed": local_world.analyzer.average_speed,
        "average_speed_count": local_world.analyzer.average_speed_count,
    }


def _restore_log_list(target: list, saved: list) -> None:
    target.clear()
    target.extend(saved)


def _restore_outlink_snapshot(snapshot: dict) -> None:
    outlink = snapshot["outlink"]
    terminal_node = snapshot["terminal_node"]
    local_world = snapshot["local_world"]
    link_state = snapshot["link_state"]
    boundary_state = snapshot["boundary_state"]
    outlink.vehicles.clear()
    for vehicle in snapshot["vehicles_order"]:
        outlink.vehicles.append(vehicle)
    outlink.capacity_out_remain = snapshot["capacity_out_remain"]
    outlink.cum_departure[:] = snapshot["cum_departure"]
    outlink.traveltime_actual[:] = snapshot["traveltime_actual"]
    terminal_node.flow_capacity_remain = snapshot["flow_capacity_remain"]
    link_state._flow_allowance = snapshot["flow_allowance"]
    link_state._cumulative_observed_outflow_exit_vehicle_names[:] = snapshot[
        "observed_names"
    ]
    link_state._cumulative_constrained_sink_end_trip_vehicle_names[:] = snapshot[
        "sink_names"
    ]
    boundary_state._vehicle_removal_records[:] = snapshot["removal_records"]
    link_state._completed_virtual_timesteps[:] = snapshot[
        "completed_virtual_timesteps"
    ]
    link_state._completed_process_results_by_virtual_timestep.clear()
    link_state._completed_process_results_by_virtual_timestep.update(
        snapshot["completed_process_results"]
    )
    for saved in snapshot["vehicle_fields"]:
        vehicle = saved["vehicle"]
        vehicle.state = saved["state"]
        vehicle.link = saved["link"]
        vehicle.leader = saved["leader"]
        vehicle.follower = saved["follower"]
        vehicle.x = saved["x"]
        vehicle.x_old = saved["x_old"]
        vehicle.x_next = saved["x_next"]
        vehicle.v = saved["v"]
        vehicle.move_remain = saved["move_remain"]
        vehicle.arrival_time = saved["arrival_time"]
        vehicle.travel_time = saved["travel_time"]
        vehicle.link_arrival_time = saved["link_arrival_time"]
        vehicle.route_next_link = saved["route_next_link"]
        vehicle.flag_waiting_for_trip_end = saved["flag_waiting_for_trip_end"]
        vehicle.order_control_current_visit = saved["order_control_current_visit"]
        vehicle.order_control_visit_id = saved["order_control_visit_id"]
        vehicle.link_old = saved["link_old"]
        vehicle.route_pref = saved["route_pref"]
        vehicle.flag_trip_aborted = saved["flag_trip_aborted"]
        _restore_log_list(vehicle.log_t, saved["log_t"])
        _restore_log_list(vehicle.log_state, saved["log_state"])
        _restore_log_list(vehicle.log_link, saved["log_link"])
        _restore_log_list(vehicle.log_x, saved["log_x"])
        _restore_log_list(vehicle.log_s, saved["log_s"])
        _restore_log_list(vehicle.log_v, saved["log_v"])
        _restore_log_list(vehicle.log_lane, saved["log_lane"])
        _restore_log_list(vehicle.log_t_link, saved["log_t_link"])
        if saved["in_running"]:
            local_world.VEHICLES_RUNNING[vehicle.name] = vehicle
        else:
            local_world.VEHICLES_RUNNING.pop(vehicle.name, None)
        if saved["in_living"]:
            local_world.VEHICLES_LIVING[vehicle.name] = vehicle
        else:
            local_world.VEHICLES_LIVING.pop(vehicle.name, None)
    local_world.analyzer.average_speed = snapshot["average_speed"]
    local_world.analyzer.average_speed_count = snapshot["average_speed_count"]
