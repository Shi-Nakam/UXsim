"""
診断用: 最新の初期小規模 trial と同じ条件で TVT-MP を再実行し、
各 timestep の driver 戻り値から候補形成・評価・選択をファイルへ残す。

本番コードと trial script は変更しない。trial module の main() は呼ばない。
研究用 CSV は生成しない。

順位は次を分けて記録する。

- candidate Visit 集合内の baseline local order（candidate_visits の保存順）
- candidate Visit 集合内の trade local order
- trade scope 内の local rank change
- Node 全体の baseline 予測通過順
- Node 全体の actual 通過順
- snapshot 時点の同一 inlink 内物理順

baseline Node passage order は、診断側が Node の1台移動 method を一時的に包み、
TVT順位適用 baseline fork で移動が成功した順を観測する。
actual Node passage order は、simulation 終了後の実 World の正式 registry から読む。
最新 trial の transactions / visits CSV と照合する。
旧診断出力 directory は上書きしない。
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

import uxsim.order_control_tvt_mp_driver as driver_module
import uxsim.uxsim as uxsim_module

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_tvt_mp_small_scale_initial as initial_trial


DIAGNOSTIC_NAME = "tvt_mp_small_scale_initial_decision_trace"
REFERENCE_SCENARIO_NAME = (
    "tvt_mp_small_scale_initial_baseline_arrival_order_run"
)
REFERENCE_TRIAL_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / "tvt_mp_small_scale_initial_seed_1_baseline_arrival_order"
)
DIAGNOSTIC_OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / "tvt_mp_small_scale_initial_seed_1_baseline_arrival_order_decision_trace"
)
BASELINE_PASSAGE_CAPTURE_METHOD = (
    "diagnostic_wrapper_of_node_transfer_one_vehicle_success_order"
    "_on_tvt_rank_applying_baseline_fork"
)
ARRIVAL_SOURCE_COLLECTOR_SNAPSHOT = "collector_snapshot"
ARRIVAL_SOURCE_CURRENT_VISIT_OUTSIDE_SNAPSHOT = (
    "current_visit_outside_snapshot_set"
)

DECISION_SUMMARY_NAME = "decision_summary.csv"
CANDIDATE_SUMMARY_NAME = "candidate_summary.csv"
SELECTED_RESULT_SUMMARY_NAME = "selected_result_summary.csv"
DECISION_TRACE_NAME = "decision_trace.json"

OUTPUT_FILE_NAMES = (
    DECISION_SUMMARY_NAME,
    CANDIDATE_SUMMARY_NAME,
    SELECTED_RESULT_SUMMARY_NAME,
    DECISION_TRACE_NAME,
)

# 後段に存在しない値を、空欄と誤解されないように明示する。
NOT_APPLICABLE = "not_applicable"

REASON_NO_FEASIBLE = "no_economically_feasible_candidate"
REASON_UNIQUE_SURPLUS = "unique_maximum_surplus"
REASON_UNIQUE_BUYER_COUNT = "maximum_surplus_then_unique_maximum_buyer_count"
REASON_FINAL_RNG = "final_tie_resolved_by_local_rng"

OUTCOME_FIFO_VIOLATION = "fifo_violation"
OUTCOME_UNRESOLVED = "local_virtual_calculation_unresolved"
OUTCOME_INFEASIBLE = "economically_infeasible"
OUTCOME_LOWER_SURPLUS = "feasible_not_selected_lower_surplus"
OUTCOME_LOWER_BUYER_COUNT = "feasible_not_selected_lower_buyer_count"
OUTCOME_FINAL_RNG = "feasible_not_selected_final_rng"
OUTCOME_SELECTED = "selected"

SELECTION_STATUS_SELECTED = "selected"
SELECTION_STATUS_NO_FEASIBLE = "no_economically_feasible_candidate"

DECISION_SUMMARY_FIELDS = (
    "timestep",
    "node_name",
    "build_status",
    "right_of_entry_visit_key",
    "right_of_entry_baseline_passage_timestep",
    "candidate_visit_count",
    "concrete_buyer_candidate_count",
    "general_trade_rank_candidate_count",
    "fifo_true_count",
    "fifo_false_count",
    "resolved_count",
    "unresolved_count",
    "economic_evaluation_count",
    "economically_feasible_count",
    "selection_status",
    "selection_reason",
    "rng_was_used",
    "selected_candidate_identity",
    "selected_buyer_count",
    "selected_total_buyer_value_G",
    "selected_total_required_compensation_R",
    "selected_surplus",
    "buyer_payment_total",
    "seller_compensation_total",
    "final_rank_status",
    "final_rank_visit_count",
)

CANDIDATE_SUMMARY_FIELDS = (
    "timestep",
    "node_name",
    "candidate_identity",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "trade_scope",
    "trade_order",
    "fifo_preserved",
    "local_calculation_present",
    "resolved",
    "stop_reason",
    "unresolved_reasons",
    "buyer_passage_records",
    "seller_passage_records",
    "total_buyer_value_G",
    "total_required_compensation_R",
    "surplus",
    "economically_feasible",
    "infeasibility_reasons",
    "selected",
    "candidate_outcome_reason",
)

SELECTED_RESULT_FIELDS = (
    "timestep",
    "node_name",
    "selected_candidate_identity",
    "selection_reason",
    "record_type",
    "visit_key",
    "vehicle_name",
    "amount",
    "final_local_rank",
    "formal_route_next_link_name",
    "finalization_source",
)


def refuse_existing_diagnostic_directory() -> None:
    """既存の診断出力を消さず、同名 directory があるときは実行前に止める。"""
    if DIAGNOSTIC_OUTPUT_DIR.exists():
        raise RuntimeError(
            "Diagnostic output directory already exists: "
            f"{DIAGNOSTIC_OUTPUT_DIR}. This script does not delete, "
            "overwrite, or rename it."
        )


def visit_key_to_json(visit_key):
    """VisitKey を JSON に書ける辞書へ変換する。車両名と visit ID の両方を残す。"""
    if visit_key is None:
        return None
    vehicle_name, visit_id = visit_key
    return {
        "vehicle_name": vehicle_name,
        "visit_id": visit_id,
    }


def format_visit_key(visit_key) -> str:
    """CSV 用。例: veh_b2:1。object id では識別しない。"""
    if visit_key is None:
        return ""
    vehicle_name, visit_id = visit_key
    return f"{vehicle_name}:{visit_id}"


def format_visit_key_sequence(visit_keys) -> str:
    parts = []
    for visit_key in visit_keys:
        parts.append(format_visit_key(visit_key))
    return ";".join(parts)


def format_candidate_identity(node_name: str, buyers_sorted) -> str:
    """同じ Node 内では buyers_sorted が候補の正式な identity である。"""
    return node_name + "|" + format_visit_key_sequence(buyers_sorted)


def enum_value(value):
    if value is None:
        return None
    return value.value


def visit_keys_to_json(visit_keys):
    converted = []
    for visit_key in visit_keys:
        converted.append(visit_key_to_json(visit_key))
    return converted


def csv_cell(value) -> str:
    """欠損は空文字。bool は true/false。数値は丸めない。"""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def require_same_node_name(
    *,
    timestep: int,
    node_index: int,
    expected_node_name: str,
    actual_node_name: str,
    stage_name: str,
) -> None:
    if actual_node_name != expected_node_name:
        raise RuntimeError(
            f"T={timestep} node index {node_index}: {stage_name} node_name "
            f"{actual_node_name!r} does not match candidate Visit set node "
            f"{expected_node_name!r}. This diagnostic script does not "
            "realign Nodes."
        )


def require_same_length(
    *,
    timestep: int,
    node_name: str,
    left_name: str,
    left_length: int,
    right_name: str,
    right_length: int,
) -> None:
    if left_length != right_length:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: {left_name} length "
            f"{left_length} does not match {right_name} length {right_length}."
        )


def read_driver_stage_chain(result, timestep: int):
    """
    driver 戻り値から各段階の set result を、正式 field 名で順に取り出す。

    戻り値オブジェクト自体は呼び出し側の局所変数にだけ置き、リストへ保存しない。
    """
    atomic_apply_set_result = result.atomic_apply_set_result
    if atomic_apply_set_result is None:
        raise RuntimeError(
            f"T={timestep}: atomic_apply_set_result is None. "
            "This diagnostic expects every decision timestep to have "
            "TVT-MP target Nodes."
        )

    validation_set = (
        atomic_apply_set_result.final_consistency_validation_set_result
    )
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
    right_of_entry_selection_result = (
        candidate_visit_set.right_of_entry_selection_result
    )
    leading_confirmation_result = (
        right_of_entry_selection_result.leading_confirmation_result
    )
    arrived_confirmation_result = (
        leading_confirmation_result.arrived_confirmation_result
    )
    alignment_fork_result = arrived_confirmation_result.alignment_fork_result
    fork_result = alignment_fork_result.fork_result

    return {
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "concrete_nodes": (
            concrete_set.node_concrete_buyer_candidate_set_results
        ),
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "fifo_nodes": fifo_set.node_fifo_inspection_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "payment_nodes": payment_set.node_payment_and_compensation_results,
        "final_rank_nodes": final_rank_set.node_final_rank_results,
        "fork_result": fork_result,
        "baseline_collector": fork_result.collector,
        "baseline_timestep_T": fork_result.baseline_timestep_T,
        "configured_horizon_steps": fork_result.configured_horizon_steps,
        "inlink_physical_orders": fork_result.inlink_physical_orders,
        "target_node_names": tuple(fork_result.target_node_names),
    }


# Baseline fork には候補局所仮想計算のような timestep 別の clearance 停止履歴は保存されない。
# ここでは collector が持つ到着・通過・snapshot 物理順だけを記録し、存在しない詳細は捏造しない。


def copy_exported_baseline_visit_record(exported: dict) -> dict:
    """collector.export_node_baseline_visits の1行を、診断用 dict へ明示コピーする。"""
    vehicle_name = exported["vehicle_name"]
    visit_id = exported["visit_id"]
    return {
        "vehicle_name": vehicle_name,
        "vehicle_id": exported["vehicle_id"],
        "node_name": exported["node_name"],
        "inlink_name": exported["inlink_name"],
        "visit_id": visit_id,
        "visit_key": visit_key_to_json((vehicle_name, visit_id)),
        "was_arrived_at_snapshot": exported["was_arrived_at_snapshot"],
        "baseline_arrival_timestep": exported["baseline_arrival_timestep"],
        "arrival_tiebreaker": exported["arrival_tiebreaker"],
        "route_next_link_name": exported["route_next_link_name"],
        "baseline_passage_timestep": exported["baseline_passage_timestep"],
    }


def baseline_arrival_information_is_complete(record: dict) -> bool:
    if record["baseline_arrival_timestep"] is None:
        return False
    if record["arrival_tiebreaker"] is None:
        return False
    return True


def visit_key_tuple_from_json_dict(visit_key_dict: dict) -> tuple[str, int]:
    return (visit_key_dict["vehicle_name"], visit_key_dict["visit_id"])


def convert_snapshot_inlink_physical_orders_for_node(
    *,
    timestep: int,
    node_name: str,
    inlink_physical_orders,
) -> list[dict]:
    """
    snapshot 時点の同一 inlink 内物理順。index 0 が Node に最も近い物理先頭である。

    これは Node 全体の baseline 順位ではない。candidate local order でもない。
    baseline passage order でもない。
    """
    converted = []
    for physical_order in inlink_physical_orders:
        if physical_order.node_name != node_name:
            continue
        seen_visit_keys = set()
        visit_keys_head_to_tail = []
        for visit_key in physical_order.visit_keys_head_to_tail:
            if visit_key in seen_visit_keys:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r} inlink "
                    f"{physical_order.inlink_name!r}: duplicate VisitKey "
                    f"{visit_key!r} in snapshot physical order."
                )
            seen_visit_keys.add(visit_key)
            visit_keys_head_to_tail.append(visit_key_to_json(visit_key))
        converted.append(
            {
                "node_name": physical_order.node_name,
                "inlink_name": physical_order.inlink_name,
                "visit_keys_head_to_tail": visit_keys_head_to_tail,
            }
        )
    return converted


def build_baseline_node_bundle(
    *,
    timestep: int,
    node_name: str,
    baseline_collector,
    baseline_timestep_T: int,
    configured_horizon_steps: int,
    target_node_names: tuple[str, ...],
    inlink_physical_orders,
) -> dict:
    # export は snapshot 固定集合だけを返す。集合外 Visit はここには出ない。
    exported_rows = baseline_collector.export_node_baseline_visits(node_name)
    visit_records = []
    seen_visit_keys = set()
    for exported in exported_rows:
        copied = copy_exported_baseline_visit_record(exported)
        visit_key_tuple = visit_key_tuple_from_json_dict(copied["visit_key"])
        if visit_key_tuple in seen_visit_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: duplicate baseline VisitKey "
                f"{visit_key_tuple!r}."
            )
        seen_visit_keys.add(visit_key_tuple)
        visit_records.append(copied)

    unresolved_records = []
    for record in visit_records:
        if not baseline_arrival_information_is_complete(record):
            unresolved_records.append(record)

    snapshot_orders = convert_snapshot_inlink_physical_orders_for_node(
        timestep=timestep,
        node_name=node_name,
        inlink_physical_orders=inlink_physical_orders,
    )
    for snapshot_order in snapshot_orders:
        if snapshot_order["node_name"] != node_name:
            raise RuntimeError(
                f"T={timestep}: snapshot physical order node "
                f"{snapshot_order['node_name']!r} does not match target "
                f"{node_name!r}."
            )

    return {
        "baseline_fork_summary": {
            "baseline_timestep_T": baseline_timestep_T,
            "configured_horizon_steps": configured_horizon_steps,
            "target_node_names": list(target_node_names),
        },
        "baseline_visit_records": visit_records,
        "baseline_unresolved_visits": unresolved_records,
        "snapshot_inlink_physical_orders": snapshot_orders,
    }


def rank_change_direction(
    *,
    baseline_local_rank: int,
    candidate_trade_local_rank: int,
) -> str:
    """同じ candidate Visit 集合の中での local rank 変化。"""
    if candidate_trade_local_rank < baseline_local_rank:
        return "moved_earlier"
    if candidate_trade_local_rank == baseline_local_rank:
        return "unchanged"
    return "moved_later"


def build_candidate_baseline_local_order(
    *,
    timestep: int,
    node_name: str,
    candidate_visit_node,
) -> tuple[list[dict], dict]:
    """
    candidate_visits の保存順が、候補集合内の正式な baseline local order である。

    再ソートしない。戻り値の dict は内部照合用であり、JSON へは出さない。
    """
    rows = []
    local_rank_by_visit_key = {}
    seen_visit_keys = set()
    local_rank = 1
    for candidate_visit in candidate_visit_node.candidate_visits:
        row = convert_candidate_visit(candidate_visit)
        visit_key = visit_key_tuple_from_json_dict(row["visit_key"])
        if visit_key in seen_visit_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: duplicate VisitKey "
                f"{visit_key!r} in candidate_visits."
            )
        seen_visit_keys.add(visit_key)
        row["candidate_baseline_local_rank"] = local_rank
        local_rank_by_visit_key[visit_key] = local_rank
        rows.append(row)
        local_rank = local_rank + 1
    return rows, local_rank_by_visit_key


def enrich_trade_rank_details_with_local_comparison(
    *,
    timestep: int,
    node_name: str,
    trade_rank_details: list[dict],
    trade_rank_node,
    candidate_baseline_local_rank_by_visit_key: dict,
) -> None:
    """
    同じ candidate Visit 集合の baseline local rank と trade local rank を比べる。

    Node 全体の到着順や通過順とは比べない。rank_changes は trade scope だけ。
    """
    trade_results = trade_rank_node.candidate_trade_rank_results
    if len(trade_results) != len(trade_rank_details):
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: trade rank result count does "
            "not match trade rank detail count."
        )
    candidate_visit_keys = set(candidate_baseline_local_rank_by_visit_key)

    for index, trade_result in enumerate(trade_results):
        trade_detail = trade_rank_details[index]
        trade_scope = trade_result.trade_scope
        trade_rank_visit_keys = set()
        for visit_key, _rank_value in trade_result.trade_rank_items():
            if visit_key in trade_rank_visit_keys:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: duplicate VisitKey "
                    f"{visit_key!r} in trade rank items."
                )
            trade_rank_visit_keys.add(visit_key)
        if trade_rank_visit_keys != candidate_visit_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: trade rank VisitKey set "
                "does not match candidate_visits."
            )

        trade_scope_baseline_local_order = []
        for visit_key in trade_scope:
            if visit_key not in candidate_baseline_local_rank_by_visit_key:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: trade scope Visit "
                    f"{visit_key!r} is not in candidate_visits."
                )
            baseline_local_rank = candidate_baseline_local_rank_by_visit_key[
                visit_key
            ]
            trade_scope_baseline_local_order.append(
                {
                    "visit_key": visit_key_to_json(visit_key),
                    "candidate_baseline_local_rank": baseline_local_rank,
                }
            )
        trade_scope_baseline_local_order = sorted(
            trade_scope_baseline_local_order,
            key=lambda item: item["candidate_baseline_local_rank"],
        )

        trade_scope_candidate_rows = []
        for visit_key in trade_scope:
            candidate_trade_local_rank = trade_result.assigned_rank(visit_key)
            trade_scope_candidate_rows.append(
                {
                    "visit_key": visit_key_to_json(visit_key),
                    "candidate_trade_local_rank": candidate_trade_local_rank,
                }
            )
        trade_scope_candidate_order = sorted(
            trade_scope_candidate_rows,
            key=lambda item: item["candidate_trade_local_rank"],
        )

        rank_changes = []
        for visit_key in trade_scope:
            baseline_local_rank = candidate_baseline_local_rank_by_visit_key[
                visit_key
            ]
            candidate_trade_local_rank = trade_result.assigned_rank(visit_key)
            direction = rank_change_direction(
                baseline_local_rank=baseline_local_rank,
                candidate_trade_local_rank=candidate_trade_local_rank,
            )
            rank_changes.append(
                {
                    "visit_key": visit_key_to_json(visit_key),
                    "candidate_baseline_local_rank": baseline_local_rank,
                    "candidate_trade_local_rank": candidate_trade_local_rank,
                    "rank_change_direction": direction,
                }
            )

        trade_detail["trade_scope_baseline_local_order"] = (
            trade_scope_baseline_local_order
        )
        trade_detail["trade_scope_candidate_order"] = trade_scope_candidate_order
        trade_detail["rank_changes"] = rank_changes


def convert_candidate_visit(candidate_visit) -> dict:
    return {
        "visit_key": visit_key_to_json(candidate_visit.visit_key),
        "vehicle_id": candidate_visit.vehicle_id,
        "inlink_name": candidate_visit.inlink_name,
        "baseline_arrival_timestep": candidate_visit.baseline_arrival_timestep,
        "arrival_tiebreaker": candidate_visit.arrival_tiebreaker,
        "route_next_link_name": candidate_visit.route_next_link_name,
        "baseline_passage_timestep": candidate_visit.baseline_passage_timestep,
    }


def convert_buyer_prefix(prefix_result) -> dict:
    prefixes = []
    for prefix in prefix_result.buyer_prefixes_empty_to_max:
        prefixes.append(visit_keys_to_json(prefix))
    return {
        "node_name": prefix_result.node_name,
        "inlink_name": prefix_result.inlink_name,
        "buyer_prefixes_empty_to_max": prefixes,
    }


def convert_passage_record(passage_record) -> dict:
    return {
        "visit_key": visit_key_to_json(passage_record.visit_key),
        "vehicle_name": passage_record.vehicle_name,
        "trade_role": enum_value(passage_record.trade_role),
        "binding_partition": enum_value(passage_record.binding_partition),
        "binding_rank": passage_record.binding_rank,
        "baseline_passage_timestep": passage_record.baseline_passage_timestep,
        "candidate_passage_timestep": passage_record.candidate_passage_timestep,
        "route_next_link_name": passage_record.route_next_link_name,
        "route_origin": enum_value(passage_record.route_origin),
        "inlink_name": passage_record.inlink_name,
    }


def format_passage_records_for_csv(passage_records, trade_role_value: str) -> str:
    """buyer または seller の予測通過だけを、役割が分かる文字列にする。"""
    parts = []
    for record in passage_records:
        if record["trade_role"] != trade_role_value:
            continue
        visit_text = (
            record["visit_key"]["vehicle_name"]
            + ":"
            + str(record["visit_key"]["visit_id"])
        )
        baseline = record["baseline_passage_timestep"]
        candidate = record["candidate_passage_timestep"]
        parts.append(
            f"{visit_text} baseline={baseline} candidate={candidate}"
        )
    if len(parts) == 0:
        return NOT_APPLICABLE
    return " | ".join(parts)


def convert_clearance_stop(stop_context) -> dict | None:
    if stop_context is None:
        return None
    return {
        "virtual_timestep": stop_context.virtual_timestep,
        "offset": stop_context.offset,
        "stopped_binding_visit_key": visit_key_to_json(
            stop_context.stopped_binding_visit_key
        ),
    }


def convert_traffic_observation(observation) -> dict:
    return {
        "visit_key": visit_key_to_json(observation.visit_key),
        "vehicle_name": observation.vehicle_name,
        "vehicle_id": observation.vehicle_id,
        "trade_role": enum_value(observation.trade_role),
        "binding_partition": enum_value(observation.binding_partition),
        "binding_rank": observation.binding_rank,
        "trade_scope_rank": observation.trade_scope_rank,
        "inlink_name": observation.inlink_name,
        "route_next_link_name": observation.route_next_link_name,
        "true_vot_per_second": observation.true_vot_per_second,
        "baseline_passage_timestep": observation.baseline_passage_timestep,
        "candidate_passage_timestep": observation.candidate_passage_timestep,
        "passage_observation_status": enum_value(
            observation.passage_observation_status
        ),
        "observed_offset": observation.observed_offset,
        "observed_virtual_timestep": observation.observed_virtual_timestep,
        "predicted_time_difference_timesteps": (
            observation.predicted_time_difference_timesteps
        ),
        "predicted_time_difference_seconds": (
            observation.predicted_time_difference_seconds
        ),
        "predicted_signed_time_value_change": (
            observation.predicted_signed_time_value_change
        ),
        "last_checked_offset": observation.last_checked_offset,
        "last_checked_virtual_timestep": (
            observation.last_checked_virtual_timestep
        ),
        "last_temporary_skip_reason": enum_value(
            observation.last_temporary_skip_reason
        ),
        "last_temporary_skip_offset": observation.last_temporary_skip_offset,
        "latest_clearance_stop_context": convert_clearance_stop(
            observation.latest_clearance_stop_context
        ),
        "horizon_exhausted": observation.horizon_exhausted,
        "observation_complete": observation.observation_complete,
    }


def convert_binding_transfer_scan(scan_result) -> dict:
    skipped = []
    for skip in scan_result.temporarily_skipped_visits:
        skipped.append(
            {
                "binding_visit_key": visit_key_to_json(skip.binding_visit_key),
                "vehicle_name": skip.vehicle_name,
                "skip_reason": enum_value(skip.skip_reason),
            }
        )
    return {
        "node_name": scan_result.node_name,
        "virtual_timestep": scan_result.virtual_timestep,
        "transferred_binding_visit_keys": visit_keys_to_json(
            scan_result.transferred_binding_visit_keys
        ),
        "temporarily_skipped_visits": skipped,
        "stop_reason": enum_value(scan_result.stop_reason),
        "stopped_binding_visit_key": visit_key_to_json(
            scan_result.stopped_binding_visit_key
        ),
    }


def convert_unbound_transfer(transfer_result) -> dict:
    transferred = []
    for record in transfer_result.transferred_vehicle_records:
        transferred.append(
            {
                "vehicle_name": record.vehicle_name,
                "inlink_name": record.inlink_name,
                "outlink_name": record.outlink_name,
                "route_classification": enum_value(record.route_classification),
                "virtual_timestep": record.virtual_timestep,
                "selection_index": record.selection_index,
                "acceptable_outlink_names": list(record.acceptable_outlink_names),
            }
        )
    skips = []
    for skip in transfer_result.temporary_skips:
        skips.append(
            {
                "vehicle_name": skip.vehicle_name,
                "skip_reason": enum_value(skip.skip_reason),
            }
        )
    return {
        "node_name": transfer_result.node_name,
        "virtual_timestep": transfer_result.virtual_timestep,
        "stop_reason": enum_value(transfer_result.stop_reason),
        "transferred_vehicle_records": transferred,
        "temporary_skips": skips,
        "stopped_vehicle_name": transfer_result.stopped_vehicle_name,
        "candidate_vehicle_names_in_fcfs_order": list(
            transfer_result.candidate_vehicle_names_in_fcfs_order
        ),
    }


def convert_local_vehicle_advance(advance_result) -> dict:
    return {
        "node_name": advance_result.node_name,
        "virtual_timestep": advance_result.virtual_timestep,
        "advanced_vehicle_names": list(advance_result.advanced_vehicle_names),
        "preexisting_incoming_vehicle_names": list(
            advance_result.preexisting_incoming_vehicle_names
        ),
        "newly_arrived_vehicle_names": list(
            advance_result.newly_arrived_vehicle_names
        ),
        "newly_arrived_binding_visit_keys": visit_keys_to_json(
            advance_result.newly_arrived_binding_visit_keys
        ),
        "incoming_vehicle_names_before": list(
            advance_result.incoming_vehicle_names_before
        ),
        "incoming_vehicle_names_after": list(
            advance_result.incoming_vehicle_names_after
        ),
    }


def convert_outlink_boundary(boundary_result) -> dict:
    outlink_results = []
    for outlink_result in boundary_result.outlink_results:
        outlink_results.append(
            {
                "outlink_name": outlink_result.outlink_name,
                "terminal_node_name": outlink_result.terminal_node_name,
                "boundary_mode": enum_value(outlink_result.boundary_mode),
                "flow_allowance_before": outlink_result.flow_allowance_before,
                "flow_allowance_added": outlink_result.flow_allowance_added,
                "flow_allowance_after": outlink_result.flow_allowance_after,
                "vehicle_names_at_end_before": list(
                    outlink_result.vehicle_names_at_end_before
                ),
                "observed_outflow_boundary_exit_vehicle_names": list(
                    outlink_result.observed_outflow_boundary_exit_vehicle_names
                ),
                "constrained_sink_end_trip_vehicle_names": list(
                    outlink_result.constrained_sink_end_trip_vehicle_names
                ),
                "waiting_vehicle_names_after": list(
                    outlink_result.waiting_vehicle_names_after
                ),
                "capacity_out_remain_before": (
                    outlink_result.capacity_out_remain_before
                ),
                "capacity_out_remain_after": (
                    outlink_result.capacity_out_remain_after
                ),
                "terminal_node_flow_capacity_remain_before": (
                    outlink_result.terminal_node_flow_capacity_remain_before
                ),
                "terminal_node_flow_capacity_remain_after": (
                    outlink_result.terminal_node_flow_capacity_remain_after
                ),
            }
        )
    return {
        "node_name": boundary_result.node_name,
        "virtual_timestep": boundary_result.virtual_timestep,
        "outlink_results": outlink_results,
    }


def convert_virtual_timestep(timestep_result) -> dict:
    """候補 local の1仮想時刻。live World は含めず、凍結記録だけを写す。"""
    newly_recorded = visit_keys_to_json(
        timestep_result.newly_recorded_required_passage_visit_keys
    )
    return {
        "node_name": timestep_result.node_name,
        "virtual_timestep": timestep_result.virtual_timestep,
        "offset": timestep_result.offset,
        "binding_transfer_result": convert_binding_transfer_scan(
            timestep_result.binding_transfer_result
        ),
        "unbound_fcfs_result": convert_unbound_transfer(
            timestep_result.unbound_fcfs_result
        ),
        "newly_recorded_required_passage_visit_keys": newly_recorded,
        "local_vehicle_advance_result": convert_local_vehicle_advance(
            timestep_result.local_vehicle_advance_result
        ),
        "outlink_boundary_result": convert_outlink_boundary(
            timestep_result.outlink_boundary_result
        ),
        "required_passages_complete_after_node_passage": (
            timestep_result.required_passages_complete_after_node_passage
        ),
        "calculation_finished_after_timestep_end": (
            timestep_result.calculation_finished_after_timestep_end
        ),
        "resolved_after_timestep_end": timestep_result.resolved_after_timestep_end,
        "traffic_observation_complete_after_node_passage": (
            timestep_result.traffic_observation_complete_after_node_passage
        ),
        "economic_required_first_completed_at_this_timestep": (
            timestep_result.economic_required_first_completed_at_this_timestep
        ),
        "traffic_observation_first_completed_at_this_timestep": (
            timestep_result.traffic_observation_first_completed_at_this_timestep
        ),
    }


def convert_local_virtual_calculation(local_result) -> dict:
    passage_records = []
    for passage_record in local_result.required_passage_records:
        passage_records.append(convert_passage_record(passage_record))

    unresolved_reasons = []
    for reason in local_result.unresolved_reasons:
        unresolved_reasons.append(enum_value(reason))

    observations = []
    for observation in local_result.traffic_observation_records:
        observations.append(convert_traffic_observation(observation))

    timestep_results = []
    for timestep_result in local_result.timestep_results:
        timestep_results.append(convert_virtual_timestep(timestep_result))

    return {
        "resolved": local_result.resolved,
        "stop_reason": enum_value(local_result.stop_reason),
        "unresolved_reasons": unresolved_reasons,
        "required_passage_records": passage_records,
        "traffic_observation_records": observations,
        "economic_required_passages_complete_offset": (
            local_result.economic_required_passages_complete_offset
        ),
        "economic_required_passages_complete_virtual_timestep": (
            local_result.economic_required_passages_complete_virtual_timestep
        ),
        "all_trade_scope_passages_complete_offset": (
            local_result.all_trade_scope_passages_complete_offset
        ),
        "all_trade_scope_passages_complete_virtual_timestep": (
            local_result.all_trade_scope_passages_complete_virtual_timestep
        ),
        "timestep_results": timestep_results,
    }


def convert_buyer_economic_record(record) -> dict:
    return {
        "visit_key": visit_key_to_json(record.visit_key),
        "vehicle_name": record.vehicle_name,
        "declared_vot_per_second": record.declared_vot_per_second,
        "baseline_passage_timestep": record.baseline_passage_timestep,
        "candidate_passage_timestep": record.candidate_passage_timestep,
        "expected_time_saving_timesteps": record.expected_time_saving_timesteps,
        "expected_time_saving_seconds": record.expected_time_saving_seconds,
        "gross_time_value_G_b": record.gross_time_value_G_b,
        "passes_positive_buyer_value_condition": (
            record.passes_positive_buyer_value_condition
        ),
    }


def convert_seller_economic_record(record) -> dict:
    return {
        "visit_key": visit_key_to_json(record.visit_key),
        "vehicle_name": record.vehicle_name,
        "declared_vot_per_second": record.declared_vot_per_second,
        "baseline_passage_timestep": record.baseline_passage_timestep,
        "candidate_passage_timestep": record.candidate_passage_timestep,
        "raw_passage_difference_timesteps": (
            record.raw_passage_difference_timesteps
        ),
        "expected_waiting_increase_timesteps": (
            record.expected_waiting_increase_timesteps
        ),
        "raw_passage_difference_seconds": record.raw_passage_difference_seconds,
        "expected_waiting_increase_seconds": (
            record.expected_waiting_increase_seconds
        ),
        "required_compensation_R_s": record.required_compensation_R_s,
    }


def convert_economic_evaluation(economic_result) -> dict:
    buyer_records = []
    for record in economic_result.buyer_economic_records:
        buyer_records.append(convert_buyer_economic_record(record))
    seller_records = []
    for record in economic_result.seller_economic_records:
        seller_records.append(convert_seller_economic_record(record))
    infeasibility_reasons = []
    for reason in economic_result.infeasibility_reasons:
        infeasibility_reasons.append(enum_value(reason))
    return {
        "buyer_economic_records": buyer_records,
        "seller_economic_records": seller_records,
        "total_buyer_value_G": economic_result.total_buyer_value_G,
        "total_required_compensation_R": (
            economic_result.total_required_compensation_R
        ),
        "surplus": economic_result.surplus,
        "economically_feasible": economic_result.economically_feasible,
        "infeasibility_reasons": infeasibility_reasons,
    }


def join_reason_values(reason_values) -> str:
    if len(reason_values) == 0:
        return ""
    return ";".join(reason_values)


def derive_selection_reason(
    *,
    timestep: int,
    node_name: str,
    selection_status: str,
    rng_was_used: bool,
    selected_buyers,
    candidate_rows: list[dict],
) -> str:
    """
    選択理由は本番 result に文章で保存されていない。

    診断側は、保存済みの surplus・buyer 数・rng_was_used だけから分類する。
    local RNG は再実行しない。比較は本番と同じ完全一致で、tolerance は使わない。
    """
    # 候補形成前（right-of-entry なし等）や concrete buyer 候補が1件もない timestep は、
    # 本番の surplus・buyer 数による選択規則の対象外である。ここを経済的不成立と混同しない。
    if len(candidate_rows) == 0:
        if selection_status != SELECTION_STATUS_NO_FEASIBLE:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: no concrete buyer candidate "
                "rows, but selection_status is "
                f"{selection_status!r}."
            )
        if selected_buyers is not None:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: no concrete buyer candidate "
                "rows, but a selected candidate is present."
            )
        if rng_was_used is not False:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: no concrete buyer candidate "
                "rows, but rng_was_used is not False."
            )
        return ""

    feasible_rows = []
    for row in candidate_rows:
        if row["economically_feasible"] is True:
            feasible_rows.append(row)

    # concrete buyer 候補が経済評価まで進み、成立候補が0件のときだけ no_economically_feasible_candidate。
    if len(feasible_rows) == 0:
        if selection_status != SELECTION_STATUS_NO_FEASIBLE:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: no economically feasible "
                "candidate, but selection_status is "
                f"{selection_status!r}."
            )
        if selected_buyers is not None:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: no economically feasible "
                "candidate, but a selected candidate is present."
            )
        if rng_was_used is not False:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: no economically feasible "
                "candidate, but rng_was_used is not False."
            )
        return REASON_NO_FEASIBLE

    if selection_status != SELECTION_STATUS_SELECTED:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: economically feasible "
            f"candidates exist, but selection_status is {selection_status!r}."
        )
    if selected_buyers is None:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: selection_status is selected, "
            "but selected buyers are missing."
        )

    maximum_surplus = feasible_rows[0]["surplus"]
    for row in feasible_rows:
        if row["surplus"] > maximum_surplus:
            maximum_surplus = row["surplus"]

    maximum_surplus_rows = []
    for row in feasible_rows:
        if row["surplus"] == maximum_surplus:
            maximum_surplus_rows.append(row)

    if len(maximum_surplus_rows) == 1:
        if rng_was_used is not False:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: unique maximum surplus, "
                "but rng_was_used is not False."
            )
        winner = maximum_surplus_rows[0]
        if winner["buyers_sorted_value"] != selected_buyers:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: selected candidate "
                f"{format_candidate_identity(node_name, selected_buyers)!r} "
                "is not the unique maximum-surplus candidate "
                f"{winner['candidate_identity']!r}."
            )
        return REASON_UNIQUE_SURPLUS

    maximum_buyer_count = maximum_surplus_rows[0]["buyer_count"]
    for row in maximum_surplus_rows:
        if row["buyer_count"] > maximum_buyer_count:
            maximum_buyer_count = row["buyer_count"]

    maximum_buyer_rows = []
    for row in maximum_surplus_rows:
        if row["buyer_count"] == maximum_buyer_count:
            maximum_buyer_rows.append(row)

    if len(maximum_buyer_rows) == 1:
        if rng_was_used is not False:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: unique maximum buyer "
                "count after surplus, but rng_was_used is not False."
            )
        winner = maximum_buyer_rows[0]
        if winner["buyers_sorted_value"] != selected_buyers:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: selected candidate "
                f"{format_candidate_identity(node_name, selected_buyers)!r} "
                "is not the unique maximum-buyer-count candidate "
                f"{winner['candidate_identity']!r}."
            )
        return REASON_UNIQUE_BUYER_COUNT

    if rng_was_used is not True:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: final tie remains, but "
            "rng_was_used is not True."
        )

    selected_is_in_tie = False
    for row in maximum_buyer_rows:
        if row["buyers_sorted_value"] == selected_buyers:
            selected_is_in_tie = True
    if selected_is_in_tie is not True:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: selected candidate "
            f"{format_candidate_identity(node_name, selected_buyers)!r} "
            "is not in the final tied candidate set."
        )
    return REASON_FINAL_RNG


def assign_candidate_outcome_reasons(
    *,
    timestep: int,
    node_name: str,
    candidate_rows: list[dict],
    selection_reason: str,
    selected_buyers,
) -> None:
    """候補がどの段階で残ったか、落ちたかを outcome reason に分ける。"""
    feasible_rows = []
    for row in candidate_rows:
        if row["economically_feasible"] is True:
            feasible_rows.append(row)

    maximum_surplus = None
    maximum_buyer_count_at_surplus = None
    if len(feasible_rows) > 0:
        maximum_surplus = feasible_rows[0]["surplus"]
        for row in feasible_rows:
            if row["surplus"] > maximum_surplus:
                maximum_surplus = row["surplus"]
        maximum_surplus_rows = []
        for row in feasible_rows:
            if row["surplus"] == maximum_surplus:
                maximum_surplus_rows.append(row)
        maximum_buyer_count_at_surplus = maximum_surplus_rows[0]["buyer_count"]
        for row in maximum_surplus_rows:
            if row["buyer_count"] > maximum_buyer_count_at_surplus:
                maximum_buyer_count_at_surplus = row["buyer_count"]

    for row in candidate_rows:
        identity = row["candidate_identity"]
        if row["fifo_preserved"] is False:
            row["candidate_outcome_reason"] = OUTCOME_FIFO_VIOLATION
            row["selected"] = False
            continue
        if row["resolved"] is not True:
            row["candidate_outcome_reason"] = OUTCOME_UNRESOLVED
            row["selected"] = False
            continue
        if row["economically_feasible"] is not True:
            row["candidate_outcome_reason"] = OUTCOME_INFEASIBLE
            row["selected"] = False
            continue

        is_selected = row["buyers_sorted_value"] == selected_buyers
        row["selected"] = is_selected
        if is_selected:
            row["candidate_outcome_reason"] = OUTCOME_SELECTED
            continue

        if row["surplus"] != maximum_surplus and row["surplus"] < maximum_surplus:
            row["candidate_outcome_reason"] = OUTCOME_LOWER_SURPLUS
            continue
        if row["surplus"] == maximum_surplus:
            if row["buyer_count"] < maximum_buyer_count_at_surplus:
                row["candidate_outcome_reason"] = OUTCOME_LOWER_BUYER_COUNT
                continue
            if (
                row["buyer_count"] == maximum_buyer_count_at_surplus
                and selection_reason == REASON_FINAL_RNG
            ):
                row["candidate_outcome_reason"] = OUTCOME_FINAL_RNG
                continue

        raise RuntimeError(
            f"T={timestep} node {node_name!r}: candidate {identity!r} "
            "is economically feasible but its non-selection reason could "
            f"not be classified. selection_reason={selection_reason!r}."
        )


def build_candidate_rows_for_node(
    *,
    timestep: int,
    node_name: str,
    concrete_node,
    trade_rank_node,
    fifo_node,
    local_node,
    economic_node,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    concrete buyer 候補を起点に、後段 result を同じ順・同じ buyers_sorted で結ぶ。

    FIFO False は local 仮想計算へ進まない。後段に無いことを経済的不成立とは扱わない。
    """
    concrete_sets = concrete_node.concrete_buyer_candidate_sets
    trade_results = trade_rank_node.candidate_trade_rank_results
    fifo_results = fifo_node.candidate_fifo_inspection_results
    local_results = local_node.candidate_local_virtual_calculation_results
    economic_results = economic_node.candidate_economic_evaluation_results

    require_same_length(
        timestep=timestep,
        node_name=node_name,
        left_name="concrete_buyer_candidate_sets",
        left_length=len(concrete_sets),
        right_name="candidate_trade_rank_results",
        right_length=len(trade_results),
    )
    require_same_length(
        timestep=timestep,
        node_name=node_name,
        left_name="candidate_trade_rank_results",
        left_length=len(trade_results),
        right_name="candidate_fifo_inspection_results",
        right_length=len(fifo_results),
    )

    candidate_rows = []
    trade_rank_details = []
    fifo_details = []
    expected_local_buyers = []

    for index, concrete_set in enumerate(concrete_sets):
        trade_result = trade_results[index]
        fifo_result = fifo_results[index]
        buyers_sorted = concrete_set.buyers_sorted
        identity = format_candidate_identity(node_name, buyers_sorted)

        if trade_result.buyers_sorted != buyers_sorted:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: trade-rank candidate "
                f"index {index} buyers do not match concrete buyer set "
                f"{identity!r}."
            )
        if fifo_result.general_trade_rank_result is not trade_result:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: FIFO result index {index} "
                f"does not reference trade-rank candidate {identity!r}."
            )
        if fifo_result.preserves_inlink_fifo is True:
            expected_local_buyers.append(buyers_sorted)
        elif fifo_result.preserves_inlink_fifo is not False:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: FIFO result for "
                f"{identity!r} is not a strict bool."
            )

        trade_rank_items = []
        for visit_key, rank_value in trade_result.trade_rank_items():
            trade_rank_items.append(
                {
                    "visit_key": visit_key_to_json(visit_key),
                    "trade_rank": rank_value,
                }
            )
        trade_detail = {
            "candidate_identity": identity,
            "buyers_sorted": visit_keys_to_json(trade_result.buyers_sorted),
            "sellers_sorted": visit_keys_to_json(trade_result.sellers_sorted),
            "nonparticipating_visits_sorted": visit_keys_to_json(
                trade_result.nonparticipating_visits_sorted
            ),
            "last_buyer_rank": trade_result.last_buyer_rank,
            "trade_scope": visit_keys_to_json(trade_result.trade_scope),
            "trade_order": visit_keys_to_json(trade_result.trade_order),
            "trade_rank_items": trade_rank_items,
        }
        trade_rank_details.append(trade_detail)
        fifo_details.append(
            {
                "candidate_identity": identity,
                "preserves_inlink_fifo": fifo_result.preserves_inlink_fifo,
            }
        )

        row = {
            "timestep": timestep,
            "node_name": node_name,
            "candidate_identity": identity,
            "buyers_sorted_value": buyers_sorted,
            "buyer_count": len(buyers_sorted),
            "buyers_sorted": format_visit_key_sequence(trade_result.buyers_sorted),
            "sellers_sorted": format_visit_key_sequence(
                trade_result.sellers_sorted
            ),
            "nonparticipating_visits_sorted": format_visit_key_sequence(
                trade_result.nonparticipating_visits_sorted
            ),
            "trade_scope": format_visit_key_sequence(trade_result.trade_scope),
            "trade_order": format_visit_key_sequence(trade_result.trade_order),
            "fifo_preserved": fifo_result.preserves_inlink_fifo,
            "local_calculation_present": False,
            "resolved": NOT_APPLICABLE,
            "stop_reason": NOT_APPLICABLE,
            "unresolved_reasons": NOT_APPLICABLE,
            "buyer_passage_records": NOT_APPLICABLE,
            "seller_passage_records": NOT_APPLICABLE,
            "required_passage_records": [],
            "total_buyer_value_G": NOT_APPLICABLE,
            "total_required_compensation_R": NOT_APPLICABLE,
            "surplus": NOT_APPLICABLE,
            "economically_feasible": NOT_APPLICABLE,
            "infeasibility_reasons": NOT_APPLICABLE,
            "selected": False,
            "candidate_outcome_reason": "",
            "local_detail": None,
            "economic_detail": None,
        }
        candidate_rows.append(row)

    require_same_length(
        timestep=timestep,
        node_name=node_name,
        left_name="FIFO True candidates",
        left_length=len(expected_local_buyers),
        right_name="local virtual calculation results",
        right_length=len(local_results),
    )

    local_by_index_for_economic = []
    for index, local_result in enumerate(local_results):
        actual_buyers = local_result.concrete_buyer_candidate_set.buyers_sorted
        expected_buyers = expected_local_buyers[index]
        identity = format_candidate_identity(node_name, expected_buyers)
        if actual_buyers != expected_buyers:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: local virtual calculation "
                f"index {index} does not match FIFO True candidate {identity!r}."
            )
        if local_result.node_name != node_name:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: local virtual calculation "
                f"for {identity!r} has node_name {local_result.node_name!r}."
            )

        matched_row = None
        for row in candidate_rows:
            if row["buyers_sorted_value"] == actual_buyers:
                matched_row = row
                break
        if matched_row is None:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: local virtual calculation "
                f"{identity!r} has no concrete buyer row."
            )
        if matched_row["fifo_preserved"] is not True:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: FIFO False candidate "
                f"{identity!r} has a local virtual calculation."
            )

        local_detail = convert_local_virtual_calculation(local_result)
        local_detail["candidate_identity"] = identity
        matched_row["local_calculation_present"] = True
        matched_row["resolved"] = local_result.resolved
        matched_row["stop_reason"] = local_detail["stop_reason"]
        matched_row["unresolved_reasons"] = join_reason_values(
            local_detail["unresolved_reasons"]
        )
        if matched_row["unresolved_reasons"] == "":
            matched_row["unresolved_reasons"] = ""
        matched_row["required_passage_records"] = local_detail[
            "required_passage_records"
        ]
        matched_row["buyer_passage_records"] = format_passage_records_for_csv(
            local_detail["required_passage_records"],
            "buyer",
        )
        matched_row["seller_passage_records"] = format_passage_records_for_csv(
            local_detail["required_passage_records"],
            "seller",
        )
        matched_row["local_detail"] = local_detail
        if local_result.resolved is True:
            local_by_index_for_economic.append(local_result)

    require_same_length(
        timestep=timestep,
        node_name=node_name,
        left_name="resolved local virtual calculations",
        left_length=len(local_by_index_for_economic),
        right_name="economic evaluation results",
        right_length=len(economic_results),
    )

    for index, economic_result in enumerate(economic_results):
        expected_local = local_by_index_for_economic[index]
        actual_local = economic_result.candidate_local_virtual_calculation_result
        buyers_sorted = actual_local.concrete_buyer_candidate_set.buyers_sorted
        identity = format_candidate_identity(node_name, buyers_sorted)
        if actual_local is not expected_local:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: economic evaluation index "
                f"{index} does not reference resolved local calculation "
                f"{identity!r}."
            )
        matched_row = None
        for row in candidate_rows:
            if row["buyers_sorted_value"] == buyers_sorted:
                matched_row = row
                break
        if matched_row is None or matched_row["resolved"] is not True:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: economic evaluation "
                f"{identity!r} is not a resolved FIFO True candidate."
            )
        economic_detail = convert_economic_evaluation(economic_result)
        economic_detail["candidate_identity"] = identity
        matched_row["economic_detail"] = economic_detail
        matched_row["total_buyer_value_G"] = economic_detail["total_buyer_value_G"]
        matched_row["total_required_compensation_R"] = economic_detail[
            "total_required_compensation_R"
        ]
        matched_row["surplus"] = economic_detail["surplus"]
        matched_row["economically_feasible"] = economic_detail[
            "economically_feasible"
        ]
        matched_row["infeasibility_reasons"] = join_reason_values(
            economic_detail["infeasibility_reasons"]
        )

    return candidate_rows, trade_rank_details, fifo_details


