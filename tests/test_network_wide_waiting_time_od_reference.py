"""OD minimum free-flow reference, AWT, AWWT, and detour time.

Small worlds only. This file does not import helpers from the route-conditional
test module, and it does not run the 320-OD or 3,000-vehicle checks.
"""

from dataclasses import replace
from types import MappingProxyType

import pytest

from uxsim import World
from uxsim.analyzer import Analyzer
from uxsim.uxsim import Link, Node, Vehicle
import uxsim.network_wide_waiting_time_evaluation as evaluation

PARTICIPATING = "cohort_participating"
NONPARTICIPATING = "cohort_nonparticipating"


def _world(name, reaction_time=1.0, tmax=400.0):
    return World(
        name=name,
        deltan=1,
        reaction_time=reaction_time,
        tmax=tmax,
        random_seed=0,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        hard_deterministic_mode=True,
        vehicle_logging_timestep_interval=1,
    )


def _add_link(
    world,
    name,
    start_name,
    end_name,
    length,
    speed,
    capacity_in=None,
    user_function=None,
):
    """Add a link. capacity_in and user_function are passed to addLink when set.

    If capacity_in is 0, init_after_tmax_fix sets capacity_in_remain from it;
    changing capacity_in after construction does not fix remain.
    """
    kwargs = {
        "length": length,
        "free_flow_speed": speed,
        "number_of_lanes": 1,
        "jam_density": 0.2,
        "signal_group": [0],
    }
    if capacity_in is not None:
        kwargs["capacity_in"] = capacity_in
    if user_function is not None:
        kwargs["user_function"] = user_function
    return world.addLink(
        name,
        start_name,
        end_name,
        **kwargs,
    )


def _add_vehicle(world, name, origin_name, destination_name, departure_timestep, route_names):
    vehicle = world.addVehicle(
        origin_name,
        destination_name,
        departure_timestep,
        name=name,
        departure_time_is_time_step=1,
        mode="single_trip",
    )
    if route_names is not None:
        vehicle.enforce_route(list(route_names))
    return vehicle


def _chain_world(name, prefix, length, speed, vehicle_name, departure_timestep=0):
    world = _world(name)
    world.addNode(f"{prefix}_orig", 0.0, 0.0, signal=[0])
    world.addNode(f"{prefix}_dest", 1.0, 0.0, signal=[0])
    link_name = f"{prefix}_link"
    _add_link(world, link_name, f"{prefix}_orig", f"{prefix}_dest", length, speed)
    _add_vehicle(
        world,
        vehicle_name,
        f"{prefix}_orig",
        f"{prefix}_dest",
        departure_timestep,
        [link_name],
    )
    return world


def _release_inflow_at_timestep_5(link):
    if link.W.T == 5:
        link.capacity_in = 1.0
        link.capacity_in_remain = link.W.DELTAN


def _vot_map(names, vot=1.0):
    values = {}
    for name in names:
        values[name] = vot
    return values


def _cohort_map(names, cohort=PARTICIPATING):
    values = {}
    for name in names:
        values[name] = cohort
    return values


def _evaluate(world, names, vot=1.0, cohort=PARTICIPATING, method_name="fcfs", **kwargs):
    vot_by_name = kwargs.pop("true_vot_per_second_by_vehicle_name", None)
    if vot_by_name is None:
        vot_by_name = _vot_map(names, vot)
    cohort_by_name = kwargs.pop("evaluation_cohort_by_vehicle_name", None)
    if cohort_by_name is None:
        cohort_by_name = _cohort_map(names, cohort)
    return evaluation.evaluate_network_wide_waiting_time(
        world,
        method_name,
        names,
        vot_by_name,
        cohort_by_name,
        **kwargs,
    )


def _assert_no_simulation_object(value, seen=None):
    if seen is None:
        seen = []
    if id(value) in seen:
        return
    seen.append(id(value))
    assert not isinstance(value, (World, Vehicle, Node, Link, Analyzer))
    if isinstance(value, (str, bytes)):
        return
    if isinstance(value, dict) or isinstance(value, MappingProxyType):
        for key, item in value.items():
            _assert_no_simulation_object(key, seen)
            _assert_no_simulation_object(item, seen)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_simulation_object(item, seen)
        return
    if hasattr(value, "__dataclass_fields__"):
        for field_name in value.__dataclass_fields__:
            _assert_no_simulation_object(getattr(value, field_name), seen)


