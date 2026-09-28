"""
TVT-MP upper driver.

One public entry calls the completed TVT-MP stages in official order,
then applies the validated result once. It does not reimplement
candidate search, payment, or final-rank branching.
"""

from __future__ import annotations

from dataclasses import dataclass

from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    confirm_already_arrived_undetermined_visits,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    run_snapshot_fixed_baseline_fork_and_align_undetermined_visits,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    build_tvt_candidate_visit_set,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    build_tvt_inlink_candidate_physical_orders,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    confirm_leading_nonparticipating_decision_window_visits,
)
from uxsim.order_control_tvt_mp_atomic_apply import (
    OrderControlTvtMpAtomicApplySetResult,
    apply_tvt_mp_validated_result,
)
from uxsim.order_control_tvt_mp_candidate_selection import (
    select_tvt_mp_candidates,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    build_tvt_mp_concrete_buyer_candidate_sets,
)
from uxsim.order_control_tvt_mp_economic_evaluation import (
    evaluate_tvt_mp_candidate_economics,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    build_tvt_mp_fifo_inspection_results,
)
from uxsim.order_control_tvt_mp_final_consistency_validation import (
    validate_tvt_mp_final_consistency,
)
from uxsim.order_control_tvt_mp_final_rank import (
    build_tvt_mp_final_ranks,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    build_tvt_mp_general_trade_ranks,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    evaluate_tvt_mp_candidate_local_virtual_calculations,
)
from uxsim.order_control_tvt_mp_payment_and_compensation import (
    calculate_tvt_mp_payments_and_compensations,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.order_control_tvt_right_of_entry_selection import (
    select_right_of_entry_decision_window_visits,
)
from uxsim.uxsim import Vehicle, World


_DECISION_WINDOW_STEPS = 6


@dataclass(frozen=True)
class OrderControlTvtMpDriverResult:
    """Successful driver return. Live traffic objects are not stored."""

    atomic_apply_set_result: OrderControlTvtMpAtomicApplySetResult | None


def run_tvt_mp_driver(real_W) -> OrderControlTvtMpDriverResult:
    """
    Run one TVT-MP decision for every current TVT target Node.

    The only public input is the real World. Target Nodes, the rank
    ledger, and the shared settings are read from that World.
    """
    _require_world(real_W)
    _require_timestep(real_W.T)
    target_node_names = _collect_target_node_names(real_W)
    if len(target_node_names) == 0:
        return OrderControlTvtMpDriverResult(atomic_apply_set_result=None)

    _require_started_timestep_type(real_W.order_control_tvt_driver_started_timestep)
    _reject_same_timestep_restart(real_W)
    _reject_timestep_moved_backward(real_W)
    _require_common_settings(real_W)

    # Record acceptance before baseline or ledger creation. A later
    # exception must not clear this value: completed early confirmation
    # is not rolled back, so the same timestep cannot start again.
    real_W.order_control_tvt_driver_started_timestep = real_W.T

    rank_states = real_W.order_control_tvt_rank_states_by_node_name
    _ensure_target_rank_states(rank_states, target_node_names)

    alignment_result = run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(
        real_W,
        target_node_names=target_node_names,
        baseline_horizon_steps=real_W.order_control_tvt_baseline_horizon_steps,
        rank_states_by_node_name=rank_states,
    )
    arrived_confirmation_result = confirm_already_arrived_undetermined_visits(
        alignment_result,
        rank_states_by_node_name=rank_states,
        real_W=real_W,
    )
    participation_mapping = _build_participation_mapping(
        real_W,
        arrived_confirmation_result,
    )
    leading_confirmation_result = confirm_leading_nonparticipating_decision_window_visits(
        arrived_confirmation_result,
        rank_states_by_node_name=rank_states,
        participates_by_visit_key=participation_mapping,
        real_W=real_W,
    )
    right_of_entry_result = select_right_of_entry_decision_window_visits(
        leading_confirmation_result,
        rank_states_by_node_name=rank_states,
        participates_by_visit_key=participation_mapping,
    )
    candidate_visit_set_result = build_tvt_candidate_visit_set(
        right_of_entry_result,
        rank_states_by_node_name=rank_states,
        max_tvt_candidate_visit_count=(
            real_W.order_control_tvt_max_candidate_visit_count
        ),
    )
    inlink_physical_order_result = build_tvt_inlink_candidate_physical_orders(
        candidate_visit_set_result,
    )
    concrete_buyer_candidate_set_result = build_tvt_mp_concrete_buyer_candidate_sets(
        inlink_physical_order_result,
        participates_by_visit_key=participation_mapping,
    )
    general_trade_rank_result = build_tvt_mp_general_trade_ranks(
        concrete_buyer_candidate_set_result,
        participates_by_visit_key=participation_mapping,
    )
    fifo_inspection_result = build_tvt_mp_fifo_inspection_results(
        general_trade_rank_result,
    )
    local_virtual_calculation_result = (
        evaluate_tvt_mp_candidate_local_virtual_calculations(
            real_W,
            fifo_inspection_result,
            rank_states_by_node_name=rank_states,
        )
    )
    economic_evaluation_result = evaluate_tvt_mp_candidate_economics(
        local_virtual_calculation_result,
        real_W,
    )
    candidate_selection_result = select_tvt_mp_candidates(
        economic_evaluation_result,
        real_W,
    )
    payment_and_compensation_result = calculate_tvt_mp_payments_and_compensations(
        candidate_selection_result,
    )
    final_rank_result = build_tvt_mp_final_ranks(
        payment_and_compensation_result,
    )
    validation_result = validate_tvt_mp_final_consistency(
        final_rank_result,
    )
    atomic_apply_set_result = apply_tvt_mp_validated_result(
        validation_result,
        real_W,
        rank_states,
    )
    return OrderControlTvtMpDriverResult(
        atomic_apply_set_result=atomic_apply_set_result,
    )


def _require_world(real_W):
    if not isinstance(real_W, World):
        raise ValueError(
            "real_W must be a World; got "
            f"{type(real_W).__name__}."
        )


def _require_timestep(timestep):
    if type(timestep) is not int:
        raise ValueError(
            "real_W.T must be a Python int and must not be bool; got "
            f"{type(timestep).__name__}."
        )


def _collect_target_node_names(real_W):
    target_node_names = []
    seen_names = set()
    for node in real_W.NODES:
        if node.order_control_type != "time_value":
            continue
        if node.order_control_eligible is not True:
            continue
        if node.name in seen_names:
            raise RuntimeError(
                "Duplicate TVT target Node name "
                f"{node.name!r} in World.NODES."
            )
        seen_names.add(node.name)
        target_node_names.append(node.name)
    return tuple(target_node_names)


def _require_started_timestep_type(started_timestep):
    if started_timestep is None:
        return
    if type(started_timestep) is not int:
        raise RuntimeError(
            "order_control_tvt_driver_started_timestep must be None or "
            "a Python int; got "
            f"{type(started_timestep).__name__}."
        )


def _reject_same_timestep_restart(real_W):
    started_timestep = real_W.order_control_tvt_driver_started_timestep
    if started_timestep == real_W.T:
        raise RuntimeError(
            "TVT-MP driver was already started at timestep "
            f"{real_W.T}."
        )


def _reject_timestep_moved_backward(real_W):
    started_timestep = real_W.order_control_tvt_driver_started_timestep
    if started_timestep is None:
        return
    if real_W.T < started_timestep:
        raise RuntimeError(
            "TVT-MP driver timestep moved backward: current T="
            f"{real_W.T}, started timestep={started_timestep}."
        )


def _require_common_settings(real_W):
    horizon = real_W.order_control_tvt_baseline_horizon_steps
    if type(horizon) is not int or horizon < _DECISION_WINDOW_STEPS:
        raise ValueError(
            "order_control_tvt_baseline_horizon_steps must be a Python "
            f"int greater than or equal to {_DECISION_WINDOW_STEPS}; got "
            f"{horizon!r}."
        )

    max_candidate_visit_count = real_W.order_control_tvt_max_candidate_visit_count
    if (
        type(max_candidate_visit_count) is not int
        or max_candidate_visit_count < 1
    ):
        raise ValueError(
            "order_control_tvt_max_candidate_visit_count must be a Python "
            "int greater than or equal to 1 when TVT target Nodes exist; "
            f"got {max_candidate_visit_count!r}."
        )

    _require_evaluation_end_margin(real_W)


def _require_evaluation_end_margin(real_W):
    """
    Require horizon + 1 timesteps counted from the evaluation end.

    The evaluation end timestep is the first of those remaining timesteps.
    Unset evaluation end keeps manual driver calls unchanged. The decision
    window length is not part of this count.
    """
    if real_W.order_control_tvt_evaluation_end_timestep is None:
        return
    evaluation_end_timestep = real_W._require_tvt_evaluation_end_timestep()
    horizon = real_W.order_control_tvt_baseline_horizon_steps
    remaining_steps = real_W.TSIZE - evaluation_end_timestep
    required_steps = horizon + 1
    if remaining_steps < required_steps:
        raise ValueError(
            "Insufficient internal timesteps at the evaluation end for "
            "baseline_horizon_steps plus one post-horizon timestep margin: "
            f"evaluation_end_timestep={evaluation_end_timestep}, "
            f"baseline_horizon_steps={horizon}, "
            f"remaining_steps={remaining_steps}, "
            f"required_steps={required_steps}, "
            f"TSIZE={real_W.TSIZE}."
        )


def _ensure_target_rank_states(rank_states, target_node_names):
    if type(rank_states) is not dict:
        raise RuntimeError(
            "order_control_tvt_rank_states_by_node_name must be a dict; got "
            f"{type(rank_states).__name__}."
        )
    for node_name in target_node_names:
        if node_name not in rank_states:
            rank_states[node_name] = OrderControlTvtNodeRankState(node_name)
            continue
        rank_state = rank_states[node_name]
        if not isinstance(rank_state, OrderControlTvtNodeRankState):
            raise RuntimeError(
                "Rank ledger for Node "
                f"{node_name!r} must be OrderControlTvtNodeRankState; got "
                f"{type(rank_state).__name__}."
            )
        if rank_state.node_name != node_name:
            raise RuntimeError(
                "Rank ledger node_name "
                f"{rank_state.node_name!r} does not match dict key "
                f"{node_name!r}."
            )


def _build_participation_mapping(real_W, arrived_confirmation_result):
    """
    Map decision-window VisitKeys to Vehicle.participates_in_order_exchange.

    declared VOT is not read. Visits outside the decision window are omitted.
    """
    alignment_fork_result = arrived_confirmation_result.alignment_fork_result
    baseline_timestep_T = alignment_fork_result.fork_result.baseline_timestep_T
    window_end = baseline_timestep_T + _DECISION_WINDOW_STEPS
    participation_mapping = {}

    for alignment_result in alignment_fork_result.alignment_results:
        for resolved_visit in alignment_result.resolved_undetermined_visits:
            arrival_timestep = resolved_visit.baseline_arrival_timestep
            if arrival_timestep <= baseline_timestep_T:
                continue
            if arrival_timestep > window_end:
                continue
            visit_key = resolved_visit.visit_key
            vehicle_name = visit_key[0]
            participates = _read_participation(real_W, vehicle_name)
            participation_mapping[visit_key] = participates
    return participation_mapping


def _read_participation(real_W, vehicle_name):
    if vehicle_name not in real_W.VEHICLES:
        raise RuntimeError(
            f"Vehicle {vehicle_name!r} is not in real_W.VEHICLES."
        )
    vehicle = real_W.VEHICLES[vehicle_name]
    if not isinstance(vehicle, Vehicle):
        raise RuntimeError(
            f"real_W.VEHICLES[{vehicle_name!r}] must be a Vehicle; got "
            f"{type(vehicle).__name__}."
        )
    if not hasattr(vehicle, "participates_in_order_exchange"):
        raise RuntimeError(
            f"Vehicle {vehicle_name!r} has no participates_in_order_exchange."
        )
    participates = vehicle.participates_in_order_exchange
    if type(participates) is not bool:
        raise RuntimeError(
            "Vehicle "
            f"{vehicle_name!r} participates_in_order_exchange must be a "
            f"Python bool; got {type(participates).__name__}."
        )
    return participates
