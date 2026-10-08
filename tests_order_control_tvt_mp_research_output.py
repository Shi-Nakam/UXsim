"""Contract tests for TVT-MP research aggregation and CSV export."""

from __future__ import annotations

import copy
import csv
import dataclasses
import inspect

import pytest

from tests_order_control_tvt_mp_individual_ex_post_evaluation import (
    _NODE_NAME,
    _add_trade_to_world,
    _evaluation_end_world,
    _prepare_and_commit_evaluation_end,
    _prepare_and_commit_trade_ex_post,
    _visit_key,
)
from tests_order_control_tvt_mp_physical_transfer import _as_fork
from uxsim.order_control_tvt_mp_actual_passage import (
    OrderControlTvtMpActualPassageRole,
    OrderControlTvtMpTradeExPostEvaluationStatus,
    commit_tvt_mp_individual_ex_post_evaluation,
    prepare_tvt_mp_individual_ex_post_evaluation,
)
from uxsim.order_control_tvt_mp_candidate_local_virtual_calculation import (
    OrderControlTvtMpCandidatePassageObservationStatus,
)
from uxsim.order_control_tvt_mp_research_output import (
    OrderControlTvtMpResearchOutputBundle,
    OrderControlTvtMpResearchOutputNodeRow,
    OrderControlTvtMpResearchOutputScenarioRow,
    OrderControlTvtMpResearchOutputTransactionRow,
    OrderControlTvtMpResearchOutputVisitRow,
    OrderControlTvtMpResearchOutputVehicleRow,
    build_tvt_mp_research_output,
    write_tvt_mp_research_output_csv,
)
from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
)
import uxsim.uxsim as uxsim_module

_SCENARIO = "research_scenario_a"


def _field_names(cls):
    return [field.name for field in dataclasses.fields(cls)]


def _attach_rank_state_for_node(
    world,
    node_name: str,
    *,
    extra_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...] = (),
) -> OrderControlTvtNodeRankState:
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    visit_keys: list[OrderControlTvtVisitKey] = list(extra_confirmed_visit_keys)
    for (entry_node_name, visit_key), _entry in (
        registry.entries_by_node_name_and_visit_key.items()
    ):
        if entry_node_name == node_name and visit_key not in visit_keys:
            visit_keys.append(visit_key)
    rank_state = OrderControlTvtNodeRankState(node_name)
    for visit_key in visit_keys:
        rank_state.register_undetermined_visit(visit_key)
    rank_state.confirm_visits_in_order(tuple(visit_keys))
    world.order_control_tvt_rank_states_by_node_name[node_name] = rank_state
    return rank_state


def _commit_individual_ex_post(world) -> None:
    prepared = prepare_tvt_mp_individual_ex_post_evaluation(world)
    commit_tvt_mp_individual_ex_post_evaluation(prepared)


def _research_ready_world(
    role_specs,
    *,
    scenario_name: str = _SCENARIO,
    buyers_sorted=None,
    decision_timestep=10,
    extra_confirmed_visit_keys: tuple[OrderControlTvtVisitKey, ...] = (),
):
    world = _evaluation_end_world()
    trade, transaction_key = _add_trade_to_world(
        world,
        role_specs,
        buyers_sorted=buyers_sorted,
        decision_timestep=decision_timestep,
        finalize_unobserved=True,
    )
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    _attach_rank_state_for_node(
        world,
        _NODE_NAME,
        extra_confirmed_visit_keys=extra_confirmed_visit_keys,
    )
    output = build_tvt_mp_research_output(world, scenario_name)
    return world, trade, transaction_key, output


def _basic_buyer_seller_specs(*, buyer_observed=True, seller_observed=True):
    return [
        {
            "role": OrderControlTvtMpActualPassageRole.BUYER,
            "vehicle_name": "buyer_a",
            "observed": buyer_observed,
            "payment_paid_in_this_transaction": 5.0,
        },
        {
            "role": OrderControlTvtMpActualPassageRole.SELLER,
            "vehicle_name": "seller_a",
            "observed": seller_observed,
            "payment_received_in_this_transaction": 7.0,
        },
    ]


