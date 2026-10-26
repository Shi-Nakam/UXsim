"""
Read selected established trades on the four-cross nonparticipating 20 percent
trial and record each party's saved inlink_name.

Inlink names come only from the selected candidate's saved party records.
Vehicle names are not used to guess an inlink.
"""

from __future__ import annotations

import ast
import csv
import json
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
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateTrafficObservationRecord,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_research_output import build_tvt_mp_research_output


SCENARIO_NAME = trial.SCENARIO_NAME
TRIAL_OUTPUT_DIR = trial.TRIAL_OUTPUT_DIR
EXPECTED_WORLD_T_AFTER_SIM = 900
EXPECTED_TRANSACTIONS = 228
EXPECTED_PARTIES = 626
EXPECTED_BUYERS = 263
EXPECTED_SELLERS = 324
EXPECTED_NONPARTICIPATING_PARTIES = 39
EXPECTED_NONPARTICIPATING_TRANSACTIONS = 37
EXPECTED_MULTIPLE_BUYER_TRANSACTIONS = 32
EXPECTED_MULTIPLE_SELLER_TRANSACTIONS = 83
EXPECTED_MAXIMUM_PARTY_COUNT = 6
EXPECTED_MAXIMUM_PARTY_TRANSACTIONS = 1
EXPECTED_MAXIMUM_TRANSACTION = {
    "tvt_decision_timestep": 392,
    "node_name": "northwest_intersection",
    "buyer_count": 3,
    "seller_count": 3,
    "nonparticipating_count": 0,
    "trade_scope_count": 6,
    "buyers": {
        ("veh_nw_sw_base_048", 1),
        ("veh_wn_en_base_025", 1),
        ("veh_wn_se_base_025", 1),
    },
    "sellers": {
        ("veh_en_sw_base_026", 2),
        ("veh_sw_nw_base_039", 2),
        ("veh_sw_nw_base_040", 2),
    },
}

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "established_party_inlinks"
    )
)
TRANSACTION_CSV = "established_transactions_inlink_summary.csv"
PARTY_CSV = "established_transaction_parties_with_inlinks.csv"
MAXIMUM_CSV = "maximum_party_transactions.csv"
SAME_BUYER_CSV = "same_inlink_multiple_buyer_transactions.csv"
SAME_SELLER_CSV = "same_inlink_multiple_seller_transactions.csv"
NONPARTICIPATING_CSV = "nonparticipating_transactions.csv"
COEXIST_CSV = "same_inlink_participant_nonparticipating_transactions.csv"
SUMMARY_NAME = "established_party_inlinks_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    TRANSACTION_CSV,
    PARTY_CSV,
    MAXIMUM_CSV,
    SAME_BUYER_CSV,
    SAME_SELLER_CSV,
    NONPARTICIPATING_CSV,
    COEXIST_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)

TRANSACTION_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "selected_candidate_evaluation_index",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "buyer_inlinks",
    "seller_inlinks",
    "nonparticipating_inlinks",
    "same_inlink_multiple_buyer",
    "same_inlink_multiple_seller",
    "same_inlink_buyer_and_nonparticipating",
    "same_inlink_seller_and_nonparticipating",
    "same_inlink_participant_and_nonparticipating",
    "same_inlink_role_combinations",
    "maximum_party_count",
    "is_maximum_party_transaction",
)
PARTY_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "selected_candidate_evaluation_index",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "role",
    "participates_in_order_exchange",
    "inlink_name",
    "baseline_local_rank",
    "post_trade_local_rank",
    "binding_partition",
    "is_right_of_entry_holder",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.transactions: list[dict] = []


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is {vehicle_name!r}.")
    if type(visit_id) is not int or type(visit_id) is bool:
        raise RuntimeError(f"VisitKey visit id is {visit_id!r}.")
    return (vehicle_name, visit_id)


def _join_visits(visit_keys) -> str:
    return "|".join(_visit_text(visit_key) for visit_key in visit_keys)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _one_node(results, node_name: str, timestep: int, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"T={timestep} {node_name}: {label} count is {count}.")
    return matched


def _saved_columns(atomic):
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
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
    }


def _evaluation_index(economic_results, selected_economic, node_name: str, timestep: int) -> int:
    evaluation_index = None
    index = 0
    for candidate_economic in economic_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if evaluation_index is not None:
                raise RuntimeError(
                    f"T={timestep} {node_name}: selected economic result appears more than once."
                )
            evaluation_index = index
    if evaluation_index is None:
        raise RuntimeError(f"T={timestep} {node_name}: selected economic result is missing.")
    return evaluation_index


