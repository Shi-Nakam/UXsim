# Synthetic fixture. These networks are built inside this file so a full
# UXsim run can be compared with itself. They are not a field network.
#
# After the common-seed change, origin choice, in-trip choice, and ordinary
# merge do not read the sequential W.rng stream. Two Worlds with the same
# network, the same vehicle plan, and the same explicit seed must therefore
# finish with the same traffic results even if one W.rng is advanced before
# the run. The expected result is the other World's result.
#
# This file does not import the old W.rng.choice diagnostics, does not ask
# the production route-selection helper for an expected link, and does not
# read a keyed uniform to decide a link. Passing does not depend on counting
# W.rng.choice calls or on inspecting source text.
#
# duo_noise is 0 so a pre-run W.rng advance cannot change link costs through
# shortest-path noise. hard_deterministic_mode stays False. Nodes keep the
# default single signal phase, which does not cycle. Order control is left
# off. No vehicle is given a specified route.
#
# Run from the repository root:
#   python tests_common_seed_rng_full_simulation_invariance.py

from uxsim import Vehicle
from uxsim import World


_WORLD_RNG_ADVANCE_COUNT = 4


def _generator_state(generator):
    return generator.bit_generator.state


def _new_world(name, random_seed):
    # Synthetic small world. Noise is off so W.rng cannot move link costs.
    # The mode is still the ordinary non-hard-deterministic mode.
    return World(
        name=name,
        deltan=1,
        tmax=160,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=random_seed,
        hard_deterministic_mode=False,
        duo_noise=0.0,
        reaction_time=1,
    )


def _advance_world_rng_only(W):
    """Draw several W.rng values. Leave the other generators and entropy."""
    entropy_before = W._common_seed_rng_internal_entropy
    merge_state_before = _generator_state(W.normal_merge_rng)
    rng_before = _generator_state(W.rng)
    draw_index = 0
    while draw_index < _WORLD_RNG_ADVANCE_COUNT:
        W.rng.random()
        draw_index += 1
    rng_after = _generator_state(W.rng)
    assert rng_after != rng_before
    assert W._common_seed_rng_internal_entropy == entropy_before
    assert _generator_state(W.normal_merge_rng) == merge_state_before
    return rng_before, rng_after


def _add_link(W, name, start_node, end_node, merge_priority=1):
    W.addLink(
        name,
        start_node,
        end_node,
        length=80,
        free_flow_speed=20,
        number_of_lanes=1,
        merge_priority=merge_priority,
    )


def _build_two_route_network(W):
    # Origin has two outlinks, so departure can be a probabilistic choice.
    # Each fork has two outlinks to the same destination, so the trip can
    # make a second probabilistic choice before it ends.
    W.addNode("orig", 0, 0)
    W.addNode("east_fork", 1, 1)
    W.addNode("west_fork", 1, -1)
    W.addNode("dest", 2, 0)
    _add_link(W, "east_out", "orig", "east_fork")
    _add_link(W, "west_out", "orig", "west_fork")
    _add_link(W, "east_north", "east_fork", "dest")
    _add_link(W, "east_south", "east_fork", "dest")
    _add_link(W, "west_north", "west_fork", "dest")
    _add_link(W, "west_south", "west_fork", "dest")


def _build_merge_network(W):
    # Two approaches reach one outlink together, so ordinary merge has more
    # than one waiting vehicle to choose from.
    W.addNode("orig_low", 0, 0)
    W.addNode("orig_high", 0, 1)
    W.addNode("merge", 1, 0)
    W.addNode("dest", 2, 0)
    _add_link(W, "in_low", "orig_low", "merge", merge_priority=1)
    _add_link(W, "in_high", "orig_high", "merge", merge_priority=3)
    _add_link(W, "out", "merge", "dest")


def _assert_ordinary_fixture(W):
    assert W.hard_deterministic_mode is False
    for node in W.NODES:
        assert node.order_control_type == "none"
        assert node.order_control_eligible is False
    for vehicle in W.VEHICLES.values():
        assert vehicle.specified_route is None


def _add_two_route_vehicles(W):
    # Departures are far enough apart that the three vehicles do not queue.
    W.addVehicle("orig", "dest", 0, name="veh_0")
    W.addVehicle("orig", "dest", 25, name="veh_1")
    W.addVehicle("orig", "dest", 50, name="veh_2")
    _assert_ordinary_fixture(W)


def _add_merge_vehicles(W):
    W.addVehicle("orig_low", "dest", 0, name="veh_low")
    W.addVehicle("orig_high", "dest", 0, name="veh_high")
    _assert_ordinary_fixture(W)


def _log_t_link_rows(vehicle):
    rows = []
    for entry in vehicle.log_t_link:
        clock = entry[0]
        place = entry[1]
        if place == "home" or place == "end":
            place_name = place
        else:
            place_name = place.name
        rows.append((clock, place_name))
    return tuple(rows)


