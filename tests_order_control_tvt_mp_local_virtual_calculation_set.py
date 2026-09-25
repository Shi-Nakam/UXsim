# Tests for the TVT-MP all-candidate local virtual calculation entry.
#
# Run from the repository root:
#   python tests_order_control_tvt_mp_local_virtual_calculation_set.py

from __future__ import annotations

import ast
import copy
import dataclasses
import inspect
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from uxsim.order_control_baseline_collector import OrderControlBaselineCollector
from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
    OrderControlBaselineDownstreamBoundaryResult,
)
from uxsim.order_control_baseline_driver import OrderControlBaselineForkResult
from uxsim.order_control_tvt_arrived_undetermined_confirmation import (
    OrderControlTvtArrivedUndeterminedConfirmationResult,
    OrderControlTvtNodeArrivedUndeterminedConfirmationResult,
)
from uxsim.order_control_tvt_baseline_alignment import (
    OrderControlTvtSnapshotUndeterminedAlignmentResult,
)
from uxsim.order_control_tvt_baseline_fork_alignment import (
    OrderControlTvtBaselineForkAlignmentResult,
)
from uxsim.order_control_tvt_candidate_visit_set import (
    OrderControlTvtCandidateVisitSetResult,
    OrderControlTvtCandidateVisitSetStatus,
    OrderControlTvtNodeCandidateVisitSetResult,
)
from uxsim.order_control_tvt_inlink_candidate_physical_order import (
    OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    OrderControlTvtNodeInlinkCandidatePhysicalOrderResult,
)
from uxsim.order_control_tvt_leading_nonparticipating_confirmation import (
    OrderControlTvtLeadingNonparticipatingConfirmationResult,
    OrderControlTvtNodeLeadingNonparticipatingConfirmationResult,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidateFinalNodeRecord,
    OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    OrderControlTvtMpCandidateLocalVirtualCalculationStopReason,
    OrderControlTvtMpCandidateUnresolvedReason,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
    OrderControlTvtMpConcreteBuyerCandidateSetResult,
    OrderControlTvtNodeMpConcreteBuyerCandidateSetResult,
)
from uxsim.order_control_tvt_mp_fifo_inspection import (
    OrderControlTvtMpCandidateFifoInspectionResult,
    OrderControlTvtMpFifoInspectionSetResult,
    OrderControlTvtNodeMpFifoInspectionResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
    OrderControlTvtMpGeneralTradeRankSetResult,
    OrderControlTvtNodeMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRankSequence,
)
from uxsim.order_control_tvt_mp_local_virtual_calculation_set import (
    OrderControlTvtMpLocalVirtualCalculationSetResult,
    OrderControlTvtNodeMpLocalVirtualCalculationResult,
    evaluate_tvt_mp_candidate_local_virtual_calculations,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
)
from uxsim.order_control_tvt_right_of_entry_selection import (
    OrderControlTvtNodeRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionResult,
    OrderControlTvtRightOfEntrySelectionStatus,
)
from uxsim.uxsim import World
import uxsim.order_control_tvt_mp_local_virtual_calculation_set as set_mod


BASELINE_T = 10
COMPLETE = OrderControlTvtCandidateVisitSetStatus.BASELINE_INFORMATION_COMPLETE
PRODUCTION_PATH = (
    Path(__file__).resolve().parent
    / "uxsim"
    / "order_control_tvt_mp_local_virtual_calculation_set.py"
)

_NORMAL_NOT_GENERATED = (
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
    OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_UNRESOLVED_ARRIVALS,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE,
    OrderControlTvtCandidateVisitSetStatus.UNRESOLVED_CANDIDATE_PASSAGES,
)

_FORBIDDEN_SET_FIELD_NAMES = {
    "candidate_id",
    "candidate_index",
    "fifo_false_records",
    "candidate_count",
    "fifo_true_count",
    "fifo_false_count",
    "resolved_count",
    "unresolved_count",
    "resolved_results",
    "unresolved_results",
    "economic_evaluation_candidates",
    "local_world",
    "candidate_local_state",
    "calculation_state",
    "expected_time_saving",
    "waiting_increase",
    "G_b",
    "R_s",
    "G",
    "R",
    "surplus",
    "utility",
    "payment",
    "compensation",
}

_FORBIDDEN_NODE_FIELD_NAMES = set(_FORBIDDEN_SET_FIELD_NAMES) | {
    "fifo_inspection_set_result",
}


def _field_names(cls) -> tuple[str, ...]:
    names = []
    for field in dataclasses.fields(cls):
        names.append(field.name)
    return tuple(names)


def _assert_frozen(instance) -> None:
    field_name = dataclasses.fields(instance)[0].name
    try:
        setattr(instance, field_name, None)
        raise AssertionError(f"expected frozen type {type(instance).__name__}")
    except dataclasses.FrozenInstanceError:
        pass


def _assert_no_live_objects(value, *, path: str) -> None:
    if value is None:
        return
    if isinstance(value, (str, bytes, int, float, bool)):
        return
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            _assert_no_live_objects(item, path=f"{path}[{index}]")
        return
    type_name = type(value).__name__
    if type_name in {"World", "Node", "Link", "Vehicle"}:
        raise AssertionError(f"{path} holds live {type_name}")
    if "LocalState" in type_name or "CalculationState" in type_name:
        raise AssertionError(f"{path} holds live {type_name}")
    if dataclasses.is_dataclass(value):
        for field in dataclasses.fields(value):
            _assert_no_live_objects(
                getattr(value, field.name),
                path=f"{path}.{field.name}",
            )
        return


def _new_world(name: str) -> World:
    world = World(
        name=name,
        deltan=1,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    world.addNode("orig_a", 0, 0)
    world.addNode("orig_b", 0, 1)
    world.addNode("orig_c", 0, 2)
    world.addNode(
        "merge",
        1,
        0,
        order_control_eligible=True,
        order_control_type="time_value",
        flow_capacity=1.0,
        number_of_lanes=1,
    )
    world.addNode("dest", 2, 0)
    world.addNode("dest_b", 2, 1)
    world.addLink("in_a", "orig_a", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("in_b", "orig_b", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("in_c", "orig_c", "merge", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("out", "merge", "dest", length=200, free_flow_speed=20, number_of_lanes=1)
    world.addLink("side", "merge", "dest_b", length=200, free_flow_speed=20, number_of_lanes=1)
    return world


def _plain_world(*, name: str = "tvt_mp_set_entry", timestep: int = BASELINE_T) -> World:
    world = _new_world(name)
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = timestep
    return world


def _place(world, vehicle, link, route) -> None:
    vehicle.link = link
    vehicle.state = "run"
    vehicle.x = link.length
    vehicle.x_old = link.length
    vehicle.x_next = link.length
    vehicle.v = 4.0
    vehicle.lane = 0
    vehicle.leader = None
    vehicle.follower = None
    vehicle.route_next_link = route
    vehicle.link_arrival_time = 5.0
    vehicle.move_remain = 2.0
    vehicle.flag_waiting_for_trip_end = 0
    world.VEHICLES_RUNNING[vehicle.name] = vehicle


def _open_real_world_capacities(world, node_name: str = "merge") -> None:
    node = world.get_node(node_name)
    node.flow_capacity_remain = 10.0
    node.order_control_clearance_timesteps = 0
    node.last_order_control_inlink = None
    node.last_order_control_entry_timestep = None
    for link in list(node.inlinks.values()) + list(node.outlinks.values()):
        link.capacity_out_remain = 10.0
        link.capacity_in_remain = 10.0


def _block_clearance_from_other_inlink(world, node_name: str = "merge") -> None:
    node = world.get_node(node_name)
    other_inlink = world.get_link("in_b")
    node.last_order_control_inlink = other_inlink
    node.last_order_control_entry_timestep = BASELINE_T
    node.order_control_clearance_timesteps = 100


def _outlink_boundary(name: str, terminal: str, active: int, transferred: int):
    return OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name=name,
        terminal_node_name=terminal,
        active_timestep_count=active,
        transferred_vehicle_count=transferred,
    )


def _constrained_sink_boundary(node_name: str = "merge"):
    return OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name=node_name,
        outlink_results=(
            _outlink_boundary("out", "dest", 0, 0),
            _outlink_boundary("side", "dest_b", 0, 0),
        ),
    )


def _overall_boundary(*node_results):
    return OrderControlBaselineDownstreamBoundaryResult(node_results=tuple(node_results))


def _trade_rank(
    *,
    buyers_sorted: tuple,
    sellers_sorted: tuple = (),
    nonparticipating_visits_sorted: tuple = (),
    last_buyer_rank: int | None = None,
    trade_scope: tuple | None = None,
    trade_order: tuple | None = None,
) -> OrderControlTvtMpGeneralTradeRankResult:
    buyers = tuple(buyers_sorted)
    sellers = tuple(sellers_sorted)
    if trade_scope is None:
        trade_scope = buyers + sellers + tuple(nonparticipating_visits_sorted)
    if trade_order is None:
        trade_order = trade_scope
    if last_buyer_rank is None:
        last_buyer_rank = len(buyers)
    trade_rank_by_visit_key = {}
    for rank_number, visit_key in enumerate(trade_order, start=1):
        trade_rank_by_visit_key[visit_key] = rank_number
    return OrderControlTvtMpGeneralTradeRankResult(
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=buyers,
        ),
        buyers_sorted=buyers,
        sellers_sorted=sellers,
        nonparticipating_visits_sorted=tuple(nonparticipating_visits_sorted),
        last_buyer_rank=last_buyer_rank,
        trade_scope=tuple(trade_scope),
        trade_order=tuple(trade_order),
        trade_rank_by_visit_key=trade_rank_by_visit_key,
    )


def _dummy_binding_sequence(node_name: str, concrete):
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=BASELINE_T,
        concrete_buyer_candidate_set=concrete,
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=(),
        outside_trade_scope_inside_k_fixed_visits=(),
        visits_in_binding_order=(),
        k_last_buyer=1,
        k_decision_window=1,
        k_fixed=1,
    )