def _role_name(role) -> str:
    if role is OrderControlTvtMpLocalBindingTradeRole.BUYER:
        return "buyer"
    if role is OrderControlTvtMpLocalBindingTradeRole.SELLER:
        return "seller"
    if role is OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING:
        return "nonparticipating"
    raise RuntimeError(f"Unsupported trade role {role!r}.")


def _baseline_ranks(candidate_visits, node_name: str, timestep: int) -> dict:
    ranks = {}
    position = 0
    for candidate_visit in candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"T={timestep} {node_name}: candidate visit type is {type(candidate_visit).__name__}."
            )
        position = position + 1
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in ranks:
            raise RuntimeError(f"T={timestep} {node_name}: duplicate candidate visit {_visit_text(visit_key)}.")
        ranks[visit_key] = position
    return ranks


def _post_trade_ranks(trade_result, visit_keys, node_name: str, timestep: int) -> dict:
    if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
        raise RuntimeError(f"T={timestep} {node_name}: trade result type is {type(trade_result).__name__}.")
    ranks = {}
    for visit_key in visit_keys:
        rank_value = trade_result.assigned_rank(visit_key)
        if type(rank_value) is not int or type(rank_value) is bool:
            raise RuntimeError(f"T={timestep} {node_name}: post-trade rank is {rank_value!r}.")
        ranks[visit_key] = rank_value
    return ranks


def _matching_trade_result(trade_rank_node, buyers_sorted, node_name: str, timestep: int):
    if not isinstance(trade_rank_node, OrderControlTvtNodeMpGeneralTradeRankResult):
        raise RuntimeError(f"T={timestep} {node_name}: trade rank node type is wrong.")
    found = None
    for trade_result in trade_rank_node.candidate_trade_rank_results:
        candidate_buyers = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.buyers_sorted)
        if candidate_buyers != buyers_sorted:
            continue
        if found is not None:
            raise RuntimeError(f"T={timestep} {node_name}: two trade results share buyers.")
        found = trade_result
    if found is None:
        raise RuntimeError(f"T={timestep} {node_name}: no trade result matches selected buyers.")
    return found


def _traffic_by_key(local_result, node_name: str, timestep: int) -> dict:
    mapping = {}
    for record in local_result.traffic_observation_records:
        if not isinstance(record, OrderControlTvtMpCandidateTrafficObservationRecord):
            raise RuntimeError(f"T={timestep} {node_name}: traffic record type is wrong.")
        visit_key = _plain_visit_key(record.visit_key)
        if visit_key in mapping:
            raise RuntimeError(f"T={timestep} {node_name}: duplicate traffic record {_visit_text(visit_key)}.")
        mapping[visit_key] = record
    return mapping


def _binding_by_key(local_result) -> dict:
    mapping = {}
    for binding_visit in local_result.binding_rank_sequence.visits_in_binding_order:
        mapping[_plain_visit_key(binding_visit.visit_key)] = binding_visit
    return mapping


def _participation(world, vehicle_name: str) -> bool:
    vehicle = world.VEHICLES.get(vehicle_name)
    if vehicle is None:
        raise RuntimeError(f"Vehicle {vehicle_name!r} is missing.")
    participates = vehicle.participates_in_order_exchange
    if type(participates) is not bool:
        raise RuntimeError(f"{vehicle_name} participates_in_order_exchange is {participates!r}.")
    return participates


def _require_inlink(inlink_name, visit_key, node_name: str, timestep: int) -> str:
    if not isinstance(inlink_name, str) or inlink_name == "":
        raise RuntimeError(
            f"T={timestep} {node_name}: {_visit_text(visit_key)} inlink_name is {inlink_name!r}."
        )
    return inlink_name


def _group_by_inlink(parties) -> dict:
    grouped = {}
    for party in parties:
        inlink_name = party["inlink_name"]
        if inlink_name not in grouped:
            grouped[inlink_name] = {"buyer": [], "seller": [], "nonparticipating": []}
        grouped[inlink_name][party["role"]].append(party["visit_key"])
    return grouped


