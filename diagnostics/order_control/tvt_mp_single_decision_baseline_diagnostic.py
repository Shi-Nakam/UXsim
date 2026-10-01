# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Stage 1: single time_value junction, four snapshot-fixed not-yet-arrived visits,
# real run_snapshot_fixed_baseline_fork, baseline arrival/passage checks only.
#
# Run from repository root:
#   python diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py

from __future__ import annotations

import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from uxsim import World
from uxsim.order_control_baseline_driver import run_snapshot_fixed_baseline_fork
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetStatus,
)
from uxsim.order_control_tvt_mp_candidate_binding_transfer import (
    OrderControlTvtMpBindingVisitTemporarySkipReason,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionStatus,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    OrderControlTvtMpPaymentAndCompensationStatus,
)
from uxsim.order_control_tvt_mp_driver import run_tvt_mp_driver
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_final_rank import OrderControlTvtMpFinalRankStatus
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtRightOfEntrySelectionStatus,
)

# --- Network constants (aligned with tests_order_control_baseline_driver) ---

JUNCTION_NODE_NAME = "junction"
OUTLINK_NAME = "out"
LINK_LENGTH = 200.0
FREE_FLOW_SPEED = 20.0
NUMBER_OF_LANES = 1

SNAPSHOT_TIMESTEP_T = 10
BASELINE_HORIZON_STEPS = 25
WORLD_TMAX = 120

EXPECTED_BASELINE_ARRIVALS = {"A": 11, "B": 12, "C": 13, "D": 14}
# RoE passage p must satisfy every candidate arrival <= p - 1 (P-1 rule).
# Arrivals 11..14 therefore need A passage >= 15; outlink gate delays merge.
OUTLINK_GATE_RELEASE_TIMESTEP = 15
EXPECTED_BASELINE_PASSAGES = {"A": 15, "B": 16, "C": 17, "D": 18}
OUTLINK_GATE_VEHICLE_NAME = "outlink_passage_gate_vehicle"

STAGE2_DECLARED_VOT_BY_VEHICLE = {
    "A": 0.0,
    "B": 1.0,
    "C": 5.0,
    "D": 100.0,
}
STAGE2_VOT_TRUE_BY_VEHICLE = {
    "A": 12.0,
    "B": 13.0,
    "C": 6.0,
    "D": 15.0,
}

EXPECTED_CONCRETE_BUYER_LABELS = (
    ("B",),
    ("D",),
    ("B", "D"),
)


@dataclass
class AdvanceUntilMetrics:
    vehicle_name: str
    exec_simulation_call_count: int
    world_t_at_start: int
    world_t_at_end: int
    elapsed_seconds: float


@dataclass
class BuildDiagnosticWorldTimings:
    total_seconds: float = 0.0
    world_constructor_seconds: float = 0.0
    add_nodes_links_seconds: float = 0.0
    prepare_network_total_seconds: float = 0.0
    finalize_scenario_seconds: float = 0.0
    link_update_seconds: float = 0.0


@dataclass
class DriverPipelineTrace:
    """Saved references reached from one successful run_tvt_mp_driver result."""

    atomic_apply_set_result: object
    final_consistency_validation_set_result: object
    final_rank_set_result: object
    payment_and_compensation_set_result: object
    candidate_selection_set_result: object
    economic_evaluation_set_result: object
    local_virtual_calculation_set_result: object
    fifo_inspection_set_result: object
    general_trade_rank_set_result: object
    concrete_buyer_candidate_set_result: object
    inlink_candidate_physical_order_result: object
    candidate_visit_set_result: object
    right_of_entry_selection_result: object


@dataclass
class WorldPrepareTimingBreakdown:
    build_diagnostic_world: BuildDiagnosticWorldTimings = field(
        default_factory=BuildDiagnosticWorldTimings
    )
    add_diagnostic_vehicles_seconds: float = 0.0
    advance_all_vehicles_seconds: float = 0.0
    advance_by_vehicle: dict[str, AdvanceUntilMetrics] = field(default_factory=dict)
    open_junction_capacities_seconds: float = 0.0
    snapshot_placement_seconds: float = 0.0
    assert_capacity_ready_seconds: float = 0.0


VEHICLE_SPECS = (
    {
        "name": "A",
        "origin": "orig_roe",
        "inlink": "in_roe",
        "participates": True,
        "vot_declared": 10.0,
        "vot_true": 12.0,
        # Free flow: one step moves u*DT (=20). Arrival at T+1 needs x=160 at snapshot.
        "snapshot_x": 160.0,
    },
    {
        "name": "B",
        "origin": "orig_aux",
        "inlink": "in_aux",
        "participates": True,
        "vot_declared": 11.0,
        "vot_true": 13.0,
        "snapshot_x": 140.0,
    },
    {
        "name": "C",
        "origin": "orig_np",
        "inlink": "in_np",
        "participates": False,
        "vot_declared": 5.0,
        "vot_true": 6.0,
        "snapshot_x": 120.0,
    },
    {
        "name": "D",
        "origin": "orig_buy",
        "inlink": "in_buy",
        "participates": True,
        "vot_declared": 14.0,
        "vot_true": 15.0,
        "snapshot_x": 100.0,
    },
)


def prepare_network(world: World) -> None:
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()


