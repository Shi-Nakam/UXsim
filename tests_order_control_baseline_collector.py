# Unit tests for OrderControlBaselineCollector (design memo §25.17, phase-1 scope).
#
# Run from the repository root:
#   python tests_order_control_baseline_collector.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from uxsim.order_control_baseline_collector import (
    OrderControlBaselineCollector,
    OrderControlBaselineVisitRecord,
)
from uxsim import World


def _new_collector() -> OrderControlBaselineCollector:
    return OrderControlBaselineCollector()


def _register_arrived_a(
    collector: OrderControlBaselineCollector,
    *,
    vehicle_name: str = "veh_a",
    vehicle_id: int = 0,
    node_name: str = "merge",
    inlink_name: str = "in1",
    visit_id: int = 1,
    baseline_arrival_timestep: int = 50,
    arrival_tiebreaker: float = 0.25,
    route_next_link_name: str = "out",
) -> None:
    collector.register_snapshot_visit(
        vehicle_name=vehicle_name,
        vehicle_id=vehicle_id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=baseline_arrival_timestep,
        arrival_tiebreaker=arrival_tiebreaker,
        route_next_link_name=route_next_link_name,
        baseline_passage_timestep=None,
    )


def _register_not_arrived_b(
    collector: OrderControlBaselineCollector,
    *,
    vehicle_name: str = "veh_b",
    vehicle_id: int = 1,
    node_name: str = "merge",
    inlink_name: str = "in2",
    visit_id: int = 2,
) -> None:
    collector.register_snapshot_visit(
        vehicle_name=vehicle_name,
        vehicle_id=vehicle_id,
        node_name=node_name,
        inlink_name=inlink_name,
        visit_id=visit_id,
        was_arrived_at_snapshot=False,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
        baseline_passage_timestep=None,
    )


def _assert_same_record_in_all_indexes(
    collector: OrderControlBaselineCollector,
    record: OrderControlBaselineVisitRecord,
) -> None:
    primary = collector._visit_records_by_primary_key[
        (record.vehicle_name, record.visit_id)
    ]
    by_vehicle = collector._visit_record_by_vehicle_name[record.vehicle_name]
    node_list = collector._visit_records_by_node_name[record.node_name]
    assert primary is record
    assert by_vehicle is record
    assert record in node_list


def test_register_arrived_snapshot_visit_a():
    collector = _new_collector()
    _register_arrived_a(collector)
    record = collector._visit_records_by_primary_key[("veh_a", 1)]
    assert record.was_arrived_at_snapshot is True
    assert record.baseline_arrival_timestep == 50
    assert record.arrival_tiebreaker == 0.25
    assert record.route_next_link_name == "out"
    assert record.baseline_passage_timestep is None
    _assert_same_record_in_all_indexes(collector, record)


def test_register_not_arrived_snapshot_visit_b():
    collector = _new_collector()
    _register_not_arrived_b(collector)
    record = collector._visit_records_by_primary_key[("veh_b", 2)]
    assert record.was_arrived_at_snapshot is False
    assert record.baseline_arrival_timestep is None
    assert record.arrival_tiebreaker is None
    assert record.route_next_link_name is None
    _assert_same_record_in_all_indexes(collector, record)


def test_register_rejects_duplicate_primary_key():
    collector = _new_collector()
    _register_arrived_a(collector, vehicle_name="veh_x", visit_id=3)
    try:
        collector.register_snapshot_visit(
            vehicle_name="veh_x",
            vehicle_id=9,
            node_name="merge",
            inlink_name="in9",
            visit_id=3,
            was_arrived_at_snapshot=False,
            baseline_arrival_timestep=None,
            arrival_tiebreaker=None,
            route_next_link_name=None,
            baseline_passage_timestep=None,
        )
        raise AssertionError("Expected ValueError for duplicate primary key")
    except ValueError as exc:
        assert "Duplicate snapshot visit primary key" in str(exc)


def test_register_rejects_same_vehicle_second_visit():
    collector = _new_collector()
    _register_arrived_a(collector, vehicle_name="veh_dup", visit_id=1)
    try:
        _register_not_arrived_b(collector, vehicle_name="veh_dup", visit_id=2)
        raise AssertionError("Expected ValueError for duplicate vehicle_name")
    except ValueError as exc:
        assert "already registered" in str(exc)