def _same_inlink_flags(parties) -> dict:
    grouped = _group_by_inlink(parties)
    multiple_buyer = False
    multiple_seller = False
    buyer_and_nonparticipating = False
    seller_and_nonparticipating = False
    combinations = []
    for inlink_name in sorted(grouped):
        roles = grouped[inlink_name]
        if len(roles["buyer"]) >= 2:
            multiple_buyer = True
            combinations.append(f"{inlink_name}:multiple_buyers")
        if len(roles["seller"]) >= 2:
            multiple_seller = True
            combinations.append(f"{inlink_name}:multiple_sellers")
        if len(roles["buyer"]) >= 1 and len(roles["nonparticipating"]) >= 1:
            buyer_and_nonparticipating = True
            combinations.append(f"{inlink_name}:buyer+nonparticipating")
        if len(roles["seller"]) >= 1 and len(roles["nonparticipating"]) >= 1:
            seller_and_nonparticipating = True
            combinations.append(f"{inlink_name}:seller+nonparticipating")
    return {
        "same_inlink_multiple_buyer": multiple_buyer,
        "same_inlink_multiple_seller": multiple_seller,
        "same_inlink_buyer_and_nonparticipating": buyer_and_nonparticipating,
        "same_inlink_seller_and_nonparticipating": seller_and_nonparticipating,
        "same_inlink_participant_and_nonparticipating": (
            buyer_and_nonparticipating or seller_and_nonparticipating
        ),
        "same_inlink_role_combinations": "|".join(combinations),
    }


def _unique_inlinks(parties, role_name: str) -> str:
    names = []
    for party in parties:
        if party["role"] != role_name:
            continue
        if party["inlink_name"] not in names:
            names.append(party["inlink_name"])
    return "|".join(names)


def _capture_selected(world, columns, node_name: str, timestep: int) -> None:
    selection_node = _one_node(columns["selection_nodes"], node_name, timestep, "selection")
    selected_economic = selection_node.selected_candidate_economic_result
    if selected_economic is None:
        return
    economic_node = _one_node(columns["economic_nodes"], node_name, timestep, "economic")
    evaluation_index = _evaluation_index(
        economic_node.candidate_economic_evaluation_results,
        selected_economic,
        node_name,
        timestep,
    )
    local_result = selected_economic.candidate_local_virtual_calculation_result
    buyers_sorted = tuple(
        _plain_visit_key(visit_key)
        for visit_key in local_result.binding_rank_sequence.concrete_buyer_candidate_set.buyers_sorted
    )
    trade_rank_node = _one_node(columns["trade_rank_nodes"], node_name, timestep, "trade rank")
    trade_result = _matching_trade_result(trade_rank_node, buyers_sorted, node_name, timestep)
    sellers_sorted = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.sellers_sorted)
    nonparticipating_sorted = tuple(
        _plain_visit_key(visit_key) for visit_key in trade_result.nonparticipating_visits_sorted
    )
    trade_scope = tuple(_plain_visit_key(visit_key) for visit_key in trade_result.trade_scope)
    expected_scope = set(buyers_sorted + sellers_sorted + nonparticipating_sorted)
    if set(trade_scope) != expected_scope or len(trade_scope) != len(expected_scope):
        raise RuntimeError(f"T={timestep} {node_name}: trade_scope does not match role lists.")
    candidate_visit_node = _one_node(
        columns["candidate_visit_nodes"], node_name, timestep, "candidate visits"
    )
    baseline_ranks = _baseline_ranks(candidate_visit_node.candidate_visits, node_name, timestep)
    post_trade = _post_trade_ranks(trade_result, trade_scope, node_name, timestep)
    traffic = _traffic_by_key(local_result, node_name, timestep)
    binding = _binding_by_key(local_result)
    right_of_entry_node = _one_node(
        columns["right_of_entry_nodes"], node_name, timestep, "right of entry"
    )
    right_of_entry = None
    if right_of_entry_node.right_of_entry_visit_key is not None:
        right_of_entry = _plain_visit_key(right_of_entry_node.right_of_entry_visit_key)
    identity = f"T={timestep}|{node_name}|index={evaluation_index}|{_join_visits(buyers_sorted)}"
    parties = []
    for visit_key in trade_scope:
        record = traffic.get(visit_key)
        if record is None:
            raise RuntimeError(f"T={timestep} {node_name}: {_visit_text(visit_key)} has no traffic record.")
        role_name = _role_name(record.trade_role)
        participates = _participation(world, visit_key[0])
        if role_name in ("buyer", "seller") and participates is not True:
            raise RuntimeError(f"{_visit_text(visit_key)} role {role_name} is not participating.")
        if role_name == "nonparticipating" and participates is not False:
            raise RuntimeError(f"{_visit_text(visit_key)} nonparticipating flag is not False.")
        binding_visit = binding.get(visit_key)
        if binding_visit is None:
            raise RuntimeError(f"T={timestep} {node_name}: {_visit_text(visit_key)} has no binding visit.")
        parties.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": timestep,
                "node_name": node_name,
                "candidate_identity": identity,
                "selected_candidate_evaluation_index": evaluation_index,
                "buyers_sorted": _join_visits(buyers_sorted),
                "sellers_sorted": _join_visits(sellers_sorted),
                "nonparticipating_visits_sorted": _join_visits(nonparticipating_sorted),
                "vehicle_name": visit_key[0],
                "visit_id": visit_key[1],
                "visit_key": _visit_text(visit_key),
                "visit_key_tuple": visit_key,
                "role": role_name,
                "participates_in_order_exchange": participates,
                "inlink_name": _require_inlink(record.inlink_name, visit_key, node_name, timestep),
                "baseline_local_rank": baseline_ranks[visit_key],
                "post_trade_local_rank": post_trade[visit_key],
                "binding_partition": binding_visit.binding_partition.value,
                "is_right_of_entry_holder": visit_key == right_of_entry,
            }
        )
    flags = _same_inlink_flags(parties)
    transaction = {
        "scenario_name": SCENARIO_NAME,
        "tvt_decision_timestep": timestep,
        "node_name": node_name,
        "candidate_identity": identity,
        "selected_candidate_evaluation_index": evaluation_index,
        "buyers_sorted": _join_visits(buyers_sorted),
        "sellers_sorted": _join_visits(sellers_sorted),
        "nonparticipating_visits_sorted": _join_visits(nonparticipating_sorted),
        "buyer_keys": buyers_sorted,
        "seller_keys": sellers_sorted,
        "buyer_count": len(buyers_sorted),
        "seller_count": len(sellers_sorted),
        "nonparticipating_count": len(nonparticipating_sorted),
        "trade_scope_count": len(trade_scope),
        "buyer_inlinks": _unique_inlinks(parties, "buyer"),
        "seller_inlinks": _unique_inlinks(parties, "seller"),
        "nonparticipating_inlinks": _unique_inlinks(parties, "nonparticipating"),
        "parties": parties,
        **flags,
    }
    GATE.transactions.append(transaction)


