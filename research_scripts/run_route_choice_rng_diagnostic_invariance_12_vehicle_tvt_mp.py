"""
Layer-2 invariance trial for the production-unchanged route-choice RNG diagnostic.

This script rebuilds the existing 12-vehicle single-cross TVT-MP scenario and
runs it twice in one process:

1. TVT-MP without the route-choice RNG diagnostic
2. TVT-MP with that diagnostic installed

The second run leaves the diagnostic in place while the real simulation calls
the TVT-MP driver. That driver pickles the real World for the baseline fork
and builds candidate local Worlds. The diagnostic proxy is not left on
World.rng, so those snapshots should not pickle the proxy.

Any formal mismatch raises RuntimeError. This script does not write a CSV or
an output directory.

This is not a production seed change.
This is not keyed randomization.
This is not common random numbers.
This is not the four-method common seed/RNG framework.
This is not a 3,000-vehicle formal run.

Run from the repository root::

    python research_scripts/run_route_choice_rng_diagnostic_invariance_12_vehicle_tvt_mp.py --static-validate-only
    python research_scripts/run_route_choice_rng_diagnostic_invariance_12_vehicle_tvt_mp.py
"""

from __future__ import annotations

import ast
import math
import sys
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import is_dataclass
from pathlib import Path

import numpy as np

from uxsim import World
import uxsim.uxsim as uxsim_module
from uxsim.order_control_tvt_mp_research_output import build_tvt_mp_research_output

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from route_choice_rng_diagnostic import (  # noqa: E402
    EVENT_KIND_IN_TRIP,
    EVENT_KIND_ORIGIN,
    ORIGIN_ADMISSION_ACCEPTED,
    ORIGIN_ADMISSION_REJECTED,
    PROBABILITY_MODE_OMITTED,
    PROBABILITY_MODE_PROVIDED,
    RouteChoiceRngDiagnosticSession,
    capture_rng_state_fingerprint,
    decision_location_key,
    install_route_choice_rng_diagnostic,
    restore_route_choice_rng_diagnostic,
    route_choice_diagnostic_events,
    validate_restored_route_choice_rng_diagnostic,
)
from tvt_mp_full_run_audit_helper import (  # noqa: E402
    finalize_tvt_mp_full_run_audit,
    install_tvt_mp_full_run_audit,
)


# ---------------------------------------------------------------------------
# Constants. Both runs use this same scenario label and World name.
# ---------------------------------------------------------------------------

SCENARIO_NAME = "tvt_mp_single_cross_intersection_12_vehicle_trial"
WORLD_DISPLAY_NAME = "tvt_mp_single_cross_intersection_12_vehicle"
DIAGNOSTIC_RUN_METHOD = "tvt_mp_12_vehicle_layer2"

TRAFFIC_SEED = 0
VOT_SEED = 1

VOT_LOG_MU = -math.log(10) / 2
VOT_LOG_SIGMA = math.sqrt(math.log(10))

EVALUATION_START_TIMESTEP = 0
EVALUATION_END_TIMESTEP = 299
INTERNAL_TSIZE = 330
EXPECTED_WORLD_T_AFTER_SIM = EVALUATION_END_TIMESTEP + 1

BASELINE_HORIZON_STEPS = 30
MAX_CANDIDATE_VISIT_COUNT = 10

FREE_FLOW_SPEED_M_PER_S = 60000 / 3600
LINK_LENGTH_M = 200
NUMBER_OF_LANES = 1

CENTRAL_INTERSECTION_NODE = "intersection"
PERIPHERAL_NODE_NAMES = ("north", "east", "south", "west")
ORIGIN_DEPARTURE_ORDER = PERIPHERAL_NODE_NAMES

LINK_SPECS = (
    ("north_to_intersection", "north", "intersection"),
    ("intersection_to_north", "intersection", "north"),
    ("east_to_intersection", "east", "intersection"),
    ("intersection_to_east", "intersection", "east"),
    ("south_to_intersection", "south", "intersection"),
    ("intersection_to_south", "intersection", "south"),
    ("west_to_intersection", "west", "intersection"),
    ("intersection_to_west", "intersection", "west"),
)

# Minimums follow the existing full-run audit validation: at least one buyer
# and one seller, and zero nonparticipating rows. Exact transaction totals are
# not fixed here.
MINIMUM_ORIGIN_DRAWS = 12
MINIMUM_IN_TRIP_DRAWS = 12
MINIMUM_DIAGNOSTIC_EVENTS = 24
MINIMUM_PROBABILITY_PROVIDED = 1
MINIMUM_TRANSACTIONS = 1
MINIMUM_BUYER_VISITS = 1
MINIMUM_SELLER_VISITS = 1


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_name: str
    orig: str
    dest: str
    departure_timestep: int
    participating: bool


@dataclass
class VehicleVotRecord:
    vehicle_name: str
    origin: str
    destination: str
    departure_timestep: int
    participates_in_order_exchange: bool
    true_vot_per_second: float
    declared_vot_per_second: float | None


def _build_vehicle_specs() -> tuple:
    """Same 12 vehicles as the existing single-cross trial.

    At one departure timestep the origin order is north, east, south, west.
    """
    raw_rows = [
        ("veh_n1", "north", "south", 5),
        ("veh_e1", "east", "west", 5),
        ("veh_s1", "south", "north", 5),
        ("veh_w1", "west", "east", 5),
        ("veh_n2", "north", "east", 9),
        ("veh_e2", "east", "south", 9),
        ("veh_s2", "south", "west", 9),
        ("veh_w2", "west", "north", 9),
        ("veh_n3", "north", "west", 13),
        ("veh_e3", "east", "north", 13),
        ("veh_s3", "south", "east", 13),
        ("veh_w3", "west", "south", 13),
    ]
    specs = []
    for name, orig, dest, departure in raw_rows:
        specs.append(
            VehicleSpec(
                vehicle_name=name,
                orig=orig,
                dest=dest,
                departure_timestep=departure,
                participating=True,
            )
        )

    def sort_key(spec: VehicleSpec) -> tuple:
        origin_order = ORIGIN_DEPARTURE_ORDER.index(spec.orig)
        return (spec.departure_timestep, origin_order)

    specs.sort(key=sort_key)
    return tuple(specs)


