"""
Physical passage attempts for TVT-MP ranks.

Reads the current incoming vehicles and the node's rank ledger. Does not
import uxsim.uxsim. Does not change the ledger, payments, or formal routes.
On the real world, a confirmed passage records node passage history, then
an actual passage observation when a wait entry exists. It does not build
an actual outcome, run ex-post evaluation, or evaluate roles. It does not
call the downstream observer. A baseline fork records neither.

A TVT rank-applying baseline fork tries confirmed visits in assigned_rank
order, then unconfirmed visits in baseline arrival order. That arrival
order is a temporary scan inside the fork. It is not written to the rank
ledger. A generic baseline fork still uses ordinary merge.
"""

from uxsim.order_control_tvt_mp_actual_passage import (
    commit_tvt_mp_actual_node_passage_history,
    commit_tvt_mp_actual_passage_observation,
    prepare_tvt_mp_actual_node_passage_history,
    prepare_tvt_mp_actual_passage_observation,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


class _ConfirmedPassageCandidate:
    """One confirmed vehicle to try, in assigned_rank order."""

    def __init__(self, vehicle, inlink, outlink, visit_key, assigned_rank):
        self.vehicle = vehicle
        self.inlink = inlink
        self.outlink = outlink
        self.visit_key = visit_key
        self.assigned_rank = assigned_rank


class _UnconfirmedBaselinePassageCandidate:
    """
    One unconfirmed baseline vehicle, ordered by baseline arrival.

    The order is temporary. It is not a confirmed TVT rank.
    """

    def __init__(
        self,
        vehicle,
        inlink,
        outlink,
        visit_key,
        baseline_arrival_timestep,
        arrival_tiebreaker,
        vehicle_id,
    ):
        self.vehicle = vehicle
        self.inlink = inlink
        self.outlink = outlink
        self.visit_key = visit_key
        self.baseline_arrival_timestep = baseline_arrival_timestep
        self.arrival_tiebreaker = arrival_tiebreaker
        self.vehicle_id = vehicle_id


def transfer_tvt_mp_passage_attempts(node):
    """
    Pass vehicles at one time_value node.

    Before reading any rank ledger, classify the caller:

    - no collector: real world, latest confirmed TVT ranks
    - collector with apply_copied_tvt_confirmed_ranks True: TVT baseline
      fork, ranks confirmed before this decision
    - collector with that flag False: generic baseline fork, ordinary merge

    A generic fork does not read the rank ledger. A real world or a TVT
    rank-applying fork with no incoming vehicles returns before the ledger
    check.     One or more incoming vehicles still require that node's ledger.
    On the real world, a successful confirmed passage records node passage
    history. It also records an actual passage observation when a wait
    entry exists. A baseline fork records neither. This function does not
    finish the node transfer and does not call the downstream observer.
    """
    baseline_collector = getattr(node.W, "_order_control_baseline_collector", None)
    if baseline_collector is not None:
        apply_copied_ranks = getattr(
            baseline_collector,
            "apply_copied_tvt_confirmed_ranks",
            None,
        )
        if not isinstance(apply_copied_ranks, bool):
            raise RuntimeError(
                f"Node {node.name}: apply_copied_tvt_confirmed_ranks must be "
                f"a bool, got {apply_copied_ranks!r}."
            )
        if apply_copied_ranks is False:
            node._transfer_normal_merge()
            return None

    snapshot_vehicles = _unique_incoming_snapshot(node)
    if len(snapshot_vehicles) == 0:
        return None

    rank_state = _require_rank_state(node)
    confirmed_candidates, unconfirmed_baseline_vehicles = _classify_snapshot(
        node,
        rank_state,
        snapshot_vehicles,
    )
    # Confirmed visits are tried first. A normal physical skip does not move
    # that visit into the unconfirmed group. Clearance stop ends this timestep
    # before any unconfirmed visit is tried.
    clearance_stopped = _try_confirmed_candidates(node, confirmed_candidates)
    if clearance_stopped:
        return None

    baseline_collector = node.W._order_control_baseline_collector
    if baseline_collector is None:
        return None
    if len(unconfirmed_baseline_vehicles) == 0:
        return None
    _try_unconfirmed_baseline_vehicles(node, unconfirmed_baseline_vehicles)
    return None


def _require_rank_state(node):
    ledgers = getattr(node.W, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(ledgers, dict):
        raise RuntimeError(
            f"Node {node.name}: order_control_tvt_rank_states_by_node_name "
            "is not a dict."
        )
    if node.name not in ledgers:
        raise RuntimeError(
            f"Node {node.name}: TVT rank ledger is missing."
        )
    rank_state = ledgers[node.name]
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(
            f"Node {node.name}: TVT rank ledger has the wrong type."
        )
    if rank_state.node_name != node.name:
        raise RuntimeError(
            f"Node {node.name}: TVT rank ledger node_name is "
            f"{rank_state.node_name!r}."
        )
    return rank_state


def _unique_incoming_snapshot(node):
    snapshot_vehicles = []
    seen_vehicle_ids = set()
    for vehicle in node.incoming_vehicles:
        vehicle_identity = id(vehicle)
        if vehicle_identity in seen_vehicle_ids:
            continue
        seen_vehicle_ids.add(vehicle_identity)
        snapshot_vehicles.append(vehicle)
    return snapshot_vehicles


def _classify_snapshot(node, rank_state, snapshot_vehicles):
    confirmed_candidates = []
    unconfirmed_baseline_vehicles = []
    baseline_collector = node.W._order_control_baseline_collector
    for vehicle in snapshot_vehicles:
        if vehicle.flag_waiting_for_trip_end:
            continue
        current_visit = _require_research_candidate(node, vehicle)
        outlink = vehicle.route_next_link
        inlink = vehicle.link
        visit_key = (vehicle.name, current_visit["visit_id"])
        confirmed = rank_state.is_confirmed(visit_key)
        if baseline_collector is None and not confirmed:
            raise RuntimeError(
                f"Node {node.name}: vehicle {vehicle.name} visit "
                f"{visit_key!r} is not confirmed on the real world."
            )
        if confirmed:
            assigned_rank = rank_state.assigned_rank(visit_key)
            if assigned_rank is None:
                raise RuntimeError(
                    f"Node {node.name}: vehicle {vehicle.name} visit "
                    f"{visit_key!r} is confirmed but assigned_rank is None."
                )
            confirmed_candidates.append(
                _ConfirmedPassageCandidate(
                    vehicle,
                    inlink,
                    outlink,
                    visit_key,
                    assigned_rank,
                )
            )
        else:
            # Membership is fixed at the start of this timestep. A later
            # rebuild from incoming_vehicles would mix in a skipped confirmed
            # visit.
            unconfirmed_baseline_vehicles.append(vehicle)

    _reject_duplicate_assigned_ranks(node, confirmed_candidates)
    confirmed_candidates.sort(key=_assigned_rank_of_candidate)
    return confirmed_candidates, tuple(unconfirmed_baseline_vehicles)


def _assigned_rank_of_candidate(candidate):
    return candidate.assigned_rank


def _reject_duplicate_assigned_ranks(node, confirmed_candidates):
    seen_ranks = {}
    for candidate in confirmed_candidates:
        assigned_rank = candidate.assigned_rank
        if assigned_rank in seen_ranks:
            raise RuntimeError(
                f"Node {node.name}: assigned_rank {assigned_rank} is used by "
                f"both {seen_ranks[assigned_rank]!r} and "
                f"{candidate.vehicle.name!r}."
            )
        seen_ranks[assigned_rank] = candidate.vehicle.name


def _require_research_candidate(node, vehicle):
    if vehicle.state != "run":
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} state is "
            f"{vehicle.state!r}; expected 'run'."
        )
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} has no "
            "order_control_current_visit."
        )
    if current_visit["node"] is not node:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} current visit node "
            "does not match this node."
        )
    if current_visit["inlink"] is not vehicle.link:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} current visit inlink "
            "does not match vehicle.link."
        )
    outlink = vehicle.route_next_link
    if outlink is None:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} has "
            "route_next_link=None. A normal TVT passage candidate requires "
            "a valid outlink."
        )
    if outlink.start_node is not node:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} route_next_link does "
            "not start at this node."
        )
    outlink_is_registered = False
    for registered_outlink in node.outlinks.values():
        if registered_outlink is outlink:
            outlink_is_registered = True
            break
    if not outlink_is_registered:
        raise RuntimeError(
            f"Node {node.name}: vehicle {vehicle.name} route_next_link is "
            "not a registered outlink of this node."
        )
    return current_visit


