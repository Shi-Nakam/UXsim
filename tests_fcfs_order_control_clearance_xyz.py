# Verify clearance-aware FCFS behavior for the X/Y/Z problem.
#
# X and Z enter merge from the same inlink (direction A via linkA).
# Y enters merge from a different inlink (direction B via linkB).
# Candidate order at merge is X -> Y -> Z by (arrival_time, tiebreaker, veh.id).
#
# Network A (Tests 1A/1B/2A/2B): shared out -> dest; all three vehicles can pass.
# Network B (Tests 3A/3B): outA for X/Z, blocked outB for Y; simplified inference
# from passage times only (Y may continue after clearance when outB is infeasible).
#
# Run from the repository root:
#   python tests_fcfs_order_control_clearance_xyz.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World

TOLERANCE = 1e-9
EXPECTED_ORDER = ["veh_x", "veh_y", "veh_z"]
LINK_LENGTH = 400
LINK_SPEED = 20
OUT_LENGTH = 500
STAGGERED_SEED = 0
OUTB_BLOCK_SETTING = "outB capacity_in=0"


def _enter_times_on_link(link, vehicle_names):
    name_set = set(vehicle_names)
    return {
        veh.name: enter_time
        for enter_time, veh in sorted(link.vehicles_enter_log.items())
        if veh.name in name_set
    }


def _passage_order_on_link(link, vehicle_names):
    name_set = set(vehicle_names)
    return [
        veh.name
        for _, veh in sorted(link.vehicles_enter_log.items())
        if veh.name in name_set
    ]


def _expected_fcfs_order(vehicles, node_name="merge"):
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


def _vehicle_diag(veh, node_name="merge"):
    return {
        "arrival_time": veh.order_control_node_arrival_times[node_name],
        "tiebreaker": veh.order_control_node_arrival_tiebreakers[node_name],
        "id": veh.id,
        "state": veh.state,
    }


def _assert_gap_in_range(gap, low_steps, high_steps, deltat, msg):
    lower = low_steps * deltat - TOLERANCE
    upper = high_steps * deltat - TOLERANCE
    assert lower <= gap < upper, msg


def _failure_message(
    *,
    test_name,
    seed,
    expected_order,
    actual_order,
    actual_enter_times,
    clearance_timesteps,
    veh_x,
    veh_y,
    veh_z,
    merge,
    deltat,
    x_enter_time=None,
    y_enter_time=None,
    z_enter_time=None,
    y_gap=None,
    z_gap_after_y=None,
    outA_enter_times=None,
    outB_enter_times=None,
    z_gap_after_x=None,
    outB_block_setting=None,
):
    lines = [
        f"test_name: {test_name}",
        f"seed: {seed}",
        f"expected_order: {expected_order}",
        f"actual_order: {actual_order}",
        f"actual_enter_times: {actual_enter_times}",
        f"clearance_timesteps: {clearance_timesteps}",
        f"veh_x: {_vehicle_diag(veh_x)}",
        f"veh_y: {_vehicle_diag(veh_y)}",
        f"veh_z: {_vehicle_diag(veh_z)}",
        f"W.DELTAT: {deltat}",
        f"tolerance: {TOLERANCE}",
    ]
    if x_enter_time is not None:
        lines.append(f"x_enter_time: {x_enter_time}")
    if y_enter_time is not None:
        lines.append(f"y_enter_time: {y_enter_time}")
    if z_enter_time is not None:
        lines.append(f"z_enter_time: {z_enter_time}")
    if y_gap is not None:
        lines.append(f"y_gap: {y_gap}")
    if z_gap_after_y is not None:
        lines.append(f"z_gap_after_y: {z_gap_after_y}")
    if outA_enter_times is not None:
        lines.append(f"outA_enter_times: {outA_enter_times}")
    if outB_enter_times is not None:
        lines.append(f"outB_enter_times: {outB_enter_times}")
    if z_gap_after_x is not None:
        lines.append(f"z_gap_after_x: {z_gap_after_x}")
    if outB_block_setting is not None:
        lines.append(f"outB block setting: {outB_block_setting}")
    return "\n".join(lines)