def _record_decision(world, result) -> None:
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"Driver result type is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        return
    timestep = world.T
    if type(timestep) is not int or type(timestep) is bool:
        raise RuntimeError(f"Driver World.T is {timestep!r}.")
    columns = _saved_columns(atomic)
    seen = []
    for local_node in columns["local_nodes"]:
        if not isinstance(local_node, OrderControlTvtNodeMpLocalVirtualCalculationResult):
            raise RuntimeError(f"T={timestep}: local node type is {type(local_node).__name__}.")
        if local_node.node_name in seen:
            raise RuntimeError(f"T={timestep}: local node {local_node.node_name} is repeated.")
        seen.append(local_node.node_name)
        _capture_selected(world, columns, local_node.node_name, timestep)


def wrapped_driver(world):
    result = GATE.original_driver(world)
    if world is not GATE.real_world:
        return result
    _record_decision(world, result)
    return result


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Diagnostic hooks are already installed.")
    GATE.real_world = real_world
    GATE.original_driver = driver_module.run_tvt_mp_driver
    driver_module.run_tvt_mp_driver = wrapped_driver
    GATE.installed = True


def restore_hooks() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_driver
    GATE.original_driver = None
    GATE.real_world = None
    GATE.installed = False


def _mark_maximum(transactions) -> int:
    maximum = 0
    for transaction in transactions:
        party_count = transaction["trade_scope_count"]
        if party_count > maximum:
            maximum = party_count
    for transaction in transactions:
        transaction["maximum_party_count"] = maximum
        transaction["is_maximum_party_transaction"] = transaction["trade_scope_count"] == maximum
        for party in transaction["parties"]:
            party["maximum_party_count"] = maximum
    return maximum