def _try_confirmed_candidates(node, confirmed_candidates):
    for candidate in confirmed_candidates:
        vehicle = candidate.vehicle
        inlink = candidate.inlink
        outlink = candidate.outlink
        if vehicle not in node.incoming_vehicles:
            continue
        if vehicle.link is not inlink:
            raise RuntimeError(
                f"Node {node.name}: vehicle {vehicle.name} link changed "
                "after classification."
            )
        if _physical_passage_limits_should_skip(node, vehicle, inlink, outlink):
            continue
        if node._order_control_clearance_blocks_passage(vehicle, inlink):
            return True
        # Prepare uses the visit and outlink saved before the move.
        # A baseline fork prepares neither the node passage history nor an
        # actual observation. History covers every confirmed visit. The
        # observation covers a trade-scope wait entry only.
        prepared_history = None
        prepared_actual_passage = None
        if node.W._order_control_baseline_collector is None:
            prepared_history = prepare_tvt_mp_actual_node_passage_history(
                node=node,
                vehicle=candidate.vehicle,
                visit_key=candidate.visit_key,
                actual_outlink=candidate.outlink,
                actual_passage_timestep=node.W.T,
            )
            prepared_actual_passage = prepare_tvt_mp_actual_passage_observation(
                node=node,
                vehicle=candidate.vehicle,
                visit_key=candidate.visit_key,
                actual_outlink=candidate.outlink,
                actual_passage_timestep=node.W.T,
            )
        node._transfer_one_vehicle_between_links(vehicle, inlink, outlink)
        node.last_order_control_inlink = inlink
        node.last_order_control_entry_timestep = node.W.T
        if prepared_history is not None:
            commit_tvt_mp_actual_node_passage_history(prepared_history)
        if prepared_actual_passage is not None:
            commit_tvt_mp_actual_passage_observation(prepared_actual_passage)
    return False


