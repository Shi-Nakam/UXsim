# Arrival tiebreakers use one keyed uniform per node visit.
#
# The expected visit number is the test's own sum over the node's inlinks.
# The expected tiebreaker uses a key written in the test, not the production
# key helper. No numeric uniform is hard-coded.
#
# Run from the repository root:
#   python tests_common_seed_rng_arrival_tiebreaker.py

import ast
import inspect

from uxsim import World
from uxsim.common_seed_rng_arrival_tiebreaker import (
    ARRIVAL_TIEBREAKER_DOMAIN,
    node_visit_number_from_link_entries,
)
from uxsim.common_seed_rng_keyed_uniform import keyed_uniform_value
from uxsim.common_seed_rng_route_choice import (
    IN_TRIP_ROUTE_CHOICE_DOMAIN,
    ORIGIN_ROUTE_CHOICE_DOMAIN,
)
from uxsim.order_control_batch_level_2_reference import (
    _transfer_vehicle_reference,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    _transfer_one_vehicle_like_uxsim,
)
from uxsim.order_control_tvt_mp_candidate_local_vehicle_advance import (
    advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals,
)


def _prepare(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _new_world(name, order_control_type="fcfs"):
    W = World(
        name=name,
        deltan=1,
        tmax=80,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 1)
    W.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type=order_control_type,
        batch_size=1,
    )
    W.addNode("dest", 2, 0)
    W.addLink("link1", "orig1", "merge", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("side", "dest", "orig2", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
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


def _sum_entries_on_node_inlinks(node, entry_counts):
    """Test-side visit number. Missing inlink counts are 0."""
    total_entry_count = 0
    for inlink in node.inlinks.values():
        if inlink.name in entry_counts:
            total_entry_count = total_entry_count + entry_counts[inlink.name]
    return total_entry_count


def _move_through_node(vehicle, inlink, outlink):
    """Physical move. This records the outlink entry and does not record arrival."""
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
    node.flow_capacity_remain = 100
    node._transfer_one_vehicle_between_links(vehicle, inlink, outlink)


def _start_visit_on_link(vehicle, link, entry_count):
    vehicle.link = link
    vehicle.state = "run"
    vehicle.x = link.length
    vehicle.link_arrival_time = 0.0
    vehicle.link_entry_count_by_link_name = {link.name: entry_count}
    vehicle.begin_order_control_visit_on_link_entry()


def test_arrival_tiebreaker_domain_is_distinct_from_route_choice():
    assert ARRIVAL_TIEBREAKER_DOMAIN == "arrival_tiebreaker"
    assert ARRIVAL_TIEBREAKER_DOMAIN != ORIGIN_ROUTE_CHOICE_DOMAIN
    assert ARRIVAL_TIEBREAKER_DOMAIN != IN_TRIP_ROUTE_CHOICE_DOMAIN
    W = _new_world("arrival_domain")
    key_parts = ("veh_domain", "merge", 1)
    arrival_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        key_parts,
    )
    origin_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "origin_route_choice",
        key_parts,
    )
    in_trip_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "in_trip_route_choice",
        key_parts,
    )
    assert arrival_uniform != origin_uniform
    assert arrival_uniform != in_trip_uniform
    assert 0.0 <= arrival_uniform < 1.0


def test_node_visit_number_is_one_on_the_first_inlink_entry():
    W = _new_world("arrival_visit_one")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_visit_one")
    merge = W.get_node("merge")
    vehicle.link_entry_count_by_link_name = {"link1": 1}
    expected = _sum_entries_on_node_inlinks(
        merge,
        vehicle.link_entry_count_by_link_name,
    )
    assert expected == 1
    assert node_visit_number_from_link_entries(vehicle, merge) == 1


def test_node_visit_number_sums_every_inlink_on_a_later_visit():
    W = _new_world("arrival_visit_two_inlinks")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_two_inlinks")
    merge = W.get_node("merge")
    vehicle.link = W.get_link("link2")
    vehicle.link_entry_count_by_link_name = {"link1": 1, "link2": 1}
    expected = _sum_entries_on_node_inlinks(
        merge,
        vehicle.link_entry_count_by_link_name,
    )
    assert expected == 2
    assert node_visit_number_from_link_entries(vehicle, merge) == 2
    assert vehicle.link_entry_count_by_link_name["link2"] != expected