def test_record_baseline_arrival_for_b():
    collector = _new_collector()
    _register_not_arrived_b(collector)
    collector.record_baseline_arrival(
        vehicle_name="veh_b",
        visit_id=2,
        node_name="merge",
        baseline_arrival_timestep=55,
        arrival_tiebreaker=0.5,
        route_next_link_name="out",
    )
    record = collector._visit_records_by_primary_key[("veh_b", 2)]
    assert record.baseline_arrival_timestep == 55
    assert record.arrival_tiebreaker == 0.5
    assert record.route_next_link_name == "out"


def test_record_baseline_arrival_ignores_outside_fixed_set():
    collector = _new_collector()
    _register_arrived_a(collector)
    collector.record_baseline_arrival(
        vehicle_name="outside",
        visit_id=99,
        node_name="merge",
        baseline_arrival_timestep=60,
        arrival_tiebreaker=0.1,
        route_next_link_name="out",
    )


def test_record_baseline_arrival_rejects_duplicate_for_arrived_a():
    collector = _new_collector()
    _register_arrived_a(collector)
    try:
        collector.record_baseline_arrival(
            vehicle_name="veh_a",
            visit_id=1,
            node_name="merge",
            baseline_arrival_timestep=51,
            arrival_tiebreaker=0.9,
            route_next_link_name="out",
        )
        raise AssertionError("Expected ValueError for A duplicate arrival")
    except ValueError as exc:
        assert "snapshot-arrived visit" in str(exc)


def test_record_baseline_arrival_rejects_duplicate_for_b():
    collector = _new_collector()
    _register_not_arrived_b(collector)
    collector.record_baseline_arrival(
        vehicle_name="veh_b",
        visit_id=2,
        node_name="merge",
        baseline_arrival_timestep=55,
        arrival_tiebreaker=0.5,
        route_next_link_name="out",
    )
    try:
        collector.record_baseline_arrival(
            vehicle_name="veh_b",
            visit_id=2,
            node_name="merge",
            baseline_arrival_timestep=56,
            arrival_tiebreaker=0.6,
            route_next_link_name="out",
        )
        raise AssertionError("Expected ValueError for B duplicate arrival")
    except ValueError as exc:
        assert "Duplicate or partial arrival state" in str(exc)


def test_prepare_baseline_passage_recording_returns_none_outside_fixed_set():
    collector = _new_collector()
    _register_arrived_a(collector)
    result = collector.prepare_baseline_passage_recording(
        vehicle_name="unknown",
        visit_id=1,
        node_name="merge",
    )
    assert result is None


def test_prepare_baseline_passage_recording_success_for_arrived_a():
    collector = _new_collector()
    _register_arrived_a(collector)
    record = collector.prepare_baseline_passage_recording(
        vehicle_name="veh_a",
        visit_id=1,
        node_name="merge",
    )
    assert record is collector._visit_records_by_primary_key[("veh_a", 1)]


def test_prepare_baseline_passage_recording_rejects_not_yet_arrived_b():
    collector = _new_collector()
    _register_not_arrived_b(collector)
    try:
        collector.prepare_baseline_passage_recording(
            vehicle_name="veh_b",
            visit_id=2,
            node_name="merge",
        )
        raise AssertionError("Expected ValueError for not-yet-arrived B passage")
    except ValueError as exc:
        assert "before baseline arrival is recorded" in str(exc)


def test_prepare_baseline_passage_recording_rejects_duplicate_passage():
    collector = _new_collector()
    _register_arrived_a(collector)
    record = collector.prepare_baseline_passage_recording(
        vehicle_name="veh_a",
        visit_id=1,
        node_name="merge",
    )
    collector.apply_baseline_passage_timestep(record, 60)
    try:
        collector.prepare_baseline_passage_recording(
            vehicle_name="veh_a",
            visit_id=1,
            node_name="merge",
        )
        raise AssertionError("Expected ValueError for duplicate passage")
    except ValueError as exc:
        assert "Duplicate passage recording" in str(exc)


def test_apply_baseline_passage_timestep_sets_timestep():
    collector = _new_collector()
    _register_arrived_a(collector)
    record = collector.prepare_baseline_passage_recording(
        vehicle_name="veh_a",
        visit_id=1,
        node_name="merge",
    )
    collector.apply_baseline_passage_timestep(record, 62)
    assert record.baseline_passage_timestep == 62