VEHICLE_SPECS = _build_vehicle_specs()


# ---------------------------------------------------------------------------
# Vehicle plan and VOT. Each run draws from VOT seed 1 in this same order.
# ---------------------------------------------------------------------------


def generate_vehicle_vots(rng: np.random.Generator, count: int) -> list:
    """One lognormal draw per vehicle, in VEHICLE_SPECS order."""
    samples = rng.lognormal(mean=VOT_LOG_MU, sigma=VOT_LOG_SIGMA, size=count)
    values = []
    for value in samples:
        values.append(float(value))
    return values


def build_vehicle_vot_records(specs: tuple, vot_values: list) -> list:
    records = []
    for spec, vot in zip(specs, vot_values):
        if spec.participating:
            declared = vot
        else:
            declared = None
        records.append(
            VehicleVotRecord(
                vehicle_name=spec.vehicle_name,
                origin=spec.orig,
                destination=spec.dest,
                departure_timestep=spec.departure_timestep,
                participates_in_order_exchange=spec.participating,
                true_vot_per_second=vot,
                declared_vot_per_second=declared,
            )
        )
    return records


def build_vot_plan(vot_records: list) -> list:
    """Order-stable VOT plan. This is the comparison record, not a CSV."""
    rows = []
    for record in vot_records:
        rows.append(
            {
                "vehicle_name": record.vehicle_name,
                "origin": record.origin,
                "destination": record.destination,
                "departure_timestep": record.departure_timestep,
                "participates_in_order_exchange": record.participates_in_order_exchange,
                "true_vot_per_second": record.true_vot_per_second,
                "declared_vot_per_second": record.declared_vot_per_second,
                "traffic_seed": TRAFFIC_SEED,
                "vot_seed": VOT_SEED,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# World builder and vehicle addition
# ---------------------------------------------------------------------------


def build_world_and_network() -> World:
    """Same network and TVT settings as the existing 12-vehicle trial."""
    world = World(
        name=WORLD_DISPLAY_NAME,
        deltan=1,
        reaction_time=1,
        tmax=INTERNAL_TSIZE,
        random_seed=TRAFFIC_SEED,
        print_mode=1,
        save_mode=0,
        show_mode=0,
        show_progress=1,
    )
    world.addNode("intersection", 0, 0)
    world.addNode("north", 0, 1)
    world.addNode("east", 1, 0)
    world.addNode("south", 0, -1)
    world.addNode("west", -1, 0)
    for link_name, upstream, downstream in LINK_SPECS:
        world.addLink(
            link_name,
            upstream,
            downstream,
            length=LINK_LENGTH_M,
            free_flow_speed=FREE_FLOW_SPEED_M_PER_S,
            number_of_lanes=NUMBER_OF_LANES,
        )
    world.infer_order_control_eligible_nodes()
    world.set_order_control_for_nodes(
        [CENTRAL_INTERSECTION_NODE],
        order_control_type="time_value",
        transaction_case=None,
    )
    clearance = world.order_control_clearance_timesteps
    if clearance != 1:
        raise RuntimeError(
            f"Expected order_control_clearance_timesteps=1, got {clearance!r}."
        )
    world.order_control_tvt_evaluation_end_timestep = EVALUATION_END_TIMESTEP
    world.order_control_tvt_baseline_horizon_steps = BASELINE_HORIZON_STEPS
    world.order_control_tvt_max_candidate_visit_count = MAX_CANDIDATE_VISIT_COUNT
    return world


def add_vehicles_to_world(world: World, specs: tuple, vot_records: list) -> None:
    """OD-only addVehicle. No specified_route and no manual placement."""
    for spec, vot_record in zip(specs, vot_records):
        kwargs = {
            "name": spec.vehicle_name,
            "departure_time_is_time_step": 1,
            "vot_true": vot_record.true_vot_per_second,
            "participates_in_order_exchange": spec.participating,
        }
        if spec.participating:
            kwargs["vot_declared"] = vot_record.declared_vot_per_second
        else:
            kwargs["vot_declared"] = None
        world.addVehicle(
            spec.orig,
            spec.dest,
            spec.departure_timestep,
            **kwargs,
        )


def prepare_fresh_world() -> tuple:
    """New World, new VOT draws from seed 1, same plan as the other run."""
    vot_rng = np.random.default_rng(VOT_SEED)
    vot_values = generate_vehicle_vots(vot_rng, len(VEHICLE_SPECS))
    vot_records = build_vehicle_vot_records(VEHICLE_SPECS, vot_values)
    world = build_world_and_network()
    add_vehicles_to_world(world, VEHICLE_SPECS, vot_records)
    return world, vot_records


def verify_evaluation_end(world: World) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"After exec_simulation, expected World.T=={EXPECTED_WORLD_T_AFTER_SIM}, "
            f"got {world.T!r}."
        )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    expected_fields = (
        "evaluation_end_unobserved_finalized_timestep",
        "trade_ex_post_evaluation_finalized_timestep",
        "individual_ex_post_evaluation_finalized_timestep",
    )
    for field_name in expected_fields:
        actual = getattr(registry, field_name)
        if actual != EVALUATION_END_TIMESTEP:
            raise RuntimeError(
                f"Registry {field_name} expected {EVALUATION_END_TIMESTEP}, "
                f"got {actual!r}."
            )


def _require_tsize(world: World) -> None:
    if world.TSIZE != INTERNAL_TSIZE:
        raise RuntimeError(
            f"Expected TSIZE=={INTERNAL_TSIZE} after finalize, got {world.TSIZE}."
        )


# ---------------------------------------------------------------------------
# Canonical values. NaN matches NaN. No rounding and no tolerance.
# ---------------------------------------------------------------------------


def _canonical_number(value):
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if math.isnan(value):
            return {"__nan__": True}
        return value
    raise RuntimeError(
        f"Expected a number or None, got {type(value).__name__}: {value!r}."
    )


def _canonical_value(value):
    """Turn one formal value into nested lists and dicts."""
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (str,)):
        return value
    if isinstance(value, (int, float, np.integer, np.floating)):
        return _canonical_number(value)
    if isinstance(value, np.ndarray):
        converted = []
        for item in value.tolist():
            converted.append(_canonical_value(item))
        return converted
    if is_dataclass(value):
        return _canonical_dataclass(value)
    if isinstance(value, dict):
        converted = {}
        for key in sorted(value.keys(), key=str):
            converted[str(key)] = _canonical_value(value[key])
        return converted
    if isinstance(value, (list, tuple)):
        converted = []
        for item in value:
            converted.append(_canonical_value(item))
        return converted
    raise RuntimeError(
        "Formal snapshot cannot convert "
        f"{type(value).__name__}: {value!r}."
    )