def test_same_inlink_reentry_makes_node_visit_number_two():
    # The first move starts from link_b without a recorded entry. The counted
    # entries are the transfers onto link_a, then link_b, then link_a again.
    W = World(
        name="arrival_same_inlink_loop",
        deltan=1,
        tmax=40,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    W.addNode("n1", 0, 0)
    W.addNode("n2", 1, 0)
    W.addLink("link_a", "n1", "n2", length=100, free_flow_speed=10, number_of_lanes=1)
    W.addLink("link_b", "n2", "n1", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("n1", "n2", 0, name="veh_same_inlink")
    link_a = W.get_link("link_a")
    link_b = W.get_link("link_b")
    _move_through_node(vehicle, link_b, link_a)
    _move_through_node(vehicle, link_a, link_b)
    _move_through_node(vehicle, link_b, link_a)
    assert vehicle.link_entry_count_by_link_name == {"link_a": 2, "link_b": 1}
    n2 = W.get_node("n2")
    expected = _sum_entries_on_node_inlinks(
        n2,
        vehicle.link_entry_count_by_link_name,
    )
    assert expected == 2
    assert node_visit_number_from_link_entries(vehicle, n2) == 2


def test_links_that_do_not_end_at_the_node_are_excluded():
    W = _new_world("arrival_unrelated_link")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_unrelated")
    merge = W.get_node("merge")
    vehicle.link_entry_count_by_link_name = {"out": 40, "side": 7, "link1": 1}
    expected = _sum_entries_on_node_inlinks(
        merge,
        vehicle.link_entry_count_by_link_name,
    )
    assert expected == 1
    assert node_visit_number_from_link_entries(vehicle, merge) == 1


def test_zero_on_one_inlink_is_allowed_when_the_total_is_positive():
    W = _new_world("arrival_zero_one_inlink")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_zero_one")
    merge = W.get_node("merge")
    vehicle.link_entry_count_by_link_name = {"link1": 0, "link2": 1}
    expected = _sum_entries_on_node_inlinks(
        merge,
        vehicle.link_entry_count_by_link_name,
    )
    assert expected == 1
    assert node_visit_number_from_link_entries(vehicle, merge) == 1


def test_invalid_link_entry_counts_are_rejected():
    W = _new_world("arrival_invalid_count")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_invalid_count")
    merge = W.get_node("merge")
    invalid_counts = (-1, True, False, 1.5, "1")
    for invalid_count in invalid_counts:
        vehicle.link_entry_count_by_link_name = {"link1": invalid_count}
        _assert_value_error(
            lambda count=invalid_count: node_visit_number_from_link_entries(
                vehicle,
                merge,
            )
        )


def test_zero_node_visit_number_does_not_record_a_tiebreaker():
    W = _new_world("arrival_visit_zero")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_visit_zero")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    vehicle.link = link1
    vehicle.state = "run"
    vehicle.link_arrival_time = 0.0
    vehicle.link_entry_count_by_link_name = {}
    vehicle.begin_order_control_visit_on_link_entry()
    assert node_visit_number_from_link_entries(vehicle, merge) == 0
    rng_before = _rng_state(W)
    _assert_value_error(lambda: vehicle.record_order_control_node_arrival(merge))
    assert vehicle.order_control_current_visit["arrival_time"] is None
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] is None
    assert vehicle.order_control_node_arrival_times == {}
    assert vehicle.order_control_node_arrival_tiebreakers == {}
    assert vehicle.link_entry_count_by_link_name == {}
    assert _rng_state(W) == rng_before


def test_record_order_control_node_first_arrival_stores_keyed_legacy_value():
    W = _new_world("arrival_legacy_first")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_legacy")
    empty = W.addVehicle("orig2", "dest", 0, name="veh_legacy_empty")
    merge = W.get_node("merge")
    vehicle.link_entry_count_by_link_name = {"link1": 1}
    empty.link_entry_count_by_link_name = {}
    W.T = 4
    expected_tiebreaker = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_legacy", "merge", 1),
    )
    rng_before = _rng_state(W)
    vehicle.record_order_control_node_first_arrival(merge)
    assert vehicle.order_control_node_arrival_times["merge"] == 4 * W.DELTAT
    assert vehicle.order_control_node_arrival_tiebreakers["merge"] == expected_tiebreaker
    assert vehicle.order_control_current_visit is None
    assert _rng_state(W) == rng_before
    W.T = 8
    vehicle.record_order_control_node_first_arrival(merge)
    assert vehicle.order_control_node_arrival_times["merge"] == 4 * W.DELTAT
    assert vehicle.order_control_node_arrival_tiebreakers["merge"] == expected_tiebreaker
    assert _rng_state(W) == rng_before
    _assert_value_error(lambda: empty.record_order_control_node_first_arrival(merge))
    assert empty.order_control_node_arrival_times == {}
    assert empty.order_control_node_arrival_tiebreakers == {}
    assert _rng_state(W) == rng_before


