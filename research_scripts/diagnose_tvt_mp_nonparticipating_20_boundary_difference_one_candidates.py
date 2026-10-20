"""
Audit every TVT-MP decision for buyer Baseline A one timestep before
the right-of-entry Baseline P.

Reads the saved driver result only. One row is one concrete buyer
candidate that contains a difference-1 buyer, plus every finally
selected candidate so the selected boundary can be compared.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import uxsim.order_control_tvt_mp_driver as driver_module
from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisit,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    OrderControlTvtMpCandidateSelectionStatus,
    OrderControlTvtNodeMpCandidateSelectionResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_driver import OrderControlTvtMpDriverResult
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtNodeMpFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
)

import run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_nonparticipating_20_trial as nonparticipating_trial


SCENARIO_NAME = nonparticipating_trial.SCENARIO_NAME
TRIAL_SCRIPT_NAME = (
    "run_tvt_mp_two_cross_intersections_downstream_spillback_"
    "extended_south_pulse_nonparticipating_20_trial.py"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_seed_1_nonparticipation_seed_3_"
        "boundary_difference_one_diagnostic"
    )
)
AUDIT_CSV_NAME = "difference_one_candidate_audit.csv"
DECISION_TIMESTEP_START = 0
DECISION_TIMESTEP_END = 599
TARGET_DIFFERENCE = 1

STAGE_NOT_IN_CANDIDATE_VISITS = "no_difference_one_visit_in_candidate_visits"
STAGE_NOT_IN_BUYER_PREFIX = "difference_one_visit_not_in_any_buyer_prefix"
STAGE_CONCRETE_GENERATED = "concrete_candidate_generated"
STAGE_FIFO_FAILED = "fifo_failed"
STAGE_LOCAL_UNRESOLVED = "local_unresolved"
STAGE_ECONOMICALLY_INFEASIBLE = "economically_infeasible"
STAGE_LOWER_SURPLUS = "feasible_but_lower_surplus"
STAGE_LOWER_BUYER_COUNT = "maximum_surplus_but_lower_buyer_count"
STAGE_TIE_NOT_SELECTED = "final_tie_break_not_selected"
STAGE_SELECTED = "selected"
STAGE_UNEXPECTED = "unexpected_or_unresolved"
EXCLUSION_STAGES = (
    STAGE_NOT_IN_CANDIDATE_VISITS,
    STAGE_NOT_IN_BUYER_PREFIX,
    STAGE_CONCRETE_GENERATED,
    STAGE_FIFO_FAILED,
    STAGE_LOCAL_UNRESOLVED,
    STAGE_ECONOMICALLY_INFEASIBLE,
    STAGE_LOWER_SURPLUS,
    STAGE_LOWER_BUYER_COUNT,
    STAGE_TIE_NOT_SELECTED,
    STAGE_SELECTED,
    STAGE_UNEXPECTED,
)

AUDIT_COLUMNS = (
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "right_of_entry_visit_key",
    "right_of_entry_baseline_passage_timestep",
    "buyers_sorted",
    "trade_scope",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "last_buyer_visit_key",
    "last_buyer_baseline_arrival_timestep",
    "passage_minus_last_buyer_arrival",
    "buyer_baseline_arrivals",
    "buyer_passage_minus_arrival",
    "difference_one_buyer_visit_keys",
    "contains_difference_one_buyer",
    "last_buyer_difference_is_one",
    "is_selected_candidate",
    "concrete_candidate_generated",
    "fifo_passed",
    "local_virtual_result_present",
    "local_resolved",
    "unresolved_reasons",
    "economic_result_present",
    "economically_feasible",
    "candidate_infeasibility_reasons",
    "total_G",
    "total_R",
    "surplus",
    "decision_maximum_surplus",
    "is_maximum_surplus_candidate",
    "is_maximum_surplus_maximum_buyer_count",
    "exclusion_stage",
    "selected_transaction_filter",
)


class _Gate:
    def __init__(self) -> None:
        self.installed = False
        self.real_world = None
        self.original_run_tvt_mp_driver = None
        self.rows: list[dict] = []
        self.summary = None


GATE = _Gate()


def _decision_label(node_name: str, timestep: int) -> str:
    return f"T={timestep} {node_name}"


def _plain_visit_key(visit_key) -> tuple:
    if not isinstance(visit_key, tuple) or len(visit_key) != 2:
        raise RuntimeError(f"VisitKey is not a pair: {visit_key!r}.")
    vehicle_name, visit_id = visit_key
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(f"VisitKey vehicle name is {vehicle_name!r}.")
    if type(visit_id) is not int:
        raise RuntimeError(f"VisitKey visit id is {visit_id!r}.")
    return (vehicle_name, visit_id)


def _plain_visit_keys(visit_keys) -> tuple:
    return tuple(_plain_visit_key(visit_key) for visit_key in visit_keys)


def _visit_text(visit_key) -> str:
    vehicle_name, visit_id = visit_key
    return f"{vehicle_name}:{visit_id}"


def _join_visit_keys(visit_keys) -> str:
    return "|".join(_visit_text(visit_key) for visit_key in visit_keys)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _require_one(results, node_name: str, timestep: int, stage_name: str):
    matched = None
    match_count = 0
    for result in results:
        if result.node_name != node_name:
            continue
        match_count = match_count + 1
        matched = result
    if match_count != 1 or matched is None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: {stage_name} has "
            f"{match_count} results."
        )
    return matched


def _saved_driver_columns(atomic):
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
    alignment_set = arrived_set.alignment_fork_result
    fork_result = alignment_set.fork_result
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError(
            "Saved fork_result is not OrderControlBaselineForkResult: "
            f"{type(fork_result).__name__}."
        )
    if not isinstance(fork_result.collector, OrderControlBaselineCollector):
        raise RuntimeError("Saved fork collector is not OrderControlBaselineCollector.")
    return {
        "selection_nodes": selection_set.node_candidate_selection_results,
        "economic_nodes": economic_set.node_economic_evaluation_results,
        "local_nodes": local_set.node_local_virtual_calculation_results,
        "fifo_nodes": fifo_set.node_fifo_inspection_results,
        "trade_rank_nodes": trade_rank_set.node_trade_rank_results,
        "concrete_nodes": concrete_set.node_concrete_buyer_candidate_set_results,
        "inlink_nodes": inlink_order_set.node_inlink_candidate_physical_order_results,
        "candidate_visit_nodes": candidate_visit_set.node_candidate_set_results,
        "right_of_entry_nodes": right_of_entry_set.node_selection_results,
    }


def _max_participating_prefix(visit_keys, participates_by_visit) -> tuple:
    prefix = []
    for visit_key in visit_keys:
        if participates_by_visit[visit_key] is True:
            prefix.append(visit_key)
            continue
        break
    return tuple(prefix)


def _reason_not_in_buyer_prefix(visit_key, roe_inlink, inlink_orders, participates_by_visit) -> str:
    for inlink_order in inlink_orders:
        ordered = _plain_visit_keys(inlink_order.candidate_visit_keys_head_to_tail)
        if visit_key not in ordered:
            continue
        if inlink_order.inlink_name == roe_inlink:
            return "on_right_of_entry_inlink"
        if participates_by_visit[visit_key] is not True:
            return "nonparticipating_visit"
        prefix = _max_participating_prefix(ordered, participates_by_visit)
        if visit_key not in prefix:
            return "behind_nonparticipating_on_inlink"
        return "in_participating_prefix_but_not_in_concrete_candidate"
    return "not_in_saved_inlink_physical_order"


def _align_concrete_candidates(concrete_node, trade_node, fifo_node, node_name, timestep):
    concrete_sets = concrete_node.concrete_buyer_candidate_sets
    trade_results = trade_node.candidate_trade_rank_results
    fifo_results = fifo_node.candidate_fifo_inspection_results
    if len(concrete_sets) != len(trade_results) or len(concrete_sets) != len(fifo_results):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: concrete, trade-rank, and "
            "FIFO counts differ."
        )
    aligned = []
    seen = set()
    for stored_index, concrete_set in enumerate(concrete_sets):
        if not isinstance(concrete_set, OrderControlTvtMpConcreteBuyerCandidateSet):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: concrete set is "
                f"{type(concrete_set).__name__}."
            )
        trade_result = trade_results[stored_index]
        fifo_result = fifo_results[stored_index]
        if not isinstance(trade_result, OrderControlTvtMpGeneralTradeRankResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade result is "
                f"{type(trade_result).__name__}."
            )
        if not isinstance(fifo_result, OrderControlTvtMpCandidateFifoInspectionResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result is "
                f"{type(fifo_result).__name__}."
            )
        if trade_result.concrete_buyer_candidate_set is not concrete_set:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade rank does not "
                "reference the concrete set at the same index."
            )
        if fifo_result.general_trade_rank_result is not trade_result:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO result does not "
                "reference the trade rank at the same index."
            )
        buyers = _plain_visit_keys(concrete_set.buyers_sorted)
        if _plain_visit_keys(trade_result.buyers_sorted) != buyers:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: trade-rank buyers differ "
                "from the concrete buyer set."
            )
        if buyers in seen:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate concrete buyers."
            )
        seen.add(buyers)
        if type(fifo_result.preserves_inlink_fifo) is not bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: preserves_inlink_fifo "
                f"is {fifo_result.preserves_inlink_fifo!r}."
            )
        aligned.append(
            {
                "concrete_set": concrete_set,
                "trade_result": trade_result,
                "fifo_passed": fifo_result.preserves_inlink_fifo,
                "buyers": buyers,
                "sellers": _plain_visit_keys(trade_result.sellers_sorted),
                "nonparticipating": _plain_visit_keys(
                    trade_result.nonparticipating_visits_sorted
                ),
                "trade_scope": _plain_visit_keys(trade_result.trade_scope),
            }
        )
    return aligned


def _results_by_buyers(results, node_name, timestep, result_name, buyers_getter):
    mapping = {}
    for result in results:
        buyers = buyers_getter(result)
        if buyers in mapping:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: duplicate {result_name} "
                f"for {_join_visit_keys(buyers)}."
            )
        mapping[buyers] = result
    return mapping


def _local_buyers(local_result):
    return _plain_visit_keys(local_result.concrete_buyer_candidate_set.buyers_sorted)


def _economic_buyers(economic_result):
    local_result = economic_result.candidate_local_virtual_calculation_result
    return _local_buyers(local_result)


def _selection_flags(feasible_entries, buyers, surplus, buyer_count):
    if surplus is None:
        return False, False, None
    maximum_surplus = None
    for entry in feasible_entries:
        if maximum_surplus is None or entry["surplus"] > maximum_surplus:
            maximum_surplus = entry["surplus"]
    is_maximum_surplus = surplus == maximum_surplus
    maximum_buyer_count = None
    for entry in feasible_entries:
        if entry["surplus"] != maximum_surplus:
            continue
        if maximum_buyer_count is None or entry["buyer_count"] > maximum_buyer_count:
            maximum_buyer_count = entry["buyer_count"]
    is_maximum_buyer_count = (
        is_maximum_surplus is True and buyer_count == maximum_buyer_count
    )
    return is_maximum_surplus, is_maximum_buyer_count, maximum_surplus


def _exclusion_stage(
    contains_difference_one,
    fifo_passed,
    local_present,
    local_resolved,
    economic_present,
    economically_feasible,
    is_maximum_surplus,
    is_maximum_buyer_count,
    is_selected,
) -> str:
    if contains_difference_one is not True:
        if is_selected is True:
            return STAGE_NOT_IN_CANDIDATE_VISITS
        return STAGE_UNEXPECTED
    if fifo_passed is not True:
        return STAGE_FIFO_FAILED
    if local_present is not True or local_resolved is None:
        return STAGE_UNEXPECTED
    if local_resolved is not True:
        return STAGE_LOCAL_UNRESOLVED
    if economic_present is not True or economically_feasible is None:
        return STAGE_UNEXPECTED
    if economically_feasible is not True:
        return STAGE_ECONOMICALLY_INFEASIBLE
    if is_selected is True:
        return STAGE_SELECTED
    if is_maximum_surplus is not True:
        return STAGE_LOWER_SURPLUS
    if is_maximum_buyer_count is not True:
        return STAGE_LOWER_BUYER_COUNT
    return STAGE_TIE_NOT_SELECTED


def _audit_node(world, columns, node_name: str, timestep: int) -> dict:
    if timestep < DECISION_TIMESTEP_START or timestep > DECISION_TIMESTEP_END:
        raise RuntimeError(f"{_decision_label(node_name, timestep)} is outside 0..599.")
    candidate_visit_node = _require_one(
        columns["candidate_visit_nodes"], node_name, timestep, "candidate visits"
    )
    if not isinstance(candidate_visit_node, OrderControlTvtNodeCandidateVisitSetResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: candidate visit node type is "
            f"{type(candidate_visit_node).__name__}."
        )
    right_of_entry_node = _require_one(
        columns["right_of_entry_nodes"], node_name, timestep, "right of entry"
    )
    if not isinstance(right_of_entry_node, OrderControlTvtNodeRightOfEntrySelectionResult):
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry type is "
            f"{type(right_of_entry_node).__name__}."
        )
    concrete_node = _require_one(
        columns["concrete_nodes"], node_name, timestep, "concrete candidates"
    )
    trade_node = _require_one(
        columns["trade_rank_nodes"], node_name, timestep, "trade rank"
    )
    fifo_node = _require_one(columns["fifo_nodes"], node_name, timestep, "fifo")
    local_node = _require_one(
        columns["local_nodes"], node_name, timestep, "local virtual calculation"
    )
    economic_node = _require_one(
        columns["economic_nodes"], node_name, timestep, "economic evaluation"
    )
    selection_node = _require_one(
        columns["selection_nodes"], node_name, timestep, "candidate selection"
    )
    inlink_node = _require_one(
        columns["inlink_nodes"], node_name, timestep, "inlink physical order"
    )
    for node_result, expected_type in (
        (concrete_node, OrderControlTvtNodeMpConcreteBuyerCandidateSetResult),
        (trade_node, OrderControlTvtNodeMpGeneralTradeRankResult),
        (fifo_node, OrderControlTvtNodeMpFifoInspectionResult),
        (local_node, OrderControlTvtNodeMpLocalVirtualCalculationResult),
        (economic_node, OrderControlTvtNodeMpEconomicEvaluationResult),
        (selection_node, OrderControlTvtNodeMpCandidateSelectionResult),
    ):
        if not isinstance(node_result, expected_type):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: expected "
                f"{expected_type.__name__}, got {type(node_result).__name__}."
            )
    passage = candidate_visit_node.right_of_entry_baseline_passage_timestep
    right_key = right_of_entry_node.right_of_entry_visit_key
    if right_key is None:
        right_key_plain = None
    else:
        right_key_plain = _plain_visit_key(right_key)
    visits = {}
    participates_by_visit = {}
    for candidate_visit in candidate_visit_node.candidate_visits:
        if not isinstance(candidate_visit, OrderControlTvtCandidateVisit):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate visit is "
                f"{type(candidate_visit).__name__}."
            )
        visit_key = _plain_visit_key(candidate_visit.visit_key)
        if visit_key in visits:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: candidate_visits repeats "
                f"{_visit_text(visit_key)}."
            )
        vehicle = world.VEHICLES[visit_key[0]]
        participates = vehicle.participates_in_order_exchange
        if type(participates) is not bool:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: participation for "
                f"{_visit_text(visit_key)} is {participates!r}."
            )
        visits[visit_key] = candidate_visit
        participates_by_visit[visit_key] = participates
    if right_key_plain is not None and right_key_plain not in visits:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: right-of-entry is not in "
            "candidate_visits."
        )
    if type(passage) is int and right_key_plain is not None:
        saved_passage = visits[right_key_plain].baseline_passage_timestep
        if saved_passage != passage:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: right-of-entry passage "
                f"{passage} differs from candidate visit passage {saved_passage}."
            )
    difference_by_visit = {}
    if type(passage) is int:
        for visit_key, candidate_visit in visits.items():
            arrival = candidate_visit.baseline_arrival_timestep
            if type(arrival) is not int:
                continue
            difference_by_visit[visit_key] = passage - arrival
    difference_one_visits = tuple(
        visit_key
        for visit_key, difference in difference_by_visit.items()
        if difference == TARGET_DIFFERENCE
    )
    aligned = _align_concrete_candidates(
        concrete_node, trade_node, fifo_node, node_name, timestep
    )
    local_by_buyers = _results_by_buyers(
        local_node.candidate_local_virtual_calculation_results,
        node_name,
        timestep,
        "local result",
        _local_buyers,
    )
    economic_by_buyers = _results_by_buyers(
        economic_node.candidate_economic_evaluation_results,
        node_name,
        timestep,
        "economic result",
        _economic_buyers,
    )
    for buyers, local_result in local_by_buyers.items():
        if not isinstance(local_result, OrderControlTvtMpCandidateLocalVirtualCalculationResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result type is "
                f"{type(local_result).__name__}."
            )
        if local_result.node_name != node_name or local_result.baseline_timestep_T != timestep:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result identity "
                "does not match the decision."
            )
        matched = None
        for item in aligned:
            if item["buyers"] == buyers:
                matched = item
        if matched is None or local_result.concrete_buyer_candidate_set is not matched["concrete_set"]:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: local result does not "
                "reference the concrete candidate."
            )
        if matched["fifo_passed"] is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: FIFO-failed candidate "
                "has a local result."
            )
    for buyers, economic_result in economic_by_buyers.items():
        if not isinstance(economic_result, OrderControlTvtMpCandidateEconomicEvaluationResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic result type is "
                f"{type(economic_result).__name__}."
            )
        local_result = economic_result.candidate_local_virtual_calculation_result
        if local_by_buyers.get(buyers) is not local_result:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: economic result does not "
                "reference the saved local result."
            )
        if local_result.resolved is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: unresolved local result "
                "has an economic result."
            )
    selected_buyers = None
    selected_economic = selection_node.selected_candidate_economic_result
    if selection_node.selection_status is OrderControlTvtMpCandidateSelectionStatus.SELECTED:
        if not isinstance(selected_economic, OrderControlTvtMpCandidateEconomicEvaluationResult):
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected result type is "
                f"{type(selected_economic).__name__}."
            )
        if selected_economic.economically_feasible is not True:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected candidate is "
                "not economically feasible."
            )
        selected_local = selected_economic.candidate_local_virtual_calculation_result
        selected_buyers = _local_buyers(selected_local)
        if local_by_buyers.get(selected_buyers) is not selected_local:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected local result "
                "is not the saved local result."
            )
        if economic_by_buyers.get(selected_buyers) is not selected_economic:
            raise RuntimeError(
                f"{_decision_label(node_name, timestep)}: selected economic result "
                "is not the saved economic result."
            )
    elif selected_economic is not None:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: selection status is "
            f"{selection_node.selection_status!r} but a selected result exists."
        )
    feasible_entries = []
    for buyers, economic_result in economic_by_buyers.items():
        if economic_result.economically_feasible is True:
            feasible_entries.append(
                {
                    "buyers": buyers,
                    "surplus": economic_result.surplus,
                    "buyer_count": len(buyers),
                }
            )
    expected_buyer_keys = set()
    roe_inlink = None
    if right_key_plain is not None:
        roe_inlink = visits[right_key_plain].inlink_name
    for inlink_order in inlink_node.inlink_candidate_physical_orders:
        ordered = _plain_visit_keys(inlink_order.candidate_visit_keys_head_to_tail)
        for visit_key in ordered:
            if visit_key not in participates_by_visit:
                raise RuntimeError(
                    f"{_decision_label(node_name, timestep)}: inlink physical order "
                    f"contains {_visit_text(visit_key)} outside candidate_visits."
                )
        if roe_inlink is not None and inlink_order.inlink_name == roe_inlink:
            continue
        for visit_key in _max_participating_prefix(ordered, participates_by_visit):
            expected_buyer_keys.add(visit_key)
    actual_buyer_keys = set()
    for item in aligned:
        for visit_key in item["buyers"]:
            actual_buyer_keys.add(visit_key)
    if expected_buyer_keys != actual_buyer_keys:
        raise RuntimeError(
            f"{_decision_label(node_name, timestep)}: concrete buyer visits do "
            "not match the saved participating inlink prefixes."
        )
    prefix_misses = []
    for visit_key in difference_one_visits:
        if visit_key in actual_buyer_keys:
            continue
        prefix_misses.append(
            {
                "visit_key": visit_key,
                "reason": _reason_not_in_buyer_prefix(
                    visit_key,
                    roe_inlink,
                    inlink_node.inlink_candidate_physical_orders,
                    participates_by_visit,
                ),
            }
        )
    rows = []
    for item in aligned:
        buyers = item["buyers"]
        local_result = local_by_buyers.get(buyers)
        economic_result = economic_by_buyers.get(buyers)
        local_present = local_result is not None
        local_resolved = None
        unresolved_reasons = ""
        if local_present is True:
            local_resolved = local_result.resolved
            unresolved_reasons = "|".join(
                reason.value for reason in local_result.unresolved_reasons
            )
        economic_present = economic_result is not None
        economically_feasible = None
        infeasibility = ""
        total_g = None
        total_r = None
        surplus = None
        if economic_present is True:
            economically_feasible = economic_result.economically_feasible
            infeasibility = "|".join(
                reason.value for reason in economic_result.infeasibility_reasons
            )
            total_g = economic_result.total_buyer_value_G
            total_r = economic_result.total_required_compensation_R
            surplus = economic_result.surplus
        is_maximum_surplus = False
        is_maximum_buyer_count = False
        maximum_surplus = None
        if economically_feasible is True:
            is_maximum_surplus, is_maximum_buyer_count, maximum_surplus = _selection_flags(
                feasible_entries,
                buyers,
                surplus,
                len(buyers),
            )
        is_selected = selected_buyers == buyers
        difference_one_buyers = tuple(
            visit_key
            for visit_key in buyers
            if difference_by_visit.get(visit_key) == TARGET_DIFFERENCE
        )
        contains_difference_one = len(difference_one_buyers) > 0
        last_buyer = buyers[-1]
        last_arrival = visits[last_buyer].baseline_arrival_timestep
        if type(passage) is int and type(last_arrival) is int:
            last_difference = passage - last_arrival
        else:
            last_difference = None
        if contains_difference_one is not True and is_selected is not True:
            continue
        arrival_text = []
        difference_text = []
        for visit_key in buyers:
            arrival = visits[visit_key].baseline_arrival_timestep
            arrival_text.append(f"{_visit_text(visit_key)}={arrival}")
            if type(passage) is int and type(arrival) is int:
                difference_text.append(f"{_visit_text(visit_key)}={passage - arrival}")
        selected_filter = False
        if is_selected is True:
            selected_filter = (
                len(item["nonparticipating"]) >= 1
                or len(buyers) >= 2
                or len(item["sellers"]) >= 2
            )
        rows.append(
            {
                "scenario_name": SCENARIO_NAME,
                "tvt_decision_timestep": timestep,
                "node_name": node_name,
                "right_of_entry_visit_key": None if right_key_plain is None else _visit_text(right_key_plain),
                "right_of_entry_baseline_passage_timestep": passage,
                "buyers_sorted": _join_visit_keys(buyers),
                "trade_scope": _join_visit_keys(item["trade_scope"]),
                "sellers_sorted": _join_visit_keys(item["sellers"]),
                "nonparticipating_visits_sorted": _join_visit_keys(item["nonparticipating"]),
                "last_buyer_visit_key": _visit_text(last_buyer),
                "last_buyer_baseline_arrival_timestep": last_arrival,
                "passage_minus_last_buyer_arrival": last_difference,
                "buyer_baseline_arrivals": "|".join(arrival_text),
                "buyer_passage_minus_arrival": "|".join(difference_text),
                "difference_one_buyer_visit_keys": _join_visit_keys(difference_one_buyers),
                "contains_difference_one_buyer": contains_difference_one,
                "last_buyer_difference_is_one": last_difference == TARGET_DIFFERENCE,
                "is_selected_candidate": is_selected,
                "concrete_candidate_generated": True,
                "fifo_passed": item["fifo_passed"],
                "local_virtual_result_present": local_present,
                "local_resolved": local_resolved,
                "unresolved_reasons": unresolved_reasons,
                "economic_result_present": economic_present,
                "economically_feasible": economically_feasible,
                "candidate_infeasibility_reasons": infeasibility,
                "total_G": total_g,
                "total_R": total_r,
                "surplus": surplus,
                "decision_maximum_surplus": maximum_surplus,
                "is_maximum_surplus_candidate": is_maximum_surplus,
                "is_maximum_surplus_maximum_buyer_count": is_maximum_buyer_count,
                "exclusion_stage": _exclusion_stage(
                    contains_difference_one,
                    item["fifo_passed"],
                    local_present,
                    local_resolved,
                    economic_present,
                    economically_feasible,
                    is_maximum_surplus,
                    is_maximum_buyer_count,
                    is_selected,
                ),
                "selected_transaction_filter": selected_filter,
                "buyer_count": len(buyers),
                "seller_count": len(item["sellers"]),
                "nonparticipating_count": len(item["nonparticipating"]),
            }
        )
    return {
        "difference_one_visit_count": len(difference_one_visits),
        "difference_one_buyer_visit_count": len(
            tuple(visit_key for visit_key in difference_one_visits if visit_key in actual_buyer_keys)
        ),
        "difference_one_selected_last_buyer_count": len(
            tuple(
                visit_key
                for visit_key in difference_one_visits
                if selected_buyers is not None
                and len(selected_buyers) > 0
                and selected_buyers[-1] == visit_key
            )
        ),
        "prefix_misses": prefix_misses,
        "rows": rows,
        "candidate_visit_count": len(visits),
        "concrete_candidate_count": len(aligned),
    }


def _observe_driver_result(world, result) -> None:
    timestep = world.T
    if type(timestep) is not int:
        raise RuntimeError(f"Driver World.T is {timestep!r}.")
    if timestep < DECISION_TIMESTEP_START or timestep > DECISION_TIMESTEP_END:
        return
    if not isinstance(result, OrderControlTvtMpDriverResult):
        raise RuntimeError(f"T={timestep}: driver result is {type(result).__name__}.")
    atomic = result.atomic_apply_set_result
    if atomic is None:
        return
    columns = _saved_driver_columns(atomic)
    for candidate_visit_node in columns["candidate_visit_nodes"]:
        if len(candidate_visit_node.candidate_visits) == 0:
            continue
        audited = _audit_node(world, columns, candidate_visit_node.node_name, timestep)
        GATE.summary["decisions_with_candidate_visits"] += 1
        GATE.summary["difference_one_visits_in_candidate_visits"] += audited[
            "difference_one_visit_count"
        ]
        GATE.summary["difference_one_visits_in_concrete_buyers"] += audited[
            "difference_one_buyer_visit_count"
        ]
        GATE.summary["difference_one_selected_last_buyers"] += audited[
            "difference_one_selected_last_buyer_count"
        ]
        for miss in audited["prefix_misses"]:
            reason = miss["reason"]
            reasons = GATE.summary["prefix_miss_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
            if reason == "in_participating_prefix_but_not_in_concrete_candidate":
                GATE.summary["unexpected_prefix_misses"].append(
                    {
                        "tvt_decision_timestep": timestep,
                        "node_name": candidate_visit_node.node_name,
                        "visit_key": _visit_text(miss["visit_key"]),
                    }
                )
            elif len(GATE.summary["prefix_miss_examples"]) < 8:
                GATE.summary["prefix_miss_examples"].append(
                    {
                        "tvt_decision_timestep": timestep,
                        "node_name": candidate_visit_node.node_name,
                        "visit_key": _visit_text(miss["visit_key"]),
                        "reason": reason,
                    }
                )
        GATE.rows.extend(audited["rows"])


def wrapped_run_tvt_mp_driver(world):
    result = GATE.original_run_tvt_mp_driver(world)
    if world is not GATE.real_world:
        return result
    _observe_driver_result(world, result)
    return result


def install_observation_hook(real_world) -> None:
    if GATE.installed is True:
        raise RuntimeError("Observation hook is already installed.")
    GATE.real_world = real_world
    GATE.original_run_tvt_mp_driver = driver_module.run_tvt_mp_driver
    driver_module.run_tvt_mp_driver = wrapped_run_tvt_mp_driver
    GATE.installed = True


def restore_observation_hook() -> None:
    if GATE.installed is not True:
        return
    driver_module.run_tvt_mp_driver = GATE.original_run_tvt_mp_driver
    GATE.original_run_tvt_mp_driver = None
    GATE.real_world = None
    GATE.installed = False


def _empty_summary() -> dict:
    return {
        "decisions_with_candidate_visits": 0,
        "difference_one_visits_in_candidate_visits": 0,
        "difference_one_visits_in_concrete_buyers": 0,
        "difference_one_selected_last_buyers": 0,
        "prefix_miss_reasons": {},
        "prefix_miss_examples": [],
        "unexpected_prefix_misses": [],
    }


def _prepare_world():
    reference = nonparticipating_trial.reference
    reference.SPILLBACK_TIMESTEP_ROWS.clear()
    vot_values = nonparticipating_trial._true_vot_sequence()
    vot_records = reference.build_vehicle_vot_records(
        nonparticipating_trial.VEHICLE_SPECS,
        vot_values,
    )
    world = nonparticipating_trial.build_world()
    reference.add_vehicles_to_world(world, nonparticipating_trial.VEHICLE_SPECS, vot_records)
    world.finalize_scenario()
    return world


def _write_csv(rows) -> None:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory already exists: {OUTPUT_DIR}.")
    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    path = OUTPUT_DIR / AUDIT_CSV_NAME
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row[column]) for column in AUDIT_COLUMNS})
    for path_item in OUTPUT_DIR.iterdir():
        if path_item.name != AUDIT_CSV_NAME:
            raise RuntimeError(f"Unexpected file in output directory: {path_item.name}.")


def _count_rows(rows) -> dict:
    counts = {stage: 0 for stage in EXCLUSION_STAGES}
    counts["difference_one_concrete_candidates"] = 0
    counts["difference_one_fifo_passed"] = 0
    counts["difference_one_local_resolved"] = 0
    counts["difference_one_economically_feasible"] = 0
    counts["difference_one_maximum_surplus"] = 0
    counts["difference_one_final_selected"] = 0
    counts["selected_candidates"] = 0
    counts["selected_filter_candidates"] = 0
    last_buyer_differences = {}
    filter_last_buyer_differences = {}
    for row in rows:
        if row["contains_difference_one_buyer"] is True:
            counts["difference_one_concrete_candidates"] += 1
            counts[row["exclusion_stage"]] += 1
            if row["fifo_passed"] is True:
                counts["difference_one_fifo_passed"] += 1
            if row["local_resolved"] is True:
                counts["difference_one_local_resolved"] += 1
            if row["economically_feasible"] is True:
                counts["difference_one_economically_feasible"] += 1
            if row["is_maximum_surplus_candidate"] is True:
                counts["difference_one_maximum_surplus"] += 1
            if row["is_selected_candidate"] is True:
                counts["difference_one_final_selected"] += 1
        if row["is_selected_candidate"] is True:
            counts["selected_candidates"] += 1
            difference = row["passage_minus_last_buyer_arrival"]
            last_buyer_differences[difference] = last_buyer_differences.get(difference, 0) + 1
            if row["selected_transaction_filter"] is True:
                counts["selected_filter_candidates"] += 1
                filter_last_buyer_differences[difference] = (
                    filter_last_buyer_differences.get(difference, 0) + 1
                )
    counts["last_buyer_differences"] = last_buyer_differences
    counts["filter_last_buyer_differences"] = filter_last_buyer_differences
    return counts


def _conclusion_code(summary, counts) -> str:
    if len(summary["unexpected_prefix_misses"]) > 0 or counts[STAGE_UNEXPECTED] > 0:
        return "F"
    if summary["difference_one_visits_in_candidate_visits"] == 0:
        return "A"
    if counts["difference_one_final_selected"] > 0 or summary["difference_one_selected_last_buyers"] > 0:
        return "E"
    if (
        counts[STAGE_LOWER_SURPLUS] > 0
        or counts[STAGE_LOWER_BUYER_COUNT] > 0
        or counts[STAGE_TIE_NOT_SELECTED] > 0
    ):
        return "D"
    if counts["difference_one_concrete_candidates"] > 0:
        return "C"
    if summary["difference_one_visits_in_candidate_visits"] > 0:
        return "B"
    return "A"


def _print_report(summary, counts, rows) -> None:
    code = _conclusion_code(summary, counts)
    print(f"conclusion_code: {code}")
    print(
        "difference_one_visits_in_candidate_visits: "
        f"{summary['difference_one_visits_in_candidate_visits']}"
    )
    print(
        "difference_one_visits_in_concrete_buyers: "
        f"{summary['difference_one_visits_in_concrete_buyers']}"
    )
    print(
        "difference_one_selected_last_buyers: "
        f"{summary['difference_one_selected_last_buyers']}"
    )
    print(
        "difference_one_concrete_candidates: "
        f"{counts['difference_one_concrete_candidates']}"
    )
    print(f"difference_one_fifo_passed: {counts['difference_one_fifo_passed']}")
    print(f"difference_one_local_resolved: {counts['difference_one_local_resolved']}")
    print(
        "difference_one_economically_feasible: "
        f"{counts['difference_one_economically_feasible']}"
    )
    print(f"difference_one_maximum_surplus: {counts['difference_one_maximum_surplus']}")
    print(f"difference_one_final_selected: {counts['difference_one_final_selected']}")
    for stage in EXCLUSION_STAGES:
        print(f"exclusion_stage {stage}: {counts[stage]}")
    print(f"selected_candidates: {counts['selected_candidates']}")
    print(f"selected_filter_candidates: {counts['selected_filter_candidates']}")
    print(f"selected_last_buyer_differences: {counts['last_buyer_differences']}")
    print(
        "selected_filter_last_buyer_differences: "
        f"{counts['filter_last_buyer_differences']}"
    )
    print(f"prefix_miss_reasons: {summary['prefix_miss_reasons']}")
    print(f"decisions_with_candidate_visits: {summary['decisions_with_candidate_visits']}")
    print(f"audit_rows: {len(rows)}")
    for example in summary["prefix_miss_examples"]:
        print(
            "prefix_miss_example: "
            f"T={example['tvt_decision_timestep']} Node={example['node_name']} "
            f"VisitKey={example['visit_key']} reason={example['reason']}"
        )
    shown = {stage: 0 for stage in EXCLUSION_STAGES}
    for row in rows:
        if row["contains_difference_one_buyer"] is not True:
            continue
        stage = row["exclusion_stage"]
        if shown[stage] >= 3:
            continue
        shown[stage] = shown[stage] + 1
        print(
            "difference_one_example: "
            f"T={row['tvt_decision_timestep']} Node={row['node_name']} "
            f"VisitKey={row['difference_one_buyer_visit_keys']} "
            f"P={row['right_of_entry_baseline_passage_timestep']} "
            f"A={row['buyer_baseline_arrivals']} surplus={row['surplus']} "
            f"stage={stage}"
        )


def main() -> int:
    reference = nonparticipating_trial.reference
    original_recursion_limit = sys.getrecursionlimit()
    GATE.rows = []
    GATE.summary = _empty_summary()
    try:
        if original_recursion_limit < reference.WORLD_COPY_RECURSION_LIMIT:
            sys.setrecursionlimit(reference.WORLD_COPY_RECURSION_LIMIT)
        world = _prepare_world()
        install_observation_hook(world)
        reference.install_real_world_spillback_observation(world)
        try:
            world.exec_simulation()
        finally:
            reference.restore_real_world_spillback_observation()
            restore_observation_hook()
        counts = _count_rows(GATE.rows)
        _print_report(GATE.summary, counts, GATE.rows)
        _write_csv(GATE.rows)
        print(f"output_csv: {OUTPUT_DIR / AUDIT_CSV_NAME}")
        return 0
    finally:
        reference.restore_real_world_spillback_observation()
        restore_observation_hook()
        sys.setrecursionlimit(original_recursion_limit)


def _function_by_name(tree, name: str):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Function {name} is missing.")


def _call_names(function_node) -> list[str]:
    names = []
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def validate_static_contract() -> None:
    if SCENARIO_NAME != (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_nonparticipating_20_trial"
    ):
        raise RuntimeError("Scenario name does not match.")
    if not (SCRIPT_DIR / TRIAL_SCRIPT_NAME).is_file():
        raise RuntimeError("Target trial script is missing.")
    if DECISION_TIMESTEP_START != 0 or DECISION_TIMESTEP_END != 599:
        raise RuntimeError("Decision window is not T=0 through T=599.")
    if TARGET_DIFFERENCE != 1:
        raise RuntimeError("Target difference is not 1.")
    if AUDIT_CSV_NAME != "difference_one_candidate_audit.csv":
        raise RuntimeError("Audit CSV name does not match.")
    if "boundary_difference_one_diagnostic" not in OUTPUT_DIR.name:
        raise RuntimeError("Output directory name does not match.")
    for column in (
        "contains_difference_one_buyer",
        "last_buyer_difference_is_one",
        "is_selected_candidate",
        "right_of_entry_baseline_passage_timestep",
        "passage_minus_last_buyer_arrival",
        "exclusion_stage",
        "surplus",
        "decision_maximum_surplus",
    ):
        if column not in AUDIT_COLUMNS:
            raise RuntimeError(f"Audit CSV is missing {column}.")
    for stage in EXCLUSION_STAGES:
        if stage not in (
            "no_difference_one_visit_in_candidate_visits",
            "difference_one_visit_not_in_any_buyer_prefix",
            "concrete_candidate_generated",
            "fifo_failed",
            "local_unresolved",
            "economically_infeasible",
            "feasible_but_lower_surplus",
            "maximum_surplus_but_lower_buyer_count",
            "final_tie_break_not_selected",
            "selected",
            "unexpected_or_unresolved",
        ):
            raise RuntimeError(f"Unexpected exclusion stage {stage}.")
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    validator = _function_by_name(tree, "validate_static_contract")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id.startswith("EAST_T35"):
            raise RuntimeError("The fixed east T=35 audit contract was imported.")
    if "exec_simulation" in _call_names(validator) or "main" in _call_names(validator):
        raise RuntimeError("Static validation must not start the simulation.")
    wrapper = _function_by_name(tree, "wrapped_run_tvt_mp_driver")
    if _call_names(wrapper).count("original_run_tvt_mp_driver") != 1:
        raise RuntimeError("Driver wrapper must call the original function once.")
    returns_result = False
    for node in ast.walk(wrapper):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            if node.value.id == "result":
                returns_result = True
    if returns_result is not True:
        raise RuntimeError("Driver wrapper does not return the original result.")
    main_function = _function_by_name(tree, "main")
    restores = False
    for node in ast.walk(main_function):
        if not isinstance(node, ast.Try):
            continue
        for final_node in node.finalbody:
            for child in ast.walk(final_node):
                if isinstance(child, ast.Name) and child.id == "restore_observation_hook":
                    restores = True
    if restores is not True:
        raise RuntimeError("Hook is not restored in finally.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "copy":
            raise RuntimeError("Diagnostic source calls copy.")
        if isinstance(node, ast.Name) and node.id == "random":
            raise RuntimeError("Diagnostic source uses random.")
    if "passage - arrival" not in source:
        raise RuntimeError("Difference is not right-of-entry passage minus buyer arrival.")
    if "contains_difference_one is not True and is_selected is not True" not in source:
        raise RuntimeError("Selected candidates are not retained beside difference-1 candidates.")
    if "OUTPUT_DIR.exists()" not in source:
        raise RuntimeError("Existing output directory is not refused.")
    if _conclusion_code(
        {
            "unexpected_prefix_misses": [],
            "difference_one_visits_in_candidate_visits": 0,
            "difference_one_selected_last_buyers": 0,
        },
        {STAGE_UNEXPECTED: 0},
    ) != "A":
        raise RuntimeError("Conclusion A is not recognized.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--static-validate-only":
        validate_static_contract()
        print("Static contract validation passed.")
    else:
        raise SystemExit(main())
