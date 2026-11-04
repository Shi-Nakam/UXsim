"""Contracts for the common network-wide ACWT and ACWWT evaluation.

The tests build small UXsim worlds and call the public entry point.
They do not run the CASE 8 research script.
"""

import math
from collections.abc import Mapping
from dataclasses import replace

import pytest

from uxsim import World
from uxsim.analyzer import Analyzer
from uxsim.uxsim import Link, Node, Vehicle
import uxsim.network_wide_waiting_time_evaluation as evaluation

SPEED_60KPH_M_PER_S = 60.0 / 3.6
FREE_FLOW_LENGTH_M = 200.0
FREE_FLOW_TRIP_S = 13.0
ANALYTICAL_FREE_FLOW_S = 12.0
ORIGIN_WAIT_S = 4.0
ORIGIN_RELEASE_TIMESTEP = 5

PARTICIPATING = "tvt_participating_cohort"
NONPARTICIPATING = "tvt_nonparticipating_cohort"


@pytest.fixture(autouse=True)
def evaluation_workdir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _world(name, reaction_time=1.0, deltan=1, tmax=400.0):
    return World(
        name=name,
        deltan=deltan,
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


def _add_chain(
    world,
    prefix,
    lengths,
    speed,
    capacity_in=None,
    user_function=None,
):
    node_names = []
    node_count = len(lengths) + 1
    for index in range(node_count):
        node_name = f"{prefix}_n{index}"
        world.addNode(node_name, float(index), 0.0, signal=[0])
        node_names.append(node_name)
    link_names = []
    for index, length in enumerate(lengths):
        link_name = f"{prefix}_l{index}"
        world.addLink(
            link_name,
            node_names[index],
            node_names[index + 1],
            length=length,
            free_flow_speed=speed,
            number_of_lanes=1,
            capacity_in=capacity_in,
            user_function=user_function,
        )
        link_names.append(link_name)
    return node_names[0], node_names[-1], tuple(link_names)


def _add_vehicle(world, name, orig, dest, departure_timestep, route_names):
    vehicle = world.addVehicle(
        orig,
        dest,
        departure_timestep,
        name=name,
        departure_time_is_time_step=1,
    )
    vehicle.enforce_route(list(route_names))
    return vehicle


def _release_inflow_at_timestep_5(link):
    if link.W.T == ORIGIN_RELEASE_TIMESTEP:
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


def _evaluate(world, names, method_name="signalized_uxsim", vot=1.0, cohort=PARTICIPATING, **kwargs):
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


def _finished_free_flow_world(name="free"):
    world = _world(name)
    orig, dest, links = _add_chain(
        world,
        "free",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "veh", orig, dest, 0, links)
    world.exec_simulation()
    return world


def _assert_no_simulation_object(value, seen=None):
    if seen is None:
        seen = []
    if id(value) in seen:
        return
    seen.append(id(value))
    assert not isinstance(value, (World, Vehicle, Node, Link, Analyzer))
    if isinstance(value, (str, bytes)):
        return
    if isinstance(value, Mapping):
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


def test_same_physical_route_reuses_one_reference_replay():
    world = _world("same_route")
    orig, dest, links = _add_chain(
        world,
        "same",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "veh_a", orig, dest, 0, links)
    _add_vehicle(world, "veh_b", orig, dest, 100, links)
    world.exec_simulation()

    result = _evaluate(world, ["veh_a", "veh_b"], vot=2.0)
    counters = result.counters

    assert [record.vehicle_name for record in result.vehicle_records] == [
        "veh_a",
        "veh_b",
    ]
    assert counters.evaluated_vehicle_count == 2
    assert counters.unique_physical_route_count == 1
    assert counters.reference_replay_run_count == 1
    assert counters.reference_reuse_count == 1
    assert counters.unique_audit_identity_count == 1
    assert counters.duplicate_audit_identity_observation_count == 1
    assert counters.negative_cumulative_waiting_time_count == 0
    assert len(result.reference_results_by_physical_key) == 1
    assert result.summary.vehicle_count == 2
    assert result.summary.counters is counters

    stored = next(iter(result.reference_results_by_physical_key.values()))
    assert stored.validation_passed is True
    assert stored.minimum_trip_time_s == FREE_FLOW_TRIP_S
    assert stored.analytical_free_flow_time_s == ANALYTICAL_FREE_FLOW_S
    assert stored.minimum_trip_time_s != stored.analytical_free_flow_time_s
    for record in result.vehicle_records:
        assert record.cumulative_waiting_time_timesteps == 0
        assert record.cumulative_waiting_time_s == 0.0
        assert record.actual_trip_timesteps == FREE_FLOW_TRIP_S
        assert record.reference_minimum_trip_timesteps == FREE_FLOW_TRIP_S
        assert record.minimum_trip_time_s == FREE_FLOW_TRIP_S
        assert record.actual_travel_time_s == world.VEHICLES[record.vehicle_name].travel_time
        assert record.weighted_cumulative_waiting_time == 0.0
        assert record.reference_departure_timestep == stored.reference_departure_timestep
        assert record.reference_arrival_timestep == stored.reference_arrival_timestep


def test_link_names_do_not_cause_another_reference_replay():
    world = _world("names")
    orig_a, dest_a, links_a = _add_chain(
        world,
        "alpha",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    orig_b, dest_b, links_b = _add_chain(
        world,
        "beta",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "veh_alpha", orig_a, dest_a, 0, links_a)
    _add_vehicle(world, "veh_beta", orig_b, dest_b, 0, links_b)
    world.exec_simulation()

    result = _evaluate(world, ["veh_alpha", "veh_beta"])
    identities = next(iter(result.audit_identities_by_physical_key.values()))

    assert result.counters.unique_physical_route_count == 1
    assert result.counters.reference_replay_run_count == 1
    assert result.counters.reference_reuse_count == 1
    assert result.counters.unique_audit_identity_count == 2
    assert result.counters.duplicate_audit_identity_observation_count == 0
    assert identities == (links_a, links_b)
    assert result.vehicle_records[0].route_audit_identity == links_a
    assert result.vehicle_records[1].route_audit_identity == links_b
    physical_key = result.vehicle_records[0].physical_route_key
    assert type(physical_key[0]) is float
    assert physical_key[0] == float(world.DELTAT)
    for length, speed_u in physical_key[1]:
        assert type(length) is float
        assert type(speed_u) is float


def test_repeated_audit_identity_counts_one_duplicate():
    world = _world("repeat_name")
    orig_a, dest_a, links_a = _add_chain(
        world,
        "alpha",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    orig_b, dest_b, links_b = _add_chain(
        world,
        "beta",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "veh_a1", orig_a, dest_a, 0, links_a)
    _add_vehicle(world, "veh_b", orig_b, dest_b, 0, links_b)
    _add_vehicle(world, "veh_a2", orig_a, dest_a, 100, links_a)
    world.exec_simulation()

    result = _evaluate(world, ["veh_a1", "veh_b", "veh_a2"])
    counters = result.counters

    assert counters.evaluated_vehicle_count == 3
    assert counters.unique_physical_route_count == 1
    assert counters.reference_replay_run_count == 1
    assert counters.reference_reuse_count == 2
    assert counters.unique_audit_identity_count == 2
    assert counters.duplicate_audit_identity_observation_count == 1
    identities = result.audit_identities_by_physical_key[
        result.vehicle_records[0].physical_route_key
    ]
    assert identities == (links_a, links_b)


def _two_route_result(name, lengths_a, lengths_b, speed_a, speed_b):
    world = _world(name)
    orig_a, dest_a, links_a = _add_chain(world, "alpha", lengths_a, speed_a)
    orig_b, dest_b, links_b = _add_chain(world, "beta", lengths_b, speed_b)
    _add_vehicle(world, "veh_a", orig_a, dest_a, 0, links_a)
    _add_vehicle(world, "veh_b", orig_b, dest_b, 0, links_b)
    world.exec_simulation()
    result = _evaluate(world, ["veh_a", "veh_b"])
    return result


def test_link_order_uses_separate_physical_keys():
    result = _two_route_result(
        "order",
        (200.0, 100.0),
        (100.0, 200.0),
        SPEED_60KPH_M_PER_S,
        SPEED_60KPH_M_PER_S,
    )
    keys = [record.physical_route_key for record in result.vehicle_records]
    assert keys[0] != keys[1]
    assert result.counters.unique_physical_route_count == 2
    assert result.counters.reference_replay_run_count == 2
    assert result.counters.reference_reuse_count == 0


def test_link_length_uses_separate_physical_keys():
    result = _two_route_result(
        "length",
        (200.0,),
        (250.0,),
        SPEED_60KPH_M_PER_S,
        SPEED_60KPH_M_PER_S,
    )
    keys = [record.physical_route_key for record in result.vehicle_records]
    assert keys[0][1] != keys[1][1]
    assert result.counters.reference_replay_run_count == result.counters.unique_physical_route_count
    assert result.counters.reference_reuse_count == 0


def test_link_u_uses_separate_physical_keys():
    result = _two_route_result(
        "speed",
        (FREE_FLOW_LENGTH_M,),
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
        20.0,
    )
    keys = [record.physical_route_key for record in result.vehicle_records]
    assert keys[0][1][0][1] != keys[1][1][0][1]
    assert result.counters.reference_replay_run_count == 2
    assert result.counters.reference_reuse_count == (
        result.counters.evaluated_vehicle_count
        - result.counters.unique_physical_route_count
    )


def test_deltat_difference_is_not_shared_between_evaluations():
    world_fast = _world("deltat_1", reaction_time=1.0)
    orig, dest, links = _add_chain(
        world_fast,
        "fast",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world_fast, "veh", orig, dest, 0, links)
    world_fast.exec_simulation()

    world_slow = _world("deltat_half", reaction_time=0.5)
    orig, dest, links = _add_chain(
        world_slow,
        "slow",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world_slow, "veh", orig, dest, 0, links)
    world_slow.exec_simulation()

    first = _evaluate(world_fast, ["veh"])
    second = _evaluate(world_slow, ["veh"])
    again = _evaluate(world_fast, ["veh"])

    first_key = first.vehicle_records[0].physical_route_key
    second_key = second.vehicle_records[0].physical_route_key
    assert first_key[0] == float(world_fast.DELTAT)
    assert second_key[0] == float(world_slow.DELTAT)
    assert first_key != second_key
    assert first.reference_results_by_physical_key is not second.reference_results_by_physical_key
    assert first.counters is not again.counters
    assert again.counters.reference_replay_run_count == 1
    assert again.counters.reference_reuse_count == 0
    assert again.counters.duplicate_audit_identity_observation_count == 0


def test_origin_wait_is_four_seconds_and_minimum_trip_is_shared():
    world = _world("origin_wait")
    free_orig, free_dest, free_links = _add_chain(
        world,
        "free",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    wait_orig, wait_dest, wait_links = _add_chain(
        world,
        "wait",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
        capacity_in=0.0,
        user_function=_release_inflow_at_timestep_5,
    )
    _add_vehicle(world, "veh_free", free_orig, free_dest, 0, free_links)
    _add_vehicle(world, "veh_wait", wait_orig, wait_dest, 0, wait_links)
    world.exec_simulation()

    result = _evaluate(
        world,
        ["veh_free", "veh_wait"],
        vot=2.0,
        true_vot_per_second_by_vehicle_name={
            "veh_free": 2.0,
            "veh_wait": 2.0,
            "not_evaluated": 99.0,
        },
    )
    free_record, wait_record = result.vehicle_records
    assert result.counters.reference_replay_run_count == 1
    assert result.counters.reference_reuse_count == 1
    assert free_record.minimum_trip_time_s == FREE_FLOW_TRIP_S
    assert wait_record.minimum_trip_time_s == FREE_FLOW_TRIP_S
    assert free_record.reference_minimum_trip_timesteps == (
        wait_record.reference_minimum_trip_timesteps
    )
    assert free_record.cumulative_waiting_time_s == 0.0
    assert free_record.cumulative_waiting_time_timesteps == 0
    assert wait_record.actual_trip_timesteps == (
        wait_record.reference_minimum_trip_timesteps + 4
    )
    assert wait_record.cumulative_waiting_time_timesteps == 4
    assert wait_record.cumulative_waiting_time_s == ORIGIN_WAIT_S
    assert wait_record.cumulative_waiting_time_s == (
        wait_record.cumulative_waiting_time_timesteps * world.DELTAT
    )
    assert wait_record.actual_travel_time_s == world.VEHICLES["veh_wait"].travel_time
    assert wait_record.actual_travel_time_s == (
        wait_record.actual_trip_timesteps * world.DELTAT
    )
    assert wait_record.weighted_cumulative_waiting_time == 8.0
    assert wait_record.weighted_cumulative_waiting_time == (
        wait_record.cumulative_waiting_time_s * wait_record.true_vot_per_second
    )
    assert wait_record.weighted_cumulative_waiting_time != 8.0 / 3600.0
    assert result.summary.vehicle_count == 2
    assert result.summary.average_cumulative_waiting_time_s == (
        result.summary.total_cumulative_waiting_time_s / 2
    )
    assert result.summary.average_weighted_cumulative_waiting_time == (
        result.summary.total_weighted_cumulative_waiting_time / 2
    )


def test_negative_waiting_timesteps_are_not_rounded_to_zero(monkeypatch):
    world = _finished_free_flow_world("negative")
    real_run = evaluation._run_reference_replay

    def longer_reference(*args, **kwargs):
        result = real_run(*args, **kwargs)
        extra = 5
        return replace(
            result,
            reference_arrival_timestep=result.reference_arrival_timestep + extra,
            reference_minimum_trip_timesteps=(
                result.reference_minimum_trip_timesteps + extra
            ),
            minimum_trip_time_s=(
                result.minimum_trip_time_s + extra * result.reference_world_deltat
            ),
        )

    monkeypatch.setattr(evaluation, "_run_reference_replay", longer_reference)
    with pytest.raises(RuntimeError, match="timesteps=-5"):
        _evaluate(world, ["veh"])


def test_unvalidated_reference_result_is_not_returned(monkeypatch):
    world = _finished_free_flow_world("unvalidated")
    real_run = evaluation._run_reference_replay

    def unvalidated(*args, **kwargs):
        result = real_run(*args, **kwargs)
        return replace(result, validation_passed=False)

    monkeypatch.setattr(evaluation, "_run_reference_replay", unvalidated)
    with pytest.raises(RuntimeError, match="not stored"):
        _evaluate(world, ["veh"])


@pytest.mark.parametrize("method_name", evaluation.OFFICIAL_METHOD_NAMES)
def test_method_name_does_not_change_the_calculation(method_name):
    world = _world(f"method_{method_name}")
    free_orig, free_dest, free_links = _add_chain(
        world,
        "free",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    wait_orig, wait_dest, wait_links = _add_chain(
        world,
        "wait",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
        capacity_in=0.0,
        user_function=_release_inflow_at_timestep_5,
    )
    _add_vehicle(world, "veh_free", free_orig, free_dest, 0, free_links)
    _add_vehicle(world, "veh_wait", wait_orig, wait_dest, 0, wait_links)
    world.exec_simulation()

    result = _evaluate(world, ["veh_free", "veh_wait"], method_name=method_name)
    assert result.summary.method_name == method_name
    assert [record.method_name for record in result.vehicle_records] == [
        method_name,
        method_name,
    ]
    assert [record.cumulative_waiting_time_s for record in result.vehicle_records] == [
        0.0,
        ORIGIN_WAIT_S,
    ]
    assert result.summary.total_cumulative_waiting_time_s == ORIGIN_WAIT_S


def test_true_vot_zero_makes_weighted_waiting_zero():
    world = _world("vot_zero")
    orig, dest, links = _add_chain(
        world,
        "wait",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
        capacity_in=0.0,
        user_function=_release_inflow_at_timestep_5,
    )
    _add_vehicle(world, "veh_wait", orig, dest, 0, links)
    world.exec_simulation()

    result = _evaluate(world, ["veh_wait"], vot=0)
    record = result.vehicle_records[0]
    assert record.true_vot_per_second == 0.0
    assert record.cumulative_waiting_time_s == ORIGIN_WAIT_S
    assert record.weighted_cumulative_waiting_time == 0.0
    assert result.summary.average_weighted_cumulative_waiting_time == 0.0
    assert result.summary.vehicle_count == 1


@pytest.mark.parametrize(
    ("raw_vot", "match"),
    [
        (None, "None"),
        (True, "non-bool"),
        (False, "non-bool"),
        ("1", "non-bool"),
        (float("nan"), "finite"),
        (float("inf"), "finite"),
        (float("-inf"), "finite"),
        (-0.1, ">= 0"),
    ],
)
def test_invalid_true_vot_raises_value_error(raw_vot, match):
    world = _world("bad_vot")
    with pytest.raises(ValueError, match=match):
        evaluation.evaluate_network_wide_waiting_time(
            world,
            "fcfs",
            ["veh"],
            {"veh": raw_vot},
            {"veh": PARTICIPATING},
        )


def test_missing_true_vot_raises_value_error():
    world = _world("missing_vot")
    with pytest.raises(ValueError, match="missing"):
        evaluation.evaluate_network_wide_waiting_time(
            world,
            "batch",
            ["veh"],
            {},
            {"veh": PARTICIPATING},
        )


def test_cohort_summaries_add_up_and_do_not_change_waiting_time():
    world = _world("cohorts")
    free_orig, free_dest, free_links = _add_chain(
        world,
        "free",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    wait_orig, wait_dest, wait_links = _add_chain(
        world,
        "wait",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
        capacity_in=0.0,
        user_function=_release_inflow_at_timestep_5,
    )
    _add_vehicle(world, "veh_wait", wait_orig, wait_dest, 0, wait_links)
    _add_vehicle(world, "veh_free", free_orig, free_dest, 0, free_links)
    world.exec_simulation()
    names = ["veh_wait", "veh_free"]
    cohorts = {
        "veh_wait": PARTICIPATING,
        "veh_free": NONPARTICIPATING,
    }
    vots = {"veh_wait": 2.0, "veh_free": 4.0}
    with_status = _evaluate(
        world,
        names,
        method_name="tvt_mp",
        true_vot_per_second_by_vehicle_name=vots,
        evaluation_cohort_by_vehicle_name=cohorts,
        method_specific_participation_status_by_vehicle_name={
            "veh_wait": "participating",
            "veh_free": "nonparticipating",
        },
    )
    without_status = _evaluate(
        world,
        names,
        method_name="fcfs",
        true_vot_per_second_by_vehicle_name=vots,
        evaluation_cohort_by_vehicle_name={
            "veh_wait": NONPARTICIPATING,
            "veh_free": PARTICIPATING,
        },
    )

    assert [record.cumulative_waiting_time_s for record in with_status.vehicle_records] == [
        ORIGIN_WAIT_S,
        0.0,
    ]
    assert [record.cumulative_waiting_time_s for record in without_status.vehicle_records] == [
        ORIGIN_WAIT_S,
        0.0,
    ]
    assert with_status.vehicle_records[0].method_specific_participation_status == (
        "participating"
    )
    assert without_status.vehicle_records[0].method_specific_participation_status is None
    summaries = with_status.summary.cohort_summaries
    assert [item.evaluation_cohort for item in summaries] == [
        PARTICIPATING,
        NONPARTICIPATING,
    ]
    assert summaries[0].vehicle_count == 1
    assert summaries[0].total_cumulative_waiting_time_s == ORIGIN_WAIT_S
    assert summaries[0].average_cumulative_waiting_time_s == ORIGIN_WAIT_S
    assert summaries[0].total_weighted_cumulative_waiting_time == 8.0
    assert summaries[0].average_weighted_cumulative_waiting_time == 8.0
    assert summaries[1].vehicle_count == 1
    assert summaries[1].total_cumulative_waiting_time_s == 0.0
    assert summaries[1].total_weighted_cumulative_waiting_time == 0.0
    assert sum(item.vehicle_count for item in summaries) == with_status.summary.vehicle_count
    assert sum(item.total_cumulative_waiting_time_s for item in summaries) == (
        with_status.summary.total_cumulative_waiting_time_s
    )
    assert sum(item.total_weighted_cumulative_waiting_time for item in summaries) == (
        with_status.summary.total_weighted_cumulative_waiting_time
    )
    assert with_status.summary.average_weighted_cumulative_waiting_time == (
        with_status.summary.total_weighted_cumulative_waiting_time
        / with_status.summary.vehicle_count
    )


def test_missing_or_blank_cohort_raises_value_error():
    world = _world("bad_cohort")
    with pytest.raises(ValueError, match="missing"):
        evaluation.evaluate_network_wide_waiting_time(
            world,
            "batch",
            ["veh"],
            {"veh": 1.0},
            {},
        )
    with pytest.raises(ValueError, match="non-empty string"):
        evaluation.evaluate_network_wide_waiting_time(
            world,
            "batch",
            ["veh"],
            {"veh": 1.0},
            {"veh": ""},
        )


def test_missing_participation_status_raises_when_map_is_provided():
    world = _finished_free_flow_world("missing_status")
    with pytest.raises(ValueError, match="method_specific_participation_status"):
        _evaluate(
            world,
            ["veh"],
            method_specific_participation_status_by_vehicle_name={},
        )


@pytest.mark.parametrize("deltan", [2, True, 1.0])
def test_deltan_must_be_python_int_one(deltan):
    world = _world(f"deltan_{deltan}", deltan=deltan)
    with pytest.raises(ValueError, match="DELTAN"):
        _evaluate(world, ["veh"])


@pytest.mark.parametrize(
    ("names", "match"),
    [
        ([], "empty"),
        (["veh", "veh"], "duplicate"),
        (["missing"], "not in the real World"),
    ],
)
def test_vehicle_name_list_is_rejected_when_invalid(names, match):
    world = _finished_free_flow_world("names")
    with pytest.raises(ValueError, match=match):
        _evaluate(world, names)


def test_unfinished_vehicle_is_rejected():
    world = _world("unfinished")
    orig, dest, links = _add_chain(
        world,
        "free",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "veh", orig, dest, 0, links)
    with pytest.raises(ValueError, match="not finished"):
        _evaluate(world, ["veh"])


def test_empty_route_is_rejected(monkeypatch):
    world = _finished_free_flow_world("empty_route")
    vehicle = world.VEHICLES["veh"]

    def empty_route(*args, **kwargs):
        class EmptyRoute:
            links = []

        return EmptyRoute(), []

    monkeypatch.setattr(vehicle, "traveled_route", empty_route)
    with pytest.raises(ValueError, match="empty"):
        _evaluate(world, ["veh"])


@pytest.mark.parametrize(
    ("field_name", "bad_value", "match"),
    [
        ("length", 0, "link length"),
        ("length", -1.0, "link length"),
        ("length", float("nan"), "link length"),
        ("length", True, "link length"),
        ("u", 0, "link u"),
        ("u", -5.0, "link u"),
        ("u", float("nan"), "link u"),
        ("u", True, "link u"),
    ],
)
def test_invalid_link_length_or_u_is_rejected(field_name, bad_value, match):
    world = _finished_free_flow_world(f"link_{field_name}")
    link = world.VEHICLES["veh"].traveled_route()[0].links[0]
    setattr(link, field_name, bad_value)
    with pytest.raises(ValueError, match=match):
        _evaluate(world, ["veh"])


@pytest.mark.parametrize("bad_value", [True, False, 1.0])
def test_non_python_int_timestep_is_rejected(bad_value):
    world = _finished_free_flow_world("timestep")
    world.VEHICLES["veh"].arrival_time = bad_value
    with pytest.raises(ValueError, match="arrival timestep"):
        _evaluate(world, ["veh"])


def test_reference_deltat_mismatch_stops_the_evaluation(monkeypatch):
    world = _finished_free_flow_world("deltat_mismatch")
    real_build = evaluation._build_reference_world

    def mismatched(route_links, real_deltat):
        reference_world = real_build(route_links, real_deltat)
        reference_world.DELTAT = real_deltat + 1.0
        return reference_world

    monkeypatch.setattr(evaluation, "_build_reference_world", mismatched)
    with pytest.raises(RuntimeError, match="DELTAT"):
        _evaluate(world, ["veh"])


def test_each_evaluation_has_its_own_state_and_no_module_cache():
    world = _finished_free_flow_world("isolated")
    dict_ids_before = {}
    for name, value in vars(evaluation).items():
        if isinstance(value, dict):
            dict_ids_before[name] = id(value)

    first = _evaluate(world, ["veh"], vehicle_plan_digest="plan-a")
    second = _evaluate(
        world,
        ["veh"],
        vehicle_plan_digest="plan-b",
        comparison_metadata={"replication": 1, "unused": "audit"},
    )
    dict_ids_after = {}
    for name, value in vars(evaluation).items():
        if isinstance(value, dict):
            dict_ids_after[name] = id(value)

    assert dict_ids_before == dict_ids_after
    assert first.reference_results_by_physical_key is not (
        second.reference_results_by_physical_key
    )
    assert first.audit_identities_by_physical_key is not (
        second.audit_identities_by_physical_key
    )
    assert first.counters is not second.counters
    assert second.counters.reference_replay_run_count == 1
    assert second.counters.duplicate_audit_identity_observation_count == 0
    assert second.vehicle_plan_digest == "plan-b"
    assert dict(second.comparison_metadata) == {
        "replication": 1,
        "unused": "audit",
    }
    assert first.vehicle_records[0].cumulative_waiting_time_s == (
        second.vehicle_records[0].cumulative_waiting_time_s
    )
    with pytest.raises(TypeError):
        second.reference_results_by_physical_key["extra"] = None
    _assert_no_simulation_object(first)
    _assert_no_simulation_object(second)


def test_result_rejects_a_simulation_object_in_metadata():
    world = _finished_free_flow_world("metadata_vehicle")
    with pytest.raises(RuntimeError, match="simulation"):
        _evaluate(
            world,
            ["veh"],
            comparison_metadata={"vehicle": world.VEHICLES["veh"]},
        )


def test_evaluation_does_not_change_the_real_world_or_create_files(
    monkeypatch,
    evaluation_workdir,
    capsys,
):
    world = _world("side_effect")
    orig, dest, links = _add_chain(
        world,
        "free",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "veh", orig, dest, 0, links)
    world.exec_simulation()
    before_files = set(evaluation_workdir.rglob("*"))
    before_attributes = set(vars(world))
    before_time = (world.T, world.TIME, world.DELTAT, world.DELTAN)
    vehicle = world.VEHICLES["veh"]
    before_vehicle = (
        vehicle.state,
        vehicle.departure_time,
        vehicle.arrival_time,
        vehicle.travel_time,
    )

    def reject_exec(*args, **kwargs):
        raise AssertionError("exec_simulation was called during evaluation")

    def reject_analyzer(*args, **kwargs):
        raise AssertionError("Analyzer was created during evaluation")

    monkeypatch.setattr(World, "exec_simulation", reject_exec)
    monkeypatch.setattr(Analyzer, "__init__", reject_analyzer)
    result = _evaluate(world, ["veh"], method_name="batch")
    captured = capsys.readouterr()
    after_files = set(evaluation_workdir.rglob("*"))

    assert result.vehicle_records[0].cumulative_waiting_time_s == 0.0
    assert set(vars(world)) == before_attributes
    assert (world.T, world.TIME, world.DELTAT, world.DELTAN) == before_time
    assert (
        vehicle.state,
        vehicle.departure_time,
        vehicle.arrival_time,
        vehicle.travel_time,
    ) == before_vehicle
    assert before_files == after_files
    assert captured.out == ""
    assert captured.err == ""
    assert not hasattr(result, "real_world")
    _assert_no_simulation_object(result)


def test_case8_equivalent_contracts_hold_for_one_small_world():
    """CASE 8A-8D and 8F without executing the research script."""

    world = _world("case8")
    shared_orig, shared_dest, shared_links = _add_chain(
        world,
        "shared",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    other_orig, other_dest, other_links = _add_chain(
        world,
        "other_name",
        (FREE_FLOW_LENGTH_M,),
        SPEED_60KPH_M_PER_S,
    )
    _add_vehicle(world, "same_a", shared_orig, shared_dest, 0, shared_links)
    _add_vehicle(world, "same_b", shared_orig, shared_dest, 120, shared_links)
    _add_vehicle(world, "other", other_orig, other_dest, 0, other_links)
    world.exec_simulation()

    shared = _evaluate(world, ["same_a", "same_b"])
    assert shared.counters.evaluated_vehicle_count == 2
    assert shared.counters.unique_physical_route_count == 1
    assert shared.counters.reference_replay_run_count == 1
    assert shared.counters.reference_reuse_count == 1
    assert shared.vehicle_records[0].cumulative_waiting_time_s == 0.0
    assert shared.vehicle_records[1].cumulative_waiting_time_s == 0.0

    named = _evaluate(world, ["same_a", "other", "same_b"])
    assert named.counters.unique_physical_route_count == 1
    assert named.counters.reference_replay_run_count == 1
    assert named.counters.unique_audit_identity_count == 2
    assert named.counters.duplicate_audit_identity_observation_count == 1

    repeated = _evaluate(world, ["same_a"])
    assert repeated.counters.reference_replay_run_count == 1
    assert repeated.counters.duplicate_audit_identity_observation_count == 0
    assert repeated.reference_results_by_physical_key is not (
        shared.reference_results_by_physical_key
    )
    _assert_no_simulation_object(named)
    assert all(
        item.validation_passed
        for item in named.reference_results_by_physical_key.values()
    )
    assert math.isfinite(named.summary.average_cumulative_waiting_time_s)