def _canonical_dataclass(row) -> dict:
    converted = {}
    for field in fields(row):
        converted[field.name] = _canonical_value(getattr(row, field.name))
    return converted


def _compare_values(path: str, left, right) -> None:
    if type(left) is not type(right):
        raise RuntimeError(
            f"Snapshot type mismatch at {path}: "
            f"without_diagnostic={left!r} ({type(left).__name__}), "
            f"with_diagnostic={right!r} ({type(right).__name__})."
        )
    if isinstance(left, dict):
        left_keys = sorted(left.keys())
        right_keys = sorted(right.keys())
        if left_keys != right_keys:
            raise RuntimeError(
                f"Snapshot field mismatch at {path}: "
                f"without_diagnostic keys {left_keys}, "
                f"with_diagnostic keys {right_keys}."
            )
        for key in left_keys:
            _compare_values(f"{path}.{key}", left[key], right[key])
        return
    if isinstance(left, list):
        if len(left) != len(right):
            raise RuntimeError(
                f"Snapshot length mismatch at {path}: "
                f"without_diagnostic={len(left)}, with_diagnostic={len(right)}."
            )
        index = 0
        while index < len(left):
            _compare_values(f"{path}[{index}]", left[index], right[index])
            index = index + 1
        return
    if left != right:
        raise RuntimeError(
            f"Snapshot value mismatch at {path}: "
            f"without_diagnostic={left!r}, with_diagnostic={right!r}."
        )


# ---------------------------------------------------------------------------
# Research bundle snapshot. Row order is the builder's order.
# transactions: transaction key sort
# visits: that same transaction order, then buyer / seller / nonparticipating
# vehicles: vehicle name sort
# nodes: node name sort
# ---------------------------------------------------------------------------


def _canonical_research_bundle(bundle) -> dict:
    if bundle.scenario_name != SCENARIO_NAME:
        raise RuntimeError(
            f"Research bundle scenario_name is {bundle.scenario_name!r}, "
            f"expected {SCENARIO_NAME!r}."
        )
    return {
        "scenario_name": bundle.scenario_name,
        "transactions": _canonical_value(bundle.transactions),
        "visits": _canonical_value(bundle.visits),
        "vehicles": _canonical_value(bundle.vehicles),
        "nodes": _canonical_value(bundle.nodes),
        "scenario": _canonical_value(bundle.scenario),
    }


# ---------------------------------------------------------------------------
# Audit snapshot. Row order is the helper freeze order:
# decision_timestep, node_name, candidate_identity, then party order.
# ---------------------------------------------------------------------------


def _canonical_audit_result(audit_result) -> dict:
    return {
        "transaction_rows": _canonical_value(audit_result.transaction_rows),
        "visit_rows": _canonical_value(audit_result.visit_rows),
    }


