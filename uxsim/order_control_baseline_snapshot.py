"""
Build snapshot-fixed baseline visit registrations from a fork World state.

Reads UXsim Vehicle, Node, and Link state at baseline timestep T (fork_W.T) and
registers planned visits on an OrderControlBaselineCollector after all candidates
pass validation. Institutional TVT logic stays outside this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector

_CURRENT_VISIT_REQUIRED_KEYS = (
    "visit_id",
    "node",
    "inlink",
    "arrival_time",
    "arrival_tiebreaker",
)


def register_snapshot_fixed_visits(
    fork_W,
    collector: OrderControlBaselineCollector,
    *,
    target_node_names,
) -> int:
    """
    Identify snapshot-fixed visits on TVT target nodes and register them on collector.

    Call this only after ``fork_W.exec_simulation()`` returns normally and before the
    next ``exec_simulation()`` call. At call time, ``fork_W.T`` is baseline timestep T
    and timestep T has not been processed yet.

    The collector should be a fresh instance with no prior snapshot registrations.
    Registration entries are validated on a temporary empty collector before the
    real collector is modified. If that validation fails, the real collector is
    left unchanged. Atomicity is not guaranteed for failures specific to the real
    collector itself (for example, a non-empty collector or a substituted collector
    implementation).

    Parameters
    ----------
    fork_W
        Fork World whose current state is the snapshot at timestep T.
    collector
        Empty OrderControlBaselineCollector for this fork baseline run.
    target_node_names
        Node names returned from ``set_order_control_for_nodes(..., time_value)``,
        passed once from the research driver without retyping the same set.

    Returns
    -------
    int
        Total number of snapshot-fixed visits registered.
    """
    target_nodes = _resolve_and_validate_target_nodes(fork_W, target_node_names)
    registration_plan = _build_snapshot_visit_registration_plan(
        fork_W, target_nodes
    )
    validation_collector = OrderControlBaselineCollector()
    for registration_entry in registration_plan:
        validation_collector.register_snapshot_visit(**registration_entry)
    for registration_entry in registration_plan:
        collector.register_snapshot_visit(**registration_entry)
    return len(registration_plan)


def _resolve_and_validate_target_nodes(fork_W, target_node_names) -> list[tuple[str, object]]:
    """
    Validate every TVT target node name before any Vehicle candidate is inspected.
    """
    if isinstance(target_node_names, (str, bytes)):
        raise ValueError(
            "target_node_names must be an iterable of node name strings, "
            f"not a single string; got {target_node_names!r}."
        )
    if not isinstance(target_node_names, Iterable):
        raise ValueError(
            "target_node_names must be an iterable of node name strings; "
            f"got {type(target_node_names).__name__}."
        )

    node_name_list = list(target_node_names)
    if len(node_name_list) == 0:
        raise ValueError("target_node_names must not be empty.")

    seen_node_names: set[str] = set()
    validated_nodes: list[tuple[str, object]] = []

    for node_name in node_name_list:
        if not isinstance(node_name, str) or node_name == "":
            raise ValueError(
                "Each target node name must be a non-empty str; "
                f"got {node_name!r}."
            )
        if node_name in seen_node_names:
            raise ValueError(
                f"Duplicate target node name {node_name!r} in target_node_names."
            )
        seen_node_names.add(node_name)

        try:
            target_node = fork_W.get_node(node_name)
        except Exception as exc:
            expected_missing_node_message = f"'{node_name}' is not Node in this World"
            if str(exc) == expected_missing_node_message:
                raise ValueError(
                    f"Target node {node_name!r} does not exist in fork World."
                ) from exc
            raise

        if not target_node.order_control_eligible:
            raise ValueError(
                f"Target node {node_name!r} is not order-control eligible "
                f"(order_control_eligible=False)."
            )

        order_control_type = target_node.order_control_type
        if order_control_type != "time_value":
            raise ValueError(
                f"Target node {node_name!r} has order_control_type="
                f"{order_control_type!r}; only 'time_value' nodes are supported."
            )

        validated_nodes.append((node_name, target_node))

    return validated_nodes


def _build_snapshot_visit_registration_plan(
    fork_W,
    target_nodes: Sequence[tuple[str, object]],
) -> list[dict]:
    """
    Build collector registration dicts for all arrived and not-yet-arrived visits.

    Does not modify the collector.
    """
    baseline_timestep_T = fork_W.T
    registration_plan: list[dict] = []
    # Arrived-vehicle names only: used to skip normal A reappearance on the same
    # node's inlink scan. Not-yet-arrived (B) vehicles are not added here.
    arrived_vehicle_names: set[str] = set()
    # All A and B registration-plan vehicles across every target node: used for
    # duplicate detection via _record_planned_vehicle_name().
    vehicle_name_to_planned_visit: dict[str, tuple[str, int, str]] = {}

    for target_node_name, target_node in target_nodes:
        for arrived_vehicle in target_node.incoming_vehicles:
            if _should_skip_non_fixed_set_vehicle(arrived_vehicle):
                continue

            registration_entry = _plan_arrived_vehicle_registration(
                fork_W=fork_W,
                target_node=target_node,
                target_node_name=target_node_name,
                arrived_vehicle=arrived_vehicle,
                baseline_timestep_T=baseline_timestep_T,
            )
            _record_planned_vehicle_name(
                vehicle_name=registration_entry["vehicle_name"],
                visit_id=registration_entry["visit_id"],
                target_node_name=target_node_name,
                inlink_name=registration_entry["inlink_name"],
                vehicle_name_to_planned_visit=vehicle_name_to_planned_visit,
            )
            arrived_vehicle_names.add(registration_entry["vehicle_name"])
            registration_plan.append(registration_entry)

        for inlink in _ordered_inlinks_for_node(target_node):
            for inlink_vehicle in inlink.vehicles:
                if inlink_vehicle.name in arrived_vehicle_names:
                    _handle_arrived_vehicle_name_seen_on_inlink(
                        inlink_vehicle=inlink_vehicle,
                        target_node_name=target_node_name,
                        inlink=inlink,
                        vehicle_name_to_planned_visit=vehicle_name_to_planned_visit,
                    )
                    continue

                if _should_skip_non_fixed_set_vehicle(inlink_vehicle):
                    continue

                registration_entry = _plan_not_yet_arrived_vehicle_registration(
                    fork_W=fork_W,
                    target_node=target_node,
                    target_node_name=target_node_name,
                    inlink=inlink,
                    not_yet_arrived_vehicle=inlink_vehicle,
                )
                _record_planned_vehicle_name(
                    vehicle_name=registration_entry["vehicle_name"],
                    visit_id=registration_entry["visit_id"],
                    target_node_name=target_node_name,
                    inlink_name=registration_entry["inlink_name"],
                    vehicle_name_to_planned_visit=vehicle_name_to_planned_visit,
                )
                registration_plan.append(registration_entry)

    return registration_plan


def _ordered_inlinks_for_node(target_node):
    """
    Return inlinks in Node.inlinks insertion order (link creation order).
    """
    return list(target_node.inlinks.values())


def _should_skip_non_fixed_set_vehicle(vehicle) -> bool:
    """
    Return True for research vehicles that are normally outside the snapshot set.
    """
    if vehicle.state in ("end", "abort"):
        return True
    if vehicle.flag_waiting_for_trip_end:
        return True
    if vehicle.mode == "taxi":
        return True
    if vehicle.specified_route is not None:
        return True
    return False


def _record_planned_vehicle_name(
    *,
    vehicle_name: str,
    visit_id: int,
    target_node_name: str,
    inlink_name: str,
    vehicle_name_to_planned_visit: dict[str, tuple[str, int, str]],
) -> None:
    """
    Record one vehicle in the all-candidate duplicate-detection map.

    Raises ValueError when the same vehicle_name is already planned for a
    different fixed visit across any target node.
    """
    if vehicle_name in vehicle_name_to_planned_visit:
        existing_node_name, existing_visit_id, existing_inlink_name = (
            vehicle_name_to_planned_visit[vehicle_name]
        )
        raise ValueError(
            f"Vehicle {vehicle_name!r} would receive multiple snapshot-fixed visits: "
            f"already planned for node {existing_node_name!r} with visit_id="
            f"{existing_visit_id} on inlink {existing_inlink_name!r}, newly found "
            f"for node {target_node_name!r} with visit_id={visit_id} on inlink "
            f"{inlink_name!r}."
        )

    vehicle_name_to_planned_visit[vehicle_name] = (
        target_node_name,
        visit_id,
        inlink_name,
    )


def _handle_arrived_vehicle_name_seen_on_inlink(
    *,
    inlink_vehicle,
    target_node_name: str,
    inlink,
    vehicle_name_to_planned_visit: dict[str, tuple[str, int, str]],
) -> None:
    """
    Confirm that an inlink vehicle name already in arrived_vehicle_names is only
    the normal arrived-vehicle reappearance on the same node, visit, and inlink.

    Inputs
    ------
    inlink_vehicle
        Vehicle found during inlink.vehicles scan.
    target_node_name
        Name of the target node currently being processed.
    inlink
        Inlink deque currently being scanned.
    vehicle_name_to_planned_visit
        Map of all vehicles already added to the registration plan.

    Normal skip condition
    -----------------------
    The vehicle was registered as arrived (A) on this same target node, with the
    same visit_id, on this same inlink. This is the expected dual-container state
    before node passage.

    Raises
    ------
    ValueError
        When the vehicle name was already planned but the current node, visit,
        or inlink does not match the earlier arrived registration.
    """
    vehicle_name = inlink_vehicle.name
    planned_node_name, planned_visit_id, planned_inlink_name = (
        vehicle_name_to_planned_visit[vehicle_name]
    )

    current_visit = inlink_vehicle.order_control_current_visit
    if current_visit is None:
        raise ValueError(
            f"Vehicle {vehicle_name!r} appears again on inlink {inlink.name!r} "
            f"at target node {target_node_name!r}, but "
            f"order_control_current_visit=None while already planned as arrived "
            f"for node {planned_node_name!r} with visit_id={planned_visit_id}."
        )

    current_visit_id = current_visit["visit_id"]
    current_inlink = current_visit["inlink"]
    current_inlink_name = current_inlink.name

    is_same_target_node = target_node_name == planned_node_name
    is_same_visit_id = current_visit_id == planned_visit_id
    is_same_inlink = (
        inlink.name == planned_inlink_name and current_inlink is inlink
    )

    if is_same_target_node and is_same_visit_id and is_same_inlink:
        return

    raise ValueError(
        f"Vehicle {vehicle_name!r} would receive multiple snapshot-fixed visits: "
        f"already planned for node {planned_node_name!r} with visit_id="
        f"{planned_visit_id} on inlink {planned_inlink_name!r}, newly found "
        f"for node {target_node_name!r} with visit_id={current_visit_id} while "
        f"scanning inlink {inlink.name!r} (current visit inlink "
        f"{current_inlink_name!r})."
    )


def _require_current_visit(
    vehicle,
    *,
    target_node_name: str,
    context: str,
):
    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise ValueError(
            f"{context}: vehicle {vehicle.name!r} at target node {target_node_name!r} "
            f"has order_control_current_visit=None."
        )
    return current_visit


def _require_current_visit_required_keys(
    current_visit,
    *,
    vehicle_name: str,
    target_node_name: str,
    context: str,
) -> None:
    for key in _CURRENT_VISIT_REQUIRED_KEYS:
        if key not in current_visit:
            raise ValueError(
                f"{context}: vehicle {vehicle_name!r} at target node "
                f"{target_node_name!r} is missing current visit key {key!r}."
            )


def _require_positive_visit_id(
    visit_id,
    *,
    vehicle_name: str,
    target_node_name: str,
    context: str,
) -> int:
    if isinstance(visit_id, bool) or not isinstance(visit_id, int) or visit_id < 1:
        raise ValueError(
            f"{context}: vehicle {vehicle_name!r} at target node "
            f"{target_node_name!r} has invalid visit_id={visit_id!r}."
        )
    return visit_id


def _validate_arrival_pair(
    arrival_time,
    arrival_tiebreaker,
    *,
    vehicle_name: str,
    target_node_name: str,
    context: str,
    require_both_none: bool,
    require_both_set: bool,
) -> None:
    arrival_time_is_set = arrival_time is not None
    arrival_tiebreaker_is_set = arrival_tiebreaker is not None

    if arrival_time_is_set != arrival_tiebreaker_is_set:
        raise ValueError(
            f"{context}: vehicle {vehicle_name!r} at target node "
            f"{target_node_name!r} has inconsistent arrival state: "
            f"arrival_time={arrival_time!r}, "
            f"arrival_tiebreaker={arrival_tiebreaker!r}."
        )

    if require_both_none and arrival_time_is_set:
        raise ValueError(
            f"{context}: vehicle {vehicle_name!r} at target node "
            f"{target_node_name!r} already has arrival information at snapshot "
            f"time, but was not registered as an arrived visit from "
            f"incoming_vehicles."
        )

    if require_both_set and not arrival_time_is_set:
        raise ValueError(
            f"{context}: vehicle {vehicle_name!r} at target node "
            f"{target_node_name!r} in incoming_vehicles does not have arrival "
            f"information at snapshot time."
        )


def _plan_arrived_vehicle_registration(
    *,
    fork_W,
    target_node,
    target_node_name: str,
    arrived_vehicle,
    baseline_timestep_T: int,
) -> dict:
    context = "Arrived snapshot visit candidate"
    if arrived_vehicle.state != "run":
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} at target node "
            f"{target_node_name!r} has state={arrived_vehicle.state!r}, "
            f"expected 'run'."
        )

    current_visit = _require_current_visit(
        arrived_vehicle,
        target_node_name=target_node_name,
        context=context,
    )
    _require_current_visit_required_keys(
        current_visit,
        vehicle_name=arrived_vehicle.name,
        target_node_name=target_node_name,
        context=context,
    )
    visit_id = _require_positive_visit_id(
        current_visit["visit_id"],
        vehicle_name=arrived_vehicle.name,
        target_node_name=target_node_name,
        context=context,
    )
    if visit_id != arrived_vehicle.order_control_visit_id:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} at target node "
            f"{target_node_name!r} has current visit visit_id={visit_id}, but "
            f"vehicle order_control_visit_id="
            f"{arrived_vehicle.order_control_visit_id}."
        )

    current_visit_node = current_visit["node"]
    if current_visit_node is not target_node:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} current visit node "
            f"{current_visit_node.name!r} does not match target node "
            f"{target_node_name!r}."
        )

    current_visit_inlink = current_visit["inlink"]
    if current_visit_inlink.name not in target_node.inlinks:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} current visit inlink "
            f"{current_visit_inlink.name!r} is not an inlink of target node "
            f"{target_node_name!r}."
        )

    if arrived_vehicle.link is not current_visit_inlink:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} link "
            f"{None if arrived_vehicle.link is None else arrived_vehicle.link.name!r} "
            f"does not match current visit inlink {current_visit_inlink.name!r}."
        )

    if arrived_vehicle not in current_visit_inlink.vehicles:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} is in "
            f"incoming_vehicles of target node {target_node_name!r} but not in "
            f"inlink {current_visit_inlink.name!r}.vehicles."
        )

    arrival_time = current_visit["arrival_time"]
    arrival_tiebreaker = current_visit["arrival_tiebreaker"]
    _validate_arrival_pair(
        arrival_time,
        arrival_tiebreaker,
        vehicle_name=arrived_vehicle.name,
        target_node_name=target_node_name,
        context=context,
        require_both_none=False,
        require_both_set=True,
    )

    route_next_link = arrived_vehicle.route_next_link
    if route_next_link is None:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} at target node "
            f"{target_node_name!r} has route_next_link=None."
        )
    if route_next_link.start_node is not target_node:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} route_next_link "
            f"{route_next_link.name!r} does not start at target node "
            f"{target_node_name!r}."
        )

    baseline_arrival_timestep = int(round(arrival_time / fork_W.DELTAT))
    if baseline_arrival_timestep >= baseline_timestep_T:
        raise ValueError(
            f"{context}: vehicle {arrived_vehicle.name!r} at target node "
            f"{target_node_name!r} has baseline_arrival_timestep="
            f"{baseline_arrival_timestep}, but snapshot baseline timestep T is "
            f"{baseline_timestep_T}; arrived visits must have arrived before T."
        )

    return {
        "vehicle_name": arrived_vehicle.name,
        "vehicle_id": arrived_vehicle.id,
        "node_name": target_node_name,
        "inlink_name": current_visit_inlink.name,
        "visit_id": visit_id,
        "was_arrived_at_snapshot": True,
        "baseline_arrival_timestep": baseline_arrival_timestep,
        "arrival_tiebreaker": arrival_tiebreaker,
        "route_next_link_name": route_next_link.name,
        "baseline_passage_timestep": None,
    }


def _plan_not_yet_arrived_vehicle_registration(
    *,
    fork_W,
    target_node,
    target_node_name: str,
    inlink,
    not_yet_arrived_vehicle,
) -> dict:
    context = "Not-yet-arrived snapshot visit candidate"
    if not_yet_arrived_vehicle.state != "run":
        raise ValueError(
            f"{context}: vehicle {not_yet_arrived_vehicle.name!r} on inlink "
            f"{inlink.name!r} at target node {target_node_name!r} has "
            f"state={not_yet_arrived_vehicle.state!r}, expected 'run'."
        )

    if not_yet_arrived_vehicle.link is not inlink:
        raise ValueError(
            f"{context}: vehicle {not_yet_arrived_vehicle.name!r} link "
            f"{None if not_yet_arrived_vehicle.link is None else not_yet_arrived_vehicle.link.name!r} "
            f"does not match scanned inlink {inlink.name!r}."
        )

    current_visit = _require_current_visit(
        not_yet_arrived_vehicle,
        target_node_name=target_node_name,
        context=context,
    )
    _require_current_visit_required_keys(
        current_visit,
        vehicle_name=not_yet_arrived_vehicle.name,
        target_node_name=target_node_name,
        context=context,
    )
    visit_id = _require_positive_visit_id(
        current_visit["visit_id"],
        vehicle_name=not_yet_arrived_vehicle.name,
        target_node_name=target_node_name,
        context=context,
    )
    if visit_id != not_yet_arrived_vehicle.order_control_visit_id:
        raise ValueError(
            f"{context}: vehicle {not_yet_arrived_vehicle.name!r} at target node "
            f"{target_node_name!r} has current visit visit_id={visit_id}, but "
            f"vehicle order_control_visit_id="
            f"{not_yet_arrived_vehicle.order_control_visit_id}."
        )

    current_visit_node = current_visit["node"]
    if current_visit_node is not target_node:
        raise ValueError(
            f"{context}: vehicle {not_yet_arrived_vehicle.name!r} current visit "
            f"node {current_visit_node.name!r} does not match target node "
            f"{target_node_name!r}."
        )

    current_visit_inlink = current_visit["inlink"]
    if current_visit_inlink is not inlink:
        raise ValueError(
            f"{context}: vehicle {not_yet_arrived_vehicle.name!r} current visit "
            f"inlink {current_visit_inlink.name!r} does not match scanned inlink "
            f"{inlink.name!r}."
        )

    arrival_time = current_visit["arrival_time"]
    arrival_tiebreaker = current_visit["arrival_tiebreaker"]
    _validate_arrival_pair(
        arrival_time,
        arrival_tiebreaker,
        vehicle_name=not_yet_arrived_vehicle.name,
        target_node_name=target_node_name,
        context=context,
        require_both_none=True,
        require_both_set=False,
    )

    if not_yet_arrived_vehicle in target_node.incoming_vehicles:
        raise ValueError(
            f"{context}: vehicle {not_yet_arrived_vehicle.name!r} on inlink "
            f"{inlink.name!r} is also listed in incoming_vehicles of target node "
            f"{target_node_name!r}, but has no arrival information."
        )

    return {
        "vehicle_name": not_yet_arrived_vehicle.name,
        "vehicle_id": not_yet_arrived_vehicle.id,
        "node_name": target_node_name,
        "inlink_name": inlink.name,
        "visit_id": visit_id,
        "was_arrived_at_snapshot": False,
        "baseline_arrival_timestep": None,
        "arrival_tiebreaker": None,
        "route_next_link_name": None,
        "baseline_passage_timestep": None,
    }
