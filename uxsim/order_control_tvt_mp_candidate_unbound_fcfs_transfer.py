"""
Temporary FCFS passage of vehicles outside the binding rank sequence.

One call handles one virtual timestep. It does not advance the clock, refill
capacity, move vehicles along a link, or write the rank ledger or baseline
collector. Binding visits stay on the binding scan even if that scan skipped
them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferStopReason,
    OrderControlTvtMpBindingTransferScanResult,
    OrderControlTvtMpCandidateBindingTransferState,
    _clearance_is_satisfied,
    _formal_outlink,
    _outlink_has_entry_space,
    _require_virtual_clock_matches_copied_world,
    _transfer_one_vehicle_like_uxsim,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


class OrderControlTvtMpUnboundRouteClassification(Enum):
    """Which route rule was used for one unbound passage."""

    SNAPSHOT_FIXED_ROUTE = "snapshot_fixed_route"
    BASELINE_ARRIVAL_ROUTE = "baseline_arrival_route"
    DETERMINISTIC_VIRTUAL_ROUTE = "deterministic_virtual_route"


class OrderControlTvtMpUnboundTemporarySkipReason(Enum):
    """Ordinary inability. The scan continues with the next candidate."""

    NOT_INLINK_PHYSICAL_HEAD = "not_inlink_physical_head"
    INLINK_OUTFLOW_CAPACITY_UNAVAILABLE = "inlink_outflow_capacity_unavailable"
    OUTLINK_INFLOW_CAPACITY_UNAVAILABLE = "outlink_inflow_capacity_unavailable"
    OUTLINK_ENTRY_SPACE_UNAVAILABLE = "outlink_entry_space_unavailable"
    ACCEPTABLE_OUTLINKS_EMPTY = "acceptable_outlinks_empty"


class OrderControlTvtMpUnboundFcfsStopReason(Enum):
    """Why this timestep's unbound FCFS scan ended."""

    BINDING_CLEARANCE_STOPPED_NOT_STARTED = "binding_clearance_stopped_not_started"
    NODE_FLOW_CAPACITY_UNAVAILABLE_BEFORE_START = (
        "node_flow_capacity_unavailable_before_start"
    )
    CANDIDATES_COMPLETED = "candidates_completed"
    CLEARANCE_NOT_SATISFIED = "clearance_not_satisfied"
    NODE_FLOW_CAPACITY_UNAVAILABLE = "node_flow_capacity_unavailable"


@dataclass(frozen=True)
class OrderControlTvtMpUnboundVehicleTransferRecord:
    """One unbound vehicle that passed the target Node."""

    vehicle_name: str
    inlink_name: str
    outlink_name: str
    route_classification: OrderControlTvtMpUnboundRouteClassification
    virtual_timestep: int
    selection_index: int | None = None
    acceptable_outlink_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrderControlTvtMpUnboundTemporarySkip:
    """One unbound vehicle left in place for a later timestep."""

    vehicle_name: str
    skip_reason: OrderControlTvtMpUnboundTemporarySkipReason


@dataclass(frozen=True)
class OrderControlTvtMpUnboundFcfsTransferResult:
    """What one unbound FCFS scan did at the current virtual timestep."""

    node_name: str
    virtual_timestep: int
    stop_reason: OrderControlTvtMpUnboundFcfsStopReason
    transferred_vehicle_records: tuple[
        OrderControlTvtMpUnboundVehicleTransferRecord, ...
    ]
    temporary_skips: tuple[OrderControlTvtMpUnboundTemporarySkip, ...]
    stopped_vehicle_name: str | None
    candidate_vehicle_names_in_fcfs_order: tuple[str, ...]