def convert_payment_records(payment_node) -> tuple[list[dict], list[dict], object, object]:
    buyer_records = []
    buyer_total = 0
    for record in payment_node.buyer_payment_records:
        buyer_records.append(
            {
                "visit_key": visit_key_to_json(record.visit_key),
                "vehicle_name": record.vehicle_name,
                "payment_P_b": record.payment_P_b,
            }
        )
        buyer_total = buyer_total + record.payment_P_b
    seller_records = []
    seller_total = 0
    for record in payment_node.seller_compensation_records:
        seller_records.append(
            {
                "visit_key": visit_key_to_json(record.visit_key),
                "vehicle_name": record.vehicle_name,
                "compensation_amount": record.compensation_amount,
            }
        )
        seller_total = seller_total + record.compensation_amount
    return buyer_records, seller_records, buyer_total, seller_total


def convert_final_rank_visits(final_rank_node) -> list[dict]:
    visits = []
    for visit in final_rank_node.final_rank_visits:
        vehicle_name, visit_id = visit.visit_key
        visits.append(
            {
                "visit_key": {
                    "vehicle_name": vehicle_name,
                    "visit_id": visit_id,
                },
                "vehicle_name": vehicle_name,
                "final_local_rank": visit.final_local_rank,
                "formal_route_next_link_name": visit.formal_route_next_link_name,
                "finalization_source": enum_value(visit.finalization_source),
                "route_origin": enum_value(visit.route_origin),
            }
        )
    return visits


