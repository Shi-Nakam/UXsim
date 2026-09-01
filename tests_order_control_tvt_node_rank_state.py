# Unit tests for OrderControlTvtNodeRankState (design memo §25.25.30).
#
# Run from the repository root:
#   python tests_order_control_tvt_node_rank_state.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from unittest.mock import patch

import numpy as np

from uxsim.order_control_tvt_node_rank_state import (
    OrderControlTvtConfirmResult,
    OrderControlTvtNodeRankState,
    OrderControlTvtVisitKey,
    _verify_candidate_confirmed_state,
)


def _new_state(node_name: str = "merge") -> OrderControlTvtNodeRankState:
    return OrderControlTvtNodeRankState(node_name)


def _snapshot_state(state: OrderControlTvtNodeRankState) -> dict[str, object]:
    return {
        "k_confirmed": state.k_confirmed(),
        "confirmed": state.confirmed_visit_keys_in_order(),
        "undetermined": state.undetermined_visit_keys(),
        "export": state.export_state(),
    }


def _register(
    state: OrderControlTvtNodeRankState,
    *visit_keys: OrderControlTvtVisitKey,
) -> None:
    for visit_key in visit_keys:
        state.register_undetermined_visit(visit_key)


def test_public_types_importable_from_dedicated_module():
    assert OrderControlTvtVisitKey is not None
    assert OrderControlTvtConfirmResult is not None
    assert OrderControlTvtNodeRankState is not None


def test_init_valid_node_name():
    state = _new_state("junction_a")
    assert state.node_name == "junction_a"
    assert state.k_confirmed() == 0
    assert state.confirmed_visit_keys_in_order() == ()
    assert state.undetermined_visit_keys() == frozenset()


def test_init_rejects_empty_node_name():
    try:
        _new_state("")
        raise AssertionError("Expected ValueError for empty node_name")
    except ValueError as exc:
        assert "node_name" in str(exc)


def test_init_rejects_non_string_node_name():
    try:
        OrderControlTvtNodeRankState(None)  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for None node_name")
    except ValueError as exc:
        assert "node_name" in str(exc)


def test_visit_key_accepts_valid_tuple():
    state = _new_state()
    state.register_undetermined_visit(("veh_a", 1))
    assert state.is_undetermined(("veh_a", 1))


def test_visit_key_rejects_empty_vehicle_name():
    state = _new_state()
    try:
        state.register_undetermined_visit(("", 1))
        raise AssertionError("Expected ValueError for empty vehicle_name")
    except ValueError as exc:
        assert "vehicle_name" in str(exc)


def test_visit_key_rejects_non_string_vehicle_name():
    state = _new_state()
    try:
        state.register_undetermined_visit((123, 1))  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for non-str vehicle_name")
    except ValueError as exc:
        assert "vehicle_name" in str(exc)


def test_visit_key_rejects_bool_visit_id():
    state = _new_state()
    try:
        state.register_undetermined_visit(("veh_a", True))  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for bool visit_id")
    except ValueError as exc:
        assert "visit_id" in str(exc)


def test_visit_key_rejects_non_int_visit_id():
    state = _new_state()
    try:
        state.register_undetermined_visit(("veh_a", 1.5))  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for float visit_id")
    except ValueError as exc:
        assert "visit_id" in str(exc)


def test_visit_key_rejects_zero_and_negative_visit_id():
    state = _new_state()
    for bad_visit_id in (0, -1):
        try:
            state.register_undetermined_visit(("veh_a", bad_visit_id))
            raise AssertionError(
                f"Expected ValueError for visit_id {bad_visit_id!r}"
            )
        except ValueError as exc:
            assert "visit_id" in str(exc)


def test_visit_key_rejects_non_tuple_container():
    state = _new_state()
    try:
        state.register_undetermined_visit(["veh_a", 1])  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for list VisitKey")
    except ValueError as exc:
        assert "tuple" in str(exc)


def test_visit_key_rejects_wrong_length_tuple():
    state = _new_state()
    try:
        state.register_undetermined_visit(("veh_a",))
        raise AssertionError("Expected ValueError for length-1 tuple")
    except ValueError as exc:
        assert "length-2" in str(exc)


