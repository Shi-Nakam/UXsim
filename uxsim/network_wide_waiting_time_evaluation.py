"""
Network-wide ACWT and ACWWT for a finished UXsim World.

The same entry point serves signalized UXsim, FCFS, BATCH, and TVT-MP.
method_name is an audit label. It does not change CW_z, ACWT, or ACWWT.

This module does not export itself from uxsim/__init__.py.
It does not write files, and it does not keep a process-wide cache.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from uxsim.analyzer import Analyzer
from uxsim.uxsim import Link, Node, Vehicle, World

# Audit labels. The calculation below does not branch on these strings.
OFFICIAL_METHOD_NAMES = (
    "signalized_uxsim",
    "fcfs",
    "batch",
    "tvt_mp",
)

# Seconds agreement for values that UXsim already stored as timestep * DELTAT.
# Not used when deciding whether a timestep waiting count is negative.
_SECONDS_MATCH_ABS_TOL = 1e-6

_NON_BINDING_CAPACITY = 1000000.0
_REFERENCE_JAM_DENSITY = 0.2
_REFERENCE_FINISH_MARGIN_S = 60.0

PhysicalRouteKey = tuple[float, tuple[tuple[float, float], ...]]
RouteAuditIdentity = tuple[str, ...]


@dataclass(frozen=True)
class ReferenceReplayResult:
    """Numeric outcome of one reference replay.

    minimum_trip_time_s is reference_minimum_trip_timesteps * DELTAT.
    analytical_free_flow_time_s is sum(length/u) for audit only.
    It is not T_min,z.
    """

    physical_route_key: PhysicalRouteKey
    reference_departure_timestep: int
    reference_arrival_timestep: int
    reference_minimum_trip_timesteps: int
    minimum_trip_time_s: float
    analytical_free_flow_time_s: float
    reference_route_link_count: int
    reference_world_deltat: float
    reference_world_deltan: int
    validation_passed: bool


@dataclass(frozen=True)
class VehicleWaitingTimeRecord:
    """One finished vehicle. Times in *_s fields are seconds.

    cumulative_waiting_time_timesteps is the canonical CW_z.
    cumulative_waiting_time_s is that integer times DELTAT.
    true_vot_per_second is a per-second coefficient. It is not divided by 3600.
    """

    vehicle_name: str
    method_name: str
    physical_route_key: PhysicalRouteKey
    route_audit_identity: RouteAuditIdentity
    actual_departure_timestep: int
    actual_arrival_timestep: int
    actual_trip_timesteps: int
    reference_departure_timestep: int
    reference_arrival_timestep: int
    reference_minimum_trip_timesteps: int
    cumulative_waiting_time_timesteps: int
    actual_travel_time_s: float
    minimum_trip_time_s: float
    cumulative_waiting_time_s: float
    true_vot_per_second: float
    weighted_cumulative_waiting_time: float
    evaluation_cohort: str
    method_specific_participation_status: str | None


@dataclass(frozen=True)
class EvaluationCounters:
    evaluated_vehicle_count: int
    unique_physical_route_count: int
    reference_replay_run_count: int
    reference_reuse_count: int
    unique_audit_identity_count: int
    duplicate_audit_identity_observation_count: int
    incomplete_vehicle_count: int
    validation_failure_count: int
    negative_cumulative_waiting_time_count: int


@dataclass(frozen=True)
class CohortWaitingTimeSummary:
    """Totals for one evaluation_cohort, in first-seen vehicle order."""

    evaluation_cohort: str
    vehicle_count: int
    total_cumulative_waiting_time_s: float
    average_cumulative_waiting_time_s: float
    total_weighted_cumulative_waiting_time: float
    average_weighted_cumulative_waiting_time: float


@dataclass(frozen=True)
class NetworkWideWaitingTimeSummary:
    method_name: str
    vehicle_count: int
    total_cumulative_waiting_time_s: float
    average_cumulative_waiting_time_s: float
    total_weighted_cumulative_waiting_time: float
    average_weighted_cumulative_waiting_time: float
    cohort_summaries: tuple[CohortWaitingTimeSummary, ...]
    counters: EvaluationCounters


@dataclass(frozen=True)
class NetworkWideWaitingTimeEvaluationResult:
    vehicle_records: tuple[VehicleWaitingTimeRecord, ...]
    summary: NetworkWideWaitingTimeSummary
    reference_results_by_physical_key: Mapping[PhysicalRouteKey, ReferenceReplayResult]
    audit_identities_by_physical_key: Mapping[PhysicalRouteKey, tuple[RouteAuditIdentity, ...]]
    counters: EvaluationCounters
    vehicle_plan_digest: str | None
    comparison_metadata: Mapping | None


@dataclass
class _EvaluationContext:
    """State for a single call of evaluate_network_wide_waiting_time.

    Created inside that call. Not stored on the World and not reused.
    """

    real_deltat: float
    method_name: str
    reference_results_by_physical_key: dict = field(default_factory=dict)
    audit_identities_by_physical_key: dict = field(default_factory=dict)
    vehicle_records: list = field(default_factory=list)
    evaluated_vehicle_count: int = 0
    unique_physical_route_count: int = 0
    reference_replay_run_count: int = 0
    reference_reuse_count: int = 0
    unique_audit_identity_count: int = 0
    duplicate_audit_identity_observation_count: int = 0
    incomplete_vehicle_count: int = 0
    validation_failure_count: int = 0
    negative_cumulative_waiting_time_count: int = 0


def evaluate_network_wide_waiting_time(
    real_world: World,
    method_name: str,
    evaluated_vehicle_names: Sequence[str],
    true_vot_per_second_by_vehicle_name: Mapping[str, object],
    evaluation_cohort_by_vehicle_name: Mapping[str, object],
    method_specific_participation_status_by_vehicle_name: Mapping[str, object] | None = None,
    vehicle_plan_digest: str | None = None,
    comparison_metadata: Mapping | None = None,
) -> NetworkWideWaitingTimeEvaluationResult:
    """Evaluate network-wide waiting time on a finished real World.

    The real World is not modified and its simulation is not run again.
    Each call builds a new local context. There is no global cache and the
    context is not stored on the World.

    method_name is kept for audit. It does not change the formulas.
    Vehicles are processed in the order of evaluated_vehicle_names.
    Cohort summaries use that same first-seen order.
    Reference replays are shared only inside this call, by physical route key.
    One physical key stores one validated result. A failed replay is not stored.
    The returned object does not contain a World, Vehicle, Node, Link, or Analyzer.

    CW_z is an integer timestep difference. Seconds are that integer times DELTAT.
    true_vot_per_second multiplies those seconds directly. There is no /3600.

    Order: validate the world, DELTAN, method, names, true VOT, and cohort;
    copy optional audit data; create a new context; evaluate each vehicle;
    check counters, build the summaries, then reject a result that holds a
    simulation object.
    """

    _validate_real_world(real_world)
    _validate_method_name(method_name)
    ordered_names = _validate_evaluated_vehicle_names(evaluated_vehicle_names)
    vot_by_name = _validate_true_vot_ledger(
        ordered_names,
        true_vot_per_second_by_vehicle_name,
    )
    cohort_by_name = _validate_cohort_ledger(
        ordered_names,
        evaluation_cohort_by_vehicle_name,
    )
    status_by_name = _validate_optional_status_ledger(
        ordered_names,
        method_specific_participation_status_by_vehicle_name,
    )
    digest = _validate_vehicle_plan_digest(vehicle_plan_digest)
    metadata = _copy_comparison_metadata(comparison_metadata)

    context = _EvaluationContext(
        real_deltat=real_world.DELTAT,
        method_name=method_name,
    )
    for vehicle_name in ordered_names:
        _evaluate_one_vehicle(
            context,
            real_world,
            vehicle_name,
            vot_by_name[vehicle_name],
            cohort_by_name[vehicle_name],
            status_by_name,
        )

    counters = _counters_from_context(context)
    _require_counter_consistency(context, counters)
    summary = _build_summary(context, counters)
    result = _build_public_result(
        context,
        summary,
        counters,
        digest,
        metadata,
    )
    _require_result_contains_no_simulation_object(result)
    return result


def _validate_real_world(real_world: World) -> None:
    if not isinstance(real_world, World):
        raise ValueError(
            "real_world must be a UXsim World. "
            f"got type {type(real_world).__name__}."
        )
    deltan = real_world.DELTAN
    if type(deltan) is not int or deltan != 1:
        raise ValueError(
            "real World DELTAN must be the Python int 1. "
            f"got {deltan!r} type={type(deltan).__name__}."
        )
    deltat = real_world.DELTAT
    if isinstance(deltat, bool) or not isinstance(deltat, (int, float)):
        raise ValueError(
            "real World DELTAT must be a non-bool number. "
            f"got {deltat!r}."
        )
    if not math.isfinite(float(deltat)) or float(deltat) <= 0.0:
        raise ValueError(
            "real World DELTAT must be finite and positive. "
            f"got {deltat!r}."
        )


def _validate_method_name(method_name: str) -> None:
    if not isinstance(method_name, str) or method_name == "":
        raise ValueError(
            "method_name must be a non-empty string. "
            f"got {method_name!r}."
        )
    if method_name not in OFFICIAL_METHOD_NAMES:
        raise ValueError(
            "method_name must be one of "
            f"{OFFICIAL_METHOD_NAMES}. got {method_name!r}."
        )


def _validate_evaluated_vehicle_names(evaluated_vehicle_names: Sequence[str]) -> tuple[str, ...]:
    if isinstance(evaluated_vehicle_names, str) or not isinstance(
        evaluated_vehicle_names,
        Sequence,
    ):
        raise ValueError(
            "evaluated_vehicle_names must be a sequence of vehicle name strings."
        )
    if len(evaluated_vehicle_names) == 0:
        raise ValueError("evaluated_vehicle_names is empty.")

    ordered_names = []
    seen_names = []
    for vehicle_name in evaluated_vehicle_names:
        if not isinstance(vehicle_name, str) or vehicle_name == "":
            raise ValueError(
                "evaluated_vehicle_names contains a name that is not a "
                f"non-empty string: {vehicle_name!r}."
            )
        if vehicle_name in seen_names:
            raise ValueError(
                "evaluated_vehicle_names contains a duplicate name: "
                f"{vehicle_name!r}."
            )
        seen_names.append(vehicle_name)
        ordered_names.append(vehicle_name)
    return tuple(ordered_names)


def _validate_true_vot_ledger(
    ordered_names: Sequence[str],
    true_vot_per_second_by_vehicle_name: Mapping[str, object],
) -> dict[str, float]:
    if not isinstance(true_vot_per_second_by_vehicle_name, Mapping):
        raise ValueError(
            "true_vot_per_second_by_vehicle_name must be a mapping."
        )
    vot_by_name = {}
    for vehicle_name in ordered_names:
        if vehicle_name not in true_vot_per_second_by_vehicle_name:
            raise ValueError(
                "true_vot_per_second is missing for vehicle "
                f"{vehicle_name!r}."
            )
        raw_value = true_vot_per_second_by_vehicle_name[vehicle_name]
        vot_by_name[vehicle_name] = _require_true_vot_per_second(
            raw_value,
            vehicle_name,
        )
    return vot_by_name


def _require_true_vot_per_second(raw_value: object, vehicle_name: str) -> float:
    if raw_value is None:
        raise ValueError(
            f"true_vot_per_second for vehicle {vehicle_name!r} is None."
        )
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise ValueError(
            f"true_vot_per_second for vehicle {vehicle_name!r} must be a "
            f"non-bool int or float. got {raw_value!r}."
        )
    if not math.isfinite(float(raw_value)):
        raise ValueError(
            f"true_vot_per_second for vehicle {vehicle_name!r} must be finite. "
            f"got {raw_value!r}."
        )
    if float(raw_value) < 0.0:
        raise ValueError(
            f"true_vot_per_second for vehicle {vehicle_name!r} must be "
            f">= 0. got {raw_value!r}."
        )
    return float(raw_value)


def _validate_cohort_ledger(
    ordered_names: Sequence[str],
    evaluation_cohort_by_vehicle_name: Mapping[str, object],
) -> dict[str, str]:
    if not isinstance(evaluation_cohort_by_vehicle_name, Mapping):
        raise ValueError(
            "evaluation_cohort_by_vehicle_name must be a mapping."
        )
    cohort_by_name = {}
    for vehicle_name in ordered_names:
        if vehicle_name not in evaluation_cohort_by_vehicle_name:
            raise ValueError(
                "evaluation_cohort is missing for vehicle "
                f"{vehicle_name!r}."
            )
        raw_cohort = evaluation_cohort_by_vehicle_name[vehicle_name]
        if not isinstance(raw_cohort, str) or raw_cohort == "":
            raise ValueError(
                "evaluation_cohort for vehicle "
                f"{vehicle_name!r} must be a non-empty string. "
                f"got {raw_cohort!r}."
            )
        cohort_by_name[vehicle_name] = raw_cohort
    return cohort_by_name


def _validate_optional_status_ledger(
    ordered_names: Sequence[str],
    status_by_vehicle_name: Mapping[str, object] | None,
) -> dict[str, str] | None:
    if status_by_vehicle_name is None:
        return None
    if not isinstance(status_by_vehicle_name, Mapping):
        raise ValueError(
            "method_specific_participation_status_by_vehicle_name must be "
            "a mapping when it is provided."
        )
    status_by_name = {}
    for vehicle_name in ordered_names:
        if vehicle_name not in status_by_vehicle_name:
            raise ValueError(
                "method_specific_participation_status is missing for vehicle "
                f"{vehicle_name!r}."
            )
        raw_status = status_by_vehicle_name[vehicle_name]
        if not isinstance(raw_status, str) or raw_status == "":
            raise ValueError(
                "method_specific_participation_status for vehicle "
                f"{vehicle_name!r} must be a non-empty string. "
                f"got {raw_status!r}."
            )
        status_by_name[vehicle_name] = raw_status
    return status_by_name


def _validate_vehicle_plan_digest(vehicle_plan_digest: str | None) -> str | None:
    if vehicle_plan_digest is None:
        return None
    if not isinstance(vehicle_plan_digest, str):
        raise ValueError(
            "vehicle_plan_digest must be a string or None. "
            f"got {vehicle_plan_digest!r}."
        )
    return vehicle_plan_digest


def _copy_comparison_metadata(comparison_metadata: Mapping | None) -> dict | None:
    if comparison_metadata is None:
        return None
    if not isinstance(comparison_metadata, Mapping):
        raise ValueError("comparison_metadata must be a mapping or None.")
    copied = {}
    for key in comparison_metadata:
        if not isinstance(key, str) or key == "":
            raise ValueError(
                "comparison_metadata keys must be non-empty strings. "
                f"got {key!r}."
            )
        copied[key] = comparison_metadata[key]
    return copied


def _evaluate_one_vehicle(
    context: _EvaluationContext,
    real_world: World,
    vehicle_name: str,
    true_vot_per_second: float,
    evaluation_cohort: str,
    status_by_name: dict[str, str] | None,
) -> None:
    vehicle = _require_finished_vehicle(real_world, vehicle_name)
    if float(vehicle.W.DELTAT) != float(context.real_deltat):
        raise ValueError(
            "vehicle World DELTAT does not match the evaluation DELTAT. "
            f"vehicle={vehicle_name!r} method_name={context.method_name!r} "
            f"vehicle_DELTAT={vehicle.W.DELTAT!r} "
            f"evaluation_DELTAT={context.real_deltat!r}."
        )
    route_links = _actual_route_links(vehicle)
    physical_key = _build_physical_route_key(context.real_deltat, route_links)
    audit_identity = _build_route_audit_identity(route_links)
    _register_audit_identity(context, physical_key, audit_identity)
    reference_result = _get_or_run_reference_replay(
        context,
        route_links,
        physical_key,
    )
    record = _build_vehicle_record(
        context,
        vehicle,
        physical_key,
        audit_identity,
        reference_result,
        true_vot_per_second,
        evaluation_cohort,
        status_by_name,
    )
    context.vehicle_records.append(record)
    context.evaluated_vehicle_count += 1


def _require_finished_vehicle(real_world: World, vehicle_name: str) -> Vehicle:
    if vehicle_name not in real_world.VEHICLES:
        raise ValueError(
            f"evaluated vehicle {vehicle_name!r} is not in the real World."
        )
    vehicle = real_world.VEHICLES[vehicle_name]
    if not isinstance(vehicle, Vehicle):
        raise ValueError(
            f"real World entry {vehicle_name!r} is not a Vehicle. "
            f"got type {type(vehicle).__name__}."
        )
    if vehicle.state != "end":
        raise ValueError(
            f"vehicle {vehicle_name!r} is not finished. "
            f"state={vehicle.state!r}."
        )
    return vehicle


def _actual_route_links(vehicle: Vehicle) -> list:
    route, _timestamps = vehicle.traveled_route(
        include_arrival_time=False,
        include_departure_time=False,
    )
    route_links = list(route.links)
    if len(route_links) == 0:
        raise ValueError(
            f"actual route is empty. vehicle={vehicle.name!r}."
        )
    for index, link in enumerate(route_links):
        if link is None:
            raise ValueError(
                f"actual route contains an empty link. "
                f"vehicle={vehicle.name!r} index={index}."
            )
        _require_positive_finite_number(
            link.length,
            "link length",
            vehicle.name,
            index,
            getattr(link, "name", None),
        )
        _require_positive_finite_number(
            link.u,
            "link u",
            vehicle.name,
            index,
            getattr(link, "name", None),
        )
    return route_links


def _require_positive_finite_number(
    raw_value: object,
    label: str,
    vehicle_name: str,
    index: int,
    link_name: object,
) -> float:
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise ValueError(
            f"{label} is not a non-bool number. "
            f"vehicle={vehicle_name!r} index={index} link={link_name!r} "
            f"value={raw_value!r}."
        )
    if not math.isfinite(float(raw_value)) or float(raw_value) <= 0.0:
        raise ValueError(
            f"{label} must be finite and > 0. "
            f"vehicle={vehicle_name!r} index={index} link={link_name!r} "
            f"value={raw_value!r}."
        )
    return float(raw_value)


def _build_physical_route_key(deltat: float, route_links: Sequence) -> PhysicalRouteKey:
    """(DELTAT, ((length, link.u), ...)). Order is kept. Values are not rounded."""

    pairs = []
    for link in route_links:
        length = float(link.length)
        speed_u = float(link.u)
        pairs.append((length, speed_u))
    return (float(deltat), tuple(pairs))


def _build_route_audit_identity(route_links: Sequence) -> RouteAuditIdentity:
    names = []
    for link in route_links:
        names.append(str(link.name))
    return tuple(names)


def _register_audit_identity(
    context: _EvaluationContext,
    physical_key: PhysicalRouteKey,
    audit_identity: RouteAuditIdentity,
) -> None:
    identities = context.audit_identities_by_physical_key.get(physical_key)
    if identities is None:
        identities = []
        context.audit_identities_by_physical_key[physical_key] = identities
    if audit_identity in identities:
        context.duplicate_audit_identity_observation_count += 1
        return
    identities.append(audit_identity)
    context.unique_audit_identity_count += 1


def _get_or_run_reference_replay(
    context: _EvaluationContext,
    route_links: Sequence,
    physical_key: PhysicalRouteKey,
) -> ReferenceReplayResult:
    stored = context.reference_results_by_physical_key.get(physical_key)
    if stored is None:
        result = _run_reference_replay(
            route_links,
            context.real_deltat,
            physical_key,
            context.method_name,
        )
        if not result.validation_passed:
            context.validation_failure_count += 1
            raise RuntimeError(
                "reference replay did not pass validation and was not stored. "
                f"method_name={context.method_name!r}."
            )
        context.reference_results_by_physical_key[physical_key] = result
        context.reference_replay_run_count += 1
        context.unique_physical_route_count += 1
        return result

    if not stored.validation_passed:
        context.validation_failure_count += 1
        raise RuntimeError(
            "stored reference result is not validated. "
            f"method_name={context.method_name!r}."
        )
    if stored.physical_route_key != physical_key:
        raise RuntimeError(
            "stored reference result is filed under a different physical key. "
            f"method_name={context.method_name!r}."
        )
    context.reference_reuse_count += 1
    return stored


def _analytical_free_flow_time_s(route_links: Sequence) -> float:
    total = 0.0
    for link in route_links:
        total += float(link.length) / float(link.u)
    return total


def _reference_tmax_seconds(route_links: Sequence, real_deltat: float) -> float:
    """Finish budget for the reference run. This expression is not T_min,z."""

    link_count = len(route_links)
    return (
        _analytical_free_flow_time_s(route_links)
        + (link_count + 2) * float(real_deltat)
        + _REFERENCE_FINISH_MARGIN_S
    )


def _build_reference_world(
    route_links: Sequence,
    real_deltat: float,
) -> World:
    """One serial no-wait World. Physical inputs are order, length, u, and DELTAT."""

    if len(route_links) == 0:
        raise ValueError("cannot build a reference world from an empty route.")
    tmax_seconds = _reference_tmax_seconds(route_links, real_deltat)
    world = World(
        name="network_wide_waiting_time_reference",
        deltan=1,
        reaction_time=real_deltat,
        tmax=tmax_seconds,
        random_seed=0,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        hard_deterministic_mode=True,
        vehicle_logging_timestep_interval=1,
    )
    if type(world.DELTAN) is not int or world.DELTAN != 1:
        raise RuntimeError(
            "reference World DELTAN is not the Python int 1. "
            f"got {world.DELTAN!r}."
        )
    if world.DELTAT != real_deltat:
        raise RuntimeError(
            "reference World DELTAT does not match the real World. "
            f"reference={world.DELTAT!r} real={real_deltat!r}."
        )

    link_count = len(route_links)
    node_index = 0
    while node_index < link_count + 1:
        world.addNode(
            f"reference_node_{node_index}",
            float(node_index),
            0.0,
            signal=[0],
        )
        node_index += 1

    reference_link_names = []
    link_index = 0
    for link in route_links:
        reference_link_name = f"reference_link_{link_index}"
        world.addLink(
            reference_link_name,
            f"reference_node_{link_index}",
            f"reference_node_{link_index + 1}",
            length=float(link.length),
            free_flow_speed=float(link.u),
            number_of_lanes=1,
            jam_density=_REFERENCE_JAM_DENSITY,
            jam_density_per_lane=None,
            merge_priority=1.0,
            signal_group=[0],
            capacity_in=_NON_BINDING_CAPACITY,
            capacity_out=_NON_BINDING_CAPACITY,
        )
        reference_link_names.append(reference_link_name)
        link_index += 1

    vehicle = world.addVehicle(
        "reference_node_0",
        f"reference_node_{link_count}",
        0,
        name="reference_vehicle",
        departure_time_is_time_step=1,
        mode="single_trip",
    )
    vehicle.enforce_route(reference_link_names)
    _require_reference_structure(world, real_deltat)
    return world


def _require_reference_structure(world: World, real_deltat: float) -> None:
    if world.user_function is not None:
        raise RuntimeError("reference World user_function must be None.")
    if len(world.VEHICLES) != 1:
        raise RuntimeError(
            "reference World must contain one vehicle. "
            f"count={len(world.VEHICLES)}."
        )
    if world.DELTAT != real_deltat:
        raise RuntimeError(
            "reference World DELTAT changed while the world was built. "
            f"reference={world.DELTAT!r} real={real_deltat!r}."
        )
    for node in world.NODES:
        if node.flow_capacity is not None:
            raise RuntimeError(
                f"reference node {node.name!r} has a flow capacity."
            )
        if node.order_control_type != "none" or node.order_control_eligible:
            raise RuntimeError(
                f"reference node {node.name!r} has order control."
            )
        if node.user_function is not None:
            raise RuntimeError(
                f"reference node {node.name!r} has a user function."
            )
    for link in world.LINKS:
        if link.user_function is not None:
            raise RuntimeError(
                f"reference link {link.name!r} has a user function."
            )


def _record_travel_log_without_analyzer(vehicle: Vehicle, enforce_log: int = 0) -> None:
    """Keep traveled_route logs without writing World.analyzer.

    Vehicle.record_log writes running and waiting samples to the Analyzer.
    A reference World finalized with create_analyzer=False has no Analyzer,
    so this writer is attached to the single reference vehicle.
    """

    interval = vehicle.W.vehicle_logging_timestep_interval
    if interval != -1:
        should_sample = (
            interval == 1
            or vehicle.W.T % interval == 0
            or enforce_log
        )
        if should_sample:
            if vehicle.state != "run":
                vehicle.log_t.append(vehicle.W.T * vehicle.W.DELTAT)
                vehicle.log_state.append(vehicle.state)
                vehicle.log_link.append(-1)
                vehicle.log_x.append(-1)
                vehicle.log_s.append(-1)
                vehicle.log_v.append(-1)
                vehicle.log_lane.append(-1)
            else:
                vehicle.log_t.append(vehicle.W.T * vehicle.W.DELTAT)
                vehicle.log_state.append(vehicle.state)
                vehicle.log_link.append(vehicle.link)
                vehicle.log_x.append(vehicle.x)
                vehicle.log_v.append(vehicle.v)
                vehicle.log_lane.append(vehicle.lane)
                if vehicle.leader is not None and vehicle.link == vehicle.leader.link:
                    vehicle.log_s.append(vehicle.leader.x - vehicle.x)
                else:
                    vehicle.log_s.append(-1)

    if vehicle.link != vehicle.link_old:
        if vehicle.state == "run":
            vehicle.log_t_link.append(
                [vehicle.W.T * vehicle.W.DELTAT, vehicle.link]
            )
        elif vehicle.state == "end":
            vehicle.log_t_link.append(
                [vehicle.W.T * vehicle.W.DELTAT, "end"]
            )
        vehicle.link_old = vehicle.link


def _attach_reference_log(vehicle: Vehicle) -> None:
    def record_for_reference_vehicle(enforce_log: int = 0) -> None:
        _record_travel_log_without_analyzer(vehicle, enforce_log)

    vehicle.record_log = record_for_reference_vehicle


def _run_reference_replay_steps(world: World) -> Vehicle:
    """Limited runner for one serial reference vehicle.

    World.finalize_scenario(create_analyzer=False) does not create W.analyzer.
    World.exec_simulation expects that Analyzer: it shows progress through it,
    Vehicle.record_log writes average speed into it, and simulation_terminated
    calls Analyzer.basic_analysis. This runner therefore does not call
    exec_simulation.

    The step order follows the current exec_simulation body for a world that
    has no TVT evaluation end and no downstream-boundary observer:
    Link.update, Node.generate, Node.update, Node.transfer, Vehicle.carfollow,
    living Vehicle.update, route search and preference update, then World.TIME.
    Analyzer calls and simulation_terminated are omitted.

    The Level 2 mimic loop is a narrower node-service estimator. It is not
    this trip runner. This function is not a general simulation entry point,
    and it does not follow later edits to exec_simulation automatically.
    """

    if world.finalized == 0:
        world.finalize_scenario(create_analyzer=False)
    if hasattr(world, "analyzer") or isinstance(getattr(world, "analyzer", None), Analyzer):
        raise RuntimeError(
            "reference runner found an Analyzer. "
            "create_analyzer=False is required."
        )
    if world.user_function is not None:
        raise RuntimeError(
            "reference runner accepts only a world whose user_function is None."
        )
    if len(world.VEHICLES) != 1:
        raise RuntimeError(
            "reference runner accepts only one vehicle. "
            f"count={len(world.VEHICLES)}."
        )
    vehicle = next(iter(world.VEHICLES.values()))
    _attach_reference_log(vehicle)

    # range(0, TSIZE) is T = 0 .. TSIZE-1, matching exec_simulation's break
    # when T == TSIZE-1. The loop stops earlier once the one vehicle has ended.
    for world.T in range(0, world.TSIZE):
        for link in world.LINKS:
            link.update()
        for node in world.NODES:
            node.generate()
            node.update()
        for node in world.NODES:
            node.transfer()
        for running_vehicle in world.VEHICLES_RUNNING.values():
            running_vehicle.carfollow()
        living_names = list(world.VEHICLES_LIVING.keys())
        for living_name in living_names:
            world.VEHICLES_LIVING[living_name].update()
        if world.route_choice_update_gradual is True:
            if world.T % world.DELTAT_ROUTE == 0:
                world.ROUTECHOICE.route_search_all(noise=world.DUO_NOISE)
            world.ROUTECHOICE.homogeneous_DUO_update()
        else:
            if world.T % world.DELTAT_ROUTE == 0:
                world.ROUTECHOICE.route_search_all(noise=world.DUO_NOISE)
                world.ROUTECHOICE.homogeneous_DUO_update()
                for living_vehicle in world.VEHICLES_LIVING.values():
                    living_vehicle.route_pref_update(weight=world.DUO_UPDATE_WEIGHT)
        world.TIME = world.T * world.DELTAT
        if vehicle.state == "end":
            break
    if vehicle.state != "end":
        raise RuntimeError(
            "reference vehicle did not finish within the finish budget. "
            f"vehicle={vehicle.name!r} state={vehicle.state!r} "
            f"T={world.T} TSIZE={world.TSIZE}."
        )
    return vehicle


def _require_python_timestep(
    raw_value: object,
    label: str,
    vehicle_name: str,
    method_name: str,
) -> int:
    if type(raw_value) is not int:
        raise ValueError(
            f"{label} must be a Python int, not bool. "
            f"vehicle={vehicle_name!r} method_name={method_name!r} "
            f"value={raw_value!r}."
        )
    if raw_value < 0:
        raise ValueError(
            f"{label} must be >= 0. "
            f"vehicle={vehicle_name!r} method_name={method_name!r} "
            f"value={raw_value!r}."
        )
    return raw_value


def _seconds_match(left: float, right: float) -> bool:
    if left == right:
        return True
    return math.isclose(
        left,
        right,
        rel_tol=0.0,
        abs_tol=_SECONDS_MATCH_ABS_TOL,
    )


def _run_reference_replay(
    route_links: Sequence,
    real_deltat: float,
    physical_key: PhysicalRouteKey,
    method_name: str,
) -> ReferenceReplayResult:
    world = _build_reference_world(route_links, real_deltat)
    if world.DELTAT != real_deltat:
        raise RuntimeError(
            "reference DELTAT does not match the real World before replay. "
            f"method_name={method_name!r} "
            f"reference={world.DELTAT!r} real={real_deltat!r}."
        )
    vehicle = _run_reference_replay_steps(world)
    if world.DELTAT != real_deltat:
        raise RuntimeError(
            "reference DELTAT changed during replay. "
            f"method_name={method_name!r} "
            f"reference={world.DELTAT!r} real={real_deltat!r}."
        )
    if type(world.DELTAN) is not int or world.DELTAN != 1:
        raise RuntimeError(
            "reference DELTAN is not the Python int 1 after replay. "
            f"method_name={method_name!r} got {world.DELTAN!r}."
        )

    departure_timestep = _require_python_timestep(
        vehicle.departure_time,
        "reference departure timestep",
        vehicle.name,
        method_name,
    )
    arrival_timestep = _require_python_timestep(
        vehicle.arrival_time,
        "reference arrival timestep",
        vehicle.name,
        method_name,
    )
    if arrival_timestep < departure_timestep:
        raise RuntimeError(
            "reference arrival timestep is earlier than departure. "
            f"vehicle={vehicle.name!r} method_name={method_name!r} "
            f"departure={departure_timestep} arrival={arrival_timestep}."
        )
    if departure_timestep != 0:
        raise RuntimeError(
            "reference departure timestep must be 0. "
            f"vehicle={vehicle.name!r} method_name={method_name!r} "
            f"departure={departure_timestep}."
        )
    trip_timesteps = arrival_timestep - departure_timestep
    minimum_trip_time_s = trip_timesteps * world.DELTAT
    if not _seconds_match(float(vehicle.travel_time), minimum_trip_time_s):
        raise RuntimeError(
            "reference travel_time does not match timestep difference * DELTAT. "
            f"vehicle={vehicle.name!r} method_name={method_name!r} "
            f"travel_time={vehicle.travel_time!r} "
            f"from_timesteps={minimum_trip_time_s!r}."
        )

    route, _timestamps = vehicle.traveled_route(
        include_arrival_time=False,
        include_departure_time=False,
    )
    if len(route.links) != len(route_links):
        raise RuntimeError(
            "reference route link count does not match the actual route. "
            f"method_name={method_name!r} "
            f"reference={len(route.links)} actual={len(route_links)}."
        )
    pair_index = 0
    for link in route.links:
        expected_length, expected_u = physical_key[1][pair_index]
        if float(link.length) != expected_length or float(link.u) != expected_u:
            raise RuntimeError(
                "reference route does not match the physical route key. "
                f"method_name={method_name!r} index={pair_index} "
                f"length={link.length!r} expected_length={expected_length!r} "
                f"u={link.u!r} expected_u={expected_u!r}."
            )
        pair_index += 1

    analytical_free_flow_time_s = _analytical_free_flow_time_s(route_links)
    return ReferenceReplayResult(
        physical_route_key=physical_key,
        reference_departure_timestep=departure_timestep,
        reference_arrival_timestep=arrival_timestep,
        reference_minimum_trip_timesteps=trip_timesteps,
        minimum_trip_time_s=minimum_trip_time_s,
        analytical_free_flow_time_s=analytical_free_flow_time_s,
        reference_route_link_count=len(route.links),
        reference_world_deltat=world.DELTAT,
        reference_world_deltan=world.DELTAN,
        validation_passed=True,
    )


def _build_vehicle_record(
    context: _EvaluationContext,
    vehicle: Vehicle,
    physical_key: PhysicalRouteKey,
    audit_identity: RouteAuditIdentity,
    reference_result: ReferenceReplayResult,
    true_vot_per_second: float,
    evaluation_cohort: str,
    status_by_name: dict[str, str] | None,
) -> VehicleWaitingTimeRecord:
    if reference_result.reference_world_deltat != context.real_deltat:
        raise RuntimeError(
            "reference DELTAT does not match the real World. "
            f"vehicle={vehicle.name!r} method_name={context.method_name!r} "
            f"reference={reference_result.reference_world_deltat!r} "
            f"real={context.real_deltat!r}."
        )
    actual_departure = _require_python_timestep(
        vehicle.departure_time,
        "actual departure timestep",
        vehicle.name,
        context.method_name,
    )
    actual_arrival = _require_python_timestep(
        vehicle.arrival_time,
        "actual arrival timestep",
        vehicle.name,
        context.method_name,
    )
    if actual_arrival < actual_departure:
        raise ValueError(
            "actual arrival timestep is earlier than departure. "
            f"vehicle={vehicle.name!r} method_name={context.method_name!r} "
            f"departure={actual_departure} arrival={actual_arrival}."
        )
    actual_trip_timesteps = actual_arrival - actual_departure
    reference_trip_timesteps = reference_result.reference_minimum_trip_timesteps
    cumulative_waiting_time_timesteps = (
        actual_trip_timesteps - reference_trip_timesteps
    )
    if cumulative_waiting_time_timesteps < 0:
        context.negative_cumulative_waiting_time_count += 1
        raise RuntimeError(
            "cumulative waiting timesteps are negative and were not changed "
            "to 0. "
            f"vehicle={vehicle.name!r} method_name={context.method_name!r} "
            f"timesteps={cumulative_waiting_time_timesteps}."
        )

    actual_travel_time_s = actual_trip_timesteps * context.real_deltat
    minimum_trip_time_s = reference_trip_timesteps * context.real_deltat
    cumulative_waiting_time_s = (
        cumulative_waiting_time_timesteps * context.real_deltat
    )
    if not _seconds_match(float(vehicle.travel_time), actual_travel_time_s):
        raise RuntimeError(
            "actual travel_time does not match timestep difference * DELTAT. "
            f"vehicle={vehicle.name!r} method_name={context.method_name!r} "
            f"travel_time={vehicle.travel_time!r} "
            f"from_timesteps={actual_travel_time_s!r}."
        )
    if not _seconds_match(reference_result.minimum_trip_time_s, minimum_trip_time_s):
        raise RuntimeError(
            "stored reference minimum trip time does not match "
            "reference timesteps * DELTAT. "
            f"vehicle={vehicle.name!r} method_name={context.method_name!r} "
            f"stored={reference_result.minimum_trip_time_s!r} "
            f"from_timesteps={minimum_trip_time_s!r}."
        )

    weighted_cumulative_waiting_time = (
        cumulative_waiting_time_s * true_vot_per_second
    )
    if status_by_name is None:
        participation_status = None
    else:
        participation_status = status_by_name[vehicle.name]
    return VehicleWaitingTimeRecord(
        vehicle_name=vehicle.name,
        method_name=context.method_name,
        physical_route_key=physical_key,
        route_audit_identity=audit_identity,
        actual_departure_timestep=actual_departure,
        actual_arrival_timestep=actual_arrival,
        actual_trip_timesteps=actual_trip_timesteps,
        reference_departure_timestep=reference_result.reference_departure_timestep,
        reference_arrival_timestep=reference_result.reference_arrival_timestep,
        reference_minimum_trip_timesteps=reference_trip_timesteps,
        cumulative_waiting_time_timesteps=cumulative_waiting_time_timesteps,
        actual_travel_time_s=actual_travel_time_s,
        minimum_trip_time_s=minimum_trip_time_s,
        cumulative_waiting_time_s=cumulative_waiting_time_s,
        true_vot_per_second=true_vot_per_second,
        weighted_cumulative_waiting_time=weighted_cumulative_waiting_time,
        evaluation_cohort=evaluation_cohort,
        method_specific_participation_status=participation_status,
    )


def _counters_from_context(context: _EvaluationContext) -> EvaluationCounters:
    return EvaluationCounters(
        evaluated_vehicle_count=context.evaluated_vehicle_count,
        unique_physical_route_count=context.unique_physical_route_count,
        reference_replay_run_count=context.reference_replay_run_count,
        reference_reuse_count=context.reference_reuse_count,
        unique_audit_identity_count=context.unique_audit_identity_count,
        duplicate_audit_identity_observation_count=(
            context.duplicate_audit_identity_observation_count
        ),
        incomplete_vehicle_count=context.incomplete_vehicle_count,
        validation_failure_count=context.validation_failure_count,
        negative_cumulative_waiting_time_count=(
            context.negative_cumulative_waiting_time_count
        ),
    )


def _require_counter_consistency(
    context: _EvaluationContext,
    counters: EvaluationCounters,
) -> None:
    record_count = len(context.vehicle_records)
    if counters.evaluated_vehicle_count != record_count:
        raise RuntimeError(
            "evaluated vehicle count does not match the record count. "
            f"method_name={context.method_name!r} "
            f"count={counters.evaluated_vehicle_count} records={record_count}."
        )
    if counters.unique_physical_route_count != len(
        context.reference_results_by_physical_key
    ):
        raise RuntimeError(
            "unique physical route count does not match stored reference results. "
            f"method_name={context.method_name!r}."
        )
    if counters.reference_replay_run_count != counters.unique_physical_route_count:
        raise RuntimeError(
            "reference replay count does not match the physical key count. "
            f"method_name={context.method_name!r} "
            f"replay={counters.reference_replay_run_count} "
            f"keys={counters.unique_physical_route_count}."
        )
    expected_reuse = (
        counters.evaluated_vehicle_count - counters.unique_physical_route_count
    )
    if counters.reference_reuse_count != expected_reuse:
        raise RuntimeError(
            "reference reuse count does not match vehicles minus physical keys. "
            f"method_name={context.method_name!r} "
            f"reuse={counters.reference_reuse_count} expected={expected_reuse}."
        )
    if counters.validation_failure_count != 0:
        raise RuntimeError(
            "validation_failure_count is not 0, so no official summary is returned. "
            f"method_name={context.method_name!r} "
            f"count={counters.validation_failure_count}."
        )
    if counters.negative_cumulative_waiting_time_count != 0:
        raise RuntimeError(
            "a negative waiting timestep was counted, so no official summary "
            "is returned. "
            f"method_name={context.method_name!r}."
        )
    if counters.incomplete_vehicle_count != 0:
        raise RuntimeError(
            "an incomplete vehicle was counted, so no official summary is returned. "
            f"method_name={context.method_name!r}."
        )

    unique_from_store = 0
    for identities in context.audit_identities_by_physical_key.values():
        unique_from_store += len(identities)
    if unique_from_store != counters.unique_audit_identity_count:
        raise RuntimeError(
            "unique audit identity count does not match stored identities. "
            f"method_name={context.method_name!r} "
            f"counter={counters.unique_audit_identity_count} "
            f"stored={unique_from_store}."
        )

    seen_by_key = {}
    duplicate_from_records = 0
    for record in context.vehicle_records:
        seen_identities = seen_by_key.get(record.physical_route_key)
        if seen_identities is None:
            seen_identities = []
            seen_by_key[record.physical_route_key] = seen_identities
        if record.route_audit_identity in seen_identities:
            duplicate_from_records += 1
        else:
            seen_identities.append(record.route_audit_identity)
    if duplicate_from_records != counters.duplicate_audit_identity_observation_count:
        raise RuntimeError(
            "duplicate audit observation count does not match the records. "
            f"method_name={context.method_name!r} "
            f"counter={counters.duplicate_audit_identity_observation_count} "
            f"from_records={duplicate_from_records}."
        )


def _build_summary(
    context: _EvaluationContext,
    counters: EvaluationCounters,
) -> NetworkWideWaitingTimeSummary:
    vehicle_count = len(context.vehicle_records)
    if vehicle_count == 0:
        raise RuntimeError(
            "cannot summarize an empty evaluation. "
            f"method_name={context.method_name!r}."
        )
    total_cw = 0.0
    total_weighted = 0.0
    cohort_order = []
    cohort_records = {}
    for record in context.vehicle_records:
        if record.cumulative_waiting_time_timesteps < 0:
            raise RuntimeError(
                "official records must not contain a negative waiting timestep. "
                f"vehicle={record.vehicle_name!r} "
                f"method_name={context.method_name!r}."
            )
        total_cw += record.cumulative_waiting_time_s
        total_weighted += record.weighted_cumulative_waiting_time
        cohort_bucket = cohort_records.get(record.evaluation_cohort)
        if cohort_bucket is None:
            cohort_order.append(record.evaluation_cohort)
            cohort_bucket = []
            cohort_records[record.evaluation_cohort] = cohort_bucket
        cohort_bucket.append(record)

    cohort_summaries = []
    cohort_total_cw = 0.0
    cohort_total_weighted = 0.0
    cohort_vehicle_count = 0
    for cohort_name in cohort_order:
        records = cohort_records[cohort_name]
        cohort_count = len(records)
        cohort_cw = 0.0
        cohort_weighted = 0.0
        for record in records:
            cohort_cw += record.cumulative_waiting_time_s
            cohort_weighted += record.weighted_cumulative_waiting_time
        cohort_summaries.append(
            CohortWaitingTimeSummary(
                evaluation_cohort=cohort_name,
                vehicle_count=cohort_count,
                total_cumulative_waiting_time_s=cohort_cw,
                average_cumulative_waiting_time_s=cohort_cw / cohort_count,
                total_weighted_cumulative_waiting_time=cohort_weighted,
                average_weighted_cumulative_waiting_time=(
                    cohort_weighted / cohort_count
                ),
            )
        )
        cohort_total_cw += cohort_cw
        cohort_total_weighted += cohort_weighted
        cohort_vehicle_count += cohort_count

    if cohort_vehicle_count != vehicle_count:
        raise RuntimeError(
            "cohort vehicle counts do not add up to the evaluated vehicle count. "
            f"method_name={context.method_name!r}."
        )
    if not _seconds_match(cohort_total_cw, total_cw):
        raise RuntimeError(
            "cohort waiting totals do not add up to the overall total. "
            f"method_name={context.method_name!r}."
        )
    if not _seconds_match(cohort_total_weighted, total_weighted):
        raise RuntimeError(
            "cohort weighted totals do not add up to the overall total. "
            f"method_name={context.method_name!r}."
        )

    return NetworkWideWaitingTimeSummary(
        method_name=context.method_name,
        vehicle_count=vehicle_count,
        total_cumulative_waiting_time_s=total_cw,
        average_cumulative_waiting_time_s=total_cw / vehicle_count,
        total_weighted_cumulative_waiting_time=total_weighted,
        average_weighted_cumulative_waiting_time=total_weighted / vehicle_count,
        cohort_summaries=tuple(cohort_summaries),
        counters=counters,
    )


def _build_public_result(
    context: _EvaluationContext,
    summary: NetworkWideWaitingTimeSummary,
    counters: EvaluationCounters,
    vehicle_plan_digest: str | None,
    comparison_metadata: dict | None,
) -> NetworkWideWaitingTimeEvaluationResult:
    reference_results = {}
    for physical_key, reference_result in context.reference_results_by_physical_key.items():
        if not reference_result.validation_passed:
            raise RuntimeError(
                "a reference result in the official result is not validated. "
                f"method_name={context.method_name!r}."
            )
        reference_results[physical_key] = reference_result

    audit_identities = {}
    for physical_key, identities in context.audit_identities_by_physical_key.items():
        audit_identities[physical_key] = tuple(identities)

    for record in context.vehicle_records:
        stored = reference_results.get(record.physical_route_key)
        if stored is None:
            raise RuntimeError(
                "vehicle record has no reference result. "
                f"vehicle={record.vehicle_name!r} "
                f"method_name={context.method_name!r}."
            )
        if record.reference_minimum_trip_timesteps != stored.reference_minimum_trip_timesteps:
            raise RuntimeError(
                "vehicle reference timesteps do not match the stored replay. "
                f"vehicle={record.vehicle_name!r} "
                f"method_name={context.method_name!r}."
            )
        if not _seconds_match(record.minimum_trip_time_s, stored.minimum_trip_time_s):
            raise RuntimeError(
                "vehicle T_min does not match the stored replay. "
                f"vehicle={record.vehicle_name!r} "
                f"method_name={context.method_name!r}."
            )
        stored_identities = audit_identities.get(record.physical_route_key)
        if stored_identities is None or record.route_audit_identity not in stored_identities:
            raise RuntimeError(
                "vehicle audit identity is not registered for its physical key. "
                f"vehicle={record.vehicle_name!r} "
                f"method_name={context.method_name!r}."
            )

    if summary.vehicle_count != len(context.vehicle_records):
        raise RuntimeError(
            "summary vehicle count does not match the records. "
            f"method_name={context.method_name!r}."
        )
    if summary.counters is not counters:
        raise RuntimeError(
            "summary counters are not the official counter object. "
            f"method_name={context.method_name!r}."
        )

    if comparison_metadata is None:
        public_metadata = None
    else:
        public_metadata = MappingProxyType(comparison_metadata)
    return NetworkWideWaitingTimeEvaluationResult(
        vehicle_records=tuple(context.vehicle_records),
        summary=summary,
        reference_results_by_physical_key=MappingProxyType(reference_results),
        audit_identities_by_physical_key=MappingProxyType(audit_identities),
        counters=counters,
        vehicle_plan_digest=vehicle_plan_digest,
        comparison_metadata=public_metadata,
    )


def _require_result_contains_no_simulation_object(
    result: NetworkWideWaitingTimeEvaluationResult,
) -> None:
    if _value_contains_simulation_object(result, []):
        raise RuntimeError(
            "evaluation result contains a simulation object "
            "(World, Vehicle, Node, Link, or Analyzer). "
            f"method_name={result.summary.method_name!r}."
        )


def _value_contains_simulation_object(value: object, seen_ids: list) -> bool:
    if id(value) in seen_ids:
        return False
    seen_ids.append(id(value))
    if isinstance(value, (World, Vehicle, Node, Link, Analyzer)):
        return True
    if isinstance(value, (str, bytes, int, float, bool, type(None))):
        return False
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _value_contains_simulation_object(key, seen_ids):
                return True
            if _value_contains_simulation_object(item, seen_ids):
                return True
        return False
    if isinstance(value, (list, tuple)):
        for item in value:
            if _value_contains_simulation_object(item, seen_ids):
                return True
        return False
    if hasattr(value, "__dataclass_fields__"):
        for field_name in value.__dataclass_fields__:
            item = getattr(value, field_name)
            if _value_contains_simulation_object(item, seen_ids):
                return True
        return False
    return False