def build_selected_result_rows(
    *,
    timestep: int,
    node_name: str,
    candidate_identity: str,
    selection_reason: str,
    buyer_payments: list[dict],
    seller_compensations: list[dict],
    final_rank_visits: list[dict],
) -> list[dict]:
    """選択後の支払・補償・確定順位。0円も行として残す。"""
    rows = []
    for payment in buyer_payments:
        visit_key = payment["visit_key"]
        rows.append(
            {
                "timestep": timestep,
                "node_name": node_name,
                "selected_candidate_identity": candidate_identity,
                "selection_reason": selection_reason,
                "record_type": "buyer_payment",
                "visit_key": (
                    visit_key["vehicle_name"] + ":" + str(visit_key["visit_id"])
                ),
                "vehicle_name": payment["vehicle_name"],
                "amount": payment["payment_P_b"],
                "final_local_rank": "",
                "formal_route_next_link_name": "",
                "finalization_source": "",
            }
        )
    for compensation in seller_compensations:
        visit_key = compensation["visit_key"]
        rows.append(
            {
                "timestep": timestep,
                "node_name": node_name,
                "selected_candidate_identity": candidate_identity,
                "selection_reason": selection_reason,
                "record_type": "seller_compensation",
                "visit_key": (
                    visit_key["vehicle_name"] + ":" + str(visit_key["visit_id"])
                ),
                "vehicle_name": compensation["vehicle_name"],
                "amount": compensation["compensation_amount"],
                "final_local_rank": "",
                "formal_route_next_link_name": "",
                "finalization_source": "",
            }
        )
    for visit in final_rank_visits:
        visit_key = visit["visit_key"]
        rows.append(
            {
                "timestep": timestep,
                "node_name": node_name,
                "selected_candidate_identity": candidate_identity,
                "selection_reason": selection_reason,
                "record_type": "final_rank",
                "visit_key": (
                    visit_key["vehicle_name"] + ":" + str(visit_key["visit_id"])
                ),
                "vehicle_name": visit["vehicle_name"],
                "amount": "",
                "final_local_rank": visit["final_local_rank"],
                "formal_route_next_link_name": visit["formal_route_next_link_name"],
                "finalization_source": visit["finalization_source"],
            }
        )
    return rows


