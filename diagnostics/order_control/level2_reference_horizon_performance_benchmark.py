# Level 2 reference model horizon sensitivity and performance benchmark.
#
# Diagnostic only — not a regression test. Run from repository root:
#   python diagnostics/order_control/level2_reference_horizon_performance_benchmark.py --quick
#   python diagnostics/order_control/level2_reference_horizon_performance_benchmark.py --full

from __future__ import annotations

import argparse
import ast
import copy
import csv
import importlib.util
import pickle
import shutil
import statistics
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from uxsim import World

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REFERENCE_MODULE_PATH = (
    _REPO_ROOT / "diagnostics" / "order_control" / "level2_virtual_world_reference.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "level2_virtual_world_reference",
    _REFERENCE_MODULE_PATH,
)
_L2_REFERENCE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_L2_REFERENCE)
estimate_level2_reference = (
    _L2_REFERENCE.estimate_order_control_batch_t_trigger_level_2_reference
)

LINK_LENGTH = 200.0
LINK_SPEED = 20.0
DELTAN = 1
SNAPSHOT_T = 10
DEFAULT_REFERENCE_HORIZON = 50
DEFAULT_MIMIC_RANDOM_SEED = 0

QUICK_SCENARIOS = ("S01", "S03", "S05", "S07", "S12", "S14")
QUICK_HORIZONS = (0, 1, 5, 10, 20, 50)
FULL_HORIZONS = (0, 1, 2, 5, 10, 20, 50)
FULL_SCENARIOS = (
    "S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10",
    "S11", "S12", "S13", "S14", "S15",
)
FULL_TIMING_API_CALL_COUNT = 15 * 7 * 12  # warm-up 1 + measured 11 per scenario×horizon

BuilderReturn = Tuple[Any, Any, List[Any], List[Any], int]


@dataclass
class ScenarioDef:
    scenario_id: str
    scenario_name: str
    scenario_group: str
    builder: Callable[[], BuilderReturn]
    expected_type_a_count: int
    expected_type_b_count: int
    expected_unarrived_count: int
    notes: str
    capacity_mode: str = "boosted"
    clearance_timesteps: int = 0
    expected_outlink_blocker_count: Optional[int] = None


@dataclass
class BuiltScenario:
    merge: Any
    trigger: Any
    tracked_vehicles: List[Any]
    semantic_vehicles: List[Any]
    t_level_1: int
    metadata: Dict[str, Any]


@dataclass
class SemanticResult:
    resolved: bool
    reason: Optional[str]
    t_virtual_trigger: Optional[int]
    t_level_2_candidate: int
    simulated_timestep_count: int
    service_stop_trace_len: int
    virtual_arrival_count: int
    virtual_outlink_choice_count: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "resolved": self.resolved,
            "reason": self.reason,
            "t_virtual_trigger": self.t_virtual_trigger,
            "t_level_2_candidate": self.t_level_2_candidate,
            "simulated_timestep_count": self.simulated_timestep_count,
            "service_stop_trace_len": self.service_stop_trace_len,
            "virtual_arrival_count": self.virtual_arrival_count,
            "virtual_outlink_choice_count": self.virtual_outlink_choice_count,
        }

    @classmethod
    def from_api(cls, result: Dict[str, Any]) -> "SemanticResult":
        return cls(
            resolved=bool(result["resolved"]),
            reason=result.get("reason"),
            t_virtual_trigger=result.get("t_virtual_trigger"),
            t_level_2_candidate=int(result["t_level_2_candidate"]),
            simulated_timestep_count=int(result["simulated_timestep_count"]),
            service_stop_trace_len=len(result["service_stop_trace"]),
            virtual_arrival_count=len(result["virtual_node_arrival_timesteps"]),
            virtual_outlink_choice_count=len(result["virtual_outlink_choices"]),
        )


def _prepare_network(W: World) -> None:
    if not getattr(W, "finalized", 0):
        W.finalize_scenario()
    for link in W.LINKS:
        link.update()