def _physical_passage_limits_should_skip(node, vehicle, inlink, outlink):
    """
    Return True when ordinary physical limits block this vehicle.

    Used by both the confirmed rank scan and the unconfirmed baseline scan.
    This is a temporary skip. It is not an order-control clearance stop.
    Node flow shortage is also a temporary skip: later visits are still
    checked, even when they share the same remaining node flow.
    """
    if len(inlink.vehicles) == 0:
        return True
    if vehicle is not inlink.vehicles[0]:
        return True
    if node.flow_capacity_remain < node.W.DELTAN:
        return True
    if inlink.capacity_out_remain < node.W.DELTAN:
        return True
    if outlink.capacity_in_remain < node.W.DELTAN:
        return True
    entry_has_room = len(outlink.vehicles) < outlink.number_of_lanes
    if not entry_has_room:
        entrance_vehicle = outlink.vehicles[-outlink.number_of_lanes]
        entry_gap = outlink.delta_per_lane * node.W.DELTAN
        if entrance_vehicle.x <= entry_gap:
            return True
    return False


def _baseline_arrival_sort_key(candidate):
    """
    Temporary baseline trial order for one unconfirmed visit.

    Earlier baseline arrival is tried first. The same arrival timestep uses
    the fixed arrival tiebreaker, then vehicle id. Passage time, merge
    priority, and a passage-selection random draw are not part of this key.
    """
    return (
        candidate.baseline_arrival_timestep,
        candidate.arrival_tiebreaker,
        candidate.vehicle_id,
    )


def _require_tvt_rank_applying_baseline_collector(node):
    """This scan is only for a TVT rank-applying baseline fork."""
    baseline_collector = getattr(node.W, "_order_control_baseline_collector", None)
    if baseline_collector is None:
        raise RuntimeError(
            f"Node {node.name}: unconfirmed baseline scan requires a "
            "baseline collector."
        )
    apply_copied_ranks = getattr(
        baseline_collector,
        "apply_copied_tvt_confirmed_ranks",
        None,
    )
    if apply_copied_ranks is not True:
        raise RuntimeError(
            f"Node {node.name}: unconfirmed baseline scan requires "
            "apply_copied_tvt_confirmed_ranks True, got "
            f"{apply_copied_ranks!r}."
        )
    return baseline_collector


def _raise_baseline_rank_field_error(node, vehicle, visit_id, field_name, value):
    raise RuntimeError(
        f"Node {node.name}: vehicle {vehicle.name} visit_id {visit_id} "
        f"baseline field {field_name} is missing or inconsistent; "
        f"got {value!r}."
    )