def extract_one_node(
    *,
    timestep: int,
    node_index: int,
    candidate_visit_node,
    concrete_node,
    trade_rank_node,
    fifo_node,
    local_node,
    economic_node,
    selection_node,
    payment_node,
    final_rank_node,
    baseline_node_bundle: dict,
) -> dict:
    node_name = candidate_visit_node.node_name
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=concrete_node.node_name,
        stage_name="concrete buyer candidate set",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=trade_rank_node.node_name,
        stage_name="general trade rank",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=fifo_node.node_name,
        stage_name="FIFO inspection",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=local_node.node_name,
        stage_name="local virtual calculation",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=economic_node.node_name,
        stage_name="economic evaluation",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=selection_node.node_name,
        stage_name="candidate selection",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=payment_node.node_name,
        stage_name="payment and compensation",
    )
    require_same_node_name(
        timestep=timestep,
        node_index=node_index,
        expected_node_name=node_name,
        actual_node_name=final_rank_node.node_name,
        stage_name="final rank",
    )

    candidate_visits, candidate_baseline_local_rank_by_visit_key = (
        build_candidate_baseline_local_order(
            timestep=timestep,
            node_name=node_name,
            candidate_visit_node=candidate_visit_node,
        )
    )

    candidate_rows, trade_rank_details, fifo_details = (
        build_candidate_rows_for_node(
            timestep=timestep,
            node_name=node_name,
            concrete_node=concrete_node,
            trade_rank_node=trade_rank_node,
            fifo_node=fifo_node,
            local_node=local_node,
            economic_node=economic_node,
        )
    )

    if len(trade_rank_details) > 0:
        enrich_trade_rank_details_with_local_comparison(
            timestep=timestep,
            node_name=node_name,
            trade_rank_details=trade_rank_details,
            trade_rank_node=trade_rank_node,
            candidate_baseline_local_rank_by_visit_key=(
                candidate_baseline_local_rank_by_visit_key
            ),
        )

    selection_status = enum_value(selection_node.selection_status)
    rng_was_used = selection_node.rng_was_used
    selected_economic = selection_node.selected_candidate_economic_result
    selected_buyers = None
    selected_identity = ""
    selected_buyer_count = ""
    selected_g = ""
    selected_r = ""
    selected_surplus = ""
    if selected_economic is not None:
        selected_local = (
            selected_economic.candidate_local_virtual_calculation_result
        )
        selected_buyers = selected_local.concrete_buyer_candidate_set.buyers_sorted
        selected_identity = format_candidate_identity(node_name, selected_buyers)
        found_selected = False
        for row in candidate_rows:
            if row["buyers_sorted_value"] == selected_buyers:
                if row["economic_detail"] is None:
                    raise RuntimeError(
                        f"T={timestep} node {node_name!r}: selected candidate "
                        f"{selected_identity!r} has no economic evaluation."
                    )
                if row["total_buyer_value_G"] != selected_economic.total_buyer_value_G:
                    raise RuntimeError(
                        f"T={timestep} node {node_name!r}: selected candidate "
                        f"{selected_identity!r} total_buyer_value_G mismatch."
                    )
                if (
                    row["total_required_compensation_R"]
                    != selected_economic.total_required_compensation_R
                ):
                    raise RuntimeError(
                        f"T={timestep} node {node_name!r}: selected candidate "
                        f"{selected_identity!r} total_required_compensation_R "
                        "mismatch."
                    )
                if row["surplus"] != selected_economic.surplus:
                    raise RuntimeError(
                        f"T={timestep} node {node_name!r}: selected candidate "
                        f"{selected_identity!r} surplus mismatch."
                    )
                found_selected = True
        if found_selected is not True:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: selected candidate "
                f"{selected_identity!r} is not in this Node's economic results."
            )
        selected_buyer_count = len(selected_buyers)
        selected_g = selected_economic.total_buyer_value_G
        selected_r = selected_economic.total_required_compensation_R
        selected_surplus = selected_economic.surplus

    if payment_node.selected_candidate_economic_result is not selected_economic:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: payment result does not "
            "reference the same selected economic result."
        )
    if final_rank_node.selected_candidate_economic_result is not selected_economic:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: final rank result does not "
            "reference the same selected economic result."
        )

    selection_reason = derive_selection_reason(
        timestep=timestep,
        node_name=node_name,
        selection_status=selection_status,
        rng_was_used=rng_was_used,
        selected_buyers=selected_buyers,
        candidate_rows=candidate_rows,
    )
    assign_candidate_outcome_reasons(
        timestep=timestep,
        node_name=node_name,
        candidate_rows=candidate_rows,
        selection_reason=selection_reason,
        selected_buyers=selected_buyers,
    )

    buyer_payments, seller_compensations, buyer_total, seller_total = (
        convert_payment_records(payment_node)
    )
    final_rank_visits = convert_final_rank_visits(final_rank_node)
    if selection_status == SELECTION_STATUS_SELECTED:
        buyer_payment_total = buyer_total
        seller_compensation_total = seller_total
        if len(buyer_payments) != selected_buyer_count:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: buyer payment count "
                f"{len(buyer_payments)} does not match selected buyer count "
                f"{selected_buyer_count}."
            )
    else:
        if len(buyer_payments) != 0 or len(seller_compensations) != 0:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: payments exist without "
                "a selected candidate."
            )
        buyer_payment_total = ""
        seller_compensation_total = ""

    recomputed_buyer_total = 0
    for payment in buyer_payments:
        recomputed_buyer_total = recomputed_buyer_total + payment["payment_P_b"]
    recomputed_seller_total = 0
    for compensation in seller_compensations:
        recomputed_seller_total = (
            recomputed_seller_total + compensation["compensation_amount"]
        )
    if recomputed_buyer_total != buyer_total:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: buyer payment total does not "
            "match the sum of buyer payments."
        )
    if recomputed_seller_total != seller_total:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: seller compensation total does "
            "not match the sum of seller compensations."
        )

    fifo_true_count = 0
    fifo_false_count = 0
    resolved_count = 0
    unresolved_count = 0
    economic_evaluation_count = 0
    economically_feasible_count = 0
    for row in candidate_rows:
        if row["fifo_preserved"] is True:
            fifo_true_count = fifo_true_count + 1
        elif row["fifo_preserved"] is False:
            fifo_false_count = fifo_false_count + 1
        if row["resolved"] is True:
            resolved_count = resolved_count + 1
        elif row["resolved"] is False:
            unresolved_count = unresolved_count + 1
        if row["economic_detail"] is not None:
            economic_evaluation_count = economic_evaluation_count + 1
        if row["economically_feasible"] is True:
            economically_feasible_count = economically_feasible_count + 1

    concrete_buyer_candidates = []
    for concrete_set in concrete_node.concrete_buyer_candidate_sets:
        concrete_buyer_candidates.append(
            {
                "buyers_sorted": visit_keys_to_json(concrete_set.buyers_sorted),
                "candidate_identity": format_candidate_identity(
                    node_name,
                    concrete_set.buyers_sorted,
                ),
            }
        )
    buyer_prefixes = []
    for prefix_result in concrete_node.buyer_candidate_inlink_prefix_results:
        buyer_prefixes.append(convert_buyer_prefix(prefix_result))

    has_candidate_detail = (
        len(candidate_visits) > 0 or len(concrete_buyer_candidates) > 0
    )

    local_details = []
    economic_details = []
    if has_candidate_detail:
        for row in candidate_rows:
            if row["local_detail"] is not None:
                local_details.append(row["local_detail"])
            if row["economic_detail"] is not None:
                economic_details.append(row["economic_detail"])

    selected_rows = []
    if selection_status == SELECTION_STATUS_SELECTED:
        selected_rows = build_selected_result_rows(
            timestep=timestep,
            node_name=node_name,
            candidate_identity=selected_identity,
            selection_reason=selection_reason,
            buyer_payments=buyer_payments,
            seller_compensations=seller_compensations,
            final_rank_visits=final_rank_visits,
        )

    summary = {
        "timestep": timestep,
        "node_name": node_name,
        "build_status": enum_value(candidate_visit_node.build_status),
        "right_of_entry_visit_key": format_visit_key(
            candidate_visit_node.right_of_entry_visit_key
        ),
        "right_of_entry_baseline_passage_timestep": (
            candidate_visit_node.right_of_entry_baseline_passage_timestep
        ),
        "candidate_visit_count": len(candidate_visits),
        "concrete_buyer_candidate_count": len(concrete_buyer_candidates),
        "general_trade_rank_candidate_count": len(trade_rank_details),
        "fifo_true_count": fifo_true_count,
        "fifo_false_count": fifo_false_count,
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "economic_evaluation_count": economic_evaluation_count,
        "economically_feasible_count": economically_feasible_count,
        "selection_status": selection_status,
        "selection_reason": selection_reason,
        "rng_was_used": rng_was_used,
        "selected_candidate_identity": selected_identity,
        "selected_buyer_count": selected_buyer_count,
        "selected_total_buyer_value_G": selected_g,
        "selected_total_required_compensation_R": selected_r,
        "selected_surplus": selected_surplus,
        "buyer_payment_total": buyer_payment_total,
        "seller_compensation_total": seller_compensation_total,
        "final_rank_status": enum_value(final_rank_node.final_rank_status),
        "final_rank_visit_count": len(final_rank_visits),
    }

    detail = None
    if has_candidate_detail:
        detail = {
            "baseline_fork_summary": baseline_node_bundle["baseline_fork_summary"],
            "baseline_visit_records": baseline_node_bundle["baseline_visit_records"],
            "baseline_unresolved_visits": baseline_node_bundle[
                "baseline_unresolved_visits"
            ],
            "snapshot_inlink_physical_orders": baseline_node_bundle[
                "snapshot_inlink_physical_orders"
            ],
            "candidate_visits": candidate_visits,
            "concrete_buyer_candidates": concrete_buyer_candidates,
            "buyer_candidate_inlink_prefix_results": buyer_prefixes,
            "general_trade_rank_candidates": trade_rank_details,
            "fifo_results": fifo_details,
            "local_virtual_calculation_results": local_details,
            "economic_evaluation_results": economic_details,
            "selection_result": {
                "selection_status": selection_status,
                "selection_reason": selection_reason,
                "rng_was_used": rng_was_used,
                "selected_candidate_identity": selected_identity,
            },
            "payment_and_compensation_result": {
                "buyer_payment_records": buyer_payments,
                "seller_compensation_records": seller_compensations,
                "buyer_payment_total": buyer_total,
                "seller_compensation_total": seller_total,
            },
            "final_rank_result": {
                "final_rank_status": summary["final_rank_status"],
                "final_rank_visits": final_rank_visits,
            },
        }

    return {
        "summary": summary,
        "candidate_rows": candidate_rows,
        "selected_rows": selected_rows,
        "has_candidate_detail": has_candidate_detail,
        "detail": detail,
    }


