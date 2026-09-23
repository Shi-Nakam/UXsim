"""
Build one candidate's independent local state at baseline timestep T.

The copied World keeps the whole network so route, destination, leader, and
registration references stay intact. Vehicles outside the target Node's
inlinks, outlinks, and incoming list remain in the copy, but they are not
local update targets. This stage does not move traffic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingRankVisit,
)
from uxsim.uxsim import World


@dataclass(frozen=True)
class OrderControlTvtMpLocalLinkVehicleState:
    """One copied link and the vehicles already on it, in physical order.

    ``link`` is a live object in the copied World. Later local calculation
    may change that link's traffic state. This dataclass only prevents the
    candidate from swapping which link or which vehicle tuple it holds.
    """

    link_name: str
    link: object
    vehicles_in_physical_order: tuple[object, ...]


@dataclass(frozen=True)
class OrderControlTvtMpBindingVisitLocalVehiclePair:
    """One binding visit and the copied vehicle that is on that visit now.

    ``local_vehicle`` stays mutable. The pair itself cannot be pointed at a
    different visit or a different vehicle after construction.
    """

    binding_visit: OrderControlTvtMpLocalBindingRankVisit
    local_vehicle_name: str
    local_vehicle: object


@dataclass(frozen=True)
class OrderControlTvtMpCandidateLocalState:
    """Which copied objects a later TVT loop may update for one candidate.

    Frozen means the candidate configuration cannot be replaced: the copied
    World, the target Node, the link tuples, the local vehicle tuple, and
    the visit correspondence stay the objects chosen at construction.
    Mapping fields are read-only views.

    The interior of ``local_world`` is not frozen. A later virtual timestep
    loop may change positions, remaining capacity, incoming vehicles, and
    clearance history on these copied objects. That loop is not this stage.
    Objects outside the local sets stay in ``local_world`` and are not
    listed here, because deleting them would break routes and leaders.
    """

    binding_rank_sequence: OrderControlTvtMpLocalBindingRankSequence
    real_world_timestep_T: int
    local_world: World
    target_node_name: str
    target_node: object
    inlinks: tuple[object, ...]
    outlinks: tuple[object, ...]
    local_vehicles: tuple[object, ...]
    inlink_local_vehicle_states: tuple[OrderControlTvtMpLocalLinkVehicleState, ...]
    outlink_local_vehicle_states: tuple[OrderControlTvtMpLocalLinkVehicleState, ...]
    incoming_local_vehicles: tuple[object, ...]
    binding_visit_local_vehicle_pairs: tuple[
        OrderControlTvtMpBindingVisitLocalVehiclePair,
        ...,
    ]
    local_vehicle_by_real_vehicle_name: Mapping[str, object]
    real_vehicle_name_by_local_vehicle_name: Mapping[str, str]


def _require_real_world(real_W: object) -> World:
    if not isinstance(real_W, World):
        raise ValueError(
            "real_W must be a World; got "
            f"type {type(real_W).__name__}."
        )
    if not callable(getattr(real_W, "copy", None)):
        raise ValueError("real_W.copy is not callable.")
    if not callable(getattr(real_W, "get_node", None)):
        raise ValueError("real_W.get_node is not callable.")
    if not isinstance(getattr(real_W, "VEHICLES", None), Mapping):
        raise ValueError("real_W.VEHICLES must be a mapping from name to Vehicle.")
    return real_W


def _require_binding_rank_sequence(
    binding_rank_sequence: object,
) -> OrderControlTvtMpLocalBindingRankSequence:
    if not isinstance(
        binding_rank_sequence,
        OrderControlTvtMpLocalBindingRankSequence,
    ):
        raise ValueError(
            "binding_rank_sequence must be "
            "OrderControlTvtMpLocalBindingRankSequence; got "
            f"type {type(binding_rank_sequence).__name__}."
        )
    return binding_rank_sequence


def _require_timestep_matches_baseline(
    real_W: World,
    binding_rank_sequence: OrderControlTvtMpLocalBindingRankSequence,
) -> int:
    """Compare clock T before copying. Do not restore an earlier time."""
    real_timestep_T = real_W.T
    if type(real_timestep_T) is not int:
        raise ValueError(
            "real_W.T must be a Python int, not bool; got "
            f"type {type(real_timestep_T).__name__} with value {real_timestep_T!r}."
        )
    baseline_timestep_T = binding_rank_sequence.baseline_timestep_T
    if type(baseline_timestep_T) is not int:
        raise ValueError(
            "binding_rank_sequence.baseline_timestep_T must be a Python int, "
            f"not bool; got type {type(baseline_timestep_T).__name__} "
            f"with value {baseline_timestep_T!r}."
        )
    if real_timestep_T != baseline_timestep_T:
        raise ValueError(
            f"real_W.T {real_timestep_T} does not match "
            "binding_rank_sequence.baseline_timestep_T "
            f"{baseline_timestep_T}. The local state is not built, and the "
            "real World is not moved back to an earlier timestep."
        )
    return real_timestep_T


def _copied_target_node(local_world: World, target_node_name: str):
    if not isinstance(target_node_name, str) or target_node_name == "":
        raise ValueError(
            "binding_rank_sequence.node_name must be a non-empty str; "
            f"got {target_node_name!r}."
        )
    try:
        target_node = local_world.get_node(target_node_name)
    except Exception as exc:
        if str(exc) == f"'{target_node_name}' is not Node in this World":
            raise ValueError(
                f"Node {target_node_name!r} is not in the copied World."
            ) from exc
        raise
    if target_node is None:
        raise ValueError(
            f"Node {target_node_name!r} is not in the copied World."
        )
    return target_node


def _require_link_map(link_map: object, *, node_name: str, field_name: str) -> dict:
    if not isinstance(link_map, dict):
        raise ValueError(
            f"Node {node_name!r}: {field_name} must be a dict; got "
            f"type {type(link_map).__name__}."
        )
    return link_map


def _link_vehicle_state(
    link: object,
    *,
    node_name: str,
) -> OrderControlTvtMpLocalLinkVehicleState:
    link_name = getattr(link, "name", None)
    if not isinstance(link_name, str) or link_name == "":
        raise ValueError(
            f"Node {node_name!r}: a target link has no name."
        )
    vehicles = getattr(link, "vehicles", None)
    if vehicles is None:
        raise ValueError(
            f"Node {node_name!r}: link {link_name!r} has no vehicles sequence."
        )
    vehicles_in_physical_order = []
    for vehicle in vehicles:
        vehicles_in_physical_order.append(vehicle)
    return OrderControlTvtMpLocalLinkVehicleState(
        link_name=link_name,
        link=link,
        vehicles_in_physical_order=tuple(vehicles_in_physical_order),
    )


def _link_states_in_registration_order(
    link_map: dict,
    *,
    node_name: str,
) -> tuple[OrderControlTvtMpLocalLinkVehicleState, ...]:
    """Keep Node dict order. That is the registration order, not a new sort."""
    link_states = []
    for link in link_map.values():
        link_states.append(_link_vehicle_state(link, node_name=node_name))
    return tuple(link_states)


def _incoming_local_vehicles(target_node, *, node_name: str) -> tuple[object, ...]:
    incoming_vehicles = getattr(target_node, "incoming_vehicles", None)
    if not isinstance(incoming_vehicles, list):
        raise ValueError(
            f"Node {node_name!r}: incoming_vehicles must be a list; got "
            f"type {type(incoming_vehicles).__name__}."
        )
    incoming_local_vehicles = []
    for vehicle in incoming_vehicles:
        incoming_local_vehicles.append(vehicle)
    return tuple(incoming_local_vehicles)


def _collect_local_vehicles(
    inlink_states: tuple[OrderControlTvtMpLocalLinkVehicleState, ...],
    outlink_states: tuple[OrderControlTvtMpLocalLinkVehicleState, ...],
    incoming_local_vehicles: tuple[object, ...],
) -> tuple[object, ...]:
    """
    Union of inlink, outlink, and incoming vehicles.

    First-seen order is inlink registration order, then each link's physical
    order, then outlinks the same way, then incoming vehicles not already
    included. The same vehicle object is stored once. Membership on each
    link or in the incoming list is kept separately.
    """
    local_vehicles = []
    seen_vehicle_ids: set[int] = set()

    def add_vehicle(vehicle: object) -> None:
        vehicle_identity = id(vehicle)
        if vehicle_identity in seen_vehicle_ids:
            return
        seen_vehicle_ids.add(vehicle_identity)
        local_vehicles.append(vehicle)

    for link_state in inlink_states:
        for vehicle in link_state.vehicles_in_physical_order:
            add_vehicle(vehicle)
    for link_state in outlink_states:
        for vehicle in link_state.vehicles_in_physical_order:
            add_vehicle(vehicle)
    for vehicle in incoming_local_vehicles:
        add_vehicle(vehicle)
    return tuple(local_vehicles)


def _raise_if_link_leaks_to_real_world(
    *,
    node_name: str,
    real_W: World,
    local_world: World,
    link: object,
) -> None:
    link_name = getattr(link, "name", None)
    if not isinstance(link_name, str) or link_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: a copied local vehicle has a link with no name."
        )
    missing_link_message = f"'{link_name}' is not Link in this World"
    try:
        real_link = real_W.get_link(link_name)
    except Exception as exc:
        if str(exc) == missing_link_message:
            raise RuntimeError(
                f"Node {node_name!r}: link {link_name!r} on a copied vehicle "
                "is not registered in the real World."
            ) from exc
        raise
    if link is real_link:
        raise RuntimeError(
            f"Node {node_name!r}: copied vehicle still references real link "
            f"{link_name!r}."
        )
    try:
        local_link = local_world.get_link(link_name)
    except Exception as exc:
        if str(exc) == missing_link_message:
            raise RuntimeError(
                f"Node {node_name!r}: link {link_name!r} on a copied vehicle "
                "is not registered in the copied World."
            ) from exc
        raise
    if link is not local_link:
        raise RuntimeError(
            f"Node {node_name!r}: copied vehicle link {link_name!r} is not "
            "the link registered in the copied World."
        )


def _raise_if_route_next_link_stays_in_copy(
    *,
    node_name: str,
    real_W: World,
    local_world: World,
    vehicle: object,
) -> None:
    """
    Check the planned next link, not the link the vehicle is on now.

    ``route_next_link`` may be None on trip-end or outlink vehicles. When it
    is set, it must name a link registered in the copied World, not the real
    World.
    """
    route_next_link = getattr(vehicle, "route_next_link", None)
    if route_next_link is None:
        return
    vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: a local vehicle with route_next_link "
            f"{route_next_link!r} has no vehicle name."
        )
    link_name = getattr(route_next_link, "name", None)
    if not isinstance(link_name, str) or link_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} route_next_link "
            f"{route_next_link!r} has no valid link name."
        )
    missing_link_message = f"'{link_name}' is not Link in this World"
    try:
        real_link = real_W.get_link(link_name)
    except Exception as exc:
        if str(exc) == missing_link_message:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {vehicle_name!r} route_next_link "
                f"{link_name!r} is not registered in the real World."
            ) from exc
        raise
    if route_next_link is real_link:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} route_next_link "
            f"references the real World link {link_name!r}."
        )
    try:
        local_link = local_world.get_link(link_name)
    except Exception as exc:
        if str(exc) == missing_link_message:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {vehicle_name!r} route_next_link "
                f"{link_name!r} is not registered in the copied World."
            ) from exc
        raise
    if route_next_link is not local_link:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {vehicle_name!r} route_next_link "
            f"{link_name!r} is not the link registered in the copied World."
        )


def _raise_if_vehicle_leaks_to_real_world(
    *,
    node_name: str,
    real_W: World,
    local_world: World,
    vehicle: object,
    role_label: str,
) -> None:
    vehicle_name = getattr(vehicle, "name", None)
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: a {role_label} has no vehicle name."
        )
    real_vehicle = real_W.VEHICLES.get(vehicle_name)
    if vehicle is real_vehicle:
        raise RuntimeError(
            f"Node {node_name!r}: {role_label} {vehicle_name!r} is the real "
            "World vehicle."
        )
    if local_world.VEHICLES.get(vehicle_name) is not vehicle:
        raise RuntimeError(
            f"Node {node_name!r}: {role_label} {vehicle_name!r} is not the "
            "vehicle registered in the copied World."
        )


def _verify_local_reference_stays_in_copy(
    *,
    node_name: str,
    real_W: World,
    local_world: World,
    target_node,
    inlink_states: tuple[OrderControlTvtMpLocalLinkVehicleState, ...],
    outlink_states: tuple[OrderControlTvtMpLocalLinkVehicleState, ...],
    incoming_local_vehicles: tuple[object, ...],
    local_vehicles: tuple[object, ...],
) -> None:
    """Reject copied objects that still point at the real World."""
    real_target_node = real_W.get_node(node_name)
    if target_node is real_target_node:
        raise RuntimeError(
            f"Node {node_name!r}: copied target Node is the real Node."
        )
    for link_state in inlink_states + outlink_states:
        _raise_if_link_leaks_to_real_world(
            node_name=node_name,
            real_W=real_W,
            local_world=local_world,
            link=link_state.link,
        )
        for vehicle in link_state.vehicles_in_physical_order:
            _raise_if_vehicle_leaks_to_real_world(
                node_name=node_name,
                real_W=real_W,
                local_world=local_world,
                vehicle=vehicle,
                role_label="link vehicle",
            )
            if vehicle.link is not link_state.link:
                raise RuntimeError(
                    f"Node {node_name!r}: Vehicle {vehicle.name!r} is listed on "
                    f"link {link_state.link_name!r} but its link is different."
                )
            for neighbor, neighbor_label in (
                (vehicle.leader, "leader"),
                (vehicle.follower, "follower"),
            ):
                if neighbor is None:
                    continue
                _raise_if_vehicle_leaks_to_real_world(
                    node_name=node_name,
                    real_W=real_W,
                    local_world=local_world,
                    vehicle=neighbor,
                    role_label=neighbor_label,
                )
    for vehicle in incoming_local_vehicles:
        _raise_if_vehicle_leaks_to_real_world(
            node_name=node_name,
            real_W=real_W,
            local_world=local_world,
            vehicle=vehicle,
            role_label="incoming vehicle",
        )
    for vehicle in local_vehicles:
        if vehicle.link is not None:
            _raise_if_link_leaks_to_real_world(
                node_name=node_name,
                real_W=real_W,
                local_world=local_world,
                link=vehicle.link,
            )
        _raise_if_route_next_link_stays_in_copy(
            node_name=node_name,
            real_W=real_W,
            local_world=local_world,
            vehicle=vehicle,
        )


def _current_visit_matches_binding_visit(
    *,
    node_name: str,
    target_node,
    binding_visit: OrderControlTvtMpLocalBindingRankVisit,
    local_vehicle,
    expected_visit_id: int,
) -> None:
    current_visit = local_vehicle.order_control_current_visit
    if not isinstance(current_visit, dict):
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {local_vehicle.name!r} has no current "
            "order-control visit dict, so VisitKey "
            f"{binding_visit.visit_key!r} cannot be matched."
        )
    actual_visit_id = current_visit.get("visit_id")
    if type(actual_visit_id) is not int or actual_visit_id != expected_visit_id:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {local_vehicle.name!r} current "
            f"visit_id is {actual_visit_id!r}, but binding VisitKey "
            f"{binding_visit.visit_key!r} requires visit_id {expected_visit_id!r}."
        )
    visit_node = current_visit.get("node")
    visit_node_name = getattr(visit_node, "name", None)
    if visit_node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {local_vehicle.name!r} current visit "
            f"node is {visit_node_name!r}, not the binding target Node."
        )
    if visit_node is not target_node:
        raise RuntimeError(
            f"Node {node_name!r}: Vehicle {local_vehicle.name!r} current visit "
            "node is not the copied target Node."
        )


def _pair_binding_visits_with_local_vehicles(
    *,
    node_name: str,
    local_world: World,
    target_node,
    binding_visits: tuple[OrderControlTvtMpLocalBindingRankVisit, ...],
    local_vehicles: tuple[object, ...],
) -> tuple[OrderControlTvtMpBindingVisitLocalVehiclePair, ...]:
    local_vehicle_ids = set()
    for local_vehicle in local_vehicles:
        local_vehicle_ids.add(id(local_vehicle))
    pairs = []
    for binding_visit in binding_visits:
        visit_key = binding_visit.visit_key
        if not isinstance(visit_key, tuple) or len(visit_key) != 2:
            raise ValueError(
                f"Node {node_name!r}: binding visit_key must be "
                f"(vehicle_name, visit_id); got {visit_key!r}."
            )
        vehicle_name, expected_visit_id = visit_key
        if not isinstance(vehicle_name, str) or vehicle_name == "":
            raise ValueError(
                f"Node {node_name!r}: binding VisitKey {visit_key!r} has no "
                "vehicle name."
            )
        if type(expected_visit_id) is not int:
            raise ValueError(
                f"Node {node_name!r}: binding VisitKey {visit_key!r} visit_id "
                "must be a Python int."
            )
        local_vehicle = local_world.VEHICLES.get(vehicle_name)
        if local_vehicle is None:
            raise ValueError(
                f"Node {node_name!r}: binding VisitKey {visit_key!r} has no "
                "Vehicle in the copied World."
            )
        if local_vehicle.name != vehicle_name:
            raise RuntimeError(
                f"Node {node_name!r}: copied Vehicle name {local_vehicle.name!r} "
                f"does not match binding VisitKey {visit_key!r}."
            )
        if local_vehicle.id != binding_visit.vehicle_id:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {vehicle_name!r} id "
                f"{local_vehicle.id!r} does not match binding vehicle_id "
                f"{binding_visit.vehicle_id!r}."
            )
        _current_visit_matches_binding_visit(
            node_name=node_name,
            target_node=target_node,
            binding_visit=binding_visit,
            local_vehicle=local_vehicle,
            expected_visit_id=expected_visit_id,
        )
        if id(local_vehicle) not in local_vehicle_ids:
            raise RuntimeError(
                f"Node {node_name!r}: binding VisitKey {visit_key!r} matches "
                "a copied Vehicle that is outside the local vehicle set."
            )
        pairs.append(
            OrderControlTvtMpBindingVisitLocalVehiclePair(
                binding_visit=binding_visit,
                local_vehicle_name=local_vehicle.name,
                local_vehicle=local_vehicle,
            )
        )
    return tuple(pairs)


def _real_and_local_vehicle_name_maps(
    *,
    node_name: str,
    real_W: World,
    local_vehicles: tuple[object, ...],
) -> tuple[dict[str, object], dict[str, str]]:
    local_vehicle_by_real_vehicle_name: dict[str, object] = {}
    real_vehicle_name_by_local_vehicle_name: dict[str, str] = {}
    for local_vehicle in local_vehicles:
        local_vehicle_name = local_vehicle.name
        real_vehicle = real_W.VEHICLES.get(local_vehicle_name)
        if real_vehicle is None:
            raise RuntimeError(
                f"Node {node_name!r}: copied local Vehicle "
                f"{local_vehicle_name!r} has no same-named real Vehicle."
            )
        if real_vehicle is local_vehicle:
            raise RuntimeError(
                f"Node {node_name!r}: local Vehicle {local_vehicle_name!r} "
                "is the real Vehicle object."
            )
        if real_vehicle.name != local_vehicle_name:
            raise RuntimeError(
                f"Node {node_name!r}: real Vehicle name {real_vehicle.name!r} "
                f"does not match local Vehicle {local_vehicle_name!r}."
            )
        if real_vehicle.id != local_vehicle.id:
            raise RuntimeError(
                f"Node {node_name!r}: Vehicle {local_vehicle_name!r} id differs "
                f"between real ({real_vehicle.id!r}) and copy "
                f"({local_vehicle.id!r})."
            )
        local_vehicle_by_real_vehicle_name[real_vehicle.name] = local_vehicle
        real_vehicle_name_by_local_vehicle_name[local_vehicle_name] = (
            real_vehicle.name
        )
    return (
        local_vehicle_by_real_vehicle_name,
        real_vehicle_name_by_local_vehicle_name,
    )


def build_tvt_mp_candidate_local_state(
    real_W: World,
    binding_rank_sequence: OrderControlTvtMpLocalBindingRankSequence,
) -> OrderControlTvtMpCandidateLocalState:
    """
    Copy the real World at baseline timestep T and name the local targets.

    One call makes one new copy. Another candidate, or another call for the
    same candidate, gets another copy. Traffic is not moved, capacity is not
    changed, and objects outside the target inlinks, outlinks, and incoming
    list are left in the copy but omitted from the local sets.
    """
    real_world = _require_real_world(real_W)
    sequence = _require_binding_rank_sequence(binding_rank_sequence)
    real_world_timestep_T = _require_timestep_matches_baseline(
        real_world,
        sequence,
    )
    if not isinstance(sequence.node_name, str) or sequence.node_name == "":
        raise ValueError(
            "binding_rank_sequence.node_name must be a non-empty str; "
            f"got {sequence.node_name!r}."
        )
    local_world = real_world.copy()
    if local_world is real_world:
        raise RuntimeError("Copied World is the real World object.")
    if not isinstance(local_world, World):
        raise RuntimeError(
            "Copied World must be a World; got "
            f"type {type(local_world).__name__}."
        )

    target_node_name = sequence.node_name
    target_node = _copied_target_node(local_world, target_node_name)
    inlink_map = _require_link_map(
        target_node.inlinks,
        node_name=target_node_name,
        field_name="inlinks",
    )
    outlink_map = _require_link_map(
        target_node.outlinks,
        node_name=target_node_name,
        field_name="outlinks",
    )
    inlink_states = _link_states_in_registration_order(
        inlink_map,
        node_name=target_node_name,
    )
    outlink_states = _link_states_in_registration_order(
        outlink_map,
        node_name=target_node_name,
    )
    incoming_vehicles = _incoming_local_vehicles(
        target_node,
        node_name=target_node_name,
    )
    local_vehicles = _collect_local_vehicles(
        inlink_states,
        outlink_states,
        incoming_vehicles,
    )
    _verify_local_reference_stays_in_copy(
        node_name=target_node_name,
        real_W=real_world,
        local_world=local_world,
        target_node=target_node,
        inlink_states=inlink_states,
        outlink_states=outlink_states,
        incoming_local_vehicles=incoming_vehicles,
        local_vehicles=local_vehicles,
    )
    binding_pairs = _pair_binding_visits_with_local_vehicles(
        node_name=target_node_name,
        local_world=local_world,
        target_node=target_node,
        binding_visits=sequence.visits_in_binding_order,
        local_vehicles=local_vehicles,
    )
    (
        local_vehicle_by_real_vehicle_name,
        real_vehicle_name_by_local_vehicle_name,
    ) = _real_and_local_vehicle_name_maps(
        node_name=target_node_name,
        real_W=real_world,
        local_vehicles=local_vehicles,
    )
    inlinks = []
    for link_state in inlink_states:
        inlinks.append(link_state.link)
    outlinks = []
    for link_state in outlink_states:
        outlinks.append(link_state.link)
    return OrderControlTvtMpCandidateLocalState(
        binding_rank_sequence=sequence,
        real_world_timestep_T=real_world_timestep_T,
        local_world=local_world,
        target_node_name=target_node_name,
        target_node=target_node,
        inlinks=tuple(inlinks),
        outlinks=tuple(outlinks),
        local_vehicles=local_vehicles,
        inlink_local_vehicle_states=inlink_states,
        outlink_local_vehicle_states=outlink_states,
        incoming_local_vehicles=incoming_vehicles,
        binding_visit_local_vehicle_pairs=binding_pairs,
        local_vehicle_by_real_vehicle_name=MappingProxyType(
            local_vehicle_by_real_vehicle_name
        ),
        real_vehicle_name_by_local_vehicle_name=MappingProxyType(
            real_vehicle_name_by_local_vehicle_name
        ),
    )