def _dummy_one_candidate_result(
    *,
    node_name: str,
    concrete,
    sequence,
    resolved: bool,
    horizon: int = 6,
):
    if resolved:
        stop_reason = OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
        unresolved_reasons = ()
    else:
        stop_reason = (
            OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
        )
        unresolved_reasons = (
            OrderControlTvtMpCandidateUnresolvedReason.REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON,
        )
    return OrderControlTvtMpCandidateLocalVirtualCalculationResult(
        node_name=node_name,
        concrete_buyer_candidate_set=concrete,
        binding_rank_sequence=sequence,
        baseline_timestep_T=BASELINE_T,
        configured_horizon_steps=horizon,
        final_virtual_timestep=BASELINE_T,
        final_offset=0,
        simulated_timestep_count=1,
        stop_reason=stop_reason,
        resolved=resolved,
        required_passage_records=(),
        unresolved_reasons=unresolved_reasons,
        timestep_results=(),
        final_vehicle_records=(),
        final_inlink_records=(),
        final_outlink_records=(),
        final_node_record=OrderControlTvtMpCandidateFinalNodeRecord(
            node_name=node_name,
            incoming_vehicle_names=(),
            flow_capacity_remain=1.0,
            last_order_control_inlink_name=None,
            last_order_control_entry_timestep=None,
            order_control_clearance_timesteps=0,
        ),
        final_boundary_records=(),
    )


def _build_fifo_chain(
    *,
    node_specs,
    collector=None,
    baseline_timestep_T: int = BASELINE_T,
    configured_horizon_steps: int = 6,
    downstream_boundary_result=None,
):
    if collector is None:
        collector = object()
    node_names = []
    alignments = []
    arrived_nodes = []
    leading_nodes = []
    right_nodes = []
    visit_nodes = []
    inlink_nodes = []
    concrete_nodes = []
    trade_nodes = []
    fifo_nodes = []
    for spec in node_specs:
        node_name = spec["name"]
        node_names.append(node_name)
        status = spec.get("status", COMPLETE)
        arrived_keys = spec.get("arrived_keys", ())
        leading_keys = spec.get("leading_keys", ())
        remaining_keys = spec.get("remaining_keys", ())
        k_confirmed_before = spec.get("k_confirmed_before", 0)
        candidate_specs = spec.get("candidates", ())
        alignments.append(
            OrderControlTvtSnapshotUndeterminedAlignmentResult(
                node_name=node_name,
                resolved_undetermined_visits=(),
                unresolved_undetermined_visits=(),
                unregistered_collector_visit_keys=(),
            )
        )
        arrived_nodes.append(
            OrderControlTvtNodeArrivedUndeterminedConfirmationResult(
                node_name=node_name,
                confirmed_arrived_visit_keys=arrived_keys,
                confirm_result=OrderControlTvtConfirmResult(
                    k_confirmed_before=k_confirmed_before,
                    k_confirmed_after=k_confirmed_before + len(arrived_keys),
                    newly_confirmed_count=len(arrived_keys),
                ),
            )
        )
        leading_nodes.append(
            OrderControlTvtNodeLeadingNonparticipatingConfirmationResult(
                node_name=node_name,
                decision_window_visit_keys=leading_keys + remaining_keys,
                confirmed_leading_nonparticipating_visit_keys=leading_keys,
                remaining_decision_window_visit_keys=remaining_keys,
                confirm_result=OrderControlTvtConfirmResult(
                    k_confirmed_before=k_confirmed_before + len(arrived_keys),
                    k_confirmed_after=(
                        k_confirmed_before + len(arrived_keys) + len(leading_keys)
                    ),
                    newly_confirmed_count=len(leading_keys),
                ),
            )
        )
        right_key = spec.get("right_of_entry_visit_key", ("buy", 1))
        right_nodes.append(
            OrderControlTvtNodeRightOfEntrySelectionResult(
                node_name=node_name,
                selection_status=OrderControlTvtRightOfEntrySelectionStatus.SELECTED,
                right_of_entry_visit_key=right_key,
                k_confirmed_before=k_confirmed_before,
            )
        )
        visit_nodes.append(
            OrderControlTvtNodeCandidateVisitSetResult(
                node_name=node_name,
                build_status=status,
                right_of_entry_visit_key=right_key,
                right_of_entry_baseline_passage_timestep=12,
                k_confirmed_before=k_confirmed_before,
                p_minus_one_eligible_visit_count_before_limit=2,
                candidate_visits=(),
            )
        )
        inlink_nodes.append(
            OrderControlTvtNodeInlinkCandidatePhysicalOrderResult(
                node_name=node_name,
                build_status=status,
                inlink_candidate_physical_orders=(),
            )
        )
        trade_ranks = []
        fifo_tickets = []
        concrete_sets = []
        for candidate_spec in candidate_specs:
            trade_rank = candidate_spec["trade_rank"]
            preserves_fifo = candidate_spec.get("fifo", True)
            trade_ranks.append(trade_rank)
            concrete_sets.append(trade_rank.concrete_buyer_candidate_set)
            fifo_tickets.append(
                OrderControlTvtMpCandidateFifoInspectionResult(
                    general_trade_rank_result=trade_rank,
                    preserves_inlink_fifo=preserves_fifo,
                )
            )
        concrete_nodes.append(
            OrderControlTvtNodeMpConcreteBuyerCandidateSetResult(
                node_name=node_name,
                build_status=status,
                buyer_candidate_inlink_prefix_results=(),
                concrete_buyer_candidate_sets=tuple(concrete_sets),
            )
        )
        trade_nodes.append(
            OrderControlTvtNodeMpGeneralTradeRankResult(
                node_name=node_name,
                build_status=status,
                candidate_trade_rank_results=tuple(trade_ranks),
            )
        )
        fifo_nodes.append(
            OrderControlTvtNodeMpFifoInspectionResult(
                node_name=node_name,
                build_status=status,
                candidate_fifo_inspection_results=tuple(fifo_tickets),
            )
        )
    fork_result = OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=tuple(node_names),
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=configured_horizon_steps,
        fork_steps_executed=configured_horizon_steps,
        final_fork_timestep=baseline_timestep_T + configured_horizon_steps,
        registered_visit_count=1,
        inlink_physical_orders=(),
        downstream_boundary_result=downstream_boundary_result,
    )
    alignment_fork = OrderControlTvtBaselineForkAlignmentResult(
        fork_result=fork_result,
        alignment_results=tuple(alignments),
    )
    arrived = OrderControlTvtArrivedUndeterminedConfirmationResult(
        alignment_fork_result=alignment_fork,
        node_confirmation_results=tuple(arrived_nodes),
    )
    leading = OrderControlTvtLeadingNonparticipatingConfirmationResult(
        arrived_confirmation_result=arrived,
        node_confirmation_results=tuple(leading_nodes),
    )
    right_of_entry = OrderControlTvtRightOfEntrySelectionResult(
        leading_confirmation_result=leading,
        node_selection_results=tuple(right_nodes),
    )
    candidate_visit_set = OrderControlTvtCandidateVisitSetResult(
        right_of_entry_selection_result=right_of_entry,
        max_tvt_candidate_visit_count=2,
        node_candidate_set_results=tuple(visit_nodes),
    )
    inlink_result = OrderControlTvtInlinkCandidatePhysicalOrderSetResult(
        candidate_visit_set_result=candidate_visit_set,
        node_inlink_candidate_physical_order_results=tuple(inlink_nodes),
    )
    concrete_set_result = OrderControlTvtMpConcreteBuyerCandidateSetResult(
        inlink_candidate_physical_order_result=inlink_result,
        node_concrete_buyer_candidate_set_results=tuple(concrete_nodes),
    )
    trade_set = OrderControlTvtMpGeneralTradeRankSetResult(
        concrete_buyer_candidate_set_result=concrete_set_result,
        node_trade_rank_results=tuple(trade_nodes),
    )
    fifo_set = OrderControlTvtMpFifoInspectionSetResult(
        general_trade_rank_set_result=trade_set,
        node_fifo_inspection_results=tuple(fifo_nodes),
    )
    return fifo_set