def test_visit_key_rejects_numpy_integer_visit_id():
    state = _new_state()
    try:
        state.register_undetermined_visit(("veh_a", np.int64(1)))  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for numpy visit_id")
    except ValueError as exc:
        assert "visit_id" in str(exc)


def test_same_vehicle_name_different_visit_id_are_distinct():
    state = _new_state()
    state.register_undetermined_visit(("veh_a", 1))
    state.register_undetermined_visit(("veh_a", 2))
    assert state.undetermined_visit_keys() == frozenset({("veh_a", 1), ("veh_a", 2)})


def test_single_register_adds_to_undetermined_only():
    state = _new_state()
    state.register_undetermined_visit(("veh_a", 1))
    assert state.is_undetermined(("veh_a", 1))
    assert not state.is_confirmed(("veh_a", 1))
    assert state.assigned_rank(("veh_a", 1)) is None


def test_single_register_rejects_duplicate_undetermined():
    state = _new_state()
    state.register_undetermined_visit(("veh_a", 1))
    before = _snapshot_state(state)
    try:
        state.register_undetermined_visit(("veh_a", 1))
        raise AssertionError("Expected ValueError for duplicate undetermined")
    except ValueError as exc:
        assert "already registered as undetermined" in str(exc)
    assert _snapshot_state(state) == before


def test_single_register_rejects_confirmed_visit():
    state = _new_state()
    _register(state, ("veh_a", 1))
    state.confirm_visits_in_order([("veh_a", 1)])
    try:
        state.register_undetermined_visit(("veh_a", 1))
        raise AssertionError("Expected ValueError for confirmed re-register")
    except ValueError as exc:
        assert "already confirmed" in str(exc)
        assert "assigned_rank" in str(exc)


def test_batch_register_accepts_list_and_tuple():
    state_list = _new_state("list_node")
    state_list.register_undetermined_visits([("veh_a", 1), ("veh_b", 1)])
    assert state_list.undetermined_visit_keys() == frozenset(
        {("veh_a", 1), ("veh_b", 1)}
    )

    state_tuple = _new_state("tuple_node")
    state_tuple.register_undetermined_visits((("veh_c", 1), ("veh_d", 1)))
    assert state_tuple.undetermined_visit_keys() == frozenset(
        {("veh_c", 1), ("veh_d", 1)}
    )


def test_batch_register_rejects_non_list_or_tuple_container():
    state = _new_state()
    for bad_container in ({"veh_a", 1}, {("veh_a", 1)}, "veh_a", 123):
        try:
            state.register_undetermined_visits(bad_container)  # type: ignore[arg-type]
            raise AssertionError(
                f"Expected ValueError for container {bad_container!r}"
            )
        except ValueError as exc:
            assert "list or tuple" in str(exc)


def test_batch_register_empty_list_and_tuple_are_no_op():
    state = _new_state()
    before = _snapshot_state(state)
    state.register_undetermined_visits([])
    state.register_undetermined_visits(())
    assert _snapshot_state(state) == before


def test_batch_register_rejects_input_duplicate():
    state = _new_state()
    before = _snapshot_state(state)
    try:
        state.register_undetermined_visits([("veh_a", 1), ("veh_a", 1)])
        raise AssertionError("Expected ValueError for input duplicate")
    except ValueError as exc:
        assert "Duplicate VisitKey" in str(exc)
    assert _snapshot_state(state) == before


def test_batch_register_rejects_existing_undetermined_duplicate():
    state = _new_state()
    state.register_undetermined_visit(("veh_a", 1))
    before = _snapshot_state(state)
    try:
        state.register_undetermined_visits([("veh_b", 1), ("veh_a", 1)])
        raise AssertionError("Expected ValueError for existing undetermined")
    except ValueError as exc:
        assert "already registered as undetermined" in str(exc)
    assert _snapshot_state(state) == before


