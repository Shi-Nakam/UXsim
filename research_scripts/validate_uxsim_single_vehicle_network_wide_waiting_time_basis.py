"""
Independent UXsim validation for network-wide ACWT / ACWWT basis (single vehicle, no traffic).

Does not modify production, write outputs, or register pytest cases.
Console reporting only.

T_min,z is the travel_time of a fresh single-vehicle UXsim replay of the same
link sequence (uxsim_reference_minimum_trip_time_s).

route_free_flow_time_s = sum(length / free_flow_speed) is an analytical reference
only. It is not the formal T_min,z.

1 + sum(length / u) was falsified by CASE 4 (analytical 43s, UXsim travel_time 42s).
Do not add a fixed origin-boundary second into T_min,z.

CW_z = actual travel_time - replay minimum travel_time.

CASE 6A-6E are separate sensitivity worlds. They do not change CASE 1-5.
They do not choose a production cache key. They only print which route
attributes changed the replay travel_time in these single-vehicle trials.

CASE 7A-7G check an in-memory physical route key. The key is
(DELTAT, ((length, link.u), ...)) with link order kept. It does not round
floats, include link names, or define a persistent cache.

CASE 8A-8F are a verification-only check of shared network-wide waiting time.
They are not production code and are not a template to copy into production.
true_vot in CASE 8 is a plain verification coefficient. It does not settle
the formal ACWWT unit contract.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from typing import Callable, Sequence

from uxsim import World
from uxsim.analyzer import Analyzer as UxsimAnalyzer
from uxsim.uxsim import Link as UxsimLink
from uxsim.uxsim import Node as UxsimNode
from uxsim.uxsim import Vehicle as UxsimVehicle

TIME_ABS_TOL = 1e-6

SPEED_60KPH_M_PER_S = 60.0 / 3.6

# Large enough that one Vehicle cannot be held by link inflow or outflow.
# UXsim stores an explicit capacity_in remain as capacity_in * DELTAT.
# Do not use infinity. CASE 1-5 do not use this constant.
NON_BINDING_CAPACITY = 1000000.0

# Confirmed CASE 2 replay travel_time. Sensitivity cases only compare against it.
CASE2_REFERENCE_MINIMUM_TRIP_TIME_S = 37.0

# UXsim Link default. CASE 2 does not pass jam_density, so each link keeps this.
CASE2_DEFAULT_JAM_DENSITY = 0.2

CASE6_LINK_LENGTH_M = 200.0
CASE6A_JAM_DENSITIES = (0.05, 0.12, 0.45)
CASE6B_NUMBER_OF_LANES = (2, 3, 2)
CASE6_CASE2_LINK_NAMES = ("l1", "l2", "l3")
CASE6C_LINK_NAMES = ("link_alpha", "link_beta", "link_gamma")
CASE6D_REACTION_TIME_S = 0.5
CASE6D_DELTAN = 1
CASE6E1_DELTAN = 2
CASE6E1_REACTION_TIME_S = 1.0
CASE6E2_DELTAN = 2
CASE6E2_REACTION_TIME_S = 0.5

@dataclass(frozen=True)
class CaseSpec:
    name: str
    expected_link_names: tuple[str, ...]
    expected_route_free_flow_time_s: float
    expected_replay_minimum_trip_time_s: float
    expected_cumulative_waiting_time_s: float
    build: Callable[[], World]


@dataclass(frozen=True)
class RouteLinkSpec:
    name: str
    length: float
    free_flow_speed: float
    jam_density: float
    number_of_lanes: int


def _make_world(
    case_name: str,
    tmax_seconds: float = 600.0,
    deltan: int = 1,
    reaction_time: float = 1.0,
) -> World:
    # Defaults reproduce the CASE 1-5 world: DELTAN=1, REACTION_TIME=1, DELTAT=1.
    return World(
        name=f"validate_network_wide_waiting_{case_name}",
        deltan=deltan,
        reaction_time=reaction_time,
        tmax=tmax_seconds,
        random_seed=0,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        hard_deterministic_mode=True,
    )


def _add_vehicle_with_route(
    world: World,
    vehicle_name: str,
    orig: str,
    dest: str,
    departure_timestep: int,
    route_link_names: Sequence[str],
) -> None:
    vehicle = world.addVehicle(
        orig,
        dest,
        departure_timestep,
        name=vehicle_name,
        departure_time_is_time_step=1,
    )
    vehicle.enforce_route(list(route_link_names))


CASE4_VEHICLE_NAME = "veh_case4"
CASE4_TRACE_WINDOW_HALF_WIDTH = 3


@dataclass(frozen=True)
class Case4TraceRow:
    world_t: int
    state: str
    link_name: str | None
    x: float
    x_next: float
    move_remain: float
    v: float
    link_arrival_time: float
    flag_waiting_for_trip_end: int


def _format_trace_float(value: float) -> str:
    return repr(float(value))


def _attach_case4_trajectory_recorder(world: World) -> list[Case4TraceRow]:
    vehicle = world.VEHICLES[CASE4_VEHICLE_NAME]
    trace_rows: list[Case4TraceRow] = []

    def record_vehicle_step(veh) -> None:
        link_name = None
        if veh.link is not None:
            link_name = veh.link.name
        trace_rows.append(
            Case4TraceRow(
                world_t=int(veh.W.T),
                state=str(veh.state),
                link_name=link_name,
                x=float(veh.x),
                x_next=float(veh.x_next),
                move_remain=float(veh.move_remain),
                v=float(veh.v),
                link_arrival_time=float(veh.link_arrival_time),
                flag_waiting_for_trip_end=int(veh.flag_waiting_for_trip_end),
            )
        )

    vehicle.user_function = record_vehicle_step
    return trace_rows


def _trace_row_to_line(row: Case4TraceRow) -> str:
    return (
        f"  T={row.world_t} state={row.state} link={row.link_name} "
        f"x={_format_trace_float(row.x)} "
        f"x_next={_format_trace_float(row.x_next)} "
        f"move_remain={_format_trace_float(row.move_remain)} "
        f"v={_format_trace_float(row.v)} "
        f"link_arrival_time={_format_trace_float(row.link_arrival_time)} "
        f"flag_waiting_for_trip_end={row.flag_waiting_for_trip_end}"
    )


def _rows_in_timestep_window(
    trace_rows: list[Case4TraceRow],
    center_t: int,
    half_width: int,
) -> list[Case4TraceRow]:
    low = center_t - half_width
    high = center_t + half_width
    return [row for row in trace_rows if low <= row.world_t <= high]


def _first_timestep_where(
    trace_rows: list[Case4TraceRow],
    predicate,
) -> int | None:
    for row in trace_rows:
        if predicate(row):
            return row.world_t
    return None


def _print_case4_trajectory_trace(trace_rows: list[Case4TraceRow]) -> None:
    if not trace_rows:
        print("CASE 4 trajectory trace: (empty — recorder did not run)")
        return

    print("")
    print("CASE 4 trajectory trace (console-only diagnostic, memory recorded)")

    first_l1_t = _first_timestep_where(
        trace_rows,
        lambda row: row.link_name == "l1" and row.state == "run",
    )
    if first_l1_t is not None:
        print("")
        print("--- first Link entry (l1) vicinity ---")
        for row in _rows_in_timestep_window(
            trace_rows, first_l1_t, CASE4_TRACE_WINDOW_HALF_WIDTH + 1
        ):
            print(_trace_row_to_line(row))

    first_l2_t = _first_timestep_where(
        trace_rows, lambda row: row.link_name == "l2"
    )
    if first_l2_t is not None:
        print("")
        print("--- l1 -> l2 transfer vicinity ---")
        for row in _rows_in_timestep_window(
            trace_rows, first_l2_t, CASE4_TRACE_WINDOW_HALF_WIDTH
        ):
            print(_trace_row_to_line(row))

    first_l3_t = _first_timestep_where(
        trace_rows, lambda row: row.link_name == "l3"
    )
    if first_l3_t is not None:
        print("")
        print("--- l2 -> l3 transfer vicinity ---")
        for row in _rows_in_timestep_window(
            trace_rows, first_l3_t, CASE4_TRACE_WINDOW_HALF_WIDTH
        ):
            print(_trace_row_to_line(row))

        transfer_index = None
        for index in range(1, len(trace_rows)):
            previous = trace_rows[index - 1]
            current = trace_rows[index]
            if previous.link_name == "l2" and current.link_name == "l3":
                transfer_index = index
                break
        if transfer_index is not None:
            print("")
            print("--- l2 -> l3 transfer (high precision) ---")
            before_row = trace_rows[transfer_index - 1]
            after_row = trace_rows[transfer_index]
            print("  immediately before transfer (still on l2):")
            print(_trace_row_to_line(before_row))
            print("  immediately after transfer (on l3):")
            print(_trace_row_to_line(after_row))
        else:
            print("  (could not locate adjacent l2->l3 rows in trace)")

    last_l3_t = None
    for row in trace_rows:
        if row.link_name == "l3":
            last_l3_t = row.world_t
    end_t = _first_timestep_where(trace_rows, lambda row: row.state == "end")
    if last_l3_t is not None:
        center = end_t if end_t is not None else last_l3_t
        print("")
        print("--- l3 terminal / trip end vicinity ---")
        for row in _rows_in_timestep_window(
            trace_rows, center, CASE4_TRACE_WINDOW_HALF_WIDTH + 2
        ):
            print(_trace_row_to_line(row))


def _run_to_vehicle_end(world: World) -> None:
    world.finalize_scenario()
    if len(world.VEHICLES) != 1:
        raise RuntimeError(
            f"Expected exactly 1 vehicle, got {len(world.VEHICLES)}."
        )
    world.exec_simulation()
    vehicle = next(iter(world.VEHICLES.values()))
    if vehicle.state != "end":
        raise RuntimeError(
            f"Simulation finished but vehicle state is {vehicle.state!r}, expected 'end'. "
            f"World.T={world.T}, TSIZE={world.TSIZE}."
        )


def _link_free_flow_seconds(link) -> float:
    return float(link.length) / float(link.u)


def _actual_link_names_from_route(route) -> list[str]:
    return [link.name for link in route.links]


def _scheduled_departure_seconds(vehicle) -> float:
    route, timestamps = vehicle.traveled_route(
        include_arrival_time=True,
        include_departure_time=True,
    )
    del route
    if not timestamps:
        raise RuntimeError("traveled_route returned empty timestamps.")
    return float(timestamps[0])


def _first_link_entry_seconds(vehicle) -> float | None:
    for time_seconds, item in vehicle.log_t_link:
        if item != "home" and item != "end":
            return float(time_seconds)
    return None


def _format_log_t_link(vehicle) -> list[str]:
    lines: list[str] = []
    for time_seconds, item in vehicle.log_t_link:
        if item == "home":
            label = "home"
        elif item == "end":
            label = "end"
        else:
            label = item.name
        lines.append(f"  t={time_seconds}s  {label}")
    return lines


def _print_case_header(case_name: str) -> None:
    print("")
    print("=" * 72)
    print(case_name)
    print("=" * 72)


def _raise_timing_mismatch(case_name: str, message: str, **values: object) -> None:
    parts = [f"{case_name}: {message}"]
    for key, value in values.items():
        parts.append(f"  {key} = {value!r}")
    raise RuntimeError("\n".join(parts))


def _route_link_specs(vehicle) -> list[RouteLinkSpec]:
    route, _timestamps = vehicle.traveled_route(
        include_arrival_time=False,
        include_departure_time=False,
    )
    specs: list[RouteLinkSpec] = []
    for link in route.links:
        specs.append(
            RouteLinkSpec(
                name=link.name,
                length=float(link.length),
                free_flow_speed=float(link.u),
                jam_density=float(link.jam_density),
                number_of_lanes=int(link.number_of_lanes),
            )
        )
    return specs


def _analytical_route_free_flow_time_s(specs: Sequence[RouteLinkSpec]) -> float:
    total = 0.0
    for spec in specs:
        total += spec.length / spec.free_flow_speed
    return total


def _format_route_signature(
    specs: Sequence[RouteLinkSpec],
    deltat: float,
    deltan: int,
) -> str:
    pieces = [f"DELTAT={deltat}", f"DELTAN={deltan}"]
    for spec in specs:
        pieces.append(
            f"{spec.name}(length={spec.length},free_flow_speed={spec.free_flow_speed})"
        )
    return " | ".join(pieces)


def _build_reference_world_from_actual_route(
    specs: Sequence[RouteLinkSpec],
    deltan: int = 1,
    reaction_time: float = 1.0,
    capacity_in: float | None = None,
    capacity_out: float | None = None,
) -> World:
    """Fresh single-vehicle world. Same link sequence, no extra waiting causes.

    Defaults match CASE 1-5: DELTAN=1, REACTION_TIME=1, and UXsim's own
    capacity_in / capacity_out. Sensitivity cases pass the actual World's
    deltan and reaction_time. They pass NON_BINDING_CAPACITY only when that
    case is excluding capacity waiting.
    """
    if len(specs) == 0:
        raise RuntimeError("Cannot build a reference world from an empty route.")
    if (capacity_in is None) != (capacity_out is None):
        raise RuntimeError(
            "Reference replay capacity_in and capacity_out must be set together."
        )
    world = _make_world(
        "reference_replay",
        deltan=deltan,
        reaction_time=reaction_time,
    )
    node_count = len(specs) + 1
    for index in range(node_count):
        world.addNode(f"ref_n{index}", float(index), 0.0, signal=[0])
    link_names: list[str] = []
    for index, spec in enumerate(specs):
        if capacity_in is None:
            world.addLink(
                spec.name,
                f"ref_n{index}",
                f"ref_n{index + 1}",
                length=spec.length,
                free_flow_speed=spec.free_flow_speed,
                jam_density=spec.jam_density,
                number_of_lanes=spec.number_of_lanes,
            )
        else:
            world.addLink(
                spec.name,
                f"ref_n{index}",
                f"ref_n{index + 1}",
                length=spec.length,
                free_flow_speed=spec.free_flow_speed,
                jam_density=spec.jam_density,
                number_of_lanes=spec.number_of_lanes,
                capacity_in=capacity_in,
                capacity_out=capacity_out,
            )
        link_names.append(spec.name)
    _add_vehicle_with_route(
        world,
        "veh_reference",
        "ref_n0",
        f"ref_n{len(specs)}",
        0,
        link_names,
    )
    return world


def _run_reference_minimum_trip_time(
    specs: Sequence[RouteLinkSpec],
    deltan: int = 1,
    reaction_time: float = 1.0,
    capacity_in: float | None = None,
    capacity_out: float | None = None,
):
    world = _build_reference_world_from_actual_route(
        specs,
        deltan=deltan,
        reaction_time=reaction_time,
        capacity_in=capacity_in,
        capacity_out=capacity_out,
    )
    try:
        _run_to_vehicle_end(world)
    except RuntimeError as error:
        raise RuntimeError(
            "Reference replay did not complete. "
            f"route={[spec.name for spec in specs]}. {error}"
        ) from error
    vehicle = next(iter(world.VEHICLES.values()))
    return float(vehicle.travel_time), vehicle, world


def _validate_vehicle_case(case: CaseSpec, show_case4_trace: bool) -> None:
    world = case.build()
    case4_trace_rows: list[Case4TraceRow] | None = None
    if show_case4_trace and case.name == "CASE 4: heterogeneous links":
        case4_trace_rows = _attach_case4_trajectory_recorder(world)

    _run_to_vehicle_end(world)
    vehicle = next(iter(world.VEHICLES.values()))

    route, timestamps = vehicle.traveled_route(
        include_arrival_time=True,
        include_departure_time=True,
    )
    actual_names = _actual_link_names_from_route(route)
    route_specs = _route_link_specs(vehicle)
    route_free_flow_time_s = _analytical_route_free_flow_time_s(route_specs)
    actual_travel_time_s = float(vehicle.travel_time)

    replay_minimum_trip_time_s, replay_vehicle, replay_world = (
        _run_reference_minimum_trip_time(route_specs)
    )
    cumulative_waiting_time_s = (
        actual_travel_time_s - replay_minimum_trip_time_s
    )
    replay_minus_analytical_s = (
        replay_minimum_trip_time_s - route_free_flow_time_s
    )

    scheduled_departure_s = _scheduled_departure_seconds(vehicle)
    first_link_entry_s = _first_link_entry_seconds(vehicle)
    replay_scheduled_departure_s = _scheduled_departure_seconds(replay_vehicle)
    replay_first_link_entry_s = _first_link_entry_seconds(replay_vehicle)
    if first_link_entry_s is None or replay_first_link_entry_s is None:
        _raise_timing_mismatch(
            case.name,
            "missing first Link entry on actual or reference replay",
            actual_log=vehicle.log_t_link,
            replay_log=replay_vehicle.log_t_link,
        )

    actual_origin_boundary_s = first_link_entry_s - scheduled_departure_s
    replay_origin_boundary_s = (
        replay_first_link_entry_s - replay_scheduled_departure_s
    )
    additional_origin_wait_from_boundary_s = (
        actual_origin_boundary_s - replay_origin_boundary_s
    )

    _print_case_header(case.name)
    print("Vehicle fields:")
    print(f"  departure_time (timestep): {vehicle.departure_time}")
    print(f"  arrival_time (timestep):   {vehicle.arrival_time}")
    print(f"  state:                     {vehicle.state}")

    print("Route (traveled_route):")
    print(f"  link names: {actual_names}")
    for link in route.links:
        ff = _link_free_flow_seconds(link)
        print(
            f"  {link.name}: length={link.length}m u={link.u}m/s length/u={ff}s"
        )
    print(f"  timestamps: {timestamps}")

    print("log_t_link:")
    for line in _format_log_t_link(vehicle):
        print(line)

    print("Route signature (memory only, not cached):")
    print(
        "  "
        + _format_route_signature(
            route_specs, world.DELTAT, world.DELTAN
        )
    )

    print("Timing summary (seconds):")
    print(f"  scheduled departure:                    {scheduled_departure_s}")
    print(f"  first Link entry:                       {first_link_entry_s}")
    print(f"  actual origin entry boundary:           {actual_origin_boundary_s}")
    print(f"  replay origin entry boundary:           {replay_origin_boundary_s}")
    print(
        f"  additional origin wait from boundary:   "
        f"{additional_origin_wait_from_boundary_s}"
    )
    print(f"  analytical route free-flow time:        {route_free_flow_time_s}")
    print(f"  replay minimum travel time:             {replay_minimum_trip_time_s}")
    print(
        f"  replay minimum minus analytical:        {replay_minus_analytical_s}"
    )
    print(f"  actual travel time:                     {actual_travel_time_s}")
    print(
        f"  cumulative waiting time:                {cumulative_waiting_time_s}"
    )
    print(
        "  note: 1 + sum(length/u) is not T_min,z; CASE 4 falsified that formula."
    )

    if case4_trace_rows is not None:
        _print_case4_trajectory_trace(case4_trace_rows)

    if actual_names != list(case.expected_link_names):
        raise AssertionError(
            f"{case.name}: traveled link names {actual_names!r} != "
            f"expected {list(case.expected_link_names)!r}."
        )

    if not math.isclose(
        route_free_flow_time_s,
        case.expected_route_free_flow_time_s,
        abs_tol=TIME_ABS_TOL,
    ):
        _raise_timing_mismatch(
            case.name,
            "route_free_flow_time_s mismatch",
            observed=route_free_flow_time_s,
            expected=case.expected_route_free_flow_time_s,
        )

    if not math.isclose(
        replay_minimum_trip_time_s,
        case.expected_replay_minimum_trip_time_s,
        abs_tol=TIME_ABS_TOL,
    ):
        _raise_timing_mismatch(
            case.name,
            "replay minimum travel_time mismatch",
            replay_minimum_trip_time_s=replay_minimum_trip_time_s,
            expected=case.expected_replay_minimum_trip_time_s,
            analytical_route_free_flow_time_s=route_free_flow_time_s,
            actual_travel_time_s=actual_travel_time_s,
        )

    expected_tt_from_timesteps = (
        (vehicle.arrival_time - vehicle.departure_time) * world.DELTAT
    )
    if not math.isclose(
        actual_travel_time_s, expected_tt_from_timesteps, abs_tol=TIME_ABS_TOL
    ):
        _raise_timing_mismatch(
            case.name,
            "travel_time != (arrival_time - departure_time) * DELTAT",
            travel_time=actual_travel_time_s,
            from_timesteps=expected_tt_from_timesteps,
        )

    if not math.isclose(
        cumulative_waiting_time_s,
        case.expected_cumulative_waiting_time_s,
        abs_tol=TIME_ABS_TOL,
    ):
        _raise_timing_mismatch(
            case.name,
            "cumulative waiting time != expected (actual travel_time - replay minimum)",
            cumulative_waiting_time_s=cumulative_waiting_time_s,
            expected=case.expected_cumulative_waiting_time_s,
            actual_travel_time_s=actual_travel_time_s,
            replay_minimum_trip_time_s=replay_minimum_trip_time_s,
            analytical_route_free_flow_time_s=route_free_flow_time_s,
            replay_minus_analytical_s=replay_minus_analytical_s,
        )

    if case.expected_cumulative_waiting_time_s != 0.0:
        if not math.isclose(
            actual_travel_time_s,
            replay_minimum_trip_time_s + additional_origin_wait_from_boundary_s,
            abs_tol=TIME_ABS_TOL,
        ):
            _raise_timing_mismatch(
                case.name,
                "actual travel_time != replay minimum + additional origin wait",
                actual_travel_time_s=actual_travel_time_s,
                replay_minimum_trip_time_s=replay_minimum_trip_time_s,
                additional_origin_wait_from_boundary_s=(
                    additional_origin_wait_from_boundary_s
                ),
            )
        if not math.isclose(
            cumulative_waiting_time_s,
            additional_origin_wait_from_boundary_s,
            abs_tol=TIME_ABS_TOL,
        ):
            _raise_timing_mismatch(
                case.name,
                "CW_z != additional origin wait from first-link boundary",
                cumulative_waiting_time_s=cumulative_waiting_time_s,
                additional_origin_wait_from_boundary_s=(
                    additional_origin_wait_from_boundary_s
                ),
                actual_origin_boundary_s=actual_origin_boundary_s,
                replay_origin_boundary_s=replay_origin_boundary_s,
            )

    del replay_world

    print(f"PASS {case.name}")


def build_case1() -> World:
    world = _make_world("case1")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("dest", 1.0, 0.0, signal=[0])
    world.addLink(
        "l1",
        "orig",
        "dest",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    _add_vehicle_with_route(world, "veh_case1", "orig", "dest", 0, ("l1",))
    return world


def build_case2() -> World:
    world = _make_world("case2")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("internal_1", 1.0, 0.0, signal=[0])
    world.addNode("internal_2", 2.0, 0.0, signal=[0])
    world.addNode("dest", 3.0, 0.0, signal=[0])
    world.addLink(
        "l1",
        "orig",
        "internal_1",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    world.addLink(
        "l2",
        "internal_1",
        "internal_2",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    world.addLink(
        "l3",
        "internal_2",
        "dest",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    _add_vehicle_with_route(
        world, "veh_case2", "orig", "dest", 0, ("l1", "l2", "l3")
    )
    return world


def build_case3() -> World:
    world = _make_world("case3")
    world.addNode("orig_external", 0.0, 0.0, signal=[0])
    world.addNode("intermediate_external", 1.0, 0.0, signal=[0])
    world.addNode("internal", 2.0, 0.0, signal=[0])
    world.addNode("dest_external", 3.0, 0.0, signal=[0])
    world.addLink(
        "l_oe_ie",
        "orig_external",
        "intermediate_external",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    world.addLink(
        "l_ie_in",
        "intermediate_external",
        "internal",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    world.addLink(
        "l_in_de",
        "internal",
        "dest_external",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    _add_vehicle_with_route(
        world,
        "veh_case3",
        "orig_external",
        "dest_external",
        0,
        ("l_oe_ie", "l_ie_in", "l_in_de"),
    )
    return world


def build_case4() -> World:
    world = _make_world("case4")
    world.addNode("n0", 0.0, 0.0, signal=[0])
    world.addNode("n1", 1.0, 0.0, signal=[0])
    world.addNode("n2", 2.0, 0.0, signal=[0])
    world.addNode("n3", 3.0, 0.0, signal=[0])
    world.addLink(
        "l1",
        "n0",
        "n1",
        length=120.0,
        free_flow_speed=10.0,
        number_of_lanes=1,
    )
    world.addLink(
        "l2",
        "n1",
        "n2",
        length=200.0,
        free_flow_speed=20.0,
        number_of_lanes=1,
    )
    world.addLink(
        "l3",
        "n2",
        "n3",
        length=300.0,
        free_flow_speed=15.0,
        number_of_lanes=1,
    )
    _add_vehicle_with_route(world, "veh_case4", "n0", "n3", 0, ("l1", "l2", "l3"))
    return world


CASE5_RELEASE_TIMESTEP = 5

# capacity_in stays closed until T=5. Unconstrained replay of the same link
# finishes in 13s. The extra 4s is waiting, not part of T_min,z.
CASE5_EXPECTED_ADDITIONAL_ORIGIN_WAIT_S = 4.0


def _case5_release_first_link_inflow(link) -> None:
    if link.W.T == CASE5_RELEASE_TIMESTEP:
        link.capacity_in = 1.0
        link.capacity_in_remain = link.W.DELTAN


def build_case5() -> World:
    world = _make_world("case5")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("dest", 1.0, 0.0, signal=[0])
    world.addLink(
        "l1",
        "orig",
        "dest",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
        capacity_in=0.0,
        user_function=_case5_release_first_link_inflow,
    )
    _add_vehicle_with_route(world, "veh_case5", "orig", "dest", 0, ("l1",))
    return world


CASES: tuple[CaseSpec, ...] = (
    CaseSpec(
        name="CASE 1: 1 Link",
        expected_link_names=("l1",),
        expected_route_free_flow_time_s=12.0,
        expected_replay_minimum_trip_time_s=13.0,
        expected_cumulative_waiting_time_s=0.0,
        build=build_case1,
    ),
    CaseSpec(
        name="CASE 2: 3 Link internal nodes",
        expected_link_names=("l1", "l2", "l3"),
        expected_route_free_flow_time_s=36.0,
        expected_replay_minimum_trip_time_s=37.0,
        expected_cumulative_waiting_time_s=0.0,
        build=build_case2,
    ),
    CaseSpec(
        name="CASE 3: external nodes on path",
        expected_link_names=("l_oe_ie", "l_ie_in", "l_in_de"),
        expected_route_free_flow_time_s=36.0,
        expected_replay_minimum_trip_time_s=37.0,
        expected_cumulative_waiting_time_s=0.0,
        build=build_case3,
    ),
    CaseSpec(
        name="CASE 4: heterogeneous links",
        expected_link_names=("l1", "l2", "l3"),
        expected_route_free_flow_time_s=42.0,
        expected_replay_minimum_trip_time_s=42.0,
        expected_cumulative_waiting_time_s=0.0,
        build=build_case4,
    ),
    CaseSpec(
        name="CASE 5: origin inflow wait",
        expected_link_names=("l1",),
        expected_route_free_flow_time_s=12.0,
        expected_replay_minimum_trip_time_s=13.0,
        expected_cumulative_waiting_time_s=CASE5_EXPECTED_ADDITIONAL_ORIGIN_WAIT_S,
        build=build_case5,
    ),
)


@dataclass(frozen=True)
class SensitivityCaseSpec:
    key: str
    name: str
    changed_attributes: tuple[str, ...]
    fixed_attributes: tuple[str, ...]
    signature_candidates: tuple[str, ...]
    uses_non_binding_capacity: bool
    matched_actual_reference_attributes: tuple[str, ...]
    expected_link_names: tuple[str, ...]
    expected_deltan: int
    expected_reaction_time_s: float
    expects_fixed_replay_seconds: float | None
    signature_comparison: str
    build: Callable[[], World]
    run_mismatched_deltat_reference: bool = False


@dataclass
class SensitivityRunResult:
    key: str
    name: str
    changed_attributes: tuple[str, ...]
    fixed_attributes: tuple[str, ...]
    signature_candidates: tuple[str, ...]
    uses_non_binding_capacity: bool
    deltat: float
    deltan: int
    reaction_time: float
    actual_travel_time_s: float
    reference_travel_time_s: float
    cumulative_waiting_time_s: float
    difference_from_case2_s: float
    actual_minus_reference_s: float
    mismatched_deltat_reference_travel_time_s: float | None
    limited_judgment: str


def _build_case6_series_world(
    case_name: str,
    vehicle_name: str,
    link_names: tuple[str, str, str],
    jam_densities: tuple[float, float, float],
    number_of_lanes: tuple[int, int, int],
    deltan: int,
    reaction_time: float,
    use_non_binding_capacity: bool,
) -> World:
    """Three links in series. One vehicle. No signal and no order control."""
    world = _make_world(
        case_name,
        deltan=deltan,
        reaction_time=reaction_time,
    )
    node_names = ("orig", "n1", "n2", "dest")
    for index, node_name in enumerate(node_names):
        world.addNode(node_name, float(index), 0.0, signal=[0])
    for index, link_name in enumerate(link_names):
        start_name = node_names[index]
        end_name = node_names[index + 1]
        if use_non_binding_capacity:
            world.addLink(
                link_name,
                start_name,
                end_name,
                length=CASE6_LINK_LENGTH_M,
                free_flow_speed=SPEED_60KPH_M_PER_S,
                jam_density=jam_densities[index],
                number_of_lanes=number_of_lanes[index],
                capacity_in=NON_BINDING_CAPACITY,
                capacity_out=NON_BINDING_CAPACITY,
            )
        else:
            world.addLink(
                link_name,
                start_name,
                end_name,
                length=CASE6_LINK_LENGTH_M,
                free_flow_speed=SPEED_60KPH_M_PER_S,
                jam_density=jam_densities[index],
                number_of_lanes=number_of_lanes[index],
            )
    _add_vehicle_with_route(
        world,
        vehicle_name,
        "orig",
        "dest",
        0,
        link_names,
    )
    return world


def build_case6a() -> World:
    return _build_case6_series_world(
        case_name="case6a",
        vehicle_name="veh_case6a",
        link_names=CASE6_CASE2_LINK_NAMES,
        jam_densities=CASE6A_JAM_DENSITIES,
        number_of_lanes=(1, 1, 1),
        deltan=1,
        reaction_time=1.0,
        use_non_binding_capacity=True,
    )


def build_case6b() -> World:
    return _build_case6_series_world(
        case_name="case6b",
        vehicle_name="veh_case6b",
        link_names=CASE6_CASE2_LINK_NAMES,
        jam_densities=(
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
        ),
        number_of_lanes=CASE6B_NUMBER_OF_LANES,
        deltan=1,
        reaction_time=1.0,
        use_non_binding_capacity=True,
    )


def build_case6c() -> World:
    return _build_case6_series_world(
        case_name="case6c",
        vehicle_name="veh_case6c",
        link_names=CASE6C_LINK_NAMES,
        jam_densities=(
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
        ),
        number_of_lanes=(1, 1, 1),
        deltan=1,
        reaction_time=1.0,
        use_non_binding_capacity=False,
    )


def build_case6d() -> World:
    return _build_case6_series_world(
        case_name="case6d",
        vehicle_name="veh_case6d",
        link_names=CASE6_CASE2_LINK_NAMES,
        jam_densities=(
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
        ),
        number_of_lanes=(1, 1, 1),
        deltan=CASE6D_DELTAN,
        reaction_time=CASE6D_REACTION_TIME_S,
        use_non_binding_capacity=True,
    )


def build_case6e1() -> World:
    return _build_case6_series_world(
        case_name="case6e1",
        vehicle_name="veh_case6e1",
        link_names=CASE6_CASE2_LINK_NAMES,
        jam_densities=(
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
        ),
        number_of_lanes=(1, 1, 1),
        deltan=CASE6E1_DELTAN,
        reaction_time=CASE6E1_REACTION_TIME_S,
        use_non_binding_capacity=True,
    )


def build_case6e2() -> World:
    return _build_case6_series_world(
        case_name="case6e2",
        vehicle_name="veh_case6e2",
        link_names=CASE6_CASE2_LINK_NAMES,
        jam_densities=(
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
            CASE2_DEFAULT_JAM_DENSITY,
        ),
        number_of_lanes=(1, 1, 1),
        deltan=CASE6E2_DELTAN,
        reaction_time=CASE6E2_REACTION_TIME_S,
        use_non_binding_capacity=True,
    )


_CASE6_COMMON_FIXED_ATTRIBUTES = (
    "link order: three links in series",
    f"length: {CASE6_LINK_LENGTH_M} m on every link",
    "free_flow_speed: 60/3.6 m/s on every link",
    "one Vehicle, departure timestep 0, route fixed",
    "no other vehicles, no congestion, no signal",
    "no order-control, no Node flow_capacity, no user_function",
)

_CASE6_MATCHED_ATTRIBUTES = (
    "link order",
    "length",
    "free_flow_speed",
    "jam_density",
    "number_of_lanes",
    "DELTAN",
    "REACTION_TIME",
    "DELTAT = REACTION_TIME * DELTAN",
)


SENSITIVITY_CASES: tuple[SensitivityCaseSpec, ...] = (
    SensitivityCaseSpec(
        key="6A",
        name="CASE 6A: jam density sensitivity",
        changed_attributes=(
            "jam_density only: "
            f"{CASE6A_JAM_DENSITIES[0]}, {CASE6A_JAM_DENSITIES[1]}, "
            f"{CASE6A_JAM_DENSITIES[2]} "
            f"(CASE 2 keeps the UXsim default {CASE2_DEFAULT_JAM_DENSITY})",
        ),
        fixed_attributes=_CASE6_COMMON_FIXED_ATTRIBUTES + (
            "number_of_lanes = 1 on every link",
            "DELTAN = 1",
            "REACTION_TIME = 1 s",
            "DELTAT = 1 s",
            "capacity_in and capacity_out = NON_BINDING_CAPACITY",
        ),
        signature_candidates=("jam_density",),
        uses_non_binding_capacity=True,
        matched_actual_reference_attributes=_CASE6_MATCHED_ATTRIBUTES,
        expected_link_names=CASE6_CASE2_LINK_NAMES,
        expected_deltan=1,
        expected_reaction_time_s=1.0,
        expects_fixed_replay_seconds=CASE2_REFERENCE_MINIMUM_TRIP_TIME_S,
        signature_comparison=(
            "Compare replay travel_time with CASE 2's 37 s while jam_density "
            "differs and capacity cannot bind one vehicle."
        ),
        build=build_case6a,
    ),
    SensitivityCaseSpec(
        key="6B",
        name="CASE 6B: number of lanes sensitivity",
        changed_attributes=(
            "number_of_lanes only: "
            f"{CASE6B_NUMBER_OF_LANES[0]}, {CASE6B_NUMBER_OF_LANES[1]}, "
            f"{CASE6B_NUMBER_OF_LANES[2]}",
        ),
        fixed_attributes=_CASE6_COMMON_FIXED_ATTRIBUTES + (
            f"jam_density = {CASE2_DEFAULT_JAM_DENSITY} on every link",
            "DELTAN = 1",
            "REACTION_TIME = 1 s",
            "DELTAT = 1 s",
            "capacity_in and capacity_out = NON_BINDING_CAPACITY",
            "one Vehicle, so no leader",
        ),
        signature_candidates=("number_of_lanes",),
        uses_non_binding_capacity=True,
        matched_actual_reference_attributes=_CASE6_MATCHED_ATTRIBUTES,
        expected_link_names=CASE6_CASE2_LINK_NAMES,
        expected_deltan=1,
        expected_reaction_time_s=1.0,
        expects_fixed_replay_seconds=CASE2_REFERENCE_MINIMUM_TRIP_TIME_S,
        signature_comparison=(
            "Compare replay travel_time with CASE 2's 37 s while lane counts "
            "differ, capacity cannot bind, and no leader exists."
        ),
        build=build_case6b,
    ),
    SensitivityCaseSpec(
        key="6C",
        name="CASE 6C: link name sensitivity",
        changed_attributes=(
            "link names only: "
            f"{CASE6C_LINK_NAMES[0]}, {CASE6C_LINK_NAMES[1]}, "
            f"{CASE6C_LINK_NAMES[2]} "
            "(CASE 2 names l1, l2, l3 are not used)",
        ),
        fixed_attributes=_CASE6_COMMON_FIXED_ATTRIBUTES + (
            f"jam_density = {CASE2_DEFAULT_JAM_DENSITY} on every link",
            "number_of_lanes = 1 on every link",
            "DELTAN = 1",
            "REACTION_TIME = 1 s",
            "DELTAT = 1 s",
            "capacity_in and capacity_out left as UXsim defaults, same as CASE 2",
        ),
        signature_candidates=("link name as a physical attribute", "link name as an audit identifier"),
        uses_non_binding_capacity=False,
        matched_actual_reference_attributes=_CASE6_MATCHED_ATTRIBUTES + (
            "UXsim default capacity_in and capacity_out",
        ),
        expected_link_names=CASE6C_LINK_NAMES,
        expected_deltan=1,
        expected_reaction_time_s=1.0,
        expects_fixed_replay_seconds=CASE2_REFERENCE_MINIMUM_TRIP_TIME_S,
        signature_comparison=(
            "Compare replay travel_time with CASE 2's 37 s when only the link "
            "names differ. Keep the physical conclusion separate from cache identity."
        ),
        build=build_case6c,
    ),
    SensitivityCaseSpec(
        key="6D",
        name="CASE 6D: DELTAT sensitivity",
        changed_attributes=(
            f"REACTION_TIME = {CASE6D_REACTION_TIME_S} s with DELTAN = {CASE6D_DELTAN}",
            "DELTAT becomes REACTION_TIME * DELTAN = 0.5 s (CASE 2 uses 1 s)",
        ),
        fixed_attributes=_CASE6_COMMON_FIXED_ATTRIBUTES + (
            f"jam_density = {CASE2_DEFAULT_JAM_DENSITY} on every link",
            "number_of_lanes = 1 on every link",
            "DELTAN stays 1",
            "capacity_in and capacity_out = NON_BINDING_CAPACITY on the actual "
            "World and on both reference Worlds",
        ),
        signature_candidates=("DELTAT", "REACTION_TIME when DELTAN is unchanged"),
        uses_non_binding_capacity=True,
        matched_actual_reference_attributes=_CASE6_MATCHED_ATTRIBUTES,
        expected_link_names=CASE6_CASE2_LINK_NAMES,
        expected_deltan=CASE6D_DELTAN,
        expected_reaction_time_s=CASE6D_REACTION_TIME_S,
        expects_fixed_replay_seconds=None,
        signature_comparison=(
            "Official CW_z uses a reference World with the same DELTAT. "
            "A second reference with DELTAT=1 is printed only to show the "
            "difference. That second travel_time is not CW_z."
        ),
        build=build_case6d,
        run_mismatched_deltat_reference=True,
    ),
    SensitivityCaseSpec(
        key="6E-1",
        name="CASE 6E-1: DELTAN change with REACTION_TIME fixed",
        changed_attributes=(
            f"DELTAN = {CASE6E1_DELTAN} (CASE 2 uses 1)",
            f"REACTION_TIME stays {CASE6E1_REACTION_TIME_S} s",
            "DELTAT therefore becomes 2 s",
        ),
        fixed_attributes=_CASE6_COMMON_FIXED_ATTRIBUTES + (
            f"jam_density = {CASE2_DEFAULT_JAM_DENSITY} on every link",
            "number_of_lanes = 1 on every link",
            "capacity_in and capacity_out = NON_BINDING_CAPACITY",
            "no order-control",
        ),
        signature_candidates=(
            "DELTAN together with the DELTAT change it causes when REACTION_TIME is fixed",
        ),
        uses_non_binding_capacity=True,
        matched_actual_reference_attributes=_CASE6_MATCHED_ATTRIBUTES,
        expected_link_names=CASE6_CASE2_LINK_NAMES,
        expected_deltan=CASE6E1_DELTAN,
        expected_reaction_time_s=CASE6E1_REACTION_TIME_S,
        expects_fixed_replay_seconds=None,
        signature_comparison=(
            "Do not read this travel_time as a pure DELTAN effect. "
            "REACTION_TIME is fixed, so DELTAT changes too. "
            "CASE 6E-2 holds DELTAT at 1 s."
        ),
        build=build_case6e1,
    ),
    SensitivityCaseSpec(
        key="6E-2",
        name="CASE 6E-2: DELTAN change with DELTAT held at 1 s",
        changed_attributes=(
            f"DELTAN = {CASE6E2_DELTAN}",
            f"REACTION_TIME = {CASE6E2_REACTION_TIME_S} s",
            "DELTAT = REACTION_TIME * DELTAN = 1 s, the same as CASE 2",
        ),
        fixed_attributes=_CASE6_COMMON_FIXED_ATTRIBUTES + (
            f"jam_density = {CASE2_DEFAULT_JAM_DENSITY} on every link",
            "number_of_lanes = 1 on every link",
            "DELTAT = 1 s",
            "capacity_in and capacity_out = NON_BINDING_CAPACITY",
            "no order-control",
        ),
        signature_candidates=("DELTAN when DELTAT is unchanged",),
        uses_non_binding_capacity=True,
        matched_actual_reference_attributes=_CASE6_MATCHED_ATTRIBUTES,
        expected_link_names=CASE6_CASE2_LINK_NAMES,
        expected_deltan=CASE6E2_DELTAN,
        expected_reaction_time_s=CASE6E2_REACTION_TIME_S,
        expects_fixed_replay_seconds=None,
        signature_comparison=(
            "Measure whether replay travel_time still equals CASE 2's 37 s "
            "when DELTAT is 1 s but DELTAN is not 1. Do not assume the answer."
        ),
        build=build_case6e2,
    ),
)


def _seconds_close(left: float, right: float) -> bool:
    return math.isclose(left, right, abs_tol=TIME_ABS_TOL)


def _ordered_specified_route_links(vehicle) -> list:
    if vehicle.specified_route is None:
        raise RuntimeError(
            f"Vehicle {vehicle.name} has no enforced route."
        )
    return list(vehicle.specified_route)


def _assert_no_waiting_controls(
    case_name: str,
    world: World,
    use_non_binding_capacity: bool,
) -> None:
    if len(world.VEHICLES) != 1:
        raise RuntimeError(
            f"{case_name}: expected 1 vehicle before simulation, "
            f"found {len(world.VEHICLES)}."
        )
    for node in world.NODES:
        if node.flow_capacity is not None:
            raise RuntimeError(
                f"{case_name}: node {node.name} has flow_capacity={node.flow_capacity}."
            )
        if node.user_function is not None:
            raise RuntimeError(
                f"{case_name}: node {node.name} has a user_function."
            )
        if node.order_control_type != "none" or node.order_control_eligible:
            raise RuntimeError(
                f"{case_name}: node {node.name} has order-control "
                f"type={node.order_control_type!r}, "
                f"eligible={node.order_control_eligible!r}."
            )
        if list(node.signal) != [0]:
            raise RuntimeError(
                f"{case_name}: node {node.name} signal={list(node.signal)!r}, "
                "expected [0]."
            )
    for link in world.LINKS:
        if link.user_function is not None:
            raise RuntimeError(
                f"{case_name}: link {link.name} has a user_function."
            )
        if use_non_binding_capacity:
            if not _seconds_close(float(link.capacity_in), NON_BINDING_CAPACITY):
                raise RuntimeError(
                    f"{case_name}: link {link.name} capacity_in={link.capacity_in}, "
                    f"expected {NON_BINDING_CAPACITY}."
                )
            if not _seconds_close(float(link.capacity_out), NON_BINDING_CAPACITY):
                raise RuntimeError(
                    f"{case_name}: link {link.name} capacity_out={link.capacity_out}, "
                    f"expected {NON_BINDING_CAPACITY}."
                )


def _assert_world_timing(
    case_name: str,
    world: World,
    expected_deltan: int,
    expected_reaction_time_s: float,
) -> None:
    expected_deltat = float(expected_reaction_time_s) * float(expected_deltan)
    if int(world.DELTAN) != expected_deltan:
        raise RuntimeError(
            f"{case_name}: DELTAN={world.DELTAN}, expected {expected_deltan}."
        )
    if not _seconds_close(float(world.REACTION_TIME), float(expected_reaction_time_s)):
        raise RuntimeError(
            f"{case_name}: REACTION_TIME={world.REACTION_TIME}, "
            f"expected {expected_reaction_time_s}."
        )
    if not _seconds_close(float(world.DELTAT), expected_deltat):
        raise RuntimeError(
            f"{case_name}: DELTAT={world.DELTAT}, "
            f"expected REACTION_TIME * DELTAN = {expected_deltat}."
        )


def _assert_same_route_physics(
    case_name: str,
    actual_links: Sequence,
    reference_links: Sequence,
) -> None:
    if len(actual_links) != len(reference_links):
        raise RuntimeError(
            f"{case_name}: actual route has {len(actual_links)} links, "
            f"reference route has {len(reference_links)} links."
        )
    for actual_link, reference_link in zip(actual_links, reference_links):
        if actual_link.name != reference_link.name:
            raise RuntimeError(
                f"{case_name}: link name {actual_link.name!r} != "
                f"reference {reference_link.name!r}."
            )
        if not _seconds_close(float(actual_link.length), float(reference_link.length)):
            raise RuntimeError(
                f"{case_name}: {actual_link.name} length "
                f"{actual_link.length} != reference {reference_link.length}."
            )
        if not _seconds_close(float(actual_link.u), float(reference_link.u)):
            raise RuntimeError(
                f"{case_name}: {actual_link.name} free_flow_speed "
                f"{actual_link.u} != reference {reference_link.u}."
            )
        if not _seconds_close(
            float(actual_link.jam_density), float(reference_link.jam_density)
        ):
            raise RuntimeError(
                f"{case_name}: {actual_link.name} jam_density "
                f"{actual_link.jam_density} != reference {reference_link.jam_density}."
            )
        if int(actual_link.number_of_lanes) != int(reference_link.number_of_lanes):
            raise RuntimeError(
                f"{case_name}: {actual_link.name} number_of_lanes "
                f"{actual_link.number_of_lanes} != "
                f"reference {reference_link.number_of_lanes}."
            )
        if not _seconds_close(
            float(actual_link.capacity_in), float(reference_link.capacity_in)
        ):
            raise RuntimeError(
                f"{case_name}: {actual_link.name} capacity_in "
                f"{actual_link.capacity_in} != reference {reference_link.capacity_in}."
            )
        if not _seconds_close(
            float(actual_link.capacity_out), float(reference_link.capacity_out)
        ):
            raise RuntimeError(
                f"{case_name}: {actual_link.name} capacity_out "
                f"{actual_link.capacity_out} != reference {reference_link.capacity_out}."
            )


def _sensitivity_context_lines(
    case_name: str,
    message: str,
    actual_world: World,
    actual_vehicle,
    reference_world: World | None,
    reference_travel_time_s: float | None,
) -> str:
    lines = [f"{case_name}: {message}"]
    lines.append(
        "  actual World: "
        f"DELTAT={actual_world.DELTAT} DELTAN={actual_world.DELTAN} "
        f"REACTION_TIME={actual_world.REACTION_TIME}"
    )
    if reference_world is not None:
        lines.append(
            "  reference World: "
            f"DELTAT={reference_world.DELTAT} DELTAN={reference_world.DELTAN} "
            f"REACTION_TIME={reference_world.REACTION_TIME}"
        )
    route_links = _ordered_specified_route_links(actual_vehicle)
    for link in route_links:
        lines.append(
            "  link "
            f"name={link.name} length={link.length} free_flow_speed={link.u} "
            f"jam_density={link.jam_density} "
            f"jam_density_per_lane={link.jam_density_per_lane} "
            f"number_of_lanes={link.number_of_lanes} "
            f"capacity_in={link.capacity_in} capacity_out={link.capacity_out}"
        )
    lines.append(f"  actual travel_time={float(actual_vehicle.travel_time)}")
    lines.append(f"  reference travel_time={reference_travel_time_s}")
    return "\n".join(lines)


def _print_attribute_list(title: str, items: Sequence[str]) -> None:
    print(title)
    for item in items:
        print(f"  - {item}")


def _print_route_columns(links: Sequence) -> None:
    names = [link.name for link in links]
    lengths = [float(link.length) for link in links]
    speeds = [float(link.u) for link in links]
    jam_densities = [float(link.jam_density) for link in links]
    jam_densities_per_lane = [link.jam_density_per_lane for link in links]
    lanes = [int(link.number_of_lanes) for link in links]
    capacity_ins = [float(link.capacity_in) for link in links]
    capacity_outs = [float(link.capacity_out) for link in links]
    print("Route:")
    print(f"  link names: {names}")
    print(f"  length: {lengths}")
    print(f"  free_flow_speed: {speeds}")
    print(f"  jam_density: {jam_densities}")
    print(f"  jam_density_per_lane: {jam_densities_per_lane}")
    print(f"  number_of_lanes: {lanes}")
    print(f"  capacity_in: {capacity_ins}")
    print(f"  capacity_out: {capacity_outs}")


def _print_world_timing(title: str, world: World) -> None:
    print(title)
    print(f"  DELTAT: {world.DELTAT}")
    print(f"  DELTAN: {world.DELTAN}")
    print(f"  REACTION_TIME: {world.REACTION_TIME}")


def _limited_judgment_for_result(
    spec: SensitivityCaseSpec,
    reference_travel_time_s: float,
    mismatched_deltat_reference_travel_time_s: float | None,
) -> str:
    matches_case2 = _seconds_close(
        reference_travel_time_s,
        CASE2_REFERENCE_MINIMUM_TRIP_TIME_S,
    )
    if spec.key == "6A":
        return (
            "Under one vehicle, no leader, and non-binding capacity, "
            "changing jam_density left replay travel_time at "
            f"{reference_travel_time_s} s. "
            "jam_density is not required for physical T_min,z in this setting. "
            "It can still change capacity, so the reference World fixes "
            "capacity_in and capacity_out instead of putting jam_density into "
            "the physical signature."
        )
    if spec.key == "6B":
        return (
            "Under one vehicle, no leader, and non-binding capacity, "
            "changing number_of_lanes left replay travel_time at "
            f"{reference_travel_time_s} s. "
            "number_of_lanes is not required for physical T_min,z in this setting. "
            "It can still change capacity and leader spacing, so the reference "
            "World fixes capacity and does not create a leader."
        )
    if spec.key == "6C":
        return (
            "Changing only the link names left replay travel_time at "
            f"{reference_travel_time_s} s. "
            "Link names are not required to compute physical T_min,z. "
            "They are still useful as an audit, debug, and cache-identity label. "
            "That label is not a physical attribute."
        )
    if spec.key == "6D":
        mismatch_text = "not run"
        if mismatched_deltat_reference_travel_time_s is not None:
            mismatch_text = f"{mismatched_deltat_reference_travel_time_s} s"
        case2_text = "changed from" if not matches_case2 else "stayed equal to"
        return (
            "Official CW_z uses the reference World with the same DELTAT as the "
            f"actual World. Replay travel_time is {reference_travel_time_s} s, "
            f"which {case2_text} CASE 2's {CASE2_REFERENCE_MINIMUM_TRIP_TIME_S} s. "
            "The DELTAT=1 reference, which is not used for CW_z, "
            f"returned {mismatch_text}. "
            "Actual and reference Worlds must carry the same DELTAT."
        )
    if spec.key == "6E-1":
        return (
            "REACTION_TIME stayed at CASE 2's value, so changing DELTAN also "
            f"changed DELTAT. Replay travel_time is {reference_travel_time_s} s. "
            "This comparison does not isolate DELTAN. Use CASE 6E-2 for that."
        )
    if spec.key == "6E-2":
        if matches_case2:
            return (
                "DELTAT stayed at 1 s. Replay travel_time stayed at "
                f"{CASE2_REFERENCE_MINIMUM_TRIP_TIME_S} s when DELTAN changed. "
                "In this single-vehicle, non-binding-capacity trial, DELTAN did "
                "not change physical T_min,z. "
                "Whether DELTAN must stay in a general signature is still open: "
                "DELTAN is the platoon size and can affect capacity checks and "
                "leader spacing, which this case does not exercise."
            )
        return (
            "DELTAT stayed at 1 s, but replay travel_time "
            f"{reference_travel_time_s} s differed from CASE 2's "
            f"{CASE2_REFERENCE_MINIMUM_TRIP_TIME_S} s. "
            "DELTAN changed physical T_min,z even without a DELTAT change. "
            "Treat DELTAN as required in the physical signature, separately from DELTAT."
        )
    raise RuntimeError(f"No judgment text for sensitivity case {spec.key}.")


def _validate_sensitivity_case(spec: SensitivityCaseSpec) -> SensitivityRunResult:
    world = spec.build()
    _assert_no_waiting_controls(spec.name, world, spec.uses_non_binding_capacity)
    _assert_world_timing(
        spec.name,
        world,
        spec.expected_deltan,
        spec.expected_reaction_time_s,
    )
    actual_vehicle_before_run = next(iter(world.VEHICLES.values()))
    actual_route_links = _ordered_specified_route_links(actual_vehicle_before_run)
    if spec.key == "6C":
        for link in actual_route_links:
            if link.name in CASE6_CASE2_LINK_NAMES:
                raise RuntimeError(
                    f"{spec.name}: link name {link.name!r} is a CASE 2 name. "
                    "CASE 6C must rename every link."
                )

    try:
        _run_to_vehicle_end(world)
    except RuntimeError as error:
        raise RuntimeError(
            f"{spec.name}: actual World did not complete. {error}"
        ) from error

    actual_vehicle = next(iter(world.VEHICLES.values()))
    route_specs = _route_link_specs(actual_vehicle)
    traveled_names = [spec_row.name for spec_row in route_specs]
    if traveled_names != list(spec.expected_link_names):
        raise RuntimeError(
            _sensitivity_context_lines(
                spec.name,
                "traveled link names differ from the case definition",
                world,
                actual_vehicle,
                None,
                None,
            )
            + f"\n  traveled={traveled_names!r}\n  expected={list(spec.expected_link_names)!r}"
        )

    if spec.uses_non_binding_capacity:
        reference_capacity_in: float | None = NON_BINDING_CAPACITY
        reference_capacity_out: float | None = NON_BINDING_CAPACITY
    else:
        reference_capacity_in = None
        reference_capacity_out = None

    try:
        reference_travel_time_s, reference_vehicle, reference_world = (
            _run_reference_minimum_trip_time(
                route_specs,
                deltan=int(world.DELTAN),
                reaction_time=float(world.REACTION_TIME),
                capacity_in=reference_capacity_in,
                capacity_out=reference_capacity_out,
            )
        )
    except RuntimeError as error:
        raise RuntimeError(
            _sensitivity_context_lines(
                spec.name,
                "reference replay did not complete",
                world,
                actual_vehicle,
                None,
                None,
            )
            + f"\n  cause: {error}"
        ) from error

    _assert_world_timing(
        spec.name + " reference",
        reference_world,
        spec.expected_deltan,
        spec.expected_reaction_time_s,
    )
    _assert_same_route_physics(
        spec.name,
        _ordered_specified_route_links(actual_vehicle),
        _ordered_specified_route_links(reference_vehicle),
    )
    if not _seconds_close(float(world.DELTAT), float(reference_world.DELTAT)):
        raise RuntimeError(
            _sensitivity_context_lines(
                spec.name,
                "actual and reference DELTAT differ",
                world,
                actual_vehicle,
                reference_world,
                reference_travel_time_s,
            )
        )
    if int(world.DELTAN) != int(reference_world.DELTAN):
        raise RuntimeError(
            _sensitivity_context_lines(
                spec.name,
                "actual and reference DELTAN differ",
                world,
                actual_vehicle,
                reference_world,
                reference_travel_time_s,
            )
        )

    actual_travel_time_s = float(actual_vehicle.travel_time)
    cumulative_waiting_time_s = actual_travel_time_s - float(reference_travel_time_s)
    difference_from_case2_s = (
        float(reference_travel_time_s) - CASE2_REFERENCE_MINIMUM_TRIP_TIME_S
    )
    actual_minus_reference_s = cumulative_waiting_time_s

    mismatched_travel_time_s: float | None = None
    mismatched_world = None
    if spec.run_mismatched_deltat_reference:
        try:
            mismatched_travel_time_s, _mismatched_vehicle, mismatched_world = (
                _run_reference_minimum_trip_time(
                    route_specs,
                    deltan=1,
                    reaction_time=1.0,
                    capacity_in=reference_capacity_in,
                    capacity_out=reference_capacity_out,
                )
            )
        except RuntimeError as error:
            raise RuntimeError(
                _sensitivity_context_lines(
                    spec.name,
                    "DELTAT-mismatched reference did not complete",
                    world,
                    actual_vehicle,
                    reference_world,
                    reference_travel_time_s,
                )
                + f"\n  cause: {error}"
            ) from error
        if _seconds_close(float(mismatched_world.DELTAT), float(world.DELTAT)):
            raise RuntimeError(
                _sensitivity_context_lines(
                    spec.name,
                    "the diagnostic reference used the same DELTAT as the actual World",
                    world,
                    actual_vehicle,
                    mismatched_world,
                    mismatched_travel_time_s,
                )
            )

    _print_case_header(spec.name)
    _print_attribute_list("Changed attributes:", spec.changed_attributes)
    _print_attribute_list("Fixed attributes:", spec.fixed_attributes)
    _print_attribute_list(
        "Signature candidates checked by this case:",
        spec.signature_candidates,
    )
    print(f"Comparison: {spec.signature_comparison}")
    _print_world_timing("Actual World:", world)
    _print_world_timing("Reference World:", reference_world)
    _print_route_columns(_ordered_specified_route_links(actual_vehicle))
    print("Results:")
    print(f"  actual travel_time: {actual_travel_time_s}")
    print(f"  reference replay travel_time: {reference_travel_time_s}")
    print(f"  CW_z: {cumulative_waiting_time_s}")
    print(
        "  difference from CASE 2 replay 37 s: "
        f"{difference_from_case2_s}"
    )
    print(f"  actual minus reference: {actual_minus_reference_s}")
    if mismatched_world is not None and mismatched_travel_time_s is not None:
        print("DELTAT-mismatched reference (not used for CW_z):")
        _print_world_timing("  mismatched reference World:", mismatched_world)
        print(f"  mismatched reference travel_time: {mismatched_travel_time_s}")
        print(
            "  matched reference minus mismatched reference: "
            f"{float(reference_travel_time_s) - float(mismatched_travel_time_s)}"
        )
        print(
            "  note: CASE 2's 37 s used UXsim default capacity. "
            "This diagnostic reference uses the same non-binding capacity as CASE 6D."
        )
    if spec.key == "6E-2":
        print(
            "  note: equality with CASE 2's 37 s is measured, not assumed. "
            "CASE 6E-2 uses NON_BINDING_CAPACITY so the DELTAN=2 platoon is not "
            "held by derived link capacity. CASE 2 itself used UXsim's default capacity."
        )

    if not _seconds_close(actual_travel_time_s, float(reference_travel_time_s)):
        raise RuntimeError(
            _sensitivity_context_lines(
                spec.name,
                "actual travel_time != reference replay travel_time",
                world,
                actual_vehicle,
                reference_world,
                reference_travel_time_s,
            )
        )
    if not _seconds_close(cumulative_waiting_time_s, 0.0):
        raise RuntimeError(
            _sensitivity_context_lines(
                spec.name,
                "CW_z != 0",
                world,
                actual_vehicle,
                reference_world,
                reference_travel_time_s,
            )
        )
    if spec.expects_fixed_replay_seconds is not None:
        if not _seconds_close(
            float(reference_travel_time_s),
            spec.expects_fixed_replay_seconds,
        ):
            raise RuntimeError(
                _sensitivity_context_lines(
                    spec.name,
                    "reference replay travel_time != the fixed expected seconds",
                    world,
                    actual_vehicle,
                    reference_world,
                    reference_travel_time_s,
                )
                + f"\n  expected_replay_s={spec.expects_fixed_replay_seconds}"
            )

    judgment = _limited_judgment_for_result(
        spec,
        float(reference_travel_time_s),
        mismatched_travel_time_s,
    )
    print("Limited judgment:")
    print(f"  {judgment}")
    print(f"PASS {spec.name}")

    del mismatched_world
    return SensitivityRunResult(
        key=spec.key,
        name=spec.name,
        changed_attributes=spec.changed_attributes,
        fixed_attributes=spec.fixed_attributes,
        signature_candidates=spec.signature_candidates,
        uses_non_binding_capacity=spec.uses_non_binding_capacity,
        deltat=float(world.DELTAT),
        deltan=int(world.DELTAN),
        reaction_time=float(world.REACTION_TIME),
        actual_travel_time_s=actual_travel_time_s,
        reference_travel_time_s=float(reference_travel_time_s),
        cumulative_waiting_time_s=cumulative_waiting_time_s,
        difference_from_case2_s=difference_from_case2_s,
        actual_minus_reference_s=actual_minus_reference_s,
        mismatched_deltat_reference_travel_time_s=mismatched_travel_time_s,
        limited_judgment=judgment,
    )


def _print_signature_sensitivity_summary(
    results: Sequence[SensitivityRunResult],
) -> None:
    by_key = {result.key: result for result in results}
    result_6d = by_key["6D"]
    result_6e2 = by_key["6E-2"]
    deltat_changed_vs_case2 = not _seconds_close(
        result_6d.reference_travel_time_s,
        CASE2_REFERENCE_MINIMUM_TRIP_TIME_S,
    )
    mismatch_differs = False
    if result_6d.mismatched_deltat_reference_travel_time_s is not None:
        mismatch_differs = not _seconds_close(
            result_6d.reference_travel_time_s,
            result_6d.mismatched_deltat_reference_travel_time_s,
        )
    deltan_changes_tmin_at_same_deltat = not _seconds_close(
        result_6e2.reference_travel_time_s,
        CASE2_REFERENCE_MINIMUM_TRIP_TIME_S,
    )

    print("")
    print("=" * 72)
    print("Route signature sensitivity summary")
    print("=" * 72)
    print("This script does not implement a production cache key.")
    print("The classes below restate only the measurements in this run.")
    print("")
    print("1. Attributes confirmed necessary for physical T_min,z")
    print(
        "  - link order, length, and free_flow_speed are the replay input. "
        "CASE 6 does not vary them; CASE 1-5 already required the same route."
    )
    if deltat_changed_vs_case2 or mismatch_differs:
        print(
            "  - DELTAT, through the World settings that reproduce it. "
            f"CASE 6D replay={result_6d.reference_travel_time_s} s, "
            f"DELTAT=1 diagnostic reference="
            f"{result_6d.mismatched_deltat_reference_travel_time_s} s."
        )
    else:
        print(
            "  - DELTAT must still be identical on the actual and reference Worlds. "
            "This run did not show a numeric travel_time change, so a broader "
            "claim that DELTAT always changes T_min,z is not confirmed here."
        )
    if deltan_changes_tmin_at_same_deltat:
        print(
            "  - DELTAN. CASE 6E-2 kept DELTAT at 1 s and replay travel_time was "
            f"{result_6e2.reference_travel_time_s} s, not "
            f"{CASE2_REFERENCE_MINIMUM_TRIP_TIME_S} s."
        )
    print("")
    print("2. Attributes that did not change physical T_min,z in this trial")
    print(
        "  - jam_density, when capacity_in and capacity_out cannot bind one "
        f"vehicle. CASE 6A replay={by_key['6A'].reference_travel_time_s} s."
    )
    print(
        "  - number_of_lanes, when capacity cannot bind and there is no leader. "
        f"CASE 6B replay={by_key['6B'].reference_travel_time_s} s."
    )
    print(
        "  - link name, as a physical input. "
        f"CASE 6C replay={by_key['6C'].reference_travel_time_s} s."
    )
    if not deltan_changes_tmin_at_same_deltat:
        print(
            "  - DELTAN, in this single-vehicle non-binding trial with DELTAT held "
            f"at 1 s. CASE 6E-2 replay={result_6e2.reference_travel_time_s} s."
        )
    print("")
    print("3. Attributes fixed on the reference World to exclude capacity waiting")
    print("  - capacity_in = NON_BINDING_CAPACITY")
    print("  - capacity_out = NON_BINDING_CAPACITY")
    print("  - no signal, no order-control, no Node flow_capacity")
    print("  - no Node or Link user_function")
    print("  - one Vehicle and an enforced route")
    print("  - CASE 6C does not override capacity. It keeps the CASE 2 default.")
    print("")
    print("4. Not needed for physical T_min,z, but useful for audit or cache identity")
    print(
        "  - link names. CASE 6C shows they do not set the travel_time. "
        "Keeping them in an audit or cache key can still prevent collisions "
        "and make a route readable. Do not treat that label as a physical input."
    )
    print("")
    print("5. Still unresolved")
    print("  - the final production cache key is not chosen by this script")
    print(
        "  - jam_density and number_of_lanes when a leader exists or capacity binds"
    )
    if not deltan_changes_tmin_at_same_deltat:
        print(
            "  - DELTAN outside this single-vehicle non-binding setting. "
            "CASE 6E-1 cannot separate DELTAN from the DELTAT change."
        )
    if not (deltat_changed_vs_case2 or mismatch_differs):
        print(
            "  - whether every route's T_min,z changes when DELTAT changes. "
            "This network did not show a numeric difference."
        )
    print("")
    print("Per-case judgments:")
    for result in results:
        print(f"  {result.name}")
        print(f"    {result.limited_judgment}")


@dataclass(frozen=True)
class PhysicalLinkView:
    """Plain link numbers for CASE 7. Not a UXsim Link."""

    name: str
    length: float
    u: float


@dataclass(frozen=True)
class IdentityCaseNote:
    name: str
    comparison: str
    expected_relation: str


def _build_physical_route_key(deltat, route_links) -> tuple:
    """Hash-ready physical key. Uses link.u, not link.free_flow_speed.

    Floats are not rounded and are not turned into strings.
    Link names are not included. Link order is kept.
    """
    pairs = []
    for link in route_links:
        length = float(link.length)
        speed_u = float(link.u)
        pairs.append((length, speed_u))
    return (float(deltat), tuple(pairs))


def _build_route_audit_identity(route_links) -> tuple[str, ...]:
    """Link-name tuple for audit display. Not part of the physical key."""
    names = []
    for link in route_links:
        names.append(str(link.name))
    return tuple(names)


def _format_physical_route_key_for_display(key) -> str:
    """Human-readable text. Do not use this string as a dict key."""
    deltat = key[0]
    pairs = key[1]
    parts = [f"DELTAT={deltat!r}"]
    link_index = 1
    for length, speed_u in pairs:
        parts.append(
            f"link{link_index}(length={length!r}, u={speed_u!r})"
        )
        link_index += 1
    return " | ".join(parts)


def _raise_identity_failure(case_name: str, message: str, **details) -> None:
    lines = [f"{case_name}: {message}"]
    for name, value in details.items():
        lines.append(f"  {name} = {value!r}")
    raise RuntimeError("\n".join(lines))


def _print_identity_case(
    case_name: str,
    comparison: str,
    key_left,
    key_right,
    audit_left,
    audit_right,
    dict_entry_count: int,
    conclusion: str,
) -> None:
    same_key = key_left == key_right
    same_hash = hash(key_left) == hash(key_right)
    _print_case_header(case_name)
    print(f"Comparison: {comparison}")
    print("Physical key (display only; the tuple itself is the dict key):")
    print(f"  left:  {_format_physical_route_key_for_display(key_left)}")
    print(f"  right: {_format_physical_route_key_for_display(key_right)}")
    print(f"Audit identity left:  {audit_left}")
    print(f"Audit identity right: {audit_right}")
    if same_key:
        print("  physical keys: same")
    else:
        print("  physical keys: different")
    if same_hash:
        print("  hashes: same")
    else:
        print("  hashes: different")
    print(f"  dict entry count: {dict_entry_count}")
    print(f"Limited conclusion: {conclusion}")


def _case7_equal_route(names: tuple[str, str, str]) -> list[PhysicalLinkView]:
    speed = 60.0 / 3.6
    first = PhysicalLinkView(names[0], 200.0, speed)
    second = PhysicalLinkView(names[1], 200.0, speed)
    third = PhysicalLinkView(names[2], 200.0, speed)
    return [first, second, third]


def _validate_case7a() -> None:
    case_name = "CASE 7A: same numeric values"
    route_left = _case7_equal_route(("l1", "l2", "l3"))
    route_right = _case7_equal_route(("l1", "l2", "l3"))
    key_left = _build_physical_route_key(1.0, route_left)
    key_right = _build_physical_route_key(1.0, route_right)
    audit_left = _build_route_audit_identity(route_left)
    audit_right = _build_route_audit_identity(route_right)
    memory = {}
    memory[key_left] = "shared-replay"
    entry_count = len(memory)
    retrieved = None
    if key_right in memory:
        retrieved = memory[key_right]
    _print_identity_case(
        case_name,
        "two separately built routes with DELTAT=1 and three 200 m, 60/3.6 links",
        key_left,
        key_right,
        audit_left,
        audit_right,
        entry_count,
        "The same stored numbers can share one in-memory dict entry.",
    )
    if key_left != key_right or hash(key_left) != hash(key_right):
        _raise_identity_failure(
            case_name,
            "separately built equal routes did not produce the same key",
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            dict_entry_count=entry_count,
        )
    if entry_count != 1 or retrieved != "shared-replay":
        _raise_identity_failure(
            case_name,
            "the second key did not read the value stored by the first key",
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            retrieved=retrieved,
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


def _validate_case7b() -> None:
    case_name = "CASE 7B: link names only"
    route_left = _case7_equal_route(("l1", "l2", "l3"))
    route_right = _case7_equal_route(("link_alpha", "link_beta", "link_gamma"))
    key_left = _build_physical_route_key(1.0, route_left)
    key_right = _build_physical_route_key(1.0, route_right)
    audit_left = _build_route_audit_identity(route_left)
    audit_right = _build_route_audit_identity(route_right)
    memory = {}
    memory[key_left] = "shared-replay"
    entry_count = len(memory)
    _print_identity_case(
        case_name,
        "same length and u, names l1/l2/l3 versus link_alpha/link_beta/link_gamma",
        key_left,
        key_right,
        audit_left,
        audit_right,
        entry_count,
        "Link names are not required to share a physical result. "
        "The name tuple can still show which route was displayed.",
    )
    if key_left != key_right:
        _raise_identity_failure(
            case_name,
            "physical keys differed when only link names differed",
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            audit_left=audit_left,
            audit_right=audit_right,
            dict_entry_count=entry_count,
        )
    if audit_left == audit_right:
        _raise_identity_failure(
            case_name,
            "audit identities were the same after renaming every link",
            audit_left=audit_left,
            audit_right=audit_right,
            key_left=key_left,
            key_right=key_right,
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


def _validate_case7c() -> None:
    case_name = "CASE 7C: link order"
    route_left = [
        PhysicalLinkView("l1", 120.0, 10.0),
        PhysicalLinkView("l2", 200.0, 20.0),
        PhysicalLinkView("l3", 300.0, 15.0),
    ]
    route_right = [
        PhysicalLinkView("l2", 200.0, 20.0),
        PhysicalLinkView("l1", 120.0, 10.0),
        PhysicalLinkView("l3", 300.0, 15.0),
    ]
    key_left = _build_physical_route_key(1.0, route_left)
    key_right = _build_physical_route_key(1.0, route_right)
    memory = {}
    memory[key_left] = "order-left"
    memory[key_right] = "order-right"
    entry_count = len(memory)
    _print_identity_case(
        case_name,
        "(120, 10), (200, 20), (300, 15) versus the first two links swapped",
        key_left,
        key_right,
        _build_route_audit_identity(route_left),
        _build_route_audit_identity(route_right),
        entry_count,
        "The same link conditions in a different order are different routes.",
    )
    if key_left == key_right or entry_count != 2:
        _raise_identity_failure(
            case_name,
            "reordered links did not produce separate dict entries",
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


def _validate_case7d() -> None:
    case_name = "CASE 7D: DELTAT"
    route = _case7_equal_route(("l1", "l2", "l3"))
    key_left = _build_physical_route_key(1.0, route)
    key_right = _build_physical_route_key(0.5, route)
    memory = {}
    memory[key_left] = "deltat-1"
    memory[key_right] = "deltat-0.5"
    entry_count = len(memory)
    _print_identity_case(
        case_name,
        "same links with DELTAT 1.0 versus DELTAT 0.5",
        key_left,
        key_right,
        _build_route_audit_identity(route),
        _build_route_audit_identity(route),
        entry_count,
        "A different DELTAT must not share the stored replay result.",
    )
    if key_left == key_right or entry_count != 2:
        _raise_identity_failure(
            case_name,
            "different DELTAT values produced the same dict entry",
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


def _validate_case7e() -> None:
    case_name = "CASE 7E: tiny length difference"
    length_left = 200.0
    length_right = 200.00000000000003
    route_left = [PhysicalLinkView("l1", length_left, 10.0)]
    route_right = [PhysicalLinkView("l1", length_right, 10.0)]
    key_left = _build_physical_route_key(1.0, route_left)
    key_right = _build_physical_route_key(1.0, route_right)
    memory = {}
    memory[key_left] = "length-left"
    memory[key_right] = "length-right"
    entry_count = len(memory)
    rounded_left = round(length_left, 10)
    rounded_right = round(length_right, 10)
    _print_identity_case(
        case_name,
        "length 200.0 versus 200.00000000000003, other values unchanged",
        key_left,
        key_right,
        _build_route_audit_identity(route_left),
        _build_route_audit_identity(route_right),
        entry_count,
        "The formal key keeps the stored floats and does not round them.",
    )
    print(f"  stored length left:  {length_left!r}")
    print(f"  stored length right: {length_right!r}")
    print(
        "  diagnostic only, not a formal key: "
        f"round(length, 10) -> {rounded_left!r} and {rounded_right!r}"
    )
    if rounded_left == rounded_right and length_left != length_right:
        print(
            "  diagnostic: rounding to 10 decimal places would collapse "
            "these different stored lengths."
        )
    if length_left == length_right or key_left == key_right or entry_count != 2:
        _raise_identity_failure(
            case_name,
            "the unrounded physical key collapsed a tiny length difference",
            length_left=length_left,
            length_right=length_right,
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


def _validate_case7f() -> None:
    case_name = "CASE 7F: tiny speed difference"
    speed_left = 60.0 / 3.6
    speed_right = (60.0 / 3.6) + 1e-15
    route_left = [PhysicalLinkView("l1", 200.0, speed_left)]
    route_right = [PhysicalLinkView("l1", 200.0, speed_right)]
    key_left = _build_physical_route_key(1.0, route_left)
    key_right = _build_physical_route_key(1.0, route_right)
    memory = {}
    memory[key_left] = "speed-left"
    memory[key_right] = "speed-right"
    entry_count = len(memory)
    stored_values_differ = speed_left != speed_right
    _print_identity_case(
        case_name,
        "u = 60/3.6 versus (60/3.6)+1e-15, judged by stored float equality",
        key_left,
        key_right,
        _build_route_audit_identity(route_left),
        _build_route_audit_identity(route_right),
        entry_count,
        "The formal key follows the float Python actually stored. "
        "A decimal spelling is not used as the decision.",
    )
    print(f"  stored u left:  {speed_left!r}")
    print(f"  stored u right: {speed_right!r}")
    if stored_values_differ:
        print("  stored floats: different, so the formal keys must differ")
        conclusion_ok = key_left != key_right and entry_count == 2
    else:
        print(
            "  stored floats: same. Python absorbed 1e-15 into the same float. "
            "This case does not claim they are different keys."
        )
        conclusion_ok = key_left == key_right and entry_count == 1
    if not conclusion_ok:
        _raise_identity_failure(
            case_name,
            "formal key did not follow stored float equality",
            speed_left=speed_left,
            speed_right=speed_right,
            stored_values_differ=stored_values_differ,
            key_left=key_left,
            key_right=key_right,
            hash_left=hash(key_left),
            hash_right=hash(key_right),
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


def _validate_case7g() -> None:
    case_name = "CASE 7G: physical key uses link.u"
    world = _make_world("case7g")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("dest", 1.0, 0.0, signal=[0])
    world.addLink(
        "l1",
        "orig",
        "dest",
        length=200.0,
        free_flow_speed=SPEED_60KPH_M_PER_S,
        number_of_lanes=1,
    )
    link = world.LINKS[0]
    speed_before = float(link.u)
    free_flow_before = float(link.free_flow_speed)
    if free_flow_before != speed_before:
        _raise_identity_failure(
            case_name,
            "initial free_flow_speed and u differ",
            free_flow_speed=free_flow_before,
            u=speed_before,
        )
    key_before = _build_physical_route_key(world.DELTAT, [link])
    manual_before = (float(world.DELTAT), ((float(link.length), float(link.u)),))
    new_speed = 10.0
    link.change_free_flow_speed(new_speed)
    speed_after = float(link.u)
    free_flow_after = float(link.free_flow_speed)
    key_after = _build_physical_route_key(world.DELTAT, [link])
    manual_after = (float(world.DELTAT), ((float(link.length), float(link.u)),))
    memory = {}
    memory[key_before] = "before"
    memory[key_after] = "after"
    entry_count = len(memory)
    _print_identity_case(
        case_name,
        "one validation Link before and after change_free_flow_speed(10.0); no simulation",
        key_before,
        key_after,
        _build_route_audit_identity([link]),
        _build_route_audit_identity([link]),
        entry_count,
        "The physical key reads link.u. Both attributes move together, "
        "and the key changes when that stored speed changes.",
    )
    print(f"  before: free_flow_speed={free_flow_before!r} u={speed_before!r}")
    print(f"  after:  free_flow_speed={free_flow_after!r} u={speed_after!r}")
    if free_flow_after != new_speed or speed_after != new_speed:
        _raise_identity_failure(
            case_name,
            "change_free_flow_speed did not update both attributes to the new value",
            free_flow_speed=free_flow_after,
            u=speed_after,
            expected=new_speed,
            key_before=key_before,
            key_after=key_after,
            dict_entry_count=entry_count,
        )
    if key_before != manual_before or key_after != manual_after:
        _raise_identity_failure(
            case_name,
            "physical key was not built from DELTAT, length, and link.u",
            key_before=key_before,
            manual_before=manual_before,
            key_after=key_after,
            manual_after=manual_after,
            dict_entry_count=entry_count,
        )
    if key_before == key_after or entry_count != 2:
        _raise_identity_failure(
            case_name,
            "speed change did not produce a different physical key",
            key_before=key_before,
            key_after=key_after,
            hash_before=hash(key_before),
            hash_after=hash(key_after),
            dict_entry_count=entry_count,
        )
    print(f"PASS {case_name}")


IDENTITY_CASE_NOTES: tuple[IdentityCaseNote, ...] = (
    IdentityCaseNote(
        name="CASE 7A: same numeric values",
        comparison="Two separately built copies of DELTAT=1 and three equal links.",
        expected_relation="same physical key, same hash, one dict entry, second key reads the stored value",
    ),
    IdentityCaseNote(
        name="CASE 7B: link names only",
        comparison="Same length and u. Names l1/l2/l3 versus link_alpha/link_beta/link_gamma.",
        expected_relation="same physical key, different audit identity",
    ),
    IdentityCaseNote(
        name="CASE 7C: link order",
        comparison="(120, 10), (200, 20), (300, 15) versus the first two pairs swapped.",
        expected_relation="different physical keys and two dict entries",
    ),
    IdentityCaseNote(
        name="CASE 7D: DELTAT",
        comparison="Same links with DELTAT 1.0 versus 0.5.",
        expected_relation="different physical keys and two dict entries",
    ),
    IdentityCaseNote(
        name="CASE 7E: tiny length difference",
        comparison="length 200.0 versus 200.00000000000003.",
        expected_relation="unrounded keys differ; fixed-decimal rounding is diagnostic only",
    ),
    IdentityCaseNote(
        name="CASE 7F: tiny speed difference",
        comparison="u = 60/3.6 versus (60/3.6)+1e-15.",
        expected_relation="follow stored float equality; do not decide from decimal spelling",
    ),
    IdentityCaseNote(
        name="CASE 7G: physical key uses link.u",
        comparison="Validation Link before and after change_free_flow_speed. No simulation.",
        expected_relation="key uses link.u and changes when that speed changes",
    ),
)


def _print_identity_summary() -> None:
    print("")
    print("=" * 72)
    print("Physical route identity summary")
    print("=" * 72)
    print("  - Do not round numeric values.")
    print("  - Include DELTAT.")
    print("  - Keep link order.")
    print("  - Use length and link.u.")
    print("  - Keep link names out of the physical key.")
    print("  - The key is a candidate for an in-memory dict inside one evaluation run.")
    print("  - A persistent storage format is not chosen.")
    print("  - Production implementation has not started.")


def _run_identity_cases() -> None:
    _validate_case7a()
    _validate_case7b()
    _validate_case7c()
    _validate_case7d()
    _validate_case7e()
    _validate_case7f()
    _validate_case7g()
    _print_identity_summary()


# CASE 8 is verification-only. It keeps one fresh in-memory state per
# evaluation. It does not publish a production module and it does not keep a
# module-level cache.
CASE8_METHOD_NAMES = (
    "signalized_uxsim",
    "fcfs",
    "batch",
    "tvt_mp",
)
CASE8_PARTICIPATION_CATEGORIES = (
    "participating",
    "nonparticipating",
    "unspecified",
)
# Plain multiplier for the CASE 8 weighted product. Not a yen-per-second
# contract and not the formal ACWWT unit.
CASE8_VERIFICATION_TRUE_VOT = 2.0
CASE8_REFERENCE_WORLD_NAME = "case8_reference_replay"
CASE8_REFERENCE_JAM_DENSITY = 0.2


@dataclass
class Case8ReferenceReplayResult:
    """Numbers from one reference replay. The World itself is not stored.

    minimum_trip_time_s and reference_vehicle_travel_time are seconds.
    analytical_free_flow_time_s is a diagnostic sum of length/u, in seconds.
    It is not the formal T_min,z.
    """

    physical_route_key: tuple
    minimum_trip_time_s: float
    analytical_free_flow_time_s: float
    reference_route_link_count: int
    reference_world_deltat: float
    reference_world_deltan: int
    reference_vehicle_arrival_time: float
    reference_vehicle_travel_time: float
    validation_passed: bool


@dataclass
class Case8VehicleRecord:
    """One finished vehicle. true_vot is the CASE 8 verification coefficient.

    actual_travel_time_s, minimum_trip_time_s, and cumulative_waiting_time_s
    are seconds. weighted_cumulative_waiting_time is true_vot times CW_z.
    """

    vehicle_name: str
    method_name: str
    physical_route_key: tuple
    route_audit_identity: tuple
    actual_travel_time_s: float
    minimum_trip_time_s: float
    cumulative_waiting_time_s: float
    true_vot: float
    weighted_cumulative_waiting_time: float
    participation_category: str


@dataclass
class Case8EvaluationCounters:
    evaluated_vehicle_count: int = 0
    unique_physical_route_count: int = 0
    reference_replay_run_count: int = 0
    reference_reuse_count: int = 0
    unique_audit_identity_count: int = 0
    duplicate_audit_identity_observation_count: int = 0
    incomplete_vehicle_count: int = 0
    validation_failure_count: int = 0
    negative_cumulative_waiting_time_count: int = 0


@dataclass
class Case8EvaluationState:
    """Local state for one evaluation call. Create a new one every time."""

    real_deltat: float
    method_name: str
    reference_results_by_physical_key: dict
    audit_identities_by_physical_key: dict
    counters: Case8EvaluationCounters
    vehicle_records: list


@dataclass
class Case8EvaluationResult:
    method_name: str
    vehicle_records: list
    reference_results_by_physical_key: dict
    audit_identities_by_physical_key: dict
    counters: Case8EvaluationCounters
    average_cumulative_waiting_time_s: float
    average_weighted_cumulative_waiting_time: float


@dataclass(frozen=True)
class Case8CaseNote:
    name: str
    purpose: str
    expected_relation: str


def _case8_make_quiet_world(
    label: str,
    deltan: int = 1,
    reaction_time: float = 1.0,
    tmax_seconds: float = 600.0,
) -> World:
    """Actual CASE 8 world. No Analyzer is created until a later finalize."""
    return World(
        name=f"case8_{label}",
        deltan=deltan,
        reaction_time=reaction_time,
        tmax=tmax_seconds,
        random_seed=0,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        hard_deterministic_mode=True,
        vehicle_logging_timestep_interval=1,
    )


def _case8_add_route_chain(
    world: World,
    chain_name: str,
    link_names: Sequence[str],
    lengths: Sequence[float],
    speeds: Sequence[float],
    vehicle_name: str,
    row_y: float,
    departure_timestep: int = 0,
    capacity_in: float | None = None,
    link_user_function=None,
) -> None:
    """One serial chain and one vehicle. Nodes do not connect to other chains."""
    if not (len(link_names) == len(lengths) == len(speeds)):
        raise RuntimeError(
            f"CASE 8 chain {chain_name} was given unequal link columns."
        )
    if len(link_names) == 0:
        raise RuntimeError(f"CASE 8 chain {chain_name} has no links.")

    node_names = []
    node_count = len(link_names) + 1
    for index in range(node_count):
        node_name = f"{chain_name}_node_{index}"
        world.addNode(node_name, float(index), float(row_y), signal=[0])
        node_names.append(node_name)

    for index in range(len(link_names)):
        if capacity_in is None and link_user_function is None:
            world.addLink(
                link_names[index],
                node_names[index],
                node_names[index + 1],
                length=lengths[index],
                free_flow_speed=speeds[index],
                number_of_lanes=1,
            )
        elif link_user_function is None:
            world.addLink(
                link_names[index],
                node_names[index],
                node_names[index + 1],
                length=lengths[index],
                free_flow_speed=speeds[index],
                number_of_lanes=1,
                capacity_in=capacity_in,
            )
        else:
            world.addLink(
                link_names[index],
                node_names[index],
                node_names[index + 1],
                length=lengths[index],
                free_flow_speed=speeds[index],
                number_of_lanes=1,
                capacity_in=capacity_in,
                user_function=link_user_function,
            )

    _add_vehicle_with_route(
        world,
        vehicle_name,
        node_names[0],
        node_names[-1],
        departure_timestep,
        link_names,
    )


def _case8_record_travel_log_without_analyzer(vehicle, enforce_log: int = 0) -> None:
    """Verification substitute for Vehicle.record_log.

    The normal logger also writes into World.analyzer. CASE 8 worlds are
    finalized with create_analyzer=False, so this writer keeps the route log
    and does not touch an Analyzer.
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
            vehicle.log_t_link.append([vehicle.W.T * vehicle.W.DELTAT, vehicle.link])
        elif vehicle.state == "end":
            vehicle.log_t_link.append([vehicle.W.T * vehicle.W.DELTAT, "end"])
        vehicle.link_old = vehicle.link