def test_first_arrival_stores_the_keyed_tiebreaker_once():
    W = _new_world("arrival_first")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_first")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    _start_visit_on_link(vehicle, link1, 1)
    W.T = 4
    key_parts = ("veh_first", "merge", 1)
    expected_tiebreaker = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        key_parts,
    )
    rng_before = _rng_state(W)
    vehicle.record_order_control_node_arrival(merge)
    visit = vehicle.order_control_current_visit
    assert visit["arrival_time"] == W.T * W.DELTAT
    assert visit["arrival_tiebreaker"] == expected_tiebreaker
    assert vehicle.order_control_node_arrival_times["merge"] == visit["arrival_time"]
    assert vehicle.order_control_node_arrival_tiebreakers["merge"] == expected_tiebreaker
    assert _rng_state(W) == rng_before

    stored_tiebreaker = visit["arrival_tiebreaker"]
    W.T = 6
    vehicle.record_order_control_node_arrival(merge)
    assert visit["arrival_tiebreaker"] == stored_tiebreaker
    assert visit["arrival_time"] == 4 * W.DELTAT
    assert _rng_state(W) == rng_before

    later_clock = _new_world("arrival_first_later_clock")
    later_vehicle = later_clock.addVehicle("orig1", "dest", 0, name="veh_first")
    _start_visit_on_link(later_vehicle, later_clock.get_link("link1"), 1)
    later_clock.T = 9
    later_vehicle.record_order_control_node_arrival(later_clock.get_node("merge"))
    assert later_vehicle.order_control_current_visit["arrival_tiebreaker"] == expected_tiebreaker
    assert later_vehicle.order_control_current_visit["arrival_time"] == 9 * later_clock.DELTAT


def test_revisit_uses_a_new_key_and_keeps_the_first_ledger():
    W = _new_world("arrival_revisit")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_revisit")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    side = W.get_link("side")
    link2 = W.get_link("link2")
    _start_visit_on_link(vehicle, link1, 1)
    if vehicle not in link1.vehicles:
        link1.vehicles.append(vehicle)
    W.T = 2
    vehicle.record_order_control_node_arrival(merge)
    first_tiebreaker = vehicle.order_control_node_arrival_tiebreakers["merge"]
    first_time = vehicle.order_control_node_arrival_times["merge"]
    first_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_revisit", "merge", 1),
    )
    assert first_tiebreaker == first_uniform

    _move_through_node(vehicle, link1, out)
    _move_through_node(vehicle, out, side)
    _move_through_node(vehicle, side, link2)
    assert vehicle.link is link2
    assert vehicle.link_entry_count_by_link_name["link1"] == 1
    assert vehicle.link_entry_count_by_link_name["link2"] == 1
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] is None
    vehicle.order_control_visit_id = 9
    vehicle.order_control_current_visit["visit_id"] = 9
    second_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_revisit", "merge", 2),
    )
    visit_id_uniform = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_revisit", "merge", 9),
    )
    assert first_uniform != second_uniform
    assert second_uniform != visit_id_uniform
    rng_before = _rng_state(W)
    W.T = 11
    vehicle.record_order_control_node_arrival(merge)
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] == second_uniform
    assert vehicle.order_control_current_visit["arrival_time"] == 11 * W.DELTAT
    assert vehicle.order_control_node_arrival_tiebreakers["merge"] == first_tiebreaker
    assert vehicle.order_control_node_arrival_times["merge"] == first_time
    assert vehicle.order_control_visit_id == 9
    assert _rng_state(W) == rng_before


