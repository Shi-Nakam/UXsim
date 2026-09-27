"""
Tests for TVT-MP atomic apply.

Run from the repository root:
    python tests_order_control_tvt_mp_atomic_apply.py
"""

from __future__ import annotations

import dataclasses
import inspect
from dataclasses import replace

import tests_order_control_tvt_mp_final_consistency_validation as saved
import tests_order_control_tvt_mp_final_rank as fx
from uxsim.order_control_tvt_candidate_visit_set import OrderControlTvtCandidateVisit
from uxsim.order_control_tvt_mp_atomic_apply import (
    OrderControlTvtMpAtomicApplySetResult,
    OrderControlTvtMpTradeEstablishmentLogRecord,
    OrderControlTvtMpTradeEstablishmentRole,
    apply_tvt_mp_validated_result,
)
from uxsim.order_control_tvt_mp_concrete_buyer_candidate_set import (
    OrderControlTvtMpConcreteBuyerCandidateSet,
)
from uxsim.order_control_tvt_mp_final_consistency_validation import (
    OrderControlTvtMpFinalConsistencyValidationSetResult,
    validate_tvt_mp_final_consistency,
)
from uxsim.order_control_tvt_mp_final_rank import (
    OrderControlTvtMpFinalRankSetResult,
)
from uxsim.order_control_tvt_mp_general_trade_rank import (
    OrderControlTvtMpGeneralTradeRankResult,
)
from uxsim.order_control_tvt_mp_local_binding_rank_sequence import (
    OrderControlTvtMpLocalBindingRankSequence,
    OrderControlTvtMpLocalBindingTradeRole,
)
from uxsim.order_control_tvt_node_rank_state import OrderControlTvtNodeRankState
from uxsim.uxsim import Vehicle, World


BUYER = OrderControlTvtMpTradeEstablishmentRole.BUYER
SELLER = OrderControlTvtMpTradeEstablishmentRole.SELLER
BINDING_BUYER = OrderControlTvtMpLocalBindingTradeRole.BUYER
BINDING_SELLER = OrderControlTvtMpLocalBindingTradeRole.SELLER
BINDING_NONPARTICIPATING = OrderControlTvtMpLocalBindingTradeRole.NONPARTICIPATING
BINDING_OUTSIDE = OrderControlTvtMpLocalBindingTradeRole.OUTSIDE_TRADE_SCOPE
ESTABLISHMENT_FIELDS = (
    "tvt_decision_timestep",
    "node_name",
    "buyers_sorted",
    "visit_key",
    "vehicle_name",
    "trade_role",
    "baseline_local_rank",
    "post_trade_local_rank",
    "ledger_assigned_rank",
    "rank_change",
    "formal_route_next_link_name",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "payment_paid_in_this_transaction",
    "payment_received_in_this_transaction",
    "declared_vot_per_second",
    "true_vot_per_second",
)


def _visit(name, visit_id=1):
    return (name, visit_id)


def _candidate_visits(visit_keys):
    visits = []
    for visit_key in visit_keys:
        visits.append(
            OrderControlTvtCandidateVisit(
                visit_key=visit_key,
                vehicle_id=visit_key[1],
                inlink_name="in",
                baseline_arrival_timestep=11,
                arrival_tiebreaker=0,
                route_next_link_name="stored-route",
                baseline_passage_timestep=12,
            )
        )
    return tuple(visits)


def _trade_result(buyers_sorted, candidate_order, rank_by_visit):
    trade_rank = {}
    for visit_key in candidate_order:
        trade_rank[visit_key] = rank_by_visit[visit_key]
    trade_order_list = list(candidate_order)
    trade_order_list.sort(key=lambda visit_key: trade_rank[visit_key])
    return OrderControlTvtMpGeneralTradeRankResult(
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=buyers_sorted,
        ),
        buyers_sorted=buyers_sorted,
        sellers_sorted=(),
        nonparticipating_visits_sorted=(),
        last_buyer_rank=1,
        trade_scope=buyers_sorted,
        trade_order=tuple(trade_order_list),
        trade_rank_by_visit_key=trade_rank,
    )


def _with_trade_history(final_rank_set, histories):
    """Attach candidate_visits and, when ranks are present, one trade-rank row."""
    payment_set = final_rank_set.payment_and_compensation_set_result
    selection_set = payment_set.candidate_selection_set_result
    economic_set = selection_set.economic_evaluation_set_result
    local_set = economic_set.local_virtual_calculation_set_result
    fifo_set = local_set.fifo_inspection_set_result
    trade_set = fifo_set.general_trade_rank_set_result
    concrete_set = trade_set.concrete_buyer_candidate_set_result
    inlink_set = concrete_set.inlink_candidate_physical_order_result
    candidate_set = inlink_set.candidate_visit_set_result

    candidate_nodes = list(candidate_set.node_candidate_set_results)
    trade_nodes = list(trade_set.node_trade_rank_results)
    index = 0
    for history in histories:
        if history is not None:
            candidate_nodes[index] = replace(
                candidate_nodes[index],
                candidate_visits=_candidate_visits(history["order"]),
            )
            if history["ranks"] is not None:
                selected = final_rank_set.node_final_rank_results[
                    index
                ].selected_candidate_economic_result
                buyers_sorted = (
                    selected.candidate_local_virtual_calculation_result
                    .concrete_buyer_candidate_set.buyers_sorted
                )
                trade_nodes[index] = replace(
                    trade_nodes[index],
                    candidate_trade_rank_results=(
                        _trade_result(
                            buyers_sorted,
                            history["order"],
                            history["ranks"],
                        ),
                    ),
                )
        index = index + 1

    new_candidate_set = replace(
        candidate_set,
        node_candidate_set_results=tuple(candidate_nodes),
    )
    new_inlink_set = replace(
        inlink_set,
        candidate_visit_set_result=new_candidate_set,
    )
    new_concrete_set = replace(
        concrete_set,
        inlink_candidate_physical_order_result=new_inlink_set,
    )
    new_trade_set = replace(
        trade_set,
        concrete_buyer_candidate_set_result=new_concrete_set,
        node_trade_rank_results=tuple(trade_nodes),
    )
    new_fifo_set = replace(fifo_set, general_trade_rank_set_result=new_trade_set)
    new_local_set = replace(
        local_set,
        fifo_inspection_set_result=new_fifo_set,
    )
    new_economic_set = replace(
        economic_set,
        local_virtual_calculation_set_result=new_local_set,
    )
    new_selection_set = replace(
        selection_set,
        economic_evaluation_set_result=new_economic_set,
    )
    new_payment_set = replace(
        payment_set,
        candidate_selection_set_result=new_selection_set,
    )
    return replace(
        final_rank_set,
        payment_and_compensation_set_result=new_payment_set,
    )


