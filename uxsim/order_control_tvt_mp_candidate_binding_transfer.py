"""
Pass binding-rank vehicles through one target Node at the current virtual time.

The scan walks the completed binding sequence from the front. A visit that
has not arrived, is not the physical head of its inlink, lacks ordinary
capacity, or lacks outlink entry space stays in the sequence and is skipped
for this timestep. The next binding visit is still tried.

Only unmet clearance ends node passage for this timestep. Skipped visits are
tried again from the front at the next virtual timestep. This stage does not
advance vehicles along a link, refill capacity, or move the virtual clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from uxsim.order_control_tvt_mp_candidate_virtual_time import (
    OrderControlTvtMpCandidateVirtualTimeState,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


class OrderControlTvtMpBindingTransferStopReason(Enum):
    """Why this timestep's binding-rank node passage scan ended."""

    BINDING_SEQUENCE_COMPLETED = "binding_sequence_completed"
    CLEARANCE_NOT_SATISFIED = "clearance_not_satisfied"


class OrderControlTvtMpBindingVisitTemporarySkipReason(Enum):
    """Why one binding visit stays unpassed and the scan continues."""

    NOT_ARRIVED_AT_TARGET_NODE = "not_arrived_at_target_node"
    NOT_INLINK_PHYSICAL_HEAD = "not_inlink_physical_head"
    INLINK_OUTFLOW_CAPACITY_UNAVAILABLE = "inlink_outflow_capacity_unavailable"
    OUTLINK_INFLOW_CAPACITY_UNAVAILABLE = "outlink_inflow_capacity_unavailable"
    NODE_FLOW_CAPACITY_UNAVAILABLE = "node_flow_capacity_unavailable"
    OUTLINK_ENTRY_SPACE_UNAVAILABLE = "outlink_entry_space_unavailable"


@dataclass(frozen=True)
class OrderControlTvtMpBindingVisitTemporarySkip:
    """One binding visit left in place for a later timestep."""

    binding_visit_key: OrderControlTvtVisitKey
    vehicle_name: str
    skip_reason: OrderControlTvtMpBindingVisitTemporarySkipReason


@dataclass(frozen=True)
class OrderControlTvtMpBindingTransferScanResult:
    """What one binding-rank scan did at the current virtual timestep."""

    node_name: str
    virtual_timestep: int
    transferred_binding_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    temporarily_skipped_visits: tuple[OrderControlTvtMpBindingVisitTemporarySkip, ...]
    stop_reason: OrderControlTvtMpBindingTransferStopReason
    stopped_binding_visit_key: OrderControlTvtVisitKey | None


class OrderControlTvtMpCandidateBindingTransferState:
    """Which binding visits this candidate has already passed through the Node.

    The completed binding sequence itself is not edited. A later scan starts
    again at the front. Visits recorded here are not passed a second time.
    Visits that were only skipped are not recorded here, so they are eligible
    again.
    """

    def __init__(
        self,
        virtual_time_state: OrderControlTvtMpCandidateVirtualTimeState,
    ) -> None:
        self._virtual_time_state = virtual_time_state
        self._transferred_binding_visit_keys: list[OrderControlTvtVisitKey] = []

    @property
    def virtual_time_state(self) -> OrderControlTvtMpCandidateVirtualTimeState:
        return self._virtual_time_state

    @property
    def transferred_binding_visit_keys(self) -> tuple[OrderControlTvtVisitKey, ...]:
        return tuple(self._transferred_binding_visit_keys)


def initialize_tvt_mp_candidate_binding_transfer_state(
    virtual_time_state: OrderControlTvtMpCandidateVirtualTimeState,
) -> OrderControlTvtMpCandidateBindingTransferState:
    """Start passage tracking. No vehicle is moved."""
    if not isinstance(
        virtual_time_state,
        OrderControlTvtMpCandidateVirtualTimeState,
    ):
        raise ValueError(
            "virtual_time_state must be "
            "OrderControlTvtMpCandidateVirtualTimeState; got "
            f"type {type(virtual_time_state).__name__}."
        )
    _require_virtual_clock_matches_copied_world(virtual_time_state)
    return OrderControlTvtMpCandidateBindingTransferState(virtual_time_state)


def _require_virtual_clock_matches_copied_world(
    virtual_time_state: OrderControlTvtMpCandidateVirtualTimeState,
) -> int:
    local_world = virtual_time_state.candidate_local_state.local_world
    virtual_timestep = virtual_time_state.current_virtual_timestep
    if local_world.T != virtual_timestep:
        raise RuntimeError(
            "copied World time "
            f"{local_world.T!r} does not match virtual timestep "
            f"{virtual_timestep}. Binding passage does not move the clock."
        )
    if virtual_time_state.simulated_timestep_count != virtual_time_state.current_offset:
        raise RuntimeError(
            "simulated_timestep_count does not equal current_offset."
        )
    return virtual_timestep