def extract_plain_diagnostic_values(
    timestep: int,
    result,
    passage_rows_by_node_name: dict,
) -> list[dict]:
    """1回の driver 戻り値を、参照を残さない単純値へ変換する。"""
    stages = read_driver_stage_chain(result, timestep)
    stage_names = (
        "candidate_visit_nodes",
        "concrete_nodes",
        "trade_rank_nodes",
        "fifo_nodes",
        "local_nodes",
        "economic_nodes",
        "selection_nodes",
        "payment_nodes",
        "final_rank_nodes",
    )
    node_count = len(stages["candidate_visit_nodes"])
    for stage_name in stage_names:
        if len(stages[stage_name]) != node_count:
            raise RuntimeError(
                f"T={timestep}: stage {stage_name} has "
                f"{len(stages[stage_name])} Nodes, but candidate Visit set "
                f"has {node_count} Nodes."
            )

    target_node_names = stages["target_node_names"]
    if len(target_node_names) != node_count:
        raise RuntimeError(
            f"T={timestep}: fork target_node_names length "
            f"{len(target_node_names)} does not match Node result count "
            f"{node_count}."
        )

    decisions = []
    for node_index in range(node_count):
        node_name = stages["candidate_visit_nodes"][node_index].node_name
        if target_node_names[node_index] != node_name:
            raise RuntimeError(
                f"T={timestep} node index {node_index}: fork target node "
                f"{target_node_names[node_index]!r} does not match candidate "
                f"Visit set node {node_name!r}."
            )
        baseline_node_bundle = build_baseline_node_bundle(
            timestep=timestep,
            node_name=node_name,
            baseline_collector=stages["baseline_collector"],
            baseline_timestep_T=stages["baseline_timestep_T"],
            configured_horizon_steps=stages["configured_horizon_steps"],
            target_node_names=target_node_names,
            inlink_physical_orders=stages["inlink_physical_orders"],
        )
        decision = extract_one_node(
            timestep=timestep,
            node_index=node_index,
            candidate_visit_node=stages["candidate_visit_nodes"][node_index],
            concrete_node=stages["concrete_nodes"][node_index],
            trade_rank_node=stages["trade_rank_nodes"][node_index],
            fifo_node=stages["fifo_nodes"][node_index],
            local_node=stages["local_nodes"][node_index],
            economic_node=stages["economic_nodes"][node_index],
            selection_node=stages["selection_nodes"][node_index],
            payment_node=stages["payment_nodes"][node_index],
            final_rank_node=stages["final_rank_nodes"][node_index],
            baseline_node_bundle=baseline_node_bundle,
        )
        if decision["has_candidate_detail"]:
            node_name = decision["summary"]["node_name"]
            if node_name in passage_rows_by_node_name:
                passage_order = passage_rows_by_node_name[node_name]
            else:
                passage_order = []
            decision["detail"]["baseline_node_passage_order"] = passage_order
        decisions.append(decision)
    return decisions


def _is_tvt_rank_applying_baseline_target(node) -> bool:
    """TVT順位適用 baseline fork の対象 Node だけを観測する。"""
    collector = getattr(node.W, "_order_control_baseline_collector", None)
    if collector is None:
        return False
    if getattr(collector, "apply_copied_tvt_confirmed_ranks", None) is not True:
        return False
    if node.order_control_type != "time_value":
        return False
    if node.order_control_eligible is not True:
        return False
    return True


def _prepare_baseline_passage_facts(node, vehicle, inlink, outlink) -> dict:
    """移動前の単純値だけを控える。移動後は current Visit が替わり得る。"""
    current_visit = vehicle.order_control_current_visit
    visit_id = None
    arrival_time = None
    current_tiebreaker = None
    if isinstance(current_visit, dict):
        visit_id = current_visit.get("visit_id")
        arrival_time = current_visit.get("arrival_time")
        current_tiebreaker = current_visit.get("arrival_tiebreaker")

    collector = node.W._order_control_baseline_collector
    snapshot = None
    visit_id_is_usable = (
        type(visit_id) is int and visit_id >= 1
    )
    if visit_id_is_usable:
        snapshot = collector.get_baseline_visit_snapshot(vehicle.name, visit_id)

    snapshot_present = isinstance(snapshot, dict)
    snapshot_arrival_timestep = None
    snapshot_tiebreaker = None
    snapshot_vehicle_id = None
    if snapshot_present:
        snapshot_arrival_timestep = snapshot.get("baseline_arrival_timestep")
        snapshot_tiebreaker = snapshot.get("arrival_tiebreaker")
        snapshot_vehicle_id = snapshot.get("vehicle_id")

    inlink_name = None
    if inlink is not None:
        inlink_name = inlink.name
    outlink_name = None
    if outlink is not None:
        outlink_name = outlink.name

    return {
        "node_name": node.name,
        "vehicle_name": vehicle.name,
        "live_vehicle_id": vehicle.id,
        "visit_id": visit_id,
        "inlink_name": inlink_name,
        "outlink_name": outlink_name,
        "arrival_time": arrival_time,
        "current_visit_tiebreaker": current_tiebreaker,
        "snapshot_present": snapshot_present,
        "snapshot_arrival_timestep": snapshot_arrival_timestep,
        "snapshot_tiebreaker": snapshot_tiebreaker,
        "snapshot_vehicle_id": snapshot_vehicle_id,
        "passage_timestep": node.W.T,
        "deltat": node.W.DELTAT,
    }


def _baseline_passage_row_from_prepared(prepared: dict) -> dict:
    """成功した移動について、集合内外の材料を混ぜずに1行へする。"""
    node_name = prepared["node_name"]
    vehicle_name = prepared["vehicle_name"]
    visit_id = prepared["visit_id"]
    if type(visit_id) is not int or visit_id < 1:
        raise RuntimeError(
            f"Node {node_name}: baseline passage for vehicle {vehicle_name} "
            f"has no usable visit_id; got {visit_id!r}."
        )
    if prepared["snapshot_present"] is True:
        arrival_source = ARRIVAL_SOURCE_COLLECTOR_SNAPSHOT
        snapshot_fixed = True
        baseline_arrival_timestep = prepared["snapshot_arrival_timestep"]
        arrival_tiebreaker = prepared["snapshot_tiebreaker"]
        vehicle_id = prepared["snapshot_vehicle_id"]
        if vehicle_id != prepared["live_vehicle_id"]:
            raise RuntimeError(
                f"Node {node_name}: collector vehicle_id {vehicle_id!r} does "
                f"not match live vehicle {vehicle_name} id "
                f"{prepared['live_vehicle_id']!r}."
            )
    elif prepared["snapshot_present"] is False:
        arrival_source = ARRIVAL_SOURCE_CURRENT_VISIT_OUTSIDE_SNAPSHOT
        snapshot_fixed = False
        arrival_time = prepared["arrival_time"]
        arrival_tiebreaker = prepared["current_visit_tiebreaker"]
        deltat = prepared["deltat"]
        arrival_time_is_finite = (
            type(arrival_time) is not bool
            and isinstance(arrival_time, (int, float))
            and math.isfinite(arrival_time)
        )
        deltat_is_positive = (
            type(deltat) is not bool
            and isinstance(deltat, (int, float))
            and math.isfinite(deltat)
            and deltat > 0
        )
        if not arrival_time_is_finite or not deltat_is_positive:
            raise RuntimeError(
                f"Node {node_name}: outside-snapshot vehicle {vehicle_name} "
                "has no usable arrival_time or DELTAT for baseline passage "
                f"capture; arrival_time={arrival_time!r}, DELTAT={deltat!r}."
            )
        baseline_arrival_timestep = int(round(arrival_time / deltat))
        vehicle_id = prepared["live_vehicle_id"]
    else:
        raise RuntimeError(
            f"Node {node_name}: snapshot presence for {vehicle_name} is not "
            "a bool."
        )

    if (
        type(baseline_arrival_timestep) is not int
        or baseline_arrival_timestep < 0
    ):
        raise RuntimeError(
            f"Node {node_name}: baseline arrival timestep for {vehicle_name} "
            f"is not a non-negative int; got {baseline_arrival_timestep!r}."
        )
    tiebreaker_is_finite = (
        type(arrival_tiebreaker) is not bool
        and isinstance(arrival_tiebreaker, (int, float))
        and math.isfinite(arrival_tiebreaker)
    )
    if not tiebreaker_is_finite:
        raise RuntimeError(
            f"Node {node_name}: arrival tiebreaker for {vehicle_name} is not "
            f"a finite number; got {arrival_tiebreaker!r}."
        )
    if type(vehicle_id) is not int or vehicle_id < 0:
        raise RuntimeError(
            f"Node {node_name}: vehicle id for {vehicle_name} is not a "
            f"non-negative int; got {vehicle_id!r}."
        )
    if type(prepared["passage_timestep"]) is not int:
        raise RuntimeError(
            f"Node {node_name}: passage timestep for {vehicle_name} is not "
            f"an int; got {prepared['passage_timestep']!r}."
        )

    return {
        "node_name": node_name,
        "visit_key": visit_key_to_json((vehicle_name, visit_id)),
        "vehicle_name": vehicle_name,
        "vehicle_id": vehicle_id,
        "inlink_name": prepared["inlink_name"],
        "outlink_name": prepared["outlink_name"],
        "baseline_passage_timestep": prepared["passage_timestep"],
        "baseline_arrival_timestep": baseline_arrival_timestep,
        "arrival_tiebreaker": arrival_tiebreaker,
        "arrival_source": arrival_source,
        "snapshot_fixed": snapshot_fixed,
    }