def _assert_route_conditional_properties(record):
    assert record.route_conditional_minimum_trip_timesteps == (
        record.reference_minimum_trip_timesteps
    )
    assert record.route_conditional_minimum_trip_time_s == record.minimum_trip_time_s
    assert record.route_conditional_waiting_time_timesteps == (
        record.cumulative_waiting_time_timesteps
    )
    assert record.route_conditional_waiting_time_s == record.cumulative_waiting_time_s
    assert record.weighted_route_conditional_waiting_time == (
        record.weighted_cumulative_waiting_time
    )


def _assert_vehicle_identity(record):
    assert record.od_based_waiting_time_timesteps == (
        record.cumulative_waiting_time_timesteps + record.detour_time_timesteps
    )
    assert record.od_based_waiting_time_timesteps == (
        record.actual_trip_timesteps - record.od_minimum_free_flow_trip_timesteps
    )
    assert record.detour_time_timesteps == (
        record.reference_minimum_trip_timesteps
        - record.od_minimum_free_flow_trip_timesteps
    )
    assert record.weighted_od_based_waiting_time == (
        record.od_based_waiting_time_s * record.true_vot_per_second
    )
    assert record.weighted_detour_time == record.detour_time_s * record.true_vot_per_second
    assert record.weighted_od_based_waiting_time == (
        record.weighted_cumulative_waiting_time + record.weighted_detour_time
    )
    _assert_route_conditional_properties(record)


def _assert_summary_identity(summary):
    assert summary.average_waiting_time_s == (
        summary.total_od_based_waiting_time_s / summary.vehicle_count
    )
    assert summary.average_weighted_waiting_time == (
        summary.total_weighted_od_based_waiting_time / summary.vehicle_count
    )
    assert summary.average_detour_time_s == (
        summary.total_detour_time_s / summary.vehicle_count
    )
    assert summary.total_route_conditional_waiting_time_s == (
        summary.total_cumulative_waiting_time_s
    )
    assert summary.route_conditional_average_waiting_time_s == (
        summary.average_cumulative_waiting_time_s
    )
    assert summary.total_weighted_route_conditional_waiting_time == (
        summary.total_weighted_cumulative_waiting_time
    )
    assert summary.route_conditional_average_weighted_waiting_time == (
        summary.average_weighted_cumulative_waiting_time
    )
    assert summary.total_weighted_od_based_waiting_time == (
        summary.total_weighted_route_conditional_waiting_time
        + summary.total_weighted_detour_time
    )
    cohort_od = 0.0
    cohort_detour = 0.0
    cohort_count = 0
    for cohort in summary.cohort_summaries:
        assert cohort.average_waiting_time_s == (
            cohort.total_od_based_waiting_time_s / cohort.vehicle_count
        )
        assert cohort.average_weighted_waiting_time == (
            cohort.total_weighted_od_based_waiting_time / cohort.vehicle_count
        )
        assert cohort.total_route_conditional_waiting_time_s == (
            cohort.total_cumulative_waiting_time_s
        )
        assert cohort.total_weighted_od_based_waiting_time == (
            cohort.total_weighted_route_conditional_waiting_time
            + cohort.total_weighted_detour_time
        )
        cohort_od += cohort.total_od_based_waiting_time_s
        cohort_detour += cohort.total_detour_time_s
        cohort_count += cohort.vehicle_count
    assert cohort_count == summary.vehicle_count
    assert cohort_od == summary.total_od_based_waiting_time_s
    assert cohort_detour == summary.total_detour_time_s


def _finished_chain(name="chain", vehicle_name="veh"):
    world = _chain_world(name, "only", 200.0, 10.0, vehicle_name)
    world.exec_simulation()
    return world


def _detour_world(vehicle_names=("veh",), departure_timesteps=None):
    """Long enforced route plus one shorter direct link."""

    world = _world("detour")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("mid", 1.0, 0.0, signal=[0])
    world.addNode("dest", 2.0, 0.0, signal=[0])
    _add_link(world, "long_0", "orig", "mid", 1000.0, 10.0)
    _add_link(world, "long_1", "mid", "dest", 1000.0, 10.0)
    _add_link(world, "short", "orig", "dest", 100.0, 10.0)
    if departure_timesteps is None:
        departure_timesteps = []
        for index in range(len(vehicle_names)):
            departure_timesteps.append(0)
    for index, vehicle_name in enumerate(vehicle_names):
        _add_vehicle(
            world,
            vehicle_name,
            "orig",
            "dest",
            departure_timesteps[index],
            ["long_0", "long_1"],
        )
    world.exec_simulation()
    return world


