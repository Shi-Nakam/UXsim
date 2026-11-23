# Ordinary merge uses its own sequential Generator.
#
# Expected draws are built in this file from the same seed contract as
# World.__init__: saved SeedSequence entropy, then spawn_key (1,).
# This file does not call a production seed helper to obtain that Generator.
# No numeric uniform is hard-coded.
#
# Run from the repository root:
#   python tests_common_seed_rng_normal_merge.py

import numbers

import numpy as np

from uxsim import World


# Fixed ordinary-merge stream id. World.__init__ uses this same spawn_key.
# spawn_key (0,) is the existing order-control child. A bare SeedSequence
# of the entropy would repeat W.rng when the entropy is the original seed.
_NORMAL_MERGE_SPAWN_KEY = (1,)
_DRAW_COUNT = 4


def _prepare(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()
    for node in W.NODES:
        node.flow_capacity_update()


def _new_world(name, random_seed, hard_deterministic_mode=False):
    W = World(
        name=name,
        deltan=1,
        tmax=50,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=random_seed,
        hard_deterministic_mode=hard_deterministic_mode,
    )
    return W


def _entropy_words_from_seed(random_seed):
    """Independent copy of the stored-entropy shape. Not a production helper."""
    parent = np.random.SeedSequence(random_seed)
    raw_entropy = parent.entropy
    if type(raw_entropy) is bool:
        raise AssertionError("SeedSequence entropy must not be a bool")
    if type(raw_entropy) is int:
        return (raw_entropy,)
    if isinstance(raw_entropy, numbers.Integral):
        return (int(raw_entropy),)
    entropy_words = []
    for word in raw_entropy:
        entropy_words.append(int(word))
    if len(entropy_words) == 0:
        raise AssertionError("SeedSequence entropy must not be empty")
    return tuple(entropy_words)


def _independent_normal_merge_rng(random_seed):
    entropy_words = _entropy_words_from_seed(random_seed)
    ordinary_merge_seed_sequence = np.random.SeedSequence(
        entropy_words,
        spawn_key=_NORMAL_MERGE_SPAWN_KEY,
    )
    return np.random.default_rng(ordinary_merge_seed_sequence)


def _state(generator):
    return generator.bit_generator.state


def _draws(generator, draw_count):
    drawn_values = []
    draw_index = 0
    while draw_index < draw_count:
        drawn_values.append(generator.random())
        draw_index += 1
    return drawn_values


def _build_merge_network(W, in1_priority=1, in2_priority=3):
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 1)
    W.addNode("merge", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink(
        "in1",
        "orig1",
        "merge",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=in1_priority,
    )
    W.addLink(
        "in2",
        "orig2",
        "merge",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=in2_priority,
    )
    W.addLink(
        "out",
        "merge",
        "dest",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    _prepare(W)


def _place_at_head(vehicle, inlink, outlink):
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
    node = inlink.end_node
    if vehicle not in node.incoming_vehicles:
        node.incoming_vehicles.append(vehicle)
    inlink.capacity_out_remain = 100
    outlink.capacity_in_remain = 100
    node.flow_capacity_remain = 100
    node.signal_phase = 0


def _choice_weights(vehicles):
    merge_priorities = []
    for vehicle in vehicles:
        merge_priorities.append(vehicle.link.merge_priority)
    weight_array = np.array(merge_priorities, dtype=float)
    if sum(weight_array) == 0:
        weight_array = np.ones(len(weight_array))
    return weight_array / sum(weight_array)


def test_world_has_separate_normal_merge_generator():
    W = _new_world("normal_merge_attr", 1)
    assert isinstance(W.normal_merge_rng, np.random.Generator)
    assert W.normal_merge_rng is not W.rng
    assert W.normal_merge_rng is not W.order_control_rng
    assert _state(W.normal_merge_rng) == _state(_independent_normal_merge_rng(1))
    assert _state(W.normal_merge_rng) != _state(W.rng)
    assert _state(W.normal_merge_rng) != _state(W.order_control_rng)


def test_same_seed_same_normal_merge_series_for_different_world_names():
    left = _new_world("normal_merge_left", 11)
    right = _new_world("normal_merge_right", 11)
    assert left.name != right.name
    assert _state(left.normal_merge_rng) == _state(right.normal_merge_rng)
    assert _state(left.normal_merge_rng) == _state(_independent_normal_merge_rng(11))
    left_draws = _draws(left.normal_merge_rng, _DRAW_COUNT)
    right_draws = _draws(right.normal_merge_rng, _DRAW_COUNT)
    assert left_draws == right_draws


def test_different_seeds_have_different_normal_merge_series():
    first = _new_world("normal_merge_seed_21", 21)
    second = _new_world("normal_merge_seed_22", 22)
    assert _state(first.normal_merge_rng) != _state(second.normal_merge_rng)
    first_draws = _draws(first.normal_merge_rng, _DRAW_COUNT)
    second_draws = _draws(second.normal_merge_rng, _DRAW_COUNT)
    assert first_draws != second_draws
    draw_index = 0
    different_draw_count = 0
    while draw_index < _DRAW_COUNT:
        if first_draws[draw_index] != second_draws[draw_index]:
            different_draw_count += 1
        draw_index += 1
    assert different_draw_count >= 2


def test_the_three_generators_do_not_advance_each_other():
    W = _new_world("normal_merge_streams", 3)
    merge_state = _state(W.normal_merge_rng)
    shared_state = _state(W.rng)
    order_state = _state(W.order_control_rng)

    W.rng.random()
    shared_after = _state(W.rng)
    assert shared_after != shared_state
    assert _state(W.normal_merge_rng) == merge_state
    assert _state(W.order_control_rng) == order_state

    W.order_control_rng.random()
    order_after = _state(W.order_control_rng)
    assert order_after != order_state
    assert _state(W.normal_merge_rng) == merge_state
    assert _state(W.rng) == shared_after

    W.normal_merge_rng.random()
    assert _state(W.rng) == shared_after
    assert _state(W.order_control_rng) == order_after
    assert _state(W.normal_merge_rng) != merge_state


def test_copy_keeps_current_normal_merge_state_on_a_different_generator():
    W = _new_world("normal_merge_copy", 4)
    W.normal_merge_rng.random()
    W.normal_merge_rng.random()
    copied = W.copy()

    assert copied.normal_merge_rng is not W.normal_merge_rng
    assert _state(copied.normal_merge_rng) == _state(W.normal_merge_rng)

    original_draw = W.normal_merge_rng.random()
    assert _state(copied.normal_merge_rng) != _state(W.normal_merge_rng)
    copy_draw = copied.normal_merge_rng.random()
    assert copy_draw == original_draw

    second_copy = W.copy()
    assert second_copy.normal_merge_rng is not W.normal_merge_rng
    assert _state(second_copy.normal_merge_rng) == _state(W.normal_merge_rng)
    second_copy.normal_merge_rng.random()
    assert _state(W.normal_merge_rng) != _state(second_copy.normal_merge_rng)


def test_copy_after_merge_matches_then_one_side_can_diverge():
    random_seed = 6
    W = _new_world("normal_merge_copy_after", random_seed)
    _build_merge_network(W)
    low = W.addVehicle("orig1", "dest", 0, name="veh_low")
    high = W.addVehicle("orig2", "dest", 0, name="veh_high")
    in1 = W.get_link("in1")
    in2 = W.get_link("in2")
    out = W.get_link("out")
    _place_at_head(low, in1, out)
    _place_at_head(high, in2, out)

    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    expected_vehicle = expected.choice([low, high], p=_choice_weights([low, high]))
    W.get_node("merge").transfer()
    assert expected_vehicle.link is out
    assert _state(W.normal_merge_rng) == _state(expected)

    copied = W.copy()
    assert copied.normal_merge_rng is not W.normal_merge_rng
    assert _state(copied.normal_merge_rng) == _state(W.normal_merge_rng)
    copied.normal_merge_rng.random()
    assert _state(W.normal_merge_rng) != _state(copied.normal_merge_rng)


def test_normal_merge_follows_the_dedicated_series():
    random_seed = 8
    W = _new_world("normal_merge_transfer", random_seed)
    _build_merge_network(W)
    low = W.addVehicle("orig1", "dest", 0, name="veh_low")
    high = W.addVehicle("orig2", "dest", 0, name="veh_high")
    in1 = W.get_link("in1")
    in2 = W.get_link("in2")
    out = W.get_link("out")
    _place_at_head(low, in1, out)
    _place_at_head(high, in2, out)

    shared_state = _state(W.rng)
    order_state = _state(W.order_control_rng)
    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    expected_vehicle = expected.choice([low, high], p=_choice_weights([low, high]))

    W.get_node("merge").transfer()

    assert expected_vehicle.link is out
    assert _state(W.normal_merge_rng) == _state(expected)
    assert _state(W.rng) == shared_state
    assert _state(W.order_control_rng) == order_state


def test_multiple_outlinks_are_shuffled_by_the_dedicated_generator():
    random_seed = 9
    W = _new_world("normal_merge_shuffle", random_seed)
    W.addNode("orig_open", 0, 0)
    W.addNode("orig_closed", 0, 1)
    W.addNode("merge", 1, 0)
    W.addNode("dest_open", 2, 0)
    W.addNode("dest_closed", 2, 1)
    W.addLink(
        "in_open",
        "orig_open",
        "merge",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=1,
    )
    W.addLink(
        "in_closed",
        "orig_closed",
        "merge",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=1,
    )
    W.addLink(
        "out_open",
        "merge",
        "dest_open",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    W.addLink(
        "out_closed",
        "merge",
        "dest_closed",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    _prepare(W)
    open_vehicle = W.addVehicle("orig_open", "dest_open", 0, name="veh_open")
    closed_vehicle = W.addVehicle("orig_closed", "dest_closed", 0, name="veh_closed")
    in_open = W.get_link("in_open")
    in_closed = W.get_link("in_closed")
    out_open = W.get_link("out_open")
    out_closed = W.get_link("out_closed")
    _place_at_head(open_vehicle, in_open, out_open)
    _place_at_head(closed_vehicle, in_closed, out_closed)
    out_closed.capacity_in_remain = 0

    shared_state = _state(W.rng)
    order_state = _state(W.order_control_rng)
    expected = _independent_normal_merge_rng(random_seed)
    two_outlinks = [out_open, out_closed]
    expected.shuffle(two_outlinks)
    expected_vehicle = expected.choice(
        [open_vehicle],
        p=_choice_weights([open_vehicle]),
    )

    W.get_node("merge")._transfer_normal_merge()

    assert expected_vehicle.link is out_open
    assert closed_vehicle.link is in_closed
    assert _state(W.normal_merge_rng) == _state(expected)
    assert _state(W.rng) == shared_state
    assert _state(W.order_control_rng) == order_state


def test_choice_uses_merge_priority_on_the_dedicated_generator():
    random_seed = 10
    W = _new_world("normal_merge_priority", random_seed)
    _build_merge_network(W, in1_priority=1, in2_priority=4)
    low = W.addVehicle("orig1", "dest", 0, name="veh_priority_low")
    high = W.addVehicle("orig2", "dest", 0, name="veh_priority_high")
    out = W.get_link("out")
    _place_at_head(low, W.get_link("in1"), out)
    _place_at_head(high, W.get_link("in2"), out)
    assert low.link.merge_priority == 1
    assert high.link.merge_priority == 4

    shared_state = _state(W.rng)
    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    weights = _choice_weights([low, high])
    assert weights[1] > weights[0]
    expected_vehicle = expected.choice([low, high], p=weights)

    merge_state_before = _state(W.normal_merge_rng)
    W.get_node("merge")._transfer_normal_merge()

    assert expected_vehicle.link is out
    assert _state(W.normal_merge_rng) != merge_state_before
    assert _state(W.normal_merge_rng) == _state(expected)
    assert _state(W.rng) == shared_state


def test_zero_merge_priority_sum_uses_equal_weights():
    random_seed = 12
    W = _new_world("normal_merge_zero_priority", random_seed)
    _build_merge_network(W, in1_priority=0, in2_priority=0)
    first = W.addVehicle("orig1", "dest", 0, name="veh_zero_first")
    second = W.addVehicle("orig2", "dest", 0, name="veh_zero_second")
    out = W.get_link("out")
    _place_at_head(first, W.get_link("in1"), out)
    _place_at_head(second, W.get_link("in2"), out)

    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    equal_weights = np.ones(2) / 2
    expected_vehicle = expected.choice([first, second], p=equal_weights)
    W.get_node("merge")._transfer_normal_merge()
    assert expected_vehicle.link is out
    assert _state(W.normal_merge_rng) == _state(expected)


def test_hard_deterministic_merge_does_not_draw():
    W = _new_world("normal_merge_hard", 13, hard_deterministic_mode=True)
    _build_merge_network(W, in1_priority=1, in2_priority=3)
    low = W.addVehicle("orig1", "dest", 0, name="veh_hard_low")
    high = W.addVehicle("orig2", "dest", 0, name="veh_hard_high")
    in1 = W.get_link("in1")
    in2 = W.get_link("in2")
    out = W.get_link("out")
    _place_at_head(low, in1, out)
    _place_at_head(high, in2, out)

    shared_state = _state(W.rng)
    order_state = _state(W.order_control_rng)
    merge_state = _state(W.normal_merge_rng)
    W.get_node("merge")._transfer_normal_merge()

    assert high.link is out
    assert low.link is in1
    assert _state(W.normal_merge_rng) == merge_state
    assert _state(W.rng) == shared_state
    assert _state(W.order_control_rng) == order_state


def test_no_outlink_only_shuffles_an_empty_list():
    random_seed = 14
    W = _new_world("normal_merge_empty", random_seed)
    _build_merge_network(W)
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_no_route")
    in1 = W.get_link("in1")
    out = W.get_link("out")
    _place_at_head(vehicle, in1, out)
    vehicle.route_next_link = None

    shared_state = _state(W.rng)
    order_state = _state(W.order_control_rng)
    expected = _independent_normal_merge_rng(random_seed)
    empty_outlinks = []
    expected.shuffle(empty_outlinks)
    W.get_node("merge")._transfer_normal_merge()

    assert vehicle.link is in1
    assert _state(W.normal_merge_rng) == _state(expected)
    assert _state(W.rng) == shared_state
    assert _state(W.order_control_rng) == order_state


def test_one_candidate_still_shuffles_and_chooses():
    random_seed = 15
    W = _new_world("normal_merge_one", random_seed)
    _build_merge_network(W)
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_only")
    in1 = W.get_link("in1")
    out = W.get_link("out")
    _place_at_head(vehicle, in1, out)

    shared_state = _state(W.rng)
    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    expected_vehicle = expected.choice([vehicle], p=_choice_weights([vehicle]))
    W.get_node("merge")._transfer_normal_merge()

    assert expected_vehicle is vehicle
    assert vehicle.link is out
    assert _state(W.normal_merge_rng) == _state(expected)
    assert _state(W.rng) == shared_state


def _build_two_merge_world(name, random_seed):
    W = _new_world(name, random_seed)
    W.addNode("a1", 0, 0)
    W.addNode("a2", 0, 1)
    W.addNode("merge_a", 1, 0)
    W.addNode("dest_a", 2, 0)
    W.addNode("b1", 0, 2)
    W.addNode("b2", 0, 3)
    W.addNode("merge_b", 1, 2)
    W.addNode("dest_b_open", 2, 2)
    W.addNode("dest_b_closed", 2, 3)
    W.addLink(
        "in_a1",
        "a1",
        "merge_a",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=1,
    )
    W.addLink(
        "in_a2",
        "a2",
        "merge_a",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=3,
    )
    W.addLink(
        "out_a",
        "merge_a",
        "dest_a",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    W.addLink(
        "in_b1",
        "b1",
        "merge_b",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=1,
    )
    W.addLink(
        "in_b2",
        "b2",
        "merge_b",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
        merge_priority=1,
    )
    W.addLink(
        "out_b_open",
        "merge_b",
        "dest_b_open",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    W.addLink(
        "out_b_closed",
        "merge_b",
        "dest_b_closed",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    _prepare(W)
    low = W.addVehicle("a1", "dest_a", 0, name="veh_a_low")
    high = W.addVehicle("a2", "dest_a", 0, name="veh_a_high")
    open_vehicle = W.addVehicle("b1", "dest_b_open", 0, name="veh_b_open")
    closed_vehicle = W.addVehicle("b2", "dest_b_closed", 0, name="veh_b_closed")
    _place_at_head(low, W.get_link("in_a1"), W.get_link("out_a"))
    _place_at_head(high, W.get_link("in_a2"), W.get_link("out_a"))
    _place_at_head(open_vehicle, W.get_link("in_b1"), W.get_link("out_b_open"))
    _place_at_head(closed_vehicle, W.get_link("in_b2"), W.get_link("out_b_closed"))
    W.get_link("out_b_closed").capacity_in_remain = 0
    return W


def _replay_merge_a(rng, low, high):
    one_outlink = ["merge_a"]
    rng.shuffle(one_outlink)
    return rng.choice([low, high], p=_choice_weights([low, high]))


def _replay_merge_b(rng, open_vehicle):
    two_outlinks = ["open", "closed"]
    rng.shuffle(two_outlinks)
    return rng.choice([open_vehicle], p=_choice_weights([open_vehicle]))


def test_merge_order_changes_the_later_draw():
    random_seed = 16
    first_then_second = _build_two_merge_world("normal_merge_order_ab", random_seed)
    second_then_first = _build_two_merge_world("normal_merge_order_ba", random_seed)

    first_then_second.get_node("merge_a")._transfer_normal_merge()
    first_then_second.get_node("merge_b")._transfer_normal_merge()
    second_then_first.get_node("merge_b")._transfer_normal_merge()
    second_then_first.get_node("merge_a")._transfer_normal_merge()

    assert _state(first_then_second.normal_merge_rng) != _state(
        second_then_first.normal_merge_rng
    )

    replay_ab = _independent_normal_merge_rng(random_seed)
    low_ab = first_then_second.VEHICLES["veh_a_low"]
    high_ab = first_then_second.VEHICLES["veh_a_high"]
    open_ab = first_then_second.VEHICLES["veh_b_open"]
    chosen_a_first = _replay_merge_a(replay_ab, low_ab, high_ab)
    chosen_b_second = _replay_merge_b(replay_ab, open_ab)
    assert chosen_a_first.link is first_then_second.get_link("out_a")
    assert chosen_b_second.link is first_then_second.get_link("out_b_open")
    assert _state(first_then_second.normal_merge_rng) == _state(replay_ab)

    replay_ba = _independent_normal_merge_rng(random_seed)
    low_ba = second_then_first.VEHICLES["veh_a_low"]
    high_ba = second_then_first.VEHICLES["veh_a_high"]
    open_ba = second_then_first.VEHICLES["veh_b_open"]
    chosen_b_first = _replay_merge_b(replay_ba, open_ba)
    chosen_a_second = _replay_merge_a(replay_ba, low_ba, high_ba)
    assert chosen_b_first.link is second_then_first.get_link("out_b_open")
    assert chosen_a_second.link is second_then_first.get_link("out_a")
    assert _state(second_then_first.normal_merge_rng) == _state(replay_ba)
    assert _state(first_then_second.rng) == _state(second_then_first.rng)
    assert _state(first_then_second.order_control_rng) == _state(
        second_then_first.order_control_rng
    )


def test_route_choice_and_arrival_do_not_advance_normal_merge_rng():
    W = _new_world("normal_merge_other_events", 17)
    W.addNode("orig", 0, 0)
    W.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="fcfs",
    )
    W.addNode("dest", 2, 0)
    W.addLink("in1", "orig", "merge", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("out1", "merge", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("out2", "merge", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("orig", "dest", 0, name="veh_other")
    in1 = W.get_link("in1")
    vehicle.link = in1
    vehicle.state = "run"
    vehicle.x = in1.length
    vehicle.link_arrival_time = 0.0
    vehicle.link_entry_count_by_link_name = {"in1": 1}
    for link in W.LINKS:
        vehicle.route_pref[link.id] = 1.0

    merge_state = _state(W.normal_merge_rng)
    shared_state = _state(W.rng)
    order_state = _state(W.order_control_rng)

    vehicle.begin_order_control_visit_on_link_entry()
    W.T = 4
    vehicle.record_order_control_node_arrival(W.get_node("merge"))
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] is not None
    assert _state(W.normal_merge_rng) == merge_state

    vehicle.route_next_link_choice()
    assert vehicle.route_next_link is not None
    assert vehicle.current_link_route_choice_attempt_count == 1
    assert _state(W.normal_merge_rng) == merge_state
    assert _state(W.rng) == shared_state
    assert _state(W.order_control_rng) == order_state


def test_fcfs_and_time_value_transfer_do_not_use_normal_merge_rng():
    fcfs_world = _new_world("normal_merge_fcfs_caller", 18)
    fcfs_world.addNode("orig", 0, 0)
    fcfs_world.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="fcfs",
    )
    fcfs_world.addNode("dest", 2, 0)
    fcfs_world.addLink(
        "in1",
        "orig",
        "merge",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    fcfs_world.addLink(
        "out",
        "merge",
        "dest",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    _prepare(fcfs_world)
    fcfs_merge_state = _state(fcfs_world.normal_merge_rng)
    fcfs_world.get_node("merge").transfer()
    assert _state(fcfs_world.normal_merge_rng) == fcfs_merge_state

    time_value_world = _new_world("normal_merge_tvt_caller", 19)
    time_value_world.addNode("orig", 0, 0)
    time_value_world.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    time_value_world.addNode("dest", 2, 0)
    time_value_world.addLink(
        "in1",
        "orig",
        "merge",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    time_value_world.addLink(
        "out",
        "merge",
        "dest",
        length=100,
        free_flow_speed=10,
        number_of_lanes=1,
    )
    _prepare(time_value_world)
    time_value_merge_state = _state(time_value_world.normal_merge_rng)
    time_value_world.get_node("merge").transfer()
    assert _state(time_value_world.normal_merge_rng) == time_value_merge_state


def test_signal_block_does_not_choose():
    random_seed = 23
    W = _new_world("normal_merge_signal", random_seed)
    _build_merge_network(W)
    low = W.addVehicle("orig1", "dest", 0, name="veh_signal_low")
    high = W.addVehicle("orig2", "dest", 0, name="veh_signal_high")
    in1 = W.get_link("in1")
    in2 = W.get_link("in2")
    out = W.get_link("out")
    _place_at_head(low, in1, out)
    _place_at_head(high, in2, out)
    merge = W.get_node("merge")
    merge.signal = [0, 1]
    merge.signal_phase = 1
    in1.signal_group = [0]
    in2.signal_group = [0]

    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    merge._transfer_normal_merge()

    assert low.link is in1
    assert high.link is in2
    assert _state(W.normal_merge_rng) == _state(expected)


def test_capacity_block_does_not_choose():
    random_seed = 24
    W = _new_world("normal_merge_capacity", random_seed)
    _build_merge_network(W)
    low = W.addVehicle("orig1", "dest", 0, name="veh_capacity_low")
    high = W.addVehicle("orig2", "dest", 0, name="veh_capacity_high")
    in1 = W.get_link("in1")
    in2 = W.get_link("in2")
    out = W.get_link("out")
    _place_at_head(low, in1, out)
    _place_at_head(high, in2, out)
    out.capacity_in_remain = 0

    expected = _independent_normal_merge_rng(random_seed)
    one_outlink = [out]
    expected.shuffle(one_outlink)
    W.get_node("merge")._transfer_normal_merge()

    assert low.link is in1
    assert high.link is in2
    assert _state(W.normal_merge_rng) == _state(expected)


TESTS = [
    test_world_has_separate_normal_merge_generator,
    test_same_seed_same_normal_merge_series_for_different_world_names,
    test_different_seeds_have_different_normal_merge_series,
    test_the_three_generators_do_not_advance_each_other,
    test_copy_keeps_current_normal_merge_state_on_a_different_generator,
    test_copy_after_merge_matches_then_one_side_can_diverge,
    test_normal_merge_follows_the_dedicated_series,
    test_multiple_outlinks_are_shuffled_by_the_dedicated_generator,
    test_choice_uses_merge_priority_on_the_dedicated_generator,
    test_zero_merge_priority_sum_uses_equal_weights,
    test_hard_deterministic_merge_does_not_draw,
    test_no_outlink_only_shuffles_an_empty_list,
    test_one_candidate_still_shuffles_and_chooses,
    test_merge_order_changes_the_later_draw,
    test_route_choice_and_arrival_do_not_advance_normal_merge_rng,
    test_fcfs_and_time_value_transfer_do_not_use_normal_merge_rng,
    test_signal_block_does_not_choose,
    test_capacity_block_does_not_choose,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Common seed/RNG normal merge tests passed.")