def test_batch_register_rejects_confirmed_contamination():
    state = _new_state()
    _register(state, ("veh_a", 1))
    state.confirm_visits_in_order([("veh_a", 1)])
    before = _snapshot_state(state)
    try:
        state.register_undetermined_visits([("veh_b", 1), ("veh_a", 1)])
        raise AssertionError("Expected ValueError for confirmed contamination")
    except ValueError as exc:
        assert "already confirmed" in str(exc)
    assert _snapshot_state(state) == before


def test_batch_register_rejects_invalid_visit_key_without_partial_register():
    state = _new_state()
    before = _snapshot_state(state)
    try:
        state.register_undetermined_visits([("veh_a", 1), ("", 2)])
        raise AssertionError("Expected ValueError for invalid visit key")
    except ValueError:
        pass
    assert _snapshot_state(state) == before


def test_node_states_are_independent():
    state_a = _new_state("node_a")
    state_b = _new_state("node_b")
    state_a.register_undetermined_visit(("veh_a", 1))
    assert state_b.undetermined_visit_keys() == frozenset()


def test_confirm_empty_list_and_tuple_are_no_op():
    state = _new_state()
    _register(state, ("veh_a", 1))
    state.confirm_visits_in_order([("veh_a", 1)])
    before = _snapshot_state(state)

    result_list = state.confirm_visits_in_order([])
    assert result_list.k_confirmed_before == 1
    assert result_list.k_confirmed_after == 1
    assert result_list.newly_confirmed_count == 0
    assert _snapshot_state(state) == before

    result_tuple = state.confirm_visits_in_order(())
    assert result_tuple.k_confirmed_before == 1
    assert result_tuple.k_confirmed_after == 1
    assert result_tuple.newly_confirmed_count == 0
    assert _snapshot_state(state) == before


def test_confirm_single_visit_starts_at_rank_one():
    state = _new_state()
    _register(state, ("veh_a", 1))
    result = state.confirm_visits_in_order([("veh_a", 1)])
    assert result.k_confirmed_before == 0
    assert result.k_confirmed_after == 1
    assert result.newly_confirmed_count == 1
    assert state.assigned_rank(("veh_a", 1)) == 1
    assert state.undetermined_visit_keys() == frozenset()


def test_confirm_multiple_visits_preserves_input_order():
    state = _new_state()
    _register(state, ("vehicle_g", 1), ("vehicle_f", 1), ("vehicle_h", 1))
    # Input order is the confirmation order; do not sort by vehicle name.
    confirm_column = [
        ("vehicle_g", 1),
        ("vehicle_f", 1),
        ("vehicle_h", 1),
    ]
    result = state.confirm_visits_in_order(confirm_column)
    assert result.k_confirmed_before == 0
    assert result.k_confirmed_after == 3
    assert result.newly_confirmed_count == 3
    assert state.confirmed_visit_keys_in_order() == tuple(confirm_column)
    assert state.assigned_rank(("vehicle_g", 1)) == 1
    assert state.assigned_rank(("vehicle_f", 1)) == 2
    assert state.assigned_rank(("vehicle_h", 1)) == 3


def test_confirm_appends_after_existing_confirmed_block():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    state.confirm_visits_in_order([("veh_a", 1), ("veh_b", 1)])
    result = state.confirm_visits_in_order([("veh_c", 1)])
    assert result.k_confirmed_before == 2
    assert result.k_confirmed_after == 3
    assert state.assigned_rank(("veh_c", 1)) == 3


def test_confirm_result_count_fields_match():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1))
    result = state.confirm_visits_in_order([("veh_a", 1), ("veh_b", 1)])
    assert result.newly_confirmed_count == result.k_confirmed_after - result.k_confirmed_before


def test_confirm_multiple_rounds_keep_contiguous_ranks():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    state.confirm_visits_in_order([("veh_a", 1)])
    state.confirm_visits_in_order([("veh_b", 1)])
    result = state.confirm_visits_in_order([("veh_c", 1)])
    assert result.k_confirmed_after == 3
    assert state.k_confirmed() == 3
    assert state.assigned_rank(("veh_c", 1)) == 3