def _require_audit_and_research_minimums(bundle, audit_result) -> None:
    """Same buyer / seller / FIFO checks as the existing audit validation.

    Values are read from the frozen rows. Nothing is written to disk.
    """
    transaction_rows = audit_result.transaction_rows
    visit_rows = audit_result.visit_rows
    if len(transaction_rows) != len(bundle.transactions):
        raise RuntimeError(
            "Transaction audit row count "
            f"{len(transaction_rows)} != research transactions "
            f"{len(bundle.transactions)}."
        )
    if len(visit_rows) != len(bundle.visits):
        raise RuntimeError(
            f"Visit audit row count {len(visit_rows)} != research visits "
            f"{len(bundle.visits)}."
        )
    if len(bundle.transactions) < MINIMUM_TRANSACTIONS:
        raise RuntimeError(
            f"Research transactions {len(bundle.transactions)} "
            f"< {MINIMUM_TRANSACTIONS}."
        )
    if len(bundle.scenario) != 1:
        raise RuntimeError(
            f"Research scenario rows must be 1, got {len(bundle.scenario)}."
        )
    scenario_row = bundle.scenario[0]
    if scenario_row.transaction_count != len(bundle.transactions):
        raise RuntimeError(
            "Scenario transaction_count "
            f"{scenario_row.transaction_count} != transaction rows "
            f"{len(bundle.transactions)}."
        )
    if scenario_row.nonparticipating_visit_count != 0:
        raise RuntimeError(
            "Scenario nonparticipating_visit_count is "
            f"{scenario_row.nonparticipating_visit_count}, expected 0."
        )

    for index, row in enumerate(transaction_rows):
        role_sum = row.buyer_count + row.seller_count + row.nonparticipating_count
        if role_sum != row.trade_scope_count:
            raise RuntimeError(
                f"Transaction audit row {index}: "
                "buyer+seller+nonparticipating != trade_scope_count: "
                f"{row.buyer_count}+{row.seller_count}+"
                f"{row.nonparticipating_count} != {row.trade_scope_count}."
            )
        if row.fifo_inspection_passed is not True:
            raise RuntimeError(
                f"Transaction audit row {index}: fifo_inspection_passed is "
                f"{row.fifo_inspection_passed!r}, expected True."
            )
        if row.fifo_violation_count < 0:
            raise RuntimeError(
                f"Transaction audit row {index}: fifo_violation_count is "
                f"{row.fifo_violation_count!r}."
            )
        for count_name in (
            "max_same_inlink_party_count",
            "max_same_inlink_buyer_count",
            "max_same_inlink_seller_count",
            "max_same_inlink_nonparticipating_count",
        ):
            count_value = getattr(row, count_name)
            if count_value < 0:
                raise RuntimeError(
                    f"Transaction audit row {index}: {count_name} is {count_value!r}."
                )

    buyer_row_count = 0
    seller_row_count = 0
    nonparticipating_row_count = 0
    for index, row in enumerate(visit_rows):
        if row.role == "buyer":
            buyer_row_count = buyer_row_count + 1
            if row.buyer_value_G_b is None or row.payment_P_b is None:
                raise RuntimeError(
                    f"Visit audit buyer row {index} is missing G_b or payment_P_b."
                )
        elif row.role == "seller":
            seller_row_count = seller_row_count + 1
            if (
                row.seller_required_compensation_R_s is None
                or row.compensation_C_s is None
            ):
                raise RuntimeError(
                    f"Visit audit seller row {index} is missing R_s or compensation_C_s."
                )
        elif row.role == "nonparticipating":
            nonparticipating_row_count = nonparticipating_row_count + 1
        else:
            raise RuntimeError(
                f"Visit audit row {index}: unknown role {row.role!r}."
            )
        for required_name in (
            "inlink_name",
            "baseline_arrival_timestep",
            "baseline_local_rank",
            "post_trade_local_rank",
            "assigned_rank",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
        ):
            if getattr(row, required_name) is None:
                raise RuntimeError(
                    f"Visit audit row {index}: missing {required_name}."
                )
        if row.same_inlink_fifo_preserved is not True:
            raise RuntimeError(
                f"Visit audit row {index}: same_inlink_fifo_preserved is "
                f"{row.same_inlink_fifo_preserved!r}, expected True."
            )
        if (
            row.actual_node_arrival_timestep is not None
            and row.actual_passage_timestep is not None
            and row.actual_passage_timestep < row.actual_node_arrival_timestep + 1
        ):
            raise RuntimeError(
                f"Visit audit row {index}: actual_passage_timestep "
                f"{row.actual_passage_timestep} is before actual arrival "
                f"{row.actual_node_arrival_timestep} + 1."
            )

    if buyer_row_count < MINIMUM_BUYER_VISITS:
        raise RuntimeError(
            f"Buyer visit rows {buyer_row_count} < {MINIMUM_BUYER_VISITS}."
        )
    if seller_row_count < MINIMUM_SELLER_VISITS:
        raise RuntimeError(
            f"Seller visit rows {seller_row_count} < {MINIMUM_SELLER_VISITS}."
        )
    if nonparticipating_row_count != 0:
        raise RuntimeError(
            f"Nonparticipating visit rows {nonparticipating_row_count}, expected 0."
        )


# ---------------------------------------------------------------------------
# Vehicle, Link, and World snapshots
# ---------------------------------------------------------------------------


def _link_name(link):
    if link is None:
        return None
    return link.name


def _canonical_log_t_link(vehicle) -> list:
    rows = []
    for entry in vehicle.log_t_link:
        label = entry[1]
        if isinstance(label, str):
            label_name = label
        else:
            label_name = label.name
        rows.append([_canonical_number(entry[0]), label_name])
    return rows


def _canonical_named_number_dict(raw_dict) -> dict:
    converted = {}
    for key in sorted(raw_dict.keys()):
        converted[str(key)] = _canonical_number(raw_dict[key])
    return converted


def _canonical_current_visit(visit):
    if visit is None:
        return None
    return {
        "visit_id": _canonical_number(visit["visit_id"]),
        "node_name": visit["node"].name,
        "inlink_name": visit["inlink"].name,
        "earliest_arrival_timestep": _canonical_number(
            visit["earliest_arrival_timestep"]
        ),
        "arrival_time": _canonical_number(visit["arrival_time"]),
        "arrival_tiebreaker": _canonical_number(visit["arrival_tiebreaker"]),
        "batch_assignment": _canonical_value(visit["batch_assignment"]),
    }


def _canonical_vehicle_row(vehicle) -> dict:
    return {
        "name": vehicle.name,
        "state": vehicle.state,
        "origin": vehicle.orig.name,
        "destination": vehicle.dest.name,
        "departure_time": _canonical_number(vehicle.departure_time),
        "travel_time": _canonical_number(vehicle.travel_time),
        "current_link_name": _link_name(vehicle.link),
        "route_next_link_name": _link_name(vehicle.route_next_link),
        "x": _canonical_number(vehicle.x),
        "v": _canonical_number(vehicle.v),
        "link_arrival_time": _canonical_number(vehicle.link_arrival_time),
        "log_t_link": _canonical_log_t_link(vehicle),
        "order_control_visit_id": _canonical_number(vehicle.order_control_visit_id),
        "order_control_current_visit": _canonical_current_visit(
            vehicle.order_control_current_visit
        ),
        "order_control_node_arrival_times": _canonical_named_number_dict(
            vehicle.order_control_node_arrival_times
        ),
        "order_control_node_arrival_tiebreakers": _canonical_named_number_dict(
            vehicle.order_control_node_arrival_tiebreakers
        ),
        "payment_paid": _canonical_number(vehicle.payment_paid),
        "payment_received": _canonical_number(vehicle.payment_received),
        "true_vot_per_second": _canonical_number(vehicle.vot_true),
        "declared_vot_per_second": _canonical_number(vehicle.vot_declared),
        "participates_in_order_exchange": bool(vehicle.participates_in_order_exchange),
    }


def _canonical_vehicle_rows(world: World) -> list:
    rows = []
    for vehicle_name in sorted(world.VEHICLES.keys()):
        rows.append(_canonical_vehicle_row(world.VEHICLES[vehicle_name]))
    return rows