class OrderControlTvtMpCandidateUnboundFcfsTransferState:
    """Unbound passages already completed for one candidate.

    The binding sequence and the baseline collector are not edited. A second
    scan at a completed virtual timestep is rejected without changes.
    """

    def __init__(
        self,
        binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
        baseline_collector: OrderControlBaselineCollector,
        snapshot_fixed_visit_keys: tuple[OrderControlTvtVisitKey, ...],
    ) -> None:
        self._binding_transfer_state = binding_transfer_state
        self._baseline_collector = baseline_collector
        self._snapshot_fixed_visit_keys = snapshot_fixed_visit_keys
        self._completed_virtual_timesteps: list[int] = []
        self._transferred_unbound_vehicle_names: list[str] = []

    @property
    def binding_transfer_state(self) -> OrderControlTvtMpCandidateBindingTransferState:
        return self._binding_transfer_state

    @property
    def baseline_collector(self) -> OrderControlBaselineCollector:
        return self._baseline_collector

    @property
    def snapshot_fixed_visit_keys(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return self._snapshot_fixed_visit_keys

    @property
    def completed_virtual_timesteps(self) -> tuple[int, ...]:
        return tuple(self._completed_virtual_timesteps)

    @property
    def transferred_unbound_vehicle_names(self) -> tuple[str, ...]:
        return tuple(self._transferred_unbound_vehicle_names)


def initialize_tvt_mp_candidate_unbound_fcfs_transfer_state(
    binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
    baseline_collector: OrderControlBaselineCollector,
) -> OrderControlTvtMpCandidateUnboundFcfsTransferState:
    """Remember the collector's target-Node visit keys. Traffic is not moved."""
    if not isinstance(
        binding_transfer_state,
        OrderControlTvtMpCandidateBindingTransferState,
    ):
        raise ValueError(
            "binding_transfer_state must be "
            "OrderControlTvtMpCandidateBindingTransferState; got "
            f"type {type(binding_transfer_state).__name__}."
        )
    if not isinstance(baseline_collector, OrderControlBaselineCollector):
        raise ValueError(
            "baseline_collector must be OrderControlBaselineCollector; got "
            f"type {type(baseline_collector).__name__}."
        )
    virtual_time_state = binding_transfer_state.virtual_time_state
    _require_virtual_clock_matches_copied_world(virtual_time_state)
    candidate_local_state = virtual_time_state.candidate_local_state
    target_node_name = candidate_local_state.target_node_name
    sequence = candidate_local_state.binding_rank_sequence
    if sequence.node_name != target_node_name:
        raise RuntimeError(
            f"Node {target_node_name!r}: binding sequence node "
            f"{sequence.node_name!r} does not match the candidate target Node."
        )
    if sequence.baseline_timestep_T != virtual_time_state.baseline_timestep_T:
        raise RuntimeError(
            f"Node {target_node_name!r}: binding baseline timestep "
            f"{sequence.baseline_timestep_T} does not match virtual time "
            f"baseline {virtual_time_state.baseline_timestep_T}."
        )
    if candidate_local_state.real_world_timestep_T != sequence.baseline_timestep_T:
        raise RuntimeError(
            f"Node {target_node_name!r}: copied baseline timestep "
            f"{candidate_local_state.real_world_timestep_T} does not match "
            f"binding baseline {sequence.baseline_timestep_T}."
        )
    exported = baseline_collector.export_node_baseline_visits(target_node_name)
    snapshot_keys: list[OrderControlTvtVisitKey] = []
    for record in exported:
        if not isinstance(record, dict):
            raise RuntimeError(
                f"Node {target_node_name!r}: collector export is not a dict."
            )
        if record.get("node_name") != target_node_name:
            raise RuntimeError(
                f"Node {target_node_name!r}: collector record node "
                f"{record.get('node_name')!r} does not match the target Node."
            )
        vehicle_name = record.get("vehicle_name")
        visit_id = record.get("visit_id")
        if not isinstance(vehicle_name, str) or vehicle_name == "":
            raise RuntimeError(
                f"Node {target_node_name!r}: collector vehicle_name is invalid."
            )
        if isinstance(visit_id, bool) or not isinstance(visit_id, int) or visit_id < 1:
            raise RuntimeError(
                f"Node {target_node_name!r}: collector visit_id is invalid."
            )
        snapshot = baseline_collector.get_baseline_visit_snapshot(
            vehicle_name, visit_id
        )
        if snapshot is None:
            raise RuntimeError(
                f"Node {target_node_name!r}: exported VisitKey "
                f"{(vehicle_name, visit_id)!r} has no collector snapshot."
            )
        if snapshot.get("node_name") != target_node_name:
            raise RuntimeError(
                f"Node {target_node_name!r}: snapshot node does not match."
            )
        if snapshot.get("visit_id") != visit_id:
            raise RuntimeError(
                f"Node {target_node_name!r}: snapshot visit_id does not match."
            )
        snapshot_keys.append((vehicle_name, visit_id))
    return OrderControlTvtMpCandidateUnboundFcfsTransferState(
        binding_transfer_state,
        baseline_collector,
        tuple(snapshot_keys),
    )


def _require_positive_deltan(local_world, target_node) -> float:
    deltan = local_world.DELTAN
    if isinstance(deltan, bool) or not isinstance(deltan, (int, float)) or deltan <= 0:
        raise ValueError(
            f"Node {target_node.name!r}: copied World DELTAN must be a "
            f"positive number; got {deltan!r}."
        )
    return deltan


def _is_research_excluded(local_vehicle) -> bool:
    """Same vehicles the snapshot registration leaves out of the fixed set."""
    if getattr(local_vehicle, "state", None) in ("end", "abort"):
        return True
    if getattr(local_vehicle, "flag_waiting_for_trip_end", 0):
        return True
    if getattr(local_vehicle, "mode", None) == "taxi":
        return True
    if getattr(local_vehicle, "specified_route", None) is not None:
        return True
    dest = getattr(local_vehicle, "dest", None)
    link = getattr(local_vehicle, "link", None)
    if dest is not None and link is not None and dest is link.end_node:
        return True
    return False


def _current_visit_key(target_node, local_vehicle) -> OrderControlTvtVisitKey:
    current_visit = local_vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} is in "
            "incoming_vehicles without a current order-control visit."
        )
    visit_id = current_visit.get("visit_id")
    if isinstance(visit_id, bool) or not isinstance(visit_id, int) or visit_id < 1:
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
            f"visit_id is invalid; got {visit_id!r}."
        )
    if current_visit.get("node") is not target_node:
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} current "
            "visit node is not the copied target Node."
        )
    return (local_vehicle.name, visit_id)


