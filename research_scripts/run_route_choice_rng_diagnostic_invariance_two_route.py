"""
Layer-1 invariance trial for production-unchanged route-choice RNG diagnostic.

For each small synthetic case this script runs two simulations in one process:

1. Without the diagnostic installed
2. With ``route_choice_rng_diagnostic`` installed on the same scenario seed

It then compares formal simulation outputs and final RNG fingerprints. Any
mismatch raises ``RuntimeError``. This script does not write CSV or output
directories.

This is not a production seed change, not keyed randomization, and not the
four-method common seed/RNG framework. Do not use it for 3,000-vehicle formal runs.

Run from the repository root::

    python research_scripts/run_route_choice_rng_diagnostic_invariance_two_route.py --static-validate-only
    python research_scripts/run_route_choice_rng_diagnostic_invariance_two_route.py
"""

from __future__ import annotations

import argparse
import ast
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from uxsim import World
import uxsim.uxsim as uxsim_module

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from route_choice_rng_diagnostic import (  # noqa: E402
    EVENT_KIND_IN_TRIP,
    EVENT_KIND_ORIGIN,
    ORIGIN_ADMISSION_REJECTED,
    PROBABILITY_MODE_OMITTED,
    PROBABILITY_MODE_PROVIDED,
    RouteChoiceRngDiagnosticSession,
    capture_rng_state_fingerprint,
    decision_location_key,
    install_route_choice_rng_diagnostic,
    restore_route_choice_rng_diagnostic,
    route_choice_diagnostic_events,
    validate_restored_route_choice_rng_diagnostic,
)

# ---------------------------------------------------------------------------
# 1. Shared constants. World name is the same for diagnostic on and off.
# ---------------------------------------------------------------------------

WORLD_DISPLAY_NAME = "route_choice_rng_invariance_layer1"
FIXED_RANDOM_SEED = 42
DELTAN = 1
DELTAT = 1
REACTION_TIME = 1
DUO_UPDATE_TIME = 10_000
ROUTE_ASSIGNMENT = "uxsim_dynamic_route_choice_from_od"

CASE_TWO_ROUTE_MULTIPLE_ORIGIN = "two_route_multiple_origin_choice_case"
CASE_SINGLE_CANDIDATE = "single_candidate_case"
CASE_BLOCKED_ORIGIN_RETRY = "blocked_origin_retry_case"
CASE_IN_TRIP_RETRY = "in_trip_retry_case"

CASE_NAMES = (
    CASE_TWO_ROUTE_MULTIPLE_ORIGIN,
    CASE_SINGLE_CANDIDATE,
    CASE_BLOCKED_ORIGIN_RETRY,
    CASE_IN_TRIP_RETRY,
)

SCRIPT_BASENAME = SCRIPT_PATH.name


@dataclass(frozen=True)
class CaseCoverageMinimum:
    """Minimum event counts each case must reach in the diagnostic run."""

    case_name: str
    minimum_total_events: int
    minimum_origin_draws: int
    minimum_in_trip_draws: int
    minimum_probability_provided: int
    minimum_probability_omitted: int
    minimum_single_candidate: int
    minimum_multiple_candidate: int
    minimum_rejected_origins: int
    minimum_retry_locations: int
    minimum_same_timestep_same_node_origin_pairs: int


# Coverage roles follow UXsim's timestep order. T=0 ends with DUO route_pref
# replacement, so the first origin choice at T=1 does not keep the addVehicle
# route_pref. Finite paths get p= provided. A path made only of capacity_in=0
# links can get p omitted. 0 means that phenomenon is not this case's job.
IN_TRIP_RETRY_DOWNSTREAM_CAPACITY_IN = 0.01