def test_detour_is_zero_when_the_traveled_route_is_the_only_route():
    world = _finished_chain()
    result = _evaluate(world, ["veh"], vot=2.0)
    record = result.vehicle_records[0]

    assert record.detour_time_timesteps == 0
    assert record.detour_time_s == 0.0
    assert record.weighted_detour_time == 0.0
    assert record.od_based_waiting_time_timesteps == record.cumulative_waiting_time_timesteps
    assert record.od_based_waiting_time_s == record.cumulative_waiting_time_s
    assert record.cumulative_waiting_time_timesteps == 0
    assert result.summary.average_waiting_time_s == (
        result.summary.average_cumulative_waiting_time_s
    )
    assert result.summary.average_weighted_waiting_time == (
        result.summary.average_weighted_cumulative_waiting_time
    )
    assert record.od_reference_route_audit_identity == ("only_link",)
    assert record.origin_name == "only_orig"
    assert record.destination_name == "only_dest"
    assert record.od_reference_departure_timestep == 0
    assert type(record.od_reference_arrival_timestep) is int
    assert record.od_reference_signature_digest == result.network_free_flow_signature_digest
    _assert_vehicle_identity(record)
    _assert_summary_identity(result.summary)
    assert result.counters.unique_od_reference_count == 1
    assert result.counters.od_reference_replay_run_count == 1
    assert result.counters.od_reference_reuse_count == 0
    assert result.counters.negative_od_based_waiting_time_count == 0
    assert result.counters.negative_detour_time_count == 0


def test_positive_detour_keeps_route_conditional_fields():
    world = _detour_world()
    result = _evaluate(world, ["veh"], vot=3.0)
    record = result.vehicle_records[0]

    assert record.route_audit_identity == ("long_0", "long_1")
    assert record.od_reference_route_audit_identity == ("short",)
    assert record.detour_time_timesteps > 0
    assert record.cumulative_waiting_time_timesteps == 0
    assert record.od_based_waiting_time_timesteps == record.detour_time_timesteps
    assert record.cumulative_waiting_time_s == 0.0
    assert result.summary.average_cumulative_waiting_time_s == 0.0
    assert result.summary.average_waiting_time_s == record.od_based_waiting_time_s
    assert result.summary.average_waiting_time_s > (
        result.summary.average_cumulative_waiting_time_s
    )
    assert result.summary.average_weighted_waiting_time == (
        record.weighted_od_based_waiting_time
    )
    assert result.summary.average_weighted_waiting_time > (
        result.summary.average_weighted_cumulative_waiting_time
    )
    _assert_vehicle_identity(record)
    _assert_summary_identity(result.summary)
    stored = result.od_reference_results_by_od_key[("orig", "dest")]
    assert stored.validation_passed is True
    assert stored.od_reference_world_deltan == 1
    assert type(stored.od_reference_world_deltan) is int
    assert stored.od_minimum_free_flow_trip_timesteps == (
        record.od_minimum_free_flow_trip_timesteps
    )


def test_same_od_shares_one_reference():
    world = _detour_world(("veh_a", "veh_b"), [0, 50])
    result = _evaluate(world, ["veh_a", "veh_b"])

    assert result.counters.evaluated_vehicle_count == 2
    assert result.counters.unique_od_reference_count == 1
    assert result.counters.od_reference_replay_run_count == 1
    assert result.counters.od_reference_reuse_count == 1
    assert result.counters.unique_od_route_audit_identity_count == 1
    assert result.counters.duplicate_od_route_audit_identity_observation_count == 1
    assert len(result.od_reference_results_by_od_key) == 1
    first = result.vehicle_records[0]
    second = result.vehicle_records[1]
    assert first.od_minimum_free_flow_trip_timesteps == (
        second.od_minimum_free_flow_trip_timesteps
    )
    assert first.od_reference_route_audit_identity == ("short",)
    assert second.od_reference_route_audit_identity == ("short",)
    _assert_vehicle_identity(first)
    _assert_vehicle_identity(second)