def _replace_fork(fifo_set, **fields):
    trade_set = fifo_set.general_trade_rank_set_result
    concrete = trade_set.concrete_buyer_candidate_set_result
    inlink = concrete.inlink_candidate_physical_order_result
    visit_set = inlink.candidate_visit_set_result
    right = visit_set.right_of_entry_selection_result
    leading = right.leading_confirmation_result
    arrived = leading.arrived_confirmation_result
    alignment = arrived.alignment_fork_result
    new_fork = dataclasses.replace(alignment.fork_result, **fields)
    new_alignment = dataclasses.replace(alignment, fork_result=new_fork)
    new_arrived = dataclasses.replace(arrived, alignment_fork_result=new_alignment)
    new_leading = dataclasses.replace(leading, arrived_confirmation_result=new_arrived)
    new_right = dataclasses.replace(right, leading_confirmation_result=new_leading)
    new_visit = dataclasses.replace(visit_set, right_of_entry_selection_result=new_right)
    new_inlink = dataclasses.replace(inlink, candidate_visit_set_result=new_visit)
    new_concrete = dataclasses.replace(
        concrete,
        inlink_candidate_physical_order_result=new_inlink,
    )
    new_trade = dataclasses.replace(
        trade_set,
        concrete_buyer_candidate_set_result=new_concrete,
    )
    return dataclasses.replace(fifo_set, general_trade_rank_set_result=new_trade)


def _complete_node_spec(node_name, candidates, **extra):
    spec = {"name": node_name, "status": COMPLETE, "candidates": list(candidates)}
    spec.update(extra)
    return spec


def _not_generated_node_spec(node_name, status):
    return {"name": node_name, "status": status, "candidates": []}


_UNSET = object()


def _one_true_merge_chain(
    *,
    fifo=True,
    remaining_keys=(("buy", 1),),
    downstream_boundary_result=_UNSET,
    configured_horizon_steps=6,
    collector=None,
    extra_candidates=(),
):
    trade = _trade_rank(buyers_sorted=(("buy", 1),))
    candidates = [{"trade_rank": trade, "fifo": fifo}]
    candidates.extend(extra_candidates)
    if downstream_boundary_result is _UNSET:
        downstream_boundary_result = _overall_boundary(_constrained_sink_boundary())
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                candidates,
                remaining_keys=remaining_keys,
            )
        ],
        collector=collector,
        configured_horizon_steps=configured_horizon_steps,
        downstream_boundary_result=downstream_boundary_result,
    )
    return fifo_set


def _rank_states(*node_names):
    mapping = {}
    for node_name in node_names:
        mapping[node_name] = OrderControlTvtNodeRankState(node_name)
    return mapping


class _StageHarness:
    def __init__(
        self,
        *,
        resolved_flags=None,
        binding_error=None,
        local_state_error=None,
        init_error=None,
        run_error=None,
        raise_on_run=None,
        raise_on_binding=None,
        raise_on_local_state=None,
        raise_on_init=None,
    ) -> None:
        self.resolved_flags = resolved_flags
        self.binding_error = binding_error
        self.local_state_error = local_state_error
        self.init_error = init_error
        self.run_error = run_error
        self.raise_on_run = raise_on_run
        self.raise_on_binding = raise_on_binding
        self.raise_on_local_state = raise_on_local_state
        self.raise_on_init = raise_on_init
        self.binding_calls = []
        self.local_state_calls = []
        self.init_calls = []
        self.run_calls = []
        self.copied_worlds = []
        self.local_states = []
        self.calc_states = []
        self.original_world_copy = World.copy

    def binding(self, fifo_set, ticket, rank_state):
        self.binding_calls.append((fifo_set, ticket, rank_state))
        if self.raise_on_binding == len(self.binding_calls):
            raise self.binding_error
        if self.binding_error is not None and self.raise_on_binding is None:
            raise self.binding_error
        concrete = ticket.general_trade_rank_result.concrete_buyer_candidate_set
        return _dummy_binding_sequence(rank_state.node_name, concrete)

    def local_state(self, real_W, sequence):
        self.local_state_calls.append((real_W, sequence))
        if self.raise_on_local_state == len(self.local_state_calls):
            raise self.local_state_error
        if self.local_state_error is not None and self.raise_on_local_state is None:
            raise self.local_state_error
        local = SimpleNamespace(
            binding_rank_sequence=sequence,
            local_world=object(),
            target_node=object(),
            local_vehicles=(object(),),
        )
        self.local_states.append(local)
        return local

    def init(self, candidate_local_state, collector, boundary, horizon):
        self.init_calls.append(
            (candidate_local_state, collector, boundary, horizon)
        )
        if self.raise_on_init == len(self.init_calls):
            raise self.init_error
        if self.init_error is not None and self.raise_on_init is None:
            raise self.init_error
        calc = SimpleNamespace(candidate_local_state=candidate_local_state)
        self.calc_states.append(calc)
        return calc

    def run(self, calculation_state):
        self.run_calls.append(calculation_state)
        if self.raise_on_run == len(self.run_calls):
            raise self.run_error
        if self.run_error is not None and self.raise_on_run is None:
            raise self.run_error
        sequence = calculation_state.candidate_local_state.binding_rank_sequence
        resolved = True
        if self.resolved_flags is not None:
            resolved = self.resolved_flags[len(self.run_calls) - 1]
        return _dummy_one_candidate_result(
            node_name=sequence.node_name,
            concrete=sequence.concrete_buyer_candidate_set,
            sequence=sequence,
            resolved=resolved,
        )

    def world_copy(self, world):
        copied = self.original_world_copy(world)
        self.copied_worlds.append(copied)
        return copied


@contextmanager
def _patched_stage_apis(harness: _StageHarness):
    with (
        patch.object(
            set_mod,
            "build_tvt_mp_local_binding_rank_sequence",
            harness.binding,
        ),
        patch.object(
            set_mod,
            "build_tvt_mp_candidate_local_state",
            harness.local_state,
        ),
        patch.object(
            set_mod,
            "initialize_tvt_mp_candidate_local_virtual_calculation_state",
            harness.init,
        ),
        patch.object(
            set_mod,
            "run_tvt_mp_candidate_local_virtual_calculation",
            harness.run,
        ),
        patch.object(World, "copy", harness.world_copy),
    ):
        yield harness


def _evaluate(world, fifo_set, rank_states):
    return evaluate_tvt_mp_candidate_local_virtual_calculations(
        world,
        fifo_set,
        rank_states_by_node_name=rank_states,
    )