def _default_history():
    buyer = _visit("buyer")
    seller = _visit("seller")
    watcher = _visit("watcher")
    later = _visit("later")
    return {
        "order": (seller, buyer, watcher, later),
        "ranks": {
            buyer: 1,
            seller: 2,
            watcher: 3,
            later: 4,
        },
    }


def _validated_selected(**kwargs):
    final_rank_set = saved._selected_final_rank_set(**kwargs)
    final_rank_set = _with_trade_history(final_rank_set, (_default_history(),))
    return validate_tvt_mp_final_consistency(final_rank_set)


def _validated_from_final_rank_set(final_rank_set, histories):
    prepared = _with_trade_history(final_rank_set, histories)
    return validate_tvt_mp_final_consistency(prepared)


def _world(node_routes, vehicle_names, *, timestep=10):
    """
    node_routes maps a target Node name to the formal outlink names that
    must be registered on that Node.
    """
    world = World(
        name="atomic-apply",
        deltan=1,
        reaction_time=1.0,
        tmax=120,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=1,
    )
    world.addNode("orig", 0, 0)
    world.addNode("dest", 10, 0)
    x_position = 1
    for node_name in node_routes:
        world.addNode(node_name, x_position, 0)
        x_position = x_position + 1
    for node_name, route_names in node_routes.items():
        for route_name in route_names:
            world.addLink(
                route_name,
                node_name,
                "dest",
                length=100,
                free_flow_speed=10,
            )
    for vehicle_name in vehicle_names:
        vehicle = world.addVehicle("orig", "dest", 0, name=vehicle_name)
        vehicle.vot_true = 1.5
        vehicle.vot_declared = 50.0
        vehicle.payment_paid = 10.0
        vehicle.payment_received = 20.0
        vehicle.order_exchange_log = ["old"]
        vehicle.participates_in_order_exchange = True
    world.T = timestep
    return world


def _rank_state(node_name, visit_keys):
    rank_state = OrderControlTvtNodeRankState(node_name)
    for visit_key in visit_keys:
        rank_state.register_undetermined_visit(visit_key)
    return rank_state


def _selected_context(**kwargs):
    validation = _validated_selected(**kwargs)
    node_name = validation.final_rank_set_result.node_final_rank_results[0].node_name
    routes = (
        "route-buyer",
        "route-seller",
        "route-watcher",
        "route-later",
    )
    world = _world(
        {node_name: routes},
        ("buyer", "seller", "watcher", "later"),
    )
    world.VEHICLES["buyer"].vot_true = 1.5
    world.VEHICLES["seller"].vot_true = 2.5
    world.VEHICLES["watcher"].vot_true = None
    world.VEHICLES["later"].vot_true = None
    rank_states = {
        node_name: _rank_state(
            node_name,
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        ),
    }
    return validation, world, rank_states


def _snapshot(world, rank_states):
    ledgers = {}
    for node_name, rank_state in rank_states.items():
        ledgers[node_name] = rank_state.export_state()
    vehicles = {}
    for vehicle_name, vehicle in world.VEHICLES.items():
        if isinstance(vehicle, Vehicle):
            if isinstance(vehicle.order_exchange_log, list):
                log_copy = list(vehicle.order_exchange_log)
            else:
                log_copy = vehicle.order_exchange_log
            vehicles[vehicle_name] = (
                vehicle.payment_paid,
                vehicle.payment_received,
                log_copy,
                vehicle.vot_true,
                vehicle.vot_declared,
                vehicle.participates_in_order_exchange,
            )
        else:
            vehicles[vehicle_name] = ("not-vehicle", type(vehicle).__name__)
    return (world.T, ledgers, vehicles)


def _assert_runtime_unchanged(validation, world, rank_states):
    before = _snapshot(world, rank_states)
    try:
        apply_tvt_mp_validated_result(validation, world, rank_states)
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True
    assert _snapshot(world, rank_states) == before


def _record_for(vehicle):
    assert len(vehicle.order_exchange_log) == 2
    record = vehicle.order_exchange_log[1]
    assert isinstance(record, OrderControlTvtMpTradeEstablishmentLogRecord)
    return record


def _replace_validation_payment_node(validation, node_index, payment_node):
    final_rank_set = validation.final_rank_set_result
    payment_set = final_rank_set.payment_and_compensation_set_result
    payment_nodes = list(payment_set.node_payment_and_compensation_results)
    payment_nodes[node_index] = payment_node
    new_payment_set = replace(
        payment_set,
        node_payment_and_compensation_results=tuple(payment_nodes),
    )
    new_final_rank_set = replace(
        final_rank_set,
        payment_and_compensation_set_result=new_payment_set,
    )
    return OrderControlTvtMpFinalConsistencyValidationSetResult(
        final_rank_set_result=new_final_rank_set,
    )