def test_another_vehicle_name_is_a_different_arrival_key():
    def _tiebreaker(world_name, vehicle_name):
        W = _new_world(world_name)
        vehicle = W.addVehicle("orig1", "dest", 0, name=vehicle_name)
        _start_visit_on_link(vehicle, W.get_link("link1"), 1)
        W.T = 3
        vehicle.record_order_control_node_arrival(W.get_node("merge"))
        return vehicle.order_control_current_visit["arrival_tiebreaker"]

    forward_a = _tiebreaker("arrival_order_a_then_b", "veh_a")
    forward_b = _tiebreaker("arrival_order_a_then_b_second", "veh_b")
    reverse_b = _tiebreaker("arrival_order_b_then_a", "veh_b")
    reverse_a = _tiebreaker("arrival_order_b_then_a_second", "veh_a")
    assert forward_a == reverse_a
    assert forward_b == reverse_b
    uniform_a = keyed_uniform_value(
        _new_world("arrival_uniform_a")._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_a", "merge", 1),
    )
    uniform_b = keyed_uniform_value(
        _new_world("arrival_uniform_b")._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_b", "merge", 1),
    )
    assert uniform_a != uniform_b
    assert forward_a == uniform_a
    assert forward_b == uniform_b


def test_world_copy_keeps_the_same_tiebreaker_on_a_separate_ledger():
    W = _new_world("arrival_copy")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_copy")
    _start_visit_on_link(vehicle, W.get_link("link1"), 1)
    copied = W.copy()
    copied_vehicle = copied.VEHICLES["veh_copy"]
    assert copied_vehicle is not vehicle
    assert copied._common_seed_rng_internal_entropy == W._common_seed_rng_internal_entropy
    W.T = 5
    copied.T = 5
    rng_before = _rng_state(W)
    copied_vehicle.record_order_control_node_arrival(copied.get_node("merge"))
    expected_tiebreaker = keyed_uniform_value(
        W._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_copy", "merge", 1),
    )
    assert copied_vehicle.order_control_current_visit["arrival_tiebreaker"] == expected_tiebreaker
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] is None
    assert vehicle.order_control_node_arrival_tiebreakers == {}
    vehicle.record_order_control_node_arrival(W.get_node("merge"))
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] == expected_tiebreaker
    assert _rng_state(W) == rng_before


def test_order_control_type_is_not_part_of_the_arrival_key():
    def _recorded(order_control_type):
        W = _new_world("arrival_type_" + order_control_type, order_control_type)
        vehicle = W.addVehicle("orig1", "dest", 0, name="veh_type")
        _start_visit_on_link(vehicle, W.get_link("link1"), 1)
        W.T = 4
        vehicle.record_order_control_node_arrival(W.get_node("merge"))
        return vehicle.order_control_current_visit["arrival_tiebreaker"]

    fcfs_tiebreaker = _recorded("fcfs")
    batch_tiebreaker = _recorded("batch")
    expected_tiebreaker = keyed_uniform_value(
        _new_world("arrival_type_expected")._common_seed_rng_internal_entropy,
        "arrival_tiebreaker",
        ("veh_type", "merge", 1),
    )
    assert fcfs_tiebreaker == expected_tiebreaker
    assert batch_tiebreaker == expected_tiebreaker


def test_physical_entry_does_not_record_an_arrival_tiebreaker():
    W = _new_world("arrival_not_at_entry")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_entry")
    link1 = W.get_link("link1")
    out = W.get_link("out")
    rng_before = _rng_state(W)
    _move_through_node(vehicle, out, link1)
    assert vehicle.link is link1
    assert vehicle.link_entry_count_by_link_name == {"link1": 1}
    assert vehicle.order_control_current_visit is not None
    assert vehicle.order_control_current_visit["arrival_time"] is None
    assert vehicle.order_control_current_visit["arrival_tiebreaker"] is None
    assert vehicle.order_control_node_arrival_tiebreakers == {}
    assert _rng_state(W) == rng_before


def test_none_order_control_type_does_not_record_an_arrival_tiebreaker():
    W = _new_world("arrival_type_none", "none")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_type_none")
    merge = W.get_node("merge")
    vehicle.link = W.get_link("link1")
    vehicle.link_entry_count_by_link_name = {}
    rng_before = _rng_state(W)
    vehicle.record_order_control_node_arrival(merge)
    assert vehicle.order_control_node_arrival_tiebreakers == {}
    assert vehicle.order_control_current_visit is None
    assert _rng_state(W) == rng_before