def _fifo_tickets(fifo_set, node_index=0):
    return fifo_set.node_fifo_inspection_results[node_index].candidate_fifo_inspection_results


def _world_fingerprint(world):
    incoming_names = []
    merge = world.get_node("merge")
    for vehicle in merge.incoming_vehicles:
        incoming_names.append(vehicle.name)
    vehicle_positions = []
    for name, vehicle in world.VEHICLES.items():
        vehicle_positions.append((name, vehicle.x, vehicle.state, vehicle.link.name if vehicle.link is not None else None))
    rng_state = copy.deepcopy(world.rng.bit_generator.state)
    return {
        "T": world.T,
        "TIME": world.TIME,
        "incoming": tuple(incoming_names),
        "vehicles": tuple(vehicle_positions),
        "rng": rng_state,
        "clearance": merge.order_control_clearance_timesteps,
        "capacity": merge.flow_capacity_remain,
    }


def _register_snapshot(collector, vehicle, *, route_name: str, node_name: str = "merge"):
    visit = vehicle.order_control_current_visit
    collector.register_snapshot_visit(
        vehicle_name=vehicle.name,
        vehicle_id=vehicle.id,
        node_name=node_name,
        inlink_name=vehicle.link.name,
        visit_id=visit["visit_id"],
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=8,
        arrival_tiebreaker=0.1,
        route_next_link_name=route_name,
        baseline_passage_timestep=None,
    )


def _place_buyer(world, vehicle, *, inlink_name: str, route_name: str) -> tuple:
    inlink = world.get_link(inlink_name)
    route = world.get_link(route_name)
    merge = world.get_node("merge")
    _place(world, vehicle, inlink, route)
    vehicle.begin_order_control_visit_on_link_entry()
    vehicle.order_control_current_visit["arrival_time"] = 1.0
    vehicle.order_control_current_visit["arrival_tiebreaker"] = 0.1
    inlink.vehicles.append(vehicle)
    merge.incoming_vehicles.append(vehicle)
    visit = vehicle.order_control_current_visit
    return (vehicle.name, visit["visit_id"])


def _prepare_end_to_end_buyers(
    vehicle_specs,
    *,
    horizon: int,
    block_clearance: bool = False,
    fifo_flags=None,
    downstream_boundary_result=None,
):
    world = _new_world("tvt_mp_set_entry_e2e")
    created = {}
    for spec in vehicle_specs:
        created[spec["name"]] = world.addVehicle(
            spec["origin"],
            spec["dest"],
            0,
            name=spec["name"],
        )
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = BASELINE_T
    collector = OrderControlBaselineCollector()
    visit_keys = []
    candidates = []
    for index, spec in enumerate(vehicle_specs):
        vehicle = created[spec["name"]]
        visit_key = _place_buyer(
            world,
            vehicle,
            inlink_name=spec["inlink"],
            route_name=spec["route"],
        )
        visit_keys.append(visit_key)
        _register_snapshot(collector, vehicle, route_name=spec["route"])
        fifo_flag = True
        if fifo_flags is not None:
            fifo_flag = fifo_flags[index]
        candidates.append(
            {
                "trade_rank": _trade_rank(buyers_sorted=(visit_key,)),
                "fifo": fifo_flag,
            }
        )
    remaining_keys = ()
    if visit_keys:
        remaining_keys = (visit_keys[0],)
    if downstream_boundary_result is None:
        downstream_boundary_result = _overall_boundary(_constrained_sink_boundary())
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                candidates,
                remaining_keys=remaining_keys,
            )
        ],
        collector=collector,
        configured_horizon_steps=horizon,
        downstream_boundary_result=downstream_boundary_result,
    )
    _open_real_world_capacities(world)
    if block_clearance:
        _block_clearance_from_other_inlink(world)
    rank_states = _rank_states("merge")
    return world, fifo_set, rank_states, collector, visit_keys, created


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


def test_node_and_set_results_are_frozen_dataclasses_with_tuple_fields():
    world = _plain_world()
    fifo_set = _build_fifo_chain(
        node_specs=[_not_generated_node_spec("merge", _NORMAL_NOT_GENERATED[0])],
        downstream_boundary_result=None,
    )
    result = _evaluate(world, fifo_set, {})
    _assert_frozen(result)
    _assert_frozen(result.node_local_virtual_calculation_results[0])
    assert dataclasses.is_dataclass(OrderControlTvtNodeMpLocalVirtualCalculationResult)
    assert dataclasses.is_dataclass(OrderControlTvtMpLocalVirtualCalculationSetResult)
    assert _field_names(OrderControlTvtNodeMpLocalVirtualCalculationResult) == (
        "node_name",
        "build_status",
        "candidate_local_virtual_calculation_results",
    )
    assert _field_names(OrderControlTvtMpLocalVirtualCalculationSetResult) == (
        "fifo_inspection_set_result",
        "node_local_virtual_calculation_results",
    )
    assert isinstance(result.node_local_virtual_calculation_results, tuple)
    assert isinstance(
        result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results,
        tuple,
    )


def test_set_result_keeps_input_fifo_object_and_has_no_forbidden_fields():
    world = _plain_world()
    fifo_set = _build_fifo_chain(
        node_specs=[_not_generated_node_spec("merge", _NORMAL_NOT_GENERATED[0])],
        downstream_boundary_result=None,
    )
    result = _evaluate(world, fifo_set, {})
    assert result.fifo_inspection_set_result is fifo_set
    node_fields = set(_field_names(OrderControlTvtNodeMpLocalVirtualCalculationResult))
    set_fields = set(_field_names(OrderControlTvtMpLocalVirtualCalculationSetResult))
    assert node_fields.isdisjoint(_FORBIDDEN_NODE_FIELD_NAMES)
    assert set_fields.isdisjoint(_FORBIDDEN_SET_FIELD_NAMES)
    _assert_no_live_objects(result, path="set_result")


def test_candidate_results_are_existing_one_candidate_type():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    candidate_result = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results[0]
    assert isinstance(
        candidate_result,
        OrderControlTvtMpCandidateLocalVirtualCalculationResult,
    )
    assert candidate_result.concrete_buyer_candidate_set is (
        _fifo_tickets(fifo_set)[0].general_trade_rank_result.concrete_buyer_candidate_set
    )


def test_public_api_signature_and_absence_of_set_or_node_state_apis():
    signature = inspect.signature(evaluate_tvt_mp_candidate_local_virtual_calculations)
    parameters = list(signature.parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "real_W",
        "fifo_inspection_set_result",
        "rank_states_by_node_name",
    ]
    assert parameters[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
    assert parameters[1].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
    assert parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
    source = ast.parse(PRODUCTION_PATH.read_text(encoding="utf-8"))
    public_functions = []
    public_classes = []
    for node in source.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            public_functions.append(node.name)
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            public_classes.append(node.name)
    assert public_functions == ["evaluate_tvt_mp_candidate_local_virtual_calculations"]
    assert public_classes == [
        "OrderControlTvtNodeMpLocalVirtualCalculationResult",
        "OrderControlTvtMpLocalVirtualCalculationSetResult",
    ]
    world = _plain_world()
    fifo_set = _build_fifo_chain(
        node_specs=[_not_generated_node_spec("merge", _NORMAL_NOT_GENERATED[0])],
        downstream_boundary_result=None,
    )
    try:
        evaluate_tvt_mp_candidate_local_virtual_calculations(
            world,
            fifo_set,
            {},
        )
        raise AssertionError("expected TypeError for positional rank_states")
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# Input checks
# ---------------------------------------------------------------------------


def test_rejects_non_world_without_copying():
    fifo_set = _one_true_merge_chain()
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(object(), fifo_set, _rank_states("merge"))
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "World" in str(error)
    assert harness.copied_worlds == []
    assert harness.binding_calls == []


def test_rejects_non_fifo_result_without_copying():
    world = _plain_world()
    fingerprint = _world_fingerprint(world)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, object(), _rank_states("merge"))
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "FifoInspectionSetResult" in str(error)
    assert harness.copied_worlds == []
    assert _world_fingerprint(world) == fingerprint