def _canonical_enter_log(link) -> list:
    """One vehicle per timestamp. This log can overwrite an earlier vehicle."""
    rows = []
    for timestep_key in sorted(link.vehicles_enter_log.keys()):
        vehicle = link.vehicles_enter_log[timestep_key]
        rows.append([_canonical_number(timestep_key), vehicle.name])
    return rows


def _vehicle_names_on_link(link) -> list:
    names = []
    for vehicle in link.vehicles:
        names.append(vehicle.name)
    return names


def _canonical_link_row(link) -> dict:
    return {
        "name": link.name,
        "capacity_in": _canonical_number(link.capacity_in),
        "capacity_in_remain": _canonical_number(link.capacity_in_remain),
        "capacity_out": _canonical_number(link.capacity_out),
        "capacity_out_remain": _canonical_number(link.capacity_out_remain),
        "cum_arrival": _canonical_value(np.asarray(link.cum_arrival)),
        "cum_departure": _canonical_value(np.asarray(link.cum_departure)),
        "traveltime_actual": _canonical_value(np.asarray(link.traveltime_actual)),
        "vehicles_enter_log": _canonical_enter_log(link),
        "vehicle_names_in_link_order": _vehicle_names_on_link(link),
    }


def _canonical_link_rows(world: World) -> list:
    rows = []
    link_names = sorted(link.name for link in world.LINKS)
    for link_name in link_names:
        rows.append(_canonical_link_row(world.get_link(link_name)))
    return rows


def _decision_timesteps(audit_result) -> list:
    timesteps = []
    for row in audit_result.transaction_rows:
        timesteps.append(int(row.decision_timestep))
    return timesteps


def _completed_vehicle_count(world: World) -> int:
    completed = 0
    for vehicle in world.VEHICLES.values():
        if vehicle.state == "end":
            completed = completed + 1
    return completed


def _canonical_world_section(world: World, bundle, audit_result) -> dict:
    """RNG fingerprints and the TVT counters this script can read.

    Production does not store a driver call counter. The compared field is
    order_control_tvt_driver_started_timestep, which the driver sets to the
    current timestep on each accepted entry and leaves at the last one.
    decision_timesteps follows the frozen audit transaction row order.
    """
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    rng_json, rng_sha = capture_rng_state_fingerprint(world.rng)
    order_json, order_sha = capture_rng_state_fingerprint(world.order_control_rng)
    return {
        "world_t": int(world.T),
        "world_time": _canonical_number(world.TIME),
        "tsize": int(world.TSIZE),
        "completed_vehicle_count": _completed_vehicle_count(world),
        "rng_canonical_json": rng_json,
        "rng_sha256": rng_sha,
        "order_control_rng_canonical_json": order_json,
        "order_control_rng_sha256": order_sha,
        "evaluation_end_unobserved_finalized_timestep": int(
            registry.evaluation_end_unobserved_finalized_timestep
        ),
        "trade_ex_post_evaluation_finalized_timestep": int(
            registry.trade_ex_post_evaluation_finalized_timestep
        ),
        "individual_ex_post_evaluation_finalized_timestep": int(
            registry.individual_ex_post_evaluation_finalized_timestep
        ),
        "tvt_driver_last_started_timestep": _canonical_number(
            world.order_control_tvt_driver_started_timestep
        ),
        "transaction_count": len(bundle.transactions),
        "visit_count": len(bundle.visits),
        "decision_timesteps": _decision_timesteps(audit_result),
    }


def build_formal_snapshot(world: World, vot_records: list, bundle, audit_result) -> dict:
    return {
        "research_bundle": _canonical_research_bundle(bundle),
        "full_run_audit": _canonical_audit_result(audit_result),
        "vehicles": _canonical_vehicle_rows(world),
        "links": _canonical_link_rows(world),
        "world": _canonical_world_section(world, bundle, audit_result),
        "vot_plan": _canonical_value(build_vot_plan(vot_records)),
    }


def compare_formal_snapshots(without_snapshot: dict, with_snapshot: dict) -> None:
    _compare_values("formal", without_snapshot, with_snapshot)


# ---------------------------------------------------------------------------
# Route diagnostic validation
# ---------------------------------------------------------------------------


def _require_contiguous(ordinals, label: str) -> None:
    expected = 1
    for ordinal in ordinals:
        if ordinal != expected:
            raise RuntimeError(
                f"{label} gap: saw {ordinal}, expected {expected}."
            )
        expected = expected + 1


def validate_diagnostic_events(session, events) -> None:
    if len(events) < MINIMUM_DIAGNOSTIC_EVENTS:
        raise RuntimeError(
            f"Diagnostic events {len(events)} < {MINIMUM_DIAGNOSTIC_EVENTS}."
        )
    draw_ordinals_by_vehicle = {}
    attempt_ordinals_by_location = {}
    for event in events:
        if event.world_kind != "real":
            raise RuntimeError(
                f"Event world_kind is {event.world_kind!r}, expected 'real'."
            )
        if event.choice_called is not True:
            continue
        if event.rng_state_fingerprint_before is None:
            raise RuntimeError(
                f"{event.vehicle_name} choice is missing the before fingerprint."
            )
        if event.rng_state_fingerprint_after is None:
            raise RuntimeError(
                f"{event.vehicle_name} choice is missing the after fingerprint."
            )
        if event.selected_link_name is None:
            raise RuntimeError(
                f"{event.vehicle_name} choice is missing selected_link_name."
            )
        if event.event_kind == EVENT_KIND_ORIGIN:
            if event.origin_admission not in (
                ORIGIN_ADMISSION_ACCEPTED,
                ORIGIN_ADMISSION_REJECTED,
            ):
                raise RuntimeError(
                    f"Origin event for {event.vehicle_name} has admission "
                    f"{event.origin_admission!r}."
                )
        elif event.event_kind == EVENT_KIND_IN_TRIP:
            if event.origin_admission is not None:
                raise RuntimeError(
                    f"In-trip event for {event.vehicle_name} has admission "
                    f"{event.origin_admission!r}."
                )
        else:
            raise RuntimeError(
                f"Unknown event_kind {event.event_kind!r} for {event.vehicle_name}."
            )
        if event.probability_mode == PROBABILITY_MODE_PROVIDED:
            if event.provided_probability_matches_recomputed is not True:
                raise RuntimeError(
                    f"{event.vehicle_name} p-provided choice did not match "
                    "the recomputed probability."
                )
        elif event.probability_mode == PROBABILITY_MODE_OMITTED:
            if event.provided_probability_matches_recomputed is not None:
                raise RuntimeError(
                    f"{event.vehicle_name} p-omitted choice has comparison flag "
                    f"{event.provided_probability_matches_recomputed!r}."
                )
        if event.vehicle_name not in draw_ordinals_by_vehicle:
            draw_ordinals_by_vehicle[event.vehicle_name] = []
        draw_ordinals_by_vehicle[event.vehicle_name].append(event.route_choice_ordinal)
        location_key = decision_location_key(event)
        if location_key not in attempt_ordinals_by_location:
            attempt_ordinals_by_location[location_key] = []
        attempt_ordinals_by_location[location_key].append(
            event.attempt_ordinal_at_location
        )
    for vehicle_name in draw_ordinals_by_vehicle:
        _require_contiguous(
            draw_ordinals_by_vehicle[vehicle_name],
            f"route_choice_ordinal for {vehicle_name}",
        )
    for location_key in attempt_ordinals_by_location:
        _require_contiguous(
            attempt_ordinals_by_location[location_key],
            f"attempt_ordinal_at_location for {location_key!r}",
        )