def _require_clearance_pair(target_node) -> None:
    last_inlink_is_missing = target_node.last_order_control_inlink is None
    last_timestep_is_missing = target_node.last_order_control_entry_timestep is None
    if last_inlink_is_missing != last_timestep_is_missing:
        raise RuntimeError(
            f"Node {target_node.name!r}: clearance history is only half set; "
            f"last_order_control_inlink={target_node.last_order_control_inlink!r}, "
            "last_order_control_entry_timestep="
            f"{target_node.last_order_control_entry_timestep!r}."
        )


def _clearance_is_satisfied(target_node, inlink, local_world) -> bool:
    """Same rule as order-control clearance: a different inlink must wait."""
    _require_clearance_pair(target_node)
    if target_node.last_order_control_inlink is None:
        return True
    if inlink is target_node.last_order_control_inlink:
        return True
    return (
        local_world.T - target_node.last_order_control_entry_timestep
        > target_node.order_control_clearance_timesteps
    )


def _outlink_has_entry_space(outlink, local_world) -> bool:
    """Same entrance test as ``Node.transfer`` and the BATCH reference."""
    if len(outlink.vehicles) < outlink.number_of_lanes:
        return True
    vehicle_at_entrance = outlink.vehicles[-outlink.number_of_lanes]
    return vehicle_at_entrance.x > outlink.delta_per_lane * local_world.DELTAN


def _formal_outlink(target_node, local_world, route_next_link_name: str):
    if not isinstance(route_next_link_name, str) or route_next_link_name == "":
        raise ValueError(
            f"Node {target_node.name!r}: binding route_next_link_name must be "
            f"a non-empty str; got {route_next_link_name!r}."
        )
    outlink = target_node.outlinks.get(route_next_link_name)
    if outlink is None:
        raise ValueError(
            f"Node {target_node.name!r}: binding route "
            f"{route_next_link_name!r} is not an outlink of the target Node."
        )
    registered_outlink = local_world.get_link(route_next_link_name)
    if outlink is not registered_outlink:
        raise RuntimeError(
            f"Node {target_node.name!r}: outlink {route_next_link_name!r} "
            "is not the link registered in the copied World."
        )
    if outlink.start_node is not target_node:
        raise RuntimeError(
            f"Node {target_node.name!r}: outlink {route_next_link_name!r} "
            "does not leave the copied target Node."
        )
    return outlink


def _require_current_visit_matches_binding_visit(
    *,
    target_node,
    binding_visit,
    local_vehicle,
) -> None:
    visit_key = binding_visit.visit_key
    current_visit = local_vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} has no "
            f"current order-control visit for binding VisitKey {visit_key!r}."
        )
    if current_visit.get("visit_id") != visit_key[1]:
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} current "
            f"visit_id is {current_visit.get('visit_id')!r}, but binding "
            f"VisitKey {visit_key!r} does not match."
        )
    if current_visit.get("node") is not target_node:
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} current "
            "visit node is not the copied target Node."
        )