def _replace_selected(validation, node_index, selected):
    final_rank_set = validation.final_rank_set_result
    final_nodes = list(final_rank_set.node_final_rank_results)
    final_nodes[node_index] = replace(
        final_nodes[node_index],
        selected_candidate_economic_result=selected,
    )
    payment_set = final_rank_set.payment_and_compensation_set_result
    payment_nodes = list(payment_set.node_payment_and_compensation_results)
    payment_nodes[node_index] = replace(
        payment_nodes[node_index],
        selected_candidate_economic_result=selected,
    )
    new_payment_set = replace(
        payment_set,
        node_payment_and_compensation_results=tuple(payment_nodes),
    )
    new_final_rank_set = OrderControlTvtMpFinalRankSetResult(
        payment_and_compensation_set_result=new_payment_set,
        node_final_rank_results=tuple(final_nodes),
    )
    return OrderControlTvtMpFinalConsistencyValidationSetResult(
        final_rank_set_result=new_final_rank_set,
    )


def _sequence(node_name, buyers_sorted, partition_3, partition_4, remaining):
    visits = tuple(partition_3) + tuple(partition_4)
    return OrderControlTvtMpLocalBindingRankSequence(
        node_name=node_name,
        baseline_timestep_T=10,
        concrete_buyer_candidate_set=OrderControlTvtMpConcreteBuyerCandidateSet(
            buyers_sorted=tuple(buyers_sorted),
        ),
        confirmed_before_this_baseline_visits=(),
        preconfirmed_by_this_baseline_visits=(),
        trade_scope_of_this_candidate_visits=tuple(partition_3),
        outside_trade_scope_inside_k_fixed_visits=tuple(partition_4),
        visits_in_binding_order=visits,
        k_last_buyer=len(partition_3),
        k_decision_window=len(remaining),
        k_fixed=max(len(partition_3), len(remaining)),
    )


def _custom_selected_validation(
    node_name,
    buyer_names,
    seller_name,
    *,
    payment_amount=99.0,
):
    buyers = []
    for buyer_name in buyer_names:
        buyers.append(fx._buyer_record(buyer_name))
    sellers = ()
    partition_3 = []
    for buyer_name in buyer_names:
        partition_3.append(
            saved._binding(
                buyer_name,
                rank=len(partition_3) + 1,
                partition=fx.PARTITION_3,
                route="route-" + buyer_name,
                role=BINDING_BUYER,
            )
        )
    if seller_name is not None:
        sellers = (
            saved._seller(
                seller_name,
                required_compensation_R_s=1.0,
            ),
        )
        partition_3.append(
            saved._binding(
                seller_name,
                rank=len(partition_3) + 1,
                partition=fx.PARTITION_3,
                route="route-" + seller_name,
                role=BINDING_SELLER,
            )
        )
    remaining = []
    for binding_visit in partition_3:
        remaining.append(binding_visit.visit_key)
    buyers_sorted = []
    for buyer_name in buyer_names:
        buyers_sorted.append(_visit(buyer_name))
    sequence = _sequence(
        node_name,
        buyers_sorted,
        tuple(partition_3),
        (),
        tuple(remaining),
    )
    selected = saved._economic(node_name, sequence, tuple(buyers), sellers)
    buyer_records, seller_records = saved._payment_records(
        tuple(buyers),
        sellers,
        payment_amount=payment_amount,
    )
    spec = {
        "node_name": node_name,
        "build_status": fx.COMPLETE,
        "selected": selected,
        "remaining": tuple(remaining),
        "leading": (),
        "buyer_records": buyer_records,
        "seller_records": seller_records,
        "routes": {},
    }
    for visit_key in remaining:
        spec["routes"][visit_key] = "collector-" + visit_key[0]
    visits = saved._visits_from_partitions(tuple(partition_3), ())
    payment_set = fx._build([spec])
    final_rank_set = saved._final_set(
        payment_set,
        (
            {
                "status": saved.SELECTED_RANKS,
                "selected": selected,
                "visits": visits,
            },
        ),
    )
    rank_by_visit = {}
    position = 1
    for visit_key in remaining:
        rank_by_visit[visit_key] = position
        position = position + 1
    history = {"order": tuple(remaining), "ranks": rank_by_visit}
    return _validated_from_final_rank_set(final_rank_set, (history,))


def test_public_names_fields_and_no_trade_identity_type():
    signature = inspect.signature(apply_tvt_mp_validated_result)
    assert apply_tvt_mp_validated_result.__name__ == "apply_tvt_mp_validated_result"
    assert list(signature.parameters) == [
        "final_consistency_validation_set_result",
        "real_W",
        "rank_states_by_node_name",
    ]
    for parameter in signature.parameters.values():
        assert parameter.default is inspect.Parameter.empty
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert list(OrderControlTvtMpAtomicApplySetResult.__dataclass_fields__) == [
        "final_consistency_validation_set_result",
    ]
    assert list(OrderControlTvtMpTradeEstablishmentLogRecord.__dataclass_fields__) == (
        list(ESTABLISHMENT_FIELDS)
    )
    assert dataclasses.is_dataclass(OrderControlTvtMpAtomicApplySetResult)
    assert dataclasses.is_dataclass(OrderControlTvtMpTradeEstablishmentLogRecord)
    assert OrderControlTvtMpAtomicApplySetResult.__dataclass_params__.frozen is True
    assert (
        OrderControlTvtMpTradeEstablishmentLogRecord.__dataclass_params__.frozen
        is True
    )
    role_names = []
    for role in OrderControlTvtMpTradeEstablishmentRole:
        role_names.append(role.name)
    assert role_names == ["BUYER", "SELLER"]
    import uxsim.order_control_tvt_mp_atomic_apply as apply_module

    assert not hasattr(apply_module, "OrderControlTvtMpTradeIdentity")
    assert "binding_rank" not in ESTABLISHMENT_FIELDS
    assert "final_local_rank" not in ESTABLISHMENT_FIELDS