def _count_choice_events(events) -> dict:
    origin_draws = 0
    in_trip_draws = 0
    probability_provided = 0
    for event in events:
        if event.choice_called is not True:
            continue
        if event.event_kind == EVENT_KIND_ORIGIN:
            origin_draws = origin_draws + 1
        if event.event_kind == EVENT_KIND_IN_TRIP:
            in_trip_draws = in_trip_draws + 1
        if event.probability_mode == PROBABILITY_MODE_PROVIDED:
            probability_provided = probability_provided + 1
    return {
        "origin_draws": origin_draws,
        "in_trip_draws": in_trip_draws,
        "probability_provided": probability_provided,
    }


def validate_layer2_diagnostic_coverage(session, events) -> dict:
    """Require the real-World draws and the baseline-fork wrapper pass.

    order_control_baseline_driver calls fork_W.exec_simulation when the
    baseline visit set is not empty. That copied World is not the real World,
    so each Node.generate there increments virtual_node_generate_pass_count.
    A selected TVT transaction in this scenario goes through that fork.

    Candidate local vehicle advance does not call route_next_link_choice.
    virtual_route_choice_pass_count is therefore reported and not required.
    """
    counts = _count_choice_events(events)
    if counts["origin_draws"] < MINIMUM_ORIGIN_DRAWS:
        raise RuntimeError(
            f"Origin draws {counts['origin_draws']} < {MINIMUM_ORIGIN_DRAWS}."
        )
    if counts["in_trip_draws"] < MINIMUM_IN_TRIP_DRAWS:
        raise RuntimeError(
            f"In-trip draws {counts['in_trip_draws']} < {MINIMUM_IN_TRIP_DRAWS}."
        )
    if counts["probability_provided"] < MINIMUM_PROBABILITY_PROVIDED:
        raise RuntimeError(
            "p-provided events "
            f"{counts['probability_provided']} < {MINIMUM_PROBABILITY_PROVIDED}."
        )
    if session.virtual_node_generate_pass_count < 1:
        raise RuntimeError(
            "virtual_node_generate_pass_count is "
            f"{session.virtual_node_generate_pass_count}. "
            "A non-empty baseline fork calls exec_simulation, which calls "
            "Node.generate on the copied World."
        )
    if session.proxy_pickle_rejection_count != 0:
        raise RuntimeError(
            "proxy_pickle_rejection_count is "
            f"{session.proxy_pickle_rejection_count}."
        )
    counts["virtual_node_generate_pass_count"] = session.virtual_node_generate_pass_count
    counts["virtual_route_choice_pass_count"] = session.virtual_route_choice_pass_count
    counts["proxy_pickle_rejection_count"] = session.proxy_pickle_rejection_count
    counts["diagnostic_event_count"] = len(events)
    return counts


def _validate_diagnostic_restoration(session) -> None:
    validate_restored_route_choice_rng_diagnostic(session)
    if uxsim_module.Node.generate is not session.original_node_generate:
        raise RuntimeError("Node.generate was not restored by identity.")
    if (
        uxsim_module.Vehicle.route_next_link_choice
        is not session.original_route_next_link_choice
    ):
        raise RuntimeError(
            "Vehicle.route_next_link_choice was not restored by identity."
        )
    if session.real_world.rng is not session.original_generator:
        raise RuntimeError("real_world.rng is not the original Generator object.")
    if not isinstance(session.real_world.rng, np.random.Generator):
        raise RuntimeError("real_world.rng is not numpy.random.Generator.")
    if len(session.generator_restore_failure_messages) != 0:
        raise RuntimeError(
            "generator_restore_failure_messages is not empty: "
            f"{session.generator_restore_failure_messages!r}."
        )
    if len(session.call_count_violation_messages) != 0:
        raise RuntimeError(
            "call_count_violation_messages is not empty: "
            f"{session.call_count_violation_messages!r}."
        )
    if session.proxy_pickle_rejection_count != 0:
        raise RuntimeError(
            "proxy_pickle_rejection_count is "
            f"{session.proxy_pickle_rejection_count}."
        )


# ---------------------------------------------------------------------------
# One run without the diagnostic, then one run with it.
# The audit helper keeps one module-level state, so the first finalize must
# finish before the second install.
# finalize_tvt_mp_full_run_audit requires the research bundle, so the bundle
# is built first. That is the existing validation order.
# ---------------------------------------------------------------------------