def _build_three_inlink_network(name: str, clearance: int = 0) -> World:
    W = World(
        name=name,
        deltan=DELTAN,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.set_order_control_clearance_timesteps(clearance)
    W.addNode("orig1", 0, 0)
    W.addNode("orig2", 0, 2)
    W.addNode("orig3", 0, 4)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest", 2, 1)
    W.addLink(
        "link1", "orig1", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "link2", "orig2", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "link3", "orig3", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out", "merge", "dest", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    _prepare_network(W)
    return W


def _build_multi_outlink_network(name: str, clearance: int = 0) -> World:
    W = World(
        name=name,
        deltan=DELTAN,
        tmax=200,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
        hard_deterministic_mode=True,
    )
    W.set_order_control_clearance_timesteps(clearance)
    W.addNode("orig1", 0, 0)
    W.addNode(
        "merge",
        1,
        1,
        order_control_eligible=True,
        order_control_type="batch",
    )
    W.addNode("dest1", 2, 0)
    W.addNode("dest2", 2, 2)
    W.addNode("dest3", 2, 4)
    W.addLink(
        "link1", "orig1", "merge", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out1", "merge", "dest1", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out2", "merge", "dest2", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    W.addLink(
        "out3", "merge", "dest3", length=LINK_LENGTH, free_flow_speed=LINK_SPEED,
        number_of_lanes=1,
    )
    _prepare_network(W)
    return W


def _make_vehicle(W: World, orig_name: str, name: str, dest: str = "dest") -> Any:
    return W.addVehicle(orig_name, dest, 0, name=name)


def _sync_visit(
    veh, merge, link, earliest, arrival_time, tiebreaker, batch_assignment=None
):
    if veh.order_control_visit_id == 0:
        veh.order_control_visit_id = 1
    veh.order_control_current_visit = {
        "visit_id": veh.order_control_visit_id,
        "node": merge,
        "inlink": link,
        "earliest_arrival_timestep": earliest,
        "arrival_time": arrival_time,
        "arrival_tiebreaker": tiebreaker,
        "batch_assignment": batch_assignment,
    }


def _setup_arrived(
    merge, veh, link, out_link, earliest, arrival_time, tiebreaker, x=LINK_LENGTH
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = LINK_SPEED
    veh.move_remain = 0.0
    veh.link_arrival_time = 0.0
    veh.route_next_link = out_link
    veh.order_control_earliest_arrival_timesteps[merge.name] = earliest
    veh.order_control_node_arrival_times[merge.name] = arrival_time
    veh.order_control_node_arrival_tiebreakers[merge.name] = tiebreaker
    _sync_visit(veh, merge, link, earliest, arrival_time, tiebreaker)
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    if veh not in merge.incoming_vehicles:
        merge.incoming_vehicles.append(veh)


def _setup_unarrived(
    merge,
    veh,
    link,
    earliest,
    *,
    x: float = 150.0,
    route_next_link=None,
    use_link_as_route: bool = True,
):
    veh.link = link
    veh.state = "run"
    veh.x = x
    veh.v = LINK_SPEED
    veh.move_remain = LINK_SPEED
    veh.x_old = x
    veh.x_next = x
    veh.link_arrival_time = 0.0
    if route_next_link is None and use_link_as_route:
        veh.route_next_link = link
    else:
        veh.route_next_link = route_next_link
    veh.order_control_earliest_arrival_timesteps[merge.name] = earliest
    _sync_visit(veh, merge, link, earliest, None, None)
    if veh not in link.vehicles:
        link.vehicles.append(veh)
    assert veh not in merge.incoming_vehicles


def _register_unit(merge, batch_id: int, inlink, vehicles: Sequence[Any]) -> None:
    visit_ids = []
    for veh in vehicles:
        visit = veh.order_control_current_visit
        visit["batch_assignment"] = batch_id
        veh.order_control_batch_assignments[merge.name] = batch_id
        visit_ids.append(visit["visit_id"])
    merge.order_control_batch_service_queue.append(
        {
            "batch_id": batch_id,
            "inlink": inlink,
            "vehicles": list(vehicles),
            "visit_ids": visit_ids,
        }
    )


def _boost_capacity(merge, *links) -> None:
    for link in links:
        link.capacity_in_remain = 1e6
        link.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6


def _count_types(merge, tracked: Sequence[Any]) -> Tuple[int, int, int]:
    type_a = 0
    type_b = 0
    unarrived = 0
    outlink_set = set(merge.outlinks.values())
    for veh in tracked:
        if veh not in merge.incoming_vehicles:
            unarrived += 1
        rnl = veh.route_next_link
        if rnl is not None and rnl in outlink_set:
            type_a += 1
        elif rnl is None or rnl is veh.link:
            type_b += 1
    return type_a, type_b, unarrived


def _outlink_blocker_count(
    tracked: Sequence[Any], semantic: Sequence[Any]
) -> int:
    semantic_ids = {id(veh) for veh in semantic}
    return sum(1 for veh in tracked if id(veh) not in semantic_ids)


def _scenario_metadata(
    merge,
    tracked: Sequence[Any],
    semantic: Sequence[Any],
    clearance: int,
    capacity_mode: str,
) -> Dict[str, Any]:
    queue_vehicle_count = sum(len(u["vehicles"]) for u in merge.order_control_batch_service_queue)
    service_unit_count = len(merge.order_control_batch_service_queue)
    type_a, type_b, unarrived = _count_types(merge, semantic)
    unarrived_x = [
        veh.x for veh in semantic
        if veh not in merge.incoming_vehicles
    ]
    trigger = semantic[-1] if semantic else (tracked[-1] if tracked else None)
    return {
        "snapshot_timestep": int(merge.W.T),
        "queue_vehicle_count": queue_vehicle_count,
        "service_unit_count": service_unit_count,
        "inlink_count": len(merge.inlinks),
        "outlink_count": len(merge.outlinks),
        "type_a_count": type_a,
        "type_b_count": type_b,
        "unarrived_count": unarrived,
        "outlink_blocker_count": _outlink_blocker_count(tracked, semantic),
        "unarrived_min_x": min(unarrived_x) if unarrived_x else None,
        "unarrived_max_x": max(unarrived_x) if unarrived_x else None,
        "clearance_timesteps": clearance,
        "capacity_mode": capacity_mode,
        "trigger_inlink": trigger.link.name if trigger is not None else None,
        "trigger_name": trigger.name if trigger is not None else None,
    }


def _snapshot_world_state(merge, vehicles: Sequence[Any]) -> Dict[str, Any]:
    return {
        "W_T": merge.W.T,
        "service_queue": [
            {
                "batch_id": unit["batch_id"],
                "inlink": unit["inlink"].name,
                "vehicles": [veh.name for veh in unit["vehicles"]],
                "visit_ids": list(unit["visit_ids"]),
            }
            for unit in merge.order_control_batch_service_queue
        ],
        "last_inlink": (
            merge.last_order_control_inlink.name
            if merge.last_order_control_inlink is not None
            else None
        ),
        "last_entry": merge.last_order_control_entry_timestep,
        "next_id": merge.order_control_batch_next_id,
        "flow_capacity_remain": merge.flow_capacity_remain,
        "rng_state": copy.deepcopy(merge.W.rng.bit_generator.state),
        "vehicles": {
            veh.name: {
                "state": veh.state,
                "link": veh.link.name if veh.link is not None else None,
                "x": veh.x,
                "v": veh.v,
                "route_next_link": (
                    veh.route_next_link.name
                    if veh.route_next_link is not None
                    else None
                ),
                "assignment": copy.copy(veh.order_control_batch_assignments),
                "visit": (
                    None
                    if veh.order_control_current_visit is None
                    else {
                        "visit_id": veh.order_control_current_visit["visit_id"],
                        "node": veh.order_control_current_visit["node"].name,
                        "inlink": veh.order_control_current_visit["inlink"].name,
                        "earliest_arrival_timestep": veh.order_control_current_visit[
                            "earliest_arrival_timestep"
                        ],
                        "arrival_time": veh.order_control_current_visit.get("arrival_time"),
                        "arrival_tiebreaker": veh.order_control_current_visit.get(
                            "arrival_tiebreaker"
                        ),
                        "batch_assignment": veh.order_control_current_visit.get(
                            "batch_assignment"
                        ),
                    }
                ),
            }
            for veh in vehicles
        },
        "incoming_vehicles": [veh.name for veh in merge.incoming_vehicles],
        "link_vehicles": {
            link.name: [veh.name for veh in link.vehicles]
            for link in list(merge.inlinks.values()) + list(merge.outlinks.values())
        },
        "capacity": {
            link.name: {
                "capacity_in_remain": link.capacity_in_remain,
                "capacity_out_remain": link.capacity_out_remain,
            }
            for link in list(merge.inlinks.values()) + list(merge.outlinks.values())
        },
    }


def _assert_world_unchanged(before: Dict[str, Any], after: Dict[str, Any]) -> None:
    for key in (
        "W_T", "service_queue", "last_inlink", "last_entry", "next_id",
        "flow_capacity_remain", "rng_state", "vehicles", "incoming_vehicles",
        "link_vehicles", "capacity",
    ):
        if before[key] != after[key]:
            raise ValueError(f"real World snapshot mismatch on key {key!r}")


def _percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_v = sorted(values)
    k = (p / 100.0) * (len(sorted_v) - 1)
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return float(sorted_v[f])
    return float(sorted_v[f] + (k - f) * (sorted_v[c] - sorted_v[f]))


def _run_api_timed(merge, trigger, t_level_1: int, virtual_horizon: int) -> Tuple[float, SemanticResult]:
    start = time.perf_counter()
    result = estimate_level2_reference(
        merge,
        trigger,
        t_level_1,
        virtual_horizon,
        mimic_random_seed=DEFAULT_MIMIC_RANDOM_SEED,
    )
    elapsed = time.perf_counter() - start
    return elapsed, SemanticResult.from_api(result)


def _run_api_semantic(merge, trigger, t_level_1: int, virtual_horizon: int) -> SemanticResult:
    result = estimate_level2_reference(
        merge,
        trigger,
        t_level_1,
        virtual_horizon,
        mimic_random_seed=DEFAULT_MIMIC_RANDOM_SEED,
    )
    return SemanticResult.from_api(result)


# --- Scenario builders (return merge, trigger, tracked, semantic, t_level_1) ---


def _build_s01() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s01", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = [trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s02() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s02", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(
        merge, a1, link1, 0, x=199.0, route_next_link=out, use_link_as_route=False
    )
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = 10
    tracked = [a1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s03() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s03", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(
        merge, a1, link1, 0, x=150.0, route_next_link=out, use_link_as_route=False
    )
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = 10
    tracked = [a1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s04() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s04", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(
        merge, a1, link1, 0, x=50.0, route_next_link=out, use_link_as_route=False
    )
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = 10
    tracked = [a1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s05() -> BuilderReturn:
    W = _build_multi_outlink_network("bench_s05", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest2")
    _setup_unarrived(
        merge, a1, link1, 0, x=199.0, route_next_link=None, use_link_as_route=False
    )
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    link1.vehicles = deque([a1, trigger])
    merge.incoming_vehicles = [trigger]
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, out1, out2, out3)
    t_level_1 = 10
    tracked = [a1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s06() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s06", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = [a1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s07() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s07", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    vehicles = [_make_vehicle(W, "orig1", f"A{i}") for i in range(1, 6)]
    trigger = _make_vehicle(W, "orig2", "TRIG")
    for i, veh in enumerate(vehicles):
        _setup_arrived(
            merge, veh, link1, out, 0, 10.0 + i * 0.1, 0.1 + i * 0.01,
            x=LINK_LENGTH - i * 0.5,
        )
    link1.vehicles = deque(vehicles)
    merge.incoming_vehicles = list(vehicles)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, vehicles)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = list(vehicles) + [trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s08() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s08", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    a_vehicles = [_make_vehicle(W, "orig1", f"A{i}") for i in range(1, 6)]
    b_vehicles = [_make_vehicle(W, "orig2", f"B{i}") for i in range(1, 6)]
    trigger = _make_vehicle(W, "orig3", "TRIG")
    for i, veh in enumerate(a_vehicles):
        _setup_arrived(merge, veh, link1, out, 0, 10.0 + i * 0.1, 0.1 + i * 0.01)
    link1.vehicles = deque(a_vehicles)
    for i, veh in enumerate(b_vehicles):
        _setup_arrived(merge, veh, link2, out, 0, 11.0 + i * 0.1, 0.2 + i * 0.01)
    link2.vehicles = deque(b_vehicles)
    _setup_arrived(merge, trigger, link3, out, 0, 12.0, 0.3)
    merge.incoming_vehicles = a_vehicles + b_vehicles + [trigger]
    _register_unit(merge, 0, link1, a_vehicles)
    _register_unit(merge, 1, link2, b_vehicles)
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, link3, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = a_vehicles + b_vehicles + [trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s09() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s09", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    all_queue: List[Any] = []
    unit_vehicles: List[List[Any]] = []
    for unit_idx, inlink_name, orig in [
        (0, "link1", "orig1"),
        (1, "link2", "orig2"),
        (2, "link3", "orig3"),
        (3, "link1", "orig1"),
        (4, "link2", "orig2"),
    ]:
        inlink = W.get_link(inlink_name)
        vehicles = [_make_vehicle(W, orig, f"U{unit_idx}V{i}") for i in range(1, 5)]
        for i, veh in enumerate(vehicles):
            _setup_arrived(
                merge, veh, inlink, out, 0, 10.0 + unit_idx + i * 0.05, 0.1 + i * 0.01
            )
        inlink.vehicles = deque(list(inlink.vehicles) + vehicles)
        unit_vehicles.append(vehicles)
        all_queue.extend(vehicles)
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, trigger, link3, out, 0, 20.0, 0.9)
    merge.incoming_vehicles = all_queue + [trigger]
    for batch_id, inlink_name, vehicles in zip(
        range(5),
        ["link1", "link2", "link3", "link1", "link2"],
        unit_vehicles,
    ):
        _register_unit(merge, batch_id, W.get_link(inlink_name), vehicles)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, link3, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = all_queue + [trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s10() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s10", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    unarrived = [
        _make_vehicle(W, "orig1", f"U{i}") for i in range(1, 6)
    ]
    for i, veh in enumerate(unarrived):
        _setup_unarrived(
            merge, veh, link1, 0, x=150.0 - i * 0.5,
            route_next_link=out, use_link_as_route=False,
        )
    link1.vehicles = deque(unarrived)
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, unarrived)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = 10
    tracked = unarrived + [trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s11() -> BuilderReturn:
    W = _build_multi_outlink_network("bench_s11", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    out1 = W.get_link("out1")
    out2 = W.get_link("out2")
    out3 = W.get_link("out3")
    a1 = _make_vehicle(W, "orig1", "A1", dest="dest1")
    b1 = _make_vehicle(W, "orig1", "B1", dest="dest2")
    trigger = _make_vehicle(W, "orig1", "TRIG", dest="dest3")
    _setup_arrived(merge, a1, link1, out1, 0, 10.0, 0.1)
    _setup_unarrived(merge, b1, link1, 0, x=199.0)
    link1.vehicles = deque([a1, b1])
    _setup_arrived(merge, trigger, link1, out2, 0, 12.0, 0.2)
    trigger.link = link1
    merge.incoming_vehicles = [a1, trigger]
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link1, [b1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, out1, out2, out3)
    t_level_1 = 10
    tracked = [a1, b1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s12() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s12", clearance=0)
    merge = W.get_node("merge")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    blocker = _make_vehicle(W, "orig1", "BLOCK")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    blocker.link = out
    blocker.state = "run"
    blocker.x = 0.0
    blocker.v = 0.0
    blocker.x_old = 0.0
    blocker.x_next = 0.0
    blocker.link_arrival_time = 0.0
    blocker.route_next_link = None
    out.vehicles.append(blocker)
    W.VEHICLES_RUNNING[blocker.name] = blocker
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    out.capacity_in_remain = 1e6
    link2.capacity_out_remain = 1e6
    merge.flow_capacity_remain = 1e6
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = [blocker, trigger]
    semantic = [trigger]
    return merge, trigger, tracked, semantic, t_level_1


def _build_s13() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s13", clearance=1)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    link3 = W.get_link("link3")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    b1 = _make_vehicle(W, "orig2", "B1")
    trigger = _make_vehicle(W, "orig3", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, b1, link2, out, 0, 11.0, 0.2)
    _setup_arrived(merge, trigger, link3, out, 0, 12.0, 0.3)
    _register_unit(merge, 0, link1, [a1])
    _register_unit(merge, 1, link2, [b1])
    merge.last_order_control_inlink = link1
    merge.last_order_control_entry_timestep = 9
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, link3, out)
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = [a1, b1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s14() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s14", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_arrived(merge, a1, link1, out, 0, 10.0, 0.1)
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    link1.capacity_out_remain = 0.0
    link2.capacity_out_remain = 0.0
    out.capacity_in_remain = 1e6
    merge.flow_capacity_remain = 1e6
    t_level_1 = merge.estimate_order_control_batch_t_trigger_level_1(trigger)
    tracked = [a1, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_s15() -> BuilderReturn:
    W = _build_three_inlink_network("bench_s15", clearance=0)
    merge = W.get_node("merge")
    link1 = W.get_link("link1")
    link2 = W.get_link("link2")
    out = W.get_link("out")
    a1 = _make_vehicle(W, "orig1", "A1")
    a2 = _make_vehicle(W, "orig1", "A2")
    a3 = _make_vehicle(W, "orig1", "A3")
    trigger = _make_vehicle(W, "orig2", "TRIG")
    _setup_unarrived(
        merge, a1, link1, 0, x=50.0, route_next_link=out, use_link_as_route=False
    )
    _setup_unarrived(
        merge, a2, link1, 0, x=40.0, route_next_link=out, use_link_as_route=False
    )
    _setup_unarrived(
        merge, a3, link1, 0, x=30.0, route_next_link=out, use_link_as_route=False
    )
    link1.vehicles = deque([a1, a2, a3])
    _setup_arrived(merge, trigger, link2, out, 0, 12.0, 0.2)
    _register_unit(merge, 0, link1, [a1, a2, a3])
    merge.last_order_control_inlink = None
    merge.last_order_control_entry_timestep = None
    W.T = SNAPSHOT_T
    _boost_capacity(merge, link1, link2, out)
    t_level_1 = 10
    tracked = [a1, a2, a3, trigger]
    return merge, trigger, tracked, tracked, t_level_1


def _build_scenario(defn: ScenarioDef) -> BuiltScenario:
    merge, trigger, tracked, semantic, t_level_1 = defn.builder()
    meta = _scenario_metadata(
        merge, tracked, semantic, defn.clearance_timesteps, defn.capacity_mode
    )
    return BuiltScenario(
        merge=merge,
        trigger=trigger,
        tracked_vehicles=list(tracked),
        semantic_vehicles=list(semantic),
        t_level_1=t_level_1,
        metadata=meta,
    )


def _get_scenario_registry() -> Dict[str, ScenarioDef]:
    return {
        "S01": ScenarioDef(
            "S01", "arrived_trigger_baseline", "G1", _build_s01,
            1, 0, 0, "Trigger only, no service unit; early resolved exit",
            capacity_mode="boosted",
        ),
        "S02": ScenarioDef(
            "S02", "unarrived_near_x199", "G3", _build_s02,
            2, 0, 1, "Near node end unarrived Type A",
        ),
        "S03": ScenarioDef(
            "S03", "unarrived_mid_x150_type_a", "G1", _build_s03,
            2, 0, 1, "Mid-distance unarrived Type A",
        ),
        "S04": ScenarioDef(
            "S04", "unarrived_far_x50", "G3", _build_s04,
            2, 0, 1, "Far unarrived Type A",
        ),
        "S05": ScenarioDef(
            "S05", "type_b_unarrived_multi_outlink", "G1", _build_s05,
            1, 1, 1, "Type B unarrived with modulo outlink choice",
        ),
        "S06": ScenarioDef(
            "S06", "one_vehicle_one_unit_arrived", "G2", _build_s06,
            2, 0, 0, "Single unit single vehicle arrived",
        ),
        "S07": ScenarioDef(
            "S07", "five_vehicles_one_unit_arrived", "G2", _build_s07,
            6, 0, 0, "Five vehicles in one service unit",
        ),
        "S08": ScenarioDef(
            "S08", "ten_vehicles_two_units", "G2", _build_s08,
            11, 0, 0, "Ten vehicles in two units (5 each)",
        ),
        "S09": ScenarioDef(
            "S09", "twenty_vehicles_five_units", "G2", _build_s09,
            21, 0, 0, "Twenty vehicles in five units",
        ),
        "S10": ScenarioDef(
            "S10", "five_unarrived_one_unit", "G2", _build_s10,
            6, 0, 5, "Five unarrived in one unit at x~150",
        ),
        "S11": ScenarioDef(
            "S11", "type_a_type_b_mixed", "G2", _build_s11,
            2, 1, 1, "Type A arrived + Type B unarrived",
        ),
        "S12": ScenarioDef(
            "S12", "outlink_entrance_recovery", "G3", _build_s12,
            1, 0, 0, "Outlink entrance space recovery wait",
            capacity_mode="outlink_blocked",
            expected_outlink_blocker_count=1,
        ),
        "S13": ScenarioDef(
            "S13", "clearance_long_wait", "G3", _build_s13,
            3, 0, 0, "Clearance=1 long wait to T~14",
            clearance_timesteps=1,
        ),
        "S14": ScenarioDef(
            "S14", "capacity_refill_wait", "G3", _build_s14,
            2, 0, 0, "Offset=0 capacity-out depleted; refill at offset>=1",
            capacity_mode="depleted_offset0",
        ),
        "S15": ScenarioDef(
            "S15", "multiple_far_unarrived_queue", "G3", _build_s15,
            4, 0, 3, "Multiple far unarrived in one service unit",
        ),
    }


def _self_check_scenario(
    defn: ScenarioDef,
    horizons: Sequence[int],
    reference_horizon: int,
) -> Tuple[SemanticResult, Dict[int, SemanticResult]]:
    built = _build_scenario(defn)
    merge, trigger, tracked, t_level_1 = (
        built.merge, built.trigger, built.tracked_vehicles, built.t_level_1
    )
    meta = built.metadata

    if meta["queue_vehicle_count"] != sum(
        len(u["vehicles"]) for u in merge.order_control_batch_service_queue
    ):
        raise ValueError(f"{defn.scenario_id}: queue_vehicle_count mismatch")
    if meta["service_unit_count"] != len(merge.order_control_batch_service_queue):
        raise ValueError(f"{defn.scenario_id}: service_unit_count mismatch")
    if meta["type_a_count"] != defn.expected_type_a_count:
        raise ValueError(
            f"{defn.scenario_id}: type_a_count {meta['type_a_count']} "
            f"!= expected {defn.expected_type_a_count}"
        )
    if meta["type_b_count"] != defn.expected_type_b_count:
        raise ValueError(
            f"{defn.scenario_id}: type_b_count {meta['type_b_count']} "
            f"!= expected {defn.expected_type_b_count}"
        )
    if meta["unarrived_count"] != defn.expected_unarrived_count:
        raise ValueError(
            f"{defn.scenario_id}: unarrived_count {meta['unarrived_count']} "
            f"!= expected {defn.expected_unarrived_count}"
        )
    if defn.expected_outlink_blocker_count is not None:
        if meta["outlink_blocker_count"] != defn.expected_outlink_blocker_count:
            raise ValueError(
                f"{defn.scenario_id}: outlink_blocker_count "
                f"{meta['outlink_blocker_count']} != expected "
                f"{defn.expected_outlink_blocker_count}"
            )

    before_rng = pickle.dumps(merge.W.rng.bit_generator.state)
    before_snap = _snapshot_world_state(merge, tracked)
    ref_sem = _run_api_semantic(merge, trigger, t_level_1, reference_horizon)
    after_snap = _snapshot_world_state(merge, tracked)
    after_rng = pickle.dumps(merge.W.rng.bit_generator.state)
    _assert_world_unchanged(before_snap, after_snap)
    if before_rng != after_rng:
        raise ValueError(f"{defn.scenario_id}: RNG state changed after reference call")

    horizon_results: Dict[int, SemanticResult] = {}
    resolved_tvt: Optional[int] = None
    for h in sorted(horizons):
        built_h = _build_scenario(defn)
        m, tr, trk, tl1 = (
            built_h.merge, built_h.trigger, built_h.tracked_vehicles, built_h.t_level_1
        )
        b_snap = _snapshot_world_state(m, trk)
        b_rng = pickle.dumps(m.W.rng.bit_generator.state)
        sem1 = _run_api_semantic(m, tr, tl1, h)
        a_snap = _snapshot_world_state(m, trk)
        a_rng = pickle.dumps(m.W.rng.bit_generator.state)
        _assert_world_unchanged(b_snap, a_snap)
        if b_rng != a_rng:
            raise ValueError(f"{defn.scenario_id}: RNG changed at horizon {h}")

        built_h2 = _build_scenario(defn)
        sem2 = _run_api_semantic(
            built_h2.merge, built_h2.trigger, built_h2.t_level_1, h
        )
        if sem1.as_dict() != sem2.as_dict():
            raise ValueError(
                f"{defn.scenario_id}: determinism failed at horizon {h}"
            )
        horizon_results[h] = sem1

        if sem1.resolved:
            if resolved_tvt is None:
                resolved_tvt = sem1.t_virtual_trigger
            else:
                if not sem1.resolved:
                    raise ValueError(
                        f"{defn.scenario_id}: resolved became False at horizon {h}"
                    )
                if sem1.t_virtual_trigger != resolved_tvt:
                    raise ValueError(
                        f"{defn.scenario_id}: t_virtual_trigger changed at horizon {h}"
                    )
        elif resolved_tvt is not None:
            raise ValueError(
                f"{defn.scenario_id}: resolved became False after True at horizon {h}"
            )

    if defn.scenario_id == "S05" and ref_sem.virtual_outlink_choice_count < 1:
        raise ValueError("S05: expected virtual_outlink_choice_count >= 1 at reference")

    return ref_sem, horizon_results


RAW_CSV_COLUMNS = [
    "scenario_id", "scenario_name", "scenario_group", "repeat_index", "is_warmup",
    "virtual_horizon", "reference_horizon", "snapshot_timestep", "t_level_1",
    "queue_vehicle_count", "service_unit_count", "inlink_count", "outlink_count",
    "type_a_count", "type_b_count", "unarrived_count", "outlink_blocker_count",
    "unarrived_min_x",
    "unarrived_max_x", "clearance_timesteps", "capacity_mode", "trigger_inlink",
    "trigger_name", "mimic_random_seed", "elapsed_seconds", "resolved", "reason",
    "t_virtual_trigger", "t_level_2_candidate", "simulated_timestep_count",
    "service_stop_trace_len", "virtual_arrival_count", "virtual_outlink_choice_count",
]

SEMANTIC_CSV_COLUMNS = [
    "scenario_id", "scenario_name", "scenario_group", "virtual_horizon",
    "reference_horizon", "resolved", "reason", "t_virtual_trigger",
    "t_level_2_candidate", "simulated_timestep_count", "service_stop_trace_len",
    "virtual_arrival_count", "virtual_outlink_choice_count",
    "resolved_at_reference", "reference_t_virtual_trigger",
    "matches_reference_horizon", "minimum_resolving_horizon",
    "t_virtual_trigger_stable_after_resolution",
]

TIMING_SUMMARY_COLUMNS = [
    "scenario_id", "scenario_name", "scenario_group", "virtual_horizon",
    "measured_repeat_count", "elapsed_median", "elapsed_min", "elapsed_max",
    "elapsed_mean", "elapsed_p90", "resolved", "t_virtual_trigger",
    "simulated_timestep_count",
]

HORIZON_SUMMARY_COLUMNS = [
    "virtual_horizon", "scenario_count", "resolved_scenario_count",
    "resolved_fraction", "reference_match_count", "reference_match_fraction",
    "median_of_scenario_medians", "max_scenario_median", "unresolved_scenarios",
]


def _compute_scenario_semantic_summary(
    sid: str,
    horizons: Sequence[int],
    semantic_by_scenario_horizon: Dict[Tuple[str, int], SemanticResult],
    ref_sem: SemanticResult,
) -> Tuple[Optional[int], Optional[bool]]:
    min_resolving: Optional[int] = None
    for h in sorted(horizons):
        if semantic_by_scenario_horizon[(sid, h)].resolved:
            min_resolving = h
            break

    if not ref_sem.resolved:
        return None, None

    stable_after = True
    last_tvt: Optional[int] = None
    for h in sorted(horizons):
        sem = semantic_by_scenario_horizon[(sid, h)]
        if sem.resolved:
            if last_tvt is not None and sem.t_virtual_trigger != last_tvt:
                stable_after = False
            last_tvt = sem.t_virtual_trigger
    return min_resolving, stable_after


def _write_csv(path: Path, columns: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _run_benchmark(
    mode: str,
    scenarios: Sequence[str],
    horizons: Sequence[int],
    reference_horizon: int,
    repeats: int,
    output_dir: Path,
) -> Dict[str, Any]:
    registry = _get_scenario_registry()
    warmup_count = 1
    total_start = time.perf_counter()
    self_check_api_calls = 0
    timing_api_calls = 0

    raw_rows: List[Dict[str, Any]] = []
    semantic_rows: List[Dict[str, Any]] = []
    timing_summary_rows: List[Dict[str, Any]] = []
    reference_results: Dict[str, SemanticResult] = {}
    semantic_by_scenario_horizon: Dict[Tuple[str, int], SemanticResult] = {}
    timing_elapsed: Dict[Tuple[str, int], List[float]] = {}

    print(f"=== Level 2 reference horizon benchmark ({mode}) ===")
    print(f"Scenarios: {', '.join(scenarios)}")
    print(f"Horizons: {list(horizons)}")
    print(f"Reference horizon: {reference_horizon}")
    print(f"Warm-up per scenario×horizon: {warmup_count}")
    print(f"Measured repeats: {repeats}")

    for sid in scenarios:
        defn = registry[sid]
        print(f"Self-check: {sid} ...")
        ref_sem, horizon_sem = _self_check_scenario(defn, horizons, reference_horizon)
        reference_results[sid] = ref_sem
        self_check_api_calls += 1 + len(horizons) + len(horizons)  # ref + horizons + determinism rebuild

        for h, sem in horizon_sem.items():
            semantic_by_scenario_horizon[(sid, h)] = sem

        for h in horizons:
            timing_elapsed[(sid, h)] = []
            for repeat_idx in range(warmup_count + repeats):
                is_warmup = repeat_idx < warmup_count
                built = _build_scenario(defn)
                merge, trigger, tracked, t_level_1 = (
                    built.merge, built.trigger, built.tracked_vehicles, built.t_level_1
                )
                meta = built.metadata
                elapsed, sem = _run_api_timed(merge, trigger, t_level_1, h)
                timing_api_calls += 1

                row = {
                    **meta,
                    "scenario_id": sid,
                    "scenario_name": defn.scenario_name,
                    "scenario_group": defn.scenario_group,
                    "repeat_index": repeat_idx,
                    "is_warmup": is_warmup,
                    "virtual_horizon": h,
                    "reference_horizon": reference_horizon,
                    "t_level_1": t_level_1,
                    "mimic_random_seed": DEFAULT_MIMIC_RANDOM_SEED,
                    "elapsed_seconds": elapsed,
                    **sem.as_dict(),
                }
                raw_rows.append(row)
                if not is_warmup:
                    timing_elapsed[(sid, h)].append(elapsed)

    # Semantic summary rows
    for sid in scenarios:
        defn = registry[sid]
        ref_sem = reference_results[sid]
        ref_resolved = ref_sem.resolved
        ref_tvt = ref_sem.t_virtual_trigger
        min_resolving, stable_after = _compute_scenario_semantic_summary(
            sid, horizons, semantic_by_scenario_horizon, ref_sem
        )
        for h in sorted(horizons):
            sem = semantic_by_scenario_horizon[(sid, h)]
            matches = None
            if ref_resolved and sem.resolved:
                matches = sem.t_virtual_trigger == ref_tvt
            elif not ref_resolved:
                matches = None
            semantic_rows.append({
                "scenario_id": sid,
                "scenario_name": defn.scenario_name,
                "scenario_group": defn.scenario_group,
                "virtual_horizon": h,
                "reference_horizon": reference_horizon,
                **sem.as_dict(),
                "resolved_at_reference": ref_resolved,
                "reference_t_virtual_trigger": ref_tvt,
                "matches_reference_horizon": matches,
                "minimum_resolving_horizon": min_resolving,
                "t_virtual_trigger_stable_after_resolution": stable_after,
            })

    # Timing summary
    for sid in scenarios:
        defn = registry[sid]
        for h in horizons:
            elapsed_list = timing_elapsed[(sid, h)]
            sem = semantic_by_scenario_horizon[(sid, h)]
            timing_summary_rows.append({
                "scenario_id": sid,
                "scenario_name": defn.scenario_name,
                "scenario_group": defn.scenario_group,
                "virtual_horizon": h,
                "measured_repeat_count": len(elapsed_list),
                "elapsed_median": statistics.median(elapsed_list),
                "elapsed_min": min(elapsed_list),
                "elapsed_max": max(elapsed_list),
                "elapsed_mean": statistics.mean(elapsed_list),
                "elapsed_p90": _percentile(elapsed_list, 90),
                "resolved": sem.resolved,
                "t_virtual_trigger": sem.t_virtual_trigger,
                "simulated_timestep_count": sem.simulated_timestep_count,
            })

    # Horizon summary
    horizon_summary_rows: List[Dict[str, Any]] = []
    for h in horizons:
        resolved_count = sum(
            1 for sid in scenarios
            if semantic_by_scenario_horizon[(sid, h)].resolved
        )
        ref_match_count = 0
        ref_match_eligible = 0
        medians: List[float] = []
        unresolved_list: List[str] = []
        for sid in scenarios:
            sem = semantic_by_scenario_horizon[(sid, h)]
            ref_sem = reference_results[sid]
            if not sem.resolved:
                unresolved_list.append(sid)
            if ref_sem.resolved:
                ref_match_eligible += 1
                if sem.resolved and sem.t_virtual_trigger == ref_sem.t_virtual_trigger:
                    ref_match_count += 1
            medians.append(statistics.median(timing_elapsed[(sid, h)]))
        horizon_summary_rows.append({
            "virtual_horizon": h,
            "scenario_count": len(scenarios),
            "resolved_scenario_count": resolved_count,
            "resolved_fraction": resolved_count / len(scenarios),
            "reference_match_count": ref_match_count,
            "reference_match_fraction": (
                ref_match_count / ref_match_eligible if ref_match_eligible else None
            ),
            "median_of_scenario_medians": statistics.median(medians),
            "max_scenario_median": max(medians),
            "unresolved_scenarios": ",".join(unresolved_list),
        })

    prefix = f"level2_ref_horizon_{mode}"
    raw_path = output_dir / f"{prefix}_raw_timing.csv"
    semantic_path = output_dir / f"{prefix}_semantic_summary.csv"
    timing_path = output_dir / f"{prefix}_timing_summary.csv"
    horizon_path = output_dir / f"{prefix}_horizon_summary.csv"

    _write_csv(raw_path, RAW_CSV_COLUMNS, raw_rows)
    _write_csv(semantic_path, SEMANTIC_CSV_COLUMNS, semantic_rows)
    _write_csv(timing_path, TIMING_SUMMARY_COLUMNS, timing_summary_rows)
    _write_csv(horizon_path, HORIZON_SUMMARY_COLUMNS, horizon_summary_rows)

    total_elapsed = time.perf_counter() - total_start

    # Console summary
    print()
    print(f"Total elapsed (including self-check): {total_elapsed:.2f} s")
    print(f"Self-check API calls (approx): {self_check_api_calls}")
    print(f"Timing API calls: {timing_api_calls}")
    print(f"Raw CSV: {raw_path}")
    print(f"Semantic CSV: {semantic_path}")
    print(f"Timing summary CSV: {timing_path}")
    print(f"Horizon summary CSV: {horizon_path}")
    print()
    print("Scenario × horizon (semantic + median ms):")
    for sid in scenarios:
        for h in horizons:
            sem = semantic_by_scenario_horizon[(sid, h)]
            med = statistics.median(timing_elapsed[(sid, h)])
            ref_sem = reference_results[sid]
            match = ""
            if ref_sem.resolved and sem.resolved:
                match = "ref_match" if sem.t_virtual_trigger == ref_sem.t_virtual_trigger else "ref_DIFF"
            print(
                f"  {sid} h={h}: resolved={sem.resolved} "
                f"t_vt={sem.t_virtual_trigger} sim_steps={sem.simulated_timestep_count} "
                f"median_ms={med*1000:.2f} {match}"
            )

    print()
    print("Horizon summary:")
    for row in horizon_summary_rows:
        print(
            f"  h={row['virtual_horizon']}: resolved={row['resolved_scenario_count']}/"
            f"{row['scenario_count']} "
            f"({row['resolved_fraction']:.2%}) "
            f"median_of_medians_ms={row['median_of_scenario_medians']*1000:.2f} "
            f"max_median_ms={row['max_scenario_median']*1000:.2f}"
        )
        if row["unresolved_scenarios"]:
            print(f"    unresolved: {row['unresolved_scenarios']}")

    measured_timing_rows = len(scenarios) * len(horizons) * repeats
    timing_api_elapsed_total = sum(row["elapsed_seconds"] for row in raw_rows)
    timing_api_elapsed_mean = timing_api_elapsed_total / max(timing_api_calls, 1)
    quick_non_timing_elapsed = total_elapsed - timing_api_elapsed_total
    quick_timing_calls = timing_api_calls
    full_pure_timing_estimate = timing_api_elapsed_mean * FULL_TIMING_API_CALL_COUNT
    work_ratio = FULL_TIMING_API_CALL_COUNT / max(quick_timing_calls, 1)
    full_end_to_end_estimate = full_pure_timing_estimate + quick_non_timing_elapsed * work_ratio
    print()
    print("Full mode time estimate (approximate):")
    print(f"  quick total elapsed: {total_elapsed:.2f} s")
    print(f"  quick timing API elapsed total: {timing_api_elapsed_total:.2f} s")
    print(f"  quick non-timing elapsed: {quick_non_timing_elapsed:.2f} s")
    print(f"  timing API call mean: {timing_api_elapsed_mean*1000:.2f} ms")
    print(f"  quick measured timing rows: {measured_timing_rows}")
    print(f"  full timing API call count: {FULL_TIMING_API_CALL_COUNT}")
    print(f"  full pure timing estimate: {full_pure_timing_estimate:.1f} s")
    print(f"  full end-to-end proportional estimate: {full_end_to_end_estimate:.1f} s")
    print(f"  full 2x safety estimate: {full_end_to_end_estimate*2:.1f} s")
    print(f"  full 3x safety estimate: {full_end_to_end_estimate*3:.1f} s")
    if repeats <= 3:
        print("  (p90 with few repeats is indicative only)")

    return {
        "mode": mode,
        "raw_path": raw_path,
        "semantic_path": semantic_path,
        "timing_path": timing_path,
        "horizon_path": horizon_path,
        "raw_row_count": len(raw_rows),
        "semantic_row_count": len(semantic_rows),
        "timing_summary_row_count": len(timing_summary_rows),
        "horizon_summary_row_count": len(horizon_summary_rows),
        "timing_api_calls": timing_api_calls,
        "self_check_api_calls": self_check_api_calls,
        "total_elapsed": total_elapsed,
        "timing_api_elapsed_total": timing_api_elapsed_total,
        "quick_non_timing_elapsed": quick_non_timing_elapsed,
        "timing_api_elapsed_mean": timing_api_elapsed_mean,
        "measured_timing_rows": measured_timing_rows,
        "full_pure_timing_estimate": full_pure_timing_estimate,
        "full_end_to_end_estimate": full_end_to_end_estimate,
    }


def _parse_horizons(text: str) -> Tuple[int, ...]:
    parts = [x.strip() for x in text.split(",") if x.strip()]
    if not parts:
        raise ValueError("empty horizons list")
    return tuple(int(x) for x in parts)


def _copy_benchmark_csv(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.resolve() == destination.resolve():
        return

    shutil.copy2(source, destination)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Level 2 reference horizon performance benchmark",
    )
    parser.add_argument("--quick", action="store_true", help="Quick mode (6 scenarios)")
    parser.add_argument("--full", action="store_true", help="Full small-benchmark mode")
    parser.add_argument("--output-dir", type=Path, default=None, help="CSV output directory")
    parser.add_argument("--raw-csv", type=Path, default=None)
    parser.add_argument("--semantic-csv", type=Path, default=None)
    parser.add_argument("--timing-summary-csv", type=Path, default=None)
    parser.add_argument("--horizons", type=str, default=None, help="Comma-separated horizons")
    parser.add_argument("--repeats", type=int, default=None, help="Measured repeats (excludes warm-up)")
    parser.add_argument("--reference-horizon", type=int, default=DEFAULT_REFERENCE_HORIZON)
    args = parser.parse_args(argv)

    if args.quick and args.full:
        print("Error: --quick and --full cannot be used together", file=sys.stderr)
        return 2

    if args.full:
        mode = "full"
        scenarios = FULL_SCENARIOS
        horizons = FULL_HORIZONS
        default_repeats = 11
    else:
        mode = "quick"
        scenarios = QUICK_SCENARIOS
        horizons = QUICK_HORIZONS
        default_repeats = 5

    if args.horizons is not None:
        try:
            horizons = _parse_horizons(args.horizons)
        except ValueError as exc:
            print(f"Error: invalid --horizons: {exc}", file=sys.stderr)
            return 2
    if not horizons:
        print("Error: --horizons must not be empty", file=sys.stderr)
        return 2
    if any(h < 0 for h in horizons):
        print("Error: --horizons values must be >= 0", file=sys.stderr)
        return 2

    repeats = args.repeats if args.repeats is not None else default_repeats
    if repeats < 1:
        print("Error: --repeats must be >= 1", file=sys.stderr)
        return 2
    if args.reference_horizon < 0:
        print("Error: --reference-horizon must be >= 0", file=sys.stderr)
        return 2

    if args.output_dir is not None:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="level2_ref_horizon_benchmark_"))

    result = _run_benchmark(
        mode=mode,
        scenarios=scenarios,
        horizons=horizons,
        reference_horizon=args.reference_horizon,
        repeats=repeats,
        output_dir=output_dir,
    )
    print(f"Benchmark output directory: {output_dir}")

    if args.raw_csv:
        _copy_benchmark_csv(result["raw_path"], args.raw_csv)
    if args.semantic_csv:
        _copy_benchmark_csv(result["semantic_path"], args.semantic_csv)
    if args.timing_summary_csv:
        _copy_benchmark_csv(result["timing_path"], args.timing_summary_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