def _traveled_link_names(vehicle):
    route, _entry_times = vehicle.traveled_route(
        include_arrival_time=False,
        include_departure_time=False,
    )
    return tuple(route.links_name)


def _completion_order(W):
    ranked = []
    for vehicle in W.VEHICLES.values():
        ranked.append((vehicle.arrival_time, vehicle.name))
    ranked.sort()
    names = []
    for _arrival_time, name in ranked:
        names.append(name)
    return tuple(names)


def _traffic_snapshot(W):
    vehicle_rows = {}
    total_travel_time = 0.0
    total_distance_traveled = 0.0
    completed_trips = 0
    last_completed_trip_time = None
    for name, vehicle in W.VEHICLES.items():
        total_distance_traveled += vehicle.distance_traveled
        if vehicle.state == "end":
            completed_trips += 1
            total_travel_time += vehicle.travel_time
            completed_trip_time = vehicle.arrival_time * vehicle.W.DELTAT
            if (
                last_completed_trip_time is None
                or completed_trip_time > last_completed_trip_time
            ):
                last_completed_trip_time = completed_trip_time
        vehicle_rows[name] = {
            "state": vehicle.state,
            "departure_time": vehicle.departure_time,
            "arrival_time": vehicle.arrival_time,
            "travel_time": vehicle.travel_time,
            "destination_name": vehicle.dest.name,
            "traveled_route_link_names": _traveled_link_names(vehicle),
            "log_t_link": _log_t_link_rows(vehicle),
        }
    total_vehicles = len(W.VEHICLES)
    unfinished_trips = total_vehicles - completed_trips
    if completed_trips == 0:
        average_travel_time = None
    else:
        average_travel_time = total_travel_time / completed_trips
    return {
        "vehicle_names": tuple(W.VEHICLES.keys()),
        "vehicles": vehicle_rows,
        "completion_order": _completion_order(W),
        "total_vehicles": total_vehicles,
        "completed_trips": completed_trips,
        "unfinished_trips": unfinished_trips,
        "total_travel_time": total_travel_time,
        "average_travel_time": average_travel_time,
        "total_distance_traveled": total_distance_traveled,
        "last_completed_trip_time": last_completed_trip_time,
    }


def _origin_attempt_total(W):
    total = 0
    for vehicle in W.VEHICLES.values():
        total += vehicle.origin_route_choice_attempt_count
    return total


def _ledger_total(ledger, world_name):
    total = 0
    for increase in ledger[world_name].values():
        total += increase
    return total


def _exec_both_with_in_trip_ledger(control, perturbed):
    """Count in-trip attempt increases without keeping the production choice.

    The current counter is reset when a vehicle enters another link, so the
    value left at the end of the run is not the trip total. This ledger
    stores only the increase across each real call. The original method is
    called once and its chosen link is left as it is.
    """
    ledger = {control.name: {}, perturbed.name: {}}
    original = Vehicle.route_next_link_choice

    def wrapped(vehicle):
        before = vehicle.current_link_route_choice_attempt_count
        original(vehicle)
        after = vehicle.current_link_route_choice_attempt_count
        increase = after - before
        if increase > 0:
            by_vehicle = ledger[vehicle.W.name]
            already = by_vehicle.get(vehicle.name, 0)
            by_vehicle[vehicle.name] = already + increase

    Vehicle.route_next_link_choice = wrapped
    try:
        control.exec_simulation()
        perturbed.exec_simulation()
    finally:
        Vehicle.route_next_link_choice = original
    assert Vehicle.route_next_link_choice is original
    return ledger


def _out_link_passage(W, out_link_name):
    passages = []
    for vehicle in W.VEHICLES.values():
        for clock, place_name in _log_t_link_rows(vehicle):
            if place_name == out_link_name:
                passages.append((clock, vehicle.name))
                break
    passages.sort()
    return tuple(passages)


def _link_entry_clock(vehicle, link_name):
    for clock, place_name in _log_t_link_rows(vehicle):
        if place_name == link_name:
            return clock
    raise AssertionError(f"{vehicle.name} did not enter {link_name}")