def test_selected_node_writes_ranks_money_and_establishment_rows():
    validation, world, rank_states = _selected_context()
    buyer_log_before = world.VEHICLES["buyer"].order_exchange_log
    result = apply_tvt_mp_validated_result(validation, world, rank_states)
    assert result.final_consistency_validation_set_result is validation
    assert isinstance(result, OrderControlTvtMpAtomicApplySetResult)

    rank_state = rank_states["merge"]
    assert rank_state.confirmed_visit_keys_in_order() == (
        _visit("buyer"),
        _visit("seller"),
        _visit("watcher"),
        _visit("later"),
    )
    assert rank_state.assigned_rank(_visit("buyer")) == 1
    assert rank_state.formal_route_next_link_name(_visit("buyer")) == "route-buyer"
    assert rank_state.formal_route_next_link_name(_visit("later")) == "route-later"
    assert rank_state.k_confirmed() == 4

    buyer = world.VEHICLES["buyer"]
    seller = world.VEHICLES["seller"]
    watcher = world.VEHICLES["watcher"]
    later = world.VEHICLES["later"]
    assert buyer.payment_paid == 109.0
    assert buyer.payment_received == 20.0
    assert seller.payment_paid == 10.0
    assert seller.payment_received == 21.0
    assert watcher.payment_paid == 10.0
    assert watcher.order_exchange_log == ["old"]
    assert later.order_exchange_log == ["old"]
    assert buyer.order_exchange_log is not buyer_log_before
    assert buyer_log_before == ["old"]
    assert buyer.vot_declared == 50.0
    assert buyer.vot_true == 1.5
    assert seller.vot_true == 2.5

    buyer_record = _record_for(buyer)
    seller_record = _record_for(seller)
    assert buyer_record.tvt_decision_timestep == 10
    assert buyer_record.tvt_decision_timestep == world.T
    assert buyer_record.node_name == "merge"
    assert buyer_record.buyers_sorted == (_visit("buyer"),)
    assert seller_record.buyers_sorted == (_visit("buyer"),)
    assert buyer_record.visit_key == _visit("buyer")
    assert buyer_record.vehicle_name == "buyer"
    assert buyer_record.trade_role is BUYER
    assert seller_record.trade_role is SELLER
    # candidate_visits order is seller, buyer, watcher, later.
    assert buyer_record.baseline_local_rank == 2
    assert seller_record.baseline_local_rank == 1
    assert buyer_record.post_trade_local_rank == 1
    assert seller_record.post_trade_local_rank == 2
    assert buyer_record.rank_change == 1
    assert seller_record.rank_change == -1
    assert buyer_record.ledger_assigned_rank == 1
    assert seller_record.ledger_assigned_rank == 2
    assert buyer_record.formal_route_next_link_name == "route-buyer"
    assert seller_record.formal_route_next_link_name == "route-seller"
    assert buyer_record.baseline_passage_timestep == 12
    assert buyer_record.candidate_passage_timestep == 11
    assert seller_record.baseline_passage_timestep == 11
    assert seller_record.candidate_passage_timestep == 12
    assert buyer_record.payment_paid_in_this_transaction == 99.0
    assert buyer_record.payment_received_in_this_transaction == 0
    assert seller_record.payment_paid_in_this_transaction == 0
    assert seller_record.payment_received_in_this_transaction == 1.0
    assert buyer_record.declared_vot_per_second == 1.0
    assert buyer_record.true_vot_per_second == 1.5
    assert seller_record.declared_vot_per_second == 1.0
    assert seller_record.true_vot_per_second == 2.5
    assert not hasattr(buyer_record, "binding_rank")
    assert not hasattr(buyer_record, "final_local_rank")
    buyer.vot_true = 999.0
    buyer.vot_declared = 888.0
    assert buyer_record.true_vot_per_second == 1.5
    assert buyer_record.declared_vot_per_second == 1.0
    try:
        buyer_record.node_name = "other"
        frozen_rejected = False
    except dataclasses.FrozenInstanceError:
        frozen_rejected = True
    assert frozen_rejected is True


def test_existing_confirmed_prefix_shifts_ledger_rank_only():
    validation, world, rank_states = _selected_context()
    rank_state = rank_states["merge"]
    prefix = _visit("prefix")
    rank_state.register_undetermined_visit(prefix)
    rank_state.confirm_visits_and_formal_target_node_routes_atomically(
        [(prefix, "route-buyer")],
        {"route-buyer"},
    )
    apply_tvt_mp_validated_result(validation, world, rank_states)
    buyer_record = _record_for(world.VEHICLES["buyer"])
    seller_record = _record_for(world.VEHICLES["seller"])
    assert buyer_record.baseline_local_rank == 2
    assert buyer_record.post_trade_local_rank == 1
    assert buyer_record.ledger_assigned_rank == 2
    assert seller_record.ledger_assigned_rank == 3
    assert rank_state.assigned_rank(_visit("buyer")) == 2
    assert rank_state.confirmed_visit_keys_in_order()[0] == prefix


def test_two_buyers_each_keep_the_same_buyer_tuple():
    validation = _custom_selected_validation(
        "east",
        ("buyer", "buyer_b"),
        None,
    )
    world = _world(
        {"east": ("route-buyer", "route-buyer_b")},
        ("buyer", "buyer_b"),
    )
    rank_states = {
        "east": _rank_state("east", (_visit("buyer"), _visit("buyer_b"))),
    }
    apply_tvt_mp_validated_result(validation, world, rank_states)
    expected_buyers = (_visit("buyer"), _visit("buyer_b"))
    first = _record_for(world.VEHICLES["buyer"])
    second = _record_for(world.VEHICLES["buyer_b"])
    assert first.buyers_sorted == expected_buyers
    assert second.buyers_sorted == expected_buyers
    assert first.trade_role is BUYER
    assert second.trade_role is BUYER
    assert first.payment_received_in_this_transaction == 0
    assert second.payment_paid_in_this_transaction == 99.0
    assert world.VEHICLES["buyer"].payment_received == 20.0
    assert world.VEHICLES["buyer_b"].payment_paid == 109.0


