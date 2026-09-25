"""
TVT-MP selection of at most one economically feasible candidate per Node.

This module reads saved economic-evaluation results and, for each target
Node, keeps economically feasible candidates, then the maximum surplus,
then the maximum buyer count. Only a final tie of two or more candidates
uses a local temporary RNG. It does not recompute economics, does not
compute payment or compensation, and does not change the real World or
the existing World RNG objects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    OrderControlTvtMpCandidateEconomicEvaluationResult,
    OrderControlTvtMpEconomicEvaluationSetResult,
    OrderControlTvtNodeMpEconomicEvaluationResult,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtVisitKey
from uxsim.uxsim import World


class OrderControlTvtMpCandidateSelectionStatus(Enum):
    """Outcome of candidate selection for one target Node."""

    SELECTED = "selected"
    NO_ECONOMICALLY_FEASIBLE_CANDIDATE = "no_economically_feasible_candidate"


@dataclass(frozen=True)
class OrderControlTvtNodeMpCandidateSelectionResult:
    """Selection outcome for one target Node."""

    node_name: str
    selection_status: OrderControlTvtMpCandidateSelectionStatus
    selected_candidate_economic_result: (
        OrderControlTvtMpCandidateEconomicEvaluationResult | None
    )
    rng_was_used: bool


@dataclass(frozen=True)
class OrderControlTvtMpCandidateSelectionSetResult:
    """All-Node candidate selection result for one economic-evaluation set."""

    economic_evaluation_set_result: OrderControlTvtMpEconomicEvaluationSetResult
    node_candidate_selection_results: tuple[
        OrderControlTvtNodeMpCandidateSelectionResult,
        ...,
    ]


def select_tvt_mp_candidates(
    economic_evaluation_set_result,
    real_W,
) -> OrderControlTvtMpCandidateSelectionSetResult:
    """
    Select at most one economically feasible candidate for every target Node.

    Selection uses saved surplus, then buyer count. A local temporary RNG
    is built only when two or more candidates share both values. This
    function does not use real_W.rng or real_W.order_control_rng, does not
    compute payment or compensation, and returns no partial overall result.
    """
    economic_set_result = _require_economic_evaluation_set_result(
        economic_evaluation_set_result,
    )
    real_world = _require_real_world(real_W)
    random_seed = _require_world_random_seed(real_world)
    world_timestep_T = _require_world_timestep_t(real_world)

    node_economic_results = economic_set_result.node_economic_evaluation_results
    if not isinstance(node_economic_results, tuple):
        raise RuntimeError(
            "node_economic_evaluation_results must be a tuple; got "
            f"type {type(node_economic_results).__name__}."
        )
    node_local_results = _require_matching_node_local_results(
        economic_set_result,
        node_economic_results=node_economic_results,
    )

    node_selection_results: list[OrderControlTvtNodeMpCandidateSelectionResult] = []
    node_index = 0
    for node_economic_result in node_economic_results:
        node_local_result = node_local_results[node_index]
        node_selection_result = _select_for_one_node(
            node_economic_result=node_economic_result,
            node_local_result=node_local_result,
            random_seed=random_seed,
            world_timestep_T=world_timestep_T,
        )
        node_selection_results.append(node_selection_result)
        node_index = node_index + 1

    return _build_overall_selection_result(
        economic_set_result=economic_set_result,
        node_selection_results=tuple(node_selection_results),
    )


def _require_economic_evaluation_set_result(
    economic_evaluation_set_result: object,
) -> OrderControlTvtMpEconomicEvaluationSetResult:
    if not isinstance(
        economic_evaluation_set_result,
        OrderControlTvtMpEconomicEvaluationSetResult,
    ):
        raise ValueError(
            "economic_evaluation_set_result must be "
            "OrderControlTvtMpEconomicEvaluationSetResult; got "
            f"type {type(economic_evaluation_set_result).__name__}."
        )
    return economic_evaluation_set_result


def _require_real_world(real_W: object) -> World:
    if not isinstance(real_W, World):
        raise ValueError(
            "real_W must be a World; got "
            f"type {type(real_W).__name__}."
        )
    return real_W


def _require_world_random_seed(real_world: World) -> int | None:
    """
    Return World.random_seed after checking the existing World contract.

    Legal values are None or a non-negative Python int. bool is rejected
    because it is a subclass of int. A negative int is rejected rather than
    converted, because numpy SeedSequence does not accept negative entropy.
    """
    if not hasattr(real_world, "random_seed"):
        raise ValueError("real_W.random_seed is missing.")
    random_seed = real_world.random_seed
    if random_seed is None:
        return None
    if type(random_seed) is not int:
        raise ValueError(
            "real_W.random_seed must be a Python int or None, not bool; got "
            f"type {type(random_seed).__name__} with value {random_seed!r}."
        )
    if random_seed < 0:
        raise ValueError(
            "real_W.random_seed must be a non-negative Python int or None; "
            f"got {random_seed!r}."
        )
    return random_seed


def _require_world_timestep_t(real_world: World) -> int:
    """
    Return World.T after checking it is a non-negative Python int.

    World timesteps start at 0. bool is rejected. A negative value is
    rejected rather than converted, because it is not a legal timestep and
    numpy SeedSequence does not accept negative entropy integers.
    """
    if not hasattr(real_world, "T"):
        raise ValueError("real_W.T is missing.")
    world_timestep_T = real_world.T
    if type(world_timestep_T) is not int:
        raise ValueError(
            "real_W.T must be a Python int, not bool; got "
            f"type {type(world_timestep_T).__name__} with value "
            f"{world_timestep_T!r}."
        )
    if world_timestep_T < 0:
        raise ValueError(
            "real_W.T must be a non-negative Python int; got "
            f"{world_timestep_T!r}."
        )
    return world_timestep_T


def _require_matching_node_local_results(
    economic_set_result: OrderControlTvtMpEconomicEvaluationSetResult,
    *,
    node_economic_results: tuple[OrderControlTvtNodeMpEconomicEvaluationResult, ...],
) -> tuple[OrderControlTvtNodeMpLocalVirtualCalculationResult, ...]:
    local_set_result = economic_set_result.local_virtual_calculation_set_result
    if not isinstance(
        local_set_result,
        OrderControlTvtMpLocalVirtualCalculationSetResult,
    ):
        raise RuntimeError(
            "local_virtual_calculation_set_result must be "
            "OrderControlTvtMpLocalVirtualCalculationSetResult; got "
            f"type {type(local_set_result).__name__}."
        )
    node_local_results = local_set_result.node_local_virtual_calculation_results
    if not isinstance(node_local_results, tuple):
        raise RuntimeError(
            "node_local_virtual_calculation_results must be a tuple; got "
            f"type {type(node_local_results).__name__}."
        )
    if len(node_local_results) != len(node_economic_results):
        raise RuntimeError(
            "economic Node results and local virtual-calculation Node "
            "results must have the same length; got "
            f"{len(node_economic_results)} economic Node results and "
            f"{len(node_local_results)} local Node results."
        )
    return node_local_results


def _select_for_one_node(
    *,
    node_economic_result: object,
    node_local_result: object,
    random_seed: int | None,
    world_timestep_T: int,
) -> OrderControlTvtNodeMpCandidateSelectionResult:
    if not isinstance(
        node_economic_result,
        OrderControlTvtNodeMpEconomicEvaluationResult,
    ):
        raise RuntimeError(
            "Each node economic-evaluation result must be "
            "OrderControlTvtNodeMpEconomicEvaluationResult; got "
            f"type {type(node_economic_result).__name__}."
        )
    if not isinstance(
        node_local_result,
        OrderControlTvtNodeMpLocalVirtualCalculationResult,
    ):
        raise RuntimeError(
            "Each node local virtual-calculation result must be "
            "OrderControlTvtNodeMpLocalVirtualCalculationResult; got "
            f"type {type(node_local_result).__name__}."
        )

    node_name = node_economic_result.node_name
    _require_node_name_string(node_name, field_name="economic node_name")
    _require_node_name_string(
        node_local_result.node_name,
        field_name="local node_name",
    )
    if node_local_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: local virtual-calculation node_name "
            f"{node_local_result.node_name!r} does not match the economic "
            "Node result."
        )

    candidate_economic_results = (
        node_economic_result.candidate_economic_evaluation_results
    )
    if not isinstance(candidate_economic_results, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: candidate_economic_evaluation_results "
            "must be a tuple; got "
            f"type {type(candidate_economic_results).__name__}."
        )

    identities_in_node: list[tuple[str, tuple[OrderControlTvtVisitKey, ...]]] = []
    feasible_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult] = []
    for candidate_economic_result in candidate_economic_results:
        _require_candidate_economic_result_type(
            candidate_economic_result,
            node_name=node_name,
        )
        _require_candidate_belongs_to_input_tuple(
            candidate_economic_result,
            candidate_economic_results,
            node_name=node_name,
        )
        _validate_candidate_economic_result(
            candidate_economic_result,
            node_name=node_name,
        )
        candidate_identity = _build_candidate_identity(
            node_name=node_name,
            candidate_economic_result=candidate_economic_result,
        )
        _require_identity_not_already_seen(
            candidate_identity,
            identities_in_node,
            node_name=node_name,
        )
        identities_in_node.append(candidate_identity)
        if candidate_economic_result.economically_feasible is True:
            feasible_candidates.append(candidate_economic_result)

    if len(feasible_candidates) == 0:
        return _build_node_candidate_selection_result(
            node_name=node_name,
            selection_status=(
                OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
            ),
            selected_candidate_economic_result=None,
            rng_was_used=False,
            input_candidate_results=candidate_economic_results,
        )

    maximum_surplus_candidates = _extract_maximum_surplus_candidates(
        feasible_candidates,
        node_name=node_name,
    )
    if len(maximum_surplus_candidates) == 1:
        return _build_selected_node_result(
            node_name=node_name,
            selected_candidate_economic_result=maximum_surplus_candidates[0],
            rng_was_used=False,
            input_candidate_results=candidate_economic_results,
        )

    maximum_buyer_count_candidates = _extract_maximum_buyer_count_candidates(
        maximum_surplus_candidates,
        node_name=node_name,
    )
    if len(maximum_buyer_count_candidates) == 1:
        return _build_selected_node_result(
            node_name=node_name,
            selected_candidate_economic_result=maximum_buyer_count_candidates[0],
            rng_was_used=False,
            input_candidate_results=candidate_economic_results,
        )

    selected_candidate = _select_final_tied_candidate_with_local_rng(
        tied_candidates=maximum_buyer_count_candidates,
        node_name=node_name,
        random_seed=random_seed,
        world_timestep_T=world_timestep_T,
    )
    return _build_selected_node_result(
        node_name=node_name,
        selected_candidate_economic_result=selected_candidate,
        rng_was_used=True,
        input_candidate_results=candidate_economic_results,
    )


def _require_node_name_string(node_name: object, *, field_name: str) -> str:
    if not isinstance(node_name, str) or node_name == "":
        raise RuntimeError(
            f"{field_name} must be a non-empty str; got {node_name!r}."
        )
    return node_name


def _require_candidate_economic_result_type(
    candidate_economic_result: object,
    *,
    node_name: str,
) -> None:
    if not isinstance(
        candidate_economic_result,
        OrderControlTvtMpCandidateEconomicEvaluationResult,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: each candidate economic result must be "
            "OrderControlTvtMpCandidateEconomicEvaluationResult; got "
            f"type {type(candidate_economic_result).__name__}."
        )


def _require_candidate_belongs_to_input_tuple(
    candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
    candidate_economic_results: tuple[
        OrderControlTvtMpCandidateEconomicEvaluationResult,
        ...,
    ],
    *,
    node_name: str,
) -> None:
    for existing_candidate in candidate_economic_results:
        if existing_candidate is candidate_economic_result:
            return
    raise RuntimeError(
        f"Node {node_name!r}: candidate economic result is not an object "
        "from the input economic Node result."
    )


def _validate_candidate_economic_result(
    candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
    *,
    node_name: str,
) -> None:
    economically_feasible = candidate_economic_result.economically_feasible
    if type(economically_feasible) is not bool:
        raise RuntimeError(
            f"Node {node_name!r}: economically_feasible must be a strict "
            "Python bool; got "
            f"type {type(economically_feasible).__name__} with value "
            f"{economically_feasible!r}."
        )

    infeasibility_reasons = candidate_economic_result.infeasibility_reasons
    if not isinstance(infeasibility_reasons, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: infeasibility_reasons must be a tuple; "
            f"got type {type(infeasibility_reasons).__name__}."
        )

    if economically_feasible is True:
        if len(infeasibility_reasons) != 0:
            raise RuntimeError(
                f"Node {node_name!r}: economically_feasible is True but "
                "infeasibility_reasons is not empty."
            )
    else:
        if len(infeasibility_reasons) == 0:
            raise RuntimeError(
                f"Node {node_name!r}: economically_feasible is False but "
                "infeasibility_reasons is empty."
            )

    total_buyer_value_G = _require_finite_number(
        candidate_economic_result.total_buyer_value_G,
        field_name="total_buyer_value_G",
        node_name=node_name,
    )
    total_required_compensation_R = _require_finite_number(
        candidate_economic_result.total_required_compensation_R,
        field_name="total_required_compensation_R",
        node_name=node_name,
    )
    surplus = _require_finite_number(
        candidate_economic_result.surplus,
        field_name="surplus",
        node_name=node_name,
    )
    expected_surplus = total_buyer_value_G - total_required_compensation_R
    if surplus != expected_surplus:
        raise RuntimeError(
            f"Node {node_name!r}: saved surplus {surplus!r} does not equal "
            f"total_buyer_value_G - total_required_compensation_R "
            f"({expected_surplus!r})."
        )

    buyer_economic_records = candidate_economic_result.buyer_economic_records
    if not isinstance(buyer_economic_records, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: buyer_economic_records must be a tuple; "
            f"got type {type(buyer_economic_records).__name__}."
        )

    local_result = _require_candidate_local_result(
        candidate_economic_result,
        node_name=node_name,
    )
    if local_result.node_name != node_name:
        raise RuntimeError(
            f"Node {node_name!r}: candidate local result node_name "
            f"{local_result.node_name!r} does not match the Node result."
        )

    buyers_sorted = _require_buyers_sorted_tuple(
        local_result,
        node_name=node_name,
    )
    buyer_count = len(buyer_economic_records)
    if buyer_count != len(buyers_sorted):
        raise RuntimeError(
            f"Node {node_name!r}: buyer_economic_records length "
            f"{buyer_count} does not match buyers_sorted length "
            f"{len(buyers_sorted)}."
        )
    _require_buyer_visit_keys_match_buyers_sorted(
        buyer_economic_records=buyer_economic_records,
        buyers_sorted=buyers_sorted,
        node_name=node_name,
    )

    if economically_feasible is True:
        if buyer_count < 1:
            raise RuntimeError(
                f"Node {node_name!r}: economically feasible candidate has "
                "no buyer economic records."
            )
        for buyer_record in buyer_economic_records:
            gross_time_value_G_b = _require_finite_number(
                buyer_record.gross_time_value_G_b,
                field_name="gross_time_value_G_b",
                node_name=node_name,
            )
            if not (gross_time_value_G_b > 0):
                raise RuntimeError(
                    f"Node {node_name!r}: economically feasible candidate "
                    "has a buyer with gross_time_value_G_b <= 0."
                )
        if not (total_buyer_value_G >= total_required_compensation_R):
            raise RuntimeError(
                f"Node {node_name!r}: economically feasible candidate has "
                "total_buyer_value_G < total_required_compensation_R."
            )


def _require_finite_number(
    value: object,
    *,
    field_name: str,
    node_name: str,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a finite number; got "
            f"type {type(value).__name__} with value {value!r}."
        )
    if not math.isfinite(value):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a finite number; got "
            f"{value!r}."
        )
    return value


def _require_candidate_local_result(
    candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
    *,
    node_name: str,
) -> OrderControlTvtMpCandidateLocalVirtualCalculationResult:
    local_result = (
        candidate_economic_result.candidate_local_virtual_calculation_result
    )
    if not isinstance(
        local_result,
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: candidate_local_virtual_calculation_result "
            "must be OrderControlTvtMpCandidateLocalVirtualCalculationResult; "
            f"got type {type(local_result).__name__}."
        )
    return local_result


def _require_buyers_sorted_tuple(
    local_result: OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    *,
    node_name: str,
) -> tuple[OrderControlTvtVisitKey, ...]:
    concrete_buyer_candidate_set = local_result.concrete_buyer_candidate_set
    if not isinstance(
        concrete_buyer_candidate_set,
        OrderControlTvtMpConcreteBuyerCandidateSet,
    ):
        raise RuntimeError(
            f"Node {node_name!r}: concrete_buyer_candidate_set must be "
            "OrderControlTvtMpConcreteBuyerCandidateSet; got "
            f"type {type(concrete_buyer_candidate_set).__name__}."
        )
    buyers_sorted = concrete_buyer_candidate_set.buyers_sorted
    if not isinstance(buyers_sorted, tuple):
        raise RuntimeError(
            f"Node {node_name!r}: buyers_sorted must be a tuple; got "
            f"type {type(buyers_sorted).__name__}."
        )
    for visit_key in buyers_sorted:
        _require_visit_key(visit_key, node_name=node_name)
    return buyers_sorted


def _require_visit_key(
    visit_key: object,
    *,
    node_name: str,
) -> OrderControlTvtVisitKey:
    if not isinstance(visit_key, tuple) or len(visit_key) != 2:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey must be a length-2 tuple "
            f"(vehicle_name, visit_id); got {visit_key!r}."
        )
    vehicle_name, visit_id = visit_key
    if not isinstance(vehicle_name, str) or vehicle_name == "":
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey vehicle_name must be a "
            f"non-empty str; got {vehicle_name!r}."
        )
    if type(visit_id) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey visit_id must be a Python int, "
            f"not bool; got type {type(visit_id).__name__} with value "
            f"{visit_id!r}."
        )
    if visit_id < 1:
        raise RuntimeError(
            f"Node {node_name!r}: VisitKey visit_id must be >= 1; got "
            f"{visit_id!r}."
        )
    return (vehicle_name, visit_id)


def _require_buyer_visit_keys_match_buyers_sorted(
    *,
    buyer_economic_records: tuple[object, ...],
    buyers_sorted: tuple[OrderControlTvtVisitKey, ...],
    node_name: str,
) -> None:
    record_visit_keys: list[OrderControlTvtVisitKey] = []
    for buyer_record in buyer_economic_records:
        visit_key = _require_visit_key(
            getattr(buyer_record, "visit_key", None),
            node_name=node_name,
        )
        if _visit_key_is_in_list(visit_key, record_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {visit_key!r} appears "
                "more than once among buyer_economic_records."
            )
        record_visit_keys.append(visit_key)

    seen_buyers_sorted: list[OrderControlTvtVisitKey] = []
    for visit_key in buyers_sorted:
        if _visit_key_is_in_list(visit_key, seen_buyers_sorted):
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {visit_key!r} appears "
                "more than once in buyers_sorted."
            )
        seen_buyers_sorted.append(visit_key)

    for visit_key in record_visit_keys:
        if not _visit_key_is_in_list(visit_key, buyers_sorted):
            raise RuntimeError(
                f"Node {node_name!r}: buyer VisitKey {visit_key!r} from "
                "buyer_economic_records is not in buyers_sorted."
            )
    for visit_key in buyers_sorted:
        if not _visit_key_is_in_list(visit_key, record_visit_keys):
            raise RuntimeError(
                f"Node {node_name!r}: buyers_sorted VisitKey {visit_key!r} "
                "is not among buyer_economic_records."
            )


def _visit_key_is_in_list(
    visit_key: OrderControlTvtVisitKey,
    visit_keys: list[OrderControlTvtVisitKey] | tuple[OrderControlTvtVisitKey, ...],
) -> bool:
    for existing_visit_key in visit_keys:
        if existing_visit_key == visit_key:
            return True
    return False


def _build_candidate_identity(
    *,
    node_name: str,
    candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
) -> tuple[str, tuple[OrderControlTvtVisitKey, ...]]:
    """
    Stable candidate identity: Node name plus the official buyers_sorted
    VisitKey column. Enumeration index and object identity numbers are not
    used.
    """
    local_result = _require_candidate_local_result(
        candidate_economic_result,
        node_name=node_name,
    )
    buyers_sorted = _require_buyers_sorted_tuple(
        local_result,
        node_name=node_name,
    )
    return (node_name, buyers_sorted)


def _require_identity_not_already_seen(
    candidate_identity: tuple[str, tuple[OrderControlTvtVisitKey, ...]],
    seen_identities: list[tuple[str, tuple[OrderControlTvtVisitKey, ...]]],
    *,
    node_name: str,
) -> None:
    for seen_identity in seen_identities:
        if seen_identity == candidate_identity:
            raise RuntimeError(
                f"Node {node_name!r}: candidate identity {candidate_identity!r} "
                "is duplicated inside the Node."
            )


def _extract_maximum_surplus_candidates(
    feasible_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult],
    *,
    node_name: str,
) -> list[OrderControlTvtMpCandidateEconomicEvaluationResult]:
    if len(feasible_candidates) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: internal contradiction: feasible candidate "
            "list is empty while extracting maximum surplus."
        )
    maximum_surplus = feasible_candidates[0].surplus
    for candidate_economic_result in feasible_candidates:
        surplus = candidate_economic_result.surplus
        if surplus > maximum_surplus:
            maximum_surplus = surplus

    maximum_surplus_candidates: list[
        OrderControlTvtMpCandidateEconomicEvaluationResult
    ] = []
    for candidate_economic_result in feasible_candidates:
        if candidate_economic_result.surplus == maximum_surplus:
            maximum_surplus_candidates.append(candidate_economic_result)
    if len(maximum_surplus_candidates) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: internal contradiction: no candidate "
            "matches the computed maximum surplus."
        )
    return maximum_surplus_candidates


def _buyer_count(
    candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
) -> int:
    return len(candidate_economic_result.buyer_economic_records)


def _extract_maximum_buyer_count_candidates(
    surplus_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult],
    *,
    node_name: str,
) -> list[OrderControlTvtMpCandidateEconomicEvaluationResult]:
    if len(surplus_candidates) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: internal contradiction: maximum-surplus "
            "candidate list is empty while extracting maximum buyer count."
        )
    maximum_buyer_count = _buyer_count(surplus_candidates[0])
    for candidate_economic_result in surplus_candidates:
        buyer_count = _buyer_count(candidate_economic_result)
        if buyer_count > maximum_buyer_count:
            maximum_buyer_count = buyer_count

    maximum_buyer_count_candidates: list[
        OrderControlTvtMpCandidateEconomicEvaluationResult
    ] = []
    for candidate_economic_result in surplus_candidates:
        if _buyer_count(candidate_economic_result) == maximum_buyer_count:
            maximum_buyer_count_candidates.append(candidate_economic_result)
    if len(maximum_buyer_count_candidates) == 0:
        raise RuntimeError(
            f"Node {node_name!r}: internal contradiction: no candidate "
            "matches the computed maximum buyer count."
        )
    return maximum_buyer_count_candidates


def _sort_tied_candidates_by_identity(
    tied_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult],
    *,
    node_name: str,
) -> list[OrderControlTvtMpCandidateEconomicEvaluationResult]:
    """
    Fix the RNG population order from stable candidate identities.

    This sort is used only for the final tie. Public Node and candidate
    order is not rewritten.
    """
    identity_and_candidate_pairs: list[
        tuple[
            tuple[str, tuple[OrderControlTvtVisitKey, ...]],
            OrderControlTvtMpCandidateEconomicEvaluationResult,
        ]
    ] = []
    for candidate_economic_result in tied_candidates:
        candidate_identity = _build_candidate_identity(
            node_name=node_name,
            candidate_economic_result=candidate_economic_result,
        )
        identity_and_candidate_pairs.append(
            (candidate_identity, candidate_economic_result)
        )

    sorted_pairs = sorted(
        identity_and_candidate_pairs,
        key=_identity_sort_key,
    )
    sorted_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult] = []
    for pair in sorted_pairs:
        sorted_candidates.append(pair[1])
    return sorted_candidates


def _identity_sort_key(
    identity_and_candidate_pair: tuple[
        tuple[str, tuple[OrderControlTvtVisitKey, ...]],
        OrderControlTvtMpCandidateEconomicEvaluationResult,
    ],
) -> tuple[str, tuple[OrderControlTvtVisitKey, ...]]:
    return identity_and_candidate_pair[0]


def _append_utf8_bytes_as_integers(
    integer_list: list[int],
    text: str,
    *,
    field_name: str,
    node_name: str,
) -> None:
    """
    Encode one string as UTF-8 length followed by each byte value.

    Length is stored first so string boundaries are not ambiguous.
    """
    if not isinstance(text, str):
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a str; got "
            f"type {type(text).__name__}."
        )
    text_bytes = text.encode("utf-8")
    integer_list.append(len(text_bytes))
    for byte_value in text_bytes:
        integer_list.append(byte_value)


def _append_non_negative_python_int(
    integer_list: list[int],
    value: object,
    *,
    field_name: str,
    node_name: str,
) -> None:
    if type(value) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a Python int, not "
            f"bool; got type {type(value).__name__} with value {value!r}."
        )
    if value < 0:
        raise RuntimeError(
            f"Node {node_name!r}: {field_name} must be a non-negative "
            f"Python int; got {value!r}."
        )
    integer_list.append(value)


def _build_seed_material_integers(
    *,
    random_seed: int | None,
    world_timestep_T: int,
    node_name: str,
    sorted_tied_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult],
) -> tuple[int, ...]:
    """
    Build an explicit integer sequence for numpy SeedSequence entropy.

    The sequence is not a concatenated display string. None random_seed is
    encoded with a presence flag so it is not placed inside the integer
    list.
    """
    integer_list: list[int] = []
    if random_seed is None:
        integer_list.append(0)
    else:
        integer_list.append(1)
        _append_non_negative_python_int(
            integer_list,
            random_seed,
            field_name="random_seed",
            node_name=node_name,
        )
    _append_non_negative_python_int(
        integer_list,
        world_timestep_T,
        field_name="World.T",
        node_name=node_name,
    )
    _append_utf8_bytes_as_integers(
        integer_list,
        node_name,
        field_name="node_name",
        node_name=node_name,
    )
    _append_non_negative_python_int(
        integer_list,
        len(sorted_tied_candidates),
        field_name="tied_candidate_count",
        node_name=node_name,
    )
    for candidate_economic_result in sorted_tied_candidates:
        candidate_identity = _build_candidate_identity(
            node_name=node_name,
            candidate_economic_result=candidate_economic_result,
        )
        identity_node_name = candidate_identity[0]
        buyers_sorted = candidate_identity[1]
        _append_utf8_bytes_as_integers(
            integer_list,
            identity_node_name,
            field_name="identity node_name",
            node_name=node_name,
        )
        _append_non_negative_python_int(
            integer_list,
            len(buyers_sorted),
            field_name="buyers_sorted count",
            node_name=node_name,
        )
        for visit_key in buyers_sorted:
            vehicle_name, visit_id = visit_key
            _append_utf8_bytes_as_integers(
                integer_list,
                vehicle_name,
                field_name="vehicle_name",
                node_name=node_name,
            )
            _append_non_negative_python_int(
                integer_list,
                visit_id,
                field_name="visit_id",
                node_name=node_name,
            )
    return tuple(integer_list)


def _build_local_selection_rng(seed_material_integers: tuple[int, ...]):
    seed_sequence = np.random.SeedSequence(entropy=seed_material_integers)
    local_rng = np.random.default_rng(seed_sequence)
    return local_rng


def _require_rng_index_in_range(
    index: object,
    tied_candidate_count: int,
    *,
    node_name: str,
) -> int:
    if type(index) is not int:
        raise RuntimeError(
            f"Node {node_name!r}: RNG index must be a Python int; got "
            f"type {type(index).__name__} with value {index!r}."
        )
    if index < 0 or index >= tied_candidate_count:
        raise RuntimeError(
            f"Node {node_name!r}: RNG index {index!r} is outside the range "
            f"[0, {tied_candidate_count})."
        )
    return index


def _select_index_with_local_rng(
    *,
    local_rng,
    tied_candidate_count: int,
    node_name: str,
) -> int:
    generated_index = local_rng.integers(0, tied_candidate_count)
    index = int(generated_index)
    return _require_rng_index_in_range(
        index,
        tied_candidate_count,
        node_name=node_name,
    )


def _select_final_tied_candidate_with_local_rng(
    *,
    tied_candidates: list[OrderControlTvtMpCandidateEconomicEvaluationResult],
    node_name: str,
    random_seed: int | None,
    world_timestep_T: int,
) -> OrderControlTvtMpCandidateEconomicEvaluationResult:
    if len(tied_candidates) < 2:
        raise RuntimeError(
            f"Node {node_name!r}: internal contradiction: local RNG selection "
            "requires two or more final tied candidates."
        )
    seen_identities: list[tuple[str, tuple[OrderControlTvtVisitKey, ...]]] = []
    for candidate_economic_result in tied_candidates:
        candidate_identity = _build_candidate_identity(
            node_name=node_name,
            candidate_economic_result=candidate_economic_result,
        )
        _require_identity_not_already_seen(
            candidate_identity,
            seen_identities,
            node_name=node_name,
        )
        seen_identities.append(candidate_identity)

    sorted_tied_candidates = _sort_tied_candidates_by_identity(
        tied_candidates,
        node_name=node_name,
    )
    seed_material_integers = _build_seed_material_integers(
        random_seed=random_seed,
        world_timestep_T=world_timestep_T,
        node_name=node_name,
        sorted_tied_candidates=sorted_tied_candidates,
    )
    local_rng = _build_local_selection_rng(seed_material_integers)
    selected_index = _select_index_with_local_rng(
        local_rng=local_rng,
        tied_candidate_count=len(sorted_tied_candidates),
        node_name=node_name,
    )
    selected_candidate = sorted_tied_candidates[selected_index]
    return selected_candidate


def _build_selected_node_result(
    *,
    node_name: str,
    selected_candidate_economic_result: OrderControlTvtMpCandidateEconomicEvaluationResult,
    rng_was_used: bool,
    input_candidate_results: tuple[
        OrderControlTvtMpCandidateEconomicEvaluationResult,
        ...,
    ],
) -> OrderControlTvtNodeMpCandidateSelectionResult:
    return _build_node_candidate_selection_result(
        node_name=node_name,
        selection_status=OrderControlTvtMpCandidateSelectionStatus.SELECTED,
        selected_candidate_economic_result=selected_candidate_economic_result,
        rng_was_used=rng_was_used,
        input_candidate_results=input_candidate_results,
    )


def _build_node_candidate_selection_result(
    *,
    node_name: str,
    selection_status: OrderControlTvtMpCandidateSelectionStatus,
    selected_candidate_economic_result: (
        OrderControlTvtMpCandidateEconomicEvaluationResult | None
    ),
    rng_was_used: object,
    input_candidate_results: tuple[
        OrderControlTvtMpCandidateEconomicEvaluationResult,
        ...,
    ],
) -> OrderControlTvtNodeMpCandidateSelectionResult:
    if type(rng_was_used) is not bool:
        raise RuntimeError(
            f"Node {node_name!r}: rng_was_used must be a strict Python bool; "
            f"got type {type(rng_was_used).__name__} with value "
            f"{rng_was_used!r}."
        )
    if not isinstance(selection_status, OrderControlTvtMpCandidateSelectionStatus):
        raise RuntimeError(
            f"Node {node_name!r}: selection_status must be "
            "OrderControlTvtMpCandidateSelectionStatus; got "
            f"{selection_status!r}."
        )
    if (
        selection_status
        is OrderControlTvtMpCandidateSelectionStatus.SELECTED
    ):
        if selected_candidate_economic_result is None:
            raise RuntimeError(
                f"Node {node_name!r}: SELECTED requires a selected candidate."
            )
        found_in_input = False
        for input_candidate in input_candidate_results:
            if input_candidate is selected_candidate_economic_result:
                found_in_input = True
                break
        if found_in_input is False:
            raise RuntimeError(
                f"Node {node_name!r}: selected candidate is not an object "
                "from the input economic Node result."
            )
    elif (
        selection_status
        is OrderControlTvtMpCandidateSelectionStatus.NO_ECONOMICALLY_FEASIBLE_CANDIDATE
    ):
        if selected_candidate_economic_result is not None:
            raise RuntimeError(
                f"Node {node_name!r}: NO_ECONOMICALLY_FEASIBLE_CANDIDATE "
                "requires selected_candidate_economic_result is None."
            )
        if rng_was_used is not False:
            raise RuntimeError(
                f"Node {node_name!r}: NO_ECONOMICALLY_FEASIBLE_CANDIDATE "
                "requires rng_was_used is False."
            )
    else:
        raise RuntimeError(
            f"Node {node_name!r}: unknown selection_status {selection_status!r}."
        )
    return OrderControlTvtNodeMpCandidateSelectionResult(
        node_name=node_name,
        selection_status=selection_status,
        selected_candidate_economic_result=selected_candidate_economic_result,
        rng_was_used=rng_was_used,
    )


def _build_overall_selection_result(
    *,
    economic_set_result: OrderControlTvtMpEconomicEvaluationSetResult,
    node_selection_results: tuple[
        OrderControlTvtNodeMpCandidateSelectionResult,
        ...,
    ],
) -> OrderControlTvtMpCandidateSelectionSetResult:
    return OrderControlTvtMpCandidateSelectionSetResult(
        economic_evaluation_set_result=economic_set_result,
        node_candidate_selection_results=node_selection_results,
    )