def test_export_node_baseline_visits_returns_plain_dict_copies():
    collector = _new_collector()
    _register_arrived_a(collector)
    _register_not_arrived_b(collector)
    exported = collector.export_node_baseline_visits("merge")
    assert len(exported) == 2
    for item in exported:
        assert isinstance(item, dict)
        assert set(item.keys()) == {
            "vehicle_name",
            "vehicle_id",
            "node_name",
            "inlink_name",
            "visit_id",
            "was_arrived_at_snapshot",
            "baseline_arrival_timestep",
            "arrival_tiebreaker",
            "route_next_link_name",
            "baseline_passage_timestep",
        }
    names = {item["vehicle_name"] for item in exported}
    assert names == {"veh_a", "veh_b"}


def test_get_baseline_visit_snapshot_returns_plain_dict_copy():
    collector = _new_collector()
    _register_arrived_a(collector)
    snapshot = collector.get_baseline_visit_snapshot("veh_a", 1)
    assert snapshot is not None
    assert snapshot["vehicle_name"] == "veh_a"
    assert snapshot["visit_id"] == 1
    assert snapshot["baseline_arrival_timestep"] == 50


def test_read_results_do_not_mutate_collector_internal_state():
    collector = _new_collector()
    _register_arrived_a(collector)
    record_before = collector._visit_records_by_primary_key[("veh_a", 1)]

    node_export = collector.export_node_baseline_visits("merge")
    node_export[0]["baseline_arrival_timestep"] = 999
    node_export.append({"vehicle_name": "fake"})

    single = collector.get_baseline_visit_snapshot("veh_a", 1)
    assert single is not None
    single["route_next_link_name"] = "mutated"

    record_after = collector._visit_records_by_primary_key[("veh_a", 1)]
    assert record_after is record_before
    assert record_after.baseline_arrival_timestep == 50
    assert record_after.route_next_link_name == "out"
    assert len(collector.export_node_baseline_visits("merge")) == 1


def test_register_rejects_bool_visit_id():
    collector = _new_collector()
    try:
        collector.register_snapshot_visit(
            vehicle_name="veh",
            vehicle_id=0,
            node_name="merge",
            inlink_name="in1",
            visit_id=True,
            was_arrived_at_snapshot=False,
            baseline_arrival_timestep=None,
            arrival_tiebreaker=None,
            route_next_link_name=None,
            baseline_passage_timestep=None,
        )
        raise AssertionError("Expected ValueError for bool visit_id")
    except ValueError as exc:
        assert "visit_id" in str(exc)


def test_register_rejects_zero_and_negative_visit_id():
    collector = _new_collector()
    for bad_visit_id in (0, -1):
        try:
            collector.register_snapshot_visit(
                vehicle_name="veh",
                vehicle_id=0,
                node_name="merge",
                inlink_name="in1",
                visit_id=bad_visit_id,
                was_arrived_at_snapshot=False,
                baseline_arrival_timestep=None,
                arrival_tiebreaker=None,
                route_next_link_name=None,
                baseline_passage_timestep=None,
            )
            raise AssertionError(f"Expected ValueError for visit_id={bad_visit_id}")
        except ValueError as exc:
            assert "visit_id" in str(exc)


def test_register_rejects_bool_and_negative_vehicle_id():
    collector = _new_collector()
    for bad_vehicle_id in (True, -1):
        try:
            collector.register_snapshot_visit(
                vehicle_name="veh",
                vehicle_id=bad_vehicle_id,
                node_name="merge",
                inlink_name="in1",
                visit_id=1,
                was_arrived_at_snapshot=False,
                baseline_arrival_timestep=None,
                arrival_tiebreaker=None,
                route_next_link_name=None,
                baseline_passage_timestep=None,
            )
            raise AssertionError(
                f"Expected ValueError for vehicle_id={bad_vehicle_id!r}"
            )
        except ValueError as exc:
            assert "vehicle_id" in str(exc)


def test_register_arrived_a_rejects_missing_arrival_fields():
    collector = _new_collector()
    try:
        collector.register_snapshot_visit(
            vehicle_name="veh",
            vehicle_id=0,
            node_name="merge",
            inlink_name="in1",
            visit_id=1,
            was_arrived_at_snapshot=True,
            baseline_arrival_timestep=None,
            arrival_tiebreaker=0.1,
            route_next_link_name="out",
            baseline_passage_timestep=None,
        )
        raise AssertionError("Expected ValueError for missing arrival timestep on A")
    except ValueError as exc:
        assert "baseline_arrival_timestep" in str(exc)


