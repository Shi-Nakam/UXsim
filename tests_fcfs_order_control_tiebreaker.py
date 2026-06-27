# Verify FCFS fixed tiebreaker for simultaneous arrivals at order-control nodes.
#
# Run from the repository root:
#   python tests_fcfs_order_control_tiebreaker.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim import World


def _passage_order_on_link(link, vehicle_names=None):
    names = [veh.name for _, veh in sorted(link.vehicles_enter_log.items())]
    if vehicle_names is not None:
        name_set = set(vehicle_names)
        names = [name for name in names if name in name_set]
    return names


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


def test_fcfs_tiebreaker_orders_simultaneous_arrivals():
    W = World(
        name="fcfs_simultaneous_arrival_tiebreaker",
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

    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")
    assert merge.order_control_type == "fcfs"

    veh_tie_1 = W.addVehicle("orig1", "dest", 0, name="veh_tie_1")
    veh_tie_2 = W.addVehicle("orig2", "dest", 0, name="veh_tie_2")

    W.exec_simulation()

    assert "merge" in veh_tie_1.order_control_node_arrival_times
    assert "merge" in veh_tie_2.order_control_node_arrival_times
    assert "merge" in veh_tie_1.order_control_node_arrival_tiebreakers
    assert "merge" in veh_tie_2.order_control_node_arrival_tiebreakers

    arrival1 = veh_tie_1.order_control_node_arrival_times["merge"]
    arrival2 = veh_tie_2.order_control_node_arrival_times["merge"]
    assert arrival1 == arrival2, (
        "同時到着せず\n"
        f"veh_tie_1 arrival_time: {arrival1}\n"
        f"veh_tie_2 arrival_time: {arrival2}"
    )

    tb1 = veh_tie_1.order_control_node_arrival_tiebreakers["merge"]
    tb2 = veh_tie_2.order_control_node_arrival_tiebreakers["merge"]
    id1 = veh_tie_1.id
    id2 = veh_tie_2.id

    assert isinstance(tb1, (int, float))
    assert isinstance(tb2, (int, float))
    assert id1 != id2

    expected_order = _expected_fcfs_order([veh_tie_1, veh_tie_2], "merge")

    outlink = W.get_link("out")
    actual_order = _passage_order_on_link(
        outlink, vehicle_names=["veh_tie_1", "veh_tie_2"]
    )

    assert actual_order == expected_order, (
        "tiebreaker順に通過せず\n"
        f"expected_order: {expected_order}\n"
        f"actual_order: {actual_order}\n"
        f"veh_tie_1 arrival_time: {arrival1}\n"
        f"veh_tie_2 arrival_time: {arrival2}\n"
        f"veh_tie_1 tiebreaker: {tb1}\n"
        f"veh_tie_2 tiebreaker: {tb2}\n"
        f"veh_tie_1 id: {id1}\n"
        f"veh_tie_2 id: {id2}"
    )

    assert veh_tie_1.state == "end"
    assert veh_tie_2.state == "end"

    print("FCFS simultaneous-arrival tiebreaker test passed.")


if __name__ == "__main__":
    test_fcfs_tiebreaker_orders_simultaneous_arrivals()
