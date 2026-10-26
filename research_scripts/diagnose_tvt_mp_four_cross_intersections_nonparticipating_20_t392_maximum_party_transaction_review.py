"""
Review the T=392 northwest maximum-party established trade.

Reads the saved selected candidate, economic records, and research output.
Does not rebuild the candidate or infer inlinks from vehicle names.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial as trial
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateTrafficObservationRecord,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpBuyerEconomicRecord,
    OrderControlTvtMpSellerEconomicRecord,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_research_output import build_tvt_mp_research_output
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_TIMESTEP = 392
TARGET_NODE_NAME = "northwest_intersection"
EXPECTED_EVALUATION_INDEX = 5
EXPECTED_WORLD_T_AFTER_SIM = 900
FLOAT_REL_TOL = 1e-12
FLOAT_ABS_TOL = 1e-12
SCENARIO_NAME = trial.SCENARIO_NAME

EXPECTED_TOTAL_G = 4.688146262221871
EXPECTED_TOTAL_R = 3.316785077593115
EXPECTED_OFFICIAL_PAYMENT = 3.3167850775931145
EXPECTED_OFFICIAL_COMPENSATION = 3.316785077593115
EXPECTED_REFERENCE_PAYMENT = 3.3167850775931145
EXPECTED_REFERENCE_COMPENSATION = 3.316785077593115
EXPECTED_BUYER_REALIZED_GAIN = 1.3713611846287552
EXPECTED_SELLER_REALIZED_GAIN = 0.0

INLINK_NORTHEAST = "northeast_intersection_to_northwest_intersection"
INLINK_SOUTHWEST = "southwest_intersection_to_northwest_intersection"
INLINK_WEST_NORTH = "west_north_od_to_northwest_intersection"
INLINK_NORTH_WEST = "north_west_od_to_northwest_intersection"

EXPECTED_PARTIES = (
    {
        "vehicle_name": "veh_en_sw_base_026",
        "visit_id": 2,
        "role": "seller",
        "baseline_local_rank": 1,
        "post_trade_local_rank": 4,
        "baseline_arrival_timestep": 398,
        "baseline_passage_timestep": 412,
        "candidate_passage_timestep": 420,
        "assigned_node_continuous_rank": 182,
        "formal_inlink_name": INLINK_NORTHEAST,
    },
    {
        "vehicle_name": "veh_sw_nw_base_039",
        "visit_id": 2,
        "role": "seller",
        "baseline_local_rank": 2,
        "post_trade_local_rank": 5,
        "baseline_arrival_timestep": 400,
        "baseline_passage_timestep": 402,
        "candidate_passage_timestep": 402,
        "assigned_node_continuous_rank": 183,
        "formal_inlink_name": INLINK_SOUTHWEST,
    },
    {
        "vehicle_name": "veh_sw_nw_base_040",
        "visit_id": 2,
        "role": "seller",
        "baseline_local_rank": 3,
        "post_trade_local_rank": 6,
        "baseline_arrival_timestep": 402,
        "baseline_passage_timestep": 406,
        "candidate_passage_timestep": 410,
        "assigned_node_continuous_rank": 184,
        "formal_inlink_name": INLINK_SOUTHWEST,
    },
    {
        "vehicle_name": "veh_wn_en_base_025",
        "visit_id": 1,
        "role": "buyer",
        "baseline_local_rank": 4,
        "post_trade_local_rank": 1,
        "baseline_arrival_timestep": 404,
        "baseline_passage_timestep": 410,
        "candidate_passage_timestep": 406,
        "assigned_node_continuous_rank": 179,
        "formal_inlink_name": INLINK_WEST_NORTH,
    },
    {
        "vehicle_name": "veh_nw_sw_base_048",
        "visit_id": 1,
        "role": "buyer",
        "baseline_local_rank": 5,
        "post_trade_local_rank": 2,
        "baseline_arrival_timestep": 408,
        "baseline_passage_timestep": 416,
        "candidate_passage_timestep": 412,
        "assigned_node_continuous_rank": 180,
        "formal_inlink_name": INLINK_NORTH_WEST,
    },
    {
        "vehicle_name": "veh_wn_se_base_025",
        "visit_id": 1,
        "role": "buyer",
        "baseline_local_rank": 6,
        "post_trade_local_rank": 3,
        "baseline_arrival_timestep": 410,
        "baseline_passage_timestep": 420,
        "candidate_passage_timestep": 416,
        "assigned_node_continuous_rank": 181,
        "formal_inlink_name": INLINK_WEST_NORTH,
    },
)

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t392_maximum_party_transaction_review"
    )
)
SIDE_BY_SIDE_CSV = "t392_maximum_party_side_by_side.csv"
CANDIDATE_ORDER_CSV = "t392_maximum_party_candidate_order.csv"
TRANSACTION_CSV = "t392_maximum_party_transaction_summary.csv"
SUMMARY_NAME = "t392_maximum_party_review.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    SIDE_BY_SIDE_CSV,
    CANDIDATE_ORDER_CSV,
    TRANSACTION_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)

PARTY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "selected_candidate_evaluation_index",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "role",
    "participates_in_order_exchange",
    "is_right_of_entry_holder",
    "formal_inlink_name",
    "predicted_route_next_link_name",
    "formal_route_next_link_name",
    "actual_route_next_link_name",
    "baseline_arrival_timestep",
    "actual_first_arrival_timestep",
    "actual_minus_baseline_arrival_timesteps",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "baseline_local_rank",
    "post_trade_local_rank",
    "binding_rank",
    "binding_partition",
    "assigned_node_continuous_rank",
    "actual_node_passage_rank",
    "actual_rank_change",
    "true_vot_per_second",
    "declared_vot_per_second",
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "individual_economic_condition_status",
    "passes_positive_buyer_value_condition",
    "official_payment",
    "official_compensation",
    "reference_payment",
    "reference_compensation",
    "realized_time_value",
    "realized_delay_loss",
    "realized_gain",
    "satisfaction_status",
    "satisfaction_reason",
)

TRANSACTION_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "selected_candidate_evaluation_index",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "total_G",
    "total_R",
    "surplus",
    "total_official_payment",
    "total_official_compensation",
    "payment_balance_difference",
    "payment_balance_satisfied",
    "total_reference_payment",
    "total_reference_compensation",
    "buyer_realized_gain_total",
    "seller_realized_gain_total",
    "buyer_satisfied_count",
    "seller_satisfied_count",
    "buyer_unsatisfied_count",
    "seller_unsatisfied_count",
    "actual_observed_party_count",
    "rank_difference_total",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.original_arrival = None
        self.captured = False
        self.parties: list[dict] = []
        self.transaction: dict | None = None
        self.arrivals: dict[tuple[str, int], int] = {}
        self.deltat = None


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _expected_by_key() -> dict:
    mapping = {}
    for party in EXPECTED_PARTIES:
        mapping[(party["vehicle_name"], party["visit_id"])] = party
    return mapping


def _close(left, right) -> bool:
    return math.isclose(left, right, rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


def _require_close(left, right, label: str) -> None:
    if type(left) is bool or type(right) is bool:
        raise RuntimeError(f"{label} is bool.")
    if _close(float(left), float(right)) is not True:
        raise RuntimeError(f"{label}: {left!r} != {right!r}.")


def _formal_arrival_timestep(arrival_time, deltat) -> int:
    formal_timestep = int(round(arrival_time / deltat))
    if type(formal_timestep) is not int or type(formal_timestep) is bool or formal_timestep < 0:
        raise RuntimeError(f"Formal arrival timestep is {formal_timestep!r}.")
    return formal_timestep


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _one_node(results, node_name: str, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"T={TARGET_TIMESTEP} {node_name}: {label} count is {count}.")
    return matched


def _saved_columns(atomic) -> dict:
    validation_set = atomic.final_consistency_validation_set_result
    final_rank_set = validation_set.final_rank_set_result
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection_set = payment_set.candidate_selection_set_result
    economic_set = selection_set.economic_evaluation_set_result
    local_set = economic_set.local_virtual_calculation_set_result
    fifo_set = local_set.fifo_inspection_set_result
    trade_rank_set = fifo_set.general_trade_rank_set_result
    concrete_set = trade_rank_set.concrete_buyer_candidate_set_result
    inlink_order_set = concrete_set.inlink_candidate_physical_order_result
    candidate_visit_set = inlink_order_set.candidate_visit_set_result
    right_of_entry_set = candidate_visit_set.right_of_entry_selection_result
    leading_set = right_of_entry_set.leading_confirmation_result
    arrived_set = leading_set.arrived_confirmation_result
    fork_result = arrived_set.alignment_fork_result.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError("Saved fork_result type is wrong.")
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError("Saved collector type is wrong.")
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "collector": collector,
    }


def _evaluation_index(economic_results, selected_economic) -> int:
    found = None
    index = 0
    for candidate_economic in economic_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if found is not None:
                raise RuntimeError("Selected economic result appears more than once.")
            found = index
    if found is None:
        raise RuntimeError("Selected economic result is missing from the node list.")
    return found


def _role_name(role) -> str:
    if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return "buyer"
    if role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return "seller"
    if role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return "nonparticipating"
    raise RuntimeError(f"Unsupported trade role {role!r}.")


def _baseline_order(candidate_visits) -> list:
    ordered = []
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError("candidate_visits entry type is wrong.")
        ordered.append(_plain_visit_key(candidate_visit.visit_key))
    return ordered


def _trade_result_for_buyers(trade_rank_node, buyers_sorted):
    if not isinstance(trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError("Trade rank node type is wrong.")
    found = None
    for trade_result in trade_rank_node.candidate_trade_rank_results:
        candidate_buyers = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted)
        if candidate_buyers != buyers_sorted:
            continue
        if found is not None:
            raise RuntimeError("Two trade results share the selected buyers.")
        found = trade_result
    if found is None or not isinstance(found, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError("No trade result matches the selected buyers.")
    return found


def _records_by_key(records, label: str) -> dict:
    mapping = {}
    for record in records:
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(f"{label} repeats {_visit_text(visit_key)}.")
        mapping[visit_key] = record
    return mapping


def _capture_t392(world, result) -> None:
    if GATE.captured is True:
        raise RuntimeError("T=392 northwest transaction was saved twice.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"Driver result type is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError("T=392 atomic_apply_set_result is None.")
    columns = _saved_columns(atomic)
    selection_node = _one_node(columns["selection_nodes"], TARGET_NODE_NAME, "selection")
    selected_economic = selection_node.selected_candidate_economic_result
    if selected_economic is None:
        raise RuntimeError("T=392 northwest has no selected candidate.")
    economic_node = _one_node(columns["economic_nodes"], TARGET_NODE_NAME, "economic")
    evaluation_index = _evaluation_index(
        economic_node.candidate_economic_evaluation_results,
        selected_economic,
    )
    if evaluation_index != EXPECTED_EVALUATION_INDEX:
        raise RuntimeError(f"Selected evaluation index is {evaluation_index}, not 5.")
    local_result = selected_economic.candidate_local_virtual_calculation_result
    buyers_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    trade_result = _trade_result_for_buyers(
        _one_node(columns["trade_rank_nodes"], TARGET_NODE_NAME, "trade rank"),
        buyers_sorted,
    )
    candidate_visit_node = _one_node(
        columns["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate visits"
    )
    baseline_order = _baseline_order(candidate_visit_node.candidate_visits)
    binding_by_key = {}
    for binding_visit in local_result.binding_rank_sequence.visits_in_binding_order:
        binding_by_key[_plain_visit_key(binding_visit.visit_key)] = binding_visit
    traffic_by_key = _records_by_key(local_result.traffic_observation_records, "traffic")
    buyer_records = _records_by_key(selected_economic.buyer_economic_records, "buyer economic")
    seller_records = _records_by_key(selected_economic.seller_economic_records, "seller economic")
    right_node = _one_node(columns["right_of_entry_nodes"], TARGET_NODE_NAME, "right of entry")
    right_of_entry = None
    if right_node.right_of_entry_visit_key is not None:
        right_of_entry = _plain_visit_key(right_node.right_of_entry_visit_key)
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError("Northwest rank state is missing after T=392.")
    identity = f"T={TARGET_TIMESTEP}|{TARGET_NODE_NAME}|index={evaluation_index}"
    expected = _expected_by_key()
    parties = []
    scope = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.trade_scope)
    for visit_key in scope:
        if visit_key not in expected:
            raise RuntimeError(f"Unexpected party {_visit_text(visit_key)}.")
        binding_visit = binding_by_key.get(visit_key)
        traffic = traffic_by_key.get(visit_key)
        if binding_visit is None or not isinstance(traffic, OrderControlTvtMpCandidateTrafficObservationRecord):
            raise RuntimeError(f"{_visit_text(visit_key)} is missing binding or traffic.")
        role_name = _role_name(binding_visit.trade_role)
        if traffic.inlink_name != binding_visit.inlink_name:
            raise RuntimeError(f"{_visit_text(visit_key)} inlink sources differ.")
        snapshot = columns["collector"].get_baseline_visit_snapshot(visit_key[0], visit_key[1])
        if snapshot is None:
            raise RuntimeError(f"{_visit_text(visit_key)} baseline snapshot is missing.")
        if snapshot.get("baseline_arrival_timestep") != binding_visit.baseline_arrival_timestep:
            raise RuntimeError(f"{_visit_text(visit_key)} baseline arrival sources differ.")
        vehicle = world.VEHICLES.get(visit_key[0])
        if vehicle is None:
            raise RuntimeError(f"Vehicle {visit_key[0]!r} is missing.")
        participates = vehicle.participates_in_order_exchange
        if role_name == "buyer":
            buyer_record = buyer_records.get(visit_key)
            if not isinstance(buyer_record, OrderControlTvtMpBuyerEconomicRecord):
                raise RuntimeError(f"{_visit_text(visit_key)} buyer economic record is missing.")
            if visit_key in seller_records:
                raise RuntimeError(f"{_visit_text(visit_key)} also has a seller record.")
            gross = buyer_record.gross_time_value_G_b
            required = None
            passes = buyer_record.passes_positive_buyer_value_condition
            declared = buyer_record.declared_vot_per_second
            if passes is True:
                status = "passes_positive_buyer_value_condition"
            elif passes is False:
                status = "fails_positive_buyer_value_condition"
            else:
                raise RuntimeError("passes_positive_buyer_value_condition is not bool.")
            expected_g = (
                (buyer_record.baseline_passage_timestep - buyer_record.candidate_passage_timestep)
                * world.DELTAT
                * declared
            )
            _require_close(gross, expected_g, f"{_visit_text(visit_key)} G_b")
        else:
            seller_record = seller_records.get(visit_key)
            if not isinstance(seller_record, OrderControlTvtMpSellerEconomicRecord):
                raise RuntimeError(f"{_visit_text(visit_key)} seller economic record is missing.")
            if visit_key in buyer_records:
                raise RuntimeError(f"{_visit_text(visit_key)} also has a buyer record.")
            gross = None
            required = seller_record.required_compensation_R_s
            passes = None
            declared = seller_record.declared_vot_per_second
            status = None
            expected_r = (
                (seller_record.candidate_passage_timestep - seller_record.baseline_passage_timestep)
                * world.DELTAT
                * declared
            )
            _require_close(required, expected_r, f"{_visit_text(visit_key)} R_s")
        baseline_passage = snapshot.get("baseline_passage_timestep")
        candidate_passage = traffic.candidate_passage_timestep
        post_trade_rank = trade_result.assigned_rank(visit_key)
        assigned_rank = rank_state.assigned_rank(visit_key)
        parties.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": TARGET_TIMESTEP,
                "node_name": TARGET_NODE_NAME,
                "candidate_identity": identity,
                "selected_candidate_evaluation_index": evaluation_index,
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "visit_key_tuple": visit_key,
                "role": role_name,
                "participates_in_order_exchange": participates,
                "is_right_of_entry_holder": visit_key == right_of_entry,
                "formal_inlink_name": binding_visit.inlink_name,
                "predicted_route_next_link_name": binding_visit.route_next_link_name,
                "formal_route_next_link_name": rank_state.formal_route_next_link_name(visit_key),
                "baseline_arrival_timestep": binding_visit.baseline_arrival_timestep,
                "baseline_passage_timestep": baseline_passage,
                "candidate_passage_timestep": candidate_passage,
                "baseline_local_rank": baseline_order.index(visit_key) + 1,
                "post_trade_local_rank": post_trade_rank,
                "binding_rank": binding_visit.binding_rank,
                "binding_partition": binding_visit.binding_partition.value,
                "assigned_node_continuous_rank": assigned_rank,
                "true_vot_per_second": traffic.true_vot_per_second,
                "declared_vot_per_second": declared,
                "gross_time_value_G_b": gross,
                "required_compensation_R_s": required,
                "individual_economic_condition_status": status,
                "passes_positive_buyer_value_condition": passes,
            }
        )
    if len(buyer_records) != 3 or len(seller_records) != 3:
        raise RuntimeError("Buyer or seller economic record count is not 3.")
    GATE.captured = True
    GATE.deltat = world.DELTAT
    GATE.parties = parties
    GATE.transaction = {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": TARGET_TIMESTEP,
        "node_name": TARGET_NODE_NAME,
        "candidate_identity": identity,
        "selected_candidate_evaluation_index": evaluation_index,
        "buyers_sorted": buyers_sorted,
        "total_G": selected_economic.total_buyer_value_G,
        "total_R": selected_economic.total_required_compensation_R,
        "surplus": selected_economic.surplus,
    }


def wrapped_driver(world):
    result = GATE.original_driver(world)
    if world is not GATE.real_world:
        return result
    if world.T != TARGET_TIMESTEP:
        return result
    _capture_t392(world, result)
    return result


def wrapped_arrival(vehicle, node):
    result = GATE.original_arrival(vehicle, node)
    if vehicle.W is not GATE.real_world:
        return result
    if getattr(vehicle.W, "_order_control_baseline_collector", None) is not None:
        return result
    if node is None or node.name != TARGET_NODE_NAME:
        return result
    current_visit = getattr(vehicle, "order_control_current_visit", None)
    if not isinstance(current_visit, dict):
        return result
    if current_visit.get("node") is not node:
        return result
    visit_id = current_visit.get("visit_id")
    if type(visit_id) is not int or type(visit_id) is bool:
        return result
    key = (vehicle.name, visit_id)
    if key not in _expected_by_key():
        return result
    arrival_time = current_visit.get("arrival_time")
    if arrival_time is None:
        return result
    formal_timestep = _formal_arrival_timestep(arrival_time, vehicle.W.DELTAT)
    if key not in GATE.arrivals:
        if formal_timestep != vehicle.W.T:
            raise RuntimeError(
                f"First arrival {_visit_text(key)} formal {formal_timestep} != World.T {vehicle.W.T}."
            )
        GATE.arrivals[key] = formal_timestep
    else:
        from_production = _formal_arrival_timestep(arrival_time, vehicle.W.DELTAT)
        if GATE.arrivals[key] != from_production:
            raise RuntimeError(f"Re-registration changed arrival for {_visit_text(key)}.")
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Diagnostic hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_driver = driver_module.run_tvt_mp_driver
    GATE.original_arrival = uxsim_module.Vehicle.record_order_control_node_arrival
    driver_module.run_tvt_mp_driver = wrapped_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = wrapped_arrival
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_driver
    uxsim_module.Vehicle.record_order_control_node_arrival = GATE.original_arrival
    GATE.original_driver = None
    GATE.original_arrival = None
    GATE.real_world = None
    GATE.installed = False


def _join_research(bundle) -> dict:
    buyers = GATE.transaction["buyers_sorted"]
    matched = []
    for row in bundle.transactions:
        if row.tvt_decision_timestep != TARGET_TIMESTEP or row.node_name != TARGET_NODE_NAME:
            continue
        if tuple(_plain_visit_key(visit_key) for visit_key in row.buyers_sorted) != buyers:
            continue
        matched.append(row)
    if len(matched) != 1:
        raise RuntimeError(f"T=392 research transactions matched {len(matched)}.")
    transaction_row = matched[0]
    visit_rows = {}
    for row in bundle.visits:
        if row.tvt_decision_timestep != TARGET_TIMESTEP or row.node_name != TARGET_NODE_NAME:
            continue
        if tuple(_plain_visit_key(visit_key) for visit_key in row.buyers_sorted) != buyers:
            continue
        visit_rows[(row.vehicle_name, row.visit_id)] = row
    for party in GATE.parties:
        visit = visit_rows.get(party["visit_key_tuple"])
        if visit is None:
            raise RuntimeError(f"Research visit missing for {party['visit_key']}.")
        arrival = GATE.arrivals.get(party["visit_key_tuple"])
        party["actual_first_arrival_timestep"] = arrival
        if arrival is None:
            party["actual_minus_baseline_arrival_timesteps"] = None
        else:
            party["actual_minus_baseline_arrival_timesteps"] = arrival - party["baseline_arrival_timestep"]
        party["actual_passage_timestep"] = visit.actual_passage_timestep
        party["actual_route_next_link_name"] = visit.actual_route_next_link_name
        party["actual_node_passage_rank"] = visit.actual_node_passage_rank
        party["actual_rank_change"] = visit.actual_rank_change
        party["official_payment"] = visit.official_payment
        party["official_compensation"] = visit.official_compensation
        party["reference_payment"] = visit.reference_payment
        party["reference_compensation"] = visit.reference_compensation
        party["realized_time_value"] = visit.realized_time_value
        party["realized_delay_loss"] = visit.realized_delay_loss
        party["realized_gain"] = visit.realized_gain
        party["satisfaction_status"] = visit.satisfaction_status
        party["satisfaction_reason"] = visit.satisfaction_reason
        if party["baseline_passage_timestep"] is None or party["candidate_passage_timestep"] is None:
            raise RuntimeError(f"{party['visit_key']} passage is missing.")
        party["baseline_minus_candidate_passage_timesteps"] = (
            party["baseline_passage_timestep"] - party["candidate_passage_timestep"]
        )
        party["baseline_minus_actual_passage_timesteps"] = (
            None
            if visit.actual_passage_timestep is None
            else party["baseline_passage_timestep"] - visit.actual_passage_timestep
        )
        party["candidate_minus_actual_passage_timesteps"] = (
            None
            if visit.actual_passage_timestep is None
            else party["candidate_passage_timestep"] - visit.actual_passage_timestep
        )
        if visit.formal_route_next_link_name != party["formal_route_next_link_name"]:
            raise RuntimeError(f"{party['visit_key']} formal route differs from research output.")
        if visit.predicted_route_next_link_name != party["predicted_route_next_link_name"]:
            raise RuntimeError(f"{party['visit_key']} predicted route differs from research output.")
        if visit.assigned_rank != party["assigned_node_continuous_rank"]:
            raise RuntimeError(f"{party['visit_key']} assigned rank differs from research output.")
        _require_close(visit.true_vot_per_second, party["true_vot_per_second"], f"{party['visit_key']} true VOT")
    return transaction_row


def _finish_transaction(transaction_row) -> dict:
    buyer_g = 0.0
    seller_r = 0.0
    payment = 0.0
    compensation = 0.0
    reference_payment = 0.0
    reference_compensation = 0.0
    buyer_gain = 0.0
    seller_gain = 0.0
    buyer_satisfied = 0
    seller_satisfied = 0
    buyer_unsatisfied = 0
    seller_unsatisfied = 0
    observed = 0
    rank_difference = 0
    for party in GATE.parties:
        if party["role"] == "buyer":
            buyer_g = buyer_g + party["gross_time_value_G_b"]
            payment = payment + party["official_payment"]
            reference_payment = reference_payment + party["reference_payment"]
            buyer_gain = buyer_gain + party["realized_gain"]
            if party["satisfaction_status"] == "satisfied":
                buyer_satisfied = buyer_satisfied + 1
            else:
                buyer_unsatisfied = buyer_unsatisfied + 1
            if party["official_compensation"] is not None or party["required_compensation_R_s"] is not None:
                raise RuntimeError(f"{party['visit_key']} buyer compensation field is present.")
        else:
            seller_r = seller_r + party["required_compensation_R_s"]
            compensation = compensation + party["official_compensation"]
            reference_compensation = reference_compensation + party["reference_compensation"]
            seller_gain = seller_gain + party["realized_gain"]
            if party["satisfaction_status"] == "satisfied":
                seller_satisfied = seller_satisfied + 1
            else:
                seller_unsatisfied = seller_unsatisfied + 1
            if party["official_payment"] is not None or party["gross_time_value_G_b"] is not None:
                raise RuntimeError(f"{party['visit_key']} seller payment field is present.")
        if party["actual_passage_timestep"] is not None:
            observed = observed + 1
        rank_difference = rank_difference + (
            party["assigned_node_continuous_rank"] - party["actual_node_passage_rank"]
        )
    surplus = GATE.transaction["surplus"]
    _require_close(buyer_g, GATE.transaction["total_G"], "sum G_b")
    _require_close(seller_r, GATE.transaction["total_R"], "sum R_s")
    _require_close(surplus, GATE.transaction["total_G"] - GATE.transaction["total_R"], "surplus")
    _require_close(payment, transaction_row.buyer_official_payment_total, "payment sum")
    _require_close(compensation, transaction_row.seller_official_compensation_total, "compensation sum")
    difference = payment - compensation
    balanced = _close(payment, compensation)
    row = {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": TARGET_TIMESTEP,
        "node_name": TARGET_NODE_NAME,
        "candidate_identity": GATE.transaction["candidate_identity"],
        "selected_candidate_evaluation_index": EXPECTED_EVALUATION_INDEX,
        "buyer_count": 3,
        "seller_count": 3,
        "nonparticipating_count": 0,
        "trade_scope_count": 6,
        "total_G": GATE.transaction["total_G"],
        "total_R": GATE.transaction["total_R"],
        "surplus": surplus,
        "total_official_payment": payment,
        "total_official_compensation": compensation,
        "payment_balance_difference": difference,
        "payment_balance_satisfied": balanced,
        "total_reference_payment": reference_payment,
        "total_reference_compensation": reference_compensation,
        "buyer_realized_gain_total": buyer_gain,
        "seller_realized_gain_total": seller_gain,
        "buyer_satisfied_count": buyer_satisfied,
        "seller_satisfied_count": seller_satisfied,
        "buyer_unsatisfied_count": buyer_unsatisfied,
        "seller_unsatisfied_count": seller_unsatisfied,
        "actual_observed_party_count": observed,
        "rank_difference_total": rank_difference,
    }
    return row


def _validate_expected(world, transaction_row, summary_row) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(f"World.T is {world.T}.")
    if GATE.captured is not True or len(GATE.parties) != 6:
        raise RuntimeError("T=392 six-party capture is missing.")
    expected = _expected_by_key()
    if set(party["visit_key_tuple"] for party in GATE.parties) != set(expected):
        raise RuntimeError("Party VisitKey set differs.")
    for party in GATE.parties:
        known = expected[party["visit_key_tuple"]]
        for field_name in (
            "role",
            "formal_inlink_name",
            "baseline_arrival_timestep",
            "baseline_passage_timestep",
            "candidate_passage_timestep",
            "baseline_local_rank",
            "post_trade_local_rank",
            "assigned_node_continuous_rank",
        ):
            if party[field_name] != known[field_name]:
                raise RuntimeError(f"{party['visit_key']} {field_name} is {party[field_name]!r}.")
        if party["actual_first_arrival_timestep"] is None or party["actual_passage_timestep"] is None:
            raise RuntimeError(f"{party['visit_key']} arrival or actual passage is missing.")
        if party["actual_node_passage_rank"] is None:
            raise RuntimeError(f"{party['visit_key']} actual passage rank is missing.")
        if party["role"] in ("buyer", "seller") and party["participates_in_order_exchange"] is not True:
            raise RuntimeError(f"{party['visit_key']} participation flag is wrong.")
    _require_close(summary_row["total_G"], EXPECTED_TOTAL_G, "total_G")
    _require_close(summary_row["total_R"], EXPECTED_TOTAL_R, "total_R")
    _require_close(summary_row["total_official_payment"], EXPECTED_OFFICIAL_PAYMENT, "official payment")
    _require_close(
        summary_row["total_official_compensation"],
        EXPECTED_OFFICIAL_COMPENSATION,
        "official compensation",
    )
    _require_close(summary_row["total_reference_payment"], EXPECTED_REFERENCE_PAYMENT, "reference payment")
    _require_close(
        summary_row["total_reference_compensation"],
        EXPECTED_REFERENCE_COMPENSATION,
        "reference compensation",
    )
    _require_close(summary_row["buyer_realized_gain_total"], EXPECTED_BUYER_REALIZED_GAIN, "buyer gain")
    _require_close(summary_row["seller_realized_gain_total"], EXPECTED_SELLER_REALIZED_GAIN, "seller gain")
    if summary_row["payment_balance_satisfied"] is not True:
        raise RuntimeError("Payment balance is not satisfied.")
    if summary_row["buyer_satisfied_count"] != 3 or summary_row["seller_satisfied_count"] != 3:
        raise RuntimeError("Satisfaction counts differ.")
    if summary_row["buyer_unsatisfied_count"] != 0 or summary_row["seller_unsatisfied_count"] != 0:
        raise RuntimeError("Unsatisfied counts differ.")
    if summary_row["actual_observed_party_count"] != 6 or summary_row["rank_difference_total"] != 0:
        raise RuntimeError("Observed count or rank difference total differs.")
    if transaction_row.rank_difference_total != 0:
        raise RuntimeError("Research rank_difference_total is not 0.")
    _compare_trial_csv(summary_row)


def _parse_number(text):
    if text is None or text == "":
        return None
    if "." in text:
        return float(text)
    return int(text)


def _read_csv(path: Path) -> list[dict]:
    if path.is_file() is not True:
        raise RuntimeError(f"Missing trial CSV {path}.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _compare_trial_csv(summary_row) -> None:
    transactions = _read_csv(trial.TRIAL_OUTPUT_DIR / "tvt_mp_transactions.csv")
    visits = _read_csv(trial.TRIAL_OUTPUT_DIR / "tvt_mp_visits.csv")
    buyers_text = "|".join(_visit_text(visit_key) for visit_key in GATE.transaction["buyers_sorted"])
    matched = [
        row
        for row in transactions
        if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
        and row["node_name"] == TARGET_NODE_NAME
        and row["buyers_sorted"] == buyers_text
    ]
    if len(matched) != 1:
        raise RuntimeError("Trial transaction CSV does not contain one T=392 northwest row.")
    csv_transaction = matched[0]
    _require_close(
        _parse_number(csv_transaction["buyer_official_payment_total"]),
        summary_row["total_official_payment"],
        "CSV payment",
    )
    _require_close(
        _parse_number(csv_transaction["seller_official_compensation_total"]),
        summary_row["total_official_compensation"],
        "CSV compensation",
    )
    for party in GATE.parties:
        visit_matches = [
            row
            for row in visits
            if row["tvt_decision_timestep"] == str(TARGET_TIMESTEP)
            and row["node_name"] == TARGET_NODE_NAME
            and row["buyers_sorted"] == buyers_text
            and row["vehicle_name"] == party["vehicle_name"]
            and row["visit_id"] == str(party["visit_id"])
            and row["role"] == party["role"]
        ]
        if len(visit_matches) != 1:
            raise RuntimeError(f"Trial visit CSV match count for {party['visit_key']} is {len(visit_matches)}.")
        visit = visit_matches[0]
        if _parse_number(visit["actual_passage_timestep"]) != party["actual_passage_timestep"]:
            raise RuntimeError(f"CSV actual passage differs for {party['visit_key']}.")
        if _parse_number(visit["assigned_rank"]) != party["assigned_node_continuous_rank"]:
            raise RuntimeError(f"CSV assigned rank differs for {party['visit_key']}.")
        if visit["satisfaction_status"] != party["satisfaction_status"]:
            raise RuntimeError(f"CSV satisfaction differs for {party['visit_key']}.")


def _build_summary(summary_row) -> str:
    baseline_rows = sorted(GATE.parties, key=lambda row: row["baseline_local_rank"])
    candidate_rows = sorted(GATE.parties, key=lambda row: row["post_trade_local_rank"])
    zero_vot_sellers = [
        row["visit_key"]
        for row in GATE.parties
        if row["role"] == "seller"
        and row["declared_vot_per_second"] == 0
        and row["required_compensation_R_s"] == 0
    ]
    lines = [
        "T=392 northwest_intersection の最大6 party取引。",
        "buyer 3、seller 3、nonparticipating 0。selected evaluation index=5。",
        "Baseline順は seller 3人のあと buyer 3人。Candidate順は buyer 3人が先で seller 3人が後。",
        "同一inlink複数seller: southwest_intersection_to_northwest_intersection。",
        "同一inlink複数buyer: west_north_od_to_northwest_intersection。",
        "",
        "Baseline順の交通・順位:",
    ]
    for row in baseline_rows:
        lines.append(
            f"  {row['visit_key']} {row['role']} {row['formal_inlink_name']} "
            f"A {row['baseline_arrival_timestep']}/{row['actual_first_arrival_timestep']} "
            f"P {row['baseline_passage_timestep']}/{row['candidate_passage_timestep']}/{row['actual_passage_timestep']} "
            f"rank {row['baseline_local_rank']}/{row['post_trade_local_rank']}/"
            f"C{row['assigned_node_continuous_rank']}/A{row['actual_node_passage_rank']}"
        )
    lines.append("")
    lines.append("Candidate順の経済:")
    for row in candidate_rows:
        lines.append(
            f"  {row['visit_key']} VOT {row['declared_vot_per_second']} "
            f"G {row['gross_time_value_G_b']} R {row['required_compensation_R_s']} "
            f"pay {row['official_payment']} comp {row['official_compensation']} "
            f"gain {row['realized_gain']} {row['satisfaction_status']}"
        )
    if len(zero_vot_sellers) > 0:
        lines.append(
            "申告VOTが0のsellerは必要補償R_sも0: " + ", ".join(zero_vot_sellers)
        )
    lines.extend(
        [
            "",
            (
                f"total_G {summary_row['total_G']} total_R {summary_row['total_R']} "
                f"surplus {summary_row['surplus']}"
            ),
            (
                f"payment {summary_row['total_official_payment']} "
                f"compensation {summary_row['total_official_compensation']} "
                f"difference {summary_row['payment_balance_difference']}"
            ),
            "buyer satisfied 3 / unsatisfied 0。seller satisfied 3 / unsatisfied 0。",
            "保存済み正式値の範囲で矛盾は確認されなかった。",
            "これはproduction全体の完全な正当性証明ではない。",
        ]
    )
    return "\n".join(lines) + "\n"


def _prepare_world():
    world = trial.build_world()
    vot_values = trial._true_vot_sequence()
    vot_records = trial.build_vehicle_vot_records(trial.VEHICLE_SPECS, vot_values)
    trial.add_vehicles_to_world(world, trial.VEHICLE_SPECS, vot_records)
    trial.verify_world_participation(world, vot_records)
    world.finalize_scenario()
    return world


def main(argv=None) -> int:
    if argv is None:
        arguments = sys.argv[1:]
    else:
        arguments = list(argv)
    if len(arguments) > 1:
        raise SystemExit("Unexpected CLI arguments.")
    if len(arguments) == 1:
        if arguments[0] != "--static-validate-only":
            raise SystemExit(f"Unknown CLI option: {arguments[0]!r}.")
        validate_static_contract()
        return 0
    GATE.captured = False
    GATE.parties = []
    GATE.transaction = None
    GATE.arrivals = {}
    original_limit = sys.getrecursionlimit()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
            raise RuntimeError("Diagnostic output directory is the trial output directory.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        bundle = build_tvt_mp_research_output(world, SCENARIO_NAME)
        transaction_row = _join_research(bundle)
        summary_row = _finish_transaction(transaction_row)
        _validate_expected(world, transaction_row, summary_row)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        baseline_rows = sorted(GATE.parties, key=lambda row: row["baseline_local_rank"])
        candidate_rows = sorted(GATE.parties, key=lambda row: row["post_trade_local_rank"])
        _write_csv(OUTPUT_DIR / SIDE_BY_SIDE_CSV, PARTY_COLUMNS, baseline_rows)
        _write_csv(OUTPUT_DIR / CANDIDATE_ORDER_CSV, PARTY_COLUMNS, candidate_rows)
        _write_csv(OUTPUT_DIR / TRANSACTION_CSV, TRANSACTION_COLUMNS, [summary_row])
        (OUTPUT_DIR / SUMMARY_NAME).write_text(_build_summary(summary_row), encoding="utf-8")
        manifest = {
            "diagnostic_script": SCRIPT_PATH.name,
            "scenario_name": SCENARIO_NAME,
            "target_timestep": TARGET_TIMESTEP,
            "target_node_name": TARGET_NODE_NAME,
            "candidate_identity": GATE.transaction["candidate_identity"],
            "selected_candidate_evaluation_index": EXPECTED_EVALUATION_INDEX,
            "party_count": 6,
            "output_files": list(OUTPUT_FILE_NAMES),
            "validation_result": "passed",
            "mismatch_count": 0,
        }
        (OUTPUT_DIR / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        trial.reference.restore_real_world_spillback_observation()
        restore_hooks()
        sys.setrecursionlimit(original_limit)


def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_count(function_node, owner: str, attr: str) -> int:
    count = 0
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != attr:
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == owner:
            count = count + 1
    return count


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Output directory equals the trial directory.")
    if "t392_maximum_party_transaction_review" not in str(OUTPUT_DIR):
        raise RuntimeError("Output directory name is wrong.")
    for file_name in OUTPUT_FILE_NAMES:
        if file_name not in source:
            raise RuntimeError(f"Missing output name {file_name}.")
    for text in (
        "northwest_intersection",
        "gross_time_value_G_b",
        "required_compensation_R_s",
        "buyer_economic_records",
        "seller_economic_records",
        INLINK_SOUTHWEST,
        INLINK_WEST_NORTH,
    ):
        if text not in source:
            raise RuntimeError(f"Missing contract text {text}.")
    if TARGET_TIMESTEP != 392 or EXPECTED_EVALUATION_INDEX != 5:
        raise RuntimeError("Target timestep or evaluation index constant is wrong.")
    driver = _function_node(tree, "wrapped_driver")
    arrival = _function_node(tree, "wrapped_arrival")
    if driver is None or arrival is None:
        raise RuntimeError("Wrapper is missing.")
    if _call_count(driver, "GATE", "original_driver") != 1:
        raise RuntimeError("wrapped_driver must call original_driver once.")
    if _call_count(arrival, "GATE", "original_arrival") != 1:
        raise RuntimeError("wrapped_arrival must call original_arrival once.")
    install_node = _function_node(tree, "install_hooks")
    restore_node = _function_node(tree, "restore_hooks")
    if install_node is None or restore_node is None:
        raise RuntimeError("Hook install or restore is missing.")
    main_node = _function_node(tree, "main")
    validate_line = None
    mkdir_line = None
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_validate_expected":
                validate_line = node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "mkdir":
                mkdir_line = node.lineno
    if validate_line is None or mkdir_line is None or validate_line >= mkdir_line:
        raise RuntimeError("Runtime validation must run before mkdir.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation runs simulation, hooks, or mkdir.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