def build_diagnostic_world(
    build_timings: BuildDiagnosticWorldTimings,
) -> World:
    build_start = time.perf_counter()

    constructor_start = time.perf_counter()
    world = World(
        name="tvt_mp_single_decision_baseline_diagnostic",
        deltan=1,
        tmax=WORLD_TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    build_timings.world_constructor_seconds = (
        time.perf_counter() - constructor_start
    )

    nodes_links_start = time.perf_counter()
    world.addNode("orig_roe", 0, 0)
    world.addNode("orig_aux", 0, 1)
    world.addNode("orig_np", 0, 2)
    world.addNode("orig_buy", 0, 3)
    world.addNode(
        JUNCTION_NODE_NAME,
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    world.addNode("dest", 2, 0)

    link_kwargs = {
        "length": LINK_LENGTH,
        "free_flow_speed": FREE_FLOW_SPEED,
        "number_of_lanes": NUMBER_OF_LANES,
    }
    world.addLink("in_roe", "orig_roe", JUNCTION_NODE_NAME, **link_kwargs)
    world.addLink("in_aux", "orig_aux", JUNCTION_NODE_NAME, **link_kwargs)
    world.addLink("in_np", "orig_np", JUNCTION_NODE_NAME, **link_kwargs)
    world.addLink("in_buy", "orig_buy", JUNCTION_NODE_NAME, **link_kwargs)
    world.addLink(OUTLINK_NAME, JUNCTION_NODE_NAME, "dest", **link_kwargs)
    build_timings.add_nodes_links_seconds = (
        time.perf_counter() - nodes_links_start
    )

    prepare_network_start = time.perf_counter()
    if not getattr(world, "finalized", 0):
        finalize_start = time.perf_counter()
        world.finalize_scenario()
        build_timings.finalize_scenario_seconds = (
            time.perf_counter() - finalize_start
        )
    else:
        build_timings.finalize_scenario_seconds = 0.0

    link_update_start = time.perf_counter()
    for link in world.LINKS:
        link.update()
    build_timings.link_update_seconds = time.perf_counter() - link_update_start
    build_timings.prepare_network_total_seconds = (
        time.perf_counter() - prepare_network_start
    )

    build_timings.total_seconds = time.perf_counter() - build_start
    return world


def add_diagnostic_vehicles(world: World) -> dict[str, object]:
    vehicles_by_name: dict[str, object] = {}
    for spec in VEHICLE_SPECS:
        vehicle = world.addVehicle(
            spec["origin"],
            "dest",
            0,
            name=spec["name"],
            participates_in_order_exchange=spec["participates"],
            vot_declared=spec["vot_declared"],
            vot_true=spec["vot_true"],
        )
        vehicles_by_name[spec["name"]] = vehicle
    return vehicles_by_name


def advance_until_on_inlink(vehicle, inlink_name: str) -> AdvanceUntilMetrics:
    advance_start = time.perf_counter()
    world_t_at_start = vehicle.W.T
    exec_simulation_call_count = 0

    while vehicle.link is None or vehicle.link.name != inlink_name:
        if not vehicle.W.check_simulation_ongoing():
            raise RuntimeError(
                f"Vehicle {vehicle.name!r} did not reach inlink {inlink_name!r} "
                f"before simulation ended (W.T={vehicle.W.T})."
            )
        vehicle.W.exec_simulation(duration_t2=vehicle.W.DELTAT)
        exec_simulation_call_count += 1

    return AdvanceUntilMetrics(
        vehicle_name=vehicle.name,
        exec_simulation_call_count=exec_simulation_call_count,
        world_t_at_start=world_t_at_start,
        world_t_at_end=vehicle.W.T,
        elapsed_seconds=time.perf_counter() - advance_start,
    )


def assert_vehicle_on_approach_inlink(vehicle, spec: dict) -> None:
    inlink_name = spec["inlink"]
    junction = vehicle.W.get_node(JUNCTION_NODE_NAME)
    inlink = vehicle.W.get_link(inlink_name)

    assert vehicle.state == "run", (
        f"{vehicle.name}: expected state 'run', got {vehicle.state!r}"
    )
    assert vehicle.link is inlink, (
        f"{vehicle.name}: expected link {inlink_name!r}, "
        f"got {None if vehicle.link is None else vehicle.link.name!r}"
    )
    current_visit = vehicle.order_control_current_visit
    assert current_visit is not None, (
        f"{vehicle.name}: order_control_current_visit is None"
    )
    assert current_visit["node"] is junction, (
        f"{vehicle.name}: visit node mismatch"
    )
    assert current_visit["inlink"] is inlink, (
        f"{vehicle.name}: visit inlink mismatch"
    )
    assert current_visit["visit_id"] == vehicle.order_control_visit_id, (
        f"{vehicle.name}: visit_id {current_visit['visit_id']} != "
        f"order_control_visit_id {vehicle.order_control_visit_id}"
    )
    assert vehicle in inlink.vehicles, (
        f"{vehicle.name}: not in {inlink_name}.vehicles"
    )
    assert vehicle.name in vehicle.W.VEHICLES_RUNNING, (
        f"{vehicle.name}: not in VEHICLES_RUNNING"
    )


def align_free_flow_kinematics_for_snapshot(vehicle, inlink) -> None:
    """Match carfollow/update expectations for a lone vehicle on the link."""
    world = vehicle.W
    step_distance = inlink.u * world.DELTAT
    vehicle.lane = 0
    vehicle.leader = None
    vehicle.follower = None
    vehicle.x_old = vehicle.x
    raw_next = vehicle.x + step_distance
    if raw_next > inlink.length:
        vehicle.move_remain = raw_next - inlink.length
        vehicle.x_next = inlink.length
    else:
        vehicle.move_remain = 0.0
        vehicle.x_next = raw_next
    vehicle.v = inlink.u


def ensure_single_vehicle_on_inlink(inlink, vehicle) -> None:
    inlink.vehicles.clear()
    inlink.vehicles.append(vehicle)


def place_not_yet_arrived_at_snapshot(
    world: World,
    vehicle,
    *,
    inlink_name: str,
    snapshot_timestep: int,
    x_position: float,
) -> None:
    """
    B-type snapshot contract (see tests_order_control_baseline_driver helper).
    route_next_link stays unset for collector registration; kinematics are aligned
    for the next fork timestep.
    """
    inlink = world.get_link(inlink_name)
    junction = world.get_node(JUNCTION_NODE_NAME)

    world.T = snapshot_timestep
    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = x_position
    vehicle.link_arrival_time = float((snapshot_timestep - 1) * world.DELTAT)

    ensure_single_vehicle_on_inlink(inlink, vehicle)

    if vehicle in junction.incoming_vehicles:
        junction.incoming_vehicles.remove(vehicle)

    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise RuntimeError(
            f"{vehicle.name}: expected current visit before snapshot placement"
        )
    current_visit["arrival_time"] = None
    current_visit["arrival_tiebreaker"] = None

    align_free_flow_kinematics_for_snapshot(vehicle, inlink)

    # B-type collector registration still stores route_next_link_name=None.
    vehicle.route_next_link = world.get_link(OUTLINK_NAME)

    assert vehicle.x < inlink.length, (
        f"{vehicle.name}: snapshot x={vehicle.x} must be before link end "
        f"{inlink.length}"
    )


def make_timed_outlink_gate_user_function(
    outlink_name: str,
    release_timestep: int,
):
    """Hold a diagnostic gate vehicle at the outlink entrance until release_timestep."""

    def hold_gate_vehicle(vehicle) -> None:
        if vehicle.link is None or vehicle.link.name != outlink_name:
            return
        # Remove at the end of timestep release_timestep - 1 so merge at
        # release_timestep is unobstructed.
        if vehicle.W.T >= release_timestep - 1:
            outlink = vehicle.link
            if vehicle in outlink.vehicles:
                outlink.vehicles.remove(vehicle)
            vehicle.link = None
            vehicle.state = "end"
            vehicle.W.VEHICLES_RUNNING.pop(vehicle.name, None)
            vehicle.W.VEHICLES_LIVING.pop(vehicle.name, None)
            return
        vehicle.x = 0.0
        vehicle.x_old = 0.0
        vehicle.x_next = 0.0
        vehicle.v = 0.0
        vehicle.move_remain = 0.0

    return hold_gate_vehicle


def place_outlink_passage_gate_vehicle(world: World) -> None:
    """
    Diagnostic-only outlink entrance gate so RoE passage occurs late enough
    for four P-1-eligible candidate visits (arrivals 11..14 need passage >= 15).
    """
    outlink = world.get_link(OUTLINK_NAME)
    gate_vehicle = world.addVehicle(
        "orig_roe",
        "dest",
        0,
        name=OUTLINK_GATE_VEHICLE_NAME,
    )
    gate_vehicle.link = outlink
    gate_vehicle.state = "run"
    gate_vehicle.x = 0.0
    gate_vehicle.x_old = 0.0
    gate_vehicle.x_next = 0.0
    gate_vehicle.v = 0.0
    gate_vehicle.move_remain = 0.0
    gate_vehicle.link_arrival_time = 0.0
    # Vehicle.__init__ does not set route_next_link; outlink snapshot requires the attribute.
    gate_vehicle.route_next_link = None
    gate_vehicle.user_function = make_timed_outlink_gate_user_function(
        OUTLINK_NAME,
        OUTLINK_GATE_RELEASE_TIMESTEP,
    )
    if gate_vehicle not in outlink.vehicles:
        outlink.vehicles.append(gate_vehicle)
    world.VEHICLES_RUNNING[gate_vehicle.name] = gate_vehicle


def open_junction_capacities_for_baseline(world: World) -> None:
    """Diagnostic-only: avoid copy/fork inheriting tight capacity tokens."""
    junction = world.get_node(JUNCTION_NODE_NAME)
    junction.flow_capacity_remain = 1.0e10
    junction.order_control_clearance_timesteps = 0
    junction.last_order_control_inlink = None
    junction.last_order_control_entry_timestep = None

    for link_name in ("in_roe", "in_aux", "in_np", "in_buy", OUTLINK_NAME):
        link = world.get_link(link_name)
        link.capacity_in_remain = 1.0e10
        link.capacity_out_remain = 1.0e10


def assert_capacity_ready_for_fork(world: World) -> None:
    junction = world.get_node(JUNCTION_NODE_NAME)
    assert junction.flow_capacity_remain > world.DELTAN, (
        f"junction flow_capacity_remain too low: {junction.flow_capacity_remain}"
    )
    for link_name in ("in_roe", "in_aux", "in_np", "in_buy", OUTLINK_NAME):
        link = world.get_link(link_name)
        assert link.capacity_in_remain >= world.DELTAN, (
            f"{link_name} capacity_in_remain={link.capacity_in_remain}"
        )
        assert link.capacity_out_remain >= world.DELTAN, (
            f"{link_name} capacity_out_remain={link.capacity_out_remain}"
        )


def collect_vehicle_snapshot_row(vehicle, spec: dict) -> dict:
    inlink = vehicle.W.get_link(spec["inlink"])
    current_visit = vehicle.order_control_current_visit
    return {
        "vehicle_name": vehicle.name,
        "visit_id": vehicle.order_control_visit_id,
        "inlink_name": spec["inlink"],
        "x": vehicle.x,
        "x_next": vehicle.x_next,
        "move_remain": vehicle.move_remain,
        "arrival_time": current_visit["arrival_time"] if current_visit else None,
        "in_incoming": vehicle in vehicle.W.get_node(JUNCTION_NODE_NAME).incoming_vehicles,
    }


def get_baseline_visit_snapshot(collector, vehicle) -> dict:
    return collector.get_baseline_visit_snapshot(
        vehicle.name,
        vehicle.order_control_visit_id,
    )


def assert_arrival_order(
    snapshots_by_name: dict[str, dict],
    snapshot_timestep_t: int,
) -> None:
    names = ["A", "B", "C", "D"]
    arrivals = []
    for name in names:
        snap = snapshots_by_name[name]
        arrival = snap["baseline_arrival_timestep"]
        assert arrival is not None, (
            f"{name}: baseline_arrival_timestep is None; full snapshot={snap}"
        )
        assert snapshot_timestep_t < arrival <= snapshot_timestep_t + 6, (
            f"{name}: arrival {arrival} outside "
            f"({snapshot_timestep_t}, {snapshot_timestep_t + 6}]"
        )
        arrivals.append((name, arrival))

    for index in range(len(arrivals) - 1):
        left_name, left_arrival = arrivals[index]
        right_name, right_arrival = arrivals[index + 1]
        assert left_arrival < right_arrival, (
            f"Arrival order violated: {left_name}={left_arrival}, "
            f"{right_name}={right_arrival}; all arrivals={arrivals}"
        )


def assert_passage_recorded(snapshots_by_name: dict[str, dict]) -> None:
    for name in ("A", "B", "C", "D"):
        snap = snapshots_by_name[name]
        passage = snap["baseline_passage_timestep"]
        arrival = snap["baseline_arrival_timestep"]
        assert passage is not None, (
            f"{name}: baseline_passage_timestep is None; snapshot={snap}"
        )
        assert passage >= arrival + 1, (
            f"{name}: passage {passage} < arrival+1 ({arrival + 1})"
        )


def assert_expected_baseline_timesteps(snapshots_by_name: dict[str, dict]) -> None:
    for name, expected_arrival in EXPECTED_BASELINE_ARRIVALS.items():
        actual = snapshots_by_name[name]["baseline_arrival_timestep"]
        assert actual == expected_arrival, (
            f"{name}: baseline_arrival_timestep={actual}, expected {expected_arrival}"
        )
    for name, expected_passage in EXPECTED_BASELINE_PASSAGES.items():
        actual = snapshots_by_name[name]["baseline_passage_timestep"]
        assert actual == expected_passage, (
            f"{name}: baseline_passage_timestep={actual}, expected {expected_passage}"
        )


def assert_inlink_physical_orders(fork_result) -> None:
    expected_inlinks = {"in_roe", "in_aux", "in_np", "in_buy"}
    seen = set()
    for physical_order in fork_result.inlink_physical_orders:
        assert physical_order.node_name == JUNCTION_NODE_NAME
        seen.add(physical_order.inlink_name)
        assert len(physical_order.visit_keys_head_to_tail) == 1
    assert seen == expected_inlinks, (
        f"Unexpected inlink physical orders: {seen!r}"
    )


def visit_keys_to_vehicle_names(
    visit_keys: tuple[OrderControlTvtVisitKey, ...],
) -> tuple[str, ...]:
    return tuple(visit_key[0] for visit_key in visit_keys)


def apply_stage2_vot_settings(vehicles_by_name: dict[str, object]) -> None:
    for vehicle_name, declared_vot in STAGE2_DECLARED_VOT_BY_VEHICLE.items():
        vehicle = vehicles_by_name[vehicle_name]
        vehicle.vot_declared = declared_vot
        vehicle.vot_true = STAGE2_VOT_TRUE_BY_VEHICLE[vehicle_name]


def assert_real_world_unchanged_after_stage1_baseline_fork(world: World) -> None:
    assert world.T == SNAPSHOT_TIMESTEP_T, (
        f"real_W.T={world.T}, expected {SNAPSHOT_TIMESTEP_T}"
    )
    assert world._order_control_baseline_collector is None, (
        "real_W._order_control_baseline_collector must be None after Stage 1 fork"
    )
    assert world._order_control_baseline_downstream_boundary_observer is None, (
        "real_W downstream boundary observer must be None after Stage 1 fork"
    )


def configure_world_for_stage2_driver(world: World) -> None:
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = 4
    world.order_control_tvt_evaluation_end_timestep = None
    world.order_control_tvt_driver_started_timestep = None
    world.order_control_tvt_rank_states_by_node_name = {}


def trace_driver_pipeline(driver_result) -> DriverPipelineTrace:
    atomic_apply_set_result = driver_result.atomic_apply_set_result
    final_consistency_validation_set_result = (
        atomic_apply_set_result.final_consistency_validation_set_result
    )
    final_rank_set_result = (
        final_consistency_validation_set_result.final_rank_set_result
    )
    payment_and_compensation_set_result = (
        final_rank_set_result.payment_and_compensation_set_result
    )
    candidate_selection_set_result = (
        payment_and_compensation_set_result.candidate_selection_set_result
    )
    economic_evaluation_set_result = (
        candidate_selection_set_result.economic_evaluation_set_result
    )
    local_virtual_calculation_set_result = (
        economic_evaluation_set_result.local_virtual_calculation_set_result
    )
    fifo_inspection_set_result = (
        local_virtual_calculation_set_result.fifo_inspection_set_result
    )
    general_trade_rank_set_result = (
        fifo_inspection_set_result.general_trade_rank_set_result
    )
    concrete_buyer_candidate_set_result = (
        general_trade_rank_set_result.concrete_buyer_candidate_set_result
    )
    inlink_candidate_physical_order_result = (
        concrete_buyer_candidate_set_result.inlink_candidate_physical_order_result
    )
    candidate_visit_set_result = (
        inlink_candidate_physical_order_result.candidate_visit_set_result
    )
    right_of_entry_selection_result = (
        candidate_visit_set_result.right_of_entry_selection_result
    )
    return DriverPipelineTrace(
        atomic_apply_set_result=atomic_apply_set_result,
        final_consistency_validation_set_result=(
            final_consistency_validation_set_result
        ),
        final_rank_set_result=final_rank_set_result,
        payment_and_compensation_set_result=payment_and_compensation_set_result,
        candidate_selection_set_result=candidate_selection_set_result,
        economic_evaluation_set_result=economic_evaluation_set_result,
        local_virtual_calculation_set_result=local_virtual_calculation_set_result,
        fifo_inspection_set_result=fifo_inspection_set_result,
        general_trade_rank_set_result=general_trade_rank_set_result,
        concrete_buyer_candidate_set_result=concrete_buyer_candidate_set_result,
        inlink_candidate_physical_order_result=inlink_candidate_physical_order_result,
        candidate_visit_set_result=candidate_visit_set_result,
        right_of_entry_selection_result=right_of_entry_selection_result,
    )


def junction_node_result(node_results: tuple, node_name: str = JUNCTION_NODE_NAME):
    for node_result in node_results:
        if node_result.node_name == node_name:
            return node_result
    raise AssertionError(f"No node result for {node_name!r}")


def find_trade_rank_result_by_buyers(
    node_trade_rank_result,
    expected_buyer_names: tuple[str, ...],
):
    for trade_rank_result in node_trade_rank_result.candidate_trade_rank_results:
        buyer_names = visit_keys_to_vehicle_names(trade_rank_result.buyers_sorted)
        if buyer_names == expected_buyer_names:
            return trade_rank_result
    raise AssertionError(
        f"No trade rank result for buyers {expected_buyer_names!r}"
    )


def find_local_virtual_result_by_buyers(
    node_local_result,
    expected_buyer_names: tuple[str, ...],
):
    for local_result in node_local_result.candidate_local_virtual_calculation_results:
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        if buyer_names == expected_buyer_names:
            return local_result
    raise AssertionError(
        f"No local virtual result for buyers {expected_buyer_names!r}"
    )


def find_economic_result_by_buyers(
    node_economic_result,
    expected_buyer_names: tuple[str, ...],
):
    for economic_result in node_economic_result.candidate_economic_evaluation_results:
        local_result = economic_result.candidate_local_virtual_calculation_result
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        if buyer_names == expected_buyer_names:
            return economic_result
    return None


def find_fifo_result_by_buyers(
    node_fifo_result,
    expected_buyer_names: tuple[str, ...],
):
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        trade_rank_result = fifo_result.general_trade_rank_result
        buyer_names = visit_keys_to_vehicle_names(trade_rank_result.buyers_sorted)
        if buyer_names == expected_buyer_names:
            return fifo_result
    raise AssertionError(f"No FIFO result for buyers {expected_buyer_names!r}")


@dataclass(frozen=True)
class TimestepBindingTransferDiagnosticRow:
    offset: int
    virtual_timestep: int
    transferred_binding_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    newly_recorded_required_passage_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    required_passages_complete_after_node_passage: bool
    calculation_finished_after_timestep_end: bool
    resolved_after_timestep_end: bool


@dataclass(frozen=True)
class NonparticipatingVisitBindingObservation:
    visit_key: OrderControlTvtVisitKey
    appearance_count: int
    first_offset: int | None
    first_virtual_timestep: int | None
    observed_before_stop: bool
    remaining_allowed_offset_count_if_unobserved: int | None


@dataclass(frozen=True)
class CandidateNonparticipatingPassageObservation:
    buyer_names: tuple[str, ...]
    nonparticipating_visit_keys: tuple[OrderControlTvtVisitKey, ...]
    resolved: bool
    stop_reason: object
    final_offset: int
    final_virtual_timestep: int
    simulated_timestep_count: int
    configured_horizon_steps: int
    timestep_rows: tuple[TimestepBindingTransferDiagnosticRow, ...]
    nonparticipating_visit_observations: tuple[
        NonparticipatingVisitBindingObservation,
        ...
    ]
    c_not_in_required_passage_records: bool
    c_never_in_newly_recorded_required_passage_keys: bool


def get_trade_scope_nonparticipating_visit_keys(
    trade_rank_result,
) -> tuple[OrderControlTvtVisitKey, ...]:
    return tuple(trade_rank_result.nonparticipating_visits_sorted)


def collect_binding_passage_offsets_for_visit_key(
    timestep_results: tuple,
    target_visit_key: OrderControlTvtVisitKey,
) -> tuple[tuple[int, int], ...]:
    appearances: list[tuple[int, int]] = []
    for timestep_result in timestep_results:
        transferred_keys = (
            timestep_result.binding_transfer_result.transferred_binding_visit_keys
        )
        if target_visit_key in transferred_keys:
            appearances.append(
                (timestep_result.offset, timestep_result.virtual_timestep)
            )
    return tuple(appearances)


def remaining_allowed_offset_count_after_stop(
    configured_horizon_steps: int,
    final_offset: int,
) -> int:
    last_allowed_offset = configured_horizon_steps - 1
    return last_allowed_offset - final_offset


def build_timestep_binding_transfer_diagnostic_rows(
    local_result,
) -> tuple[TimestepBindingTransferDiagnosticRow, ...]:
    rows: list[TimestepBindingTransferDiagnosticRow] = []
    for timestep_result in local_result.timestep_results:
        rows.append(
            TimestepBindingTransferDiagnosticRow(
                offset=timestep_result.offset,
                virtual_timestep=timestep_result.virtual_timestep,
                transferred_binding_visit_keys=tuple(
                    timestep_result.binding_transfer_result.transferred_binding_visit_keys
                ),
                newly_recorded_required_passage_visit_keys=tuple(
                    timestep_result.newly_recorded_required_passage_visit_keys
                ),
                required_passages_complete_after_node_passage=(
                    timestep_result.required_passages_complete_after_node_passage
                ),
                calculation_finished_after_timestep_end=(
                    timestep_result.calculation_finished_after_timestep_end
                ),
                resolved_after_timestep_end=timestep_result.resolved_after_timestep_end,
            )
        )
    return tuple(rows)


def build_nonparticipating_visit_binding_observation(
    visit_key: OrderControlTvtVisitKey,
    binding_appearances: tuple[tuple[int, int], ...],
    *,
    configured_horizon_steps: int,
    final_offset: int,
) -> NonparticipatingVisitBindingObservation:
    appearance_count = len(binding_appearances)
    if appearance_count == 0:
        return NonparticipatingVisitBindingObservation(
            visit_key=visit_key,
            appearance_count=0,
            first_offset=None,
            first_virtual_timestep=None,
            observed_before_stop=False,
            remaining_allowed_offset_count_if_unobserved=(
                remaining_allowed_offset_count_after_stop(
                    configured_horizon_steps,
                    final_offset,
                )
            ),
        )
    first_offset, first_virtual_timestep = binding_appearances[0]
    return NonparticipatingVisitBindingObservation(
        visit_key=visit_key,
        appearance_count=appearance_count,
        first_offset=first_offset,
        first_virtual_timestep=first_virtual_timestep,
        observed_before_stop=True,
        remaining_allowed_offset_count_if_unobserved=None,
    )


def visit_key_absent_from_required_passage_records(
    local_result,
    visit_key: OrderControlTvtVisitKey,
) -> bool:
    for record in local_result.required_passage_records:
        if record.visit_key == visit_key:
            return False
    return True


def visit_key_never_in_newly_recorded_required_passage_keys(
    local_result,
    visit_key: OrderControlTvtVisitKey,
) -> bool:
    for timestep_result in local_result.timestep_results:
        if visit_key in timestep_result.newly_recorded_required_passage_visit_keys:
            return False
    return True


def build_candidate_nonparticipating_passage_observation(
    trade_rank_result,
    local_result,
) -> CandidateNonparticipatingPassageObservation:
    buyer_names = visit_keys_to_vehicle_names(
        local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    nonparticipating_visit_keys = get_trade_scope_nonparticipating_visit_keys(
        trade_rank_result
    )
    timestep_rows = build_timestep_binding_transfer_diagnostic_rows(local_result)
    nonparticipating_observations: list[NonparticipatingVisitBindingObservation] = []
    for visit_key in nonparticipating_visit_keys:
        binding_appearances = collect_binding_passage_offsets_for_visit_key(
            local_result.timestep_results,
            visit_key,
        )
        nonparticipating_observations.append(
            build_nonparticipating_visit_binding_observation(
                visit_key,
                binding_appearances,
                configured_horizon_steps=local_result.configured_horizon_steps,
                final_offset=local_result.final_offset,
            )
        )

    c_not_in_required = True
    c_never_in_newly_recorded = True
    for visit_key in nonparticipating_visit_keys:
        if not visit_key_absent_from_required_passage_records(local_result, visit_key):
            c_not_in_required = False
        if not visit_key_never_in_newly_recorded_required_passage_keys(
            local_result,
            visit_key,
        ):
            c_never_in_newly_recorded = False

    return CandidateNonparticipatingPassageObservation(
        buyer_names=buyer_names,
        nonparticipating_visit_keys=nonparticipating_visit_keys,
        resolved=local_result.resolved,
        stop_reason=local_result.stop_reason,
        final_offset=local_result.final_offset,
        final_virtual_timestep=local_result.final_virtual_timestep,
        simulated_timestep_count=local_result.simulated_timestep_count,
        configured_horizon_steps=local_result.configured_horizon_steps,
        timestep_rows=timestep_rows,
        nonparticipating_visit_observations=tuple(nonparticipating_observations),
        c_not_in_required_passage_records=c_not_in_required,
        c_never_in_newly_recorded_required_passage_keys=c_never_in_newly_recorded,
    )


def build_all_candidate_nonparticipating_passage_observations(
    pipeline: DriverPipelineTrace,
) -> tuple[CandidateNonparticipatingPassageObservation, ...]:
    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    observations: list[CandidateNonparticipatingPassageObservation] = []
    for buyer_labels in EXPECTED_CONCRETE_BUYER_LABELS:
        trade_rank_result = find_trade_rank_result_by_buyers(
            node_trade_rank_result,
            buyer_labels,
        )
        local_result = find_local_virtual_result_by_buyers(
            node_local_result,
            buyer_labels,
        )
        observations.append(
            build_candidate_nonparticipating_passage_observation(
                trade_rank_result,
                local_result,
            )
        )
    return tuple(observations)


def assert_nonparticipating_candidate_passage_observations(
    pipeline: DriverPipelineTrace,
    observations: tuple[CandidateNonparticipatingPassageObservation, ...],
) -> None:
    observations_by_buyers = {
        observation.buyer_names: observation for observation in observations
    }
    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )

    for buyer_labels in (("D",), ("B", "D")):
        observation = observations_by_buyers[buyer_labels]
        nonparticipating_names = visit_keys_to_vehicle_names(
            observation.nonparticipating_visit_keys
        )
        assert nonparticipating_names == ("C",), (
            f"candidate {buyer_labels!r}: nonparticipating visits "
            f"{nonparticipating_names!r}, expected ('C',)"
        )
        assert len(observation.nonparticipating_visit_keys) == 1
        c_visit_key = observation.nonparticipating_visit_keys[0]

        local_result = find_local_virtual_result_by_buyers(
            node_local_result,
            buyer_labels,
        )
        for record in local_result.required_passage_records:
            assert record.visit_key != c_visit_key, (
                f"candidate {buyer_labels!r}: C found in required_passage_records"
            )
        for timestep_result in local_result.timestep_results:
            assert (
                c_visit_key
                not in timestep_result.newly_recorded_required_passage_visit_keys
            ), (
                f"candidate {buyer_labels!r}: C found in "
                "newly_recorded_required_passage_visit_keys"
            )

        assert len(observation.nonparticipating_visit_observations) == 1
        c_binding_observation = observation.nonparticipating_visit_observations[0]
        assert c_binding_observation.appearance_count in (0, 1), (
            f"candidate {buyer_labels!r}: C binding passage appearance_count="
            f"{c_binding_observation.appearance_count}, expected 0 or 1"
        )


def print_nonparticipating_candidate_passage_observation_report(
    observations: tuple[CandidateNonparticipatingPassageObservation, ...],
) -> None:
    print()
    print("23. Nonparticipating candidate-passage observation")
    candidates_with_c_observed: list[tuple[str, ...]] = []
    candidates_with_c_unobserved: list[tuple[str, ...]] = []

    for observation in observations:
        print(f"   candidate buyers_sorted = {observation.buyer_names}")
        print(
            f"   nonparticipating VisitKey count = "
            f"{len(observation.nonparticipating_visit_keys)}"
        )
        if len(observation.nonparticipating_visit_keys) == 0:
            print()
            continue

        print(
            f"   nonparticipating VisitKeys = {observation.nonparticipating_visit_keys}"
        )
        print(f"   resolved = {observation.resolved}")
        print(f"   stop_reason = {observation.stop_reason}")
        print(f"   final_offset = {observation.final_offset}")
        print(f"   final_virtual_timestep = {observation.final_virtual_timestep}")
        print(
            f"   simulated_timestep_count = {observation.simulated_timestep_count}"
        )
        print(
            f"   configured_horizon_steps = {observation.configured_horizon_steps}"
        )
        print("   timestep binding-transfer rows:")
        for row in observation.timestep_rows:
            transferred_names = visit_keys_to_vehicle_names(
                row.transferred_binding_visit_keys
            )
            newly_required_names = visit_keys_to_vehicle_names(
                row.newly_recorded_required_passage_visit_keys
            )
            print(
                f"     offset={row.offset}, virtual_timestep={row.virtual_timestep}, "
                f"transferred_binding_visit_keys={row.transferred_binding_visit_keys} "
                f"(names={transferred_names}), "
                f"newly_recorded_required_passage_visit_keys="
                f"{row.newly_recorded_required_passage_visit_keys} "
                f"(names={newly_required_names}), "
                f"required_passages_complete_after_node_passage="
                f"{row.required_passages_complete_after_node_passage}, "
                f"calculation_finished_after_timestep_end="
                f"{row.calculation_finished_after_timestep_end}, "
                f"resolved_after_timestep_end={row.resolved_after_timestep_end}"
            )

        for np_observation in observation.nonparticipating_visit_observations:
            vehicle_name = np_observation.visit_key[0]
            print(f"   nonparticipating visit {np_observation.visit_key}:")
            print(f"     binding passage appearance_count = {np_observation.appearance_count}")
            print(f"     first_offset = {np_observation.first_offset}")
            print(
                f"     first_virtual_timestep = {np_observation.first_virtual_timestep}"
            )
            print(
                f"     not in required_passage_records = "
                f"{observation.c_not_in_required_passage_records}"
            )
            print(
                f"     never in newly_recorded_required_passage_visit_keys = "
                f"{observation.c_never_in_newly_recorded_required_passage_keys}"
            )
            if np_observation.observed_before_stop:
                print(
                    f"     passage status before stop: observed "
                    f"(binding passage at offset={np_observation.first_offset}, "
                    f"virtual_timestep={np_observation.first_virtual_timestep})"
                )
            else:
                print(
                    "     passage status before stop: not observed before "
                    "current local calculation stopped"
                )
                print(
                    f"     remaining_allowed_offset_count = "
                    f"{np_observation.remaining_allowed_offset_count_if_unobserved}"
                )

        if observation.buyer_names in (("D",), ("B", "D")):
            c_observation = observation.nonparticipating_visit_observations[0]
            if c_observation.observed_before_stop:
                candidates_with_c_observed.append(observation.buyer_names)
            else:
                candidates_with_c_unobserved.append(observation.buyer_names)
        print()

    print(
        "   candidates_with_C_observed_before_stop = "
        f"{candidates_with_c_observed}"
    )
    print(
        "   candidates_with_C_unobserved_before_stop = "
        f"{candidates_with_c_unobserved}"
    )
    print()
    print("24. Nonparticipating observation asserts: PASS")


def print_economic_infeasibility_debug(
    node_economic_result,
    node_local_result,
) -> None:
    print("   Economic infeasibility debug (all local candidates):")
    for local_result in node_local_result.candidate_local_virtual_calculation_results:
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        print(f"     candidate {buyer_names}: resolved={local_result.resolved}")
    print("   Economic evaluation records (resolved only):")
    if len(node_economic_result.candidate_economic_evaluation_results) == 0:
        print("     (no resolved economic records)")
    for economic_result in node_economic_result.candidate_economic_evaluation_results:
        local_result = economic_result.candidate_local_virtual_calculation_result
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        print(f"     candidate {buyer_names}:")
        print(f"       total_buyer_value_G = {economic_result.total_buyer_value_G}")
        print(
            f"       total_required_compensation_R = "
            f"{economic_result.total_required_compensation_R}"
        )
        print(f"       surplus = {economic_result.surplus}")
        print(
            f"       economically_feasible = {economic_result.economically_feasible}"
        )
        print(
            f"       infeasibility_reasons = {economic_result.infeasibility_reasons}"
        )
        for buyer_record in economic_result.buyer_economic_records:
            print(f"       buyer {buyer_record.vehicle_name}:")
            print(
                f"         baseline_passage={buyer_record.baseline_passage_timestep}, "
                f"candidate_passage={buyer_record.candidate_passage_timestep}"
            )
            print(
                f"         expected_time_saving_timesteps="
                f"{buyer_record.expected_time_saving_timesteps}"
            )
            print(
                f"         declared_vot_per_second="
                f"{buyer_record.declared_vot_per_second}"
            )
            print(f"         gross_time_value_G_b={buyer_record.gross_time_value_G_b}")
        for seller_record in economic_result.seller_economic_records:
            print(f"       seller {seller_record.vehicle_name}:")
            print(
                f"         baseline_passage={seller_record.baseline_passage_timestep}, "
                f"candidate_passage={seller_record.candidate_passage_timestep}"
            )
            print(
                f"         expected_waiting_increase_timesteps="
                f"{seller_record.expected_waiting_increase_timesteps}"
            )
            print(
                f"         required_compensation_R_s="
                f"{seller_record.required_compensation_R_s}"
            )


def assert_stage2_driver_results(
    driver_result,
    pipeline: DriverPipelineTrace,
    world: World,
) -> None:
    assert driver_result is not None
    assert pipeline.atomic_apply_set_result is not None

    candidate_visit_set_result = pipeline.candidate_visit_set_result
    node_candidate_result = junction_node_result(
        candidate_visit_set_result.node_candidate_set_results
    )
    right_of_entry_node = junction_node_result(
        pipeline.right_of_entry_selection_result.node_selection_results
    )
    assert right_of_entry_node.right_of_entry_visit_key is not None
    assert right_of_entry_node.right_of_entry_visit_key[0] == "A"

    candidate_visits = node_candidate_result.candidate_visits
    assert len(candidate_visits) == 4, (
        f"candidate_visits count={len(candidate_visits)}, "
        f"names={[visit.visit_key[0] for visit in candidate_visits]}, "
        f"build_status={node_candidate_result.build_status}"
    )
    candidate_vehicle_names = [visit.visit_key[0] for visit in candidate_visits]
    assert candidate_vehicle_names == ["A", "B", "C", "D"]

    node_concrete_result = junction_node_result(
        pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )
    concrete_sets = node_concrete_result.concrete_buyer_candidate_sets
    assert len(concrete_sets) == 3
    concrete_labels = {
        visit_keys_to_vehicle_names(concrete_set.buyers_sorted)
        for concrete_set in concrete_sets
    }
    assert concrete_labels == set(EXPECTED_CONCRETE_BUYER_LABELS)

    node_fifo_result = junction_node_result(
        pipeline.fifo_inspection_set_result.node_fifo_inspection_results
    )
    fifo_results = node_fifo_result.candidate_fifo_inspection_results
    assert len(fifo_results) == 3
    assert all(
        fifo_result.preserves_inlink_fifo is True for fifo_result in fifo_results
    )

    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    trade_d = find_trade_rank_result_by_buyers(node_trade_rank_result, ("D",))
    assert visit_keys_to_vehicle_names(trade_d.buyers_sorted) == ("D",)
    assert visit_keys_to_vehicle_names(trade_d.sellers_sorted) == ("A", "B")
    assert visit_keys_to_vehicle_names(trade_d.nonparticipating_visits_sorted) == ("C",)

    trade_bd = find_trade_rank_result_by_buyers(node_trade_rank_result, ("B", "D"))
    assert visit_keys_to_vehicle_names(trade_bd.buyers_sorted) == ("B", "D")
    assert visit_keys_to_vehicle_names(trade_bd.sellers_sorted) == ("A",)
    assert visit_keys_to_vehicle_names(trade_bd.nonparticipating_visits_sorted) == ("C",)

    trade_b = find_trade_rank_result_by_buyers(node_trade_rank_result, ("B",))
    assert visit_keys_to_vehicle_names(trade_b.buyers_sorted) == ("B",)
    assert visit_keys_to_vehicle_names(trade_b.sellers_sorted) == ("A",)

    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    local_results = node_local_result.candidate_local_virtual_calculation_results
    assert len(local_results) == 3
    resolved_count = sum(1 for local_result in local_results if local_result.resolved)
    unresolved_count = len(local_results) - resolved_count
    assert resolved_count >= 1, (
        f"resolved_count={resolved_count}, unresolved_count={unresolved_count}; "
        "inspect local virtual stop_reason output"
    )

    node_economic_result = junction_node_result(
        pipeline.economic_evaluation_set_result.node_economic_evaluation_results
    )
    feasible_results = [
        economic_result
        for economic_result in node_economic_result.candidate_economic_evaluation_results
        if economic_result.economically_feasible
    ]
    if len(feasible_results) == 0:
        print_economic_infeasibility_debug(node_economic_result, node_local_result)
    assert len(feasible_results) >= 1, (
        "No economically feasible candidate; see economic debug output above"
    )

    node_selection_result = junction_node_result(
        pipeline.candidate_selection_set_result.node_candidate_selection_results
    )
    assert (
        node_selection_result.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    )
    assert node_selection_result.selected_candidate_economic_result is not None

    node_payment_result = junction_node_result(
        pipeline.payment_and_compensation_set_result.node_payment_and_compensation_results
    )
    assert node_payment_result.selected_candidate_economic_result is not None

    node_final_rank_result = junction_node_result(
        pipeline.final_rank_set_result.node_final_rank_results
    )
    assert (
        node_final_rank_result.final_rank_status
        is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS
    )
    assert pipeline.final_consistency_validation_set_result is not None
    assert pipeline.atomic_apply_set_result is not None
    assert world.order_control_tvt_driver_started_timestep == world.T


def print_stage2_report(
    world: World,
    pipeline: DriverPipelineTrace,
    stage2_seconds: float,
    timings: dict[str, float],
) -> None:
    candidate_visit_set_result = pipeline.candidate_visit_set_result
    node_candidate_result = junction_node_result(
        candidate_visit_set_result.node_candidate_set_results
    )
    right_of_entry_node = junction_node_result(
        pipeline.right_of_entry_selection_result.node_selection_results
    )
    node_concrete_result = junction_node_result(
        pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )
    node_fifo_result = junction_node_result(
        pipeline.fifo_inspection_set_result.node_fifo_inspection_results
    )
    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    node_economic_result = junction_node_result(
        pipeline.economic_evaluation_set_result.node_economic_evaluation_results
    )
    node_selection_result = junction_node_result(
        pipeline.candidate_selection_set_result.node_candidate_selection_results
    )
    node_payment_result = junction_node_result(
        pipeline.payment_and_compensation_set_result.node_payment_and_compensation_results
    )
    node_final_rank_result = junction_node_result(
        pipeline.final_rank_set_result.node_final_rank_results
    )

    print()
    print("=" * 72)
    print("TVT-MP single-decision driver diagnostic (stage 2)")
    print("=" * 72)
    print()
    print("10. TVT-MP driver settings")
    print(f"   world.T = {world.T}")
    print(
        f"   order_control_tvt_baseline_horizon_steps = "
        f"{world.order_control_tvt_baseline_horizon_steps}"
    )
    print(
        f"   order_control_tvt_max_candidate_visit_count = "
        f"{world.order_control_tvt_max_candidate_visit_count}"
    )
    print(
        f"   order_control_tvt_evaluation_end_timestep = "
        f"{world.order_control_tvt_evaluation_end_timestep}"
    )
    print(
        f"   order_control_tvt_driver_started_timestep = "
        f"{world.order_control_tvt_driver_started_timestep}"
    )
    for name in ("A", "B", "C", "D"):
        vehicle = world.VEHICLES[name]
        print(
            f"   {name} vot_declared={vehicle.vot_declared}, "
            f"vot_true={vehicle.vot_true}, "
            f"participates={vehicle.participates_in_order_exchange}"
        )
    print()
    print("11. Right-of-entry and candidate visits")
    print(f"   right_of_entry_visit_key = {right_of_entry_node.right_of_entry_visit_key}")
    print(f"   candidate_visit_count = {len(node_candidate_result.candidate_visits)}")
    for visit in node_candidate_result.candidate_visits:
        print(f"   candidate visit {visit.visit_key}")
    print()
    print("12. Concrete buyer candidates")
    for concrete_set in node_concrete_result.concrete_buyer_candidate_sets:
        print(f"   buyers_sorted = {visit_keys_to_vehicle_names(concrete_set.buyers_sorted)}")
    print()
    print("13. FIFO inspection")
    fifo_true_count = 0
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        if fifo_result.preserves_inlink_fifo:
            fifo_true_count += 1
        buyer_names = visit_keys_to_vehicle_names(
            fifo_result.general_trade_rank_result.buyers_sorted
        )
        print(
            f"   {buyer_names}: preserves_inlink_fifo="
            f"{fifo_result.preserves_inlink_fifo}"
        )
    print(f"   fifo_true_count = {fifo_true_count}")
    print()
    print("14. General trade-rank roles")
    for expected_buyers in EXPECTED_CONCRETE_BUYER_LABELS:
        trade_rank_result = find_trade_rank_result_by_buyers(
            node_trade_rank_result,
            expected_buyers,
        )
        print(f"   candidate {expected_buyers}:")
        print(
            f"     buyers_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.buyers_sorted)}"
        )
        print(
            f"     sellers_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.sellers_sorted)}"
        )
        print(
            f"     nonparticipating_visits_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.nonparticipating_visits_sorted)}"
        )
        print(
            f"     trade_scope = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.trade_scope)}"
        )
        print(
            f"     trade_order = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.trade_order)}"
        )
    print()
    print("15. Local virtual-calculation results")
    resolved_count = 0
    for expected_buyers in EXPECTED_CONCRETE_BUYER_LABELS:
        local_result = find_local_virtual_result_by_buyers(
            node_local_result,
            expected_buyers,
        )
        if local_result.resolved:
            resolved_count += 1
        print(f"   candidate {expected_buyers}:")
        print(f"     resolved = {local_result.resolved}")
        print(f"     stop_reason = {local_result.stop_reason}")
        print(f"     unresolved_reasons = {local_result.unresolved_reasons}")
        print(f"     final_offset = {local_result.final_offset}")
        print(
            f"     simulated_timestep_count = {local_result.simulated_timestep_count}"
        )
    print(f"   resolved_count = {resolved_count}")
    print(
        f"   unresolved_count = "
        f"{len(node_local_result.candidate_local_virtual_calculation_results) - resolved_count}"
    )
    print()
    print("16. Economic evaluation")
    for expected_buyers in EXPECTED_CONCRETE_BUYER_LABELS:
        economic_result = find_economic_result_by_buyers(
            node_economic_result,
            expected_buyers,
        )
        print(f"   candidate {expected_buyers}:")
        if economic_result is None:
            print("     (not evaluated: unresolved or skipped)")
            local_result = find_local_virtual_result_by_buyers(
                node_local_result,
                expected_buyers,
            )
            print(f"     local resolved = {local_result.resolved}")
            continue
        print(f"     total_buyer_value_G = {economic_result.total_buyer_value_G}")
        print(
            f"     total_required_compensation_R = "
            f"{economic_result.total_required_compensation_R}"
        )
        print(f"     surplus = {economic_result.surplus}")
        print(f"     economically_feasible = {economic_result.economically_feasible}")
        print(f"     infeasibility_reasons = {economic_result.infeasibility_reasons}")
        for buyer_record in economic_result.buyer_economic_records:
            print(f"     buyer {buyer_record.vehicle_name}:")
            print(
                f"       baseline_passage={buyer_record.baseline_passage_timestep}, "
                f"candidate_passage={buyer_record.candidate_passage_timestep}"
            )
            print(
                f"       expected_time_saving_timesteps="
                f"{buyer_record.expected_time_saving_timesteps}"
            )
            print(
                f"       declared_vot_per_second="
                f"{buyer_record.declared_vot_per_second}"
            )
            print(f"       gross_time_value_G_b={buyer_record.gross_time_value_G_b}")
        for seller_record in economic_result.seller_economic_records:
            print(f"     seller {seller_record.vehicle_name}:")
            print(
                f"       baseline_passage={seller_record.baseline_passage_timestep}, "
                f"candidate_passage={seller_record.candidate_passage_timestep}"
            )
            print(
                f"       expected_waiting_increase_timesteps="
                f"{seller_record.expected_waiting_increase_timesteps}"
            )
            print(
                f"       required_compensation_R_s="
                f"{seller_record.required_compensation_R_s}"
            )
    print()
    print("17. Candidate selection")
    print(f"   selection_status = {node_selection_result.selection_status}")
    selected = node_selection_result.selected_candidate_economic_result
    if selected is not None:
        selected_buyers = visit_keys_to_vehicle_names(
            selected.candidate_local_virtual_calculation_result.concrete_buyer_candidate_set.buyers_sorted
        )
        print(f"   selected buyers_sorted = {selected_buyers}")
        print(f"   selected surplus = {selected.surplus}")
    print()
    print("18. Payment and compensation")
    print(
        f"   payment_and_compensation_status = "
        f"{node_payment_result.payment_and_compensation_status}"
    )
    print(f"   buyer_payment_record_count = {len(node_payment_result.buyer_payment_records)}")
    print(
        f"   seller_compensation_record_count = "
        f"{len(node_payment_result.seller_compensation_records)}"
    )
    print()
    print("19. Final rank and validation")
    print(f"   final_rank_status = {node_final_rank_result.final_rank_status}")
    print(f"   final_rank_visit_count = {len(node_final_rank_result.final_rank_visits)}")
    print("   final_consistency_validation_set_result present = True")
    print()
    print("20. Atomic apply")
    print("   atomic_apply_set_result present = True")
    print()
    print("21. Stage 2 timings (seconds)")
    print(f"   stage2_run_tvt_mp_driver = {stage2_seconds:.4f}")
    print(f"   world_prepare = {timings['world_prepare']:.4f}")
    print(f"   stage1_baseline_fork = {timings['baseline_fork']:.4f}")
    print(f"   total = {timings['total']:.4f}")
    print()
    print("22. Stage 2 all asserts: PASS")
    print("=" * 72)


def format_passage_order(snapshots_by_name: dict[str, dict]) -> list[str]:
    items = []
    for name in ("A", "B", "C", "D"):
        snap = snapshots_by_name[name]
        items.append((name, snap["baseline_passage_timestep"]))
    items.sort(key=lambda pair: pair[1])
    return [f"{name}@{ts}" for name, ts in items]


def print_world_prepare_timing_breakdown(
    breakdown: WorldPrepareTimingBreakdown,
    timings: dict[str, float],
) -> None:
    build = breakdown.build_diagnostic_world
    print()
    print("9. World prepare timing breakdown (seconds)")
    print(f"   build_diagnostic_world (total) = {build.total_seconds:.4f}")
    print(f"     World constructor = {build.world_constructor_seconds:.4f}")
    print(f"     Node and Link add = {build.add_nodes_links_seconds:.4f}")
    print(f"     prepare_network (total) = {build.prepare_network_total_seconds:.4f}")
    print(f"       finalize_scenario = {build.finalize_scenario_seconds:.4f}")
    print(f"       all link.update = {build.link_update_seconds:.4f}")
    print(
        f"   add_diagnostic_vehicles = "
        f"{breakdown.add_diagnostic_vehicles_seconds:.4f}"
    )
    print(
        f"   advance_all_vehicles = "
        f"{breakdown.advance_all_vehicles_seconds:.4f}"
    )
    for vehicle_name in ("A", "B", "C", "D"):
        metrics = breakdown.advance_by_vehicle[vehicle_name]
        print(
            f"     advance_until_on_inlink {vehicle_name} = "
            f"{metrics.elapsed_seconds:.4f} "
            f"(exec_simulation calls={metrics.exec_simulation_call_count}, "
            f"T {metrics.world_t_at_start} -> {metrics.world_t_at_end})"
        )
    print(
        f"   open_junction_capacities_for_baseline = "
        f"{breakdown.open_junction_capacities_seconds:.4f}"
    )
    print(
        f"   snapshot_placement (total) = "
        f"{breakdown.snapshot_placement_seconds:.4f}"
    )
    print(
        f"   assert_capacity_ready_for_fork = "
        f"{breakdown.assert_capacity_ready_seconds:.4f}"
    )
    print(f"   world_prepare (overall) = {timings['world_prepare']:.4f}")
    print(f"   baseline_fork = {timings['baseline_fork']:.4f}")
    print(f"   total = {timings['total']:.4f}")
    print()


def print_report(
    *,
    world: World,
    vehicles_by_name: dict,
    pre_snapshot_rows: list[dict],
    fork_result,
    baseline_rows: list[dict],
    arrival_order: list[str],
    passage_order: list[str],
    timings: dict[str, float],
    prepare_breakdown: WorldPrepareTimingBreakdown,
) -> None:
    print("=" * 72)
    print("TVT-MP single-decision baseline fork diagnostic (stage 1)")
    print("=" * 72)
    print()
    print("1. Settings")
    print(f"   snapshot_timestep_T = {SNAPSHOT_TIMESTEP_T}")
    print(f"   baseline_horizon_steps = {BASELINE_HORIZON_STEPS}")
    print(f"   link length = {LINK_LENGTH}, u = {FREE_FLOW_SPEED}, lanes = {NUMBER_OF_LANES}")
    print(f"   hard_deterministic_mode = {world.hard_deterministic_mode}")
    print()
    print("2. World scale")
    print(f"   nodes = {len(world.NODES)}, links = {len(world.LINKS)}")
    print(
        f"   vehicles = {len(world.VEHICLES)}, TMAX = {world.TMAX}, "
        f"TSIZE = {world.TSIZE}"
    )
    print()
    print("3. Per-vehicle snapshot placement")
    for row in pre_snapshot_rows:
        print(f"   {row}")
    print()
    print("4. Per-vehicle baseline collector results")
    for row in baseline_rows:
        print(f"   {row}")
    print()
    print("5. Arrival order (by name)")
    print(f"   {' < '.join(arrival_order)}")
    print()
    print("6. Passage order (by timestep)")
    print(f"   {', '.join(passage_order)}")
    print()
    print("7. Timings (seconds)")
    print(f"   world_prepare = {timings['world_prepare']:.4f}")
    print(f"   baseline_fork = {timings['baseline_fork']:.4f}")
    if "stage2_driver" in timings:
        print(f"   stage2_run_tvt_mp_driver = {timings['stage2_driver']:.4f}")
    print(f"   total = {timings['total']:.4f}")
    print()
    print("8. All asserts: PASS")
    print_world_prepare_timing_breakdown(prepare_breakdown, timings)
    print("=" * 72)


# --- Stage 3: separate World. C is skipped only by outlink entry space. ---

# Baseline fork: Node.update runs flow_capacity_update then Stage3JunctionFlowHold
# (zeros flow while W.T < release_timestep), then Node.transfer records passage at
# W.T. release=15 allows transfer at T=15 (same as candidate vt 15). release=16
# still blocks at T=15 and opens at T=16 so buyer D baseline passage > 15.
STAGE3_BASELINE_FLOW_RELEASE_TIMESTEP = 16
STAGE3_APPROACH_HOLD_TIMESTEP = 100000
STAGE3_DECLARED_VOT_BY_VEHICLE = {
    "A": STAGE2_DECLARED_VOT_BY_VEHICLE["A"],
    "B": STAGE2_DECLARED_VOT_BY_VEHICLE["B"],
    "C": STAGE2_DECLARED_VOT_BY_VEHICLE["C"],
    "D": STAGE2_DECLARED_VOT_BY_VEHICLE["D"],
}
STAGE3_VOT_TRUE_BY_VEHICLE = {
    "A": STAGE2_VOT_TRUE_BY_VEHICLE["A"],
    "B": STAGE2_VOT_TRUE_BY_VEHICLE["B"],
    "C": STAGE2_VOT_TRUE_BY_VEHICLE["C"],
    "D": STAGE2_VOT_TRUE_BY_VEHICLE["D"],
}

STAGE3_VEHICLE_SPECS = (
    {
        "name": "A",
        "origin": "orig_roe",
        "inlink": "in_roe",
        "destination": "dest_c",
        "outlink": "out_c",
        "participates": True,
        "merge_priority": 4.0,
        "snapshot_x": 160.0,
    },
    {
        "name": "B",
        "origin": "orig_aux",
        "inlink": "in_aux",
        "destination": "dest_b",
        "outlink": "out_b",
        "participates": True,
        "merge_priority": 3.0,
        "snapshot_x": 140.0,
    },
    {
        "name": "C",
        "origin": "orig_np",
        "inlink": "in_np",
        "destination": "dest_c",
        "outlink": "out_c",
        "participates": False,
        "merge_priority": 2.0,
        "snapshot_x": 120.0,
    },
    {
        "name": "D",
        "origin": "orig_buy",
        "inlink": "in_buy",
        "destination": "dest_d",
        "outlink": "out_d",
        "participates": True,
        "merge_priority": 1.0,
        "snapshot_x": 100.0,
    },
)

STAGE3_INLINK_NAMES = ("in_roe", "in_aux", "in_np", "in_buy")
STAGE3_OUTLINK_NAMES = ("out_d", "out_c", "out_b")
STAGE3_LINK_NAMES = STAGE3_INLINK_NAMES + STAGE3_OUTLINK_NAMES

# Candidate-local virtual time refills each inlink once per offset>0 when
# capacity_out_remain < DELTAN * number_of_lanes (here 1), adding
# capacity_out * DELTAT. Snapshot sets capacity_out_remain=0; offset 0 scans
# before any refill. Scan at offset k>=1 sees k refills while remain stays
# below 1. Offsets 2..4 need remain < DELTAN; offset 5 needs remain >= DELTAN:
# 4 * cap < 1 and 5 * cap >= 1 => cap = 0.2.
STAGE3_APPROACH_INLINK_CAPACITY_OUT = 0.2
STAGE3_APPROACH_INLINK_CAPACITY_IN = 10000.0
# While inlink outflow capacity is held, local advance still runs at x=length and
# leaves move_remain=20. Binding transfer maps that to x=20 on out_c, which
# clears default entry space (threshold 5). jam_density 0.05 => delta_per_lane
# 20 so x=20 does not free a second lane (needs x > 20).
STAGE3_OUT_C_JAM_DENSITY = 0.05


class Stage3JunctionFlowHold:
    """Delay baseline node passage without adding a fifth vehicle.

    Node.update calls this during the baseline fork. Candidate-local
    calculation does not call Node.update, so the local completion scan
    keeps the open flow prepared on the real World.
    """

    def __init__(self) -> None:
        self.release_timestep = STAGE3_APPROACH_HOLD_TIMESTEP

    def apply(self, node) -> None:
        if node.W.T < self.release_timestep:
            node.flow_capacity_remain = 0.0


def build_stage3_world(
    build_timings: BuildDiagnosticWorldTimings,
) -> tuple[World, Stage3JunctionFlowHold]:
    build_start = time.perf_counter()

    constructor_start = time.perf_counter()
    world = World(
        name="tvt_mp_stage3_outlink_entry_space_diagnostic",
        deltan=1,
        tmax=WORLD_TMAX,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    build_timings.world_constructor_seconds = (
        time.perf_counter() - constructor_start
    )

    nodes_links_start = time.perf_counter()
    world.addNode("orig_roe", 0, 0)
    world.addNode("orig_aux", 0, 1)
    world.addNode("orig_np", 0, 2)
    world.addNode("orig_buy", 0, 3)
    world.addNode(
        JUNCTION_NODE_NAME,
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
    )
    world.addNode("dest_d", 2, 0)
    world.addNode("dest_c", 2, 1)
    world.addNode("dest_b", 2, 2)

    link_kwargs = {
        "length": LINK_LENGTH,
        "free_flow_speed": FREE_FLOW_SPEED,
        "number_of_lanes": NUMBER_OF_LANES,
    }
    for spec in STAGE3_VEHICLE_SPECS:
        world.addLink(
            spec["inlink"],
            spec["origin"],
            JUNCTION_NODE_NAME,
            merge_priority=spec["merge_priority"],
            **link_kwargs,
        )
    world.addLink("out_d", JUNCTION_NODE_NAME, "dest_d", **link_kwargs)
    world.addLink(
        "out_c",
        JUNCTION_NODE_NAME,
        "dest_c",
        jam_density=STAGE3_OUT_C_JAM_DENSITY,
        **link_kwargs,
    )
    world.addLink("out_b", JUNCTION_NODE_NAME, "dest_b", **link_kwargs)
    build_timings.add_nodes_links_seconds = (
        time.perf_counter() - nodes_links_start
    )

    prepare_network_start = time.perf_counter()
    if not getattr(world, "finalized", 0):
        finalize_start = time.perf_counter()
        world.finalize_scenario()
        build_timings.finalize_scenario_seconds = (
            time.perf_counter() - finalize_start
        )
    else:
        build_timings.finalize_scenario_seconds = 0.0

    link_update_start = time.perf_counter()
    for link in world.LINKS:
        link.update()
    build_timings.link_update_seconds = time.perf_counter() - link_update_start
    build_timings.prepare_network_total_seconds = (
        time.perf_counter() - prepare_network_start
    )

    flow_hold = Stage3JunctionFlowHold()
    junction = world.get_node(JUNCTION_NODE_NAME)
    junction.user_function = flow_hold.apply

    build_timings.total_seconds = time.perf_counter() - build_start
    return world, flow_hold


def add_stage3_vehicles(world: World) -> dict[str, object]:
    vehicles_by_name: dict[str, object] = {}
    for spec in STAGE3_VEHICLE_SPECS:
        vehicle_name = spec["name"]
        vehicle = world.addVehicle(
            spec["origin"],
            spec["destination"],
            0,
            name=vehicle_name,
            links_prefer=[spec["outlink"]],
            participates_in_order_exchange=spec["participates"],
            vot_declared=STAGE3_DECLARED_VOT_BY_VEHICLE[vehicle_name],
            vot_true=STAGE3_VOT_TRUE_BY_VEHICLE[vehicle_name],
        )
        vehicles_by_name[vehicle_name] = vehicle
    return vehicles_by_name


def advance_stage3_until_natural_outlink_choice(
    world: World,
    vehicles_by_name: dict[str, object],
) -> None:
    """Run the real World until each vehicle has chosen its outlink.

    Route choice happens when the vehicle reaches the junction. This loop
    stops before the next node transfer by holding flow, then the caller
    moves each vehicle back to the snapshot position. route_next_link is
    left as the simulator chose it.
    """
    junction = world.get_node(JUNCTION_NODE_NAME)
    remaining_names = [spec["name"] for spec in STAGE3_VEHICLE_SPECS]
    step_count = 0
    step_limit = WORLD_TMAX

    while len(remaining_names) > 0:
        if step_count >= step_limit:
            raise RuntimeError(
                "Stage 3 vehicles did not reach the junction with the "
                f"intended outlink. Still waiting: {remaining_names}."
            )
        if not world.check_simulation_ongoing():
            raise RuntimeError(
                "Stage 3 approach ended before every vehicle chose an "
                f"outlink. Still waiting: {remaining_names}."
            )
        world.exec_simulation(duration_t2=world.DELTAT)
        step_count += 1

        still_waiting = []
        for vehicle_name in remaining_names:
            vehicle = vehicles_by_name[vehicle_name]
            spec = None
            for candidate_spec in STAGE3_VEHICLE_SPECS:
                if candidate_spec["name"] == vehicle_name:
                    spec = candidate_spec
            inlink = world.get_link(spec["inlink"])
            outlink = world.get_link(spec["outlink"])
            if vehicle not in junction.incoming_vehicles:
                still_waiting.append(vehicle_name)
                continue
            if vehicle.link is not inlink:
                actual_link = None
                if vehicle.link is not None:
                    actual_link = vehicle.link.name
                raise RuntimeError(
                    f"Stage 3 vehicle {vehicle_name} left {spec['inlink']} "
                    f"before snapshot placement. Current link: {actual_link}."
                )
            chosen_outlink = vehicle.route_next_link
            chosen_name = None
            if chosen_outlink is not None:
                chosen_name = chosen_outlink.name
            if chosen_outlink is not outlink:
                raise RuntimeError(
                    f"Stage 3 vehicle {vehicle_name} chose outlink "
                    f"{chosen_name}, expected {spec['outlink']}."
                )
        remaining_names = still_waiting


def place_stage3_vehicle_at_common_snapshot(
    world: World,
    vehicle,
    spec: dict,
) -> None:
    """Return one naturally routed vehicle to its Stage 3 not-yet-arrived x."""
    inlink = world.get_link(spec["inlink"])
    outlink = world.get_link(spec["outlink"])
    junction = world.get_node(JUNCTION_NODE_NAME)
    snapshot_x = spec["snapshot_x"]

    vehicle.link = inlink
    vehicle.state = "run"
    vehicle.x = snapshot_x
    vehicle.link_arrival_time = float((SNAPSHOT_TIMESTEP_T - 1) * world.DELTAT)
    ensure_single_vehicle_on_inlink(inlink, vehicle)

    if vehicle in junction.incoming_vehicles:
        junction.incoming_vehicles.remove(vehicle)

    current_visit = vehicle.order_control_current_visit
    if current_visit is None:
        raise RuntimeError(
            f"{vehicle.name}: expected a natural current visit before "
            "Stage 3 snapshot placement."
        )
    current_visit["arrival_time"] = None
    current_visit["arrival_tiebreaker"] = None
    if JUNCTION_NODE_NAME in vehicle.order_control_node_arrival_times:
        del vehicle.order_control_node_arrival_times[JUNCTION_NODE_NAME]
    if JUNCTION_NODE_NAME in vehicle.order_control_node_arrival_tiebreakers:
        del vehicle.order_control_node_arrival_tiebreakers[JUNCTION_NODE_NAME]

    align_free_flow_kinematics_for_snapshot(vehicle, inlink)

    if vehicle.route_next_link is not outlink:
        actual_name = None
        if vehicle.route_next_link is not None:
            actual_name = vehicle.route_next_link.name
        raise RuntimeError(
            f"{vehicle.name}: snapshot route_next_link is {actual_name}, "
            f"expected the naturally chosen {spec['outlink']}."
        )
    if vehicle.x >= inlink.length:
        raise RuntimeError(
            f"{vehicle.name}: snapshot x={vehicle.x} is not before "
            f"{inlink.length}."
        )


def rewind_stage3_link_cumulative_counts_to_snapshot(world: World) -> None:
    """Drop approach-step cumulative counts that sit past snapshot T.

    Link.update appends one cum_arrival and cum_departure entry per
    timestep. Virtual time extends a short list up to T, but it does not
    shorten a list left long by the route-choice approach.
    """
    expected_length = world.T + 1
    for link in world.LINKS:
        if len(link.cum_arrival) > expected_length:
            del link.cum_arrival[expected_length:]
        if len(link.cum_departure) > expected_length:
            del link.cum_departure[expected_length:]


def configure_stage3_approach_inlink_capacities(world: World) -> None:
    """Finite capacity_out on the four approach inlinks only.

    capacity_out_remain is reset to 0 so approach driving does not carry
    refilled tokens into the snapshot copied by candidate-local calculation.
    """
    for link_name in STAGE3_INLINK_NAMES:
        link = world.get_link(link_name)
        link.capacity_in = STAGE3_APPROACH_INLINK_CAPACITY_IN
        link.capacity_out = STAGE3_APPROACH_INLINK_CAPACITY_OUT
        link.capacity_in_remain = STAGE3_APPROACH_INLINK_CAPACITY_IN
        link.capacity_out_remain = 0.0


def open_stage3_capacities_for_same_scan_passage(world: World) -> None:
    """Open flow and link tokens. Keep clearance satisfied inside one scan.

    D, A, and B use three different inlinks. Clearance 0 still rejects a
    second inlink when the gap is 0. A negative clearance makes that gap
    satisfied, so the completion scan is not stopped by clearance.
    The public setter rejects a negative value, so the junction field is
    assigned directly.

    Approach inlinks use a small finite capacity_out so candidate-local
    binding waits until all four vehicles are incoming; outlinks stay open.
    """
    junction = world.get_node(JUNCTION_NODE_NAME)
    junction.flow_capacity = None
    junction.flow_capacity_remain = 1.0e10
    junction.order_control_clearance_timesteps = -1
    junction.last_order_control_inlink = None
    junction.last_order_control_entry_timestep = None

    configure_stage3_approach_inlink_capacities(world)
    for link_name in STAGE3_OUTLINK_NAMES:
        link = world.get_link(link_name)
        link.capacity_in_remain = 1.0e10
        link.capacity_out_remain = 1.0e10


def configure_stage3_driver_settings(world: World) -> None:
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = 4
    world.order_control_tvt_evaluation_end_timestep = None
    world.order_control_tvt_driver_started_timestep = None
    world.order_control_tvt_rank_states_by_node_name = {}


def stage3_candidate_visits_by_name(node_candidate_result) -> dict[str, object]:
    visits_by_name = {}
    for visit in node_candidate_result.candidate_visits:
        visits_by_name[visit.visit_key[0]] = visit
    return visits_by_name


def stage3_baseline_sort_key(visit) -> tuple:
    return (
        visit.baseline_arrival_timestep,
        visit.arrival_tiebreaker,
        visit.vehicle_id,
    )


def collect_stage3_skip_rows_for_vehicle(
    local_result,
    vehicle_name: str,
) -> list[dict]:
    rows = []
    for timestep_result in local_result.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        for skip in binding_result.temporarily_skipped_visits:
            if skip.vehicle_name != vehicle_name:
                continue
            rows.append(
                {
                    "offset": timestep_result.offset,
                    "virtual_timestep": timestep_result.virtual_timestep,
                    "visit_key": skip.binding_visit_key,
                    "skip_reason": skip.skip_reason,
                }
            )
    return rows


def stage3_vehicle_inlink_name(vehicle_name: str) -> str:
    for spec in STAGE3_VEHICLE_SPECS:
        if spec["name"] == vehicle_name:
            return spec["inlink"]
    raise KeyError(f"unknown Stage 3 vehicle {vehicle_name!r}")


def stage3_timestep_result_at_offset(local_result, offset: int):
    for timestep_result in local_result.timestep_results:
        if timestep_result.offset == offset:
            return timestep_result
    raise AssertionError(
        f"offset {offset} not found in candidate-local timestep_results"
    )


def stage3_traffic_observation_record_for_vehicle(local_result, vehicle_name: str):
    for record in local_result.traffic_observation_records:
        if record.vehicle_name == vehicle_name:
            return record
    raise AssertionError(
        f"{vehicle_name}: no traffic_observation_record in candidate-local result"
    )


def stage3_completion_timestep_result(local_result):
    """Timestep of C's last OUTLINK_ENTRY_SPACE_UNAVAILABLE skip (offset 5 / vt 15).

    Used as the economic-required completion boundary before C's binding transfer
    at offset 6 finishes the full trade_scope observation.
    """
    c_skip_rows = collect_stage3_skip_rows_for_vehicle(local_result, "C")
    if len(c_skip_rows) == 0:
        raise AssertionError("C has no temporary skips in candidate-local trace")
    entry_space_reason = (
        OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE
    )
    entry_space_rows = [
        row
        for row in c_skip_rows
        if row["skip_reason"] is entry_space_reason
    ]
    if len(entry_space_rows) == 0:
        raise AssertionError(
            "C never skipped for OUTLINK_ENTRY_SPACE_UNAVAILABLE"
        )
    completion_virtual_timestep = entry_space_rows[-1]["virtual_timestep"]
    for timestep_result in local_result.timestep_results:
        if timestep_result.virtual_timestep == completion_virtual_timestep:
            return timestep_result
    raise AssertionError(
        "completion virtual timestep not found in timestep_results"
    )


def count_stage3_skip_reason_before_virtual_timestep(
    local_result,
    vehicle_name: str,
    skip_reason,
    before_virtual_timestep: int,
) -> int:
    count = 0
    for timestep_result in local_result.timestep_results:
        if timestep_result.virtual_timestep >= before_virtual_timestep:
            continue
        for skip in timestep_result.binding_transfer_result.temporarily_skipped_visits:
            if skip.vehicle_name != vehicle_name:
                continue
            if skip.skip_reason is skip_reason:
                count += 1
    return count


def count_stage3_transferred_appearances(
    local_result,
    vehicle_name: str,
) -> int:
    appearance_count = 0
    for timestep_result in local_result.timestep_results:
        transferred_keys = (
            timestep_result.binding_transfer_result.transferred_binding_visit_keys
        )
        for visit_key in transferred_keys:
            if visit_key[0] == vehicle_name:
                appearance_count += 1
    return appearance_count


def print_stage3_economic_details(node_economic_result) -> None:
    print("   Stage 3 economic records:")
    if len(node_economic_result.candidate_economic_evaluation_results) == 0:
        print("     (no economic records)")
        return
    for economic_result in node_economic_result.candidate_economic_evaluation_results:
        local_result = economic_result.candidate_local_virtual_calculation_result
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        print(f"     candidate {buyer_names}:")
        print(f"       total_G = {economic_result.total_buyer_value_G}")
        print(f"       total_R = {economic_result.total_required_compensation_R}")
        print(f"       surplus = {economic_result.surplus}")
        print(
            f"       economically_feasible = {economic_result.economically_feasible}"
        )
        print(
            f"       infeasibility_reasons = {economic_result.infeasibility_reasons}"
        )
        for buyer_record in economic_result.buyer_economic_records:
            print(f"       buyer {buyer_record.vehicle_name}:")
            print(
                f"         baseline_passage="
                f"{buyer_record.baseline_passage_timestep}"
            )
            print(
                f"         candidate_passage="
                f"{buyer_record.candidate_passage_timestep}"
            )
            print(
                f"         expected_saving_timesteps="
                f"{buyer_record.expected_time_saving_timesteps}"
            )
            print(
                f"         declared_vot={buyer_record.declared_vot_per_second}"
            )
            print(f"         G_b={buyer_record.gross_time_value_G_b}")
        for seller_record in economic_result.seller_economic_records:
            print(f"       seller {seller_record.vehicle_name}:")
            print(
                f"         baseline_passage="
                f"{seller_record.baseline_passage_timestep}"
            )
            print(
                f"         candidate_passage="
                f"{seller_record.candidate_passage_timestep}"
            )
            print(
                f"         expected_waiting_increase_timesteps="
                f"{seller_record.expected_waiting_increase_timesteps}"
            )
            print(f"         R_s={seller_record.required_compensation_R_s}")


def assert_stage3_counterexample(
    pipeline: DriverPipelineTrace,
    world: World,
) -> None:
    node_candidate_result = junction_node_result(
        pipeline.candidate_visit_set_result.node_candidate_set_results
    )
    assert (
        node_candidate_result.build_status
        is OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )
    visits_by_name = stage3_candidate_visits_by_name(node_candidate_result)
    assert list(visits_by_name.keys()) == ["A", "B", "C", "D"] or set(
        visits_by_name.keys()
    ) == {"A", "B", "C", "D"}
    assert set(visits_by_name.keys()) == {"A", "B", "C", "D"}

    ordered_names = sorted(visits_by_name.keys(), key=lambda name: stage3_baseline_sort_key(visits_by_name[name]))
    assert ordered_names == ["A", "B", "C", "D"], (
        "Stage 3 baseline order is not A, B, C, D. "
        + ", ".join(
            (
                f"{name}: arrival={visits_by_name[name].baseline_arrival_timestep}, "
                f"tiebreaker={visits_by_name[name].arrival_tiebreaker}, "
                f"vehicle_id={visits_by_name[name].vehicle_id}"
            )
            for name in ordered_names
        )
    )

    expected_arrivals = {"A": 11, "B": 12, "C": 13, "D": 14}
    for vehicle_name, expected_arrival in expected_arrivals.items():
        visit = visits_by_name[vehicle_name]
        arrival = visit.baseline_arrival_timestep
        passage = visit.baseline_passage_timestep
        assert arrival == expected_arrival, (
            f"{vehicle_name}: baseline arrival {arrival} != {expected_arrival}"
        )
        assert passage is not None
        assert passage >= arrival + 1, (
            f"{vehicle_name}: baseline passage {passage} < arrival+1 ({arrival + 1})"
        )
    roe_passage = node_candidate_result.right_of_entry_baseline_passage_timestep
    assert roe_passage is not None
    for vehicle_name in ("A", "B", "C", "D"):
        arrival = visits_by_name[vehicle_name].baseline_arrival_timestep
        assert arrival <= roe_passage - 1, (
            f"{vehicle_name}: arrival {arrival} > RoE passage-1 ({roe_passage - 1})"
        )
    assert visits_by_name["A"].route_next_link_name == "out_c"
    assert visits_by_name["C"].route_next_link_name == "out_c"
    assert visits_by_name["B"].route_next_link_name == "out_b"
    assert visits_by_name["D"].route_next_link_name == "out_d"

    right_of_entry_node = junction_node_result(
        pipeline.right_of_entry_selection_result.node_selection_results
    )
    leading_node = junction_node_result(
        pipeline.right_of_entry_selection_result.leading_confirmation_result.node_confirmation_results
    )
    assert (
        right_of_entry_node.selection_status
        is OrderControlTvtRightOfEntrySelectionStatus.SELECTED
    )
    assert right_of_entry_node.right_of_entry_visit_key is not None
    assert right_of_entry_node.right_of_entry_visit_key[0] == "A"
    assert len(leading_node.confirmed_leading_nonparticipating_visit_keys) == 0
    remaining_window_names = visit_keys_to_vehicle_names(
        leading_node.remaining_decision_window_visit_keys
    )
    assert remaining_window_names == ("A", "B", "C", "D")
    candidate_names = [
        visit.visit_key[0] for visit in node_candidate_result.candidate_visits
    ]
    assert len(node_candidate_result.candidate_visits) == 4
    assert candidate_names == ["A", "B", "C", "D"]

    node_concrete_result = junction_node_result(
        pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )
    concrete_labels = {
        visit_keys_to_vehicle_names(concrete_set.buyers_sorted)
        for concrete_set in node_concrete_result.concrete_buyer_candidate_sets
    }
    assert concrete_labels == {("B",), ("D",), ("B", "D")}

    node_fifo_result = junction_node_result(
        pipeline.fifo_inspection_set_result.node_fifo_inspection_results
    )
    fifo_true_count = 0
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        if fifo_result.preserves_inlink_fifo is True:
            fifo_true_count += 1
    assert fifo_true_count == 3

    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    for expected_buyers in EXPECTED_CONCRETE_BUYER_LABELS:
        find_trade_rank_result_by_buyers(node_trade_rank_result, expected_buyers)
        find_fifo_result_by_buyers(node_fifo_result, expected_buyers)

    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    for expected_buyers in EXPECTED_CONCRETE_BUYER_LABELS:
        find_local_virtual_result_by_buyers(node_local_result, expected_buyers)

    trade_d = find_trade_rank_result_by_buyers(node_trade_rank_result, ("D",))
    assert visit_keys_to_vehicle_names(trade_d.buyers_sorted) == ("D",)
    assert visit_keys_to_vehicle_names(trade_d.sellers_sorted) == ("A", "B")
    assert visit_keys_to_vehicle_names(trade_d.nonparticipating_visits_sorted) == ("C",)
    assert visit_keys_to_vehicle_names(trade_d.trade_order) == ("D", "A", "C", "B")
    fifo_d = find_fifo_result_by_buyers(node_fifo_result, ("D",))
    assert fifo_d.preserves_inlink_fifo is True

    trade_bd = find_trade_rank_result_by_buyers(node_trade_rank_result, ("B", "D"))
    assert visit_keys_to_vehicle_names(trade_bd.buyers_sorted) == ("B", "D")
    assert visit_keys_to_vehicle_names(trade_bd.sellers_sorted) == ("A",)
    assert visit_keys_to_vehicle_names(trade_bd.nonparticipating_visits_sorted) == ("C",)

    local_d = find_local_virtual_result_by_buyers(node_local_result, ("D",))
    assert local_d is not None
    assert local_d.resolved is True
    assert (
        local_d.stop_reason
        is OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
    )

    required_names = []
    for record in local_d.required_passage_records:
        required_names.append(record.vehicle_name)
    assert required_names == ["D", "A", "B"] or set(required_names) == {"D", "A", "B"}
    assert set(required_names) == {"D", "A", "B"}
    assert "C" not in required_names
    candidate_passage_by_name = {
        record.vehicle_name: record.candidate_passage_timestep
        for record in local_d.required_passage_records
    }
    assert candidate_passage_by_name == {"D": 15, "A": 15, "B": 15}
    assert local_d.final_offset == 6
    assert local_d.final_virtual_timestep == 16
    assert local_d.simulated_timestep_count == 6
    assert local_d.unresolved_reasons == ()
    assert local_d.economic_required_passages_complete_offset == 5
    assert local_d.economic_required_passages_complete_virtual_timestep == 15
    assert local_d.all_trade_scope_passages_complete_offset == 6
    assert local_d.all_trade_scope_passages_complete_virtual_timestep == 16
    assert count_stage3_transferred_appearances(local_d, "C") == 1

    d_baseline_passage = visits_by_name["D"].baseline_passage_timestep
    assert d_baseline_passage > candidate_passage_by_name["D"]
    assert visits_by_name["A"].baseline_passage_timestep >= candidate_passage_by_name["A"]
    assert visits_by_name["B"].baseline_passage_timestep >= candidate_passage_by_name["B"]

    for timestep_result in local_d.timestep_results:
        newly_recorded_names = visit_keys_to_vehicle_names(
            timestep_result.newly_recorded_required_passage_visit_keys
        )
        assert "C" not in newly_recorded_names
        transferred_names = visit_keys_to_vehicle_names(
            timestep_result.binding_transfer_result.transferred_binding_visit_keys
        )
        if timestep_result.offset == 6:
            assert transferred_names == ("C",)
        else:
            assert "C" not in transferred_names

    offset_5_result = stage3_timestep_result_at_offset(local_d, 5)
    assert offset_5_result.virtual_timestep == 15
    assert offset_5_result.required_passages_complete_after_node_passage is True
    assert offset_5_result.resolved_after_timestep_end is True
    assert offset_5_result.traffic_observation_complete_after_node_passage is False
    assert offset_5_result.economic_required_first_completed_at_this_timestep is True
    assert offset_5_result.traffic_observation_first_completed_at_this_timestep is False
    assert offset_5_result.calculation_finished_after_timestep_end is False
    offset_5_transferred = visit_keys_to_vehicle_names(
        offset_5_result.binding_transfer_result.transferred_binding_visit_keys
    )
    assert offset_5_transferred == ("D", "A", "B")
    offset_5_newly_recorded = visit_keys_to_vehicle_names(
        offset_5_result.newly_recorded_required_passage_visit_keys
    )
    assert set(offset_5_newly_recorded) == {"D", "A", "B"}

    offset_6_result = stage3_timestep_result_at_offset(local_d, 6)
    assert offset_6_result.virtual_timestep == 16
    offset_6_transferred = visit_keys_to_vehicle_names(
        offset_6_result.binding_transfer_result.transferred_binding_visit_keys
    )
    assert offset_6_transferred == ("C",)
    offset_6_newly_recorded = visit_keys_to_vehicle_names(
        offset_6_result.newly_recorded_required_passage_visit_keys
    )
    assert offset_6_newly_recorded == ()
    assert offset_6_result.required_passages_complete_after_node_passage is True
    assert offset_6_result.resolved_after_timestep_end is True
    assert offset_6_result.traffic_observation_complete_after_node_passage is True
    assert offset_6_result.economic_required_first_completed_at_this_timestep is False
    assert offset_6_result.traffic_observation_first_completed_at_this_timestep is True
    assert offset_6_result.calculation_finished_after_timestep_end is True

    outlink_entry_space_reason = (
        OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE
    )
    c_traffic_d = stage3_traffic_observation_record_for_vehicle(local_d, "C")
    assert c_traffic_d.visit_key == ("C", 1)
    assert (
        c_traffic_d.trade_role
        is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING
    )
    assert (
        c_traffic_d.passage_observation_status
        is OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
    )
    assert c_traffic_d.candidate_passage_timestep == 16
    assert c_traffic_d.observed_offset == 6
    assert c_traffic_d.observed_virtual_timestep == 16
    assert c_traffic_d.baseline_passage_timestep == 17
    assert c_traffic_d.predicted_time_difference_timesteps == 1
    assert c_traffic_d.predicted_time_difference_seconds == world.DELTAT * 1
    assert c_traffic_d.predicted_signed_time_value_change == (
        world.DELTAT * 1 * STAGE3_VOT_TRUE_BY_VEHICLE["C"]
    )
    assert c_traffic_d.last_temporary_skip_reason is outlink_entry_space_reason
    assert c_traffic_d.last_temporary_skip_offset == 5
    assert c_traffic_d.horizon_exhausted is False
    assert c_traffic_d.observation_complete is True

    local_bd = find_local_virtual_result_by_buyers(node_local_result, ("B", "D"))
    assert local_bd is not None
    assert local_bd.final_offset == 6
    assert local_bd.final_virtual_timestep == 16
    assert local_bd.simulated_timestep_count == 6
    assert local_bd.economic_required_passages_complete_offset == 6
    assert local_bd.economic_required_passages_complete_virtual_timestep == 16
    assert local_bd.all_trade_scope_passages_complete_offset == 6
    assert local_bd.all_trade_scope_passages_complete_virtual_timestep == 16
    bd_required_names = {
        record.vehicle_name for record in local_bd.required_passage_records
    }
    assert bd_required_names == {"B", "D", "A"}
    assert "C" not in bd_required_names
    for timestep_result in local_bd.timestep_results:
        newly_recorded_names = visit_keys_to_vehicle_names(
            timestep_result.newly_recorded_required_passage_visit_keys
        )
        assert "C" not in newly_recorded_names
    c_traffic_bd = stage3_traffic_observation_record_for_vehicle(local_bd, "C")
    assert (
        c_traffic_bd.passage_observation_status
        is OrderControlTvtMpCandidatePassageObservationStatus.OBSERVED
    )
    assert c_traffic_bd.candidate_passage_timestep == 15
    assert c_traffic_bd.observed_offset == 5
    assert c_traffic_bd.observed_virtual_timestep == 15

    inlink_capacity_reason = (
        OrderControlTvtMpBindingVisitTemporarySkipReason.INLINK_OUTFLOW_CAPACITY_UNAVAILABLE
    )
    not_arrived_reason = (
        OrderControlTvtMpBindingVisitTemporarySkipReason.NOT_ARRIVED_AT_TARGET_NODE
    )
    economic_required_completion_result = stage3_completion_timestep_result(local_d)
    completion_virtual_timestep = (
        economic_required_completion_result.virtual_timestep
    )
    completion_offset = economic_required_completion_result.offset
    transferred_before_completion = set()
    for timestep_result in local_d.timestep_results:
        if timestep_result.virtual_timestep >= completion_virtual_timestep:
            continue
        for visit_key in (
            timestep_result.binding_transfer_result.transferred_binding_visit_keys
        ):
            transferred_before_completion.add(visit_key[0])
    arrived_before_completion = set()
    for timestep_result in local_d.timestep_results:
        if timestep_result.virtual_timestep >= completion_virtual_timestep:
            continue
        for skip in timestep_result.binding_transfer_result.temporarily_skipped_visits:
            if (
                skip.skip_reason
                is not_arrived_reason
            ):
                arrived_before_completion.add(skip.vehicle_name)
        for visit_key in (
            timestep_result.binding_transfer_result.transferred_binding_visit_keys
        ):
            arrived_before_completion.add(visit_key[0])
    for vehicle_name in ("A", "B", "C"):
        if vehicle_name in transferred_before_completion:
            continue
        assert vehicle_name in arrived_before_completion, (
            f"{vehicle_name}: expected to be arrived before completion scan "
            f"vt={completion_virtual_timestep}"
        )
        capacity_skip_count = count_stage3_skip_reason_before_virtual_timestep(
            local_d,
            vehicle_name,
            inlink_capacity_reason,
            completion_virtual_timestep,
        )
        assert capacity_skip_count >= 1, (
            f"{vehicle_name}: expected INLINK_OUTFLOW_CAPACITY_UNAVAILABLE "
            f"while arrived and unpassed before completion scan "
            f"vt={completion_virtual_timestep}, got count={capacity_skip_count}"
        )
    not_arrived_seen = False
    for timestep_result in local_d.timestep_results:
        if timestep_result.virtual_timestep >= completion_virtual_timestep:
            continue
        for skip in timestep_result.binding_transfer_result.temporarily_skipped_visits:
            if skip.skip_reason is not_arrived_reason:
                not_arrived_seen = True
                break
        if not_arrived_seen:
            break
    assert not_arrived_seen, (
        "expected NOT_ARRIVED_AT_TARGET_NODE skips before completion scan"
    )
    for timestep_result in local_d.timestep_results:
        if timestep_result.offset >= completion_offset:
            continue
        transferred_before = visit_keys_to_vehicle_names(
            timestep_result.binding_transfer_result.transferred_binding_visit_keys
        )
        assert transferred_before == (), (
            f"offset {timestep_result.offset}: unexpected binding transfers "
            f"{transferred_before} before completion offset {completion_offset}"
        )

    c_skip_rows = collect_stage3_skip_rows_for_vehicle(local_d, "C")
    assert len(c_skip_rows) >= 1
    entry_space_rows = []
    for skip_row in c_skip_rows:
        if (
            skip_row["skip_reason"]
            is OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE
        ):
            entry_space_rows.append(skip_row)
    assert len(entry_space_rows) >= 1, (
        "C was skipped, but never for OUTLINK_ENTRY_SPACE_UNAVAILABLE. "
        f"Observed skips: {c_skip_rows}"
    )
    last_skip = c_skip_rows[-1]
    assert (
        last_skip["skip_reason"]
        is OrderControlTvtMpBindingVisitTemporarySkipReason.OUTLINK_ENTRY_SPACE_UNAVAILABLE
    )
    assert economic_required_completion_result.virtual_timestep == last_skip[
        "virtual_timestep"
    ]
    assert completion_offset == 5
    assert completion_virtual_timestep == 15
    newly_recorded_names = visit_keys_to_vehicle_names(
        economic_required_completion_result.newly_recorded_required_passage_visit_keys
    )
    assert set(newly_recorded_names) == {"D", "A", "B"}
    assert (
        economic_required_completion_result.required_passages_complete_after_node_passage
        is True
    )
    assert (
        economic_required_completion_result.calculation_finished_after_timestep_end
        is False
    )
    assert economic_required_completion_result.resolved_after_timestep_end is True
    assert (
        economic_required_completion_result.traffic_observation_complete_after_node_passage
        is False
    )
    transferred_on_economic_required = visit_keys_to_vehicle_names(
        economic_required_completion_result.binding_transfer_result.transferred_binding_visit_keys
    )
    assert transferred_on_economic_required == ("D", "A", "B")

    node_economic_result = junction_node_result(
        pipeline.economic_evaluation_set_result.node_economic_evaluation_results
    )
    economic_d = find_economic_result_by_buyers(node_economic_result, ("D",))
    assert economic_d is not None, (
        "candidate ('D',) did not reach economic evaluation"
    )
    buyer_d_record = None
    for buyer_record in economic_d.buyer_economic_records:
        if buyer_record.vehicle_name == "D":
            buyer_d_record = buyer_record
            break
    assert buyer_d_record is not None
    assert buyer_d_record.expected_time_saving_timesteps > 0
    assert buyer_d_record.gross_time_value_G_b > 0
    assert economic_d.total_buyer_value_G > 0
    assert (
        economic_d.total_buyer_value_G
        >= economic_d.total_required_compensation_R
    )
    assert economic_d.economically_feasible is True
    assert economic_d.infeasibility_reasons == ()

    feasible_results = []
    for economic_result in node_economic_result.candidate_economic_evaluation_results:
        if economic_result.economically_feasible:
            feasible_results.append(economic_result)
    if len(feasible_results) == 0:
        print_stage3_economic_details(node_economic_result)
    assert len(feasible_results) >= 1

    node_selection_result = junction_node_result(
        pipeline.candidate_selection_set_result.node_candidate_selection_results
    )
    assert (
        node_selection_result.selection_status
        is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    )
    assert node_selection_result.selected_candidate_economic_result is not None

    node_payment_result = junction_node_result(
        pipeline.payment_and_compensation_set_result.node_payment_and_compensation_results
    )
    assert node_payment_result is not None

    node_final_rank_result = junction_node_result(
        pipeline.final_rank_set_result.node_final_rank_results
    )
    assert node_final_rank_result is not None
    assert (
        node_final_rank_result.final_rank_status
        is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS
    )
    assert pipeline.final_consistency_validation_set_result is not None
    assert pipeline.atomic_apply_set_result is not None
    assert world.order_control_tvt_driver_started_timestep == world.T


STAGE3_PIPELINE_CANDIDATE_IDENTITIES: tuple[tuple[str, ...], ...] = (
    ("B",),
    ("D",),
    ("B", "D"),
)

COMMON_STAGE_WORKLOAD_CANDIDATE_IDENTITIES: tuple[tuple[str, ...], ...] = (
    ("B",),
    ("D",),
    ("B", "D"),
)


@dataclass(frozen=True)
class TvtMpPerCandidateWorkload:
    """Saved local virtual and trade-rank fields for one concrete buyer set."""

    buyers_sorted: tuple[str, ...]
    seller_count: int
    nonparticipating_count: int
    trade_scope_count: int
    binding_sequence_visit_count: int
    configured_horizon_steps: int
    resolved: bool
    stop_reason: object
    final_offset: int
    simulated_timestep_count: int
    timestep_result_count: int
    binding_transfer_success_visit_count: int
    temporary_skip_count: int
    temporary_skip_reason_counts: dict[str, int]
    newly_recorded_required_passage_count: int
    required_buyer_count: int
    required_seller_count: int
    baseline_passage_record_count: int
    candidate_passage_recorded_required_visit_count: int
    horizon_step_ratio: float


@dataclass(frozen=True)
class TvtMpStageWorkloadSummary:
    """Aggregated TVT-MP workload from one saved driver pipeline."""

    stage_label: str
    target_node_count: int
    candidate_visit_count: int
    concrete_candidate_count: int
    general_trade_rank_candidate_count: int
    fifo_inspection_candidate_count: int
    fifo_true_candidate_count: int
    local_virtual_candidate_count: int
    resolved_candidate_count: int
    unresolved_candidate_count: int
    economic_evaluation_candidate_count: int
    economically_feasible_candidate_count: int
    selected_candidate_buyers: tuple[str, ...] | None
    expected_candidate_local_world_copy_count: int
    per_candidate: tuple[TvtMpPerCandidateWorkload, ...]
    total_simulated_timestep_count: int
    total_timestep_result_count: int
    total_binding_transfer_success_visit_count: int
    total_temporary_skip_count: int
    total_temporary_skip_reason_counts: dict[str, int]
    resolved_rate: float
    total_horizon_step_ratio: float


def _skip_reason_label(skip_reason: object) -> str:
    return str(skip_reason)


def _count_local_virtual_traffic(local_result) -> tuple[int, int, dict[str, int], int]:
    binding_transfer_success = 0
    temporary_skip_count = 0
    skip_reason_counter: Counter[str] = Counter()
    newly_recorded_required = 0
    for timestep_result in local_result.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        binding_transfer_success += len(
            binding_result.transferred_binding_visit_keys
        )
        for skip in binding_result.temporarily_skipped_visits:
            temporary_skip_count += 1
            skip_reason_counter[_skip_reason_label(skip.skip_reason)] += 1
        newly_recorded_required += len(
            timestep_result.newly_recorded_required_passage_visit_keys
        )
    return (
        binding_transfer_success,
        temporary_skip_count,
        dict(skip_reason_counter),
        newly_recorded_required,
    )


def _collect_per_candidate_workload(
    local_result,
    trade_rank_result,
) -> TvtMpPerCandidateWorkload:
    buyers_sorted = visit_keys_to_vehicle_names(
        local_result.concrete_buyer_candidate_set.buyers_sorted
    )
    (
        binding_transfer_success,
        temporary_skip_count,
        skip_reason_counts,
        newly_recorded_required,
    ) = _count_local_virtual_traffic(local_result)
    required_buyer_count = 0
    required_seller_count = 0
    baseline_passage_record_count = 0
    candidate_passage_recorded = 0
    for record in local_result.required_passage_records:
        if record.baseline_passage_timestep is not None:
            baseline_passage_record_count += 1
        if record.candidate_passage_timestep is not None:
            candidate_passage_recorded += 1
        if record.trade_role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
            required_buyer_count += 1
        if record.trade_role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
            required_seller_count += 1
    horizon_steps = local_result.configured_horizon_steps
    horizon_ratio = (
        local_result.simulated_timestep_count / horizon_steps
        if horizon_steps > 0
        else 0.0
    )
    return TvtMpPerCandidateWorkload(
        buyers_sorted=buyers_sorted,
        seller_count=len(trade_rank_result.sellers_sorted),
        nonparticipating_count=len(trade_rank_result.nonparticipating_visits_sorted),
        trade_scope_count=len(trade_rank_result.trade_scope),
        binding_sequence_visit_count=len(
            local_result.binding_rank_sequence.visits_in_binding_order
        ),
        configured_horizon_steps=horizon_steps,
        resolved=local_result.resolved,
        stop_reason=local_result.stop_reason,
        final_offset=local_result.final_offset,
        simulated_timestep_count=local_result.simulated_timestep_count,
        timestep_result_count=len(local_result.timestep_results),
        binding_transfer_success_visit_count=binding_transfer_success,
        temporary_skip_count=temporary_skip_count,
        temporary_skip_reason_counts=skip_reason_counts,
        newly_recorded_required_passage_count=newly_recorded_required,
        required_buyer_count=required_buyer_count,
        required_seller_count=required_seller_count,
        baseline_passage_record_count=baseline_passage_record_count,
        candidate_passage_recorded_required_visit_count=candidate_passage_recorded,
        horizon_step_ratio=horizon_ratio,
    )


def collect_tvt_mp_stage_workload_summary(
    pipeline: DriverPipelineTrace,
    *,
    stage_label: str,
) -> TvtMpStageWorkloadSummary:
    node_candidate_result = junction_node_result(
        pipeline.candidate_visit_set_result.node_candidate_set_results
    )
    node_concrete_result = junction_node_result(
        pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )
    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    node_fifo_result = junction_node_result(
        pipeline.fifo_inspection_set_result.node_fifo_inspection_results
    )
    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    node_economic_result = junction_node_result(
        pipeline.economic_evaluation_set_result.node_economic_evaluation_results
    )
    node_selection_result = junction_node_result(
        pipeline.candidate_selection_set_result.node_candidate_selection_results
    )

    fifo_true_count = 0
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        if fifo_result.preserves_inlink_fifo is True:
            fifo_true_count += 1

    local_results = node_local_result.candidate_local_virtual_calculation_results
    resolved_count = sum(1 for local_result in local_results if local_result.resolved)
    unresolved_count = len(local_results) - resolved_count

    feasible_count = 0
    for economic_result in node_economic_result.candidate_economic_evaluation_results:
        if economic_result.economically_feasible:
            feasible_count += 1

    selected_buyers = None
    selected = node_selection_result.selected_candidate_economic_result
    if selected is not None:
        selected_buyers = visit_keys_to_vehicle_names(
            selected.candidate_local_virtual_calculation_result.concrete_buyer_candidate_set.buyers_sorted
        )

    per_candidate_list = []
    for local_result in local_results:
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        trade_rank_result = find_trade_rank_result_by_buyers(
            node_trade_rank_result,
            buyer_names,
        )
        per_candidate_list.append(
            _collect_per_candidate_workload(local_result, trade_rank_result)
        )
    per_candidate = tuple(
        sorted(per_candidate_list, key=lambda row: row.buyers_sorted)
    )

    total_skip_counter: Counter[str] = Counter()
    total_binding_transfer = 0
    total_skip = 0
    total_simulated = 0
    total_timestep_results = 0
    for row in per_candidate:
        total_binding_transfer += row.binding_transfer_success_visit_count
        total_skip += row.temporary_skip_count
        total_skip_counter.update(row.temporary_skip_reason_counts)
        total_simulated += row.simulated_timestep_count
        total_timestep_results += row.timestep_result_count

    horizon_steps_sum = sum(
        row.configured_horizon_steps for row in per_candidate
    )
    total_horizon_ratio = (
        total_simulated / horizon_steps_sum if horizon_steps_sum > 0 else 0.0
    )
    resolved_rate = resolved_count / len(local_results) if local_results else 0.0

    return TvtMpStageWorkloadSummary(
        stage_label=stage_label,
        target_node_count=len(
            pipeline.candidate_visit_set_result.node_candidate_set_results
        ),
        candidate_visit_count=len(node_candidate_result.candidate_visits),
        concrete_candidate_count=len(
            node_concrete_result.concrete_buyer_candidate_sets
        ),
        general_trade_rank_candidate_count=len(
            node_trade_rank_result.candidate_trade_rank_results
        ),
        fifo_inspection_candidate_count=len(
            node_fifo_result.candidate_fifo_inspection_results
        ),
        fifo_true_candidate_count=fifo_true_count,
        local_virtual_candidate_count=len(local_results),
        resolved_candidate_count=resolved_count,
        unresolved_candidate_count=unresolved_count,
        economic_evaluation_candidate_count=len(
            node_economic_result.candidate_economic_evaluation_results
        ),
        economically_feasible_candidate_count=feasible_count,
        selected_candidate_buyers=selected_buyers,
        expected_candidate_local_world_copy_count=fifo_true_count,
        per_candidate=per_candidate,
        total_simulated_timestep_count=total_simulated,
        total_timestep_result_count=total_timestep_results,
        total_binding_transfer_success_visit_count=total_binding_transfer,
        total_temporary_skip_count=total_skip,
        total_temporary_skip_reason_counts=dict(total_skip_counter),
        resolved_rate=resolved_rate,
        total_horizon_step_ratio=total_horizon_ratio,
    )


def _workload_candidate_by_buyers(
    summary: TvtMpStageWorkloadSummary,
    buyers: tuple[str, ...],
) -> TvtMpPerCandidateWorkload:
    for row in summary.per_candidate:
        if row.buyers_sorted == buyers:
            return row
    raise KeyError(f"no workload row for buyers {buyers!r} in {summary.stage_label}")


def _print_stage_workload_node_summary(summary: TvtMpStageWorkloadSummary) -> None:
    print(f"   stage = {summary.stage_label}")
    print(f"   target_node_count = {summary.target_node_count}")
    print(f"   candidate_visit_count = {summary.candidate_visit_count}")
    print(f"   concrete_candidate_count = {summary.concrete_candidate_count}")
    print(
        "   general_trade_rank_candidate_count = "
        f"{summary.general_trade_rank_candidate_count}"
    )
    print(
        "   fifo_inspection_candidate_count = "
        f"{summary.fifo_inspection_candidate_count}"
    )
    print(f"   fifo_true_candidate_count = {summary.fifo_true_candidate_count}")
    print(
        "   local_virtual_candidate_count = "
        f"{summary.local_virtual_candidate_count}"
    )
    print(f"   resolved_candidate_count = {summary.resolved_candidate_count}")
    print(f"   unresolved_candidate_count = {summary.unresolved_candidate_count}")
    print(
        "   economic_evaluation_candidate_count = "
        f"{summary.economic_evaluation_candidate_count}"
    )
    print(
        "   economically_feasible_candidate_count = "
        f"{summary.economically_feasible_candidate_count}"
    )
    print(f"   selected_candidate_buyers = {summary.selected_candidate_buyers}")
    print(
        "   expected_candidate_local_world_copy_count = "
        f"{summary.expected_candidate_local_world_copy_count} "
        "(expected from one local World per FIFO-True candidate; not directly timed)"
    )


def _print_per_candidate_workload_row(row: TvtMpPerCandidateWorkload) -> None:
    print(f"     buyers_sorted = {row.buyers_sorted}")
    print(f"       seller_count = {row.seller_count}")
    print(f"       nonparticipating_count = {row.nonparticipating_count}")
    print(f"       trade_scope_count = {row.trade_scope_count}")
    print(
        "       binding_sequence_visit_count = "
        f"{row.binding_sequence_visit_count}"
    )
    print(f"       configured_horizon_steps = {row.configured_horizon_steps}")
    print(f"       resolved = {row.resolved}")
    print(f"       stop_reason = {row.stop_reason}")
    print(f"       final_offset = {row.final_offset}")
    print(f"       simulated_timestep_count = {row.simulated_timestep_count}")
    print(f"       timestep_result_count = {row.timestep_result_count}")
    print(
        "       binding_transfer_success_visit_count = "
        f"{row.binding_transfer_success_visit_count}"
    )
    print(f"       temporary_skip_count = {row.temporary_skip_count}")
    print(
        "       temporary_skip_reason_counts = "
        f"{row.temporary_skip_reason_counts}"
    )
    print(
        "       newly_recorded_required_passage_count = "
        f"{row.newly_recorded_required_passage_count}"
    )
    print(f"       required_buyer_count = {row.required_buyer_count}")
    print(f"       required_seller_count = {row.required_seller_count}")
    print(
        "       baseline_passage_record_count = "
        f"{row.baseline_passage_record_count}"
    )
    print(
        "       candidate_passage_recorded_required_visit_count = "
        f"{row.candidate_passage_recorded_required_visit_count}"
    )
    print(f"       horizon_step_ratio = {row.horizon_step_ratio:.4f}")


def print_stage2_versus_stage3_workload_comparison(
    *,
    stage2_summary: TvtMpStageWorkloadSummary,
    stage3_summary: TvtMpStageWorkloadSummary,
    stage2_driver_seconds: float,
    stage3_driver_seconds: float,
) -> None:
    print("=" * 72)
    print("38. Stage 2 versus Stage 3 workload comparison")
    print()
    print("1. Stage 2 summary")
    _print_stage_workload_node_summary(stage2_summary)
    print()
    print("2. Stage 3 summary")
    _print_stage_workload_node_summary(stage3_summary)
    print()
    print("3. Candidate-by-candidate comparison")
    for identity in COMMON_STAGE_WORKLOAD_CANDIDATE_IDENTITIES:
        stage2_row = _workload_candidate_by_buyers(stage2_summary, identity)
        stage3_row = _workload_candidate_by_buyers(stage3_summary, identity)
        print(f"   buyers_sorted = {identity}")
        print("     Stage 2:")
        _print_per_candidate_workload_row(stage2_row)
        print("     Stage 3:")
        _print_per_candidate_workload_row(stage3_row)
    print()
    print("4. Aggregated workload counts")
    for label, summary in (
        ("Stage 2", stage2_summary),
        ("Stage 3", stage3_summary),
    ):
        print(f"   {label}:")
        print(
            "     total_simulated_timestep_count = "
            f"{summary.total_simulated_timestep_count}"
        )
        print(
            "     total_timestep_result_count = "
            f"{summary.total_timestep_result_count}"
        )
        print(
            "     total_binding_transfer_success_visit_count = "
            f"{summary.total_binding_transfer_success_visit_count}"
        )
        print(
            "     total_temporary_skip_count = "
            f"{summary.total_temporary_skip_count}"
        )
        print(
            "     total_temporary_skip_reason_counts = "
            f"{summary.total_temporary_skip_reason_counts}"
        )
        print(f"     resolved_rate = {summary.resolved_rate:.4f}")
        print(
            "     total_horizon_step_ratio = "
            f"{summary.total_horizon_step_ratio:.4f}"
        )
    print()
    print("5. Driver timing comparison (this run only)")
    driver_delta = stage3_driver_seconds - stage2_driver_seconds
    driver_ratio = (
        stage3_driver_seconds / stage2_driver_seconds
        if stage2_driver_seconds > 0
        else float("inf")
    )
    print(f"   stage2_driver_seconds = {stage2_driver_seconds:.4f}")
    print(f"   stage3_driver_seconds = {stage3_driver_seconds:.4f}")
    print(f"   stage3_minus_stage2_seconds = {driver_delta:.4f}")
    print(f"   stage3_over_stage2_ratio = {driver_ratio:.4f}")
    print()
    print("6. Interpretation limits")
    print(
        "   - Stage 2 and Stage 3 differ in traffic state and outlink layout "
        "even when candidate counts match."
    )
    print(
        "   - Driver time difference cannot be attributed to nonparticipating "
        "C remaining unpassed alone."
    )
    print(
        "   - Saved results do not include per-stage internal timings or "
        "isolated World.copy durations."
    )
    print(
        "   - This comparison uses whole-driver timing and saved workload "
        "counts only."
    )
    print(
        "   - Additional load from approaches A/B/C is not measured in this "
        "diagnostic output."
    )
    print("=" * 72)


def assert_stage2_stage3_workload_invariants(
    stage2_summary: TvtMpStageWorkloadSummary,
    stage3_summary: TvtMpStageWorkloadSummary,
) -> None:
    assert stage2_summary.target_node_count == 1
    assert stage3_summary.target_node_count == 1
    assert stage2_summary.concrete_candidate_count == 3
    assert stage3_summary.concrete_candidate_count == 3
    assert stage2_summary.fifo_true_candidate_count == 3
    assert stage3_summary.fifo_true_candidate_count == 3
    assert stage2_summary.local_virtual_candidate_count == 3
    assert stage3_summary.local_virtual_candidate_count == 3

    for summary in (stage2_summary, stage3_summary):
        for row in summary.per_candidate:
            # Saved results keep one timestep_result per processed offset
            # (0 .. final_offset). simulated_timestep_count equals final_offset.
            assert row.simulated_timestep_count == row.final_offset, (
                f"{summary.stage_label} {row.buyers_sorted}: "
                f"simulated_timestep_count {row.simulated_timestep_count} != "
                f"final_offset {row.final_offset}"
            )
            assert row.timestep_result_count == row.final_offset + 1, (
                f"{summary.stage_label} {row.buyers_sorted}: "
                f"timestep_results {row.timestep_result_count} != "
                f"final_offset + 1 ({row.final_offset + 1})"
            )
        assert (
            summary.resolved_candidate_count + summary.unresolved_candidate_count
            == summary.local_virtual_candidate_count
        )
        assert (
            summary.expected_candidate_local_world_copy_count
            == summary.fifo_true_candidate_count
        )

    stage2_identities = {row.buyers_sorted for row in stage2_summary.per_candidate}
    stage3_identities = {row.buyers_sorted for row in stage3_summary.per_candidate}
    expected_identities = set(COMMON_STAGE_WORKLOAD_CANDIDATE_IDENTITIES)
    assert stage2_identities == expected_identities
    assert stage3_identities == expected_identities


def stage3_buyer_identity_from_visit_keys(
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
) -> tuple[str, ...]:
    return visit_keys_to_vehicle_names(buyers_sorted)


def stage3_fork_collector_from_pipeline(pipeline: DriverPipelineTrace):
    right_of_entry_result = pipeline.right_of_entry_selection_result
    leading_result = right_of_entry_result.leading_confirmation_result
    arrived_result = leading_result.arrived_confirmation_result
    alignment_fork_result = arrived_result.alignment_fork_result
    fork_result = alignment_fork_result.fork_result
    return fork_result.collector


def stage3_identity_present_in_concrete_sets(
    node_concrete_result,
    identity: tuple[str, ...],
) -> bool:
    for concrete_set in node_concrete_result.concrete_buyer_candidate_sets:
        candidate_identity = stage3_buyer_identity_from_visit_keys(
            concrete_set.buyers_sorted
        )
        if candidate_identity == identity:
            return True
    return False


def stage3_identity_present_in_trade_ranks(
    node_trade_rank_result,
    identity: tuple[str, ...],
) -> bool:
    for trade_rank_result in node_trade_rank_result.candidate_trade_rank_results:
        candidate_identity = stage3_buyer_identity_from_visit_keys(
            trade_rank_result.buyers_sorted
        )
        if candidate_identity == identity:
            return True
    return False


def stage3_identity_present_in_fifo_results(
    node_fifo_result,
    identity: tuple[str, ...],
) -> bool:
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        trade_rank_result = fifo_result.general_trade_rank_result
        candidate_identity = stage3_buyer_identity_from_visit_keys(
            trade_rank_result.buyers_sorted
        )
        if candidate_identity == identity:
            return True
    return False


def stage3_identity_present_in_fifo_true_results(
    node_fifo_result,
    identity: tuple[str, ...],
) -> bool:
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        if fifo_result.preserves_inlink_fifo is not True:
            continue
        trade_rank_result = fifo_result.general_trade_rank_result
        candidate_identity = stage3_buyer_identity_from_visit_keys(
            trade_rank_result.buyers_sorted
        )
        if candidate_identity == identity:
            return True
    return False


def stage3_identity_present_in_local_results(
    node_local_result,
    identity: tuple[str, ...],
) -> bool:
    for local_result in node_local_result.candidate_local_virtual_calculation_results:
        candidate_identity = stage3_buyer_identity_from_visit_keys(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        if candidate_identity == identity:
            return True
    return False


def stage3_first_missing_stage_for_identity(
    node_concrete_result,
    node_trade_rank_result,
    node_fifo_result,
    node_local_result,
    identity: tuple[str, ...],
) -> str | None:
    stage_checks = (
        (
            "concrete candidate",
            stage3_identity_present_in_concrete_sets(
                node_concrete_result,
                identity,
            ),
        ),
        (
            "general trade rank",
            stage3_identity_present_in_trade_ranks(
                node_trade_rank_result,
                identity,
            ),
        ),
        (
            "FIFO inspection",
            stage3_identity_present_in_fifo_results(
                node_fifo_result,
                identity,
            ),
        ),
        (
            "FIFO True",
            stage3_identity_present_in_fifo_true_results(
                node_fifo_result,
                identity,
            ),
        ),
        (
            "local virtual result",
            stage3_identity_present_in_local_results(
                node_local_result,
                identity,
            ),
        ),
    )
    for stage_name, is_present in stage_checks:
        if not is_present:
            return stage_name
    return None


def print_stage3_pipeline_diagnostic_before_candidate_lookup(
    pipeline: DriverPipelineTrace,
) -> None:
    print("=" * 72)
    print("25. Stage 3 pipeline diagnostic before candidate lookup")
    print()

    right_of_entry_result = pipeline.right_of_entry_selection_result
    leading_result = right_of_entry_result.leading_confirmation_result
    candidate_visit_set_result = pipeline.candidate_visit_set_result
    node_candidate_result = junction_node_result(
        candidate_visit_set_result.node_candidate_set_results
    )
    node_concrete_result = junction_node_result(
        pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )
    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    node_fifo_result = junction_node_result(
        pipeline.fifo_inspection_set_result.node_fifo_inspection_results
    )
    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    right_of_entry_node = junction_node_result(
        right_of_entry_result.node_selection_results
    )
    leading_node = junction_node_result(leading_result.node_confirmation_results)
    collector = stage3_fork_collector_from_pipeline(pipeline)

    print("1. Node result counts")
    print(f"   target_node_name = {JUNCTION_NODE_NAME}")
    print(
        "   right_of_entry_node_result_count = "
        f"{len(right_of_entry_result.node_selection_results)}"
    )
    print(
        "   candidate_visit_set_node_result_count = "
        f"{len(candidate_visit_set_result.node_candidate_set_results)}"
    )
    print(
        "   concrete_candidate_node_result_count = "
        f"{len(pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results)}"
    )
    print(
        "   general_trade_rank_node_result_count = "
        f"{len(pipeline.general_trade_rank_set_result.node_trade_rank_results)}"
    )
    print(
        "   fifo_node_result_count = "
        f"{len(pipeline.fifo_inspection_set_result.node_fifo_inspection_results)}"
    )
    print(
        "   local_virtual_node_result_count = "
        f"{len(pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results)}"
    )
    print()

    print("2. Right-of-entry")
    print(f"   selection_status = {right_of_entry_node.selection_status}")
    print(
        f"   right_of_entry_visit_key = "
        f"{right_of_entry_node.right_of_entry_visit_key}"
    )
    roe_vehicle_name = None
    if right_of_entry_node.right_of_entry_visit_key is not None:
        roe_vehicle_name = right_of_entry_node.right_of_entry_visit_key[0]
    print(f"   right_of_entry_vehicle_name = {roe_vehicle_name}")
    print(f"   k_confirmed_before = {right_of_entry_node.k_confirmed_before}")
    print()

    print("3. Leading decision-window")
    print(
        "   decision_window_visit_keys = "
        f"{leading_node.decision_window_visit_keys}"
    )
    print(
        "   confirmed_leading_nonparticipating_visit_keys = "
        f"{leading_node.confirmed_leading_nonparticipating_visit_keys}"
    )
    print(
        "   remaining_decision_window_visit_keys = "
        f"{leading_node.remaining_decision_window_visit_keys}"
    )
    print()

    print("4. Candidate visit set")
    print(f"   build_status = {node_candidate_result.build_status}")
    print(
        f"   right_of_entry_visit_key = "
        f"{node_candidate_result.right_of_entry_visit_key}"
    )
    print(
        "   right_of_entry_baseline_passage_timestep = "
        f"{node_candidate_result.right_of_entry_baseline_passage_timestep}"
    )
    print(
        "   p_minus_one_eligible_visit_count_before_limit = "
        f"{node_candidate_result.p_minus_one_eligible_visit_count_before_limit}"
    )
    print(f"   candidate_visits_count = {len(node_candidate_result.candidate_visits)}")
    for visit in node_candidate_result.candidate_visits:
        vehicle_name = visit.visit_key[0]
        print(f"   candidate_visit {vehicle_name}:")
        print(f"     visit_key = {visit.visit_key}")
        print(f"     vehicle_name = {vehicle_name}")
        print(f"     inlink_name = {visit.inlink_name}")
        print(f"     baseline_arrival_timestep = {visit.baseline_arrival_timestep}")
        print(f"     arrival_tiebreaker = {visit.arrival_tiebreaker}")
        print(f"     baseline_passage_timestep = {visit.baseline_passage_timestep}")
        print(f"     route_next_link_name = {visit.route_next_link_name}")
    print()

    print("5. Stage 3 baseline collector (fork result on saved pipeline)")
    for vehicle_name in ("A", "B", "C", "D"):
        visit_id = None
        for visit in node_candidate_result.candidate_visits:
            if visit.visit_key[0] == vehicle_name:
                visit_id = visit.visit_key[1]
                break
        if visit_id is None:
            exported = collector.export_node_baseline_visits(JUNCTION_NODE_NAME)
            for record in exported:
                if record["vehicle_name"] == vehicle_name:
                    visit_id = record["visit_id"]
                    snap = record
                    break
            else:
                print(f"   {vehicle_name}: (no collector record found)")
                continue
        else:
            snap = collector.get_baseline_visit_snapshot(vehicle_name, visit_id)
        if snap is None:
            print(f"   {vehicle_name}: (collector snapshot is None)")
            continue
        print(f"   {vehicle_name}:")
        print(f"     vehicle_name = {snap['vehicle_name']}")
        print(f"     visit_id = {snap['visit_id']}")
        print(
            f"     was_arrived_at_snapshot = {snap['was_arrived_at_snapshot']}"
        )
        print(
            f"     baseline_arrival_timestep = {snap['baseline_arrival_timestep']}"
        )
        print(f"     arrival_tiebreaker = {snap['arrival_tiebreaker']}")
        print(f"     route_next_link_name = {snap['route_next_link_name']}")
        print(
            f"     baseline_passage_timestep = {snap['baseline_passage_timestep']}"
        )
    print()

    print("6. Concrete buyer candidate set")
    print(f"   build_status = {node_concrete_result.build_status}")
    for prefix_result in node_concrete_result.buyer_candidate_inlink_prefix_results:
        prefix_labels = []
        for prefix in prefix_result.buyer_prefixes_empty_to_max:
            prefix_labels.append(visit_keys_to_vehicle_names(prefix))
        print(f"   inlink {prefix_result.inlink_name}:")
        print(f"     buyer_prefixes_empty_to_max = {prefix_labels}")
    print(
        "   concrete_candidate_count = "
        f"{len(node_concrete_result.concrete_buyer_candidate_sets)}"
    )
    for concrete_set in node_concrete_result.concrete_buyer_candidate_sets:
        buyer_names = visit_keys_to_vehicle_names(concrete_set.buyers_sorted)
        print(f"   buyers_sorted VisitKeys = {concrete_set.buyers_sorted}")
        print(f"   buyers_sorted vehicle_names = {buyer_names}")
    print()

    print("7. General trade rank")
    print(f"   build_status = {node_trade_rank_result.build_status}")
    print(
        "   candidate_trade_rank_result_count = "
        f"{len(node_trade_rank_result.candidate_trade_rank_results)}"
    )
    for trade_rank_result in node_trade_rank_result.candidate_trade_rank_results:
        buyer_names = visit_keys_to_vehicle_names(trade_rank_result.buyers_sorted)
        print(f"   candidate {buyer_names}:")
        print(
            "     buyers_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.buyers_sorted)}"
        )
        print(
            "     sellers_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.sellers_sorted)}"
        )
        print(
            "     nonparticipating_visits_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.nonparticipating_visits_sorted)}"
        )
        print(
            "     trade_scope = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.trade_scope)}"
        )
        print(
            "     trade_order = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.trade_order)}"
        )
        print(f"     last_buyer_rank = {trade_rank_result.last_buyer_rank}")
    print()

    print("8. FIFO inspection")
    print(f"   build_status = {node_fifo_result.build_status}")
    print(
        "   candidate_fifo_inspection_result_count = "
        f"{len(node_fifo_result.candidate_fifo_inspection_results)}"
    )
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        buyer_names = visit_keys_to_vehicle_names(
            fifo_result.general_trade_rank_result.buyers_sorted
        )
        print(f"   candidate {buyer_names}:")
        print(f"     preserves_inlink_fifo = {fifo_result.preserves_inlink_fifo}")
    print()

    print("9. Local virtual calculation set")
    print(f"   build_status = {node_local_result.build_status}")
    print(
        "   candidate_local_virtual_calculation_result_count = "
        f"{len(node_local_result.candidate_local_virtual_calculation_results)}"
    )
    for local_result in node_local_result.candidate_local_virtual_calculation_results:
        buyer_names = visit_keys_to_vehicle_names(
            local_result.concrete_buyer_candidate_set.buyers_sorted
        )
        print(f"   candidate {buyer_names}:")
        print(f"     resolved = {local_result.resolved}")
        print(f"     stop_reason = {local_result.stop_reason}")
        print(f"     final_offset = {local_result.final_offset}")
        print(
            f"     simulated_timestep_count = {local_result.simulated_timestep_count}"
        )
    print()

    print("10. Stage presence summary (by buyer vehicle-name identity)")
    stage_labels = (
        "concrete candidate",
        "general trade rank",
        "FIFO inspection",
        "FIFO True",
        "local virtual result",
    )
    for identity in STAGE3_PIPELINE_CANDIDATE_IDENTITIES:
        print(f"   identity {identity}:")
        print(
            f"     concrete candidate = "
            f"{stage3_identity_present_in_concrete_sets(node_concrete_result, identity)}"
        )
        print(
            f"     general trade rank = "
            f"{stage3_identity_present_in_trade_ranks(node_trade_rank_result, identity)}"
        )
        print(
            f"     FIFO inspection = "
            f"{stage3_identity_present_in_fifo_results(node_fifo_result, identity)}"
        )
        print(
            f"     FIFO True = "
            f"{stage3_identity_present_in_fifo_true_results(node_fifo_result, identity)}"
        )
        print(
            f"     local virtual result = "
            f"{stage3_identity_present_in_local_results(node_local_result, identity)}"
        )
    d_identity = ("D",)
    first_missing = stage3_first_missing_stage_for_identity(
        node_concrete_result,
        node_trade_rank_result,
        node_fifo_result,
        node_local_result,
        d_identity,
    )
    if first_missing is None:
        print(
            "   candidate ('D',) first missing stage = "
            "(present through local virtual result)"
        )
    else:
        print(
            "   candidate ('D',) first missing stage = "
            f"{first_missing}"
        )
    print("=" * 72)
    sys.stdout.flush()


def print_stage3_report(
    world: World,
    pipeline: DriverPipelineTrace,
    build_timings: BuildDiagnosticWorldTimings,
    world_prepare_seconds: float,
    driver_seconds: float,
    stage3_total_seconds: float,
) -> None:
    node_candidate_result = junction_node_result(
        pipeline.candidate_visit_set_result.node_candidate_set_results
    )
    visits_by_name = stage3_candidate_visits_by_name(node_candidate_result)
    right_of_entry_node = junction_node_result(
        pipeline.right_of_entry_selection_result.node_selection_results
    )
    node_concrete_result = junction_node_result(
        pipeline.concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results
    )
    node_fifo_result = junction_node_result(
        pipeline.fifo_inspection_set_result.node_fifo_inspection_results
    )
    node_trade_rank_result = junction_node_result(
        pipeline.general_trade_rank_set_result.node_trade_rank_results
    )
    node_local_result = junction_node_result(
        pipeline.local_virtual_calculation_set_result.node_local_virtual_calculation_results
    )
    local_d = find_local_virtual_result_by_buyers(node_local_result, ("D",))
    local_bd = find_local_virtual_result_by_buyers(node_local_result, ("B", "D"))
    trade_d = find_trade_rank_result_by_buyers(node_trade_rank_result, ("D",))
    node_economic_result = junction_node_result(
        pipeline.economic_evaluation_set_result.node_economic_evaluation_results
    )
    node_selection_result = junction_node_result(
        pipeline.candidate_selection_set_result.node_candidate_selection_results
    )
    node_final_rank_result = junction_node_result(
        pipeline.final_rank_set_result.node_final_rank_results
    )

    print("=" * 72)
    print("26. Stage 3 counterexample World settings")
    print(f"   world_name = {world.name}")
    print(f"   deltan = {world.DELTAN}")
    print(f"   random_seed = {world.random_seed}")
    print(f"   hard_deterministic_mode = {world.hard_deterministic_mode}")
    print(f"   snapshot_T = {SNAPSHOT_TIMESTEP_T}")
    print(f"   baseline_horizon_steps = {BASELINE_HORIZON_STEPS}")
    print("   max_candidate_visit_count = 4")
    print("   snapshot_x_by_vehicle:")
    for spec in STAGE3_VEHICLE_SPECS:
        print(f"     {spec['name']} = {spec['snapshot_x']}")
    print(
        "   baseline_flow_release_timestep = "
        f"{STAGE3_BASELINE_FLOW_RELEASE_TIMESTEP}"
    )
    print(
        "   junction_clearance_timesteps = "
        f"{world.get_node(JUNCTION_NODE_NAME).order_control_clearance_timesteps}"
    )
    print(
        "   approach_inlink_capacity_out = "
        f"{STAGE3_APPROACH_INLINK_CAPACITY_OUT}"
    )
    print(
        "   approach_inlink_capacity_in = "
        f"{STAGE3_APPROACH_INLINK_CAPACITY_IN}"
    )
    print("   vehicles = A seller out_c, B seller out_b, C nonparticipating out_c, D buyer out_d")
    print(
        "   declared_vot = "
        f"{STAGE3_DECLARED_VOT_BY_VEHICLE}"
    )
    print()

    print("27. Stage 3 baseline collector results")
    ordered_names = sorted(
        visits_by_name.keys(),
        key=lambda name: stage3_baseline_sort_key(visits_by_name[name]),
    )
    for vehicle_name in ("A", "B", "C", "D"):
        visit = visits_by_name[vehicle_name]
        print(f"   {vehicle_name}:")
        print(f"     visit_key = {visit.visit_key}")
        print(f"     inlink = {visit.inlink_name}")
        print(f"     route_next_link = {visit.route_next_link_name}")
        print(f"     baseline_arrival = {visit.baseline_arrival_timestep}")
        print(f"     arrival_tiebreaker = {visit.arrival_tiebreaker}")
        print(f"     vehicle_id = {visit.vehicle_id}")
        print(f"     baseline_passage = {visit.baseline_passage_timestep}")
    print(f"   baseline_order = {ordered_names}")
    print(
        "   candidate_visit_build_status = "
        f"{node_candidate_result.build_status}"
    )
    print()

    print("28. Stage 3 right-of-entry and candidate visits")
    print(
        "   right_of_entry = "
        f"{right_of_entry_node.right_of_entry_visit_key}"
    )
    print(
        "   right_of_entry_baseline_passage = "
        f"{node_candidate_result.right_of_entry_baseline_passage_timestep}"
    )
    for visit in node_candidate_result.candidate_visits:
        print(
            f"   candidate_visit {visit.visit_key[0]} "
            f"arrival={visit.baseline_arrival_timestep} "
            f"passage={visit.baseline_passage_timestep}"
        )
    print()

    print("29. Stage 3 concrete candidates and FIFO")
    fifo_true_count = 0
    for fifo_result in node_fifo_result.candidate_fifo_inspection_results:
        buyer_names = visit_keys_to_vehicle_names(
            fifo_result.general_trade_rank_result.buyers_sorted
        )
        if fifo_result.preserves_inlink_fifo is True:
            fifo_true_count += 1
        print(
            f"   {buyer_names}: preserves_inlink_fifo="
            f"{fifo_result.preserves_inlink_fifo}"
        )
    concrete_labels = []
    for concrete_set in node_concrete_result.concrete_buyer_candidate_sets:
        concrete_labels.append(
            visit_keys_to_vehicle_names(concrete_set.buyers_sorted)
        )
    print(f"   concrete_candidates = {concrete_labels}")
    print(f"   fifo_true_count = {fifo_true_count}")
    print()

    print("30. Stage 3 trade roles and complete binding sequence")
    for expected_buyers in (("B",), ("D",), ("B", "D")):
        trade_rank_result = find_trade_rank_result_by_buyers(
            node_trade_rank_result,
            expected_buyers,
        )
        print(f"   candidate {expected_buyers}:")
        print(
            "     buyers_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.buyers_sorted)}"
        )
        print(
            "     sellers_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.sellers_sorted)}"
        )
        print(
            "     nonparticipating_visits_sorted = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.nonparticipating_visits_sorted)}"
        )
        print(
            "     trade_scope = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.trade_scope)}"
        )
        print(
            "     trade_order = "
            f"{visit_keys_to_vehicle_names(trade_rank_result.trade_order)}"
        )
    print("   candidate ('D',) binding sequence:")
    for binding_visit in local_d.binding_rank_sequence.visits_in_binding_order:
        print(
            f"     rank {binding_visit.binding_rank}: "
            f"{binding_visit.visit_key[0]} "
            f"role={binding_visit.trade_role} "
            f"partition={binding_visit.binding_partition} "
            f"route={binding_visit.route_next_link_name} "
            f"inlink={binding_visit.inlink_name}"
        )
    print()

    print("31. Stage 3 candidate-local timestep trace")
    print("   candidate ('D',)")
    binding_order_names = []
    for binding_visit in local_d.binding_rank_sequence.visits_in_binding_order:
        binding_order_names.append(binding_visit.visit_key[0])
    for timestep_result in local_d.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        print(f"   offset = {timestep_result.offset}")
        print(f"     virtual_timestep = {timestep_result.virtual_timestep}")
        print(f"     binding_order = {tuple(binding_order_names)}")
        print(
            "     transferred_binding_visit_keys = "
            f"{binding_result.transferred_binding_visit_keys}"
        )
        print(
            "     temporarily_skipped_visits count = "
            f"{len(binding_result.temporarily_skipped_visits)}"
        )
        for skip in binding_result.temporarily_skipped_visits:
            print(f"       skip VisitKey = {skip.binding_visit_key}")
            print(f"       skip reason = {skip.skip_reason}")
        print(
            "     newly_recorded_required_passage_visit_keys = "
            f"{timestep_result.newly_recorded_required_passage_visit_keys}"
        )
        print(
            "     required_passages_complete_after_node_passage = "
            f"{timestep_result.required_passages_complete_after_node_passage}"
        )
        print(
            "     calculation_finished_after_timestep_end = "
            f"{timestep_result.calculation_finished_after_timestep_end}"
        )
        print(
            "     resolved_after_timestep_end = "
            f"{timestep_result.resolved_after_timestep_end}"
        )
    print()

    print("31a. Stage 3 candidate-local capacity and binding diagnostic")
    print("   candidate ('D',)")
    print(
        "   note: OrderControlTvtMpCandidateVirtualTimestepResult does not "
        "store per-inlink capacity_out_remain at binding-scan time; "
        "skip reasons below verify the hold."
    )
    print(
        "   vehicle_to_inlink = "
        f"{ {name: stage3_vehicle_inlink_name(name) for name in ('A', 'B', 'C', 'D')} }"
    )
    for timestep_result in local_d.timestep_results:
        binding_result = timestep_result.binding_transfer_result
        print(f"   offset = {timestep_result.offset}")
        print(f"     virtual_timestep = {timestep_result.virtual_timestep}")
        print(
            "     transferred_binding_visit_keys = "
            f"{binding_result.transferred_binding_visit_keys}"
        )
        print(
            "     temporarily_skipped_visits = "
            f"{len(binding_result.temporarily_skipped_visits)}"
        )
        for skip in binding_result.temporarily_skipped_visits:
            print(f"       VisitKey = {skip.binding_visit_key}")
            print(f"       skip_reason = {skip.skip_reason}")
        print(
            "     newly_recorded_required_passage_visit_keys = "
            f"{timestep_result.newly_recorded_required_passage_visit_keys}"
        )
        print(
            "     required_passages_complete_after_node_passage = "
            f"{timestep_result.required_passages_complete_after_node_passage}"
        )
        print(
            "     calculation_finished_after_timestep_end = "
            f"{timestep_result.calculation_finished_after_timestep_end}"
        )
        print(
            "     resolved_after_timestep_end = "
            f"{timestep_result.resolved_after_timestep_end}"
        )
    print()

    print("32. Stage 3 C temporary-skip evidence")
    c_skip_rows = collect_stage3_skip_rows_for_vehicle(local_d, "C")
    print(f"   C skip count = {len(c_skip_rows)}")
    for skip_row in c_skip_rows:
        print(
            f"   offset={skip_row['offset']} "
            f"virtual_timestep={skip_row['virtual_timestep']} "
            f"VisitKey={skip_row['visit_key']} "
            f"reason={skip_row['skip_reason']}"
        )
    print(
        "   C transferred_binding appearance count = "
        f"{count_stage3_transferred_appearances(local_d, 'C')}"
    )
    print()

    print("33. Stage 3 required passage and trade_scope observation completion")
    print(
        "   note: candidate ('D',) becomes resolved at offset 5 once economic "
        "required passages complete, but calculation_finished stays False until "
        "offset 6 when nonparticipating C binding-transfers and trade_scope "
        "traffic observation completes."
    )
    print(f"   resolved = {local_d.resolved}")
    print(f"   stop_reason = {local_d.stop_reason}")
    print(f"   final_offset = {local_d.final_offset}")
    print(f"   final_virtual_timestep = {local_d.final_virtual_timestep}")
    print(f"   simulated_timestep_count = {local_d.simulated_timestep_count}")
    print(
        "   economic_required_passages_complete_offset = "
        f"{local_d.economic_required_passages_complete_offset}"
    )
    print(
        "   economic_required_passages_complete_virtual_timestep = "
        f"{local_d.economic_required_passages_complete_virtual_timestep}"
    )
    print(
        "   all_trade_scope_passages_complete_offset = "
        f"{local_d.all_trade_scope_passages_complete_offset}"
    )
    print(
        "   all_trade_scope_passages_complete_virtual_timestep = "
        f"{local_d.all_trade_scope_passages_complete_virtual_timestep}"
    )
    c_traffic_d = stage3_traffic_observation_record_for_vehicle(local_d, "C")
    print("   candidate ('D',) C final traffic observation:")
    print(
        f"     passage_observation_status = "
        f"{c_traffic_d.passage_observation_status}"
    )
    print(
        f"     candidate_passage_timestep = "
        f"{c_traffic_d.candidate_passage_timestep}"
    )
    print(
        f"     predicted_time_difference_timesteps = "
        f"{c_traffic_d.predicted_time_difference_timesteps}"
    )
    print(
        f"     predicted_signed_time_value_change = "
        f"{c_traffic_d.predicted_signed_time_value_change}"
    )
    print(
        f"     last_temporary_skip_reason = "
        f"{c_traffic_d.last_temporary_skip_reason}"
    )
    print(
        f"     last_temporary_skip_offset = "
        f"{c_traffic_d.last_temporary_skip_offset}"
    )
    print(
        "   candidate ('B', 'D') economic_required_passages_complete_offset = "
        f"{local_bd.economic_required_passages_complete_offset}"
    )
    print(
        "   candidate ('B', 'D') all_trade_scope_passages_complete_offset = "
        f"{local_bd.all_trade_scope_passages_complete_offset}"
    )
    c_traffic_bd = stage3_traffic_observation_record_for_vehicle(local_bd, "C")
    print("   candidate ('B', 'D') C final traffic observation:")
    print(
        f"     passage_observation_status = "
        f"{c_traffic_bd.passage_observation_status}"
    )
    print(
        f"     candidate_passage_timestep = "
        f"{c_traffic_bd.candidate_passage_timestep}"
    )
    print(
        f"     observed_offset = {c_traffic_bd.observed_offset}, "
        f"observed_virtual_timestep = "
        f"{c_traffic_bd.observed_virtual_timestep}"
    )
    for record in local_d.required_passage_records:
        print(
            f"   required {record.vehicle_name}: "
            f"baseline_passage={record.baseline_passage_timestep}, "
            f"candidate_passage={record.candidate_passage_timestep}, "
            f"role={record.trade_role}"
        )
    print(
        "   trade_order = "
        f"{visit_keys_to_vehicle_names(trade_d.trade_order)}"
    )
    print()

    print("34. Stage 3 economic and selection")
    economic_d = find_economic_result_by_buyers(node_economic_result, ("D",))
    print("   candidate ('D',) economic summary:")
    for buyer_record in economic_d.buyer_economic_records:
        if buyer_record.vehicle_name != "D":
            continue
        print(
            "     buyer D expected_time_saving_timesteps = "
            f"{buyer_record.expected_time_saving_timesteps}"
        )
        print(f"     buyer D gross_time_value_G_b = {buyer_record.gross_time_value_G_b}")
    for seller_record in economic_d.seller_economic_records:
        print(f"     seller {seller_record.vehicle_name}:")
        print(f"       baseline_passage = {seller_record.baseline_passage_timestep}")
        print(f"       candidate_passage = {seller_record.candidate_passage_timestep}")
        print(
            "       expected_waiting_increase_timesteps = "
            f"{seller_record.expected_waiting_increase_timesteps}"
        )
        print(f"       declared_vot_per_second = {seller_record.declared_vot_per_second}")
        print(f"       required_compensation_R_s = {seller_record.required_compensation_R_s}")
    print(f"     total_G = {economic_d.total_buyer_value_G}")
    print(f"     total_R = {economic_d.total_required_compensation_R}")
    print(f"     surplus = {economic_d.surplus}")
    print(f"     economically_feasible = {economic_d.economically_feasible}")
    print_stage3_economic_details(node_economic_result)
    feasible_count = 0
    for economic_result in node_economic_result.candidate_economic_evaluation_results:
        if economic_result.economically_feasible:
            feasible_count += 1
    print(f"   economically_feasible_count = {feasible_count}")
    print(f"   selection_status = {node_selection_result.selection_status}")
    selected = node_selection_result.selected_candidate_economic_result
    if selected is not None:
        selected_buyers = visit_keys_to_vehicle_names(
            selected.candidate_local_virtual_calculation_result.concrete_buyer_candidate_set.buyers_sorted
        )
        print(f"   selected_candidate = {selected_buyers}")
        print(f"   selected_surplus = {selected.surplus}")
    node_payment_result = junction_node_result(
        pipeline.payment_and_compensation_set_result.node_payment_and_compensation_results
    )
    print(
        "   payment_and_compensation_status = "
        f"{node_payment_result.payment_and_compensation_status}"
    )
    print()

    print("35. Stage 3 final rank, validation, and atomic apply")
    print(f"   final_rank_status = {node_final_rank_result.final_rank_status}")
    print(
        "   final_rank_visit_count = "
        f"{len(node_final_rank_result.final_rank_visits)}"
    )
    print("   validation result present = True")
    print("   atomic apply result present = True")
    print()

    print("36. Stage 3 timings")
    print(f"   stage3_world_prepare_seconds = {world_prepare_seconds:.4f}")
    print(
        "   stage3_finalize_scenario_seconds = "
        f"{build_timings.finalize_scenario_seconds:.4f}"
    )
    print(
        "   stage3_finalize_scenario is included in world prepare, "
        "not in driver time"
    )
    print(f"   stage3_run_tvt_mp_driver_seconds = {driver_seconds:.4f}")
    print(f"   stage3_total_seconds = {stage3_total_seconds:.4f}")
    print()


def run_stage3_counterexample() -> tuple[DriverPipelineTrace, float]:
    stage3_total_start = time.perf_counter()
    world_prepare_start = time.perf_counter()
    build_timings = BuildDiagnosticWorldTimings()
    world, flow_hold = build_stage3_world(build_timings)

    vehicles_by_name = add_stage3_vehicles(world)
    advance_stage3_until_natural_outlink_choice(world, vehicles_by_name)
    world.T = SNAPSHOT_TIMESTEP_T
    for spec in STAGE3_VEHICLE_SPECS:
        place_stage3_vehicle_at_common_snapshot(
            world,
            vehicles_by_name[spec["name"]],
            spec,
        )
    world.T = SNAPSHOT_TIMESTEP_T
    rewind_stage3_link_cumulative_counts_to_snapshot(world)
    open_stage3_capacities_for_same_scan_passage(world)
    flow_hold.release_timestep = STAGE3_BASELINE_FLOW_RELEASE_TIMESTEP
    configure_stage3_driver_settings(world)
    world_prepare_seconds = time.perf_counter() - world_prepare_start

    driver_start = time.perf_counter()
    driver_result = run_tvt_mp_driver(world)
    driver_seconds = time.perf_counter() - driver_start
    stage3_total_seconds = time.perf_counter() - stage3_total_start

    pipeline = trace_driver_pipeline(driver_result)
    print_stage3_pipeline_diagnostic_before_candidate_lookup(pipeline)
    print_stage3_report(
        world,
        pipeline,
        build_timings,
        world_prepare_seconds,
        driver_seconds,
        stage3_total_seconds,
    )
    assert_stage3_counterexample(pipeline, world)
    print("37. Stage 3 counterexample asserts: PASS")
    print("=" * 72)
    return pipeline, driver_seconds


def main() -> None:
    total_start = time.perf_counter()
    world_prepare_start = time.perf_counter()
    prepare_breakdown = WorldPrepareTimingBreakdown()

    world = build_diagnostic_world(prepare_breakdown.build_diagnostic_world)

    add_vehicles_start = time.perf_counter()
    vehicles_by_name = add_diagnostic_vehicles(world)
    prepare_breakdown.add_diagnostic_vehicles_seconds = (
        time.perf_counter() - add_vehicles_start
    )

    advance_all_start = time.perf_counter()
    for spec in VEHICLE_SPECS:
        vehicle = vehicles_by_name[spec["name"]]
        advance_metrics = advance_until_on_inlink(vehicle, spec["inlink"])
        prepare_breakdown.advance_by_vehicle[spec["name"]] = advance_metrics
        assert_vehicle_on_approach_inlink(vehicle, spec)
    prepare_breakdown.advance_all_vehicles_seconds = (
        time.perf_counter() - advance_all_start
    )

    capacity_start = time.perf_counter()
    open_junction_capacities_for_baseline(world)
    prepare_breakdown.open_junction_capacities_seconds = (
        time.perf_counter() - capacity_start
    )

    snapshot_start = time.perf_counter()
    pre_snapshot_rows = []
    for spec in VEHICLE_SPECS:
        vehicle = vehicles_by_name[spec["name"]]
        place_not_yet_arrived_at_snapshot(
            world,
            vehicle,
            inlink_name=spec["inlink"],
            snapshot_timestep=SNAPSHOT_TIMESTEP_T,
            x_position=spec["snapshot_x"],
        )
        pre_snapshot_rows.append(collect_vehicle_snapshot_row(vehicle, spec))
    prepare_breakdown.snapshot_placement_seconds = (
        time.perf_counter() - snapshot_start
    )

    assert_capacity_start = time.perf_counter()
    assert_capacity_ready_for_fork(world)
    prepare_breakdown.assert_capacity_ready_seconds = (
        time.perf_counter() - assert_capacity_start
    )

    place_outlink_passage_gate_vehicle(world)

    if world._order_control_baseline_collector is not None:
        raise RuntimeError("real_W collector must be None before baseline fork")

    world_prepare_seconds = time.perf_counter() - world_prepare_start

    fork_start = time.perf_counter()
    fork_result = run_snapshot_fixed_baseline_fork(
        world,
        target_node_names=(JUNCTION_NODE_NAME,),
        baseline_horizon_steps=BASELINE_HORIZON_STEPS,
    )
    fork_seconds = time.perf_counter() - fork_start

    collector = fork_result.collector

    assert fork_result.registered_visit_count == 4, (
        f"registered_visit_count={fork_result.registered_visit_count}"
    )
    assert fork_result.target_node_names == (JUNCTION_NODE_NAME,)
    assert fork_result.baseline_timestep_T == SNAPSHOT_TIMESTEP_T
    assert fork_result.configured_horizon_steps == BASELINE_HORIZON_STEPS
    assert fork_result.fork_steps_executed == BASELINE_HORIZON_STEPS
    assert (
        fork_result.final_fork_timestep
        == SNAPSHOT_TIMESTEP_T + BASELINE_HORIZON_STEPS
    )

    snapshots_by_name: dict[str, dict] = {}
    baseline_rows = []
    for spec in VEHICLE_SPECS:
        vehicle = vehicles_by_name[spec["name"]]
        snap = get_baseline_visit_snapshot(collector, vehicle)
        assert snap is not None, (
            f"No collector snapshot for {vehicle.name} visit_id="
            f"{vehicle.order_control_visit_id}"
        )
        assert snap["was_arrived_at_snapshot"] is False, (
            f"{vehicle.name}: was_arrived_at_snapshot={snap['was_arrived_at_snapshot']}"
        )
        snapshots_by_name[vehicle.name] = snap
        baseline_rows.append(snap)

    assert_arrival_order(snapshots_by_name, SNAPSHOT_TIMESTEP_T)
    assert_passage_recorded(snapshots_by_name)
    assert_expected_baseline_timesteps(snapshots_by_name)
    assert_inlink_physical_orders(fork_result)

    arrival_order = ["A", "B", "C", "D"]
    arrival_order = sorted(
        arrival_order,
        key=lambda name: snapshots_by_name[name]["baseline_arrival_timestep"],
    )
    passage_order = format_passage_order(snapshots_by_name)

    assert_real_world_unchanged_after_stage1_baseline_fork(world)
    apply_stage2_vot_settings(vehicles_by_name)
    configure_world_for_stage2_driver(world)
    assert world.T == SNAPSHOT_TIMESTEP_T

    stage2_start = time.perf_counter()
    driver_result = run_tvt_mp_driver(world)
    stage2_seconds = time.perf_counter() - stage2_start

    stage2_pipeline = trace_driver_pipeline(driver_result)
    assert_stage2_driver_results(driver_result, stage2_pipeline, world)

    total_seconds = time.perf_counter() - total_start
    timings = {
        "world_prepare": world_prepare_seconds,
        "baseline_fork": fork_seconds,
        "stage2_driver": stage2_seconds,
        "total": total_seconds,
    }

    print_report(
        world=world,
        vehicles_by_name=vehicles_by_name,
        pre_snapshot_rows=pre_snapshot_rows,
        fork_result=fork_result,
        baseline_rows=baseline_rows,
        arrival_order=arrival_order,
        passage_order=passage_order,
        timings=timings,
        prepare_breakdown=prepare_breakdown,
    )
    print_stage2_report(world, stage2_pipeline, stage2_seconds, timings)
    nonparticipating_observations = (
        build_all_candidate_nonparticipating_passage_observations(stage2_pipeline)
    )
    assert_nonparticipating_candidate_passage_observations(
        stage2_pipeline,
        nonparticipating_observations,
    )
    print_nonparticipating_candidate_passage_observation_report(
        nonparticipating_observations
    )
    stage3_pipeline, stage3_driver_seconds = run_stage3_counterexample()
    stage2_workload = collect_tvt_mp_stage_workload_summary(
        stage2_pipeline,
        stage_label="Stage 2",
    )
    stage3_workload = collect_tvt_mp_stage_workload_summary(
        stage3_pipeline,
        stage_label="Stage 3",
    )
    assert_stage2_stage3_workload_invariants(stage2_workload, stage3_workload)
    print_stage2_versus_stage3_workload_comparison(
        stage2_summary=stage2_workload,
        stage3_summary=stage3_workload,
        stage2_driver_seconds=stage2_seconds,
        stage3_driver_seconds=stage3_driver_seconds,
    )


if __name__ == "__main__":
    main()