def _execute_audited_simulation(world: World) -> None:
    """Install the audit, then run the one simulation shared by both runs."""
    _require_tsize(world)
    install_tvt_mp_full_run_audit(world)
    world.exec_simulation()


def _collect_formal_snapshot(world: World, vot_records: list) -> dict:
    """Build the bundle, then finalize the audit. The helper requires that order."""
    verify_evaluation_end(world)
    bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
    audit_result = finalize_tvt_mp_full_run_audit(world, bundle)
    _require_audit_and_research_minimums(bundle, audit_result)
    return build_formal_snapshot(world, vot_records, bundle, audit_result)


def run_without_route_choice_diagnostic() -> dict:
    world, vot_records = prepare_fresh_world()
    world.finalize_scenario()
    _execute_audited_simulation(world)
    return _collect_formal_snapshot(world, vot_records)


def run_with_route_choice_diagnostic() -> tuple:
    world, vot_records = prepare_fresh_world()
    session = RouteChoiceRngDiagnosticSession(
        world,
        run_method=DIAGNOSTIC_RUN_METHOD,
    )
    install_route_choice_rng_diagnostic(session)
    try:
        world.finalize_scenario()
        _execute_audited_simulation(world)
    finally:
        restore_route_choice_rng_diagnostic(session)
    _validate_diagnostic_restoration(session)
    events = route_choice_diagnostic_events(session)
    validate_diagnostic_events(session, events)
    coverage = validate_layer2_diagnostic_coverage(session, events)
    snapshot = _collect_formal_snapshot(world, vot_records)
    return snapshot, coverage


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _role_counts(snapshot: dict) -> dict:
    buyer_count = 0
    seller_count = 0
    for row in snapshot["full_run_audit"]["visit_rows"]:
        if row["role"] == "buyer":
            buyer_count = buyer_count + 1
        elif row["role"] == "seller":
            seller_count = seller_count + 1
    return {
        "buyer_count": buyer_count,
        "seller_count": seller_count,
    }


def print_success_summary(snapshot: dict, coverage: dict) -> None:
    roles = _role_counts(snapshot)
    world_section = snapshot["world"]
    print(f"vehicle_count={len(snapshot['vehicles'])}")
    print(f"transaction_count={world_section['transaction_count']}")
    print(f"visit_count={world_section['visit_count']}")
    print(f"buyer_count={roles['buyer_count']}")
    print(f"seller_count={roles['seller_count']}")
    print(f"diagnostic_event_count={coverage['diagnostic_event_count']}")
    print(f"real_origin_draw_count={coverage['origin_draws']}")
    print(f"real_in_trip_draw_count={coverage['in_trip_draws']}")
    print(
        "virtual_node_generate_pass_count="
        f"{coverage['virtual_node_generate_pass_count']}"
    )
    print(
        "virtual_route_choice_pass_count="
        f"{coverage['virtual_route_choice_pass_count']}"
    )
    print(
        "proxy_pickle_rejection_count="
        f"{coverage['proxy_pickle_rejection_count']}"
    )
    print("formal_research_bundle_match=True")
    print("full_run_audit_match=True")
    print("vehicle_state_match=True")
    print("link_state_match=True")
    print("final_rng_state_match=True")
    print("final_order_control_rng_state_match=True")
    print("method_restoration_passed=True")
    print("layer_2_all_passed=True")
    print("baseline_candidate_pickle_path_exercised=True")
    print("proxy_pickle_contamination_not_observed=True")
    print("production_files_modified=False")
    print("existing_outputs_modified=False")
    print("keyed_randomization_used=False")
    print("layer_1_and_layer_2_invariance_confirmed=True")


def run_layer2_invariance() -> None:
    without_snapshot = run_without_route_choice_diagnostic()
    with_snapshot, coverage = run_with_route_choice_diagnostic()
    compare_formal_snapshots(without_snapshot, with_snapshot)
    if coverage["virtual_node_generate_pass_count"] < 1:
        raise RuntimeError(
            "Refusing to report baseline pickle exercise without a virtual "
            "Node.generate pass."
        )
    if coverage["proxy_pickle_rejection_count"] != 0:
        raise RuntimeError(
            "Refusing to report a clean pickle path with proxy rejections."
        )
    print_success_summary(with_snapshot, coverage)


# ---------------------------------------------------------------------------
# Static validation. This parses the source and does not simulate.
# ---------------------------------------------------------------------------


def _call_name(node: ast.AST):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _function_defs(tree: ast.AST) -> dict:
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = node
    return found


def _calls_in_function(function_def: ast.FunctionDef) -> list:
    calls = []
    for node in ast.walk(function_def):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name is None:
            continue
        calls.append((node.lineno, name))
    return calls


def _count_name(calls: list, name: str) -> int:
    count = 0
    for _line_number, call_name in calls:
        if call_name == name:
            count = count + 1
    return count


def _first_line(calls: list, name: str):
    for line_number, call_name in calls:
        if call_name == name:
            return line_number
    return None


def _require_before(calls: list, first: str, second: str, function_name: str) -> None:
    first_line = _first_line(calls, first)
    second_line = _first_line(calls, second)
    if first_line is None or second_line is None:
        raise RuntimeError(
            f"Static validation: {function_name} must call {first} and {second}."
        )
    if first_line >= second_line:
        raise RuntimeError(
            f"Static validation: {function_name} must call {first} before {second}."
        )


def _finally_calls_restore(function_def: ast.FunctionDef) -> bool:
    for node in ast.walk(function_def):
        if not isinstance(node, ast.Try):
            continue
        for statement in node.finalbody:
            for child in ast.walk(statement):
                if isinstance(child, ast.Call):
                    if _call_name(child.func) == "restore_route_choice_rng_diagnostic":
                        return True
    return False


