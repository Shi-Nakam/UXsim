# Verify Phase 4-6R Step 1 BATCH current-visit accessors and legacy earliest history.
#
# Run from the repository root:
#   python tests_order_control_batch_current_visit_accessors.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import math

import pytest

from uxsim import World


def _prepare_network(W):
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def expected_earliest_arrival_timestep(link_entry_timestep, link, W, tau_timesteps):
    free_flow_travel_timesteps = math.ceil((link.length / link.u) / W.DELTAT)
    return link_entry_timestep + free_flow_travel_timesteps + tau_timesteps


def _build_merge_world(name="batch_current_visit_accessors", *, order_control_type="batch"):
    W = World(
        name=name,
        deltan=1,
        tmax=400,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type=order_control_type,
    )
    W.addNode("dest", 2, 1)
    W.addLink("link1", "orig1", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("link2", "orig2", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    W.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)
    return W


def _advance_until_on_link(veh, link_name):
    while veh.link is None or veh.link.name != link_name:
        if not veh.W.check_simulation_ongoing():
            raise AssertionError(f"Vehicle did not reach link {link_name}")
        veh.W.exec_simulation(duration_t2=1)


def _ensure_current_visit_on_link(veh, merge, link):
    visit = veh.order_control_current_visit
    if visit is None or visit["node"] is not merge or visit["inlink"] is not link:
        veh.link = link
        veh.link_arrival_time = veh.W.T * veh.W.DELTAT
        veh.begin_order_control_visit_on_link_entry()
    return veh.order_control_current_visit


def test_trigger_rank_key_returns_current_visit_values():
    W = _build_merge_world("batch_trigger_rank_normal")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_trigger_rank")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = 30.0
    visit["arrival_tiebreaker"] = 0.42
    veh.order_control_node_arrival_times["merge"] = 10.0
    veh.order_control_node_arrival_tiebreakers["merge"] = 0.99

    key = veh.get_order_control_batch_trigger_rank_key(merge)
    assert key == (30.0, 0.42, veh.id)
    assert key != (
        veh.order_control_node_arrival_times["merge"],
        veh.order_control_node_arrival_tiebreakers["merge"],
        veh.id,
    )


def test_trigger_rank_key_raises_when_current_visit_missing():
    W = _build_merge_world("batch_trigger_rank_no_visit")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_no_visit")
    veh.order_control_current_visit = None
    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        veh.get_order_control_batch_trigger_rank_key(merge)


def test_trigger_rank_key_raises_when_node_mismatch():
    W = _build_merge_world("batch_trigger_rank_node_mismatch")
    merge = W.get_node("merge")
    dest = W.get_node("dest")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_node_mismatch")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = 10.0
    visit["arrival_tiebreaker"] = 0.1
    visit["node"] = dest
    with pytest.raises(ValueError, match="does not match BATCH node"):
        veh.get_order_control_batch_trigger_rank_key(merge)


def test_trigger_rank_key_raises_when_both_arrival_fields_none():
    W = _build_merge_world("batch_trigger_rank_both_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_both_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = None
    visit["arrival_tiebreaker"] = None
    with pytest.raises(ValueError, match="incomplete arrival state"):
        veh.get_order_control_batch_trigger_rank_key(merge)


def test_trigger_rank_key_raises_when_arrival_time_none_only():
    W = _build_merge_world("batch_trigger_rank_time_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_time_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = None
    visit["arrival_tiebreaker"] = 0.5
    with pytest.raises(ValueError, match="incomplete arrival state"):
        veh.get_order_control_batch_trigger_rank_key(merge)


def test_trigger_rank_key_raises_when_arrival_tiebreaker_none_only():
    W = _build_merge_world("batch_trigger_rank_tie_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_tie_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["arrival_time"] = 10.0
    visit["arrival_tiebreaker"] = None
    with pytest.raises(ValueError, match="incomplete arrival state"):
        veh.get_order_control_batch_trigger_rank_key(merge)


def test_earliest_accessor_returns_current_visit_value():
    W = _build_merge_world("batch_earliest_normal")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_earliest")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["earliest_arrival_timestep"] = 42
    veh.order_control_earliest_arrival_timesteps["merge"] = 7

    assert veh.get_order_control_batch_earliest_arrival_timestep(merge) == 42
    assert veh.get_order_control_batch_earliest_arrival_timestep(merge) != (
        veh.order_control_earliest_arrival_timesteps["merge"]
    )


def test_earliest_accessor_allows_pre_arrival_vehicle():
    W = _build_merge_world("batch_earliest_pre_arrival")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_pre_arrival")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["earliest_arrival_timestep"] = 15
    visit["arrival_time"] = None
    visit["arrival_tiebreaker"] = None

    assert veh.get_order_control_batch_earliest_arrival_timestep(merge) == 15


def test_earliest_accessor_raises_when_current_visit_missing():
    W = _build_merge_world("batch_earliest_no_visit")
    merge = W.get_node("merge")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_earliest_no_visit")
    veh.order_control_current_visit = None
    with pytest.raises(ValueError, match="order_control_current_visit is None"):
        veh.get_order_control_batch_earliest_arrival_timestep(merge)


def test_earliest_accessor_raises_when_node_mismatch():
    W = _build_merge_world("batch_earliest_node_mismatch")
    merge = W.get_node("merge")
    dest = W.get_node("dest")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_earliest_mismatch")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["earliest_arrival_timestep"] = 12
    visit["node"] = dest
    with pytest.raises(ValueError, match="does not match BATCH node"):
        veh.get_order_control_batch_earliest_arrival_timestep(merge)


def test_earliest_accessor_raises_when_earliest_none():
    W = _build_merge_world("batch_earliest_none")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_earliest_none")
    _advance_until_on_link(veh, "link1")
    visit = _ensure_current_visit_on_link(veh, merge, link1)
    visit["earliest_arrival_timestep"] = None
    with pytest.raises(ValueError, match="earliest_arrival_timestep is None"):
        veh.get_order_control_batch_earliest_arrival_timestep(merge)


def test_first_visit_earliest_same_value_in_legacy_and_current_visit():
    W = _build_merge_world("batch_first_visit_earliest")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_first_visit")
    _advance_until_on_link(veh, "link1")

    assert veh.order_control_visit_id == 1
    visit = veh.order_control_current_visit
    assert visit is not None
    assert "merge" in veh.order_control_earliest_arrival_timesteps
    assert (
        veh.order_control_earliest_arrival_timesteps["merge"]
        == visit["earliest_arrival_timestep"]
    )
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected = expected_earliest_arrival_timestep(
        link_entry, link1, W, W.order_control_batch_tau_timesteps
    )
    assert visit["earliest_arrival_timestep"] == expected


def test_revisit_preserves_legacy_earliest_first_visit_value():
    W = _build_merge_world("batch_revisit_legacy_earliest")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_revisit_legacy")

    _advance_until_on_link(veh, "link1")
    first_legacy = veh.order_control_earliest_arrival_timesteps["merge"]
    first_visit_id = veh.order_control_visit_id

    W.T = 50
    veh.link = link2
    veh.link_arrival_time = W.T * W.DELTAT
    veh.begin_order_control_visit_on_link_entry()

    assert veh.order_control_visit_id == first_visit_id + 1
    assert veh.order_control_earliest_arrival_timesteps["merge"] == first_legacy
    link_entry = int(round(veh.link_arrival_time / W.DELTAT))
    expected_revisit = expected_earliest_arrival_timestep(
        link_entry, link2, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_current_visit["earliest_arrival_timestep"] == expected_revisit
    assert expected_revisit != first_legacy
    assert veh.get_order_control_batch_earliest_arrival_timestep(merge) == expected_revisit


def test_ineligible_nodes_do_not_record_legacy_earliest():
    W = World(
        name="batch_ineligible_no_legacy",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode("ineligible", 1, 0, order_control_eligible=False, order_control_type="none")
    W.addNode("eligible_none", 2, 0, order_control_eligible=True, order_control_type="none")
    W.addNode("dest", 3, 0)
    W.addLink("l1", "orig", "ineligible", length=100, free_flow_speed=20, number_of_lanes=1)
    W.addLink("l2", "ineligible", "eligible_none", length=100, free_flow_speed=20, number_of_lanes=1)
    W.addLink("l3", "eligible_none", "dest", length=100, free_flow_speed=20, number_of_lanes=1)
    _prepare_network(W)

    veh = W.addVehicle("orig", "dest", 0, name="veh_ineligible_path")
    _advance_until_on_link(veh, "l1")
    assert veh.order_control_current_visit is None
    assert veh.order_control_earliest_arrival_timesteps == {}

    _advance_until_on_link(veh, "l2")
    assert veh.order_control_current_visit is None
    assert veh.order_control_earliest_arrival_timesteps == {}


def test_legacy_record_method_first_visit_only():
    W = _build_merge_world("batch_legacy_record_compat")
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    veh = W.addVehicle("orig1", "dest", 0, name="veh_legacy_record")
    veh.link = link1
    veh.link_arrival_time = 0.0
    assert veh.order_control_visit_id == 0
    assert veh.order_control_current_visit is None

    veh.record_order_control_earliest_arrival_timestep_for_current_link()
    expected = expected_earliest_arrival_timestep(
        0, link1, W, W.order_control_batch_tau_timesteps
    )
    assert veh.order_control_earliest_arrival_timesteps["merge"] == expected
    assert veh.order_control_visit_id == 0
    assert veh.order_control_current_visit is None

    veh.order_control_earliest_arrival_timesteps["merge"] = 999
    veh.record_order_control_earliest_arrival_timestep_for_current_link()
    assert veh.order_control_earliest_arrival_timesteps["merge"] == 999
    assert veh.order_control_visit_id == 0
    assert veh.order_control_current_visit is None


TESTS = [
    test_trigger_rank_key_returns_current_visit_values,
    test_trigger_rank_key_raises_when_current_visit_missing,
    test_trigger_rank_key_raises_when_node_mismatch,
    test_trigger_rank_key_raises_when_both_arrival_fields_none,
    test_trigger_rank_key_raises_when_arrival_time_none_only,
    test_trigger_rank_key_raises_when_arrival_tiebreaker_none_only,
    test_earliest_accessor_returns_current_visit_value,
    test_earliest_accessor_allows_pre_arrival_vehicle,
    test_earliest_accessor_raises_when_current_visit_missing,
    test_earliest_accessor_raises_when_node_mismatch,
    test_earliest_accessor_raises_when_earliest_none,
    test_first_visit_earliest_same_value_in_legacy_and_current_visit,
    test_revisit_preserves_legacy_earliest_first_visit_value,
    test_ineligible_nodes_do_not_record_legacy_earliest,
    test_legacy_record_method_first_visit_only,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control batch current visit accessor tests passed.")
