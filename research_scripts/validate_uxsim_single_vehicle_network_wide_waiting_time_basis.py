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


def _make_world(case_name: str, tmax_seconds: float = 600.0) -> World:
    return World(
        name=f"validate_network_wide_waiting_{case_name}",
        deltan=1,
        reaction_time=1,
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
) -> World:
    """Fresh single-vehicle world. Same link sequence, no extra waiting causes."""
    if len(specs) == 0:
        raise RuntimeError("Cannot build a reference world from an empty route.")
    world = _make_world("reference_replay")
    node_count = len(specs) + 1
    for index in range(node_count):
        world.addNode(f"ref_n{index}", float(index), 0.0, signal=[0])
    link_names: list[str] = []
    for index, spec in enumerate(specs):
        world.addLink(
            spec.name,
            f"ref_n{index}",
            f"ref_n{index + 1}",
            length=spec.length,
            free_flow_speed=spec.free_flow_speed,
            jam_density=spec.jam_density,
            number_of_lanes=spec.number_of_lanes,
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


def _run_reference_minimum_trip_time(specs: Sequence[RouteLinkSpec]):
    world = _build_reference_world_from_actual_route(specs)
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

    print("")
    print("All cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
