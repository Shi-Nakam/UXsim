# Verify BATCH candidate extraction grouped by inlink.
#
# Run from the repository root:
#   python tests_order_control_batch_candidates_by_inlink.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import copy

from uxsim import World


def _build_network(
    name="batch_candidates_by_inlink",
    merge_order_control_type="batch",
    merge_eligible=True,
):
    W = World(
        name=name,
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("orig3", 0, 4)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=merge_eligible,
        order_control_type=merge_order_control_type,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link3", "orig3", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    return W


def _make_vehicle(W, orig_name, name, departure_time=0):
    return W.addVehicle(orig_name, "dest", departure_time, name=name)


def _sync_pre_arrival_current_visit(veh, merge, link, earliest):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    visit = veh.order_control_current_visit
    if visit is None or visit.get("node") is not merge or visit.get("inlink") is not link:
        veh.order_control_current_visit = {
            "visit_id": veh.order_control_visit_id,
            "node": merge,
            "inlink": link,
            "earliest_arrival_timestep": earliest,
            "arrival_time": None,
            "arrival_tiebreaker": None,
            "batch_assignment": None,
        }
    else:
        visit["visit_id"] = veh.order_control_visit_id
        visit["node"] = merge
        visit["inlink"] = link
        visit["earliest_arrival_timestep"] = earliest
        visit["arrival_time"] = None
        visit["arrival_tiebreaker"] = None
        visit["batch_assignment"] = None


def _place_on_inlink(veh, link, earliest, x=100.0, v=20.0, route_next_link=None):
    merge = link.end_node
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = v
    veh.order_control_earliest_arrival_timesteps["merge"] = earliest
    _sync_pre_arrival_current_visit(veh, merge, link, earliest)
    if route_next_link is not None:
        veh.route_next_link = route_next_link
    link.vehicles.append(veh)


def _snapshot_state(merge, vehicles):
    return {
        "inlinks": copy.copy(merge.inlinks),
        "inlink_vehicles": {
            link.name: list(link.vehicles) for link in merge.inlinks.values()
        },
        "incoming_vehicles": list(merge.incoming_vehicles),
        "service_queue": list(merge.order_control_batch_service_queue),
        "next_id": merge.order_control_batch_next_id,
        "last_inlink": merge.last_order_control_inlink,
        "last_entry_timestep": merge.last_order_control_entry_timestep,
        "clearance_timesteps": merge.order_control_clearance_timesteps,
        "W_T": getattr(merge.W, "T", 0),
        "vehicles": {
            veh.name: {
                "batch_assignments": copy.copy(veh.order_control_batch_assignments),
                "earliest": copy.copy(veh.order_control_earliest_arrival_timesteps),
                "state": veh.state,
                "v": veh.v,
                "x": veh.x,
                "link": veh.link,
                "route_next_link": getattr(veh, "route_next_link", None),
            }
            for veh in vehicles
        },
    }


def test_basic_extraction_by_inlink():
    W = _build_network("batch_candidates_basic")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")

    veh1 = _make_vehicle(W, "orig1", "veh1")
    veh2 = _make_vehicle(W, "orig2", "veh2")
    _place_on_inlink(veh1, link1, earliest=9)
    _place_on_inlink(veh2, link2, earliest=10)

    result = merge.get_order_control_batch_candidates_by_inlink(10)

    assert isinstance(result, dict)
    assert set(result.keys()) == {link1, link2}
    assert result[link1] == [veh1]
    assert result[link2] == [veh2]
    assert result[link1][0] is veh1
    assert W.get_link("link3") not in result


def test_no_duplicate_from_incoming_vehicles():
    W = _build_network("batch_candidates_no_duplicate")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = _make_vehicle(W, "orig1", "veh_arrived")
    _place_on_inlink(veh, link1, earliest=10)
    merge.incoming_vehicles.append(veh)

    result = merge.get_order_control_batch_candidates_by_inlink(10)

    assert list(result.keys()) == [link1]
    assert result[link1] == [veh]
    assert result[link1].count(veh) == 1


def test_earliest_arrival_boundary():
    W = _build_network("batch_candidates_boundary")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    _place_on_inlink(veh_a, link1, earliest=9, x=150.0)
    _place_on_inlink(veh_b, link1, earliest=10, x=100.0)
    _place_on_inlink(veh_c, link1, earliest=11, x=50.0)

    result = merge.get_order_control_batch_candidates_by_inlink(10)

    assert result[link1] == [veh_a, veh_b]


def test_non_decreasing_earliest_valid():
    W = _build_network("batch_candidates_non_decreasing_ok")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    earliest_values = [9, 9, 10, 12]
    vehicles = []
    for idx, earliest in enumerate(earliest_values):
        veh = _make_vehicle(W, "orig1", f"veh_{idx}")
        _place_on_inlink(veh, link1, earliest=earliest, x=50.0 * (len(earliest_values) - idx))
        vehicles.append(veh)

    result = merge.get_order_control_batch_candidates_by_inlink(12)
    assert result[link1] == vehicles


def test_non_decreasing_earliest_invalid():
    W = _build_network("batch_candidates_non_decreasing_bad")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    for idx, earliest in enumerate([9, 12, 10]):
        veh = _make_vehicle(W, "orig1", f"veh_{idx}")
        _place_on_inlink(veh, link1, earliest=earliest, x=50.0 * (3 - idx))

    try:
        merge.get_order_control_batch_candidates_by_inlink(12)
        assert False, "expected ValueError for non-decreasing violation"
    except ValueError:
        pass


def test_missing_earliest_raises_and_does_not_fill():
    W = _build_network("batch_candidates_missing_earliest")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = _make_vehicle(W, "orig1", "veh_missing")
    veh.link = link1
    veh.state = "run"
    veh.x = 100.0
    veh.v = 20.0
    link1.vehicles.append(veh)

    before = copy.deepcopy(veh.order_control_earliest_arrival_timesteps)
    try:
        merge.get_order_control_batch_candidates_by_inlink(10)
        assert False, "expected ValueError for missing earliest record"
    except ValueError:
        pass
    assert veh.order_control_earliest_arrival_timesteps == before


def test_invalid_earliest_values_raise():
    invalid_values = [-1, 1.5, "10", True, None]
    for invalid in invalid_values:
        W = _build_network(f"batch_candidates_invalid_{invalid!r}")
        merge = W.get_node("merge")
        link1 = W.get_link("link1")
        veh = _make_vehicle(W, "orig1", "veh_invalid")
        _place_on_inlink(veh, link1, earliest=10)
        veh.order_control_earliest_arrival_timesteps["merge"] = invalid
        veh.order_control_current_visit["earliest_arrival_timestep"] = invalid
        try:
            merge.get_order_control_batch_candidates_by_inlink(10)
            assert False, f"expected ValueError for earliest={invalid!r}"
        except ValueError:
            pass


def test_assigned_prefix_valid_candidates():
    W = _build_network("batch_candidates_assigned_prefix")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    veh_d = _make_vehicle(W, "orig1", "veh_d")
    _place_on_inlink(veh_a, link1, earliest=8, x=160.0)
    _place_on_inlink(veh_b, link1, earliest=9, x=120.0)
    _place_on_inlink(veh_c, link1, earliest=10, x=80.0)
    _place_on_inlink(veh_d, link1, earliest=11, x=40.0)
    veh_a.order_control_batch_assignments["merge"] = 0
    veh_b.order_control_batch_assignments["merge"] = 1

    result = merge.get_order_control_batch_candidates_by_inlink(12)
    assert result[link1] == [veh_c, veh_d]


def test_assigned_prefix_violations_raise():
  cases = [
      ["veh_a", "veh_b", "veh_c"],
      ["veh_a", "veh_b", "veh_c"],
  ]
  assignment_patterns = [
      [False, True, False],
      [True, False, True],
  ]
  for names, assigned_flags in zip(cases, assignment_patterns):
      W = _build_network("batch_candidates_assignment_bad")
      merge = W.get_node("merge")
      link1 = W.get_link("link1")
      for idx, (veh_name, assigned) in enumerate(zip(names, assigned_flags)):
          veh = _make_vehicle(W, "orig1", veh_name)
          _place_on_inlink(veh, link1, earliest=10 + idx, x=50.0 * (3 - idx))
          if assigned:
              veh.order_control_batch_assignments["merge"] = idx
      try:
          merge.get_order_control_batch_candidates_by_inlink(20)
          assert False, f"expected ValueError for assignment pattern {assigned_flags}"
      except ValueError:
          pass


def test_other_node_assignment_is_unassigned_here():
    W = _build_network("batch_candidates_other_node_assignment")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = _make_vehicle(W, "orig1", "veh_other_node")
    _place_on_inlink(veh, link1, earliest=10)
    veh.order_control_batch_assignments["other_node"] = 0

    result = merge.get_order_control_batch_candidates_by_inlink(10)
    assert result[link1] == [veh]


def test_continuous_unassigned_suffix_candidates():
    W = _build_network("batch_candidates_suffix")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh_a = _make_vehicle(W, "orig1", "veh_a")
    veh_b = _make_vehicle(W, "orig1", "veh_b")
    veh_c = _make_vehicle(W, "orig1", "veh_c")
    veh_d = _make_vehicle(W, "orig1", "veh_d")
    _place_on_inlink(veh_a, link1, earliest=8, x=160.0)
    _place_on_inlink(veh_b, link1, earliest=10, x=120.0)
    _place_on_inlink(veh_c, link1, earliest=12, x=80.0)
    _place_on_inlink(veh_d, link1, earliest=15, x=40.0)
    veh_a.order_control_batch_assignments["merge"] = 0

    result = merge.get_order_control_batch_candidates_by_inlink(12)
    assert result[link1] == [veh_b, veh_c]


def test_fifo_order_preserved_without_resorting():
    W = _build_network("batch_candidates_fifo")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh1 = _make_vehicle(W, "orig1", "veh1")
    veh2 = _make_vehicle(W, "orig1", "veh2")
    veh3 = _make_vehicle(W, "orig1", "veh3")
    _place_on_inlink(veh1, link1, earliest=10, x=300.0)
    _place_on_inlink(veh2, link1, earliest=10, x=200.0)
    _place_on_inlink(veh3, link1, earliest=11, x=100.0)

    original = list(link1.vehicles)
    result = merge.get_order_control_batch_candidates_by_inlink(12)

    assert list(link1.vehicles) == original
    assert result[link1] == [veh1, veh2, veh3]


def test_zero_speed_vehicle_is_candidate():
    W = _build_network("batch_candidates_zero_speed")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = _make_vehicle(W, "orig1", "veh_stopped")
    _place_on_inlink(veh, link1, earliest=10, v=0.0)

    result = merge.get_order_control_batch_candidates_by_inlink(10)
    assert result[link1] == [veh]


def test_non_run_vehicle_raises():
    W = _build_network("batch_candidates_non_run")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = _make_vehicle(W, "orig1", "veh_non_run")
    _place_on_inlink(veh, link1, earliest=10)
    veh.state = "end"

    try:
        merge.get_order_control_batch_candidates_by_inlink(10)
        assert False, "expected ValueError for non-run vehicle"
    except ValueError:
        pass


def test_route_next_link_none_is_candidate():
    W = _build_network("batch_candidates_route_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")

    veh = _make_vehicle(W, "orig1", "veh_route_none")
    _place_on_inlink(veh, link1, earliest=10, route_next_link=None)
    veh.route_next_link = None

    assert veh.route_next_link is None

    result = merge.get_order_control_batch_candidates_by_inlink(10)
    assert result[link1] == [veh]


def test_invalid_node_settings_raise():
    W_none = _build_network("batch_candidates_node_none", merge_order_control_type="none")
    W_fcfs = _build_network("batch_candidates_node_fcfs", merge_order_control_type="fcfs")
    W_ineligible = _build_network("batch_candidates_node_ineligible")
    W_ineligible.get_node("merge").order_control_eligible = False

    for merge in (W_none.get_node("merge"), W_fcfs.get_node("merge"), W_ineligible.get_node("merge")):
        try:
            merge.get_order_control_batch_candidates_by_inlink(10)
            assert False, f"expected ValueError for node {merge.name}"
        except ValueError:
            pass


def test_empty_result_for_valid_batch_node_with_no_candidates():
    W = _build_network("batch_candidates_empty")
    merge = W.get_node("merge")
    assert merge.get_order_control_batch_candidates_by_inlink(10) == {}


def test_t_trigger_validation():
    W = _build_network("batch_candidates_t_trigger")
    merge = W.get_node("merge")

    invalid_values = [-1, 1.5, "10", True, False, None]
    for invalid in invalid_values:
        try:
            merge.get_order_control_batch_candidates_by_inlink(invalid)
            assert False, f"expected ValueError for t_trigger={invalid!r}"
        except ValueError:
            pass

    for valid in (0, 1, 10):
        assert merge.get_order_control_batch_candidates_by_inlink(valid) == {}


def test_inlink_end_node_mismatch_raises():
    W = _build_network("batch_candidates_inlink_end_node")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    original_end_node = link1.end_node
    link1.end_node = W.get_node("dest")

    try:
        merge.get_order_control_batch_candidates_by_inlink(10)
        assert False, "expected ValueError for inlink.end_node mismatch"
    except ValueError:
        pass
    finally:
        link1.end_node = original_end_node


def test_vehicle_link_mismatch_raises():
    W = _build_network("batch_candidates_vehicle_link")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")

    veh = _make_vehicle(W, "orig1", "veh_wrong_link")
    _place_on_inlink(veh, link1, earliest=10)
    veh.link = link2

    try:
        merge.get_order_control_batch_candidates_by_inlink(10)
        assert False, "expected ValueError for veh.link mismatch"
    except ValueError:
        pass


def test_multiple_inlinks_return_independent_lists():
    W = _build_network("batch_candidates_independent_lists")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")

    veh1 = _make_vehicle(W, "orig1", "veh1")
    veh2 = _make_vehicle(W, "orig2", "veh2")
    _place_on_inlink(veh1, link1, earliest=10)
    _place_on_inlink(veh2, link2, earliest=11)

    result = merge.get_order_control_batch_candidates_by_inlink(12)
    assert result[link1] is not result[link2]

    result[link1].append("mutated")
    assert result[link2] == [veh2]
    assert list(link1.vehicles) == [veh1]
    assert list(link2.vehicles) == [veh2]


def test_no_side_effects():
    W = _build_network("batch_candidates_no_side_effects")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")

    veh1 = _make_vehicle(W, "orig1", "veh1")
    veh2 = _make_vehicle(W, "orig2", "veh2")
    _place_on_inlink(veh1, link1, earliest=10)
    _place_on_inlink(veh2, link2, earliest=11)
    merge.incoming_vehicles.append(veh1)
    vehicles = [veh1, veh2]

    before = _snapshot_state(merge, vehicles)
    result = merge.get_order_control_batch_candidates_by_inlink(12)
    after = _snapshot_state(merge, vehicles)

    assert result[link1] == [veh1]
    assert result[link2] == [veh2]
    assert before == after


def main():
    test_basic_extraction_by_inlink()
    test_no_duplicate_from_incoming_vehicles()
    test_earliest_arrival_boundary()
    test_non_decreasing_earliest_valid()
    test_non_decreasing_earliest_invalid()
    test_missing_earliest_raises_and_does_not_fill()
    test_invalid_earliest_values_raise()
    test_assigned_prefix_valid_candidates()
    test_assigned_prefix_violations_raise()
    test_other_node_assignment_is_unassigned_here()
    test_continuous_unassigned_suffix_candidates()
    test_fifo_order_preserved_without_resorting()
    test_zero_speed_vehicle_is_candidate()
    test_non_run_vehicle_raises()
    test_route_next_link_none_is_candidate()
    test_invalid_node_settings_raise()
    test_empty_result_for_valid_batch_node_with_no_candidates()
    test_t_trigger_validation()
    test_inlink_end_node_mismatch_raises()
    test_vehicle_link_mismatch_raises()
    test_multiple_inlinks_return_independent_lists()
    test_no_side_effects()
    print("Order-control batch candidates by inlink tests passed.")


if __name__ == "__main__":
    main()