def test_zero_sellers_writes_only_the_buyer_row():
    partition_3 = (
        saved._binding(
            "buyer",
            rank=1,
            partition=fx.PARTITION_3,
            route="route-buyer",
            role=BINDING_BUYER,
        ),
    )
    final_rank_set = saved._selected_final_rank_set(
        sellers=(),
        partition_3=partition_3,
        partition_4=(),
        remaining=(_visit("buyer"),),
    )
    history = {
        "order": (_visit("buyer"),),
        "ranks": {_visit("buyer"): 1},
    }
    validation = _validated_from_final_rank_set(final_rank_set, (history,))
    world = _world({"merge": ("route-buyer",)}, ("buyer", "seller"))
    seller_before = _snapshot(world, {})
    rank_states = {"merge": _rank_state("merge", (_visit("buyer"),))}
    apply_tvt_mp_validated_result(validation, world, rank_states)
    assert len(world.VEHICLES["buyer"].order_exchange_log) == 2
    assert world.VEHICLES["seller"].order_exchange_log == ["old"]
    assert world.VEHICLES["seller"].payment_received == seller_before[2]["seller"][1]


def test_zero_payment_and_zero_compensation_still_write_rows():
    seller = saved._seller(
        "seller",
        declared_vot_per_second=0.0,
        required_compensation_R_s=0.0,
        expected_waiting_increase_timesteps=1,
        raw_passage_difference_timesteps=1,
    )
    final_rank_set = saved._selected_final_rank_set(
        sellers=(seller,),
        payment_amount=0.0,
    )
    validation = _validated_from_final_rank_set(
        final_rank_set,
        (_default_history(),),
    )
    world = _world(
        {
            "merge": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            )
        },
        ("buyer", "seller", "watcher", "later"),
    )
    world.VEHICLES["buyer"].vot_true = 0.0
    world.VEHICLES["seller"].vot_true = 4.0
    rank_states = {
        "merge": _rank_state(
            "merge",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        )
    }
    apply_tvt_mp_validated_result(validation, world, rank_states)
    buyer_record = _record_for(world.VEHICLES["buyer"])
    seller_record = _record_for(world.VEHICLES["seller"])
    assert buyer_record.payment_paid_in_this_transaction == 0.0
    assert seller_record.payment_received_in_this_transaction == 0.0
    assert seller_record.declared_vot_per_second == 0.0
    assert seller_record.true_vot_per_second == 4.0
    assert buyer_record.true_vot_per_second == 0.0
    assert buyer_record.declared_vot_per_second != buyer_record.true_vot_per_second
    assert world.VEHICLES["buyer"].payment_paid == 10.0
    assert world.VEHICLES["seller"].payment_received == 20.0
    assert world.VEHICLES["watcher"].order_exchange_log == ["old"]