def _read_csv_rows(path: Path) -> list[dict]:
    if path.is_file() is not True:
        raise RuntimeError(f"Trial CSV is missing: {path}.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _transaction_key(row) -> tuple:
    return (str(row["tvt_decision_timestep"]), row["node_name"], row["buyers_sorted"])


def _compare_trial_csv(transactions) -> None:
    trial_transactions = _read_csv_rows(TRIAL_OUTPUT_DIR / "tvt_mp_transactions.csv")
    trial_visits = _read_csv_rows(TRIAL_OUTPUT_DIR / "tvt_mp_visits.csv")
    diagnostic_keys = []
    for transaction in transactions:
        key = _transaction_key(transaction)
        if key in diagnostic_keys:
            raise RuntimeError(f"Duplicate diagnostic transaction key {key}.")
        diagnostic_keys.append(key)
    trial_keys = []
    for row in trial_transactions:
        key = _transaction_key(row)
        if key in trial_keys:
            raise RuntimeError(f"Duplicate trial transaction key {key}.")
        trial_keys.append(key)
    if set(diagnostic_keys) != set(trial_keys):
        raise RuntimeError("Diagnostic transactions do not match tvt_mp_transactions.csv.")
    if len(trial_keys) != EXPECTED_TRANSACTIONS:
        raise RuntimeError(f"Trial transaction CSV has {len(trial_keys)} rows.")
    diagnostic_parties = set()
    for transaction in transactions:
        for party in transaction["parties"]:
            party_key = (
                str(transaction["tvt_decision_timestep"]),
                transaction["node_name"],
                transaction["buyers_sorted"],
                party["vehicle_name"],
                str(party["visit_id"]),
                party["role"],
            )
            if party_key in diagnostic_parties:
                raise RuntimeError(f"Duplicate diagnostic party {party_key}.")
            diagnostic_parties.add(party_key)
    trial_parties = set()
    for row in trial_visits:
        party_key = (
            str(row["tvt_decision_timestep"]),
            row["node_name"],
            row["buyers_sorted"],
            row["vehicle_name"],
            str(row["visit_id"]),
            row["role"],
        )
        if party_key in trial_parties:
            raise RuntimeError(f"Duplicate trial visit {party_key}.")
        trial_parties.add(party_key)
    if diagnostic_parties != trial_parties:
        raise RuntimeError("Diagnostic parties do not match tvt_mp_visits.csv.")
    if len(trial_parties) != EXPECTED_PARTIES:
        raise RuntimeError(f"Trial visit CSV has {len(trial_parties)} rows.")


def _validate_runtime(world, transactions, maximum_party_count) -> None:
    if world.T != EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T_AFTER_SIM}.")
    participating = 0
    nonparticipating = 0
    for vehicle in world.VEHICLES.values():
        if vehicle.participates_in_order_exchange is True:
            participating = participating + 1
        elif vehicle.participates_in_order_exchange is False:
            nonparticipating = nonparticipating + 1
    if participating != trial.EXPECTED_PARTICIPATING_COUNT:
        raise RuntimeError(f"Participating count is {participating}.")
    if nonparticipating != trial.EXPECTED_NONPARTICIPATING_COUNT:
        raise RuntimeError(f"Nonparticipating count is {nonparticipating}.")
    if len(transactions) != EXPECTED_TRANSACTIONS:
        raise RuntimeError(f"Established transaction count is {len(transactions)}.")
    buyer_count = 0
    seller_count = 0
    nonparticipating_count = 0
    multiple_buyer = 0
    multiple_seller = 0
    nonparticipating_transactions = 0
    maximum_transactions = []
    for transaction in transactions:
        recomputed = _same_inlink_flags(transaction["parties"])
        for field_name in recomputed:
            if transaction[field_name] != recomputed[field_name]:
                raise RuntimeError(f"Same-inlink flag {field_name} does not match party grouping.")
        role_total = (
            transaction["buyer_count"]
            + transaction["seller_count"]
            + transaction["nonparticipating_count"]
        )
        if role_total != transaction["trade_scope_count"]:
            raise RuntimeError("trade_scope_count does not equal role counts.")
        if len(transaction["parties"]) != transaction["trade_scope_count"]:
            raise RuntimeError("Party count does not equal trade_scope_count.")
        buyer_count = buyer_count + transaction["buyer_count"]
        seller_count = seller_count + transaction["seller_count"]
        nonparticipating_count = nonparticipating_count + transaction["nonparticipating_count"]
        if transaction["buyer_count"] >= 2:
            multiple_buyer = multiple_buyer + 1
        if transaction["seller_count"] >= 2:
            multiple_seller = multiple_seller + 1
        if transaction["nonparticipating_count"] >= 1:
            nonparticipating_transactions = nonparticipating_transactions + 1
        if transaction["is_maximum_party_transaction"] is True:
            maximum_transactions.append(transaction)
    if buyer_count != EXPECTED_BUYERS or seller_count != EXPECTED_SELLERS:
        raise RuntimeError("Buyer or seller party count differs.")
    if nonparticipating_count != EXPECTED_NONPARTICIPATING_PARTIES:
        raise RuntimeError("Nonparticipating party count differs.")
    if buyer_count + seller_count + nonparticipating_count != EXPECTED_PARTIES:
        raise RuntimeError("Party total is not 626.")
    if nonparticipating_transactions != EXPECTED_NONPARTICIPATING_TRANSACTIONS:
        raise RuntimeError("Nonparticipating transaction count differs.")
    if multiple_buyer != EXPECTED_MULTIPLE_BUYER_TRANSACTIONS:
        raise RuntimeError("Multiple-buyer transaction count differs.")
    if multiple_seller != EXPECTED_MULTIPLE_SELLER_TRANSACTIONS:
        raise RuntimeError("Multiple-seller transaction count differs.")
    if maximum_party_count != EXPECTED_MAXIMUM_PARTY_COUNT:
        raise RuntimeError(f"Maximum party count is {maximum_party_count}.")
    if len(maximum_transactions) != EXPECTED_MAXIMUM_PARTY_TRANSACTIONS:
        raise RuntimeError("Maximum party transaction count differs.")
    maximum = maximum_transactions[0]
    expected = EXPECTED_MAXIMUM_TRANSACTION
    if maximum["tvt_decision_timestep"] != expected["tvt_decision_timestep"]:
        raise RuntimeError("Maximum transaction timestep is not T=392.")
    if maximum["node_name"] != expected["node_name"]:
        raise RuntimeError("Maximum transaction node is not northwest_intersection.")
    if set(maximum["buyer_keys"]) != expected["buyers"]:
        raise RuntimeError("Maximum transaction buyers differ.")
    if set(maximum["seller_keys"]) != expected["sellers"]:
        raise RuntimeError("Maximum transaction sellers differ.")
    if maximum["nonparticipating_count"] != 0 or maximum["trade_scope_count"] != 6:
        raise RuntimeError("Maximum transaction role counts differ.")
    _compare_trial_csv(transactions)


