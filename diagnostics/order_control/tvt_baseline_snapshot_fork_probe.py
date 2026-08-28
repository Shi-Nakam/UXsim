# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Integration probe for the all-World baseline snapshot-fixed visit path:
# - branch real_W into fork_W
# - attach OrderControlBaselineCollector on fork_W only
# - register snapshot-fixed visits via register_snapshot_fixed_visits()
# - advance fork_W only and record baseline arrival/passage facts for the
#   snapshot-fixed set (A/B)
# - confirm outside-fixed-set vehicles are ignored by collector arrival and
#   passage notifications after they reach the target node via normal UXsim paths
# - confirm real_W state and RNG are unchanged
# - does NOT implement or reproduce TVT institutional logic itself
#
# Scope: single time_value node, single-lane links, small demand. Does not
# verify multi-node networks, mixed control types, large demand, long-run
# performance, two-stage observation, T+6 windows, right_of_entry_vehicle
# selection, trade_rank, or payments/compensation.
#
# Run from repository root:
#   python diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py

from __future__ import annotations

import pickle
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from uxsim import World
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_snapshot import register_snapshot_fixed_visits

# Calibrated on the small junction world below via normal exec_simulation():
# - dep 0 with an outlink blocker reaches junction before snapshot W.T==20
# - dep 11 is not yet arrived at snapshot W.T==20 (timestep 20 not processed)
# - fork processes timestep 20 while B remains not-yet-arrived, then records
#   baseline arrival during processed timestep 21 (exec afterwards W.T==22)
# - B baseline passage during processed timestep 22
# - outside_fixed_vehicle added at snapshot W.T==20, enters in via normal paths,
#   reaches junction and passes through while collector ignores notifications
SNAPSHOT_T = 20
ARRIVED_DEPARTURE = 0
NOT_YET_ARRIVED_DEPARTURE = 11
MAX_FORK_STEPS = 30

ARRIVED_VEHICLE_NAME = "arrived_fixed_vehicle"
NOT_YET_ARRIVED_VEHICLE_NAME = "not_yet_arrived_fixed_vehicle"
OUTSIDE_VEHICLE_NAME = "outside_fixed_vehicle"
BLOCKER_VEHICLE_NAME = "outlink_blocker"

JUNCTION_NODE_NAME = "junction"
INLINK_NAME = "in"
OUTLINK_NAME = "out"
OUTLINK_FREE_FLOW_SPEED = 20.0


def _make_blocker_hold_at_entrance_user_function(outlink_name: str):
    """
    Pin the diagnostic blocker at the outlink entrance after each Vehicle.update().

    World.set_traveltime_instant() divides by outlink.u, so setting outlink.u to
    zero breaks link.update(). Holding the blocker via user_function keeps normal
    outlink speed while preserving run-vehicle management consistency.
    """

    def _hold_blocker_at_entrance(vehicle) -> None:
        if vehicle.link is not None and vehicle.link.name == outlink_name:
            vehicle.x = 0.0
            vehicle.x_old = 0.0
            vehicle.x_next = 0.0
            vehicle.v = 0.0
            vehicle.move_remain = 0.0

    return _hold_blocker_at_entrance


def _prepare_network(W: World) -> None:
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_small_time_value_world() -> World:
    W = World(
        name="tvt_baseline_snapshot_fork_probe",
        deltan=1,
        tmax=100,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=0,
    )
    W.addNode("orig", 0, 0)
    W.addNode(
        JUNCTION_NODE_NAME,
        1,
        0,
        order_control_eligible=True,
        order_control_type="none",
    )
    W.addNode("dest", 2, 0)
    W.addLink(
        INLINK_NAME,
        "orig",
        JUNCTION_NODE_NAME,
        length=200,
        free_flow_speed=OUTLINK_FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        OUTLINK_NAME,
        JUNCTION_NODE_NAME,
        "dest",
        length=200,
        free_flow_speed=OUTLINK_FREE_FLOW_SPEED,
        number_of_lanes=1,
    )
    _prepare_network(W)
    return W


def _place_outlink_blocker(W: World, blocker_name: str = BLOCKER_VEHICLE_NAME):
    """
    Place a diagnostic-only run Vehicle at the outlink entrance.

    The blocker is registered in VEHICLES_RUNNING so it receives the same
    carfollow()/update() sequence as other run vehicles. A diagnostic
    user_function pins x/x_old/x_next at the entrance after each update because
    setting outlink.u to zero breaks link.set_traveltime_instant().

    This is not a normal Node.generate() or Node.transfer() link entry. Vehicle
    management dicts and outlink.vehicles are kept consistent, but link
    cum_arrival, vehicles_enter_log, and capacity_in_remain are not updated as
    in standard entry. The blocker keeps A from passing before snapshot; it is
    not part of a production driver.
    """
    outlink = W.get_link(OUTLINK_NAME)
    normal_outlink_u = float(outlink.u)

    blocker = W.addVehicle("orig", "dest", 0, name=blocker_name)
    blocker.link = outlink
    blocker.state = "run"
    blocker.x = 0.0
    blocker.x_old = 0.0
    blocker.x_next = 0.0
    blocker.v = 0.0
    blocker.move_remain = 0.0
    blocker.link_arrival_time = 0.0
    blocker.user_function = _make_blocker_hold_at_entrance_user_function(OUTLINK_NAME)
    if blocker not in outlink.vehicles:
        outlink.vehicles.append(blocker)
    W.VEHICLES_RUNNING[blocker.name] = blocker
    return blocker, normal_outlink_u


