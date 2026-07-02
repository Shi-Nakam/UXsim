# Verify clearance-aware FCFS behavior with clearance_timesteps=1.
#
# Run from the repository root:
#   python tests_fcfs_order_control_clearance_1.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

TOLERANCE = 1e-9


def _passage_order_on_link(link, vehicle_names=None):
    names = [veh.name for _, veh in sorted(link.vehicles_enter_log.items())]
    if vehicle_names is not None:
        name_set = set(vehicle_names)
        names = [name for name in names if name in name_set]
    return names


def _passage_times_on_link(link, vehicle_names):
    name_set = set(vehicle_names)
    return {
        veh.name: enter_time
        for enter_time, veh in sorted(link.vehicles_enter_log.items())
        if veh.name in name_set
    }


def _expected_fcfs_order(vehicles, node_name):
    return [
        veh.name
        for veh in sorted(
            vehicles,
            key=lambda veh: (
                veh.order_control_node_arrival_times[node_name],
                veh.order_control_node_arrival_tiebreakers[node_name],
                veh.id,
            ),
        )
    ]


def _failure_message(
    *,
    expected_order,
    actual_order,
    actual_enter_times,
    first_enter_time,
    second_enter_time,
    time_gap,
    deltat,
    tolerance,
    veh_clr_1,
    veh_clr_2,
    merge,
):
    return (
        f"expected_order: {expected_order}\n"
        f"actual_order: {actual_order}\n"
        f"actual_enter_times: {actual_enter_times}\n"
        f"first_enter_time: {first_enter_time}\n"
        f"second_enter_time: {second_enter_time}\n"
        f"time_gap: {time_gap}\n"
        f"W.DELTAT: {deltat}\n"
        f"time_gap / W.DELTAT: {time_gap / deltat}\n"
        f"tolerance: {tolerance}\n"
        f"veh_clr_1 arrival_time: {veh_clr_1.order_control_node_arrival_times['merge']}\n"
        f"veh_clr_2 arrival_time: {veh_clr_2.order_control_node_arrival_times['merge']}\n"
        f"veh_clr_1 tiebreaker: {veh_clr_1.order_control_node_arrival_tiebreakers['merge']}\n"
        f"veh_clr_2 tiebreaker: {veh_clr_2.order_control_node_arrival_tiebreakers['merge']}\n"
        f"veh_clr_1 id: {veh_clr_1.id}\n"
        f"veh_clr_2 id: {veh_clr_2.id}\n"
        f"clearance_timesteps: {merge.order_control_clearance_timesteps}\n"
        f"veh_clr_1 state: {veh_clr_1.state}\n"
        f"veh_clr_2 state: {veh_clr_2.state}"
    )


def test_clearance_one_requires_extra_timestep_for_direction_change():
    W = World(
        name="fcfs_clearance_one_basic",
        deltan=1,
        tmax=400,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )

    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("merge", 1, 1)
    W.addNode("dest", 2, 1)

    link_length = 400
    link_speed = 20
    W.addLink(
        "link1", "orig1", "merge", length=link_length, free_flow_speed=link_speed, number_of_lanes=1
    )
    W.addLink(
        "link2", "orig2", "merge", length=link_length, free_flow_speed=link_speed, number_of_lanes=1
    )
    W.addLink(
        "out", "merge", "dest", length=500, free_flow_speed=link_speed, number_of_lanes=1
    )

    W.infer_order_control_eligible_nodes()
    merge = W.get_node("merge")
    assert merge.order_control_eligible is True

    W.set_order_control_clearance_timesteps(1)
    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")

    assert merge.order_control_type == "fcfs"
    assert merge.order_control_clearance_timesteps == 1

    veh_clr_1 = W.addVehicle("orig1", "dest", 0, name="veh_clr_1")
    veh_clr_2 = W.addVehicle("orig2", "dest", 0, name="veh_clr_2")

    W.exec_simulation()

    assert "merge" in veh_clr_1.order_control_node_arrival_times
    assert "merge" in veh_clr_2.order_control_node_arrival_times
    assert "merge" in veh_clr_1.order_control_node_arrival_tiebreakers
    assert "merge" in veh_clr_2.order_control_node_arrival_tiebreakers

    arrival1 = veh_clr_1.order_control_node_arrival_times["merge"]
    arrival2 = veh_clr_2.order_control_node_arrival_times["merge"]
    assert arrival1 == arrival2, (
        "同時到着せず\n"
        f"veh_clr_1 arrival_time: {arrival1}\n"
        f"veh_clr_2 arrival_time: {arrival2}"
    )

    expected_order = _expected_fcfs_order([veh_clr_1, veh_clr_2], "merge")

    outlink = W.get_link("out")
    vehicle_names = ["veh_clr_1", "veh_clr_2"]
    actual_order = _passage_order_on_link(outlink, vehicle_names=vehicle_names)
    actual_enter_times = _passage_times_on_link(outlink, vehicle_names)

    basic_msg = (
        f"expected_order: {expected_order}\n"
        f"actual_order: {actual_order}\n"
        f"actual_enter_times: {actual_enter_times}\n"
        f"clearance_timesteps: {merge.order_control_clearance_timesteps}\n"
        f"veh_clr_1 state: {veh_clr_1.state}\n"
        f"veh_clr_2 state: {veh_clr_2.state}"
    )

    assert actual_order == expected_order, f"通過順が期待と一致しない\n{basic_msg}"
    assert len(actual_enter_times) == 2, f"out進入記録が2台分ない\n{basic_msg}"

    first_name = expected_order[0]
    second_name = expected_order[1]
    first_enter_time = actual_enter_times[first_name]
    second_enter_time = actual_enter_times[second_name]
    time_gap = second_enter_time - first_enter_time

    msg = _failure_message(
        expected_order=expected_order,
        actual_order=actual_order,
        actual_enter_times=actual_enter_times,
        first_enter_time=first_enter_time,
        second_enter_time=second_enter_time,
        time_gap=time_gap,
        deltat=W.DELTAT,
        tolerance=TOLERANCE,
        veh_clr_1=veh_clr_1,
        veh_clr_2=veh_clr_2,
        merge=merge,
    )

    assert first_enter_time != second_enter_time, (
        f"同一タイムステップ内に異方向Vehicleが連続してoutに入った可能性\n{msg}"
    )
    assert second_enter_time > first_enter_time, (
        f"2台目のout進入時刻が1台目より後でない\n{msg}"
    )
    assert time_gap >= 2 * W.DELTAT - TOLERANCE, (
        f"clearance_timesteps=1 で異方向通過までの間隔が不足\n{msg}"
    )

    assert veh_clr_1.state == "end", msg
    assert veh_clr_2.state == "end", msg

    print(f"first_enter_time: {first_enter_time}")
    print(f"second_enter_time: {second_enter_time}")
    print(f"time_gap: {time_gap}")
    print(f"W.DELTAT: {W.DELTAT}")
    print(f"time_gap / W.DELTAT: {time_gap / W.DELTAT}")
    print("FCFS clearance=1 test passed.")


if __name__ == "__main__":
    test_clearance_one_requires_extra_timestep_for_direction_change()