def test_confirm_rejects_reconfirm_with_distinct_message():
    state = _new_state()
    _register(state, ("veh_a", 1))
    state.confirm_visits_in_order([("veh_a", 1)])
    before = _snapshot_state(state)
    try:
        state.confirm_visits_in_order([("veh_a", 1)])
        raise AssertionError("Expected ValueError for re-confirm")
    except ValueError as exc:
        message = str(exc)
        assert "('veh_a', 1)" in message
        assert "already confirmed" in message
        assert "assigned_rank" in message
        assert "1" in message
    assert _snapshot_state(state) == before


def test_confirm_rejects_unregistered_with_distinct_message():
    state = _new_state()
    before = _snapshot_state(state)
    try:
        state.confirm_visits_in_order([("veh_x", 1)])
        raise AssertionError("Expected ValueError for unregistered confirm")
    except ValueError as exc:
        message = str(exc)
        assert "('veh_x', 1)" in message
        assert "not pre-registered" in message
        assert "already confirmed" not in message
    assert _snapshot_state(state) == before


def test_reconfirm_and_unregistered_messages_differ():
    state = _new_state()
    _register(state, ("veh_a", 1))
    state.confirm_visits_in_order([("veh_a", 1)])

    try:
        state.confirm_visits_in_order([("veh_a", 1)])
        raise AssertionError("Expected re-confirm ValueError")
    except ValueError as reconfirm_exc:
        reconfirm_message = str(reconfirm_exc)

    try:
        state.confirm_visits_in_order([("veh_z", 1)])
        raise AssertionError("Expected unregistered ValueError")
    except ValueError as unregistered_exc:
        unregistered_message = str(unregistered_exc)

    assert reconfirm_message != unregistered_message


def test_confirm_rejects_input_duplicate():
    state = _new_state()
    _register(state, ("veh_a", 1))
    before = _snapshot_state(state)
    try:
        state.confirm_visits_in_order([("veh_a", 1), ("veh_a", 1)])
        raise AssertionError("Expected ValueError for confirm duplicate")
    except ValueError as exc:
        assert "Duplicate VisitKey" in str(exc)
    assert _snapshot_state(state) == before


def test_confirm_rejects_non_list_or_tuple_container():
    state = _new_state()
    _register(state, ("veh_a", 1))
    try:
        state.confirm_visits_in_order({("veh_a", 1)})  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for set container")
    except ValueError as exc:
        assert "list or tuple" in str(exc)


def test_confirm_leaves_state_unchanged_when_middle_key_unregistered():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_c", 1))
    before = _snapshot_state(state)
    try:
        state.confirm_visits_in_order([("veh_a", 1), ("veh_b", 1), ("veh_c", 1)])
        raise AssertionError("Expected ValueError for middle unregistered key")
    except ValueError:
        pass
    assert _snapshot_state(state) == before


def test_confirm_leaves_state_unchanged_when_middle_key_already_confirmed():
    state = _new_state()
    pending_first = ("veh_b", 1)
    already_confirmed_middle = ("veh_a", 1)
    pending_last = ("veh_c", 1)
    _register(state, already_confirmed_middle, pending_first, pending_last)
    state.confirm_visits_in_order([already_confirmed_middle])
    before = _snapshot_state(state)
    try:
        state.confirm_visits_in_order(
            [
                pending_first,
                already_confirmed_middle,
                pending_last,
            ]
        )
        raise AssertionError("Expected ValueError for middle re-confirm")
    except ValueError as exc:
        assert "already confirmed" in str(exc)
        assert repr(already_confirmed_middle) in str(exc)
    assert _snapshot_state(state) == before


def test_confirm_input_list_mutation_after_call_does_not_change_state():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1))
    confirm_column = [("veh_a", 1), ("veh_b", 1)]
    state.confirm_visits_in_order(confirm_column)
    confirm_column.append(("veh_c", 1))
    assert state.k_confirmed() == 2
    assert state.confirmed_visit_keys_in_order() == (("veh_a", 1), ("veh_b", 1))