def _case8_attach_log_without_analyzer(world: World) -> None:
    for vehicle in world.VEHICLES.values():
        def record_for_this_vehicle(enforce_log=0, bound_vehicle=vehicle):
            _case8_record_travel_log_without_analyzer(
                bound_vehicle,
                enforce_log,
            )

        vehicle.record_log = record_for_this_vehicle


def _case8_all_vehicles_finished(world: World) -> bool:
    if len(world.VEHICLES) == 0:
        return False
    for vehicle in world.VEHICLES.values():
        if vehicle.state != "end":
            return False
    return True


def _case8_execute_without_analyzer(world: World) -> None:
    """Run a CASE 8 world without creating an Analyzer or an output directory.

    UXsim's exec_simulation writes progress and vehicle samples to the
    Analyzer, and Analyzer creates out{world name}. This loop keeps the same
    link, node, and vehicle steps and skips those Analyzer calls.
    """
    if world.finalized == 0:
        world.finalize_scenario(create_analyzer=False)
    if hasattr(world, "analyzer"):
        raise RuntimeError(
            "CASE 8 created an Analyzer. "
            f"world={world.name!r}."
        )
    _case8_attach_log_without_analyzer(world)

    for world.T in range(0, world.TSIZE):
        for link in world.LINKS:
            link.update()
        for node in world.NODES:
            node.generate()
            node.update()
        for node in world.NODES:
            node.transfer()
        for vehicle in world.VEHICLES_RUNNING.values():
            vehicle.carfollow()
        living_names = list(world.VEHICLES_LIVING.keys())
        for vehicle_name in living_names:
            world.VEHICLES_LIVING[vehicle_name].update()
        if world.T % world.DELTAT_ROUTE == 0:
            world.ROUTECHOICE.route_search_all(noise=world.DUO_NOISE)
            world.ROUTECHOICE.homogeneous_DUO_update()
            for vehicle in world.VEHICLES_LIVING.values():
                vehicle.route_pref_update(weight=world.DUO_UPDATE_WEIGHT)
        world.TIME = world.T * world.DELTAT
        if world.user_function is not None:
            world.user_function(world)
        if _case8_all_vehicles_finished(world):
            break
        if world.T == world.TSIZE - 1:
            break