def test_two_selected_nodes_apply_together():
    east = _custom_selected_validation("east", ("east_buyer",), "east_seller")
    west = _custom_selected_validation("west", ("west_buyer",), None)
    east_final = east.final_rank_set_result
    west_final = west.final_rank_set_result
    east_payment = east_final.payment_and_compensation_set_result
    west_spec_selected = east_final.node_final_rank_results[0].selected_candidate_economic_result
    # Rebuild one chain from the two already-validated node specs' saved objects
    # by using the custom builder's single-node results is not a shared chain.
    # A combined set is built from each node's payment spec fields.
    east_payment_node = east_payment.node_payment_and_compensation_results[0]
    west_payment_node = (
        west_final.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    east_spec = {
        "node_name": "east",
        "build_status": fx.COMPLETE,
        "selected": east_final.node_final_rank_results[0].selected_candidate_economic_result,
        "remaining": (
            _visit("east_buyer"),
            _visit("east_seller"),
        ),
        "leading": (),
        "buyer_records": east_payment_node.buyer_payment_records,
        "seller_records": east_payment_node.seller_compensation_records,
        "routes": {},
    }
    west_spec = {
        "node_name": "west",
        "build_status": fx.COMPLETE,
        "selected": west_final.node_final_rank_results[0].selected_candidate_economic_result,
        "remaining": (_visit("west_buyer"),),
        "leading": (),
        "buyer_records": west_payment_node.buyer_payment_records,
        "seller_records": (),
        "routes": {},
    }
    for visit_key in east_spec["remaining"]:
        east_spec["routes"][visit_key] = "collector-" + visit_key[0]
    for visit_key in west_spec["remaining"]:
        west_spec["routes"][visit_key] = "collector-" + visit_key[0]
    payment_set = fx._build([east_spec, west_spec])
    final_rank_set = saved._final_set(
        payment_set,
        (
            {
                "status": saved.SELECTED_RANKS,
                "selected": east_spec["selected"],
                "visits": east_final.node_final_rank_results[0].final_rank_visits,
            },
            {
                "status": saved.SELECTED_RANKS,
                "selected": west_spec["selected"],
                "visits": west_final.node_final_rank_results[0].final_rank_visits,
            },
        ),
    )
    histories = (
        {
            "order": (_visit("east_buyer"), _visit("east_seller")),
            "ranks": {_visit("east_buyer"): 1, _visit("east_seller"): 2},
        },
        {
            "order": (_visit("west_buyer"),),
            "ranks": {_visit("west_buyer"): 1},
        },
    )
    validation = _validated_from_final_rank_set(final_rank_set, histories)
    assert len(validation.final_rank_set_result.node_final_rank_results) == 2
    world = _world(
        {
            "east": ("route-east_buyer", "route-east_seller"),
            "west": ("route-west_buyer",),
        },
        ("east_buyer", "east_seller", "west_buyer"),
    )
    rank_states = {
        "east": _rank_state(
            "east",
            (_visit("east_buyer"), _visit("east_seller")),
        ),
        "west": _rank_state("west", (_visit("west_buyer"),)),
    }
    result = apply_tvt_mp_validated_result(validation, world, rank_states)
    assert result.final_consistency_validation_set_result is validation
    assert _record_for(world.VEHICLES["east_buyer"]).node_name == "east"
    assert _record_for(world.VEHICLES["west_buyer"]).node_name == "west"
    assert world.VEHICLES["east_seller"].payment_received == 21.0
    assert rank_states["east"].k_confirmed() == 2
    assert rank_states["west"].k_confirmed() == 1
    assert west_spec_selected is not None


def test_fallback_writes_ranks_and_routes_without_money_or_history():
    final_rank_set = saved._fallback_final_rank_set()
    validation = validate_tvt_mp_final_consistency(final_rank_set)
    world = _world({"merge": ("base-alpha", "base-beta")}, ("alpha", "beta"))
    world.VEHICLES["alpha"].vot_true = None
    rank_states = {
        "merge": _rank_state("merge", (_visit("alpha"), _visit("beta"))),
    }
    apply_tvt_mp_validated_result(validation, world, rank_states)
    rank_state = rank_states["merge"]
    assert rank_state.confirmed_visit_keys_in_order() == (
        _visit("alpha"),
        _visit("beta"),
    )
    assert rank_state.formal_route_next_link_name(_visit("alpha")) == "base-alpha"
    assert world.VEHICLES["alpha"].payment_paid == 10.0
    assert world.VEHICLES["alpha"].payment_received == 20.0
    assert world.VEHICLES["alpha"].order_exchange_log == ["old"]
    assert world.VEHICLES["beta"].order_exchange_log == ["old"]
    assert world.VEHICLES["alpha"].vot_true is None


def test_no_visits_nodes_do_not_change_ledgers():
    empty_validation = validate_tvt_mp_final_consistency(
        saved._no_visits_final_rank_set(preconfirmed=False)
    )
    preconfirmed_validation = validate_tvt_mp_final_consistency(
        saved._no_visits_final_rank_set(preconfirmed=True)
    )
    for validation in (empty_validation, preconfirmed_validation):
        world = _world({"merge": ()}, ())
        rank_states = {"merge": OrderControlTvtNodeRankState("merge")}
        before = _snapshot(world, rank_states)
        result = apply_tvt_mp_validated_result(validation, world, rank_states)
        assert result.final_consistency_validation_set_result is validation
        assert _snapshot(world, rank_states) == before
        assert len(validation.final_rank_set_result.node_final_rank_results) == 1


def test_empty_node_is_kept_and_selected_node_still_applies():
    selected = saved._selected_final_rank_set(node_name="east")
    selected_node = selected.node_final_rank_results[0]
    selected_payment = (
        selected.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    east_spec = {
        "node_name": "east",
        "build_status": fx.COMPLETE,
        "selected": selected_node.selected_candidate_economic_result,
        "remaining": (
            _visit("buyer"),
            _visit("seller"),
            _visit("watcher"),
            _visit("later"),
        ),
        "leading": (),
        "buyer_records": selected_payment.buyer_payment_records,
        "seller_records": selected_payment.seller_compensation_records,
        "routes": {},
    }
    for visit_key in east_spec["remaining"]:
        east_spec["routes"][visit_key] = "collector-" + visit_key[0]
    empty_spec = fx._empty_window_spec("west")
    payment_set = fx._build([empty_spec, east_spec])
    final_rank_set = saved._final_set(
        payment_set,
        (
            {"status": saved.NO_VISITS, "selected": None, "visits": ()},
            {
                "status": saved.SELECTED_RANKS,
                "selected": east_spec["selected"],
                "visits": selected_node.final_rank_visits,
            },
        ),
    )
    validation = _validated_from_final_rank_set(
        final_rank_set,
        (None, _default_history()),
    )
    assert len(validation.final_rank_set_result.node_final_rank_results) == 2
    world = _world(
        {
            "west": (),
            "east": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            ),
        },
        ("buyer", "seller", "watcher", "later"),
    )
    rank_states = {
        "west": OrderControlTvtNodeRankState("west"),
        "east": _rank_state(
            "east",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        ),
    }
    apply_tvt_mp_validated_result(validation, world, rank_states)
    assert rank_states["west"].k_confirmed() == 0
    assert rank_states["east"].k_confirmed() == 4
    assert _record_for(world.VEHICLES["buyer"]).node_name == "east"


def test_missing_empty_node_rank_state_changes_nothing():
    selected = saved._selected_final_rank_set(node_name="east")
    selected_node = selected.node_final_rank_results[0]
    selected_payment = (
        selected.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    east_spec = {
        "node_name": "east",
        "build_status": fx.COMPLETE,
        "selected": selected_node.selected_candidate_economic_result,
        "remaining": (
            _visit("buyer"),
            _visit("seller"),
            _visit("watcher"),
            _visit("later"),
        ),
        "leading": (),
        "buyer_records": selected_payment.buyer_payment_records,
        "seller_records": selected_payment.seller_compensation_records,
        "routes": {},
    }
    for visit_key in east_spec["remaining"]:
        east_spec["routes"][visit_key] = "collector-" + visit_key[0]
    payment_set = fx._build([east_spec, fx._empty_window_spec("west")])
    final_rank_set = saved._final_set(
        payment_set,
        (
            {
                "status": saved.SELECTED_RANKS,
                "selected": east_spec["selected"],
                "visits": selected_node.final_rank_visits,
            },
            {"status": saved.NO_VISITS, "selected": None, "visits": ()},
        ),
    )
    validation = _validated_from_final_rank_set(
        final_rank_set,
        (_default_history(), None),
    )
    world = _world(
        {
            "east": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            ),
            "west": (),
        },
        ("buyer", "seller", "watcher", "later"),
    )
    rank_states = {
        "east": _rank_state(
            "east",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        ),
    }
    _assert_runtime_unchanged(validation, world, rank_states)


def _two_node_selected_then_fallback():
    selected = saved._selected_final_rank_set(node_name="east")
    selected_node = selected.node_final_rank_results[0]
    selected_payment = (
        selected.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    east_spec = {
        "node_name": "east",
        "build_status": fx.COMPLETE,
        "selected": selected_node.selected_candidate_economic_result,
        "remaining": (
            _visit("buyer"),
            _visit("seller"),
            _visit("watcher"),
            _visit("later"),
        ),
        "leading": (),
        "buyer_records": selected_payment.buyer_payment_records,
        "seller_records": selected_payment.seller_compensation_records,
        "routes": {},
    }
    for visit_key in east_spec["remaining"]:
        east_spec["routes"][visit_key] = "collector-" + visit_key[0]
    west_spec = fx._fallback_spec(
        "west",
        remaining=(_visit("alpha"),),
        build_status=fx.COMPLETE,
    )
    payment_set = fx._build([east_spec, west_spec])
    final_rank_set = saved._final_set(
        payment_set,
        (
            {
                "status": saved.SELECTED_RANKS,
                "selected": east_spec["selected"],
                "visits": selected_node.final_rank_visits,
            },
            {
                "status": saved.FALLBACK_RANKS,
                "selected": None,
                "visits": (
                    saved._rank_record(
                        _visit("alpha"),
                        1,
                        "base-alpha",
                        saved.BASELINE_SOURCE,
                    ),
                ),
            },
        ),
    )
    validation = _validated_from_final_rank_set(
        final_rank_set,
        (_default_history(), None),
    )
    return validation


def test_second_node_unregistered_visit_leaves_first_node_unchanged():
    validation = _two_node_selected_then_fallback()
    world = _world(
        {
            "east": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            ),
            "west": ("base-alpha",),
        },
        ("buyer", "seller", "watcher", "later", "alpha"),
    )
    rank_states = {
        "east": _rank_state(
            "east",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        ),
        "west": OrderControlTvtNodeRankState("west"),
    }
    _assert_runtime_unchanged(validation, world, rank_states)


def test_second_node_missing_outlink_leaves_every_ledger_unchanged():
    validation = _two_node_selected_then_fallback()
    world = _world(
        {
            "east": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            ),
            "west": (),
        },
        ("buyer", "seller", "watcher", "later", "alpha"),
    )
    rank_states = {
        "east": _rank_state(
            "east",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        ),
        "west": _rank_state("west", (_visit("alpha"),)),
    }
    _assert_runtime_unchanged(validation, world, rank_states)