def test_register_not_arrived_b_rejects_arrival_fields_present():
    collector = _new_collector()
    try:
        collector.register_snapshot_visit(
            vehicle_name="veh",
            vehicle_id=0,
            node_name="merge",
            inlink_name="in1",
            visit_id=1,
            was_arrived_at_snapshot=False,
            baseline_arrival_timestep=50,
            arrival_tiebreaker=None,
            route_next_link_name=None,
            baseline_passage_timestep=None,
        )
        raise AssertionError("Expected ValueError for B with arrival timestep")
    except ValueError as exc:
        assert "baseline_arrival_timestep" in str(exc)


def test_record_baseline_arrival_rejects_node_mismatch():
    collector = _new_collector()
    _register_not_arrived_b(collector)
    try:
        collector.record_baseline_arrival(
            vehicle_name="veh_b",
            visit_id=2,
            node_name="other_node",
            baseline_arrival_timestep=55,
            arrival_tiebreaker=0.5,
            route_next_link_name="out",
        )
        raise AssertionError("Expected ValueError for arrival node mismatch")
    except ValueError as exc:
        assert "Node mismatch" in str(exc)


def test_prepare_baseline_passage_recording_rejects_visit_id_mismatch():
    collector = _new_collector()
    _register_arrived_a(collector, visit_id=4)
    try:
        collector.prepare_baseline_passage_recording(
            vehicle_name="veh_a",
            visit_id=99,
            node_name="merge",
        )
        raise AssertionError("Expected ValueError for visit_id mismatch")
    except ValueError as exc:
        assert "visit_id mismatch" in str(exc)


def test_prepare_baseline_passage_recording_rejects_node_mismatch():
    collector = _new_collector()
    _register_arrived_a(collector)
    try:
        collector.prepare_baseline_passage_recording(
            vehicle_name="veh_a",
            visit_id=1,
            node_name="other_node",
        )
        raise AssertionError("Expected ValueError for passage node mismatch")
    except ValueError as exc:
        assert "Node mismatch" in str(exc)


def test_prepare_baseline_passage_recording_rejects_missing_arrival_tiebreaker():
    collector = _new_collector()
    collector.register_snapshot_visit(
        vehicle_name="veh_partial",
        vehicle_id=3,
        node_name="merge",
        inlink_name="in3",
        visit_id=5,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=50,
        arrival_tiebreaker=0.2,
        route_next_link_name="out",
        baseline_passage_timestep=None,
    )
    record = collector._visit_records_by_primary_key[("veh_partial", 5)]
    record.arrival_tiebreaker = None
    try:
        collector.prepare_baseline_passage_recording(
            vehicle_name="veh_partial",
            visit_id=5,
            node_name="merge",
        )
        raise AssertionError("Expected ValueError for missing arrival_tiebreaker")
    except ValueError as exc:
        assert "arrival_tiebreaker" in str(exc)


def test_prepare_baseline_passage_recording_rejects_missing_route_next_link_name():
    collector = _new_collector()
    collector.register_snapshot_visit(
        vehicle_name="veh_partial",
        vehicle_id=4,
        node_name="merge",
        inlink_name="in4",
        visit_id=6,
        was_arrived_at_snapshot=True,
        baseline_arrival_timestep=50,
        arrival_tiebreaker=0.2,
        route_next_link_name="out",
        baseline_passage_timestep=None,
    )
    record = collector._visit_records_by_primary_key[("veh_partial", 6)]
    record.route_next_link_name = None
    try:
        collector.prepare_baseline_passage_recording(
            vehicle_name="veh_partial",
            visit_id=6,
            node_name="merge",
        )
        raise AssertionError("Expected ValueError for missing route_next_link_name")
    except ValueError as exc:
        assert "route_next_link_name" in str(exc)


def test_export_node_baseline_visits_returns_empty_list_for_unknown_node():
    collector = _new_collector()
    _register_arrived_a(collector)
    assert collector.export_node_baseline_visits("missing_node") == []


def test_get_baseline_visit_snapshot_returns_none_for_unknown_visit():
    collector = _new_collector()
    _register_arrived_a(collector)
    assert collector.get_baseline_visit_snapshot("veh_a", 999) is None
    assert collector.get_baseline_visit_snapshot("missing", 1) is None


def test_world_initializes_baseline_collector_reference_to_none():
    W = World(
        name="baseline_collector_world_init",
        deltan=1,
        tmax=10,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )
    assert hasattr(W, "_order_control_baseline_collector")
    assert W._order_control_baseline_collector is None


def _collector_snapshot_state(collector: OrderControlBaselineCollector) -> dict:
    return {
        key: collector.get_baseline_visit_snapshot(key[0], key[1])
        for key in collector._visit_records_by_primary_key
    }