def test_different_od_pairs_are_not_shared():
    world = _world("two_od")
    world.addNode("a_orig", 0.0, 0.0, signal=[0])
    world.addNode("a_dest", 1.0, 0.0, signal=[0])
    world.addNode("b_orig", 0.0, 1.0, signal=[0])
    world.addNode("b_dest", 1.0, 1.0, signal=[0])
    _add_link(world, "a_link", "a_orig", "a_dest", 200.0, 10.0)
    _add_link(world, "b_link", "b_orig", "b_dest", 300.0, 10.0)
    _add_vehicle(world, "veh_a", "a_orig", "a_dest", 0, ["a_link"])
    _add_vehicle(world, "veh_b", "b_orig", "b_dest", 0, ["b_link"])
    world.exec_simulation()

    result = _evaluate(world, ["veh_a", "veh_b"])
    assert result.counters.unique_od_reference_count == 2
    assert result.counters.od_reference_replay_run_count == 2
    assert result.counters.od_reference_reuse_count == 0
    assert set(result.od_reference_results_by_od_key) == {
        ("a_orig", "a_dest"),
        ("b_orig", "b_dest"),
    }
    assert result.vehicle_records[0].od_reference_route_audit_identity == ("a_link",)
    assert result.vehicle_records[1].od_reference_route_audit_identity == ("b_link",)
    assert result.vehicle_records[0].od_minimum_free_flow_trip_timesteps != (
        result.vehicle_records[1].od_minimum_free_flow_trip_timesteps
    )


def test_cohort_averages_use_each_cohort_count():
    world = _world("cohorts")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("mid", 1.0, 0.0, signal=[0])
    world.addNode("dest", 2.0, 0.0, signal=[0])
    world.addNode("other_orig", 0.0, 1.0, signal=[0])
    world.addNode("other_dest", 1.0, 1.0, signal=[0])
    _add_link(world, "long_0", "orig", "mid", 1000.0, 10.0)
    _add_link(world, "long_1", "mid", "dest", 1000.0, 10.0)
    _add_link(world, "short", "orig", "dest", 100.0, 10.0)
    _add_link(world, "other", "other_orig", "other_dest", 200.0, 10.0)
    _add_vehicle(world, "long_veh", "orig", "dest", 0, ["long_0", "long_1"])
    _add_vehicle(world, "other_veh", "other_orig", "other_dest", 0, ["other"])
    world.exec_simulation()

    result = _evaluate(
        world,
        ["long_veh", "other_veh"],
        method_name="tvt_mp",
        true_vot_per_second_by_vehicle_name={"long_veh": 2.0, "other_veh": 4.0},
        evaluation_cohort_by_vehicle_name={
            "long_veh": PARTICIPATING,
            "other_veh": NONPARTICIPATING,
        },
    )
    summaries = result.summary.cohort_summaries
    assert [item.evaluation_cohort for item in summaries] == [
        PARTICIPATING,
        NONPARTICIPATING,
    ]
    assert summaries[0].vehicle_count == 1
    assert summaries[1].vehicle_count == 1
    assert summaries[0].total_detour_time_s > 0.0
    assert summaries[1].total_detour_time_s == 0.0
    assert summaries[0].average_waiting_time_s == summaries[0].total_od_based_waiting_time_s
    assert summaries[1].average_waiting_time_s == summaries[1].total_od_based_waiting_time_s
    assert result.summary.average_waiting_time_s == (
        result.summary.total_od_based_waiting_time_s / 2
    )
    long_record = result.vehicle_records[0]
    assert long_record.cumulative_waiting_time_timesteps == 0
    assert long_record.od_based_waiting_time_timesteps == long_record.detour_time_timesteps
    _assert_vehicle_identity(long_record)
    _assert_vehicle_identity(result.vehicle_records[1])
    _assert_summary_identity(result.summary)


def test_mode_other_than_single_trip_is_rejected():
    world = _finished_chain("mode")
    world.VEHICLES["veh"].mode = "taxi"
    with pytest.raises(ValueError, match="single_trip"):
        _evaluate(world, ["veh"])


def test_invalid_origin_is_rejected():
    world = _finished_chain("bad_origin")
    other = _world("outside")
    other.addNode("outside_node", 0.0, 0.0, signal=[0])
    world.VEHICLES["veh"].orig = other.NODES[0]
    with pytest.raises(ValueError, match="origin"):
        _evaluate(world, ["veh"])