def test_ineligible_node_does_not_record_an_arrival_tiebreaker():
    W = World(
        name="arrival_ineligible",
        deltan=1,
        tmax=40,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    W.addNode("orig", 0, 0)
    W.addNode("mid", 1, 0)
    W.addNode("dest", 2, 0)
    W.addLink("road", "orig", "mid", length=100, free_flow_speed=10, number_of_lanes=1)
    _prepare(W)
    vehicle = W.addVehicle("orig", "dest", 0, name="veh_ineligible")
    mid = W.get_node("mid")
    vehicle.link = W.get_link("road")
    vehicle.link_entry_count_by_link_name = {}
    rng_before = _rng_state(W)
    vehicle.record_order_control_node_arrival(mid)
    assert vehicle.order_control_node_arrival_tiebreakers == {}
    assert vehicle.order_control_current_visit is None
    assert _rng_state(W) == rng_before


def test_arrival_recording_call_sites_match_the_world_contracts():
    # Candidate local advance calls the formal arrival recorder when a
    # vehicle reaches the target node. Binding transfer and Level 2
    # reference transfer do not. This is the call-site contract. The
    # keyed value itself is checked by the arrival recorder tests.
    def _attribute_calls(function):
        tree = ast.parse(inspect.getsource(function))
        called_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called_names.append(node.func.attr)
        return called_names

    advance_calls = _attribute_calls(
        advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals
    )
    binding_calls = _attribute_calls(_transfer_one_vehicle_like_uxsim)
    level2_calls = _attribute_calls(_transfer_vehicle_reference)
    assert "record_order_control_node_arrival" in advance_calls
    assert "record_order_control_node_arrival" not in binding_calls
    assert "record_order_control_node_arrival" not in level2_calls


def test_arrival_record_keeps_visit_identity_and_attempt_counters():
    W = _new_world("arrival_identity")
    vehicle = W.addVehicle("orig1", "dest", 0, name="veh_identity")
    link1 = W.get_link("link1")
    _start_visit_on_link(vehicle, link1, 1)
    visit = vehicle.order_control_current_visit
    visit_id_before = visit["visit_id"]
    earliest_before = visit["earliest_arrival_timestep"]
    vehicle.current_link_route_choice_attempt_count = 4
    vehicle.origin_route_choice_attempt_count = 2
    W.T = 7
    vehicle.record_order_control_node_arrival(W.get_node("merge"))
    assert visit["visit_id"] == visit_id_before
    assert visit["earliest_arrival_timestep"] == earliest_before
    assert visit["batch_assignment"] is None
    assert visit["arrival_time"] == 7 * W.DELTAT
    assert vehicle.link_entry_count_by_link_name == {"link1": 1}
    assert vehicle.current_link_route_choice_attempt_count == 4
    assert vehicle.origin_route_choice_attempt_count == 2
    assert vehicle.order_control_visit_id == visit_id_before


TESTS = [
    test_arrival_tiebreaker_domain_is_distinct_from_route_choice,
    test_node_visit_number_is_one_on_the_first_inlink_entry,
    test_node_visit_number_sums_every_inlink_on_a_later_visit,
    test_same_inlink_reentry_makes_node_visit_number_two,
    test_links_that_do_not_end_at_the_node_are_excluded,
    test_zero_on_one_inlink_is_allowed_when_the_total_is_positive,
    test_invalid_link_entry_counts_are_rejected,
    test_zero_node_visit_number_does_not_record_a_tiebreaker,
    test_record_order_control_node_first_arrival_stores_keyed_legacy_value,
    test_first_arrival_stores_the_keyed_tiebreaker_once,
    test_revisit_uses_a_new_key_and_keeps_the_first_ledger,
    test_another_vehicle_name_is_a_different_arrival_key,
    test_world_copy_keeps_the_same_tiebreaker_on_a_separate_ledger,
    test_order_control_type_is_not_part_of_the_arrival_key,
    test_physical_entry_does_not_record_an_arrival_tiebreaker,
    test_none_order_control_type_does_not_record_an_arrival_tiebreaker,
    test_ineligible_node_does_not_record_an_arrival_tiebreaker,
    test_arrival_recording_call_sites_match_the_world_contracts,
    test_arrival_record_keeps_visit_identity_and_attempt_counters,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Common seed/RNG arrival tiebreaker tests passed.")