def _case8_require_finished_world(world: World) -> None:
    unfinished_names = []
    for vehicle in world.VEHICLES.values():
        if vehicle.state != "end":
            unfinished_names.append(vehicle.name)
    if unfinished_names:
        raise RuntimeError(
            "CASE 8 actual world did not finish every vehicle. "
            f"world={world.name!r} unfinished={unfinished_names!r} "
            f"T={world.T} TSIZE={world.TSIZE}."
        )


def _case8_assert_no_output_directory(world_name: str) -> None:
    output_directory = f"out{world_name}"
    if os.path.isdir(output_directory):
        raise RuntimeError(
            "CASE 8 created an output directory: "
            f"{output_directory}"
        )


def _case8_validate_real_world(real_world: World) -> None:
    deltan = real_world.DELTAN
    if type(deltan) is not int or deltan != 1:
        raise ValueError(
            "CASE 8 real World DELTAN must be the int 1. "
            f"got {deltan!r} type={type(deltan).__name__}."
        )
    deltat = real_world.DELTAT
    if isinstance(deltat, bool) or not isinstance(deltat, (int, float)):
        raise ValueError(
            "CASE 8 real World DELTAT is not a number. "
            f"got {deltat!r}."
        )
    if not math.isfinite(float(deltat)) or float(deltat) <= 0.0:
        raise ValueError(
            "CASE 8 real World DELTAT must be finite and positive. "
            f"got {deltat!r}."
        )