# --- precondition rejection ---


def test_build_rejects_baseline_fork():
    world, _trade, _key, _output = _research_ready_world(_basic_buyer_seller_specs())
    fork = _as_fork(world)
    fork._order_control_baseline_collector = object()
    with pytest.raises(RuntimeError, match="baseline fork"):
        build_tvt_mp_research_output(fork, _SCENARIO)


def test_build_rejects_evaluation_end_not_set():
    world = _evaluation_end_world()
    world.order_control_tvt_evaluation_end_timestep = None
    with pytest.raises(ValueError, match="evaluation_end"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_world_t_before_evaluation_end_plus_one():
    world = _evaluation_end_world()
    world.T = world.order_control_tvt_evaluation_end_timestep
    with pytest.raises(RuntimeError, match="World.T"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_unobserved_finalization_not_done():
    world = _evaluation_end_world()
    _add_trade_to_world(
        world,
        _basic_buyer_seller_specs(),
        finalize_unobserved=False,
    )
    with pytest.raises(RuntimeError, match="evaluation_end_unobserved_finalized"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_trade_ex_post_not_done():
    world = _evaluation_end_world()
    _add_trade_to_world(world, _basic_buyer_seller_specs(), finalize_unobserved=True)
    with pytest.raises(RuntimeError, match="trade_ex_post_evaluation_finalized"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_individual_ex_post_not_done():
    world = _evaluation_end_world()
    _add_trade_to_world(world, _basic_buyer_seller_specs(), finalize_unobserved=True)
    _prepare_and_commit_trade_ex_post(world)
    with pytest.raises(RuntimeError, match="individual_ex_post_evaluation_finalized"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_finalized_timestep_mismatch():
    world, _trade, _key, _output = _research_ready_world(_basic_buyer_seller_specs())
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    registry.trade_ex_post_evaluation_finalized_timestep = (
        registry.trade_ex_post_evaluation_finalized_timestep - 1
    )
    with pytest.raises(RuntimeError, match="trade_ex_post_evaluation_finalized_timestep"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_invalid_wait_registry_type():
    world, _trade, _key, _output = _research_ready_world(_basic_buyer_seller_specs())
    world.order_control_tvt_mp_actual_passage_wait_registry = object()
    with pytest.raises(RuntimeError, match="wait_registry"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_invalid_history_registry_type():
    world, _trade, _key, _output = _research_ready_world(_basic_buyer_seller_specs())
    world.order_control_tvt_mp_actual_node_passage_history_registry = object()
    with pytest.raises(RuntimeError, match="history_registry"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_missing_rank_state_for_trade_node():
    world = _evaluation_end_world()
    _add_trade_to_world(world, _basic_buyer_seller_specs(), finalize_unobserved=True)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    with pytest.raises(RuntimeError, match="no rank state"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_invalid_rank_state_type():
    world, _trade, _key, _output = _research_ready_world(_basic_buyer_seller_specs())
    world.order_control_tvt_rank_states_by_node_name[_NODE_NAME] = object()
    with pytest.raises(RuntimeError, match="rank state"):
        build_tvt_mp_research_output(world, _SCENARIO)


def test_build_rejects_empty_scenario_name():
    world, _trade, _key, _output = _research_ready_world(_basic_buyer_seller_specs())
    with pytest.raises(ValueError, match="scenario_name"):
        build_tvt_mp_research_output(world, "")


# --- transaction table ---


def test_transaction_row_field_order_matches_design():
    assert _field_names(OrderControlTvtMpResearchOutputTransactionRow) == [
        "scenario_name",
        "tvt_decision_timestep",
        "node_name",
        "buyers_sorted",
        "buyer_visit_count",
        "seller_visit_count",
        "nonparticipating_visit_count",
        "trade_scope_visit_count",
        "trade_ex_post_evaluation_status",
        "buyer_actual_declared_time_saving_value_total",
        "seller_actual_required_compensation_total",
        "buyer_official_payment_total",
        "seller_official_compensation_total",
        "buyer_reference_payment_total",
        "seller_reference_compensation_total",
        "buyer_evaluated_count",
        "buyer_satisfied_count",
        "buyer_unsatisfied_count",
        "buyer_unevaluated_count",
        "seller_evaluated_count",
        "seller_satisfied_count",
        "seller_unsatisfied_count",
        "seller_unevaluated_count",
        "buyer_realized_gain_total",
        "seller_realized_gain_total",
        "buyer_actual_observed_count",
        "buyer_actual_unobserved_count",
        "seller_actual_observed_count",
        "seller_actual_unobserved_count",
        "nonparticipating_actual_observed_count",
        "nonparticipating_actual_unobserved_count",
        "nonparticipating_candidate_predictable_count",
        "nonparticipating_candidate_unpredictable_count",
        "nonparticipating_predicted_external_effect_total",
        "nonparticipating_actual_external_effect_total",
        "nonparticipating_candidate_minus_actual_total",
        "rank_difference_evaluated_count",
        "rank_difference_unavailable_count",
        "moved_earlier_count",
        "rank_exact_count",
        "moved_later_count",
        "rank_difference_total",
    ]


def test_transaction_table_covers_three_trade_ex_post_statuses():
    world = _evaluation_end_world()
    specs_feasible = _basic_buyer_seller_specs()
    specs_infeasible = [
        {
            "role": OrderControlTvtMpActualPassageRole.BUYER,
            "vehicle_name": "buyer_b",
            "baseline_minus_actual_passage_seconds": 0,
            "payment_paid_in_this_transaction": 0.0,
        },
        {
            "role": OrderControlTvtMpActualPassageRole.SELLER,
            "vehicle_name": "seller_b",
            "baseline_minus_actual_passage_seconds": -120,
            "payment_received_in_this_transaction": 0.0,
        },
    ]
    specs_unavailable = [
        {
            "role": OrderControlTvtMpActualPassageRole.BUYER,
            "vehicle_name": "buyer_c",
            "observed": False,
        },
        {
            "role": OrderControlTvtMpActualPassageRole.SELLER,
            "vehicle_name": "seller_c",
            "observed": True,
        },
    ]
    _add_trade_to_world(
        world,
        specs_feasible,
        decision_timestep=10,
        buyers_sorted=(_visit_key("buyer_a"),),
        finalize_unobserved=False,
    )
    _add_trade_to_world(
        world,
        specs_infeasible,
        decision_timestep=11,
        buyers_sorted=(_visit_key("buyer_b"),),
        finalize_unobserved=False,
    )
    _add_trade_to_world(
        world,
        specs_unavailable,
        decision_timestep=12,
        buyers_sorted=(_visit_key("buyer_c"),),
        finalize_unobserved=False,
    )
    _prepare_and_commit_evaluation_end(world)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    _attach_rank_state_for_node(world, _NODE_NAME)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    statuses = [row.trade_ex_post_evaluation_status for row in output.transactions]
    assert statuses == [
        OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_FEASIBLE.value,
        OrderControlTvtMpTradeExPostEvaluationStatus.EX_POST_INFEASIBLE.value,
        OrderControlTvtMpTradeExPostEvaluationStatus.EVALUATION_UNAVAILABLE.value,
    ]
    unavailable_row = output.transactions[2]
    assert unavailable_row.buyer_reference_payment_total is None
    assert unavailable_row.buyer_realized_gain_total is None
    assert unavailable_row.buyer_unevaluated_count == 1
    assert unavailable_row.buyer_official_payment_total == pytest.approx(3.0)


def test_transaction_table_distinguishes_zero_and_none_for_np_effects():
    world = _evaluation_end_world()
    specs = [
        {
            "role": OrderControlTvtMpActualPassageRole.BUYER,
            "vehicle_name": "buyer_a",
        },
        {
            "role": OrderControlTvtMpActualPassageRole.SELLER,
            "vehicle_name": "seller_a",
        },
        {
            "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
            "vehicle_name": "np_a",
            "observed": False,
        },
    ]
    _add_trade_to_world(world, specs, finalize_unobserved=False)
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    np_key = _visit_key("np_a")
    np_entry = registry.entries_by_node_name_and_visit_key[(_NODE_NAME, np_key)]
    np_entry.predicted_observation_status = (
        OrderControlTvtMpCandidatePassageObservationStatus.UNOBSERVED_AT_HORIZON
    )
    np_entry.baseline_minus_candidate_passage_timesteps = None
    np_entry.baseline_minus_candidate_passage_seconds = None
    np_entry.baseline_minus_candidate_time_value = None
    _prepare_and_commit_evaluation_end(world)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    _attach_rank_state_for_node(world, _NODE_NAME)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    row = output.transactions[0]
    assert row.nonparticipating_visit_count == 1
    assert row.nonparticipating_candidate_unpredictable_count == 1
    assert row.nonparticipating_predicted_external_effect_total is None


def test_transaction_rank_difference_counts_signs():
    world = _evaluation_end_world()
    buyers_sorted = (_visit_key("buyer_a"),)
    specs = _basic_buyer_seller_specs()
    _add_trade_to_world(
        world,
        specs,
        buyers_sorted=buyers_sorted,
        finalize_unobserved=True,
    )
    registry = world.order_control_tvt_mp_actual_passage_wait_registry
    buyer_key = _visit_key("buyer_a")
    seller_key = _visit_key("seller_a")
    rank_state = OrderControlTvtNodeRankState(_NODE_NAME)
    rank_state.register_undetermined_visit(buyer_key)
    rank_state.register_undetermined_visit(seller_key)
    rank_state.confirm_visits_in_order((buyer_key, seller_key))
    world.order_control_tvt_rank_states_by_node_name[_NODE_NAME] = rank_state
    history = world.order_control_tvt_mp_actual_node_passage_history_registry
    from uxsim.order_control_tvt_mp_actual_passage import (
        OrderControlTvtMpActualNodePassageRecord,
    )

    history.records_by_node_name[_NODE_NAME] = (
        OrderControlTvtMpActualNodePassageRecord(
            visit_key=seller_key,
            actual_passage_timestep=12,
            actual_route_next_link_name="link_actual",
            actual_node_passage_rank=1,
        ),
        OrderControlTvtMpActualNodePassageRecord(
            visit_key=buyer_key,
            actual_passage_timestep=12,
            actual_route_next_link_name="link_actual",
            actual_node_passage_rank=2,
        ),
    )
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    row = output.transactions[0]
    assert row.moved_earlier_count == 1
    assert row.moved_later_count == 1
    assert row.rank_exact_count == 0
    assert row.rank_difference_total == 0


# --- visit-level outcome table ---


def test_visit_row_field_order_matches_design():
    names = _field_names(OrderControlTvtMpResearchOutputVisitRow)
    assert names[0:8] == [
        "scenario_name",
        "tvt_decision_timestep",
        "node_name",
        "buyers_sorted",
        "vehicle_name",
        "visit_id",
        "role",
        "actual_observation_status",
    ]
    assert "assigned_rank" in names
    assert "actual_rank_change" in names
    assert "welfare" not in names


def test_visit_table_includes_three_roles_and_vot_distinction():
    world, _trade, _key, output = _research_ready_world(
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
            {
                "role": OrderControlTvtMpActualPassageRole.NONPARTICIPATING,
                "vehicle_name": "np_a",
            },
        ]
    )
    roles = [row.role for row in output.visits]
    assert roles == ["buyer", "seller", "nonparticipating"]
    buyer_row = output.visits[0]
    np_row = output.visits[2]
    assert buyer_row.declared_vot_per_second == pytest.approx(1.0)
    assert np_row.declared_vot_per_second is None
    assert buyer_row.realized_gain is not None
    assert np_row.realized_gain is None
    assert buyer_row.true_vot_per_second == pytest.approx(0.5)


def test_visit_table_excludes_ledger_only_visit_without_wait_entry():
    extra = (_visit_key("ledger_only"),)
    world, _trade, _key, output = _research_ready_world(
        _basic_buyer_seller_specs(),
        extra_confirmed_visit_keys=extra,
    )
    visit_keys = {(row.vehicle_name, row.visit_id) for row in output.visits}
    assert ("ledger_only", 1) not in visit_keys
    node_row = output.nodes[0]
    assert node_row.assigned_visit_count == 3


def test_visit_table_evaluation_unavailable_has_none_monetary_outcomes():
    world = _evaluation_end_world()
    specs = [
        {
            "role": OrderControlTvtMpActualPassageRole.BUYER,
            "vehicle_name": "buyer_a",
            "observed": False,
        },
        {
            "role": OrderControlTvtMpActualPassageRole.SELLER,
            "vehicle_name": "seller_a",
            "observed": True,
        },
    ]
    _add_trade_to_world(world, specs, finalize_unobserved=True)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    _attach_rank_state_for_node(world, _NODE_NAME)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    buyer_row = output.visits[0]
    assert buyer_row.realized_gain is None
    assert buyer_row.satisfaction_status is None
    assert buyer_row.reference_payment is None
    assert buyer_row.official_payment == pytest.approx(3.0)


# --- vehicle summary ---


def test_vehicle_summary_aggregates_multiple_transactions_for_same_vehicle():
    world = _evaluation_end_world()
    _add_trade_to_world(
        world,
        [
            {"role": OrderControlTvtMpActualPassageRole.BUYER, "vehicle_name": "buyer_a"},
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_a"},
        ],
        decision_timestep=10,
        buyers_sorted=(_visit_key("buyer_a"),),
        finalize_unobserved=False,
    )
    _add_trade_to_world(
        world,
        [
            {
                "role": OrderControlTvtMpActualPassageRole.BUYER,
                "vehicle_name": "buyer_a",
                "visit_id": 2,
            },
            {"role": OrderControlTvtMpActualPassageRole.SELLER, "vehicle_name": "seller_b"},
        ],
        decision_timestep=11,
        buyers_sorted=(_visit_key("buyer_a", 2),),
        finalize_unobserved=False,
    )
    _prepare_and_commit_evaluation_end(world)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    _attach_rank_state_for_node(world, _NODE_NAME)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    buyer_vehicle = next(
        row for row in output.vehicles if row.vehicle_name == "buyer_a"
    )
    assert buyer_vehicle.transaction_count == 2
    assert buyer_vehicle.buyer_count == 2
    assert not hasattr(buyer_vehicle, "overall_satisfaction_status")


def test_vehicle_summary_includes_assigned_only_vehicle():
    extra = (_visit_key("assigned_only"),)
    world, _trade, _key, output = _research_ready_world(
        _basic_buyer_seller_specs(),
        extra_confirmed_visit_keys=extra,
    )
    names = [row.vehicle_name for row in output.vehicles]
    assert "assigned_only" in names
    assigned_row = next(
        row for row in output.vehicles if row.vehicle_name == "assigned_only"
    )
    assert assigned_row.assigned_visit_count == 1


# --- node summary ---


def test_node_summary_includes_transactionless_node_with_ledger_only():
    world = _evaluation_end_world()
    _add_trade_to_world(world, _basic_buyer_seller_specs(), finalize_unobserved=True)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    empty_node = OrderControlTvtNodeRankState("empty_node")
    only_key = _visit_key("ledger_vehicle")
    empty_node.register_undetermined_visit(only_key)
    empty_node.confirm_visits_in_order((only_key,))
    world.order_control_tvt_rank_states_by_node_name["empty_node"] = empty_node
    _attach_rank_state_for_node(world, _NODE_NAME)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    node_names = [row.node_name for row in output.nodes]
    assert node_names == ["empty_node", _NODE_NAME]
    empty_row = output.nodes[0]
    assert empty_row.transaction_count == 0
    assert empty_row.assigned_visit_count == 1


def test_node_summary_rank_population_uses_full_ledger_not_p3_only():
    extra = (_visit_key("partition_four"),)
    world, _trade, _key, output = _research_ready_world(
        _basic_buyer_seller_specs(),
        extra_confirmed_visit_keys=extra,
    )
    node_row = next(row for row in output.nodes if row.node_name == _NODE_NAME)
    assert node_row.assigned_visit_count == 3
    assert node_row.buyer_visit_count == 1


# --- scenario summary ---


def test_scenario_summary_single_row_without_welfare_or_traffic_metrics():
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    assert len(output.scenario) == 1
    row = output.scenario[0]
    assert row.evaluation_end_timestep == world.order_control_tvt_evaluation_end_timestep
    names = _field_names(OrderControlTvtMpResearchOutputScenarioRow)
    assert "welfare" not in " ".join(names)
    assert "average_speed" not in names
    assert "travel_time" not in names


# --- CSV export ---


def test_csv_writes_five_files_with_headers_and_field_order(tmp_path):
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    paths = write_tvt_mp_research_output_csv(output, tmp_path)
    assert set(paths.keys()) == {
        "tvt_mp_transactions.csv",
        "tvt_mp_visits.csv",
        "tvt_mp_vehicles.csv",
        "tvt_mp_nodes.csv",
        "tvt_mp_scenario.csv",
    }
    for filename, row_type in (
        ("tvt_mp_transactions.csv", OrderControlTvtMpResearchOutputTransactionRow),
        ("tvt_mp_visits.csv", OrderControlTvtMpResearchOutputVisitRow),
        ("tvt_mp_vehicles.csv", OrderControlTvtMpResearchOutputVehicleRow),
        ("tvt_mp_nodes.csv", OrderControlTvtMpResearchOutputNodeRow),
        ("tvt_mp_scenario.csv", OrderControlTvtMpResearchOutputScenarioRow),
    ):
        path = tmp_path / filename
        assert path.exists()
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            assert header == _field_names(row_type)


def test_csv_writes_none_as_empty_and_enum_as_value(tmp_path):
    world = _evaluation_end_world()
    specs = [
        {
            "role": OrderControlTvtMpActualPassageRole.BUYER,
            "vehicle_name": "buyer_a",
            "observed": False,
        },
        {
            "role": OrderControlTvtMpActualPassageRole.SELLER,
            "vehicle_name": "seller_a",
            "observed": True,
        },
    ]
    _add_trade_to_world(world, specs, finalize_unobserved=True)
    _prepare_and_commit_trade_ex_post(world)
    _commit_individual_ex_post(world)
    _attach_rank_state_for_node(world, _NODE_NAME)
    output = build_tvt_mp_research_output(world, _SCENARIO)
    write_tvt_mp_research_output_csv(output, tmp_path, overwrite=True)
    with (tmp_path / "tvt_mp_transactions.csv").open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    data_row = rows[1]
    header = rows[0]
    gain_index = header.index("buyer_realized_gain_total")
    status_index = header.index("trade_ex_post_evaluation_status")
    assert data_row[gain_index] == ""
    assert data_row[status_index] == "evaluation_unavailable"


def test_csv_overwrite_false_rejects_existing_file(tmp_path):
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    write_tvt_mp_research_output_csv(output, tmp_path)
    with pytest.raises(FileExistsError):
        write_tvt_mp_research_output_csv(output, tmp_path, overwrite=False)


def test_csv_overwrite_true_replaces_files(tmp_path):
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    write_tvt_mp_research_output_csv(output, tmp_path)
    first_mtime = (tmp_path / "tvt_mp_visits.csv").stat().st_mtime_ns
    write_tvt_mp_research_output_csv(output, tmp_path, overwrite=True)
    second_mtime = (tmp_path / "tvt_mp_visits.csv").stat().st_mtime_ns
    assert second_mtime >= first_mtime


def test_csv_does_not_modify_unrelated_file(tmp_path):
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    unrelated = tmp_path / "keep_me.txt"
    unrelated.write_text("unchanged", encoding="utf-8")
    write_tvt_mp_research_output_csv(output, tmp_path)
    assert unrelated.read_text(encoding="utf-8") == "unchanged"


def test_csv_creates_directory_when_parent_exists(tmp_path):
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    target = tmp_path / "outdir"
    write_tvt_mp_research_output_csv(output, target)
    assert (target / "tvt_mp_scenario.csv").exists()


# --- live invariance and determinism ---


def test_build_is_deterministic_for_same_world():
    world, _trade, _key, _first = _research_ready_world(_basic_buyer_seller_specs())
    second = build_tvt_mp_research_output(world, _SCENARIO)
    third = build_tvt_mp_research_output(world, _SCENARIO)
    assert second == third


def test_build_and_export_do_not_mutate_live_registries(tmp_path):
    world, _trade, transaction_key, output = _research_ready_world(
        _basic_buyer_seller_specs()
    )
    registry_before = copy.deepcopy(
        world.order_control_tvt_mp_actual_passage_wait_registry
    )
    history_before = copy.deepcopy(
        world.order_control_tvt_mp_actual_node_passage_history_registry
    )
    rank_before = copy.deepcopy(world.order_control_tvt_rank_states_by_node_name)
    rebuild = build_tvt_mp_research_output(world, _SCENARIO)
    write_tvt_mp_research_output_csv(rebuild, tmp_path)
    registry_after = world.order_control_tvt_mp_actual_passage_wait_registry
    assert (
        registry_after.trade_ex_post_evaluation_results_by_transaction_key
        == registry_before.trade_ex_post_evaluation_results_by_transaction_key
    )
    assert (
        world.order_control_tvt_mp_actual_node_passage_history_registry.records_by_node_name
        == history_before.records_by_node_name
    )
    assert (
        world.order_control_tvt_rank_states_by_node_name[_NODE_NAME].k_confirmed()
        == rank_before[_NODE_NAME].k_confirmed()
    )


def test_reexport_from_same_bundle_is_value_identical(tmp_path):
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    write_tvt_mp_research_output_csv(output, first_dir)
    write_tvt_mp_research_output_csv(output, second_dir)
    for name in (
        "tvt_mp_transactions.csv",
        "tvt_mp_visits.csv",
        "tvt_mp_vehicles.csv",
        "tvt_mp_nodes.csv",
        "tvt_mp_scenario.csv",
    ):
        assert (first_dir / name).read_text(encoding="utf-8") == (
            second_dir / name
        ).read_text(encoding="utf-8")


def test_bundle_is_frozen_without_live_registry_references():
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    with pytest.raises(dataclasses.FrozenInstanceError):
        output.scenario_name = "mutated"


def test_uxsim_does_not_auto_connect_research_output_api():
    source = inspect.getsource(uxsim_module)
    assert "build_tvt_mp_research_output" not in source
    assert "write_tvt_mp_research_output_csv" not in source


def test_research_output_bundle_row_types():
    world, _trade, _key, output = _research_ready_world(_basic_buyer_seller_specs())
    assert isinstance(output, OrderControlTvtMpResearchOutputBundle)
    assert isinstance(output.transactions[0], OrderControlTvtMpResearchOutputTransactionRow)
    assert isinstance(output.visits[0], OrderControlTvtMpResearchOutputVisitRow)