def install_baseline_passage_observer(capture: DiagnosticCapture):
    """成功した1台移動だけを、TVT順位適用 baseline fork で控える。"""
    node_class = uxsim_module.Node
    original_transfer = node_class._transfer_one_vehicle_between_links

    def observed_transfer(node, vehicle, inlink, outlink):
        observe = _is_tvt_rank_applying_baseline_target(node)
        prepared = None
        if observe:
            if capture.driver_call_open is not True:
                raise RuntimeError(
                    f"Node {node.name}: baseline passage observed outside an "
                    "open diagnostic driver call."
                )
            prepared = _prepare_baseline_passage_facts(
                node,
                vehicle,
                inlink,
                outlink,
            )
        returned = original_transfer(node, vehicle, inlink, outlink)
        if observe:
            capture.record_successful_baseline_passage(prepared)
        return returned

    node_class._transfer_one_vehicle_between_links = observed_transfer
    return original_transfer


def restore_baseline_passage_observer(original_transfer) -> None:
    uxsim_module.Node._transfer_one_vehicle_between_links = original_transfer


class DiagnosticCapture:
    """wrapper が残すのは変換済みの単純値だけである。"""

    def __init__(self) -> None:
        self.call_count = 0
        self.decisions = []
        self.inside_driver_call = False
        self.driver_call_open = False
        self.decision_timestep = None
        self.passage_rows_by_node_name = {}

    def begin_driver_call(self, timestep: int) -> None:
        if self.inside_driver_call or self.driver_call_open:
            raise RuntimeError(
                f"T={timestep}: diagnostic wrapper re-entered. "
                "The original driver must be called once per wrapper call."
            )
        if len(self.passage_rows_by_node_name) != 0:
            raise RuntimeError(
                f"T={timestep}: baseline passage buffer is not empty at the "
                "start of a driver call."
            )
        self.inside_driver_call = True
        self.driver_call_open = True
        self.decision_timestep = timestep

    def discard_driver_call(self) -> None:
        self.passage_rows_by_node_name = {}
        self.driver_call_open = False
        self.inside_driver_call = False
        self.decision_timestep = None

    def complete_driver_call(self, result) -> None:
        timestep = self.decision_timestep
        passage_rows = self.passage_rows_by_node_name
        self.passage_rows_by_node_name = {}
        self.driver_call_open = False
        try:
            plain_decisions = extract_plain_diagnostic_values(
                timestep,
                result,
                passage_rows,
            )
        finally:
            self.inside_driver_call = False
            self.decision_timestep = None
        self.call_count = self.call_count + 1
        for decision in plain_decisions:
            self.decisions.append(decision)

    def record_successful_baseline_passage(self, prepared: dict) -> None:
        if self.driver_call_open is not True:
            raise RuntimeError(
                "Baseline passage was recorded outside an open driver call."
            )
        row = _baseline_passage_row_from_prepared(prepared)
        node_name = row["node_name"]
        if node_name not in self.passage_rows_by_node_name:
            self.passage_rows_by_node_name[node_name] = []
        node_rows = self.passage_rows_by_node_name[node_name]
        row["baseline_node_passage_rank"] = len(node_rows) + 1
        node_rows.append(row)


def install_driver_wrapper(capture: DiagnosticCapture):
    original_run_tvt_mp_driver = driver_module.run_tvt_mp_driver

    def diagnostic_run_tvt_mp_driver(real_W):
        # 意思決定時刻は、Link 更新前に driver が呼ばれた時点の World.T である。
        capture.begin_driver_call(real_W.T)
        try:
            result = original_run_tvt_mp_driver(real_W)
        except Exception:
            capture.discard_driver_call()
            raise
        try:
            capture.complete_driver_call(result)
        except Exception:
            capture.discard_driver_call()
            raise
        return result

    driver_module.run_tvt_mp_driver = diagnostic_run_tvt_mp_driver
    return original_run_tvt_mp_driver


def restore_driver(original_run_tvt_mp_driver) -> None:
    driver_module.run_tvt_mp_driver = original_run_tvt_mp_driver


def build_vehicle_json(vot_records) -> list[dict]:
    vehicles = []
    for record in vot_records:
        vehicles.append(
            {
                "vehicle_name": record.vehicle_name,
                "origin": record.origin,
                "destination": record.destination,
                "departure_timestep": record.departure_timestep,
                "participating": record.participates_in_order_exchange,
                "true_vot_per_second": record.true_vot_per_second,
                "declared_vot_per_second": record.declared_vot_per_second,
            }
        )
    return vehicles


def decision_json_record(decision: dict) -> dict:
    record = dict(decision["summary"])
    if decision["has_candidate_detail"]:
        record["baseline_fork_summary"] = decision["detail"]["baseline_fork_summary"]
        record["baseline_visit_records"] = decision["detail"]["baseline_visit_records"]
        record["baseline_unresolved_visits"] = decision["detail"][
            "baseline_unresolved_visits"
        ]
        record["snapshot_inlink_physical_orders"] = decision["detail"][
            "snapshot_inlink_physical_orders"
        ]
        record["baseline_node_passage_order"] = decision["detail"][
            "baseline_node_passage_order"
        ]
        record["candidate_visits"] = decision["detail"]["candidate_visits"]
        record["concrete_buyer_candidates"] = decision["detail"][
            "concrete_buyer_candidates"
        ]
        record["buyer_candidate_inlink_prefix_results"] = decision["detail"][
            "buyer_candidate_inlink_prefix_results"
        ]
        record["general_trade_rank_candidates"] = decision["detail"][
            "general_trade_rank_candidates"
        ]
        record["fifo_results"] = decision["detail"]["fifo_results"]
        record["local_virtual_calculation_results"] = decision["detail"][
            "local_virtual_calculation_results"
        ]
        record["economic_evaluation_results"] = decision["detail"][
            "economic_evaluation_results"
        ]
        record["selection_result"] = decision["detail"]["selection_result"]
        record["payment_and_compensation_result"] = decision["detail"][
            "payment_and_compensation_result"
        ]
        record["final_rank_result"] = decision["detail"]["final_rank_result"]
    return record


def write_csv(path: Path, fieldnames, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output_row = {}
            for field_name in fieldnames:
                output_row[field_name] = csv_cell(row[field_name])
            writer.writerow(output_row)


def write_diagnostic_files(
    vot_records,
    decisions: list[dict],
    actual_node_passage_orders: dict,
) -> None:
    DIAGNOSTIC_OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_OUTPUT_DIR.mkdir(exist_ok=False)

    summary_rows = []
    candidate_rows = []
    selected_rows = []
    decision_records = []
    for decision in decisions:
        summary_rows.append(decision["summary"])
        for row in decision["candidate_rows"]:
            candidate_rows.append(row)
        for row in decision["selected_rows"]:
            selected_rows.append(row)
        decision_records.append(decision_json_record(decision))

    write_csv(
        DIAGNOSTIC_OUTPUT_DIR / DECISION_SUMMARY_NAME,
        DECISION_SUMMARY_FIELDS,
        summary_rows,
    )
    write_csv(
        DIAGNOSTIC_OUTPUT_DIR / CANDIDATE_SUMMARY_NAME,
        CANDIDATE_SUMMARY_FIELDS,
        candidate_rows,
    )
    write_csv(
        DIAGNOSTIC_OUTPUT_DIR / SELECTED_RESULT_SUMMARY_NAME,
        SELECTED_RESULT_FIELDS,
        selected_rows,
    )

    document = {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "scenario_name": REFERENCE_SCENARIO_NAME,
        "reference_trial_directory": str(REFERENCE_TRIAL_DIR),
        "diagnostic_output_directory": str(DIAGNOSTIC_OUTPUT_DIR),
        "baseline_passage_capture_method": BASELINE_PASSAGE_CAPTURE_METHOD,
        "traffic_seed": initial_trial.TRAFFIC_SEED,
        "vot_seed": initial_trial.VOT_SEED,
        "evaluation_start_timestep": initial_trial.EVALUATION_START_TIMESTEP,
        "evaluation_end_timestep": initial_trial.EVALUATION_END_TIMESTEP,
        "internal_tsize": initial_trial.INTERNAL_TSIZE,
        "baseline_horizon_steps": initial_trial.BASELINE_HORIZON_STEPS,
        "max_candidate_visit_count": initial_trial.MAX_CANDIDATE_VISIT_COUNT,
        "vehicles": build_vehicle_json(vot_records),
        "actual_node_passage_orders": actual_node_passage_orders,
        "decisions": decision_records,
    }
    json_path = DIAGNOSTIC_OUTPUT_DIR / DECISION_TRACE_NAME
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def verify_baseline_fork_decision_detail(decision: dict) -> None:
    """候補内 local 順位と、観測した Node 通過順の整合を確認する。"""
    if not decision["has_candidate_detail"]:
        return
    detail = decision["detail"]
    summary = decision["summary"]
    timestep = summary["timestep"]
    node_name = summary["node_name"]

    required_keys = (
        "baseline_fork_summary",
        "baseline_visit_records",
        "baseline_unresolved_visits",
        "snapshot_inlink_physical_orders",
        "baseline_node_passage_order",
        "candidate_visits",
    )
    for key in required_keys:
        if key not in detail:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: missing baseline detail "
                f"field {key!r}."
            )
    forbidden_keys = (
        "baseline_official_order",
        "baseline_passage_order",
        "official_rank_by_visit_key",
    )
    for key in forbidden_keys:
        if key in detail:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: removed field {key!r} is "
                "still in the decision detail."
            )

    fork_summary = detail["baseline_fork_summary"]
    if fork_summary["baseline_timestep_T"] is None:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: baseline_timestep_T is missing."
        )
    if node_name not in fork_summary["target_node_names"]:
        raise RuntimeError(
            f"T={timestep} node {node_name!r}: node not in baseline fork "
            "target_node_names."
        )

    local_rank_by_visit_key = {}
    expected_rank = 1
    for row in detail["candidate_visits"]:
        visit_key_tuple = visit_key_tuple_from_json_dict(row["visit_key"])
        if visit_key_tuple in local_rank_by_visit_key:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: duplicate VisitKey in "
                "candidate_visits."
            )
        if row["candidate_baseline_local_rank"] != expected_rank:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: candidate baseline local "
                "ranks are not consecutive from 1 in stored order."
            )
        local_rank_by_visit_key[visit_key_tuple] = expected_rank
        expected_rank = expected_rank + 1

    collector_records_by_visit_key = {}
    for record in detail["baseline_visit_records"]:
        visit_key_tuple = visit_key_tuple_from_json_dict(record["visit_key"])
        collector_records_by_visit_key[visit_key_tuple] = record

    for snapshot_order in detail["snapshot_inlink_physical_orders"]:
        if snapshot_order["node_name"] != node_name:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: snapshot physical order "
                f"node {snapshot_order['node_name']!r} mismatch. This list is "
                "same-inlink snapshot order, not a Node passage order."
            )
        seen_snapshot_keys = set()
        for visit_key_dict in snapshot_order["visit_keys_head_to_tail"]:
            visit_key_tuple = visit_key_tuple_from_json_dict(visit_key_dict)
            if visit_key_tuple in seen_snapshot_keys:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r} inlink "
                    f"{snapshot_order['inlink_name']!r}: duplicate VisitKey in "
                    "snapshot_inlink_physical_orders."
                )
            seen_snapshot_keys.add(visit_key_tuple)

    _verify_trade_scope_local_comparison(
        timestep=timestep,
        node_name=node_name,
        detail=detail,
        local_rank_by_visit_key=local_rank_by_visit_key,
    )
    _verify_baseline_node_passage_order(
        timestep=timestep,
        node_name=node_name,
        detail=detail,
        collector_records_by_visit_key=collector_records_by_visit_key,
    )