def _case8_collect_evaluated_vehicles(
    real_world: World,
    evaluated_vehicle_names: Sequence[str] | None,
) -> list:
    if evaluated_vehicle_names is None:
        vehicles = []
        for vehicle_name in real_world.VEHICLES:
            vehicles.append(real_world.VEHICLES[vehicle_name])
    else:
        vehicles = []
        for vehicle_name in evaluated_vehicle_names:
            if vehicle_name not in real_world.VEHICLES:
                raise ValueError(
                    "CASE 8 evaluated vehicle does not exist: "
                    f"{vehicle_name!r}."
                )
            vehicles.append(real_world.VEHICLES[vehicle_name])
    if len(vehicles) == 0:
        raise ValueError("CASE 8 has no vehicles to evaluate.")
    for vehicle in vehicles:
        if vehicle.state != "end":
            raise ValueError(
                "CASE 8 vehicle is not finished. "
                f"vehicle={vehicle.name!r} state={vehicle.state!r}."
            )
    return vehicles


def _case8_get_actual_route_links(vehicle) -> list:
    route, _timestamps = vehicle.traveled_route(
        include_arrival_time=False,
        include_departure_time=False,
    )
    route_links = list(route.links)
    if len(route_links) == 0:
        raise ValueError(
            "CASE 8 actual route is empty. "
            f"vehicle={vehicle.name!r}."
        )
    for index, link in enumerate(route_links):
        if link is None:
            raise ValueError(
                "CASE 8 actual route contains an empty link. "
                f"vehicle={vehicle.name!r} index={index}."
            )
        length = float(link.length)
        speed_u = float(link.u)
        if not math.isfinite(length) or length <= 0.0:
            raise ValueError(
                "CASE 8 link length is invalid. "
                f"vehicle={vehicle.name!r} index={index} "
                f"link={link.name!r} length={link.length!r}."
            )
        if not math.isfinite(speed_u) or speed_u <= 0.0:
            raise ValueError(
                "CASE 8 link u is invalid. "
                f"vehicle={vehicle.name!r} index={index} "
                f"link={link.name!r} u={link.u!r}."
            )
    return route_links


