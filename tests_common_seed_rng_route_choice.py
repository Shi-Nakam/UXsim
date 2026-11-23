# Origin and in-trip route choice use one keyed uniform per probabilistic event.
#
# Production-selection tests compute the expected link in this file from an
# explicit key and the cumulative-probability rule. They do not ask the
# production category helper for that expectation. Separate tests call the
# helper directly for empty lists, one candidate, and invalid values.
# No numeric uniform is hard-coded for a World event. The same explicit key
# can be recomputed in Terminal through keyed_uniform_value.
#
# Run from the repository root:
#   python tests_common_seed_rng_route_choice.py

import math

from uxsim import World
from uxsim.common_seed_rng_keyed_uniform import keyed_uniform_value
from uxsim.common_seed_rng_route_choice import (
    IN_TRIP_ROUTE_CHOICE_DOMAIN,
    ORIGIN_ROUTE_CHOICE_DOMAIN,
    select_route_choice_candidate,
)


def _prepare(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _new_world(name, hard_deterministic_mode=False):
    W = World(
        name=name,
        deltan=1,
        tmax=80,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
        hard_deterministic_mode=hard_deterministic_mode,
    )
    return W


def _rng_state(W):
    return (
        W.rng.bit_generator.state,
        W.order_control_rng.bit_generator.state,
    )


def _assert_value_error(function):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def _expected_link(candidate_links, weights, uniform_value):
    """Same category rule as production, written out for an independent check."""
    total_weight = 0.0
    for weight in weights:
        total_weight += weight
    if total_weight > 0.0:
        cumulative_probability = 0.0
        for candidate_link, weight in zip(candidate_links, weights):
            cumulative_probability += weight / total_weight
            if uniform_value < cumulative_probability:
                return candidate_link
        return candidate_links[-1]
    equal_index = int(uniform_value * len(candidate_links))
    if equal_index >= len(candidate_links):
        equal_index = len(candidate_links) - 1
    return candidate_links[equal_index]


def _add_origin_fork(W):
    W.addNode("orig", 0, 0)
    W.addNode("east", 1, 0)
    W.addNode("north", 0, 1)
    W.addLink("east_link", "orig", "east", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("north_link", "orig", "north", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)


def _queue_at_origin(W, vehicle):
    vehicle.state = "wait"
    W.get_node("orig").generation_queue.append(vehicle)


def _set_origin_weights(vehicle, W, east_weight, north_weight):
    vehicle.route_pref[W.get_link("east_link").id] = east_weight
    vehicle.route_pref[W.get_link("north_link").id] = north_weight


def _add_junction(W):
    W.addNode("orig", 0, 0)
    W.addNode("junction", 1, 0)
    W.addNode("dest", 2, 0)
    W.addNode("side", 1, 1)
    W.addLink("in_link", "orig", "junction", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("out_dest", "junction", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("out_side", "junction", "side", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)


def _place_on_in_link(W, vehicle, entry_count):
    in_link = W.get_link("in_link")
    vehicle.link = in_link
    vehicle.state = "run"
    vehicle.x = in_link.length
    vehicle.link_entry_count_by_link_name = {"in_link": entry_count}
    in_link.vehicles.append(vehicle)


def _set_junction_weights(vehicle, W, dest_weight, side_weight):
    vehicle.route_pref[W.get_link("out_dest").id] = dest_weight
    vehicle.route_pref[W.get_link("out_side").id] = side_weight


def test_origin_and_in_trip_domains_are_distinct_fixed_strings():
    assert ORIGIN_ROUTE_CHOICE_DOMAIN == "origin_route_choice"
    assert IN_TRIP_ROUTE_CHOICE_DOMAIN == "in_trip_route_choice"
    assert ORIGIN_ROUTE_CHOICE_DOMAIN != IN_TRIP_ROUTE_CHOICE_DOMAIN
    W = _new_world("route_choice_domains")
    _add_origin_fork(W)
    entropy = W._common_seed_rng_internal_entropy
    origin_key = ("veh_domain", "orig", 0)
    in_trip_key = ("veh_domain", "in_link", 1, 0)
    origin_uniform = keyed_uniform_value(
        entropy,
        "origin_route_choice",
        origin_key,
    )
    in_trip_uniform = keyed_uniform_value(
        entropy,
        "in_trip_route_choice",
        in_trip_key,
    )
    same_parts_other_domain = keyed_uniform_value(
        entropy,
        "in_trip_route_choice",
        origin_key,
    )
    assert origin_uniform != same_parts_other_domain
    assert 0.0 <= origin_uniform < 1.0
    assert 0.0 <= in_trip_uniform < 1.0


def test_origin_zero_candidates_does_not_draw_or_increment_attempt():
    W = _new_world("route_choice_origin_zero")
    _add_origin_fork(W)
    vehicle = W.addVehicle(
        "orig",
        "east",
        0,
        name="veh_origin_zero",
        links_prefer=["east_link"],
        links_avoid=["east_link"],
    )
    _queue_at_origin(W, vehicle)
    rng_before = _rng_state(W)
    _assert_value_error(W.get_node("orig").generate)
    assert vehicle.origin_route_choice_attempt_count == 0
    assert vehicle.link is None
    assert vehicle in W.get_node("orig").generation_queue
    assert _rng_state(W) == rng_before


def test_origin_one_candidate_selects_without_keyed_draw():
    W = _new_world("route_choice_origin_one")
    W.addNode("orig", 0, 0)
    W.addNode("dest", 1, 0)
    W.addLink("only_link", "orig", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("orig", "dest", 0, name="veh_origin_one")
    _queue_at_origin(W, vehicle)
    rng_before = _rng_state(W)
    W.get_node("orig").generate()
    assert vehicle.link is W.get_link("only_link")
    assert vehicle.origin_route_choice_attempt_count == 0
    assert _rng_state(W) == rng_before

    W2 = _new_world("route_choice_origin_one_again")
    W2.addNode("orig", 0, 0)
    W2.addNode("dest", 1, 0)
    W2.addLink("only_link", "orig", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W2)
    vehicle2 = W2.addVehicle("orig", "dest", 0, name="veh_origin_one")
    _queue_at_origin(W2, vehicle2)
    W2.get_node("orig").generate()
    assert vehicle2.link.name == "only_link"
    assert vehicle2.origin_route_choice_attempt_count == 0


def test_origin_two_candidates_uses_current_attempt_and_not_world_rng():
    W = _new_world("route_choice_origin_two")
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_origin_two")
    _set_origin_weights(vehicle, W, 3.0, 1.0)
    _queue_at_origin(W, vehicle)
    candidate_links = [W.get_link("east_link"), W.get_link("north_link")]
    weights = [3.0, 1.0]
    uniform_value = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "origin_route_choice",
        ("veh_origin_two", "orig", 0),
    )
    expected_link = _expected_link(candidate_links, weights, uniform_value)
    rng_before = _rng_state(W)
    W.get_node("orig").generate()
    assert vehicle.link is expected_link
    assert vehicle.origin_route_choice_attempt_count == 1
    assert _rng_state(W) == rng_before


def test_origin_zero_preference_uses_equal_categories():
    W = _new_world("route_choice_origin_equal")
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_origin_equal")
    _set_origin_weights(vehicle, W, 0.0, 0.0)
    _queue_at_origin(W, vehicle)
    candidate_links = [W.get_link("east_link"), W.get_link("north_link")]
    uniform_value = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "origin_route_choice",
        ("veh_origin_equal", "orig", 0),
    )
    expected_link = _expected_link(candidate_links, [0.0, 0.0], uniform_value)
    W.get_node("orig").generate()
    assert vehicle.link is expected_link
    assert vehicle.origin_route_choice_attempt_count == 1


def test_origin_rejected_entry_keeps_the_consumed_attempt():
    W = _new_world("route_choice_origin_rejected")
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_origin_rejected")
    _set_origin_weights(vehicle, W, 3.0, 1.0)
    _queue_at_origin(W, vehicle)
    W.get_link("east_link").capacity_in_remain = 0
    W.get_link("north_link").capacity_in_remain = 0
    rng_before = _rng_state(W)
    W.get_node("orig").generate()
    assert vehicle.link is None
    assert vehicle.origin_route_choice_attempt_count == 1
    assert vehicle in W.get_node("orig").generation_queue
    assert _rng_state(W) == rng_before

    W.get_link("east_link").capacity_in_remain = 100
    W.get_link("north_link").capacity_in_remain = 100
    candidate_links = [W.get_link("east_link"), W.get_link("north_link")]
    uniform_value = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "origin_route_choice",
        ("veh_origin_rejected", "orig", 1),
    )
    expected_link = _expected_link(candidate_links, [3.0, 1.0], uniform_value)
    W.get_node("orig").generate()
    assert vehicle.link is expected_link
    assert vehicle.origin_route_choice_attempt_count == 2


def test_origin_negative_preference_does_not_increment_attempt():
    W = _new_world("route_choice_origin_negative")
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_origin_negative")
    _set_origin_weights(vehicle, W, -1.0, 1.0)
    _queue_at_origin(W, vehicle)
    rng_before = _rng_state(W)
    _assert_value_error(W.get_node("orig").generate)
    assert vehicle.origin_route_choice_attempt_count == 0
    assert vehicle.link is None
    assert _rng_state(W) == rng_before


def test_in_trip_dead_end_sets_no_next_link_without_an_attempt():
    W = _new_world("route_choice_dead_end")
    W.addNode("orig", 0, 0)
    W.addNode("dangling", 1, 0)
    W.addNode("elsewhere", 2, 0)
    W.addLink("dead_link", "orig", "dangling", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("orig", "elsewhere", 0, name="veh_dead_end")
    dead_link = W.get_link("dead_link")
    vehicle.link = dead_link
    vehicle.state = "run"
    rng_before = _rng_state(W)
    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is None
    assert vehicle.current_link_route_choice_attempt_count == 0
    assert vehicle.link_entry_count_by_link_name == {}
    assert _rng_state(W) == rng_before


def test_in_trip_zero_final_candidates_does_not_increment_attempt():
    W = _new_world("route_choice_in_trip_zero")
    _add_junction(W)
    vehicle = W.addVehicle(
        "orig",
        "dest",
        0,
        name="veh_in_trip_zero",
        links_prefer=["out_dest"],
        links_avoid=["out_dest"],
    )
    _place_on_in_link(W, vehicle, 1)
    previous_route_next_link = W.get_link("out_dest")
    vehicle.route_next_link = previous_route_next_link
    rng_before = _rng_state(W)
    _assert_value_error(vehicle.route_next_link_choice)
    assert vehicle.route_next_link is previous_route_next_link
    assert vehicle.current_link_route_choice_attempt_count == 0
    assert vehicle.link_entry_count_by_link_name == {"in_link": 1}
    assert vehicle.link is W.get_link("in_link")
    assert _rng_state(W) == rng_before


def test_in_trip_one_candidate_does_not_increment_attempt():
    W = _new_world("route_choice_in_trip_one")
    W.addNode("orig", 0, 0)
    W.addNode("mid", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink("first", "orig", "mid", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("second", "mid", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("orig", "dest", 0, name="veh_in_trip_one")
    first = W.get_link("first")
    vehicle.link = first
    vehicle.state = "run"
    vehicle.link_entry_count_by_link_name = {"first": 1}
    rng_before = _rng_state(W)
    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is W.get_link("second")
    assert vehicle.current_link_route_choice_attempt_count == 0
    assert vehicle.link_entry_count_by_link_name == {"first": 1}
    assert _rng_state(W) == rng_before


def test_in_trip_two_candidates_uses_link_name_entry_count_and_attempt():
    W = _new_world("route_choice_in_trip_two")
    _add_junction(W)
    vehicle = W.addVehicle("orig", "dest", 0, name="veh_in_trip_two")
    _place_on_in_link(W, vehicle, 1)
    _set_junction_weights(vehicle, W, 1.0, 3.0)
    candidate_links = [W.get_link("out_dest"), W.get_link("out_side")]
    uniform_value = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "in_trip_route_choice",
        ("veh_in_trip_two", "in_link", 1, 0),
    )
    expected_link = _expected_link(candidate_links, [1.0, 3.0], uniform_value)
    rng_before = _rng_state(W)
    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is expected_link
    assert vehicle.current_link_route_choice_attempt_count == 1
    assert vehicle.link_entry_count_by_link_name == {"in_link": 1}
    assert vehicle.link is W.get_link("in_link")
    assert vehicle.origin_route_choice_attempt_count == 0
    assert _rng_state(W) == rng_before

    # Still on the same link, so the next call is another attempt, not a reset.
    next_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "in_trip_route_choice",
        ("veh_in_trip_two", "in_link", 1, 1),
    )
    next_expected = _expected_link(candidate_links, [1.0, 3.0], next_uniform)
    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is next_expected
    assert vehicle.current_link_route_choice_attempt_count == 2
    assert vehicle.link_entry_count_by_link_name == {"in_link": 1}


def test_in_trip_missing_or_zero_entry_count_stops_without_increment():
    W = _new_world("route_choice_missing_count")
    _add_junction(W)
    missing = W.addVehicle("orig", "dest", 0, name="veh_missing_count")
    _place_on_in_link(W, missing, 1)
    missing.link_entry_count_by_link_name = {}
    _set_junction_weights(missing, W, 1.0, 1.0)
    previous_route_next_link = W.get_link("out_dest")
    missing.route_next_link = previous_route_next_link
    rng_before = _rng_state(W)
    _assert_value_error(missing.route_next_link_choice)
    assert missing.current_link_route_choice_attempt_count == 0
    assert missing.route_next_link is previous_route_next_link
    assert _rng_state(W) == rng_before

    zero = W.addVehicle("orig", "dest", 0, name="veh_zero_count")
    _place_on_in_link(W, zero, 0)
    _set_junction_weights(zero, W, 1.0, 1.0)
    zero_previous_route_next_link = W.get_link("out_dest")
    zero.route_next_link = zero_previous_route_next_link
    _assert_value_error(zero.route_next_link_choice)
    assert zero.current_link_route_choice_attempt_count == 0
    assert zero.link_entry_count_by_link_name == {"in_link": 0}
    assert zero.route_next_link is zero_previous_route_next_link


def _move_through_node(vehicle, inlink, outlink):
    """Move one vehicle with the ordinary physical-transfer helper.

    The caller chooses the outlink. This does not call route choice.
    The vehicle is placed at the head of inlink, then
    Node._transfer_one_vehicle_between_links records the outlink entry
    and resets the in-trip attempt.
    """
    node = inlink.end_node
    if vehicle in inlink.vehicles:
        inlink.vehicles.remove(vehicle)
    inlink.vehicles.appendleft(vehicle)
    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = inlink.length
    vehicle.v = inlink.u
    vehicle.move_remain = 0
    vehicle.leader = None
    vehicle.follower = None
    vehicle.link_arrival_time = 0.0
    vehicle.route_next_link = outlink
    if vehicle not in node.incoming_vehicles:
        node.incoming_vehicles.append(vehicle)
    inlink.capacity_out_remain = 100
    outlink.capacity_in_remain = 100
    node._transfer_one_vehicle_between_links(vehicle, inlink, outlink)


def test_prefer_uses_link_name_order_not_registration_order():
    # Registration order at orig is z_link, then a_link.
    # Link-name order is a_link, then z_link.
    # Prefer contains both, so production sorts the two by name.
    # Equal weights make those two orders select opposite links for every
    # uniform in [0, 1). In-trip uses the same prefer sort.
    W = _new_world("route_choice_name_order")
    W.addNode("orig", 0, 0)
    W.addNode("zed", 1, 0)
    W.addNode("aye", 0, 1)
    W.addLink("z_link", "orig", "zed", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("a_link", "orig", "aye", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle(
        "orig",
        "zed",
        0,
        name="veh_name_order",
        links_prefer=["z_link", "a_link"],
    )
    registration_order = [W.get_link("z_link"), W.get_link("a_link")]
    name_order = [W.get_link("a_link"), W.get_link("z_link")]
    vehicle.route_pref[registration_order[0].id] = 1.0
    vehicle.route_pref[registration_order[1].id] = 1.0
    _queue_at_origin(W, vehicle)
    uniform_value = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "origin_route_choice",
        ("veh_name_order", "orig", 0),
    )
    weights = [1.0, 1.0]
    registration_expected = _expected_link(registration_order, weights, uniform_value)
    name_expected = _expected_link(name_order, weights, uniform_value)
    assert registration_expected is not name_expected
    rng_before = _rng_state(W)
    W.get_node("orig").generate()
    assert vehicle.link is name_expected
    assert vehicle.origin_route_choice_attempt_count == 1
    assert _rng_state(W) == rng_before


def test_route_choice_candidate_helper_rejects_invalid_weights_and_uniforms():
    first = "first_link"
    second = "second_link"
    _assert_value_error(
        lambda: select_route_choice_candidate([], [1.0], 0.0)
    )
    # One candidate is that link. The helper does not read the weight or the
    # uniform. That is the no-draw contract for a single remaining link.
    assert select_route_choice_candidate([first], [True], 1.0) is first
    assert select_route_choice_candidate([first], [float("nan")], True) is first

    _assert_value_error(
        lambda: select_route_choice_candidate([first, second], [1.0], 0.0)
    )
    _assert_value_error(
        lambda: select_route_choice_candidate(
            [first, second],
            [1.0, 1.0, 1.0],
            0.0,
        )
    )

    invalid_weights = (
        -1.0,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        False,
    )
    for invalid_weight in invalid_weights:
        _assert_value_error(
            lambda weight=invalid_weight: select_route_choice_candidate(
                [first, second],
                [weight, 1.0],
                0.0,
            )
        )

    invalid_uniforms = (-0.1, 1.0, float("nan"), True, 0)
    for invalid_uniform in invalid_uniforms:
        _assert_value_error(
            lambda uniform=invalid_uniform: select_route_choice_candidate(
                [first, second],
                [1.0, 1.0],
                uniform,
            )
        )


def test_route_choice_candidate_helper_handles_boundaries():
    first = "first_link"
    second = "second_link"
    third = "third_link"
    # Positive total. 0.0 selects the first link. The boundary of equal
    # weights is 0.5: the draw uses strict <, so 0.5 selects the second.
    assert select_route_choice_candidate(
        [first, second],
        [1.0, 3.0],
        0.0,
    ) is first
    just_below_half = math.nextafter(0.5, 0.0)
    assert select_route_choice_candidate(
        [first, second],
        [1.0, 1.0],
        just_below_half,
    ) is first
    assert select_route_choice_candidate(
        [first, second],
        [1.0, 1.0],
        0.5,
    ) is second

    # Total 0 is an equal-category draw in candidate order.
    # 0.0, 0.5, and 0.9 land in slots 0, 1, and 2.
    assert select_route_choice_candidate(
        [first, second, third],
        [0.0, 0.0, 0.0],
        0.0,
    ) is first
    assert select_route_choice_candidate(
        [first, second, third],
        [0.0, 0.0, 0.0],
        0.5,
    ) is second
    assert select_route_choice_candidate(
        [first, second, third],
        [0.0, 0.0, 0.0],
        0.9,
    ) is third
    # A positive total already reaches cumulative 1 for ordinary weights.
    # The last-candidate remainder for rounding that never crosses the
    # uniform is not forced by these values.


def test_loop_reentry_changes_the_in_trip_uniform():
    # feeder -> loop_in -> hop -> return_feeder -> loop_in.
    # At n2, registration order is hop then spur. Both stay candidates.
    W = _new_world("route_choice_loop_count")
    W.addNode("feeder_start", 0, 0)
    W.addNode("n1", 1, 0)
    W.addNode("n2", 2, 0)
    W.addNode("n3", 2, 1)
    W.addNode("spur_end", 3, 0)
    W.addLink("feeder", "feeder_start", "n1", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("loop_in", "n1", "n2", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("hop", "n2", "n3", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("spur", "n2", "spur_end", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("return_feeder", "n3", "n1", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("feeder_start", "spur_end", 0, name="veh_loop_count")
    feeder = W.get_link("feeder")
    loop_in = W.get_link("loop_in")
    hop = W.get_link("hop")
    spur = W.get_link("spur")
    return_feeder = W.get_link("return_feeder")
    candidate_links = [hop, spur]
    vehicle.route_pref[hop.id] = 1.0
    vehicle.route_pref[spur.id] = 1.0

    _move_through_node(vehicle, feeder, loop_in)
    assert vehicle.link is loop_in
    assert vehicle.link_entry_count_by_link_name == {"loop_in": 1}
    assert vehicle.current_link_route_choice_attempt_count == 0
    assert vehicle.origin_route_choice_attempt_count == 0

    first_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "in_trip_route_choice",
        ("veh_loop_count", "loop_in", 1, 0),
    )
    second_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "in_trip_route_choice",
        ("veh_loop_count", "loop_in", 2, 0),
    )
    assert first_uniform != second_uniform
    rng_before = _rng_state(W)
    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is _expected_link(
        candidate_links,
        [1.0, 1.0],
        first_uniform,
    )
    assert vehicle.current_link_route_choice_attempt_count == 1
    assert vehicle.link_entry_count_by_link_name == {"loop_in": 1}
    assert _rng_state(W) == rng_before

    # The choice above may select spur. The return path uses hop so the
    # vehicle can reenter loop_in. The transfer helper does not choose.
    _move_through_node(vehicle, loop_in, hop)
    assert vehicle.link is hop
    assert vehicle.link_entry_count_by_link_name["loop_in"] == 1
    assert vehicle.link_entry_count_by_link_name["hop"] == 1
    assert vehicle.current_link_route_choice_attempt_count == 0

    _move_through_node(vehicle, hop, return_feeder)
    assert vehicle.link is return_feeder
    assert vehicle.link_entry_count_by_link_name["return_feeder"] == 1
    assert vehicle.current_link_route_choice_attempt_count == 0

    _move_through_node(vehicle, return_feeder, loop_in)
    assert vehicle.link is loop_in
    assert vehicle.link_entry_count_by_link_name["loop_in"] == 2
    assert vehicle.current_link_route_choice_attempt_count == 0
    assert vehicle.order_control_visit_id == 0
    assert vehicle.origin_route_choice_attempt_count == 0

    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is _expected_link(
        candidate_links,
        [1.0, 1.0],
        second_uniform,
    )
    assert vehicle.current_link_route_choice_attempt_count == 1
    assert vehicle.link_entry_count_by_link_name["loop_in"] == 2
    assert vehicle.order_control_visit_id == 0
    assert _rng_state(W) == rng_before


def test_hard_deterministic_keeps_max_preference_without_an_attempt():
    W = _new_world("route_choice_hard_origin", hard_deterministic_mode=True)
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_hard_origin")
    _set_origin_weights(vehicle, W, 1.0, 5.0)
    _queue_at_origin(W, vehicle)
    rng_before = _rng_state(W)
    W.get_node("orig").generate()
    assert vehicle.link is W.get_link("north_link")
    assert vehicle.origin_route_choice_attempt_count == 0
    assert _rng_state(W) == rng_before

    tied = _new_world("route_choice_hard_tie", hard_deterministic_mode=True)
    _add_origin_fork(tied)
    tied_vehicle = tied.addVehicle("orig", "east", 0, name="veh_hard_tie")
    _set_origin_weights(tied_vehicle, tied, 3.0, 3.0)
    _queue_at_origin(tied, tied_vehicle)
    tied.get_node("orig").generate()
    assert tied_vehicle.link is tied.get_link("east_link")
    assert tied_vehicle.origin_route_choice_attempt_count == 0

    junction = _new_world("route_choice_hard_in_trip", hard_deterministic_mode=True)
    _add_junction(junction)
    in_trip = junction.addVehicle("orig", "dest", 0, name="veh_hard_in_trip")
    _place_on_in_link(junction, in_trip, 1)
    _set_junction_weights(in_trip, junction, 1.0, 4.0)
    rng_before = _rng_state(junction)
    in_trip.route_next_link_choice()
    assert in_trip.route_next_link is junction.get_link("out_side")
    assert in_trip.current_link_route_choice_attempt_count == 0
    assert _rng_state(junction) == rng_before


def test_specified_route_does_not_draw_or_increment_attempt():
    W = _new_world("route_choice_specified_origin")
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_specified_origin")
    _set_origin_weights(vehicle, W, 100.0, 0.0)
    vehicle.specified_route = [W.get_link("north_link")]
    _queue_at_origin(W, vehicle)
    rng_before = _rng_state(W)
    W.get_node("orig").generate()
    assert vehicle.link is W.get_link("north_link")
    assert vehicle.origin_route_choice_attempt_count == 0
    assert _rng_state(W) == rng_before

    bad = _new_world("route_choice_specified_bad")
    bad.addNode("orig", 0, 0)
    bad.addNode("east", 1, 0)
    bad.addNode("north", 0, 1)
    bad.addLink("east_link", "orig", "east", length=100, free_flow_speed=10, number_of_lanes=1)
    bad.addLink("north_link", "orig", "north", length=100, free_flow_speed=10, number_of_lanes=1)
    unrelated = bad.addLink(
        "unrelated",
        "east",
        "north",
        length=50,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    _prepare(bad)
    other = bad.addVehicle("orig", "east", 0, name="veh_specified_bad")
    other.specified_route = [unrelated]
    _queue_at_origin(bad, other)
    _assert_value_error(bad.get_node("orig").generate)
    assert other.origin_route_choice_attempt_count == 0

    junction = _new_world("route_choice_specified_in_trip")
    _add_junction(junction)
    in_trip = junction.addVehicle("orig", "dest", 0, name="veh_specified_in_trip")
    _place_on_in_link(junction, in_trip, 1)
    _set_junction_weights(in_trip, junction, 100.0, 0.0)
    in_trip.specified_route = [junction.get_link("out_side")]
    rng_before = _rng_state(junction)
    in_trip.route_next_link_choice()
    assert in_trip.route_next_link is junction.get_link("out_side")
    assert in_trip.current_link_route_choice_attempt_count == 0
    assert in_trip.link_entry_count_by_link_name == {"in_link": 1}
    assert _rng_state(junction) == rng_before


def test_world_copy_matches_and_keeps_attempts_separate():
    W = _new_world("route_choice_copy")
    _add_origin_fork(W)
    vehicle = W.addVehicle("orig", "east", 0, name="veh_copy")
    _set_origin_weights(vehicle, W, 3.0, 1.0)
    _queue_at_origin(W, vehicle)
    copied = W.copy()
    assert copied._common_seed_rng_internal_entropy == W._common_seed_rng_internal_entropy
    copied_vehicle = copied.VEHICLES["veh_copy"]
    assert copied_vehicle.origin_route_choice_attempt_count == 0
    assert copied_vehicle is not vehicle
    copied.get_node("orig").generate()
    assert vehicle.origin_route_choice_attempt_count == 0
    assert vehicle.link is None
    assert copied_vehicle.origin_route_choice_attempt_count == 1
    uniform_value = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "origin_route_choice",
        ("veh_copy", "orig", 0),
    )
    expected_link = _expected_link(
        [W.get_link("east_link"), W.get_link("north_link")],
        [3.0, 1.0],
        uniform_value,
    )
    assert copied_vehicle.link.name == expected_link.name
    W.get_node("orig").generate()
    assert vehicle.link.name == copied_vehicle.link.name
    assert vehicle.origin_route_choice_attempt_count == 1


def test_vehicle_choice_does_not_depend_on_call_order():
    def _chosen_names(call_order):
        W = _new_world("route_choice_order_" + "_".join(call_order))
        _add_junction(W)
        vehicle_a = W.addVehicle("orig", "dest", 0, name="veh_a")
        vehicle_b = W.addVehicle("orig", "dest", 0, name="veh_b")
        _place_on_in_link(W, vehicle_a, 1)
        _place_on_in_link(W, vehicle_b, 1)
        _set_junction_weights(vehicle_a, W, 2.0, 1.0)
        _set_junction_weights(vehicle_b, W, 2.0, 1.0)
        for vehicle_name in call_order:
            W.VEHICLES[vehicle_name].route_next_link_choice()
        return {
            "veh_a": W.VEHICLES["veh_a"].route_next_link.name,
            "veh_b": W.VEHICLES["veh_b"].route_next_link.name,
        }

    forward = _chosen_names(["veh_a", "veh_b"])
    reverse = _chosen_names(["veh_b", "veh_a"])
    assert forward == reverse
    solo = _new_world("route_choice_order_solo")
    _add_junction(solo)
    only = solo.addVehicle("orig", "dest", 0, name="veh_a")
    _place_on_in_link(solo, only, 1)
    _set_junction_weights(only, solo, 2.0, 1.0)
    uniform_value = keyed_uniform_value(
        solo._common_seed_rng_internal_entropy,
        "in_trip_route_choice",
        ("veh_a", "in_link", 1, 0),
    )
    expected = _expected_link(
        [solo.get_link("out_dest"), solo.get_link("out_side")],
        [2.0, 1.0],
        uniform_value,
    )
    only.route_next_link_choice()
    assert only.route_next_link is expected
    assert forward["veh_a"] == expected.name


def test_single_path_trip_still_reaches_the_only_destination():
    W = _new_world("route_choice_single_path", hard_deterministic_mode=True)
    W.addNode("orig", 0, 0)
    W.addNode("mid", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink("first", "orig", "mid", length=20, free_flow_speed=20, number_of_lanes=1)
    W.addLink("second", "mid", "dest", length=20, free_flow_speed=20, number_of_lanes=1)
    vehicle = W.addVehicle("orig", "dest", 0, name="veh_single_path")
    W.exec_simulation()
    assert vehicle.state == "end"
    assert vehicle.link_entry_count_by_link_name == {"first": 1, "second": 1}
    assert vehicle.origin_route_choice_attempt_count == 0
    assert vehicle.current_link_route_choice_attempt_count == 0


TESTS = [
    test_origin_and_in_trip_domains_are_distinct_fixed_strings,
    test_origin_zero_candidates_does_not_draw_or_increment_attempt,
    test_origin_one_candidate_selects_without_keyed_draw,
    test_origin_two_candidates_uses_current_attempt_and_not_world_rng,
    test_prefer_uses_link_name_order_not_registration_order,
    test_origin_zero_preference_uses_equal_categories,
    test_origin_rejected_entry_keeps_the_consumed_attempt,
    test_origin_negative_preference_does_not_increment_attempt,
    test_in_trip_dead_end_sets_no_next_link_without_an_attempt,
    test_in_trip_zero_final_candidates_does_not_increment_attempt,
    test_in_trip_one_candidate_does_not_increment_attempt,
    test_in_trip_two_candidates_uses_link_name_entry_count_and_attempt,
    test_in_trip_missing_or_zero_entry_count_stops_without_increment,
    test_loop_reentry_changes_the_in_trip_uniform,
    test_route_choice_candidate_helper_rejects_invalid_weights_and_uniforms,
    test_route_choice_candidate_helper_handles_boundaries,
    test_hard_deterministic_keeps_max_preference_without_an_attempt,
    test_specified_route_does_not_draw_or_increment_attempt,
    test_world_copy_matches_and_keeps_attempts_separate,
    test_vehicle_choice_does_not_depend_on_call_order,
    test_single_path_trip_still_reaches_the_only_destination,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Common seed/RNG route choice tests passed.")