def test_invalid_destination_is_rejected():
    world = _finished_chain("bad_dest")
    world.VEHICLES["veh"].dest = "not-a-node"
    with pytest.raises(ValueError, match="destination"):
        _evaluate(world, ["veh"])


def test_same_origin_and_destination_is_rejected():
    world = _finished_chain("same_node")
    vehicle = world.VEHICLES["veh"]
    vehicle.dest = vehicle.orig
    with pytest.raises(ValueError, match="same node"):
        _evaluate(world, ["veh"])


def test_nonzero_route_choice_penalty_is_outside_scope():
    world = _finished_chain("penalty")
    world.LINKS[0].route_choice_penalty = 2.0
    with pytest.raises(ValueError, match="route_choice_penalty"):
        _evaluate(world, ["veh"])


def test_capacity_in_zero_is_outside_scope():
    world = _finished_chain("closed")
    world.LINKS[0].capacity_in = 0
    with pytest.raises(ValueError, match="capacity_in"):
        _evaluate(world, ["veh"])


def test_unfinished_od_reference_stops(monkeypatch):
    world = _finished_chain("unfinished_od")

    def tiny_budget(real_world):
        return 0.0

    monkeypatch.setattr(evaluation, "_od_reference_tmax_seconds", tiny_budget)
    with pytest.raises(RuntimeError, match="did not finish"):
        _evaluate(world, ["veh"])


def test_discontinuous_od_route_stops(monkeypatch):
    world = _world("broken_route")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("mid", 1.0, 0.0, signal=[0])
    world.addNode("dest", 2.0, 0.0, signal=[0])
    world.addNode("side", 0.0, 1.0, signal=[0])
    _add_link(world, "first", "orig", "mid", 100.0, 10.0)
    _add_link(world, "second", "mid", "dest", 100.0, 10.0)
    _add_link(world, "side_link", "orig", "side", 100.0, 10.0)
    _add_vehicle(world, "veh", "orig", "dest", 0, ["first", "second"])
    world.exec_simulation()

    def disconnected(vehicle):
        return ["first", "side_link"]

    monkeypatch.setattr(evaluation, "_od_traveled_link_names", disconnected)
    with pytest.raises(RuntimeError, match="not connected"):
        _evaluate(world, ["veh"])


def test_looped_od_route_stops(monkeypatch):
    world = _finished_chain("loop")

    def repeated(vehicle):
        return ["only_link", "only_link"]

    monkeypatch.setattr(evaluation, "_od_traveled_link_names", repeated)
    with pytest.raises(RuntimeError, match="repeats a link"):
        _evaluate(world, ["veh"])


def test_signature_mismatch_is_not_stored(monkeypatch):
    world = _finished_chain("digest")
    real_run = evaluation._run_od_reference_replay

    def wrong_digest(real_world, od_key, signature_digest, method_name):
        result = real_run(real_world, od_key, signature_digest, method_name)
        return replace(result, network_free_flow_signature_digest="0" * 64)

    monkeypatch.setattr(evaluation, "_run_od_reference_replay", wrong_digest)
    with pytest.raises(RuntimeError, match="signature digest"):
        _evaluate(world, ["veh"])


def test_negative_od_based_waiting_is_not_rounded_to_zero(monkeypatch):
    world = _finished_chain("negative_od")
    real_run = evaluation._run_od_reference_replay

    def too_long(real_world, od_key, signature_digest, method_name):
        result = real_run(real_world, od_key, signature_digest, method_name)
        extra = 5
        return replace(
            result,
            od_reference_arrival_timestep=result.od_reference_arrival_timestep + extra,
            od_minimum_free_flow_trip_timesteps=(
                result.od_minimum_free_flow_trip_timesteps + extra
            ),
            od_minimum_free_flow_trip_time_s=(
                result.od_minimum_free_flow_trip_time_s
                + extra * result.od_reference_world_deltat
            ),
        )

    monkeypatch.setattr(evaluation, "_run_od_reference_replay", too_long)
    with pytest.raises(RuntimeError, match="OD-based waiting timesteps are negative"):
        _evaluate(world, ["veh"])