def _fcfs_sort_key(target_node, local_vehicle, real_vehicle_id: int) -> tuple:
    current_visit = local_vehicle.order_control_current_visit
    arrival_time = current_visit.get("arrival_time")
    arrival_tiebreaker = current_visit.get("arrival_tiebreaker")
    if (
        isinstance(arrival_time, bool)
        or not isinstance(arrival_time, (int, float))
        or isinstance(arrival_tiebreaker, bool)
        or not isinstance(arrival_tiebreaker, (int, float))
        or isinstance(real_vehicle_id, bool)
        or not isinstance(real_vehicle_id, int)
    ):
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} FCFS "
            "key is not orderable; "
            f"arrival_time={arrival_time!r}, "
            f"arrival_tiebreaker={arrival_tiebreaker!r}, "
            f"real_vehicle_id={real_vehicle_id!r}."
        )
    return (arrival_time, arrival_tiebreaker, real_vehicle_id)


def _collector_snapshot(baseline_collector, target_node, vehicle_name, visit_id):
    snapshot = baseline_collector.get_baseline_visit_snapshot(vehicle_name, visit_id)
    if snapshot is None:
        raise RuntimeError(
            f"Node {target_node.name!r}: VisitKey {(vehicle_name, visit_id)!r} "
            "is in the snapshot-fixed set but has no collector record. "
            "This is not route class 4."
        )
    if snapshot.get("node_name") != target_node.name:
        raise RuntimeError(
            f"Node {target_node.name!r}: collector record node "
            f"{snapshot.get('node_name')!r} does not match the target Node."
        )
    if snapshot.get("vehicle_name") != vehicle_name or snapshot.get("visit_id") != visit_id:
        raise RuntimeError(
            f"Node {target_node.name!r}: collector record identity does not "
            f"match VisitKey {(vehicle_name, visit_id)!r}."
        )
    return snapshot


def _classify_route(target_node, snapshot):
    was_arrived = snapshot.get("was_arrived_at_snapshot")
    route_name = snapshot.get("route_next_link_name")
    if not isinstance(was_arrived, bool):
        raise RuntimeError(
            f"Node {target_node.name!r}: was_arrived_at_snapshot must be bool."
        )
    route_missing = route_name is None or route_name == ""
    if was_arrived and route_missing:
        raise RuntimeError(
            f"Node {target_node.name!r}: snapshot-arrived Visit "
            f"{snapshot.get('vehicle_name')!r} has no route_next_link_name."
        )
    if was_arrived:
        return (
            OrderControlTvtMpUnboundRouteClassification.SNAPSHOT_FIXED_ROUTE,
            route_name,
        )
    if not route_missing:
        if not isinstance(route_name, str):
            raise RuntimeError(
                f"Node {target_node.name!r}: route_next_link_name must be str "
                f"or empty; got {route_name!r}."
            )
        return (
            OrderControlTvtMpUnboundRouteClassification.BASELINE_ARRIVAL_ROUTE,
            route_name,
        )
    return (
        OrderControlTvtMpUnboundRouteClassification.DETERMINISTIC_VIRTUAL_ROUTE,
        None,
    )