def test_rejects_non_mapping_rank_states_without_mutating_upstream():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    fifo_id = id(fifo_set)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, ["merge"])
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "Mapping" in str(error)
    assert id(fifo_set) == fifo_id
    assert harness.copied_worlds == []


def test_real_world_timestep_must_match_baseline_and_bool_is_rejected():
    world = _plain_world(timestep=11)
    fifo_set = _one_true_merge_chain()
    fingerprint = _world_fingerprint(world)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected ValueError for T mismatch")
        except ValueError as error:
            assert "baseline_timestep_T" in str(error)
    assert harness.copied_worlds == []
    assert _world_fingerprint(world) == fingerprint

    world.T = BASELINE_T
    matching = _evaluate(world, _build_fifo_chain(
        node_specs=[_not_generated_node_spec("merge", _NORMAL_NOT_GENERATED[0])],
        downstream_boundary_result=None,
    ), {})
    assert matching.node_local_virtual_calculation_results[0].build_status is _NORMAL_NOT_GENERATED[0]

    world.T = True
    try:
        _evaluate(world, fifo_set, _rank_states("merge"))
        raise AssertionError("expected ValueError for bool T")
    except ValueError as error:
        assert "Python int" in str(error)


def test_fork_baseline_timestep_bool_is_runtime_error():
    world = _plain_world()
    fifo_set = _replace_fork(_one_true_merge_chain(), baseline_timestep_T=True)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "baseline_timestep_T" in str(error)
    assert harness.copied_worlds == []
    assert harness.binding_calls == []


# ---------------------------------------------------------------------------
# Node order
# ---------------------------------------------------------------------------


def test_node_order_follows_fifo_and_target_and_boundary_index():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("z_buy", 1),))
    second = _trade_rank(buyers_sorted=(("a_buy", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec("z_node", [{"trade_rank": first, "fifo": True}]),
            _complete_node_spec("a_node", [{"trade_rank": second, "fifo": True}]),
        ],
        downstream_boundary_result=_overall_boundary(
            _constrained_sink_boundary("z_node"),
            _constrained_sink_boundary("a_node"),
        ),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("z_node", "a_node"))
    names = []
    for node_result in result.node_local_virtual_calculation_results:
        names.append(node_result.node_name)
    assert names == ["z_node", "a_node"]
    assert names != sorted(names)
    fork = fifo_set.general_trade_rank_set_result.concrete_buyer_candidate_set_result.inlink_candidate_physical_order_result.candidate_visit_set_result.right_of_entry_selection_result.leading_confirmation_result.arrived_confirmation_result.alignment_fork_result.fork_result
    assert fork.target_node_names == ("z_node", "a_node")
    assert fork.downstream_boundary_result.node_results[0].node_name == "z_node"
    assert fork.downstream_boundary_result.node_results[1].node_name == "a_node"
    assert harness.init_calls[0][2] is fork.downstream_boundary_result.node_results[0]
    assert harness.init_calls[1][2] is fork.downstream_boundary_result.node_results[1]


def test_node_count_mismatch_with_target_names_raises_runtime_error():
    world = _plain_world()
    fifo_set = _replace_fork(
        _one_true_merge_chain(),
        target_node_names=("merge", "other"),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "count" in str(error)
    assert harness.binding_calls == []


def test_node_name_mismatch_with_target_names_raises_runtime_error():
    world = _plain_world()
    fifo_set = _replace_fork(
        _one_true_merge_chain(),
        target_node_names=("other",),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "other" in str(error)
            assert "merge" in str(error)
    assert harness.binding_calls == []


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def test_normal_not_generated_statuses_return_empty_without_rank_boundary_or_copy():
    world = _plain_world()
    for status in _NORMAL_NOT_GENERATED:
        fifo_set = _build_fifo_chain(
            node_specs=[_not_generated_node_spec("merge", status)],
            downstream_boundary_result=None,
        )
        harness = _StageHarness()
        with _patched_stage_apis(harness):
            result = _evaluate(world, fifo_set, {})
        node_result = result.node_local_virtual_calculation_results[0]
        assert node_result.node_name == "merge"
        assert node_result.build_status is status
        assert node_result.candidate_local_virtual_calculation_results == ()
        assert harness.binding_calls == []
        assert harness.copied_worlds == []
        assert harness.init_calls == []


def test_complete_with_zero_candidates_is_empty_and_does_not_require_rank_or_boundary():
    world = _plain_world()
    fifo_set = _build_fifo_chain(
        node_specs=[_complete_node_spec("merge", [])],
        downstream_boundary_result=None,
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, {})
    node_result = result.node_local_virtual_calculation_results[0]
    assert node_result.build_status is COMPLETE
    assert node_result.candidate_local_virtual_calculation_results == ()
    assert harness.binding_calls == []
    assert harness.copied_worlds == []


def test_complete_all_fifo_false_is_empty_and_keeps_false_on_fifo_result():
    world = _plain_world()
    fifo_set = _one_true_merge_chain(fifo=False, downstream_boundary_result=None)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, {})
    node_result = result.node_local_virtual_calculation_results[0]
    assert node_result.candidate_local_virtual_calculation_results == ()
    assert _fifo_tickets(fifo_set)[0].preserves_inlink_fifo is False
    assert result.fifo_inspection_set_result is fifo_set
    assert harness.binding_calls == []
    assert harness.copied_worlds == []
    assert harness.run_calls == []


def test_unexpected_status_raises_runtime_error_and_returns_no_partial_result():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("first", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec("merge", [{"trade_rank": first, "fifo": True}]),
            {
                "name": "other",
                "status": "not-a-known-status",
                "candidates": [],
            },
        ],
        downstream_boundary_result=_overall_boundary(
            _constrained_sink_boundary("merge"),
            _constrained_sink_boundary("other"),
        ),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            overall = _evaluate(world, fifo_set, _rank_states("merge", "other"))
            raise AssertionError(f"expected RuntimeError, got {overall!r}")
        except RuntimeError as error:
            assert "other" in str(error)
            assert "not-a-known-status" in str(error)
    assert len(harness.run_calls) == 1


# ---------------------------------------------------------------------------
# FIFO selection
# ---------------------------------------------------------------------------


def test_only_fifo_true_candidates_are_executed_in_upstream_relative_order():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("first", 1),))
    second = _trade_rank(buyers_sorted=(("second", 1),))
    third = _trade_rank(buyers_sorted=(("third", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [
                    {"trade_rank": first, "fifo": True},
                    {"trade_rank": second, "fifo": False},
                    {"trade_rank": third, "fifo": True},
                ],
            )
        ],
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    tickets = _fifo_tickets(fifo_set)
    assert [ticket.preserves_inlink_fifo for ticket in tickets] == [True, False, True]
    assert len(harness.binding_calls) == 2
    assert harness.binding_calls[0][1] is tickets[0]
    assert harness.binding_calls[1][1] is tickets[2]
    assert len(harness.local_state_calls) == 2
    assert len(harness.init_calls) == 2
    assert len(harness.run_calls) == 2
    assert harness.copied_worlds == []
    node_result = result.node_local_virtual_calculation_results[0]
    kept = node_result.candidate_local_virtual_calculation_results
    assert len(kept) == 2
    assert kept[0].concrete_buyer_candidate_set is first.concrete_buyer_candidate_set
    assert kept[1].concrete_buyer_candidate_set is third.concrete_buyer_candidate_set


def test_false_then_true_still_processes_the_true_candidate():
    world = _plain_world()
    false_rank = _trade_rank(buyers_sorted=(("false_buy", 1),))
    true_rank = _trade_rank(buyers_sorted=(("true_buy", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [
                    {"trade_rank": false_rank, "fifo": False},
                    {"trade_rank": true_rank, "fifo": True},
                ],
            )
        ],
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    tickets = _fifo_tickets(fifo_set)
    assert harness.binding_calls[0][1] is tickets[1]
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert len(kept) == 1
    assert kept[0].concrete_buyer_candidate_set is true_rank.concrete_buyer_candidate_set


# ---------------------------------------------------------------------------
# Rank state and boundary
# ---------------------------------------------------------------------------


def test_rank_state_is_required_only_for_nodes_with_fifo_true_candidates():
    world = _plain_world()
    true_rank = _trade_rank(buyers_sorted=(("true_buy", 1),))
    false_rank = _trade_rank(buyers_sorted=(("false_buy", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _not_generated_node_spec(
                "empty",
                OrderControlTvtCandidateVisitSetStatus.NOT_BUILT_NO_RIGHT_OF_ENTRY,
            ),
            _complete_node_spec("false_node", [{"trade_rank": false_rank, "fifo": False}]),
            _complete_node_spec("true_node", [{"trade_rank": true_rank, "fifo": True}]),
        ],
        downstream_boundary_result=_overall_boundary(
            _constrained_sink_boundary("empty"),
            _constrained_sink_boundary("false_node"),
            _constrained_sink_boundary("true_node"),
        ),
    )
    extra = OrderControlTvtNodeRankState("unused")
    rank_states = {
        "true_node": OrderControlTvtNodeRankState("true_node"),
        "unused": extra,
    }
    original_keys = list(rank_states.keys())
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, rank_states)
    assert list(rank_states.keys()) == original_keys
    assert harness.binding_calls[0][2] is rank_states["true_node"]
    assert [node.node_name for node in result.node_local_virtual_calculation_results] == [
        "empty",
        "false_node",
        "true_node",
    ]


def test_missing_or_wrong_rank_state_is_value_error_for_true_nodes():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, {})
            raise AssertionError("expected ValueError for missing rank state")
        except ValueError as error:
            assert "merge" in str(error)
    assert harness.binding_calls == []

    with _patched_stage_apis(_StageHarness()):
        try:
            _evaluate(world, fifo_set, {"merge": "not-a-rank-state"})
            raise AssertionError("expected ValueError for rank state type")
        except ValueError as error:
            assert "OrderControlTvtNodeRankState" in str(error)

    with _patched_stage_apis(_StageHarness()):
        try:
            _evaluate(world, fifo_set, {"merge": OrderControlTvtNodeRankState("other")})
            raise AssertionError("expected ValueError for node_name mismatch")
        except ValueError as error:
            assert "other" in str(error)


def test_boundary_none_is_runtime_error_only_when_a_true_candidate_exists():
    world = _plain_world()
    empty = _build_fifo_chain(
        node_specs=[_complete_node_spec("merge", [])],
        downstream_boundary_result=None,
    )
    result = _evaluate(world, empty, {})
    assert result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results == ()

    fifo_set = _one_true_merge_chain(downstream_boundary_result=None)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError for missing boundary")
        except RuntimeError as error:
            assert "downstream_boundary_result" in str(error)
    assert harness.run_calls == []


def test_boundary_count_and_name_mismatch_raise_runtime_error():
    world = _plain_world()
    fifo_set = _one_true_merge_chain(
        downstream_boundary_result=_overall_boundary(
            _constrained_sink_boundary("merge"),
            _constrained_sink_boundary("other"),
        )
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError for boundary count")
        except RuntimeError as error:
            assert "node_results" in str(error)

    fifo_set = _one_true_merge_chain(
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary("other"))
    )
    with _patched_stage_apis(_StageHarness()):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError for boundary name")
        except RuntimeError as error:
            assert "other" in str(error)


def test_rank_states_mapping_proxy_is_accepted_and_left_unchanged():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    inner = _rank_states("merge")
    proxy = MappingProxyType(inner)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, proxy)
    assert result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert list(proxy.keys()) == ["merge"]