def _build_and_run_network_a(seed, clearance_timesteps, departure_times):
    W = World(
        name=f"fcfs_clearance_xyz_a_{seed}_{clearance_timesteps}",
        deltan=1,
        tmax=600,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=seed,
    )

    W.addNode("origA", 0, 0)
    W.addNode("origB", 0, 2)
    W.addNode("merge", 1, 1)
    W.addNode("dest", 2, 1)

    W.addLink(
        "linkA", "origA", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED, number_of_lanes=1
    )
    W.addLink(
        "linkB", "origB", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED, number_of_lanes=1
    )
    W.addLink(
        "out", "merge", "dest", length=OUT_LENGTH, free_flow_speed=LINK_SPEED, number_of_lanes=1
    )

    W.infer_order_control_eligible_nodes()
    merge = W.get_node("merge")
    assert merge.order_control_eligible is True

    W.set_order_control_clearance_timesteps(clearance_timesteps)
    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")

    veh_x = W.addVehicle("origA", "dest", departure_times["veh_x"], name="veh_x")
    veh_y = W.addVehicle("origB", "dest", departure_times["veh_y"], name="veh_y")
    veh_z = W.addVehicle("origA", "dest", departure_times["veh_z"], name="veh_z")

    W.exec_simulation()

    return {
        "W": W,
        "merge": merge,
        "veh_x": veh_x,
        "veh_y": veh_y,
        "veh_z": veh_z,
        "out": W.get_link("out"),
    }


def _build_and_run_network_b(seed, clearance_timesteps, departure_times):
    W = World(
        name=f"fcfs_clearance_xyz_b_{seed}_{clearance_timesteps}",
        deltan=1,
        tmax=600,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=seed,
    )

    W.addNode("origA", 0, 0)
    W.addNode("origB", 0, 2)
    W.addNode("merge", 1, 1)
    W.addNode("destA", 2, 0)
    W.addNode("destB", 2, 2)

    W.addLink(
        "linkA", "origA", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED, number_of_lanes=1
    )
    W.addLink(
        "linkB", "origB", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED, number_of_lanes=1
    )
    W.addLink(
        "outA", "merge", "destA", length=OUT_LENGTH, free_flow_speed=LINK_SPEED, number_of_lanes=1
    )
    W.addLink(
        "outB",
        "merge",
        "destB",
        length=OUT_LENGTH,
        free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
        capacity_in=0,
    )

    W.infer_order_control_eligible_nodes()
    merge = W.get_node("merge")
    assert merge.order_control_eligible is True

    W.set_order_control_clearance_timesteps(clearance_timesteps)
    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")

    veh_x = W.addVehicle("origA", "destA", departure_times["veh_x"], name="veh_x")
    veh_y = W.addVehicle("origB", "destB", departure_times["veh_y"], name="veh_y")
    veh_z = W.addVehicle("origA", "destA", departure_times["veh_z"], name="veh_z")

    W.exec_simulation()

    return {
        "W": W,
        "merge": merge,
        "veh_x": veh_x,
        "veh_y": veh_y,
        "veh_z": veh_z,
        "outA": W.get_link("outA"),
        "outB": W.get_link("outB"),
    }


def _find_seed_by_expected_order(build_fn, clearance_timesteps, departure_times):
    for seed in range(100):
        result = build_fn(seed, clearance_timesteps, departure_times)
        expected_order = _expected_fcfs_order(
            [result["veh_x"], result["veh_y"], result["veh_z"]]
        )
        if expected_order == EXPECTED_ORDER:
            result["seed"] = seed
            result["expected_order"] = expected_order
            return result
    return None


def _assert_candidate_order_recorded(veh_x, veh_y, veh_z, merge):
    assert merge.order_control_type == "fcfs"
    for veh in (veh_x, veh_y, veh_z):
        assert "merge" in veh.order_control_node_arrival_times
        assert "merge" in veh.order_control_node_arrival_tiebreakers

    expected_order = _expected_fcfs_order([veh_x, veh_y, veh_z])
    assert expected_order == EXPECTED_ORDER, (
        "候補順序が X -> Y -> Z になっていない\n"
        f"expected_order: {expected_order}\n"
        f"required: {EXPECTED_ORDER}"
    )
    return expected_order