def _format_transaction_line(transaction) -> str:
    return (
        f"T={transaction['tvt_decision_timestep']} {transaction['node_name']} "
        f"parties={transaction['trade_scope_count']} "
        f"buyer={transaction['buyer_count']} seller={transaction['seller_count']} "
        f"nonparticipating={transaction['nonparticipating_count']} "
        f"combinations={transaction['same_inlink_role_combinations']}"
    )


def _build_summary(transactions, maximum_party_count) -> str:
    same_buyer = [row for row in transactions if row["same_inlink_multiple_buyer"] is True]
    same_seller = [row for row in transactions if row["same_inlink_multiple_seller"] is True]
    coexist_buyer = [row for row in transactions if row["same_inlink_buyer_and_nonparticipating"] is True]
    coexist_seller = [row for row in transactions if row["same_inlink_seller_and_nonparticipating"] is True]
    coexist = [row for row in transactions if row["same_inlink_participant_and_nonparticipating"] is True]
    maximum_rows = [row for row in transactions if row["is_maximum_party_transaction"] is True]
    multiple_buyer = sum(1 for row in transactions if row["buyer_count"] >= 2)
    multiple_seller = sum(1 for row in transactions if row["seller_count"] >= 2)
    nonparticipating_rows = [row for row in transactions if row["nonparticipating_count"] >= 1]
    lines = [
        "成立取引の正式inlink集計（selected Candidateの保存inlink_name）。",
        "Vehicle名からinlinkは推測していない。",
        f"成立取引数: {len(transactions)}",
        f"最大当事者数: {maximum_party_count}",
        f"複数buyer取引数: {multiple_buyer}",
        f"そのうち同一inlink複数buyer: {len(same_buyer)}",
        f"複数seller取引数: {multiple_seller}",
        f"そのうち同一inlink複数seller: {len(same_seller)}",
        f"nonparticipating含有取引数: {len(nonparticipating_rows)}",
        f"同一inlinkにbuyerとnonparticipating: {len(coexist_buyer)}",
        f"同一inlinkにsellerとnonparticipating: {len(coexist_seller)}",
        f"同一inlinkにbuyerまたはsellerとnonparticipating: {len(coexist)}",
        "",
        "最大当事者取引:",
    ]
    for row in maximum_rows:
        lines.append(
            f"  T={row['tvt_decision_timestep']} {row['node_name']} "
            f"buyers={row['buyers_sorted']} sellers={row['sellers_sorted']} "
            f"nonparticipating={row['nonparticipating_visits_sorted']}"
        )
    lines.append("")
    lines.append("同一inlink複数buyer:")
    for row in same_buyer:
        lines.append("  " + _format_transaction_line(row))
    lines.append("")
    lines.append("同一inlink複数seller:")
    for row in same_seller:
        lines.append("  " + _format_transaction_line(row))
    lines.append("")
    lines.append("同一inlinkに参加者とnonparticipating:")
    for row in coexist:
        lines.append("  " + _format_transaction_line(row))
    return "\n".join(lines) + "\n"


