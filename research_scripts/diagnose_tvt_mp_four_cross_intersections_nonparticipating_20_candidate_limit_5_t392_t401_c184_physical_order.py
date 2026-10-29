"""
Read-only diagnostic: T=392/T=401 baseline snapshot inlink physical order vs C184/C185.

Uses fork_result.inlink_physical_orders and formal driver atomic chain only.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial as trial
import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState

TARGET_NODE_NAME = "northwest_intersection"
TIMESTEP_T392 = 392
TIMESTEP_T401 = 401
CAPTURE_TIMESTEPS = frozenset({TIMESTEP_T392, TIMESTEP_T401})
SIMULATION_UNTIL_TIMESTEP = 401
EXPECTED_WORLD_T_AFTER_SIM = 402

VISIT_A = ("veh_sw_nw_base_041", 2)
VISIT_B = ("veh_wn_se_base_025", 1)

T392_SELECTED_TRADE_SCOPE = frozenset(
    {
        ("veh_nw_sw_base_048", 1),
        ("veh_en_sw_base_026", 2),
        ("veh_sw_nw_base_039", 2),
        ("veh_sw_nw_base_040", 2),
        ("veh_wn_en_base_025", 1),
    }
)

EXPECTED_T392_C_RANKS = {
    ("veh_nw_sw_base_048", 1): 179,
    ("veh_en_sw_base_026", 2): 180,
    ("veh_sw_nw_base_039", 2): 181,
    ("veh_sw_nw_base_040", 2): 182,
    ("veh_wn_en_base_025", 1): 183,
}

REASON_ARRIVED_AT_SNAPSHOT = "was_arrived_at_snapshot"
REASON_RANK_CONFIRMED = "rank_already_confirmed"
REASON_ARRIVAL_UNAVAILABLE = "baseline_arrival_unavailable"
REASON_ARRIVAL_AFTER_P_MINUS_ONE = "baseline_arrival_later_than_p_minus_one"
REASON_OUTSIDE_CANDIDATE_LIMIT = "candidate_count_limit_outside_top_n"
REASON_NOT_IN_SNAPSHOT_EXPORT = "not_in_snapshot_fixed_visit_set"
REASON_OTHER_INCONSISTENCY = "other_formal_inconsistency"
REASON_P_MINUS_ONE_ELIGIBLE = "p_minus_one_eligible"

FORMAL_CANDIDATE_OUTSIDE_INELIGIBLE_REASONS = frozenset(
    {
        REASON_OUTSIDE_CANDIDATE_LIMIT,
        REASON_ARRIVAL_AFTER_P_MINUS_ONE,
        REASON_ARRIVAL_UNAVAILABLE,
        REASON_NOT_IN_SNAPSHOT_EXPORT,
        REASON_ARRIVED_AT_SNAPSHOT,
        REASON_RANK_CONFIRMED,
    }
)

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "t392_t401_c184_physical_order"
    )
)
COMPARISON_CSV = "t392_t401_target_visit_comparison.csv"
INLINK_ORDERS_CSV = "t392_t401_inlink_physical_orders.csv"
REVIEW_NAME = "t392_t401_c184_physical_order_review.txt"
OUTPUT_FILE_NAMES = (COMPARISON_CSV, INLINK_ORDERS_CSV, REVIEW_NAME)

COMPARISON_COLUMNS = (
    "record_kind",
    "decision_timestep",
    "target_label",
    "visit_key",
    "in_physical_order",
    "formal_inlink_name",
    "physical_index_head_to_tail",
    "ahead_visit_keys",
    "same_inlink_as_other_target",
    "physical_relation_to_other_target",
    "in_candidate_visits",
    "in_collector_export",
    "was_arrived_at_snapshot",
    "baseline_arrival_timestep",
    "baseline_passage_timestep",
    "p_minus_one_eligible",
    "p_minus_one_ineligible_reason",
    "right_of_entry_visit_key",
    "is_right_of_entry",
    "candidate_baseline_local_rank",
    "appears_as_considered_buyer",
    "selected_candidate_present",
    "pre_rank_status",
    "pre_assigned_c_rank",
    "post_rank_status",
    "post_assigned_c_rank",
    "assigned_c_rank_after_decision",
    "selected_trade_scope_visits_ahead",
    "selected_trade_scope_ahead_count",
    "behind_any_t392_selected_trade_scope_visit",
    "finalization_source",
    "final_rank_status",
)

INLINK_COLUMNS = (
    "record_kind",
    "decision_timestep",
    "node_name",
    "inlink_name",
    "physical_index",
    "visit_key",
    "reference_target_label",
    "in_t392_selected_trade_scope",
    "baseline_arrival_timestep",
    "baseline_passage_timestep",
    "assigned_c_rank_after_t392_decision",
    "assigned_c_rank_after_t401_decision",
    "visit_keys_head_to_tail",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.original_arrival = None
        self.captures: dict[int, dict] = {}
        self.comparison_rows: list[dict] = []
        self.inlink_rows: list[dict] = []
        self.review_text = ""


GATE = _Gate()


def _visit_text(visit_key) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple:
    return (visit_key[0], visit_key[1])


def _visit_keys_pipe(visit_keys) -> str:
    return "|".join(_visit_text(_plain_visit_key(key)) for key in visit_keys)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _validate_csv_rows(columns, rows, label: str) -> None:
    column_set = set(columns)
    for index, row in enumerate(rows):
        if type(row) is not dict:
            raise RuntimeError(f"{label} row {index} is not a dict.")
        extra = set(row.keys()) - column_set
        if len(extra) != 0:
            raise RuntimeError(f"{label} row {index} extra keys {sorted(extra)!r}.")
        missing = column_set - set(row.keys())
        if len(missing) != 0:
            raise RuntimeError(f"{label} row {index} missing keys {sorted(missing)!r}.")


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row[column]) for column in columns})


def _one_node(results, node_name: str, label: str):
    matched = None
    count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(f"{node_name} {label} count is {count}.")
    return matched


def _stages_from_atomic(atomic) -> dict:
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
        raise RuntimeError("fork_result type is wrong.")
    collector = fork_result.collector
    if not isinstance(collector, OrderControlBaselineCollector):
        raise RuntimeError("collector type is wrong.")
    return {
        "fork_result": fork_result,
        "collector": collector,
        "inlink_physical_orders": fork_result.inlink_physical_orders,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "final_rank_nodes": final_rank_set.node_final_rank_results,
    }


def _rank_state(world) -> OrderControlTvtNodeRankState:
    rank_state = world.order_control_tvt_rank_states_by_node_name.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise RuntimeError(f"Northwest rank state missing at World.T={world.T}.")
    return rank_state


def _rank_membership_snapshot(world) -> dict:
    rank_state = _rank_state(world)
    confirmed_ranks_by_visit_key: dict[tuple, int] = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        assigned = rank_state.assigned_rank(visit_key)
        if assigned is None:
            raise RuntimeError(f"{_visit_text(plain)} is confirmed but has no assigned rank.")
        confirmed_ranks_by_visit_key[plain] = assigned
    undetermined_visit_keys = frozenset(
        _plain_visit_key(visit_key) for visit_key in rank_state.undetermined_visit_keys()
    )
    overlap = set(confirmed_ranks_by_visit_key) & undetermined_visit_keys
    if len(overlap) != 0:
        raise RuntimeError("Confirmed and undetermined visit keys overlap in rank snapshot.")
    return {
        "confirmed_ranks_by_visit_key": confirmed_ranks_by_visit_key,
        "undetermined_visit_keys": undetermined_visit_keys,
    }


def _rank_status_label(snapshot: dict, visit_key: tuple) -> str:
    if visit_key in snapshot["confirmed_ranks_by_visit_key"]:
        return "confirmed"
    if visit_key in snapshot["undetermined_visit_keys"]:
        return "undetermined"
    return "absent"


def _assigned_rank_from_snapshot(snapshot: dict, visit_key: tuple):
    return snapshot["confirmed_ranks_by_visit_key"].get(visit_key)


def _selected_trade_scope_ahead_of_visit(ahead_visit_keys: list[tuple]) -> tuple[list[tuple], int, bool]:
    selected_ahead = [key for key in ahead_visit_keys if key in T392_SELECTED_TRADE_SCOPE]
    count = len(selected_ahead)
    return selected_ahead, count, count > 0


def _collector_record(collector, visit_key: tuple) -> dict | None:
    return collector.get_baseline_visit_snapshot(visit_key[0], visit_key[1])


def _require_bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise RuntimeError(f"{label} must be bool.")
    return value


def _p_minus_one_ordered_keys(collector, pre_rank_snapshot: dict, p: int) -> list[tuple]:
    exported = collector.export_node_baseline_visits(TARGET_NODE_NAME)
    selected: list[tuple] = []
    for record in exported:
        if _require_bool(record["was_arrived_at_snapshot"], "was_arrived_at_snapshot"):
            continue
        visit_key = (record["vehicle_name"], record["visit_id"])
        if visit_key in pre_rank_snapshot["confirmed_ranks_by_visit_key"]:
            continue
        if visit_key not in pre_rank_snapshot["undetermined_visit_keys"]:
            continue
        arrival_value = record["baseline_arrival_timestep"]
        if arrival_value is None:
            continue
        if type(arrival_value) is not int or type(arrival_value) is bool:
            raise RuntimeError("baseline_arrival_timestep type is wrong.")
        if arrival_value > p - 1:
            continue
        selected.append(visit_key)
    def _sort_key(key: tuple):
        record = _collector_record(collector, key)
        if record is None:
            raise RuntimeError(f"{_visit_text(key)} missing from collector during P-1 sort.")
        return (
            record["baseline_arrival_timestep"],
            record["arrival_tiebreaker"],
            record["vehicle_id"],
        )

    selected.sort(key=_sort_key)
    return selected


def _classify_p_minus_one(
    visit_key: tuple,
    collector,
    pre_rank_snapshot: dict,
    p: int,
    candidate_visit_keys: list[tuple],
) -> tuple[bool, str]:
    record = _collector_record(collector, visit_key)
    if record is None:
        return False, REASON_NOT_IN_SNAPSHOT_EXPORT
    if _require_bool(record["was_arrived_at_snapshot"], "was_arrived_at_snapshot"):
        return False, REASON_ARRIVED_AT_SNAPSHOT
    if visit_key in pre_rank_snapshot["confirmed_ranks_by_visit_key"]:
        return False, REASON_RANK_CONFIRMED
    if visit_key not in pre_rank_snapshot["undetermined_visit_keys"]:
        return False, REASON_OTHER_INCONSISTENCY
    arrival_value = record["baseline_arrival_timestep"]
    if arrival_value is None:
        return False, REASON_ARRIVAL_UNAVAILABLE
    if type(arrival_value) is not int or type(arrival_value) is bool:
        return False, REASON_OTHER_INCONSISTENCY
    if arrival_value > p - 1:
        return False, REASON_ARRIVAL_AFTER_P_MINUS_ONE
    ordered = _p_minus_one_ordered_keys(collector, pre_rank_snapshot, p)
    if visit_key not in ordered:
        return False, REASON_OTHER_INCONSISTENCY
    if visit_key in candidate_visit_keys:
        return True, REASON_P_MINUS_ONE_ELIGIBLE
    position = ordered.index(visit_key)
    if position >= trial.MAX_CANDIDATE_VISIT_COUNT:
        return False, REASON_OUTSIDE_CANDIDATE_LIMIT
    return False, REASON_OTHER_INCONSISTENCY


def _validate_physical_orders(inlink_physical_orders, timestep: int) -> list[dict]:
    rows = []
    seen_keys: set[tuple] = set()
    for physical_order in inlink_physical_orders:
        if physical_order.node_name != TARGET_NODE_NAME:
            continue
        keys = []
        for visit_key in physical_order.visit_keys_head_to_tail:
            plain = _plain_visit_key(visit_key)
            if plain in seen_keys:
                raise RuntimeError(
                    f"T={timestep} duplicate VisitKey {_visit_text(plain)} in physical orders."
                )
            seen_keys.add(plain)
            keys.append(plain)
        rows.append(
            {
                "node_name": physical_order.node_name,
                "inlink_name": physical_order.inlink_name,
                "visit_keys_head_to_tail": keys,
            }
        )
    return rows


def _locate_in_physical_orders(order_rows: list[dict], visit_key: tuple):
    for order in order_rows:
        for index, key in enumerate(order["visit_keys_head_to_tail"]):
            if key == visit_key:
                ahead = order["visit_keys_head_to_tail"][:index]
                return order["inlink_name"], index, ahead, order["visit_keys_head_to_tail"]
    return None, None, [], []


def _physical_relation(index_a, index_b, same_inlink: bool) -> str:
    if not same_inlink:
        return "different_inlink"
    if index_a is None or index_b is None:
        return "missing_from_order"
    if index_a < index_b:
        return "A_ahead_of_B"
    if index_a > index_b:
        return "A_behind_B"
    return "same_position"


def _capture_decision(
    world,
    stages: dict,
    pre_rank_snapshot: dict,
    post_rank_snapshot: dict,
) -> dict:
    collector = stages["collector"]
    candidate_node = _one_node(stages["candidate_visit_nodes"], TARGET_NODE_NAME, "candidate visits")
    right_node = _one_node(stages["right_of_entry_nodes"], TARGET_NODE_NAME, "right of entry")
    selection_node = _one_node(stages["selection_nodes"], TARGET_NODE_NAME, "selection")
    economic_node = _one_node(stages["economic_nodes"], TARGET_NODE_NAME, "economic")
    final_rank_node = _one_node(stages["final_rank_nodes"], TARGET_NODE_NAME, "final rank")

    p = candidate_node.right_of_entry_baseline_passage_timestep
    if type(p) is not int or type(p) is bool:
        raise RuntimeError(f"T={world.T} right-of-entry passage timestep is missing.")

    candidate_visit_keys = [
        _plain_visit_key(cv.visit_key) for cv in candidate_node.candidate_visits
    ]
    order_rows = _validate_physical_orders(stages["inlink_physical_orders"], world.T)

    roe_key = None
    if right_node.right_of_entry_visit_key is not None:
        roe_key = _plain_visit_key(right_node.right_of_entry_visit_key)

    selected_present = selection_node.selected_candidate_economic_result is not None

    buyers_in_any: dict[tuple, bool] = {VISIT_A: False, VISIT_B: False}
    for candidate_economic in economic_node.candidate_economic_evaluation_results:
        sequence = candidate_economic.candidate_local_virtual_calculation_result.binding_rank_sequence
        for buyer_key in sequence.concrete_buyer_candidate_set.buyers_sorted:
            plain = _plain_visit_key(buyer_key)
            if plain in buyers_in_any:
                buyers_in_any[plain] = True

    final_by_key = {}
    for final_visit in final_rank_node.final_rank_visits:
        plain = _plain_visit_key(final_visit.visit_key)
        final_by_key[plain] = final_visit

    targets = {"A": VISIT_A, "B": VISIT_B}
    target_info: dict[str, dict] = {}
    for label, visit_key in targets.items():
        inlink, index, ahead, _full = _locate_in_physical_orders(order_rows, visit_key)
        record = _collector_record(collector, visit_key)
        eligible, reason = _classify_p_minus_one(
            visit_key, collector, pre_rank_snapshot, p, candidate_visit_keys
        )
        local_rank = ""
        if visit_key in candidate_visit_keys:
            local_rank = str(candidate_visit_keys.index(visit_key) + 1)
        final_visit = final_by_key.get(visit_key)
        post_assigned = _assigned_rank_from_snapshot(post_rank_snapshot, visit_key)
        scope_ahead: list[tuple] = []
        scope_ahead_count = ""
        behind_scope = ""
        if world.T == TIMESTEP_T392 and label == "A":
            if inlink is None:
                scope_ahead = []
                scope_ahead_count = "not_in_physical_order"
                behind_scope = "not_in_physical_order"
            else:
                scope_ahead, scope_count, behind_flag = _selected_trade_scope_ahead_of_visit(ahead)
                scope_ahead_count = scope_count
                behind_scope = behind_flag
        target_info[label] = {
            "visit_key": visit_key,
            "in_physical_order": inlink is not None,
            "formal_inlink_name": inlink if inlink is not None else "",
            "physical_index": index,
            "ahead_visit_keys": ahead,
            "in_candidate_visits": visit_key in candidate_visit_keys,
            "in_collector_export": record is not None,
            "was_arrived_at_snapshot": record.get("was_arrived_at_snapshot") if record else "",
            "baseline_arrival_timestep": record.get("baseline_arrival_timestep") if record else "",
            "baseline_passage_timestep": record.get("baseline_passage_timestep") if record else "",
            "p_minus_one_eligible": eligible,
            "p_minus_one_ineligible_reason": reason if not eligible else "",
            "is_right_of_entry": roe_key == visit_key,
            "candidate_baseline_local_rank": local_rank,
            "appears_as_considered_buyer": buyers_in_any[visit_key],
            "selected_candidate_present": selected_present,
            "pre_rank_status": _rank_status_label(pre_rank_snapshot, visit_key),
            "pre_assigned_c_rank": _assigned_rank_from_snapshot(pre_rank_snapshot, visit_key),
            "post_rank_status": _rank_status_label(post_rank_snapshot, visit_key),
            "post_assigned_c_rank": post_assigned,
            "assigned_c_rank_after_decision": post_assigned,
            "selected_trade_scope_visits_ahead": scope_ahead,
            "selected_trade_scope_ahead_count": scope_ahead_count,
            "behind_any_t392_selected_trade_scope_visit": behind_scope,
            "finalization_source": final_visit.finalization_source.value if final_visit else "",
            "final_rank_status": final_rank_node.final_rank_status.value,
        }

    same_inlink = (
        target_info["A"]["formal_inlink_name"] != ""
        and target_info["A"]["formal_inlink_name"] == target_info["B"]["formal_inlink_name"]
    )
    relation = _physical_relation(
        target_info["A"]["physical_index"],
        target_info["B"]["physical_index"],
        same_inlink,
    )

    return {
        "timestep": world.T,
        "p": p,
        "roe_key": roe_key,
        "order_rows": order_rows,
        "target_info": target_info,
        "same_inlink": same_inlink,
        "physical_relation": relation,
        "candidate_visit_keys": candidate_visit_keys,
        "final_rank_visits": list(final_rank_node.final_rank_visits),
        "pre_confirmed_ranks_by_visit_key": dict(pre_rank_snapshot["confirmed_ranks_by_visit_key"]),
        "pre_undetermined_visit_keys": pre_rank_snapshot["undetermined_visit_keys"],
        "post_confirmed_ranks_by_visit_key": dict(post_rank_snapshot["confirmed_ranks_by_visit_key"]),
        "post_undetermined_visit_keys": post_rank_snapshot["undetermined_visit_keys"],
        "collector": collector,
    }


def _csv_selected_scope_cells(timestep: int, label: str, info: dict) -> tuple[str, str, str]:
    if timestep != TIMESTEP_T392 or label != "A":
        return "", "", ""
    ahead = info["selected_trade_scope_visits_ahead"]
    count_value = info["selected_trade_scope_ahead_count"]
    behind_value = info["behind_any_t392_selected_trade_scope_visit"]
    if count_value == "not_in_physical_order":
        return "not_in_physical_order", "not_in_physical_order", "not_in_physical_order"
    return _visit_keys_pipe(ahead), str(count_value), _csv_cell(behind_value)


def _post_rank_map(capture: dict) -> dict[tuple, int]:
    return capture["post_confirmed_ranks_by_visit_key"]


def _build_output_tables() -> None:
    GATE.comparison_rows = []
    GATE.inlink_rows = []
    cap392 = GATE.captures[TIMESTEP_T392]
    cap401 = GATE.captures[TIMESTEP_T401]
    post392 = _post_rank_map(cap392)
    post401 = _post_rank_map(cap401)

    for timestep in (TIMESTEP_T392, TIMESTEP_T401):
        capture = GATE.captures.get(timestep)
        if capture is None:
            raise RuntimeError(f"Missing capture for T={timestep}.")
        roe_text = _visit_text(capture["roe_key"]) if capture["roe_key"] is not None else ""
        for label in ("A", "B"):
            info = capture["target_info"][label]
            scope_visits, scope_count, behind_scope = _csv_selected_scope_cells(timestep, label, info)
            GATE.comparison_rows.append(
                {
                    "record_kind": "target",
                    "decision_timestep": timestep,
                    "target_label": label,
                    "visit_key": _visit_text(info["visit_key"]),
                    "in_physical_order": info["in_physical_order"],
                    "formal_inlink_name": info["formal_inlink_name"],
                    "physical_index_head_to_tail": info["physical_index"],
                    "ahead_visit_keys": _visit_keys_pipe(info["ahead_visit_keys"]),
                    "same_inlink_as_other_target": capture["same_inlink"],
                    "physical_relation_to_other_target": capture["physical_relation"],
                    "in_candidate_visits": info["in_candidate_visits"],
                    "in_collector_export": info["in_collector_export"],
                    "was_arrived_at_snapshot": info["was_arrived_at_snapshot"],
                    "baseline_arrival_timestep": info["baseline_arrival_timestep"],
                    "baseline_passage_timestep": info["baseline_passage_timestep"],
                    "p_minus_one_eligible": info["p_minus_one_eligible"],
                    "p_minus_one_ineligible_reason": info["p_minus_one_ineligible_reason"],
                    "right_of_entry_visit_key": roe_text,
                    "is_right_of_entry": info["is_right_of_entry"],
                    "candidate_baseline_local_rank": info["candidate_baseline_local_rank"],
                    "appears_as_considered_buyer": info["appears_as_considered_buyer"],
                    "selected_candidate_present": info["selected_candidate_present"],
                    "pre_rank_status": info["pre_rank_status"],
                    "pre_assigned_c_rank": info["pre_assigned_c_rank"],
                    "post_rank_status": info["post_rank_status"],
                    "post_assigned_c_rank": info["post_assigned_c_rank"],
                    "assigned_c_rank_after_decision": info["post_assigned_c_rank"],
                    "selected_trade_scope_visits_ahead": scope_visits,
                    "selected_trade_scope_ahead_count": scope_count,
                    "behind_any_t392_selected_trade_scope_visit": behind_scope,
                    "finalization_source": info["finalization_source"],
                    "final_rank_status": info["final_rank_status"],
                }
            )

        for order in capture["order_rows"]:
            GATE.inlink_rows.append(
                {
                    "record_kind": "inlink_order",
                    "decision_timestep": timestep,
                    "node_name": order["node_name"],
                    "inlink_name": order["inlink_name"],
                    "physical_index": "",
                    "visit_key": "",
                    "reference_target_label": "",
                    "in_t392_selected_trade_scope": "",
                    "baseline_arrival_timestep": "",
                    "baseline_passage_timestep": "",
                    "assigned_c_rank_after_t392_decision": "",
                    "assigned_c_rank_after_t401_decision": "",
                    "visit_keys_head_to_tail": _visit_keys_pipe(order["visit_keys_head_to_tail"]),
                }
            )

    for timestep in (TIMESTEP_T392, TIMESTEP_T401):
        capture = GATE.captures[timestep]
        collector = capture["collector"]
        for label, visit_key in (("A", VISIT_A), ("B", VISIT_B)):
            info = capture["target_info"][label]
            inlink = info["formal_inlink_name"]
            target_index = info["physical_index"]
            if inlink == "" or target_index is None:
                continue
            for order in capture["order_rows"]:
                if order["inlink_name"] != inlink:
                    continue
                for index, key in enumerate(order["visit_keys_head_to_tail"]):
                    if index >= target_index:
                        break
                    record = _collector_record(collector, key)
                    GATE.inlink_rows.append(
                        {
                            "record_kind": "forward_neighbor",
                            "decision_timestep": timestep,
                            "node_name": TARGET_NODE_NAME,
                            "inlink_name": inlink,
                            "physical_index": index,
                            "visit_key": _visit_text(key),
                            "reference_target_label": label,
                            "in_t392_selected_trade_scope": key in T392_SELECTED_TRADE_SCOPE,
                            "baseline_arrival_timestep": record.get("baseline_arrival_timestep") if record else "",
                            "baseline_passage_timestep": record.get("baseline_passage_timestep") if record else "",
                            "assigned_c_rank_after_t392_decision": post392.get(key),
                            "assigned_c_rank_after_t401_decision": post401.get(key),
                            "visit_keys_head_to_tail": "",
                        }
                    )
                break


def _require_int(value, label: str) -> None:
    if type(value) is not int or type(value) is bool:
        raise RuntimeError(f"{label} must be int.")


def _validate_target_b_presence(info: dict, timestep: int) -> None:
    if info["in_physical_order"] is not True or info["in_collector_export"] is not True:
        raise RuntimeError(
            f"T={timestep} B must be in snapshot physical order and collector export."
        )
    if info["formal_inlink_name"] == "":
        raise RuntimeError(f"T={timestep} B formal inlink missing.")
    if type(info["physical_index"]) is not int or type(info["physical_index"]) is bool:
        raise RuntimeError(f"T={timestep} B physical index must be int.")


def _validate_t392_visit_a(info: dict) -> None:
    if info["in_candidate_visits"] is True:
        raise RuntimeError("T=392: A should not be in candidate_visits.")
    if info["in_physical_order"] is True:
        if info["formal_inlink_name"] == "":
            raise RuntimeError("T=392 A in physical order but formal inlink is empty.")
        _require_int(info["physical_index"], "T=392 A physical index")
        if info["in_collector_export"] is not True:
            raise RuntimeError("T=392 A in physical order but missing from collector export.")
        if info["selected_trade_scope_ahead_count"] == "not_in_physical_order":
            raise RuntimeError("T=392 A in physical order but selected-scope ahead is not_in_physical_order.")
        return
    if info["physical_index"] is not None:
        raise RuntimeError("T=392 A absent from physical order but physical_index is set.")
    if len(info["ahead_visit_keys"]) != 0:
        raise RuntimeError("T=392 A absent from physical order but ahead_visit_keys is non-empty.")
    if info["selected_trade_scope_ahead_count"] != "not_in_physical_order":
        raise RuntimeError("T=392 A absent from physical order but selected-scope ahead count is wrong.")
    if info["behind_any_t392_selected_trade_scope_visit"] != "not_in_physical_order":
        raise RuntimeError("T=392 A absent from physical order but behind-scope flag is wrong.")
    if info["in_collector_export"] is not True:
        if info["p_minus_one_ineligible_reason"] != REASON_NOT_IN_SNAPSHOT_EXPORT:
            raise RuntimeError(
                "T=392 A absent from collector export must have not_in_snapshot_fixed_visit_set reason."
            )
        if info["formal_inlink_name"] != "":
            raise RuntimeError("T=392 A absent from collector export must have empty formal inlink.")
        return
    raise RuntimeError(
        "T=392 A in collector export but absent from snapshot physical order (formal contract violation)."
    )


def _validate_t401_visit_a(info: dict, cap401: dict) -> None:
    if info["in_physical_order"] is not True:
        raise RuntimeError("T=401 A must be in snapshot physical order.")
    if info["in_collector_export"] is not True:
        raise RuntimeError("T=401 A must be in collector export.")
    if info["formal_inlink_name"] == "":
        raise RuntimeError("T=401 A formal inlink missing.")
    _require_int(info["physical_index"], "T=401 A physical index")
    _require_int(info["baseline_arrival_timestep"], "T=401 A baseline arrival")
    _require_int(info["baseline_passage_timestep"], "T=401 A baseline passage")
    if info["is_right_of_entry"] is not True:
        raise RuntimeError("T=401 A must be right-of-entry.")
    if VISIT_A in cap401["pre_confirmed_ranks_by_visit_key"]:
        raise RuntimeError("T=401 pre snapshot: A must not be confirmed.")
    if VISIT_A not in cap401["pre_undetermined_visit_keys"]:
        raise RuntimeError("T=401 pre snapshot: A must be undetermined.")
    if cap401["pre_confirmed_ranks_by_visit_key"].get(VISIT_A) is not None:
        raise RuntimeError("T=401: A must not have pre-driver C rank.")
    if cap401["post_confirmed_ranks_by_visit_key"].get(VISIT_A) != 184:
        raise RuntimeError("T=401: A must have post-driver C184.")
    if cap401["roe_key"] != VISIT_A:
        raise RuntimeError("T=401 right-of-entry is not A.")


def _validate_runtime() -> None:
    cap392 = GATE.captures[TIMESTEP_T392]
    cap401 = GATE.captures[TIMESTEP_T401]
    post392 = cap392["post_confirmed_ranks_by_visit_key"]
    post401 = cap401["post_confirmed_ranks_by_visit_key"]
    for visit_key, expected in EXPECTED_T392_C_RANKS.items():
        if post392.get(visit_key) != expected:
            raise RuntimeError(f"T=392 {_visit_text(visit_key)} C rank mismatch.")
    if VISIT_B in post392:
        raise RuntimeError("T=392: B should have no C rank.")
    if VISIT_A in post392:
        raise RuntimeError("T=392: A should have no C rank.")
    if post401.get(VISIT_A) != 184:
        raise RuntimeError("T=401: A should have C184.")
    if VISIT_B in post401:
        raise RuntimeError("T=401: B should have no C rank.")
    _validate_t392_visit_a(cap392["target_info"]["A"])
    _validate_t401_visit_a(cap401["target_info"]["A"], cap401)
    _validate_target_b_presence(cap392["target_info"]["B"], TIMESTEP_T392)
    _validate_target_b_presence(cap401["target_info"]["B"], TIMESTEP_T401)
    for timestep, capture in ((TIMESTEP_T392, cap392), (TIMESTEP_T401, cap401)):
        if capture.get("order_rows") is None or len(capture["order_rows"]) == 0:
            raise RuntimeError(f"T={timestep} physical order rows missing (fork_result).")


def _p_minus_one_reason_label(reason: str) -> str:
    mapping = {
        REASON_OUTSIDE_CANDIDATE_LIMIT: "outside candidate limit",
        REASON_ARRIVAL_AFTER_P_MINUS_ONE: "arrival after P−1",
        REASON_ARRIVAL_UNAVAILABLE: "arrival unavailable",
        REASON_NOT_IN_SNAPSHOT_EXPORT: "not in snapshot fixed set",
        REASON_ARRIVED_AT_SNAPSHOT: "was_arrived_at_snapshot",
        REASON_RANK_CONFIRMED: "rank_already_confirmed",
        REASON_OTHER_INCONSISTENCY: "other",
        REASON_P_MINUS_ONE_ELIGIBLE: "p_minus_one_eligible",
    }
    return mapping.get(reason, reason)


def _part_verdict(condition: bool, refute: bool = False) -> str:
    if refute:
        return "反証"
    if condition:
        return "支持"
    return "正式objectだけでは未確定"


def _baseline_arrival_comparison(a_arrival, b_arrival) -> str:
    if type(a_arrival) is not int or type(b_arrival) is not int:
        return "comparison_unavailable"
    if a_arrival < b_arrival:
        return "A_earlier_than_B"
    if a_arrival > b_arrival:
        return "A_later_than_B"
    return "A_equal_B"


def _hypothesis_parts() -> dict:
    c392 = GATE.captures[TIMESTEP_T392]
    c401 = GATE.captures[TIMESTEP_T401]
    a392 = c392["target_info"]["A"]
    b392 = c392["target_info"]["B"]
    a401 = c401["target_info"]["A"]
    b401 = c401["target_info"]["B"]

    if a392["in_physical_order"] is True:
        part_a = "支持"
    else:
        part_a = "正式objectだけでは未確定"

    behind_scope = False
    narrow_observable = a392["in_physical_order"] is True
    if not narrow_observable:
        part_b = "正式objectだけでは未確定"
    elif a392["selected_trade_scope_ahead_count"] == "not_in_physical_order":
        part_b = "正式objectだけでは未確定"
    else:
        behind_scope = a392["behind_any_t392_selected_trade_scope_visit"] is True
        part_b = _part_verdict(behind_scope)

    if a392["in_candidate_visits"] is True:
        part_c = "反証"
        candidate_outside_formal = False
    elif a392["p_minus_one_eligible"] is True:
        part_c = "反証"
        candidate_outside_formal = False
    else:
        reason = a392["p_minus_one_ineligible_reason"]
        if reason in FORMAL_CANDIDATE_OUTSIDE_INELIGIBLE_REASONS:
            candidate_outside_formal = True
            part_c = "支持"
        else:
            candidate_outside_formal = False
            part_c = "正式objectだけでは未確定"

    part_d = _part_verdict(a401["is_right_of_entry"] is True, refute=a401["is_right_of_entry"] is False)
    part_e = _part_verdict(
        a401["post_assigned_c_rank"] == 184,
        refute=a401["post_assigned_c_rank"] is not None and a401["post_assigned_c_rank"] != 184,
    )

    comp392 = _baseline_arrival_comparison(
        a392["baseline_arrival_timestep"], b392["baseline_arrival_timestep"]
    )
    comp401 = _baseline_arrival_comparison(
        a401["baseline_arrival_timestep"], b401["baseline_arrival_timestep"]
    )

    broad_supported = (
        candidate_outside_formal
        and a392["in_candidate_visits"] is False
        and a401["is_right_of_entry"] is True
        and VISIT_A in c401["pre_undetermined_visit_keys"]
        and VISIT_A not in c401["pre_confirmed_ranks_by_visit_key"]
        and a401["post_assigned_c_rank"] == 184
        and b401["post_assigned_c_rank"] is None
    )
    scope_supported = narrow_observable and behind_scope

    refuted = (
        a392["in_candidate_visits"] is True
        or a392["p_minus_one_eligible"] is True
        or a401["is_right_of_entry"] is False
        or a401["post_assigned_c_rank"] != 184
        or b401["post_assigned_c_rank"] is not None
    )
    if refuted:
        overall = "反証"
    elif broad_supported and scope_supported:
        overall = "支持"
    elif broad_supported:
        overall = "部分支持"
    elif scope_supported:
        overall = "部分支持"
    else:
        overall = "正式objectだけでは未確定"

    return {
        "part_a": part_a,
        "part_b": part_b,
        "part_c": part_c,
        "part_c_reason": _p_minus_one_reason_label(
            a392["p_minus_one_ineligible_reason"] or REASON_P_MINUS_ONE_ELIGIBLE
        ),
        "part_d": part_d,
        "part_e": part_e,
        "part_f_t392": comp392,
        "part_f_t401": comp401,
        "overall": overall,
        "scope_ahead_visits": a392["selected_trade_scope_visits_ahead"],
        "scope_ahead_count": a392["selected_trade_scope_ahead_count"],
    }


def _classify_hypothesis() -> str:
    return _hypothesis_parts()["overall"]


def _build_review() -> str:
    c392 = GATE.captures[TIMESTEP_T392]
    c401 = GATE.captures[TIMESTEP_T401]
    parts = _hypothesis_parts()
    a392 = c392["target_info"]["A"]
    a401 = c401["target_info"]["A"]
    b401 = c401["target_info"]["B"]
    narrow_observable = a392["in_physical_order"] is True
    lines = [
        "T=392/T=401 C184 physical order diagnostic",
        f"Visit A: {_visit_text(VISIT_A)}",
        f"Visit B: {_visit_text(VISIT_B)}",
        "",
        "Observations T=392",
        f"  A in snapshot physical order: {a392['in_physical_order']}",
        f"  A in collector export: {a392['in_collector_export']}",
        f"  A formal inlink: {a392['formal_inlink_name']}",
        f"  A physical index: {a392['physical_index']}",
        f"  A Candidate outside reason: {a392['p_minus_one_ineligible_reason'] or REASON_P_MINUS_ONE_ELIGIBLE}",
        f"  A physical ahead visits observable: {narrow_observable}",
        f"  A behind selected trade-scope visit(s) decidable: "
        f"{narrow_observable and a392['selected_trade_scope_ahead_count'] != 'not_in_physical_order'}",
        "",
        "Observations T=401",
        f"  A formal inlink: {a401['formal_inlink_name']}",
        f"  A physical index: {a401['physical_index']}",
        f"  A ahead visit keys: {_visit_keys_pipe(a401['ahead_visit_keys'])}",
        f"  A baseline arrival: {a401['baseline_arrival_timestep']}",
        f"  A baseline passage: {a401['baseline_passage_timestep']}",
        f"  A right-of-entry: {a401['is_right_of_entry']}",
        f"  A C184 (post-driver): {a401['post_assigned_c_rank']}",
        f"  B baseline arrival: {b401['baseline_arrival_timestep']}",
        f"  B C rank undetermined at T=401 (post-driver): {b401['post_assigned_c_rank'] is None}",
        "",
        "Hypothesis parts",
        f"  A. T=392 A in snapshot physical order: {parts['part_a']}",
        f"  B. T=392 A behind selected trade-scope visit(s): {parts['part_b']}",
        f"     selected_trade_scope_visits_ahead: "
        f"{_visit_keys_pipe(parts['scope_ahead_visits']) if parts['scope_ahead_count'] != 'not_in_physical_order' else 'not_in_physical_order'}",
        f"     selected_trade_scope_ahead_count: {parts['scope_ahead_count']}",
    ]
    reason_raw = a392["p_minus_one_ineligible_reason"] or ""
    if parts["part_c"] == "反証":
        lines.append(
            f"  C. T=392 A outside Candidate direct reason: {parts['part_c']} ({parts['part_c_reason']})"
        )
    elif reason_raw in FORMAL_CANDIDATE_OUTSIDE_INELIGIBLE_REASONS:
        lines.append(
            f"  C. T=392 A outside Candidate direct reason: {parts['part_c']} ({parts['part_c_reason']})"
        )
    else:
        lines.append(f"  C. T=392 A outside Candidate direct reason: {parts['part_c']}")
        lines.append("     Candidate外理由: 正式objectだけでは未確定")
        lines.append(f"     reason: {reason_raw if reason_raw != '' else '(empty)'}")
    lines.extend(
        [
        f"  D. T=401 A right-of-entry: {parts['part_d']}",
        f"  E. T=401 A received C184: {parts['part_e']}",
        f"  F. Baseline arrival A vs B at T=392: {parts['part_f_t392']}",
        f"  F. Baseline arrival A vs B at T=401: {parts['part_f_t401']}",
        "",
        ]
    )
    lines.extend(
        [
        "T=392",
        f"  A in candidate_visits: {a392['in_candidate_visits']}",
        f"  A P-1 reason: {a392['p_minus_one_ineligible_reason'] or REASON_P_MINUS_ONE_ELIGIBLE}",
        f"  candidate_visits (formal order): {_visit_keys_pipe(c392['candidate_visit_keys'])}",
        "",
        "T=401",
        f"  candidate_visits (formal order): {_visit_keys_pipe(c401['candidate_visit_keys'])}",
        f"  right-of-entry: {_visit_text(c401['roe_key']) if c401['roe_key'] else ''}",
        f"  A post assigned C rank: {c401['target_info']['A']['post_assigned_c_rank']}",
        f"  B post assigned C rank: {c401['target_info']['B']['post_assigned_c_rank']}",
        "  final rank visits (formal order):",
        ]
    )
    for final_visit in c401["final_rank_visits"]:
        plain = _plain_visit_key(final_visit.visit_key)
        lines.append(
            f"    local_rank={final_visit.final_local_rank} {_visit_text(plain)} "
            f"source={final_visit.finalization_source.value}"
        )
    lines.append("")
    lines.append("Conclusions (no T=392 inlink or physical-order inference)")
    lines.append(
        "  1. Same-inlink behind selected trade-scope at T=392: "
        f"{parts['part_b']} (requires T=392 snapshot physical order for A)"
    )
    if a392["in_collector_export"] is False:
        lines.append(
            "  2. T=392 fact: A was not in snapshot fixed visit set (collector export)."
        )
    else:
        lines.append("  2. T=392 fact: A was in snapshot fixed visit set (collector export).")
    lines.append(
        "  3. T=401 fact: A appears in formal snapshot, was right-of-entry, received C184 after driver."
    )
    lines.append(
        f"  4. Temporal/state gap vs B at T=401: A C184={a401['post_assigned_c_rank']}, "
        f"B C rank={b401['post_assigned_c_rank']}, "
        f"baseline arrival comparison={parts['part_f_t401']}"
    )
    lines.append("")
    lines.append(f"Overall hypothesis verdict: {parts['overall']}")
    return "\n".join(lines) + "\n"


def wrapped_driver(world):
    pre_rank_snapshot = None
    if world is GATE.real_world:
        if getattr(world, "_order_control_baseline_collector", None) is None:
            if world.T in CAPTURE_TIMESTEPS:
                pre_rank_snapshot = _rank_membership_snapshot(world)
    result = GATE.original_driver(world)
    if world is not GATE.real_world:
        return result
    if getattr(world, "_order_control_baseline_collector", None) is not None:
        return result
    if world.T not in CAPTURE_TIMESTEPS:
        return result
    if pre_rank_snapshot is None:
        raise RuntimeError(f"T={world.T} pre-driver rank snapshot is missing.")
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={world.T} driver result type is wrong.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(f"T={world.T} atomic_apply_set_result is None.")
    post_rank_snapshot = _rank_membership_snapshot(world)
    stages = _stages_from_atomic(atomic)
    GATE.captures[world.T] = _capture_decision(
        world, stages, pre_rank_snapshot, post_rank_snapshot
    )
    return result


def wrapped_arrival(vehicle, node):
    return GATE.original_arrival(vehicle, node)


def install_hooks(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Hooks already installed.")
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

    GATE.captures = {}
    GATE.comparison_rows = []
    GATE.inlink_rows = []
    original_limit = sys.getrecursionlimit()
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation(until_t=SIMULATION_UNTIL_TIMESTEP * world.DELTAT)
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        if world.T != EXPECTED_WORLD_T_AFTER_SIM:
            raise RuntimeError(f"World.T is {world.T}, expected {EXPECTED_WORLD_T_AFTER_SIM}.")
        if set(GATE.captures.keys()) != CAPTURE_TIMESTEPS:
            raise RuntimeError(f"Captured timesteps {sorted(GATE.captures.keys())!r} are wrong.")
        _validate_runtime()
        _build_output_tables()
        GATE.review_text = _build_review()
        _validate_csv_rows(COMPARISON_COLUMNS, GATE.comparison_rows, COMPARISON_CSV)
        _validate_csv_rows(INLINK_COLUMNS, GATE.inlink_rows, INLINK_ORDERS_CSV)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_csv(OUTPUT_DIR / COMPARISON_CSV, COMPARISON_COLUMNS, GATE.comparison_rows)
        _write_csv(OUTPUT_DIR / INLINK_ORDERS_CSV, INLINK_COLUMNS, GATE.inlink_rows)
        (OUTPUT_DIR / REVIEW_NAME).write_text(GATE.review_text, encoding="utf-8")
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


def _module_string_constants(tree) -> set[str]:
    values: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if isinstance(node.value, ast.Constant) and type(node.value.value) is str:
                values.add(node.value.value)
    return values


def _stages_reads_fork_physical_orders(tree) -> bool:
    stages = _function_node(tree, "_stages_from_atomic")
    if stages is None:
        return False
    for node in ast.walk(stages):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant) or key.value != "inlink_physical_orders":
                continue
            if isinstance(value, ast.Attribute) and value.attr == "inlink_physical_orders":
                if isinstance(value.value, ast.Name) and value.value.id == "fork_result":
                    return True
    for node in ast.walk(stages):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Constant) and key.value == "inlink_physical_orders":
                    if isinstance(value, ast.Attribute) and value.attr == "inlink_physical_orders":
                        return True
    return False


def _validate_physical_order_walker(tree) -> bool:
    fn = _function_node(tree, "_validate_physical_orders")
    if fn is None:
        return False
    for node in ast.walk(fn):
        if isinstance(node, ast.Attribute) and node.attr == "visit_keys_head_to_tail":
            return True
    return False


def _capture_decision_has_no_rank_state(tree) -> bool:
    capture_fn = _function_node(tree, "_capture_decision")
    if capture_fn is None:
        return False
    for node in ast.walk(capture_fn):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        for key in node.value.keys:
            if isinstance(key, ast.Constant) and key.value == "rank_state":
                return False
    return True


def _classify_p_minus_one_uses_pre_snapshot(tree) -> bool:
    fn = _function_node(tree, "_classify_p_minus_one")
    if fn is None:
        return False
    param_names = [arg.arg for arg in fn.args.args]
    if "pre_rank_snapshot" not in param_names:
        return False
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_p_minus_one_ordered_keys":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Name):
                    if node.args[1].id == "pre_rank_snapshot":
                        return True
    return False


def _wrapped_driver_passes_snapshots(tree) -> bool:
    driver_fn = _function_node(tree, "wrapped_driver")
    if driver_fn is None:
        return False
    for node in ast.walk(driver_fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "_capture_decision":
            continue
        if len(node.args) >= 4:
            return True
    return False


def validate_static_contract() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    if TIMESTEP_T392 != 392 or TIMESTEP_T401 != 401:
        raise RuntimeError("Capture timesteps must be 392 and 401.")
    if SIMULATION_UNTIL_TIMESTEP != 401 or EXPECTED_WORLD_T_AFTER_SIM != 402:
        raise RuntimeError("Simulation end must be T=401 with World.T=402.")
    if CAPTURE_TIMESTEPS != frozenset({392, 401}):
        raise RuntimeError("CAPTURE_TIMESTEPS must be {392, 401}.")
    module_strings = _module_string_constants(tree)
    for file_name in (COMPARISON_CSV, INLINK_ORDERS_CSV, REVIEW_NAME):
        if file_name not in module_strings:
            raise RuntimeError(f"Missing output file name constant {file_name!r}.")
    output_names_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "OUTPUT_FILE_NAMES":
                    output_names_node = node.value
    if not isinstance(output_names_node, ast.Tuple) or len(output_names_node.elts) != 3:
        raise RuntimeError("OUTPUT_FILE_NAMES must be a 3-tuple.")
    if _stages_reads_fork_physical_orders(tree) is not True:
        raise RuntimeError("_stages_from_atomic must read fork_result.inlink_physical_orders.")
    if _validate_physical_order_walker(tree) is not True:
        raise RuntimeError("_validate_physical_orders must use visit_keys_head_to_tail.")
    if _function_node(tree, "_rank_membership_snapshot") is None:
        raise RuntimeError("Pre/post rank membership snapshot helper is missing.")
    if _capture_decision_has_no_rank_state(tree) is not True:
        raise RuntimeError("_capture_decision must not store mutable rank_state.")
    if _classify_p_minus_one_uses_pre_snapshot(tree) is not True:
        raise RuntimeError("_classify_p_minus_one must use pre_rank_snapshot.")
    if _wrapped_driver_passes_snapshots(tree) is not True:
        raise RuntimeError("wrapped_driver must pass pre/post snapshots to _capture_decision.")
    driver = _function_node(tree, "wrapped_driver")
    if driver is None or _call_count(driver, "GATE", "original_driver") != 1:
        raise RuntimeError("wrapped_driver must call original_driver once.")
    main_node = _function_node(tree, "main")
    mkdir_line = None
    sim_until = False
    for node in ast.walk(main_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "mkdir":
                mkdir_line = node.lineno
            if node.func.attr == "exec_simulation":
                for keyword in node.keywords:
                    if keyword.arg == "until_t":
                        sim_until = True
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
    if sim_until is not True:
        raise RuntimeError("main must call exec_simulation with until_t.")
    static_node = _function_node(tree, "validate_static_contract")
    for node in ast.walk(static_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "mkdir", "install_hooks", "restore_hooks"):
                raise RuntimeError("Static validation must not run simulation or hooks.")
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