def _release_fork_outlink_blocker(fork_blocker) -> None:
    """Allow the fork-side blocker to advance via normal carfollow()/update()."""
    fork_blocker.user_function = None


def _assert_blocker_placement_consistent(
    W: World, blocker, *, normal_outlink_u: float
) -> None:
    outlink = W.get_link(OUTLINK_NAME)
    if blocker.name not in W.VEHICLES:
        raise AssertionError("outlink_blocker must be in W.VEHICLES")
    if blocker.name not in W.VEHICLES_LIVING:
        raise AssertionError("outlink_blocker must be in W.VEHICLES_LIVING")
    if blocker.name not in W.VEHICLES_RUNNING:
        raise AssertionError("outlink_blocker must be in W.VEHICLES_RUNNING")
    if blocker not in outlink.vehicles:
        raise AssertionError("outlink_blocker must be in outlink.vehicles")
    if blocker.state != "run":
        raise AssertionError("outlink_blocker must have state 'run' at placement")
    if blocker.link is not outlink:
        raise AssertionError("outlink_blocker.link must be the out link")
    if blocker.x != 0.0:
        raise AssertionError(f"outlink_blocker.x must be 0, got {blocker.x}")
    if blocker.x_next != 0.0:
        raise AssertionError(
            f"outlink_blocker.x_next must be 0, got {blocker.x_next}"
        )
    if blocker.move_remain != 0.0:
        raise AssertionError(
            f"outlink_blocker.move_remain must be 0, got {blocker.move_remain}"
        )
    if outlink.u != normal_outlink_u:
        raise AssertionError(
            f"outlink.u must remain {normal_outlink_u} while blocked, got {outlink.u}"
        )
    if blocker.user_function is None:
        raise AssertionError("outlink_blocker must have a hold user_function")


def _assert_blocker_at_entrance_after_snapshot(W: World, blocker) -> None:
    outlink = W.get_link(OUTLINK_NAME)
    if blocker.name not in W.VEHICLES_RUNNING:
        raise AssertionError(
            "outlink_blocker must remain in W.VEHICLES_RUNNING at snapshot"
        )
    if blocker.link is not outlink:
        raise AssertionError("outlink_blocker must remain on outlink at snapshot")
    if blocker.x != 0.0:
        raise AssertionError(
            f"outlink_blocker must remain at outlink entrance, x={blocker.x}"
        )


def _assert_blocker_management_on_fork(fork_W: World, blocker) -> bool:
    if blocker.state == "run":
        if blocker.name not in fork_W.VEHICLES_RUNNING:
            raise AssertionError(
                "run outlink_blocker must remain in fork_W.VEHICLES_RUNNING"
            )
        if blocker.name not in fork_W.VEHICLES_LIVING:
            raise AssertionError(
                "run outlink_blocker must remain in fork_W.VEHICLES_LIVING"
            )
        if blocker.link is None:
            raise AssertionError("run outlink_blocker.link must not be None")
        if blocker.link.W is not fork_W:
            raise AssertionError("run outlink_blocker.link must belong to fork_W")
        return True

    if blocker.state == "end":
        if blocker.name in fork_W.VEHICLES_RUNNING:
            raise AssertionError(
                "ended outlink_blocker must not remain in fork_W.VEHICLES_RUNNING"
            )
        if blocker.name in fork_W.VEHICLES_LIVING:
            raise AssertionError(
                "ended outlink_blocker must not remain in fork_W.VEHICLES_LIVING"
            )
        if blocker.link is not None:
            raise AssertionError("ended outlink_blocker.link must be None")
        return True

    raise AssertionError(
        f"outlink_blocker has unexpected state {blocker.state!r} on fork_W"
    )


def _current_visit_summary(vehicle) -> dict | None:
    visit = vehicle.order_control_current_visit
    if visit is None:
        return None
    node = visit.get("node")
    inlink = visit.get("inlink")
    return {
        "visit_id": visit.get("visit_id"),
        "node_name": None if node is None else node.name,
        "inlink_name": None if inlink is None else inlink.name,
        "arrival_time": visit.get("arrival_time"),
        "arrival_tiebreaker": visit.get("arrival_tiebreaker"),
    }