def test_staged_k_confirmed_before_after_external_preconfirm_columns():
    state = _new_state()
    # Existing confirmed block from an earlier timestep.
    _register(state, ("veh_a", 1), ("veh_b", 1))
    state.confirm_visits_in_order([("veh_a", 1), ("veh_b", 1)])

    # External institutional processing built these columns; the rank-state
    # component only stores the VisitKey order it receives.
    _register(state, ("veh_c", 1), ("veh_d", 1))
    arrived_preconfirm_column = [("veh_c", 1), ("veh_d", 1)]
    state.confirm_visits_in_order(arrived_preconfirm_column)

    _register(state, ("veh_e", 1))
    non_participant_preconfirm_column = [("veh_e", 1)]
    state.confirm_visits_in_order(non_participant_preconfirm_column)

    k_confirmed_before = state.k_confirmed()
    assert k_confirmed_before == 5

    _register(state, ("veh_g", 1), ("veh_f", 1), ("veh_h", 1))
    final_column_built_by_external_processing = [
        ("veh_g", 1),
        ("veh_f", 1),
        ("veh_h", 1),
    ]
    final_result = state.confirm_visits_in_order(final_column_built_by_external_processing)
    assert final_result.k_confirmed_before == 5
    assert final_result.k_confirmed_after == 8
    assert final_result.newly_confirmed_count == 3
    assert state.assigned_rank(("veh_g", 1)) == 6
    assert state.assigned_rank(("veh_f", 1)) == 7
    assert state.assigned_rank(("veh_h", 1)) == 8


def test_outside_decision_window_visit_confirmed_in_input_order():
    state = _new_state()
    inside_window_visit = ("veh_q", 1)
    outside_window_tvt_candidate_visit = ("veh_r", 1)
    another_inside_window_visit = ("veh_s", 1)
    # VisitKey carries no inside/outside flag; names mark external roles only.
    _register(
        state,
        inside_window_visit,
        outside_window_tvt_candidate_visit,
        another_inside_window_visit,
    )
    final_column_from_external_processing = [
        inside_window_visit,
        outside_window_tvt_candidate_visit,
        another_inside_window_visit,
    ]
    result = state.confirm_visits_in_order(final_column_from_external_processing)
    assert result.k_confirmed_before == 0
    assert result.k_confirmed_after == 3
    assert state.confirmed_visit_keys_in_order() == tuple(final_column_from_external_processing)
    assert state.assigned_rank(outside_window_tvt_candidate_visit) == 2
    assert outside_window_tvt_candidate_visit not in state.undetermined_visit_keys()


def test_confirm_result_has_three_fields_only_and_is_frozen():
    state = _new_state()
    _register(state, ("veh_a", 1))
    result = state.confirm_visits_in_order([("veh_a", 1)])
    field_names = {field.name for field in dataclasses.fields(result)}
    assert field_names == {
        "k_confirmed_before",
        "k_confirmed_after",
        "newly_confirmed_count",
    }
    assert not hasattr(result, "confirmed_visit_keys")
    try:
        result.k_confirmed_after = 99  # type: ignore[misc]
        raise AssertionError("Expected frozen ConfirmResult to reject mutation")
    except dataclasses.FrozenInstanceError:
        pass


def test_read_confirmed_visit_keys_returns_tuple_not_internal_list():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1))
    state.confirm_visits_in_order([("veh_a", 1), ("veh_b", 1)])
    confirmed = state.confirmed_visit_keys_in_order()
    assert isinstance(confirmed, tuple)
    confirmed_list = list(confirmed)
    confirmed_list.append(("veh_c", 1))
    assert state.confirmed_visit_keys_in_order() == (("veh_a", 1), ("veh_b", 1))


def test_read_undetermined_visit_keys_returns_frozenset_not_internal_set():
    state = _new_state()
    state.register_undetermined_visit(("veh_a", 1))
    undetermined = state.undetermined_visit_keys()
    assert isinstance(undetermined, frozenset)
    assert state.undetermined_visit_keys() == frozenset({("veh_a", 1)})