def _classification_counts(transactions) -> dict:
    return {
        "same_inlink_multiple_buyer": sum(
            1 for row in transactions if row["same_inlink_multiple_buyer"] is True
        ),
        "same_inlink_multiple_seller": sum(
            1 for row in transactions if row["same_inlink_multiple_seller"] is True
        ),
        "same_inlink_buyer_and_nonparticipating": sum(
            1 for row in transactions if row["same_inlink_buyer_and_nonparticipating"] is True
        ),
        "same_inlink_seller_and_nonparticipating": sum(
            1 for row in transactions if row["same_inlink_seller_and_nonparticipating"] is True
        ),
        "same_inlink_participant_and_nonparticipating": sum(
            1 for row in transactions if row["same_inlink_participant_and_nonparticipating"] is True
        ),
        "nonparticipating_transactions": sum(
            1 for row in transactions if row["nonparticipating_count"] >= 1
        ),
        "multiple_buyer_transactions": sum(1 for row in transactions if row["buyer_count"] >= 2),
        "multiple_seller_transactions": sum(1 for row in transactions if row["seller_count"] >= 2),
    }


def _write_outputs(transactions, maximum_party_count) -> None:
    parties = []
    for transaction in transactions:
        parties.extend(transaction["parties"])
    summary = _build_summary(transactions, maximum_party_count)
    manifest = {
        "diagnostic_script": SCRIPT_PATH.name,
        "scenario_name": SCENARIO_NAME,
        "input_trial_output_directory": str(TRIAL_OUTPUT_DIR),
        "expected_counts": {
            "transactions": EXPECTED_TRANSACTIONS,
            "parties": EXPECTED_PARTIES,
            "buyers": EXPECTED_BUYERS,
            "sellers": EXPECTED_SELLERS,
            "nonparticipating_parties": EXPECTED_NONPARTICIPATING_PARTIES,
            "nonparticipating_transactions": EXPECTED_NONPARTICIPATING_TRANSACTIONS,
            "multiple_buyer_transactions": EXPECTED_MULTIPLE_BUYER_TRANSACTIONS,
            "multiple_seller_transactions": EXPECTED_MULTIPLE_SELLER_TRANSACTIONS,
            "maximum_party_count": EXPECTED_MAXIMUM_PARTY_COUNT,
        },
        "actual_counts": {
            "transactions": len(transactions),
            "parties": len(parties),
        },
        "maximum_party_count": maximum_party_count,
        "classification_counts": _classification_counts(transactions),
        "output_files": list(OUTPUT_FILE_NAMES),
    }
    _write_csv(OUTPUT_DIR / TRANSACTION_CSV, TRANSACTION_COLUMNS, transactions)
    _write_csv(OUTPUT_DIR / PARTY_CSV, PARTY_COLUMNS, parties)
    _write_csv(
        OUTPUT_DIR / MAXIMUM_CSV,
        TRANSACTION_COLUMNS,
        [row for row in transactions if row["is_maximum_party_transaction"] is True],
    )
    _write_csv(
        OUTPUT_DIR / SAME_BUYER_CSV,
        TRANSACTION_COLUMNS,
        [row for row in transactions if row["same_inlink_multiple_buyer"] is True],
    )
    _write_csv(
        OUTPUT_DIR / SAME_SELLER_CSV,
        TRANSACTION_COLUMNS,
        [row for row in transactions if row["same_inlink_multiple_seller"] is True],
    )
    _write_csv(
        OUTPUT_DIR / NONPARTICIPATING_CSV,
        TRANSACTION_COLUMNS,
        [row for row in transactions if row["nonparticipating_count"] >= 1],
    )
    _write_csv(
        OUTPUT_DIR / COEXIST_CSV,
        TRANSACTION_COLUMNS,
        [row for row in transactions if row["same_inlink_participant_and_nonparticipating"] is True],
    )
    (OUTPUT_DIR / SUMMARY_NAME).write_text(summary, encoding="utf-8")
    (OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    GATE.transactions = []
    original_limit = sys.getrecursionlimit()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if OUTPUT_DIR == TRIAL_OUTPUT_DIR:
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
        build_tvt_mp_research_output(world, SCENARIO_NAME)
        maximum_party_count = _mark_maximum(GATE.transactions)
        _validate_runtime(world, GATE.transactions, maximum_party_count)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_outputs(GATE.transactions, maximum_party_count)
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


def _ast_label(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_label(node.value)
        if parent is None:
            return None
        return parent + "." + node.attr
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    return None


def _assignment_pairs(function_node):
    pairs = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = _ast_label(node.targets[0])
        value = _ast_label(node.value)
        if target is not None and value is not None:
            pairs.append((target, value))
    return pairs


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if OUTPUT_DIR == TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory equals the trial output directory.")
    output_text = str(OUTPUT_DIR)
    if "established_party_inlinks" not in output_text:
        raise RuntimeError("OUTPUT_DIR name is missing established_party_inlinks.")
    if "all_participating" in output_text:
        raise RuntimeError("OUTPUT_DIR collides with the all-participating diagnostic.")
    for file_name in OUTPUT_FILE_NAMES:
        if file_name not in source:
            raise RuntimeError(f"Output file name {file_name} is missing.")
    for expected_text in (
        "same_inlink_multiple_buyer",
        "same_inlink_multiple_seller",
        "same_inlink_buyer_and_nonparticipating",
        "same_inlink_seller_and_nonparticipating",
        "same_inlink_participant_and_nonparticipating",
    ):
        if expected_text not in source:
            raise RuntimeError(f"Same-inlink class {expected_text} is missing.")
    wrapper = _function_node(tree, "wrapped_driver")
    if wrapper is None:
        raise RuntimeError("wrapped_driver is missing.")
    original_calls = 0
    for node in ast.walk(wrapper):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "original_driver":
                original_calls = original_calls + 1
    if original_calls != 1:
        raise RuntimeError("wrapped_driver must call original_driver exactly once.")
    install_node = _function_node(tree, "install_hooks")
    restore_node = _function_node(tree, "restore_hooks")
    if install_node is None or restore_node is None:
        raise RuntimeError("install_hooks or restore_hooks is missing.")
    install_pairs = _assignment_pairs(install_node)
    restore_pairs = _assignment_pairs(restore_node)
    if ("GATE.original_driver", "driver_module.run_tvt_mp_driver") not in install_pairs:
        raise RuntimeError("install_hooks does not save the original driver.")
    if ("driver_module.run_tvt_mp_driver", "wrapped_driver") not in install_pairs:
        raise RuntimeError("install_hooks does not install wrapped_driver.")
    if ("driver_module.run_tvt_mp_driver", "GATE.original_driver") not in restore_pairs:
        raise RuntimeError("restore_hooks does not restore the original driver.")
    static_function = _function_node(tree, "validate_static_contract")
    if static_function is None:
        raise RuntimeError("validate_static_contract is missing.")
    for node in ast.walk(static_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "install_hooks", "restore_hooks", "mkdir"):
                raise RuntimeError("Static validation runs simulation, hooks, or mkdir.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("install_hooks", "restore_hooks", "exec_simulation"):
                raise RuntimeError("Static validation runs simulation or hooks.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
        if isinstance(node, ast.FunctionDef) and "inlink_from_vehicle" in node.name:
            raise RuntimeError("Diagnostic infers inlink from a vehicle name.")
    called = []
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    for name in ("system", "rmtree", "unlink", "rmdir"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
    for module_name in imported:
        if module_name in ("subprocess", "shutil", "git"):
            raise RuntimeError(f"Diagnostic imports {module_name}.")
    if _function_node(tree, "_same_inlink_flags") is None:
        raise RuntimeError("_same_inlink_flags is missing.")
    if "record.inlink_name" not in source and "traffic" not in source:
        raise RuntimeError("Diagnostic does not read a saved inlink_name.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