def test_record_baseline_arrival_ignores_outside_fixed_set_without_validating_arrival_payload():
    collector = _new_collector()
    _register_arrived_a(collector)
    _register_not_arrived_b(collector)
    state_before = _collector_snapshot_state(collector)

    collector.record_baseline_arrival(
        vehicle_name="outside_vehicle",
        visit_id=999,
        node_name=None,
        baseline_arrival_timestep=None,
        arrival_tiebreaker=None,
        route_next_link_name=None,
    )

    assert _collector_snapshot_state(collector) == state_before


def test_record_baseline_arrival_checks_node_mismatch_before_new_arrival_validation_for_b():
    collector = _new_collector()
    _register_not_arrived_b(collector)
    try:
        collector.record_baseline_arrival(
            vehicle_name="veh_b",
            visit_id=2,
            node_name="other_node",
            baseline_arrival_timestep=None,
            arrival_tiebreaker=None,
            route_next_link_name=None,
        )
        raise AssertionError(
            "Expected Node mismatch before new arrival value validation"
        )
    except ValueError as exc:
        assert "Node mismatch" in str(exc)
        assert "baseline_arrival_timestep" not in str(exc)


def test_record_baseline_arrival_checks_a_duplicate_before_new_arrival_validation():
    collector = _new_collector()
    _register_arrived_a(collector)
    try:
        collector.record_baseline_arrival(
            vehicle_name="veh_a",
            visit_id=1,
            node_name="merge",
            baseline_arrival_timestep=None,
            arrival_tiebreaker=None,
            route_next_link_name=None,
        )
        raise AssertionError(
            "Expected A duplicate arrival before new arrival value validation"
        )
    except ValueError as exc:
        assert "snapshot-arrived visit" in str(exc)
        assert "baseline_arrival_timestep" not in str(exc)


def test_prepare_baseline_passage_recording_returns_none_outside_fixed_set_without_validating_payload():
    collector = _new_collector()
    _register_arrived_a(collector)
    result = collector.prepare_baseline_passage_recording(
        vehicle_name="outside_vehicle",
        visit_id=None,
        node_name=None,
    )
    assert result is None


TESTS = [
    test_register_arrived_snapshot_visit_a,
    test_register_not_arrived_snapshot_visit_b,
    test_register_rejects_duplicate_primary_key,
    test_register_rejects_same_vehicle_second_visit,
    test_record_baseline_arrival_for_b,
    test_record_baseline_arrival_ignores_outside_fixed_set,
    test_record_baseline_arrival_rejects_duplicate_for_arrived_a,
    test_record_baseline_arrival_rejects_duplicate_for_b,
    test_prepare_baseline_passage_recording_returns_none_outside_fixed_set,
    test_prepare_baseline_passage_recording_success_for_arrived_a,
    test_prepare_baseline_passage_recording_rejects_not_yet_arrived_b,
    test_prepare_baseline_passage_recording_rejects_duplicate_passage,
    test_apply_baseline_passage_timestep_sets_timestep,
    test_export_node_baseline_visits_returns_plain_dict_copies,
    test_get_baseline_visit_snapshot_returns_plain_dict_copy,
    test_read_results_do_not_mutate_collector_internal_state,
    test_register_rejects_bool_visit_id,
    test_register_rejects_zero_and_negative_visit_id,
    test_register_rejects_bool_and_negative_vehicle_id,
    test_register_arrived_a_rejects_missing_arrival_fields,
    test_register_not_arrived_b_rejects_arrival_fields_present,
    test_record_baseline_arrival_rejects_node_mismatch,
    test_prepare_baseline_passage_recording_rejects_visit_id_mismatch,
    test_prepare_baseline_passage_recording_rejects_node_mismatch,
    test_prepare_baseline_passage_recording_rejects_missing_arrival_tiebreaker,
    test_prepare_baseline_passage_recording_rejects_missing_route_next_link_name,
    test_export_node_baseline_visits_returns_empty_list_for_unknown_node,
    test_get_baseline_visit_snapshot_returns_none_for_unknown_visit,
    test_world_initializes_baseline_collector_reference_to_none,
    test_record_baseline_arrival_ignores_outside_fixed_set_without_validating_arrival_payload,
    test_record_baseline_arrival_checks_node_mismatch_before_new_arrival_validation_for_b,
    test_record_baseline_arrival_checks_a_duplicate_before_new_arrival_validation,
    test_prepare_baseline_passage_recording_returns_none_outside_fixed_set_without_validating_payload,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print("Order-control baseline collector tests passed.")