# ---------------------------------------------------------------------------
# Mocked normal results
# ---------------------------------------------------------------------------


def test_resolved_and_unresolved_are_both_kept_and_false_is_omitted():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("first", 1),))
    second = _trade_rank(buyers_sorted=(("second", 1),))
    third = _trade_rank(buyers_sorted=(("third", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [
                    {"trade_rank": first, "fifo": True},
                    {"trade_rank": second, "fifo": False},
                    {"trade_rank": third, "fifo": True},
                ],
            )
        ],
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    harness = _StageHarness(resolved_flags=(True, False))
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert len(kept) == 2
    assert kept[0].resolved is True
    assert kept[0].stop_reason is OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
    assert kept[1].resolved is False
    assert kept[1].stop_reason is (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
    )
    assert isinstance(result.node_local_virtual_calculation_results, tuple)
    assert isinstance(kept, tuple)


def test_all_unresolved_and_empty_sellers_are_kept():
    world = _plain_world()
    empty_sellers = _trade_rank(buyers_sorted=(("buy", 1),), sellers_sorted=())
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [{"trade_rank": empty_sellers, "fifo": True}],
            )
        ],
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    harness = _StageHarness(resolved_flags=(False,))
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert len(kept) == 1
    assert kept[0].resolved is False
    assert empty_sellers.sellers_sorted == ()


def test_horizon_value_from_fork_is_passed_to_initialize():
    world = _plain_world()
    fifo_set = _one_true_merge_chain(configured_horizon_steps=1)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        _evaluate(world, fifo_set, _rank_states("merge"))
    assert harness.init_calls[0][3] == 1

    fifo_set = _one_true_merge_chain(configured_horizon_steps=6)
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        _evaluate(world, fifo_set, _rank_states("merge"))
    assert harness.init_calls[0][3] == 6


def test_candidate_local_objects_are_independent_under_mocked_execution():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("first", 1),))
    second = _trade_rank(buyers_sorted=(("second", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [
                    {"trade_rank": first, "fifo": True},
                    {"trade_rank": second, "fifo": True},
                ],
            )
        ],
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    harness = _StageHarness()
    with _patched_stage_apis(harness):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    assert harness.local_states[0] is not harness.local_states[1]
    assert harness.local_states[0].local_world is not harness.local_states[1].local_world
    assert harness.local_states[0].target_node is not harness.local_states[1].target_node
    assert harness.local_states[0].local_vehicles[0] is not harness.local_states[1].local_vehicles[0]
    assert harness.calc_states[0] is not harness.calc_states[1]
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert kept[0].concrete_buyer_candidate_set is first.concrete_buyer_candidate_set
    assert kept[1].concrete_buyer_candidate_set is second.concrete_buyer_candidate_set
    harness.local_states[0].local_world = "mutated"
    assert harness.local_states[1].local_world != "mutated"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


def test_binding_value_error_stops_the_set_and_skips_later_candidates():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("first", 1),))
    second = _trade_rank(buyers_sorted=(("second", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [
                    {"trade_rank": first, "fifo": True},
                    {"trade_rank": second, "fifo": True},
                ],
            )
        ],
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    harness = _StageHarness(binding_error=ValueError("binding failed"), raise_on_binding=1)
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "binding failed" in str(error)
    assert len(harness.binding_calls) == 1
    assert harness.local_state_calls == []
    assert harness.run_calls == []


def test_binding_runtime_error_stops_the_set():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    harness = _StageHarness(binding_error=RuntimeError("identity mismatch"))
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "identity mismatch" in str(error)
    assert harness.run_calls == []


def test_local_state_errors_are_not_converted_to_unresolved():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    harness = _StageHarness(local_state_error=ValueError("local state value"))
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "local state value" in str(error)
    assert harness.run_calls == []

    harness = _StageHarness(local_state_error=RuntimeError("local state runtime"))
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "local state runtime" in str(error)


def test_initialize_and_run_errors_stop_later_nodes_without_partial_result():
    world = _plain_world()
    first = _trade_rank(buyers_sorted=(("first", 1),))
    second = _trade_rank(buyers_sorted=(("second", 1),))
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec("merge", [{"trade_rank": first, "fifo": True}]),
            _complete_node_spec("other", [{"trade_rank": second, "fifo": True}]),
        ],
        downstream_boundary_result=_overall_boundary(
            _constrained_sink_boundary("merge"),
            _constrained_sink_boundary("other"),
        ),
    )
    harness = _StageHarness(init_error=ValueError("init value"), raise_on_init=1)
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge", "other"))
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "init value" in str(error)
    assert len(harness.init_calls) == 1
    assert harness.run_calls == []

    harness = _StageHarness(init_error=RuntimeError("init runtime"), raise_on_init=1)
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge", "other"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "init runtime" in str(error)

    harness = _StageHarness(run_error=ValueError("run value"), raise_on_run=1)
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge", "other"))
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert "run value" in str(error)
    assert len(harness.run_calls) == 1
    assert len(harness.binding_calls) == 1

    harness = _StageHarness(run_error=RuntimeError("run runtime"), raise_on_run=1)
    fingerprint = _world_fingerprint(world)
    with _patched_stage_apis(harness):
        try:
            _evaluate(world, fifo_set, _rank_states("merge", "other"))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as error:
            assert "run runtime" in str(error)
    assert _world_fingerprint(world) == fingerprint
    assert len(harness.local_states) == 1
    first_local = harness.local_states[0]
    first_local.local_world = "kept"
    assert first_local.local_world == "kept"