CASE_COVERAGE_MINIMUMS = {
    # Finite two-route p=provided choices. Does not own p omitted.
    # same_timestep_same_node_origin_pairs is an indirect signal, not proof
    # that one Node.generate call drew more than once.
    CASE_TWO_ROUTE_MULTIPLE_ORIGIN: CaseCoverageMinimum(
        case_name=CASE_TWO_ROUTE_MULTIPLE_ORIGIN,
        minimum_total_events=4,
        minimum_origin_draws=2,
        minimum_in_trip_draws=1,
        minimum_probability_provided=1,
        minimum_probability_omitted=0,
        minimum_single_candidate=0,
        minimum_multiple_candidate=2,
        minimum_rejected_origins=0,
        minimum_retry_locations=0,
        minimum_same_timestep_same_node_origin_pairs=1,
    ),
    # One-candidate choices. A positive preference sum still passes p=.
    CASE_SINGLE_CANDIDATE: CaseCoverageMinimum(
        case_name=CASE_SINGLE_CANDIDATE,
        minimum_total_events=2,
        minimum_origin_draws=1,
        minimum_in_trip_draws=1,
        minimum_probability_provided=1,
        minimum_probability_omitted=0,
        minimum_single_candidate=2,
        minimum_multiple_candidate=0,
        minimum_rejected_origins=0,
        minimum_retry_locations=0,
        minimum_same_timestep_same_node_origin_pairs=0,
    ),
    # Official p-omitted case: the only outlink has capacity_in=0.
    # The vehicle stays waiting. That unfinished state is still compared.
    CASE_BLOCKED_ORIGIN_RETRY: CaseCoverageMinimum(
        case_name=CASE_BLOCKED_ORIGIN_RETRY,
        minimum_total_events=2,
        minimum_origin_draws=2,
        minimum_in_trip_draws=0,
        minimum_probability_provided=0,
        minimum_probability_omitted=1,
        minimum_single_candidate=2,
        minimum_multiple_candidate=0,
        minimum_rejected_origins=1,
        minimum_retry_locations=1,
        minimum_same_timestep_same_node_origin_pairs=0,
    ),
    # Downstream links stay finite for route search (capacity_in > 0) but
    # cannot accept a transfer before tmax, so in-trip choice retries with p=.
    CASE_IN_TRIP_RETRY: CaseCoverageMinimum(
        case_name=CASE_IN_TRIP_RETRY,
        minimum_total_events=3,
        minimum_origin_draws=1,
        minimum_in_trip_draws=2,
        minimum_probability_provided=1,
        minimum_probability_omitted=0,
        minimum_single_candidate=0,
        minimum_multiple_candidate=2,
        minimum_rejected_origins=0,
        minimum_retry_locations=1,
        minimum_same_timestep_same_node_origin_pairs=0,
    ),
}


@dataclass(frozen=True)
class CoverageCounts:
    case_name: str
    total_events: int
    origin_draws: int
    in_trip_draws: int
    probability_provided: int
    probability_omitted: int
    single_candidate: int
    multiple_candidate: int
    rejected_origins: int
    retry_locations: int
    same_timestep_same_node_origin_pairs: int


@dataclass(frozen=True)
class CaseRunSummary:
    case_name: str
    vehicle_count: int
    coverage: CoverageCounts
    formal_match: bool
    rng_match: bool
    order_control_rng_match: bool


# ---------------------------------------------------------------------------
# 2. World helpers
# ---------------------------------------------------------------------------


def _make_base_world(tmax_seconds: float) -> World:
    """Create a fresh World with identical display settings for both runs."""
    world = World(
        name=WORLD_DISPLAY_NAME,
        deltan=DELTAN,
        tmax=tmax_seconds,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=FIXED_RANDOM_SEED,
        duo_update_time=DUO_UPDATE_TIME,
        hard_deterministic_mode=False,
    )
    if world.hard_deterministic_mode is not False:
        raise RuntimeError("hard_deterministic_mode must stay False for this trial.")
    return world


def _route_pref_for_links(world: World, link_weights_by_name: dict[str, float]) -> dict:
    """Build the Link-object-keyed route_pref input expected by World.addVehicle."""
    route_pref = {}
    for link_name, weight in link_weights_by_name.items():
        link = world.get_link(link_name)
        route_pref[link] = float(weight)
    return route_pref


def _finalize_and_run(world: World) -> None:
    world.finalize_scenario()
    world.exec_simulation()


# ---------------------------------------------------------------------------
# 3. Case builders
# ---------------------------------------------------------------------------