def _transfer_one_vehicle_like_uxsim(
    *,
    target_node,
    local_world,
    local_vehicle,
    inlink,
    outlink,
) -> None:
    """
    Move one vehicle from an inlink into an outlink.

    The order matches ``Node.transfer`` and BATCH ``_transfer_vehicle_reference``.
    It does not end a trip, choose a new route, or clear every incoming vehicle.
    """
    deltan = local_world.DELTAN
    virtual_time_seconds = local_world.T * local_world.DELTAT
    if len(inlink.vehicles) == 0 or inlink.vehicles[0] is not local_vehicle:
        raise RuntimeError(
            f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} is not "
            f"the physical head of inlink {inlink.name!r}, so it is not moved."
        )
    if inlink.capacity_out_remain - deltan < 0:
        raise RuntimeError(
            f"Node {target_node.name!r}: inlink {inlink.name!r} "
            "capacity_out_remain would become negative."
        )
    if outlink.capacity_in_remain - deltan < 0:
        raise RuntimeError(
            f"Node {target_node.name!r}: outlink {outlink.name!r} "
            "capacity_in_remain would become negative."
        )
    if (
        target_node.flow_capacity is not None
        and target_node.flow_capacity_remain - deltan < 0
    ):
        raise RuntimeError(
            f"Node {target_node.name!r}: flow_capacity_remain would become "
            "negative."
        )
    inlink.cum_departure[-1] += deltan
    outlink.cum_arrival[-1] += deltan
    inlink.traveltime_actual[
        int(local_vehicle.link_arrival_time / local_world.DELTAT) :
    ] = virtual_time_seconds - local_vehicle.link_arrival_time

    local_vehicle.link_arrival_time = virtual_time_seconds
    inlink.capacity_out_remain -= deltan
    outlink.capacity_in_remain -= deltan
    if target_node.flow_capacity is not None:
        target_node.flow_capacity_remain -= deltan

    inlink.vehicles.popleft()
    outlink.vehicles_enter_log[virtual_time_seconds] = local_vehicle
    local_vehicle.link = outlink
    local_vehicle.begin_order_control_visit_on_link_entry()
    local_vehicle.x = 0

    if local_vehicle.follower is not None:
        local_vehicle.follower.leader = None
        local_vehicle.follower = None

    if len(outlink.vehicles) > 0:
        local_vehicle.lane = (
            outlink.vehicles[-1].lane + 1
        ) % outlink.number_of_lanes
    else:
        local_vehicle.lane = 0

    local_vehicle.leader = None
    if len(outlink.vehicles) >= outlink.number_of_lanes:
        local_vehicle.leader = outlink.vehicles[-outlink.number_of_lanes]
        local_vehicle.leader.follower = local_vehicle

    x_next = local_vehicle.move_remain * outlink.u / inlink.u
    if local_vehicle.leader is not None:
        congested_x = (
            local_vehicle.leader.x_old
            - local_vehicle.link.delta_per_lane * local_vehicle.W.DELTAN
        )
        if congested_x < local_vehicle.x:
            congested_x = local_vehicle.x
        if x_next > congested_x:
            x_next = congested_x
    if x_next >= outlink.length:
        x_next = outlink.length

    local_vehicle.x = x_next
    local_vehicle.v += local_vehicle.x / local_world.DELTAT
    local_vehicle.move_remain = 0
    outlink.vehicles.append(local_vehicle)
    target_node.incoming_vehicles.remove(local_vehicle)
    target_node.last_order_control_inlink = inlink
    target_node.last_order_control_entry_timestep = local_world.T


def _skip(
    binding_visit,
    local_vehicle,
    skip_reason: OrderControlTvtMpBindingVisitTemporarySkipReason,
) -> OrderControlTvtMpBindingVisitTemporarySkip:
    return OrderControlTvtMpBindingVisitTemporarySkip(
        binding_visit_key=binding_visit.visit_key,
        vehicle_name=local_vehicle.name,
        skip_reason=skip_reason,
    )


def scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
    binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
) -> OrderControlTvtMpBindingTransferScanResult:
    """
    Try the binding sequence once at the current virtual timestep.

    Already passed visits are left alone. Temporary skips do not remove a
    visit. Unmet clearance returns immediately and does not look at later
    binding visits.
    """
    if not isinstance(
        binding_transfer_state,
        OrderControlTvtMpCandidateBindingTransferState,
    ):
        raise ValueError(
            "binding_transfer_state must be "
            "OrderControlTvtMpCandidateBindingTransferState; got "
            f"type {type(binding_transfer_state).__name__}."
        )
    virtual_time_state = binding_transfer_state.virtual_time_state
    virtual_timestep = _require_virtual_clock_matches_copied_world(virtual_time_state)
    candidate_local_state = virtual_time_state.candidate_local_state
    local_world = candidate_local_state.local_world
    target_node = candidate_local_state.target_node
    binding_pairs = candidate_local_state.binding_visit_local_vehicle_pairs
    binding_visits = candidate_local_state.binding_rank_sequence.visits_in_binding_order
    if len(binding_pairs) != len(binding_visits):
        raise RuntimeError(
            f"Node {target_node.name!r}: binding visit pairs do not match "
            "the completed binding sequence."
        )
    deltan = local_world.DELTAN
    if isinstance(deltan, bool) or not isinstance(deltan, (int, float)) or deltan <= 0:
        raise ValueError(
            f"copied World DELTAN must be a positive number; got {deltan!r}."
        )

    already_transferred = set(binding_transfer_state.transferred_binding_visit_keys)
    transferred_this_scan: list[OrderControlTvtVisitKey] = []
    skipped_this_scan: list[OrderControlTvtMpBindingVisitTemporarySkip] = []
    target_inlinks = set(candidate_local_state.inlinks)

    for binding_index, binding_pair in enumerate(binding_pairs):
        binding_visit = binding_pair.binding_visit
        if binding_visit is not binding_visits[binding_index]:
            raise RuntimeError(
                f"Node {target_node.name!r}: binding pair at index "
                f"{binding_index} is not the visit in binding order."
            )
        if binding_visit.binding_rank != binding_index + 1:
            raise RuntimeError(
                f"Node {target_node.name!r}: binding rank "
                f"{binding_visit.binding_rank} is not index {binding_index} + 1."
            )
        visit_key = binding_visit.visit_key
        if visit_key in already_transferred:
            continue

        local_vehicle = binding_pair.local_vehicle
        if local_vehicle.name != visit_key[0]:
            raise RuntimeError(
                f"Node {target_node.name!r}: local vehicle "
                f"{local_vehicle.name!r} does not match binding VisitKey "
                f"{visit_key!r}."
            )
        if local_world.VEHICLES.get(local_vehicle.name) is not local_vehicle:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                "is not the vehicle registered in the copied World."
            )
        _require_current_visit_matches_binding_visit(
            target_node=target_node,
            binding_visit=binding_visit,
            local_vehicle=local_vehicle,
        )

        inlink = local_vehicle.link
        if inlink not in target_inlinks:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                "is not on a target inlink while its binding visit is still "
                "unpassed."
            )
        vehicles_on_inlink = list(inlink.vehicles)
        if local_vehicle not in vehicles_on_inlink:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                f"is not listed on inlink {inlink.name!r}."
            )
        if local_vehicle not in target_node.incoming_vehicles:
            skipped_this_scan.append(
                _skip(
                    binding_visit,
                    local_vehicle,
                    OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE,
                )
            )
            continue
        if vehicles_on_inlink[0] is not local_vehicle:
            skipped_this_scan.append(
                _skip(
                    binding_visit,
                    local_vehicle,
                    OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_INLINK_PHYSICAL_HEAD,
                )
            )
            continue

        outlink = _formal_outlink(
            target_node,
            local_world,
            binding_visit.route_next_link_name,
        )
        route_next_link = local_vehicle.route_next_link
        if route_next_link is not None and route_next_link.name != outlink.name:
            raise RuntimeError(
                f"Node {target_node.name!r}: Vehicle {local_vehicle.name!r} "
                f"route_next_link {route_next_link.name!r} does not match "
                f"binding route {outlink.name!r}."
            )
        if not _clearance_is_satisfied(target_node, inlink, local_world):
            return OrderControlTvtMpBindingTransferScanResult(
                node_name=target_node.name,
                virtual_timestep=virtual_timestep,
                transferred_binding_visit_keys=tuple(transferred_this_scan),
                temporarily_skipped_visits=tuple(skipped_this_scan),
                stop_reason=(
                    OrderControlTvtMpBindingTransferStopReason.CLEARANCE_NOT_SATISFIED
                ),
                stopped_binding_visit_key=visit_key,
            )
        if inlink.capacity_out_remain < deltan:
            skipped_this_scan.append(
                _skip(
                    binding_visit,
                    local_vehicle,
                    OrderControlTvtMpBindingVisitTemporarySkipReason.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE,
                )
            )
            continue
        if outlink.capacity_in_remain < deltan:
            skipped_this_scan.append(
                _skip(
                    binding_visit,
                    local_vehicle,
                    OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_INFLOW_CAPACITY_UNAVAILABLE,
                )
            )
            continue
        if target_node.flow_capacity_remain < deltan:
            skipped_this_scan.append(
                _skip(
                    binding_visit,
                    local_vehicle,
                    OrderControlTvtMpBindingVisitTemporarySkipReason.NODE_FLOW_CAPACITY_UNAVAILABLE,
                )
            )
            continue
        if not _outlink_has_entry_space(outlink, local_world):
            skipped_this_scan.append(
                _skip(
                    binding_visit,
                    local_vehicle,
                    OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE,
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
        binding_transfer_state._transferred_binding_visit_keys.append(visit_key)
        already_transferred.add(visit_key)
        transferred_this_scan.append(visit_key)

    return OrderControlTvtMpBindingTransferScanResult(
        node_name=target_node.name,
        virtual_timestep=virtual_timestep,
        transferred_binding_visit_keys=tuple(transferred_this_scan),
        temporarily_skipped_visits=tuple(skipped_this_scan),
        stop_reason=(
            OrderControlTvtMpBindingTransferStopReason.BINDING_SEQUENCE_COMPLETED
        ),
        stopped_binding_visit_key=None,
    )