def test_failure_does_not_call_rank_commit_and_success_does():
    validation, world, rank_states = _selected_context()
    original = (
        OrderControlTvtNodeRankState._commit_prepared_formal_route_confirmation
    )
    calls = {"count": 0}

    def wrapped(self, prepared):
        calls["count"] = calls["count"] + 1
        return original(self, prepared)

    OrderControlTvtNodeRankState._commit_prepared_formal_route_confirmation = wrapped
    try:
        world.T = 11
        before = _snapshot(world, rank_states)
        try:
            apply_tvt_mp_validated_result(validation, world, rank_states)
            raised = False
        except RuntimeError:
            raised = True
        assert raised is True
        assert calls["count"] == 0
        assert _snapshot(world, rank_states) == before
        world.T = 10
        apply_tvt_mp_validated_result(validation, world, rank_states)
        assert calls["count"] == 1
    finally:
        OrderControlTvtNodeRankState._commit_prepared_formal_route_confirmation = (
            original
        )


def test_missing_vehicle_changes_nothing():
    validation, world, rank_states = _selected_context()
    del world.VEHICLES["buyer"]
    _assert_runtime_unchanged(validation, world, rank_states)


def test_non_vehicle_object_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"] = "not-a-vehicle"
    _assert_runtime_unchanged(validation, world, rank_states)


def test_payment_paid_bool_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].payment_paid = True
    _assert_runtime_unchanged(validation, world, rank_states)


def test_payment_received_string_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["seller"].payment_received = "20"
    _assert_runtime_unchanged(validation, world, rank_states)


def test_non_finite_current_money_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].payment_paid = float("nan")
    _assert_runtime_unchanged(validation, world, rank_states)


def test_negative_current_money_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["seller"].payment_received = -1.0
    _assert_runtime_unchanged(validation, world, rank_states)


def test_updated_money_overflow_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].payment_paid = 1e308
    payment_node = (
        validation.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    buyer_record = payment_node.buyer_payment_records[0]
    huge_record = replace(buyer_record, payment_P_b=1e308)
    seller_records = payment_node.seller_compensation_records
    replaced_node = replace(
        payment_node,
        buyer_payment_records=(huge_record,),
        seller_compensation_records=seller_records,
    )
    broken = _replace_validation_payment_node(validation, 0, replaced_node)
    _assert_runtime_unchanged(broken, world, rank_states)


def test_order_exchange_log_must_be_a_list():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].order_exchange_log = ("old",)
    _assert_runtime_unchanged(validation, world, rank_states)


def test_vot_true_none_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].vot_true = None
    _assert_runtime_unchanged(validation, world, rank_states)


def test_vot_true_bool_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["seller"].vot_true = True
    _assert_runtime_unchanged(validation, world, rank_states)


def test_vot_true_negative_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].vot_true = -0.1
    _assert_runtime_unchanged(validation, world, rank_states)