def build_two_route_multiple_origin_choice_world() -> World:
    """Finite two-route network for p=provided origin and in-trip choices.

    This case does not own p-omitted draws. Two vehicles can leave the same
    origin on the same timestep. Counting those draws does not prove they came
    from one ``Node.generate`` call. Explicit ``route_pref`` is replaced by DUO
    at the end of T=0, before the first origin choice at T=1.
    """
    world = _make_base_world(tmax_seconds=80.0)
    world.addNode("orig", 0.0, 0.0)
    world.addNode("mid1", 1.0, 1.0)
    world.addNode("mid2", -1.0, 1.0)
    world.addNode("dest", 0.0, 2.0)
    link11 = world.addLink(
        "link11",
        "orig",
        "mid1",
        length=1000.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    world.addLink(
        "link12",
        "mid1",
        "dest",
        length=1000.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    link21 = world.addLink(
        "link21",
        "orig",
        "mid2",
        length=1000.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    world.addLink(
        "link22",
        "mid2",
        "dest",
        length=1000.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    _ = link11
    _ = link21
    pref_positive = _route_pref_for_links(
        world,
        {
            "link11": 3.0,
            "link12": 1.0,
            "link21": 1.0,
            "link22": 3.0,
        },
    )
    pref_zero = _route_pref_for_links(
        world,
        {
            "link11": 0.0,
            "link12": 0.0,
            "link21": 0.0,
            "link22": 0.0,
        },
    )
    world.addVehicle(
        "orig",
        "dest",
        departure_time=0,
        name="veh_pref_mid1",
        route_pref=pref_positive,
        direct_call=True,
    )
    world.addVehicle(
        "orig",
        "dest",
        departure_time=0,
        name="veh_pref_zero",
        route_pref=pref_zero,
        direct_call=True,
    )
    world.addVehicle(
        "orig",
        "dest",
        departure_time=10,
        name="veh_in_trip_only",
        route_pref=pref_positive,
        direct_call=True,
    )
    return world


def build_single_candidate_case_world() -> World:
    """One-outlink line. A positive preference sum still calls choice with p=.

    This case does not own p-omitted draws. DUO replaces route preference at
    the end of T=0, before the first origin choice at T=1.
    """
    world = _make_base_world(tmax_seconds=40.0)
    world.addNode("orig", 0.0, 0.0)
    world.addNode("mid", 0.0, 1.0)
    world.addNode("dest", 0.0, 2.0)
    world.addLink(
        "link_om",
        "orig",
        "mid",
        length=500.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    world.addLink(
        "link_md",
        "mid",
        "dest",
        length=500.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    world.addVehicle(
        "orig",
        "dest",
        departure_time=0,
        name="veh_single_path",
        route_pref=None,
        direct_call=True,
    )
    return world


def build_blocked_origin_retry_case_world() -> World:
    """Official p-omitted case: the only outlink has ``capacity_in=0``.

    Route search treats that link as infinite travel time, so the preference
    sum at the origin choice can be 0 and ``choice`` is called without ``p``.
    Admission stays rejected and the same decision location is retried. The
    vehicle is not expected to finish. Both runs still compare that end state.
    """
    world = _make_base_world(tmax_seconds=30.0)
    world.addNode("orig", 0.0, 0.0)
    world.addNode("dest", 0.0, 1.0)
    # Reject post-choice origin admission using formal link inflow capacity, not
    # a manually placed blocker vehicle.
    world.addLink(
        "link_only",
        "orig",
        "dest",
        length=300.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
        capacity_in=0,
    )
    world.addVehicle(
        "orig",
        "dest",
        departure_time=0,
        name="veh_wait_origin",
        route_pref=None,
        direct_call=True,
    )
    return world


def build_in_trip_retry_case_world() -> World:
    """In-trip redraw while both downstream links are finite but not enterable.

    ``capacity_in=0.01`` keeps the links finite in route search, so DUO can
    leave a positive preference and ``choice`` is called with ``p``. With
    ``DELTAN=1`` and ``tmax=50``, refill stays below one vehicle, so transfer
    fails and the same link-end choice repeats. Explicit ``route_pref`` is not
    assumed to survive: T=0 DUO replaces it before the first origin choice.
    """
    world = _make_base_world(tmax_seconds=50.0)
    world.addNode("orig", 0.0, 0.0)
    world.addNode("merge", 0.0, 1.0)
    world.addNode("dest_a", 1.0, 2.0)
    world.addNode("dest_b", -1.0, 2.0)
    world.addLink(
        "link_up",
        "orig",
        "merge",
        length=400.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
    )
    # Positive but tiny inflow. Route search stays finite. Remain stays below
    # DELTAN through tmax, so either choice still cannot transfer.
    world.addLink(
        "link_a",
        "merge",
        "dest_a",
        length=300.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
        capacity_in=IN_TRIP_RETRY_DOWNSTREAM_CAPACITY_IN,
    )
    world.addLink(
        "link_b",
        "merge",
        "dest_b",
        length=300.0,
        free_flow_speed=20.0,
        jam_density=0.2,
        number_of_lanes=1,
        capacity_in=IN_TRIP_RETRY_DOWNSTREAM_CAPACITY_IN,
    )
    route_pref = _route_pref_for_links(
        world,
        {
            "link_up": 1.0,
            "link_a": 5.0,
            "link_b": 1.0,
        },
    )
    world.addVehicle(
        "orig",
        "dest_a",
        departure_time=0,
        name="veh_merge_retry",
        route_pref=route_pref,
        direct_call=True,
    )
    return world


CASE_BUILDERS = {
    CASE_TWO_ROUTE_MULTIPLE_ORIGIN: build_two_route_multiple_origin_choice_world,
    CASE_SINGLE_CANDIDATE: build_single_candidate_case_world,
    CASE_BLOCKED_ORIGIN_RETRY: build_blocked_origin_retry_case_world,
    CASE_IN_TRIP_RETRY: build_in_trip_retry_case_world,
}


# ---------------------------------------------------------------------------
# 4. Snapshot and comparison
# ---------------------------------------------------------------------------


def _canonical_float(value):
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if math.isnan(value):
            return {"__nan__": True}
        if math.isinf(value):
            if value > 0:
                return {"__inf__": "positive"}
            return {"__inf__": "negative"}
        return value
    raise RuntimeError(f"Unsupported float field type {type(value).__name__}.")


def _canonical_array(values) -> list:
    converted = []
    for item in np.asarray(values).tolist():
        converted.append(_canonical_float(item))
    return converted


def _canonical_log_t_link(vehicle) -> list:
    rows = []
    for entry in vehicle.log_t_link:
        timestep_value = _canonical_float(entry[0])
        label = entry[1]
        if isinstance(label, str):
            label_name = label
        else:
            label_name = label.name
        rows.append([timestep_value, label_name])
    return rows


def _canonical_vehicle_row(vehicle) -> dict:
    current_link_name = None
    if vehicle.link is not None:
        current_link_name = vehicle.link.name
    route_next_link_name = None
    if hasattr(vehicle, "route_next_link") and vehicle.route_next_link is not None:
        route_next_link_name = vehicle.route_next_link.name
    origin_name = vehicle.orig.name
    destination_name = vehicle.dest.name
    return {
        "name": vehicle.name,
        "state": vehicle.state,
        "origin_name": origin_name,
        "destination_name": destination_name,
        "departure_time": _canonical_float(vehicle.departure_time),
        "travel_time": _canonical_float(vehicle.travel_time),
        "current_link_name": current_link_name,
        "route_next_link_name": route_next_link_name,
        "x": _canonical_float(vehicle.x),
        "v": _canonical_float(vehicle.v),
        "link_arrival_time": _canonical_float(vehicle.link_arrival_time),
        "log_t_link": _canonical_log_t_link(vehicle),
    }


def _canonical_link_enter_log(link) -> list:
    rows = []
    keys = sorted(link.vehicles_enter_log.keys())
    for timestep_key in keys:
        vehicle = link.vehicles_enter_log[timestep_key]
        rows.append([_canonical_float(timestep_key), vehicle.name])
    return rows


def _canonical_link_row(link) -> dict:
    return {
        "name": link.name,
        "capacity_in": _canonical_float(link.capacity_in),
        "capacity_in_remain": _canonical_float(link.capacity_in_remain),
        # vehicles_enter_log keeps one vehicle per timestamp on a link.
        # It is not the only evidence of link entry.
        "vehicles_enter_log": _canonical_link_enter_log(link),
        "cum_arrival": _canonical_array(link.cum_arrival),
        "cum_departure": _canonical_array(link.cum_departure),
        "traveltime_actual": _canonical_array(link.traveltime_actual),
    }


def build_formal_snapshot(world: World) -> dict:
    """Collect order-stable formal outputs. Object identity is not stored."""
    rng_json, rng_sha = capture_rng_state_fingerprint(world.rng)
    oc_json, oc_sha = capture_rng_state_fingerprint(world.order_control_rng)
    vehicle_names = sorted(world.VEHICLES.keys())
    vehicles = []
    for vehicle_name in vehicle_names:
        vehicles.append(_canonical_vehicle_row(world.VEHICLES[vehicle_name]))
    link_names = sorted(link.name for link in world.LINKS)
    links = []
    for link_name in link_names:
        links.append(_canonical_link_row(world.get_link(link_name)))
    completed_count = 0
    for vehicle in world.VEHICLES.values():
        if vehicle.state == "end":
            completed_count = completed_count + 1
    return {
        "world_t": int(world.T),
        "world_time": _canonical_float(world.TIME),
        "vehicles": vehicles,
        "links": links,
        "completed_vehicle_count": completed_count,
        "rng_canonical_json": rng_json,
        "rng_sha256": rng_sha,
        "order_control_rng_canonical_json": oc_json,
        "order_control_rng_sha256": oc_sha,
    }


def _compare_values(case_name: str, path: str, left, right) -> None:
    if type(left) is not type(right):
        raise RuntimeError(
            f"{case_name} snapshot type mismatch at {path}: "
            f"{type(left).__name__} vs {type(right).__name__}."
        )
    if isinstance(left, dict):
        left_keys = sorted(left.keys())
        right_keys = sorted(right.keys())
        if left_keys != right_keys:
            raise RuntimeError(
                f"{case_name} snapshot dict key mismatch at {path}: "
                f"{left_keys} vs {right_keys}."
            )
        for key in left_keys:
            _compare_values(case_name, f"{path}.{key}", left[key], right[key])
        return
    if isinstance(left, list):
        if len(left) != len(right):
            raise RuntimeError(
                f"{case_name} snapshot list length mismatch at {path}: "
                f"{len(left)} vs {len(right)}."
            )
        index = 0
        while index < len(left):
            _compare_values(case_name, f"{path}[{index}]", left[index], right[index])
            index = index + 1
        return
    if left != right:
        raise RuntimeError(
            f"{case_name} snapshot value mismatch at {path}: "
            f"without_diagnostic={left!r}, with_diagnostic={right!r}."
        )


def compare_formal_snapshots(case_name: str, without_diag: dict, with_diag: dict) -> None:
    _compare_values(case_name, "formal", without_diag, with_diag)


# ---------------------------------------------------------------------------
# 5. Diagnostic coverage
# ---------------------------------------------------------------------------


def _count_same_timestep_same_node_origin_pairs(events) -> int:
    """Heuristic only: same node and timestep does not prove one generate call.

    The common diagnostic module does not store a generate-call id. Multiple
    origin draws at the same node and timestep are consistent with one
    ``Node.generate`` call when several admissions succeed in that call.
    """
    groups = defaultdict(int)
    for event in events:
        if not event.choice_called:
            continue
        if event.event_kind != EVENT_KIND_ORIGIN:
            continue
        key = (event.decision_node_name, event.decision_timestep)
        groups[key] = groups[key] + 1
    pair_count = 0
    for _key, count in groups.items():
        if count >= 2:
            pair_count = pair_count + 1
    return pair_count


def compute_coverage_counts(case_name: str, events) -> CoverageCounts:
    origin_draws = 0
    in_trip_draws = 0
    probability_provided = 0
    probability_omitted = 0
    single_candidate = 0
    multiple_candidate = 0
    rejected_origins = 0
    attempts_by_location = {}
    for event in events:
        if not event.choice_called:
            continue
        if event.event_kind == EVENT_KIND_ORIGIN:
            origin_draws = origin_draws + 1
        if event.event_kind == EVENT_KIND_IN_TRIP:
            in_trip_draws = in_trip_draws + 1
        if event.probability_mode == PROBABILITY_MODE_PROVIDED:
            probability_provided = probability_provided + 1
        if event.probability_mode == PROBABILITY_MODE_OMITTED:
            probability_omitted = probability_omitted + 1
        candidate_count = len(event.ordered_candidate_link_names)
        if candidate_count == 1:
            single_candidate = single_candidate + 1
        if candidate_count >= 2:
            multiple_candidate = multiple_candidate + 1
        if event.origin_admission == ORIGIN_ADMISSION_REJECTED:
            rejected_origins = rejected_origins + 1
        # Group by decision location, not by attempt number. A location counts
        # once when any of its attempts is 2 or later.
        if event.attempt_ordinal_at_location is not None:
            location_key = decision_location_key(event)
            if location_key not in attempts_by_location:
                attempts_by_location[location_key] = []
            attempts_by_location[location_key].append(event.attempt_ordinal_at_location)
    retry_location_count = 0
    for location_key in attempts_by_location:
        saw_retry = False
        for attempt_ordinal in attempts_by_location[location_key]:
            if attempt_ordinal >= 2:
                saw_retry = True
        if saw_retry:
            retry_location_count = retry_location_count + 1
    return CoverageCounts(
        case_name=case_name,
        total_events=len(events),
        origin_draws=origin_draws,
        in_trip_draws=in_trip_draws,
        probability_provided=probability_provided,
        probability_omitted=probability_omitted,
        single_candidate=single_candidate,
        multiple_candidate=multiple_candidate,
        rejected_origins=rejected_origins,
        retry_locations=retry_location_count,
        same_timestep_same_node_origin_pairs=_count_same_timestep_same_node_origin_pairs(
            events
        ),
    )


def _require_minimum(actual: int, minimum: int, case_name: str, label: str) -> None:
    if actual >= minimum:
        return
    raise RuntimeError(
        f"{case_name} diagnostic coverage failed for {label}: "
        f"saw {actual}, required at least {minimum}."
    )


def validate_coverage_minimums(coverage: CoverageCounts) -> None:
    minimums = CASE_COVERAGE_MINIMUMS[coverage.case_name]
    _require_minimum(
        coverage.total_events,
        minimums.minimum_total_events,
        coverage.case_name,
        "total_events",
    )
    _require_minimum(
        coverage.origin_draws,
        minimums.minimum_origin_draws,
        coverage.case_name,
        "origin_draws",
    )
    _require_minimum(
        coverage.in_trip_draws,
        minimums.minimum_in_trip_draws,
        coverage.case_name,
        "in_trip_draws",
    )
    _require_minimum(
        coverage.probability_provided,
        minimums.minimum_probability_provided,
        coverage.case_name,
        "probability_provided",
    )
    _require_minimum(
        coverage.probability_omitted,
        minimums.minimum_probability_omitted,
        coverage.case_name,
        "probability_omitted",
    )
    _require_minimum(
        coverage.single_candidate,
        minimums.minimum_single_candidate,
        coverage.case_name,
        "single_candidate",
    )
    _require_minimum(
        coverage.multiple_candidate,
        minimums.minimum_multiple_candidate,
        coverage.case_name,
        "multiple_candidate",
    )
    _require_minimum(
        coverage.rejected_origins,
        minimums.minimum_rejected_origins,
        coverage.case_name,
        "rejected_origins",
    )
    _require_minimum(
        coverage.retry_locations,
        minimums.minimum_retry_locations,
        coverage.case_name,
        "retry_locations",
    )
    _require_minimum(
        coverage.same_timestep_same_node_origin_pairs,
        minimums.minimum_same_timestep_same_node_origin_pairs,
        coverage.case_name,
        "same_timestep_same_node_origin_pairs",
    )


def validate_diagnostic_events(session: RouteChoiceRngDiagnosticSession, events) -> None:
    if len(events) == 0:
        raise RuntimeError("Diagnostic run produced zero route-choice events.")
    draw_ordinals_by_vehicle = {}
    attempt_ordinals_by_location = {}
    for event in events:
        if event.world_kind != "real":
            raise RuntimeError(f"Non-real event world_kind {event.world_kind!r}.")
        if event.choice_called:
            if (
                event.rng_state_fingerprint_before is None
                or event.rng_state_fingerprint_after is None
            ):
                raise RuntimeError(
                    f"Draw event for vehicle {event.vehicle_name} is missing fingerprints."
                )
            if event.selected_link_name is None:
                raise RuntimeError(
                    f"Draw event for vehicle {event.vehicle_name} is missing selected_link_name."
                )
            if event.probability_mode == PROBABILITY_MODE_PROVIDED:
                if event.provided_probability_matches_recomputed is not True:
                    raise RuntimeError(
                        f"Draw event for vehicle {event.vehicle_name} did not match "
                        "recomputed normalized probabilities."
                    )
            elif event.probability_mode == PROBABILITY_MODE_OMITTED:
                if event.provided_probability_matches_recomputed is not None:
                    raise RuntimeError(
                        f"Omitted-p event for vehicle {event.vehicle_name} "
                        "stored a probability match flag."
                    )
            if event.event_kind == EVENT_KIND_ORIGIN:
                if event.origin_admission not in ("accepted", "rejected"):
                    raise RuntimeError(
                        f"Origin draw for vehicle {event.vehicle_name} "
                        f"has origin_admission {event.origin_admission!r}."
                    )
            if event.event_kind == EVENT_KIND_IN_TRIP:
                if event.origin_admission is not None:
                    raise RuntimeError(
                        f"In-trip draw for vehicle {event.vehicle_name} "
                        f"has origin_admission {event.origin_admission!r}."
                    )
            if event.vehicle_name not in draw_ordinals_by_vehicle:
                draw_ordinals_by_vehicle[event.vehicle_name] = []
            draw_ordinals_by_vehicle[event.vehicle_name].append(event.route_choice_ordinal)
            # Attempt ordinal itself must not be part of the grouping key.
            # Group by decision location first, then check attempts 1, 2, 3, ...
            location_key = decision_location_key(event)
            if location_key not in attempt_ordinals_by_location:
                attempt_ordinals_by_location[location_key] = []
            attempt_ordinals_by_location[location_key].append(
                event.attempt_ordinal_at_location
            )
            continue
        if event.route_choice_ordinal is not None:
            raise RuntimeError(
                f"Non-draw event for vehicle {event.vehicle_name} advanced route_choice_ordinal."
            )
    for vehicle_name in draw_ordinals_by_vehicle:
        expected = 1
        for ordinal in draw_ordinals_by_vehicle[vehicle_name]:
            if ordinal != expected:
                raise RuntimeError(
                    f"route_choice_ordinal gap for vehicle {vehicle_name}: "
                    f"saw {ordinal}, expected {expected}."
                )
            expected = expected + 1
    for location_key in attempt_ordinals_by_location:
        expected = 1
        for ordinal in attempt_ordinals_by_location[location_key]:
            if ordinal != expected:
                raise RuntimeError(
                    f"attempt_ordinal_at_location gap for {location_key!r}: "
                    f"saw {ordinal}, expected {expected}."
                )
            expected = expected + 1
    if session.proxy_pickle_rejection_count != 0:
        raise RuntimeError(
            "Diagnostic RNG proxy pickle rejection count is not zero."
        )
    if len(session.generator_restore_failure_messages) != 0:
        raise RuntimeError(
            "Generator restore failure messages are not empty after diagnostic run."
        )
    if len(session.call_count_violation_messages) != 0:
        raise RuntimeError(
            "Original production call count violations were recorded."
        )
    if session.real_world.rng is not session.original_generator:
        raise RuntimeError(
            "real_world.rng is not the original Generator object after diagnostic run."
        )


def _require_link_capacity_in(case_name: str, link, expected_capacity_in: float) -> None:
    if link.capacity_in != expected_capacity_in:
        raise RuntimeError(
            f"{case_name} link {link.name} capacity_in is {link.capacity_in!r}; "
            f"expected {expected_capacity_in!r}."
        )


def _require_remain_below_one_vehicle(case_name: str, world: World, link) -> None:
    if not (link.capacity_in_remain < world.DELTAN):
        raise RuntimeError(
            f"{case_name} link {link.name} capacity_in_remain is "
            f"{link.capacity_in_remain!r}; expected < DELTAN {world.DELTAN!r}."
        )


def validate_case_specific_end_state(case_name: str, world: World) -> None:
    """Read end-state inflow capacity. Do not change the World."""
    if case_name == CASE_IN_TRIP_RETRY:
        link_a = world.get_link("link_a")
        link_b = world.get_link("link_b")
        _require_link_capacity_in(
            case_name,
            link_a,
            IN_TRIP_RETRY_DOWNSTREAM_CAPACITY_IN,
        )
        _require_link_capacity_in(
            case_name,
            link_b,
            IN_TRIP_RETRY_DOWNSTREAM_CAPACITY_IN,
        )
        _require_remain_below_one_vehicle(case_name, world, link_a)
        _require_remain_below_one_vehicle(case_name, world, link_b)
        return
    if case_name == CASE_BLOCKED_ORIGIN_RETRY:
        link_only = world.get_link("link_only")
        _require_link_capacity_in(case_name, link_only, 0)
        _require_remain_below_one_vehicle(case_name, world, link_only)


# ---------------------------------------------------------------------------
# 6. Run one case
# ---------------------------------------------------------------------------


def run_case_without_diagnostic(case_name: str) -> dict:
    builder = CASE_BUILDERS[case_name]
    world = builder()
    _finalize_and_run(world)
    validate_case_specific_end_state(case_name, world)
    return build_formal_snapshot(world)


def run_case_with_diagnostic(case_name: str) -> tuple[dict, RouteChoiceRngDiagnosticSession, tuple]:
    builder = CASE_BUILDERS[case_name]
    world = builder()
    session = RouteChoiceRngDiagnosticSession(world, run_method=case_name)
    install_route_choice_rng_diagnostic(session)
    try:
        _finalize_and_run(world)
    finally:
        restore_route_choice_rng_diagnostic(session)
    validate_restored_route_choice_rng_diagnostic(session)
    if uxsim_module.Node.generate is not session.original_node_generate:
        raise RuntimeError(f"{case_name}: Node.generate was not restored by identity.")
    if (
        uxsim_module.Vehicle.route_next_link_choice
        is not session.original_route_next_link_choice
    ):
        raise RuntimeError(
            f"{case_name}: Vehicle.route_next_link_choice was not restored by identity."
        )
    events = route_choice_diagnostic_events(session)
    validate_diagnostic_events(session, events)
    validate_case_specific_end_state(case_name, world)
    snapshot = build_formal_snapshot(world)
    return snapshot, session, events


def run_one_case_invariance(case_name: str) -> CaseRunSummary:
    without_snapshot = run_case_without_diagnostic(case_name)
    with_snapshot, _session, events = run_case_with_diagnostic(case_name)
    compare_formal_snapshots(case_name, without_snapshot, with_snapshot)
    coverage = compute_coverage_counts(case_name, events)
    validate_coverage_minimums(coverage)
    vehicle_count = len(with_snapshot["vehicles"])
    formal_match = True
    rng_match = without_snapshot["rng_sha256"] == with_snapshot["rng_sha256"]
    order_control_rng_match = (
        without_snapshot["order_control_rng_sha256"]
        == with_snapshot["order_control_rng_sha256"]
    )
    if rng_match is False or order_control_rng_match is False:
        raise RuntimeError(f"{case_name}: final RNG fingerprints differ between runs.")
    return CaseRunSummary(
        case_name=case_name,
        vehicle_count=vehicle_count,
        coverage=coverage,
        formal_match=formal_match,
        rng_match=rng_match,
        order_control_rng_match=order_control_rng_match,
    )


def print_case_summary(summary: CaseRunSummary) -> None:
    coverage = summary.coverage
    print(f"case={summary.case_name}")
    print(f"  vehicle_count={summary.vehicle_count}")
    print(f"  diagnostic_event_count={coverage.total_events}")
    print(f"  origin_draw_count={coverage.origin_draws}")
    print(f"  in_trip_draw_count={coverage.in_trip_draws}")
    print(f"  probability_provided_count={coverage.probability_provided}")
    print(f"  probability_omitted_count={coverage.probability_omitted}")
    print(f"  single_candidate_count={coverage.single_candidate}")
    print(f"  multiple_candidate_count={coverage.multiple_candidate}")
    print(f"  rejected_origin_count={coverage.rejected_origins}")
    print(f"  retry_location_count={coverage.retry_locations}")
    print(
        "  same_timestep_same_node_origin_pair_groups="
        f"{coverage.same_timestep_same_node_origin_pairs}"
    )
    print(f"  formal_snapshot_match={summary.formal_match}")
    print(f"  final_rng_state_match={summary.rng_match}")
    print(f"  final_order_control_rng_state_match={summary.order_control_rng_match}")


# ---------------------------------------------------------------------------
# 7. Static validation
# ---------------------------------------------------------------------------


def validate_script_statically() -> None:
    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(SCRIPT_PATH))

    # CASE_NAMES is a tuple of case constant identifiers (ast.Name), not string
    # literals. Static validation checks those names and then the runtime values.
    expected_case_constant_names = (
        "CASE_TWO_ROUTE_MULTIPLE_ORIGIN",
        "CASE_SINGLE_CANDIDATE",
        "CASE_BLOCKED_ORIGIN_RETRY",
        "CASE_IN_TRIP_RETRY",
    )
    expected_case_values = (
        "two_route_multiple_origin_choice_case",
        "single_candidate_case",
        "blocked_origin_retry_case",
        "in_trip_retry_case",
    )

    case_names_assignments = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "CASE_NAMES":
                case_names_assignments.append(node)

    if len(case_names_assignments) == 0:
        raise RuntimeError(
            "Static validation could not find a CASE_NAMES assignment in the module body."
        )
    if len(case_names_assignments) > 1:
        raise RuntimeError(
            f"Static validation found {len(case_names_assignments)} CASE_NAMES "
            "assignments; expected exactly one."
        )

    case_names_assign = case_names_assignments[0]
    if not isinstance(case_names_assign.value, ast.Tuple):
        raise RuntimeError(
            "Static validation expected CASE_NAMES to be assigned from a tuple; "
            f"got {type(case_names_assign.value).__name__}."
        )

    referenced_constant_names = []
    for element in case_names_assign.value.elts:
        if not isinstance(element, ast.Name):
            raise RuntimeError(
                "Static validation expected each CASE_NAMES tuple element to be "
                f"ast.Name; got {type(element).__name__}."
            )
        referenced_constant_names.append(element.id)

    if tuple(referenced_constant_names) != expected_case_constant_names:
        raise RuntimeError(
            "Static validation CASE_NAMES constant references do not match: "
            f"expected {expected_case_constant_names!r}, "
            f"got {tuple(referenced_constant_names)!r}."
        )

    if CASE_NAMES != expected_case_values:
        raise RuntimeError(
            "Static validation CASE_NAMES runtime values do not match: "
            f"expected {expected_case_values!r}, got {CASE_NAMES!r}."
        )
    if FIXED_RANDOM_SEED != 42:
        raise RuntimeError("Static validation expects FIXED_RANDOM_SEED == 42.")
    if WORLD_DISPLAY_NAME != "route_choice_rng_invariance_layer1":
        raise RuntimeError("Static validation expects a fixed WORLD_DISPLAY_NAME.")
    required_functions = (
        "build_formal_snapshot",
        "run_case_without_diagnostic",
        "run_case_with_diagnostic",
        "run_one_case_invariance",
        "validate_script_statically",
    )
    defined_names = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defined_names.add(node.name)
    for function_name in required_functions:
        if function_name not in defined_names:
            raise RuntimeError(
                f"Static validation missing required function {function_name}."
            )
    import_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "tests":
            import_nodes.append(node)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("tests"):
                    import_nodes.append(node)
    if len(import_nodes) != 0:
        raise RuntimeError("Static validation found a forbidden tests import.")
    print(
        "static validation ok: route-choice RNG diagnostic layer-1 invariance script",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# 8. Main
# ---------------------------------------------------------------------------


def run_all_cases() -> bool:
    summaries = []
    for case_name in CASE_NAMES:
        summary = run_one_case_invariance(case_name)
        summaries.append(summary)
        print_case_summary(summary)
    print("all_cases_passed=True")
    print("production_files_modified=False")
    print("existing_outputs_modified=False")
    print("keyed_randomization_used=False")
    print("simulation_result_invariance_confirmed=True")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Layer-1 route-choice RNG diagnostic invariance trial.",
    )
    parser.add_argument(
        "--static-validate-only",
        action="store_true",
        help="Parse this script and check constants without running simulation.",
    )
    args = parser.parse_args()
    if args.static_validate_only:
        validate_script_statically()
        return 0
    run_all_cases()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())