# Names checked only on real AST import and call nodes, not in comments or strings.
_FORBIDDEN_IMPORTED_NAMES = (
    "write_tvt_mp_research_output_csv",
    "write_tvt_mp_full_run_audit_csv",
)
_FORBIDDEN_IMPORTED_MODULE_NAMES = (
    "run_tvt_mp_single_cross_intersection_12_vehicle_trial",
    "run_tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation",
)
_FORBIDDEN_CALL_NAME_IDS = (
    "write_tvt_mp_research_output_csv",
    "write_tvt_mp_full_run_audit_csv",
    "open",
    "mkdir",
    "write_text",
    "to_csv",
)
_FORBIDDEN_CALL_ATTRIBUTE_NAMES = (
    "mkdir",
    "write_text",
    "to_csv",
)


def _raise_forbidden_static(kind: str, name: str, line_number: int) -> None:
    raise RuntimeError(
        f"Static validation: forbidden {kind} {name!r} at line {line_number}."
    )


def _assert_no_forbidden_imports(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                if imported_name in _FORBIDDEN_IMPORTED_MODULE_NAMES:
                    _raise_forbidden_static("import", imported_name, node.lineno)
                for forbidden_name in _FORBIDDEN_IMPORTED_NAMES:
                    if imported_name == forbidden_name:
                        _raise_forbidden_static("import", forbidden_name, node.lineno)
            continue
        if isinstance(node, ast.ImportFrom):
            module_name = node.module
            if module_name in _FORBIDDEN_IMPORTED_MODULE_NAMES:
                _raise_forbidden_static("import", module_name, node.lineno)
            for alias in node.names:
                imported_name = alias.name
                if imported_name in _FORBIDDEN_IMPORTED_NAMES:
                    _raise_forbidden_static("import", imported_name, node.lineno)


def _assert_no_forbidden_calls(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in _FORBIDDEN_CALL_NAME_IDS:
                _raise_forbidden_static("call", func.id, node.lineno)
            continue
        if isinstance(func, ast.Attribute):
            if func.attr in _FORBIDDEN_CALL_ATTRIBUTE_NAMES:
                _raise_forbidden_static("call", func.attr, node.lineno)
            if func.attr in _FORBIDDEN_IMPORTED_NAMES:
                _raise_forbidden_static("call", func.attr, node.lineno)


def validate_script_statically() -> None:
    if TRAFFIC_SEED != 0:
        raise RuntimeError(f"TRAFFIC_SEED must be 0, got {TRAFFIC_SEED}.")
    if VOT_SEED != 1:
        raise RuntimeError(f"VOT_SEED must be 1, got {VOT_SEED}.")
    if EVALUATION_END_TIMESTEP != 299:
        raise RuntimeError(
            f"EVALUATION_END_TIMESTEP must be 299, got {EVALUATION_END_TIMESTEP}."
        )
    if INTERNAL_TSIZE != 330:
        raise RuntimeError(f"INTERNAL_TSIZE must be 330, got {INTERNAL_TSIZE}.")
    if BASELINE_HORIZON_STEPS != 30:
        raise RuntimeError(
            f"BASELINE_HORIZON_STEPS must be 30, got {BASELINE_HORIZON_STEPS}."
        )
    if MAX_CANDIDATE_VISIT_COUNT != 10:
        raise RuntimeError(
            "MAX_CANDIDATE_VISIT_COUNT must be 10, "
            f"got {MAX_CANDIDATE_VISIT_COUNT}."
        )
    if len(VEHICLE_SPECS) != 12:
        raise RuntimeError(f"Expected 12 vehicles, got {len(VEHICLE_SPECS)}.")
    expected_names = (
        "veh_n1",
        "veh_e1",
        "veh_s1",
        "veh_w1",
        "veh_n2",
        "veh_e2",
        "veh_s2",
        "veh_w2",
        "veh_n3",
        "veh_e3",
        "veh_s3",
        "veh_w3",
    )
    actual_names = []
    for spec in VEHICLE_SPECS:
        actual_names.append(spec.vehicle_name)
        if spec.participating is not True:
            raise RuntimeError(f"{spec.vehicle_name} must participate.")
    if tuple(actual_names) != expected_names:
        raise RuntimeError(
            f"Vehicle name order is {actual_names}, expected {expected_names}."
        )

    source_text = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(SCRIPT_PATH))
    _assert_no_forbidden_imports(tree)
    _assert_no_forbidden_calls(tree)
    functions = _function_defs(tree)
    run_function_names = (
        "run_without_route_choice_diagnostic",
        "run_with_route_choice_diagnostic",
    )
    for function_name in run_function_names:
        if function_name not in functions:
            raise RuntimeError(f"Static validation: missing {function_name}.")

    exec_owners = []
    for function_name, function_def in functions.items():
        calls = _calls_in_function(function_def)
        exec_count = _count_name(calls, "exec_simulation")
        if exec_count == 0:
            continue
        exec_owners.append((function_name, exec_count))
    if exec_owners != [("_execute_audited_simulation", 1)]:
        raise RuntimeError(
            "Static validation: exec_simulation must be called once, "
            "only inside _execute_audited_simulation. "
            f"Found {exec_owners}."
        )

    execute_calls = _calls_in_function(functions["_execute_audited_simulation"])
    _require_before(
        execute_calls,
        "install_tvt_mp_full_run_audit",
        "exec_simulation",
        "_execute_audited_simulation",
    )
    collect_calls = _calls_in_function(functions["_collect_formal_snapshot"])
    _require_before(
        collect_calls,
        "build_tvt_mp_research_output",
        "finalize_tvt_mp_full_run_audit",
        "_collect_formal_snapshot",
    )

    with_function = functions["run_with_route_choice_diagnostic"]
    with_calls = _calls_in_function(with_function)
    _require_before(
        with_calls,
        "install_route_choice_rng_diagnostic",
        "finalize_scenario",
        "run_with_route_choice_diagnostic",
    )
    if _finally_calls_restore(with_function) is not True:
        raise RuntimeError(
            "Static validation: run_with_route_choice_diagnostic must restore "
            "the diagnostic in try/finally."
        )

    print(
        "Static validation passed for the 12-vehicle TVT-MP layer-2 trial.",
        file=sys.stderr,
    )


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_script_statically()
        return 0
    run_layer2_invariance()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