def test_read_membership_and_assigned_rank_for_confirmed_undetermined_unregistered():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1))
    state.confirm_visits_in_order([("veh_a", 1)])

    assert state.is_confirmed(("veh_a", 1)) is True
    assert state.is_undetermined(("veh_a", 1)) is False
    assert state.assigned_rank(("veh_a", 1)) == 1

    assert state.is_confirmed(("veh_b", 1)) is False
    assert state.is_undetermined(("veh_b", 1)) is True
    assert state.assigned_rank(("veh_b", 1)) is None

    assert state.is_confirmed(("veh_z", 1)) is False
    assert state.is_undetermined(("veh_z", 1)) is False
    assert state.assigned_rank(("veh_z", 1)) is None


def test_read_apis_reject_invalid_visit_key():
    state = _new_state()
    for method_name in ("is_confirmed", "is_undetermined", "assigned_rank"):
        method = getattr(state, method_name)
        try:
            method(("", 1))
            raise AssertionError(
                f"Expected ValueError from {method_name} for invalid VisitKey"
            )
        except ValueError as exc:
            assert "visit_key" in str(exc) or "vehicle_name" in str(exc)


def test_export_state_structure_and_sort_orders():
    state = _new_state("junction_a")
    _register(state, ("veh_b", 2), ("veh_a", 1), ("veh_c", 1))
    state.confirm_visits_in_order([("veh_b", 2), ("veh_a", 1)])
    state.register_undetermined_visit(("veh_z", 3))
    state.register_undetermined_visit(("veh_m", 1))

    exported = state.export_state()
    assert set(exported.keys()) == {
        "node_name",
        "k_confirmed",
        "confirmed_visits",
        "undetermined_visits",
    }
    assert exported["node_name"] == "junction_a"
    assert exported["k_confirmed"] == 2

    confirmed_visits = exported["confirmed_visits"]
    assert [item["assigned_rank"] for item in confirmed_visits] == [1, 2]
    assert confirmed_visits[0] == {
        "vehicle_name": "veh_b",
        "visit_id": 2,
        "assigned_rank": 1,
    }
    for item in confirmed_visits:
        assert set(item.keys()) == {"vehicle_name", "visit_id", "assigned_rank"}

    undetermined_visits = exported["undetermined_visits"]
    assert undetermined_visits == [
        {"vehicle_name": "veh_c", "visit_id": 1},
        {"vehicle_name": "veh_m", "visit_id": 1},
        {"vehicle_name": "veh_z", "visit_id": 3},
    ]
    for item in undetermined_visits:
        assert set(item.keys()) == {"vehicle_name", "visit_id"}


def test_export_undetermined_visits_sorts_same_vehicle_by_visit_id():
    state = _new_state()
    # Registration order is 3, 1, 2 so a missing visit_id sort would keep
    # that order instead of the diagnostic order 1, 2, 3.
    state.register_undetermined_visits(
        [
            ("vehicle_same", 3),
            ("vehicle_same", 1),
            ("vehicle_same", 2),
        ]
    )
    exported = state.export_state()
    assert exported["undetermined_visits"] == [
        {
            "vehicle_name": "vehicle_same",
            "visit_id": 1,
        },
        {
            "vehicle_name": "vehicle_same",
            "visit_id": 2,
        },
        {
            "vehicle_name": "vehicle_same",
            "visit_id": 3,
        },
    ]


def test_export_state_isolation_from_nested_mutations():
    state = _new_state()
    _register(state, ("veh_a", 1), ("veh_b", 1), ("veh_c", 1))
    state.confirm_visits_in_order([("veh_a", 1)])

    exported = state.export_state()
    before = _snapshot_state(state)

    exported["node_name"] = "changed"
    exported["k_confirmed"] = 999
    exported["confirmed_visits"].append(
        {"vehicle_name": "hack", "visit_id": 9, "assigned_rank": 99}
    )
    exported["confirmed_visits"][0]["assigned_rank"] = 99
    exported["undetermined_visits"].append({"vehicle_name": "hack", "visit_id": 9})
    exported["undetermined_visits"][0]["visit_id"] = 99

    assert _snapshot_state(state) == before