# ---------------------------------------------------------------------------
# Out of scope
# ---------------------------------------------------------------------------


def test_does_not_rerun_upstream_or_call_economic_or_selection_apis():
    world = _plain_world()
    fifo_set = _one_true_merge_chain()
    called = []

    def mark(name):
        def _inner(*args, **kwargs):
            called.append(name)
            raise AssertionError(name)

        return _inner

    harness = _StageHarness()
    with _patched_stage_apis(harness):
        with (
            patch(
                "uxsim.order_control_baseline_driver.run_snapshot_fixed_baseline_fork",
                mark("baseline"),
            ),
            patch(
                "uxsim.order_control_tvt_mp_fifo_inspection.build_tvt_mp_fifo_inspection_results",
                mark("fifo"),
            ),
            patch(
                "uxsim.order_control_tvt_mp_general_trade_rank.build_tvt_mp_general_trade_ranks",
                mark("trade"),
            ),
            patch(
                "uxsim.order_control_tvt_mp_concrete_buyer_candidate_set.build_tvt_mp_concrete_buyer_candidate_sets",
                mark("concrete"),
            ),
            patch.object(
                OrderControlTvtNodeRankState,
                "confirm_visits_and_formal_target_node_routes_atomically",
                mark("confirm"),
            ),
            patch(
                "uxsim.order_control_tvt_mp_candidate_local_virtual_calculation.run_tvt_mp_candidate_local_virtual_calculation_one_timestep",
                mark("one_timestep"),
            ),
        ):
            result = _evaluate(world, fifo_set, _rank_states("merge"))
    assert called == []
    assert result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results


def test_production_source_keeps_required_shape_and_forbids_out_of_scope_work():
    source_text = PRODUCTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    called_names = set()
    imported_modules = set()
    function_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            else:
                imported_modules.add((node.module or "").split(".")[0])
        if isinstance(node, ast.FunctionDef):
            function_names.append(node.name)
    forbidden_calls = {
        "exec_simulation",
        "run_snapshot_fixed_baseline_fork",
        "build_tvt_mp_fifo_inspection_results",
        "build_tvt_mp_general_trade_ranks",
        "build_tvt_mp_concrete_buyer_candidate_sets",
        "confirm_visits_and_formal_target_node_routes_atomically",
        "run_tvt_mp_candidate_local_virtual_calculation_one_timestep",
    }
    assert called_names.isdisjoint(forbidden_calls)
    assert "random" not in imported_modules
    assert "ThreadPoolExecutor" not in called_names
    assert "Pool" not in called_names
    assert "evaluate_tvt_mp_candidate_local_virtual_calculations" in function_names
    assert "for node_index, fifo_node_result in enumerate" in source_text
    assert "for candidate_fifo_inspection_result in" in source_text
    assert "build_tvt_mp_local_binding_rank_sequence" in source_text
    assert "build_tvt_mp_candidate_local_state" in source_text
    assert "initialize_tvt_mp_candidate_local_virtual_calculation_state" in source_text
    assert "run_tvt_mp_candidate_local_virtual_calculation(" in source_text
    lowered = source_text.lower()
    for token in (
        "payment",
        "compensation",
        "surplus",
        "utility",
        "expected time saving",
        "candidate selection",
    ):
        assert token not in lowered
    assert "dataclass(frozen=True)" in source_text
    assert "preserves_inlink_fifo is True" in source_text
    assert "real_world.copy" not in source_text
    assert "World.copy" not in source_text


# ---------------------------------------------------------------------------
# End-to-end with real one-candidate APIs
# ---------------------------------------------------------------------------


def test_end_to_end_one_resolved_candidate_on_horizon_one_and_multiple():
    for horizon in (1, 6):
        world, fifo_set, rank_states, collector, visit_keys, created = _prepare_end_to_end_buyers(
            [
                {
                    "name": "buyer_veh",
                    "origin": "orig_a",
                    "dest": "dest",
                    "inlink": "in_a",
                    "route": "out",
                }
            ],
            horizon=horizon,
        )
        fingerprint = _world_fingerprint(world)
        collector_before = collector.get_baseline_visit_snapshot(
            visit_keys[0][0],
            visit_keys[0][1],
        )
        rank_before = rank_states["merge"].k_confirmed()
        result = _evaluate(world, fifo_set, rank_states)
        kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
        assert len(kept) == 1
        assert kept[0].resolved is True
        assert kept[0].stop_reason is OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.RESOLVED
        assert kept[0].configured_horizon_steps == horizon
        assert result.fifo_inspection_set_result is fifo_set
        assert _world_fingerprint(world) == fingerprint
        assert collector.get_baseline_visit_snapshot(visit_keys[0][0], visit_keys[0][1]) == collector_before
        assert rank_states["merge"].k_confirmed() == rank_before
        assert created["buyer_veh"].link.name == "in_a"
        _assert_no_live_objects(result, path="resolved_set")


def test_end_to_end_one_unresolved_candidate_is_kept():
    world, fifo_set, rank_states, _collector, _visit_keys, _created = _prepare_end_to_end_buyers(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            }
        ],
        horizon=1,
        block_clearance=True,
    )
    result = _evaluate(world, fifo_set, rank_states)
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert len(kept) == 1
    assert kept[0].resolved is False
    assert kept[0].stop_reason is (
        OrderControlTvtMpCandidateLocalVirtualCalculationStopReason.HORIZON_EXHAUSTED_UNRESOLVED
    )


def test_end_to_end_mixed_true_false_and_independent_copies():
    copied = []
    original_copy = World.copy

    def counting_copy(world):
        copied_world = original_copy(world)
        copied.append(copied_world)
        return copied_world

    world, fifo_set, rank_states, collector, visit_keys, created = _prepare_end_to_end_buyers(
        [
            {
                "name": "buyer_a",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            },
            {
                "name": "buyer_b",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
            },
        ],
        horizon=1,
        fifo_flags=(True, False),
    )
    fingerprint = _world_fingerprint(world)
    rng_before = copy.deepcopy(world.rng.bit_generator.state)
    with patch.object(World, "copy", counting_copy):
        result = _evaluate(world, fifo_set, rank_states)
    assert len(copied) == 1
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert len(kept) == 1
    assert kept[0].concrete_buyer_candidate_set is (
        _fifo_tickets(fifo_set)[0].general_trade_rank_result.concrete_buyer_candidate_set
    )
    assert _fifo_tickets(fifo_set)[1].preserves_inlink_fifo is False
    assert _world_fingerprint(world) == fingerprint
    assert world.rng.bit_generator.state == rng_before
    assert collector is (
        fifo_set.general_trade_rank_set_result.concrete_buyer_candidate_set_result.inlink_candidate_physical_order_result.candidate_visit_set_result.right_of_entry_selection_result.leading_confirmation_result.arrived_confirmation_result.alignment_fork_result.fork_result.collector
    )
    assert created["buyer_a"].name == "buyer_a"