def _assert_network_a_result(result, test_name, gap_low_steps, gap_high_steps):
    W = result["W"]
    merge = result["merge"]
    veh_x = result["veh_x"]
    veh_y = result["veh_y"]
    veh_z = result["veh_z"]
    out = result["out"]
    seed = result["seed"]

    expected_order = _assert_candidate_order_recorded(veh_x, veh_y, veh_z, merge)
    assert merge.order_control_clearance_timesteps == result["clearance_timesteps"]

    actual_order = _passage_order_on_link(out, EXPECTED_ORDER)
    enter_times = _enter_times_on_link(out, EXPECTED_ORDER)

    basic_msg = _failure_message(
        test_name=test_name,
        seed=seed,
        expected_order=expected_order,
        actual_order=actual_order,
        actual_enter_times=enter_times,
        clearance_timesteps=merge.order_control_clearance_timesteps,
        veh_x=veh_x,
        veh_y=veh_y,
        veh_z=veh_z,
        merge=merge,
        deltat=W.DELTAT,
    )

    assert actual_order == expected_order, f"通過順が期待と一致しない\n{basic_msg}"
    assert len(enter_times) == 3, f"out進入記録が3台分ない\n{basic_msg}"

    x_enter_time = enter_times["veh_x"]
    y_enter_time = enter_times["veh_y"]
    z_enter_time = enter_times["veh_z"]
    y_gap = y_enter_time - x_enter_time
    z_gap_after_y = z_enter_time - y_enter_time

    msg = _failure_message(
        test_name=test_name,
        seed=seed,
        expected_order=expected_order,
        actual_order=actual_order,
        actual_enter_times=enter_times,
        clearance_timesteps=merge.order_control_clearance_timesteps,
        veh_x=veh_x,
        veh_y=veh_y,
        veh_z=veh_z,
        merge=merge,
        deltat=W.DELTAT,
        x_enter_time=x_enter_time,
        y_enter_time=y_enter_time,
        z_enter_time=z_enter_time,
        y_gap=y_gap,
        z_gap_after_y=z_gap_after_y,
    )

    assert actual_order.index("veh_z") > actual_order.index("veh_y"), (
        f"ZがYを追い越した\n{msg}"
    )
    _assert_gap_in_range(y_gap, gap_low_steps, gap_high_steps, W.DELTAT, msg)
    _assert_gap_in_range(z_gap_after_y, gap_low_steps, gap_high_steps, W.DELTAT, msg)

    assert veh_x.state == "end", msg
    assert veh_y.state == "end", msg
    assert veh_z.state == "end", msg

    print(f"test_name: {test_name}")
    print(f"seed: {seed}")
    print(f"expected_order: {expected_order}")
    print(f"actual_order: {actual_order}")
    print(f"actual_enter_times: {enter_times}")
    print(f"x_enter_time: {x_enter_time}")
    print(f"y_enter_time: {y_enter_time}")
    print(f"z_enter_time: {z_enter_time}")
    print(f"y_gap: {y_gap}")
    print(f"z_gap_after_y: {z_gap_after_y}")
    print(f"clearance_timesteps: {merge.order_control_clearance_timesteps}")
    print(
        f"x_arrival_time: {veh_x.order_control_node_arrival_times['merge']}, "
        f"y_arrival_time: {veh_y.order_control_node_arrival_times['merge']}, "
        f"z_arrival_time: {veh_z.order_control_node_arrival_times['merge']}"
    )


def _assert_network_b_result(result, test_name):
    W = result["W"]
    merge = result["merge"]
    veh_x = result["veh_x"]
    veh_y = result["veh_y"]
    veh_z = result["veh_z"]
    outA = result["outA"]
    outB = result["outB"]
    seed = result["seed"]

    expected_order = _assert_candidate_order_recorded(veh_x, veh_y, veh_z, merge)
    assert merge.order_control_clearance_timesteps == 1

    outA_enter_times = _enter_times_on_link(outA, ["veh_x", "veh_z"])
    outB_enter_times = _enter_times_on_link(outB, ["veh_y"])

    basic_msg = _failure_message(
        test_name=test_name,
        seed=seed,
        expected_order=expected_order,
        actual_order=_passage_order_on_link(outA, ["veh_x", "veh_z"]),
        actual_enter_times=outA_enter_times,
        clearance_timesteps=merge.order_control_clearance_timesteps,
        veh_x=veh_x,
        veh_y=veh_y,
        veh_z=veh_z,
        merge=merge,
        deltat=W.DELTAT,
        outA_enter_times=outA_enter_times,
        outB_enter_times=outB_enter_times,
        outB_block_setting=OUTB_BLOCK_SETTING,
    )

    assert len(outA_enter_times) == 2, f"outA進入記録が2台分ない\n{basic_msg}"
    assert "veh_y" not in outB_enter_times, f"veh_y が blocked outB に進入した\n{basic_msg}"

    x_enter_time = outA_enter_times["veh_x"]
    z_enter_time = outA_enter_times["veh_z"]
    z_gap_after_x = z_enter_time - x_enter_time

    msg = _failure_message(
        test_name=test_name,
        seed=seed,
        expected_order=expected_order,
        actual_order=_passage_order_on_link(outA, ["veh_x", "veh_z"]),
        actual_enter_times=outA_enter_times,
        clearance_timesteps=merge.order_control_clearance_timesteps,
        veh_x=veh_x,
        veh_y=veh_y,
        veh_z=veh_z,
        merge=merge,
        deltat=W.DELTAT,
        x_enter_time=x_enter_time,
        z_enter_time=z_enter_time,
        outA_enter_times=outA_enter_times,
        outB_enter_times=outB_enter_times,
        z_gap_after_x=z_gap_after_x,
        outB_block_setting=OUTB_BLOCK_SETTING,
    )

    assert x_enter_time < z_enter_time, f"ZがXより前にoutAへ進入した\n{msg}"
    _assert_gap_in_range(z_gap_after_x, 2, 3, W.DELTAT, msg)

    assert veh_x.state == "end", msg
    assert veh_z.state == "end", msg

    print(f"test_name: {test_name}")
    print(f"seed: {seed}")
    print(f"expected_order: {expected_order}")
    print(f"outA_enter_times: {outA_enter_times}")
    print(f"outB_enter_times: {outB_enter_times}")
    print(f"x_enter_time: {x_enter_time}")
    print(f"z_enter_time: {z_enter_time}")
    print(f"z_gap_after_x: {z_gap_after_x}")
    print(f"clearance_timesteps: {merge.order_control_clearance_timesteps}")


