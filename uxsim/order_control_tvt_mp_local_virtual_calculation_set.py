"""
TVT-MP all-candidate local virtual calculation entry.

Walks a saved FIFO inspection set in stored Node and candidate order.
Only FIFO-passed candidates are sent to the existing one-candidate
orchestrating loop. FIFO False candidates are skipped. Resolved and
normal unresolved results are both kept. This module does not rebuild
ranks, rerun FIFO inspection, rerun baseline, or evaluate economics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryResult,
)
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetStatus,
)
from uxsim.order_control_tvt_mp_candidate_local_state import (
    build_tvt_mp_candidate_local_state,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    initialize_tvt_mp_candidate_local_virtual_calculation_state,
    run_tvt_mp_candidate_local_virtual_calculation,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtMpFifoInspectionSetResult,
    OrderControlTvtNodeMpFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    build_tvt_mp_local_binding_rank_sequence,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import World


_NORMAL_NOT_GENERATED_STATUSES = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
)


@dataclass(frozen=True)
class OrderControlTvtNodeMpLocalVirtualCalculationResult:
    """Local virtual-calculation results for one target Node, in FIFO True order."""

    node_name: str
    build_status: OrderControlTvtCandidateVisitSetStatus
    candidate_local_virtual_calculation_results: tuple[
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
        ...,
    ]


@dataclass(frozen=True)
class OrderControlTvtMpLocalVirtualCalculationSetResult:
    """All-Node local virtual-calculation entry result."""

    fifo_inspection_set_result: OrderControlTvtMpFifoInspectionSetResult
    node_local_virtual_calculation_results: tuple[
        OrderControlTvtNodeMpLocalVirtualCalculationResult,
        ...,
    ]


def evaluate_tvt_mp_candidate_local_virtual_calculations(
    real_W,
    fifo_inspection_set_result,
    *,
    rank_states_by_node_name,
) -> OrderControlTvtMpLocalVirtualCalculationSetResult:
    """
    Run one-candidate local virtual calculation for every FIFO-passed candidate.

    Node order and candidate order come from the saved FIFO inspection
    result. FIFO False candidates are not copied and are not executed.
    """
    real_world = _require_real_world(real_W)
    fifo_set = _require_fifo_inspection_set_result(fifo_inspection_set_result)
    rank_states = _require_rank_states_mapping(rank_states_by_node_name)
    fork_result = _fork_result_from_fifo_set(fifo_set)
    _require_real_world_matches_baseline(real_world, fork_result)
    _require_fifo_nodes_match_target_node_names(fifo_set, fork_result)

    node_results: list[OrderControlTvtNodeMpLocalVirtualCalculationResult] = []
    fifo_node_results = fifo_set.node_fifo_inspection_results
    for node_index, fifo_node_result in enumerate(fifo_node_results):
        node_result = _evaluate_one_fifo_node(
            real_world=real_world,
            fifo_set=fifo_set,
            fifo_node_result=fifo_node_result,
            node_index=node_index,
            fork_result=fork_result,
            rank_states_by_node_name=rank_states,
        )
        node_results.append(node_result)

    return OrderControlTvtMpLocalVirtualCalculationSetResult(
        fifo_inspection_set_result=fifo_set,
        node_local_virtual_calculation_results=tuple(node_results),
    )


def _require_real_world(real_W: object) -> World:
    if not isinstance(real_W, World):
        raise ValueError(
            "real_W must be a World; got "
            f"type {type(real_W).__name__}."
        )
    return real_W


def _require_fifo_inspection_set_result(
    fifo_inspection_set_result: object,
) -> OrderControlTvtMpFifoInspectionSetResult:
    if not isinstance(
        fifo_inspection_set_result,
        OrderControlTvtMpFifoInspectionSetResult,
    ):
        raise ValueError(
            "fifo_inspection_set_result must be "
            "OrderControlTvtMpFifoInspectionSetResult; got "
            f"type {type(fifo_inspection_set_result).__name__}."
        )
    return fifo_inspection_set_result


def _require_rank_states_mapping(rank_states_by_node_name: object) -> Mapping:
    if isinstance(rank_states_by_node_name, (str, bytes)):
        raise ValueError(
            "rank_states_by_node_name must be a Mapping from node name to "
            f"OrderControlTvtNodeRankState; got {type(rank_states_by_node_name).__name__}."
        )
    if not isinstance(rank_states_by_node_name, Mapping):
        raise ValueError(
            "rank_states_by_node_name must be a Mapping from node name to "
            f"OrderControlTvtNodeRankState; got {type(rank_states_by_node_name).__name__}."
        )
    return rank_states_by_node_name


def _fork_result_from_fifo_set(
    fifo_set: OrderControlTvtMpFifoInspectionSetResult,
) -> OrderControlBaselineForkResult:
    """Read the saved baseline fork through the existing result chain once."""
    try:
        general_trade_rank_set_result = fifo_set.general_trade_rank_set_result
        concrete_buyer_candidate_set_result = (
            general_trade_rank_set_result.concrete_buyer_candidate_set_result
        )
        inlink_candidate_physical_order_result = (
            concrete_buyer_candidate_set_result.inlink_candidate_physical_order_result
        )
        candidate_visit_set_result = (
            inlink_candidate_physical_order_result.candidate_visit_set_result
        )
        right_of_entry_selection_result = (
            candidate_visit_set_result.right_of_entry_selection_result
        )
        leading_confirmation_result = (
            right_of_entry_selection_result.leading_confirmation_result
        )
        arrived_confirmation_result = (
            leading_confirmation_result.arrived_confirmation_result
        )
        alignment_fork_result = arrived_confirmation_result.alignment_fork_result
        fork_result = alignment_fork_result.fork_result
    except AttributeError as error:
        raise RuntimeError(
            "fifo_inspection_set_result is missing a required upstream "
            "result on the saved reference chain to fork_result."
        ) from error
    if not isinstance(fork_result, OrderControlBaselineForkResult):
        raise RuntimeError(
            "alignment_fork_result.fork_result must be "
            "OrderControlBaselineForkResult; got "
            f"type {type(fork_result).__name__}."
        )
    return fork_result


def _require_python_int_timestep(
    value: object,
    *,
    field_name: str,
    error_type: type[Exception],
) -> int:
    if type(value) is not int:
        raise error_type(
            f"{field_name} must be a Python int, not bool; got type "
            f"{type(value).__name__} with value {value!r}."
        )
    return value


def _require_real_world_matches_baseline(
    real_world: World,
    fork_result: OrderControlBaselineForkResult,
) -> None:
    real_timestep = _require_python_int_timestep(
        real_world.T,
        field_name="real_W.T",
        error_type=ValueError,
    )
    baseline_timestep = _require_python_int_timestep(
        fork_result.baseline_timestep_T,
        field_name="fork_result.baseline_timestep_T",
        error_type=RuntimeError,
    )
    if real_timestep != baseline_timestep:
        raise ValueError(
            "real_W.T must equal fork_result.baseline_timestep_T; "
            f"real_W.T={real_timestep!r}, "
            f"baseline_timestep_T={baseline_timestep!r}."
        )


def _require_fifo_nodes_match_target_node_names(
    fifo_set: OrderControlTvtMpFifoInspectionSetResult,
    fork_result: OrderControlBaselineForkResult,
) -> None:
    fifo_node_results = fifo_set.node_fifo_inspection_results
    target_node_names = fork_result.target_node_names
    if not isinstance(fifo_node_results, tuple):
        raise RuntimeError(
            "node_fifo_inspection_results must be a tuple; got "
            f"{type(fifo_node_results).__name__}."
        )
    if not isinstance(target_node_names, tuple):
        raise RuntimeError(
            "fork_result.target_node_names must be a tuple; got "
            f"{type(target_node_names).__name__}."
        )
    fifo_count = len(fifo_node_results)
    target_count = len(target_node_names)
    if fifo_count != target_count:
        raise RuntimeError(
            "FIFO Node result count "
            f"{fifo_count} does not match fork_result.target_node_names "
            f"count {target_count}."
        )
    for node_index, fifo_node_result in enumerate(fifo_node_results):
        if not isinstance(fifo_node_result, OrderControlTvtNodeMpFifoInspectionResult):
            raise RuntimeError(
                f"node_fifo_inspection_results[{node_index}] must be "
                "OrderControlTvtNodeMpFifoInspectionResult; got "
                f"type {type(fifo_node_result).__name__}."
            )
        target_node_name = target_node_names[node_index]
        if fifo_node_result.node_name != target_node_name:
            raise RuntimeError(
                f"FIFO Node result at index {node_index} has node_name "
                f"{fifo_node_result.node_name!r}, but "
                f"fork_result.target_node_names[{node_index}] is "
                f"{target_node_name!r}."
            )


def _build_status_is_normal_not_generated(
    build_status: object,
) -> bool:
    return build_status in _NORMAL_NOT_GENERATED_STATUSES


def _build_status_is_complete(build_status: object) -> bool:
    return (
        build_status
        is OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
    )


def _empty_node_result(
    fifo_node_result: OrderControlTvtNodeMpFifoInspectionResult,
) -> OrderControlTvtNodeMpLocalVirtualCalculationResult:
    return OrderControlTvtNodeMpLocalVirtualCalculationResult(
        node_name=fifo_node_result.node_name,
        build_status=fifo_node_result.build_status,
        candidate_local_virtual_calculation_results=(),
    )


def _candidate_is_fifo_true(
    candidate_fifo_inspection_result: object,
) -> bool:
    if not isinstance(
        candidate_fifo_inspection_result,
        OrderControlTvtMpCandidateFifoInspectionResult,
    ):
        raise RuntimeError(
            "candidate_fifo_inspection_result must be "
            "OrderControlTvtMpCandidateFifoInspectionResult; got "
            f"type {type(candidate_fifo_inspection_result).__name__}."
        )
    return candidate_fifo_inspection_result.preserves_inlink_fifo is True


def _node_has_fifo_true_candidate(
    fifo_node_result: OrderControlTvtNodeMpFifoInspectionResult,
) -> bool:
    for candidate_fifo_inspection_result in (
        fifo_node_result.candidate_fifo_inspection_results
    ):
        if _candidate_is_fifo_true(candidate_fifo_inspection_result):
            return True
    return False


def _rank_state_for_evaluated_node(
    *,
    node_name: str,
    rank_states_by_node_name: Mapping,
) -> OrderControlTvtNodeRankState:
    if node_name not in rank_states_by_node_name:
        raise ValueError(
            f"rank_states_by_node_name has no OrderControlTvtNodeRankState "
            f"for Node {node_name!r}."
        )
    rank_state = rank_states_by_node_name[node_name]
    if not isinstance(rank_state, OrderControlTvtNodeRankState):
        raise ValueError(
            f"rank_states_by_node_name[{node_name!r}] must be "
            "OrderControlTvtNodeRankState; got "
            f"type {type(rank_state).__name__}."
        )
    if rank_state.node_name != node_name:
        raise ValueError(
            f"rank_states_by_node_name[{node_name!r}].node_name is "
            f"{rank_state.node_name!r}, not {node_name!r}."
        )
    return rank_state


def _downstream_boundary_node_result_for_evaluated_node(
    *,
    node_name: str,
    node_index: int,
    fork_result: OrderControlBaselineForkResult,
) -> OrderControlBaselineDownstreamBoundaryNodeResult:
    overall_boundary_result = fork_result.downstream_boundary_result
    if overall_boundary_result is None:
        raise RuntimeError(
            f"Node {node_name!r}: downstream_boundary_result is None while "
            "at least one FIFO-passed candidate requires local virtual "
            "calculation. An empty baseline is not an observed active "
            "count of zero."
        )
    if not isinstance(
        overall_boundary_result,
        OrderControlBaselineDownstreamBoundaryResult,
    ):
        raise RuntimeError(
            "fork_result.downstream_boundary_result must be "
            "OrderControlBaselineDownstreamBoundaryResult; got "
            f"type {type(overall_boundary_result).__name__}."
        )
    node_results = overall_boundary_result.node_results
    target_node_names = fork_result.target_node_names
    if len(node_results) != len(target_node_names):
        raise RuntimeError(
            "downstream_boundary_result.node_results count "
            f"{len(node_results)} does not match "
            f"fork_result.target_node_names count {len(target_node_names)}."
        )
    if node_index >= len(node_results):
        raise RuntimeError(
            f"Node {node_name!r}: downstream_boundary_result.node_results "
            f"has no entry at index {node_index}."
        )
    node_boundary_result = node_results[node_index]
    if not isinstance(
        node_boundary_result,
        OrderControlBaselineDownstreamBoundaryNodeResult,
    ):
        raise RuntimeError(
            f"downstream_boundary_result.node_results[{node_index}] must be "
            "OrderControlBaselineDownstreamBoundaryNodeResult; got "
            f"type {type(node_boundary_result).__name__}."
        )
    target_node_name = target_node_names[node_index]
    if node_boundary_result.node_name != node_name:
        raise RuntimeError(
            f"downstream_boundary_result.node_results[{node_index}].node_name "
            f"is {node_boundary_result.node_name!r}, but the FIFO Node "
            f"result is {node_name!r}."
        )
    if node_boundary_result.node_name != target_node_name:
        raise RuntimeError(
            f"downstream_boundary_result.node_results[{node_index}].node_name "
            f"is {node_boundary_result.node_name!r}, but "
            f"fork_result.target_node_names[{node_index}] is "
            f"{target_node_name!r}."
        )
    return node_boundary_result


def _evaluate_one_fifo_true_candidate(
    *,
    real_world: World,
    fifo_set: OrderControlTvtMpFifoInspectionSetResult,
    candidate_fifo_inspection_result: OrderControlTvtMpCandidateFifoInspectionResult,
    rank_state: OrderControlTvtNodeRankState,
    fork_result: OrderControlBaselineForkResult,
    downstream_boundary_node_result: (
        OrderControlBaselineDownstreamBoundaryNodeResult
    ),
) -> OrderControlTvtMpCandidateLocalVirtualCalculationResult:
    binding_rank_sequence = build_tvt_mp_local_binding_rank_sequence(
        fifo_set,
        candidate_fifo_inspection_result,
        rank_state,
    )
    candidate_local_state = build_tvt_mp_candidate_local_state(
        real_world,
        binding_rank_sequence,
    )
    calculation_state = (
        initialize_tvt_mp_candidate_local_virtual_calculation_state(
            candidate_local_state,
            fork_result.collector,
            downstream_boundary_node_result,
            fork_result.configured_horizon_steps,
        )
    )
    one_candidate_result = run_tvt_mp_candidate_local_virtual_calculation(
        calculation_state
    )
    return one_candidate_result


def _evaluate_complete_node_candidates(
    *,
    real_world: World,
    fifo_set: OrderControlTvtMpFifoInspectionSetResult,
    fifo_node_result: OrderControlTvtNodeMpFifoInspectionResult,
    node_index: int,
    fork_result: OrderControlBaselineForkResult,
    rank_states_by_node_name: Mapping,
) -> tuple[OrderControlTvtMpCandidateLocalVirtualCalculationResult, ...]:
    node_name = fifo_node_result.node_name
    candidate_results: list[
        OrderControlTvtMpCandidateLocalVirtualCalculationResult
    ] = []
    rank_state = None
    downstream_boundary_node_result = None
    for candidate_fifo_inspection_result in (
        fifo_node_result.candidate_fifo_inspection_results
    ):
        if not _candidate_is_fifo_true(candidate_fifo_inspection_result):
            continue
        if rank_state is None:
            rank_state = _rank_state_for_evaluated_node(
                node_name=node_name,
                rank_states_by_node_name=rank_states_by_node_name,
            )
        if downstream_boundary_node_result is None:
            downstream_boundary_node_result = (
                _downstream_boundary_node_result_for_evaluated_node(
                    node_name=node_name,
                    node_index=node_index,
                    fork_result=fork_result,
                )
            )
        one_candidate_result = _evaluate_one_fifo_true_candidate(
            real_world=real_world,
            fifo_set=fifo_set,
            candidate_fifo_inspection_result=candidate_fifo_inspection_result,
            rank_state=rank_state,
            fork_result=fork_result,
            downstream_boundary_node_result=downstream_boundary_node_result,
        )
        candidate_results.append(one_candidate_result)
    return tuple(candidate_results)


def _evaluate_one_fifo_node(
    *,
    real_world: World,
    fifo_set: OrderControlTvtMpFifoInspectionSetResult,
    fifo_node_result: OrderControlTvtNodeMpFifoInspectionResult,
    node_index: int,
    fork_result: OrderControlBaselineForkResult,
    rank_states_by_node_name: Mapping,
) -> OrderControlTvtNodeMpLocalVirtualCalculationResult:
    build_status = fifo_node_result.build_status
    if _build_status_is_normal_not_generated(build_status):
        return _empty_node_result(fifo_node_result)
    if not _build_status_is_complete(build_status):
        raise RuntimeError(
            f"Node {fifo_node_result.node_name!r}: unexpected "
            f"candidate visit set build status {build_status!r}."
        )
    if not _node_has_fifo_true_candidate(fifo_node_result):
        return _empty_node_result(fifo_node_result)
    candidate_results = _evaluate_complete_node_candidates(
        real_world=real_world,
        fifo_set=fifo_set,
        fifo_node_result=fifo_node_result,
        node_index=node_index,
        fork_result=fork_result,
        rank_states_by_node_name=rank_states_by_node_name,
    )
    return OrderControlTvtNodeMpLocalVirtualCalculationResult(
        node_name=fifo_node_result.node_name,
        build_status=fifo_node_result.build_status,
        candidate_local_virtual_calculation_results=candidate_results,
    )
