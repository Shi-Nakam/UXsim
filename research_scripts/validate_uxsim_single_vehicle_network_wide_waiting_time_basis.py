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
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from typing import Callable, Sequence

from uxsim import World

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

    print("")
    print("All cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