def test_xyz_simultaneous_clearance_zero_blocks_z():
    test_name = "test_xyz_simultaneous_clearance_zero_blocks_z"
    departure_times = {"veh_x": 0, "veh_y": 0, "veh_z": 1}
    clearance_timesteps = 0

    result = _find_seed_by_expected_order(
        _build_and_run_network_a, clearance_timesteps, departure_times
    )
    assert result is not None, (
        "Could not find a seed producing expected_order == ['veh_x', 'veh_y', 'veh_z']"
    )
    result["clearance_timesteps"] = clearance_timesteps
    _assert_network_a_result(result, test_name, gap_low_steps=1, gap_high_steps=2)


def test_xyz_staggered_clearance_zero_blocks_z():
    test_name = "test_xyz_staggered_clearance_zero_blocks_z"
    departure_times = {"veh_x": 0, "veh_y": 1, "veh_z": 2}
    clearance_timesteps = 0

    result = _build_and_run_network_a(STAGGERED_SEED, clearance_timesteps, departure_times)
    result["seed"] = STAGGERED_SEED
    result["clearance_timesteps"] = clearance_timesteps
    _assert_network_a_result(result, test_name, gap_low_steps=1, gap_high_steps=2)


def test_xyz_simultaneous_clearance_one_blocks_z():
    test_name = "test_xyz_simultaneous_clearance_one_blocks_z"
    departure_times = {"veh_x": 0, "veh_y": 0, "veh_z": 1}
    clearance_timesteps = 1

    result = _find_seed_by_expected_order(
        _build_and_run_network_a, clearance_timesteps, departure_times
    )
    assert result is not None, (
        "Could not find a seed producing expected_order == ['veh_x', 'veh_y', 'veh_z']"
    )
    result["clearance_timesteps"] = clearance_timesteps
    _assert_network_a_result(result, test_name, gap_low_steps=2, gap_high_steps=3)


def test_xyz_staggered_clearance_one_blocks_z():
    test_name = "test_xyz_staggered_clearance_one_blocks_z"
    departure_times = {"veh_x": 0, "veh_y": 1, "veh_z": 2}
    clearance_timesteps = 1

    result = _build_and_run_network_a(STAGGERED_SEED, clearance_timesteps, departure_times)
    result["seed"] = STAGGERED_SEED
    result["clearance_timesteps"] = clearance_timesteps
    _assert_network_a_result(result, test_name, gap_low_steps=2, gap_high_steps=3)


def test_xyz_simultaneous_y_blocked_z_passes_after_clearance():
    # Simplified inference: Y cannot enter blocked outB; Z passes outA after clearance.
    test_name = "test_xyz_simultaneous_y_blocked_z_passes_after_clearance"
    departure_times = {"veh_x": 0, "veh_y": 0, "veh_z": 1}
    clearance_timesteps = 1

    result = _find_seed_by_expected_order(
        _build_and_run_network_b, clearance_timesteps, departure_times
    )
    assert result is not None, (
        "Could not find a seed producing expected_order == ['veh_x', 'veh_y', 'veh_z']"
    )
    _assert_network_b_result(result, test_name)


def test_xyz_staggered_y_blocked_z_passes_after_clearance():
    # Simplified inference: staggered arrivals; Y blocked on outB; Z passes outA after clearance.
    test_name = "test_xyz_staggered_y_blocked_z_passes_after_clearance"
    departure_times = {"veh_x": 0, "veh_y": 1, "veh_z": 2}
    clearance_timesteps = 1

    result = _build_and_run_network_b(STAGGERED_SEED, clearance_timesteps, departure_times)
    result["seed"] = STAGGERED_SEED
    _assert_network_b_result(result, test_name)


if __name__ == "__main__":
    test_xyz_simultaneous_clearance_zero_blocks_z()
    test_xyz_staggered_clearance_zero_blocks_z()
    test_xyz_simultaneous_clearance_one_blocks_z()
    test_xyz_staggered_clearance_one_blocks_z()
    test_xyz_simultaneous_y_blocked_z_passes_after_clearance()
    test_xyz_staggered_y_blocked_z_passes_after_clearance()
    print("FCFS clearance X/Y/Z tests passed.")