def test_vot_true_nan_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["buyer"].vot_true = float("nan")
    _assert_runtime_unchanged(validation, world, rank_states)


def test_vot_true_infinity_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.VEHICLES["seller"].vot_true = float("inf")
    _assert_runtime_unchanged(validation, world, rank_states)


def test_duplicate_vehicle_money_record_changes_nothing():
    validation, world, rank_states = _selected_context()
    payment_node = (
        validation.final_rank_set_result.payment_and_compensation_set_result
        .node_payment_and_compensation_results[0]
    )
    buyer_record = payment_node.buyer_payment_records[0]
    replaced_node = replace(
        payment_node,
        buyer_payment_records=(buyer_record, buyer_record),
    )
    broken = _replace_validation_payment_node(validation, 0, replaced_node)
    _assert_runtime_unchanged(broken, world, rank_states)


def test_timestep_mismatch_changes_nothing():
    validation, world, rank_states = _selected_context()
    world.T = 11
    _assert_runtime_unchanged(validation, world, rank_states)


def test_missing_baseline_rank_changes_nothing():
    final_rank_set = saved._selected_final_rank_set()
    validation = validate_tvt_mp_final_consistency(final_rank_set)
    world = _world(
        {
            "merge": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            )
        },
        ("buyer", "seller", "watcher", "later"),
    )
    rank_states = {
        "merge": _rank_state(
            "merge",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        )
    }
    _assert_runtime_unchanged(validation, world, rank_states)


def test_missing_post_trade_rank_changes_nothing():
    final_rank_set = saved._selected_final_rank_set()
    history = {"order": _default_history()["order"], "ranks": None}
    validation = _validated_from_final_rank_set(final_rank_set, (history,))
    world = _world(
        {
            "merge": (
                "route-buyer",
                "route-seller",
                "route-watcher",
                "route-later",
            )
        },
        ("buyer", "seller", "watcher", "later"),
    )
    rank_states = {
        "merge": _rank_state(
            "merge",
            (
                _visit("buyer"),
                _visit("seller"),
                _visit("watcher"),
                _visit("later"),
            ),
        )
    }
    _assert_runtime_unchanged(validation, world, rank_states)


def test_passage_timestep_mismatch_changes_nothing():
    validation, world, rank_states = _selected_context()
    selected = validation.final_rank_set_result.node_final_rank_results[
        0
    ].selected_candidate_economic_result
    buyer_records = list(selected.buyer_economic_records)
    buyer_records[0] = replace(buyer_records[0], baseline_passage_timestep=None)
    broken_selected = replace(
        selected,
        buyer_economic_records=tuple(buyer_records),
    )
    broken = _replace_selected(validation, 0, broken_selected)
    _assert_runtime_unchanged(broken, world, rank_states)


def test_negative_buyer_declared_vot_changes_nothing():
    validation, world, rank_states = _selected_context()
    selected = validation.final_rank_set_result.node_final_rank_results[
        0
    ].selected_candidate_economic_result
    buyer_records = list(selected.buyer_economic_records)
    buyer_records[0] = replace(buyer_records[0], declared_vot_per_second=-0.1)
    broken_selected = replace(
        selected,
        buyer_economic_records=tuple(buyer_records),
    )
    broken = _replace_selected(validation, 0, broken_selected)
    _assert_runtime_unchanged(broken, world, rank_states)


def test_negative_seller_declared_vot_changes_nothing():
    validation, world, rank_states = _selected_context()
    selected = validation.final_rank_set_result.node_final_rank_results[
        0
    ].selected_candidate_economic_result
    seller_records = list(selected.seller_economic_records)
    seller_records[0] = replace(seller_records[0], declared_vot_per_second=-1.0)
    broken_selected = replace(
        selected,
        seller_economic_records=tuple(seller_records),
    )
    broken = _replace_selected(validation, 0, broken_selected)
    _assert_runtime_unchanged(broken, world, rank_states)


def test_trade_role_mismatch_changes_nothing():
    validation, world, rank_states = _selected_context()
    selected = validation.final_rank_set_result.node_final_rank_results[
        0
    ].selected_candidate_economic_result
    local_result = selected.candidate_local_virtual_calculation_result
    sequence = local_result.binding_rank_sequence
    binding_visits = []
    for binding_visit in sequence.trade_scope_of_this_candidate_visits:
        if binding_visit.visit_key == _visit("buyer"):
            binding_visits.append(
                replace(binding_visit, trade_role=BINDING_SELLER)
            )
        else:
            binding_visits.append(binding_visit)
    broken_sequence = replace(
        sequence,
        trade_scope_of_this_candidate_visits=tuple(binding_visits),
    )
    broken_local = replace(
        local_result,
        binding_rank_sequence=broken_sequence,
    )
    broken_selected = replace(
        selected,
        candidate_local_virtual_calculation_result=broken_local,
    )
    broken = _replace_selected(validation, 0, broken_selected)
    _assert_runtime_unchanged(broken, world, rank_states)


def test_public_input_type_errors_are_value_errors():
    validation, world, rank_states = _selected_context()
    cases = (
        (None, world, rank_states),
        (validation, None, rank_states),
        (validation, world, ["not-a-mapping"]),
        (validation, world, {"merge": "not-a-rank-state"}),
    )
    for args in cases:
        try:
            apply_tvt_mp_validated_result(*args)
            raised = False
        except ValueError:
            raised = True
        assert raised is True
    assert rank_states["merge"].k_confirmed() == 0


def test_rank_state_node_name_mismatch_changes_nothing():
    validation, world, rank_states = _selected_context()
    rank_states["merge"] = _rank_state(
        "other",
        (
            _visit("buyer"),
            _visit("seller"),
            _visit("watcher"),
            _visit("later"),
        ),
    )
    _assert_runtime_unchanged(validation, world, rank_states)


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