def test_confirm_runtime_error_during_candidate_verification_leaves_state_unchanged():
    state = _new_state()
    existing_confirmed = ("veh_existing", 1)
    pending_first = ("veh_pending_a", 1)
    pending_second = ("veh_pending_b", 1)
    _register(state, existing_confirmed, pending_first, pending_second)
    state.confirm_visits_in_order([existing_confirmed])

    before_k_confirmed = state.k_confirmed()
    before_confirmed = state.confirmed_visit_keys_in_order()
    before_undetermined = state.undetermined_visit_keys()
    before_existing_rank = state.assigned_rank(existing_confirmed)
    before_export = state.export_state()
    confirm_column = [pending_first, pending_second]
    confirm_result = "not-called"

    with patch(
        "uxsim.order_control_tvt_node_rank_state._verify_candidate_confirmed_state",
        side_effect=RuntimeError("forced candidate verification failure"),
    ) as verify_mock:
        try:
            confirm_result = state.confirm_visits_in_order(confirm_column)
            raise AssertionError(
                "Expected RuntimeError from candidate verification; "
                f"got ConfirmResult {confirm_result!r}"
            )
        except RuntimeError as exc:
            assert str(exc) == "forced candidate verification failure"

    assert verify_mock.call_count == 1
    assert confirm_result == "not-called"
    assert state.k_confirmed() == before_k_confirmed
    assert state.confirmed_visit_keys_in_order() == before_confirmed
    assert state.undetermined_visit_keys() == before_undetermined
    assert state.assigned_rank(existing_confirmed) == before_existing_rank
    assert state.is_undetermined(pending_first) is True
    assert state.is_undetermined(pending_second) is True
    assert state.is_confirmed(pending_first) is False
    assert state.is_confirmed(pending_second) is False
    assert state.export_state() == before_export


def test_runtime_error_on_candidate_list_dict_length_mismatch():
    confirmed_list = [("veh_a", 1)]
    rank_dict: dict[OrderControlTvtVisitKey, int] = {}
    undetermined_set: set[OrderControlTvtVisitKey] = set()
    try:
        _verify_candidate_confirmed_state(
            confirmed_list,
            rank_dict,
            undetermined_set,
            k_confirmed_before=0,
            k_confirmed_after=1,
            newly_confirmed_count=1,
            newly_confirmed_visit_keys=(("veh_a", 1),),
        )
        raise AssertionError("Expected RuntimeError for list/dict length mismatch")
    except RuntimeError as exc:
        assert "length" in str(exc)


def test_runtime_error_on_candidate_rank_position_mismatch():
    confirmed_list = [("veh_a", 1)]
    rank_dict = {("veh_a", 1): 2}
    undetermined_set: set[OrderControlTvtVisitKey] = set()
    try:
        _verify_candidate_confirmed_state(
            confirmed_list,
            rank_dict,
            undetermined_set,
            k_confirmed_before=0,
            k_confirmed_after=1,
            newly_confirmed_count=1,
            newly_confirmed_visit_keys=(("veh_a", 1),),
        )
        raise AssertionError("Expected RuntimeError for rank mismatch")
    except RuntimeError as exc:
        assert "position" in str(exc) or "assigned_rank" in str(exc)


def test_runtime_error_when_confirmed_visit_remains_in_undetermined_set():
    visit_key = ("veh_a", 1)
    confirmed_list = [visit_key]
    rank_dict = {visit_key: 1}
    undetermined_set = {visit_key}
    try:
        _verify_candidate_confirmed_state(
            confirmed_list,
            rank_dict,
            undetermined_set,
            k_confirmed_before=0,
            k_confirmed_after=1,
            newly_confirmed_count=1,
            newly_confirmed_visit_keys=(visit_key,),
        )
        raise AssertionError(
            "Expected RuntimeError for confirmed visit in undetermined set"
        )
    except RuntimeError as exc:
        assert "undetermined" in str(exc)