def test_negative_detour_is_not_rounded_to_zero(monkeypatch):
    world = _world("negative_detour")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("dest", 1.0, 0.0, signal=[0])
    _add_link(
        world,
        "wait_link",
        "orig",
        "dest",
        200.0,
        10.0,
        capacity_in=0.0,
        user_function=_release_inflow_at_timestep_5,
    )
    _add_vehicle(world, "veh", "orig", "dest", 0, ["wait_link"])
    world.exec_simulation()
    assert world.LINKS[0].capacity_in == 1.0

    baseline = _evaluate(world, ["veh"])
    base_record = baseline.vehicle_records[0]
    assert base_record.cumulative_waiting_time_timesteps > 0
    assert base_record.od_based_waiting_time_timesteps >= 0
    assert base_record.detour_time_timesteps == 0

    real_run = evaluation._run_od_reference_replay

    def slightly_longer_than_route(real_world, od_key, signature_digest, method_name):
        result = real_run(real_world, od_key, signature_digest, method_name)
        extra = 1
        return replace(
            result,
            od_reference_arrival_timestep=result.od_reference_arrival_timestep + extra,
            od_minimum_free_flow_trip_timesteps=(
                result.od_minimum_free_flow_trip_timesteps + extra
            ),
            od_minimum_free_flow_trip_time_s=(
                result.od_minimum_free_flow_trip_time_s
                + extra * result.od_reference_world_deltat
            ),
        )

    monkeypatch.setattr(evaluation, "_run_od_reference_replay", slightly_longer_than_route)
    with pytest.raises(RuntimeError, match="detour timesteps are negative"):
        _evaluate(world, ["veh"])


def test_od_reference_uses_route_choice_without_enforce_route(monkeypatch):
    world = _detour_world()
    enforce_world_names = []
    od_vehicles = []
    real_enforce = Vehicle.enforce_route
    real_add = World.addVehicle

    def wrapped_enforce(self, route, set_avoid=False):
        enforce_world_names.append(self.W.name)
        return real_enforce(self, route, set_avoid=set_avoid)

    def wrapped_add(self, *args, **kwargs):
        vehicle = real_add(self, *args, **kwargs)
        if self.name == evaluation._OD_REFERENCE_WORLD_NAME:
            od_vehicles.append(vehicle)
        return vehicle

    monkeypatch.setattr(Vehicle, "enforce_route", wrapped_enforce)
    monkeypatch.setattr(World, "addVehicle", wrapped_add)
    result = _evaluate(world, ["veh"])

    assert od_vehicles
    for vehicle in od_vehicles:
        assert vehicle.specified_route is None
        assert vehicle.mode == "single_trip"
        assert vehicle.W is not world
        assert vehicle.orig is not world.VEHICLES["veh"].orig
        assert vehicle.dest is not world.VEHICLES["veh"].dest
    assert evaluation._OD_REFERENCE_WORLD_NAME not in enforce_world_names
    assert "network_wide_waiting_time_reference" in enforce_world_names
    assert result.vehicle_records[0].od_reference_route_audit_identity == ("short",)