def _vehicle_snapshot(W: World, vehicle_names: list[str]) -> dict:
    vehicles = {}
    for name in vehicle_names:
        vehicle = W.VEHICLES[name]
        entry = {
            "state": vehicle.state,
            "link_name": None if vehicle.link is None else vehicle.link.name,
            "x": float(vehicle.x),
            "link_arrival_time": float(vehicle.link_arrival_time),
            "order_control_visit_id": vehicle.order_control_visit_id,
            "current_visit": _current_visit_summary(vehicle),
            "has_user_function": vehicle.user_function is not None,
        }
        if name == BLOCKER_VEHICLE_NAME:
            entry["x_old"] = float(vehicle.x_old)
            entry["x_next"] = float(vehicle.x_next)
            entry["v"] = float(vehicle.v)
            entry["move_remain"] = float(vehicle.move_remain)
        vehicles[name] = entry
    return vehicles


def _rng_state_bytes(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


def _real_world_comparison_snapshot(W: World, vehicle_names: list[str]) -> dict:
    junction = W.get_node(JUNCTION_NODE_NAME)
    inlink = W.get_link(INLINK_NAME)
    outlink = W.get_link(OUTLINK_NAME)
    return {
        "world": {
            "T": W.T,
            "TIME": W.TIME,
            "rng_state": _rng_state_bytes(W.rng),
            "order_control_rng_state": _rng_state_bytes(W.order_control_rng),
            "collector_is_none": W._order_control_baseline_collector is None,
        },
        "vehicles": _vehicle_snapshot(W, vehicle_names),
        "nodes": {
            JUNCTION_NODE_NAME: {
                "incoming_vehicle_names": [
                    vehicle.name for vehicle in junction.incoming_vehicles
                ],
            }
        },
        "links": {
            INLINK_NAME: {
                "vehicle_names": [vehicle.name for vehicle in inlink.vehicles],
            },
            OUTLINK_NAME: {
                "vehicle_names": [vehicle.name for vehicle in outlink.vehicles],
                "u": float(outlink.u),
            },
        },
    }


def _assert_snapshot_equal(before: dict, after: dict, context: str) -> None:
    if before != after:
        raise AssertionError(
            f"real_W comparison snapshot mismatch after {context}: "
            f"before={before!r} after={after!r}"
        )


def _assert_arrived_snapshot_vehicle(W: World, vehicle, snapshot_T: int) -> None:
    junction = W.get_node(JUNCTION_NODE_NAME)
    inlink = W.get_link(INLINK_NAME)
    visit = vehicle.order_control_current_visit
    if visit is None:
        raise AssertionError(f"{vehicle.name}: expected current visit at snapshot")
    if vehicle not in junction.incoming_vehicles:
        raise AssertionError(
            f"{vehicle.name}: expected to be in junction.incoming_vehicles at snapshot"
        )
    if vehicle not in inlink.vehicles:
        raise AssertionError(
            f"{vehicle.name}: expected to be in in.vehicles at snapshot"
        )
    if visit["node"] is not junction:
        raise AssertionError(f"{vehicle.name}: current visit node must be junction")
    if visit["inlink"] is not inlink:
        raise AssertionError(f"{vehicle.name}: current visit inlink must be in")
    if visit["arrival_time"] is None or visit["arrival_tiebreaker"] is None:
        raise AssertionError(
            f"{vehicle.name}: expected arrival_time and arrival_tiebreaker at snapshot"
        )
    if vehicle.route_next_link is None or vehicle.route_next_link.name != OUTLINK_NAME:
        raise AssertionError(f"{vehicle.name}: expected route_next_link out at snapshot")
    arrival_timestep = int(round(visit["arrival_time"] / W.DELTAT))
    if arrival_timestep >= snapshot_T:
        raise AssertionError(
            f"{vehicle.name}: arrival timestep {arrival_timestep} must be < {snapshot_T}"
        )


def _assert_not_yet_arrived_snapshot_vehicle(W: World, vehicle) -> None:
    junction = W.get_node(JUNCTION_NODE_NAME)
    inlink = W.get_link(INLINK_NAME)
    visit = vehicle.order_control_current_visit
    if visit is None:
        raise AssertionError(f"{vehicle.name}: expected current visit at snapshot")
    if vehicle not in inlink.vehicles:
        raise AssertionError(f"{vehicle.name}: expected on in.vehicles at snapshot")
    if vehicle in junction.incoming_vehicles:
        raise AssertionError(
            f"{vehicle.name}: must not be in junction.incoming_vehicles at snapshot"
        )
    if visit["node"] is not junction:
        raise AssertionError(f"{vehicle.name}: current visit node must be junction")
    if visit["inlink"] is not inlink:
        raise AssertionError(f"{vehicle.name}: current visit inlink must be in")
    if visit["arrival_time"] is not None or visit["arrival_tiebreaker"] is not None:
        raise AssertionError(
            f"{vehicle.name}: arrival information must be None at snapshot"
        )


def _assert_blocker_excluded_from_fixed_set(W: World, blocker) -> None:
    junction = W.get_node(JUNCTION_NODE_NAME)
    inlink = W.get_link(INLINK_NAME)
    if blocker in inlink.vehicles:
        raise AssertionError("outlink_blocker must not be on in.vehicles")
    if blocker in junction.incoming_vehicles:
        raise AssertionError("outlink_blocker must not be in junction.incoming_vehicles")


def _assert_registration_immediately_after(
    collector: OrderControlBaselineCollector,
    *,
    arrived_vehicle,
    not_yet_arrived_vehicle,
    registered_count: int,
) -> None:
    if registered_count != 2:
        raise AssertionError(
            f"register_snapshot_fixed_visits returned {registered_count}, expected 2"
        )

    arrived_visit_id = arrived_vehicle.order_control_visit_id
    not_yet_visit_id = not_yet_arrived_vehicle.order_control_visit_id

    arrived_record = collector.get_baseline_visit_snapshot(
        arrived_vehicle.name, arrived_visit_id
    )
    not_yet_record = collector.get_baseline_visit_snapshot(
        not_yet_arrived_vehicle.name, not_yet_visit_id
    )
    if arrived_record is None or not_yet_record is None:
        raise AssertionError(
            "expected both fixed-set records immediately after register"
        )

    if arrived_record["was_arrived_at_snapshot"] is not True:
        raise AssertionError(
            "arrived_fixed_vehicle must be was_arrived_at_snapshot=True"
        )
    if arrived_record["baseline_arrival_timestep"] is None:
        raise AssertionError(
            "arrived_fixed_vehicle must have baseline_arrival_timestep"
        )
    if arrived_record["baseline_passage_timestep"] is not None:
        raise AssertionError("arrived_fixed_vehicle passage must still be None")
    if arrived_record["route_next_link_name"] != OUTLINK_NAME:
        raise AssertionError(
            "arrived_fixed_vehicle route_next_link_name must be out"
        )

    if not_yet_record["was_arrived_at_snapshot"] is not False:
        raise AssertionError(
            "not_yet_arrived_fixed_vehicle must be was_arrived_at_snapshot=False"
        )
    if not_yet_record["baseline_arrival_timestep"] is not None:
        raise AssertionError(
            "not_yet_arrived baseline_arrival_timestep must be None"
        )
    if not_yet_record["arrival_tiebreaker"] is not None:
        raise AssertionError("not_yet_arrived arrival_tiebreaker must be None")
    if not_yet_record["route_next_link_name"] is not None:
        raise AssertionError("not_yet_arrived route_next_link_name must be None")
    if not_yet_record["baseline_passage_timestep"] is not None:
        raise AssertionError("not_yet_arrived passage must still be None")

    export_records = collector.export_node_baseline_visits(JUNCTION_NODE_NAME)
    if len(export_records) != registered_count:
        raise AssertionError(
            f"junction export count {len(export_records)} != registered_count "
            f"{registered_count}"
        )


def _assert_reference_independence(
    real_W: World,
    fork_W: World,
    fork_collector: OrderControlBaselineCollector,
    arrived_vehicle,
    not_yet_arrived_vehicle,
    blocker,
    *,
    normal_outlink_u: float,
) -> bool:
    if real_W is fork_W:
        raise AssertionError("real_W and fork_W must be different World objects")
    if real_W.get_node(JUNCTION_NODE_NAME) is fork_W.get_node(JUNCTION_NODE_NAME):
        raise AssertionError("junction Node objects must differ between real_W and fork_W")
    if real_W.get_link(INLINK_NAME) is fork_W.get_link(INLINK_NAME):
        raise AssertionError("in Link objects must differ between real_W and fork_W")
    if real_W.get_link(OUTLINK_NAME) is fork_W.get_link(OUTLINK_NAME):
        raise AssertionError("out Link objects must differ between real_W and fork_W")
    if real_W.VEHICLES[arrived_vehicle.name] is fork_W.VEHICLES[arrived_vehicle.name]:
        raise AssertionError("arrived Vehicle objects must differ")
    if (
        real_W.VEHICLES[not_yet_arrived_vehicle.name]
        is fork_W.VEHICLES[not_yet_arrived_vehicle.name]
    ):
        raise AssertionError("not-yet-arrived Vehicle objects must differ")
    if real_W.VEHICLES[blocker.name] is fork_W.VEHICLES[blocker.name]:
        raise AssertionError("blocker Vehicle objects must differ")

    real_outlink = real_W.get_link(OUTLINK_NAME)
    fork_outlink = fork_W.get_link(OUTLINK_NAME)
    fork_blocker = fork_W.VEHICLES[blocker.name]
    if fork_blocker.name not in fork_W.VEHICLES_RUNNING:
        raise AssertionError("fork blocker must be in fork_W.VEHICLES_RUNNING")
    if fork_blocker.link is not fork_outlink:
        raise AssertionError("fork blocker.link must be fork outlink")
    if fork_blocker not in fork_outlink.vehicles:
        raise AssertionError("fork blocker must be in fork outlink.vehicles")
    if real_outlink.u != normal_outlink_u:
        raise AssertionError(
            f"real_W outlink.u must remain {normal_outlink_u}, got {real_outlink.u}"
        )
    if fork_outlink.u != normal_outlink_u:
        raise AssertionError(
            f"fork outlink.u must remain {normal_outlink_u} before release, "
            f"got {fork_outlink.u}"
        )
    if fork_blocker.user_function is None:
        raise AssertionError("fork blocker must still have hold user_function before release")

    fork_arrived = fork_W.VEHICLES[arrived_vehicle.name]
    fork_not_yet = fork_W.VEHICLES[not_yet_arrived_vehicle.name]
    fork_junction = fork_W.get_node(JUNCTION_NODE_NAME)
    fork_inlink = fork_W.get_link(INLINK_NAME)

    if fork_arrived.link is not fork_inlink and fork_arrived.link is not None:
        if fork_arrived.link.W is not fork_W:
            raise AssertionError("fork arrived vehicle link must belong to fork_W")
    arrived_visit = fork_arrived.order_control_current_visit
    if arrived_visit is not None:
        if arrived_visit["node"] is not fork_junction:
            raise AssertionError("fork arrived current visit node must be fork junction")
        if arrived_visit["inlink"] is not fork_inlink:
            raise AssertionError("fork arrived current visit inlink must be fork in")

    not_yet_visit = fork_not_yet.order_control_current_visit
    if not_yet_visit is not None:
        if not_yet_visit["node"] is not fork_junction:
            raise AssertionError("fork not-yet current visit node must be fork junction")
        if not_yet_visit["inlink"] is not fork_inlink:
            raise AssertionError("fork not-yet current visit inlink must be fork in")

    if real_W._order_control_baseline_collector is not None:
        raise AssertionError("real_W collector must remain None")
    if fork_W._order_control_baseline_collector is not fork_collector:
        raise AssertionError("fork_W collector must be the probe collector")
    if hasattr(fork_collector, "W"):
        raise AssertionError("collector must not hold a World back-reference")
    return True


def _outside_record_is_absent(
    collector: OrderControlBaselineCollector, outside_vehicle_name: str
) -> bool:
    for record in collector.export_node_baseline_visits(JUNCTION_NODE_NAME):
        if record["vehicle_name"] == outside_vehicle_name:
            return False
    return True


def _outside_vehicle_collector_record_absent(
    collector: OrderControlBaselineCollector,
    outside_vehicle,
    expected_export_count: int,
    *,
    require_positive_visit_id: bool = True,
) -> bool:
    if require_positive_visit_id:
        visit_id = outside_vehicle.order_control_visit_id
        if not isinstance(visit_id, int) or isinstance(visit_id, bool) or visit_id <= 0:
            return False
        if (
            collector.get_baseline_visit_snapshot(outside_vehicle.name, visit_id)
            is not None
        ):
            return False
    if not _outside_record_is_absent(collector, outside_vehicle.name):
        return False
    if (
        len(collector.export_node_baseline_visits(JUNCTION_NODE_NAME))
        != expected_export_count
    ):
        return False
    return True


def _assert_outside_vehicle_not_recorded(
    collector: OrderControlBaselineCollector,
    outside_vehicle,
    expected_export_count: int,
    context: str,
    *,
    require_positive_visit_id: bool = True,
) -> bool:
    if require_positive_visit_id:
        visit_id = outside_vehicle.order_control_visit_id
        if not isinstance(visit_id, int) or isinstance(visit_id, bool) or visit_id <= 0:
            raise AssertionError(
                f"{context}: outside vehicle visit_id must be a positive int, "
                f"got {visit_id!r}"
            )
        if (
            collector.get_baseline_visit_snapshot(outside_vehicle.name, visit_id)
            is not None
        ):
            raise AssertionError(
                f"{context}: outside vehicle must have no collector record for "
                f"visit_id={visit_id}"
            )
    if not _outside_record_is_absent(collector, outside_vehicle.name):
        raise AssertionError(
            f"{context}: outside vehicle name must not appear in node export"
        )
    export_count = len(collector.export_node_baseline_visits(JUNCTION_NODE_NAME))
    if export_count != expected_export_count:
        raise AssertionError(
            f"{context}: junction export count {export_count} != "
            f"expected {expected_export_count}"
        )
    return True


def _observe_outside_vehicle_progress(
    fork_W: World,
    outside_vehicle,
    *,
    outside_entered_inlink: bool,
    outside_arrived_at_target_node: bool,
    outside_arrival_timestep: int | None,
    outside_passed_target_node: bool,
) -> tuple[bool, bool, int | None, bool]:
    fork_junction = fork_W.get_node(JUNCTION_NODE_NAME)
    fork_inlink = fork_W.get_link(INLINK_NAME)
    fork_outlink = fork_W.get_link(OUTLINK_NAME)

    entered_inlink = outside_entered_inlink
    if not entered_inlink:
        visit = outside_vehicle.order_control_current_visit
        if outside_vehicle.link is fork_inlink:
            entered_inlink = True
        elif (
            visit is not None
            and visit.get("node") is fork_junction
            and visit.get("inlink") is fork_inlink
        ):
            entered_inlink = True

    arrived_at_target = outside_arrived_at_target_node
    arrival_timestep = outside_arrival_timestep
    if not arrived_at_target:
        visit = outside_vehicle.order_control_current_visit
        if visit is not None:
            node = visit.get("node")
            inlink = visit.get("inlink")
            arrival_time = visit.get("arrival_time")
            arrival_tiebreaker = visit.get("arrival_tiebreaker")
            if (
                node is fork_junction
                and inlink is fork_inlink
                and arrival_time is not None
                and arrival_tiebreaker is not None
            ):
                arrived_at_target = True
                arrival_timestep = int(round(arrival_time / fork_W.DELTAT))

    passed_target = outside_passed_target_node
    if not passed_target and arrived_at_target and outside_vehicle.link is fork_outlink:
        passed_target = True

    return entered_inlink, arrived_at_target, arrival_timestep, passed_target


def _fork_progress_satisfied(
    collector: OrderControlBaselineCollector,
    *,
    arrived_vehicle,
    not_yet_arrived_vehicle,
    outside_vehicle,
    export_count_after_register: int,
    outside_entered_inlink: bool,
    outside_arrived_at_target_node: bool,
    outside_passed_target_node: bool,
    outside_checked_after_arrival: bool,
    outside_checked_after_passage: bool,
) -> bool:
    arrived_record = collector.get_baseline_visit_snapshot(
        arrived_vehicle.name, arrived_vehicle.order_control_visit_id
    )
    not_yet_record = collector.get_baseline_visit_snapshot(
        not_yet_arrived_vehicle.name,
        not_yet_arrived_vehicle.order_control_visit_id,
    )
    if arrived_record is None or not_yet_record is None:
        return False
    if arrived_record["baseline_passage_timestep"] is None:
        return False
    if not_yet_record["baseline_arrival_timestep"] is None:
        return False
    if not_yet_record["baseline_passage_timestep"] is None:
        return False
    if not outside_entered_inlink:
        return False
    if not outside_arrived_at_target_node:
        return False
    if not outside_passed_target_node:
        return False
    if not outside_checked_after_arrival:
        return False
    if not outside_checked_after_passage:
        return False
    if not _outside_vehicle_collector_record_absent(
        collector, outside_vehicle, export_count_after_register
    ):
        return False
    return True


def run_probe() -> dict:
    # 1. Build real_W
    real_W = _build_small_time_value_world()

    # 2. Configure time_value target nodes and derive node names once
    configured_tvt_nodes = real_W.set_order_control_for_nodes(
        [JUNCTION_NODE_NAME],
        order_control_type="time_value",
    )
    tvt_target_node_names = [node.name for node in configured_tvt_nodes]

    # 3. Place blocker and fixed-set vehicles, then advance to snapshot_T
    blocker, normal_outlink_u = _place_outlink_blocker(real_W)
    _assert_blocker_placement_consistent(real_W, blocker, normal_outlink_u=normal_outlink_u)
    arrived_vehicle = real_W.addVehicle(
        "orig", "dest", ARRIVED_DEPARTURE, name=ARRIVED_VEHICLE_NAME
    )
    not_yet_arrived_vehicle = real_W.addVehicle(
        "orig",
        "dest",
        NOT_YET_ARRIVED_DEPARTURE,
        name=NOT_YET_ARRIVED_VEHICLE_NAME,
    )
    real_W.exec_simulation(duration_t2=SNAPSHOT_T * real_W.DELTAT)

    if real_W._order_control_baseline_collector is not None:
        raise AssertionError("real_W collector must be None before fork")
    if real_W.T != SNAPSHOT_T:
        raise AssertionError(
            f"real_W.T must be {SNAPSHOT_T} before fork, got {real_W.T}"
        )

    junction = real_W.get_node(JUNCTION_NODE_NAME)
    if not junction.order_control_eligible:
        raise AssertionError("junction must be order-control eligible")
    if junction.order_control_type != "time_value":
        raise AssertionError("junction must be time_value on real_W")

    blocker = real_W.VEHICLES[BLOCKER_VEHICLE_NAME]
    _assert_blocker_at_entrance_after_snapshot(real_W, blocker)
    _assert_blocker_excluded_from_fixed_set(real_W, blocker)
    _assert_arrived_snapshot_vehicle(real_W, arrived_vehicle, SNAPSHOT_T)
    _assert_not_yet_arrived_snapshot_vehicle(real_W, not_yet_arrived_vehicle)

    # 4. Save real_W comparison snapshot before fork
    real_vehicle_names = [
        ARRIVED_VEHICLE_NAME,
        NOT_YET_ARRIVED_VEHICLE_NAME,
        BLOCKER_VEHICLE_NAME,
    ]
    real_snapshot_before_fork = _real_world_comparison_snapshot(
        real_W, real_vehicle_names
    )
    real_outlink_u_before_fork = float(real_W.get_link(OUTLINK_NAME).u)

    # 5. fork_W = real_W.copy()
    fork_W = real_W.copy()
    if fork_W.T != SNAPSHOT_T:
        raise AssertionError(
            f"fork_W.T must be {SNAPSHOT_T} immediately after copy, got {fork_W.T}"
        )

    fork_collector = OrderControlBaselineCollector()
    fork_W._order_control_baseline_collector = fork_collector

    fork_arrived = fork_W.VEHICLES[ARRIVED_VEHICLE_NAME]
    fork_not_yet = fork_W.VEHICLES[NOT_YET_ARRIVED_VEHICLE_NAME]
    fork_blocker = fork_W.VEHICLES[BLOCKER_VEHICLE_NAME]
    fork_outlink = fork_W.get_link(OUTLINK_NAME)

    reference_independence = _assert_reference_independence(
        real_W,
        fork_W,
        fork_collector,
        arrived_vehicle,
        not_yet_arrived_vehicle,
        blocker,
        normal_outlink_u=normal_outlink_u,
    )

    # 6. Register snapshot-fixed visits on fork_W once
    registered_count = register_snapshot_fixed_visits(
        fork_W,
        fork_collector,
        target_node_names=tvt_target_node_names,
    )
    _assert_registration_immediately_after(
        fork_collector,
        arrived_vehicle=fork_arrived,
        not_yet_arrived_vehicle=fork_not_yet,
        registered_count=registered_count,
    )
    export_count_after_register = len(
        fork_collector.export_node_baseline_visits(JUNCTION_NODE_NAME)
    )

    # 7. Add outside-fixed-set vehicle on fork_W only
    outside_vehicle = fork_W.addVehicle(
        "orig", "dest", fork_W.T, name=OUTSIDE_VEHICLE_NAME
    )
    if OUTSIDE_VEHICLE_NAME in real_W.VEHICLES:
        raise AssertionError("outside_fixed_vehicle must not exist on real_W")
    _assert_outside_vehicle_not_recorded(
        fork_collector,
        outside_vehicle,
        export_count_after_register,
        context="after outside vehicle add",
        require_positive_visit_id=False,
    )

    # 8. Release fork-side blocker hold so it can leave via normal motion
    _release_fork_outlink_blocker(fork_blocker)
    real_blocker = real_W.VEHICLES[BLOCKER_VEHICLE_NAME]
    if fork_blocker.user_function is not None:
        raise AssertionError("fork blocker hold user_function must be cleared")
    if real_blocker.user_function is None:
        raise AssertionError("real_W blocker hold user_function must remain after fork release")
    if float(real_W.get_link(OUTLINK_NAME).u) != normal_outlink_u:
        raise AssertionError("real_W outlink.u must remain unchanged after fork release")
    if float(fork_outlink.u) != normal_outlink_u:
        raise AssertionError(
            f"fork outlink.u must remain {normal_outlink_u}, got {fork_outlink.u}"
        )

    outside_entered_inlink = False
    outside_arrived_at_target_node = False
    outside_passed_target_node = False
    outside_arrival_timestep: int | None = None
    outside_checked_after_arrival = False
    outside_checked_after_passage = False

    fork_steps_executed = 0
    for _step_index in range(MAX_FORK_STEPS):
        fork_W.exec_simulation(duration_t2=fork_W.DELTAT)
        fork_steps_executed += 1

        (
            outside_entered_inlink,
            outside_arrived_at_target_node,
            outside_arrival_timestep,
            outside_passed_target_node,
        ) = _observe_outside_vehicle_progress(
            fork_W,
            outside_vehicle,
            outside_entered_inlink=outside_entered_inlink,
            outside_arrived_at_target_node=outside_arrived_at_target_node,
            outside_arrival_timestep=outside_arrival_timestep,
            outside_passed_target_node=outside_passed_target_node,
        )

        if outside_arrived_at_target_node and not outside_checked_after_arrival:
            _assert_outside_vehicle_not_recorded(
                fork_collector,
                outside_vehicle,
                export_count_after_register,
                context="after outside vehicle arrival",
            )
            outside_checked_after_arrival = True

        if outside_passed_target_node and not outside_checked_after_passage:
            _assert_outside_vehicle_not_recorded(
                fork_collector,
                outside_vehicle,
                export_count_after_register,
                context="after outside vehicle passage",
            )
            outside_checked_after_passage = True

        if _fork_progress_satisfied(
            fork_collector,
            arrived_vehicle=fork_arrived,
            not_yet_arrived_vehicle=fork_not_yet,
            outside_vehicle=outside_vehicle,
            export_count_after_register=export_count_after_register,
            outside_entered_inlink=outside_entered_inlink,
            outside_arrived_at_target_node=outside_arrived_at_target_node,
            outside_passed_target_node=outside_passed_target_node,
            outside_checked_after_arrival=outside_checked_after_arrival,
            outside_checked_after_passage=outside_checked_after_passage,
        ):
            break
    else:
        arrived_record = fork_collector.get_baseline_visit_snapshot(
            fork_arrived.name, fork_arrived.order_control_visit_id
        )
        not_yet_record = fork_collector.get_baseline_visit_snapshot(
            fork_not_yet.name, fork_not_yet.order_control_visit_id
        )
        raise AssertionError(
            "fork forward exceeded MAX_FORK_STEPS="
            f"{MAX_FORK_STEPS}; fork_W.T={fork_W.T}; "
            f"arrived_record={arrived_record}; not_yet_record={not_yet_record}; "
            f"outside_visit_id={outside_vehicle.order_control_visit_id}; "
            f"outside_entered_inlink={outside_entered_inlink}; "
            f"outside_arrived_at_target_node={outside_arrived_at_target_node}; "
            f"outside_passed_target_node={outside_passed_target_node}; "
            f"outside_arrival_timestep={outside_arrival_timestep}; "
            f"outside_checked_after_arrival={outside_checked_after_arrival}; "
            f"outside_checked_after_passage={outside_checked_after_passage}; "
            f"export_count={len(fork_collector.export_node_baseline_visits(JUNCTION_NODE_NAME))}"
        )

    # 9. Confirm real_W unchanged
    real_snapshot_after_fork = _real_world_comparison_snapshot(
        real_W, real_vehicle_names
    )
    real_world_unchanged = real_snapshot_before_fork == real_snapshot_after_fork
    if not real_world_unchanged:
        _assert_snapshot_equal(
            real_snapshot_before_fork,
            real_snapshot_after_fork,
            context="fork forward and collector checks",
        )

    real_outlink_speed_unchanged = (
        float(real_W.get_link(OUTLINK_NAME).u) == real_outlink_u_before_fork == normal_outlink_u
    )
    if not real_outlink_speed_unchanged:
        raise AssertionError(
            "real_W outlink.u must remain unchanged across fork forward"
        )

    blocker_managed_consistently = _assert_blocker_management_on_fork(
        fork_W, fork_blocker
    )

    outside_fixed_vehicle_recorded = not _outside_vehicle_collector_record_absent(
        fork_collector,
        outside_vehicle,
        export_count_after_register,
    )
    if outside_fixed_vehicle_recorded:
        raise AssertionError(
            "outside_fixed_vehicle must not have a collector record at probe end"
        )

    arrived_record = fork_collector.get_baseline_visit_snapshot(
        fork_arrived.name, fork_arrived.order_control_visit_id
    )
    not_yet_record = fork_collector.get_baseline_visit_snapshot(
        fork_not_yet.name, fork_not_yet.order_control_visit_id
    )

    return {
        "snapshot_timestep": SNAPSHOT_T,
        "registered_visit_count": registered_count,
        "arrived_fixed_vehicle": {
            "baseline_arrival_timestep": arrived_record["baseline_arrival_timestep"],
            "baseline_passage_timestep": arrived_record["baseline_passage_timestep"],
        },
        "not_yet_arrived_fixed_vehicle": {
            "baseline_arrival_timestep": not_yet_record["baseline_arrival_timestep"],
            "baseline_passage_timestep": not_yet_record["baseline_passage_timestep"],
        },
        "outside_fixed_vehicle_entered_inlink": outside_entered_inlink,
        "outside_fixed_vehicle_arrived_at_target_node": outside_arrived_at_target_node,
        "outside_fixed_vehicle_passed_target_node": outside_passed_target_node,
        "outside_fixed_vehicle_arrival_timestep": outside_arrival_timestep,
        "outside_fixed_vehicle_recorded": outside_fixed_vehicle_recorded,
        "real_world_unchanged": real_world_unchanged,
        "reference_independence": reference_independence,
        "blocker_state": fork_blocker.state,
        "blocker_managed_consistently": blocker_managed_consistently,
        "real_outlink_speed_unchanged": real_outlink_speed_unchanged,
        "final_fork_timestep": fork_W.T,
        "fork_steps_executed": fork_steps_executed,
    }


def main() -> None:
    result = run_probe()
    print(result)
    print("TVT baseline snapshot fork probe passed.")


if __name__ == "__main__":
    main()