def _verify_trade_scope_local_comparison(
    *,
    timestep: int,
    node_name: str,
    detail: dict,
    local_rank_by_visit_key: dict,
) -> None:
    candidate_visit_keys = set(local_rank_by_visit_key)
    for trade_detail in detail["general_trade_rank_candidates"]:
        if "trade_scope_baseline_official_order" in trade_detail:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: removed trade-scope "
                "official order is still present."
            )
        comparison_fields = (
            "trade_scope_baseline_local_order",
            "trade_scope_candidate_order",
            "rank_changes",
        )
        for field_name in comparison_fields:
            if field_name not in trade_detail:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r} candidate "
                    f"{trade_detail.get('candidate_identity')!r}: missing "
                    f"{field_name}."
                )

        trade_items = trade_detail["trade_rank_items"]
        trade_keys = set()
        seen_ranks = set()
        expected_trade_rank = 1
        for item in trade_items:
            visit_key_tuple = visit_key_tuple_from_json_dict(item["visit_key"])
            if visit_key_tuple in trade_keys:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: duplicate trade rank "
                    f"VisitKey {visit_key_tuple!r}."
                )
            trade_keys.add(visit_key_tuple)
            rank_value = item["trade_rank"]
            if rank_value in seen_ranks:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: duplicate trade rank "
                    f"{rank_value}."
                )
            seen_ranks.add(rank_value)
            if rank_value != expected_trade_rank:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: trade local ranks are "
                    "not consecutive from 1."
                )
            expected_trade_rank = expected_trade_rank + 1
        if trade_keys != candidate_visit_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: trade rank VisitKeys do "
                "not match candidate_visits."
            )

        scope_keys = set()
        for scope_row in trade_detail["trade_scope"]:
            scope_keys.add(visit_key_tuple_from_json_dict(scope_row))
        if not scope_keys.issubset(candidate_visit_keys):
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: trade_scope is not a "
                "subset of candidate_visits."
            )

        baseline_scope_keys = _scope_keys_in_order(
            trade_detail["trade_scope_baseline_local_order"]
        )
        candidate_scope_keys = _scope_keys_in_order(
            trade_detail["trade_scope_candidate_order"]
        )
        change_keys = _scope_keys_in_order(trade_detail["rank_changes"])
        if baseline_scope_keys != scope_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: "
                "trade_scope_baseline_local_order is not exactly trade_scope."
            )
        if candidate_scope_keys != scope_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: "
                "trade_scope_candidate_order is not exactly trade_scope."
            )
        if change_keys != scope_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: rank_changes is not "
                "exactly trade_scope."
            )
        previous_baseline_rank = None
        for row in trade_detail["trade_scope_baseline_local_order"]:
            rank_value = row["candidate_baseline_local_rank"]
            if (
                previous_baseline_rank is not None
                and rank_value <= previous_baseline_rank
            ):
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: trade-scope baseline "
                    "local order is not strictly increasing."
                )
            previous_baseline_rank = rank_value
        previous_trade_rank = None
        for row in trade_detail["trade_scope_candidate_order"]:
            rank_value = row["candidate_trade_local_rank"]
            if previous_trade_rank is not None and rank_value <= previous_trade_rank:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: trade-scope candidate "
                    "order is not strictly increasing."
                )
            previous_trade_rank = rank_value

        for change in trade_detail["rank_changes"]:
            visit_key_tuple = visit_key_tuple_from_json_dict(change["visit_key"])
            baseline_local_rank = change["candidate_baseline_local_rank"]
            candidate_trade_local_rank = change["candidate_trade_local_rank"]
            if local_rank_by_visit_key[visit_key_tuple] != baseline_local_rank:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: rank change baseline "
                    "local rank disagrees with candidate_visits."
                )
            expected_direction = rank_change_direction(
                baseline_local_rank=baseline_local_rank,
                candidate_trade_local_rank=candidate_trade_local_rank,
            )
            if change["rank_change_direction"] != expected_direction:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: rank_change_direction "
                    "does not match the two local ranks."
                )


def _scope_keys_in_order(rows: list[dict]) -> set:
    keys = set()
    for row in rows:
        visit_key_tuple = visit_key_tuple_from_json_dict(row["visit_key"])
        if visit_key_tuple in keys:
            raise RuntimeError(
                f"Duplicate VisitKey {visit_key_tuple!r} in a trade-scope list."
            )
        keys.add(visit_key_tuple)
    return keys


def _verify_baseline_node_passage_order(
    *,
    timestep: int,
    node_name: str,
    detail: dict,
    collector_records_by_visit_key: dict,
) -> None:
    seen_keys = set()
    expected_rank = 1
    previous_timestep = None
    for row in detail["baseline_node_passage_order"]:
        if row["node_name"] != node_name:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: baseline passage row node "
                f"{row['node_name']!r} does not match."
            )
        visit_key_tuple = visit_key_tuple_from_json_dict(row["visit_key"])
        if visit_key_tuple in seen_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: duplicate baseline passage "
                f"VisitKey {visit_key_tuple!r}."
            )
        seen_keys.add(visit_key_tuple)
        if row["baseline_node_passage_rank"] != expected_rank:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: baseline passage ranks are "
                "not consecutive from 1 in stored order."
            )
        expected_rank = expected_rank + 1
        passage_timestep = row["baseline_passage_timestep"]
        if previous_timestep is not None and passage_timestep < previous_timestep:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: baseline passage timestep "
                "moved backwards."
            )
        previous_timestep = passage_timestep

        source = row["arrival_source"]
        snapshot_fixed = row["snapshot_fixed"]
        if source == ARRIVAL_SOURCE_COLLECTOR_SNAPSHOT:
            if snapshot_fixed is not True:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: collector source is "
                    "not marked snapshot_fixed."
                )
            if visit_key_tuple not in collector_records_by_visit_key:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: collector passage "
                    f"{visit_key_tuple!r} is missing from collector records."
                )
            collector_record = collector_records_by_visit_key[visit_key_tuple]
            if (
                collector_record["baseline_arrival_timestep"]
                != row["baseline_arrival_timestep"]
                or collector_record["arrival_tiebreaker"]
                != row["arrival_tiebreaker"]
                or collector_record["vehicle_id"] != row["vehicle_id"]
                or collector_record["baseline_passage_timestep"]
                != row["baseline_passage_timestep"]
            ):
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: captured collector "
                    f"passage for {visit_key_tuple!r} disagrees with the "
                    "collector record."
                )
        elif source == ARRIVAL_SOURCE_CURRENT_VISIT_OUTSIDE_SNAPSHOT:
            if snapshot_fixed is not False:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: outside-snapshot "
                    "source is marked snapshot_fixed."
                )
            if row["baseline_arrival_timestep"] is None:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: outside-snapshot "
                    "passage is missing baseline_arrival_timestep."
                )
            if row["arrival_tiebreaker"] is None or row["vehicle_id"] is None:
                raise RuntimeError(
                    f"T={timestep} node {node_name!r}: outside-snapshot "
                    "passage is missing tiebreaker or vehicle id."
                )
        else:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: unknown arrival_source "
                f"{source!r}."
            )

    for visit_key_tuple, record in collector_records_by_visit_key.items():
        if record["baseline_passage_timestep"] is None:
            continue
        if visit_key_tuple not in seen_keys:
            raise RuntimeError(
                f"T={timestep} node {node_name!r}: collector passage for "
                f"{visit_key_tuple!r} was not captured in "
                "baseline_node_passage_order."
            )


def count_csv_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        row_count = 0
        for _row in reader:
            row_count = row_count + 1
    if row_count < 1:
        raise RuntimeError(f"CSV has no header: {path}")
    return row_count - 1


def verify_diagnostic_results(
    *,
    world,
    capture: DiagnosticCapture,
    evaluation_report: dict,
) -> None:
    expected_calls = initial_trial.EXPECTED_DRIVER_CALL_COUNT
    if capture.call_count != expected_calls:
        raise RuntimeError(
            "Driver wrapper call count "
            f"{capture.call_count} does not match expected {expected_calls}."
        )
    if len(capture.decisions) != expected_calls:
        raise RuntimeError(
            "Decision summary row count "
            f"{len(capture.decisions)} does not match expected {expected_calls}."
        )

    expected_timesteps = []
    timestep = initial_trial.EVALUATION_START_TIMESTEP
    while timestep <= initial_trial.EVALUATION_END_TIMESTEP:
        expected_timesteps.append(timestep)
        timestep = timestep + 1

    actual_timesteps = []
    for decision in capture.decisions:
        actual_timesteps.append(decision["summary"]["timestep"])
    if actual_timesteps != expected_timesteps:
        raise RuntimeError(
            "Decision timesteps are not exactly one Node row for every "
            f"timestep from {initial_trial.EVALUATION_START_TIMESTEP} "
            f"through {initial_trial.EVALUATION_END_TIMESTEP}."
        )

    if world.T != initial_trial.EXPECTED_WORLD_T_AFTER_SIM:
        raise RuntimeError(
            f"World.T {world.T!r} does not match expected "
            f"{initial_trial.EXPECTED_WORLD_T_AFTER_SIM}."
        )
    if evaluation_report["world_t_ok"] is not True:
        raise RuntimeError("evaluation end world_t_ok is not True.")
    if evaluation_report["unobserved_ok"] is not True:
        raise RuntimeError("evaluation end unobserved_ok is not True.")
    if evaluation_report["trade_ex_post_ok"] is not True:
        raise RuntimeError("evaluation end trade_ex_post_ok is not True.")
    if evaluation_report["individual_ex_post_ok"] is not True:
        raise RuntimeError("evaluation end individual_ex_post_ok is not True.")

    written_names = []
    for path in DIAGNOSTIC_OUTPUT_DIR.iterdir():
        if path.is_file():
            written_names.append(path.name)
        else:
            raise RuntimeError(
                f"Unexpected non-file in diagnostic directory: {path}"
            )
    if sorted(written_names) != sorted(OUTPUT_FILE_NAMES):
        raise RuntimeError(
            "Diagnostic directory files "
            f"{sorted(written_names)!r} do not match "
            f"{sorted(OUTPUT_FILE_NAMES)!r}."
        )

    summary_row_count = count_csv_data_rows(
        DIAGNOSTIC_OUTPUT_DIR / DECISION_SUMMARY_NAME
    )
    if summary_row_count != expected_calls:
        raise RuntimeError(
            f"decision_summary.csv has {summary_row_count} data rows, "
            f"expected {expected_calls}."
        )

    for decision in capture.decisions:
        summary = decision["summary"]
        identity = summary["selected_candidate_identity"]
        if summary["selection_status"] == SELECTION_STATUS_SELECTED:
            matched = None
            for row in decision["candidate_rows"]:
                if row["candidate_identity"] == identity and row["selected"] is True:
                    matched = row
            if matched is None:
                raise RuntimeError(
                    f"T={summary['timestep']} node {summary['node_name']!r}: "
                    f"selected identity {identity!r} is missing from "
                    "candidate rows."
                )
            if matched["total_buyer_value_G"] != summary["selected_total_buyer_value_G"]:
                raise RuntimeError(
                    f"T={summary['timestep']} node {summary['node_name']!r}: "
                    "selected G does not match the economic result."
                )
            if (
                matched["total_required_compensation_R"]
                != summary["selected_total_required_compensation_R"]
            ):
                raise RuntimeError(
                    f"T={summary['timestep']} node {summary['node_name']!r}: "
                    "selected R does not match the economic result."
                )
            if matched["surplus"] != summary["selected_surplus"]:
                raise RuntimeError(
                    f"T={summary['timestep']} node {summary['node_name']!r}: "
                    "selected surplus does not match the economic result."
                )
            if decision["detail"]["final_rank_result"] is None:
                raise RuntimeError(
                    f"T={summary['timestep']} node {summary['node_name']!r}: "
                    "final rank detail is missing."
                )

    for decision in capture.decisions:
        verify_baseline_fork_decision_detail(decision)


def collect_console_facts(capture: DiagnosticCapture) -> dict:
    candidate_timesteps = []
    concrete_buyer_total = 0
    fifo_false_total = 0
    unresolved_total = 0
    feasible_total = 0
    selected_count = 0
    selection_reason_not_applicable_count = 0
    reason_counts = {
        REASON_NO_FEASIBLE: 0,
        REASON_UNIQUE_SURPLUS: 0,
        REASON_UNIQUE_BUYER_COUNT: 0,
        REASON_FINAL_RNG: 0,
    }
    for decision in capture.decisions:
        summary = decision["summary"]
        if (
            summary["candidate_visit_count"] > 0
            or summary["concrete_buyer_candidate_count"] > 0
        ):
            candidate_timesteps.append(summary["timestep"])
        concrete_buyer_total = (
            concrete_buyer_total + summary["concrete_buyer_candidate_count"]
        )
        fifo_false_total = fifo_false_total + summary["fifo_false_count"]
        unresolved_total = unresolved_total + summary["unresolved_count"]
        feasible_total = feasible_total + summary["economically_feasible_count"]
        if summary["selection_status"] == SELECTION_STATUS_SELECTED:
            selected_count = selected_count + 1
        reason = summary["selection_reason"]
        if reason == "":
            selection_reason_not_applicable_count = (
                selection_reason_not_applicable_count + 1
            )
            continue
        if reason not in reason_counts:
            raise RuntimeError(f"Unexpected selection reason {reason!r}.")
        reason_counts[reason] = reason_counts[reason] + 1
    return {
        "candidate_timesteps": candidate_timesteps,
        "concrete_buyer_total": concrete_buyer_total,
        "fifo_false_total": fifo_false_total,
        "unresolved_total": unresolved_total,
        "feasible_total": feasible_total,
        "selected_count": selected_count,
        "outside_snapshot_passage_rows": _count_outside_snapshot_passage_rows(
            capture
        ),
        "selection_reason_not_applicable_count": (
            selection_reason_not_applicable_count
        ),
        "reason_counts": reason_counts,
    }


def print_console_summary(capture: DiagnosticCapture) -> None:
    facts = collect_console_facts(capture)
    print()
    print("=== TVT-MP decision trace diagnostic ===")
    print(f"driver wrapper call count: {capture.call_count}")
    print(f"decision summary row count: {len(capture.decisions)}")
    print(
        "timesteps with candidate visits or concrete buyer candidates: "
        + str(facts["candidate_timesteps"])
    )
    print(f"concrete buyer candidate total: {facts['concrete_buyer_total']}")
    print(f"FIFO False candidate total: {facts['fifo_false_total']}")
    print(f"unresolved candidate total: {facts['unresolved_total']}")
    print(f"economically feasible candidate total: {facts['feasible_total']}")
    print(f"selected candidate count: {facts['selected_count']}")
    print(
        "outside-snapshot baseline passage rows: "
        + str(facts["outside_snapshot_passage_rows"])
    )
    print(
        "selection reason not applicable: "
        + str(facts["selection_reason_not_applicable_count"])
    )
    print("selection reason counts:")
    for reason_name, reason_count in facts["reason_counts"].items():
        print(f"  {reason_name}: {reason_count}")
    print(f"output directory: {DIAGNOSTIC_OUTPUT_DIR}")
    print("files:")
    for file_name in OUTPUT_FILE_NAMES:
        print(f"  {file_name}")
    print()


def _count_outside_snapshot_passage_rows(capture: DiagnosticCapture) -> int:
    count = 0
    for decision in capture.decisions:
        if not decision["has_candidate_detail"]:
            continue
        for row in decision["detail"]["baseline_node_passage_order"]:
            if row["arrival_source"] == ARRIVAL_SOURCE_CURRENT_VISIT_OUTSIDE_SNAPSHOT:
                count = count + 1
    return count


