"""
Advance local vehicles once after this timestep's binding-rank node passage.

UXsim's main loop computes every running vehicle's next position before any
vehicle moves, then ``Vehicle.update`` applies those positions. A vehicle that
reaches the end of a link is appended to that link's end node
``incoming_vehicles`` during ``Vehicle.update``, which walks
``VEHICLES_LIVING`` in registration order.

This stage follows that order for the candidate's target inlinks and outlinks
only. It does not call ``Vehicle.update``, so it does not choose a route, end
a trip, or leave the outlink. Vehicles already waiting in ``incoming_vehicles``
stay there, including several from the same inlink. Vehicles that reach the
target node during this advance are appended after that existing queue and are
not sent back through node passage in the same virtual timestep.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingTransferScanResult,
    OrderControlTvtMpCandidateBindingTransferState,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey


@dataclass(frozen=True)
class OrderControlTvtMpLocalVehicleAdvanceResult:
    """One local advance and the incoming queue before and after it."""

    node_name: str
    virtual_timestep: int
    advanced_vehicle_names: tuple[str, ...]
    preexisting_incoming_vehicle_names: tuple[str, ...]
    newly_arrived_vehicle_names: tuple[str, ...]
    newly_arrived_binding_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    incoming_vehicle_names_before: tuple[str, ...]
    incoming_vehicle_names_after: tuple[str, ...]


class OrderControlTvtMpCandidateLocalVehicleAdvanceState:
    """Records which virtual timesteps have already advanced local vehicles.

    One candidate advances once at a virtual timestep. A second call at the
    same timestep is rejected. The next timestep is a separate call, after
    the caller has scanned node passage again.
    """

    def __init__(
        self,
        binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
    ) -> None:
        self._binding_transfer_state = binding_transfer_state
        self._completed_virtual_timesteps: list[int] = []

    @property
    def binding_transfer_state(self) -> OrderControlTvtMpCandidateBindingTransferState:
        return self._binding_transfer_state

    @property
    def completed_virtual_timesteps(self) -> tuple[int, ...]:
        return tuple(self._completed_virtual_timesteps)


def initialize_tvt_mp_candidate_local_vehicle_advance_state(
    binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
) -> OrderControlTvtMpCandidateLocalVehicleAdvanceState:
    """Start advance tracking. No vehicle is moved."""
    if not isinstance(
        binding_transfer_state,
        OrderControlTvtMpCandidateBindingTransferState,
    ):
        raise ValueError(
            "binding_transfer_state must be "
            "OrderControlTvtMpCandidateBindingTransferState; got "
            f"type {type(binding_transfer_state).__name__}."
        )
    _require_virtual_clock(binding_transfer_state)
    return OrderControlTvtMpCandidateLocalVehicleAdvanceState(
        binding_transfer_state
    )


def _require_virtual_clock(
    binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
) -> int:
    virtual_time_state = binding_transfer_state.virtual_time_state
    local_world = virtual_time_state.candidate_local_state.local_world
    virtual_timestep = virtual_time_state.current_virtual_timestep
    if local_world.T != virtual_timestep:
        raise RuntimeError(
            "copied World time "
            f"{local_world.T!r} does not match virtual timestep "
            f"{virtual_timestep}. Local vehicle advance does not move the clock."
        )
    if virtual_time_state.simulated_timestep_count != virtual_time_state.current_offset:
        raise RuntimeError(
            "simulated_timestep_count does not equal current_offset."
        )
    return virtual_timestep


def _require_scan_matches_this_timestep(
    *,
    binding_transfer_state: OrderControlTvtMpCandidateBindingTransferState,
    binding_transfer_scan_result: OrderControlTvtMpBindingTransferScanResult,
    virtual_timestep: int,
    node_name: str,
) -> None:
    """The public scan result is the proof that node passage already returned."""
    if binding_transfer_scan_result.virtual_timestep != virtual_timestep:
        raise RuntimeError(
            f"Node {node_name!r}: binding passage scan virtual timestep "
            f"{binding_transfer_scan_result.virtual_timestep} does not match "
            f"current virtual timestep {virtual_timestep}."
        )
    if binding_transfer_scan_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: binding passage scan node is "
            f"{binding_transfer_scan_result.node_name!r}."
        )
    transferred_keys = binding_transfer_state.transferred_binding_visit_keys
    scanned_keys = binding_transfer_scan_result.transferred_binding_visit_keys
    # seq[-0:] is the whole sequence, so an empty scan is checked separately.
    if len(scanned_keys) == 0:
        return
    if transferred_keys[-len(scanned_keys) :] != scanned_keys:
        raise RuntimeError(
            f"Node {node_name!r}: binding passage scan transferred "
            f"{scanned_keys!r}, which is not the end of the recorded "
            f"transferred visits {transferred_keys!r}."
        )


def _require_number(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a number, not bool; got "
            f"type {type(value).__name__} with value {value!r}."
        )


def _unique_target_links(candidate_local_state) -> tuple[list, list]:
    inlinks = []
    seen_inlink_ids: set[int] = set()
    for link in candidate_local_state.inlinks:
        if id(link) in seen_inlink_ids:
            continue
        seen_inlink_ids.add(id(link))
        inlinks.append(link)
    outlinks = []
    seen_outlink_ids: set[int] = set()
    for link in candidate_local_state.outlinks:
        if id(link) in seen_outlink_ids:
            continue
        seen_outlink_ids.add(id(link))
        outlinks.append(link)
    return inlinks, outlinks


def _vehicles_on_target_links(
    *,
    node_name: str,
    target_node,
    inlinks: list,
    outlinks: list,
) -> dict[int, object]:
    """Map vehicle object id to the one target link that currently holds it."""
    link_by_vehicle_id: dict[int, object] = {}
    for link in inlinks:
        if link.end_node is not target_node:
            raise RuntimeError(
                f"Node {node_name!r}: inlink {link.name!r} does not end at "
                "the target Node."
            )
        for vehicle in link.vehicles:
            if id(vehicle) in link_by_vehicle_id:
                other_link = link_by_vehicle_id[id(vehicle)]
                raise RuntimeError(
                    f"Node {node_name!r}: Vehicle {vehicle.name!r} is on both "
                    f"{other_link.name!r} and {link.name!r}."
                )
            link_by_vehicle_id[id(vehicle)] = link
    for link in outlinks:
        if link.start_node is not target_node:
            raise RuntimeError(
                f"Node {node_name!r}: outlink {link.name!r} does not leave "
                "the target Node."
            )
        for vehicle in link.vehicles:
            if id(vehicle) in link_by_vehicle_id:
                other_link = link_by_vehicle_id[id(vehicle)]
                raise RuntimeError(
                    f"Node {node_name!r}: Vehicle {vehicle.name!r} is on both "
                    f"{other_link.name!r} and {link.name!r}."
                )
            link_by_vehicle_id[id(vehicle)] = link
    return link_by_vehicle_id


def _living_target_vehicles(
    *,
    node_name: str,
    local_world,
    link_by_vehicle_id: dict[int, object],
) -> list:
    """Target-link vehicles in ``VEHICLES_LIVING`` registration order."""
    living_vehicles = []
    seen_ids: set[int] = set()
    for vehicle in local_world.VEHICLES_LIVING.values():
        if id(vehicle) not in link_by_vehicle_id:
            continue
        living_vehicles.append(vehicle)
        seen_ids.add(id(vehicle))
    for vehicle_id, link in link_by_vehicle_id.items():
        if vehicle_id in seen_ids:
            continue
        raise RuntimeError(
            f"Node {node_name!r}: a vehicle on link {link.name!r} is not in "
            "VEHICLES_LIVING, so it has no UXsim update order."
        )
    return living_vehicles


def _require_vehicle_can_be_advanced(
    *,
    node_name: str,
    local_world,
    vehicle,
    link,
) -> None:
    if vehicle.state != "run":
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} on link "
            f"{link.name!r} has state {vehicle.state!r}; local advance only "
            "moves running vehicles."
        )
    if vehicle.mode != "single_trip":
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} mode "
            f"{vehicle.mode!r} is not single_trip. This stage does not "
            "implement taxi movement."
        )
    if local_world.VEHICLES_RUNNING.get(vehicle.name) is not vehicle:
        raise RuntimeError(
            f"Node {node_name!r}: running Vehicle {vehicle.name!r} is not "
            "registered in VEHICLES_RUNNING."
        )
    _require_number(vehicle.x, f"Vehicle {vehicle.name}.x")
    _require_number(vehicle.x_old, f"Vehicle {vehicle.name}.x_old")
    _require_number(vehicle.x_next, f"Vehicle {vehicle.name}.x_next")
    _require_number(vehicle.v, f"Vehicle {vehicle.name}.v")
    _require_number(vehicle.move_remain, f"Vehicle {vehicle.name}.move_remain")
    _require_number(link.u, f"Link {link.name}.u")
    _require_number(link.length, f"Link {link.name}.length")
    _require_number(link.delta_per_lane, f"Link {link.name}.delta_per_lane")
    if link.u <= 0:
        raise RuntimeError(
            f"Node {node_name!r}: link {link.name!r} free-flow speed is "
            f"{link.u!r}."
        )
    if vehicle.link is not link:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} link does not "
            f"match the link queue {link.name!r}."
        )
    if vehicle.leader is not None and vehicle.leader.link is not link:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} leader is not on "
            f"link {link.name!r}."
        )
    if vehicle.follower is not None and vehicle.follower.link is not link:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} follower is not on "
            f"link {link.name!r}."
        )
    if vehicle.leader is not None and vehicle.leader.follower is not vehicle:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} leader does not "
            "point back to this vehicle."
        )
    if vehicle.follower is not None and vehicle.follower.leader is not vehicle:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} follower does not "
            "point back to this vehicle."
        )


def _preexisting_incoming_ids(
    *,
    node_name: str,
    target_node,
    inlinks: list,
    link_by_vehicle_id: dict[int, object],
) -> tuple[list, set[int]]:
    preexisting_ids: set[int] = set()
    preexisting_vehicles = []
    inlink_ids = set()
    for link in inlinks:
        inlink_ids.add(id(link))
    for vehicle in target_node.incoming_vehicles:
        if id(vehicle) in preexisting_ids:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {vehicle.name!r} is already "
                "in incoming_vehicles. Duplicate incoming entries are not "
                "removed automatically."
            )
        link = link_by_vehicle_id.get(id(vehicle))
        if link is None or id(link) not in inlink_ids:
            raise RuntimeError(
                f"Node {node_name!r}: incoming Vehicle {vehicle.name!r} is "
                "not on a target inlink."
            )
        preexisting_ids.add(id(vehicle))
        preexisting_vehicles.append(vehicle)
    return preexisting_vehicles, preexisting_ids


def _next_position_like_carfollow(vehicle, link, local_world) -> tuple[float, float]:
    """
    Same arithmetic as ``Vehicle.carfollow``.

    ``leader.x`` is the position before any vehicle in this advance moves.
    The returned move_remain is written only when the free-flow step would
    pass the end of the link. Otherwise the caller's current move_remain
    stays, matching ``carfollow``.
    """
    x_next = vehicle.x + link.u * local_world.DELTAT
    if vehicle.leader is not None:
        congested_x = vehicle.leader.x - link.delta_per_lane * local_world.DELTAN
        if congested_x < vehicle.x:
            congested_x = vehicle.x
        if x_next > congested_x:
            x_next = congested_x
    move_remain = vehicle.move_remain
    if x_next > link.length:
        move_remain = x_next - link.length
        x_next = link.length
    return x_next, move_remain


def _reaches_target_node_as_transfer_request(vehicle, link, target_node, x_next: float) -> bool:
    """
    True when standard ``Vehicle.update`` would append this vehicle.

    A single-trip vehicle whose destination is this node is not appended.
    This stage also does not end that trip. Taxi and dead-end abort are
    rejected earlier or are not a transfer request.
    """
    if x_next != link.length:
        return False
    if link.end_node is not target_node:
        return False
    if vehicle.dest is link.end_node:
        return False
    if len(link.end_node.outlinks.values()) == 0 and vehicle.trip_abort == 1:
        return False
    return True


def _require_new_arrival_visit_is_unrecorded(
    node_name: str,
    vehicle,
    target_node,
) -> None:
    """A new arrival must still have an empty current-visit arrival pair.

    Vehicles already in ``incoming_vehicles`` are not checked here. They may
    already hold ``arrival_time`` and ``arrival_tiebreaker``.
    """
    if not target_node.order_control_eligible or target_node.order_control_type == "none":
        raise RuntimeError(
            f"Node {node_name!r}: cannot record an order-control arrival."
        )
    current_visit = vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} has no current "
            "order-control visit at the new arrival."
        )
    if current_visit.get("node") is not target_node:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} current visit node "
            "is not the copied target Node."
        )
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} current visit_id "
            f"must be a Python int; got {visit_id!r}."
        )
    if "arrival_time" not in current_visit or "arrival_tiebreaker" not in current_visit:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} current visit is "
            "missing arrival_time or arrival_tiebreaker."
        )
    arrival_time = current_visit["arrival_time"]
    arrival_tiebreaker = current_visit["arrival_tiebreaker"]
    # Not yet in incoming_vehicles, so a stored arrival would be a partial
    # record. Both fields must still be None. One field, or both, is enough.
    if arrival_time is not None or arrival_tiebreaker is not None:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle.name!r} would be a new "
            "incoming arrival but the current visit arrival record is already "
            f"set; arrival_time={arrival_time!r}, "
            f"arrival_tiebreaker={arrival_tiebreaker!r}."
        )


def _snapshot_baseline_collector_arrival_fields(local_world):
    """Arrival fields ``record_order_control_node_arrival`` may write.

    Candidate copies of the real World keep this collector as None. When a
    collector is present, only the three arrival fields on each existing
    record are saved. No new record is created by that method.
    """
    collector = local_world._order_control_baseline_collector
    if collector is None:
        return None
    records = getattr(collector, "_visit_records_by_primary_key", None)
    if not isinstance(records, dict):
        raise RuntimeError(
            "copied World baseline collector arrival fields cannot be restored."
        )
    saved_records = []
    for record in records.values():
        saved_records.append(
            (
                record,
                record.baseline_arrival_timestep,
                record.arrival_tiebreaker,
                record.route_next_link_name,
            )
        )
    return saved_records


def _snapshot_local_advance_for_rollback(
    *,
    local_world,
    target_node,
    planned_motions: list,
) -> dict:
    vehicle_motions = []
    new_arrival_records = []
    for motion in planned_motions:
        vehicle = motion["vehicle"]
        vehicle_motions.append(
            (
                vehicle,
                vehicle.x,
                vehicle.x_old,
                vehicle.x_next,
                vehicle.v,
                vehicle.move_remain,
            )
        )
        if not motion["is_new_arrival"]:
            continue
        current_visit = vehicle.order_control_current_visit
        new_arrival_records.append(
            (
                vehicle,
                current_visit,
                current_visit["arrival_time"],
                current_visit["arrival_tiebreaker"],
                dict(vehicle.order_control_node_arrival_times),
                dict(vehicle.order_control_node_arrival_tiebreakers),
            )
        )
    return {
        "vehicle_motions": vehicle_motions,
        "incoming_vehicles": list(target_node.incoming_vehicles),
        "target_node": target_node,
        "new_arrival_records": new_arrival_records,
        "rng_state": copy.deepcopy(local_world.rng.bit_generator.state),
        "order_control_rng_state": copy.deepcopy(
            local_world.order_control_rng.bit_generator.state
        ),
        "local_world": local_world,
        "baseline_collector_records": _snapshot_baseline_collector_arrival_fields(
            local_world
        ),
    }


def _restore_local_advance_snapshot(snapshot: dict) -> None:
    """Put back the copied World fields written by one failed advance."""
    for vehicle, x, x_old, x_next, speed, move_remain in snapshot["vehicle_motions"]:
        vehicle.x = x
        vehicle.x_old = x_old
        vehicle.x_next = x_next
        vehicle.v = speed
        vehicle.move_remain = move_remain
    target_node = snapshot["target_node"]
    target_node.incoming_vehicles[:] = snapshot["incoming_vehicles"]
    for (
        vehicle,
        current_visit,
        arrival_time,
        arrival_tiebreaker,
        arrival_times,
        arrival_tiebreakers,
    ) in snapshot["new_arrival_records"]:
        vehicle.order_control_current_visit = current_visit
        current_visit["arrival_time"] = arrival_time
        current_visit["arrival_tiebreaker"] = arrival_tiebreaker
        vehicle.order_control_node_arrival_times.clear()
        vehicle.order_control_node_arrival_times.update(arrival_times)
        vehicle.order_control_node_arrival_tiebreakers.clear()
        vehicle.order_control_node_arrival_tiebreakers.update(arrival_tiebreakers)
    local_world = snapshot["local_world"]
    local_world.rng.bit_generator.state = snapshot["rng_state"]
    local_world.order_control_rng.bit_generator.state = snapshot[
        "order_control_rng_state"
    ]
    baseline_records = snapshot["baseline_collector_records"]
    if baseline_records is None:
        return
    for record, arrival_timestep, tiebreaker, route_name in baseline_records:
        record.baseline_arrival_timestep = arrival_timestep
        record.arrival_tiebreaker = tiebreaker
        record.route_next_link_name = route_name


def advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
    local_vehicle_advance_state: OrderControlTvtMpCandidateLocalVehicleAdvanceState,
    binding_transfer_scan_result: OrderControlTvtMpBindingTransferScanResult,
) -> OrderControlTvtMpLocalVehicleAdvanceResult:
    """
    Move target-link vehicles one step and append only new node arrivals.

    The scan result must be the binding passage result for this same virtual
    timestep. This function does not scan again and does not advance the clock.
    """
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
        binding_transfer_scan_result,
        OrderControlTvtMpBindingTransferScanResult,
    ):
        raise ValueError(
            "binding_transfer_scan_result must be "
            "OrderControlTvtMpBindingTransferScanResult; got "
            f"type {type(binding_transfer_scan_result).__name__}."
        )
    binding_transfer_state = local_vehicle_advance_state.binding_transfer_state
    virtual_timestep = _require_virtual_clock(binding_transfer_state)
    candidate_local_state = (
        binding_transfer_state.virtual_time_state.candidate_local_state
    )
    local_world = candidate_local_state.local_world
    target_node = candidate_local_state.target_node
    node_name = candidate_local_state.target_node_name
    if virtual_timestep in local_vehicle_advance_state.completed_virtual_timesteps:
        raise RuntimeError(
            f"Node {node_name!r}: local vehicles were already advanced at "
            f"virtual timestep {virtual_timestep}."
        )
    _require_scan_matches_this_timestep(
        binding_transfer_state=binding_transfer_state,
        binding_transfer_scan_result=binding_transfer_scan_result,
        virtual_timestep=virtual_timestep,
        node_name=node_name,
    )
    _require_number(local_world.DELTAT, "local_world.DELTAT")
    _require_number(local_world.DELTAN, "local_world.DELTAN")
    if local_world.DELTAT <= 0 or local_world.DELTAN <= 0:
        raise ValueError(
            "copied World DELTAT and DELTAN must be positive; got "
            f"DELTAT={local_world.DELTAT!r}, DELTAN={local_world.DELTAN!r}."
        )

    inlinks, outlinks = _unique_target_links(candidate_local_state)
    link_by_vehicle_id = _vehicles_on_target_links(
        node_name=node_name,
        target_node=target_node,
        inlinks=inlinks,
        outlinks=outlinks,
    )
    living_vehicles = _living_target_vehicles(
        node_name=node_name,
        local_world=local_world,
        link_by_vehicle_id=link_by_vehicle_id,
    )
    for vehicle in living_vehicles:
        _require_vehicle_can_be_advanced(
            node_name=node_name,
            local_world=local_world,
            vehicle=vehicle,
            link=link_by_vehicle_id[id(vehicle)],
        )
    preexisting_vehicles, preexisting_ids = _preexisting_incoming_ids(
        node_name=node_name,
        target_node=target_node,
        inlinks=inlinks,
        link_by_vehicle_id=link_by_vehicle_id,
    )

    planned_motions = []
    for vehicle in living_vehicles:
        link = link_by_vehicle_id[id(vehicle)]
        x_next, move_remain = _next_position_like_carfollow(
            vehicle,
            link,
            local_world,
        )
        requests_transfer = _reaches_target_node_as_transfer_request(
            vehicle,
            link,
            target_node,
            x_next,
        )
        is_new_arrival = requests_transfer and id(vehicle) not in preexisting_ids
        if is_new_arrival:
            _require_new_arrival_visit_is_unrecorded(node_name, vehicle, target_node)
        planned_motions.append(
            {
                "vehicle": vehicle,
                "link": link,
                "x_next": x_next,
                "move_remain": move_remain,
                "is_new_arrival": is_new_arrival,
            }
        )

    # Checks above do not move vehicles or draw arrival tiebreakers.
    # ``record_order_control_node_arrival`` writes the visit, the first-arrival
    # dictionaries, and one candidate RNG as soon as it is called. Snapshot the
    # copied World first so a later arrival failure puts all of that back.
    arrival_snapshot = _snapshot_local_advance_for_rollback(
        local_world=local_world,
        target_node=target_node,
        planned_motions=planned_motions,
    )
    advanced_names = []
    newly_arrived_names = []
    newly_arrived_visit_keys = []
    try:
        for motion in planned_motions:
            vehicle = motion["vehicle"]
            x_next = motion["x_next"]
            vehicle.v = (x_next - vehicle.x) / local_world.DELTAT
            vehicle.x_old = vehicle.x
            vehicle.x_next = x_next
            vehicle.move_remain = motion["move_remain"]
            vehicle.x = x_next
            advanced_names.append(vehicle.name)
            if not motion["is_new_arrival"]:
                continue
            # Append in living order, then record that same vehicle. The next
            # new arrival is recorded only after this one has succeeded.
            target_node.incoming_vehicles.append(vehicle)
            vehicle.record_order_control_node_arrival(target_node)
            current_visit = vehicle.order_control_current_visit
            newly_arrived_names.append(vehicle.name)
            newly_arrived_visit_keys.append((vehicle.name, current_visit["visit_id"]))
    except Exception as arrival_error:
        try:
            _restore_local_advance_snapshot(arrival_snapshot)
        except Exception as restore_error:
            raise RuntimeError(
                f"Node {node_name!r}: could not restore the copied World after "
                f"{type(arrival_error).__name__}: {arrival_error}. Restore "
                f"error: {restore_error}"
            ) from arrival_error
        raise
    incoming_names_before = []
    for vehicle in preexisting_vehicles:
        incoming_names_before.append(vehicle.name)
    incoming_names_after = []
    for vehicle in target_node.incoming_vehicles:
        incoming_names_after.append(vehicle.name)

    local_vehicle_advance_state._completed_virtual_timesteps.append(virtual_timestep)
    return OrderControlTvtMpLocalVehicleAdvanceResult(
        node_name=node_name,
        virtual_timestep=virtual_timestep,
        advanced_vehicle_names=tuple(advanced_names),
        preexisting_incoming_vehicle_names=tuple(incoming_names_before),
        newly_arrived_vehicle_names=tuple(newly_arrived_names),
        newly_arrived_binding_visit_keys=tuple(newly_arrived_visit_keys),
        incoming_vehicle_names_before=tuple(incoming_names_before),
        incoming_vehicle_names_after=tuple(incoming_names_after),
    )