def test_two_route_full_simulation_matches_after_world_rng_advance():
    random_seed = 17
    control = _new_world("invariance_two_route_control", random_seed)
    perturbed = _new_world("invariance_two_route_perturbed", random_seed)
    _build_two_route_network(control)
    _build_two_route_network(perturbed)
    _add_two_route_vehicles(control)
    _add_two_route_vehicles(perturbed)

    assert (
        control._common_seed_rng_internal_entropy
        == perturbed._common_seed_rng_internal_entropy
    )
    assert _generator_state(control.normal_merge_rng) == _generator_state(
        perturbed.normal_merge_rng
    )
    _rng_before, rng_after = _advance_world_rng_only(perturbed)
    assert rng_after != _rng_before
    assert _generator_state(control.rng) != _generator_state(perturbed.rng)
    assert (
        control._common_seed_rng_internal_entropy
        == perturbed._common_seed_rng_internal_entropy
    )
    assert _generator_state(control.normal_merge_rng) == _generator_state(
        perturbed.normal_merge_rng
    )

    ledger = _exec_both_with_in_trip_ledger(control, perturbed)

    assert _traffic_snapshot(control) == _traffic_snapshot(perturbed)
    assert _traffic_snapshot(control)["unfinished_trips"] == 0
    assert _traffic_snapshot(control)["completed_trips"] == 3
    assert _origin_attempt_total(control) > 0
    assert _origin_attempt_total(perturbed) > 0
    assert _ledger_total(ledger, control.name) > 0
    assert _ledger_total(ledger, perturbed.name) > 0


def test_world_copy_preserves_route_choice_counts_and_normal_merge_state():
    W = _new_world("invariance_copy", 31)
    _build_two_route_network(W)
    _add_two_route_vehicles(W)
    finished = W.exec_simulation(duration_t2=12)
    assert finished == 0

    copied = W.copy()
    assert copied is not W
    assert (
        copied._common_seed_rng_internal_entropy
        == W._common_seed_rng_internal_entropy
    )

    saw_link_entry = False
    for name, vehicle in W.VEHICLES.items():
        copied_vehicle = copied.VEHICLES[name]
        assert (
            copied_vehicle.link_entry_count_by_link_name
            == vehicle.link_entry_count_by_link_name
        )
        assert (
            copied_vehicle.link_entry_count_by_link_name
            is not vehicle.link_entry_count_by_link_name
        )
        assert (
            copied_vehicle.origin_route_choice_attempt_count
            == vehicle.origin_route_choice_attempt_count
        )
        assert (
            copied_vehicle.current_link_route_choice_attempt_count
            == vehicle.current_link_route_choice_attempt_count
        )
        for _link_name, entry_count in vehicle.link_entry_count_by_link_name.items():
            if entry_count >= 1:
                saw_link_entry = True
    assert saw_link_entry is True

    assert copied.normal_merge_rng is not W.normal_merge_rng
    assert _generator_state(copied.normal_merge_rng) == _generator_state(
        W.normal_merge_rng
    )
    original_merge_state = _generator_state(W.normal_merge_rng)
    copied.normal_merge_rng.random()
    assert _generator_state(copied.normal_merge_rng) != _generator_state(
        W.normal_merge_rng
    )
    assert _generator_state(W.normal_merge_rng) == original_merge_state


def test_ordinary_merge_full_simulation_matches_after_world_rng_advance():
    random_seed = 29
    control = _new_world("invariance_merge_control", random_seed)
    perturbed = _new_world("invariance_merge_perturbed", random_seed)
    _build_merge_network(control)
    _build_merge_network(perturbed)
    _add_merge_vehicles(control)
    _add_merge_vehicles(perturbed)

    merge_state_before = _generator_state(control.normal_merge_rng)
    assert merge_state_before == _generator_state(perturbed.normal_merge_rng)
    assert (
        control._common_seed_rng_internal_entropy
        == perturbed._common_seed_rng_internal_entropy
    )
    _advance_world_rng_only(perturbed)
    assert _generator_state(control.rng) != _generator_state(perturbed.rng)
    assert _generator_state(control.normal_merge_rng) == _generator_state(
        perturbed.normal_merge_rng
    )

    control.exec_simulation()
    perturbed.exec_simulation()

    assert _traffic_snapshot(control) == _traffic_snapshot(perturbed)
    assert _traffic_snapshot(control)["unfinished_trips"] == 0
    control_passage = _out_link_passage(control, "out")
    perturbed_passage = _out_link_passage(perturbed, "out")
    assert control_passage == perturbed_passage
    assert len(control_passage) == 2
    assert control_passage[0][0] != control_passage[1][0]

    low_entry = _link_entry_clock(control.VEHICLES["veh_low"], "in_low")
    high_entry = _link_entry_clock(control.VEHICLES["veh_high"], "in_high")
    assert low_entry == high_entry

    merge_state_after = _generator_state(control.normal_merge_rng)
    assert merge_state_after != merge_state_before
    assert merge_state_after == _generator_state(perturbed.normal_merge_rng)
    assert _generator_state(control.rng) != _generator_state(perturbed.rng)


TESTS = [
    test_two_route_full_simulation_matches_after_world_rng_advance,
    test_world_copy_preserves_route_choice_counts_and_normal_merge_state,
    test_ordinary_merge_full_simulation_matches_after_world_rng_advance,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(
        "Common seed/RNG full-simulation invariance tests passed "
        f"({len(TESTS)} tests)."
    )