def test_runner_travel_time_matches_exec_simulation(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    world = _finished_chain("runner_match")
    result = _evaluate(world, ["veh"])
    record = result.vehicle_records[0]
    twin = evaluation._build_od_reference_world(
        world,
        record.origin_name,
        record.destination_name,
    )
    twin.exec_simulation()
    twin_vehicle = next(iter(twin.VEHICLES.values()))

    assert twin_vehicle.specified_route is None
    assert twin_vehicle.travel_time == record.od_minimum_free_flow_trip_time_s
    assert twin.name == evaluation._OD_REFERENCE_WORLD_NAME
    assert twin is not world


def test_signature_digest_is_stable_and_follows_length_and_u():
    world = _finished_chain("signature")
    first = _evaluate(world, ["veh"])
    second = _evaluate(world, ["veh"])
    assert first.network_free_flow_signature_digest == (
        second.network_free_flow_signature_digest
    )
    assert len(first.network_free_flow_signature_digest) == 64
    assert "network_free_flow_signature" not in first.__dataclass_fields__

    link = world.LINKS[0]
    original_length = link.length
    original_u = link.u
    link.length = original_length / 2.0
    shorter = _evaluate(world, ["veh"])
    assert shorter.network_free_flow_signature_digest != (
        first.network_free_flow_signature_digest
    )
    link.length = original_length
    link.u = original_u * 2.0
    faster = _evaluate(world, ["veh"])
    assert faster.network_free_flow_signature_digest != (
        first.network_free_flow_signature_digest
    )


def test_od_reference_is_not_carried_between_evaluations():
    world = _finished_chain("isolated")
    first = _evaluate(world, ["veh"])
    second = _evaluate(world, ["veh"])

    assert first.od_reference_results_by_od_key is not (
        second.od_reference_results_by_od_key
    )
    assert first.od_route_audit_identities_by_od_key is not (
        second.od_route_audit_identities_by_od_key
    )
    assert second.counters.od_reference_replay_run_count == 1
    assert second.counters.od_reference_reuse_count == 0
    assert second.counters.unique_od_reference_count == 1
    with pytest.raises(TypeError):
        second.od_reference_results_by_od_key[("extra", "extra")] = None
    identity = second.od_route_audit_identities_by_od_key[("only_orig", "only_dest")]
    assert isinstance(identity, tuple)
    assert isinstance(second.od_reference_results_by_od_key, MappingProxyType)


def test_evaluation_does_not_change_the_real_world_or_write_files(
    monkeypatch,
    tmp_path,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    world = _finished_chain("side_effect")
    before_files = set(tmp_path.rglob("*"))
    before_time = (world.T, world.TIME, world.DELTAT, world.DELTAN)
    vehicle = world.VEHICLES["veh"]
    before_vehicle = (
        vehicle.state,
        vehicle.departure_time,
        vehicle.arrival_time,
        vehicle.travel_time,
        vehicle.orig,
        vehicle.dest,
    )
    link = world.LINKS[0]
    before_link = (link.length, link.u, link.capacity_in, link.route_choice_penalty)

    def reject_exec(*args, **kwargs):
        raise AssertionError("exec_simulation was called during evaluation")

    def reject_analyzer(*args, **kwargs):
        raise AssertionError("Analyzer was created during evaluation")

    monkeypatch.setattr(World, "exec_simulation", reject_exec)
    monkeypatch.setattr(Analyzer, "__init__", reject_analyzer)
    result = _evaluate(world, ["veh"], vot=0.0)
    captured = capsys.readouterr()

    assert (world.T, world.TIME, world.DELTAT, world.DELTAN) == before_time
    assert (
        vehicle.state,
        vehicle.departure_time,
        vehicle.arrival_time,
        vehicle.travel_time,
        vehicle.orig,
        vehicle.dest,
    ) == before_vehicle
    assert (link.length, link.u, link.capacity_in, link.route_choice_penalty) == before_link
    assert set(tmp_path.rglob("*")) == before_files
    assert captured.out == ""
    assert captured.err == ""
    record = result.vehicle_records[0]
    assert record.true_vot_per_second == 0.0
    assert record.weighted_od_based_waiting_time == 0.0
    assert record.weighted_detour_time == 0.0
    assert result.summary.average_weighted_waiting_time == 0.0
    _assert_no_simulation_object(result)


def test_true_vot_zero_keeps_positive_od_seconds():
    world = _world("vot_zero")
    world.addNode("orig", 0.0, 0.0, signal=[0])
    world.addNode("dest", 1.0, 0.0, signal=[0])
    _add_link(
        world,
        "wait_link",
        "orig",
        "dest",
        200.0,
        10.0,
        capacity_in=0.0,
        user_function=_release_inflow_at_timestep_5,
    )
    _add_vehicle(world, "veh", "orig", "dest", 0, ["wait_link"])
    world.exec_simulation()

    result = _evaluate(world, ["veh"], vot=0.0)
    record = result.vehicle_records[0]
    assert record.cumulative_waiting_time_s > 0.0
    assert record.od_based_waiting_time_s > 0.0
    assert record.od_based_waiting_time_s == record.cumulative_waiting_time_s
    assert record.detour_time_timesteps == 0
    assert record.weighted_cumulative_waiting_time == 0.0
    assert record.weighted_od_based_waiting_time == 0.0
    assert result.summary.average_waiting_time_s == record.od_based_waiting_time_s
    assert result.summary.average_weighted_waiting_time == 0.0
    assert result.summary.average_waiting_time_s != 0.0
    _assert_vehicle_identity(record)
    _assert_summary_identity(result.summary)