def _acceptable_outlinks(target_node, local_world, deltan) -> list:
    accepted = []
    for outlink in target_node.outlinks.values():
        if outlink.capacity_in_remain < deltan:
            continue
        if not _outlink_has_entry_space(outlink, local_world):
            continue
        accepted.append(outlink)
    accepted.sort(key=lambda outlink: outlink.id)
    return accepted


def _extract_unbound_candidates(
    *,
    unbound_state: OrderControlTvtMpCandidateUnboundFcfsTransferState,
    target_node,
    candidate_local_state,
):
    incoming = list(target_node.incoming_vehicles)
    seen_ids = set()
    for local_vehicle in incoming:
        vehicle_identity = id(local_vehicle)
        if vehicle_identity in seen_ids:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                "is listed twice in incoming_vehicles."
            )
        seen_ids.add(vehicle_identity)
    binding_keys = {
        visit.visit_key
        for visit in candidate_local_state.binding_rank_sequence.visits_in_binding_order
    }
    binding_keys.update(unbound_state.binding_transfer_state.transferred_binding_visit_keys)
    already_transferred = set(unbound_state.transferred_unbound_vehicle_names)
    snapshot_keys = set(unbound_state.snapshot_fixed_visit_keys)
    target_inlinks = set(candidate_local_state.inlinks)
    candidates = []
    for local_vehicle in incoming:
        if local_vehicle.name in already_transferred:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                "was already transferred but is still incoming."
            )
        if _is_research_excluded(local_vehicle):
            continue
        if local_vehicle.link not in target_inlinks:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                "is incoming but not on a target inlink."
            )
        if local_vehicle not in list(local_vehicle.link.vehicles):
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                "is incoming but not listed on its inlink."
            )
        visit_key = _current_visit_key(target_node, local_vehicle)
        if visit_key in binding_keys:
            continue
        if visit_key not in snapshot_keys:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                f"VisitKey {visit_key!r} is outside the snapshot-fixed set. "
                "This is not route class 4."
            )
        candidates.append(local_vehicle)
    ordered = []
    for local_vehicle in candidates:
        real_id = candidate_local_state.real_vehicle_id(local_vehicle.name)
        ordered.append(
            (_fcfs_sort_key(target_node, local_vehicle, real_id), local_vehicle)
        )
    ordered.sort(key=lambda item: item[0])
    return tuple(item[1] for item in ordered)


def _empty_result(
    *,
    node_name: str,
    virtual_timestep: int,
    stop_reason: OrderControlTvtMpUnboundFcfsStopReason,
) -> OrderControlTvtMpUnboundFcfsTransferResult:
    return OrderControlTvtMpUnboundFcfsTransferResult(
        node_name=node_name,
        virtual_timestep=virtual_timestep,
        stop_reason=stop_reason,
        transferred_vehicle_records=(),
        temporary_skips=(),
        stopped_vehicle_name=None,
        candidate_vehicle_names_in_fcfs_order=(),
    )


def _complete(
    unbound_state: OrderControlTvtMpCandidateUnboundFcfsTransferState,
    virtual_timestep: int,
    result: OrderControlTvtMpUnboundFcfsTransferResult,
) -> OrderControlTvtMpUnboundFcfsTransferResult:
    unbound_state._completed_virtual_timesteps.append(virtual_timestep)
    return result


def scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep(
    unbound_fcfs_transfer_state: OrderControlTvtMpCandidateUnboundFcfsTransferState,
    binding_transfer_scan_result: OrderControlTvtMpBindingTransferScanResult,
) -> OrderControlTvtMpUnboundFcfsTransferResult:
    """
    Try unbound vehicles once, in this timestep's FCFS order.

    A second call at the same virtual timestep raises and changes nothing.
    Clearance or node-flow shortage ends the scan. Ordinary inability skips
    only that vehicle.
    """
    if not isinstance(
        unbound_fcfs_transfer_state,
        OrderControlTvtMpCandidateUnboundFcfsTransferState,
    ):
        raise ValueError(
            "unbound_fcfs_transfer_state must be "
            "OrderControlTvtMpCandidateUnboundFcfsTransferState; got "
            f"type {type(unbound_fcfs_transfer_state).__name__}."
        )
    if not isinstance(
        binding_transfer_scan_result,
        OrderControlTvtMpBindingTransferScanResult,
    ):
        raise ValueError(
            "binding_transfer_scan_result must be "
            "OrderControlTvtMpBindingTransferScanResult; got "
            f"type {type(binding_transfer_scan_result).__name__}."
        )
    binding_state = unbound_fcfs_transfer_state.binding_transfer_state
    virtual_time_state = binding_state.virtual_time_state
    virtual_timestep = _require_virtual_clock_matches_copied_world(virtual_time_state)
    if virtual_timestep in unbound_fcfs_transfer_state.completed_virtual_timesteps:
        raise RuntimeError(
            f"virtual timestep {virtual_timestep} was already completed for "
            "unbound FCFS passage."
        )
    candidate_local_state = virtual_time_state.candidate_local_state
    local_world = candidate_local_state.local_world
    target_node = candidate_local_state.target_node
    if binding_transfer_scan_result.node_name != target_node.name:
        raise RuntimeError(
            f"Node {target_node.name!r}: binding scan node "
            f"{binding_transfer_scan_result.node_name!r} does not match."
        )
    if binding_transfer_scan_result.virtual_timestep != virtual_timestep:
        raise RuntimeError(
            f"Node {target_node.name!r}: binding scan timestep "
            f"{binding_transfer_scan_result.virtual_timestep} does not match "
            f"virtual timestep {virtual_timestep}."
        )
    if virtual_time_state.current_virtual_timestep != virtual_timestep:
        raise RuntimeError(
            f"Node {target_node.name!r}: current virtual timestep does not "
            f"match {virtual_timestep}."
        )
    deltan = _require_positive_deltan(local_world, target_node)
    if (
        binding_transfer_scan_result.stop_reason
        is OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
    ):
        return _complete(
            unbound_fcfs_transfer_state,
            virtual_timestep,
            _empty_result(
                node_name=target_node.name,
                virtual_timestep=virtual_timestep,
                stop_reason=(
                    OrderControlTvtMpUnboundFcfsStopReason.BINDING_CLEARANCE_STOPPED_NOT_STARTED
                ),
            ),
        )
    if target_node.flow_capacity_remain < deltan:
        return _complete(
            unbound_fcfs_transfer_state,
            virtual_timestep,
            _empty_result(
                node_name=target_node.name,
                virtual_timestep=virtual_timestep,
                stop_reason=(
                    OrderControlTvtMpUnboundFcfsStopReason.NODE_FLOW_CAPACITY_UNAVAILABLE_BEFORE_START
                ),
            ),
        )

    candidates = _extract_unbound_candidates(
        unbound_state=unbound_fcfs_transfer_state,
        target_node=target_node,
        candidate_local_state=candidate_local_state,
    )
    candidate_names = tuple(vehicle.name for vehicle in candidates)
    transferred: list[OrderControlTvtMpUnboundVehicleTransferRecord] = []
    skipped: list[OrderControlTvtMpUnboundTemporarySkip] = []
    collector = unbound_fcfs_transfer_state.baseline_collector

    for local_vehicle in candidates:
        inlink = local_vehicle.link
        if len(inlink.vehicles) == 0 or inlink.vehicles[0] is not local_vehicle:
            skipped.append(
                OrderControlTvtMpUnboundTemporarySkip(
                    vehicle_name=local_vehicle.name,
                    skip_reason=(
                        OrderControlTvtMpUnboundTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD
                    ),
                )
            )
            continue
        if inlink.capacity_out_remain < deltan:
            skipped.append(
                OrderControlTvtMpUnboundTemporarySkip(
                    vehicle_name=local_vehicle.name,
                    skip_reason=(
                        OrderControlTvtMpUnboundTemporarySkipReason.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE
                    ),
                )
            )
            continue
        if not _clearance_is_satisfied(target_node, inlink, local_world):
            return _complete(
                unbound_fcfs_transfer_state,
                virtual_timestep,
                OrderControlTvtMpUnboundFcfsTransferResult(
                    node_name=target_node.name,
                    virtual_timestep=virtual_timestep,
                    stop_reason=(
                        OrderControlTvtMpUnboundFcfsStopReason.CLEARANCE_NOT_SATISFIED
                    ),
                    transferred_vehicle_records=tuple(transferred),
                    temporary_skips=tuple(skipped),
                    stopped_vehicle_name=local_vehicle.name,
                    candidate_vehicle_names_in_fcfs_order=candidate_names,
                ),
            )
        if target_node.flow_capacity_remain < deltan:
            return _complete(
                unbound_fcfs_transfer_state,
                virtual_timestep,
                OrderControlTvtMpUnboundFcfsTransferResult(
                    node_name=target_node.name,
                    virtual_timestep=virtual_timestep,
                    stop_reason=(
                        OrderControlTvtMpUnboundFcfsStopReason.NODE_FLOW_CAPACITY_UNAVAILABLE
                    ),
                    transferred_vehicle_records=tuple(transferred),
                    temporary_skips=tuple(skipped),
                    stopped_vehicle_name=local_vehicle.name,
                    candidate_vehicle_names_in_fcfs_order=candidate_names,
                ),
            )

        visit_key = _current_visit_key(target_node, local_vehicle)
        snapshot = _collector_snapshot(
            collector, target_node, visit_key[0], visit_key[1]
        )
        classification, route_name = _classify_route(target_node, snapshot)
        selection_index = None
        acceptable_names: tuple[str, ...] = ()
        if classification is OrderControlTvtMpUnboundRouteClassification.DETERMINISTIC_VIRTUAL_ROUTE:
            acceptable = _acceptable_outlinks(target_node, local_world, deltan)
            if len(acceptable) == 0:
                skipped.append(
                    OrderControlTvtMpUnboundTemporarySkip(
                        vehicle_name=local_vehicle.name,
                        skip_reason=(
                            OrderControlTvtMpUnboundTemporarySkipReason.ACCEPTABLE_OUTLINKS_EMPTY
                        ),
                    )
                )
                continue
            real_id = candidate_local_state.real_vehicle_id(local_vehicle.name)
            selection_index = real_id % len(acceptable)
            outlink = acceptable[selection_index]
            acceptable_names = tuple(link.name for link in acceptable)
        else:
            outlink = _formal_outlink(target_node, local_world, route_name)
            if outlink.capacity_in_remain < deltan:
                skipped.append(
                    OrderControlTvtMpUnboundTemporarySkip(
                        vehicle_name=local_vehicle.name,
                        skip_reason=(
                            OrderControlTvtMpUnboundTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE
                        ),
                    )
                )
                continue
            if not _outlink_has_entry_space(outlink, local_world):
                skipped.append(
                    OrderControlTvtMpUnboundTemporarySkip(
                        vehicle_name=local_vehicle.name,
                        skip_reason=(
                            OrderControlTvtMpUnboundTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE
                        ),
                    )
                )
                continue

        _transfer_one_vehicle_like_uxsim(
            target_node=target_node,
            local_world=local_world,
            local_vehicle=local_vehicle,
            inlink=inlink,
            outlink=outlink,
        )
        unbound_fcfs_transfer_state._transferred_unbound_vehicle_names.append(
            local_vehicle.name
        )
        transferred.append(
            OrderControlTvtMpUnboundVehicleTransferRecord(
                vehicle_name=local_vehicle.name,
                inlink_name=inlink.name,
                outlink_name=outlink.name,
                route_classification=classification,
                virtual_timestep=virtual_timestep,
                selection_index=selection_index,
                acceptable_outlink_names=acceptable_names,
            )
        )

    return _complete(
        unbound_fcfs_transfer_state,
        virtual_timestep,
        OrderControlTvtMpUnboundFcfsTransferResult(
            node_name=target_node.name,
            virtual_timestep=virtual_timestep,
            stop_reason=OrderControlTvtMpUnboundFcfsStopReason.CANDIDATES_COMPLETED,
            transferred_vehicle_records=tuple(transferred),
            temporary_skips=tuple(skipped),
            stopped_vehicle_name=None,
            candidate_vehicle_names_in_fcfs_order=candidate_names,
        ),
    )
