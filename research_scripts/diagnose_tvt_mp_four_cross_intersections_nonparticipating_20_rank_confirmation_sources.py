"""
Identify formal rank-confirmation sources for northwest_intersection visits
that receive a new C rank while selected=False on the nonparticipating 20%
four-cross trial.

Reads only run_tvt_mp_driver() upstream result objects. Does not change
production, the trial, or other diagnostics.
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
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankStatus,
    OrderControlTvtMpFinalizationSource,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState


TARGET_NODE_NAME = "northwest_intersection"
ACTUAL_TRACE_START_TIMESTEP = 390
ACTUAL_TRACE_END_TIMESTEP = 406

REQUIRED_RUNTIME_VISITS = (
    {
        "vehicle_name": "veh_sw_nw_base_038",
        "visit_id": 2,
        "decision_timestep": 390,
        "assigned_rank": 178,
        "participates_in_order_exchange": True,
    },
    {
        "vehicle_name": "veh_sw_nw_base_041",
        "visit_id": 2,
        "decision_timestep": 404,
        "assigned_rank": 185,
        "participates_in_order_exchange": True,
    },
    {
        "vehicle_name": "veh_nw_sw_base_049",
        "visit_id": 1,
        "decision_timestep": 406,
        "assigned_rank": 186,
        "participates_in_order_exchange": False,
    },
)

CONFIRMATION_SOURCE_ALREADY_ARRIVED = "already_arrived_undetermined_confirmation"
CONFIRMATION_SOURCE_LEADING_NONPARTICIPATING = "leading_nonparticipating_confirmation"
CONFIRMATION_SOURCE_SELECTED_CANDIDATE_FINAL = "selected_candidate_final_rank"
CONFIRMATION_SOURCE_BASELINE_FALLBACK = "baseline_fallback_final_rank"
CONFIRMATION_SOURCE_SELECTED_OUTSIDE_SCOPE_BASELINE = (
    "selected_candidate_outside_trade_scope_baseline_rank"
)

FORMAL_CONFIRMATION_SOURCE_CLASSIFICATIONS = (
    CONFIRMATION_SOURCE_ALREADY_ARRIVED,
    CONFIRMATION_SOURCE_LEADING_NONPARTICIPATING,
    CONFIRMATION_SOURCE_BASELINE_FALLBACK,
    CONFIRMATION_SOURCE_SELECTED_OUTSIDE_SCOPE_BASELINE,
)

OUTPUT_DIR = (
    trial.reference.TRIAL_PARENT
    / (
        "tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_"
        "600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_"
        "rank_confirmation_sources"
    )
)
RANK_CONFIRMATION_SOURCES_CSV = "rank_confirmation_sources.csv"
SUMMARY_NAME = "rank_confirmation_sources_summary.txt"
MANIFEST_NAME = "manifest.json"
OUTPUT_FILE_NAMES = (
    RANK_CONFIRMATION_SOURCES_CSV,
    SUMMARY_NAME,
    MANIFEST_NAME,
)

CSV_COLUMNS = (
    "tvt_decision_timestep",
    "node_name",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "participates_in_order_exchange",
    "selected",
    "selected_candidate_evaluation_index",
    "assigned_rank_before",
    "assigned_rank_after",
    "newly_confirmed",
    "confirmation_source",
    "in_confirmed_arrived_visit_keys",
    "in_confirmed_leading_nonparticipating_visit_keys",
    "in_final_rank_visits",
    "final_rank_status",
    "final_local_rank",
    "finalization_source",
    "formal_route_next_link_name",
    "route_origin",
    "decision_window_visit_keys",
    "remaining_decision_window_visit_keys",
    "confirmed_arrived_visit_keys",
    "confirmed_leading_nonparticipating_visit_keys",
)


class _StopAfterRankConfirmationTargetsCaptured(Exception):
    """Stop the real World once all required target visits are recorded."""


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_driver = None
        self.rows: list[dict] = []
        self.captured_target_keys: set[tuple[str, int]] = set()
        self.ever_confirmed_keys: set[tuple[str, int]] = set()
        self.early_stop_timestep: int | None = None


GATE = _Gate()


def _visit_text(visit_key: tuple[str, int]) -> str:
    return f"{visit_key[0]}:{visit_key[1]}"


def _plain_visit_key(visit_key) -> tuple[str, int]:
    vehicle_name = visit_key[0]
    visit_id = visit_key[1]
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is {vehicle_name!r}.")
    if type(visit_id) is not int or type(visit_id) is bool:
        raise RuntimeError(f"VisitKey visit id is {visit_id!r}.")
    return (vehicle_name, visit_id)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        if value is True:
            return "True"
        return "False"
    return str(value)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            cells = {column: _csv_cell(row.get(column)) for column in columns}
            writer.writerow(cells)


def _serialize_visit_keys(visit_keys) -> str:
    parts = []
    for visit_key in visit_keys:
        parts.append(_visit_text(_plain_visit_key(visit_key)))
    return "|".join(parts)


def _is_diagnostic_real_world(world) -> bool:
    if GATE.real_world is not None and world is not GATE.real_world:
        return False
    if getattr(world, "_order_control_baseline_collector", None) is not None:
        return False
    return True


def _rank_map(world) -> dict[tuple[str, int], int]:
    states = getattr(world, "order_control_tvt_rank_states_by_node_name", None)
    if not isinstance(states, dict):
        return {}
    rank_state = states.get(TARGET_NODE_NAME)
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        return {}
    ranks: dict[tuple[str, int], int] = {}
    for visit_key in rank_state.confirmed_visit_keys_in_order():
        plain = _plain_visit_key(visit_key)
        ranks[plain] = rank_state.assigned_rank(visit_key)
    return ranks


def _one_node(results, label: str, timestep: int):
    matched = None
    count = 0
    for result in results:
        if result.node_name != TARGET_NODE_NAME:
            continue
        count = count + 1
        matched = result
    if count != 1 or matched is None:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: {label} count is {count}."
        )
    return matched


def _upstream_from_atomic(atomic, timestep: int) -> dict:
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
    return {
        "timestep": timestep,
        "final_rank_nodes": final_rank_set.node_final_rank_results,
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "leading_nodes": leading_set.node_confirmation_results,
        "arrived_nodes": arrived_set.node_confirmation_results,
    }


def _find_one_based_evaluation_index(
    candidate_economic_results,
    selected_economic,
    timestep: int,
) -> int:
    evaluation_index = None
    index = 0
    for candidate_economic in candidate_economic_results:
        index = index + 1
        if candidate_economic is selected_economic:
            if evaluation_index is not None:
                raise RuntimeError(
                    f"T={timestep} {TARGET_NODE_NAME}: selected economic result appears more than once."
                )
            evaluation_index = index
    if evaluation_index is None:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: selected economic result is missing from the node list."
        )
    if type(evaluation_index) is not int or type(evaluation_index) is bool:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: evaluation index must be a Python int."
        )
    if evaluation_index < 1:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: evaluation index must be >= 1."
        )
    return evaluation_index


def _count_visit_key_hits(visit_keys, plain_key: tuple[str, int]) -> int:
    count = 0
    for visit_key in visit_keys:
        if _plain_visit_key(visit_key) == plain_key:
            count = count + 1
    return count


def _find_unique_final_rank_record(
    final_rank_visits,
    plain_key: tuple[str, int],
    timestep: int,
):
    found = None
    count = 0
    for record in final_rank_visits:
        if _plain_visit_key(record.visit_key) == plain_key:
            count = count + 1
            found = record
    if count != 1:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: final_rank_visits match count for "
            f"{_visit_text(plain_key)} is {count}, expected 1."
        )
    return found


def _confirmation_source_from_final_rank(
    final_rank_node,
    final_record,
    timestep: int,
    plain_key: tuple[str, int],
) -> str:
    if final_record.finalization_source is OrderControlTvtMpFinalizationSource.SELECTED_CANDIDATE:
        return CONFIRMATION_SOURCE_SELECTED_CANDIDATE_FINAL
    if final_record.finalization_source is OrderControlTvtMpFinalizationSource.BASELINE:
        status = final_rank_node.final_rank_status
        if status is OrderControlTvtMpFinalRankStatus.BASELINE_FALLBACK_RANKS:
            return CONFIRMATION_SOURCE_BASELINE_FALLBACK
        if status is OrderControlTvtMpFinalRankStatus.SELECTED_CANDIDATE_RANKS:
            return CONFIRMATION_SOURCE_SELECTED_OUTSIDE_SCOPE_BASELINE
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: BASELINE finalization for "
            f"{_visit_text(plain_key)} has unsupported final_rank_status {status!r}."
        )
    raise RuntimeError(
        f"T={timestep} {TARGET_NODE_NAME}: unsupported finalization_source "
        f"{final_record.finalization_source!r} for {_visit_text(plain_key)}."
    )


def _classify_confirmation_source(
    plain_key: tuple[str, int],
    arrived_node,
    leading_node,
    final_rank_node,
    timestep: int,
) -> str:
    in_arrived = (
        _count_visit_key_hits(arrived_node.confirmed_arrived_visit_keys, plain_key) > 0
    )
    in_leading = (
        _count_visit_key_hits(
            leading_node.confirmed_leading_nonparticipating_visit_keys,
            plain_key,
        )
        > 0
    )
    final_record = None
    in_final = False
    for record in final_rank_node.final_rank_visits:
        if _plain_visit_key(record.visit_key) == plain_key:
            in_final = True
            if final_record is not None:
                raise RuntimeError(
                    f"T={timestep} {TARGET_NODE_NAME}: duplicate final_rank_visits for "
                    f"{_visit_text(plain_key)}."
                )
            final_record = record
    source_hits = []
    if in_arrived is True:
        source_hits.append(CONFIRMATION_SOURCE_ALREADY_ARRIVED)
    if in_leading is True:
        source_hits.append(CONFIRMATION_SOURCE_LEADING_NONPARTICIPATING)
    if in_final is True:
        if final_record is None:
            raise RuntimeError(
                f"T={timestep} {TARGET_NODE_NAME}: in_final_rank_visits without record."
            )
        source_hits.append(
            _confirmation_source_from_final_rank(
                final_rank_node,
                final_record,
                timestep,
                plain_key,
            )
        )
    if len(source_hits) == 0:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: no formal confirmation source for "
            f"{_visit_text(plain_key)}."
        )
    if len(source_hits) > 1:
        raise RuntimeError(
            f"T={timestep} {TARGET_NODE_NAME}: multiple confirmation sources for "
            f"{_visit_text(plain_key)}: {source_hits!r}."
        )
    return source_hits[0]


def _vehicle_participation(world, vehicle_name: str) -> bool:
    vehicles = getattr(world, "VEHICLES", None)
    if not isinstance(vehicles, dict):
        raise RuntimeError("World.VEHICLES is not a dict.")
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"vehicle_name must be a non-empty str, got {vehicle_name!r}."
        )
    vehicle = vehicles.get(vehicle_name)
    if vehicle is None:
        raise RuntimeError(f"Vehicle {vehicle_name!r} is missing from the World.")
    if getattr(vehicle, "name", None) != vehicle_name:
        raise RuntimeError(
            f"World.VEHICLES[{vehicle_name!r}] has vehicle name "
            f"{getattr(vehicle, 'name', None)!r}."
        )
    participates = getattr(vehicle, "participates_in_order_exchange", None)
    if type(participates) is not bool:
        raise RuntimeError(
            f"{vehicle_name} participates_in_order_exchange is {participates!r}."
        )
    return participates


def _expected_participation_from_vot(vot_records, vehicle_name: str) -> bool:
    for record in vot_records:
        if record.vehicle_name == vehicle_name:
            participates = record.participates_in_order_exchange
            if type(participates) is not bool:
                raise RuntimeError(
                    f"vot record {vehicle_name} participates_in_order_exchange is {participates!r}."
                )
            return participates
    raise RuntimeError(f"vot record for {vehicle_name!r} is missing.")


def _verify_participation_against_trial(world, vot_records) -> None:
    for required in REQUIRED_RUNTIME_VISITS:
        vehicle_name = required["vehicle_name"]
        expected = required["participates_in_order_exchange"]
        runtime = _vehicle_participation(world, vehicle_name)
        from_vot = _expected_participation_from_vot(vot_records, vehicle_name)
        if runtime is not expected:
            raise RuntimeError(
                f"{vehicle_name} runtime participates={runtime!r}, expected {expected!r}."
            )
        if from_vot is not expected:
            raise RuntimeError(
                f"{vehicle_name} vot participates={from_vot!r}, expected {expected!r}."
            )
        if runtime is not from_vot:
            raise RuntimeError(
                f"{vehicle_name} runtime participates {runtime!r} differs from vot {from_vot!r}."
            )


def _build_row_for_newly_confirmed(
    world,
    timestep: int,
    plain_key: tuple[str, int],
    assigned_rank_before,
    assigned_rank_after: int,
    upstream: dict,
) -> dict:
    arrived_node = _one_node(upstream["arrived_nodes"], "arrived confirmation", timestep)
    leading_node = _one_node(upstream["leading_nodes"], "leading confirmation", timestep)
    final_rank_node = _one_node(upstream["final_rank_nodes"], "final rank", timestep)
    selection_node = _one_node(upstream["selection_nodes"], "candidate selection", timestep)
    economic_node = _one_node(upstream["economic_nodes"], "economic evaluation", timestep)

    selected_economic = selection_node.selected_candidate_economic_result
    selected = selected_economic is not None
    evaluation_index = None
    if selected is True:
        evaluation_index = _find_one_based_evaluation_index(
            economic_node.candidate_economic_evaluation_results,
            selected_economic,
            timestep,
        )

    confirmation_source = _classify_confirmation_source(
        plain_key,
        arrived_node,
        leading_node,
        final_rank_node,
        timestep,
    )

    in_arrived = (
        _count_visit_key_hits(arrived_node.confirmed_arrived_visit_keys, plain_key) > 0
    )
    in_leading = (
        _count_visit_key_hits(
            leading_node.confirmed_leading_nonparticipating_visit_keys,
            plain_key,
        )
        > 0
    )
    final_record = None
    in_final = False
    for record in final_rank_node.final_rank_visits:
        if _plain_visit_key(record.visit_key) == plain_key:
            in_final = True
            final_record = record
            break

    final_rank_status = ""
    final_local_rank = None
    finalization_source = ""
    formal_route_next_link_name = ""
    route_origin = ""
    if final_record is not None:
        final_rank_status = final_rank_node.final_rank_status.value
        final_local_rank = final_record.final_local_rank
        finalization_source = final_record.finalization_source.value
        formal_route_next_link_name = final_record.formal_route_next_link_name
        route_origin = final_record.route_origin.value

    vehicle_name, visit_id = plain_key
    participates = _vehicle_participation(world, vehicle_name)

    return {
        "tvt_decision_timestep": timestep,
        "node_name": TARGET_NODE_NAME,
        "vehicle_name": vehicle_name,
        "visit_id": visit_id,
        "visit_key": _visit_text(plain_key),
        "participates_in_order_exchange": participates,
        "selected": selected,
        "selected_candidate_evaluation_index": evaluation_index,
        "assigned_rank_before": assigned_rank_before,
        "assigned_rank_after": assigned_rank_after,
        "newly_confirmed": True,
        "confirmation_source": confirmation_source,
        "in_confirmed_arrived_visit_keys": in_arrived,
        "in_confirmed_leading_nonparticipating_visit_keys": in_leading,
        "in_final_rank_visits": in_final,
        "final_rank_status": final_rank_status,
        "final_local_rank": final_local_rank,
        "finalization_source": finalization_source,
        "formal_route_next_link_name": formal_route_next_link_name,
        "route_origin": route_origin,
        "decision_window_visit_keys": _serialize_visit_keys(
            leading_node.decision_window_visit_keys
        ),
        "remaining_decision_window_visit_keys": _serialize_visit_keys(
            leading_node.remaining_decision_window_visit_keys
        ),
        "confirmed_arrived_visit_keys": _serialize_visit_keys(
            arrived_node.confirmed_arrived_visit_keys
        ),
        "confirmed_leading_nonparticipating_visit_keys": _serialize_visit_keys(
            leading_node.confirmed_leading_nonparticipating_visit_keys
        ),
    }


def _record_driver_decision(
    world,
    timestep: int,
    before_ranks: dict[tuple[str, int], int],
    after_ranks: dict[tuple[str, int], int],
    result: OrderControlTvtMpDriverResult,
) -> None:
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={timestep}: driver result type is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        raise RuntimeError(f"T={timestep}: atomic_apply_set_result is None.")
    upstream = _upstream_from_atomic(atomic, timestep)

    for plain_key, rank_before in before_ranks.items():
        if plain_key not in after_ranks:
            continue
        rank_after = after_ranks[plain_key]
        if rank_after != rank_before:
            raise RuntimeError(
                f"T={timestep}: assigned rank changed for {_visit_text(plain_key)} "
                f"from {rank_before} to {rank_after}."
            )

    for plain_key, rank_after in after_ranks.items():
        if plain_key in before_ranks:
            continue
        if plain_key in GATE.ever_confirmed_keys:
            raise RuntimeError(
                f"T={timestep}: {_visit_text(plain_key)} is newly confirmed again."
            )
        GATE.ever_confirmed_keys.add(plain_key)
        row = _build_row_for_newly_confirmed(
            world,
            timestep,
            plain_key,
            None,
            rank_after,
            upstream,
        )
        GATE.rows.append(row)
        for required in REQUIRED_RUNTIME_VISITS:
            if (
                required["vehicle_name"] == plain_key[0]
                and required["visit_id"] == plain_key[1]
            ):
                GATE.captured_target_keys.add(plain_key)


def _all_required_targets_captured() -> bool:
    required_keys = {
        (item["vehicle_name"], item["visit_id"]) for item in REQUIRED_RUNTIME_VISITS
    }
    return required_keys.issubset(GATE.captured_target_keys)


def wrapped_driver(world):
    diagnostic_real_world = _is_diagnostic_real_world(world) is True
    timestep = world.T
    record_decision = False
    before_ranks = None

    if diagnostic_real_world is True:
        record_decision = (
            type(timestep) is int
            and type(timestep) is not bool
            and ACTUAL_TRACE_START_TIMESTEP <= timestep <= ACTUAL_TRACE_END_TIMESTEP
        )
        if record_decision is True:
            before_ranks = _rank_map(world)

    result = GATE.original_driver(world)

    if diagnostic_real_world is not True:
        return result

    if record_decision is True:
        after_ranks = _rank_map(world)
        _record_driver_decision(world, timestep, before_ranks, after_ranks, result)
        if _all_required_targets_captured() is True:
            GATE.early_stop_timestep = timestep
            raise _StopAfterRankConfirmationTargetsCaptured()

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


def _reset_gate() -> None:
    GATE.rows = []
    GATE.captured_target_keys = set()
    GATE.ever_confirmed_keys = set()
    GATE.early_stop_timestep = None


def _row_for_required_visit(rows: list[dict], required: dict) -> dict:
    vehicle_name = required["vehicle_name"]
    visit_id = required["visit_id"]
    decision_timestep = required["decision_timestep"]
    matches = []
    for row in rows:
        if row.get("vehicle_name") != vehicle_name:
            continue
        if row.get("visit_id") != visit_id:
            continue
        if row.get("tvt_decision_timestep") != decision_timestep:
            continue
        matches.append(row)
    if len(matches) != 1:
        raise RuntimeError(
            f"Required visit {vehicle_name}:{visit_id} at T={decision_timestep} "
            f"has {len(matches)} CSV rows, expected 1."
        )
    return matches[0]


def _validate_runtime(world) -> None:
    for row in GATE.rows:
        plain = (row["vehicle_name"], row["visit_id"])
        if row.get("newly_confirmed") is not True:
            raise RuntimeError(f"{_visit_text(plain)} newly_confirmed is not True.")
        if row.get("confirmation_source") in ("", None):
            raise RuntimeError(f"{_visit_text(plain)} confirmation_source is missing.")

    for required in REQUIRED_RUNTIME_VISITS:
        row = _row_for_required_visit(GATE.rows, required)
        plain = (required["vehicle_name"], required["visit_id"])
        if row.get("assigned_rank_before") is not None:
            raise RuntimeError(
                f"Required visit {_visit_text(plain)} was already confirmed before driver."
            )
        if row.get("assigned_rank_after") != required["assigned_rank"]:
            raise RuntimeError(
                f"Required visit {_visit_text(plain)} assigned rank is "
                f"{row.get('assigned_rank_after')!r}, not {required['assigned_rank']}."
            )
        if row.get("participates_in_order_exchange") is not required[
            "participates_in_order_exchange"
        ]:
            raise RuntimeError(
                f"Required visit {_visit_text(plain)} participates flag differs."
            )
        if row.get("selected") is not False:
            raise RuntimeError(
                f"Required visit {_visit_text(plain)} selected is not False."
            )
        source = row.get("confirmation_source")
        if not isinstance(source, str) or source == "":
            raise RuntimeError(
                f"Required visit {_visit_text(plain)} confirmation_source is not unique."
            )

    if GATE.early_stop_timestep is None:
        raise RuntimeError("Early stop timestep was not recorded.")


def _build_summary() -> str:
    lines = [
        "Rank confirmation sources for northwest_intersection (selected=False, new C rank).",
        f"Trace window: T={ACTUAL_TRACE_START_TIMESTEP}..{ACTUAL_TRACE_END_TIMESTEP}.",
        "",
    ]
    header = (
        "decision_T | visit_key | participates | selected | C_rank | "
        "confirmation_source | final_rank_status | finalization_source"
    )
    lines.append(header)
    for required in REQUIRED_RUNTIME_VISITS:
        row = _row_for_required_visit(GATE.rows, required)
        participates_text = "participating" if row["participates_in_order_exchange"] else "nonparticipating"
        lines.append(
            f"T={row['tvt_decision_timestep']} | {row['visit_key']} | {participates_text} | "
            f"selected={row['selected']} | C{row['assigned_rank_after']} | "
            f"{row['confirmation_source']} | {row['final_rank_status']} | "
            f"{row['finalization_source']}"
        )
    lines.append("")
    lines.append(
        f"Early stop after real driver at T={GATE.early_stop_timestep} "
        "(all required targets recorded)."
    )
    return "\n".join(lines) + "\n"


def _write_outputs() -> None:
    summary_text = _build_summary()
    manifest = {
        "script": str(SCRIPT_PATH.relative_to(REPO_ROOT)),
        "target_node_name": TARGET_NODE_NAME,
        "trace_start_timestep": ACTUAL_TRACE_START_TIMESTEP,
        "trace_end_timestep": ACTUAL_TRACE_END_TIMESTEP,
        "required_runtime_visits": list(REQUIRED_RUNTIME_VISITS),
        "formal_confirmation_source_classifications": list(
            FORMAL_CONFIRMATION_SOURCE_CLASSIFICATIONS
        ),
        "early_stop_timestep": GATE.early_stop_timestep,
        "output_files": list(OUTPUT_FILE_NAMES),
        "row_count": len(GATE.rows),
    }
    _write_csv(OUTPUT_DIR / RANK_CONFIRMATION_SOURCES_CSV, CSV_COLUMNS, GATE.rows)
    (OUTPUT_DIR / SUMMARY_NAME).write_text(summary_text, encoding="utf-8")
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
    _verify_participation_against_trial(world, vot_records)
    world.finalize_scenario()
    return world, vot_records


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

    _reset_gate()
    original_limit = sys.getrecursionlimit()
    stopped = False
    try:
        if OUTPUT_DIR.exists():
            raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
        if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
            raise RuntimeError("Diagnostic output directory is the trial output directory.")
        if original_limit < trial.reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(trial.reference.WORLD_COPY_RECURSION_LIMIT)
        world, _vot_records = _prepare_world()
        install_hooks(world)
        trial.reference.install_real_world_spillback_observation(world)
        try:
            try:
                world.exec_simulation()
            except _StopAfterRankConfirmationTargetsCaptured:
                stopped = True
        finally:
            trial.reference.restore_real_world_spillback_observation()
            restore_hooks()
        if stopped is not True:
            raise RuntimeError(
                "Simulation did not stop early after all required rank confirmations."
            )
        _validate_runtime(world)
        OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
        _write_outputs()
        print(f"Wrote {OUTPUT_DIR}")
        return 0
    finally:
        trial.reference.restore_real_world_spillback_observation()
        restore_hooks()
        sys.setrecursionlimit(original_limit)


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
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = _ast_label(node.targets[0])
        value = _ast_label(node.value)
        if target is None or value is None:
            continue
        pairs.append((target, value))
    return pairs


def _require_assignment(pairs, target, value, label: str) -> None:
    for pair in pairs:
        if pair[0] == target and pair[1] == value:
            return
    raise RuntimeError(f"Static hook binding is missing: {label}.")


def _function_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _restore_returns_when_not_installed(function_node) -> bool:
    if len(function_node.body) == 0:
        return False
    first = function_node.body[0]
    if not isinstance(first, ast.If):
        return False
    test = first.test
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Attribute) or test.left.attr != "installed":
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.IsNot):
        return False
    compared = test.comparators[0]
    if not isinstance(compared, ast.Constant) or compared.value is not True:
        return False
    for statement in first.body:
        if isinstance(statement, ast.Return):
            return True
    return False


def _validate_hook_install_restore(tree) -> None:
    install_node = _function_node(tree, "install_hooks")
    restore_node = _function_node(tree, "restore_hooks")
    if install_node is None or restore_node is None:
        raise RuntimeError("install_hooks or restore_hooks is missing.")
    if _restore_returns_when_not_installed(restore_node) is not True:
        raise RuntimeError("restore_hooks does not return immediately when hooks are not installed.")
    install_pairs = _assignment_pairs(install_node)
    restore_pairs = _assignment_pairs(restore_node)
    bindings = (
        (
            "driver_module.run_tvt_mp_driver",
            "GATE.original_driver",
            "wrapped_driver",
        ),
    )
    for target_name, original_name, wrapper_name in bindings:
        if _function_node(tree, wrapper_name) is None:
            raise RuntimeError(f"Wrapper function {wrapper_name} is missing.")
        _require_assignment(install_pairs, original_name, target_name, f"install saves {target_name}")
        _require_assignment(install_pairs, target_name, wrapper_name, f"install patches {target_name}")
        _require_assignment(restore_pairs, target_name, original_name, f"restore writes back {target_name}")
        _require_assignment(restore_pairs, original_name, "None", f"restore clears {original_name}")


def _wrapped_driver_calls_original_once(tree) -> None:
    wrapper_node = _function_node(tree, "wrapped_driver")
    if wrapper_node is None:
        raise RuntimeError("wrapped_driver is missing.")
    call_count = 0
    for node in ast.walk(wrapper_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "original_driver":
            if isinstance(func.value, ast.Name) and func.value.id == "GATE":
                call_count = call_count + 1
        if isinstance(func, ast.Name) and func.id == "original_driver":
            call_count = call_count + 1
    if call_count != 1:
        raise RuntimeError("wrapped_driver must call GATE.original_driver exactly once.")


def _iterates_world_vehicles_directly(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.For):
            continue
        iter_node = node.iter
        if isinstance(iter_node, ast.Attribute):
            if (
                iter_node.attr == "VEHICLES"
                and isinstance(iter_node.value, ast.Name)
                and iter_node.value.id == "world"
            ):
                return True
    return False


def _function_calls_getattr_for_attribute(
    function_node,
    object_variable_name: str,
    attribute_name: str,
) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "getattr":
            continue
        if len(node.args) < 2:
            continue
        object_arg = node.args[0]
        attribute_arg = node.args[1]
        if not isinstance(object_arg, ast.Name) or object_arg.id != object_variable_name:
            continue
        if not isinstance(attribute_arg, ast.Constant) or attribute_arg.value != attribute_name:
            continue
        return True
    return False


def _function_uses_vehicles_get(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "get":
            continue
        if not isinstance(func.value, ast.Name) or func.value.id != "vehicles":
            continue
        if len(node.args) < 1:
            continue
        key_arg = node.args[0]
        if isinstance(key_arg, ast.Name) and key_arg.id == "vehicle_name":
            return True
    return False


def _function_reads_participates(function_node) -> bool:
    if _function_calls_getattr_for_attribute(
        function_node,
        "vehicle",
        "participates_in_order_exchange",
    ):
        return True
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr != "participates_in_order_exchange":
            continue
        if isinstance(node.value, ast.Name) and node.value.id == "vehicle":
            return True
    return False


def _function_checks_bool_participates(function_node) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        if not isinstance(left, ast.Call):
            continue
        if not isinstance(left.func, ast.Name) or left.func.id != "type":
            continue
        if len(left.args) != 1:
            continue
        if not isinstance(left.args[0], ast.Name) or left.args[0].id != "participates":
            continue
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, ast.IsNot) and isinstance(comparator, ast.Name):
                if comparator.id == "bool":
                    return True
    return False


def _function_gets_vehicles_dict(function_node) -> bool:
    if _function_calls_getattr_for_attribute(function_node, "world", "VEHICLES") is not True:
        return False
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "isinstance":
            continue
        if len(node.args) < 2:
            continue
        value_arg = node.args[0]
        type_arg = node.args[1]
        if isinstance(value_arg, ast.Name) and value_arg.id == "vehicles":
            if isinstance(type_arg, ast.Name) and type_arg.id == "dict":
                return True
    return False


def _validate_vehicle_participation_static(tree) -> None:
    function_node = _function_node(tree, "_vehicle_participation")
    if function_node is None:
        raise RuntimeError("_vehicle_participation is missing.")
    if _iterates_world_vehicles_directly(function_node) is True:
        raise RuntimeError("_vehicle_participation iterates world.VEHICLES directly.")
    if _function_gets_vehicles_dict(function_node) is not True:
        raise RuntimeError("_vehicle_participation does not treat World.VEHICLES as a dict.")
    if _function_uses_vehicles_get(function_node) is not True:
        raise RuntimeError("_vehicle_participation does not use vehicles.get(vehicle_name).")
    if _function_reads_participates(function_node) is not True:
        raise RuntimeError(
            "_vehicle_participation does not read participates_in_order_exchange."
        )
    if _function_checks_bool_participates(function_node) is not True:
        raise RuntimeError("_vehicle_participation does not validate bool participates.")


def _validate_main_stop(tree) -> None:
    main_node = _function_node(tree, "main")
    if main_node is None:
        raise RuntimeError("main is missing.")
    saw_sentinel = False
    for node in ast.walk(main_node):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            raise RuntimeError("main has a bare except.")
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            raise RuntimeError("main catches Exception.")
        if (
            isinstance(node.type, ast.Name)
            and node.type.id == "_StopAfterRankConfirmationTargetsCaptured"
        ):
            saw_sentinel = True
    if saw_sentinel is not True:
        raise RuntimeError("main does not catch _StopAfterRankConfirmationTargetsCaptured.")


def _module_constants(tree):
    strings = set()
    integers = set()
    for body_node in tree.body:
        if isinstance(body_node, ast.Assign):
            value_root = body_node.value
        elif isinstance(body_node, ast.AnnAssign) and body_node.value is not None:
            value_root = body_node.value
        else:
            continue
        for subnode in ast.walk(value_root):
            if not isinstance(subnode, ast.Constant):
                continue
            if isinstance(subnode.value, str):
                strings.add(subnode.value)
            if type(subnode.value) is int and type(subnode.value) is not bool:
                integers.add(subnode.value)
    return strings, integers


def validate_static_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    if OUTPUT_DIR == trial.TRIAL_OUTPUT_DIR:
        raise RuntimeError("Diagnostic output directory equals the trial output directory.")
    strings, integers = _module_constants(tree)
    for text in FORMAL_CONFIRMATION_SOURCE_CLASSIFICATIONS:
        if text not in strings:
            raise RuntimeError(f"Module constants do not include confirmation source {text!r}.")
    if CONFIRMATION_SOURCE_SELECTED_CANDIDATE_FINAL not in strings:
        raise RuntimeError("Module constants do not include selected_candidate_final_rank.")
    for required in REQUIRED_RUNTIME_VISITS:
        if required["vehicle_name"] not in strings:
            raise RuntimeError(f"Module constants do not include {required['vehicle_name']!r}.")
        if required["decision_timestep"] not in integers:
            raise RuntimeError(
                f"Module constants do not include T={required['decision_timestep']}."
            )
        if required["assigned_rank"] not in integers:
            raise RuntimeError(
                f"Module constants do not include rank {required['assigned_rank']}."
            )
    if ACTUAL_TRACE_START_TIMESTEP not in integers or ACTUAL_TRACE_END_TIMESTEP not in integers:
        raise RuntimeError("Trace timestep constants are missing.")
    if TARGET_NODE_NAME not in strings:
        raise RuntimeError("TARGET_NODE_NAME is missing from module constants.")
    for file_name in OUTPUT_FILE_NAMES:
        if file_name not in strings:
            raise RuntimeError(f"OUTPUT_FILE_NAMES must include {file_name!r}.")
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
    for name in ("system", "rmtree", "unlink", "rmdir"):
        if name in called:
            raise RuntimeError(f"Diagnostic calls {name}.")
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    for module_name in imported:
        if module_name in ("subprocess", "shutil", "git"):
            raise RuntimeError(f"Diagnostic imports {module_name}.")
    static_function = _function_node(tree, "validate_static_contract")
    if static_function is None:
        raise RuntimeError("validate_static_contract is missing.")
    for node in ast.walk(static_function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("exec_simulation", "install_hooks", "restore_hooks", "mkdir"):
                raise RuntimeError("Static validation runs the simulation, hooks, or mkdir.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("install_hooks", "restore_hooks", "exec_simulation"):
                raise RuntimeError("Static validation runs the simulation or hooks.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "main" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "trial":
                    raise RuntimeError("Diagnostic calls trial.main.")
    sentinel = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "_StopAfterRankConfirmationTargetsCaptured":
            sentinel = node
    if sentinel is None:
        raise RuntimeError("Diagnostic sentinel exception is missing.")
    if _function_node(tree, "_classify_confirmation_source") is None:
        raise RuntimeError("_classify_confirmation_source is missing.")
    _validate_hook_install_restore(tree)
    _wrapped_driver_calls_original_once(tree)
    _validate_vehicle_participation_static(tree)
    _validate_main_stop(tree)
    print("static contract ok")


if __name__ == "__main__":
    raise SystemExit(main())