def test_end_to_end_two_true_candidates_use_separate_copies_and_keep_identity_order():
    copied = []
    original_copy = World.copy

    def counting_copy(world):
        copied_world = original_copy(world)
        copied.append(copied_world)
        return copied_world

    world, fifo_set, rank_states, collector, visit_keys, created = _prepare_end_to_end_buyers(
        [
            {
                "name": "buyer_a",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            },
            {
                "name": "buyer_b",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
            },
        ],
        horizon=1,
        fifo_flags=(True, True),
    )
    fingerprint = _world_fingerprint(world)
    with patch.object(World, "copy", counting_copy):
        result = _evaluate(world, fifo_set, rank_states)
    assert len(copied) == 2
    assert copied[0] is not copied[1]
    assert copied[0].get_node("merge") is not copied[1].get_node("merge")
    assert copied[0].VEHICLES["buyer_a"] is not copied[1].VEHICLES["buyer_a"]
    copied[0].T = 99
    assert copied[1].T == BASELINE_T
    assert world.T == BASELINE_T
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    tickets = _fifo_tickets(fifo_set)
    assert len(kept) == 2
    assert kept[0].concrete_buyer_candidate_set is tickets[0].general_trade_rank_result.concrete_buyer_candidate_set
    assert kept[1].concrete_buyer_candidate_set is tickets[1].general_trade_rank_result.concrete_buyer_candidate_set
    by_identity = {}
    for candidate_result in kept:
        by_identity[id(candidate_result.concrete_buyer_candidate_set)] = candidate_result.resolved
    reversed_results = []
    for ticket in reversed(tickets):
        rank_state = rank_states["merge"]
        sequence = set_mod.build_tvt_mp_local_binding_rank_sequence(
            fifo_set,
            ticket,
            rank_state,
        )
        local_state = set_mod.build_tvt_mp_candidate_local_state(world, sequence)
        calc = set_mod.initialize_tvt_mp_candidate_local_virtual_calculation_state(
            local_state,
            collector,
            _constrained_sink_boundary(),
            1,
        )
        reversed_results.append(
            set_mod.run_tvt_mp_candidate_local_virtual_calculation(calc)
        )
    reversed_by_identity = {}
    for candidate_result in reversed_results:
        reversed_by_identity[id(candidate_result.concrete_buyer_candidate_set)] = (
            candidate_result.resolved
        )
    assert by_identity == reversed_by_identity
    public_order = []
    for candidate_result in kept:
        public_order.append(id(candidate_result.concrete_buyer_candidate_set))
    assert public_order == [
        id(tickets[0].general_trade_rank_result.concrete_buyer_candidate_set),
        id(tickets[1].general_trade_rank_result.concrete_buyer_candidate_set),
    ]
    assert _world_fingerprint(world) == fingerprint
    assert created["buyer_a"] is world.VEHICLES["buyer_a"]
    assert visit_keys[0][0] == "buyer_a"


def test_end_to_end_outlink_order_mismatch_is_detected_by_existing_initialize():
    world, fifo_set, rank_states, _collector, _visit_keys, _created = _prepare_end_to_end_buyers(
        [
            {
                "name": "buyer_veh",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            }
        ],
        horizon=1,
        downstream_boundary_result=_overall_boundary(
            OrderControlBaselineDownstreamBoundaryNodeResult(
                node_name="merge",
                outlink_results=(
                    _outlink_boundary("side", "dest_b", 0, 0),
                    _outlink_boundary("out", "dest", 0, 0),
                ),
            )
        ),
    )
    fingerprint = _world_fingerprint(world)
    try:
        _evaluate(world, fifo_set, rank_states)
        raise AssertionError("expected RuntimeError from one-candidate initialize")
    except RuntimeError as error:
        assert "outlink order" in str(error)
    assert _world_fingerprint(world) == fingerprint


def test_end_to_end_second_candidate_error_does_not_rollback_first_copy_or_real_world():
    copied = []
    original_copy = World.copy

    def counting_copy(world):
        copied_world = original_copy(world)
        copied.append(copied_world)
        return copied_world

    world, fifo_set, rank_states, _collector, _visit_keys, _created = _prepare_end_to_end_buyers(
        [
            {
                "name": "buyer_a",
                "origin": "orig_a",
                "dest": "dest",
                "inlink": "in_a",
                "route": "out",
            },
            {
                "name": "buyer_b",
                "origin": "orig_b",
                "dest": "dest",
                "inlink": "in_b",
                "route": "out",
            },
        ],
        horizon=1,
        fifo_flags=(True, True),
    )
    fingerprint = _world_fingerprint(world)
    original_run = set_mod.run_tvt_mp_candidate_local_virtual_calculation
    run_count = {"n": 0}

    def run_then_fail(calculation_state):
        run_count["n"] += 1
        if run_count["n"] == 1:
            result = original_run(calculation_state)
            local_world = calculation_state.candidate_local_state.local_world
            local_world._set_entry_keep_marker = "first-candidate-not-rolled-back"
            return result
        raise RuntimeError("second candidate failed")

    with patch.object(World, "copy", counting_copy):
        with patch.object(
            set_mod,
            "run_tvt_mp_candidate_local_virtual_calculation",
            run_then_fail,
        ):
            try:
                _evaluate(world, fifo_set, rank_states)
                raise AssertionError("expected RuntimeError")
            except RuntimeError as error:
                assert "second candidate failed" in str(error)
    assert len(copied) == 2
    assert copied[0] is not copied[1]
    assert copied[0] is not world
    assert copied[0]._set_entry_keep_marker == "first-candidate-not-rolled-back"
    assert not hasattr(world, "_set_entry_keep_marker")
    assert not hasattr(copied[1], "_set_entry_keep_marker")
    assert _world_fingerprint(world) == fingerprint


def test_end_to_end_resolved_and_unresolved_mix_on_one_node():
    world = _new_world("tvt_mp_set_entry_mix")
    buyer_a = world.addVehicle("orig_a", "dest", 0, name="buyer_a")
    buyer_b = world.addVehicle("orig_b", "dest", 0, name="buyer_b")
    if not getattr(world, "finalized", 0):
        world.finalize_scenario()
    for link in world.LINKS:
        link.update()
    world.T = BASELINE_T
    collector = OrderControlBaselineCollector()
    key_a = _place_buyer(world, buyer_a, inlink_name="in_a", route_name="out")
    key_b = _place_buyer(world, buyer_b, inlink_name="in_b", route_name="out")
    _register_snapshot(collector, buyer_a, route_name="out")
    _register_snapshot(collector, buyer_b, route_name="out")
    fifo_set = _build_fifo_chain(
        node_specs=[
            _complete_node_spec(
                "merge",
                [
                    {"trade_rank": _trade_rank(buyers_sorted=(key_a,)), "fifo": True},
                    {"trade_rank": _trade_rank(buyers_sorted=(key_b,)), "fifo": True},
                ],
                remaining_keys=(key_a,),
            )
        ],
        collector=collector,
        configured_horizon_steps=1,
        downstream_boundary_result=_overall_boundary(_constrained_sink_boundary()),
    )
    _open_real_world_capacities(world)
    original_run = set_mod.run_tvt_mp_candidate_local_virtual_calculation
    outcomes = []

    def run_and_block_second(calculation_state):
        if len(outcomes) == 1:
            local_state = calculation_state.candidate_local_state
            other = local_state.local_world.get_link("in_a")
            node = local_state.target_node
            node.last_order_control_inlink = other
            node.last_order_control_entry_timestep = BASELINE_T
            node.order_control_clearance_timesteps = 100
        result = original_run(calculation_state)
        outcomes.append(result.resolved)
        return result

    with patch.object(
        set_mod,
        "run_tvt_mp_candidate_local_virtual_calculation",
        run_and_block_second,
    ):
        result = _evaluate(world, fifo_set, _rank_states("merge"))
    kept = result.node_local_virtual_calculation_results[0].candidate_local_virtual_calculation_results
    assert len(kept) == 2
    assert kept[0].resolved is True
    assert kept[1].resolved is False
    assert outcomes == [True, False]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_tests_registry_matches_defined_functions():
    defined_names = []
    defined_functions = []
    for name, value in list(globals().items()):
        if name.startswith("test_") and callable(value):
            defined_names.append(name)
            defined_functions.append(value)
    tests_names = []
    for function in TESTS:
        tests_names.append(function.__name__)
    assert tests_names == defined_names
    assert list(TESTS) == defined_functions
    assert len(TESTS) == len(defined_functions)
    assert len(set(TESTS)) == len(TESTS)


TESTS = tuple(
    value
    for name, value in list(globals().items())
    if name.startswith("test_") and callable(value)
)


if __name__ == "__main__":
    for current_case in TESTS:
        current_case()
        print("PASS", current_case.__name__)
    print(len(TESTS), "tests passed")