def convert_actual_node_passage_orders(world) -> dict:
    """実 World の通過履歴を、保存順のまま単純値へ写す。registry は変えない。"""
    registry = world.order_control_tvt_mp_actual_node_passage_history_registry
    orders = {}
    for node_name, records in registry.records_by_node_name.items():
        rows = []
        for record in records:
            vehicle_name, visit_id = record.visit_key
            rows.append(
                {
                    "actual_node_passage_rank": record.actual_node_passage_rank,
                    "actual_passage_timestep": record.actual_passage_timestep,
                    "node_name": node_name,
                    "visit_key": visit_key_to_json((vehicle_name, visit_id)),
                    "actual_route_next_link_name": (
                        record.actual_route_next_link_name
                    ),
                }
            )
        orders[node_name] = rows
    return orders


def verify_actual_node_passage_orders(orders: dict) -> None:
    for node_name, rows in orders.items():
        seen_keys = set()
        expected_rank = 1
        previous_timestep = None
        for row in rows:
            if row["node_name"] != node_name:
                raise RuntimeError(
                    f"Actual passage row node {row['node_name']!r} does not "
                    f"match {node_name!r}."
                )
            visit_key_tuple = visit_key_tuple_from_json_dict(row["visit_key"])
            if visit_key_tuple in seen_keys:
                raise RuntimeError(
                    f"Node {node_name!r}: duplicate actual passage VisitKey "
                    f"{visit_key_tuple!r}."
                )
            seen_keys.add(visit_key_tuple)
            if row["actual_node_passage_rank"] != expected_rank:
                raise RuntimeError(
                    f"Node {node_name!r}: actual passage ranks are not "
                    "consecutive from 1 in stored order."
                )
            expected_rank = expected_rank + 1
            passage_timestep = row["actual_passage_timestep"]
            if (
                previous_timestep is not None
                and passage_timestep < previous_timestep
            ):
                raise RuntimeError(
                    f"Node {node_name!r}: actual passage timestep moved "
                    "backwards."
                )
            previous_timestep = passage_timestep


def _csv_optional_number(text: str):
    if text is None or text == "":
        return None
    if "." in text or "e" in text or "E" in text:
        return float(text)
    return int(text)


def _read_reference_csv(file_name: str) -> list[dict]:
    path = REFERENCE_TRIAL_DIR / file_name
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(row)
    return rows


def _buyers_text_from_selected_identity(node_name: str, identity: str) -> str:
    prefix = node_name + "|"
    if not identity.startswith(prefix):
        raise RuntimeError(
            f"Selected identity {identity!r} does not start with {prefix!r}."
        )
    body = identity[len(prefix):]
    return body.replace(";", "|")


def _format_buyers_sorted(buyers_sorted) -> str:
    parts = []
    for vehicle_name, visit_id in buyers_sorted:
        parts.append(f"{vehicle_name}:{visit_id}")
    return "|".join(parts)


def verify_reference_trial_csv(
    capture: DiagnosticCapture,
    actual_node_passage_orders: dict,
    world,
) -> None:
    """最新 trial CSV と、この診断 run の選択結果を完全比較する。"""
    from uxsim.order_control_tvt_mp_research_output import (
        build_tvt_mp_research_output,
    )

    transaction_rows = _read_reference_csv("tvt_mp_transactions.csv")
    visit_rows = _read_reference_csv("tvt_mp_visits.csv")
    for row in transaction_rows:
        if row["scenario_name"] != REFERENCE_SCENARIO_NAME:
            raise RuntimeError(
                "Reference transaction scenario_name "
                f"{row['scenario_name']!r} is not {REFERENCE_SCENARIO_NAME!r}."
            )
    for row in visit_rows:
        if row["scenario_name"] != REFERENCE_SCENARIO_NAME:
            raise RuntimeError(
                "Reference visit scenario_name "
                f"{row['scenario_name']!r} is not {REFERENCE_SCENARIO_NAME!r}."
            )

    csv_transactions = {}
    for row in transaction_rows:
        identity = (
            int(row["tvt_decision_timestep"]),
            row["node_name"],
            row["buyers_sorted"],
        )
        if identity in csv_transactions:
            raise RuntimeError(f"Duplicate reference transaction {identity!r}.")
        csv_transactions[identity] = row

    selected_transactions = {}
    selected_decisions = {}
    for decision in capture.decisions:
        summary = decision["summary"]
        if summary["selection_status"] != SELECTION_STATUS_SELECTED:
            continue
        buyers_text = _buyers_text_from_selected_identity(
            summary["node_name"],
            summary["selected_candidate_identity"],
        )
        identity = (summary["timestep"], summary["node_name"], buyers_text)
        if identity in selected_transactions:
            raise RuntimeError(f"Duplicate selected transaction {identity!r}.")
        selected_transactions[identity] = summary
        selected_decisions[identity] = decision

    bundle = build_tvt_mp_research_output(world, REFERENCE_SCENARIO_NAME)
    bundle_transactions = {}
    for row in bundle.transactions:
        identity = (
            row.tvt_decision_timestep,
            row.node_name,
            _format_buyers_sorted(row.buyers_sorted),
        )
        bundle_transactions[identity] = row
    if set(selected_transactions) != set(csv_transactions):
        raise RuntimeError(
            "Selected diagnostic transactions "
            f"{sorted(selected_transactions)!r} do not match the reference "
            f"trial CSV {sorted(csv_transactions)!r}."
        )
    if set(bundle_transactions) != set(csv_transactions):
        raise RuntimeError(
            "This run's research transactions do not match the reference "
            "trial CSV."
        )

    for identity, summary in selected_transactions.items():
        csv_row = csv_transactions[identity]
        bundle_row = bundle_transactions[identity]
        csv_payment = _csv_optional_number(csv_row["buyer_official_payment_total"])
        csv_compensation = _csv_optional_number(
            csv_row["seller_official_compensation_total"]
        )
        if summary["buyer_payment_total"] != csv_payment:
            raise RuntimeError(
                f"Transaction {identity!r}: diagnostic buyer payment "
                f"{summary['buyer_payment_total']!r} does not match CSV "
                f"{csv_payment!r}."
            )
        if summary["seller_compensation_total"] != csv_compensation:
            raise RuntimeError(
                f"Transaction {identity!r}: diagnostic seller compensation "
                f"{summary['seller_compensation_total']!r} does not match "
                f"CSV {csv_compensation!r}."
            )
        if bundle_row.buyer_official_payment_total != csv_payment:
            raise RuntimeError(
                f"Transaction {identity!r}: research-output buyer payment "
                "does not match the reference CSV."
            )
        if bundle_row.seller_official_compensation_total != csv_compensation:
            raise RuntimeError(
                f"Transaction {identity!r}: research-output seller "
                "compensation does not match the reference CSV."
            )

    bundle_visits = {}
    for row in bundle.visits:
        visit_identity = (
            row.tvt_decision_timestep,
            row.node_name,
            _format_buyers_sorted(row.buyers_sorted),
            row.vehicle_name,
            row.visit_id,
        )
        bundle_visits[visit_identity] = row

    for csv_visit in visit_rows:
        identity = (
            int(csv_visit["tvt_decision_timestep"]),
            csv_visit["node_name"],
            csv_visit["buyers_sorted"],
        )
        visit_key = (
            csv_visit["vehicle_name"],
            int(csv_visit["visit_id"]),
        )
        decision = selected_decisions[identity]
        _compare_reference_visit(
            identity=identity,
            visit_key=visit_key,
            csv_visit=csv_visit,
            decision=decision,
            actual_node_passage_orders=actual_node_passage_orders,
            bundle_visit=bundle_visits[
                (
                    identity[0],
                    identity[1],
                    identity[2],
                    visit_key[0],
                    visit_key[1],
                )
            ],
        )


def _compare_reference_visit(
    *,
    identity,
    visit_key,
    csv_visit: dict,
    decision: dict,
    actual_node_passage_orders: dict,
    bundle_visit,
) -> None:
    passage = None
    for row in decision["candidate_rows"]:
        if row["selected"] is not True:
            continue
        for record in row["local_detail"]["required_passage_records"]:
            record_key = visit_key_tuple_from_json_dict(record["visit_key"])
            if record_key == visit_key:
                passage = record
    if passage is None:
        raise RuntimeError(
            f"Transaction {identity!r} visit {visit_key!r} has no selected "
            "candidate passage record."
        )

    csv_baseline = _csv_optional_number(csv_visit["baseline_passage_timestep"])
    csv_candidate = _csv_optional_number(csv_visit["candidate_passage_timestep"])
    csv_actual = _csv_optional_number(csv_visit["actual_passage_timestep"])
    if passage["baseline_passage_timestep"] != csv_baseline:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: baseline passage "
            f"{passage['baseline_passage_timestep']!r} does not match CSV "
            f"{csv_baseline!r}."
        )
    if passage["candidate_passage_timestep"] != csv_candidate:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: candidate passage "
            f"{passage['candidate_passage_timestep']!r} does not match CSV "
            f"{csv_candidate!r}."
        )
    if passage["trade_role"] != csv_visit["role"]:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: role "
            f"{passage['trade_role']!r} does not match CSV "
            f"{csv_visit['role']!r}."
        )

    payment_amount = None
    compensation_amount = None
    payments = decision["detail"]["payment_and_compensation_result"]
    for payment in payments["buyer_payment_records"]:
        payment_key = visit_key_tuple_from_json_dict(payment["visit_key"])
        if payment_key == visit_key:
            payment_amount = payment["payment_P_b"]
    for compensation in payments["seller_compensation_records"]:
        compensation_key = visit_key_tuple_from_json_dict(
            compensation["visit_key"]
        )
        if compensation_key == visit_key:
            compensation_amount = compensation["compensation_amount"]
    csv_payment = _csv_optional_number(csv_visit["official_payment"])
    csv_compensation = _csv_optional_number(csv_visit["official_compensation"])
    if payment_amount != csv_payment:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: official payment "
            f"{payment_amount!r} does not match CSV {csv_payment!r}."
        )
    if compensation_amount != csv_compensation:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: official compensation "
            f"{compensation_amount!r} does not match CSV {csv_compensation!r}."
        )

    csv_assigned = _csv_optional_number(csv_visit["assigned_rank"])
    if bundle_visit.assigned_rank != csv_assigned:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: assigned rank "
            f"{bundle_visit.assigned_rank!r} does not match CSV {csv_assigned!r}."
        )

    actual_row = None
    node_name = identity[1]
    for row in actual_node_passage_orders[node_name]:
        actual_key = visit_key_tuple_from_json_dict(row["visit_key"])
        if actual_key == visit_key:
            actual_row = row
    if actual_row is None:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r} is missing from the actual "
            "node passage order."
        )
    if actual_row["actual_passage_timestep"] != csv_actual:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: actual passage "
            f"{actual_row['actual_passage_timestep']!r} does not match CSV "
            f"{csv_actual!r}."
        )
    csv_actual_rank = _csv_optional_number(csv_visit["actual_node_passage_rank"])
    if actual_row["actual_node_passage_rank"] != csv_actual_rank:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: actual rank "
            f"{actual_row['actual_node_passage_rank']!r} does not match CSV "
            f"{csv_actual_rank!r}."
        )
    csv_rank_change = _csv_optional_number(csv_visit["actual_rank_change"])
    if bundle_visit.actual_rank_change != csv_rank_change:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: actual rank change "
            f"{bundle_visit.actual_rank_change!r} does not match CSV "
            f"{csv_rank_change!r}."
        )

    if bundle_visit.realized_gain != _csv_optional_number(
        csv_visit["realized_gain"]
    ):
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: realized gain does not "
            "match the reference CSV."
        )
    if bundle_visit.satisfaction_status != csv_visit["satisfaction_status"]:
        raise RuntimeError(
            f"Visit {visit_key!r} at {identity!r}: satisfaction "
            f"{bundle_visit.satisfaction_status!r} does not match CSV "
            f"{csv_visit['satisfaction_status']!r}."
        )


def main() -> int:
    refuse_existing_diagnostic_directory()

    vot_rng = np.random.default_rng(initial_trial.VOT_SEED)
    vot_values = initial_trial.generate_vehicle_vots(
        vot_rng,
        len(initial_trial.VEHICLE_SPECS),
    )
    vot_records = initial_trial.build_vehicle_vot_records(
        initial_trial.VEHICLE_SPECS,
        vot_values,
    )

    world = initial_trial.build_world_and_network()
    initial_trial.add_vehicles_to_world(
        world,
        initial_trial.VEHICLE_SPECS,
        vot_records,
    )
    world.finalize_scenario()
    if world.TSIZE != initial_trial.INTERNAL_TSIZE:
        raise RuntimeError(
            f"Expected TSIZE=={initial_trial.INTERNAL_TSIZE} after finalize, "
            f"got {world.TSIZE}."
        )

    capture = DiagnosticCapture()
    # Node method を先に包み、終了時は driver を先に戻してから Node method を戻す。
    original_transfer = install_baseline_passage_observer(capture)
    try:
        original_run_tvt_mp_driver = install_driver_wrapper(capture)
        try:
            world.exec_simulation()
            evaluation_report = initial_trial.verify_evaluation_end(world)
            actual_orders = convert_actual_node_passage_orders(world)
            verify_actual_node_passage_orders(actual_orders)
            write_diagnostic_files(
                vot_records,
                capture.decisions,
                actual_orders,
            )
            verify_diagnostic_results(
                world=world,
                capture=capture,
                evaluation_report=evaluation_report,
            )
            verify_reference_trial_csv(capture, actual_orders, world)
        finally:
            restore_driver(original_run_tvt_mp_driver)
    finally:
        restore_baseline_passage_observer(original_transfer)

    if driver_module.run_tvt_mp_driver is not original_run_tvt_mp_driver:
        raise RuntimeError(
            "Driver wrapper was not restored after the diagnostic run."
        )
    if (
        uxsim_module.Node._transfer_one_vehicle_between_links
        is not original_transfer
    ):
        raise RuntimeError(
            "Node transfer method was not restored after the diagnostic run."
        )

    print_console_summary(capture)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
