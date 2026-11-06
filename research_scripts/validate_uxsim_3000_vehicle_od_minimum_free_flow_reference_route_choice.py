"""
UXsim自身の通常経路選択が、OD間最短自由流Referenceとして使えるかの実装前検証。

このscriptはproduction実装ではない。
現行UXsim、現行6×6 grid、全168 Linkが200 m、自由流速度60 km/h、
現行3,000台Vehicle plan（departure T=0〜999、traffic seed 0、
demand generation seed 42、Vehicle plan SHA-256固定）に実際に含まれる
320種類のODペアだけを対象にする。

各ODはVehicle 1台だけの独立した自由流Worldで確認する。
評価側で新しい汎用ダイクストラframeworkは作らない。
AWT・AWWTは正式算出しない。
Route-Conditional評価moduleは変更しない。

Network構造、Link物理条件、経路選択、seed契約、OD生成方式が変わった場合は、
この検証をやり直す必要がある。

TMAXの根拠:
全Linkは200 m、自由流速度は60 km/hなので、1 Linkの自由流時間は
200 / (60 / 3.6) = 12秒である。
6×6 gridの外部OD間では、格子上のマンハッタン距離は最大10であり、
進入connectorと退出connectorを加えると最短でも高々12 Link、約144秒である。
TMAX=600秒は、その自由流最短経路を完走できる余裕であり、
混雑時に観測された44 Linkの実走行ルートを基準にしていない。

経路更新の間隔は現行UXsimの既定値600秒のままにする。
したがってroute_search_allはT=0で実行され、次はT=600である。
1台の自由流トリップはT=600より前に終わる。

理論最短コストは、Linkコスト float(length) / float(u) のNetworkX最短経路である。
uxsim.Utilities.enumerate_k_shortest_routes は同じ既定コストを使うが、
実装が最短単純経路ジェネレータを全件list化してからk件に切る。
6×6 gridでは全単純経路の列挙が終わらないため、この検証では呼ばない。
代わりに、同じコストのnetworkx.shortest_pathと、
コストが最小値を超えた時点で打ち切るshortest_simple_pathsを使う。
同一方向の並行Linkがある場合は、DiGraph化で情報が増減し得るため停止する。

同率最短経路では、Link名列の完全一致を合格条件にしない。
合格は、選ばれた経路のlength/u合計が最小コストと一致することである。

正式なOD minimum free-flow trip time候補は、連続量のlength/u合計ではなく、
UXsimが記録するVehicle.travel_timeである。
これは (arrival_time - departure_time) * DELTAT と一致しなければならない。
length/u合計との一致は、経路コストの監査であり、timestep値そのものの監査ではない。
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import networkx as nx
import numpy as np

from uxsim import World
from uxsim.uxsim import Link


# ---------------------------------------------------------------------------
# 1. Validation-only constants. This is not a production scenario.
# ---------------------------------------------------------------------------

VALIDATION_SCOPE = "validate_uxsim_3000_vehicle_od_minimum_free_flow_reference_route_choice"
VALIDATION_ONLY = True
FUTURE_REVALIDATION_NOTE = (
    "Revalidate this script if the network, link attributes, route choice, "
    "seed contract, or OD generation changes. This file is not a production "
    "OD minimum free-flow reference."
)

EXPECTED_VEHICLE_PLAN_SHA256 = (
    "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
)
EXPECTED_UNIQUE_OD_PAIR_COUNT = 320

NUM_VEHICLES = 3000
DEPARTURE_START = 0
DEPARTURE_END = 999
MIN_OD_MANHATTAN_DISTANCE = 5
DEMAND_GEN_SEED = 42
RANDOM_SEED = 0

GRID_SIZE = 6
TOTAL_NODE_COUNT = 60
TOTAL_LINK_COUNT = 168
INTERNAL_LINK_LENGTH = 200
OD_CONNECTOR_LENGTH = 200
FREE_FLOW_SPEED_KMH = 60
FREE_FLOW_SPEED = FREE_FLOW_SPEED_KMH / 3.6
JAM_DENSITY = 0.2
NUMBER_OF_LANES = 1
MERGE_PRIORITY = 1

DELTAN = 1
REACTION_TIME = 1
EXPECTED_DELTAT = 1
DUO_UPDATE_TIME = 600
FREE_FLOW_TMAX = 600
REPLAY_RUN_COUNT = 2
REFERENCE_DEPARTURE_TIME = 0
REFERENCE_VEHICLE_NAME = "od_free_flow_reference"
MAX_EQUAL_SHORTEST_ROUTES = 10
FREE_FLOW_COST_ABS_TOL = 1e-6

# Previously observed Route-Conditional mean free-flow trip time.
# This script does not recompute it and does not compute official AWT.
ROUTE_CONDITIONAL_MEAN_FREE_FLOW_TRIP_TIME_AUDIT_SECONDS = 125.352

REPRESENTATIVE_OD_TYPES = (
    "same_side",
    "opposite_sides",
    "adjacent_sides",
    "diagonal",
    "short_distance",
    "long_distance",
)

OUTPUT_DIR_NAME = (
    "validate_uxsim_3000_vehicle_od_minimum_free_flow_reference_route_choice"
)
OD_CSV_NAME = "od_reference_validation.csv"
SUMMARY_JSON_NAME = "summary.json"
RUN_SUMMARY_TXT_NAME = "run_summary.txt"

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
TRIAL_OUTPUT_DIR = REPO_ROOT / "research_outputs" / "trial" / OUTPUT_DIR_NAME


def _grid_node_name(row: int, column: int) -> str:
    return f"g_{row}_{column}"


def _external_od_node_names() -> tuple[str, ...]:
    names = []
    for column in range(GRID_SIZE):
        names.append(f"top_{column}")
        names.append(f"bottom_{column}")
    for row in range(GRID_SIZE):
        names.append(f"left_{row}")
        names.append(f"right_{row}")
    return tuple(names)


def _od_to_grid_coord_map() -> dict[str, tuple[int, int]]:
    mapping = {}
    for column in range(GRID_SIZE):
        mapping[f"top_{column}"] = (0, column)
        mapping[f"bottom_{column}"] = (GRID_SIZE - 1, column)
    for row in range(GRID_SIZE):
        mapping[f"left_{row}"] = (row, 0)
        mapping[f"right_{row}"] = (row, GRID_SIZE - 1)
    return mapping


def _build_link_specs() -> tuple[tuple, ...]:
    specs = []
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            specs.append((f"h_{row}_{column}_{column + 1}", left_node, right_node, INTERNAL_LINK_LENGTH, 0))
            specs.append((f"h_{row}_{column + 1}_{column}", right_node, left_node, INTERNAL_LINK_LENGTH, 0))
    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            specs.append((f"v_{row}_{row + 1}_{column}", upper_node, lower_node, INTERNAL_LINK_LENGTH, 1))
            specs.append((f"v_{row + 1}_{row}_{column}", lower_node, upper_node, INTERNAL_LINK_LENGTH, 1))
    for column in range(GRID_SIZE):
        top_node = f"top_{column}"
        bottom_node = f"bottom_{column}"
        north_grid = _grid_node_name(0, column)
        south_grid = _grid_node_name(GRID_SIZE - 1, column)
        specs.append((f"top_{column}_to_g_0_{column}", top_node, north_grid, OD_CONNECTOR_LENGTH, 1))
        specs.append((f"g_0_{column}_to_top_{column}", north_grid, top_node, OD_CONNECTOR_LENGTH, 1))
        specs.append((f"bottom_{column}_to_g_5_{column}", bottom_node, south_grid, OD_CONNECTOR_LENGTH, 1))
        specs.append((f"g_5_{column}_to_bottom_{column}", south_grid, bottom_node, OD_CONNECTOR_LENGTH, 1))
    for row in range(GRID_SIZE):
        left_node = f"left_{row}"
        right_node = f"right_{row}"
        west_grid = _grid_node_name(row, 0)
        east_grid = _grid_node_name(row, GRID_SIZE - 1)
        specs.append((f"left_{row}_to_g_{row}_0", left_node, west_grid, OD_CONNECTOR_LENGTH, 0))
        specs.append((f"g_{row}_0_to_left_{row}", west_grid, left_node, OD_CONNECTOR_LENGTH, 0))
        specs.append((f"right_{row}_to_g_{row}_5", right_node, east_grid, OD_CONNECTOR_LENGTH, 0))
        specs.append((f"g_{row}_5_to_right_{row}", east_grid, right_node, OD_CONNECTOR_LENGTH, 0))
    return tuple(specs)


def _manhattan_distance(origin_coord, destination_coord) -> int:
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


EXTERNAL_OD_NODES = _external_od_node_names()
OD_TO_GRID_COORD = _od_to_grid_coord_map()
ALL_LINK_SPECS = _build_link_specs()


# ---------------------------------------------------------------------------
# 2. Vehicle plan. Same sequence as the current FCFS 3000-vehicle trial.
# ---------------------------------------------------------------------------

def generate_vehicle_plans() -> list[dict]:
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    vehicle_index = 0
    while len(plans) < NUM_VEHICLES:
        origin = rng.choice(EXTERNAL_OD_NODES)
        destination = rng.choice(EXTERNAL_OD_NODES)
        if origin == destination:
            continue
        origin_grid_coord = OD_TO_GRID_COORD[origin]
        destination_grid_coord = OD_TO_GRID_COORD[destination]
        manhattan_distance = _manhattan_distance(origin_grid_coord, destination_grid_coord)
        if manhattan_distance < MIN_OD_MANHATTAN_DISTANCE:
            continue
        departure_time = DEPARTURE_START + (
            (DEPARTURE_END - DEPARTURE_START) * len(plans) / max(NUM_VEHICLES - 1, 1)
        )
        plans.append(
            {
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time,
                "name": f"veh_{vehicle_index}",
                "origin_grid_coord": origin_grid_coord,
                "destination_grid_coord": destination_grid_coord,
                "manhattan_distance": manhattan_distance,
            }
        )
        vehicle_index = vehicle_index + 1
    return plans


def _vehicle_plan_digest(plans: list[dict]) -> str:
    hasher = hashlib.sha256()
    for plan in plans:
        line = (
            f"{plan['name']}|{plan['origin']}|{plan['destination']}|"
            f"{plan['departure_time']!r}\n"
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def verify_vehicle_plans(plans: list[dict]) -> str:
    if len(plans) != NUM_VEHICLES:
        raise RuntimeError(f"Vehicle plan count is {len(plans)}, expected {NUM_VEHICLES}.")
    external = []
    for name in EXTERNAL_OD_NODES:
        external.append(name)
    previous_departure = None
    for index, plan in enumerate(plans):
        expected_name = f"veh_{index}"
        if plan["name"] != expected_name:
            raise RuntimeError(
                f"Vehicle plan {index} name is {plan['name']!r}, expected {expected_name!r}."
            )
        if plan["origin"] == plan["destination"]:
            raise RuntimeError(f"{plan['name']} origin equals destination.")
        if plan["origin"] not in external or plan["destination"] not in external:
            raise RuntimeError(f"{plan['name']} OD is not an external OD node.")
        if plan["manhattan_distance"] < MIN_OD_MANHATTAN_DISTANCE:
            raise RuntimeError(
                f"{plan['name']} Manhattan distance is {plan['manhattan_distance']}."
            )
        departure_time = plan["departure_time"]
        if departure_time < DEPARTURE_START or departure_time > DEPARTURE_END:
            raise RuntimeError(
                f"{plan['name']} departure {departure_time!r} is outside "
                f"T={DEPARTURE_START}..{DEPARTURE_END}."
            )
        if previous_departure is not None and departure_time < previous_departure:
            raise RuntimeError(f"{plan['name']} departure decreased.")
        previous_departure = departure_time
    if plans[0]["departure_time"] != DEPARTURE_START:
        raise RuntimeError(
            f"First departure is {plans[0]['departure_time']!r}, expected {DEPARTURE_START}."
        )
    if plans[-1]["departure_time"] != DEPARTURE_END:
        raise RuntimeError(
            f"Last departure is {plans[-1]['departure_time']!r}, expected {DEPARTURE_END}."
        )
    digest = _vehicle_plan_digest(plans)
    if digest != EXPECTED_VEHICLE_PLAN_SHA256:
        raise RuntimeError(
            "vehicle_plan_sha256 mismatch. "
            f"expected {EXPECTED_VEHICLE_PLAN_SHA256}, got {digest}."
        )
    return digest


def extract_unique_od_pairs(plans: list[dict]) -> list[dict]:
    """Keep the first vehicle-plan appearance order. Do not sort the pairs."""
    records = []
    index_by_od = {}
    for plan in plans:
        key = (plan["origin"], plan["destination"])
        if key in index_by_od:
            record_index = index_by_od[key]
            records[record_index]["vehicle_count"] = records[record_index]["vehicle_count"] + 1
            continue
        index_by_od[key] = len(records)
        origin_coord = OD_TO_GRID_COORD[plan["origin"]]
        destination_coord = OD_TO_GRID_COORD[plan["destination"]]
        records.append(
            {
                "origin": plan["origin"],
                "destination": plan["destination"],
                "vehicle_count": 1,
                "manhattan_distance": plan["manhattan_distance"],
                "side_relation": _side_relation(plan["origin"], plan["destination"]),
                "is_diagonal": origin_coord[0] != destination_coord[0] and origin_coord[1] != destination_coord[1],
            }
        )
    if len(records) != EXPECTED_UNIQUE_OD_PAIR_COUNT:
        raise RuntimeError(
            f"Unique OD pair count is {len(records)}, expected {EXPECTED_UNIQUE_OD_PAIR_COUNT}."
        )
    vehicle_total = 0
    for record in records:
        vehicle_total = vehicle_total + record["vehicle_count"]
    if vehicle_total != NUM_VEHICLES:
        raise RuntimeError(
            f"OD vehicle counts sum to {vehicle_total}, expected {NUM_VEHICLES}."
        )
    return records


def _boundary_side(node_name: str) -> str:
    if node_name.startswith("top_"):
        return "top"
    if node_name.startswith("bottom_"):
        return "bottom"
    if node_name.startswith("left_"):
        return "left"
    if node_name.startswith("right_"):
        return "right"
    raise RuntimeError(f"{node_name} is not an external OD node.")


def _side_relation(origin: str, destination: str) -> str:
    origin_side = _boundary_side(origin)
    destination_side = _boundary_side(destination)
    if origin_side == destination_side:
        return "same_side"
    opposite_pairs = {
        ("top", "bottom"),
        ("bottom", "top"),
        ("left", "right"),
        ("right", "left"),
    }
    if (origin_side, destination_side) in opposite_pairs:
        return "opposite_sides"
    return "adjacent_sides"


# ---------------------------------------------------------------------------
# 3. One-vehicle free-flow world. No order control and no specified route.
# ---------------------------------------------------------------------------

def _build_free_flow_world() -> World:
    world = World(
        name="uxsim_od_minimum_free_flow_reference_validation",
        deltan=DELTAN,
        reaction_time=REACTION_TIME,
        duo_update_time=DUO_UPDATE_TIME,
        duo_update_weight=0.5,
        duo_noise=0.01,
        route_choice_principle="homogeneous_DUO",
        route_choice_update_gradual=False,
        instantaneous_TT_timestep_interval=5,
        random_seed=RANDOM_SEED,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        show_progress=0,
        tmax=FREE_FLOW_TMAX,
        vehicle_logging_timestep_interval=1,
        hard_deterministic_mode=True,
        user_function=None,
    )
    if world.DELTAT != EXPECTED_DELTAT:
        raise RuntimeError(f"DELTAT is {world.DELTAT!r}, expected {EXPECTED_DELTAT}.")
    if world.hard_deterministic_mode is not True:
        raise RuntimeError("hard_deterministic_mode is not True.")
    if world.DUO_UPDATE_TIME != DUO_UPDATE_TIME:
        raise RuntimeError(f"DUO update time is {world.DUO_UPDATE_TIME!r}.")

    spacing = 1.0
    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            world.addNode(
                _grid_node_name(row, column),
                column * spacing,
                -row * spacing,
            )
    for column in range(GRID_SIZE):
        world.addNode(f"top_{column}", column * spacing, spacing)
        world.addNode(f"bottom_{column}", column * spacing, -GRID_SIZE * spacing)
    for row in range(GRID_SIZE):
        world.addNode(f"left_{row}", -spacing, -row * spacing)
        world.addNode(f"right_{row}", GRID_SIZE * spacing, -row * spacing)

    for link_name, start_node, end_node, length, signal_group in ALL_LINK_SPECS:
        world.addLink(
            link_name,
            start_node,
            end_node,
            length=length,
            free_flow_speed=FREE_FLOW_SPEED,
            jam_density=JAM_DENSITY,
            number_of_lanes=NUMBER_OF_LANES,
            merge_priority=MERGE_PRIORITY,
            signal_group=signal_group,
        )
    _assert_free_flow_world_contract(world)
    return world


def _assert_free_flow_world_contract(world: World) -> None:
    if len(world.NODES) != TOTAL_NODE_COUNT:
        raise RuntimeError(f"Node count is {len(world.NODES)}, expected {TOTAL_NODE_COUNT}.")
    if len(world.LINKS) != TOTAL_LINK_COUNT:
        raise RuntimeError(f"Link count is {len(world.LINKS)}, expected {TOTAL_LINK_COUNT}.")
    directed_pairs = {}
    for link in world.LINKS:
        if link.length != INTERNAL_LINK_LENGTH:
            raise RuntimeError(f"Link {link.name} length is {link.length!r}, expected 200.")
        if link.u != FREE_FLOW_SPEED or link.free_flow_speed != FREE_FLOW_SPEED:
            raise RuntimeError(f"Link {link.name} free-flow speed is not 60 km/h.")
        if link.u <= 0:
            raise RuntimeError(f"Link {link.name} has non-positive free-flow speed.")
        if link.route_choice_penalty != 0:
            raise RuntimeError(f"Link {link.name} route_choice_penalty is {link.route_choice_penalty!r}.")
        if link.capacity_in is None or link.capacity_in <= 0:
            raise RuntimeError(f"Link {link.name} capacity_in is {link.capacity_in!r}.")
        if link.capacity_out is None or link.capacity_out <= 0:
            raise RuntimeError(f"Link {link.name} capacity_out is {link.capacity_out!r}.")
        pair = (link.start_node.name, link.end_node.name)
        if pair in directed_pairs:
            raise RuntimeError(
                "Parallel same-direction links exist: "
                f"{directed_pairs[pair]} and {link.name} both connect {pair[0]} -> {pair[1]}. "
                "Stop before shortest-path audit, because a DiGraph would drop one of them."
            )
        directed_pairs[pair] = link.name
    for node in world.NODES:
        if node.signal != [0]:
            raise RuntimeError(f"Node {node.name} signal is {node.signal!r}, expected [0].")
        if node.flow_capacity is not None:
            raise RuntimeError(f"Node {node.name} flow_capacity is {node.flow_capacity!r}.")
        if node.order_control_type != "none":
            raise RuntimeError(
                f"Node {node.name} order_control_type is {node.order_control_type!r}."
            )
        if node.order_control_eligible is not False:
            raise RuntimeError(f"Node {node.name} order_control_eligible is not False.")
    if len(world.VEHICLES) != 0:
        raise RuntimeError("Free-flow world builder must not add vehicles.")


def _assert_unconstrained_vehicle(vehicle) -> None:
    if vehicle.specified_route is not None:
        raise RuntimeError(f"{vehicle.name} already has specified_route.")
    if len(vehicle.links_prefer) != 0 or len(vehicle.links_avoid) != 0:
        raise RuntimeError(f"{vehicle.name} has links_prefer or links_avoid.")
    if vehicle.mode != "single_trip":
        raise RuntimeError(f"{vehicle.name} mode is {vehicle.mode!r}.")
    if vehicle.state != "home":
        raise RuntimeError(f"{vehicle.name} state is {vehicle.state!r} before simulation.")
    if vehicle.departure_time != REFERENCE_DEPARTURE_TIME:
        raise RuntimeError(
            f"{vehicle.name} departure_time is {vehicle.departure_time!r}, expected 0."
        )
    preference_sum = float(np.sum(list(vehicle.route_pref.values())))
    if preference_sum != 0.0:
        raise RuntimeError(
            f"{vehicle.name} initial route_pref sum is {preference_sum!r}, expected 0."
        )


def _make_route_choice_timing_observer(bucket: dict):
    """Read-only observer. It does not change the vehicle or the network."""

    def user_function(world: World) -> None:
        vehicle = world.VEHICLES[REFERENCE_VEHICLE_NAME]
        if world.T == 0:
            bucket["end_t0_state"] = vehicle.state
            bucket["end_t0_in_generation_queue"] = vehicle in vehicle.orig.generation_queue
            bucket["end_t0_link_is_none"] = vehicle.link is None
            bucket["end_t0_route_pref_sum"] = float(np.sum(vehicle.route_pref))
            max_gap = 0.0
            for link in world.LINKS:
                if len(link.traveltime_instant) == 0:
                    bucket["instant_travel_time_missing"] = True
                    continue
                instant_cost = float(link.traveltime_instant[-1])
                length_over_u = float(link.length) / float(link.u)
                gap = abs(instant_cost - length_over_u)
                if gap > max_gap:
                    max_gap = gap
            bucket["end_t0_max_instant_gap"] = max_gap
        if world.T == 1:
            bucket["end_t1_state"] = vehicle.state
            if vehicle.link is None:
                bucket["end_t1_link"] = None
            else:
                bucket["end_t1_link"] = vehicle.link.name

    return user_function


def _assert_route_choice_timing(bucket: dict, origin: str, destination: str) -> None:
    if bucket.get("end_t0_state") != "wait":
        raise RuntimeError(
            "At the end of T=0 the reference vehicle was not waiting.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"state: {bucket.get('end_t0_state')!r}"
        )
    if bucket.get("end_t0_in_generation_queue") is not True or bucket.get("end_t0_link_is_none") is not True:
        raise RuntimeError(
            "At the end of T=0 the vehicle should be in the generation queue and not on a link.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"observations: {bucket!r}"
        )
    route_pref_sum = bucket.get("end_t0_route_pref_sum")
    if route_pref_sum is None or route_pref_sum <= 0.0:
        raise RuntimeError(
            "Route preference was not updated by the end of T=0.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"route_pref_sum: {route_pref_sum!r}"
        )
    if bucket.get("instant_travel_time_missing") is True:
        raise RuntimeError(
            "Instantaneous travel time was missing at T=0.\n"
            f"origin: {origin}\n"
            f"destination: {destination}"
        )
    max_gap = bucket.get("end_t0_max_instant_gap")
    if max_gap is None or max_gap > FREE_FLOW_COST_ABS_TOL:
        raise RuntimeError(
            "T=0 instantaneous travel time does not match length/u.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"max_abs_gap: {max_gap!r}"
        )
    if bucket.get("end_t1_state") != "run" or bucket.get("end_t1_link") is None:
        raise RuntimeError(
            "At the end of T=1 the vehicle had not entered its first link.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"state: {bucket.get('end_t1_state')!r}\n"
            f"link: {bucket.get('end_t1_link')!r}"
        )


# ---------------------------------------------------------------------------
# 4. Theoretical free-flow cost. NetworkX, weight = length/u, no new Dijkstra.
# ---------------------------------------------------------------------------

def _build_length_over_u_graph(world: World) -> nx.DiGraph:
    graph = nx.DiGraph()
    for link in world.LINKS:
        weight = float(link.length) / float(link.u)
        start_name = link.start_node.name
        end_name = link.end_node.name
        if graph.has_edge(start_name, end_name):
            raise RuntimeError(
                f"Parallel edge {start_name} -> {end_name} reached graph construction."
            )
        graph.add_edge(start_name, end_name, weight=weight, link_name=link.name)
    return graph


def _node_path_cost(graph: nx.DiGraph, node_path: list[str]) -> float:
    cost = 0.0
    for index in range(len(node_path) - 1):
        start_name = node_path[index]
        end_name = node_path[index + 1]
        cost = cost + float(graph[start_name][end_name]["weight"])
    return cost


def _node_path_link_names(graph: nx.DiGraph, node_path: list[str]) -> list[str]:
    names = []
    for index in range(len(node_path) - 1):
        start_name = node_path[index]
        end_name = node_path[index + 1]
        names.append(graph[start_name][end_name]["link_name"])
    return names


def _costs_equal(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=FREE_FLOW_COST_ABS_TOL)


def _theoretical_shortest(graph: nx.DiGraph, origin: str, destination: str) -> tuple[list[str], float]:
    try:
        node_path = nx.shortest_path(graph, origin, destination, weight="weight")
        reported_cost = float(nx.shortest_path_length(graph, origin, destination, weight="weight"))
    except nx.NetworkXNoPath as error:
        raise RuntimeError(
            "No theoretical free-flow path exists.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"networkx: {error}"
        ) from error
    link_names = _node_path_link_names(graph, node_path)
    summed_cost = _node_path_cost(graph, node_path)
    if _costs_equal(reported_cost, summed_cost) is not True:
        raise RuntimeError(
            "NetworkX shortest_path_length and the explicit length/u sum disagree.\n"
            f"origin: {origin}\n"
            f"destination: {destination}\n"
            f"reported_cost: {reported_cost!r}\n"
            f"summed_cost: {summed_cost!r}\n"
            f"route: {link_names}"
        )
    return link_names, summed_cost


def _bounded_equal_shortest_routes(graph: nx.DiGraph, origin: str, destination: str) -> list[dict]:
    """Stop at the first route whose cost exceeds the minimum, or at the cap."""
    path_generator = nx.shortest_simple_paths(graph, origin, destination, weight="weight")
    collected = []
    minimum_cost = None
    for node_path in path_generator:
        cost = _node_path_cost(graph, node_path)
        if minimum_cost is None:
            minimum_cost = cost
        elif _costs_equal(cost, minimum_cost) is not True:
            break
        link_names = _node_path_link_names(graph, node_path)
        collected.append(
            {
                "link_names": link_names,
                "link_count": len(link_names),
                "free_flow_cost": cost,
            }
        )
        if len(collected) >= MAX_EQUAL_SHORTEST_ROUTES:
            break
    return collected


def _route_length_over_u(world: World, link_names: list[str]) -> float:
    cost = 0.0
    for link_name in link_names:
        link = world.get_link(link_name)
        cost = cost + float(link.length) / float(link.u)
    return cost


def _traveled_link_names(vehicle) -> list[str]:
    names = []
    for log_row in vehicle.log_t_link:
        logged_link = log_row[1]
        if isinstance(logged_link, Link):
            names.append(logged_link.name)
    return names


def _raise_od_failure(origin: str, destination: str, message: str, details: dict) -> None:
    lines = [
        message,
        f"origin: {origin}",
        f"destination: {destination}",
        "Formal success files were not written.",
    ]
    for key in details:
        lines.append(f"{key}: {details[key]}")
    raise RuntimeError("\n".join(lines))


def _inspect_completed_route(world: World, vehicle, origin: str, destination: str, theoretical_link_names: list[str], theoretical_cost: float) -> dict:
    if vehicle.state != "end" or vehicle.arrival_time < 0 or vehicle.travel_time < 0:
        _raise_od_failure(
            origin,
            destination,
            "Reference vehicle did not complete within TMAX.",
            {
                "state": vehicle.state,
                "arrival_time": vehicle.arrival_time,
                "travel_time": vehicle.travel_time,
                "tmax": FREE_FLOW_TMAX,
                "route": _traveled_link_names(vehicle),
            },
        )
    trip_timesteps = vehicle.arrival_time - vehicle.departure_time
    expected_travel_time = trip_timesteps * world.DELTAT
    if vehicle.travel_time != expected_travel_time:
        _raise_od_failure(
            origin,
            destination,
            "Vehicle.travel_time does not equal (arrival-departure) * DELTAT.",
            {
                "travel_time": vehicle.travel_time,
                "arrival_time": vehicle.arrival_time,
                "departure_time": vehicle.departure_time,
                "deltat": world.DELTAT,
                "expected_travel_time": expected_travel_time,
            },
        )
    if math.isfinite(vehicle.travel_time) is not True or vehicle.travel_time <= 0:
        _raise_od_failure(
            origin,
            destination,
            "OD minimum free-flow trip time candidate is not finite and positive.",
            {"travel_time": vehicle.travel_time},
        )

    link_names = _traveled_link_names(vehicle)
    if len(link_names) == 0:
        _raise_od_failure(origin, destination, "UXsim route is empty.", {"route": link_names})

    visited_nodes = []
    repeated_link = False
    repeated_node = False
    seen_links = []
    for index, link_name in enumerate(link_names):
        if link_name not in world.LINKS_NAME_DICT:
            _raise_od_failure(
                origin,
                destination,
                "UXsim route contains a link that is not in the network.",
                {"missing_link": link_name, "route": link_names},
            )
        link = world.get_link(link_name)
        if link_name in seen_links:
            repeated_link = True
        seen_links.append(link_name)
        if index == 0:
            if link.start_node.name != origin:
                _raise_od_failure(
                    origin,
                    destination,
                    "UXsim route does not leave the origin.",
                    {"first_link": link_name, "start_node": link.start_node.name, "route": link_names},
                )
            visited_nodes.append(link.start_node.name)
        else:
            if link.start_node.name != visited_nodes[-1]:
                _raise_od_failure(
                    origin,
                    destination,
                    "UXsim route links are not connected.",
                    {
                        "previous_node": visited_nodes[-1],
                        "link": link_name,
                        "link_start": link.start_node.name,
                        "route": link_names,
                    },
                )
        if link.end_node.name in visited_nodes:
            repeated_node = True
        visited_nodes.append(link.end_node.name)
    if visited_nodes[-1] != destination:
        _raise_od_failure(
            origin,
            destination,
            "UXsim route does not arrive at the destination.",
            {"final_node": visited_nodes[-1], "route": link_names},
        )
    if repeated_link is True or repeated_node is True:
        _raise_od_failure(
            origin,
            destination,
            "UXsim route repeats a link or a node.",
            {
                "route": link_names,
                "nodes": visited_nodes,
                "repeated_link": repeated_link,
                "repeated_node": repeated_node,
            },
        )

    uxsim_cost = _route_length_over_u(world, link_names)
    cost_difference = uxsim_cost - theoretical_cost
    shortest_cost_match = _costs_equal(uxsim_cost, theoretical_cost)
    if shortest_cost_match is not True:
        _raise_od_failure(
            origin,
            destination,
            "UXsim route free-flow cost does not match the theoretical OD minimum.",
            {
                "uxsim_route": link_names,
                "uxsim_cost": uxsim_cost,
                "theoretical_route": theoretical_link_names,
                "theoretical_cost": theoretical_cost,
                "cost_difference": cost_difference,
                "travel_time": vehicle.travel_time,
            },
        )
    return {
        "link_names": link_names,
        "link_count": len(link_names),
        "free_flow_cost": uxsim_cost,
        "theoretical_link_names": list(theoretical_link_names),
        "theoretical_link_count": len(theoretical_link_names),
        "theoretical_cost": theoretical_cost,
        "departure_time": vehicle.departure_time,
        "arrival_time": vehicle.arrival_time,
        "travel_time": vehicle.travel_time,
        "trip_timesteps": trip_timesteps,
        "cost_difference": cost_difference,
        "shortest_cost_match": True,
        "route_name_match": link_names == list(theoretical_link_names),
        "repeated_link": False,
        "repeated_node": False,
        "completed": True,
        "route_empty": False,
    }


def _main_contract_passed(record: dict) -> bool:
    """Pass on shortest free-flow cost, completion, and a simple route.

    Identical link names are not the contract. Two different link sequences
    can both be shortest when their length/u sums match.
    """
    if record["completed"] is not True:
        return False
    if record["route_empty"] is True:
        return False
    if record["repeated_link"] is True or record["repeated_node"] is True:
        return False
    if record["shortest_cost_match"] is not True:
        return False
    if math.isfinite(record["travel_time"]) is not True or record["travel_time"] <= 0:
        return False
    return True


def _simulate_unconstrained_route(origin: str, destination: str, theoretical_link_names: list[str], theoretical_cost: float, timing_bucket: dict | None) -> dict:
    world = _build_free_flow_world()
    world.addVehicle(
        origin,
        destination,
        REFERENCE_DEPARTURE_TIME,
        name=REFERENCE_VEHICLE_NAME,
        mode="single_trip",
    )
    if len(world.VEHICLES) != 1:
        raise RuntimeError(f"OD world has {len(world.VEHICLES)} vehicles, expected 1.")
    vehicle = world.VEHICLES[REFERENCE_VEHICLE_NAME]
    _assert_unconstrained_vehicle(vehicle)
    if timing_bucket is not None:
        world.user_function = _make_route_choice_timing_observer(timing_bucket)
    world.exec_simulation()
    if timing_bucket is not None:
        _assert_route_choice_timing(timing_bucket, origin, destination)
    outcome = _inspect_completed_route(
        world,
        vehicle,
        origin,
        destination,
        theoretical_link_names,
        theoretical_cost,
    )
    if _main_contract_passed(outcome) is not True:
        _raise_od_failure(
            origin,
            destination,
            "Unconstrained UXsim route failed the main free-flow contract.",
            {"outcome": outcome},
        )
    return outcome


def _simulate_enforced_route(origin: str, destination: str, link_names: list[str], theoretical_cost: float) -> dict:
    world = _build_free_flow_world()
    world.addVehicle(
        origin,
        destination,
        REFERENCE_DEPARTURE_TIME,
        name=REFERENCE_VEHICLE_NAME,
        mode="single_trip",
    )
    vehicle = world.VEHICLES[REFERENCE_VEHICLE_NAME]
    vehicle.enforce_route(list(link_names), set_avoid=False)
    if vehicle.specified_route is None:
        raise RuntimeError("enforce_route did not set specified_route.")
    world.exec_simulation()
    outcome = _inspect_completed_route(
        world,
        vehicle,
        origin,
        destination,
        link_names,
        theoretical_cost,
    )
    if outcome["link_names"] != list(link_names):
        _raise_od_failure(
            origin,
            destination,
            "Enforced equal-cost route was not followed.",
            {
                "requested_route": link_names,
                "traveled_route": outcome["link_names"],
                "travel_time": outcome["travel_time"],
                "theoretical_cost": theoretical_cost,
            },
        )
    return outcome


def _compare_replays(origin: str, destination: str, first: dict, second: dict) -> dict:
    travel_time_match = first["travel_time"] == second["travel_time"] and first["arrival_time"] == second["arrival_time"]
    route_identity_match = first["link_names"] == second["link_names"]
    if travel_time_match is not True:
        _raise_od_failure(
            origin,
            destination,
            "Two independent free-flow replays disagree on reference travel time.",
            {
                "run1_travel_time": first["travel_time"],
                "run2_travel_time": second["travel_time"],
                "run1_arrival_time": first["arrival_time"],
                "run2_arrival_time": second["arrival_time"],
                "run1_route": first["link_names"],
                "run2_route": second["link_names"],
                "run1_cost": first["free_flow_cost"],
                "run2_cost": second["free_flow_cost"],
            },
        )
    if route_identity_match is not True:
        if first["shortest_cost_match"] is not True or second["shortest_cost_match"] is not True:
            _raise_od_failure(
                origin,
                destination,
                "Replay routes differ and at least one is not a shortest free-flow route.",
                {
                    "run1_route": first["link_names"],
                    "run2_route": second["link_names"],
                    "run1_cost": first["free_flow_cost"],
                    "run2_cost": second["free_flow_cost"],
                    "theoretical_cost": first["theoretical_cost"],
                },
            )
    return {
        "route_identity_match": route_identity_match,
        "travel_time_match": True,
    }


def _od_matches_representative_type(record: dict, type_name: str, minimum_manhattan: int, maximum_manhattan: int) -> bool:
    if type_name == "same_side":
        return record["side_relation"] == "same_side"
    if type_name == "opposite_sides":
        return record["side_relation"] == "opposite_sides"
    if type_name == "adjacent_sides":
        return record["side_relation"] == "adjacent_sides"
    if type_name == "diagonal":
        return record["is_diagonal"] is True
    if type_name == "short_distance":
        return record["manhattan_distance"] == minimum_manhattan
    if type_name == "long_distance":
        return record["manhattan_distance"] == maximum_manhattan
    raise RuntimeError(f"Unknown representative OD type {type_name!r}.")


def _select_representative_ods(od_records: list[dict], graph: nx.DiGraph) -> list[dict]:
    minimum_manhattan = od_records[0]["manhattan_distance"]
    maximum_manhattan = od_records[0]["manhattan_distance"]
    for record in od_records:
        if record["manhattan_distance"] < minimum_manhattan:
            minimum_manhattan = record["manhattan_distance"]
        if record["manhattan_distance"] > maximum_manhattan:
            maximum_manhattan = record["manhattan_distance"]

    selected = []
    used_pairs = []
    for type_name in REPRESENTATIVE_OD_TYPES:
        chosen = None
        for record in od_records:
            pair = (record["origin"], record["destination"])
            already_used = False
            for used_pair in used_pairs:
                if used_pair == pair:
                    already_used = True
            if already_used is True:
                continue
            if _od_matches_representative_type(record, type_name, minimum_manhattan, maximum_manhattan) is not True:
                continue
            routes = _bounded_equal_shortest_routes(graph, record["origin"], record["destination"])
            if len(routes) < 2:
                continue
            chosen = {
                "available": True,
                "type_name": type_name,
                "origin": record["origin"],
                "destination": record["destination"],
                "manhattan_distance": record["manhattan_distance"],
                "side_relation": record["side_relation"],
                "candidate_limit": MAX_EQUAL_SHORTEST_ROUTES,
                "selection_rule": (
                    "First vehicle-plan OD of this type with at least two equal "
                    "length/u costs, skipping OD pairs already selected for another type. "
                    f"At most {MAX_EQUAL_SHORTEST_ROUTES} equal-cost routes are simulated."
                ),
                "equal_cost_routes": routes,
                "minimum_manhattan_in_plan": minimum_manhattan,
                "maximum_manhattan_in_plan": maximum_manhattan,
            }
            used_pairs.append(pair)
            break
        if chosen is None:
            chosen = {
                "available": False,
                "type_name": type_name,
                "candidate_limit": MAX_EQUAL_SHORTEST_ROUTES,
                "selection_rule": (
                    "First unused vehicle-plan OD of this type with at least two equal costs."
                ),
                "reason": "No remaining OD of this type had two or more equal-cost routes within the cap.",
                "minimum_manhattan_in_plan": minimum_manhattan,
                "maximum_manhattan_in_plan": maximum_manhattan,
            }
        selected.append(chosen)
    return selected


def _check_representative_equal_routes(selected: list[dict]) -> dict:
    checked_route_count = 0
    matched_route_count = 0
    for item in selected:
        if item["available"] is not True:
            item["simulated_routes"] = []
            item["travel_times_match"] = None
            item["link_counts"] = []
            continue
        simulated = []
        for route_info in item["equal_cost_routes"]:
            outcome = _simulate_enforced_route(
                item["origin"],
                item["destination"],
                route_info["link_names"],
                route_info["free_flow_cost"],
            )
            simulated.append(
                {
                    "link_names": outcome["link_names"],
                    "link_count": outcome["link_count"],
                    "free_flow_cost": outcome["free_flow_cost"],
                    "arrival_time": outcome["arrival_time"],
                    "travel_time": outcome["travel_time"],
                    "trip_timesteps": outcome["trip_timesteps"],
                }
            )
        reference_travel_time = simulated[0]["travel_time"]
        reference_arrival_time = simulated[0]["arrival_time"]
        link_counts = []
        for outcome in simulated:
            link_counts.append(outcome["link_count"])
            checked_route_count = checked_route_count + 1
            if outcome["travel_time"] != reference_travel_time or outcome["arrival_time"] != reference_arrival_time:
                _raise_od_failure(
                    item["origin"],
                    item["destination"],
                    "Equal-cost shortest routes do not share one reference travel time.",
                    {
                        "type_name": item["type_name"],
                        "reference_travel_time": reference_travel_time,
                        "reference_arrival_time": reference_arrival_time,
                        "this_travel_time": outcome["travel_time"],
                        "this_arrival_time": outcome["arrival_time"],
                        "this_route": outcome["link_names"],
                        "this_link_count": outcome["link_count"],
                        "all_simulated": simulated,
                    },
                )
            matched_route_count = matched_route_count + 1
        item["simulated_routes"] = simulated
        item["travel_times_match"] = True
        item["link_counts"] = link_counts
        unique_link_counts = []
        for link_count in link_counts:
            if link_count not in unique_link_counts:
                unique_link_counts.append(link_count)
        item["link_counts_identical"] = len(unique_link_counts) == 1
    return {
        "checked_route_count": checked_route_count,
        "matched_route_count": matched_route_count,
    }


# ---------------------------------------------------------------------------
# 5. Output. Written only after every check has passed.
# ---------------------------------------------------------------------------

def _format_route(link_names: list[str]) -> str:
    return " ".join(link_names)


def _write_validation_outputs(rows: list[dict], summary: dict, run_summary_text: str) -> None:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(f"Refusing to overwrite {TRIAL_OUTPUT_DIR}.")
    TRIAL_OUTPUT_DIR.mkdir(parents=True)
    csv_path = TRIAL_OUTPUT_DIR / OD_CSV_NAME
    summary_path = TRIAL_OUTPUT_DIR / SUMMARY_JSON_NAME
    run_summary_path = TRIAL_OUTPUT_DIR / RUN_SUMMARY_TXT_NAME
    if csv_path.exists() or summary_path.exists() or run_summary_path.exists():
        raise RuntimeError("Refusing to overwrite validation output files.")

    fieldnames = [
        "origin",
        "destination",
        "vehicle_count",
        "side_relation",
        "is_diagonal",
        "manhattan_distance",
        "run1_link_names",
        "run1_link_count",
        "run1_free_flow_cost",
        "run1_departure_time",
        "run1_arrival_time",
        "run1_travel_time",
        "run1_trip_timesteps",
        "run1_cost_difference",
        "run2_link_names",
        "run2_link_count",
        "run2_free_flow_cost",
        "run2_departure_time",
        "run2_arrival_time",
        "run2_travel_time",
        "run2_trip_timesteps",
        "run2_cost_difference",
        "theoretical_link_names",
        "theoretical_link_count",
        "theoretical_free_flow_cost",
        "od_minimum_free_flow_trip_time_candidate",
        "shortest_cost_match",
        "route_name_match_run1",
        "route_identity_match",
        "travel_time_match",
        "repeated_link",
        "repeated_node",
        "completed",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run_summary_path.write_text(run_summary_text, encoding="utf-8")


def _build_csv_row(od_record: dict, first: dict, second: dict, comparison: dict) -> dict:
    return {
        "origin": od_record["origin"],
        "destination": od_record["destination"],
        "vehicle_count": od_record["vehicle_count"],
        "side_relation": od_record["side_relation"],
        "is_diagonal": od_record["is_diagonal"],
        "manhattan_distance": od_record["manhattan_distance"],
        "run1_link_names": _format_route(first["link_names"]),
        "run1_link_count": first["link_count"],
        "run1_free_flow_cost": first["free_flow_cost"],
        "run1_departure_time": first["departure_time"],
        "run1_arrival_time": first["arrival_time"],
        "run1_travel_time": first["travel_time"],
        "run1_trip_timesteps": first["trip_timesteps"],
        "run1_cost_difference": first["cost_difference"],
        "run2_link_names": _format_route(second["link_names"]),
        "run2_link_count": second["link_count"],
        "run2_free_flow_cost": second["free_flow_cost"],
        "run2_departure_time": second["departure_time"],
        "run2_arrival_time": second["arrival_time"],
        "run2_travel_time": second["travel_time"],
        "run2_trip_timesteps": second["trip_timesteps"],
        "run2_cost_difference": second["cost_difference"],
        "theoretical_link_names": _format_route(first["theoretical_link_names"]),
        "theoretical_link_count": first["theoretical_link_count"],
        "theoretical_free_flow_cost": first["theoretical_cost"],
        "od_minimum_free_flow_trip_time_candidate": first["travel_time"],
        "shortest_cost_match": True,
        "route_name_match_run1": first["route_name_match"],
        "route_identity_match": comparison["route_identity_match"],
        "travel_time_match": comparison["travel_time_match"],
        "repeated_link": False,
        "repeated_node": False,
        "completed": True,
    }


def _summary_lines(summary: dict) -> list[str]:
    lines = [
        "UXsim OD minimum free-flow reference route-choice validation",
        "validation_only: true",
        f"validation_scope: {VALIDATION_SCOPE}",
        FUTURE_REVALIDATION_NOTE,
        f"vehicle plan hash: {summary['vehicle_plan_sha256']}",
        f"vehicle count: {summary['vehicle_count']}",
        f"unique OD pair count: {summary['unique_od_pair_count']}",
        f"OD replay run count: {summary['od_replay_run_count']}",
        "simulated world count (two replays plus representative enforced routes): "
        f"{summary['total_world_count']}",
        f"completed OD count: {summary['completed_od_count']}",
        f"shortest cost match OD count: {summary['shortest_cost_match_od_count']}",
        f"shortest cost mismatch OD count: {summary['shortest_cost_mismatch_od_count']}",
        f"route identity stable OD count: {summary['route_identity_stable_od_count']}",
        f"route identity changed OD count: {summary['route_identity_changed_od_count']}",
        f"reference travel time stable OD count: {summary['reference_travel_time_stable_od_count']}",
        f"reference travel time mismatch OD count: {summary['reference_travel_time_mismatch_od_count']}",
        f"route loop OD count: {summary['route_loop_od_count']}",
        f"minimum OD reference trip time: {summary['minimum_od_reference_trip_time']}",
        f"maximum OD reference trip time: {summary['maximum_od_reference_trip_time']}",
        "vehicle-plan weighted average OD minimum free-flow trip time: "
        f"{summary['weighted_average_od_reference_trip_time']}",
        "route-conditional mean free-flow trip time audit seconds: "
        f"{summary['route_conditional_mean_free_flow_trip_time_audit_seconds']}",
        "audit difference (route-conditional mean minus weighted OD reference): "
        f"{summary['route_conditional_audit_minus_weighted_od_reference']}",
        "This weighted average is not official AWT. Actual trip time was not subtracted.",
        f"representative equal-shortest route checks: {summary['representative_equal_route_check_count']}",
        f"representative equal-shortest reference time matches: {summary['representative_equal_route_time_match_count']}",
        summary["final_judgment"],
    ]
    return lines


# ---------------------------------------------------------------------------
# 6. Static validation. No World and no simulation.
# ---------------------------------------------------------------------------

def _function_node(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _collect_call_names_in_order(node, found: list[str]) -> None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            found.append(func.id)
        elif isinstance(func, ast.Attribute):
            found.append(func.attr)
    for child in ast.iter_child_nodes(node):
        _collect_call_names_in_order(child, found)


def _literal_command_strings(node: ast.expr) -> list[str] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        parts = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                parts.append(elt.value)
            else:
                return None
        return parts
    return None


def _literal_argv_invokes_forbidden_git(parts: list[str]) -> bool:
    if len(parts) == 0:
        return False
    if len(parts) == 1:
        tokens = parts[0].split()
    else:
        tokens = list(parts)
    for index, token in enumerate(tokens):
        if token != "git" and token.endswith("/git") is not True:
            continue
        if index + 1 >= len(tokens):
            continue
        if tokens[index + 1] in {"add", "commit", "push"}:
            return True
    return False


def _assert_no_git_command_execution(tree: ast.Module) -> None:
    subprocess_methods = {"run", "call", "check_call", "check_output"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        module_name = node.func.value.id
        method_name = node.func.attr
        if len(node.args) == 0:
            continue
        literal = _literal_command_strings(node.args[0])
        if literal is None or _literal_argv_invokes_forbidden_git(literal) is not True:
            continue
        if module_name == "os" and method_name == "system":
            raise RuntimeError("This validation script must not execute Git commands via os.system.")
        if module_name == "subprocess" and method_name in subprocess_methods:
            raise RuntimeError("This validation script must not execute Git commands via subprocess.")


def _assert_static_call_scope(tree: ast.Module) -> None:
    forbidden_anywhere = {
        "set_order_control_for_nodes",
        "infer_order_control_eligible_nodes",
        "evaluate_network_wide_waiting_time",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if module_name == "uxsim.network_wide_waiting_time_evaluation":
                raise RuntimeError("This script must not import the production evaluation module.")
            if "run_fcfs_6x6_grid" in module_name:
                raise RuntimeError("This script must not import the FCFS trial script.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_anywhere:
                raise RuntimeError(f"Unexpected call {node.func.attr}.")
            if node.func.attr == "addVehicle":
                for keyword in node.keywords:
                    if keyword.arg == "specified_route":
                        raise RuntimeError("addVehicle must not receive specified_route.")

    unconstrained = _function_node(tree, "_simulate_unconstrained_route")
    enforced = _function_node(tree, "_simulate_enforced_route")
    contract = _function_node(tree, "_main_contract_passed")
    if unconstrained is None or enforced is None or contract is None:
        raise RuntimeError("Route simulation helpers are missing.")
    unconstrained_calls = []
    _collect_call_names_in_order(unconstrained, unconstrained_calls)
    if unconstrained_calls.count("addVehicle") != 1:
        raise RuntimeError("The unconstrained world must add exactly one vehicle.")
    if "exec_simulation" not in unconstrained_calls:
        raise RuntimeError("The unconstrained check must use normal exec_simulation.")
    if "enforce_route" in unconstrained_calls:
        raise RuntimeError("The unconstrained check must leave route choice to UXsim.")
    enforced_calls = []
    _collect_call_names_in_order(enforced, enforced_calls)
    if "enforce_route" not in enforced_calls:
        raise RuntimeError("The equal-cost representative check must call enforce_route.")

    contract_source = ast.get_source_segment(SCRIPT_PATH.read_text(encoding="utf-8"), contract)
    if contract_source is None:
        raise RuntimeError("Could not read the main contract helper.")
    if "shortest_cost_match" not in contract_source:
        raise RuntimeError("The main contract must inspect shortest free-flow cost.")
    if "route_identity_match" in contract_source or "route_name_match" in contract_source:
        raise RuntimeError("The main contract must not require identical link names.")

    run_function = _function_node(tree, "_run_od_reference_validation")
    if run_function is None:
        raise RuntimeError("_run_od_reference_validation is missing.")
    run_source = ast.get_source_segment(SCRIPT_PATH.read_text(encoding="utf-8"), run_function)
    if run_source is None:
        raise RuntimeError("Could not read the run function.")
    exists_pos = run_source.find("TRIAL_OUTPUT_DIR.exists")
    verify_pos = run_source.find("verify_vehicle_plans")
    unique_pos = run_source.find("EXPECTED_UNIQUE_OD_PAIR_COUNT")
    replay_pos = run_source.find("REPLAY_RUN_COUNT")
    simulate_pos = run_source.find("_simulate_unconstrained_route")
    write_pos = run_source.find("_write_validation_outputs")
    if min(exists_pos, verify_pos, unique_pos, replay_pos) < 0:
        raise RuntimeError("Run path is missing the plan, OD count, replay, or output guard.")
    if exists_pos > simulate_pos or verify_pos > simulate_pos:
        raise RuntimeError("Plan hash and output guard must happen before OD simulation.")
    if write_pos < simulate_pos:
        raise RuntimeError("Success files must be written after the OD simulations.")

    validator = _function_node(tree, "validate_static_contract")
    if validator is None:
        raise RuntimeError("validate_static_contract is missing.")
    validator_calls = []
    _collect_call_names_in_order(validator, validator_calls)
    if "exec_simulation" in validator_calls or "_run_od_reference_validation" in validator_calls:
        raise RuntimeError("Static validation must not simulate.")


def validate_static_contract() -> None:
    if VALIDATION_ONLY is not True:
        raise RuntimeError("This script must stay validation_only.")
    if NUM_VEHICLES != 3000:
        raise RuntimeError("NUM_VEHICLES must be 3000.")
    if DEPARTURE_START != 0 or DEPARTURE_END != 999:
        raise RuntimeError("Departure window must be T=0..999.")
    if DEMAND_GEN_SEED != 42 or RANDOM_SEED != 0:
        raise RuntimeError("Demand seed must be 42 and traffic seed must be 0.")
    if MIN_OD_MANHATTAN_DISTANCE != 5:
        raise RuntimeError("Manhattan filter must stay at 5.")
    if EXPECTED_UNIQUE_OD_PAIR_COUNT != 320:
        raise RuntimeError("Unique OD expectation must stay at 320.")
    if REPLAY_RUN_COUNT != 2:
        raise RuntimeError("Each OD must be replayed twice.")
    if DELTAN != 1 or REACTION_TIME != 1 or EXPECTED_DELTAT != 1:
        raise RuntimeError("The free-flow world must use DELTAN=1 and DELTAT=1.")
    if FREE_FLOW_TMAX != 600:
        raise RuntimeError("Free-flow TMAX must stay at the documented 600 seconds.")
    if INTERNAL_LINK_LENGTH != 200 or OD_CONNECTOR_LENGTH != 200:
        raise RuntimeError("Every link length must be 200 m.")
    if FREE_FLOW_SPEED_KMH != 60:
        raise RuntimeError("Free-flow speed must be 60 km/h.")
    if len(ALL_LINK_SPECS) != TOTAL_LINK_COUNT:
        raise RuntimeError("Link spec count is not 168.")
    if EXPECTED_VEHICLE_PLAN_SHA256 != (
        "0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9"
    ):
        raise RuntimeError("Vehicle plan hash constant changed.")
    if MAX_EQUAL_SHORTEST_ROUTES != 10:
        raise RuntimeError("Equal-cost route cap must stay at 10.")
    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    _assert_no_git_command_execution(tree)
    _assert_static_call_scope(tree)
    cost_helper = _function_node(tree, "_route_length_over_u")
    if cost_helper is None:
        raise RuntimeError("length/u route cost helper is missing.")
    cost_source = ast.get_source_segment(source_text, cost_helper)
    if cost_source is None or "length" not in cost_source or ".u" not in cost_source:
        raise RuntimeError("Route cost must be computed from length/u.")


# ---------------------------------------------------------------------------
# 7. Run
# ---------------------------------------------------------------------------

def _run_od_reference_validation() -> int:
    if TRIAL_OUTPUT_DIR.exists():
        raise RuntimeError(f"Refusing to overwrite {TRIAL_OUTPUT_DIR}.")

    plans = generate_vehicle_plans()
    vehicle_plan_sha256 = verify_vehicle_plans(plans)
    od_records = extract_unique_od_pairs(plans)
    if len(od_records) != EXPECTED_UNIQUE_OD_PAIR_COUNT:
        raise RuntimeError(
            f"Unique OD pair count is {len(od_records)}, expected {EXPECTED_UNIQUE_OD_PAIR_COUNT}."
        )

    audit_world = _build_free_flow_world()
    graph = _build_length_over_u_graph(audit_world)

    replay_outcomes = []
    for od_record in od_records:
        replay_outcomes.append([None, None])

    timing_bucket = {}
    timing_checked = False
    for replay_index in range(REPLAY_RUN_COUNT):
        for od_index, od_record in enumerate(od_records):
            if od_index % 20 == 0:
                print(
                    f"replay {replay_index + 1}/{REPLAY_RUN_COUNT}: "
                    f"OD {od_index + 1}/{len(od_records)}"
                )
            origin = od_record["origin"]
            destination = od_record["destination"]
            theoretical_link_names, theoretical_cost = _theoretical_shortest(graph, origin, destination)
            observer = None
            if replay_index == 0 and od_index == 0:
                observer = timing_bucket
                timing_checked = True
            outcome = _simulate_unconstrained_route(
                origin,
                destination,
                theoretical_link_names,
                theoretical_cost,
                observer,
            )
            replay_outcomes[od_index][replay_index] = outcome
    if timing_checked is not True:
        raise RuntimeError("Route-choice timing probe did not run.")

    rows = []
    weighted_time_sum = 0.0
    minimum_trip_time = None
    maximum_trip_time = None
    route_identity_stable = 0
    route_identity_changed = 0
    for od_index, od_record in enumerate(od_records):
        first = replay_outcomes[od_index][0]
        second = replay_outcomes[od_index][1]
        comparison = _compare_replays(
            od_record["origin"],
            od_record["destination"],
            first,
            second,
        )
        if comparison["route_identity_match"] is True:
            route_identity_stable = route_identity_stable + 1
        else:
            route_identity_changed = route_identity_changed + 1
        weighted_time_sum = weighted_time_sum + first["travel_time"] * od_record["vehicle_count"]
        if minimum_trip_time is None or first["travel_time"] < minimum_trip_time:
            minimum_trip_time = first["travel_time"]
        if maximum_trip_time is None or first["travel_time"] > maximum_trip_time:
            maximum_trip_time = first["travel_time"]
        rows.append(_build_csv_row(od_record, first, second, comparison))

    representatives = _select_representative_ods(od_records, graph)
    representative_counts = _check_representative_equal_routes(representatives)
    total_world_count = EXPECTED_UNIQUE_OD_PAIR_COUNT * REPLAY_RUN_COUNT
    total_world_count = total_world_count + representative_counts["checked_route_count"]
    weighted_average = weighted_time_sum / NUM_VEHICLES
    audit_difference = (
        ROUTE_CONDITIONAL_MEAN_FREE_FLOW_TRIP_TIME_AUDIT_SECONDS - weighted_average
    )
    final_judgment = f"All {EXPECTED_UNIQUE_OD_PAIR_COUNT} OD pairs passed."

    summary = {
        "validation_only": True,
        "validation_scope": VALIDATION_SCOPE,
        "future_revalidation_note": FUTURE_REVALIDATION_NOTE,
        "production_awt_implemented": False,
        "production_awwt_implemented": False,
        "vehicle_plan_sha256": vehicle_plan_sha256,
        "vehicle_count": NUM_VEHICLES,
        "unique_od_pair_count": EXPECTED_UNIQUE_OD_PAIR_COUNT,
        "od_replay_run_count": REPLAY_RUN_COUNT,
        "total_world_count": total_world_count,
        "completed_od_count": EXPECTED_UNIQUE_OD_PAIR_COUNT,
        "shortest_cost_match_od_count": EXPECTED_UNIQUE_OD_PAIR_COUNT,
        "shortest_cost_mismatch_od_count": 0,
        "route_identity_stable_od_count": route_identity_stable,
        "route_identity_changed_od_count": route_identity_changed,
        "reference_travel_time_stable_od_count": EXPECTED_UNIQUE_OD_PAIR_COUNT,
        "reference_travel_time_mismatch_od_count": 0,
        "route_loop_od_count": 0,
        "minimum_od_reference_trip_time": minimum_trip_time,
        "maximum_od_reference_trip_time": maximum_trip_time,
        "weighted_average_od_reference_trip_time": weighted_average,
        "route_conditional_mean_free_flow_trip_time_audit_seconds": (
            ROUTE_CONDITIONAL_MEAN_FREE_FLOW_TRIP_TIME_AUDIT_SECONDS
        ),
        "route_conditional_audit_minus_weighted_od_reference": audit_difference,
        "weighted_average_is_official_awt": False,
        "representative_candidate_limit": MAX_EQUAL_SHORTEST_ROUTES,
        "representative_od_checks": representatives,
        "representative_equal_route_check_count": representative_counts["checked_route_count"],
        "representative_equal_route_time_match_count": representative_counts["matched_route_count"],
        "route_choice_timing_probe": timing_bucket,
        "theoretical_cost_method": (
            "networkx.shortest_path weight=float(link.length)/float(link.u). "
            "enumerate_k_shortest_routes is not called because it materializes every simple path."
        ),
        "link_name_identity_is_main_contract": False,
        "final_judgment": final_judgment,
    }
    lines = _summary_lines(summary)
    run_summary_text = "\n".join(lines) + "\n"
    _write_validation_outputs(rows, summary, run_summary_text)
    for line in lines:
        print(line)
    print("output directory:", TRIAL_OUTPUT_DIR)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--static-validate-only"]:
        validate_static_contract()
        print("static validation passed")
        return 0
    if len(argv) != 0:
        raise RuntimeError(f"Unknown arguments: {argv!r}.")
    return _run_od_reference_validation()


if __name__ == "__main__":
    raise SystemExit(main())