def test_runtime_error_on_confirm_result_count_mismatch():
    confirmed_list = [("veh_a", 1)]
    rank_dict = {("veh_a", 1): 1}
    undetermined_set: set[OrderControlTvtVisitKey] = set()
    try:
        _verify_candidate_confirmed_state(
            confirmed_list,
            rank_dict,
            undetermined_set,
            k_confirmed_before=0,
            k_confirmed_after=1,
            newly_confirmed_count=2,
            newly_confirmed_visit_keys=(("veh_a", 1),),
        )
        raise AssertionError("Expected RuntimeError for count mismatch")
    except RuntimeError as exc:
        assert "newly_confirmed_count" in str(exc)


TESTS = [
    test_public_types_importable_from_dedicated_module,
    test_init_valid_node_name,
    test_init_rejects_empty_node_name,
    test_init_rejects_non_string_node_name,
    test_visit_key_accepts_valid_tuple,
    test_visit_key_rejects_empty_vehicle_name,
    test_visit_key_rejects_non_string_vehicle_name,
    test_visit_key_rejects_bool_visit_id,
    test_visit_key_rejects_non_int_visit_id,
    test_visit_key_rejects_zero_and_negative_visit_id,
    test_visit_key_rejects_non_tuple_container,
    test_visit_key_rejects_wrong_length_tuple,
    test_visit_key_rejects_numpy_integer_visit_id,
    test_same_vehicle_name_different_visit_id_are_distinct,
    test_single_register_adds_to_undetermined_only,
    test_single_register_rejects_duplicate_undetermined,
    test_single_register_rejects_confirmed_visit,
    test_batch_register_accepts_list_and_tuple,
    test_batch_register_rejects_non_list_or_tuple_container,
    test_batch_register_empty_list_and_tuple_are_no_op,
    test_batch_register_rejects_input_duplicate,
    test_batch_register_rejects_existing_undetermined_duplicate,
    test_batch_register_rejects_confirmed_contamination,
    test_batch_register_rejects_invalid_visit_key_without_partial_register,
    test_node_states_are_independent,
    test_confirm_empty_list_and_tuple_are_no_op,
    test_confirm_single_visit_starts_at_rank_one,
    test_confirm_multiple_visits_preserves_input_order,
    test_confirm_appends_after_existing_confirmed_block,
    test_confirm_result_count_fields_match,
    test_confirm_multiple_rounds_keep_contiguous_ranks,
    test_confirm_rejects_reconfirm_with_distinct_message,
    test_confirm_rejects_unregistered_with_distinct_message,
    test_reconfirm_and_unregistered_messages_differ,
    test_confirm_rejects_input_duplicate,
    test_confirm_rejects_non_list_or_tuple_container,
    test_confirm_leaves_state_unchanged_when_middle_key_unregistered,
    test_confirm_leaves_state_unchanged_when_middle_key_already_confirmed,
    test_confirm_input_list_mutation_after_call_does_not_change_state,
    test_staged_k_confirmed_before_after_external_preconfirm_columns,
    test_outside_decision_window_visit_confirmed_in_input_order,
    test_confirm_result_has_three_fields_only_and_is_frozen,
    test_read_confirmed_visit_keys_returns_tuple_not_internal_list,
    test_read_undetermined_visit_keys_returns_frozenset_not_internal_set,
    test_read_membership_and_assigned_rank_for_confirmed_undetermined_unregistered,
    test_read_apis_reject_invalid_visit_key,
    test_export_state_structure_and_sort_orders,
    test_export_undetermined_visits_sorts_same_vehicle_by_visit_id,
    test_export_state_isolation_from_nested_mutations,
    test_confirm_runtime_error_during_candidate_verification_leaves_state_unchanged,
    test_runtime_error_on_candidate_list_dict_length_mismatch,
    test_runtime_error_on_candidate_rank_position_mismatch,
    test_runtime_error_when_confirmed_visit_remains_in_undetermined_set,
    test_runtime_error_on_confirm_result_count_mismatch,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(
        f"Order-control TVT node rank state tests passed ({len(TESTS)} tests)."
    )