def _case8_build_physical_route_key(deltat, route_links) -> tuple:
    """Same tuple as CASE 7. Link order is kept and values are not rounded."""
    return _build_physical_route_key(deltat, route_links)


def _case8_build_route_audit_identity(route_links) -> tuple:
    """Same name tuple as CASE 7. Built from the same link list as the key."""
    return _build_route_audit_identity(route_links)


def _case8_register_route_audit_identity(
    state: Case8EvaluationState,
    physical_key,
    audit_identity,
) -> None:
    identities = state.audit_identities_by_physical_key.get(physical_key)
    if identities is None:
        identities = []
        state.audit_identities_by_physical_key[physical_key] = identities
    if audit_identity in identities:
        state.counters.duplicate_audit_identity_observation_count += 1
        return
    identities.append(audit_identity)
    state.counters.unique_audit_identity_count += 1


def _case8_compute_reference_tmax(route_links, deltat: float) -> float:
    """Finish-time budget for the reference run. This is not T_min,z."""
    analytical_free_flow_time_s = 0.0
    for link in route_links:
        analytical_free_flow_time_s += float(link.length) / float(link.u)
    link_count = len(route_links)
    return (
        analytical_free_flow_time_s
        + (link_count + 2) * float(deltat)
        + 60.0
    )