def _copy_validated_baseline_rank_fields(node, vehicle, visit_id, inlink, outlink, snapshot):
    """
    Read one public collector snapshot and check the arrival-order facts.

    A missing snapshot, a partial arrival record, or a route that does not
    match the live outlink is a broken baseline record. Do not invent an
    order from merge priority or a random draw.
    """
    if not isinstance(snapshot, dict):
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "baseline_visit_snapshot", snapshot
        )
    if snapshot.get("node_name") != node.name:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "node_name", snapshot.get("node_name")
        )
    if snapshot.get("vehicle_name") != vehicle.name:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "vehicle_name", snapshot.get("vehicle_name")
        )
    if snapshot.get("visit_id") != visit_id:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "visit_id", snapshot.get("visit_id")
        )
    if snapshot.get("inlink_name") != inlink.name:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "inlink_name", snapshot.get("inlink_name")
        )

    baseline_arrival_timestep = snapshot.get("baseline_arrival_timestep")
    arrival_tiebreaker = snapshot.get("arrival_tiebreaker")
    vehicle_id = snapshot.get("vehicle_id")
    route_next_link_name = snapshot.get("route_next_link_name")

    if baseline_arrival_timestep is None:
        _raise_baseline_rank_field_error(
            node,
            vehicle,
            visit_id,
            "baseline_arrival_timestep",
            baseline_arrival_timestep,
        )
    if isinstance(baseline_arrival_timestep, bool) or not isinstance(
        baseline_arrival_timestep, int
    ) or baseline_arrival_timestep < 0:
        _raise_baseline_rank_field_error(
            node,
            vehicle,
            visit_id,
            "baseline_arrival_timestep",
            baseline_arrival_timestep,
        )

    if arrival_tiebreaker is None:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "arrival_tiebreaker", arrival_tiebreaker
        )
    if isinstance(arrival_tiebreaker, bool) or not isinstance(
        arrival_tiebreaker, (int, float)
    ):
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "arrival_tiebreaker", arrival_tiebreaker
        )

    if vehicle_id is None:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "vehicle_id", vehicle_id
        )
    if isinstance(vehicle_id, bool) or not isinstance(vehicle_id, int) or vehicle_id < 0:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "vehicle_id", vehicle_id
        )
    if vehicle_id != vehicle.id:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "vehicle_id", vehicle_id
        )

    if route_next_link_name is None or route_next_link_name == "":
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "route_next_link_name", route_next_link_name
        )
    if route_next_link_name != outlink.name:
        _raise_baseline_rank_field_error(
            node, vehicle, visit_id, "route_next_link_name", route_next_link_name
        )

    return baseline_arrival_timestep, arrival_tiebreaker, vehicle_id


def _build_unconfirmed_baseline_candidates(node, unconfirmed_baseline_vehicles):
    """
    Order the fixed unconfirmed set by baseline arrival.

    Vehicles that have not arrived are not in this set. Do not pull extra
    visits from the collector. The collector return order is not the rank.
    """
    baseline_collector = _require_tvt_rank_applying_baseline_collector(node)
    candidates = []
    for vehicle in unconfirmed_baseline_vehicles:
        current_visit = _require_research_candidate(node, vehicle)
        inlink = vehicle.link
        outlink = vehicle.route_next_link
        visit_id = current_visit["visit_id"]
        visit_key = (vehicle.name, visit_id)
        snapshot = baseline_collector.get_baseline_visit_snapshot(
            vehicle.name,
            visit_id,
        )
        if snapshot is None:
            _raise_baseline_rank_field_error(
                node,
                vehicle,
                visit_id,
                "baseline_visit_snapshot",
                None,
            )
        (
            baseline_arrival_timestep,
            arrival_tiebreaker,
            vehicle_id,
        ) = _copy_validated_baseline_rank_fields(
            node,
            vehicle,
            visit_id,
            inlink,
            outlink,
            snapshot,
        )
        candidates.append(
            _UnconfirmedBaselinePassageCandidate(
                vehicle,
                inlink,
                outlink,
                visit_key,
                baseline_arrival_timestep,
                arrival_tiebreaker,
                vehicle_id,
            )
        )
    candidates.sort(key=_baseline_arrival_sort_key)
    return candidates


def _try_unconfirmed_baseline_vehicles(node, unconfirmed_baseline_vehicles):
    """
    Try one timestep of unconfirmed baseline visits in arrival order.

    The set was classified at the start of this timestep. Whether a vehicle
    can pass is read from the live links after the confirmed scan. A normal
    physical block skips only that vehicle. Unmet clearance stops the rest
    of this scan. This helper does not clear incoming_vehicles and does not
    record an actual passage.
    """
    candidates = _build_unconfirmed_baseline_candidates(
        node,
        unconfirmed_baseline_vehicles,
    )
    for candidate in candidates:
        vehicle = candidate.vehicle
        inlink = candidate.inlink
        outlink = candidate.outlink
        if vehicle not in node.incoming_vehicles:
            continue
        if vehicle.link is not inlink:
            raise RuntimeError(
                f"Node {node.name}: vehicle {vehicle.name} link changed "
                "after classification."
            )
        if vehicle.route_next_link is not outlink:
            raise RuntimeError(
                f"Node {node.name}: vehicle {vehicle.name} route_next_link "
                "changed after classification."
            )
        if _physical_passage_limits_should_skip(node, vehicle, inlink, outlink):
            continue
        if node._order_control_clearance_blocks_passage(vehicle, inlink):
            return None
        node._transfer_one_vehicle_between_links(vehicle, inlink, outlink)
        node.last_order_control_inlink = inlink
        node.last_order_control_entry_timestep = node.W.T
    return None