def _case8_build_reference_world(route_links, real_deltat: float) -> World:
    """Standard reference world from the design notes. Verification copy only."""
    if len(route_links) == 0:
        raise ValueError("CASE 8 cannot build a reference world from an empty route.")
    tmax_seconds = _case8_compute_reference_tmax(route_links, real_deltat)
    world = World(
        name=CASE8_REFERENCE_WORLD_NAME,
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
        raise ValueError(
            "CASE 8 reference World DELTAN must be the int 1. "
            f"got {world.DELTAN!r} type={type(world.DELTAN).__name__}."
        )
    if world.DELTAT != real_deltat:
        raise ValueError(
            "CASE 8 reference DELTAT does not match the real World. "
            f"reference={world.DELTAT!r} real={real_deltat!r}."
        )

    link_count = len(route_links)
    for index in range(link_count + 1):
        world.addNode(
            f"reference_node_{index}",
            float(index),
            0.0,
            signal=[0],
        )
    reference_link_names = []
    for index, link in enumerate(route_links):
        reference_link_name = f"reference_link_{index}"
        world.addLink(
            reference_link_name,
            f"reference_node_{index}",
            f"reference_node_{index + 1}",
            length=float(link.length),
            free_flow_speed=float(link.u),
            number_of_lanes=1,
            jam_density=CASE8_REFERENCE_JAM_DENSITY,
            jam_density_per_lane=None,
            merge_priority=1.0,
            signal_group=[0],
            capacity_in=NON_BINDING_CAPACITY,
            capacity_out=NON_BINDING_CAPACITY,
        )
        reference_link_names.append(reference_link_name)
    _add_vehicle_with_route(
        world,
        "case8_reference_vehicle",
        "reference_node_0",
        f"reference_node_{link_count}",
        0,
        reference_link_names,
    )

    for node in world.NODES:
        if node.flow_capacity is not None:
            raise RuntimeError(
                "CASE 8 reference node has a flow capacity. "
                f"node={node.name!r}."
            )
        if node.order_control_type != "none" or node.order_control_eligible:
            raise RuntimeError(
                "CASE 8 reference node has order control. "
                f"node={node.name!r}."
            )
        if node.user_function is not None:
            raise RuntimeError(
                "CASE 8 reference node has a user function. "
                f"node={node.name!r}."
            )
    for link in world.LINKS:
        if link.user_function is not None:
            raise RuntimeError(
                "CASE 8 reference link has a user function. "
                f"link={link.name!r}."
            )
    return world


def _case8_run_reference_replay(
    route_links,
    real_deltat: float,
    physical_key,
) -> Case8ReferenceReplayResult:
    world = _case8_build_reference_world(route_links, real_deltat)
    _case8_execute_without_analyzer(world)
    if hasattr(world, "analyzer"):
        raise RuntimeError("CASE 8 reference replay created an Analyzer.")
    if len(world.VEHICLES) != 1:
        raise RuntimeError(
            "CASE 8 reference world does not have one vehicle. "
            f"count={len(world.VEHICLES)}."
        )
    vehicle = next(iter(world.VEHICLES.values()))
    if vehicle.state != "end":
        raise RuntimeError(
            "CASE 8 reference vehicle did not finish. "
            f"state={vehicle.state!r} T={world.T} TSIZE={world.TSIZE}."
        )
    travel_time_s = float(vehicle.travel_time)
    if not math.isfinite(travel_time_s) or travel_time_s < 0.0:
        raise RuntimeError(
            "CASE 8 reference travel_time is invalid. "
            f"travel_time={vehicle.travel_time!r}."
        )
    if vehicle.arrival_time is None or vehicle.arrival_time < 0:
        raise RuntimeError(
            "CASE 8 reference arrival_time is invalid. "
            f"arrival_time={vehicle.arrival_time!r}."
        )
    route, _timestamps = vehicle.traveled_route(
        include_arrival_time=False,
        include_departure_time=False,
    )
    if len(route.links) != len(route_links):
        raise RuntimeError(
            "CASE 8 reference route link count does not match. "
            f"reference={len(route.links)} actual={len(route_links)}."
        )
    for index, link in enumerate(route.links):
        expected_length = float(route_links[index].length)
        expected_u = float(route_links[index].u)
        if float(link.length) != expected_length or float(link.u) != expected_u:
            raise RuntimeError(
                "CASE 8 reference route does not match the actual physical route. "
                f"index={index} reference_length={link.length!r} "
                f"actual_length={expected_length!r} "
                f"reference_u={link.u!r} actual_u={expected_u!r}."
            )
    if type(world.DELTAN) is not int or world.DELTAN != 1:
        raise RuntimeError(
            "CASE 8 reference DELTAN changed during replay. "
            f"got {world.DELTAN!r}."
        )
    if world.DELTAT != real_deltat:
        raise RuntimeError(
            "CASE 8 reference DELTAT changed during replay. "
            f"reference={world.DELTAT!r} real={real_deltat!r}."
        )

    analytical_free_flow_time_s = 0.0
    for link in route_links:
        analytical_free_flow_time_s += float(link.length) / float(link.u)
    result = Case8ReferenceReplayResult(
        physical_route_key=physical_key,
        minimum_trip_time_s=travel_time_s,
        analytical_free_flow_time_s=analytical_free_flow_time_s,
        reference_route_link_count=len(route.links),
        reference_world_deltat=world.DELTAT,
        reference_world_deltan=world.DELTAN,
        reference_vehicle_arrival_time=vehicle.arrival_time,
        reference_vehicle_travel_time=travel_time_s,
        validation_passed=True,
    )
    # Drop the only local names that point at the reference objects.
    del vehicle
    del world
    del route
    return result


def _case8_get_or_run_reference_replay(
    state: Case8EvaluationState,
    route_links,
    physical_key,
) -> Case8ReferenceReplayResult:
    stored = state.reference_results_by_physical_key.get(physical_key)
    if stored is None:
        result = _case8_run_reference_replay(
            route_links,
            state.real_deltat,
            physical_key,
        )
        if not result.validation_passed:
            state.counters.validation_failure_count += 1
            raise RuntimeError(
                "CASE 8 will not store an unvalidated reference result."
            )
        state.reference_results_by_physical_key[physical_key] = result
        state.counters.reference_replay_run_count += 1
        state.counters.unique_physical_route_count += 1
        return result

    if not stored.validation_passed:
        state.counters.validation_failure_count += 1
        raise RuntimeError(
            "CASE 8 stored reference result is not validated."
        )
    if stored.physical_route_key != physical_key:
        state.counters.validation_failure_count += 1
        raise RuntimeError(
            "CASE 8 stored reference result is under a different physical key."
        )
    if stored.minimum_trip_time_s != stored.reference_vehicle_travel_time:
        state.counters.validation_failure_count += 1
        raise RuntimeError(
            "CASE 8 stored minimum trip time does not match the stored travel time."
        )
    state.counters.reference_reuse_count += 1
    return stored


def _case8_read_true_vot(vehicle_name: str, true_vot_by_vehicle_name: dict):
    if vehicle_name not in true_vot_by_vehicle_name:
        raise ValueError(
            "CASE 8 true_vot is missing. "
            f"vehicle={vehicle_name!r}."
        )
    true_vot = true_vot_by_vehicle_name[vehicle_name]
    if isinstance(true_vot, bool) or not isinstance(true_vot, (int, float)):
        raise ValueError(
            "CASE 8 true_vot is invalid. "
            f"vehicle={vehicle_name!r} true_vot={true_vot!r}."
        )
    if not math.isfinite(float(true_vot)):
        raise ValueError(
            "CASE 8 true_vot is invalid. "
            f"vehicle={vehicle_name!r} true_vot={true_vot!r}."
        )
    return float(true_vot)


def _case8_read_participation(vehicle_name: str, participation_by_vehicle_name: dict) -> str:
    if vehicle_name not in participation_by_vehicle_name:
        return "unspecified"
    category = participation_by_vehicle_name[vehicle_name]
    if category not in CASE8_PARTICIPATION_CATEGORIES:
        raise ValueError(
            "CASE 8 participation category is invalid. "
            f"vehicle={vehicle_name!r} category={category!r}."
        )
    return category


def _case8_build_vehicle_record(
    state: Case8EvaluationState,
    vehicle,
    physical_key,
    audit_identity,
    reference_result: Case8ReferenceReplayResult,
    true_vot_by_vehicle_name: dict,
    participation_by_vehicle_name: dict,
) -> Case8VehicleRecord:
    actual_travel_time_s = float(vehicle.travel_time)
    if not math.isfinite(actual_travel_time_s):
        raise ValueError(
            "CASE 8 actual travel_time is invalid. "
            f"vehicle={vehicle.name!r} travel_time={vehicle.travel_time!r}."
        )
    # method_name is stored for the audit. It is not used in this subtraction.
    cumulative_waiting_time_s = (
        actual_travel_time_s - reference_result.minimum_trip_time_s
    )
    if cumulative_waiting_time_s < -TIME_ABS_TOL:
        state.counters.negative_cumulative_waiting_time_count += 1
        raise RuntimeError(
            "CASE 8 CW_z is clearly negative and was not changed to 0. "
            f"vehicle={vehicle.name!r} CW_z={cumulative_waiting_time_s!r}."
        )
    true_vot = _case8_read_true_vot(vehicle.name, true_vot_by_vehicle_name)
    weighted = true_vot * cumulative_waiting_time_s
    participation_category = _case8_read_participation(
        vehicle.name,
        participation_by_vehicle_name,
    )
    return Case8VehicleRecord(
        vehicle_name=vehicle.name,
        method_name=state.method_name,
        physical_route_key=physical_key,
        route_audit_identity=audit_identity,
        actual_travel_time_s=actual_travel_time_s,
        minimum_trip_time_s=reference_result.minimum_trip_time_s,
        cumulative_waiting_time_s=cumulative_waiting_time_s,
        true_vot=true_vot,
        weighted_cumulative_waiting_time=weighted,
        participation_category=participation_category,
    )


def _case8_build_summary(state: Case8EvaluationState) -> tuple[float, float]:
    vehicle_count = len(state.vehicle_records)
    if vehicle_count == 0:
        raise RuntimeError("CASE 8 cannot summarize an empty vehicle list.")
    total_cw = 0.0
    total_weighted = 0.0
    for record in state.vehicle_records:
        total_cw += record.cumulative_waiting_time_s
        total_weighted += record.weighted_cumulative_waiting_time
    average_cw = total_cw / vehicle_count
    average_weighted = total_weighted / vehicle_count
    return average_cw, average_weighted


def _case8_check_result_consistency(state: Case8EvaluationState) -> None:
    counters = state.counters
    if counters.validation_failure_count != 0:
        raise RuntimeError(
            "CASE 8 will not return an official summary. "
            f"validation_failure_count={counters.validation_failure_count}."
        )
    if counters.reference_replay_run_count != counters.unique_physical_route_count:
        raise RuntimeError(
            "CASE 8 replay count does not match the number of physical keys. "
            f"replay={counters.reference_replay_run_count} "
            f"keys={counters.unique_physical_route_count}."
        )
    if counters.evaluated_vehicle_count != (
        counters.reference_replay_run_count + counters.reference_reuse_count
    ):
        raise RuntimeError(
            "CASE 8 vehicle count does not match replay plus reuse. "
            f"vehicles={counters.evaluated_vehicle_count} "
            f"replay={counters.reference_replay_run_count} "
            f"reuse={counters.reference_reuse_count}."
        )
    if len(state.vehicle_records) != counters.evaluated_vehicle_count:
        raise RuntimeError(
            "CASE 8 record count does not match the evaluated vehicle count. "
            f"records={len(state.vehicle_records)} "
            f"vehicles={counters.evaluated_vehicle_count}."
        )
    if len(state.reference_results_by_physical_key) != counters.unique_physical_route_count:
        raise RuntimeError(
            "CASE 8 stored reference count does not match the key count."
        )
    for physical_key, reference_result in state.reference_results_by_physical_key.items():
        if not reference_result.validation_passed:
            raise RuntimeError(
                "CASE 8 stored reference result did not pass validation."
            )
        if reference_result.physical_route_key != physical_key:
            raise RuntimeError(
                "CASE 8 stored reference result key does not match its dict key."
            )
    for record in state.vehicle_records:
        reference_result = state.reference_results_by_physical_key.get(
            record.physical_route_key
        )
        if reference_result is None:
            raise RuntimeError(
                "CASE 8 vehicle has no reference result. "
                f"vehicle={record.vehicle_name!r}."
            )
        if record.minimum_trip_time_s != reference_result.minimum_trip_time_s:
            raise RuntimeError(
                "CASE 8 vehicle T_min,z does not match the stored reference. "
                f"vehicle={record.vehicle_name!r}."
            )
        identities = state.audit_identities_by_physical_key.get(
            record.physical_route_key
        )
        if identities is None or record.route_audit_identity not in identities:
            raise RuntimeError(
                "CASE 8 audit identity is not registered for its physical key. "
                f"vehicle={record.vehicle_name!r}."
            )


def _case8_value_holds_simulation_object(value, seen_ids: set) -> bool:
    if id(value) in seen_ids:
        return False
    seen_ids.add(id(value))
    if isinstance(value, (World, UxsimVehicle, UxsimNode, UxsimLink, UxsimAnalyzer)):
        return True
    if isinstance(value, (str, bytes, int, float, bool, type(None))):
        return False
    if isinstance(value, dict):
        for key, item in value.items():
            if _case8_value_holds_simulation_object(key, seen_ids):
                return True
            if _case8_value_holds_simulation_object(item, seen_ids):
                return True
        return False
    if isinstance(value, (list, tuple)):
        for item in value:
            if _case8_value_holds_simulation_object(item, seen_ids):
                return True
        return False
    if hasattr(value, "__dataclass_fields__"):
        for field_name in value.__dataclass_fields__:
            item = getattr(value, field_name)
            if _case8_value_holds_simulation_object(item, seen_ids):
                return True
        return False
    return False


def _case8_new_state(real_world: World, method_name: str) -> Case8EvaluationState:
    return Case8EvaluationState(
        real_deltat=real_world.DELTAT,
        method_name=method_name,
        reference_results_by_physical_key={},
        audit_identities_by_physical_key={},
        counters=Case8EvaluationCounters(),
        vehicle_records=[],
    )


def _case8_evaluate_vehicle_list(
    real_world: World,
    vehicles: Sequence,
    method_name: str,
    true_vot_by_vehicle_name: dict,
    participation_by_vehicle_name: dict,
) -> Case8EvaluationResult:
    """One evaluation. The state exists only inside this call."""
    _case8_validate_real_world(real_world)
    if len(vehicles) == 0:
        raise ValueError("CASE 8 has no vehicles to evaluate.")
    for vehicle in vehicles:
        if vehicle.state != "end":
            raise ValueError(
                "CASE 8 vehicle is not finished. "
                f"vehicle={vehicle.name!r} state={vehicle.state!r}."
            )

    state = _case8_new_state(real_world, method_name)
    for vehicle in vehicles:
        if float(vehicle.W.DELTAT) != float(state.real_deltat):
            raise ValueError(
                "CASE 8 cannot mix different DELTAT values in one evaluation. "
                f"vehicle={vehicle.name!r} "
                f"vehicle_DELTAT={vehicle.W.DELTAT!r} "
                f"evaluation_DELTAT={state.real_deltat!r}."
            )
        if type(vehicle.W.DELTAN) is not int or vehicle.W.DELTAN != 1:
            raise ValueError(
                "CASE 8 vehicle world DELTAN must be the int 1. "
                f"vehicle={vehicle.name!r} DELTAN={vehicle.W.DELTAN!r}."
            )
        route_links = _case8_get_actual_route_links(vehicle)
        physical_key = _case8_build_physical_route_key(
            state.real_deltat,
            route_links,
        )
        audit_identity = _case8_build_route_audit_identity(route_links)
        _case8_register_route_audit_identity(state, physical_key, audit_identity)
        reference_result = _case8_get_or_run_reference_replay(
            state,
            route_links,
            physical_key,
        )
        record = _case8_build_vehicle_record(
            state,
            vehicle,
            physical_key,
            audit_identity,
            reference_result,
            true_vot_by_vehicle_name,
            participation_by_vehicle_name,
        )
        state.vehicle_records.append(record)
        state.counters.evaluated_vehicle_count += 1

    _case8_check_result_consistency(state)
    average_cw, average_weighted = _case8_build_summary(state)
    result = Case8EvaluationResult(
        method_name=method_name,
        vehicle_records=state.vehicle_records,
        reference_results_by_physical_key=state.reference_results_by_physical_key,
        audit_identities_by_physical_key=state.audit_identities_by_physical_key,
        counters=state.counters,
        average_cumulative_waiting_time_s=average_cw,
        average_weighted_cumulative_waiting_time=average_weighted,
    )
    if _case8_value_holds_simulation_object(result, set()):
        raise RuntimeError(
            "CASE 8 result still holds a World, Vehicle, Node, Link, or Analyzer."
        )
    return result


def _case8_evaluate_world(
    real_world: World,
    method_name: str,
    true_vot_by_vehicle_name: dict,
    participation_by_vehicle_name: dict,
    evaluated_vehicle_names: Sequence[str] | None = None,
) -> Case8EvaluationResult:
    _case8_validate_real_world(real_world)
    vehicles = _case8_collect_evaluated_vehicles(
        real_world,
        evaluated_vehicle_names,
    )
    return _case8_evaluate_vehicle_list(
        real_world,
        vehicles,
        method_name,
        true_vot_by_vehicle_name,
        participation_by_vehicle_name,
    )


def _case8_vot_map(vehicle_names: Sequence[str]) -> dict:
    vot_by_name = {}
    for vehicle_name in vehicle_names:
        vot_by_name[vehicle_name] = CASE8_VERIFICATION_TRUE_VOT
    return vot_by_name


def _case8_print_counts(label: str, result: Case8EvaluationResult) -> None:
    counters = result.counters
    cw_values = []
    for record in result.vehicle_records:
        cw_values.append(record.cumulative_waiting_time_s)
    print(
        f"  {label}: vehicles={counters.evaluated_vehicle_count} "
        f"keys={counters.unique_physical_route_count} "
        f"replay={counters.reference_replay_run_count} "
        f"reuse={counters.reference_reuse_count} "
        f"audit={counters.unique_audit_identity_count} "
        f"CW_z={cw_values}"
    )


def _case8_print_success(
    case_name: str,
    comparison: str,
    result: Case8EvaluationResult,
    conclusion: str,
    print_header: bool = True,
) -> None:
    counters = result.counters
    cw_values = []
    for record in result.vehicle_records:
        cw_values.append(record.cumulative_waiting_time_s)
    if print_header:
        _print_case_header(case_name)
    print(f"Comparison: {comparison}")
    print(f"  method_name: {result.method_name}")
    print(f"  evaluated vehicles: {counters.evaluated_vehicle_count}")
    print(f"  unique physical routes: {counters.unique_physical_route_count}")
    print(f"  reference replay runs: {counters.reference_replay_run_count}")
    print(f"  reference reuse: {counters.reference_reuse_count}")
    print(f"  audit identities: {counters.unique_audit_identity_count}")
    print(
        "  duplicate audit observations: "
        f"{counters.duplicate_audit_identity_observation_count}"
    )
    print(f"  CW_z: {cw_values}")
    print(f"Limited conclusion: {conclusion}")
    print(f"PASS {case_name}")


def _case8_assert_same_measured_times(
    case_name: str,
    left: Case8EvaluationResult,
    right: Case8EvaluationResult,
) -> None:
    if len(left.vehicle_records) != len(right.vehicle_records):
        raise RuntimeError(
            f"{case_name}: method results have different vehicle counts."
        )
    for index, left_record in enumerate(left.vehicle_records):
        right_record = right.vehicle_records[index]
        if left_record.vehicle_name != right_record.vehicle_name:
            raise RuntimeError(
                f"{case_name}: method results are not in the same vehicle order."
            )
        if left_record.minimum_trip_time_s != right_record.minimum_trip_time_s:
            raise RuntimeError(
                f"{case_name}: T_min,z changed with method_name. "
                f"vehicle={left_record.vehicle_name!r}."
            )
        if left_record.cumulative_waiting_time_s != right_record.cumulative_waiting_time_s:
            raise RuntimeError(
                f"{case_name}: CW_z changed with method_name. "
                f"vehicle={left_record.vehicle_name!r}."
            )
        if (
            left_record.weighted_cumulative_waiting_time
            != right_record.weighted_cumulative_waiting_time
        ):
            raise RuntimeError(
                f"{case_name}: weighted CW changed with method_name. "
                f"vehicle={left_record.vehicle_name!r}."
            )


def _case8_run_actual(world: World) -> World:
    _case8_execute_without_analyzer(world)
    _case8_require_finished_world(world)
    _case8_assert_no_output_directory(world.name)
    _case8_assert_no_output_directory(CASE8_REFERENCE_WORLD_NAME)
    return world


def _validate_case8a() -> None:
    case_name = "CASE 8A: same physical route is shared"
    _print_case_header(case_name)
    world = _case8_make_quiet_world("8a")
    lengths = (200.0, 200.0, 200.0)
    speeds = (
        SPEED_60KPH_M_PER_S,
        SPEED_60KPH_M_PER_S,
        SPEED_60KPH_M_PER_S,
    )
    link_names = ("l1", "l2", "l3")
    _case8_add_route_chain(
        world,
        "chain8a",
        link_names,
        lengths,
        speeds,
        "veh_8a_first",
        row_y=0.0,
        departure_timestep=0,
    )
    _add_vehicle_with_route(
        world,
        "veh_8a_second",
        "chain8a_node_0",
        "chain8a_node_3",
        100,
        link_names,
    )
    _case8_run_actual(world)
    vehicle_names = ["veh_8a_first", "veh_8a_second"]
    vot_by_name = _case8_vot_map(vehicle_names)
    participation_by_name = {
        "veh_8a_first": "participating",
        "veh_8a_second": "nonparticipating",
    }
    results = []
    for method_name in CASE8_METHOD_NAMES:
        result = _case8_evaluate_world(
            world,
            method_name,
            vot_by_name,
            participation_by_name,
        )
        counters = result.counters
        if counters.unique_physical_route_count != 1:
            raise RuntimeError(f"{case_name}: expected one physical key.")
        if counters.reference_replay_run_count != 1:
            raise RuntimeError(f"{case_name}: expected one reference replay.")
        if counters.reference_reuse_count != 1:
            raise RuntimeError(f"{case_name}: expected one reuse.")
        if counters.evaluated_vehicle_count != 2:
            raise RuntimeError(f"{case_name}: expected two vehicles.")
        if len(result.vehicle_records) != 2:
            raise RuntimeError(f"{case_name}: expected two records.")
        if counters.unique_audit_identity_count != 1:
            raise RuntimeError(f"{case_name}: expected one audit identity.")
        first = result.vehicle_records[0]
        second = result.vehicle_records[1]
        if first.minimum_trip_time_s != second.minimum_trip_time_s:
            raise RuntimeError(f"{case_name}: the two vehicles do not share T_min,z.")
        if first.physical_route_key != second.physical_route_key:
            raise RuntimeError(f"{case_name}: physical keys differ.")
        if first.route_audit_identity != ("l1", "l2", "l3"):
            raise RuntimeError(f"{case_name}: audit identity changed.")
        results.append(result)
        _case8_print_counts(method_name, result)
    for result in results[1:]:
        _case8_assert_same_measured_times(case_name, results[0], result)
    _case8_print_success(
        case_name,
        "two finished vehicles, same links, four method names",
        results[0],
        "One evaluation replays once. method_name does not change T_min,z or CW_z. "
        "No method-specific field is read.",
        print_header=False,
    )


def _validate_case8b() -> None:
    case_name = "CASE 8B: same physics, different link names"
    world_left = _case8_make_quiet_world("8b_left")
    lengths = (200.0, 200.0, 200.0)
    speeds = (
        SPEED_60KPH_M_PER_S,
        SPEED_60KPH_M_PER_S,
        SPEED_60KPH_M_PER_S,
    )
    left_names = ("l1", "l2", "l3")
    _case8_add_route_chain(
        world_left,
        "chain8b_left",
        left_names,
        lengths,
        speeds,
        "veh_8b_left_first",
        row_y=0.0,
    )
    _add_vehicle_with_route(
        world_left,
        "veh_8b_left_second",
        "chain8b_left_node_0",
        "chain8b_left_node_3",
        100,
        left_names,
    )
    _case8_run_actual(world_left)

    world_right = _case8_make_quiet_world("8b_right")
    right_names = ("link_alpha", "link_beta", "link_gamma")
    _case8_add_route_chain(
        world_right,
        "chain8b_right",
        right_names,
        lengths,
        speeds,
        "veh_8b_right",
        row_y=1.0,
    )
    _case8_run_actual(world_right)
    _case8_validate_real_world(world_left)
    _case8_validate_real_world(world_right)
    if world_left.DELTAT != world_right.DELTAT:
        raise RuntimeError(f"{case_name}: the two worlds do not share DELTAT.")

    vehicles = [
        world_left.VEHICLES["veh_8b_left_first"],
        world_right.VEHICLES["veh_8b_right"],
        world_left.VEHICLES["veh_8b_left_second"],
    ]
    vehicle_names = ["veh_8b_left_first", "veh_8b_right", "veh_8b_left_second"]
    result = _case8_evaluate_vehicle_list(
        world_left,
        vehicles,
        "signalized_uxsim",
        _case8_vot_map(vehicle_names),
        {},
    )
    counters = result.counters
    identities = result.audit_identities_by_physical_key[
        result.vehicle_records[0].physical_route_key
    ]
    if counters.unique_physical_route_count != 1 or counters.reference_replay_run_count != 1:
        raise RuntimeError(f"{case_name}: link names caused another replay.")
    if counters.reference_reuse_count != 2:
        raise RuntimeError(f"{case_name}: expected two reuses.")
    if counters.unique_audit_identity_count != 2:
        raise RuntimeError(f"{case_name}: expected two audit identities.")
    if counters.duplicate_audit_identity_observation_count != 1:
        raise RuntimeError(f"{case_name}: the repeated name tuple was stored again.")
    if identities != [("l1", "l2", "l3"), ("link_alpha", "link_beta", "link_gamma")]:
        raise RuntimeError(
            f"{case_name}: audit identity order was not the first-seen order. "
            f"got {identities!r}."
        )
    if result.vehicle_records[0].participation_category != "unspecified":
        raise RuntimeError(
            f"{case_name}: a missing participation mapping was not unspecified."
        )
    _case8_print_success(
        case_name,
        "l1/l2/l3 and link_alpha/link_beta/link_gamma with the same length and u",
        result,
        "One physical key, one replay, two audit identities, no duplicate tuple.",
    )


def _case8_assert_separated_keys(case_name: str, result: Case8EvaluationResult, expected_key_count: int) -> None:
    counters = result.counters
    if counters.unique_physical_route_count != expected_key_count:
        raise RuntimeError(
            f"{case_name}: expected {expected_key_count} physical keys."
        )
    if counters.reference_replay_run_count != expected_key_count:
        raise RuntimeError(
            f"{case_name}: replay count does not match the separated keys."
        )
    if counters.reference_reuse_count != 0:
        raise RuntimeError(f"{case_name}: different physical keys were reused.")
    keys = []
    for record in result.vehicle_records:
        if record.physical_route_key not in keys:
            keys.append(record.physical_route_key)
    if len(keys) != expected_key_count:
        raise RuntimeError(f"{case_name}: vehicle keys were not separated.")


def _validate_case8c() -> None:
    case_name = "CASE 8C: different physical routes stay separate"
    _print_case_header(case_name)

    order_world = _case8_make_quiet_world("8c_order")
    _case8_add_route_chain(
        order_world,
        "chain8c_order_left",
        ("order_l1", "order_l2"),
        (120.0, 200.0),
        (10.0, 20.0),
        "veh_8c_order_left",
        row_y=0.0,
    )
    _case8_add_route_chain(
        order_world,
        "chain8c_order_right",
        ("order_r1", "order_r2"),
        (200.0, 120.0),
        (20.0, 10.0),
        "veh_8c_order_right",
        row_y=1.0,
    )
    _case8_run_actual(order_world)
    order_result = _case8_evaluate_world(
        order_world,
        "fcfs",
        _case8_vot_map(["veh_8c_order_left", "veh_8c_order_right"]),
        {},
    )
    _case8_assert_separated_keys("CASE 8C link order", order_result, 2)
    _case8_print_counts("link order", order_result)

    length_world = _case8_make_quiet_world("8c_length")
    _case8_add_route_chain(
        length_world,
        "chain8c_length_left",
        ("length_left",),
        (200.0,),
        (10.0,),
        "veh_8c_length_left",
        row_y=0.0,
    )
    _case8_add_route_chain(
        length_world,
        "chain8c_length_right",
        ("length_right",),
        (250.0,),
        (10.0,),
        "veh_8c_length_right",
        row_y=1.0,
    )
    _case8_run_actual(length_world)
    length_result = _case8_evaluate_world(
        length_world,
        "batch",
        _case8_vot_map(["veh_8c_length_left", "veh_8c_length_right"]),
        {},
    )
    _case8_assert_separated_keys("CASE 8C length", length_result, 2)
    _case8_print_counts("length", length_result)

    speed_world = _case8_make_quiet_world("8c_u")
    _case8_add_route_chain(
        speed_world,
        "chain8c_u_left",
        ("u_left",),
        (200.0,),
        (10.0,),
        "veh_8c_u_left",
        row_y=0.0,
    )
    _case8_add_route_chain(
        speed_world,
        "chain8c_u_right",
        ("u_right",),
        (200.0,),
        (20.0,),
        "veh_8c_u_right",
        row_y=1.0,
    )
    _case8_run_actual(speed_world)
    speed_result = _case8_evaluate_world(
        speed_world,
        "tvt_mp",
        _case8_vot_map(["veh_8c_u_left", "veh_8c_u_right"]),
        {},
    )
    _case8_assert_separated_keys("CASE 8C u", speed_result, 2)
    _case8_print_counts("u", speed_result)

    deltat_left = _case8_make_quiet_world("8c_deltat_1", reaction_time=1.0)
    _case8_add_route_chain(
        deltat_left,
        "chain8c_deltat_1",
        ("deltat_link",),
        (200.0,),
        (SPEED_60KPH_M_PER_S,),
        "veh_8c_deltat_1",
        row_y=0.0,
    )
    _case8_run_actual(deltat_left)
    deltat_right = _case8_make_quiet_world("8c_deltat_0_5", reaction_time=0.5)
    _case8_add_route_chain(
        deltat_right,
        "chain8c_deltat_0_5",
        ("deltat_link",),
        (200.0,),
        (SPEED_60KPH_M_PER_S,),
        "veh_8c_deltat_0_5",
        row_y=0.0,
    )
    _case8_run_actual(deltat_right)
    deltat_left_result = _case8_evaluate_world(
        deltat_left,
        "signalized_uxsim",
        _case8_vot_map(["veh_8c_deltat_1"]),
        {},
    )
    deltat_right_result = _case8_evaluate_world(
        deltat_right,
        "signalized_uxsim",
        _case8_vot_map(["veh_8c_deltat_0_5"]),
        {},
    )
    _case8_assert_separated_keys("CASE 8C DELTAT left", deltat_left_result, 1)
    _case8_assert_separated_keys("CASE 8C DELTAT right", deltat_right_result, 1)
    left_key = deltat_left_result.vehicle_records[0].physical_route_key
    right_key = deltat_right_result.vehicle_records[0].physical_route_key
    if left_key == right_key:
        raise RuntimeError(f"{case_name}: different DELTAT values shared one key.")
    _case8_print_counts("DELTAT 1 s", deltat_left_result)
    _case8_print_counts("DELTAT 0.5 s", deltat_right_result)
    print("  DELTAT values were evaluated as separate worlds.")
    print(
        "Limited conclusion: link order, length, u, and DELTAT each keep a separate replay."
    )
    print(f"PASS {case_name}")


def _validate_case8d() -> None:
    case_name = "CASE 8D: origin wait changes only CW_z"
    world = _case8_make_quiet_world("8d")
    _case8_add_route_chain(
        world,
        "chain8d_free",
        ("free_l1",),
        (200.0,),
        (SPEED_60KPH_M_PER_S,),
        "veh_8d_free",
        row_y=0.0,
    )
    _case8_add_route_chain(
        world,
        "chain8d_wait",
        ("wait_l1",),
        (200.0,),
        (SPEED_60KPH_M_PER_S,),
        "veh_8d_wait",
        row_y=1.0,
        capacity_in=0.0,
        link_user_function=_case5_release_first_link_inflow,
    )
    _case8_run_actual(world)
    vehicle_names = ["veh_8d_free", "veh_8d_wait"]
    vot_by_name = _case8_vot_map(vehicle_names)
    participation_by_name = {
        "veh_8d_free": "participating",
        "veh_8d_wait": "nonparticipating",
    }
    results = []
    for method_name in CASE8_METHOD_NAMES:
        result = _case8_evaluate_world(
            world,
            method_name,
            vot_by_name,
            participation_by_name,
        )
        results.append(result)
    for result in results[1:]:
        _case8_assert_same_measured_times(case_name, results[0], result)
    result = results[0]
    free_record = result.vehicle_records[0]
    wait_record = result.vehicle_records[1]
    if free_record.physical_route_key != wait_record.physical_route_key:
        raise RuntimeError(f"{case_name}: the two vehicles do not share a physical key.")
    if free_record.minimum_trip_time_s != wait_record.minimum_trip_time_s:
        raise RuntimeError(f"{case_name}: T_min,z was not shared.")
    if result.counters.reference_replay_run_count != 1:
        raise RuntimeError(f"{case_name}: the reference replay was not shared.")
    if result.counters.reference_reuse_count != 1:
        raise RuntimeError(f"{case_name}: expected the second vehicle to reuse T_min,z.")
    if not math.isclose(free_record.cumulative_waiting_time_s, 0.0, abs_tol=TIME_ABS_TOL):
        raise RuntimeError(
            f"{case_name}: the vehicle without the hold has CW_z="
            f"{free_record.cumulative_waiting_time_s!r}."
        )
    if not math.isclose(
        wait_record.cumulative_waiting_time_s,
        CASE5_EXPECTED_ADDITIONAL_ORIGIN_WAIT_S,
        abs_tol=TIME_ABS_TOL,
    ):
        raise RuntimeError(
            f"{case_name}: origin wait CW_z="
            f"{wait_record.cumulative_waiting_time_s!r}, "
            f"expected {CASE5_EXPECTED_ADDITIONAL_ORIGIN_WAIT_S}."
        )
    expected_weighted = (
        CASE8_VERIFICATION_TRUE_VOT * CASE5_EXPECTED_ADDITIONAL_ORIGIN_WAIT_S
    )
    if not math.isclose(
        wait_record.weighted_cumulative_waiting_time,
        expected_weighted,
        abs_tol=TIME_ABS_TOL,
    ):
        raise RuntimeError(
            f"{case_name}: weighted CW did not use the verification coefficient."
        )
    if wait_record.participation_category != "nonparticipating":
        raise RuntimeError(
            f"{case_name}: nonparticipating did not keep the same true_vot product."
        )
    _case8_print_success(
        case_name,
        "same 200 m route, one vehicle held by the CASE 5 origin release",
        result,
        "Shared T_min,z. Only the held vehicle gains the CASE 5 extra 4 s.",
    )


def _case8_expect_stop(item_name: str, expected_type: type, action) -> None:
    try:
        action()
    except expected_type as error:
        print(f"CASE 8E: {item_name}")
        print(f"  expected exception: {expected_type.__name__}")
        print(f"  stopped: {error}")
        print(f"PASS CASE 8E: {item_name}")
        return
    except Exception as error:
        raise RuntimeError(
            f"CASE 8E {item_name} stopped with {type(error).__name__}, "
            f"expected {expected_type.__name__}."
        ) from error
    raise RuntimeError(
        f"CASE 8E {item_name} returned an official result instead of stopping."
    )


def _case8_finished_single_link_world(label: str, vehicle_name: str) -> World:
    world = _case8_make_quiet_world(label)
    _case8_add_route_chain(
        world,
        f"chain_{label}",
        ("l1",),
        (200.0,),
        (SPEED_60KPH_M_PER_S,),
        vehicle_name,
        row_y=0.0,
    )
    return _case8_run_actual(world)


def _validate_case8e() -> None:
    case_name = "CASE 8E: bad input does not return an official result"
    _print_case_header(case_name)

    def stop_bad_deltan():
        world = _case8_make_quiet_world("8e_deltan", deltan=2)
        _case8_evaluate_world(world, "signalized_uxsim", {}, {})

    _case8_expect_stop("DELTAN is not int 1", ValueError, stop_bad_deltan)

    def stop_empty_route():
        world = _case8_finished_single_link_world("8e_empty", "veh_8e_empty")

        def empty_route(include_arrival_time=False, include_departure_time=False):
            del include_arrival_time, include_departure_time

            class EmptyRoute:
                links = []

            return EmptyRoute(), []

        world.VEHICLES["veh_8e_empty"].traveled_route = empty_route
        _case8_evaluate_world(
            world,
            "fcfs",
            _case8_vot_map(["veh_8e_empty"]),
            {},
        )

    _case8_expect_stop("actual route is empty", ValueError, stop_empty_route)

    def stop_unfinished():
        world = _case8_make_quiet_world("8e_unfinished")
        _case8_add_route_chain(
            world,
            "chain8e_unfinished",
            ("l1",),
            (200.0,),
            (SPEED_60KPH_M_PER_S,),
            "veh_8e_unfinished",
            row_y=0.0,
        )
        _case8_evaluate_world(
            world,
            "batch",
            _case8_vot_map(["veh_8e_unfinished"]),
            {},
        )

    _case8_expect_stop("vehicle is not finished", ValueError, stop_unfinished)

    def stop_bad_length():
        world = _case8_finished_single_link_world("8e_length", "veh_8e_length")
        route_links = _case8_get_actual_route_links(world.VEHICLES["veh_8e_length"])
        route_links[0].length = 0.0
        _case8_evaluate_world(
            world,
            "tvt_mp",
            _case8_vot_map(["veh_8e_length"]),
            {},
        )

    _case8_expect_stop("link length is 0", ValueError, stop_bad_length)

    def stop_bad_u():
        world = _case8_finished_single_link_world("8e_u", "veh_8e_u")
        route_links = _case8_get_actual_route_links(world.VEHICLES["veh_8e_u"])
        route_links[0].u = float("nan")
        _case8_evaluate_world(
            world,
            "signalized_uxsim",
            _case8_vot_map(["veh_8e_u"]),
            {},
        )

    _case8_expect_stop("link u is NaN", ValueError, stop_bad_u)

    def stop_missing_vot():
        world = _case8_finished_single_link_world("8e_vot_missing", "veh_8e_vot")
        _case8_evaluate_world(world, "fcfs", {}, {})

    _case8_expect_stop("true_vot is missing", ValueError, stop_missing_vot)

    def stop_invalid_vot():
        world = _case8_finished_single_link_world("8e_vot_invalid", "veh_8e_vot_bad")
        _case8_evaluate_world(
            world,
            "batch",
            {"veh_8e_vot_bad": float("nan")},
            {},
        )

    _case8_expect_stop("true_vot is NaN", ValueError, stop_invalid_vot)

    def stop_missing_vehicle():
        world = _case8_make_quiet_world("8e_missing_name")
        _case8_add_route_chain(
            world,
            "chain8e_missing",
            ("l1",),
            (200.0,),
            (SPEED_60KPH_M_PER_S,),
            "veh_8e_present",
            row_y=0.0,
        )
        _case8_evaluate_world(
            world,
            "tvt_mp",
            {},
            {},
            evaluated_vehicle_names=["veh_does_not_exist"],
        )

    _case8_expect_stop(
        "evaluated vehicle name does not exist",
        ValueError,
        stop_missing_vehicle,
    )
    print(
        "Limited conclusion: each bad input stopped with no official ACWT or ACWWT."
    )
    print(f"PASS {case_name}")


def _validate_case8f() -> None:
    case_name = "CASE 8F: evaluations do not keep the previous result"
    world = _case8_make_quiet_world("8f")
    _case8_add_route_chain(
        world,
        "chain8f",
        ("l1",),
        (200.0,),
        (SPEED_60KPH_M_PER_S,),
        "veh_8f",
        row_y=0.0,
    )
    _case8_run_actual(world)
    attribute_names_before = set(vars(world))
    vot_by_name = _case8_vot_map(["veh_8f"])
    first = _case8_evaluate_world(world, "signalized_uxsim", vot_by_name, {})
    second = _case8_evaluate_world(world, "tvt_mp", vot_by_name, {})
    if first.reference_results_by_physical_key is second.reference_results_by_physical_key:
        raise RuntimeError(f"{case_name}: the two evaluations share one result dict.")
    if first.audit_identities_by_physical_key is second.audit_identities_by_physical_key:
        raise RuntimeError(f"{case_name}: the two evaluations share one audit dict.")
    if first.counters is second.counters:
        raise RuntimeError(f"{case_name}: the two evaluations share one counter object.")
    if first.counters.reference_replay_run_count != 1:
        raise RuntimeError(f"{case_name}: the first evaluation did not replay.")
    if second.counters.reference_replay_run_count != 1:
        raise RuntimeError(
            f"{case_name}: the second evaluation reused the first result."
        )
    if second.counters.reference_reuse_count != 0:
        raise RuntimeError(f"{case_name}: the second evaluation did not start empty.")
    first.reference_results_by_physical_key["sentinel"] = "changed-first-only"
    if "sentinel" in second.reference_results_by_physical_key:
        raise RuntimeError(f"{case_name}: changing the first dict changed the second.")
    attribute_names_after = set(vars(world))
    if attribute_names_before != attribute_names_after:
        added_names = sorted(attribute_names_after - attribute_names_before)
        raise RuntimeError(
            f"{case_name}: the real World gained attributes {added_names!r}."
        )
    if _case8_value_holds_simulation_object(first, set()):
        raise RuntimeError(f"{case_name}: the first result holds a simulation object.")
    if _case8_value_holds_simulation_object(second, set()):
        raise RuntimeError(f"{case_name}: the second result holds a simulation object.")
    _case8_assert_no_output_directory(world.name)
    _case8_assert_no_output_directory(CASE8_REFERENCE_WORLD_NAME)
    _case8_print_success(
        case_name,
        "the same finished world evaluated twice",
        second,
        "The second run starts empty, replays again, and stores no reference World.",
    )


def _print_case8_summary() -> None:
    print("")
    print("=" * 72)
    print("CASE 8 summary")
    print("=" * 72)
    print("  - The same physical route shares one reference replay.")
    print("  - A different physical route gets its own replay.")
    print("  - Link-name tuples are kept for audit and are not replay keys.")
    print("  - Origin waiting is added only to that vehicle's CW_z.")
    print("  - Bad input stops without an official result.")
    print("  - A later evaluation does not keep the previous result.")
    print("  - signalized_uxsim, fcfs, batch, and tvt_mp use the same calculation.")
    print("  - true_vot here is a verification coefficient, not the formal ACWWT unit.")
    print("  - Production implementation has not started.")
    print("  - This script writes no files.")


CASE8_CASE_NOTES: tuple[Case8CaseNote, ...] = (
    Case8CaseNote(
        name="CASE 8A: same physical route is shared",
        purpose="Several finished vehicles with the same physical route share one replay.",
        expected_relation="one physical key, one replay, the rest reuse; four method names do not change the formula",
    ),
    Case8CaseNote(
        name="CASE 8B: same physics, different link names",
        purpose="Keep more than one link-name tuple for one physical key.",
        expected_relation="one replay, first-seen audit order, an exact repeat is not appended",
    ),
    Case8CaseNote(
        name="CASE 8C: different physical routes stay separate",
        purpose="Separate link order, length, u, and DELTAT.",
        expected_relation="different keys and separate replays; DELTAT uses separate evaluations",
    ),
    Case8CaseNote(
        name="CASE 8D: origin wait changes only CW_z",
        purpose="Match the CASE 5 origin hold on one of two equal physical routes.",
        expected_relation="shared T_min,z, CW_z 0 without the hold and 4 s with the hold",
    ),
    Case8CaseNote(
        name="CASE 8E: bad input does not return an official result",
        purpose="Stop for bad DELTAN, an empty route, an unfinished vehicle, bad length, bad u, bad true_vot, and a missing name.",
        expected_relation="ValueError before an official summary, including before replay when the input is already invalid",
    ),
    Case8CaseNote(
        name="CASE 8F: evaluations do not keep the previous result",
        purpose="Run the same world twice and show that the second state starts empty.",
        expected_relation="distinct dicts, a second replay, no reference World object, no file",
    ),
)


def _run_case8_cases() -> None:
    _validate_case8a()
    _validate_case8b()
    _validate_case8c()
    _validate_case8d()
    _validate_case8e()
    _validate_case8f()
    _print_case8_summary()


def run_static_validation_only() -> None:
    print("Static validation (no World build, no simulation, no file I/O)")
    print("Contract: production unchanged; console-only validation script.")
    print(f"Cases: {len(CASES)}")
    for case in CASES:
        print(f"  - {case.name}")
        print(f"      expected links: {case.expected_link_names}")
        print(
            f"      expected analytical route free-flow time (s): "
            f"{case.expected_route_free_flow_time_s}"
        )
        print(
            f"      expected replay minimum travel time (s): "
            f"{case.expected_replay_minimum_trip_time_s}"
        )
        print(
            f"      expected cumulative waiting time (s): "
            f"{case.expected_cumulative_waiting_time_s}"
        )
    print("Contract:")
    print("  T_min,z is the travel_time of a UXsim reference replay of the same route.")
    print("  sum(length/u) is an analytical reference, not the formal T_min,z.")
    print("  1 + sum(length/u) was falsified by CASE 4.")
    print("  CASE 1-4: actual travel_time matches the replay and CW_z=0.")
    print("  CASE 5: CW_z is only the extra origin wait from capacity_in.")
    print("  production is not modified; this script writes no files.")
    print("  CASE 4 trajectory trace is off unless --case4-trajectory-trace is set.")
    print("Sensitivity cases (no World is built in this mode):")
    print(f"  count: {len(SENSITIVITY_CASES)}")
    print("  CASE 1-5 expectations and checks are unchanged.")
    print("  production is not modified; this script writes no files.")
    print("  CASE 4 trajectory trace is not enabled by the sensitivity cases.")
    for spec in SENSITIVITY_CASES:
        print(f"  - {spec.name}")
        print("      changed:")
        for item in spec.changed_attributes:
            print(f"        - {item}")
        print("      fixed:")
        for item in spec.fixed_attributes:
            print(f"        - {item}")
        if spec.uses_non_binding_capacity:
            print(
                "      capacity policy: set capacity_in and capacity_out to "
                f"NON_BINDING_CAPACITY={NON_BINDING_CAPACITY} "
                "so one vehicle is not delayed by link capacity."
            )
        else:
            print(
                "      capacity policy: leave UXsim default capacity_in and "
                "capacity_out, matching CASE 2."
            )
        print("      actual/reference attributes kept identical:")
        for item in spec.matched_actual_reference_attributes:
            print(f"        - {item}")
        if spec.expects_fixed_replay_seconds is None:
            print("      fixed expected travel_time: none")
        else:
            print(
                "      fixed expected replay travel_time (s): "
                f"{spec.expects_fixed_replay_seconds}"
            )
        print(f"      signature comparison: {spec.signature_comparison}")
    print("Route-signature classes printed after a full run:")
    print("  1. necessary for physical T_min,z")
    print("  2. no effect on physical T_min,z in this trial")
    print("  3. fixed on the reference World to exclude capacity waiting")
    print("  4. not physical, but useful for audit or cache identity")
    print("  5. still unresolved")
    print("  No production cache key is implemented.")
    print("Identity cases (CASE 7G World is not built in this mode):")
    print(f"  count: {len(IDENTITY_CASE_NOTES)}")
    print("  Formal physical key: (float(DELTAT), ((float(length), float(link.u)), ...)).")
    print("  Link order is kept. Floats are not rounded. Link names are not in the physical key.")
    print("  Display text is not used as a dict key.")
    print("  CASE 1-6 expectations and checks are unchanged.")
    print("  production is not modified; this script writes no files.")
    for note in IDENTITY_CASE_NOTES:
        print(f"  - {note.name}")
        print(f"      comparison: {note.comparison}")
        print(f"      expected: {note.expected_relation}")
    print("Sharing cases (CASE 8 worlds are not built in this mode):")
    print(f"  count: {len(CASE8_CASE_NOTES)}")
    print("  Common to signalized UXsim, FCFS, BATCH, and TVT-MP.")
    print("  method_name does not change T_min,z or CW_z.")
    print("  A reference result stores numbers only. It does not store the reference World.")
    print("  Each evaluation creates a new in-memory state.")
    print("  CASE 1-7 expectations and checks are unchanged.")
    print("  production is not modified.")
    print("  tests are not modified.")
    print("  this script writes no files.")
    for note in CASE8_CASE_NOTES:
        print(f"  - {note.name}")
        print(f"      purpose: {note.purpose}")
        print(f"      expected: {note.expected_relation}")
    print("Static validation OK")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate UXsim single-vehicle network-wide waiting time basis "
            "for ACWT/ACWWT (no output files)."
        )
    )
    parser.add_argument(
        "--static-validate-only",
        action="store_true",
        help="Print static contract checks only; no simulation.",
    )
    parser.add_argument(
        "--case4-trajectory-trace",
        action="store_true",
        help="Print the CASE 4 boundary trajectory trace. Off by default.",
    )
    args = parser.parse_args()

    if args.static_validate_only:
        run_static_validation_only()
        return 0

    for case in CASES:
        _validate_vehicle_case(case, args.case4_trajectory_trace)

    sensitivity_results = []
    for spec in SENSITIVITY_CASES:
        sensitivity_results.append(_validate_sensitivity_case(spec))
    _print_signature_sensitivity_summary(sensitivity_results)
    _run_identity_cases()
    _run_case8_cases()

    print("")
    print("All cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
